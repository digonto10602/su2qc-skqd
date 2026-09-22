# H0 re-plan after the diagnostic — planner analysis and rulings (2026-09-22)

planner-fable, max effort, after gate H0_diag (`validation/H0_diag.json`, FAIL 6/8, C3 decisive) and
`validation/BLOCKED.md`.  **No QPU time was used for this analysis and none is authorised by it.**  Every number
below is read from a named JSON key or is a labelled planner computation (P7–P13, continuing P1–P6 of
`reports/H0_canary_planner_analysis_20260922.md`) whose reproduction snippet is in section 10; the snippets run on
the laptop in the `coding` environment (P9 takes 8 minutes, the others seconds) and touch no raw data.

## 0. Rulings in one place

1. **The cause is settled, the size is not.**  H_B (the SamplerV2 options) is rejected: J1 gave 35 accepted of
   2000 against 374.5 ± 17.4 under H_B (`H0_diag.json:data.decision`).  Idle-time decoherence is the cause.  But the
   accepted count is not the clean count: **the accepted shots of J1 are not clean shots** (P8).  The ideal output of
   the canary circuit is the reference string with probability 0.8833; if the 16.4 accepted shots above the
   garbage floor were clean, 15.0 of them would be the reference string, and 2 were (P = 3.9e-5).  13 of the 35
   accepted strings are codewords at Hamming distance 2 from the reference with ideal probability 0.000 — few-error
   strings that happen to decode.  Pooled over the five hardware jobs (8267 shots, all option sets) the reference
   string was seen 6 times against a garbage expectation of 2.02 (P = 0.017): the clean-shot fraction on patch 1
   is **f_clean ≈ 6.7e-4 (1σ 2.6e-4 – 1.1e-3)**, not the 0.0101 that inverting J1's accepted yield gives, and not
   the 0.0255 of the canary.  The preregistered H_A prediction (30.8 accepted) matched the accepted count for the
   wrong reason.
2. **The corrected model** (section 3): the clean-shot fraction of a circuit is predicted by the seeded Aer
   simulation of the **scheduled** circuit (idle windows as explicit `delay`s, which Aer's relaxation pass charges
   with the target's T1/T2), and the analytic PTA model `f_gates e^{-S_T1 - S_T2}` of `skqd.idle` is kept as the
   closed-form **bound** used for the shot plan, the patch score and the device-requirement algebra.  Which T2: the
   record's Hahn-echo T2 is the optimistic end (PTA: 11x above the pooled clean count; Aer on scheduled circuits
   is a further ~12x above the PTA on FakeFez, P9), the measured free-induction T2* the pessimistic end (PTA: 5.8x
   below).  The effective in-circuit budget on patch 1 is S_eff = 5.76 (1σ 5.28–6.71) against S_echo = 3.32 and
   S_T2* = 7.52 — 60 % of the way from the echo end to the T2* end.  **Decision: T2 is a measured input, not a
   record field** — every session measures T2* on its patch with the windowed Ramsey pub that already exists
   (0.6 s of execution), and the prediction is made at both ends; whether the T2* end of the Aer model reproduces
   the pooled clean count within a factor 3 is the first criterion of the new laptop gate `H0_model` (prompts/20).
   No number in this ruling is fitted: the two ends are computed from the record and from the H0_diag measurement.
3. **Patch selection becomes part of the preparation** (section 4).  The amendment-01 item-1 work committed at 76b4fd5
   (`scripts/h0_patch_select.py`) already does the right search: every embedding of the frozen
   circuit's 12-node interaction tree into the device coupling graph — the same circuit relabelled, no
   re-routing — scored by the PTA clean f at the record's echo T2, exhaustively and deterministically.  On the
   committed 30-qubit records its winner replaces qubit 146 (T2 16.0 us) by 140 (36.0 us) for 1.41x in f
   (1.069e-2 against 7.583e-3, `reports/H0_patch_select.md`); on the full FakeFez snapshot (1494 embeddings)
   the best patch gains 3.31x over the transpiler's (9.40e-3 against 2.84e-3), i.e. **S_idle(echo) ≈ 2.6 for the
   best embedding a Heron r2 snapshot offers this 51-us circuit** — patches with S_idle(echo) ≈ 1 do not exist
   for it.  Rule R1' (D1', owner): the full-device live record of the session day (free) is searched by that
   script, all circuits are re-frozen on the winning 12 qubits, and the selection table is committed with the
   fingerprint.  A free survey of ibm_fez, ibm_marrakesh and ibm_kingston through that search is part of
   prompts/20.
4. **The option set** (section 5): D8 (DD XY4 + gate and measurement twirling) is replaced by **D8' = DD off,
   twirling off** for every production job.  This is a correction of a choice made without evidence — the dry run
   that motivated D8 ignored the options — not a response to a bad result: on clean shots the factorial has no power
   (0–2 reference hits per cell), and the accepted-yield ranking it produced (J1 best) is the near-clean acceptance
   term, which twirling removes.  The decisive reason is that the prediction must be parameter-free: DD's
   refocusing efficiency and twirling's pulse cost are not computable from the calibration.  Client-side DD
   (multi-cycle, qubit-selective, runtime DD off) stays a lever to be tested in preregistered cells on the selected
   patch, with clean-yield statistics, never adopted from this diagnostic.
