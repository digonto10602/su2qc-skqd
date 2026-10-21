| term | baseline IR CX | operator-exact best (proposal) | input-specific best, range over 15 references |
|---|---|---|---|
| hop0 | 278 | 140 (bframed_sw) | 0–14 (rpkg) |
| hop1 | 54 | 52 (full_sw) | 0–38 (rpkg) |
| hop2 | 258 | 110 (bframed_sw) | 14–44 (rpkg, rpkg_sw) |
| hop3 | 1548 | 256 (bframed_sw) | 6–44 (rpkg, rpkg_sw) |
| hop4 | 390 | 166 (bframed_sw) | 52–112 (bframed_sw, framed_sw, rpkg, rpkg_sw) |
| hop5 | 542 | 178 (bframed_sw) | 40–58 (rpkg_sw) |
| hop6 | 260 | 134 (bframed_sw) | 30–44 (rpkg, rpkg_sw) |
| hop7 | 390 | 166 (bframed_sw) | 68–108 (bframed_sw, framed_sw, rpkg, rpkg_sw) |
| hop8 | 244 | 116 (framed_sw) | 30–56 (framed_sw, rpkg_sw) |
| hop9 | 54 | 52 (full_sw) | 52–52 (rpkg_sw) |
| plaq0 | 228 | 88 (cfg) | 54–84 (cfg_sw, cfg_t_sw) |
| plaq1 | 66468 | 220 (cfg_sw) | 152–208 (cfg_sw, cfg_t_sw) |
| plaq2 | 806 | 96 (cfg) | 96–96 (cfg) |
| sum | 71520 | 1774 | 594–958 (term-wise extremes) |

| iteration | proposals available | class A term sum | class B term sum per reference (min / mean / max) |
|---|---|---|---|
| it1 | cf1, cf2, pkg, rpkg | 4588 | 734 / 888.0 / 1044 |
| it2 | cf1, cf2, cfg, cfg_t, pkg, rpkg | 4440 | 636 / 762.1 / 934 |
| it3 | cf1, cf2, cf2_sw, cfg, cfg_sw, cfg_t, cfg_t_sw, full_sw, pkg, rpkg, rpkg_sw | 3074 | 606 / 716.5 / 846 |
| it4 | cf1, cf2, cf2_sw, cfg, cfg_sw, cfg_t, cfg_t_sw, framed_sw, full_sw, pkg, rpkg, rpkg_sw | 2734 | 606 / 715.5 / 844 |
| it5 | bframed, bframed_sw, cf1, cf2, cf2_sw, cfg, cfg_sw, cfg_t, cfg_t_sw, framed_sw, full_sw, pkg, rpkg, rpkg_sw | 1774 | 606 / 713.6 / 828 |

input: 75/75 pass; ZZ 582–800 (mean 683.5, 104.7x below 71 548); depth_2q 292–469; max dev 3.14e-14; max |leak| 6.88e-14; max direct leak 9.75e-30; max l2 4.94e-14; max prune bound 8.48e-14; max certified dev 1.16e-13; max certified leak 7.67e-27

| circuit (input) | level | ZZ | 2q depth | PhasedX | Q1L | rounding bound B | f H1-1 | f H2-1 | f H2-2 | f Helios-1 |
|---|---|---|---|---|---|---|---|---|---|---|
| B0_ref102_k1 | 0 | 660 | 349 | 1760 | True | 1.4e-14 | 0.479 | 0.455 | 0.536 | 0.556 |
| B0_ref102_k1 | 2 | 629 | 330 | 750 | not applicable (level 2 rewrites gates; unverified) | – | 0.502 | 0.480 | 0.566 | 0.587 |
| B1_ref230_k1 | 0 | 582 | 292 | 1564 | True | 1.0e-14 | 0.518 | 0.497 | 0.575 | 0.594 |
| B1_ref230_k1 | 2 | 560 | 279 | 662 | not applicable (level 2 rewrites gates; unverified) | – | 0.538 | 0.518 | 0.601 | 0.621 |
| B0_ref345_k4 | 0 | 800 | 469 | 2168 | True | 3.9e-14 | 0.415 | 0.387 | 0.472 | 0.491 |
| B0_ref345_k4 | 2 | 775 | 451 | 899 | not applicable (level 2 rewrites gates; unverified) | – | 0.435 | 0.407 | 0.499 | 0.521 |
| B0_ref1338_k5 | 0 | 762 | 428 | 2058 | True | 4.2e-15 | 0.431 | 0.404 | 0.488 | 0.508 |
| B0_ref1338_k5 | 2 | 737 | 412 | 857 | not applicable (level 2 rewrites gates; unverified) | – | 0.452 | 0.425 | 0.516 | 0.537 |

