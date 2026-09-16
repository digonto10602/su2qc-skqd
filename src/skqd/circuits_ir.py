"""
Backend-independent circuit description ("IR") of the support-generating
circuits, built from exact local block unitaries of the Hamiltonian terms.
The IR is a list of gates (name, qubits, params):

    ('x',  [q], None)                     Pauli X (state preparation)
    ('h',  [q], None)
    ('rz', [q], angle)                    Rz(angle) = exp(-i angle Z / 2)
    ('p',  [q], angle)                    phase gate diag(1, e^{i angle})
    ('cp', [c, t], angle)                 controlled phase diag(1,1,1,e^{i angle})
    ('cx', [c, t], None)
    ('unitary', qubits, U)                dense 2^k x 2^k unitary, qubits[0] = least significant bit

Everything in this file is executed and verified in numpy (reference_sim.py);
the Qiskit and CUDA-Q modules only translate the IR.

Term gates for exp(-i theta H_gamma), gamma in {diag, hop_l, plaq_P}:
  * diag: exact phases from n_x and j_l read from the codeword bits
      corner:   n = (q1 xor q2) + 2 q3            (valid codewords)
      interior: n = f + 2 q4 (1 - f), f = q1 xor q2 xor q3 (parity of the flux ends)
      electric: (g^2/2) * 3/4 per flux link, applied once, on the 'out' end's flux qubit
  * hop_l: dense local unitary on the support of reference_sim.term_support
  * plaq_P: structured gate at 2x2 (corner-only plaquettes) with a Gray-code
    uniformly controlled Rz; dense local unitary otherwise (only usable for
    statevector simulation when the support has <= 12 qubits; larger supports
    raise NotImplementedError until the S2-b decomposition exists).
    Note: the structured gate equals the dense block unitary on the codeword
    subspace but is NOT the identity on leaked (non-codeword) strings, whereas
    the dense local unitary is; with noise the two differ on leaked states.

Coarse single-step circuit (manual Step 4.3 b): X gates preparing the reference
codeword, then the term gates with theta = k dt in the order diag, hop_0, hop_1,
..., plaq_0, ...  (same order as krylov.term_groups).  First-order Trotter: the
same block repeated k times with theta = dt.

Symbols: theta = angle, dt = Krylov step, k = coarse-step multiplier.
"""
from __future__ import annotations

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.csgraph as csgraph

from .codec import Codec
from .exact import Model, mass_default
from .krylov import references
from .reference_sim import (apply_local, bits_to_int, local_unitary, localize,
                            plaquette_pair_amplitudes, term_support)


# ------------------------------------------------------------ uniformly controlled Rz
def gray(j: int) -> int:
    return j ^ (j >> 1)


def ucr_gray(theta_list: list, controls: list, target: int, axis: str = "z") -> list:
    """Gray-code decomposition of  sum_c |c><c| (x) R_axis(theta_c)  (c = sum_j c_j 2^j over
    `controls` in order) into 2^k rotations on the target and 2^k CNOTs (controls -> target).

    Works for axis 'z' and 'y' (the CNOT anticommutes with the rotation generator on the
    target: X Rz(t) X = Rz(-t), X Ry(t) X = Ry(-t)); axis 'x' is NOT allowed here because
    X commutes with Rx (conjugate an x-rotation to y with fixed single-qubit gates instead).
    With k = 0 the result is a single rotation."""
    assert axis in ("z", "y"), axis
    k = len(controls)
    N = 2 ** k
    theta = np.asarray(theta_list, dtype=float)
    assert len(theta) == N
    if k == 0:
        return [(f"r{axis}", [target], float(theta[0]))]
    M = np.array([[(-1) ** bin(c & gray(j)).count("1") for j in range(N)] for c in range(N)], dtype=float)
    alpha = M.T @ theta / N
    gates = []
    for j in range(N):
        gates.append((f"r{axis}", [target], float(alpha[j])))
        nxt = j + 1
        if nxt == N:
            bit = k - 1
        else:
            bit = (nxt & -nxt).bit_length() - 1  # lowest set bit of j+1 = bit flipped from g_j to g_{j+1}
        gates.append(("cx", [controls[bit], target], None))
    return gates


def ucrz_gray(theta_list: list, controls: list, target: int) -> list:
    """Uniformly controlled Rz (Gray code); kept as the name used by plaq_gates and the tests."""
    return ucr_gray(theta_list, controls, target, axis="z")


# ============================================================ structured term gates
# Exact basic-gate decomposition of exp(-i theta O_loc) for a Hamiltonian term whose local
# block h (reference_sim.localize) connects only a few configurations:
#
#   1. inside a connected block (a chain of at most a handful of configurations) the exact
#      exponential is written as a product of two-level (Givens) rotations between
#      computational basis states, in a schedule shared by every block of the term;
#   2. all two-level rotations of one schedule step that share the qubit-flip pattern d are
#      merged into ONE uniformly controlled rotation: CNOT(t -> q) for the other flipped
#      qubits q compresses the pair onto a single target qubit t, the remaining support
#      qubits select the angle, and the angle is zero wherever the term does nothing;
#   3. the control set is minimised: a control is dropped whenever every pair of local
#      strings it merges either needs the same rotation or is not a codeword (such strings
#      never occur, so the gate may act on them arbitrarily -- it stays unitary and it
#      still maps codewords to codewords, which is what the leakage check tests).
#
# The result equals the dense local unitary on the codeword subspace (tests/test_circuits_ir)
# but consists of {cx, ry, rz, unitary(1 qubit), gphase} only.

