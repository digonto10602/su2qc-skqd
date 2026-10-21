"""Vertex frames for hopping terms (family HF, label mine): cheap vertex-local changes of basis applied before
the package's block synthesis, so that the blocks of the framed generator share flip patterns and angle tables.

Frame per end vertex v of the hopping link l (qubits of v: flux bits in codec order, then the vertex bit q):
  P  parity fold: CX(f -> L_v) for the other flux bits f of v, so that L_v holds the vertex's flux parity
     (n_v = 1 iff it is 1); the hop then flips L_v together with the matter label.
  B  bright rotation: where the vertex factor maps one state onto a combination of two intertwiner states
     (n = 1, all three fluxes 1/2), one two-level rotation on q makes that combination a basis state
     (as for the plaquette corners, src/c2x4/plaqfactor.py).
The framed generator h'' = F h F^dag is computed on the frame image of the local codewords (exact), the package
synthesis is run on it with the occupied strings as the only valid ones, and the circuit is F^dag S F
(conjugation, Lean Compress2x4.exp_conj_frame; restriction, Compress2x4.exp_agree_mulVec).
"""
from __future__ import annotations

import numpy as np

from . import env  # noqa: F401
from .evaluate import term_unitary_columns
from .plaqfactor import invert
from .reach import synth_on


def vertex_parity_frame(P, name: str) -> list:
    l = int(name[3:])
    lat = P.M.lat
    codec = P.E.codec
    ends = lat.ends()
    x, y, _ = lat.links[l]
    gates = []
    for v in (x, y):
        o = int(codec.offsets[v])
        flux = [(ll, o + j) for j, (ll, _r) in enumerate(ends[v])]
        L = [q for ll, q in flux if ll == l][0]
        for ll, q in flux:
            if ll != l:
                gates.append(("cx", [q, L], None))
    return gates


def framed_gates(P, name: str, theta: float, frame: list, contract=None, stats=None, anc=None) -> list:
    """`anc`: a support qubit that the frame leaves at 0 on every codeword (a clean ancilla): the angle-linear
    multiplexors may then write a flag into it (linsynth.FLAG)."""
    sup, states, h, pos = P.local(name)
    k = len(sup)
    gpos = {q: i for i, q in enumerate(sup)}
    fr_loc = [(nm, [gpos[q] for q in qs], par) for nm, qs, par in frame]
    cols = states if contract is None else [int(s) for s in contract]
    idx = np.array([pos[int(s)] for s in cols])
    hc = np.asarray(h)[np.ix_(idx, idx)]
    col, out, amp = term_unitary_columns(frame, sup, cols)
    # the frames used here are permutations (CX) or real rotations; build F|_C as a dense matrix
    om = np.unique(out[np.abs(amp) > 1e-14])
    opos = {int(s): i for i, s in enumerate(om)}
    F = np.zeros((len(om), len(cols)), dtype=complex)
    for c_, o_, a_ in zip(col, out, amp):
        if abs(a_) > 1e-14:
            F[opos[int(o_)], c_] += a_
    H2 = F @ hc @ F.conj().T
    if np.abs(np.imag(H2)).max() > 1e-12 and np.abs(np.real(H2)).max() > 1e-12:
        pass                                    # complex generator: synth_on picks the real gauge
    if anc is not None:
        if np.any((om >> gpos[anc]) & 1):
            raise AssertionError(f"ancilla {anc} is not clean after the frame")
        from .linsynth import FLAG
        old = FLAG["q"]
        FLAG["q"] = gpos[anc]
        try:
            core = synth_on([int(s) for s in om], H2, k, theta, stats=stats)
        finally:
            FLAG["q"] = old
    else:
        core = synth_on([int(s) for s in om], H2, k, theta, stats=stats)
    core = [(nm, [sup[q] for q in qs], par) for nm, qs, par in core]
    return frame + core + invert(frame)


