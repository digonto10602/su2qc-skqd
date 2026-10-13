# Campaign 33 token C4_F4_B0a (class 4): E7(0.10) x O0, S3-quota half a, B=0 (1e5)

**Status: PASS** — `python scripts/campaign33.py --token C4_F4_B0a`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-13 11:21:08 PDT.  Runtime 1395 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec; GPUs 1; tasks 1; wall 1395 s; GPU node-hours (shared QOS, G/4 x t) 0.09686; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.02634; peak GPU memory 1783 MiB; mean GPU utilisation 52.82 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 15.5, sampling_s 1323.8, bootstrap_and_readout_s 59.5, analysis_s 59.6.

## C4_F4_B0a: E7_0.10 x NAT-O0, B=0, s3quota half a, part 1 of 2

| shots | |B_all| | E_R - E0 | certificate | width | E0 inside | recall S999 | W | f_hit (k=1) | f_hat_ideal 95 % |
|---|---|---|---|---|---|---|---|---|---|
| 50016 | 376 | 0.0001212 | kato_temple_exact_E1 | 0.0004585 | True | 1 | 1 | 0.1943 | [0.1671, 0.1816] |

## Notes

- part 1 of 2 per data/campaign33/sizing_33a.json (written from validation/C4_FCELLS_A.json job 59570315; validation/C4_FCELLS_B.json (absent: not yet harvested))

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P13 (part 1 of 2) E_R >= E0 - 1e-9 on this part's shots (CV0 and the certificate are read at assembly on the merged parts) | {'variational': True, 'E0_inside_information': True} | variational | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 1395 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum (C4_F*: the plan of record in full) | full | no reduction below the minimum | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C4_F4_B0a.json`.
