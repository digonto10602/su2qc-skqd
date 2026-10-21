"""Cross-check: the v1 circuits built here with genie's builders (circuits.build_v1) equal, gate by gate and bit for
bit, genie's frozen family files read through genie's loader (notes/009, families.get_family_ir).
Writes noise/data/checks/v1_build_vs_frozen.json."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits
from provenance import provenance, dump

def same(a, b):
    if a[0] != b[0] or list(a[1]) != list(b[1]):
        return False
    if a[2] is None or b[2] is None:
        return a[2] is None and b[2] is None
    return np.array_equal(np.asarray(a[2], dtype=complex), np.asarray(b[2], dtype=complex))

rows = {}
for fam in circuits.FAMILY_V1:
    for t, (g, md) in circuits.genie_ir(fam).items():
        mine = circuits.v1_gates(fam, t)
        rows[f"{fam}|{t}"] = {"n_gates_mine": len(mine), "n_gates_frozen": len(g),
                              "identical": bool(len(mine) == len(g) and all(same(a, b) for a, b in zip(mine, g))),
                              "frozen_content_sha256": md.get("content_sha256")}
F = circuits.genie_family_api()
dump({"rows": rows, "n": len(rows), "n_identical": sum(r["identical"] for r in rows.values()),
      "genie_family_headers": {f: {k: v for k, v in F.family_header(f).items() if k in ("provenance", "file_sha256", "version", "n_circuits")} for f in circuits.FAMILY_V1},
      "provenance": provenance()}, os.path.join(circuits.NOISE, "data", "checks", "v1_build_vs_frozen.json"))
print(len(rows), sum(r["identical"] for r in rows.values()))
