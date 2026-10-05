#!/usr/bin/env python3
"""
Gate CF_traj (prompts/28 Part A, A3; completed and re-assembled under prompts/29 Part A'): the decisive
trajectory test of the A6 reference-hit excess, and the near-clean correction r_nc of the reference-hit
statistic.

Reads the raw trajectory chunks written by scripts/cf_trajectories.py (data/cf_trajectories/<id>[__xx]/),
the A4 counting-control counts (data/cf_trajectories/control_xx/), the A0 timing record, the A6 dry-run
counts (data/hardware/Q0P_2x3_dryrun/) and the phase-only check (data/quantinuum/a6_phase_error_check.json),
audits the A6 Aer path, runs the package checks, and writes validation/CF_traj.json + reports/CF_traj.md
through skqd.report.GateResult (no typed numbers).

Definitions (prompts/28; planner's labels, not manual terms):
  g0   = (1 - 15/16 p2)^n_zz (1 - 3/4 p1)^n_1q        probability of no gate-error event
  f0'  = g0 x readout survival of the reference string  (predict.json aer_channel_no_error_probability)
  h_ref = <p_tau(ref)> over FAULTY trajectories (post-readout)
  f_hit^traj = f0' + (1 - f0') h_ref / p_ref,  rho_ref = f_hit^traj / f0'
  f_T^traj   = f0' + (1 - f0') <sum_{T_c} p_tau> / sum_{T_c} p_c,  rho_T = f_T^traj / f0'
  f_eff(s)   = f0' + (1 - f0') <p_tau(s)> / p_c(s)
  T_c = {s : p_c(s) >= 1e-3, s != ref};  benign = TV(sector-normalised p_tau, p_c) < 1e-3 (pre-readout)
Intervals: 95 % bootstrap percentile over trajectories (B = 2000, seed 2028); means also with s.e.
prompts/29 (the ideal-sample fraction; rho_T kept as information, its STOP retired):
  b(delta)       = fraction of FAULTY trajectories with TV_pre < delta,  delta in {1e-3, 1e-2, 0.03}
  f_ideal(delta) = f0' + (1 - f0') b(delta),  r(delta) = f_hit^traj / f_ideal(delta)
  pooled (k = 1 arms B0_ref25_k1 + B1_ref57_k1 at the Stage E/P v3 shots 800 / 800):
    f_hit^pool = sum_c N_c p_ref,c f_hit,c / sum_c N_c p_ref,c   (the expectation of pooled_reference_string_test
                 without its garbage term), f_ideal^pool = sum_c N_c f_ideal,c / sum_c N_c,
    r^pool(delta) = f_hit^pool / f_ideal^pool;  bootstrap stratified by arm (one generator, seed 2028)
  r_nc = the upper end of the 95 % bootstrap interval (97.5th percentile) of r^pool(1e-3)
         -> data/cf_trajectories/r_nc.json
  floor-theorem check: min over S99 of f_eff(s) / f_ideal(1e-3) >= 0.95 on every arm
  k = 4 mixture bias: clean_fraction_mixture (readout factor 1.0) on N [f0' p_c + (1 - f0') <p_tau>_post]
         at N = 200 and 2000; bias = (w-implied f) / f_ideal(1e-3) of the same arm
  return (2.1): post-readout p_tau(ref) > 0.5; TV "machine zero" = TV_pre < 1e-12

Run in the isolated venv (the A6-path audit reads the frozen pytket circuits):
  ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/gate_CF_traj.py [--skip-checks]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402

import cf_trajectories as cf  # noqa: E402

GATE = "CF_traj"
TITLE = ("Pauli-trajectory decomposition of the A6 reference-hit excess and the near-clean correction r_nc "
         "(prompts/28 Part A, re-assembled under prompts/29 Part A')")
WHAT_PASS_MEANS = (
    "the excess of reference-string hits over the fault-free expectation in the A6 Aer run is reproduced by "
    "an independent Pauli-trajectory decomposition of the same channel on the same circuit, and a bit-flip-only "
    "control gives the fault-free count; the reference-string estimator therefore measures the "
    "clean-plus-near-clean fraction, not the fault-free fraction.  Under prompts/29 the completed run also fixes "
    "the ratio r_nc of the reference-hit fraction to the ideal-sample fraction f_ideal(1e-3) (A6 gate-noise "
    "channel only), checks the floor theorem on every arm and measures the k = 4 mixture estimator's bias.  "
    "PASS says nothing about any device.")
CIRC = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
DRYRUN = os.path.join(ROOT, "data", "hardware", "Q0P_2x3_dryrun")
PREDICT = os.path.join(ROOT, "data", "quantinuum", "q0p_stages", "predict.json")
PHASE = os.path.join(ROOT, "data", "quantinuum", "a6_phase_error_check.json")
CODING_PY = "/home/digimonk/anaconda3/envs/coding/bin/python"
VENV_PY = os.path.join(os.path.expanduser("~"), ".local", "share", "su2qc-quantinuum", "venv", "bin", "python")
PINS_EXPECTED = {"python": "3.12.14", "qiskit": "2.5.2", "qiskit-aer": "0.17.2",
                 "qiskit-ibm-runtime": "0.49.0", "numpy": "2.5.2", "scipy": "1.18.0"}
# prompts/28 A2: arms, planned K and seeds (the xx arm's seed is the executor's choice: A4 gives none)
ARMS = {"B0_ref25_k1": {"channel": "depol", "K": 720, "seeds": [101, 102, 103]},
        "B1_ref57_k1": {"channel": "depol", "K": 240, "seeds": [201]},
        "B0_ref25_k4": {"channel": "depol", "K": 240, "seeds": [301]}}
XX_ARM = {"id": "B0_ref25_k1", "channel": "xx", "K": 120, "seeds": [401]}
A6_SHOTS_PER_K1 = 140                 # the A6 dry run (predict.json dryrun.jobs)
PHASE_SHOTS = 40
CONTROL_SHOTS = 280
MARGIN = 0.7                          # rule D3'-R margin
RHO_T_STOP = 1.5                      # prompts/28 STOP, retired by prompts/29 (f_T withdrawn): information only
# prompts/29 Part A'
DELTAS = (1e-3, 1e-2, 0.03)           # A'2: TV thresholds of b(delta)
DELTA_BAR = 1e-3                      # 3(1): the bar's referent is f_ideal(1e-3)
R_NC_STOP = 1.3                       # A'3: STOP (planner) if r_nc > 1.3
FLOOR_MIN = 0.95                      # A'3 C4': min_S99 f_eff / f_ideal >= 0.95 on every arm
MIX_BAND = (0.67, 1.5)                # A'3: STOP if the k = 4 mixture bias lies outside
MIX_N = (200, 2000)                   # A'2: the mixture estimator at N = 200 and N = 2000
MIX_ARM = "B0_ref25_k4"
POOL_SHOTS = {"B0_ref25_k1": 800, "B1_ref57_k1": 800}   # 3(3): Stage E/P v3 shots of the two k = 1 circuits
RETURN_P = 0.5                        # 2.1: a return has p_tau(ref) > 0.5
TV_ZERO = 1e-12                       # "TV exactly 0" read as machine zero
R_NC_PATH = os.path.join(ROOT, "data", "cf_trajectories", "r_nc.json")
A5_ENDS = {"star": ("result.json", "trajectories.json"), "echo": ("result_echo.json", "trajectories_echo.json")}
A5_K = 2000                           # A'1: K = 2000 at each T2 end
LOW_SIDE_SIGMAS = 3.0                 # prompts/28 C2: low-side failure by > 3 standard errors -> STOP
P_MIN = 0.05                          # C2: two-sided Poisson P >= 0.05
N_BOOT, BOOT_SEED = 2000, 2028
PROMPT_C5_LITERAL_1Q = 3053           # prompts/28 C5 as typed; compared, see c5 notes


def load_json(p):
    with open(p) as fh:
        return json.load(fh)


def two_sided_poisson_p(k: int, mu: float) -> float:
    from scipy.stats import poisson

    return float(min(1.0, 2.0 * min(poisson.cdf(k, mu), poisson.sf(k - 1, mu))))


def poisson_band(mu: float, conf: float = 0.95) -> list:
    from scipy.stats import poisson

    a = (1.0 - conf) / 2.0
    return [int(poisson.ppf(a, mu)), int(poisson.ppf(1.0 - a, mu))]


def clopper_pearson(k: int, n: int, conf: float = 0.95) -> list:
    from scipy.stats import beta

    a = (1.0 - conf) / 2.0
    lo = 0.0 if k == 0 else float(beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a, k + 1, n - k))
    return [lo, hi]


def ival(point, boot):
    boot = np.asarray(boot, float)
    return {"value": float(point), "se_boot": float(np.std(boot, ddof=1)),
            "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]}


def ref_hits(counts_rec: dict, ref_int: int) -> int:
    from skqd.reference_sim import bits_to_int, qiskit_key_to_bits

    return int(sum(v for k, v in counts_rec["counts"].items() if bits_to_int(qiskit_key_to_bits(k)) == int(ref_int)))


# =========================================================================== prompts/29: f_ideal, r, r_nc
def delta_tag(d: float) -> str:
    """JSON key suffix of a TV threshold: 1e-3 -> 'd1e-03'."""
    return f"d{float(d):.0e}"


def ideal_fraction(f0: float, w, h, tv, p_ref: float, deltas=DELTAS) -> dict:
    """prompts/29 2.2 for trajectory weights w (sum 1):
    b(delta) = sum_tau w_tau [TV_pre(tau) < delta]; f_ideal(delta) = f0' + (1 - f0') b(delta);
    f_hit = f0' + (1 - f0') <p_tau(ref)>_post / p_ref; r(delta) = f_hit / f_ideal(delta)."""
    w = np.asarray(w, float)
    f_hit = f0 + (1.0 - f0) * float(w @ np.asarray(h, float)) / p_ref
    out = {"f_hit": f_hit}
    tv = np.asarray(tv, float)
    for d in deltas:
        t = delta_tag(d)
        b = float(w @ (tv < d))
        fi = f0 + (1.0 - f0) * b
        out[f"b_{t}"] = b
        out[f"f_ideal_{t}"] = fi
        out[f"r_{t}"] = f_hit / fi
    return out


def pooled_ratio(parts: list, deltas=DELTAS, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """The pooled r(delta) of the k = 1 arms (prompts/29 3(1)).

    parts = [{"id", "f0", "p_ref", "h", "tv", "shots"}, ...].  The device statistic is
    pooled_reference_string_test: hits summed over circuits / sum_c N_c p_ref,c, whose expectation is
    f_hit^pool = sum_c N_c p_ref,c f_hit,c / sum_c N_c p_ref,c; the referent is the pooled shot fraction
    f_ideal^pool = sum_c N_c f_ideal,c / sum_c N_c.  r^pool = f_hit^pool / f_ideal^pool.
    Bootstrap: trajectories resampled within each arm (stratified), one generator (seed) drawing the arms'
    multinomial weights in the order given."""
    rng = np.random.default_rng(seed)
    Ws = [rng.multinomial(len(p["h"]), np.full(len(p["h"]), 1.0 / len(p["h"])), size=n_boot) / len(p["h"])
          for p in parts]
    Nh = np.array([float(p["shots"]) * float(p["p_ref"]) for p in parts])
    Nf = np.array([float(p["shots"]) for p in parts])

    def pool(ws):
        per = [ideal_fraction(p["f0"], w, p["h"], p["tv"], p["p_ref"], deltas) for p, w in zip(parts, ws)]
        fh = float(Nh @ [q["f_hit"] for q in per]) / Nh.sum()
        out = {"f_hit": fh}
        for d in deltas:
            t = delta_tag(d)
            fi = float(Nf @ [q[f"f_ideal_{t}"] for q in per]) / Nf.sum()
            out[f"f_ideal_{t}"] = fi
            out[f"r_{t}"] = fh / fi
        return out

    point = pool([np.full(len(p["h"]), 1.0 / len(p["h"])) for p in parts])
    boots = [pool([W[i] for W in Ws]) for i in range(n_boot)]
    res = {}
    for k, v in point.items():
        arr = np.array([b[k] for b in boots])
        res[k] = {"value": float(v), "se_boot": float(np.std(arr, ddof=1)),
                  "ci95": [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))],
                  "one_sided_upper95": float(np.percentile(arr, 95.0))}
    return res


def return_classification(trajs: list, tv, p_return: float = RETURN_P, tv_zero: float = TV_ZERO) -> dict:
    """prompts/29 2.1: returns = faulty trajectories with post-readout p_tau(ref) > p_return; single-event
    returns by native Pauli label; TV of the returns (machine zero, < 1e-3, < 0.04)."""
    from collections import Counter

    tv = np.asarray(tv, float)
    h = np.array([t["p_ref_post"] for t in trajs])
    ret = h > p_return
    single = [t for t, r in zip(trajs, ret) if r and len(t["events"]) == 1]
    single_all = [t for t in trajs if len(t["events"]) == 1]
    single_x = [t for t in single_all if set(t["events"][0][4]) <= {"I", "X"}]
    n_ret = int(ret.sum())
    tvr = tv[ret]
    return {
        "definition": f"return = post-readout p_tau(ref) > {p_return}; TV = sector-normalised pre-readout distance",
        "K": len(trajs), "n_returns": n_ret,
        "share_of_h_ref_carried_by_returns": float(h[ret].sum() / h.sum()) if h.sum() > 0 else None,
        "n_single_event_returns": len(single),
        "single_event_returns_by_pauli": dict(sorted(Counter(t["events"][0][4] for t in single).items())),
        "single_event_returns_by_site_kind": dict(sorted(Counter(t["events"][0][2] for t in single).items())),
        "n_single_event_trajectories": len(single_all),
        "n_single_event_x_type_trajectories": len(single_x),
        "n_single_event_x_type_returns": int(sum(1 for t in single_x if t["p_ref_post"] > p_return)),
        "n_returns_tv_machine_zero": int(np.sum(tvr < tv_zero)), "tv_machine_zero_threshold": tv_zero,
        "n_returns_tv_below_1e-3": int(np.sum(tvr < 1e-3)),
        "n_returns_tv_below_0.04": int(np.sum(tvr < 0.04)),
        "fraction_returns_tv_machine_zero": float(np.mean(tvr < tv_zero)) if n_ret else None,
        "fraction_returns_tv_below_1e-3": float(np.mean(tvr < 1e-3)) if n_ret else None,
        "tv_of_returns_sorted": [float(x) for x in np.sort(tvr)],
    }


def mixture_expectation(f0: float, pc, P_mean, N: int) -> dict:
    """prompts/29 A'2: clean_fraction_mixture (readout factor 1.0) on the population mixture
    N [f0' p_c + (1 - f0') <p_tau>] (expected accepted counts per sector state, not a sample)."""
    from skqd.skqd import clean_fraction_mixture

    pc = np.asarray(pc, float)
    n = float(N) * (f0 * pc + (1.0 - f0) * np.asarray(P_mean, float))
    return clean_fraction_mixture(n, pc, len(pc), int(N), readout_factor=1.0)


def floor_theorem_check(feff_S99, pc_S99, point) -> dict:
    """prompts/29 2.4 (information beside C4'): f_eff(s) >= f_ideal(delta) (1 - 2 delta / p_c(s)) for every
    state; counted per delta over the S99 states with p_c > 0 (the bound is vacuous where 2 delta >= p_c)."""
    out = {}
    feff_S99, pc_S99 = np.asarray(feff_S99, float), np.asarray(pc_S99, float)
    m = pc_S99 > 0
    for d in DELTAS:
        t = delta_tag(d)
        bound = point[f"f_ideal_{t}"] * (1.0 - 2.0 * d / pc_S99[m])
        out[t] = {"n_states": int(m.sum()), "n_below_bound": int(np.sum(feff_S99[m] < bound)),
                  "n_bound_nonvacuous": int(np.sum(bound > 0)),
                  "min_margin_feff_minus_bound": float(np.min(feff_S99[m] - bound))}
    return out


# =========================================================================== arm statistics
def load_arm(cid, channel):
    chunks = cf.load_chunks(cid, channel)
    if not chunks:
        return None
    base = chunks[0][1]
    trajs = [t for _f, c in chunks for t in c["trajectories"]]
    return {"chunks": chunks, "base": base, "trajs": trajs}


def arm_statistics(cid: str, arm: dict, man: dict, A6: dict, predict: dict | None) -> dict:
    base, trajs = arm["base"], arm["trajs"]
    K = len(trajs)
    p2, p1 = A6["depolarizing_2q_rzz"], A6["depolarizing_1q_rx_ry"]
    p10, p01 = A6["readout_p1_given_0"], A6["readout_p0_given_1"]
    c = man["counts"]
    g0 = cf.no_error_probability(c["n_zz"], c["n_phasedx"], p2, p1)
    r_ref = cf.readout_survival(man["reference_bits"], p10, p01)
    f0 = g0 * r_ref
    checks = {"g0_vs_chunk_abs": abs(g0 - base["no_error_probability_g0"]),
              "readout_survival_vs_chunk_abs": abs(r_ref - base["readout_survival_reference"])}
    pred = (predict or {}).get("dryrun", {}).get("predictions", {}).get(cid)
    if pred:
        checks["f0_vs_predict_json_abs"] = abs(f0 - float(pred["aer_channel_no_error_probability"]))
    checks["f0_check_ok"] = all(v < 1e-12 for k, v in checks.items() if k.endswith("_abs"))
    sec = base["sector"]
    pc = np.asarray(base["ideal"]["p_c"], float)
    p_ref = float(man["p_reference"])
    tail = np.asarray(sec["tail_pos"], int)
    pT = float(pc[tail].sum())
    S99, S999 = np.asarray(sec["S99"], int), np.asarray(sec["S999"], int)
    h = np.array([t["p_ref_post"] for t in trajs])
    h_pre = np.array([t["p_ref_pre"] for t in trajs])
    tl = np.array([t["tail_post"] for t in trajs])
    tv = np.array([t["tv_pre"] for t in trajs])
    zo = np.array([t["z_only"] for t in trajs], bool)
    n2 = np.array([t["n_2q"] for t in trajs])
    n1 = np.array([t["n_1q"] for t in trajs])
    P = np.array([t["p_sector_post"] for t in trajs])
    benign = tv < cf.BENIGN_TV

    def derived(w):
        """All statistics for trajectory weights w (sum 1): the point (w = 1/K) and each bootstrap draw."""
        hm = float(w @ h)
        tm = float(w @ tl)
        Pm = w @ P
        f_hit = f0 + (1 - f0) * hm / p_ref
        f_T = f0 + (1 - f0) * tm / pT
        with np.errstate(divide="ignore", invalid="ignore"):
            feff = np.where(pc > 0, f0 + (1 - f0) * Pm / np.where(pc > 0, pc, 1.0), np.nan)
        r99, r999 = feff[S99] / f0, feff[S999] / f0
        tail99 = [s for s in S99 if pc[s] >= cf.TAIL_P_MIN]
        tail999 = [s for s in S999 if pc[s] >= cf.TAIL_P_MIN]
        out = {"h_ref": hm, "f_hit": f_hit, "rho_ref": f_hit / f0, "tail_mean": tm, "f_T": f_T,
                "rho_T": f_T / f0, "benign_fraction": float(w @ benign),
                "min_feff_over_f0_S99": float(np.nanmin(r99)), "min_feff_over_f0_S999": float(np.nanmin(r999)),
                "median_feff_over_f0_S99": float(np.nanmedian(r99)),
                "median_feff_over_f0_S999": float(np.nanmedian(r999)),
                "max_feff_over_f0_S99": float(np.nanmax(r99)), "max_feff_over_f0_S999": float(np.nanmax(r999)),
                "min_feff_over_f0_S99_tail": float(np.min(feff[tail99] / f0)) if tail99 else None,
                "max_feff_over_f0_S99_tail": float(np.max(feff[tail99] / f0)) if tail99 else None,
                "min_feff_over_f0_S999_tail": float(np.min(feff[tail999] / f0)) if tail999 else None,
                "max_feff_over_f0_S999_tail": float(np.max(feff[tail999] / f0)) if tail999 else None,
                "min_feff_over_fT_S99": float(np.nanmin(feff[S99]) / f_T),
                "n_S99_p_c_zero": int(np.sum(pc[S99] <= 0)), "n_S999_p_c_zero": int(np.sum(pc[S999] <= 0)),
                "n_S99_feff_below_margin_fT": int(np.sum(feff[S99] < MARGIN * f_T)),
                "_feff": feff}
        idl = ideal_fraction(f0, w, h, tv, p_ref)
        if abs(idl["f_hit"] - f_hit) > 1e-12:
            raise RuntimeError("ideal_fraction's f_hit differs from arm_statistics' f_hit")
        for d in DELTAS:
            t = delta_tag(d)
            for k in ("b", "f_ideal", "r"):
                out[f"{k}_{t}"] = idl[f"{k}_{t}"]
            out[f"min_feff_over_fideal_S99_{t}"] = float(np.nanmin(feff[S99]) / idl[f"f_ideal_{t}"])
        return out

    point = derived(np.full(K, 1.0 / K))
    rng = np.random.default_rng(BOOT_SEED)
    W = rng.multinomial(K, np.full(K, 1.0 / K), size=N_BOOT) / K
    boots = [derived(w) for w in W]
    stats = {}
    for key, v in point.items():
        if key.startswith("_") or v is None:
            continue
        stats[key] = ival(v, [b[key] for b in boots])
    stats["h_ref"]["se_analytic"] = float(np.std(h, ddof=1) / math.sqrt(K))
    stats["tail_mean"]["se_analytic"] = float(np.std(tl, ddof=1) / math.sqrt(K))
    nb = int(benign.sum())
    stats["benign_fraction"]["ci95_clopper_pearson"] = clopper_pearson(nb, K)
    feff = point["_feff"]
    per_state = []
    for rank, s in enumerate(S999):
        per_state.append({"pos": int(s), "int": int(sec["ints"][s]), "rank": rank, "in_S99": bool(rank < len(S99)),
                          "p_c": float(pc[s]), "mean_p_tau_post": float(P[:, s].mean()),
                          "feff_over_f0": float(feff[s] / f0),
                          "feff_over_fideal_1e-3": float(feff[s] / point[f"f_ideal_{delta_tag(DELTA_BAR)}"]),
                          "in_tail_class": bool(int(s) in set(tail.tolist())),
                          "is_reference": bool(int(s) == int(sec["ref_pos"]))})
    # exact decomposition (information): E[hit]/N = g0 * ideal post-readout p(ref) + (1 - g0) h_ref
    p_ref_post0 = float(base["ideal"]["p_ref_post_readout"])
    hit_exact = g0 * p_ref_post0 + (1 - g0) * point["h_ref"]
    hit_prompt = f0 * p_ref + (1 - f0) * point["h_ref"]
    # Z-only stratum (pre-readout: the phase-only check had no readout error)
    zs = {"n_z_only": int(zo.sum()), "fraction_z_only": float(zo.mean())}
    if zo.any():
        zs["h_Z"] = float(h_pre[zo].mean())
        zs["h_Z_se"] = float(np.std(h_pre[zo], ddof=1) / math.sqrt(zo.sum())) if zo.sum() > 1 else None
        # importance reweighting to the phase channel (Z events at the full event rate):
        # P_phase(tau) / P_depol(tau) = 5^n2 3^n1 for Z-type tau (2q: (e2/3)/(e2/15); 1q: e1/(e1/3))
        w = np.where(zo, 5.0 ** n2 * 3.0 ** n1, 0.0)
        zs["phase_channel_reweighted"] = {
            "mean_weight": float(w.mean()), "mean_weight_expected": 1.0,
            "h_faulty_unnormalised": float(np.mean(w * h_pre)),
            "h_faulty_self_normalised": float(np.sum(w * h_pre) / np.sum(w)),
            "note": ("information: the Z-only stratum of the depolarizing draws is weighted towards ONE event "
                     "(each extra Z event costs a factor 1/5 or 1/3), whereas the phase-only check draws Z events "
                     "at the full event rate; this importance-reweighted mean is the phase channel's faulty-shot "
                     "average estimated from the same trajectories (unbiased, high variance)")}
    events_hist = {"n_events": {str(k): int(np.sum(n2 + n1 == k)) for k in sorted(set((n2 + n1).tolist()))}}
    by_z = {"h_ref_z_only": float(h[zo].mean()) if zo.any() else None,
            "h_ref_not_z_only": float(h[~zo].mean()) if (~zo).any() else None,
            "tail_z_only": float(tl[zo].mean()) if zo.any() else None,
            "tail_not_z_only": float(tl[~zo].mean()) if (~zo).any() else None}
    chunks = [{"file": os.path.relpath(f, ROOT), "chunk": c["chunk"], "seed": c["seed"], "K": c["K"],
               "git_commit": c["git_commit"], "git_dirty_scripts_src": c["git_dirty_scripts_src"],
               "wall_s": c["wall_s"], "workers": c["workers"], "n_draws": c["n_draws"],
               "n_rejected_all_identity": c["n_rejected_all_identity"],
               "crosscheck_from_scratch_max_abs_dprob": next(
                   (t["crosscheck_from_scratch_max_abs_dprob"] for t in c["trajectories"]
                    if "crosscheck_from_scratch_max_abs_dprob" in t), None),
               "verify_json_p_sector_max_abs": c["ideal"]["p_sector_vs_verify_json_max_abs"],
               "aer_error_placement_after_gate": c["aer_error_placement_check"]["error_applied_after_gate"]}
              for f, c in arm["chunks"]]
    draws = sum(ch["n_draws"] for ch in chunks)
    rej = sum(ch["n_rejected_all_identity"] for ch in chunks)
    return {
        "id": cid, "channel": base["channel"], "K": K, "chunks": chunks,
        "n_zz": int(c["n_zz"]), "n_phasedx": int(c["n_phasedx"]), "p_ref": p_ref,
        "g0": g0, "readout_survival_reference": r_ref, "f0_prime": f0, "f0_checks": checks,
        "rejection": {"n_draws": draws, "n_rejected": rej, "fraction": rej / draws if draws else None,
                      "expected_g0": g0,
                      "z": (rej - draws * g0) / math.sqrt(draws * g0 * (1 - g0)) if draws else None},
        "tail_class": {"size": int(len(tail)), "p_Tc": pT, "p_min": cf.TAIL_P_MIN},
        "S99_size": int(len(S99)), "S999_size": int(len(S999)),
        "stats": stats,
        "hit_fraction_per_shot": {"prompt_formula_f0p_pref_plus_1mf0_h": hit_prompt,
                                  "exact_g0_pideal_post_plus_1mg0_h": hit_exact,
                                  "difference": hit_exact - hit_prompt,
                                  "f_hit_exact_decomposition": hit_exact / p_ref},
        "z_stratum": zs, "by_error_type": by_z, "event_counts": events_hist,
        "per_state_S999": per_state,
        "floor_theorem_S99": floor_theorem_check(feff[S99], pc[S99], point),
        "returns": return_classification(trajs, tv),
        "_h_se": float(np.std(h, ddof=1) / math.sqrt(K)), "_h_pre_mean": float(h_pre.mean()),
        "_h": h, "_tv": tv, "_P": P, "_pc": pc,
    }


def hamming_block(arm):
    trajs = arm["trajs"]
    m = np.mean([t["hamming_post"] for t in trajs], axis=0)
    ms = np.mean([t["hamming_post_sector"] for t in trajs], axis=0)
    return {"faulty_mean_weight_by_distance": [float(x) for x in m],
            "faulty_mean_in_sector_weight_by_distance": [float(x) for x in ms],
            "ideal_post_readout_weight_by_distance": arm["base"]["ideal"]["hamming_post_readout"]}


# =========================================================================== A6-path audit
def a6_path_audit(mans):
    """The circuit objects run_aer hands to AerSimulator.run for the two A6 circuits, the noise model and the
    simulator options of the dry run; a 1-shot noisy run's metadata (what Aer did with the circuit)."""
    from qiskit_aer import AerSimulator

    import quantinuum_submit as qs
    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn

    sess = load_json(os.path.join(DRYRUN, "session.json"))
    nm = qs.a6_noise_model()
    out = {"session": os.path.relpath(os.path.join(DRYRUN, "session.json"), ROOT),
           "session_git_commit": sess["git_commit"],
           "sampler": ("quantinuum_submit.run_aer: qcs = [skqd.circuits_qiskit.ir_to_qiskit(ir, n, measure=True)] "
                       "with ir from skqd.quantinuum_native.pytket_to_ir(frozen circuit); "
                       "AerSimulator(noise_model=a6_noise_model(), method='statevector', seed_simulator=aer_seed, "
                       "max_parallel_threads=threads).run(qcs, shots=shots) -- no transpile call on this path"),
           "aer_options": {"method": "statevector", "seed_simulator": [j["aer_seed"] for j in sess["jobs"]],
                           "max_parallel_threads": sess["arguments"]["threads"], "shots": sess["arguments"]["shots"]},
           "noise_model": {"basis_gates": list(nm.basis_gates), "noise_instructions": sorted(nm.noise_instructions),
                           "noise_qubits": sorted(int(q) for q in nm.noise_qubits),
                           "str": str(nm)},
           "circuits": {}}
    ok = True
    for cid in ("B0_ref25_k1", "B1_ref57_k1"):
        man = mans[cid]
        ir, n, qmap = qn.pytket_to_ir(qs.load_frozen(CIRC, man))
        qc = cq.ir_to_qiskit(ir, n, measure=True)
        ops = {k: int(v) for k, v in qc.count_ops().items()}
        n1 = ops.get("rx", 0) + ops.get("ry", 0)
        # consecutive rzz on the same pair with no gate on either qubit in between (what a merge would remove)
        last = {}
        mergeable = 0
        for inst in qc.data:
            qs_ = tuple(sorted(qc.find_bit(q).index for q in inst.qubits))
            name = inst.operation.name
            if name == "rzz":
                if all(last.get(q) == ("rzz", qs_) for q in qs_):
                    mergeable += 1
                for q in qs_:
                    last[q] = ("rzz", qs_)
            elif name not in ("barrier",):
                for q in qs_:
                    last[q] = (name, None)
        rec = {"ops": ops, "n_rzz": ops.get("rzz", 0), "n_noisy_1q_rx_ry": n1,
               "manifest_n_zz": int(man["counts"]["n_zz"]), "manifest_n_phasedx": int(man["counts"]["n_phasedx"]),
               "adjacent_same_pair_rzz_in_executed_circuit": mergeable,
               "one_noisy_1q_rotation_per_phasedx": n1 == int(man["counts"]["n_phasedx"]),
               "rzz_equals_2158": ops.get("rzz", 0) == 2158,
               "measure_map_identity": qmap == {q: q for q in range(n)}}
        ok = ok and rec["one_noisy_1q_rotation_per_phasedx"] and rec["rzz_equals_2158"]
        out["circuits"][cid] = rec
    # what Aer reports for a 1-shot run of the executed B0 circuit under the A6 model
    man = mans["B0_ref25_k1"]
    ir, n, _ = qn.pytket_to_ir(qs.load_frozen(CIRC, man))
    qc = cq.ir_to_qiskit(ir, n, measure=True)
    t0 = time.time()
    res = AerSimulator(noise_model=nm, method="statevector", seed_simulator=11).run(qc, shots=1).result()
    md = res.results[0].metadata
    out["one_shot_metadata"] = {k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(v))
                                for k, v in dict(md).items()}
    out["one_shot_wall_s"] = time.time() - t0
    want = {"rzz", "rx", "ry", "measure"}
    out["noise_instructions_ok"] = set(nm.noise_instructions) == want
    out["ok"] = bool(ok and out["noise_instructions_ok"])
    lo_hi = sorted(int(m["counts"]["n_phasedx"]) for m in mans.values() if m.get("kind") != "calibration")
    out["prompt_c5_literal"] = {
        "typed_value": PROMPT_C5_LITERAL_1Q,
        "phasedx_counts_of_the_44_frozen_circuits": {"min": lo_hi[0], "max": lo_hi[-1]},
        "matches_any_frozen_circuit": PROMPT_C5_LITERAL_1Q in lo_hi,
        "note": ("prompts/28 C5 types 3053 noisy 1q rotations; A3 defines the requirement as 'one noisy 1q rotation "
                 "per PhasedX'.  The A6 circuits carry 3091 (B0_ref25_k1) and 2989 (B1_ref57_k1) PhasedX in their "
                 "manifests; C5 is evaluated against the per-circuit PhasedX count (A3's definition)")}
    return out


