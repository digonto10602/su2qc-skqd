# Planner ruling (2026-10-03): the 2x3 shot rule and the clean-fraction estimator

Planner: Fable 5.1 (high).  Prompt written: `prompts/28_2x3_shot_rule_and_clean_fraction_estimator.md`.
Commit of the inputs: a2e6060 (gate Q0P_2x3 PASS 7/7).  QPU seconds spent: 0.  HQC spent: 0.  No push.

Every number below is read from `validation/Q0P_2x3.json`, `data/quantinuum/q0p_stages/predict.json`,
`data/quantinuum/a6_phase_error_check.json`, `data/S2D_recall_at_f.json`, `validation/H0_2x2.json`,
`validation/H0_kpilot.json`, `validation/H0_ddtest.json`, `validation/H0_model.json`,
`data/quantinuum/devices_20261002.json`, or computed by the planner prototype
`scratch/planner/d3s_2x3_shot_rule_20261003.py` (output `scratch/planner/d3s_2x3_shot_rule_20261003.json`,
runtime 3 s per sector, inputs: the frozen circuits' sector distributions of `verify.json`, `Model(3)`,
$\lambda^*$, the HQC formula).  Prototype numbers are labelled **planner arithmetic** and must be reproduced by
gate Q0P_2x3_plan (prompts/28 Part B) before they are cited anywhere else.

## 1 What was asked

The owner sent the two problems of the Stage A run of prompts/26 to the planner (2026-10-03):

1. Rule D3' — every state of the sector must reach $\lambda^* = 6.2958$ expected clean counts from the $k = 4$
   circuits at $0.7 f$ — cannot size a 2x3 campaign ($N_4 \approx 8.8 \times 10^{35}$ at $f = 0.1$ in $B=0$;
   `validation/Q0P_2x3.json data.stage_A.predict.campaign`).  Rule on the 2x3 shot rule, derived from what the
   shots are for; state whether 2x2's D3' (run in H0_2x2) is consistent with it; give the shot and HQC table at
   $f \in \{0.05, 0.10, 0.15\}$.
2. The reference-string clean-fraction estimator overstates $f$ even in a pure gate-noise model: A6 gave
   $f = 0.2502$ [0.1927, 0.3195] (95 %) against 0.1502 (gate-only model) / 0.1722 (Aer channel), 64 hits
   against 44.06 expected from fault-free shots ($P = 0.0028$).  Diagnose (near-clean term or bug), specify a
   decisive offline test, rule on the correct statistic, state the consequences for the 2x2 records, fix the
   Stage E GO rule, and give the effect on the H2-2 sizing.

## 2 Problem 1 — the 2x3 shot rule

### 2.1 What the shots are for

Jargon: the *support* $B$ is the set of decoded bit strings (gauge-invariant configurations) the quantum device
returns; SKQD diagonalises the Hamiltonian in the span of $B$ (manual Step 5).  The *exact support*
$S_\varepsilon$ is the smallest set of configurations carrying $1 - \varepsilon$ of the exact ground state's weight
(manual 5.4); *recall* $R_\varepsilon = |B \cap S_\varepsilon| / |S_\varepsilon|$.  The preregistered targets that
the shots serve are: gate S1, recall of $S_{10^{-3}}$ $\ge 0.9$ at $f \ge 0.1$; gate H1, a certified interval of
width $\le 0.1$ containing $E_0$ and recall $\ge 0.8$; gate H2, the $B = 1$ cluster energy certified to
$\pm r_H \le 0.15$; P1, the curves $E_R - E_0$ and $R_{10^{-3}}$ versus $|B|$ (manual Steps 6.3, 10).  No
criterion asks for every state of the 677- or 426-state sector.  The variational bound (manual 5.2) means extra
strings never hurt; the only thing shots must buy is that the states carrying the ground-state weight are in
$B$.

