# DRY RUN (laptop path check, reduced size): Campaign 33 token C3_SEL (class 3): optional: Selene (QuEST, IdealErrorModel) on the QIR export of the 4 Stage-E circuits

**Status: FAIL** — `python scripts/campaign33.py --token C3_SEL --dry-run`.  Environment: Python 3.12.14, numpy 2.5.3, scipy None, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 17:46:09 MDT.  Runtime 1 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Selene (selene-sim, Quest statevector simulator, IdealErrorModel) on the QIR export: UNAVAILABLE (FileNotFoundError: [Errno 2] No such file or directory: '/home/digimonk/Projects/su2qc-skqd-v0.1.0/data/campaign33/qir/B0_ref25_k1.ll'); device engine unavailable (requested CPU, available ['CPU']); GPU mode None; GPUs None; tasks None; wall 1 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot None; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': 'unavailable: ModuleNotFoundError', 'qiskit_aer': 'unavailable: ModuleNotFoundError', 'numpy': '2.5.3', 'scipy': 'unavailable: ModuleNotFoundError', 'python': '3.12.14'}.  Phases (s): engine_setup_s 0.7.

## Notes

- C3_SEL is DROPPED by data/campaign33/engines.json (Selene's QIR front end (qir-qis 0.1.11) rejects `__quantum__qis__read_result__body`, which pytket-qir 2.0.2 emits for every measurement in every profile (and `__quantum__qis__phasedx__body` unless rebased): the QIR route of prompts/33 A6 does not run; a HUGR/Guppy route would be a new conversion, not built here); its job is not requested on Perlmutter
- the engine could not be set up: FileNotFoundError: [Errno 2] No such file or directory: '/home/digimonk/Projects/su2qc-skqd-v0.1.0/data/campaign33/qir/B0_ref25_k1.ll'

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested engine (CPU, its own env) | Selene (selene-sim, Quest statevector simulator, IdealErrorModel) on the QIR export: UNAVAILABLE (FileNotFoundError: [Errno 2] No such file or directory: '/home/digimonk/Projects/su2qc-skqd-v0.1.0/data/campaign33/qir/B0_ref25_k1.ll') | the engine ran | FAIL |
| S2 wall time inside the walltime budget | 1 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': False, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C3_SEL.json`.
