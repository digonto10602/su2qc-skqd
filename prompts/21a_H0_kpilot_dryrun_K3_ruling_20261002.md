# 21a — Ruling on the Part-D STOP of prompts/21: the dry-run K3 on the FakeKingston snapshot
executor: executor-opus   effort: high
time budget: 1 h of laptop work; **0 QPU s in this file** (Part E of prompts/21 follows only after this addendum's criteria pass)   machine: laptop CPU

> Planner-fable, 2026-10-02.  Addendum to `prompts/21_kingston_T2star_pilot.md`; it changes nothing in the
> preregistration (`data/hardware/H0_kpilot_prep/prereg_ec74eb8bf15dde41.json`, commit 148e873), nothing on the
> device side of any criterion, and no counts file.  Facts verified by the planner in the files:
> `validation/H0_kpilot_dryrun.json` FAIL on K3 only (smallest diagonal 0.85125 = logical 8 = qubit 92, measured
> error 0.14625 at 4000 shots; K4–K8 PASS, K5 12/12, r_eff 0.9775 [0.9573, 0.9939], f_pool 0.2073);
> `data/hardware/H0_kpilot_prep/calibration_20261002T1627Z.json` carries measure_error 0.0243 on qubit 92 and the
> patch's worst 0.0448 (qubit 72), i.e. a live expected minimum diagonal ≈ 0.955 ≥ 0.9; the prereg's fingerprint
> `ec74eb8b…` matched at predict time and at the 17:51Z calwatch; `validation/S2D_levers.json` PASS 9/9 with C6
> "30 cells checked, worst 0.099" — part 0 is done as ruled.

## Ruling
**Option (a).**  The dry run's job is a path check against the *simulator's own* model; K3 as written (≥ 0.9)
measures the FakeKingston snapshot's readout, which is a property of the snapshot, not of the day's device, and is
exactly the kind of number the dry run cannot be asked to pass.  The device-side K3 stays **≥ 0.9 (`DIAG_MIN`),
unchanged**.  Nothing is re-sampled; the preregistration stays valid; the pilot proceeds to Part E on the same
content.

## What the executor changes (`scripts/gate_H0_kpilot.py`, assemble stage only)
1. In dry-run mode K3 becomes: for every patch qubit q, the measured diagonals d00_q, d11_q of the confusion matrix
   agree with the readout error the Aer noise model actually carries — read it from
   `NoiseModel.from_backend(resolve_backend(index.common.backend))` (`_local_readout_errors[(q,)]`'s probability
   matrix: expected d00 = P[0][0], d11 = P[1][1]; if the snapshot has no asymmetric entries the matrix is symmetric
   in ε and the same code applies) — within 3 binomial σ, σ = sqrt(p(1 − p)/4000), on both diagonals, for all 12
   qubits.  Record per qubit: expected, measured, σ, z.  The criterion string says "(dry run: agreement with the
   snapshot's readout model; the device criterion ≥ 0.9 is evaluated only on device counts)".  Expected on the
   recorded dry-run counts: qubit 92 measured 0.85125 / 0.85625 against the snapshot's ≈ 0.851 (σ ≈ 0.0056) passes;
   any qubit outside 3σ on the dry run is a genuine path problem → STOP and hand back.
2. Device mode K3 unchanged (min diagonal ≥ 0.9 from the live all-0 / all-1 pubs).  Additionally the
   **preflight expectation** is made explicit: `--stage predict` (and the assemble stage) write
   `data.readout_expected_live = {per-qubit 1 − measure_error of the prereg's patch record, min}` and the predict
   stage **refuses** (STOP, nothing submitted) if that minimum is < `DIAG_MIN` — so the device K3 is a preregistered
   expectation (today 0.9552 from qubit 72's 0.0448), not a surprise.  This is a read of the already-committed record;
   the prereg JSON is not edited.
3. The dry-run min diagonal (0.85125) stays in `validation/H0_kpilot_dryrun.json` as information next to the live
   expectation, with one sentence in `reports/H0_kpilot_dryrun.md` naming qubit 92's snapshot error 0.1492 vs the live
   0.0243 as the cause of the first FAIL.
4. `tests/test_h0_kpilot.py`: (i) a synthetic dry-run confusion table inside 3σ of a synthetic readout matrix passes
   the dry-run K3 and a table 5σ off fails it; (ii) the device-mode K3 on a synthetic min diagonal 0.89 fails and 0.91
   passes (the constant is `DIAG_MIN`, not a new number).

## Dry run: re-assemble only, no re-sampling
`python scripts/gate_H0_kpilot.py --stage assemble --counts data/hardware/H0_kpilot_dryrun/counts --dry-run --out
H0_kpilot_dryrun` on the **existing** dry-run counts (seed 11; a re-sample would reproduce them bit for bit and
add nothing).  Expected: PASS with K3 in its dry-run form, every other criterion value identical to the committed
file (K4 0 mismatches / 53 strings, K5 12/12 and r_eff 0.9775, K7 dev 0.026, K8 GO recomputed GO).  If any
non-K3 value changes, the assemble stage read something it should not have → STOP.

## The preregistration stays valid
The prereg content (patch, circuits, windows, thresholds, Aer grid, estimate 9.04 s) does not depend on the dry
run, and the live fingerprint still equals `ec74eb8b…`.  D10 is **not** triggered by this ruling; it is triggered only
if `h0_calwatch.py --once` at Part E1 reports a move, in which case prompts/21 E1 applies as written (re-run A2–C4
on the new content, commit, retry once).  The one change to the analysis code (dry-run K3 form) is committed
**before** Part E2 and named in the report's preregistration block ("dry-run K3 form changed at commit <hash>,
device K3 unchanged; no prereg number edited"); K1 keeps checking the prereg commit 148e873 against the submission
time.  The day's Aer r_crit 0.2788 against the preregistered 0.3285 is read exactly as prompts/21 says: the
r-verdict uses 0.3285, the day's value is reported beside it (15 % apart on a 4000-shot grid), and no threshold moves.

## Pass criteria for this addendum (before Part E)
- `validation/H0_kpilot_dryrun.json` PASS; its K3 value lists 12 qubits with |z| ≤ 3 on both diagonals; its
  `data.readout_expected_live.min` ≥ 0.9; `data.readout.min_diagonal` (0.85125) kept as information.
- Every non-K3 criterion value byte-identical to commit 9e57fb6's file.
- `pytest -q tests` passes with the two new tests; `python scripts/check_package.py` OK.
- Commit "H0_kpilot: dry-run K3 reads the snapshot's own readout model (device K3 >= 0.9 unchanged); dry run PASS;
  live readout expectation 0.9552 recorded" — **no push**; then prompts/21 Part E as written (E1 calwatch, E2 one
  job, E3 retrieve, E4 account), Part F.

## Not done / not allowed
No loosening of the device-side K3; no edit of the prereg JSON, the counts, `h0_submit.py` or `DIAG_MIN`; no
second dry run with different seeds; no submission until the criteria above are met; no push.
