# Owner decision, 2026-10-02: run the full 2x2 SKQD on ibm_kingston whether or not the signed f >= 0.1 budget is met

Recorded by executor-opus under prompts/24 step R.0 (generated from `validation/H0_ddtest.json`; no number typed by hand).

## The owner's instruction, verbatim (2026-10-02)

> ibm approval is still waiting, have to do with the 600 second budget we have now, replan with the planner, check from arxiv which procedure can decrease the decoherence issue, test with that, if nothing works, start preparing to send the 2x2 circuit anyway to qpus to finish run and see result all the way through to the end, meaning the skqd run for 2x2 plaquettes using 121 s of qpu time.

Source: the header of `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (planner-fable, 2026-10-02) and the coordinator's
brief of the same day, which quotes the same sentence as the owner's authorisation for (i) the one Stage T job and (ii) the
Stage R jobs, with the coordinator's ruling that Stage R is pure rule D3' at the adopted f (planner decision P8's D3''-H0 lift of
the seven k = 1 circuits struck).

## What is waived, and against what measurement

- **The signed bar** (amendment 01 section 1(c), prompts/12): mean clean-shot fraction f >= 0.1 over the family, worst circuit
  >= 0.05, read on the scheduled circuit (amendment 01 item 2).
- **The measurement it is waived against:** Stage T (gate H0_ddtest, status PASS) adopted cell **T3** by the preregistered
  rule P7; its pooled reference-string clean fraction on the two k = 1 circuits is f = 0.1129 (68 % [0.1093,
  0.1166], 95 % [0.1058, 0.1203]); the baseline (no DD) cell measured
  f = 0.0400 (95 % [0.0358, 0.0446]).
- Stage T's read of the signed bar on the adopted cell's 95 % interval: **GO**.  That read covers two k = 1
  circuits only; the bar has never been measured on the family (k = 2-4), so the owner's decision -- not the read -- is what
  authorises Stage R.

## Scope

- The waiver is for the 2x2 run of prompts/24 Stage R only (gate H0_2x2, `data/hardware/H0_2x2_prep`).
- It changes no criterion, tolerance, convention, decoder, signed circuit family or criterion constant (`DIAG_MIN`, `E0_TOL`,
  `F_TOLERANCE`, `SIGMA_C3PRIME`, `C6_TOL`, `READOUT_FACTOR`, the D3' constants); it is not a precedent for 2x3.
- Every Stage R preregistration and report cites this file.
