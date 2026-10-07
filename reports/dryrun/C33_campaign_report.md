# DRY RUN skeleton: 2x3 four-class campaign: matrix, S3-quota merges and the comparison with every earlier 2x3 result

**Status: PASS** — `python scripts/campaign33.py --stage assemble --dry-run`; prompt prompts/33 (A7, section 6).

> **DRY RUN SKELETON** — assembled from the laptop dry-run JSONs (validation/dryrun/), every number is a reduced-size path check, not a campaign result.

## Campaign matrix

| token | status | scenario | variant | sector | f_hit | f_hat_ideal | recall S999 | E_R - E0 | s/shot | node-hours |
|---|---|---|---|---|---|---|---|---|---|---|
| C1_IDEAL | PASS | None | None | None | None | None | None | None | 0.3915 | None |
| C2_CAL | PASS | None | None | None | None | None | None | None | None | None |
| C2_GATE | PASS | I-GATE | IBM-U | None | None | None | None | None | 72.56 | None |
| C2_ECHO | PASS | I-ECHO | IBM-T0 | None | None | None | None | None | 107.8 | None |
| C2_STAR | PASS | I-STAR | IBM-T0 | None | None | None | None | None | 81.46 | None |
| C2_XY4 | PASS | I-XY4 | IBM-T3 | None | None | None | None | None | 95.52 | None |
| C2_XY4 | PASS | I-XY4 | IBM-T3 | None | None | None | None | None | 95.52 | None |
| C2_COH | PASS | I-COH | IBM-T0 | None | None | None | None | None | 97.68 | None |
| C3_AER | PASS | None | None | None | None | None | None | None | 0.3738 | None |
| C3_LE | PASS | None | None | None | None | None | None | None | 55.22 | None |
| C3_SEL | FAIL | None | None | None | None | None | None | None | None | None |
| C4_FCELLS_A | PASS | E1 | NAT-O0 | None | 0.2736 | 0.2454 | None | None | 10.43 | None |
| C4_FCELLS_B | PASS | E6a | NAT-O0 | None | 0.6841 | 0.6135 | None | None | 15.75 | None |
| C4_F1_B0 | PASS | E1 | NAT-O0 | B=0 | -1.035e-06 | -9.279e-07 | 0.1163 | 0.1884 | 6.456 | None |
| C4_F1_B1 | PASS | E1 | NAT-O0 | B=1 | 0.1827 | 0.1638 | 0.08421 | 0.5199 | 13.11 | None |
| C4_F2_B0 | PASS | E2 | NAT-O0 | B=0 | 0.1808 | 0.1622 | 0.09302 | 0.2047 | 12.33 | None |
| C4_F2_B1 | PASS | E2 | NAT-O0 | B=1 | 0.1827 | 0.1638 | 0.06316 | 0.6678 | 10.98 | None |
| C4_F3_B0 | PASS | E3 | NAT-O0 | B=0 | 0.1808 | 0.1622 | 0.09302 | 0.2047 | 21.38 | None |
| C4_F3_B1 | PASS | E3 | NAT-O0 | B=1 | -1.045e-06 | -9.375e-07 | 0.03158 | 0.8261 | 26.81 | None |
| C4_F4_B0a | PASS | E7_0.10 | NAT-O0 | B=0 | 0.2712 | 0.2432 | 0.1163 | 0.1972 | 14.77 | None |
| C4_F4_B0b | PASS | E7_0.10 | NAT-O0 | B=0 | -1.035e-06 | -9.279e-07 | 0.09302 | 0.2047 | 14.76 | None |
| C4_F4_B1a | PASS | E7_0.10 | NAT-O0 | B=1 | 0.2741 | 0.2458 | 0.05263 | 0.8261 | 18.48 | None |
| C4_F4_B1b | PASS | E7_0.10 | NAT-O0 | B=1 | 0.137 | 0.1229 | 0.07368 | 0.6678 | 16.74 | None |
| C4_F5_B0 | PASS | E7_0.07 | NAT-O0 | B=0 | 0.3617 | 0.3243 | 0.1047 | 0.1967 | 10.65 | None |
| C4_F5_B1 | PASS | E7_0.07 | NAT-O0 | B=1 | -1.045e-06 | -9.375e-07 | 0.06316 | 0.5231 | 6.986 | None |
| C4_F6_B0 | PASS | E5b | NAT-O0 | B=0 | -1.035e-06 | -9.279e-07 | 0.1163 | 0.1894 | 26.08 | None |
| C4_F6_B1 | PASS | E5b | NAT-O0 | B=1 | -1.045e-06 | -9.375e-07 | 0.04211 | 0.8261 | 26.07 | None |
| C4_F7_B0 | PASS | E1 | NAT-O2 | B=0 | 0.3617 | 0.3243 | 0.1279 | 0.1888 | 6.959 | None |
| C4_F7_B1 | PASS | E1 | NAT-O2 | B=1 | -1.045e-06 | -9.375e-07 | 0.05263 | 0.6678 | 10.4 | None |
| C4_F8_B0a | PASS | E8 | IR-L3-RZZ | B=0 | 0.3391 | 0.304 | 0.1047 | 0.2047 | 7.335 | None |
| C4_F8_B0b | PASS | E8 | IR-L3-RZZ | B=0 | -1.035e-06 | -9.279e-07 | 0.1047 | 0.2047 | 11.7 | None |
| C4_F8_B1a | PASS | E8 | IR-L3-RZZ | B=1 | 0.137 | 0.1229 | 0.04211 | 0.6678 | 14.39 | None |
| C4_F8_B1b | PASS | E8 | IR-L3-RZZ | B=1 | 0.137 | 0.1229 | 0.05263 | 0.8157 | 14.43 | None |
| C4_CF | PASS | None | None | None | None | None | None | None | 9.434 | None |

