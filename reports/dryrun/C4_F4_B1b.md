# DRY RUN (laptop path check, reduced size): Campaign 33 token C4_F4_B1b (class 4): E7(0.10) x O0, S3-quota half b, B=1 (1e5)

**Status: PASS** — `python scripts/campaign33.py --token C4_F4_B1b --dry-run`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 17:18:34 MDT.  Runtime 285 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 285 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 16.74; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '2.5.2', 'qiskit_aer': '0.17.2', 'numpy': '2.5.2', 'scipy': '1.18.0', 'python': '3.12.14'}.  Phases (s): sampling_s 279.4, bootstrap_s 0.0, analysis_s 1.0.

## C4_F4_B1b: E7_0.10 x NAT-O0, B=1, s3quota half b

| shots | |B_all| | E_R - E0 | certificate | width | E0 inside | recall S999 | W | f_hit (k=1) | f_hat_ideal 95 % |
|---|---|---|---|---|---|---|---|---|---|
| 16 | 7 | 0.6678 | weinstein | 1.456 | True | 0.07368 | 0.7845 | 0.137 | [0.00311, 0.6847] |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P13 E_R >= E0 - 1e-9 everywhere, prefixes nested (CV0), E0 inside the certificate of ruling 2 at N | {'variational': True, 'cv0': True, 'E0_inside': True, 'certificate': 'weinstein'} | all true | True |

## Notes

- dry run: 4 of 12 circuits used (['B1_ref27_k1', 'B1_ref27_k2', 'B1_ref57_k1', 'B1_ref57_k4'])

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 285 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | {'B1_ref57_k1': 4, 'B1_ref57_k4': 4, 'B1_ref27_k1': 4, 'B1_ref27_k2': 4} | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C4_F4_B1b.json`.
