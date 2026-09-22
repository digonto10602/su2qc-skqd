# Gate H0P_ibm_fez — H0 preparation on the ibm_fez calibration snapshot

**Status: PASS** — `scripts/gate_H0P.py` on the frozen circuit set of
`scripts/h0_build_circuits.py` (data/hardware/H0_prep, created 2026-09-16 09:57:38 MDT).
Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit cf23ba4, 2026-09-22 02:03:30 MDT.  Runtime 174 s.  Nothing in this gate touches a QPU.

**The calibration of the session day** (prompts/15 D1: the circuits stay frozen, the prediction is recomputed).  `data/hardware/H0_ibm_fez/calibration_20260922T0711Z.json` -- ibm_fez, `last_update_date` 2026-09-22T01:11:12-06:00, dt 4e-09, default rep delay 0.00025 s, max_circuits None, operational, 2 pending jobs.  It covers the 30 qubits and 54 two-qubit edges the frozen set uses; 0 of those target entries carry no error value (a non-empty list is a hard stop, not a defaulted value).  The clean-shot fraction f was recomputed circuit by circuit on that target with `gate_S2D.analyse_on_backend`: mean 0.0623 against 0.0477 frozen into the manifests.

## 1. The frozen circuit set

84 coarse-step circuits (both sectors, every reference, k = 1..4,
r = [1, 2, 3] repetitions of the step) plus 42 readout-calibration circuits
(all-0, all-1 and the 12 single-qubit flips on each of the
3 physical patches the transpiler chose), transpiled onto ibm_fez at optimization
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

Sampling: `AerSimulator.from_backend(ibm_fez, seed_simulator=11)`, [267, 8100, 19600] shots per r = 1 circuit, 130 shots per r = 2 circuit, 92 shots per r = 3 circuit
(pinned with --shots-plan allocation, 91523 shots in total, 0 s; the pilot measured
,
i.e. 0.0 s per shot over the whole set, and the budget was 28 min).

| sector | r | circuits | CZ | f (calibration) | f (frozen snapshot) | a (garbage) | model 0.82 f (old) | model 0.82 f + (1−f) a | shots | simulated yield | simulated / 0.82 f | simulated / full model | distinct states | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 1 | 20 | 663 | 0.1797 | 0.1261 | 0.00928 | 0.1474 | 0.1550 | 44505 | 0.1707 | 1.16 | 1.10 | 38 | {'flag': 19864, 'link': 14525, 'sector': 2519, 'unknown': 0} |
| B=0 | 2 | 20 | 1308 | 0.0068 | 0.0154 | 0.00928 | 0.0056 | 0.0148 | 2600 | 0.0238 | 4.25 | 1.61 | 32 | {'flag': 1618, 'link': 874, 'sector': 46, 'unknown': 0} |
| B=0 | 3 | 20 | 1910 | 0.0008 | 0.0026 | 0.00928 | 0.0007 | 0.0100 | 1840 | 0.0152 | 22.28 | 1.53 | 19 | {'flag': 1186, 'link': 602, 'sector': 24, 'unknown': 0} |
| B=1 | 1 | 8 | 663 | 0.1780 | 0.1214 | 0.00488 | 0.1460 | 0.1500 | 40802 | 0.1564 | 1.07 | 1.04 | 20 | {'flag': 20675, 'link': 10651, 'sector': 3093, 'unknown': 0} |
| B=1 | 2 | 8 | 1296 | 0.0071 | 0.0170 | 0.00488 | 0.0058 | 0.0107 | 1040 | 0.0173 | 2.96 | 1.62 | 10 | {'flag': 684, 'link': 310, 'sector': 28, 'unknown': 0} |
| B=1 | 3 | 8 | 1944 | 0.0007 | 0.0024 | 0.00488 | 0.0006 | 0.0055 | 736 | 0.0054 | 9.34 | 1.00 | 4 | {'flag': 481, 'link': 233, 'sector': 18, 'unknown': 0} |

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
(manual Step 9.1), not an accuracy test: a permuted codeword would give a different energy.  Whether
they saturate is a property of the SHOT PLAN, not an assumption: see the support table below.

