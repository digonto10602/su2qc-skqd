#!/usr/bin/env python3
"""
prompts/26 A5: the Quantinuum device table for 2x2 / 2x3 / 2x4 -> data/quantinuum/devices_20261002.json.

Every vendor number is encoded VERBATIM with its `source` URL and `read_on` date, copied from the
planner survey `reports/qpu_survey_2x3_20261002.md` section 2 (read 2026-10-02); every number this
script derives from them carries its inputs, and every assumption is flagged `ESTIMATE`.  The IonQ
rows are NOT retyped: they are read from `data/ionq_2x3_feasibility_20261001.json` and recomputed
with the same function to 1e-12.  The 2x3 counts are the FROZEN native circuits
(`data/quantinuum/circuits_2x3/*.manifest.json`, prompts/26 A3).

Nothing here is a measurement by this project; no account, no network.  Runs in `coding` (no pytket).

Usage: python scripts/quantinuum_device_table.py
"""
import glob
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from skqd.device_req import clean_shot_fraction, required_error  # noqa: E402
from skqd.quantinuum_native import (HQC_DIVISOR, HQC_JOB_BASE, MAX_HQC_PER_JOB,  # noqa: E402
                                    MAX_SHOTS_PER_JOB, hqc_per_shot)

READ_ON = "2026-10-02"
OUT = os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")
CIRC_DIR = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
PROTOTYPE = os.path.join(ROOT, "scratch", "planner", "quantinuum_2x3_prototype_20261002.json")
IONQ = os.path.join(ROOT, "data", "ionq_2x3_feasibility_20261001.json")
F_MEAN_MIN, F_WORST_MIN = 0.1, 0.05
REPRO_TOL = 1e-12

PERF = "https://docs.quantinuum.com/systems/user_guide/hardware_user_guide/performance_validation.html"
HELIOS_PAPER = "https://arxiv.org/html/2511.05465"
HELIOS_DS = ("https://docs.quantinuum.com/systems/_static/assets/data_sheets/"
             "Quantinuum%20Helios%20Product%20Data%20Sheet.pdf")
H2_DS = ("https://docs.quantinuum.com/systems/_static/assets/data_sheets/"
         "Quantinuum%20H2%20Product%20Data%20Sheet.pdf")
H2_EMU_DS = ("https://assets.website-files.com/62b9d45fb3f64842a96c9686/665f5f1f753da03b53be9da8_"
             "Quantinuum%20H2%20Emulator%20Product%20Data%20Sheet%20v1.2%204Jun24.pdf")
H1_PAGE = "https://www.quantinuum.com/products-solutions/system-model-h1-series"
AZURE_PROVIDER = "https://learn.microsoft.com/en-us/azure/quantum/provider-quantinuum"
AZURE_PRICING = "https://learn.microsoft.com/en-us/azure/quantum/pricing"
HELIOS_COSTING = "https://docs.quantinuum.com/systems/trainings/helios/getting_started/costing.html"
QCUP = "https://docs.olcf.ornl.gov/quantum/quantum_access.html"
WORKFLOW = "https://docs.quantinuum.com/systems/user_guide/hardware_user_guide/workflow.html"
SURVEY = "reports/qpu_survey_2x3_20261002.md section 2.1"

