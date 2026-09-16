# Gate H0_dryrun — 2x2 calibration session on AerSimulator.from_backend(FakeFez) [local testing mode]

**Status: PASS** — `scripts/gate_H0.py --counts data/hardware/H0_dryrun/counts --out H0_dryrun`,
126 counts files (84 coarse-step + 42 readout-calibration circuits),
dry run: **True**.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 1223e92, 2026-09-16 12:03:30 MDT.  Runtime 1 s.

Sampler options of the session: `{"default_shots": 40, "dynamical_decoupling": {"enable": true, "sequence_type": "XY4"}, "twirling": {"enable_gates": true, "enable_measure": true, "strategy": "active-accum"}, "error_mitigation": "none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)"}`.

## 1. Decoder validity

| sector | accepted random strings | fraction |
|---|---|---|
| B=0 | 38 / 4096 | 0.928% |
| B=1 | 20 / 4096 | 0.488% |

58 distinct accepted bit strings were decoded and re-encoded;
0 did not reproduce themselves.  A mismatch would mean the bit order of the
counts keys is not the codec's.

## 2. Yield versus CZ count

Prediction used for the 30 % criterion: the simulated yield of validation/H0P.json (gate H0P, 2026-09-16 11:40:23 MDT), the preregistered prediction of reports/H0_prereg_draft.md.

| sector | r | circuits | CZ | shots | accepted | measured yield | model 0.82 f | predicted yield | measured f | relative deviation | rejections |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 1 | 20 | 663 | 5340 | 790 | 0.1479 | 0.1034 | 0.1493 | 0.1804 | 0.009 | {'flag': 2460, 'link': 1784, 'sector': 306, 'unknown': 0} |
| B=0 | 2 | 20 | 1308 | 2600 | 100 | 0.0385 | 0.0127 | 0.0381 | 0.0469 | 0.010 | {'flag': 1537, 'link': 901, 'sector': 62, 'unknown': 0} |
| B=0 | 3 | 20 | 1910 | 1840 | 28 | 0.0152 | 0.0021 | 0.0174 | 0.0186 | 0.125 | {'flag': 1164, 'link': 614, 'sector': 34, 'unknown': 0} |
| B=1 | 1 | 8 | 663 | 2136 | 284 | 0.1330 | 0.0995 | 0.1353 | 0.1621 | 0.017 | {'flag': 1163, 'link': 506, 'sector': 183, 'unknown': 0} |
| B=1 | 2 | 8 | 1296 | 1040 | 28 | 0.0269 | 0.0139 | 0.0288 | 0.0328 | 0.067 | {'flag': 674, 'link': 293, 'sector': 45, 'unknown': 0} |
| B=1 | 3 | 8 | 1944 | 736 | 7 | 0.0095 | 0.0020 | 0.0109 | 0.0116 | 0.125 | {'flag': 494, 'link': 211, 'sector': 24, 'unknown': 0} |

## 3. Ritz consistency

| sector | sector dimension | decoded states | with references | E_R | exact E_0 | \|E_R − E_0\| | recall of the 99.9 % support |
|---|---|---|---|---|---|---|---|
| B=0 | 38 | 38 | 38 | -3.6407665507 | -3.6407665507 | 0.00e+00 | 1.000 |
| B=1 | 20 | 20 | 20 | -1.8615880345 | -1.8615880345 | 0.00e+00 | 1.000 |

## 4. Readout confusion

