# 21 — The ibm_kingston pilot: in-circuit T2*/T2_echo on the selected patch, and the direct f_clean of the best schedulable signed circuit (gate H0_kpilot); part 0 applies the C6 ruling to S2D_levers
executor: executor-opus   effort: high (xhigh if a STOP fires and the cause is not obvious); runner-sonnet low for the Aer prediction cells and the retrieval polling; scribe-haiku low for the status tables and the LOG rows
time budget: 1 day of laptop work in commands < 30 min each; **QPU: one job, execution estimate ≤ 30 s (`--max-qpu-seconds 30`), billed usage expected ≈ 12 s, hard cap 60 s billed**; Perlmutter not needed   machine: laptop CPU (i7-8750H, 62 GiB) + ibm_kingston (open plan, instance `open-instance`)

> Written by planner-fable on 2026-10-02 under the owner's instruction of the same day: *"run the short kingston
> pilot to measure it, send c6 to planner, do not push until it is settled."*  The C6 ruling is
> `reports/S2D_levers_C6_ruling_20261002.md` (part 0 below applies it).  **Nothing in this prompt is pushed**;
> every commit is local and the push stays the owner's call.  No criterion constant, convention, decoder, frozen
> circuit of `data/hardware/H0_prep` or committed validation JSON other than the re-assembled
> `validation/S2D_levers.json` is changed.  Account facts read on 2026-10-02 10:48 local (0 QPU s): only
> `open-instance` is visible; ibm_fez / ibm_kingston / ibm_marrakesh operational (kingston 1 pending job); usage 17 s
> of 600 s, period ending 2026-10-02T16:48:25Z after which the allowance renews; the 400-minute allocation is not
> visible yet — **the pilot is written for the open instance and fits either period**.

## Goal
Gate S2D_levers (`validation/S2D_levers.json: data.verdict`) turned the 2x2-on-IBM question into one measurable
threshold: with the best schedulable circuit of the **signed** family (`L1_seed_alap`: default term order, seed 2,
ALAP with explicit delays, 588 CZ, T_s 44.24 us on the kingston patch [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94,
95]) Aer predicts f_clean **0.2170** at the record's Hahn-echo T2 and **0.0312** at the fez-transferred ratio 0.174,
and f ≥ 0.1 needs an in-circuit T2*/T2_echo ratio **r ≥ r_crit = 0.3285** (`data.verdict.r_crit_0.1_signed_family.
aer_interpolated.value`; the reordered L4_all row has 0.3302 and 0.2426 / 0.0278, i.e. no better at the deciding
end).  The only measurement of that ratio in the project is on ibm_fez patch 1 (`validation/S2D_idle.json:
data.t2_bracket`: nine measured qubits 0.070–1.209, median 0.174; `validation/H0_model.json` C3: the T2* end
post-dicts the measured clean count to 1.05x).  This pilot measures the ratio **on the kingston patch the day's
calibration selects**, with the same windowed-Ramsey pub at the circuit's own duration and at half of it, and —
the planner's physics call, section "Decisions" — **also runs the circuit itself**, so that f_clean is measured
directly with the reference-string statistic and the ratio is read as the model's explanation rather than as its
only evidence.  The deliverable is gate **H0_kpilot**, a measurement gate (PASS = preregistered, measured, verified,
consistent) whose `data.decision` block carries the GO / NO-GO / AMBIGUOUS verdict preregistered in section
"Preregistration".  Whatever the pilot shows is recorded.