# ---- specifications, verbatim (survey section 2.1, every source read 2026-10-02) ------------
SPECS = {
    "quantinuum_h2_2": {
        "device_name": "H2-2", "source": [PERF, H2_DS], "read_on": READ_ON, "transcribed_from": SURVEY,
        "verbatim": {"two_qubit_gate_error": "8.3e-04", "two_qubit_gate_error_uncertainty": "4.8e-05",
                     "one_qubit_gate_error": "2.8e-05", "SPAM": "6.7e-04 (0), 1.2e-03 (1)",
                     "memory_error_per_depth1_circuit_time": "1.2e-04",
                     "parallel_two_qubit_operations": "4 (data sheet)", "qubits": "56",
                     "connectivity": "all-to-all",
                     "native_gates": "Rxy (PhasedX), Rz (virtual), ZZMax, ZZPhase (RZZ), TK2"},
        "eps2": 8.3e-4, "eps1": 2.8e-5, "eps_ro_0": 6.7e-4, "eps_ro_1": 1.2e-3,
        "memory_error_per_depth1": 1.2e-4, "zones": 4, "qubits": 56,
    },
    "quantinuum_helios_1": {
        "device_name": "Helios-1", "source": [PERF, HELIOS_PAPER, HELIOS_DS, WORKFLOW],
        "read_on": READ_ON, "transcribed_from": SURVEY,
        "verbatim": {"two_qubit_gate_error": "7.9e-04 (RB sweep); paper: 7.9(2)x10^-4",
                     "one_qubit_gate_error": "0.3e-04; paper 2.5(1)x10^-5", "SPAM": "4.8e-04; paper 4.8(6)x10^-4",
                     "depth1_time": "average depth-1 time ... 55 ms per layer (98-qubit random layer incl. sort)",
                     "memory_error": "linear memory error rate of 5(1)x10^-4 per depth-1 time",
                     "parallel_two_qubit_operations": "2Q operations are executed in only four of the eight quantum logic zones",
                     "qubits": "98", "connectivity": "all-to-all (ring + 2 linear regions)",
                     "programs": "Guppy/HUGR; Pytket can be submitted to Helios by loading the user circuit into Guppy source"},
        "eps2": 7.9e-4, "eps1": 3.0e-5, "eps_ro_0": 4.8e-4, "eps_ro_1": 4.8e-4,
        "memory_error_per_depth1": 5.0e-4, "depth1_time_s": 0.055, "zones": 4, "qubits": 98,
    },
    "quantinuum_h1_1": {
        "device_name": "H1-1", "source": [PERF, H1_PAGE], "read_on": READ_ON, "transcribed_from": SURVEY,
        "verbatim": {"two_qubit_gate_error": "9.7e-04", "one_qubit_gate_error": "1.8e-05",
                     "SPAM": "1.2e-03 / 3.4e-03", "memory_error_per_depth1_circuit_time": "2.2e-04",
                     "qubits": "20", "connectivity": "all-to-all, 5 gate zones",
                     "data_sheet": "H1 data sheet URL returned 404 on 2026-10-02"},
        "eps2": 9.7e-4, "eps1": 1.8e-5, "eps_ro_0": 1.2e-3, "eps_ro_1": 3.4e-3,
        "memory_error_per_depth1": 2.2e-4, "zones": 5, "qubits": 20,
    },
    "quantinuum_h2_1": {
        "device_name": "H2-1", "source": [PERF, H2_DS, H2_EMU_DS], "read_on": READ_ON, "transcribed_from": SURVEY,
        "verbatim": {"two_qubit_gate_error": "1.1e-03", "one_qubit_gate_error": "1.9e-05",
                     "SPAM": "6.0e-04 / 1.4e-03", "memory_error_per_depth1_circuit_time": "2.0e-04",
                     "emulator_linear_dephasing_rate": "0.0028 /s (H2 emulator data sheet v1.2, H2-1 defaults, 2024)",
                     "parallel_two_qubit_operations": "4", "qubits": "56", "connectivity": "all-to-all"},
        "eps2": 1.1e-3, "eps1": 1.9e-5, "eps_ro_0": 6.0e-4, "eps_ro_1": 1.4e-3,
        "memory_error_per_depth1": 2.0e-4, "zones": 4, "qubits": 56,
    },
}
EPS_RO_RULE = "eps_ro = mean of the published 0 and 1 SPAM values (as the planner prototype)"

# ---- the memory (transport/idle) model: ESTIMATE, the planner prototype's three scenarios -----
H2_1_DEPHASING_PER_S = 0.0028          # H2 emulator data sheet v1.2 (H2-1 defaults)
MEMORY_MODEL = {
    "flag": "ESTIMATE",
    "t_round_scenarios_s": {"low": 0.5e-3, "mid": 1.1e-3, "high": 4.4e-3},
    "t_round_reasons": {
        "low": "70 us gate + ~300 us post-shift cooling + short transport (Helios paper Sec. II.3)",
        "mid": "55 ms / 49 gates: the Helios full-register random layer per gate",
        "high": "55 ms / (49/4) rounds: one round of a full random layer incl. the sort"},
    "memory_rate_per_qubit_per_s": {
        "quantinuum_helios_1": 5.0e-4 / 0.055,
        "quantinuum_h2_1": H2_1_DEPHASING_PER_S,
        "quantinuum_h2_2": H2_1_DEPHASING_PER_S * 1.2 / 2.0,
        "quantinuum_h1_1": H2_1_DEPHASING_PER_S * 2.2 / 2.0},
    "memory_rate_inputs": ("Helios 5e-4 per 55 ms layer (arXiv:2511.05465); H2-1 emulator linear "
                           "dephasing 0.0028 /s; H2-2 and H1-1 scaled by the performance-validation "
                           "memory errors 1.2e-4 / 2.0e-4 and 2.2e-4 / 2.0e-4"),
    "rounds_rule": "rounds = max(ceil(n_2q / parallel zones), two-qubit critical-path depth)",
    "S_idle": "S_idle = n_qubits x rounds x t_round x rate;  f_with_memory = f_gate_only x exp(-S_idle)",
    "source": "planner prototype scratch/planner/quantinuum_2x3_prototype_20261002.py (survey section 3)",
}