f with the package's memory model (ESTIMATE, t_round low/mid/high), input:
  B0_ref102_k1 level 0: H2-2 0.532/0.526/0.499 (rounds 349, qubits 56); Helios-1 0.531/0.504/0.376 (rounds 349, qubits 98); H1-1 0.472/0.463/0.419 (rounds 349, qubits 20); H2-1 0.449/0.441/0.403 (rounds 349, qubits 56)
  B0_ref102_k1 level 2: H2-2 0.561/0.556/0.528 (rounds 330, qubits 56); Helios-1 0.563/0.535/0.405 (rounds 330, qubits 98); H1-1 0.495/0.487/0.443 (rounds 330, qubits 20); H2-1 0.474/0.466/0.428 (rounds 330, qubits 56)
  B1_ref230_k1 level 0: H2-2 0.571/0.566/0.541 (rounds 292, qubits 56); Helios-1 0.573/0.548/0.429 (rounds 292, qubits 98); H1-1 0.512/0.504/0.464 (rounds 292, qubits 20); H2-1 0.492/0.485/0.450 (rounds 292, qubits 56)
  B1_ref230_k1 level 2: H2-2 0.597/0.592/0.567 (rounds 279, qubits 56); Helios-1 0.600/0.575/0.455 (rounds 279, qubits 98); H1-1 0.532/0.524/0.484 (rounds 279, qubits 20); H2-1 0.513/0.506/0.471 (rounds 279, qubits 56)
  B0_ref345_k4 level 0: H2-2 0.467/0.461/0.428 (rounds 469, qubits 56); Helios-1 0.463/0.431/0.291 (rounds 469, qubits 98); H1-1 0.407/0.397/0.347 (rounds 469, qubits 20); H2-1 0.380/0.372/0.329 (rounds 469, qubits 56)
  B0_ref345_k4 level 2: H2-2 0.494/0.488/0.455 (rounds 451, qubits 56); Helios-1 0.491/0.459/0.314 (rounds 451, qubits 98); H1-1 0.426/0.417/0.366 (rounds 451, qubits 20); H2-1 0.400/0.392/0.349 (rounds 451, qubits 56)
  B0_ref1338_k5 level 0: H2-2 0.484/0.478/0.447 (rounds 428, qubits 56); Helios-1 0.481/0.451/0.315 (rounds 428, qubits 98); H1-1 0.423/0.414/0.367 (rounds 428, qubits 20); H2-1 0.398/0.390/0.349 (rounds 428, qubits 56)
  B0_ref1338_k5 level 2: H2-2 0.511/0.505/0.474 (rounds 412, qubits 56); Helios-1 0.510/0.479/0.339 (rounds 412, qubits 98); H1-1 0.444/0.434/0.386 (rounds 412, qubits 20); H2-1 0.418/0.410/0.369 (rounds 412, qubits 56)
A1 input: 975 checks, worst dev 1.05e-14, worst leak 6.20e-31

operator: 75/75 pass; ZZ 1736–1740 (mean 1739.2, 41.1x below 71 548); depth_2q 1275–1280; max dev 5.84e-14; max |leak| 1.20e-13; max direct leak 4.50e-29; max l2 6.61e-14; max prune bound 9.82e-14; max certified dev 1.54e-13; max certified leak 1.06e-26

