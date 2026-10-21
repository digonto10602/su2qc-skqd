"""Planner computation for notes/007 (planner-fable, 2026-10-21): the numbers behind the lower-bound section.

Writes data/planner_bounds_007.json.  Three things, nothing else:

  A  the corner-factor ratio of every plaquette corner (small pair magnitude / large pair magnitude), read
     from data/p2_1_structure.json, and the Walsh support of the product-form angle table
     theta(x) = theta0 * prod_c r_c^{x_c} on the four corner-parity bits (no don't-cares);
  B  the Schmidt rank of the exact coarse states across the mid-ladder cut (qubits 0-13 | 14-27) and the
     number of entangled qubits, with the rigorous (and weak) two-qubit-gate lower bounds they imply:
     n_2q >= ceil(log_4 SR) and n_2q >= ceil(n_entangled / 2);
  C  for each hop term, the largest Schmidt rank of any exact output column across the (vertex x | rest) cut,
     the rigorous lower bound on the operator Schmidt rank of any completion of the term.

Run:  cd 2x4_compression_using_ai_v1 && python scripts/planner_bounds_007.py   (about one minute)
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import scipy.linalg as sla

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from c2x4 import env  # noqa: E402
from c2x4.problem import get_problem  # noqa: E402


def walsh_support(table: np.ndarray, m: int, tol: float = 1e-12) -> int:
    c = np.arange(1 << m)
    S = np.arange(1 << m)
    pc = np.vectorize(lambda v: bin(v).count("1"))
    W = (-1.0) ** pc(c[:, None] & S[None, :])
    a = W.T @ table / (1 << m)
    return int(np.sum(np.abs(a) > tol))


def schmidt_rank_state(psi: np.ndarray, ints: np.ndarray, nA: int, tol: float = 1e-12) -> int:
    """Rank of the coefficient matrix of psi across (low nA bits | high bits)."""
    nz = np.nonzero(np.abs(psi) > 1e-15)[0]
    lo = ints[nz] & ((1 << nA) - 1)
    hi = ints[nz] >> nA
    ulo, ilo = np.unique(lo, return_inverse=True)
    uhi, ihi = np.unique(hi, return_inverse=True)
    M = np.zeros((len(ulo), len(uhi)), dtype=complex)
    M[ilo, ihi] = psi[nz]
    s = np.linalg.svd(M, compute_uv=False)
    return int(np.sum(s > tol * s[0])), len(ulo), len(uhi)


def entangled_qubits(psi: np.ndarray, ints: np.ndarray, n: int) -> int:
    """Qubits whose reduced state is mixed (purity < 1 - 1e-12)."""
    p = np.abs(psi) ** 2
    cnt = 0
    for q in range(n):
        bit = (ints >> q) & 1
        p1 = float(p[bit == 1].sum())
        # purity of the reduced 1-qubit state needs coherences too: rho = Tr_rest |psi><psi|
        rest = ints & ~(1 << q)
        urest, irest = np.unique(rest, return_inverse=True)
        M = np.zeros((2, len(urest)), dtype=complex)
        M[bit, irest] = psi
        rho = M @ M.conj().T
        purity = float(np.real(np.trace(rho @ rho)))
        if purity < 1 - 1e-12:
            cnt += 1
    return cnt


def main():
    t0 = time.time()
    P = get_problem()
    out = {"produced_by": "2x4_compression_using_ai_v1/scripts/planner_bounds_007.py",
           "git_commit": env.git_commit(), "written_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}

    # ---- A: corner ratios and the product-form Walsh support
    with open(os.path.join(env.DATA, "p2_1_structure.json")) as fh:
        S = json.load(fh)
    A = {}
    for pn, p in S["plaquettes"].items():
        corners = {}
        ratios = []
        for c in p["corners"]:
            mags = sorted({round(sv, 10) for b in c["blocks"] for sv in b["singular_values"] if sv > 1e-12})
            r = mags[0] / mags[-1] if len(mags) > 1 else None
            corners[c["key"]] = {"magnitudes": mags, "ratio_small_over_large": r,
                                 "ratio_minus_inv_sqrt2": (None if r is None else r - 1 / np.sqrt(2)),
                                 "n_three_state_blocks": sum(1 for b in c["blocks"] if len(b["states"]) == 3),
                                 "isolated_valid_states": c.get("isolated_valid_states", [])}
            if r is not None:
                ratios.append(r)
        # product-form table on the 4 parity bits: theta(x) = prod_c r_c^{x_c} (signs omitted: a sign per
        # corner is itself a one-mask factor and does not change the support count)
        m = len(ratios)
        table = np.array([np.prod([ratios[c] ** ((x >> c) & 1) for c in range(m)]) for x in range(1 << m)])
        A[pn] = {"corners": corners, "n_distinct_nonzero_magnitudes_of_product": int(len(np.unique(np.round(table, 10)))),
                 "walsh_support_product_form_no_dontcares": walsh_support(table, m), "n_parity_bits": m}
    out["A_plaquette_angle_tables"] = A

    # ---- B: state Schmidt rank across the mid-ladder cut, entangled qubits
    ints = np.asarray(P.ints, dtype=np.int64)
    B = {}
    for twoB, ref, k in [(0, 102, 1), (2, 230, 1), (0, 345, 4), (0, 1338, 5)]:
        psi = P.target(twoB, ref, k)
        sr, nlo, nhi = schmidt_rank_state(psi, ints, 14)
        ne = entangled_qubits(psi, ints, P.n)
        B[P.tag(twoB, ref, k)] = {"schmidt_rank_cut_0_13_vs_14_27": sr, "distinct_left_strings": nlo,
                                  "distinct_right_strings": nhi, "support_size": int(np.sum(np.abs(psi) > 1e-15)),
                                  "bound_log4_SR": int(np.ceil(np.log(sr) / np.log(4))),
                                  "entangled_qubits": ne, "bound_half_entangled": int(np.ceil(ne / 2))}
    out["B_state_bounds"] = B

    # ---- C: per-hop output-column Schmidt rank across (vertex x | rest)
    C = {}
    lat = P.M.lat
    codec = P.E.codec
    for l in range(len(lat.links)):
        name = f"hop{l}"
        sup, states, h, pos = P.local(name)
        x, y, _ = lat.links[l]
        xq = set(range(int(codec.offsets[x]), int(codec.offsets[x]) + int(codec.widths[x])))
        lpos = [i for i, q in enumerate(sup) if q in xq]
        theta = P.theta(0, 1)
        U = sla.expm(-1j * theta * np.asarray(h))
        st = np.asarray(states, dtype=np.int64)
        gpos = {q: i for i, q in enumerate(sup)}
        # local integer of each codeword in `sup` order
        loc = np.array([sum(((s >> q) & 1) << gpos[q] for q in sup) for s in st], dtype=np.int64)
        maskA = sum(1 << i for i in lpos)
        best = 0
        for j in range(U.shape[1]):
            col = U[:, j]
            nz = np.nonzero(np.abs(col) > 1e-12)[0]
            a = loc[nz] & maskA
            b = loc[nz] & ~maskA
            ua, ia = np.unique(a, return_inverse=True)
            ub, ib = np.unique(b, return_inverse=True)
            M = np.zeros((len(ua), len(ub)), dtype=complex)
            M[ia, ib] = col[nz]
            s = np.linalg.svd(M, compute_uv=False)
            best = max(best, int(np.sum(s > 1e-12 * s[0])))
        C[name] = {"support_qubits": len(sup), "n_local_codewords": len(states),
                   "max_output_column_schmidt_rank_x_vs_rest": best,
                   "bound_log4": int(np.ceil(np.log(best) / np.log(4))) if best > 1 else 0}
    out["C_hop_column_bounds"] = C
    out["wall_s"] = time.time() - t0
    with open(os.path.join(env.DATA, "planner_bounds_007.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "A_plaquette_angle_tables"}, indent=1))
    for pn, a in A.items():
        print(pn, {c: (v["magnitudes"], v["ratio_minus_inv_sqrt2"]) for c, v in a["corners"].items()},
              "distinct", a["n_distinct_nonzero_magnitudes_of_product"], "walsh", a["walsh_support_product_form_no_dontcares"])


if __name__ == "__main__":
    main()
