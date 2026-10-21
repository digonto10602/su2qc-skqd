"""Merge loop archives: operator part from --operator, input part from every --inputs file (references disjoint or
the better candidate per term kept).  Writes the archive of --out with provenance.

Usage: python scripts/merge_archives.py --out it6 --operator it6 --inputs it6b0,it6b1,it6b2 [--lx 4]"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from c2x4.env import archive_path, write_json      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--operator", required=True)
ap.add_argument("--inputs", required=True)
args = ap.parse_args()
t0 = time.time()
with open(archive_path(args.operator)) as fh:
    op = json.load(fh)
inp = {}
for lab in args.inputs.split(","):
    with open(archive_path(lab)) as fh:
        d = json.load(fh)
    for ref, row in d.get("input", {}).items():
        if ref not in inp:
            inp[ref] = row
            continue
        for nm, v in row.items():
            if nm == "twoB":
                continue
            old = inp[ref].get(nm)
            if old is None or (v["best"] and (old["best"] is None or
                                              (v["best"]["n_2q"], v["best"]["depth_2q"]) <
                                              (old["best"]["n_2q"], old["best"]["depth_2q"]))):
                inp[ref][nm] = v
p = archive_path(args.out)
write_json(p, {"operator": op["operator"], "input": inp},
           produced_by="2x4_compression_using_ai_v1/scripts/merge_archives.py",
           parameters={"operator_from": args.operator, "inputs_from": args.inputs.split(",")}, t_start=t0)
print("wrote", p, "refs", sorted(inp, key=int))