BILLING = {
    "formula": "HQC = 5 + C (N_1q + 10 N_2q + 5 N_m) / 5000 per job",
    "N_1q": "PhasedX count (Rz excluded: 'Rz operations excluded')", "N_2q": "ZZPhase + ZZMax count",
    "N_m": "initialisations + measurements (= 2 x n_qubits for one measurement per qubit)",
    "C": "shots", "job_base_hqc": HQC_JOB_BASE, "divisor": HQC_DIVISOR,
    "limits": {"max_shots_per_job": MAX_SHOTS_PER_JOB, "max_hqc_per_job": MAX_HQC_PER_JOB,
               "max_hqc_per_shot_H2": 50},
    "source": [AZURE_PROVIDER, HELIOS_COSTING], "read_on": READ_ON,
    "syntax_checkers": "Syntax Checkers usage is offered free-of-charge (Azure provider page)",
    "azure_plans": {"source": AZURE_PRICING, "read_on": READ_ON,
                    "standard": "USD 125,000/month = 10k HQC + 100k eHQC",
                    "premium": "USD 175,000/month = 17k HQC",
                    "pay_as_you_go": "per HQC usage, rate by contact"},
    "usd_per_hqc_ESTIMATE": {"value": 125000.0 / 10000.0, "flag": "ESTIMATE",
                             "label": "Azure-Standard-equivalent (USD 125,000 / 10,000 HQC); the "
                                      "pay-as-you-go and research rates are not public"},
}
ACCESS = {
    "QCUP": {"source": QCUP, "read_on": READ_ON,
             "verbatim": {"form": "Project Application Form (year-round, myOLCF)",
                          "vendors": "IBM, Quantinuum, IonQ, IQM", "emulator_default": "6000 seconds",
                          "hardware_default": "0 HQCs",
                          "allocation": "Requests for machine credits must be justified using results from an emulator",
                          "deadline": "monthly; request by the 25th of the preceding month",
                          "eligibility": "US national labs, universities, government, and industry; quantinuum.com: Researchers in the United States may apply"}},
    "research_agreement": "Sales@Quantinuum.com (Nexus account / research agreement)",
    "azure": "Azure Quantum workspace (plans above)",
}


def eps_ro_of(s):
    return 0.5 * (s["eps_ro_0"] + s["eps_ro_1"])


def ceil100(x):
    return int(math.ceil(x / 100.0) * 100)


def solve_eps2(fn, target, lo=0.0, hi=0.05, iters=200):
    """Largest eps2 with fn(eps2) >= target, fn decreasing (bisection; None if fn(0) < target)."""
    if fn(lo) < target:
        return None
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if fn(mid) >= target:
            lo = mid
        else:
            hi = mid
    return lo


# ---- counts -----------------------------------------------------------------------------------
def counts_2x3():
    mans = sorted(glob.glob(os.path.join(CIRC_DIR, "B*_ref*_k*.manifest.json")))
    if len(mans) != 44:
        raise SystemExit(f"expected 44 frozen 2x3 manifests in {CIRC_DIR}, found {len(mans)}: run "
                         f"scripts/quantinuum_build_circuits.py first")
    per = []
    for p in mans:
        m = json.load(open(p))
        c = m["counts"]
        per.append({"id": m["id"], "sector": m["sector"], "n_2q": c["n_zz"], "n_1q": c["n_phasedx"],
                    "n_meas": c["n_meas"], "n_qubits": c["n_qubits"], "depth_2q": c["depth_2q"],
                    "hqc_per_shot": m["hqc_per_shot"]})
    return {"per_circuit": per, "n_qubits": per[0]["n_qubits"], "n_meas": per[0]["n_meas"],
            "n_2q_mean": float(np.mean([p["n_2q"] for p in per])),
            "n_1q_mean": float(np.mean([p["n_1q"] for p in per])),
            "depth_2q_max": int(max(p["depth_2q"] for p in per)),
            "hqc_per_shot_mean": float(np.mean([p["hqc_per_shot"] for p in per])),
            "source": "data/quantinuum/circuits_2x3/*.manifest.json counts (frozen native circuits; "
                      "n_1q = PhasedX, Rz virtual)"}


