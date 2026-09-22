#!/usr/bin/env python3
"""
Gate S2D_idle — gate S2D's 2x2 criterion re-evaluated on the IDLE-AWARE clean-shot fraction.

Item 2 of `proposal/amendment_01_devices_and_budgets.md` replaces the fixed CZ numbers of
manual Step 4.3 by the criterion of section 1(c): mean f >= 0.1 over the production circuit
set and worst-circuit f >= 0.05.  Gate S2D evaluated that criterion on

    f_gates = prod_{cz} (1 - eps_edge) x prod_{measured} (1 - eps_ro)      (`analyse_on_backend`)

and found 2x2/Heron PASS at mean 0.1248, worst 0.1166 on the FakeFez calibration.  Gate H0
then ran the circuits: the canary measured f = 0.0255 (8 accepted of 267) where that model
predicted 0.2195, and gate H0_diag (2026-09-22, 15.0 s of QPU over four jobs) showed the whole
discrepancy is the term the model does not contain -- the time a qubit waits for other qubits'
gates.  `f_gates` omits it; so does `NoiseModel.from_backend` on an unscheduled circuit.

**This script changes what f means, not what the bar is.**  The 0.1 and 0.05 thresholds are
the owner's and are used exactly as they stand.  f becomes

    f = f_gates x exp(-S_idle),    S_idle = S_T1 + S_T2   (DD off)      (`skqd.idle`)

with S_T1, S_T2 the idle-window relaxation budget of the circuit's own ASAP schedule on the
calibration record.  Gate S2D's `analyse_on_backend` is not touched and `validation/S2D.json`,
`S2.json` and the H0P chain remain the record of what was computed with the gate-only model;
this gate writes `validation/S2D_idle.json` beside them.

**The T2 bracket is an open parameter, not a choice made here.**  H0_diag measured the
free-induction T2* on the canary patch and found it 2-7x shorter than the calibration's
Hahn-echo T2 (median ratio 0.174 over the 9 qubits with a usable time).  On the echo T2 the
idle-aware model predicted 31 accepted shots against the measured 35 (a factor 1.13); on the
measured T2* it is 89x too pessimistic.  Both ends are therefore computed and reported, and
the convention is a recorded field (`t2_convention`) of every number below, never a default
buried in the code.  Which end the amendment is written on is the planner's decision.

What is computed (offline, no QPU time, no IBM account):
  1. the 28 exact structured 2x2 coarse-step circuits of gate S2D, transpiled exactly as gate
     S2D transpiles them (FakeFez, optimization_level 3, seed_transpiler 7), with f_gates
     asserted equal to `gate_S2D.analyse_on_backend` to 1e-12 and to `validation/S2D.json`;
  2. their ASAP schedules and idle budgets on TWO calibration records -- the FakeFez snapshot
     gate S2D used, and the live ibm_fez record the canary actually ran on -- at both ends of
     the T2 bracket, DD off and over the DD refocusing bracket rho;
  3. the criterion (mean >= 0.1, worst >= 0.05) evaluated at each end;
  4. what a device would have to satisfy instead: the log-error budget accounting, and the
     factor by which the patch's coherence times (equivalently: its idle time) would have to
     improve for the criterion to be met on this circuit family;
  5. the implication for the 2x3 requirement sheet, as a shift of the half-space of
     `skqd.device_req` by S_idle (the sheet itself is not edited).

Usage: python scripts/gate_S2D_idle.py [--level 3] [--seed 7] [--no-tests] [--quick]
Expected runtime: about 30 s plus the test suite (i7-8750H, CPU only).
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd import device_req as dr  # noqa: E402
from skqd import idle  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import yield_model  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# The owner's bars -- unchanged, and not recomputed anywhere in this file.
F_MEAN_MIN, F_WORST_MIN = 0.1, 0.05

RHOS = (0.0, 0.25, 0.5, 1.0)          # DD refocusing bracket (prompts/19, h0_idle_model.RHOS)
LIVE_RECORD = os.path.join("data", "hardware", "H0_ibm_fez_canary",
                           "calibration_at_submission_20260922T1400Z.json")
FROZEN_IDLE_MODEL = os.path.join("data", "hardware", "H0_diag_prep",
                                 "idle_model_frozen_set_7fd6d65e.json")
CANARY_ID = "B0_ref06_k1_rep1"        # sector B=0, reference 6, k = 1 -- the circuit H0 ran
CANARY_KEY = ("B=0", 6, 1)
ANCHOR_FACTOR = 1.5                   # the idle-aware post-diction must be this close to J1
TOL = 1e-12


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


# --------------------------------------------------------------------- the circuit set
def build_2x2_set(level, seed, quick=False):
    """The 28 circuits of gate S2D's 2x2 set, transpiled with gate S2D's own settings."""
    from qiskit import transpile
    from qiskit_ibm_runtime.fake_provider import FakeFez

    from gate_S2D import circuit_set
    from skqd import circuits_qiskit as cq

    M, F, gates = circuit_set(2)
    if quick:
        gates = [g for g in gates if g[2] == 1]
    backend = FakeFez()
    out, qubits, edges = [], set(), set()
    for twoB, r, k, ir in gates:
        qc = cq.ir_to_qiskit(ir, F.n, measure=True)
        tq = transpile(qc, backend=backend, optimization_level=level, seed_transpiler=seed)
        label = (f"B={twoB // 2}", int(r), int(k))
        out.append((label, tq))
        for inst in tq.data:
            if inst.operation.name == "barrier":
                continue
            qs = tuple(tq.find_bit(q).index for q in inst.qubits)
            qubits.update(qs)
            if inst.operation.name == "cz":
                edges.add(qs)
    return M, out, sorted(qubits), sorted(edges), backend


def f_gates_on_record(tq, record):
    """`gate_S2D.analyse_on_backend`'s f, evaluated on a calibration RECORD."""
    import h0_support_plan as sp
    cz = {}
    for e in record["edges"].values():
        key = tuple(e["target_key"])
        for k in (key, key[::-1]):
            cz[k] = e["cz_error"]
    meas = {int(q): v["measure_error"] for q, v in record["qubits"].items()}
    f, n_cz, n_meas = sp.f_from_calibration(tq, cz, meas)
    return float(f), int(n_cz), int(n_meas)


