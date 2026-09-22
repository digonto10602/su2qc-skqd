#!/usr/bin/env python3
"""
The idle-aware yield model (prompts/19 step A) — the term both H0 predictions omit.

`gate_S2D.analyse_on_backend` multiplies the calibration's cz and measure errors; Aer's
`NoiseModel.from_backend` attaches depolarizing + thermal relaxation to each *gate* for
that gate's duration on that gate's qubits.  Neither sees the time a qubit spends WAITING
for other qubits' gates.  On a heavy-hex device the routed 2x2 circuit is nearly serial
(depth 1328 for 663 CZ, 43.71 us before readout) and each of its 12 qubits idles 19-42 us
of it (`reports/H0_canary_planner_analysis_20260922.md`, planner computation P1).

This script schedules every circuit of a prep directory ASAP on a calibration RECORD
(`scripts/h0_backends.py`), collects the idle windows of every active qubit, and adds the
idle relaxation budget in the Pauli-twirling approximation of thermal relaxation -- the
channel Aer's `RelaxationNoisePass` would put on an explicit `delay`:

    per window w on qubit q:   p = (1 - e^{-w/T1_q})/4 + (1 - e^{-w/T2_q})/2
    S_T1 = sum_q sum_w (1 - e^{-w/T1_q})/4       S_T2 = sum_q sum_w (1 - e^{-w/T2_q})/2

The runtime's `PadDynamicalDecoupling` pads a window only if it is longer than
`sequence_min_length_ratios` (default 2.0) times the sequence length, so with XY4 =
4 x sx_duration a window is DD-eligible when w / (4 sx_duration) > 2.0; it inserts one
sequence per window, costing S_DD = sum_eligible 4 x sx_error.  The refocusing efficiency
rho (the fraction of the eligible-window T2 budget that survives DD) is not computable
from the calibration, so the predictions are given as a bracket over rho:

    f(rho)  = f_gates x exp(-S_T1 - rho S_T2_eligible - S_T2_ineligible - S_DD)
    f_dd_off = f_gates x exp(-S_T1 - S_T2)
    yield    = 0.82 f + (1 - f) a        (manual Step 4.4, `skqd.skqd.yield_model`)

with `f_gates` the SAME product of cz and measure errors the prediction used, evaluated on
the record by `h0_support_plan.f_from_calibration` (asserted equal to
`gate_S2D.analyse_on_backend` to 1e-12 whenever a backend object is available) and `a` the
sector's exhaustive garbage acceptance.

Nothing here is a criterion and nothing here is fitted: the inputs are the calibration
record's own T1, T2, durations and errors.  The output JSON is also the PREREGISTRATION
file of prompts/19 (`h0_submit.py --prereg`): it carries the calibration fingerprint the
session may be submitted on, and the predictions of the diagnostic jobs.

Usage:
  python scripts/h0_idle_model.py --calibration data/hardware/H0_ibm_fez_canary/calibration_at_submission_20260922T1400Z.json
  python scripts/h0_idle_model.py --backend ibm_fez --prep data/hardware/H0_diag_prep --md reports/H0_diag_prereg.md
Runtime: seconds per circuit (about 1 min over the 84 frozen circuits); no QPU time.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd import idle  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.skqd import READOUT_FACTOR, yield_model  # noqa: E402

from gate_H0P import load_circuit, load_index, load_manifests, random_acceptance  # noqa: E402
from h0_backends import (calibration_fingerprint, fresh_calibration,  # noqa: E402
                         frozen_qubits_and_edges, resolve_backend)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DD_MIN_LENGTH_RATIO = idle.DD_MIN_LENGTH_RATIO   # PadDynamicalDecoupling default (skqd.idle)
XY4_PULSES = idle.XY4_PULSES                    # X, Y, X, Y -- 4 x the single-qubit pulse
RHOS = (0.0, 0.25, 0.5, 1.0)  # the DD refocusing bracket of the planner analysis, section 2
DURATION_TOL = 1e-12          # h0_qpu_time.circuit_duration_s must agree to this


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


# --------------------------------------------------------------------------- durations
# The schedule and the idle budget now live in `skqd.idle` (the library form of this
# script, prompts/20): the functions below are the script's names for them, so that
# every number this file has ever written is produced by the same code as before.
def record_duration(rec, name, qubits, dt=None):
    """`skqd.idle.instruction_duration_s`, with this script's SystemExit on a gap."""
    try:
        return idle.instruction_duration_s(rec, name, qubits)
    except KeyError as exc:
        raise SystemExit(str(exc).strip('"'))


