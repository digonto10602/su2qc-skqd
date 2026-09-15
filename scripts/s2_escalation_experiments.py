#!/usr/bin/env python3
"""
Planner diagnostics for the gate-S2 escalation (prompts/11): two experiments that need no new
physics and bound what compilation and term ablation can gain.

  1. Coupling-map experiment: the structured coarse step (validation/S2.json circuits) transpiled
     at level 3 on all-to-all, heavy-hex (seed sweep), square grid and a line.
  2. Ablation emulation at 2x3: the S1 production-budget recall (2e5 shots per sector, proxy
     fidelity f) when plaquette or diagonal terms are removed from the coarse-step generator.

Writes data/S2_escalation_experiments.json and reports/S2_escalation_analysis.md.
Runtime about 4 minutes on the laptop CPU.
"""
import json
import os
import sys
import time
import warnings

import numpy as np
import scipy.sparse as sp

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import basis_vector, coarse_states, references  # noqa: E402
from skqd.report import ROOT, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import certify, ritz, support_metrics  # noqa: E402

G2 = 4.0


def cz_count(qc, cmap, seed, level=3):
    from qiskit import transpile
    tq = transpile(qc, basis_gates=["rz", "sx", "x", "cz"], coupling_map=cmap, optimization_level=level,
                   seed_transpiler=seed)
    return int(tq.count_ops().get("cz", 0))


def coupling_map_experiment(seeds=8):
    from qiskit.transpiler import CouplingMap
    from skqd import circuits_qiskit as cq
    out, rows = {}, []
    for Lx, hh, grid in ((2, 3, (3, 4)), (3, 5, (4, 5))):
        M = Model(Lx)
        F = CircuitFactory(M, G2)
        n = Codec(M.basis).n_qubits
        dt = M.reference(G2, 0).dt
        circuits = {"coarse step k=1": F.coarse_step(references(M.basis, 0)[0], 1, dt)}
        if Lx == 3:
            circuits["plaq1"] = F.plaq_gates(1, dt, True)
            circuits["hop4"] = F.hop_gates(4, dt)
        for name, gates in circuits.items():
            qc = cq.ir_to_qiskit(gates, n, measure=False)
            a2a = cz_count(qc, None, 7)
            hhx = [cz_count(qc, CouplingMap.from_heavy_hex(hh), s) for s in range(seeds)]
            gr = [cz_count(qc, CouplingMap.from_grid(*grid), s) for s in range(seeds)]
            line = cz_count(qc, CouplingMap.from_line(n), 7)
            key = f"2x{Lx}|{name}"
            out[key] = dict(all_to_all=a2a, heavy_hex_distance=hh, heavy_hex_seed7=hhx[7], heavy_hex_best=min(hhx),
                            heavy_hex_mean=float(np.mean(hhx)), grid=list(grid), grid_best=min(gr),
                            grid_mean=float(np.mean(gr)), line=line, seeds=seeds)
            rows.append([f"2x{Lx}", name, a2a, f"{hhx[7]} / {min(hhx)} / {np.mean(hhx):.0f}",
                         f"{min(gr)} / {np.mean(gr):.0f}", line])
    return out, rows


def ablation_experiment():
    from gate_S1 import emulate
    m = mass_default(G2)
    M = Model(3)
    H = M.H(G2)
    codec = Codec(M.basis)
    cw = codec.all_codewords()
    G = M.terms.groups(G2, m)
    variants = {
        "full (S1 generator)": list(G),
        "no plaq1 (interior-corner plaquette)": [k for k in G if k != "plaq1"],
        "no plaquettes": [k for k in G if not k.startswith("plaq")],
        "no diag": [k for k in G if k != "diag"],
    }
    out, rows = {}, []
    for twoB in (0, 2):
        r = M.reference(G2, twoB, k=4)
        refs = references(M.basis, twoB)
        p = np.zeros(M.basis.dim)
        p[r.indices] = np.abs(r.ground) ** 2
        S999 = np.argsort(p)[::-1][:r.support999]
        for name, keys in variants.items():
            rng = np.random.default_rng(20260914)
            groups = [sp.csr_matrix(G[k]) for k in keys]
            sts = [s for rr in refs for s in coarse_states(groups, basis_vector(M.basis.dim, rr), r.dt, 4)[1:]]
            pmax = np.max(np.array([np.abs(s) ** 2 for s in sts]), axis=0)
            n_reach = int(np.sum(pmax[S999] > 1e-3))
            shots = int(round(2e5 / len(sts)))
            rec = {}
            row = [f"B={twoB // 2}", name, f"{n_reach} of {len(S999)}"]
            for f in (0.2, 0.1):
                acc, rej, B, y = emulate(codec, cw, H, sts, shots, f, rng, twoB, refs)
                res = ritz(H, B)
                met = support_metrics(B, p, 1e-3)
                cert = certify(res, r.E0, float(r.energies[1]))
                inside = bool(cert.weinstein[0] - 1e-12 <= r.E0 <= cert.weinstein[1] + 1e-12)
                rec[f"f={f}"] = dict(recall=met["recall"], size=len(B), err=res.ER - r.E0, yield_=y, E0_in_weinstein=inside)
                row.append(f"{met['recall']:.3f} / {len(B)} / {res.ER - r.E0:.1e} / {'yes' if inside else 'NO'}")
            out[f"B={twoB // 2}|{name}"] = dict(terms=keys, circuits=len(sts), shots_per_circuit=shots, reach=n_reach,
                                                support999=int(len(S999)), **rec)
            rows.append(row)
    return out, rows