## Inputs
- `reports/S2D_levers_C6_ruling_20261002.md` (part 0), `reports/S2D_levers_2x2_kingston.md`,
  `reports/S2D_levers_planner_analysis_20261001.md` (P7, P9), `reports/H0_replan_planner_analysis_20260922.md`
  section 3.2 (D5'), `data/H0_replan_owner_decisions.md` (D8', D1', D5', C2', C3', H0P-Y').
- JSON: `validation/S2D_levers.json` (`data.verdict`, `data.rows.L1_seed_alap`, `data.aer.L1_seed_alap`, `data.live`,
  `data.information.budgets`), `validation/H0_diag.json` (`data.idle_tests.J1.{ramw,t1w}`, `data.jobs` usage),
  `validation/H0_model.json` (`data.C1_estimator_validation`, `data.C3_bracket_postdiction`), `validation/S2D_idle.json`
  (`data.t2_bracket`), `data/S2D_levers/rows.json`, `data/S2D_levers/circuits/L1_seed{,_alap}.{json,qpy.gz}`,
  `data/S2D_levers/family/diag-hop0-hop1-hop2-hop3-plaq0_s2/` and `data/S2D_levers/family.json`,
  `data/hardware/S2D_levers_20261001T1902Z/ibm_kingston_20261001T1902Z.json` (the last full-device record),
  `data/hardware/H0_diag_J1/session.json` (usage per job, options record), `data/hardware/H0_diag_prep/index.json`
  (the diag manifest format).
- Code to read before writing: `scripts/h0_diag_circuits.py` (`build_t1w`, `build_ramw`, `windows`, `expected_ops`,
  the manifest fields), `scripts/gate_H0_diag.py` (`idle_tests`, `readout_reference`, `marginal_ones`, `load_job`,
  `usage_block`, constants `SIGMA`, `RATE_LO/HI`, `IDLE_QUBITS_MIN`, `POSTDICTION_FACTOR`), `scripts/h0_t2_override.py`
  (rule M-T2), `scripts/gate_S2D_levers.py` (`embedding_search`, `candidate_circuit`, `family_on_patch`, `fresh_base`,
  `scheduled`, `delay_schedule`, `pta_at`, `decode_cell`, `stage_e4_aer`, `aer_r_crit`, `fresh_record`), `scripts/
  h0_patch_select.py` (`relabel`, `record_covers`, `score_patch`, `rank_key`), `scripts/h0_device_survey.py`
  (`full_device_record`, `d3pp_budget`), `scripts/h0_backends.py` (`fresh_calibration`, `calibration_fingerprint`,
  `calibration_diff`, `backend_from_record`, `frozen_qubits_and_edges`), `scripts/h0_submit.py` (`preflight`,
  `calibration_gate`, `plan_groups`, the `--prereg` path, `--dry-run`, `--retrieve`, `--status --record-calibration`),
  `scripts/h0_qpu_time.py` (`estimate`), `scripts/gate_H0P.py` (`schedule_circuit`, `apply_t2_override`,
  `load_circuit`, `load_manifests`, `CIRCUIT_KINDS`), `scripts/gate_H0_model.py` (`chunk_seed`, `decode_histogram`),
  `scripts/h0_idle_model.py` (the prereg JSON keys `load_prereg` / `preflight` read: `calibration.{fingerprint,
  path,last_update_date}`, `created`, `commit`), `src/skqd/skqd.py` (`reference_string_test`,
  `pooled_reference_string_test`, `clean_fraction_mixture`, `READOUT_FACTOR`), `src/skqd/idle.py` (`schedule_asap`,
  `idle_budget`, `effective_t2`), `src/skqd/hardware.py` (`logical_statevector`, `transpiled_layout`),
  `scripts/ibm_account.py` (`open_service`, `--check`; **the key is never printed and never passed on a command
  line**), `tests/test_h0_scripts.py` (the submission-path tests to imitate).
- Environment: qiskit 2.5.2 / qiskit-aer 0.17.2 / qiskit-ibm-runtime 0.49.0 (`validation/S2D_levers.json: data.versions`).

## Planner decisions carried by this prompt
- **The circuit under test is `L1_seed_alap` (signed family), not `L4_all`.**  Reasons, all from
  `validation/S2D_levers.json`: (i) at the deciding (transferred) end the signed row is at least as good
  (0.0312 vs 0.0278) and r_crit is the same to three digits (0.3285 vs 0.3302); (ii) the echo-end gain of the
  reordered family (0.2426 vs 0.2170, 1.12x) is paid for by a hidden D3' cost (N4 42700/21000 against 6000/14500,
  `data.information.budgets`) and by an unsigned operator; (iii) L4_all needs the fractional target (`rzz`/`rx`,
  runtime `validate_rzz_pubs`), a submission path this project has never exercised live — not a risk to put inside a
  short pilot whose job is to measure the device.  The family question stays the owner's; nothing here signs it.
- **The circuit flies, not only the Ramsey pubs.**  The ratio is the model's *input*; f_clean is the *question*.  On
  fez the ramw ratios spread 0.07–1.21 across one patch (`S2D_idle.json`), Aer's dephasing on a delay is exponential
  while free induction over short windows may be Gaussian, and the single hardware post-diction of the model is 1.05x
  on one patch at one end.  Running `B0_ref06_k1` and `B1_ref07_k1` of the signed family at 4000 shots each measures
  f_clean with the reference-string statistic to ± 0.006 at f = 0.1 (the decision band) for 2.4 s of execution, and
  the ratio then either explains the measured f (model consistent) or does not (a finding).  `B0_ref06_k4` at 4000
  shots is carried because the owner approved D5' with two Krylov depths; it is information only (the C6 ruling:
  the clean-f estimators are not tolerance-calibrated at p_ref 0.13).
