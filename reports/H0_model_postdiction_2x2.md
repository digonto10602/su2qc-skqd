# Gate H0_model — post-diction of the H0 hardware counts at both ends of the T2 bracket

**Status: PASS** — `scripts/gate_H0_model.py`, circuit
`B0_ref06_k1_rep1` (663 CZ, B=0), calibration record `data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json`
(fingerprint `7fd6d65eaa1a1b4f`, 2026-09-22T08:00:30-06:00).
Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 6180c6a, 2026-09-30 15:31:18 MDT.  Runtime 2 s.  **No QPU time**: the hardware counts are the
2.0 s canary and the 15.0 s diagnostic already on disk, read-only.

The question is not whether the device performed: gate H0_diag settled that.  It is whether
the corrected model — Aer on the **scheduled** circuit, at a **measured** dephasing time, read
with the **clean-yield** statistic — reproduces the counts that already exist.  All three
corrections are needed: the unscheduled simulation has no idle windows at all, the record has
no free-induction T2, and the accepted-shot yield counts near-clean strings as clean.

## 1. C1 — is the estimator unbiased where the truth is known?

Two seeded Aer samples of the same circuit on the FakeFez snapshot, 2000 shots each, one
scheduled and one not.  The mixture estimator uses the whole accepted histogram; the
reference-count estimator uses one number.  They must agree, because on this circuit the
reference string carries 0.8833 of the ideal output.

| sample | circuit | shots | accepted | reference hits | clean (mixture) | clean (n_ref / p_ref) | clean (garbage-corrected) | relative deviation | near-clean | garbage | f_clean (mixture) | f_clean (reference) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| unscheduled | B0_ref06_k1_rep1 | 2000 | 328 | 178 | 206.3 | 201.5 | 201.0 | 0.024 | 105.5 | 16.2 | 1.258e-01 | 1.225e-01 |
| scheduled | B0_ref06_k1_rep1 | 2000 | 73 | 21 | 24.0 | 23.8 | 23.2 | 0.011 | 30.7 | 18.3 | 1.465e-02 | 1.416e-02 |

The near-clean column is the residual of the amended Step-4.4 model (decision M4.4):
accepted − clean − N a (1 − f).  It is 32 % and 42 % of the accepted shots of the unscheduled and of
the scheduled sample respectively — which is why the accepted count is not a clean-shot
measurement on the simulator either, not only on the device.

## 2. C2 — do the device counts carry a clean component at all?

The five hardware pubs of this circuit (canary + the four diagnostic option cells), decoded
here from the raw counts.  "expected if clean" is what the reference-string count would be if
the accepted shots above the garbage floor were clean shots; `P(<= seen)` is the Poisson
probability of seeing no more than the observed number under that hypothesis.

| job | shots | accepted | garbage floor N a | excess | reference hits | expected if the excess were clean | P(<= seen) | distance histogram d = 0..8 | w (mixture) | f_clean (mixture) |
|---|---|---|---|---|---|---|---|---|---|---|
| H0_ibm_fez_canary | 267 | 8 | 2.5 | 5.5 | 2 | 4.9 | 1.29e-01 | [2, 0, 2, 3, 0, 0, 0, 0, 1] | 0.407 | 1.49e-02 |
| H0_diag_J1 | 2000 | 35 | 18.6 | 16.4 | 2 | 15.0 | 3.88e-05 | [2, 0, 13, 5, 1, 6, 0, 5, 0] | 0.039 | 8.27e-04 |
| H0_diag_J2 | 2000 | 27 | 18.6 | 8.4 | 1 | 7.9 | 3.16e-03 | [1, 0, 9, 3, 0, 4, 1, 3, 1] | 0.013 | 2.14e-04 |
| H0_diag_J3 | 2000 | 25 | 18.6 | 6.4 | 1 | 6.2 | 1.48e-02 | [1, 0, 4, 4, 2, 6, 1, 2, 0] | 0.019 | 2.90e-04 |
| H0_diag_J4 | 2000 | 17 | 18.6 | -1.6 | 0 | -0.9 | - | [0, 0, 1, 1, 3, 6, 1, 2, 0] | 0.000 | 0.00e+00 |
| **pooled** | 8267 | - | 2.02 | - | 6 | 2.02 | P(>=) 0.0172 | - | 0.035 | 6.65e-04 |

Ideal mass by Hamming distance to the reference codeword: [0.883, 0.0, 0.001, 0.109, 0.0, 0.001, 0.002, 0.001, 0.003];
the decoder's exhaustive random-string acceptance of this sector is 0.00928
over 38 codewords.  Pooled: **6 reference hits over 8267 shots
against 2.018 expected from garbage**, P = 0.0172, i.e. a clean
component of **4.0 shots** and f_clean = **6.650e-04**
(1 sigma 2.56e-04 – 1.07e-03).

## 3. C3 / C4 — the bracket post-diction