| patch | logical qubit | physical qubit | P(0\|0) | P(1\|1) | measured error | snapshot error | ratio |
|---|---|---|---|---|---|---|---|
| patch0 | 0 | 77 | 0.9920 | 0.9912 | 0.0084 | 0.0085 | 0.98 |
| patch0 | 1 | 78 | 0.9764 | 0.9769 | 0.0234 | 0.0227 | 1.03 |
| patch0 | 2 | 84 | 0.9981 | 0.9979 | 0.0020 | 0.0024 | 0.83 |
| patch0 | 3 | 85 | 0.9869 | 0.9866 | 0.0132 | 0.0127 | 1.04 |
| patch0 | 4 | 86 | 0.9958 | 0.9962 | 0.0040 | 0.0042 | 0.96 |
| patch0 | 5 | 87 | 0.9800 | 0.9806 | 0.0197 | 0.0188 | 1.05 |
| patch0 | 6 | 88 | 0.9955 | 0.9952 | 0.0046 | 0.0044 | 1.05 |
| patch0 | 7 | 89 | 0.9834 | 0.9835 | 0.0166 | 0.0168 | 0.98 |
| patch0 | 8 | 90 | 0.9976 | 0.9965 | 0.0030 | 0.0027 | 1.11 |
| patch0 | 9 | 97 | 0.9958 | 0.9959 | 0.0041 | 0.0042 | 1.00 |
| patch0 | 10 | 107 | 0.9922 | 0.9921 | 0.0078 | 0.0073 | 1.07 |
| patch0 | 11 | 108 | 0.9956 | 0.9956 | 0.0044 | 0.0046 | 0.94 |
| patch1 | 0 | 117 | 0.9915 | 0.9910 | 0.0088 | 0.0085 | 1.02 |
| patch1 | 1 | 122 | 0.9935 | 0.9928 | 0.0069 | 0.0063 | 1.08 |
| patch1 | 2 | 123 | 0.9944 | 0.9924 | 0.0066 | 0.0063 | 1.04 |
| patch1 | 3 | 124 | 0.9962 | 0.9952 | 0.0043 | 0.0046 | 0.92 |
| patch1 | 4 | 125 | 0.9876 | 0.9859 | 0.0133 | 0.0125 | 1.07 |
| patch1 | 5 | 136 | 0.9957 | 0.9935 | 0.0054 | 0.0046 | 1.16 |
| patch1 | 6 | 141 | 0.9949 | 0.9952 | 0.0049 | 0.0049 | 1.01 |
| patch1 | 7 | 142 | 0.9939 | 0.9935 | 0.0063 | 0.0061 | 1.03 |
| patch1 | 8 | 143 | 0.9960 | 0.9954 | 0.0043 | 0.0044 | 0.98 |
| patch1 | 9 | 144 | 0.9896 | 0.9884 | 0.0110 | 0.0107 | 1.03 |
| patch1 | 10 | 145 | 0.9854 | 0.9866 | 0.0140 | 0.0139 | 1.01 |
| patch1 | 11 | 146 | 0.9936 | 0.9930 | 0.0067 | 0.0059 | 1.14 |
| patch2 | 0 | 121 | 0.9820 | 0.9838 | 0.0171 | 0.0171 | 1.00 |
| patch2 | 1 | 122 | 0.9937 | 0.9926 | 0.0068 | 0.0063 | 1.07 |
| patch2 | 2 | 123 | 0.9932 | 0.9931 | 0.0068 | 0.0063 | 1.07 |
| patch2 | 3 | 124 | 0.9949 | 0.9932 | 0.0059 | 0.0046 | 1.28 |
| patch2 | 4 | 136 | 0.9950 | 0.9950 | 0.0050 | 0.0046 | 1.08 |
| patch2 | 5 | 140 | 0.9909 | 0.9892 | 0.0099 | 0.0081 | 1.23 |
| patch2 | 6 | 141 | 0.9951 | 0.9948 | 0.0051 | 0.0049 | 1.03 |
| patch2 | 7 | 142 | 0.9933 | 0.9934 | 0.0067 | 0.0061 | 1.09 |
| patch2 | 8 | 143 | 0.9951 | 0.9958 | 0.0046 | 0.0044 | 1.04 |
| patch2 | 9 | 144 | 0.9883 | 0.9894 | 0.0111 | 0.0107 | 1.04 |
| patch2 | 10 | 145 | 0.9862 | 0.9845 | 0.0146 | 0.0139 | 1.05 |
| patch2 | 11 | 146 | 0.9942 | 0.9944 | 0.0057 | 0.0059 | 0.98 |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| decoder validity: accepted strings that re-encode to themselves | 58 of 58 | all | PASS |
| B=0: acceptance of random bit strings (exhaustive over 4096 strings) | 0.928% | < 1% | PASS |
| B=1: acceptance of random bit strings (exhaustive over 4096 strings) | 0.488% | < 1% | PASS |
| B=0 r=1 (663 CZ): measured f = 0.1804 vs the predicted f = 0.1820 | 0.0088 | relative deviation <= 0.30 | PASS |
| B=1 r=1 (663 CZ): measured f = 0.1621 vs the predicted f = 0.1650 | 0.0173 | relative deviation <= 0.30 | PASS |
| B=0: decoded support reproduces the exact E0 = -3.6408 | 0 | |E_R - E_0| < 1e-06 | PASS |
| B=1: decoded support reproduces the exact E0 = -1.8616 | 0 | |E_R - E_0| < 1e-06 | PASS |
| readout confusion on 3 patch(es): smallest diagonal element | 0.9764 | >= 0.9 | PASS |
| readout error per qubit against the frozen calibration snapshot (worst ratio; on a real device this is the calibration-drift item) | 1.28 | within a factor 3 | PASS |

Every number above is computed by `scripts/gate_H0.py` from the raw counts in `data/hardware/H0_dryrun/counts` and stored in
`validation/H0_dryrun.json`.  The counts files are never modified.
