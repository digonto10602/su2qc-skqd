# Gate H0_canary — 2x2 calibration session on ibm_fez

**Status: FAIL** — `scripts/gate_H0.py --counts data/hardware/H0_ibm_fez_canary/counts --out H0_canary`,
3 counts files (1 coarse-step + 2 readout-calibration circuits),
dry run: **False**.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 390c325, 2026-09-22 11:49:01 MDT.  Runtime 1 s.

Sampler options of the session: `{"default_shots": 267, "dynamical_decoupling": {"enable": true, "sequence_type": "XY4"}, "twirling": {"enable_gates": true, "enable_measure": true, "strategy": "active-accum"}, "error_mitigation": "none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)"}`.

## 1. Decoder validity

| sector | accepted random strings | fraction |
|---|---|---|
| B=0 | 38 / 4096 | 0.928% |

7 distinct accepted bit strings were decoded and re-encoded;
0 did not reproduce themselves.  A mismatch would mean the bit order of the
counts keys is not the codec's.

## 2. Yield versus CZ count

Prediction used for the 30 % criterion: the simulated yield of validation/H0P_ibm_fez.json (gate H0P_ibm_fez, 2026-09-22 11:46:55 MDT), the preregistered prediction of reports/H0_prereg_draft.md.

Yield model (manual Step 4.4, both terms): y = 0.82 f + (1-f) a, with a = the decoder's random-string
acceptance of the target sector (B=0 0.00928, exhaustive).  The measured and predicted
clean-shot fractions are the inverse, f = (y - a) / (0.82 - a) = skqd.skqd.clean_fraction_from_yield(y, a); the column "measured f (0.82 f
model)" is the first term alone, kept for comparison.  **The 30 % criterion is the relative deviation of the
two f values** (r = 1 circuits only: at r = 2, 3 the inversion is ill-conditioned because f approaches a).

| sector | r | circuits | CZ | shots | accepted | measured yield | a (garbage) | model 0.82 f (old) | model 0.82 f + (1−f) a | predicted yield | measured f | predicted f | measured f (0.82 f model) | relative deviation of f | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 1 | 1 | 663 | 267 | 8 | 0.0300 | 0.00928 | 0.1034 | 0.1115 | 0.1872 | 0.0255 | 0.2195 | 0.0365 | 0.884 | {'flag': 176, 'link': 78, 'sector': 5, 'unknown': 0} |

## 3. Ritz consistency

| sector | sector dimension | decoded states | with references | E_R | exact E_0 | \|E_R − E_0\| | recall of the 99.9 % support |
|---|---|---|---|---|---|---|---|
| B=0 | 38 | 7 | 8 | -3.5795694592 | -3.6407665507 | 6.12e-02 | 0.500 |

**B=0**: 7 of 38 sector states decoded,
31 missing (5 (0,0,0,0); (0,2,0,2), 9 (0,0,0,0); (2,0,0,2), 10 (0,0,0,0); (2,0,2,0), 17 (0,0,0,1); (0,2,1,1), 18 (0,0,0,1); (2,0,1,1), 22 (0,0,1,0); (2,1,0,1), 25 (0,0,1,1); (0,1,1,2), 26 (0,0,1,1); (2,1,1,0), 29 (0,1,0,0); (1,1,0,2), 32 (0,1,0,1); (1,1,1,1), 34 (0,1,1,0); (1,0,2,1), 35 (0,1,1,0); (1,2,0,1), 38 (0,1,1,1); (1,0,1,2), 39 (0,1,1,1); (1,2,1,0), 42 (1,0,0,0); (1,0,1,2), 46 (1,0,0,1); (1,0,2,1), 47 (1,0,0,1); (1,2,0,1), 49 (1,0,1,0); (1,1,1,1), 51 (1,0,1,1); (1,1,0,2), 52 (1,0,1,1); (1,1,2,0), 55 (1,1,0,0); (0,1,1,2), 56 (1,1,0,0); (2,1,1,0), 59 (1,1,0,1); (0,1,2,1), 60 (1,1,0,1); (2,1,0,1), 63 (1,1,1,0); (0,2,1,1), 64 (1,1,1,0); (2,0,1,1), 69 (1,1,1,1); (0,0,2,2), 71 (1,1,1,1); (0,2,0,2), 75 (1,1,1,1); (2,0,0,2), 76 (1,1,1,1); (2,0,2,0), 78 (1,1,1,1); (2,2,0,0)).  Shot plan: N4 = 6900, 38505 r = 1 shots, min lambda_s at 0.7 f = 6.3266 (lambda* = 6.2958), P(all 38 states seen from clean shots) = 0.99771.
The eight least observed states:

