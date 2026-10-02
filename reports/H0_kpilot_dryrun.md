# Gate H0_kpilot_dryrun -- the kingston T2* pilot, dry run (local Aer on the FakeKingston snapshot; a path check, not a prediction)

**Status: PASS** -- `scripts/gate_H0_kpilot.py --stage assemble --counts data/hardware/H0_kpilot_dryrun/counts --dry-run --out H0_kpilot_dryrun`.
Runtime 49 s.  Every number below is computed by the script from the raw counts and from
`data/hardware/H0_kpilot_prep/prereg_ec74eb8bf15dde41.json` and is stored in `validation/H0_kpilot_dryrun.json`.

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on f, r_eff or the decision: a NO-GO pilot is a PASS gate.

## 1. The decision (dry_run: true)

| quantity | value |
|---|---|
| f_pool (reference-string statistic, two k = 1 circuits) | **0.2073** 68 % [0.2013, 0.2134], 95 % [0.1955, 0.2196] |
| pooled reference hits / garbage expectation | 1207 / 1.95 |
| worst circuit (B0_ref06_k1) f 95 % | [0.1905, 0.2247] against 0.05 |
| **decision** | **GO** |
| top-up shots (only if AMBIGUOUS) | None |
| r_eff | **0.9775** 68 % [0.9573, 0.9939], 95 % [0.9396, 1.0112] |
| r_crit preregistered / day | 0.3285 / 0.2788 |
| r verdict | above |
| f_Aer(r_eff) (B0_ref06_k1, mixture grid) | 0.2099 (interpolated) |
| measured / Aer, model_consistent (factor 3) | 0.987, True |
| same with the reference statistic on both sides | 0.975, True |
| f and r verdicts agree | True |
| shape ratio median (2 = exponential, 4 = Gaussian) | 1.97 |
| qubits resolved long / half | 12 / 12 |
| usage (s) | 0.0 |

Preregistered rule: GO iff f_pool,lo95 >= 0.1 and min_c f_c,lo95 >= 0.05; NO-GO iff f_pool,hi95 < 0.1 or
min_c f_c,hi95 < 0.05; AMBIGUOUS otherwise.  The direct measurement decides f; a disagreement with the r-verdict is a
model finding.

## 2. Preregistration

`data/hardware/H0_kpilot_prep/prereg_ec74eb8bf15dde41.json`, written 2026-10-02 17:41:28 UTC at commit `cc9d60e` on the patch record
`data/hardware/H0_kpilot_prep/calibration_20261002T1627Z.json` (fingerprint `ec74eb8bf15dde411d7d17701b4eb1805fc0954130b0876422155202c7a5ab32`).  Patch [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]; windows
128 dt = 512 ns, N_long 86
(44.03 us), N_half 43 (22.02 us)
matched to T_s 44.24 us; 8 pubs x 4000 shots; execution estimate
9.04 s.

## 3. Live block

