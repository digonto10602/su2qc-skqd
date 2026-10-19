import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import numpy as np  # noqa: E402

from skqd.exact import Model  # noqa: E402
from skqd.krylov import ideal_sector_distribution  # noqa: E402
from skqd.skqd import exact_support  # noqa: E402
from h0_support_plan import d3r_plan  # noqa: E402

M = Model(4)
cd = os.path.join(ROOT, "data/quantinuum/circuits_2x4")
idx = json.load(open(os.path.join(cd, "index.json")))
mans = {}
for c in idx["circuits"]:
    m = json.load(open(os.path.join(cd, f"{c}.manifest.json")))
    if m["source"] == "structured":
        mans[m["base_id"]] = m
print(len(mans))
for tb in (0, 2):
    r = M.reference(4.0, tb, k=4)
    prob = np.zeros(M.basis.dim)
    prob[r.indices] = abs(r.ground) ** 2
    pos = {int(b): i for i, b in enumerate(r.indices)}
    S99 = [pos[int(s)] for s in exact_support(prob, 1e-2)]
    S999 = [pos[int(s)] for s in exact_support(prob, 1e-3)]
    ids = sorted(c for c, m in mans.items() if m["twoB"] == tb)
    t = time.time()
    P = {c: ideal_sector_distribution(M, 4.0, tb, mans[c]["reference"], mans[c]["k"], mans[c]["dt"], 1)["p"] for c in ids}
    print("dist", time.time() - t)
    k4 = [c for c in ids if mans[c]["k"] == 4]
    for f in (1.0, 0.1, 0.05):
        if f == 1.0:
            d = d3r_plan(P, {c: 1.0 for c in ids}, ids, k4, S99, S999, margin=1.0, readout_factor=1.0)
        else:
            d = d3r_plan(P, {c: f for c in ids}, ids, k4, S99, S999)
        print(tb, f, d["shots_total"], d["lp_shots_total"], d["k4_extra_per_circuit"], d["P_recall_S999_ge_target"],
              d["floor_circuits"], max(d["shots"].values()))