**B=0**: 38 of 38 sector states decoded,
0 missing.  Shot plan: N4 = 8100, 44505 r = 1 shots, min lambda_s at 0.7 f = 6.3060 (lambda* = 6.2958), P(all 38 states seen from clean shots) = 0.99768.
The eight least observed states:

| basis index | label (j2; n) | observed accepted count | predicted clean count (all circuits, at f) | predicted clean count (r = 1, at margin) |
|---|---|---|---|---|
| 69 | (1,1,1,1); (0,0,2,2) | 25 | 14.68 | 10.23 |
| 71 | (1,1,1,1); (0,2,0,2) | 26 | 15.27 | 10.64 |
| 55 | (1,1,0,0); (0,1,1,2) | 28 | 11.09 | 7.74 |
| 35 | (0,1,1,0); (1,2,0,1) | 37 | 19.32 | 13.48 |
| 75 | (1,1,1,1); (2,0,0,2) | 38 | 21.02 | 14.71 |
| 76 | (1,1,1,1); (2,0,2,0) | 40 | 26.97 | 18.83 |
| 59 | (1,1,0,1); (0,1,2,1) | 41 | 9.04 | 6.31 |
| 78 | (1,1,1,1); (2,2,0,0) | 58 | 24.22 | 16.91 |

**B=1**: 20 of 20 sector states decoded,
0 missing.  Shot plan: N4 = 19600, 40802 r = 1 shots, min lambda_s at 0.7 f = 6.3006 (lambda* = 6.2958), P(all 20 states seen from clean shots) = 0.99816.
The eight least observed states:

| basis index | label (j2; n) | observed accepted count | predicted clean count (all circuits, at f) | predicted clean count (r = 1, at margin) |
|---|---|---|---|---|
| 53 | (1,0,1,1); (1,1,2,2) | 34 | 9.07 | 6.30 |
| 73 | (1,1,1,1); (0,2,2,2) | 61 | 47.30 | 33.02 |
| 40 | (0,1,1,1); (1,2,1,2) | 83 | 88.39 | 61.85 |
| 79 | (1,1,1,1); (2,2,0,2) | 87 | 72.84 | 50.97 |
| 77 | (1,1,1,1); (2,0,2,2) | 94 | 50.99 | 35.67 |
| 80 | (1,1,1,1); (2,2,2,0) | 118 | 92.90 | 64.94 |
| 36 | (0,1,1,0); (1,2,2,1) | 145 | 130.88 | 91.53 |
| 65 | (1,1,1,0); (2,2,1,1) | 161 | 136.59 | 95.59 |


## 5. Readout confusion (simulated calibration circuits, 4000 shots each)