def schedule(qc, rec):
    """ASAP schedule of `qc` on the record's durations (prompts/19 A2) -- `skqd.idle`."""
    return idle.schedule_asap(qc, rec)


def budgets(sch, rec, t2_s=None):
    """The idle relaxation budget of a scheduled circuit (prompts/19 A3) -- `skqd.idle`."""
    return idle.idle_budget(sch, rec, t2_s)


def f_on_record(qc, rec):
    """(f_gates, f_gates_only, measure survival) of `gate_S2D.analyse_on_backend` on a record."""
    import h0_support_plan as sp
    cz = {}
    for e in rec["edges"].values():
        key = tuple(e["target_key"])
        for k in (key, key[::-1]):
            cz[k] = e["cz_error"]
    meas = {int(q): v["measure_error"] for q, v in rec["qubits"].items()}
    f, n_cz, n_meas = sp.f_from_calibration(qc, cz, meas)
    ro = 1.0
    for inst in qc.data:
        if inst.operation.name == "measure":
            ro *= (1.0 - float(meas[qc.find_bit(inst.qubits[0]).index]))
    return float(f), float(f / ro) if ro else None, float(ro), int(n_cz), int(n_meas)


def predictions(f_gates, tot, a):
    """The bracket of prompts/19 A4: DD off, and DD on at each refocusing efficiency rho."""
    f_off = idle.f_idle_aware(f_gates, tot)
    out = {"f_gates": f_gates, "garbage_acceptance": a,
           "dd_off": {"f": f_off, "yield": yield_model(f_off, a) if a is not None else None},
           "dd_on": {}}
    for rho in RHOS:
        f = idle.f_idle_aware(f_gates, tot, rho)
        out["dd_on"][str(rho)] = {"rho": rho, "f": f,
                                  "yield": yield_model(f, a) if a is not None else None}
    return out


def idle_test_prediction(man, rec):
    """Per-qubit `t1w` / `ramw` predictions of prompts/19 D6 on this record."""
    Td = float(man["total_delay_s"])
    out = {}
    for q in man["physical_qubits"]:
        qq = rec["qubits"][str(q)]
        T1, T2 = float(qq["T1_s"]), float(qq["T2_s"])
        out[str(q)] = {"T1_s": T1, "T2_s": T2,
                       "P_survive_t1w": math.exp(-Td / T1),
                       "P_zero_ramw_bound": (1.0 + math.exp(-Td / T2)) / 2.0}
    return {"total_delay_s": Td, "expected_bits": man.get("expected_bits"), "per_qubit": out}


