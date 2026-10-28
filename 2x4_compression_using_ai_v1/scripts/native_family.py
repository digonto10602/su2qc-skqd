"""Native Quantinuum conversion of a FROZEN family (loader c2x4.families) with the package's own converter
(pytket level 0), the package's conversion proof Q1L (local_equivalence_35a, structured source) and the package's
gate-only clean-shot fraction f (skqd.device_req.clean_shot_fraction, n_1q = PhasedX, n_meas = n_qubits) for every
Quantinuum row of data/quantinuum/devices_20261002.json -- the formula of validation/Q0P_2x3.json, for information.

Run with the isolated venv (never the coding env):
  ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/native_family.py --family compressed_circuit_llm_2x3_classA
Writes data/native_<family>.json (2x4) or <lattice folder>/data/c2x<L>/native_<family>.json (2x3, 2x2; c2x4.env.lattice_data).
"""
from __future__ import annotations

import argparse
import math
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(STUDY, "src"))
sys.path.insert(0, os.path.join(ROOT, "src"))

from c2x4.env import lattice_data, write_json                  # noqa: E402
from c2x4.families import family_header, get_family_ir         # noqa: E402
from skqd.device_req import clean_shot_fraction                # noqa: E402
from skqd.quantinuum_native import (compile_native, ir_to_pytket, local_equivalence_35a,   # noqa: E402
                                    native_counts, pytket_to_ir, versions)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--ids", default="all")
    ap.add_argument("--no-q1l", action="store_true")
    ap.add_argument("--max-wall", type=float, default=1700.0)
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    t_start = time.time()
    hdr = family_header(args.family)
    dev = json.load(open(os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")))["specs"]
    want = None if args.ids == "all" else set(args.ids.split(","))
    rows = []
    truncated = False
    for cid, g, md in get_family_ir(args.family):
        if want is not None and cid not in want:
            continue
        if time.time() - t_start > args.max_wall:
            truncated = True
            break
        n = md["n_qubits"]
        # the package converter has no 'cz'; CZ = CP(pi) exactly (diag(1, 1, 1, -1)), one ZZPhase either way
        g = [("cp", qs, math.pi) if nm == "cz" else (nm, qs, par) for nm, qs, par in g]
        t0 = time.time()
        nat = compile_native(ir_to_pytket(g, n, measure=True), "H2-2", optimisation_level=0)
        cnt = native_counts(nat)
        q1l = None if args.no_q1l else local_equivalence_35a(g, nat, n, structured=True)
        _back, _nn, qmap = pytket_to_ir(nat)
        f = {}
        for key, s_ in dev.items():
            if "eps2" not in s_:
                continue
            ero = 0.5 * (s_["eps_ro_0"] + s_["eps_ro_1"])
            f[s_.get("device_name", key)] = clean_shot_fraction(cnt["n_zz"], cnt["n_phasedx"], n,
                                                                s_["eps2"], s_["eps1"], ero)
        rows.append({"circuit_id": cid, "n_2q_ir": md["n_2q"], "native_counts": cnt,
                     "measure_map_identity": qmap == {q: q for q in range(n)},
                     "Q1L_ok": None if q1l is None else q1l["ok"],
                     "rounding_bound_B": None if q1l is None else q1l["iii_rounding"]["state_bound_B"],
                     "clean_shot_fraction_gate_only": f, "s": time.time() - t0})
        print(cid, cnt["n_zz"], cnt["n_phasedx"], cnt["depth_2q"], rows[-1]["Q1L_ok"],
              f"f(H2-2) {f.get('H2-2', float('nan')):.4f}", flush=True)
    devs = sorted({d for r in rows for d in r["clean_shot_fraction_gate_only"]})
    summary = {"n": len(rows), "n_zz": [min(r["native_counts"]["n_zz"] for r in rows),
                                        max(r["native_counts"]["n_zz"] for r in rows)],
               "n_zz_mean": sum(r["native_counts"]["n_zz"] for r in rows) / len(rows),
               "n_phasedx_mean": sum(r["native_counts"]["n_phasedx"] for r in rows) / len(rows),
               "depth_2q": [min(r["native_counts"]["depth_2q"] for r in rows),
                            max(r["native_counts"]["depth_2q"] for r in rows)],
               "zz_equals_ir_2q": all(r["native_counts"]["n_zz"] == r["n_2q_ir"] for r in rows),
               "all_Q1L_ok": None if args.no_q1l else all(r["Q1L_ok"] for r in rows),
               "max_rounding_bound_B": None if args.no_q1l else max(r["rounding_bound_B"] for r in rows),
               "f_gate_only": {d: {"min": min(r["clean_shot_fraction_gate_only"][d] for r in rows),
                                   "mean": sum(r["clean_shot_fraction_gate_only"][d] for r in rows) / len(rows),
                                   "max": max(r["clean_shot_fraction_gate_only"][d] for r in rows)} for d in devs},
               "truncated": truncated}
    print(json.dumps(summary, indent=1))
    lab = f"_{args.label}" if args.label else ""
    write_json(os.path.join(lattice_data(hdr["lattice"]), f"native_{args.family}{lab}.json"), {"rows": rows, "summary": summary, "versions": versions()},
               produced_by="2x4_compression_using_ai_v1/scripts/native_family.py",
               parameters={"family": args.family, "device_compiled_for": "H2-2", "level": 0,
                           "n_1q_model": "PhasedX count (Rz virtual)", "n_meas": "n_qubits",
                           "devices": "data/quantinuum/devices_20261002.json", "ids": args.ids}, t_start=t_start)


if __name__ == "__main__":
    main()
