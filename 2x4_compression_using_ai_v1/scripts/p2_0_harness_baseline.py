"""P2-0: the evaluator harness must reproduce the frozen baseline before it judges anything.

Checks (each number goes to data/p2_0_harness_baseline.json):
  * the baseline IR of the given circuits (CircuitFactory(Model(4), 4.0).coarse_step) counts
    cx 71 544 / ry 70 308 / cp 4 -> two-qubit 71 548 (manifest original_ir_counts) and a
    two-qubit depth to compare with the native depth_2q 70 300;
  * the state bar on those circuits (S2_2x4 measured 1.07e-13 on B0_ref0_k1);
  * the term-level operator check of every hop/plaq term at theta = dt (B = 0), which also
    validates the index-qubit trick of `verify_term_operator`.
Usage: python scripts/p2_0_harness_baseline.py [--circuits B0:0:1,B1:0:1]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.env import ROOT, write_json                          # noqa: E402
from c2x4.evaluate import counts, verify_circuit, verify_term_operator   # noqa: E402
from c2x4.problem import get_problem                          # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuits", default="0:0:1,2:0:1",
                    help="comma list of twoB:slot:k (slot = position in krylov.references)")
    ap.add_argument("--no-terms", action="store_true")
    args = ap.parse_args()
    t_start = time.time()
    P = get_problem()
    print(f"model ready ({time.time() - t_start:.1f} s); refs {P.refs}; dt {P.dt}", flush=True)
    out = {"circuits": {}, "terms": {}}
    for spec in args.circuits.split(","):
        twoB, slot, k = (int(x) for x in spec.split(":"))
        ref = P.refs[twoB][slot]
        t0 = time.time()
        g = P.baseline_circuit(twoB, ref, k)
        build = time.time() - t0
        c = counts(g)
        v = verify_circuit(P, g, twoB, ref, k)
        man = os.path.join(ROOT, "data", "quantinuum", "circuits_2x4",
                           f"{P.tag(twoB, ref, k)}.structured.manifest.json")
        frozen = None
        if os.path.exists(man):
            with open(man) as fh:
                d = json.load(fh)
            frozen = {"original_ir_counts": d["original_ir_counts"],
                      "native_level0_counts": {kk: d["levels"]["0"]["counts"][kk]
                                               for kk in ("n_zz", "depth_2q", "n_phasedx", "n_rz")},
                      "manifest": os.path.relpath(man, ROOT)}
        out["circuits"][P.tag(twoB, ref, k)] = {"slot": slot, "build_s": build, "counts": c,
                                                "verification": v, "frozen_manifest": frozen}
        print(f"{P.tag(twoB, ref, k)}: 2q {c['n_2q']} depth2q {c['depth_2q']} | dev "
              f"{v['max_dev_phase_aligned']:.2e} leak {v['leakage']:.2e} ({v['sparse_wall_s']:.0f} s)"
              f" | frozen {frozen and frozen['native_level0_counts']}", flush=True)
    if not args.no_terms:
        th = P.theta(0, 1)
        for nm in P.names[1:]:
            g = P.baseline_term_ir(nm, th)
            r = verify_term_operator(P, nm, g, th)
            r["counts"] = counts(g)
            out["terms"][nm] = r
            print(f"  term {nm}: 2q {r['counts']['n_2q']} dev {r['max_dev']:.2e} "
                  f"leak {r['max_leak']:.2e} ({r['wall_s']:.1f} s)", flush=True)
    p = write_json("data/p2_0_harness_baseline.json", out,
                   produced_by="2x4_compression_using_ai_v1/scripts/p2_0_harness_baseline.py",
                   parameters={"circuits": args.circuits, "g2": P.g2, "m": P.m, "dt": P.dt,
                               "bar": {"max_dev": 1e-10, "leakage": 1e-9}},
                   t_start=t_start)
    print("wrote", p)


if __name__ == "__main__":
    main()
