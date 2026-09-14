"""
Qiskit translation of the IR circuits (circuits_ir.py) and the laptop-side
helpers: statevector check against the numpy reference, transpiled CZ counts
(gate S2), Aer noise-model sampling (gate S3).

NOT executed in the cloud sandbox where this package was assembled (PyPI was
not reachable there): the first laptop gate, scripts/laptop_L2_qiskit_check.py,
verifies this module against skqd.reference_sim / skqd.circuits_ir, which are
the validated ground truth.  Keep the API surface small and standard
(QuantumCircuit, transpile, Statevector, UnitaryGate, AerSimulator, NoiseModel).

Conventions.  IR qubit k = Qiskit qubit k.  A `unitary` IR gate on qubits
[q_0, ..., q_{k-1}] with matrix U (q_0 = least significant bit) is
qc.unitary(U, [q_0, ..., q_{k-1}]), which is Qiskit's own little-endian
convention.  Counts keys from Qiskit have qubit 0 at the right end; use
skqd.reference_sim.qiskit_key_to_bits to convert them to this package's bit tuples.
"""
from __future__ import annotations

import numpy as np

from .reference_sim import qiskit_key_to_bits


def ir_to_qiskit(gates: list, n: int, measure: bool = True):
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n, n if measure else 0)
    for name, qs, par in gates:
        if name == "x":
            qc.x(qs[0])
        elif name == "h":
            qc.h(qs[0])
        elif name == "rz":
            qc.rz(par, qs[0])
        elif name == "p":
            qc.p(par, qs[0])
        elif name == "cp":
            qc.cp(par, qs[0], qs[1])
        elif name == "cx":
            qc.cx(qs[0], qs[1])
        elif name == "unitary":
            qc.unitary(np.asarray(par), list(qs), label=f"U{len(qs)}")
        else:
            raise ValueError(name)
    if measure:
        qc.barrier()
        qc.measure(range(n), range(n))
    return qc


def statevector(gates: list, n: int) -> np.ndarray:
    """Exact statevector of the IR circuit (no measurement), in this package's bit order."""
    from qiskit.quantum_info import Statevector

    qc = ir_to_qiskit(gates, n, measure=False)
    return np.asarray(Statevector(qc).data)


def transpile_counts(gates: list, n: int, coupling_map=None, basis=("rz", "sx", "x", "cz"),
                     optimization_level: int = 3, seed: int = 7) -> dict:
    """Transpile to the given basis (default: Heron-like {rz, sx, x, cz}) and return
    the gate counts, depth, and CZ count.  coupling_map: None (all-to-all) or a Qiskit
    CouplingMap (e.g. CouplingMap.from_heavy_hex(3))."""
    from qiskit import transpile

    qc = ir_to_qiskit(gates, n, measure=False)
    tq = transpile(qc, basis_gates=list(basis), coupling_map=coupling_map,
                   optimization_level=optimization_level, seed_transpiler=seed)
    ops = tq.count_ops()
    return {"ops": dict(ops), "depth": tq.depth(), "cz": int(ops.get("cz", 0)), "n_qubits": tq.num_qubits}


def generic_noise_model(p1: float = 3e-4, p2: float = 3e-3, p_ro: float = 1e-2):
    """Aer noise model: depolarizing errors on 1- and 2-qubit gates, symmetric readout flips.
    Replace by NoiseModel.from_backend(backend) with a real calibration for gate S3."""
    from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(p1, 1), ["rz", "sx", "x", "h", "p"])
    nm.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ["cz", "cx", "cp"])
    nm.add_all_qubit_readout_error(ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]]))
    return nm


def sample(gates: list, n: int, shots: int, noise_model=None, coupling_map=None,
           basis=("rz", "sx", "x", "cz"), seed: int = 11, method: str = "automatic",
           device: str = "CPU") -> dict:
    """Run the circuit on AerSimulator and return {bit tuple: count} in this package's order.
    device='GPU' requires qiskit-aer-gpu (the laptop's GTX 1060 Max-Q is supported)."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    qc = ir_to_qiskit(gates, n, measure=True)
    kwargs = dict(method=method, device=device, seed_simulator=seed)
    if noise_model is not None:
        kwargs["noise_model"] = noise_model
    sim = AerSimulator(**kwargs)
    tq = transpile(qc, sim, basis_gates=list(basis), coupling_map=coupling_map, optimization_level=1,
                   seed_transpiler=seed)
    result = sim.run(tq, shots=shots).result()
    counts = result.get_counts()
    return {qiskit_key_to_bits(k): v for k, v in counts.items()}
