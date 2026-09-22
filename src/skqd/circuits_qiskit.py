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
        elif name == "ry":
            qc.ry(par, qs[0])
        elif name == "rx":
            qc.rx(par, qs[0])
        elif name == "gphase":
            qc.global_phase += par
        elif name == "p":
            qc.p(par, qs[0])
        elif name == "cp":
            qc.cp(par, qs[0], qs[1])
        elif name == "cx":
            qc.cx(qs[0], qs[1])
        elif name == "unitary":
            qc.unitary(np.asarray(par), list(qs), label=f"U{len(qs)}")
        elif name == "mcu":
            from qiskit.circuit.library import UnitaryGate

            U2, cstate = par
            g = UnitaryGate(np.asarray(U2)).control(len(qs) - 1, ctrl_state=int(cstate))
            qc.append(g, [*qs[:-1], qs[-1]])
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


def _aer_options(noise_model=None, seed: int = 11, method: str = "automatic",
                 device: str = "CPU", batched_shots_gpu: bool = False,
                 cu_statevec_enable: bool = True, precision: str = "double") -> dict:
    """The AerSimulator keyword arguments, split out from `_aer_simulator` so that the GPU-only
    set can be checked on a machine without a GPU (tests/test_ci_gpu_mode.py); nothing here
    imports qiskit."""
    kwargs = dict(method=method, device=device, seed_simulator=seed)
    if noise_model is not None:
        kwargs["noise_model"] = noise_model
    if device == "GPU":
        if method == "automatic":
            kwargs["method"] = "statevector"
        if batched_shots_gpu:
            kwargs["batched_shots_gpu"] = True
        if cu_statevec_enable:
            kwargs["cuStateVec_enable"] = True
        if precision != "double":
            kwargs["precision"] = precision
    return kwargs


def _aer_simulator(noise_model=None, seed: int = 11, method: str = "automatic",
                   device: str = "CPU", batched_shots_gpu: bool = False,
                   cu_statevec_enable: bool = True, precision: str = "double"):
    """AerSimulator configured per the owner's engine and HPC policy (RUNBOOK.md, "Engine and
    HPC policy for Perlmutter runs"): for noisy shot sampling on a GPU the policy fixes
    ``AerSimulator(method="statevector", device="GPU", cuStateVec_enable=True,
    batched_shots_gpu=True)``.

    Every GPU-only option is passed ONLY when device == "GPU", so the CPU path (the laptop and
    every other gate) is bit-for-bit what it was before this function existed.  On the GPU the
    policy's method is used when the caller left `method` at its default "automatic"; an explicit
    method is never overridden.

    precision: "double" per policy -- `precision="single"` is allowed only after a tolerance
    check, so the flag exists and defaults to double; nothing in this package passes "single".

    Both options exist in qiskit-aer 0.15.1 (the CI pin; verified against the 0.15.1 wheel's
    `AerSimulator._default_options`: `cuStateVec_enable=False`, `batched_shots_gpu=False`,
    `batched_shots_gpu_max_qubits=16`) and in 0.17.2 (the laptop).  Aer's own documentation of
    `batched_shots_gpu` states "cuStateVec_enable is not supported for this option", i.e. with
    both set Aer batches the shots when the number of ACTIVE qubits is <= 16 and otherwise falls
    back to the cuStateVec kernels -- at 2x2 the generic-noise circuits use 12 qubits (batched)
    and the FakeFez patch 17 (cuStateVec).  Neither combination is an error.  If some Aer build
    nevertheless rejects an option (AerError "Invalid option ..."), it is dropped and the run
    continues, so the gate never dies on a simulator flag.
    """
    from qiskit_aer import AerSimulator

    kwargs = _aer_options(noise_model=noise_model, seed=seed, method=method, device=device,
                          batched_shots_gpu=batched_shots_gpu,
                          cu_statevec_enable=cu_statevec_enable, precision=precision)
    try:
        return AerSimulator(**kwargs)
    except Exception as exc:                                        # pragma: no cover (GPU only)
        dropped = [k for k in ("cuStateVec_enable", "batched_shots_gpu", "precision")
                   if k in kwargs]
        if not dropped:
            raise
        for k in dropped:
            kwargs.pop(k)
        import warnings

        warnings.warn(f"AerSimulator rejected {dropped} ({exc}); retrying without them",
                      RuntimeWarning)
        return AerSimulator(**kwargs)


def _transpile_for(qc, sim, backend=None, basis=("rz", "sx", "x", "cz"), coupling_map=None,
                   optimization_level: int = 3, seed: int = 11):
    """The transpilation `sample` and `sample_many` share, so that a batched run and a loop of
    single runs execute exactly the same circuits.  With a backend the circuit is mapped ONTO
    that backend (`basis` and `coupling_map` are then ignored); without one it is put into the
    given basis at optimization level 1, which is what gate L4 has always done."""
    from qiskit import transpile

    if backend is not None:
        return transpile(qc, backend=backend, optimization_level=optimization_level,
                         seed_transpiler=seed)
    return transpile(qc, sim, basis_gates=list(basis), coupling_map=coupling_map,
                     optimization_level=1, seed_transpiler=seed)


