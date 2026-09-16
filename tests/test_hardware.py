"""Unit tests for skqd.hardware: readout confusion model and layout bookkeeping."""
import numpy as np
import pytest

from skqd.codec import Codec
from skqd.exact import Model
from skqd.hardware import (apply_inverse, codeword_bit_order, confusion_matrix,
                           link_consistency_checks, logical_statevector, transpiled_layout)


def _forward(dist: dict, C: np.ndarray) -> dict:
    """Apply the tensored readout model C to an exact distribution over bit tuples."""
    n = C.shape[0]
    out = {}
    for bits, w in dist.items():
        for m in range(2 ** n):
            mb = tuple((m >> q) & 1 for q in range(n))
            p = w
            for q in range(n):
                p *= C[q, mb[q], bits[q]]
            if p:
                out[mb] = out.get(mb, 0.0) + p
    return out


def _model(errs):
    """C[q] from (p(1|0), p(0|1)) pairs."""
    C = np.zeros((len(errs), 2, 2))
    for q, (e01, e10) in enumerate(errs):
        C[q] = [[1 - e01, e10], [e01, 1 - e10]]
    return C


def test_confusion_matrix_recovers_the_model():
    errs = [(0.10, 0.20), (0.05, 0.02), (0.01, 0.30)]
    C = _model(errs)
    N = 10 ** 7
    preps = [(0, 0, 0), (1, 1, 1)] + [tuple(1 if i == q else 0 for i in range(3)) for q in range(3)]
    counts_by_prep = {p: {k: N * v for k, v in _forward({p: 1.0}, C).items()} for p in preps}
    Chat = confusion_matrix(counts_by_prep)
    assert Chat.shape == (3, 2, 2)
    assert np.allclose(Chat.sum(axis=1), 1.0)
    assert np.abs(Chat - C).max() < 1e-9


def test_confusion_matrix_accepts_string_keys_and_needs_both_preparations():
    C = _model([(0.1, 0.2), (0.0, 0.0)])
    counts = {"00": {"00": 900, "10": 100}, "11": {"11": 800, "01": 200}}
    Chat = confusion_matrix(counts)
    assert Chat[0, 1, 0] == pytest.approx(0.1)
    assert Chat[0, 0, 1] == pytest.approx(0.2)
    assert np.abs(Chat - C).max() < 1e-12
    with pytest.raises(ValueError):
        confusion_matrix({"00": {"00": 10}})          # qubits never prepared in 1


def test_apply_inverse_undoes_the_readout_model():
    C = _model([(0.10, 0.20), (0.05, 0.02), (0.01, 0.30)])
    truth = {(0, 0, 0): 600.0, (1, 0, 1): 300.0, (1, 1, 1): 100.0}
    noisy = _forward(truth, C)
    back = apply_inverse(noisy, C, tol=1e-9)
    for bits, w in truth.items():
        assert back.get(bits, 0.0) == pytest.approx(w, abs=1e-6)
    assert sum(back.values()) == pytest.approx(sum(truth.values()), abs=1e-6)
    # every extra entry is numerical noise only
    extra = [abs(v) for k, v in back.items() if k not in truth]
    assert max(extra, default=0.0) < 1e-6


def test_apply_inverse_is_the_exact_tensor_inverse():
    rng = np.random.default_rng(3)
    C = _model([(0.07, 0.11), (0.03, 0.21)])
    counts = {tuple((i >> q) & 1 for q in range(2)): float(rng.integers(1, 100)) for i in range(4)}
    back = apply_inverse(counts, C)
    again = apply_inverse(back, np.stack([np.linalg.inv(C[q]) for q in range(2)]))
    for bits, v in counts.items():
        assert again[bits] == pytest.approx(v, abs=1e-9)


def test_codeword_bit_order_and_link_checks_match_the_codec():
    M = Model(2)
    codec = Codec(M.basis)
    order = codeword_bit_order(codec)
    assert [e["qubit"] for e in order] == list(range(codec.n_qubits))
    checks = link_consistency_checks(codec)
    assert len(checks) == M.lat.n_links
    for k, label in enumerate(M.basis.labels):
        bits = codec.encode(label)
        j2 = label[0]
        for c in checks:                       # both ends of a link carry the same flux bit
            a, b = c["qubits"]
            assert bits[a] == bits[b] == j2[c["link"]]
        for e in order:                        # the flux bits are the link labels themselves
            if e["role"] == "flux":
                assert bits[e["qubit"]] == j2[e["link"]]


def test_logical_statevector_undoes_the_transpiler_permutation():
    qiskit = pytest.importorskip("qiskit")
    from qiskit.quantum_info import Statevector
    from qiskit.transpiler import CouplingMap

    qc = qiskit.QuantumCircuit(4, 4)
    qc.h(0)
    for a, b in ((0, 1), (1, 2), (2, 3), (0, 3), (0, 2)):
        qc.cx(a, b)
    qc.t(3)
    qc.ry(0.3, 1)
    want = np.asarray(Statevector(qc).data)
    qc.measure(range(4), range(4))
    tq = qiskit.transpile(qc, basis_gates=["rz", "sx", "x", "cz"],
                          coupling_map=CouplingMap.from_line(6), initial_layout=[5, 4, 3, 2],
                          optimization_level=3, seed_transpiler=7)
    lay = transpiled_layout(tq, 4)
    assert lay["measurement_consistent"]
    got = logical_statevector(tq, 4)
    assert abs(abs(np.vdot(want, got)) - 1.0) < 1e-9