| item | value |
|---|---|
| job id(s) / status | ['769e80e7-3e8f-48f8-9b84-d36d00ee3915'] / ['DONE'] |
| usage (s) | 0.0 |
| preflight estimate (s) | None |
| fingerprint at prereg / submission / retrieval | `ec74eb8bf15dde41` / `n/a` / `n/a` |
| prereg match at submission | None |
| retrieval diff | None |
| prereg commit time / submitted | None (added in None, None) / None |
| account usage before / after | 17 s (583 left) / None s (None left) |
| sampler options | {'default_shots': 4000, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |

## 4. Readout

Smallest confusion diagonal 0.8512; measured readout survival of the patch prod_q (1 - e_q)
= 0.7094 (the analysis applies the manual's factor 0.82).  Preregistered live expectation
(1 - measure_error of the patch record): min 0.9552 on qubit 72.
Dry-run K3 (prompts/21a, option (a)): the measured diagonals are compared with the readout model of the simulator (NoiseModel.from_backend(FakeKingston) local readout errors) within 3 binomial sigma at 4000 shots.  The first assembly of this dry run failed the device form (>= 0.9) because qubit 92 carries a snapshot readout error of 0.1492 against the live record's 0.0243; the device criterion is unchanged and is evaluated only on device counts.

## 5. Windowed Ramsey (readout-corrected; T2* by rule S3)

| qubit | raw P0 long | P0 long | sigma | raw P0 half | P0 half | sigma | T2* long (us) | T2* half (us) | T2* used (us) | T2 echo (us) | T2*/T2 echo | shape ratio | echo bound long / half | P0 at r=0.174 long / half |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 59 | 0.9495 | 0.9582 | 0.0035 | 0.9663 | 0.9752 | 0.0029 | 504.0 | 432.0 | 504.0 (measured, long) | 473.0 | 1.066 | 1.71 | 0.9556 / 0.9773 | 0.7928 / 0.8826 |
| 71 | 0.8832 | 0.8891 | 0.0051 | 0.9330 | 0.9395 | 0.0040 | 175.7 | 170.7 | 175.7 (measured, long) | 172.5 | 1.018 | 1.94 | 0.8874 / 0.9401 | 0.6153 / 0.7401 |
| 72 | 0.8325 | 0.8703 | 0.0065 | 0.8805 | 0.9235 | 0.0057 | 146.6 | 132.6 | 146.6 (measured, long) | 138.2 | 1.061 | 1.81 | 0.8636 / 0.9264 | 0.5801 / 0.7001 |
| 73 | 0.8860 | 0.9220 | 0.0055 | 0.9247 | 0.9643 | 0.0045 | 259.6 | 297.0 | 259.6 (measured, long) | 270.7 | 0.959 | 2.29 | 0.9249 / 0.9609 | 0.6963 / 0.8133 |
| 74 | 0.9038 | 0.9112 | 0.0047 | 0.9420 | 0.9501 | 0.0038 | 225.2 | 209.5 | 225.2 (measured, long) | 205.1 | 1.098 | 1.86 | 0.9034 / 0.9491 | 0.6456 / 0.7698 |
| 75 | 0.8488 | 0.8597 | 0.0059 | 0.9107 | 0.9238 | 0.0047 | 133.7 | 133.1 | 133.7 (measured, long) | 133.0 | 1.005 | 1.99 | 0.8591 / 0.9237 | 0.5746 / 0.6931 |
| 79 | 0.7742 | 0.7790 | 0.0067 | 0.8700 | 0.8762 | 0.0054 | 75.5 | 77.4 | 75.5 (measured, long) | 78.4 | 0.963 | 2.05 | 0.7852 / 0.8776 | 0.5198 / 0.5996 |
| 91 | 0.8310 | 0.8373 | 0.0060 | 0.9078 | 0.9156 | 0.0047 | 111.8 | 119.1 | 111.8 (measured, long) | 120.2 | 0.931 | 2.13 | 0.8466 / 0.9163 | 0.5609 / 0.6744 |
| 92 | 0.7993 | 0.9265 | 0.0090 | 0.8223 | 0.9590 | 0.0085 | 276.9 | 257.4 | 276.9 (measured, long) | 302.0 | 0.917 | 1.86 | 0.9322 / 0.9648 | 0.7163 / 0.8288 |
| 93 | 0.8558 | 0.8610 | 0.0056 | 0.9257 | 0.9318 | 0.0042 | 135.2 | 150.1 | 135.2 (measured, long) | 138.4 | 0.977 | 2.22 | 0.8637 / 0.9265 | 0.5803 / 0.7004 |
| 94 | 0.8952 | 0.9153 | 0.0051 | 0.9365 | 0.9589 | 0.0041 | 237.4 | 256.4 | 237.4 (measured, long) | 264.9 | 0.896 | 2.16 | 0.9234 / 0.9601 | 0.6924 / 0.8101 |
| 95 | 0.9543 | 0.9591 | 0.0033 | 0.9677 | 0.9727 | 0.0028 | 515.6 | 392.3 | 515.6 (measured, long) | 521.0 | 0.990 | 1.52 | 0.9595 / 0.9793 | 0.8076 / 0.8922 |

## 6. Windowed T1

| qubit | raw P1 | P1 corrected | P1 predicted | T1 measured (us) | T1 record (us) | rate ratio | in band |
|---|---|---|---|---|---|---|---|
| 59 | 0.8665 | 0.8692 | 0.8679 | 314.1 | 310.8 | 0.99 | yes |
| 71 | 0.8360 | 0.8390 | 0.8410 | 250.9 | 254.3 | 1.01 | yes |
| 72 | 0.8065 | 0.8381 | 0.8459 | 249.4 | 263.1 | 1.06 | yes |
| 73 | 0.8678 | 0.9002 | 0.8868 | 418.8 | 366.6 | 0.88 | yes |
| 74 | 0.8612 | 0.8674 | 0.8725 | 309.6 | 322.9 | 1.04 | yes |
| 75 | 0.8570 | 0.8698 | 0.8767 | 315.6 | 334.6 | 1.06 | yes |
| 79 | 0.8685 | 0.8732 | 0.8654 | 324.6 | 304.5 | 0.94 | yes |
| 91 | 0.8313 | 0.8383 | 0.8473 | 249.7 | 265.6 | 1.06 | yes |
| 92 | 0.7520 | 0.8527 | 0.8588 | 276.2 | 289.3 | 1.05 | yes |
| 93 | 0.8805 | 0.8832 | 0.8784 | 354.7 | 339.6 | 0.96 | yes |
| 94 | 0.8582 | 0.8795 | 0.8748 | 342.9 | 329.1 | 0.96 | yes |
| 95 | 0.8885 | 0.8926 | 0.8863 | 387.6 | 364.8 | 0.94 | yes |

## 7. r_eff against r_crit

r_eff = **0.9775** (68 % [0.9573, 0.9939], 95 % [0.9396, 1.0112];
10000 bootstrap draws, 0 failed) on 338 delay windows
(ALAP B0_ref06_k1 explicit delays, leading excluded); S_T2 at the measured T2* 0.924 against 0.903 at the echo T2;
idle-weighted harmonic mean of T2*/T2_echo 0.978.  Preregistered r_crit 0.3285;
the day's 0.2788.

## 8. The circuits

| circuit | shots | accepted | ref hits | garbage expectation | P_ge | p_ref | f_clean reference [68 %] [95 %] | f_clean mixture [68 %] | C6 dev (info) | Aer f r=1 / r_eff / 0.174 | distance histogram |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B0_ref06_k1 | 4000 | 933 | 601 | 0.98 | 0.00e+00 | 0.8833 | 0.2071 [0.1986, 0.2159] [0.1905, 0.2247] | 0.2062 [0.2015, 0.2107] | 0.005 | 0.2114 / 0.2099 / 0.0413 | [601, 0, 180, 104, 4, 22, 3, 6, 6, 2, 5, 0, 0] |
| B1_ref07_k1 | 4000 | 779 | 606 | 0.98 | 0.00e+00 | 0.8891 | 0.2075 [0.1990, 0.2163] [0.1909, 0.2251] | 0.2072 [0.2038, 0.2105] | 0.001 | 0.2268 / 0.2221 / 0.0458 | [606, 0, 66, 74, 0, 12, 0, 2, 17, 1, 1] |
| B0_ref06_k4 | 4000 | 792 | 82 | 0.98 | 1.15e-124 | 0.1270 | 0.1946 [0.1729, 0.2188] [0.1535, 0.2431] | 0.2060 [0.1995, 0.2120] | 0.059 | 0.2379 / 0.2334 / 0.0555 | [82, 0, 106, 274, 13, 98, 89, 77, 7, 30, 11, 0, 5] |

B0_ref06_k4 is information only (C6 ruling: the estimators are not tolerance-calibrated at p_ref 0.13).

## 9. Budgets at the measured f_pool (information)

{"f": 0.20729269327520858, "D3prime_N4": {"B=0": 7000, "B=1": 17000}, "D3prime_execution_s": 36.241321820000024, "D3prime_total_coarse_shots": 74607, "D3pp_H0_shots_per_k1": 676, "D3pp_H0_execution_s": 17.188748684000004}
information: the signed family's 28 r = 1 circuits relabelled onto the pilot's patch at their own durations; r = 2, 3 excluded (not rebuilt in this family)

## 10. Honest limits

- r_eff is one number for a patch whose per-qubit ratios may spread an order of magnitude (this patch: T2*/T2_echo
  0.896-1.098; fez: 0.070-1.209); the uniform-r axis is the one r_crit is defined on, and the per-qubit table is beside it.
- Aer's dephasing on a delay is exponential; the shape ratio (median 1.97; 2 exponential, 4 Gaussian) tests
  that with two lengths only.  A Gaussian decay makes the many short windows of the circuit less harmful than the long Ramsey
  windows suggest -- the direction in which the r-verdict could be pessimistic while the f-verdict is not; that is why f is primary.
- Two k = 1 circuits are not the 28-circuit family; the S2D bar is read on them as a pilot.  The k = 4 cell's f is information.
- The readout factor 0.82 of manual Step 4.4 is applied to both statistics and to the Aer predictions; the patch's measured
  readout survival is 0.7094.
- One job on one calibration content; a drift between submission and retrieval is reported (retrieval diff above), not corrected.

## 11. Criteria

| check | value | criterion | result |
|---|---|---|---|
| K1 preregistration before data | n/a (dry run) | device run only | PASS |
| K2 one job DONE, usage <= 60 s, estimate <= 30 s, 8 x 4000 counts, DD/twirling off | n/a (dry run) | device run only | PASS |
| K3 readout confusion of the patch (all-0 / all-1 pubs) (dry run: agreement with the snapshot's readout model; the device criterion >= 0.9 is evaluated only on device counts) | 12/12 qubits with |z| <= 3 on both diagonals (max |z| 2.43); min diagonal 0.8512 (information); live expectation min 0.9552 (qubit 72) | all 12 within 3 binomial sigma; live expectation >= 0.9 | PASS |
| K4 decoder round trip over every accepted string of the three coarse pubs | 0 mismatches over 53 strings | 0 | PASS |
| K5 idle tests (reference record: the FakeKingston snapshot) | T2* measured 12/12; P0 <= echo bound + 3 sigma at both windows 12/12; 1/T1 in [0.5, 2.0] x record 12/12; r_eff 0.9775 68 % [0.9573, 0.9939] 95 % [0.9396, 1.0112]; dry run: T2* within 3 sigma of the snapshot's echo T2 12/12 | >= 10 of 12 each; r_eff finite with both intervals | PASS |
| K6 circuits: exactness of the three coarse circuits at build, ALAP scheduling asserted, idle-pub op multisets as intended | exact True (max |d| 5.7e-13), alap True, ops True | all hold | PASS |
| K7 every preregistered Aer cell present with strided seeds; r = 1 B0_ref06_k1 within 25 % of S2D_levers' L1_seed_alap cell (mapping reproduced) | cells True; day 0.2114 vs 0.2170 (dev 0.026) | present, strided, <= 0.25 | PASS |
| K8 data.decision complete and reproduces the preregistered rule from the recorded intervals | missing []; decision GO, recomputed GO | complete and equal | PASS |
| K9 pytest -q tests and scripts/check_package.py | n/a (--skip-tests, dry run) | all pass | PASS |
