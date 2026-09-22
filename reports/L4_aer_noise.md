# Laptop gate L4 — Aer noise-model sampling at 2x2 (S3 preparation)

**Status: PASS** — `scripts/laptop_L4_aer_noise.py`, generic depolarizing model p1 = 0.0003, p2 = 0.003, readout 0.01,
device GPU, budget 25.0 min, pilot 1000 shots, min-shots 500.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.28-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-09-22 01:22:38 PDT.  Runtime 677 s.

| sector | circuits | shots/circuit | mean CZ | f (model) | a (garbage) | predicted 0.8864 f (first term only) | predicted 0.8864 f + (1−f) a | measured yield | measured / first term | measured / full model | \|B\| | E_R − E_0 | recall 99.9% | fp | Weinstein | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 20 | 20000 | 288 | 0.421 | 0.00928 | 0.373 | 0.378 | 0.458 | 1.23 | 1.21 | 38 | 0.0e+00 | 1.00 | 0 | [-3.6408, -3.6408] | {'flag': 116192, 'link': 70609, 'sector': 30024, 'unknown': 0} |
| B=1 | 8 | 20000 | 288 | 0.421 | 0.00488 | 0.373 | 0.376 | 0.441 | 1.18 | 1.17 | 20 | 0.0e+00 | 1.00 | 0 | [-1.8616, -1.8616] | {'flag': 52310, 'link': 19165, 'sector': 17955, 'unknown': 0} |

| check | value | criterion | result |
|---|---|---|---|
| B=0: measured yield within a factor 3 of the model (1-p_ro)^n f + (1-f) a, f = <(1-p2)^CZ>, a = 0.00928 exhaustive | 0.458 vs 0.378 (ratio 1.21; the first term alone, 0.8864 f = 0.373, gives 1.23) | ratio in [1/3, 3] (the model is a rough proxy) | PASS |
| B=0: exact E0 inside the Weinstein interval | -3.6408 | inside | PASS |
| B=1: measured yield within a factor 3 of the model (1-p_ro)^n f + (1-f) a, f = <(1-p2)^CZ>, a = 0.00488 exhaustive | 0.441 vs 0.376 (ratio 1.17; the first term alone, 0.8864 f = 0.373, gives 1.18) | ratio in [1/3, 3] (the model is a rough proxy) | PASS |
| B=1: exact E0 inside the Weinstein interval | -1.8616 | inside | PASS |

**Engine and resources** (RUNBOOK.md policy): engine Qiskit Aer statevector (GPU, cuStateVec/batched shots), qiskit 1.4.3 / aer 0.15.1, device GPU, GPUs not measured, tasks 1, walltime 677 s, E(p) not measured (E(p) needs T_1 and T_p from at least two task counts; this run is a single task, so it is not measured), GPU node-hours used not measured, peak GPU memory 27915 MiB, GPU utilization 15.3 % mean, 27 % peak over 68 nvidia-smi samples. Cheapest measured cost 0.00103 s/shot (timing ladder at 2000 shots), so a full-size run of this gate (the same 2x2 circuits at the per-sector shot quota of data/S2D_recall_at_f.json (32 circuits x 6250 shots), both sectors, 400000 shots) would take 0.11 h on this device.  The 2x3 cost of gate S3 is not extrapolated from this ladder: 20 qubits is a different simulation.

Timing ladder on one circuit, device GPU with batched_shots_gpu (the per-shot cost falls as the batch grows, so a run at a different shot count cannot be sized from a single pilot point):

| shots | seconds | s/shot |
|---|---|---|
| 20 | 0.21 | 0.01056 |
| 100 | 0.29 | 0.00291 |
| 500 | 0.65 | 0.00129 |
| 1000 | 1.06 | 0.00106 |
| 2000 | 2.06 | 0.00103 |

Note: at 2x2 the sectors saturate (38 and 20 states), so the Ritz error is a consistency check only (manual
Step 9.1).  The prediction the criterion uses is the manual's Step-4.4 yield model with BOTH its terms,
y = 0.82 f + (1-f) a ("the accepted-shot yield is ~ 0.82 f plus the garbage that decodes as valid",
`skqd.skqd.yield_model`): a = the decoder's random-string acceptance of the sector, measured exhaustively
over all 4096 bit strings (0.00928 for B=0, 0.00488 for B=1), and with --backend f is the
0.82 f-fraction of gate S2D computed from the same calibration snapshot as `validation/S2D.json`.  The column
"measured / 0.82 f" is the first term alone, the model this gate used before prompts/14, kept for comparison.
The ratio against the full model is the H0 rehearsal number (how well the manual's yield model describes a
full device simulation).
