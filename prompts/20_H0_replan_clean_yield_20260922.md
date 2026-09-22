# 20 — H0 re-plan: the clean-yield statistic, the scheduled-Aer prediction at both ends of the T2 bracket, the post-diction gate H0_model, and the free device survey
executor: executor-opus   effort: high (xhigh on the second attempt); runner-sonnet low for the Aer runs, the survey and the regressions; scribe-haiku low for the status tables
time budget: 2 days of laptop work in commands < 30 min each (the scheduled-Aer runs are about 5 min per 2000 shots; split by shots); read-only target metadata for the survey; **0 QPU seconds**   machine: laptop (CPU) + read-only ibm_fez / ibm_marrakesh / ibm_kingston metadata

> Written by planner-fable at max effort after gate H0_diag (FAIL 6/8, C3 decisive: H_B rejected).  The rulings
> and every number are in `reports/H0_replan_planner_analysis_20260922.md` (read it first; sections 0, 2, 3, 8).
> The central new fact: the accepted shots of the diagnostic are not clean shots (2 reference-string hits where 15
> were expected in J1; 13 of 35 accepted strings are distance-2 codewords with ideal probability 0); pooled over
> the five hardware pubs the clean-shot fraction on patch 1 is 6.7e-4, between the echo-T2 end (7.6e-3) and the
> T2* end (1.1e-4) of the idle model.  This prompt spends **no QPU time**, changes **no criterion constant, no
> convention, no frozen circuit, no preregistered JSON**, and prepares the owner's decisions of section 8 of the
> analysis behind flags whose defaults reproduce today's outputs bit for bit.  prompts/07 clause (b) stays in force.
>
> **Files you must not touch** (three executor agents are working on amendment-01 items 1–3 in them; their
> first state is committed at 76b4fd5 — build on that commit, never on a working-tree copy):
> `proposal/amendment_01_devices_and_budgets.md`, `scripts/gate_S2D.py`, `src/skqd/device_req.py`,
> `scripts/h0_patch_select.py`, `scripts/gate_S2D_idle.py`, `scripts/s2_family_duration_compare.py`,
> `scripts/h0_idle_model.py`, `src/skqd/idle.py`, `scripts/s2_duration_*.py`, and every existing `validation/*.json` (you write only
> `validation/H0_model.json` and the regression outputs named below).  If a step needs `skqd.idle`, import it as it
> is on disk and do not edit it; if it is not yet committed when you start part D, do part D last.

## Goal
Make the H0 prediction chain predict clean shots: (1) a clean-yield estimator that weights accepted strings by the
ideal distribution, validated where the truth is known; (2) an Aer prediction on scheduled circuits (idle windows
as explicit delays) with a per-qubit T2 override, so that both ends of the bracket — the record's Hahn-echo T2 and
the measured free-induction T2* — are computed by the same code; (3) gate `H0_model`, the post-diction of the
existing hardware counts by that chain, whose criterion C3 decides whether the T2* end is the working model;
(4) the reference-string and mixture tables in gate_H0 as information; (5) the free survey of the three reachable
Heron devices as full-device calibration records, searched by the in-flight `scripts/h0_patch_select.py` (run,
not edited), so that the owner can decide the patch and the device.  Then STOP
for the owner's decisions (analysis section 8); the pilot session is prompts/21.

## Inputs
- `reports/H0_replan_planner_analysis_20260922.md` (rulings, P7–P13 with snippets), `reports/H0_canary_planner_analysis_20260922.md`
  (P1–P6), `validation/H0_diag.json`, `validation/H0_canary.json`, `validation/BLOCKED.md`.
- Raw counts (read-only): `data/hardware/H0_ibm_fez_canary/counts/`, `data/hardware/H0_diag_J{1,2,3,4}/counts/`;
  the records `data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json` (fingerprint 7fd6d65e…, the 30 frozen
  qubits) and `data/hardware/H0_diag_prep/calibration_20260922T1400Z.json` (a44b6ac0…, patch 1 only).
- `data/hardware/H0_prep/` (frozen set, read-only), `data/hardware/H0_diag_prep/idle_model_frozen_set_7fd6d65e.json`,
  `data/hardware/H0_ibm_fez/shot_plan_20260922T1400Z.json`, `data/hardware/H0_ibm_fez/sim_cache/` (read-only).
