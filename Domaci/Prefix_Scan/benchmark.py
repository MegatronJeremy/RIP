"""
CUDA prefix sum benchmark: CPU vs Hillis-Steele vs Blelloch vs Warp Shuffle.

Sve tri GPU implementacije koriste isti multi-block obrazac:
  1. per-block inclusive scan (algoritam se razlikuje izmedju implementacija)
  2. rekurzivni scan block-totala
  3. dodaj prefiks prethodnih blokova nazad

Razlikuju se samo u tome KAKO rade scan jednog bloka.
"""

import cupy as cp
import numpy as np
import time
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Hillis-Steele (original, O(N log N) work, single buffer sa dva sync-a)
# ---------------------------------------------------------------------------
HILLIS_STEELE = r'''
extern "C" {

__global__ void hsBlockScan(float *d_out, float *d_in, float *d_blockSums, int n) {
    extern __shared__ float temp[];
    int tid = threadIdx.x;
    int gid = blockIdx.x * blockDim.x + tid;
    int bs  = blockDim.x;

    temp[tid] = (gid < n) ? d_in[gid] : 0.0f;
    __syncthreads();

    for (int d = 1; d < bs; d *= 2) {
        float val = (tid >= d) ? temp[tid - d] : 0.0f;
        __syncthreads();
        if (tid >= d) temp[tid] += val;
        __syncthreads();
    }

    if (gid < n)        d_out[gid] = temp[tid];
    if (tid == bs - 1)  d_blockSums[blockIdx.x] = temp[tid];
}

}
'''

# ---------------------------------------------------------------------------
# Blelloch (work-efficient, O(N) work, upsweep + downsweep).
# Nativno daje EXCLUSIVE scan; konvertujemo u inclusive dodavanjem d_in.
# Napomena: bez padding-a za bank conflicts radi citljivosti -- to bi bila
# sledeca optimizacija (vidi GPU Gems 3, Ch. 39).
# ---------------------------------------------------------------------------
BLELLOCH = r'''
extern "C" {

__global__ void blellochBlockScan(float *d_out, float *d_in, float *d_blockSums, int n) {
    extern __shared__ float temp[];
    int tid = threadIdx.x;
    int gid = blockIdx.x * blockDim.x + tid;
    int bs  = blockDim.x;

    float my_in = (gid < n) ? d_in[gid] : 0.0f;
    temp[tid] = my_in;
    __syncthreads();

    // Upsweep (reduce phase) - gradimo binarno stablo parcijalnih suma
    int offset = 1;
    for (int d = bs >> 1; d > 0; d >>= 1) {
        __syncthreads();
        if (tid < d) {
            int ai = offset * (2*tid + 1) - 1;
            int bi = offset * (2*tid + 2) - 1;
            temp[bi] += temp[ai];
        }
        offset *= 2;
    }

    // Sacuvaj block total, postavi koren na 0
    if (tid == 0) {
        d_blockSums[blockIdx.x] = temp[bs - 1];
        temp[bs - 1] = 0.0f;
    }

    // Downsweep - propagiramo prefikse niz stablo
    for (int d = 1; d < bs; d *= 2) {
        offset >>= 1;
        __syncthreads();
        if (tid < d) {
            int ai = offset * (2*tid + 1) - 1;
            int bi = offset * (2*tid + 2) - 1;
            float t   = temp[ai];
            temp[ai]  = temp[bi];
            temp[bi] += t;
        }
    }
    __syncthreads();

    // Exclusive -> inclusive
    if (gid < n) d_out[gid] = temp[tid] + my_in;
}

}
'''

