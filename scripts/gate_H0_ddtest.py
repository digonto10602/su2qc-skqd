#!/usr/bin/env python3
"""
Gate H0_ddtest (prompts/24 Stage T) -- one preregistered four-cell A/B test of client-side
dynamical decoupling against the no-DD baseline on the pilot's two signed k = 1 circuits on
ibm_kingston, read by the preregistered adoption rule P7.

A measurement gate: PASS = preregistered, measured, verified, consistent (K1-K8).  There is no
criterion on the ratios, on the adoption or on the signed-bar read.

Stages (all 0 QPU s; the one submission is `scripts/h0_submit.py`, unchanged):

  reserve    T.A3: rule D3' at the pilot's f_pool on the day's record for the 28 signed circuits
             relabelled onto the pilot's patch, Stage R's job groups, the largest job, the reserve
             1.3 x total + 1.3 x largest, the Stage T estimate -> `<prep>/reserve.json`.  Exit 3 if
             40 + reserve > the remaining seconds of the account check.
             Coordinator ruling (2026-10-02) on planner decision P8: the D3''-H0 lift of the seven
             k = 1 circuits is STRUCK -- Stage R is pure D3' at the adopted f.
  predict    T.C1: the preregistration `<prep>/prereg_<fp16>.json`.
  prereg-md  T.C2: `reports/H0_ddtest_prereg_<stamp>.md` from that JSON.
  assemble   T.D2 / T.F1: the analysis on a counts directory -> `validation/<out>.json` and the report.
"""
import argparse
import glob
import gzip
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gate_H0_kpilot as GK  # noqa: E402  (import only)

ROOT = GK.ROOT
PREP = os.path.join("data", "hardware", "H0_ddtest_prep")
PILOT_PREP = os.path.join("data", "hardware", "H0_kpilot_prep")
DEVICE = "ibm_kingston"
CELLS = ("T0", "T1", "T2", "T3")
CANDIDATES = ("T1", "T2", "T3")
BASE_IDS = ("B0_ref06_k1", "B1_ref07_k1")
# ---- preregistered constants (prompts/24 P5-P7; none of them tuned on data)
SHOTS = 6000
CAL_SHOTS_T = 6000
MAX_ESTIMATE_S = 30.0
MAX_USAGE_S = 40.0
RATIO_FLOOR = 1.25            # P7: R_i >= 1.25
RATIO_LO_BAR = 1.0            # P7: R_i,lo95 > 1
BAR_MEAN = 0.1                # the signed bar (amendment 01 / prompts/12), read only
Z95 = 1.959963984540054
BOOT_DRAWS, BOOT_SEED = 10000, 11
CONF68, CONF95 = GK.CONF68, GK.CONF95
# ---- the reserve (P1 and the QPU-seconds table)
RESERVE_FACTOR = 1.3
BILLED_FACTOR_INFO = 12.0 / 9.04      # the pilot's billed / estimate (information)
STAGE_T_BILLED_CAP = 40.0
STAGE_R_CAL_SHOTS = 4000             # D3_CAL_SHOTS
STAGE_R_CAL_CIRCUITS = 2             # the patch's all-0 / all-1 pubs
STAGE_R_MAX_PUBS = 14                # --max-pubs-per-job of R.E2
F_PILOT = None                       # read from validation/H0_kpilot.json at run time
P8_RULING = ("Coordinator ruling (2026-10-02) on planner decision P8: the D3''-H0 lift of the seven k = 1 circuits "
             "is STRUCK; Stage R is pure rule D3' at the adopted cell's f_pool, which is what the owner named "
             "(\"121 s\").  The planner's prompt file is not edited; the strike enters here (reserve, plan, tests).")
PLANNER_EXPECTATION = ("Planner expectation (prompts/24 P7, written before data): the signed bar will not be reached "
                       "(it needs R >~ 2.4); whether any cell qualifies is genuinely open -- the Aer null is R = 0.82-0.94 "
                       "and the ceiling is x4.3 (reports/ibm_decoherence_literature_20261002.md section 4).")
ADOPTION_RULE = ("A cell i in {T1, T2, T3} qualifies iff R_i,lo95 > 1 and R_i >= 1.25.  Among qualifying cells the one "
                 "with the largest point R_i is adopted for Stage R; if none qualifies, Stage R runs the baseline (T0).  "
                 "Signed bar on the adopted cell: GO iff f_adopted,lo95 >= 0.1, NO-GO iff f_adopted,hi95 < 0.1, "
                 "AMBIGUOUS otherwise (information for the owner; Stage R proceeds in every case under the owner's "
                 "decision).")
RATIO_RULE = ("R_i = f_i / f_0 = X_i / X_0 (pooled excess reference counts over the two k = 1 circuits: same shots, same "
              "p_ref, same readout factor); 95 % interval exp(ln R_i +- 1.96 sqrt(1/X_i + 1/X_0)) (Poisson on the "
              "excess counts, the garbage expectation subtracted as in the pilot); a parametric bootstrap (10 000 draws, "
              "seed 11) beside it as a cross-check, never as the verdict.")

p, rel, load_json, dump_json, now, git_commit, versions = (GK.p, GK.rel, GK.load_json, GK.dump_json, GK.now,
                                                          GK.git_commit, GK.versions)


def f_pilot():
    return float(load_json(p("validation", "H0_kpilot.json"))["data"]["decision"]["f_pool"])


# --------------------------------------------------------------------------- pure: the plan (tested)
def d3_shots(P, mans, f, ls, floor, margin, readout_factor, round_to):
    """Rule D3' per circuit (r = 1 only): N4 per sector for its k = 4 circuits, the floor
    elsewhere -- exactly `h0_device_survey.d3_budget`'s assignment, returned per circuit."""
    import h0_support_plan as sp
    f_by = {m["id"]: float(f) for m in mans}
    shots, n4 = {}, {}
    for sec in sorted({m["sector"] for m in mans}):
        sm = [m for m in mans if m["sector"] == sec]
        r1 = [m["id"] for m in sm]
        k4 = [m["id"] for m in sm if int(m["k"]) == 4]
        n4[sec] = sp.n4_of_sector({c: P[c] for c in r1}, f_by, r1, k4, floor, ls, margin=margin,
                                  readout_factor=readout_factor, round_to=round_to)
        for m in sm:
            shots[m["id"]] = n4[sec] if m["id"] in k4 else floor
    return shots, n4


def job_groups(shots_by_id, dur_by_id, rep, max_pubs):
    """`h0_submit.plan_groups` over (id, shots): [{shots, chunk, ids, execution_s}]."""
    from h0_submit import plan_groups
    jobs = [({"id": c}, int(s)) for c, s in sorted(shots_by_id.items())]
    out = []
    for sh, ci, chunk in plan_groups(jobs, max_pubs):
        ids = [m["id"] for m in chunk]
        ex = sum(sh * (float(dur_by_id[c]) + rep) for c in ids)
        out.append({"shots": int(sh), "chunk": int(ci), "n_pubs": len(ids), "ids": ids, "execution_s": float(ex)})
    return out


def reserve_of(groups, factor=RESERVE_FACTOR):
    total = float(sum(g["execution_s"] for g in groups))
    largest = max(groups, key=lambda g: g["execution_s"])
    return {"total_execution_s": total, "largest_job": {k: largest[k] for k in ("shots", "chunk", "n_pubs", "execution_s")},
            "reserve_s": factor * total + factor * float(largest["execution_s"]),
            "rule": "1.3 x total execution estimate + 1.3 x the largest job (retry margin), prompts/24 QPU-seconds table"}


