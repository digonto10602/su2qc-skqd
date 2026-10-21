"""Evaluate a candidate family: term-level operator check (A1) at every theta used, full-circuit state bar
(A2) on the requested circuits, counts and two-qubit depth (A5).  Writes data/eval_<family>_<label>.json.

Usage:
  python scripts/eval_family.py --family F2a --circuits all            # 60 circuits, k = 1..4
  python scripts/eval_family.py --family F2a --circuits 0:102:1,2:230:1 --kmax 5
  python scripts/eval_family.py --family F2a --circuits all --kmax 5 --label k5
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.env import write_json                                   # noqa: E402
from c2x4.evaluate import (BAR_DEV, BAR_LEAK, counts, verify_circuit, verify_circuit_pruned,   # noqa: E402
                           verify_term_operator)
from c2x4.family import (FAMILIES, archive_family, baseline_builder, circuit, get_reach,   # noqa: E402
                         term_builder)
from c2x4.reach import contract_states                             # noqa: E402
from c2x4.problem import get_problem                               # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--circuits", default="all", help="'all' or comma list twoB:ref:k")
    ap.add_argument("--kmax", type=int, default=4)
    ap.add_argument("--label", default="")
    ap.add_argument("--no-terms", action="store_true")
    ap.add_argument("--terms-only", action="store_true", help="A1 only (no full-circuit simulation)")
    ap.add_argument("--prune-tau", type=float, default=None,
                    help="certified pruned simulation (evaluate.verify_circuit_pruned); default: exact, no pruning")
    ap.add_argument("--max-wall", type=float, default=1700.0, help="stop starting new circuits after this (s)")
    args = ap.parse_args()
    t_start = time.time()
    P = get_problem()
    if args.family.startswith("arch:"):
        parts = args.family.split(":")                # arch:<label>:<input|operator>[:pp]
        fam = archive_family(parts[1], parts[2], peephole=(len(parts) > 3 and parts[3] == "pp"))
    else:
        fam = FAMILIES[args.family]
    if args.circuits == "all":
        ids = P.circuit_ids(args.kmax)
    else:
        ids = [tuple(int(v) for v in s.split(":")) for s in args.circuits.split(",")]
    out = {"family": args.family, "drop_diag": fam.get("drop_diag", False),
           "peephole": fam.get("peephole", False),
           "builders": {nm: getattr(b, "tag", b.__name__) for nm, b in fam["builders"].items()},
           "terms": {}, "circuits": {}}
    # ---- A1 term level at every theta used
    if not args.no_terms:
        for nm in P.names[1:]:
            b = term_builder(fam, nm)
            if b is baseline_builder:
                continue
            rows = []
            if getattr(b, "contract", "") == "input-specific":
                cases = sorted({(twoB, ref, P.theta(twoB, k)) for (twoB, ref, k) in ids})
            else:
                cases = sorted({(None, None, P.theta(twoB, k)) for (twoB, _r, k) in ids})
            for (twoB, ref, th) in cases:
                g = b(P, nm, th, {"twoB": twoB, "ref": ref, "k": None})
                restrict = None
                if ref is not None:
                    restrict = contract_states(P, nm, get_reach(P).local_reachable(ref, nm))
                r = verify_term_operator(P, nm, g, th, restrict_to=restrict)
                r["counts"] = counts(g)
                r["reference"] = ref
                rows.append(r)
            worst = max(rows, key=lambda r: r["max_dev"])
            out["terms"][nm] = {"rows": rows, "worst_dev": worst["max_dev"],
                                "worst_leak": max(r["max_leak"] for r in rows),
                                "n_2q": sorted({r["counts"]["n_2q"] for r in rows})}
            print(f"A1 {nm}: worst dev {worst['max_dev']:.2e}, worst leak "
                  f"{out['terms'][nm]['worst_leak']:.2e}, 2q {out['terms'][nm]['n_2q']}", flush=True)
    # ---- A2 + A5 per circuit
    n_pass = 0
    for (twoB, ref, k) in ([] if args.terms_only else ids):
        if time.time() - t_start > args.max_wall:
            print("wall limit reached: remaining circuits not run (30-minute rule)", flush=True)
            out["truncated_at_wall_s"] = args.max_wall
            break
        g = circuit(P, fam, twoB, ref, k)
        c = counts(g)
        v = (verify_circuit(P, g, twoB, ref, k) if args.prune_tau is None
             else verify_circuit_pruned(P, g, twoB, ref, k, tau=args.prune_tau))
        n_pass += int(v["pass"])
        out["circuits"][P.tag(twoB, ref, k)] = {"counts": c, "verification": v}
        print(f"A2 {P.tag(twoB, ref, k)}: 2q {c['n_2q']} depth2q {c['depth_2q']} 1q {c['n_1q']} | "
              f"dev {v['max_dev_phase_aligned']:.2e} leak {v['leakage']:.2e} "
              f"{'' if 'certified_max_dev' not in v else 'cert ' + format(v['certified_max_dev'], '.2e') + ' '}"
              f"pass {v['pass']} "
              f"({v['sparse_wall_s']:.1f} s)", flush=True)
    cs = out["circuits"].values()
    if cs:
        out["summary"] = {
            "n_circuits": len(out["circuits"]), "n_pass": n_pass,
            "max_dev_phase_aligned": max(x["verification"]["max_dev_phase_aligned"] for x in cs),
            "max_certified_dev": max(x["verification"].get("certified_max_dev", x["verification"]["max_dev_phase_aligned"]) for x in cs),
            "max_certified_leakage": max(x["verification"].get("certified_leakage", abs(x["verification"]["leakage"])) for x in cs),
            "max_abs_leakage": max(abs(x["verification"]["leakage"]) for x in cs),
            "n_2q_range": [min(x["counts"]["n_2q"] for x in cs), max(x["counts"]["n_2q"] for x in cs)],
            "depth_2q_range": [min(x["counts"]["depth_2q"] for x in cs),
                               max(x["counts"]["depth_2q"] for x in cs)],
            "bar": {"max_dev": BAR_DEV, "leakage": BAR_LEAK},
            "baseline": {"n_2q": 71548, "depth_2q": 70300,
                         "source": "data/quantinuum/circuits_2x4/*.structured.manifest.json levels.0.counts; "
                                   "reproduced by data/p2_0_harness_baseline.json"}}
        print("summary:", out["summary"], flush=True)
    label = f"_{args.label}" if args.label else ""
    p = write_json(f"data/eval_{args.family.replace(':', '_')}{label}.json", out,
                   produced_by="2x4_compression_using_ai_v1/scripts/eval_family.py",
                   parameters={"family": args.family, "circuits": args.circuits, "kmax": args.kmax,
                               "g2": P.g2, "m": P.m, "dt": P.dt, "prune_tau": args.prune_tau}, t_start=t_start)
    print("wrote", p)


if __name__ == "__main__":
    main()
