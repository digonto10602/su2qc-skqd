"""Corner factorisation of a plaquette term and the "corner frame + one rotation" circuit (label CF1, mine).

Facts used (each re-checked numerically at run time, never assumed):
  F1  on the local codeword space C of the term, h = A_0 (x) A_1 (x) A_2 (x) A_3 with A_c a real matrix on
      corner c's qubits (fit: log-magnitudes by least squares, signs over F2; checked on every codeword
      column and every one of the 2^k rows);
  F2  after the corner frames (CX(p_a -> p_b) and one bright/dark rotation per three-state block) and the
      CNOT ladder from p_1, the generator is X_{p_1} (x) diag(F) on the occupied states (checked entry by
      entry), so exp(-i theta h) = Frame^dag . UCR_x(2 theta F) . Frame on C.
Identities this relies on are proved in Lean (lean/Compress2x4/*.lean): conjugation of the exponential by a
unitary, agreement of exponentials on an invariant subspace on which two generators agree, the CNOT-ladder
Pauli identity, and the uniformly controlled rotation.
"""
from __future__ import annotations

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.csgraph as csg

from . import env  # noqa: F401
from .evaluate import term_unitary_columns
from skqd.circuits_ir import _multiplexed_two_level, run_ir   # noqa: E402  (package synthesis blocks, read-only)


# ------------------------------------------------------------------ layout
def corners_of(P, pidx: int) -> list:
    """The four corners of plaquette `pidx` in the order c00, c10, c11, c01 with their qubits:
    `qubits` (global, codec order), `plinks` (the two flux qubits of plaquette links), `third` (flux
    qubit of the third link or None), `q` (the vertex bit)."""
    lat = P.M.lat
    codec = P.E.codec
    ends = lat.ends()
    pl = lat.plaquettes[pidx]
    plinks = {pl[k] for k in ("b", "r", "t", "l")}
    out = []
    for key in ("c00", "c10", "c11", "c01"):
        s = pl[key]
        o = int(codec.offsets[s])
        w = int(codec.widths[s])
        flux = [(l, o + j) for j, (l, _) in enumerate(ends[s])]
        out.append({"key": key, "site": int(s), "qubits": list(range(o, o + w)),
                    "plinks": [q for l, q in flux if l in plinks],
                    "plink_ids": [l for l, q in flux if l in plinks],
                    "third": ([q for l, q in flux if l not in plinks] or [None])[0],
                    "q": o + len(flux)})
    return out


def _sub(s: int, pos: list) -> int:
    """Bits of local integer s at positions `pos` packed into a small integer (pos[0] = bit 0)."""
    v = 0
    for j, p in enumerate(pos):
        v |= ((s >> p) & 1) << j
    return v


# ------------------------------------------------------------------ F2 helpers
def f2_solve(A: np.ndarray, b: np.ndarray):
    """Solve A x = b over F2; returns (consistent, one solution)."""
    A = (A % 2).astype(np.uint8).copy()
    b = (b % 2).astype(np.uint8).copy()
    m, n = A.shape
    r = 0
    piv = []
    for c in range(n):
        if r == m:
            break
        p = np.nonzero(A[r:, c])[0]
        if len(p) == 0:
            continue
        p = p[0] + r
        A[[r, p]] = A[[p, r]]
        b[[r, p]] = b[[p, r]]
        rows = np.nonzero(A[:, c])[0]
        rows = rows[rows != r]
        A[rows] ^= A[r]
        b[rows] ^= b[r]
        piv.append(c)
        r += 1
    ok = not np.any(b[r:])
    x = np.zeros(n, np.uint8)
    for i, c in enumerate(piv):
        x[c] = b[i]
    return ok, x