def stage_r_plan(f, full_rec, mp, cal_T, rep, family_T=None):
    """Rule D3' (P8 lift struck) for the signed family's 28 circuits relabelled by `mp` at
    their own durations on `full_rec`, plus the two readout pubs at 4000 shots."""
    import gate_S2D_levers as G
    import h0_device_survey as ds
    from qiskit import qpy
    from skqd import idle
    from skqd.skqd import READOUT_FACTOR, poisson_lambda_star
    fam = load_json(p("data", "S2D_levers", "family.json"))["families"]["diag-hop0-hop1-hop2-hop3-plaq0_s2"]
    T, P, mans = {}, {}, []
    for c in fam["circuits"]:
        if family_T is not None:
            T[c["id"]] = float(family_T[c["id"]])
        else:
            with gzip.open(p(fam["qpy_dir"], c["id"] + ".qpy.gz"), "rb") as fh:
                tq = qpy.load(fh)[0]
            T[c["id"]] = float(idle.schedule_asap(G.relabelled(tq, mp), full_rec)["T_total_s"])
        P[c["id"]] = G.ideal_distribution(list(G.DEFAULT_ORDER), c["twoB"], c["reference"], c["theta"])["p_unnormalised"]
        mans.append({"id": c["id"], "sector": c["sector"], "repetitions": 1, "k": c["k"]})
    ls = poisson_lambda_star(ds.D3_K, ds.D3_CONF)
    shots, n4 = d3_shots(P, mans, f, ls, ds.D3_FLOOR, ds.D3_MARGIN, READOUT_FACTOR, ds.D3_ROUND)
    allshots = dict(shots)
    dur = dict(T)
    for i in range(STAGE_R_CAL_CIRCUITS):
        cid = ("cal_patch_all0", "cal_patch_all1")[i]
        allshots[cid] = STAGE_R_CAL_SHOTS
        dur[cid] = float(cal_T)
    groups = job_groups(allshots, dur, rep, STAGE_R_MAX_PUBS)
    res = reserve_of(groups)
    return {"f": float(f), "rule": "D3' (prompts/16), unchanged constants; P8's D3''-H0 lift struck",
            "lambda_star": ls, "margin": ds.D3_MARGIN, "floor": ds.D3_FLOOR, "round_to": ds.D3_ROUND,
            "N4": n4, "shots_by_circuit": shots, "total_coarse_shots": int(sum(shots.values())),
            "calibration_circuits": STAGE_R_CAL_CIRCUITS, "calibration_shots": STAGE_R_CAL_SHOTS,
            "calibration_duration_s": float(cal_T), "rep_delay_s": rep, "durations_s": T,
            "groups": groups, "n_jobs": len(groups), **res}


def stage_t_estimate(T_k1, cal_T, rep):
    """8 coarse pubs (2 circuits x 4 cells) + 2 readout pubs, all at 6000 shots."""
    coarse = sum(len(CELLS) * SHOTS * (float(T_k1[c]) + rep) for c in BASE_IDS)
    cal = 2 * CAL_SHOTS_T * (float(cal_T) + rep)
    return {"coarse_s": coarse, "calibration_s": cal, "total_execution_s": coarse + cal,
            "cap_estimator_s": MAX_ESTIMATE_S, "cap_billed_s": STAGE_T_BILLED_CAP,
            "expected_billed_s_information": (coarse + cal) * BILLED_FACTOR_INFO}


# --------------------------------------------------------------------------- pure: the decision (tested)
def ratio_interval(X_i, X_0, z=Z95):
    """(R, [lo, hi]) of the excess-count ratio, Poisson on the excess counts."""
    if X_i is None or X_0 is None or X_i <= 0 or X_0 <= 0:
        return (None if (X_0 is None or X_0 <= 0) else (X_i / X_0)), [None, None]
    R = X_i / X_0
    s = math.sqrt(1.0 / X_i + 1.0 / X_0)
    return R, [math.exp(math.log(R) - z * s), math.exp(math.log(R) + z * s)]


def qualifies(R, R95):
    return bool(R is not None and R95 and R95[0] is not None and R95[0] > RATIO_LO_BAR and R >= RATIO_FLOOR)


def adopt(cells):
    """`cells` = {cell: {"R": R, "R_95": [lo, hi]}} for T1-T3 -> (adopted cell, qualifying list)."""
    q = [c for c in CANDIDATES if c in cells and qualifies(cells[c]["R"], cells[c]["R_95"])]
    if not q:
        return "T0", q
    return max(q, key=lambda c: cells[c]["R"]), q


def signed_bar(f95, bar=BAR_MEAN):
    lo, hi = float(f95[0]), float(f95[1])
    if lo >= bar:
        return "GO"
    if hi < bar:
        return "NO-GO"
    return "AMBIGUOUS"


def bootstrap_ratio(rows_i, rows_0, draws=BOOT_DRAWS, seed=BOOT_SEED):
    """Parametric bootstrap of X_i / X_0: every circuit's reference count ~ Poisson(observed)."""
    rng = np.random.default_rng(seed)
    exp_i = sum(float(r[1]) * float(r[3]) / float(r[4]) for r in rows_i)
    exp_0 = sum(float(r[1]) * float(r[3]) / float(r[4]) for r in rows_0)
    ni = sum(rng.poisson(float(r[0]), draws) for r in rows_i)
    n0 = sum(rng.poisson(float(r[0]), draws) for r in rows_0)
    Xi, X0 = ni - exp_i, n0 - exp_0
    ok = (X0 > 0)
    R = Xi[ok] / X0[ok]
    if R.size == 0:
        return {"draws": draws, "seed": seed, "R_95": [None, None], "failed": int(draws)}
    return {"draws": draws, "seed": seed, "failed": int(draws - R.size),
            "R_95": [float(np.percentile(R, 2.5)), float(np.percentile(R, 97.5))],
            "median": float(np.median(R))}


DECISION_FIELDS = ("cells", "adopted", "qualifying", "signed_bar", "f_adopted", "f_adopted_95", "usage_s", "dry_run")
CELL_FIELDS = ("f_pool", "f_pool_68", "f_pool_95", "f_by_circuit", "excess_hits", "R", "R_95", "R_bootstrap_95",
               "null_ratio", "qualifies")


def decision_complete(dec):
    miss = []
    for k in DECISION_FIELDS:
        if k not in dec or (dec[k] is None and not (k == "usage_s" and dec.get("dry_run"))):
            miss.append(k)
    for c, v in (dec.get("cells") or {}).items():
        for k in CELL_FIELDS:
            if c == "T0" and k in ("R_95", "R_bootstrap_95", "qualifies"):
                continue
            if k not in v or v[k] is None:
                miss.append(f"{c}.{k}")
    return miss


