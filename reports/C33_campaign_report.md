# 2x3 four-class campaign: matrix, S3-quota merges and the comparison with every earlier 2x3 result

**Status: FAIL** — `python scripts/campaign33.py --stage assemble`; prompt prompts/33 (A7, section 6), prompts/33f R3.

## Campaign matrix

| token | status | scenario | variant | sector | f_hit | f_hat_ideal | recall S999 | E_R - E0 | s/shot | node-hours |
|---|---|---|---|---|---|---|---|---|---|---|
| C1_IDEAL | PASS | None | None | None | None | None | None | None | 3.338e-05 | 0.006206 |
| C2_CAL | PASS | None | None | None | None | None | None | None | 1.84 | 0.1261 |
| C2_GATE | pending | None | None | None | None | None | None | None | None | None |
| C2_ECHO | pending | None | None | None | None | None | None | None | None | None |
| C2_STAR | pending | None | None | None | None | None | None | None | None | None |
| C2_XY4 | pending | None | None | None | None | None | None | None | None | None |
| C2_COH | pending | None | None | None | None | None | None | None | None | None |
| C3_AER | PASS | None | None | None | None | None | None | None | 4.946e-05 | 0.004098 |
| C3_LE | pending | None | None | None | None | None | None | None | None | None |
| C3_SEL | pending | None | None | None | None | None | None | None | None | None |
| C4_FCELLS_A | FAIL | E1 | NAT-O0 | None | 0.2312 | 0.2074 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E2 | NAT-O0 | None | 0.2675 | 0.2399 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E3 | NAT-O0 | None | 0.1136 | 0.1018 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E4 | NAT-O0 | None | 0.2552 | 0.2288 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E5a | NAT-O0 | None | 0.2353 | 0.211 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E5b | NAT-O0 | None | 0.2442 | 0.219 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E5c | NAT-O0 | None | 0.2162 | 0.1939 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E1 | NAT-O1 | None | 0.2552 | 0.2288 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E2 | NAT-O1 | None | 0.2675 | 0.2399 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_A | FAIL | E3 | NAT-O1 | None | 0.1136 | 0.1018 | None | None | 0.07955 | 0.1611 |
| C4_FCELLS_B | PASS | E6a | NAT-O0 | None | 0.5274 | 0.473 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6b | NAT-O0 | None | 0.06772 | 0.06073 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6c | NAT-O0 | None | 0.008208 | 0.007361 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.05 | NAT-O0 | None | 0.1095 | 0.09815 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.07 | NAT-O0 | None | 0.1594 | 0.1429 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.10 | NAT-O0 | None | 0.1751 | 0.157 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.15 | NAT-O0 | None | 0.26 | 0.2331 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6a | NAT-O1 | None | 0.5028 | 0.4509 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6b | NAT-O1 | None | 0.06567 | 0.05889 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6c | NAT-O1 | None | 0.006156 | 0.00552 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.05 | NAT-O1 | None | 0.1108 | 0.09938 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.07 | NAT-O1 | None | 0.1402 | 0.1258 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.10 | NAT-O1 | None | 0.1888 | 0.1693 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.15 | NAT-O1 | None | 0.2387 | 0.2141 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6a | NAT-O2 | None | 0.5069 | 0.4546 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6b | NAT-O2 | None | 0.05541 | 0.04969 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6c | NAT-O2 | None | 0.009576 | 0.008588 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.05 | NAT-O2 | None | 0.1019 | 0.09141 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.07 | NAT-O2 | None | 0.1416 | 0.127 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.10 | NAT-O2 | None | 0.1724 | 0.1546 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.15 | NAT-O2 | None | 0.2442 | 0.219 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6a | NAT-O3 | None | 0.4748 | 0.4257 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6b | NAT-O3 | None | 0.06499 | 0.05828 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6c | NAT-O3 | None | 0.003419 | 0.003066 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.05 | NAT-O3 | None | 0.1211 | 0.1086 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.07 | NAT-O3 | None | 0.1307 | 0.1172 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.10 | NAT-O3 | None | 0.184 | 0.165 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.15 | NAT-O3 | None | 0.2216 | 0.1988 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6a | NAT-O4 | None | 0.5021 | 0.4503 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6b | NAT-O4 | None | 0.0602 | 0.05398 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E6c | NAT-O4 | None | 0.009576 | 0.008588 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.05 | NAT-O4 | None | 0.1033 | 0.09263 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.07 | NAT-O4 | None | 0.1313 | 0.1178 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.10 | NAT-O4 | None | 0.171 | 0.1534 | None | None | 0.02444 | 0.1296 |
| C4_FCELLS_B | PASS | E7_0.15 | NAT-O4 | None | 0.2442 | 0.219 | None | None | 0.02444 | 0.1296 |
| C4_F1_B0 | PASS | E1 | NAT-O0 | B=0 | 0.2544 | 0.2281 | 1 | 0.000329 | 0.02769 | 0.1241 |
| C4_F1_B1 | PASS | E1 | NAT-O0 | B=1 | 0.2428 | 0.2177 | 1 | 8.996e-05 | 0.02362 | 0.05952 |
| C4_F2_B0 | PASS | E2 | NAT-O0 | B=0 | 0.2707 | 0.2427 | 1 | 0.000311 | 0.02509 | 0.1124 |
| C4_F2_B1 | PASS | E2 | NAT-O0 | B=1 | 0.2719 | 0.2438 | 1 | 4.503e-05 | 0.02626 | 0.06578 |
| C4_F3_B0 | pending | None | None | None | None | None | None | None | None | None |
| C4_F3_B1 | pending | None | None | None | None | None | None | None | None | None |
| C4_F4_B0a | FAIL | E7_0.10 | NAT-O0 | B=0 | 0.1927 | 0.1728 | 1 | 7.257e-05 | 0.02634 | 0.09686 |
| C4_F4_B0b | FAIL | E7_0.10 | NAT-O0 | B=0 | 0.1825 | 0.1636 | 1 | 6.864e-05 | 0.02632 | 0.09641 |
| C4_F4_B1a | PASS | E7_0.10 | NAT-O0 | B=1 | 0.1846 | 0.1655 | 1 | 0.0001357 | 0.02602 | 0.09381 |
| C4_F4_B1b | PASS | E7_0.10 | NAT-O0 | B=1 | 0.1783 | 0.1599 | 1 | 0.0002363 | 0.02613 | 0.09445 |
| C4_F5_B0 | PASS | E7_0.07 | NAT-O0 | B=0 | 0.1445 | 0.1296 | 1 | 0.0002427 | 0.02734 | 0.1544 |
| C4_F5_B1 | PASS | E7_0.07 | NAT-O0 | B=1 | 0.1302 | 0.1167 | 1 | 0.000108 | 0.02637 | 0.09532 |
| C4_F6_B0 | pending | None | None | None | None | None | None | None | None | None |
| C4_F6_B1 | pending | None | None | None | None | None | None | None | None | None |
| C4_F7_B0 | PASS | E1 | NAT-O2 | B=0 | 0.2483 | 0.2226 | 1 | 0.0003349 | 0.02157 | 0.04515 |
| C4_F7_B1 | PASS | E1 | NAT-O2 | B=1 | 0.2622 | 0.2351 | 1 | 0.0001944 | 0.01876 | 0.04806 |
| C4_F8_B0a | PASS | E8 | IR-L3-RZZ | B=0 | 0.131 | 0.1175 | 1 | 0.000122 | 0.01987 | 0.0746 |
| C4_F8_B0b | PASS | E8 | IR-L3-RZZ | B=0 | 0.1364 | 0.1223 | 1 | 5.765e-05 | 0.01854 | 0.07149 |
| C4_F8_B1a | PASS | E8 | IR-L3-RZZ | B=1 | 0.1358 | 0.1218 | 1 | 0.0002709 | 0.01873 | 0.06795 |
| C4_F8_B1b | PASS | E8 | IR-L3-RZZ | B=1 | 0.1356 | 0.1216 | 1 | 0.0001535 | 0.01895 | 0.06975 |
| C4_CF | FAIL | None | None | None | None | None | None | None | 0.4755 | 0.1667 |