- Code: `src/skqd/skqd.py` (`yield_model`, `clean_fraction_from_yield`, `READOUT_FACTOR`), `src/skqd/codec.py`
  (`Codec.decode` raises `Reject`; `Codec.encode`), `src/skqd/reference_sim.py` (`qiskit_key_to_bits(key)`),
  `src/skqd/krylov.py` (`apply_groups`, `basis_vector`, `term_groups`), `scripts/h0_support_plan.py`
  (`ideal_probabilities`, `f_from_calibration`), `scripts/gate_H0P.py` (`analyse_records`, the sampling loop at the
  `AerSimulator.from_backend` call, the cache keyed by fingerprint), `scripts/gate_H0.py` (`analyse_records` import,
  `prediction`, the criteria block — **not edited**), `scripts/gate_H0_diag.py` (the readout-corrected T2* inversion:
  reuse its per-qubit rule), `scripts/h0_backends.py` (`resolve_backend`, `fresh_calibration`,
  `calibration_fingerprint`), `scripts/ibm_account.py` (`open_service`), `scripts/run_gate.py`, `scripts/update_status.py`.
- Installed stack: qiskit 2.5.2 (`transpile(..., optimization_level=0, scheduling_method="asap")` inserts `Delay`s
  on the target's durations — P9 verified 519 delays and an unchanged CZ count on the canary circuit;
  `Target.qubit_properties` must be *assigned* as a list, in-place edits do not reach the target — prompts/17 PC 3),
  qiskit-aer 0.17.2 (`AerSimulator.from_backend` charges `delay` with thermal relaxation from `qubit_properties`;
  prompts/19 D6 verified it against e^{−T/T1} and (1 + e^{−T/T2})/2 on the idle-test circuits), qiskit-ibm-runtime
  0.49.0.  Aer cost on this laptop: unscheduled 168 s, scheduled 278 s per 2000 shots of the canary circuit (P9).

## Planner decisions carried by this prompt (fixed before any new data exist; details in the analysis)
- **M-A** The analytic PTA of `skqd.idle` is a bound; the prediction of record is Aer on the scheduled circuit.
- **M-T2** T2 is a measured input: the prediction is made at both ends (record T2; measured T2*) by the same code;
  the T2* per qubit follows the rule: measured value where P(0) − 3σ > 0.5, else the 3σ upper bound, else the
  smallest resolved bound on the patch; provenance recorded per qubit.
- **M-C** The clean-yield estimator of section 3.4 is the statistic of the post-diction and of the survey tables;
  gate H0's criterion code is unchanged until the owner signs C2'.
- **D8'** (owner) production options DD off / twirling off; nothing in this prompt submits anything, so the only
  effect here is that `h0_submit.py --dd off --twirling off` must be the documented production command in the
  hand-back; the defaults of `h0_submit.py` are NOT changed by this prompt.
- **R1'** (owner, D1') patch selection = the exhaustive embedding search of the in-flight `scripts/h0_patch_select.py`
  on a full-device record of the session day, then a one-patch re-freeze (analysis section 4); this prompt runs
  the search on the survey records (part E) but freezes no circuit.
- **D3''-H0** (owner) H0's r = 1 shots may be sized for criterion 2's clean-f statistic instead of clean
  saturation (analysis section 7c); this prompt only tabulates both budgets.

## Steps

### A. The clean-yield estimator (`src/skqd/skqd.py`; about 2 h)
A1. `clean_fraction_mixture(n_by_state, p_ideal, dim, n_shots, readout_factor=READOUT_FACTOR)`: `n_by_state` =
    accepted counts per sector position (length dim), `p_ideal` the ideal sector distribution of the circuit
    (sums to 1 to 1e-9, else ValueError); maximise `L(w) = Σ_s n_s log(w p_s + (1 − w)/dim)` over w ∈ [0, 1] on a
    grid of 2001 points refined by `scipy.optimize.minimize_scalar` (bounded); return a dict with `w`, `w_68`
    (profile-likelihood interval, Δlog L = 0.5), `accepted`, `clean_accepted = w × accepted`,
    `clean_yield = clean_accepted / n_shots`, `f_clean = clean_yield / readout_factor`, `f_clean_68`, `logL_gain =
    L(w) − L(0)`.  `w = 0` when the accepted histogram is flat; never raise on a zero-count circuit (return w = 0,
    intervals [0, 1]).
