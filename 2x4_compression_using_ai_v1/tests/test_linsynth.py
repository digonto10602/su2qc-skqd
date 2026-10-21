"""C4: angle-linear synthesis (exact block rounds, k-independent skeleton), flags, CX-run resynthesis, rounding bound."""
import os
import sys

import numpy as np
import scipy.linalg as sla

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.linsynth import LinRot, lin_block_rounds, lin_two_level    # noqa: E402
from c2x4.peephole import _same_permutation, resynth_cx_runs          # noqa: E402
from skqd.circuits_ir import run_ir                                   # noqa: E402


def _recon(rounds, n):
    U = np.eye(n, dtype=complex)
    for rd in rounds:
        for (i, j, V) in rd:
            V = V.unitary() if isinstance(V, LinRot) else V
            M = np.eye(n, dtype=complex)
            M[np.ix_([i, j], [i, j])] = V
            U = M @ U
    return U


def test_block_rounds_exact_and_sign():
    rng = np.random.default_rng(7)
    for K in ([[0.7, -0.4]], [[-0.7]], [[0.3], [-0.9]]):
        K = np.array(K)
        a, b = K.shape
        A = np.zeros((a + b, a + b))
        A[:a, a:] = K
        A[a:, :a] = -K.T
        th = float(rng.uniform(0.1, 0.9))
        assert np.abs(_recon(lin_block_rounds(A, th), a + b) - sla.expm(th * A)).max() < 1e-13


def test_lin_two_level_skeleton_independent_of_theta():
    G = np.array([[0, 0.5], [0.5, 0]])
    sk = set()
    for th in (0.1, 0.7, 2.9, 5.5):
        g = lin_two_level(0b101, [(0b000, 0b101, LinRot(G, th)), (0b010, 0b111, LinRot(-G, th))],
                          np.array([0, 5, 2, 7]), 3)
        sk.add(tuple((n, tuple(q)) for n, q, _p in g))
        U = np.zeros((8, 8), dtype=complex)
        for s in range(8):
            v = np.zeros(8, dtype=complex)
            v[s] = 1
            U[:, s] = run_ir(g, 3, v)
        R = LinRot(G, th).unitary()
        assert np.abs(U[np.ix_([0, 5], [0, 5])] - R).max() < 1e-13
        assert np.abs(U[np.ix_([2, 7], [2, 7])] - LinRot(-G, th).unitary()).max() < 1e-13
    assert len(sk) == 1


def test_cx_resynthesis_is_exact():
    run = [("cx", [0, 1], None), ("cx", [1, 2], None), ("cx", [0, 1], None), ("cx", [1, 2], None),
           ("cx", [2, 0], None)]
    out, saved = resynth_cx_runs(run)
    assert _same_permutation(run, out, [0, 1, 2]) and saved >= 0
