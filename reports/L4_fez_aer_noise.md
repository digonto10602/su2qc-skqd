# Laptop gate L4_fez — Aer noise-model sampling at 2x2 (S3 preparation)

**Status: PASS** — `scripts/laptop_L4_aer_noise.py`, NoiseModel.from_backend(FakeFez) (calibration snapshot: per-edge CZ, per-qubit readout, T1/T2), circuits transpiled onto FakeFez at optimization level 3, seed 7,
device CPU, budget 20.0 min, pilot 50 shots, min-shots 1.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 3722018, 2026-09-16 12:28:26 MDT.  Runtime 450 s.

| sector | circuits | shots/circuit | mean CZ | f (model) | a (garbage) | predicted 0.8200 f (first term only) | predicted 0.8200 f + (1−f) a | measured yield | measured / first term | measured / full model | \|B\| | E_R − E_0 | recall 99.9% | fp | Weinstein | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 20 | 258 | 663 | 0.126 | 0.00928 | 0.103 | 0.112 | 0.147 | 1.42 | 1.32 | 38 | 0.0e+00 | 1.00 | 0 | [-3.6408, -3.6408] | {'flag': 2505, 'link': 1609, 'sector': 289, 'unknown': 0} |
| B=1 | 8 | 722 | 663 | 0.121 | 0.00488 | 0.100 | 0.104 | 0.136 | 1.36 | 1.31 | 20 | 0.0e+00 | 1.00 | 0 | [-1.8616, -1.8616] | {'flag': 3138, 'link': 1336, 'sector': 519, 'unknown': 0} |

| check | value | criterion | result |
|---|---|---|---|
| B=0: measured yield within a factor 3 of the model 0.82 f + (1-f) a, f from the FakeFez calibration (gate S2D), a = 0.00928 exhaustive | 0.147 vs 0.112 (ratio 1.32; the first term alone, 0.8200 f = 0.103, gives 1.42) | ratio in [1/3, 3] (the model is a rough proxy) | PASS |
| B=0: exact E0 inside the Weinstein interval | -3.6408 | inside | PASS |
| B=1: measured yield within a factor 3 of the model 0.82 f + (1-f) a, f from the FakeFez calibration (gate S2D), a = 0.00488 exhaustive | 0.136 vs 0.104 (ratio 1.31; the first term alone, 0.8200 f = 0.100, gives 1.36) | ratio in [1/3, 3] (the model is a rough proxy) | PASS |
| B=1: exact E0 inside the Weinstein interval | -1.8616 | inside | PASS |

Note: at 2x2 the sectors saturate (38 and 20 states), so the Ritz error is a consistency check only (manual
Step 9.1).  The prediction the criterion uses is the manual's Step-4.4 yield model with BOTH its terms,
y = 0.82 f + (1-f) a ("the accepted-shot yield is ~ 0.82 f plus the garbage that decodes as valid",
`skqd.skqd.yield_model`): a = the decoder's random-string acceptance of the sector, measured exhaustively
over all 4096 bit strings (0.00928 for B=0, 0.00488 for B=1), and with --backend f is the
0.82 f-fraction of gate S2D computed from the same calibration snapshot as `validation/S2D.json`.  The column
"measured / 0.82 f" is the first term alone, the model this gate used before prompts/14, kept for comparison.
The ratio against the full model is the H0 rehearsal number (how well the manual's yield model describes a
full device simulation).
