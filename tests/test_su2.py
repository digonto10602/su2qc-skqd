import itertools

import numpy as np

from skqd.fermions import check_algebra
from skqd.su2 import SIGMA, LinkSpace, clebsch_gordan


def test_clebsch_gordan_known_values():
    assert abs(clebsch_gordan(0.5, 0.5, 0.5, -0.5, 0, 0) - 1 / np.sqrt(2)) < 1e-12
    assert abs(clebsch_gordan(0.5, -0.5, 0.5, 0.5, 0, 0) + 1 / np.sqrt(2)) < 1e-12
    assert abs(clebsch_gordan(0.5, 0.5, 0.5, 0.5, 1, 1) - 1.0) < 1e-12
    assert abs(clebsch_gordan(1, 1, 0.5, -0.5, 0.5, 0.5) - np.sqrt(2 / 3)) < 1e-12


def test_link_covariance_and_algebra():
    T = [s / 2 for s in SIGMA]
    eps = np.zeros((3, 3, 3))
    eps[0, 1, 2] = eps[1, 2, 0] = eps[2, 0, 1] = 1
    eps[0, 2, 1] = eps[2, 1, 0] = eps[1, 0, 2] = -1
    for jmax in (0.5, 1.0):
        L = LinkSpace(jmax)
        U = L.U()
        Lg, Rg = L.generators()
        for a in range(3):
            for i in range(2):
                for j in range(2):
                    assert np.allclose(Lg[a] @ U[i][j] - U[i][j] @ Lg[a], -sum(T[a][i, k] * U[k][j] for k in range(2)), atol=1e-12)
                    assert np.allclose(Rg[a] @ U[i][j] - U[i][j] @ Rg[a], sum(U[i][k] * T[a][k, j] for k in range(2)), atol=1e-12)
        for G in (Lg, Rg):
            for a, b in itertools.product(range(3), repeat=2):
                assert np.allclose(G[a] @ G[b] - G[b] @ G[a], sum(1j * eps[a, b, c] * G[c] for c in range(3)), atol=1e-12)
        cas = np.diag(sum(g @ g for g in Lg)).real
        assert np.allclose(cas, L.casimir().diagonal().real)


def test_fermion_algebra():
    assert check_algebra() < 1e-14