5. **The programme** (section 6): r = 1 only at 2x2 on this device class; r = 2, 3 are at the garbage floor at any
   budget (f ≈ f_r1²).  What H0 can still certify: decoder validity on real strings, the readout confusion, the
   existence and size of a clean component (reference-string test), and a measured clean f at 663 CZ on a chosen
   patch.  What it cannot: the yield-versus-CZ ladder of manual Step 9.1, and — as written — its criterion 2 on
   patch 1 (section 7).  Criterion 3 (E0 to 1e-6) is passed by garbage saturation at every budget the project has
   ever planned and is not a device test.  H1/H2 at 2x3 do not run on a superconducting device under any option;
   on the ion-trap route of amendment 01 they depend on a vendor spec that includes the in-circuit dephasing time
   (T2* under the vendor's own DD) and the two-qubit gate duration, which item 4 must now carry.
6. **Can H0 pass, and at what budget** (section 7): on patch 1, **no** — under D3' at f_clean = 6.7e-4 the r = 1
   shots alone are about 2.2e7 (about 6500 s of execution, eleven months of the allowance), and criterion 2 compares an
   accepted-yield inversion (biased 15x on J1) with a model that brackets over a factor 66.  On a T2-selected patch
   the D3' budget is 174 s at f_clean = 0.03, 116 s at 0.05, 73 s at 0.10 (P11); the month's remaining 583 s fit a
   plan down to f_clean ≈ 0.013 (374 s).  Whether such a patch exists on a reachable device is what the survey and
   the pilot of prompts/21 measure.  Criterion 2 becomes a fair test only with the clean-yield statistic (C2',
   owner) and a prediction whose T2 input is measured on the patch.  Because criterion 3 is void, H0's shots
   need only serve criterion 2: sizing the k = 1 circuits for σ_f/f ≈ 0.10 costs ≈ 140/f_clean shots each
   (D3''-H0, owner), 143 s at f_clean = 0.002 — inside the month even at the pessimistic expectation.

## 1. What the diagnostic established (facts; `validation/H0_diag.json`)

| item | value | key |
|---|---|---|
| J1 (DD off, twirling off) accepted of 2000 | **35**; H_A 30.85 ± 5.51, H_B 374.50 ± 17.45, floor 18.55 | `data.decision` |
| J2 (XY4, off) / J3 (off, on) / J4 (XY4, on) | 27 / 25 / 17 | `data.canary_pubs` |
| ratios | J2/J1 0.771, J3/J1 0.714, J4/J2 0.630 | `data.ratios` |
| mixture chi-square (rejection split, 2 dof) | J1 40.93, J2 14.29, J3 0.24, J4 1.00 | `data.canary_pubs.*.mixture` |
| C4a / C4b / C6 | 11 of 12; 12 of 12; 0.9625 | `criteria[3,4,7]` |
| C5 post-diction with measured T1/T2* | J1 88.585, J2 11.96 (factor 3) → FAIL | `criteria[5,6]` |
| usage | 5.0 + 4.0 + 3.0 + 3.0 = 15.0 s | `data.total_usage_s` |
| T2* (J1 ramw), fully dephased qubits | 123, 125, 141, 144, 145 (P(0) ≤ 0.5 at 43.52 us); 146: 19.4 us vs record 16.0 | `data.idle_tests.J1.ramw` |
| t1w under XY4 (J2) | survival of qubit 117 0.257 vs 0.759 without DD; 5 of 12 inside the band | `data.idle_tests.J2.t1w` |

| gate S2D_idle (`validation/S2D_idle.json`, amendment-01 items 1–3, commit 76b4fd5) | FAIL at both ends: live record, echo T2, mean f 6.71e-3 / worst 1.54e-3; T2* 1.30e-5 / 3.40e-7; most favourable point (rho = 0) 0.0623 < 0.1.  Its V5 "hardware anchor" (30.8 predicted vs 35 measured, factor 1.135) anchors on the accepted count and must be re-read on the clean count (section 2) | `reports/S2D_idle_device_budgets.md` |
| patch search (`data/H0_patch_select.json`, commit 76b4fd5) | 30-qubit live records: 10 embeddings, winner [117, 122, 123, 124, 125, 136, 140, 141, 142, 143, 144, 145], f 1.069e-2 vs 7.583e-3 (1.41x), the same winner on all 7 records; FakeFez full device: 1494 embeddings, winner f 9.40e-3 vs 2.84e-3 (3.31x), the transpiler's patch ranked 57 | `reports/H0_patch_select.md` |

**P7 (statistics of the accepted counts).**  Poisson errors on the factorial: J2/J1 = 0.77 ± 0.20 (1.2σ from 1),
J3/J1 = 0.71 ± 0.19 (1.5σ), J4/J2 = 0.63 ± 0.19 (1.9σ), J4/J1 = 0.49 ± 0.14 (3.6σ).  Above the garbage floor
18.55: J1 by 3.8σ (P = 4.2e-4), J2 2.0σ (0.039), J3 1.5σ (0.088), J4 −0.4σ.  Inverting J1's accepted yield with
`clean_fraction_from_yield` gives f = 0.01014 (1σ 0.0065–0.0138), i.e. an effective budget S = −ln(f/f_gates) =
3.03 (2.73–3.48) against the record's PTA 3.32 — the "1.13" agreement, and P(N1 ≥ 35 | 30.85) = 0.25.  At 2000
shots σ_f/f = 0.36, so the 30 % criterion cannot even be evaluated on one cell; 25 400 shots would be needed for
σ_f/f = 0.10 at that f.  All of this is about accepted shots; section 2 is why that is not enough.

## 2. The accepted shots are not the clean shots (P8)

The canary circuit `B0_ref06_k1_rep1` (reference 6, k = 1, dt = 0.24501) has the ideal output distribution
p(reference) = **0.8833**, four states at distance 3 with 0.027–0.028 each, and 0.001 or less elsewhere; over
Hamming distance to the reference codeword the ideal mass is [0.883, 0, 0.001, 0.109, 0, 0.001, 0.002, 0.001,
0.003] while the 38 codewords themselves are distributed [0.026, 0, 0.105, 0.105, 0.026, 0.211, 0.053, 0.211, 0.026]
(uniform garbage).  Decoding the raw counts of the five hardware pubs of this circuit:

| job (options) | N | accepted | floor N·a | excess | reference seen | expected if the excess were clean | P(≤ seen) | distance histogram of the accepted (d = 0..8) | log L(ideal mix) − log L(uniform) |
|---|---|---|---|---|---|---|---|---|---|
| canary (XY4, tw on) | 267 | 8 | 2.5 | 5.5 | 2 | 4.9 | 0.13 | 2, 0, 2, 3, 0, 0, 0, 0, 1 | +3.2 |
| J1 (off, off) | 2000 | 35 | 18.6 | 16.4 | 2 | 15.0 | **3.9e-5** | 2, 0, **13**, 5, 1, 6, 0, 5, 0 | −12.0 |
| J2 (XY4, off) | 2000 | 27 | 18.6 | 8.4 | 1 | 7.9 | 3.2e-3 | 1, 0, 9, 3, 0, 4, 1, 3, 1 | −6.0 |
| J3 (off, tw on) | 2000 | 25 | 18.6 | 6.4 | 1 | 6.2 | 0.015 | 1, 0, 4, 4, 2, 6, 1, 2, 0 | −3.6 |
| J4 (XY4, tw on) | 2000 | 17 | 18.6 | −1.6 | 0 | — | — | 0, 0, 1, 1, 3, 6, 1, 2, 0 | +1.4 |

The most frequent accepted states of J1 are basis indices 5 (5 shots), 10 (5), 55 (3), 12 (2): the first three
at distance 2 from the reference with ideal probability 0.000.  These are the reference codeword with one
*correlated* two-bit error that keeps the link consistency and the vertex flags — a flux flipped at both ends of a
link — and they are what the decoder accepts from a register with a few structured errors per shot.  With
twirling on (J3, J4) they nearly disappear (4 and 1 at distance 2) and the accepted count falls to the floor; the
rejection-split chi-square tells the same story (J1 40.9, J4 1.0: twirling turns structured few-error strings into
uniform garbage).  The factorial ranked the option sets by this near-clean term, not by clean shots.

**Pooled clean-shot evidence.**  Over the five pubs (8267 shots, all option sets): reference string 6 times,
garbage expectation N a / 38 = 2.02, P(≥ 6 | garbage) = 0.017 — there is a clean component, of 4.0 shots
(1σ 1.5–6.4).  Hence f_clean = (6 − 2.02) / (8267 × 0.82 × 0.8833) = **6.65e-4 (2.6e-4 – 1.07e-3)**, and the
effective per-shot error budget S_eff = −ln(f_clean / 0.21034) = **5.76 (5.28–6.71)**.  Per cell the reference
hits are 2, 2, 1, 1, 0 — the options make no measurable difference at this level.  Two consequences:

- The yield model of manual Step 4.4, y = 0.82 f + (1 − f) a, lacks a term: accepted strings that are neither
  clean nor uniform garbage.  It is not a hardware artefact — Aer has it too (P9: on FakeFez, unscheduled, 328
  accepted of 2000 of which 178 reference → clean ≈ 202, uniform garbage ≈ 15, near-clean ≈ 111, a third of the
  acceptances; scheduled, 73 accepted, 21 reference → clean ≈ 24, garbage ≈ 19, near-clean ≈ 31).  It hid inside
  H0P's [1/3, 3] ratio band and inside L4_fez's "Aer 1.3x above the model".
- Gate H0's criterion 2 inverts the accepted yield on both sides.  On the device the inversion overstates f_clean by
  15x (J1: 0.0101 vs ≈ 6.7e-4); on Aer by 1.4–2.3x.  The bias does not cancel between prediction and measurement,
  so the criterion as written does not measure what it names.  The clean-yield statistic must be one that weights
  the accepted strings by the ideal distribution (section 3.4).

For the record: C3 stands.  Under H_B the options were the cause and switching them off restores ≈ 374 accepted;
every cell is at or near the garbage floor with 0–2 clean shots, so the options neither caused the shortfall nor
cure it.  What changes is the reading of the "31 vs 35": it was not a validation of the echo-T2 idle model.

## 3. The corrected model

### 3.1 What the two implementations are, and what each omits

- **Analytic PTA** (`skqd.idle`, the prompts/19 model): f = f_gates e^{−S_T1 − S_T2}, per idle window
  p = (1 − e^{−w/T1})/4 + (1 − e^{−w/T2})/2 on the record's T1 and Hahn-echo T2, every error destroying the shot.
  Parameter-free; conservative in its bookkeeping (Z errors on qubits in a computational-basis state, and T1 on
  qubits in |0>, do nothing to the outcome, but are charged).  P10: 22.4 % of the canary circuit's S_T2 (0.576 of
  2.568 units) sits in windows before a qubit's first or after its last `sx`, where a Z error is provably invisible;
  qubit 146's 25.3-us trailing window alone is 0.397.  This is the exact part of the over-charging; the rest
  (errors inside the structured term blocks, where qubits wait in the X basis) is charged correctly.