# ---------------------------------------------------------------------------
# Warp shuffle scan - dvostepeni: scan unutar warp-a kroz __shfl_up_sync,
# zatim scan warp-totala, pa dodaj nazad. Shared memory samo za warp-totale.
# ---------------------------------------------------------------------------
WARP_SHUFFLE = r'''
extern "C" {

__device__ __forceinline__ float warpInclusiveScan(float val) {
    int lane = threadIdx.x & 31;
    #pragma unroll
    for (int d = 1; d < 32; d *= 2) {
        float t = __shfl_up_sync(0xffffffff, val, d);
        if (lane >= d) val += t;
    }
    return val;
}

__global__ void warpBlockScan(float *d_out, float *d_in, float *d_blockSums, int n) {
    __shared__ float warp_sums[32];  // dovoljno za blockDim <= 1024

    int tid     = threadIdx.x;
    int gid     = blockIdx.x * blockDim.x + tid;
    int lane    = tid & 31;
    int warp_id = tid >> 5;
    int n_warps = (blockDim.x + 31) >> 5;

    float val = (gid < n) ? d_in[gid] : 0.0f;

    // 1. scan unutar warp-a (potpuno u registrima, bez shared mem, bez barijera)
    val = warpInclusiveScan(val);

    // 2. poslednja nit svakog warp-a upisuje warp-total
    if (lane == 31) warp_sums[warp_id] = val;
    __syncthreads();

    // 3. prvi warp skenira warp-totale
    if (warp_id == 0) {
        float w = (lane < n_warps) ? warp_sums[lane] : 0.0f;
        w = warpInclusiveScan(w);
        if (lane < n_warps) warp_sums[lane] = w;
    }
    __syncthreads();

    // 4. dodaj prefiks prethodnih warp-ova
    if (warp_id > 0) val += warp_sums[warp_id - 1];

    if (gid < n)               d_out[gid] = val;
    if (tid == blockDim.x - 1) d_blockSums[blockIdx.x] = val;
}

}
'''

# ---------------------------------------------------------------------------
# Zajednicki kernel: dodaj scanovane block-totale natrag svakom bloku > 0
# ---------------------------------------------------------------------------
ADD_BLOCK_SUMS = r'''
extern "C" __global__
void addBlockSums(float *d_out, float *d_blockSumsScanned, int n) {
    int gid = blockIdx.x * blockDim.x + threadIdx.x;
    if (blockIdx.x > 0 && gid < n) {
        d_out[gid] += d_blockSumsScanned[blockIdx.x - 1];
    }
}
'''

_hs    = cp.RawModule(code=HILLIS_STEELE).get_function('hsBlockScan')
_bl    = cp.RawModule(code=BLELLOCH).get_function('blellochBlockScan')
_ws    = cp.RawModule(code=WARP_SHUFFLE).get_function('warpBlockScan')
_add   = cp.RawModule(code=ADD_BLOCK_SUMS).get_function('addBlockSums')

BLOCK_SIZE = 1024  # mora biti stepen dvojke (Blelloch zahteva)


def _multiblock_scan(d_in, block_scan_kernel, shared_mem_bytes):
    """Generic multi-block scaffolding -- razlikuje se samo block_scan_kernel."""
    n = d_in.size
    d_out = cp.empty_like(d_in)
    num_blocks = (n + BLOCK_SIZE - 1) // BLOCK_SIZE

    if num_blocks == 1:
        d_block_sums = cp.zeros(1, dtype=cp.float32)
        block_scan_kernel((1,), (BLOCK_SIZE,),
                          (d_out, d_in, d_block_sums, np.int32(n)),
                          shared_mem=shared_mem_bytes)
        return d_out

    d_block_sums = cp.empty(num_blocks, dtype=cp.float32)
    block_scan_kernel((num_blocks,), (BLOCK_SIZE,),
                      (d_out, d_in, d_block_sums, np.int32(n)),
                      shared_mem=shared_mem_bytes)

    d_block_sums_scanned = _multiblock_scan(d_block_sums, block_scan_kernel,
                                            shared_mem_bytes)

    _add((num_blocks,), (BLOCK_SIZE,),
         (d_out, d_block_sums_scanned, np.int32(n)))
    return d_out


def scan_hillis_steele(d_in):
    return _multiblock_scan(d_in, _hs, BLOCK_SIZE * 4)


def scan_blelloch(d_in):
    return _multiblock_scan(d_in, _bl, BLOCK_SIZE * 4)


def scan_warp_shuffle(d_in):
    # warp_sums je staticko shared mem unutar kernela; eksterno 0
    return _multiblock_scan(d_in, _ws, 0)


# ---------------------------------------------------------------------------
# Tajmiranje
# ---------------------------------------------------------------------------
def time_gpu(fn, d_in, iters=100, warmup=10):
    for _ in range(warmup):
        fn(d_in)
    cp.cuda.Stream.null.synchronize()
    start, end = cp.cuda.Event(), cp.cuda.Event()
    start.record()
    for _ in range(iters):
        fn(d_in)
    end.record()
    end.synchronize()
    return cp.cuda.get_elapsed_time(start, end) / 1000.0 / iters


