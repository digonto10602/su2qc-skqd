"""Structure checks of MANUAL §3b on 2x2, 2x3 and 2x4 (read-only for the study; writes only into this folder).

For every term of every lattice:
  * blocks of the local matrix and whether each is bipartite with zero diagonal (skqd.circuits_ir._bipartition);
For every plaquette:
  * the corner factorisation h_P|_C = (x)_c A_c (src/c2x4/plaqfactor.py:factorise): product residual on every row
    and codeword column, magnitude residual;
For every hop (H_hop = T + T^dag, T the n_x-raising part):
  * a REAL product check of T = eta * a_x (x) b_y (x) s_rest on every raising element (the fit of
    src/c2x4/hopframe.py:hop_vertex_factors returns a_x, b_y only; here the third factor s_rest, on the qubits outside
    the two end vertices, is kept and the product is compared with h element by element);
  * whether the JW dependence is a pure parity sign: h[i,j] (-1)^{parity(JW bits)} independent of the JW bits;
  * the equal-step property of each vertex factor: for every n = 0 state s0 with u = R s0 != 0 (R the raising
    factor: a_x, or b_y^T at the lowering end), | ||R u|| / ||u|| - ||u|| |  (zero for an equal-step chain
    0 -> 1 -> 2, the bright combination included).
Writes examples/structure_checks/structure_checks.json.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(STUDY, "src"))
sys.path.insert(0, os.path.join(ROOT, "src"))
import c2x4.env as env                                         # noqa: E402
env.CACHE = os.path.join(HERE, "cache")                        # sandbox (no cache file of data/ is touched)
import c2x4.problem as problem                                 # noqa: E402
problem.CACHE = env.CACHE

import scipy.sparse as sp                                      # noqa: E402
from skqd.circuits_ir import _bipartition                      # noqa: E402
from c2x4.plaqfactor import _sub, corners_of, f2_solve, factorise   # noqa: E402
from c2x4.problem import Problem                               # noqa: E402
from c2x4.reach import components                              # noqa: E402


def blocks(P, nm):
    sup, states, h, pos = P.local(nm)
    h = np.asarray(h)
    A = np.abs(h) > 1e-12
    np.fill_diagonal(A, False)
    lab = components(sp.csr_matrix(h))
    ok, sizes = True, []
    for b in np.unique(lab):
        idx = np.flatnonzero(lab == b)
        sizes.append(len(idx))
        if len(idx) > 1 and (_bipartition(A[np.ix_(idx, idx)]) is None or np.abs(np.diag(h)[idx]).max() > 1e-12):
            ok = False
    return {"blocks": len(sizes), "largest_block": int(max(sizes)), "all_bipartite_zero_diagonal": ok}


def hop_checks(P, nm):
    l = int(nm[3:])
    lat, codec = P.M.lat, P.E.codec
    sup, states, h, pos = P.local(nm)
    h = np.asarray(h)
    x, y, _ = lat.links[l]
    gp = {q: i for i, q in enumerate(sup)}
    parts = []
    for s in (x, y):
        o, w = int(codec.offsets[s]), codec.widths[s]
        parts.append([gp[q] for q in range(o, o + w)])
    parts.append([i for i in range(len(sup)) if i not in parts[0] + parts[1]])
    states = np.array(states)

    def nvert(site, sl, pp):
        return codec.decode_vertex(site, tuple((int(sl) >> p) & 1 for p in pp))[1]
    I, J = np.nonzero(np.abs(h) > 1e-12)
    sel = [e for e, (i, j) in enumerate(zip(I, J)) if nvert(x, states[i], parts[0]) == nvert(x, states[j], parts[0]) + 1]
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
    coef = (-1.0) ** sg.astype(float) * np.exp(xm)
    pred = eta * np.exp(A @ np.log(np.abs(coef))) * (-1.0) ** ((A @ sg.astype(float)) % 2)
    prod_res = float(np.abs(pred - vals).max())
    # JW sign: is h[i, j] (-1)^{parity of the JW bits} independent of the JW bits (direct test on h, the same test
    # hopframe.jwc_framed_gates applies in its frame)?  The fitted third factor is not gauge-unique, so it is not used.
    rest = parts[2]
    jw = {"n_jw_qubits": len(rest)}
    if rest:
        Jmask = sum(1 << j for j in rest)
        keep = [i for i in range(len(sup)) if i not in rest]
        h0, changes, consistent = {}, False, True
        for i_, j_ in zip(I, J):
            si, sj = int(states[i_]), int(states[j_])
            if (si & Jmask) != (sj & Jmask):
                changes = True
            v_ = h[i_, j_] * (-1) ** bin(sj & Jmask).count("1")
            key = (_sub(si, keep), _sub(sj, keep))
            if key in h0 and abs(h0[key] - v_) > 1e-12:
                consistent = False
            h0[key] = v_
        jw.update({"term_changes_jw_bits": changes, "sign_is_jw_parity_times_h0": consistent and not changes})
    # equal-step chains (raising factor of each end vertex)
    eq = []
    for c, site in ((0, x), (1, y)):
        w = len(parts[c])
        R = np.zeros((1 << w, 1 << w))
        for (o, i), q in keys[c].items():
            R[o, i] = coef[off[c] + q]
        if c == 1:
            R = R.T                                  # b_y lowers n_y: its transpose raises
        res = 0.0
        for s0 in range(1 << w):
            try:
                if codec.decode_vertex(site, tuple((s0 >> p) & 1 for p in range(w)))[1] != 0:
                    continue
            except Exception:
                continue
            u = R[:, s0]
            if np.linalg.norm(u) < 1e-12:
                continue
            res = max(res, abs(np.linalg.norm(R @ u) / np.linalg.norm(u) - np.linalg.norm(u)))
        eq.append(res)
    return {"eta": "i" if eta == 1j else "real", "n_raising_elements": len(sel), "signs_factorise": bool(ok),
            "product_residual": prod_res, "magnitude_fit_residual": float(np.abs(A @ xm - np.log(np.abs(v))).max()),
            "jw": jw, "equal_step_residual_x": eq[0], "equal_step_residual_y": eq[1]}


def main():
    t0 = time.time()
    out = {}
    for lx in (2, 3, 4):
        P = Problem(lx)
        row = {"n_qubits": P.n, "dim": int(P.M.basis.dim), "codec_widths": [int(w) for w in P.E.codec.widths],
               "terms": {}}
        for nm in P.term_names():
            r = blocks(P, nm)
            if nm.startswith("plaq"):
                p = int(nm[4:])
                fac = factorise(P, nm, corners_of(P, p))
                r["corner_factorisation"] = {"product_residual_all_rows": fac["product_residual_all_rows"],
                                             "magnitude_residual": fac["magnitude_residual"],
                                             "interior_corners": sum(1 for c in corners_of(P, p) if c["third"] is not None)}
            else:
                r["hop"] = hop_checks(P, nm)
            row["terms"][nm] = r
        terms = row["terms"].values()
        row["summary"] = {
            "all_blocks_bipartite_zero_diagonal": all(t["all_bipartite_zero_diagonal"] for t in terms),
            "max_plaq_product_residual": max(t["corner_factorisation"]["product_residual_all_rows"] for t in terms
                                             if "corner_factorisation" in t),
            "max_hop_product_residual": max(t["hop"]["product_residual"] for t in terms if "hop" in t),
            "all_hop_signs_factorise": all(t["hop"]["signs_factorise"] for t in terms if "hop" in t),
            "max_equal_step_residual": max(max(t["hop"]["equal_step_residual_x"], t["hop"]["equal_step_residual_y"])
                                           for t in terms if "hop" in t),
            "hops_with_jw_qubits": [nm for nm, t in row["terms"].items() if "hop" in t and t["hop"]["jw"]["n_jw_qubits"]],
            "all_jw_signs_are_parity_times_h0": all(t["hop"]["jw"].get("sign_is_jw_parity_times_h0", True)
                                                    for t in terms if "hop" in t)}
        out[f"2x{lx}"] = row
        print(f"2x{lx}", row["summary"], flush=True)
    env.write_json(os.path.join(HERE, "structure_checks.json"), out,
                   produced_by="2x4_compression_using_ai_v1/examples/structure_checks/run_structure_checks.py",
                   parameters={"lattices": [2, 3, 4], "g2": 4.0, "threshold": 1e-12}, t_start=t0)


if __name__ == "__main__":
    main()
