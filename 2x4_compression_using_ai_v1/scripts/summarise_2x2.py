"""Collect the numbers of the 2x2 compressed families (notes/011) into
2x2_compression_using_ai_v1/data/c2x2/summary_2x2.json (one folder per lattice, notes/012): IR and native
counts, two-qubit depth, gate-only clean-shot fraction f (skqd.device_req.clean_shot_fraction, the formula of
scripts/native_family.py) for both classes AND for the package's frozen 2x2 family (from its manifests, same formula,
same device table), the verification numbers (certified pruned, Aer, random superposition, class-B phase, native
Q1/Q1L), and the local dry run of scripts/quantinuum_submit.py on the exports (session.json + counts files, read only).

Usage (coding env): python scripts/summarise_2x2.py --dryrun-dir <dir holding dryrun_2x2_class{A,B}/>
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(STUDY, "src"))
sys.path.insert(0, os.path.join(ROOT, "src"))

from c2x4.env import lattice_data, lattice_study, write_json   # noqa: E402
from skqd.device_req import clean_shot_fraction       # noqa: E402

D = lattice_data("2x2")                                               # 2x2_compression_using_ai_v1/data/c2x2
NAT = os.path.join(lattice_study("2x2"), "data", "families", "native_2x2")
FROZEN = os.path.join(ROOT, "data", "quantinuum", "circuits_2x2")


def load(p):
    with open(p) as fh:
        return json.load(fh)


def f_table(n_zz, n_px, n_meas, dev):
    out = {}
    for key, s_ in dev.items():
        if "eps2" not in s_:
            continue
        ero = 0.5 * (s_["eps_ro_0"] + s_["eps_ro_1"])
        out[s_.get("device_name", key)] = clean_shot_fraction(n_zz, n_px, n_meas, s_["eps2"], s_["eps1"], ero)
    return out


def rng(vals):
    return {"min": min(vals), "max": max(vals), "mean": float(np.mean(vals))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun-dir", required=True)
    args = ap.parse_args()
    t0 = time.time()
    dev = load(os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json"))["specs"]
    out = {"classes": {}}
    # ---- frozen package 2x2 family, same formula
    fidx = load(os.path.join(FROZEN, "index.json"))
    fr = []
    for cid in fidx["circuits"]:
        m = load(os.path.join(FROZEN, cid + ".manifest.json"))
        c = m["counts"]
        fr.append({"id": cid, "n_zz": c["n_zz"], "n_phasedx": c["n_phasedx"], "depth_2q": c["depth_2q"],
                   "f": f_table(c["n_zz"], c["n_phasedx"], c["n_qubits"], dev)})
    devs = sorted(fr[0]["f"])
    out["frozen_2x2"] = {"source": "data/quantinuum/circuits_2x2/<id>.manifest.json counts (frozen level 0)",
                         "n_zz": rng([r["n_zz"] for r in fr]), "n_phasedx": rng([r["n_phasedx"] for r in fr]),
                         "depth_2q": rng([r["depth_2q"] for r in fr]),
                         "f_gate_only": {d: rng([r["f"][d] for r in fr]) for d in devs}}
    for cls in ("A", "B"):
        name = f"compressed_circuit_llm_2x2_class{cls}"
        lab = "operator" if cls == "A" else "input"
        ev = load(os.path.join(D, f"eval_arch_L2_it1_{lab}_pp2_all28_pruned.json"))
        aer = load(os.path.join(D, f"aer_{name}.json"))
        nat = load(os.path.join(D, f"native_{name}.json"))
        idx = load(os.path.join(NAT, name, "index.json"))
        cert = load(os.path.join(D, f"cert_L2_it1_{lab}.json"))
        evc = ev["circuits"].values()
        per = {}
        for cid in idx["circuits"]:
            m = load(os.path.join(NAT, name, cid + ".manifest.json"))
            per[cid] = {"ir_n_2q": m["ir_n_2q"], "ir_depth_2q": m["ir_depth_2q"], "n_zz": m["counts"]["n_zz"],
                        "n_phasedx": m["counts"]["n_phasedx"], "depth_2q_native": m["counts"]["depth_2q"],
                        "f_H2-2": m["clean_shot_fraction_gate_only"]["H2-2"],
                        "frozen_n_zz": m["frozen_counterpart"]["n_zz"]}
        dr_dir = os.path.join(args.dryrun_dir, f"dryrun_2x2_class{cls}")
        ses = load(os.path.join(dr_dir, "session.json"))
        cfiles = sorted(glob.glob(os.path.join(dr_dir, "counts", "*.json")))
        p_ref_obs = []
        for p in cfiles:
            r = load(p)
            if r.get("kind") == "calibration":
                continue
            key = "".join(str((r["reference_int"] >> q) & 1) for q in reversed(range(r["n_qubits"])))
            p_ref_obs.append({"id": r["id"], "shots": r["shots"], "ref_count": r["counts"].get(key, 0),
                              "p_reference_ideal": r["p_reference"]})
        out["classes"][cls] = {
            "family": name, "family_file_sha256": idx["family_file_sha256"],
            "ir": {"n_2q": rng([x["counts"]["n_2q"] for x in evc]), "depth_2q": rng([x["counts"]["depth_2q"] for x in evc])},
            "native": {"n_zz": idx["summary"]["n_zz"], "n_phasedx": idx["summary"]["n_phasedx"],
                       "depth_2q": idx["summary"]["depth_2q"], "hqc_per_shot": idx["summary"]["hqc_per_shot"],
                       "f_gate_only": idx["summary"]["clean_shot_fraction_gate_only"]},
            "per_circuit": per,
            "verification": {
                "certified_pruned": {"n": ev["summary"]["n_circuits"], "n_pass": ev["summary"]["n_pass"],
                                     "max_dev_measured": ev["summary"]["max_dev_phase_aligned"],
                                     "max_certified_dev_incl_rounding": ev["summary"]["max_certified_dev"],
                                     "max_rounding_bound": max(x["verification"]["rounding"]["rounding_bound"]
                                                               for x in evc),
                                     "max_certified_leakage": ev["summary"]["max_certified_leakage"],
                                     "skeleton_k_independent": ev["summary"]["skeleton_k_independent"]["all"],
                                     "file": f"2x2_compression_using_ai_v1/data/c2x2/eval_arch_L2_it1_{lab}_pp2_all28_pruned.json"},
                "aer": {k: aer["summary"][k] for k in ("n", "n_pass", "max_abs_dpsi", "max_leakage_total",
                                                       "max_abs_phase_minus_predicted", "n_2q_consistent",
                                                       "dt_consistent")},
                "random_superposition": aer["summary"].get("random_superposition"),
                "aer_file": f"2x2_compression_using_ai_v1/data/c2x2/aer_{name}.json",
                "native": {"all_Q1": idx["summary"]["all_Q1"], "all_Q1L": idx["summary"]["all_Q1L"],
                           "max_abs_dpsi_vs_exact": idx["summary"]["max_abs_dpsi_vs_exact"],
                           "max_leakage": idx["summary"]["max_leakage"],
                           "max_Q1L_rounding_state_bound_B": idx["summary"]["max_Q1L_rounding_state_bound_B"],
                           "native_family_json_all_Q1L": nat["summary"]["all_Q1L_ok"]},
                "milp_walsh_certificate": cert["summary"]},
            "dry_run": {"session": os.path.join(dr_dir, "session.json"), "n_jobs": len(ses["jobs"]),
                        "shots_total": sum(j["n_shots"] for j in ses["jobs"]),
                        "hqc_estimate_total": ses["hqc_estimate_total"], "status": sorted({j["status"] for j in ses["jobs"]}),
                        "n_counts_files": len(cfiles), "index_sha256": ses["index_sha256"],
                        "reference_hits_A6_noise": p_ref_obs},
        }
    out["comparison"] = {cls: {"n_zz_mean_ratio_vs_frozen": out["classes"][cls]["native"]["n_zz"]["mean"] /
                               out["frozen_2x2"]["n_zz"]["mean"],
                               "f_H2-2_mean": out["classes"][cls]["native"]["f_gate_only"]["H2-2"]["mean"],
                               "f_H2-2_mean_frozen": out["frozen_2x2"]["f_gate_only"]["H2-2"]["mean"]}
                         for cls in ("A", "B")}
    p = write_json(os.path.join(D, "summary_2x2.json"), out, produced_by="2x4_compression_using_ai_v1/scripts/summarise_2x2.py",
                   parameters={"dryrun_dir": args.dryrun_dir, "devices": "data/quantinuum/devices_20261002.json",
                               "f_formula": "clean_shot_fraction(n_zz, n_phasedx, n_qubits, eps2, eps1, (eps_ro_0+eps_ro_1)/2)"},
                   t_start=t0)
    print(json.dumps({"frozen": out["frozen_2x2"], "comparison": out["comparison"]}, indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
