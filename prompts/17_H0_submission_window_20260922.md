# 17 — H0 submission window (2026-09-22): the preflight must test the calibration CONTENT of the frozen patch, not its timestamp
executor: executor-opus   effort: high (xhigh on the second attempt)   (runner-sonnet low for the regressions of A''5, the
watch log of A''8, the retrieval polling and the gate runs; scribe-haiku low for the status tables; the OWNER at STOP A and
STOP B; planner-fable max only when an escalation clause below fires or after validation/H0.json exists)
time budget: part A'' (engineering on the laptop, no QPU, no account needed except A''7) <= 1 day, every command < 30 min;
A''7 (regenerate the day's prediction, read-only target access, 0 QPU seconds) about 10 min from the sampling cache or
about 30 min if the calibration content has moved; the session (part B'') as prompts/16 part B': about 2.5 h of laptop
time in commands < 30 min, queue waits excluded; QPU execution 69.69 s estimated on the 20260922T0711Z calibration
(`data/hardware/H0_ibm_fez/qpu_time_estimate_20260922T0711Z.json`, cap 120 s)
machine: laptop (CPU) + read-only ibm_fez metadata; the QPU only at B''6 and B''8 with the owner's go

> Written by planner-fable at max effort after part B' of prompts/16 (LOG row of 2026-09-22, commits 0c6b6f1 and 79f4dae)
> measured that its own submission guard cannot be satisfied: the chain B'2 -> B'4 takes 28m40s, an owner decision sits
> between the prediction and the submission, and ibm_fez changes its `last_update_date` every 30-56 minutes.  The
> guard is replaced by the check it was a proxy for, with **no tolerance**; nothing else changes.  No QPU time was spent
> for this prompt and none is authorised by it except at the two owner go points, exactly as in prompts/15 and 16.
> Every number below is read from a JSON of the repository (the key is named) or is a **planner computation [PC]** made
> on 2026-09-22 with repository data and code; every [PC] has its reproduction snippet in the appendix and is pinned by a
> pass criterion of part A''.

## Goal
Make the H0 session (prompts/15 part B as corrected by prompts/16 part B') executable: keep the guarantee of prompts/15
frozen item 2 — the preregistered prediction is the one made on the calibration the jobs are submitted under — while
removing a refusal that fires when nothing the prediction depends on has changed.  Then re-issue STOP A with the
0711Z prediction (regenerated with the new fields) and run the canary, the main submission and gate H0 unchanged.

## Failure (prompts/LOG.md row of 2026-09-22, commit 79f4dae; the data files named)
- `scripts/h0_submit.py:preflight` refuses to submit when the live `last_update_date` of ibm_fez differs from
  `validation/H0P_ibm_fez.json:data.calibration.last_update_date` (prompts/15 frozen item 2, A3) and from the shot
  plan's (prompts/16 F3); `scripts/gate_H0P.py` refuses a shot plan or a cache file whose date differs from the live
  one (prompts/16 F2).
- ibm_fez `last_update_date` observed (all -06:00): 2026-09-21T14:53:59 (`calibration_20260921T2053Z.json`),
  2026-09-21T23:44:00 (`calibration_20260922T0544Z.json`), 2026-09-22T00:20:08 (`calibration_20260922T0620Z.json`),
  2026-09-22T01:11:12 (`calibration_20260922T0711Z.json`).  Inter-update windows: 30m17s (14:23:42 -> 14:53:59, the
  planner's observation of 2026-09-21), 36m08s, 51m04s, and one still open at >= 56 min (01:11:12 -> 02:07, when the
  plan stamp still equalled the live one).  No cadence to plan around.
- Critical path B'2 -> B'4 measured 28m40s (01:34:50 -> 02:03:30): plan 116 s, estimate 9 s, the three `--sample-only`
  classes concurrently 23m39s wall (22m04s / 18m55s / 23m39s; about 29 min if sequential), analysis 175 s.  Every
  invocation inside the 30-minute rule.
- Attempt 1 (stamp 20260922T0544Z): B'2 125 s, B'3 10 s, B=0 r=1 sampled in 9m30s, B=1 r=1 in 8m46s, then the r=2/3
  invocation was refused after 28 s because the date had moved to 00:20:08.  The 0620Z stamp produced only a
  calibration record.  Attempt 2 (0711Z) completed: `validation/H0P_ibm_fez.json` **PASS 18/18** — N4 8100 (B=0) /
  19600 (B=1), r=1 shots 44505 / 40802, 259523 shots in all, `min_lambda_r1_at_margin` 6.3060 / 6.3006 >= 6.2958,
  supports 38/38 and 20/20 with `missing_states == []`, |E_R - E_0| = 0.0 in both sectors, `total_execution_s`
  69.690 <= 120, `missing_errors == []`.  Against the 2026-09-21 values (N4 8200 / 19700, r=1 shots 45005 / 41002)
  the substance barely moved although the timestamp did — the clue.
- A watcher holding one `resolve_backend()` object reported a stale `last_update_date` for 71 min (a 45 s poller missed
  the 01:11:12 update): `IBMBackend.properties()` is cached per object.

## Diagnosis
**The timestamp is not the calibration of the patch.**  [PC 1] Define the *fingerprint* of a calibration record as the
sha256 of the JSON (`sort_keys=True`, `separators=(",", ":")`) of its four blocks `dt_s`, `default_rep_delay_s`,
`qubits` (30 qubits x {measure_error, measure_duration_s, sx_error, sx_duration_s, x_error, x_duration_s,
rz_duration_s, T1_s, T2_s}) and `edges` (54 edges x {target_key, directed_pairs_of_the_frozen_set, cz_error,
cz_duration_s}) — everything `calibration_record` stores except the device metadata (`last_update_date`, `stamp`,
`status`, `basis_gates`, `max_circuits`).  Over the four committed records:

| record | `last_update_date` | fingerprint (first 16 hex) | leaves changed vs the previous record |
|---|---|---|---|
| calibration_20260921T2053Z.json | 2026-09-21T14:53:59-06:00 | 54c0a533945c6178 | — |
| calibration_20260922T0544Z.json | 2026-09-21T23:44:00-06:00 | d937c672ec9fce9a | 30 (all `measure_error`; cz, T1, T2, sx, x, durations untouched) |
| calibration_20260922T0620Z.json | 2026-09-22T00:20:08-06:00 | d937c672ec9fce9a | 0 |
| calibration_20260922T0711Z.json | 2026-09-22T01:11:12-06:00 | d937c672ec9fce9a | 0 |

Three consecutive timestamp changes, zero changes in the 30 x 9 + 54 x 4 numbers the prediction reads.  The only content
change on record (14:53:59 -> 23:44:00) was a readout recalibration of all 30 qubits: ratios new/old from 0.3735 (qubit
141) to 2.6571 (qubit 146), median 0.9952, mean readout error 0.011918 -> 0.011833.  The readout errors are quantized in
steps of 1/8192 (all 120 values in the four records are integer multiples, 26 to 586 [PC 1]); a re-measurement returning
the same integer on all 30 qubits and the same cz error on all 54 edges is not plausible, so the three stamp updates of
the night came from calibrations of other parts of the 156-qubit device or of quantities the record does not hold —
none of which enters the prediction.

**What the prediction depends on.**  `gate_H0P.py` on a live backend samples the frozen QPY circuits (unchanged, D1) with
`AerSimulator.from_backend(backend, seed_simulator=11)` at the plan's shots.  `qiskit_aer.noise.NoiseModel.from_backend`
(aer 0.17.2, read today) builds the model from `backend.target` only: the readout error of each measured qubit from
`target["measure"][(q,)].error` (symmetric), a depolarizing + thermal-relaxation error for every instruction from its
`.error`, `.duration` and the `target.qubit_properties` T1/T2 of the qubits it acts on, and a `RelaxationNoisePass` that
acts on `Delay` instructions only (the frozen set has none: barrier, cz, measure, rz, sx, x).  The clean-shot fraction f
(`gate_S2D.analyse_on_backend`) is the product over the circuit's cz and measure instructions of (1 - error).  The QPU
time estimate uses the target's durations, `dt` and `default_rep_delay`.  All of it is local to the 30 qubits and 54
edges of the frozen set and all of it is in the record — the fingerprint is exactly the set of inputs.  [PC 3, FakeFez,
circuit B0_ref06_k1_rep1, 300 shots, seed 11]: perturbing qubit 0 (outside the patch: measure error 0.3, a cz error 0.2,
T1 x 0.5) leaves the seeded Aer counts **and** the fingerprint identical; perturbing qubit 117 (inside: measure error
0.3, or sx error 0.2, or the used cz edge (117, 125) x 1.5, or T1 x 0.5) changes both.  One caveat that shapes the unit
test: a x 1.5 readout change on one qubit left the 300 seeded shots identical although the noise model had changed
(0.00854 -> 0.01282; 1.3 expected flipped decisions, P(none) = 0.28 [PC]) — the fingerprint inequality is the assertion,
and the counts assertion needs a hard perturbation.

**Consequences.**  (i) The 0544Z and 0711Z plans have identical `f_by_circuit` and identical `shots_by_circuit`
[PC 2] and the identical estimate 69.690 s: the prediction refused at 00:20:08 and the one accepted at 01:11:12 are the
same prediction.  (ii) The exact-stamp rule refuses submission in exactly the cases where re-running B'2-B'4 reproduces
the prediction bit for bit (same circuits, seed, shots, noise model).  (iii) It is unsatisfiable by construction even
without a human: between the prediction and the main submission sit the canary's queue wait, execution and retrieval
polling, none under our control, on top of the 28m40s chain; the stamp cadence is IBM's.  (iv) f is insensitive to what
actually changed: between 2053Z and 0711Z the r=1 circuits' f moved by -0.68 % to +0.48 % (max over all 84 circuits
1.26 %, an r=3 circuit) while individual readout errors moved by factors up to 2.66 [PC 2].  (v) The cache trap: in
qiskit-ibm-runtime 0.49.0 `IBMBackend.target` calls `properties()` (cached) and `_convert_to_target()` which rebuilds
only `if refresh or not self._target`; `properties(refresh=True)` alone therefore leaves a stale target.
`IBMBackend.refresh()` (exists in 0.49.0) refreshes configuration, properties and target; a new
`service.backend(name)` object also starts clean.

## Decisions (planner; fixed before any device data exist)

**D9 — The preflight tests calibration identity of the frozen patch, with no tolerance.**  Submission (canary and main,
`--submit` and `--submit --resume`) requires, read from a backend object created or `refresh()`ed in the same
invocation: (a) the fingerprint of the live calibration record equals the fingerprint of the record the prediction was
made from (`validation/H0P_<backend>.json:data.calibration.path`, and `data.calibration.fingerprint` when present) and,
with `--shots-plan`, equals the plan's `calibration.fingerprint`; (b) the live f of every one of the 84 frozen circuits
(`analyse_on_backend`) equals the plan's `f_by_circuit[c]` and the prediction's
`f_recomputed_on_the_day.per_circuit[c].f_live` to 1e-9 (`h0_support_plan.F_CROSSCHECK_TOL`); (c) the like-for-like
checks of prompts/16 F3 (plan shots == prediction shots) and every other preflight item of prompts/15 A3 unchanged.
The live `last_update_date` is recorded (with `stamp_match` true/false) but not required.  The live record is written
to `<out>/calibration_at_submission_<live stamp>.json` before the decision, so a refusal leaves its evidence on disk.

*Why not the bounded-drift candidate (live f of the r=1 circuits within a tolerance of the prediction's).*  Rejected on
the data: (1) f is the wrong quantity — in the one content change on record it moved 0.7 % while per-qubit readout
errors moved by x 2.66; the readout-drift item of gate H0 (prompts/15 D7, RO_FACTOR 3) and the confusion-matrix
prediction of criterion 4 (simulated minimum diagonal 0.9603) are per qubit and reference the prediction's record, so an
f-window of even 1 % would have accepted a prediction whose per-qubit reference was stale by a factor 2.66 against a
factor-3 criterion; (2) any tolerance on the prediction side of criterion 2 shifts its effective window by that
tolerance — a loosening by construction, however small; (3) there is one drift observation in the repository, which is
not data to set a tolerance from.  Identity needs no tolerance.

*Why D9 is a correction and not a loosening.*  Frozen item 2 of prompts/15 exists so that the preregistered prediction
is the one made on the calibration the jobs run under; the stamp was its proxy.  As a predicate on the world the
fingerprint accepts a superset of the stamp rule (stamp equal implies content equal), but every additional accepted case
is one in which re-running the prediction is a no-op: same inputs, same seed, bit-identical JSON — shown on FakeFez
[PC 3], shown on the device by the identical 0544Z/0711Z plans [PC 2], and pinned by the tests of F6.  The guarantee
is unchanged; a false refusal is removed.  In two respects the guard becomes stronger: it compares the 30 x 9 + 54 x 4
numbers and cross-checks 84 clean-shot fractions instead of one string, and it writes the submission-time record next
to the prediction-time and retrieval-time records.  It is the opposite of D3' in direction (D3' added shots; D9 removes
a refusal) and the same in kind: the check now tests the premise it was written for.  Like D3' it uses no device
outcome — no counts exist — only calibration metadata, so it is preregistration-consistent.  What the fingerprint does
not cover (other qubits of the device) the prediction never modelled either; crosstalk from outside the patch is
outside the model in both directions, and the retrieval-time record keeps the run-time drift on file as before.

**D10 — Re-prediction on a content change; the owner's go stands across a rule-based re-prediction.**  If the live
fingerprint at any submission differs from the prediction's, B''2-B''4 are re-run on the new content (plan, estimate,
`--refresh-cache` on all classes, analysis; 28m40s wall on this laptop), committed, and the submission is retried.
This is prompts/15 frozen item 2's own instruction ("re-run step B3, commit, submit; no owner re-go is needed unless
the stop rule of B3 fires") with "stamp" read as "content".  The go therefore stands provided the re-prediction is PASS
18/18, the r=1 simulated yields are >= 0.05 (the B3 stop rule), the estimate is <= 120 s (D6, enforced by the
preflight), and the plan was built by the same rule D3' (margin 0.7, floor 267, lambda* 6.2958, seed 11).  The numbers
of the re-prediction are posted to the owner in the prompts/16 B'5 format, but not waited for — unless the owner marks
the go as **"single"** (this prediction only), in which case a fresh go is awaited.  The STOP A hand-back asks the
owner to say "standing" or "single"; unspecified means "standing", i.e. prompts/15 frozen item 2.  The canary's go
rules (D5: DONE, usage <= 30 s, round trip 0 mismatches, >= 10 accepted of 267, confusion diagonal >= 0.9) do not
reference the prediction file, so a canary GO stands across a re-prediction.  A first go is always required: nothing
here lets the executor run the canary or the main without one.

