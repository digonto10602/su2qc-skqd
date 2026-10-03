"""prompts/26 A2: the Quantinuum native conversion (src/skqd/quantinuum_native.py).

Every conversion rule is checked numerically against pytket's own `Circuit.get_unitary()` and
against this package's qiskit statevector; the PhasedX order and the half-turn factor are fixed
HERE, not from memory.  pytket lives in the isolated venv ~/.local/share/su2qc-quantinuum/venv
(prompts/26 A1, coordinator ruling: nothing is installed into `coding`), so every test that needs
it skips with that reason in `coding`; the pytket-free tests (HQC formula, counts reader, global
phase residual) run in both.
"""
import importlib.util
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd import circuits_qiskit as cq  # noqa: E402
from skqd import quantinuum_native as qn  # noqa: E402
from skqd.reference_sim import bits_to_int, int_to_bits, qiskit_key_to_bits  # noqa: E402

HAVE_PYTKET = importlib.util.find_spec("pytket") is not None
needs_pytket = pytest.mark.skipif(
    not HAVE_PYTKET,
    reason="pytket is not installed in this interpreter; it lives in the isolated venv "
           "~/.local/share/su2qc-quantinuum/venv (prompts/26 A1) -- run "
           "~/.local/share/su2qc-quantinuum/venv/bin/python -m pytest -q tests/test_quantinuum_native.py")


def ir_unitary_be(gates, n):
    """The IR circuit's unitary in pytket's ILO-BE convention (qubit 0 = most significant)."""
    from qiskit.quantum_info import Operator

    return Operator(cq.ir_to_qiskit(gates, n, measure=False)).reverse_qargs().data


def random_ir(n, n_gates, rng, names=("rz", "rx", "ry", "rzz")):
    gates = []
    for _ in range(n_gates):
        nm = names[rng.integers(len(names))]
        if nm == "rzz":
            a, b = rng.choice(n, 2, replace=False)
            gates.append(("rzz", [int(a), int(b)], float(rng.uniform(-2 * np.pi, 2 * np.pi))))
        else:
            gates.append((nm, [int(rng.integers(n))], float(rng.uniform(-2 * np.pi, 2 * np.pi))))
    return gates


# --------------------------------------------------------------------------- pytket-free
def test_hqc_formula_at_the_planner_mean_counts():
    c = {"n_phasedx": 3053, "n_zz": 2158, "n_qubits": 20, "n_meas": 20}
    assert abs(qn.hqc_per_shot(c) - (3053 + 10 * 2158 + 5 * 40) / 5000.0) < 1e-12
    assert abs(qn.hqc_per_shot(c) - 4.9666) < 1e-12
    assert abs(qn.hqc_job(c, 1000) - (5.0 + 1000 * 4.9666)) < 1e-9


def test_counts_reader_orders_bits_by_index_and_refuses_other_registers():
    # tuples in the order c[2], c[0], c[1]: (0, 1, 0) means c[0] = 1 -> our key 1
    out = qn.counts_from_pytket_readouts({(0, 1, 0): 7}, [("c", 2), ("c", 0), ("c", 1)])
    assert out == {(1, 0, 0): 7}
    assert bits_to_int((1, 0, 0)) == 1
    with pytest.raises(ValueError):
        qn.counts_from_pytket_readouts({(0, 1): 1}, [("c", 0), ("m", 0)])
    with pytest.raises(ValueError):
        qn.counts_from_pytket_readouts({(0, 1): 1}, [("c", 0), ("c", 2)])


def test_global_phase_residual_removes_only_a_global_phase():
    rng = np.random.default_rng(3)
    a = rng.normal(size=16) + 1j * rng.normal(size=16)
    a /= np.linalg.norm(a)
    r = qn.global_phase_residual(np.exp(0.7j) * a, a)
    assert r["max_abs_dpsi"] < 1e-15 and abs(r["phase_rad"] - 0.7) < 1e-12
    b = a.copy()
    b[0] *= -1
    assert qn.global_phase_residual(b, a)["max_abs_dpsi"] > 1e-3


