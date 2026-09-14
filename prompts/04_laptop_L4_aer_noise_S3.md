# 04 — L4: Aer noise-model sampling at 2x2 (gate S3 preparation)
executor: runner-sonnet   effort: low   (executor-opus at high for the calibration-based model)
time budget: 30 min (the script scales shots to `--budget-minutes 25`)   machine: laptop (CPU, or GPU if L2 found it working)

## Goal
Replace the proxy noise of gate S1 by a gate-level Aer noise model (depolarizing CZ error p2, single-qubit
p1, readout flips) on the exact 2x2 circuits, decode, and compare the measured accepted yield with the
manual's rule yield ≈ 0.82 f, f = (1 − ε)^N_CZ.  Also the first application of the 30-minute rule: the
script measures a 1000-shot pilot and chooses the shots per circuit so that both sectors fit in 25 minutes.

## Inputs
- `validation/L3.json` (CZ counts; f is computed from them)
- `scripts/laptop_L4_aer_noise.py`

## Steps
1. `python scripts/run_gate.py L4 --p2 3e-3 --budget-minutes 25` (add `--gpu` if qiskit-aer-gpu works)
2. `python scripts/run_gate.py L4 --p2 1e-3 --budget-minutes 25` (second point of the yield-versus-ε curve;
   the JSON of the first run is overwritten — copy it to `validation/L4_p2_3e-3.json` first)
3. Record in prompts/LOG.md: shots per circuit chosen, seconds per shot, yields, and what a 2x3 run
   (20 qubits, 32–44 circuits per sector, 2e5 shots per sector) would take at the measured rate; if it exceeds
   30 min, mark it "desktop RTX 3070 or cluster" in reports/laptop_vs_hpc_plan.md (scribe-haiku).
4. Push on PASS.

## Pass criteria
- measured yield within a factor 3 of 0.82 f for both sectors (the proxy is rough; the goal is the curve, not
  an exact match)
- exact E0 inside the Weinstein interval in both sectors
- total runtime < 30 min

## Outputs
validation/L4.json (+ copies per p2), reports/L4_aer_noise.md, prompts/LOG.md, laptop_vs_hpc_plan.md updated.

## Escalation
If the yield is far below 0.82 f at the transpiled CZ count, the circuits are too deep for the proxy to apply
(f ≪ 0.05): this is the S2 problem, not an S3 failure — note it and proceed to prompt 06.  If the Weinstein
criterion fails, the decoder/sector filter is letting wrong configurations in: executor-opus checks the
rejection counts in the JSON, then planner-fable.
