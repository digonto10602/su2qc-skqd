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