# --------------------------------------------------------------------------- T.A3 reserve
def stage_reserve(args):
    from skqd import idle
    t0 = time.time()
    prep = args.prep
    info = load_json(p(prep, "live.json"))
    full = load_json(info["record"]["path"])
    acct_files = sorted(glob.glob(p(prep, "account_check_*.json")))
    if not acct_files:
        raise SystemExit("no account check in the prep directory: run h0_ddtest_circuits.py --stage account")
    acct = load_json(acct_files[-1])
    remaining = float((acct.get("usage") or {}).get("usage_remaining_seconds"))
    psel = load_json(p(PILOT_PREP, "select.json"))
    mp = {int(k): int(v) for k, v in psel["winner_mapping"].items()}
    from gate_H0P import load_circuit, load_manifests
    _m, pcals = load_manifests(p(PILOT_PREP))
    cal_T = float(np.mean([idle.schedule_asap(load_circuit(p(PILOT_PREP), c), full)["T_total_s"] for c in pcals]))
    rep = float(full.get("default_rep_delay_s") or 250e-6)
    f0 = f_pilot()
    plan = stage_r_plan(f0, full, mp, cal_T, rep)
    T_k1 = {c: plan["durations_s"][c] for c in BASE_IDS}
    st = stage_t_estimate(T_k1, cal_T, rep)
    # cross-check: the pilot's own function at the pilot's f on the day's record (14 cal circuits, H0_prep's)
    bud = GK.budgets_at(f0, PILOT_PREP, full, mp)
    pilot_bud = load_json(p("validation", "H0_kpilot.json"))["data"]["budgets_at_f_pool"]
    committed = STAGE_T_BILLED_CAP + plan["reserve_s"]
    out = {"stage": "reserve", "created": now(), "commit": git_commit(), "qpu_seconds": 0,
           "script": "scripts/gate_H0_ddtest.py --stage reserve",
           "p8_ruling": P8_RULING,
           "record": {"path": info["record"]["path"], "fingerprint": full["fingerprint"],
                      "last_update_date": full["last_update_date"]},
           "account_check": rel(acct_files[-1]), "remaining_s_at_check": remaining,
           "f_sizing": f0, "f_sizing_source": "validation/H0_kpilot.json data.decision.f_pool",
           "patch_mapping": "the pilot's (data/hardware/H0_kpilot_prep/select.json winner_mapping)",
           "stage_R_plan": plan,
           "stage_T_estimate": st,
           "budgets_at_cross_check": {"function": "gate_H0_kpilot.budgets_at (14 readout circuits of H0_prep at 4000)",
                                      "day": bud, "pilot_validation": pilot_bud,
                                      "N4_reproduced": bud.get("D3prime_N4") == pilot_bud.get("D3prime_N4")},
           "committed_before_stage_T_s": committed,
           "fits": committed <= remaining,
           "stop_rule": "STOP if 40 + reserve > remaining (prompts/24 T.A3)",
           "runtime_s": time.time() - t0}
    dump_json(out, p(prep, "reserve.json"))
    print("| item | execution estimate (s) | reserve / cap (s) |")
    print("|---|---|---|")
    print(f"| remaining at start ({rel(acct_files[-1])}) | - | {remaining:.0f} |")
    print(f"| Stage T: 8 coarse pubs x {SHOTS} | {st['coarse_s']:.2f} | - |")
    print(f"| Stage T: 2 cal pubs x {CAL_SHOTS_T} | {st['calibration_s']:.2f} | - |")
    print(f"| Stage T total | {st['total_execution_s']:.2f} (billed ~{st['expected_billed_s_information']:.1f}) | "
          f"estimator {MAX_ESTIMATE_S:.0f}, billed {STAGE_T_BILLED_CAP:.0f} |")
    for g in plan["groups"]:
        print(f"| Stage R job: {g['n_pubs']} pubs x {g['shots']} (chunk {g['chunk']}) | {g['execution_s']:.2f} | - |")
    print(f"| Stage R total at f = {f0:.4f} (D3', P8 lift struck) | {plan['total_execution_s']:.2f} | - |")
    print(f"| Stage R reserve = 1.3 x total + 1.3 x largest ({plan['largest_job']['execution_s']:.2f}) | - | "
          f"{plan['reserve_s']:.1f} |")
    print(f"| committed before Stage T submits | - | {committed:.1f} <= {remaining:.0f}: {committed <= remaining} |")
    print(f"N4 {plan['N4']}, coarse shots {plan['total_coarse_shots']}; budgets_at cross-check N4 {bud.get('D3prime_N4')} "
          f"(pilot {pilot_bud.get('D3prime_N4')}), execution {bud.get('D3prime_execution_s'):.2f} s with 14 cal circuits")
    if committed > remaining:
        print(f"STOP: 40 + reserve = {committed:.1f} s > remaining {remaining:.0f} s")
        return 3
    if st["total_execution_s"] > MAX_ESTIMATE_S:
        print(f"STOP: the Stage T estimate {st['total_execution_s']:.1f} s > {MAX_ESTIMATE_S:.0f} s")
        return 3
    return 0


# --------------------------------------------------------------------------- T.C1 predict
def prep_manifests(prep):
    return GK.prep_manifests(prep)


def patch_record(prep):
    return GK.patch_record(prep)


