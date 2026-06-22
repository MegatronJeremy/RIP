# Indeks materijala — RIP (Veljko Milutinović)

Sažetak svih preuzetih predavanja/materijala, sa najbitnijim poentama po fajlu.
Svi originalni fajlovi su u ovom folderu (`oskar_slides/`, `maxeler/`) zajedno sa
`*_extracted.txt` verzijama (sirov tekst izvučen iz slajdova/PDF-ova).

## Okvir kursa — "The Optimal Architecture"
(iz `maxeler/The_Ultimate_DataFlow_for_Ultimate_SuperComputers_on_a_Chips.pptx`)

Veljkova centralna teza — podela optimalne arhitekture po slojevima, što se
direktno poklapa sa temama domaćih:

- **ControlFlow (CF):** N MultiCore CPU-ova, 1000N ManyCore GPU-ova → tema **CF multicore/manycore**
- **DataFlow (DF):** ASIC SystolicArray (fiksno) i FPGA ExecutionGraph (rekonfigurabilno) → tema **DF maxDFE / DF googleTPU**
- **EnergyFlow:** periferije za eksterne akceleratore — Bio, Molekularno, Opto, Quantum → teme **Bio, Chem, Opto, Quantum**
- **DiffusionFlow:** memorija i I/O

Raspodela tranzistorskog budžeta zavisi od: VLSI/WSI plafona, tipa aplikacije
(SW DataFlow / ML), strategije (CF- vs DF-orijentisano) i memorije.

Slajd 4+ sadrži veliku komparativnu tabelu proizvođača CPU/GPU čipova
(Alibaba, RISC-V, SiFive, AMD, Nvidia, Esperanto, Intel, MCST Elbrus...) —
korisno kao referenca za domaći "CF multicore/manycore".

---

## Oskar Mencer — Tutorial Slides: Theory (7 delova)
MaxAcademy Lecture Series, septembar 2011. Ovo je teorijska osnova za
**DF maxDFE** temu domaćeg.

### 01 — Introduction and Motivation
- Problem exaflop superkompjutera: 1 exaflop = 10^18 FLOPS; sa CPU jezgrima
  (8 FLOPS/clock @ 2.5GHz) trebalo bi 50M jezgara → ~500k čipova → ~50-100MW
  samo za CPU (poređenje: 'Jaguar' supercomputer trošio 6MW).
- Power efficiency: Green500 — najbolji (BlueGene/Q) 1.6 GFLOPS/W; da bi se
  dostiglo 1 exaflop na 6MW potrebno je 170 GFLOPS/W.
- Specijalizovani čip (ASIC) za jednu aplikaciju: nema instrukcija, nema
  branch prediction, eksplicitan paralelizam, streaming bez multi-level keša.
  Problem: nepraktično imati mašinu optimizovanu samo za jedan kod.
- Rešenje: rekonfigurabilan čip (FPGA) koji se reprogramira u runtime-u za
  različite aplikacije/verzije.
- Tipičan sastav aplikacije: 1,000,000 linija kod ukupno, ali samo ~2,000
  linija je "kernel" koji vredi akcelerisati (+20,000 linija softvera treba
  restrukturirati) → CPU dobar za latency/control-intensive kod, DataFlow
  engine dobar za high-throughput repetitivnu obradu velikih količina podataka.
- Gde staviti custom arhitekturu u sistemu: on-chip, koprocesor uz L1/L2 keš,
  preko QPI/HyperTransport, kao memory controller, kao DIMM, na PCIe, unutar
  perifernog uređaja (npr. disk kontroler).
- Bottleneci zavise od aplikacije: memory latency/bandwidth/size, ALU
  resursi/latencija, bus bandwidth.
- FPGA skalira po istoj Murovoj krivoj kao CPU.

### 02 — Programming with MaxCompiler
- MaxCompiler = kompletno razvojno okruženje za Maxeler FPGA akceleratore;
  MaxJ (ekstenzija Jave) opisuje dataflow graf, generiše hardver, host kod u C
  ga koristi.
