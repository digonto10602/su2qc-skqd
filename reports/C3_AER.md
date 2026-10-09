# Campaign 33 token C3_AER (class 3): NAT-O0 noiseless on Aer: per-state agreement; f=1 SKQD reference of the native family

**Status: PASS** — `python scripts/campaign33.py --token C3_AER`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-09 12:03:39 PDT.  Runtime 59 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec (noiseless); GPUs 1; tasks 1; wall 59 s; GPU node-hours (shared QOS, G/4 x t) 0.004098; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 4.946e-05; peak GPU memory 429 MiB; mean GPU utilisation 1.5 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 12.0, exactness_s 28.2, noiseless_sampling_s 22.5, analysis_s 3.7.

## Exactness (vs the exact Krylov states)

| family | circuits | max |dpsi| | max leakage | all ok |
|---|---|---|---|---|
| NAT-O0 | 44 | 2.085e-13 | 1.283e-13 | True |

## Noiseless f = 1 SKQD reference

| sector | prefix | shots | |B_all| | recall S999 | E_R - E0 | certificate | E0 inside |
|---|---|---|---|---|---|---|---|
| B=0 | plan_f010 | 34909 | 327 | 1 | 0.0001828 | kato_temple_exact_E1 | True |
| B=0 | uniform_2e5 | 200000 | 414 | 1 | 7.902e-05 | kato_temple_exact_E1 | True |
| B=1 | plan_f010 | 99000 | 344 | 1 | 0.0001827 | weinstein | True |
| B=1 | uniform_2e5 | 199992 | 327 | 1 | 0.0001935 | weinstein | True |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P1 max |dpsi| < 1e-10 and leakage < 1e-9 on every circuit of every allowed family | {'NAT-O0': [2.0848540460878082e-13, 1.283417816466681e-13]} | < 1e-10 / < 1e-9 | PASS |
| P2 per-state 5 sigma test |n_s/N - p_s| <= 5 sqrt(p_s(1-p_s)/N), p_s >= 1e-3, every sampled circuit | {'circuits': 44, 'states_tested': 1393, 'max_z': 4.082708580125121, 'failures': 0} | 0 failures (Bonferroni false-alarm < 1e-2 over <= 9000 states) | PASS |
| P3 noiseless SKQD at the f = 0.10 plan: recall of S999 >= 0.9 in both sectors | {'B=0': 1.0, 'B=1': 1.0} | >= 0.9 | PASS |
| P3 E0 inside the Kato-Temple (B=0) / Weinstein (B=1) interval at the plan; E_R >= E0 - 1e-9 | {'B=0': [[-5.603019550453782, -5.602417672886843], 0.00018278499492296874], 'B=1': [[-3.860849761664514, -3.8259017778929536], 0.00018266523119336853]} | inside; variational | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 59 s | <= min(walltime 1800 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | full | no reduction below the minimum | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C3_AER.json`.
