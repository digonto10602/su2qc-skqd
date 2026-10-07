# DRY RUN (laptop path check, reduced size): Campaign 33 token C4_CF (class 4): CF_traj redo on the GPU: K=2000 faulty Pauli trajectories per arm

**Status: PASS** — `python scripts/campaign33.py --token C4_CF --dry-run`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 17:46:08 MDT.  Runtime 381 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Aer statevector per trajectory (CPU), checkpoints in memory; device CPU (requested CPU, available ['CPU']); GPU mode None; GPUs None; tasks None; wall 381 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 9.434; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '2.5.2', 'qiskit_aer': '0.17.2', 'numpy': '2.5.2', 'scipy': '1.18.0', 'python': '3.12.14'}.  Phases (s): trajectories_s 380.4.

## Arms (r at delta 1e-3)

| arm | K | r | r 95 % | f_hit | f_ideal | floor min |
|---|---|---|---|---|---|---|
| B0_ref25_k1 | 9 | 0.9926 | [0.9899, 1.001] | 0.3534 | 0.3561 | 0.9588 |
| B1_ref57_k1 | 5 | 1.001 | [1, 1.003] | 0.1725 | 0.1724 | 1 |
| B0_ref25_k4 | 6 | 1.789 | [1, 3.365] | 0.3081 | 0.1722 | 1.756 |
| B0_ref25_k1__xx | 8 | 1.001 | [1, 1.003] | 0.1722 | 0.1721 | 1 |

## Pooled k = 1 r(1e-3) and r_nc

| pooled r | 95 % | new r_nc | old r_nc | old pooled 95 % |
|---|---|---|---|---|
| 0.9958 | [0.9928, 1.001] | 1.001 | 1.115 | [1.029, 1.115] |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P16 r per arm with 95 % bootstrap intervals; pooled r; new r_nc = its upper end | {'B0_ref25_k1': 0.992618109605795, 'B1_ref57_k1': 1.000882929070056, 'B0_ref25_k4': 1.7892869363755766, 'B0_ref25_k1__xx': 1.000909940822966} | fields present | True |
| P17 floor theorem (CF_traj C4'): min_S99 f_eff / f_ideal(1e-3) >= 0.95 on every arm | {'B0_ref25_k1': 0.9588450238147029, 'B1_ref57_k1': 1.0000034574405767, 'B0_ref25_k4': 1.7561295006315403, 'B0_ref25_k1__xx': 1.000058949761462} | >= 0.95 | True |

## Notes

- owner item (prompts/33 section 8): the new r_nc 1.0012 lies outside the old pooled interval [1.0285934561902321, 1.1151352098004452]; no criterion or verdict is changed by this token

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 381 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | {'B0_ref25_k1': 9, 'B1_ref57_k1': 5, 'B0_ref25_k4': 6, 'B0_ref25_k1__xx': 8} | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C4_CF.json`.
