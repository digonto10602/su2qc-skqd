"""Review 001, item 5: native level-0 pytket counts (package converter) and the package's f formula.
Run with ~/.local/share/su2qc-quantinuum/venv/bin/python."""
import json, math, os, pickle, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))
from skqd.device_req import clean_shot_fraction
from skqd.quantinuum_native import ir_to_pytket, compile_native
import pytket
circs = pickle.load(open(os.path.join(HERE, "001_cache", "circuits.pkl"), "rb"))
dev = json.load(open(os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")))["specs"]["quantinuum_h2_2"]
e2, e1, ero = dev["eps2"], dev["eps1"], 0.5 * (dev["eps_ro_0"] + dev["eps_ro_1"])
genie = {"A": json.load(open(os.path.join(HERE, "..", "data", "native_it5_operator.json"))),
         "B": json.load(open(os.path.join(HERE, "..", "data", "native_it5_input.json")))}
out = {"device": "H2-2", "eps2": e2, "eps1": e1, "eps_ro": ero, "eps_ro_rule": "mean(eps_ro_0, eps_ro_1) as p1_device_threshold / package",
       "n_meas": 28, "pytket": pytket.__version__, "rows": []}
for key in [("B", 2, 230, 1), ("A", 0, 102, 1)]:
    g = circs[key]
    nat = compile_native(ir_to_pytket(g, 28, measure=True), "H2-2", optimisation_level=0)
    ops = {}
    for cmd in nat.get_commands():
        ops[cmd.op.type.name] = ops.get(cmd.op.type.name, 0) + 1
    n_zz = ops.get("ZZPhase", 0) + ops.get("ZZMax", 0) + ops.get("TK2", 0)
    n_px = ops.get("PhasedX", 0)
    from pytket import OpType
    d2 = nat.depth_by_type({OpType.ZZPhase, OpType.ZZMax, OpType.TK2})
    f_pkg = clean_shot_fraction(n_zz, n_px, 28, e2, e1, ero)
    f_hand = (1 - e2) ** n_zz * (1 - e1) ** n_px * (1 - ero) ** 28
    tag = f"B{key[1]//2}_ref{key[2]}_k{key[3]}"
    gr = [r for r in genie[key[0]]["rows"] if r["tag"] == tag and r["level"] == 0] if "rows" in genie[key[0]] else []
    out["rows"].append({"class": key[0], "tag": tag, "native_ops": ops, "n_zz": n_zz, "n_phasedx": n_px,
                        "depth_2q_native": d2, "f_H2_2_package_formula": f_pkg, "f_H2_2_direct_product": f_hand,
                        "genie_row": ({kk: gr[0][kk] for kk in ("native_counts", "f") if kk in gr[0]} if gr else None)})
    print(key, n_zz, n_px, d2, f_pkg, f_hand)
json.dump(out, open(os.path.join(HERE, "001_native_f.json"), "w"), indent=1, default=str)
