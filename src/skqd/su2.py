"""
SU(2) building blocks: spin matrices, Clebsch-Gordan coefficients, and the
truncated electric-basis link operators.

Conventions (fixed here and verified numerically by tests/test_su2.py and by
gate E1, which checks [G_a(x), H] = 0 in the redundant basis):

* Link Hilbert space  H_link = (+)_{j <= jmax}  span{ |j, mL, mR> },
  dimension  sum_j (2j+1)^2  (= 5 for jmax = 1/2, 14 for jmax = 1).
  The state |j, mL, mR> is the wavefunction  sqrt(2j+1) D^j_{mL mR}(U).
* U_{ij}  (i, j in {+1/2, -1/2} colour indices) is multiplication by
  D^{1/2}_{ij}(U), projected to j <= jmax:
      <j' mL' mR'| U_ij |j mL mR> = sqrt((2j+1)/(2j'+1))
                                    * C(1/2 i, j mL | j' mL') * C(1/2 j, j mR | j' mR')
  (Clebsch-Gordan series of D^{1/2} D^j).
* Left generator  L_a = -J_a^T  acting on the mL index, right generator
  R_a = +J_a acting on the mR index (as matrices on the ket coefficients).
  They satisfy exactly, also in the truncated space,
      [L_a, U_ij] = -(T_a U)_ij ,   [R_a, U_ij] = +(U T_a)_ij ,   T_a = sigma_a/2,
  and  sum_a L_a^2 = sum_a R_a^2 = j(j+1)  (the electric energy E^2).
* Matter transforms with Q_a = psi^dag (sigma_a/2) psi, so that
  psi^dag_x U(x->y) psi_y is gauge invariant with
  G_a(x) = sum_{out} L_a + sum_{in} R_a + Q_a(x) (+ sigma_a/2 for a static charge).

Every symbol: j = link spin (0 or 1/2 for jmax=1/2), mL/mR = magnetic quantum
numbers of the left (start-site) and right (end-site) index of the link,
i,j = colour indices of the 2x2 matrix U, T_a = SU(2) generators in the
fundamental representation.
"""
from __future__ import annotations

from functools import lru_cache
from math import factorial, sqrt

import numpy as np

SIGMA = [
    np.array([[0, 1], [1, 0]], dtype=complex),
    np.array([[0, -1j], [1j, 0]], dtype=complex),
    np.array([[1, 0], [0, -1]], dtype=complex),
]


def spin_matrices(j: float):
    """Standard spin-j matrices (J_x, J_y, J_z), basis m = j, j-1, ..., -j."""
    d = int(round(2 * j + 1))
    m = np.array([j - k for k in range(d)])
    Jz = np.diag(m).astype(complex)
    Jp = np.zeros((d, d), dtype=complex)
    for k in range(1, d):  # <m+1| J+ |m>, m = m[k]
        mm = m[k]
        Jp[k - 1, k] = sqrt(j * (j + 1) - mm * (mm + 1))
    Jm = Jp.conj().T
    return [(Jp + Jm) / 2, (Jp - Jm) / (2j), Jz]


def m_values(j: float):
    d = int(round(2 * j + 1))
    return [j - k for k in range(d)]


@lru_cache(maxsize=None)
def _cg_cached(j1, m1, j2, m2, J, M):
    return _clebsch_gordan(j1, m1, j2, m2, J, M)


def clebsch_gordan(j1, m1, j2, m2, J, M) -> float:
    """Clebsch-Gordan coefficient <j1 m1 j2 m2 | J M> (Condon-Shortley phase),
    Racah's closed formula. All arguments are (half-)integers as floats."""
    key = tuple(round(2 * x) for x in (j1, m1, j2, m2, J, M))
    return _cg_cached(*[k / 2 for k in key])


