# Gate K1_2x3_fpilot -- the 2x3 clean-fraction pilot, ibm_kingston

**Status: PASS** -- `scripts/gate_K1_2x3_fpilot.py --stage assemble --counts data/hardware/K1_2x3_ibm_kingston/counts`.
Runtime 422 s.  Every number below is computed by the script from the raw counts and from `data/hardware/K1_2x3_prep/prereg_99035ef05c36019e.json`
and is stored in `validation/K1_2x3_fpilot.json`.  Prompt in force: `prompts/27_2x3_substantial_result_strategy.md`
stage 0b; owner decision `data/owner_decision_20261005_k1_2x3_fpilot.md`.

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on f or on the decision (a NO-GO pilot is a PASS gate).

## 1. Live block

| item | value |
|---|---|
| job id(s) / status | ['db2avbe8v0ts73c2i8b0'] / ['DONE'] |
| usage (s) | 188.0 |
| preflight estimate (s) | 182.63120000000325 (preregistered 182.63) |
| fingerprint at prereg / submission / retrieval | `99035ef05c36019e` / `99035ef05c36019e` / `99035ef05c36019e` |
| prereg match at submission / retrieval | True / True |
| retrieval diff | None |
| prereg added / submitted | f8df126bdb37f05da090a38e607bed877bbd642e 2026-10-06T02:05:51-06:00 / 2026-10-06 08:22:03 UTC |
| account after | 327 s used, 273 s left |
| sampler options | {'default_shots': 100000, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |

## 2. Reference hits and the clean fraction

| circuit | shots | accepted | reference hits | garbage expectation N a/dim | P(>= hits | garbage) | f_hit [95 %] | f_hat_ideal [95 %] |
|---|---|---|---|---|---|---|---|
| B0_ref117_k1 | 100000 | 58 | 0 | 0.095 | 1 | -1.253e-06 [-1.253e-06, 4.721e-05] | -1.123e-06 [-1.123e-06, 4.233e-05] |
| B1_ref29_k1 | 100000 | 45 | 0 | 0.095 | 1 | -1.253e-06 [-1.253e-06, 4.721e-05] | -1.123e-06 [-1.123e-06, 4.233e-05] |

Pooled over the two circuits: **0 reference hits against 0.191 expected from
garbage** (P(>= observed | garbage only) = 1); f_hit =
-1.253e-06 (68 % [-1.253e-06, 1.084e-05], 95 % [-1.253e-06, 2.298e-05]); f_hat_ideal = f_hit / r_nc =
-1.123e-06 (95 % [-1.123e-06, 2.060e-05]), r_nc = 1.1151.

## 3. Decision (preregistered)

**NO-GO** (point class NO-GO; 95 % ends NO-GO / NO-GO;
firm: True).  Rule: Statistic: f_hat_ideal = f_hit / r_nc (owner decision 1a, 2026-10-05), f_hit = the pooled reference-string clean fraction of the two k = 1 circuits (pooled_reference_string_test, readout factor 0.82, garbage expectation N a / dim subtracted), r_nc read from data/cf_trajectories/r_nc.json. GO-B if f_hat_ideal >= 1e-3 (a Tier-B 2x3 run costs <= 2e7 shots per sector); GO-A if 3e-4 <= f_hat_ideal < 1e-3 (Tier A only); NO-GO below 3e-4 (prompts/27 stage 0b).  The class is read on the point value; the classes of the 95 % (Garwood) interval ends are reported beside it and the decision is called firm when all three agree.  f_hit is reported beside f_hat_ideal.

r_nc is a gate-noise value (gate CF_traj, the A6 gate-only channel).  Under IBM idle dephasing the A5 model gives f_hit < f_ideal (r < 1 at both T2 ends), so dividing f_hit by r_nc = 1.115 can only LOWER the estimate there: the correction is conservative on this device.

## 4. The preregistered prediction bracket

| circuit | f end | f | expected reference hits |
|---|---|---|---|
| B0_ref117_k1 | f_gates_layout (no idle) | 1.671e-05 | 1.37 |
| B0_ref117_k1 | f_idle_aware_xy4 echo (2x2 transfer) | 4.687e-15 | 0.0954 |
| B0_ref117_k1 | f_idle_aware echo | 1.662e-15 | 0.0954 |
| B0_ref117_k1 | f_idle_aware_xy4 0.174 (2x2 transfer) | 1.467e-34 | 0.0954 |
| B0_ref117_k1 | f_idle_aware 0.174 | 5.202e-35 | 0.0954 |
| B1_ref29_k1 | f_gates_layout (no idle) | 1.674e-05 | 1.37 |
| B1_ref29_k1 | f_idle_aware_xy4 echo (2x2 transfer) | 4.773e-15 | 0.0954 |
| B1_ref29_k1 | f_idle_aware echo | 1.693e-15 | 0.0954 |
| B1_ref29_k1 | f_idle_aware_xy4 0.174 (2x2 transfer) | 1.552e-34 | 0.0954 |
| B1_ref29_k1 | f_idle_aware 0.174 | 5.506e-35 | 0.0954 |

## 5. Readout

Smallest confusion diagonal 0.9358 (qubit 92) over the 20 measured qubits;
survival product 0.7105.

## 6. Honest limits

- <!-- k1_ddrep_note --> **The XY4 cell this job carries did not replicate on 2026-10-06** (gate H0_ddrep, status PASS, job db29p6nr11fs7396e4ig, `validation/H0_ddrep.json`): on the 2x2 patch the T3 (client XY4) gain was R = 0.895 [0.804, 0.996] (95 %, class INTERMEDIATE) against R = 2.819 [2.495, 3.185] on 2026-10-02 (`validation/H0_ddtest.json`); R1 False, R2 False (|ln R_new - ln R_old| = 1.148 > 0.162), and the no-DD baseline f_T0 = 0.0818 [0.0758, 0.0881] against 0.0400 on 2026-10-02, on the same QPYs.  K1 is run as built (owner decision: cell T3, unchanged), so the 'XY4 transfer' ends of the bracket in section 4, which multiply by the 2026-10-02 R, are not supported by that day's data (on 2026-10-06 T3 sat below the no-DD baseline: the 95 % interval of R excludes 1 from above).  The decision statistic f_hit does not use R.
- Two circuits, one calibration content, one job: the number is a pilot reading for this day's patch, not a device constant.
- The XY4 entries of the bracket are a 2x2 transfer; the f_hit statistic counts near-clean shots as well as clean ones
  (gate CF_traj), which the r_nc division corrects for gate noise only.
- At the expected f the counts are dominated by Poisson noise on a handful of hits; the 95 % interval, not the point, says
  what the data exclude.

## 7. Criteria

| check | value | criterion | result |
|---|---|---|---|
| K1 preregistration committed before the submission; prereg = session = submission fingerprint; retrieval fingerprint recorded (a move is information) | prereg added f8df126 2026-10-06T02:05:51-06:00, submitted 2026-10-06 08:22:03 UTC; fingerprints equal True; retrieval match True | commit < submission, equal fingerprints, retrieval recorded | PASS |
| K2 one job DONE, usage_s <= 300, preflight estimate <= 300 s, 4 counts files x 1e5 shots, DD off and twirling off | jobs ['db2avbe8v0ts73c2i8b0'] ['DONE'], usage 188.0 s, estimate 182.63 s, counts ok True, options off True | all hold | PASS |
| K3 readout confusion of the measured qubits (all-0 / all-1 pubs): smallest diagonal | 0.9358 | >= 0.9 | PASS |
| K4 decoder round trip over every accepted string of the coarse pubs | 0 mismatches over 99 strings | 0 | PASS |
| K5 circuits: exactness vs the exact Krylov state (< 1e-10, leakage < 1e-9) before and after T3, ALAP with no moved op and duration = unscheduled T_total, DD statevector = base, no pulses in leading / trailing windows, kingston basis | 2/2; max |d| 2.3e-12, max leak 2.1e-13 | all hold | PASS |
| K6 dry-run gate validation/K1_2x3_fpilot_dryrun.json PASS | PASS | PASS | PASS |
| K7 data.decision complete and the decision recomputed from the recorded rows | complete True; decision NO-GO (recomputed NO-GO) | complete and equal | PASS |
| K8 pytest -q tests and scripts/check_package.py | pytest: 342 passed, 19 skipped, 62 warnings in 414.53s (0:06:54); check_package rc 0 | all pass | PASS |
