# Campaign 33 token C2_KCHK (class 2): prompts/33d R3 + 33e R2: the GPU Kraus check on IBM-T0 B0_ref117_k1 (I-ECHO); run 2 (default, --content cpu_only): Kraus and RM on the CPU in a separate process on the step's CPUs beside a 128-shot RM cuStateVec anchor, the four GPU arms read from run 1 (job 59780907, archived); raw counts; decides the class-2 representation

**Status: FAIL** — `python scripts/campaign33.py --token C2_KCHK`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-15 17:54:33 PDT.  Runtime 2760 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec (the 128-shot RM anchor); GPUs 1; tasks 1; wall 2760 s; GPU node-hours (shared QOS, G/4 x t) 0.1917; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.4275; peak GPU memory 2295 MiB; mean GPU utilisation 0.722 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 10.3, gpu_anchor_s 54.7, cpu_process_s 2757.5.

## C2_KCHK run 2 arms (I-ECHO on IBM-T0 B0_ref117_k1); GPU arms read from run 1

| arm | run | engine | representation | shots | minimum | s/shot | mean weight | se |
|---|---|---|---|---|---|---|---|---|
| kraus_gpu_cusv | 1 | GPU custatevec | kraus | 256 | 256 | 1.92 | 2.996 | 0.2351 |
| rm_gpu_cusv | 1 | GPU custatevec | rm | 512 | 512 | 0.4172 | 7.434 | 0.09964 |
| kraus_gpu_native | 1 | GPU native | kraus | 256 | 64 | 2.223 | 3.566 | 0.2466 |
| kraus_gpu_cusv_nofusion | 1 | GPU custatevec_nofusion | kraus | 128 | 32 | 5.047 | 1.141 | 0.2187 |
| rm_gpu_cusv_anchor | 2 | GPU custatevec | rm | 128 | 128 | 0.4275 | 7.062 | 0.2048 |
| kraus_cpu | 2 | CPU statevector (separate process) | kraus | 7 | 8 | 213.7 | 8.429 | 0.7825 |
| rm_cpu | 2 | CPU statevector (separate process) | rm | 12 | 8 | 93.9 | 6.667 | 0.4144 |

## Pairwise comparisons (P4a statistic, 3 sigma)

| pair | z mean weight | max |z| marginal | clbits outside | min visible marginal diff |
|---|---|---|---|---|
| kraus_gpu_cusv~kraus_cpu | -6.649 | 5.939 | [2, 3, 8, 9, 16, 17] | 0.5746 |
| rm_gpu_cusv~rm_cpu | 1.799 | 2.626 | [] | 0.4381 |
| rm_gpu_cusv~kraus_cpu | -1.261 | 11.77 | [2, 3, 5, 8, 17] | 0.5708 |
| kraus_gpu_native~kraus_cpu | -5.927 | 5.829 | [2, 3, 5, 8, 9, 16, 17] | 0.5746 |
| kraus_gpu_cusv_nofusion~kraus_cpu | -8.97 | 5.998 | [8, 9, 16, 17] | 0.5822 |
| rm_cpu~kraus_cpu | -1.99 | 2.267 | [] | 0.7134 |
| kraus_gpu_cusv~rm_gpu_cusv | -17.38 | 10.97 | [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | 0.1148 |
| rm_gpu_cusv_anchor~rm_gpu_cusv | -1.63 | 2.003 | [] | 0.1482 |
| rm_gpu_cusv_anchor~rm_cpu | 0.8564 | 2.531 | [] | 0.4529 |
| kraus_gpu_cusv_nofusion~kraus_gpu_cusv | -5.778 | 5.084 | [0, 4, 9, 10, 11, 12, 13, 15, 16, 18, 19] | 0.1624 |
| kraus_gpu_native~kraus_gpu_cusv | 1.674 | 2.591 | [] | 0.1326 |
| kraus_gpu_native~kraus_gpu_cusv_nofusion | 7.36 | 5.797 | [0, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19] | 0.1624 |

## K4 the CI CPU arms vs the laptop CPU reference

| arm | shots (CI, laptop) | mean weight | z mean weight | agree |
|---|---|---|---|---|
| kraus_cpu | [7, 29] | [8.429, 7.621] | 0.9058 | True |
| rm_cpu | [12, 24] | [6.667, 6.917] | -0.3544 | True |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P0a run 1 archived byte-identically (sha256 of the archive = the harvested run 1's) | 30f6326b5dba109bdfd454e645057b099ffc9ad37a75e6587e244c2bfad712b4 | validation/archive/C2_KCHK_job59780907.json with sha256 30f6326b5dba109bdfd454e645057b099ffc9ad37a75e6587e244c2bfad712b4 | PASS |
| P0b run 1's GPU arms: the stored structure equals the one recomputed from their raw counts | {'kraus_gpu_cusv': [256, 0.0], 'rm_gpu_cusv': [512, 0.0], 'kraus_gpu_native': [256, 0.0], 'kraus_gpu_cusv_nofusion': [128, 0.0]} | sum of counts = shots_done and max |diff| <= 1e-12 | PASS |
| K1 kraus_gpu_cusv (run 1) vs kraus_cpu (run 2): bug_confirmed iff |z_w| > 3 (both outcomes PASS; the field is the decision) | {'z_w': -6.649096451944512, 'w': [2.99609375, 8.428571428571429], 'bug_confirmed': True} | decided (both arms sampled) | PASS |
| K2 production representation: rm iff rm_gpu_cusv (run 1) agrees with rm_cpu and kraus_cpu (run 2) (|z_w| <= 3, no marginal beyond 3 sigma), else blocked | {'production_representation': 'blocked', 'z_w': {'rm_gpu_cusv~rm_cpu': 1.799454869423125, 'rm_gpu_cusv~kraus_cpu': -1.261413419278466}, 'clbits_outside': {'rm_gpu_cusv~rm_cpu': [], 'rm_gpu_cusv~kraus_cpu': [2, 3, 5, 8, 17]}} | decided (all three arms sampled) | PASS |
| K3 validated Kraus GPU path (run 1's native / cuStateVec-no-fusion arms vs kraus_cpu of run 2): first with |z_w| <= 3, else none | {'validated_kraus_gpu_path': 'none', 'z_w': {'kraus_gpu_native': -5.926638613263177, 'kraus_gpu_cusv_nofusion': -8.970356245556617}} | recorded | PASS |
| K4 the two CPU references agree (CI CPU arms vs the laptop's c33c_diag summary): |z_w| <= 3 per representation; recorded -- a disagreement is a STOP for the planner, not a token failure (prompts/33e R3 (b), section 2) | {'status': 'agree', 'stop_planner': False, 'z_w': {'kraus_cpu': 0.9057732720657067, 'rm_cpu': -0.3544398202895614}} | recorded (evaluated when the laptop summary is in the commit) | PASS |
| P0 raw counts of every run-2 arm stored (sum of counts = shots_done) | {'rm_gpu_cusv_anchor': [128, 128], 'kraus_cpu': [7, 7], 'rm_cpu': [12, 12]} | equal | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 2760 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI; run.cpu_affinity == SLURM_CPUS_PER_TASK) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True, 'cpu_affinity': 1, 'slurm_cpus_per_task': 32} | every policy field non-null on the CI and cpu_affinity == SLURM_CPUS_PER_TASK there; present on the laptop | FAIL |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | {'rm_gpu_cusv_anchor': [128, 128], 'kraus_cpu': [7, 8], 'rm_cpu': [12, 8]} | no reduction below the minimum | FAIL |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C2_KCHK.json`.
