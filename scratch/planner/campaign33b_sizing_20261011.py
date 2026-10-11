#!/usr/bin/env python3
"""Planner arithmetic for prompts/33b (2026-10-11): scenario-aware class-4 sizing from the recorded per-chunk
timings of validation/C4_FCELLS_A.json (job 59570315) and data/campaign33/sizing_33a.json.  Orientation only;
scripts/campaign33_resize.py recomputes everything it uses (rule 1)."""
import json, math, numpy as np
R = "/home/digimonk/Projects/su2qc-skqd-v0.1.0/.claude/worktrees/agent-a10b1f247068a4adc"
fa = json.load(open(f"{R}/validation/C4_FCELLS_A.json"))
sz = json.load(open(f"{R}/data/campaign33/sizing_33a.json"))
out = {"inputs": {"fcells_a": "validation/C4_FCELLS_A.json job 59570315 data.cells.*.chunks, data.ladder.points",
                  "sizing": "data/campaign33/sizing_33a.json runs.*.total_shots, cv3.*.shots, fit, budget"}}
# ---- 1. per-cell slope fits t = c + b n over the recorded chunks
cells = fa["data"]["cells"]
fits = {}
for key, c in cells.items():
    xs, ys = [], []
    for circ, chs in c["chunks"].items():
        for ch in chs:
            xs.append(ch["shots"]); ys.append(ch["seconds"])
    xs, ys = np.array(xs, float), np.array(ys, float)
    A = np.vstack([np.ones_like(xs), xs]).T
    (cc, bb), *_ = np.linalg.lstsq(A, ys, rcond=None)
    fits[key] = {"c_s": float(cc), "b_s_per_shot": float(bb), "n_chunks": len(xs),
                 "rms_s": float(np.sqrt(np.mean((A @ np.array([cc, bb]) - ys) ** 2))),
                 "cell_seconds": c["seconds"], "cell_shots": c["shots"], "complete": c["complete"],
                 "r_eff_1428": float(bb + cc / 1428)}
lad = sz["fit"]; r_lad = lad["r_eff_s_per_shot"]; chunk = lad["chunk"]
bE1 = fits["E1|NAT-O0"]["b_s_per_shot"]
for k, v in fits.items():
    v["ratio_slope_to_E1_O0"] = v["b_s_per_shot"] / bE1
    v["ratio_reff_to_ladder"] = v["r_eff_1428"] / r_lad          # the executor's statistic
out["cell_fits"] = fits
# ---- 2. scenario rates: r_s = r_ladder x max over measured families of (b_{s,fam} / b_{E1,O0})
ratio = {}
for k, v in fits.items():
    s = k.split("|")[0]
    ratio[s] = max(ratio.get(s, 0.0), v["ratio_slope_to_E1_O0"])
ratio["E1"] = max(ratio["E1"], 1.0)
# unmeasured scenarios: E6*/E7* are the E1 builder with other parameters (same instruction set) -> E1's ratio,
# labelled 'assumed = E1 (same channel classes)'; E8 on IR-L3-RZZ: gate S3 measured 0.0199 s/shot at 476-shot
# calls (validation/S3.json data.cost.seconds_per_shot_best_ladder) < the E1 ladder 0.0288 at 476 -> E1's ratio
# as an upper bound until C4_FCELLS_B's s3_redo timing is read.
assumed = {"E6a": "E1", "E6b": "E1", "E6c": "E1", "E7_0.05": "E1", "E7_0.07": "E1", "E7_0.10": "E1",
           "E7_0.15": "E1", "E8": "E1 (upper bound; S3 0.0199 < E1 ladder 0.0288 at 476)"}
for s, src in assumed.items():
    ratio[s] = ratio["E1"]
rate = {s: r_lad * q for s, q in ratio.items()}
out["scenario_ratio"] = ratio; out["scenario_rate_s_per_shot"] = rate; out["assumed"] = assumed
# ---- 3. N_max per kind and parts per run
B = sz["budget"]; share = B["shares"]
def nmax(kind, s):
    return int(math.floor(share[kind] * (B["budget_s"] - B["setup_s"]) / (B["contingency"] * rate[s])))
runs = {}
tot_slots_f = 0
for run, r in sz["runs"].items():
    s = r["scenario"]; kind = r["kind"]
    nm = nmax(kind, s)
    n = max(1, math.ceil(r["total_shots"] / nm))
    runs[run] = {"scenario": s, "kind": kind, "total_shots": r["total_shots"], "rate": rate[s], "N_max": nm,
                 "parts_33a": r["parts"], "parts_33b": n, "slots_33b": n - 1,
                 "sampling_s_at_rate": r["total_shots"] * rate[s],
                 "fraction_of_part_reached_33a": min(1.0, (r["N_max"] * r_lad) / (max(r["part_shots"]) * rate[s]))}
    tot_slots_f += n - 1