def counts_2x2():
    s2 = json.load(open(os.path.join(ROOT, "validation", "S2.json")))["data"]
    o = s2["2x2"]["coarse_step"]["all_to_all"]["ops"]
    return {"n_qubits": 12, "n_meas": 12, "n_2q": int(o["cz"]), "n_1q": int(o["sx"] + o["x"]),
            "depth_2q": None,
            "source": "validation/S2.json data.2x2.coarse_step.all_to_all.ops (CZ basis; n_1q = sx + x, "
                      "rz virtual; no ZZPhase build of 2x2 exists -- at 2x3 the RZZ and CZ counts "
                      "differ by 6 of 2164)"}


def counts_2x4():
    s = json.load(open(os.path.join(ROOT, "validation", "S2_2x4.json")))["data"]
    c = s["compile"]["compile_4_exact_a2a_k1"]["circuits"]["B0_ref0_k1"]["maps"]["all_to_all"]
    return {"n_qubits": 28, "n_meas": 28, "n_2q": int(c["n_2q"]), "n_1q": int(c["n_sx"] + c["n_x"]),
            "depth_2q": int(c.get("cz_depth") or 0) or None,
            "source": "validation/S2_2x4.json data.compile.compile_4_exact_a2a_k1.circuits.B0_ref0_k1."
                      "maps.all_to_all (signed exact family, CZ basis; n_1q = sx + x)"}


def shots_2x3_scaled(f):
    r = json.load(open(os.path.join(ROOT, "data", "S2D_recall_at_f.json")))["results"]
    base = {s: int(r[f"{s}|f=0.1"]["shot_rule_union_reading_N_sector"]) for s in ("B=0", "B=1")}
    return {s: ceil100(N * 0.1 / f) for s, N in base.items()}, base


def shots_2x2_scaled(f):
    h = json.load(open(os.path.join(ROOT, "validation", "H0_2x2.json")))["data"]["shot_plan"]
    plan = json.load(open(os.path.join(ROOT, h["path"])))
    f0 = float(plan["f_sizing_input"]["f_pool"])
    return ceil100(int(h["total_coarse_shots"]) * f0 / f), {"total_coarse_shots": int(h["total_coarse_shots"]),
                                                             "f_pool": f0, "path": h["path"]}


# ---- one row ------------------------------------------------------------------------------------
def memory_block(name, f_gate, n_qubits, n2, depth_2q, zones):
    rate = MEMORY_MODEL["memory_rate_per_qubit_per_s"][name]
    gate_bound = math.ceil(n2 / zones)
    rounds = max(gate_bound, depth_2q or 0)
    out = {"flag": "ESTIMATE", "rate_per_qubit_per_s": rate, "rounds": rounds,
           "rounds_gate_bound": gate_bound, "depth_2q": depth_2q, "scenarios": {}}
    for lab, t in MEMORY_MODEL["t_round_scenarios_s"].items():
        shot_s = rounds * t
        S = n_qubits * shot_s * rate
        out["scenarios"][lab] = {"t_round_s": t, "shot_time_s": shot_s, "S_idle_nats": S,
                                 "f_with_memory": f_gate * math.exp(-S)}
    return out


