# Campaign 33 token C4_CF (class 4): CF_traj redo on the GPU: K=2000 faulty Pauli trajectories per arm

**Status: FAIL** — `python scripts/campaign33.py --token C4_CF`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-13 08:17:05 PDT.  Runtime 2401 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Aer statevector per trajectory (GPU), checkpoints in memory; device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode None; GPUs 1; tasks 1; wall 2401 s; GPU node-hours (shared QOS, G/4 x t) 0.1667; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.4755; peak GPU memory 473 MiB; mean GPU utilisation 2.197 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 14.0, trajectories_s 2400.5.

## Arms (r at delta 1e-3)

| arm | K | r | r 95 % | f_hit | f_ideal | floor min |
|---|---|---|---|---|---|---|
| B0_ref25_k1 | 1232 | 1.061 | [1.035, 1.09] | 0.2532 | 0.2386 | 1.057 |
| B1_ref57_k1 | 1262 | 1.048 | [1.016, 1.082] | 0.235 | 0.2242 | 1.048 |
| B0_ref25_k4 | 1244 | 1.172 | [1.128, 1.217] | 0.2478 | 0.2114 | 1.172 |
| B0_ref25_k1__xx | 1239 | 1.052 | [1.029, 1.075] | 0.1831 | 0.1741 | 1.052 |

## Pooled k = 1 r(1e-3) and r_nc

| pooled r | 95 % | new r_nc | old r_nc | old pooled 95 % |
|---|---|---|---|---|
| 1.055 | [1.033, 1.078] | 1.078 | 1.115 | [1.029, 1.115] |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P16 r per arm with 95 % bootstrap intervals; pooled r; new r_nc = its upper end | {'B0_ref25_k1': 1.0609849861673817, 'B1_ref57_k1': 1.0483133476577402, 'B0_ref25_k4': 1.1720203542733039, 'B0_ref25_k1__xx': 1.0516929598521412} | fields present | PASS |
| P17 floor theorem (CF_traj C4'): min_S99 f_eff / f_ideal(1e-3) >= 0.95 on every arm | {'B0_ref25_k1': 1.0566536447076567, 'B1_ref57_k1': 1.0483133476577216, 'B0_ref25_k4': 1.1720203542732954, 'B0_ref25_k1__xx': 1.051692959852136} | >= 0.95 | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 2401 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | {'B0_ref25_k1': 1232, 'B1_ref57_k1': 1262, 'B0_ref25_k4': 1244, 'B0_ref25_k1__xx': 1239} | no reduction below the minimum | FAIL |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C4_CF.json`.
