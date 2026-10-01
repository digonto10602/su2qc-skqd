# 23 — 2x2 on IBM: measure the duration levers and decide what the signed f >= 0.1 criterion needs
executor: executor-opus   effort: high (xhigh on the second attempt); runner-sonnet low for the staged Aer cells and the regressions; scribe-haiku low for the status tables
time budget: 2 days of laptop work in commands < 30 min each; **0 QPU seconds** (live IBM target reads are metadata and are permitted); Perlmutter not needed   machine: laptop CPU (i7-8750H, 62 GiB)

> Written by planner-fable on 2026-10-01.  The planner's own computations (P1–P10, with snippets) are in
> `reports/S2D_levers_planner_analysis_20261001.md`; read it first.  This prompt changes **no criterion
> constant, no convention, no decoder, no frozen circuit and no committed validation JSON**; it is a
> measurement and a recommendation.  The deliverable is gate **`S2D_levers`** (a measurement gate: PASS means
> *measured, verified, consistent*, never *affordable*; the verdict is a data block, not a criterion).

## Goal
The owner asked how to make the 2x2 leg doable on IBM.  Gate H0_diag and gate H0_model established that the
2x2 coarse step loses its clean shots to idle-time dephasing over a nearly serial 43.71-us circuit, and that the
prediction of record is Aer on the **scheduled** circuit at the **measured free-induction T2** read with the
**clean-yield** statistic (`validation/H0_model.json`: 1.05x at the T2* end, 49.58x at the echo end).  The
literature catalogue (`prompts/low_clean_fraction_techniques.md`) prices its techniques with the gate-only model
that was 15–50x off here, so each lever has to be judged by whether it shortens the scheduled duration or the idle
budget.  This prompt measures, on the best patch of ibm_kingston and with the signed chain, every lever that can
be evaluated without a QPU — best-of-N transpilation (B4), term order, fractional `rx`/`rzz` gates (B3), ALAP
scheduling with explicit delays — and reports for each: the scheduled duration, S_T1, S_T2 at both ends of the
T2 bracket, the predicted f (PTA bound and Aer prediction), the 0.1 / 0.05 bars, and the break-even ratio
r_crit = T2*/T2_echo above which f >= 0.1.  **The planner's anchors (P7) already show that on the kingston
winner the frozen canary reaches f_clean 0.080 (ASAP) and 0.104 (ALAP) at the echo end and 0.006 / 0.029 at the
fez-transferred T2* end**: duration is a factor, the patch's in-circuit T2* is the decider, and this gate turns
that unknown into one measurable threshold for the pilot of prompts/21.

### What the planner already measured (P1–P10), so that the executor confirms rather than discovers
- P1: `h0_patch_select.py` refuses on the kingston record because physical qubit **146 is uncalibrated there**
  (T1 None, T2 None, sx_error 1.0, readout 0.501); the identity embedding is skipped for coverage and the
  script misreports that as "the enumeration is wrong".
- P2: 24 transpiler seeds, default order, Heron r2 map, kingston durations: T_s 44.24–50.18 us, CZ 588–668;
  the frozen canary 47.96 us / 663 CZ on the same record; best seed 0.92x.  One transpile = 0.1 s.
