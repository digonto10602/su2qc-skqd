"""Angle-linear multiplexor synthesis (label "LIN", mine; C4 step 6 of notes/007 §6, plan notes/010).

Why.  In it3-it5 every theta-dependent rotation reached the sparse-Walsh synthesis as a 2x2 UNITARY at the circuit's
own angle, and the structural decisions (control reduction by numerical equality of slot unitaries, the axis
orientation, zero tests) were taken on those unitaries.  A few of them changed with theta, so the two-qubit count
of a (reference, term) varied by up to 4 across k (data/eval_arch_it5_*_pp_all75_pruned.json; gate Q0P's Q2 wants
it equal).  Here a theta-dependent two-level op is carried as its GENERATOR: LinRot(G, theta) means exp(-i theta G)
with G a fixed 2x2 traceless Hermitian matrix.  All decisions (target, control reduction, Walsh support, walk order)
are taken on the theta-free coefficient table c(slot) with slot unitary R_n(theta c) = exp(-i theta c n.sigma / 2);
only the emitted angles are multiplied by theta.  So the gate skeleton (names and qubits) is identical for every k
by construction, and the angle table is exactly linear in theta (no wrap at 2 pi).

Block rounds.  `lin_block_rounds` is the package's bipartite SVD construction (`circuits_ir._block_rounds`):
exp(theta A) = Bas . [pair rotations exp(theta [[0, s_i], [-s_i, 0]])] . Bas^T with Bas theta-independent; the pair
rotations are returned as LinRot(-s_i sigma_y, theta) (exp(theta [[0,s],[-s,0]]) = exp(-i theta (-s sigma_y))), the
basis changes as constant unitaries (theta-free already).  Non-bipartite blocks are refused (NotImplementedError)
instead of falling back to a theta-dependent generic decomposition.
"""
from __future__ import annotations

import contextlib

import numpy as np

from . import env  # noqa: F401
from skqd.circuits_ir import (_FLIP2, _basis_change_to_y, _bipartition, _frame_cnot, _generic_two_level,   # noqa: E402
                              _pack, _reduce_controls)
from .sparsemux import SOLVER, mask_walk, sparse_walsh, sw_two_level, walk_cost

_SX = np.array([[0, 1], [1, 0]], dtype=complex)
_SY = np.array([[0, -1j], [1j, 0]], dtype=complex)
_SZ = np.array([[1, 0], [0, -1]], dtype=complex)


CONJ = {"q": None}     # local index of a sign-parity qubit p: every theta-multiplexor is conjugated by CZ(p, t)


class LinRot:
    """exp(-i theta G), G a 2x2 traceless Hermitian generator (theta-free); acts in the basis (a, b) of its item."""
    __slots__ = ("G", "theta", "const")

    def __init__(self, G, theta: float, const: bool = False):
        self.G = np.asarray(G, dtype=complex)
        self.theta = float(theta)
        self.const = bool(const)

    def unitary(self) -> np.ndarray:
        n = self.pauli()
        g = float(np.linalg.norm(n))
        if g == 0.0:
            return np.eye(2, dtype=complex)
        A = (n[0] * _SX + n[1] * _SY + n[2] * _SZ) / g
        return np.cos(self.theta * g) * np.eye(2) - 1j * np.sin(self.theta * g) * A

    def pauli(self) -> np.ndarray:
        G = self.G
        return np.array([float(np.real(G[0, 1])), float(np.imag(G[1, 0])), float(np.real(G[0, 0]))])

    def flipped(self) -> "LinRot":
        return LinRot(_FLIP2 @ self.G @ _FLIP2, self.theta, self.const)


