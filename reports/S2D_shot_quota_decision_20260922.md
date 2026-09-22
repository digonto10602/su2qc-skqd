# Amendment 01, open item 5 — the shot quota of manual Step 9.2: analysis and recommendation (2026-09-22)

Planner memo (planner-fable, max effort) for the owner's signature of `proposal/amendment_01_devices_and_budgets.md`,
section 5 item 5.  Nothing was run on hardware; no threshold, tolerance, convention or circuit was changed; the
amendment file itself is not edited (the caller folds this memo and the item-4 analysis into it).

**Sources.**  Every number is either (a) read from a JSON of this repository or from the manual — the key or the
line is named — or (b) a **planner computation [PC]** made on 2026-09-22 with the repository's own code
(`skqd.exact.Model(3)`, `skqd.krylov.coarse_states` on the Step 4.2 references, `skqd.skqd.exact_support`,
`poisson_lambda_star`, `READOUT_FACTOR`, the per-circuit f of `validation/S2D.json:data.2x3.per_circuit`, and for
the emulated widths the same emulator as `scripts/gate_S1.py` / `scripts/s2d_recall_at_predicted_f.py`).  The
three [PC] snippets are in the appendix (26 s, 2 s and 342 s on the laptop CPU); the emulation snippet reproduces
the committed recall and |B| values of `data/S2D_recall_at_f.json` exactly (same seeds, same RNG stream), which
is its check.  [PC] values are to be superseded by a script + JSON once the owner signs (section 7).

## 1. The manual's two statements, and whether they can both hold

Step 4.4 (line 130): *"the design rule is therefore: circuits of one coarse step (≤ 500 CZ, f ≳ 0.2 on a
Heron-class device with ε ≤ 3×10⁻³), and shots chosen so that a configuration of ideal probability p is seen at
least three times with 95% probability,"* — eq. (5) (line 132): *"S ≥ 6.3/(0.82 f p) ≃ 7.7/(f p) (Poisson mean
6.3), e.g. f = 0.2, p = 10⁻³: S ≈ 3.9×10⁴ **per circuit**"* — line 134: *"which Nighthawk r2 (10⁵ circuits per
second) executes in seconds and Heron (4×10³ per second) in a quarter of a minute.  Total budgets of 2×10⁵ shots
per sector are assumed below."*

Step 9.2 (line 208): *"circuit set: references of Step 4.2 × coarse steps k = 1..4 (32–44 circuits per sector) at
≤ 500 CZ each; shots from Eq. (5) with the measured f, budget 2×10⁵ per sector"*.  Step 8.3 (line 204): *"fix the
shot budget by Eq. (5) from the measured f.  Gate S3: recall of the 99.9% support ≥ 0.9 in simulation for the
production circuit set."*  Plan B (line 239): *"reduce the circuit set to k = 1, 2 coarse steps (≤ 500 CZ) and
raise shots by Eq. (5)"*.  Gate table (Step 10): S1 *"emulated support recall ≥ 0.9 at f ≥ 0.1 with the production
budget"*, S3 *"Aer device-model recall ≥ 0.9 for the production set; shot budget fixed"*, H1 *"certified interval
I₀ of width ≤ 0.1 containing the exact E₀; recall ≥ 0.8"*, H2 *"cluster energy certified to ±r_H ≤ 0.15"*.