- **Aer on a scheduled circuit** (P9, FakeFez, canary circuit, 2000 shots, seed 11): `transpile(qc, backend,
  optimization_level=0, scheduling_method="asap")` inserts 519 `delay`s and leaves the 663 CZ untouched;
  `AerSimulator.from_backend` then charges them through its relaxation pass.  Unscheduled: 328 accepted, f (by
  yield inversion) 0.1908 against the gate-only 0.1261 (1.51x — the visibility effect noted in the earlier
  analysis).  Scheduled: 73 accepted, 21 reference, f 0.0336 against the PTA 0.0028 (**11.8x**).  So on the same
  snapshot and the same T1/T2, Aer's idle penalty is e^{−1.74} where the PTA's is e^{−3.79}: the PTA is a bound, not
  a prediction, and the prediction of record must be Aer on the scheduled circuit.  The unscheduled Aer path of
  gate_H0P (the dry run's "H_B confirmed") is simply missing the delays; one flag fixes it.
- **Neither contains the near-clean acceptance in its analytic form**; Aer produces it by simulation.  The
  clean-yield estimator (3.4) is therefore applied to Aer's counts and to the device's counts alike.

### 3.2 Which T2

The record has no T2*.  The two ends and the measurement on patch 1, canary circuit, pooled 8267 shots (P8):

| model | f_clean | expected clean reference hits over 8267 shots | measured / predicted | S |
|---|---|---|---|---|
| PTA, record T1 and Hahn-echo T2 | 7.58e-3 | 45.4 | 0.09 | 3.32 |
| PTA, measured T1 and free-induction T2* (H0_diag post-diction inputs) | 1.14e-4 | 0.69 | 5.8 | 7.52 |
| **measured (pooled reference hits 6, garbage 2.02)** | **6.65e-4** | 4.0 (1.5–6.4) | 1 | **5.76 (5.28–6.71)** |
| Aer scheduled, record T2 / measured T2* on the live record 7fd6d65e | to be computed by gate `H0_model` (prompts/20 C3) | | | |

The measurement sits between the ends, 60 % of the way from echo to T2* in S.  No experiment in hand locates the
effective in-circuit dephasing more precisely, and no fit is made here.  Ruling: (i) T2* is measured on every
patch before it is used (the `ramw` pub, 85 x 512 ns, exists; a second window length, 21.76 us, is added so that
the decay shape — exponential vs Gaussian, which matters for the many short windows — is pinned; both pubs cost
1.2 s of execution inside the pilot job); (ii) the prediction of record is Aer on the scheduled circuits with the
target's `qubit_properties.t2` replaced per qubit by the measured T2* (rule: the measured value where P(0) is
resolved, else the 3σ upper bound, else the smallest resolved bound on the patch; every value written to the JSON
with its provenance), and the echo end is computed alongside as the bracket; (iii) whether the T2* end reproduces
the pooled clean count of patch 1 within a factor 3 is criterion C3 of gate `H0_model` — the post-diction the
project owes itself before the next submission; if both ends miss by more than a factor 3 the planner returns.
The in-flight `skqd.idle.effective_t2(per_qubit_ratio=...)` is the right interface for the analytic bound; the
same table feeds the Aer target.