Sizes (planner prototype, `Model(3).reference(4.0, twoB)`): $B=0$: $|S_{99}| = 31$, $|S_{999}| = 86$ of 677;
$B=1$: $|S_{99}| = 42$, $|S_{999}| = 95$ of 426 (the manual's 86 and 95, Step 4.2).

### 2.2 Why D3' diverges and what the frozen circuits reach

D3' asks for every sector state; 32 states of $B=0$ and 11 of $B=1$ have total $k = 4$ probability below
$10^{-6}$ (smallest $1.2 \times 10^{-34}$ / $1.6 \times 10^{-9}$; `predict.json campaign.*.k4_reachability`).
None of them is in $S_{999}$: restricted to $S_{999}$ the frozen circuits reach every state —
minimum over $S_{999}$ of $\sum_{c} p_c(s)$ is $5.89 \times 10^{-3}$ ($B=0$) / $1.10 \times 10^{-3}$ ($B=1$), of
$\sum_{k=4} p_c(s)$ $2.41 \times 10^{-3}$ / $6.20 \times 10^{-4}$, of $\max_c p_c(s)$ $1.64 \times 10^{-3}$ /
$6.19 \times 10^{-4}$ (planner arithmetic; the manual's "86 of 86 and 94 of 95 above $10^{-3}$").  The
unreachable states are unreachable *because* they carry no ground-state weight at $k \le 4$: D3' was
measuring the wrong set, not the wrong constant.

### 2.3 The candidate rules, with the same guarantee numbers (planner arithmetic, $y = 0.82 \times 0.7 \times f$)

"Recall floor" = expected recall of $S_{999}$ from clean shots alone, $\frac{1}{|S_{999}|}\sum_s (1 - e^{-\lambda_s})$;
$P(R \ge 0.9)$ = the exact Poisson-binomial probability that the clean shots alone recall $\ge 0.9$ of $S_{999}$
(78 of 86, 86 of 95 states); "below $\lambda^*$" = $S_{999}$ states with expected clean count $< \lambda^*$.
HQC = $\sum_{\rm jobs} [5 + C\,(N_{1q} + 10 N_{2q} + 5 N_m)/5000]$ with jobs of $\le 10{,}000$ shots
(`devices_20261002.json billing`; 4.9666 HQC per shot at the mean counts).

| rule | f | B=0 shots | B=1 shots | total HQC | recall floor B=0 / B=1 | P(R >= 0.9) B=0 / B=1 | below λ* B=0 / B=1 |
|---|---|---|---|---|---|---|---|
| D3'-S: λ* on every S999 state, LP allocation | 0.05 | 375,000 | 735,000 | 5,516,281 | 0.9999 / 0.9999 | 1.000 / 1.000 | 0 / 0 |
| D3'-S | 0.10 | 190,300 | 368,700 | 2,778,106 | 0.9999 / 0.9999 | 1.000 / 1.000 | 0 / 0 |
| D3'-S | 0.15 | 128,600 | 246,500 | 1,864,217 | 0.9999 / 0.9999 | 1.000 / 1.000 | 0 / 0 |
| D3'-S, k=4-scaled allocation (as D3') | 0.10 | 368,008 | 532,503 | 4,475,236 | 1.0000 / 1.0000 | — | 0 / 0 |
| λ* on S99 only (LP) | 0.10 | 27,000 | 49,500 | 380,341 | 0.8691 / 0.9500 | 0.156 / 0.993 | 48 / 34 |
| D3-type union (the Stage A record) | 0.05 | 204,320 | 203,100 | 2,023,192 | 0.9849 / 0.9282 | 1.000 / 0.895 | 23 / 38 |
| D3-type union | 0.10 | 102,208 | 101,604 | 1,012,182 | 0.9849 / 0.9282 | 1.000 / 0.895 | 23 / 38 |
| D3-type union | 0.15 | 68,128 | 67,704 | 674,650 | 0.9849 / 0.9282 | 1.000 / 0.895 | 23 / 38 |
| **D3'-R (ruling)** | 0.05 | 63,875 | 96,503 | 797,157 | 0.9402 / 0.9501 | 0.953 / 0.993 | 45 / 34 |
| **D3'-R** | 0.10 | 34,909 | 49,203 | 418,166 | 0.9418 / 0.9500 | 0.960 / 0.993 | 45 / 34 |
| **D3'-R** | 0.15 | 27,309 | 33,503 | 302,382 | 0.9427 / 0.9502 | 0.965 / 0.994 | 47 / 34 |

Readings.  (i) The D3-type union reading ($N = \lambda^*/(10^{-3} y)$, gate S1's rule scaled by $1/(0.7f)$) is
not what it claims: its guarantee is written for a state of pooled probability $10^{-3}$, but the rarest
$S_{999}$ states have pooled probability $5.9 \times 10^{-3}/32 = 1.8 \times 10^{-4}$ ($B=0$) and
$1.1 \times 10^{-3}/12 = 9 \times 10^{-5}$ ($B=1$) under its even spread, so 23 / 38 of them sit below $\lambda^*$
and in $B=1$ the clean-only probability of reaching recall 0.9 is 0.895.  It passed the S2D emulation
(`data/S2D_recall_at_f.json`: min recall 0.958 at $f = 0.0534$ with $2 \times 10^5$ shots) because garbage and
near-clean acceptances add states that the clean-only floor does not count.  (ii) λ* on $S_{99}$ alone is too
weak in $B=0$ ($P(R \ge 0.9) = 0.16$).  (iii) D3'-S buys $P(\text{all 86 / 95 seen}) \approx 0.99$, which no
criterion asks for, at 2.78e6 HQC.

### 2.4 The ruling: rule D3'-R

**Rule D3'-R** (the planner's label; "R" for recall).  For each sector, with the clean yield per shot
$y = 0.82 \times 0.7 \times f$ (readout factor, margin and $f$ exactly as in D3'):

(a) every state of $S_{99}$ receives an expected clean count $\ge \lambda^* = 6.2958$ from the sector's circuits
    (manual eq. 5 — three observations with 95 % probability — applied to each state's *actual* circuit
    probabilities $p_c(s)$, summed over circuits), the allocation being the linear programme of minimum total
    shots with every circuit at $\ge 267$ shots (the floor of D3');

(b) the $k = 4$ circuits are then topped up, in multiples of 100, until the probability that the clean shots
    alone recall $\ge 0.9$ of $S_{999}$ is $\ge 0.95$ (exact Poisson-binomial over the $S_{999}$ states).

Constants and their justification: $\lambda^*$, 0.82, 0.7, 267, 100 are the signed D3' constants, unchanged;
$S_{99}$ for (a) because those 31 / 42 states carry 99 % of the ground-state weight and are what the certified
energy (H1 width, H2 $r_H$) depends on; $0.9$ in (b) is S1's recall criterion (the stricter of S1's 0.9 and H1's
0.8); $0.95$ is the confidence level the manual uses in eq. (5).  The LP is the cheapest allocation with the
same guarantee; it concentrates shots on the $k = 4$ circuits that produce the rare states (at $f = 0.10$:
`B0_ref25_k4` 17,600, `B1_ref57_k4` 20,600, `B1_ref27_k4` 14,800, `B1_ref29_k4` 11,400; 33 of 44 circuits at
the floor), which is what D3' did at 2x2 by hand.  The guarantee is stated on clean shots only, so garbage and
near-clean acceptances are a margin, not an input.  The 0.82 factor is a conservative double count on
Quantinuum (its $f_0$ already contains the readout survival, `reports/Q0P_2x3.md` A6 note); it is kept because
2x2 was sized with it.

The plan of record at the three $f$ (planner arithmetic; USD at the Azure-Standard-equivalent ESTIMATE
12.5 USD/HQC, machine hours at the mid memory scenario 2.1175 s/shot):

| f | B=0 shots | B=0 HQC | B=1 shots | B=1 HQC | total shots | jobs | total HQC | USD (ESTIMATE) | machine h (ESTIMATE) | P(R >= 0.9) B=0 / B=1 | λ_min on S99 B=0 / B=1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | 63,875 | 317,546 | 96,503 | 479,612 | 160,378 | 55 | 797,157 | 9.96e6 | 94.3 | 0.953 / 0.993 | 7.25 / 6.31 |
| 0.10 | 34,909 | 173,614 | 49,203 | 244,553 | 84,112 | 49 | 418,166 | 5.23e6 | 49.5 | 0.960 / 0.993 | 7.34 / 6.30 |
| 0.15 | 27,309 | 135,860 | 33,503 | 166,522 | 60,812 | 46 | 302,382 | 3.78e6 | 35.8 | 0.965 / 0.994 | 7.74 / 6.32 |

The two readout-calibration circuits (no two-qubit gates) are added by the gate at 1,000 shots each (about
45 HQC each by the formula).  The floor circuits cost about 1,331 HQC each (planner arithmetic:
$5 + 267 \times 4.9666$), i.e. about 44,000 HQC for the 33 floor circuits — 10 % of the campaign at $f = 0.10$.

### 2.5 Is 2x2 consistent?

Yes; 2x2 stays as recorded.  At 2x2 the exact supports are small ($|S_{999}| = 16$ of 38 in $B=0$, 13 of 20 in
$B=1$; `validation/H0_2x2.json data.support.*.recall_B_all.exact_support_size`) and D3' asked for every state,
so the recorded plan ($N_4$ = 13,100 / 31,400) over-delivers on both conditions of D3'-R: the minimum expected
clean count over $S_{999}$ at the margin $f$ is 30.15 ($B=0$) / 32.76 ($B=1$) against $\lambda^* = 6.30$
(`data.support.*.per_state.lambda_s_margin`, planner reading), and every $S_{999}$ state was observed at least
59 / 80 times (`per_state.n_s`).  Nothing in the H0_2x2 record depends on which rule names the plan.  Part B2
makes this a unit test (`d3r_plan` at 2x2 returns sector totals $\le$ the recorded ones).

## 3 Problem 2 — the clean-fraction estimator

### 3.1 Diagnosis

The estimator counts every shot that ends on the reference string.  A fault-free shot ends there with
probability $p_{\rm ref} = 0.915$ (B0_ref25_k1).  A faulty shot ends there too whenever its errors do not change
the measured string: on these circuits the state is, for most of the circuit, within a few per cent of a
computational basis state (the reference), and a $Z$-type Pauli error on a qubit that is in $|0\rangle$ or
$|1\rangle$ at that moment is a phase, not a flip.  Aer's depolarizing channel makes 3 of its 15 two-qubit Paulis
and 1 of its 3 one-qubit Paulis $Z$-type, so a fraction of the faulty shots is "near-clean" in exactly the sense
of decision M4.4 (`data/H0_replan_owner_decisions.md`).  The evidence that this, and not a bug, is what A6 saw:

- 64 hits against 44.06 fault-free, i.e. an excess of 19.9 hits from $280 \times (1 - 0.1722) = 231.8$ faulty
  shots: 8.6 % of faulty shots end on the reference (planner arithmetic from `predict.json dryrun`);
- the phase-only control (`a6_phase_error_check.json`): a $Z$-type-only channel at the same event rate gave 11
  hits in 40 shots against 6.39 if only fault-free shots hit and 36.6 if every phase error were harmless —
  about 15 % of the $Z$-only faulty shots return to the reference ((11 − 6.39)/(36.6 − 6.39) = 0.153, planner
  arithmetic, wide interval at 40 shots).  Most $Z$ errors are *not* harmless because the compiler's PhasedX
  frames put the state in a rotated basis during many ZZPhase gates, where a native-frame $Z$ is a flip in the
  computational frame;
- the same mechanism was measured on ibm_fez (prompts/20: accepted shots mostly near-clean) and in the 2x2 Aer
  samples (`validation/H0_model.json` C1: near-clean 105.5 of 2000 unscheduled, 30.7 scheduled).

Two readings are therefore consistent with the data and one is not: (physics) the excess is the $Z$-type
near-clean term; (bug) the Aer path applies fewer error events than the model counts — for example if a
transpile step merged consecutive `rzz` on the same pair, every merged pair would remove one error event and
raise $f_0'$ without any near-clean physics.  The dry-run's `accepted` counts cannot separate these.  The
*mixture* estimator does not help: at $k = 1$ the reference carries 91 % of the shape, so it gives 0.351 / 0.305
(readout factor 0.82) on the same data (`predict.json dryrun.clean_statistics_project_path.per_circuit`) —
both estimators measure the same thing at $k = 1$.

### 3.2 The decisive test (prompts/28 Part A, gate CF_traj)

A Pauli-trajectory decomposition of the same channel on the same frozen circuit: the fault-free fraction
$f_0'$ is known analytically (0.17209 / 0.17236), so only faulty trajectories are simulated; each trajectory's
exact output distribution is computed once (one 20-qubit statevector, about 31 s per core by the `verify.json`
timing), giving $p_\tau(\mathrm{ref})$ and $p_\tau(s)$ for every target state without sampling noise.  With
$K = 720$ trajectories on B0_ref25_k1 the predicted hit fraction is known to about $\pm 0.02$ (95 %).  The
test is decisive because it has two independent arms: (i) the trajectory prediction must reproduce the 64 hits
(two-sided Poisson $P \ge 0.05$); (ii) a *counting control* on the Aer path — the same event probabilities with
bit-flipping Paulis only ($XX$, $X$) — must give the fault-free count (about 44 ± 6.6 of 280), because a bit flip
cannot hide.  If the control gives about 64 again, the Aer path applies fewer events than modelled and it is
a bug.  The same run yields what the rule needs: the per-state effective rates $f_{\rm eff}(s)$ on $S_{99}$ /
$S_{999}$, the benign fraction $b$ (trajectories whose output distribution is the ideal one), and the ratios
$\rho_{\rm ref} = f_{\rm hit}/f_0'$, $\rho_T = f_T/f_0'$.  Cost: about 3 h of laptop wall time in five background
chunks of $\le 25$ min (6 workers), 0 HQC; Perlmutter is not available for it (the CI allowlist has no such
token and only the owner can add one).

### 3.3 The correct statistic

Three quantities, which the records so far have called by one name:

- $f_0$, the **fault-free fraction**: the manual's $f \simeq (1 - \epsilon)^{N}$ (Step 4.4), what every device
  prediction in this repository computes (`device_req.clean_shot_fraction`, the device table, the H2-2 rows).
- $f_{\rm eff}(s)$, the **per-state effective rate**: expected count of state $s$ minus garbage, over
  $N p_c(s)$.  This is what a shot rule actually uses — the expected clean count of state $s$ is
  $N\,f_{\rm eff}(s)\,p_c(s)$.  Because every faulty shot contributes a non-negative amount,
  $f_{\rm eff}(s) \ge f_0$ for every state: $f_0$ is a guaranteed floor.
- $f_{\rm hit} = f_{\rm eff}(\mathrm{ref})$, the **reference-hit fraction**: what `reference_string_test`
  measures.  The reference is the attractor of the near-clean mechanism, so $f_{\rm hit}$ is the *top* of the
  range, not a floor, and it is not the rate at which the rare states are sampled.

Ruling.  (1) The budget criterion $f \ge 0.1$ (mean) / $0.05$ (worst) **means $f_0$** — the manual's definition,
the quantity the predictions compute, and a floor for every state.  (2) The campaign is **sized** on the
per-state effective rates; since they cannot be measured state by state on a device, the device-side statistic
is the **tail-class fraction** $f_T$: the reference-string construction applied to the class
$T_c = \{s : p_c(s) \ge 10^{-3},\ s \ne \mathrm{ref}\}$ — exactly the probability class the rule is written for
($10^{-3}$ is the support threshold of manual 5.4) — with the garbage expectation $N a |T_c|/\mathrm{dim}$
subtracted and a Garwood interval on the pooled tail count.  $f_T$ is an average of $f_{\rm eff}(s)$ over the
target class, so it satisfies $f_0 \le f_T \le f_{\rm hit}$ in expectation; the trajectory test measures
$\rho_T = f_T/f_0$ and the spread of $f_{\rm eff}(s)/f_T$ over $S_{99}$ under the Aer model, and the rule's 0.7
margin must cover that spread (a STOP is set at $\rho_T > 1.5$).  (3) The reference count is kept for what it
was introduced for — the C3' bit-order test ($\ge 3\sigma$ per $k = 1$ circuit) — and the ratio
$\rho_{\rm hit} = f_{\rm hit}/f_T$ is reported as the near-clean index, with CF_traj's Aer value beside it.  (4)
$f_T$ needs tail counts: at $k = 1$ the tail carries 8.2 / 8.5 % of the output, at $k = 4$ 71.9 / 75.5 %
(planner prototype `tails`), so the Stage E / P plans move shots to the $k = 4$ circuits (section 3.5).

### 3.4 Consequences for the 2x2 records (nothing rewritten; an information block, prompts/28 B4)

- Every recorded $f$ at 2x2 is $f_{\rm hit}$: `H0_kpilot` $f_{\rm pool}$ 0.0413 [0.0361, 0.0470]; `H0_ddtest`
  T0 0.0400 [0.0358, 0.0446], T2 0.1118 [0.1048, 0.1192], T3 0.1129 [0.1058, 0.1203] (the adopted cell, $R$ = 2.82
  [2.50, 3.19]; `validation/H0_ddtest.json data.decision.cells`);
  `H0_2x2` pooled 0.1271 [0.1084, 0.1479].  The near-clean factor on ibm_kingston is not measured; on IBM
  hardware the dominant error is idle dephasing — $Z$-type, the very mechanism — so the factor could be larger
  than Aer's gate-noise value.
- **Verdicts that do not change**: H0_kpilot NO-GO (strengthened: $f_0 \le f_{\rm hit} = 0.041$); H0_ddtest's
  adoption of T3 ($R = X_i/X_0$ is a ratio of hit statistics; both cells carry the same construction) — with the
  information that DD changes the error composition, so $R$ is not exactly a ratio of $f_0$ values; H0_2x2
  criteria R1-R8 (R5 compares the same statistic on both sides; the D3' reproduction is a consistency check;
  the energies are $f$-independent — the sectors saturate, $E_R = E_0$ at $|B| = 38$ / 20; recall 1.0 from the
  observed per-state counts); H0_model (C1 compares the mixture estimator with the reference count — a
  consistency of two $f_{\rm hit}$ estimators, which is what it says; C2-C4 are on hit counts).
- **Statement that is qualified**: the "signed bar GO" fields of H0_ddtest and H0_2x2 ($f_{\rm pool,lo95}
  \ge 0.1$) are GO on $f_{\rm hit}$; the bar on $f_0$ at 2x2 is not established.  The optional CF_traj arm A5
  (the T3 circuit under a Pauli-twirled idle model) gives the only model estimate of the 2x2 factor.
- The 2x2 plan was sized at $f_{\rm hit} = 0.1129$; the per-state counts settle it (section 2.5).

### 3.5 The Stage E GO rule of prompts/26, fixed before any emulator run

Old (prompts/26 E4 / `GO_RULE`): GO iff the 95 % lower bound of the pooled reference-string $f_E \ge 0.05$ and the
point estimate $\ge 0.10$.  With $\rho_{\rm ref} \approx 1.45$ (A6: 0.2502 / 0.1722) that rule would pass a device
with $f_0 \approx 0.07$.  New (prompts/28 B3, preregistration v2):

- statistic: $f_T$ pooled over the stage's circuits (`pooled_tail_class_test`, Garwood 95 %);
- **GO iff $f_{T,\rm lo95} \ge 0.05$ and $f_T \ge 0.10$; NO-GO iff $f_{T,\rm hi95} < 0.10$; AMBIGUOUS otherwise**
  (one top-up by Poisson scaling as in H0_kpilot); the bars 0.1 / 0.05 unchanged;
- C3' kept per $k = 1$ circuit; $\rho_{\rm hit}$ reported as information;
- Stage E v2: `B0_ref25_k1` 600, `B1_ref57_k1` 600, `B0_ref25_k4` 400, `B1_ref57_k4` 400 on H2-2E (planner
  arithmetic: 2,000 shots, about 9,950 eHQC against 11,940 for v1; expected tail hits 69 at $f_0 = 0.10$, 104 at
  0.15, versus 46 / 69 under the v1 split — Garwood 95 % on 69 counts is [0.78, 1.27] of the point, enough for
  the three-way rule);
- Stage P v2: the same four circuits at 500 shots each on H2-2 (about 9,950 HQC, as the v1 pilot).

### 3.6 Effect on the H2-2 sizing and on the campaign

- The campaign rule changes from the D3-type union (1.01e6 HQC at $f = 0.10$; prompts/26's "about 5e5 HQC" was
  this rule at $f = 0.14$) to D3'-R: 418,166 HQC at $f = 0.10$, 302,382 at $f = 0.15$, 797,157 at $f = 0.05$
  (planner arithmetic, table 2.4), with a stronger clean-only guarantee than the D3-type in $B=1$.
- The sizing input becomes $f_T$ of Stage P (point estimate), the plan at $0.7 f_T$; a preregistered
  mid-campaign check on $S_{99}$ (observed/expected $< 0.7$ → one re-sizing of the second half) protects
  against a device near-clean spread larger than Aer's.
- Pilot and Stage E costs are unchanged in size (about 9,950 HQC / eHQC each) but change in composition.
- At the H2-2 gate-only $f_0 = 0.150$ (mid memory 0.140; `validation/Q0P_2x3.json data.stage_A.predict.devices`)
  the campaign is 60,812-84,112 shots, 36-50 machine hours at the mid scenario, 3.0e5-4.2e5 HQC.

## 4 What the executor must run (prompts/28)

Part A (gate CF_traj): the trajectory engine and three arms (720 / 240 / 240 trajectories), the bit-flip
counting control (280 Aer shots), the A6-path audit, the optional 2x2 PTA arm — about 3 h of laptop wall time
in background chunks, 0 HQC.  Part B (gate Q0P_2x3_plan + information block): the tail-class statistic with
tests, `d3r_plan` reproducing the prototype to the shot, the plan gate with the emulated recall check, the
preregistration v2, the 2x2 information file; about one executor day.

## 5 Problems and assumptions

- The planner prototype rounds the floor circuits to 300 inside its LP and to 267 in the D3'-R block; the gate
  uses 267 everywhere.  Totals above are the D3'-R block's (267).
- D3'-R's guarantee uses the *ideal* per-circuit distributions and the floor $f_0 \le f_{\rm eff}(s)$ only
  through the margin: the trajectory test quantifies the spread of $f_{\rm eff}(s)$ under Aer's gate model; the
  device's spread (memory errors are dephasing, $Z$-type) is unknown until Stage P, hence the mid-campaign check.
- The 0.82 readout factor double-counts the readout survival on Quantinuum (conservative, kept for consistency
  with 2x2); removing it would lower every shot count by 18 % and is the owner's call, not the executor's.
- The HQC/USD figures assume the published formula and the Azure-Standard-equivalent rate (ESTIMATE); the
  machine hours assume the mid memory scenario of the device table (ESTIMATE).
- A small defect in `gate_Q0P_2x3.analyse_dryrun`: the timing-pilot loop reuses the name `a`, so
  `predict.json dryrun.garbage_acceptance` holds a pilot record; the computed rows used the right value
  (0.00146).  Fixed in Part B1; the Q0P_2x3 verdict is unaffected.
