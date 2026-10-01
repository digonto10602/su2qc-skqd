"""The exact sparse statevector simulator against `circuits_ir.run_ir` (gate S2_2x4, C4).

`skqd.sparse_sim` is the only route by which the 28-qubit 2x4 circuits are simulated, so its
agreement with the dense reference is the evidence that the 2x4 numbers mean anything.  The
2x3 (2^20) and 2x4 (2^28) dense cross-checks are marked `slow` and left out of the default
pytest run; gate S2_2x4 runs them (`--stage circuits`, `--stage dense`).
"""
import os

import numpy as np
import pytest

from skqd.circuits_ir import CircuitFactory, run_ir
from skqd.exact import Model
from skqd.krylov import references
from skqd.reference_sim import CodewordEmbedding
from skqd.sparse_sim import SparseState, project, run_sparse, run_sparse_qiskit

SLOW = pytest.mark.skipif(not os.environ.get("SKQD_SLOW"),
                          reason="slow dense statevector check; set SKQD_SLOW=1")


def test_every_gate_type_matches_run_ir():
    """Random circuits over the whole IR gate set on 6 qubits, dense vs sparse."""
    rng = np.random.default_rng(0)
    n = 6
    worst = 0.0
    for trial in range(20):
        gates = []
        for _ in range(60):
            kind = rng.integers(0, 10)
            a, b = (int(x) for x in rng.choice(n, size=2, replace=False))
            th = float(rng.normal())
            if kind == 0:
                gates.append(("x", [a], None))
            elif kind == 1:
                gates.append(("cx", [a, b], None))
            elif kind == 2:
                gates.append(("p", [a], th))
            elif kind == 3:
                gates.append(("rz", [a], th))
            elif kind == 4:
                gates.append(("cp", [a, b], th))
            elif kind == 5:
                gates.append(("ry", [a], th))
            elif kind == 6:
                gates.append(("rx", [a], th))
            elif kind == 7:
                gates.append(("h", [a], None))
            elif kind == 8:
                gates.append(("gphase", [], th))
            else:
                A = rng.normal(size=(2, 2)) + 1j * rng.normal(size=(2, 2))
                Q, _ = np.linalg.qr(A)
                gates.append(("unitary", [a], Q))
        init = int(rng.integers(0, 2 ** n))
        psi = np.zeros(2 ** n, dtype=complex)
        psi[init] = 1.0
        dense = run_ir(gates, n, psi)
        sp = run_sparse(gates, n, init_int=init)
        worst = max(worst, float(np.abs(dense - sp.dense()).max()))
        assert abs(sp.norm() - 1.0) < 1e-12, trial
    assert worst < 1e-13, worst


def test_mcu_and_cz_match_run_ir():
    rng = np.random.default_rng(3)
    n = 5
    A = rng.normal(size=(2, 2)) + 1j * rng.normal(size=(2, 2))
    Q, _ = np.linalg.qr(A)
    gates = [("h", [q], None) for q in range(n)]
    gates += [("mcu", [0, 1, 2, 4], (Q, 2)), ("cz", [1, 3], None),
              ("mcu", [3, 4], (Q, 1))]
    dense = run_ir([g for g in gates if g[0] != "cz"], n)
    # run_ir has no 'cz': express it as cp(pi) for the dense reference
    dense = run_ir([("cp", g[1], np.pi) if g[0] == "cz" else g for g in gates], n)
    sp = run_sparse(gates, n)
    assert np.abs(dense - sp.dense()).max() < 1e-13


def test_exact_zeros_are_the_only_entries_dropped():
    """A support entry with a genuinely tiny but nonzero amplitude survives."""
    n = 3
    tiny = 1e-30
    gates = [("ry", [0], 2 * tiny)]
    sp = run_sparse(gates, n)
    idx, amp = sp.sorted_state()
    assert set(idx.tolist()) == {0, 1}
    assert abs(amp[1] - tiny) < 1e-40


def test_project_and_leakage():
    n = 4
    gates = [("h", [0], None), ("cx", [0, 1], None)]
    sp = run_sparse(gates, n)
    v, leak = project(sp, [0, 3])
    assert abs(np.sum(np.abs(v) ** 2) - 1.0) < 1e-14
    assert abs(leak) < 1e-14
    v2, leak2 = project(sp, [0])
    assert abs(leak2 - 0.5) < 1e-14
    assert abs(sp.leakage([0]) - 0.5) < 1e-14


def test_state_rejects_too_many_qubits():
    with pytest.raises(ValueError):
        SparseState(70)