# =========================================================================== checks (C6)
def run_checks():
    t0 = time.time()
    out = {}
    for tag, py in (("coding", CODING_PY), ("venv", VENV_PY)):
        r = subprocess.run([py, "-m", "pytest", "-q", "tests"], cwd=ROOT, capture_output=True, text=True)
        out[f"pytest_{tag}"] = {"python": py, "returncode": r.returncode,
                                "summary": (r.stdout.strip().splitlines() or [""])[-1]}
    c = subprocess.run([CODING_PY, os.path.join("scripts", "check_package.py")], cwd=ROOT, capture_output=True, text=True)
    out["check_package"] = {"returncode": c.returncode, "tail": "\n".join(c.stdout.strip().splitlines()[-3:])}
    code = ("import sys,json,qiskit,qiskit_aer,qiskit_ibm_runtime,numpy,scipy;print(json.dumps({'python':"
            "sys.version.split()[0],'qiskit':qiskit.__version__,'qiskit-aer':qiskit_aer.__version__,"
            "'qiskit-ibm-runtime':qiskit_ibm_runtime.__version__,'numpy':numpy.__version__,'scipy':scipy.__version__}))")
    pr = subprocess.run([CODING_PY, "-c", code], capture_output=True, text=True)
    out["pins_now"] = json.loads(pr.stdout.strip().splitlines()[-1])
    out["pins_ok"] = out["pins_now"] == PINS_EXPECTED
    out["seconds"] = time.time() - t0
    out["ok"] = (out["pytest_coding"]["returncode"] == 0 and out["pytest_venv"]["returncode"] == 0
                 and c.returncode == 0 and out["pins_ok"])
    return out


