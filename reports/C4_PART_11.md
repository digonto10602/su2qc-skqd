# Campaign 33 token C4_PART_11 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_11.json in the requested commit (frun part i of n, dropped f-cells, or a cv3 equal-shots sample), written by scripts/campaign33_resize.py

**Status: PASS** — `python scripts/campaign33.py --token C4_PART_11`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-14 09:06:28 PDT.  Runtime 676 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec; GPUs 1; tasks 1; wall 676 s; GPU node-hours (shared QOS, G/4 x t) 0.04692; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.01827; peak GPU memory 1783 MiB; mean GPU utilisation 45.91 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 12.1, sampling_s 622.3, bootstrap_and_readout_s 45.2, analysis_s 45.3.

## C4_PART_11: E1 x NAT-O2, B=1, plan, part 2 of 2

| shots | |B_all| | E_R - E0 | certificate | width | E0 inside | recall S999 | W | f_hit (k=1) | f_hat_ideal 95 % |
|---|---|---|---|---|---|---|---|---|---|
| 33800 | 317 | 0.0003055 | weinstein | 0.04799 | True | 1 | 1 | 0.2567 | [0.2003, 0.2634] |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P0 slot content written for this slot (prompts/33b R4: seed_token_index = the index of the run's own F token, or the slot's own for f-cells; slot = this token) | {'seed_token_index': 27, 'expected': 27, 'rule': "the run's own F token", 'slot': 'C4_PART_11', 'this_token': 'C4_PART_11', 'content': 'frun', 'token_matches_run': True} | equal | PASS |
| P13 (part 2 of 2) E_R >= E0 - 1e-9 on this part's shots (CV0 and the certificate are read at assembly on the merged parts) | {'variational': True, 'E0_inside_information': True} | variational | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 676 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | full | no reduction below the minimum | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C4_PART_11.json`.