### 3.3 Sensitivity, and why patch selection is a precondition for criterion 2 (P13)

Criterion 2 accepts |f_meas − f_pred| ≤ 0.30 f_pred, i.e. an error of at most ln(1.3) = 0.26 units in the model's
total budget S.  On patch 1 the ends of the bracket differ by 4.2 units and the measurement misses the parameter-
free end by 2.4; even the record-vs-measured T1 alone (S_T1 0.755 vs 0.942) is 0.19.  A 25 % uncertainty on the
idle budget keeps criterion 2 fair only if S_idle ≤ 1.05; on patch 1 S_idle(echo) = 3.32.  Every uncertainty in
the idle physics is multiplicative in S_idle, so the only way to make the 30 % test meaningful is to make S_idle
small: fewer, shorter windows on qubits with long T2 and T2*.  That is a patch (and device) property, which is why
patch selection precedes any H0 attempt, and why the pilot on the selected patch must measure f_clean directly.

### 3.4 The clean-yield statistic (C2', for the owner)

For a circuit c with ideal sector distribution p_c(s) and accepted counts n_s (N_acc accepted of N shots), fit
one parameter w by maximum likelihood in P(s | accepted) = w p_c(s) + (1 − w)/dim; then clean accepted = w N_acc,
ŷ_clean = w N_acc / N, f̂ = ŷ_clean / 0.82, with the profile-likelihood 68 % interval.  For k = 1 circuits
(p_max 0.883 / 0.889) the reference-string count is an independent check; for k = 4 (p_max 0.127 / 0.177, 35 of 38
and 20 of 20 states above 1e-3) the estimator relies on the whole distribution.  Applied identically to the Aer
prediction and to the hardware counts, and validated on Aer samples where the reference count gives the truth
(gate `H0_model` C1).  It replaces `clean_fraction_from_yield(y, a)` in criterion 2 **only** if the owner signs
C2'; prompts/20 builds it behind a flag with the old statistic as default.  The tolerance 0.30 is unchanged.

### 3.5 Where the term enters

| consumer | today | corrected |
|---|---|---|
| gate H0 criterion 2 prediction | Aer, unscheduled QPY, yield inversion | Aer, scheduled, T2* target, clean-yield estimator (C2') |
| D3' shot plan (`h0_support_plan.py`) | f_c = gate-only `analyse_on_backend` | f_c = the PTA bound at the measured T2* of the patch (conservative; the rule, margin 0.7, floor 267, λ* are unchanged) |
| patch score (rule R1) | none | PTA bound on the record's T2 (the only T2 known before the pilot) |
| gate S2D 2x2/Heron f, amendment 01 section 1(c) | gate-only product | withdrawn as a hardware statement (earlier analysis); the S_idle of `device_req.target_with_idle` is the effective budget — on patch 1 1.7x the echo-PTA value — and the T2* end is the conservative input for the 2x3 requirement sheet (item 4; not edited here) |
| manual Step 4.4 yield model | y = 0.82 f + (1 − f) a | plus the near-clean term; f in eq. (5) is f_clean (amendment line, owner) |
| QPU-time estimate (`h0_qpu_time.py`) | unchanged | unchanged |

## 4. Patch selection (rule R1', fixed before any live full-device record is read)

- **The search** is `scripts/h0_patch_select.py` (commit 76b4fd5): all injective embeddings of the frozen canary
  circuit's interaction tree (12 nodes, 11 edges, degree sequence [3, 3, 2 x 6, 1 x 4]) into the device coupling
  graph, each scored by the PTA clean f = f_gates e^{−S_T1 − S_T2} on the record's T1 and echo T2 (`skqd.idle`
  through `h0_idle_model.py`); ties by larger f_gates, smaller worst-qubit S_T2, then the smallest qubit tuple.
  Same circuit, different qubits: no second transpiler solution to argue about.  It needs a **full-device**
  record (the committed H0 records cover only the 30 frozen qubits — 10 embeddings — which is why its live
  gain is 1.41x while the FakeFez full-device gain is 3.31x); the survey of prompts/20 writes such records for
  the three reachable devices in the `calibration_record` format, from free target metadata.