| basis index | label (j2; n) | observed accepted count | predicted clean count (all circuits, at f) | predicted clean count (r = 1, at margin) |
|---|---|---|---|---|
| 5 | (0,0,0,0); (0,2,0,2) | 0 | 191.89 | 133.68 |
| 9 | (0,0,0,0); (2,0,0,2) | 0 | 49.42 | 34.51 |
| 10 | (0,0,0,0); (2,0,2,0) | 0 | 238.55 | 166.35 |
| 17 | (0,0,0,1); (0,2,1,1) | 0 | 506.16 | 353.63 |
| 18 | (0,0,0,1); (2,0,1,1) | 0 | 163.17 | 114.07 |
| 22 | (0,0,1,0); (2,1,0,1) | 0 | 141.96 | 99.23 |
| 25 | (0,0,1,1); (0,1,1,2) | 0 | 221.62 | 154.98 |
| 26 | (0,0,1,1); (2,1,1,0) | 0 | 50.41 | 35.24 |


## 4. Readout confusion

| patch | logical qubit | physical qubit | P(0\|0) | P(1\|1) | measured error | snapshot error | ratio | calibration error | ratio vs calibration |
|---|---|---|---|---|---|---|---|---|---|
| patch1 | 0 | 117 | 0.9775 | 0.9888 | 0.0169 | 0.0085 | 1.97 | 0.0134 | 1.26 |
| patch1 | 1 | 122 | 0.9925 | 0.9888 | 0.0094 | 0.0063 | 1.48 | 0.0144 | 0.65 |
| patch1 | 2 | 123 | 0.9850 | 0.9738 | 0.0206 | 0.0063 | 3.25 | 0.0059 | 3.52 |
| patch1 | 3 | 124 | 1.0000 | 1.0000 | 0.0000 | 0.0046 | - | 0.0063 | - |
| patch1 | 4 | 125 | 0.9775 | 0.9888 | 0.0169 | 0.0125 | 1.35 | 0.0198 | 0.85 |
| patch1 | 5 | 136 | 0.9963 | 0.9888 | 0.0075 | 0.0046 | 1.61 | 0.0085 | 0.88 |
| patch1 | 6 | 141 | 0.9925 | 0.9925 | 0.0075 | 0.0049 | 1.53 | 0.0139 | 0.54 |
| patch1 | 7 | 142 | 0.9925 | 0.9963 | 0.0056 | 0.0061 | 0.92 | 0.0066 | 0.85 |
| patch1 | 8 | 143 | 0.9925 | 0.9925 | 0.0075 | 0.0044 | 1.70 | 0.0071 | 1.06 |
| patch1 | 9 | 144 | 0.9963 | 0.9963 | 0.0037 | 0.0107 | 0.35 | 0.0068 | 0.55 |
| patch1 | 10 | 145 | 0.9888 | 0.9963 | 0.0075 | 0.0139 | 0.54 | 0.0142 | 0.53 |
| patch1 | 11 | 146 | 0.9925 | 0.9925 | 0.0075 | 0.0059 | 1.28 | 0.0049 | 1.53 |

The drift criterion (factor 3) is evaluated against `data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json` (ibm_fez, calibration 2026-09-22T08:00:30-06:00) -- the calibration the prediction was made from (prompts/15 D7).  The circuits were transpiled onto FakeFez and ran on ibm_fez; the comparison with that frozen snapshot is reported without a criterion.


## Criteria

| check | value | criterion | result |
|---|---|---|---|
| decoder validity: accepted strings that re-encode to themselves | 7 of 7 | all | PASS |
| B=0: acceptance of random bit strings (exhaustive over 4096 strings) | 0.928% | < 1% | PASS |
| B=0 r=1 (663 CZ): measured f = 0.0255 vs the predicted f = 0.2195 (both from y = 0.82 f + (1-f) a inverted at a = 0.00928) | 0.8838 | relative deviation <= 0.30 | FAIL |
| B=0: decoded support reproduces the exact E0 = -3.6408 (support 7 decoded + references = 8 of the 38-dimensional sector: NOT saturated) | 0.0611971 | |E_R - E_0| < 1e-06 | FAIL |
| readout confusion on 1 patch(es): smallest diagonal element | 0.9738 | >= 0.9 | PASS |
| readout error per qubit against the calibration the prediction was made from (ibm_fez, 2026-09-22T08:00:30-06:00; worst ratio, the calibration-drift item of prompts/15 D7) | 3.516 | within a factor 3 | FAIL |

Every number above is computed by `scripts/gate_H0.py` from the raw counts in `data/hardware/H0_ibm_fez_canary/counts` and stored in
`validation/H0_canary.json`.  The counts files are never modified.
