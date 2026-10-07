# DRY RUN (laptop path check, reduced size): Campaign 33 token C4_FCELLS_A (class 4): 10-min ladder then f-cells E1,E2,E3,E4,E5a/b/c x O0-O4 (+O6 info)

**Status: PASS** — `python scripts/campaign33.py --token C4_FCELLS_A --dry-run`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 17:17:53 MDT.  Runtime 323 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 323 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 10.43; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '2.5.2', 'qiskit_aer': '0.17.2', 'numpy': '2.5.2', 'scipy': '1.18.0', 'python': '3.12.14'}.  Phases (s): ladder_s 110.7, cells_s 208.6.

## f-cells

| scenario | variant | shots | f_hit (k=1 pooled) | f_hit 95 % | f_hat_ideal | GO v3 (info) | accepted B0_k1 | f0 B0_k1 |
|---|---|---|---|---|---|---|---|---|
| E1 | NAT-O0 | 20 | 0.2736 | [0.07456, 0.7006] | 0.2454 | GO | 0.375 | 0.1721 |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P10 each variant's f_hit vs the O0 cell (Delta, sigma, verdict reported; an exact optimisation may move f) | 0 | fields present | True |
| P11 E1 x O0 reference hits on the k = 1 circuits inside the 95 % band of the CF_traj prediction (a physics criterion: STOP on FAIL) | 4 | in [0, 8] (prediction 3.6 +- 0.1) | True |

## Notes

- 41 cells dropped for the budget: ['E2|NAT-O1', 'E3|NAT-O2', 'E4|NAT-O3', 'E5a|NAT-O4', 'E5b|NAT-O6', 'E5c|NAT-O0', 'E2|NAT-O0', 'E3|NAT-O0', 'E4|NAT-O0', 'E5a|NAT-O0', 'E5b|NAT-O0', 'E1|NAT-O1', 'E3|NAT-O1', 'E4|NAT-O1', 'E5a|NAT-O1', 'E5b|NAT-O1', 'E5c|NAT-O1', 'E1|NAT-O2', 'E2|NAT-O2', 'E4|NAT-O2', 'E5a|NAT-O2', 'E5b|NAT-O2', 'E5c|NAT-O2', 'E1|NAT-O3', 'E2|NAT-O3', 'E3|NAT-O3', 'E5a|NAT-O3', 'E5b|NAT-O3', 'E5c|NAT-O3', 'E1|NAT-O4', 'E2|NAT-O4', 'E3|NAT-O4', 'E4|NAT-O4', 'E5b|NAT-O4', 'E5c|NAT-O4', 'E1|NAT-O6', 'E2|NAT-O6', 'E3|NAT-O6', 'E4|NAT-O6', 'E5a|NAT-O6', 'E5c|NAT-O6']

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 323 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C4_FCELLS_A.json`.
