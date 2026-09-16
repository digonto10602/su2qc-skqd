#!/usr/bin/env python3
"""
Step 3 of prompts/11 — does the fixed-angle generator still generate the support?

For one 2x3 sector and one angle mode it builds the coarse-step circuits of EVERY reference
and k = 1..4 with `skqd.circuits_ir.run_ir` on the full 2^20 statevector, projects them onto
the dressed basis with `reference_sim.CodewordEmbedding`, and runs the gate-S1 production
emulation on them (`gate_S1.emulate`, 2e5 shots per sector, proxy fidelity f = 0.2 and 0.1,
seed 20260914) exactly as `scripts/s2_escalation_experiments.py` does for the ablations.

  python scripts/s2_fixed_recall.py --mode fixed --sector 0     (B = 0, 8 references x 4 = 32 circuits)
  python scripts/s2_fixed_recall.py --mode exact --sector 2     (consistency check: must reproduce S1)

`--mode exact` is the control: the exact structured circuits go through the same route, so
the recall it produces must be the gate-S1 number (1.000 at f = 0.1, |B| = 347 in B = 0 and
246 in B = 1); its per-circuit deviation from `krylov.coarse_states` is recorded too.

One sector takes about 40 s per circuit on the laptop CPU (2^20 amplitudes, ~4400 IR gates):
about 22 min for B = 0 and 9 min for B = 1, inside the 30-minute rule.  Each run writes
data/S2_fixed_recall_<mode>_B<b>.json and merges all fragments into data/S2_fixed_recall.json,
which `scripts/gate_S2.py --angle-mode fixed --out S2_fixed` folds into validation/S2_fixed.json.
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from skqd.circuits_ir import CircuitFactory, run_ir  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import basis_vector, coarse_states, references, term_groups  # noqa: E402
from skqd.reference_sim import CodewordEmbedding  # noqa: E402
from skqd.report import ROOT  # noqa: E402
from skqd.skqd import certify, ritz, support_metrics  # noqa: E402

G2 = 4.0
SEED = 20260914


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="fixed", choices=("exact", "fixed"))
    ap.add_argument("--sector", type=int, default=0, choices=(0, 2), help="2B (0 = B=0, 2 = B=1)")
    ap.add_argument("--shots", type=float, default=2e5, help="total shots per sector")
    ap.add_argument("--kmax", type=int, default=4)
    args = ap.parse_args()
    from gate_S1 import emulate

    t0 = time.time()
    twoB = args.sector
    M = Model(3)
    H = M.H(G2)
    codec = Codec(M.basis)
    cw = codec.all_codewords()
    E = CodewordEmbedding(M)
    F = CircuitFactory(M, G2, angle_mode=args.mode)
    r = M.reference(G2, twoB, k=4)
    refs = references(M.basis, twoB)
    groups = term_groups(M.terms, G2, mass_default(G2))

    sts, leaks, devs, fids, times = [], [], [], [], []
    for rr in refs:
        exact = coarse_states(groups, basis_vector(M.basis.dim, rr), r.dt, args.kmax)
        for k in range(1, args.kmax + 1):
            tc = time.time()
            psi = run_ir(F.coarse_step(rr, k, r.dt), E.n)
            times.append(time.time() - tc)
            leaks.append(abs(E.leakage(psi)))
            v = E.project(psi)
            devs.append(float(np.abs(v - exact[k]).max()))
            fids.append(float(abs(np.vdot(exact[k], v))))
            sts.append(v / np.linalg.norm(v))
            print(f"  ref {rr} k={k}: {times[-1]:.1f} s, leakage {leaks[-1]:.1e}, "
                  f"|<exact|circuit>| {fids[-1]:.4f}, total {time.time() - t0:.0f} s", flush=True)

    p = np.zeros(M.basis.dim)
    p[r.indices] = np.abs(r.ground) ** 2
    S999 = np.argsort(p)[::-1][:r.support999]
    pmax = np.max(np.array([np.abs(s) ** 2 for s in sts]), axis=0)
    n_reach = int(np.sum(pmax[S999] > 1e-3))
    shots = int(round(args.shots / len(sts)))
    out = dict(mode=args.mode, twoB=twoB, circuits=len(sts), shots_per_circuit=shots,
               references=len(refs), kmax=args.kmax, reach=n_reach, support999=int(len(S999)),
               max_leakage=float(max(leaks)), max_deviation_vs_exact_emulation=float(max(devs)),
               min_fidelity_vs_exact_emulation=float(min(fids)), seed=SEED,
               mean_run_ir_s=float(np.mean(times)))
    rng = np.random.default_rng(SEED)
    for f in (0.2, 0.1):
        acc, rej, B, y = emulate(codec, cw, H, sts, shots, f, rng, twoB, refs)
        res = ritz(H, B)
        met = support_metrics(B, p, 1e-3)
        cert = certify(res, r.E0, float(r.energies[1]))
        inside = bool(cert.weinstein[0] - 1e-12 <= r.E0 <= cert.weinstein[1] + 1e-12)
        out[f"f={f}"] = dict(recall=float(met["recall"]), size=int(len(B)),
                             err=float(res.ER - r.E0), yield_=float(y),
                             false_positives=float(met["false_positives"]),
                             E0_in_weinstein=inside, ER=float(res.ER), E0=float(r.E0))
        print(f"  f={f}: recall {met['recall']:.3f}, |B| {len(B)}, E_R - E_0 {res.ER - r.E0:.2e}, "
              f"E0 in Weinstein: {inside}", flush=True)
    out["runtime_s"] = time.time() - t0

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    frag = os.path.join(ROOT, "data", f"S2_fixed_recall_{args.mode}_B{twoB // 2}.json")
    with open(frag, "w") as fh:
        json.dump(out, fh, indent=1)
    merged = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "S2_fixed_recall_*_B*.json"))):
        d = json.load(open(path))
        merged[f"{d['mode']}|B={d['twoB'] // 2}"] = d
    with open(os.path.join(ROOT, "data", "S2_fixed_recall.json"), "w") as fh:
        json.dump(merged, fh, indent=1)
    print(f"{args.mode} B={twoB // 2}: {out['runtime_s']:.0f} s, written {os.path.basename(frag)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
