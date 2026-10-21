"""Second look at the B=1 CV2 STOP (information for the planner, not a gate number): the Weinstein r_H of the
oracle support (references + the top states by exact ground-state weight) at the sizes the emulation reached."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import numpy as np  # noqa: E402

import gate_CV as CV  # noqa: E402
from skqd.controls import oracle  # noqa: E402
from skqd.skqd import ritz  # noqa: E402

M, codec, acc, sectors = CV.sectors_L(4)
S = sectors["B=1"]
out = {}
d8 = json.load(open(os.path.join(CV.CV4_DIR, "resize_s8.json")))["sectors"]["B=1"]["seeds"]
sizes = sorted({v["half"]["B_all_size"] for v in d8.values()} | {v["full"]["B_all_size"] for v in d8.values()}
               | {500, 1000, 2000, 3000, 4000})
for n in sizes:
    B = sorted(set(int(x) for x in oracle(S.prob, S.sector_idx, n)) | set(S.refs))
    r = ritz(S.H, np.asarray(B))
    out[n] = {"size": len(B), "rH": float(r.rH), "E_R_minus_E0": float(r.ER - S.E0), "W": float(S.prob[B].sum())}
    print(n, out[n], flush=True)
emu = {sd: {"half": [v["half"]["B_all_size"], v["half"]["all"]["rH"]], "full": [v["full"]["B_all_size"], v["full"]["all"]["rH"]]}
       for sd, v in d8.items()}
json.dump({"oracle_B1": out, "emulation_s8_B1": emu}, open(os.path.join(ROOT, "scratch", "executor36", "oracle_b1.json"), "w"),
          indent=1)
print(emu)
