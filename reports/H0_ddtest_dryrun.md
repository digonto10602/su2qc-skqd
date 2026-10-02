# Gate H0_ddtest_dryrun -- client-side DD A/B test, dry run (local Aer on the FakeKingston snapshot; a path check, not a prediction)

**Status: PASS** -- `scripts/gate_H0_ddtest.py --stage assemble --counts data/hardware/H0_ddtest_dryrun/counts --dry-run --out H0_ddtest_dryrun`.
Runtime 15 s.  Every number below is computed by the script from the raw counts and from `data/hardware/H0_ddtest_prep/prereg_84d59cbf9b5973d1.json`
and is stored in `validation/H0_ddtest_dryrun.json`.  Prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage T).

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on the ratios, the adoption or the signed-bar read. Aer cannot show a DD gain: its relaxation on a delay is Markovian, so the dry-run ratios sit near the null values exp(-S_DD) and are path checks, not predictions (P10).

## 1. Preregistration

`data/hardware/H0_ddtest_prep/prereg_84d59cbf9b5973d1.json`, written 2026-10-02 19:53:23 UTC at commit `e447bd0` on the patch record
`data/hardware/H0_ddtest_prep/calibration_20261002T1906Z.json` (fingerprint `84d59cbf9b5973d11d2c4be496f8d55da0d6f06d3dd8a33265fb47832dd432c9`).  Patch [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]; 10 pubs x 6000
shots; execution estimate 17.26 s.  Rule: A cell i in {T1, T2, T3} qualifies iff R_i,lo95 > 1 and R_i >= 1.25.  Among qualifying cells the one with the largest point R_i is adopted for Stage R; if none qualifies, Stage R runs the baseline (T0).  Signed bar on the adopted cell: GO iff f_adopted,lo95 >= 0.1, NO-GO iff f_adopted,hi95 < 0.1, AMBIGUOUS otherwise (information for the owner; Stage R proceeds in every case under the owner's decision).  R_i = f_i / f_0 = X_i / X_0 (pooled excess reference counts over the two k = 1 circuits: same shots, same p_ref, same readout factor); 95 % interval exp(ln R_i +- 1.96 sqrt(1/X_i + 1/X_0)) (Poisson on the excess counts, the garbage expectation subtracted as in the pilot); a parametric bootstrap (10 000 draws, seed 11) beside it as a cross-check, never as the verdict.

## 2. Live block

| item | value |
|---|---|
| job id(s) / status | ['f54a2ece-b8ff-4962-92db-e3dfdd02806b'] / ['DONE'] |
| usage (s) | 0.0 |
| preflight estimate (s) | None |
| fingerprint at prereg / submission / retrieval | `84d59cbf9b5973d1` / `n/a` / `n/a` |
| prereg match at submission / retrieval | None / None |
| retrieval diff | None |
| prereg commit time / submitted | None (added in None, None) / None |
| account usage before / after | 29 s (571 left) / None s (None left) |
| sampler options | {'default_shots': 6000, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |

## 3. The four cells against their null values

| cell | accepted | ref hits | garbage exp. | excess X | f_pool [68 %] [95 %] | R = X_i/X_0 | R 95 % | R bootstrap 95 % | null e^-S_DD | R / null | qualifies |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T0 | 2498 | 1753 | 2.93 | 1750.1 | 0.2007 [0.1959, 0.2056] [0.1912, 0.2105] | 1.000 | n/a | n/a | 1.000 | n/a | None |
| T1 | 1862 | 1253 | 2.93 | 1250.1 | 0.1434 [0.1393, 0.1475] [0.1354, 0.1517] | 0.714 | [0.664, 0.768] | [0.664, 0.767] | 0.816 | 0.875 | False |
| T2 | 2024 | 1349 | 2.93 | 1346.1 | 0.1544 [0.1502, 0.1587] [0.1461, 0.1630] | 0.769 | [0.716, 0.826] | [0.715, 0.826] | 0.841 | 0.915 | False |
| T3 | 2059 | 1381 | 2.93 | 1378.1 | 0.1580 [0.1538, 0.1624] [0.1496, 0.1668] | 0.787 | [0.734, 0.845] | [0.733, 0.847] | 0.944 | 0.834 | False |

Per circuit:

| cell | circuit | accepted | ref hits | f reference [95 %] | f mixture [68 %] | C6 dev (info) | pulses | distance histogram |
|---|---|---|---|---|---|---|---|---|
| T0 | B0_ref06_k1 | 1319 | 856 | 0.1966 [0.1834, 0.2106] | 0.1997 [0.1961, 0.2033] | 0.016 | 0 | [856, 0, 231, 162, 10, 16, 2, 6, 28, 2, 6, 0, 0] |
| T0 | B1_ref07_k1 | 1179 | 897 | 0.2047 [0.1913, 0.2189] | 0.2053 [0.2024, 0.2081] | 0.003 | 0 | [897, 0, 117, 119, 0, 17, 0, 2, 24, 0, 3] |
| T1 | B0_ref06_k1 | 992 | 609 | 0.1398 [0.1287, 0.1516] | 0.1423 [0.1391, 0.1455] | 0.018 | 862 | [609, 0, 199, 129, 6, 22, 5, 9, 9, 0, 4, 0, 0] |
| T1 | B1_ref07_k1 | 870 | 644 | 0.1469 [0.1355, 0.1590] | 0.1465 [0.1439, 0.1491] | 0.002 | 862 | [644, 0, 105, 88, 0, 12, 0, 6, 12, 0, 3] |
| T2 | B0_ref06_k1 | 1086 | 671 | 0.1541 [0.1424, 0.1665] | 0.1598 [0.1564, 0.1631] | 0.037 | 776 | [671, 0, 197, 155, 5, 22, 0, 11, 19, 0, 5, 0, 1] |
| T2 | B1_ref07_k1 | 938 | 678 | 0.1547 [0.1430, 0.1670] | 0.1551 [0.1522, 0.1578] | 0.003 | 780 | [678, 0, 107, 96, 0, 13, 0, 11, 26, 0, 7] |
| T3 | B0_ref06_k1 | 1073 | 646 | 0.1483 [0.1368, 0.1605] | 0.1528 [0.1493, 0.1562] | 0.030 | 244 | [646, 0, 215, 147, 9, 20, 1, 8, 24, 0, 2, 0, 1] |
| T3 | B1_ref07_k1 | 986 | 735 | 0.1677 [0.1555, 0.1806] | 0.1695 [0.1668, 0.1721] | 0.011 | 244 | [735, 0, 94, 109, 0, 15, 0, 8, 19, 0, 6] |

## 4. Adoption (preregistered rule P7)

Qualifying cells: none.  **Adopted: T0** -- f_adopted = 0.2007 (68 % [0.1959, 0.2056],
95 % [0.1912, 0.2105]).

## 5. The signed bar (information for the owner)

f >= 0.1 read on the adopted cell's 95 % interval: **GO**.  Stage R proceeds in every case under the owner's
decision of 2026-10-02.

## 6. The Stage R reserve at the adopted f (P1)

Coordinator ruling (2026-10-02) on planner decision P8: the D3''-H0 lift of the seven k = 1 circuits is STRUCK; Stage R is pure rule D3' at the adopted cell's f_pool, which is what the owner named ("121 s").  The planner's prompt file is not edited; the strike enters here (reserve, plan, tests).

| Stage R job: pubs | shots | chunk | execution (s) |
|---|---|---|---|
| 14 | 267 | 0 | 1.11 |
| 7 | 267 | 1 | 0.55 |
| 2 | 4000 | 0 | 2.02 |
| 5 | 7300 | 0 | 10.82 |
| 2 | 17600 | 0 | 10.44 |

N4 {'B=0': 7300, 'B=1': 17600}; coarse shots 77307; total 24.94 s; reserve
46.5 s against 571 s left: fits True.

## 7. Readout

Smallest confusion diagonal 0.8468; readout survival prod_q (1 - e_q) 0.6964;
preregistered live expectation min 0.9525 (qubit 72).

## 8. Honest limits

- Stage T compares four cells inside one job on one calibration content; its ratios carry no statement about other days or
  patches.  The null ratios (e^-S_DD) assume the record's x error for every inserted pulse.
- Three candidates are tested; the family-wise chance that a null cell qualifies on the interval alone is <= 7.5 %, and the
  1.25 floor is a cost argument, not a physics threshold.
- A qualifying ratio raises f for *this* circuit's idle structure; the signed bar is read on the adopted cell's lower 95 % bound
  and nothing else.
- Two k = 1 circuits are not a family-level statement at other k.
- One calibration content; drift between submission and retrieval is reported (above), not corrected.

## 9. Criteria

| check | value | criterion | result |
|---|---|---|---|
| K1 preregistration before data | n/a (dry run) | device run only | PASS |
| K2 one job DONE, usage <= 40 s, estimate <= 30 s, 10 x 6000 counts, DD/twirling off, reserve present | n/a (dry run) | device run only | PASS |
| K3 readout (dry run: agreement with the snapshot's readout model, prompts/21a; the device criterion >= 0.9 is evaluated only on device counts) | 12/12 qubits with |z| <= 3; min diagonal 0.8468 (information); live expectation min 0.9525 (qubit 72) | all 12 within 3 binomial sigma; live expectation >= 0.9 | PASS |
| K4 decoder round trip over every accepted string of the 8 coarse pubs | 0 mismatches over 54 strings | 0 | PASS |
| K5 circuits: exactness at build (< 1e-10, leakage < 1e-9), DD statevector = base to 1e-10, duration equal to 1 dt, no pulses in leading / trailing windows, basis = kingston's, op multisets as recorded, S_DD and null ratio present, ALAP scheduling asserted | 8/8 circuits; max |d| 5.7e-13 | all hold | PASS |
| K6 dry-run gate PASS | n/a (this is the dry run) | device run only | PASS |
| K7 data.decision complete and the adoption and signed-bar verdict recomputed from the recorded intervals | missing []; adopted T0 (recomputed T0), bar GO (recomputed GO) | complete and equal | PASS |
| K8 pytest -q tests and scripts/check_package.py | n/a (--skip-tests) | all pass | PASS |
