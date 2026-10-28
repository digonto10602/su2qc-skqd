"""Tables of report 004 (C4 + C3), read from the JSON files the runs wrote; nothing is recomputed except sums and
means.  Writes data/report004_tables.json."""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from c2x4.env import STUDY, lattice_data, write_json        # noqa: E402

D = os.path.join(STUDY, "data")


def _abs(rel):
    """'c2x3/<file>' -> the 2x3 folder's data/c2x3/<file> (notes/012); anything else -> this folder's data/<rel>.
    The relative name stays the table key, as before the split."""
    if rel.startswith("c2x3/"):
        return os.path.join(lattice_data("2x3"), rel[len("c2x3/"):])
    return os.path.join(D, rel)


def load(rel):
    with open(_abs(rel)) as fh:
        return json.load(fh)


def fam_stats(rel):
    d = load(rel)
    c = d["circuits"]
    n2 = [v["counts"]["n_2q"] for v in c.values()]
    d2 = [v["counts"]["depth_2q"] for v in c.values()]
    s = d["summary"]
    return {"file": rel, "n": len(c), "n_pass": s["n_pass"], "n_2q_min": min(n2), "n_2q_max": max(n2),
            "n_2q_mean": statistics.mean(n2), "depth_2q_min": min(d2), "depth_2q_max": max(d2),
            "depth_2q_mean": statistics.mean(d2), "max_dev_measured": s["max_dev_phase_aligned"],
            "max_certified_dev": s["max_certified_dev"], "max_certified_leakage": s["max_certified_leakage"],
            "max_leakage_direct": max(v["verification"].get("leakage_direct", 0.0) for v in c.values()),
            "max_rounding_bound": max((v["verification"].get("rounding", {}).get("rounding_bound", 0.0)
                                       for v in c.values()), default=None),
            "max_prune_bound": max(v["verification"].get("prune_bound", 0.0) for v in c.values()),
            "skeleton_k_independent": s.get("skeleton_k_independent", {}).get("all"),
            "k_dependent_references_by_count": _kdep(c)}


def _kdep(c):
    by = {}
    for cid, v in c.items():
        by.setdefault(cid.rsplit("_k", 1)[0], set()).add(v["counts"]["n_2q"])
    return sorted(r for r, s in by.items() if len(s) > 1)


t0 = time.time()
out = {}
out["2x4"] = {"A_v1": fam_stats("eval_arch_it5_operator_pp_all75_pruned.json"),
              "B_v1": fam_stats("eval_arch_it5_input_pp_all75_pruned.json"),
              "A_v2": fam_stats("eval_arch_it6_operator_pp2_all75_pruned.json"),
              "B_v2": fam_stats("eval_arch_it6_input_pp2_all75_pruned.json")}
rv1 = load("rounding_v1.json")
out["2x4"]["v1_with_rounding"] = {k: {kk: vv for kk, vv in v.items() if kk != "circuits"} for k, v in rv1.items() if k.startswith("compressed")}
out["2x3"] = {"A": fam_stats("c2x3/eval_arch_L3_it1_operator_pp2_all44_pruned.json"),
              "B": fam_stats("c2x3/eval_arch_L3_it1_input_pp2_all44_pruned.json")}
# per-term class A and class-B means, it5 vs it6 (and 2x3)
a5, a6 = load("archive_it5.json"), load("archive_it6.json")
a3 = load("c2x3/archive_L3_it1.json")
terms4 = [f"hop{i}" for i in range(10)] + ["plaq0", "plaq1", "plaq2"]
terms3 = [f"hop{i}" for i in range(7)] + ["plaq0", "plaq1"]
out["per_term_2x4"] = {nm: {"A_it5": a5["operator"][nm]["best"]["n_2q"], "A_it5_label": a5["operator"][nm]["best"]["label"],
                            "A_it6": a6["operator"][nm]["best"]["n_2q"], "A_it6_label": a6["operator"][nm]["best"]["label"],
                            "B_it5_mean": statistics.mean(r[nm]["best"]["n_2q"] for r in a5["input"].values()),
                            "B_it6_mean": statistics.mean(r[nm]["best"]["n_2q"] for r in a6["input"].values()),
                            "B_it6_min": min(r[nm]["best"]["n_2q"] for r in a6["input"].values()),
                            "B_it6_max": max(r[nm]["best"]["n_2q"] for r in a6["input"].values())}
                       for nm in terms4}
