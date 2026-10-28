"""Collect every number of the k = 5 add-on families of 2x2 and 2x3 (owner 2026-10-28, notes/014) into
data/k5_addons_2x2_2x3.json.  Reads only files written by the production scripts:

  * the frozen add-on family files and their base (k = 1..4) family files: file sha256 (base checked against the
    `family_file_sha256` recorded in the base native export's index.json, i.e. the base files are unchanged), dt,
    counts per circuit compared with EVERY k = 1..4 circuit of the same reference in the base file (n_2q, n_1q,
    depth_2q, ops, and the gate skeleton = gate names and qubits with angles ignored);
  * the certified pruned evaluation (eval_family.py, rounding term included) and the Aer statevector check
    (verify_aer_family.py, incl. the random-superposition test, seeds 11 and 12, and the class-B phase check);
  * the native export folders (index.json + manifests): ZZ / PhasedX / depth-2q / HQC per shot, Q1, Q1L, rounding
    bound B, round trips, calibration copies (sha256 equal to the frozen calibration files); native ZZ / PhasedX
    compared with the base export's k = 1..4 circuits of the same reference;
  * the local dry run of scripts/quantinuum_submit.py (session.json read only);
  * read-only cross-check against the package's frozen k = 5 folders data/quantinuum/circuits_2x{2,3}_k5/ (built by
    another agent): for every id whose manifest exists there, equal dt, k, twoB, reference and reference_int.

Usage (coding env): python scripts/summarise_k5_addons.py
  (dry-run sessions: <lattice folder>/data/c2x<L>/dryrun/session_class<A|B>_k5.json, copied from the --out folder of
  scripts/quantinuum_submit.py --dry-run --all --records-only; or --dryrun-root <dir holding dryrun_<family>/>)
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

from c2x4.env import lattice_data, lattice_study, write_json                      # noqa: E402
from c2x4.families import decode_gates, family_header, family_path, load_frozen   # noqa: E402

FAMS = [("2x2", "A"), ("2x2", "B"), ("2x3", "A"), ("2x3", "B")]


def sha256_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def rng(xs):
    return {"min": min(xs), "max": max(xs), "mean": sum(xs) / len(xs)}


def skel(gates):
    return hashlib.sha256(repr([(str(n), [int(q) for q in qs]) for n, qs, _p in gates]).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun-root", default=None)
    args = ap.parse_args()
    t0 = time.time()
    out = {"families": {}}
    for lat, cls in FAMS:
        L = int(lat[2])
        base, name = f"compressed_circuit_llm_{lat}_class{cls}", f"compressed_circuit_llm_{lat}_class{cls}_k5"
        cname = "operator" if cls == "A" else "input"
        hb, ha = family_header(base), family_header(name)
        bfile = load_frozen(base)["circuits"]
        afile = load_frozen(name)["circuits"]
        bexp = os.path.join(lattice_study(lat), "data", "families", f"native_{lat}", base)
        bidx = json.load(open(os.path.join(bexp, "index.json")))
        rec = {"lattice": lat, "class": cls, "family": name, "base_family": base,
               "family_file": os.path.relpath(family_path(name), ROOT), "family_file_sha256": sha256_file(family_path(name)),
               "base_file": os.path.relpath(family_path(base), ROOT), "base_file_sha256": sha256_file(family_path(base)),
               "base_file_sha256_at_base_export": bidx["family_file_sha256"],
               "base_file_unchanged": sha256_file(family_path(base)) == bidx["family_file_sha256"],
               "addon_of_recorded": ha.get("addon_of"),
               "spec": ha["spec"], "spec_equals_base": ha["spec"] == hb["spec"],
               "dt": ha["dt"], "dt_equals_base": ha["dt"] == hb["dt"], "dt_source": ha["dt_source"],
               "n_circuits": len(afile), "ids": [c["metadata"]["circuit_id"] for c in afile],
               "k_values": sorted({c["metadata"]["k"] for c in afile}),
               "theta_equals_5dt": all(c["metadata"]["theta"] == 5 * c["metadata"]["dt"] for c in afile),
               "n_2q": rng([c["metadata"]["n_2q"] for c in afile]),
               "n_1q": rng([c["metadata"]["n_1q"] for c in afile]),
               "depth_2q": rng([c["metadata"]["depth_2q"] for c in afile])}
        # counts / skeleton vs base k = 1..4 of the same reference
        per = {}
        for c in afile:
            m = c["metadata"]
            sib = [b for b in bfile if b["metadata"]["twoB"] == m["twoB"] and b["metadata"]["reference"] == m["reference"]]
            sk = skel(decode_gates(c["gates"]))
            per[m["circuit_id"]] = {
                "n_2q": m["n_2q"], "n_1q": m["n_1q"], "depth_2q": m["depth_2q"],
                "base_k": sorted(b["metadata"]["k"] for b in sib),
                "counts_equal_base_k1_4": all((b["metadata"]["n_2q"], b["metadata"]["n_1q"], b["metadata"]["depth_2q"],
                                               b["metadata"]["ops"]) == (m["n_2q"], m["n_1q"], m["depth_2q"], m["ops"])
                                              for b in sib),
                "skeleton_equal_base_k1_4": all(skel(decode_gates(b["gates"])) == sk for b in sib)}
        rec["per_circuit_vs_base"] = per
        rec["all_counts_equal_base_k1_4"] = all(v["counts_equal_base_k1_4"] and v["base_k"] == [1, 2, 3, 4]
                                                for v in per.values())
        rec["all_skeletons_equal_base_k1_4"] = all(v["skeleton_equal_base_k1_4"] for v in per.values())
        # certified pruned evaluation
        ep = os.path.join(lattice_data(lat), f"eval_arch_L{L}_it1_{cname}_pp2_k5_pruned.json")
        ev = json.load(open(ep))
        s = ev["summary"]
        rec["certified_eval"] = {"file": os.path.relpath(ep, ROOT), "n": s["n_circuits"], "n_pass": s["n_pass"],
                                 "max_dev_phase_aligned": s["max_dev_phase_aligned"],
                                 "max_certified_dev": float(s["max_certified_dev"]),
                                 "max_certified_leakage": float(s["max_certified_leakage"]),
                                 "max_abs_leakage": s["max_abs_leakage"], "prune_tau": ev["parameters"]["prune_tau"],
                                 "term_level_worst_dev": max(t["worst_dev"] for t in ev["terms"].values()),
                                 "term_level_worst_leak": max(t["worst_leak"] for t in ev["terms"].values()),
                                 "bar": s["bar"]}
        # Aer
        apth = os.path.join(lattice_data(lat), f"aer_{name}.json")
        aer = json.load(open(apth))
        rec["aer"] = {"file": os.path.relpath(apth, ROOT), **{k: v for k, v in aer["summary"].items()},
                      "engine": aer["engine"]}
        # native export
        d = os.path.join(lattice_study(lat), "data", "families", f"native_{lat}", name)
        idx = json.load(open(os.path.join(d, "index.json")))
        mans = [json.load(open(os.path.join(d, c + ".manifest.json"))) for c in idx["circuits"]]
        bmans = {c: json.load(open(os.path.join(bexp, c + ".manifest.json"))) for c in bidx["circuits"]}
        q1 = [m["levels"]["0"]["passes_Q1"] for m in mans]
        se = [m["levels"]["0"]["state_vs_exact_target"] for m in mans]
        nat_vs_base = {}
        for m in mans:
            bs = [bm for bm in bmans.values() if bm["twoB"] == m["twoB"] and bm["reference"] == m["reference"]]
            nat_vs_base[m["id"]] = {"n_zz": m["counts"]["n_zz"], "n_phasedx": m["counts"]["n_phasedx"],
                                    "base_n_zz": sorted({bm["counts"]["n_zz"] for bm in bs}),
                                    "base_n_phasedx": sorted({bm["counts"]["n_phasedx"] for bm in bs}),
                                    "base_k": sorted(bm["k"] for bm in bs)}
        cal_ok = {}
        for c in idx["calibration"]:
            cm = json.load(open(os.path.join(d, c + ".manifest.json")))
            fdir = os.path.join(ROOT, cm["copied_from"])
            cal_ok[c] = all(sha256_file(os.path.join(d, cm["files"][k])) == sha256_file(os.path.join(fdir, cm["files"][k]))
                            for k in ("json", "qasm"))
        rec["native"] = {
            "export_dir": os.path.relpath(d, ROOT), "index_sha256": sha256_file(os.path.join(d, "index.json")),
            "ids": idx["circuits"], "calibration": idx["calibration"], "calibration_byte_identical": cal_ok,
            "calibration_copied_from": sorted({json.load(open(os.path.join(d, c + ".manifest.json")))["copied_from"]
                                               for c in idx["calibration"]}),
            "n_zz": rng([m["counts"]["n_zz"] for m in mans]), "n_phasedx": rng([m["counts"]["n_phasedx"] for m in mans]),
            "depth_2q": rng([m["counts"]["depth_2q"] for m in mans]),
            "hqc_per_shot": rng([m["hqc_per_shot"] for m in mans]),
            "f_gate_only_H2_2": rng([m["clean_shot_fraction_gate_only"]["H2-2"] for m in mans]),
            "native_zz_equals_ir_2q": all(m["counts"]["n_zz"] == m["ir_n_2q"] for m in mans),
            "n_Q1_pass": sum(1 for x in q1 if x is True),
            "max_abs_dpsi_vs_exact": max(x["max_abs_dpsi"] for x in se),
            "max_leakage_vs_exact": max(x["leakage"] for x in se),
            "max_abs_dpsi_vs_ir": max(m["levels"]["0"]["state_vs_original_ir"]["max_abs_dpsi"] for m in mans),
            "n_Q1L_pass": sum(1 for m in mans if m["Q1L"]["ok"]),
            "max_Q1L_rounding_state_bound_B": max(m["Q1L"]["rounding_state_bound_B"] for m in mans),
            "round_trips_all_ok": all(m["round_trips"]["json_counts_equal"] and m["round_trips"]["qasm_counts_equal"]
                                      and m["round_trips"]["json"]["max_abs_dpsi"] < 1e-10
                                      and m["round_trips"]["qasm"]["max_abs_dpsi"] < 1e-10 for m in mans),
            "dt_per_circuit": {m["id"]: m["dt"] for m in mans},
            "native_vs_base_k1_4": nat_vs_base,
            "native_counts_equal_base_k1_4": all(v["base_n_zz"] == [v["n_zz"]] and v["base_n_phasedx"] == [v["n_phasedx"]]
                                                 and v["base_k"] == [1, 2, 3, 4] for v in nat_vs_base.values())}
        # dry run
        sp = (os.path.join(args.dryrun_root, f"dryrun_{name}", "session.json") if args.dryrun_root else
              os.path.join(lattice_data(lat), "dryrun", f"session_class{cls}_k5.json"))
        if os.path.exists(sp):
            s = json.load(open(sp))
            rec["dry_run"] = {"session": os.path.relpath(sp, ROOT), "session_sha256": sha256_file(sp), "n_jobs": len(s["jobs"]),
                              "n_circuit_jobs": sum(1 for j in s["jobs"] if not j["circuit_id"].startswith("CAL_")),
                              "shots_total": sum(j["n_shots"] for j in s["jobs"]),
                              "shots_per_circuit": sorted({j["n_shots"] for j in s["jobs"]}),
                              "hqc_estimate_total": s["hqc_estimate_total"],
                              "hqc_estimate_circuits_only": float(sum(j["hqc_estimate"] for j in s["jobs"]
                                                                      if not j["circuit_id"].startswith("CAL_"))),
                              "records_only": bool(s.get("records_only", False)),
                              "statuses": sorted({j["status"] for j in s["jobs"]}),
                              "index_sha256_matches": s["index_sha256"] == rec["native"]["index_sha256"],
                              "circuits_arg": s["arguments"]["circuits"]}
        # read-only cross-check against the package's frozen k = 5 folder (another agent's work)
        fk5 = os.path.join(ROOT, "data", "quantinuum", f"circuits_{lat}_k5")
        xc = {}
        for m in mans:
            fp = os.path.join(fk5, m["id"] + ".manifest.json")
            if os.path.exists(fp):
                fm = json.load(open(fp))
                xc[m["id"]] = {key: fm.get(key) == m[key] for key in ("dt", "k", "twoB", "reference", "reference_int")}
        rec["frozen_k5_crosscheck"] = {"dir": os.path.relpath(fk5, ROOT), "exists": os.path.isdir(fk5),
                                       "index_present": os.path.exists(os.path.join(fk5, "index.json")),
                                       "n_manifests_found": len(xc), "n_ids": len(mans),
                                       "all_equal": all(all(v.values()) for v in xc.values()) if xc else None,
                                       "per_id": xc}
        out["families"][name] = rec
    p = write_json(os.path.join(STUDY, "data", "k5_addons_2x2_2x3.json"), out,
                   produced_by="2x4_compression_using_ai_v1/scripts/summarise_k5_addons.py",
                   parameters={"dryrun_root": args.dryrun_root}, t_start=t0)
    print(p)
    for fam, r in out["families"].items():
        n, dr = r["native"], r.get("dry_run", {})
        print(fam, r["n_circuits"], "2q", r["n_2q"]["min"], r["n_2q"]["max"], "eq-base", r["all_counts_equal_base_k1_4"],
              r["all_skeletons_equal_base_k1_4"], "| cert", f"{r['certified_eval']['max_certified_dev']:.1e}",
              "aer", f"{r['aer']['max_abs_dpsi']:.1e}", "| ZZ", n["n_zz"]["min"], n["n_zz"]["max"], "Q1", n["n_Q1_pass"],
              "Q1L", n["n_Q1L_pass"], f"B {n['max_Q1L_rounding_state_bound_B']:.1e}", "nat-eq-base",
              n["native_counts_equal_base_k1_4"], "| dry", dr.get("n_jobs"), dr.get("hqc_estimate_total"),
              "| frozen-k5 x-check", r["frozen_k5_crosscheck"]["n_manifests_found"], r["frozen_k5_crosscheck"]["all_equal"])


if __name__ == "__main__":
    main()