def row(name, spec, lat, cnt):
    e2, e1, ero = spec["eps2"], spec["eps1"], eps_ro_of(spec)
    out = {"device": spec["device_name"], "lattice": lat, "eps2": e2, "eps1": e1, "eps_ro": ero,
           "eps_ro_rule": EPS_RO_RULE, "qubits_fit": spec["qubits"] >= cnt["n_qubits"]}
    if lat == "2x3":
        per = cnt["per_circuit"]
        fs = [clean_shot_fraction(p["n_2q"], p["n_1q"], p["n_meas"], e2, e1, ero) for p in per]
        f_mean, f_worst = float(np.mean(fs)), float(min(fs))
        n2 = int(round(cnt["n_2q_mean"]))
        out.update({"f_gate_only_mean": f_mean, "f_gate_only_worst": f_worst,
                    "f_gate_only_worst_id": per[int(np.argmin(fs))]["id"],
                    "f_2q_only": clean_shot_fraction(n2, 0, 0, e2, 0.0, 0.0),
                    "eps2_for_mean_f_0.1": solve_eps2(
                        lambda x: float(np.mean([clean_shot_fraction(p["n_2q"], p["n_1q"], p["n_meas"], x, e1, ero)
                                                 for p in per])), F_MEAN_MIN),
                    "eps2_for_worst_f_0.05": solve_eps2(
                        lambda x: float(min(clean_shot_fraction(p["n_2q"], p["n_1q"], p["n_meas"], x, e1, ero)
                                            for p in per)), F_WORST_MIN),
                    "hqc_per_shot_mean": cnt["hqc_per_shot_mean"]})
        f_gate, depth2 = f_mean, cnt["depth_2q_max"]
        hps = cnt["hqc_per_shot_mean"]
    else:
        f_gate = clean_shot_fraction(cnt["n_2q"], cnt["n_1q"], cnt["n_meas"], e2, e1, ero)
        other = clean_shot_fraction(0, cnt["n_1q"], cnt["n_meas"], 0.0, e1, ero)
        out.update({"f_gate_only_mean": f_gate, "f_gate_only_worst": f_gate,
                    "f_2q_only": clean_shot_fraction(cnt["n_2q"], 0, 0, e2, 0.0, 0.0),
                    "eps2_for_mean_f_0.1": required_error(cnt["n_2q"], F_MEAN_MIN, other),
                    "eps2_for_worst_f_0.05": required_error(cnt["n_2q"], F_WORST_MIN, other)})
        depth2 = cnt.get("depth_2q")
        hps = hqc_per_shot({"n_phasedx": cnt["n_1q"], "n_zz": cnt["n_2q"],
                            "n_qubits": cnt["n_qubits"], "n_meas": cnt["n_meas"]})
        out["hqc_per_shot_mean"] = hps
    out["meets_mean_0.1_gate_only"] = out["f_gate_only_mean"] >= F_MEAN_MIN
    out["meets_worst_0.05_gate_only"] = out["f_gate_only_worst"] >= F_WORST_MIN
    mem = memory_block(name, f_gate, cnt["n_qubits"], int(round(cnt.get("n_2q_mean", cnt.get("n_2q", 0)))),
                       depth2, spec["zones"])
    out["memory_ESTIMATE"] = mem
    if depth2 is None:
        mem["note"] = "no two-qubit depth recorded for this lattice: rounds = the gate bound only"
    f_mid = mem["scenarios"]["mid"]["f_with_memory"]
    out["f_with_memory_mid_ESTIMATE"] = f_mid
    out["meets_mean_0.1_with_memory_mid_ESTIMATE"] = f_mid >= F_MEAN_MIN
    # D3-type shots scaled as 1/f (at the mid memory scenario, as the planner prototype)
    usd = BILLING["usd_per_hqc_ESTIMATE"]["value"]
    if f_mid < 1e-12:
        out["shots"] = "not computable (f < 1e-12)"
        return out
    if lat == "2x3":
        per_sec, base = shots_2x3_scaled(f_mid)
        tot = sum(per_sec.values())
        out["shots_rule"] = ("data/S2D_recall_at_f.json results.<sector>|f=0.1.shot_rule_union_reading_N_sector "
                             "x 0.1 / f, rounded up to 100")
        out["shots_per_sector"] = per_sec
        out["shots_base_at_f_0.1"] = base
    elif lat == "2x2":
        tot, base = shots_2x2_scaled(f_mid)
        out["shots_rule"] = "validation/H0_2x2.json data.shot_plan.total_coarse_shots x f_pool / f, rounded up to 100"
        out["shots_base"] = base
    else:
        out["shots"] = "not computed for 2x4 (f below any plan)"
        return out
    jobs = int(math.ceil(tot / MAX_SHOTS_PER_JOB))
    hqc = tot * hps + HQC_JOB_BASE * jobs
    out.update({"f_used_for_shots": f_mid, "shots_total": tot, "jobs_lower_bound": jobs,
                "hqc_total_ESTIMATE": hqc, "usd_ESTIMATE_azure_standard_equivalent": hqc * usd,
                "machine_hours_mid_ESTIMATE": tot * mem["scenarios"]["mid"]["shot_time_s"] / 3600.0,
                "hqc_per_job_at_max_shots": HQC_JOB_BASE + MAX_SHOTS_PER_JOB * hps,
                "job_limit_fit": HQC_JOB_BASE + MAX_SHOTS_PER_JOB * hps <= MAX_HQC_PER_JOB})
    return out