- Hardver: MaxCard (1 FPGA), MaxNode (1U server, 4x MAX3 kartice + Xeon CPU-ovi,
  PCIe Gen2, 50-80W, 24-48GB RAM), MaxRack (10/20/40U).
- Razvojni tok: identifikuj kod za akceleraciju → napiši MaxCompiler kod →
  simuliraj → build za hardver → integriši sa host kodom → ako ne zadovoljava
  performans, vrati se i transformiši app/arhitekturu.

### 03 — More MaxCompiler Programming
- Brojači (counters) za loop iteration varijable — računaju se direktno na
  FPGA-u umesto da se šalju kao stream (manje I/O, manje data transfera).
- Tri vrste ulaza: stream (novi podatak svaki cycle, O(N) transfer), counter
  (računa se on-chip, bez transfera), compile-time konstanta (statična kroz
  ceo proračun) i scalar input (za vrednosti koje se retko menjaju, bez
  ponovne kompilacije).

### 04 — Number Representations and Arithmetic
- Performans zavisi od broja aritmetičkih jedinica koje stanu na FPGA →
  manja preciznost = više jedinica = veći throughput (accuracy vs. performance
  tradeoff).
- Tipovi reprezentacije: integer (unsigned, two's complement), floating point,
  fixed point, logaritamska reprezentacija, redundantni brojni sistemi
  (signed-digit), residue (modulo) sistemi, decimalni (BCD).
- One's complement vs. two's complement vs. sign-magnitude — prednosti/mane
  (simetrija oko nule, brzina, kompleksnost add/sub).

### 05 — Stream Scheduling
- Svaka operacija u pipeline-u ima latenciju (broj cycle-ova od ulaza do
  izlaza), throughput ostaje 1 vrednost/cycle.
- Problem: podaci stižu u pogrešnom trenutku zbog različitih latencija granaka
  → rešenje je ubacivanje buffera (balansiranje) da se sve sinhronizuje.
- Scheduling algoritam transformiše apstraktni dataflow graf u graf koji daje
  tačan rezultat uzimajući u obzir latencije; optimizuje se za: latenciju,
  količinu buffer-a, površinu (resource sharing). Radi automatski i na
  grafovima sa hiljadama nodova.

### 06 — Loops and Cyclic Graphs
- Klasifikacija petlji po: pristupnom obrascu nizu (stride), loop-carried
  dependency distanci (fiksna = dobro, varijabilna = loše).
- Metrike: odnos računanja i memorijskog pristupa, working set veličina
  (→ custom memory hijerarhija), bottleneck (CPU/memorija/IO).
- Tipovi: proste fiksne petlje (vector add), ugnježdene petlje (counter
  chains, streaming/unrolling), petlje promenljive dužine (konverzija u
  fiksnu dužinu), petlje sa dependency ciklusima (cyclic dataflow grafovi i
  kako iskoristiti pipelining unutar njih).

### 07 — Elementary Functions
- Elementarne funkcije neophodne za: 2D/3D grafiku (trig funkcije), obradu
  slike (gamma), signal processing (FFT), govor, CAD geometriju, fiziku/
  biologiju/hemiju.
- Univerzalna procedura računanja f(x): (1) redukcija argumenta x' = g(x),
  x' u [a,b]; (2) aproksimacija f(g(x)) na tom intervalu (polinomska/
  racionalna/tabelarna/shift-and-add metoda); (3) rekonstrukcija f(x) = h(f(g(x))).
- Primer: sin(x) — redukcija mod π/2, pa racionalna aproksimacija (bez
  rekonstrukcije). Primer: exp(x) — redukcija preko deljenja sa 0.5·ln(2).

---

## Ostali materijali (`maxeler/`)

