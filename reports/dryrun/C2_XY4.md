# DRY RUN (laptop path check, reduced size): Campaign 33 token C2_XY4 (class 2): I-XY4 on IBM-T3, echo and star halves (information)

**Status: PASS** — `python scripts/campaign33.py --token C2_XY4 --dry-run`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 6e2cdaf, 2026-10-18 13:55:21 MDT.  Runtime 239 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 239 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 59.16; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 0.7, noise_model_build_s 110.9, sampling_and_decoding_s 124.0.

## I-XY4 on IBM-T3: arms vs the K1 strings

| arm | run | representation | shots | mean weight | K1 mean weight | z weight | max |z| marginal | accepted | hits | P(K1 accepted | model) | counts power | roundtrip mismatches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| production | B0_ref117_k1|echo | pta | 1 | 13 | 9.771 | 451.8 | 334.1 | 0 | 0 | None | underpowered | 0 |
| production | B1_ref29_k1|echo | pta | 1 | 10 | 9.769 | 32.26 | 355.8 | 0 | 0 | None | underpowered | 0 |

## In-cell RM (production) vs Kraus (no reference arm) (information)

| run | z mean weight | max |z| marginal | pass |
|---|---|---|---|

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P6 decoder round trip on every accepted string (both arms) | {'production:B0_ref117_k1|echo': 0, 'production:B1_ref29_k1|echo': 0} | 0 mismatches | True |
| P7' K1 comparison per run: Poisson probabilities of the measured 58 / 45 accepted and 0 / 0 hits, the z table of the mean Hamming weight and every marginal, comparison_power; no reference arm (no validated Kraus GPU path) | {'B0_ref117_k1|echo': 'underpowered/like_for_like', 'B1_ref29_k1|echo': 'underpowered/like_for_like'} | fields present (no threshold) | True |

## Notes

- dry run: PTA stands in for every arm (rm production), 1 shot per run -- a path check, not the CI's channels

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S0 representation decided (prompts/33f R2: data/campaign33/c2_representation_decision.json production_representation = rm; never a silent default) | {'file': 'data/campaign33/c2_representation_decision.json', 'sha256': '3cad544f32abcfdc6335e3aaab9bef7d2f6f6685afbe19bbccebfa6edb54f7ee', 'production_representation': 'rm', 'reference_arm': 'none', 'stub': False} | the decision file present with production_representation rm | PASS |
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 239 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False, 'cpu_affinity': 12, 'slurm_cpus_per_task': None} | every policy field non-null on the CI and cpu_affinity == SLURM_CPUS_PER_TASK there; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C2_XY4.json`.
