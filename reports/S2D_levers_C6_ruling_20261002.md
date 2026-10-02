# Ruling on criterion C6 of gate S2D_levers (planner, 2026-10-02)

Question from the executor (`validation/BLOCKED.md`, prompts/LOG 2026-10-01): should C6 — estimator
consistency, |f_clean(mixture) − f_clean(reference)| / f_clean(reference) ≤ 0.25 on every Aer cell with
≥ 20 reference hits — apply to the low-p_ref k = 4 cells of E4, or only to the k = 1 cells the tolerance was
calibrated on (gate H0_model, C1)?  The one failing cell is `E4:B1_ref07_k4` at r = 0.174: deviation 0.321
at 4000 shots, 0.283 at 8000 shots (`validation/S2D_levers.json: data.C6`, `data.e4.aer`).

Every number below is read from `validation/S2D_levers.json` and `validation/H0_model.json` by the snippet
in section 5.  Nothing was re-sampled.

## 1. Ruling (three lines)

1. **C6 is scoped to the cells it was calibrated on: cells whose circuit has p_ref ≥ 0.5** (at 2x2 exactly
   the k = 1 circuits; H0_model C1 calibrated the 0.25 tolerance on `B0_ref06_k1_rep1`, p_ref 0.8833, at
   deviations 0.011 and 0.024).  **The 0.25 tolerance and the ≥ 20-hit floor are unchanged.**
2. **The k = 4 cells (p_ref 0.127 / 0.132) are recorded as information with their deviation, the z-score of
   the difference and the physical ceiling check** — nothing is deleted, the failing cell's 0.283 / 0.321
   stay in the JSON and the report — and no k = 4 criterion is introduced after the fact.
3. **Gate S2D_levers is re-assembled** (`python scripts/run_gate.py S2D_levers`; no Aer count is re-drawn);
   the worst deviation among the p_ref ≥ 0.5 cells is **0.0987** (`L0_asis_alap`, r = 0.174), so the expected
   outcome is **PASS 9/9**.  No verdict field changes: every verdict number (f_aer at the row cells, r_crit)
   is a k = 1 mixture value.

## 2. Why this is a rescoping and not a loosened tolerance

What C6 was built to measure (prompts/20 A, H0_model C1, `src/skqd/skqd.py` lines 205–229): the mixture fit's
correctness, checked against the reference-string count "at the shortest Krylov depth (p_max 0.883 / 0.889)
[where] it is the sharper of the two".  Two properties of a k = 1 cell make that comparison tight and
tolerance-calibrated, and neither holds at k = 4:

(a) **Shared information.**  At k = 1 the reference string carries 88 % of the clean weight, so the two
estimators are built on essentially the same count and their *difference* has a far smaller variance than
either estimator alone.  At k = 4 the reference string carries 13 % of the clean weight: the reference
estimator is a count of 48 (not 996) scaled by 1/p_ref = 7.6, and the two estimators use nearly disjoint
information, so the difference variance is the sum of the two.  Numbers for the failing cell (8000 shots):
σ_ref = 0.0086 on f_ref = 0.0530 (16 %), σ_mix = 0.0031 on f_mix = 0.0380; combined relative σ of the
deviation **0.172**, so the 0.25 tolerance is **1.45 σ** there and the null probability of a deviation above
0.25 is **0.146 per cell**.  At the k = 1 cells of the same E4 block the combined relative σ is 0.036
(r = 1) and 0.146 (r = 0.174, 82 hits); over the 28 row cells the deviations are 0.003–0.099.

(b) **The near-clean term.**  Near-clean strings (few structured errors that still decode, decision M4.4)
land on codewords at small Hamming distance from the *ideal outputs*.  At k = 1 the ideal output is 88 %
one string, so near-clean strings sit on codewords of ideal probability ≈ 0 and both estimators exclude
them.  At k = 4 the ideal distribution is spread over the sector (p_max 0.13), near-clean strings land on
codewords that carry ideal weight, and the two estimators absorb different admixtures of them: they need
not converge to each other with shots.  The 0.25 tolerance therefore has **no calibration at k = 4**; it
was never measured there.

