#!/usr/bin/env python3
"""
Planner check after gate S2D: the operational requirement behind the CZ budget is gate S1's
criterion (recall of the 99.9 % support >= 0.9 with the production budget of 2e5 shots per
sector).  This script re-runs the S1 production emulation at the clean-shot fractions S2D
predicts for the 2x3 all-to-all device (validation/S2D.json: f mean, f with virtual rz) and
below, over three seeds, and evaluates the shot rule in its per-sector (union-support) reading.
Writes data/S2D_recall_at_f.json and reports/S2D_recall_at_predicted_f.md.  Runtime ~3 min.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from gate_S1 import emulate  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import basis_vector, coarse_states, references, term_groups  # noqa: E402
from skqd.report import ROOT, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import certify, poisson_lambda_star, ritz, support_metrics  # noqa: E402


def main():
    t0 = time.time()
    s2d = json.load(open(os.path.join(ROOT, "validation", "S2D.json")))["data"]
    f_pred = s2d["2x3"]["f"]["mean"]
    f_vrz = s2d["2x3"]["f_virtual_rz"]["mean"]
    fs = [0.1, round(f_vrz, 4), round(f_pred, 4), 0.03]
    g2 = 4.0
    m = mass_default(g2)
    M = Model(3)
    H = M.H(g2)
    codec = Codec(M.basis)
    cw = codec.all_codewords()
    groups = term_groups(M.terms, g2, m)
    seeds = [20260914, 1, 2]
    out, rows = {}, []
    lam = poisson_lambda_star(3, 0.95)
    for twoB in (0, 2):
        r = M.reference(g2, twoB, k=4)
        refs = references(M.basis, twoB)
        p = np.zeros(M.basis.dim)
        p[r.indices] = np.abs(r.ground) ** 2
        sts = [s for rr in refs for s in coarse_states(groups, basis_vector(M.basis.dim, rr), r.dt, 4)[1:]]
        shots = int(round(2e5 / len(sts)))
        for f in fs:
            recs, sizes, ys, inside = [], [], [], []
            for seed in seeds:
                rng = np.random.default_rng(seed)
                acc, rej, B, y = emulate(codec, cw, H, sts, shots, f, rng, twoB, refs)
                res = ritz(H, B)
                met = support_metrics(B, p, 1e-3)
                cert = certify(res, r.E0, float(r.energies[1]))
                recs.append(met["recall"]); sizes.append(len(B)); ys.append(y)
                inside.append(bool(cert.weinstein[0] - 1e-12 <= r.E0 <= cert.weinstein[1] + 1e-12))
            y_mean = float(np.mean(ys))
            n_sector_union = int(np.ceil(lam / (1e-3 * y_mean)))
            out[f"B={twoB // 2}|f={f}"] = dict(circuits=len(sts), shots_per_circuit=shots, recall=recs, recall_min=min(recs),
                                              size=sizes, yield_mean=y_mean, E0_in_weinstein=inside,
                                              shot_rule_union_reading_N_sector=n_sector_union)
            rows.append([f"B={twoB // 2}", f, len(sts), shots, " / ".join(f"{x:.3f}" for x in recs), min(recs),
                         "/".join(str(s) for s in sizes), f"{y_mean:.4f}", "yes" if all(inside) else "NO", n_sector_union])
    data = dict(source="validation/S2D.json", f_predicted_2x3=f_pred, f_predicted_2x3_virtual_rz=f_vrz, seeds=seeds,
                lambda_star=lam, p=1e-3, results=out, runtime_s=time.time() - t0)
    with open(os.path.join(ROOT, "data", "S2D_recall_at_f.json"), "w") as fh:
        json.dump(data, fh, indent=1)
    write_report("S2D_recall_at_predicted_f.md", f"""# 2x3 recall at the clean-shot fractions predicted by gate S2D (production budget 2e5 shots per sector)

Produced by `scripts/s2d_recall_at_predicted_f.py`; numbers in `data/S2D_recall_at_f.json`.  {env_block()}  Runtime {data['runtime_s']:.0f} s.

Gate S2D (`validation/S2D.json`) predicts f = {f_pred:.4f} for the exact 2x3 coarse-step circuits on the declared all-to-all
device (eps2 = 1e-3, eps1 = 1e-4, eps_ro = 2e-3), or {f_vrz:.4f} if rz is virtual.  The operational requirement behind the
CZ budget is gate S1's criterion: recall of the 99.9 % support >= 0.9 with 2e5 shots per sector.  This table applies that
criterion at those f (S1 proxy emulation, all references, coarse steps k = 1..4, three seeds).

{md_table(["sector", "f", "circuits", "shots/circuit", "recall (3 seeds)", "min recall", "|B|", "yield", "E0 in Weinstein", "N_sector, shot rule per sector"], rows)}

The last column is the manual's shot rule (a configuration of ideal probability p = 1e-3 seen >= 3 times with 95 %
probability, lambda* = {lam:.3f}) applied to the sector as a whole (the support is the union over circuits), N = lambda*/(p y);
gate S2D applied it per circuit and multiplied by the number of circuits, which is the reading that fails the 2e5 quota.
""")
    print(md_table(["sector", "f", "min recall", "yield", "N_sector union"], [[r[0], r[1], r[5], r[7], r[9]] for r in rows]))


if __name__ == "__main__":
    main()