_PAULI = (np.eye(2, dtype=complex),
          np.array([[0, 1], [1, 0]], dtype=complex),
          np.array([[0, -1j], [1j, 0]], dtype=complex),
          np.array([[1, 0], [0, -1]], dtype=complex))
_FLIP2 = np.array([[0, 1], [1, 0]], dtype=complex)
_I2 = np.eye(2, dtype=complex)


def _phase_su2(V):
    """V = e^{i delta} W with W in SU(2); returns (delta, W)."""
    det = V[0, 0] * V[1, 1] - V[0, 1] * V[1, 0]
    delta = float(np.angle(det) / 2)
    return delta, V * np.exp(-1j * delta)


def _axis_angle(W):
    """W = cos(t/2) I - i sin(t/2) n.sigma (W in SU(2)); returns (n, t)."""
    c = float(np.real(W[0, 0] + W[1, 1]) / 2)
    c = min(1.0, max(-1.0, c))
    s = np.array([-np.imag(np.trace(_PAULI[k] @ W) / 2) for k in (1, 2, 3)], dtype=float)
    ns = float(np.linalg.norm(s))
    if ns < 1e-13:
        return np.array([0.0, 0.0, 1.0]), 0.0
    return s / ns, 2 * float(np.arctan2(ns, c))


def _basis_change_to_y(n):
    """B with B^dag Y B = n.sigma, so exp(-i t/2 n.sigma) = B^dag Ry(t) B."""
    A = n[0] * _PAULI[1] + n[1] * _PAULI[2] + n[2] * _PAULI[3]
    _, Pa = np.linalg.eigh(A)
    _, Py = np.linalg.eigh(_PAULI[2])
    return Py @ Pa.conj().T


def _zyz(W):
    """W in SU(2) as Rz(b) Ry(g) Rz(a); returns (a, g, b)."""
    if abs(W[1, 0]) < 1e-13:
        ph = float(np.angle(W[1, 1]) - np.angle(W[0, 0]))
        return ph / 2, 0.0, ph / 2
    g = 2 * float(np.arctan2(abs(W[1, 0]), abs(W[0, 0])))
    p = float(np.angle(W[1, 1]))
    m = float(np.angle(W[1, 0]))
    return p - m, g, p + m


def _chain_order(A):
    """Order of a path graph with boolean adjacency A, or None if A is not a path."""
    n = A.shape[0]
    deg = A.sum(axis=1)
    if n == 1:
        return [0]
    if deg.max() > 2 or list(deg).count(1) != 2:
        return None
    start = int(np.where(deg == 1)[0][0])
    order, prev, cur = [start], -1, int(np.where(deg == 1)[0][0])
    while len(order) < n:
        nxt = [j for j in range(n) if A[cur, j] and j != prev]
        if not nxt:
            return None
        prev, cur = cur, nxt[0]
        order.append(cur)
    return order if len(set(order)) == n else None


def _generic_two_level(U, tol=1e-13):
    """Any n x n unitary as two-level ops [(i, j, V)] in CIRCUIT order (first entry acts
    first); V acts in the basis (i, j).  Exact by construction (Givens elimination)."""
    n = U.shape[0]
    if n == 1:
        assert abs(U[0, 0] - 1) < 1e-10, "a 1x1 block must be gauge-fixed to 1"
        return []
    M = np.array(U, dtype=complex)
    ops = []
    for j in range(n - 1):
        for i in range(n - 1, j, -1):
            b = M[i, j]
            if abs(b) < tol:
                continue
            a = M[j, j]
            r = float(np.hypot(abs(a), abs(b)))
            V = np.array([[np.conj(a) / r, np.conj(b) / r], [-b / r, a / r]], dtype=complex)
            M[[j, i], :] = V @ M[[j, i], :]
            ops.append((j, i, V))
    D = np.diag(M).copy()
    circ = []
    for a in range(0, n - 1, 2):
        if abs(D[a] - 1) > tol or abs(D[a + 1] - 1) > tol:
            circ.append((a, a + 1, np.diag([D[a], D[a + 1]]).astype(complex)))
    if n % 2 == 1 and abs(D[n - 1] - 1) > tol:
        circ.append((0, n - 1, np.diag([1.0 + 0j, D[n - 1]])))
    for (j, i, V) in reversed(ops):
        circ.append((j, i, V.conj().T))
    return circ


def _bipartition(A):
    """2-colouring of the block graph, or None if it is not bipartite."""
    n = A.shape[0]
    col = [-1] * n
    col[0] = 0
    stack = [0]
    while stack:
        i = stack.pop()
        for j in range(n):
            if A[i, j]:
                if col[j] == -1:
                    col[j] = 1 - col[i]
                    stack.append(j)
                elif col[j] == col[i]:
                    return None
    if -1 in col:
        return None
    return col


