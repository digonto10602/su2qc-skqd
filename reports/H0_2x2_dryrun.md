# Gate H0_2x2_dryrun -- the full 2x2 SKQD run, dry run (local Aer on the FakeKingston snapshot at 1000 shots per pub; a path check)

**Status: PASS** -- `scripts/gate_H0_2x2.py --stage assemble --counts data/hardware/H0_2x2_dryrun/counts --dry-run --out H0_2x2_dryrun`.
Runtime 17 s.  Every number below is computed by the script from the raw counts and `data/hardware/H0_2x2_prep/prereg_84d59cbf9b5973d1.json` and is stored
in `validation/H0_2x2_dryrun.json`.  Prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage R).

**Owner decision (`data/owner_decision_20261002_run_below_signed_budget.md`):** this run is authorised by the owner's decision of 2026-10-02 to run the full 2x2
SKQD whether or not the signed f >= 0.1 budget is met (Stage T's read of the signed bar on the adopted cell: GO):
"ibm approval is still waiting, have to do with the 600 second budget we have now, replan with the planner, check from arxiv which procedure can decrease the decoherence issue, test with that, if nothing works, start preparing to send the 2x2 circuit anyway to qpus to finish run and see result all the way through to the end, meaning the skqd run for 2x2 plaquettes using 121 s of qpu time."

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on E_R(B_sig), the baselines' percentile or the recall -- they are the result.  Coordinator ruling (2026-10-02) on planner decision P8: the D3''-H0 lift of the seven k = 1 circuits is STRUCK; Stage R is pure rule D3' at the adopted cell's f_pool, which is what the owner named ("121 s").  The planner's prompt file is not edited; the strike enters here (reserve, plan, tests).

## 1. Live

| item | value |
|---|---|
| jobs / status | ['ca550a1d-4589-43d3-8eba-a530d3bfdd3b', '5ee32d83-0fa6-47d8-a6cb-d975243645cf', '70e72ca3-07e8-4ba4-b659-373085dbc06b'] / ['DONE', 'DONE', 'DONE'] |
| usage per job (s) / total | {'ca550a1d-4589-43d3-8eba-a530d3bfdd3b': 0.0, '5ee32d83-0fa6-47d8-a6cb-d975243645cf': 0.0, '70e72ca3-07e8-4ba4-b659-373085dbc06b': 0.0} / 0.0 |
| preflight estimate (s) / reserve / cap | None / 79.5 / 46 |
| fingerprint at prereg / submission / retrieval | `84d59cbf9b5973d1` / `n/a` / `n/a` |
| retrieval diff | None |
| account before / after | 49 s used (551 left) / None s used (None left) |
| options | {'default_shots': 1000, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |
| configuration | Stage T cell T3 (f 0.1129, 95 % [0.1058, 0.1203]) |
| shot plan | N4 {'B=0': 13100, 'B=1': 31400}, 133907 coarse shots, estimate 41.71 s |

## 2. Readout

Smallest confusion diagonal 0.8360; survival product 0.6996; live expectation min
0.9525.

## 3. Decoder round trip and random acceptance

0 mismatches over 58 accepted strings; random acceptance
{'B=0': 0.00927734375, 'B=1': 0.0048828125} (gate E2: 0.00927734375 / 0.0048828125).

## 4. Clean fraction (the seven k = 1 circuits)

| circuit | shots | ref hits | garbage exp. | z | f reference [68 %] [95 %] | f mixture [68 %] |
|---|---|---|---|---|---|---|
| B0_ref06_k1 | 1000 | 126 | 0.24 | 254.5 | 0.1736 [0.1581, 0.1905] [0.1440, 0.2075] | 0.1813 [0.1724, 0.1897] |
| B0_ref17_k1 | 1000 | 119 | 0.24 | 240.3 | 0.1636 [0.1486, 0.1800] [0.1349, 0.1965] | 0.1674 [0.1607, 0.1733] |
| B0_ref21_k1 | 1000 | 132 | 0.24 | 266.7 | 0.1815 [0.1657, 0.1987] [0.1512, 0.2160] | 0.1848 [0.1775, 0.1914] |
| B0_ref30_k1 | 1000 | 106 | 0.24 | 214.0 | 0.1457 [0.1315, 0.1613] [0.1187, 0.1769] | 0.1623 [0.1549, 0.1689] |
| B0_ref43_k1 | 1000 | 120 | 0.24 | 242.4 | 0.1650 [0.1499, 0.1815] [0.1362, 0.1980] | 0.1684 [0.1610, 0.1751] |
| B1_ref07_k1 | 1000 | 116 | 0.24 | 234.3 | 0.1588 [0.1440, 0.1750] [0.1306, 0.1912] | 0.1621 [0.1556, 0.1679] |
| B1_ref14_k1 | 1000 | 125 | 0.24 | 252.5 | 0.1711 [0.1558, 0.1879] [0.1418, 0.2046] | 0.1724 [0.1655, 0.1786] |

Pooled f = **0.1656** (68 % [0.1599, 0.1715], 95 % [0.1544, 0.1774]); Stage T's adopted cell
T3: 0.1129 (95 % [0.1058, 0.1203]); relative deviation 0.467
(tolerance 0.3).

## 5. Support per sector

| sector | shots | accepted | mu_s | N a / dim | B_all | B_sig | recall B_all | recall B_sig | |S_0.999| |
|---|---|---|---|---|---|---|---|---|---|
| B=0 | 20000 | 3485 | 4.88 | 4.9 | 38/38 | 29/38 | 1.000 | 1.000 | 16 |
| B=1 | 8000 | 1288 | 1.95 | 2.0 | 20/20 | 17/20 | 1.000 | 1.000 | 13 |

k-resolved growth (cumulative over k <= k_max):

| sector | k_max | shots | B_all | B_sig |
|---|---|---|---|---|
| B=0 | 1 | 5000 | 32 | 20 |
| B=0 | 2 | 10000 | 37 | 24 |
| B=0 | 3 | 15000 | 38 | 27 |
| B=0 | 4 | 20000 | 38 | 29 |
| B=1 | 1 | 2000 | 15 | 8 |
| B=1 | 2 | 4000 | 19 | 10 |
| B=1 | 3 | 6000 | 20 | 14 |
| B=1 | 4 | 8000 | 20 | 17 |

Per state:

| sector | basis | label | n_s | mu_s | lambda_s (0.7) | z | P(Poisson(mu) >= n) | in B_sig | |<s|Omega>|^2 |  |
|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 3 | (0,0,0,0); (0,0,2,2) | 114 | 4.88 | 167.93 | 49.4 | 1.00e-110 | yes | 1.71e-03 |  |
| B=0 | 5 | (0,0,0,0); (0,2,0,2) | 95 | 4.88 | 132.20 | 40.8 | 2.05e-85 | yes | 1.71e-03 |  |
| B=0 | 6 | (0,0,0,0); (0,2,2,0) | 460 | 4.88 | 474.24 | 206.0 | 0.00e+00 | yes | 8.19e-01 | ref |
| B=0 | 9 | (0,0,0,0); (2,0,0,2) | 33 | 4.88 | 34.95 | 12.7 | 5.42e-17 | yes | 2.04e-05 |  |
| B=0 | 10 | (0,0,0,0); (2,0,2,0) | 98 | 4.88 | 165.08 | 42.1 | 2.61e-89 | yes | 1.71e-03 |  |
| B=0 | 12 | (0,0,0,0); (2,2,0,0) | 104 | 4.88 | 206.82 | 44.9 | 3.23e-97 | yes | 1.71e-03 |  |
| B=0 | 17 | (0,0,0,1); (0,2,1,1) | 350 | 4.88 | 327.01 | 156.2 | 0.00e+00 | yes | 4.08e-02 | ref |
| B=0 | 18 | (0,0,0,1); (2,0,1,1) | 64 | 4.88 | 115.06 | 26.8 | 7.67e-48 | yes | 1.11e-04 |  |
| B=0 | 21 | (0,0,1,0); (0,1,2,1) | 387 | 4.88 | 341.17 | 172.9 | 0.00e+00 | yes | 4.08e-02 | ref |
| B=0 | 22 | (0,0,1,0); (2,1,0,1) | 59 | 4.88 | 99.99 | 24.5 | 2.55e-42 | yes | 1.11e-04 |  |
| B=0 | 25 | (0,0,1,1); (0,1,1,2) | 62 | 4.88 | 153.74 | 25.8 | 1.30e-45 | yes | 9.77e-04 |  |
| B=0 | 26 | (0,0,1,1); (2,1,1,0) | 19 | 4.88 | 35.70 | 6.4 | 9.97e-07 | yes | 1.23e-05 |  |
| B=0 | 29 | (0,1,0,0); (1,1,0,2) | 47 | 4.88 | 85.24 | 19.1 | 7.60e-30 | yes | 1.11e-04 |  |
| B=0 | 30 | (0,1,0,0); (1,1,2,0) | 371 | 4.88 | 339.77 | 165.7 | 0.00e+00 | yes | 4.08e-02 | ref |
| B=0 | 32 | (0,1,0,1); (1,1,1,1) | 115 | 4.88 | 197.04 | 49.8 | 4.26e-112 | yes | 2.23e-03 |  |
| B=0 | 34 | (0,1,1,0); (1,0,2,1) | 105 | 4.88 | 160.68 | 45.3 | 1.50e-98 | yes | 9.77e-04 |  |
| B=0 | 35 | (0,1,1,0); (1,2,0,1) | 13 | 4.88 | 13.64 | 3.7 | 1.65e-03 |  | 1.23e-05 |  |
| B=0 | 38 | (0,1,1,1); (1,0,1,2) | 20 | 4.88 | 63.99 | 6.8 | 2.40e-07 | yes | 2.69e-05 |  |
| B=0 | 39 | (0,1,1,1); (1,2,1,0) | 19 | 4.88 | 25.93 | 6.4 | 9.97e-07 | yes | 7.81e-05 |  |
| B=0 | 42 | (1,0,0,0); (1,0,1,2) | 59 | 4.88 | 80.14 | 24.5 | 2.55e-42 | yes | 1.11e-04 |  |
| B=0 | 43 | (1,0,0,0); (1,2,1,0) | 367 | 4.88 | 342.76 | 163.9 | 0.00e+00 | yes | 4.08e-02 | ref |
| B=0 | 46 | (1,0,0,1); (1,0,2,1) | 13 | 4.88 | 24.75 | 3.7 | 1.65e-03 |  | 1.23e-05 |  |
| B=0 | 47 | (1,0,0,1); (1,2,0,1) | 84 | 4.88 | 172.23 | 35.8 | 1.71e-71 | yes | 9.77e-04 |  |
| B=0 | 49 | (1,0,1,0); (1,1,1,1) | 119 | 4.88 | 193.77 | 51.6 | 1.27e-117 | yes | 2.23e-03 |  |
| B=0 | 51 | (1,0,1,1); (1,1,0,2) | 25 | 4.88 | 55.79 | 9.1 | 9.89e-11 | yes | 2.69e-05 |  |
| B=0 | 52 | (1,0,1,1); (1,1,2,0) | 27 | 4.88 | 30.78 | 10.0 | 3.30e-12 | yes | 7.81e-05 |  |
| B=0 | 55 | (1,1,0,0); (0,1,1,2) | 8 | 4.88 | 7.82 | 1.4 | 1.21e-01 |  | 1.23e-05 |  |
| B=0 | 56 | (1,1,0,0); (2,1,1,0) | 98 | 4.88 | 178.92 | 42.1 | 2.61e-89 | yes | 9.77e-04 |  |
| B=0 | 59 | (1,1,0,1); (0,1,2,1) | 9 | 4.88 | 6.32 | 1.9 | 6.07e-02 |  | 7.81e-05 |  |
| B=0 | 60 | (1,1,0,1); (2,1,0,1) | 33 | 4.88 | 74.49 | 12.7 | 5.42e-17 | yes | 2.69e-05 |  |
| B=0 | 63 | (1,1,1,0); (0,2,1,1) | 25 | 4.88 | 24.12 | 9.1 | 9.89e-11 | yes | 7.81e-05 |  |
| B=0 | 64 | (1,1,1,0); (2,0,1,1) | 28 | 4.88 | 68.11 | 10.5 | 5.72e-13 | yes | 2.69e-05 |  |
| B=0 | 69 | (1,1,1,1); (0,0,2,2) | 3 | 4.88 | 10.32 | -0.9 | 8.65e-01 |  | 2.52e-06 |  |
| B=0 | 71 | (1,1,1,1); (0,2,0,2) | 4 | 4.88 | 10.73 | -0.4 | 7.18e-01 |  | 2.52e-06 |  |
| B=0 | 72 | (1,1,1,1); (0,2,2,0) | 27 | 4.88 | 30.15 | 10.0 | 3.30e-12 | yes | 1.29e-03 |  |
| B=0 | 75 | (1,1,1,1); (2,0,0,2) | 5 | 4.88 | 14.89 | 0.1 | 5.39e-01 |  | 4.49e-07 |  |
| B=0 | 76 | (1,1,1,1); (2,0,2,0) | 7 | 4.88 | 19.02 | 1.0 | 2.21e-01 |  | 2.52e-06 |  |
| B=0 | 78 | (1,1,1,1); (2,2,0,0) | 9 | 4.88 | 17.07 | 1.9 | 6.07e-02 |  | 2.52e-06 |  |
| B=1 | 7 | (0,0,0,0); (0,2,2,2) | 265 | 1.95 | 301.07 | 188.2 | 0.00e+00 | yes | 4.37e-01 | ref |
| B=1 | 11 | (0,0,0,0); (2,0,2,2) | 78 | 1.95 | 302.37 | 54.4 | 6.10e-94 | yes | 4.81e-03 |  |
| B=1 | 13 | (0,0,0,0); (2,2,0,2) | 84 | 1.95 | 237.05 | 58.7 | 1.16e-103 | yes | 4.81e-03 |  |
| B=1 | 14 | (0,0,0,0); (2,2,2,0) | 287 | 1.95 | 376.43 | 204.0 | 0.00e+00 | yes | 4.37e-01 | ref |
| B=1 | 19 | (0,0,0,1); (2,2,1,1) | 94 | 1.95 | 446.77 | 65.9 | 2.84e-120 | yes | 2.71e-02 |  |
| B=1 | 23 | (0,0,1,0); (2,1,2,1) | 133 | 1.95 | 621.14 | 93.8 | 4.50e-189 | yes | 2.71e-02 |  |
| B=1 | 27 | (0,0,1,1); (2,1,1,2) | 48 | 1.95 | 379.10 | 32.9 | 1.07e-48 | yes | 6.51e-04 |  |
| B=1 | 31 | (0,1,0,0); (1,1,2,2) | 60 | 1.95 | 228.39 | 41.5 | 4.89e-66 | yes | 2.71e-02 |  |
| B=1 | 36 | (0,1,1,0); (1,2,2,1) | 14 | 1.95 | 91.54 | 8.6 | 2.20e-08 | yes | 2.25e-03 |  |
| B=1 | 40 | (0,1,1,1); (1,2,1,2) | 9 | 1.95 | 62.05 | 5.0 | 2.00e-04 | yes | 9.33e-07 |  |
| B=1 | 44 | (1,0,0,0); (1,2,1,2) | 90 | 1.95 | 367.12 | 63.0 | 1.43e-113 | yes | 2.71e-02 |  |
| B=1 | 48 | (1,0,0,1); (1,2,2,1) | 35 | 1.95 | 223.27 | 23.6 | 2.17e-31 | yes | 2.25e-03 |  |
| B=1 | 53 | (1,0,1,1); (1,1,2,2) | 5 | 1.95 | 6.30 | 2.2 | 4.85e-02 |  | 9.33e-07 |  |
| B=1 | 57 | (1,1,0,0); (2,1,1,2) | 19 | 1.95 | 147.78 | 12.2 | 4.31e-13 | yes | 6.51e-04 |  |
| B=1 | 61 | (1,1,0,1); (2,1,2,1) | 15 | 1.95 | 100.83 | 9.3 | 2.83e-09 | yes | 9.33e-07 |  |
| B=1 | 65 | (1,1,1,0); (2,2,1,1) | 10 | 1.95 | 95.96 | 5.8 | 3.82e-05 | yes | 9.33e-07 |  |
| B=1 | 73 | (1,1,1,1); (0,2,2,2) | 12 | 1.95 | 32.76 | 7.2 | 1.07e-06 | yes | 6.70e-04 |  |
| B=1 | 77 | (1,1,1,1); (2,0,2,2) | 7 | 1.95 | 35.83 | 3.6 | 4.00e-03 |  | 3.17e-06 |  |
| B=1 | 79 | (1,1,1,1); (2,2,0,2) | 7 | 1.95 | 51.22 | 3.6 | 4.00e-03 |  | 3.17e-06 |  |
| B=1 | 80 | (1,1,1,1); (2,2,2,0) | 16 | 1.95 | 64.85 | 10.1 | 3.43e-10 | yes | 6.70e-04 |  |

## 6. Energies (Ritz basis = set u sector references)

| sector | set | |basis| | E_R | E0 exact | |E_R - E0| | r_H | Weinstein (gap-assumed) | Kato-Temple | Weinstein contains an eigenvalue | closure |
|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | B_all | 38 | -3.6407665507 | -3.6407665507 | 0.000e+00 | 6.140e-15 | [-3.640767, -3.640767] | [-3.640767, -3.640767] | True | 0.000e+00 |
| B=0 | B_sig | 29 | -3.6399869398 | -3.6407665507 | 7.796e-04 | 7.051e-02 | [-3.710502, -3.639987] | [-3.641841, -3.639987] | True | 1.525e-02 |
| B=1 | B_all | 20 | -1.8615880345 | -1.8615880345 | 0.000e+00 | 1.509e-15 | [-1.861588, -1.861588] | [-1.861588, -1.861588] | True | 0.000e+00 |
| B=1 | B_sig | 17 | -1.8615221008 | -1.8615880345 | 6.593e-05 | 2.458e-02 | [-1.886099, -1.861522] | [-1.875892, -1.861522] | True | 5.267e-03 |

Criterion 3 of prompts/07 on B_all: B=0 |E_R - E0| = 0.00e+00 (holds True); B=1 |E_R - E0| = 0.00e+00 (holds True) -- **not a device test** (C3').

## 7. Baselines

| sector | baseline | E_R mean +- std | E_R 2.5-97.5 % | |B| | hardware percentile (E_R <= hardware) |
|---|---|---|---|---|---|
| B=0 | garbage-only (100 seeds 11..110) | -3.640030 +- 0.002910 | [-3.640767, -3.629518] | 37.7 [36, 38] | B_all 82.0 / B_sig 92.0 |
| B=0 | random at |B| = 29 (200 seeds 23..222) | -3.617951 +- 0.009808 | [-3.633806, -3.598748] | 29 | B_sig 0.0 |
| B=1 | garbage-only (100 seeds 11..110) | -1.827516 +- 0.051895 | [-1.861588, -1.679474] | 17.3 [14, 20] | B_all 6.0 / B_sig 15.0 |
| B=1 | random at |B| = 17 (200 seeds 23..222) | -1.829282 +- 0.043489 | [-1.861547, -1.683279] | 17 | B_sig 3.5 |

## 8. C22 saturation

{"B=0": {"N": 20000, "Na_over_dim": 4.8828125, "saturates_from_noise": false}, "B=1": {"N": 8000, "Na_over_dim": 1.953125, "saturates_from_noise": false}} (rule: N a / dim >= 5 fills the sector from accidentally-valid noise alone).

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
| R1 preregistration before data (as K1, over all jobs); the owner-decision file exists and is cited | n/a (dry run); owner file cited True | device run only | PASS |
| R2 (dry run form: the counts carry the dry run's 1000 shots; the plan's shots are checked by the preflight) | counts at 1000: True; circuits carry cell T3: True | all hold | PASS |
| R3 readout (dry-run form, prompts/21a: within 3 sigma of the snapshot's readout model) | ok True; min diagonal 0.8360 (information); live expectation min 0.9525 | all within 3 sigma | PASS |
| R4 decoder round trip 0 mismatches; the sectors' random acceptance equals gate E2's exhaustive values (a_B=0 = 0.00927734375, a_B=1 = 0.0048828125) | 0 mismatches over 58 strings; acceptance {'B=0': 0.00927734375, 'B=1': 0.0048828125} | 0 and equal to E2 | PASS |
| R5 (dry-run form: C3' only; the consistency with Stage T's device f is evaluated on device counts) | C3' 7/7; pooled f 0.1656 vs Stage T 0.1129 (information) | >= 3 sigma each | PASS |
| R6 circuits: exactness of all 28 at build, schedule assertions, DD checks (i)-(v), durations; the shot plan reproduces rule D3' | exact True (max |d| 2.6e-14); alap True; DD checks True; durations True; D3' reproduced True | all hold | PASS |
| R7 data.energies, data.support, data.baselines complete with seeds; criterion 3 computed and labelled 'not a device test'; the Weinstein interval contains some exact eigenvalue of the sector | blocks complete; seeds True; criterion 3 B=0 |E_R - E0| 0.00e+00, B=1 |E_R - E0| 0.00e+00 (not a device test); Weinstein contains a sector eigenvalue True | all hold | PASS |
| R8 pytest / check_package (dry run: run before the device assembly) | n/a (--skip-tests) | - | PASS |
