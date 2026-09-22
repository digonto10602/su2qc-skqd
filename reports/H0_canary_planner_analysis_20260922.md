# H0 canary NO-GO — planner analysis and ruling (2026-09-22)

planner-fable, max effort, after `validation/BLOCKED.md` (prompts/17 B''6).  No QPU time was used for this
analysis.  Every number is read from a named JSON key or is a labelled planner computation (P1–P6) whose
reproduction snippet is in section 9; the snippets run on the laptop in seconds and touch no raw data.

## 0. Rulings in one place

1. **prompts/07 clause (b) fires as written on its trigger** (measured f / predicted f = 0.116 < 0.7,
   `validation/H0_canary.json:data.f_comparison["B=0 r=1"]`): the 2x3 budget is not spent,
   `slurm/s3_2x3.sbatch` is not launched with Heron-derived parameters, and the main H0 submission stays held.
   **Its prescribed re-plan (Plan B, k = 1, 2 only) is not adopted yet**, because at 2x2 it cannot act on the
   quantity that failed: every frozen circuit is already one exact structured step of 663 CZ whatever its k
   (`validation/H0P_ibm_fez.json`: r = 1 cz_min = cz_max = 663 over k = 1..4), so Plan B changes the number of
   circuits and shots, not f.  The shortfall has a computable cause that the prediction omits (section 2), and the
   correct next step is a diagnostic that costs at most 40 s of the 598 s left (section 6), after which the plan
   is re-sized with a model that contains the missing term.
2. **The next measurement** is one diagnostic session of four SamplerV2 jobs on ibm_fez (prompts/19): the frozen
   canary circuit under the 2x2 factorial {DD on/off} x {twirling on/off} at 2000 shots each, plus two windowed
   idle tests (T1 and Ramsey, 85 x 512 ns) with and without DD, plus all-0/all-1 at 2000 shots.  Estimated
   execution 5.7 s over 20000 shots; billed cost bounded by 4 x (2 s job overhead as billed for the canary) + 5.7 s
   ≈ 14 s; caps 30 s per job, 40 s in all (section 6).  Each outcome is mapped to what it rules in or out.