# --------------------------------------------------------------------------- driver
def analyse(prep, rec, only=None, backend=None, shots=2000, hb=None):
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    allm = mans + cals
    if only:
        keep = set(only)
        allm = [m for m in allm if m["id"] in keep]
        missing = keep - {m["id"] for m in allm}
        if missing:
            raise SystemExit(f"--only: no such circuit(s) in {prep}: {sorted(missing)}")
    model = Model(int(index["common"]["lattice"].split("x")[1]))
    codec = Codec(model.basis)
    acc = {}
    for m in allm:
        if m.get("twoB") is not None and m["sector"] not in acc:
            acc[m["sector"]] = random_acceptance(codec, m["twoB"])["fraction"]

    circuits, patch_S_T2 = {}, {}
    for m in allm:
        qc = load_circuit(prep, m)
        sch = schedule(qc, rec)
        per_q, tot = budgets(sch, rec)
        f_gates, f_gates_only, ro, n_cz, n_meas = f_on_record(qc, rec)
        if backend is not None and n_cz > 0:
            # gate_S2D.analyse_on_backend needs at least one cz (it reports the worst edge);
            # the idle-test and readout-calibration circuits have none, and for them the
            # record-backed f is the product of the measure errors alone.
            from gate_S2D import analyse_on_backend
            f_target = float(analyse_on_backend(qc, backend)["f"])
            if abs(f_target - f_gates) > 1e-12:
                raise SystemExit(f"{m['id']}: the record-backed f {f_gates!r} differs from "
                                 f"analyse_on_backend's {f_target!r} by "
                                 f"{abs(f_target - f_gates):.3e} > 1e-12")
        from h0_qpu_time import circuit_duration_s
        if backend is not None:
            d = circuit_duration_s(qc, backend.target.durations(), backend.target)
            if abs(d - sch["T_total_s"]) > DURATION_TOL:
                raise SystemExit(f"{m['id']}: the scheduled duration {sch['T_total_s']!r} differs "
                                 f"from h0_qpu_time.circuit_duration_s {d!r}")
        a = acc.get(m.get("sector"))
        e = {
            "id": m["id"], "kind": m["kind"], "sector": m.get("sector"),
            "repetitions": m.get("repetitions"), "k": m.get("k"),
            "patch_index": m.get("patch_index"), "physical_qubits": m["physical_qubits"],
            "n_cz": n_cz, "n_measure": n_meas, "depth": m.get("depth"),
            "T_s": sch["T_s"], "T_total_s": sch["T_total_s"],
            "measure_duration_s": sch["measure_duration_s"],
            "f_gates": f_gates, "f_gates_only": f_gates_only, "measure_survival": ro,
            "budget": tot, "per_qubit": per_q,
            "prediction": predictions(f_gates, tot, a),
        }
        if m["kind"] == "idle_test":
            e["idle_test_prediction"] = idle_test_prediction(m, rec)
        circuits[m["id"]] = e
        if m["kind"] == "coarse_step":      # the cal circuits have no idle time at all
            pk = f"patch{m.get('patch_index')} r={m.get('repetitions')}"
            patch_S_T2.setdefault(pk, []).append(tot["S_T2"])

    out = {
        "script": "scripts/h0_idle_model.py",
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "commit": git_commit(),
        "prep": os.path.relpath(prep, ROOT),
        "prep_created": index["created"],
        "n_circuits": len(circuits),
        "calibration": {
            "backend": rec.get("backend"), "last_update_date": rec.get("last_update_date"),
            "stamp": rec.get("stamp"),
            "fingerprint": rec.get("fingerprint") or calibration_fingerprint(rec),
        },
        "model": {
            "schedule": "ASAP on the record's durations; rz and barrier cost 0; delay = duration x dt",
            "idle_budget": ("per idle window w on qubit q: (1 - e^{-w/T1})/4 + (1 - e^{-w/T2})/2 "
                            "(Pauli-twirling approximation of thermal relaxation)"),
            "dd": (f"PadDynamicalDecoupling pads a window when w / ({XY4_PULSES} x sx_duration) > "
                   f"{DD_MIN_LENGTH_RATIO} (sequence_min_length_ratios default); one XY4 sequence "
                   f"per window at a cost of {XY4_PULSES} x sx_error"),
            "f": ("f_gates = prod(1 - cz_error) x prod(1 - measure_error) = "
                  "gate_S2D.analyse_on_backend on this record; f_gates_only divides the measure "
                  "survival out"),
            "yield": f"y = {READOUT_FACTOR} f + (1 - f) a (manual Step 4.4, skqd.skqd.yield_model)",
            "rho": "the fraction of the DD-eligible T2 budget that survives DD; not computable here",
            "rhos": list(RHOS),
        },
        "garbage_acceptance": acc,
        "per_patch_S_T2": {k: {"mean": float(np.mean(v)), "min": float(np.min(v)),
                               "max": float(np.max(v)), "n_circuits": len(v)}
                           for k, v in sorted(patch_S_T2.items())},
        "circuits": circuits,
    }
    ref_key = None
    cman = next((m for m in allm if m["id"] == "B0_ref06_k1_rep1"), None)
    if cman is not None:
        bits = codec.encode(model.basis.labels[int(cman["reference"])])
        ref_key = "".join(str(int(b)) for b in reversed(bits))
    out["session_prediction"] = session_prediction(out, shots, hb, ref_key)
    return out


