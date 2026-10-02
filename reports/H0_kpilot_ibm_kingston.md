# Gate H0_kpilot -- the kingston T2* pilot, ibm_kingston

**Status: FAIL** -- `scripts/gate_H0_kpilot.py --stage assemble --counts data/hardware/H0_kpilot_ibm_kingston/counts --out H0_kpilot`.
Runtime 450 s.  Every number below is computed by the script from the raw counts and from
`data/hardware/H0_kpilot_prep/prereg_ec74eb8bf15dde41.json` and is stored in `validation/H0_kpilot.json`.

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on f, r_eff or the decision: a NO-GO pilot is a PASS gate.

## 1. The decision

| quantity | value |
|---|---|
| f_pool (reference-string statistic, two k = 1 circuits) | **0.0413** 68 % [0.0386, 0.0441], 95 % [0.0361, 0.0470] |
| pooled reference hits / garbage expectation | 242 / 1.95 |
| worst circuit (B0_ref06_k1) f 95 % | [0.0332, 0.0486] against 0.05 |
| **decision** | **NO-GO** |
| top-up shots (only if AMBIGUOUS) | None |
| r_eff | **0.0974** 68 % [0.0879, 0.1022], 95 % [0.0757, 0.1154] |
| r_crit preregistered / day | 0.3285 / 0.2788 |
| r verdict | below |
| f_Aer(r_eff) (B0_ref06_k1, mixture grid) | 0.0124 (extrapolated below the grid) |
| measured / Aer, model_consistent (factor 3) | 3.268, False |
| same with the reference statistic on both sides | 2.971, True |
| f and r verdicts agree | True |
| Aer-equivalent uniform r of the measured B0_ref06_k1 f (information) | 0.1721 (extrapolated) |
| qubits with P0 < 1/2 - 3 sigma (coherent phase, information) | {'59': ['long'], '71': ['long', 'half'], '72': ['long'], '73': ['long', 'half'], '74': ['long'], '79': ['long'], '92': ['long'], '93': ['half'], '94': ['half']} |
| shape ratio median (2 = exponential, 4 = Gaussian) | 2.93 |
| qubits resolved long / half | 5 / 7 |
| usage (s) | 12.0 |

Preregistered rule: GO iff f_pool,lo95 >= 0.1 and min_c f_c,lo95 >= 0.05; NO-GO iff f_pool,hi95 < 0.1 or
min_c f_c,hi95 < 0.05; AMBIGUOUS otherwise.  The direct measurement decides f; a disagreement with the r-verdict is a
model finding.

## 2. Preregistration

`data/hardware/H0_kpilot_prep/prereg_ec74eb8bf15dde41.json`, written 2026-10-02 17:41:28 UTC at commit `cc9d60e` on the patch record
`data/hardware/H0_kpilot_prep/calibration_20261002T1627Z.json` (fingerprint `ec74eb8bf15dde411d7d17701b4eb1805fc0954130b0876422155202c7a5ab32`).  Patch [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]; windows
128 dt = 512 ns, N_long 86
(44.03 us), N_half 43 (22.02 us)
matched to T_s 44.24 us; 8 pubs x 4000 shots; execution estimate
9.04 s.  Analysis change after the preregistration:
dry-run K3 form changed (prompts/21a option (a)); device K3 >= 0.9 unchanged; no prereg number edited (commit `f705553`).

## 3. Live block