A2. `reference_string_test(n_ref, n_shots, p_ref, acceptance, dim)`: expected garbage hits `n_shots × acceptance /
    dim`, `sigma = sqrt(expected)`, `excess`, `z = excess / sigma`, `P_ge = poisson.sf(n_ref − 1, expected)`, and the
    clean-yield estimate `excess / (n_shots × p_ref)` with the Poisson 68 % interval on n_ref.
A3. `ideal_sector_distribution(model, g2, twoB, reference, k, dt, repetitions)` (in `skqd.krylov` or
    `skqd.skqd`): `apply_groups` r times at angle k dt from `basis_vector(reference)`, projected on the sector
    indices — the same computation `h0_support_plan.ideal_probabilities` cross-checks; assert agreement with the
    QPY-derived probabilities of the frozen set to 1e-9 in a test (`B0_ref06_k1_rep1`: p(reference) = 0.8833).
A4. Tests (`tests/test_clean_yield.py`): (i) synthetic mixtures drawn with `numpy.random.default_rng(11)` at
    w ∈ {0, 0.1, 0.5, 0.9} and N_acc = 1e4 over the B=0 k=1 distribution: the estimate within 0.02 of the truth and
    the 68 % interval covering it in ≥ 3 of the 4 cases; (ii) a flat histogram gives w = 0; (iii) the reference test
    reproduces P8's pooled numbers when fed 6 hits over 8267 shots with acceptance 38/4096 (expected 2.018,
    P_ge 0.017 ± 0.001, f_clean 6.65e-4 ± 1e-6).

### B. The scheduled-Aer prediction path with a T2 override (`scripts/gate_H0P.py`; about 3 h)
B1. `--schedule {none,asap}` (default `none`, so every existing output is reproduced): with `asap`, each circuit is
    passed through `transpile(circ, backend=backend, optimization_level=0, scheduling_method="asap",
    seed_transpiler=7)` before `sim.run`; assert per circuit that the multiset of non-delay operations is unchanged
    and record `n_delays`, the scheduled duration in dt and its agreement with `h0_qpu_time.circuit_duration_s`
    (to within one `dt`); the cache key gains `schedule` and `t2_override_sha`.
B2. `--t2-override <json>` (default none): a file `{ "source": ..., "per_qubit": { "<physical>": {"T2_s": ...,
    "provenance": "measured|upper_bound|patch_minimum|record"} } }`; before `AerSimulator.from_backend` the
    backend's `target.qubit_properties` is replaced by a new list in which the listed qubits carry the override
    T2 (T1 unchanged; T2 clipped to ≤ 2 T1 with a warning that is recorded); the record written to
    `data/hardware/<...>/calibration_<stamp>.json` keeps the original T2 and gains `t2_override` with the table.
    Provide `scripts/h0_t2_override.py --from-diag validation/H0_diag.json --job J1 --out <json>` that builds the
    file from the `ramw` inversion by the M-T2 rule (patch 1: 117 72.5 us measured, 122 36.5, 124 17.7, 136 35.9,
    142 18.6, 143 15.2, 146 19.4; 123 and 145 the 3σ upper bounds 13.3 and 13.4; 125, 141, 144 the patch minimum
    13.3 us — check these against `H0_diag.json:data.idle_tests.J1.ramw.per_qubit` and print the table).