- **The re-freeze** (D1'): every r = 1, 2, 3 circuit of both sectors is transpiled on the coupling map
  restricted to the winning 12 qubits with the winner's logical-to-physical map as `initial_layout`, so that one
  patch carries the whole set (14 readout-calibration circuits instead of 42: 14.1 s instead of 42.3 s).  The
  CZ count and the PTA f of every circuit on the shared patch are recorded next to the frozen set's values; a
  circuit that loses more than 2x against its own best embedding is reported (the owner then chooses between one
  patch and per-circuit patches).  Leak-free verification as in `h0_build_circuits.py`; new directory; `H0_prep`
  untouched; D9 unchanged, so a selection made on stale content is refused.
- **What the searches say about feasibility.**  Live 30-qubit record: the best embedding has S_T1 + S_T2 =
  0.770 + 2.182 = 2.95 (f 1.069e-2); FakeFez full device: S_idle(echo) = ln(0.1261/0.0094) ≈ 2.6 for the best
  of 1494 (P12's coarser view: 12-qubit trees with all T2 ≥ 80 us exist on that snapshot, all ≥ 100 us do not;
  T2 percentiles 22.6/48.1/88.0/122.9/158.0 us).  The circuit's 12 qubits each idle 19–42 us of its 44–51 us;
  with T2 ≈ 100–150 us on every qubit that is still ≈ 0.15–0.2 units per qubit, so S_idle(echo) ≈ 2–2.6 is the
  floor for this circuit on a Heron r2 — the lever is real (1.4–3.3x in f) but bounded.
- The score uses the echo T2 because T2* is unknown before the pilot; the pilot (prompts/21) measures T2* and
  f_clean on the winner.  On patch 1 the measured budget was 1.73x the echo-PTA value; whether that ratio
  transfers to a high-T2 patch is not known (T2* need not scale with T2).
- The rule, the objective, the tie-breaks and the re-freeze procedure are written here and in the script's
  docstring before any full-device live record is read; the survey's only freedom is the device the owner names.

## 5. The option set: D8 → D8'

D8 froze DD XY4 and gate + measurement twirling (`active-accum`) on the strength of a dry run in which the options
were inert (`data/hardware/H0_dryrun/session.json:sampler_options_effective` false).  The factorial measured the
accepted yield of each cell; on clean shots it measured 2, 1, 1, 0 reference hits, which is no measurement.  The
ranking J1 > J2 > J3 > J4 is the near-clean acceptance term, which twirling removes (section 2), so "DD's measured
benefit 0.77" and "twirling's 0.71 / 0.63" are not statements about clean shots.  What the diagnostic does say:
under XY4 at one sequence per 512-ns window the `t1w` survival of qubit 117 fell from 0.759 to 0.257 and 7 of 12
qubits left the T1 band, while the `ramw` coherence improved on 9 of 12 (`H0_diag.json:data.idle_tests.J2`): the
pulse cost is real and qubit-specific, the refocusing is real, and the net effect at the circuit's window lengths
is unmeasured.  Ruling: **D8' = DD off, twirling off** for every production job, because the prediction of record
must contain no quantity that cannot be computed from the calibration or measured on the patch — DD's rho and
twirling's pulse cost are neither.  This corrects a choice that was made without evidence; it is not a reaction
to J4 = 17.  DD (client-side, multi-cycle, on the long-window qubits only, `PadDynamicalDecoupling(...,
qubits=[...], insert_multiple_cycles=True)` with runtime DD off — the lever the earlier analysis named) and
twirling may be re-introduced only as preregistered cells on the selected patch with enough shots for the
clean-yield estimator, i.e. after the pilot has shown f_clean ≳ 0.01 there.

## 6. The programme

- **2x2, this device class.**  r = 1 only.  r = 2 and r = 3 circuits sit at the garbage floor on every patch of the
  frozen set (PTA on the record: f 4.3e-6 and 2.5e-8, `data/hardware/H0_diag_prep/idle_model_frozen_set_7fd6d65e.json`;
  with the measured S_eff they are lower still) and stay in the plan only as the informational floor test at their
  frozen 130 / 92 shots (2.2 s).  The manual's Step 9.1 axis "yield versus CZ count at N_CZ ≈ 250, 500, 750" does
  not survive: the routed coarse step is 663 CZ and the second point is the floor.
- **What H0 can certify**: decoder validity and the parity checks on real strings (0 round-trip mismatches over 68
  + 7 distinct accepted strings; random acceptance 0.928 % / 0.488 % exhaustive), the readout confusion (0.9738,
  0.9625 measured), the existence of a clean component and its size on a chosen patch (reference-string test), the
  near-clean acceptance structure (a method result: the decoder accepts few-error strings at 0.65 % in J1, comparable
  to the uniform 0.93 %), and a measured f_clean at 663 CZ.  With the clean statistic (C2') and a T2*-informed
  prediction, criterion 2 becomes a fair test on a patch with S_idle ≲ 1.
- **What H0 cannot certify**: criterion 3 as a device test — with N_sector a/dim ≥ 5 the sector saturates from
  garbage alone (every plan the project has made, including the original D3' plan at 43k shots: 10.5 garbage hits
  per state), so E_R = E_0 to 1e-6 is the decoder's exhaustive property, established by E2, not the device's.  A
  bit-order error would instead show as clean shots landing on non-reference strings; the reference-string test
  per k = 1 circuit is the proposed replacement (C3', owner).
- **H1/H2 at 2x3.**  The mechanism — dephasing at the free-induction rate over a nearly serial routed circuit —
  scales with duration x qubits.  On any superconducting device the 2x3 step (5477 routed CZ, `validation/S2.json`)
  has a duration of order 400 us on 20 qubits: not a candidate under any option, which the S2/S2D FAILs already
  said on cost.  On the ion-trap route the same term reads Σ_q [t_idle,q/(2 T1_q) + t_idle,q/(2 T2*_q)] with
  t_idle ≈ the circuit duration (serial two-qubit gates), so the vendor spec of amendment 01 item 4 must carry
  t_2q, t_1q and the in-circuit T2* under the vendor's DD; no number for it is computable in this repository.
  H1/H2 survive only as conditional on that spec.  Manual Step 9.2's premise (f ≳ 0.2 at ≤ 500 CZ) never held for
  these circuits on any device the project has a quote for; Step 9.3 (2x4) is out of reach; the Step 10 rows P1 and
  M1 (classical, simulation) are untouched.

## 7. Can gate H0 pass, and at what budget (P11)

Rule D3' as it stands (r = 2, 3 at 130/92, floor 267, margin 0.7, λ* = 6.2958, N4 to the next 100), with the
ideal per-state probabilities of the frozen family (layout-independent), the frozen circuits' durations, the 250-us
rep delay, and one patch (14 calibration circuits at 4000 shots):

| clean f of the r = 1 circuits | N4 (B=0 / B=1) | r = 1 shots (B=0 / B=1) | execution (s) | with ≈ 2 s x 6 jobs |
|---|---|---|---|---|
| gate-only 0.2103 (the 1400Z plan) | 6 900 / 16 700 | 38 505 / 35 002 | 38.0 | 50.0 |
| 0.10 | 14 800 / 35 500 | 78 005 / 72 602 | 60.8 | 72.8 |
| 0.05 | 29 900 / 71 200 | 153 505 / 144 002 | 104.2 | 116.2 |
| 0.03 | 50 000 / 118 900 | 254 005 / 239 402 | 162.1 | 174.1 |
| 0.02 | 75 100 / 178 400 | 379 505 / 358 402 | 234.3 | 246.3 |
| 0.0126 | 119 300 / 283 400 | 600 505 / 568 402 | 361.6 | 373.6 |
| PTA echo 0.0076 (patch 1 as frozen; 42 calibration circuits) | 199 000 / 471 900 | 999 005 / 945 402 | 618.9 | 630.9 |
| measured 6.7e-4 (patch 1) | scales as 1/f: ≈ 2.2e7 r = 1 shots | | ≈ 6500 | |

Answers.  (a) On patch 1: no — the plan does not fit a month at the echo-PTA f and is eleven times over the
remaining allowance at the measured f_clean; and criterion 2 would be a comparison of the wrong statistic with a
model that brackets over a factor 66.  (b) On a selected patch, under D3' as it stands: the plan fits the
remaining 583 s down to f_clean ≈ 0.013 (374 s).  But the exhaustive search puts the best S_idle(echo) a Heron r2
offers this circuit at ≈ 2.6 (2.95 on the live 30-qubit record); if patch 1's measured ratio S_eff/S_echo = 1.73
transfers, S_eff ≈ 4.5 and f_clean ≈ 2e-3 — a planner expectation, not a computed value — at which D3' needs
≈ 6.4e6 r = 1 shots (≈ 1900 s).  **Under D3' as it stands, H0 is unlikely to fit a month on any patch of this
device class**; only the pilot can say whether a high-T2 patch does better than that ratio.  (c) The way out
follows from section 6: criterion 3 is void, so the r = 1 shots need only serve criterion 2's clean-f statistic.
For the k = 1 circuits (p(ref) = 0.883 / 0.889) the reference-string estimator reaches σ_f/f ≈ 0.10 at about
100 clean reference hits, i.e. N ≈ 140/f_clean shots per circuit (garbage included: at f_clean = 0.002 and
69 000 shots, 100 clean hits over 16.9 garbage hits give σ = 10.8 %); the seven k = 1 circuits then cost
483 000 shots = 143 s at f_clean = 0.002, 196 000 = 58 s at 0.005, plus 14.1 s of calibration, 2.2 s of r = 2, 3
and 21 x 267 floor shots — inside the month at the pessimistic expectation.  That is a named change (D3''-H0,
owner): for gate H0 only; D3' stays the rule wherever the support matters (H1/H2).  (d) Criterion 2 passes only
with C2' and a T2*-informed prediction; criterion 3 passes trivially; criteria 1, 4, 5 pass on the evidence
already in hand.

## 8. Named changes for the owner (nothing below is applied by prompts/20; it is prepared behind flags)

| id | change | why |
|---|---|---|
| D8' | production sampler options: DD off, gate and measurement twirling off | the prediction must be parameter-free; D8 was chosen without evidence (section 5) |
| D1' | the circuit set is re-frozen on the session day on the patch chosen by rule R1 from the live record, into a new directory, with the selection table committed; `H0_prep` untouched; D9 unchanged | idle time is the dominant term and T2 is a per-qubit property (section 4) |
| D3'-f | rule D3' unchanged; its f_c input becomes the PTA bound at the patch's measured T2* | the plan must be sized on clean shots, and the gate-only f is 300x off on patch 1 |
| D3''-H0 | for gate H0 only: the r = 1 shots are sized for criterion 2's clean-f statistic — the k = 1 circuits at ≈ 140/f_clean shots (σ_f/f ≈ 0.10), the other r = 1 circuits at the floor 267, r = 2, 3 at 130/92, 14 calibration circuits at 4000 — not for clean saturation | criterion 3 is void at every budget (section 6); at 2x2 the D3' plan buys nothing but seconds |
| D5' | the canary becomes a pilot on the selected patch: `ramw` at two window lengths, `t1w`, the k = 1 and k = 4 B = 0 circuits at N_pilot shots, D8' options; go rule on the pilot's clean f and on the D3' budget at that f | the model needs T2* and f_clean measured on the patch before the main run is sized (section 3.2) |
| C2' | criterion 2's statistic: the clean-yield estimator of section 3.4 on both sides; prediction = Aer on scheduled circuits at the measured T2*; tolerance 0.30 unchanged | the accepted-yield inversion is biased 15x on the device (section 2) |
| C3' | add: for every k = 1 circuit the reference-string count exceeds its garbage expectation by ≥ 3σ (bit-order test); criterion 3 kept but labelled as not a device test | criterion 3 is passed by garbage saturation (section 6) |
| H0P-Y' | gate H0P's ratio criterion becomes a sandwich: PTA bound at the T2 used ≤ Aer-scheduled clean f ≤ Aer-unscheduled clean f | the PTA is a bound, not a prediction (section 3.1) |
| M4.4 | amendment line: the manual's yield model gains the near-clean acceptance term and eq. (5) uses f_clean | section 2 |
| item 4 | the 2x3 requirement sheet's S_idle uses the in-circuit T2* (vendor-measured, under the vendor's DD), not the echo T2 | section 6; for the amendment executors, not for prompts/20 |

Unchanged: the four prereg criteria's constants (F_TOLERANCE 0.30, RANDOM_ACCEPT_MAX 0.01, E0_TOL 1e-6, DIAG_MIN
0.9, RO_FACTOR 3, READOUT_FACTOR 0.82), λ* 6.2958, the D3' rule, D2 (4000 calibration shots), D4, D6 (caps),
D7, D9–D11, the decoder and every convention, the r = 2, 3 shots, prompts/07 clause (b) (in force).
`validation/H0_diag.json` and `validation/H0_canary.json` stay as they are; the corrected analysis of the same
counts is a new gate (`H0_model`), never an edit of a preregistered one.

## 9. What prompts/20 does, and what waits

prompts/20 (executor, laptop, no QPU): the clean-yield estimator and its tests; the scheduled Aer path and the
T2 override in gate_H0P behind flags; gate `H0_model` — the post-diction of the existing counts at both ends of the
bracket (its C3 decides whether the T2* end is the working model); the reference-string and mixture tables in
gate_H0 as information; the free three-device survey with full-device records for the in-flight patch search; regressions.  It does not
touch the in-flight amendment files (`src/skqd/idle.py`, `src/skqd/device_req.py`, `scripts/h0_idle_model.py`,
`scripts/h0_patch_select.py`, `scripts/gate_S2D.py`, `scripts/gate_S2D_idle.py`,
`scripts/s2_family_duration_compare.py`, `proposal/amendment_01_devices_and_budgets.md`, any `validation/*.json` of an
existing gate); rule R1' runs the
in-flight search script on the survey's full-device records and edits nothing of it.  prompts/21 (planner, after the owner's
decisions on section 8 and after `H0_model`): the pilot session on the selected patch (about 10 s of QPU), the
re-freeze, the prediction at both ends, and — only if the pilot's f_clean puts the D3' plan inside the cap — the
main H0 submission.