def lin_block_rounds(A, theta, fallback=None):
    """Drop-in for circuits_ir._block_rounds returning LinRot for the theta-dependent pair rotations."""
    n = A.shape[0]
    if n == 1:
        assert abs(A[0, 0]) < 1e-12, "isolated configuration with a diagonal element"
        return []
    Adj = np.abs(A) > 1e-12
    np.fill_diagonal(Adj, False)
    col = _bipartition(Adj)
    if col is None or np.abs(np.diag(A)).max() > 1e-12:
        raise NotImplementedError("non-bipartite block: no angle-linear decomposition")
    if fallback is not None:
        fallback.append(False)
    ia = [i for i in range(n) if col[i] == 0]
    ib = [i for i in range(n) if col[i] == 1]
    K = np.real(A[np.ix_(ia, ib)])
    U, S, Vt = np.linalg.svd(K)
    V = Vt.T.copy()
    U = U.copy()
    for X in (U, V):
        for i in range(X.shape[1]):
            j = int(np.argmax(np.abs(X[:, i])))
            X[:, i] = X[:, i] * np.sign(X[j, i])
        d = np.linalg.det(X)
        if abs(d - 1) > 1e-9:
            X[:, -1] = X[:, -1] * d
    opsU = _generic_two_level(U.T.astype(complex))
    opsV = _generic_two_level(V.T.astype(complex))
    rounds = []
    for r in range(max(len(opsU), len(opsV))):
        rd = []
        if r < len(opsU):
            i, j, W = opsU[r]
            rd.append((ia[i], ia[j], W))
        if r < len(opsV):
            i, j, W = opsV[r]
            rd.append((ib[i], ib[j], W))
        rounds.append(rd)
    D = U.T @ K @ V                                   # the gauge fix above may flip signs: D_ii = +-S_i
    off = D.copy()
    for i in range(min(D.shape)):
        off[i, i] = 0.0
    if np.abs(off).max(initial=0.0) > 1e-10:
        raise AssertionError("singular-value blocks are not decoupled")
    rd = []
    for i in range(min(len(ia), len(ib))):
        if abs(D[i, i]) > 1e-14:
            rd.append((ia[i], ib[i], LinRot(-D[i, i] * _SY, theta)))
    if rd:
        rounds.append(rd)
    invU = [(i, j, W.conj().T) for (i, j, W) in reversed(opsU)]
    invV = [(i, j, W.conj().T) for (i, j, W) in reversed(opsV)]
    for r in range(max(len(invU), len(invV))):
        rd = []
        if r < len(invU):
            i, j, W = invU[r]
            rd.append((ia[i], ia[j], W))
        if r < len(invV):
            i, j, W = invV[r]
            rd.append((ib[i], ib[j], W))
        rounds.append(rd)
    return rounds


def _solve_table(coef, free, ctrl, prune_max=64):
    """Control reduction + sparse Walsh (LP or MILP) + walk for one theta-free coefficient table over `ctrl`
    (slot bit i = ctrl[i]).  Returns None or (walk+frame cost, keep ctrl qubits, frame pairs, a, order, reduced)."""
    m = len(ctrl)
    N = 1 << m
    basis, _c2, _f2 = _reduce_controls(coef[:, None, None], free, m)
    frame = []
    for w in basis:
        pv = w.bit_length() - 1
        for q in range(m):
            if q != pv and ((w >> q) & 1):
                frame.append((ctrl[pv], ctrl[q]))
    pivots = [w.bit_length() - 1 for w in basis]
    keep = [i for i in range(m) if i not in pivots]
    ct, ft = coef[:, None, None].copy(), free.copy()
    for (a_, b_) in frame:
        ct, ft = _frame_cnot(ct, ft, ctrl.index(a_), ctrl.index(b_))
    ct = ct[:, 0, 0]
    fixed_full = ~ft
    mr = len(keep)
    keep_val = np.zeros(N, dtype=np.int64)
    for bit, q in enumerate(keep):
        keep_val |= ((np.arange(N) >> q) & 1) << bit
    red_fixed = np.zeros(1 << mr, dtype=bool)
    red_val = np.zeros(1 << mr)
    for i in np.flatnonzero(fixed_full):
        r = keep_val[i]
        if red_fixed[r] and abs(red_val[r] - ct[i]) > 1e-9:
            return None
        red_fixed[r] = True
        red_val[r] = ct[i]
    fidx = np.flatnonzero(red_fixed)
    try:
        if SOLVER["mode"] == "milp":
            from .certify import milp_walsh
            a, sup = milp_walsh(mr, fidx, red_val[fidx])
        else:
            a, sup = sparse_walsh(mr, fidx, red_val[fidx], prune_max=prune_max)
    except RuntimeError:
        return None
    masks = [int(S) for S in sup if S != 0 and abs(a[S]) > 1e-15]
    order = mask_walk(masks)
    return (walk_cost(order) + 2 * len(frame), [ctrl[q] for q in keep], frame, a, order, (mr, fidx, red_val[fidx]))


