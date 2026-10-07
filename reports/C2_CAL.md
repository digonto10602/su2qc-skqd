# Campaign 33 token C2_CAL (class 2): 21-qubit timing ladder {8,32,128,512} on B0_ref117_k1 (IBM-T0), Kraus vs PTA, cuStateVec vs batched; sizes C2_*

**Status: FAIL** — `python scripts/campaign33.py --token C2_CAL`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-07 10:07:52 PDT.  Runtime 779 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec; GPUs 1; tasks 1; wall 779 s; GPU node-hours (shared QOS, G/4 x t) 0.0541; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 3.177; peak GPU memory 2491 MiB; mean GPU utilisation 48.35 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'python': '3.12.14'}.  Phases (s): ladder_s 766.8.

## Timing ladder (I-ECHO on IBM-T0 B0_ref117_k1)

| representation|mode | shots | s | s/shot | accepted |
|---|---|---|---|---|
| kraus|custatevec | 8 | 55.04 | 6.88 | 0 |
| kraus|custatevec | 32 | 101.7 | 3.177 | 1 |
| kraus|custatevec | 128 | None | None | None |
| kraus|custatevec | 512 | None | None | None |
| kraus|batched | 8 | 84.21 | 10.53 | 0 |
| kraus|batched | 32 | None | None | None |
| kraus|batched | 128 | None | None | None |
| kraus|batched | 512 | None | None | None |
| pta|custatevec | 8 | 14.7 | 1.838 | 0 |
| pta|custatevec | 32 | 25.41 | 0.7941 | 0 |
| pta|custatevec | 128 | 47.85 | 0.3738 | 0 |
| pta|custatevec | 512 | 138.1 | 0.2697 | 1 |
| pta|batched | 8 | 18.29 | 2.287 | 0 |
| pta|batched | 32 | 46.32 | 1.447 | 0 |
| pta|batched | 128 | 141.6 | 1.106 | 0 |
| pta|batched | 512 | None | None | None |

## Kraus vs PTA agreement

| mode | kraus [acc, N] | pta [acc, N] | z | agree 3 sigma |
|---|---|---|---|---|
| custatevec | None | None | None | None |
| batched | None | None | None | None |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P4 Kraus vs PTA accepted fractions within 3 sigma at >= 512 shots (else kraus_only, still PASS) | {'custatevec': None, 'batched': None} | <= 3 sigma, or representation kraus_only | PASS |
| P5 timing ladder >= 2 points per mode | {'kraus|custatevec': 2, 'kraus|batched': 1, 'pta|custatevec': 4, 'pta|batched': 3} | >= 2 per (representation, mode) | FAIL |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 779 s | <= min(walltime 2700 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | full | no reduction below the minimum | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C2_CAL.json`.