# ------------------------------------------------------------------ vertex factors and bright frames
def hop_vertex_factors(P, name: str):
    """Fit T = eta a_x (x) b_y (x) s on the n_x-raising entries (as scripts/p2_1_structure.py); returns
    (parts: [x qubits, y qubits] as global qubit lists, [a_x, b_y] real matrices, eta)."""
    from .plaqfactor import _sub, f2_solve
    l = int(name[3:])
    lat, codec = P.M.lat, P.E.codec
    sup, states, h, pos = P.local(name)
    x, y, _ = lat.links[l]
    gp = {q: i for i, q in enumerate(sup)}
    gparts = []
    for s in (x, y):
        o, w = int(codec.offsets[s]), codec.widths[s]
        gparts.append(list(range(o, o + w)))
    parts = [[gp[q] for q in gq] for gq in gparts]
    parts.append([i for i in range(len(sup)) if i not in parts[0] + parts[1]])
    states = np.array(states)

    def nx(sl):
        return codec.decode_vertex(x, tuple((int(sl) >> p) & 1 for p in parts[0]))[1]
    I, J = np.nonzero(np.abs(h) > 1e-12)
    sel = [e for e, (i, j) in enumerate(zip(I, J)) if nx(states[i]) == nx(states[j]) + 1]
    keys = [dict() for _ in parts]
    for e in sel:
        for c, pp in enumerate(parts):
            keys[c].setdefault((_sub(int(states[I[e]]), pp), _sub(int(states[J[e]]), pp)), len(keys[c]))
    off = np.cumsum([0] + [len(k) for k in keys])
    A = np.zeros((len(sel), off[-1]))
    for r, e in enumerate(sel):
        for c, pp in enumerate(parts):
            A[r, off[c] + keys[c][(_sub(int(states[I[e]]), pp), _sub(int(states[J[e]]), pp))]] = 1
    vals = h[I[sel], J[sel]]
    eta = 1j if np.abs(np.imag(vals)).max() > 1e-12 else 1.0
    v = np.real(vals / eta)
    xm, *_ = np.linalg.lstsq(A, np.log(np.abs(v)), rcond=None)
    ok, sg = f2_solve(A.astype(np.uint8), (v < 0).astype(np.uint8))
    if not ok:
        raise ValueError("hop signs do not factorise")
    mats = []
    for c in (0, 1):
        w = len(parts[c])
        Mx = np.zeros((1 << w, 1 << w))
        for (o, i), q in keys[c].items():
            Mx[o, i] = (-1.0) ** int(sg[off[c] + q]) * np.exp(xm[off[c] + q])
        mats.append(Mx)
    valid = [sorted({_sub(int(s), parts[c]) for s in states}) for c in (0, 1)]
    return gparts, mats, eta, valid


def vertex_bright_frame(P, name: str) -> list:
    """Parity fold, then for every vertex state mapped by the vertex factor onto two intertwiner states (or
    reached from two), one two-level rotation on the vertex bit making that combination a basis state."""
    from .plaqfactor import _gate_unitary
    from skqd.circuits_ir import _multiplexed_two_level as _mtl
    fold = vertex_parity_frame(P, name)
    gparts, mats, eta, valid = hop_vertex_factors(P, name)
    out = list(fold)
    for c in (0, 1):
        qs = gparts[c]
        w = len(qs)
        loc = [(nm, [qs.index(q) for q in qq], par) for nm, qq, par in fold if all(q in qs for q in qq)]
        U = _gate_unitary(loc, w)
        A1 = np.real(U @ mats[c] @ U.conj().T)
        vset = np.array(sorted({int(np.argmax(np.abs(U[:, s]))) for s in valid[c]}), dtype=np.int64)
        done = set()
        for s0 in range(1 << w):
            for M_ in (A1[:, s0], A1[s0, :]):                  # images of s0 (raising) or preimages
                nz = [int(t) for t in np.flatnonzero(np.abs(M_) > 1e-12)]
                if len(nz) == 2 and tuple(nz) not in done:
                    s1, s2 = nz
                    d = s1 ^ s2
                    if d & (d - 1):
                        raise NotImplementedError("bright pair differs in more than one bit")
                    v1, v2 = M_[s1], M_[s2]
                    R = np.array([[v1, v2], [-v2, v1]], dtype=complex) / np.hypot(v1, v2)
                    g = _mtl(d, [(s1, s2, R)], vset, w)
                    out += [(nm, [qs[q] for q in qq], par) for nm, qq, par in g]
                    done.add(tuple(nz))
                    U = _gate_unitary(loc + [(nm, qq, par) for nm, qq, par in
                                             [(n_, q_, p_) for n_, q_, p_ in g]], w)
                    loc = loc + g
                    A1 = np.real(U @ mats[c] @ U.conj().T)
    return out


