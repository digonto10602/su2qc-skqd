"""Noisy SKQD campaign aggregate: every <lattice results>/<family>/<device>/noisy_skqd.json -> one row per
(lattice, family, device, sector) in noise/data/results/noisy_skqd_campaign_summary.json; refreshes index.json.

Usage: python scripts/skqd_aggregate.py
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NOISE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(NOISE, "src"))
sys.path.insert(0, HERE)
import campaign as C  # noqa: E402
import results  # noqa: E402
from provenance import provenance, dump  # noqa: E402

OUT = os.path.join(NOISE, "data", "results", "noisy_skqd_campaign_summary.json")


def main():
    rows, files = [], []
    for lat, base in results.RESULTS_DIRS.items():
        for p in sorted(glob.glob(os.path.join(base, lat, "*", "*", "noisy_skqd.json"))):
            d = results.load(lat, p.split(os.sep)[-3], p.split(os.sep)[-2], "noisy_skqd")
            files.append(os.path.relpath(p, results.ROOT))
            for sec, s in d["summary"].items():
                r = {"lattice": lat, "family": C.short(d["family"]), "device": d["device"], "sector": sec}
                r.update(s)
                r["git_commit"] = d["provenance"]["git_commit"]
                r["file"] = os.path.relpath(p, results.ROOT)
                rows.append(r)
    budget = C.load_budget()
    dump({"what": "noisy SKQD campaign: one row per (lattice, family, device, sector); noisy plan point (B_all) and "
                  "the ideal (noiseless) samples of the same size side by side",
          "columns": {"acceptance": "accepted / shots, all circuits of the sector",
                      "f_hit": "reference hits / sum(shots x p_ref), all circuits of the sector (k1: k = 1 only)",
                      "r_nc": "f_hit / f_ideal(1e-3)", "E_R_minus_E0": "Ritz energy on B_all minus exact E0 (plan point)",
                      "width": "certificate width (Kato-Temple with the exact E1 at B=0, Weinstein 2 r_H at B=1)",
                      "E0_inside": "exact E0 inside the certificate interval", "recall_S999": "recall of S99.9",
                      "W": "ground-state weight captured by B_all", "CV": "CV1-CV5 ok (gate_CV criteria)",
                      "ideal_*": "the same quantities on ideal samples with the same per-circuit shot counts"},
          "rows": rows, "files": files, "budget": os.path.relpath(C.BUDGET_JSON, results.ROOT),
          "budget_total_thread_hours": budget.get("total_thread_hours"),
          "loader": "noise/src/results.py: load(lattice, family, device, 'noisy_skqd')",
          "provenance": provenance()}, OUT)
    import aggregate
    aggregate.index()
    print("rows", len(rows), "->", OUT)


if __name__ == "__main__":
    main()