out["per_term_2x3"] = {nm: {"A": a3["operator"][nm]["best"]["n_2q"], "A_label": a3["operator"][nm]["best"]["label"],
                            "B_mean": statistics.mean(r[nm]["best"]["n_2q"] for r in a3["input"].values()),
                            "B_min": min(r[nm]["best"]["n_2q"] for r in a3["input"].values()),
                            "B_max": max(r[nm]["best"]["n_2q"] for r in a3["input"].values())}
                       for nm in terms3}
for key, terms in (("per_term_2x4", terms4), ("per_term_2x3", terms3)):
    pt = out[key]
    out[key + "_sums"] = {c: sum(pt[nm][c] for nm in terms) for c in pt[terms[0]] if not c.endswith("label")}
# certificates
for rel, key in (("cert_it6_operator.json", "cert_2x4_A"), ("cert_it6_input.json", "cert_2x4_B"),
                 ("c2x3/cert_L3_it1_operator.json", "cert_2x3_A"), ("c2x3/cert_L3_it1_input.json", "cert_2x3_B")):
    if os.path.exists(os.path.join(D, rel)):
        s = load(rel)["summary"]
        out[key] = {k: v for k, v in s.items() if k != "gap_support"}
        out[key]["file"] = rel
        out[key]["uncertified"] = [{k: r.get(k) for k in ("reference", "term", "mux", "m", "n_free", "support_used",
                                                          "support_lb", "milp_status", "walk_cnots")}
                                   for r in s["gap_support"]]
# Aer and native
for rel in ("c2x3/aer_compressed_circuit_llm_2x3_classA.json", "c2x3/aer_compressed_circuit_llm_2x3_classB.json",
            *sorted(os.path.relpath(x, D) for x in __import__("glob").glob(os.path.join(D, "aer_compressed_circuit_llm_2x4_*_v2_sample_*.json"))),
            "c2x3/native_compressed_circuit_llm_2x3_classA.json", "c2x3/native_compressed_circuit_llm_2x3_classB.json",
            "native_compressed_circuit_llm_2x4_classA_v2.json", "native_compressed_circuit_llm_2x4_classB_v2.json"):
    if os.path.exists(_abs(rel)):
        out[rel] = load(rel)["summary"]
for rel in sorted(os.path.relpath(x, D) for x in __import__("glob").glob(os.path.join(D, "aer_compressed_circuit_llm_2x4_*_v2_sample_*.json"))):
    out[rel + ":circuits"] = load(rel)["circuits"]
if os.path.exists(os.path.join(D, "cert_it6_operator_plaq1_long.json")):
    out["cert_plaq1_long"] = {k: v for k, v in load("cert_it6_operator_plaq1_long.json").items()
                              if k in ("support_used", "support_lb", "support_ub_found", "status", "M_theta", "milp_wall_s")}
# frozen 2x3 family and its f (quoted from the package files)
root = os.path.dirname(STUDY)
with open(os.path.join(root, "data", "quantinuum", "circuits_2x3", "index.json")) as fh:
    idx = json.load(fh)
with open(os.path.join(root, "validation", "Q0P_2x3.json")) as fh:
    q0p = json.load(fh)
out["frozen_2x3"] = {"index_summary": idx["summary"], "source": "data/quantinuum/circuits_2x3/index.json",
                     "Q0P_2x3_status": q0p.get("status"),
                     "Q0P_2x3_f_gate_only": {dv: {kk: q0p["data"]["stage_A"]["predict"]["devices"][dv].get(kk)
                                                  for kk in ("device", "f_gate_only_mean", "f_gate_only_worst")}
                                             for dv in q0p["data"]["stage_A"]["predict"]["devices"]},
                     "Q0P_2x3_source": "validation/Q0P_2x3.json data.stage_A.predict.devices"}
write_json("data/report004_tables.json", out, produced_by="2x4_compression_using_ai_v1/scripts/report004_tables.py",
           parameters={}, t_start=t0)
print(json.dumps({k: v for k, v in out.items() if not k.startswith("per_term_2x4") or k.endswith("sums")},
                 indent=1, default=str)[:6000])
