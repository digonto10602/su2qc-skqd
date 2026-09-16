# 13 — H0 preparation on Heron (gate H0P) and the S3 desktop job
executor: executor-opus   effort: high   planner: planner-fable (max)
time budget: 1 day; each run < 30 min   machine: laptop (CPU); the S3 production run is specified for the RTX 3070 / Slurm
prerequisites met: S2 exact circuits (validation/S2.json), S2D 2x2/Heron f = 0.125 (validation/S2D.json), L4_fez PASS
(validation/L4_fez.json), owner decision of 2026-09-16 (combined plan, prompts/12)

## Goal
Make the first QPU session (prompt 07, manual Step 9.1) executable without further engineering on the day, and make
the 2x3 device-model simulation (gate S3) a one-command job for the desktop GPU or the cluster.  Everything here runs
against the FakeFez calibration snapshot as a stand-in for the real Heron r2 backend; the real run replaces one
argument.  Nothing in this prompt touches a QPU.

## Inputs
- prompts/07 (H0 steps and criteria), reports/S2D_device_budgets.md, validation/S2D.json (patch, CZ counts, f),
  validation/L4_fez.json (simulated yields 0.144 / 0.138 vs model 0.103 / 0.100), scripts/laptop_L4_aer_noise.py
  (--backend path), src/skqd/codec.py (Codec.decode_counts, rejection reasons), src/skqd/skqd.py (ritz, certify,
  shot_rule), qiskit_ibm_runtime (SamplerV2, fake_provider.FakeFez, AerSimulator.from_backend)
- manual Step 9.1: yield versus CZ count "by repetition" -> use r = 1, 2, 3 repetitions of the same coarse step
  (U^r, each a valid gauge-invariant generator), giving about 663 / 1326 / 1989 CZ on the Fez patch

## Steps
1. **Freeze the H0 circuit set** (`scripts/h0_build_circuits.py`): for B = 0 and B = 1, every reference, k = 1..4,
   repetitions r = 1, 2, 3; transpile onto FakeFez (level 3, seed 7); save to `data/hardware/H0_prep/circuits/` as
   QPY plus a manifest JSON per circuit (sector, reference, k, r, CZ count, depth, physical qubits, logical->physical
   map, the codeword bit order, and the list of flux-bit link-consistency checks that the decoder applies).  Verify
   the noiseless statevector of every transpiled circuit is leak-free (< 1e-9, CodewordEmbedding) — this checks the
   layout permutation, which is exactly what a real run gets wrong.  Also build the readout-calibration circuits
   (all-0, all-1, single-qubit flips on the 12 patch qubits).
2. **Predicted yield curve** (`scripts/gate_H0P.py` -> validation/H0P.json, reports/H0P_heron_preparation.md):
   with `AerSimulator.from_backend(FakeFez())` sample the r = 1, 2, 3 circuits inside a 25-minute budget (pilot and
   shot scaling as in laptop_L4_aer_noise.py; one process per sector if needed), decode, and tabulate per r: CZ,
   f from the calibration product (as S2D computes it), the manual's model yield 0.82 f, the simulated yield, and
   the ratio.  Record rejection reasons.  Compute the readout confusion matrix from the simulated calibration
   circuits (new `src/skqd/hardware.py`: `confusion_matrix(counts_by_prep)`, `apply_inverse(counts, C)` with a
   unit test) and its diagonal per qubit.  Ritz consistency: decoded B = 0 and B = 1 supports must reproduce
   E0 = -3.6408 and -1.8616 to 1e-6 (the sectors saturate).
3. **Submission path** (`scripts/h0_submit.py`): builds the SamplerV2 job(s) from the frozen circuits with dynamical
   decoupling and Pauli twirling enabled and no error mitigation of expectation values; `--dry-run` executes them on
   `AerSimulator.from_backend(FakeFez())` instead of a QPU and writes counts to `data/hardware/H0_dryrun/counts/`
   in the exact format the real run will use (one JSON per circuit with the manifest fields and the raw counts);
   `--backend <name>` with a real IBM backend is the production path (do not call it; no IBM account is assumed).
   Then write `scripts/gate_H0.py` (prompt 07 step 5): reads a counts directory, decodes, computes yields,
   confusion matrix, Ritz energies and the prompt-07 criteria, writes validation/H0<suffix>.json; run it on the
   dry-run counts with `--out H0_dryrun`.
4. **S3 desktop job** (`scripts/s3_device_model.py`, `slurm/s3_2x3.sbatch`): one command that samples the exact
   circuits of a lattice and sector with a device noise model — `--backend FakeFez` for 2x2, or the declared
   ion-trap model (`--eps2 --eps1 --eps-ro`, RZZ basis, all-to-all) for 2x3 — with Aer `device='GPU',
   batched_shots_gpu=True` when available and CPU otherwise, shots per sector from `--shots-per-sector`
   (default 2e5), decodes, and writes validation/S3_<tag>.json with the S3 criterion (recall of the 99.9 % support
   >= 0.9) plus yield, |B|, Ritz error and certification.  Laptop smoke test: `--lattice 3 --sector 1
   --shots-per-sector 24 --tag smoke` (12 circuits x 2 shots, about 2 minutes) proving the pipeline end to end;
   record the CPU seconds per shot and print the projected job size for 2e5 shots per sector.  The sbatch file
   requests one GPU and calls the same script for the four 2x3 sectors of Step 9.2 (B = 0, B = 1, r = 1, r = 2).
5. **H0 preregistration draft** (`reports/H0_prereg_draft.md`, generated by gate_H0P.py from H0P.json): the frozen
   circuit list summary, the predicted yields per r (both the model 0.82 f and the simulated yield, stating which
   one the 30 % criterion will be judged against — the planner's decision: the simulated yield with the day's
   calibration, since L4_fez shows the model is 1.39x conservative), the shot plan from shot_rule with the per-sector
   reading, and the pass criteria of prompt 07.
6. `pytest -q tests`; `python scripts/update_status.py`; commit per step; `python scripts/run_gate.py H0P --push` on PASS.

## Pass criteria (gate H0P)
- every frozen circuit (both sectors, all k, r = 1, 2, 3) is leak-free after transpilation onto FakeFez (< 1e-9)
- simulated decoded supports reproduce E0 to 1e-6 in both sectors; acceptance among flagged strings < 1 %
- predicted yield table exists for r = 1, 2, 3 with simulated yields within a factor 3 of 0.82 f (L4 criterion)
- confusion matrix computed; every diagonal element >= 0.9
- dry-run counts exist and gate_H0.py produced validation/H0_dryrun.json from them (its own criteria may FAIL
  on the dry run only for the readout-confusion-vs-real-device items; report them)
- S3 smoke test wrote validation/S3_smoke.json; tests pass

## Outputs
data/hardware/H0_prep/ (circuits + manifests + calibration circuits), data/hardware/H0_dryrun/counts/,
validation/H0P.json, validation/H0_dryrun.json, validation/S3_smoke.json, reports/H0P_heron_preparation.md,
reports/H0_prereg_draft.md, scripts/{h0_build_circuits,gate_H0P,h0_submit,gate_H0,s3_device_model}.py,
slurm/s3_2x3.sbatch, src/skqd/hardware.py, prompts/LOG.md.  Push: yes.

## Escalation
If a transpiled circuit leaks (layout permutation or measurement order wrong), fix the mapping in the build script,
never in codec.py; if leakage persists after two attempts, stop and report the permutation found.  If the r = 1
simulated yield is below 0.05, stop: the calibration snapshot is not representative and the planner decides.
