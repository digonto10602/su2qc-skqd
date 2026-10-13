# DRY RUN (laptop path check, reduced size): Campaign 33 token C2_KCHK (class 2): prompts/33d R3: the GPU Kraus check on IBM-T0 B0_ref117_k1 (I-ECHO): Kraus and RM on cuStateVec, Kraus on Aer's native GPU kernels and on cuStateVec without fusion, Kraus and RM on the CPU in a separate process; raw counts; decides the class-2 representation

**Status: FAIL** — `python scripts/campaign33.py --token C2_KCHK --dry-run`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit a6e4c14, 2026-10-13 15:18:17 MDT.  Runtime 1152 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 1152 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 128.4; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '2.5.2', 'qiskit_aer': '0.17.2', 'numpy': '2.5.2', 'scipy': '1.18.0', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 0.9, gpu_arms_s 1148.7, cpu_process_s 1148.7.

## C2_KCHK arms (I-ECHO on IBM-T0 B0_ref117_k1)

| arm | engine | representation | shots | minimum | s/shot | mean weight | se |
|---|---|---|---|---|---|---|---|
| kraus_gpu_cusv | CPU stand-in for GPU custatevec | kraus | 2 | 2 | 126.1 | 9.5 | 0.5 |
| rm_gpu_cusv | CPU stand-in for GPU custatevec | rm | 2 | 2 | 128.4 | 10.5 | 0.5 |
| kraus_gpu_native | CPU stand-in for GPU native | kraus | 2 | 2 | 126.8 | 7.5 | 1.5 |
| kraus_gpu_cusv_nofusion | CPU stand-in for GPU custatevec_nofusion | kraus | 2 | 2 | 123.2 | 8 | 2 |
| kraus_cpu | CPU statevector (separate process) | kraus | 2 | 2 | 243.6 | 8 | 4 |
| rm_cpu | CPU statevector (separate process) | rm | 2 | 2 | 243.6 | 11 | 2 |

## Pairwise comparisons (P4a statistic, 3 sigma)

| pair | z mean weight | max |z| marginal | clbits outside | min visible marginal diff |
|---|---|---|---|---|
| kraus_gpu_cusv~kraus_cpu | 0.3721 | inf | [2, 9, 11] | 1.5 |
| rm_gpu_cusv~rm_cpu | -0.2425 | inf | [13, 17, 19] | 1.5 |
| rm_gpu_cusv~kraus_cpu | 0.6202 | inf | [10] | 1.5 |
| kraus_gpu_native~kraus_cpu | -0.117 | inf | [1, 2] | 1.5 |
| kraus_gpu_cusv_nofusion~kraus_cpu | 0 | inf | [2, 4, 7] | 1.5 |
| rm_cpu~kraus_cpu | 0.6708 | inf | [8] | 1.5 |
| kraus_gpu_cusv~rm_gpu_cusv | -1.414 | inf | [6, 10, 17] | 1.5 |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| K1 kraus_gpu_cusv vs kraus_cpu: bug_confirmed iff |z_w| > 3 (both outcomes PASS; the field is the decision) | {'z_w': 0.3721042037676254, 'w': [9.5, 8.0], 'bug_confirmed': False} | decided (both arms sampled) | True |
| K2 production representation: rm iff rm_gpu_cusv agrees with rm_cpu and kraus_cpu (|z_w| <= 3, no marginal beyond 3 sigma), else blocked | {'production_representation': 'blocked', 'z_w': {'rm_gpu_cusv~rm_cpu': -0.24253562503633297, 'rm_gpu_cusv~kraus_cpu': 0.6201736729460423}, 'clbits_outside': {'rm_gpu_cusv~rm_cpu': [13, 17, 19], 'rm_gpu_cusv~kraus_cpu': [10]}} | decided (all three arms sampled) | True |
| K3 validated Kraus GPU path (reference arm of the cells): first of native / cuStateVec-no-fusion with |z_w| <= 3 against kraus_cpu, else none | {'validated_kraus_gpu_path': 'kraus_gpu_native', 'z_w': {'kraus_gpu_native': -0.11704114719613057, 'kraus_gpu_cusv_nofusion': 0.0}} | recorded | True |

## Notes

- dry run: CPU only, the Pauli-twirled representation stands in for every arm (Kraus on this CPU costs minutes per call), 2 shots per arm -- a path check of the arms, the CPU subprocess, the raw counts and the decision block, not a measurement

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P0 raw counts of every arm stored (sum of counts = shots_done) | {'kraus_gpu_cusv': [2, 2], 'rm_gpu_cusv': [2, 2], 'kraus_gpu_native': [2, 2], 'kraus_gpu_cusv_nofusion': [2, 2], 'kraus_cpu': [2, 2], 'rm_cpu': [2, 2]} | equal | PASS |
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 1152 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | FAIL |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C2_KCHK.json`.
