#!/usr/bin/env python3
"""
Gate H0_ddrep (prompts/32 part A) -- one preregistered job on ibm_kingston that replicates the
XY4 gain of gate H0_ddtest (T0 vs T3), replicates the collapse of the context-aware cell T1, and
discriminates three hypotheses for that collapse with four mechanism cells (M1 CA+/-, M2 XX,
M3 X(-X), M4 CA minus the two hottest qubits) and four pulse-train calibration pubs.

A measurement gate: PASS = preregistered, measured, verified, consistent (D1-D8).  No criterion
depends on R1, R2, C1, the classes or the mechanism reading.

Stages (0 QPU s; the one submission is `scripts/h0_submit.py`, unchanged):
  reserve    P7: remaining - 45 >= max(300, 1.3 x the K1 estimate) -> <prep>/reserve.json (exit 3 if not)
  predict    A.2.3: the preregistration <prep>/prereg_<fp16>.json (live D9 check unless --offline)
  prereg-md  A.2.4: reports/H0_ddrep_prereg_<stamp>.md from that JSON
  assemble   A.2.5: the analysis of a counts directory -> validation/<out>.json + the report
`gate_H0_ddtest.py` is imported, never edited.
"""
import argparse
import glob
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gate_H0_ddtest as GD  # noqa: E402  (import only)
import gate_H0_kpilot as GK  # noqa: E402  (import only)

ROOT = GK.ROOT
PREP = os.path.join("data", "hardware", "H0_ddrep_prep")
DEVICE = "ibm_kingston"
BASE_IDS = GD.BASE_IDS
CELLS = ("T0", "T1", "T3", "M1", "M2", "M3", "M4")
DD_CELLS = CELLS[1:]
TRAIN_IDS = ("train_XX_8", "train_XX_32", "train_XX_128", "train_XpXm_128")
TRAIN_N = {"train_XX_8": 8, "train_XX_32": 32, "train_XX_128": 128, "train_XpXm_128": 128}
XX_TRAINS = ("train_XX_8", "train_XX_32", "train_XX_128")
N_PUBS = len(CELLS) * len(BASE_IDS) + 2 + len(TRAIN_IDS)
# ---- preregistered constants (prompts/32 P5-P7; none tuned on data)
SHOTS = 6000
MAX_ESTIMATE_S = 36.0
MAX_USAGE_S = 45.0
B_RESERVE_S = 300.0
K1_RESERVE_FACTOR = 1.3
COLLAPSED_HI95 = 0.25
INTACT_LO95 = 1.0
Z95 = GD.Z95
Z_ONE_SIDED = 1.645
EPS_HA = 0.01                 # P5 / P4 H_A: epsilon_q >= 0.01 rad
N_QUBITS_HA = 6               # ... on >= 6 of 12 qubits
TRAIN_EXCESS_HA = 0.05        # XX-128 above XpXm-128 by > 0.05
C_FACTOR_HD = 3.0             # c_q > 3 x_error
EPS_GRID_MAX = math.pi / 8
EPS_GRID_STEP = 1e-4
TRAIN_BOOT_DRAWS, TRAIN_BOOT_SEED = 2000, 32
K1_REHEARSAL_PREREG = os.path.join("data", "K1_2x3_fpilot", "rehearsal_committed_record", "prep",
                                   "prereg_38012b45ebcd2366.json")
DDTEST_JSON = os.path.join("validation", "H0_ddtest.json")
R_NC_JSON = os.path.join("data", "cf_trajectories", "r_nc.json")

PLANNER_EXPECTATION = ("T3 replicates (R about 2.8); T1 collapses again; the mechanism reading is open -- the planner's own "
                       "bound shows H_A at the RB-level epsilon cannot reach 0.012 unless the errors are coherent across "
                       "windows or the x pulse is worse than its aliased record value, which the trains measure.")
CLASS_RULE = ("Classes per circuit cell on R_i = X_i / X_0 (gate_H0_ddtest.ratio_interval, Poisson 95 %): COLLAPSED iff "
              "R_hi95 < 0.25; INTACT iff R_lo95 > 1; INTERMEDIATE otherwise.  If X_i <= 0 (no excess reference hits) "
              "the interval is [0, U_i / L_0] with U_i = the Garwood 97.5 % upper limit of the cell's pooled reference count "
              "minus its garbage expectation and L_0 = the Garwood 2.5 % lower limit of T0's count minus T0's garbage "
              "expectation (executor addition fixed before data: the ratio_interval of gate_H0_ddtest is undefined there).")
READING_RULE = ("M1 INTACT -> H_A; M1 COLLAPSED and M4 INTACT -> H_D; M1 COLLAPSED and M4 not INTACT -> H_B; any other "
                "pattern -> 'no single hypothesis' (reported as the table of classes).  The P4 trains are read beside it as "
                "the independent measurement of H_A's parameter: the pair (circuit reading, epsilon reading) is the result.  "
                "M2/M3: ln(R_M3 / R_M2) with sigma sqrt(1/X_M3 + 1/X_M2); one-sided z > 1.645 = 'compensation matters'.  "
                "M3 against T3: information.")
PREDICTION_TABLE = {
    "T1": {"H_A": "COLLAPSED", "H_B": "COLLAPSED", "H_D": "COLLAPSED"},
    "M1": {"H_A": "INTACT", "H_B": "COLLAPSED", "H_D": "COLLAPSED"},
    "M2": {"H_A": "not INTACT, and R_M2 < R_M3", "H_B": "INTACT", "H_D": "INTACT"},
    "M3": {"H_A": "INTACT", "H_B": "INTACT", "H_D": "INTACT"},
    "M4": {"H_A": "not INTACT", "H_B": "not INTACT", "H_D": "INTACT"},
    "P4 trains": {"H_A": "epsilon_q >= 0.01 rad on >= 6 of 12 qubits, XX-128 above XpXm-128 by > 0.05",
                  "H_B": "all four at the floor (readout + n c_q)",
                  "H_D": "c_95 or c_91 > 3 x_error, the others at x_error"},
}
TRAIN_READING_RULE = (
    "Executor operationalisation of P4's table (fixed before data): per qubit P1 = readout-corrected P(1) "
    "(p - (1 - P00)) / (P00 + P11 - 1) with the job's own confusion diagonal; c_q = (P1(XpXm-128) - P1(XX-8)) / 120; "
    "floor_n = P1(XX-8) + (n - 8) c_q; epsilon_q = argmin over [0, pi/8] (grid 1e-4 rad) of sum_{n in 8, 32, 128} "
    "(P1(XX-n) - floor_n - sin^2(n epsilon / 2))^2; 68 % intervals by a parametric bootstrap (2000 draws, seed 32: "
    "binomial train and confusion counts).  H_A pattern: epsilon_q >= 0.01 on >= 6 of 12 qubits AND P1(XX-128) - "
    "P1(XpXm-128) > 0.05 on >= 6 of 12 qubits.  H_B pattern ('all four at the floor'): on every qubit P1(XX-128) - "
    "P1(XpXm-128) <= 0.05 and P1(XX-32) - floor_32 <= 0.05.  H_D pattern: c_q > 3 x_error_q on at least one of the two "
    "hot qubits and c_q <= 3 x_error_q on every other qubit (x_error of the preregistered patch record).")
R_VERDICTS = ("R1 gain replicated: T3 qualifies under the H0_ddtest adoption rule (R_T3,lo95 > 1 and R_T3 >= 1.25).  "
              "R2 magnitude consistent: |ln R_T3,new - ln R_T3,old| <= 1.96 sqrt(sigma_new^2 + sigma_old^2), sigma_new = "
              "sqrt(1/X_T3 + 1/X_T0), sigma_old from H0_ddtest's T3 interval.  C1 collapse replicated: T1 is COLLAPSED.  "
              "The signed bar is read on T3 (information) on f_hit and on f_hat_ideal = f_hit / r_nc (owner decision 1a).")

p, rel, load_json, dump_json, now, git_commit, versions = (GK.p, GK.rel, GK.load_json, GK.dump_json, GK.now,
                                                          GK.git_commit, GK.versions)


def r2_old():
    """(ln R_T3,old, sigma_old) from validation/H0_ddtest.json at import (never typed)."""
    c = load_json(p(DDTEST_JSON))["data"]["decision"]["cells"]
    lo, hi = c["T3"]["R_95"]
    return math.log(float(c["T3"]["R"])), (math.log(hi) - math.log(lo)) / (2.0 * Z95)


R2_LNR_OLD, R2_SIGMA_OLD = r2_old()


def f_t0_ddtest():
    return float(load_json(p(DDTEST_JSON))["data"]["decision"]["cells"]["T0"]["f_pool"])


