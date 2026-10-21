"""Reviewer note 2 for the v1 families: the a priori floating-point rounding term (evaluate.rounding_bound) of every
v1 circuit, added to the certified bound of the it5 verification records.  Writes data/rounding_v1.json."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from c2x4.env import STUDY, write_json                                  # noqa: E402
from c2x4.evaluate import BAR_DEV, BAR_LEAK, rounding_bound              # noqa: E402
from c2x4.families import family_header, get_family_ir                  # noqa: E402

t0 = time.time()
out = {}
for name in ("compressed_circuit_llm_2x4_classA_v1", "compressed_circuit_llm_2x4_classB_v1"):
    hdr = family_header(name)
    with open(os.path.join(STUDY, hdr["verification_files"][0])) as fh:
        ver = json.load(fh)["circuits"]
    rows = {}
    for cid, g, md in get_family_ir(name):
        rb = rounding_bound(g)
        v = ver[cid]["verification"]
        cd = v["certified_max_dev"] + rb["rounding_bound"]
        cl = (v["certified_leakage"] ** 0.5 + rb["rounding_bound"]) ** 2
        rows[cid] = {"rounding_bound": rb["rounding_bound"], "n_nonpermutation_gates": rb["n_nonpermutation_gates"],
                     "certified_max_dev_without_rounding": v["certified_max_dev"],
                     "certified_max_dev_with_rounding": cd, "certified_leakage_with_rounding": cl,
                     "pass": bool(cd < BAR_DEV and cl < BAR_LEAK)}
    out[name] = {"circuits": rows, "max_rounding_bound": max(r["rounding_bound"] for r in rows.values()),
                 "max_certified_dev_with_rounding": max(r["certified_max_dev_with_rounding"] for r in rows.values()),
                 "max_certified_leakage_with_rounding": max(r["certified_leakage_with_rounding"] for r in rows.values()),
                 "n_pass": sum(r["pass"] for r in rows.values()), "n": len(rows)}
    print(name, {k: v for k, v in out[name].items() if k != "circuits"})
write_json("data/rounding_v1.json", out, produced_by="2x4_compression_using_ai_v1/scripts/rounding_v1.py",
           parameters={"model": "standard model, u = 2^-53, complex product sqrt2*gamma_2 (Higham Lemma 3.5), "
                                "entries within 1 ulp; Lean Compress2x4.pair_round_bound / gate_round_sq / entry_err_sq"},
           t_start=t0)