def _clebsch_gordan(j1, m1, j2, m2, J, M):
    if abs(m1 + m2 - M) > 1e-9:
        return 0.0
    if J < abs(j1 - j2) - 1e-9 or J > j1 + j2 + 1e-9:
        return 0.0
    if abs(m1) > j1 + 1e-9 or abs(m2) > j2 + 1e-9 or abs(M) > J + 1e-9:
        return 0.0

    def f(x):
        return factorial(int(round(x)))

    pref = sqrt(
        (2 * J + 1)
        * f(J + j1 - j2) * f(J - j1 + j2) * f(j1 + j2 - J) / f(j1 + j2 + J + 1)
    )
    pref *= sqrt(f(J + M) * f(J - M) * f(j1 - m1) * f(j1 + m1) * f(j2 - m2) * f(j2 + m2))
    s = 0.0
    kmin = int(round(max(0, j2 - J - m1, j1 - J + m2)))
    kmax = int(round(min(j1 + j2 - J, j1 - m1, j2 + m2)))
    for k in range(kmin, kmax + 1):
        denom = (
            f(k) * f(j1 + j2 - J - k) * f(j1 - m1 - k) * f(j2 + m2 - k)
            * f(J - j2 + m1 + k) * f(J - j1 - m2 + k)
        )
        s += (-1) ** k / denom
    return pref * s


class LinkSpace:
    """Electric basis of one link truncated at jmax, and the operators on it."""

    def __init__(self, jmax: float = 0.5):
        self.jmax = jmax
        self.spins = [k / 2 for k in range(int(round(2 * jmax)) + 1)]
        self.states = []  # (j, mL, mR)
        self.offset = {}
        for j in self.spins:
            self.offset[j] = len(self.states)
            for mL in m_values(j):
                for mR in m_values(j):
                    self.states.append((j, mL, mR))
        self.dim = len(self.states)
        self.index = {s: k for k, s in enumerate(self.states)}
        self._U = None
        self._L = None
        self._R = None

    # ----- operators ---------------------------------------------------------
    def U(self):
        """U[i][j] : dim x dim matrices, colour indices i,j in (0 -> +1/2, 1 -> -1/2)."""
        if self._U is None:
            col = [0.5, -0.5]
            U = [[np.zeros((self.dim, self.dim), dtype=complex) for _ in range(2)] for _ in range(2)]
            for (j, mL, mR), k in self.index.items():
                for jp in self.spins:
                    if abs(jp - j) != 0.5:
                        continue  # 1/2 (x) j contains only j +- 1/2
                    for a, i_col in enumerate(col):
                        for b, j_col in enumerate(col):
                            mLp, mRp = mL + i_col, mR + j_col
                            if abs(mLp) > jp + 1e-9 or abs(mRp) > jp + 1e-9:
                                continue
                            kp = self.index[(jp, mLp, mRp)]
                            val = sqrt((2 * j + 1) / (2 * jp + 1))
                            val *= clebsch_gordan(0.5, i_col, j, mL, jp, mLp)
                            val *= clebsch_gordan(0.5, j_col, j, mR, jp, mRp)
                            U[a][b][kp, k] += val
            self._U = U
        return self._U

    def generators(self):
        """(L_a, R_a) a=x,y,z as dim x dim matrices: L_a = -J_a^T on mL, R_a = J_a on mR."""
        if self._L is None:
            L = [np.zeros((self.dim, self.dim), dtype=complex) for _ in range(3)]
            R = [np.zeros((self.dim, self.dim), dtype=complex) for _ in range(3)]
            for j in self.spins:
                J = spin_matrices(j)
                mv = m_values(j)
                for a in range(3):
                    La = -J[a].T
                    Ra = J[a]
                    # L acts on the mL index:  <j mL' mR| L_a |j mL mR> = (La)[mL', mL]
                    for p, mL in enumerate(mv):
                        for q, mLp in enumerate(mv):
                            for mR in mv:
                                L[a][self.index[(j, mLp, mR)], self.index[(j, mL, mR)]] += La[q, p]
                    # R acts on the mR index:  <j mL mR'| R_a |j mL mR> = (Ra)[mR', mR]
                    for p, mR in enumerate(mv):
                        for q, mRp in enumerate(mv):
                            for mL in mv:
                                R[a][self.index[(j, mL, mRp)], self.index[(j, mL, mR)]] += Ra[q, p]
            self._L, self._R = L, R
        return self._L, self._R

    def casimir(self):
        """E^2 = j(j+1), diagonal."""
        return np.diag([j * (j + 1) for (j, _, _) in self.states]).astype(complex)

    def j_of(self, k: int) -> float:
        return self.states[k][0]

    def block(self, j: float):
        """Index range of the spin-j block."""
        d = int(round(2 * j + 1))
        o = self.offset[j]
        return o, o + d * d
