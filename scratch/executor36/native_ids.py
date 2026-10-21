import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))
import quantinuum_lattice_tests as QL  # noqa: E402

idx, mans, _ = QL.family(4)
done = {r["base_id"] for r in json.load(open(os.path.join(ROOT, "ci/parts/QV_2x4_01.json")))["runs"]}
ids = [c for c in idx["circuits"] if mans[c].get("source") == "structured" and int(mans[c]["k"]) == 1
       and mans[c]["base_id"] not in done]
open(os.path.join(ROOT, "scratch/executor36/native_ids.txt"), "w").write(" ".join(ids))
print(len(ids), ids)