# ------------------------------------------------------------------ factorisation
def factorise(P, name: str, corners: list) -> dict:
    """Fit h = (x)_c A_c on the term's local codewords; returns the corner matrices (indexed by the
    corner's qubits in codec order, bit j = corners[c]['qubits'][j]) and the residuals."""
    sup, states, h, pos = P.local(name)
    if np.abs(np.imag(h)).max() > 1e-12:
        raise ValueError(f"{name}: complex generator, the real fit does not apply")
    h = np.real(h)
    gpos = {q: i for i, q in enumerate(sup)}
    cpos = [[gpos[q] for q in c["qubits"]] for c in corners]
    states = np.array(states, dtype=np.int64)
    I, J = np.nonzero(np.abs(h) > 1e-12)
    keys = [dict() for _ in corners]
    for i, j in zip(I, J):
        for c, cp in enumerate(cpos):
            kk = (_sub(int(states[i]), cp), _sub(int(states[j]), cp))
            keys[c].setdefault(kk, len(keys[c]))
    off = np.cumsum([0] + [len(k) for k in keys])
    A = np.zeros((len(I), off[-1]))
    for e, (i, j) in enumerate(zip(I, J)):
        for c, cp in enumerate(cpos):
            A[e, off[c] + keys[c][(_sub(int(states[i]), cp), _sub(int(states[j]), cp))]] = 1
    vals = h[I, J]
    x, *_ = np.linalg.lstsq(A, np.log(np.abs(vals)), rcond=None)
    mag_res = float(np.abs(A @ x - np.log(np.abs(vals))).max())
    ok, sg = f2_solve(A.astype(np.uint8), (vals < 0).astype(np.uint8))
    if not ok:
        raise ValueError(f"{name}: signs do not factorise over the corners")
    mats = []
    for c, corner in enumerate(corners):
        w = len(corner["qubits"])
        Mx = np.zeros((1 << w, 1 << w))
        for (o, i), q in keys[c].items():
            Mx[o, i] = (-1.0) ** int(sg[off[c] + q]) * np.exp(x[off[c] + q])
        mats.append(Mx)
    # full check: product on every codeword column, every row of the 2^k local space
    K = sp.csr_matrix([[1.0]])
    for c in range(len(corners) - 1, -1, -1):
        K = sp.kron(K, sp.csr_matrix(mats[c]), format="csr")
    # K is indexed by the concatenation of the corners' bits (corner 0 lowest); map to support order
    perm_bits = sum(cpos, [])
    k = len(sup)
    assert sorted(perm_bits) == list(range(k)), "corners must tile the support"
    def to_corner_order(s):
        return sum(((int(s) >> p) & 1) << j for j, p in enumerate(perm_bits))
    cs = np.array([to_corner_order(s) for s in states], dtype=np.int64)
    Kc = K[:, cs].tocoo()
    # rows back to support order
    inv = np.zeros(1 << k, dtype=np.int64)
    allr = np.arange(1 << k)
    sup_of = np.zeros(1 << k, dtype=np.int64)
    for j, p in enumerate(perm_bits):
        sup_of |= ((allr >> j) & 1) << p
    rows = sup_of[Kc.row]
    Hs = sp.csr_matrix((h[I, J], (states[I], J)), shape=(1 << k, len(states)))
    Ks = sp.csr_matrix((Kc.data, (rows, Kc.col)), shape=(1 << k, len(states)))
    prod_res = float(abs(Ks - Hs).max())
    return {"mats": mats, "corner_positions": cpos, "magnitude_residual": mag_res,
            "product_residual_all_rows": prod_res, "n_elements": int(len(I)),
            "pairs_per_corner": [len(k_) for k_ in keys]}


def corner_blocks(Mx: np.ndarray):
    """Connected blocks (lists of states with at least one nonzero element) of a corner matrix."""
    G = (np.abs(Mx) > 1e-12) | (np.abs(Mx.T) > 1e-12)
    n, lab = csg.connected_components(sp.csr_matrix(G), directed=False)
    out = []
    for b in range(n):
        idx = [int(s) for s in np.nonzero(lab == b)[0] if G[s].any()]
        if idx:
            out.append(idx)
    return out


# ------------------------------------------------------------------ corner frame
def _gate_unitary(gates: list, w: int) -> np.ndarray:
    U = np.zeros((1 << w, 1 << w), dtype=complex)
    for s in range(1 << w):
        v = np.zeros(1 << w, dtype=complex)
        v[s] = 1
        U[:, s] = run_ir(gates, w, v)
    return U


def corner_frame(Mx: np.ndarray, corner: dict, valid: list):
    """Corner-local gate list (local qubit indices 0..w-1 = corner['qubits']) that brings the corner
    matrix to the form X_{p_a} (x) D on its blocks.  Returns (gates, transformed matrix, p_a local index)."""
    qs = corner["qubits"]
    w = len(qs)
    ja, jb = qs.index(corner["plinks"][0]), qs.index(corner["plinks"][1])
    gates = [("cx", [ja, jb], None)]
    U = _gate_unitary(gates, w)
    A1 = np.real(U @ Mx @ U.conj().T)
    vset = sorted({int(np.argmax(np.abs(U[:, s]))) for s in valid})       # CX is a permutation
    for blk in corner_blocks(A1):
        if len(blk) == 2:
            continue
        if len(blk) != 3:
            raise NotImplementedError(f"corner block of size {len(blk)}")
        deg = [(np.abs(A1[s, blk]) > 1e-12).sum() for s in blk]
        s0 = blk[int(np.argmax(deg))]
        s1, s2 = [s for s in blk if s != s0]
        d = s1 ^ s2
        if d & (d - 1):
            raise NotImplementedError("the two states of the three-state block differ in more than one bit")
        v1, v2 = A1[s1, s0], A1[s2, s0]
        nv = np.hypot(v1, v2)
        R = np.array([[v1, v2], [-v2, v1]], dtype=complex) / nv        # bright -> s1, dark -> s2
        gates += _multiplexed_two_level(d, [(s1, s2, R)], np.array(vset, dtype=np.int64), w)
    U = _gate_unitary(gates, w)
    A2 = U @ Mx @ U.conj().T
    if np.abs(np.imag(A2)).max() > 1e-12:
        raise AssertionError("corner frame produced a complex matrix")
    A2 = np.real(A2)
    # check the X_{p_a} (x) D form
    for i, j in zip(*np.nonzero(np.abs(A2) > 1e-12)):
        if (i ^ j) != (1 << ja):
            raise AssertionError(f"corner frame: element ({i},{j}) is not a p_a flip")
    return gates, A2, ja


