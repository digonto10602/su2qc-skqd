# Campaign 33 token C4_PART_13 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_13.json in the requested commit (frun part i of n, dropped f-cells, or a cv3 equal-shots sample), written by scripts/campaign33_resize.py

**Status: PASS** — `python scripts/campaign33.py --token C4_PART_13`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-15 12:54:14 PDT.  Runtime 1612 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec; GPUs 1; tasks 1; wall 1612 s; GPU node-hours (shared QOS, G/4 x t) 0.112; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.05016; peak GPU memory 1783 MiB; mean GPU utilisation 77.2 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 13.3, cells_s 1605.0.

## f-cells (slot)

| scenario | variant | shots | f_hit (k=1 pooled) | f_hit 95 % |
|---|---|---|---|---|
| E1 | NAT-O2 | 2000 | 0.2593 | [0.2338, 0.2867] |
| E1 | NAT-O3 | 2000 | 0.249 | [0.2241, 0.276] |
| E1 | NAT-O4 | 2000 | 0.2422 | [0.2176, 0.2688] |
| E1 | NAT-O6 | 2000 | 0.2497 | [0.2247, 0.2767] |
| E2 | NAT-O2 | 2000 | 0.2634 | [0.2377, 0.291] |
| E2 | NAT-O3 | 2000 | 0.273 | [0.2468, 0.3011] |
| E2 | NAT-O4 | 2000 | 0.2517 | [0.2267, 0.2788] |
| E2 | NAT-O6 | 2000 | 0.2463 | [0.2215, 0.2731] |
| E3 | NAT-O2 | 2000 | 0.1245 | [0.1071, 0.144] |
| E3 | NAT-O3 | 2000 | 0.09919 | [0.08371, 0.1167] |
| E3 | NAT-O4 | 2000 | 0.1163 | [0.09947, 0.1352] |
| E3 | NAT-O6 | 2000 | 0.09714 | [0.08182, 0.1145] |
| E4 | NAT-O1 | 2000 | 0.2818 | [0.2553, 0.3104] |
| E4 | NAT-O2 | 2000 | 0.2606 | [0.2351, 0.2882] |
| E4 | NAT-O3 | 2000 | 0.2429 | [0.2182, 0.2695] |
| E4 | NAT-O4 | 2000 | 0.2456 | [0.2208, 0.2724] |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P0 slot content written for this slot (prompts/33b R4: seed_token_index = the index of the run's own F token, or the slot's own for f-cells; slot = this token) | {'seed_token_index': 45, 'expected': 45, 'rule': "the slot's own token (f-cells have no run)", 'slot': 'C4_PART_13', 'this_token': 'C4_PART_13', 'content': 'fcells', 'token_matches_run': True} | equal | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 1612 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | full | no reduction below the minimum | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C4_PART_13.json`.