def _real_gauge(states, h):
    """Find a linear functional f (a bit mask over the support) such that the diagonal gauge
    D = diag(i^{f.z}) makes D^dag h D purely imaginary, h = i A with A real antisymmetric.
    Then exp(-i theta h) = D exp(theta A) D^dag with exp(theta A) REAL orthogonal, so every
    two-level rotation of the decomposition is a real rotation and one uniformly controlled
    Ry per schedule step is enough.  Returns (f, A) or None."""
    idx = np.argwhere(np.abs(h) > 1e-12)
    ds = sorted({int(states[i]) ^ int(states[j]) for i, j in idx if i != j})
    if not ds:
        return 0, np.real(np.imag(h))
    if np.abs(np.real(h)).max() < 1e-11:              # already purely imaginary
        return 0, np.real(np.imag(h))
    # solve f . d = 1 (mod 2) for every difference pattern d (Gaussian elimination over F2)
    piv = []
    for d in ds:
        v, r = d, 1
        for (p, pv, pr) in piv:
            if (v >> p) & 1:
                v ^= pv
                r ^= pr
        if v == 0:
            if r:
                return 0, -1j * h            # no such gauge: keep the complex generator
        else:
            piv.append((v.bit_length() - 1, v, r))
    f = 0
    for (p, pv, pr) in sorted(piv):
        if pr ^ (bin(pv & f & ~(1 << p)).count("1") % 2):
            f |= 1 << p
    for d in ds:
        assert bin(f & d).count("1") % 2 == 1
    phi = np.array([bin(f & int(z)).count("1") % 2 for z in states])
    g = (1j) ** (phi[None, :] - phi[:, None])
    h2 = h * g
    if np.abs(np.real(h2)).max() > 1e-11:
        return 0, -1j * h
    return f, np.real(np.imag(h2))


def _gauge_gates(f, k):
    """Circuit for D = diag(i^{f.z}) on the support (local qubit indices)."""
    bits = [q for q in range(k) if (f >> q) & 1]
    if not bits:
        return [], []
    t = bits[0]
    cn = [("cx", [q, t], None) for q in bits[1:]]
    return cn + [("p", [t], np.pi / 2)] + cn[::-1], cn + [("p", [t], -np.pi / 2)] + cn[::-1]


def _block_rounds(A, theta):
    """exp(theta A) (A real antisymmetric = -i h) as a list of ROUNDS of two-level ops; ops
    inside a round act on disjoint pairs and commute.  Every block of the SU(2) Hamiltonian
    is bipartite with a zero diagonal -- a hopping term changes n_x by one, a plaquette flips
    all four link spins -- so A = [[0, K], [-K^T, 0]] in the two-colour basis and, with the
    real singular value decomposition K = U S V^T,

        exp(theta A) = (U + V) . [pair rotations of angle theta s_i] . (U + V)^T,

    i.e. one basis change inside each colour class (a single real two-level rotation when the
    class has two states) and one round of independent two-level rotations between the paired
    states.  For a three-configuration chain this is the Givens-chain construction (|B| = 1,
    one rotation, three rounds); a four-configuration chain of 2x3 also needs three rounds
    instead of the six two-level unitaries of a generic 4x4 unitary."""
    n = A.shape[0]
    if n == 1:
        assert abs(A[0, 0]) < 1e-12, "isolated configuration with a diagonal element"
        return []
    Adj = np.abs(A) > 1e-12
    np.fill_diagonal(Adj, False)
    col = _bipartition(Adj)
    if col is None or np.abs(np.diag(A)).max() > 1e-12:
        return [[op] for op in _generic_two_level(sla.expm(theta * A).astype(complex))]
    ia = [i for i in range(n) if col[i] == 0]
    ib = [i for i in range(n) if col[i] == 1]
    K = A[np.ix_(ia, ib)]
    U, S, Vt = np.linalg.svd(K)
    V = Vt.conj().T.copy()
    U = U.copy()
    for X in (U, V):        # gauge: largest entry of each column real > 0, det = +1 (a proper
        for i in range(X.shape[1]):                      # rotation, so that no reflection --
            j = int(np.argmax(np.abs(X[:, i])))          # which is not a y-rotation -- appears)
            X[:, i] = X[:, i] * (np.conj(X[j, i]) / abs(X[j, i]))
        d = np.linalg.det(X)
        if abs(d - 1) > 1e-9:
            X[:, -1] = X[:, -1] * np.conj(d)
    Bas = np.zeros((n, n), dtype=U.dtype)
    Bas[np.ix_(ia, ia)] = U
    Bas[np.ix_(ib, ib)] = V
    W0 = Bas.conj().T @ sla.expm(theta * A) @ Bas       # decoupled on the singular pairs
    opsU = _generic_two_level(U.conj().T.astype(complex))
    opsV = _generic_two_level(V.conj().T.astype(complex))
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
    rd = []
    chk = np.array(W0, dtype=complex)
    for i in range(min(len(ia), len(ib))):
        pr = [ia[i], ib[i]]
        Mi = W0[np.ix_(pr, pr)].astype(complex)
        chk[np.ix_(pr, pr)] = np.eye(2)
        if np.abs(Mi - np.eye(2)).max() > 1e-14:
            rd.append((ia[i], ib[i], Mi))
    for i in range(min(len(ia), len(ib)), max(len(ia), len(ib))):
        j = ia[i] if len(ia) > len(ib) else ib[i]
        chk[j, j] = 1.0
    assert np.abs(chk - np.eye(n)).max() < 1e-10, "singular-value blocks are not decoupled"
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