def test_qiskit_to_ir_and_rzz_in_ir_to_qiskit():
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(2)
    qc.rz(0.3, 0)
    qc.rzz(0.9, 0, 1)
    qc.rx(-0.2, 1)
    qc.global_phase = 0.4
    ir = qn.qiskit_to_ir(qc)
    assert ir[0] == ("gphase", [], 0.4) and ir[2] == ("rzz", [0, 1], 0.9)
    from qiskit.quantum_info import Statevector

    assert np.max(np.abs(cq.statevector(ir, 2) - Statevector(qc).data)) < 1e-14


def test_statevector_aer_agrees_with_statevector():
    rng = np.random.default_rng(11)
    gates = [("h", [q], None) for q in range(6)] + random_ir(6, 80, rng)
    a, b = cq.statevector(gates, 6), cq.statevector_aer(gates, 6, threads=1)
    assert np.max(np.abs(a - b)) < 1e-13


# --------------------------------------------------------------------------- conversion rules
@needs_pytket
@pytest.mark.parametrize("name", ["rz", "rx", "ry"])
def test_one_qubit_rules_with_the_half_turn_factor(name):
    for ang in (0.3, -1.7, math.pi, 2.5 * math.pi):
        g = [(name, [0], ang)]
        U = qn.ir_to_pytket(g, 1, measure=False).get_unitary()
        assert np.max(np.abs(U - ir_unitary_be(g, 1))) < 1e-12
    # the half-turn factor: Rz(1.0) in pytket is rz(pi) in the IR, not rz(1.0)
    from pytket import Circuit

    c = Circuit(1)
    c.Rz(1.0, 0)
    assert np.max(np.abs(c.get_unitary() - ir_unitary_be([("rz", [0], math.pi)], 1))) < 1e-12
    assert np.max(np.abs(c.get_unitary() - ir_unitary_be([("rz", [0], 1.0)], 1))) > 0.1


@needs_pytket
def test_rzz_is_zzphase_of_angle_over_pi_and_zzmax():
    from pytket import Circuit

    for ang in (0.37, -math.pi / 2, 1.9):
        g = [("rzz", [0, 1], ang)]
        U = qn.ir_to_pytket(g, 2, measure=False).get_unitary()
        assert np.max(np.abs(U - ir_unitary_be(g, 2))) < 1e-12
    c = Circuit(2)
    c.ZZMax(0, 1)
    ir, n, _ = qn.pytket_to_ir(c)
    assert np.max(np.abs(c.get_unitary() - ir_unitary_be(ir, 2))) < 1e-12
    # and on an asymmetric 3-qubit placement (the qubit order of the reader)
    c3 = Circuit(3)
    c3.Rx(0.3, 0)
    c3.ZZPhase(0.21, 2, 0)
    c3.Ry(0.7, 1)
    ir3, _, _ = qn.pytket_to_ir(c3)
    assert np.max(np.abs(c3.get_unitary() - ir_unitary_be(ir3, 3))) < 1e-12


@needs_pytket
def test_phasedx_order_is_fixed_by_the_unitary():
    from pytket import Circuit

    for a, b in ((0.5, 0.25), (1.3, -0.7), (0.11, 1.4)):
        c = Circuit(1)
        c.add_gate(qn_optype("PhasedX"), [a, b], [0])
        ir, _, _ = qn.pytket_to_ir(c)
        assert [g[0] for g in ir] == ["rz", "rx", "rz"]
        assert np.max(np.abs(c.get_unitary() - ir_unitary_be(ir, 1))) < 1e-12
        # documented operator product Rz(b) Rx(a) Rz(-b) (half-turns)
        def rz(t):
            return np.diag([np.exp(-1j * np.pi * t / 2), np.exp(1j * np.pi * t / 2)])

        def rx(t):
            return np.array([[np.cos(np.pi * t / 2), -1j * np.sin(np.pi * t / 2)],
                             [-1j * np.sin(np.pi * t / 2), np.cos(np.pi * t / 2)]])
        assert np.max(np.abs(c.get_unitary() - rz(b) @ rx(a) @ rz(-b))) < 1e-12
        # the other time order is a different gate: the test discriminates
        wrong = [("rz", [0], math.pi * b), ("rx", [0], math.pi * a), ("rz", [0], -math.pi * b)]
        assert np.max(np.abs(c.get_unitary() - ir_unitary_be(wrong, 1))) > 1e-2