def _flag_variants(coef, free, ctrl, aq, max_lits=3, top=4):
    """Candidate dark/type flags (label FLG, mine): g = AND of 2..max_lits literals over the control bits, equal to 1
    on every slot with a nonzero coefficient; the flag is written into the clean ancilla aq (a control bit that is 0 on
    every occupied slot) so the nonzero entries move to the aq = 1 half, where the zero-coefficient slots no longer
    constrain the table.  Returns [(literals, coef', free', flag 2q cost both ways)]."""
    import itertools
    if aq not in ctrl:
        return []
    ai = ctrl.index(aq)
    fixed = np.flatnonzero(~free)
    if np.any((fixed >> ai) & 1):
        return []
    nz = fixed[np.abs(coef[fixed]) > 1e-12]
    z0 = fixed[np.abs(coef[fixed]) <= 1e-12]
    if len(nz) == 0 or len(z0) == 0:
        return []
    lits = []
    for p in range(len(ctrl)):
        if p == ai:
            continue
        v = (nz >> p) & 1
        if np.all(v == v[0]):
            lits.append((p, int(v[0])))
    cands = []
    for r in range(2, max_lits + 1):
        for sub in itertools.combinations(lits, r):
            g0 = np.ones(len(z0), dtype=bool)
            for p, v in sub:
                g0 &= ((z0 >> p) & 1) == v
            cands.append((int((~g0).sum()), -r, sub))
    cands.sort(reverse=True)
    out = []
    for score, _r, sub in cands[:top]:
        g = np.ones(len(fixed), dtype=bool)
        for p, v in sub:
            g &= ((fixed >> p) & 1) == v
        c2 = np.zeros_like(coef)
        f2 = np.ones_like(free)
        new = fixed | (g.astype(np.int64) << ai)
        c2[new] = coef[fixed]
        f2[new] = False
        out.append(([(ctrl[p], v) for p, v in sub], c2, f2, 6 if len(sub) == 2 else 12))
    return out


def _flag_gates(lits, aq):
    """Relative-phase AND of the literals into aq (Margolus 3-CX Toffoli for 2 literals, the 6-CX RC3X of
    Maslov 2016 / qiskit RC3XGate for 3): Toffoli times a diagonal phase on (literals, aq); used only as
    compute ... uncompute around a multiplexor that is diagonal on its controls, where the phase cancels
    (Lean Compress2x4.relphase_cancel)."""
    neg = [("x", [q], None) for q, v in lits if v == 0]
    qs = [q for q, _v in lits]
    T, Td = np.pi / 4, -np.pi / 4
    if len(qs) == 2:
        c1, c2 = qs
        core = [("h", [aq], None), ("p", [aq], T), ("cx", [c2, aq], None), ("p", [aq], Td), ("cx", [c1, aq], None),
                ("p", [aq], T), ("cx", [c2, aq], None), ("p", [aq], Td), ("h", [aq], None)]
    else:
        c1, c2, c3 = qs
        core = [("h", [aq], None), ("p", [aq], T), ("cx", [c3, aq], None), ("p", [aq], Td), ("h", [aq], None),
                ("cx", [c1, aq], None), ("p", [aq], T), ("cx", [c2, aq], None), ("p", [aq], Td),
                ("cx", [c1, aq], None), ("p", [aq], T), ("cx", [c2, aq], None), ("p", [aq], Td),
                ("h", [aq], None), ("p", [aq], T), ("cx", [c3, aq], None), ("p", [aq], Td), ("h", [aq], None)]
    return neg + core + neg


