# DRY RUN (laptop path check, reduced size): Campaign 33 token C2_KCHK (class 2): prompts/33d R3 + 33e R2: the GPU Kraus check on IBM-T0 B0_ref117_k1 (I-ECHO); run 2 (default, --content cpu_only): Kraus and RM on the CPU in a separate process on the step's CPUs beside a 128-shot RM cuStateVec anchor, the four GPU arms read from run 1 (job 59780907, archived); raw counts; decides the class-2 representation

**Status: PASS** — `python scripts/campaign33.py --token C2_KCHK --dry-run`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 39e0516, 2026-10-15 12:22:02 MDT.  Runtime 936 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 936 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 114.5; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 0.8, gpu_anchor_s 232.9, cpu_process_s 933.0.

## C2_KCHK run 2 arms (I-ECHO on IBM-T0 B0_ref117_k1); GPU arms read from run 1

| arm | run | engine | representation | shots | minimum | s/shot | mean weight | se |
|---|---|---|---|---|---|---|---|---|
| kraus_gpu_cusv | 1 | GPU custatevec | kraus | 256 | 256 | 1.92 | 2.996 | 0.2351 |
| rm_gpu_cusv | 1 | GPU custatevec | rm | 512 | 512 | 0.4172 | 7.434 | 0.09964 |
| kraus_gpu_native | 1 | GPU native | kraus | 256 | 64 | 2.223 | 3.566 | 0.2466 |
| kraus_gpu_cusv_nofusion | 1 | GPU custatevec_nofusion | kraus | 128 | 32 | 5.047 | 1.141 | 0.2187 |
| rm_gpu_cusv_anchor | 2 | CPU stand-in for GPU custatevec | rm | 2 | 2 | 114.5 | 8 | 1 |
| kraus_cpu | 2 | CPU statevector (separate process) | kraus | 2 | 2 | 206.7 | 8 | 4 |
| rm_cpu | 2 | CPU statevector (separate process) | rm | 2 | 2 | 188.3 | 11 | 2 |

## Pairwise comparisons (P4a statistic, 3 sigma)

| pair | z mean weight | max |z| marginal | clbits outside | min visible marginal diff |
|---|---|---|---|---|
| kraus_gpu_cusv~kraus_cpu | -1.249 | 56.51 | [1, 2, 4, 7, 8, 9, 10, 11] | 1.065 |
| rm_gpu_cusv~rm_cpu | -1.781 | 27.69 | [3, 8, 9, 13, 14, 16, 17, 19] | 1.063 |
| rm_gpu_cusv~kraus_cpu | -0.1416 | 56.86 | [1, 2, 4, 7, 8, 9, 10, 11] | 1.063 |
| kraus_gpu_native~kraus_cpu | -1.106 | 59.99 | [1, 2, 4, 7, 8, 9, 10, 11] | 1.065 |
| kraus_gpu_cusv_nofusion~kraus_cpu | -1.712 | 73.03 | [1, 7, 9] | 1.069 |
| rm_cpu~kraus_cpu | 0.6708 | inf | [8] | 1.5 |
| kraus_gpu_cusv~rm_gpu_cusv | -17.38 | 10.97 | [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | 0.1148 |
| rm_gpu_cusv_anchor~rm_gpu_cusv | 0.5636 | 43.51 | [1, 2, 3, 4, 6, 9, 10, 14, 15, 16] | 1.063 |
| rm_gpu_cusv_anchor~rm_cpu | -1.342 | inf | [3, 9, 14] | 1.5 |
| kraus_gpu_cusv_nofusion~kraus_gpu_cusv | -5.778 | 5.084 | [0, 4, 9, 10, 11, 12, 13, 15, 16, 18, 19] | 0.1624 |
| kraus_gpu_native~kraus_gpu_cusv | 1.674 | 2.591 | [] | 0.1326 |
| kraus_gpu_native~kraus_gpu_cusv_nofusion | 7.36 | 5.797 | [0, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19] | 0.1624 |

## K4 the CI CPU arms vs the laptop CPU reference

| arm | shots (CI, laptop) | mean weight | z mean weight | agree |
|---|---|---|---|---|
| kraus_cpu | [2, 19] | [8, 7.474] | 0.1303 | True |
| rm_cpu | [2, 24] | [11, 6.917] | 1.963 | True |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| K1 kraus_gpu_cusv (run 1) vs kraus_cpu (run 2): bug_confirmed iff |z_w| > 3 (both outcomes PASS; the field is the decision) | {'z_w': -1.248820894996344, 'w': [2.99609375, 8.0], 'bug_confirmed': False} | decided (both arms sampled) | True |
| K2 production representation: rm iff rm_gpu_cusv (run 1) agrees with rm_cpu and kraus_cpu (run 2) (|z_w| <= 3, no marginal beyond 3 sigma), else blocked | {'production_representation': 'blocked', 'z_w': {'rm_gpu_cusv~rm_cpu': -1.7809940604099272, 'rm_gpu_cusv~kraus_cpu': -0.14155764666132578}, 'clbits_outside': {'rm_gpu_cusv~rm_cpu': [3, 8, 9, 13, 14, 16, 17, 19], 'rm_gpu_cusv~kraus_cpu': [1, 2, 4, 7, 8, 9, 10, 11]}} | decided (all three arms sampled) | True |
| K3 validated Kraus GPU path (run 1's native / cuStateVec-no-fusion arms vs kraus_cpu of run 2): first with |z_w| <= 3, else none | {'validated_kraus_gpu_path': 'kraus_gpu_native', 'z_w': {'kraus_gpu_native': -1.1062985441745348, 'kraus_gpu_cusv_nofusion': -1.7122865097752757}} | recorded | True |
| K4 the two CPU references agree (CI CPU arms vs the laptop's c33c_diag summary): |z_w| <= 3 per representation; recorded -- a disagreement is a STOP for the planner, not a token failure (prompts/33e R3 (b), section 2) | {'status': 'agree', 'stop_planner': False, 'z_w': {'kraus_cpu': 0.1303141316093172, 'rm_cpu': 1.9632805657938275}} | recorded (evaluated when the laptop summary is in the commit) | True |

## Notes

- dry run: CPU only, the Pauli-twirled representation stands in for the CPU arms and the anchor (Kraus on this CPU costs minutes per shot), 2 shots per CPU arm, 2 anchor shots -- a path check of run 2, not a measurement

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P0a run 1 archived byte-identically (sha256 of the archive = the harvested run 1's) | 30f6326b5dba109bdfd454e645057b099ffc9ad37a75e6587e244c2bfad712b4 | validation/archive/C2_KCHK_job59780907.json with sha256 30f6326b5dba109bdfd454e645057b099ffc9ad37a75e6587e244c2bfad712b4 | PASS |
| P0b run 1's GPU arms: the stored structure equals the one recomputed from their raw counts | {'kraus_gpu_cusv': [256, 0.0], 'rm_gpu_cusv': [512, 0.0], 'kraus_gpu_native': [256, 0.0], 'kraus_gpu_cusv_nofusion': [128, 0.0]} | sum of counts = shots_done and max |diff| <= 1e-12 | PASS |
| P0 raw counts of every run-2 arm stored (sum of counts = shots_done) | {'rm_gpu_cusv_anchor': [2, 2], 'kraus_cpu': [2, 2], 'rm_cpu': [2, 2]} | equal | PASS |
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 936 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False, 'cpu_affinity': 12, 'slurm_cpus_per_task': None} | every policy field non-null on the CI and cpu_affinity == SLURM_CPUS_PER_TASK there; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C2_KCHK.json`.