def sample(gates: list, n: int, shots: int, noise_model=None, coupling_map=None,
           basis=("rz", "sx", "x", "cz"), seed: int = 11, method: str = "automatic",
           device: str = "CPU", backend=None, optimization_level: int = 3,
           batched_shots_gpu: bool = False, cu_statevec_enable: bool = True,
           precision: str = "double") -> dict:
    """Run ONE circuit on AerSimulator and return {bit tuple: count} in this package's order.
    For many circuits use `sample_many`, which issues a single `run([...])` call as the owner's
    HPC policy requires; this function stays as it was for the single-circuit callers (gate L2,
    the L4 pilot and timing ladder).

    device='GPU' requires qiskit-aer-gpu (NOT available on this laptop: the 0.15.1 wheel is
    incompatible with the pinned qiskit 2.5.2; the Perlmutter CI runs qiskit 1.4.3 + aer-gpu
    0.15.1 on an A100).  The GPU options (statevector, cuStateVec_enable, batched_shots_gpu,
    precision) are handled in `_aer_simulator` and reach Aer only when device='GPU'.

    backend: a Qiskit BackendV2 (e.g. FakeFez()).  When given, the circuit is transpiled
    ONTO that backend (its coupling map, basis and layout, optimization_level, seed) before
    sampling, so that a NoiseModel.from_backend(backend) applies its per-qubit and per-edge
    calibration to the physical qubits the circuit really uses; `basis` and `coupling_map`
    are then ignored.  Aer truncates the idle device qubits, so only the active patch is
    simulated.  Classical bit i still carries IR qubit i."""
    sim = _aer_simulator(noise_model=noise_model, seed=seed, method=method, device=device,
                         batched_shots_gpu=batched_shots_gpu,
                         cu_statevec_enable=cu_statevec_enable, precision=precision)
    tq = _transpile_for(ir_to_qiskit(gates, n, measure=True), sim, backend=backend, basis=basis,
                        coupling_map=coupling_map, optimization_level=optimization_level, seed=seed)
    result = sim.run(tq, shots=shots).result()
    counts = result.get_counts()
    return {qiskit_key_to_bits(k): v for k, v in counts.items()}


def sample_many(gates_list: list, n: int, shots: int, noise_model=None, coupling_map=None,
                basis=("rz", "sx", "x", "cz"), seed: int = 11, method: str = "automatic",
                device: str = "CPU", backend=None, optimization_level: int = 3,
                batched_shots_gpu: bool = False, cu_statevec_enable: bool = True,
                precision: str = "double") -> list:
    """Sample MANY IR circuits in ONE `AerSimulator.run([...])` call and return one
    {bit tuple: count} dict per circuit, in the order given, in this package's bit order.

    The owner's HPC policy (RUNBOOK.md): "transpile once and reuse; submit many circuits in ONE
    run([...]) call ... rather than a Python loop of run calls".  A loop pays the simulator and
    transpiler set-up per call -- measured on this laptop CPU as 1.4 s for the first call against
    0.18 s for the next (gate L4's timing ladder), and about 6 s per call in the H0P work -- and
    on a GPU it re-enters the CUDA context each time and cannot spread circuits over the device.

    Each circuit is transpiled individually with the same arguments `sample` uses (shared
    `_transpile_for`), so the executed circuits are identical to the ones a `sample` loop would
    execute.  The measured counts are NOT bit-for-bit those of such a loop: with one
    `seed_simulator` Aer derives a separate RNG stream per experiment, so only the first
    experiment of the batch reproduces a single `sample` call (checked in
    tests/test_ci_gpu_mode.py, which pins `sample_many([g]) == sample(g)` and the identity of the
    batched results for circuits whose outcome is deterministic).

    API note: only `transpile`, `AerSimulator`, `run([...])` and `Result.get_counts(i)` are used,
    all present in qiskit 1.4.3 / aer 0.15.1 (the CI) and 2.5.2 / 0.17.2 (the laptop)."""
    sim = _aer_simulator(noise_model=noise_model, seed=seed, method=method, device=device,
                         batched_shots_gpu=batched_shots_gpu,
                         cu_statevec_enable=cu_statevec_enable, precision=precision)
    tqs = [_transpile_for(ir_to_qiskit(g, n, measure=True), sim, backend=backend, basis=basis,
                          coupling_map=coupling_map, optimization_level=optimization_level,
                          seed=seed)
           for g in gates_list]
    result = sim.run(tqs, shots=shots).result()
    out = []
    for i in range(len(tqs)):
        counts = result.get_counts(i)
        out.append({qiskit_key_to_bits(k): v for k, v in counts.items()})
    return out
