"""Reachable sets and term synthesis restricted to them (family F1, input-specific exact class).

Structural support.  The circuit starts on ONE codeword (the reference) and applies the term groups in the
package order.  exp(-i theta H_gamma) maps a basis state only inside its connected component of the graph of
H_gamma (any analytic function of H_gamma is block diagonal on those components), so the set S_gamma of
codewords that can carry amplitude before term gamma is the union of the components of earlier terms reached
from the reference -- an exact UPPER bound, independent of theta (the numerical support is a subset).

Restriction.  Term gamma acts as W (x) 1_env on its support.  If the local circuit W equals exp(-i theta h)
on every local string of the touched blocks B_gamma (the blocks of h containing the local part of some
c in S_gamma), then W (x) 1 equals the exact term on span(S_gamma), and the result lies in span(S_{gamma+1}).
By induction over the terms (Lean: Compress2x4.Reach) the whole circuit equals the exact coarse step on the
reference input.  Every other local codeword is a don't-care for the synthesis.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as csg

from . import env  # noqa: F401
from skqd.circuits_ir import (_block_rounds, _gauge_gates, _multiplexed_two_level,   # noqa: E402
                              _real_gauge)


def components(H) -> np.ndarray:
    A = (abs(sp.csr_matrix(H)) > 1e-12).astype(np.int8).tocsr()
    A.setdiag(0)
    A.eliminate_zeros()
    _n, lab = csg.connected_components(A, directed=False)
    return lab


class Reach:
    """Structural supports of every term for every reference (cached on the Problem)."""

    def __init__(self, P):
        self.P = P
        self.labs = [components(H) for H in P.mats]
        self.cw = P.E.codewords
        self._cache = {}

    def before(self, ref: int) -> dict:
        """{term name: sorted global basis indices that can carry amplitude before the term}."""
        if ref in self._cache:
            return self._cache[ref]
        struct = np.zeros(self.P.M.basis.dim, dtype=bool)
        struct[ref] = True
        out = {}
        for nm, lab in zip(self.P.names, self.labs):
            idx = np.flatnonzero(struct)
            out[nm] = idx
            struct = np.isin(lab, np.unique(lab[idx]))
        out["_final"] = np.flatnonzero(struct)
        self._cache[ref] = out
        return out

    def local_reachable(self, ref: int, name: str) -> list:
        sup = self.P.support(name)
        idx = self.before(ref)[name]
        w = (1 << np.arange(len(sup))).astype(np.int64)
        loc = (self.cw[idx][:, sup].astype(np.int64) * w).sum(axis=1)
        return sorted(int(v) for v in np.unique(loc))


def restricted_term_gates(P, name: str, theta: float, reach_local: list, stats=None) -> list:
    """`circuits_ir.structured_term_gates` (exact mode) restricted to the blocks touched by `reach_local`:
    only those blocks are synthesised and only their strings are 'valid' (must be acted on correctly);
    every other local string is a don't-care for the control minimisation."""
    sup, states, h, pos = P.local(name)
    k = len(sup)
    A = np.abs(h) > 1e-12
    np.fill_diagonal(A, False)
    ncomp, lab = csg.connected_components(sp.csr_matrix(A), directed=False)
    touched = sorted({int(lab[pos[s]]) for s in reach_local})
    keep_idx = np.flatnonzero(np.isin(lab, touched))
    valid = np.array(sorted(int(states[i]) for i in keep_idx), dtype=np.int64)
    if np.abs(np.diag(h)[keep_idx]).max(initial=0.0) > 1e-12:
        raise NotImplementedError("diagonal elements in a touched block")
    nontriv = [c for c in touched if (lab == c).sum() > 1]
    if not nontriv:
        return []                                      # identity on every reachable string
    f, Aop = _real_gauge(states, h)
    if np.abs(np.imag(np.asarray(Aop))).max() > 1e-11:
        raise NotImplementedError("no real gauge")
    pre, post = _gauge_gates(f, k)
    blocks = []
    for c in nontriv:
        idx = np.where(lab == c)[0]
        rounds = _block_rounds(np.real(Aop)[np.ix_(idx, idx)], theta)
        if rounds:
            blocks.append([[(int(states[idx[i]]), int(states[idx[j]]), V) for (i, j, V) in rd]
                           for rd in rounds])
    out = []
    for step in range(max((len(b) for b in blocks), default=0)):
        by_diff = {}
        for b in blocks:
            if step < len(b):
                for (a, bb, V) in b[step]:
                    by_diff.setdefault(a ^ bb, []).append((a, bb, V))
        for d in sorted(by_diff):
            out += _multiplexed_two_level(d, by_diff[d], valid, k, stats=stats)
    out = post + out + pre
    return [(nm, [sup[q] for q in qs], par) for nm, qs, par in out]


def contract_states(P, name: str, reach_local: list) -> list:
    """The input contract of a restricted term: every local string of the blocks touched by the
    reachable local states (the term must act exactly on all of them)."""
    sup, states, h, pos = P.local(name)
    A = np.abs(h) > 1e-12
    np.fill_diagonal(A, False)
    _n, lab = csg.connected_components(sp.csr_matrix(A), directed=False)
    touched = {int(lab[pos[s]]) for s in reach_local}
    return sorted(int(states[i]) for i in np.flatnonzero(np.isin(lab, sorted(touched))))
