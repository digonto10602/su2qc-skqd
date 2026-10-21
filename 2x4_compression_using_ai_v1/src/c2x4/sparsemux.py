"""Sparse-Walsh synthesis of a uniformly controlled rotation with don't-care slots (family F4, label SW, mine).

A uniformly controlled y rotation sum_c |c><c| (x) Ry(theta_c) equals prod_S exp(-i a_S Z_S Y_t / 2) whenever
theta_c = sum_S a_S (-1)^{|S & c|} (the generators commute; Walsh expansion).  Each factor is
CX_S Ry(a_S) CX_S with CX_S the CNOTs from the controls in S to the target, and consecutive factors share
CNOTs, so the cost is the length of a closed walk through the masks S (Hamming metric), starting and ending
at the empty set.  The Gray-code chain of the package is the special case 'all 2^m masks', 2^m CNOTs.

Here the slots that are never occupied are free: we look for the angle table that agrees with the required
angles on the fixed slots and has the fewest nonzero Walsh coefficients (L1-minimisation by linear
programming, then greedy pruning, then an exact least-squares re-solve on the chosen support; a support is
accepted only if it reproduces every fixed angle to 1e-12).

The table construction (target choice, compression CNOTs, which slots are fixed or free) is the package's
`circuits_ir._multiplexed_two_level`, re-done here because that function does not return its free slots.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

from . import env  # noqa: F401
from skqd.circuits_ir import (_FLIP2, _I2, _axis_angle, _basis_change_to_y, _multiplexed_two_level,  # noqa: E402
                              _pack, _phase_su2)


SOLVER = {"mode": "lp"}          # "lp": L1 + greedy pruning (it3-it5); "milp": exact minimum support (certify.py)


def walsh_matrix(m: int) -> np.ndarray:
    c = np.arange(1 << m)
    S = np.arange(1 << m)
    pc = np.vectorize(lambda v: bin(v).count("1"))
    return (-1.0) ** pc(c[:, None] & S[None, :])


def sparse_walsh(m: int, fixed_idx: np.ndarray, fixed_val: np.ndarray, tol: float = 1e-12,
                 prune_max: int = 64):
    """Few-term Walsh coefficients a (length 2^m) with W[fixed] a = fixed_val exactly; returns (a, support)."""
    N = 1 << m
    W = walsh_matrix(m)
    A = W[fixed_idx]
    b = np.asarray(fixed_val, dtype=float)
    if len(fixed_idx) == N:
        a = (W.T @ _full(N, fixed_idx, b)) / N
        sup = np.flatnonzero(np.abs(a) > 1e-13)
        return a, sup
    # L1 minimisation: a = u - v, u, v >= 0
    c = np.ones(2 * N)
    res = linprog(c, A_eq=np.hstack([A, -A]), b_eq=b, bounds=(0, None), method="highs")
    if res.status != 0:
        raise RuntimeError(f"linprog failed: {res.message}")
    a = res.x[:N] - res.x[N:]
    sup = list(np.flatnonzero(np.abs(a) > 1e-10))

    def solve_on(support):
        if not support:
            return None, np.inf
        As = A[:, support]
        x, *_ = np.linalg.lstsq(As, b, rcond=None)
        r = float(np.abs(As @ x - b).max()) if len(b) else 0.0
        return x, r

    x, r = solve_on(sup)
    if r > tol:
        # the LP support itself is not exactly consistent (numerics): fall back to the full spectrum
        sup = list(range(N))
        x, r = solve_on(sup)
        if r > tol:
            raise RuntimeError("no exact Walsh solution")
    # greedy pruning: drop the smallest coefficient while an exact solution remains
    improved = len(sup) <= prune_max
    while improved and len(sup) > 1:
        improved = False
        for j in np.argsort(np.abs(x)):
            trial = [s for i, s in enumerate(sup) if i != j]
            xt, rt = solve_on(trial)
            if rt <= tol:
                sup, x = trial, xt
                improved = True
                break
    a = np.zeros(N)
    a[sup] = x
    return a, np.array(sup, dtype=int)


def _full(N, idx, val):
    v = np.zeros(N)
    v[idx] = val
    return v


def mask_walk(masks: list) -> list:
    """Order the masks to shorten the closed walk from and back to 0 (nearest neighbour + 2-opt)."""
    rem = [int(s) for s in masks]
    cur, order = 0, []
    while rem:
        j = min(range(len(rem)), key=lambda i: (bin(rem[i] ^ cur).count("1"), rem[i]))
        cur = rem.pop(j)
        order.append(cur)

    def cost(o):
        path = [0] + o + [0]
        return sum(bin(path[i] ^ path[i + 1]).count("1") for i in range(len(path) - 1))

    best = cost(order)
    improved = True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                o2 = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                c2 = cost(o2)
                if c2 < best:
                    order, best, improved = o2, c2, True
    return order


def walk_cost(order: list) -> int:
    path = [0] + order + [0]
    return sum(bin(path[i] ^ path[i + 1]).count("1") for i in range(len(path) - 1))


def sw_two_level(diff: int, items: list, valid, k: int, stats=None, prune_max: int = 64) -> list:
    """Drop-in replacement of `_multiplexed_two_level`: the package's target choice, compression CNOTs and
    control reduction (invariance directions with don't-cares, `_reduce_controls`), then the reduced angle
    table is synthesised by the sparse-Walsh parity walk instead of the full Gray-code chain.  Falls back to
    the package function when the slot unitaries do not share one rotation axis."""
    from skqd.circuits_ir import _frame_cnot, _reduce_controls
    valid = np.asarray(valid, dtype=np.int64)
    bits = [q for q in range(k) if (diff >> q) & 1]
    best = None
    for t in bits[:3]:
        rest = diff ^ (1 << t)
        N = 1 << (k - 1)
        mats = np.tile(_I2, (N, 1, 1))
        free = np.ones(N, dtype=bool)
        for (a, b, V) in items:
            za = a ^ rest if (a >> t) & 1 else a
            zb = b ^ rest if (b >> t) & 1 else b
            V = np.asarray(V, dtype=complex)
            if (za >> t) & 1:
                za, zb = zb, za
                V = _FLIP2 @ V @ _FLIP2
            slot = _pack(za, t)
            mats[slot] = V
            free[slot] = False
        sl = np.arange(N)
        z0 = (sl & ((1 << t) - 1)) | ((sl >> t) << (t + 1))
        z1 = z0 | (1 << t)
        s0 = np.where((z0 >> t) & 1, z0 ^ rest, z0)
        s1 = np.where((z1 >> t) & 1, z1 ^ rest, z1)
        free &= ~(np.isin(s0, valid) | np.isin(s1, valid))
        ctrl = [q for q in range(k) if q != t]
        m = k - 1
        basis, _m2, _f2 = _reduce_controls(mats, free, m)
        frame = []
        for w in basis:
            pv = w.bit_length() - 1
            for q in range(m):
                if q != pv and ((w >> q) & 1):
                    frame.append((ctrl[pv], ctrl[q]))
        pivots = [w.bit_length() - 1 for w in basis]
        keep = [i for i in range(m) if i not in pivots]
        # apply the frame to the ORIGINAL table and fixed mask, then reduce: a reduced slot is fixed if any
        # slot of its coset (all values of the pivot bits) is fixed
        mt, ft = mats.copy(), free.copy()
        for (a_, b_) in frame:
            mt, ft = _frame_cnot(mt, ft, ctrl.index(a_), ctrl.index(b_))
        fixed_full = ~ft
        mr = len(keep)
        keep_val = np.zeros(N, dtype=np.int64)
        for bit, q in enumerate(keep):
            keep_val |= ((np.arange(N) >> q) & 1) << bit
        # angles on fixed slots
        ref, ang_full, ok = None, np.zeros(N), True
        for i in np.flatnonzero(fixed_full):
            d, Wm = _phase_su2(mt[i])
            if abs(d) > 1e-13:
                ok = False
                break
            nvec, ang = _axis_angle(Wm)
            if abs(ang) < 1e-13:
                ang_full[i] = 2 * np.pi if np.real(Wm[0, 0]) < 0 else 0.0
                continue
            if ref is None:
                ref = nvec
            if np.linalg.norm(nvec - ref) < 1e-8:
                ang_full[i] = ang
            elif np.linalg.norm(nvec + ref) < 1e-8:
                ang_full[i] = -ang
            else:
                ok = False
                break
        if not ok or ref is None:
            continue
        red_fixed = np.zeros(1 << mr, dtype=bool)
        red_val = np.zeros(1 << mr)
        consistent = True
        for i in np.flatnonzero(fixed_full):
            r = keep_val[i]
            if red_fixed[r] and abs(red_val[r] - ang_full[i]) > 1e-9:
                consistent = False
                break
            red_fixed[r] = True
            red_val[r] = ang_full[i]
        if not consistent:
            continue
        fidx = np.flatnonzero(red_fixed)
        try:
            if SOLVER["mode"] == "milp":
                from .certify import milp_walsh
                a, sup = milp_walsh(mr, fidx, red_val[fidx])
            else:
                a, sup = sparse_walsh(mr, fidx, red_val[fidx], prune_max=prune_max)
        except RuntimeError:
            continue
        masks = [int(S) for S in sup if S != 0 and abs(a[S]) > 1e-15]
        order = mask_walk(masks)
        cost = walk_cost(order) + 2 * len(frame) + 2 * (len(bits) - 1)
        if best is None or cost < best[0]:
            best = (cost, t, rest, [ctrl[q] for q in keep], a, order, ref, frame, (mr, fidx, red_val[fidx]))
    if best is None:
        return _multiplexed_two_level(diff, items, valid, k, stats=stats)
    cost, t, rest, ctrl_r, a, order, ref, frame, reduced = best
    B = _basis_change_to_y(ref)
    gates = [("unitary", [t], B)]
    if abs(a[0]) > 1e-15:
        gates.append(("ry", [t], float(a[0])))
    cur = 0
    for S in order:
        for i in range(len(ctrl_r)):
            if ((S ^ cur) >> i) & 1:
                gates.append(("cx", [ctrl_r[i], t], None))
        cur = S
        gates.append(("ry", [t], float(a[S])))
    for i in range(len(ctrl_r)):
        if (cur >> i) & 1:
            gates.append(("cx", [ctrl_r[i], t], None))
    gates.append(("unitary", [t], B.conj().T))
    comp = [("cx", [t, q], None) for q in range(k) if (rest >> q) & 1]
    fr = [("cx", [a_, b_], None) for a_, b_ in frame]
    if stats is not None:
        stats.append({"flip_pattern": int(diff), "target": int(t), "n_controls": len(ctrl_r),
                      "n_terms": len(order) + 1, "walk_cnots": walk_cost(order), "frame_cnots": len(frame),
                      "n_rotations": len(items), "support_used": len(order),
                      "reduced_table": {"m": int(reduced[0]), "fixed_idx": [int(v) for v in reduced[1]],
                                        "fixed_val": [float(v) for v in reduced[2]]}})
    return comp + fr + gates + fr[::-1] + comp


import contextlib


@contextlib.contextmanager
def use_sparse_mux():
    """Temporarily route the study's constructions (plaqfactor, reach) through `sw_two_level`."""
    from . import plaqfactor, reach
    old = (plaqfactor._multiplexed_two_level, reach._multiplexed_two_level)
    plaqfactor._multiplexed_two_level = sw_two_level
    reach._multiplexed_two_level = sw_two_level
    try:
        yield
    finally:
        plaqfactor._multiplexed_two_level, reach._multiplexed_two_level = old