def write_r_nc(pooled: dict, arms: dict) -> dict:
    """data/cf_trajectories/r_nc.json: r_nc = the upper end of the 95 % bootstrap interval of the pooled
    r(1e-3) (prompts/29 3(1)); with the commit, K and seeds per arm."""
    tb = delta_tag(DELTA_BAR)
    commit, dirty = cf.git_commit()
    rec = {"produced_by": "scripts/gate_CF_traj.py", "prompt": "prompts/29_cf_traj_reruling_ideal_sample_fraction.md "
           "3(1) and A'2", "created": cf.now(), "git_commit": commit, "git_dirty_scripts_src": dirty,
           "r_nc": pooled[f"r_{tb}"]["ci95"][1],
           "definition": ("r_nc = upper end (97.5th percentile) of the 95 % bootstrap interval of the pooled "
                          "f_hit / f_ideal(1e-3) over the k = 1 arms; f_hit^pool = sum_c N_c p_ref,c f_hit,c / "
                          "sum_c N_c p_ref,c (the expectation of pooled_reference_string_test without its garbage "
                          "term), f_ideal^pool = sum_c N_c f_ideal,c / sum_c N_c, N_c = the Stage E/P v3 shots"),
           "delta": DELTA_BAR, "pooled_r_point": pooled[f"r_{tb}"]["value"],
           "pooled_r_ci95": pooled[f"r_{tb}"]["ci95"],
           "pooled_r_one_sided_upper95_information": pooled[f"r_{tb}"]["one_sided_upper95"],
           "pooled_f_hit": pooled["f_hit"]["value"], "pooled_f_ideal": pooled[f"f_ideal_{tb}"]["value"],
           "pool_weights_shots": POOL_SHOTS, "bootstrap": {"B": N_BOOT, "seed": BOOT_SEED,
                                                          "scheme": "trajectories resampled within each arm"},
           "arms": {c: {"K": arms[c]["K"], "seeds": sorted(ch["seed"] for ch in arms[c]["chunks"]),
                        "chunk_commits": sorted({ch["git_commit"] for ch in arms[c]["chunks"]}),
                        "f0_prime": arms[c]["f0_prime"], "p_ref": arms[c]["p_ref"],
                        "f_hit": arms[c]["stats"]["f_hit"], f"f_ideal_{tb}": arms[c]["stats"][f"f_ideal_{tb}"],
                        f"r_{tb}": arms[c]["stats"][f"r_{tb}"]} for c in POOL_SHOTS},
           "planned_K": {c: ARMS[c]["K"] for c in POOL_SHOTS},
           "complete": all(arms[c]["K"] >= ARMS[c]["K"] for c in POOL_SHOTS),
           "stop_rule": f"prompts/29 A'3: STOP (planner returns) if r_nc > {R_NC_STOP}",
           "stop": bool(pooled[f"r_{tb}"]["ci95"][1] > R_NC_STOP),
           "caveat": ("r_nc is a gate-noise (A6 channel) value; on H2-2 the memory term is 5-30 % of the gate term "
                      "(survey), so the composition stays gate-dominated; on IBM devices (idle dephasing) it is "
                      "unknown and A5 gives the only model estimate (prompts/29 3(1))")}
    with open(R_NC_PATH, "w") as fh:
        json.dump(rec, fh, indent=1)
    return rec