# --------------------------------------------------------------------- the T2 bracket
def measured_t2_ratios(path=None, cell="J1"):
    """The measured end of the T2 bracket, as ratios T2_measured / T2_record.

    Read from `validation/H0_diag.json`: the windowed Ramsey (`ramw`) pub of the given
    diagnostic cell, readout-corrected there, one entry per qubit that produced either a
    T2* or a 3-sigma upper bound.  Ratios rather than times, so that the measurement made
    on the canary patch can be carried to another qubit of another record explicitly; the
    fallback for a qubit with no measurement is the median of the measured ratios.
    """
    p = path or os.path.join(ROOT, "validation", "H0_diag.json")
    with open(p) as fh:
        d = json.load(fh)["data"]
    per = d["idle_tests"][cell]["ramw"]["per_qubit"]
    ratios, used_bound, no_time = {}, [], []
    for q, v in per.items():
        t2 = v["T2star_measured_s"] or v["T2star_upper_bound_s"]
        if not t2:
            no_time.append(int(q))
            continue
        if v["T2star_measured_s"] is None:
            used_bound.append(int(q))
        ratios[int(q)] = float(t2) / float(v["T2_record_s"])
    if not ratios:
        raise SystemExit(f"{p}: the {cell} ramw pub produced no usable dephasing time")
    med = float(np.median(list(ratios.values())))
    return {
        "per_qubit_ratio": ratios, "fallback_ratio": med,
        "source": f"validation/H0_diag.json data.idle_tests.{cell}.ramw (windowed Ramsey, "
                  f"total delay {d['idle_tests'][cell]['ramw']['total_delay_s'] * 1e6:.2f} us)",
        "n_measured": len(ratios), "n_from_upper_bound": len(used_bound),
        "qubits_from_upper_bound": sorted(used_bound),
        "qubits_without_a_usable_time": sorted(no_time),
        "ratio_min": float(min(ratios.values())), "ratio_max": float(max(ratios.values())),
        "note": ("T2_record is the calibration's Hahn-echo T2; a fully dephased qubit "
                 "contributes its 3-sigma upper bound, a qubit with neither contributes "
                 "nothing and takes the fallback ratio like any unmeasured qubit"),
    }


def t2_conventions(record, qubits, measured):
    """The two ends of the bracket as {name: (label, {qubit: T2})}."""
    echo = idle.effective_t2(record, qubits, ratio=1.0)
    star = idle.effective_t2(record, qubits, ratio=measured["fallback_ratio"],
                             per_qubit_ratio=measured["per_qubit_ratio"])
    return {
        "echo": {"t2_s": echo, "ratio": 1.0,
                 "label": "Hahn-echo T2 of the calibration record (the record as it stands)",
                 "anchor": "on this end the idle-aware model predicted 31 accepted shots of "
                           "2000 against the measured 35 (gate H0_diag, factor 1.13)"},
        "star": {"t2_s": star, "ratio": measured["fallback_ratio"],
                 "label": "measured free-induction T2* (H0_diag windowed Ramsey), as a ratio "
                          "to the record's echo T2",
                 "anchor": "on this end the same model is 89x too pessimistic against J1 "
                           "(gate H0_diag criterion C5)"},
    }