Aer on the scheduled circuit against the record the device ran under, once with the record's
Hahn-echo T2 and once with the free-induction T2* of the diagnostic's windowed Ramsey pub.
8000 shots per end in 4 invocations of
2000 (seeds [11, 2011, 4011, 6011]).

| dephasing time | shots | accepted | reference hits | garbage expectation | clean reference hits | scaled to the 8267 hardware shots | predicted / measured | f_clean (reference) | f_clean (mixture) | accepted per 2000 shots | accepted / J1's 35 | distance histogram |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| record Hahn-echo T2 | 8000 | 504 | 193 | 1.95 | 191.05 | 197.42 | 49.58 | 3.297e-02 | 3.315e-02 | 126.0 | 3.60 | [193, 0, 163, 68, 16, 29, 2, 12, 7] |
| measured free-induction T2* | 8000 | 121 | 6 | 1.95 | 4.05 | 4.18 | 1.05 | 6.984e-04 | 6.197e-04 | 30.2 | 0.86 | [6, 0, 23, 23, 4, 26, 6, 14, 4] |

Criterion C3 is on the T2* end: its predicted clean reference hits, scaled to the hardware's
8267 shots, must lie in [1.33, 11.95] — a factor
3 of the measured 3.98.  The echo end is
computed by the same code and reported with its ratio; it is not a criterion, because the
record's echo T2 is not the time the circuit's unrefocused idle windows see.

## 4. The T2 table and its provenance

Rule M-T2: the measured T2* where the readout-corrected inversion resolves it, else the
3 sigma upper bound, else the smallest resolved value on the patch.  Source:
`validation/H0_diag.json: data.idle_tests.J1.ramw (diag_patch1_ramw, 2000 shots, total delay 43.52 us, readout reference J1 own all-0/all-1)`.

| physical qubit | logical | T2* measured (us) | 3 sigma bound (us) | T2 echo, record (us) | T2 used (us) | provenance | echo / used |
|---|---|---|---|---|---|---|---|
| 117 | 0 | 72.5 | 87.2 | 183.9 | 72.5 | measured | 2.5 |
| 122 | 1 | 36.5 | 43.6 | 53.8 | 36.5 | measured | 1.5 |
| 123 | 2 | - | 13.3 | 124.8 | 13.3 | upper_bound | 9.4 |
| 124 | 3 | 17.7 | 23.2 | 101.9 | 17.7 | measured | 5.7 |
| 125 | 4 | - | - | 50.5 | 13.3 | patch_minimum | 3.8 |
| 136 | 5 | 35.9 | 42.9 | 87.4 | 35.9 | measured | 2.4 |
| 141 | 6 | - | - | 108.1 | 13.3 | patch_minimum | 8.1 |
| 142 | 7 | 18.6 | 24.1 | 265.1 | 18.6 | measured | 14.3 |
| 143 | 8 | 15.2 | 20.9 | 115.6 | 15.2 | measured | 7.6 |
| 144 | 9 | - | - | 190.9 | 13.3 | patch_minimum | 14.3 |
| 145 | 10 | - | 13.4 | 130.8 | 13.4 | upper_bound | 9.8 |
| 146 | 11 | 19.4 | 24.8 | 16.0 | 19.4 | measured | 0.8 |

7 measured,
2 upper bounds,
3 at the patch minimum.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| C1 unscheduled Aer sample (2000 shots, seed 11): the mixture estimate of the clean accepted shots 206.3 against the reference-count estimate n_ref / p_ref = 201.5 (near-clean 105.5, garbage 16.2) | 0.0237 | relative deviation <= 0.25 | PASS |
| C1 scheduled Aer sample (2000 shots, seed 11): the mixture estimate of the clean accepted shots 24.0 against the reference-count estimate n_ref / p_ref = 23.8 (near-clean 30.7, garbage 18.3) | 0.0108 | relative deviation <= 0.25 | PASS |
| C2 the device counts carry a clean component: 6 reference-string hits over 8267 shots of 5 pubs against a garbage expectation of 2.018 (2.80 sigma; clean 4.0 shots, f_clean 6.650e-04) | 0.0172 | P(>= n | garbage) < 0.05 | PASS |
| C3 the T2* end of the bracket post-dicts the measured clean count: predicted 4.18 clean reference hits over 8267 shots against the measured 3.98 (echo end 197.42, ratio 49.58) | 1.0503 | predicted / measured in [0.33, 3.00] | PASS |
| C4 the T2* end reproduces the acceptance structure: predicted 30.2 accepted shots per 2000 against J1's 35 (echo end 126.0; distance chi-square vs J1 16.9, information) | 0.8643 | predicted / measured in [0.50, 2] | PASS |

Every number above is computed by `scripts/gate_H0_model.py` and stored in
`validation/H0_model.json`.  The hardware counts in `data/hardware/H0_*/counts/` are never
modified; the Aer counts of section 3 are written once to `data/hardware/H0_model` with the settings
they were drawn under and are refused rather than re-drawn.