- **Patch rule R1'-pilot (fixed here, before any live read):** the exhaustive embedding search of
  `gate_S2D_levers.embedding_search` (objective: PTA echo f with DD off, `h0_patch_select.rank_key` tie-break,
  unchanged) of the `L1_seed` candidate circuit on the day's **full-device** kingston record, run **once**; the
  winner is the patch.  If the winner's mapping equals `L1_seed_alap`'s (`data/S2D_levers/circuits/L1_seed_alap.json:
  mapping_transpiled_to_kingston`), the committed QPY is used byte for byte (sha256 asserted); otherwise the
  candidate is relabelled with `h0_patch_select.relabel` and scheduled ALAP on the day's record exactly as
  `gate_S2D_levers.scheduled` does (`optimization_level 0`, `scheduling_method "alap"`, `seed_transpiler 7`,
  `schedule_circuit`'s no-op-changed assertion).  No second search after the data; no manual choice.
- **Windows match the circuit under test:** window = 128 dt if 128 × dt_kingston = 512 ns (± 1 ps), else the
  multiple of max(granularity, pulse_alignment) nearest 512 ns; `N_long = round(T_s / window_s)` with T_s the
  ALAP-scheduled duration of `B0_ref06_k1` on the patch (44.24 us on the S2D_levers patch → 86 windows of 512 ns =
  44.03 us); `N_half = round(N_long / 2)` (43 → 22.02 us).  Record all four numbers.  The second length is D5''s
  shape pin (exponential vs Gaussian) and resolves qubits fully dephased at the long window.
- **Options D8':** `--dd off --twirling off`; no resilience, raw bit strings.
- **Uniform 4000 shots on all 8 pubs → one job** (`h0_submit.plan_groups` makes one job per distinct shot count;
  one job keeps every pub under one calibration content and one `usage` figure).
- **Not in this prompt:** the main H0 submission (any job beyond the one pilot job), the re-freeze of the family,
  the family signature, DD cells, a top-up of shots (an AMBIGUOUS verdict returns to the owner with the top-up
  computed), any push, any edit of `data/hardware/H0_prep`, `scripts/h0_submit.py` (read-only here — its options
  and preflight are used as they are), `gate_H0.py`, the decoders, `src/skqd/{su2,lattice,codec,reference_sim}.py`.

## Preregistration (binding; every number here is recomputed by the gate script on the day's record and written
to `data/hardware/H0_kpilot_prep/prereg_<fp16>.json` and committed BEFORE submission)
- **Pubs (8) and shots (4000 each, 32 000 in all):** `kpilot_ramw_long` (sx; N_long windows; sx† ; measure),
  `kpilot_ramw_half` (N_half windows), `kpilot_t1w_long` (x; N_long windows; measure) — all three on the 12 patch
  qubits with `initial_layout = sorted(patch)`, level 0, seed 7, op multiset asserted (`expected_ops` generalised to N);
  `cal_patch_all0`, `cal_patch_all1` (readout reference of the patch, as the diag's); `B0_ref06_k1`, `B1_ref07_k1`,
  `B0_ref06_k4` of the signed family placed by `gate_S2D_levers.family_on_patch`'s rule (identical pattern → the
  row's mapping; else the best embedding onto the row's qubit set), each scheduled ALAP with explicit delays and
  verified exact (max |Δ| < 1e-10 on the codewords in the default order, leakage < 1e-9, measurement map consistent).
- **Execution estimate (planner arithmetic from `data.rows.L1_seed_alap.compile.T_total_s` = 46.42 us, the ramw
  44.03 + 2.18 us, half 22.02 + 2.18 us, cal 2.18 us, rep delay 250 us = `data.information.budgets.rep_delay_s`):
  3 × 4000 × 296.4 us + 2 × 4000 × 296.2 us + 4000 × 274.2 us + 2 × 4000 × 252.2 us ≈ 9.0 s.**  The committed jobs
  show billed usage ≈ estimate + 1–2 s per job (`H0_diag.json: data.jobs`: J1 5 pubs × 2000 → 5.0 s, J2 3 pubs →
  4.0 s, J3 → 3.0 s; canary 801 shots → 2.0 s), so expect **≈ 11–12 s billed**.  The preflight cap is
  `--max-qpu-seconds 30` on the estimator (≤ ≈ 32 s billed), the hard cap 60 s billed.  **If the day's estimate
  exceeds 30 s, nothing is submitted: STOP, return to the owner with the estimate** — do not cut shots to fit.
- **Statistics and their σ (all existing functions, no new constant):**
  (S1) per k = 1 circuit, `reference_string_test(n_ref, 4000, p_ref, a_sector, dim)` → f_clean with the Garwood
  interval at conf 0.6827 (68 %) and, called again with conf 0.9545, the 95 % interval; `clean_fraction_mixture`
  alongside (68 % profile) with the C6 deviation reported (p_ref 0.883 / 0.889 ≥ 0.5: the ruling's scope applies —
  a deviation > 0.25 on hardware is an information flag, not a gate failure).
  (S2) `pooled_reference_string_test` over the two k = 1 circuits → **f_pool** with 68 % and 95 % intervals (the
  shots-weighted mean, the "mean f" of the S2D bar).
  (S3) per qubit q and window W ∈ {long, half}: readout-corrected P0 and its binomial σ (`gate_H0_diag.idle_tests`,
  `SIGMA = 3`); T2*_q from the window with the smaller relative σ, σ_T2*/T2* = 2 σ_P0 / (|2P0 − 1| · |ln(2P0 − 1)|),
  among windows with 2P0 − 1 > 0; else the 3σ upper bound at the half window; else the patch minimum (rule M-T2
  extended to two windows, fixed here); provenance written per qubit.  Shape ratio ln(2P0_long − 1)/ln(2P0_half − 1)
  per doubly-resolved qubit (2 = exponential, 4 = Gaussian; information).
  (S4) **r_eff** = the uniform ratio r solving S_T2(r × T2_echo,q) = S_T2(T2*_q) by bisection on log r (1e-6), with
  S_T2 the PTA sum of `skqd.idle.idle_budget` over the **explicit delay windows of the ALAP `B0_ref06_k1` circuit
  with the leading |0> delays excluded** (`gate_S2D_levers.delay_schedule(..., include_leading=False)`) and T2_echo
  from the day's record — i.e. the same uniform-r axis on which `data.aer.L1_seed_alap` and r_crit are defined.
  σ(r_eff): parametric bootstrap, 10 000 draws of every P0 from N(P0, σ_P0) clipped to [0, 1], the S3 rule
  re-applied per draw, 16/84 and 2.5/97.5 percentiles; seed 11.  The idle-weighted harmonic-mean ratio and the
  per-qubit ratios T2*_q / T2_echo,q are reported beside it.
  (S5) f_Aer(r_eff): log-log interpolation on the **day's** Aer grid (step C3) of `B0_ref06_k1`; the day's r_crit by
  the same interpolation (`gate_S2D_levers.aer_r_crit`), reported next to the preregistered **0.3285**.