def mixture_bias_block(arm: dict) -> dict:
    """prompts/29 A'2 / C7: the k = 4 mixture-estimator expectation and its bias against f_ideal(1e-3);
    95 % bootstrap interval over trajectories (the arm's own bootstrap weights: B = 2000, seed 2028)."""
    tb = delta_tag(DELTA_BAR)
    f0, pc, P, tv = arm["f0_prime"], arm["_pc"], arm["_P"], arm["_tv"]
    K = len(tv)
    fid = arm["stats"][f"f_ideal_{tb}"]["value"]
    per_N = {}
    for N in MIX_N:
        r = mixture_expectation(f0, pc, P.mean(axis=0), N)
        per_N[str(N)] = {k: r[k] for k in ("w", "w_68", "accepted", "shots", "f_clean", "f_clean_68", "logL_gain")}
        per_N[str(N)]["bias_ratio"] = r["f_clean"] / fid
        per_N[str(N)]["bias_ratio_68_profile"] = [x / fid for x in r["f_clean_68"]]
    t0 = time.time()
    W = np.random.default_rng(BOOT_SEED).multinomial(K, np.full(K, 1.0 / K), size=N_BOOT) / K
    bias, fmix = [], []
    for w in W:
        r = mixture_expectation(f0, pc, w @ P, MIX_N[-1])
        fmix.append(r["f_clean"])
        bias.append(r["f_clean"] / (f0 + (1.0 - f0) * float(w @ (tv < DELTA_BAR))))
    point = per_N[str(MIX_N[-1])]
    return {"arm": arm["id"], "K": K, "f0_prime": f0, "f_ideal_point": fid,
            "f_hit_point": arm["stats"]["f_hit"]["value"], "per_N": per_N,
            "w_independent_of_N": abs(per_N[str(MIX_N[0])]["w"] - per_N[str(MIX_N[-1])]["w"]) < 1e-6,
            "f_mix": ival(point["f_clean"], fmix), "bias_ratio": ival(point["bias_ratio"], bias),
            "f_mix_over_f0_prime": point["f_clean"] / f0, "f_mix_over_f_hit": point["f_clean"] / arm["stats"]["f_hit"]["value"],
            "stop_band": list(MIX_BAND), "bootstrap_s": time.time() - t0,
            "note": ("the population mixture is an expectation (no sampling noise), so w does not depend on N; "
                     "N sets only the profile-likelihood interval (w_68).  The 95 % interval is the bootstrap over "
                     "trajectories (the model uncertainty of the population)")}


