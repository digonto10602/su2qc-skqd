# 19 — H0 canary NO-GO: diagnostic session on ibm_fez (idle-time model, DD/twirling factorial)
executor: executor-opus   effort: high (xhigh on the second attempt); runner-sonnet may run steps E2–E4 and G1; scribe-haiku the status tables
time budget: laptop 5 h in commands of < 30 min; QPU wall time about 15 min; QPU usage cap 40 s (of 598 s left)   machine: laptop + ibm_fez (owner's go required before any submission)

> Written by planner-fable at max effort after `validation/BLOCKED.md` (canary NO-GO, 8 accepted of 267).
> The ruling and every number below are in `reports/H0_canary_planner_analysis_20260922.md` (read it first).
> prompts/07 clause (b) is in force: no 2x3 budget, no `slurm/s3_2x3.sbatch` with Heron-derived parameters, no
> main H0 submission.  This prompt spends at most 40 s of QPU time to decide between two hypotheses and to
> measure the inputs of the model that will replace the prediction.  It changes no criterion constant, no
> convention, no frozen circuit, and none of the rules D1–D11 for the production path; the sampler options
> are varied here for diagnostic jobs only, under new flags whose defaults reproduce D8 exactly.

## Failure (from validation/BLOCKED.md and validation/H0_canary.json)
- canary go rule (prompts/15 D5): accepted 8 of 267, rule >= 10 → NO-GO; the other four rules pass.
- criterion "B=0 r=1 (663 CZ): measured f vs predicted f": 0.02551 vs 0.21952, relative deviation 0.8838 (<= 0.30).
- calibration identity held (`fingerprint_match` true, retrieval diff 0 leaves): not drift.
- raw strings: 253 distinct of 267; rejections 176/78/5 = the uniform-garbage split (planner P3).

## Diagnosis (summary; the full argument is sections 2–4 of the analysis report)
The prediction (`gate_S2D.analyse_on_backend` and `AerSimulator.from_backend` in `scripts/gate_H0P.py:517`, on the
frozen QPY circuits with no schedule and no `delay`) contains gate and readout errors only.  The routed 2x2 circuit
is nearly serial (depth 1328 for 663 CZ, 43.71 us before readout) and each of the 12 qubits idles 19–42 us of it.
On the calibration record the device ran under, the idle relaxation budget (Pauli-twirled thermal relaxation over
the idle windows) is 3.323 error units (T1 part 0.755, T2 part 2.568; qubit 146 with T2 = 16 us alone 0.93),
against 2.15–2.36 units missing between prediction and measurement.  That is hypothesis **H_A**.  The competing
hypothesis **H_B** — the SamplerV2 options (DD XY4, twirling `active-accum`) were live for the first time and
are harmful — has one mechanism of the right order (twirling puts random Paulis on every accumulated-active
qubit in each of ~663 layers; up to ~1.3 units if unmerged) that cannot be computed from the repository.  Under
H_A, switching DD off makes the yield worse (31 ± 6 of 2000); under H_B it restores the prediction (374 ± 17).
The two are 5 sigma apart in either direction at 2000 shots.  H_C (gate-level excess beyond the calibration) is
bounded by the same cell.

## Fix (what this prompt delivers)
1. `scripts/h0_idle_model.py` — the idle-aware yield model (schedule + per-qubit idle windows + PTA relaxation
   budget + DD-eligible windows) for any prep directory on any calibration record; reproduces planner P1.
2. `scripts/h0_diag_circuits.py` — the diagnostic circuit set on patch 1 (`t1w`, `ramw`, the frozen canary
   circuit byte-identical, the two patch-1 readout circuits) in the H0_prep format.
3. `scripts/h0_submit.py` — flags `--dd {XY4,XX,XpXm,off}` (default XY4) and `--twirling {on,off}` (default on),
   the options record made truthful, kind `idle_test` accepted, `--prereg <json>` fingerprint identity.
4. `scripts/gate_H0_diag.py` — the preregistered analysis (criteria C1–C6 below), written and dry-run-tested
   before any submission.
5. The session: four jobs J1–J4, submit-then-retrieve with job ids on disk, J1 first, J2–J4 only if J1's usage
   is <= 10 s.  Then `validation/H0_diag.json`, `reports/H0_diag_hardware_2x2.md`, LOG, hand-back.

## Inputs
- `reports/H0_canary_planner_analysis_20260922.md` (sections 2, 6, 9), `validation/BLOCKED.md`,
  `validation/H0_canary.json`, `data/hardware/H0_ibm_fez_canary/` (session, counts, calibration records).
- `data/hardware/H0_prep/` (frozen set; `circuits/B0_ref06_k1_rep1.qpy.gz`, sha256 of the gz
  8f372da0f5e88bdc404cf148d747024510501ee2822bdd35e63bf77375e8ada9; `cal_patch1_all0`, `cal_patch1_all1`).
- `scripts/h0_qpu_time.py` (`circuit_duration_s` is the ASAP critical path — extend it per qubit, do not
  re-derive), `scripts/gate_S2D.py:analyse_on_backend` (f; note it includes the 12 measure errors),
  `scripts/h0_backends.py` (`fresh_calibration`, `calibration_fingerprint`, record format),
  `scripts/h0_submit.py` (`sampler_options`, `options_record`, `load_manifests`, `preflight`, `submit_phase`),
  `scripts/h0_build_circuits.py` (manifest format of the readout-calibration circuits, `dump_qpy_gz`,
  `transpiled_layout`, `logical_statevector`), `scripts/gate_H0P.py` (`analyse_records`, `YIELD_FACTOR`).
- prompts/15 (D4 submit-then-retrieve, D6 caps, D8 options record, D9 in prompts/17), prompts/17 (D9–D11).
- Runtime semantics verified in the installed qiskit-ibm-runtime 0.49.0: DD pads `delay` instructions and any
  idle gap longer than 2 x the sequence length (`sequence_min_length_ratios` default 2.0), one sequence per
  window, only on qubits already acted on (`skip_reset_qubits`); twirling `active-accum` twirls the union of
  qubits active so far in every twirled 2q layer; `delay` is in ibm_fez's basis (`basis_gates` of the record).

## Steps

### A. `scripts/h0_idle_model.py` (laptop, ~30 min to write, seconds to run)
A1. CLI: `--prep DIR` (default `data/hardware/H0_prep`), `--calibration RECORD.json` **or** `--backend NAME`
    (then `h0_backends.fresh_calibration` writes the record and the fingerprint as gate_H0P does), `--only IDS`,
    `--out JSON` (default `data/hardware/<prep name>/idle_model_<fingerprint16>.json`), `--md` (report path).
A2. Per circuit (QPY loaded as in `h0_build_circuits.load_qpy_gz`): ASAP schedule with the record's durations
    (cz per edge, sx/x per qubit, rz 0, barrier 0, measure excluded from the idle budget, `delay` = duration x dt);
    per active qubit: busy time, idle time, list of idle windows (a barrier synchronises like the P1 snippet);
    T = critical path before the measure layer (must equal `h0_qpu_time.circuit_duration_s` minus the measure
    duration to 1e-12).
A3. Budgets: `S_T1 = sum_windows (1 - exp(-w/T1))/4`, `S_T2 = sum_windows (1 - exp(-w/T2))/2`, per qubit and
    total; `dd_eligible` = windows with w/(4 x sx_duration) > 2.0; `S_DD = sum_eligible 4 x sx_error`;
    `S_T2_eligible`, `S_T2_ineligible`.  `f_gates` = `analyse_on_backend(...)['f']` evaluated on the record
    (write a record-backed evaluator: the same product over the circuit's cz and measure errors read from the
    record; assert it equals the target-backed value to 1e-12 when a backend is given) and
    `f_gates_only = f_gates / prod_q (1 - measure_error_q)`.
A4. Predictions per circuit with a = the sector's exhaustive garbage acceptance (reuse gate_H0P's
    `analyse_records` random-acceptance code or read it from `validation/H0P_ibm_fez.json:data.garbage_acceptance`):
    `yield_dd_off = 0.82 f_gates e^{-S_T1 - S_T2} + (1 - f) a`;
    `yield_dd_on[rho]` for rho in (0, 0.25, 0.5, 1): `f = f_gates e^{-S_T1 - rho S_T2_eligible - S_T2_ineligible - S_DD}`.
