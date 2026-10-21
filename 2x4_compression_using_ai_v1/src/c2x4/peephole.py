"""Exact peephole pass (family F5): cancel pairs of identical CX gates across everything that commutes with
them, and merge consecutive one-qubit rotations of the same axis on the same qubit.

Commutation rules used (each proved in lean/Compress2x4/Peephole.lean in the bit model, for every n):
  R1  gates on disjoint qubits commute with CX(c, t);
  R2  a diagonal gate (rz, p, cp, cz, rzz, gphase) that does not act on the target t commutes with CX(c, t);
  R3  CX(c, t) and CX(c', t') commute when c != t' and c' != t (shared control, or shared target, or disjoint);
  R4  X-type one-qubit gates on the target (x, rx) commute with CX(c, t);
  C1  CX(c, t) CX(c, t) = 1.
Merges: rz(a) rz(b) = rz(a+b), ry(a) ry(b) = ry(a+b), p(a) p(b) = p(a+b) on the same qubit (one-qubit,
not scored, kept for tidiness).
"""
from __future__ import annotations

DIAG = {"rz", "p", "cp", "cz", "rzz", "gphase"}
XTYPE = {"x", "rx"}


def commutes_with_cx(g, c: int, t: int) -> bool:
    nm, qs, _ = g
    if c not in qs and t not in qs:
        return True                                     # R1
    if nm in DIAG and t not in qs:
        return True                                     # R2
    if nm == "cx":
        c2, t2 = qs
        return c2 != t and t2 != c                      # R3
    if nm in XTYPE and qs == [t]:
        return True                                     # R4
    return False


def cancel_cx(gates: list, window: int = 400) -> tuple:
    """One left-to-right sweep; returns (new gate list, number of CX pairs removed)."""
    g = list(gates)
    alive = [True] * len(g)
    removed = 0
    for i, gi in enumerate(g):
        if not alive[i] or gi[0] != "cx":
            continue
        c, t = gi[1]
        steps = 0
        for j in range(i + 1, len(g)):
            if not alive[j]:
                continue
            gj = g[j]
            if gj[0] == "cx" and gj[1] == [c, t]:
                alive[i] = alive[j] = False
                removed += 1
                break
            if not commutes_with_cx(gj, c, t):
                break
            steps += 1
            if steps > window:
                break
    return [x for x, a in zip(g, alive) if a], removed


def merge_1q(gates: list) -> list:
    out = []
    last = {}                                           # qubit -> index in out of its last gate
    for nm, qs, par in gates:
        if nm in ("rz", "ry", "p") and len(qs) == 1:
            q = qs[0]
            k = last.get(q)
            if k is not None and out[k][0] == nm and out[k][1] == qs:
                out[k] = (nm, qs, out[k][2] + par)
                continue
        out.append((nm, qs, par))
        for q in qs:
            last[q] = len(out) - 1
    return out


def optimise(gates: list, rounds: int = 6) -> tuple:
    total = 0
    for _ in range(rounds):
        gates = merge_1q(gates)
        gates, r = cancel_cx(gates)
        total += r
        if r == 0:
            break
    return gates, total


# ------------------------------------------------------------------ C4 step 4: CNOT-run resynthesis (label CXR, mine)
def _cx_matrix(run: list, qs: list):
    import numpy as np
    pos = {q: i for i, q in enumerate(qs)}
    A = np.eye(len(qs), dtype=np.uint8)
    for _nm, (c, t), _p in run:
        A[pos[t]] ^= A[pos[c]]            # row t <- row t xor row c (x_t <- x_t + x_c)
    return A


def _same_permutation(r1: list, r2: list, qs: list) -> bool:
    """Exhaustive check on all 2^|qs| basis labels that two CNOT lists are the same relabelling (Lean:
    Compress2x4.perm_eq_of_fun_eq turns this into equality of the operators)."""
    import numpy as np
    pos = {q: i for i, q in enumerate(qs)}
    s = np.arange(1 << len(qs), dtype=np.int64)

    def run(r):
        v = s.copy()
        for _nm, (c, t), _p in r:
            v ^= ((v >> pos[c]) & 1) << pos[t]
        return v
    return bool(np.array_equal(run(r1), run(r2)))


def _synth_gauss(A, qs: list) -> list:
    """CNOT circuit for the GF(2) matrix A (rows = output bits as functions of input bits) by Gaussian
    elimination: reduce A to the identity with row operations R_i <- R_i + R_j (each one CX(q_j -> q_i)), then the
    circuit is the reversed list."""
    import numpy as np
    M = A.copy()
    n = len(qs)
    ops = []
    for c in range(n):
        if not M[c, c]:
            r = next((r for r in range(c + 1, n) if M[r, c]), None)
            if r is None:
                return None
            M[c] ^= M[r]
            ops.append((r, c))
        for r in range(n):
            if r != c and M[r, c]:
                M[r] ^= M[c]
                ops.append((c, r))
    if not np.array_equal(M, np.eye(n, dtype=np.uint8)):
        return None
    return [("cx", [qs[a], qs[b]], None) for a, b in reversed(ops)]


def resynth_cx_runs(gates: list, min_len: int = 3) -> tuple:
    """Replace every maximal run of consecutive CX gates by a shorter equivalent CNOT circuit when Gaussian
    elimination (on A or on A^T, mirrored) finds one; exact (same GF(2) linear map = same permutation of basis
    states, Lean Compress2x4 bit model: a CNOT network is determined by its linear map)."""
    out, i, saved = [], 0, 0
    n = len(gates)
    while i < n:
        if gates[i][0] != "cx":
            out.append(gates[i])
            i += 1
            continue
        j = i
        while j < n and gates[j][0] == "cx":
            j += 1
        run = gates[i:j]
        if len(run) >= min_len:
            qs = sorted({q for _g, qq, _p in run for q in qq})
            A = _cx_matrix(run, qs)
            best = run
            c1 = _synth_gauss(A, qs)
            if c1 is not None and len(c1) < len(best):
                best = c1
            c2 = _synth_gauss(A.T.copy(), qs)            # A^T circuit, reversed with control/target swapped
            if c2 is not None:
                c2 = [("cx", [t, c], None) for _nm, (c, t), _p in reversed(c2)]
                if len(c2) < len(best):
                    best = c2
            if best is not run:
                assert _same_permutation(run, best, qs), "CX resynthesis changed the permutation"
                saved += len(run) - len(best)
            out += best
        else:
            out += run
        i = j
    return out, saved
