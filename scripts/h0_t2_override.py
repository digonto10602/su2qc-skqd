#!/usr/bin/env python3
"""
The per-qubit T2 override file of prompts/20 B2 (rule M-T2).

The calibration record carries the Hahn-ECHO T2, which is what a refocused measurement sees.
The frozen 2x2 coarse step refocuses nothing: each of its 12 qubits idles 19-42 us of the
circuit's 44-51 us in a computational or X basis state, so the relevant dephasing time is the
free-induction T2*, which no calibration record reports.  Gate H0_diag measured it on patch 1
with the windowed Ramsey pub `diag_patch1_ramw` (85 x 512 ns = 43.52 us, 2000 shots,
readout-corrected), and the two are far apart: on patch 1 the echo values are 16-265 us and
the free-induction values 13-73 us, an S_T2 budget of 2.57 against 6.58 units.

Rule M-T2 (fixed in prompts/20 before any new data exist), per qubit:

  1. the MEASURED T2* where the readout-corrected inversion resolves it, i.e. where
     2 P(0) - 1 > 0 so that T2* = -T_delay / ln(2 P(0) - 1) exists;
  2. else the 3 sigma UPPER BOUND -T_delay / ln(2 (P(0) + 3 sigma) - 1), where that exists;
  3. else the smallest resolved value on the patch (`patch_minimum`) -- a qubit that is fully
     dephased at 43.52 us with no resolvable bound is not given a longer time than the worst
     qubit that could be resolved.

Every value is written with its provenance, so the JSON says which of the three applied.
The file is consumed by `scripts/gate_H0P.py --t2-override` (which assigns it into
`target.qubit_properties` before `AerSimulator.from_backend`) and by
`scripts/gate_H0_model.py`, which reads it for the T2* end of the bracket.

Nothing here measures anything: it reads `validation/H0_diag.json`, which is the 15.0 s of
QPU the diagnostic spent on 2026-09-22.  No QPU time.

Usage:
  python scripts/h0_t2_override.py --from-diag validation/H0_diag.json --job J1 \
      --out data/hardware/H0_model/t2_override_J1_ramw.json
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIGMA = 3.0          # the same 3 sigma gate_H0_diag.py uses for the Ramsey upper bound
RULE = ("measured T2* where the readout-corrected inversion resolves it; else the 3 sigma "
        "upper bound; else the smallest resolved value on the patch (rule M-T2, prompts/20)")


def override_from_ramw(ramw: dict, sigma: float = SIGMA) -> dict:
    """Apply rule M-T2 to one `ramw` block of `validation/H0_diag.json`.

    `ramw["per_qubit"]` is keyed by PHYSICAL qubit and carries `T2star_measured_s`,
    `T2star_upper_bound_s` (already at `sigma` = 3 in gate_H0_diag.py), `fully_dephased`,
    `P_zero`, `sigma` and the record's `T2_record_s`."""
    per_q = ramw["per_qubit"]
    resolved = []
    for v in per_q.values():
        for key in ("T2star_measured_s", "T2star_upper_bound_s"):
            if v.get(key):
                resolved.append(float(v[key]))
    patch_min = min(resolved) if resolved else None
    out, table = {}, []
    for q, v in sorted(per_q.items(), key=lambda kv: int(kv[0])):
        if v.get("T2star_measured_s"):
            t2, prov = float(v["T2star_measured_s"]), "measured"
        elif v.get("T2star_upper_bound_s"):
            t2, prov = float(v["T2star_upper_bound_s"]), "upper_bound"
        elif patch_min is not None:
            t2, prov = float(patch_min), "patch_minimum"
        else:
            raise SystemExit(f"qubit {q}: no measured value, no bound and no resolved value on "
                             f"the patch -- rule M-T2 has nothing to apply")
        out[str(int(q))] = {"T2_s": t2, "provenance": prov}
        table.append({"qubit": int(q), "logical": v.get("logical"),
                      "P_zero": v.get("P_zero"), "sigma": v.get("sigma"),
                      "fully_dephased": v.get("fully_dephased"),
                      "T2star_measured_s": v.get("T2star_measured_s"),
                      "T2star_upper_bound_s": v.get("T2star_upper_bound_s"),
                      "T2_record_echo_s": v.get("T2_record_s"),
                      "T2_used_s": t2, "provenance": prov,
                      "echo_over_used": (float(v["T2_record_s"]) / t2
                                         if v.get("T2_record_s") and t2 else None)})
    return {"per_qubit": out, "table": table, "patch_minimum_s": patch_min,
            "n_measured": sum(1 for r in table if r["provenance"] == "measured"),
            "n_upper_bound": sum(1 for r in table if r["provenance"] == "upper_bound"),
            "n_patch_minimum": sum(1 for r in table if r["provenance"] == "patch_minimum")}