def k1_estimate():
    pre = load_json(p(K1_REHEARSAL_PREREG))
    return float(pre["execution_estimate"]["total_execution_s"]), K1_REHEARSAL_PREREG


# =========================================================================== pure functions (tested)
def reserve_fits(remaining, k1_est, billed_cap=MAX_USAGE_S, b_cap=B_RESERVE_S, factor=K1_RESERVE_FACTOR):
    need = max(float(b_cap), factor * float(k1_est))
    return {"remaining_s": float(remaining), "billed_cap_A_s": float(billed_cap), "after_A_s": float(remaining) - billed_cap,
            "B_need_s": need, "B_cap_s": float(b_cap), "K1_estimate_s": float(k1_est), "K1_factor": factor,
            "fits": float(remaining) - billed_cap >= need}


def garwood(n, conf):
    from scipy.stats import chi2
    a = 1.0 - conf
    lo = 0.0 if n == 0 else float(chi2.ppf(a / 2.0, 2 * n) / 2.0)
    hi = float(chi2.ppf(1.0 - a / 2.0, 2 * n + 2) / 2.0)
    return lo, hi


def cell_ratio(n_i, g_i, n_0, g_0):
    """{R, R_95, branch} of R = X_i / X_0 with X = n - g (pooled reference count minus garbage)."""
    X_i, X_0 = float(n_i) - float(g_i), float(n_0) - float(g_0)
    if X_0 <= 0:
        return {"R": None, "R_95": [None, None], "branch": "baseline without excess (X_0 <= 0): undefined"}
    if X_i > 0:
        R, R95 = GD.ratio_interval(X_i, X_0)
        return {"R": R, "R_95": R95, "branch": "ratio_interval (Poisson on the excess counts)"}
    U = garwood(int(n_i), 0.95)[1] - float(g_i)
    L = garwood(int(n_0), 0.95)[0] - float(g_0)
    hi = (max(U, 0.0) / L) if L > 0 else None
    return {"R": X_i / X_0, "R_95": [0.0, hi], "branch": "X_i <= 0: [0, U_i / L_0] (Garwood 97.5 % / 2.5 %)"}


def classify(R95):
    if not R95 or R95[1] is None:
        return "UNDETERMINED"
    lo, hi = R95
    if hi < COLLAPSED_HI95:
        return "COLLAPSED"
    if lo is not None and lo > INTACT_LO95:
        return "INTACT"
    return "INTERMEDIATE"


def reading(classes):
    m1, m4 = classes.get("M1"), classes.get("M4")
    if m1 == "INTACT":
        return "H_A"
    if m1 == "COLLAPSED" and m4 == "INTACT":
        return "H_D"
    if m1 == "COLLAPSED" and m4 != "INTACT":
        return "H_B"
    return "no single hypothesis"


def prediction_matches(classes, R):
    """Per hypothesis and cell: does the observed class meet the P5 prediction (information)."""
    def not_intact(c):
        return c in ("COLLAPSED", "INTERMEDIATE")
    m2_lt_m3 = (R.get("M2") is not None and R.get("M3") is not None and R["M2"] < R["M3"])
    preds = {
        "H_A": {"T1": classes["T1"] == "COLLAPSED", "M1": classes["M1"] == "INTACT",
                "M2": not_intact(classes["M2"]) and m2_lt_m3, "M3": classes["M3"] == "INTACT",
                "M4": not_intact(classes["M4"])},
        "H_B": {"T1": classes["T1"] == "COLLAPSED", "M1": classes["M1"] == "COLLAPSED",
                "M2": classes["M2"] == "INTACT", "M3": classes["M3"] == "INTACT", "M4": not_intact(classes["M4"])},
        "H_D": {"T1": classes["T1"] == "COLLAPSED", "M1": classes["M1"] == "COLLAPSED",
                "M2": classes["M2"] == "INTACT", "M3": classes["M3"] == "INTACT", "M4": classes["M4"] == "INTACT"},
    }
    return {h: {"cells": v, "n_match": int(sum(v.values())), "all_match": all(v.values())} for h, v in preds.items()}


def r2_verdict(X3, X0, lnR_old=None, sigma_old=None):
    lnR_old = R2_LNR_OLD if lnR_old is None else lnR_old
    sigma_old = R2_SIGMA_OLD if sigma_old is None else sigma_old
    if X3 is None or X0 is None or X3 <= 0 or X0 <= 0:
        return {"lnR_new": None, "sigma_new": None, "tolerance": None, "consistent": False}
    ln_new = math.log(X3 / X0)
    s_new = math.sqrt(1.0 / X3 + 1.0 / X0)
    tol = Z95 * math.sqrt(s_new ** 2 + sigma_old ** 2)
    return {"lnR_new": ln_new, "sigma_new": s_new, "lnR_old": lnR_old, "sigma_old": sigma_old,
            "difference": ln_new - lnR_old, "tolerance": tol, "consistent": abs(ln_new - lnR_old) <= tol}


def log_ratio_z(Xa, Xb):
    """ln(Xa / Xb), its Poisson sigma and z (None when an excess is not positive)."""
    if Xa is None or Xb is None or Xa <= 0 or Xb <= 0:
        return {"lnR": None, "sigma": None, "z": None, "compensation_matters": None}
    ln = math.log(Xa / Xb)
    s = math.sqrt(1.0 / Xa + 1.0 / Xb)
    return {"lnR": ln, "sigma": s, "z": ln / s, "compensation_matters": ln / s > Z_ONE_SIDED}


def readout_correct(p_raw, p00, p11):
    den = np.asarray(p00) + np.asarray(p11) - 1.0
    return (np.asarray(p_raw) - (1.0 - np.asarray(p00))) / den


EPS_GRID = np.arange(0.0, EPS_GRID_MAX + EPS_GRID_STEP / 2, EPS_GRID_STEP)


def train_fit(P8, P32, P128, Pxpxm):
    """(epsilon, c) per element of the (broadcast) inputs -- the P4 model with the planner's floor."""
    P8, P32, P128, Pxpxm = (np.asarray(x, dtype=float) for x in (P8, P32, P128, Pxpxm))
    c = (Pxpxm - P8) / 120.0
    ys = []
    for n, Pn in ((8, P8), (32, P32), (128, P128)):
        floor = P8 + (n - 8) * c
        ys.append(Pn - floor)
    model = {n: np.sin(n * EPS_GRID / 2.0) ** 2 for n in (8, 32, 128)}
    ssr = sum((y[..., None] - model[n]) ** 2 for y, n in zip(ys, (8, 32, 128)))
    eps = EPS_GRID[np.argmin(ssr, axis=-1)]
    return eps, c


def train_readings(per_q, hot):
    """The three P4 patterns (executor operationalisation, preregistered as TRAIN_READING_RULE)."""
    qs = sorted(per_q, key=int)
    n_eps = sum(1 for q in qs if per_q[q]["epsilon"] >= EPS_HA)
    n_exc = sum(1 for q in qs if per_q[q]["P1"]["train_XX_128"] - per_q[q]["P1"]["train_XpXm_128"] > TRAIN_EXCESS_HA)
    ha = n_eps >= N_QUBITS_HA and n_exc >= N_QUBITS_HA
    hb = all(per_q[q]["P1"]["train_XX_128"] - per_q[q]["P1"]["train_XpXm_128"] <= TRAIN_EXCESS_HA
             and per_q[q]["P1"]["train_XX_32"] - per_q[q]["floor"]["32"] <= TRAIN_EXCESS_HA for q in qs)
    hot = [str(int(h)) for h in hot]
    above = {q: per_q[q]["c_per_pulse"] > C_FACTOR_HD * per_q[q]["x_error_record"] for q in qs}
    hd = any(above.get(h) for h in hot) and not any(above[q] for q in qs if q not in hot)
    return {"H_A": bool(ha), "H_B": bool(hb), "H_D": bool(hd), "n_qubits_eps_ge_0.01": n_eps,
            "n_qubits_XX128_minus_XpXm128_gt_0.05": n_exc,
            "qubits_c_above_3_x_error": sorted((q for q in qs if above[q]), key=int), "hot_qubits": hot}