# ------------------------------------------------------------------ the term circuit
def frame_generator(P, name: str, frame: list, contract=None):
    """h'' = F h F^dag on the frame image of the local codewords (or of the `contract` subset, which must be
    a union of blocks of h), as a sparse matrix over the 2^k local strings, plus the occupied set Omega
    (basis strings with a nonzero amplitude in F|C>)."""
    sup, states, h, pos = P.local(name)
    k = len(sup)
    if contract is not None:
        idx = np.array([pos[int(s_)] for s_ in contract])
        states = [int(states[i]) for i in idx]
        h = np.asarray(h)[np.ix_(idx, idx)]
    col, out, amp = term_unitary_columns(frame, sup, states)
    keep = np.abs(amp) > 0
    FC = sp.csr_matrix((amp[keep], (out[keep], col[keep])), shape=(1 << k, len(states)))
    Hd = sp.csr_matrix(np.asarray(h))
    H2 = (FC @ Hd @ FC.conj().T).tocsr()
    H2.data[np.abs(H2.data) < 1e-15] = 0          # exact zeros from cancellation only
    H2.eliminate_zeros()
    omega = np.unique(out[np.abs(amp) > 1e-14])
    return H2, omega


def cf1_gates(P, name: str, theta: float, pidx: int, return_info: bool = False, contract=None):
    """CF1: corner frames, CNOT ladder, ONE multiplexed rotation, inverse frames (global qubit indices)."""
    sup, states, h, pos = P.local(name)
    corners = corners_of(P, pidx)
    fac = factorise(P, name, corners)
    frame = []
    pa_global = []
    for c, corner in enumerate(corners):
        cp = fac["corner_positions"][c]
        valid = sorted({_sub(int(s), cp) for s in states})
        g, A2, ja = corner_frame(fac["mats"][c], corner, valid)
        frame += [(nm, [corner["qubits"][q] for q in qs], par) for nm, qs, par in g]
        pa_global.append(corner["qubits"][ja])
    p1 = pa_global[0]
    frame += [("cx", [p1, q], None) for q in pa_global[1:]]
    H2, omega = frame_generator(P, name, frame, contract)
    gpos = {q: i for i, q in enumerate(sup)}
    t = gpos[p1]
    coo = H2.tocoo()
    if np.any((coo.row ^ coo.col) != (1 << t)):
        raise AssertionError("frame generator is not X on p_1 (x) diagonal")
    if np.abs(np.imag(coo.data)).max() > 1e-12:
        raise AssertionError("frame generator is not real")
    Fval = {}
    for r, c_, v in zip(coo.row, coo.col, np.real(coo.data)):
        Fval[int(c_)] = float(v)
    items = []
    for s0 in sorted({int(s) & ~(1 << t) for s in omega}):
        s1 = s0 | (1 << t)
        f = Fval.get(s0, 0.0)
        if abs(f - Fval.get(s1, 0.0)) > 1e-12:
            raise AssertionError("frame generator is not symmetric on a pair")
        if f == 0.0:
            continue
        cth, sth = np.cos(theta * f), np.sin(theta * f)
        items.append((s0, s1, np.array([[cth, -1j * sth], [-1j * sth, cth]], dtype=complex)))
    stats = []
    core = _multiplexed_two_level(1 << t, items, np.array(omega, dtype=np.int64), len(sup), stats=stats)
    core = [(nm, [sup[q] for q in qs], par) for nm, qs, par in core]
    inv = invert(frame)
    gates = frame + core + inv
    if return_info:
        return gates, {"factorisation": {k_: v for k_, v in fac.items() if k_ != "mats"},
                       "corners": corners, "p1": p1, "omega": int(len(omega)),
                       "n_rotations": len(items), "multiplexer": stats,
                       "frame_2q": sum(1 for g in frame if g[0] in ("cx", "cz", "cp", "rzz"))}
    return gates


def invert(gates: list) -> list:
    """Inverse of an IR gate list (only the gate kinds used by the frames)."""
    out = []
    for nm, qs, par in reversed(gates):
        if nm in ("cx", "x", "h", "cz"):
            out.append((nm, qs, par))
        elif nm in ("ry", "rz", "rx", "p", "cp", "rzz", "gphase"):
            out.append((nm, qs, -par))
        elif nm == "unitary":
            out.append((nm, qs, np.asarray(par).conj().T))
        else:
            raise ValueError(f"cannot invert {nm}")
    return out


