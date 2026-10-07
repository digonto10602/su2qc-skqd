# DRY RUN (laptop path check, reduced size): Campaign 33 token C1_IDEAL (class 1): IR-L0, NAT-O0, IBM-U/T0/T3 exactness vs the exact Krylov states; noiseless sampling at the f=0.10 plan and 2e5 per sector; the f=1 SKQD reference

**Status: PASS** — `python scripts/campaign33.py --token C1_IDEAL --dry-run`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 18:14:34 MDT.  Runtime 287 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 287 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.3915; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'python': '3.12.14'}.  Phases (s): exactness_s 183.4, noiseless_sampling_s 100.2, analysis_s 0.8.

## Exactness (vs the exact Krylov states)

| family | circuits | max |dpsi| | max leakage | all ok |
|---|---|---|---|---|
| IR-L0 | 8 | 3.131e-14 | 9.237e-14 | True |
| NAT-O0 | 8 | 2.087e-13 | 1.175e-13 | True |
| IBM-T0 | 2 | 2.331e-12 | 2.143e-13 | True |

## Noiseless f = 1 SKQD reference

| sector | prefix | shots | |B_all| | recall S999 | E_R - E0 | certificate | E0 inside |
|---|---|---|---|---|---|---|---|
| B=0 | plan_f010 | 41 | 23 | 0.2558 | 0.1384 | kato_temple_exact_E1 | True |
| B=0 | uniform_2e5 | 128 | 25 | 0.2791 | 0.1251 | kato_temple_exact_E1 | True |
| B=1 | plan_f010 | 50 | 21 | 0.1895 | 0.1037 | weinstein | True |
| B=1 | uniform_2e5 | 128 | 24 | 0.2211 | 0.1037 | weinstein | True |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P1 max |dpsi| < 1e-10 and leakage < 1e-9 on every circuit of every allowed family | {'IR-L0': [3.130617310633016e-14, 9.237055564881302e-14], 'NAT-O0': [2.0870099463463683e-13, 1.1746159600534156e-13], 'IBM-T0': [2.3312214167978764e-12, 2.142730437526552e-13]} | < 1e-10 / < 1e-9 | True |
| P2 per-state 5 sigma test |n_s/N - p_s| <= 5 sqrt(p_s(1-p_s)/N), p_s >= 1e-3, every sampled circuit | {'circuits': 10, 'states_tested': 207, 'max_z': 5.386266756660347, 'failures': 2} | 0 failures (Bonferroni false-alarm < 1e-2 over <= 9000 states) | False |
| P3 noiseless SKQD at the f = 0.10 plan: recall of S999 >= 0.9 in both sectors | {'B=0': 0.2558139534883721, 'B=1': 0.18947368421052632} | >= 0.9 | False |
| P3 E0 inside the Kato-Temple (B=0) / Weinstein (B=1) interval at the plan; E_R >= E0 - 1e-9 | {'B=0': [[-5.743225392949604, -5.4641874178229], 0.13841304005886634], 'B=1': [[-4.372350638361099, -3.7224266781917614], 0.10365776493238554]} | inside; variational | True |

## Notes

- dry run: the IBM exactness and per-state checks use IBM-T0 only (the CI runs U, T0, T3)
- dry run: 8 of 44 circuits used (['B0_ref117_k1', 'B0_ref117_k2', 'B0_ref25_k1', 'B0_ref25_k4', 'B1_ref27_k1', 'B1_ref27_k2', 'B1_ref57_k1', 'B1_ref57_k4'])
- dry run: 8 of 44 circuits used (['B0_ref117_k1', 'B0_ref117_k2', 'B0_ref25_k1', 'B0_ref25_k4', 'B1_ref27_k1', 'B1_ref27_k2', 'B1_ref57_k1', 'B1_ref57_k4'])
- dry run: 8 of 44 circuits used (['B0_ref117_k1', 'B0_ref117_k2', 'B0_ref25_k1', 'B0_ref25_k4', 'B1_ref27_k1', 'B1_ref27_k2', 'B1_ref57_k1', 'B1_ref57_k4'])

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 287 s | <= min(walltime 1800 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C1_IDEAL.json`.