# --------------------------------------------------------------------- evaluation
def agg(values):
    v = list(values)
    return {"mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}


def evaluate_record(circuits, record, measured, backend=None):
    """Schedules, idle budgets and idle-aware f of the whole set on one calibration record."""
    qubits = sorted(int(q) for q in record["qubits"])
    conv = t2_conventions(record, qubits, measured)
    per = []
    max_df, max_dT = 0.0, 0.0
    for label, tq in circuits:
        sch = idle.schedule_asap(tq, record)
        fg, n_cz, n_meas = f_gates_on_record(tq, record)
        if backend is not None:
            from gate_S2D import analyse_on_backend
            from h0_qpu_time import circuit_duration_s
            max_df = max(max_df, abs(analyse_on_backend(tq, backend)["f"] - fg))
            max_dT = max(max_dT, abs(circuit_duration_s(tq, backend.target.durations(),
                                                        backend.target) - sch["T_total_s"]))
        e = {"sector": label[0], "reference": label[1], "k": label[2],
             "n_cz": n_cz, "n_measure": n_meas, "f_gates": fg,
             "T_s": sch["T_s"], "T_total_s": sch["T_total_s"],
             "measured_qubits": sch["measured_qubits"], "active_qubits": sch["active"],
             "f": {}, "budget": {}}
        for name, c in conv.items():
            per_q, tot = idle.idle_budget(sch, record, t2_s=c["t2_s"])
            e["budget"][name] = tot
            e["f"][name] = {"dd_off": idle.f_idle_aware(fg, tot),
                            "dd_on": {str(r): idle.f_idle_aware(fg, tot, r) for r in RHOS},
                            "S_idle": idle.idle_log_budget(tot)}
            if name == "echo":
                e["per_qubit_echo"] = per_q
        per.append(e)

    out = {
        "calibration": {k: record.get(k) for k in
                        ("backend", "last_update_date", "stamp", "fingerprint")},
        "n_circuits": len(per),
        "f_gates": agg([e["f_gates"] for e in per]),
        "n_cz": agg([e["n_cz"] for e in per]),
        "T_s": agg([e["T_s"] for e in per]),
        "reproduction": {"max_abs_diff_f_vs_analyse_on_backend": max_df,
                         "max_abs_diff_duration_vs_h0_qpu_time": max_dT},
        "t2_convention": {k: {kk: vv for kk, vv in v.items() if kk != "t2_s"}
                          for k, v in conv.items()},
        "t2_s_per_qubit": {k: {str(q): t for q, t in v["t2_s"].items()
                               if q in set(per[0]["active_qubits"])}
                           for k, v in conv.items()},
        "by_convention": {},
        "per_circuit": per,
    }
    for name in conv:
        b = {"S_T1": agg([e["budget"][name]["S_T1"] for e in per]),
             "S_T2": agg([e["budget"][name]["S_T2"] for e in per]),
             "S_idle": agg([e["f"][name]["S_idle"] for e in per]),
             "S_DD": agg([e["budget"][name]["S_DD"] for e in per]),
             "dd_eligible": agg([e["budget"][name]["dd_eligible"] for e in per]),
             "n_windows": agg([e["budget"][name]["n_windows"] for e in per]),
             "f_dd_off": agg([e["f"][name]["dd_off"] for e in per]),
             "f_dd_on": {str(r): agg([e["f"][name]["dd_on"][str(r)] for e in per])
                         for r in RHOS}}
        b["criterion_dd_off"] = criterion(b["f_dd_off"])
        b["criterion_best_of_bracket"] = criterion(b["f_dd_on"]["0.0"])
        out["by_convention"][name] = b
    return out


def criterion(f_agg):
    """The owner's criterion of amendment 01 section 1(c), read on a given f."""
    return {"mean_f": f_agg["mean"], "worst_f": f_agg["min"],
            "mean_f_min": F_MEAN_MIN, "worst_f_min": F_WORST_MIN,
            "mean_passes": bool(f_agg["mean"] >= F_MEAN_MIN),
            "worst_passes": bool(f_agg["min"] >= F_WORST_MIN),
            "passes": bool(f_agg["mean"] >= F_MEAN_MIN and f_agg["min"] >= F_WORST_MIN),
            "thresholds_source": "amendment 01 section 1(c) / gate S2D (unchanged)"}


# --------------------------------------------------------------------- what a device needs
def coherence_scale(circuits, record, conv_t2, stat="mean", target=F_MEAN_MIN,
                    lam_max=1e6, iters=200):
    """Factor lam on every T1 and T2 of the patch at which `stat` of the idle-aware f reaches
    `target` (DD off).  Because (1 - e^{-w/(lam T)}) is the same function of the window w
    scaled by 1/lam, lam is equally the factor by which the SCHEDULE would have to shrink.
    None when even lam -> infinity (no idle time at all) leaves f below the target: the gate
    errors alone then exhaust the budget."""
    base = []
    for _label, tq in circuits:
        sch = idle.schedule_asap(tq, record)
        fg, _n, _m = f_gates_on_record(tq, record)
        base.append((sch, fg))
    qubits = sorted(int(q) for q in record["qubits"])

    def value(lam):
        vals = []
        t1 = idle.effective_t1(record, qubits, ratio=lam)
        t2 = {q: t * lam for q, t in conv_t2.items()}
        for sch, fg in base:
            _pq, tot = idle.idle_budget(sch, record, t2_s=t2, t1_s=t1)
            vals.append(idle.f_idle_aware(fg, tot))
        return float(np.mean(vals)) if stat == "mean" else float(np.min(vals))

    limit = (float(np.mean([f for _s, f in base])) if stat == "mean"
             else float(np.min([f for _s, f in base])))
    if limit < target:
        return None, limit
    lo, hi = 1.0, 1.0
    if value(lo) >= target:
        return 1.0, limit
    while value(hi) < target:
        hi *= 2.0
        if hi > lam_max:
            return None, limit
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if value(mid) >= target:
            hi = mid
        else:
            lo = mid
    return float(hi), limit


def log_budget_accounting(f_gates, s_idle, f_target=F_MEAN_MIN):
    """Where the log-error budget ln(1/f_target) goes once idle time is charged."""
    spent_gates = -math.log(f_gates)
    budget = -math.log(f_target)
    return {"f_target": f_target, "budget_log": budget,
            "spent_by_gates_and_readout": spent_gates, "spent_by_idle": float(s_idle),
            "total": spent_gates + float(s_idle),
            "over_budget_by": spent_gates + float(s_idle) - budget,
            "f_gates": f_gates, "f_idle_aware": f_gates * math.exp(-float(s_idle)),
            "statement": "n_2q eps2~ + n_meas eps_ro~ + S_idle <= ln(1/f_target) "
                         "(skqd.device_req.target_with_idle)"}


def implication_2x3(s_idle_values, path=None):
    """What the idle term does to the 2x3 requirement sheet, WITHOUT editing the sheet.

    The sheet (`reports/S2D_2x3_device_requirements.md`, `data/S2D_2x3_device_requirements.json`)
    inverts the gate-only f on the 44-circuit all-to-all set.  With idle time the criterion is
    the same half-space shifted by S_idle, so every requirement it states is the requirement at
    the shifted target `device_req.target_with_idle(f_target, S_idle)`.  This function
    recomputes the sheet's two-qubit requirement at a range of S_idle -- it does not claim a
    value of S_idle for that device: no schedule, gate duration or coherence time has been
    declared for it, and until they are, S_idle at 2x3 is not computable here.
    """
    p = path or os.path.join(ROOT, "data", "S2D_2x3_device_requirements.json")
    with open(p) as fh:
        d = json.load(fh)
    counts = [dr.CircuitCounts(c["rzz"], c["n_1q"], c["n_rz"], d["counts"]["measured_qubits"],
                               c["label"]) for c in d["counts"]["per_circuit_recomputed"]]
    decl = d["feasible_region"]["declared_inputs"]
    eps2, eps1, eps_ro = decl["eps2"], decl["eps1"], decl["eps_ro"]
    rows = []
    for s in s_idle_values:
        try:
            tgt_mean = dr.target_with_idle(F_MEAN_MIN, s)
            tgt_worst = dr.target_with_idle(F_WORST_MIN, s)
        except ValueError as exc:
            rows.append({"S_idle": float(s), "unreachable": str(exc)})
            continue
        rows.append({
            "S_idle": float(s),
            "f_target_mean_shifted": tgt_mean, "f_target_worst_shifted": tgt_worst,
            "eps2_for_mean": dr.required_error_for_set(counts, "2q", eps2, eps1, eps_ro,
                                                       tgt_mean, stat="mean"),
            "eps2_for_worst": dr.required_error_for_set(counts, "2q", eps2, eps1, eps_ro,
                                                        tgt_worst, stat="min"),
            "mean_f_at_declared": dr.set_f(counts, eps2, eps1, eps_ro)["mean"] * math.exp(-s),
        })
    return {
        "source": "data/S2D_2x3_device_requirements.json (counts and declared inputs; the "
                  "sheet itself is unchanged)",
        "n_circuits": len(counts), "declared_inputs": decl,
        "eps2_of_the_sheet_at_S_idle_0": rows[0].get("eps2_for_mean"),
        "rows": rows,
        "note": ("S_idle at 2x3 is NOT computed here: the all-to-all device has no declared "
                 "gate durations and no declared T1/T2, so its schedule cannot be built.  The "
                 "rows are the requirement AS A FUNCTION of whatever S_idle it turns out to "
                 "have; the largest S_idle in the table is the 2x2/Heron value measured on "
                 "the live record (section 4), shown for scale only."),
    }


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--quick", action="store_true", help="k = 1 only (smoke test, not the gate)")
    args = ap.parse_args()
    t0 = time.time()

    from gate_S2D import garbage_acceptance_exhaustive
    from h0_backends import calibration_record

    R = GateResult("S2D_idle",
                   "Gate S2D's 2x2 criterion (mean f >= 0.1, worst f >= 0.05) re-evaluated on "
                   "the idle-aware clean-shot fraction, at both ends of the T2 bracket")
    M2, circuits, qubits, edges, backend = build_2x2_set(args.level, args.seed, args.quick)
    print(f"2x2: {len(circuits)} circuits on {len(qubits)} physical qubits, {len(edges)} "
          f"directed edges ({time.time() - t0:.0f} s)", flush=True)

    measured = measured_t2_ratios()
    print(f"T2* ratios: {measured['n_measured']} measured, median {measured['fallback_ratio']:.4f}",
          flush=True)

    records = {"FakeFez snapshot (the calibration gate S2D used)":
               calibration_record(backend, qubits, edges)}
    with open(os.path.join(ROOT, LIVE_RECORD)) as fh:
        live = json.load(fh)
    records["live ibm_fez at the canary submission"] = live
    missing_q = [q for q in qubits if str(q) not in live["qubits"]]
    live_edges = set()
    for e in live["edges"].values():
        a, b = e["target_key"]
        live_edges.update({(a, b), (b, a)})
    missing_e = [e for e in edges if tuple(e) not in live_edges]
    if missing_q or missing_e:
        raise SystemExit(f"the live record does not cover the transpiled set: qubits "
                         f"{missing_q}, edges {missing_e}")

    data = {
        "what_changed": ("f now includes idle-time relaxation over the circuit's own ASAP "
                         "schedule (skqd.idle); the thresholds 0.1 and 0.05 are unchanged and "
                         "gate_S2D.analyse_on_backend is untouched"),
        "criterion": {"mean_f_min": F_MEAN_MIN, "worst_f_min": F_WORST_MIN,
                      "source": "amendment 01 section 1(c) / gate S2D",
                      "f_model": "f = f_gates x exp(-S_idle), f_gates = "
                                 "gate_S2D.analyse_on_backend, S_idle = S_T1 + S_T2 (DD off) "
                                 "or S_T1 + rho S_T2_eligible + S_T2_ineligible + S_DD (DD on)"},
        "circuit_family": "exact structured circuits, CircuitFactory default; coarse steps "
                          "k = 1..4 of every reference of both sectors (validation/S2.json)",
        "transpiler": {"backend": "FakeFez", "optimization_level": args.level,
                       "seed_transpiler": args.seed, "identical_to": "gate_S2D 2x2 path"},
        "t2_bracket": measured,
        "records": {}, "quick": bool(args.quick),
    }
    for tag, rec in records.items():
        be = backend if tag.startswith("FakeFez") else None
        data["records"][tag] = evaluate_record(circuits, rec, measured, backend=be)
        e = data["records"][tag]
        for name in ("echo", "star"):
            c = e["by_convention"][name]["criterion_dd_off"]
            print(f"  {tag} / T2 {name}: DD off mean f {c['mean_f']:.5f}, worst {c['worst_f']:.5f}"
                  f" -> {'PASS' if c['passes'] else 'FAIL'} ({time.time() - t0:.0f} s)", flush=True)

    # ---------------------------------------------------------------- the hardware anchor
    a = garbage_acceptance_exhaustive(M2)
    live_eval = data["records"]["live ibm_fez at the canary submission"]
    canary = next(e for e in live_eval["per_circuit"]
                  if (e["sector"], e["reference"], e["k"]) == CANARY_KEY)
    with open(os.path.join(ROOT, "validation", "H0_diag.json")) as fh:
        diag = json.load(fh)["data"]
    shots = int(diag["decision"]["shots_J1"])
    N1 = int(diag["decision"]["N1"])
    anchor = {}
    for name in ("echo", "star"):
        f = canary["f"][name]["dd_off"]
        y = yield_model(f, a["B=0"])
        anchor[name] = {
            "f_idle_aware": f, "yield": y, "expected_accepted": shots * y,
            "measured_accepted": N1, "shots": shots,
            "factor_measured_over_predicted": (N1 / (shots * y)) if y > 0 else None,
            "measured_f_of_the_canary_pub": diag["canary_pubs"]["J1"]["clean_fraction_from_yield"],
        }
    anchor["gate_only_for_comparison"] = {
        "f_gates": canary["f_gates"],
        "yield": yield_model(canary["f_gates"], a["B=0"]),
        "expected_accepted": shots * yield_model(canary["f_gates"], a["B=0"]),
        "measured_accepted": N1,
        "factor_measured_over_predicted": N1 / (shots * yield_model(canary["f_gates"], a["B=0"])),
    }
    anchor["measured_f_by_cell"] = {j: v["clean_fraction_from_yield"]
                                    for j, v in diag["canary_pubs"].items()}
    anchor["measured_f_H0_canary"] = json.load(
        open(os.path.join(ROOT, "validation", "H0_canary.json")))["data"]["f_comparison"][
        "B=0 r=1"]["measured_f"]
    anchor["circuit"] = CANARY_ID
    anchor["garbage_acceptance"] = a
    data["hardware_anchor"] = anchor

    # the committed idle model of the frozen set: the same circuit, the same record
    with open(os.path.join(ROOT, FROZEN_IDLE_MODEL)) as fh:
        frozen = json.load(fh)["circuits"][CANARY_ID]
    diffs = {k: abs(canary["budget"]["echo"][k] - frozen["budget"][k])
             for k in ("S_T1", "S_T2", "S_DD")}
    diffs["T_s"] = abs(canary["T_s"] - frozen["T_s"])
    diffs["f_gates"] = abs(canary["f_gates"] - frozen["f_gates"])
    data["frozen_circuit_check"] = {
        "source": FROZEN_IDLE_MODEL, "circuit": CANARY_ID,
        "max_abs_diff": max(diffs.values()), "per_field": diffs,
        "dd_eligible_here": canary["budget"]["echo"]["dd_eligible"],
        "dd_eligible_frozen": frozen["budget"]["dd_eligible"],
        "note": ("the S2D circuit (B=0, reference 6, k = 1) transpiled here IS the frozen "
                 "canary circuit: same family, same backend, same optimization level and seed"),
    }

    # ---------------------------------------------------------------- what a device needs
    need = {}
    for tag, rec in records.items():
        qs = sorted(int(q) for q in rec["qubits"])
        conv = t2_conventions(rec, qs, measured)
        e = data["records"][tag]
        row = {}
        for name in ("echo", "star"):
            lam_mean, lim_mean = coherence_scale(circuits, rec, conv[name]["t2_s"],
                                                 stat="mean", target=F_MEAN_MIN)
            lam_worst, lim_worst = coherence_scale(circuits, rec, conv[name]["t2_s"],
                                                   stat="min", target=F_WORST_MIN)
            row[name] = {
                "coherence_scale_for_mean_0.1": lam_mean,
                "coherence_scale_for_worst_0.05": lam_worst,
                "limit_mean_f_gates": lim_mean, "limit_worst_f_gates": lim_worst,
                "log_budget_mean": log_budget_accounting(
                    e["f_gates"]["mean"], e["by_convention"][name]["S_idle"]["mean"]),
                "meaning": ("every T1 and T2 of the patch multiplied by this factor -- "
                            "equivalently every idle window divided by it -- with the gate "
                            "and readout errors of the record unchanged"),
            }
        need[tag] = row
    data["device_requirement"] = need

    # ---------------------------------------------------------------- 2x3 implication
    s_live = data["records"]["live ibm_fez at the canary submission"][
        "by_convention"]["echo"]["S_idle"]["mean"]
    data["implication_2x3"] = implication_2x3([0.0, 0.1, 0.3, 1.0, round(s_live, 3)])

    # ---------------------------------------------------------------- criteria
    with open(os.path.join(ROOT, "validation", "S2D.json")) as fh:
        s2d = json.load(fh)["data"]["2x2"]["snapshots"]["FakeFez"]
    ff = data["records"]["FakeFez snapshot (the calibration gate S2D used)"]
    d_mean = abs(ff["f_gates"]["mean"] - s2d["f"]["mean"])
    d_worst = abs(ff["f_gates"]["min"] - s2d["f"]["min"])
    R.add("V1 gate-only f reproduces validation/S2D.json (FakeFez mean and worst)",
          max(d_mean, d_worst), f"<= {TOL:.0e}", max(d_mean, d_worst) <= TOL)
    R.add("V2 f on the record equals gate_S2D.analyse_on_backend over the 28 circuits",
          ff["reproduction"]["max_abs_diff_f_vs_analyse_on_backend"], f"<= {TOL:.0e}",
          ff["reproduction"]["max_abs_diff_f_vs_analyse_on_backend"] <= TOL)
    R.add("V3 the ASAP schedule reproduces h0_qpu_time.circuit_duration_s",
          ff["reproduction"]["max_abs_diff_duration_vs_h0_qpu_time"], f"<= {TOL:.0e}",
          ff["reproduction"]["max_abs_diff_duration_vs_h0_qpu_time"] <= TOL)
    R.add(f"V4 the {CANARY_ID} budget reproduces the committed idle model of the frozen set",
          data["frozen_circuit_check"]["max_abs_diff"], f"<= {TOL:.0e}",
          data["frozen_circuit_check"]["max_abs_diff"] <= TOL)
    R.add(f"V5 hardware anchor: idle-aware (echo T2) predicts "
          f"{anchor['echo']['expected_accepted']:.1f} accepted of {shots}, measured {N1}",
          round(anchor["echo"]["factor_measured_over_predicted"], 3),
          f"within a factor {ANCHOR_FACTOR}",
          1.0 / ANCHOR_FACTOR <= anchor["echo"]["factor_measured_over_predicted"] <= ANCHOR_FACTOR)
    for tag in records:
        short = "FakeFez" if tag.startswith("FakeFez") else "live ibm_fez"
        for name, end in (("echo", "Hahn-echo T2"), ("star", "measured T2*")):
            c = data["records"][tag]["by_convention"][name]["criterion_dd_off"]
            R.add(f"C {short} / {end}: mean idle-aware f over the {ff['n_circuits']} circuits "
                  f"(DD off)", c["mean_f"], f">= {F_MEAN_MIN}", c["mean_passes"])
            R.add(f"C {short} / {end}: worst-circuit idle-aware f (DD off)",
                  c["worst_f"], f">= {F_WORST_MIN}", c["worst_passes"])
    best = data["records"]["live ibm_fez at the canary submission"][
        "by_convention"]["echo"]["criterion_best_of_bracket"]
    R.add("C most favourable point of the whole bracket (live record, echo T2, rho = 0: DD "
          "refocuses the eligible windows perfectly): mean f", best["mean_f"],
          f">= {F_MEAN_MIN}", best["mean_passes"])
    if not args.no_tests:
        tp = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT,
                            capture_output=True, text=True)
        line = tp.stdout.strip().splitlines()[-1] if tp.stdout.strip() else "no output"
        line = re.sub(r"\x1b\[[0-9;]*m", "", line)      # pytest colours its summary line
        R.add("pytest -q tests", line, "all pass", tp.returncode == 0)
        data["pytest"] = line
    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report("S2D_idle_device_budgets.md", report_text(args, R, data))
    print(R.criteria_table())
    return 0 if R.passed else 1


