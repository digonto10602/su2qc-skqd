"""The independent evaluator: gate counts, two-qubit depth, exact verification.

Verification is exact (complex128, no magnitude threshold) and never uses the proposer's code:

* `verify_circuit` -- the package bar (prompts/35b R1): the 28-qubit state of the candidate,
  run by the package's exact sparse simulator `skqd.sparse_sim.run_sparse` from |0...0>, read on
  the 37 165 codewords and compared with `Problem.target` (the `krylov.coarse_states` state);
  max |Delta psi| after removing the global phase < 1e-10 and leakage < 1e-9.
* `verify_term_operator` -- term level, on EVERY local codeword at once: the gate list acts on
  the support qubits of the term; we append ceil(log2 N) "index" qubits that carry the column
  label, start from the uniform superposition sum_s |s>|idx(s)>/sqrt(N) over the N local
  codewords, and run the same exact sparse simulator.  By linearity the amplitude on
  |out>|idx(s)> is U[out, s]/sqrt(N), so one run returns every codeword column of the
  candidate's unitary U (rows over all 2^k local strings).  Compared with expm(-i theta h).
"""
from __future__ import annotations

import time

import numpy as np
import scipy.linalg as sla

from . import env  # noqa: F401
from skqd.sparse_sim import SparseState, apply_ir, run_sparse   # noqa: E402

TWO_Q = {"cx", "cz", "cp", "rzz"}
ONE_Q = {"x", "h", "rz", "ry", "rx", "p", "sx", "unitary"}
FREE = {"gphase", "barrier"}

BAR_DEV = 1e-10
BAR_LEAK = 1e-9


def counts(gates: list) -> dict:
    """Two-qubit count (each cx/cz/cp/rzz = one ZZPhase after the package's conversion rule,
    prompts/35b R4), one-qubit count, per-name counts, and the two-qubit depth (longest chain
    of two-qubit gates, one-qubit gates acting as wires -- pytket's depth_2q)."""
    by = {}
    level = {}
    depth2 = 0
    n1 = n2 = 0
    for name, qs, par in gates:
        by[name] = by.get(name, 0) + 1
        if name in TWO_Q:
            if len(qs) != 2:
                raise ValueError(f"{name} on {qs}")
            n2 += 1
            a, b = qs
            lv = max(level.get(a, 0), level.get(b, 0)) + 1
            level[a] = level[b] = lv
            depth2 = max(depth2, lv)
        elif name in ONE_Q:
            if name == "unitary" and len(qs) != 1:
                raise ValueError("multi-qubit 'unitary' has no two-qubit cost: decompose it first")
            n1 += 1
        elif name in FREE:
            continue
        else:
            raise ValueError(f"gate '{name}' is not in the costed gate set")
    return {"n_2q": n2, "n_1q": n1, "depth_2q": depth2, "by_name": by, "n_gates": len(gates)}


def verify_circuit(P, gates: list, twoB: int, ref: int, k: int) -> dict:
    """The package bar on the candidate's own (reference, k)."""
    t0 = time.time()
    st = run_sparse(gates, P.n)
    wall = time.time() - t0
    got = st.dense_on(P.ints)
    tgt = P.target(twoB, ref, k)
    ov = np.vdot(tgt, got)
    phase = np.angle(ov) if abs(ov) > 0 else 0.0
    dev_raw = float(np.abs(got - tgt).max())
    dev = float(np.abs(got * np.exp(-1j * phase) - tgt).max())
    leak = float(1.0 - np.sum(np.abs(got) ** 2))
    return {"twoB": twoB, "reference": ref, "k": k, "theta": P.theta(twoB, k),
            "max_dev_phase_aligned": dev, "max_dev_raw": dev_raw, "global_phase": float(phase),
            "leakage": leak, "norm": st.norm(), "fidelity": float(abs(ov) ** 2),
            "sparse_wall_s": wall, "sparse_max_support": int(st.max_support),
            "pass": bool(dev < BAR_DEV and abs(leak) < BAR_LEAK)}


def term_unitary_columns(gates: list, support: list, local_states: list):
    """Columns U[:, s] of the candidate's unitary on the support, for every local codeword s.
    Returns (rows: dict s -> (out ints array, amplitudes array))."""
    k = len(support)
    N = len(local_states)
    na = max(1, int(np.ceil(np.log2(N))))
    gmap = {q: i for i, q in enumerate(support)}
    loc = []
    for name, qs, par in gates:
        if any(q not in gmap for q in qs):
            raise ValueError(f"gate {name} on {qs} leaves the support {support}")
        loc.append((name, [gmap[q] for q in qs], par))
    idx = np.array([s | (j << k) for j, s in enumerate(local_states)], dtype=np.int64)
    o = np.argsort(idx)
    amp = np.full(N, 1.0 / np.sqrt(N), dtype=complex)
    st = SparseState(k + na, idx=idx[o], amp=amp[o])
    apply_ir(st, loc)
    st.to_sparse()
    col = (st.idx >> k).astype(np.int64)
    out = st.idx & ((1 << k) - 1)
    return col, out, st.amp * np.sqrt(N)


def verify_term_operator(P, name: str, gates: list, theta: float, restrict_to=None) -> dict:
    """Operator check of a term gate list against exp(-i theta h_loc) on the local codewords
    (all of them, or the subset `restrict_to` of local codeword ints = an input contract)."""
    t0 = time.time()
    sup, states, h, pos = P.local(name)
    cols_states = states if restrict_to is None else sorted(int(s) for s in restrict_to)
    U = sla.expm(-1j * theta * h)
    col, out, amp = term_unitary_columns(gates, sup, cols_states)
    states_arr = np.array(states, dtype=np.int64)
    # reference columns
    ref_col = np.array([pos[s] for s in cols_states])
    Uref = U[:, ref_col]                                 # rows: local codewords
    # candidate as dense over codeword rows + leakage per column
    N = len(cols_states)
    got = np.zeros((len(states), N), dtype=complex)
    inrow = np.isin(out, states_arr)
    rows = np.searchsorted(states_arr, out[inrow])
    np.add.at(got, (rows, col[inrow]), amp[inrow])
    leak_cols = np.zeros(N)
    np.add.at(leak_cols, col[~inrow], np.abs(amp[~inrow]) ** 2)
    dev = float(np.abs(got - Uref).max())
    return {"term": name, "theta": theta, "n_columns": N,
            "contract": "all local codewords" if restrict_to is None else "restricted input set",
            "max_dev": dev, "max_leak": float(leak_cols.max()),
            "max_dev_outside_codewords": float(np.sqrt(leak_cols.max())),
            "wall_s": time.time() - t0}
