"""Exact minimum Walsh support of a multiplexor angle table with don't-care slots (planner step 2, notes/007 §5.3;
plan notes/010).  Label "MWS certificate" is mine.

Problem.  A uniformly controlled rotation on m (reduced) controls has the angle table theta(c), c in {0,1}^m, fixed
on the slots F (the occupied labels) and free elsewhere.  In walk form it costs one CNOT per step of a closed walk
from the empty mask through every mask S != 0 with a nonzero Walsh coefficient
    a_S = 2^-m sum_c (-1)^{|S & c|} theta(c)
(the empty mask is an uncontrolled rotation).  So the CNOT count of the walk is >= s + 1 when s >= 1 nonzero
non-empty masks remain (a closed walk through s distinct nonzero masks has s + 1 edges, each >= 1 CNOT).

MILP.  Free-slot angles y (|y_i| <= M_theta), a = a0 + K y with a0 = 2^-m W[:, F] theta_F and K = 2^-m W[:, free];
binary z_S (S != 0) with |a_S| <= M_S z_S, M_S = |a0_S| + ||K_S||_1 M_theta (valid for every y in the box);
minimise sum_S z_S.  HiGHS (scipy.optimize.milp).  The returned dual bound is a lower bound on the support of
every completion with free angles in [-M_theta, M_theta] (the class of the certificate; M_theta is recorded); the
primal solution's support is re-solved exactly by least squares on the fixed slots and accepted only at residual
<= 1e-12, which makes it a genuine upper bound.  certified_optimal := (upper bound == lower bound).

Floating point: HiGHS works in double precision with feasibility tolerance 1e-9; a near-feasible "solution" can
only make the reported minimum smaller, i.e. the lower bound is conservative up to HiGHS's own correctness, which is
not formally verified (stated in the report).
"""
from __future__ import annotations

import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .sparsemux import sparse_walsh, walsh_matrix

M_THETA = 8 * np.pi
EXACT_TOL = 1e-12


def _exact_on(W_fixed, b, support):
    if not support:
        r = float(np.abs(b).max()) if len(b) else 0.0
        return None, r
    As = W_fixed[:, support]
    x, *_ = np.linalg.lstsq(As, b, rcond=None)
    return x, float(np.abs(As @ x - b).max()) if len(b) else 0.0


