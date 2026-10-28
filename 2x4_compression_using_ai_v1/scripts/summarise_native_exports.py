"""Collect the numbers of the 2x3 / 2x4 native exports (notes/013) into data/native_exports_2x3_2x4.json: per family
the export folder, index.json sha256, ZZ / PhasedX / depth-2q / HQC-per-shot ranges, Q1 and Q1L pass counts, the
largest Q1L rounding bound, the circuits without a frozen counterpart, the calibration copies, and the local dry run
of scripts/quantinuum_submit.py (session.json read only: job count, shots, formula HQC total, statuses).

Usage (coding env): python scripts/summarise_native_exports.py --dryrun-root <dir holding dryrun_<family>/>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(STUDY, "src"))

from c2x4.env import lattice_study, write_json        # noqa: E402

EXPORTS = [("2x3", "compressed_circuit_llm_2x3_classA"), ("2x3", "compressed_circuit_llm_2x3_classB"),
           ("2x4", "compressed_circuit_llm_2x4_classA"), ("2x4", "compressed_circuit_llm_2x4_classB"),
           ("2x4", "compressed_circuit_llm_2x4_classA_v2"), ("2x4", "compressed_circuit_llm_2x4_classB_v2")]


def sha256_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def rng(xs):
    return {"min": min(xs), "max": max(xs), "mean": sum(xs) / len(xs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun-root", required=True)
    args = ap.parse_args()
    t0 = time.time()
    out = {"families": {}}
    for lat, fam in EXPORTS:
        d = os.path.join(lattice_study(lat), "data", "families", f"native_{lat}", fam)
        idx = json.load(open(os.path.join(d, "index.json")))
        mans = [json.load(open(os.path.join(d, c + ".manifest.json"))) for c in idx["circuits"]]
        q1 = [m["levels"]["0"]["passes_Q1"] for m in mans]
        se = [m["levels"]["0"]["state_vs_exact_target"] for m in mans if m["levels"]["0"]["state_vs_exact_target"]]
        rec = {"lattice": lat, "export_dir": os.path.relpath(d, ROOT), "family_in_files": idx["family"],
               "index_sha256": sha256_file(os.path.join(d, "index.json")),
               "n_circuits": len(mans), "calibration": idx["calibration"],
               "calibration_files": {c: json.load(open(os.path.join(d, c + ".manifest.json")))["files"]
                                     for c in idx["calibration"]},
               "files_gzipped": any(m["files"]["json"].endswith(".gz") for m in mans),
               "n_zz": rng([m["counts"]["n_zz"] for m in mans]),
               "n_phasedx": rng([m["counts"]["n_phasedx"] for m in mans]),
               "depth_2q": rng([m["counts"]["depth_2q"] for m in mans]),
               "hqc_per_shot": rng([m["hqc_per_shot"] for m in mans]),
               "f_gate_only_H2_2": rng([m["clean_shot_fraction_gate_only"]["H2-2"] for m in mans]),
               "state_check": sorted({m.get("state_check", "aer") for m in mans}),
               "n_Q1_pass": sum(1 for x in q1 if x is True), "n_Q1_not_computed": sum(1 for x in q1 if x is None),
               "max_abs_dpsi_vs_exact": max((x["max_abs_dpsi"] for x in se), default=None),
               "max_leakage_vs_exact": max((x["leakage"] for x in se), default=None),
               "n_Q1L_pass": sum(1 for m in mans if m["Q1L"]["ok"]),
               "max_Q1L_rounding_state_bound_B": max(m["Q1L"]["rounding_state_bound_B"] for m in mans),
               "round_trips_all_ok": all(
                   (m["round_trips"].get("json_Q1L_ok", True) and m["round_trips"].get("qasm_Q1L_ok", True)
                    and m["round_trips"]["json_counts_equal"] and m["round_trips"]["qasm_counts_equal"]) for m in mans),
               "without_frozen_counterpart": [m["id"] for m in mans if m["frozen_counterpart"]["id"] is None],
               "frozen_counterpart_dir": idx["frozen_counterpart"]["dir"],
               "frozen_counterpart_suffix": idx["frozen_counterpart"].get("id_suffix", "")}
        sp = os.path.join(args.dryrun_root, f"dryrun_{fam}", "session.json")
        if os.path.exists(sp):
            s = json.load(open(sp))
            rec["dry_run"] = {"session": sp, "n_jobs": len(s["jobs"]),
                              "n_circuit_jobs": sum(1 for j in s["jobs"] if not j["circuit_id"].startswith("CAL_")),
                              "shots_total": sum(j["n_shots"] for j in s["jobs"]),
                              "shots_per_circuit": sorted({j["n_shots"] for j in s["jobs"]}),
                              "hqc_estimate_total": s["hqc_estimate_total"],
                              "hqc_estimate_circuits_only": float(sum(j["hqc_estimate"] for j in s["jobs"]
                                                                      if not j["circuit_id"].startswith("CAL_"))),
                              "records_only": bool(s.get("records_only", False)),
                              "statuses": sorted({j["status"] for j in s["jobs"]}),
                              "index_sha256_matches": s["index_sha256"] == rec["index_sha256"],
                              "circuits_arg": s["arguments"]["circuits"]}
        out["families"][fam] = rec
    p = write_json("data/native_exports_2x3_2x4.json", out, produced_by="2x4_compression_using_ai_v1/scripts/"
                   "summarise_native_exports.py", parameters={"dryrun_root": args.dryrun_root}, t_start=t0)
    print(p)
    for fam, r in out["families"].items():
        dr = r.get("dry_run", {})
        print(fam, r["n_circuits"], "ZZ", r["n_zz"]["min"], r["n_zz"]["max"], "PX", r["n_phasedx"]["min"],
              r["n_phasedx"]["max"], "HQC/shot", round(r["hqc_per_shot"]["min"], 4), round(r["hqc_per_shot"]["max"], 4),
              "Q1", r["n_Q1_pass"], "Q1L", r["n_Q1L_pass"], "| dry", dr.get("n_jobs"), dr.get("hqc_estimate_total"))


if __name__ == "__main__":
    main()