def analyse_trains(records_by_id, ro, patch, rec, hot, draws=TRAIN_BOOT_DRAWS, seed=TRAIN_BOOT_SEED):
    """Per qubit raw / corrected P(1) of the four trains, c_q, epsilon_q and 68 % bootstrap intervals."""
    from gate_H0_diag import marginal_ones
    n = len(patch)
    raw, shots = {}, {}
    for tid in TRAIN_IDS:
        man, counts = records_by_id[tid]
        if man["logical_to_physical"] != list(patch):
            raise SystemExit(f"{tid}: clbit order is not the patch order")
        raw[tid], shots[tid] = marginal_ones(counts, n)
    p00 = np.array(ro["P_measure_0_given_0"])
    p11 = np.array(ro["P_measure_1_given_1"])
    cal_shots = int(ro.get("shots") or SHOTS)
    P = {tid: readout_correct(raw[tid], p00, p11) for tid in TRAIN_IDS}
    eps, c = train_fit(P["train_XX_8"], P["train_XX_32"], P["train_XX_128"], P["train_XpXm_128"])
    rng = np.random.default_rng(seed)
    bP = {}
    b00 = rng.binomial(cal_shots, p00, size=(draws, n)) / cal_shots
    b11 = rng.binomial(cal_shots, p11, size=(draws, n)) / cal_shots
    for tid in TRAIN_IDS:
        br = rng.binomial(shots[tid], np.clip(raw[tid], 0, 1), size=(draws, n)) / shots[tid]
        bP[tid] = readout_correct(br, b00, b11)
    beps, bc = train_fit(bP["train_XX_8"], bP["train_XX_32"], bP["train_XX_128"], bP["train_XpXm_128"])
    per_q = {}
    for i, q in enumerate(patch):
        xe = float(rec["qubits"][str(q)]["x_error"])
        per_q[str(q)] = {
            "clbit": i, "P1_raw": {tid: float(raw[tid][i]) for tid in TRAIN_IDS},
            "P1": {tid: float(P[tid][i]) for tid in TRAIN_IDS},
            "floor": {str(nn): float(P["train_XX_8"][i] + (nn - 8) * c[i]) for nn in (8, 32, 128)},
            "epsilon": float(eps[i]), "epsilon_68": [float(np.percentile(beps[:, i], 16)), float(np.percentile(beps[:, i], 84))],
            "c_per_pulse": float(c[i]), "c_68": [float(np.percentile(bc[:, i], 16)), float(np.percentile(bc[:, i], 84))],
            "x_error_record": xe, "c_over_x_error": (float(c[i]) / xe) if xe > 0 else None,
            "XX128_minus_XpXm128": float(P["train_XX_128"][i] - P["train_XpXm_128"][i]),
            "epsilon_RB_level_sqrt_6_x_error": math.sqrt(6.0 * xe)}
    rd = train_readings(per_q, hot)
    return {"per_qubit": per_q, "readings": rd, "shots": shots, "rule": TRAIN_READING_RULE,
            "bootstrap": {"draws": draws, "seed": seed}, "grid": {"max": EPS_GRID_MAX, "step": EPS_GRID_STEP}}


def h_a_bounds(per_q_pulses, rec):
    """The planner's two ends of the coherent-pulse-error bound on T1 (eps_q = sqrt(6 x_error_q))."""
    win, lin = 1.0, 1.0
    for q, n in per_q_pulses.items():
        eps = math.sqrt(6.0 * float(rec["qubits"][str(q)]["x_error"]))
        win *= math.cos(8 * eps / 2) ** (2 * int(n) / 8)
        lin *= math.cos(int(n) * eps / 2) ** 2
    return {"per_window_coherent_8_pulse_windows": win, "fully_coherent_linear": lin,
            "eps_rule": "eps_q = sqrt(6 x_error_q) on the record; coherent inside 8-pulse windows and random-walk across "
                        "them (first) / coherent over the whole circuit (second)"}


# =========================================================================== reserve
def latest_account(prep):
    fs = sorted(glob.glob(p(prep, "account_check_*.json")))
    if not fs:
        raise SystemExit("no account check in the prep directory: run h0_ddrep_circuits.py --stage account")
    return fs[-1], load_json(fs[-1])


def stage_reserve(args):
    prep = args.prep
    path, acct = latest_account(prep)
    remaining = float((acct.get("usage") or {}).get("usage_remaining_seconds"))
    k1, k1src = k1_estimate()
    r = reserve_fits(remaining, k1)
    out = {"stage": "reserve", "created": now(), "commit": git_commit(), "qpu_seconds": 0,
           "script": "scripts/gate_H0_ddrep.py --stage reserve", "account_check": rel(path),
           "remaining_s_at_check": remaining, "K1_estimate_source": k1src + " execution_estimate.total_execution_s",
           "K1_estimate_note": "the K1 rehearsal estimate on the committed record, until B.2 recomputes it on the day's record",
           "rule": "fits iff remaining - 45 >= max(300, 1.3 x K1 estimate) (prompts/32 P7)", **r}
    dump_json(out, p(prep, "reserve.json"))
    print(f"remaining {remaining:.0f} s; after A's cap {r['after_A_s']:.0f} s; B needs {r['B_need_s']:.1f} s "
          f"(max(300, 1.3 x {k1:.2f})): fits {r['fits']}")
    return 0 if r["fits"] else 3


