# 15 — H0: first QPU session on ibm_fez (2x2 calibration run, manual Step 9.1, gate H0)
executor: executor-opus   effort: high   (runner-sonnet low for the retrieval polling and the gate runs; scribe-haiku low for
the status tables; the two go/no-go points before QPU submission are the OWNER's; planner-fable max only after
validation/H0.json exists or when an escalation clause below fires)
time budget: part A (engineering, no QPU) 1 day, every command < 30 min; part B (session day) every laptop command
< 30 min, QPU queue waits excluded; QPU execution 46.7 s estimated (0.78 min of the open plan's 10 min per month)
machine: laptop (CPU) for everything classical + QPU ibm_fez (IBM Quantum Platform, open plan, instance `open-instance`)
prerequisites met: H0P PASS (validation/H0P.json, commit 2392fb3), H0_dryrun PASS (validation/H0_dryrun.json), the IBM
account saved and checked on 2026-09-21 (`scripts/ibm_account.py --check`: the frozen set runs "as frozen" on ibm_fez,
ibm_marrakesh and ibm_kingston, all Heron r2, 156 qubits, operational), owner's device choice: **ibm_fez** (2026-09-21)

> Written by planner-fable at max effort.  Nothing in this prompt relaxes a threshold: the H0 criteria are the four of
> prompts/07 and reports/H0_prereg_draft.md section 4 (decoder validity with random-string acceptance < 1 %, measured f
> within 30 % of the prediction for the r = 1 circuits through `clean_fraction_from_yield`, Ritz energies to 1e-6,
> readout-confusion diagonal >= 0.9), unchanged.  Every number below is from validation/*.json, data/*.json, or the
> live-target measurements of 2026-09-21 listed under Inputs; the few derived statistics are labelled "planner
> arithmetic" with their inputs.

## Goal
Run the first QPU session of the project: the 2x2 calibration run of manual Step 9.1 on ibm_fez with the frozen
circuit set of `data/hardware/H0_prep` (84 coarse-step circuits, r = 1, 2, 3 repetitions of the coarse step at 663 /
1305 / 1920 CZ, plus 42 readout-calibration circuits on 3 patches), and evaluate gate H0 from the raw counts with
`scripts/gate_H0.py` exactly as it ran on the dry run.  H0 decides whether the 2x3 production budget is spent
(prompts/07 escalation clause): the measured clean-shot fraction f at 663 CZ is the number every later shot budget
rests on (`shot_rule`, manual eq. 5).  Two things stand between the repository and the session: (i) the
preregistration requires the predicted yields to be recomputed from the calibration of the session day, and the
scripts cannot yet resolve a live backend (`h0_build_circuits.py:96,113`, `gate_H0P.py:267-271` hard-code FakeFez /
FakeTorino); (ii) `h0_submit.py` blocks on `job.result()` inside its submission loop and holds the only copy of the
job IDs in memory.  Part A fixes both without touching the frozen circuits; part B is the session, with two owner
stop points before any QPU submission.

## Inputs
- prompts/07 (H0 steps, criteria, escalation), prompts/13 and prompts/14 (H0P, the yield model y = 0.82 f + (1-f) a),
  reports/H0_prereg_draft.md (the draft preregistration; section 2 states the recompute-on-the-day requirement),
  reports/H0P_heron_preparation.md, reports/H0_dryrun_hardware_2x2.md
- validation/H0P.json (commit 2392fb3): frozen set of 2026-09-16 09:57:38 MDT, leakage max 1.49e-14; r = 1 f
  (FakeFez snapshot) 0.1261 (B=0) / 0.1214 (B=1); a = 0.00928 / 0.00488 (exhaustive over 4096 strings); simulated
  r = 1 yields 0.1493 / 0.1353 (pinned shots 267 / 130 / 92 per r = 1 / 2 / 3 circuit, seed 11, 13692 shots, 4000
  calibration shots per circuit, runtime 1179 s); predicted f = clean_fraction_from_yield(0.1493, 0.00928) = 0.1727
  and 0.1600; full-model yields 0.1115 / 0.1038; confusion diagonal min 0.9768; E0 = -3.6408 / -1.8616
- validation/H0_dryrun.json: 126 counts files in 4 SamplerV2 jobs (one per distinct shot count 92 / 130 / 267 / 4000),
  58/58 accepted strings re-encode, measured f 0.1710 / 0.1571 vs predicted 0.1727 / 0.1600 (deviations 0.9 % /
  1.8 %), readout-error ratio vs snapshot worst 1.28, dry-run runtime 1044 s
- data/hardware/H0_prep/index.json: the 28 r = 1 circuits read out on patch 1 (24 circuits, qubits
  [117, 122, 123, 124, 125, 136, 141, 142, 143, 144, 145, 146]) and patch 2 (4 circuits); patch 0 carries the r = 2, 3
  circuits; `B0_ref06_k1_rep1` (663 CZ, patch 1) is the canary circuit of step B5
- scripts: h0_build_circuits.py, gate_H0P.py, h0_submit.py, gate_H0.py, ibm_account.py (`open_service`,
  `frozen_requirements`, `check_backend` — reuse them), gate_S2D.py (`analyse_on_backend`: it reads only
  `backend.target` — `t["cz"][edge].error`, `t["measure"][(q,)].error`, `t[sx|x|rz]` — so it should work on a live
  `IBMBackend`; step A1 verifies this instead of assuming it), src/skqd/hardware.py (`confusion_matrix` raises unless
  every qubit is prepared in both 0 and 1 — the canary therefore carries all-0 AND all-1 of its patch), src/skqd/skqd.py
  (`yield_model`, `clean_fraction_from_yield`, `shot_rule`, READOUT_FACTOR = 0.82)
- Installed stack (introspected 2026-09-21): qiskit 2.5.2, qiskit-ibm-runtime 0.49.0 (channel `ibm_quantum_platform`
  only), qiskit-aer 0.17.2.  `RuntimeJobV2.usage()`, `.metrics()`, `.status()`, `.done()` and
  `QiskitRuntimeService.job(job_id)` exist; `SamplerOptions.execution` has `init_qubits`, `meas_type`, `rep_delay`;
  `SamplerOptions.environment.job_tags` exists; `IBMBackend.max_circuits` exists (None on FakeFez).
- Live ibm_fez target, measured 2026-09-21 by the planner (recomputed and recorded by step B2): dt 4 ns; sx / x 24 ns;
  cz 68-88 ns; measure 1660 ns; default_rep_delay 250 us, rep_delay_range [0, 2 ms].  ASAP schedule of the frozen
  QPY circuits with the shot plan 1:267 2:130 3:92 and 4000 calibration shots: r = 1: 28 circuits, 46.0 us each,
  2.2 QPU s; r = 2: 28 circuits, 89.2 us, 1.2 s; r = 3: 28 circuits, 133.9 us, 1.0 s; readout calibration: 42
  circuits, 1.7 us, 4000 shots, 42.3 s; total 181692 shots, 46.7 s = 0.78 min.  Queue at check time: ibm_fez 1
  pending job (marrakesh 5, kingston 2).  The frozen set uses 30 physical qubits, 54 distinct two-qubit edges and the
  basis {cz, rz, sx, x, measure}, all present with calibration data on the live coupling map.

## Planner decisions (fixed before any data exist; the reasons are part of the preregistration)

**D1 — The circuits stay frozen; only the prediction is recomputed on the day.**  The prereg's sentence "re-run
`h0_build_circuits.py --backend <device>`" is replaced by this rule: `data/hardware/H0_prep` (QPY + manifests +
index.json, commit 2392fb3) is submitted byte-for-byte as validated by H0P and by `ibm_account.py --check` on the live
map.  Re-transpiling on the live target would let level-3 layout selection choose a different patch from the day's
error rates, producing a set that neither H0P nor the dry run ever saw.  What IS recomputed on the day, from the live
`backend.target`: the per-circuit clean-shot fraction f (`analyse_on_backend` on the frozen circuit against the live
errors), the full-model yield, the Aer device-model simulation (`AerSimulator.from_backend(<live ibm_fez>)`, same
pinned shots and seed as H0P) and the per-qubit readout errors.  The builder's live path (step A1) exists only as the
contingency of step B3b (re-freeze if the frozen patch has collapsed on the live calibration) and writes to a NEW
directory; it never touches `H0_prep`.

**D2 — Readout calibration stays at 4000 shots per circuit.**  The calibration is 168000 of the 181692 shots and 42.3
of the 46.7 QPU seconds (90.6 %) because every shot costs about the same on this device (planner arithmetic from the
live durations: 252 us per calibration shot vs 294 us per r = 1 shot — the 250 us rep delay dominates both), so the
share is purely the shot count.  It is kept because the factor-3 readout-drift item of `gate_H0.py` needs it: the
best qubit of the frozen patches has a snapshot readout error of 0.0024 (physical 84, validation/H0_dryrun.json), its
P(1|1) is estimated from the 2 preparations in which it is 1, and the expected number of error events is 2 N e =
4.9 at N = 1000 but 19.5 at N = 4000 (planner arithmetic; Poisson: the probability that at least one of the 36
qubit-patch entries falls below a third of its reference by statistics alone is 0.81 at N = 1000 and 0.013 at
N = 4000).  The diagonal >= 0.9 criterion alone would be satisfied with far fewer shots (sigma of a diagonal element
0.0024 at N = 4000), but the drift item and the day's measured readout survival — the quantity prompts/14's
escalation named as the replacement for the fixed 0.82 — are worth 42 s of a 600 s month.  The rep delay is NOT
reduced to save time: a shorter delay changes the initial state (residual excitation), i.e. the physics, for a saving
the budget does not need.  Whole-session execution 46.7 s leaves >= 9 min of the month for a second session if H0
asks for one.

**D3 — Coarse-step shots stay at 1:267 2:130 3:92, like-for-like with the H0P simulation.**  The r = 1 comparison
then has equal statistical weight on both sides: at the simulated yields, sigma_f / f = 3.5 % (B=0, 5340 shots) and
5.7 % (B=1, 2136 shots), so the two-sample sigma of the measured / predicted f ratio is 4.9 % / 8.0 % (planner
arithmetic from validation/H0P.json) against a 30 % criterion.  More device shots would not sharpen a comparison
whose prediction side is simulated at 267 shots, and the r = 2, 3 points measure the shape of the yield-versus-CZ
curve (informational, prompts/13), not f.  Any denser r = 1 or r = 3 measurement (e.g. for a precise readout factor)
is a planner decision after H0, funded from the >= 9 min left.  The shot rule's support budget (60872 / 63270 shots
per r = 1 circuit at the clean yield, reports/H0_prereg_draft.md section 3) is NOT spent here, as the prereg says.

**D4 — Submit-then-retrieve is REQUIRED before the session.**  `h0_submit.py` currently calls `job.result()` inside
the loop: the process blocks for the full queue time of each job in series (4 jobs, one per distinct shot count), the
job IDs live only in memory until the loop ends, and a dead process (laptop sleep, network drop, the 30-minute rule)
loses the pointers to the raw data — the one artefact of this project that cannot be recomputed.  A queue of 1-5
jobs at check time says nothing about the wait at submission time on a fair-share open plan.  The change is small
(step A3): every `sampler.run` writes its job ID to `session.json` before the next submission, all groups are
submitted back-to-back so they queue in parallel, and `--retrieve` turns finished jobs into counts files from the
IDs.  The dry run exercises the same functions in one process; only `service.job(job_id)` is live-only, and the
canary (D5) exercises that.

**D5 — A canary job precedes the main submission.**  One job of 3 pubs at 267 shots: `B0_ref06_k1_rep1` (663 CZ,
patch 1) plus `cal_patch1_all0` and `cal_patch1_all1` — 801 shots, about 0.21 s of execution (planner arithmetic
from the live durations: 267 x 297.7 us + 534 x 251.8 us).  It is the first live use of the SamplerV2 options (the local testing mode of the dry run
ignores DD and twirling: "Options ... have no effect in local testing mode", data/hardware/H0_dryrun/session.json),
of the classical-register order on a real job, of `--retrieve`, and of the per-job usage accounting of the open
plan — all cheaper to learn on 801 shots than on 181692.  Go rules (script-checkable, step B5): the job reaches DONE
and `usage()` is recorded; every accepted string re-encodes to itself; at least 10 of the 267 shots are accepted (the
prediction is 39.9 accepted at the simulated yield 0.1493; a device delivering only garbage, y = a = 0.0093, gives
2.5 accepted and reaches 10 with probability 2.3e-4 — planner arithmetic from validation/H0P.json); the confusion
diagonal of patch 1 is >= 0.9; the job's reported usage is <= 30 s (D6).  The canary's counts are raw data in their
own directory; they are never merged into the H0 analysis.

**D6 — Budget caps (planner rules, not physics).**  Monthly allowance 600 s.  The main session is submitted only if
the recomputed execution estimate (step B2) is <= 120 s (20 % of the month; the 2026-09-21 value is 46.7 s), and the
session is judged over budget if the sum of `job.usage()` over the canary and the 4 main jobs exceeds 180 s (30 %).
If the canary's usage shows a per-job overhead that would push 4 jobs past 180 s, stop at B6 and report.  No
resubmission of any kind without the planner: the remaining minutes of the month are allocated by the planner after
H0, not by the session.

**D7 — The readout-drift item of gate_H0.py references the day's calibration.**  `gate_H0.py` compares the measured
per-qubit readout error with `readout_error_snapshot` of the manifest — the FakeFez snapshot of 2025-02-26, 19
months old.  The item was added in prompts/13 as "the calibration-drift item, expected to move on a real device": its
purpose is drift between the prediction and the run.  On the day the prediction is made from the live calibration
(D1), so the reference for the factor-3 criterion is the live calibration recorded at prediction time
(`--calibration data/hardware/H0_ibm_fez/calibration_<stamp>.json`); the comparison with the 2025 snapshot is still
reported, as information, whenever the manifest's backend differs from the session backend.  The factor 3 is
unchanged; the four prereg criteria are unchanged; this only assigns the item the reference the prereg requires.

**D8 — Sampler options are those of the dry run, frozen.**  `SamplerV2` in job mode (no Session, no Batch: the
open plan has no session access and the jobs are independent), dynamical decoupling XY4, gate and measurement
twirling with strategy `active-accum`, no error mitigation of any kind (raw bit strings), `execution.init_qubits`
default, `execution.rep_delay` default (250 us on ibm_fez), `environment.job_tags = ["su2qc-skqd", "H0", "<commit>",
"<out dir name>"]`.  All of it is recorded in session.json and in every counts file.

## Frozen before submission — never touched after
1. `data/hardware/H0_prep/` (QPY, manifests, index.json) at commit 2392fb3 — the manifests are not rewritten by any
   step of this prompt (the day's f goes into validation/H0P_ibm_fez.json, not into the manifests).
2. The day's prediction: `validation/H0P_ibm_fez.json`, `reports/H0_prereg_ibm_fez.md`, the calibration record
   `data/hardware/H0_ibm_fez/calibration_<stamp>.json`, committed before the canary; the commit hash and the
   calibration's `last_update_date` are written into session.json by `--submit`, which refuses to submit if the live
   `last_update_date` differs (re-run step B3, commit, submit; no owner re-go is needed unless the stop rule of B3
   fires).
3. The shot plan (D3), the calibration shots (D2), the sampler options (D8), the canary composition (D5).
4. The criteria constants: F_TOLERANCE 0.30, RANDOM_ACCEPT_MAX 0.01, E0_TOL 1e-6, DIAG_MIN 0.9, RO_FACTOR 3 in
   gate_H0P.py / gate_H0.py; `READOUT_FACTOR` 0.82 and the yield model in src/skqd/skqd.py; the decoder in
   src/skqd/codec.py.  Part A ends with a commit; gate_H0.py's criteria code is not edited after that commit.  If a
   bug in gate_H0.py is found after the counts exist, the fix is a new prompt from the planner, the raw counts are
   re-analysed, and both analyses are kept in git.
5. Raw counts (`data/hardware/H0_ibm_fez*/counts/*.json`) are written once; `h0_submit.py` refuses to overwrite
   (existing rule) and `--retrieve` skips files that exist.  They are committed as they are.

## Steps

### Part A — engineering on the laptop (no QPU, no account needed except A1's read-only target access)

A1. **Live-backend resolution.**  Add `resolve_backend(name)` (e.g. in `scripts/h0_backends.py`, imported by the
    three scripts): `"FakeFez"` / `"FakeTorino"` return the fake class instance exactly as today; any other name
    returns `ibm_account.open_service().backend(name)`.  `h0_build_circuits.py --backend <name>` becomes free-form
    (default FakeFez, unchanged); for a live backend `--out` must be given and must not be `data/hardware/H0_prep`
    (refuse); the manifest's `backend` field records the live name and `backend_calibration_last_update` records
    `backend.properties().last_update_date` (ISO, UTC).  `gate_H0P.py --backend <name>` (default None = the
    snapshot named in index.json, unchanged path): for a live backend it builds `AerSimulator.from_backend(live,
    seed_simulator=args.seed)`, recomputes per circuit `analyse_on_backend(load_circuit(prep, m), live)` and uses that
    f (`f_calibration_mean` = live) in the yield table and criteria, keeps the manifest value as an extra column
    "f (FakeFez snapshot)", and writes `data/hardware/H0_ibm_fez/calibration_<stamp>.json` with: backend name,
    `last_update_date`, `<stamp>` = that date as `YYYYMMDDTHHMMZ`, dt, default rep_delay, `max_circuits`, status
    (operational, pending_jobs), and for the 30 frozen qubits / 54 frozen edges the target's measure error and
    duration, sx and x error, T1, T2, cz error and duration.  Verify the claim about `analyse_on_backend`: assert
    that none of the 54 cz `.error`, 30 measure `.error` values is None on the live target (record the check in the
    calibration JSON; a None is a hard stop of B3, not a value to default).  The prereg file name: `H0_prereg_draft.md`
    for a fake backend (unchanged), `H0_prereg_<backend>.md` for a live one; add `--no-prereg`.  Expected runtime of
    the code change: 2 h; of the FakeFez re-checks below: 2 + 20 min.
    - Reproducibility of the fake path, builder: `python scripts/h0_build_circuits.py --backend FakeFez --out
      /tmp/H0_prep_repro` (about 2 min), then the new `python scripts/h0_compare_prep.py data/hardware/H0_prep
      /tmp/H0_prep_repro`: for all 126 ids `qpy.load` both files and require `QuantumCircuit.__eq__`, equal
      `count_ops()`, equal `layout.final_index_layout()`, and equal manifest fields cz, depth, physical_qubits,
      logical_to_physical, measurement_map_clbit_to_physical, f_calibration_snapshot (to 1e-12).  (The gzip
      container carries a timestamp, so the .qpy.gz sha256 is NOT the comparison.)
    - Reproducibility of the fake path, H0P: `python scripts/gate_H0P.py --shots-by-rep 1:267 2:130 3:92
      --budget-minutes 14 --pilot-shots 60 --cal-shots 4000 --seed 11 --out H0P_repro --no-prereg --no-tests`
      (about 20 min) and compare with validation/H0P.json:
      `python -c "import json;a=json.load(open('validation/H0P.json'))['data'];b=json.load(open('validation/H0P_repro.json'))['data'];A=a['analysis'];B=b['analysis'];assert all(A['by_sector_repetition'][k][f]==B['by_sector_repetition'][k][f] for k in A['by_sector_repetition'] for f in ('yield','f_calibration_mean','model_yield_full','garbage_acceptance'));assert all(A['by_sector'][s]['ER']==B['by_sector'][s]['ER'] for s in A['by_sector']);assert A['confusion_summary']['min_diagonal']==B['confusion_summary']['min_diagonal'];print('H0P_repro identical')"`

A2. **gate_H0.py.**  (i) `--calibration <json>`: when given, the readout-error criterion (factor RO_FACTOR = 3)
    uses the live per-qubit measure error of that file as the reference; the manifest-snapshot comparison stays in
    the table and the JSON as `readout_vs_snapshot_informational` (no criterion) whenever the manifest backend differs
    from the counts' backend, and stays a criterion (unchanged) when they are the same (dry run).  (ii) Guard the
    worst-ratio computation: a measured error of exactly 0 must not raise (`1.0 / min(good)`); report the ratio as
    None and treat the entry as "fewer than one error event" in the JSON.  (iii) Record `support_size_decoded` vs
    `sector_dimension` per sector in the criteria line of the E0 check, so a non-saturated support is distinguishable
    from a bit-order error in the report.  Regression: `python scripts/gate_H0.py --counts data/hardware/H0_dryrun/counts
    --out H0_dryrun` must PASS 9/9 with every `criteria[*].value` identical to the committed validation/H0_dryrun.json
    (`git diff validation/H0_dryrun.json` may differ only in the environment block).

A3. **Submit / retrieve split in h0_submit.py.**  Phases: `--submit` (implied by `--backend`), `--retrieve`,
    `--status`.  `session.json` is the state: `jobs` becomes a list with ONE entry PER JOB {group shots, chunk index, circuit
    ids, job_id, submitted (UTC), status, usage_s, metrics (timestamps, queue wait), retrieved (UTC),
    counts_written} (the per-circuit list of the old format moves to a `circuits` key; the committed dry-run
    session.json keeps its old format as history).  `--submit`: preflight (live
    only) — backend name equals `--backend`; `status().operational`; `check_backend(backend,
    frozen_requirements(prep))` returns no problems; `max_circuits` is None or >= the largest chunk; the live
    `properties().last_update_date` equals `validation/H0P_ibm_fez.json`'s (else refuse with the message "re-run
    gate_H0P.py --backend ibm_fez"); the execution estimate of `h0_qpu_time.py` (A4) <= `--max-qpu-seconds` (default
    120); no target counts file exists — then for each group: `job = sampler.run(pubs, shots=sh)`, append
    {job_id, ...} to session.json and write it atomically (tmp + rename) BEFORE the next `sampler.run`; if a
    submission raises (e.g. a pending-job limit of the plan), record the exception and exit non-zero; `--submit
    --resume` submits only the groups without a job_id.  `--retrieve [--wait S]`: for each job_id
    `service.job(job_id)`, poll `status()` every 30 s for up to S seconds (S <= 1500 so one invocation respects the
    30-minute rule), and for each DONE job write the counts files exactly as today (manifest + raw counts + key
    convention + job_id + sampler options + `usage_s` + `job.metrics()`), skipping existing files with a warning;
    record `job.usage()` (call it again on later `--status` invocations: it is 0 until IBM's accounting completes) and
    `total_usage_s` in session.json.  `--only <id> [<id> ...]` restricts the circuit list (canary).  `--dry-run`
    keeps running both phases in one process through the same `write_counts_for_job` function on the local job
    objects; `--retrieve` on a dry-run session exits non-zero with "local jobs cannot be retrieved by id".  Tests
    (all on the laptop, ~5 min): `python scripts/h0_submit.py --dry-run --shots-by-rep 1:4 2:4 3:4 --cal-shots 4
    --out /tmp/h0_split_test` (126 counts files, 4 job ids in session.json, every job `counts_written: true`); the
    same command again must exit non-zero BEFORE any sampling ("counts files are raw data"); `python
    scripts/h0_submit.py --retrieve --out /tmp/h0_split_test` exits non-zero with the local-mode message; `python
    scripts/h0_submit.py --dry-run --only B0_ref06_k1_rep1 cal_patch1_all0 cal_patch1_all1 --shots 267 --cal-shots
    267 --out /tmp/h0_canary_test` (1 job, 3 pubs) followed by `python scripts/gate_H0.py --counts
    /tmp/h0_canary_test/counts --out H0_canary_test`, which must run to completion without a traceback (its status
    is expected FAIL: one circuit cannot saturate the sector); delete validation/H0_canary_test.json and its report
    afterwards (test artefacts, not gate outputs).

A4. **`scripts/h0_qpu_time.py`** — the execution-time estimate from the repository: for every frozen circuit, an
    ASAP schedule on the target's instruction durations (`target.durations()` +
    `qiskit.transpiler.passes.ASAPScheduleAnalysis`, or an equivalent critical-path sum) gives the circuit duration;
    per group: circuits x shots x (duration + rep_delay); JSON with the per-group table, `total_shots`,
    `total_execution_s`, dt, rep_delay used, the basis durations (sx, x, cz min/max, measure), the target's
    `last_update_date` when live.  `--backend FakeFez` as the offline test (prints the table); on the live target in
    B2 it must reproduce the 2026-09-21 values (46.7 s total; 46.0 / 89.2 / 133.9 us per r = 1 / 2 / 3 circuit)
    within 10 % unless the durations were recalibrated, in which case the new durations are the record.

A5. `pytest -q tests` (32 tests + any new ones for `resolve_backend` name routing and the gate_H0 zero-error guard);
    `python scripts/update_status.py` after adding the rows `H0P_ibm_fez` ("H0P re-predicted on the live ibm_fez
    calibration of the session day", laptop) and keeping `H0` (QPU) — the canary is NOT a gate row.  Commit
    "prompts/15 part A: live-backend paths, submit/retrieve split, QPU-time estimate, gate_H0 calibration reference",
    push.  Append the part-A outcome to prompts/LOG.md.

### Part B — the session day (laptop + ibm_fez).  Every command < 30 min; queue waits are not compute time.

B1. **Preflight.**  `mkdir -p data/hardware/H0_ibm_fez && python scripts/ibm_account.py --check 2>&1 | tee
    data/hardware/H0_ibm_fez/preflight_check.txt` (about 1 min).  Required in the output: `ibm_fez: 156 qubits ...
    operational` and `OK: the frozen set runs on ibm_fez as frozen`.  If ibm_fez is not operational or the set does
    not fit as frozen: stop, report (the owner may choose another day; a different device is a planner decision —
    the prediction and the canary are device-specific).

B2. **Execution-time estimate.**  `python scripts/h0_qpu_time.py --backend ibm_fez --shots-by-rep 1:267 2:130 3:92
    --cal-shots 4000 --out data/hardware/H0_ibm_fez/qpu_time_estimate.json` (about 2 min).  Required:
    `total_execution_s <= 120`.

B3. **The day's prediction (the preregistration).**  `python scripts/gate_H0P.py --backend ibm_fez --shots-by-rep
    1:267 2:130 3:92 --budget-minutes 14 --pilot-shots 60 --cal-shots 4000 --seed 11 --out H0P_ibm_fez` (about 20
    min; if it exceeds 25 min use `--budget-minutes 10` and say so in the LOG).  Outputs: validation/H0P_ibm_fez.json
    (status must be PASS on the same 16 criteria as H0P), reports/H0P_ibm_fez_heron_preparation.md,
    reports/H0_prereg_ibm_fez.md, data/hardware/H0_ibm_fez/calibration_<stamp>.json.  Stop rule (prompts/13): if
    `data.analysis.by_sector_repetition["B=0 r=1"].yield` or `["B=1 r=1"].yield` is below 0.05, run the contingency
    B3b; otherwise commit: "H0 session day: prediction on the live ibm_fez calibration <stamp>".
    B3b (contingency, only if the stop rule fired): `python scripts/h0_build_circuits.py --backend ibm_fez --out
    data/hardware/H0_prep_ibm_fez` (about 3 min), `python scripts/ibm_account.py --check --prep
    data/hardware/H0_prep_ibm_fez`, then B3 again with `--prep data/hardware/H0_prep_ibm_fez` (the new set is then
    the frozen set for every later step, and every `--prep` below changes accordingly).  If the r = 1 simulated
    yield is still below 0.05 in either sector: STOP, no submission, write validation/BLOCKED.md with both
    predictions and hand over to the planner.

B4. **STOP A — hand back to the owner.  Do not run B5 in the same turn.**  The hand-back message contains: the path
    of reports/H0_prereg_ibm_fez.md and its commit hash; the r = 1 predicted yields and f for both sectors and the
    live f of the frozen patch next to the FakeFez values (0.1261 / 0.1214); the calibration `last_update_date`;
    `total_execution_s` of B2; the canary command of B5 verbatim.  The owner's reply "go canary" (or equivalent)
    authorises B5 only.

B5. **Canary** (D5): `python scripts/h0_submit.py --backend ibm_fez --only B0_ref06_k1_rep1 cal_patch1_all0
    cal_patch1_all1 --shots 267 --cal-shots 267 --out data/hardware/H0_ibm_fez_canary` (seconds; 1 job, 3 pubs);
    commit session.json at once ("H0 canary submitted: job <id>").  Then (runner-sonnet) `python
    scripts/h0_submit.py --retrieve --wait 1500 --out data/hardware/H0_ibm_fez_canary`, re-invoked until the job is
    DONE (each invocation < 30 min; report the queue wait).  Analysis: `python scripts/gate_H0.py --counts
    data/hardware/H0_ibm_fez_canary/counts --out H0_canary --predict-from validation/H0P_ibm_fez.json --calibration
    data/hardware/H0_ibm_fez/calibration_<stamp>.json` (its status is expected FAIL on the E0 item — one circuit
    cannot saturate the 38-state sector — and possibly on the statistics of 267 shots; that is not the go rule).  Go
    rules, checked with:
    `python -c "import json;s=json.load(open('data/hardware/H0_ibm_fez_canary/session.json'));j=s['jobs'][0];c=json.load(open('validation/H0_canary.json'))['data'];pc=[p for p in c['analysis']['per_circuit'] if p['id']=='B0_ref06_k1_rep1'][0];ok=(j['status']=='DONE' and j['usage_s'] is not None and j['usage_s']<=30 and c['codeword_roundtrip']['mismatches']==0 and pc['accepted']>=10 and c['analysis']['confusion_summary']['min_diagonal']>=0.9);print('canary GO' if ok else 'canary NO-GO', j['usage_s'], pc['accepted'], c['analysis']['confusion_summary']['min_diagonal'])"`
    Commit the canary directory, validation/H0_canary.json and reports/H0_canary_hardware_2x2.md.

B6. **STOP B — hand back to the owner.  Do not run B7 in the same turn.**  Report: the canary line above, the queue
    wait, `usage_s`, the accepted count and yield of the canary circuit next to the prediction (39.9 of 267), and the
    main command of B7 verbatim.  If the canary is NO-GO, this is a hand-over to the planner instead (Escalation).
    The owner's "go main" authorises B7 only.

B7. **Main submission and retrieval.**  `python scripts/h0_submit.py --backend ibm_fez --shots-by-rep 1:267 2:130
    3:92 --cal-shots 4000 --out data/hardware/H0_ibm_fez` (seconds; 4 jobs, 126 pubs; the preflight of A3 runs again —
    if the calibration `last_update_date` moved since B3, re-run B3, commit, then submit; the owner's go stands unless
    the B3 stop rule fires).  Commit session.json at once ("H0 submitted to ibm_fez: 4 job ids").  Then
    (runner-sonnet) `python scripts/h0_submit.py --retrieve --wait 1500 --out data/hardware/H0_ibm_fez` until all 4
    jobs are DONE and 126 counts files exist; `python scripts/h0_submit.py --status --out data/hardware/H0_ibm_fez`
    once more later for the final `usage_s`.  Commit the counts: "H0 raw counts from ibm_fez (never modified)".
    Record at retrieval time a second calibration file `calibration_at_retrieval_<stamp2>.json` (same content as
    B3's) so that drift during the queue is on record.

B8. **Gate H0.**  `python scripts/run_gate.py H0 --push --timeout 1800 --counts data/hardware/H0_ibm_fez/counts --out
    H0 --predict-from validation/H0P_ibm_fez.json --calibration data/hardware/H0_ibm_fez/calibration_<stamp>.json`
    (seconds).  Outputs validation/H0.json and reports/H0_hardware_2x2.md; on PASS the runner commits and pushes; on
    FAIL it writes validation/BLOCKED.md (Escalation).

B9. **Bookkeeping** (scribe-haiku): `python scripts/update_status.py`; prompts/LOG.md entry with the job ids, the
    queue waits, the per-job and total usage, the two owner authorisations quoted with their timestamps, and the H0
    criteria table; the CLAUDE.md status paragraph; commit and push.  Then planner-fable (max) writes prompt 16
    (the post-H0 decision on the 2x3 plan) whether H0 passed or failed.

## Pass criteria

Part A (all must hold before B1):
- `scripts/h0_compare_prep.py data/hardware/H0_prep /tmp/H0_prep_repro` exits 0 and prints 126/126 identical.
- validation/H0P_repro.json: status PASS and the one-liner of A1 prints "H0P_repro identical" (the six simulated
  yields, f, full-model yields, garbage acceptances, both E_R and the confusion minimum equal to those of
  validation/H0P.json — the FakeFez path is unchanged).
- validation/H0_dryrun.json regenerated by the new gate_H0.py: status PASS, 9 criteria, `criteria[*].value` identical
  to the committed file.
- /tmp/h0_split_test/session.json: 4 jobs, each with a non-null `job_id` and `counts_written: true`; 126 counts
  files; the repeated command exits non-zero before sampling; `--retrieve` on it exits non-zero with the local-mode
  message; the canary dry run writes 3 counts files in 1 job and gate_H0.py completes on them without a traceback.
- `pytest -q tests`: all pass.
Part B:
- B1: preflight_check.txt contains "OK: the frozen set runs on ibm_fez as frozen" and "operational".
- B2: qpu_time_estimate.json `total_execution_s` <= 120 (record the value).
- B3: validation/H0P_ibm_fez.json status PASS (16 criteria as H0P, evaluated on the live calibration);
  `data.calibration.last_update_date` present; all 54 cz and 30 measure errors non-None (`data.calibration.
  missing_errors == []`); `by_sector_repetition["B=0 r=1"].yield >= 0.05` and `["B=1 r=1"].yield >= 0.05`.
- B5: the canary one-liner prints "canary GO".
- B7: data/hardware/H0_ibm_fez/session.json: 4 jobs with status DONE, `counts_written: true`, 126 counts files;
  `total_usage_s` (canary + 4 jobs) <= 180.
- B8, gate H0 (validation/H0.json, status PASS), the criteria of prompts/07 and the prereg, unchanged:
  1. decoder validity: `data.codeword_roundtrip.mismatches == 0`; random-string acceptance < 1 % per sector
     (`data.analysis.random_acceptance[sec].fraction`; exhaustive, device-independent: 0.928 % / 0.488 %);
  2. `data.f_comparison["B=0 r=1"].relative_deviation <= 0.30` and `["B=1 r=1"]` likewise, where the prediction is
     the simulated yield of validation/H0P_ibm_fez.json and both f come from `clean_fraction_from_yield(y, a)`;
  3. `data.analysis.by_sector["B=0"].abs_error < 1e-6` and `["B=1"]` likewise (E0 = -3.6408 / -1.8616);
  4. `data.analysis.confusion_summary.min_diagonal >= 0.9`;
  5. readout error per qubit against the day's calibration: worst ratio <= 3 (D7).
- The r = 2 and r = 3 rows of the yield table exist with their measured yields, rejection reasons and distinct
  states (informational: the shape of the yield-versus-CZ curve of manual Step 9.1).

## Outputs
scripts/{h0_backends,h0_compare_prep,h0_qpu_time}.py (new), scripts/{h0_build_circuits,gate_H0P,h0_submit,gate_H0,
update_status}.py (extended), tests; validation/{H0P_repro,H0P_ibm_fez,H0_canary,H0}.json; reports/{H0P_repro_heron_
preparation,H0P_ibm_fez_heron_preparation,H0_prereg_ibm_fez,H0_canary_hardware_2x2,H0_hardware_2x2}.md;
data/hardware/H0_ibm_fez/{preflight_check.txt,qpu_time_estimate.json,calibration_<stamp>.json,
calibration_at_retrieval_<stamp2>.json,session.json,counts/*.json (126)}; data/hardware/H0_ibm_fez_canary/{session.json,
counts/*.json (3)}; prompts/LOG.md entries for part A and part B; reports/PROJECT_STATUS.md, validation/gates.md,
CLAUDE.md status.  Push: yes after part A, after every commit of part B, and by `run_gate.py H0 --push` on PASS.
data/hardware/H0_prep is untouched (verify with `git status data/hardware/H0_prep` = clean before B5).

## Escalation
- Part A: if the FakeFez path is not reproduced (A1 comparisons), do not start part B; look for the nondeterminism
  (transpiler seed, Aer threading, an accidental manifest rewrite) for at most two attempts, then stop and write
  validation/BLOCKED.md for the planner.
- B1-B3: a non-operational device or a frozen set that no longer fits is a wait, not a fix; a None error field on the
  live target is a stop (no defaulting); the r = 1 stop rule after B3b is a planner call.  Nothing is submitted.
- B5 canary NO-GO: no main submission.  A job rejected or failed by the runtime (no QPU time is spent on a failed
  job) is reported with the runtime's message; the options are frozen (D8), so the fix — if any — is the planner's.
  Fewer than 10 accepted of 267 with a clean round trip means the device delivers far less than predicted at 663 CZ:
  that is already the prompts/07 clause (below) at canary scale; the planner decides before the main budget is spent.
- B7: a failed job is recorded, not resubmitted; `--submit --resume` only after the planner's OK, and only if the
  calibration `last_update_date` is unchanged (otherwise the session would mix calibrations).
- B8, H0 FAIL — no resubmission in any case (the analysis needs no QPU time):
  (a) round-trip or E0 criterion fails with a saturated support: bit order or convention on the real job — stop, do
      not touch codec.py / reference_sim.py, hand the counts and the failing strings to the planner;
      E0 fails with `support_size_decoded < sector_dimension`: the support did not saturate — report the sizes; the
      planner decides whether a denser r = 1 run is funded from the remaining budget;
  (b) r = 1 f criterion fails with measured f < 0.7 x predicted f in either sector: the prompts/07 clause — the 2x3
      budget is not spent, `slurm/s3_2x3.sbatch` is not launched with Heron-derived parameters, and the planner
      re-plans with k = 1, 2 coarse steps only (Plan B of manual Sec. 11);
  (c) fails with measured f > 1.3 x predicted f: the device beats the day's device-model simulation — still a FAIL of
      the preregistered criterion; the planner decides how the prediction model is revised (never post hoc in this
      gate);
  (d) the drift item fails: compare `calibration_<stamp>.json` with `calibration_at_retrieval_<stamp2>.json`; a
      re-prediction on the retrieval calibration may be run and reported as a post-hoc analysis, clearly labelled,
      but validation/H0.json keeps the preregistered prediction.
- 30-minute rule: B3 is the only long step (about 20 min); `--wait` is capped at 1500 s per invocation; if any
  laptop command exceeds 30 min, stop it, re-parametrize as named above and record it in the LOG.
