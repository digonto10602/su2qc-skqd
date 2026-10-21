"""A4: native Quantinuum conversion of finalist circuits with the package's own converter (pytket level 0).

Run with the isolated venv (never the coding env):
  ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/native_check.py --ir data/cache/finalists_<label>.pkl --label <label>
Input: a pickle written by scripts/dump_finalists.py (list of {tag, twoB, ref, k, family, gates}).
Per circuit: skqd.quantinuum_native.ir_to_pytket -> compile_native(H2-2, level 0) -> native_counts; the conversion
proof local_equivalence_35a (Q1L (i) + (ii), structured source) and the rounding bound B; the native circuit read
back (pytket_to_ir) and run on the exact sparse simulator against the exact target (max |dpsi| phase-aligned,
leakage); the package's gate-only clean-shot fraction f (skqd.device_req.clean_shot_fraction, n_1q = PhasedX,
28 measurements) for every Quantinuum row of data/quantinuum/devices_20261002.json.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(STUDY, "src"))
sys.path.insert(0, os.path.join(ROOT, "src"))

from c2x4.env import CACHE, write_json                        # noqa: E402
from skqd.device_req import clean_shot_fraction                # noqa: E402
from skqd.quantinuum_native import (compile_native, ir_to_pytket, local_equivalence_35a,   # noqa: E402
                                    native_counts, pytket_to_ir, versions)
from c2x4.evaluate import certified_state_check               # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--max-wall", type=float, default=1700.0)
    ap.add_argument("--levels", default="0", help="pytket optimisation levels (Q1L only at level 0)")
    ap.add_argument("--simulate", action="store_true",
                    help="also run the native circuit on the certified pruned simulator (notes/006)")
    args = ap.parse_args()
    t_start = time.time()
    with open(args.ir if os.path.isabs(args.ir) else os.path.join(STUDY, args.ir), "rb") as fh:
        items = pickle.load(fh)
    ints = np.load(os.path.join(CACHE, "codeword_ints.npy"))
    dev = json.load(open(os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")))["specs"]
    rows = []
    for it in items:
        if time.time() - t_start > args.max_wall:
            print("wall limit: remaining circuits not converted", flush=True)
            break
        g = it["gates"]
        tgt = np.load(os.path.join(CACHE, f"target_{it['tag']}.npy"))
        for lev in (int(v) for v in args.levels.split(",")):
            t0 = time.time()
            circ = ir_to_pytket(g, 28, measure=True)
            nat = compile_native(circ, "H2-2", optimisation_level=lev)
            t_comp = time.time() - t0
            cnt = native_counts(nat)
            t1 = time.time()
            q1l = local_equivalence_35a(g, nat, 28, structured=True) if lev == 0 else None
            t_q1l = time.time() - t1
            back, nn, qmap = pytket_to_ir(nat)
            dev_pa, leak_direct = None, None
            chk = None
            if args.simulate:
                chk = certified_state_check([x for x in back if x[0] not in ("measure",)], 28, ints, tgt)
                dev_pa, leak_direct = chk["certified_max_dev"], chk["certified_leakage"]
            f = {}
            for key, s_ in dev.items():
                if "eps2" not in s_:
                    continue
                ero = 0.5 * (s_["eps_ro_0"] + s_["eps_ro_1"])
                f[s_.get("device_name", key)] = clean_shot_fraction(cnt["n_zz"], cnt["n_phasedx"], 28,
                                                                    s_["eps2"], s_["eps1"], ero)
            row = {"tag": it["tag"], "family": it["family"], "twoB": it["twoB"], "reference": it["ref"],
                   "k": it["k"], "level": lev, "native_counts": cnt, "compile_s": t_comp,
                   "measure_map_identity": qmap == {q: q for q in range(28)},
                   "Q1L_ok": None if q1l is None else q1l["ok"],
                   "Q1L_skeleton_ok": None if q1l is None else q1l["i_skeleton"]["ok"],
                   "Q1L_segments_max_residual": None if q1l is None else
                   q1l["ii_segments_vs_readback"]["segments_max_residual"],
                   "rounding_bound_B": None if q1l is None else q1l["iii_rounding"]["state_bound_B"],
                   "q1l_s": t_q1l,
                   "native_state_check": chk,
                   "state_bar_pass": None if chk is None else chk["pass"],
                   "clean_shot_fraction_gate_only": f}
            rows.append(row)
            print(f"{it['tag']} [{it['family']}] level {lev}: ZZ {cnt['n_zz']} depth2q {cnt['depth_2q']} PhasedX "
                  f"{cnt['n_phasedx']} | Q1L {row['Q1L_ok']} B {row['rounding_bound_B']} | native certified dev {dev_pa} leak {leak_direct} "
                  f"| f(H2-2) {f.get('H2-2', float('nan')):.3f} (compile {t_comp:.1f} s, Q1L {t_q1l:.1f} s)", flush=True)
    write_json(f"data/native_{args.label}.json", {"rows": rows, "versions": versions()},
               produced_by="2x4_compression_using_ai_v1/scripts/native_check.py",
               parameters={"ir": args.ir, "device_compiled_for": "H2-2", "levels": args.levels,
                           "n_meas": 28, "n_1q_model": "PhasedX count (Rz virtual), as data/p1_device_threshold.json",
                           "devices": "data/quantinuum/devices_20261002.json"}, t_start=t_start)


if __name__ == "__main__":
    main()
