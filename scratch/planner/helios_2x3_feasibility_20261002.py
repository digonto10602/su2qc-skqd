#!/usr/bin/env python3
"""Planner prototype (prompts/27): gate-only clean-shot fraction of the 2x3 circuit families on
Quantinuum Helios / H2 and the HQC cost per shot, using the repository's own algebra
(skqd.device_req.clean_shot_fraction) and counts (data/S2D_2x3_device_requirements.json).
Vendor inputs (fetched 2026-10-02): Helios arXiv:2511.05465 Table 2 -- 2q 7.9e-4, 1q 2.5e-5,
SPAM 4.8e-4, memory 5e-4 per depth-1 transport, 2Q gate ~70 us, 55 ms per depth-1 layer at 98
qubits; H2 product page -- 2q fidelity ">99.9%" (taken as eps2 = 1e-3, an upper bound on the
error); Azure pricing page -- HQC = 5 + C (N_1q + 10 N_2q + 5 N_m)/5000, Standard plan
USD 125,000/month for 10k HQC (= USD 12.5/HQC, planner arithmetic).
Output: scratch/planner/helios_2x3_feasibility_20261002.json
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from skqd.device_req import clean_shot_fraction, required_error  # noqa: E402

req = json.load(open(os.path.join(ROOT, "data", "S2D_2x3_device_requirements.json")))
lev = req["levers"]
families = {
    "signed exact (RZZ basis)": dict(n_2q=2158, n_1q=7310, n_rz=4257, src="counts.coarse_step / levers.virtual_rz"),
    "fixed-angle generator": dict(n_2q=1620, n_1q=5415, n_rz=3216, src="levers.fixed_angle_generator.counts_rzz_recomputed"),
    "no plaq1": dict(n_2q=1394, n_1q=4830, n_rz=2727, src="levers.term_ablation no plaq1"),
    "fixed-angle + no plaq1": dict(n_2q=1218, n_1q=None, n_rz=None, src="levers.combined_fixed_angle_no_plaq1_virtual_rz (1q 1699 with virtual rz)"),
}
families["fixed-angle + no plaq1"]["n_1q_virtual"] = 1699
devices = {
    "Helios (arXiv:2511.05465 Table 2)": dict(eps2=7.9e-4, eps1=2.5e-5, eps_ro=4.8e-4),
    "H2 (product page '>99.9%', eps2 = 1e-3 bound; 1q 1e-4, SPAM 2e-3 assumed)": dict(eps2=1e-3, eps1=1e-4, eps_ro=2e-3),
    "IonQ Forte spec (information)": dict(eps2=4e-3, eps1=2e-4, eps_ro=5e-3),
}
rows = []
for fam, c in families.items():
    n1 = c.get("n_1q_virtual", None)
    if n1 is None:
        n1 = c["n_1q"] - c["n_rz"]
    for dev, e in devices.items():
        f = clean_shot_fraction(c["n_2q"], n1, 20, e["eps2"], e["eps1"], e["eps_ro"])
        hqc = (n1 + 10 * c["n_2q"] + 5 * 20) / 5000.0
        rows.append(dict(family=fam, device=dev, n_2q=c["n_2q"], n_1q_virtual_rz=n1, f_gate_only=f,
                         hqc_per_shot=hqc, usd_per_shot_at_12p5=12.5 * hqc,
                         # D3-type per-sector shot count scales as 1/f: 71500 at f = 0.1 (data/S2D_recall_at_f.json)
                         shots_per_sector_D3_scaled=71500 * 0.1 / f if f > 0 else None))
# idle estimate on Helios: memory error 5e-4 per depth-1 transport layer per qubit (arXiv:2511.05465
# Sec. III.2.4). Upper bound: every 2Q layer of the circuit is a depth-1 transport for all 20 qubits.
# 2Q depth of the signed circuit (all-to-all compile) is not separately recorded; use the all-gate
# depth 7325 (validation/S2.json) as a pessimistic proxy and 2158 (fully serial 2Q gates) as the
# optimistic one.
mem = 5e-4
idle = {}
for label, L in [("pessimistic: depth 7325 layers", 7325), ("optimistic: 2158 serial 2Q layers", 2158),
                 ("if 4 zones parallelise: 540 layers", 2158 // 4)]:
    S = 20 * L * mem
    idle[label] = dict(layers=L, S_idle_nats=S, exp_minus_S=__import__("math").exp(-S))
out = dict(rows=rows, helios_idle_estimate=idle,
           helios_time_estimate=dict(note="55 ms per depth-1 layer at 98 qubits random pairing (arXiv:2511.05465 Sec. II.3); "
                                          "20-qubit circuits transport less, so this is an upper bound per layer",
                                     seconds_per_shot_pessimistic=7325 * 0.055, seconds_per_shot_optimistic=540 * 0.055),
           eps2_required_signed_for_mean_f_0p1_virtual_rz=required_error("2q", dict(n_2q=2158, n_1q=3053, n_meas=20), 0.1,
                                                                          dict(eps1=2.5e-5, eps_ro=4.8e-4)) if False else None)
print(json.dumps(out, indent=1))
with open(os.path.join(ROOT, "scratch", "planner", "helios_2x3_feasibility_20261002.json"), "w") as fh:
    json.dump(out, fh, indent=1)