B3. Outputs added to `validation/H0P*.json` (no criterion touched): per (sector, repetition) the mixture estimate
    (A1) of the simulated counts, the reference-string test (A2) for the k = 1 circuits, and — when
    `--schedule asap` — the analytic PTA bound at the T2 actually used (`skqd.idle.f_idle_aware` on the same
    record; if `skqd.idle` is not yet committed, `h0_support_plan.f_from_calibration` x the P1-snippet budget) so
    that the sandwich `PTA ≤ Aer-scheduled clean f ≤ Aer-unscheduled clean f` is printed as information (H0P-Y' is
    the owner's).
B4. FakeFez check (runner): `python scripts/gate_H0P.py --backend FakeFez --only-ids B0_ref06_k1_rep1
    --shots-by-rep 1:2000 --seed 11 --schedule asap --cal-shots 0 --no-prereg --no-tests --out H0P_sched_check`
    (add `--only-ids` and `--cal-shots 0` if missing; about 5 min): the seeded counts must give **73 accepted and 21
    reference hits** (P9); with `--schedule none` **328 / 178**.  Delete the `H0P_sched_check` artefacts afterwards
    (test outputs, not gate outputs) or keep them under `validation/` only if `update_status.py` is told to skip them.

### C. Gate `H0_model` — the post-diction of the existing counts (`scripts/gate_H0_model.py`, `run_gate.py H0_model`; about 3 h + 45 min of Aer)
C1. **Estimator validation on Aer samples** (FakeFez, canary circuit, seed 11, 2000 shots each, unscheduled and
    scheduled — reuse B4's counts): the mixture estimate of clean accepted shots versus the reference-count estimate
    `n_ref / p_ref` on the same sample; criterion: within 25 % on both samples (expected about 202 and 24 clean
    accepted).  Record the near-clean count `accepted − clean − N a (1 − f)` for each (about 111 and 31).
C2. **The pooled device clean count** from the five pubs of `B0_ref06_k1_rep1` (counts directories above):
    reproduce P8's table (per pub: accepted, reference hits, expected if clean, P(≤ seen), the distance histogram)
    and the pooled reference test; criterion: `P_ge` of the pooled test < 0.05 (expected 0.017) — the clean
    component exists.  Also the mixture estimate per pub (informational; J1 expected w ≈ 0.06 with a wide interval).
C3. **The bracket post-diction on the live record 7fd6d65e** (`data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json`
    loaded through a `FakeFez` object whose target is overwritten with the record's 30 x 9 + 54 x 4 numbers — write
    `h0_backends.backend_from_record(record, base=FakeFez())` and assert `calibration_record(backend_from_record(r))`
    fingerprints equal r's): Aer scheduled, canary circuit, seed 11, 8000 shots in four 2000-shot invocations
    (< 30 min each), once with the record's T2 (echo end) and once with the T2 override of B2 (T2* end).  For each
    end: the mixture clean count, the reference hits, the accepted count, the distance histogram.  **Criterion C3:
    the T2* end's predicted clean reference hits, scaled to 8267 shots, lie within a factor 3 of the measured 4.0
    (i.e. in [1.33, 12.0]).**  The echo end is recorded with its ratio (expected far above; information).
C4. **Acceptance structure**: the T2* end's predicted accepted count for 2000 shots against J1's 35; criterion
    within a factor 2.  The distance histogram's chi-square against J1's [2, 0, 13, 5, 1, 6, 0, 5, 0] is
    information.
C5. Status PASS iff C1, C2, C3, C4.  JSON: `validation/H0_model.json` with every table above, the T2 override table
    with provenance, the fingerprint of the record, the Aer settings, the runtimes.  Report
    `reports/H0_model_postdiction_2x2.md` generated from the JSON.  `update_status.py`: row `H0_model` ("post-diction
    of the H0 hardware counts by the scheduled-Aer model at both ends of the T2 bracket; the clean-yield
    statistic", laptop).  Also add the two planner reports to the reports table.

### D. Information tables in gate_H0 (`scripts/gate_H0.py`; about 1 h; the criteria block is NOT edited)
D1. `--clean-statistic {yield,mixture}` (default `yield`): with `mixture`, `data.f_comparison_mixture` carries the
    A1 estimate on both the prediction's simulated counts (from the H0P JSON, which B3 now stores) and the hardware
    counts, with the same `relative_deviation` arithmetic, **as information**; `data.reference_string_tests` (A2)
    for every k = 1 circuit under either setting.  Regression: `python scripts/gate_H0.py --counts
    data/hardware/H0_dryrun/counts --out H0_dryrun` PASS 9/9 with `criteria[*].value` identical to the committed
    file; `python scripts/gate_H0.py --counts data/hardware/H0_ibm_fez_canary/counts --out H0_canary
    --predict-from validation/H0P_ibm_fez.json --calibration data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json`
    reproduces the committed `criteria[*].value` exactly (the file is regenerated with the same status FAIL 3/6 and
    the added tables; commit it as a regeneration, noting it in the LOG).

### E. The free device survey and the full-device patch search (`scripts/h0_device_survey.py`; about 2 h; 0 QPU seconds; runner may execute)
E1. For each of `ibm_fez`, `ibm_marrakesh`, `ibm_kingston` (a NEW backend object per device via `resolve_backend`;
    skip a device that is not reachable and say so): write a **full-device** record in exactly the
    `h0_backends.calibration_record` format — all qubits, all coupling edges, `dt_s`, `default_rep_delay_s`,
    `fingerprint` over the four blocks, `last_update_date`, `stamp` — to
    `data/hardware/device_survey_20260922/<backend>_<stamp>.json`.  This is the input the in-flight
    `scripts/h0_patch_select.py --calibration <record>` reads (do not modify that script; if its reader needs a
    field the record lacks, add the field to the record, never to the script).  Read-only metadata; 0 QPU seconds.
E2. Per device the P12 statistics on live data: T2 percentiles (10/25/50/75/90), fractions ≥ 50/100/150 us, and
    the largest connected components with readout ≤ 3 % and CZ error ≤ 1 % at T2_min ∈ {40, 60, 80, 100, 120, 150}
    us (BFS over the coupling map; no networkx dependency).
E3. Per device: `python scripts/h0_patch_select.py --calibration data/hardware/device_survey_20260922/<backend>_<stamp>.json
    --md reports/H0_patch_select_<backend>_20260922.md` (about 90 s per 1500 candidates) — the exhaustive embedding
    search of the frozen canary circuit's tree.  Record the winner, its f_gates, S_T1, S_T2, PTA clean f, its
    weakest three qubits by T2, and two budgets at that f, both labelled as the echo-T2 end: the D3' budget (P11
    interpolated in 1/f) and the D3''-H0 budget (140/f shots per k = 1 circuit + 21 x 267 + 6216 + 14 x 4000, at
    the record's durations and rep delay).
E4. `reports/H0_device_survey_20260922.md`: the E2 tables, the E3 winners per device, and the sentence the owner
    needs: best device/patch, its echo-end PTA f, both budgets, and the note that the measured S_eff on patch 1
    was 1.73x the echo-PTA value while the T2* end is unknown until the pilot.  No number outside the JSONs.

### F. Bookkeeping
F1. `pytest -q tests`; `python scripts/check_package.py`; `graphify update .`; `python scripts/update_status.py`;
    the CLAUDE.md status paragraph (scribe: two sentences on H0_diag's outcome, the clean-yield finding, and the
    H0_model status); LOG row; commits: "prompts/20 part A–B: clean-yield estimator, scheduled-Aer path with T2
    override", "gate H0_model: <status> (C3 ratio <value>)", "prompts/20 part D–E: gate_H0 information tables,
    device survey".  Push per the owner's rule.

### STOP — hand back to the owner; nothing is submitted, no circuit is frozen
The hand-back names: `validation/H0_model.json` status and the C3 ratio at both ends; the pooled clean count line;
the survey's winning patch per device with its PTA clean f and both budgets; the nine named changes of analysis
section 8 as a checklist (D8', D1', D3'-f, D3''-H0, D5', C2', C3', H0P-Y', M4.4) each with "sign / amend / reject"; and the
production command that prompts/21 will use verbatim: `python scripts/h0_submit.py --backend <device> --prep
<new prep> ... --dd off --twirling off`.  The planner writes prompts/21 (the pilot on the selected patch, about 10 s
of QPU) only after the owner's answers.

## Pass criteria
- `pytest -q tests`: all pass; the A4 tests present (w within 0.02 at N_acc = 1e4; flat → 0; the pooled reference
  test reproduces expected 2.018, P_ge 0.017 ± 0.001, f_clean 6.65e-4 ± 1e-6).
- B4: `--schedule asap` gives 73 accepted / 21 reference hits on FakeFez seed 11 (2000 shots); `--schedule none`
  328 / 178; non-delay op multisets identical; `n_delays` 519.
- `validation/H0_model.json`: C1 both ratios within 25 %; C2 `P_ge` < 0.05 (value 0.017 ± 0.001); C3 the T2*-end
  clean reference hits scaled to 8267 shots in [1.33, 12.0]; C4 accepted within a factor 2 of 35; status PASS iff
  all four.  The echo-end numbers present with their ratios.  Runtimes per invocation < 30 min.
- Regressions: `validation/H0_dryrun.json` PASS 9/9 with identical `criteria[*].value`; `validation/H0_canary.json`
  regenerated with identical `criteria[*].value`; the prompts/15 A1 one-liner prints "H0P_repro identical" after
  `python scripts/gate_H0P.py --shots-by-rep 1:267 2:130 3:92 --budget-minutes 14 --pilot-shots 60 --cal-shots 4000
  --seed 11 --out H0P_repro --no-prereg --no-tests` (default `--schedule none`; about 20 min).
- `data/hardware/device_survey_20260922/` holds one full-device record per reachable device in the
  `calibration_record` format; `reports/H0_patch_select_<backend>_20260922.md` exists for each (written by the
  in-flight script, unmodified); `reports/H0_device_survey_20260922.md` has the E2 and E3 tables for each; every
  number in it is in the JSONs.
- `git status` shows none of the do-not-touch files modified by this prompt (`git diff --stat` against the start
  commit lists none of them); no file under any `counts/` directory or `data/hardware/H0_prep/` changed.

## Outputs
`src/skqd/skqd.py` (+ `skqd.krylov` helper), `tests/test_clean_yield.py`, `scripts/gate_H0P.py` (flags),
`scripts/h0_t2_override.py` (new), `scripts/gate_H0_model.py` (new), `scripts/gate_H0.py` (information tables),
`scripts/h0_device_survey.py` (new), `scripts/h0_backends.py` (`backend_from_record`), `scripts/update_status.py`
(row); `validation/H0_model.json`, `reports/H0_model_postdiction_2x2.md`, `data/hardware/H0_model/` (the Aer
sample counts of C1/C3 with their settings), `data/hardware/device_survey_20260922/*.json`,
`reports/H0_device_survey_20260922.md`, `reports/H0_patch_select_<backend>_20260922.md` (x 3); regenerated `validation/H0_dryrun.json`, `validation/H0_canary.json`,
`validation/H0P_repro.json`; `prompts/LOG.md` rows; `reports/PROJECT_STATUS.md`, `validation/gates.md`, CLAUDE.md
status.  Push: yes on the owner's rule; nothing is submitted to any device.

## Escalation
- C3 fails at the T2* end **and** the echo end is also outside [1.33, 12.0]: neither end of the bracket describes
  the device; write `validation/BLOCKED.md` with both post-dictions, the distance histograms and the T2 tables,
  and stop — the planner returns at max.  Do not tune T2, T1 or the estimator's background to make it pass.
- C1 fails (the estimator is biased by > 25 % on an Aer sample): the uniform background is inadequate for that
  distribution — stop after recording the two estimates; do not change the criterion; hand back (the planner will
  decide between a flip-neighbour background and the reference-string statistic alone).
- B1: scheduling changes a non-delay operation count on any circuit, or the scheduled duration differs from
  `h0_qpu_time.circuit_duration_s` by more than one dt: stop, report the circuit and both op lists.
- B2: the T2 override does not change the seeded counts on FakeFez (assignment of `qubit_properties` did not reach
  the noise model): verify with the prompts/17 PC 3 pattern (a hard perturbation must change the counts) before
  concluding; if it still does not, stop and report.
- E1: a device unreachable or its target lacking T2 for more than 10 % of qubits: report it, survey the others.
- 30-minute rule: every Aer invocation is capped at 2000 shots (about 5 min scheduled); the survey rungs are about
  1 min each; H0P_repro about 20 min.  If any command exceeds 30 min, split it and record it in the LOG.
- Two honest failures on the same step: stop and hand back with the traceback verbatim.
