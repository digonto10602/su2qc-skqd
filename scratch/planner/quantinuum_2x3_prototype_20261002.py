"""Planner prototype (2026-10-02): the signed 2x3 circuits in the RZZ basis, their two-qubit
layering, and the clean-shot fraction f on each surveyed device.

Planner arithmetic only.  Every device number is quoted from the survey
(reports/qpu_survey_2x3_20261002.md) with its URL; the counts come from gate_S2D.circuit_set(3)
transpiled exactly as gate S2D did (basis rz, rx, ry, rzz; coupling_map None; level 3; seed 7).
Output: scratch/planner/quantinuum_2x3_prototype_20261002.json.
"""
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import numpy as np  # noqa: E402
from qiskit import transpile  # noqa: E402

from skqd import circuits_qiskit as cq  # noqa: E402
from skqd.device_req import clean_shot_fraction, required_error  # noqa: E402
from gate_S2D import circuit_set, analyse_rzz  # noqa: E402

t0 = time.time()
M, F, circs = circuit_set(3)
n = M.codec.n_qubits if hasattr(M, "codec") else None
rows = []
angles_all = []
for twoB, r, k, gates in circs:
    nq = int(max(q for _, qs, _ in gates for q in qs) + 1)
    qc = cq.ir_to_qiskit(gates, nq, measure=False)
    tq = transpile(qc, basis_gates=["rz", "rx", "ry", "rzz"], coupling_map=None,
                   optimization_level=3, seed_transpiler=7)
    a = analyse_rzz(tq, 1e-3, 1e-4, 2e-3, nq)
    d2 = tq.depth(filter_function=lambda inst: inst.operation.num_qubits == 2)
    ang = [abs(float(inst.operation.params[0])) for inst in tq.data if inst.operation.name == "rzz"]
    angles_all.extend(ang)
    # ASAP layering of the two-qubit gates alone (1q gates assumed free): layers = d2.
    rows.append({"sector": f"B={twoB//2}", "ref": int(r), "k": k, "n_qubits": nq,
                 "rzz": a["rzz"], "n_1q": a["n_1q"], "n_rz": a["n_rz"],
                 "n_1q_physical_virtual_rz": a["n_1q"] - a["n_rz"], "depth_all": a["depth"],
                 "depth_2q_only": int(d2), "rzz_angle_abs_mean": float(np.mean(ang)),
                 "rzz_angle_abs_max": float(np.max(ang)), "rzz_angle_abs_min": float(np.min(ang))})
    if k == 1:
        print(rows[-1], flush=True)

n2q = int(np.mean([r["rzz"] for r in rows]))
n1q = int(round(np.mean([r["n_1q_physical_virtual_rz"] for r in rows])))
nmeas = rows[0]["n_qubits"]
d2_mean = float(np.mean([r["depth_2q_only"] for r in rows]))
d2_max = max(r["depth_2q_only"] for r in rows)

