# Campaign 33 token C2_CAL (class 2): 21-qubit timing ladder {8,32,128,512} on B0_ref117_k1 (IBM-T0), Kraus vs PTA, cuStateVec vs batched; sizes C2_*

**Status: PASS** — `python scripts/campaign33.py --token C2_CAL`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-13 08:19:41 PDT.  Runtime 1816 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec; GPUs 1; tasks 1; wall 1816 s; GPU node-hours (shared QOS, G/4 x t) 0.1261; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 1.84; peak GPU memory 2295 MiB; mean GPU utilisation 81.77 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 7.1, noise_model_build_s 35.4, rm_check_s 13.0, arms_s 1765.2.

## C2_CAL run 2 arms (I-ECHO on IBM-T0 B0_ref117_k1, cuStateVec)

| representation | target | shots done | points | s/shot (largest point) | mean weight | se | accepted | reference hits |
|---|---|---|---|---|---|---|---|---|
| pta | 512 | 512 | 4 | 0.287 | 9.957 | 0.1021 | 0 | 0 |
| rm | 1024 | 1024 | 8 | 0.3539 | 7.42 | 0.07662 | 4 | 0 |
| kraus | 1024 | 640 | 5 | 1.84 | 2.398 | 0.1358 | 1 | 0 |

## Garbage-structure comparisons

| comparison | z mean weight | max |z| marginal | marginals outside | pass |
|---|---|---|---|---|
| P4a RM vs Kraus | 32.2 | 18.06 | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | False |
| P4b PTA vs Kraus (information) | 44.47 | 21.71 | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | False |
| P4c pta vs K1 (information) | 1.817 | 2.874 | [] | True |
| P4c rm vs K1 (information) | -30.55 | 44.47 | [0, 1, 2, 3, 5, 7, 8, 11, 14, 15, 16, 17, 18, 19] | False |
| P4c kraus vs K1 (information) | -54.2 | 64.23 | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | False |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P0 run-1 record archived unedited and referenced (supersedes + sha256) | 54b77474065486eaa0f43b5e1c7403ed521ddafcd1d3abd58d6b85fca1022ac7 | validation/archive/C2_CAL_job59491475.json present | PASS |
| P4r RM model: no Kraus instruction (to_dict and delay-pass errors); the T2 <= T1 qubits identical to the Kraus model | {'changed': [59, 69, 92, 95], 'unchanged': 17, 'max_superop_diff': 0.0, 'kraus_in_rm': {'to_dict': 0, 'custom_pass_sites': 0, 'custom_pass_sites_total': 8004}} | 0 kraus; SuperOp / readout diff <= 1e-12 on unchanged sites | PASS |
| P4a RM vs Kraus garbage structure: |z| <= 3 on the mean Hamming weight and every marginal (decides the production representation; PASS or FAIL are both a decision) | {'pass': False, 'z_w': 32.196020649340085, 'max_abs_z_marginal': 18.058239322781933, 'production': 'kraus'} | decided (both arms sampled) | PASS |
| P4b PTA vs Kraus, same statistic (information; expected to fail: PTA is unital) | {'pass': False, 'z_w': 44.47309559150446, 'max_abs_z_marginal': 21.70899467801984} | information | PASS |
| P4c each arm vs the K1 measurement (z of the weight and marginals, readout share; information) | {'pta': 1.8171368100745533, 'rm': -30.552998930766726, 'kraus': -54.19501871202047} | fields present | PASS |
| P5' >= 2 ladder points per representation (cuStateVec) and Kraus shots_done >= the minimum | {'points': {'pta': 4, 'rm': 8, 'kraus': 5}, 'kraus_shots_done': 640} | >= 2 each; Kraus >= 384 | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 1816 s | <= min(walltime 2700 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | {'pta': 512, 'rm': 1024, 'kraus': 640} | no reduction below the minimum | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C2_CAL.json`.
