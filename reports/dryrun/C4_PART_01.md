# DRY RUN (laptop path check, reduced size): Campaign 33 token C4_PART_01 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_01.json in the requested commit (frun part i of n, dropped f-cells, or a cv3 equal-shots sample), written by scripts/campaign33_resize.py

**Status: PASS** — `python scripts/campaign33.py --token C4_PART_01 --dry-run`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 7186860, 2026-10-11 12:39:25 MDT.  Runtime 258 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 258 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 10.15; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '2.5.2', 'qiskit_aer': '0.17.2', 'numpy': '2.5.2', 'scipy': '1.18.0', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 0.8, sampling_s 253.9, bootstrap_and_readout_s 1.2, analysis_s 1.3.

## C4_PART_01: E7_0.07 x NAT-O0, B=1, plan, part 2 of 2

| shots | |B_all| | E_R - E0 | certificate | width | E0 inside | recall S999 | W | f_hit (k=1) | f_hat_ideal 95 % |
|---|---|---|---|---|---|---|---|---|---|
| 25 | 6 | 0.8261 | weinstein | 1.62 | True | 0.05263 | 0.766 | -1.045e-06 | [-9.375e-07, 0.6044] |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P13 (part 2 of 2) E_R >= E0 - 1e-9 on this part's shots (CV0 and the certificate are read at assembly on the merged parts) | {'variational': True, 'E0_inside_information': True} | variational | True |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P0 slot content written for this slot (prompts/33b R4: seed_token_index = the index of the run's own F token, or the slot's own for f-cells; slot = this token) | {'seed_token_index': 23, 'expected': 23, 'rule': "the run's own F token", 'slot': 'C4_PART_01', 'this_token': 'C4_PART_01', 'content': 'frun', 'token_matches_run': True} | equal | PASS |
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 258 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C4_PART_01.json`.