# --------------------------------------------------------------------- report
def report_text(args, R, D):
    rows = []
    for tag, e in D["records"].items():
        for name in ("echo", "star"):
            b = e["by_convention"][name]
            rows.append([tag.split(" (")[0], name, f"{e['f_gates']['mean']:.4f}",
                         f"{b['S_T1']['mean']:.3f}", f"{b['S_T2']['mean']:.3f}",
                         f"{b['f_dd_off']['mean']:.2e}", f"{b['f_dd_off']['min']:.2e}",
                         "PASS" if b["criterion_dd_off"]["passes"] else "**FAIL**",
                         f"{b['f_dd_on']['0.0']['mean']:.2e}",
                         f"{b['f_dd_on']['1.0']['mean']:.2e}"])
    brows = []
    for tag, e in D["records"].items():
        for name in ("echo", "star"):
            b = e["by_convention"][name]
            for r in ("0.0", "0.25", "0.5", "1.0"):
                brows.append([tag.split(" (")[0], name, r, f"{b['f_dd_on'][r]['mean']:.3e}",
                              f"{b['f_dd_on'][r]['min']:.3e}"])
    a = D["hardware_anchor"]
    arows = [["idle-aware, echo T2", f"{a['echo']['f_idle_aware']:.2e}",
              f"{a['echo']['expected_accepted']:.1f}", a["echo"]["measured_accepted"],
              f"{a['echo']['factor_measured_over_predicted']:.2f}"],
             ["idle-aware, measured T2*", f"{a['star']['f_idle_aware']:.2e}",
              f"{a['star']['expected_accepted']:.1f}", a["star"]["measured_accepted"],
              f"{a['star']['factor_measured_over_predicted']:.2f}"],
             ["gate-only (gate S2D's f)", f"{a['gate_only_for_comparison']['f_gates']:.4f}",
              f"{a['gate_only_for_comparison']['expected_accepted']:.1f}",
              a["gate_only_for_comparison"]["measured_accepted"],
              f"{a['gate_only_for_comparison']['factor_measured_over_predicted']:.3f}"]]
    nrows = []
    for tag, row in D["device_requirement"].items():
        for name in ("echo", "star"):
            v = row[name]
            lb = v["log_budget_mean"]
            nrows.append([tag.split(" (")[0], name,
                          f"{lb['spent_by_gates_and_readout']:.3f}", f"{lb['spent_by_idle']:.3f}",
                          f"{lb['budget_log']:.3f}", f"{lb['over_budget_by']:.3f}",
                          "n/a" if v["coherence_scale_for_mean_0.1"] is None
                          else f"{v['coherence_scale_for_mean_0.1']:.1f}",
                          "n/a" if v["coherence_scale_for_worst_0.05"] is None
                          else f"{v['coherence_scale_for_worst_0.05']:.1f}"])
    irows = []
    for r in D["implication_2x3"]["rows"]:
        if "unreachable" in r:
            irows.append([f"{r['S_idle']:.3f}", "unreachable", "-", "-", "-"])
            continue
        irows.append([f"{r['S_idle']:.3f}", f"{r['f_target_mean_shifted']:.4f}",
                      "none" if r["eps2_for_mean"] is None else f"{r['eps2_for_mean']:.3e}",
                      "none" if r["eps2_for_worst"] is None else f"{r['eps2_for_worst']:.3e}",
                      f"{r['mean_f_at_declared']:.4f}"])
    m = D["t2_bracket"]
    return f"""# Gate S2D's criterion on the idle-aware f — 2x2 on Heron

{R.title}.  Generated by `scripts/gate_S2D_idle.py` at commit `{git_commit()}`; every number
is read from `validation/S2D_idle.json`, which the same run wrote.  {env_block()}
Runtime {R.runtime_s:.0f} s.  No QPU time: both calibrations are committed records.
`pytest -q tests`: {D.get('pytest', 'not run')}.

**Status: {'PASS' if R.passed else 'FAIL'}.**

## 0. What changed and what did not

{D['what_changed']}.

The criterion is unchanged: **mean f >= {F_MEAN_MIN}, worst-circuit f >= {F_WORST_MIN}**
({D['criterion']['source']}).  The f model is

    {D['criterion']['f_model']}

Gate S2D's `analyse_on_backend` is not modified and `validation/S2D.json` is not overwritten:
they are the record of what was computed before gate H0 ran the circuits.  The gate-only f is
the S_idle = 0 limit of the model above and is reproduced here to {TOL:.0e} (criteria V1, V2).

## 1. The T2 bracket

The calibration record carries the vendor's **Hahn-echo T2**.  The windowed Ramsey test of
gate H0_diag measured the **free-induction T2\\*** on the same patch on the same day:
{m['n_measured']} of 12 qubits produced a usable time ({m['n_from_upper_bound']} of them only a
3-sigma upper bound, qubits {m['qubits_from_upper_bound']}), and the ratio T2\\*/T2_echo ranges
{m['ratio_min']:.3f}-{m['ratio_max']:.3f} with median **{m['fallback_ratio']:.4f}**, which is
the fallback for the unmeasured qubits.  Source: {m['source']}.

The effective dephasing time inside a circuit lies somewhere between the two and H0_diag does
not determine where (its criterion C5 failed by a factor 89 at the T2\\* end and the echo end
post-dicts J1 to a factor 1.13).  **Both ends are reported; neither is adopted here.**

## 2. The criterion on the idle-aware f (DD off)

{md_table(["calibration record", "T2", "f_gates mean", "S_T1 mean", "S_T2 mean",
           "idle-aware f mean", "worst", "criterion", "f mean at rho=0", "f mean at rho=1"], rows)}

`rho` is the fraction of the DD-eligible T2 budget that survives dynamical decoupling: rho = 0
is perfect refocusing (the most favourable point of the bracket, not an achievable one -- the
canary ran with XY4 DD on and measured a *lower* yield than with it off), rho = 1 is no
refocusing at all with the pulse cost still paid.

{md_table(["calibration record", "T2", "rho", "f mean", "f worst"], brows)}

## 3. The hardware anchor

The circuit `{a['circuit']}` of this set is the canary gate H0 ran ({D['frozen_circuit_check']['note']};
its budget reproduces the committed `{D['frozen_circuit_check']['source']}` to
{D['frozen_circuit_check']['max_abs_diff']:.1e}).  Against the J1 cell of gate H0_diag
(DD off, twirling off, {a['echo']['shots']} shots, {a['echo']['measured_accepted']} accepted):

{md_table(["f model", "f", "accepted predicted", "accepted measured", "measured / predicted"], arows)}

Measured f of the canary circuit by diagnostic cell:
{", ".join(f"{k} {v:.4f}" for k, v in a['measured_f_by_cell'].items())}; and
{a['measured_f_H0_canary']:.4f} in the canary job itself (`validation/H0_canary.json`).  Every
measured value is below the worst-circuit bar {F_WORST_MIN}, independently of any model.

## 4. What a device would have to satisfy

The criterion is the half-space {D['device_requirement'][list(D['device_requirement'])[0]]['echo']['log_budget_mean']['statement']}:

{md_table(["calibration record", "T2", "spent by gates + readout", "spent by idle",
           "budget ln(1/0.1)", "over budget by", "coherence x for mean 0.1",
           "coherence x for worst 0.05"], nrows)}

The last two columns are the factor by which every T1 and T2 of the patch would have to be
multiplied -- equivalently, the factor by which every idle window would have to shrink -- with
the record's gate and readout errors unchanged.

## 5. Implication for the 2x3 requirement sheet (not edited here)

{D['implication_2x3']['note']}  The sheet's requirement is recomputed at the shifted target
`f_target e^(S_idle)` (`skqd.device_req.target_with_idle`) over the same
{D['implication_2x3']['n_circuits']} circuits and declared inputs:

{md_table(["S_idle", "shifted mean target", "eps2 for mean 0.1", "eps2 for worst 0.05",
           "mean f at the declared eps2"], irows)}

At S_idle = 0 the first row reproduces the sheet's own two-qubit requirement
({D['implication_2x3']['eps2_of_the_sheet_at_S_idle_0']:.3e}).

## 6. Criteria

{R.criteria_table()}
"""


if __name__ == "__main__":
    sys.exit(main())
