# 07 — H0: first QPU session, 2x2 calibration run (12 qubits)
executor: executor-opus   effort: high   (planner-fable max for the go/no-go decision)
time budget: one QPU session + 1 day analysis   machine: IBM Heron-class device (or the Nighthawk r2 if available) + laptop for post-processing
prerequisites: S2 PASS (structured circuits ≤ 250 CZ at 2x2), S3 PASS (Aer device-model recall ≥ 0.9 with the production set), L2/L4 PASS

## Goal
Manual Step 9.1: validate the codewords, decoder and sector filter on real bit strings; measure the accepted
yield versus CZ count with the one-step circuits (N_CZ ≈ 250, 500, 750 by repetition); measure the per-qubit
readout confusion; verify the flux-bit link-consistency checks.  Ritz energies are a consistency check of bit
order and conventions (the 2x2 sectors saturate), not an accuracy test.

## Inputs
- production circuit set: `CircuitFactory(Model(2), g2=4).circuit_set(twoB, dt)` for B = 0 and B = 1, transpiled
  with the structured gates of prompt 06 to the device basis and coupling map (`transpile_counts`)
- shot rule, eq. (5): S ≥ 7.7/(f p) with p = 1e-3 and the f predicted by S3 (record it before the run)
- `skqd.codec.Codec.decode_counts` for post-selection; `skqd.skqd.ritz/certify` for the consistency check

## Steps
1. Build and freeze the circuit list (JSON of the transpiled QASM, CZ counts, qubit map) in
   `data/hardware/H0_<date>/circuits/`; write the preregistration paragraph (expected yields from S3) in
   `reports/H0_prereg_<date>.md` BEFORE submitting.
2. Submit with dynamical decoupling and Pauli twirling only (no error-mitigated expectation values: SKQD needs
   raw bit strings); also submit the readout-calibration circuits (all-0 / all-1 and single-qubit flips).
3. Save raw counts to `data/hardware/H0_<date>/counts/*.json` (never modify them); decode with the sector filter;
   record accepted yield, rejection reasons (flag / link / sector) per circuit; compute the readout confusion
   matrix; compute Ritz energies per sector with certification.
4. Compare the measured f (accepted yield / 0.82) with the S3 prediction; H0 criterion: within 30 %.
5. reports/H0_hardware_2x2.md via a script (`scripts/gate_H0.py`, to be written by executor-opus: it must
   produce validation/H0.json from the raw counts, no hand-typed numbers), commit and push.

## Pass criteria
- decoder validity: every accepted string is a valid codeword of the target sector (by construction) and the
  fraction of accepted strings among random-looking (flagged) ones is < 1 %
- measured f within 30 % of the S3 model for the 250-CZ circuits
- Ritz energies of the saturated sectors reproduce E0 = −3.6408 (B = 0) and −1.8616 (B = 1) to 1e-6
  (the sectors saturate, so any bit-order mistake shows up as a wrong energy)

## Outputs
raw counts, calibration snapshot, transpiled circuits, validation/H0.json, reports/H0_hardware_2x2.md.  Push: yes.

## Escalation
If the yield is far below the model at 250 CZ, do not spend the 2x3 budget: planner-fable re-plans (fewer
coarse steps k = 1, 2 only; Plan B of manual Sec. 11).
