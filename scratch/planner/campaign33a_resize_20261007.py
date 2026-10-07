"""Planner arithmetic for prompts/33a (2026-10-07): re-sizing after the first CI wave of campaign 33.
Inputs: scratch/planner/C2_CAL_job59491475.json (= origin/master validation/C2_CAL.json, job 59491475),
validation/S3.json, data/hardware/K1_2x3_ibm_kingston/counts/*.json, the kingston record of 2026-10-06.
Every number printed here is labelled "planner arithmetic" in the prompt; the executor recomputes it in code."""
import json, math, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = lambda p: json.load(open(os.path.join(ROOT, p)))
out = {"inputs": {}}
cal = J("scratch/planner/C2_CAL_job59491475.json")["data"]
# ---- 1. per-call / per-shot fits of the custatevec ladders (t = n_calls * c + N * b, least squares)
def fit(points):
    xs = [(p["calls"], p["shots_done"], p["seconds"]) for p in points if "seconds" in p]
    if len(xs) < 2:
        return None
    # solve least squares for (c, b)
    import numpy as np
    A = np.array([[k, n] for k, n, _ in xs], float); y = np.array([t for *_, t in xs])
    c, b = np.linalg.lstsq(A, y, rcond=None)[0]
    return {"points": xs, "per_call_s": float(c), "per_shot_s": float(b)}
fits = {k: fit(v["ladder"]) for k, v in cal["cells"].items()}
out["ladder_fits"] = fits
pta_b = fits["pta|custatevec"]["per_shot_s"]; pta_c = fits["pta|custatevec"]["per_call_s"]
kr_b = fits["kraus|custatevec"]["per_shot_s"]; kr_c = fits["kraus|custatevec"]["per_call_s"]
kr_flat = cal["cells"]["kraus|custatevec"]["ladder"][1]["seconds_per_shot"]   # 3.177 at 32 shots (measured, no fit)
pta_512 = cal["cells"]["pta|custatevec"]["ladder"][3]["seconds_per_shot"]
# ---- 2. C2_CAL run 2 budget: budget 35 min (walltime 45 - 10), setup ~120 s, sampling share 0.75
B2 = 35 * 60; setup = 120
kraus_1024_fit = 8 * kr_c + 1024 * kr_b; kraus_512_fit = 4 * kr_c + 512 * kr_b
kraus_512_flat = 512 * kr_flat; kraus_1024_flat = 1024 * kr_flat
pta_1024 = 8 * pta_c + 1024 * pta_b
out["c2_cal_run2"] = {"budget_s": B2, "setup_s": setup, "sampling_share": 0.75,
                      "sampling_s_available": 0.75 * (B2 - setup),
                      "pta_1024_chunks128_s": pta_1024, "kraus_512_fit_s": kraus_512_fit, "kraus_512_flat_s": kraus_512_flat,
                      "kraus_1024_fit_s": kraus_1024_fit, "kraus_1024_flat_s": kraus_1024_flat,
                      "kraus_shots_that_fit_after_pta_fit": int((0.75 * (B2 - setup) - pta_1024) / kr_b),
                      "kraus_shots_that_fit_after_pta_flat": int((0.75 * (B2 - setup) - pta_1024) / kr_flat)}
# ---- 3. class-2 production per 60-min job: budget 50 min, setup 120 s, share 0.75
B = 50 * 60; avail = 0.75 * (B - setup)
out["c2_production_per_job"] = {"sampling_s_available": avail,
    "kraus_shots_fit_rate": int(avail / kr_b), "kraus_shots_flat_rate": int(avail / kr_flat),
    "pta_shots_fit_rate": int(avail / pta_b), "pta_shots_512_rate": int(avail / pta_512),
    "per_circuit_2_runs": {"kraus_fit": int(avail / kr_b / 2), "kraus_flat": int(avail / kr_flat / 2), "pta": int(avail / pta_512 / 2)},
    "per_circuit_4_runs_XY4": {"kraus_fit": int(avail / kr_b / 4), "kraus_flat": int(avail / kr_flat / 4), "pta": int(avail / pta_512 / 4)},
    "expected_accepted_at_K1_rate_5.8e-4": {"shots_500": 500 * 5.8e-4, "shots_4000": 4000 * 5.8e-4}}
