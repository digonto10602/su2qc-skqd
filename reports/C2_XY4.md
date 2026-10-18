# Campaign 33 token C2_XY4 (class 2): I-XY4 on IBM-T3, echo and star halves (information)

**Status: PASS** — `python scripts/campaign33.py --token C2_XY4`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-18 15:53:29 PDT.  Runtime 1765 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode custatevec; GPUs 1; tasks 1; wall 1765 s; GPU node-hours (shared QOS, G/4 x t) 0.1226; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.3399; peak GPU memory 2295 MiB; mean GPU utilisation 85.74 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 39.4, noise_model_build_s 10.2, sampling_and_decoding_s 1745.4.

## I-XY4 on IBM-T3: arms vs the K1 strings

| arm | run | representation | shots | mean weight | K1 mean weight | z weight | max |z| marginal | accepted | hits | P(K1 accepted | model) | counts power | roundtrip mismatches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| production | B0_ref117_k1|echo | rm | 2544 | 9.787 | 9.771 | 0.3571 | 4.408 | 4 | 0 | 1.58e-19 | underpowered | 0 |
| production | B1_ref29_k1|echo | rm | 2544 | 9.736 | 9.769 | -0.7241 | 4.864 | 1 | 0 | 0.3387 | underpowered | 0 |

## In-cell RM (production) vs Kraus (no reference arm) (information)

| run | z mean weight | max |z| marginal | pass |
|---|---|---|---|

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S0 representation decided (prompts/33f R2: data/campaign33/c2_representation_decision.json production_representation = rm; never a silent default) | {'file': 'data/campaign33/c2_representation_decision.json', 'sha256': '3cad544f32abcfdc6335e3aaab9bef7d2f6f6685afbe19bbccebfa6edb54f7ee', 'production_representation': 'rm', 'reference_arm': 'none', 'stub': False} | the decision file present with production_representation rm | PASS |
| P6 decoder round trip on every accepted string (both arms) | {'production:B0_ref117_k1|echo': 0, 'production:B1_ref29_k1|echo': 0} | 0 mismatches | PASS |
| P7' K1 comparison per run: Poisson probabilities of the measured 58 / 45 accepted and 0 / 0 hits, the z table of the mean Hamming weight and every marginal, comparison_power; no reference arm (no validated Kraus GPU path) | {'B0_ref117_k1|echo': 'underpowered/like_for_like', 'B1_ref29_k1|echo': 'underpowered/like_for_like'} | fields present (no threshold) | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 1765 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI; run.cpu_affinity == SLURM_CPUS_PER_TASK) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True, 'cpu_affinity': 32, 'slurm_cpus_per_task': 32} | every policy field non-null on the CI and cpu_affinity == SLURM_CPUS_PER_TASK there; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | full | no reduction below the minimum | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C2_XY4.json`.