- P3: the critical path is 455 CZ (30.94 us) + 532 one-qubit pulses (17.02 us at kingston's 32-ns sx): the
  one-qubit pulses are 35 % of the duration; the busiest qubit alone runs 259 CZ + 297 pulses (the packing floor).
- P4: `rzz` basis: 252 vs 256 two-qubit gates all-to-all, 584 vs 588 routed (−1.6 %, **no "f → √f"**); every rzz
  angle is 0.5π (580) or 0.058π (4), inside (0, π/2].  `rx` cuts the one-qubit pulse layers 520 → 398 (−23 %).
  Neither offline snapshot has `rzz`/`rx`: the durations and errors come only from the live fractional target.
- P5: all 720 term orders at one seed: T_s 35.78–51.52 us (default 44.24); the shortest orders route through
  15 active qubits, so the scan's objective must be the idle-aware f, not T.
- P6: PTA on the kingston winner reproduces the survey (0.056220) and the owner's "halved" figure (0.11759);
  PTA r_crit(0.1) exists only at half duration (0.754).
- P7: Aer, kingston winner, 2000 shots: echo ASAP f_clean 0.0797, echo ALAP 0.1039, r = 0.5 ASAP 0.0459,
  r = 0.174 ASAP 0.0059, r = 0.174 ALAP 0.0287.  Aer/PTA 1.42x at the echo end.  66–81 s per 2000 shots.
- P9: "diag last / dropped" is 8 CZ of 618 — not a lever.  P10: garbage saturates both sectors above ~20.5k shots.

## Inputs
- `reports/S2D_levers_planner_analysis_20261001.md` (P1–P10 and snippets); `prompts/low_clean_fraction_techniques.md`
  (B1, B3, B4, C22 only); `reports/H0_replan_planner_analysis_20260922.md` (sections 3–5);
  `data/H0_replan_owner_decisions.md` (D8', D1', D5', C2', C3', H0P-Y').
- JSON: `validation/H0_model.json` (`data.t2_override_table`, `data.C1_estimator_validation`), `validation/S2D_idle.json`
  (`data.t2_bracket`: per-qubit ratios, fallback 0.174), `data/S2_duration_compare.json` (`circuits["exact|frozen|B0_ref06_k1_rep1"]`,
  `rescheduling_headroom`), `data/H0_device_survey_live_20260930.json` (`devices[2].patch_select.winner`),
  `data/hardware/device_survey_20260922/ibm_kingston_20260930T2255Z.json` (the committed kingston record),
  `validation/S2.json` (`data.2x2`), `data/ionq_2x3_feasibility_20261001.json` (`results["2x2|..."]`),
  `data/hardware/H0_prep/circuits/B0_ref06_k1_rep1.{json,qpy.gz}` (read only).
- Code (read before writing): `scripts/h0_patch_select.py` (`search`, `enumerate_embeddings`, `circuit_ops`,
  `relabel`, `score_patch`, `rank_key`, `record_covers`), `scripts/h0_device_survey.py` (`full_device_record`,
  `patch_search_without_the_incumbent`, `d3_budget`, `d3pp_budget`, `frozen_durations`, `ideal_p`),
  `scripts/h0_backends.py` (`fresh_calibration`, `calibration_record`, `backend_from_record`, `calibration_fingerprint`,
  `resolve_backend`), `scripts/gate_H0P.py` (`schedule_circuit`, `apply_t2_override`, `clean_statistics`,
  `random_acceptance`, `load_circuit`, `load_manifests`), `scripts/gate_H0_model.py` (`chunk_seed`, `geometry`,
  `decode_histogram`, `postdiction` — the seeded-chunk and clean-statistic pattern), `scripts/h0_idle_model.py`
  (`schedule`, `budgets`, `f_on_record`, `predictions`), `scripts/h0_support_plan.py` (`f_from_calibration`,
  `n4_of_sector`), `scripts/h0_build_circuits.py` (`step_gates`, `repeated_coarse_step`, the leak-free verification),
  `src/skqd/idle.py` (`instruction_duration_s`, `schedule_asap`, `idle_budget`, `effective_t2`), `src/skqd/coherence.py`
  (`uniform_record`, `packing_bound`), `src/skqd/hardware.py` (`transpiled_layout`, `logical_statevector`),
  `src/skqd/krylov.py` (`apply_groups`, `term_groups`, `ideal_sector_distribution`), `src/skqd/hamiltonian.py`
  (`Terms.groups`: keys `diag`, `hop{l}`, `plaq{p}` — the same names as `CircuitFactory.diag_gates/hop_gates/plaq_gates`),
  `src/skqd/skqd.py` (`clean_fraction_mixture`, `reference_string_test`, `exact_support`, `READOUT_FACTOR`),
  `scripts/ibm_account.py` (`open_service`, `--check`), `tests/test_h0_patch_select.py`, `tests/test_idle.py`.
- Environment: qiskit 2.5.2 / qiskit-aer 0.17.2 / qiskit-ibm-runtime 0.49.0.  The fractional translation plugin is
  registered as `ibm_dynamic_and_fractional` (`qiskit_ibm_runtime.transpiler.plugin.IBMDynamicFractionalTranslationPlugin`;
  it appends `FoldRzzAngle` when `rzz` is in the target); a fractional backend object is
  `QiskitRuntimeService().backend("ibm_kingston", use_fractional_gates=True)`.

## Planner decisions carried by this prompt
- **Device and patch.**  ibm_kingston, the survey winner's patch as the anchor; the scan re-selects the patch per
  candidate circuit by the idle-aware objective (rule R1', `h0_patch_select` unchanged in its objective and
  tie-break) on a **fresh** live full-device kingston record read in this step.  ibm_fez / ibm_marrakesh are not
  re-surveyed (the 2026-09-30 survey ranks them 3.5x and 12x below kingston in PTA f).
- **The chain.**  Every prediction row: PTA bound (`skqd.idle`) and Aer on the scheduled circuit
  (`AerSimulator.from_backend` of a FakeKingston base carrying the record, `backend_from_record` strict), at the
  echo end and at uniform transferred ratios r ∈ {1, 0.5, 0.25, 0.174} of the record's T2 (`apply_t2_override`),
  read with the clean-yield statistic (`reference_string_test` and `clean_fraction_mixture`, both reported).  The
  transferred ratios are labelled as a planner construction (fez patch-1 measured 0.070–1.209, median 0.153;
  9-measured fallback 0.174); nothing in this prompt fits or chooses a T2*.
- **Options.**  D8' (DD off, twirling off) for every prediction; DD appears only as the PTA ceiling at rho = 0 with
  the record's pulse cost S_DD, labelled "ceiling, not a prediction".
- **Term order is in scope** as a lever because P5 shows it is the largest compile-level one, on the condition that a
  reordered family is verified exactly (statevector against `apply_groups` in the new order), leak-free, and its
  reach of the exact 99.9 % support and its k = 1 p_ref are recomputed and reported.  Whether to adopt it is the
  owner's signature, not this gate's.
- **Fractional gates are measured, then carried only if they pay**: if the scheduled duration of the fractional
  transpilation of the best candidate is not at least 5 % shorter than its cz/sx transpilation on the live
  durations, the fractional rows are recorded in the compile table and dropped from the Aer table (the reason printed).
- **Not in this prompt**: re-synthesis of the structured terms (target choice, control minimisation), codec/layout
  changes (re-open E1–E3), DD cells (pilot, preregistered), any submission, 2x3 on IBM (one computed line only).

## Steps

### A. `scripts/h0_patch_select.py`: the uncovered-incumbent case (about 1 h)
A1. In `search()`, after `by_set` is built: if `incumbent_set` is not in `by_set`, look it up in `skipped`
    (compare `physical_qubits`).  If it is there, set `incumbent = None`, add
    `out["incumbent_unscorable"] = {"physical_qubits": [...], "reason": <the record_covers reason>}`, skip the
    `h0_idle_model` consistency check (record `consistency_with_h0_idle_model = {"ok": None, "reason": ...}`), and
    make every `gain` entry that divides by the incumbent `None`.  If it is in neither list, raise exactly as now
    (that is the enumeration bug the message describes).  Add a module-level docstring line saying so.
A2. `finding_text`, `report_text`, `build_stability`, `build_finding`: None-safe for `incumbent is None` (print
    "incumbent not scorable on this record: <reason>" instead of the comparison sentences).
A3. Tests (`tests/test_h0_patch_select.py`): (i) on the committed kingston record the search completes, `incumbent is
    None`, `incumbent_unscorable.reason` contains "146" and "T1_s", `best.physical_qubits ==
    [82, 83, 96, 102, 103, 104, 105, 106, 107, 117, 125, 126]` and `best.f_dd_off == 0.05622012608266227` to 1e-12
    (the survey's fallback result: this is the check that the fixed path and the fallback are the same computation);
    (ii) the existing tests pass unchanged (the fez records still have a scorable incumbent, every committed number
    identical).  `python scripts/h0_patch_select.py --calibration data/hardware/device_survey_20260922/ibm_kingston_20260930T2255Z.json --out data/S2D_levers/patch_select_ibm_kingston_20260930.json --md reports/S2D_levers_patch_select_ibm_kingston_20260930.md`
    (about 2 min) must now run to completion.  `h0_device_survey.py` is not edited (its fallback stays as the record of
    how the survey was made).

### B. Live reads (about 30 min; metadata only)
B1. `python scripts/ibm_account.py --check` (the account and the reachable devices; stop and report if kingston is not
    reachable — then run everything below on the committed record and mark the fractional rows "not measured").
B2. A fresh full-device kingston record through `h0_device_survey.full_device_record("ibm_kingston")` (it calls
    `fresh_calibration`, i.e. `backend.refresh()` first — a NEW backend object per read, never a cached one), written to
    `data/hardware/S2D_levers_<stamp>/ibm_kingston_<stamp>.json`; record its fingerprint and `calibration_diff` against
    the committed 20260930T2255Z record (number of leaves moved, families).
B3. The fractional target: `svc.backend("ibm_kingston", use_fractional_gates=True)` (a separate object); write
    `data/hardware/S2D_levers_<stamp>/ibm_kingston_fractional_<stamp>.json` with `basis_gates`, and for every qubit
    `rx_duration_s`, `rx_error`, for every coupling edge `rzz_duration_s`, `rzz_error` (from
    `target["rx"][(q,)]`, `target["rzz"][(a,b)]`; None recorded as None, never defaulted), plus `last_update_date`.  If
    the target has no `rzz`/`rx`, record that and skip D.  Also print the `cz` and `sx` durations of the same target so
    the two reads are shown to be the same calibration (fingerprint of the plain blocks equal to B2's, or the diff).

### C. The scan (`scripts/gate_S2D_levers.py --stage scan`, about 1 h of compute in 20-min commands)
C1. Candidates: the B = 0 reference-6 k = 1 exact coarse step (`repeated_coarse_step`, the canary's parameters), built
    in every term order of {diag, hop0, hop1, hop2, hop3, plaq0} (720) and transpiled on the Heron r2 coupling map
    (`FakeKingston().coupling_map`; assert it equals the live record's edge set) with basis rz/sx/x/cz, level 3, seeds
    0..N−1 with **N = 8** (5760 transpiles, about 10–20 min; `--seeds` to change).  Per candidate record: order, seed,
    n_cz, n_1q, depth, cz layers, active qubits, and the ASAP schedule on a **uniform kingston-like record**
    (`coherence.uniform_record(156, edges, t_2q=68e-9, t_1q=32e-9, t_ro=2.18e-6, T1=<record median T1>, T2=<record median T2>)`):
    T_s, busy_max (packing floor), S_T1, S_T2, and the proxy f_proxy = f_gates(uniform mean cz / readout errors of the
    record) x exp(−S_T1 − S_T2).  Write `data/S2D_levers/scan.json` (all rows) and print the top 20 by f_proxy, by T_s and
    by n_cz.  **Expected**: the default order at seed 2 reproduces P2/P5 (44.24 us, 588 CZ, 12 active) and the order
    (plaq0, hop2, diag, hop1, hop3, hop0) at seed 2 gives 35.78 us, 629 CZ, 15 active — stop if either differs (the
    engine or the transpiler changed).
C2. `--stage select`: for the as-is frozen canary and for the top **K = 8** candidates by f_proxy (plus the best by T_s
    and the best by n_cz if not already in), run the exhaustive embedding search on the **fresh** kingston record
    (`enumerate_embeddings` / `record_covers` / `score_patch` / `rank_key` of `h0_patch_select`, the PTA echo objective;
    about 2 min per candidate), keep the winner mapping and its PTA score; also score every candidate on the survey
    winner's qubits when its pattern is the canary's tree.  Write `data/S2D_levers/select.json`.
C3. Rows of the lever table (ids fixed here): `L0_asis_asap` (frozen canary relabelled on its winning embedding),
    `L0_asis_alap` (same, ALAP), `L1_seed` (default order, best seed by the selected PTA f), `L2_order` (best (order, seed)
    by the selected PTA f), `L3_rx` (L2's circuit transpiled with the fractional target, part D; or L1's if L2 is not
    adopted), `L4_all` (the best of L1–L3 scheduled ALAP), plus `L0_asis_dd_ceiling` (PTA only, rho = 0).  Every row's
    circuit is written as `data/S2D_levers/circuits/<row>.qpy.gz` (QPY version 13, as prompts/22 did) with a manifest
    (order, seed, mapping, n_cz, T_s, pattern edges).

### D. Fractional transpilation (`--stage fractional`, about 2 h including code)
D1. `augment_target(base_backend, fractional_json)`: add `RXGate(Parameter("t"))` on every qubit and
    `RZZGate(Parameter("t"))` on every edge of the fractional JSON to a FakeKingston target already carrying the record
    (`backend_from_record`), with `InstructionProperties(duration, error)` from the JSON (`Target.add_instruction`).
    `fractional_record(record, fractional_json)`: a copy of the plain record with `rx_duration_s`/`rx_error` under each
    qubit and `rzz_duration_s`/`rzz_error` under each edge, `record_kind = "fractional"` (its fingerprint is a different
    record's, which is correct — the plain record's fingerprint and D9 are untouched).
D2. Additive durations in `src/skqd/idle.py:instruction_duration_s`: `rx` → `qubits[q]["rx_duration_s"]`, `rzz` → the
    edge's `rzz_duration_s`, each raising the existing KeyError when the key is absent; regression in `tests/test_idle.py`:
    the frozen canary on the committed fez record still gives T_s 4.3708e-05, S_T1 0.7552952713856562,
    S_T2 2.5675961961706695 to 1e-12 (the C7 anchor of gate S2_2x4), and a 2-qubit toy circuit with one rzz and one rx
    schedules to their recorded durations.  Additive keyword in `scripts/h0_support_plan.py:f_from_calibration`:
    `two_qubit_errors={"cz": cz_error}` (default: today's behaviour bit for bit) so that a fractional circuit's f_gates
    multiplies the `rzz` edge errors as well: f_gates = Π_{cz, rzz} (1 − ε_edge) x Π_meas (1 − ε_ro); one-qubit errors
    stay out of f_gates as in gate S2D (`f_including_1q_errors` reported next to it).
D3. Transpile the L2 (or L1) IR with `transpile(qc, backend=augmented_base, optimization_level=3, seed_transpiler=<its seed>,
    translation_method="ibm_dynamic_and_fractional")` and, as the control, the same with the plain base; record ops,
    the rzz angle histogram (every |angle| in [0, π/2] after `FoldRzzAngle`: criterion C5), T_s on the fractional record
    (ASAP), f_gates, and the duration ratio fractional / plain.  If the fractional target lacks `rzz` or `rx`, or the
    ratio is > 0.95, record and drop L3 from part E (print why).  The embedding search for L3 runs on the fractional
    record (its idle windows depend on the rx/rzz durations).

### E. Predictions (`--stage aer --row <id> --ratio <r> --chunk <i>`, about 90 min of compute in ≤ 10-min commands)
E1. For every row of C3 except the DD ceiling: PTA (`idle.idle_budget` with `t2_s = r x T2_record` per active qubit; T1
    from the record) at r ∈ {1, 0.5, 0.25, 0.174}, S_DD and the rho = 0 ceiling; r_crit(0.1) and r_crit(0.05) by bisection
    on log r (report "none" when f(r = 1) < target).  Also the PTA row at the per-qubit **fez** ratio table transferred by
    logical role (`validation/S2D_idle.json: data.t2_bracket.per_qubit_ratio` keyed by the frozen physical qubit, mapped
    through the candidate's logical→physical map; fallback 0.174) — labelled "fez table transferred, information".
E2. Aer: `backend_from_record(fresh record, base=FakeKingston(), strict=True)` (planner-verified on the committed
    record: qubit 146 is None in both, the fingerprint round-trips), `apply_t2_override` for r ≠ 1 on the row's active
    qubits, `transpile(circuit, backend=base, optimization_level=0, scheduling_method="asap"|"alap", seed_transpiler=7)`
    with `schedule_circuit`'s assertion that no non-delay op changed, `AerSimulator.from_backend(base, seed_simulator=s)`,
    **4000 shots per cell as 2 chunks of 2000 with `chunk_seed` (seed + chunk x 2000: consecutive seeds are NOT independent,
    `gate_H0_model.chunk_seed`)**; cells whose clean reference hits are below 20 get two more chunks.  Counts are written
    once to `data/hardware/S2D_levers_<stamp>/aer/<row>_r<r>_<sched>_chunk<i>.json` and refused rather than re-drawn.
    Read every cell with `reference_string_test` (f_clean, reference hits, garbage expectation) and `clean_fraction_mixture`
    (f_clean, w, profile interval); C6 checks the two agree.  Expected first cells (P7 on the committed record, 2000 shots,
    seed 11): L0_asis_asap r = 1: 221 accepted / 116 reference hits, f_clean 0.0797; L0_asis_alap r = 1: 309 / 151, 0.1039 —
    reproduce these two on the committed record before the fresh-record runs (C3).
E3. r_crit by Aer: log-linear interpolation of ln f_clean(mixture) against ln r on the grid, labelled "interpolated";
    the PTA r_crit beside it.
E4. For the recommended row only: the PTA over all 28 r = 1 circuits of the family on the selected patch (mean and
    worst f at r = 1 and r = 0.174; the 0.1 / 0.05 bars read on both), and Aer at r = 1 and r = 0.174 for
    `B0_ref06_k4`, `B1_ref00_k1` and `B1_ref00_k4` (4000 shots each).

### F. The family check for a reordered step (`--stage family`, about 30 min)
F1. For the recommended order (and for L2 if different): all (sector, reference, k = 1..4) circuits built with that order,
    transpiled with the row's seed on the Heron map; **structure identity** (are n_cz, depth and the pattern identical across k
    and references? report per circuit); exactness: the noiseless statevector of each transpiled circuit
    (`logical_statevector`) against `apply_groups([groups[name] for name in order], basis_vector(ref), k dt)` on the
    codewords, max |Δ| < 1e-10 and leakage < 1e-9 (C4); the ideal sector distributions; reach of the exact 99.9 % support
    (`exact_support(|ground state|^2, 1e-3)` per sector, states with p ≥ 1e-3 in at least one circuit of the family: compare
    with the default family's reach computed the same way); p_ref of every k = 1 circuit beside the default family's
    (0.8833 / 0.8894 at 2x2); the D3' N4 and D3''-H0 budgets at f(r = 1) and f(r = 0.174) of the row with
    `h0_device_survey.d3_budget` / `d3pp_budget` logic on the row's durations (information).

### G. Assemble, report, bookkeeping (about 2 h)
G1. `--stage assemble` → `validation/S2D_levers.json` and `reports/S2D_levers_2x2_kingston.md`; `python scripts/run_gate.py
    S2D_levers` runs the assemble stage.  Report sections: what PASS means; the live-read block (fingerprints, diff);
    the compile table (every row: order, seed, n_cz, n_1q, depth, CZ layers, active qubits, T_s, busy_max, idle summed,
    duration ratio to L0); **the deciding table** (per row and schedule: S_T1, S_T2 at r = 1 and r = 0.174, PTA f and Aer
    f_clean at the four r, the 0.1 / 0.05 bars at each, r_crit PTA and Aer); the DD ceiling line; the family check; the
    C22 paragraph with P10's saturation shots computed by the script; the 2x3 line (f_gates = Π over 5477 CZ at the
    record's mean CZ error, computed); the IonQ line from `data/ionq_2x3_feasibility_20261001.json`; honest limits (section
    4 of the planner analysis, verbatim with the JSON's numbers); the verdict block; criteria.
G2. The verdict block `data.verdict`: `duration_ratio_best` (T_s of the best row / T_s of L0 on the fresh record),
    `duration_halved_reachable` (= ratio ≤ 0.5), `best_row`, `f_aer_echo_best`, `f_aer_transfer_0.174_best`,
    `meets_0.1_at_echo` / `meets_0.05_at_echo` / `meets_0.1_at_transfer_0.174` / `meets_0.05_at_transfer_0.174` (Aer,
    mixture), `r_crit_0.1 = {"pta": .., "aer_interpolated": ..}`, `r_crit_0.05`, `recommendation` (one paragraph generated
    from these fields: which row, ALAP with explicit delays, whether the family changes, and that the pilot's `ramw` on the
    selected patch — about 1 s of QPU, prompts/21 — is read against r_crit; if `meets_0.1_at_transfer_0.174` is false the
    paragraph says plainly that f ≥ 0.1 on IBM is conditional on a T2*/T2 ratio above r_crit on that patch, and names the
    IonQ line as the alternative with its own idle caveat).
G3. `pytest -q tests`, `python scripts/check_package.py`, `graphify update .`; append
    `("S2D_levers", "2x2 duration levers on ibm_kingston: compile/schedule levers measured, f predicted at both T2 ends, r_crit (measurement gate; no budget criterion)", "laptop")`
    at the end of `GATES` in `scripts/update_status.py`; `python scripts/update_status.py`; LOG rows; commits:
    "h0_patch_select: incumbent not covered by the record is a device fact, not an enumeration error",
    "skqd.idle / h0_support_plan: additive rx and rzz durations and errors", "gate S2D_levers: <status> (best row <id>,
    duration ratio <x>, f_aer echo <..>, transfer <..>, r_crit <..>)".  Push per the owner's rule.

## Pass criteria (gate S2D_levers; all machine-checked in `validation/S2D_levers.json`)
- C1 patch selection: on the committed kingston record the fixed `search()` completes with `incumbent is None`, the
  reason naming qubit 146 and `T1_s`, and `best.physical_qubits` / `best.f_dd_off` identical (1e-12) to
  `data/H0_device_survey_live_20260930.json: devices[2].patch_select.winner`; on
  `data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json` the result is identical to `data/H0_patch_select.json`
  (best patch, incumbent f, gain to 1e-12).
- C2 live reads: the fresh kingston record has `missing_errors == []` (qubit 146's values are recorded, never defaulted;
  if its `T1_s` is None it is simply not scorable) and its fingerprint and diff against the committed record are recorded;
  the fractional read is recorded (present or absent), with the plain-block fingerprint equal to the fresh record's or the
  diff listed.
- C3 anchors: (i) the frozen canary relabelled on the survey mapping, scheduled on the **committed** kingston record,
  reproduces T_total 5.0144e-05, S_T1 0.49389348458842963, S_T2 0.9954977738711279, f 0.05622012608266227 to 1e-9
  relative; (ii) the scan reproduces P2/P5 (default order, seed 2: 588 CZ, 44.24 us, 12 active; order (plaq0, hop2, diag,
  hop1, hop3, hop0), seed 2: 629 CZ, 35.78 us, 15 active) on the uniform record of C1; (iii) the two P7 Aer cells on the
  committed record at 2000 shots, seed 11 (ASAP: 221 accepted / 116 reference hits; ALAP: 309 / 151) are reproduced —
  identical counts on this stack (same seed, circuit and noise model), or, if any count differs, f_clean(reference) within
  25 % of 0.0797 / 0.1039 with the qiskit / qiskit-aer / qiskit-ibm-runtime versions and the differing counts recorded.
- C4 every row's circuit and every circuit of part F: leakage < 1e-9 and max |Δ| against the exact coarse state in that
  row's term order < 1e-10 on the codewords; routing ancillas back in |0> (that is what `logical_statevector` enforces).
- C5 fractional rows: every rzz angle in [0, π/2] after transpilation; the fractional circuit passes C4; the fractional
  record's rx/rzz leaves are all non-None on the row's active qubits and edges (else the row is marked not measured, which
  is not a failure).
- C6 estimator consistency on every Aer cell with ≥ 20 reference hits: |f_clean(mixture) − f_clean(reference)| /
  f_clean(reference) ≤ 0.25 (the H0_model C1 tolerance); chunks strided by their shot count.
- C7 scheduling changes no non-delay op (the `schedule_circuit` assertion) and the scheduled duration agrees with
  `h0_qpu_time.circuit_duration_s` to 1e-12 on every row; for every ASAP row the PTA budget computed from the explicit
  delay windows equals `idle_budget` on the unscheduled circuit to 1e-9 (P7: S_T1 0.4938, S_T2 0.9954 = P6); for every
  ALAP row the delay-window budget with the leading delays (before a qubit's first gate) excluded and included are both
  recorded next to the ASAP value.
- C8 family (part F): the reordered family's reach of the exact 99.9 % support of each sector ≥ the default family's
  reach; max |Δ| of C4 over all its circuits; p_ref of its k = 1 circuits reported (information; a value < 0.5 is flagged
  "weakens C3'", not failed).
- C9 `pytest -q tests` all pass; `python scripts/check_package.py` OK.
- Status PASS iff C1–C9.  **No criterion on any f, duration ratio or r_crit**: those are the verdict fields.

## Outputs
`scripts/h0_patch_select.py` (A1–A2), `tests/test_h0_patch_select.py` (+2 tests), `src/skqd/idle.py` (D2, additive),
`scripts/h0_support_plan.py` (D2, additive keyword), `tests/test_idle.py` (+2 tests), `scripts/gate_S2D_levers.py`,
`tests/test_s2d_levers.py` (the augment/fractional-record helpers, the verdict logic on a synthetic table),
`data/hardware/S2D_levers_<stamp>/` (records, fractional leaves, Aer counts — committed), `data/S2D_levers/*.json`
(scan, select, compile, family fragments — committed; `scan.json` may be large: keep every row but only the fields of C1),
`data/S2D_levers/circuits/*.qpy.gz` (the rows' circuits, QPY v13), `data/S2D_levers/patch_select_ibm_kingston_20260930.json`,
`reports/S2D_levers_patch_select_ibm_kingston_20260930.md`, `validation/S2D_levers.json`,
`reports/S2D_levers_2x2_kingston.md`, `scripts/update_status.py` (+1 row), `prompts/LOG.md` rows (executor's),
`validation/gates.md` / `reports/PROJECT_STATUS.md` regenerated.  Push: yes on PASS per the owner's rule.

## Time budget per command (this laptop; planner-measured where stated)
| command | expected | limit |
|---|---|---|
| A3 patch-select on the kingston record | about 2 min (survey: 1454 embeddings) | 30 min |
| B1–B3 live reads | 1–3 min | 30 min |
| C1 scan, 720 orders x 8 seeds | 10–20 min (P2/P5: 0.1–0.2 s per transpile + schedule) | 30 min (split by seed with `--seeds a b`) |
| C2 select, 10 candidates | about 20 min (2 min each) | 30 min (split by candidate) |
| D3 fractional transpile + verify | about 2 min | 30 min |
| E2 one Aer cell (2 chunks x 2000 shots) | about 2.5 min (P7: 66–81 s per 2000) | 10 min; ≤ 6 cells per command |
| E4 the 28-circuit PTA + 3 Aer circuits x 2 ends | about 20 min | 30 min |
| F1 family: 28 circuits transpiled + statevectors | about 5 min | 30 min |
| pytest default | < 8 min | — |
If any command exceeds 30 min: stop it, split it (per seed range, per candidate, per cell), record the split in the LOG,
and never reduce a tolerance, a shot count or a vector count to make it fit.

## Honest limits (to be stated in the report verbatim, with the numbers from the JSON)
- The transferred-T2* rows are a planner construction (uniform ratios; the fez table by logical role); T2* is qubit-specific
  and need not scale with the echo T2.  Only the `ramw` pub of the pilot on the selected patch (prompts/21, D5') replaces it.
- Aer's dephasing on a delay is exponential; the free-induction decay over short windows may be closer to Gaussian — the
  pilot's two window lengths exist for that reason.
- The H0_model post-diction (1.05x) used ASAP scheduling against a hardware run whose server-side schedule is not on record;
  explicit delays in the submitted circuits remove that ambiguity for the next run.
- A reordered coarse step is a new family; this gate verifies it, the owner signs it (amendment), and no freeze happens here.
- 2x3 on IBM: the computed gate-only product over the 5477 routed CZ at this record's mean CZ error (printed) leaves no
  duration lever anything to rescue.  IonQ for 2x2: gate-only 0.216–0.303 meets the bar; the serial-idle estimate puts Aria
  at 0.0506 / 0.0810 (below 0.1, at the 0.05 worst bar) and Forte is not computable without gate times — the vendor spec of
  amendment 01 item 4 decides.
- At 2x2 the sectors saturate from garbage above about 20.5k shots (C22, P10): no SKQD energy at 2x2 is a hardware claim;
  configuration recovery is excluded at 2x2.

## Escalation
- Kingston unreachable or the account check fails: run everything on the committed record, mark the fractional rows "not
  measured", say so in the report; do not stop.
- `backend_from_record` strict check fails on the fresh record: report the `calibration_diff`; if the only differing leaves
  are qubit 146's None vs a base value, pass `base` with its qubit 146 properties set to None (assigned list) — never a
  defaulted T1/T2.
- C3(ii) differs: the engine or the transpiler changed under this prompt — stop and report before measuring anything else.
- C4 fails for a reordered circuit while the default order passes: the IR assembly order and the `apply_groups` order
  disagree — check that both lists are the same permutation of `Terms.groups` keys; do not switch to a dense unitary.
- C6 fails on a cell: re-check the chunk seeds (strided, not consecutive) and the T2 override reaching the target
  (`apply_t2_override`'s own check); two honest failures → `validation/BLOCKED.md` with the cell's counts file named.
- Any Aer cell above 10 min: split by chunk; above 30 min for one chunk: stop and report the per-shot cost.
- Two honest failures on the same step: stop and hand back with the traceback verbatim.

## Do-not-touch list (binding)
`data/hardware/H0_prep`, `data/hardware/H0_*` (read only), every existing `validation/*.json`,
`data/H0_device_survey_live_20260930.json` and the survey records, `src/skqd/{su2,lattice,codec,reference_sim}.py`,
every criterion constant and decoder, `scripts/h0_device_survey.py`, `scripts/h0_submit.py`, `proposal/`, CLAUDE.md's
status paragraph (the scribe does it), the planner's LOG row.  `src/skqd/idle.py` and `scripts/h0_support_plan.py` are
touched additively only (D2) with the committed-record regressions; `scripts/h0_patch_select.py` gets the A1–A2 change
only, with every committed fez number reproduced (C1).
