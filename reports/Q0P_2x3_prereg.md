# Q0P_2x3 preregistration block (prompts/26 A8) — generated from data/quantinuum/q0p_stages/predict.json

Created 2026-10-03 03:22:48 UTC.  Every number below is copied by `scripts/gate_Q0P_2x3.py --stage prereg-md` from the JSON; none is typed.  These are PREDICTIONS from vendor-published error rates (gate-only) and an ESTIMATE of the memory term; the vendor emulator (Stage E) replaces the memory estimate.

## Per device: gate-only f of the 44 frozen circuits and the three memory scenarios (ESTIMATE)

| device | f mean | f worst | pilot k=1 circuits | low | mid | high |
|---|---|---|---|---|---|---|
| H2-2 | 0.1502 | 0.15 | B0_ref25_k1: 0.15, B1_ref57_k1: 0.1504 | 0.1454 | 0.1398 | 0.113 |
| Helios-1 | 0.1642 | 0.164 | B0_ref25_k1: 0.164, B1_ref57_k1: 0.1645 | 0.1378 | 0.1117 | 0.0352 |
| H1-1 | 0.1113 | 0.1113 | B0_ref25_k1: 0.1113, B1_ref57_k1: 0.1115 | 0.1049 | 0.09771 | 0.06607 |
| H2-1 | 0.08602 | 0.08596 | B0_ref25_k1: 0.08596, B1_ref57_k1: 0.08613 | 0.08151 | 0.07641 | 0.05353 |

## Stage E plan (H2-2E, noise model on; eHQC)

| circuit | shots | jobs | eHQC | max_cost (formula + 10 %) |
|---|---|---|---|---|
| B0_ref25_k1 | 1000 | 1 | 4979 | 5477.12 |
| B1_ref57_k1 | 1000 | 1 | 4959 | 5454.68 |
| B0_ref25_k4 | 200 | 1 | 998.7 | 1098.59 |
| B1_ref57_k4 | 200 | 1 | 998.8 | 1098.68 |

Total 1.194e+04 eHQC.  GO rule: GO to Stage P iff the 95 % lower bound of pooled f_E >= 0.05 and the point estimate >= 0.10 (the signed bars applied to the emulator).

## Stage P pilot (H2-2; not under prompts/26)

| circuit | shots | jobs | HQC |
|---|---|---|---|
| B0_ref25_k1 | 1000 | 1 | 4979 |
| B1_ref57_k1 | 1000 | 1 | 4959 |

Total 9938 HQC (USD 1.242e+05, Azure-Standard-equivalent ESTIMATE).  Full-campaign GO rule: pooled device f 95 % lower bound >= 0.05 and point estimate >= 0.10.

## Full campaign, finite plan: the D3-type union reading at 0.7 f (data/S2D_recall_at_f.json, gate S1's recall rule, scaled as 1/(0.7 f), spread evenly over the sector's circuits)

| f | N_sector | shots | jobs (<= 10,000 shots each) | HQC | USD ESTIMATE | machine hours (H2-2 mid ESTIMATE) |
|---|---|---|---|---|---|---|
| 0.05 | {'B=0': 204300, 'B=1': 203100} | 407,420 | 56 | 2.023e+06 | 2.529e+07 | 239.6 |
| 0.1 | {'B=0': 102200, 'B=1': 101600} | 203,812 | 44 | 1.012e+06 | 1.265e+07 | 119.9 |
| 0.15 | {'B=0': 68100, 'B=1': 67700} | 135,832 | 44 | 6.746e+05 | 8.433e+06 | 79.9 |

## Rule D3' at 0.7 f (scripts/h0_support_plan.n4_of_sector; floor 267, round 100, lambda* from skqd.skqd.poisson_lambda_star, readout factor 0.82 as the rule defines it)

| f | N4 B=0 | N4 B=1 | finite campaign | k = 4 reachability |
|---|---|---|---|---|
| 0.05 | 1.762e+36 | 1.335e+11 | False | B=0: 32/677 states below 1e-6 (min 1.2e-34); B=1: 11/426 states below 1e-6 (min 1.6e-09) |
| 0.1 | 8.809e+35 | 6.673e+10 | False | B=0: 32/677 states below 1e-6 (min 1.2e-34); B=1: 11/426 states below 1e-6 (min 1.6e-09) |
| 0.15 | 5.873e+35 | 4.449e+10 | False | B=0: 32/677 states below 1e-6 (min 1.2e-34); B=1: 11/426 states below 1e-6 (min 1.6e-09) |