def qn_optype(name):
    from pytket import OpType

    return getattr(OpType, name)


@needs_pytket
def test_global_phase_is_carried_by_the_reader():
    from pytket import Circuit

    c = Circuit(1)
    c.Rx(0.4, 0)
    c.add_phase(0.3)
    ir, _, _ = qn.pytket_to_ir(c)
    assert ir[0][0] == "gphase" and abs(ir[0][2] - 0.3 * math.pi) < 1e-15
    assert np.max(np.abs(c.get_unitary() - ir_unitary_be(ir, 1))) < 1e-12


# --------------------------------------------------------------------------- compile_native
@needs_pytket
@pytest.mark.parametrize("level", [0, 1, 2])
def test_random_6q_round_trip_through_compile_native(level):
    rng = np.random.default_rng(100 + level)
    gates = [("h", [q], None) for q in range(6)] + random_ir(6, 120, rng)
    ref = cq.statevector(gates, 6)
    # the unitary part (no measurement): every level is state-exact
    cc = qn.compile_native(qn.ir_to_pytket(gates, 6, measure=False), "H2-2", level)
    ir, n, qmap = qn.pytket_to_ir(cc)
    assert n == 6 and qmap == {}
    assert qn.global_phase_residual(cq.statevector(ir, 6), ref)["max_abs_dpsi"] < 1e-12


@needs_pytket
def test_level0_with_measurement_is_state_exact_and_maps_qk_to_ck():
    rng = np.random.default_rng(7)
    gates = [("h", [q], None) for q in range(6)] + random_ir(6, 120, rng)
    cc = qn.compile_native(qn.ir_to_pytket(gates, 6, measure=True), "H2-2", 0)
    ir, n, qmap = qn.pytket_to_ir(cc)
    assert qmap == {k: k for k in range(6)}
    assert qn.global_phase_residual(cq.statevector(ir, 6), cq.statevector(gates, 6))["max_abs_dpsi"] < 1e-12


@needs_pytket
def test_level2_with_measurement_drops_diagonal_gates_before_measure():
    """The finding of prompts/26 A3: at level >= 1 TKET's RemoveRedundancies deletes the Rz gates
    in front of a Measure.  The measured distribution is unchanged, the state is not; Q1 is a
    STATE criterion, so such a circuit cannot be frozen."""
    rng = np.random.default_rng(5)
    gates = [("h", [q], None) for q in range(6)] + random_ir(6, 120, rng)
    gates += [("rz", [q], 0.3 + 0.1 * q) for q in range(6)]
    ref = cq.statevector(gates, 6)
    cc = qn.compile_native(qn.ir_to_pytket(gates, 6, measure=True), "H2-2", 2)
    ir, _, _ = qn.pytket_to_ir(cc)
    got = cq.statevector(ir, 6)
    assert np.max(np.abs(np.abs(got) ** 2 - np.abs(ref) ** 2)) < 1e-12
    assert qn.global_phase_residual(got, ref)["max_abs_dpsi"] > 1e-3


@needs_pytket
def test_compile_native_rejects_non_native_and_permuted_circuits():
    from pytket import Circuit, OpType

    c = Circuit(2)
    c.CX(0, 1)
    with pytest.raises(qn.NativeCompileError):
        qn.check_native(c)
    c = Circuit(3)
    c.Rz(0.1, 0)
    c.SWAP(0, 1)
    c.replace_SWAPs()
    with pytest.raises(qn.NativeCompileError):
        qn.check_native(c)
    c = Circuit(2)
    c.add_gate(OpType.TK2, [0.1, 0.2, 0.3], [0, 1])
    with pytest.raises(qn.NativeCompileError):
        qn.check_native(c)