# ------------------------------------------------------------------ C4 step 3: JW sign as a conjugation (label JWC, mine)
def _parity(v: int) -> int:
    return bin(int(v)).count("1") & 1


def jwc_framed_gates(P, name: str, theta: float, frame: list, contract=None, stats=None, anc=None) -> list:
    """Hop with the Jordan-Wigner sign taken out of the multiplexors (notes/007 §6 step 3; plan notes/010).

    The framed generator is H2 = (-1)^{par(J)} h0, J the support qubits outside the two end vertices (the JW string),
    h0 independent of J (checked element by element; a NotImplementedError otherwise).  Fold par(J) into p = J[0]
    (CX J[i] -> p), synthesise exp(-i theta h0) on the remaining qubits with the angle-linear synthesis, and conjugate
    every theta-multiplexor's target by CZ(p, t): Z_t W(a) Z_t = W(-a) for a closed CNOT walk W, so the p = 1 branch is
    exp(+i theta h0) = B^T P(-theta) B (B the theta-free basis change of the bipartite block rounds).  Lean:
    Compress2x4.walk_conj_neg (new in C4) and exp_conj_frame."""
    from .linsynth import CONJ, use_linear
    sup, states, h, pos = P.local(name)
    k = len(sup)
    gpos = {q: i for i, q in enumerate(sup)}
    lat, codec = P.M.lat, P.E.codec
    x, y, _ = lat.links[int(name[3:])]
    vq = set()
    for s_ in (x, y):
        o, w = int(codec.offsets[s_]), codec.widths[s_]
        vq |= set(range(o, o + w))
    J = [gpos[q] for q in sup if q not in vq]
    if not J:
        raise NotImplementedError("no JW qubits")
    cols = states if contract is None else [int(s_) for s_ in contract]
    idx = np.array([pos[int(s_)] for s_ in cols])
    hc = np.asarray(h)[np.ix_(idx, idx)]
    col, out, amp = term_unitary_columns(frame, sup, cols)
    om = np.unique(out[np.abs(amp) > 1e-14])
    opos = {int(s_): i for i, s_ in enumerate(om)}
    F = np.zeros((len(om), len(cols)), dtype=complex)
    for c_, o_, a_ in zip(col, out, amp):
        if abs(a_) > 1e-14:
            F[opos[int(o_)], c_] += a_
    H2 = F @ hc @ F.conj().T
    R = [i for i in range(k) if i not in J]
    Jmask = sum(1 << j for j in J)

    def rest_of(s_):
        return sum(((int(s_) >> r) & 1) << i for i, r in enumerate(R))
    h0 = {}
    for i_, j_ in zip(*np.nonzero(np.abs(H2) > 1e-13)):
        si, sj = int(om[i_]), int(om[j_])
        if (si & Jmask) != (sj & Jmask):
            raise NotImplementedError("the term changes a JW qubit")
        v = H2[i_, j_] * (-1) ** _parity(sj & Jmask)
        key = (rest_of(si), rest_of(sj))
        if key in h0 and abs(h0[key] - v) > 1e-12:
            raise NotImplementedError("the JW dependence is not a pure parity sign")
        h0[key] = v
    rstates = sorted({rest_of(s_) for s_ in om})
    rpos = {s_: i for i, s_ in enumerate(rstates)}
    H0 = np.zeros((len(rstates), len(rstates)), dtype=complex)
    for (a_, b_), v in h0.items():
        H0[rpos[a_], rpos[b_]] = v
    p = J[0]
    fold = [("cx", [sup[j], sup[p]], None) for j in J[1:]]
    kr = len(R) + 1                                   # register: R qubits, then p
    from .linsynth import FLAG
    old, oldf = CONJ["q"], FLAG["q"]
    CONJ["q"] = len(R)
    if anc is not None:
        if np.any((om >> gpos[anc]) & 1):
            raise AssertionError(f"ancilla {anc} is not clean after the frame")
        FLAG["q"] = R.index(gpos[anc])
    try:
        with use_linear("milp" if SOLVER_MODE["milp"] else "lp"):
            core = synth_on(rstates, H0, kr, theta, stats=stats)
    finally:
        CONJ["q"], FLAG["q"] = old, oldf
    regmap = [sup[r] for r in R] + [sup[p]]
    core = [(nm, [regmap[q] for q in qs], par) for nm, qs, par in core]
    return frame + fold + core + invert(fold) + invert(frame)


