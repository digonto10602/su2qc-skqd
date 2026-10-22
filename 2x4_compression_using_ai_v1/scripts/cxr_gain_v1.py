"""Step 4 evidence: what the CNOT-run resynthesis (+ peephole) removes from the frozen v1 circuits.
Writes data/cxr_gain_v1.json."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from c2x4.env import write_json                       # noqa: E402
from c2x4.evaluate import counts                      # noqa: E402
from c2x4.families import get_family_ir               # noqa: E402
from c2x4.peephole import optimise, resynth_cx_runs   # noqa: E402

t0 = time.time()
out = {}
for name in ("compressed_circuit_llm_2x4_classA_v1", "compressed_circuit_llm_2x4_classB_v1"):
    rows = {}
    for cid, g, md in get_family_ir(name):
        g2, _ = resynth_cx_runs(g)
        g3, _ = optimise(g2)
        rows[cid] = {"n_2q_before": counts(g)["n_2q"], "n_2q_after": counts(g3)["n_2q"]}
    gains = [r["n_2q_before"] - r["n_2q_after"] for r in rows.values()]
    out[name] = {"gain_min": min(gains), "gain_max": max(gains), "gain_mean": sum(gains) / len(gains), "circuits": rows}
    print(name, out[name]["gain_min"], out[name]["gain_max"])
write_json("data/cxr_gain_v1.json", out, produced_by="2x4_compression_using_ai_v1/scripts/cxr_gain_v1.py",
           parameters={"pass": "resynth_cx_runs then optimise"}, t_start=t0)