def lin_two_level(diff: int, items: list, valid, k: int, stats=None, prune_max: int = 64) -> list:
    """Multiplexed two-level step for LinRot items (all with one theta): the package's target choice and compression
    CNOTs, control reduction on the theta-free coefficient table, sparse Walsh (LP or MILP) on it, walk of Ry(theta a_S)
    conjugated by the theta-free basis change to the common axis.  With FLAG["q"] set (a clean ancilla of the
    register), flagged variants of the table are tried as well (`_flag_variants`)."""
    from .plaqfactor import invert
    valid = np.asarray(valid, dtype=np.int64)
    theta = items[0][2].theta
    const = items[0][2].const
    if any(abs(L.theta - theta) > 0 or L.const != const for _a, _b, L in items):
        raise ValueError("LinRot items with different theta in one multiplexor")
    bits = [q for q in range(k) if (diff >> q) & 1]
    best = None
    for t in bits[:3]:
        rest = diff ^ (1 << t)
        N = 1 << (k - 1)
        coef = np.zeros(N)
        free = np.ones(N, dtype=bool)
        axis, ok = None, True
        for (a, b, L) in items:
            za = a ^ rest if (a >> t) & 1 else a
            zb = b ^ rest if (b >> t) & 1 else b
            assert za ^ zb == (1 << t), "flip pattern does not compress to one qubit"
            if (za >> t) & 1:
                za, zb = zb, za
                L = L.flipped()
            nvec = L.pauli()
            g = float(np.linalg.norm(nvec))
            slot = _pack(za, t)
            free[slot] = False
            if g == 0.0:
                coef[slot] = 0.0
                continue
            if axis is None:
                axis = nvec / g
            dp = float(np.dot(nvec, axis)) / g
            if abs(abs(dp) - 1.0) > 1e-9:
                ok = False
                break
            coef[slot] = 2.0 * g * np.sign(dp)
        if not ok or axis is None:
            continue
        sl = np.arange(N)
        z0 = (sl & ((1 << t) - 1)) | ((sl >> t) << (t + 1))
        z1 = z0 | (1 << t)
        s0 = np.where((z0 >> t) & 1, z0 ^ rest, z0)
        s1 = np.where((z1 >> t) & 1, z1 ^ rest, z1)
        free &= ~(np.isin(s0, valid) | np.isin(s1, valid))
        ctrl = [q for q in range(k) if q != t]
        variants = [(None, coef, free, 0)]
        if FLAG["q"] is not None and FLAG["q"] != t:
            variants += _flag_variants(coef, free, ctrl, FLAG["q"])
        for lits, cf, fr_, fcost in variants:
            r = _solve_table(cf, fr_, ctrl, prune_max)
            if r is None:
                continue
            cost = r[0] + fcost + 2 * (len(bits) - 1)
            if best is None or cost < best[0]:
                best = (cost, t, rest, r[1], r[3], r[4], axis, r[2], r[5], lits)
    if best is None:
        raise NotImplementedError("no common rotation axis for the LinRot items of one multiplexor")
    cost, t, rest, ctrl_r, a, order, axis, frame, reduced, lits = best
    B = _basis_change_to_y(axis)
    gates = [("unitary", [t], B)]
    cq = None if const else CONJ["q"]
    if cq is not None:                   # conditional sign flip of every angle (JW conjugation, hopframe.jwc_*)
        gates.append(("cz", [cq, t], None))
    if abs(a[0]) > 1e-15:
        gates.append(("ry", [t], float(theta * a[0])))
    cur = 0
    for S in order:
        for i in range(len(ctrl_r)):
            if ((S ^ cur) >> i) & 1:
                gates.append(("cx", [ctrl_r[i], t], None))
        cur = S
        gates.append(("ry", [t], float(theta * a[S])))
    for i in range(len(ctrl_r)):
        if (cur >> i) & 1:
            gates.append(("cx", [ctrl_r[i], t], None))
    if cq is not None:
        gates.append(("cz", [cq, t], None))
    gates.append(("unitary", [t], B.conj().T))
    comp = [("cx", [t, q], None) for q in range(k) if (rest >> q) & 1]
    fr = [("cx", [a_, b_], None) for a_, b_ in frame]
    fl = _flag_gates(lits, FLAG["q"]) if lits else []
    if stats is not None:
        stats.append({"flip_pattern": int(diff), "target": int(t), "n_controls": len(ctrl_r),
                      "conj_cz": 0 if cq is None else 2, "flag_literals": len(lits) if lits else 0,
                      "flag_cnots": 0 if not lits else (6 if len(lits) == 2 else 12),
                      "n_terms": len(order) + 1, "walk_cnots": walk_cost(order), "frame_cnots": len(frame),
                      "n_rotations": len(items), "support_used": len(order), "theta_linear": not const,
                      "reduced_table": {"m": int(reduced[0]), "fixed_idx": [int(v) for v in reduced[1]],
                                        "fixed_val": [float(v) for v in reduced[2]],
                                        "scale": "1" if const else "theta"}})
    return comp + fl + fr + gates + fr[::-1] + invert(fl) + comp


