"""One iteration of the loop: run every applicable proposal for every (reference, term), verify each candidate
on its contract (A1: max deviation <= 1e-10, leakage <= 1e-12), keep the best verified one per
(reference, term) for the input-specific class and per term for the operator-exact class.

Writes data/archive_<label>.json (the archive) -- the families `best_input_<label>` and
`best_operator_<label>` read it.  Selection angle: theta = 1 * dt of the sector (gate counts of every
proposal are theta-independent; every circuit is re-verified at its own theta by eval_family.py).

Usage: python scripts/loop_select.py --label it1 --proposals rpkg,cf1,cf2 [--refs 102,16833] [--merge]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.env import STUDY, write_json                                    # noqa: E402
from c2x4.evaluate import counts, verify_term_operator                    # noqa: E402
from c2x4.family import get_reach                                         # noqa: E402
from c2x4.problem import get_problem                                      # noqa: E402
from c2x4.proposals import PROPOSALS, applicable                          # noqa: E402
from c2x4.reach import contract_states                                    # noqa: E402

A1_DEV, A1_LEAK = 1e-10, 1e-12


def try_candidate(P, label, nm, th, con, loc):
    t0 = time.time()
    try:
        g = PROPOSALS[label]["fn"](P, nm, th, con, loc)
    except Exception as exc:                       # a failed proposal is recorded, never silently dropped
        return {"label": label, "error": repr(exc)[:300], "accepted": False}
    c = counts(g)
    r = verify_term_operator(P, nm, g, th, restrict_to=con)
    ok = r["max_dev"] <= A1_DEV and r["max_leak"] <= A1_LEAK
    return {"label": label, "n_2q": c["n_2q"], "depth_2q": c["depth_2q"], "n_1q": c["n_1q"],
            "max_dev": r["max_dev"], "max_leak": r["max_leak"], "accepted": bool(ok),
            "wall_s": time.time() - t0}


def best(rows):
    acc = [r for r in rows if r.get("accepted")]
    return min(acc, key=lambda r: (r["n_2q"], r["depth_2q"])) if acc else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--proposals", required=True)
    ap.add_argument("--refs", default="all")
    ap.add_argument("--terms", default="all")
    ap.add_argument("--merge", action="store_true", help="merge into an existing archive of this label")
    args = ap.parse_args()
    t_start = time.time()
    P = get_problem()
    R = get_reach(P)
    labels = args.proposals.split(",")
    terms = P.names[1:] if args.terms == "all" else args.terms.split(",")
    path = os.path.join(STUDY, "data", f"archive_{args.label}.json")
    arch = {"input": {}, "operator": {}}
    if args.merge and os.path.exists(path):
        with open(path) as fh:
            old = json.load(fh)
        arch = {"input": old.get("input", {}), "operator": old.get("operator", {})}
    # ---- operator-exact class (reference independent), at theta = dt of B = 0
    th0 = P.theta(0, 1)
    for nm in terms:
        rows = [try_candidate(P, lb, nm, th0, None, None) for lb in labels
                if applicable(lb, nm) and PROPOSALS[lb]["contract"] in ("operator", "both")]
        prev = arch["operator"].get(nm, {}).get("candidates", [])
        rows = prev + [r for r in rows if r["label"] not in {p["label"] for p in prev}]
        b = best(rows)
        arch["operator"][nm] = {"candidates": rows, "best": b}
        print(f"operator {nm}: " + ", ".join(f"{r['label']}={r.get('n_2q', 'ERR')}{'' if r.get('accepted') else '(x)'}"
                                              for r in rows) + f" -> {b and b['label']}", flush=True)
    # ---- input-specific class
    refs = [(tb, r) for tb in (0, 2) for r in P.refs[tb]]
    if args.refs != "all":
        want = {int(v) for v in args.refs.split(",")}
        refs = [(tb, r) for tb, r in refs if r in want]
    for twoB, ref in refs:
        th = P.theta(twoB, 1)
        key = str(ref)
        arch["input"].setdefault(key, {"twoB": twoB})
        for nm in terms:
            loc = R.local_reachable(ref, nm)
            con = contract_states(P, nm, loc)
            rows = [try_candidate(P, lb, nm, th, con, loc) for lb in labels if applicable(lb, nm)]
            prev = arch["input"][key].get(nm, {}).get("candidates", [])
            rows = prev + [r for r in rows if r["label"] not in {p["label"] for p in prev}]
            b = best(rows)
            arch["input"][key][nm] = {"candidates": rows, "best": b, "n_contract_states": len(con)}
        tot = sum(arch["input"][key][nm]["best"]["n_2q"] for nm in P.names[1:] if nm in arch["input"][key]
                  and arch["input"][key][nm]["best"])
        print(f"input ref {ref}: sum of best term 2q = {tot} "
              f"({', '.join(nm + ':' + arch['input'][key][nm]['best']['label'] + '=' + str(arch['input'][key][nm]['best']['n_2q']) for nm in terms if arch['input'][key][nm]['best'])})",
              flush=True)
    write_json(path, arch, produced_by="2x4_compression_using_ai_v1/scripts/loop_select.py",
               parameters={"label": args.label, "proposals": labels, "terms": terms, "refs": args.refs,
                           "A1": {"max_dev": A1_DEV, "max_leak": A1_LEAK},
                           "selection_theta": "1 * dt of the sector"}, t_start=t_start)
    print("wrote", path, f"({time.time() - t_start:.0f} s)")


if __name__ == "__main__":
    main()