## S3-quota merges (a + b halves)

| run|sector | status | shots | recall S999 | E0 in Weinstein | P15 |
|---|---|---|---|---|---|
| F4|B=0 | merged | 32 | 0.1163 | True | None |
| F4|B=1 | merged | 32 | 0.09474 | True | None |
| F8|B=0 | merged | 48 | 0.1163 | True | False |
| F8|B=1 | merged | 32 | 0.06316 | True | False |

## Comparison with the earlier 2x3 results (prompts/33 section 6)

| old result | redo | status | difference (verdict) |
|---|---|---|---|
| S1 production B=0 f=0.1 (proxy noise, 2e5/sector) | C4_F4_* (merged a+b) | merged | recall: no_old_uncertainty (Delta -0.8837); B_size: no_old_uncertainty (Delta -336); E_R_minus_E0: no_old_uncertainty (Delta 0.1969); weinstein_width: no_old_uncertainty (Delta 0.9554) |
| S1 production B=1 f=0.1 (proxy noise, 2e5/sector) | C4_F4_* (merged a+b) | merged | recall: no_old_uncertainty (Delta -0.8947); B_size: no_old_uncertainty (Delta -244); E_R_minus_E0: no_old_uncertainty (Delta 0.6668); weinstein_width: no_old_uncertainty (Delta 1.373) |
| S3 (job 58771538): E8 on IR-L3-RZZ, B=0, 32 x 100, seed 11 | C4_FCELLS_B s3_redo | done | yield: consistent (Delta -0.2172) |
| S3 criterion (never evaluated) | C4_F8_* merged | merged | - |
| S3_smoke: B=1, 24 shots, recall 0.0737 | C4_F8_B1* | superseded | - |
| L4_p2_1e-3: Aer noise-model sampling at 2x2 (S3 preparation) | not redone | not_applicable | - |
| L4_p2_3e-3: Aer noise-model sampling at 2x2 (S3 preparation) | not redone | not_applicable | - |
| Q0P A6 dry run: 64 hits / 280, f_hit 0.2502 | C4_FCELLS_A E1 x NAT-O0 (k = 1 circuits) | done | f_hit: consistent (Delta 0.02346) |
| CF_traj pooled r(1e-3) 1.0693 [1.0285934561902321, 1.1151352098004452], r_nc 1.1151 | C4_CF (K = 2000 per arm) | done | pooled_r: tension (Delta -0.07343) |
| CV_2x3_plan / Q0P_2x3_plan P3 B=0 f=0.10 (proxy at 0.7 f, 3 seeds) | C4_F5_B0 | done | recall_S999: inconsistent (Delta -0.8566); CV1_dE: not_comparable (Delta None) |
| CV_2x3_plan / Q0P_2x3_plan P3 B=1 f=0.10 (proxy at 0.7 f, 3 seeds) | C4_F5_B1 | done | recall_S999: inconsistent (Delta -0.8912); CV1_dE: inconsistent (Delta -0.0014) |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_GATE | done | - |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_ECHO | done | - |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_STAR | done | - |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_XY4 | done | - |
| K1 measured 0 / 0 hits, 58 / 45 accepted of 1e5; K0/K1 analytic predictions | C2_COH | done | - |
| C3_AER (Aer, noiseless, NAT-O0) | C3_LE | done | - |
| C3_AER (Aer, noiseless, NAT-O0) | C3_SEL | pending | - |
| S2D 2x3 declared-model f 0.0534 (virtual Rz 0.0817) | C4_FCELLS_B E7 cells (and E8 on IR-L3-RZZ in the S3 redo) | done | - |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| every token JSON present | 33 of 33 | 33 of 33 | PASS |
| every present token PASS (tokens dropped by data/campaign33/engines.json excluded) | {'C3_SEL': 'DROPPED'} | no FAIL | PASS |
| comparison table generated (section 6 rows) | 19 | >= 10 rows | PASS |

Every number above is read from validation/*.json and data/*.json by `src/skqd/campaign33/assemble.py` and stored in `validation/dryrun/C33_campaign.json`.
