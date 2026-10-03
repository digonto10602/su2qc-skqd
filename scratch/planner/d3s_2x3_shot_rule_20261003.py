"""Planner arithmetic for prompts/28 (2026-10-03): rule D3'-S at 2x3.

Inputs: the frozen-circuit sector distributions of gate Q0P_2x3 (data/quantinuum/q0p_stages/verify.json
per_circuit.p_sector, the Aer statevector of the frozen native circuit), the manifests
(data/quantinuum/circuits_2x3/*.manifest.json: reference, counts, hqc_per_shot), the exact ground state of
each sector (skqd.exact.Model(3).reference(4.0, twoB)), lambda* (skqd.skqd.poisson_lambda_star),
the HQC formula (skqd.quantinuum_native.hqc_per_shot, 5 HQC per job, 10,000 shots per job).
Output: scratch/planner/d3s_2x3_shot_rule_20261003.json.  Everything here is to be reproduced by the
executor's gate (prompts/28 Part B); this file is the planner's prototype, not a validation record.
"""
import glob
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from skqd.exact import Model  # noqa: E402
from skqd.skqd import READOUT_FACTOR, poisson_lambda_star  # noqa: E402
from skqd import quantinuum_native as qn  # noqa: E402

G2, MARGIN, FLOOR, ROUND, MAXJ, JOB_BASE = 4.0, 0.7, 267, 100, 10000, 5.0
t0 = time.time()
V = json.load(open(os.path.join(ROOT, "data/quantinuum/q0p_stages/verify.json")))["per_circuit"]
mans = {}
for p in glob.glob(os.path.join(ROOT, "data/quantinuum/circuits_2x3/*.manifest.json")):
    m = json.load(open(p))
    if m.get("kind") == "calibration" or m["id"].startswith("CAL"):
        continue
    mans[m["id"]] = m
assert len(mans) == 44, len(mans)
lam = poisson_lambda_star()
M = Model(3)
out = {"inputs": {"lambda_star": lam, "margin": MARGIN, "floor": FLOOR, "round_to": ROUND, "readout_factor": READOUT_FACTOR,
                  "g2": G2, "job_base_hqc": JOB_BASE, "max_shots_per_job": MAXJ}, "sectors": {}, "plans": {}}


def ceil100(x):
    return int(np.ceil(max(float(x), 0.0) / ROUND) * ROUND)