## 10. Reproduction snippets (laptop, `coding` environment; nothing here writes into data/ or validation/)

P7 — accepted-count statistics of the factorial (1 s):
```python
import json, math
from scipy.stats import binom, poisson
d = json.load(open('validation/H0_diag.json'))['data']; a = d['garbage_acceptance']; fg = d['postdiction']['J1']['f_gates']
im = json.load(open('data/hardware/H0_diag_prep/idle_model_a44b6ac02709b471.json'))['circuits']['B0_ref06_k1_rep1']
S1, S2 = im['budget']['S_T1'], im['budget']['S_T2']; N = 2000
for name, n in (('J1', 35), ('J2', 27), ('J3', 25), ('J4', 17)):
    y = n / N; f = (y - a) / (0.82 - a); s = math.sqrt(n) / N
    print(name, round(f, 5), round((y - s - a) / (0.82 - a), 5), round((y + s - a) / (0.82 - a), 5),
          'S_eff', round(-math.log(f / fg), 3) if f > 0 else None, 'floor sigma', round((n - N * a) / math.sqrt(N * a), 1),
          'P(>=n|floor)', poisson.sf(n - 1, N * a))
print('record S', S1 + S2, 'P(N1>=35|30.85)', binom.sf(34, N, d['decision']['prediction_H_A']['yield']))
for lab, (x, y) in {'J2/J1': (27, 35), 'J3/J1': (25, 35), 'J4/J2': (17, 27), 'J4/J1': (17, 35)}.items():
    r = x / y; print(lab, round(r, 2), '+-', round(r * math.sqrt(1 / x + 1 / y), 2))
# expected: J1 f 0.01014 [0.00649, 0.01379] S_eff 3.032; 3.8 sigma above the floor, P 4.2e-4; record S 3.323; P(N1>=35) 0.249;
# J2/J1 0.77 +- 0.20, J3/J1 0.71 +- 0.19, J4/J2 0.63 +- 0.19, J4/J1 0.49 +- 0.14
```