# ---------------------------------------------------------------- devices (survey section 2)
# eps2, eps1, eps_ro(mean of 0/1 if two values), zones (parallel 2q), memory rate per qubit per
# second (ESTIMATE: memory error per depth-1 time / depth-1 time), note.
# Per-round (one two-qubit gate round incl. transport and cooling) time scenarios, ESTIMATE:
#  low  0.5 ms: 70 us gate + ~300 us post-shift cooling + short transport (Helios paper Sec. II.3)
#  mid  1.1 ms: 55 ms / 49 gates, the full-register random layer of the Helios paper per gate
#  high 4.4 ms: 55 ms / (49/4) rounds, one round of a full random layer incl. the sort
T_ROUND_SCENARIOS_S = {"low": 0.5e-3, "mid": 1.1e-3, "high": 4.4e-3}
# memory rate per qubit per second, ESTIMATE: Helios 5e-4 per 55 ms layer (arXiv:2511.05465);
# H2-1 emulator linear_dephasing_rate 0.0028 /s (H2 emulator data sheet v1.2) scaled by the
# performance-validation memory errors H2-2 1.2e-4 / H2-1 2.0e-4 and H1-1 2.2e-4 / 2.0e-4.
MEM_RATE = {"helios": 5.0e-4 / 0.055, "h2_1": 0.0028, "h2_2": 0.0028 * 1.2 / 2.0, "h1_1": 0.0028 * 2.2 / 2.0}
devices = {
    "quantinuum_helios_1": dict(eps2=7.9e-4, eps1=3.0e-5, eps_ro=4.8e-4, zones=4, mem_rate_per_s=MEM_RATE["helios"],
                                mem_per_layer=5.0e-4, layer_time_s=0.055, layer_gates=49,
                                all_to_all=True, qubits=98),
    "quantinuum_h2_2": dict(eps2=8.3e-4, eps1=2.8e-5, eps_ro=0.5 * (6.7e-4 + 1.2e-3), zones=4, mem_rate_per_s=MEM_RATE["h2_2"],
                            mem_per_layer=1.2e-4, layer_time_s=None, layer_gates=28,
                            all_to_all=True, qubits=56),
    "quantinuum_h2_1": dict(eps2=1.1e-3, eps1=1.9e-5, eps_ro=0.5 * (6.0e-4 + 1.4e-3), zones=4, mem_rate_per_s=MEM_RATE["h2_1"],
                            mem_per_layer=2.0e-4, layer_time_s=None, layer_gates=28,
                            all_to_all=True, qubits=56),
    "quantinuum_h1_1": dict(eps2=9.7e-4, eps1=1.8e-5, eps_ro=0.5 * (1.2e-3 + 3.4e-3), zones=5, mem_rate_per_s=MEM_RATE["h1_1"],
                            mem_per_layer=2.2e-4, layer_time_s=None, layer_gates=10,
                            all_to_all=True, qubits=20),
    "ionq_forte_spec": dict(eps2=4e-3, eps1=2e-4, eps_ro=5e-3, zones=None, mem_per_layer=None,
                            layer_time_s=None, layer_gates=None, all_to_all=True, qubits=36),
    "ionq_tempo_target": dict(eps2=1e-3, eps1=1e-4, eps_ro=5e-3, zones=None, mem_per_layer=None,
                              layer_time_s=None, layer_gates=None, all_to_all=True, qubits=100),
    "aqt_ibex_q1": dict(eps2=1.3e-2, eps1=3e-4, eps_ro=None, zones=None, mem_per_layer=None,
                        layer_time_s=None, layer_gates=None, all_to_all=True, qubits=12),
    "quera_gemini": dict(eps2=2.3e-3, eps1=3e-3, eps_ro=3e-3, zones=None, mem_per_layer=None,
                         layer_time_s=None, layer_gates=None, all_to_all=False, qubits=260),
    "infleqtion_sqale": dict(eps2=2.7e-3, eps1=None, eps_ro=None, zones=None, mem_per_layer=None,
                             layer_time_s=None, layer_gates=None, all_to_all=False, qubits=100),
    "google_willow_rcs_config": dict(eps2=1.4e-3, eps1=3.5e-4, eps_ro=7e-3, zones=None,
                                     mem_per_layer=None, layer_time_s=None, layer_gates=None,
                                     all_to_all=False, qubits=105),
    "google_willow_qec_config": dict(eps2=3.3e-3, eps1=3.5e-4, eps_ro=7e-3, zones=None,
                                     mem_per_layer=None, layer_time_s=None, layer_gates=None,
                                     all_to_all=False, qubits=105),
    "ibm_kingston_best_edge": dict(eps2=8.164e-4, eps1=2.44e-4, eps_ro=8.97e-3, zones=None,
                                   mem_per_layer=None, layer_time_s=None, layer_gates=None,
                                   all_to_all=False, qubits=156),
    "ibm_heron_r3_nighthawk_class": dict(eps2=2.15e-3, eps1=2.44e-4, eps_ro=8.97e-3, zones=None,
                                         mem_per_layer=None, layer_time_s=None, layer_gates=None,
                                         all_to_all=False, qubits=120),
    "rigetti_cepheus_1_36q": dict(eps2=5e-3, eps1=1e-3, eps_ro=None, zones=None, mem_per_layer=None,
                                  layer_time_s=None, layer_gates=None, all_to_all=False, qubits=36),
    "iqm_emerald": dict(eps2=5e-3, eps1=7e-4, eps_ro=None, zones=None, mem_per_layer=None,
                        layer_time_s=None, layer_gates=None, all_to_all=False, qubits=54),
}
ROUTING_OVERHEAD_HEAVY_HEX = 5477 / 2164      # validation/S2.json, measured
ROUTING_OVERHEAD_SQUARE_EST = 1.8             # ESTIMATE for square lattices (not computed)
HQC_PER_SHOT = (n1q + 10 * n2q + 5 * 2 * nmeas) / 5000.0
USD_PER_HQC_AZURE_STANDARD = 125000.0 / 10000.0   # Azure Standard plan: USD125,000 / 10k HQC
N_SECTOR_AT_F01 = {"B=0": 71500, "B=1": 71075}    # data/S2D_recall_at_f.json (D3-type rule, f = 0.1)