def _as_const_linrot(V):
    """A constant 2x2 unitary as LinRot(G, 1, const=True) when it is in SU(2) (no phase); else None."""
    from skqd.circuits_ir import _axis_angle, _phase_su2
    d, W = _phase_su2(np.asarray(V, dtype=complex))
    if abs(d) > 1e-13:
        return None
    nvec, ang = _axis_angle(W)
    if abs(ang) < 1e-13:
        if np.real(W[0, 0]) < 0:
            return None
        return LinRot(np.zeros((2, 2)), 1.0, const=True)
    G = 0.5 * ang * (nvec[0] * _SX + nvec[1] * _SY + nvec[2] * _SZ)
    return LinRot(G, 1.0, const=True)


def two_level(diff: int, items: list, valid, k: int, stats=None, **kw) -> list:
    """Dispatcher: LinRot items -> lin_two_level; constant unitaries -> converted to constant LinRot (theta = 1) and
    lin_two_level when CONST_LIN["on"] (so flags apply to them too), else sw_two_level (theta-free already)."""
    lin = [it for it in items if isinstance(it[2], LinRot)]
    const = [it for it in items if not isinstance(it[2], LinRot)]
    out = []
    if const:
        conv = None
        if CONST_LIN["on"]:
            conv = [(a, b, _as_const_linrot(V)) for a, b, V in const]
            if any(c[2] is None for c in conv):
                conv = None
        done = False
        if conv is not None:
            try:
                out += lin_two_level(diff, conv, valid, k, stats=stats)
                done = True
            except NotImplementedError:
                done = False
        if not done:
            out += sw_two_level(diff, const, valid, k, stats=stats)
    if lin:
        out += lin_two_level(diff, lin, valid, k, stats=stats)
    return out


FLAG = {"q": None}            # local index of a clean ancilla available to the multiplexors (flag variants)
CONST_LIN = {"on": False}     # route constant multiplexors through lin_two_level too


@contextlib.contextmanager
def use_linear(mode: str = "lp"):
    """Route the study's constructions through the angle-linear synthesis (and LP or MILP Walsh supports)."""
    from . import plaqfactor, reach
    old = (plaqfactor._multiplexed_two_level, reach._multiplexed_two_level, reach._block_rounds,
           plaqfactor.LINEAR["on"], SOLVER["mode"])
    plaqfactor._multiplexed_two_level = two_level
    reach._multiplexed_two_level = two_level
    reach._block_rounds = lin_block_rounds
    plaqfactor.LINEAR["on"] = True
    SOLVER["mode"] = mode
    try:
        yield
    finally:
        (plaqfactor._multiplexed_two_level, reach._multiplexed_two_level, reach._block_rounds,
         plaqfactor.LINEAR["on"], SOLVER["mode"]) = old
