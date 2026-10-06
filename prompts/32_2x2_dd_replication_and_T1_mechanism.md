# 32 — Owner decision 2026-10-06, option A then B: the 2x3 IBM NO-GO recorded on K0; one preregistered job on ibm_kingston that replicates the XY4 gain and tests the mechanism of the context-aware DD collapse (gate H0_ddrep); then the K1 2x3 pilot as built when kingston publishes CZ calibration again
executor: executor-opus   effort: high
time budget: about 10 h of executor work (0 QPU s until step A.E), spread over the days kingston needs to come back; one QPU job for A (cap 45 s billed), then B's one job (cap 300 s billed, unchanged)   machine: laptop + QPU (ibm_kingston)

Owner decision (verbatim, `data/owner_decision_20261006_A_then_B.md`): "I want you to do A first, then when that
is finished, do B because by that time it might be online".

Code orientation rule (binding, from the owner's global instructions): `graphify-out/graph.json` exists.  Use
`graphify query "<question>"`, `graphify explain "<symbol>"`, `graphify path "A" "B"`, `graphify affected "<symbol>"`
before grepping or reading many files; read raw files only to edit or debug specific lines; run `graphify update .`
after changing code and before handing back.

Rule 1 of CLAUDE.md is binding: every number in a report comes from `validation/*.json` or `data/*.json`; the
numbers in this prompt are either quoted from those files (source named) or marked **planner arithmetic**
(`scratch/planner/ddrep_budget_20261006.{py,json}`, 0 QPU s) and must be recomputed by the gate on the day's record.

## Goal

Three deliverables, in the owner's order.

**A1 — the 2x3 IBM NO-GO, recorded.**  Gate K0_2x3_2x4 PASS 6/6 (`validation/K0_2x3_2x4.json`) is a *model verdict*
on the committed record of 2026-10-02: the signed 2x3 circuit routed on ibm_kingston has 5659 CZ, an ALAP duration of
410.3 us, a two-qubit-only ceiling f_ceiling 9.83e-3, f_gates on the layout 6.07e-6, and an idle-aware clean fraction
of 1.06e-16 (echo T2) / 3.73e-38 (T2* at ratio 0.174) — reference hits at the garbage level (0.095 per circuit at 1e5
shots).  Record this as an information block and a short generated note; no QPU seconds are spent on 2x3 before B.

**A2 — gate H0_ddrep (one preregistered job on ibm_kingston, 20 pubs x 6000 shots).**  (a) Replicate the XY4 gain of
`validation/H0_ddtest.json` (T0 no DD vs T3 = client XY4 in windows >= 1.024 us, on the two signed k = 1 circuits
`B0_ref06_k1`, `B1_ref07_k1`, same statistic, same adoption rule) on a fresh calibration; (b) replicate the collapse
of the context-aware cell T1 in the same job; (c) discriminate three hypotheses for that collapse with four circuit
cells and four pulse-train calibration pubs, each with a preregistered prediction under each hypothesis.  Why it
matters: the H0_2x2 result (`validation/H0_2x2.json`) stands on the T3 configuration, measured once on one
calibration; the technical note needs the gain replicated and the collapse explained before either is reported as
a finding (`reports/H0_2x2_full_hardware_report_20261002.md` sections 3 and 7).

**B — the K1 2x3 pilot as built** (`scripts/gate_K1_2x3_fpilot.py`, one job, cap 300 s billed), executed through its
existing stages when ibm_kingston again publishes CZ calibration, with every precondition of the gate unchanged.

## Inputs (read first)

- `data/owner_decision_20261006_A_then_B.md`, `data/owner_decision_20261005_k1_2x3_fpilot.md`,
  `data/owner_decision_20261005_partB.md` (decisions 1a, 3a).
- `validation/K0_2x3_2x4.json` (`data.2x3.committed`: routing, alap, idle terms; the criteria list) and the K1 LOG row
  (`prompts/LOG.md`, 2026-10-05/06) for the K1 resume order.
- `validation/H0_ddtest.json` (`data.decision`, `data.decision_rule`, `data.power_prereg`, `data.pubs`, `data.patch`,
  `data.calibration_prereg`), `reports/H0_ddtest_ibm_kingston.md`, `data/hardware/H0_ddtest_prep/` (the committed
  T0/T1/T2/T3 QPYs and manifests with `dd.pulses_per_physical_qubit`, `index.json`, `select.json`,
  `prereg_84d59cbf9b5973d1.json`, `calibration_20261002T1906Z.json`, `ibm_kingston_full_20261002T1906Z.json`).
- `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage T steps T.A–T.F: this prompt follows them step for
  step with new names), `scripts/h0_ddtest_circuits.py` (`dd_variant`, `dd_checks`, `window_violations`, `timeline`,
  `translate_y`, `record_durations`, `build_coarse`, `stage_patchcal`), `scripts/gate_H0_ddtest.py`
  (`ratio_interval`, `adopt`, `signed_bar`, `stage_predict`, `stage_prereg_md`, `stage_assemble`),
  `scripts/h0_submit.py` (read-only), `scripts/h0_calwatch.py`, `scripts/h0_qpu_time.py`, `scripts/ibm_account.py`,
  `scripts/h0_device_survey.py` (`full_device_record`), `scripts/h0_backends.py` (`fresh_calibration`,
  `calibration_fingerprint`, `frozen_qubits_and_edges`).
- `reports/H0_2x2_full_hardware_report_20261002.md` sections 3 and 7, `reports/ibm_decoherence_literature_20261002.md`
  sections 2–3 (C1–C4).
- The installed qiskit 2.5.2 source of `ContextAwareDynamicalDecoupling`
  (`qiskit/transpiler/passes/scheduling/padding/context_aware_dynamical_decoupling.py`): read `get_orthogonal_sequence`,
  `_get_wire_coloring`, `_bitflips_to_timings`, `WalshHadamardSequence`.
- `data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json` (498 s left),
  `data/hardware/K0_prep/ibm_kingston_full_20261006T0042Z.json` (status `maintenance`, 352 of 352 cz keys without an
  error value).
- `scratch/planner/ddrep_budget_20261006.{py,json}` (this prompt's planner arithmetic; re-run it, it costs seconds).

## Planner decisions carried by this prompt (fixed before any new data exist)

**P1. Device: ibm_kingston, same patch, when it is back.**  Reasons, in order of weight.  (i) Power: the ratio
statistic decides the 1.25 floor only when the baseline carries enough excess reference hits — at the 10-02 baseline
f_T0 = 0.0400 the per-cell excess is X = 349.07 (`H0_ddtest.json: data.decision.cells.T0.excess_hits`), sigma_lnR =
sqrt(2/X) = 0.0757, 95 % factor 1.160, and a true 1.25 has a lower bound of 1.078 > 1 (**planner arithmetic**,
reproducing `data.power_prereg`).  No other device has a measured 2x2 baseline: on ibm_fez the last direct number is
f_clean = 6.7e-4 on the old configuration (prompts/20), where X would be about 6 and nothing is decidable; ibm_marrakesh
has no data at all.  A cross-device replication would therefore need its own pilot and a larger shot count — a new
unknown, not a replication.  (ii) The mechanism cells M1 and M4 are *derived from the T1 circuit byte for byte*
(same 862 pulses at the same start times); on the same patch the collapse is replicated in the strict sense and the
derived cells differ from it in exactly one thing.  (iii) The technical note's claim is "the gain holds on a fresh
calibration of the same device and the collapse has a mechanism"; cross-device generality is a separate, later claim.
Wait-and-poll rule and fallback: section A.W below.

**P2. Patch rule.**  Run the R1'-pilot embedding search on the day's full record exactly as `h0_ddtest_circuits.py
--stage select` does (information: winner, its score, the committed patch's score on the same record).  Keep the
committed patch [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95] **unless** (a) a qubit or edge of it is uncalibrated
on the day's record (missing error leaf) or (b) its `f_dd_off` score on the day's record is below 0.5 x the winner's.
In case (a)/(b) the winner is used, the T0/T1/T3 circuits are rebuilt by the same code on the new patch, and the gate
records `patch_reproduced: false` (a same-device, new-patch replication; the prereg says so in one sentence).  The
T0, T1, T3 QPYs are reused byte for byte when the patch is reproduced (`force_reuse` as in `build_coarse`).

**P3. The cells (seven circuit cells x two base circuits; parameters fixed here, never tuned on data).**

| cell | what it is | how it is built | pulses per circuit (B0_ref06_k1 on the 10-02 patch; `H0_ddtest.json`, `data/hardware/H0_ddtest_prep/circuits/*.json`) |
|---|---|---|---|
| T0 | no DD (same-job control) | the committed T0 QPY | 0 |
| T1 | context-aware Walsh-X DD, `min_duration` 128 dt (the collapsed cell) | the committed T1 QPY | 862 (q95 130, q91 118, q94 96, q74 90, q92 90, ...) |
| T3 | XY4 in windows >= 1.024 us (the adopted cell) | the committed T3 QPY | 244 |
| M1 | **CA +/-**: T1's pulse trains with alternating signs | `alternate_signs(T1, base)`: on every qubit, every second *inserted* x pulse (2nd, 4th, ...) is wrapped as `rz(-pi)`, `x`, `rz(+pi)` in circuit order (matrix Rz(pi) X Rz(-pi) = -X exactly; the same virtual-Z mechanism by which `translate_y` makes T2/T3's Y); timing identical to T1 | 862 x, 862 rz |
| M2 | **XX**: X-only CPMG pairs on the runtime's window set | `PadDynamicalDecoupling(durations, [XGate(), XGate()], sequence_min_length_ratios=[4.0], pulse_alignment=<target's>)` after `ALAPScheduleAnalysis(durations)`, as `dd_variant` builds T2; ratio 4.0 x (2 x 32 ns) = 256 ns = T2's window threshold (2.0 x 4 x 32 ns), so the pulsed window set is T2's | 2 per T2 window (expected 388 = 776/2; the build asserts the window set equals T2's) |
| M3 | **X(-X)**: M2 with alternating signs | `alternate_signs(M2, base)`; timing identical to M2 | 388 x, 388 rz |
| M4 | **CA minus the two hottest qubits**: T1 with every inserted pulse removed from the two physical qubits that carry the most T1 pulses (on the 10-02 patch: 95 and 91; q91 is also the patch's worst T1/T2 qubit, 99 us / 68 us in the record) | `strip_pulses_on(T1, base, {q_a, q_b})`: each removed x is replaced by `delay(8 dt)` on that qubit so every other start time is unchanged | 862 - 248 = 614 |

Every cell is verified in memory by `h0_ddtest_circuits.dd_checks` (i)–(v) before it is dumped (statevector = base
up to a global phase to 1e-10; duration = base to 1 dt; base ops keep their start times; inserted ops are only x / rz,
none in a leading window or after a measurement; basis {rz, sx, x, cz, delay, measure, barrier}; per-qubit pulses,
S_DD and the null ratio exp(-S_DD) on the day's record), plus `dd_exactness` (C4).  Three build-time identities are
asserted and recorded: the inserted-x start-time multiset of M1 equals T1's and of M3 equals M2's; M2's pulsed
windows (per qubit, start/end) equal T2's committed manifest's; M4's inserted ops equal T1's minus those on
{q_a, q_b}.  `h0_ddtest_circuits.py` is **imported, not edited** (gate K1 imports it too); the new functions live in
`scripts/h0_ddrep_circuits.py`.

**P4. Four pulse-train calibration pubs (the direct measurement of H_A's and H_D's parameters).**  On all 12 patch
qubits simultaneously, from |0>: a train of n back-to-back `x` pulses then measure, for XX-8 (n = 8), XX-32, XX-128,
and XpXm-128 (128 pulses with alternating signs by the same `alternate_signs` rule).  P(1) per qubit, readout-corrected
with the job's own confusion diagonal.  Readings: an over-rotation epsilon per pulse gives P(1) = sin^2(n epsilon/2)
on the XX trains (growing as n^2 before it aliases at n epsilon = pi) and the floor on XpXm-128; the floor itself,
(P1(XpXm-128) - P1(XX-8))/120 per pulse, is the incoherent per-pulse cost, to be compared with the record's x_error.
Fit epsilon_q per qubit from the three XX points by least squares with the XpXm floor subtracted; report epsilon_q,
c_q and their 68 % intervals.  Note (planner finding on the record): `x_error == sx_error` on every patch qubit of
`ibm_kingston_full_20261002T1906Z.json` — the x pulse's own error is *not measured* by the calibration, which is why
these pubs exist.  Pub duration 128 x 32 ns = 4.1 us + rep delay; shots 6000 like every other pub so the job stays
one job (`h0_submit.py` chunks mixed shot counts into separate jobs).

**P5. Hypotheses and preregistered predictions.**  Classes per circuit cell, read on the H0_ddtest ratio
R_i = X_i / X_0 with its Poisson 95 % interval (`gate_H0_ddtest.ratio_interval`, unchanged): **COLLAPSED** iff
R_hi95 < 0.25; **INTACT** iff R_lo95 > 1; **INTERMEDIATE** otherwise.  (0.25 is 3.3x below T1's pulse-cost null 0.816
and 8x above T1's measured hi95 0.031; 1 is the adoption bar.)

- **H_A — coherent accumulation of the x pulse's rotation error inside uncompensated X-only trains.**  Inside a Walsh
  window the n pulses are separated only by delays, so their over-rotation errors add linearly (n epsilon); sign
  alternation (X, -X) and XY4 cancel this at first order.  With epsilon at the RB level, epsilon_q = sqrt(6 x_error_q),
  the bound on T1's survival is 0.087 if the errors are coherent inside 8-pulse windows and random-walk across windows,
  and 3.4e-9 if they are coherent over the whole circuit (**planner arithmetic**, `ddrep_budget_20261006.json:
  H_A_bound_T1`); the measured R_T1 = 0.012 / null 0.816 = 0.014 sits between, so H_A needs either cross-window
  coherence or an x-pulse error above the aliased record value.  P4 measures epsilon directly.
- **H_B — the context-aware pass's output as such** (its staggered placement, or any interaction of that circuit
  object with the runtime that the local checks (i)–(v) cannot see).  Note: on a CZ-based Heron the pass's gate-context
  rule is inert — `_get_wire_coloring` presets colours only for `CXGate` / `ECRGate` neighbours — so T1 is "orthogonal
  Walsh-X sequences on adjacent idle qubits" and nothing else.
- **H_D — qubit-specific cost of dense driving** (a per-pulse cost far above x_error on the qubits that received the
  most pulses, 95 and 91; T2 drove 79 and 94 with 108 / 100 pulses without harm but put only 16 / 48 on 95 / 91).

| cell | H_A | H_B | H_D |
|---|---|---|---|
| T1 | COLLAPSED | COLLAPSED | COLLAPSED |
| M1 CA +/- | **INTACT** | COLLAPSED | COLLAPSED |
| M2 XX | not INTACT, and R_M2 < R_M3 | INTACT | INTACT (8 / 24 pulses on 95 / 91) |
| M3 X(-X) | INTACT | INTACT | INTACT |
| M4 CA minus {95, 91} | not INTACT (614 pulses, up to 96 on one qubit) | not INTACT (71 % of the pulses remain) | **INTACT** |
| P4 trains | epsilon_q >= 0.01 rad on >= 6 of 12 qubits, XX-128 above XpXm-128 by > 0.05 | all four at the floor (readout + n c_q) | c_95 or c_91 > 3 x_error, the others at x_error |

Reading rule (preregistered, mechanical): M1 INTACT -> H_A; M1 COLLAPSED and M4 INTACT -> H_D; M1 COLLAPSED and M4 not
INTACT -> H_B; any other pattern -> "no single hypothesis", reported as the table of classes.  The P4 trains are read
beside it as the independent measurement of H_A's parameter: the pair (circuit reading, epsilon reading) is the
result.  The M2/M3 pair measures the first-order compensation gain on the runtime timing, ln(R_M3 / R_M2) with its
interval (one-sided z > 1.645 = "compensation matters"), independent of the context-aware pass; M3 against T3 is
information on X-only-robust vs XY4 (the literature expects them comparable, C2 of the literature report).

**P6. Replication verdicts (preregistered).**  R1 *gain replicated*: T3 qualifies under the H0_ddtest adoption rule
(R_T3,lo95 > 1 and R_T3 >= 1.25).  R2 *magnitude consistent*: |ln R_T3,new - ln 2.819| <= 1.96 sqrt(sigma_new^2 +
sigma_old^2), sigma_old = (ln 3.185 - ln 2.495) / 3.92 = 0.0623 (**planner arithmetic** from
`data.decision.cells.T3.R_95`; tolerance 0.192 at the 10-02 power).  C1 *collapse replicated*: T1 is COLLAPSED.
The signed bar is read on T3 (`signed_bar`, information, both on f_hit and on f_hat_ideal = f_hit / 1.115 per owner
decision 1a).  No criterion of the gate depends on R1, R2, C1 or the mechanism reading: a measurement gate PASSES when
it is preregistered, measured, verified and consistent.

**P7. Shots, estimate, caps, and B's reserve.**  Every pub 6000 shots (P5 of prompts/24 unchanged; the power above).
Pubs: 7 cells x 2 circuits = 14 coarse + 2 readout (all-0 / all-1) + 4 trains = **20 pubs, one job**.  Execution
estimate (**planner arithmetic** with the 10-02 durations 46.42 / 46.55 us, rep delay 250 us, cal 2.196 us, train
4.1 us): 7 x (1.7785 + 1.7793) + 2 x 1.513 + 4 x 1.525 = **34.03 s**; the same arithmetic reproduces H0_ddtest's
17.2576 s exactly.  Billed has exceeded the estimate by 2.26–2.96 s per job on this account (H0_kpilot, H0_ddtest,
H0_2x2) -> expected billed about 37 s.  Caps: estimator <= 36 s (STOP above), **billed cap 45 s**.  B's reserve is
taken before A spends anything: 498 - 45 = **453 s >= 300 s** (K1's billed cap) and **>= 1.3 x 182.45 = 237.2 s**
(K1's rehearsal estimate x 1.3): both hold, A is not shrunk.  On the day: STOP if `usage_remaining_seconds` - 45 <
max(300, 1.3 x the K1 estimate recomputed on the day's record).  Information: the account's usage period is a
rolling 28-day window (literature report, table of section 1), so the 17 s of 2026-09-22 leave the window around
2026-10-20 — `ibm_account.py --check` is the source of truth, never this sentence.

**P8. Options and guards unchanged:** runtime DD off, twirling off (D8'); D9 on the patch's calibration content
(`fresh_calibration`, `calibration_fingerprint`); prereg committed before submission; dry run on the FakeKingston
snapshot must PASS; one job; counts never overwritten; no criterion constant, tolerance, decoder, convention or frozen
circuit changed.

## Steps

### A.0 — the 2x3 IBM NO-GO on K0 (about 45 min; 0 QPU s)

A.0.1. New `scripts/k0_nogo_note.py`: reads `validation/K0_2x3_2x4.json` only and writes
`reports/K0_2x3_ibm_heron_nogo.md`: title "2x3 on IBM Heron: NO-GO on the K0 analysis (a model verdict, not a
measurement)", the record label and fingerprint, routed CZ, active qubits, ALAP duration, f_ceiling_2q, the
best-patch bound, f_gates_layout, S_idle and f_idle_aware at both T2 ends, the XY4 transfer, the eps2 needed for
f = 0.05 and the factor by which the best edge misses it, the garbage expectation per circuit at 1e5 shots, and the
sentence "Every number above is computed from the calibration record named; none is a measurement on the device.
Option B (prompts/32) is the one measurement this verdict allows: the K1 pilot as an upper limit."  Also a JSON block
`data.k0_2x3_nogo` with the same fields copied verbatim into `validation/H0_ddrep.json` at assembly (A.F) so the gate
carries the verdict it was ordered with.  No number typed by hand.

A.0.2. `scripts/update_status.py`: add the `GATES` row ("H0_ddrep", "one-job replication of the XY4 gain (T0 vs T3)
and of the context-aware collapse (T1) with four mechanism cells (CA+/-, XX, X(-X), CA minus two qubits) and four
pulse-train pubs on the two k = 1 circuits; preregistered classes and reading rule (measurement gate)", "QPU").

### A.W — wait-and-poll for ibm_kingston (free metadata only; interleaved with A.1–A.4, which need no device)

A.W.1. New `scripts/h0_devicewatch.py --backend ibm_kingston --once --patch-from
data/hardware/H0_ddtest_prep/calibration_20261002T1906Z.json --out data/hardware/H0_ddrep_prep/devicewatch.jsonl`:
one metadata read (`backend.status()`, a fresh `backend.target`, `backend.properties()`), appends one JSON line
{when, status_msg, operational, pending_jobs, last_update_date, n_cz_keys_with_error, n_cz_keys_total,
patch_edges_calibrated / patch_edges_total (the edges of the patch record), patch_qubits_calibrated (of 12)}; exit 0 when `status_msg ==
"active"`, `operational`, every patch qubit and edge carries an error value, and the target has cz errors on >= 90 %
of its cz keys; exit 2 otherwise.  Note `--stage account` of `h0_ddtest_circuits.py` is NOT sufficient: the 10-06
record shows `operational: True` with `status_msg: maintenance` and zero cz errors.

A.W.2. Cadence: at most one poll per hour, and at least one per executor session, logged.  Do the 0-QPU work (A.1–A.4,
B's 0-QPU preparation that does not need the live record) between polls.  When a session ends with exit 2, hand back
"WAITING (kingston maintenance since ~2026-10-06T01:12Z; last poll <when>)" with the next command; the coordinator
re-invokes at most daily.

A.W.3. Cap and fallback: if no poll returns 0 by **2026-10-13T01:12Z** (7 days of maintenance), run the fez
preparation at 0 QPU s — `ibm_account.py --check`, `full_device_record("ibm_fez")`, `scripts/h0_patch_select.py`
(idle-aware exhaustive search on that record) and the planner-arithmetic power table X = 6000 x 0.82 x f x p_ref at the
search's predicted f (echo and T2* ends) — and STOP to the owner with: the kingston log, the fez patch and its
predicted X per cell, and the sentence that a cross-device run is a pilot, not a replication, unless X >= 150 (sigma_lnR
<= 0.115, a true 1.25 still decidable).  Do not submit anything to fez or marrakesh without a new owner decision.
B keeps polling under its own cap (B.0).

### A.1 — circuits (`scripts/h0_ddrep_circuits.py`; about 3 h to write, minutes to run; 0 QPU s)

A.1.1. Stages, mirroring `h0_ddtest_circuits.py` (import it; default `--prep data/hardware/H0_ddrep_prep`):
`account` (STOP if `usage_remaining_seconds` < 345 = 300 + 45, or kingston not `active`), `record` (full-device record,
`calibration_diff` against `data/hardware/H0_ddtest_prep/ibm_kingston_full_20261002T1906Z.json`, information),
`select` (P2), `build`, `patchcal` (D9 record of the patch).

A.1.2. `build`: T0/T1/T3 by `h0_ddtest_circuits.build_coarse` with `force_reuse` of the committed QPYs (byte equality
asserted when the patch is reproduced, else rebuilt and flagged); M2 by `dd_variant`-style code with
`dd_sequences=[XGate(), XGate()]`, ratio 4.0; `alternate_signs(out, base)` -> M1 from T1, M3 from M2;
`strip_pulses_on(out, base, hot)` -> M4 from T1 with `hot` = the two qubits with the largest
`dd.pulses_per_physical_qubit` in T1's manifest (recorded; expected {95, 91}); `dd_checks` + `dd_exactness` on all;
the three identities of P3 asserted; the four train pubs (P4) as `kind: pulse_train` manifests with the train length,
the sign pattern and the per-qubit op list; the two readout pubs as before.  Dump QPY + manifests + `index.json`.
Pub ids: `<base>_<cell>` for the 14 coarse pubs, `train_XX_8`, `train_XX_32`, `train_XX_128`, `train_XpXm_128`,
`cal_patch_all0`, `cal_patch_all1`.  Check that `h0_submit.py` (read-only) treats `pulse_train` manifests as
non-calibration pubs at `--shots`; if it does not, give the train manifests `kind: coarse_step` with
`test: "pulse_train"` and the fields `load_circuit` needs, and say so in the report — do not edit `h0_submit.py`.

A.1.3. Local prototype on `FakeKingston` with the committed 10-02 record before kingston is back (the build must not
depend on the live record for anything but D9): the build runs end to end on `--record
data/hardware/H0_ddtest_prep/ibm_kingston_full_20261002T1906Z.json`; the resulting pulse counts and the P3 identities
go into the report's "prototype on the committed record" block (not a prereg).

### A.2 — gate script (`scripts/gate_H0_ddrep.py`; about 3 h; 0 QPU s)

A.2.1. Stages `reserve`, `predict`, `prereg-md`, `assemble`, importing `gate_H0_ddtest` (`ratio_interval`, `adopt`,
`signed_bar`, the Garwood helpers of `gate_H0_kpilot`) — `gate_H0_ddtest.py` is not edited.  Constants: `CELLS =
("T0", "T1", "T3", "M1", "M2", "M3", "M4")`, `SHOTS = 6000`, `MAX_ESTIMATE_S = 36.0`, `MAX_USAGE_S = 45.0`,
`B_RESERVE_S = 300.0`, `K1_ESTIMATE_S` read from the rehearsal prereg under `data/K1_2x3_fpilot/rehearsal_committed_record/` (the
182.45 s estimate; until B.2 recomputes it on the day's record), `COLLAPSED_HI95 = 0.25`, `INTACT_LO95 = 1.0`, `R2_LNR_OLD` and
`R2_SIGMA_OLD` computed from `validation/H0_ddtest.json` at import (never typed).

A.2.2. `reserve`: the day's `ibm_account.py --check` JSON -> remaining; `fits = remaining - MAX_USAGE_S >= max(B_RESERVE_S,
1.3 x K1_ESTIMATE_S)`; write `<prep>/reserve.json`; exit 3 if not.

A.2.3. `predict`: `<prep>/prereg_<fp16>.json` in the format `h0_submit.preflight` reads (`calibration.{fingerprint,
path, last_update_date, stamp}`, `created`, `commit`, `script`), carrying: the patch and `patch_reproduced`; the 20 pubs
x 6000; the execution estimate by `h0_qpu_time.estimate` on the day's durations (STOP if > 36 s); per cell the pulses,
S_DD, null ratio; the expected excess hits per cell at f_T0 = 0.0400 (`H0_ddtest.json`) and the power line (sigma_lnR,
95 % factor, lower bound of a true 1.25); P5's class thresholds, the prediction table and the reading rule verbatim;
P6's verdict definitions with `R2_LNR_OLD`, `R2_SIGMA_OLD`; the H_A bounds of T1 recomputed on the day's record (both
ends); the reserve block; the planner's expectation line: "T3 replicates (R about 2.8); T1 collapses again; the
mechanism reading is open — the planner's own bound shows H_A at the RB-level epsilon cannot reach 0.012 unless the
errors are coherent across windows or the x pulse is worse than its aliased record value, which the trains measure."
No Aer prediction of a DD gain (P10 of prompts/24: Aer cannot show one).

A.2.4. `prereg-md`: `reports/H0_ddrep_prereg_<stamp>.md` from the JSON.  **Commit** "H0_ddrep: preregistration on
ibm_kingston calibration <fp16> (7 cells x 2 + 2 cal + 4 trains, 20 pubs x 6000, estimate <x> s, B reserve <y> s)".

A.2.5. `assemble` (`--counts <dir> [--dry-run] --out H0_ddrep`): per cell `f_pool`, 68/95 % intervals, `f_by_circuit`
(reference and mixture), `excess_hits`, `R`, `R_95`, `R_bootstrap_95`, `null_ratio`, `class`; `replication: {R1, R2
(with lnR_new, tolerance), C1, adopted, qualifying, signed_bar_f_hit, signed_bar_f_hat_ideal}`; `mechanism:
{classes, reading, M3_over_M2: {lnR, sigma, z}, M3_over_T3 (information)}`; `trains: per qubit {P1 per pub, floor,
epsilon, epsilon_68, c_per_pulse, x_error_record}` and the P4 readings; `k0_2x3_nogo` (A.0.1); readout block;
C6 deviations (information; p_ref >= 0.5); distance histograms; usage; account before/after; the dry-run flag.
Report `reports/H0_ddrep_ibm_kingston.md` (or `_dryrun.md`) with: what PASS means; prereg block; live block; the
cell table with classes; the replication verdicts; the mechanism table (predicted vs observed, the reading); the
train table; the K0 NO-GO block; honest limits (one job, one patch, one calibration; the classes are preregistered
thresholds, not fits; the reading rule names a hypothesis class, not a microscopic cause).

A.2.6. `tests/test_h0_ddrep.py`: `alternate_signs` on a toy padded circuit (every second inserted x wrapped, base x
untouched, statevector equal up to phase, start times unchanged); `strip_pulses_on` (inserted ops removed only on the
named qubits, delays restore the timeline); the M2 window-set identity on a toy schedule with one 256-ns and one
200-ns window; the class function on synthetic intervals (all three classes, both boundaries); the reading rule on
the four patterns of P5; R2 on a synthetic interval pair; the reserve arithmetic (fits / does not fit); the train
fit on synthetic P(1) with a known epsilon and floor.  `pytest -q tests`, `python scripts/check_package.py`,
`graphify update .`.

### A.3 — dry run (about 20 min; 0 QPU s; must PASS)

A.3.1. `python scripts/h0_submit.py --dry-run --prep data/hardware/H0_ddrep_prep --shots 6000 --cal-shots 6000
--max-pubs-per-job 20 --seed 11 --out data/hardware/H0_ddrep_dryrun` (on the committed-record prototype if kingston is
still down; repeat on the day's build before submission).

A.3.2. `python scripts/gate_H0_ddrep.py --stage assemble --counts data/hardware/H0_ddrep_dryrun/counts --dry-run
--out H0_ddrep_dryrun` -> `validation/H0_ddrep_dryrun.json`, `reports/H0_ddrep_dryrun.md`; K3 in its dry-run form
(prompts/21a); ratios reported against the null values with the sentence "Aer cannot show a DD gain"; the train pubs
on Aer give P(1) at the readout floor (Aer has no coherent pulse error) — state it.  STOP on any criterion failure
other than the documented dry-run forms.

### A.4 — the day kingston is back: record, patch, prereg (about 1 h; 0 QPU s)

A.4.1. `ibm_account.py --check` -> `data/hardware/H0_ddrep_prep/account_check_<stamp>.json`; `h0_devicewatch.py --once`
exit 0; `--stage record`, `--stage select` (P2), `--stage build` on the day's record, `--stage patchcal`;
`gate_H0_ddrep.py --stage reserve` (exit 3 = STOP to the owner with the numbers); `--stage predict`, `--stage
prereg-md`; commit (A.2.4).  Re-run A.3 on the day's build (`validation/H0_ddrep_dryrun.json` PASS).

### A.5 — the one submission (about 30 min wall; the QPU spend, cap 45 s billed)

A.5.1. `python scripts/h0_calwatch.py --backend ibm_kingston --once --reference data/hardware/H0_ddrep_prep/calibration_<stamp>.json
--out data/hardware/H0_ddrep_prep/calibration_watch.jsonl` (exit 3 = moved -> D10: re-run A.4 on the new content, at
most twice, then STOP).

A.5.2. `python scripts/h0_submit.py --backend ibm_kingston --prep data/hardware/H0_ddrep_prep --shots 6000 --cal-shots
6000 --dd off --twirling off --prereg data/hardware/H0_ddrep_prep/prereg_<fp16>.json --max-qpu-seconds 36
--max-pubs-per-job 20 --job-tags H0_ddrep --out data/hardware/H0_ddrep_ibm_kingston`; commit `session.json` at once.

A.5.3. `--retrieve --wait 1500` until DONE; `--status --record-calibration`; commit counts + session ("H0_ddrep: counts
retrieved, usage <u> s, retrieval fingerprint <match/moved>").  A.5.4. `ibm_account.py --check` ->
`data/hardware/H0_ddrep_ibm_kingston/account_check_after_<stamp>.json`.

### A.F — analysis and bookkeeping (about 2 h; 0 QPU s)

`python scripts/gate_H0_ddrep.py --stage assemble --counts data/hardware/H0_ddrep_ibm_kingston/counts --out H0_ddrep`
(`run_gate.py H0_ddrep`) -> `validation/H0_ddrep.json`, `reports/H0_ddrep_ibm_kingston.md`; `update_status.py`; LOG row;
commit "gate H0_ddrep: <status> (R1 <..>, R2 <..>, C1 <..>, reading <..>)".  No push.

### B — the K1 2x3 pilot as built (after A.5.4; the K1 preconditions unchanged)

B.0. Polling: the same `h0_devicewatch.py --once`, at most hourly, logged to `data/hardware/K1_2x3_prep/devicewatch.jsonl`;
A's readiness is B's readiness (the same condition: kingston `active` with cz calibration published).  Cap: if kingston
has not published cz calibration by **2026-10-20T01:12Z** (14 days of maintenance), STOP and ask the owner (K1 is not
moved to another device by this prompt).

B.1. Budget gate before anything: `ibm_account.py --check`; STOP to the owner if `usage_remaining_seconds` < max(300,
1.3 x the K1 estimate recomputed on the day's record in B.2) (owner decision 2026-10-06, second paragraph).

B.2. The resume order of the K1 LOG row, unchanged: `python scripts/gate_K0_2x3_2x4.py --live` (K0 on the day's record
must PASS; STOP otherwise); `gate_K1_2x3_fpilot.py --stage record`, `--stage build` (one circuit per invocation, ~20
min each), `--stage patchcal`, `--stage predict`, `--stage prereg-md`; commit; `--stage dryrun`; `--stage assemble
--dry-run`; then `--stage submit --live` only if the owner decision file exists and every precondition the script
checks holds (K0 PASS on the day's record, prereg committed, dry run PASS, calwatch / D9 match, estimate <= 300 s,
enough seconds).  Retrieve, `assemble`, report, LOG row, commit.  No push.  The decision is read on f_hat_ideal =
f_hit / 1.115 (decision 1a) exactly as the script does.

## Pass criteria

### Gate H0_ddrep (`validation/H0_ddrep.json`; status PASS iff D1–D8; **no criterion on R1, R2, C1, the classes or the reading**)
- D1 prereg committed before submission (`prereg_commit` < submission time); prereg = submission = retrieval
  fingerprint recorded (a retrieval move is information).
- D2 one job DONE; `usage_s <= 45`; preflight estimate `<= 36`; 20 counts files x 6000; sampler options DD off, twirling
  off; `reserve.json` present with `remaining - 45 >= max(300, 1.3 x K1 estimate)` true at the pre-submission check.
- D3 readout confusion of the patch: smallest diagonal >= 0.9.
- D4 decoder round trip over every accepted string of the 14 coarse pubs: 0 mismatches.
- D5 circuits: 14/14 coarse circuits pass `dd_checks` (i)–(v) and `dd_exactness` (max |d| < 1e-10, leakage < 1e-9);
  T0/T1/T3 byte-identical to the H0_ddtest QPYs when `patch_reproduced` (else rebuilt with the flag and the reason);
  the three P3 identities hold (M1 = T1 timing, M3 = M2 timing, M2 windows = T2 windows, M4 = T1 minus {hot}); the
  train pubs' op lists are the declared trains; all in the kingston basis.
- D6 `validation/H0_ddrep_dryrun.json` PASS on the day's build.
- D7 `data.replication`, `data.mechanism`, `data.trains`, `data.k0_2x3_nogo` complete (no missing key); the classes,
  R1, R2, C1 and the reading recomputed from the recorded intervals equal the recorded ones; `k0_2x3_nogo` fields equal
  `validation/K0_2x3_2x4.json`'s.
- D8 `pytest -q tests` and `python scripts/check_package.py` pass.

### Gate K1_2x3_fpilot: unchanged (the script's own criteria; PASS = preregistered, measured, verified, consistent).

## Outputs
- `reports/K0_2x3_ibm_heron_nogo.md` (generated), `scripts/k0_nogo_note.py`.
- `scripts/h0_ddrep_circuits.py`, `scripts/gate_H0_ddrep.py`, `scripts/h0_devicewatch.py`, `tests/test_h0_ddrep.py`.
- `data/hardware/H0_ddrep_prep/` (records, select, circuits, patchcal, prereg, reserve, devicewatch and calwatch logs),
  `data/hardware/H0_ddrep_dryrun/`, `data/hardware/H0_ddrep_ibm_kingston/` (session, counts, account checks).
- `validation/H0_ddrep_dryrun.json`, `validation/H0_ddrep.json`, `reports/H0_ddrep_prereg_<stamp>.md`,
  `reports/H0_ddrep_dryrun.md`, `reports/H0_ddrep_ibm_kingston.md`; then K1's own outputs.
- `prompts/LOG.md` rows (one per part: A.0, A.W/A.1–A.3 prototype, A.4–A.F, B), `validation/gates.md` /
  `reports/PROJECT_STATUS.md` via `update_status.py`.  Commit after each part; **no push**.

## Escalation and STOP conditions
- Kingston not `active` or the patch not fully calibrated: wait under A.W (cap 2026-10-13T01:12Z, then the fez
  preparation + STOP to the owner); B's cap 2026-10-20T01:12Z, then STOP to the owner.
- `remaining - 45 < max(300, 1.3 x K1 estimate)`, estimate > 36 s, or `usage_s` would exceed 45: STOP with the
  numbers; no resizing.  (At 498 s both hold with 453 s to spare — **planner arithmetic**; the day's check decides.)
- Fingerprint moved at calwatch or refused by the preflight: D10, at most twice, then STOP.
- Job ERROR / CANCELLED: record; no automatic resubmission; the owner decides on the retry margin.
- A dry run fails on a D-criterion: fix the analysis, re-run; never edit a counts file; two honest failures -> hand
  back with the traceback.
- The committed patch fails P2 (a) or (b): rebuild on the winner, flag `patch_reproduced: false`, continue (not a STOP).
- The mechanism reading is "no single hypothesis": report the class table; do not add cells or shots; hand back.
- If the executor believes a threshold above (0.25, 1.0, 1.25, the R2 tolerance, 36 / 45 s) is wrong: STOP and say
  so; do not change it.
- B: any K1 precondition fails -> the script's own STOP; K0 `--live` FAIL on the day's record -> STOP to the owner.

## Do-not-touch list (binding)
`scripts/h0_submit.py`, `scripts/h0_ddtest_circuits.py`, `scripts/gate_H0_ddtest.py`, `scripts/gate_K1_2x3_fpilot.py`
(its stages run as they are), `scripts/gate_K0_2x3_2x4.py`, `scripts/h0_patch_select.py`, every existing
`validation/*.json` and `data/hardware/H0_*`, `data/hardware/K0_prep`, `data/hardware/K1_2x3_prep/select.json`, every
prereg JSON once committed, every criterion constant, decoder, convention (`src/skqd/{su2,lattice,codec,reference_sim}.py`),
`proposal/`, the planner's LOG row, CLAUDE.md's status paragraph.

## LOG row (one per part)
`| 2026-10-xx | prompts/32_2x2_dd_replication_and_T1_mechanism.md <part> | <gate> | executor-opus | <outcome with the JSON's numbers> | <commits> | <open items> |`
