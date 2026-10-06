#!/usr/bin/env python3
"""Planner arithmetic for prompts/33 (2026-10-06): matched-f error rates, per-job sizing, totals.
Inputs are read from validation/*.json and data/*.json; nothing here is a gate result."""
import json, math, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
J = lambda p: json.load(open(os.path.join(ROOT, p)))
out = {"inputs": {}, "matched_f": {}, "jobs": [], "totals": {}}

# --- inputs -------------------------------------------------------------------------------
s3 = J("validation/S3.json")["data"]
sps = s3["cost"]["seconds_per_shot_best_ladder"]            # 0.0198663 s/shot, 20 q, A100, job 58771538
out["inputs"]["s_per_shot_S3_best_ladder"] = sps
out["inputs"]["s_per_shot_S3_batched_32x14"] = s3["cost"]["seconds_per_shot_mean"]
out["inputs"]["S3_gpu_util_pct"] = s3["run"]["gpu_telemetry"]["mean_utilization_pct"]
out["inputs"]["S3_peak_mem_mib"] = s3["run"]["gpu_telemetry"]["peak_memory_mib"]
l4 = J("validation/L4.json")["data"]
out["inputs"]["s_per_shot_L4_12q"] = l4["B=0"]["t_per_shot"]
dev = J("data/quantinuum/devices_20261002.json")
h22 = dev["rows"]["2x3|quantinuum_h2_2"]; hel = dev["rows"]["2x3|quantinuum_helios_1"]
n2, n1, nm = dev["prototype_reproduction"]["quantinuum_h2_2"]["counts"]    # 2158, 3053, 20
out["inputs"]["counts_mean_circuit"] = {"n_2q": n2, "n_1q_phasedx": n1, "n_meas": nm}
out["inputs"]["H2-2"] = {"eps2": h22["eps2"], "eps1": h22["eps1"], "eps_ro": h22["eps_ro"],
                          "f_gate_only_mean": h22["f_gate_only_mean"], "eps2_for_mean_f_0.1": h22["eps2_for_mean_f_0.1"]}
out["inputs"]["Helios-1"] = {"eps2": hel["eps2"], "eps1": hel["eps1"], "eps_ro": hel["eps_ro"],
                              "f_gate_only_mean": hel["f_gate_only_mean"]}
plan = J("validation/CV_2x3_plan.json")["data"]["plan"]
shots = {f: {s: plan[f][s]["final_shots_total"] for s in plan[f]} for f in plan}
out["inputs"]["plan_of_record_shots"] = shots
cft = J("data/cf_trajectories/r_nc.json")
out["inputs"]["r_nc"] = cft.get("r_nc")

# --- matched-f: eps2 such that the mean gate-only f equals the target (eps1, eps_ro fixed at H2-2) ----------
def f_gate(eps2, eps1, ero): return (1-eps2)**n2 * (1-eps1)**n1 * (1-ero)**nm
def eps2_for(ftarget, eps1, ero):
    lnf = math.log(ftarget) - n1*math.log(1-eps1) - nm*math.log(1-ero)
    return 1 - math.exp(lnf/n2)
chk = f_gate(h22["eps2"], h22["eps1"], h22["eps_ro"])
out["matched_f"]["check_H2-2_formula_vs_table"] = {"formula": chk, "table": h22["f_gate_only_mean"], "abs_diff": abs(chk-h22["f_gate_only_mean"])}
chk2 = eps2_for(0.10, h22["eps1"], h22["eps_ro"])
out["matched_f"]["check_eps2_for_0.1_vs_table"] = {"formula": chk2, "table": h22["eps2_for_mean_f_0.1"], "abs_diff": abs(chk2-h22["eps2_for_mean_f_0.1"])}
for ft in (0.05, 0.07, 0.10, 0.15):
    e = eps2_for(ft, h22["eps1"], h22["eps_ro"])
    out["matched_f"][f"f={ft:.2f}"] = {"eps2": e, "scale_vs_H2-2": e/h22["eps2"], "f_check": f_gate(e, h22["eps1"], h22["eps_ro"])}
# Aer-channel no-fault probability g0 (fault-free fraction f0' before readout) for the A6 model
p2, p1 = h22["eps2"], h22["eps1"]
g0 = (1-15/16*p2)**n2 * (1-3/4*p1)**n1
out["matched_f"]["A6_g0_no_fault_before_readout_mean_counts"] = g0

# --- job sizing ---------------------------------------------------------------------------------
CONT = 1.25          # contingency on the measured s/shot (the 44-circuit batching cost 2.35x at 14 shots/call in S3; 1.25 assumes per-circuit chunks of >= 476 shots)
FIXED_MIN = 5.0      # load QPY, build noise model, decode, Ritz, report
def gpu_min(nshots, sps=sps): return nshots*sps*CONT/60.0 + FIXED_MIN
def job(token, wall_min, est_min, shots_, what, cls):
    out["jobs"].append({"token": token, "walltime_min": wall_min, "estimate_min": round(est_min,1), "shots": shots_, "what": what, "class": cls})