# ---- 4. the hardware garbage structure (K1 counts): mean Hamming weight and per-position P(1)
hw = {}
for f in sorted(glob.glob(os.path.join(ROOT, "data/hardware/K1_2x3_ibm_kingston/counts/*.json"))):
    cnt = json.load(open(f)); cnt = cnt.get("counts", cnt)
    N = sum(cnt.values()); L = len(next(iter(cnt)))
    ones = [0] * L; s = 0; s2 = 0
    for k, v in cnt.items():
        w = k.count("1"); s += v * w; s2 += v * w * w
        for i, ch in enumerate(k):
            if ch == "1": ones[i] += v
    m = s / N; var = s2 / N - m * m
    hw[os.path.basename(f)[:-5]] = {"shots": N, "mean_hamming_weight": m, "sd_hamming_weight": math.sqrt(var),
                                    "se_mean": math.sqrt(var / N), "p1_by_string_position": [o / N for o in ones]}
out["k1_hardware_garbage_structure"] = hw
# ---- 5. power of the Kraus-vs-PTA agreement test at n shots per representation (binary strings, p ~ 0.5)
def power(n):
    sd_hw = math.sqrt(20 * 0.25)      # fully scrambled 20-bit string: sd of the Hamming weight ~ sqrt(20/4)
    return {"n": n, "se_mean_hw_one_sample": sd_hw / math.sqrt(n), "se_mean_hw_two_sample": sd_hw * math.sqrt(2 / n),
            "min_detectable_hw_shift_3sigma_two_sample": 3 * sd_hw * math.sqrt(2 / n),
            "se_marginal_one_sample": math.sqrt(0.25 / n), "min_detectable_marginal_shift_3sigma_two_sample": 3 * math.sqrt(0.5 / n)}
out["agreement_test_power"] = [power(n) for n in (512, 1024)]
hw_deficit_hw = 10.0 - hw["B0_ref117_k1"]["mean_hamming_weight"]
out["hardware_hw_deficit_vs_unital_limit"] = {"B0_ref117_k1": hw_deficit_hw, "B1_ref29_k1": 10.0 - hw["B1_ref29_k1"]["mean_hamming_weight"],
                                              "sigma_at_512_one_sample": hw_deficit_hw / power(512)["se_mean_hw_one_sample"],
                                              "sigma_at_1024_one_sample": hw_deficit_hw / power(1024)["se_mean_hw_one_sample"]}
# ---- 6. the patch's T1/T2 and the relaxation over the scheduled duration
rec = J("data/hardware/K0_prep/ibm_kingston_full_20261006T0652Z.json")["qubits"]
phys = [50, 51, 52, 53, 54, 55, 58, 59, 68, 69, 70, 71, 72, 73, 74, 75, 79, 92, 93, 94, 95]
T = 0.0004111520000000163
rows = {str(p): {"T1_us": rec[str(p)]["T1_s"] * 1e6, "T2_us": rec[str(p)]["T2_s"] * 1e6, "T2_gt_T1": rec[str(p)]["T2_s"] > rec[str(p)]["T1_s"],
                 "exp_minus_T_over_T1": math.exp(-T / rec[str(p)]["T1_s"])} for p in phys}
out["patch_relaxation"] = {"scheduled_duration_s": T, "qubits": rows, "n_T2_gt_T1": sum(r["T2_gt_T1"] for r in rows.values()),
                           "mean_exp_minus_T_over_T1": sum(r["exp_minus_T_over_T1"] for r in rows.values()) / len(rows)}
# ---- 7. class-4 sizing bands (native 20-qubit circuits): S3's two rates and the inferred per-call set-up
s3 = J("validation/S3.json")["data"]["cost"]
r_best = s3["seconds_per_shot_best_ladder"]; r_mean = s3["seconds_per_shot_mean"]
c_call = (r_mean - r_best) * 100          # S3 sampled 32 x 100 shots, one call each: the per-call set-up implied by the two rates
r_476 = r_best + c_call / 476
out["class4_rates"] = {"s3_best_ladder": r_best, "s3_mean_100_shot_calls": r_mean, "implied_per_call_s": c_call,
                       "r_eff_at_chunk_476": r_476, "r_eff_at_chunk_1428": r_best + c_call / 1428, "contingency": 1.25}
