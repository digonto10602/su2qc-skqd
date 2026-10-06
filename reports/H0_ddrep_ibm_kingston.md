# Gate H0_ddrep -- XY4 replication and the T1-collapse mechanism, ibm_kingston

**Status: PASS** -- `scripts/gate_H0_ddrep.py --stage assemble --counts data/hardware/H0_ddrep_ibm_kingston/counts --out H0_ddrep`.
Runtime 422 s.  Every number below is computed by the script from the raw counts and from `data/hardware/H0_ddrep_prep/prereg_cb40a250fb24387d.json` and is
stored in `validation/H0_ddrep.json`.  Prompt in force: `prompts/32_2x2_dd_replication_and_T1_mechanism.md (part A)`; owner decision `data/owner_decision_20261006_A_then_B.md`.

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on R1, R2, C1, the classes or the mechanism reading.

## 1. Preregistration

`data/hardware/H0_ddrep_prep/prereg_cb40a250fb24387d.json`, written 2026-10-06 06:29:26 UTC at commit `4f0e87b` on the patch record `data/hardware/H0_ddrep_prep/calibration_20261006T0501Z.json`
(fingerprint `cb40a250fb24387d2caed751bc9cb8c2b15378a67471fc93da873e057d6ee6e4`).  Patch [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95] (reproduced: True); hot qubits of M4
[91, 95]; 20 pubs x 6000 shots; execution estimate 34.04 s.

## 2. Live block

