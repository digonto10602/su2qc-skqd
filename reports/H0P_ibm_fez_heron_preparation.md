# Gate H0P_ibm_fez — H0 preparation on the ibm_fez calibration snapshot

**Status: PASS** — `scripts/gate_H0P.py` on the frozen circuit set of
`scripts/h0_build_circuits.py` (data/hardware/H0_prep, created 2026-09-16 09:57:38 MDT).
Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 1e6d7d3, 2026-09-22 11:46:55 MDT.  Runtime 319 s.  Nothing in this gate touches a QPU.

**The calibration of the session day** (prompts/15 D1: the circuits stay frozen, the prediction is recomputed).  `data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json` -- ibm_fez, `last_update_date` 2026-09-22T08:00:30-06:00, fingerprint `7fd6d65eaa1a1b4f` (prompts/17 D9: the sha256 of the 30 qubit and 54 edge blocks this prediction reads), dt 4e-09, default rep delay 0.00025 s, max_circuits None, operational, 4 pending jobs.  It covers the 30 qubits and 54 two-qubit edges the frozen set uses; 0 of those target entries carry no error value (a non-empty list is a hard stop, not a defaulted value).  The clean-shot fraction f was recomputed circuit by circuit on that target with `gate_S2D.analyse_on_backend`: mean 0.0695 against 0.0477 frozen into the manifests.

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

Sampling: `AerSimulator.from_backend(ibm_fez, seed_simulator=11)`, [267, 6900, 16800] shots per r = 1 circuit, 130 shots per r = 2 circuit, 92 shots per r = 3 circuit
(pinned with --shots-plan allocation, 79923 shots in total, 0 s; the pilot measured
,
i.e. 0.0 s per shot over the whole set, and the budget was 28 min).

| sector | r | circuits | CZ | f (calibration) | f (frozen snapshot) | a (garbage) | model 0.82 f (old) | model 0.82 f + (1−f) a | shots | simulated yield | simulated / 0.82 f | simulated / full model | distinct states | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 1 | 20 | 663 | 0.2103 | 0.1261 | 0.00928 | 0.1725 | 0.1798 | 38505 | 0.1872 | 1.09 | 1.04 | 38 | {'flag': 16857, 'link': 12147, 'sector': 2291, 'unknown': 0} |
| B=0 | 2 | 20 | 1308 | 0.0055 | 0.0154 | 0.00928 | 0.0045 | 0.0137 | 2600 | 0.0138 | 3.08 | 1.01 | 24 | {'flag': 1713, 'link': 787, 'sector': 64, 'unknown': 0} |
| B=0 | 3 | 20 | 1910 | 0.0007 | 0.0026 | 0.00928 | 0.0005 | 0.0098 | 1840 | 0.0120 | 22.16 | 1.22 | 19 | {'flag': 1203, 'link': 587, 'sector': 28, 'unknown': 0} |
| B=1 | 1 | 8 | 663 | 0.1822 | 0.1214 | 0.00488 | 0.1494 | 0.1534 | 35202 | 0.1750 | 1.17 | 1.14 | 20 | {'flag': 17628, 'link': 8570, 'sector': 2842, 'unknown': 0} |
| B=1 | 2 | 8 | 1296 | 0.0059 | 0.0170 | 0.00488 | 0.0049 | 0.0097 | 1040 | 0.0106 | 2.17 | 1.09 | 9 | {'flag': 719, 'link': 286, 'sector': 24, 'unknown': 0} |
| B=1 | 3 | 8 | 1944 | 0.0006 | 0.0024 | 0.00488 | 0.0005 | 0.0053 | 736 | 0.0054 | 12.02 | 1.02 | 3 | {'flag': 504, 'link': 210, 'sector': 18, 'unknown': 0} |

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
0 missing.  Shot plan: N4 = 6900, 38505 r = 1 shots, min lambda_s at 0.7 f = 6.3266 (lambda* = 6.2958), P(all 38 states seen from clean shots) = 0.99771.
The eight least observed states:

| basis index | label (j2; n) | observed accepted count | predicted clean count (all circuits, at f) | predicted clean count (r = 1, at margin) |
|---|---|---|---|---|
| 71 | (1,1,1,1); (0,2,0,2) | 24 | 15.26 | 10.64 |
| 69 | (1,1,1,1); (0,0,2,2) | 32 | 14.68 | 10.23 |
| 59 | (1,1,0,1); (0,1,2,1) | 34 | 9.06 | 6.33 |
| 55 | (1,1,0,0); (0,1,1,2) | 38 | 11.07 | 7.73 |
| 75 | (1,1,1,1); (2,0,0,2) | 39 | 20.98 | 14.69 |
| 35 | (0,1,1,0); (1,2,0,1) | 43 | 19.29 | 13.47 |
| 76 | (1,1,1,1); (2,0,2,0) | 46 | 26.94 | 18.82 |
| 78 | (1,1,1,1); (2,2,0,0) | 54 | 24.20 | 16.90 |