**Arithmetic (manual numbers only).**  Eq. (5) at its own design point gives 38 389 shots per circuit
(`validation/S2D.json:data.shot_budget."manual design point".N_circuit`, reproducing the manual's 3.9×10⁴).
Times the circuit set of the same sentence of Step 9.2: 32 × 38 389 = 1 228 448 and 44 × 38 389 = 1 689 116
(`N_sector` of the same block).  Both are 6–8 times the 2×10⁵ of that sentence.  **Under the literal reading —
eq. (5) per circuit, as its own example says — the sentence of Step 9.2 cannot be satisfied at any f ≤ 0.2 with
the circuit set it prescribes.  The manual is self-inconsistent on this point; the inconsistency is internal to
the document and was computable on 10 Sept 2026 without any device data.**

The only reading that reconciles the two clauses is to take p in eq. (5) as the probability of a configuration
in the sector's *pooled* sampling distribution (the union support of Step 5.1), which gives N_sector = 6.3/(0.82 f p)
= 38 389 at f = 0.2 and 123 954 / 124 569 (B=0 / B=1) at the S2D f (`data/S2D_recall_at_f.json:
shot_rule_union_reading_N_sector`), both ≤ 2×10⁵.  That reading contradicts the words "per circuit" in eq. (5) and
changes what p means (a state with p = 10⁻³ in one circuit has pooled probability 10⁻³/32 at B=0).  It is a
re-interpretation, not the text.

Two computed observations on where 2×10⁵ may come from (hypotheses, not findings): 5 × 38 389 = 191 945 ≈ 2×10⁵,
i.e. eq. (5) at the design point for a single reference with five coarse circuits (Table 4 row "8 references × 5
coarse circuits", Algorithm 3 "k = 0..4"), before Step 4.2 made multi-reference generation "essential"; and, at
f = 0.2, 2×10⁵ coincides with the per-state plan under which every 99.9 %-support state of B=1 is seen **at least
once** with 95 % probability (199 656, section 4 [PC]).  Neither can be verified from the text.

**Which statement is binding.**  What the preregistration *tests* is the recall of the 99.9 % support with the
production budget (S1 PASS: recall 1.000 / 0.989 at f = 0.1 with 2×10⁵ shots, `validation/S1.json:criteria[0,2]`;
S3 and H1 use the same quantity).  No gate tests "three hits per configuration at p = 10⁻³"; the only place it was
ever checked literally is gate S2D's criterion 7 (`validation/S2D.json:criteria[6]`, 4 605 472 > 2×10⁵), and that
criterion fails at the manual's own design point too — it can never pass for the Step 9.2 circuit set, whatever the
device.  The binding statement is therefore the quota as the budget under which every tested guarantee was
validated; eq. (5) is a sizing rule whose p was never specified for the multi-reference set.  S2D's criterion-7 FAIL
is a finding about the manual, not about the device or this package.

## 2. Two guarantees, separated

- **G1, the recall guarantee** (S1 ≥ 0.9, S3 ≥ 0.9, H1 ≥ 0.8): a statement about the union support B over all
  circuits of a sector against the exact 99.9 % support S (86 states at B=0, 95 at B=1, `skqd.skqd.exact_support`).
  A state counts once it is observed *once* in *any* circuit.  Its expected clean count over the sector is
  λ_s = Σ_c N_c · 0.82 f_c · p_c(s), with p_c(s) the ideal probability of s in circuit c; P(s seen) = 1 − e^{−λ_s}
  (Poisson, clean shots only, no garbage credit — the same model as rule D3' of prompts/16).
- **G2, the per-configuration detection rule** (eq. 5): in a circuit where s has ideal probability p, N_c shots
  see s at least three times with probability 0.95 from that circuit alone: N_c ≥ λ*/(0.82 f p), λ* = 6.2958
  (`poisson_lambda_star(3, 0.95)`).  Per circuit, at a nominal p, independent of the ground-state weight of s.
  Three hits (rather than one) make the *count ranking* of the primary-endpoint curve stable ("top-|B| by count",
  Table 3) and protect a single observation against being a garbage acceptance — that is my reading of its purpose;
  the manual does not say.

The quota was written for G1: "Total budgets of 2×10⁵ shots per sector are assumed below" introduces the
emulations (Table 4's last row, Step 6.2, gate S1), all of which spend a *total* per sector, and the gates that
check it check recall.  Eq. (5) states G2.  They coincide only under the pooled reading of section 1.

**What the quota delivers, per support state [PC]** (2×10⁵ split uniformly: 6 250 shots on each of the 32 B=0
circuits, 16 667 on each of the 12 B=1 circuits, exactly the plan of `data/S2D_recall_at_f.json`; f per circuit from
S2D, 0.05319–0.05373):

| sector (support) | f | min λ_s | states with λ_s < 6.30 (three hits) | states with λ_s < 3.00 (one hit, 95 %) | E[recall], Poisson | emulated recall, 3 seeds (`data/S2D_recall_at_f.json`) | P(recall < 0.9) | P(recall < 0.8) | P(all support states seen) | p* of eq. (5) per circuit at this N_c |
|---|---|---|---|---|---|---|---|---|---|---|
| B=0 (86) | S2D 0.0533 | 1.61 | 10 | 2 | 0.9934 | 1.000 / 0.988 / 1.000 | 1.3e-13 | 2.6e-41 | 0.54 | 0.0230 |
| B=1 (95) | S2D 0.0535 | 0.80 | 35 | 15 | 0.9602 | 0.958 / 0.989 / 0.989 | 8.4e-4 | 8.3e-15 | 0.011 | 0.00861 |
| B=0 | virtual rz 0.0817 | 2.47 | 6 | 2 | 0.9978 | 1.000 / 1.000 / 1.000 | 1.7e-21 | 4.8e-66 | 0.82 | 0.0150 |
| B=1 | virtual rz 0.0819 | 1.23 | 27 | 8 | 0.9809 | 0.979 / 0.989 / 0.979 | 1.4e-7 | 1.3e-25 | 0.13 | 0.00562 |
| B=0 | 0.7 × S2D = 0.0373 | 1.13 | 20 | 6 | 0.9861 | — | 1.1e-8 | 6.6e-27 | 0.26 | 0.0329 |
| B=1 | 0.7 × S2D = 0.0375 | 0.56 | 38 | 29 | 0.9328 | — | **0.069** | 1.0e-8 | 3.4e-4 | 0.0123 |
| B=0 | 0.2 (design point) | 6.04 | 2 | 0 | 0.99995 | — | — | — | 0.995 | 0.00614 |
| B=1 | 0.2 (design point) | 3.00 | 6 | 0 | 0.9980 | — | — | — | 0.82 | 0.00230 |

(P(recall < x) is exact for independent misses — Poisson-binomial over the support states; recall < 0.9 needs
≥ 9 of 86 or ≥ 10 of 95 misses.  The Poisson model is conservative against the emulation by 0.3–2 points of recall,
because the emulator's local corruption and readout flips also produce accepted valid states.)

Reading.  (i) At the declared f the quota delivers G1 with margin: the risk that emulated recall falls below 0.9
is 10⁻¹³ (B=0) and 8×10⁻⁴ (B=1); below H1's 0.8 it is negligible.  (ii) It does **not** deliver G2 at p = 10⁻³:
the per-circuit guarantee at the quota covers only p ≥ 0.023 (B=0) / 0.0086 (B=1), a factor 23 / 8.6 above the
manual's p — and even at f = 0.2 six B=1 support states stay below three expected hits.  (iii) G2 at p = 10⁻³ per
circuit is neither necessary for G1 (which holds without it) nor sufficient for the support: six B=1 support states
never reach p = 10⁻³ in any circuit (max_c p_c(s) = 6.2e-4 to 8.5e-4 [PC]; the S1 report's "89 of 95", against the
manual's "94 of 95"), so eq. (5) at p = 10⁻³ says nothing about them however many shots are spent — only the union
count λ_s does.  (iv) The margin of G1 is thin in one place: if the device's f is 30 % below the declared value, the
B=1 recall criterion becomes a 7 % risk at the quota — a fixed quota degrades silently with f, which is exactly why
Step 9.2 says "shots from Eq. (5) with the measured f".

**So the contradiction is between two guarantees, not two numbers.**  It dissolves once the preregistration names
which guarantee the shots are sized for and evaluates it on the states the recall criterion counts (section 4).

## 3. The three options of the amendment, costed

| option | shots per sector B=0 / B=1 | S3 simulation at 3.198 s per shot (laptop CPU, `validation/S2D.json:data.per_shot_cost_2x3`) | buys | forgoes / breaks |
|---|---|---|---|---|
| **A. raise the quota to eq. (5) per circuit at the measured f** | 4 605 472 / 1 722 096 (S2D `shot_budget`), 6.33×10⁶ in all | 4 092 / 1 530 CPU-h (S2D `desktop_job_hours_per_sector_this_cpu`) | G2 at p = 10⁻³ in every circuit, for every configuration of the sector, most of them outside the 99.9 % support (median Σ_c p_c(s) over the support is 0.041 / 0.023 [PC]: the support states are not the p = 10⁻³ configurations) | 32× / 8.6× the quota; device time = N/throughput, throughput unknown (S2D's illustrative 100 / 300 / 1000 shots per minute give 767 / 256 / 77 h for B=0 alone); the six weakest B=1 support states still uncovered per circuit |
| **B. reduce the circuit set** | circuits affordable under 2×10⁵ at eq. (5): ⌊2×10⁵/143 921⌋ = 1 at the S2D f, ⌊2×10⁵/38 389⌋ = 5 at f = 0.2 — i.e. one reference; Plan B (k = 1, 2 only) costs 16 × 143 921 = 2 302 736 / 6 × 143 508 = 861 048 | — | nothing that the quota does not already give | multi-reference coverage, which Step 4.2 calls essential: a single reference reaches 61 of 86 / 34 of 95 support states at p > 10⁻³ against 86 / 89 for all references (`validation/S1.json:data.reach|…`).  Not viable at any f considered |
| **C. accept a larger p at the quota** | 200 000 / 200 004 | 178 / 178 CPU-h | G1 as in section 2 (P(recall < 0.9) 10⁻¹³ / 8×10⁻⁴ at the declared f) | G2 weakened to p* = 0.0230 / 0.00861 per circuit (0.00614 / 0.00230 at f = 0.2); the weakest support states (max_c p_c = 1.6e-3 / 6.2e-4) covered only through the union (P(seen) 0.80 / 0.55); the widths of section 4 stay at the quota's values (H1 Weinstein 0.074–0.098, H2 0.097–0.123); the guarantee degrades with f |

Option A buys a guarantee the physics does not use, at a cost that is not known to be affordable; option B destroys
the coverage that makes the support reachable; option C keeps the budget and every tested guarantee at the declared
f, but leaves the preregistration with a design rule (eq. 5) that its own budget cannot honour and a recall margin
that evaporates if f is 30 % low.

## 4. The fourth option: the per-state rule of D3' (prompts/16) transferred to 2x3

**Rule.**  Every state s of the exact 99.9 % support of the sector (86 / 95 states) must have expected clean count
λ_s = Σ_c N_c · 0.82 f_c · p_c(s) ≥ λ* = 6.2958 over the sector's production circuits (the union support of Step
5.1), at the measured f; f_c is the clean-shot fraction of circuit c (today S2D's declared-input value per circuit;
on the day the pilot's measured value, manual timeline week 3), p_c(s) its ideal probability in the production
circuit (`coarse_states`; the structured circuits reproduce it to 1.9e-14, `validation/S2.json`).  Structure as
D3': the quota's uniform split is the floor on every circuit; the k = 4 circuits of the sector (8 at B=0, 3 at
B=1 — the coarse step at the largest angle, which spreads the references furthest and is where every weak support
state has its best circuit [PC]) receive N₄ extra shots, the smallest multiple of 100 that satisfies the rule.
Garbage acceptances are not credited.  This is the sentence already adopted for H0 (prompts/16, D3'), with the
target set changed from "every sector state" (saturation, 38 / 20 states at 2x2) to "every 99.9 %-support state"
(2x3 is the SKQD test; its sectors of 677 / 426 states are not meant to saturate, manual Step 0).

**Numbers [PC].**  N_sector = 2×10⁵ + n_k4 × N₄:

| f | level | B=0: N₄ per k=4 circuit / N_sector / min λ_s / E[recall] / P(all 86 seen) / S3 CPU-h | B=1: N₄ / N_sector / min λ_s / E[recall] / P(all 95 seen) / S3 CPU-h |
|---|---|---|---|
| S2D declared (0.0534) | **three hits, 95 % (λ* = 6.2958)** | **44 500 / 556 000** / 6.30 / 0.99996 / 0.9965 / 494 h | **202 700 / 808 104** / 6.30 / 0.99996 / 0.9960 / 718 h |
| S2D declared | one hit, 95 % (λ = 2.9957) | 13 200 / 305 600 / 3.00 / 0.9988 / 0.902 / 272 h | 81 000 / 443 004 / 3.00 / 0.9982 / 0.837 / 394 h |
| virtual rz (0.0817) | three hits | 23 800 / 390 400 / 347 h | 122 100 / 566 304 / 503 h |
| virtual rz | one hit | 3 300 / 226 400 / 201 h | 42 600 / 327 804 / 291 h |
| 0.7 × S2D (0.0374) | three hits | 70 100 / 760 800 / 676 h | 302 200 / 1 106 604 / 983 h |
| 0.7 × S2D | one hit | 25 400 / 403 200 / 358 h | 128 300 / 584 904 / 520 h |
| S2D declared | three hits, uniform over all circuits instead of the k = 4 allocation | 24 425 per circuit / 781 600 | 130 877 per circuit / 1 570 524 |
| S2D declared | three hits, unconstrained linear-programme optimum | 242 518 (only the 6 reaching k = 4 circuits get shots) | 481 132 (only the 3 k = 4 circuits) |

P(recall < 0.9) under the three-hit plan is below 10⁻⁵⁵ in both sectors; under the one-hit plan below 10⁻²⁵.  The
LP optimum is 2.3× / 1.7× cheaper than the D3'-type allocation but abandons k = 1..3, i.e. the yield-versus-CZ
curve of claim (iii) and the k-resolved support statistics; the D3'-type allocation keeps every circuit at the
quota's count and adds to the k = 4 circuits only — the same trade the H0 plan made, one sentence to preregister.

**Emulated consequences [PC]** (same emulator as gate S1, p_ro = 1 %, three seeds, f = 0.0534; the "quota" rows
reproduce `data/S2D_recall_at_f.json` exactly):

| plan | sector | shots | \|B\| (3 seeds) | recall | captured weight | E_R − E₀ | r_H = Weinstein width | Kato–Temple width | gap assumption r_H < E₁ − E_R |
|---|---|---|---|---|---|---|---|---|---|
| quota 2×10⁵ | B=0 | 200 000 | 313 / 311 / 320 | 1.000 / 0.988 / 1.000 | 0.99992 / 0.99986 / 0.99994 | 6.9e-4 / 1.1e-3 / 5.5e-4 | **0.0798 / 0.0985 / 0.0740** | 0.0023 / 0.0036 / 0.0020 | holds |
| D3'-type, three hits | B=0 | 556 000 | 489 / 494 / 492 | 1.000 × 3 | 0.999995 × 3 | 5.5e-5 / 5.8e-5 / 5.0e-5 | **0.0242 / 0.0246 / 0.0238** | 2.1e-4 – 2.2e-4 | holds |
| D3'-type, one hit (fallback) | B=0 | 305 600 | 394 / 385 / 393 | 1.000 × 3 | 0.999973 / 0.999976 / 0.999978 | 2.7e-4 / 2.3e-4 / 2.2e-4 | 0.0529 / 0.0484 / 0.0470 | 0.0010 / 0.0009 / 0.0008 | holds |
| quota 2×10⁵ | B=1 | 200 004 | 224 / 237 / 222 | 0.958 / 0.989 / 0.989 | 0.99969 / 0.99983 / 0.99978 | 2.1e-3 / 1.2e-3 / 1.5e-3 | **0.1234 / 0.0974 / 0.1025** | not valid (gap fails) | fails |
| D3'-type, three hits | B=1 | 808 104 | 369 / 362 / 367 | 1.000 × 3 | 0.999998 / 0.999994 / 0.999998 | 1.6e-5 / 4.9e-5 / 1.6e-5 | **0.0124 / 0.0207 / 0.0128** | 0.0063 / 0.0175 / 0.0067 | **holds** (splitting E₁ − E₀ = 0.024) |
| D3'-type, one hit (fallback) | B=1 | 443 004 | 325 / 322 / 321 | 1.000 × 3 | 0.999969 / 0.999983 / 0.999962 | 2.3e-4 / 1.3e-4 / 2.8e-4 | 0.0429 / 0.0333 / 0.0461 | not valid (gap fails) | fails |

For comparison, gate S1 at f = 0.1 with 2×10⁵ shots: r_H = 0.0542 (B=0) / 0.0837 (B=1), gap assumption false at
B=1 (`validation/S1.json:data.production`).

Three consequences for the hardware gates.  (1) **H1** ("certified interval of width ≤ 0.1"): at the quota and the
declared f the Weinstein interval is 0.074–0.098 wide — inside 0.1 in all three seeds but with one seed at 0.098;
the Kato–Temple interval (0.002–0.004, gap-assumed, and the gap holds) passes comfortably.  Under the three-hit
plan the Weinstein width is 0.024.  (2) **H2** ("cluster energy certified to ±r_H ≤ 0.15"): at the quota r_H =
0.097–0.123 (passes, margin ≤ 0.05); under the three-hit plan 0.012–0.021 — and since that is below the cluster
splitting 0.024 the gap assumption holds in all three seeds, i.e. the manual's *"preregistered stretch goal, not a
gate"* (Step 5.3: "resolving the splitting requires r_H below the splitting (0.024 at 2×3)") is met in emulation
under the per-state plan and not under the quota.  The one-hit fallback plan already gives recall 1.000 in every seed and halves the quota's widths (r_H 0.047–0.053 / 0.033–0.046), but at B=1 r_H stays above the splitting, so the gap assumption fails as it does at the quota: the stretch goal needs the three-hit level.  (3) The recall metric counts states, the energies count weight:
the ten B=0 / thirty-five B=1 support states left below three expected hits by the quota carry 6.2e-4 / 2.2e-3 of
the ground-state weight, and the six B=1 states that drive N₄ carry 2.3e-4 in all (eq. (6) bound on E_R − E₀ for
losing them: 3.9e-3 with W = 16.80) [PC].  The rule therefore spends most of its B=1 shots on states that matter
for the preregistered recall metric and the count-ranked endpoint, not for E₀ — which is a reason to keep the
recall metric as preregistered rather than to redefine it now.

**Does D3' transfer?**  Mechanically yes: the formula, λ*, the 0.82 factor, the k = 4 allocation and the
"smallest multiple of 100" are unchanged (`scripts/h0_support_plan.py:n4_of_sector` takes the circuit set, the
per-circuit f and the ideal probabilities; only the target-state index set differs).  Four differences at 2x3:
(i) target set = `exact_support(p, 1e-3)` of the sector, not the whole sector; (ii) the ideal probabilities come
from `coarse_states` until the 2x3 circuits are frozen for the ion device, after which the amplitude cross-check
of `h0_support_plan.py` (QPY statevector vs `apply_groups`, < 1e-9) must be repeated — S2's 1.9e-14 makes a
surprise unlikely; (iii) f_c is a vendor-declared class value today and the pilot's measurement on the day (the
rule scales as 1/f: 0.7 f costs 761 k / 1 107 k); (iv) the margin: D3' used 0.7 × f_cal because H0's criterion 2
tolerates 30 %; at 2x3 the equivalent is the statistical precision of the pilot's f, which is not a preregistered
tolerance — the rule is stated at the measured f, and the 0.7 row is the sensitivity, not a proposal.
Validation status of the rule itself: at 2x2 the D3' plan predicted saturation and the FakeFez rehearsal delivered
it (`validation/H0P_rehearsal.json` PASS 18/18, supports 38/38 and 20/20, prompts/LOG.md 2026-09-21).

## 5. Recommendation for the owner's signature

**Sign (one rule, one number at the declared inputs).**  Step 9.2's "budget 2×10⁵ per sector" becomes:

> Shots per 2x3 sector: 2×10⁵ split uniformly over the sector's production circuits as the floor, plus N₄ shots on
> each k = 4 circuit, N₄ the smallest multiple of 100 such that every state of the exact 99.9 % support has expected
> clean count Σ_c N_c · 0.82 f_c · p_c(s) ≥ 6.2958 (three observations with 95 % probability, manual eq. 5) at the
> measured f, garbage not credited.  At the declared 2x3 inputs of gate S2D this is **556 000 (B=0) and 808 104
> (B=1) shots, 1 364 104 in all**; the counts are recomputed once from the pilot's measured f and frozen before the
> production run (the H0 procedure: plan file stamped with the calibration, checked by the submitter).

**What it buys.**  Every support state seen ≥ 3 times with probability ≥ 0.95 (≥ once with 0.998); expected recall
0.99996, P(recall < 0.9) < 10⁻⁵⁵, P(all support states seen) 0.996 in both sectors [PC]; in emulation |B| 489–494 /
362–369, E_R − E₀ ≈ 5e-5 / 2–5e-5, r_H 0.024 (H1 needs ≤ 0.1) and 0.012–0.021 (H2 needs ≤ 0.15) with the B=1 gap
assumption holding — the stretch goal of Step 5.3 within reach.  Eq. (5) is honoured in its own words ("seen at
least three times with 95 % probability") for every configuration the recall criterion counts, and the shot count
follows the measured f as Step 9.2 requires.

**What it forgoes.**  Eq. (5) at p = 10⁻³ per circuit for configurations *outside* the 99.9 % support (option A,
6.33×10⁶ shots): those may be seen fewer than three times or not at all, which affects the size and count-ranking
statistics of the endpoint curve at large |B| and nothing in the certified energies.  It also forgoes the fixed
2×10⁵ cap: the cost scales as 1/f_measured (0.7 × declared f → 760 800 / 1 106 604).

**Measured cost.**  Shots: 1 364 104 (3.4× the quota's 400 004; 4.6× less than option A).  S3 simulation at the
laptop's measured 3.198 s per shot: 494 + 718 = 1 212 CPU-h against 355 h at the quota and 5 622 h for option A —
a desktop-GPU / cluster job either way (S3 is not yet on the Perlmutter allowlist; the batched-shot GPU rate is not
measured, `validation/L4.json` notes: no GPU path on the laptop).  Device time: N/throughput; with S2D's
*illustrative* 100 / 300 / 1000 shots per minute the plan is 227 / 76 / 23 h of device time for both sectors — the
vendor's actual throughput is an owner input, as the amendment already says.

**Named fallback, to be chosen at signature and not on the day.**  If the device allocation cannot carry the
three-hit level, the same rule at the one-hit level (λ = 2.9957, "seen at least once with 95 %") costs 305 600 /
443 004 shots (748 604 in all, 1.9× the quota; 665 CPU-h) with expected recall 0.9988 / 0.9982 and P(all support
states seen) 0.90 / 0.84; its emulated widths are in the table of section 4 (recall 1.000 in all seeds, r_H 0.047–0.053 / 0.033–0.046, B=1 gap assumption not met).  The bare quota (option C) is the
last resort and must then be preregistered with its computed risk (P(recall < 0.9) = 8×10⁻⁴ at the declared f,
0.069 at 0.7 f, H1 Weinstein width 0.074–0.098).

**Does this change the preregistration?**  Yes: the quota becomes a floor and the production count is set by the
rule; the p of eq. (5) becomes the actual ideal probability of each support state in the production circuits,
summed over the sector.  Unchanged: the recall thresholds (0.9 S1/S3, 0.8 H1), the widths (0.1 H1, 0.15 H2), λ*
(three hits, 95 %), the 0.82 readout factor, p_ro = 1 % of the proxy, the circuit family and set (32 / 12 circuits,
k = 1..4), the references, every convention.  **Why it is a correction and not a response to S2D's FAIL:** (a) the
defect is internal to the manual — line 132's "3.9×10⁴ per circuit" times line 208's "32–44 circuits" exceeds line
208's "2×10⁵" — and needs no device number to see; (b) no measured device value enters the rule, the declared f
enters this memo only to price it, and the count on the day comes from the measured f exactly as Step 9.2 already
prescribes; (c) the change adds shots and strengthens every tested guarantee (recall, both widths) — a post-hoc
relaxation would do the opposite; (d) it is the rule already adopted for H0 in prompts/16 and validated in
rehearsal, so both lattices are sized by one preregistered sentence; (e) S2D's criterion 7, which the change
replaces, could never pass for the manual's circuit set at any f ≤ 0.2, so it was not measuring the device.

## 6. Residual risks

- The rule's cost is set by six B=1 support states with p_c(s) ≤ 8.5e-4 in every circuit (ground-state weight
  3.4e-5–4.3e-5 each); the manual's "94 of 95" would have implied one such state.  The discrepancy was recorded at
  S1 time (`reports/S1_support_emulation_controls.md`, 89 of 95) and is not new; it is why B=1 costs 1.45× B=0.
- The Poisson model is conservative against the emulation by 0.3–2 points of recall (section 2); the emulated
  widths are single-noise-model numbers (the S1 proxy), not the Aer device model of S3 — S3 at the signed plan is
  the check, and its cost is the 1 212 CPU-h above.
- f on the day: the rule is evaluated once, from the pilot; if the pilot's f is 30 % below the declared value the
  three-hit plan costs 1.87×10⁶ shots.  A cap on the day is the owner's to set now, not the executor's then
  (prompts/16 B'3 logic).

## 7. What the executor does once the owner signs (for the caller's next prompt; nothing here is started)

1. `scripts/shot_plan_2x3.py` (or `h0_support_plan.py` generalised by a `--lattice/--target support999` option):
   the rule of section 5 from `coarse_states` and S2D's per-circuit f, with `--f-measured` override, JSON
   `data/shot_plan_2x3_<source>.json` (keys as `data/H0_shot_plan_*.json`: `rule, lambda_star, floor, sectors.<sec>.
   {support999, N4, N_sector, min_lambda, expected_recall, P_all_seen, per_state[...]}, shots_by_circuit`) and a
   report; pass criteria: `sectors["B=0"].N4 == 44500`, `["B=1"].N4 == 202700`, `min_lambda >= 6.2958` both, the
   emulated recall/|B| of the quota rows equal to `data/S2D_recall_at_f.json`.  Runtime ≈ 1 min plus ≈ 6 min if the
   emulation table of section 4 is regenerated (it should be, into the same JSON).
2. Gate S2D: criterion 7 ("shots per sector from the shot rule ≤ 2e5") is replaced by two criteria per sector,
   "per-state plan: min λ_s ≥ λ*" and "N_sector at the declared f ≤ the signed allocation A_sector" (A is the
   owner's number; if the owner signs the plan itself, A = 556 000 / 808 104); the eq.-(5)-per-circuit table stays
   in the report as information.  `scripts/make_amendment.py` section 3 is regenerated from the new JSON.
3. Gate S3 runs at the signed plan's `shots_by_circuit`, not at 2×10⁵ (`slurm/s3_2x3.sbatch` gains `--shots-plan`);
   S3 to the Perlmutter allowlist or the desktop GPU; the 30-minute rule applies per invocation via the sampling
   cache pattern of prompts/16 F2.
4. Tests: the D3' arithmetic on the 2x3 target set (synthetic and real), the cross-check against
   `data/S2D_recall_at_f.json`.
5. When the 2x3 circuits are frozen for the ion device: the amplitude cross-check (< 1e-9) before the plan is
   recomputed from the pilot's f.

## Appendix — reproduction of the [PC] numbers (repository code only)

A1. Per-state expected counts under the quota, the per-state rule (uniform and LP), eq. (5) readings (26 s):

```
python - <<'EOF'
import sys, json, numpy as np; sys.path.insert(0,'src')
from skqd.exact import Model, mass_default
from skqd.krylov import references, term_groups, coarse_states, basis_vector
from skqd.skqd import poisson_lambda_star, READOUT_FACTOR, exact_support, shot_rule
from scipy.optimize import linprog
M=Model(3); g2=4.0; G=term_groups(M.terms,g2,mass_default(g2)); lam3=poisson_lambda_star(3,0.95); lam1=poisson_lambda_star(1,0.95)
S2D=json.load(open('validation/S2D.json'))['data']; fpc={(c['sector'],int(c['reference']),int(c['k'])):c['f'] for c in S2D['2x3']['per_circuit']}
for sec,twoB in (('B=0',0),('B=1',2)):
    r=M.reference(g2,twoB,k=4); p=np.zeros(M.basis.dim); p[r.indices]=np.abs(r.ground)**2; S=exact_support(p,1e-3)
    circ,P=[],[]
    for rr in references(M.basis,twoB):
        for k,st in enumerate(coarse_states(G,basis_vector(M.basis.dim,rr),r.dt,4)[1:],start=1): circ.append((sec,int(rr),k)); P.append((np.abs(st)**2)[S])
    P=np.array(P); nC=len(P); N=int(round(2e5/nC)); y=READOUT_FACTOR*np.array([fpc[c] for c in circ]); rate=(y[:,None]*P).sum(axis=0); lam=N*rate
    lp=linprog(np.ones(nC),A_ub=-(y[:,None]*P).T,b_ub=-lam3*np.ones(len(S)),bounds=[(0,None)]*nC,method='highs')
    print(sec,'support',len(S),'reach p>=1e-3',int((P.max(axis=0)>=1e-3).sum()),'quota: min lam %.2f'%lam.min(),'below lam*',int((lam<lam3).sum()),'below ln20',int((lam<lam1).sum()),
          'E[recall] %.4f'%np.mean(1-np.exp(-lam)),'P(all) %.3f'%np.prod(1-np.exp(-lam)),'p* %.4f'%(lam3/(y.mean()*N)),
          'uniform 3-hit N_sector',int(np.ceil(lam3/rate.min()))*nC,'1-hit',int(np.ceil(lam1/rate.min()))*nC,'LP',int(np.ceil(lp.fun)),'eq5 per circuit x nC',shot_rule(1e-3,y.mean())*nC)
EOF
```

A2. The D3'-type plan (floor + N₄ on the k = 4 circuits) and the Poisson-binomial recall risk (2 s):

```
python - <<'EOF'
import sys, json, numpy as np; sys.path.insert(0,'src')
from skqd.exact import Model, mass_default
from skqd.krylov import references, term_groups, coarse_states, basis_vector
from skqd.skqd import poisson_lambda_star, READOUT_FACTOR, exact_support
M=Model(3); g2=4.0; G=term_groups(M.terms,g2,mass_default(g2)); lam3=poisson_lambda_star(3,0.95); lam1=poisson_lambda_star(1,0.95)
S2D=json.load(open('validation/S2D.json'))['data']; fpc={(c['sector'],int(c['reference']),int(c['k'])):c['f'] for c in S2D['2x3']['per_circuit']}
def tail(q,kmin):
    d=np.zeros(len(q)+1); d[0]=1.0
    for qi in q: d[1:]=d[1:]*(1-qi)+d[:-1]*qi; d[0]*=(1-qi)
    return float(d[kmin:].sum())
for sec,twoB in (('B=0',0),('B=1',2)):
    r=M.reference(g2,twoB,k=4); p=np.zeros(M.basis.dim); p[r.indices]=np.abs(r.ground)**2; S=exact_support(p,1e-3)
    circ,P=[],[]
    for rr in references(M.basis,twoB):
        for k,st in enumerate(coarse_states(G,basis_vector(M.basis.dim,rr),r.dt,4)[1:],start=1): circ.append(k); P.append((np.abs(st)**2)[S])
    P=np.array(P); nC=len(P); k4=np.array([k==4 for k in circ]); floor=int(round(2e5/nC)); m90=int(np.floor(0.1*len(S)))+1
    for marg in (1.0,0.7):
        y=READOUT_FACTOR*marg*np.array([fpc[(sec,int(rr),k)] for rr in references(M.basis,twoB) for k in (1,2,3,4)]); rate=y[:,None]*P
        for lt,tag in ((lam3,'3hit'),(lam1,'1hit')):
            N4=int(np.ceil(max(float(np.max((lt-floor*rate.sum(axis=0))/rate[k4].sum(axis=0))),0)/100)*100)
            shots=np.where(k4,floor+N4,floor); lam=(shots[:,None]*rate).sum(axis=0); q=np.exp(-lam)
            print(sec,'margin',marg,tag,'N4',N4,'N_sector',int(shots.sum()),'min lam %.3f'%lam.min(),'E[recall] %.5f'%np.mean(1-q),'P(rec<0.9) %.1e'%tail(q,m90),'P(all) %.4f'%np.prod(1-q),'CPU-h %.0f'%(shots.sum()*S2D['per_shot_cost_2x3']['seconds_per_shot']/3600))
        lam=floor*rate.sum(axis=0); q=np.exp(-lam); print(sec,'margin',marg,'quota: E[recall] %.4f'%np.mean(1-q),'P(rec<0.9) %.1e'%tail(q,m90))
EOF
```

A3. Emulated |B|, recall, E_R − E₀, r_H and the gap assumption at f = 0.0534 for the quota and the D3'-type plans
(342 s for the quota + three-hit rows; the one-hit rows, 197 s, use `N4 = {'B=0': 13200, 'B=1': 81000}`):

```
python - <<'EOF'
import sys, json, numpy as np; sys.path.insert(0,'src'); sys.path.insert(0,'scripts')
from gate_S1 import P_RO; from skqd.noise import measure_and_decode; from skqd.codec import Codec
from skqd.exact import Model, mass_default; from skqd.krylov import basis_vector, coarse_states, references, term_groups
from skqd.skqd import certify, ritz, support_metrics
f=round(json.load(open('validation/S2D.json'))['data']['2x3']['f']['mean'],4)
M=Model(3); g2=4.0; H=M.H(g2); codec=Codec(M.basis); cw=codec.all_codewords(); G=term_groups(M.terms,g2,mass_default(g2))
N4={'B=0':44500,'B=1':202700}
for sec,twoB in (('B=0',0),('B=1',2)):
    r=M.reference(g2,twoB,k=4); refs=references(M.basis,twoB); p=np.zeros(M.basis.dim); p[r.indices]=np.abs(r.ground)**2
    sts=[(k,st) for rr in refs for k,st in enumerate(coarse_states(G,basis_vector(M.basis.dim,rr),r.dt,4)[1:],start=1)]
    floor=int(round(2e5/len(sts)))
    for name,extra in (('quota',0),("D3' 3-hit",N4[sec])):
        for seed in (20260914,1,2):
            rng=np.random.default_rng(seed); acc_all={}
            for k,st in sts:
                acc,_=measure_and_decode(codec,cw,st,floor+(extra if k==4 else 0),f,P_RO,rng,target_twoB=twoB)
                for kk,c in acc.items(): acc_all[kk]=acc_all.get(kk,0)+c
            B=np.array(sorted(set(acc_all)|set(refs))); res=ritz(H,B); met=support_metrics(B,p,1e-3); cert=certify(res,r.E0,float(r.energies[1]))
            print(sec,name,seed,'|B|',len(B),'recall %.3f'%met['recall'],'err %.1e'%(res.energies[0]-r.E0),'rH %.4f'%cert.rH,'gap',cert.gap_assumption_holds)
EOF
```