**D11 — The sampling cache is keyed by fingerprint.**  The seven files of `data/hardware/H0_ibm_fez/sim_cache`
(committed at 0c6b6f1; `calibration_last_update_date` 2026-09-22T01:11:12-06:00) are valid for any stamp whose patch
content equals theirs.  Each gets `calibration_fingerprint` added (a metadata edit; the `counts` block is hash-verified
unchanged), and they are refused only when the fingerprint moves — then all seven are re-sampled with `--refresh-cache`
and the superseded files stay in git.  The same for `data/hardware/H0_rehearsal_cache` (FakeFez).

**Whether the 0711Z prediction can still be used.**  Yes, for as long as the live fingerprint equals
d937c672ec9fce9ab8cf51ed58c70c41b05cd9d4599daee2c42492377886a848 (A''7 verifies this on the day and regenerates the
JSON with the new fields from the cache in about 5 min, 0 QPU seconds).  If the content has moved by then, B''2-B''4
are re-run in full (D10); the 0711Z artefacts stay in git as the record of the night.

## What changes (named) and what does not
1. **prompts/15 frozen item 2**, the refusal condition of `--submit`: "the live `last_update_date` differs" becomes "the
   live calibration fingerprint of the frozen patch differs, or the live f of any frozen circuit differs from the plan's
   or the prediction's by >= 1e-9".  The commit hash and the live stamp are still written to session.json; the
   fingerprints (prediction, submission) and `calibration_at_submission_<stamp>.json` are added.