- **Decision rule on f (primary; the S2D bar read on the pilot's two k = 1 circuits):**
  **GO** iff f_pool,lo95 ≥ 0.1 **and** min_c f_c,lo95 ≥ 0.05;  **NO-GO** iff f_pool,hi95 < 0.1 **or**
  min_c f_c,hi95 < 0.05;  **AMBIGUOUS** otherwise (the 95 % interval straddles a bar) → STOP: the report states the
  additional shots that would make the pooled interval exclude 0.1 at the measured f (Poisson scaling, computed),
  and nothing more is submitted without the owner.  Planner expectation (from the fez ratio and the Aer grid:
  f_Aer(0.153–0.174) = 0.031): **NO-GO is the likely outcome**; it is a result, not a failure of the gate.
- **Decision rule on r (secondary; the model's consistency):** `r_verdict` = "above" iff r_eff,lo68 ≥ 0.3285,
  "below" iff r_eff,hi68 < 0.3285, else "straddles"; `model_consistent` iff f_B0,meas / f_Aer(r_eff) ∈ [1/3, 3]
  (the `POSTDICTION_FACTOR` of gate H0_diag / H0_model C3, unchanged).  If the f-verdict and the r-verdict disagree
  (e.g. GO with r below r_crit), **the direct measurement decides f** and the disagreement is reported as a model
  finding (the exponential-on-delay model would then be wrong on this patch); it is not averaged away.
- **Preregistered predictions written before submission:** Aer (scheduled, day's record, `apply_t2_override` at
  uniform r on the patch qubits, 4000 shots as 2 chunks of 2000 with `chunk_seed` strided seeds 11 / 2011, counts
  written once and refused rather than re-drawn) for `B0_ref06_k1` at r ∈ {1, 0.5, 0.3285, 0.25, 0.174} and for
  `B1_ref07_k1`, `B0_ref06_k4` at r ∈ {1, 0.174}: f_clean (both statistics, intervals) and the expected reference
  hits at 4000 shots; the PTA bound at the same r; per qubit the ramw P0 bound at the echo T2, (1 + e^{−T/T2})/2,
  for both windows, and P0 at r = 0.174; the t1w survival e^{−T/T1}.
- **D9 at both ends:** submission only if `calibration_fingerprint` of the live patch record equals the prereg's
  (`h0_submit --prereg`), and the retrieval-time record (`--status --record-calibration`) is diffed against it
  (information: a move between submission and retrieval is reported, never silently accepted).
- **What is NOT done:** no second job, no main H0 run, no re-freeze, no push.

## Steps

### Part 0. Apply the C6 ruling and re-assemble S2D_levers (about 1 h; 0 QPU s)
0.1 Read `reports/S2D_levers_C6_ruling_20261002.md` section 4 and implement exactly that in
    `scripts/gate_S2D_levers.py` (constant `C6_P_REF_MIN = 0.5`; the pass/fail list restricted to cells with
    `p_reference >= C6_P_REF_MIN`; the new `data.C6_information_low_p_ref` block with dev, σ_ref, σ_mix, z,
    clean_accepted_{reference,mixture,ceiling}, `reference_exceeds_ceiling`, `shots_for_tolerance_at_3_sigma`, and the
    summary {n_cells, max_abs_z, sum_z2, chi2_p}; the criterion name and value strings as written there; the report's
    "C6 ruling" section generated from the JSON).  `C6_TOL` and `MIN_REF_HITS` untouched.
0.2 `tests/test_s2d_levers.py`: (i) from the committed `validation/S2D_levers.json`, `E4:B1_ref07_k4` r = 0.174 gives
    z = −1.65 ± 0.02 and clean_accepted_ceiling 324.9 < clean_accepted_reference 347.9; (ii) a synthetic p_ref = 0.9 cell
    at deviation 0.30 still fails C6; (iii) a synthetic p_ref = 0.13 cell at deviation 0.30 is information, not a failure.
0.3 `python scripts/run_gate.py S2D_levers` (assemble; about 8 min with the regressions).  Expected: **PASS 9/9**, C6
    value "30 cells checked, worst 0.099; 28/28 row cells present; 4 low-p_ref cells recorded (max |z| 2.22)".  If
    the worst p_ref ≥ 0.5 deviation is not 0.0987 or the status is not PASS, STOP (the assemble stage re-drew or
    re-read something it should not have) and hand back.
0.4 `validation/BLOCKED.md`: append "resolved 2026-10-02 by the planner ruling (reports/S2D_levers_C6_ruling_20261002.md):
    C6 scoped to p_ref ≥ 0.5; S2D_levers PASS 9/9 on re-assembly"; `python scripts/update_status.py`; LOG row; commit
    "gate S2D_levers: C6 scoped to p_ref >= 0.5 per the planner ruling of 2026-10-02; PASS 9/9 (k = 4 cells kept as
    information with z)".  **No push.**

### Part A. Account and the day's records (about 10 min; metadata only, 0 QPU s)
A1. `python scripts/ibm_account.py --check` → record instance, plan, usage before the pilot, kingston status and
    pending jobs, into `data/hardware/H0_kpilot_prep/account_check_<stamp>.json` (never the key).  STOP if kingston is
    not reachable or not operational.
A2. `h0_device_survey.full_device_record("ibm_kingston")` (a NEW backend object; `fresh_calibration` → `refresh()`) →
    `data/hardware/H0_kpilot_prep/ibm_kingston_full_<stamp>.json`; `calibration_diff` against
    `data/hardware/S2D_levers_20261001T1902Z/ibm_kingston_20261001T1902Z.json` (leaves moved, families); qubit 146's
    leaves recorded as they are (None stays None).

### Part B. Patch selection and the pilot circuit set (`scripts/h0_kpilot_circuits.py`, about 2 h)
B1. `--stage select`: `embedding_search(candidate_circuit(L1_seed cand), day record, a_B0)` → winner mapping, top 5,
    `n_embeddings`, whether the S2D_levers mapping is reproduced (`on_survey_patch` with the committed set) →
    `data/hardware/H0_kpilot_prep/select.json`.  About 2 min.
B2. `--stage build` → `data/hardware/H0_kpilot_prep/{index.json, circuits/*.json, circuits/*.qpy.gz}` in the
    `h0_build_circuits` manifest format (`common` with `backend: "FakeKingston"`, `backend_qubits: 156`,
    `n_logical_qubits: 12`; per circuit `id`, `kind` ∈ {idle_test, coarse_step, readout_calibration}, `test`,
    `sector`, `reference`, `k`, `repetitions: 1`, `physical_qubits`, `logical_to_physical`, `measurement_map`, `ops`,
    `qpy`, `qpy_gz_sha256`, `n_windows`, `window_dt`, `window_s`, `total_delay_s`, `expected_bits`, `schedule:
    "alap"`, `T_s`, `T_total_s`, `n_delays`, `leading_delay_s` per qubit, `exactness {max_abs_delta, leakage}`,
    `record_fingerprint_full`, `source_qpy_sha256` for the three family circuits).  Readout-calibration circuits as
    `h0_build_circuits` builds them for a patch.  The three coarse circuits: placed and ALAP-scheduled as the
    Decisions section says; `schedule_circuit`'s assertion; exactness via `logical_statevector` against
    `apply_groups` in the default order (the C4 check of prompts/23); the committed `L1_seed_alap.qpy.gz` used byte
    for byte when the mapping is reproduced.  Window arithmetic printed and written (dt, granularity, pulse_alignment,
    window_s, N_long, N_half, T_s matched).
B3. The patch-scoped calibration record for D9: `fresh_calibration(backend, qubits, edges)` with
    `frozen_qubits_and_edges(prep)` → `data/hardware/H0_kpilot_prep/calibration_<stamp>.json`; assert every qubit and
    edge leaf equals the full-device record's (A2) — if not, the calibration moved between the two reads: repeat A2–B3
    (D10-style re-run of the same scripts, no parameter change), at most twice, then STOP.

### Part C. Preregistration and predictions (`scripts/gate_H0_kpilot.py --stage predict`, about 45 min in
≤ 10-min commands; 0 QPU s)
C1. The prereg file `data/hardware/H0_kpilot_prep/prereg_<fp16>.json` in the format `h0_submit.preflight` and
    `gate_H0_diag.load_prereg` read (`calibration.{fingerprint, path, last_update_date, stamp}`, `created`, `commit`,
    `script`), **written by gate_H0_kpilot.py, not by h0_idle_model.py** (its `schedule_asap` counts explicit delays as
    busy time — `src/skqd/idle.py` docstring — and would report no idle budget for an ALAP circuit).  PTA on the
    explicit delay windows, leading excluded and included both recorded (`delay_schedule`, `pta_at`), at
    r ∈ {1, 0.5, 0.3285, 0.25, 0.174}.
