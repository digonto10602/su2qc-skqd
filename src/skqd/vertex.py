"""
Local singlet (intertwiner) tensors of one dressed vertex — Algorithm 1 of the
SKQD manual (VERTEXTENSORS).

A vertex owns one index per link end (mL of outgoing links, mR of incoming
links, canonical order = link index order), its matter Fock state, and
optionally a static spin-1/2.  Its physical states are the singlets of the
Gauss-law generators
    G_a = sum_{out} L_a + sum_{in} R_a + Q_a|_n (+ sigma_a/2 for a static charge),
i.e. the kernel of sum_a G_a^2 restricted to the occupation-n block.

When the kernel has dimension > 1 the states are labelled by the fusion-tree
(intertwiner) label iota: the simultaneous eigenbasis of the cumulative
Casimirs C_k = (G^{(1)} + ... + G^{(k)})^2 over the constituents in canonical
order (link ends, then matter, then static charge), combined into the single
operator sum_k 7^{k-2} C_k (k = 2 .. K'-1) as in the manual.  For an uncharged
interior vertex with three flux ends and n = 1, iota in {0, 1} is the
intermediate spin J_12 in {0, 1} of the first two link ends.

Symbols: j_e = spin of end e, role_e in {out, in}, n = quark occupation,
d_e = 2 j_e + 1, K = number of ends, K' = number of constituents.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .fermions import FOCK_BLOCK, Q_OPS
from .su2 import SIGMA, spin_matrices


def _kron_all(mats):
    out = np.array([[1.0 + 0j]])
    for m in mats:
        out = np.kron(out, m)
    return out


def _embed(op, dims, pos):
    mats = [np.eye(d, dtype=complex) for d in dims]
    mats[pos] = op
    return _kron_all(mats)


@lru_cache(maxsize=None)
def vertex_tensors(ends: tuple, n: int, static: bool = False):
    """
    ends  : tuple of (j, role) with role 'out' or 'in', canonical order
    n     : quark occupation 0, 1, 2
    static: whether a static spin-1/2 sits on the vertex

    Returns a tuple of real arrays T^(iota) of shape [d_1, ..., d_K, 4(, 2)]
    (matter index = full 4-dim Fock index, nonzero only in the occupation-n
    block), orthonormal, ordered by the fusion-tree label iota.
    """
    dims = [int(round(2 * j + 1)) for j, _ in ends] + [4] + ([2] if static else [])
    K = len(ends)
    # generators of each constituent, embedded in the local space
    gens = []  # list over constituents of [G_x, G_y, G_z]
    for e, (j, role) in enumerate(ends):
        J = spin_matrices(j)
        gens.append([_embed(-J[a].T if role == "out" else J[a], dims, e) for a in range(3)])
    gens.append([_embed(Q_OPS[a], dims, K) for a in range(3)])
    if static:
        gens.append([_embed(SIGMA[a] / 2, dims, K + 1) for a in range(3)])
    G = [sum(g[a] for g in gens) for a in range(3)]
    C = sum(g @ g for g in G)
    # restrict to the occupation-n block of the matter index
    block_idx = FOCK_BLOCK[n]
    full_dim = int(np.prod(dims))
    keep = np.zeros(full_dim, dtype=bool)
    idx = np.arange(full_dim).reshape(dims)
    for c in block_idx:
        keep[np.take(idx, c, axis=K).ravel()] = True
    sel = np.where(keep)[0]
    Cn = C[np.ix_(sel, sel)]
    assert np.abs(Cn.imag).max() < 1e-12, "sum_a G_a^2 should be real symmetric"
    w, v = np.linalg.eigh(Cn.real)
    kern = v[:, w < 1e-9]
    k = kern.shape[1]
    if k == 0:
        return tuple()
    if k > 1:
        # fusion-tree label: cumulative Casimirs over constituents in canonical order
        label_op = np.zeros_like(C)
        cum = [np.zeros_like(C) for _ in range(3)]
        Kp = len(gens)
        for kk in range(1, Kp + 1):
            for a in range(3):
                cum[a] = cum[a] + gens[kk - 1][a]
            if 2 <= kk <= Kp - 1:
                label_op = label_op + 7.0 ** (kk - 2) * sum(c @ c for c in cum)
        lab = kern.T @ label_op[np.ix_(sel, sel)].real @ kern
        lw, lv = np.linalg.eigh((lab + lab.T) / 2)
        assert np.min(np.diff(lw)) > 1e-6, f"fusion-tree label degenerate: {lw}"
        kern = kern @ lv
    tensors = []
    for c in range(k):
        vec = np.zeros(full_dim)
        vec[sel] = kern[:, c]
        # phase convention: largest-magnitude component positive
        p = np.argmax(np.abs(vec))
        if vec[p] < 0:
            vec = -vec
        tensors.append(vec.reshape(dims))
    return tuple(tensors)


def kernel_dim(ends: tuple, n: int, static: bool = False) -> int:
    return len(vertex_tensors(ends, n, static))