def test_2x2_coarse_steps_and_trotter_match_run_ir():
    """C4 at 2x2: the 20 circuits of gate S2 (both sectors, k = 1..4, Trotter)."""
    M = Model(2)
    E = CodewordEmbedding(M)
    worst, n_circ = 0.0, 0
    for mode in ("exact", "fixed"):
        F = CircuitFactory(M, 4.0, angle_mode=mode)
        for twoB in (0, 2):
            dt = float(M.reference(4.0, twoB).dt)
            for r in references(M.basis, twoB)[:2]:
                for k in (1, 2, 3, 4):
                    g = F.coarse_step(r, k, dt)
                    worst = max(worst, float(np.abs(run_ir(g, E.n)
                                                    - run_sparse(g, E.n).dense()).max()))
                    n_circ += 1
                g = F.trotter(r, 2, dt)
                worst = max(worst, float(np.abs(run_ir(g, E.n)
                                                - run_sparse(g, E.n).dense()).max()))
                n_circ += 1
    assert n_circ == 40                       # 20 per angle mode
    assert worst < 1e-13, worst


def test_transpiled_circuit_matches_qiskit_statevector():
    """`run_sparse_qiskit` on a level-3 transpiled 2x2 coarse step, against Statevector."""
    pytest.importorskip("qiskit")
    from qiskit import transpile
    from qiskit.quantum_info import Statevector

    from skqd import circuits_qiskit as cq

    M = Model(2)
    E = CodewordEmbedding(M)
    F = CircuitFactory(M, 4.0)
    dt = float(M.reference(4.0, 0).dt)
    gates = F.coarse_step(references(M.basis, 0)[0], 1, dt)
    qc = cq.ir_to_qiskit(gates, E.n, measure=False)
    tq = transpile(qc, basis_gates=["rz", "sx", "x", "cz"], optimization_level=3,
                   seed_transpiler=7)
    ref = np.asarray(Statevector(tq).data)
    sp = run_sparse_qiskit(tq)
    assert np.abs(ref - sp.dense()).max() < 1e-13
    assert abs(sp.leakage(E.ints)) < 1e-9


@SLOW
def test_2x3_coarse_steps_match_run_ir():
    """C4 at 2x3: the k = 1, 2 circuits of reference 0 on the 2^20 statevector."""
    M = Model(3)
    E = CodewordEmbedding(M)
    F = CircuitFactory(M, 4.0)
    dt = float(M.reference(4.0, 0).dt)
    r = references(M.basis, 0)[0]
    worst = 0.0
    for k in (1, 2):
        g = F.coarse_step(r, k, dt)
        worst = max(worst, float(np.abs(run_ir(g, E.n) - run_sparse(g, E.n).dense()).max()))
    assert worst < 1e-13, worst


def test_qiskit_to_ir_accepts_the_other_gate_names():
    """`qiskit_to_ir` also translates the names a NON-transpiled circuit carries (h, cx, cp,
    ry, rx, p) and the global phase, and rejects anything it cannot execute exactly."""
    qiskit = pytest.importorskip("qiskit")
    from qiskit.quantum_info import Statevector

    from skqd.sparse_sim import qiskit_to_ir

    qc = qiskit.QuantumCircuit(4)
    qc.h(0)
    qc.x(1)
    qc.cx(0, 2)
    qc.ry(0.31, 1)
    qc.rx(-0.77, 3)
    qc.p(0.4, 2)
    qc.rz(1.1, 0)
    qc.cp(0.9, 1, 3)
    qc.sx(2)
    qc.cz(0, 3)
    qc.global_phase += 0.25
    qc.barrier()
    names = {g[0] for g in qiskit_to_ir(qc)}
    assert {"h", "x", "cx", "ry", "rx", "p", "rz", "cp", "sx", "cz", "gphase", "barrier"} <= names
    ref = np.asarray(Statevector(qc).data)
    assert np.abs(ref - run_sparse_qiskit(qc).dense()).max() < 1e-13
    bad = qiskit.QuantumCircuit(2)
    bad.swap(0, 1)
    with pytest.raises(ValueError):
        qiskit_to_ir(bad)


def test_apply_ir_rejects_an_unknown_gate_and_a_multiqubit_unitary():
    from skqd.sparse_sim import SparseState, apply_ir

    st = SparseState(3)
    with pytest.raises(ValueError):
        apply_ir(st, [("swap", [0, 1], None)])
    with pytest.raises(NotImplementedError):
        apply_ir(st, [("unitary", [0, 1], np.eye(4))])
    apply_ir(st, [("measure", [0], None), ("delay", [0], None), ("id", [0], None)])
    assert st.support_size == 1
