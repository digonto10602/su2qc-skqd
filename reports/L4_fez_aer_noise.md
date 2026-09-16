# Laptop gate L4_fez — Aer noise-model sampling at 2x2 (S3 preparation)

**Status: PASS** — `scripts/laptop_L4_aer_noise.py`, NoiseModel.from_backend(FakeFez) (calibration snapshot: per-edge CZ, per-qubit readout, T1/T2), circuits transpiled onto FakeFez at optimization level 3, seed 7,
device CPU, budget 25.0 min, pilot 50 shots, min-shots 1.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 7c8150f, 2026-09-16 07:15:55 MDT.  Runtime 530 s.

| sector | circuits | shots/circuit | mean CZ | f (model) | predicted yield | measured yield | measured / predicted | \|B\| | E_R − E_0 | recall 99.9% | fp | Weinstein | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 20 | 331 | 663 | 0.126 | 0.103 | 0.144 | 1.39 | 38 | 0.0e+00 | 1.00 | 0 | [-3.6408, -3.6408] | {'flag': 3214, 'link': 2090, 'sector': 364, 'unknown': 0} |
| B=1 | 8 | 895 | 663 | 0.121 | 0.100 | 0.138 | 1.39 | 20 | 0.0e+00 | 1.00 | 0 | [-1.8616, -1.8616] | {'flag': 3864, 'link': 1664, 'sector': 643, 'unknown': 0} |

| check | value | criterion | result |
|---|---|---|---|
| B=0: measured yield within a factor 3 of the proxy 0.82 f, f from the FakeFez calibration (gate S2D) | 0.144 vs 0.103 (ratio 1.39) | ratio in [1/3, 3] (the proxy is a rough model) | PASS |
| B=0: exact E0 inside the Weinstein interval | -3.6408 | inside | PASS |
| B=1: measured yield within a factor 3 of the proxy 0.82 f, f from the FakeFez calibration (gate S2D) | 0.138 vs 0.100 (ratio 1.39) | ratio in [1/3, 3] (the proxy is a rough model) | PASS |
| B=1: exact E0 inside the Weinstein interval | -1.8616 | inside | PASS |

Note: at 2x2 the sectors saturate (38 and 20 states), so the Ritz error is a consistency check only (manual
Step 9.1).  The prediction column is 0.103 / 0.100 = the proxy "0.82 f, f from the FakeFez calibration (gate S2D)"; with --backend it is the
0.82 f of gate S2D, computed from the same calibration snapshot as `validation/S2D.json`, so the ratio column is
the H0 rehearsal number (how well the manual's yield model describes a full device simulation).