### MaxelerBelgradeTalkAugust10.pdf — Oskar Mencer, Beograd, avgust 2010
"Vertical Acceleration: From Algorithms to Logic Gates considering Economics
of Computation". Konkretni case study-evi:
- Chevron 3D Finite Difference: Maxeler FPGA 30x brže od 8-core Intel node.
- Angle gathers (Stanford Center for Earth and Environmental Sciences): 48x
  speedup uz custom trace memory system (prefetch trace buffer-a).
- Hardver linija: MaxCard → MaxBox (4 kartice u 1U) → MaxRack.

### flyer.pdf — "Maximum Performance Computing at Exascale"
- Cilj: exascale aplikacije u 3MW do 2018.
- Maxeler DFE ubrzanja: 20-50x u vremenu obrade, >90% manje energije po node-u
  u odnosu na konvencionalni sistem ekvivalentnih performansi.
- 5 ključnih prepreka ka exascale: Power, Programmability, Communication,
  Space, Reliability.

### MaxelerCatalogJuly2013.pdf
Katalog proizvoda/rešenja Maxeler-a (jul 2013) — pregled hardverskih platformi
i softverskog stack-a; korisno za referencu specifikacija/proizvoda ako treba
za domaći.

### RiskAnalyticsBrochure.pdf
Brošura o primeni Maxeler DFE u finansijskoj risk analitici (JPMorgan use
case — vezano za Forbes članak naveden na maxeler.php stranici).

### Maxeler-examples1.ppt, MaxelerEssence.ppt
Tutorial/praktični primeri (Saša & Veljko) i "Essence" pregled — nisu
ekstrahovani u txt (stari .ppt binarni format, python-pptx ne podržava).
Otvoriti direktno u PowerPoint-u ako treba.

---

## "The Ultimate - Long = CMOQ" (indico.global PDF, 202 strane)
Veljkova "duga" verzija prezentacije — uvodi CMOQ (Chem/Molecular/Opto/Quantum,
deo "EnergyFlow" sloja). Počinje istorijskim pregledom:
- Flynn-ova klasifikacija (SISD/SIMD/MISD/MIMD).
- DARPA-in prvi GaAs mikroprocesor (ranih 80-ih, Star Wars/SDI program) —
  GaAs RISC čip cilj 100 MIPS, 10,000 gate-ova; pouka: "mere technological
  change is NOT a solution" zbog off-chip/on-chip delay-a koji vode do
  asimptotskog zasićenja ubrzanja → direktno relevantno za **GaAs** temu
  domaćeg (3+4).
- Dalje strane (nisu detaljno pregledane) — verovatno pokrivaju Opto/Quantum/
  Molecular akceleratore u širem kontekstu DataFlow arhitekture; vredi
  pretražiti `4_The_Ultimate_Long_CMOQ_extracted.txt` po ključnoj reči teme
  koja vam treba (npr. "Quantum", "Opto", "Bio").

---

## Mapiranje materijala → teme domaćih

| Domaći | Tema | Najrelevantniji materijal |
|---|---|---|
| 1+2 | CF multicore / manycore | `The_Ultimate_DataFlow...pptx` (tabela proizvođača CPU/GPU) |
| 3+4 | GaAs / 2+6 | `4_The_Ultimate_Long_CMOQ.pdf` (DARPA GaAs istorija) |
| 5+6 | DF maxDFE / DF googleTPU | Oskar 01-07 (kompletna MaxCompiler teorija), Belgrade Talk, flyer |
| 7+8 | IoT / WSN | (nije pokriveno ovim materijalima — potrebno dodatno istraživanje) |
| 9+10 | Opto / Quantum | `4_The_Ultimate_Long_CMOQ.pdf` (EnergyFlow sloj) |
| 11+12 | Bio / Chem | `4_The_Ultimate_Long_CMOQ.pdf` (EnergyFlow sloj) |

Za IoT/WSN trenutno nema preuzetog materijala sa ovih sajtova — vredi pitati
Veljka/Nikolu za izvor ili pretražiti samostalno.