job("C1_IDEAL", 30, 12.0, "n/a (statevector + sampling; cost independent of shots)", "noiseless: IR level-0, native O0, IBM-routed; exactness + sampling checks; f=1 SKQD reference", 1)
job("C2_CAL", 45, 30.0, "ladder 8..512 x 2 models", "21-q ladder: Kraus from_backend-equivalent vs Pauli-twirled relaxation; batched vs cuStateVec; sizes C2_*", 2)
for t, w in (("C2_GATE","gate-only (unscheduled), 2 K1 circuits"),("C2_ECHO","ALAP delays, relaxation at echo T2"),("C2_STAR","ALAP delays, T2* = 0.174 T2echo"),("C2_XY4","T3 circuits as flown (XY4 pulses), echo T2 and T2*"),("C2_COH","C2_ECHO + coherent x over-rotation 0.018 rad")):
    job(t, 60, 50.0, "sized by C2_CAL to 50 min (target 1e5 per circuit)", w, 2)
job("C3_AER", 30, 12.0, "plan f=0.10 (133 909) + 2e5/sector", "frozen native O0 family, Aer GPU noiseless (qiskit path); TVD vs exact", 3)
job("C3_LE", 60, 50.0, "ladder 2..64 then fill to 50 min, 4 Stage-E circuits", "pytket-pecos H2-1LE local emulator (noiseless, CPU, env skqd-pecos); TVD vs C3_AER", 3)
job("C3_SEL", 60, 50.0, "ladder then fill to 50 min (optional)", "Selene QuEST ideal model via QIR (optional, env skqd-selene)", 3)
ncells_A, ncells_B = 40, 35
job("C4_FCELLS_A", 60, gpu_min(ncells_A*2000), ncells_A*2000, "f-cells 800/800/200/200: scenarios E1,E2,E3,E4,E5x3 x variants O0-O4 (+ladder)", 4)
job("C4_FCELLS_B", 60, gpu_min(ncells_B*2000)+2.0, ncells_B*2000+3200, "f-cells: E6x3,E7x4 x O0-O4; + faithful S3 3200-shot redo (seed 11, level-3 IR)", 4)
full = [("F1","H2-2 PV rates x O0","f=0.15"),("F2","Helios-1 PV rates x O0","f=0.15"),("F3","H2-2E emulator set 2025-07-16 (angle-scaled ZZ) x O0","f=0.15"),
        ("F5","matched f=0.07 x O0 (like-for-like CV_2x3_plan f=0.10 at 0.7 f)","f=0.10"),("F6","H2-2 PV + memory mid (t_round 1.1 ms) x O0","f=0.15"),
        ("F7","H2-2 PV x best exact optimisation","f=0.15")]
for tag, what, fp in full:
    for sec in ("B=0","B=1"):
        n = shots[fp][sec]
        job(f"C4_{tag}_{sec.replace('=','')}", 60, gpu_min(n), n, f"{what}; plan-of-record shots {fp} {sec}; order-kept sequence; CV0-CV5, certificates, recall", 4)
for tag, what in (("F4","matched f=0.10 x O0, 2e5 per sector (S1 redo; CV prefix at the f=0.10 plan)"),("F8","S3 declared model (eps2 1e-3, eps1 1e-4 on rz/rx/ry, ro 2e-3) x O0, 2e5 per sector (S3 criterion)")):
    for sec in ("B0","B1"):
        for b in ("a","b"):
            job(f"C4_{tag}_{sec}{b}", 60, gpu_min(100000), 100000, f"{what}; batch {b} of 2 x 1e5, {sec}", 4)
job("C4_CF", 60, 45.0, "K=2000 trajectories x 4 arms (statevector runs)", "CF_traj redo on GPU: r per arm, pooled r, r_nc", 4)
tot_est = sum(j["estimate_min"] for j in out["jobs"]); tot_wall = sum(j["walltime_min"] for j in out["jobs"])
out["totals"] = {"n_jobs": len(out["jobs"]), "sum_estimate_h": tot_est/60, "sum_walltime_cap_h": tot_wall/60,
                 "gpu_node_hours_estimate_G_over_4": tot_est/60/4, "gpu_node_hours_cap_G_over_4": tot_wall/60/4,
                 "days_at_concurrent4_cap16_per_day": math.ceil(len(out["jobs"])/16), "days_at_concurrent4_cap24_per_day": math.ceil(len(out["jobs"])/24),
                 "days_at_current_1_job_6_per_day": math.ceil(len(out["jobs"])/6),
                 "shots_total_noisy_gpu": sum(j["shots"] for j in out["jobs"] if isinstance(j["shots"], int))}
# sanity: how long would 2e5 per sector take at the measured rate, and the plan-of-record?
out["totals"]["minutes_2e5_shots_at_measured_rate_no_contingency"] = 2e5*sps/60
out["totals"]["minutes_plan_f0.10_B1_no_contingency"] = shots["f=0.10"]["B=1"]*sps/60
p = os.path.join(ROOT, "scratch", "planner", "campaign33_sizing_20261006.json")
json.dump(out, open(p, "w"), indent=1)
print(json.dumps(out["matched_f"], indent=1)); print(json.dumps(out["totals"], indent=1))
for j in out["jobs"]: print(f"{j['token']:16s} wall {j['walltime_min']:3d} est {j['estimate_min']:5.1f}  {j['shots']}")