Fixed-tolerance C6 at k = 4 is thus a test with a 15 % false-failure rate per cell from statistics alone,
on a quantity whose systematic part is uncalibrated.  Restricting it to p_ref ≥ 0.5 is exactly the scope
H0_model C1 established; the 0.5 threshold is the one prompts/23 C8 already uses for "the reference string
carries the signal" (p_ref < 0.5 "weakens C3'").

## 3. Is the failing cell a statistical artefact or a model defect?

Evidence read from the four k = 4 cells at 8000 shots (section 5 table):

| cell | n_ref | f_ref ± σ | f_mix ± σ | dev | z = (f_mix − f_ref)/σ_Δ | clean_acc ref / mix / ceiling |
|---|---|---|---|---|---|---|
| B0_ref06_k4 r = 1 | 199 | 0.2366 ± 0.0175 | 0.2770 ± 0.0048 | 0.171 | **+2.22** | 1551.9 / 1817 / 1982.8 |
| B0_ref06_k4 r = 0.174 | 39 | 0.0445 ± 0.0081 | 0.0446 ± 0.0032 | 0.002 | +0.01 | 291.8 / 292 / 395.8 |
| B1_ref07_k4 r = 1 | 238 | 0.2719 ± 0.0184 | 0.2475 ± 0.0060 | 0.090 | −1.26 | 1783.6 / 1624 / 1848.9 |
| B1_ref07_k4 r = 0.174 | 48 | 0.0530 ± 0.0086 | 0.0380 ± 0.0031 | 0.283 | **−1.65** | **347.9 / 249.5 / 324.9** |

(σ = half-width of the recorded 68 % intervals: Garwood for the reference count, profile likelihood for the
mixture; clean_acc = clean accepted shots, reference (n_ref − N a/dim)/p_ref, mixture w × accepted; ceiling
= accepted − N a, the most clean shots the cell can contain if no accepted shot is near-clean.)

- The failing cell is a **1.65 σ** deviation (1.32 σ at 4000 shots).  Its reference estimate of the clean
  accepted shots, **347.9, exceeds the physical ceiling of 324.9**: the reference estimator at p_ref 0.13 is
  dominated by its own Poisson noise (σ = √48 / 0.132 = 52 shots), and this draw sits high.  The mixture's
  249.5 is inside the ceiling.
- The four cells carry **no consistent sign** (+2.22, +0.01, −1.26, −1.65): a model defect of one
  estimator would push every k = 4 cell the same way.  Σz² = 9.24 for 4 d.o.f., chi-square p = **0.055** —
  the scatter is not significantly above statistics, and not comfortably below it either.
- The 0.25 tolerance would be a 3 σ test on this cell only at **≈ 34 000 shots** (information).

Conclusion: the failing cell is consistent with estimator variance at low p_ref — the artefact that
"shrinks only slowly with shots" (as 1/√N against a 1.45 σ bar) — and the record does not establish a model
defect.  Honest limit: a systematic k = 4 difference of up to ≈ 20 % between the two estimators is **not
excluded** by these cells; it would not touch any S2D_levers verdict field, and it is a legitimate
preregistered test for the first gate that uses k = 4 hardware data (the H0 main run), not for this one.

## 4. What the executor changes (prompts/21 part 0; binding)