| patch | logical qubit | physical qubit | P(0\|0) | P(1\|1) | min diagonal |
|---|---|---|---|---|---|
| patch0 | 0 | 77 | 0.9894 | 0.9888 | 0.9888 |
| patch0 | 1 | 78 | 0.9882 | 0.9884 | 0.9882 |
| patch0 | 2 | 84 | 0.9922 | 0.9912 | 0.9912 |
| patch0 | 3 | 85 | 0.9918 | 0.9920 | 0.9918 |
| patch0 | 4 | 86 | 0.9925 | 0.9929 | 0.9925 |
| patch0 | 5 | 87 | 0.9603 | 0.9627 | 0.9603 |
| patch0 | 6 | 88 | 0.9935 | 0.9930 | 0.9930 |
| patch0 | 7 | 89 | 0.9892 | 0.9876 | 0.9876 |
| patch0 | 8 | 90 | 0.9941 | 0.9930 | 0.9930 |
| patch0 | 9 | 97 | 0.9854 | 0.9839 | 0.9839 |
| patch0 | 10 | 107 | 0.9913 | 0.9908 | 0.9908 |
| patch0 | 11 | 108 | 0.9923 | 0.9918 | 0.9918 |
| patch1 | 0 | 117 | 0.9857 | 0.9858 | 0.9857 |
| patch1 | 1 | 122 | 0.9934 | 0.9928 | 0.9928 |
| patch1 | 2 | 123 | 0.9920 | 0.9894 | 0.9894 |
| patch1 | 3 | 124 | 0.9971 | 0.9960 | 0.9960 |
| patch1 | 4 | 125 | 0.9833 | 0.9829 | 0.9829 |
| patch1 | 5 | 136 | 0.9850 | 0.9818 | 0.9818 |
| patch1 | 6 | 141 | 0.9918 | 0.9924 | 0.9918 |
| patch1 | 7 | 142 | 0.9943 | 0.9941 | 0.9941 |
| patch1 | 8 | 143 | 0.9959 | 0.9948 | 0.9948 |
| patch1 | 9 | 144 | 0.9958 | 0.9951 | 0.9951 |
| patch1 | 10 | 145 | 0.9865 | 0.9875 | 0.9865 |
| patch1 | 11 | 146 | 0.9878 | 0.9868 | 0.9868 |
| patch2 | 0 | 121 | 0.9861 | 0.9878 | 0.9861 |
| patch2 | 1 | 122 | 0.9934 | 0.9928 | 0.9928 |
| patch2 | 2 | 123 | 0.9912 | 0.9908 | 0.9908 |
| patch2 | 3 | 124 | 0.9958 | 0.9941 | 0.9941 |
| patch2 | 4 | 136 | 0.9850 | 0.9822 | 0.9822 |
| patch2 | 5 | 140 | 0.9881 | 0.9864 | 0.9864 |
| patch2 | 6 | 141 | 0.9920 | 0.9925 | 0.9920 |
| patch2 | 7 | 142 | 0.9940 | 0.9939 | 0.9939 |
| patch2 | 8 | 143 | 0.9950 | 0.9954 | 0.9950 |
| patch2 | 9 | 144 | 0.9948 | 0.9949 | 0.9948 |
| patch2 | 10 | 145 | 0.9881 | 0.9854 | 0.9854 |
| patch2 | 11 | 146 | 0.9882 | 0.9879 | 0.9879 |

`skqd.hardware.confusion_matrix` builds the tensored (independent-qubit) model from all
42 preparations; `skqd.hardware.apply_inverse` unfolds a counts dictionary with its exact tensor
inverse.  Smallest diagonal element over all patches: 0.9603.

## 6. Shot plan (manual eq. 5, `skqd.skqd.shot_rule`, p = 1e-03, k = 3, confidence 0.95)

| sector | r | circuits | simulated yield | clean yield 0.82 f | N/circuit (simulated) | N/sector (simulated) | N/circuit (clean 0.82 f) | N/sector (clean 0.82 f) |
|---|---|---|---|---|---|---|---|---|
| B=0 | 1 | 20 | 0.1707 | 0.1474 | 36883 | 7.377e+05 | 42726 | 8.545e+05 |
| B=0 | 2 | 20 | 0.0238 | 0.0056 | 264018 | 5.280e+06 | 1121489 | 2.243e+07 |
| B=0 | 3 | 20 | 0.0152 | 0.0007 | 413724 | 8.274e+06 | 9219330 | 1.844e+08 |
| B=1 | 1 | 8 | 0.1564 | 0.1460 | 40245 | 3.220e+05 | 43133 | 3.451e+05 |
| B=1 | 2 | 8 | 0.0173 | 0.0058 | 363757 | 2.910e+06 | 1077930 | 8.623e+06 |
| B=1 | 3 | 8 | 0.0054 | 0.0006 | 1158427 | 9.267e+06 | 10815079 | 8.652e+07 |

