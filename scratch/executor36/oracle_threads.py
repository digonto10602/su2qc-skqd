"""Why does r_H(oracle) differ between the gate (BLAS 1 thread) and scratch/executor36/oracle_b1.py (BLAS 4)?
Recompute the oracle sets for the three B_all(8N) sizes with the reference eigenvector computed under 1 and 4
BLAS threads (information for the cluster-diagnostic record)."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import numpy as np  # noqa: E402  (imported before gate_CV: the BLAS pool keeps the caller's OMP_NUM_THREADS)
from threadpoolctl import threadpool_limits  # noqa: E402

import gate_CV as CV  # noqa: E402
from skqd.controls import oracle  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.skqd import ritz  # noqa: E402

M = Model(4)
H = M.H(4.0).tocsr()
refs = [int(r) for r in references(M.basis, 2)]
sidx = np.asarray(M.basis.sector(2), dtype=int)
scr = json.load(open(os.path.join(ROOT, "scratch", "executor36", "oracle_b1.json")))["oracle_B1"]
out = {}
for th in (1, 4):
    with threadpool_limits(th):
        r = M.reference(4.0, 2, k=4)
    prob = np.zeros(M.basis.dim)
    prob[r.indices] = np.abs(r.ground) ** 2
    for n in (1583, 1538, 1560):
        O = sorted(set(int(x) for x in oracle(prob, sidx, n)) | set(refs))
        with threadpool_limits(1):
            rr = ritz(H, np.asarray(O))
        out[f"threads{th}_n{n}"] = {"rH": float(rr.rH), "minus_scratch": float(rr.rH - scr[str(n)]["rH"])}
        print(th, n, out[f"threads{th}_n{n}"], flush=True)
json.dump(out, open(os.path.join(ROOT, "scratch", "executor36", "oracle_threads.json"), "w"), indent=1)