def cost(shots):
    jobs, hqc = 0, 0.0
    for c, s in shots.items():
        nj = -(-int(s) // MAXJ)
        hqc += JOB_BASE * nj + s * qn.hqc_per_shot(mans[c]["counts"])
        jobs += nj
    return {"shots_total": int(sum(shots.values())), "jobs": jobs, "hqc_total": hqc}


for twoB, sec in ((0, "B=0"), (2, "B=1")):
    r = M.reference(G2, twoB, k=4)
    idx = [int(b) for b in r.indices]
    w = np.abs(r.ground) ** 2
    order = np.argsort(w)[::-1]
    S999 = np.sort(order[: r.support999])
    ids = sorted(c for c, m in mans.items() if int(m["twoB"]) == twoB)
    P = {}
    for c in ids:
        p = np.asarray(V[c]["p_sector"], float)
        assert len(p) == r.dim
        P[c] = p / p.sum()
    k4 = [c for c in ids if int(mans[c]["k"]) == 4]
    k_le3 = [c for c in ids if int(mans[c]["k"]) <= 4 and c not in k4]
    sum_all = sum(P[c] for c in ids)
    sum_k4 = sum(P[c] for c in k4)
    # reachability of the target support
    per_state = []
    for s in S999:
        per_state.append({"sector_pos": int(s), "basis_index": idx[s], "ground_weight": float(w[s]),
                          "sum_p_all_circuits": float(sum_all[s]), "sum_p_k4": float(sum_k4[s]),
                          "max_p_any_circuit": float(max(P[c][s] for c in ids))})
    # tail class per circuit (for the f_T estimator): states != reference with p >= 1e-3
    tails = {}
    for c in ids:
        ref_pos = idx.index(int(mans[c]["reference"]))
        mask = (P[c] >= 1e-3)
        mask[ref_pos] = False
        tails[c] = {"p_reference": float(P[c][ref_pos]), "n_tail_states": int(mask.sum()),
                    "tail_weight": float(P[c][mask].sum()),
                    "tail_in_S999": int(np.isin(np.where(mask)[0], S999).sum()),
                    "S999_weight": float(P[c][S999].sum())}
    out["sectors"][sec] = {"dim": r.dim, "E0": float(r.E0), "support999_size": int(r.support999),
                           "support99_size": int(r.support99),
                           "S999_min_sum_p_all": float(min(x["sum_p_all_circuits"] for x in per_state)),
                           "S999_min_sum_p_k4": float(min(x["sum_p_k4"] for x in per_state)),
                           "S999_min_max_p": float(min(x["max_p_any_circuit"] for x in per_state)),
                           "S999_min_ground_weight": float(min(x["ground_weight"] for x in per_state)),
                           "S999_per_state": per_state, "tails": tails,
                           "full_sector_min_sum_p_k4": float(sum_k4.min()),
                           "full_sector_states_sum_p_k4_below_1e-6": int((sum_k4 < 1e-6).sum())}
    for f in (0.05, 0.10, 0.15):
        y = READOUT_FACTOR * MARGIN * f
        # (a) D3' allocation restricted to S999: floor on k<=3, N4 on k=4
        base = sum(FLOOR * y * P[c][S999] for c in k_le3)
        denom = sum(y * P[c][S999] for c in k4)
        need = (lam - base) / denom
        N4 = max(ceil100(need.max()), FLOOR)
        shots_a = {c: (N4 if c in k4 else FLOOR) for c in ids}
        # (b) even spread over all circuits of the sector
        N_even = ceil100((lam / (y * sum_all[S999])).max())
        shots_b = {c: N_even for c in ids}
        # (c) LP: min total shots s.t. every S999 state >= lambda*, N_c >= floor
        from scipy.optimize import linprog
        A = -np.array([[y * P[c][s] for c in ids] for s in S999])
        res = linprog(np.ones(len(ids)), A_ub=A, b_ub=-lam * np.ones(len(S999)),
                      bounds=[(FLOOR, None)] * len(ids), method="highs")
        assert res.success, res.message
        shots_c = {c: max(ceil100(x), FLOOR) for c, x in zip(ids, res.x)}
        lam_c = sum(shots_c[c] * y * P[c][S999] for c in ids)
        assert lam_c.min() >= lam - 1e-9
        # D3-type union reading from data/S2D_recall_at_f.json, as gate Q0P_2x3 computes it
        rec = json.load(open(os.path.join(ROOT, "data/S2D_recall_at_f.json")))["results"]
        base_u = int(rec[f"{sec}|f=0.1"]["shot_rule_union_reading_N_sector"])
        n_u = int(np.ceil(base_u * 0.1 / (MARGIN * f) / 100.0) * 100)
        per_u = int(np.ceil(n_u / len(ids)))
        shots_u = {c: per_u for c in ids}
        out["plans"][f"{sec}|f={f:.2f}"] = {
            "f": f, "clean_yield_per_shot": y,
            "D3S_k4_scaled": {"N4": N4, "need_max": float(need.max()), "shots": shots_a, **cost(shots_a),
                              "lambda_min_S999": float((base + N4 * denom).min()),
                              "lambda_min_full_sector": float(sum(shots_a[c] * y * P[c] for c in ids).min())},
            "D3S_even": {"N_per_circuit": N_even, "shots": shots_b, **cost(shots_b)},
            "D3S_LP": {"shots": shots_c, **cost(shots_c), "lambda_min_S999": float(lam_c.min())},
            "D3type_union": {"N_sector_rule": n_u, "per_circuit": per_u, "shots": shots_u, **cost(shots_u),
                             "lambda_min_S999": float(sum(per_u * y * P[c][S999] for c in ids).min())},
        }
    print(sec, "done", round(time.time() - t0), "s", flush=True)
out["runtime_s"] = time.time() - t0
json.dump(out, open(os.path.join(ROOT, "scratch/planner/d3s_2x3_shot_rule_20261003.json"), "w"), indent=1)
for k, v in out["plans"].items():
    print(k, "| D3S k4:", v["D3S_k4_scaled"]["N4"], v["D3S_k4_scaled"]["shots_total"], round(v["D3S_k4_scaled"]["hqc_total"]),
          "| even:", v["D3S_even"]["N_per_circuit"], v["D3S_even"]["shots_total"], round(v["D3S_even"]["hqc_total"]),
          "| LP:", v["D3S_LP"]["shots_total"], round(v["D3S_LP"]["hqc_total"]),
          "| D3type:", v["D3type_union"]["shots_total"], round(v["D3type_union"]["hqc_total"]), "lam_min", round(v["D3type_union"]["lambda_min_S999"], 2))
for sec, s in out["sectors"].items():
    print(sec, {k: s[k] for k in s if k not in ("S999_per_state", "tails")})
    for c, t in s["tails"].items():
        if c.endswith("k1") or c.endswith("k4"):
            print("  ", c, t)

# ---- addendum (same run): expected clean-only recall floors and the S99 variant ---------------
from scipy.optimize import linprog  # noqa: E402
add = {}
for twoB, sec in ((0, "B=0"), (2, "B=1")):
    r = M.reference(G2, twoB, k=4)
    w = np.abs(r.ground) ** 2
    order = np.argsort(w)[::-1]
    S999 = np.sort(order[: r.support999]); S99 = np.sort(order[: r.support99])
    ids = sorted(c for c, m in mans.items() if int(m["twoB"]) == twoB)
    P = {c: np.asarray(V[c]["p_sector"], float) for c in ids}
    P = {c: p / p.sum() for c, p in P.items()}
    for f in (0.05, 0.10, 0.15):
        y = READOUT_FACTOR * MARGIN * f
        key = f"{sec}|f={f:.2f}"
        plans = out["plans"][key]
        rows = {}
        for name in ("D3S_k4_scaled", "D3S_even", "D3S_LP", "D3type_union"):
            sh = plans[name]["shots"]
            lam_s = sum(sh[c] * y * P[c] for c in ids)
            rows[name] = {"recall_floor_S999": float(np.mean(1 - np.exp(-lam_s[S999]))),
                          "recall_floor_S99": float(np.mean(1 - np.exp(-lam_s[S99]))),
                          "P_all_S999_seen": float(np.prod(1 - np.exp(-lam_s[S999]))),
                          "weight_floor_S999": float(np.sum(w[S999] * (1 - np.exp(-lam_s[S999])))),
                          "n_S999_states_below_lambda_star": int((lam_s[S999] < lam).sum())}
        A = -np.array([[y * P[c][s] for c in ids] for s in S99])
        res = linprog(np.ones(len(ids)), A_ub=A, b_ub=-lam * np.ones(len(S99)), bounds=[(FLOOR, None)] * len(ids), method="highs")
        sh = {c: max(ceil100(x), FLOOR) for c, x in zip(ids, res.x)}
        lam_s = sum(sh[c] * y * P[c] for c in ids)
        rows["D3S99_LP"] = {"shots": sh, **cost(sh), "recall_floor_S999": float(np.mean(1 - np.exp(-lam_s[S999]))),
                            "recall_floor_S99": float(np.mean(1 - np.exp(-lam_s[S99]))),
                            "lambda_min_S99": float(lam_s[S99].min()), "lambda_min_S999": float(lam_s[S999].min()),
                            "n_S999_states_below_lambda_star": int((lam_s[S999] < lam).sum())}
        plans["recall_floors"] = rows
        plans["D3S99_LP"] = rows["D3S99_LP"]
json.dump(out, open(os.path.join(ROOT, "scratch/planner/d3s_2x3_shot_rule_20261003.json"), "w"), indent=1)
for k, v in out["plans"].items():
    print(k)
    for name, rr in v["recall_floors"].items():
        print("   ", name, "shots", v[name]["shots_total"], "hqc", round(v[name]["hqc_total"]), {a: (round(b, 4) if isinstance(b, float) else b) for a, b in rr.items() if a != "shots"})

# ---- addendum 2: rule D3'-R (the planner's ruling, prompts/28): LP for lambda* on S99, then the k = 4
# circuits scaled by the smallest multiple of 100 until P(clean-only recall of S999 >= 0.9) >= 0.95
# (Poisson-binomial over the S999 states, exact DP); floor 267 kept exactly.
R_TARGET, P_TARGET = 0.9, 0.95


def recall_tail_prob(q, k_needed):
    """P(sum of independent Bernoulli(q_i) >= k_needed), exact DP."""
    dist = np.zeros(len(q) + 1); dist[0] = 1.0
    for qi in q:
        dist[1:] = dist[1:] * (1 - qi) + dist[:-1] * qi
        dist[0] *= (1 - qi)
    return float(dist[k_needed:].sum())


for twoB, sec in ((0, "B=0"), (2, "B=1")):
    r = M.reference(G2, twoB, k=4)
    w = np.abs(r.ground) ** 2
    order = np.argsort(w)[::-1]
    S999 = np.sort(order[: r.support999]); S99 = np.sort(order[: r.support99])
    k_needed = int(np.ceil(R_TARGET * len(S999)))
    ids = sorted(c for c, m in mans.items() if int(m["twoB"]) == twoB)
    k4 = [c for c in ids if int(mans[c]["k"]) == 4]
    P = {c: np.asarray(V[c]["p_sector"], float) for c in ids}
    P = {c: p / p.sum() for c, p in P.items()}
    for f in (0.05, 0.10, 0.15):
        y = READOUT_FACTOR * MARGIN * f
        A = -np.array([[y * P[c][s] for c in ids] for s in S99])
        res = linprog(np.ones(len(ids)), A_ub=A, b_ub=-lam * np.ones(len(S99)), bounds=[(FLOOR, None)] * len(ids), method="highs")
        sh = {c: (FLOOR if x <= FLOOR + 1e-9 else ceil100(x)) for c, x in zip(ids, res.x)}
        extra = 0
        while True:
            sh2 = {c: sh[c] + (extra if c in k4 else 0) for c in ids}
            lam_s = sum(sh2[c] * y * P[c] for c in ids)
            pr = recall_tail_prob(1 - np.exp(-lam_s[S999]), k_needed)
            if pr >= P_TARGET:
                break
            extra += ROUND
        lam_s = sum(sh2[c] * y * P[c] for c in ids)
        out["plans"][f"{sec}|f={f:.2f}"]["D3R"] = {
            "shots": sh2, **cost(sh2), "k4_extra_per_circuit": extra, "lp_S99_shots_total": int(sum(sh.values())),
            "lambda_min_S99": float(lam_s[S99].min()), "lambda_min_S999": float(lam_s[S999].min()),
            "recall_floor_S999": float(np.mean(1 - np.exp(-lam_s[S999]))),
            "P_recall_S999_ge_0.9": pr, "k_needed_of_S999": k_needed,
            "n_S999_states_below_lambda_star": int((lam_s[S999] < lam).sum()),
            "P_all_S99_seen": float(np.prod(1 - np.exp(-lam_s[S99]))),
            "rule": "LP: min total shots s.t. every S99 state >= lambda* at y = 0.82 x 0.7 x f, N_c >= 267; then the k = 4 "
                    "circuits +extra (multiple of 100) until P(recall of S999 >= 0.9) >= 0.95 (Poisson-binomial, clean shots only)"}
        for name in ("D3type_union", "D3S_LP", "D3S99_LP"):
            lam_s = sum(out["plans"][f"{sec}|f={f:.2f}"][name]["shots"][c] * y * P[c] for c in ids)
            out["plans"][f"{sec}|f={f:.2f}"]["recall_floors"][name]["P_recall_S999_ge_0.9"] = recall_tail_prob(1 - np.exp(-lam_s[S999]), k_needed)
json.dump(out, open(os.path.join(ROOT, "scratch/planner/d3s_2x3_shot_rule_20261003.json"), "w"), indent=1)
print("---- D3'-R")
for k, v in out["plans"].items():
    d = v["D3R"]
    print(k, "shots", d["shots_total"], "jobs", d["jobs"], "hqc", round(d["hqc_total"]), "extra", d["k4_extra_per_circuit"], "lp", d["lp_S99_shots_total"],
          "lam_min S99/S999", round(d["lambda_min_S99"], 2), round(d["lambda_min_S999"], 2), "floor", round(d["recall_floor_S999"], 4),
          "P(R>=0.9)", round(d["P_recall_S999_ge_0.9"], 4), "below", d["n_S999_states_below_lambda_star"],
          "| D3type P(R>=0.9)", round(v["recall_floors"]["D3type_union"]["P_recall_S999_ge_0.9"], 4),
          "| S99LP P", round(v["recall_floors"]["D3S99_LP"]["P_recall_S999_ge_0.9"], 4))