| item | value |
|---|---|
| job id(s) / status | ['davv8504oijs73e88fvg'] / ['DONE'] |
| usage (s) | 12.0 |
| preflight estimate (s) | 9.042240000000005 |
| fingerprint at prereg / submission / retrieval | `ec74eb8bf15dde41` / `ec74eb8bf15dde41` / `ec74eb8bf15dde41` |
| prereg match at submission | True |
| retrieval diff | None |
| prereg commit time / submitted | 2026-10-02T11:15:19-06:00 (added in 148e873dc36fe67f9469f06c53cbf0cfc97a9e9a, 2026-10-02T11:41:39-06:00) / 2026-10-02 18:12:35 UTC |
| account usage before / after | 17 s (583 left) / 29 s (571 left) |
| sampler options | {'default_shots': 4000, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |

## 4. Readout

Smallest confusion diagonal 0.9420; measured readout survival of the patch prod_q (1 - e_q)
= 0.8383 (the analysis applies the manual's factor 0.82).  Preregistered live expectation
(1 - measure_error of the patch record): min 0.9552 on qubit 72.


## 5. Windowed Ramsey (readout-corrected; T2* by rule S3)

| qubit | raw P0 long | P0 long | sigma | raw P0 half | P0 half | sigma | T2* long (us) | T2* half (us) | T2* used (us) | T2 echo (us) | T2*/T2 echo | shape ratio | echo bound long / half | P0 at r=0.174 long / half |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 59 | 0.1927 | 0.1879 | 0.0063 | 0.4912 | 0.4892 | 0.0080 | n/a | n/a | 6.0 (upper_bound_3sigma_half, half) | 481.4 | 0.013 | n/a | 0.9563 / 0.9776 | 0.7956 / 0.8844 |
| 71 | 0.2935 | 0.2888 | 0.0073 | 0.3868 | 0.3828 | 0.0078 | n/a | n/a | 6.0 (patch_minimum, None) | 205.9 | 0.029 | n/a | 0.9038 / 0.9493 | 0.6463 / 0.7705 |
| 72 | 0.4842 | 0.4676 | 0.0087 | 0.7240 | 0.7307 | 0.0078 | n/a | 28.5 | 28.5 (measured, half) | 152.1 | 0.187 | n/a | 0.8743 / 0.9326 | 0.5947 / 0.7176 |
| 73 | 0.4107 | 0.3895 | 0.0081 | 0.3277 | 0.3033 | 0.0077 | n/a | n/a | 6.0 (patch_minimum, None) | 179.2 | 0.034 | n/a | 0.8911 / 0.9422 | 0.6218 / 0.7468 |
| 74 | 0.2873 | 0.2811 | 0.0073 | 0.5517 | 0.5493 | 0.0080 | n/a | 9.5 | 9.5 (measured, half) | 191.4 | 0.050 | n/a | 0.8972 / 0.9457 | 0.6333 / 0.7581 |
| 75 | 0.6943 | 0.6923 | 0.0075 | 0.8585 | 0.8609 | 0.0057 | 46.1 | 67.5 | 46.1 (measured, long) | 144.3 | 0.319 | 2.93 | 0.8685 / 0.9293 | 0.5866 / 0.7081 |
| 79 | 0.4470 | 0.4456 | 0.0080 | 0.6970 | 0.7003 | 0.0074 | n/a | 24.1 | 24.1 (measured, half) | 89.4 | 0.269 | n/a | 0.8055 / 0.8908 | 0.5295 / 0.6214 |
| 91 | 0.5615 | 0.5580 | 0.0079 | 0.7775 | 0.7762 | 0.0066 | 20.4 | 37.1 | 37.1 (measured, half) | 68.3 | 0.543 | 3.63 | 0.7624 / 0.8622 | 0.5123 / 0.5784 |
| 92 | 0.3315 | 0.3221 | 0.0079 | 0.5782 | 0.5850 | 0.0083 | n/a | 12.4 | 12.4 (measured, half) | 287.1 | 0.043 | n/a | 0.9289 / 0.9631 | 0.7071 / 0.8218 |
| 93 | 0.6703 | 0.6685 | 0.0075 | 0.1545 | 0.1477 | 0.0058 | 40.5 | n/a | 40.5 (measured, long) | 160.4 | 0.252 | n/a | 0.8800 / 0.9359 | 0.6032 / 0.7272 |
| 94 | 0.7185 | 0.7324 | 0.0074 | 0.1162 | 0.1047 | 0.0053 | 57.5 | n/a | 57.5 (measured, long) | 218.4 | 0.263 | n/a | 0.9087 / 0.9521 | 0.6570 / 0.7802 |
| 95 | 0.6753 | 0.6794 | 0.0076 | 0.7957 | 0.8030 | 0.0065 | 43.0 | 44.0 | 43.0 (measured, long) | 451.6 | 0.095 | 2.05 | 0.9535 / 0.9762 | 0.7855 / 0.8778 |

## 6. Windowed T1

| qubit | raw P1 | P1 corrected | P1 predicted | T1 measured (us) | T1 record (us) | rate ratio | in band |
|---|---|---|---|---|---|---|---|
| 59 | 0.8323 | 0.8373 | 0.8636 | 247.9 | 300.3 | 1.21 | yes |
| 71 | 0.8828 | 0.8890 | 0.8536 | 374.3 | 278.1 | 0.74 | yes |
| 72 | 0.8020 | 0.8464 | 0.8265 | 264.1 | 231.1 | 0.88 | yes |
| 73 | 0.7695 | 0.7977 | 0.8397 | 194.8 | 252.1 | 1.29 | yes |
| 74 | 0.7440 | 0.7506 | 0.8281 | 153.5 | 233.4 | 1.52 | yes |
| 75 | 0.8207 | 0.8363 | 0.8458 | 246.3 | 262.9 | 1.07 | yes |
| 79 | 0.8640 | 0.8711 | 0.8498 | 319.2 | 270.6 | 0.85 | yes |
| 91 | 0.7472 | 0.7540 | 0.6411 | 155.9 | 99.0 | 0.64 | yes |
| 92 | 0.6590 | 0.6678 | 0.8350 | 109.1 | 244.2 | 2.24 | no |
| 93 | 0.8732 | 0.8803 | 0.8833 | 345.5 | 354.7 | 1.03 | yes |
| 94 | 0.8313 | 0.8405 | 0.7724 | 253.5 | 170.5 | 0.67 | yes |
| 95 | 0.8243 | 0.8330 | 0.8652 | 241.0 | 304.1 | 1.26 | yes |

## 7. r_eff against r_crit

r_eff = **0.0974** (68 % [0.0879, 0.1022], 95 % [0.0757, 0.1154];
10000 bootstrap draws, 0 failed) on 338 delay windows
(ALAP B0_ref06_k1 explicit delays, leading excluded); S_T2 at the measured T2* 8.667 against 1.011 at the echo T2;
idle-weighted harmonic mean of T2*/T2_echo 0.061.  Preregistered r_crit 0.3285;
the day's 0.2788.

## 8. The circuits

| circuit | shots | accepted | ref hits | garbage expectation | P_ge | p_ref | f_clean reference [68 %] [95 %] | f_clean mixture [68 %] | C6 dev (info) | Aer f r=1 / r_eff / 0.174 | distance histogram |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B0_ref06_k1 | 4000 | 196 | 118 | 0.98 | 4.94e-197 | 0.8833 | 0.0404 [0.0366, 0.0445] [0.0332, 0.0486] | 0.0409 [0.0386, 0.0430] | 0.011 | 0.2114 / 0.0124 / 0.0413 | [118, 0, 39, 23, 1, 4, 2, 4, 4, 0, 1, 0, 0] |
| B1_ref07_k1 | 4000 | 160 | 124 | 0.98 | 1.33e-209 | 0.8891 | 0.0422 [0.0384, 0.0464] [0.0349, 0.0505] | 0.0418 [0.0401, 0.0433] | 0.010 | 0.2268 / 0.0269 / 0.0458 | [124, 0, 11, 13, 0, 5, 0, 2, 5, 0, 0] |
| B0_ref06_k4 | 4000 | 158 | 17 | 0.98 | 7.48e-16 | 0.1270 | 0.0385 [0.0287, 0.0510] [0.0212, 0.0636] | 0.0279 [0.0244, 0.0314] | 0.274 | 0.2379 / 0.0342 / 0.0555 | [17, 0, 21, 35, 4, 32, 13, 20, 1, 9, 6, 0, 0] |

B0_ref06_k4 is information only (C6 ruling: the estimators are not tolerance-calibrated at p_ref 0.13).

## 9. Budgets at the measured f_pool (information)

{"f": 0.041292968981847554, "D3prime_N4": {"B=0": 36200, "B=1": 86300}, "D3prime_execution_s": 120.6122586200001, "D3prime_total_coarse_shots": 359207, "D3pp_H0_shots_per_k1": 3391, "D3pp_H0_execution_s": 22.82290582400001}
information: the signed family's 28 r = 1 circuits relabelled onto the pilot's patch at their own durations; r = 2, 3 excluded (not rebuilt in this family)

## 10. Honest limits

- r_eff is one number for a patch whose per-qubit ratios may spread an order of magnitude (this patch: T2*/T2_echo
  0.013-0.543; fez: 0.070-1.209); the uniform-r axis is the one r_crit is defined on, and the per-qubit table is beside it.
- Aer's dephasing on a delay is exponential; the shape ratio (median 2.93; 2 exponential, 4 Gaussian) tests
  that with two lengths only.  A Gaussian decay makes the many short windows of the circuit less harmful than the long Ramsey
  windows suggest -- the direction in which the r-verdict could be pessimistic while the f-verdict is not; that is why f is primary.
- Two k = 1 circuits are not the 28-circuit family; the S2D bar is read on them as a pilot.  The k = 4 cell's f is information.
- The readout factor 0.82 of manual Step 4.4 is applied to both statistics and to the Aer predictions; the patch's measured
  readout survival is 0.8383.
- One job on one calibration content; a drift between submission and retrieval is reported (retrieval diff above), not corrected.
- The Ramsey inversion assumes no detuning (P0 = (1 + e^(-T/T2*))/2 >= 1/2).  9 of the
  12 qubits read P0 below 1/2 by more than 3 sigma at a window (59: ['long'], 71: ['long', 'half'], 72: ['long'], 73: ['long', 'half'], 74: ['long'], 79: ['long'], 92: ['long'], 93: ['half'], 94: ['half']): a coherent
  phase (frequency offset, or static ZZ with neighbours that are also in superposition) that the inversion reads as decay.  Where it
  applies, the T2* of rule S3 understates the dephasing time and r_eff is biased low; the Aer-equivalent ratio of the measured f
  (0.1721) is the model's reading of the circuit itself.  This is why f, not r_eff, is the decision statistic.

## 11. Criteria

| check | value | criterion | result |
|---|---|---|---|
| K1 preregistration committed before the submission; prereg = session = submission fingerprint; retrieval fingerprint recorded (a move is information) | prereg commit 2026-10-02T11:15:19-06:00, added 148e873 2026-10-02T11:41:39-06:00, submitted 2026-10-02 18:12:35 UTC; fingerprints equal True; retrieval match True | commit < submission, equal fingerprints, retrieval recorded | PASS |
| K2 one job DONE, usage_s recorded <= 60, preflight estimate <= 30 s, 8 counts files x 4000 shots, DD off and twirling off | jobs ['davv8504oijs73e88fvg'] ['DONE'], usage 12.0 s, estimate 9.04 s, counts ok True, options off True | all hold | PASS |
| K3 readout confusion of the patch (all-0 / all-1 pubs): smallest diagonal | 0.942 | >= 0.9 | PASS |
| K4 decoder round trip over every accepted string of the three coarse pubs | 0 mismatches over 45 strings | 0 | PASS |
| K5 idle tests (reference record: the prereg's patch record) | T2* measured 9/12; P0 <= echo bound + 3 sigma at both windows 12/12; 1/T1 in [0.5, 2.0] x record 11/12; r_eff 0.0974 68 % [0.0879, 0.1022] 95 % [0.0757, 0.1154] | >= 10 of 12 each; r_eff finite with both intervals | FAIL |
| K6 circuits: exactness of the three coarse circuits at build, ALAP scheduling asserted, idle-pub op multisets as intended, dry-run gate PASS | exact True (max |d| 5.7e-13), alap True, ops True, dry run PASS | all hold | PASS |
| K7 every preregistered Aer cell present with strided seeds; r = 1 B0_ref06_k1 within 25 % of S2D_levers' L1_seed_alap cell (mapping reproduced) | cells True; day 0.2114 vs 0.2170 (dev 0.026) | present, strided, <= 0.25 | PASS |
| K8 data.decision complete and reproduces the preregistered rule from the recorded intervals | missing []; decision NO-GO, recomputed NO-GO | complete and equal | PASS |
| K9 pytest -q tests and scripts/check_package.py | pytest: 233 passed, 2 skipped, 10 warnings in 405.72s (0:06:45); check_package rc 0 | all pass | PASS |
