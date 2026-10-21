"""Approximate class (notes/004): cost versus tolerance on selected circuits, every point verified.

For each circuit (twoB, ref, k) and each budget eps_total, drop blocks per term (reach.approx_contracts), build
every applicable proposal on the kept blocks, keep the cheapest one that is exact on them (A1 on the kept
strings), assemble (diagonal dropped, peephole), run the exact sparse simulator, and record the measured
eps = min_alpha || psi - e^{i alpha} psi_exact ||_2 (codewords + leakage), max |dpsi|, leakage, the L6 bound,
and the two-qubit count and depth.  Only eps_total = 1e-8 is the adopted tolerance (notes/004 3); larger
budgets are labelled 'information only'.

Usage: python scripts/approx_tiers.py --circuits 0:102:1,0:345:1,2:230:1 --budgets 1e-8,1e-6,1e-4
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.env import write_json                                         # noqa: E402
from c2x4.evaluate import counts, verify_term_operator                  # noqa: E402
from c2x4.peephole import optimise                                      # noqa: E402
from c2x4.problem import get_problem                                    # noqa: E402
from c2x4.proposals import PROPOSALS, applicable                        # noqa: E402
from c2x4.reach import approx_contracts                                 # noqa: E402
from c2x4.evaluate import verify_circuit_pruned                         # noqa: E402

LABELS = ["rpkg", "rpkg_sw", "bframed", "bframed_sw", "cfg_sw", "cfg_t_sw", "cf2_sw"]


def build_term(P, nm, th, kept):
    best = None
    for lb in LABELS:
        if not applicable(lb, nm):
            continue
        try:
            g = PROPOSALS[lb]["fn"](P, nm, th, kept, kept)
        except Exception as exc:              # recorded by omission of the label; reason printed
            print(f"   {nm} {lb}: {repr(exc)[:120]}", flush=True)
            continue
        r = verify_term_operator(P, nm, g, th, restrict_to=kept)
        if r["max_dev"] > 1e-10 or r["max_leak"] > 1e-12:
            continue
        c = counts(g)
        if best is None or (c["n_2q"], c["depth_2q"]) < (best[0], best[1]):
            best = (c["n_2q"], c["depth_2q"], lb, g)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuits", required=True)
    ap.add_argument("--budgets", default="1e-8,1e-6,1e-4")
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    t_start = time.time()
    P = get_problem()
    rows = []
    for spec in args.circuits.split(","):
        twoB, ref, k = (int(v) for v in spec.split(":"))
        th = P.theta(twoB, k)
        tgt = P.target(twoB, ref, k)
        for bud in (float(b) for b in args.budgets.split(",")):
            t0 = time.time()
            ac = approx_contracts(P, ref, k, bud)
            gates = list(P.factory.prepare(ref))
            choice = {}
            for nm in P.names[1:]:
                kept = ac[nm]["kept_states"]
                if not kept:
                    choice[nm] = ("none", 0)
                    continue
                b = build_term(P, nm, th, kept)
                choice[nm] = (b[2], b[0])
                gates += b[3]
            gates, _ = optimise(gates)
            c = counts(gates)
            v = verify_circuit_pruned(P, gates, twoB, ref, k, tau=1e-15)
            leak = v["leakage"]
            leak_direct = v["leakage_direct"]
            eps = float(v["l2_dev_phase_aligned"] + v["prune_bound"])        # certified l2 distance (notes/006)
            d = None
            bound = float(sum(v["dropped_bound"] for v in ac.values()))
            row = {"twoB": twoB, "reference": ref, "k": k, "budget_total": bud,
                   "adopted": bud <= 1e-8, "status": "adopted tolerance" if bud <= 1e-8 else "information only",
                   "n_2q": c["n_2q"], "depth_2q": c["depth_2q"], "n_1q": c["n_1q"],
                   "eps_certified": eps, "eps_measured_pruned_l2": v["l2_dev_phase_aligned"],
                   "prune_bound": v["prune_bound"], "max_abs_dev": v["max_dev_phase_aligned"], "leakage": leak,
                   "leakage_direct": leak_direct,
                   "L6_bound": bound, "eps_within_budget": bool(eps <= bud),
                   "blocks_dropped": {nm: v["n_blocks_dropped"] for nm, v in ac.items()},
                   "blocks_touched": {nm: v["n_blocks_touched"] for nm, v in ac.items()},
                   "choice": choice, "wall_s": time.time() - t0}
            rows.append(row)
            print(f"{P.tag(twoB, ref, k)} budget {bud:.0e}: 2q {c['n_2q']} depth {c['depth_2q']} | eps "
                  f"{eps:.2e} (L6 bound {bound:.2e}) max|d| {row['max_abs_dev']:.2e} leak {leak:.2e} | dropped "
                  f"{sum(row['blocks_dropped'].values())} blocks", flush=True)
            save(args, rows, t_start)


def save(args, rows, t_start):
    write_json(f"data/approx_tiers{('_' + args.label) if args.label else ''}.json", {"rows": rows},
               produced_by="2x4_compression_using_ai_v1/scripts/approx_tiers.py",
               parameters={"circuits": args.circuits, "budgets": args.budgets, "proposals": LABELS,
                           "split": "budget_total / 13 per term", "adopted_tolerance": 1e-8,
                           "tolerance_note": "notes/004-approximate-class-tolerance.md",
                           "written": "after every row (a run cut by the 30-minute limit keeps its rows)"},
               t_start=t_start)


if __name__ == "__main__":
    main()