P8 — the accepted strings against the ideal distribution, and the pooled clean count (5 s):
```python
import json, sys, math, numpy as np
sys.path.insert(0, 'src')
from scipy.stats import poisson
from skqd.exact import Model; from skqd.codec import Codec, Reject
from skqd.krylov import apply_groups, basis_vector, term_groups; from skqd.reference_sim import qiskit_key_to_bits
M = Model(2); codec = Codec(M.basis); g2 = 4.0; man = json.load(open('data/hardware/H0_prep/circuits/B0_ref06_k1_rep1.json'))
ref = M.reference(g2, 0); idx = list(map(int, ref.indices)); dim = len(idx); pos = {b: i for i, b in enumerate(idx)}
psi = apply_groups(term_groups(M.terms, g2, 3 * g2 / 16), basis_vector(M.basis.dim, man['reference']), man['k'] * man['dt'])
p = (np.abs(psi) ** 2)[idx]; pref = p[pos[man['reference']]]; a = 38 / 4096
refbits = tuple(int(x) for x in codec.encode(M.basis.labels[man['reference']]))
dist = {b: sum(x != y for x, y in zip(codec.encode(M.basis.labels[b]), refbits)) for b in idx}
print('p(ref)', round(pref, 4), 'ideal by distance', np.round(np.bincount([dist[b] for b in idx], weights=p, minlength=13)[:9], 3))
tot_N = tot_R = 0
for job in ('H0_ibm_fez_canary', 'H0_diag_J1', 'H0_diag_J2', 'H0_diag_J3', 'H0_diag_J4'):
    counts = json.load(open(f'data/hardware/{job}/counts/B0_ref06_k1_rep1.json'))['counts']
    N = sum(counts.values()); obs = np.zeros(dim); dh = np.zeros(13)
    for key, n in counts.items():
        try: b, _ = codec.decode(qiskit_key_to_bits(key), target_twoB=0)
        except Reject: continue
        obs[pos[b]] += n; dh[dist[b]] += n
    acc = obs.sum(); ex = acc - N * a; r = obs[pos[man['reference']]]; exp_r = ex * pref + N * a / dim
    print(job, N, int(acc), round(ex, 1), 'ref', int(r), 'expected', round(exp_r, 1), 'P', poisson.cdf(r, exp_r), dh[:9].astype(int).tolist())
    tot_N += N; tot_R += r
g = tot_N * a / dim; clean = tot_R - g; fc = clean / (tot_N * 0.82 * pref)
print('pooled', tot_N, int(tot_R), 'garbage', round(g, 2), 'P(>=R)', round(poisson.sf(tot_R - 1, g), 3), 'f_clean %.2e' % fc, 'S_eff', round(-math.log(fc / 0.2103446469858183), 2))
# expected: p(ref) 0.8833; J1 35 accepted, excess 16.4, ref 2 vs 15.0 (P 3.9e-5), distances [2,0,13,5,1,6,0,5,0];
# pooled 8267 shots, 6 reference hits, garbage 2.02, P 0.017, f_clean 6.65e-04, S_eff 5.76
```