**B=1**: 20 of 20 sector states decoded,
0 missing.  Shot plan: N4 = 16800, 35202 r = 1 shots, min lambda_s at 0.7 f = 6.3294 (lambda* = 6.2958), P(all 20 states seen from clean shots) = 0.99822.
The eight least observed states:

| basis index | label (j2; n) | observed accepted count | predicted clean count (all circuits, at f) | predicted clean count (r = 1, at margin) |
|---|---|---|---|---|
| 53 | (1,0,1,1); (1,1,2,2) | 32 | 9.10 | 6.33 |
| 73 | (1,1,1,1); (0,2,2,2) | 58 | 47.46 | 33.15 |
| 77 | (1,1,1,1); (2,0,2,2) | 94 | 51.17 | 35.80 |
| 40 | (0,1,1,1); (1,2,1,2) | 96 | 88.76 | 62.11 |
| 79 | (1,1,1,1); (2,2,0,2) | 97 | 73.11 | 51.17 |
| 80 | (1,1,1,1); (2,2,2,0) | 113 | 93.22 | 65.18 |
| 36 | (0,1,1,0); (1,2,2,1) | 131 | 131.46 | 91.95 |
| 65 | (1,1,1,0); (2,2,1,1) | 164 | 137.13 | 95.97 |


## 5. Readout confusion (simulated calibration circuits, 4000 shots each)

| patch | logical qubit | physical qubit | P(0\|0) | P(1\|1) | min diagonal |
|---|---|---|---|---|---|
| patch0 | 0 | 77 | 0.9893 | 0.9879 | 0.9879 |
| patch0 | 1 | 78 | 0.9869 | 0.9870 | 0.9869 |
| patch0 | 2 | 84 | 0.9960 | 0.9951 | 0.9951 |
| patch0 | 3 | 85 | 0.9895 | 0.9894 | 0.9894 |
| patch0 | 4 | 86 | 0.9931 | 0.9935 | 0.9931 |
| patch0 | 5 | 87 | 0.9540 | 0.9547 | 0.9540 |
| patch0 | 6 | 88 | 0.9967 | 0.9965 | 0.9965 |
| patch0 | 7 | 89 | 0.9872 | 0.9860 | 0.9860 |
| patch0 | 8 | 90 | 0.9957 | 0.9945 | 0.9945 |
| patch0 | 9 | 97 | 0.9931 | 0.9922 | 0.9922 |
| patch0 | 10 | 107 | 0.9915 | 0.9910 | 0.9910 |
| patch0 | 11 | 108 | 0.9917 | 0.9909 | 0.9909 |
| patch1 | 0 | 117 | 0.9862 | 0.9871 | 0.9862 |
| patch1 | 1 | 122 | 0.9856 | 0.9850 | 0.9850 |
| patch1 | 2 | 123 | 0.9947 | 0.9931 | 0.9931 |
| patch1 | 3 | 124 | 0.9946 | 0.9942 | 0.9942 |
| patch1 | 4 | 125 | 0.9797 | 0.9795 | 0.9795 |
| patch1 | 5 | 136 | 0.9921 | 0.9890 | 0.9890 |
| patch1 | 6 | 141 | 0.9857 | 0.9858 | 0.9857 |
| patch1 | 7 | 142 | 0.9930 | 0.9931 | 0.9930 |
| patch1 | 8 | 143 | 0.9927 | 0.9920 | 0.9920 |
| patch1 | 9 | 144 | 0.9936 | 0.9925 | 0.9925 |
| patch1 | 10 | 145 | 0.9850 | 0.9866 | 0.9850 |
| patch1 | 11 | 146 | 0.9944 | 0.9938 | 0.9938 |
| patch2 | 0 | 121 | 0.9898 | 0.9904 | 0.9898 |
| patch2 | 1 | 122 | 0.9858 | 0.9865 | 0.9858 |
| patch2 | 2 | 123 | 0.9937 | 0.9934 | 0.9934 |
| patch2 | 3 | 124 | 0.9931 | 0.9919 | 0.9919 |
| patch2 | 4 | 136 | 0.9911 | 0.9908 | 0.9908 |
| patch2 | 5 | 140 | 0.9791 | 0.9775 | 0.9775 |
| patch2 | 6 | 141 | 0.9859 | 0.9868 | 0.9859 |
| patch2 | 7 | 142 | 0.9929 | 0.9926 | 0.9926 |
| patch2 | 8 | 143 | 0.9922 | 0.9931 | 0.9922 |
| patch2 | 9 | 144 | 0.9921 | 0.9919 | 0.9919 |
| patch2 | 10 | 145 | 0.9864 | 0.9841 | 0.9841 |
| patch2 | 11 | 146 | 0.9952 | 0.9951 | 0.9951 |

`skqd.hardware.confusion_matrix` builds the tensored (independent-qubit) model from all
42 preparations; `skqd.hardware.apply_inverse` unfolds a counts dictionary with its exact tensor
inverse.  Smallest diagonal element over all patches: 0.9540.

## 6. Shot plan (manual eq. 5, `skqd.skqd.shot_rule`, p = 1e-03, k = 3, confidence 0.95)