# ---------------------------------------------------------- uniformly controlled U(2)
def _uc_phase(deltas, controls):
    """diag(e^{i delta_c}) on the control qubits (c = sum_j c_j 2^j over `controls`)."""
    m = len(controls)
    if m == 0:
        return [] if abs(deltas[0]) < 1e-14 else [("gphase", [], float(deltas[0]))]
    half = 1 << (m - 1)
    d0 = [deltas[2 * r] for r in range(half)]
    d1 = [deltas[2 * r + 1] for r in range(half)]
    gates = ucr_gray([d1[r] - d0[r] for r in range(half)], controls[1:], controls[0], axis="z")
    return gates + _uc_phase([(d0[r] + d1[r]) / 2 for r in range(half)], controls[1:])


def _uc_u2(table, controls, target):
    """sum_c |c><c| (x) table[c] with table[c] a 2x2 unitary on `target`."""
    deltas, Ws = [], []
    for V in table:
        d, W = _phase_su2(np.asarray(V, dtype=complex))
        deltas.append(d)
        Ws.append(W)
    gates = []
    if max(abs(d) for d in deltas) > 1e-13:
        gates += _uc_phase(deltas, controls)
    ref, angles, common = None, [], True
    for W in Ws:
        nvec, t = _axis_angle(W)
        if abs(t) < 1e-13:
            angles.append(0.0)
            continue
        if ref is None:
            ref = nvec
        if np.linalg.norm(nvec - ref) < 1e-8:
            angles.append(t)
        elif np.linalg.norm(nvec + ref) < 1e-8:
            angles.append(-t)
        else:
            common = False
            break
    if common:
        if ref is None:
            return gates
        B = _basis_change_to_y(ref)
        gates.append(("unitary", [target], B))
        gates += ucr_gray(angles, controls, target, axis="y")
        gates.append(("unitary", [target], B.conj().T))
        return gates
    zyz = [_zyz(W) for W in Ws]
    gates += ucr_gray([z[0] for z in zyz], controls, target, axis="z")
    gates += ucr_gray([z[1] for z in zyz], controls, target, axis="y")
    gates += ucr_gray([z[2] for z in zyz], controls, target, axis="z")
    return gates


# ------------------------------------------------------------- multiplexed two-level step
def _pack(z, t):
    return (z & ((1 << t) - 1)) | ((z >> (t + 1)) << t)


def _unpack(s, t):
    return (s & ((1 << t) - 1)) | ((s >> t) << (t + 1))


def _drop_control(mats, free, p):
    """Merge the two halves of the table along control bit p; None if inconsistent."""
    N = len(free) >> 1
    idx = np.arange(N)
    low = idx & ((1 << p) - 1)
    i0 = low | ((idx >> p) << (p + 1))
    i1 = i0 | (1 << p)
    f0, f1 = free[i0], free[i1]
    both = (~f0) & (~f1)
    if np.abs(mats[i0[both]] - mats[i1[both]]).max(initial=0.0) > 1e-9:
        return None
    out = np.where(f0[:, None, None], mats[i1], mats[i0])
    return out, f0 & f1


def _frame_cnot(mats, free, i, j):
    """Relabel the table for a CNOT with control bit i and target bit j (a free change of
    frame for the control qubits, which the term never flips)."""
    z = np.arange(len(free))
    y = np.where((z >> i) & 1, z ^ (1 << j), z)
    return mats[y], free[y]


def _reduce_controls(mats, free, m, max_full=10):
    """Find a maximal set of directions w in F_2^m along which the (partially free) table is
    invariant -- the table then only depends on the quotient, i.e. on m - d control bits.
    Returns (basis of the invariance subspace in reduced echelon form, filled table)."""
    z = np.arange(1 << m)
    cands = [w for w in range(1, 1 << m)] if m <= max_full else \
            [1 << i for i in range(m)] + [(1 << i) | (1 << j) for i in range(m) for j in range(i + 1, m)] + \
            [(1 << i) | (1 << j) | (1 << l) for i in range(m) for j in range(i + 1, m) for l in range(j + 1, m)]
    cands.sort(key=lambda w: (bin(w).count("1"), w))
    basis = []
    for w in cands:
        if any(_in_span(w, basis) for _ in (0,)) and basis and _in_span(w, basis):
            continue
        y = z ^ w
        both = (~free) & (~free[y])
        if np.abs(mats[both] - mats[y[both]]).max(initial=0.0) > 1e-9:
            continue
        # accept: fill the free half from the defined one
        fill = free & (~free[y])
        mats = mats.copy()
        free = free.copy()
        mats[fill] = mats[y[fill]]
        free[fill] = False
        basis.append(w)
    return _echelon(basis, m), mats, free


