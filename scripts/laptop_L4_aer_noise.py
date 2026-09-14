#!/usr/bin/env python3
"""
Laptop gate L4 (= gate S3 preparation) — Aer noise-model sampling of the 2x2
coarse-step circuits, decoding, yield, support recall and Ritz error, compared
with the proxy prediction of the manual (yield ~ 0.82 f, f = (1 - eps)^N_CZ).

The 30-minute rule: the script measures the time of a small pilot (1000 shots of
one circuit) and scales the shots per circuit so that the whole run fits the
--budget-minutes (default 25); the chosen shots are recorded in the report
together with what a bigger machine would allow.

Usage: python scripts/laptop_L4_aer_noise.py [--p2 3e-3] [--p1 3e-4] [--pro 0.01]
                                             [--budget-minutes 25] [--gpu]
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import certify, ritz, support_metrics  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p2", type=float, default=3e-3)
    ap.add_argument("--p1", type=float, default=3e-4)
    ap.add_argument("--pro", type=float, default=0.01)
    ap.add_argument("--budget-minutes", type=float, default=25.0)
    ap.add_argument("--gpu", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    R = GateResult("L4", "Aer noise-model sampling at 2x2 (S3 preparation)")
    from skqd import circuits_qiskit as cq
    device = "GPU" if args.gpu else "CPU"
    g2 = 4.0
    M = Model(2)
    F = CircuitFactory(M, g2)
    codec = Codec(M.basis)
    n = codec.n_qubits
    nm = cq.generic_noise_model(args.p1, args.p2, args.pro)
    rows = []
    for twoB in (0, 2):
        ref = M.reference(g2, twoB)
        refs = references(M.basis, twoB)
        circuits = [(r, k, F.coarse_step(r, k, ref.dt)) for r in refs for k in (1, 2, 3, 4)]
        # pilot timing -> shots per circuit within the budget
        tp = time.time()
        cq.sample(circuits[0][2], n, 1000, noise_model=nm, device=device)
        t_per_shot = (time.time() - tp) / 1000
        budget_s = args.budget_minutes * 60 / 2  # half the budget per sector
        shots = int(min(20000, max(500, budget_s / (t_per_shot * len(circuits)))))
        prob = np.zeros(M.basis.dim)
        prob[ref.indices] = np.abs(ref.ground) ** 2
        acc_all, rej_all, total = {}, {}, 0
        cz_counts = []
        for r, k, g in circuits:
            counts = cq.sample(g, n, shots, noise_model=nm, device=device)
            acc, rej = codec.decode_counts(counts, target_twoB=twoB)
            for kk, c in acc.items():
                acc_all[kk] = acc_all.get(kk, 0) + c
            for kk, c in rej.items():
                rej_all[kk] = rej_all.get(kk, 0) + c
            total += shots
        cz = cq.transpile_counts(circuits[0][2], n, optimization_level=1)["cz"]
        f_model = (1 - args.p2) ** cz
        y = sum(acc_all.values()) / total
        B = np.array(sorted(set(acc_all) | set(refs)))
        res = ritz(M.H(g2), B)
        met = support_metrics(B, prob, 1e-3)
        cert = certify(res, ref.E0, float(ref.energies[1]))
        rows.append([f"B={twoB // 2}", len(circuits), shots, cz, f"{f_model:.3f}", f"{0.82 * f_model:.3f}", f"{y:.3f}", len(B),
                     f"{res.ER - ref.E0:.1e}", f"{met['recall']:.2f}", met["false_positives"],
                     f"[{cert.weinstein[0]:.4f}, {cert.weinstein[1]:.4f}]", str(rej_all)])
        R.add(f"B={twoB // 2}: measured yield within a factor 3 of the proxy 0.82 f (f = (1-p2)^CZ)", f"{y:.3f} vs {0.82 * f_model:.3f}",
              "ratio in [1/3, 3] (the proxy is a rough model)", (0.82 * f_model) / 3 <= y <= 3 * (0.82 * f_model) + 1e-9)
        R.add(f"B={twoB // 2}: exact E0 inside the Weinstein interval", f"{ref.E0:.4f}", "inside",
              cert.weinstein[0] - 1e-9 <= ref.E0 <= cert.weinstein[1] + 1e-9)
        R.data[f"B={twoB // 2}"] = dict(shots=shots, circuits=len(circuits), cz=cz, yield_=y, size=len(B), err=res.ER - ref.E0,
                                       recall=met["recall"], t_per_shot=t_per_shot)
    R.runtime_s = time.time() - t0
    R.save()
    write_report("L4_aer_noise.md", f"""# Laptop gate L4 — Aer noise-model sampling at 2x2 (S3 preparation)

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/laptop_L4_aer_noise.py`, p1 = {args.p1}, p2 = {args.p2}, readout {args.pro},
device {device}, budget {args.budget_minutes} min.  {env_block()}  Runtime {R.runtime_s:.0f} s.

{md_table(["sector", "circuits", "shots/circuit", "CZ (level 1)", "f=(1-p2)^CZ", "0.82 f", "measured yield", "|B|",
           "E_R − E_0", "recall 99.9%", "fp", "Weinstein", "rejections"], rows)}

{R.criteria_table()}

Note: at 2x2 the sectors saturate (38 and 20 states), so the Ritz error is a consistency check only (manual
Step 9.1).  A real S3 run replaces `generic_noise_model` by `NoiseModel.from_backend(backend)` built from the
target device's calibration and uses the 2x3 circuits once the plaquette gate with interior corners exists (S2-b).
""")
    print(R.criteria_table())
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