# ================================================================== CF2: clean ancillas + flags
def toffoli(c1: int, c2: int, t: int) -> list:
    """Exact Toffoli (6 CX, standard Clifford+T decomposition; p(pi/4) = T)."""
    T, Td = np.pi / 4, -np.pi / 4
    return [("h", [t], None), ("cx", [c2, t], None), ("p", [t], Td), ("cx", [c1, t], None),
            ("p", [t], T), ("cx", [c2, t], None), ("p", [t], Td), ("cx", [c1, t], None),
            ("p", [c2], T), ("p", [t], T), ("h", [t], None), ("cx", [c1, c2], None),
            ("p", [c1], T), ("p", [c2], Td), ("cx", [c1, c2], None)]


def ccz(a: int, b: int, c: int) -> list:
    """Exact CCZ = (-1)^{abc} as 3 controlled phases + 2 CX (5 native ZZ gates):
    pi/2 (b c - (a xor b) c + a c) = pi a b c."""
    h = np.pi / 2
    return [("cp", [b, c], h), ("cx", [a, b], None), ("cp", [b, c], -h), ("cx", [a, b], None),
            ("cp", [a, c], h)]


def rtof(c1: int, c2: int, t: int) -> list:
    """Margolus relative-phase Toffoli (3 CX): Toffoli times a diagonal sign on the control
    space (|c1 c2> = |1 0> gets -1).  Used only as compute ... uncompute with `invert`."""
    q = np.pi / 4
    return [("ry", [t], q), ("cx", [c2, t], None), ("ry", [t], q), ("cx", [c1, t], None),
            ("ry", [t], -q), ("cx", [c2, t], None), ("ry", [t], -q)]


def f2_relations(vectors: np.ndarray, nbits: int) -> list:
    """Basis of {r : r . (v + v0) = 0 for all v} (affine relations of a set of bit vectors), as ints."""
    v0 = int(vectors[0])
    rows = np.array([[((int(v) ^ v0) >> b) & 1 for b in range(nbits)] for v in vectors], dtype=np.uint8)
    # null space of rows over F2
    A = rows.copy()
    m, n = A.shape
    r = 0
    piv = []
    for c in range(n):
        if r == m:
            break
        p = np.nonzero(A[r:, c])[0]
        if len(p) == 0:
            continue
        p = p[0] + r
        A[[r, p]] = A[[p, r]]
        rr = np.nonzero(A[:, c])[0]
        rr = rr[rr != r]
        A[rr] ^= A[r]
        piv.append(c)
        r += 1
    free = [c for c in range(n) if c not in piv]
    basis = []
    for f in free:
        x = np.zeros(n, np.uint8)
        x[f] = 1
        for i, c in enumerate(piv):
            x[c] = A[i, f]
        basis.append(int(sum(int(b) << j for j, b in enumerate(x))))
    return basis


