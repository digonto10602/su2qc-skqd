# Gate H0P — H0 preparation on the FakeFez calibration snapshot

**Status: PASS** — `scripts/gate_H0P.py` on the frozen circuit set of
`scripts/h0_build_circuits.py` (data/hardware/H0_prep, created 2026-09-16 09:57:38 MDT).
Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 3722018, 2026-09-16 12:51:12 MDT.  Runtime 1182 s.  Nothing in this gate touches a QPU.

## 1. The frozen circuit set

84 coarse-step circuits (both sectors, every reference, k = 1..4,
r = [1, 2, 3] repetitions of the step) plus 42 readout-calibration circuits
(all-0, all-1 and the 12 single-qubit flips on each of the
3 physical patches the transpiler chose), transpiled onto FakeFez at optimization
level 3, seed 7, and stored as QPY with one manifest JSON each.

| repetitions r | circuits | CZ mean | depth mean | f mean | f min | f max |
|---|---|---|---|---|---|---|
| 1 | 28 | 663 | 1340 | 0.1248 | 0.1166 | 0.1261 |
| 2 | 28 | 1305 | 2676 | 0.0159 | 0.0154 | 0.0185 |
| 3 | 28 | 1920 | 4008 | 0.0025 | 0.0022 | 0.0026 |

Leakage of the **transpiled** circuits (noiseless statevector, measurements removed, permuted back to
logical order with each circuit's own final layout, weight outside the codeword subspace):
max 1.49e-14 over 84 circuits, tolerance 1e-09.  The measurement map of every circuit
was checked against its final layout, so classical bit i of every counts key is logical qubit i.

## 2. Predicted yield curve by repetition

Sampling: `AerSimulator.from_backend(FakeFez(), seed_simulator=11)`, 267 shots per r = 1 circuit, 130 shots per r = 2 circuit, 92 shots per r = 3 circuit
(pinned with --shots-by-rep allocation, 13692 shots in total, 940 s; the pilot measured
0.030 s/shot at r=1, 0.063 s/shot at r=2, 0.090 s/shot at r=3,
i.e. 5.1 s per shot over the whole set, and the budget was 14 min).

| sector | r | circuits | CZ | f (calibration) | a (garbage) | model 0.82 f (old) | model 0.82 f + (1−f) a | shots | simulated yield | simulated / 0.82 f | simulated / full model | distinct states | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 1 | 20 | 663 | 0.1261 | 0.00928 | 0.1034 | 0.1115 | 5340 | 0.1493 | 1.44 | 1.34 | 38 | {'flag': 2453, 'link': 1782, 'sector': 308, 'unknown': 0} |
| B=0 | 2 | 20 | 1308 | 0.0154 | 0.00928 | 0.0127 | 0.0218 | 2600 | 0.0381 | 3.01 | 1.75 | 31 | {'flag': 1527, 'link': 913, 'sector': 61, 'unknown': 0} |
| B=0 | 3 | 20 | 1910 | 0.0026 | 0.00928 | 0.0021 | 0.0114 | 1840 | 0.0174 | 8.28 | 1.53 | 21 | {'flag': 1157, 'link': 619, 'sector': 32, 'unknown': 0} |
| B=1 | 1 | 8 | 663 | 0.1214 | 0.00488 | 0.0995 | 0.1038 | 2136 | 0.1353 | 1.36 | 1.30 | 20 | {'flag': 1150, 'link': 518, 'sector': 179, 'unknown': 0} |
| B=1 | 2 | 8 | 1296 | 0.0170 | 0.00488 | 0.0139 | 0.0187 | 1040 | 0.0288 | 2.07 | 1.54 | 13 | {'flag': 674, 'link': 293, 'sector': 43, 'unknown': 0} |
| B=1 | 3 | 8 | 1944 | 0.0024 | 0.00488 | 0.0020 | 0.0068 | 736 | 0.0109 | 5.57 | 1.59 | 6 | {'flag': 488, 'link': 218, 'sector': 22, 'unknown': 0} |

**The yield model.**  Manual Step 4.4: "the accepted-shot yield is ≈ 0.82 f plus the 0.15 % of garbage that
decodes as valid", i.e. y = 0.82 f + (1-f) a (`skqd.skqd.yield_model`).  The first term is the clean shots
that survive readout, with the f of gate S2D (per-edge CZ errors and per-qubit readout errors of the patch
the transpiler chose on this snapshot).  The second term is the non-clean fraction (1 − f) whose bit strings,
after ~1000 CZ, are close to uniformly random and are accepted whenever they happen to be a codeword of the
target sector: that happens with the decoder's random-string acceptance
a = B=0 0.00928, B=1 0.00488, measured
exhaustively over all 4096 bit strings in section 3.  The simulated column is the full Aer device model of the
same snapshot.  The criterion is the ratio "simulated / full model"; the column "simulated / 0.82 f" is the
first term alone, which is the model the gate used before prompts/14 — it describes the yield only while
f >> a / 0.82 = 0.011, i.e. at r = 1 here, and is kept in the table for comparison.
The prediction the H0 session will be judged against is the simulated yield itself (see
`reports/H0_prereg_draft.md`).  The shot plan of section 6 keeps using the CLEAN yield 0.82 f: a shot
accepted because its garbage string is a codeword adds no support.

## 3. Decoder validity

Exhaustive acceptance of random bit strings into each sector (4096 strings, the control of prompts/07):

| sector | accepted | fraction | rejection reasons |
|---|---|---|---|
| B=0 | 38 / 4096 | 0.928% | {'sector': 44, 'link': 1214, 'flag': 2800} |
| B=1 | 20 / 4096 | 0.488% | {'sector': 62, 'link': 1214, 'flag': 2800} |

## 4. Ritz consistency (bit order and conventions)

| sector | sector dimension | decoded states | with references | E_R | exact E_0 | \|E_R − E_0\| | r_H | recall of the 99.9 % support | false positives |
|---|---|---|---|---|---|---|---|---|---|
| B=0 | 38 | 38 | 38 | -3.6407665507 | -3.6407665507 | 0.00e+00 | 6.14e-15 | 1.000 | 0 |
| B=1 | 20 | 20 | 20 | -1.8615880345 | -1.8615880345 | 0.00e+00 | 1.51e-15 | 1.000 | 0 |

At 2x2 both sectors saturate, so this is a consistency check of the bit order and the conventions
(manual Step 9.1), not an accuracy test: a permuted codeword would give a different energy.

## 5. Readout confusion (simulated calibration circuits, 4000 shots each)

| patch | logical qubit | physical qubit | P(0\|0) | P(1\|1) | min diagonal |
|---|---|---|---|---|---|
| patch0 | 0 | 77 | 0.9915 | 0.9912 | 0.9912 |
| patch0 | 1 | 78 | 0.9768 | 0.9770 | 0.9768 |
| patch0 | 2 | 84 | 0.9980 | 0.9979 | 0.9979 |
| patch0 | 3 | 85 | 0.9867 | 0.9866 | 0.9866 |
| patch0 | 4 | 86 | 0.9956 | 0.9962 | 0.9956 |
| patch0 | 5 | 87 | 0.9804 | 0.9808 | 0.9804 |
| patch0 | 6 | 88 | 0.9954 | 0.9952 | 0.9952 |
| patch0 | 7 | 89 | 0.9839 | 0.9835 | 0.9835 |
| patch0 | 8 | 90 | 0.9975 | 0.9965 | 0.9965 |
| patch0 | 9 | 97 | 0.9957 | 0.9959 | 0.9957 |
| patch0 | 10 | 107 | 0.9924 | 0.9920 | 0.9920 |
| patch0 | 11 | 108 | 0.9957 | 0.9955 | 0.9955 |
| patch1 | 0 | 117 | 0.9915 | 0.9910 | 0.9910 |
| patch1 | 1 | 122 | 0.9935 | 0.9929 | 0.9929 |
| patch1 | 2 | 123 | 0.9944 | 0.9924 | 0.9924 |
| patch1 | 3 | 124 | 0.9962 | 0.9952 | 0.9952 |
| patch1 | 4 | 125 | 0.9873 | 0.9859 | 0.9859 |
| patch1 | 5 | 136 | 0.9958 | 0.9936 | 0.9936 |
| patch1 | 6 | 141 | 0.9946 | 0.9952 | 0.9946 |
| patch1 | 7 | 142 | 0.9937 | 0.9935 | 0.9935 |
| patch1 | 8 | 143 | 0.9959 | 0.9952 | 0.9952 |
| patch1 | 9 | 144 | 0.9896 | 0.9884 | 0.9884 |
| patch1 | 10 | 145 | 0.9852 | 0.9866 | 0.9852 |
| patch1 | 11 | 146 | 0.9934 | 0.9930 | 0.9930 |
| patch2 | 0 | 121 | 0.9821 | 0.9838 | 0.9821 |
| patch2 | 1 | 122 | 0.9936 | 0.9928 | 0.9928 |
| patch2 | 2 | 123 | 0.9932 | 0.9930 | 0.9930 |
| patch2 | 3 | 124 | 0.9949 | 0.9932 | 0.9932 |
| patch2 | 4 | 136 | 0.9948 | 0.9950 | 0.9948 |
| patch2 | 5 | 140 | 0.9911 | 0.9892 | 0.9892 |
| patch2 | 6 | 141 | 0.9951 | 0.9948 | 0.9948 |
| patch2 | 7 | 142 | 0.9933 | 0.9934 | 0.9933 |
| patch2 | 8 | 143 | 0.9950 | 0.9958 | 0.9950 |
| patch2 | 9 | 144 | 0.9882 | 0.9894 | 0.9882 |
| patch2 | 10 | 145 | 0.9867 | 0.9845 | 0.9845 |
| patch2 | 11 | 146 | 0.9940 | 0.9944 | 0.9940 |

`skqd.hardware.confusion_matrix` builds the tensored (independent-qubit) model from all
42 preparations; `skqd.hardware.apply_inverse` unfolds a counts dictionary with its exact tensor
inverse.  Smallest diagonal element over all patches: 0.9768.

## 6. Shot plan (manual eq. 5, `skqd.skqd.shot_rule`, p = 1e-03, k = 3, confidence 0.95)

| sector | r | circuits | simulated yield | clean yield 0.82 f | N/circuit (simulated) | N/sector (simulated) | N/circuit (clean 0.82 f) | N/sector (clean 0.82 f) |
|---|---|---|---|---|---|---|---|---|
| B=0 | 1 | 20 | 0.1493 | 0.1034 | 42183 | 8.437e+05 | 60872 | 1.217e+06 |
| B=0 | 2 | 20 | 0.0381 | 0.0127 | 165345 | 3.307e+06 | 497684 | 9.954e+06 |
| B=0 | 3 | 20 | 0.0174 | 0.0021 | 362009 | 7.240e+06 | 2998831 | 5.998e+07 |
| B=1 | 1 | 8 | 0.1353 | 0.0995 | 46533 | 3.723e+05 | 63270 | 5.062e+05 |
| B=1 | 2 | 8 | 0.0288 | 0.0139 | 218255 | 1.746e+06 | 452708 | 3.622e+06 |
| B=1 | 3 | 8 | 0.0109 | 0.0020 | 579214 | 4.634e+06 | 3227761 | 2.582e+07 |

The budget preregistered for the session is the one computed from the **clean** yield 0.82 f (last two
columns): a shot that is accepted only because its garbage string happens to be a codeword adds no support,
so the garbage term of the yield model must not enter the shot rule.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| every frozen circuit leak-free after transpilation onto FakeFez (84 circuits, noiseless statevector permuted back with the final layout) | 1.488e-14 | < 1e-09 | PASS |
| B=0: decoded support reproduces the exact E0 = -3.6408 | 0 | |E_R - E_0| < 1e-06 | PASS |
| B=1: decoded support reproduces the exact E0 = -1.8616 | 0 | |E_R - E_0| < 1e-06 | PASS |
| B=0: acceptance of random bit strings (exhaustive over all 4096 strings) | 0.928% | < 1% | PASS |
| B=1: acceptance of random bit strings (exhaustive over all 4096 strings) | 0.488% | < 1% | PASS |
| B=0 r=1 (663 CZ): simulated yield 0.149 vs the model 0.82 f + (1-f) a = 0.112 (a = 0.00928; the first term alone, 0.82 f = 0.103, gives 1.44) | 1.338 | ratio in [0.33, 3] | PASS |
| B=0 r=2 (1308 CZ): simulated yield 0.038 vs the model 0.82 f + (1-f) a = 0.022 (a = 0.00928; the first term alone, 0.82 f = 0.013, gives 3.01) | 1.748 | ratio in [0.33, 3] | PASS |
| B=0 r=3 (1910 CZ): simulated yield 0.017 vs the model 0.82 f + (1-f) a = 0.011 (a = 0.00928; the first term alone, 0.82 f = 0.002, gives 8.28) | 1.532 | ratio in [0.33, 3] | PASS |
| B=1 r=1 (663 CZ): simulated yield 0.135 vs the model 0.82 f + (1-f) a = 0.104 (a = 0.00488; the first term alone, 0.82 f = 0.100, gives 1.36) | 1.303 | ratio in [0.33, 3] | PASS |
| B=1 r=2 (1296 CZ): simulated yield 0.029 vs the model 0.82 f + (1-f) a = 0.019 (a = 0.00488; the first term alone, 0.82 f = 0.014, gives 2.07) | 1.542 | ratio in [0.33, 3] | PASS |
| B=1 r=3 (1944 CZ): simulated yield 0.011 vs the model 0.82 f + (1-f) a = 0.007 (a = 0.00488; the first term alone, 0.82 f = 0.002, gives 5.57) | 1.593 | ratio in [0.33, 3] | PASS |
| readout confusion matrix on 3 patch(es): smallest diagonal element | 0.9768 | >= 0.9 | PASS |
| dry-run counts of scripts/h0_submit.py --dry-run | 126 counts files | > 0 | PASS |
| validation/H0_dryrun.json exists (produced by this step; its own status is reported there) | present, status PASS | exists | PASS |
| validation/S3_smoke.json exists (produced by this step; its own status is reported there) | present, status FAIL | exists | PASS |
| pytest -q tests | 32 passed in 88.13s (0:01:28) | all pass | PASS |

## Scope

Every number above is computed by `scripts/gate_H0P.py` and stored in `validation/H0P.json`.
FakeFez is a calibration **snapshot** of a Heron r2 device, not a reservation on one: the real session
replaces the backend argument of `scripts/h0_submit.py` and re-runs `scripts/gate_H0.py` on the returned counts.
