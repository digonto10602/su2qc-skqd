# Gate H0_2x2 -- the full 2x2 SKQD run, ibm_kingston

**Status: PASS** -- `scripts/gate_H0_2x2.py --stage assemble --counts data/hardware/H0_2x2_ibm_kingston/counts --out H0_2x2`.
Runtime 444 s.  Every number below is computed by the script from the raw counts and `data/hardware/H0_2x2_prep/prereg_84d59cbf9b5973d1.json` and is stored
in `validation/H0_2x2.json`.  Prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage R).

**Owner decision (`data/owner_decision_20261002_run_below_signed_budget.md`):** this run is authorised by the owner's decision of 2026-10-02 to run the full 2x2
SKQD whether or not the signed f >= 0.1 budget is met (Stage T's read of the signed bar on the adopted cell: GO):
"ibm approval is still waiting, have to do with the 600 second budget we have now, replan with the planner, check from arxiv which procedure can decrease the decoherence issue, test with that, if nothing works, start preparing to send the 2x2 circuit anyway to qpus to finish run and see result all the way through to the end, meaning the skqd run for 2x2 plaquettes using 121 s of qpu time."

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on E_R(B_sig), the baselines' percentile or the recall -- they are the result.  Coordinator ruling (2026-10-02) on planner decision P8: the D3''-H0 lift of the seven k = 1 circuits is STRUCK; Stage R is pure rule D3' at the adopted cell's f_pool, which is what the owner named ("121 s").  The planner's prompt file is not edited; the strike enters here (reserve, plan, tests).

## 1. Live

| item | value |
|---|---|
| jobs / status | ['db01pddj371s73dnnqm0', 'db01pdtj371s73dnnqmg', 'db01pe04oijs73e8cl30', 'db01pelj371s73dnnqo0', 'db01peql7guc73cfndc0'] / ['DONE', 'DONE', 'DONE', 'DONE', 'DONE'] |
| usage per job (s) / total | {'db01pddj371s73dnnqm0': 3.0, 'db01pdtj371s73dnnqmg': 3.0, 'db01pe04oijs73e8cl30': 4.0, 'db01pelj371s73dnnqo0': 22.0, 'db01peql7guc73cfndc0': 21.0} / 53.0 |
| preflight estimate (s) / reserve / cap | 41.71489022000006 / 79.5 / 46 |
| fingerprint at prereg / submission / retrieval | `84d59cbf9b5973d1` / `84d59cbf9b5973d1` / `84d59cbf9b5973d1` |
| retrieval diff | None |
| account before / after | 49 s used (551 left) / 102 s used (498 left) |
| options | {'default_shots': 40, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |
| configuration | Stage T cell T3 (f 0.1129, 95 % [0.1058, 0.1203]) |
| shot plan | N4 {'B=0': 13100, 'B=1': 31400}, 133907 coarse shots, estimate 41.71 s |

## 2. Readout

Smallest confusion diagonal 0.9417; survival product 0.8338; live expectation min
0.9525.

## 3. Decoder round trip and random acceptance

0 mismatches over 58 accepted strings; random acceptance
{'B=0': 0.00927734375, 'B=1': 0.0048828125} (gate E2: 0.00927734375 / 0.0048828125).

## 4. Clean fraction (the seven k = 1 circuits)

| circuit | shots | ref hits | garbage exp. | z | f reference [68 %] [95 %] | f mixture [68 %] |
|---|---|---|---|---|---|---|
| B0_ref06_k1 | 267 | 26 | 0.07 | 101.6 | 0.1341 [0.1079, 0.1660] [0.0867, 0.1980] | 0.1276 [0.1124, 0.1415] |
| B0_ref17_k1 | 267 | 25 | 0.07 | 97.7 | 0.1286 [0.1030, 0.1599] [0.0824, 0.1914] | 0.1387 [0.1255, 0.1491] |
| B0_ref21_k1 | 267 | 27 | 0.07 | 105.5 | 0.1390 [0.1123, 0.1712] [0.0906, 0.2037] | 0.1484 [0.1377, 0.1562] |
| B0_ref30_k1 | 267 | 27 | 0.07 | 105.5 | 0.1390 [0.1123, 0.1712] [0.0906, 0.2037] | 0.1284 [0.1178, 0.1365] |
| B0_ref43_k1 | 267 | 21 | 0.07 | 82.0 | 0.1080 [0.0845, 0.1372] [0.0660, 0.1665] | 0.1279 [0.1239, 0.1279] |
| B1_ref07_k1 | 267 | 27 | 0.07 | 105.5 | 0.1384 [0.1118, 0.1705] [0.0903, 0.2028] | 0.1325 [0.1225, 0.1397] |
| B1_ref14_k1 | 267 | 20 | 0.07 | 78.1 | 0.1024 [0.0796, 0.1309] [0.0618, 0.1596] | 0.1013 [0.0904, 0.1096] |

Pooled f = **0.1271** (68 % [0.1174, 0.1375], 95 % [0.1084, 0.1479]); Stage T's adopted cell
T3: 0.1129 (95 % [0.1058, 0.1203]); relative deviation 0.126
(tolerance 0.3).

## 5. Support per sector

| sector | shots | accepted | mu_s | N a / dim | B_all | B_sig | recall B_all | recall B_sig | |S_0.999| |
|---|---|---|---|---|---|---|---|---|---|
| B=0 | 69505 | 9454 | 16.97 | 17.0 | 38/38 | 35/38 | 1.000 | 1.000 | 16 |
| B=1 | 64402 | 7885 | 15.72 | 15.7 | 20/20 | 19/20 | 1.000 | 1.000 | 13 |

k-resolved growth (cumulative over k <= k_max):

| sector | k_max | shots | B_all | B_sig |
|---|---|---|---|---|
| B=0 | 1 | 1335 | 21 | 8 |
| B=0 | 2 | 2670 | 26 | 13 |
| B=0 | 3 | 4005 | 34 | 19 |
| B=0 | 4 | 69505 | 38 | 35 |
| B=1 | 1 | 534 | 9 | 3 |
| B=1 | 2 | 1068 | 13 | 6 |
| B=1 | 3 | 1602 | 16 | 10 |
| B=1 | 4 | 64402 | 20 | 19 |

Per state:

| sector | basis | label | n_s | mu_s | lambda_s (0.7) | z | P(Poisson(mu) >= n) | in B_sig | |<s|Omega>|^2 |  |
|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 3 | (0,0,0,0); (0,0,2,2) | 374 | 16.97 | 167.93 | 86.7 | 0.00e+00 | yes | 1.71e-03 |  |
| B=0 | 5 | (0,0,0,0); (0,2,0,2) | 304 | 16.97 | 132.20 | 69.7 | 1.15e-258 | yes | 1.71e-03 |  |
| B=0 | 6 | (0,0,0,0); (0,2,2,0) | 764 | 16.97 | 474.24 | 181.3 | 0.00e+00 | yes | 8.19e-01 | ref |
| B=0 | 9 | (0,0,0,0); (2,0,0,2) | 169 | 16.97 | 34.95 | 36.9 | 7.21e-105 | yes | 2.04e-05 |  |
| B=0 | 10 | (0,0,0,0); (2,0,2,0) | 391 | 16.97 | 165.08 | 90.8 | 0.00e+00 | yes | 1.71e-03 |  |
| B=0 | 12 | (0,0,0,0); (2,2,0,0) | 443 | 16.97 | 206.82 | 103.4 | 0.00e+00 | yes | 1.71e-03 |  |
| B=0 | 17 | (0,0,0,1); (0,2,1,1) | 634 | 16.97 | 327.01 | 149.8 | 0.00e+00 | yes | 4.08e-02 | ref |
| B=0 | 18 | (0,0,0,1); (2,0,1,1) | 335 | 16.97 | 115.06 | 77.2 | 3.35e-298 | yes | 1.11e-04 |  |
| B=0 | 21 | (0,0,1,0); (0,1,2,1) | 704 | 16.97 | 341.17 | 166.8 | 0.00e+00 | yes | 4.08e-02 | ref |
| B=0 | 22 | (0,0,1,0); (2,1,0,1) | 289 | 16.97 | 99.99 | 66.0 | 5.12e-240 | yes | 1.11e-04 |  |
| B=0 | 25 | (0,0,1,1); (0,1,1,2) | 283 | 16.97 | 153.74 | 64.6 | 1.19e-232 | yes | 9.77e-04 |  |
| B=0 | 26 | (0,0,1,1); (2,1,1,0) | 137 | 16.97 | 35.70 | 29.1 | 2.82e-74 | yes | 1.23e-05 |  |
| B=0 | 29 | (0,1,0,0); (1,1,0,2) | 218 | 16.97 | 85.24 | 48.8 | 1.13e-156 | yes | 1.11e-04 |  |
| B=0 | 30 | (0,1,0,0); (1,1,2,0) | 639 | 16.97 | 339.77 | 151.0 | 0.00e+00 | yes | 4.08e-02 | ref |
| B=0 | 32 | (0,1,0,1); (1,1,1,1) | 368 | 16.97 | 197.04 | 85.2 | 0.00e+00 | yes | 2.23e-03 |  |
| B=0 | 34 | (0,1,1,0); (1,0,2,1) | 308 | 16.97 | 160.68 | 70.6 | 1.08e-263 | yes | 9.77e-04 |  |
| B=0 | 35 | (0,1,1,0); (1,2,0,1) | 67 | 16.97 | 13.64 | 12.1 | 3.80e-20 | yes | 1.23e-05 |  |
| B=0 | 38 | (0,1,1,1); (1,0,1,2) | 139 | 16.97 | 63.99 | 29.6 | 4.22e-76 | yes | 2.69e-05 |  |
| B=0 | 39 | (0,1,1,1); (1,2,1,0) | 76 | 16.97 | 25.93 | 14.3 | 8.25e-26 | yes | 7.81e-05 |  |
| B=0 | 42 | (1,0,0,0); (1,0,1,2) | 186 | 16.97 | 80.14 | 41.0 | 3.19e-122 | yes | 1.11e-04 |  |
| B=0 | 43 | (1,0,0,0); (1,2,1,0) | 563 | 16.97 | 342.76 | 132.6 | 0.00e+00 | yes | 4.08e-02 | ref |
| B=0 | 46 | (1,0,0,1); (1,0,2,1) | 91 | 16.97 | 24.75 | 18.0 | 3.07e-36 | yes | 1.23e-05 |  |
| B=0 | 47 | (1,0,0,1); (1,2,0,1) | 395 | 16.97 | 172.23 | 91.8 | 0.00e+00 | yes | 9.77e-04 |  |
| B=0 | 49 | (1,0,1,0); (1,1,1,1) | 403 | 16.97 | 193.77 | 93.7 | 0.00e+00 | yes | 2.23e-03 |  |
| B=0 | 51 | (1,0,1,1); (1,1,0,2) | 112 | 16.97 | 55.79 | 23.1 | 1.34e-52 | yes | 2.69e-05 |  |
| B=0 | 52 | (1,0,1,1); (1,1,2,0) | 97 | 16.97 | 30.78 | 19.4 | 1.01e-40 | yes | 7.81e-05 |  |
| B=0 | 55 | (1,1,0,0); (0,1,1,2) | 44 | 16.97 | 7.82 | 6.6 | 3.26e-08 | yes | 1.23e-05 |  |
| B=0 | 56 | (1,1,0,0); (2,1,1,0) | 272 | 16.97 | 178.92 | 61.9 | 2.71e-219 | yes | 9.77e-04 |  |
| B=0 | 59 | (1,1,0,1); (0,1,2,1) | 30 | 16.97 | 6.32 | 3.2 | 2.66e-03 |  | 7.81e-05 |  |
| B=0 | 60 | (1,1,0,1); (2,1,0,1) | 171 | 16.97 | 74.49 | 37.4 | 7.13e-107 | yes | 2.69e-05 |  |
| B=0 | 63 | (1,1,1,0); (0,2,1,1) | 55 | 16.97 | 24.12 | 9.2 | 2.06e-13 | yes | 7.81e-05 |  |
| B=0 | 64 | (1,1,1,0); (2,0,1,1) | 161 | 16.97 | 68.11 | 35.0 | 5.93e-97 | yes | 2.69e-05 |  |
| B=0 | 69 | (1,1,1,1); (0,0,2,2) | 28 | 16.97 | 10.32 | 2.7 | 8.64e-03 |  | 2.52e-06 |  |
| B=0 | 71 | (1,1,1,1); (0,2,0,2) | 26 | 16.97 | 10.73 | 2.2 | 2.48e-02 |  | 2.52e-06 |  |
| B=0 | 72 | (1,1,1,1); (0,2,2,0) | 59 | 16.97 | 30.15 | 10.2 | 1.52e-15 | yes | 1.29e-03 |  |
| B=0 | 75 | (1,1,1,1); (2,0,0,2) | 37 | 16.97 | 14.89 | 4.9 | 1.74e-05 | yes | 4.49e-07 |  |
| B=0 | 76 | (1,1,1,1); (2,0,2,0) | 50 | 16.97 | 19.02 | 8.0 | 6.37e-11 | yes | 2.52e-06 |  |
| B=0 | 78 | (1,1,1,1); (2,2,0,0) | 32 | 16.97 | 17.07 | 3.6 | 7.26e-04 | yes | 2.52e-06 |  |
| B=1 | 7 | (0,0,0,0); (0,2,2,2) | 555 | 15.72 | 301.07 | 136.0 | 0.00e+00 | yes | 4.37e-01 | ref |
| B=1 | 11 | (0,0,0,0); (2,0,2,2) | 719 | 15.72 | 302.37 | 177.4 | 0.00e+00 | yes | 4.81e-03 |  |
| B=1 | 13 | (0,0,0,0); (2,2,0,2) | 492 | 15.72 | 237.05 | 120.1 | 0.00e+00 | yes | 4.81e-03 |  |
| B=1 | 14 | (0,0,0,0); (2,2,2,0) | 669 | 15.72 | 376.43 | 164.8 | 0.00e+00 | yes | 4.37e-01 | ref |
| B=1 | 19 | (0,0,0,1); (2,2,1,1) | 826 | 15.72 | 446.77 | 204.3 | 0.00e+00 | yes | 2.71e-02 |  |
| B=1 | 23 | (0,0,1,0); (2,1,2,1) | 1171 | 15.72 | 621.14 | 291.4 | 0.00e+00 | yes | 2.71e-02 |  |
| B=1 | 27 | (0,0,1,1); (2,1,1,2) | 698 | 15.72 | 379.10 | 172.1 | 0.00e+00 | yes | 6.51e-04 |  |
| B=1 | 31 | (0,1,0,0); (1,1,2,2) | 455 | 15.72 | 228.39 | 110.8 | 0.00e+00 | yes | 2.71e-02 |  |
| B=1 | 36 | (0,1,1,0); (1,2,2,1) | 212 | 15.72 | 91.54 | 49.5 | 1.57e-156 | yes | 2.25e-03 |  |
| B=1 | 40 | (0,1,1,1); (1,2,1,2) | 135 | 15.72 | 62.05 | 30.1 | 2.13e-76 | yes | 9.33e-07 |  |
| B=1 | 44 | (1,0,0,0); (1,2,1,2) | 540 | 15.72 | 367.12 | 132.2 | 0.00e+00 | yes | 2.71e-02 |  |
| B=1 | 48 | (1,0,0,1); (1,2,2,1) | 351 | 15.72 | 223.27 | 84.6 | 0.00e+00 | yes | 2.25e-03 |  |
| B=1 | 53 | (1,0,1,1); (1,1,2,2) | 27 | 15.72 | 6.30 | 2.8 | 6.02e-03 |  | 9.33e-07 |  |
| B=1 | 57 | (1,1,0,0); (2,1,1,2) | 218 | 15.72 | 147.78 | 51.0 | 2.36e-163 | yes | 6.51e-04 |  |
| B=1 | 61 | (1,1,0,1); (2,1,2,1) | 176 | 15.72 | 100.83 | 40.4 | 3.21e-117 | yes | 9.33e-07 |  |
| B=1 | 65 | (1,1,1,0); (2,2,1,1) | 191 | 15.72 | 95.96 | 44.2 | 3.02e-133 | yes | 9.33e-07 |  |
| B=1 | 73 | (1,1,1,1); (0,2,2,2) | 80 | 15.72 | 32.76 | 16.2 | 1.36e-30 | yes | 6.70e-04 |  |
| B=1 | 77 | (1,1,1,1); (2,0,2,2) | 115 | 15.72 | 35.83 | 25.0 | 2.35e-58 | yes | 3.17e-06 |  |
| B=1 | 79 | (1,1,1,1); (2,2,0,2) | 131 | 15.72 | 51.22 | 29.1 | 1.11e-72 | yes | 3.17e-06 |  |
| B=1 | 80 | (1,1,1,1); (2,2,2,0) | 124 | 15.72 | 64.85 | 27.3 | 2.65e-66 | yes | 6.70e-04 |  |

## 6. Energies (Ritz basis = set u sector references)

| sector | set | |basis| | E_R | E0 exact | |E_R - E0| | r_H | Weinstein (gap-assumed) | Kato-Temple | Weinstein contains an eigenvalue | closure |
|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | B_all | 38 | -3.6407665507 | -3.6407665507 | 0.000e+00 | 6.140e-15 | [-3.640767, -3.640767] | [-3.640767, -3.640767] | True | 0.000e+00 |
| B=0 | B_sig | 35 | -3.6402188765 | -3.6407665507 | 5.477e-04 | 6.027e-02 | [-3.700489, -3.640219] | [-3.641574, -3.640219] | True | 1.301e-02 |
| B=1 | B_all | 20 | -1.8615880345 | -1.8615880345 | 0.000e+00 | 1.509e-15 | [-1.861588, -1.861588] | [-1.861588, -1.861588] | True | 0.000e+00 |
| B=1 | B_sig | 19 | -1.8615822852 | -1.8615880345 | 5.749e-06 | 5.954e-03 | [-1.867536, -1.861582] | [-1.862424, -1.861582] | True | 1.607e-03 |

Criterion 3 of prompts/07 on B_all: B=0 |E_R - E0| = 0.00e+00 (holds True); B=1 |E_R - E0| = 0.00e+00 (holds True) -- **not a device test** (C3').

## 7. Baselines

| sector | baseline | E_R mean +- std | E_R 2.5-97.5 % | |B| | hardware percentile (E_R <= hardware) |
|---|---|---|---|---|---|
| B=0 | garbage-only (100 seeds 11..110) | -3.640767 +- 0.000000 | [-3.640767, -3.640767] | 38.0 [38, 38] | B_all 100.0 / B_sig 100.0 |
| B=0 | random at |B| = 35 (200 seeds 23..222) | -3.632660 +- 0.006386 | [-3.640356, -3.618549] | 35 | B_sig 5.0 |
| B=1 | garbage-only (100 seeds 11..110) | -1.861588 +- 0.000000 | [-1.861588, -1.861588] | 20.0 [20, 20] | B_all 100.0 / B_sig 100.0 |
| B=1 | random at |B| = 19 (200 seeds 23..222) | -1.854110 +- 0.007941 | [-1.861582, -1.841042] | 19 | B_sig 28.5 |

## 8. C22 saturation

{"B=0": {"N": 69505, "Na_over_dim": 16.968994140625, "saturates_from_noise": true}, "B=1": {"N": 64402, "Na_over_dim": 15.72314453125, "saturates_from_noise": true}} (rule: N a / dim >= 5 fills the sector from accidentally-valid noise alone).

## 9. Honest limits

- Stage R runs under the owner's decision whatever the signed budget says; the signed bar was read only on Stage T's two
  k = 1 circuits, never on the family (k = 2-4 are information); the sectors saturate from accidentally-valid noise at these
  shot counts (C22 above), so E_R(B_all) reproducing E0 is a property of the decoder (gate E2), not of the device; B_sig
  excludes uniform noise but not near-clean false positives (M4.4); the garbage and random baselines are the controls that
  make the number readable.
- Seven k = 1 circuits are not a family-level statement at other k; the k = 2-4 cells' f is information (C6 ruling).
- One calibration content; drift between submission and retrieval is reported, not corrected.

## 10. Criteria

| check | value | criterion | result |
|---|---|---|---|
| R1 preregistration before data (as K1, over all jobs); the owner-decision file exists and is cited | prereg 2026-10-02T14:38:28-06:00 (added 2026-10-02T14:44:13-06:00), first submission 2026-10-02 21:05:55 UTC; fingerprints equal True; retrieval match True; owner file cited True | all hold | PASS |
| R2 every job DONE; usage per job and total recorded; total billed <= the reserve of R.A2; the counts files carry exactly the plan's shots; options record DD off / twirling off; the circuits carry the adopted DD (or none) as preregistered | jobs 5 ['DONE', 'DONE', 'DONE', 'DONE', 'DONE']; usage {'db01pddj371s73dnnqm0': 3.0, 'db01pdtj371s73dnnqmg': 3.0, 'db01pe04oijs73e8cl30': 4.0, 'db01pelj371s73dnnqo0': 22.0, 'db01peql7guc73cfndc0': 21.0} total 53.0 s vs reserve 79.5; shots as planned True; options off True; circuits T3 as preregistered True | all hold | PASS |
| R3 readout: min diagonal >= DIAG_MIN | 0.9417 | >= 0.9 | PASS |
| R4 decoder round trip 0 mismatches; the sectors' random acceptance equals gate E2's exhaustive values (a_B=0 = 0.00927734375, a_B=1 = 0.0048828125) | 0 mismatches over 58 strings; acceptance {'B=0': 0.00927734375, 'B=1': 0.0048828125} | 0 and equal to E2 | PASS |
| R5 C3' per k = 1 circuit: reference hits >= 3 sigma above the garbage expectation; pooled f of the seven k = 1 circuits within F_TOLERANCE (0.30) of Stage T's adopted-cell f_pool | C3' 7/7 (min z 78.1); pooled f 0.1271 [0.1084, 0.1479] vs Stage T 0.1129 [0.1058, 0.1203]: deviation 0.126 | >= 3 sigma each; deviation <= 0.3 | PASS |
| R6 circuits: exactness of all 28 at build, schedule assertions, DD checks (i)-(v), durations; the shot plan reproduces rule D3' | exact True (max |d| 2.6e-14); alap True; DD checks True; durations True; D3' reproduced True | all hold | PASS |
| R7 data.energies, data.support, data.baselines complete with seeds; criterion 3 computed and labelled 'not a device test'; the Weinstein interval contains some exact eigenvalue of the sector | blocks complete; seeds True; criterion 3 B=0 |E_R - E0| 0.00e+00, B=1 |E_R - E0| 0.00e+00 (not a device test); Weinstein contains a sector eigenvalue True | all hold | PASS |
| R8 dry-run gate PASS; pytest -q tests; check_package.py OK | dry run PASS; pytest: 253 passed, 2 skipped, 10 warnings in 432.79s (0:07:12); check_package rc 0 | all pass | PASS |