def cf2_gates(P, name: str, theta: float, pidx: int, return_info: bool = False, exact_toffoli=False,
              contract=None):
    """CF2 for a plaquette whose four corners are interior vertices (plaq1 at 2x4)."""
    sup, states, h, pos = P.local(name)
    gpos = {q: i for i, q in enumerate(sup)}
    corners = corners_of(P, pidx)
    if any(c["third"] is None for c in corners):
        raise NotImplementedError("CF2 is written for four interior corners")
    fac = factorise(P, name, corners)
    # ---- 1. corner frames (CX + bright rotation); remember the bright items to re-sign them
    def build_frames(bright_sign, cz_c, cz_q, ccz_xc=(0, 0, 0, 0)):
        fr, pa = [], []
        for c, corner in enumerate(corners):
            cp = fac["corner_positions"][c]
            valid = sorted({_sub(int(s), cp) for s in states})
            qs = corner["qubits"]
            w = len(qs)
            ja, jb = qs.index(corner["plinks"][0]), qs.index(corner["plinks"][1])
            g = [("cx", [ja, jb], None)]
            U = _gate_unitary(g, w)
            A1 = np.real(U @ fac["mats"][c] @ U.conj().T)
            vset = np.array(sorted({int(np.argmax(np.abs(U[:, s]))) for s in valid}), dtype=np.int64)
            for blk in corner_blocks(A1):
                if len(blk) != 3:
                    continue
                deg = [(np.abs(A1[s, blk]) > 1e-12).sum() for s in blk]
                s0 = blk[int(np.argmax(deg))]
                s1, s2 = [s for s in blk if s != s0]
                v1, v2 = A1[s1, s0], A1[s2, s0]
                R = np.array([[v1, v2], [-v2, v1]], dtype=complex) / np.hypot(v1, v2)
                if bright_sign[c]:
                    R = -R
                g += _multiplexed_two_level(s1 ^ s2, [(s1, s2, R)], vset, w)
            jc, jq = qs.index(corner["third"]), qs.index(corner["q"])
            if cz_c[c]:
                g.append(("cp", [jc, ja], np.pi))
            if cz_q[c]:
                g.append(("cp", [jq, ja], np.pi))
            if ccz_xc[c]:                                  # (-1)^{p_a (1 - x) c}
                g += [("x", [jb], None)] + ccz(ja, jb, jc) + [("x", [jb], None)]
            fr += [(nm, [qs[q] for q in qq], par) for nm, qq, par in g]
            pa.append(qs[ja])
        return fr, pa

    def labels(s):
        out = []
        for corner in corners:
            x = (s >> gpos[corner["plinks"][1]]) & 1
            cc = (s >> gpos[corner["third"]]) & 1
            qq = (s >> gpos[corner["q"]]) & 1
            out.append((x, cc, qq))
        return out

    # ---- 2. sign analysis in the plain frame (+ ladder) and choice of the cheapest corrections
    zero = [0, 0, 0, 0]
    fr0, pa = build_frames(zero, zero, zero)
    has_triple = [any(len(b_) == 3 for b_ in corner_blocks(fac["mats"][c])) for c in range(4)]
    p1 = pa[0]
    ladder = [("cx", [p1, q], None) for q in pa[1:]]
    H2, omega = frame_generator(P, name, fr0 + ladder, contract)
    coo = H2.tocoo()
    t = gpos[p1]
    if np.any((coo.row ^ coo.col) != (1 << t)):
        raise AssertionError("frame generator is not X on p_1 (x) diagonal")
    samples = [(int(cc), float(np.real(v))) for cc, v in zip(coo.col, coo.data) if not (int(cc) >> t) & 1]
    # monomials: free = all x-monomials (16), bright per corner, g per corner, g products are free too but
    # unnecessary here; costed = c_c, q_c
    import itertools as _it
    free_cols, costed_cols = [], []
    def feat(s):
        L = labels(s)
        xs = [l[0] for l in L]
        f = []
        for sub_ in _it.product([0, 1], repeat=4):
            f.append(int(all(xs[i] for i in range(4) if sub_[i])))
        for ci, (x, cc, qq) in enumerate(L):
            # bright label: its sign is free (Ry angle + 2 pi) only where a bright rotation exists
            f.append(int(x == 0 and cc == 1 and qq == 0) if has_triple[ci] else 0)
            f.append(int(cc == 1 and qq == 1))                     # g flag
        cost = []
        for (x, cc, qq) in L:
            cost += [cc, qq, int(x == 0 and cc == 1)]
        return f, cost
    F_free, F_cost, b = [], [], []
    for s, v in samples:
        f, c_ = feat(s)
        F_free.append(f)
        F_cost.append(c_)
        b.append(int(v < 0))
    F_free, F_cost, b = np.array(F_free), np.array(F_cost), np.array(b)
    unit_cost = [1, 1, 5] * 4                       # CZ(c,pa), CZ(q,pa): 1 ZZ; CCZ(pa,~x,c): 3 CP + 2 CX
    choice = None
    for sel_mask in sorted(range(1 << 12), key=lambda m_: (sum(unit_cost[i] for i in range(12) if (m_ >> i) & 1), m_)):
        sel = [i for i in range(12) if (sel_mask >> i) & 1]
        A = np.hstack([F_free, F_cost[:, sel]]) if sel else F_free
        ok, sol = f2_solve(A, b)
        if ok:
            choice = (sel, sol)
            break
    if choice is None:
        raise AssertionError("sign structure not absorbable")
    sel, sol = choice
    nfree = F_free.shape[1]
    bright_sign = [int(sol[16 + 2 * c]) for c in range(4)]
    cz_c, cz_q, ccz_xc = [0] * 4, [0] * 4, [0] * 4
    for i, s_ in enumerate(sel):
        if sol[nfree + i]:
            (cz_c, cz_q, ccz_xc)[s_ % 3][s_ // 3] = 1
    fr, pa = build_frames(bright_sign, cz_c, cz_q, ccz_xc)
    # ---- 3. ladder, then clear redundant qubits (relations on the occupied set)
    frame = fr + ladder
    _, omega = frame_generator(P, name, frame, contract)
    k = len(sup)
    rel = f2_relations(omega, k)
    # pick pivots: prefer the cleared p_a's of corners 1..3, then x of corner 3, never p1
    prefer = [gpos[q] for q in pa[1:]] + [gpos[corners[3]["plinks"][1]]]
    # reduce relations so that each preferred pivot appears in exactly one relation
    rel = list(rel)
    clear = []
    for pv in prefer:
        cand = [r for r in rel if (r >> pv) & 1]
        if not cand:
            continue
        r0 = min(cand, key=lambda r: bin(r).count("1"))
        rel = [r ^ r0 if ((r >> pv) & 1 and r != r0) else r for r in rel if r != r0]
        clear.append((pv, r0))
        if len(clear) == 4:
            break
    # constant value of each relation on omega: r . s0
    s0 = int(omega[0])
    clear_gates = []
    for pv, r in clear:
        for b_ in range(k):
            if b_ != pv and (r >> b_) & 1:
                clear_gates.append(("cx", [sup[b_], sup[pv]], None))
        if bin(r & s0).count("1") % 2:
            clear_gates.append(("x", [sup[pv]], None))
    # the clears of later pivots must not use earlier pivots as sources (they are already 0): check
    frame = frame + clear_gates
    _, omega2 = frame_generator(P, name, frame, contract)
    anc = [sup[pv] for pv, _ in clear]
    for a in anc:
        if np.any((omega2 >> gpos[a]) & 1):
            raise AssertionError(f"qubit {a} is not cleared")
    # ---- 4. flags g_c = c_c AND q_c into the clean qubits
    flags = []
    for corner, a in zip(corners, anc):
        flags += (toffoli if exact_toffoli else rtof)(corner["third"], corner["q"], a)
    frame = frame + flags
    H3, omega3 = frame_generator(P, name, frame, contract)
    coo = H3.tocoo()
    if np.any((coo.row ^ coo.col) != (1 << t)):
        raise AssertionError("final frame generator is not X on p_1 (x) diagonal")
    Fval = {int(cc): complex(v) for cc, v in zip(coo.col, coo.data)}
    items = []
    for s0_ in sorted({int(s) & ~(1 << t) for s in omega3}):
        s1_ = s0_ | (1 << t)
        f = Fval.get(s0_, 0.0)
        if abs(f - np.conj(Fval.get(s1_, 0.0))) > 1e-12 or abs(np.imag(f)) > 1e-12:
            raise AssertionError("frame generator is not real symmetric on a pair")
        f = float(np.real(f))
        if f == 0.0:
            continue
        cth, sth = np.cos(theta * f), np.sin(theta * f)
        items.append((s0_, s1_, np.array([[cth, -1j * sth], [-1j * sth, cth]], dtype=complex)))
    stats = []
    # the package's greedy control reduction tries low bit indices first: relabel the support so that
    # the bits the flags were computed from (third link, vertex bit) come first and are dropped first
    first = [gpos[c_["third"]] for c_ in corners] + [gpos[c_["q"]] for c_ in corners]
    order = first + [b_ for b_ in range(k) if b_ not in first]          # new index i <- old bit order[i]
    core = mux_relabelled(1 << t, items, omega3, k, order, stats)
    core = [(nm, [sup[q] for q in qs], par) for nm, qs, par in core]
    gates = frame + core + invert(frame)
    if return_info:
        return gates, {"bright_sign": bright_sign, "cz_c": cz_c, "cz_q": cz_q, "ccz_xc": ccz_xc, "ancillas": anc,
                       "clear_2q": sum(1 for g in clear_gates if g[0] == "cx"),
                       "frame_2q": sum(1 for g in frame if g[0] in ("cx", "cz", "cp", "rzz")),
                       "multiplexer": stats, "n_rotations": len(items)}
    return gates


def cfg_gates(P, name: str, theta: float, pidx: int, return_info: bool = False, exact_toffoli=False,
              contract=None, use_flags=True, flag_rule="dark"):
    """CF2 generalised (label CFG, mine): corners may be interior (third link + vertex bit) or corner vertices
    (two plaquette links + vertex bit).  Flags g_c = third AND q are computed only for corners that have a
    dark state (a three-state block); the sign corrections offered depend on the corner type."""
    sup, states, h, pos = P.local(name)
    gpos = {q: i for i, q in enumerate(sup)}
    corners = corners_of(P, pidx)
    fac = factorise(P, name, corners)
    # ---- 1. corner frames (CX + bright rotation); remember the bright items to re-sign them
    def build_frames(bright_sign, cz_c, cz_q, ccz_xc=(0, 0, 0, 0)):
        fr, pa = [], []
        for c, corner in enumerate(corners):
            cp = fac["corner_positions"][c]
            valid = sorted({_sub(int(s), cp) for s in states})
            qs = corner["qubits"]
            w = len(qs)
            ja, jb = qs.index(corner["plinks"][0]), qs.index(corner["plinks"][1])
            g = [("cx", [ja, jb], None)]
            U = _gate_unitary(g, w)
            A1 = np.real(U @ fac["mats"][c] @ U.conj().T)
            vset = np.array(sorted({int(np.argmax(np.abs(U[:, s]))) for s in valid}), dtype=np.int64)
            for blk in corner_blocks(A1):
                if len(blk) != 3:
                    continue
                deg = [(np.abs(A1[s, blk]) > 1e-12).sum() for s in blk]
                s0 = blk[int(np.argmax(deg))]
                s1, s2 = [s for s in blk if s != s0]
                v1, v2 = A1[s1, s0], A1[s2, s0]
                R = np.array([[v1, v2], [-v2, v1]], dtype=complex) / np.hypot(v1, v2)
                if bright_sign[c]:
                    R = -R
                g += _multiplexed_two_level(s1 ^ s2, [(s1, s2, R)], vset, w)
            jc = qs.index(corner["third"]) if corner["third"] is not None else None
            jq = qs.index(corner["q"])
            if cz_c[c]:
                g.append(("cp", [jc, ja], np.pi))
            if cz_q[c]:
                g.append(("cp", [jq, ja], np.pi))
            if ccz_xc[c]:                                  # (-1)^{p_a (1 - x) c}
                g += [("x", [jb], None)] + ccz(ja, jb, jc) + [("x", [jb], None)]
            fr += [(nm, [qs[q] for q in qq], par) for nm, qq, par in g]
            pa.append(qs[ja])
        return fr, pa

    def labels(s):
        out = []
        for corner in corners:
            x = (s >> gpos[corner["plinks"][1]]) & 1
            cc = (s >> gpos[corner["third"]]) & 1 if corner["third"] is not None else 0
            qq = (s >> gpos[corner["q"]]) & 1
            out.append((x, cc, qq))
        return out

    # ---- 2. sign analysis in the plain frame (+ ladder) and choice of the cheapest corrections
    zero = [0, 0, 0, 0]
    fr0, pa = build_frames(zero, zero, zero)
    has_triple = [any(len(b_) == 3 for b_ in corner_blocks(fac["mats"][c])) for c in range(4)]
    # a corner needs a flag when one of its valid states is annihilated by its corner matrix (a dark state,
    # either the dark member of a three-state block or an isolated valid state)
    def _has_dark(c):
        cp = fac["corner_positions"][c]
        valid = sorted({_sub(int(s_), cp) for s_ in states})
        Mx = fac["mats"][c]
        if has_triple[c]:
            return True
        if flag_rule == "triple":
            return False
        return any(not (np.abs(Mx[v]).any() or np.abs(Mx[:, v]).any()) for v in valid)
    has_dark = [_has_dark(c) for c in range(4)]
    p1 = pa[0]
    ladder = [("cx", [p1, q], None) for q in pa[1:]]
    H2, omega = frame_generator(P, name, fr0 + ladder, contract)
    coo = H2.tocoo()
    t = gpos[p1]
    if np.any((coo.row ^ coo.col) != (1 << t)):
        raise AssertionError("frame generator is not X on p_1 (x) diagonal")
    samples = [(int(cc), float(np.real(v))) for cc, v in zip(coo.col, coo.data) if not (int(cc) >> t) & 1]
    # monomials: free = all x-monomials (16), bright per corner, g per corner, g products are free too but
    # unnecessary here; costed = c_c, q_c
    import itertools as _it
    free_cols, costed_cols = [], []
    def feat(s):
        L = labels(s)
        xs = [l[0] for l in L]
        f = []
        for sub_ in _it.product([0, 1], repeat=4):
            f.append(int(all(xs[i] for i in range(4) if sub_[i])))
        for ci, (x, cc, qq) in enumerate(L):
            # bright label: its sign is free (Ry angle + 2 pi) only where a bright rotation exists
            f.append(int(x == 0 and cc == 1 and qq == 0) if has_triple[ci] else 0)
            f.append(int(cc == 1 and qq == 1) if (has_dark[ci] and use_flags) else 0)   # g flag
        cost = []
        for ci, (x, cc, qq) in enumerate(L):
            third = corners[ci]["third"] is not None
            cost += [cc if third else 0, qq, int(x == 0 and cc == 1) if third else 0]
        return f, cost
    F_free, F_cost, b = [], [], []
    for s, v in samples:
        f, c_ = feat(s)
        F_free.append(f)
        F_cost.append(c_)
        b.append(int(v < 0))
    F_free, F_cost, b = np.array(F_free), np.array(F_cost), np.array(b)
    unit_cost = [1, 1, 5] * 4                       # CZ(c,pa), CZ(q,pa): 1 ZZ; CCZ(pa,~x,c): 3 CP + 2 CX
    choice = None
    for sel_mask in sorted(range(1 << 12), key=lambda m_: (sum(unit_cost[i] for i in range(12) if (m_ >> i) & 1), m_)):
        sel = [i for i in range(12) if (sel_mask >> i) & 1]
        A = np.hstack([F_free, F_cost[:, sel]]) if sel else F_free
        ok, sol = f2_solve(A, b)
        if ok:
            choice = (sel, sol)
            break
    if choice is None:
        raise AssertionError("sign structure not absorbable")
    sel, sol = choice
    nfree = F_free.shape[1]
    bright_sign = [int(sol[16 + 2 * c]) for c in range(4)]
    cz_c, cz_q, ccz_xc = [0] * 4, [0] * 4, [0] * 4
    for i, s_ in enumerate(sel):
        if sol[nfree + i]:
            (cz_c, cz_q, ccz_xc)[s_ % 3][s_ // 3] = 1
    fr, pa = build_frames(bright_sign, cz_c, cz_q, ccz_xc)
    # ---- 3. ladder, then clear redundant qubits (relations on the occupied set)
    frame = fr + ladder
    _, omega = frame_generator(P, name, frame, contract)
    k = len(sup)
    rel = f2_relations(omega, k)
    # pick pivots: prefer the cleared p_a's of corners 1..3, then x of corner 3, never p1
    need = sum(1 for c in range(4) if has_dark[c]) if use_flags else 0
    prefer = [gpos[q] for q in pa[1:]] + [gpos[corners[3]["plinks"][1]]]
    # reduce relations so that each preferred pivot appears in exactly one relation
    rel = list(rel)
    clear = []
    for pv in prefer:
        cand = [r for r in rel if (r >> pv) & 1]
        if not cand:
            continue
        r0 = min(cand, key=lambda r: bin(r).count("1"))
        rel = [r ^ r0 if ((r >> pv) & 1 and r != r0) else r for r in rel if r != r0]
        clear.append((pv, r0))
        if len(clear) == need:
            break
    # constant value of each relation on omega: r . s0
    s0 = int(omega[0])
    clear_gates = []
    for pv, r in clear:
        for b_ in range(k):
            if b_ != pv and (r >> b_) & 1:
                clear_gates.append(("cx", [sup[b_], sup[pv]], None))
        if bin(r & s0).count("1") % 2:
            clear_gates.append(("x", [sup[pv]], None))
    # the clears of later pivots must not use earlier pivots as sources (they are already 0): check
    frame = frame + clear_gates
    _, omega2 = frame_generator(P, name, frame, contract)
    anc = [sup[pv] for pv, _ in clear]
    for a in anc:
        if np.any((omega2 >> gpos[a]) & 1):
            raise AssertionError(f"qubit {a} is not cleared")
    # ---- 4. flags g_c = c_c AND q_c into the clean qubits
    if len(anc) < need:
        raise AssertionError(f"only {len(anc)} clean qubits for {need} flags")
    flags = []
    flag_corners = [c for c in range(4) if has_dark[c]] if use_flags else []
    for c, a in zip(flag_corners, anc):
        flags += (toffoli if exact_toffoli else rtof)(corners[c]["third"], corners[c]["q"], a)
    frame = frame + flags
    H3, omega3 = frame_generator(P, name, frame, contract)
    coo = H3.tocoo()
    if np.any((coo.row ^ coo.col) != (1 << t)):
        raise AssertionError("final frame generator is not X on p_1 (x) diagonal")
    Fval = {int(cc): complex(v) for cc, v in zip(coo.col, coo.data)}
    items = []
    for s0_ in sorted({int(s) & ~(1 << t) for s in omega3}):
        s1_ = s0_ | (1 << t)
        f = Fval.get(s0_, 0.0)
        if abs(f - np.conj(Fval.get(s1_, 0.0))) > 1e-12 or abs(np.imag(f)) > 1e-12:
            raise AssertionError("frame generator is not real symmetric on a pair")
        f = float(np.real(f))
        if f == 0.0:
            continue
        cth, sth = np.cos(theta * f), np.sin(theta * f)
        items.append((s0_, s1_, np.array([[cth, -1j * sth], [-1j * sth, cth]], dtype=complex)))
    stats = []
    # the package's greedy control reduction tries low bit indices first: relabel the support so that
    # the bits the flags were computed from (third link, vertex bit) come first and are dropped first
    first = [gpos[c_["third"]] for c_ in corners if c_["third"] is not None] + [gpos[c_["q"]] for c_ in corners]
    order = first + [b_ for b_ in range(k) if b_ not in first]          # new index i <- old bit order[i]
    core = mux_relabelled(1 << t, items, omega3, k, order, stats)
    core = [(nm, [sup[q] for q in qs], par) for nm, qs, par in core]
    gates = frame + core + invert(frame)
    if return_info:
        return gates, {"has_dark": has_dark, "bright_sign": bright_sign, "cz_c": cz_c, "cz_q": cz_q, "ccz_xc": ccz_xc, "ancillas": anc,
                       "clear_2q": sum(1 for g in clear_gates if g[0] == "cx"),
                       "frame_2q": sum(1 for g in frame if g[0] in ("cx", "cz", "cp", "rzz")),
                       "multiplexer": stats, "n_rotations": len(items)}
    return gates


def _perm_int(s: int, order: list) -> int:
    """New integer whose bit i is old bit order[i]."""
    return sum(((int(s) >> o) & 1) << i for i, o in enumerate(order))


def mux_relabelled(diff: int, items: list, valid, k: int, order: list, stats=None) -> list:
    """`_multiplexed_two_level` in a relabelled bit order; gates returned in the original local labels."""
    items2 = [(_perm_int(a, order), _perm_int(b, order), V) for a, b, V in items]
    valid2 = np.array(sorted(_perm_int(v, order) for v in valid), dtype=np.int64)
    g = _multiplexed_two_level(_perm_int(diff, order), items2, valid2, k, stats=stats)
    return [(nm, [order[q] for q in qs], par) for nm, qs, par in g]