# =========================================================================== predict
def stage_predict(args):
    import gate_S2D_levers as G
    import h0_qpu_time as qt
    from gate_H0P import DIAG_MIN
    from skqd.skqd import READOUT_FACTOR
    t0 = time.time()
    prep = args.prep
    rec, prinfo, info = GK.patch_record(prep)
    index = load_json(p(prep, "index.json"))
    sel = load_json(p(prep, "select.json"))
    reserve = load_json(p(prep, "reserve.json")) if os.path.exists(p(prep, "reserve.json")) else None
    if reserve is None and not args.offline:
        raise SystemExit("reserve.json missing: run --stage reserve first")
    mans = GK.prep_manifests(prep)
    patch = index["patch"]
    if args.offline:
        from h0_backends import backend_from_record
        from qiskit_ibm_runtime.fake_provider import FakeKingston
        b, _ = backend_from_record(load_json(info["record"]["path"]), base=FakeKingston(), strict=True)
        live_fp = None
    else:
        from h0_backends import fresh_calibration, frozen_qubits_and_edges, resolve_backend
        b = resolve_backend(DEVICE)
        qubits, edges = frozen_qubits_and_edges(p(prep))
        live = fresh_calibration(b, qubits, edges)
        live_fp = live["fingerprint"]
        if live_fp != rec["fingerprint"]:
            print(f"STOP (D10): the live patch fingerprint {live_fp[:16]} is not the patch record's {rec['fingerprint'][:16]}")
            return 3
    est = qt.estimate(p(prep), b, {}, SHOTS, shots_default=SHOTS)
    f0 = f_t0_ddtest()
    cells = {}
    for cell in CELLS:
        per = {}
        for cid in BASE_IDS:
            m = mans[f"{cid}_{cell}"]
            dd = m["dd"]
            ag = G.garbage_acceptance(m["twoB"])
            n_exp = SHOTS * READOUT_FACTOR * f0 * m["p_reference"]
            per[cid] = {"id": m["id"], "n_pulses": dd["n_pulses"], "n_rz_inserted": dd.get("n_rz_inserted", 0),
                        "pulse_cost_nats": dd["pulse_cost_nats"], "null_ratio": dd["null_ratio"],
                        "pulses_per_physical_qubit": dd["pulses_per_physical_qubit"],
                        "qpy_gz_sha256": m["qpy_gz_sha256"], "scheduled_duration_s": m["scheduled_duration_s"],
                        "p_reference": m["p_reference"], "garbage_acceptance": ag, "dim": m["dim"],
                        "expected_reference_hits_at_f_T0": n_exp,
                        "expected_reference_hits_from_garbage": SHOTS * ag / m["dim"],
                        "expected_reference_hits_at_f_T0_x_null": n_exp * dd["null_ratio"]}
        m0 = mans[f"{BASE_IDS[0]}_{cell}"]
        cells[cell] = {"description": m0["dd"]["description"], "pass": m0["dd"]["pass"], "parameters": m0["dd"]["parameters"],
                       "per_circuit": per,
                       "null_ratio_pooled": (sum(v["expected_reference_hits_at_f_T0_x_null"] for v in per.values())
                                             / sum(v["expected_reference_hits_at_f_T0"] for v in per.values())),
                       "expected_excess_hits_at_f_T0_x_null": sum(v["expected_reference_hits_at_f_T0_x_null"] for v in per.values())}
    X0 = sum(v["expected_reference_hits_at_f_T0"] for v in cells["T0"]["per_circuit"].values())
    s_lnR = math.sqrt(2.0 / X0)
    R_old = math.exp(R2_LNR_OLD)
    s_new_exp = math.sqrt(1.0 / (R_old * X0) + 1.0 / X0)
    power = {"X_per_cell_at_f_T0": X0, "f_T0": f0, "f_T0_source": f"{DDTEST_JSON} data.decision.cells.T0.f_pool",
             "sigma_lnR": s_lnR, "factor_95": [math.exp(-Z95 * s_lnR), math.exp(Z95 * s_lnR)],
             "lower_bound_of_a_true_1.25": GD.RATIO_FLOOR * math.exp(-Z95 * s_lnR),
             "decidable_at_1.25": GD.RATIO_FLOOR * math.exp(-Z95 * s_lnR) > 1.0,
             "R2_tolerance_expected": Z95 * math.sqrt(s_new_exp ** 2 + R2_SIGMA_OLD ** 2),
             "note": "X = sum_c 6000 x 0.82 x f_T0 x p_ref,c; sigma_lnR = sqrt(1/X + 1/X); R2 tolerance at R_T3 = R_old"}
    hot = index.get("hot_qubits")
    ha = {cid: h_a_bounds(mans[f"{cid}_T1"]["dd"]["pulses_per_physical_qubit"], rec) for cid in BASE_IDS}
    ddt = load_json(p(DDTEST_JSON))["data"]["decision"]["cells"]
    pubs = [{"id": m["id"], "kind": m["kind"], "cell": (m.get("dd") or {}).get("cell"), "test": m.get("test"),
             "shots": SHOTS} for m in sorted(mans.values(), key=lambda m: m["id"])]
    fp16 = rec["fingerprint"][:16]
    k1, k1src = k1_estimate()
    pre = {
        "gate": "H0_ddrep", "script": "scripts/gate_H0_ddrep.py --stage predict", "created": now(), "commit": git_commit(),
        "versions": versions(), "qpu_seconds": 0, "prep": prep, "prep_created": index["created"],
        "offline_prototype": bool(args.offline),
        "calibration": {"backend": DEVICE, "fingerprint": rec["fingerprint"], "path": prinfo["path"],
                        "last_update_date": rec["last_update_date"], "stamp": rec["stamp"],
                        "full_record_path": info["record"]["path"], "full_record_fingerprint": info["record"]["fingerprint"],
                        "live_fingerprint_at_predict": live_fp,
                        "live_match_at_predict": (None if live_fp is None else live_fp == rec["fingerprint"])},
        "patch": patch, "patch_reproduced": index["patch_reproduced"],
        "patch_note": ("the committed H0_ddtest patch is kept (P2): T0/T1/T3 are the H0_ddtest QPYs byte for byte"
                       if index["patch_reproduced"] else
                       "a same-device, new-patch replication: the committed patch failed P2 and the circuits were rebuilt "
                       "by the same code on the winner"),
        "selection": {"rule": sel["rule"], "decision": sel["decision"], "winner_f_dd_off": sel["winner"]["f_dd_off"],
                      "committed_f_dd_off": (sel.get("committed_entry") or {}).get("f_dd_off"),
                      "committed_rank": sel.get("committed_rank"), "n_scored": sel["n_scored"]},
        "pubs": pubs, "n_pubs": len(pubs), "shots_per_pub": SHOTS, "total_shots": sum(x["shots"] for x in pubs),
        "sampler_options": "--dd off --twirling off (runtime DD off: the pulses are in the circuits); raw bit strings",
        "execution_estimate": {"total_execution_s": est["total_execution_s"], "total_shots": est["total_shots"],
                               "rep_delay_s": est["rep_delay_s"], "groups": est["groups"], "per_circuit": est["per_circuit"],
                               "cap_s": MAX_ESTIMATE_S, "within_cap": est["total_execution_s"] <= MAX_ESTIMATE_S,
                               "billed_cap_s": MAX_USAGE_S},
        "cells": cells, "power": power,
        "ddtest_reference": {c: {"R": ddt[c].get("R"), "R_95": ddt[c].get("R_95"), "f_pool": ddt[c]["f_pool"],
                                 "excess_hits": ddt[c]["excess_hits"]} for c in ("T0", "T1", "T2", "T3")},
        "class_rule": CLASS_RULE, "class_thresholds": {"COLLAPSED_hi95_below": COLLAPSED_HI95, "INTACT_lo95_above": INTACT_LO95},
        "prediction_table": PREDICTION_TABLE, "reading_rule": READING_RULE, "train_reading_rule": TRAIN_READING_RULE,
        "train_constants": {"eps_HA": EPS_HA, "n_qubits_HA": N_QUBITS_HA, "train_excess_HA": TRAIN_EXCESS_HA,
                            "c_factor_HD": C_FACTOR_HD},
        "replication_verdicts": R_VERDICTS,
        "R2": {"lnR_old": R2_LNR_OLD, "sigma_old": R2_SIGMA_OLD, "source": f"{DDTEST_JSON} data.decision.cells.T3 (R, R_95)",
               "sigma_old_rule": "(ln hi - ln lo) / (2 x 1.959964)"},
        "adoption_rule_reused": GD.ADOPTION_RULE, "ratio_rule_reused": GD.RATIO_RULE,
        "H_A_bounds_T1": {"per_circuit": ha, "ddtest_measured_R_T1": ddt["T1"]["R"],
                          "ddtest_null_T1": ddt["T1"]["null_ratio"],
                          "x_error_equals_sx_error_on_patch": all(rec["qubits"][str(q)]["x_error"] == rec["qubits"][str(q)]["sx_error"]
                                                                  for q in patch)},
        "hot_qubits": hot, "identities": index.get("identities"),
        "reserve": (None if reserve is None else {k: reserve[k] for k in ("remaining_s_at_check", "after_A_s", "B_need_s",
                                                                          "K1_estimate_s", "fits", "account_check")}),
        "K1_estimate_s": k1, "K1_estimate_source": k1src,
        "planner_expectation": PLANNER_EXPECTATION,
        "no_aer_prediction": "no Aer prediction of a DD gain (P10 of prompts/24: Aer cannot show one)",
        "runtime_s": time.time() - t0,
    }
    pre["readout_expected_live"] = GK.readout_expected_live(rec, patch)
    path = p(prep, f"prereg_{fp16}.json")
    if os.path.exists(path):
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel(path)], cwd=ROOT, capture_output=True).returncode == 0
        if tracked:
            raise SystemExit(f"{rel(path)} is committed as the preregistration: refusing to overwrite")
    if pre["readout_expected_live"]["min"] < DIAG_MIN:
        print(f"STOP: the live readout expectation {pre['readout_expected_live']['min']:.4f} < {DIAG_MIN}")
        return 3
    dump_json(pre, path)
    print(f"wrote {rel(path)}: {len(pubs)} pubs, estimate {est['total_execution_s']:.2f} s (cap {MAX_ESTIMATE_S:.0f}); X per "
          f"cell at f_T0 {X0:.0f}, sigma_lnR {s_lnR:.3f}; nulls " + ", ".join(f"{c} {cells[c]['null_ratio_pooled']:.3f}" for c in CELLS))
    if est["total_execution_s"] > MAX_ESTIMATE_S:
        print(f"STOP: the execution estimate {est['total_execution_s']:.1f} s exceeds {MAX_ESTIMATE_S:.0f} s")
        return 3
    return 0


def _f(x, spec="{:.4f}"):
    return "n/a" if x is None else spec.format(x)


def _iv(iv, spec="{:.4f}"):
    if not iv or iv[0] is None or iv[1] is None:
        return "n/a" if not iv or (iv[0] is None and iv[1] is None) else f"[{_f(iv[0], spec)}, {_f(iv[1], spec)}]"
    return "[" + spec.format(iv[0]) + ", " + spec.format(iv[1]) + "]"


