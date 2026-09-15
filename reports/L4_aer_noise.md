# Laptop gate L4 — Aer noise-model sampling at 2x2 (S3 preparation)

**Status: FAIL** — `scripts/laptop_L4_aer_noise.py`, p1 = 0.0003, p2 = 0.001, readout 0.01,
device CPU, budget 12.0 min, pilot 20 shots, min-shots 1.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 30684f2, 2026-09-14 18:24:06 MDT.  Runtime 1012 s.

| sector | circuits | shots/circuit | mean CZ (level 1) | f=<(1-p2)^CZ> | (1-p_ro)^n f | measured yield | |B| | E_R − E_0 | recall 99.9% | fp | Weinstein | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 20 | 8 | 35670 | 0.000 | 0.000 | 0.013 | 7 | 7.4e-02 | 0.38 | 0 | [-4.1866, -3.5666] | {'flag': 111, 'link': 46, 'sector': 1, 'unknown': 0} |
| B=1 | 8 | 22 | 35670 | 0.000 | 0.000 | 0.006 | 3 | 3.6e-01 | 0.23 | 0 | [-2.5308, -1.5000] | {'flag': 118, 'link': 53, 'sector': 4, 'unknown': 0} |

| check | value | criterion | result |
|---|---|---|---|
| B=0: measured yield within a factor 3 of the proxy (1-p_ro)^n f, f = <(1-p2)^CZ> | 0.013 vs 0.000 | ratio in [1/3, 3] (the proxy is a rough model) | FAIL |
| B=0: exact E0 inside the Weinstein interval | -3.6408 | inside | PASS |
| B=1: measured yield within a factor 3 of the proxy (1-p_ro)^n f, f = <(1-p2)^CZ> | 0.006 vs 0.000 | ratio in [1/3, 3] (the proxy is a rough model) | FAIL |
| B=1: exact E0 inside the Weinstein interval | -1.8616 | inside | PASS |

Note: at 2x2 the sectors saturate (38 and 20 states), so the Ritz error is a consistency check only (manual
Step 9.1).  A real S3 run replaces `generic_noise_model` by `NoiseModel.from_backend(backend)` built from the
target device's calibration and uses the 2x3 circuits once the plaquette gate with interior corners exists (S2-b).