| circuit (operator) | level | ZZ | 2q depth | PhasedX | Q1L | rounding bound B | f H1-1 | f H2-1 | f H2-2 | f Helios-1 |
|---|---|---|---|---|---|---|---|---|---|---|
| B0_ref102_k1 | 0 | 1740 | 1280 | 4846 | True | 3.9e-14 | 0.159 | 0.131 | 0.201 | 0.216 |
| B0_ref102_k1 | 2 | 1725 | 1278 | 1858 | not applicable (level 2 rewrites gates; unverified) | – | 0.170 | 0.141 | 0.221 | 0.239 |
| B1_ref230_k1 | 0 | 1740 | 1280 | 4847 | True | 3.1e-14 | 0.159 | 0.131 | 0.201 | 0.216 |
| B1_ref230_k1 | 2 | 1725 | 1278 | 1861 | not applicable (level 2 rewrites gates; unverified) | – | 0.170 | 0.141 | 0.221 | 0.239 |
| B0_ref345_k4 | 0 | 1738 | 1278 | 4841 | True | 1.4e-13 | 0.159 | 0.131 | 0.201 | 0.216 |
| B0_ref345_k4 | 2 | 1724 | 1277 | 1862 | not applicable (level 2 rewrites gates; unverified) | – | 0.170 | 0.141 | 0.221 | 0.239 |
| B0_ref1338_k5 | 0 | 1738 | 1278 | 4841 | True | 1.9e-14 | 0.159 | 0.131 | 0.201 | 0.216 |
| B0_ref1338_k5 | 2 | 1724 | 1277 | 1859 | not applicable (level 2 rewrites gates; unverified) | – | 0.170 | 0.141 | 0.221 | 0.239 |

f with the package's memory model (ESTIMATE, t_round low/mid/high), operator:
  B0_ref102_k1 level 0: H2-2 0.195/0.188/0.154 (rounds 1280, qubits 56); Helios-1 0.183/0.151/0.051 (rounds 1280, qubits 98); H1-1 0.150/0.141/0.098 (rounds 1280, qubits 20); H2-1 0.124/0.117/0.084 (rounds 1280, qubits 56)
  B0_ref102_k1 level 2: H2-2 0.214/0.207/0.169 (rounds 1278, qubits 56); Helios-1 0.203/0.167/0.057 (rounds 1278, qubits 98); H1-1 0.161/0.151/0.105 (rounds 1278, qubits 20); H2-1 0.134/0.126/0.090 (rounds 1278, qubits 56)
  B1_ref230_k1 level 0: H2-2 0.195/0.188/0.154 (rounds 1280, qubits 56); Helios-1 0.183/0.151/0.051 (rounds 1280, qubits 98); H1-1 0.150/0.141/0.098 (rounds 1280, qubits 20); H2-1 0.124/0.117/0.084 (rounds 1280, qubits 56)
  B1_ref230_k1 level 2: H2-2 0.214/0.207/0.169 (rounds 1278, qubits 56); Helios-1 0.203/0.167/0.057 (rounds 1278, qubits 98); H1-1 0.161/0.151/0.105 (rounds 1278, qubits 20); H2-1 0.134/0.126/0.090 (rounds 1278, qubits 56)
  B0_ref345_k4 level 0: H2-2 0.195/0.188/0.154 (rounds 1278, qubits 56); Helios-1 0.184/0.151/0.052 (rounds 1278, qubits 98); H1-1 0.151/0.141/0.098 (rounds 1278, qubits 20); H2-1 0.125/0.117/0.084 (rounds 1278, qubits 56)
  B0_ref345_k4 level 2: H2-2 0.214/0.207/0.170 (rounds 1277, qubits 56); Helios-1 0.203/0.167/0.057 (rounds 1277, qubits 98); H1-1 0.161/0.151/0.105 (rounds 1277, qubits 20); H2-1 0.134/0.126/0.091 (rounds 1277, qubits 56)
  B0_ref1338_k5 level 0: H2-2 0.195/0.188/0.154 (rounds 1278, qubits 56); Helios-1 0.184/0.151/0.052 (rounds 1278, qubits 98); H1-1 0.151/0.141/0.098 (rounds 1278, qubits 20); H2-1 0.125/0.117/0.084 (rounds 1278, qubits 56)
  B0_ref1338_k5 level 2: H2-2 0.214/0.207/0.170 (rounds 1277, qubits 56); Helios-1 0.203/0.167/0.057 (rounds 1277, qubits 98); H1-1 0.161/0.151/0.105 (rounds 1277, qubits 20); H2-1 0.134/0.126/0.091 (rounds 1277, qubits 56)
A1 operator: 130 checks, worst dev 1.01e-14, worst leak 1.37e-29
