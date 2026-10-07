# DRY RUN (laptop path check, reduced size): Campaign 33 token C3_LE (class 3): pytket-pecos H2-1LE local emulator (noiseless, CPU) on the 4 Stage-E circuits

**Status: PASS** — `python scripts/campaign33.py --token C3_LE --dry-run`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 17:48:58 MDT.  Runtime 169 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine pytket-quantinuum H2-1LE local emulator (pytket-pecos / quantum-pecos), state-vector, noiseless (CPU); device CPU (requested CPU, available ['CPU']); GPU mode None; GPUs None; tasks None; wall 169 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 55.22; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': 'unavailable: ModuleNotFoundError', 'qiskit_aer': 'unavailable: ModuleNotFoundError', 'numpy': '2.5.3', 'scipy': '1.18.1', 'python': '3.12.14'}.  Phases (s): engine_setup_s 3.2, ladder_s 55.0, sampling_s 110.4.

## C3_LE: pytket-quantinuum H2-1LE local emulator (pytket-pecos / quantum-pecos), state-vector, noiseless

| circuit | shots | states tested | max z | outside sector | reference hits |
|---|---|---|---|---|---|
| B0_ref25_k1 | 1 | 10 | 9.338 | 0 | 0 |
| B1_ref57_k1 | 1 | 8 | 0.3102 | 0 | 1 |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P8 per-state agreement with the exact distribution at 3 sigma (p_s >= 1e-3); the TV distance to C3_AER is computed at assembly | {'failures': 2, 'max_z': 9.337936376794625} | 0 failures | False |
| P9 every observed string decodes into the circuit's sector | {'B0_ref25_k1': 0, 'B1_ref57_k1': 0} | 0 outside | True |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested engine (CPU, its own env) | pytket-quantinuum H2-1LE local emulator (pytket-pecos / quantum-pecos), state-vector, noiseless (CPU) | the engine ran | PASS |
| S2 wall time inside the walltime budget | 169 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C3_LE.json`.