def stage_prereg_md(args):
    from skqd.report import md_table, write_report
    path = args.prereg or sorted(glob.glob(p(args.prep, "prereg_*.json")))[-1]
    pre = load_json(path)
    est = pre["execution_estimate"]
    cal = pre["calibration"]
    rows = []
    for c, v in pre["cells"].items():
        for cid, x in v["per_circuit"].items():
            top = sorted(x["pulses_per_physical_qubit"].items(), key=lambda kv: -kv[1])[:3]
            rows.append([c, x["id"], x["n_pulses"], x["n_rz_inserted"], f"{x['pulse_cost_nats']:.4f}", f"{x['null_ratio']:.3f}",
                         f"{x['scheduled_duration_s'] * 1e6:.3f}", f"{x['p_reference']:.4f}",
                         f"{x['expected_reference_hits_at_f_T0']:.0f}", ", ".join(f"q{q}:{n}" for q, n in top)])
    pubs = [[x["id"], x["kind"], x.get("cell") or x.get("test") or "", x["shots"]] for x in pre["pubs"]]
    pw = pre["power"]
    prow = [[c] + [v[h] for h in ("H_A", "H_B", "H_D")] for c, v in pre["prediction_table"].items()]
    harow = [[cid, f"{v['per_window_coherent_8_pulse_windows']:.4g}", f"{v['fully_coherent_linear']:.4g}"]
             for cid, v in pre["H_A_bounds_T1"]["per_circuit"].items()]
    rs = pre.get("reserve") or {}
    title_extra = " (OFFLINE PROTOTYPE on the committed record -- not a preregistration)" if pre.get("offline_prototype") else ""
    txt = f"""# H0_ddrep preregistration -- ibm_kingston, calibration `{cal['fingerprint'][:16]}`{title_extra}

Generated by `scripts/gate_H0_ddrep.py --stage prereg-md` from `{rel(path) if os.path.isabs(path) else path}` (written
{pre['created']} at commit `{pre['commit']}`).  Every number below is read from that JSON.  Nothing was submitted when this was
written; the commit that adds this file is what criterion D1 checks against the submission time.
Prompt in force: `prompts/32_2x2_dd_replication_and_T1_mechanism.md` (part A); owner decision
`data/owner_decision_20261006_A_then_B.md`.

## Calibration and patch

- Patch record `{cal['path']}`: fingerprint `{cal['fingerprint']}`, last update {cal['last_update_date']} (full record
  `{cal['full_record_path']}`); live content at the prediction identical: {cal['live_match_at_predict']}.
- Patch {pre['patch']}; patch reproduced (P2): **{pre['patch_reproduced']}** -- {pre['patch_note']}.  Selection: winner f_dd_off
  {pre['selection']['winner_f_dd_off']:.4f}, committed patch f_dd_off {_f(pre['selection']['committed_f_dd_off'])} (rank
  {pre['selection']['committed_rank']} of {pre['selection']['n_scored']}); P2 reasons {pre['selection']['decision']['reasons'] or 'none'}.
- Hot qubits of M4 (most inserted T1 pulses): {pre['hot_qubits']}.

## Pubs, shots, execution estimate

{md_table(["pub", "kind", "cell / test", "shots"], pubs)}

{pre['total_shots']} shots in one job ({pre['n_pubs']} pubs); execution estimate **{est['total_execution_s']:.2f} s** (estimator cap
{est['cap_s']:.0f} s, within: {est['within_cap']}; billed cap {est['billed_cap_s']:.0f} s; rep delay {est['rep_delay_s'] * 1e6:.0f} us).
Options: {pre['sampler_options']}.

## The seven cells (P3, parameters fixed before data)

{md_table(["cell", "circuit", "x pulses", "rz inserted", "S_DD (nats)", "null e^-S_DD", "duration (us)", "p_ref",
           "expected ref hits at f_T0", "most pulses"], rows)}

""" + "\n".join(f"- **{c}** {v['description']} -- `{v['pass']}` {json.dumps(v['parameters'])}" for c, v in pre["cells"].items()) + f"""

Build identities (P3, asserted at build): {json.dumps(pre['identities'])}

## Power (on the H0_ddtest baseline)

f_T0 = {pw['f_T0']:.4f} ({pw['f_T0_source']}); expected excess reference hits per cell X = {pw['X_per_cell_at_f_T0']:.0f}; sigma(ln R) =
{pw['sigma_lnR']:.4f}; 95 % factor {_iv(pw['factor_95'], '{:.3f}')}; lower 95 % bound of a true 1.25: {pw['lower_bound_of_a_true_1.25']:.3f}
(decidable: {pw['decidable_at_1.25']}); expected R2 tolerance at R_T3 = R_old: {pw['R2_tolerance_expected']:.4f}.

## Classes, predictions and the reading rule (P5, verbatim)

{pre['class_rule']}

{md_table(["cell", "H_A", "H_B", "H_D"], prow)}

Reading rule: {pre['reading_rule']}

Trains: {pre['train_reading_rule']}

## Replication verdicts (P6)

{pre['replication_verdicts']}  ln R_T3,old = {pre['R2']['lnR_old']:.4f}, sigma_old = {pre['R2']['sigma_old']:.4f} ({pre['R2']['source']}).

## H_A bounds on T1 (recomputed on this record)

{md_table(["circuit", "coherent in 8-pulse windows", "coherent over the circuit"], harow)}

H0_ddtest measured R_T1 = {pre['H_A_bounds_T1']['ddtest_measured_R_T1']:.4f} (null {pre['H_A_bounds_T1']['ddtest_null_T1']:.3f}); x_error == sx_error on
every patch qubit of this record: {pre['H_A_bounds_T1']['x_error_equals_sx_error_on_patch']}.

## Reserve for part B (P7)

Remaining at the account check {_f(rs.get('remaining_s_at_check'), '{:.0f}')} s; after A's billed cap {_f(rs.get('after_A_s'), '{:.0f}')} s;
B needs {_f(rs.get('B_need_s'), '{:.1f}')} s (max(300, 1.3 x K1 estimate {pre['K1_estimate_s']:.2f} s)): fits {rs.get('fits')}.

## Planner expectation (written before data)

{pre['planner_expectation']}  {pre['no_aer_prediction']}.
"""
    name = (f"H0_ddrep_prereg_prototype_{cal['stamp']}.md" if pre.get("offline_prototype") else f"H0_ddrep_prereg_{cal['stamp']}.md")
    out = write_report(name, txt)
    print(f"wrote {rel(out)}")
    return 0


# =========================================================================== assemble
REPL_FIELDS = ("R1", "R2", "C1", "adopted", "qualifying", "signed_bar_f_hit", "signed_bar_f_hat_ideal")
MECH_FIELDS = ("classes", "reading", "M3_over_M2", "M3_over_T3", "prediction_matches")
CELL_FIELDS = ("f_pool", "f_pool_68", "f_pool_95", "f_by_circuit", "excess_hits", "R", "R_95", "null_ratio", "class")


def completeness(D):
    miss = []
    for blk, fields in (("replication", REPL_FIELDS), ("mechanism", MECH_FIELDS)):
        for k in fields:
            if k not in (D.get(blk) or {}):
                miss.append(f"{blk}.{k}")
    for c, v in (D.get("cells") or {}).items():
        for k in CELL_FIELDS:
            if c == "T0" and k in ("R_95", "class"):
                continue
            if k not in v or v[k] is None:
                miss.append(f"cells.{c}.{k}")
    tr = D.get("trains") or {}
    if not tr.get("per_qubit") or "readings" not in tr:
        miss.append("trains")
    else:
        for q, v in tr["per_qubit"].items():
            for k in ("P1", "floor", "epsilon", "epsilon_68", "c_per_pulse", "x_error_record"):
                if k not in v:
                    miss.append(f"trains.{q}.{k}")
    if not D.get("k0_2x3_nogo"):
        miss.append("k0_2x3_nogo")
    return miss


def recompute(D):
    """Classes, R1, R2, C1 and the reading from the recorded intervals (D7)."""
    cells = D["cells"]
    classes = {c: classify(cells[c]["R_95"]) for c in DD_CELLS}
    R1 = GD.qualifies(cells["T3"]["R"], cells["T3"]["R_95"])
    R2 = r2_verdict(cells["T3"]["excess_hits"], cells["T0"]["excess_hits"])["consistent"]
    return {"classes": classes, "R1": R1, "R2": R2, "C1": classes["T1"] == "COLLAPSED", "reading": reading(classes)}