C2. The ramw / t1w predictions per qubit (Preregistration bullet), the window table, the pub list with shots, the
    execution estimate via `h0_qpu_time.estimate(prep, backend, {}, 4000, shots_default=4000)` on the live durations
    (STOP if > 30 s), the decision thresholds verbatim (0.1, 0.05, r_crit 0.3285, factor 3) and the planner's
    expectation line.
C3. Aer cells (`--stage aer --circuit <id> --ratio <r> --chunk <i>`; about 2.2 min per 2000 shots; ≤ 4 cells per
    command): `B0_ref06_k1` × {1, 0.5, 0.3285, 0.25, 0.174}, `B1_ref07_k1` × {1, 0.174}, `B0_ref06_k4` × {1, 0.174};
    `backend_from_record(patch record, base=FakeKingston(), strict=True)`, `apply_t2_override` at uniform r on the
    12 patch qubits (its own reach check), `AerSimulator.from_backend(base, seed_simulator=chunk_seed(11, i, 2000))`,
    counts to `data/hardware/H0_kpilot_prep/aer/<id>_r<r>_chunk<i>.json`, read with `decode_cell`'s two statistics.
    The day's f(r) grid and r_crit (log-log interpolation) into the prereg; the r = 1 cell of `B0_ref06_k1` is the
    expected reproduction of `data.aer.L1_seed_alap["1.0"]` (0.2170 [0.212, 0.222]) when the mapping is reproduced —
    report the deviation; if the mapping differs, report the new value and say so.