# =========================================================================== A5 (2x2, both T2 ends)
def a5_block() -> dict:
    """The A5 2x2 arm at both ends of the T2 bracket (scripts/cf_traj_2x2_arm.py: T2* = Ramsey, echo = record
    T2), with b(delta), f_ideal(delta), r(delta) recomputed from its trajectory file (bootstrap B = 2000,
    seed 2028)."""
    out = {"model_note": ("Markovian Pauli model of the H0_2x2 adopted circuit (cell T3, ALAP + client XY4): "
                          "depolarizing cz/sx/x from the calibration record, idle Z with probability "
                          "(1 - exp(-t/T2))/2 per explicit delay; cannot represent DD refocusing of quasi-static "
                          "dephasing, so the two T2 ends bracket a model number, not a device prediction"),
           "ends": {}}
    for tag, (res_name, traj_name) in A5_ENDS.items():
        rp, tp = os.path.join(cf.OUT, "A5_2x2", res_name), os.path.join(cf.OUT, "A5_2x2", traj_name)
        if not (os.path.exists(rp) and os.path.exists(tp)):
            out["ends"][tag] = {"status": "not run", "reason": f"{os.path.relpath(rp, ROOT)} absent"}
            continue
        res, trajs = load_json(rp), load_json(tp)
        f0, p_ref = float(res["f0_prime"]), float(res["p_ref"])
        h = np.array([t["p_ref_post"] for t in trajs])
        tv = np.array([t["tv_pre"] for t in trajs])
        K = len(h)
        if K != int(res["K"]):
            raise RuntimeError(f"A5 {tag}: {K} trajectories in {traj_name}, result says {res['K']}")
        point = ideal_fraction(f0, np.full(K, 1.0 / K), h, tv, p_ref)
        if abs(point["f_hit"] - float(res["stats"]["f_hit"]["value"])) > 1e-12:
            raise RuntimeError(f"A5 {tag}: f_hit recomputed {point['f_hit']} != result {res['stats']['f_hit']['value']}")
        W = np.random.default_rng(BOOT_SEED).multinomial(K, np.full(K, 1.0 / K), size=N_BOOT) / K
        boots = [ideal_fraction(f0, w, h, tv, p_ref) for w in W]
        st = {k: ival(v, [b[k] for b in boots]) for k, v in point.items()}
        st["rho_ref"] = res["stats"]["rho_ref"]
        st["rho_T"] = res["stats"]["rho_T"]
        out["ends"][tag] = {
            "status": res.get("status", "run"), "t2_variant": res["t2_variant"], "K": K, "seed": res["seed"],
            "git_commit": res["git_commit"], "created": res["created"], "wall_s": res["wall_s"],
            "files": [os.path.relpath(rp, ROOT), os.path.relpath(tp, ROOT)], "circuit": res["circuit"],
            "dd_cell": res["dd_cell"], "g0": res["g0"], "readout_survival_reference": res["readout_survival_reference"],
            "f0_prime": f0, "p_ref": p_ref, "n_sites": res["n_sites"], "z_only_fraction": res["z_only_fraction"],
            "n_draws": res["n_draws"], "stats": st,
            "n_benign_tv_below": {delta_tag(d): int(np.sum(tv < d)) for d in DELTAS}}
    return out


# =========================================================================== main
def fmt(x, nd=4):
    if x is None:
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    x = float(x)
    if x != 0 and (abs(x) < 1e-3 or abs(x) >= 1e5):
        return f"{x:.3e}"
    return f"{x:.{nd}g}"


