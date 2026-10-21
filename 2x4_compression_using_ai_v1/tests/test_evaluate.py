"""Unit tests of the evaluator (small systems only; the 28-qubit runs are scripts)."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.evaluate import counts, term_unitary_columns   # noqa: E402
from skqd.circuits_ir import run_ir                      # noqa: E402


def test_counts_and_depth():
    g = [("cx", [0, 1], None), ("ry", [1], 0.3), ("cx", [2, 3], None), ("cx", [1, 2], None),
         ("cp", [0, 3], 0.1), ("gphase", [], 0.2)]
    c = counts(g)
    assert c["n_2q"] == 4 and c["n_1q"] == 1
    assert c["depth_2q"] == 2          # layer 1: cx(0,1), cx(2,3); layer 2: cx(1,2), cp(0,3)


def test_counts_rejects_uncosted():
    with pytest.raises(ValueError):
        counts([("unitary", [0, 1], np.eye(4))])
    with pytest.raises(ValueError):
        counts([("mcu", [0, 1], None)])


def test_index_qubit_trick_matches_dense():
    rng = np.random.default_rng(7)
    k = 4
    g = []
    for _ in range(30):
        a, b = rng.choice(k, 2, replace=False)
        g.append(("cx", [int(a), int(b)], None))
        g.append(("ry", [int(rng.integers(k))], float(rng.normal())))
        g.append(("rz", [int(rng.integers(k))], float(rng.normal())))
    support = [3, 5, 8, 9]                                  # arbitrary global labels
    gg = [(n, [support[q] for q in qs], p) for n, qs, p in g]
    states = [0, 3, 5, 6, 9, 12, 15]
    col, out, amp = term_unitary_columns(gg, support, states)
    # dense reference: column s = run_ir from |s>
    for j, s in enumerate(states):
        v0 = np.zeros(2 ** k, complex)
        v0[s] = 1
        ref = run_ir(g, k, v0)
        got = np.zeros(2 ** k, complex)
        sel = col == j
        got[out[sel]] = amp[sel]
        assert np.abs(got - ref).max() < 1e-12