out["runs"] = runs; out["f_slots_total_33b"] = tot_slots_f
# ---- 4. cv3 samples -> parts at the fcells share
cv3 = {}
for run, c in sz["cv3"].items():
    s = sz["runs"][run]["scenario"]
    nm = nmax("fcells", s)
    cv3[run] = {"shots": c["shots"], "N_eq": c["N_eq"], "rate": rate[s], "N_max_fcells": nm,
                "parts": math.ceil(c["shots"] / nm), "sampling_s": c["shots"] * rate[s]}
out["cv3"] = cv3
# ---- 5. dropped f-cells: cost = the measured O0 cell seconds of the scenario (max over measured families)
cost = {}
for k, v in fits.items():
    s = k.split("|")[0]; cost[s] = max(cost.get(s, 0.0), v["cell_seconds"])
cap = share["fcells"] * (B["budget_s"] - B["setup_s"]) / B["contingency"]      # 1728 s of predicted sampling
prio_var = ["NAT-O1", "NAT-O2", "NAT-O3", "NAT-O4", "NAT-O6"]
prio_scen = ["E1", "E2", "E3", "E4", "E5a", "E5b", "E5c"]
dropped = [tuple(x) for x in sz["fcells"]["dropped"]]
order = [(s, f) for s in prio_scen for f in prio_var if (s, f) in dropped]
slots, cur, cur_s = [], [], 0.0
for s, f in order:
    if cur_s + cost[s] > cap and cur:
        slots.append({"cells": cur, "predicted_s": cur_s}); cur, cur_s = [], 0.0
    cur.append([s, f]); cur_s += cost[s]
if cur:
    slots.append({"cells": cur, "predicted_s": cur_s})
out["fcells"] = {"cell_cost_s": cost, "slot_capacity_s": cap, "total_predicted_s": sum(cost[s] for s, _ in order),
                 "slots": slots, "n_slots": len(slots), "order": "scenario E1..E5c, then variant O1..O6 (first fit)"}
# ---- 6. E1 vs E5b f-cell: are they distinguishable at 2000 shots?
def z(a, b):
    sa = (a["f_hit_ci"][1] - a["f_hit_ci"][0]) / 3.92; sb = (b["f_hit_ci"][1] - b["f_hit_ci"][0]) / 3.92
    return (a["f_hit"] - b["f_hit"]) / math.sqrt(sa ** 2 + sb ** 2)
pk = {k: cells[k]["stats"]["pooled_k1"] for k in cells}
out["fcell_contrasts"] = {f"{k} vs E1|NAT-O0": {"f_hit": pk[k]["f_hit"], "f_hit_E1": pk["E1|NAT-O0"]["f_hit"],
                                                "z": z(pk[k], pk["E1|NAT-O0"])} for k in pk if k != "E1|NAT-O0"}
# ---- 7. calendar: measured round trip of wave 1
out["calendar"] = {"request_commit_utc": "2026-10-08T20:25:33Z (3a768f9)", "harvest_utc": "2026-10-09T21:07:28Z",
                   "round_trip_h": 24.7, "max_concurrent": 4, "jobs_per_round_trip": 4,
                   "hours_to_maintenance_from_2026-10-12T00Z": (21 - 12) * 24 + 6,
                   "round_trips_before_maintenance": ((21 - 12) * 24 + 6) / 24.7,
                   "jobs_before_maintenance_if_never_idle": 4 * math.floor(((21 - 12) * 24 + 6) / 24.7)}
json.dump(out, open(f"{R}/scratch/planner/campaign33b_sizing_20261011.json", "w"), indent=1)
print("ladder r_eff", r_lad, "chunk", chunk)
print(f"{'cell':12s} {'b':>8s} {'c':>6s} {'slope/E1':>8s} {'reff/lad':>8s} {'cell s':>7s}")
for k, v in fits.items():
    print(f"{k:12s} {v['b_s_per_shot']:8.5f} {v['c_s']:6.3f} {v['ratio_slope_to_E1_O0']:8.3f} {v['ratio_reff_to_ladder']:8.3f} {v['cell_seconds']:7.1f}")
print("scenario rates", {k: round(v, 5) for k, v in rate.items()})
print(f"{'run':8s} {'scen':8s} {'shots':>7s} {'Nmax':>6s} {'p33a':>4s} {'p33b':>4s} {'frac33a':>7s}")
for k, v in runs.items():
    print(f"{k:8s} {v['scenario']:8s} {v['total_shots']:7d} {v['N_max']:6d} {v['parts_33a']:4d} {v['parts_33b']:4d} {v['fraction_of_part_reached_33a']:7.2f}")
print("F slots needed (parts >= 2):", tot_slots_f)
for k, v in cv3.items():
    print("cv3", k, v)
print("fcells slots", len(slots), [round(s["predicted_s"]) for s in slots], "total", round(out["fcells"]["total_predicted_s"]))
for s in slots: print("   ", s["cells"])
for k, v in out["fcell_contrasts"].items(): print(k, round(v["z"], 2), round(v["f_hit"], 4))
print(out["calendar"])
