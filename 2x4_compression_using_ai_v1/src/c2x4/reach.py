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


def synth_on(states: list, h: np.ndarray, k: int, theta: float, keep_states=None, stats=None) -> list:
    """The package's exact block synthesis (real gauge, `_block_rounds`, `_multiplexed_two_level`) for
    exp(-i theta h) on an explicit list of local strings `states` (h indexed like `states`), local qubit
    indices 0..k-1.  `keep_states` (subset, union of blocks) = the strings that must be acted on exactly;
    default all.  Every other string of the 2^k space is a don't-care."""
    h = np.asarray(h)
    states = [int(s) for s in states]
    pos = {s: i for i, s in enumerate(states)}
    A = np.abs(h) > 1e-12
    np.fill_diagonal(A, False)
    ncomp, lab = csg.connected_components(sp.csr_matrix(A), directed=False)
    if keep_states is None:
        touched = sorted(set(int(v) for v in lab))
    else:
        touched = sorted({int(lab[pos[int(s)]]) for s in keep_states})
    keep_idx = np.flatnonzero(np.isin(lab, touched))
    valid = np.array(sorted(states[i] for i in keep_idx), dtype=np.int64)
    if np.abs(np.diag(h)[keep_idx]).max(initial=0.0) > 1e-12:
        raise NotImplementedError("diagonal elements in a touched block")
    nontriv = [c for c in touched if (lab == c).sum() > 1]
    if not nontriv:
        return []
    f, Aop = _real_gauge(np.array(states), h)
    if np.abs(np.imag(np.asarray(Aop))).max() > 1e-11:
        raise NotImplementedError("no real gauge")
    pre, post = _gauge_gates(f, k)
    blocks = []
    for c in nontriv:
        idx = np.where(lab == c)[0]
        rounds = _block_rounds(np.real(Aop)[np.ix_(idx, idx)], theta)
        if rounds:
            blocks.append([[(states[idx[i]], states[idx[j]], V) for (i, j, V) in rd] for rd in rounds])
    out = []
    for step in range(max((len(b) for b in blocks), default=0)):
        by_diff = {}
        for b in blocks:
            if step < len(b):
                for (a, bb, V) in b[step]:
                    by_diff.setdefault(a ^ bb, []).append((a, bb, V))
        for d in sorted(by_diff):
            out += _multiplexed_two_level(d, by_diff[d], valid, k, stats=stats)
    return post + out + pre


# ------------------------------------------------------------------ approximate class (notes/004)
def exact_trajectory(P, ref: int, k: int) -> dict:
    """{term name: exact dressed-basis state before the term} for circuit (ref, k), complex128."""
    import scipy.sparse.linalg as spl
    th = None
    for twoB in (0, 2):
        if ref in P.refs[twoB]:
            th = P.theta(twoB, k)
    psi = np.zeros(P.M.basis.dim, dtype=complex)
    psi[ref] = 1.0
    out = {}
    for nm, H in zip(P.names, P.mats):
        out[nm] = psi.copy()
        psi = spl.expm_multiply(-1j * th * H, psi)
    out["_final"] = psi
    return out


def approx_contracts(P, ref: int, k: int, budget_total: float = 1e-8) -> dict:
    """Per term: the kept local strings (union of the kept blocks) and the bound 2 ||Pi_D phi|| of the dropped
    part, dropping blocks in increasing weight while 2 ||Pi_D phi|| <= budget_total / 13 (notes/004 4)."""
    traj = exact_trajectory(P, ref, k)
    cw = P.E.codewords
    names = P.names[1:]
    per = budget_total / len(names)
    out = {}
    for nm in names:
        sup, states, h, pos = P.local(nm)
        A = np.abs(h) > 1e-12
        np.fill_diagonal(A, False)
        _n, lab = csg.connected_components(sp.csr_matrix(A), directed=False)
        phi = traj[nm]
        nz = np.flatnonzero(np.abs(phi) > 0)
        w = (1 << np.arange(len(sup))).astype(np.int64)
        loc = (cw[nz][:, sup].astype(np.int64) * w).sum(axis=1)
        blk = np.array([lab[pos[int(s)]] for s in loc])
        weight = {}
        for b, a in zip(blk, np.abs(phi[nz]) ** 2):
            weight[int(b)] = weight.get(int(b), 0.0) + float(a)
        order = sorted(weight, key=lambda b: weight[b])
        cum, dropped = 0.0, set()
        for b in order:
            if 2.0 * np.sqrt(cum + weight[b]) <= per:
                cum += weight[b]
                dropped.add(b)
            else:
                break
        kept = [b for b in weight if b not in dropped]
        kept_states = sorted(int(states[i]) for i in np.flatnonzero(np.isin(lab, kept)))
        out[nm] = {"kept_states": kept_states, "n_blocks_touched": len(weight),
                   "n_blocks_dropped": len(dropped), "dropped_bound": 2.0 * float(np.sqrt(cum))}
    return out
