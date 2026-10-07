# DRY RUN (laptop path check, reduced size): Campaign 33 token C3_AER (class 3): NAT-O0 noiseless on Aer: per-state agreement; f=1 SKQD reference of the native family

**Status: PASS** — `python scripts/campaign33.py --token C3_AER --dry-run`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 16:54:37 MDT.  Runtime 194 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 194 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.3738; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '2.5.2', 'qiskit_aer': '0.17.2', 'numpy': '2.5.2', 'scipy': '1.18.0', 'python': '3.12.14'}.  Phases (s): exactness_s 93.5, noiseless_sampling_s 95.7, analysis_s 1.2.

## Exactness (vs the exact Krylov states)

| family | circuits | max |dpsi| | max leakage | all ok |
|---|---|---|---|---|
| NAT-O0 | 8 | 2.086e-13 | 1.17e-13 | True |

## Noiseless f = 1 SKQD reference

| sector | prefix | shots | |B_all| | recall S999 | E_R - E0 | certificate | E0 inside |
|---|---|---|---|---|---|---|---|
| B=0 | plan_f010 | 41 | 20 | 0.2209 | 0.1638 | kato_temple_exact_E1 | True |
| B=0 | uniform_2e5 | 128 | 23 | 0.2442 | 0.155 | kato_temple_exact_E1 | True |
| B=1 | plan_f010 | 50 | 19 | 0.2 | 0.1993 | weinstein | True |
| B=1 | uniform_2e5 | 128 | 23 | 0.2316 | 0.1993 | weinstein | True |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P1 max |dpsi| < 1e-10 and leakage < 1e-9 on every circuit of every allowed family | {'NAT-O0': [2.086102157601123e-13, 1.170175067954915e-13]} | < 1e-10 / < 1e-9 | True |
| P2 per-state 5 sigma test |n_s/N - p_s| <= 5 sqrt(p_s(1-p_s)/N), p_s >= 1e-3, every sampled circuit | {'circuits': 8, 'states_tested': 191, 'max_z': 4.5319076314977425, 'failures': 0} | 0 failures (Bonferroni false-alarm < 1e-2 over <= 9000 states) | True |
| P3 noiseless SKQD at the f = 0.10 plan: recall of S999 >= 0.9 in both sectors | {'B=0': 0.22093023255813954, 'B=1': 0.2} | >= 0.9 | False |
| P3 E0 inside the Kato-Temple (B=0) / Weinstein (B=1) interval at the plan; E_R >= E0 - 1e-9 | {'B=0': [[-5.777618514293297, -5.438765904486391], 0.16383455339537534], 'B=1': [[-4.4552514062226685, -3.6267633788193963], 0.19932106430475072]} | inside; variational | True |

## Notes

- dry run: 8 of 44 circuits used (['B0_ref117_k1', 'B0_ref117_k2', 'B0_ref25_k1', 'B0_ref25_k4', 'B1_ref27_k1', 'B1_ref27_k2', 'B1_ref57_k1', 'B1_ref57_k4'])
- dry run: 8 of 44 circuits used (['B0_ref117_k1', 'B0_ref117_k2', 'B0_ref25_k1', 'B0_ref25_k4', 'B1_ref27_k1', 'B1_ref27_k2', 'B1_ref57_k1', 'B1_ref57_k4'])

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 194 s | <= min(walltime 1800 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C3_AER.json`.