def main():
    t0 = time.time()
    cm, cm_rows = coupling_map_experiment()
    ab, ab_rows = ablation_experiment()
    s2 = json.load(open(os.path.join(ROOT, "validation", "S2.json")))["data"]
    yields = {n: {f"eps={e}": (1 - e) ** n for e in (1e-3, 2e-3, 3e-3)} for n in (250, 500, 618, 1000, 1500, 2164, 5477)}
    data = dict(coupling_maps=cm, ablation_2x3=ab, yield_vs_cz=yields, runtime_s=time.time() - t0,
                s2_reference=dict(cz_2x2=s2["2x2"]["per_term_cz"], cz_2x2_routed=s2["2x2"]["per_term_cz_routed"],
                                  cz_2x3=s2["2x3"]["per_term_cz"], cz_2x3_routed=s2["2x3"]["per_term_cz_routed"]))
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "S2_escalation_experiments.json"), "w") as fh:
        json.dump(data, fh, indent=1, default=float)
    yrows = [[n] + [f"{yields[n][k]:.3f}" for k in ("eps=0.001", "eps=0.002", "eps=0.003")] for n in yields]
    write_report("S2_escalation_analysis.md", f"""# Gate S2 escalation — what compilation and term ablation can and cannot gain

Produced by `scripts/s2_escalation_experiments.py` for the planner decision in `prompts/11_S2_planner_decision_20260915.md`;
numbers in `data/S2_escalation_experiments.json`.  {env_block()}  Runtime {data['runtime_s']:.0f} s.

Reference (`validation/S2.json`, exact structured circuits, level 3): 2x2 coarse step {sum(s2['2x2']['per_term_cz'].values())} CZ
all-to-all / {sum(s2['2x2']['per_term_cz_routed'].values())} routed per-term sum (step as one circuit: see S2.json);
2x3 {sum(s2['2x3']['per_term_cz'].values())} / {sum(s2['2x3']['per_term_cz_routed'].values())}.  Budget: 250 (2x2) and 500 (2x3) routed.

## 1. Coupling maps (CZ after transpilation at level 3)

{md_table(["lattice", "circuit", "all-to-all", "heavy-hex seed 7 / best of 8 / mean", "square grid best of 8 / mean", "line"], cm_rows)}

Heavy-hex costs 2.4-2.5x the all-to-all count and a seed sweep recovers only a few percent; a square lattice
(Nighthawk-like, degree 4) costs about 1.8x.  No map brings the exact 2x3 step near 500.

## 2. Term ablation at 2x3 (S1 production budget: 2e5 shots per sector, proxy fidelity f, all references, k = 1..4)

Entries: recall of the 99.9 % support / |B| / E_R - E_0 / exact E_0 inside the Weinstein interval.

{md_table(["sector", "generator", "reachable (p > 1e-3)", "f = 0.2", "f = 0.1"], ab_rows)}

The diagonal terms cost nothing to keep (8 / 20 CZ) and change nothing.  Dropping only the interior-corner plaquette
keeps the S1 criterion (recall >= 0.9 at f = 0.1) in both sectors; dropping both plaquettes fails it in B = 1.

## 3. Clean-shot fraction f = (1 - eps)^N_CZ (manual eq. 5)

{md_table(["N_CZ", "eps = 1e-3", "eps = 2e-3", "eps = 3e-3"], yrows)}
""")
    print(json.dumps({k: v for k, v in cm.items()}, indent=None)[:600])
    print("written data/S2_escalation_experiments.json, reports/S2_escalation_analysis.md")


if __name__ == "__main__":
    main()
