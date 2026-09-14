# 02 — L2: Qiskit circuits reproduce the numpy reference (2x2, 12 qubits)
executor: runner-sonnet   effort: low   (executor-opus at high if a criterion fails)
time budget: 20 min   machine: laptop (CPU; GPU optional)

## Goal
First circuit-level proof of concept: the Qiskit translation of the exact block-unitary circuits
(`skqd.circuits_qiskit`) must give the same statevectors as the numpy reference (`skqd.circuits_ir`,
`skqd.reference_sim`), which were verified against the dressed-basis emulation in the cloud.  This fixes the
bit order and the `UnitaryGate` convention on the real Qiskit installation — the cloud sandbox had no Qiskit,
so this module has never been executed before.

## Inputs
- `src/skqd/circuits_qiskit.py`, `src/skqd/circuits_ir.py`, `src/skqd/reference_sim.py`
- `reports/circuit_structure.md` (what the circuits contain)

## Steps
1. `pip install qiskit qiskit-aer` (already in requirements-laptop.txt).  Optional GPU:
   `pip install qiskit-aer-gpu` (CUDA 12 wheels; the GTX 1060 Max-Q is compute capability 6.1 and is supported
   by Aer's GPU statevector; if the wheel refuses the driver, stay on CPU and note it).
2. `python scripts/run_gate.py L2` (adds `--gpu` when qiskit-aer-gpu imports).
3. Read `validation/L2.json` and `reports/L2_qiskit_check.md`.
4. On PASS: `python scripts/run_gate.py L2 --push`.

## Pass criteria
- `max |Qiskit statevector - reference|` < 1e-9 over all 2x2 coarse (k = 1..4) and Trotter circuits, both sectors
- noiseless sampling: 100 % of shots decode
- TVD to the exact distribution below the shot-noise bound printed in the report

## Outputs
validation/L2.json, reports/L2_qiskit_check.md (with the CPU/GPU timings), prompts/LOG.md entry.  Push: yes.

## Escalation
If the statevector criterion fails with a large error (order 1): it is a qubit-order convention issue —
executor-opus (high) checks `ir_to_qiskit` (`qc.unitary(U, qubits)` expects qubits[0] as the least
significant bit) and `qiskit_key_to_bits` (reverse the counts key); fix, re-run.  If it fails with a small
error (1e-6): a `UnitaryGate` normalisation/transpose issue — compare a single 2-qubit `unitary` IR gate
against `Statevector`.  Two failed fixes → planner-fable.
