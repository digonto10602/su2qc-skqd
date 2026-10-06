# Gate K1_rehearsal_dryrun -- the 2x3 clean-fraction pilot, dry run (path check on the FakeKingston snapshot)

**Status: PASS** -- `scripts/gate_K1_2x3_fpilot.py --stage assemble --counts ../../../../tmp/claude-1000/-home-digimonk-Projects-su2qc-skqd-v0-1-0/75c713a1-f3d1-426c-9cbd-0d1bee19756d/scratchpad/k1dry/counts --dry-run`.
Runtime 11 s.  Every number below is computed by the script from the raw counts and from `../../../../tmp/claude-1000/-home-digimonk-Projects-su2qc-skqd-v0-1-0/75c713a1-f3d1-426c-9cbd-0d1bee19756d/scratchpad/k1dev/prereg_38012b45ebcd2366.json`
and is stored in `validation/K1_rehearsal_dryrun.json`.  Prompt in force: `prompts/27_2x3_substantial_result_strategy.md`
stage 0b; owner decision `data/owner_decision_20261005_k1_2x3_fpilot.md`.

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on f or on the decision (a NO-GO pilot is a PASS gate). a PATH CHECK, not a prediction: local Aer on the FakeKingston snapshot (AerSimulator.from_backend through h0_submit.py's dry-run path) at a few shots per coarse pub under the 30-minute rule; its f numbers carry no information about the device.

## 1. Live block

| item | value |
|---|---|
| job id(s) / status | ['67fff243-f8b0-4e69-83b1-ed45e5eb8e44'] / ['DONE'] |
| usage (s) | 0.0 |
| preflight estimate (s) | None (preregistered 182.45) |
| fingerprint at prereg / submission / retrieval | `38012b45ebcd2366` / `n/a` / `n/a` |
| prereg match at submission / retrieval | None / None |
| retrieval diff | None |
| prereg added / submitted | None None / None |
| account after | None s used, None s left |
| sampler options | {'default_shots': 1, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |

## 2. Reference hits and the clean fraction

| circuit | shots | accepted | reference hits | garbage expectation N a/dim | P(>= hits | garbage) | f_hit [95 %] | f_hat_ideal [95 %] |
|---|---|---|---|---|---|---|---|
| B0_ref117_k1 | 400 | 400 | 372 | 0.000 | 0 | 1.222e+00 [1.101e+00, 1.352e+00] | 1.096e+00 [9.870e-01, 1.213e+00] |
| B1_ref29_k1 | 400 | 400 | 378 | 0.000 | 0 | 1.241e+00 [1.119e+00, 1.373e+00] | 1.113e+00 [1.004e+00, 1.231e+00] |

Pooled over the two circuits: **750 reference hits against 0.001 expected from
garbage** (P(>= observed | garbage only) = 0); f_hit =
1.232e+00 (68 % [1.187e+00, 1.278e+00], 95 % [1.145e+00, 1.323e+00]); f_hat_ideal = f_hit / r_nc =
1.104e+00 (95 % [1.027e+00, 1.186e+00]), r_nc = 1.1151.

## 3. Decision (preregistered)

**GO-B** (point class GO-B; 95 % ends GO-B / GO-B;
firm: True).  Rule: Statistic: f_hat_ideal = f_hit / r_nc (owner decision 1a, 2026-10-05), f_hit = the pooled reference-string clean fraction of the two k = 1 circuits (pooled_reference_string_test, readout factor 0.82, garbage expectation N a / dim subtracted), r_nc read from data/cf_trajectories/r_nc.json. GO-B if f_hat_ideal >= 1e-3 (a Tier-B 2x3 run costs <= 2e7 shots per sector); GO-A if 3e-4 <= f_hat_ideal < 1e-3 (Tier A only); NO-GO below 3e-4 (prompts/27 stage 0b).  The class is read on the point value; the classes of the 95 % (Garwood) interval ends are reported beside it and the decision is called firm when all three agree.  f_hit is reported beside f_hat_ideal.

r_nc is a gate-noise value (gate CF_traj, the A6 gate-only channel).  Under IBM idle dephasing the A5 model gives f_hit < f_ideal (r < 1 at both T2 ends), so dividing f_hit by r_nc = 1.115 can only LOWER the estimate there: the correction is conservative on this device.

## 4. The preregistered prediction bracket

| circuit | f end | f | expected reference hits |
|---|---|---|---|
| B0_ref117_k1 | f_gates_layout (no idle) | 6.067e-06 | 0.557 |
| B0_ref117_k1 | f_idle_aware_xy4 echo (2x2 transfer) | 2.978e-16 | 0.0954 |
| B0_ref117_k1 | f_idle_aware echo | 1.056e-16 | 0.0954 |
| B0_ref117_k1 | f_idle_aware_xy4 0.174 (2x2 transfer) | 1.052e-37 | 0.0954 |
| B0_ref117_k1 | f_idle_aware 0.174 | 3.733e-38 | 0.0954 |
| B1_ref29_k1 | f_gates_layout (no idle) | 6.088e-06 | 0.559 |
| B1_ref29_k1 | f_idle_aware_xy4 echo (2x2 transfer) | 3.044e-16 | 0.0954 |
| B1_ref29_k1 | f_idle_aware echo | 1.080e-16 | 0.0954 |
| B1_ref29_k1 | f_idle_aware_xy4 0.174 (2x2 transfer) | 1.117e-37 | 0.0954 |
| B1_ref29_k1 | f_idle_aware 0.174 | 3.962e-38 | 0.0954 |

## 5. Readout

Smallest confusion diagonal 0.8470 (qubit 92) over the 20 measured qubits;
survival product 0.6123.

## 6. Honest limits

- Two circuits, one calibration content, one job: the number is a pilot reading for this day's patch, not a device constant.
- The XY4 entries of the bracket are a 2x2 transfer; the f_hit statistic counts near-clean shots as well as clean ones
  (gate CF_traj), which the r_nc division corrects for gate noise only.
- At the expected f the counts are dominated by Poisson noise on a handful of hits; the 95 % interval, not the point, says
  what the data exclude.

## 7. Criteria

| check | value | criterion | result |
|---|---|---|---|
| K1 preregistration before data | n/a (dry run) | device run only | PASS |
| K2 one job DONE, usage <= 300 s, estimate <= 300 s, 4 counts files x 1e5 shots, DD/twirling off | n/a (dry run) | device run only | PASS |
| K3 readout (dry run: agreement with the snapshot's readout model within 3 binomial sigma, the prompts/21a form; the device criterion >= 0.9 is evaluated only on device counts) | 20/20 qubits within 3 sigma; min diagonal 0.8470 (information) | all within 3 sigma | PASS |
| K4 decoder round trip over every accepted string of the coarse pubs | 0 mismatches over 16 strings | 0 | PASS |
| K5 circuits: exactness vs the exact Krylov state (< 1e-10, leakage < 1e-9) before and after T3, ALAP with no moved op and duration = unscheduled T_total, DD statevector = base, no pulses in leading / trailing windows, kingston basis | 2/2; max |d| 2.6e-12, max leak 2.0e-13 | all hold | PASS |
| K6 dry-run gate PASS | n/a (this is the dry run) | device run only | PASS |
| KD noiseless path check of the coarse pubs: every shot accepted into its sector, reference hits within 3 binomial sigma of N p_ref, pooled 0.82 x f_hit 95 % interval contains 1 (a clean run) | B0_ref117_k1: z 0.13, all accepted True; B1_ref29_k1: z 1.29, all accepted True; 0.82 f_hit 95 % [0.939, 1.085] | all hold | PASS |
| K7 data.decision complete and the decision recomputed from the recorded rows | complete True; decision GO-B (recomputed GO-B) | complete and equal | PASS |
| K8 pytest -q tests and scripts/check_package.py | n/a (--skip-tests) | all pass | PASS |