@needs_pytket
def test_offline_backend_has_no_helios_entry_in_this_pytket_quantinuum():
    """Recorded fact (pytket-quantinuum 0.59.3): the offline machine list carries H1-1, H2-1 and
    H2-2 only.  If a later version adds Helios-1 this test fails and the build must compile it."""
    from pytket.extensions.quantinuum import QuantinuumAPIOffline

    names = {m["name"] for m in QuantinuumAPIOffline().get_machine_list()}
    assert {"H1-1", "H2-2"} <= names
    if "Helios-1" not in names:
        with pytest.raises(Exception):
            qn.offline_backend("Helios-1")


# --------------------------------------------------------------------------- serialisation
@needs_pytket
def test_json_and_qasm_round_trips():
    rng = np.random.default_rng(9)
    gates = [("h", [q], None) for q in range(5)] + random_ir(5, 80, rng)
    cc = qn.compile_native(qn.ir_to_pytket(gates, 5, measure=True), "H2-2", 0)
    sv = cq.statevector(qn.pytket_to_ir(cc)[0], 5)
    q = qn.to_qasm(cc)
    assert 'include "hqslib1.inc";' in q
    via_json = cq.statevector(qn.pytket_to_ir(qn.from_json(qn.to_json(cc)))[0], 5)
    via_qasm = cq.statevector(qn.pytket_to_ir(qn.from_qasm(q))[0], 5)
    assert np.max(np.abs(via_json - sv)) < 1e-12        # JSON keeps the global phase
    assert qn.global_phase_residual(via_qasm, sv)["max_abs_dpsi"] < 1e-12   # QASM 2 does not


# --------------------------------------------------------------------------- endianness
@needs_pytket
def test_endianness_x_on_qubit_0_is_key_1():
    from pytket import Bit, Circuit
    from pytket.backends.backendresult import BackendResult
    from pytket.utils.outcomearray import OutcomeArray

    c = Circuit(3, 3)
    c.X(0)
    for k in range(3):
        c.Measure(k, k)
    cc = qn.compile_native(c, "H2-2", 0)
    ir, n, qmap = qn.pytket_to_ir(cc)
    assert qmap == {0: 0, 1: 1, 2: 2}
    sv = cq.statevector(ir, n)
    idx = int(np.argmax(np.abs(sv)))
    assert idx == 1 and bits_to_int(int_to_bits(idx, 3)) == 1
    assert bits_to_int(qiskit_key_to_bits("001")) == 1           # the qiskit reader agrees
    # a BackendResult as a pytket backend returns it: readouts in the order of c_bits
    bits = [Bit("c", 0), Bit("c", 1), Bit("c", 2)]
    res = BackendResult(shots=OutcomeArray.from_readouts([[1, 0, 0]] * 5), c_bits=bits)
    counts = res.get_counts()                                     # BasisOrder.ilo
    out = qn.counts_from_pytket_readouts(dict(counts), [("c", 0), ("c", 1), ("c", 2)])
    assert out == {(1, 0, 0): 5} and bits_to_int((1, 0, 0)) == 1
    # scrambled c_bits: get_counts() still returns ILO = (c[0], c[1], c[2])
    res2 = BackendResult(shots=OutcomeArray.from_readouts([[0, 1, 0]] * 4),
                         c_bits=[Bit("c", 2), Bit("c", 0), Bit("c", 1)])
    assert dict(res2.get_counts()) == {(1, 0, 0): 4}


@needs_pytket
def test_endianness_cross_check_on_pytket_qiskit_aer_backend():
    """Optional cross-check (pytket-qiskit is NOT used by the build): a real pytket backend run."""
    aer = pytest.importorskip("pytket.extensions.qiskit")
    from pytket import Circuit

    c = Circuit(3, 3)
    c.X(0)
    for k in range(3):
        c.Measure(k, k)
    be = aer.AerBackend()
    h = be.process_circuit(be.get_compiled_circuit(c), n_shots=8, seed=1)
    assert dict(be.get_result(h).get_counts()) == {(1, 0, 0): 8}
