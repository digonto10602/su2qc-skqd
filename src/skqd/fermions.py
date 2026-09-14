"""
Two-colour staggered-fermion site.

Local Fock space F = span{|n_1 n_2>} with the ordering (0,0), (1,0), (0,1), (1,1)
(index c = n_1 + 2 n_2).  Local annihilators with the intra-site Jordan-Wigner
sign:  psi_1 = a (x) 1,  psi_2 = P (x) a,  P = (-1)^n on one mode.

Global operators on a chain of sites (JW ordering = site index order):
    psi_{x,i} = (prod_{z<x} P_z) (x) psi^loc_{x,i},   P_z = (-1)^{n_z}.

Matter charge  Q_a = psi^dag (sigma_a/2) psi  (see su2.py for why sigma_a/2 and
not -sigma_a^T/2: it is tied to the convention L_a = -J_a^T, R_a = +J_a of the
link generators).

n = occupation number (0, 1, 2), c = Fock index, P = parity operator.
"""
from __future__ import annotations

import numpy as np

from .su2 import SIGMA

A1 = np.array([[0, 1], [0, 0]], dtype=complex)  # annihilator on one mode
P1 = np.diag([1.0, -1.0]).astype(complex)       # (-1)^n on one mode
I2 = np.eye(2, dtype=complex)

PSI = [np.kron(A1, I2), np.kron(P1, A1)]               # psi_1, psi_2 (4x4)
N_OP = sum(p.conj().T @ p for p in PSI)                 # n = n_1 + n_2
PARITY = np.kron(P1, P1)                                # (-1)^n
Q_OPS = [
    sum((SIGMA[a][i, j] / 2) * PSI[i].conj().T @ PSI[j] for i in range(2) for j in range(2))
    for a in range(3)
]
OCC = np.array([0, 1, 1, 2])                            # occupation of Fock index c
FOCK_BLOCK = {0: [0], 1: [1, 2], 2: [3]}                # Fock indices with occupation n


def check_algebra() -> float:
    """Return the largest deviation from {psi_i, psi_j^dag} = delta_ij, {psi_i, psi_j} = 0."""
    err = 0.0
    for i in range(2):
        for j in range(2):
            ac = PSI[i] @ PSI[j].conj().T + PSI[j].conj().T @ PSI[i]
            err = max(err, np.abs(ac - (np.eye(4) if i == j else 0)).max())
            aa = PSI[i] @ PSI[j] + PSI[j] @ PSI[i]
            err = max(err, np.abs(aa).max())
    return float(err)
