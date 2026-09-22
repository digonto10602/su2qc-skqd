# Gate H0_diag — the H0 diagnostic session on ibm_fez

**Status: FAIL** — `scripts/gate_H0_diag.py --prereg data/hardware/H0_diag_prep/idle_model_a44b6ac02709b471.json --out H0_diag`.
Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 4d1e8f6, 2026-09-22 14:46:44 MDT.  Runtime 1 s.  Total QPU usage of the session
**15.0 s** (cap 40 s).

Preregistration `data/hardware/H0_diag_prep/idle_model_a44b6ac02709b471.json` (written 2026-09-22 14:42:06 MDT at commit `9cfe3ec`) on the
calibration fingerprint **`a44b6ac02709b471307d9427a2bf0161f0064ba827ddf158610ca8451624c157`**
(ibm_fez, 2026-09-22T08:00:30-06:00).  The decision rule and
both predictions were fixed before any of these counts existed.

## 1. The decision

| | value |
|---|---|
| J1 accepted N1 of 2000 | **35** |
| preregistered H_A (idle relaxation, options off) | 30.8 +- 5.5 |
| preregistered H_B (the options were the cause) | 374.5 +- 17.4 |
| garbage floor (a = 0.00928) | 18.6 |
| rule | N1 = accepted shots of the canary pub of J1: N1 <= 100 rejects H_B, N1 >= 250 confirms H_B, 100 < N1 < 250 is inconclusive (prompts/19 D5 C3) |
| **outcome** | **H_B rejected (the options are not the cause; the idle term is)** |

Ratios between the cells of the factorial: J2_over_J1 = 0.771, J3_over_J1 = 0.714, J4_over_J2 = 0.630.

## 2. The four canary pubs

| job | DD | twirling | shots | accepted | yield | f from yield | distinct strings | distinct states | reference string seen | rejections | mixture c | chi-square (2 dof) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J1 | off | off | 2000 | 35 | 0.0175 | 0.0101 | 1421 | 19 | 2 | {'flag': 1246, 'link': 678, 'sector': 41, 'unknown': 0} | 0.0083 | 40.93 |
| J2 | XY4 | off | 2000 | 27 | 0.0135 | 0.0052 | 1556 | 18 | 1 | {'flag': 1327, 'link': 608, 'sector': 38, 'unknown': 0} | 0.0043 | 14.29 |
| J3 | off | on (active-accum) | 2000 | 25 | 0.0125 | 0.0040 | 1590 | 19 | 1 | {'flag': 1356, 'link': 599, 'sector': 20, 'unknown': 0} | 0.0033 | 0.24 |
| J4 | XY4 | on (active-accum) | 2000 | 17 | 0.0085 | -0.0010 | 1560 | 12 | 0 | {'flag': 1367, 'link': 599, 'sector': 17, 'unknown': 0} | -0.0008 | 1.00 |

## 3. Jobs

| job | job id(s) | status | usage (s) | calibration fingerprint | prereg match |
|---|---|---|---|---|---|
| J1 | dapegkcak42c73cierv0 | DONE | 5.0 | a44b6ac02709b471 | True |
| J2 | dapeh3318flc739m51e0 | DONE | 4.0 | a44b6ac02709b471 | True |
| J3 | dapeh7ac505c73ci2o60 | DONE | 3.0 | a44b6ac02709b471 | True |
| J4 | dapehb4ak42c73cietig | DONE | 3.0 | a44b6ac02709b471 | True |

## 4. Windowed T1 test (`diag_patch1_t1w`)

