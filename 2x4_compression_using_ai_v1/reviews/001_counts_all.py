"""Review 001: recount ZZ / 2q depth of all 150 rebuilt circuits from qiskit circuit objects; compare with genie's JSON."""
import json, os, pickle, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util
spec = importlib.util.spec_from_file_location("v", os.path.join(HERE, "001_verify_aer.py")); v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
circs = pickle.load(open(os.path.join(HERE, "001_cache", "circuits.pkl"), "rb"))
G = {"A": json.load(open(os.path.join(HERE, "..", "data", "eval_arch_it5_operator_pp_all75_pruned.json"))),
     "B": json.load(open(os.path.join(HERE, "..", "data", "eval_arch_it5_input_pp_all75_pruned.json")))}
rows = {}
mism = []
for (cls, twoB, ref, k), g in sorted(circs.items()):
    c = v.recount(v.to_qiskit(g, 28))
    tag = f"B{twoB//2}_ref{ref}_k{k}"
    gc = G[cls]["circuits"][tag]["counts"]
    ok = (c["n_2q"] == gc["n_2q"] and c["depth_2q"] == gc["depth_2q"] and c["depth_2q_qiskit"] == c["depth_2q"]
          and c["n_gt2q"] == 0)
    rows[f"{cls}:{tag}"] = {"n_2q": c["n_2q"], "depth_2q": c["depth_2q"], "depth_2q_qiskit": c["depth_2q_qiskit"],
                            "n_1q": c["n_1q"], "ops": c["ops"], "n_qubits_touched": c["n_qubits_touched"],
                            "genie_n_2q": gc["n_2q"], "genie_depth_2q": gc["depth_2q"], "match": ok}
    if not ok: mism.append(f"{cls}:{tag}")
summ = {}
for cls in "AB":
    r = [x for kk, x in rows.items() if kk.startswith(cls)]
    summ[cls] = {"n": len(r), "n_2q_min": min(x["n_2q"] for x in r), "n_2q_max": max(x["n_2q"] for x in r),
                 "n_2q_mean": sum(x["n_2q"] for x in r) / len(r),
                 "depth_2q_min": min(x["depth_2q"] for x in r), "depth_2q_max": max(x["depth_2q"] for x in r),
                 "n_1q_mean": sum(x["n_1q"] for x in r) / len(r),
                 "qubits_touched": sorted({x["n_qubits_touched"] for x in r})}
json.dump({"rows": rows, "summary": summ, "mismatches": mism}, open(os.path.join(HERE, "001_counts_all.json"), "w"), indent=1)
print(json.dumps(summ, indent=1), "mismatches", mism)