def session_prediction(out, shots, hb, reference_key=None):
    """The preregistered J1 decision of prompts/19 (H_A against H_B) at `shots` shots."""
    cid = "B0_ref06_k1_rep1"
    if cid not in out["circuits"]:
        return None
    c = out["circuits"][cid]
    a = c["prediction"]["garbage_acceptance"]
    p = c["prediction"]
    hb_yield = None
    if hb:
        path = hb if os.path.isabs(hb) else os.path.join(ROOT, hb)
        if os.path.isfile(path):
            with open(path) as fh:
                d = json.load(fh)
            hb_yield = ((d.get("data") or {}).get("analysis") or {}) \
                .get("by_sector_repetition", {}).get("B=0 r=1", {}).get("yield")

    def n(y):
        return None if y is None else {"yield": y, "expected": shots * y,
                                       "sigma": math.sqrt(shots * y * (1 - y))}

    return {
        "circuit": cid, "shots": shots,
        "reference_string": reference_key,
        "garbage_acceptance": a, "garbage_floor_expected": shots * a,
        "H_A": {"hypothesis": "idle-time relaxation (DD off, J1): f = f_gates e^{-S_T1 - S_T2}",
                **(n(p["dd_off"]["yield"]) or {})},
        "H_B": {"hypothesis": ("the SamplerV2 options (DD XY4, twirling active-accum) caused the "
                               "canary shortfall: with them off the gate-only prediction holds"),
                "source": hb, **(n(hb_yield) or {})},
        "J2_dd_on_bracket": {r: {"rho": v["rho"], "yield": v["yield"],
                                 "expected": None if v["yield"] is None else shots * v["yield"]}
                             for r, v in p["dd_on"].items()},
        "decision_rule": ("N1 = accepted shots of the canary pub of J1: N1 <= 100 rejects H_B, "
                          "N1 >= 250 confirms H_B, 100 < N1 < 250 is inconclusive (prompts/19 D5 C3)"),
        "N1_reject_H_B_at_or_below": 100,
        "N1_confirm_H_B_at_or_above": 250,
    }