def _in_span(w, basis):
    for b in sorted(basis, reverse=True):
        p = b.bit_length() - 1
        if (w >> p) & 1:
            w ^= b
    return w == 0


def _echelon(basis, m):
    """Reduced row echelon basis with distinct pivots (highest set bit)."""
    rows = []
    for w in basis:
        for r in rows:
            p = r.bit_length() - 1
            if (w >> p) & 1:
                w ^= r
        if w:
            rows.append(w)
            rows.sort(reverse=True)
    out = []
    for i, r in enumerate(rows):
        for j, r2 in enumerate(rows):
            if i != j:
                p = r2.bit_length() - 1
                if (r >> p) & 1:
                    r ^= r2
        out.append(r)
    return out


def _multiplexed_two_level(diff, items, valid, k, max_targets=3, stats=None):
    """One schedule step: every two-level op in `items` has the same flip pattern `diff`."""
    bits = [q for q in range(k) if (diff >> q) & 1]
    best = None
    for t in bits[:max_targets]:
        rest = diff ^ (1 << t)
        N = 1 << (k - 1)
        mats = np.tile(_I2, (N, 1, 1))
        free = np.ones(N, dtype=bool)
        for (a, b, V) in items:
            za = a ^ rest if (a >> t) & 1 else a
            zb = b ^ rest if (b >> t) & 1 else b
            assert za ^ zb == (1 << t), "flip pattern does not compress to one qubit"
            V = np.asarray(V, dtype=complex)
            if (za >> t) & 1:
                za, zb = zb, za
                V = _FLIP2 @ V @ _FLIP2
            slot = _pack(za, t)
            mats[slot] = V
            free[slot] = False
        # a slot that contains a codeword must be left alone unless it carries an op
        sl = np.arange(N)
        z0 = (sl & ((1 << t) - 1)) | ((sl >> t) << (t + 1))
        z1 = z0 | (1 << t)
        s0 = np.where((z0 >> t) & 1, z0 ^ rest, z0)
        s1 = np.where((z1 >> t) & 1, z1 ^ rest, z1)
        free &= ~(np.isin(s0, valid) | np.isin(s1, valid))
        ctrl = [q for q in range(k) if q != t]
        m = k - 1
        basis, mats2, free2 = _reduce_controls(mats, free, m)
        # realise the quotient: CNOT(pivot -> q) for every other bit of each basis vector
        frame = []
        for w in basis:
            p = w.bit_length() - 1
            for q in range(m):
                if q != p and ((w >> q) & 1):
                    frame.append((ctrl[p], ctrl[q]))
        keep = [i for i in range(m) if i not in [w.bit_length() - 1 for w in basis]]
        # apply the frame to the table, then drop the pivot bits
        for (a, b) in frame:
            i, j = ctrl.index(a), ctrl.index(b)
            mats2, free2 = _frame_cnot(mats2, free2, i, j)
        idx = np.zeros(1 << len(keep), dtype=np.int64)
        for bit, q in enumerate(keep):
            idx |= ((np.arange(1 << len(keep)) >> bit) & 1) << q
        mats2 = mats2[idx]
        cost = (1 << len(keep)) + 2 * len(frame)
        if best is None or cost < best[0]:
            best = (cost, t, rest, [ctrl[q] for q in keep], mats2, frame)
    _, t, rest, ctrl, mats, frame = best
    if stats is not None:
        stats.append({"flip_pattern": int(diff), "target": int(t), "n_controls": len(ctrl),
                      "n_rotations": len(items), "frame_cnots": len(frame)})
    comp = [("cx", [t, q], None) for q in range(k) if (rest >> q) & 1]
    fr = [("cx", [a, b], None) for a, b in frame]
    return comp + fr + _uc_u2(list(mats), ctrl, t) + fr[::-1] + comp


