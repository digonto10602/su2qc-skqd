#!/usr/bin/env python3
"""
Gate H0 (prompts/07 step 5) — analysis of a 2x2 calibration session from RAW COUNTS.

Reads a directory of counts files written by `scripts/h0_submit.py` (one JSON per
circuit, each carrying the manifest of the frozen circuit it came from), decodes every
shot with `skqd.codec.Codec.decode_counts`, and evaluates the prompts/07 criteria:

  1. decoder validity: every accepted string is a valid codeword of the target sector
     (checked by re-encoding the decoded label), and the acceptance of random-looking
     strings is < 1 % (exhaustive over all 2^n strings);
  2. the measured f is within 30 % of the preregistered prediction for the r = 1 circuits.
     f is recovered from an accepted-shot yield by inverting the manual's full Step-4.4
     model y = 0.82 f + (1 - f) a, i.e. f = (y - a) / (0.82 - a)
     (`skqd.skqd.clean_fraction_from_yield`), with a = the decoder's random-string
     acceptance of that sector, measured exhaustively here.  The predicted yield is the
     simulated yield of `validation/H0P.json` — the planner's decision recorded in
     `reports/H0_prereg_draft.md` — or, with `--predict model`, the model itself;
  3. the Ritz energies of the saturated 2x2 sectors reproduce the exact E0 to 1e-6;
  4. every diagonal element of the per-qubit readout confusion matrix is >= 0.9, and the
     measured per-qubit readout error agrees with the frozen calibration snapshot within
     a factor 3 (the item that is expected to move on a real device: calibration drift).

The script never touches a QPU and never modifies the counts.

Usage: python scripts/gate_H0.py --counts data/hardware/H0_dryrun/counts --out H0_dryrun
       python scripts/gate_H0.py --counts data/hardware/H0_<date>/counts --out H0
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.codec import Codec, Reject  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402

from skqd.skqd import clean_fraction_from_yield  # noqa: E402

from gate_H0P import (DIAG_MIN, E0_TOL, RANDOM_ACCEPT_MAX, YIELD_FACTOR,  # noqa: E402
                      YIELD_MODEL_NAME, analyse_records, shot_plan)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
F_TOLERANCE = 0.30          # prompts/07 step 4: measured f within 30 % of the prediction
RO_FACTOR = 3.0             # measured readout error within this factor of the frozen snapshot


def read_counts_dir(path):
    """[(manifest, {bit tuple: count})] from the counts JSONs; the keys are converted
    from the qiskit convention (rightmost character = classical bit 0) to bit tuples."""
    from skqd.reference_sim import qiskit_key_to_bits
    out = []
    for p in sorted(glob.glob(os.path.join(path, "*.json"))):
        with open(p) as fh:
            rec = json.load(fh)
        counts = {qiskit_key_to_bits(k): int(v) for k, v in rec["counts"].items()}
        man = {k: v for k, v in rec.items() if k != "counts"}
        out.append((man, counts))
    return out


def codeword_roundtrip(records, codec):
    """Every accepted string must re-encode to itself: the decoded label is a codeword
    of the target sector and the bit order is the one the codec defines."""
    checked, bad = 0, []
    seen = set()
    for man, counts in records:
        for bits in counts:
            if (man["twoB"], bits) in seen:
                continue
            seen.add((man["twoB"], bits))
            try:
                idx, label = codec.decode(bits, man["twoB"])
            except Reject:
                continue
            checked += 1
            if tuple(codec.encode(label)) != tuple(bits):
                bad.append({"id": man["id"], "bits": list(bits)})
    return {"distinct_accepted_strings": checked, "mismatches": len(bad), "examples": bad[:5]}


def prediction(args, analysis, records):
    """Preregistered predicted yield per 'sector r=..' key, and where it came from."""
    if args.predict == "model":
        return ({k: v["model_yield_full"] for k, v in analysis["by_sector_repetition"].items()},
                f"the manual's model y = {YIELD_MODEL_NAME} with the f of the frozen calibration snapshot "
                f"and the exhaustive garbage acceptance a of each sector")
    p = os.path.join(ROOT, args.predict_from)
    if os.path.exists(p):
        with open(p) as fh:
            d = json.load(fh)
        src = d["data"]["analysis"]["by_sector_repetition"]
        return ({k: v["yield"] for k, v in src.items()},
                f"the simulated yield of {args.predict_from} (gate {d['gate']}, {d['environment']['timestamp']}), "
                f"the preregistered prediction of reports/H0_prereg_draft.md")
    return ({k: v["model_yield_full"] for k, v in analysis["by_sector_repetition"].items()},
            f"the manual's model y = {YIELD_MODEL_NAME} ({args.predict_from} not found)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--counts", required=True, help="directory of counts JSONs")
    ap.add_argument("--out", default="H0", help="validation/<out>.json and reports/<out>_hardware_2x2.md")
    ap.add_argument("--predict", default="simulated", choices=("simulated", "model"))
    ap.add_argument("--predict-from", default=os.path.join("validation", "H0P.json"))
    ap.add_argument("--p", type=float, default=1e-3)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--conf", type=float, default=0.95)
    args = ap.parse_args()
    t0 = time.time()

    path = os.path.join(ROOT, args.counts) if not os.path.isabs(args.counts) else args.counts
    recs = read_counts_dir(path)
    if not recs:
        raise SystemExit(f"no counts files in {path}")
    coarse = [(m, c) for m, c in recs if m["kind"] == "coarse_step"]
    cals = [(m, c) for m, c in recs if m["kind"] == "readout_calibration"]
    common = coarse[0][0]
    M = Model(int(common["lattice"].split("x")[1]))
    codec = Codec(M.basis)
    g2 = common["g2"]
    backend = common.get("backend", "unknown")
    dry = bool(common.get("dry_run", False))

    R = GateResult(args.out, f"2x2 calibration session on {backend}: decoder validity, bit order, "
                             f"yield versus CZ count, readout confusion, Ritz consistency")
    A = analyse_records(coarse, cals, M, g2)
    rt = codeword_roundtrip(coarse, codec)
    pred, pred_src = prediction(args, A, coarse)
    plan = shot_plan(A, args.p, args.k, args.conf)

    # measured f versus the preregistered prediction, r = 1.  The criterion is on f, and f is
    # recovered from a yield by inverting the FULL model y = 0.82 f + (1 - f) a (manual Step 4.4):
    # f = (y - a) / (0.82 - a) = skqd.skqd.clean_fraction_from_yield(y, a).
    fcmp = {}
    for key, v in A["by_sector_repetition"].items():
        yp = pred.get(key)
        if not yp:
            continue
        a = v["garbage_acceptance"]
        fm, fp = clean_fraction_from_yield(v["yield"], a), clean_fraction_from_yield(yp, a)
        fcmp[key] = {"sector": v["sector"], "repetitions": v["repetitions"], "cz_mean": v["cz_mean"],
                     "measured_yield": v["yield"], "predicted_yield": yp,
                     "garbage_acceptance": a, "yield_model": YIELD_MODEL_NAME,
                     "measured_f": fm, "predicted_f": fp,
                     "measured_f_0.82f_model": v["yield"] / YIELD_FACTOR,
                     "predicted_f_0.82f_model": yp / YIELD_FACTOR,
                     "relative_deviation": float(abs(fm - fp) / fp) if fp else None,
                     "relative_deviation_of_the_yields": float(abs(v["yield"] - yp) / yp),
                     "shots": v["shots"], "accepted": v["accepted"]}

    # readout: measured error per qubit against the frozen snapshot value
    ro = {}
    for pk, v in A["confusion"].items():
        pi = int(pk.replace("patch", ""))
        man = next(m for m, _ in cals if m["patch_index"] == pi)
        snap = man.get("readout_error_snapshot")
        meas = [1.0 - 0.5 * (v["P_measure_0_given_0"][q] + v["P_measure_1_given_1"][q])
                for q in range(codec.n_qubits)]
        entry = {"physical_qubits": v["physical_qubits_logical_order"], "measured_error": meas,
                 "snapshot_error": snap}
        if snap:
            ratio = [float(m / s) if s > 0 else None for m, s in zip(meas, snap)]
            entry["ratio_measured_over_snapshot"] = ratio
            good = [r for r in ratio if r is not None]
            entry["worst_ratio"] = float(max(max(good), 1.0 / min(good))) if good else None
        ro[pk] = entry
    worst_ro = max((v["worst_ratio"] for v in ro.values() if v.get("worst_ratio")), default=None)

    data = {
        "counts_directory": args.counts, "n_counts_files": len(recs),
        "coarse_step_circuits": len(coarse), "calibration_circuits": len(cals),
        "backend": backend, "dry_run": dry,
        "sampler_options": common.get("sampler_options"),
        "prediction_source": pred_src, "predicted_yield": pred,
        "yield_model": YIELD_MODEL_NAME,
        "garbage_acceptance": {sec: A["random_acceptance"][sec]["fraction"]
                               for sec in sorted(A["random_acceptance"])},
        "yield_model_inputs": {
            "formula": f"y = {YIELD_MODEL_NAME}  (manual Step 4.4, both terms)",
            "readout_factor": YIELD_FACTOR,
            "inverse": "f = (y - a) / (0.82 - a) = skqd.skqd.clean_fraction_from_yield(y, a)",
            "garbage_acceptance_source": ("exhaustive: all 2^n bit strings through "
                                          "skqd.codec.Codec.decode for the target sector"),
            "note": ("the 30 % criterion is on f; the shot plan keeps using the clean yield 0.82 f, "
                     "since garbage acceptances add no support"),
        },
        "f_comparison": fcmp, "codeword_roundtrip": rt,
        "readout_vs_snapshot": ro, "shot_plan": plan, "analysis": A,
        "criteria_inputs": {"f_tolerance": F_TOLERANCE, "random_acceptance_max": RANDOM_ACCEPT_MAX,
                            "E0_tolerance": E0_TOL, "confusion_diagonal_min": DIAG_MIN,
                            "readout_snapshot_factor": RO_FACTOR, "yield_factor": YIELD_FACTOR},
    }

    R.add("decoder validity: accepted strings that re-encode to themselves",
          f"{rt['distinct_accepted_strings'] - rt['mismatches']} of {rt['distinct_accepted_strings']}",
          "all", rt["mismatches"] == 0)
    for sec in sorted(A["random_acceptance"]):
        ra = A["random_acceptance"][sec]
        R.add(f"{sec}: acceptance of random bit strings (exhaustive over {ra['strings']} strings)",
              f"{100 * ra['fraction']:.3f}%", f"< {100 * RANDOM_ACCEPT_MAX:.0f}%",
              ra["fraction"] < RANDOM_ACCEPT_MAX)
    for key in sorted(k for k, v in fcmp.items() if v["repetitions"] == 1):
        v = fcmp[key]
        R.add(f"{key} ({v['cz_mean']:.0f} CZ): measured f = {v['measured_f']:.4f} vs the predicted "
              f"f = {v['predicted_f']:.4f} (both from y = {YIELD_MODEL_NAME} inverted at "
              f"a = {v['garbage_acceptance']:.5f})", round(v["relative_deviation"], 4),
              f"relative deviation <= {F_TOLERANCE:.2f}", v["relative_deviation"] <= F_TOLERANCE)
    for sec in sorted(A["by_sector"]):
        s = A["by_sector"][sec]
        R.add(f"{sec}: decoded support reproduces the exact E0 = {s['exact_E0']:.4f}",
              s["abs_error"], f"|E_R - E_0| < {E0_TOL:g}", s["abs_error"] < E0_TOL)
    cs = A["confusion_summary"]
    R.add(f"readout confusion on {cs['n_patches']} patch(es): smallest diagonal element",
          round(cs["min_diagonal"], 4), f">= {DIAG_MIN}", cs["min_diagonal"] >= DIAG_MIN)
    if worst_ro is not None:
        R.add("readout error per qubit against the frozen calibration snapshot (worst ratio; on a real "
              "device this is the calibration-drift item)", round(worst_ro, 3),
              f"within a factor {RO_FACTOR:.0f}", worst_ro <= RO_FACTOR)

    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report(f"{args.out}_hardware_2x2.md", report_text(args, R, data))
    print(R.criteria_table())
    return 0 if R.passed else 1


def report_text(args, R, D):
    A = D["analysis"]
    yrows = []
    for key in sorted(A["by_sector_repetition"]):
        v = A["by_sector_repetition"][key]
        f = D["f_comparison"].get(key, {})
        yrows.append([v["sector"], v["repetitions"], v["circuits"], f"{v['cz_mean']:.0f}", v["shots"],
                      v["accepted"], f"{v['yield']:.4f}", f"{v['garbage_acceptance']:.5f}",
                      f"{v['model_yield_0.82f']:.4f}", f"{v['model_yield_full']:.4f}",
                      f"{f.get('predicted_yield', float('nan')):.4f}",
                      f"{f.get('measured_f', float('nan')):.4f}",
                      f"{f.get('predicted_f', float('nan')):.4f}",
                      f"{f.get('measured_f_0.82f_model', float('nan')):.4f}",
                      f"{f.get('relative_deviation', float('nan')) if f.get('relative_deviation') is not None else float('nan'):.3f}",
                      str(v["rejections"])])
    srows = [[sec, v["sector_dimension"], v["support_size_decoded"], v["support_size_with_references"],
              f"{v['ER']:.10f}", f"{v['exact_E0']:.10f}", f"{v['abs_error']:.2e}",
              f"{v['recall_99.9pct_support']:.3f}"] for sec, v in sorted(A["by_sector"].items())]
    crows = []
    for pk, v in sorted(A["confusion"].items()):
        rr = D["readout_vs_snapshot"].get(pk, {})
        for i, q in enumerate(v["physical_qubits_logical_order"]):
            crows.append([pk, i, q, f"{v['P_measure_0_given_0'][i]:.4f}", f"{v['P_measure_1_given_1'][i]:.4f}",
                          f"{rr['measured_error'][i]:.4f}" if rr.get("measured_error") else "-",
                          f"{rr['snapshot_error'][i]:.4f}" if rr.get("snapshot_error") else "-",
                          f"{rr['ratio_measured_over_snapshot'][i]:.2f}"
                          if rr.get("ratio_measured_over_snapshot") else "-"])
    rarows = [[sec, f"{v['accepted']} / {v['strings']}", f"{100 * v['fraction']:.3f}%"]
              for sec, v in sorted(A["random_acceptance"].items())]
    return f"""# Gate {R.gate} — 2x2 calibration session on {D['backend']}

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/gate_H0.py --counts {args.counts} --out {args.out}`,
{D['n_counts_files']} counts files ({D['coarse_step_circuits']} coarse-step + {D['calibration_circuits']} readout-calibration circuits),
dry run: **{D['dry_run']}**.  {env_block()}  Runtime {R.runtime_s:.0f} s.

Sampler options of the session: `{json.dumps(D['sampler_options'])}`.

## 1. Decoder validity

{md_table(["sector", "accepted random strings", "fraction"], rarows)}

{D['codeword_roundtrip']['distinct_accepted_strings']} distinct accepted bit strings were decoded and re-encoded;
{D['codeword_roundtrip']['mismatches']} did not reproduce themselves.  A mismatch would mean the bit order of the
counts keys is not the codec's.

## 2. Yield versus CZ count

Prediction used for the 30 % criterion: {D['prediction_source']}.

Yield model (manual Step 4.4, both terms): y = {D['yield_model']}, with a = the decoder's random-string
acceptance of the target sector ({', '.join(f"{sec} {v:.5f}" for sec, v in sorted(D['garbage_acceptance'].items()))}, exhaustive).  The measured and predicted
clean-shot fractions are the inverse, {D['yield_model_inputs']['inverse']}; the column "measured f (0.82 f
model)" is the first term alone, kept for comparison.  **The 30 % criterion is the relative deviation of the
two f values** (r = 1 circuits only: at r = 2, 3 the inversion is ill-conditioned because f approaches a).

{md_table(["sector", "r", "circuits", "CZ", "shots", "accepted", "measured yield", "a (garbage)",
            "model 0.82 f (old)", "model 0.82 f + (1−f) a", "predicted yield", "measured f",
            "predicted f", "measured f (0.82 f model)", "relative deviation of f", "rejections"], yrows)}

## 3. Ritz consistency

{md_table(["sector", "sector dimension", "decoded states", "with references", "E_R", "exact E_0",
            "\\|E_R − E_0\\|", "recall of the 99.9 % support"], srows)}

## 4. Readout confusion

{md_table(["patch", "logical qubit", "physical qubit", "P(0\\|0)", "P(1\\|1)", "measured error",
            "snapshot error", "ratio"], crows)}

## Criteria

{R.criteria_table()}

Every number above is computed by `scripts/gate_H0.py` from the raw counts in `{args.counts}` and stored in
`validation/{R.gate}.json`.  The counts files are never modified.
"""


if __name__ == "__main__":
    sys.exit(main())