## How the non-PASS and pending tokens are read (prompts/33f R3; labels only, no status changed)

| token | status | reading |
|---|---|---|
| C2_CAL | PASS | calibration (prompts/33a step B); its production decision is superseded (prompts/33d R5): the class-2 decision of record is data/campaign33/c2_representation_decision.json (prompts/33f R2) |
| C2_GATE | pending | after the maintenance (prompts/33f R3), RM |
| C2_ECHO | pending | after the maintenance (prompts/33f R3), RM |
| C2_STAR | pending | after the maintenance (prompts/33f R3), RM |
| C2_XY4 | pending | requested after prompts/33f (RM at 100 %, no reference arm) |
| C2_COH | pending | after the maintenance (prompts/33f R3), RM |
| C4_F3_B0 | pending | deferred (prompts/33b section 2; owner's call) |
| C4_F3_B1 | pending | deferred (prompts/33b section 2; owner's call) |
| C4_F6_B0 | pending | deferred (prompts/33b section 2; owner's call) |
| C4_F6_B1 | pending | deferred (prompts/33b section 2; owner's call) |
| C4_CF | FAIL | accepted as recorded (prompts/33c R4: S6 only, P16 / P17 PASS) |
| C2_KCHK | FAIL | calibration (prompts/33d R3, 33e R2); FAIL on S3 / S6 as harvested and not edited; decision in data/campaign33/c2_representation_decision.json (prompts/33f) |

## Split runs, merged at assembly (prompts/33a D4)

| run | status | kind | shots | |B_all| | E_R - E0 | certificate | width | E0 inside | recall S999 | CV1-CV5 | failing criteria |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F1_B1 | PASS | plan | 67600 | 348 | 8.996e-05 | weinstein | 0.02625 | True | 1 | CV1:ok CV2:ok CV3:ok CV4:ok CV5:ok | - |
| F2_B1 | PASS | plan | 67600 | 358 | 4.503e-05 | weinstein | 0.01801 | True | 1 | CV1:ok CV2:ok CV3:- CV4:ok CV5:ok | - |
| F4_B0a | FAIL | s3quota | 95712 | 434 | 7.257e-05 | kato_temple_exact_E1 | 0.0002699 | True | 1 | - | every part JSON present and full (S6 of ; the concatenated chunks tile the plan an |
| F4_B0b | FAIL | s3quota | 95712 | 436 | 6.864e-05 | kato_temple_exact_E1 | 0.0002569 | True | 1 | - | every part JSON present and full (S6 of ; the concatenated chunks tile the plan an |
| F4_B1a | PASS | s3quota | 99996 | 340 | 0.0001357 | weinstein | 0.03451 | True | 1 | - | - |
| F4_B1b | PASS | s3quota | 99996 | 333 | 0.0002363 | weinstein | 0.04312 | True | 1 | - | - |
| F5_B1 | PASS | plan | 99000 | 376 | 0.000108 | weinstein | 0.02791 | True | 1 | CV1:ok CV2:ok CV3:ok CV4:ok CV5:ok | - |
| F7_B1 | PASS | plan | 67600 | 353 | 0.0001944 | weinstein | 0.03703 | True | 1 | CV1:ok CV2:ok CV3:- CV4:ok CV5:ok | - |
| F8_B0a | PASS | s3quota | 100000 | 458 | 0.000122 | kato_temple_exact_E1 | 0.0004931 | True | 1 | - | - |
| F8_B0b | PASS | s3quota | 100000 | 461 | 5.765e-05 | kato_temple_exact_E1 | 0.000207 | True | 1 | - | - |
| F8_B1a | PASS | s3quota | 99996 | 326 | 0.0002709 | weinstein | 0.04627 | True | 1 | - | - |
| F8_B1b | PASS | s3quota | 99996 | 335 | 0.0001535 | weinstein | 0.03512 | True | 1 | - | - |

## S3-quota merges (a + b halves)

| run|sector | status | shots | recall S999 | E0 in Weinstein | P15 |
|---|---|---|---|---|---|
| F4|B=0 | merged | 191424 | 1 | True | None |
| F4|B=1 | merged | 199992 | 1 | True | None |
| F8|B=0 | merged | 200000 | 1 | True | True |
| F8|B=1 | merged | 199992 | 1 | True | True |

## Comparison with the earlier 2x3 results (prompts/33 section 6)

| old result | redo | status | difference (verdict) |
|---|---|---|---|
| S1 production B=0 f=0.1 (proxy noise, 2e5/sector) | C4_F4_* (merged a+b) | merged | recall: no_old_uncertainty (Delta 0); B_size: no_old_uncertainty (Delta 158); E_R_minus_E0: no_old_uncertainty (Delta -0.0002943); weinstein_width: no_old_uncertainty (Delta -0.03922) |
| S1 production B=1 f=0.1 (proxy noise, 2e5/sector) | C4_F4_* (merged a+b) | merged | recall: no_old_uncertainty (Delta 0.01053); B_size: no_old_uncertainty (Delta 125); E_R_minus_E0: no_old_uncertainty (Delta -0.0009331); weinstein_width: no_old_uncertainty (Delta -0.06163) |
| S3 (job 58771538): E8 on IR-L3-RZZ, B=0, 32 x 100, seed 11 | C4_FCELLS_B s3_redo | done | yield: consistent (Delta -0.01219) |
| S3 criterion (never evaluated) | C4_F8_* merged | merged | - |
| S3_smoke: B=1, 24 shots, recall 0.0737 | C4_F8_B1* | superseded | - |
| L4_p2_1e-3: Aer noise-model sampling at 2x2 (S3 preparation) | not redone | not_applicable | - |
| L4_p2_3e-3: Aer noise-model sampling at 2x2 (S3 preparation) | not redone | not_applicable | - |
| Q0P A6 dry run: 64 hits / 280, f_hit 0.2502 | C4_FCELLS_A E1 x NAT-O0 (k = 1 circuits) | done | f_hit: consistent (Delta -0.01896) |
| CF_traj pooled r(1e-3) 1.0693 [1.0285934561902321, 1.1151352098004452], r_nc 1.1151 | C4_CF (K = 2000 per arm) | done | pooled_r: consistent (Delta -0.01437) |
| CV_2x3_plan / Q0P_2x3_plan P3 B=0 f=0.10 (proxy at 0.7 f, 3 seeds) | C4_F5_B0 | done | recall_S999: inconsistent (Delta 0.03876); CV1_dE: inconsistent (Delta -0.004255) |
| CV_2x3_plan / Q0P_2x3_plan P3 B=1 f=0.10 (proxy at 0.7 f, 3 seeds) | C4_F5_B1 | done | recall_S999: inconsistent (Delta 0.04561); CV1_dE: not_comparable (Delta None) |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_GATE | pending | - |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_ECHO | pending | - |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_STAR | pending | - |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_XY4 | pending | - |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_COH | pending | - |
| C3_AER (Aer, noiseless, NAT-O0) | C3_LE | pending | - |
| C3_AER (Aer, noiseless, NAT-O0) | C3_SEL | pending | - |
| S2D 2x3 declared-model f 0.0534 (virtual Rz 0.0817) | C4_FCELLS_B E7 cells (and E8 on IR-L3-RZZ in the S3 redo) | done | - |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| every token JSON present | 23 of 34 | 34 of 34 | FAIL |
| every present token PASS (tokens dropped by data/campaign33/engines.json excluded) | {'C4_FCELLS_A': 'FAIL', 'C4_CF': 'FAIL', 'C2_KCHK': 'FAIL', 'C33_F4_B0a': 'FAIL', 'C33_F4_B0b': 'FAIL'} | no FAIL | FAIL |
| comparison table generated (section 6 rows) | 19 | >= 10 rows | PASS |
| P15 gate-S3 criterion B=0: recall S999 >= 0.9 at 2e5 and E0 inside Weinstein | [1.0, True] | >= 0.9 and inside | PASS |
| P15 gate-S3 criterion B=1: recall S999 >= 0.9 at 2e5 and E0 inside Weinstein | [1.0, True] | >= 0.9 and inside | PASS |

Every number above is read from validation/*.json and data/*.json by `src/skqd/campaign33/assemble.py` and stored in `validation/C33_campaign.json`.