def stage_predict(args):
    import h0_qpu_time as qt
    from gate_H0P import DIAG_MIN
    from h0_backends import fresh_calibration, frozen_qubits_and_edges, resolve_backend
    from skqd.skqd import READOUT_FACTOR
    t0 = time.time()
    prep = args.prep
    rec, prinfo, info = patch_record(prep)
    index = load_json(p(prep, "index.json"))
    sel = load_json(p(prep, "select.json"))
    reserve = load_json(p(prep, "reserve.json"))
    mans = prep_manifests(prep)
    patch = index["patch"]
    b = resolve_backend(DEVICE)
    qubits, edges = frozen_qubits_and_edges(p(prep))
    live = fresh_calibration(b, qubits, edges)
    if live["fingerprint"] != rec["fingerprint"]:
        print(f"STOP (D10): the live patch fingerprint {live['fingerprint'][:16]} is not the patch record's "
              f"{rec['fingerprint'][:16]} -- re-run record-patchcal on the new content")
        return 3
    est = qt.estimate(p(prep), b, {}, CAL_SHOTS_T, shots_default=SHOTS)
    f0 = f_pilot()
    cells = {}
    for cell in CELLS:
        per = {}
        for cid in BASE_IDS:
            m = mans[f"{cid}_{cell}"]
            dd = m["dd"]
            a = GK.decode_counts  # noqa (decoder used at assembly)
            n_exp_clean = SHOTS * READOUT_FACTOR * f0 * m["p_reference"]
            import gate_S2D_levers as G
            ag = G.garbage_acceptance(m["twoB"])
            per[cid] = {"id": m["id"], "n_pulses": dd["n_pulses"], "pulse_cost_nats": dd["pulse_cost_nats"],
                        "null_ratio": dd["null_ratio"], "pulses_per_physical_qubit": dd["pulses_per_physical_qubit"],
                        "qpy_gz_sha256": m["qpy_gz_sha256"], "scheduled_duration_s": m["scheduled_duration_s"],
                        "p_reference": m["p_reference"], "garbage_acceptance": ag, "dim": m["dim"],
                        "expected_reference_hits_at_f_pilot": n_exp_clean,
                        "expected_reference_hits_from_garbage": SHOTS * ag / m["dim"],
                        "expected_reference_hits_at_f_pilot_x_null": n_exp_clean * dd["null_ratio"]}
        X = sum(v["expected_reference_hits_at_f_pilot_x_null"] for v in per.values())
        cells[cell] = {"description": mans[f"{BASE_IDS[0]}_{cell}"]["dd"]["description"],
                       "pass": mans[f"{BASE_IDS[0]}_{cell}"]["dd"]["pass"],
                       "parameters": mans[f"{BASE_IDS[0]}_{cell}"]["dd"]["parameters"],
                       "per_circuit": per,
                       "null_ratio_pooled": (sum(v["expected_reference_hits_at_f_pilot_x_null"] for v in per.values())
                                             / sum(v["expected_reference_hits_at_f_pilot"] for v in per.values())),
                       "expected_excess_hits_at_f_pilot_x_null": X}
    X0 = sum(v["expected_reference_hits_at_f_pilot"] for v in cells["T0"]["per_circuit"].values())
    s_lnR = math.sqrt(2.0 / X0)
    power = {"X_per_cell_at_f_pilot": X0, "sigma_lnR": s_lnR,
             "factor_95": [math.exp(-Z95 * s_lnR), math.exp(Z95 * s_lnR)],
             "lower_bound_of_a_true_1.25": RATIO_FLOOR * math.exp(-Z95 * s_lnR),
             "decidable_at_1.25": RATIO_FLOOR * math.exp(-Z95 * s_lnR) > 1.0,
             "note": "P5 arithmetic reproduced: X = sum_c 6000 x 0.82 x f_pilot x p_ref,c; sigma_lnR = sqrt(1/X + 1/X)"}
    pubs = [{"id": m["id"], "kind": m["kind"], "cell": (m.get("dd") or {}).get("cell"),
             "shots": SHOTS if m["kind"] == "coarse_step" else CAL_SHOTS_T}
            for m in sorted(mans.values(), key=lambda m: m["id"])]
    fp16 = rec["fingerprint"][:16]
    kp = load_json(p("validation", "H0_kpilot.json"))["data"]
    pre = {
        "gate": "H0_ddtest", "script": "scripts/gate_H0_ddtest.py --stage predict",
        "created": now(), "commit": git_commit(), "versions": versions(), "qpu_seconds": 0,
        "prep": prep, "prep_created": index["created"],
        "calibration": {"backend": DEVICE, "fingerprint": rec["fingerprint"], "path": prinfo["path"],
                        "last_update_date": rec["last_update_date"], "stamp": rec["stamp"],
                        "full_record_path": info["record"]["path"],
                        "full_record_fingerprint": info["record"]["fingerprint"],
                        "live_fingerprint_at_predict": live["fingerprint"],
                        "live_match_at_predict": live["fingerprint"] == rec["fingerprint"]},
        "patch": patch,
        "selection": {"rule": sel["rule"], "winner_mapping": sel["winner_mapping"],
                      "mapping_reproduced": sel["mapping_reproduced"],
                      "pilot_mapping_reproduced": sel.get("pilot_mapping_reproduced"),
                      "n_embeddings": sel["n_embeddings"], "n_scored": sel["n_scored"],
                      "winner_f_dd_off": sel["winner"]["f_dd_off"]},
        "pubs": pubs, "shots_per_pub": SHOTS, "total_shots": sum(x["shots"] for x in pubs),
        "sampler_options": "--dd off --twirling off (runtime DD off: the pulses are in the circuits); raw bit strings",
        "execution_estimate": {"total_execution_s": est["total_execution_s"], "total_shots": est["total_shots"],
                               "rep_delay_s": est["rep_delay_s"], "groups": est["groups"],
                               "per_circuit": est["per_circuit"], "last_update_date": est["last_update_date"],
                               "cap_s": MAX_ESTIMATE_S, "within_cap": est["total_execution_s"] <= MAX_ESTIMATE_S,
                               "billed_cap_s": MAX_USAGE_S},
        "cells": cells, "f_pilot": f0, "f_pilot_95": kp["decision"]["f_pool_95"],
        "f_pilot_source": "validation/H0_kpilot.json data.decision",
        "power": power,
        "baseline_prediction_of_record": {"source": "validation/H0_kpilot.json data.aer_at (the pilot's Aer grid)",
                                          "aer_at": kp.get("aer_at"),
                                          "note": "no new Aer prediction cells (P10): Aer cannot show a DD gain"},
        "decision_rule": {"adoption": ADOPTION_RULE, "ratio": RATIO_RULE,
                          "thresholds": {"R_lo95_greater_than": RATIO_LO_BAR, "R_at_least": RATIO_FLOOR,
                                         "signed_bar": BAR_MEAN},
                          "statistic": "pooled_reference_string_test over each cell's two k = 1 circuits, Garwood 68 % / 95 %",
                          "family_wise_false_positive": ("three candidates at 2.5 % one-sided each: at most 7.5 % "
                                                         "before the 1.25 floor (planner arithmetic)")},
        "reserve": {"path": rel(p(prep, "reserve.json")), "reserve_s": reserve["stage_R_plan"]["reserve_s"],
                    "stage_R_total_execution_s": reserve["stage_R_plan"]["total_execution_s"],
                    "remaining_s_at_check": reserve["remaining_s_at_check"],
                    "committed_before_stage_T_s": reserve["committed_before_stage_T_s"], "fits": reserve["fits"],
                    "p8_ruling": P8_RULING},
        "coarse_circuits": {m["id"]: {k: m.get(k) for k in ("sector", "reference", "k", "theta", "cz", "n_delays",
                                                            "T_s", "T_total_s", "scheduled_duration_s", "p_reference",
                                                            "exactness", "placement", "qpy_gz_sha256", "reuse")}
                            for m in mans.values() if m["kind"] == "coarse_step"},
        "planner_expectation": PLANNER_EXPECTATION,
        "runtime_s": time.time() - t0,
    }
    pre["readout_expected_live"] = GK.readout_expected_live(rec, patch)
    path = p(prep, f"prereg_{fp16}.json")
    if os.path.exists(path):
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel(path)], cwd=ROOT,
                                 capture_output=True).returncode == 0
        if tracked:
            raise SystemExit(f"{rel(path)} is committed as the preregistration: refusing to overwrite")
    if pre["readout_expected_live"]["min"] < DIAG_MIN:
        print(f"STOP: the live readout expectation {pre['readout_expected_live']['min']:.4f} < DIAG_MIN {DIAG_MIN}")
        return 3
    dump_json(pre, path)
    print(f"wrote {rel(path)}: estimate {est['total_execution_s']:.2f} s over {est['total_shots']} shots (cap "
          f"{MAX_ESTIMATE_S:.0f}); reserve {reserve['stage_R_plan']['reserve_s']:.1f} s; X per cell at f_pilot {X0:.0f}, "
          f"sigma_lnR {s_lnR:.3f}; nulls " + ", ".join(f"{c} {cells[c]['null_ratio_pooled']:.3f}" for c in CELLS))
    if est["total_execution_s"] > MAX_ESTIMATE_S:
        print(f"STOP: the execution estimate {est['total_execution_s']:.1f} s exceeds {MAX_ESTIMATE_S:.0f} s")
        return 3
    return 0


def _f(x, spec="{:.4f}"):
    return "n/a" if x is None else spec.format(x)


def _iv(iv, spec="{:.4f}"):
    if not iv or iv[0] is None:
        return "n/a"
    return "[" + spec.format(iv[0]) + ", " + spec.format(iv[1]) + "]"