def _fixed_angle_rotations(states, Aop, theta, valid, k, stats=None):
    """`angle_mode="fixed"`: one rotation per qubit-flip pattern instead of one per
    (schedule round x flip pattern), with ONE angle for all the pairs it merges.

    The pairs are exactly the pairs of codewords connected by the generator (the same
    two-level rotations as the exact mode uses, minus the basis-change rotations inside a
    colour class, which are an artefact of diagonalising the block); the controls that are
    left only select which pairs move (validity), not the angle.  With all elements of one
    flip pattern set to the same magnitude the generator splits, pattern by pattern, into
    disjoint commuting pairs, so exp of each pattern is EXACTLY one round of two-level
    rotations -- there is nothing left to Trotterise inside a pattern.

    This is NOT exp(-i theta O_loc): it is the same gauge-invariant support generator with
    theta_eff = theta x (mean of the distinct |elements| merged into the rotation) and the
    original sign of every element.  SKQD only needs the circuits to generate the support
    (the classical step diagonalises the exact H on it), so the recall criterion of gate S1
    has to be re-established by emulation -- see prompts/11 and validation/S2_fixed.json."""
    if np.abs(np.imag(np.asarray(Aop))).max() > 1e-11:
        raise NotImplementedError("angle_mode='fixed' needs the real gauge of _real_gauge")
    A = np.real(np.asarray(Aop))
    groups = {}
    for i, j in zip(*np.nonzero(np.triu(np.abs(A) > 1e-12, 1))):
        groups.setdefault(int(states[i]) ^ int(states[j]), []).append((int(i), int(j), float(A[i, j])))
    out = []
    for d in sorted(groups):
        items = groups[d]
        mags = sorted({round(abs(a), 12) for (_, _, a) in items})
        mbar = float(np.mean(mags))
        ops = []
        for (i, j, a) in items:
            x = theta * mbar * (1.0 if a > 0 else -1.0)
            V = np.array([[np.cos(x), np.sin(x)], [-np.sin(x), np.cos(x)]], dtype=complex)
            ops.append((int(states[i]), int(states[j]), V))
        out += _multiplexed_two_level(d, ops, valid, k, stats=stats)
        if stats is not None:
            stats[-1].update(merged_elements=[float(m) for m in mags], mean_element=mbar,
                             theta_eff=float(theta * mbar), n_pairs=len(items))
    return out


def structured_term_gates(model: Model, O, support: list, theta: float, stats: list | None = None,
                          angle_mode: str = "exact") -> list:
    """Basic-gate IR for exp(-i theta O_loc) on `support` (global qubit indices).
    `angle_mode="exact"` (default) reproduces the local exponential to machine precision;
    `angle_mode="fixed"` keeps the same codeword pairs and the same validity controls but
    uses one angle per flip pattern (see _fixed_angle_rotations) -- a cheaper generator, not
    the exponential.  Both map codewords to codewords exactly.
    `stats`, if a list, receives one entry per multiplexed rotation (flip pattern, target,
    number of controls after the minimisation, number of two-level rotations it merges)."""
    assert angle_mode in ("exact", "fixed"), angle_mode
    states, h, pos = localize(model, O, support)
    k = len(support)
    A = np.abs(h) > 1e-12
    np.fill_diagonal(A, False)
    ncomp, lab = csgraph.connected_components(sp.csr_matrix(A), directed=False)
    valid = np.array(sorted(int(s) for s in states), dtype=np.int64)
    f, Aop = _real_gauge(states, h)
    pre, post = _gauge_gates(f, k)
    if angle_mode == "fixed":
        out = _fixed_angle_rotations(states, Aop, theta, valid, k, stats)
        out = post + out + pre
        return [(nm, [support[q] for q in qs], par) for nm, qs, par in out]
    blocks = []
    for c in range(ncomp):
        idx = np.where(lab == c)[0]
        rounds = _block_rounds(Aop[np.ix_(idx, idx)], theta)
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
    out = post + out + pre                       # exp(-i theta h) = D exp(theta A) D^dag
    return [(nm, [support[q] for q in qs], par) for nm, qs, par in out]