# --------------------------------------------------------------------------- report
def report_text(res, args):
    from skqd.report import md_table
    cal = res["calibration"]
    rows = []
    for name, c in sorted(res["circuits"].items()):
        b = c["budget"]
        rows.append([name, c["kind"], f"{c['T_s'] * 1e6:.2f}", f"{b['idle_s'] * 1e6:.1f}",
                     b["n_windows"], b["dd_eligible"], f"{b['S_T1']:.3f}", f"{b['S_T2']:.3f}",
                     f"{b['S_DD']:.3f}", f"{c['f_gates']:.4f}",
                     f"{c['prediction']['dd_off']['f']:.2e}"])
    qrows = []
    cid = "B0_ref06_k1_rep1"
    if cid in res["circuits"]:
        for q, v in sorted(res["circuits"][cid]["per_qubit"].items(), key=lambda kv: int(kv[0])):
            qrows.append([q, f"{v['T1_s'] * 1e6:.1f}", f"{v['T2_s'] * 1e6:.1f}",
                          f"{v['busy_s'] * 1e6:.2f}", f"{v['idle_s'] * 1e6:.2f}", v["n_windows"],
                          v["n_dd_eligible"], f"{v['longest_window_s'] * 1e6:.2f}",
                          f"{v['S_T1']:.3f}", f"{v['S_T2']:.3f}"])
    sp = res.get("session_prediction") or {}
    prows = []
    if sp:
        for name in ("H_A", "H_B"):
            h = sp.get(name) or {}
            if h.get("expected") is not None:
                prows.append([name, h["hypothesis"], f"{h['yield']:.4f}",
                              f"{h['expected']:.0f} +- {h['sigma']:.0f}"])
        for r, v in sorted((sp.get("J2_dd_on_bracket") or {}).items(), key=lambda kv: float(kv[0])):
            if v["expected"] is not None:
                prows.append([f"J2 rho={v['rho']}", "DD on, idle model", f"{v['yield']:.4f}",
                              f"{v['expected']:.0f}"])
    irows = []
    for name, c in sorted(res["circuits"].items()):
        it = c.get("idle_test_prediction")
        if not it:
            continue
        for q, v in sorted(it["per_qubit"].items(), key=lambda kv: int(kv[0])):
            irows.append([name, q, f"{v['T1_s'] * 1e6:.1f}", f"{v['T2_s'] * 1e6:.1f}",
                          f"{v['P_survive_t1w']:.3f}", f"{v['P_zero_ramw_bound']:.3f}"])
    return f"""# H0 idle-aware model — {res['prep']} on {cal['backend']} ({cal['last_update_date']})

Generated by `scripts/h0_idle_model.py` (prompts/19 step A) at commit `{res['commit']}`,
{res['created']}.  Calibration fingerprint **`{cal['fingerprint']}`** (stamp `{cal['stamp']}`).
No QPU time was used.  {res['n_circuits']} circuit(s).

{res['model']['idle_budget']}; {res['model']['dd']}.
Yield: {res['model']['yield']}.

## 1. Per circuit

{md_table(["circuit", "kind", "T (us)", "idle summed over the qubits (us)", "windows",
           "DD-eligible", "S_T1", "S_T2", "S_DD", "f_gates", "f (DD off)"], rows)}

## 2. Per qubit of `{cid}`

{md_table(["physical qubit", "T1 (us)", "T2 (us)", "busy (us)", "idle (us)", "windows",
           "DD-eligible", "longest window (us)", "S_T1", "S_T2"], qrows)}

## 3. Preregistered predictions at {sp.get('shots')} shots

{md_table(["case", "hypothesis", "yield", "accepted of " + str(sp.get('shots'))], prows)}

Garbage floor {sp.get('garbage_floor_expected', float('nan')):.1f} of {sp.get('shots')} at a =
{sp.get('garbage_acceptance', float('nan')):.5f}.  Decision rule: {sp.get('decision_rule')}.

## 4. Idle-test predictions (per physical qubit)

{md_table(["circuit", "qubit", "T1 (us)", "T2 (us)", "P(1 survives)", "P(0) bound"], irows)}

## 5. Per patch

{md_table(["patch", "circuits", "S_T2 mean", "S_T2 min", "S_T2 max"],
          [[k, v["n_circuits"], f"{v['mean']:.3f}", f"{v['min']:.3f}", f"{v['max']:.3f}"]
           for k, v in sorted(res["per_patch_S_T2"].items())])}

Every number here is computed by the script from `{args.calibration or args.backend}`; none is fitted.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--calibration", default=None, help="a calibration record JSON (offline)")
    ap.add_argument("--backend", default=None, help="read the calibration live (h0_backends.fresh_calibration)")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--shots", type=int, default=2000, help="shots the session predictions are made at")
    ap.add_argument("--hb-from", default=os.path.join("validation", "H0P_ibm_fez.json"),
                    help="the gate-only prediction that hypothesis H_B expects to be restored")
    ap.add_argument("--out", default=None, help="default <prep>/idle_model_<fingerprint16>.json")
    ap.add_argument("--cal-out", default=None,
                    help="--backend: where to write the calibration record it just read "
                         "(default <prep>/calibration_<stamp>.json)")
    ap.add_argument("--md", default=None, help="write a markdown report to this path")
    args = ap.parse_args()
    t0 = time.time()
    if (args.calibration is None) == (args.backend is None):
        raise SystemExit("give exactly one of --calibration <record.json> and --backend <name>")

    prep = os.path.join(ROOT, args.prep) if not os.path.isabs(args.prep) else args.prep
    backend = None
    if args.backend:
        backend = resolve_backend(args.backend)
        qubits, edges = frozen_qubits_and_edges(prep)
        rec = fresh_calibration(backend, qubits, edges)
        if rec["missing_errors"]:
            raise SystemExit(f"{len(rec['missing_errors'])} target entries carry no error on "
                             f"{args.backend}: the model cannot be built today")
        if args.cal_out:
            capath = (args.cal_out if os.path.isabs(args.cal_out)
                      else os.path.join(ROOT, args.cal_out))
        else:
            capath = os.path.join(prep, f"calibration_{rec['stamp']}.json")
        os.makedirs(os.path.dirname(capath), exist_ok=True)
        with open(capath, "w") as fh:
            json.dump(rec, fh, indent=1)
        print(f"wrote {os.path.relpath(capath, ROOT)} (fingerprint {rec['fingerprint'][:16]})")
    else:
        p = args.calibration if os.path.isabs(args.calibration) else os.path.join(ROOT, args.calibration)
        with open(p) as fh:
            rec = json.load(fh)

    res = analyse(prep, rec, only=args.only, backend=backend, shots=args.shots, hb=args.hb_from)
    res["calibration"]["path"] = (os.path.relpath(capath, ROOT) if args.backend
                                  else os.path.relpath(p, ROOT))
    res["calibration"]["source"] = ("live target (h0_backends.fresh_calibration)" if args.backend
                                    else "committed calibration record")
    res["runtime_s"] = time.time() - t0

    out = args.out or os.path.join(prep, f"idle_model_{res['calibration']['fingerprint'][:16]}.json")
    out = out if os.path.isabs(out) else os.path.join(ROOT, out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"wrote {os.path.relpath(out, ROOT)}")
    for cid in sorted(res["circuits"]):
        c = res["circuits"][cid]
        b = c["budget"]
        print(f"  {cid:<22} T {c['T_s'] * 1e6:8.2f} us  S_T1 {b['S_T1']:.3f}  S_T2 {b['S_T2']:.3f}  "
              f"eligible {b['dd_eligible']:4d}  S_DD {b['S_DD']:.3f}  f_gates {c['f_gates']:.4f}  "
              f"f(DD off) {c['prediction']['dd_off']['f']:.3e}")
    sp = res.get("session_prediction")
    if sp and sp.get("H_A", {}).get("expected") is not None:
        hb_txt = ("n/a" if sp["H_B"].get("expected") is None
                  else f"{sp['H_B']['expected']:.1f} +- {sp['H_B']['sigma']:.1f}")
        print(f"  J1 canary at {sp['shots']} shots: H_A {sp['H_A']['expected']:.1f} +- "
              f"{sp['H_A']['sigma']:.1f}, H_B {hb_txt} "
              f"(garbage floor {sp['garbage_floor_expected']:.1f})")
    if args.md:
        mp = args.md if os.path.isabs(args.md) else os.path.join(ROOT, args.md)
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        with open(mp, "w") as fh:
            fh.write(report_text(res, args))
        print(f"wrote {os.path.relpath(mp, ROOT)}")
    print(f"{time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