A5. Test (`tests/test_h0_idle_model.py`): on `B0_ref06_k1_rep1` with
    `data/hardware/H0_ibm_fez_canary/calibration_at_submission_20260922T1400Z.json`: T = 43.71 us (±0.01),
    S_T1 = 0.755, S_T2 = 2.568, dd_eligible = 244, S_DD = 0.317, per-qubit idle of 146 = 41.85 us, longest window
    of 146 = 25.30 us (all to 1e-3 relative; the planner's P1 table is the reference).  Run it over all 84 frozen
    circuits on that record and report the per-patch S_T2 (information for the re-plan).

### B. `scripts/h0_diag_circuits.py` (laptop, ~45 min)
B1. Patch 1 = `[117,122,123,124,125,136,141,142,143,144,145,146]`; logical i ↔ patch[i] as in the readout-calibration
    circuits (`initial_layout = patch`, `optimization_level 0`, `seed_transpiler 7`).  Window = 128 dt (512 ns at
    dt = 4 ns; verify `128 % target.granularity == 0` and against `pulse_alignment`), 85 windows (43.52 us).
B2. Circuits (12 logical qubits, 12 clbits, measure all at the end after a barrier):
    - `diag_patch1_t1w`: `x` on all; 85 x [`delay(128, unit='dt')` on all 12; `barrier`]; measure.  Expected `111111111111`.
    - `diag_patch1_ramw`: `sx` on all; 85 x [delay; barrier]; `rz(pi); sx; rz(pi)` on all (= sx^dagger up to phase);
      measure.  Expected `000000000000`.
    - `B0_ref06_k1_rep1`: copy the frozen QPY and manifest byte-for-byte; assert the gz sha256 above.
    - `cal_patch1_all0`, `cal_patch1_all1`: copied from H0_prep (sha256 asserted).
B3. Verification (no QPU): transpiled ops multiset exactly as intended (no gate merged across a delay; the
    optimizer must not touch level-0 circuits, assert it); noiseless statevector of the transpiled circuit gives
    the expected string with probability 1 − 1e-9 (as `logical_statevector` does for the cal circuits); local DD
    padding check: run `qiskit_ibm_runtime.transpiler.passes.scheduling.ALAPScheduleAnalysis` +
    `PadDynamicalDecoupling` (XY4: X, Y, X, Y) with the record's durations on `diag_patch1_ramw` and record the
    number of inserted pulses per qubit (expected 4 x 85 = 340; report the value, it is information about the
    client pass, the server pass may differ).
B4. Manifests in the H0_prep format with `kind: "idle_test"`, `expected_bits`, `n_windows`, `window_dt`,
    `window_s`, `total_delay_s`, `patch_index 1`, `physical_qubits`, `logical_to_physical`,
    `measurement_map_clbit_to_physical`, `ops`, `qpy`, `qpy_gz_sha256`; `index.json` with the same `common`,
    `frozen_set` qubit/edge lists as H0_prep (the preflight reads them) restricted to what these circuits use.
    Output dir `data/hardware/H0_diag_prep/`.

### C. `scripts/h0_submit.py` changes (laptop, ~45 min; tests in `tests/test_h0_scripts.py`)
C1. `--dd {XY4,XX,XpXm,off}` (default `XY4`; replaces `--dd-sequence`, keep the old name as an alias) and
    `--twirling {on,off}` (default `on`).  `off` → `dynamical_decoupling.enable = False`; twirling off →
    `enable_gates = False`, `enable_measure = False`.  `options_record` must report the values actually set
    (it currently hard-codes True).  Test: with no flags the record equals the canary's
    `sampler_options` in `data/hardware/H0_ibm_fez_canary/session.json` field for field (D8 unchanged).
C2. `load_manifests`: kinds `coarse_step` and `idle_test` go to the circuit list (shots from `--shots`),
    `readout_calibration` to the calibration list.  gate_H0.py must keep ignoring `idle_test` manifests
    (it filters on `coarse_step`; add a test that `gate_H0.py --counts <diag counts>` still runs on the coarse-step
    circuit alone).
C3. `--prereg JSON`: the preflight refuses submission unless the live fingerprint equals
    `JSON["calibration"]["fingerprint"]` (the idle-model output of A1 run with `--backend ibm_fez`), with the same
    diff report as D9; `--predict-from` stays optional.  Record `prereg` and its fingerprint in session.json.
C4. Job tags: `["su2qc-skqd", "H0_diag", "<commit>", "<out dir name>"]`.

### D. `scripts/gate_H0_diag.py` and the preregistration (laptop, ~1.5 h; committed BEFORE any submission)
D1. Inputs: `--prereg data/hardware/H0_diag_prep/idle_model_<fp>.json`, `--counts-J1 … --counts-J4` (the four
    session directories), `--out H0_diag`.  Reads the raw counts only; never modifies them.
D2. Per canary pub (J1–J4): accepted, yield, rejections, distinct strings, round trip (as gate_H0), the
    mixture fit c and its chi-square (planner P3 formula), and the number of times the reference string appears.
D3. Idle tests: per physical qubit, from `t1w`: P(1 survives) corrected with the same-job all-0/all-1 readout
    (J1) — for J2 use J1's readout reference and say so; from `ramw`: P(0) per qubit; implied
    `T1_meas = -T_delay/ln(P_survive)`, `T2star_meas = -T_delay/ln(2 P(0) - 1)` when P(0) > 0.5 (else "fully
    dephased", reported as an upper bound T_delay/ln(…)); for J2 the same quantities under DD (`T1_dd`, `T2_dd`).
D4. Idle-aware post-diction with measured inputs: re-run the A3 budget with `T1_meas`, `T2star_meas` (J1) and
    `T1_dd`, `T2_dd` (J2; no separate S_DD, the DD pulse cost is inside `T2_dd`) for the canary circuit; predict
    J1's and J2's yields; report the ratio measured/predicted.
D5. Criteria (all machine-checked, written into `validation/H0_diag.json`):
    - C1 every job DONE with `usage_s` recorded, each <= 30 s, total <= 40 s;
    - C2 round trip 0 mismatches over the accepted strings of J1–J4;
    - C3 decisive: J1 canary accepted N1 <= 100 (H_B rejected) or N1 >= 250 (H_B confirmed); FAIL if
      100 < N1 < 250 (inconclusive);
    - C4a `t1w` (J1): the per-qubit decay rate 1/T1_meas within [0.5, 2] x 1/T1_record for >= 10 of 12 qubits;
    - C4b `ramw` (J1): P(0) <= (1 + e^{-T_delay/T2_record})/2 + 3 sigma_binomial for >= 10 of 12 qubits;
    - C5 the D4 post-diction of J1 and of J2 within a factor 3 of the measured clean yield
      (measured yield − a versus predicted yield − a), each job separately;
    - C6 readout at 2000 shots: min confusion diagonal >= 0.9; the qubit-123 error is reported against the
      record's 0.00586 (information; RO_FACTOR 3 stays sized for the main run and is not a criterion here).
    Status PASS iff C1, C2, C3, C4a, C4b, C5, C6 all pass.  Every value also goes into the report table with its
    preregistered prediction beside it.
D6. Preregistration run: `python scripts/h0_idle_model.py --backend ibm_fez --prep data/hardware/H0_diag_prep
    --md reports/H0_diag_prereg.md` (writes the record, the fingerprint, the J1/J2 tables of section 6 of the
    analysis recomputed on the live record, the per-qubit `t1w`/`ramw` predictions, and the four submission
    commands verbatim).  Dry run of the whole chain: `h0_submit.py --dry-run --prep data/hardware/H0_diag_prep
    --shots 2000 --cal-shots 2000 --out data/hardware/H0_diag_dryrun` (Aer's `from_backend` does apply
    relaxation on explicit delays; check that the dry-run `t1w`/`ramw` per-qubit survivals agree with
    e^{-T/T1} and (1 + e^{-T/T2})/2 of the snapshot within 3 sigma — this is the local end-to-end test of D3),
    then `gate_H0_diag.py` on the dry-run counts (status will be whatever it is; the point is that it runs and
    writes the JSON with all six criteria).  `pytest -q tests`.  Commit: "prompts/19 part A–D: idle model,
    diagnostic set, option flags, gate_H0_diag, prereg on <fingerprint16>".

### STOP — hand back to the owner; nothing is submitted in this turn
Hand-back contains: the prereg report path and fingerprint; the four commands verbatim; the execution estimate
(sum of shots x (duration + rep delay) from `h0_qpu_time`, expected ≈ 5.7 s) and the billed-cost bound (≤ 4 x 2 s
+ 5.7 s); the decision table of section 6 of the analysis; the note that J3 is the cell the owner may drop
(≈ 2.6 s billed).  The owner's "go diag" authorises E1–E4 only.  If the calibration content moves before the
go, re-run D6 (D10 logic: the go stands across a rule-based re-prereg unless the owner said "single").

### E. Submission and retrieval (QPU; runner-sonnet may execute)
E1. `git status data/hardware/H0_prep data/hardware/H0_diag_prep` clean.  Preflight fingerprint = prereg fingerprint.
E2. J1: `python scripts/h0_submit.py --backend ibm_fez --prep data/hardware/H0_diag_prep --only B0_ref06_k1_rep1
    diag_patch1_t1w diag_patch1_ramw cal_patch1_all0 cal_patch1_all1 --shots 2000 --cal-shots 2000 --dd off
    --twirling off --prereg data/hardware/H0_diag_prep/idle_model_<fp>.json --max-qpu-seconds 30
    --out data/hardware/H0_diag_J1`; commit session.json at once; `--retrieve --wait 1500`; `--status
    --record-calibration`.  **Stop rule: if `usage_s` of J1 > 10 s, do not submit J2–J4; hand back.**
E3. J2 (`--only B0_ref06_k1_rep1 diag_patch1_t1w diag_patch1_ramw --dd XY4 --twirling off --out
    data/hardware/H0_diag_J2`), J3 (`--only B0_ref06_k1_rep1 --dd off --twirling on --out data/hardware/H0_diag_J3`),
    J4 (`--only B0_ref06_k1_rep1 --dd XY4 --twirling on --out data/hardware/H0_diag_J4`): submitted back-to-back,
    each session.json committed before the next submission (D4); then retrieve all three; retrieval records.
E4. Commit the four directories: "prompts/19 part E: diagnostic jobs J1–J4 on ibm_fez (job ids …, usage … s)".

### F. Analysis (laptop, minutes)
F1. `python scripts/gate_H0_diag.py --prereg … --counts-J1 data/hardware/H0_diag_J1/counts … --out H0_diag`
    (`run_gate.py H0_diag` wrapper added).  `python scripts/update_status.py`.
F2. LOG row; commit "gate H0_diag: <status>, J1 N1 = …, decision …"; push per the owner's rule.

### G. Hand-back to the planner
G1. The planner writes prompts/20 (the re-plan).  Include in the hand-back: N1–N4 with their predictions, the
    per-qubit T1/T2*/T2_dd table, the C5 ratios, the per-patch S_T2 of A5 over the 84 frozen circuits, and the
    total usage.

## Pass criteria
- `validation/H0_diag.json` status PASS with C1–C6 as defined in D5; in particular C3 decisive.
- `tests/test_h0_idle_model.py` reproduces P1 (values listed in A5); `pytest -q tests` all pass.
- The default options record of `h0_submit.py` equals the canary's (C1 test); `validation/H0_dryrun.json` and
  `validation/H0P_repro.json` regenerate identically (no regression of the production path).
- Total QPU usage of the session (sum of `usage_s` over J1–J4) <= 40 s; per job <= 30 s.
- No file under `data/hardware/H0_prep/`, `data/hardware/H0_ibm_fez_canary/` or any `counts/` directory modified.

## Outputs
`scripts/h0_idle_model.py`, `scripts/h0_diag_circuits.py`, `scripts/gate_H0_diag.py`, the h0_submit.py flags,
tests; `data/hardware/H0_diag_prep/` (circuits, manifests, index, `idle_model_<fp>.json`), `reports/H0_diag_prereg.md`,
`data/hardware/H0_diag_dryrun/`, `data/hardware/H0_diag_J{1,2,3,4}/` (session.json, counts, calibration records),
`validation/H0_diag.json`, `reports/H0_diag_hardware_2x2.md`, `prompts/LOG.md` rows, commits after D6, E2, E4, F2;
push on PASS.

## Escalation
- Any preflight refusal (fingerprint, frozen set, operational status) is a wait, not a fix; nothing is submitted.
- A job rejected or failed by the runtime: record the message, no resubmission; hand back.
- C3 inconclusive (100 < N1 < 250), or N1 <= 25 with C4 passing (garbage floor: H_C), or C4 failing (the
  record's coherence numbers do not describe the device): stop after F1, write `validation/BLOCKED.md` with the
  H0_diag table; planner at max.  Do not add jobs, shots or option variants on your own.
- 30-minute rule: no single command here should exceed 10 min; if the dry run does, use `--only` subsets.
- If the executor fails twice on the same step (e.g. the DD padding check or the level-0 transpilation), stop
  and hand back with the traceback verbatim.