def min_walsh_support(m: int, fidx, fval, M_theta: float = M_THETA, time_limit: float = 120.0) -> dict:
    """Certificate for one reduced table.  Returns lower bound (support_lb), the best exact support found
    (support_ub, its coefficient vector), status and timing.  Supports count non-empty masks only."""
    t0 = time.time()
    N = 1 << m
    fidx = np.asarray(fidx, dtype=int)
    fval = np.asarray(fval, dtype=float)
    W = walsh_matrix(m)
    free = np.setdiff1d(np.arange(N), fidx)
    Wf = W[fidx]
    if len(free) == 0:
        a = (W.T @ _embed(N, fidx, fval)) / N
        sup = [int(S) for S in np.flatnonzero(np.abs(a) > 1e-13) if S != 0]
        return {"m": m, "n_fixed": int(len(fidx)), "n_free": 0, "support_lb": len(sup), "support_ub": len(sup),
                "a": a, "status": "no free slots: Walsh transform is unique", "certified_optimal": True,
                "M_theta": None, "wall_s": time.time() - t0}
    a0 = (W[:, fidx] @ fval) / N
    K = W[:, free] / N
    nS = N - 1                                     # masks 1..N-1
    nf = len(free)
    Ms = np.abs(a0[1:]) + np.abs(K[1:]).sum(axis=1) * M_theta
    # variables: [y (nf), z (nS)]
    c = np.concatenate([np.zeros(nf), np.ones(nS)])
    A_up = np.hstack([K[1:], -np.diag(Ms)])        #  a0 + K y - M z <= 0
    A_lo = np.hstack([-K[1:], -np.diag(Ms)])       # -a0 - K y - M z <= 0
    cons = [LinearConstraint(A_up, -np.inf, -a0[1:]), LinearConstraint(A_lo, -np.inf, a0[1:])]
    integrality = np.concatenate([np.zeros(nf), np.ones(nS)])
    bounds = Bounds(np.concatenate([-M_theta * np.ones(nf), np.zeros(nS)]),
                    np.concatenate([M_theta * np.ones(nf), np.ones(nS)]))
    # warm upper bound from the LP heuristic (for reporting only; HiGHS has no warm start in scipy)
    try:
        a_lp, sup_lp = sparse_walsh(m, fidx, fval)
        lp_support = int(sum(1 for S in sup_lp if S != 0 and abs(a_lp[S]) > 1e-15))
    except RuntimeError:
        a_lp, lp_support = None, None
    res = milp(c, constraints=cons, integrality=integrality, bounds=bounds,
               options={"time_limit": time_limit, "mip_rel_gap": 0.0, "disp": False})
    lb = None
    ub_support, a_best = None, None
    if res.x is not None:
        z = res.x[nf:] > 0.5
        cand = [int(S) + 1 for S in np.flatnonzero(z)]
        x, r = _exact_on(Wf, fval, [0] + cand)
        if r <= EXACT_TOL:
            a_best = np.zeros(N)
            a_best[[0] + cand] = x
            ub_support = int(sum(1 for S in cand if abs(a_best[S]) > 1e-15))
    dual = getattr(res, "mip_dual_bound", None)
    if dual is not None and np.isfinite(dual):
        lb = int(np.ceil(dual - 1e-6))
    elif res.status == 0 and res.fun is not None:
        lb = int(round(res.fun))
    if lp_support is not None and (ub_support is None or lp_support < ub_support):
        ub_support, a_best = lp_support, a_lp
    status = {0: "optimal", 1: "time or iteration limit", 2: "infeasible", 3: "unbounded", 4: "other"}.get(
        res.status, str(res.status))
    return {"m": m, "n_fixed": int(len(fidx)), "n_free": int(nf), "support_lb": lb, "support_ub": ub_support,
            "lp_support": lp_support, "a": a_best, "status": f"MILP {status}",
            "certified_optimal": bool(lb is not None and ub_support is not None and lb == ub_support),
            "M_theta": M_theta, "wall_s": time.time() - t0}


def _embed(N, idx, val):
    v = np.zeros(N)
    v[idx] = val
    return v


def cached_min_walsh_support(m: int, fidx, fval, time_limit: float = 60.0, M_theta: float = M_THETA) -> dict:
    """min_walsh_support memoised on disk (data/cache/milp/<sha256 of the table>.json; the tables are theta-free in
    the linear synthesis, so one solve serves every k)."""
    import hashlib
    import json
    import os
    from .env import CACHE
    fidx = np.asarray(fidx, dtype=np.int64)
    fval = np.asarray(fval, dtype=np.float64)
    key = hashlib.sha256(np.int64(m).tobytes() + fidx.tobytes() + fval.tobytes() +
                         np.float64(time_limit).tobytes() + np.float64(M_theta).tobytes()).hexdigest()
    d = os.path.join(CACHE, "milp")
    p = os.path.join(d, key + ".json")
    if p in _MEMO:
        return _MEMO[p]
    if os.path.exists(p):
        with open(p) as fh:
            r = json.load(fh)
        r["a"] = None if r["a"] is None else np.array(r["a"])
        _MEMO[p] = r
        return r
    r = min_walsh_support(m, fidx, fval, M_theta=M_theta, time_limit=time_limit)
    os.makedirs(d, exist_ok=True)
    out = dict(r)
    out["a"] = None if r["a"] is None else [float(v) for v in r["a"]]
    with open(p, "w") as fh:
        json.dump(out, fh)
    _MEMO[p] = r
    return r


_MEMO = {}


def milp_walsh(m: int, fidx, fval, time_limit: float = 60.0):
    """Drop-in for sparsemux.sparse_walsh in "milp" mode: the minimum-support exact solution when the MILP finds a
    smaller one than the LP heuristic, else the heuristic's.  Returns (a, support indices incl. 0 if used)."""
    r = cached_min_walsh_support(m, fidx, fval, time_limit=time_limit)
    a = r["a"]
    if a is None:
        raise RuntimeError("no exact Walsh solution")
    sup = np.flatnonzero(np.abs(a) > 1e-15)
    return a, sup
