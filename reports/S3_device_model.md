# Gate S3 — GPU throughput calibration of the 2x3 B=0 circuit set (reduced size; the S3 recall criterion is NOT evaluated)

**Status: PASS** (calibration criteria only — gate S3 itself is NOT evaluated here) — `scripts/s3_device_model.py --lattice 3 --sector 0
--shots-per-sector 3200 --calibration
--tag ""`.  Run kind: **CALIBRATION (throughput at 20 qubits; the S3 recall criterion is NOT evaluated and the yield/recall below are measurements at the calibration shot count, not gate results)**.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-09-22 18:01:22 PDT.  Runtime 248 s.

> **This is a reduced-size THROUGHPUT CALIBRATION, not gate S3.**  NOT EVALUATED in a calibration run (recall >= 0.9 with the production budget is the gate; this job measures compute throughput).
> The yield and recall below are measurements at the calibration shot count and are **not** gate
> results.  gate L4's 19.8x GPU speed-up is at 12 qubits and must NOT be extrapolated to this gate: at 20 qubits each statevector is 256x larger and the run is chunk-dominated (prompts/18 sec. 2.1).

Noise model: all-to-all RZZ depolarizing model of the declared inputs eps2 = 0.001, eps1 = 0.0001, eps_ro = 0.002.
Aer device **GPU** (available: ['CPU', 'GPU'],
batched_shots_gpu = True).

## Sampling

32 circuits (references x k = 1..4, r = 1 repetition(s) of the coarse step) on
20 qubits, 100 shots each = 3200 shots
(as requested; 100 requested);
2162 two-qubit gates per circuit on average.

| reference | k | 2q gates | shots | accepted | yield |
|---|---|---|---|---|---|
| 25 | 1 | 2162 | 100 | 43 | 0.430 |
| 25 | 2 | 2162 | 100 | 13 | 0.130 |
| 25 | 3 | 2162 | 100 | 27 | 0.270 |
| 25 | 4 | 2162 | 100 | 29 | 0.290 |
| 795 | 1 | 2162 | 100 | 30 | 0.300 |
| 795 | 2 | 2162 | 100 | 14 | 0.140 |
| 795 | 3 | 2162 | 100 | 42 | 0.420 |
| 795 | 4 | 2162 | 100 | 18 | 0.180 |
| 525 | 1 | 2162 | 100 | 14 | 0.140 |
| 525 | 2 | 2162 | 100 | 15 | 0.150 |
| 525 | 3 | 2162 | 100 | 23 | 0.230 |
| 525 | 4 | 2162 | 100 | 11 | 0.110 |
| 333 | 1 | 2162 | 100 | 19 | 0.190 |
| 333 | 2 | 2162 | 100 | 9 | 0.090 |
| 333 | 3 | 2162 | 100 | 37 | 0.370 |
| 333 | 4 | 2162 | 100 | 24 | 0.240 |
| 169 | 1 | 2162 | 100 | 1 | 0.010 |
| 169 | 2 | 2162 | 100 | 24 | 0.240 |
| 169 | 3 | 2162 | 100 | 33 | 0.330 |
| 169 | 4 | 2162 | 100 | 24 | 0.240 |
| 117 | 1 | 2162 | 100 | 14 | 0.140 |
| 117 | 2 | 2162 | 100 | 26 | 0.260 |
| 117 | 3 | 2162 | 100 | 14 | 0.140 |
| 117 | 4 | 2162 | 100 | 44 | 0.440 |
| 86 | 1 | 2162 | 100 | 26 | 0.260 |
| 86 | 2 | 2162 | 100 | 21 | 0.210 |
| 86 | 3 | 2162 | 100 | 14 | 0.140 |
| 86 | 4 | 2162 | 100 | 18 | 0.180 |
| 70 | 1 | 2162 | 100 | 31 | 0.310 |
| 70 | 2 | 2162 | 100 | 8 | 0.080 |
| 70 | 3 | 2162 | 100 | 21 | 0.210 |
| 70 | 4 | 2162 | 100 | 8 | 0.080 |

Accepted yield 0.2172 (implied f = yield / 0.82 = 0.2649);
rejections {'flag': 1460, 'link': 796, 'sector': 249, 'unknown': 0}.  Per-circuit times are not separable: the whole sector goes through
one chunked `sample_many` call set, which is what the HPC policy asks for.

## Support and certification

|B| = 58 (58 decoded + the references) of a
677-dimensional sector; recall of the 99.9 % support
(86 states) = **0.5233**, captured weight
0.988220, false positives 0.
E_R = -5.542788 against the exact E_0 = -5.602600 (error 5.98e-02),
r_H = 5.808e-01, Weinstein [-6.1236, -5.5428].

## Cost and the production job

**Engine and resources** (RUNBOOK.md policy): engine Qiskit Aer statevector (GPU, cuStateVec/batched shots), qiskit 1.4.3 / aer 0.15.1, device GPU (requested auto, available ['CPU', 'GPU']), GPUs 1, tasks 1, walltime 245 s, E(p) not measured (E(p) needs T_1 and T_p from at least two task counts; this run is a single task, so it is not measured), GPU node-hours used 0.0681, peak GPU memory 1783 MiB, GPU utilization 30.0 % mean, 100 % peak over 25 nvidia-smi samples.  Phases (s): transpile_s 40.4, ladder_s 45.6, sampling_s 149.7, analysis_s 0.0.  Memory model: 476 shots per run() call for one circuit and 14 for all 32 at 8e+09 model bytes (x3.5 measured in L4 = 2.8e+10 real bytes); the sampling used 32 circuits x 14 shots in 8 run() call(s) with 0 out-of-memory retries.

Timing ladder on one circuit (chunked exactly as the sampling is, so the points above the chunk bound measure the chunked regime):

| shots | seconds | s/shot | run calls |
|---|---|---|---|
| 47 | 1.19 | 0.02530 | 1 |
| 238 | 4.96 | 0.02083 | 1 |
| 476 | 9.56 | 0.02008 | 1 |
| 1428 | 28.37 | 0.01987 | 3 |

0.0468 s per shot measured over the batched sector;
0.01987 s per shot at the cheapest ladder point.
the seconds per shot are measured over the whole batched sector and include the per-call set-up of every chunked run (circuit load, noise-model binding); the projection uses the cheapest ladder point when a ladder was run.  For comparison, gate S2D measured 3.20 s/shot at 10 shots per call on the laptop CPU (validation/S2D.json), which projects to 178 h per sector.
A 2e+05-shot sector at
0.01987 s/shot costs
**1.1 h** on this device and the four 2x3 jobs of manual
Step 9.2 (B = 0 and B = 1, r = 1 and r = 2) cost 4.4 h.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| calibration: Aer ran on the requested device (auto, GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| calibration: the timing ladder measured at least two shot counts | 4 of 4 points | >= 2 points | PASS |
| calibration: the batched sampling fitted the assumed GPU memory | 0 out-of-memory retries at 32 circuits x 14 shots per run() call | no OOM retry | PASS |
| calibration: wall time inside the budget the CI allows | 245 s | <= 3300 s | PASS |

Every number above is computed by `scripts/s3_device_model.py` and stored in `validation/S3.json`.
