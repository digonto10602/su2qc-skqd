# Gate H0_ddtest -- client-side DD A/B test, ibm_kingston

**Status: PASS** -- `scripts/gate_H0_ddtest.py --stage assemble --counts data/hardware/H0_ddtest_ibm_kingston/counts --out H0_ddtest`.
Runtime 601 s.  Every number below is computed by the script from the raw counts and from `data/hardware/H0_ddtest_prep/prereg_84d59cbf9b5973d1.json`
and is stored in `validation/H0_ddtest.json`.  Prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage T).

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on the ratios, the adoption or the signed-bar read.

## 1. Preregistration

`data/hardware/H0_ddtest_prep/prereg_84d59cbf9b5973d1.json`, written 2026-10-02 19:53:23 UTC at commit `e447bd0` on the patch record
`data/hardware/H0_ddtest_prep/calibration_20261002T1906Z.json` (fingerprint `84d59cbf9b5973d11d2c4be496f8d55da0d6f06d3dd8a33265fb47832dd432c9`).  Patch [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]; 10 pubs x 6000
shots; execution estimate 17.26 s.  Rule: A cell i in {T1, T2, T3} qualifies iff R_i,lo95 > 1 and R_i >= 1.25.  Among qualifying cells the one with the largest point R_i is adopted for Stage R; if none qualifies, Stage R runs the baseline (T0).  Signed bar on the adopted cell: GO iff f_adopted,lo95 >= 0.1, NO-GO iff f_adopted,hi95 < 0.1, AMBIGUOUS otherwise (information for the owner; Stage R proceeds in every case under the owner's decision).  R_i = f_i / f_0 = X_i / X_0 (pooled excess reference counts over the two k = 1 circuits: same shots, same p_ref, same readout factor); 95 % interval exp(ln R_i +- 1.96 sqrt(1/X_i + 1/X_0)) (Poisson on the excess counts, the garbage expectation subtracted as in the pilot); a parametric bootstrap (10 000 draws, seed 11) beside it as a cross-check, never as the verdict.

## 2. Live block

| item | value |
|---|---|
| job id(s) / status | ['db01005j371s73dnmbd0'] / ['DONE'] |
| usage (s) | 20.0 |
| preflight estimate (s) | 17.257584000000023 |
| fingerprint at prereg / submission / retrieval | `84d59cbf9b5973d1` / `84d59cbf9b5973d1` / `84d59cbf9b5973d1` |
| prereg match at submission / retrieval | True / True |
| retrieval diff | None |
| prereg commit time / submitted | 2026-10-02T13:39:21-06:00 (added in aa4da1e576226eb872fae7b688f339bac97cf875, 2026-10-02T13:53:50-06:00) / 2026-10-02 20:11:42 UTC |
| account usage before / after | 29 s (571 left) / 49 s (551 left) |
| sampler options | {'default_shots': 6000, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |

## 3. The four cells against their null values

| cell | accepted | ref hits | garbage exp. | excess X | f_pool [68 %] [95 %] | R = X_i/X_0 | R 95 % | R bootstrap 95 % | null e^-S_DD | R / null | qualifies |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T0 | 526 | 352 | 2.93 | 349.1 | 0.0400 [0.0379, 0.0423] [0.0358, 0.0446] | 1.000 | n/a | n/a | 1.000 | n/a | None |
| T1 | 102 | 7 | 2.93 | 4.1 | 0.0005 [0.0002, 0.0009] [-0.0000, 0.0013] | 0.012 | [0.004, 0.031] | [-0.003, 0.028] | 0.816 | 0.014 | False |
| T2 | 1429 | 978 | 2.93 | 975.1 | 0.1118 [0.1082, 0.1155] [0.1048, 0.1192] | 2.793 | [2.472, 3.157] | [2.474, 3.172] | 0.841 | 3.321 | True |
| T3 | 1456 | 987 | 2.93 | 984.1 | 0.1129 [0.1093, 0.1166] [0.1058, 0.1203] | 2.819 | [2.495, 3.185] | [2.493, 3.193] | 0.944 | 2.985 | True |

Per circuit:

| cell | circuit | accepted | ref hits | f reference [95 %] | f mixture [68 %] | C6 dev (info) | pulses | distance histogram |
|---|---|---|---|---|---|---|---|---|
| T0 | B0_ref06_k1 | 294 | 175 | 0.0399 [0.0341, 0.0465] | 0.0404 [0.0386, 0.0422] | 0.012 | 0 | [175, 0, 55, 36, 2, 6, 3, 10, 2, 2, 3, 0, 0] |
| T0 | B1_ref07_k1 | 232 | 177 | 0.0401 [0.0343, 0.0467] | 0.0397 [0.0384, 0.0410] | 0.010 | 0 | [177, 0, 19, 21, 0, 7, 0, 4, 3, 1, 0] |
| T1 | B0_ref06_k1 | 62 | 4 | 0.0006 [-0.0001, 0.0021] | 0.0007 [0.0002, 0.0012] | 0.148 | 862 | [4, 0, 15, 12, 4, 11, 0, 10, 1, 0, 3, 0, 2] |
| T1 | B1_ref07_k1 | 40 | 3 | 0.0004 [-0.0002, 0.0017] | 0.0003 [0.0000, 0.0008] | 0.125 | 862 | [3, 0, 14, 7, 0, 9, 0, 6, 0, 1, 0] |
| T2 | B0_ref06_k1 | 743 | 478 | 0.1097 [0.0998, 0.1202] | 0.1130 [0.1102, 0.1156] | 0.030 | 776 | [478, 0, 131, 103, 2, 10, 4, 7, 5, 1, 2, 0, 0] |
| T2 | B1_ref07_k1 | 686 | 500 | 0.1140 [0.1040, 0.1247] | 0.1137 [0.1112, 0.1160] | 0.003 | 780 | [500, 0, 75, 68, 0, 18, 0, 7, 15, 1, 2] |
| T3 | B0_ref06_k1 | 760 | 475 | 0.1090 [0.0992, 0.1195] | 0.1140 [0.1112, 0.1167] | 0.046 | 244 | [475, 0, 129, 115, 2, 15, 1, 9, 8, 3, 2, 0, 1] |
| T3 | B1_ref07_k1 | 696 | 512 | 0.1167 [0.1066, 0.1275] | 0.1171 [0.1148, 0.1194] | 0.004 | 244 | [512, 0, 74, 73, 0, 14, 0, 7, 13, 2, 1] |

Below-null cells (R's 95 % upper bound < the cell's null e^-S_DD): T1 (R 0.012, 95 % [0.004, 0.031], null 0.816).  Above-null cells (R's 95 % lower bound >
the null): T2 (R 2.793, 95 % [2.472, 3.157], null 0.841); T3 (R 2.819, 95 % [2.495, 3.185], null 0.944).  A ratio below the null means the inserted pulses cost more than the record's x error says (or a
mechanism the null does not contain); it is reported as measured, not averaged, and this test does not establish its cause.

## 4. Adoption (preregistered rule P7)

Qualifying cells: ['T2', 'T3'].  **Adopted: T3** -- f_adopted = 0.1129 (68 % [0.1093, 0.1166],
95 % [0.1058, 0.1203]).

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
| 5 | 13100 | 0 | 19.42 |
| 2 | 31400 | 0 | 18.62 |

N4 {'B=0': 13100, 'B=1': 31400}; coarse shots 133907; total 41.71 s; reserve
79.5 s against 551 s left: fits True.

## 7. Readout

Smallest confusion diagonal 0.9457; readout survival prod_q (1 - e_q) 0.8337;
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
| K1 preregistration committed before the submission; prereg = session = submission fingerprint; retrieval fingerprint recorded (a move is information) | prereg commit 2026-10-02T13:39:21-06:00, added aa4da1e 2026-10-02T13:53:50-06:00, submitted 2026-10-02 20:11:42 UTC; fingerprints equal True; retrieval match True | commit < submission, equal fingerprints, retrieval recorded | PASS |
| K2 one job DONE, usage_s <= 40, preflight estimate <= 30 s, 10 counts files x 6000 shots, DD off and twirling off, the reserve of T.A3 present with 40 + reserve <= remaining at start | jobs ['db01005j371s73dnmbd0'] ['DONE'], usage 20.0 s, estimate 17.26 s, counts ok True, options off True, reserve 210.8 s (+40 vs 571) True | all hold | PASS |
| K3 readout confusion of the patch (all-0 / all-1 pubs): smallest diagonal | 0.9457 | >= 0.9 | PASS |
| K4 decoder round trip over every accepted string of the 8 coarse pubs | 0 mismatches over 56 strings | 0 | PASS |
| K5 circuits: exactness at build (< 1e-10, leakage < 1e-9), DD statevector = base to 1e-10, duration equal to 1 dt, no pulses in leading / trailing windows, basis = kingston's, op multisets as recorded, S_DD and null ratio present, ALAP scheduling asserted | 8/8 circuits; max |d| 5.7e-13 | all hold | PASS |
| K6 dry-run gate validation/H0_ddtest_dryrun.json PASS | PASS | PASS | PASS |
| K7 data.decision complete and the adoption and signed-bar verdict recomputed from the recorded intervals | missing []; adopted T3 (recomputed T3), bar GO (recomputed GO) | complete and equal | PASS |
| K8 pytest -q tests and scripts/check_package.py | pytest: 252 passed, 3 skipped, 10 warnings in 589.96s (0:09:49); check_package rc 0 | all pass | PASS |
