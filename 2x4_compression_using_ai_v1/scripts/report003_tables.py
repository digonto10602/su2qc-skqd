"""Report-only helper for reports/003: per-iteration, per-term best counts from the archives (no new
compression work).  Writes data/report003_tables.json and prints markdown tables.
Usage: python scripts/report003_tables.py"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from c2x4.env import STUDY, write_json   # noqa: E402

TERMS = [f"hop{l}" for l in range(10)] + ["plaq0", "plaq1", "plaq2"]


def main():
    out = {}
    base = json.load(open(os.path.join(STUDY, "data", "p2_0_harness_baseline.json")))
    out["baseline"] = {nm: base["terms"][nm]["counts"]["n_2q"] for nm in TERMS}
    for it in ("it1", "it2", "it3", "it4", "it5"):
        a = json.load(open(os.path.join(STUDY, "data", f"archive_{it}.json")))
        A = {nm: [a["operator"][nm]["best"]["n_2q"], a["operator"][nm]["best"]["label"]] for nm in TERMS}
        B = {}
        for nm in TERMS:
            vals = [a["input"][r][nm]["best"]["n_2q"] for r in a["input"] if a["input"][r].get(nm, {}).get("best")]
            B[nm] = [min(vals), sum(vals) / len(vals), max(vals)]
        out[it] = {"classA": A, "classB_min_mean_max": B}
    write_json("data/report003_tables.json", out, produced_by="2x4_compression_using_ai_v1/scripts/report003_tables.py",
               parameters={"archives": "data/archive_it1..5.json", "baseline": "data/p2_0_harness_baseline.json"})
    its = ["it1", "it2", "it3", "it4", "it5"]
    print("| term | baseline | " + " | ".join(f"A {i}" for i in its) + " |")
    print("|---|---|" + "---|" * len(its))
    for nm in TERMS:
        print(f"| {nm} | {out['baseline'][nm]} | " + " | ".join(f"{out[i]['classA'][nm][0]} ({out[i]['classA'][nm][1]})" for i in its) + " |")
    print(f"| sum | {sum(out['baseline'].values())} | " + " | ".join(str(sum(out[i]['classA'][nm][0] for nm in TERMS)) for i in its) + " |")
    print()
    print("| term | baseline | " + " | ".join(f"B {i} mean" for i in its) + " |")
    print("|---|---|" + "---|" * len(its))
    for nm in TERMS:
        print(f"| {nm} | {out['baseline'][nm]} | " + " | ".join(f"{out[i]['classB_min_mean_max'][nm][1]:.1f}" for i in its) + " |")


if __name__ == "__main__":
    main()