SOLVER_MODE = {"milp": False}


# ------------------------------------------------------------------ C4 step 3: hop frame with a clean ancilla (label CB, mine)
def _bright_rotations(qs, mats_c, valid_c, loc):
    """The bright/dark rotations of one vertex (as in vertex_bright_frame) for a given vertex-local fold `loc`
    (local indices); returns gates in local indices of the vertex."""
    from .plaqfactor import _gate_unitary
    from skqd.circuits_ir import _multiplexed_two_level as _mtl
    w = len(qs)
    U = _gate_unitary(loc, w)
    A1 = np.real(U @ mats_c @ U.conj().T)
    vset = np.array(sorted({int(np.argmax(np.abs(U[:, s]))) for s in valid_c}), dtype=np.int64)
    done = set()
    out = []
    for s0 in range(1 << w):
        for M_ in (A1[:, s0], A1[s0, :]):
            nz = [int(t) for t in np.flatnonzero(np.abs(M_) > 1e-12)]
            if len(nz) == 2 and tuple(nz) not in done:
                s1, s2 = nz
                d = s1 ^ s2
                if d & (d - 1):
                    raise NotImplementedError("bright pair differs in more than one bit")
                v1, v2 = M_[s1], M_[s2]
                R = np.array([[v1, v2], [-v2, v1]], dtype=complex) / np.hypot(v1, v2)
                g = _mtl(d, [(s1, s2, R)], vset, w)
                out += g
                done.add(tuple(nz))
                loc = loc + g
                U = _gate_unitary(loc, w)
                A1 = np.real(U @ mats_c @ U.conj().T)
    return out


def vertex_bright_frame_clean(P, name: str, anc_vertex: int = 1, bright: bool = True):
    """Parity folds + bright rotations as vertex_bright_frame, except that vertex B = ends[anc_vertex] folds its
    parity into its first other flux qubit, and B's copy of the hopping link is then cleared by CX from A's copy
    (equal on every codeword; done before A's fold changes A's copy).  Returns (frame, ancilla qubit)."""
    l = int(name[3:])
    lat, codec = P.M.lat, P.E.codec
    ends = lat.ends()
    gparts, mats, eta, valid = hop_vertex_factors(P, name)
    xy = lat.links[l][:2]
    Lq, others = [], []
    for c, v in enumerate(xy):
        o = int(codec.offsets[v])
        flux = [(ll, o + j) for j, (ll, _r) in enumerate(ends[v])]
        Lq.append([q for ll, q in flux if ll == l][0])
        others.append([q for ll, q in flux if ll != l])
    A, B = 1 - anc_vertex, anc_vertex
    fold = {A: [("cx", [q, Lq[A]], None) for q in others[A]],
            B: [("cx", [Lq[B], others[B][0]], None)] + [("cx", [q, others[B][0]], None) for q in others[B][1:]]}
    rot = {}
    for c in (A, B):
        qs = gparts[c]
        loc = [(nm, [qs.index(q) for q in qq], par) for nm, qq, par in fold[c]]
        g = _bright_rotations(qs, mats[c], valid[c], loc) if bright else []
        rot[c] = [(nm, [qs[q] for q in qq], par) for nm, qq, par in g]
    frame = fold[B] + rot[B] + [("cx", [Lq[A], Lq[B]], None)] + fold[A] + rot[A]
    return frame, Lq[B]
