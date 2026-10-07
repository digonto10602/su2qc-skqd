# DRY RUN (laptop path check, reduced size): Campaign 33 token C2_GATE (class 2): I-GATE on IBM-U, both K1 circuits

**Status: PASS** — `python scripts/campaign33.py --token C2_GATE --dry-run`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cb7753f, 2026-10-06 18:04:42 MDT.  Runtime 76 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

> **DRY RUN** — a laptop path check at reduced size (shots x 0.01, <= 16 shots per run() call, at most 4 circuits per family/sector, CPU).  Physics criteria are listed as information; the status is the structural criteria only.  No number here is a campaign result.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device CPU (requested CPU, available ['CPU']); GPU mode cpu; GPUs None; tasks None; wall 76 s; GPU node-hours (shared QOS, G/4 x t) None; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 72.56; peak GPU memory None MiB; mean GPU utilisation None %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'python': '3.12.14'}.  Phases (s): noise_model_build_s 49.0, sampling_and_decoding_s 72.6.

## I-GATE on IBM-U

| circuit | T2 | shots | accepted | hits | accepted per 1e5 | hits per 1e5 | K1 accepted | K1 hits | P(K1 accepted | model) | roundtrip mismatches |
|---|---|---|---|---|---|---|---|---|---|---|
| B0_ref117_k1 | echo | 1 | 0 | 0 | 0 | 0 | 58 | 0 | None | 0 |

## Physics criteria (information in a dry run)

| check | value | criterion | would pass |
|---|---|---|---|
| P6 decoder round trip on every accepted string | {'B0_ref117_k1|echo': 0} | 0 mismatches | True |
| P7 simulated accepted counts and reference hits reported with the two-sided Poisson probability of the measured K1 values (58 / 45 accepted, 0 / 0 hits at 1e5) | True | fields exist (no threshold) | True |

## Notes

- dry run: PTA representation and 1 shot per run (path check); the CI uses C2_CAL's decision
- dry run: one circuit (B0_ref117_k1) per T2 convention (the CI runs both K1 circuits)
- shots per circuit 1 below the 1e5 target (target 1e5 per circuit, fitted to the budget at 61.45 s/shot (dry run: PTA at 61.454899072647095 s/shot (validation/dryrun/C2_CAL.json)); dry run: 1 shot per run (path check))

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| S1 the run happened on the requested device | CPU (available ['CPU']) | as requested | PASS |
| S2 wall time inside the walltime budget | 76 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': False} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's) | full | shots > 0 on every unit | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/dryrun/C2_GATE.json`.