3. **What moves downstream** (section 7): gate S2D's 2x2/Heron PASS (f = 0.1248) no longer supports the 2x2 half
   of amendment 01 — the product-of-gate-fidelities f is not a hardware f on this device; the 2x3 requirement
   eps2 <= 7.094e-04 stays necessary but is no longer sufficient (a duration x 1/T2 term must be added, with the
   vendor's T1, T2 and gate durations as new spec lines); the shot-quota memo's rule stands and its numbers do
   not (they scale as 1/f and were computed from a model-incomplete f); S3's Aer criterion cannot be a hardware
   go criterion until the idle term is in the model.  None of these is re-computed here: the diagnostic first.
4. **BLOCKED.md** states the facts correctly and stops one step short of the cause (section 8).

## 1. What the device data say (facts)

| quantity | value | source |
|---|---|---|
| job, shots, usage | `dapbusac505c73chv0og`, 3 pubs x 267, `usage_s` 2.0, `circuits_execution_time_ns` 265274624 | `data/hardware/H0_ibm_fez_canary/session.json` |
| accepted / yield | 8 / 267 = 0.02996; 7 distinct states; rejections flag 176, link 78, sector 5 | `validation/H0_canary.json:data.analysis.per_circuit[0]` |
| predicted yield (r = 1 group) / f | 0.18725 / 0.21952; Aer of the same circuit at 267 shots: 71 accepted | `H0_canary.json:data.predicted_yield`, `data.f_comparison`; `data/hardware/H0_ibm_fez/sim_cache/B=0_r1.json` |
| measured f, ratio | 0.02551, measured/predicted 0.1162; relative deviation 0.8838 (criterion <= 0.30) | `H0_canary.json:criteria[2]` |
| calibration identity | `fingerprint_match` true, `f_live_vs_prediction_max_abs_diff` 0.0 (84 circuits), retrieval diff 0 leaves | `session.json:preflight`, `session.json:retrieval_calibration_diff` |
| readout, patch 1 | all-0 237/267 = 0.8876 correct; all-1 240/267 = 0.8989 | `counts/cal_patch1_all0.json`, `cal_patch1_all1.json` |
| circuit | 663 CZ, 2013 one-qubit gates, depth 1328, physical qubits 117 122 123 124 125 136 141 142 143 144 145 146 | `counts/B0_ref06_k1_rep1.json` manifest |

**P2 (statistics).**  P(<= 8 | binomial n = 267, p = 0.18725) = 4.79e-15; against the seeded Aer count of this
circuit (p = 71/267) 2.66e-25.  Against pure garbage (Poisson mean a x 267 = 2.48, a = 38/4096 = 0.00928) P(>= 8) =
4.0e-3: the 8 acceptances are 2.7 sigma above the garbage floor, i.e. a real but small clean component.  The
readout-drift item (qubit 123: 11 flips in 534 preparations against the calibration's 3.13) has P(>= 11) = 4.1e-4,
about 0.5 % after the 12-qubit look-elsewhere correction.  **It is evidence of a modest readout drift on qubit 123,
not noise — but it is irrelevant to the shortfall**: the all-12-correct readout probability measured in the same
job (0.888 / 0.899) exceeds the 0.82 the yield model assumes, and matches the calibration's product
prod_q (1 − e_q) = 0.8846 (P4).  The readout part of the model is conservative on this patch today.

**P3 (structure of the raw strings).**  The failed shots are not corrupted codewords; they are uniformly random
strings.

| statistic | hardware (267 shots) | Aer prediction, seed 11 (267 shots) | uniform over 4096 |
|---|---|---|---|
| distinct strings | 253 | 180 (expectation 121.7 for 267 draws from its distribution) | expectation 258.5 |
| accepted / rejected flag : link : sector | 8 / 176 : 78 : 5 | 71 / 130 : 49 : 17 | 0.93 % / 68.4 % : 29.6 % : 1.1 % |
| reference string `000100100000` seen | 2 | 43 | 0.065 (267/4096) |
| mean min-Hamming distance to a B = 0 codeword | 2.569 | 1.468 | 2.766 |
| histogram of that distance, d = 0, 1, 2, 3, 4, 5 | 8, 33, 86, 88, 43, 9 | 71, 64, 80, 42, 8, 2 | (x 267/4096) 2.5, 24, 80, 101, 47, 11 |

The mixture "c x clean + (1 − c) x uniform" fitted on the acceptances gives c = 0.0209 and predicts the rejection
split 178.7 : 77.5 : 2.8 against the observed 176 : 78 : 5 (chi-square 1.76 for 2 dof).  The Aer prediction has
the opposite signature: peaked (43 returns of the reference), few distinct strings, and rejections dominated by
one- and two-bit corruptions (link and sector failures at 25 % and 9 % of the rejected, against 30 % and 2 %
for uniform).  **The output register of the real device is, to within statistics, maximally mixed apart from a
~2 % clean component.**  That is what a total per-shot error budget of −ln(0.0255) = 3.7 units looks like, and
it is the first fact any explanation must reproduce: the missing error is large, of order 2.2 units, not a
30 % miscalibration.

Bookkeeping of the "missing units".  The predicted f = 0.2195 is `gate_S2D.analyse_on_backend`, which
multiplies the 663 CZ errors **and the 12 measurement errors** (`log_f += log1p(-e)` for `measure`), and the
yield model then applies 0.82 again; so the gates-only survival is 0.2195 / 0.8846 = 0.248.  Taking readout once
at its measured value 0.893, the measured gates-only survival is (0.02996 − 0.00928)/(0.893 − 0.00928) = 0.0234.
Missing budget: ln(0.2195/0.0255) = 2.15 units on the gate's bookkeeping, ln(0.248/0.0234) = 2.36 units with
readout counted once.  Either way, roughly the size of the whole gate-error budget (−ln 0.248 = 1.39).

## 2. Where the prediction comes from, and the term it omits (P1)

The prediction chain is `gate_S2D.analyse_on_backend` (product of the calibration's gate and readout errors) and
`AerSimulator.from_backend(backend, seed_simulator=11)` in `scripts/gate_H0P.py:517`, run on the frozen QPY
circuits as transpiled (`optimization_level` 3, no scheduling; the op list is `sx, rz, cz, x, measure, barrier`,
no `delay`).  Aer's `NoiseModel.from_backend` attaches depolarizing + thermal-relaxation errors to each gate for
that gate's duration on that gate's qubits.  **Neither model contains the time a qubit spends waiting for other
qubits' gates.**  On a heavy-hex device the routed 2x2 circuit is nearly serial: depth 1328 for 663 CZ, i.e.
about one CZ per layer, and 12 qubits share those layers.

P1 schedules the frozen canary circuit ASAP with the durations of the calibration record the device ran under
(`calibration_at_submission_20260922T1400Z.json`: cz 68 ns, sx/x 24 ns, rz 0, measure 1.66 us):

| physical qubit | T1 (us) | T2 (us) | busy (us) | idle (us) | idle windows | windows > 192 ns (DD-eligible) | longest window (us) | p_idle T1 part | p_idle T2 part |
|---|---|---|---|---|---|---|---|---|---|
| 117 | 160.8 | 183.9 | 2.92 | 40.79 | 14 | 13 | 18.02 | 0.062 | 0.108 |
| 122 | 124.0 | 53.8 | 2.16 | 41.55 | 17 | 14 | 18.25 | 0.080 | 0.344 |
| 123 | 159.0 | 124.8 | 19.79 | 23.92 | 39 | 26 | 7.44 | 0.037 | 0.095 |
| 124 | 81.0 | 101.9 | 10.79 | 32.92 | 43 | 25 | 9.08 | 0.099 | 0.158 |
| 125 | 149.6 | 50.5 | 7.82 | 35.89 | 16 | 15 | 9.12 | 0.059 | 0.335 |
| 136 | 71.8 | 87.4 | 21.81 | 21.90 | 64 | 39 | 1.48 | 0.076 | 0.125 |
| 141 | 138.8 | 108.1 | 2.38 | 41.32 | 16 | 15 | 17.41 | 0.072 | 0.183 |
| 142 | 151.5 | 265.1 | 7.84 | 35.87 | 35 | 27 | 10.96 | 0.058 | 0.067 |
| 143 | 151.2 | 115.6 | 24.74 | 18.97 | 50 | 24 | 2.37 | 0.031 | 0.082 |
| 144 | 158.2 | 190.9 | 12.63 | 31.08 | 39 | 16 | 10.50 | 0.048 | 0.080 |
| 145 | 155.7 | 130.8 | 7.56 | 36.15 | 28 | 19 | 11.00 | 0.057 | 0.135 |
| 146 | 127.3 | **16.0** | 1.86 | 41.85 | 14 | 11 | **25.30** | 0.077 | **0.857** |

- Circuit duration before readout 43.71 us (+ 1.66 us measure = 45.37 us, identical to the session's
  `qpu_time_estimate.duration_mean_s` 4.5368e-05, which uses the same critical-path rule in `h0_qpu_time.py`).
- Idle relaxation budget in the Pauli-twirling approximation of thermal relaxation (the channel Aer's
  `RelaxationNoisePass` would put on a `delay`): per window p = (1 − e^{−w/T1})/4 + (1 − e^{−w/T2})/2.
  **Sum over all windows and qubits: 3.323 units (T1 part 0.755, T2 part 2.568)**, exp(−3.323) = 0.036.
  Three qubits carry 60 % of the T2 part: 146 (T2 = 16 us, one 25.3-us window), 122 and 125 (T2 ≈ 50 us).
- For comparison, the relaxation the Aer model does see (over busy time only) sums to 0.81 units — and that
  part is already inside the reported gate errors, so it is not missing.

**Bracket for the canary configuration (DD XY4 on, twirling on).**  The runtime's `PadDynamicalDecoupling`
pads an idle window only if it exceeds 2 x the sequence length (default `sequence_min_length_ratios` = 2.0; XY4
= 4 x 24 ns, so windows > 192 ns) and inserts **one** sequence per window with its four pulses spread evenly
(`insert_multiple_cycles` is not exposed in the SamplerV2 options).  244 of the 375 windows are eligible; the T2
budget inside them is 2.494 units, outside 0.073; the XY4 pulse cost, 4 x sx_error per eligible window, is
S_DD = 0.317.  Hence, with f_gates = 0.2195 and no twirling effect:

| DD refocuses the eligible-window T2 budget by | f = f_gates e^{−0.755 − rho 2.494 − 0.073 − 0.317} | yield 0.82 f + (1−f) a |
|---|---|---|
| fully (rho = 0) | 0.0698 | 0.0659 |
| 75 % (rho = 0.25) | 0.0374 | 0.0396 |
| 50 % (rho = 0.5) | 0.0201 | 0.0255 |
| not at all (rho = 1) | 0.0058 | 0.0140 |
| **measured** | **0.0255** | **0.0300** |

The measurement sits inside the bracket at rho ≈ 0.40 (planner arithmetic: (ln 0.0698 − ln 0.0255)/2.494), i.e.
"DD refocuses about 60 % of the idle dephasing" — a plausible number for one XY4 per window against windows of
up to 25 us on a qubit with T2 = 16 us.  The idle term is therefore the right size, it is parameter-free in its
inputs (the same calibration record the prediction used), and it is absent from both predictions.  This is the
primary hypothesis, **H_A**.

Two consequences follow directly.  (i) The L4_fez "conservative by 1.32–1.39x" finding compares Aer with the
analytic product on the same snapshot — both are gate-only models; it says nothing about hardware, and the
direction is expected (a share of late Pauli errors are Z-type and invisible to a Z-basis readout).  It does not
need reconciling with the canary.  (ii) The device "improving" between 01:11 and 08:00 (r = 1 f 0.1797 → 0.2103)
is a statement about gate and readout errors only; the T1/T2 of the patch are not in f.

## 3. The caller's hypothesis: the SamplerV2 options went live for the first time (H_B)

True as stated: `data/hardware/H0_dryrun/session.json:sampler_options_effective` is false and the canary's is
true; H0P, H0_dryrun, L4_fez and the rehearsal never exercised DD or twirling.  What the repository can and
cannot say about it:

- **Measurement twirling is exonerated by the same job.**  It applies random X before readout and un-flips
  classically; a wrong un-flip would have scrambled the all-0/all-1 pubs, which came back 0.888/0.899 correct
  against 0.8846 expected from the calibration (P4).
- **DD pulse cost is computable and small**: S_DD = 0.317 (factor 0.73) at one XY4 per eligible window.  Against
  it stands a possible benefit of up to 2.49 units.  Under H_A, switching DD off makes the yield *worse*, not
  better — that is the sharpest difference between H_A and H_B.
- **Gate twirling with strategy `active-accum` is the one option with a mechanism of the right order.**  The
  runtime docstring (`qiskit_ibm_runtime/options/twirling_options.py`): "the union of instruction qubits in the
  circuit up to the current twirled layer will be twirled in each individual twirled layer".  On a serial circuit
  of ~663 twirled layers over 12 accumulated-active qubits, that is up to ~8000 random Paulis, half of which (X, Y)
  are physical pulses if the runtime does not merge consecutive Paulis on an idle qubit: up to
  663 x 12 x 0.5 x 3.3e-4 ≈ 1.3 units (factor 0.27).  Whether they are merged, and whether the random Paulis
  themselves refocus dephasing (randomized compiling has that side effect), cannot be determined from anything in
  this repository or in the client library.  So H_B is neither excluded nor established by computation — which is
  exactly why the factorial measurement is the right next step and not a re-plan.

## 4. Other candidates weighed

- **Coherent errors, crosstalk, non-Markovian effects beyond the calibration (H_C).**  Plausible in dense CZ
  layers, but this circuit is *not* dense: one CZ per layer.  A factor 8.6 in f from gate-level excess alone would
  need each CZ to be 2.2/663 = 3.3e-3 worse than its RB value — more than doubling every CZ error on a patch whose
  mean is 2.2e-3 — with the raw strings still showing the uniform-garbage signature.  Not excluded; not the first
  hypothesis while an omitted 3.3-unit term sits in plain view.  The diagnostic's J1 cell (both options off)
  bounds it: under H_A alone J1 gives 31 ± 6 accepted of 2000; a result at the garbage floor (18.6) would need H_C
  on top.
- **A structural error in the transpiled circuit on hardware (H_D).**  Excluded to the extent the data can:
  round trip 7 of 7, the decoder accepted only valid B = 0 codewords, the reference string was seen (2 of 267,
  P3), the frozen set is leak-free at 1.5e-14 and its CZ counts match the manifests on the live target
  (`H0P_ibm_fez.json:f_recomputed_on_the_day`), and the readout map is consistent (`measurement_consistent` true).
  A bit-order or layout mistake would have put the accepted strings in the wrong sector or failed the round trip.
- **The rejection split (flag 176 / link 78 / sector 5).**  The decoder tests in order: vertex flags, then link
  consistency (the flux bit of each link seen from its two end vertices), then the sector.  For a uniformly random
  12-bit string those fail in the ratio 68.4 : 29.6 : 1.1 (exhaustive, `H0_canary.json:data.analysis.random_acceptance`);
  the hardware shows 65.9 : 29.2 : 1.9.  Had the errors been sparse (a codeword with one or two flipped bits, the Aer
  regime), link and sector failures would dominate over flag failures — a single flipped flux bit fails the link
  check, a flipped occupation bit the sector — as they do in the Aer sample (25 % link, 9 % sector).  So the split
  is *not* "78 link-check failures with a story of their own"; it is the second and third moments of the same
  uniform garbage.  It says the register is fully scrambled, consistent with H_A's 3.3 units and with H_B's large
  variant, and inconsistent with any small correction to the calibration.
- **Readout drift on qubit 123**: real at the 4e-4 level (P2), irrelevant to the yield (section 1).

## 5. Ruling on prompts/07 clause (b) and Plan B

The clause reads: "If the yield is far below the model at 250 CZ, do not spend the 2x3 budget: planner-fable
re-plans (fewer coarse steps k = 1, 2 only; Plan B of manual Sec. 11)"; prompts/15 escalation (b) restates it
with the 0.7 threshold.  The manual's Plan B (Sec. 11) reduces "the circuit set to k = 1, 2 coarse steps
(<= 500 CZ) and raise[s] shots by Eq. (5)" — it is written for Trotterized steps whose CZ count grows with k.

- Trigger: met (0.116 < 0.7).  The two prohibitions are in force from now: no 2x3 budget, no S3 launch with
  Heron-derived parameters.  Add: no main H0 submission on the current prediction.
- Plan B's remedy does not touch the failure at 2x2: the exact structured circuits have 663 routed CZ at every k,
  so "k = 1, 2 only" halves the circuit count and leaves f, the idle time and the duration unchanged.  Sizing the
  shots "by eq. (5)" at the measured f gives S >= 7.7/(0.0255 x 1e-3) = 3.0e5 per circuit (P6) — for an f that is
  unexplained and, if H_A holds, patch-dependent by a computable factor (qubit 146 alone is 0.93 of the 3.32 units).
  Re-planning on that number would be planning on sand.
- Therefore: **a diagnostic step first** (section 6), then the re-plan, which will (a) replace the yield model of
  manual Step 4.4 by one with the duration term, (b) re-select the patch on T2, (c) decide DD/twirling from the
  factorial, (d) size the shots with the D3' rule at a predicted f the diagnostic has validated, and (e) only then
  decide whether the 2x2 H0 fits the remaining budget and how the 2x3 amendment must be re-specified.  For scale,
  at the measured f the frozen r = 1 plan alone would be 331k (B = 0) + 303k (B = 1) shots = 187 s of execution
  (P6, linear scaling of the D3' plan in 1/f); the r = 2, 3 ladder is out of reach at f^2 ≈ 6.5e-4.

## 6. The next measurement: prompts/19 (diagnostic session, four jobs)

SamplerV2 options are per job, so the factorial needs four jobs.  All circuits are on patch 1; the canary circuit
is the frozen `B0_ref06_k1_rep1` byte-for-byte (sha256 8f372da0…).  Shots: 2000 per pub.

| job | options | pubs | shots | execution (P6 rule: shots x (duration + 250 us rep delay)) |
|---|---|---|---|---|
| J1 | DD off, twirling off | canary circuit; `t1w` (all-1, 85 x [delay 512 ns, barrier], measure); `ramw` (sx, 85 windows, rz(pi) sx rz(pi), measure); all-0; all-1 | 5 x 2000 | 2.78 s |
| J2 | DD XY4 on, twirling off | canary circuit; `t1w`; `ramw` | 3 x 2000 | 1.77 s |
| J3 | DD off, twirling on (`active-accum`) | canary circuit | 2000 | 0.59 s |
| J4 | DD XY4 on, twirling on — the canary's D8 options | canary circuit (replicate at 7.5x the statistics) | 2000 | 0.59 s |

Total 20000 shots, 5.7 s of execution; billed cost at the canary's ratio (0.265 s executed, 2 s billed): ≤ 14 s.
Caps: 30 s per job, 40 s for the session; J1 is submitted and retrieved first, J2–J4 only if its usage is ≤ 10 s.
Remaining allowance before the session: 598 s.

Preregistered predictions (recomputed by the executor from the live record at submission, the values below are
P5 on the 1400Z record):

| pub | under H_A (idle term, calibration T1/T2) | under H_B (options were the cause) | decision |
|---|---|---|---|
| J1 canary | f = 0.2195 e^{−3.323} = 0.0079, yield 0.0157 → 31 ± 6 of 2000 (garbage floor 18.6) | yield 0.187 → 374 ± 17 | N1 ≤ 100 rejects H_B (P = 2e-73 under H_B); N1 ≥ 250 confirms it (P(≥100 given H_A) = 5e-23); between: inconclusive → planner |
| J2 canary | 132 / 79 / 51 / 28 of 2000 for rho = 0 / 0.25 / 0.5 / 1 | ≈ 374 minus DD pulse cost | J2 > J1 is the DD benefit predicted by H_A; J2 < J1 means DD hurts on this device |
| J3 canary | ≈ J1 x (twirling cost) x (incidental refocusing) — not predicted | — | J3/J1 is the twirling effect without DD |
| J4 canary | the canary's own rate: 60 ± 8 of 2000 | — | replication; J4/J2 is the twirling effect with DD |
| `t1w` J1 | per qubit P(1 survives) = e^{−43.5 us/T1}: 0.762, 0.703, 0.760, 0.583, 0.747, 0.544, 0.730, 0.749, 0.749, 0.759, 0.755, 0.709 (qubits in the order of the P1 table) | — | measured decay rate within [0.5, 2] x 1/T1_cal for ≥ 10 of 12 qubits |
| `ramw` J1 | per qubit P(0) ≤ (1 + e^{−43.5 us/T2})/2: 0.894, 0.722, 0.852, 0.826, 0.710, 0.803, 0.834, 0.924, 0.843, 0.898, 0.858, 0.533 (T2 is a Hahn-echo bound; free induction is ≤ it) | — | P(0) ≤ bound + 3 sigma for ≥ 10 of 12 qubits; the implied T2* per qubit is the model input |
| `ramw`, `t1w` J2 | not predicted (this is the measurement of DD's refocusing and pulse cost at production window lengths: 340 XY4 pulses per qubit, budget 0.05–0.19 units per qubit) | — | gives rho per qubit; feeds the idle-aware prediction of J2 and J4 |

What each outcome means:
- **N1 ≤ 100 and the idle tests pass their criteria**: H_B rejected; H_A validated in its inputs; the idle-aware
  model (with measured T1, T2*, rho) is the prediction model of the re-plan; DD stays on iff J2 > J1; twirling
  stays on iff J4 ≥ J2 within errors.  Re-plan: patch by T2, shots by D3' at the validated f, k = 1..4 kept
  (the k index costs nothing in CZ), r = 2, 3 dropped unless f > 0.1 on the new patch.
- **N1 ≥ 250**: H_B confirmed, H_A's T1 part falsified (it alone caps J1 at ≈ 190) — the calibration's T1/T2
  would then not describe the device during the circuit, which is itself a finding; re-run the canary with the
  options off; D8 amended; the prediction chain stands.
- **100 < N1 < 250, or N1 at the garbage floor (≤ 25) with the idle tests passing**: mixed or H_C; planner at max.
- **Idle tests fail their criteria** (T1 decay outside [0.5, 2] x calibration, or Ramsey above the Hahn bound):
  the calibration's coherence numbers do not describe the device on the day; the model cannot be built from the
  record; planner at max.

## 7. What this does to the conclusions predicated on the Aer / product-of-fidelities f

The measured/predicted ratio 0.116 is a property of *this circuit on this patch of this device*; what transfers
to other devices is the **omission**, not the factor.  Item by item:

- **Gate S2D, 2x2/Heron PASS (f mean 0.1248, worst 0.1166; FakeFez snapshot).**  Computed with the gate-only
  model; the same model on the live record gives 0.2195 for the canary circuit and the device delivered 0.0255.
  With the idle term the 2x2/Heron f on patch 1 lies in [0.006, 0.070] (section 2 bracket), below S2D's worst-case
  threshold 0.05 in most of the bracket and below the 0.1 criterion everywhere.  **S2D's 2x2 conclusion — "the
  amendment is supported" for 2x2 on a Heron-class device — is withdrawn as a hardware statement** until the
  idle-aware model is validated by prompts/19 and re-run over the frozen set and candidate patches.  The gate's
  JSON is not edited; a new gate (S2D-idle, or an S2D re-run with the duration term) replaces the claim.
- **2x3 device requirement `eps2 <= 7.094e-04`** (`reports/S2D_2x3_device_requirements.md`: 2158 eps2 + 7310 eps1
  + 20 eps_ro <= 2.3026 for f >= 0.1).  The inequality remains necessary.  It must gain a term
  sum_q [t_idle,q/(4 T1_q) + t_idle,q/(2 T2_q)] <= (2.3026 − gate terms), with t_idle,q from the scheduled
  circuit on the device's gate durations.  For a trapped-ion device with serial two-qubit gates the duration is of
  order N_2q x t_2q, so the vendor must supply t_2q, t_1q, T1, T2 (under the vendor's own DD) — **four new spec
  lines for amendment 01 item 4**.  No number is estimated here: the idle term for the ion trap is not computable
  from anything in this repository.
- **Shot-quota memo (`reports/S2D_shot_quota_decision_20260922.md`: 556 000 / 808 104 at the declared 2x3 f = 0.0534).**
  The rule (D3' per-state, 2e5 floor) stands; the numbers scale as 1/f and were computed from a model-incomplete f.
  The owner should sign the rule, not the numbers; the numbers are re-issued when a measured f on the 2x3 device
  exists (its own canary, an H0-equivalent), and the idle-aware model sizes the expectation before that.
- **S3 (`slurm/s3_2x3.sbatch`, `scripts/s3_device_model.py`).**  Its criterion "Aer device-model recall >= 0.9"
  is a pipeline and post-processing test; as a hardware go criterion it is now known to be optimistic by a
  device-dependent factor that reached 8.6 on ibm_fez.  S3 stays where prompts/07 (b) puts it: not launched with
  Heron-derived parameters.  When it runs, its f input must be the idle-aware one.
- **Manual Step 4.4** ("f ≃ (1 − eps)^{N_CZ}") needs an amendment line: f ≃ (1 − eps)^{N_CZ} x
  prod_q exp(−t_idle,q/T_eff,q); the clean statement for the amendment is the requirement inequality above.
- **Gate H0's own criterion** (measured f within 30 % of the prediction) is unchanged; what changes is the
  prediction it is compared with, and only through a new gate run before the next submission — never post hoc.
- **What does not move**: E1–E3, S1, CS, L2, L5, the codec and conventions (the round trip passed on real
  strings), the S2 CZ counts, the D3' shot rule's logic, the calibration-content preflight D9 (it did its job:
  the discrepancy is not calibration drift), and the canary rule D5 (it did its job at 2 s instead of 66 s).

## 8. Is `validation/BLOCKED.md` correct?

Yes in every number and in its two structural claims (calibration drift excluded; the gap is model-versus-device
at 663 CZ).  Three additions are needed for it to state the *problem* rather than the *symptom*:

1. The gap has a computable cause that both predictions omit: idle-time relaxation of a nearly serial 43.7-us
   circuit whose qubits wait 19–42 us each, worth 3.3 Pauli-error units on the calibration's own T1/T2 against a
   missing 2.2 (section 2).  "The Aer device model" is not wrong about the gates; it was run on a circuit with no
   schedule.
2. The raw strings are uniform garbage plus 2 % clean (P3: 253 distinct of 267; rejection split within
   chi-square 1.76 of the uniform mixture); this discriminates "large omitted error" from "moderately
   miscalibrated gates" and belongs in the record.
3. The readout-drift item is a genuine 4e-4-level excess on qubit 123 (P2), not "statistically thin", and it is
   irrelevant to the shortfall because the measured all-correct readout (0.888/0.899) beats the model's 0.82.

Its "for the planner" paragraph is right that no constant, convention, decoder or frozen circuit was touched, and
that the decision is the planner's.  The next-step file name it anticipates is `prompts/19_H0_canary_diagnostic_20260922.md`.

## 9. Reproduction snippets (planner computations; laptop, `coding` env, seconds each)

P1 — schedule and idle budget of the frozen canary circuit on the submission-time calibration record:

```python
import gzip, json, numpy as np
from qiskit import qpy
with gzip.open('data/hardware/H0_prep/circuits/B0_ref06_k1_rep1.qpy.gz','rb') as fh: qc = qpy.load(fh)[0]
cal = json.load(open('data/hardware/H0_ibm_fez_canary/calibration_at_submission_20260922T1400Z.json')); Q, E = cal['qubits'], cal['edges']
active = sorted({qc.find_bit(q).index for inst in qc.data for q in inst.qubits if inst.operation.name != 'barrier'})
def dur(name, qs):
    if name in ('rz', 'barrier'): return 0.0
    if name in ('sx', 'x'): return Q[str(qs[0])]['sx_duration_s']
    if name == 'cz': a, b = qs; e = E.get(f'{a}-{b}') or E.get(f'{b}-{a}'); return e['cz_duration_s']
    if name == 'measure': return Q[str(qs[0])]['measure_duration_s']
t = {q: 0.0 for q in active}; busy = {q: 0.0 for q in active}; windows = {q: [] for q in active}
for inst in qc.data:
    name = inst.operation.name; qs = [qc.find_bit(q).index for q in inst.qubits]
    if name == 'barrier':
        qs = [q for q in qs if q in active]; tm = max(t[q] for q in qs)
        for q in qs:
            if tm > t[q] + 1e-15: windows[q].append(tm - t[q]); t[q] = tm
        continue
    if name == 'measure': continue
    d = dur(name, qs); start = max(t[q] for q in qs)
    for q in qs:
        if start > t[q] + 1e-15: windows[q].append(start - t[q])
        t[q] = start + d; busy[q] += d
T = max(t.values()); S1 = S2 = SDD = 0.0; n_elig = 0
for q in active:
    T1, T2, sx, se = Q[str(q)]['T1_s'], Q[str(q)]['T2_s'], Q[str(q)]['sx_duration_s'], Q[str(q)]['sx_error']
    S1 += sum((1 - np.exp(-w/T1))/4 for w in windows[q]); S2 += sum((1 - np.exp(-w/T2))/2 for w in windows[q])
    elig = [w for w in windows[q] if w/(4*sx) > 2.0]; n_elig += len(elig); SDD += 4*se*len(elig)
    print(q, round(T1*1e6,1), round(T2*1e6,1), round(busy[q]*1e6,2), round((T-busy[q])*1e6,2), len(windows[q]), len(elig), round(max(windows[q])*1e6,2))
print('T_us', T*1e6, 'S_T1', S1, 'S_T2', S2, 'sum', S1+S2, 'exp', np.exp(-S1-S2), 'DD-eligible', n_elig, 'S_DD', SDD)
# expected: T_us 43.71, S_T1 0.755, S_T2 2.568, sum 3.323, exp 0.0360, DD-eligible 244, S_DD 0.317
```

P2 — statistics: `from scipy.stats import binom, poisson`; `binom.cdf(8, 267, 0.18724840929749384)` = 4.79e-15;
`binom.cdf(8, 267, 71/267)` = 2.66e-25; `poisson.sf(7, 38/4096*267)` = 4.0e-3; `poisson.sf(10, 0.005859375*534)`
= 4.1e-4, look-elsewhere `1-(1-4.1e-4)**12` = 0.005.

P3 — structure of the strings (uses `skqd.codec.Codec(Model(2).basis)`, `skqd.reference_sim.qiskit_key_to_bits`,
the hardware counts and `sim_cache/B=0_r1.json:counts.B0_ref06_k1_rep1`): enumerate the 4096 strings through
`codec.decode(bits, target_twoB=0)` to get the 38 codewords and the uniform reason split; for each sample compute
the reason split, the number of distinct keys, the count of `000100100000`, and the minimum Hamming distance to
a codeword; expected distinct strings in 267 draws = sum_s (1 − (1 − p_s)^267); mixture c = (8/267 − a)/(1 − a),
chi-square of the observed split against (1 − c) x 267 x (2800, 1214, 44)/4096.  Values: section 1.

P4 — `np.prod([1 - cal['qubits'][str(q)]['measure_error'] for q in [117,122,123,124,125,136,141,142,143,144,145,146]])`
= 0.8846; 237/267 = 0.8876; 240/267 = 0.8989.

P5 — predictions: with f_g = 0.21952151475659942, a = 38/4096, y(f) = 0.82 f + (1 − f) a, N = 2000:
J1 under H_A: f = f_g e^{−0.755−2.568} = 0.0079, y = 0.0157, N y = 31.4, sqrt(N y (1−y)) = 5.6; under H_B y =
0.18724840929749384, N y = 374 ± 17.4; `binom.sf(99, 2000, 0.0157)` = 5.2e-23, `binom.cdf(100, 2000, 0.1872)` =
2.1e-73.  J2 rows: f = f_g e^{−0.755 − rho 2.494 − 0.073 − 0.317}.  Per-qubit e^{−T/T1} and (1 + e^{−T/T2})/2 at
T = 43.71 us from the record (43.52 us for 85 x 512 ns changes the third decimal only).

P6 — scaling: 38505 x 0.21952/0.02551 = 331 289; 35202 x 8.60 = 302 870; (331289 + 302870) x 295.4e-6 s = 187 s;
7.7/(0.02551 x 1e-3) = 3.02e5; 7.7/(0.21952 x 1e-3) = 3.51e4; execution per pub = shots x (45.37 + 250) us
(coarse-step and idle pubs) or shots x (1.66 + 250) us (all-0/all-1).
