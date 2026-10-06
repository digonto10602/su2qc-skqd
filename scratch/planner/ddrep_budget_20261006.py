#!/usr/bin/env python3
"""Planner arithmetic for prompts/32 (gate H0_ddrep): execution estimate of the one-job design,
power of the ratio statistic, the budget check against the K1 reserve, and the two ends of the
coherent-pulse-error bound (hypothesis H_A) on the recorded T1 circuit.

Inputs: data/hardware/H0_ddtest_prep/circuits/*_T0.json (scheduled durations),
        data/hardware/H0_ddtest_prep/ibm_kingston_full_20261002T1906Z.json (x_error per qubit),
        validation/H0_ddtest.json (T0 excess hits, T3 interval, pulses per qubit of T1),
        data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json (498 s left).
Every number printed here is PLANNER ARITHMETIC; the gate's own estimator (h0_qpu_time) and the
prereg of gate H0_ddrep replace them on the day's record.  0 QPU s.
"""
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)

dd = json.load(open("validation/H0_ddtest.json"))["data"]
T0 = json.load(open("data/hardware/H0_ddtest_prep/circuits/B0_ref06_k1_T0.json"))["scheduled_duration_s"]
T1 = json.load(open("data/hardware/H0_ddtest_prep/circuits/B1_ref07_k1_T0.json"))["scheduled_duration_s"]
acct = json.load(open("data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json"))
rec = json.load(open("data/hardware/H0_ddtest_prep/ibm_kingston_full_20261002T1906Z.json"))
rep = rec["default_rep_delay_s"]
cal_T = dd["decision"]["stage_R_reserve_at_adopted_f"]["calibration_duration_s"]
SHOTS = 6000
remaining = acct["usage"]["usage_remaining_seconds"]

out = {}
pub = lambda T: SHOTS * (T + rep)
out["H0_ddtest_estimate_reproduced_s"] = 4 * pub(T0) + 4 * pub(T1) + 2 * pub(cal_T)
out["H0_ddtest_estimate_recorded_s"] = dd["execution_estimate_prereg_s"]
n_cells = 7                      # T0, T1, T3, M1, M2, M3, M4
train_T = 128 * float(rec["qubits"]["59"]["x_duration_s"])   # the longest pulse-train pub
out["A_estimate_s"] = n_cells * (pub(T0) + pub(T1)) + 2 * pub(cal_T) + 4 * pub(train_T)
out["A_estimate_without_train_pubs_s"] = n_cells * (pub(T0) + pub(T1)) + 2 * pub(cal_T)
out["billed_minus_estimate_history_s"] = {"H0_ddtest": 20.0 - dd["execution_estimate_prereg_s"],
                                          "H0_kpilot": 12.0 - 9.04, "H0_2x2_per_job": (53.0 - 41.71) / 5}
out["A_cap_estimate_s"] = 36.0
out["A_cap_billed_s"] = 45.0
out["K1_estimate_s"] = 182.45
out["K1_cap_billed_s"] = 300.0
out["remaining_s"] = remaining
out["after_A_cap_s"] = remaining - out["A_cap_billed_s"]
out["B_reserve_ok"] = (remaining - out["A_cap_billed_s"] >= out["K1_cap_billed_s"]
                       and remaining - out["A_cap_billed_s"] >= 1.3 * out["K1_estimate_s"])
# power of the ratio statistic at the 10-02 baseline (P5 of prompts/24, unchanged)
X = dd["decision"]["cells"]["T0"]["excess_hits"]
s = math.sqrt(2.0 / X)
out["power"] = {"X_T0_excess_per_cell": X, "sigma_lnR": s, "factor_95": math.exp(1.96 * s),
                "lower_bound_of_a_true_1.25": 1.25 * math.exp(-1.96 * s)}
lo, hi = dd["decision"]["cells"]["T3"]["R_95"]
s_old = (math.log(hi) - math.log(lo)) / (2 * 1.959963984540054)
out["R2_magnitude_test"] = {"lnR_T3_old": math.log(dd["decision"]["cells"]["T3"]["R"]), "sigma_old": s_old,
                            "tolerance_lnR_95": 1.96 * math.sqrt(s ** 2 + s_old ** 2)}
# H_A bound on the recorded T1: eps_q = sqrt(6 x_error_q) (fully coherent over-rotation at the RB level)
pulses = dd["decision"]["cells"]["T1"]["n_pulses_per_circuit"]
per_q = json.load(open("data/hardware/H0_ddtest_prep/circuits/B0_ref06_k1_T1.json"))["dd"]["pulses_per_physical_qubit"]
win, lin = 1.0, 1.0
for q, n in per_q.items():
    eps = math.sqrt(6 * rec["qubits"][q]["x_error"])
    win *= math.cos(8 * eps / 2) ** (2 * n / 8)      # coherent inside 8-pulse windows, random walk across
    lin *= math.cos(n * eps / 2) ** 2                # coherent over the whole circuit
out["H_A_bound_T1"] = {"per_window_coherent_8_pulse_windows": win, "fully_coherent_linear": lin,
                       "measured_R_T1": dd["decision"]["cells"]["T1"]["R"],
                       "null_ratio_T1": dd["decision"]["cells"]["T1"]["null_ratio"],
                       "note": "x_error == sx_error in the record (aliased): the x pulse's own error is unmeasured"}
json.dump(out, open("scratch/planner/ddrep_budget_20261006.json", "w"), indent=1)
print(json.dumps(out, indent=1))
