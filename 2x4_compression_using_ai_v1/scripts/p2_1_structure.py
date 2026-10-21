"""P2-1 structure tests (numbers for reports/002): does each term's local generator factorise over vertices?

Plaquettes: h = A_c00 (x) A_c10 (x) A_c11 (x) A_c01 on the local codewords (plaqfactor.factorise): residual of the
log-magnitude fit, residual of the product against h on every codeword column and every one of the 2^k rows,
per-corner block structure (sizes, symmetric/antisymmetric, singular values).
Hops: T = eta a_x (x) b_y (x) s_JW on the entries that raise n_x (h = T + T^dag): fit residuals, phase structure.
Approximate-class diagnostic: the smallest reachable block amplitude per term for three circuits.
Writes data/p2_1_structure.json.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as csg

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.env import write_json                                      # noqa: E402
from c2x4.plaqfactor import _sub, corner_blocks, corners_of, f2_solve, factorise   # noqa: E402
from c2x4.problem import get_problem                                  # noqa: E402
from c2x4.reach import exact_trajectory                               # noqa: E402


def hop_fit(P, l):
    lat, codec = P.M.lat, P.E.codec
    nm = f"hop{l}"
    sup, states, h, pos = P.local(nm)
    x, y, _ = lat.links[l]
    gp = {q: i for i, q in enumerate(sup)}
    parts = []
    for s in (x, y):
        o, w = int(codec.offsets[s]), codec.widths[s]
        parts.append([gp[q] for q in range(o, o + w)])
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
    xm, *_ = np.linalg.lstsq(A, np.log(np.abs(vals)), rcond=None)
    ph = np.angle(vals) / (np.pi / 2)
    q = np.round(ph).astype(int) % 4
    ok, _ = f2_solve(A.astype(np.uint8), (q % 2).astype(np.uint8))
    eta = "i (x-link)" if np.all(q % 2 == 1) else "real (y-link)"
    # with the i removed the remaining sign must factorise too
    sgn = ((q // 1) % 4 >= 2).astype(np.uint8) if eta.startswith("real") else (((q - 1) % 4) // 2).astype(np.uint8)
    ok2, _ = f2_solve(A.astype(np.uint8), sgn)
    return {"support": len(sup), "n_T_elements": len(sel), "n_elements": int(len(I)),
            "parts": [len(p) for p in parts], "magnitude_fit_residual": float(np.abs(A @ xm - np.log(np.abs(vals))).max()),
            "phase_max_offset_from_multiple_of_pi_over_2": float(np.abs(ph - np.round(ph)).max()),
            "eta": eta, "sign_factorises": bool(ok2), "parity_of_phase_factorises": bool(ok)}


def main():
    t0 = time.time()
    P = get_problem()
    out = {"plaquettes": {}, "hops": {}, "block_amplitudes": {}}
    for pidx in range(3):
        nm = f"plaq{pidx}"
        corners = corners_of(P, pidx)
        fac = factorise(P, nm, corners)
        sup, states, h, pos = P.local(nm)
        cdat = []
        for c, corner in enumerate(corners):
            Mx = fac["mats"][c]
            cp = fac["corner_positions"][c]
            valid = sorted({_sub(int(s), cp) for s in states})
            blocks = []
            for b in corner_blocks(Mx):
                sub = Mx[np.ix_(b, b)]
                blocks.append({"states": [format(s, f"0{len(corner['qubits'])}b") for s in b],
                               "symmetric": bool(np.allclose(sub, sub.T)),
                               "antisymmetric": bool(np.allclose(sub, -sub.T)),
                               "singular_values": [float(v) for v in np.linalg.svd(sub, compute_uv=False)]})
            dark = [format(v, f"0{len(corner['qubits'])}b") for v in valid
                    if not (np.abs(Mx[v]).any() or np.abs(Mx[:, v]).any())]
            cdat.append({"key": corner["key"], "site": corner["site"], "qubits": corner["qubits"],
                         "plinks": corner["plinks"], "third": corner["third"], "q": corner["q"],
                         "n_valid": len(valid), "blocks": blocks, "isolated_valid_states": dark})
        out["plaquettes"][nm] = {"n_local_codewords": len(states), "n_elements": fac["n_elements"],
                                 "magnitude_fit_residual": fac["magnitude_residual"],
                                 "product_residual_all_rows": fac["product_residual_all_rows"],
                                 "corners": cdat}
        print(nm, "product residual", fac["product_residual_all_rows"], flush=True)
    for l in range(P.M.lat.n_links):
        out["hops"][f"hop{l}"] = hop_fit(P, l)
        print(f"hop{l}", out["hops"][f"hop{l}"], flush=True)
    cw = P.E.codewords
    for (twoB, ref, k) in ((0, 102, 1), (0, 345, 1), (2, 230, 1), (0, 102, 4)):
        traj = exact_trajectory(P, ref, k)
        row = {}
        for nm in P.names[1:]:
            sup, states, h, pos = P.local(nm)
            A = np.abs(h) > 1e-12
            np.fill_diagonal(A, False)
            _n, lab = csg.connected_components(sp.csr_matrix(A), directed=False)
            phi = traj[nm]
            nz = np.flatnonzero(np.abs(phi) > 0)
            w = (1 << np.arange(len(sup))).astype(np.int64)
            loc = (cw[nz][:, sup].astype(np.int64) * w).sum(axis=1)
            W = {}
            for b, a in zip([lab[pos[int(s)]] for s in loc], np.abs(phi[nz]) ** 2):
                W[int(b)] = W.get(int(b), 0.0) + float(a)
            amps = np.sqrt(np.array(sorted(W.values())))
            row[nm] = {"n_blocks_reached": int(len(amps)), "min_block_amplitude": float(amps[0]),
                       "n_below_1e-8": int((amps < 1e-8).sum()), "n_below_1e-6": int((amps < 1e-6).sum()),
                       "n_below_1e-4": int((amps < 1e-4).sum())}
        out["block_amplitudes"][P.tag(twoB, ref, k)] = row
    write_json("data/p2_1_structure.json", out, produced_by="2x4_compression_using_ai_v1/scripts/p2_1_structure.py",
               parameters={"g2": P.g2, "m": P.m, "dt": P.dt, "fit": "least squares on log|h|, signs over F2"},
               t_start=t0)


if __name__ == "__main__":
    main()
