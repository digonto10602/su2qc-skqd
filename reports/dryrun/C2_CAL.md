# DRY RUN (laptop path check, reduced size): Campaign 33 token C2_CAL (class 2): 21-qubit timing ladder {8,32,128,512} on B0_ref117_k1 (IBM-T0), Kraus vs PTA, cuStateVec vs batched; sizes C2_*

**Status: PASS** — `python scripts/campaign33.py --token C2_CAL --dry-run`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 17:03:02 MDT.  Runtime 348 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 348 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot None; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '2.5.2', 'qiskit_aer': '0.17.2', 'numpy': '2.5.2', 'scipy': '1.18.0', 'python': '3.12.14'}.  Phases (s): ladder_s 346.2.

## Timing ladder (I-ECHO on IBM-T0 B0_ref117_k1)

| representation|mode | shots | s | s/shot | accepted |
|---|---|---|---|---|
| kraus|cpu | 1 | None | None | None |
| kraus|cpu | 2 | None | None | None |
| kraus|cpu | 6 | None | None | None |
| pta|cpu | 1 | 61.45 | 61.45 | 0 |
| pta|cpu | 2 | None | None | None |
| pta|cpu | 6 | None | None | None |

## Kraus vs PTA agreement

| mode | kraus [acc, N] | pta [acc, N] | z | agree 3 sigma |
|---|---|---|---|---|
| cpu | None | None | None | None |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P4 Kraus vs PTA accepted fractions within 3 sigma at >= 512 shots (else kraus_only, still PASS) | {'cpu': None} | <= 3 sigma, or representation kraus_only | True |
| P5 timing ladder >= 2 points per mode | {'kraus|cpu': 0, 'pta|cpu': 1} | >= 2 per (representation, mode) | False |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 348 s | <= min(walltime 2700 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': False, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C2_CAL.json`.