def stage_prereg_md(args):
    from skqd.report import md_table, write_report
    path = args.prereg or sorted(glob.glob(p(args.prep, "prereg_*.json")))[-1]
    pre = load_json(path)
    est = pre["execution_estimate"]
    cal = pre["calibration"]
    res = pre["reserve"]
    rows = []
    for c, v in pre["cells"].items():
        for cid, x in v["per_circuit"].items():
            rows.append([c, x["id"], x["n_pulses"], f"{x['pulse_cost_nats']:.4f}", f"{x['null_ratio']:.3f}",
                         f"{x['scheduled_duration_s'] * 1e6:.3f}", f"{x['p_reference']:.4f}",
                         f"{x['expected_reference_hits_at_f_pilot']:.0f}", f"{x['expected_reference_hits_from_garbage']:.2f}"])
    pubs = [[x["id"], x["kind"], x.get("cell") or "", x["shots"]] for x in pre["pubs"]]
    pw = pre["power"]
    rsv = load_json(res["path"])
    grows = [[g["n_pubs"], g["shots"], g["chunk"], f"{g['execution_s']:.2f}"] for g in rsv["stage_R_plan"]["groups"]]
    txt = f"""# H0_ddtest preregistration -- ibm_kingston, calibration `{cal['fingerprint'][:16]}`

Generated by `scripts/gate_H0_ddtest.py --stage prereg-md` from `{rel(path) if os.path.isabs(path) else path}`
(written {pre['created']} at commit `{pre['commit']}`).  Every number below is read from that JSON.  Nothing was
submitted when this was written; the commit that adds this file is what criterion K1 checks against the submission time.
Prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage T).

## Calibration and patch

- Patch record `{cal['path']}`: fingerprint `{cal['fingerprint']}`, last update {cal['last_update_date']} (full-device
  record `{cal['full_record_path']}`, `{cal['full_record_fingerprint'][:16]}`); live content at the prediction identical:
  {cal['live_match_at_predict']}.
- Patch (rule R1'-pilot, run once on the day's record): {pre['patch']}; the S2D_levers `L1_seed_alap` mapping reproduced:
  {pre['selection']['mapping_reproduced']}; the pilot's mapping reproduced: {pre['selection']['pilot_mapping_reproduced']}
  ({pre['selection']['n_scored']} of {pre['selection']['n_embeddings']} embeddings scored; winner PTA f (DD off, echo T2)
  {pre['selection']['winner_f_dd_off']:.4f}).

## Pubs, shots, execution estimate

{md_table(["pub", "kind", "cell", "shots"], pubs)}

{pre['total_shots']} shots in one job; execution estimate **{est['total_execution_s']:.2f} s** (estimator cap {est['cap_s']:.0f} s,
within: {est['within_cap']}; billed cap {est['billed_cap_s']:.0f} s; rep delay {est['rep_delay_s'] * 1e6:.0f} us).  Options:
{pre['sampler_options']}.

## The four cells (P4, parameters fixed before data)

{md_table(["cell", "circuit", "pulses", "S_DD (nats)", "null ratio", "duration (us)", "p_ref",
           "expected ref hits at f_pilot", "garbage expectation"], rows)}

Cells: """ + "; ".join(f"**{c}** {v['description']} -- `{v['pass']}` {json.dumps(v['parameters'])}" for c, v in pre["cells"].items()) + f"""

Pooled null ratios: """ + ", ".join(f"{c} {v['null_ratio_pooled']:.3f}" for c, v in pre["cells"].items()) + f""".

## Power (P5 arithmetic, reproduced on this record)

f_pilot = {pre['f_pilot']:.4f} (95 % {_iv(pre['f_pilot_95'])}, {pre['f_pilot_source']}); expected excess reference
hits per cell X = {pw['X_per_cell_at_f_pilot']:.0f}; sigma(ln R) = {pw['sigma_lnR']:.4f}; 95 % factor {_iv(pw['factor_95'], '{:.3f}')};
lower 95 % bound of a true R = 1.25: {pw['lower_bound_of_a_true_1.25']:.3f} (decidable: {pw['decidable_at_1.25']}).

## Decision rule (verbatim)

- {pre['decision_rule']['adoption']}
- {pre['decision_rule']['ratio']}
- Statistic: {pre['decision_rule']['statistic']}.  Family-wise: {pre['decision_rule']['family_wise_false_positive']}.
- Prediction of record for the baseline cell: {pre['baseline_prediction_of_record']['source']} ({pre['baseline_prediction_of_record']['note']}).
- {pre['planner_expectation']}

## Stage R reserve (P1; computed before Stage T spends)

{res['p8_ruling']}

{md_table(["Stage R job: pubs", "shots", "chunk", "execution (s)"], grows)}

Stage R total {res['stage_R_total_execution_s']:.2f} s; reserve {res['reserve_s']:.1f} s; committed before Stage T submits
40 + reserve = {res['committed_before_stage_T_s']:.1f} s of {res['remaining_s_at_check']:.0f} s remaining: fits {res['fits']}.
"""
    out = write_report(f"H0_ddtest_prereg_{cal['stamp']}.md", txt)
    print(f"wrote {rel(out)}")
    return 0