P9 — scheduling + Aer on FakeFez (about 8 min; seed 11, transpiler seed 7):
```python
import gzip, sys, math
sys.path.insert(0, 'src'); sys.path.insert(0, 'scripts')
from qiskit import qpy, transpile; from qiskit_aer import AerSimulator; from qiskit_ibm_runtime.fake_provider import FakeFez
from skqd.exact import Model; from skqd.codec import Codec, Reject; from skqd.reference_sim import qiskit_key_to_bits
from h0_backends import calibration_record, frozen_qubits_and_edges
with gzip.open('data/hardware/H0_prep/circuits/B0_ref06_k1_rep1.qpy.gz', 'rb') as fh: qc = qpy.load(fh)[0]
b = FakeFez(); rec = calibration_record(b, *frozen_qubits_and_edges('data/hardware/H0_prep'))
sched = transpile(qc, backend=b, optimization_level=0, scheduling_method='asap', seed_transpiler=7)
assert sched.count_ops()['cz'] == 663 and sched.count_ops()['delay'] == 519
M = Model(2); codec = Codec(M.basis); refbits = tuple(int(x) for x in codec.encode(M.basis.labels[6])); a = 38 / 4096
sim = AerSimulator.from_backend(b, seed_simulator=11)
for name, circ in (('unscheduled', qc), ('scheduled', sched)):
    res = sim.run(circ, shots=2000).result().get_counts(); acc = nref = 0
    for key, n in res.items():
        bits = qiskit_key_to_bits(key)
        try: codec.decode(bits, target_twoB=0)
        except Reject: continue
        acc += n; nref += n * (tuple(bits) == refbits)
    print(name, acc, nref, 'f by yield inversion', round((acc / 2000 - a) / (0.82 - a), 4))
# expected: unscheduled 328 178 0.1908; scheduled 73 21 0.0336.  PTA on the FakeFez record (P1 snippet): f_gates 0.1261,
# S_T1 0.901, S_T2 2.891, f 0.0028, T 50.99 us  ->  Aer-scheduled / PTA = 11.8
```

P10 — Z-transparent windows of the canary circuit: run the P1 snippet of the earlier analysis with each window
tagged by whether it ends before the qubit's first `sx` or starts after its last `sx`; sum (1 − e^{−w/T2})/2 over
the tagged windows.  Expected: 0.576 of S_T2 = 2.568 (22.4 %); qubit 146 0.397 (its last sx at 18.39 us, one
25.30-us trailing window); prediction with the tagged part removed 40.4 accepted of 2000.

P11 — the D3' budget as a function of f (6 min; `h0_support_plan.ideal_probabilities` over the 84 frozen QPY):
```python
import json, sys, numpy as np
sys.path.insert(0, 'src'); sys.path.insert(0, 'scripts')
from skqd.exact import Model; from skqd.skqd import poisson_lambda_star, READOUT_FACTOR
from gate_H0P import load_manifests; import h0_support_plan as sp
mans, _ = load_manifests('data/hardware/H0_prep'); P, _ = sp.ideal_probabilities('data/hardware/H0_prep', mans, Model(2), 4.0, crosscheck=False)
im = json.load(open('data/hardware/H0_diag_prep/idle_model_frozen_set_7fd6d65e.json'))['circuits']; ls = poisson_lambda_star(3, 0.95)
T = {c: im[c]['T_total_s'] for c in im}; f_idle = {c: im[c]['prediction']['dd_off']['f'] for c in im}
def budget(fb, cal_circuits=14):
    shots = {}; out = []
    for sec in ('B=0', 'B=1'):
        sm = [m for m in mans if m['sector'] == sec]; r1 = [m['id'] for m in sm if m['repetitions'] == 1]; k4 = [c for c in r1 if c.split('_')[2] == 'k4']
        n4 = sp.n4_of_sector({c: P[c] for c in r1}, fb, r1, k4, 267, ls, margin=0.7, readout_factor=READOUT_FACTOR, round_to=100); out.append(n4)
        for m in sm: shots[m['id']] = (n4 if m['id'] in k4 else 267) if m['repetitions'] == 1 else {2: 130, 3: 92}[m['repetitions']]
    ex = sum(shots[c] * (T[c] + 250e-6) for c in shots) + cal_circuits * 4000 * (1.66e-6 + 250e-6)
    return out, round(ex, 1)
print('frozen patches, PTA echo, 42 cal circuits', budget(f_idle, 42))
for fu in (0.2103, 0.10, 0.05, 0.03, 0.02, 0.0126, 0.0076):
    print(fu, budget({c: (fu if c.endswith('rep1') else f_idle[c]) for c in im}))
# expected: frozen [199000, 471900] 618.9 s; 0.2103 [6900, 16700] 38.0; 0.10 [14800, 35500] 60.8; 0.05 [29900, 71200] 104.2;
# 0.03 [50000, 118900] 162.1; 0.02 [75100, 178400] 234.3; 0.0126 [119300, 283400] 361.6; 0.0076 [198000, 470000] 588.1
```

P12 — FakeFez T2 regions (10 s; `FakeFez().target.qubit_properties`, `target['measure'][(q,)].error`,
`target['cz'][edge].error`, connected components by BFS over the coupling map with T2 ≥ T2_min and readout ≤ 0.03).
Expected: percentiles 22.6/48.1/88.0/122.9/158.0 us; largest components [41, 33, 19] at 40 us, [21, 11, 11, 11]
at 60, [17, 8, 7] at 80, [6, 5, 4] at 100, [5, 4, 4] at 120, [3, 3, 2] at 150; patch 1 induced subgraph 11 edges.

P13 — sensitivity (arithmetic): ln 1.3 = 0.262; S_echo − S_T2* on patch 1 = 7.52 − 3.32 = 4.20; S_eff − S_echo =
2.44; S_T1(measured) − S_T1(record) = 0.942 − 0.755 = 0.187; 0.262 / 0.25 = 1.05.