| sector | r | circuits | simulated yield | clean yield 0.82 f | N/circuit (simulated) | N/sector (simulated) | N/circuit (clean 0.82 f) | N/sector (clean 0.82 f) |
|---|---|---|---|---|---|---|---|---|
| B=0 | 1 | 20 | 0.1872 | 0.1725 | 33623 | 6.725e+05 | 36502 | 7.300e+05 |
| B=0 | 2 | 20 | 0.0138 | 0.0045 | 454697 | 9.094e+06 | 1401590 | 2.803e+07 |
| B=0 | 3 | 20 | 0.0120 | 0.0005 | 526558 | 1.053e+07 | 11666951 | 2.333e+08 |
| B=1 | 1 | 8 | 0.1750 | 0.1494 | 35967 | 2.877e+05 | 42137 | 3.371e+05 |
| B=1 | 2 | 8 | 0.0106 | 0.0049 | 595239 | 4.762e+06 | 1293665 | 1.035e+07 |
| B=1 | 3 | 8 | 0.0054 | 0.0005 | 1158427 | 9.267e+06 | 13921727 | 1.114e+08 |

The budget preregistered for the session is the one computed from the **clean** yield 0.82 f (last two
columns): a shot that is accepted only because its garbage string happens to be a codeword adds no support,
so the garbage term of the yield model must not enter the shot rule.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| every frozen circuit leak-free after transpilation onto FakeFez (84 circuits, noiseless statevector permuted back with the final layout) | 1.488e-14 | < 1e-09 | PASS |
| B=0: decoded support reproduces the exact E0 = -3.6408 | 0 | |E_R - E_0| < 1e-06 | PASS |
| B=1: decoded support reproduces the exact E0 = -1.8616 | 0 | |E_R - E_0| < 1e-06 | PASS |
| B=0 shot plan: every one of the 38 sector states has expected clean count >= lambda* in the r = 1 circuits at 0.7 x f_cal (N4 = 6900, 38505 r = 1 shots; min lambda_s) | 6.3266 | >= lambda* = 6.2958 | PASS |
| B=1 shot plan: every one of the 20 sector states has expected clean count >= lambda* in the r = 1 circuits at 0.7 x f_cal (N4 = 16800, 35202 r = 1 shots; min lambda_s) | 6.3294 | >= lambda* = 6.2958 | PASS |
| B=0: acceptance of random bit strings (exhaustive over all 4096 strings) | 0.928% | < 1% | PASS |
| B=1: acceptance of random bit strings (exhaustive over all 4096 strings) | 0.488% | < 1% | PASS |
| B=0 r=1 (663 CZ): simulated yield 0.187 vs the model 0.82 f + (1-f) a = 0.180 (a = 0.00928; the first term alone, 0.82 f = 0.172, gives 1.09) | 1.041 | ratio in [0.33, 3] | PASS |
| B=0 r=2 (1308 CZ): simulated yield 0.014 vs the model 0.82 f + (1-f) a = 0.014 (a = 0.00928; the first term alone, 0.82 f = 0.004, gives 3.08) | 1.009 | ratio in [0.33, 3] | PASS |
| B=0 r=3 (1910 CZ): simulated yield 0.012 vs the model 0.82 f + (1-f) a = 0.010 (a = 0.00928; the first term alone, 0.82 f = 0.001, gives 22.16) | 1.219 | ratio in [0.33, 3] | PASS |
| B=1 r=1 (663 CZ): simulated yield 0.175 vs the model 0.82 f + (1-f) a = 0.153 (a = 0.00488; the first term alone, 0.82 f = 0.149, gives 1.17) | 1.141 | ratio in [0.33, 3] | PASS |
| B=1 r=2 (1296 CZ): simulated yield 0.011 vs the model 0.82 f + (1-f) a = 0.010 (a = 0.00488; the first term alone, 0.82 f = 0.005, gives 2.17) | 1.088 | ratio in [0.33, 3] | PASS |
| B=1 r=3 (1944 CZ): simulated yield 0.005 vs the model 0.82 f + (1-f) a = 0.005 (a = 0.00488; the first term alone, 0.82 f = 0.000, gives 12.02) | 1.019 | ratio in [0.33, 3] | PASS |
| readout confusion matrix on 3 patch(es): smallest diagonal element | 0.954 | >= 0.9 | PASS |
| dry-run counts of scripts/h0_submit.py --dry-run | 126 counts files | > 0 | PASS |
| validation/H0_dryrun.json exists (produced by this step; its own status is reported there) | present, status PASS | exists | PASS |
| validation/S3_smoke.json exists (produced by this step; its own status is reported there) | present, status FAIL | exists | PASS |
| pytest -q tests | [33m[32m96 passed[0m, [33m[1m7 warnings[0m[33m in 294.07s (0:04:54)[0m[0m | all pass | PASS |

## Scope

Every number above is computed by `scripts/gate_H0P.py` and stored in `validation/H0P_ibm_fez.json`.
ibm_fez is a calibration **snapshot** of a Heron r2 device, not a reservation on one: the real session
replaces the backend argument of `scripts/h0_submit.py` and re-runs `scripts/gate_H0.py` on the returned counts.
