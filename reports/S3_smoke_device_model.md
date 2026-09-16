# Gate S3 (smoke) — device-model sampling of the 2x3 B=1 circuit set

**Status: FAIL** — `scripts/s3_device_model.py --lattice 3
--sector 1 --shots-per-sector 24 --tag smoke`.
Run kind: **smoke (pipeline test, NOT the production budget)**.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 1223e92, 2026-09-16 11:46:01 MDT.  Runtime 295 s.

Noise model: all-to-all RZZ depolarizing model of the declared inputs eps2 = 0.001, eps1 = 0.0001, eps_ro = 0.002.
Aer device **CPU** (available: ['CPU'],
batched_shots_gpu = False).

## Sampling

12 circuits (references x k = 1..4, r = 1 repetition(s) of the coarse step) on
20 qubits, 2 shots each = 24 shots;
2158 two-qubit gates per circuit on average.

| reference | k | 2q gates | shots | accepted | yield | s/shot |
|---|---|---|---|---|---|---|
| 57 | 1 | 2158 | 2 | 0 | 0.000 | 10.31 |
| 57 | 2 | 2158 | 2 | 2 | 1.000 | 10.04 |
| 57 | 3 | 2158 | 2 | 1 | 0.500 | 10.26 |
| 57 | 4 | 2158 | 2 | 1 | 0.500 | 13.10 |
| 29 | 1 | 2158 | 2 | 1 | 0.500 | 10.02 |
| 29 | 2 | 2158 | 2 | 1 | 0.500 | 10.13 |
| 29 | 3 | 2158 | 2 | 2 | 1.000 | 10.00 |
| 29 | 4 | 2158 | 2 | 0 | 0.000 | 10.14 |
| 27 | 1 | 2158 | 2 | 1 | 0.500 | 10.22 |
| 27 | 2 | 2158 | 2 | 0 | 0.000 | 10.39 |
| 27 | 3 | 2158 | 2 | 1 | 0.500 | 10.14 |
| 27 | 4 | 2158 | 2 | 0 | 0.000 | 10.30 |

Accepted yield 0.4167 (implied f = yield / 0.82 = 0.5081);
rejections {'flag': 7, 'link': 2, 'sector': 5, 'unknown': 0}.

## Support and certification

|B| = 7 (7 decoded + the references) of a
426-dimensional sector; recall of the 99.9 % support
(95 states) = **0.0737**, captured weight
0.784843, false positives 0.
E_R = -3.158312 against the exact E_0 = -3.826084 (error 6.68e-01),
r_H = 1.457e+00, Weinstein [-4.6153, -3.1583].

## Cost and the production job

10.421 s per shot measured here, at 2 shots per simulator call.
the measured seconds per shot include the fixed per-call overhead of one AerSimulator.run (circuit load, noise-model binding); it amortises at large shot counts, so a short run over-estimates the production cost: gate S2D measured 3.20 s/shot at
10 shots per call on the same laptop CPU (validation/S2D.json), which projects to
178 h per sector instead.
A 2e+05-shot sector at the rate measured HERE costs
**579.0 h** on this device and the four 2x3 jobs of manual Step 9.2
(B = 0 and B = 1, r = 1 and r = 2) cost 2315.8 h.  The same command with a GPU
available uses `device='GPU', batched_shots_gpu=True`; `slurm/s3_2x3.sbatch` submits the four jobs.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| 2x3 B=1: recall of the 99.9 % support (95 states) with 24 shots | 0.0737 | >= 0.9 | FAIL |
| 2x3 B=1: exact E0 = -3.8261 inside the Weinstein interval | [-4.6153, -3.1583] | contains the exact E0 | PASS |

Every number above is computed by `scripts/s3_device_model.py` and stored in `validation/S3_smoke.json`.