def table_text(ov: dict) -> str:
    head = (f"{'qubit':>6} {'log':>4} {'P(0)':>7} {'sigma':>7} {'deph':>5} "
            f"{'T2* meas':>9} {'3s bound':>9} {'T2 echo':>9} {'T2 used':>9}  provenance")
    lines = [head, "-" * len(head)]
    for r in ov["table"]:
        def us(x):
            return "     -   " if not x else f"{float(x) * 1e6:9.1f}"
        lines.append(f"{r['qubit']:>6} {str(r['logical']):>4} "
                     f"{(r['P_zero'] or 0):7.4f} {(r['sigma'] or 0):7.4f} "
                     f"{str(bool(r['fully_dephased']))[:5]:>5} "
                     f"{us(r['T2star_measured_s'])} {us(r['T2star_upper_bound_s'])} "
                     f"{us(r['T2_record_echo_s'])} {us(r['T2_used_s'])}  {r['provenance']}")
    lines.append(f"patch minimum {ov['patch_minimum_s'] * 1e6:.1f} us; "
                 f"{ov['n_measured']} measured, {ov['n_upper_bound']} upper bound, "
                 f"{ov['n_patch_minimum']} patch minimum")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-diag", default=os.path.join("validation", "H0_diag.json"),
                    help="the gate H0_diag JSON whose idle tests carry the ramw pub")
    ap.add_argument("--job", default="J1", help="which diagnostic job's ramw to invert "
                                                "(J1 = DD off, twirling off -- the D8' option set)")
    ap.add_argument("--test", default="ramw", choices=("ramw",))
    ap.add_argument("--sigma", type=float, default=SIGMA)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    p = args.from_diag if os.path.isabs(args.from_diag) else os.path.join(ROOT, args.from_diag)
    with open(p) as fh:
        diag = json.load(fh)
    tests = ((diag.get("data") or {}).get("idle_tests") or {}).get(args.job)
    if not tests or args.test not in tests:
        have = sorted(((diag.get("data") or {}).get("idle_tests") or {}))
        raise SystemExit(f"{args.from_diag} has no {args.test} pub for job {args.job} "
                         f"(jobs present: {have})")
    ramw = tests[args.test]
    ov = override_from_ramw(ramw, args.sigma)
    rec = {
        "source": (f"{args.from_diag}: data.idle_tests.{args.job}.{args.test} "
                   f"({ramw['id']}, {ramw['shots']} shots, total delay "
                   f"{ramw['total_delay_s'] * 1e6:.2f} us, readout reference "
                   f"{ramw.get('readout_reference')})"),
        "rule": RULE,
        "sigma": float(args.sigma),
        "job": args.job, "test": args.test,
        "total_delay_s": ramw["total_delay_s"], "shots": ramw["shots"],
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "script": "scripts/h0_t2_override.py",
        "patch_minimum_s": ov["patch_minimum_s"],
        "provenance_counts": {"measured": ov["n_measured"], "upper_bound": ov["n_upper_bound"],
                              "patch_minimum": ov["n_patch_minimum"]},
        "table": ov["table"],
        "per_qubit": ov["per_qubit"],
    }
    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(rec, fh, indent=1)
    print(table_text(ov))
    print(f"wrote {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
