#!/usr/bin/env python3
"""
Is the 2x3 coarse step feasible on IonQ trapped-ion hardware?  (owner question, 2026-10-01)

Amendment 01 item 4 asks a device to satisfy the signed budget criterion -- mean clean-shot
fraction f >= 0.1, worst >= 0.05 -- and since item 2 that f includes the idle term.  This
script takes IonQ's PUBLISHED device specifications, recorded below with their source and the
date they were read, and evaluates the 2x3 circuits against that criterion with the
repository's own requirement code (`skqd.device_req`) and gate counts
(`data/S2D_2x3_device_requirements.json`, `validation/S2.json`).

Two parts, deliberately kept apart because they rest on different evidence:

  1. GATE-ONLY f.  Uses only published error rates and the measured gate counts.  No
     assumption about scheduling enters, so this part is a lower bound on the damage: idle
     time can only make f smaller.  If the criterion fails here, it fails.
  2. IDLE TERM.  Needs gate durations and an execution schedule.  IonQ publishes durations for
     Aria only, and does not publish how gates are scheduled, so this part is an ESTIMATE
     under a stated assumption (fully serial execution, the idle penalty in its small-window
     linear form S_T2 = sum_q t_idle,q / (2 T2), T1 >> duration) and is labelled as such.

Nothing here is a hardware measurement.  Vendor figures are averages that a given day's
calibration may beat or miss, and the gate-only part ignores crosstalk and leakage.

Usage: python scripts/ionq_2x3_feasibility.py
"""
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from skqd.device_req import clean_shot_fraction, required_error  # noqa: E402

READ_ON = "2026-10-01"
F_TARGET = 0.1
F_WORST = 0.05

# ---- published specifications, verbatim, with sources -------------------------------------
AZURE = "https://learn.microsoft.com/en-us/azure/quantum/provider-ionq"
FORTE = "https://www.ionq.com/quantum-systems/forte"
TEMPO = "https://www.ionq.com/quantum-systems/tempo"
SPECS = {
    "ionq_aria": {
        "source": AZURE, "source_updated": "2026-08-29 (page metadata)", "read_on": READ_ON,
        "verbatim": {"two_qubit_gate_fidelity": "99.6% (not SPAM corrected)",
                     "single_qubit_gate_fidelity": "99.95% (SPAM corrected)",
                     "SPAM": "99.61%", "T1": "10-100 s", "T2": "1 s",
                     "single_qubit_gate_time": "135 us", "two_qubit_gate_time": "600 us",
                     "qubits": 25, "connectivity": "all-to-all"},
        "eps2": 1 - 0.996, "eps1": 1 - 0.9995, "eps_ro": 1 - 0.9961,
        "t_2q_s": 600e-6, "t_1q_s": 135e-6, "T2_s": 1.0, "T1_s": 10.0, "qubits": 25,
    },
    "ionq_forte": {
        "source": FORTE, "read_on": READ_ON,
        "verbatim": {"two_qubit_gate_error": "0.4%", "one_qubit_gate_error": "0.02%",
                     "SPAM_error": "0.5%", "T1_and_T2": "10-100s, ~1s",
                     "gate_times": "NOT STATED on the page", "qubits": 36,
                     "connectivity": "all-to-all"},
        "eps2": 0.004, "eps1": 0.0002, "eps_ro": 0.005,
        "t_2q_s": None, "t_1q_s": None, "T2_s": 1.0, "T1_s": 10.0, "qubits": 36,
    },
}
# Tempo publishes TARGETS only, so it is a scenario, never a device row.
TEMPO_NOTE = {
    "source": TEMPO, "read_on": READ_ON,
    "verbatim": {"target_fidelity": "99.9%", "target_qubits": 100, "AQ": 64},
    "status": ("targets, not achieved specifications; no gate times, coherence times, SPAM or "
               "one-qubit figures are published, so Tempo cannot be evaluated as a device"),
}


def counts():
    """The measured gate counts this question is about, read from the repository."""
    s = json.load(open(os.path.join(ROOT, "data", "S2D_2x3_device_requirements.json")))
    c = s["counts"]["coarse_step"]
    s2 = json.load(open(os.path.join(ROOT, "validation", "S2.json")))["data"]
    ops22 = s2["2x2"]["coarse_step"]["all_to_all"]["ops"]
    return {
        "2x3": {"n_qubits": s["counts"]["n_qubits"], "n_2q": int(c["rzz"]["mean"]),
                "n_1q": round(c["n_1q"]["mean"]), "n_1q_virtual_rz": round(c["n_1q_virtual_rz"]["mean"]),
                "n_meas": s["counts"]["measured_qubits"],
                "source": "data/S2D_2x3_device_requirements.json counts.coarse_step "
                          "(RZZ basis, all-to-all: the natural basis of an ion trap)"},
        "2x2": {"n_qubits": 12, "n_2q": int(ops22["cz"]),
                "n_1q": int(ops22["sx"] + ops22["rz"] + ops22["x"]),
                "n_1q_virtual_rz": int(ops22["sx"] + ops22["x"]), "n_meas": 12,
                "source": "validation/S2.json data.2x2.coarse_step.all_to_all.ops"},
    }