out = {}
for name, d in devices.items():
    eps_ro = d["eps_ro"] if d["eps_ro"] is not None else 5e-3
    eps1 = d["eps1"] if d["eps1"] is not None else 2e-4
    if d["all_to_all"]:
        n2 = n2q
        overhead = 1.0
    else:
        overhead = ROUTING_OVERHEAD_HEAVY_HEX if "ibm" in name else ROUTING_OVERHEAD_SQUARE_EST
        n2 = int(round(n2q * overhead))
    f_gate = clean_shot_fraction(n2, n1q, nmeas, d["eps2"], eps1, eps_ro)
    f_2q_only = clean_shot_fraction(n2, 0, 0, d["eps2"], 0.0, 0.0)
    other = clean_shot_fraction(0, n1q, nmeas, 0.0, eps1, eps_ro)
    eps2_for_mean_01 = required_error(n2, 0.1, other)
    eps2_for_worst_005 = required_error(n2, 0.05, other)
    row = {"n_2q_used": n2, "routing_overhead": overhead,
           "routing_overhead_is_estimate": (not d["all_to_all"]) and ("ibm" not in name),
           "f_gate_only": f_gate, "f_2q_only": f_2q_only,
           "eps2_for_mean_f_0.1": eps2_for_mean_01, "eps2_for_worst_f_0.05": eps2_for_worst_005,
           "qubits_fit": d["qubits"] >= nmeas}
    if d.get("mem_rate_per_s"):
        rounds_gate_bound = math.ceil(n2 / d["zones"])
        rounds = max(rounds_gate_bound, d2_mean)           # the 2q critical path bounds the rounds
        scen = {}
        for label, t_round in T_ROUND_SCENARIOS_S.items():
            shot_s = rounds * t_round
            S_idle = nmeas * shot_s * d["mem_rate_per_s"]
            scen[label] = {"t_round_s": t_round, "shot_time_s": shot_s, "S_idle_nats": S_idle,
                           "f_with_memory": f_gate * math.exp(-S_idle)}
        row.update({"rounds_2q_estimate": rounds, "rounds_gate_bound": rounds_gate_bound,
                    "mem_rate_per_qubit_per_s_estimate": d["mem_rate_per_s"],
                    "memory_scenarios_ESTIMATE": scen,
                    "f_with_memory_estimate": scen["mid"]["f_with_memory"],
                    "shot_time_s_estimate": scen["mid"]["shot_time_s"]})
        f_use = row["f_with_memory_estimate"]
    else:
        f_use = f_gate
    row["meets_mean_0.1_gate_only"] = f_gate >= 0.1
    row["meets_worst_0.05_gate_only"] = f_gate >= 0.05
    row["meets_mean_0.1_with_memory_estimate"] = f_use >= 0.1
    if f_use > 1e-6:
        shots = {s: int(math.ceil(N * 0.1 / f_use / 100.0) * 100) for s, N in N_SECTOR_AT_F01.items()}
        tot = sum(shots.values())
        row["shots_per_sector_D3_scaled"] = shots
        row["shots_total"] = tot
        row["hqc_per_shot"] = HQC_PER_SHOT
        row["hqc_total_estimate"] = tot * HQC_PER_SHOT + 5 * math.ceil(tot / 10000)
        row["usd_at_azure_standard_rate_estimate"] = row["hqc_total_estimate"] * USD_PER_HQC_AZURE_STANDARD
        if "shot_time_s_estimate" in row:
            row["machine_hours_estimate"] = tot * row["shot_time_s_estimate"] / 3600
    else:
        row["shots_total"] = "not computable (f < 1e-6)"
    out[name] = row

res = {"produced_by": os.path.relpath(__file__, ROOT), "runtime_s": time.time() - t0,
       "counts": {"n_2q_rzz_mean": n2q, "n_1q_physical_virtual_rz_mean": n1q, "n_meas": nmeas,
                  "depth_2q_only_mean": d2_mean, "depth_2q_only_max": d2_max,
                  "rzz_angle_abs_mean_rad": float(np.mean(angles_all)),
                  "rzz_angle_abs_median_rad": float(np.median(angles_all)),
                  "rzz_angle_abs_max_rad": float(np.max(angles_all)),
                  "rzz_angle_over_pi_over_2_mean": float(np.mean(angles_all) / (math.pi / 2)),
                  "hqc_per_shot": HQC_PER_SHOT, "n_circuits": len(rows)},
       "per_circuit": rows, "devices": out,
       "constants": {"routing_overhead_heavy_hex_measured": ROUTING_OVERHEAD_HEAVY_HEX,
                     "routing_overhead_square_ESTIMATE": ROUTING_OVERHEAD_SQUARE_EST,
                     "usd_per_hqc_azure_standard_plan": USD_PER_HQC_AZURE_STANDARD,
                     "N_sector_at_f_0.1": N_SECTOR_AT_F01, "t_round_scenarios_s": T_ROUND_SCENARIOS_S, "mem_rate_per_s": MEM_RATE}}
path = os.path.join(ROOT, "scratch", "planner", "quantinuum_2x3_prototype_20261002.json")
with open(path, "w") as fh:
    json.dump(res, fh, indent=1)
print(json.dumps(res["counts"], indent=1))
for k, v in out.items():
    print(f"{k:34s} n2q={v['n_2q_used']:5d} f_gate={v['f_gate_only']:.3e} "
          f"f_mem(mid)={v.get('f_with_memory_estimate', float('nan')):.3e} eps2(0.1)={v['eps2_for_mean_f_0.1']} "
          f"shots={v.get('shots_total')} hqc={v.get('hqc_total_estimate')}")
print("wrote", path, f"{time.time()-t0:.1f}s")