| job | physical qubit | raw P(1) | P(1) readout-corrected | P(1) predicted | T1 measured (us) | T1 record (us) | rate ratio | in band |
|---|---|---|---|---|---|---|---|---|
| J1 | 117 | 0.7395 | 0.7588 | 0.7629 | 157.7 | 160.8 | 1.02 | yes |
| J1 | 122 | 0.7090 | 0.7200 | 0.7040 | 132.5 | 124.0 | 0.94 | yes |
| J1 | 123 | 0.6345 | 0.6440 | 0.7606 | 98.9 | 159.0 | 1.61 | yes |
| J1 | 124 | 0.5480 | 0.5511 | 0.5844 | 73.0 | 81.0 | 1.11 | yes |
| J1 | 125 | 0.6885 | 0.6936 | 0.7475 | 119.0 | 149.6 | 1.26 | yes |
| J1 | 136 | 0.5235 | 0.5285 | 0.5453 | 68.2 | 71.8 | 1.05 | yes |
| J1 | 141 | 0.6110 | 0.6304 | 0.7308 | 94.3 | 138.8 | 1.47 | yes |
| J1 | 142 | 0.7745 | 0.7847 | 0.7503 | 179.5 | 151.5 | 0.84 | yes |
| J1 | 143 | 0.6815 | 0.6854 | 0.7498 | 115.2 | 151.2 | 1.31 | yes |
| J1 | 144 | 0.5735 | 0.5769 | 0.7595 | 79.1 | 158.2 | 2.00 | yes |
| J1 | 145 | 0.5195 | 0.5266 | 0.7562 | 67.9 | 155.7 | 2.29 | no |
| J1 | 146 | 0.7420 | 0.7463 | 0.7104 | 148.7 | 127.3 | 0.86 | yes |
| J2 | 117 | 0.2570 | 0.2573 | 0.7629 | 32.1 | 160.8 | 5.02 | no |
| J2 | 122 | 0.4565 | 0.4625 | 0.7040 | 56.4 | 124.0 | 2.20 | no |
| J2 | 123 | 0.3465 | 0.3489 | 0.7606 | 41.3 | 159.0 | 3.85 | no |
| J2 | 124 | 0.7500 | 0.7556 | 0.5844 | 155.3 | 81.0 | 0.52 | yes |
| J2 | 125 | 0.4625 | 0.4593 | 0.7475 | 55.9 | 149.6 | 2.67 | no |
| J2 | 136 | 0.7270 | 0.7353 | 0.5453 | 141.5 | 71.8 | 0.51 | yes |
| J2 | 141 | 0.4450 | 0.4558 | 0.7308 | 55.4 | 138.8 | 2.51 | no |
| J2 | 142 | 0.7925 | 0.8029 | 0.7503 | 198.3 | 151.5 | 0.76 | yes |
| J2 | 143 | 0.4650 | 0.4664 | 0.7498 | 57.1 | 151.2 | 2.65 | no |
| J2 | 144 | 0.3810 | 0.3828 | 0.7595 | 45.3 | 158.2 | 3.49 | no |
| J2 | 145 | 0.7620 | 0.7773 | 0.7562 | 172.7 | 155.7 | 0.90 | yes |
| J2 | 146 | 0.6950 | 0.6988 | 0.7104 | 121.5 | 127.3 | 1.05 | yes |

## 5. Windowed Ramsey test (`diag_patch1_ramw`)