| item | value |
|---|---|
| job id(s) / status | ['db29p6nr11fs7396e4ig'] / ['DONE'] |
| usage (s) | 37.0 |
| preflight estimate (s) | 34.04016000000003 |
| fingerprint at prereg / submission / retrieval | `cb40a250fb24387d` / `cb40a250fb24387d` / `cb40a250fb24387d` |
| prereg match at submission / retrieval | True / True |
| retrieval diff | None |
| prereg commit time / submitted | 2026-10-06T00:25:53-06:00 (added in cd9ce122616a268bf3204e306b5d7ce664284fff, 2026-10-06T00:29:41-06:00) / 2026-10-06 07:00:40 UTC |
| account usage before / after | 102 s (498 left) / 139 s (461 left) |
| sampler options | {'default_shots': 6000, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |

## 3. The seven cells

| cell | accepted | ref hits | garbage exp. | excess X | f_pool [95 %] | R = X_i/X_0 | R 95 % | R bootstrap 95 % | null e^-S_DD | class | pulses (2 circuits) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T0 | 1134 | 716 | 2.93 | 713.1 | 0.0818 [0.0758, 0.0881] | 1.000 | n/a | n/a | 1.000 | - | 0 |
| T1 | 785 | 464 | 2.93 | 461.1 | 0.0529 [0.0481, 0.0581] | 0.647 | [0.575, 0.727] | [0.574, 0.725] | 0.841 | INTERMEDIATE | 1724 |
| T3 | 981 | 641 | 2.93 | 638.1 | 0.0732 [0.0675, 0.0792] | 0.895 | [0.804, 0.996] | [0.803, 0.994] | 0.954 | INTERMEDIATE | 488 |
| M1 | 859 | 565 | 2.93 | 562.1 | 0.0645 [0.0591, 0.0701] | 0.788 | [0.706, 0.880] | [0.703, 0.882] | 0.841 | INTERMEDIATE | 1724 |
| M2 | 974 | 578 | 2.93 | 575.1 | 0.0659 [0.0606, 0.0717] | 0.806 | [0.723, 0.900] | [0.723, 0.901] | 0.922 | INTERMEDIATE | 778 |
| M3 | 997 | 636 | 2.93 | 633.1 | 0.0726 [0.0669, 0.0786] | 0.888 | [0.798, 0.988] | [0.798, 0.987] | 0.922 | INTERMEDIATE | 778 |
| M4 | 1322 | 823 | 2.93 | 820.1 | 0.0940 [0.0876, 0.1009] | 1.150 | [1.040, 1.271] | [1.042, 1.274] | 0.880 | INTACT | 1228 |

Per circuit:

| cell | circuit | accepted | ref hits | f reference [95 %] | f mixture [68 %] | C6 dev (info) | pulses |
|---|---|---|---|---|---|---|---|
| T0 | B0_ref06_k1 | 645 | 380 | 0.0871 [0.0784, 0.0965] | 0.0902 [0.0875, 0.0928] | 0.035 | 0 |
| T0 | B1_ref07_k1 | 489 | 336 | 0.0765 [0.0683, 0.0853] | 0.0766 [0.0744, 0.0787] | 0.002 | 0 |
| T1 | B0_ref06_k1 | 426 | 221 | 0.0505 [0.0439, 0.0578] | 0.0513 [0.0490, 0.0536] | 0.016 | 862 |
| T1 | B1_ref07_k1 | 359 | 243 | 0.0552 [0.0483, 0.0628] | 0.0574 [0.0555, 0.0592] | 0.039 | 862 |
| T3 | B0_ref06_k1 | 541 | 339 | 0.0777 [0.0694, 0.0866] | 0.0782 [0.0758, 0.0806] | 0.007 | 244 |
| T3 | B1_ref07_k1 | 440 | 302 | 0.0687 [0.0610, 0.0771] | 0.0700 [0.0679, 0.0720] | 0.019 | 244 |
| M1 | B0_ref06_k1 | 461 | 285 | 0.0652 [0.0577, 0.0735] | 0.0641 [0.0618, 0.0663] | 0.018 | 862 |
| M1 | B1_ref07_k1 | 398 | 280 | 0.0637 [0.0563, 0.0718] | 0.0623 [0.0603, 0.0642] | 0.022 | 862 |
| M2 | B0_ref06_k1 | 521 | 276 | 0.0632 [0.0558, 0.0713] | 0.0675 [0.0650, 0.0700] | 0.069 | 388 |
| M2 | B1_ref07_k1 | 453 | 302 | 0.0687 [0.0610, 0.0771] | 0.0715 [0.0693, 0.0735] | 0.040 | 390 |
| M3 | B0_ref06_k1 | 512 | 302 | 0.0692 [0.0614, 0.0776] | 0.0733 [0.0709, 0.0756] | 0.060 | 388 |
| M3 | B1_ref07_k1 | 485 | 334 | 0.0760 [0.0679, 0.0848] | 0.0767 [0.0745, 0.0788] | 0.009 | 390 |
| M4 | B0_ref06_k1 | 712 | 408 | 0.0935 [0.0845, 0.1033] | 0.0972 [0.0943, 0.1000] | 0.039 | 614 |
| M4 | B1_ref07_k1 | 610 | 415 | 0.0945 [0.0855, 0.1043] | 0.0964 [0.0939, 0.0988] | 0.020 | 614 |

Classes per circuit cell on R_i = X_i / X_0 (gate_H0_ddtest.ratio_interval, Poisson 95 %): COLLAPSED iff R_hi95 < 0.25; INTACT iff R_lo95 > 1; INTERMEDIATE otherwise.  If X_i <= 0 (no excess reference hits) the interval is [0, U_i / L_0] with U_i = the Garwood 97.5 % upper limit of the cell's pooled reference count minus its garbage expectation and L_0 = the Garwood 2.5 % lower limit of T0's count minus T0's garbage expectation (executor addition fixed before data: the ratio_interval of gate_H0_ddtest is undefined there).

## 4. Replication verdicts (P6)

- R1 gain replicated (T3 qualifies under the H0_ddtest rule): **False**.
- R2 magnitude consistent: **False** -- ln R_new -0.1111 vs ln R_old 1.0364, |difference|
  1.1476 against the tolerance 0.1622.
- C1 collapse replicated (T1 COLLAPSED): **False**.
- Signed bar on T3 (information): on f_hit **NO-GO**; on f_hat_ideal = f_hit / r_nc (1.1151)
  **NO-GO** (f_hat_ideal 0.0656, 95 % [0.0599, 0.0717]).

## 5. Mechanism (P5)

| cell | observed class | H_A predicts (match) | H_B predicts (match) | H_D predicts (match) |
|---|---|---|---|---|
| T1 | INTERMEDIATE | COLLAPSED (no) | COLLAPSED (no) | COLLAPSED (no) |
| M1 | INTERMEDIATE | INTACT (no) | COLLAPSED (no) | COLLAPSED (no) |
| M2 | INTERMEDIATE | not INTACT, and R_M2 < R_M3 (yes) | INTACT (no) | INTACT (no) |
| M3 | INTERMEDIATE | INTACT (no) | INTACT (no) | INTACT (no) |
| M4 | INTACT | not INTACT (no) | not INTACT (no) | INTACT (yes) |

Reading (preregistered rule): **no single hypothesis**.  Cells matched per hypothesis: H_A 1/5, H_B 0/5, H_D 1/5.
M3 vs M2 (first-order compensation on the runtime timing): ln(R_M3/R_M2) = 0.0961 +- 0.0576,
z = 1.67 (compensation matters: True).  M3 vs T3 (information):
ln = -0.0079 +- 0.0561.

## 6. Pulse trains (P4)

| qubit | P1 XX-8 | P1 XX-32 | P1 XX-128 | P1 XpXm-128 | epsilon (rad) [68 %] | c per pulse [68 %] | x_error record | c / x_error |
|---|---|---|---|---|---|---|---|---|
| 59 | 0.0064 | 0.0663 | 0.8735 | 0.0302 | 0.0181 [0.0180, 0.0182] | 1.98e-04 [1.7e-04, 2.2e-04] | 1.88e-04 | 1.05 |
| 71 | 0.0068 | 0.0483 | 0.7569 | 0.0917 | 0.0148 [0.0147, 0.0150] | 7.08e-04 [6.7e-04, 7.4e-04] | 1.48e-04 | 4.79 |
| 72 | 0.0126 | 0.0759 | 0.9307 | 0.0248 | 0.0195 [0.0193, 0.0196] | 1.02e-04 [6.6e-05, 1.4e-04] | 1.38e-04 | 0.74 |
| 73 | 0.0136 | 0.0831 | 0.9218 | 0.0556 | 0.0186 [0.0185, 0.0187] | 3.50e-04 [3.2e-04, 3.8e-04] | 2.12e-04 | 1.65 |
| 74 | 0.0093 | 0.0924 | 0.9762 | 0.0355 | 0.0204 [0.0203, 0.0206] | 2.18e-04 [2.0e-04, 2.4e-04] | 2.37e-04 | 0.92 |
| 75 | 0.0063 | 0.0537 | 0.8353 | 0.0280 | 0.0173 [0.0172, 0.0174] | 1.81e-04 [1.6e-04, 2.1e-04] | 1.46e-04 | 1.24 |
| 79 | 0.0034 | 0.0423 | 0.7670 | 0.0368 | 0.0159 [0.0158, 0.0160] | 2.78e-04 [2.5e-04, 3.0e-04] | 2.38e-04 | 1.17 |
| 91 | 0.0077 | 0.0625 | 0.9366 | 0.1373 | 0.0171 [0.0170, 0.0173] | 1.08e-03 [1.0e-03, 1.1e-03] | 2.19e-04 | 4.92 |
| 92 | 0.0019 | 0.0284 | 0.7636 | 0.0913 | 0.0149 [0.0148, 0.0150] | 7.45e-04 [7.1e-04, 7.9e-04] | 3.33e-04 | 2.24 |
| 93 | 0.0132 | 0.0755 | 0.9601 | 0.0475 | 0.0196 [0.0195, 0.0197] | 2.86e-04 [2.6e-04, 3.1e-04] | 1.94e-04 | 1.48 |
| 94 | 0.0004 | 0.0691 | 0.9248 | 0.0444 | 0.0189 [0.0187, 0.0190] | 3.67e-04 [3.3e-04, 4.0e-04] | 1.72e-04 | 2.14 |
| 95 | 0.0144 | 0.0828 | 0.9511 | 0.0655 | 0.0190 [0.0189, 0.0191] | 4.25e-04 [3.9e-04, 4.5e-04] | 1.51e-04 | 2.81 |

Readings: H_A pattern True (epsilon >= 0.01 on 12 qubits, XX-128 - XpXm-128 > 0.05 on
12); H_B pattern False; H_D pattern False (c > 3 x_error on
['71', '91'], hot ['91', '95']).  

Rule: Executor operationalisation of P4's table (fixed before data): per qubit P1 = readout-corrected P(1) (p - (1 - P00)) / (P00 + P11 - 1) with the job's own confusion diagonal; c_q = (P1(XpXm-128) - P1(XX-8)) / 120; floor_n = P1(XX-8) + (n - 8) c_q; epsilon_q = argmin over [0, pi/8] (grid 1e-4 rad) of sum_{n in 8, 32, 128} (P1(XX-n) - floor_n - sin^2(n epsilon / 2))^2; 68 % intervals by a parametric bootstrap (2000 draws, seed 32: binomial train and confusion counts).  H_A pattern: epsilon_q >= 0.01 on >= 6 of 12 qubits AND P1(XX-128) - P1(XpXm-128) > 0.05 on >= 6 of 12 qubits.  H_B pattern ('all four at the floor'): on every qubit P1(XX-128) - P1(XpXm-128) <= 0.05 and P1(XX-32) - floor_32 <= 0.05.  H_D pattern: c_q > 3 x_error_q on at least one of the two hot qubits and c_q <= 3 x_error_q on every other qubit (x_error of the preregistered patch record).

## 7. The 2x3 IBM NO-GO (K0, recorded with this gate)

NO-GO for 2x3 on IBM Heron (ibm_kingston) on the K0 analysis: a model verdict, not a measurement: routed CZ 5659, ALAP 410.3 us, f_gates on the layout 6.069e-06,
f_idle_aware 1.057e-16 (echo) / 3.732e-38 (T2*), garbage reference hits
0.0954 per circuit at 100000 shots
(`reports/K0_2x3_ibm_heron_nogo.md`).  Every number above is computed from the calibration record named; none is a measurement on the device.  Option B (prompts/32) is the one measurement this verdict allows: the K1 pilot as an upper limit.

## 8. Readout

Smallest confusion diagonal 0.9462; preregistered live expectation min
0.9565 (qubit 72).

## 9. Honest limits

- One job, one patch, one calibration content; drift between submission and retrieval is reported, not corrected.
- The classes are preregistered thresholds on Poisson intervals, not fits; the reading rule names a hypothesis class, not a
  microscopic cause.
- The null ratios e^-S_DD assume the record's x error for every inserted pulse, and the record's x error is aliased to sx.
- The train fit assumes a coherent over-rotation epsilon plus an incoherent per-pulse cost on a floor anchored at XX-8; other
  coherent errors (axis tilt, detuning during the train) enter epsilon.
- Two k = 1 circuits are not a family-level statement.

## 10. Criteria

| check | value | criterion | result |
|---|---|---|---|
| D1 preregistration committed before the submission; prereg = submission fingerprint; retrieval fingerprint recorded (a move is information) | prereg commit 2026-10-06T00:25:53-06:00, added cd9ce12 2026-10-06T00:29:41-06:00, submitted 2026-10-06 07:00:40 UTC; fingerprints equal True; retrieval match True | commit < submission, equal fingerprints, retrieval recorded | PASS |
| D2 one job DONE, usage_s <= 45, preflight estimate <= 36 s, 20 counts files x 6000, DD off and twirling off, reserve.json with remaining - 45 >= max(300, 1.3 x K1 estimate) | jobs ['db29p6nr11fs7396e4ig'] ['DONE'], usage 37.0 s, estimate 34.04 s, counts ok True, options off True, reserve 453.0 s after A vs need 300.0 s: True | all hold | PASS |
| D3 readout confusion of the patch (all-0 / all-1 pubs): smallest diagonal | 0.9462 | >= 0.9 | PASS |
| D4 decoder round trip over every accepted string of the 14 coarse pubs | 0 mismatches over 58 strings | 0 | PASS |
| D5 circuits: 14/14 coarse circuits pass dd_checks (i)-(v) and dd_exactness; T0/T1/T3 byte-identical to H0_ddtest when patch_reproduced; the P3 identities hold; the train pubs' op lists are the declared trains; kingston basis | 14/14 circuits; reuse ok True (patch reproduced True); identities ok True; trains ok True; max |d| 5.7e-13 | all hold | PASS |
| D6 validation/H0_ddrep_dryrun.json PASS on the day's build | PASS (same build True) | PASS, same index and prereg fingerprint | PASS |
| D7 replication, mechanism, trains and k0_2x3_nogo complete; classes, R1, R2, C1 and the reading recomputed from the recorded intervals; k0 fields equal validation/K0_2x3_2x4.json's | missing []; recomputed equal True; k0 mismatches [] | complete, equal, none | PASS |
| D8 pytest -q tests and scripts/check_package.py | pytest: 342 passed, 19 skipped, 62 warnings in 414.91s (0:06:54); check_package rc 0 | all pass | PASS |