2. **prompts/16 F2**: the plan check of `gate_H0P.py` ("the plan's `calibration.last_update_date` must equal the live
   target's") and the cache key set (`calibration_last_update_date`, `shot_plan_stamp`) become fingerprint-based; the
   stamps stay in the files as information.  **prompts/16 F3**: the like-for-like check on the date becomes the check
   on the fingerprint.  **prompts/16 B'4**: "every cache file, the plan and the calibration record must carry the same
   `last_update_date`" reads "the same fingerprint".
3. **prompts/15 B7 and its escalation clause**: "if the calibration `last_update_date` moved since B3, re-run B3" reads
   "if the fingerprint moved"; `--submit --resume` only while the fingerprint is unchanged.
4. **Outputs added, no criterion touched**: `fingerprint` in the calibration record, the plan's `calibration` block,
   `validation/H0P_<backend>.json:data.calibration`, the prereg paragraph (one sentence), session.json, the cache files
   and the retrieval record; the new `scripts/h0_calwatch.py` and its log `calibration_watch.jsonl`.
Unchanged: `data/hardware/H0_prep` byte for byte; D1 (strengthened: the prediction is re-made whenever the patch content
changes, and identity is verified on the numbers, not on a string), D2, D3' (margin 0.7, floor 267, round-to 100,
lambda* 6.2958), D4-D8; the four prereg criteria and their constants (F_TOLERANCE 0.30, RANDOM_ACCEPT_MAX 0.01, E0_TOL
1e-6, DIAG_MIN 0.9, RO_FACTOR 3.0, READOUT_FACTOR 0.82); the canary composition and go rules; the caps (estimate <= 120 s,
usage <= 180 s); the decoder; the two H0P plan criteria; `scripts/gate_H0.py` (not edited by this prompt: its D7 item
keeps the prediction's record as reference).

## Inputs
- prompts/15 (D1-D8, frozen items 1-5, A3, B4-B7, escalation), prompts/16 (F2, F3, B'2-B'10, pass criteria of part B'),
  `reports/H0P_ibm_fez_escalation_20260921.md` (D3'), prompts/LOG.md row of 2026-09-22 (the measurements above).
- `validation/H0P_ibm_fez.json` (commit 0c6b6f1; PASS 18/18; `data.calibration.path` =
  `data/hardware/H0_ibm_fez/calibration_20260922T0711Z.json`; `data.shot_plan_file` =
  `data/hardware/H0_ibm_fez/shot_plan_20260922T0711Z.json`), the four `data/hardware/H0_ibm_fez/calibration_*.json`,
  `shot_plan_20260922T0544Z.json` / `shot_plan_20260922T0711Z.json`, `qpu_time_estimate_20260922T0711Z.json`
  (`total_execution_s` 69.69011163999998), `data/H0_shot_plan_live_20260921_reference.json` (the 2026-09-21 plan),
  `data/hardware/H0_ibm_fez/sim_cache/*.json` (seven files, seed 11, `shot_plan_stamp` 20260922T0711Z),
  `data/hardware/H0_rehearsal_cache/*.json`.
- Code: `scripts/h0_backends.py` (`resolve_backend`, `last_update_date`, `calibration_stamp`, `calibration_record`,
  `frozen_qubits_and_edges`), `scripts/h0_support_plan.py` (`load_calibration`, `f_from_calibration`,
  `F_CROSSCHECK_TOL = 1e-9`, the `calibration` block of the plan), `scripts/gate_H0P.py` (`cache_stamp`, `load_cache`,
  `expect()`, the plan check at the `--shots-plan` branch, `data["calibration"]`, the prereg text),
  `scripts/h0_submit.py` (`preflight`, `submit_phase`, `retrieve_phase`, session.json keys),
  `scripts/gate_S2D.py:analyse_on_backend`, `tests/test_h0_scripts.py` (`_cache_expect`,
  `test_cache_refuses_a_mismatched_field`, `test_f_from_a_calibration_record_equals_analyse_on_backend`).
- Installed stack: qiskit 2.5.2 (Rust-backed `Target`: `target["measure"][(q,)]` returns fresh property objects, so
  in-place edits of `.error` do NOT reach the target — use `Target.update_instruction_properties` and assign
  `target.qubit_properties = <list>`; measured today [PC 3]), qiskit-aer 0.17.2, qiskit-ibm-runtime 0.49.0
  (`IBMBackend.refresh()`, `properties(refresh=...)`, `_convert_to_target(refresh=...)` as described above;
  `FakeBackendV2.refresh(service)` needs a service argument — never call it on a fake backend).

## Fix (exact)
F1. **`scripts/h0_backends.py`.**  `FINGERPRINT_FIELDS = ("dt_s", "default_rep_delay_s", "qubits", "edges")`;
    `calibration_fingerprint(rec)` = `hashlib.sha256(json.dumps({k: rec[k] for k in FINGERPRINT_FIELDS},
    sort_keys=True, separators=(",", ":")).encode()).hexdigest()` (this exact serialization: the pass criteria pin the
    hashes); `calibration_record` adds the keys `fingerprint` (computed from the four blocks, so it excludes itself) and
    `fingerprint_fields`; `calibration_diff(a, b)` -> `{"n_leaves", "families" (leaf names such as measure_error),
    "leaves": [{"path", "before", "after", "ratio"}...], "max_ratio", "min_ratio"}` over the four blocks (status,
    stamps excluded); `fresh_calibration(backend, qubits, edges)` calls `backend.refresh()` when `backend` is a
    `qiskit_ibm_runtime.IBMBackend` (never on a fake backend) and returns `calibration_record(...)`.  Every live read of
    the calibration in the scripts below goes through `fresh_calibration`.
F2. **`scripts/h0_support_plan.py`.**  The plan's `calibration` block gains `fingerprint`: from `--calibration <file>` the
    fingerprint of the file; from `--backend <live>` the fingerprint of `fresh_calibration(backend, ...)` on the same
    target the f values are read from; both given -> assert equal (as the existing `backend_vs_calibration_file_max_df`
    check).  For a fake backend the fingerprint of its snapshot record.
F3. **`scripts/gate_H0P.py`.**  (i) The `--shots-plan` live check compares the plan's `calibration.fingerprint` with the
    fingerprint of the record just written (`calibration["fingerprint"]`); a plan without the field is a SystemExit
    ("re-run h0_support_plan.py"); the message on mismatch prints `calibration_diff` (n leaves, families, max ratio).
    (ii) `cache_stamp` compares `backend, seed, sector, repetition, calibration_fingerprint` and the per-circuit shots;
    `calibration_last_update_date`, `shot_plan_stamp`, `shots_plan_file` stay in the files as information; a cache file
    without `calibration_fingerprint` is refused with a message naming the A''6 migration.  `expect()` and the cache
    writers carry `calibration_fingerprint` (live: the record's; fake: the snapshot record's).  (iii)
    `data["calibration"]["fingerprint"]` and `["fingerprint_fields"]`; the prereg paragraph gains one sentence after
    the calibration paragraph: "Submission rule (prompts/17 D9): the jobs are submitted only while the live calibration
    of these 30 qubits and 54 edges is identical to this record (fingerprint `<fp>`) and the live clean-shot fraction of
    all 84 circuits equals the plan's to 1e-9; the calibration timestamp at submission is recorded and may differ from
    the one above when IBM's update touched other parts of the device."  (iv) The `--shots-by-rep` path stays
    byte-identical in its outputs (A''5 re-checks "H0P_repro identical").
F4. **`scripts/h0_submit.py`.**  (i) Factor the calibration gate into a pure function
    `calibration_gate(live_record, prediction, plan, f_live_by_circuit)` -> `(problems, record)` so it is testable on
    the committed files; `preflight` calls it with `live_record = fresh_calibration(backend, *frozen_qubits_and_edges(
    prep))` and `f_live_by_circuit = {id: analyse_on_backend(load_circuit(prep, m), backend)["f"]}` over the 84 coarse
    circuits (about 10 s).  Problems, each a refusal: prediction fingerprint != live; plan fingerprint != live (with
    `--shots-plan`); `max |f_live - plan f_by_circuit| >= 1e-9`; `max |f_live - prediction f_live| >= 1e-9`; the existing
    shots like-for-like; the existing prompts/15 A3 items.  The stamp comparison becomes `record["stamp_match"]` (bool)
    and is printed, never a problem.  (ii) Before the decision, write `<out>/calibration_at_submission_<live stamp>.json`
    (the live record) and put its path in the record.  (iii) session.json gains `calibration_fingerprint`,
    `prediction_calibration_fingerprint`, `shots_plan_calibration_fingerprint`, `fingerprint_match`, `stamp_match`,
    `f_live_vs_plan_max_abs_diff`, `calibration_at_submission_file`; dry runs write `None` for the live-only keys.
    (iv) `--status --record-calibration` (also honoured by `--retrieve` once every job is terminal) writes
    `<out>/calibration_at_retrieval_<stamp>.json` with a fresh record and stores `retrieval_calibration_file`,
    `retrieval_calibration_fingerprint`, `retrieval_fingerprint_match` (vs the prediction's) and
    `retrieval_calibration_diff` (the summary of `calibration_diff`) in session.json — the prompts/15 B7 record, now
    scripted.  (v) `--submit --resume` runs the same preflight (unchanged behaviour; the check is now the fingerprint).
F5. **New `scripts/h0_calwatch.py`** (0 QPU seconds; metadata queries only).  `--backend <name> --reference
    <calibration_<stamp>.json> --out <jsonl>` with `--once` or `--minutes M --every S` (M <= 25 so one invocation
    respects the 30-minute rule; default `--every 300`).  Every poll builds a NEW backend object via `resolve_backend`
    (the cache trap), takes `fresh_calibration`, and appends one JSON line: `utc`, `last_update_date`, `stamp`,
    `fingerprint`, `operational`, `pending_jobs`, `match_reference` (fingerprint == the reference file's),
    `stamp_changed` / `content_changed` vs the previous line, `n_leaves_changed`, `families`.  `--once` prints the line
    and exits 0 when `match_reference` is true, 3 otherwise (script-checkable).  `--summary <jsonl>` prints the stamp
    windows and the fingerprint windows (durations between changes, the open one, min / median / max) — the data the
    next timing decision needs and does not yet have.
F6. **Tests (`tests/test_h0_scripts.py`).**  (a) `test_fingerprint_of_the_committed_records`: the four files give
    54c0a533945c6178a4c5f75584f657d3188a415b6faed7406843796f0a80a795 and, for 0544Z, 0620Z, 0711Z alike,
    d937c672ec9fce9ab8cf51ed58c70c41b05cd9d4599daee2c42492377886a848.  (b)
    `test_calibration_diff_reports_the_readout_recalibration`: diff(2053Z, 0544Z) has 30 leaves, families
    == {"measure_error"}, min ratio 0.3735 +- 5e-4 (qubit 141), max ratio 2.6571 +- 5e-4 (qubit 146); diff(0544Z, 0620Z)
    and diff(0620Z, 0711Z) have 0 leaves.  (c) `test_fingerprint_is_the_noise_model_key` (FakeFez, B0_ref06_k1_rep1, 300
    shots, seed 11, about 1 min): a perturbation of qubit 0 through `update_instruction_properties` (measure error 0.3,
    the first cz key containing 0 set to error 0.2) and `qubit_properties` (T1 x 0.5, T2 clipped to <= 2 T1) leaves the
    counts equal and the fingerprint equal; a measure error 0.3 on qubit 117 changes both; the used cz edge (117, 125)
    x 1.5 changes both; T1 of qubit 117 x 0.5 changes both.  (d) the cache tests: a record differing only in
    `calibration_last_update_date` / `shot_plan_stamp` is accepted; a differing `calibration_fingerprint` or a missing
    one is refused naming the field.  (e) `test_calibration_gate_on_the_committed_records`: live = the 0620Z record with
    the prediction pointing at the 0711Z record and f equal -> no problem and `stamp_match == False`; live = the 2053Z
    record -> a problem whose text names 30 leaves and `measure_error`; a single f differing by 2e-9 -> a problem.
    (f) `fresh_calibration` calls `refresh()` exactly once on a dummy `IBMBackend`-typed object (monkeypatched
    `isinstance`) and never on FakeFez.  (g) `h0_calwatch --summary` on a synthetic 6-line log reproduces hand-computed
    windows.
F7. **Migration of the cache files** (A''6): add `calibration_fingerprint` (and `calibration_fingerprint_source` naming
    the record file) to the seven `sim_cache` files from `calibration_20260922T0711Z.json` and to the
    `H0_rehearsal_cache` files from the FakeFez snapshot record; assert the sha256 of `json.dumps(counts, sort_keys=True)`
    is unchanged file by file (snippet 5 of the appendix).

## Steps

### Part A'' — laptop, no QPU (A''7 needs the account for read-only metadata)
A''1. Implement F1-F5 (about 3 h).  `graphify update .` afterwards.
A''2. `pytest -q tests` (about 4 min with the FakeFez test).  All pass; the new tests of F6 present.
A''3. Reproduce the pinned planner computations with the appendix snippets 1 and 2 (10 s): the printed hashes, leaf
      counts, ratios and f drifts must match the values quoted there.
A''4. Snippet 3 (about 1 min) prints `True True` for the out-of-patch perturbation and `False False` for both in-patch
      ones (the same facts as test (c)).
A''5. Regressions (runner-sonnet): `python scripts/gate_H0.py --counts data/hardware/H0_dryrun/counts --out H0_dryrun`
      (PASS 9/9, `criteria[*].value` identical to the committed file); `python scripts/gate_H0P.py --shots-by-rep 1:267
      2:130 3:92 --budget-minutes 14 --pilot-shots 60 --cal-shots 4000 --seed 11 --out H0P_repro --no-prereg --no-tests`
      (about 20 min) followed by the prompts/15 A1 one-liner ("H0P_repro identical"); the prompts/16 A'4 dry-run
      submission test (`/tmp/plan_small.json`, 6 jobs, 126 counts files, all `counts_written: true`; delete the
      H0_plan_test artefacts); `python scripts/check_package.py`.
A''6. Migrate the cache files (F7, snippet 5; seconds).  `git diff --stat data/hardware/H0_ibm_fez/sim_cache` shows
      seven files changed by the two added keys only.
A''7. The day's prediction, regenerated with the new fields (read-only target access, 0 QPU seconds):
      `python scripts/h0_calwatch.py --backend ibm_fez --once --reference data/hardware/H0_ibm_fez/
      calibration_20260922T0711Z.json --out data/hardware/H0_ibm_fez/calibration_watch.jsonl` (seconds).
      - **Exit 0 (content unchanged, fingerprint d937c672...)**: `python scripts/h0_support_plan.py --backend ibm_fez
        --out data/hardware/H0_ibm_fez/shot_plan_<live stamp>.json --report reports/H0_support_plan_ibm_fez.md`
        (116 s; required: `calibration.fingerprint` == d937c672..., `shots_by_circuit` and `f_by_circuit` identical to
        `shot_plan_20260922T0711Z.json`'s, N4 8100 / 19600); `python scripts/h0_qpu_time.py --backend ibm_fez
        --shots-plan data/hardware/H0_ibm_fez/shot_plan_<live stamp>.json --cal-shots 4000 --out
        data/hardware/H0_ibm_fez/qpu_time_estimate_<live stamp>.json` (9 s; `total_execution_s` <= 120, expected
        69.690); then the analysis invocation of prompts/16 B'4 through the cache: `python scripts/gate_H0P.py --backend
        ibm_fez --shots-plan data/hardware/H0_ibm_fez/shot_plan_<live stamp>.json --sample-cache
        data/hardware/H0_ibm_fez/sim_cache --seed 11 --cal-shots 4000 --budget-minutes 28 --out H0P_ibm_fez` (175 s;
        no class re-sampled: every `sampled_now` false) -> `validation/H0P_ibm_fez.json` PASS 18/18 with
        `data.calibration.fingerprint` == d937c672... and every criterion value except the pytest line identical to
        commit 0c6b6f1's (snippet 4), `reports/H0P_ibm_fez_heron_preparation.md`, `reports/H0_prereg_ibm_fez.md` with
        the D9 sentence.  Commit: "H0 session day (3): calibration-content preflight (prompts/17 D9); prediction
        regenerated at <stamp>, fingerprint d937c672".
      - **Exit 3 (content moved)**: prompts/16 B'2-B'4 in full on the new content (the three sampling invocations with
        `--refresh-cache`, concurrently as in the LOG, each < 30 min; 28m40s wall), stop rules of prompts/16 B'2-B'4
        unchanged (min lambda >= 6.2958 by construction, estimate <= 120 s, r=1 yields >= 0.05, PASS 18/18, 38/38 and
        20/20).  Commit: "H0 session day (3): re-predicted on the ibm_fez calibration <stamp> (fingerprint <fp>)".
        If the content moves again during this re-run: stop, run `h0_calwatch.py --summary`, hand to the planner.
A''8. Start the watch log (runner-sonnet; relaunch as needed while the session waits for the owner):
      `python scripts/h0_calwatch.py --backend ibm_fez --minutes 25 --every 300 --reference
      data/hardware/H0_ibm_fez/calibration_<stamp of A''7>.json --out data/hardware/H0_ibm_fez/calibration_watch.jsonl`.
      The log is committed with the session artefacts (about 12 lines per hour).
A''9. Bookkeeping: `python scripts/update_status.py` (no new gate row; the H0P_ibm_fez row's description gains
      "(prompts/17: submission keyed on the calibration content)"), the CLAUDE.md status paragraph (scribe), the LOG
      row for part A''; commit "prompts/17 part A'': calibration-content preflight, fingerprint-keyed cache, watch log";
      push.

### STOP A (re-issued) — hand back to the owner; do not run B''6 in the same turn
The message of prompts/16 B'5 (N4 per sector, r=1 shots per sector, `P_saturation_clean_at_margin` per sector, support
sizes 38/38 and 20/20, `total_execution_s`; the prompts/15 B4 items: prereg path and commit, r=1 predicted yields and f
next to the FakeFez values, the canary command verbatim) plus: the prediction's fingerprint and its record file; the
`--summary` of the watch log (how many stamps and how long the fingerprint has held); the one-sentence rule D9; the
question **"standing or single go?"** (D10; unspecified = standing); and the go timing below.

**Go timing (both cases).**
- *The go arrives while the live fingerprint equals the prediction's* (the preflight's `--once` check, seconds):
  B''6 at once; the stamp may have moved — that is recorded, not a refusal.
- *The go arrives after the fingerprint moved*: B''2-B''4 as in A''7's second branch (28m40s, 0 QPU seconds),
  commit, then B''6 under the standing go, or after a fresh go if the owner said "single".
- *The go arrives before part A'' is committed*: the canary and the main wait for A'' — except that, if A''1 has not
  started (tree clean at 79f4dae) and the live stamp still equals 20260922T0711Z, the runner may run the canary of
  prompts/16 B'6 from that tree (0.21 s of QPU; its guard passes on the stamp).  The main submission waits for A'' in
  every case.

### Part B'' — the session (prompts/16 B'6-B'10 with the fingerprint preflight)
B''6. Canary exactly as prompts/15 B5 / prompts/16 B'6: `python scripts/h0_submit.py --backend ibm_fez --only
      B0_ref06_k1_rep1 cal_patch1_all0 cal_patch1_all1 --shots 267 --cal-shots 267 --out data/hardware/H0_ibm_fez_canary`
      (its preflight now applies D9: `fingerprint_match` must be true); commit session.json at once; `--retrieve --wait
      1500` until DONE; `gate_H0.py --counts data/hardware/H0_ibm_fez_canary/counts --out H0_canary --predict-from
      validation/H0P_ibm_fez.json --calibration <the prediction's record>`; the go one-liner of prompts/15 B5 unchanged.
B''7. STOP B as prompts/16 B'7 (the canary line, queue wait, usage, accepted vs 39.9 predicted, the main command
      verbatim, the fingerprint status at that moment).
B''8. Main: `python scripts/h0_submit.py --backend ibm_fez --shots-plan data/hardware/H0_ibm_fez/shot_plan_<stamp>.json
      --cal-shots 4000 --out data/hardware/H0_ibm_fez` (6 jobs; the preflight writes `calibration_at_submission_
      <stamp>.json`); commit session.json at once; retrieval loop as prompts/16 B'8 (pending-limit alternation of
      prompts/16 F3 if needed; `--resume` only while `fingerprint_match` holds); `python scripts/h0_submit.py --status
      --record-calibration --out data/hardware/H0_ibm_fez` once all jobs are terminal (the retrieval record); commit the
      counts "H0 raw counts from ibm_fez (never modified)".
B''9. Gate H0 exactly as prompts/16 B'9: `python scripts/run_gate.py H0 --push --timeout 1800 --counts
      data/hardware/H0_ibm_fez/counts --out H0 --predict-from validation/H0P_ibm_fez.json --calibration
      data/hardware/H0_ibm_fez/calibration_<stamp of the prediction>.json`.
B''10. Bookkeeping as prompts/16 B'10, adding the three fingerprints (prediction / submission / retrieval) with their
      stamps, `retrieval_calibration_diff` if any, and the watch-log summary; then planner-fable (max) writes prompt 18
      (the post-H0 decision on the 2x3 plan) whether H0 passed or failed.

## Pass criteria
Part A'':
- `pytest -q tests`: all pass; the seven tests of F6 present (at least 91 tests collected on this tree).
- Snippet 1 prints `54c0a533945c6178a4c5f75584f657d3188a415b6faed7406843796f0a80a795` for 2053Z and
  `d937c672ec9fce9ab8cf51ed58c70c41b05cd9d4599daee2c42492377886a848` for 0544Z, 0620Z and 0711Z; `30 leaves changed;
  ['measure_error']`, then `0 leaves changed; []` twice; the ratio line `min 0.3735 (q141) max 2.6571 (q146) median
  0.9952`; `h0_backends.calibration_fingerprint` on the same files returns the same hashes.
- Snippet 2 prints `f_by_circuit identical True shots identical True`; r=1 drift `-0.00683 .. +0.00479`, max over 84
  `0.01263`; N4 `8200 -> 8100` / `19700 -> 19600`; r1 shots `45005 -> 44505` / `41002 -> 40802`.
- Snippet 3: `counts identical True fingerprint identical True` (out of patch), `False False` (measure 0.3 on 117),
  `False False` (sx 0.2 on 117).
- `validation/H0_dryrun.json`: PASS 9/9, `criteria[*].value` identical to the committed file.
- `validation/H0P_repro.json`: the prompts/15 A1 one-liner prints "H0P_repro identical".
- `/tmp/h0_plan_test/session.json`: 6 jobs, all `counts_written: true`, 126 counts files (prompts/16 A'4 shape);
  `calibration_fingerprint` null (dry run).
- Every file of `data/hardware/H0_ibm_fez/sim_cache` and `data/hardware/H0_rehearsal_cache` carries
  `calibration_fingerprint` (d937c672... for the seven live files) and its `counts` sha256 is unchanged (snippet 5
  prints `unchanged` for every file).
- A''7, branch "exit 0": `validation/H0P_ibm_fez.json` status PASS, 18 criteria, `data.calibration.fingerprint ==
  d937c672ec9fce9ab8cf51ed58c70c41b05cd9d4599daee2c42492377886a848`, snippet 4 prints "H0P_ibm_fez regenerated
  identical"; the new plan's `shots_by_circuit` and `f_by_circuit` equal the 0711Z plan's; `total_execution_s <= 120`;
  `reports/H0_prereg_ibm_fez.md` contains the D9 sentence with that fingerprint.  Branch "exit 3": the part-B' criteria
  of prompts/16 B'2-B'4 with "last_update_date" read as "fingerprint" (`data.calibration.fingerprint` == the plan's ==
  every cache file's), PASS 18/18, 38/38 and 20/20, r=1 yields >= 0.05, `total_execution_s <= 120`.
- `data/hardware/H0_ibm_fez/calibration_watch.jsonl` exists with >= 1 line and `h0_calwatch.py --summary` runs.
Part B'':
- B''6: "canary GO"; `data/hardware/H0_ibm_fez_canary/session.json:preflight.fingerprint_match == true`.
- B''8: `data/hardware/H0_ibm_fez/session.json`: `preflight.fingerprint_match == true`, `calibration_at_submission_file`
  present, 6 jobs DONE, 126 counts files, `total_usage_s` (canary + 6 jobs) <= 180, `retrieval_calibration_fingerprint`
  recorded (equal or not to the prediction's — informational, prompts/15 escalation (d) governs the drift item).
- B''9: `validation/H0.json` PASS on the criteria of prompts/07 and the prereg, unchanged (prompts/15 B8 items 1-5
  verbatim).

## Outputs
scripts/{h0_backends,h0_support_plan,gate_H0P,h0_submit}.py (extended), scripts/h0_calwatch.py (new),
tests/test_h0_scripts.py; data/hardware/H0_ibm_fez/sim_cache/*.json and data/hardware/H0_rehearsal_cache/*.json
(fingerprint field); data/hardware/H0_ibm_fez/{shot_plan_<stamp>.json, qpu_time_estimate_<stamp>.json,
calibration_<stamp>.json, calibration_watch.jsonl}; validation/H0P_ibm_fez.json (regenerated; the 0c6b6f1 version stays
in git); reports/{H0_support_plan_ibm_fez,H0P_ibm_fez_heron_preparation,H0_prereg_ibm_fez}.md;
validation/{H0_dryrun,H0P_repro}.json (regressions); part B'': data/hardware/H0_ibm_fez_canary/*,
data/hardware/H0_ibm_fez/{calibration_at_submission_<stamp>.json, calibration_at_retrieval_<stamp>.json, session.json,
counts/*.json (126)}, validation/{H0_canary,H0}.json, reports/{H0_canary_hardware_2x2,H0_hardware_2x2}.md; prompts/LOG.md
rows for part A'' and part B''; reports/PROJECT_STATUS.md, validation/gates.md, CLAUDE.md status.  Push: yes after part
A'' and after every commit of part B''.  `git status data/hardware/H0_prep` clean at every commit; scripts/gate_H0.py,
src/skqd/codec.py and src/skqd/reference_sim.py untouched (`git diff --stat` shows none of them).

## Escalation
- A''2 / A''4: the out-of-patch perturbation changes the seeded counts -> the fingerprint is not a sufficient key: stop,
  write validation/BLOCKED.md with the perturbation and both counts dicts; do not fall back to the stamp rule and do not
  widen the fingerprint without the planner.  An in-patch perturbation that leaves the counts identical while the
  fingerprint differs is the readout rare-draw effect of the diagnosis: perturb harder (0.3), never weaken the assertion
  on the fingerprint.
- A''3: the pinned hashes are not reproduced -> the serialization differs from F1's; fix the implementation, never the
  pinned values.
- A''5: "H0P_repro identical" or the H0_dryrun identity fails -> the fake path changed; two attempts, then BLOCKED.md.
- A''7: the content moves twice during one re-prediction, or the watch log shows fingerprint windows shorter than the
  prediction's wall time -> stop and hand the `--summary` to the planner; the remedies are a shorter prediction (more
  concurrent `--only-ids` invocations, or the desktop) or a different time of day — never a weaker guard.
- Go timing: a go that arrives after the fingerprint moved is D10; a go marked "single" is awaited again after any
  re-prediction; the executor never submits without a go.
- B''6-B''10: the escalation clauses of prompts/15 and prompts/16 apply verbatim, with "last_update_date unchanged" read
  as "fingerprint unchanged" in the resume rule.  A retrieval-time fingerprint that differs from the prediction's is not
  a failure of this prompt: it is the drift prompts/15 D7 and escalation (d) were written for, and it is on record.
- 30-minute rule: every command above is capped by construction (`--minutes 25`, `--wait 1500`, the sampling split);
  if one exceeds 30 min, split it as prompts/16 says and record it in the LOG.

## Appendix — reproduction of the [PC] numbers (repository data and code only)

Snippet 1 — fingerprints and diffs of the four committed records (1 s; needs no repository code):
```
python - <<'EOF'
import json, hashlib, numpy as np
F = ("dt_s", "default_rep_delay_s", "qubits", "edges")
fp = lambda r: hashlib.sha256(json.dumps({k: r[k] for k in F}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
S = ["20260921T2053Z", "20260922T0544Z", "20260922T0620Z", "20260922T0711Z"]
R = {s: json.load(open(f"data/hardware/H0_ibm_fez/calibration_{s}.json")) for s in S}
for s in S: print(s, R[s]["last_update_date"], fp(R[s]))
def flat(d, p=""):
    o = {}
    for k, v in d.items():
        if isinstance(v, dict): o.update(flat(v, p + k + "/"))
        else: o[p + k] = v
    return o
for a, b in zip(S, S[1:]):
    fa, fb = flat({k: R[a][k] for k in F}), flat({k: R[b][k] for k in F})
    d = [k for k in fa if fa[k] != fb[k]]
    print(a, "->", b, len(d), "leaves changed;", sorted({k.split("/")[-1] for k in d}))
a, b = R[S[0]]["qubits"], R[S[1]]["qubits"]
r = {q: b[q]["measure_error"] / a[q]["measure_error"] for q in a}
print("measure_error ratio 0544Z/2053Z: min %.4f (q%s) max %.4f (q%s) median %.4f" % (
    min(r.values()), min(r, key=r.get), max(r.values()), max(r, key=r.get), np.median(list(r.values()))))
print("all measure_error values are multiples of 1/8192:",
      all(abs(v["measure_error"] * 8192 - round(v["measure_error"] * 8192)) < 1e-9 for s in S for v in R[s]["qubits"].values()))
EOF
```

Snippet 2 — the two plans of the night and the f drift since 2026-09-21 (1 s):
```
python - <<'EOF'
import json
p21 = json.load(open("data/H0_shot_plan_live_20260921_reference.json"))
p44 = json.load(open("data/hardware/H0_ibm_fez/shot_plan_20260922T0544Z.json"))
p11 = json.load(open("data/hardware/H0_ibm_fez/shot_plan_20260922T0711Z.json"))
print("0544Z vs 0711Z: f_by_circuit identical", p44["f_by_circuit"] == p11["f_by_circuit"],
      "shots identical", p44["shots_by_circuit"] == p11["shots_by_circuit"])
rel = {c: p11["f_by_circuit"][c] / p21["f_by_circuit"][c] - 1 for c in p21["f_by_circuit"]}
r1 = [c for c in rel if c.endswith("rep1")]
print("f 2053Z -> 0711Z: r=1 circuits %+.5f .. %+.5f; max |rel| over 84 %.5f" % (
    min(rel[c] for c in r1), max(rel[c] for c in r1), max(abs(v) for v in rel.values())))
for s in ("B=0", "B=1"):
    print(s, "N4 %d -> %d, r1 shots %d -> %d, f_mean_r1 %.6f -> %.6f" % (
        p21["sectors"][s]["N4"], p11["sectors"][s]["N4"], p21["sectors"][s]["r1_shots_total"],
        p11["sectors"][s]["r1_shots_total"], p21["sectors"][s]["f_mean_r1"], p11["sectors"][s]["f_mean_r1"]))
EOF
```
Expected: `True True`; `-0.00683 .. +0.00479; max 0.01263`; `B=0 N4 8200 -> 8100, r1 shots 45005 -> 44505, f_mean_r1
0.178843 -> 0.179700`; `B=1 N4 19700 -> 19600, r1 shots 41002 -> 40802, f_mean_r1 0.178182 -> 0.178004`.

Snippet 3 — the fingerprint is the key of the seeded Aer prediction (FakeFez, about 1 min; the content of test (c)):
```
python - <<'EOF'
import sys, json, hashlib
sys.path.insert(0, "scripts"); sys.path.insert(0, "src")
from gate_H0P import load_circuit, load_manifests
from h0_backends import calibration_record, frozen_qubits_and_edges
from qiskit_aer import AerSimulator
from qiskit.transpiler import InstructionProperties
from qiskit.providers import QubitProperties
from qiskit_ibm_runtime.fake_provider import FakeFez
prep = "data/hardware/H0_prep"; qubits, edges = frozen_qubits_and_edges(prep)
mans, _ = load_manifests(prep); m = next(x for x in mans if x["id"] == "B0_ref06_k1_rep1"); qc = load_circuit(prep, m)
F = ("dt_s", "default_rep_delay_s", "qubits", "edges")
fp = lambda r: hashlib.sha256(json.dumps({k: r[k] for k in F}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def run(perturb=None, shots=300):
    b = FakeFez(); t = b.target
    if perturb: perturb(t)
    rec = calibration_record(b, qubits, edges)
    return AerSimulator.from_backend(b, seed_simulator=11).run(qc, shots=shots).result().get_counts(), fp(rec)
base, fp0 = run()
def out_of_patch(t):
    p = t["measure"][(0,)]; t.update_instruction_properties("measure", (0,), InstructionProperties(duration=p.duration, error=0.3))
    e0 = next(k for k in t["cz"].keys() if 0 in k); pe = t["cz"][e0]
    t.update_instruction_properties("cz", e0, InstructionProperties(duration=pe.duration, error=0.2))
    qp = list(t.qubit_properties); q = qp[0]
    qp[0] = QubitProperties(t1=q.t1 * 0.5, t2=min(q.t2, q.t1 * 0.999), frequency=q.frequency); t.qubit_properties = qp
def in_patch_measure(t):
    p = t["measure"][(117,)]; t.update_instruction_properties("measure", (117,), InstructionProperties(duration=p.duration, error=0.3))
def in_patch_sx(t):
    p = t["sx"][(117,)]; t.update_instruction_properties("sx", (117,), InstructionProperties(duration=p.duration, error=0.2))
for name, pert in (("out-of-patch q0", out_of_patch), ("in-patch measure q117 = 0.3", in_patch_measure), ("in-patch sx q117 = 0.2", in_patch_sx)):
    c, f = run(pert); print(name + ": counts identical", c == base, "fingerprint identical", f == fp0)
EOF
```
Expected: `True True`, `False False`, `False False`.  (Measured today in addition: the used cz edge (117, 125) x 1.5 and
T1 of qubit 117 x 0.5 both change the counts; a x 1.5 measure error on qubit 117 left 300 seeded shots identical
although the NoiseModel's readout error on that qubit had changed from 0.00854 to 0.01282 — 1.3 expected flipped
decisions, e^-1.3 = 0.28.)

Snippet 4 — identity of the regenerated prediction with commit 0c6b6f1 (A''7, branch "exit 0"):
```
python - <<'EOF'
import json, subprocess
new = json.load(open("validation/H0P_ibm_fez.json"))
old = json.loads(subprocess.check_output(["git", "show", "0c6b6f1:validation/H0P_ibm_fez.json"]))
vals = lambda d: [c["value"] for c in d["criteria"] if not str(c["name"]).startswith("pytest")]
assert vals(new) == vals(old), "criteria values differ"
A, B = new["data"]["analysis"], old["data"]["analysis"]
assert all(A["by_sector_repetition"][k][f] == B["by_sector_repetition"][k][f] for k in B["by_sector_repetition"]
           for f in ("yield", "f_calibration_mean", "model_yield_full", "garbage_acceptance"))
assert all(A["by_sector"][s]["ER"] == B["by_sector"][s]["ER"] for s in B["by_sector"])
assert A["confusion_summary"]["min_diagonal"] == B["confusion_summary"]["min_diagonal"]
assert new["data"]["sampling"]["shots_by_circuit"] == old["data"]["sampling"]["shots_by_circuit"]
print("H0P_ibm_fez regenerated identical; fingerprint", new["data"]["calibration"]["fingerprint"])
EOF
```
(For the record: the 0c6b6f1 values are leakage 1.4876988529977098e-14, |E_R - E_0| 0.0 / 0.0, min lambda 6.306 /
6.3006, acceptance 0.928 % / 0.488 %, yield ratios 1.102 / 1.608 / 1.529 / 1.043 / 1.619 / 0.995, confusion 0.9603;
yields B=0 r=1 0.17069992135715087, B=1 r=1 0.15643840988186852; E_R -3.6407665507263425 / -1.8615880345350209.)

Snippet 5 — the cache migration of A''6 (seconds; after F1 exists):
```
python - <<'EOF'
import json, glob, hashlib, sys
sys.path.insert(0, "scripts")
from h0_backends import calibration_fingerprint, calibration_record, frozen_qubits_and_edges, resolve_backend
h = lambda d: hashlib.sha256(json.dumps(d["counts"], sort_keys=True).encode()).hexdigest()
live = "data/hardware/H0_ibm_fez/calibration_20260922T0711Z.json"
ref = json.load(open(live)); fp_live = calibration_fingerprint(ref)
q, e = frozen_qubits_and_edges("data/hardware/H0_prep")
fp_fake = calibration_fingerprint(calibration_record(resolve_backend("FakeFez"), q, e))
for pattern, fp, src, date in (("data/hardware/H0_ibm_fez/sim_cache/*.json", fp_live, live, ref["last_update_date"]),
                               ("data/hardware/H0_rehearsal_cache/*.json", fp_fake, "FakeFez snapshot record", "snapshot")):
    for p in sorted(glob.glob(pattern)):
        d = json.load(open(p)); assert d["calibration_last_update_date"] == date, p
        before = h(d)
        d["calibration_fingerprint"], d["calibration_fingerprint_source"] = fp, f"{src} (prompts/17 A''6 migration)"
        json.dump(d, open(p, "w"), indent=1)
        print(p, fp[:16], "unchanged" if h(json.load(open(p))) == before else "COUNTS CHANGED -- STOP")
EOF
```
