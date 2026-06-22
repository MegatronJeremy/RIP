# RIP — Razvoj i primena računarskih akceleratora

Materijali, beleške i kod za predmet **Razvoj i primena računarskih akceleratora**
kod profesora **Veljka Milutinovića** (ETF, master), u okviru
[ETF-Master](https://github.com/MegatronJeremy/ETF-Master) repozitorijuma
(uključen kao git submodule).

## O kursu

Veljko Milutinović drži 6 termina, uvek od 16:15 do 17:15, bez pauze.
Predmet podrazumeva 12 domaćih zadataka koji se rade u parovima i branе se
kao `.pptx` prezentacije (5 min po domaćem), kao i usmeni ispit vezan za
predavanja. Detaljna logistika (datumi odbrane, teme, bodovanje) je u
[`logistika.txt`](logistika.txt).

Teme domaćih, po parovima:

| Termin | Teme |
|---|---|
| 1+2 | CF multicore / CF manycore |
| 3+4 | GaAs / 2+6 |
| 5+6 | DF maxDFE / DF googleTPU |
| 7+8 | IoT / WSN |
| 9+10 | Opto / Quantum |
| 11+12 | Bio / Chem |

Bodovanje: 12 domaćih nosi 48 poena (4 po domaćem: 2 za slajdove + 2 za
priču), usmeni ispit nosi 12 poena, ukupno 60. Svaki domaći mora dobiti
2+ poena za prelaznu ocenu. Detalji u [`logistika.txt`](logistika.txt).

## Sadržaj repozitorijuma

- [`logistika.txt`](logistika.txt) — raspored, datumi odbrane, teme domaćih,
  bodovanje, linkovi do resursa (preneto sa WhatsApp-a).
- [`veljko.txt`](veljko.txt) — lične beleške o formatu slajdova koji
  Veljko voli (formalnost, bullet pointovi, struktura) i pregled urađenih
  tema (matmul, softmax, obrada slike).
- [`materijali/`](materijali) — preuzeta predavanja i prateći materijali:
  - [`materijali/Oskar_Slides/`](materijali/Oskar_Slides) — 7 delova
    teorijskih MaxAcademy predavanja (Oskar Mencer): uvod, MaxCompiler
    programiranje, brojevni sistemi, scheduling, petlje/ciklični grafovi,
    elementarne funkcije.
  - [`materijali/Maxeler/`](materijali/Maxeler) — Maxeler prezentacije,
    case study-evi (Chevron, Stanford), flyer-i, katalog, brošura o risk
    analitici.
  - [`materijali/4_The_Ultimate_Long_CMOQ.pdf`](materijali/4_The_Ultimate_Long_CMOQ.pdf)
    — Veljkova duža prezentacija (CMOQ: Chem/Molecular/Opto/Quantum sloj).
  - [`materijali/INDEX.md`](materijali/INDEX.md) — sažetak ključnih
    poenata iz svakog fajla, sa mapiranjem na teme domaćih zadataka.
  - `*_extracted.txt` fajlovi — sirov tekst izvučen iz odgovarajućih
    pptx/pdf fajlova (za brzu pretragu bez otvaranja originala).
- [`domaci/`](domaci) — domaći zadaci (Prefix Scan prezentacije) i
  [`domaci/Prefix_Scan/`](domaci/Prefix_Scan) — kod i rezultati benčmarka
  (`benchmark.py`, `requirements.txt`, `scan_benchmark.png`).

## Napomena

Za teme **IoT / WSN** (7+8) trenutno nema preuzetog materijala — potrebno je
dodatno istraživanje.