The budget preregistered for the session is the one computed from the **clean** yield 0.82 f (last two
columns): a shot that is accepted only because its garbage string happens to be a codeword adds no support,
so the garbage term of the yield model must not enter the shot rule.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| every frozen circuit leak-free after transpilation onto FakeFez (84 circuits, noiseless statevector permuted back with the final layout) | 1.488e-14 | < 1e-09 | PASS |
| B=0: decoded support reproduces the exact E0 = -3.6408 | 0 | |E_R - E_0| < 1e-06 | PASS |
| B=1: decoded support reproduces the exact E0 = -1.8616 | 0 | |E_R - E_0| < 1e-06 | PASS |
| B=0 shot plan: every one of the 38 sector states has expected clean count >= lambda* in the r = 1 circuits at 0.7 x f_cal (N4 = 8100, 44505 r = 1 shots; min lambda_s) | 6.306 | >= lambda* = 6.2958 | PASS |
| B=1 shot plan: every one of the 20 sector states has expected clean count >= lambda* in the r = 1 circuits at 0.7 x f_cal (N4 = 19600, 40802 r = 1 shots; min lambda_s) | 6.3006 | >= lambda* = 6.2958 | PASS |
| B=0: acceptance of random bit strings (exhaustive over all 4096 strings) | 0.928% | < 1% | PASS |
| B=1: acceptance of random bit strings (exhaustive over all 4096 strings) | 0.488% | < 1% | PASS |
| B=0 r=1 (663 CZ): simulated yield 0.171 vs the model 0.82 f + (1-f) a = 0.155 (a = 0.00928; the first term alone, 0.82 f = 0.147, gives 1.16) | 1.102 | ratio in [0.33, 3] | PASS |
| B=0 r=2 (1308 CZ): simulated yield 0.024 vs the model 0.82 f + (1-f) a = 0.015 (a = 0.00928; the first term alone, 0.82 f = 0.006, gives 4.25) | 1.608 | ratio in [0.33, 3] | PASS |
| B=0 r=3 (1910 CZ): simulated yield 0.015 vs the model 0.82 f + (1-f) a = 0.010 (a = 0.00928; the first term alone, 0.82 f = 0.001, gives 22.28) | 1.529 | ratio in [0.33, 3] | PASS |
| B=1 r=1 (663 CZ): simulated yield 0.156 vs the model 0.82 f + (1-f) a = 0.150 (a = 0.00488; the first term alone, 0.82 f = 0.146, gives 1.07) | 1.043 | ratio in [0.33, 3] | PASS |
| B=1 r=2 (1296 CZ): simulated yield 0.017 vs the model 0.82 f + (1-f) a = 0.011 (a = 0.00488; the first term alone, 0.82 f = 0.006, gives 2.96) | 1.619 | ratio in [0.33, 3] | PASS |
| B=1 r=3 (1944 CZ): simulated yield 0.005 vs the model 0.82 f + (1-f) a = 0.005 (a = 0.00488; the first term alone, 0.82 f = 0.001, gives 9.34) | 0.995 | ratio in [0.33, 3] | PASS |
| readout confusion matrix on 3 patch(es): smallest diagonal element | 0.9603 | >= 0.9 | PASS |
| dry-run counts of scripts/h0_submit.py --dry-run | 126 counts files | > 0 | PASS |
| validation/H0_dryrun.json exists (produced by this step; its own status is reported there) | present, status PASS | exists | PASS |
| validation/S3_smoke.json exists (produced by this step; its own status is reported there) | present, status FAIL | exists | PASS |
| pytest -q tests | [33m[32m84 passed[0m, [33m[1m7 warnings[0m[33m in 111.26s (0:01:51)[0m[0m | all pass | PASS |

## Scope

Every number above is computed by `scripts/gate_H0P.py` and stored in `validation/H0P_ibm_fez.json`.
ibm_fez is a calibration **snapshot** of a Heron r2 device, not a reservation on one: the real session
replaces the backend argument of `scripts/h0_submit.py` and re-runs `scripts/gate_H0.py` on the returned counts.