def gate_only(cnt, dev, virtual_rz):
    n1 = cnt["n_1q_virtual_rz"] if virtual_rz else cnt["n_1q"]
    f = clean_shot_fraction(cnt["n_2q"], n1, cnt["n_meas"], dev["eps2"], dev["eps1"], dev["eps_ro"])
    other = clean_shot_fraction(0, n1, cnt["n_meas"], dev["eps2"], dev["eps1"], dev["eps_ro"])
    return {"n_1q_used": n1, "f_gates": f, "budget_used_nats": -math.log(f),
            "budget_nats": math.log(1 / F_TARGET),
            "meets_mean_0.1": f >= F_TARGET, "meets_worst_0.05": f >= F_WORST,
            "eps2_required_at_published_eps1_eps_ro": required_error(cnt["n_2q"], F_TARGET, other),
            "eps2_published": dev["eps2"]}


def idle_estimate(cnt, dev, virtual_rz):
    """ESTIMATE: fully serial execution, linear small-window PTA, T1 >> duration."""
    if dev["t_2q_s"] is None:
        return {"computable": False,
                "reason": "the vendor publishes no gate durations for this device"}
    n1 = cnt["n_1q_virtual_rz"] if virtual_rz else cnt["n_1q"]
    dur = cnt["n_2q"] * dev["t_2q_s"] + n1 * dev["t_1q_s"]
    busy_per_qubit = (2 * cnt["n_2q"] * dev["t_2q_s"] + n1 * dev["t_1q_s"]) / cnt["n_qubits"]
    idle_per_qubit = max(0.0, dur - busy_per_qubit)
    s_t2 = cnt["n_qubits"] * idle_per_qubit / (2 * dev["T2_s"])
    return {"computable": True, "assumption": idle_estimate.__doc__, "duration_s": dur,
            "idle_per_qubit_s": idle_per_qubit, "S_idle_estimate": s_t2,
            "gates_per_coherence_time": dev["T2_s"] / dev["t_2q_s"],
            "idle_factor_exp_minus_S": math.exp(-s_t2)}


def main():
    cnt = counts()
    out = {"script": "scripts/ionq_2x3_feasibility.py", "read_on": READ_ON,
           "criterion": {"mean_f_min": F_TARGET, "worst_f_min": F_WORST,
                         "source": "proposal/amendment_01_devices_and_budgets.md item 2 (signed)"},
           "specs": SPECS, "tempo": TEMPO_NOTE, "counts": cnt, "results": {}}
    for lat in ("2x3", "2x2"):
        for name, dev in SPECS.items():
            for vrz in (False, True):
                key = f"{lat}|{name}|{'virtual_rz' if vrz else 'physical_rz'}"
                g = gate_only(cnt[lat], dev, vrz)
                i = idle_estimate(cnt[lat], dev, vrz)
                if i.get("computable"):
                    g["f_with_idle_estimate"] = g["f_gates"] * i["idle_factor_exp_minus_S"]
                out["results"][key] = {"gate_only": g, "idle": i}
    # scenarios: what two-qubit error would 2x3 need, gate-only, at Forte's other errors
    fo = SPECS["ionq_forte"]
    c3 = cnt["2x3"]
    out["scenario_eps2_for_2x3"] = {
        str(e2): clean_shot_fraction(c3["n_2q"], c3["n_1q_virtual_rz"], c3["n_meas"], e2,
                                     fo["eps1"], fo["eps_ro"])
        for e2 in (4e-3, 1e-3, 5e-4, 1e-4)}
    path = os.path.join(ROOT, "data", "ionq_2x3_feasibility_20261001.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"wrote {os.path.relpath(path, ROOT)}\n")
    for k, v in out["results"].items():
        g, i = v["gate_only"], v["idle"]
        idle = (f"  with idle est. {g['f_with_idle_estimate']:.1e} (S_idle ~{i['S_idle_estimate']:.1f}, "
                f"{i['duration_s']:.2f} s)") if i.get("computable") else "  idle: not computable"
        print(f"{k:34} f_gates {g['f_gates']:.2e}  meets 0.1? {g['meets_mean_0.1']!s:5}{idle}")
    print("\n2x3 gate-only f at Forte's eps1/eps_ro, virtual rz, as a function of eps2:")
    for e2, f in out["scenario_eps2_for_2x3"].items():
        print(f"   eps2 = {float(e2):.0e}  ->  f = {f:.3e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