def fi(d, nd=4):
    return f"{fmt(d['value'], nd)} [{fmt(d['ci95'][0], nd)}, {fmt(d['ci95'][1], nd)}]"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-checks", action="store_true", help="development only: C6 recorded as not run")
    args = ap.parse_args(argv)
    t_start = time.time()
    import quantinuum_submit as qs

    A6 = qs.A6_NOISE
    idx = load_json(os.path.join(CIRC, "index.json"))
    mans = {c: load_json(os.path.join(CIRC, c + ".manifest.json")) for c in idx["circuits"]}
    predict = load_json(PREDICT)
    phase = load_json(PHASE)
    G = GateResult(GATE, TITLE)
    data = {"prompt": ("prompts/28_2x3_shot_rule_and_clean_fraction_estimator.md Part A, completed and re-assembled "
                       "under prompts/29_cf_traj_reruling_ideal_sample_fraction.md Part A' (C1/C4 replaced by C1/C4', "
                       "C7 added; C2, C3, C5, C6 unchanged)"),
            "what_pass_means": WHAT_PASS_MEANS, "A6_NOISE": A6,
            "definitions": __doc__.split("Definitions")[1].split("Run in")[0].strip()}

    # ---------------------------------------------------------------- C1: timing, K, chunk files
    tpath = os.path.join(cf.OUT, "timing_A0.json")
    timing = load_json(tpath) if os.path.exists(tpath) else None
    data["A0_timing"] = timing
    arms, raw = {}, {}
    c1_notes = []
    c1_ok = timing is not None
    for cid, plan in list(ARMS.items()) + [(XX_ARM["id"] + "__xx", XX_ARM)]:
        real = cid.split("__")[0]
        a = load_arm(real, plan["channel"])
        if a is None:
            c1_ok = False
            c1_notes.append(f"{cid}: no chunk files")
            continue
        raw[cid] = a
        arms[cid] = arm_statistics(real, a, mans[real], A6, predict)
        seeds = sorted(ch["seed"] for ch in arms[cid]["chunks"])
        okK = arms[cid]["K"] >= plan["K"]
        okS = seeds == sorted(plan["seeds"])
        okC = all(ch["git_commit"] not in (None, "n/a") for ch in arms[cid]["chunks"])
        c1_ok = c1_ok and okK and okS and okC
        c1_notes.append(f"{cid}: K {arms[cid]['K']}/{plan['K']}, seeds {seeds}")
        arms[cid]["hamming"] = hamming_block(a)
    data["arms"] = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in arms.items()}
    a5 = a5_block()
    data["A5_2x2_arm"] = a5
    a5_ok = all(e.get("status") == "run" and e.get("K", 0) >= A5_K for e in a5["ends"].values()) or (
        all(e.get("status") == "not run" and e.get("reason") for e in a5["ends"].values()))
    c1_notes.append("A5: " + ", ".join(f"{t} {e.get('status')} K {e.get('K')}" for t, e in a5["ends"].items()))
    G.add("C1 A0 timing recorded; planned K reached on all four arms (every chunk file with seed and git commit); "
          "A5 recorded at both T2 ends",
          "; ".join(c1_notes), "B0_ref25_k1 720 (seeds 101-103), B1_ref57_k1 240 (201), B0_ref25_k4 240 (301), "
          f"xx control arm 120 (401); A5 K >= {A5_K} at T2* and echo T2 (or both 'not run' with the reason)",
          c1_ok and a5_ok)

    # ---------------------------------------------------------------- C2: the A6 hit prediction + A4
    observed = {}
    for cid in ("B0_ref25_k1", "B1_ref57_k1"):
        rec = load_json(os.path.join(DRYRUN, "counts", cid + ".json"))
        observed[cid] = {"hits": ref_hits(rec, mans[cid]["reference_int"]), "shots": int(rec["shots"])}
    n_obs = sum(v["hits"] for v in observed.values())
    c2 = {"observed_per_circuit": observed, "observed_total": n_obs,
          "observed_total_predict_json": predict["dryrun"]["reference_hits_total"]}
    if all(c in arms for c in ("B0_ref25_k1", "B1_ref57_k1")):
        mu, var = 0.0, 0.0
        per = {}
        for cid in ("B0_ref25_k1", "B1_ref57_k1"):
            s = arms[cid]
            N = observed[cid]["shots"]
            m = N * s["hit_fraction_per_shot"]["prompt_formula_f0p_pref_plus_1mf0_h"]
            se = N * (1 - s["f0_prime"]) * s["_h_se"]
            per[cid] = {"shots": N, "predicted": m, "se": se, "observed": observed[cid]["hits"],
                        "fault_free_only": N * s["f0_prime"] * s["p_ref"],
                        "predicted_exact_decomposition": N * s["hit_fraction_per_shot"]["exact_g0_pideal_post_plus_1mg0_h"]}
            mu += m
            var += se ** 2
        se_mu = math.sqrt(var)
        P = two_sided_poisson_p(n_obs, mu)
        # information: Poisson P with mu's trajectory uncertainty integrated (normal prior on mu, truncated > 0)
        grid = np.linspace(max(1e-6, mu - 5 * se_mu), mu + 5 * se_mu, 401)
        wts = np.exp(-0.5 * ((grid - mu) / se_mu) ** 2)
        wts /= wts.sum()
        from scipy.stats import poisson
        cdf = float(np.sum(wts * poisson.cdf(n_obs, grid)))
        sf = float(np.sum(wts * poisson.sf(n_obs - 1, grid)))
        sd_tot = math.sqrt(mu + se_mu ** 2)
        low_side = (mu < n_obs) and ((n_obs - mu) / sd_tot > LOW_SIDE_SIGMAS)
        c2.update({"per_circuit": per, "predicted_total": mu, "predicted_total_se": se_mu,
                   "fault_free_only_total": sum(v["fault_free_only"] for v in per.values()),
                   "two_sided_poisson_P": P, "two_sided_P_with_mu_uncertainty": float(min(1.0, 2 * min(cdf, sf))),
                   "sd_total_poisson_plus_trajectory": sd_tot, "z_observed_minus_predicted": (n_obs - mu) / sd_tot,
                   "prediction_below_observed_by_more_than_3_sd": bool(low_side),
                   "pooled_f_hit_traj": (sum(per[c]["shots"] * arms[c]["stats"]["f_hit"]["value"] for c in per)
                                         / sum(per[c]["shots"] for c in per)),
                   "A6_pooled_reference_string_f": predict["dryrun"]["pooled_f_estimate"],
                   "A6_pooled_reference_string_f_95": predict["dryrun"]["pooled_f_95"]})
    # A4 control
    a4 = {"present": False}
    cpath = os.path.join(cf.OUT, "control_xx", "counts", "B0_ref25_k1.json")
    xx = arms.get("B0_ref25_k1__xx")
    if os.path.exists(cpath) and xx is not None:
        rec = load_json(cpath)
        hits = ref_hits(rec, mans["B0_ref25_k1"]["reference_int"])
        N = int(rec["shots"])
        mu_xx = N * xx["hit_fraction_per_shot"]["prompt_formula_f0p_pref_plus_1mf0_h"]
        band = poisson_band(mu_xx)
        sess = load_json(os.path.join(cf.OUT, "control_xx", "session.json"))
        a4 = {"present": True, "shots": N, "seed": int(sess["jobs"][0]["aer_seed"]), "hits": hits,
              "h_ref_xx": xx["stats"]["h_ref"], "predicted": mu_xx,
              "predicted_se": N * (1 - xx["f0_prime"]) * xx["_h_se"],
              "fault_free_only": N * xx["f0_prime"] * xx["p_ref"], "poisson_95_band": band,
              "two_sided_poisson_P": two_sided_poisson_p(hits, mu_xx),
              "pass": band[0] <= hits <= band[1], "above_band": hits > band[1],
              "A6_like_count_for_280_shots": n_obs, "session": os.path.relpath(cpath, ROOT),
              "sampling_wall_s": sess.get("sampling_wall_s"), "noise_model": sess["noise_model"]}
    c2["A4_control"] = a4
    data["C2"] = c2
    c2_ok = bool(c2.get("two_sided_poisson_P", 0.0) >= P_MIN and a4.get("pass", False))
    G.add("C2 trajectory prediction of the A6 reference hits vs observed (two-sided Poisson) and the A4 control",
          (f"predicted {fmt(c2.get('predicted_total'))} +- {fmt(c2.get('predicted_total_se'))} vs observed {n_obs}, "
           f"P = {fmt(c2.get('two_sided_poisson_P'))}; A4: {a4.get('hits')} hits vs predicted "
           f"{fmt(a4.get('predicted'))}, band {a4.get('poisson_95_band')}") if "predicted_total" in c2 else "not computed",
          "P >= 0.05 and the A4 hits inside the Poisson 95 % band of the xx-arm prediction", c2_ok)

    # ---------------------------------------------------------------- C3: Z-only stratum vs phase-only check
    c3 = {"phase_check": {k: phase[k] for k in ("circuit", "shots", "seed", "reference_hits", "no_error_probability",
                                                "p_reference", "channel")}}
    c3_ok = False
    s = arms.get("B0_ref25_k1")
    if s is not None and s["z_stratum"].get("h_Z") is not None:
        g0p, pr = float(phase["no_error_probability"]), float(phase["p_reference"])
        hz = s["z_stratum"]["h_Z"]
        mu_z = PHASE_SHOTS * (g0p * pr + (1 - g0p) * hz)
        band = poisson_band(mu_z)
        k = int(phase["reference_hits"])
        c3.update({"h_Z": hz, "h_Z_se": s["z_stratum"].get("h_Z_se"), "n_z_only": s["z_stratum"]["n_z_only"],
                   "predicted": mu_z, "poisson_95_band": band, "observed": k,
                   "two_sided_poisson_P": two_sided_poisson_p(k, mu_z)})
        rw = s["z_stratum"].get("phase_channel_reweighted")
        if rw:
            mu_rw = PHASE_SHOTS * (g0p * pr + (1 - g0p) * rw["h_faulty_self_normalised"])
            c3["information_reweighted_to_phase_channel"] = {
                "h_faulty": rw["h_faulty_self_normalised"], "predicted": mu_rw, "poisson_95_band": poisson_band(mu_rw),
                "two_sided_poisson_P": two_sided_poisson_p(k, mu_rw), "mean_weight": rw["mean_weight"], "note": rw["note"]}
        c3_ok = band[0] <= k <= band[1]
    data["C3"] = c3
    G.add("C3 Z-only stratum reproduces the phase-only check (11 hits in 40)",
          (f"predicted {fmt(c3.get('predicted'))}, band {c3.get('poisson_95_band')}, observed {c3.get('observed')}"
           if "predicted" in c3 else "not computed"),
          "observed inside the Poisson 95 % band of 40 [g0 p_ref + (1 - g0) h_Z]", c3_ok)

    # ---------------------------------------------------------------- C4' (prompts/29): f_ideal, r, floor, r_nc
    tb = delta_tag(DELTA_BAR)
    all_arms = list(ARMS) + [XX_ARM["id"] + "__xx"]
    keys = [f"{k}_{delta_tag(d)}" for d in DELTAS for k in ("b", "f_ideal", "r")] + [f"min_feff_over_fideal_S99_{tb}"]
    have_all = all(cid in arms and all(k in arms[cid]["stats"] for k in keys) for cid in all_arms)
    floor = {cid: arms[cid]["stats"][f"min_feff_over_fideal_S99_{tb}"] for cid in all_arms if cid in arms}
    floor_ok = bool(floor) and len(floor) == len(all_arms) and all(v["value"] >= FLOOR_MIN for v in floor.values())
    rnc = None
    if all(c in arms for c in POOL_SHOTS):
        parts = [{"id": c, "f0": arms[c]["f0_prime"], "p_ref": arms[c]["p_ref"], "h": arms[c]["_h"],
                  "tv": arms[c]["_tv"], "shots": POOL_SHOTS[c]} for c in POOL_SHOTS]
        pooled = pooled_ratio(parts)
        rnc = write_r_nc(pooled, arms)
        data["pooled_k1"] = {"weights_shots": POOL_SHOTS, "stats": pooled, "r_nc": rnc["r_nc"],
                             "r_nc_file": os.path.relpath(R_NC_PATH, ROOT)}
    data["floor_theorem_check"] = {"criterion": f"min over S99 of f_eff / f_ideal({DELTA_BAR:g}) >= {FLOOR_MIN}",
                                   "per_arm": floor,
                                   "theorem_bound_counts": {cid: arms[cid]["floor_theorem_S99"] for cid in arms}}
    c4_ok = bool(have_all and floor_ok and rnc is not None and math.isfinite(rnc["r_nc"]))
    G.add("C4' b, f_ideal, r at delta 1e-3/1e-2/0.03 with intervals on all four arms; min_S99 f_eff/f_ideal(1e-3) "
          ">= 0.95 on every arm (floor theorem); r_nc written",
          "; ".join(f"{cid}: r(1e-3) {fi(arms[cid]['stats']['r_' + tb])}, min_S99 f_eff/f_ideal "
                    f"{fi(floor[cid])}" for cid in all_arms if cid in arms)
          + (f"; r_nc = {fmt(rnc['r_nc'])} (pooled r(1e-3) {fi(data['pooled_k1']['stats']['r_' + tb])}) -> "
             f"{os.path.relpath(R_NC_PATH, ROOT)}" if rnc else "; r_nc not computed"),
          f"all quantities present with 95 % bootstrap intervals; every min >= {FLOOR_MIN}; r_nc finite and written",
          c4_ok)

    # ---------------------------------------------------------------- C5: A6-path audit
    audit = a6_path_audit(mans)
    data["C5_A6_path_audit"] = audit
    G.add("C5 A6-path audit: 2158 rzz, one noisy 1q rotation per PhasedX, noise on rzz, rx, ry, measure",
          "; ".join(f"{c}: rzz {r['n_rzz']}, rx+ry {r['n_noisy_1q_rx_ry']} (PhasedX {r['manifest_n_phasedx']})"
                    for c, r in audit["circuits"].items()) + f"; noise_instructions {audit['noise_model']['noise_instructions']}",
          "rzz = 2158 and rx+ry = the manifest PhasedX count (prompt's typed 3053 matches no frozen circuit: see "
          "data.C5_A6_path_audit.prompt_c5_literal)", audit["ok"])

    # ---------------------------------------------------------------- C7 (prompts/29): k = 4 mixture bias
    if MIX_ARM in arms:
        data["C7_k4_mixture"] = mixture_bias_block(arms[MIX_ARM])
    mix = data.get("C7_k4_mixture", {})
    c7_ok = bool(mix and all(math.isfinite(x) for x in [mix["bias_ratio"]["value"]] + mix["bias_ratio"]["ci95"]))

    # ---------------------------------------------------------------- STOP flags + verdict
    rho_T_max = max((arms[c]["stats"]["rho_T"]["value"] for c in ARMS if c in arms), default=None)
    mix = data.get("C7_k4_mixture", {})
    mb = mix.get("bias_ratio", {}).get("value")
    stops = {"C2_low_side": bool(c2.get("prediction_below_observed_by_more_than_3_sd", False)),
             "A4_reproduces_A6_like_count": bool(a4.get("above_band", False)),
             "r_nc_above_1p3": bool(rnc is not None and rnc["r_nc"] > R_NC_STOP),
             "r_nc": rnc["r_nc"] if rnc else None,
             "k4_mixture_bias_outside_0p67_1p5": bool(mb is not None and not (MIX_BAND[0] <= mb <= MIX_BAND[1])),
             "k4_mixture_bias": mb,
             "retired_rho_T_above_1p5_information_only": bool(rho_T_max is not None and rho_T_max > RHO_T_STOP),
             "rho_T_max_over_arms": rho_T_max,
             "note": ("prompts/29 A'3: STOP flags are C2 low side, an A4-like count, r_nc > 1.3 and the k = 4 mixture "
                      "bias outside [0.67, 1.5]; the prompts/28 rho_T STOP is retired (f_T withdrawn) and kept as "
                      "information")}
    stops["any_stop"] = bool(stops["C2_low_side"] or stops["A4_reproduces_A6_like_count"] or stops["r_nc_above_1p3"]
                             or stops["k4_mixture_bias_outside_0p67_1p5"])
    data["stop_flags"] = stops
    missing = []
    for cid, plan in list(ARMS.items()) + [(XX_ARM["id"] + "__xx", XX_ARM)]:
        have = arms[cid]["K"] if cid in arms else 0
        if have < plan["K"]:
            missing.append({"arm": cid, "K_done": have, "K_planned": plan["K"],
                            "seeds_done": sorted(ch["seed"] for ch in arms[cid]["chunks"]) if cid in arms else [],
                            "seeds_planned": plan["seeds"]})
    data["arms_short_of_plan"] = missing
    if stops["C2_low_side"] or stops["A4_reproduces_A6_like_count"]:
        verdict = "bug candidate (Aer path applies fewer error events than modelled, or trajectory model too low)"
    elif c2_ok:
        verdict = ("physics: near-clean term -- the reference-hit excess is reproduced by the trajectory "
                   "decomposition and the bit-flip-only control gives the fault-free count")
    elif c2.get("predicted_total", 0) > n_obs:
        verdict = "model question: the trajectory prediction lies above the observed hits (not a bug candidate)"
    else:
        verdict = "undecided"
    data["physics_verdict"] = verdict

    # ---------------------------------------------------------------- C6
    checks = {"skipped": True, "ok": False} if args.skip_checks else run_checks()
    data["C6_checks"] = checks
    G.add("C6 pytest (coding + venv), check_package, pins unchanged",
          ("skipped" if checks.get("skipped") else
           f"coding: {checks['pytest_coding']['summary']}; venv: {checks['pytest_venv']['summary']}; "
           f"check_package rc {checks['check_package']['returncode']}; pins_ok {checks['pins_ok']}"),
          "all pass, pins = " + json.dumps(PINS_EXPECTED), checks.get("ok", False))
    G.add("C7 k = 4 mixture estimator (clean_fraction_mixture, readout factor 1.0) on the B0_ref25_k4 population "
          "mixture: bias ratio (w-implied f) / f_ideal(1e-3) reported with its interval",
          (f"bias {fi(mix['bias_ratio'])} (N = {MIX_N[0]}: f {fmt(mix['per_N'][str(MIX_N[0])]['f_clean'])}, "
           f"N = {MIX_N[1]}: f {fmt(mix['per_N'][str(MIX_N[1])]['f_clean'])}; f_ideal(1e-3) "
           f"{fmt(mix['f_ideal_point'])})") if mix else "not computed",
          f"reported with a 95 % bootstrap interval (STOP flag, not the criterion: outside [{MIX_BAND[0]}, {MIX_BAND[1]}])",
          c7_ok)

    G.data = data
    G.runtime_s = time.time() - t_start
    path = G.save()
    write_report("CF_traj.md", render(G, data, arms))
    print(f"{GATE}: {'PASS' if G.passed else 'FAIL'} -> {os.path.relpath(path, ROOT)}")
    for c in G.criteria:
        print(f"  {'PASS' if c.passed else 'FAIL'}  {c.name}: {c.value}")
    print("stop flags:", stops)
    print("verdict:", verdict)
    return 0 if G.passed else 1


