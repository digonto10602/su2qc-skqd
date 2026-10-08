"""prompts/34 (gate ENC_compare): the de-duplicated codec (encoding E2) and the `codec=` arguments.

The current codec stays the default everywhere: the `codec=None` paths must reproduce the S2 per-term
CZ counts exactly.  The dedup codec must round-trip every basis state, reject or decode every single
flip without any exception other than Reject, satisfy the `localize` locality assertions on its own
support rule for every term, and give an exact diagonal gate on all codewords."""
import json
import os

import numpy as np
import pytest

from skqd.basis import enumerate_basis
from skqd.circuits_ir import CircuitFactory, run_ir
from skqd.codec import Codec, Reject
from skqd.codec_dedup import DedupCodec
from skqd.exact import Model, mass_default
from skqd.lattice import Ladder
from skqd.reference_sim import CodewordEmbedding, bits_to_int, localize, term_support

ROOT = os.path.join(os.path.dirname(__file__), "..")
G2 = 4.0


@pytest.fixture(scope="module")
def m2():
    return Model(2)


@pytest.fixture(scope="module")
def m3():
    return Model(3)


@pytest.mark.parametrize("Lx,dim,nq", [(2, 82, 8), (3, 1727, 13)])
def test_round_trip_and_distinct(Lx, dim, nq):
    basis = enumerate_basis(Ladder(Lx))
    c = DedupCodec(basis)
    assert c.n_qubits == nq
    cw = c.all_codewords()
    assert cw.shape == (dim, nq)
    assert len({tuple(r) for r in cw.tolist()}) == dim
    for k, lab in enumerate(basis.labels):
        kk, ll = c.decode(c.encode(lab))
        assert kk == k and ll == lab


def test_single_flips_2x2_reject_or_valid():
    basis = enumerate_basis(Ladder(2))
    c = DedupCodec(basis)
    for lab in basis.labels:
        bits = c.encode(lab)
        for q in range(c.n_qubits):
            b = list(bits)
            b[q] ^= 1
            for target in (None, 0, 2):
                try:
                    k, l2 = c.decode(tuple(b), target)
                except Reject as r:
                    assert str(r) in ("flag", "sector", "unknown")
                    continue
                assert basis.labels[k] == l2


def test_decode_counts_has_no_link_reason():
    basis = enumerate_basis(Ladder(2))
    c = DedupCodec(basis)
    acc, rej = c.decode_counts({"1" * c.n_qubits: 3, "0" * c.n_qubits: 2}, 0)
    assert set(rej) == {"flag", "sector", "unknown"}
    assert sum(acc.values()) + sum(rej.values()) == 5


def test_charged_vertices_are_out_of_scope():
    basis = enumerate_basis(Ladder(2, static_sites=(0,)))
    with pytest.raises(NotImplementedError):
        DedupCodec(basis)


def test_layout_is_link_register_then_vertex_bits():
    basis = enumerate_basis(Ladder(3))
    c = DedupCodec(basis)
    lay = c.layout()
    assert [lay["links"][str(l)]["qubit"] for l in range(basis.lat.n_links)] == list(range(basis.lat.n_links))
    assert [lay["vertices"][str(s)]["qubit"] for s in range(basis.lat.n_sites)] == \
        [basis.lat.n_links + s for s in range(basis.lat.n_sites)]


def test_dedup_supports_pass_localize_2x3(m3):
    c = DedupCodec(m3.basis)
    for l in range(m3.lat.n_links):
        sup = term_support(m3, "hop", l, codec=c)
        assert sup == c.support("hop", l)
        states, h, _ = localize(m3, m3.terms.hop[l], sup, codec=c)
        assert len(states) > 0
    for P in range(len(m3.lat.plaquettes)):
        sup = term_support(m3, "plaq", P, codec=c)
        states, h, _ = localize(m3, -m3.terms.plaq[P] / (2 * G2), sup, codec=c)
        assert len(states) > 0
    assert term_support(m3, "diag", 0, codec=c) == list(range(c.n_qubits))


def test_codec_none_paths_unchanged_2x2(m2):
    """Per-term CZ of the current codec at 2x2 equals validation/S2.json term by term."""
    from skqd import circuits_qiskit as cq
    with open(os.path.join(ROOT, "validation", "S2.json")) as fh:
        expected = json.load(fh)["data"]["2x2"]["per_term_cz"]
    F = CircuitFactory(m2, G2)
    assert isinstance(F.codec, Codec)
    dt = m2.reference(G2, 0).dt
    got = {"diag": cq.transpile_counts(F.diag_gates(dt), F.n)["cz"]}
    for l in range(m2.lat.n_links):
        got[f"hop{l}"] = cq.transpile_counts(F.hop_gates(l, dt), F.n)["cz"]
    for P in range(len(m2.lat.plaquettes)):
        got[f"plaq{P}"] = cq.transpile_counts(F.plaq_gates(P, dt, True), F.n)["cz"]
    assert got == expected
    # the explicit-default and the None paths give the same supports and gates
    for l in range(m2.lat.n_links):
        assert term_support(m2, "hop", l) == term_support(m2, "hop", l, codec=None)
    E0, E1 = CodewordEmbedding(m2), CodewordEmbedding(m2, codec=None)
    assert np.array_equal(E0.ints, E1.ints) and E0.n == 12


@pytest.mark.parametrize("Lx", [2, 3])
def test_dedup_diag_gates_exact(Lx, m2, m3):
    M = m2 if Lx == 2 else m3
    c = DedupCodec(M.basis)
    F = CircuitFactory(M, G2, codec=c)
    E = CodewordEmbedding(M, codec=c)
    D = (mass_default(G2) * M.terms.mass + 0.5 * G2 * M.terms.electric).diagonal()
    rng = np.random.default_rng(7)
    for theta in (0.37, 1.3):
        v = rng.normal(size=M.basis.dim) + 1j * rng.normal(size=M.basis.dim)
        v /= np.linalg.norm(v)
        out = run_ir(F.diag_gates(theta), c.n_qubits, E.embed(v))
        ref = np.exp(-1j * theta * D) * v
        assert np.abs(E.project(out) - ref).max() < 1e-12
        assert abs(E.leakage(out)) < 1e-12


def test_dedup_embedding_ints(m2):
    c = DedupCodec(m2.basis)
    E = CodewordEmbedding(m2, codec=c)
    assert E.n == 8
    assert np.array_equal(E.ints, [bits_to_int(r) for r in c.all_codewords()])