# --------------------------------------------------------------------------- assemble
def stage_assemble(args):
    import gate_S2D_levers as G
    from gate_H0 import codeword_roundtrip, read_counts_dir
    from gate_H0_diag import readout_reference
    from gate_H0P import DIAG_MIN
    from h0_backends import calibration_diff
    from skqd.codec import Codec
    from skqd.report import GateResult, write_report
    from skqd.skqd import pooled_reference_string_test
    t0 = time.time()
    dry = bool(args.dry_run)
    out = args.out or ("H0_ddtest_dryrun" if dry else "H0_ddtest")
    prep = args.prep
    pre_path = args.prereg or GK.find_prereg(prep)
    pre = load_json(pre_path)
    missing_keys = GK.prereg_keys_ok(pre)
    mans = prep_manifests(prep)
    index = load_json(p(prep, "index.json"))
    patch = index["patch"]
    cdir = p(args.counts) if not os.path.isabs(args.counts) else args.counts
    records = read_counts_dir(cdir)
    spath = os.path.join(os.path.dirname(os.path.normpath(cdir)), "session.json")
    session = load_json(spath) if os.path.exists(spath) else None
    GK.check_mixing(dry, session, records)
    by_id = {m["id"]: (m, c) for m, c in records}
    prereg_rec = load_json(pre["calibration"]["path"])
    fx = G.factory()
    codec = Codec(fx["M"].basis)
    n = codec.n_qubits

    # ---- readout (K3)
    ro = readout_reference({"records": records}, n)
    ro_survival = float(np.prod([1.0 - e for e in ro["measured_error"]])) if ro else None
    ro_live = GK.readout_expected_live(prereg_rec, patch)
    cal_phys = mans["cal_patch_all0"]["logical_to_physical"]
    dry_k3_block = None
    if dry and ro:
        exp_model = GK.snapshot_readout_model(index["common"]["backend"], cal_phys)
        meas = {int(q): (ro["P_measure_0_given_0"][i], ro["P_measure_1_given_1"][i]) for i, q in enumerate(cal_phys)}
        shots_cal = int(sum(by_id["cal_patch_all0"][1].values()))
        k3_ok, k3_rows = GK.dry_k3(meas, exp_model, shots_cal)
        dry_k3_block = {"ok": k3_ok, "per_qubit": k3_rows, "shots": shots_cal, "sigma_k": 3.0,
                        "model": f"NoiseModel.from_backend({index['common']['backend']}) local readout errors",
                        "ruling": "prompts/21a option (a): the dry-run K3 form"}

    # ---- the cells
    coarse_ids = [f"{b}_{c}" for c in CELLS for b in BASE_IDS]
    circ = {cid: GK.decode_counts([by_id[cid][1]], mans[cid]) for cid in coarse_ids}
    rt = codeword_roundtrip([(mans[cid], by_id[cid][1]) for cid in coarse_ids], codec)
    cells = {}
    for c in CELLS:
        rows = [circ[f"{b}_{c}"]["row"] for b in BASE_IDS]
        p68 = pooled_reference_string_test(rows, conf=CONF68)
        p95 = pooled_reference_string_test(rows, conf=CONF95)
        nulls = [mans[f"{b}_{c}"]["dd"]["null_ratio"] for b in BASE_IDS]
        ws = [mans[f"{b}_{c}"]["p_reference"] for b in BASE_IDS]
        cells[c] = {"f_pool": p68["f_clean"], "f_pool_68": p68["f_clean_68"], "f_pool_95": p95["f_clean_68"],
                    "n_reference": p68["n_reference"], "expected_from_garbage": p68["expected_from_garbage"],
                    "excess_hits": p68["excess"], "rows": rows,
                    "f_by_circuit": {b: {"reference": circ[f"{b}_{c}"]["f_clean_reference"],
                                         "reference_68": circ[f"{b}_{c}"]["f_clean_reference_68"],
                                         "reference_95": circ[f"{b}_{c}"]["f_clean_reference_95"],
                                         "mixture": circ[f"{b}_{c}"]["f_clean_mixture"],
                                         "mixture_68": circ[f"{b}_{c}"]["f_clean_mixture_68"]} for b in BASE_IDS},
                    "null_ratio": float(np.dot(nulls, ws) / np.sum(ws)),
                    "null_ratio_per_circuit": dict(zip(BASE_IDS, nulls)),
                    "n_pulses_per_circuit": {b: mans[f"{b}_{c}"]["dd"]["n_pulses"] for b in BASE_IDS},
                    "pulse_cost_nats_per_circuit": {b: mans[f"{b}_{c}"]["dd"]["pulse_cost_nats"] for b in BASE_IDS},
                    "c6_relative_deviation_information": {b: circ[f"{b}_{c}"]["c6_relative_deviation"] for b in BASE_IDS},
                    "distance_histograms": {b: circ[f"{b}_{c}"]["distance_histogram"] for b in BASE_IDS},
                    "accepted": {b: circ[f"{b}_{c}"]["accepted"] for b in BASE_IDS},
                    "reference_hits": {b: circ[f"{b}_{c}"]["reference_hits"] for b in BASE_IDS}}
    X0 = cells["T0"]["excess_hits"]
    cells["T0"].update({"R": 1.0, "R_95": None, "R_bootstrap_95": None, "qualifies": None})
    for c in CANDIDATES:
        R, R95 = ratio_interval(cells[c]["excess_hits"], X0)
        boot = bootstrap_ratio(cells[c]["rows"], cells["T0"]["rows"])
        cells[c].update({"R": R, "R_95": R95, "R_bootstrap_95": boot["R_95"], "R_bootstrap": boot,
                         "R_over_null": (None if R is None else R / cells[c]["null_ratio"]),
                         "qualifies": qualifies(R, R95)})
    adopted, qual = adopt(cells)
    bar = signed_bar(cells[adopted]["f_pool_95"])

    # ---- live block
    usage_s, job_ids, statuses = None, [], []
    if session:
        jobs = [j for j in session.get("jobs", []) if j.get("job_id")]
        job_ids = [j["job_id"] for j in jobs]
        statuses = [j.get("status") for j in jobs]
        us = [j.get("usage_s") for j in jobs if j.get("usage_s") is not None]
        usage_s = float(sum(us)) if us else None
    ret_fp = (session or {}).get("retrieval_calibration_fingerprint")
    ret_diff = None
    if ret_fp and ret_fp != pre["calibration"]["fingerprint"] and (session or {}).get("retrieval_calibration_file"):
        d = calibration_diff(prereg_rec, load_json(session["retrieval_calibration_file"]))
        ret_diff = {k: d[k] for k in ("n_leaves", "families", "max_ratio", "min_ratio")}
    acct = {}
    for lab, pat in (("before", p(prep, "account_check_*.json")),
                     ("after", p(os.path.dirname(os.path.normpath(cdir)), "account_check_after_*.json"))):
        fs = sorted(glob.glob(pat))
        if fs:
            a = load_json(fs[-1])
            acct[lab] = {"file": rel(fs[-1]), "usage": a.get("usage"), "backend": a.get("backend")}

    # ---- the Stage R reserve at the adopted f (P1)
    reserve = load_json(p(prep, "reserve.json"))
    f_ad = cells[adopted]["f_pool"]
    rplan = None
    if f_ad is not None and f_ad > 0:
        full = load_json(pre["calibration"]["full_record_path"])
        sel = load_json(p(prep, "select.json"))
        mp = {int(k): int(v) for k, v in sel["winner_mapping"].items()}
        cal_T = reserve["stage_R_plan"]["calibration_duration_s"]
        rplan = stage_r_plan(f_ad, full, mp, cal_T, reserve["stage_R_plan"]["rep_delay_s"])
        rplan.pop("durations_s", None)
    rem_after = ((acct.get("after") or {}).get("usage") or {}).get("usage_remaining_seconds")
    rem_now = (float(rem_after) if rem_after is not None else
               float(reserve["remaining_s_at_check"]) - (usage_s or 0.0))
    r_fits = None if rplan is None else rplan["reserve_s"] <= rem_now

    dec = {"dry_run": dry, "cells": {c: {k: v for k, v in cells[c].items() if k != "rows"} for c in CELLS},
           "adopted": adopted, "qualifying": qual, "signed_bar": bar,
           "f_adopted": cells[adopted]["f_pool"], "f_adopted_68": cells[adopted]["f_pool_68"],
           "f_adopted_95": cells[adopted]["f_pool_95"], "usage_s": usage_s,
           "stage_R_reserve_at_adopted_f": rplan, "remaining_s_after_stage_T": rem_now,
           "stage_R_reserve_fits": r_fits}

    # ---- criteria
    R_ = GateResult(out, ("one-job A/B test of client-side DD (context-aware, XY4, XY4-long) against the no-DD baseline "
                          "on the pilot's two k = 1 circuits; adoption by the preregistered ratio rule (measurement gate)")
                    + (" -- DRY RUN" if dry else ""))
    k1_info = {}
    n_coarse = len(coarse_ids)
    if dry:
        R_.add("K1 preregistration before data", "n/a (dry run)", "device run only", True)
        R_.add("K2 one job DONE, usage <= 40 s, estimate <= 30 s, 10 x 6000 counts, DD/twirling off, reserve present",
               "n/a (dry run)", "device run only", True)
    else:
        sub = (session.get("jobs") or [{}])[0].get("submitted")
        h, tc = GK.git_commit_time(pre["commit"])
        ha, ta = GK.git_added(pre_path)
        fp_ok = (session.get("prereg_calibration_fingerprint") == pre["calibration"]["fingerprint"]
                 == session.get("calibration_fingerprint"))
        before = (tc is not None and sub is not None and GK._utc(tc) < GK._utc(sub)
                  and ta is not None and GK._utc(ta) < GK._utc(sub))
        k1_info = {"prereg_commit": pre["commit"], "prereg_commit_full": h, "prereg_commit_time": tc,
                   "prereg_added_in": ha, "prereg_added_time": ta, "submitted": sub, "fingerprints_equal": fp_ok,
                   "retrieval_fingerprint": ret_fp,
                   "retrieval_match": (None if ret_fp is None else ret_fp == pre["calibration"]["fingerprint"]),
                   "retrieval_diff": ret_diff}
        R_.add("K1 preregistration committed before the submission; prereg = session = submission fingerprint; "
               "retrieval fingerprint recorded (a move is information)",
               f"prereg commit {tc}, added {ha and ha[:7]} {ta}, submitted {sub}; fingerprints equal {fp_ok}; "
               f"retrieval match {k1_info['retrieval_match']}",
               "commit < submission, equal fingerprints, retrieval recorded",
               before and fp_ok and ret_fp is not None and not missing_keys)
        est = ((session.get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s")
        so = session.get("sampler_options") or {}
        opts_ok = (so.get("dynamical_decoupling") == {"enable": False}
                   and so.get("twirling") == {"enable_gates": False, "enable_measure": False})
        shots_ok = len(records) == n_coarse + 2 and all(int(sum(c.values())) == SHOTS for _m, c in records)
        res_ok = (reserve.get("fits") is True and
                  STAGE_T_BILLED_CAP + reserve["stage_R_plan"]["reserve_s"] <= reserve["remaining_s_at_check"])
        k2 = (len(job_ids) == 1 and statuses == ["DONE"] and usage_s is not None and usage_s <= MAX_USAGE_S
              and est is not None and est <= MAX_ESTIMATE_S and shots_ok and opts_ok and res_ok)
        R_.add("K2 one job DONE, usage_s <= 40, preflight estimate <= 30 s, 10 counts files x 6000 shots, DD off and "
               "twirling off, the reserve of T.A3 present with 40 + reserve <= remaining at start",
               f"jobs {job_ids} {statuses}, usage {usage_s} s, estimate {_f(est, '{:.2f}')} s, counts ok {shots_ok}, "
               f"options off {opts_ok}, reserve {reserve['stage_R_plan']['reserve_s']:.1f} s (+40 vs "
               f"{reserve['remaining_s_at_check']:.0f}) {res_ok}", "all hold", k2)
    if dry:
        nz = sum(1 for v in (dry_k3_block or {}).get("per_qubit", {}).values()
                 if abs(v["d00"]["z"]) <= 3 and abs(v["d11"]["z"]) <= 3)
        R_.add("K3 readout (dry run: agreement with the snapshot's readout model, prompts/21a; the device criterion "
               ">= 0.9 is evaluated only on device counts)",
               f"{nz}/12 qubits with |z| <= 3; min diagonal {_f(None if not ro else ro['min_diagonal'])} (information); "
               f"live expectation min {ro_live['min']:.4f} (qubit {ro_live['min_qubit']})",
               f"all 12 within 3 binomial sigma; live expectation >= {DIAG_MIN}",
               bool(dry_k3_block and dry_k3_block["ok"]) and nz == len(patch) and ro_live["min"] >= DIAG_MIN)
    else:
        R_.add("K3 readout confusion of the patch (all-0 / all-1 pubs): smallest diagonal",
               None if not ro else round(ro["min_diagonal"], 4), f">= {DIAG_MIN}",
               bool(ro) and GK.device_k3(ro["min_diagonal"]))
    R_.add("K4 decoder round trip over every accepted string of the 8 coarse pubs",
           f"{rt['mismatches']} mismatches over {rt['distinct_accepted_strings']} strings", "0", rt["mismatches"] == 0)
    k5_rows = {}
    for cid in coarse_ids:
        m = mans[cid]
        ex = m["exactness"]
        chk = (m["dd"].get("checks") or {})
        ok = (ex["ok"] and ex["max_abs_delta"] < 1e-10 and ex["leakage"] < 1e-9
              and (m.get("schedule_info") or {}).get("method") == "alap"
              and m["dd"].get("pulse_cost_nats") is not None and m["dd"].get("null_ratio") is not None
              and set(m["ops"]) <= {"rz", "sx", "x", "cz", "delay", "measure", "barrier"})
        if m["dd"]["cell"] != "T0":
            ok = ok and chk.get("ok") is True and chk.get("statevector_max_abs_delta_up_to_phase", 1) < 1e-10 \
                and chk.get("duration_ok") is True and chk.get("windows_ok") is True and chk.get("ops") == m["ops"]
        k5_rows[cid] = ok
    R_.add("K5 circuits: exactness at build (< 1e-10, leakage < 1e-9), DD statevector = base to 1e-10, duration equal "
           "to 1 dt, no pulses in leading / trailing windows, basis = kingston's, op multisets as recorded, S_DD and "
           "null ratio present, ALAP scheduling asserted",
           f"{sum(k5_rows.values())}/{len(k5_rows)} circuits; max |d| "
           f"{max(mans[c]['exactness']['max_abs_delta'] for c in coarse_ids):.1e}", "all hold", all(k5_rows.values()))
    if dry:
        R_.add("K6 dry-run gate PASS", "n/a (this is the dry run)", "device run only", True)
    else:
        dp = p("validation", "H0_ddtest_dryrun.json")
        dg = load_json(dp)["status"] if os.path.exists(dp) else None
        R_.add("K6 dry-run gate validation/H0_ddtest_dryrun.json PASS", dg, "PASS", dg == "PASS")
    miss = decision_complete(dec)
    re_adopt, _q = adopt({c: {"R": dec["cells"][c]["R"], "R_95": dec["cells"][c]["R_95"]} for c in CANDIDATES})
    re_bar = signed_bar(dec["cells"][re_adopt]["f_pool_95"])
    R_.add("K7 data.decision complete and the adoption and signed-bar verdict recomputed from the recorded intervals",
           f"missing {miss}; adopted {adopted} (recomputed {re_adopt}), bar {bar} (recomputed {re_bar})",
           "complete and equal", not miss and re_adopt == adopted and re_bar == bar)
    if args.skip_tests:
        checks = {"skipped": True, "ok": None}
        R_.add("K8 pytest -q tests and scripts/check_package.py", "n/a (--skip-tests)", "all pass", dry)
    else:
        checks = G.run_checks(False)
        R_.add("K8 pytest -q tests and scripts/check_package.py",
               f"pytest: {checks.get('pytest_summary')}; check_package rc {checks.get('check_package_returncode')}",
               "all pass", checks["ok"])

    R_.data = {
        "what_pass_means": ("preregistered, measured, verified, consistent; there is no criterion on the ratios, the "
                            "adoption or the signed-bar read"),
        "dry_run": dry, "versions": versions(),
        "prereg": rel(pre_path) if os.path.isabs(pre_path) else pre_path, "prereg_created": pre["created"],
        "prereg_commit": pre["commit"], "prereg_keys_missing": missing_keys,
        "calibration_prereg": pre["calibration"], "patch": patch, "pubs": pre["pubs"],
        "execution_estimate_prereg_s": pre["execution_estimate"]["total_execution_s"],
        "counts_dir": rel(cdir), "session_file": rel(spath) if session else None,
        "live": {"job_ids": job_ids, "statuses": statuses, "usage_s": usage_s,
                 "submission_fingerprint": (session or {}).get("calibration_fingerprint"),
                 "prereg_fingerprint_match": (session or {}).get("prereg_fingerprint_match"),
                 "retrieval_fingerprint": ret_fp, "retrieval_diff": ret_diff,
                 "preflight_estimate_s": (((session or {}).get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s"),
                 "sampler_options": (session or {}).get("sampler_options"), "account": acct, "K1": k1_info},
        "readout": ro, "readout_survival_product": ro_survival, "readout_expected_live": ro_live,
        "dry_run_K3": dry_k3_block, "circuits": circ, "roundtrip": rt, "decision": dec,
        "decision_rule": pre["decision_rule"], "power_prereg": pre["power"],
        "reserve_T_A3": {"path": rel(p(prep, "reserve.json")), "reserve_s": reserve["stage_R_plan"]["reserve_s"],
                         "remaining_s_at_check": reserve["remaining_s_at_check"], "p8_ruling": P8_RULING},
        "dry_run_note": ("Aer cannot show a DD gain: its relaxation on a delay is Markovian, so the dry-run ratios "
                         "sit near the null values exp(-S_DD) and are path checks, not predictions (P10)") if dry else None,
        "checks": checks,
    }
    R_.runtime_s = time.time() - t0
    path = R_.save()
    saved = load_json(path)
    name = "H0_ddtest_dryrun.md" if dry else "H0_ddtest_ibm_kingston.md"
    write_report(name, report_text(saved, R_))
    print(R_.criteria_table())
    print(f"status {saved['status']}; adopted {adopted}; " + "; ".join(
        f"{c} f {_f(cells[c]['f_pool'])} {_iv(cells[c]['f_pool_95'])} R {_f(cells[c]['R'], '{:.3f}')} "
        f"{_iv(cells[c]['R_95'], '{:.3f}')} null {cells[c]['null_ratio']:.3f}" for c in CELLS) + f"; bar {bar}")
    if not dry and r_fits is False:
        print(f"STOP (P1): the Stage R reserve at the adopted f ({rplan['reserve_s']:.1f} s) does not fit the "
              f"{rem_now:.0f} s left")
    return 0 if saved["status"] == "PASS" else 1


def report_text(saved, R_):
    from skqd.report import md_table
    D = saved["data"]
    dec = D["decision"]
    live = D["live"]
    dry = D["dry_run"]
    rows = []
    for c, v in dec["cells"].items():
        rows.append([c, sum(v["accepted"].values()), v["n_reference"], f"{v['expected_from_garbage']:.2f}",
                     f"{v['excess_hits']:.1f}", f"{_f(v['f_pool'])} {_iv(v['f_pool_68'])} {_iv(v['f_pool_95'])}",
                     _f(v["R"], "{:.3f}"), _iv(v["R_95"], "{:.3f}"), _iv(v["R_bootstrap_95"], "{:.3f}"),
                     f"{v['null_ratio']:.3f}", _f(v.get("R_over_null"), "{:.3f}"), v["qualifies"]])
    crow = []
    for c, v in dec["cells"].items():
        for b, x in v["f_by_circuit"].items():
            crow.append([c, b, v["accepted"][b], v["reference_hits"][b],
                         f"{_f(x['reference'])} {_iv(x['reference_95'])}", f"{_f(x['mixture'])} {_iv(x['mixture_68'])}",
                         _f(v["c6_relative_deviation_information"][b], "{:.3f}"), v["n_pulses_per_circuit"][b],
                         str(v["distance_histograms"][b])])
    ro = D["readout"] or {}
    k1 = live.get("K1") or {}
    acct = live.get("account") or {}
    ub = (acct.get("before") or {}).get("usage") or {}
    ua = (acct.get("after") or {}).get("usage") or {}
    rp = dec.get("stage_R_reserve_at_adopted_f") or {}
    grows = [[g["n_pubs"], g["shots"], g["chunk"], f"{g['execution_s']:.2f}"] for g in rp.get("groups", [])]
    ad = dec["adopted"]
    title = "dry run (local Aer on the FakeKingston snapshot; a path check, not a prediction)" if dry else "ibm_kingston"
    return f"""# Gate {saved['gate']} -- client-side DD A/B test, {title}

**Status: {saved['status']}** -- `scripts/gate_H0_ddtest.py --stage assemble --counts {D['counts_dir']}{' --dry-run' if dry else ''} --out {saved['gate']}`.
Runtime {saved['runtime_s']:.0f} s.  Every number below is computed by the script from the raw counts and from `{D['prereg']}`
and is stored in `validation/{saved['gate']}.json`.  Prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage T).

## 0. What PASS means

{D['what_pass_means']}.{(' ' + D['dry_run_note'] + '.') if D.get('dry_run_note') else ''}

## 1. Preregistration

`{D['prereg']}`, written {D['prereg_created']} at commit `{D['prereg_commit']}` on the patch record
`{D['calibration_prereg']['path']}` (fingerprint `{D['calibration_prereg']['fingerprint']}`).  Patch {D['patch']}; 10 pubs x 6000
shots; execution estimate {D['execution_estimate_prereg_s']:.2f} s.  Rule: {D['decision_rule']['adoption']}  {D['decision_rule']['ratio']}

## 2. Live block

| item | value |
|---|---|
| job id(s) / status | {live['job_ids']} / {live['statuses']} |
| usage (s) | {live['usage_s']} |
| preflight estimate (s) | {live['preflight_estimate_s']} |
| fingerprint at prereg / submission / retrieval | `{D['calibration_prereg']['fingerprint'][:16]}` / `{(live['submission_fingerprint'] or 'n/a')[:16]}` / `{(live['retrieval_fingerprint'] or 'n/a')[:16]}` |
| prereg match at submission / retrieval | {live['prereg_fingerprint_match']} / {k1.get('retrieval_match')} |
| retrieval diff | {live['retrieval_diff']} |
| prereg commit time / submitted | {k1.get('prereg_commit_time')} (added in {k1.get('prereg_added_in')}, {k1.get('prereg_added_time')}) / {k1.get('submitted')} |
| account usage before / after | {ub.get('usage_consumed_seconds')} s ({ub.get('usage_remaining_seconds')} left) / {ua.get('usage_consumed_seconds')} s ({ua.get('usage_remaining_seconds')} left) |
| sampler options | {live['sampler_options']} |

## 3. The four cells against their null values

{md_table(["cell", "accepted", "ref hits", "garbage exp.", "excess X", "f_pool [68 %] [95 %]", "R = X_i/X_0",
           "R 95 %", "R bootstrap 95 %", "null e^-S_DD", "R / null", "qualifies"], rows)}

Per circuit:

{md_table(["cell", "circuit", "accepted", "ref hits", "f reference [95 %]", "f mixture [68 %]", "C6 dev (info)",
           "pulses", "distance histogram"], crow)}

## 4. Adoption (preregistered rule P7)

Qualifying cells: {dec['qualifying'] or 'none'}.  **Adopted: {ad}** -- f_adopted = {_f(dec['f_adopted'])} (68 % {_iv(dec['f_adopted_68'])},
95 % {_iv(dec['f_adopted_95'])}).

## 5. The signed bar (information for the owner)

f >= 0.1 read on the adopted cell's 95 % interval: **{dec['signed_bar']}**.  Stage R proceeds in every case under the owner's
decision of 2026-10-02.

## 6. The Stage R reserve at the adopted f (P1)

{D['reserve_T_A3']['p8_ruling']}

{md_table(["Stage R job: pubs", "shots", "chunk", "execution (s)"], grows) if grows else 'not computed'}

N4 {rp.get('N4')}; coarse shots {rp.get('total_coarse_shots')}; total {_f(rp.get('total_execution_s'), '{:.2f}')} s; reserve
{_f(rp.get('reserve_s'), '{:.1f}')} s against {_f(dec.get('remaining_s_after_stage_T'), '{:.0f}')} s left: fits {dec.get('stage_R_reserve_fits')}.

## 7. Readout

Smallest confusion diagonal {_f(ro.get('min_diagonal'))}; readout survival prod_q (1 - e_q) {_f(D['readout_survival_product'])};
preregistered live expectation min {D['readout_expected_live']['min']:.4f} (qubit {D['readout_expected_live']['min_qubit']}).

## 8. Honest limits

- Stage T compares four cells inside one job on one calibration content; its ratios carry no statement about other days or
  patches.  The null ratios (e^-S_DD) assume the record's x error for every inserted pulse.
- Three candidates are tested; the family-wise chance that a null cell qualifies on the interval alone is <= 7.5 %, and the
  1.25 floor is a cost argument, not a physics threshold.
- A qualifying ratio raises f for *this* circuit's idle structure; the signed bar is read on the adopted cell's lower 95 % bound
  and nothing else.
- Two k = 1 circuits are not a family-level statement at other k.
- One calibration content; drift between submission and retrieval is reported (above), not corrected.

## 9. Criteria

{R_.criteria_table()}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("reserve", "predict", "prereg-md", "assemble"))
    ap.add_argument("--prep", default=PREP)
    ap.add_argument("--prereg", default=None)
    ap.add_argument("--counts", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    return {"reserve": stage_reserve, "predict": stage_predict, "prereg-md": stage_prereg_md,
            "assemble": stage_assemble}[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