# ---------------------------------------------------------------------- term gates
class CircuitFactory:
    def __init__(self, model: Model, g2: float, m: float | None = None, structured_hopping: bool = True,
                 angle_mode: str = "exact"):
        assert angle_mode in ("exact", "fixed"), angle_mode
        self.model = model
        self.g2 = g2
        self.m = mass_default(g2) if m is None else m
        self.codec = Codec(model.basis)
        self.n = self.codec.n_qubits
        self.lat = model.lat
        self.ends = self.lat.ends()
        self.structured_hopping = structured_hopping
        self.angle_mode = angle_mode        # "exact" = exp(-i theta H_gamma); "fixed" = one angle
        self.fixed_stats = {}               # per rotation of the fixed-angle circuits (term -> stats)
        self._hop_cache = {}
        self._struct_cache = {}

    def _structured(self, name, O, sup, theta):
        key = (name, round(theta, 12), self.angle_mode)
        if key not in self._struct_cache:
            st = []
            self._struct_cache[key] = structured_term_gates(self.model, O, sup, theta, stats=st,
                                                            angle_mode=self.angle_mode)
            self.fixed_stats[(name, round(theta, 12))] = st
        return self._struct_cache[key]

    # ----- state preparation
    def prepare(self, basis_index: int) -> list:
        bits = self.codec.encode(self.model.basis.labels[basis_index])
        return [("x", [q], None) for q, b in enumerate(bits) if b]

    # ----- diagonal term
    def diag_gates(self, theta: float) -> list:
        gates = []
        lat, codec = self.lat, self.codec
        for s in range(lat.n_sites):
            o = codec.offsets[s]
            sgn = 1.0 if lat.parity(s) == 0 else -1.0
            phi = theta * self.m * sgn                     # exp(-i phi n_x)
            k = len(self.ends[s])
            if k == 2 and not lat.is_static(s):
                q1, q2, q3 = o, o + 1, o + 2
                gates += [("cx", [q1, q2], None), ("p", [q2], -phi), ("cx", [q1, q2], None), ("p", [q3], -2 * phi)]
            elif k == 3 and not lat.is_static(s):
                q1, q2, q3, q4 = o, o + 1, o + 2, o + 3
                # parity f into q3, then exp(-i phi f) exp(-2 i phi q4 (1-f))
                gates += [("cx", [q1, q3], None), ("cx", [q2, q3], None),
                          ("p", [q3], -phi), ("p", [q4], -2 * phi), ("cp", [q3, q4], 2 * phi),
                          ("cx", [q2, q3], None), ("cx", [q1, q3], None)]
            else:
                raise NotImplementedError("diagonal gates for charged vertices: use the dense diagonal unitary")
        # electric term on the 'out' end of each link
        for l, (x, y, _) in enumerate(lat.links):
            pos = [ll for ll, _ in self.ends[x]].index(l)
            q = codec.offsets[x] + pos
            gates.append(("p", [q], -theta * self.g2 * 0.375))
        return gates

    # ----- hopping terms
    def hop_gates_dense(self, l: int, theta: float) -> list:
        """The exact local block unitary as one dense `unitary` gate (the L3 baseline)."""
        sup = term_support(self.model, "hop", l)
        key = (l, round(theta, 12))
        if key not in self._hop_cache:
            self._hop_cache[key] = local_unitary(self.model, self.model.terms.hop[l], sup, theta)
        return [("unitary", sup, self._hop_cache[key])]

    def hop_gates_structured(self, l: int, theta: float) -> list:
        """Controlled-Givens-chain decomposition of exp(-i theta H_hop_l) (gate S2); with
        angle_mode="fixed" the same pairs with one angle per flip pattern (prompts/11)."""
        return self._structured(f"hop{l}", self.model.terms.hop[l],
                                term_support(self.model, "hop", l), theta)

    def hop_gates(self, l: int, theta: float) -> list:
        if self.structured_hopping:
            return self.hop_gates_structured(l, theta)
        return self.hop_gates_dense(l, theta)

    # ----- plaquette terms
    def plaq_gates(self, P: int, theta: float, structured: bool = True) -> list:
        pl = self.lat.plaquettes[P]
        corners = [pl["c00"], pl["c10"], pl["c11"], pl["c01"]]
        if structured and all(self.codec.widths[s] == 3 for s in corners):
            table = plaquette_pair_amplitudes(self.model, P)
            q1 = [self.codec.offsets[s] for s in corners]
            q2 = [self.codec.offsets[s] + 1 for s in corners]
            gates = [("cx", [a, b], None) for a, b in zip(q1, q2)]
            gates += [("h", [a], None) for a in q1]
            gates += [("cx", [a, b], None) for a, b in zip(q1[:-1], q1[1:])]
            mags, mbar = [], 0.0
            if self.angle_mode == "fixed":
                # same pair rotation, one magnitude for every corner-parity class that moves
                # (zero stays zero: those strings are not connected by the plaquette)
                mags = sorted({round(abs(v), 12) for v in table.values() if abs(v) > 1e-12})
                mbar = float(np.mean(mags)) if mags else 0.0
                self.fixed_stats[(f"plaq{P}", round(theta, 12))] = [
                    {"flip_pattern": None, "target": int(q1[-1]), "n_controls": len(q2),
                     "n_rotations": int(sum(1 for v in table.values() if abs(v) > 1e-12)),
                     "frame_cnots": 0, "merged_elements": [float(m) for m in mags],
                     "mean_element": mbar, "theta_eff": float(theta * mbar / self.g2),
                     "n_pairs": int(sum(1 for v in table.values() if abs(v) > 1e-12))}]
            angles = []
            for c in range(16):
                p = tuple((c >> j) & 1 for j in range(4))
                w = table.get(p, 0.0)
                if self.angle_mode == "fixed" and abs(w) > 1e-12:
                    w = mbar if w > 0 else -mbar
                angles.append(-theta * w / self.g2)
            gates += ucrz_gray(angles, q2, q1[-1])
            gates += [("cx", [a, b], None) for a, b in reversed(list(zip(q1[:-1], q1[1:])))]
            gates += [("h", [a], None) for a in q1]
            gates += [("cx", [a, b], None) for a, b in zip(q1, q2)]
            return gates
        sup = term_support(self.model, "plaq", P)
        O = -self.model.terms.plaq[P] / (2 * self.g2)
        if structured:
            # interior corners (2x3 and larger): the generic controlled-Givens-chain gates
            # (the corner-only case above keeps its dedicated pair-rotation gate, which gate
            # CS verifies; structured_term_gates would give 22 CX there instead of 30)
            return self._structured(f"plaq{P}", O, sup, theta)
        if len(sup) > 12:
            raise NotImplementedError(
                f"plaquette {P} acts on {len(sup)} qubits (interior corners): the dense local unitary would need "
                f"{(2 ** len(sup)) ** 2 * 16 / 2 ** 30:.1f} GiB; use the structured gates (structured=True).")
        U = local_unitary(self.model, O, sup, theta)
        return [("unitary", sup, U)]

    # ----- circuits
    def coarse_step(self, ref_index: int, k: int, dt: float, structured_plaquette=True) -> list:
        theta = k * dt
        gates = self.prepare(ref_index)
        if k == 0:
            return gates
        gates += self.diag_gates(theta)
        for l in range(self.lat.n_links):
            gates += self.hop_gates(l, theta)
        for P in range(len(self.lat.plaquettes)):
            gates += self.plaq_gates(P, theta, structured_plaquette)
        return gates

    def trotter(self, ref_index: int, steps: int, dt: float, structured_plaquette=True) -> list:
        gates = self.prepare(ref_index)
        for _ in range(steps):
            gates += self.diag_gates(dt)
            for l in range(self.lat.n_links):
                gates += self.hop_gates(l, dt)
            for P in range(len(self.lat.plaquettes)):
                gates += self.plaq_gates(P, dt, structured_plaquette)
        return gates

    def circuit_set(self, twoB: int, dt: float, kmax: int = 4) -> dict:
        """{(ref index, k): gate list} for all references of the sector and k = 1..kmax."""
        out = {}
        for r in references(self.model.basis, twoB):
            for k in range(1, kmax + 1):
                out[(r, k)] = self.coarse_step(r, k, dt)
        return out


