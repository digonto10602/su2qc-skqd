"""Collect the numbers of a loop iteration into data/summary_<label>.json and print the markdown tables used in
reports/ (every number in the report tables comes from here; nothing is typed by hand).

Inputs: data/archive_<label>.json, data/eval_arch_<label>_{input,operator}_pp_all75_part{0,1,2}.json,
data/eval_arch_<label>_input_pp_terms_part{0,1,2}.json, data/eval_arch_<label>_operator_pp_terms.json,
data/p2_0_harness_baseline.json, optional data/native_<label>_{input,operator}.json, data/approx_tiers.json.
Usage: python scripts/summarise.py --label it5
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.env import STUDY, write_json        # noqa: E402

TERMS = [f"hop{l}" for l in range(10)] + ["plaq0", "plaq1", "plaq2"]


def load(p):
    p = p if os.path.isabs(p) else os.path.join(STUDY, p)
    with open(p) as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--history", default="", help="comma list of archive labels for the iteration table")
    args = ap.parse_args()
    L = args.label
    arch = load(f"data/archive_{L}.json")
    base = load("data/p2_0_harness_baseline.json")
    out = {"label": L}
    # ---- per-term costs
    rows = []
    for nm in TERMS:
        b = base["terms"][nm]["counts"]["n_2q"]
        op = arch["operator"][nm]["best"]
        inp = [arch["input"][r][nm]["best"] for r in arch["input"] if nm in arch["input"][r]]
        inp = [x for x in inp if x]
        rows.append({"term": nm, "baseline": b, "operator_best": op["n_2q"], "operator_label": op["label"],
                     "input_min": min(x["n_2q"] for x in inp), "input_max": max(x["n_2q"] for x in inp),
                     "input_labels": sorted({x["label"] for x in inp})})
    out["terms"] = rows
    # ---- circuits
    for cls in ("input", "operator"):
        circ = {}
        pr = os.path.join(STUDY, "data", f"eval_arch_{L}_{cls}_pp_all75_pruned.json")
        files = [pr] if os.path.exists(pr) else \
            sorted(glob.glob(os.path.join(STUDY, "data", f"eval_arch_{L}_{cls}_pp_all75_part*.json")))
        for p in files:
            circ.update(load(p)["circuits"])
        if not circ:
            continue
        vals = list(circ.values())
        s = {"n_circuits": len(circ), "n_pass": sum(v["verification"]["pass"] for v in vals),
             "n_2q_min": min(v["counts"]["n_2q"] for v in vals), "n_2q_max": max(v["counts"]["n_2q"] for v in vals),
             "n_2q_mean": sum(v["counts"]["n_2q"] for v in vals) / len(vals),
             "depth_2q_min": min(v["counts"]["depth_2q"] for v in vals),
             "depth_2q_max": max(v["counts"]["depth_2q"] for v in vals),
             "n_1q_mean": sum(v["counts"]["n_1q"] for v in vals) / len(vals),
             "max_dev_phase_aligned": max(v["verification"]["max_dev_phase_aligned"] for v in vals),
             "max_abs_leakage": max(abs(v["verification"]["leakage"]) for v in vals),
             "max_leakage_direct": max(v["verification"].get("leakage_direct", float("nan")) for v in vals),
             "max_l2_dev": max(v["verification"].get("l2_dev_phase_aligned", float("nan")) for v in vals),
             "max_prune_bound": max(v["verification"].get("prune_bound", 0.0) for v in vals),
             "max_certified_dev": max(v["verification"].get("certified_max_dev",
                                                             v["verification"]["max_dev_phase_aligned"]) for v in vals),
             "max_certified_leakage": max(v["verification"].get("certified_leakage", float("nan")) for v in vals),
             "method": vals[0]["verification"].get("method", "exact sparse_sim"),
             "files": [os.path.relpath(p, STUDY) for p in files],
             "ratio_vs_71548_mean": 71548 / (sum(v["counts"]["n_2q"] for v in vals) / len(vals)),
             "by_circuit": {t: {"n_2q": v["counts"]["n_2q"], "depth_2q": v["counts"]["depth_2q"],
                                "dev": v["verification"]["max_dev_phase_aligned"],
                                "leak": v["verification"]["leakage"]} for t, v in sorted(circ.items())}}
        out[f"circuits_{cls}"] = s
    # ---- term checks (A1)
    for cls in ("input", "operator"):
        files = sorted(glob.glob(os.path.join(STUDY, "data", f"eval_arch_{L}_{cls}_pp_terms*.json")))
        worst_dev, worst_leak, n = 0.0, 0.0, 0
        for p in files:
            for nm, t in load(p)["terms"].items():
                for r in t["rows"]:
                    worst_dev = max(worst_dev, r["max_dev"])
                    worst_leak = max(worst_leak, r["max_leak"])
                    n += 1
        if files:
            out[f"A1_{cls}"] = {"n_checks": n, "worst_dev": worst_dev, "worst_leak": worst_leak,
                                "files": [os.path.relpath(p, STUDY) for p in files]}
    # ---- native (+ the package's memory model, flagged ESTIMATE by the package itself)
    import math
    from c2x4.env import ROOT
    devtab = json.load(open(os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")))
    mm = devtab["memory_model"]
    for cls in ("input", "operator"):
        p = os.path.join(STUDY, "data", f"native_{L}_{cls}.json")
        if os.path.exists(p):
            rows_n = load(p)["rows"]
            for r in rows_n:
                c = r["native_counts"]
                mem = {}
                for key, spec in devtab["specs"].items():
                    if key not in mm["memory_rate_per_qubit_per_s"] or "eps2" not in spec:
                        continue
                    name = spec.get("device_name", key)
                    zones = spec.get("zones", 1)
                    rounds = max(math.ceil(c["n_zz"] / zones), c["depth_2q"])
                    mem[name] = {sc: r["clean_shot_fraction_gate_only"][name] *
                                 math.exp(-28 * rounds * t * mm["memory_rate_per_qubit_per_s"][key])
                                 for sc, t in mm["t_round_scenarios_s"].items()}
                    mem[name]["rounds"] = rounds
                    mem[name]["qubits_available"] = spec.get("qubits")
                r["f_with_memory_ESTIMATE"] = mem
            out[f"native_{cls}"] = rows_n
    out["memory_model_source"] = {"file": "data/quantinuum/devices_20261002.json memory_model",
                                  "flag": mm["flag"], "S_idle": mm["S_idle"], "rounds_rule": mm["rounds_rule"]}
    # ---- loop history (term sums per archive; diagonal group not included)
    hist = []
    for H in [h for h in args.history.split(",") if h]:
        a = load(f"data/archive_{H}.json")
        props = sorted({c["label"] for nm in TERMS for c in a["operator"][nm]["candidates"]} |
                       {c["label"] for r in a["input"].values() for nm in TERMS if nm in r for c in r[nm]["candidates"]})
        op = sum(a["operator"][nm]["best"]["n_2q"] for nm in TERMS)
        per_ref = {r: sum(a["input"][r][nm]["best"]["n_2q"] for nm in TERMS) for r in a["input"]}
        hist.append({"archive": H, "proposals": props, "operator_term_sum": op,
                     "input_term_sum_min": min(per_ref.values()), "input_term_sum_max": max(per_ref.values()),
                     "input_term_sum_mean": sum(per_ref.values()) / len(per_ref), "input_by_ref": per_ref})
    out["history"] = hist
    write_json(f"data/summary_{L}.json", out, produced_by="2x4_compression_using_ai_v1/scripts/summarise.py",
               parameters={"label": L})
    # ---- markdown
    print("| term | baseline IR CX | operator-exact best (proposal) | input-specific best, range over 15 references |")
    print("|---|---|---|---|")
    for r in rows:
        print(f"| {r['term']} | {r['baseline']} | {r['operator_best']} ({r['operator_label']}) | "
              f"{r['input_min']}–{r['input_max']} ({', '.join(r['input_labels'])}) |")
    print(f"| sum | {sum(r['baseline'] for r in rows)} | {sum(r['operator_best'] for r in rows)} | "
          f"{sum(r['input_min'] for r in rows)}–{sum(r['input_max'] for r in rows)} (term-wise extremes) |")
    if hist:
        print("\n| iteration | proposals available | class A term sum | class B term sum per reference (min / mean / max) |")
        print("|---|---|---|---|")
        for h in hist:
            print(f"| {h['archive']} | {', '.join(h['proposals'])} | {h['operator_term_sum']} | "
                  f"{h['input_term_sum_min']} / {h['input_term_sum_mean']:.1f} / {h['input_term_sum_max']} |")
    for cls in ("input", "operator"):
        s = out.get(f"circuits_{cls}")
        if s:
            print(f"\n{cls}: {s['n_pass']}/{s['n_circuits']} pass; ZZ {s['n_2q_min']}–{s['n_2q_max']} (mean "
                  f"{s['n_2q_mean']:.1f}, {s['ratio_vs_71548_mean']:.1f}x below 71 548); depth_2q "
                  f"{s['depth_2q_min']}–{s['depth_2q_max']}; max dev {s['max_dev_phase_aligned']:.2e}; "
                  f"max |leak| {s['max_abs_leakage']:.2e}; max direct leak {s['max_leakage_direct']:.2e}; "
                  f"max l2 {s['max_l2_dev']:.2e}; max prune bound {s['max_prune_bound']:.2e}; max certified dev "
                  f"{s['max_certified_dev']:.2e}; max certified leak {s['max_certified_leakage']:.2e}")
        nat = out.get(f"native_{cls}")
        if nat:
            devs = sorted(nat[0]["clean_shot_fraction_gate_only"])
            print(f"\n| circuit ({cls}) | level | ZZ | 2q depth | PhasedX | Q1L | rounding bound B | "
                  + " | ".join(f"f {d}" for d in devs) + " |")
            print("|---|---|---|---|---|---|---|" + "---|" * len(devs))
            for r in nat:
                c = r["native_counts"]
                Bv = "–" if r["rounding_bound_B"] is None else f"{r['rounding_bound_B']:.1e}"
                q = "not applicable (level 2 rewrites gates; unverified)" if r["Q1L_ok"] is None else str(r["Q1L_ok"])
                print(f"| {r['tag']} | {r['level']} | {c['n_zz']} | {c['depth_2q']} | {c['n_phasedx']} | {q} | {Bv} | "
                      + " | ".join(f"{r['clean_shot_fraction_gate_only'][d]:.3f}" for d in devs) + " |")
        if nat:
            print(f"\nf with the package's memory model (ESTIMATE, t_round low/mid/high), {cls}:")
            for r in nat:
                print(f"  {r['tag']} level {r['level']}: " + "; ".join(
                    f"{d} {v['low']:.3f}/{v['mid']:.3f}/{v['high']:.3f} (rounds {v['rounds']}, qubits {v['qubits_available']})"
                    for d, v in r["f_with_memory_ESTIMATE"].items()))
        a = out.get(f"A1_{cls}")
        if a:
            print(f"A1 {cls}: {a['n_checks']} checks, worst dev {a['worst_dev']:.2e}, worst leak {a['worst_leak']:.2e}")


if __name__ == "__main__":
    main()