def stage_assemble(args):
    import gate_S2D_levers as G
    import k0_nogo_note as K0N
    from gate_H0 import codeword_roundtrip, read_counts_dir
    from gate_H0_diag import readout_reference
    from gate_H0P import DIAG_MIN
    from h0_backends import calibration_diff
    from skqd.codec import Codec
    from skqd.report import GateResult, write_report
    from skqd.skqd import corrected_clean_fraction, pooled_reference_string_test
    t0 = time.time()
    dry = bool(args.dry_run)
    out = args.out or ("H0_ddrep_dryrun" if dry else "H0_ddrep")
    prep = args.prep
    pre_path = args.prereg or GK.find_prereg(prep)
    pre = load_json(pre_path)
    missing_keys = GK.prereg_keys_ok(pre)
    mans = GK.prep_manifests(prep)
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

    # ---- readout (D3)
    ro = readout_reference({"records": records}, n)
    if ro:
        ro["shots"] = int(sum(by_id["cal_patch_all0"][1].values()))
    ro_live = GK.readout_expected_live(prereg_rec, patch)
    cal_phys = mans["cal_patch_all0"]["logical_to_physical"]
    dry_k3_block = None
    if dry and ro:
        exp_model = GK.snapshot_readout_model(index["common"]["backend"], cal_phys)
        meas = {int(q): (ro["P_measure_0_given_0"][i], ro["P_measure_1_given_1"][i]) for i, q in enumerate(cal_phys)}
        k3_ok, k3_rows = GK.dry_k3(meas, exp_model, ro["shots"])
        dry_k3_block = {"ok": k3_ok, "per_qubit": k3_rows, "shots": ro["shots"], "sigma_k": 3.0,
                        "model": f"NoiseModel.from_backend({index['common']['backend']}) local readout errors",
                        "ruling": "prompts/21a option (a): the dry-run K3 form"}

    # ---- the cells
    coarse_ids = [f"{b}_{c}" for c in CELLS for b in BASE_IDS]
    circ = {cid: GK.decode_counts([by_id[cid][1]], mans[cid]) for cid in coarse_ids}
    rt = codeword_roundtrip([(mans[cid], by_id[cid][1]) for cid in coarse_ids], codec)
    cells, rows_by = {}, {}
    p95_by = {}
    for c in CELLS:
        rows = [circ[f"{b}_{c}"]["row"] for b in BASE_IDS]
        rows_by[c] = rows
        p68 = pooled_reference_string_test(rows, conf=GK.CONF68)
        p95 = pooled_reference_string_test(rows, conf=GK.CONF95)
        p95_by[c] = p95
        nulls = [mans[f"{b}_{c}"]["dd"]["null_ratio"] for b in BASE_IDS]
        ws = [mans[f"{b}_{c}"]["p_reference"] for b in BASE_IDS]
        cells[c] = {"description": mans[f"{BASE_IDS[0]}_{c}"]["dd"]["description"],
                    "f_pool": p68["f_clean"], "f_pool_68": p68["f_clean_68"], "f_pool_95": p95["f_clean_68"],
                    "n_reference": p68["n_reference"], "expected_from_garbage": p68["expected_from_garbage"],
                    "excess_hits": p68["excess"],
                    "f_by_circuit": {b: {"reference": circ[f"{b}_{c}"]["f_clean_reference"],
                                         "reference_68": circ[f"{b}_{c}"]["f_clean_reference_68"],
                                         "reference_95": circ[f"{b}_{c}"]["f_clean_reference_95"],
                                         "mixture": circ[f"{b}_{c}"]["f_clean_mixture"],
                                         "mixture_68": circ[f"{b}_{c}"]["f_clean_mixture_68"]} for b in BASE_IDS},
                    "null_ratio": float(np.dot(nulls, ws) / np.sum(ws)),
                    "null_ratio_per_circuit": dict(zip(BASE_IDS, nulls)),
                    "n_pulses_per_circuit": {b: mans[f"{b}_{c}"]["dd"]["n_pulses"] for b in BASE_IDS},
                    "c6_relative_deviation_information": {b: circ[f"{b}_{c}"]["c6_relative_deviation"] for b in BASE_IDS},
                    "distance_histograms": {b: circ[f"{b}_{c}"]["distance_histogram"] for b in BASE_IDS},
                    "accepted": {b: circ[f"{b}_{c}"]["accepted"] for b in BASE_IDS},
                    "reference_hits": {b: circ[f"{b}_{c}"]["reference_hits"] for b in BASE_IDS}}
    c0 = cells["T0"]
    c0.update({"R": 1.0, "R_95": None, "class": None, "R_bootstrap_95": None})
    for c in DD_CELLS:
        cr = cell_ratio(cells[c]["n_reference"], cells[c]["expected_from_garbage"], c0["n_reference"], c0["expected_from_garbage"])
        boot = GD.bootstrap_ratio(rows_by[c], rows_by["T0"])
        cells[c].update({"R": cr["R"], "R_95": cr["R_95"], "R_branch": cr["branch"], "R_bootstrap_95": boot["R_95"],
                         "R_bootstrap": boot, "R_over_null": (None if cr["R"] is None else cr["R"] / cells[c]["null_ratio"]),
                         "class": classify(cr["R_95"])})
    classes = {c: cells[c]["class"] for c in DD_CELLS}
    R1 = GD.qualifies(cells["T3"]["R"], cells["T3"]["R_95"])
    r2 = r2_verdict(cells["T3"]["excess_hits"], c0["excess_hits"])
    rnc = load_json(p(R_NC_JSON))
    fhi = corrected_clean_fraction(p95_by["T3"], rnc["r_nc"], rnc["pooled_r_ci95"])
    repl = {"R1": R1, "R2": r2["consistent"], "R2_detail": r2, "C1": classes["T1"] == "COLLAPSED",
            "adopted": ("T3" if R1 else "T0"), "qualifying": (["T3"] if R1 else []),
            "signed_bar_f_hit": GD.signed_bar(cells["T3"]["f_pool_95"]),
            "signed_bar_f_hat_ideal": GD.signed_bar(fhi["f_hat_ideal_interval"]), "f_hat_ideal_T3": fhi,
            "rule": R_VERDICTS}
    Rmap = {c: cells[c]["R"] for c in DD_CELLS}
    mech = {"classes": classes, "reading": reading(classes),
            "M3_over_M2": log_ratio_z(cells["M3"]["excess_hits"], cells["M2"]["excess_hits"]),
            "M3_over_T3": log_ratio_z(cells["M3"]["excess_hits"], cells["T3"]["excess_hits"]),
            "prediction_matches": prediction_matches(classes, Rmap), "rule": READING_RULE,
            "prediction_table": PREDICTION_TABLE}

    # ---- trains
    trains = None
    if ro and all(t in by_id for t in TRAIN_IDS):
        trains = analyse_trains(by_id, ro, patch, prereg_rec, index.get("hot_qubits") or [])
        if dry:
            trains["dry_run_note"] = ("Aer has no coherent pulse error: the dry-run trains sit at the readout floor plus the "
                                      "snapshot's incoherent x error; the epsilon fit reads noise")

    # ---- K0 block
    k0 = load_json(p(K0N.K0_JSON))
    k0blk = load_json(p(K0N.OUT_JSON))
    k0_bad = K0N.check_block(k0blk, k0)

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
    reserve = load_json(p(prep, "reserve.json")) if os.path.exists(p(prep, "reserve.json")) else None

    # ---- criteria
    R_ = GateResult(out, ("one-job replication of the XY4 gain (T0 vs T3) and of the context-aware collapse (T1) with four "
                          "mechanism cells and four pulse-train pubs on ibm_kingston (measurement gate)")
                    + (" -- DRY RUN" if dry else ""))
    k1_info = {}
    if dry:
        R_.add("D1 preregistration committed before the submission", "n/a (dry run)", "device run only", True)
        R_.add("D2 one job DONE, usage <= 45 s, estimate <= 36 s, 20 x 6000 counts, DD/twirling off, B reserve",
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
        R_.add("D1 preregistration committed before the submission; prereg = submission fingerprint; retrieval "
               "fingerprint recorded (a move is information)",
               f"prereg commit {tc}, added {ha and ha[:7]} {ta}, submitted {sub}; fingerprints equal {fp_ok}; retrieval "
               f"match {k1_info['retrieval_match']}", "commit < submission, equal fingerprints, retrieval recorded",
               before and fp_ok and ret_fp is not None and not missing_keys)
        est = ((session.get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s")
        so = session.get("sampler_options") or {}
        opts_ok = (so.get("dynamical_decoupling") == {"enable": False}
                   and so.get("twirling") == {"enable_gates": False, "enable_measure": False})
        shots_ok = len(records) == N_PUBS and all(int(sum(c.values())) == SHOTS for _m, c in records)
        res_ok = bool(reserve and reserve.get("fits") is True
                      and reserve["remaining_s_at_check"] - MAX_USAGE_S >= max(B_RESERVE_S, K1_RESERVE_FACTOR * reserve["K1_estimate_s"]))
        d2 = (len(job_ids) == 1 and statuses == ["DONE"] and usage_s is not None and usage_s <= MAX_USAGE_S
              and est is not None and est <= MAX_ESTIMATE_S and shots_ok and opts_ok and res_ok)
        R_.add("D2 one job DONE, usage_s <= 45, preflight estimate <= 36 s, 20 counts files x 6000, DD off and twirling off, "
               "reserve.json with remaining - 45 >= max(300, 1.3 x K1 estimate)",
               f"jobs {job_ids} {statuses}, usage {usage_s} s, estimate {_f(est, '{:.2f}')} s, counts ok {shots_ok}, options "
               f"off {opts_ok}, reserve {None if not reserve else round(reserve['after_A_s'], 1)} s after A vs need "
               f"{None if not reserve else round(reserve['B_need_s'], 1)} s: {res_ok}", "all hold", d2)
    if dry:
        nz = sum(1 for v in (dry_k3_block or {}).get("per_qubit", {}).values()
                 if abs(v["d00"]["z"]) <= 3 and abs(v["d11"]["z"]) <= 3)
        R_.add("D3 readout (dry run: agreement with the snapshot's readout model, prompts/21a; the device criterion >= 0.9 "
               "is evaluated only on device counts)",
               f"{nz}/12 qubits with |z| <= 3; min diagonal {_f(None if not ro else ro['min_diagonal'])} (information); live "
               f"expectation min {ro_live['min']:.4f} (qubit {ro_live['min_qubit']})",
               f"all 12 within 3 binomial sigma; live expectation >= {DIAG_MIN}",
               bool(dry_k3_block and dry_k3_block["ok"]) and nz == len(patch) and ro_live["min"] >= DIAG_MIN)
    else:
        R_.add("D3 readout confusion of the patch (all-0 / all-1 pubs): smallest diagonal",
               None if not ro else round(ro["min_diagonal"], 4), f">= {DIAG_MIN}", bool(ro) and GK.device_k3(ro["min_diagonal"]))
    R_.add("D4 decoder round trip over every accepted string of the 14 coarse pubs",
           f"{rt['mismatches']} mismatches over {rt['distinct_accepted_strings']} strings", "0", rt["mismatches"] == 0)
    d5_rows = {}
    for cid in coarse_ids:
        m = mans[cid]
        ex = m["exactness"]
        chk = (m["dd"].get("checks") or {})
        ok = (ex["ok"] and ex["max_abs_delta"] < 1e-10 and ex["leakage"] < 1e-9
              and (m.get("schedule_info") or {}).get("method") == "alap"
              and m["dd"].get("pulse_cost_nats") is not None and m["dd"].get("null_ratio") is not None
              and set(m["ops"]) <= set(("rz", "sx", "x", "cz", "delay", "measure", "barrier")))
        if m["dd"]["cell"] != "T0":
            ok = ok and chk.get("ok") is True and chk.get("statevector_max_abs_delta_up_to_phase", 1) < 1e-10 \
                and chk.get("duration_ok") is True and chk.get("windows_ok") is True and chk.get("ops") == m["ops"]
        d5_rows[cid] = ok
    reuse = index.get("reuse") or {}
    reuse_ok = (all((reuse.get(f"{b}_{c}") or {}).get("byte_for_byte") for b in BASE_IDS for c in ("T0", "T1", "T3"))
                if index.get("patch_reproduced") else all(reuse.get(f"{b}_{c}") is not None for b in BASE_IDS for c in ("T0", "T1", "T3")))
    ident_ok = all(v.get("ok") for v in (index.get("identities") or {}).values()) and len(index.get("identities") or {}) == len(BASE_IDS)
    train_ok = True
    for tid in TRAIN_IDS:
        m = mans[tid]
        nn = TRAIN_N[tid]
        alt = tid.startswith("train_XpXm")
        want = []
        for j in range(nn):
            want += (["rz(-1pi)", "x", "rz(+1pi)"] if (alt and j % 2 == 1) else ["x"])
        want.append("measure")
        train_ok = train_ok and m["train"]["per_qubit_ops"] == want and m["train"]["n_pulses"] == nn \
            and set(m["ops"]) <= {"x", "rz", "measure", "barrier"} and m["logical_to_physical"] == list(patch)
    d5 = all(d5_rows.values()) and reuse_ok and ident_ok and train_ok
    R_.add("D5 circuits: 14/14 coarse circuits pass dd_checks (i)-(v) and dd_exactness; T0/T1/T3 byte-identical to H0_ddtest "
           "when patch_reproduced; the P3 identities hold; the train pubs' op lists are the declared trains; kingston basis",
           f"{sum(d5_rows.values())}/{len(d5_rows)} circuits; reuse ok {reuse_ok} (patch reproduced "
           f"{index.get('patch_reproduced')}); identities ok {ident_ok}; trains ok {train_ok}; max |d| "
           f"{max(mans[c]['exactness']['max_abs_delta'] for c in coarse_ids):.1e}", "all hold", d5)
    if dry:
        R_.add("D6 dry-run gate PASS on the day's build", "n/a (this is the dry run)", "device run only", True)
    else:
        dp = p("validation", "H0_ddrep_dryrun.json")
        dj = load_json(dp) if os.path.exists(dp) else {}
        same_build = ((dj.get("data") or {}).get("index_created") == index["created"]
                      and ((dj.get("data") or {}).get("calibration_prereg") or {}).get("fingerprint") == pre["calibration"]["fingerprint"])
        R_.add("D6 validation/H0_ddrep_dryrun.json PASS on the day's build", f"{dj.get('status')} (same build {same_build})",
               "PASS, same index and prereg fingerprint", dj.get("status") == "PASS" and same_build)

    D = {"cells": {c: {k: v for k, v in cells[c].items()} for c in CELLS}, "replication": repl, "mechanism": mech,
         "trains": trains, "k0_2x3_nogo": k0blk}
    miss = completeness(D)
    rc = recompute(D)
    eq = (rc["classes"] == classes and rc["R1"] == repl["R1"] and rc["R2"] == repl["R2"] and rc["C1"] == repl["C1"]
          and rc["reading"] == mech["reading"])
    R_.add("D7 replication, mechanism, trains and k0_2x3_nogo complete; classes, R1, R2, C1 and the reading recomputed from "
           "the recorded intervals; k0 fields equal validation/K0_2x3_2x4.json's",
           f"missing {miss}; recomputed equal {eq}; k0 mismatches {k0_bad}", "complete, equal, none",
           not miss and eq and not k0_bad)
    if args.skip_tests:
        checks = {"skipped": True, "ok": None}
        R_.add("D8 pytest -q tests and scripts/check_package.py", "n/a (--skip-tests)", "all pass", dry)
    else:
        checks = G.run_checks(False)
        R_.add("D8 pytest -q tests and scripts/check_package.py",
               f"pytest: {checks.get('pytest_summary')}; check_package rc {checks.get('check_package_returncode')}",
               "all pass", checks["ok"])

    R_.data = {
        "what_pass_means": ("preregistered, measured, verified, consistent; there is no criterion on R1, R2, C1, the classes "
                            "or the mechanism reading"),
        "dry_run": dry, "versions": versions(), "prompt": "prompts/32_2x2_dd_replication_and_T1_mechanism.md (part A)",
        "owner_decision": "data/owner_decision_20261006_A_then_B.md",
        "prereg": rel(pre_path) if os.path.isabs(pre_path) else pre_path, "prereg_created": pre["created"],
        "prereg_commit": pre["commit"], "prereg_keys_missing": missing_keys, "offline_prototype": pre.get("offline_prototype"),
        "calibration_prereg": pre["calibration"], "patch": patch, "patch_reproduced": index.get("patch_reproduced"),
        "index_created": index["created"], "hot_qubits": index.get("hot_qubits"), "identities": index.get("identities"),
        "reuse": reuse, "pubs": pre["pubs"], "execution_estimate_prereg_s": pre["execution_estimate"]["total_execution_s"],
        "counts_dir": rel(cdir), "session_file": rel(spath) if session else None,
        "live": {"job_ids": job_ids, "statuses": statuses, "usage_s": usage_s,
                 "submission_fingerprint": (session or {}).get("calibration_fingerprint"),
                 "prereg_fingerprint_match": (session or {}).get("prereg_fingerprint_match"),
                 "retrieval_fingerprint": ret_fp, "retrieval_diff": ret_diff,
                 "preflight_estimate_s": (((session or {}).get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s"),
                 "sampler_options": (session or {}).get("sampler_options"), "account": acct, "D1": k1_info},
        "reserve": reserve,
        "readout": ro, "readout_expected_live": ro_live, "dry_run_K3": dry_k3_block,
        "circuits": circ, "roundtrip": rt, **D,
        "class_rule": CLASS_RULE, "power_prereg": pre["power"],
        "dry_run_note": ("Aer cannot show a DD gain: its relaxation on a delay is Markovian, so the dry-run ratios sit near the "
                         "null values exp(-S_DD) and are path checks, not predictions (P10 of prompts/24); the train pubs on "
                         "Aer sit at the readout floor plus the snapshot's incoherent x error (no coherent pulse error)") if dry else None,
        "checks": checks,
    }
    R_.runtime_s = time.time() - t0
    path = R_.save()
    saved = load_json(path)
    name = (f"{out}.md" if dry else "H0_ddrep_ibm_kingston.md")
    write_report(name, report_text(saved, R_))
    print(R_.criteria_table())
    print(f"status {saved['status']}; " + "; ".join(
        f"{c} f {_f(cells[c]['f_pool'])} R {_f(cells[c]['R'], '{:.3f}')} {_iv(cells[c]['R_95'], '{:.3f}')} {cells[c].get('class')}"
        for c in CELLS) + f"; R1 {repl['R1']} R2 {repl['R2']} C1 {repl['C1']}; reading {mech['reading']}")
    return 0 if saved["status"] == "PASS" else 1


def report_text(saved, R_):
    from skqd.report import md_table
    D = saved["data"]
    dry = D["dry_run"]
    live = D["live"]
    rp = D["replication"]
    mc = D["mechanism"]
    rows = []
    for c, v in D["cells"].items():
        rows.append([c, sum(v["accepted"].values()), v["n_reference"], f"{v['expected_from_garbage']:.2f}",
                     f"{v['excess_hits']:.1f}", f"{_f(v['f_pool'])} {_iv(v['f_pool_95'])}", _f(v["R"], "{:.3f}"),
                     _iv(v["R_95"], "{:.3f}"), _iv(v.get("R_bootstrap_95"), "{:.3f}"), f"{v['null_ratio']:.3f}",
                     v.get("class") or "-", sum(v["n_pulses_per_circuit"].values())])
    crow = []
    for c, v in D["cells"].items():
        for b, x in v["f_by_circuit"].items():
            crow.append([c, b, v["accepted"][b], v["reference_hits"][b], f"{_f(x['reference'])} {_iv(x['reference_95'])}",
                         f"{_f(x['mixture'])} {_iv(x['mixture_68'])}", _f(v["c6_relative_deviation_information"][b], "{:.3f}"),
                         v["n_pulses_per_circuit"][b]])
    prow = []
    for c in ("T1", "M1", "M2", "M3", "M4"):
        prow.append([c, mc["classes"][c]] + [f"{mc['prediction_table'][c][h]} ({'yes' if mc['prediction_matches'][h]['cells'][c] else 'no'})"
                                             for h in ("H_A", "H_B", "H_D")])
    tr = D.get("trains") or {}
    trow = []
    for q, v in sorted((tr.get("per_qubit") or {}).items(), key=lambda kv: int(kv[0])):
        trow.append([q] + [f"{v['P1'][t]:.4f}" for t in TRAIN_IDS] +
                    [f"{v['epsilon']:.4f} {_iv(v['epsilon_68'])}", f"{v['c_per_pulse']:.2e} {_iv(v['c_68'], '{:.1e}')}",
                     f"{v['x_error_record']:.2e}", _f(v.get("c_over_x_error"), "{:.2f}")])
    rd = tr.get("readings") or {}
    k0 = D["k0_2x3_nogo"]
    acct = live.get("account") or {}
    ub = (acct.get("before") or {}).get("usage") or {}
    ua = (acct.get("after") or {}).get("usage") or {}
    k1 = live.get("D1") or {}
    r2 = rp["R2_detail"]
    title = ("dry run (local Aer on the FakeKingston snapshot; a path check, not a prediction)" if dry else "ibm_kingston")
    if D.get("offline_prototype"):
        title += " -- OFFLINE PROTOTYPE on the committed 2026-10-02 record"
    return f"""# Gate {saved['gate']} -- XY4 replication and the T1-collapse mechanism, {title}

**Status: {saved['status']}** -- `scripts/gate_H0_ddrep.py --stage assemble --counts {D['counts_dir']}{' --dry-run' if dry else ''} --out {saved['gate']}`.
Runtime {saved['runtime_s']:.0f} s.  Every number below is computed by the script from the raw counts and from `{D['prereg']}` and is
stored in `validation/{saved['gate']}.json`.  Prompt in force: `{D['prompt']}`; owner decision `{D['owner_decision']}`.

## 0. What PASS means

{D['what_pass_means']}.{(' ' + D['dry_run_note'] + '.') if D.get('dry_run_note') else ''}

## 1. Preregistration

`{D['prereg']}`, written {D['prereg_created']} at commit `{D['prereg_commit']}` on the patch record `{D['calibration_prereg']['path']}`
(fingerprint `{D['calibration_prereg']['fingerprint']}`).  Patch {D['patch']} (reproduced: {D['patch_reproduced']}); hot qubits of M4
{D['hot_qubits']}; {len(D['pubs'])} pubs x {SHOTS} shots; execution estimate {D['execution_estimate_prereg_s']:.2f} s.

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

## 3. The seven cells

{md_table(["cell", "accepted", "ref hits", "garbage exp.", "excess X", "f_pool [95 %]", "R = X_i/X_0", "R 95 %",
           "R bootstrap 95 %", "null e^-S_DD", "class", "pulses (2 circuits)"], rows)}

Per circuit:

{md_table(["cell", "circuit", "accepted", "ref hits", "f reference [95 %]", "f mixture [68 %]", "C6 dev (info)", "pulses"], crow)}

{D['class_rule']}

## 4. Replication verdicts (P6)

- R1 gain replicated (T3 qualifies under the H0_ddtest rule): **{rp['R1']}**.
- R2 magnitude consistent: **{rp['R2']}** -- ln R_new {_f(r2.get('lnR_new'))} vs ln R_old {_f(r2.get('lnR_old'))}, |difference|
  {_f(None if r2.get('difference') is None else abs(r2['difference']))} against the tolerance {_f(r2.get('tolerance'))}.
- C1 collapse replicated (T1 COLLAPSED): **{rp['C1']}**.
- Signed bar on T3 (information): on f_hit **{rp['signed_bar_f_hit']}**; on f_hat_ideal = f_hit / r_nc ({rp['f_hat_ideal_T3']['r_nc']:.4f})
  **{rp['signed_bar_f_hat_ideal']}** (f_hat_ideal {_f(rp['f_hat_ideal_T3']['f_hat_ideal'])}, 95 % {_iv(rp['f_hat_ideal_T3']['f_hat_ideal_interval'])}).

## 5. Mechanism (P5)

{md_table(["cell", "observed class", "H_A predicts (match)", "H_B predicts (match)", "H_D predicts (match)"], prow)}

Reading (preregistered rule): **{mc['reading']}**.  Cells matched per hypothesis: """ + ", ".join(
        f"{h} {v['n_match']}/5" for h, v in mc["prediction_matches"].items()) + f""".
M3 vs M2 (first-order compensation on the runtime timing): ln(R_M3/R_M2) = {_f(mc['M3_over_M2']['lnR'])} +- {_f(mc['M3_over_M2']['sigma'])},
z = {_f(mc['M3_over_M2']['z'], '{:.2f}')} (compensation matters: {mc['M3_over_M2']['compensation_matters']}).  M3 vs T3 (information):
ln = {_f(mc['M3_over_T3']['lnR'])} +- {_f(mc['M3_over_T3']['sigma'])}.

## 6. Pulse trains (P4)

{md_table(["qubit", "P1 XX-8", "P1 XX-32", "P1 XX-128", "P1 XpXm-128", "epsilon (rad) [68 %]", "c per pulse [68 %]",
           "x_error record", "c / x_error"], trow) if trow else 'not analysed'}

Readings: H_A pattern {rd.get('H_A')} (epsilon >= 0.01 on {rd.get('n_qubits_eps_ge_0.01')} qubits, XX-128 - XpXm-128 > 0.05 on
{rd.get('n_qubits_XX128_minus_XpXm128_gt_0.05')}); H_B pattern {rd.get('H_B')}; H_D pattern {rd.get('H_D')} (c > 3 x_error on
{rd.get('qubits_c_above_3_x_error')}, hot {rd.get('hot_qubits')}).  {tr.get('dry_run_note') or ''}

Rule: {tr.get('rule')}

## 7. The 2x3 IBM NO-GO (K0, recorded with this gate)

{k0['verdict']}: routed CZ {k0['routed_cz']}, ALAP {k0['alap_duration_s'] * 1e6:.1f} us, f_gates on the layout {k0['f_gates_layout']:.3e},
f_idle_aware {k0['f_idle_aware_echo']:.3e} (echo) / {k0['f_idle_aware_transferred']:.3e} (T2*), garbage reference hits
{k0['garbage_reference_hits_per_circuit']['value']:.4f} per circuit at {k0['garbage_reference_hits_per_circuit']['shots']} shots
(`reports/K0_2x3_ibm_heron_nogo.md`).  {k0['closing']}

## 8. Readout

Smallest confusion diagonal {_f((D['readout'] or {}).get('min_diagonal'))}; preregistered live expectation min
{D['readout_expected_live']['min']:.4f} (qubit {D['readout_expected_live']['min_qubit']}).

## 9. Honest limits

- One job, one patch, one calibration content; drift between submission and retrieval is reported, not corrected.
- The classes are preregistered thresholds on Poisson intervals, not fits; the reading rule names a hypothesis class, not a
  microscopic cause.
- The null ratios e^-S_DD assume the record's x error for every inserted pulse, and the record's x error is aliased to sx.
- The train fit assumes a coherent over-rotation epsilon plus an incoherent per-pulse cost on a floor anchored at XX-8; other
  coherent errors (axis tilt, detuning during the train) enter epsilon.
- Two k = 1 circuits are not a family-level statement.

## 10. Criteria

{R_.criteria_table()}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("reserve", "predict", "prereg-md", "assemble"))
    ap.add_argument("--prep", default=PREP)
    ap.add_argument("--prereg", default=None)
    ap.add_argument("--counts", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--offline", action="store_true", help="predict: offline prototype (no live D9 read)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    return {"reserve": stage_reserve, "predict": stage_predict, "prereg-md": stage_prereg_md,
            "assemble": stage_assemble}[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