def render_ideal(data, arms) -> list:
    """Report sections of prompts/29 (every number read from `data` / `arms`)."""
    tb = delta_tag(DELTA_BAR)
    L = ["## prompts/29: the ideal-sample fraction per arm (95 % bootstrap intervals, B = 2000, seed 2028)", ""]
    rows = []
    for cid, s in arms.items():
        st = s["stats"]
        for d in DELTAS:
            t = delta_tag(d)
            rows.append([cid, s["K"], fmt(s["f0_prime"], 6), fi(st["f_hit"]), f"{d:g}", fi(st[f"b_{t}"]),
                         fi(st[f"f_ideal_{t}"]), fi(st[f"r_{t}"]), fi(st[f"min_feff_over_fideal_S99_{t}"])])
    L += [md_table(["arm", "K", "f0'", "f_hit", "delta", "b(delta)", "f_ideal(delta)", "r(delta) = f_hit/f_ideal",
                    "min_S99 f_eff/f_ideal"], rows), ""]
    pk = data.get("pooled_k1")
    if pk:
        rows = []
        for d in DELTAS:
            t = delta_tag(d)
            v = pk["stats"][f"r_{t}"]
            rows.append([f"{d:g}", fmt(pk["stats"][f"f_ideal_{t}"]["value"]), fi(v), fmt(v["one_sided_upper95"])])
        L += [f"Pooled k = 1 (weights: shots {pk['weights_shots']}; pooled f_hit {fi(pk['stats']['f_hit'])}):", "",
              md_table(["delta", "pooled f_ideal", "pooled r [95 %]", "one-sided 95 % upper (information)"], rows), "",
              f"**r_nc = {fmt(pk['r_nc'])}** (upper end of the 95 % interval of the pooled r({DELTA_BAR:g})), written to "
              f"`{pk['r_nc_file']}`.", ""]
    fl = data["floor_theorem_check"]
    L += ["### Floor theorem check (prompts/29 2.4)", "", f"Criterion: {fl['criterion']}.", "",
          md_table(["arm", "min_S99 f_eff/f_ideal(1e-3)"] + [f"#S99 below f_ideal(1 - 2 delta/p_c), delta {d:g}"
                                                             for d in DELTAS],
                   [[cid, fi(v)] + [f"{fl['theorem_bound_counts'][cid][delta_tag(d)]['n_below_bound']} of "
                                    f"{fl['theorem_bound_counts'][cid][delta_tag(d)]['n_states']}" for d in DELTAS]
                    for cid, v in fl["per_arm"].items()]), ""]
    L += ["### Returns to the reference (prompts/29 2.1)", "",
          md_table(["arm", "K", "returns", "share of h_ref", "single-event returns", "by Pauli",
                    "TV machine 0", "TV < 1e-3", "TV < 0.04", "single-event X-type: returns / all"],
                   [[cid, r["K"], r["n_returns"], fmt(r["share_of_h_ref_carried_by_returns"], 3),
                     r["n_single_event_returns"], json.dumps(r["single_event_returns_by_pauli"]),
                     r["n_returns_tv_machine_zero"], r["n_returns_tv_below_1e-3"], r["n_returns_tv_below_0.04"],
                     f"{r['n_single_event_x_type_returns']} / {r['n_single_event_x_type_trajectories']}"]
                    for cid, r in ((c, arms[c]["returns"]) for c in arms)]), ""]
    mx = data.get("C7_k4_mixture")
    if mx:
        L += ["### C7: the k = 4 mixture estimator against f_ideal", "",
              md_table(["N", "w", "w 68 % (profile)", "w-implied f", "bias = f / f_ideal(1e-3)", "bias 68 % (profile)"],
                       [[N, fmt(v["w"]), [fmt(x) for x in v["w_68"]], fmt(v["f_clean"]), fmt(v["bias_ratio"]),
                         [fmt(x) for x in v["bias_ratio_68_profile"]]] for N, v in mx["per_N"].items()]), "",
              f"Arm {mx['arm']} (K = {mx['K']}): f0' {fmt(mx['f0_prime'])}, f_ideal(1e-3) {fmt(mx['f_ideal_point'])}, "
              f"f_hit {fmt(mx['f_hit_point'])}; mixture f {fi(mx['f_mix'])}; **bias ratio {fi(mx['bias_ratio'])}** "
              f"(95 % bootstrap); f_mix/f0' = {fmt(mx['f_mix_over_f0_prime'])}.  {mx['note']}.", ""]
    a5 = data["A5_2x2_arm"]
    rows = []
    for tag, e in a5["ends"].items():
        if e.get("status") != "run":
            rows.append([tag, e.get("status"), e.get("reason", ""), "", "", "", "", ""])
            continue
        st = e["stats"]
        rows.append([tag, e["K"], fmt(e["f0_prime"]), fi(st["f_hit"]), fi(st[f"f_ideal_{tb}"]), fi(st[f"r_{tb}"]),
                     fi(st[f"f_ideal_{delta_tag(0.03)}"]), fi(st[f"r_{delta_tag(0.03)}"])])
    L += ["### A5: the 2x2 arm at both ends of the T2 bracket (model numbers, information)", "", a5["model_note"] + ".", "",
          md_table(["T2 end", "K", "f0'", "f_hit", "f_ideal(1e-3)", "r(1e-3)", "f_ideal(0.03)", "r(0.03)"], rows), ""]
    return L