C4. `--stage prereg-md` → `reports/H0_kpilot_prereg_<stamp>.md` from the JSON (no typed number).  **Commit**
    "H0_kpilot: preregistration on ibm_kingston calibration <fp16> (patch [...], 8 pubs x 4000 shots, estimate <x> s)"
    — the commit hash is what K1 checks against the submission time.

### Part D. Dry run on the simulator (about 10 min; 0 QPU s; must PASS before Part E)
D1. `python scripts/h0_submit.py --dry-run --prep data/hardware/H0_kpilot_prep --shots 4000 --cal-shots 4000
    --max-pubs-per-job 8 --seed 11 --out data/hardware/H0_kpilot_dryrun` (one local job, 8 pubs; the local testing mode
    ignores DD/twirling options — they are off anyway).
D2. `python scripts/gate_H0_kpilot.py --stage assemble --counts data/hardware/H0_kpilot_dryrun/counts --dry-run
    --out H0_kpilot_dryrun` → `validation/H0_kpilot_dryrun.json`, `reports/H0_kpilot_dryrun.md`: the whole analysis
    (S1–S5, the decision logic) runs on the dry-run counts; K3–K6 and K8 must PASS; K1/K2 are "n/a (dry run)"; the
    decision block is labelled `dry_run: true` (on the snapshot's echo T2 the expected reading is r_eff ≈ 1 and GO — a
    path check, not a prediction).  The dry-run `T1`/`T2*` must agree with the snapshot's within the diag's own bands
    (1/T1 in [0.5, 2] × record; T2* within 3σ of the snapshot's echo T2 for ≥ 10 of 12 qubits).  STOP on any failure.

### Part E. The one submission (about 30 min wall; the QPU spend)
E1. Pre-check: `python scripts/h0_calwatch.py --once` against the prereg's patch record (exit 0 = match; exit 3 =
    moved → re-run A2–C4 on the new content (D10), commit, and only then continue; at most twice, then STOP).
