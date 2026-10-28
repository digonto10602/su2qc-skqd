"""Load every circuit of the 2x3 / 2x4 native exports (notes/013) exactly as the package's submission script does
(`scripts/quantinuum_submit.py`: load_index, load_manifest, load_frozen -- the sha256 check of the (uncompressed) JSON
text against the manifest, then pytket from_json), and compare the loaded circuit's native counts with the manifest.
Imports the package script read-only; nothing is submitted, no network.

Run with the isolated venv:
  ~/.local/share/su2qc-quantinuum/venv/bin/python 2x4_compression_using_ai_v1/scripts/check_native_exports_load.py
Writes data/native_exports_load_check.json.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(STUDY, "src"))
sys.path.insert(0, os.path.join(ROOT, "src"))

from c2x4.env import lattice_study, write_json        # noqa: E402
from skqd import quantinuum_native as qn              # noqa: E402

EXPORTS = [("2x3", "compressed_circuit_llm_2x3_classA"), ("2x3", "compressed_circuit_llm_2x3_classB"),
           ("2x4", "compressed_circuit_llm_2x4_classA"), ("2x4", "compressed_circuit_llm_2x4_classB"),
           ("2x4", "compressed_circuit_llm_2x4_classA_v2"), ("2x4", "compressed_circuit_llm_2x4_classB_v2")]


def main():
    t0 = time.time()
    spec = importlib.util.spec_from_file_location("quantinuum_submit", os.path.join(ROOT, "scripts", "quantinuum_submit.py"))
    qs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qs)
    out = {}
    for lat, fam in EXPORTS:
        cdir = os.path.join(lattice_study(lat), "data", "families", f"native_{lat}", fam)
        index = qs.load_index(cdir)
        ids = list(index["circuits"]) + list(index.get("calibration", []))
        bad = []
        for cid in ids:
            man = qs.load_manifest(cdir, cid)
            circ = qs.load_frozen(cdir, man)                 # raises on a sha256 mismatch
            if qn.native_counts(circ)["ops"] != man["counts"]["ops"]:
                bad.append(cid)
        out[fam] = {"dir": os.path.relpath(cdir, ROOT), "n_loaded": len(ids), "n_counts_mismatch": len(bad),
                    "mismatches": bad, "ok": not bad}
        print(fam, out[fam], flush=True)
    write_json("data/native_exports_load_check.json", {"exports": out, "all_ok": all(v["ok"] for v in out.values()),
                                                         "versions": qn.versions()},
               produced_by="2x4_compression_using_ai_v1/scripts/check_native_exports_load.py",
               parameters={"loader": "scripts/quantinuum_submit.py load_index/load_manifest/load_frozen"}, t_start=t0)


if __name__ == "__main__":
    main()