def render(G, data, arms):
    L = [f"# Gate {GATE}: {TITLE}", "",
         f"Status: **{'PASS' if G.passed else 'FAIL'}**.  Prompt: {data['prompt']}.  Generated by "
         "`scripts/gate_CF_traj.py` from `validation/CF_traj.json`; every number below is read "
         "from that file.  0 QPU s, 0 HQC.", "",
         f"What PASS means: {WHAT_PASS_MEANS}", "",
         f"Physics verdict: **{data['physics_verdict']}**.", "",
         f"STOP flags (prompts/29 A'3): any STOP = **{data['stop_flags']['any_stop']}**; r_nc = "
         f"{fmt(data['stop_flags']['r_nc'])} (STOP above {R_NC_STOP}); k = 4 mixture bias "
         f"{fmt(data['stop_flags']['k4_mixture_bias'])} (STOP outside [{MIX_BAND[0]}, {MIX_BAND[1]}]).", "",
         *( ["Arms short of plan:", "",
             md_table(["arm", "K done", "K planned", "seeds done", "seeds planned"],
                      [[m["arm"], m["K_done"], m["K_planned"], m["seeds_done"], m["seeds_planned"]]
                       for m in data["arms_short_of_plan"]]), ""] if data.get("arms_short_of_plan") else []),
         "## Criteria", "", G.criteria_table(), "",
         "## Definitions (the planner's labels, prompts/28 and prompts/29; not manual terms)", "", "```",
         data["definitions"], "```", "", *render_ideal(data, arms),
         "## Per-arm results of prompts/28 (95 % bootstrap intervals over trajectories; rho_T information only)", ""]
    rows = []
    for cid, s in arms.items():
        st = s["stats"]
        rows.append([cid, s["channel"], s["K"], fmt(s["f0_prime"], 6), fi(st["h_ref"]), fi(st["f_hit"]), fi(st["f_T"]),
                     fi(st["rho_ref"]), fi(st["rho_T"]), fi(st["benign_fraction"])])
    L += [md_table(["arm", "channel", "K", "f0'", "h_ref", "f_hit^traj", "f_T^traj", "rho_ref", "rho_T", "b"], rows), ""]
    rows = []
    for cid, s in arms.items():
        st = s["stats"]
        rows.append([cid, s["tail_class"]["size"], fmt(s["tail_class"]["p_Tc"]), fi(st["min_feff_over_f0_S99"]),
                     fi(st["median_feff_over_f0_S99"]), fi(st["min_feff_over_f0_S999"]), fi(st["median_feff_over_f0_S999"]),
                     fi(st["min_feff_over_fT_S99"]), fi(st["n_S99_feff_below_margin_fT"])])
    L += ["Per-state effective rates ($f_{\\rm eff}(s)/f_0'$; states with tiny $p_c(s)$ inflate the median/max, the "
          "per-state table is in the JSON, `data.arms.<arm>.per_state_S999`):", "",
          md_table(["arm", "|T_c|", "p_Tc", "min S99", "median S99", "min S999", "median S999",
                    "min f_eff/f_T on S99", "#S99 with f_eff < 0.7 f_T"], rows), ""]
    c2 = data["C2"]
    if "predicted_total" in c2:
        L += ["## C2: the A6 reference hits", "",
              md_table(["circuit", "shots", "observed", "fault-free only", "trajectory prediction", "s.e."],
                       [[c, v["shots"], v["observed"], fmt(v["fault_free_only"]), fmt(v["predicted"]), fmt(v["se"])]
                        for c, v in c2["per_circuit"].items()]
                       + [["total", sum(v["shots"] for v in c2["per_circuit"].values()), c2["observed_total"],
                           fmt(c2["fault_free_only_total"]), fmt(c2["predicted_total"]), fmt(c2["predicted_total_se"])]]),
              "", f"Two-sided Poisson P = {fmt(c2['two_sided_poisson_P'])} (with the trajectory uncertainty of the "
              f"mean integrated: {fmt(c2['two_sided_P_with_mu_uncertainty'])}); (observed - predicted)/sd = "
              f"{fmt(c2['z_observed_minus_predicted'])}.  Pooled trajectory $f_{{\\rm hit}}$ = {fmt(c2['pooled_f_hit_traj'])} "
              f"against the A6 reference-string estimate {fmt(c2['A6_pooled_reference_string_f'])} "
              f"(95 % {[fmt(x) for x in c2['A6_pooled_reference_string_f_95']]}).", ""]
    a4 = c2["A4_control"]
    if a4.get("present"):
        L += ["## A4: bit-flip-only counting control (Aer sampler path)", "",
              f"{a4['shots']} shots, seed {a4['seed']}: **{a4['hits']}** reference hits; prediction from the xx "
              f"trajectory arm {fmt(a4['predicted'])} +- {fmt(a4['predicted_se'])} (fault-free only "
              f"{fmt(a4['fault_free_only'])}), Poisson 95 % band {a4['poisson_95_band']}, two-sided P "
              f"{fmt(a4['two_sided_poisson_P'])}; the A6 depolarizing run gave {a4['A6_like_count_for_280_shots']} "
              f"in the same number of shots.", ""]
    c3 = data["C3"]
    if "predicted" in c3:
        L += ["## C3: Z-only stratum vs the phase-only check", "",
              f"{c3['n_z_only']} Z-only faulty trajectories of B0_ref25_k1, mean pre-readout $p_\\tau$(ref) = "
              f"{fmt(c3['h_Z'])} (s.e. {fmt(c3['h_Z_se'])}); prediction 40 [g0 p_ref + (1 - g0) h_Z] = "
              f"{fmt(c3['predicted'])}, band {c3['poisson_95_band']}, observed {c3['observed']}."]
        rw = c3.get("information_reweighted_to_phase_channel")
        if rw:
            L += ["", f"Information: reweighted to the phase channel's event-count distribution, h = {fmt(rw['h_faulty'])}, "
                  f"prediction {fmt(rw['predicted'])}, band {rw['poisson_95_band']} (mean weight {fmt(rw['mean_weight'])}, "
                  "expected 1).  " + rw["note"]]
        L += [""]
    au = data["C5_A6_path_audit"]
    L += ["## C5: A6-path audit", "", au["sampler"], "",
          md_table(["circuit", "rzz", "rx+ry", "manifest ZZ", "manifest PhasedX", "adjacent same-pair rzz"],
                   [[c, r["n_rzz"], r["n_noisy_1q_rx_ry"], r["manifest_n_zz"], r["manifest_n_phasedx"],
                     r["adjacent_same_pair_rzz_in_executed_circuit"]] for c, r in au["circuits"].items()]),
          "", f"Noise instructions {au['noise_model']['noise_instructions']}, basis {au['noise_model']['basis_gates']}.  "
          f"Prompt literal: {au['prompt_c5_literal']['note']}.", ""]
    L += ["## Where the faulty weight goes (Hamming distance from the reference, 20-bit strings)", ""]
    hdr = ["arm"] + [f"d={d}" for d in range(0, 7)] + ["d>=7"]
    rows = []
    for cid, s in arms.items():
        w = s["hamming"]["faulty_mean_weight_by_distance"]
        rows.append([cid] + [fmt(x, 3) for x in w[:7]] + [fmt(sum(w[7:]), 3)])
    L += [md_table(hdr, rows), ""]
    L += ["## STOP flags", "", "```", json.dumps(data["stop_flags"], indent=1), "```", "",

          "## Timing (A0)", "", "```", json.dumps(data["A0_timing"], indent=1), "```", "", env_block(), ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