def time_cpu(arr, iters=100, warmup=5):
    for _ in range(warmup):
        np.cumsum(arr)
    t0 = time.perf_counter()
    for _ in range(iters):
        np.cumsum(arr)
    return (time.perf_counter() - t0) / iters


def check(h_in, fn, name):
    ref = np.cumsum(h_in)
    out = fn(cp.asarray(h_in)).get()
    rtol = max(1e-3, 1e-6 * len(h_in))
    if not np.allclose(out, ref, rtol=rtol, atol=1e-3 * np.max(np.abs(ref))):
        max_err = np.max(np.abs(out - ref)) / max(np.max(np.abs(ref)), 1e-9)
        print(f"  [warn] {name} max rel err {max_err:.2e} at N={len(h_in)}")


def main():
    sizes = [2 ** i for i in range(8, 25)]  # 256 .. ~16M

    print(f"{'N':>10}  {'CPU':>9}  {'HS':>9}  {'Blelloch':>9}  {'WarpShfl':>9}  "
          f"{'HS x':>6}  {'Bl x':>6}  {'WS x':>6}")
    print("-" * 90)

    rows = []
    for n in sizes:
        rng = np.random.default_rng(0)
        h_in = rng.random(n, dtype=np.float32)
        d_in = cp.asarray(h_in)

        if n in (256, 4096, 65536, 1048576, 16777216):
            check(h_in, scan_hillis_steele, 'HS')
            check(h_in, scan_blelloch,      'Blelloch')
            check(h_in, scan_warp_shuffle,  'WarpShfl')

        iters = max(10, min(2000, 10_000_000 // n))

        t_cpu = time_cpu(h_in, iters=iters)
        t_hs  = time_gpu(scan_hillis_steele, d_in, iters=iters)
        t_bl  = time_gpu(scan_blelloch,      d_in, iters=iters)
        t_ws  = time_gpu(scan_warp_shuffle,  d_in, iters=iters)

        rows.append((n, t_cpu, t_hs, t_bl, t_ws))
        print(f"{n:>10}  {t_cpu*1e6:>8.1f}us  {t_hs*1e6:>8.1f}us  "
              f"{t_bl*1e6:>8.1f}us  {t_ws*1e6:>8.1f}us  "
              f"{t_cpu/t_hs:>5.2f}x  {t_cpu/t_bl:>5.2f}x  {t_cpu/t_ws:>5.2f}x")

    ns      = [r[0] for r in rows]
    cpu_us  = [r[1] * 1e6 for r in rows]
    hs_us   = [r[2] * 1e6 for r in rows]
    bl_us   = [r[3] * 1e6 for r in rows]
    ws_us   = [r[4] * 1e6 for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    ax1.loglog(ns, cpu_us, 'o-', label='CPU (numpy.cumsum)', lw=2)
    ax1.loglog(ns, hs_us,  's-', label='Hillis-Steele',      lw=2)
    ax1.loglog(ns, bl_us,  '^-', label='Blelloch',           lw=2)
    ax1.loglog(ns, ws_us,  'd-', label='Warp shuffle',       lw=2)
    ax1.set_xlabel('N')
    ax1.set_ylabel('Time (μs)')
    ax1.set_title('Prefix sum: CPU vs 3 GPU implementations')
    ax1.legend()
    ax1.grid(True, which='both', alpha=0.3)

    ax2.loglog(ns, [c/h for c, h in zip(cpu_us, hs_us)], 's-', label='HS',           lw=2)
    ax2.loglog(ns, [c/b for c, b in zip(cpu_us, bl_us)], '^-', label='Blelloch',     lw=2)
    ax2.loglog(ns, [c/w for c, w in zip(cpu_us, ws_us)], 'd-', label='Warp shuffle', lw=2)
    ax2.axhline(1.0, color='k', linestyle='--', alpha=0.5, label='break-even')
    ax2.set_xlabel('N')
    ax2.set_ylabel('Speedup over CPU')
    ax2.set_title('GPU speedup over CPU')
    ax2.legend()
    ax2.grid(True, which='both', alpha=0.3)

    plt.tight_layout()
    plt.savefig('scan_benchmark.png', dpi=120)
    print("\nSaved scan_benchmark.png")


if __name__ == '__main__':
    main()