# ------------------------------------------------------------------ numpy execution
def _two_bit_view(state, a, b):
    """state viewed as (rest, bit max(a,b), middle, bit min(a,b), low) -- an in-place view."""
    hi, lo = max(a, b), min(a, b)
    return state.reshape(-1, 2, 1 << (hi - lo - 1), 2, 1 << lo), (hi == a)


def run_ir(gates: list, n: int, state: np.ndarray | None = None) -> np.ndarray:
    """Statevector simulation of an IR gate list (qubit 0 = least significant bit).

    Permutation gates (x, cx) and diagonal gates (rz, p, cp) are applied in place on
    strided views -- the same operation as apply_local (tests/test_circuits_ir checks the
    two against each other), three to five times faster on the 2^20 statevectors of 2x3."""
    if state is None:
        state = np.zeros(2 ** n, dtype=complex)
        state[0] = 1.0
    else:
        state = np.array(state, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    CX = np.array([[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0]], dtype=complex)
    for name, qs, par in gates:
        if name == "x":
            v = state.reshape(-1, 2, 1 << qs[0])
            tmp = v[:, 0, :].copy()
            v[:, 0, :] = v[:, 1, :]
            v[:, 1, :] = tmp
        elif name == "cx":
            c, t = qs
            v, c_is_hi = _two_bit_view(state, c, t)
            s0 = (slice(None), 1, slice(None), 0, slice(None)) if c_is_hi else \
                 (slice(None), 0, slice(None), 1, slice(None))
            s1 = (slice(None), 1, slice(None), 1, slice(None))
            tmp = v[s0].copy()
            v[s0] = v[s1]
            v[s1] = tmp
        elif name == "p":
            v = state.reshape(-1, 2, 1 << qs[0])
            v[:, 1, :] *= np.exp(1j * par)
        elif name == "cp":
            v, _ = _two_bit_view(state, qs[0], qs[1])
            v[:, 1, :, 1, :] *= np.exp(1j * par)
        elif name == "rz":
            v = state.reshape(-1, 2, 1 << qs[0])
            v[:, 0, :] *= np.exp(-1j * par / 2)
            v[:, 1, :] *= np.exp(1j * par / 2)
        elif name == "h":
            state = apply_local(state, H, qs, n)
        elif name == "ry":
            c, s_ = np.cos(par / 2), np.sin(par / 2)
            state = apply_local(state, np.array([[c, -s_], [s_, c]], dtype=complex), qs, n)
        elif name == "rx":
            c, s_ = np.cos(par / 2), np.sin(par / 2)
            state = apply_local(state, np.array([[c, -1j * s_], [-1j * s_, c]], dtype=complex), qs, n)
        elif name == "gphase":
            state = state * np.exp(1j * par)
        elif name == "unitary":
            state = apply_local(state, par, qs, n)
        elif name == "mcu":
            U2, cstate = par
            U2 = np.asarray(U2, dtype=complex)
            ctrls, t = list(qs[:-1]), qs[-1]
            idx = np.arange(2 ** n)
            mask = ((idx >> t) & 1) == 0
            for j, c in enumerate(ctrls):
                mask &= (((idx >> c) & 1) == ((cstate >> j) & 1))
            i0 = idx[mask]
            i1 = i0 | (1 << t)
            a, b = state[i0].copy(), state[i1].copy()
            state = state.copy()
            state[i0] = U2[0, 0] * a + U2[0, 1] * b
            state[i1] = U2[1, 0] * a + U2[1, 1] * b
        else:
            raise ValueError(name)
    return state


def gate_counts(gates: list) -> dict:
    out = {}
    for name, qs, _ in gates:
        key = name if name not in ("unitary", "mcu") else f"{name}{len(qs)}q"
        out[key] = out.get(key, 0) + 1
    return out