def fits_in(shots, share, rate):
    return shots * rate * 1.25 <= share * (B - setup)
plan = {"quota_half_1e5": (100000, 0.75), "plan_B1_67600": (67600, 0.6), "plan_B1_F5_99000": (99000, 0.6),
        "plan_B0_27309": (27309, 0.6), "plan_B0_F5_34909": (34909, 0.6), "fcells_A_80000": (80000, 0.75), "fcells_B_73200": (73200, 0.75)}
out["class4_fit"] = {k: {"shots": n, "share": sh, "max_shots_at_r_best": int(sh * (B - setup) / (r_best * 1.25)),
                         "max_shots_at_r_476": int(sh * (B - setup) / (r_476 * 1.25)),
                         "max_shots_at_r_mean": int(sh * (B - setup) / (r_mean * 1.25)),
                         "fits_r_best": fits_in(n, sh, r_best), "fits_r_476": fits_in(n, sh, r_476), "fits_r_mean": fits_in(n, sh, r_mean),
                         "parts_at_r_476": math.ceil(n / int(sh * (B - setup) / (r_476 * 1.25)))} for k, (n, sh) in plan.items()}
# ---- 8. extra part slots needed under r_476 (the executor recomputes with the C4_FCELLS_A ladder)
p = out["class4_fit"]
extra = (4 * (p["quota_half_1e5"]["parts_at_r_476"] - 1) * 2      # F4 and F8: 4 half-tokens each
         + 5 * (p["plan_B1_67600"]["parts_at_r_476"] - 1) + (p["plan_B1_F5_99000"]["parts_at_r_476"] - 1)
         + 6 * (p["plan_B0_27309"]["parts_at_r_476"] - 1))
out["extra_part_slots_at_r_476"] = extra
out["noise_sites"] = {"IBM-T0_B0_ref117_k1": {"cz": 5659, "sx": 11401, "x_pulses_replaced_by_delays_in_T0": 2656, "delays_T3_manifest": 5596, "measure": 20, "n_qubits": 21},
                      "NAT-O0_mean": {"rzz": 2158, "one_qubit": 3053, "measure": 20, "n_qubits": 20},
                      "ratio_sites_times_state": ((5659 + 11401 + 5596 + 20) / (2158 + 3053 + 20)) * 2,
                      "measured_ratio_pta_512_over_s3_best": pta_512 / r_best}
json.dump(out, open(os.path.join(ROOT, "scratch/planner/campaign33a_resize_20261007.json"), "w"), indent=1)
print(json.dumps({k: out[k] for k in ("ladder_fits", "c2_cal_run2", "c2_production_per_job", "hardware_hw_deficit_vs_unital_limit",
                                       "agreement_test_power", "class4_rates", "class4_fit", "extra_part_slots_at_r_476", "noise_sites")}, indent=1, default=str)[:9000])
print("n_T2_gt_T1", out["patch_relaxation"]["n_T2_gt_T1"], "mean exp(-T/T1)", out["patch_relaxation"]["mean_exp_minus_T_over_T1"])
print({k: (v["mean_hamming_weight"], v["se_mean"]) for k, v in hw.items()})
# ---- 9. readout asymmetry's share of the hardware Hamming-weight deficit (K1 readout block, 20 patch qubits)
ro = J("validation/K1_2x3_fpilot.json")["data"]["readout"]
p00 = sum(ro["P_0_given_0"]) / 20; p11 = sum(ro["P_1_given_1"]) / 20
out["readout_share_of_hw_deficit"] = {"mean_P00": p00, "mean_P11": p11, "hw_shift_uniform_string": 10 * ((1 - p11) - (1 - p00)),
                                      "note": "a uniform 20-bit string read through the mean confusion loses 10[(1-P11)-(1-P00)] bits of weight"}
json.dump(out, open(os.path.join(ROOT, "scratch/planner/campaign33a_resize_20261007.json"), "w"), indent=1)
print("readout share", out["readout_share_of_hw_deficit"])
