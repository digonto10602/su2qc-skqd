# Campaign 33 token C4_FCELLS_A (class 4): 10-min ladder then f-cells E1,E2,E3,E4,E5a/b/c x O0-O4 (+O6 info)

**Status: FAIL** — `python scripts/campaign33.py --token C4_FCELLS_A`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-09 13:14:53 PDT.  Runtime 2320 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec; GPUs 1; tasks 1; wall 2320 s; GPU node-hours (shared QOS, G/4 x t) 0.1611; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.07955; peak GPU memory 2.355e+04 MiB; mean GPU utilisation 77.89 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 15.7, ladder_s 718.6, cells_s 1590.9.

## f-cells

| scenario | variant | shots | f_hit (k=1 pooled) | f_hit 95 % | f_hat_ideal | GO v3 (info) | accepted B0_k1 | f0 B0_k1 |
|---|---|---|---|---|---|---|---|---|
| E1 | NAT-O0 | 2000 | 0.2312 | [0.2072, 0.2572] | 0.2074 | GO | 0.315 | 0.1721 |
| E2 | NAT-O0 | 2000 | 0.2675 | [0.2416, 0.2954] | 0.2399 | GO | 0.345 | 0.1867 |
| E3 | NAT-O0 | 2000 | 0.1136 | [0.09694, 0.1322] | 0.1018 | GO | 0.1888 | 0.06099 |
| E4 | NAT-O0 | 2000 | 0.2552 | [0.2299, 0.2824] | 0.2288 | GO | 0.3438 | 0.1856 |
| E5a | NAT-O0 | 2000 | 0.2353 | [0.2111, 0.2616] | 0.211 | GO | 0.295 | 0.1631 |
| E5b | NAT-O0 | 2000 | 0.2442 | [0.2195, 0.2709] | 0.219 | GO | 0.335 | 0.1528 |
| E5c | NAT-O0 | 2000 | 0.2162 | [0.193, 0.2414] | 0.1939 | GO | 0.2913 | 0.1071 |
| E1 | NAT-O1 | 2000 | 0.2552 | [0.2299, 0.2824] | 0.2288 | GO | 0.3337 | 0.172 |
| E2 | NAT-O1 | 2000 | 0.2675 | [0.2416, 0.2954] | 0.2399 | GO | 0.3588 | 0.1867 |
| E3 | NAT-O1 | 2000 | 0.1136 | [0.09694, 0.1322] | 0.1018 | GO | 0.2087 | 0.06094 |

## Notes

- 32 cells dropped for the budget: ['E4|NAT-O1', 'E5a|NAT-O1', 'E5b|NAT-O1', 'E5c|NAT-O1', 'E1|NAT-O2', 'E2|NAT-O2', 'E3|NAT-O2', 'E4|NAT-O2', 'E5a|NAT-O2', 'E5b|NAT-O2', 'E5c|NAT-O2', 'E1|NAT-O3', 'E2|NAT-O3', 'E3|NAT-O3', 'E4|NAT-O3', 'E5a|NAT-O3', 'E5b|NAT-O3', 'E5c|NAT-O3', 'E1|NAT-O4', 'E2|NAT-O4', 'E3|NAT-O4', 'E4|NAT-O4', 'E5a|NAT-O4', 'E5b|NAT-O4', 'E5c|NAT-O4', 'E1|NAT-O6', 'E2|NAT-O6', 'E3|NAT-O6', 'E4|NAT-O6', 'E5a|NAT-O6', 'E5b|NAT-O6', 'E5c|NAT-O6']

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P10 each variant's f_hit vs the O0 cell (Delta, sigma, verdict reported; an exact optimisation may move f) | 3 | fields present | PASS |
| P11 E1 x O0 reference hits on the k = 1 circuits inside the 95 % band of the CF_traj prediction (a physics criterion: STOP on FAIL) | 338 | in [302, 427] (prediction 362.6 +- 12.9) | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 2320 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | 10 of 42 cells | no reduction below the minimum | FAIL |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C4_FCELLS_A.json`.