E2. `python scripts/h0_submit.py --backend ibm_kingston --prep data/hardware/H0_kpilot_prep --shots 4000
    --cal-shots 4000 --dd off --twirling off --prereg data/hardware/H0_kpilot_prep/prereg_<fp16>.json
    --max-qpu-seconds 30 --max-pubs-per-job 8 --job-tags H0_kpilot --out data/hardware/H0_kpilot_ibm_kingston`.
    The preflight prints `prereg_fingerprint_match`; it refuses on a mismatch, a non-operational device, a missing
    error leaf, or an estimate above 30 s.  **One job.  Commit `session.json` immediately** ("H0_kpilot: job <id>
    submitted on <fp16>").
E3. `python scripts/h0_submit.py --retrieve --wait 1500 --out data/hardware/H0_kpilot_ibm_kingston` (re-run until DONE;
    each invocation ≤ 25 min); then `--status --record-calibration` (retrieval-time record and its diff against the
    prereg's).  Commit the counts and the session ("H0_kpilot: counts retrieved, usage <u> s, retrieval fingerprint
    <match/moved>").  Counts files are raw data: never overwritten, never edited.
E4. `python scripts/ibm_account.py --check` again → usage after the pilot into
    `data/hardware/H0_kpilot_ibm_kingston/account_check_after_<stamp>.json`.

### Part F. Analysis, report, bookkeeping (about 2 h; 0 QPU s)
F1. `python scripts/gate_H0_kpilot.py --stage assemble --counts data/hardware/H0_kpilot_ibm_kingston/counts
    --out H0_kpilot` → `validation/H0_kpilot.json`, `reports/H0_kpilot_ibm_kingston.md` (`python scripts/run_gate.py
    H0_kpilot` runs this stage).  The assemble stage refuses to mix dry-run and device counts (it reads
    `session.dry_run`).  Report sections: what PASS means; the preregistration block (patch, windows, pubs, estimate,
    predictions, thresholds, commit hash); the live block (fingerprints at prereg / submission / retrieval, usage before
    and after, job id, usage_s); readout confusion; the Ramsey table per qubit (both windows: raw and corrected P0, σ,
    T2* and provenance, the echo T2, the ratio, the shape ratio, the echo bound and r = 0.174 prediction); the T1
    table; **r_eff with 68 / 95 % intervals against r_crit 0.3285 and the day's r_crit**; the circuit table (per
    circuit: accepted, reference hits, garbage expectation, P_ge, f_clean both statistics with 68 / 95 %, the Aer
    predictions at r = 1 / r_eff / 0.174, the distance histogram); **f_pool with its intervals against 0.1, the worst
    circuit against 0.05, the decision**; `model_consistent`; the D3''-H0 and D3' budgets at the measured f_pool
    (`h0_device_survey.d3pp_budget` / `d3_budget` logic on the family's durations — information, for the owner's next
    decision); honest limits (section below, with the JSON's numbers); criteria.
F2. `data.decision`: `f_pool`, `f_pool_68`, `f_pool_95`, `f_by_circuit` (both statistics, both intervals),
    `worst_circuit_f_95`, `decision` ∈ {GO, NO-GO, AMBIGUOUS}, `ambiguous_topup_shots` (null unless AMBIGUOUS),
    `r_eff`, `r_eff_68`, `r_eff_95`, `r_crit_preregistered` (0.3285), `r_crit_day`, `r_verdict`, `f_aer_at_r_eff`,
    `model_consistent`, `shape_ratio_median`, `n_qubits_resolved_{long,half}`, `usage_s`, `dry_run`.
F3. `pytest -q tests` (new `tests/test_h0_kpilot.py`: the S3 rule on synthetic P0 tables incl. a fully-dephased qubit,
    r_eff bisection against a hand-computable two-window case, the decision logic on synthetic intervals for all three
    outcomes, the prereg-format keys, the dry-run/device mixing refusal); `python scripts/check_package.py`;
    `graphify update .`; append `("H0_kpilot", "ibm_kingston pilot on the selected patch: windowed Ramsey at two
    lengths (T2*/T2_echo ratio r_eff vs r_crit), T1, the signed k = 1 circuits' direct f_clean; GO/NO-GO on f >= 0.1
    (measurement gate)", "QPU")` to `GATES` in `scripts/update_status.py`; `python scripts/update_status.py`; LOG
    rows (one per part, the executor's); commits "gate H0_kpilot: <status> (decision <GO|NO-GO|AMBIGUOUS>, f_pool
    <x> [95 %: a, b], r_eff <r> [68 %: a, b] vs r_crit 0.3285, usage <u> s)".  **No push.**

## Pass criteria (gate H0_kpilot; all machine-checked in `validation/H0_kpilot.json`)
- K1 preregistration before data: the prereg JSON's `commit` exists in `git log` and its commit time precedes
  `session.jobs[0].submitted`; `session.prereg_calibration_fingerprint == prereg.calibration.fingerprint ==
  session.calibration_fingerprint`; the retrieval-time fingerprint recorded (equal → `retrieval_match` true; moved →
  false, with the diff; information, not a failure).
- K2 one job, status DONE, `usage_s` recorded and ≤ 60; the preflight execution estimate ≤ 30 s; 8 counts files
  with 4000 shots each; `sampler_options` record shows DD off and twirling off.
- K3 readout: confusion min diagonal ≥ 0.9 (`DIAG_MIN`) on the patch from the two cal pubs.
- K4 decoder round trip over every accepted string of the three coarse pubs: 0 mismatches.
- K5 idle tests: ≥ 10 of 12 qubits (`IDLE_QUBITS_MIN`) with a T2* of provenance "measured" at one of the two
  windows; every qubit's P0 ≤ echo bound + 3σ at both windows for ≥ 10 of 12 (C4b analogue); 1/T1 within
  [0.5, 2] × the record's for ≥ 10 of 12 (C4a analogue); `r_eff` finite with both intervals.
- K6 circuits: every coarse circuit's exactness at build (max |Δ| < 1e-10, leakage < 1e-9), `schedule_circuit`'s
  assertion, op multisets of the idle pubs as intended, the dry-run gate `validation/H0_kpilot_dryrun.json` PASS.
- K7 the Aer prediction cells present for every (circuit, r) of C3 with strided seeds and counts files on disk; the
  r = 1 `B0_ref06_k1` cell within 25 % of `S2D_levers.json: data.aer.L1_seed_alap["1.0"].f_clean_mixture` when the
  mapping is reproduced (else reported, not checked).
- K8 `data.decision` complete (every field of F2 non-null except `ambiguous_topup_shots` when not AMBIGUOUS) and the
  decision reproduces the preregistered rule from the recorded intervals (the test recomputes it).
- K9 `pytest -q tests` all pass; `python scripts/check_package.py` OK.
- Status PASS iff K1–K9.  **No criterion on f, r_eff or the decision itself**: a NO-GO pilot is a PASS gate.

## Outputs
`scripts/gate_S2D_levers.py` (+ ruling), `tests/test_s2d_levers.py` (+3), `validation/S2D_levers.json` (re-assembled),
`reports/S2D_levers_2x2_kingston.md` (+ C6 ruling section), `validation/BLOCKED.md` (+ resolved line);
`scripts/h0_kpilot_circuits.py`, `scripts/gate_H0_kpilot.py`, `tests/test_h0_kpilot.py`,
`data/hardware/H0_kpilot_prep/` (account check, full-device and patch records, select.json, index.json, circuits/,
aer/, prereg_<fp16>.json), `reports/H0_kpilot_prereg_<stamp>.md`, `data/hardware/H0_kpilot_dryrun/` (session, counts),
`validation/H0_kpilot_dryrun.json`, `reports/H0_kpilot_dryrun.md`, `data/hardware/H0_kpilot_ibm_kingston/` (session.json,
counts/, calibration_at_submission_*.json, calibration_at_retrieval_*.json, account check after),
`validation/H0_kpilot.json`, `reports/H0_kpilot_ibm_kingston.md`, `scripts/update_status.py` (+1 row),
`validation/gates.md` / `reports/PROJECT_STATUS.md` regenerated, `prompts/LOG.md` rows.  **Push: no.**

## Time budget per command (laptop; planner-measured where stated)
| command | expected | limit |
|---|---|---|
| 0.3 S2D_levers re-assemble (+ regressions) | about 8 min | 30 min |
| A1–A2 live reads | 1–3 min | 30 min |
| B1 embedding search on the full record | about 2 min (S2D_levers C2: 2 min per candidate) | 30 min |
| B2 build + exactness of 3 circuits + 5 pubs | about 3 min | 30 min |
| C3 one Aer cell (2 × 2000 shots) | about 2.2 min (S2D_levers: 61–73 s per 2000) | 10 min; ≤ 4 cells per command |
| D1 dry run (8 pubs × 4000 on Aer) | about 4–8 min (diag dry run: 124 s for 5 × 2000) | 30 min |
| E3 retrieve | queue-bound; one invocation ≤ 25 min (`--wait 1500`) | repeat |
| F1 assemble | < 2 min | 30 min |
| pytest | < 9 min | — |

## Honest limits (to be stated in the report verbatim, with the JSON's numbers)
- r_eff is one number for a patch whose per-qubit ratios may spread an order of magnitude (fez: 0.070–1.209); the
  uniform-r axis is the one r_crit is defined on, and the per-qubit table is beside it.  A per-qubit Aer prediction
  (`apply_t2_override` with the measured table, rule M-T2) is the H0_model path and is computed here only as
  information if time allows; it is not the decision statistic.
- Aer's dephasing on a delay is exponential; the shape ratio tests that with two lengths only.  A Gaussian decay makes
  the many short windows of the circuit *less* harmful than the long Ramsey windows suggest — the direction in which
  the r-verdict could be pessimistic while the f-verdict is not; that is why f is primary.
- Two k = 1 circuits are not the 28-circuit family; the S2D bar is read on them as a pilot, and the family-level
  statement needs the main run.  The k = 4 cell's f is information (C6 ruling).
- The readout factor 0.82 of manual Step 4.4 is applied to both statistics and to the Aer predictions, so the
  comparison with r_crit and with the 0.1 bar is in the convention of S2D_levers; the patch's measured readout
  survival Π_q P(correct) is reported beside it.
- One job on one calibration content; a device drift between submission and retrieval is reported, not corrected.

## Escalation
- Kingston unreachable / not operational / 146-style missing leaves on the selected patch: STOP, record, hand back
  (the day's reads are kept; nothing is submitted).
- Execution estimate > 30 s, or `--check` shows less than 60 s of allowance in the current period: STOP, return to
  the owner with the numbers; do not resize.
- Fingerprint moved at E1 or refused at E2: D10 — re-run A2–C4 on the new content with no parameter change, commit,
  retry once; a second move → STOP (the device is recalibrating; try another day).
- Job ERROR / CANCELLED: record the session, hand back; **no automatic resubmission** (it would be a second QPU spend).
- The dry run fails on a K-criterion: fix the analysis, re-run D1–D2; never edit a counts file; two honest failures
  → hand back with the traceback.
- AMBIGUOUS decision: STOP as preregistered; the report carries the top-up computation; the owner decides.
- Any analysis number that disagrees with its S2D_levers / H0_diag counterpart by more than the stated tolerance
  (K7, the dry-run bands): stop and report before submitting.

## Do-not-touch list (binding)
`data/hardware/H0_prep`, `data/hardware/H0_*` (read only; new directories `H0_kpilot_*` are created), every existing
`validation/*.json` except the re-assembled `S2D_levers.json` and `BLOCKED.md`, `scripts/h0_submit.py`,
`scripts/gate_H0.py`, `scripts/h0_device_survey.py`, `scripts/h0_patch_select.py`, `src/skqd/{su2,lattice,codec,
reference_sim}.py`, every criterion constant and decoder, `proposal/`, CLAUDE.md's status paragraph (the scribe does
it after the owner reads the result), the planner's LOG row.  `scripts/gate_S2D_levers.py` gets the part-0 change
only; no Aer count under `data/hardware/S2D_levers_*/aer/` is re-drawn.