| job | physical qubit | raw P(0) | P(0) readout-corrected | P(0) bound from the record | T2* measured (us) | T2* upper bound (us) | T2 record (us) | under the bound |
|---|---|---|---|---|---|---|---|---|
| J1 | 117 | 0.7735 | 0.7744 | 0.8946 | 72.5 | 87.2 | 183.9 | yes |
| J1 | 122 | 0.6555 | 0.6517 | 0.7227 | 36.5 | 43.6 | 53.8 | yes |
| J1 | 123 | 0.4910 | 0.4846 | 0.8528 | - | 13.3 | 124.8 | yes |
| J1 | 124 | 0.5450 | 0.5430 | 0.8263 | 17.7 | 23.2 | 101.9 | yes |
| J1 | 125 | 0.4430 | 0.4427 | 0.7113 | - | - | 50.5 | yes |
| J1 | 136 | 0.6510 | 0.6489 | 0.8039 | 35.9 | 42.9 | 87.4 | yes |
| J1 | 141 | 0.3815 | 0.3617 | 0.8343 | - | - | 108.1 | yes |
| J1 | 142 | 0.5530 | 0.5480 | 0.9243 | 18.6 | 24.1 | 265.1 | yes |
| J1 | 143 | 0.5300 | 0.5286 | 0.8432 | 15.2 | 20.9 | 115.6 | yes |
| J1 | 144 | 0.4465 | 0.4433 | 0.8981 | - | - | 190.9 | yes |
| J1 | 145 | 0.4915 | 0.4848 | 0.8585 | - | 13.4 | 130.8 | yes |
| J1 | 146 | 0.5540 | 0.5528 | 0.5330 | 19.4 | 24.8 | 16.0 | yes |
| J2 | 117 | 0.5535 | 0.5457 | 0.8946 | 18.2 | 23.8 | 183.9 | yes |
| J2 | 122 | 0.5935 | 0.5885 | 0.7227 | 25.1 | 30.9 | 53.8 | yes |
| J2 | 123 | 0.6325 | 0.6296 | 0.8528 | 32.2 | 38.8 | 124.8 | yes |
| J2 | 124 | 0.7940 | 0.7950 | 0.8263 | 82.5 | 99.2 | 101.9 | yes |
| J2 | 125 | 0.7400 | 0.7506 | 0.7113 | 63.0 | 75.6 | 50.5 | no |
| J2 | 136 | 0.7150 | 0.7139 | 0.8039 | 51.3 | 60.9 | 87.4 | yes |
| J2 | 141 | 0.6030 | 0.5946 | 0.8343 | 26.1 | 32.2 | 108.1 | yes |
| J2 | 142 | 0.8080 | 0.8070 | 0.9243 | 89.2 | 107.7 | 265.1 | yes |
| J2 | 143 | 0.6700 | 0.6702 | 0.8432 | 40.4 | 48.0 | 115.6 | yes |
| J2 | 144 | 0.4510 | 0.4478 | 0.8981 | - | - | 190.9 | yes |
| J2 | 145 | 0.5900 | 0.5866 | 0.8585 | 24.8 | 30.6 | 130.8 | yes |
| J2 | 146 | 0.6930 | 0.6933 | 0.5330 | 45.8 | 54.4 | 16.0 | no |

## 6. Idle-aware post-diction with the measured coherence times

| job | S_T1 | S_T2 | f predicted | yield predicted | yield measured | measured/predicted clean yield | within a factor 3 |
|---|---|---|---|---|---|---|---|
| J1 | 0.942 | 6.574 | 1.145e-04 | 0.00937 | 0.01750 | 88.585 | no |
| J2 | 1.414 | 4.766 | 4.355e-04 | 0.00963 | 0.01350 | 11.960 | no |

## 7. Readout

Smallest confusion diagonal of patch 1 in J1: 0.9625
(criterion >= 0.9).
Qubit 123: measured error 0.01200 against the record 0.00586, ratio 2.05 (information, not a criterion).

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| C1 every job DONE with usage recorded, each <= 30 s, total <= 40 s (4 job directory/ies: J1 5.0 s, J2 4.0 s, J3 3.0 s, J4 3.0 s) | 15 | per job <= 30, total <= 40 | PASS |
| C2 decoder round trip over the accepted strings of 4 canary pub(s) (68 distinct strings) | 0 mismatch(es) | 0 | PASS |
| C3 decisive J1 count: N1 = 35 of 2000 against the preregistered 31 (H_A) and 374 (H_B) -- H_B rejected (the options are not the cause; the idle term is) | 35 | <= 100 or >= 250 | PASS |
| C4a t1w (J1): per-qubit decay rate 1/T1_measured within [0.5, 2.0] x 1/T1_record | 11 of 12 | >= 10 of 12 | PASS |
| C4b ramw (J1): P(0) <= (1 + e^-T/T2_record)/2 + 3 sigma_binomial | 12 of 12 | >= 10 of 12 | PASS |
| C5 J1: the idle-aware post-diction with the measured T1/T2 predicts a clean yield 0.00009 against the measured 0.00822 | 88.585 | within a factor 3 | FAIL |
| C5 J2: the idle-aware post-diction with the measured T1/T2 predicts a clean yield 0.00035 against the measured 0.00422 | 11.96 | within a factor 3 | FAIL |
| C6 readout confusion of patch 1 at 2000 shots (J1): smallest diagonal element | 0.9625 | >= 0.9 | PASS |

Every number above is computed by `scripts/gate_H0_diag.py` from the raw counts of the job directories
and from `data/hardware/H0_diag_prep/idle_model_a44b6ac02709b471.json`, and is stored in `validation/H0_diag.json`.  The counts files are never modified.