def reproduce_prototype():
    P = json.load(open(PROTOTYPE))
    c = P["counts"]
    out = {}
    for name, spec in SPECS.items():
        f = clean_shot_fraction(c["n_2q_rzz_mean"], c["n_1q_physical_virtual_rz_mean"], c["n_meas"],
                                spec["eps2"], spec["eps1"], eps_ro_of(spec))
        fp = P["devices"][name]["f_gate_only"]
        out[name] = {"f_table": f, "f_prototype": fp, "abs_diff": abs(f - fp),
                     "counts": [c["n_2q_rzz_mean"], c["n_1q_physical_virtual_rz_mean"], c["n_meas"]]}
    return out


def reproduce_ionq():
    J = json.load(open(IONQ))
    out = {}
    for key, v in J["results"].items():
        lat, dev, mode = key.split("|")
        cnt, spec = J["counts"][lat], J["specs"][dev]
        n1 = cnt["n_1q_virtual_rz"] if mode == "virtual_rz" else cnt["n_1q"]
        f = clean_shot_fraction(cnt["n_2q"], n1, cnt["n_meas"], spec["eps2"], spec["eps1"], spec["eps_ro"])
        out[key] = {"f_table": f, "f_json": v["gate_only"]["f_gates"], "abs_diff": abs(f - v["gate_only"]["f_gates"])}
    fo, c3 = J["specs"]["ionq_forte"], J["counts"]["2x3"]
    for e2, fj in J["scenario_eps2_for_2x3"].items():
        f = clean_shot_fraction(c3["n_2q"], c3["n_1q_virtual_rz"], c3["n_meas"], float(e2), fo["eps1"], fo["eps_ro"])
        out[f"scenario_eps2_for_2x3|{e2}"] = {"f_table": f, "f_json": fj, "abs_diff": abs(f - fj)}
    return out, {k: J[k] for k in ("specs", "tempo", "counts", "results", "read_on", "script")}


def offline_machine_list():
    p = os.path.join(ROOT, "data", "quantinuum", "offline_machine_list.json")
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    counts = {"2x2": counts_2x2(), "2x3": counts_2x3(), "2x4": counts_2x4()}
    rows = {f"{lat}|{name}": row(name, spec, lat, counts[lat])
            for lat in ("2x3", "2x2", "2x4") for name, spec in SPECS.items()}
    proto = reproduce_prototype()
    ionq_repro, ionq_rows = reproduce_ionq()
    repro_ok = (all(v["abs_diff"] <= REPRO_TOL for v in proto.values())
                and all(v["abs_diff"] <= REPRO_TOL for v in ionq_repro.values()))
    out = {
        "produced_by": "scripts/quantinuum_device_table.py", "prompt": "prompts/26 A5", "read_on": READ_ON,
        "criterion": {"mean_f_min": F_MEAN_MIN, "worst_f_min": F_WORST_MIN,
                      "source": "proposal/amendment_01_devices_and_budgets.md item 2 (signed)"},
        "specs": SPECS, "memory_model": MEMORY_MODEL, "billing": BILLING, "access": ACCESS,
        "offline_machine_list_pytket_quantinuum": offline_machine_list(),
        "counts": counts, "rows": rows,
        "prototype_reproduction": proto, "ionq_reproduction": ionq_repro,
        "reproduction_tolerance": REPRO_TOL, "reproduction_ok": repro_ok,
        "ionq_rows_as_read": ionq_rows,
        "not_established": [
            "No number here was measured by this project; Quantinuum values are vendor RB-sweep values of unspecified date.",
            "The memory term is an ESTIMATE (three scenarios); the vendor emulator (Stage E) settles it.",
            "USD per HQC is the Azure Standard-plan equivalent; pay-as-you-go and research rates are not public.",
            "2x2 and 2x4 counts are CZ-basis transpilations; only 2x3 has a native ZZPhase build."],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote {os.path.relpath(OUT, ROOT)}  (reproduction ok: {repro_ok})")
    for k, v in rows.items():
        sh = v.get("shots_total", v.get("shots"))
        print(f"  {k:28s} f_gate mean {v['f_gate_only_mean']:.4e} worst {v['f_gate_only_worst']:.4e} "
              f"f_mid {v['f_with_memory_mid_ESTIMATE']:.4e} shots {sh} HQC {v.get('hqc_total_ESTIMATE')}")
    return 0 if repro_ok else 1


if __name__ == "__main__":
    sys.exit(main())