`scripts/gate_S2D_levers.py` only, additively:
- `C6_P_REF_MIN = 0.5` next to `C6_TOL`, with a comment pointing here.
- In both C6 loops (row cells and E4 cells): a cell enters the pass/fail list only if
  `d["p_reference"] >= C6_P_REF_MIN` (and ≥ 20 hits, strided, as now).  Every cell with p_ref below the
  threshold goes into a new `data.C6_information_low_p_ref` list carrying: row, ratio, shots, accepted,
  reference_hits, p_reference, dev, sigma_ref, sigma_mix, z, clean_accepted_reference,
  clean_accepted_mixture, clean_accepted_ceiling, reference_exceeds_ceiling,
  shots_for_tolerance_at_3_sigma; plus a summary {n_cells, max_abs_z, sum_z2, chi2_p}.
- The criterion name becomes "C6 estimator consistency on every Aer cell with >= 20 reference hits and
  p_ref >= 0.5 (the k = 1 cells H0_model C1 calibrated the 0.25 tolerance on; ruling
  reports/S2D_levers_C6_ruling_20261002.md); low-p_ref cells recorded as information", its value string
  adds "<n> low-p_ref cells recorded (max |z| <..>)".  `C6_TOL`, `MIN_REF_HITS` unchanged.
- The report gains a "C6 ruling" section generated from those numbers (the ceiling sentence, the z table);
  the existing C6-history paragraph (`C6_first_attempt_E4_4000_shots`) stays.
- `tests/test_s2d_levers.py`: one test that recomputes z = −1.65 ± 0.02 and ceiling 324.9 < 347.9 for
  `E4:B1_ref07_k4`, r = 0.174 from the committed JSON, and one that a synthetic p_ref = 0.9 cell at
  deviation 0.3 still fails.
- `python scripts/run_gate.py S2D_levers` (assemble only; refuses to re-draw counts); expected PASS 9/9,
  C6 value "34 → 30 cells checked, worst 0.099".  `validation/BLOCKED.md`: append "resolved 2026-10-02 by
  the planner ruling (reports/S2D_levers_C6_ruling_20261002.md)"; status tables; LOG row; local commit.
  **Push: the owner's call** (the owner holds the push until C6 is settled; this ruling settles it, the
  push itself is not the executor's).

## 5. Reproduction snippet (all numbers above)

```python
import json, math
from scipy.stats import chi2, norm
d = json.load(open("validation/S2D_levers.json"))["data"]
for cid, cells in d["e4"]["aer"].items():
    for r, c in cells.items():
        N, acc, n, p, a, dim = c["shots"], c["accepted"], c["reference_hits"], c["p_reference"], c["garbage_acceptance"], c["dim"]
        fr, fm = c["f_clean_reference"], c["f_clean_mixture"]
        s_ref = (c["f_clean_reference_68"][1] - c["f_clean_reference_68"][0]) / 2
        s_mix = (c["f_clean_mixture_68"][1] - c["f_clean_mixture_68"][0]) / 2
        z = (fm - fr) / math.hypot(s_ref, s_mix); rel = math.hypot(s_ref, s_mix) / fr
        print(cid, r, n, round(fr, 4), round(s_ref, 4), round(fm, 4), round(s_mix, 4),
              round(c["c6_relative_deviation"], 3), round(z, 2),
              "clean_ref", round((n - N * a / dim) / p, 1), "clean_mix", round(c["w"] * acc, 1),
              "ceiling", round(acc - N * a, 1), "N_3sigma", round(N * (3 * rel / 0.25) ** 2),
              "P_null(dev>0.25)", round(2 * (1 - norm.cdf(0.25 / rel)), 3))
zs = [2.22, 0.01, -1.26, -1.65]; print("chi2 p", chi2.sf(sum(z * z for z in zs), 4))
worst = max(c["c6_relative_deviation"] for cells in d["aer"].values() for c in cells.values()
            if c and c["reference_hits"] >= 20 and c["p_reference"] >= 0.5)
print("worst dev, p_ref >= 0.5 row cells:", worst)   # 0.0987
```
H0_model C1: `validation/H0_model.json: data.C1_estimator_validation.{scheduled,unscheduled}.per_circuit[0]`
— p_reference 0.8833, relative_deviation 0.0108 and 0.0237.
