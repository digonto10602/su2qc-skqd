# Campaign 33 token C2_KCHK (class 2): prompts/33d R3: the GPU Kraus check on IBM-T0 B0_ref117_k1 (I-ECHO): Kraus and RM on cuStateVec, Kraus on Aer's native GPU kernels and on cuStateVec without fusion, Kraus and RM on the CPU in a separate process; raw counts; decides the class-2 representation

**Status: FAIL** — `python scripts/campaign33.py --token C2_KCHK`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-14 10:03:30 PDT.  Runtime 2312 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode per arm (custatevec, native, custatevec_nofusion); GPUs 1; tasks 1; wall 2312 s; GPU node-hours (shared QOS, G/4 x t) 0.1606; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.4172; peak GPU memory 2295 MiB; mean GPU utilisation 62.47 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 34.2, gpu_arms_s 2020.5, cpu_process_s 2305.2.

## C2_KCHK arms (I-ECHO on IBM-T0 B0_ref117_k1)

| arm | engine | representation | shots | minimum | s/shot | mean weight | se |
|---|---|---|---|---|---|---|---|
| kraus_gpu_cusv | GPU custatevec | kraus | 256 | 256 | 1.92 | 2.996 | 0.2351 |
| rm_gpu_cusv | GPU custatevec | rm | 512 | 512 | 0.4172 | 7.434 | 0.09964 |
| kraus_gpu_native | GPU native | kraus | 256 | 64 | 2.223 | 3.566 | 0.2466 |
| kraus_gpu_cusv_nofusion | GPU custatevec_nofusion | kraus | 128 | 32 | 5.047 | 1.141 | 0.2187 |
| kraus_cpu | CPU statevector (separate process) | kraus | 0 | 16 | None | None | None |
| rm_cpu | CPU statevector (separate process) | rm | 0 | 16 | None | None | None |

## Pairwise comparisons (P4a statistic, 3 sigma)

| pair | z mean weight | max |z| marginal | clbits outside | min visible marginal diff |
|---|---|---|---|---|
| kraus_gpu_cusv~kraus_cpu | None | None | None | None |
| rm_gpu_cusv~rm_cpu | None | None | None | None |
| rm_gpu_cusv~kraus_cpu | None | None | None | None |
| kraus_gpu_native~kraus_cpu | None | None | None | None |
| kraus_gpu_cusv_nofusion~kraus_cpu | None | None | None | None |
| rm_cpu~kraus_cpu | None | None | None | None |
| kraus_gpu_cusv~rm_gpu_cusv | -17.38 | 10.97 | [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | 0.1148 |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| K1 kraus_gpu_cusv vs kraus_cpu: bug_confirmed iff |z_w| > 3 (both outcomes PASS; the field is the decision) | {'z_w': None, 'w': None, 'bug_confirmed': None} | decided (both arms sampled) | FAIL |
| K2 production representation: rm iff rm_gpu_cusv agrees with rm_cpu and kraus_cpu (|z_w| <= 3, no marginal beyond 3 sigma), else blocked | {'production_representation': 'blocked', 'z_w': {'rm_gpu_cusv~rm_cpu': None, 'rm_gpu_cusv~kraus_cpu': None}, 'clbits_outside': {'rm_gpu_cusv~rm_cpu': None, 'rm_gpu_cusv~kraus_cpu': None}} | decided (all three arms sampled) | FAIL |
| K3 validated Kraus GPU path (reference arm of the cells): first of native / cuStateVec-no-fusion with |z_w| <= 3 against kraus_cpu, else none | {'validated_kraus_gpu_path': 'none', 'z_w': {'kraus_gpu_native': None, 'kraus_gpu_cusv_nofusion': None}} | recorded | PASS |
| P0 raw counts of every arm stored (sum of counts = shots_done) | {'kraus_gpu_cusv': [256, 256], 'rm_gpu_cusv': [512, 512], 'kraus_gpu_native': [256, 256], 'kraus_gpu_cusv_nofusion': [128, 128], 'kraus_cpu': [0, 0], 'rm_cpu': [0, 0]} | equal | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 2312 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | {'kraus_gpu_cusv': [256, 256], 'rm_gpu_cusv': [512, 512], 'kraus_gpu_native': [256, 64], 'kraus_gpu_cusv_nofusion': [128, 32], 'kraus_cpu': [0, 16], 'rm_cpu': [0, 16]} | no reduction below the minimum | FAIL |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C2_KCHK.json`.
