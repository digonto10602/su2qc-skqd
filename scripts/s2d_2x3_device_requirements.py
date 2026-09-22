#!/usr/bin/env python3
"""
Device requirements sheet for the 2x3 all-to-all device -- open item 4 of
`proposal/amendment_01_devices_and_budgets.md`.

The amendment states one number for the 2x3 device ("two-qubit error 7.09e-04 or better"),
which holds eps1 and eps_ro at their declared values and says nothing about connectivity,
the native gate set, measurement, or the trade-off between the three error channels.  This
script turns that into a specification a vendor can answer:

  1. the gate counts the 2x3 coarse step needs on an all-to-all device -- per term, per
     circuit, and for the whole production set -- recomputed with `skqd.circuits_ir` and
     `gate_S2D.analyse_rzz` and checked against `validation/S2.json` and `validation/S2D.json`;
  2. the FEASIBLE REGION f(eps2, eps1, eps_ro) >= 0.1 for those counts: the exact
     error-budget half-space, the required eps2 as a function of eps1 at several eps_ro,
     the marginal requirement on each channel, and the tolerable routing overhead -- with
     and without a virtual-rz frame change;
  3. mean and worst-circuit f over the 44 circuits of the production set for every candidate
     error set, since the criterion constrains both (mean >= 0.1, worst >= 0.05), plus the
     shot rule at each;
  4. the levers already measured in this repository (fixed-angle generator of
     `validation/S2_fixed.json`, term and coupling-map ablations of
     `data/S2_escalation_experiments.json`, virtual rz) and how much each buys;
  5. a vendor-facing summary, with today's Heron numbers from this repository's own
     measurements (`validation/S2D.json`, `validation/H0P_ibm_fez.json`) so the gap is explicit.

Writes `data/S2D_2x3_device_requirements.json` and
`reports/S2D_2x3_device_requirements.md` (every number in the report comes from the JSON).

Changes nothing else: no criterion, tolerance, convention or decoder is touched, and
validation/S2.json, validation/S2D.json, validation/S2_fixed.json are read only.

Usage: python scripts/s2d_2x3_device_requirements.py [--quick] [--no-tests]
  --quick: k = 1 only (8 + 3 circuits instead of 44) -- the region tables are unchanged,
           the per-circuit spread is then taken from validation/S2D.json.
Runtime: about 7 minutes on the i7-8750H (CPU only), inside the 30-minute rule.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd import circuits_qiskit as cq  # noqa: E402
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.device_req import (CircuitCounts, budget_shares, circuit_f,  # noqa: E402
                             log_error_budget, required_error, required_error_for_set,
                             set_f, uniform_scale_for_set)
from skqd.exact import Model  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.report import ROOT, env_block, environment, md_table, write_report  # noqa: E402
from skqd.skqd import poisson_lambda_star, shot_rule  # noqa: E402

from gate_S2D import analyse_rzz  # noqa: E402  (the f model of gate S2D, not reimplemented)

G2 = 4.0
LX = 3                                  # the 2x3 ladder
BASIS_RZZ = ["rz", "rx", "ry", "rzz"]   # native gate set of the all-to-all RZZ device
LEVEL, SEED = 3, 7                      # gate S2D's transpiler settings
EPS2, EPS1, EPS_RO = 1e-3, 1e-4, 2e-3   # gate S2D's DECLARED inputs (vendor-class, not measured)
F_MEAN_MIN, F_WORST_MIN = 0.1, 0.05     # the amended criterion (amendment 01 section 1(c))
P_CONF, K_MIN, CONF = 1e-3, 3, 0.95     # the preregistered shot rule (manual Step 4.4)
YIELD_FACTOR = 0.82
S1_RECALL_MIN = 0.9                     # gate S1's recall criterion (preregistered, unchanged here)
EPS1_GRID = (0.0, 1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4)
EPS_RO_GRID = (1e-3, 2e-3, 5e-3, 1e-2)
ROUTING_OVERHEADS = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5)
SECTOR_CIRCUITS = {"B=0": 32, "B=1": 12}


# --------------------------------------------------------------------------- inputs
def load(path):
    with open(os.path.join(ROOT, path)) as fh:
        return json.load(fh)


def s2d_counts():
    """The 44 per-circuit RZZ-basis counts recorded by gate S2D (validation/S2D.json)."""
    per = load("validation/S2D.json")["data"]["2x3"]["per_circuit"]
    return [CircuitCounts(e["rzz"], e["n_1q"], e["n_rz"], 20,
                          f"{e['sector']} ref{e['reference']} k{e['k']}") for e in per]


def live_heron():
    """Today's Heron, from this repository's own live-calibration measurement.

    validation/H0P_ibm_fez.json -> data.f_recomputed_on_the_day: the per-circuit mean CZ
    edge error and mean readout error of the frozen 2x2 patches, computed by
    gate_S2D.analyse_on_backend against the LIVE ibm_fez target of the session day.
    """
    d = load("validation/H0P_ibm_fez.json")["data"]
    per = d["f_recomputed_on_the_day"]["per_circuit"]
    patches = sorted({(round(v["mean_edge_error"], 15), round(v["mean_readout_error"], 15))
                      for v in per.values()})
    best = min(patches)                      # the patch the day's layout actually preferred
    return {"backend": d["backend"], "live": bool(d["backend_is_live"]),
            "calibration_stamp": d["calibration"]["stamp"],
            "calibration_last_update": d["calibration"]["last_update_date"],
            "n_qubits": int(d["calibration"]["n_qubits_frozen_set"]),
            "n_edges": int(d["calibration"]["n_edges_frozen_set"]),
            "distinct_patches": [{"mean_edge_error": a, "mean_readout_error": b}
                                 for a, b in patches],
            "best_patch_mean_edge_error": best[0], "best_patch_mean_readout_error": best[1],
            "source": ("validation/H0P_ibm_fez.json -> data.f_recomputed_on_the_day.per_circuit "
                       "(gate_S2D.analyse_on_backend on the live ibm_fez target)")}


# --------------------------------------------------------------------------- counts
def transpile_rzz(gates, n, measure):
    from qiskit import transpile
    qc = cq.ir_to_qiskit(gates, n, measure=measure)
    return transpile(qc, basis_gates=BASIS_RZZ, coupling_map=None,
                     optimization_level=LEVEL, seed_transpiler=SEED)


def term_counts(F, n, dt):
    """Per-term counts of the coarse step, in the native RZZ basis and in the CZ basis.

    The CZ column is the reproduction check against validation/S2.json (per_term_cz), which
    used the same theta = dt of the B = 0 reference.
    """  # noqa: D401
    terms = [("diag", F.diag_gates(dt))]
    terms += [(f"hop{l}", F.hop_gates(l, dt)) for l in range(F.lat.n_links)]
    terms += [(f"plaq{P}", F.plaq_gates(P, dt, True)) for P in range(len(F.lat.plaquettes))]
    out = {}
    for name, gates in terms:
        a = analyse_rzz(transpile_rzz(gates, n, measure=False), EPS2, EPS1, EPS_RO, 0)
        cz = cq.transpile_counts(gates, n, coupling_map=None, optimization_level=LEVEL, seed=SEED)
        out[name] = {"rzz": a["rzz"], "n_1q": a["n_1q"], "n_rz": a["n_rz"], "depth": a["depth"],
                     "cz_all_to_all": cz["cz"], "ir_gates": len(gates)}
    return out


def counts_of_set(n, sets):
    """analyse_rzz on every circuit of a set: [(label, gates)] -> [CircuitCounts], records."""
    cc, rec = [], []
    for label, gates in sets:
        a = analyse_rzz(transpile_rzz(gates, n, measure=True), EPS2, EPS1, EPS_RO, n)
        a["label"] = label
        rec.append({k: a[k] for k in ("label", "rzz", "n_1q", "n_rz", "depth", "f", "f_virtual_rz")})
        cc.append(CircuitCounts(a["rzz"], a["n_1q"], a["n_rz"], n, label))
    return cc, rec


# --------------------------------------------------------------------------- region
def requirement_row(counts, eps1, eps_ro, virtual_rz):
    """The binding eps2 requirement at (eps1, eps_ro): mean f >= 0.1 AND worst f >= 0.05."""
    mean = required_error_for_set(counts, "2q", EPS2, eps1, eps_ro, F_MEAN_MIN, virtual_rz, "mean")
    worst = required_error_for_set(counts, "2q", EPS2, eps1, eps_ro, F_WORST_MIN, virtual_rz, "min")
    both = None if (mean is None or worst is None) else min(mean, worst)
    return {"eps1": eps1, "eps_ro": eps_ro, "virtual_rz": virtual_rz,
            "eps2_for_mean_f_0.1": mean, "eps2_for_worst_f_0.05": worst,
            "eps2_required": both,
            "binding": None if both is None else ("mean f >= 0.1" if mean <= (worst or mean)
                                                  else "worst f >= 0.05")}


def marginals(counts, virtual_rz):
    """Requirement on each channel with the other two at the declared values."""
    out = {}
    for ch in ("2q", "1q", "ro"):
        mean = required_error_for_set(counts, ch, EPS2, EPS1, EPS_RO, F_MEAN_MIN, virtual_rz, "mean")
        worst = required_error_for_set(counts, ch, EPS2, EPS1, EPS_RO, F_WORST_MIN, virtual_rz, "min")
        declared = {"2q": EPS2, "1q": EPS1, "ro": EPS_RO}[ch]
        out[ch] = {"declared": declared, "eps_for_mean_f_0.1": mean,
                   "eps_for_worst_f_0.05": worst,
                   "factor_improvement_needed": None if mean is None else declared / mean,
                   "feasible_alone": mean is not None}
    return out


def routing_table(mean_counts, virtual_rz):
    """Required eps2 when the device routes: n_2q -> rho x n_2q at fixed one-qubit count.

    Optimistic by construction (routing also adds one-qubit gates, see the measured
    heavy-hex point in the same table), so these are LOWER bounds on the requirement.
    """
    rows = []
    for rho in ROUTING_OVERHEADS:
        n2 = int(round(rho * mean_counts.n_2q))
        c = CircuitCounts(n2, mean_counts.n_1q, mean_counts.n_rz, mean_counts.n_meas)
        rest = circuit_f(CircuitCounts(0, c.n_1q, c.n_rz, c.n_meas), 0.0, EPS1, EPS_RO, virtual_rz)
        rows.append({"routing_overhead": rho, "n_2q": n2, "n_1q": c.one_qubit(virtual_rz),
                     "eps2_required": required_error(n2, F_MEAN_MIN, rest)})
    return rows


# --------------------------------------------------------------------------- candidates
def evaluate(counts, name, eps2, eps1, eps_ro, virtual_rz, note=""):
    st = set_f(counts, eps2, eps1, eps_ro, virtual_rz)
    sh = budget_shares(counts[0], eps2, eps1, eps_ro, F_MEAN_MIN, virtual_rz)
    rec = {"name": name, "eps2": eps2, "eps1": eps1, "eps_ro": eps_ro,
           "virtual_rz": bool(virtual_rz), "mean_f": st["mean"], "worst_f": st["min"],
           "max_f": st["max"], "worst_circuit": st["worst_label"],
           "meets_mean": bool(st["mean"] >= F_MEAN_MIN), "meets_worst": bool(st["min"] >= F_WORST_MIN),
           "log_budget_spend": sh["spend"], "log_budget": sh["budget_log"],
           "over_budget_by": sh["over_budget_by"],
           "f_shortfall_factor": F_MEAN_MIN / st["mean"] if st["mean"] > 0 else None,
           "note": note, "shot_budget": {}}
    rec["meets_criterion"] = bool(rec["meets_mean"] and rec["meets_worst"])
    for sec, ncirc in SECTOR_CIRCUITS.items():
        sub = [c for c in counts if c.label.startswith(sec)] or counts
        fm = set_f(sub, eps2, eps1, eps_ro, virtual_rz)["mean"]
        y = YIELD_FACTOR * fm
        n = shot_rule(P_CONF, y, K_MIN, CONF) if y > 0 else None
        rec["shot_budget"][sec] = {"n_circuits": ncirc, "mean_f": fm, "yield_clean": y,
                                   "N_circuit": n, "N_sector": None if n is None else n * ncirc}
    return rec


def max_two_qubit_gates(f_target, eps2, rest_factor):
    """Largest two-qubit gate count with rest_factor x (1 - eps2)^n >= f_target."""
    import math
    if rest_factor <= f_target:
        return 0
    return int(math.floor(math.log(f_target / rest_factor) / math.log1p(-eps2)))


def fmt(x, nd=3):
    if x is None:
        return "not reachable"
    return f"{x:.{nd}e}"


def ffmt(x):
    """f values: fixed point where it is readable, scientific when it is tiny."""
    return f"{x:.4f}" if x >= 1e-3 else f"{x:.3e}"


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="k = 1 only (the region tables are unchanged)")
    ap.add_argument("--no-tests", action="store_true")
    args = ap.parse_args()
    t0 = time.time()

    s2 = load("validation/S2.json")["data"]
    s2d = load("validation/S2D.json")["data"]
    s2f = load("validation/S2_fixed.json")["data"]
    esc = load("data/S2_escalation_experiments.json")

    M = Model(LX)
    F = CircuitFactory(M, G2)                       # exact structured circuits (the S2 default)
    n = F.n
    dt0 = M.reference(G2, 0).dt
    print(f"2x3: {n} qubits, building the production set ({time.time() - t0:.0f} s)", flush=True)

    # ------------------------------------------------------------- 1: gate counts
    terms = term_counts(F, n, dt0)
    ks = (1,) if args.quick else (1, 2, 3, 4)
    sets = []
    for twoB in (0, 2):
        dt = M.reference(G2, twoB).dt
        for r in references(M.basis, twoB):
            for k in ks:
                sets.append((f"B={twoB // 2} ref{r} k{k}", F.coarse_step(r, k, dt)))
    counts, per_circuit = counts_of_set(n, sets)
    print(f"  {len(counts)} circuits transpiled to {BASIS_RZZ} ({time.time() - t0:.0f} s)", flush=True)

    # the reference set the region tables use: the recomputed 44 circuits, or S2D's record
    # (identical by construction) when --quick shortened the recomputation
    recorded = s2d_counts()
    recomputed_subset_matches = all(
        any(c.n_2q == d.n_2q and c.n_1q == d.n_1q and c.n_rz == d.n_rz for d in recorded)
        for c in counts)
    region_counts = counts if len(counts) == len(recorded) else recorded
    mean_counts = CircuitCounts(int(round(np.mean([c.n_2q for c in region_counts]))),
                                int(round(np.mean([c.n_1q for c in region_counts]))),
                                int(round(np.mean([c.n_rz for c in region_counts]))), n)

    cz_a2a = cq.transpile_counts(sets[0][1], n, coupling_map=None,
                                 optimization_level=LEVEL, seed=SEED)["cz"]
    checks = {
        "per_term_cz_all_to_all_vs_S2": {
            "recomputed": {k: v["cz_all_to_all"] for k, v in terms.items()},
            "S2_json": s2["2x3"]["per_term_cz"],
            "match": {k: v["cz_all_to_all"] for k, v in terms.items()} == s2["2x3"]["per_term_cz"]},
        "coarse_step_cz_all_to_all_vs_S2": {
            "recomputed": int(cz_a2a), "S2_json": int(s2["2x3"]["coarse_step"]["all_to_all"]["cz"]),
            "match": int(cz_a2a) == int(s2["2x3"]["coarse_step"]["all_to_all"]["cz"])},
        "k1_rzz_counts_vs_S2D": {
            "recomputed": {kk: per_circuit[0][kk] for kk in ("rzz", "n_1q", "n_rz", "depth")},
            "S2D_json": {kk: s2d["2x3"]["per_circuit"][0][kk] for kk in ("rzz", "n_1q", "n_rz", "depth")},
            "match": all(per_circuit[0][kk] == s2d["2x3"]["per_circuit"][0][kk]
                         for kk in ("rzz", "n_1q", "n_rz", "depth"))},
        "every_recomputed_circuit_is_in_the_S2D_record": bool(recomputed_subset_matches),
        "region_counts_source": ("recomputed here" if region_counts is counts
                                 else "validation/S2D.json data.2x3.per_circuit"),
    }

    counts_block = {
        "device": "all-to-all, native two-qubit RZZ (no routing)",
        "n_qubits": n, "measured_qubits": n, "n_circuits_production_set": len(recorded),
        "n_circuits_recomputed_here": len(counts),
        "per_term": terms,
        "per_term_note": ("theta = dt of the B = 0 reference, the same angle validation/S2.json "
                          "used for per_term_cz; the coarse step is diag + all 7 hopping terms + "
                          "both plaquettes.  Compare per_term_rzz_sum with coarse_step.rzz to see "
                          "how much the transpiler merges across term boundaries"),
        "per_term_rzz_sum": int(sum(v["rzz"] for v in terms.values())),
        "coarse_step": {
            "rzz": {"mean": float(np.mean([c.n_2q for c in region_counts])),
                    "min": int(min(c.n_2q for c in region_counts)),
                    "max": int(max(c.n_2q for c in region_counts))},
            "n_1q": {"mean": float(np.mean([c.n_1q for c in region_counts])),
                     "min": int(min(c.n_1q for c in region_counts)),
                     "max": int(max(c.n_1q for c in region_counts))},
            "n_rz": {"mean": float(np.mean([c.n_rz for c in region_counts])),
                     "min": int(min(c.n_rz for c in region_counts)),
                     "max": int(max(c.n_rz for c in region_counts))},
            "n_1q_virtual_rz": {"mean": float(np.mean([c.one_qubit(True) for c in region_counts]))},
            "depth": s2d["2x3"]["depth"],
            "depth_source": "validation/S2D.json data.2x3.depth (same circuits, same transpiler settings)",
            "mean_counts_used_for_the_region": {"n_2q": mean_counts.n_2q, "n_1q": mean_counts.n_1q,
                                                "n_rz": mean_counts.n_rz, "n_meas": mean_counts.n_meas},
        },
        "cz_basis_all_to_all": int(cz_a2a),
        "cz_basis_routed_heavy_hex_d5": int(s2["2x3"]["coarse_step"]["routed"]["cz"]),
        "per_circuit_recomputed": per_circuit,
        "reproduction_checks": checks,
    }

    # ------------------------------------------------------------- 2: feasible region
    region = {"criterion": {"mean_f_min": F_MEAN_MIN, "worst_f_min": F_WORST_MIN,
                            "source": "amendment 01 section 1(c) / gate S2D"},
              "declared_inputs": {"eps2": EPS2, "eps1": EPS1, "eps_ro": EPS_RO,
                                  "source": "validation/S2D.json data.assumed_inputs"}}
    for vz in (False, True):
        tag = "virtual_rz" if vz else "physical_rz"
        st = set_f(region_counts, EPS2, EPS1, EPS_RO, vz)
        region[tag] = {
            "half_space": log_error_budget(mean_counts, F_MEAN_MIN, vz),
            "at_declared_inputs": {
                "mean_f": st["mean"], "worst_f": st["min"], "max_f": st["max"],
                "worst_circuit": st["worst_label"],
                "min_over_mean": st["spread_min_over_mean"],
                "budget_shares": budget_shares(mean_counts, EPS2, EPS1, EPS_RO, F_MEAN_MIN, vz)},
            "marginal_requirements": marginals(region_counts, vz),
            "eps2_grid": [requirement_row(region_counts, e1, ero, vz)
                          for ero in EPS_RO_GRID for e1 in EPS1_GRID],
            "uniform_scale_for_mean_f_0.1": uniform_scale_for_set(
                region_counts, EPS2, EPS1, EPS_RO, F_MEAN_MIN, vz),
            "routing_overhead": routing_table(mean_counts, vz),
        }
    # the fully measured routed point: a heavy-hex device would execute these counts
    routed = s2["2x3"]["coarse_step"]["routed"]
    n1_routed = int(sum(v for k, v in routed["ops"].items()
                        if k in ("rz", "sx", "x", "rx", "ry", "h", "p", "u")))
    region["measured_routed_heavy_hex_point"] = {
        "n_2q": int(routed["cz"]), "n_1q": n1_routed, "n_rz": int(routed["ops"].get("rz", 0)),
        "routing_overhead_vs_all_to_all": float(routed["cz"]) / float(s2["2x3"]["coarse_step"]["all_to_all"]["cz"]),
        "eps2_required_for_f_0.1": required_error(
            int(routed["cz"]), F_MEAN_MIN,
            circuit_f(CircuitCounts(0, n1_routed, 0, n), 0.0, EPS1, EPS_RO)),
        "source": "validation/S2.json data.2x3.coarse_step.routed (CZ basis, heavy-hex d = 5)"}
    mrp = region["measured_routed_heavy_hex_point"]
    mrp["requirement_tightens_by"] = (
        None if mrp["eps2_required_for_f_0.1"] in (None, 0) else
        region["physical_rz"]["marginal_requirements"]["2q"]["eps_for_mean_f_0.1"]
        / mrp["eps2_required_for_f_0.1"])
    mrp["one_qubit_gate_overhead_vs_all_to_all"] = n1_routed / float(
        counts_block["coarse_step"]["n_1q"]["mean"])

    # ------------------------------------------------------------- 3: candidate error sets
    lh = live_heron()
    fez = s2d["2x2"]["snapshots"]["FakeFez"]
    req2 = region["physical_rz"]["marginal_requirements"]["2q"]["eps_for_mean_f_0.1"]
    req2v = region["virtual_rz"]["marginal_requirements"]["2q"]["eps_for_mean_f_0.1"]
    req1 = region["physical_rz"]["marginal_requirements"]["1q"]["eps_for_mean_f_0.1"]
    lam = region["physical_rz"]["uniform_scale_for_mean_f_0.1"]
    routed_counts = [CircuitCounts(int(routed["cz"]), n1_routed,
                                   int(routed["ops"].get("rz", 0)), n, "B=0 routed heavy-hex")]
    cand = [
        evaluate(region_counts, "D0: declared inputs of gate S2D", EPS2, EPS1, EPS_RO, False,
                 "the amendment's 2x3 row; reproduces validation/S2D.json data.2x3.f"),
        evaluate(region_counts, "D0v: declared inputs, virtual rz", EPS2, EPS1, EPS_RO, True,
                 "reproduces validation/S2D.json data.2x3.f_virtual_rz"),
        evaluate(region_counts, "R1: the amendment's eps2, declared eps1/eps_ro", req2, EPS1, EPS_RO,
                 False, "the minimum two-qubit error at the declared eps1 and eps_ro"),
        evaluate(region_counts, "R1v: minimum eps2 with virtual rz", req2v, EPS1, EPS_RO, True,
                 "what a virtual-rz frame change buys on the two-qubit requirement"),
        evaluate(region_counts, "R2: declared eps2, minimum eps1", EPS2, req1, EPS_RO, False,
                 "the one-qubit-limited corner: eps2 stays at 1e-3"),
        evaluate(region_counts, "R3: all three declared errors scaled by the same factor",
                 lam * EPS2, lam * EPS1, lam * EPS_RO, False,
                 f"uniform improvement factor 1/lam = {1 / lam:.3f} on every channel"),
        evaluate(region_counts, "R4: round vendor point eps2 = 5e-4", 5e-4, EPS1, EPS_RO, False,
                 "a round number inside the feasible region"),
        evaluate(region_counts, "R5: round vendor point eps2 = 5e-4, eps_ro = 5e-3, virtual rz",
                 5e-4, EPS1, 5e-3, True, "shows how much readout error the region tolerates"),
        evaluate(region_counts, "H1: today's Heron (live ibm_fez patch) AS IF all-to-all",
                 lh["best_patch_mean_edge_error"], 0.0, lh["best_patch_mean_readout_error"], False,
                 "eps1 = 0, i.e. an upper bound on f; the 2x3 counts are the all-to-all ones, "
                 "which a heavy-hex device cannot execute without routing"),
        evaluate(region_counts, "H2: FakeFez snapshot patch AS IF all-to-all",
                 fez["patch_mean_edge_error"], 0.0, fez["patch_mean_readout_error"], False,
                 "the calibration snapshot on which the 2x2 row of the amendment passes"),
        evaluate(routed_counts, "H3: today's Heron on the ROUTED 2x3 circuit (what it would run)",
                 lh["best_patch_mean_edge_error"], 0.0, lh["best_patch_mean_readout_error"], False,
                 "validation/S2.json routed counts on the heavy-hex d = 5 map, eps1 = 0"),
    ]

    # ------------------------------------------------------------- 4: levers
    print(f"  levers ({time.time() - t0:.0f} s)", flush=True)
    Ff = CircuitFactory(M, G2, angle_mode="fixed")
    fixed_gates = Ff.coarse_step(references(M.basis, 0)[0], 1, dt0)
    fixed_counts, fixed_rec = counts_of_set(n, [("B=0 fixed-angle k1", fixed_gates)])
    fixed_cz = cq.transpile_counts(fixed_gates, n, coupling_map=None,
                                   optimization_level=LEVEL, seed=SEED)["cz"]
    # term ablations, exact generator: the coarse step without a term group
    abl = {}
    r0 = references(M.basis, 0)[0]
    variants = {
        "no plaq1 (interior-corner plaquette)": [t for t in range(len(F.lat.plaquettes)) if t != 1],
        "no plaquettes": [],
    }
    for name, keep in variants.items():
        g = F.prepare(r0) + F.diag_gates(dt0)
        for l in range(F.lat.n_links):
            g += F.hop_gates(l, dt0)
        for P in keep:
            g += F.plaq_gates(P, dt0, True)
        cc, rec = counts_of_set(n, [(f"B=0 {name} k1", g)])
        abl[name] = {"counts": rec[0],
                     "cz_all_to_all": cq.transpile_counts(g, n, coupling_map=None,
                                                          optimization_level=LEVEL, seed=SEED)["cz"],
                     "eps2_required_for_mean_f_0.1": required_error_for_set(
                         cc, "2q", EPS2, EPS1, EPS_RO, F_MEAN_MIN, False, "mean"),
                     "eps2_required_virtual_rz": required_error_for_set(
                         cc, "2q", EPS2, EPS1, EPS_RO, F_MEAN_MIN, True, "mean"),
                     "f_at_declared_inputs": circuit_f(cc[0], EPS2, EPS1, EPS_RO),
                     "f_at_declared_inputs_virtual_rz": circuit_f(cc[0], EPS2, EPS1, EPS_RO, True)}
    # the most permissive combination the repository can price: fixed angles, no plaq1, virtual rz
    gf = Ff.prepare(r0) + Ff.diag_gates(dt0)
    for l in range(Ff.lat.n_links):
        gf += Ff.hop_gates(l, dt0)
    gf += Ff.plaq_gates(0, dt0, True)
    comb_counts, comb_rec = counts_of_set(n, [("B=0 fixed-angle, no plaq1, k1", gf)])

    esc_recall = esc["ablation_2x3"]
    levers = {
        "virtual_rz": {
            "status": "UNSPENT -- a platform property, not a compilation choice",
            "what_it_removes": f"{mean_counts.n_rz} of the {mean_counts.n_1q} one-qubit gates "
                               f"per circuit carry no error",
            "mean_f_before": region["physical_rz"]["at_declared_inputs"]["mean_f"],
            "mean_f_after": region["virtual_rz"]["at_declared_inputs"]["mean_f"],
            "eps2_requirement_before": req2, "eps2_requirement_after": req2v,
            "evidence": "validation/S2D.json data.2x3.f_virtual_rz (reproduced here)"},
        "connectivity": {
            "status": "SPENT -- all-to-all is the floor; the requirement is already quoted there",
            "all_to_all_cz": esc["coupling_maps"]["2x3|coarse step k=1"]["all_to_all"],
            "grid_best_cz": esc["coupling_maps"]["2x3|coarse step k=1"]["grid_best"],
            "heavy_hex_best_cz": esc["coupling_maps"]["2x3|coarse step k=1"]["heavy_hex_best"],
            "line_cz": esc["coupling_maps"]["2x3|coarse step k=1"]["line"],
            "seeds": esc["coupling_maps"]["2x3|coarse step k=1"]["seeds"],
            "evidence": "data/S2_escalation_experiments.json coupling_maps"},
        "fixed_angle_generator": {
            "status": ("UNSPENT ON AN ALL-TO-ALL DEVICE -- gate S2_fixed was stopped on the ROUTED "
                       "heavy-hex cost (3736 CZ against the old 500-CZ budget), a routing cost that "
                       "does not exist on an all-to-all device; its all-to-all cost is 25 % below "
                       "the exact generator.  Not adopted by amendment 01 section 1(b): the owner "
                       "decides"),
            "counts_rzz_recomputed": fixed_rec[0],
            "cz_all_to_all_recomputed": int(fixed_cz),
            "cz_all_to_all_S2_fixed_json": int(s2f["2x3"]["coarse_step"]["all_to_all"]["cz"]),
            "cz_all_to_all_exact_S2_json": int(s2["2x3"]["coarse_step"]["all_to_all"]["cz"]),
            "cz_routed_heavy_hex_S2_fixed_json": int(s2f["2x3"]["coarse_step"]["routed"]["cz"]),
            "f_at_declared_inputs": circuit_f(fixed_counts[0], EPS2, EPS1, EPS_RO),
            "f_at_declared_inputs_virtual_rz": circuit_f(fixed_counts[0], EPS2, EPS1, EPS_RO, True),
            "eps2_required_for_mean_f_0.1": required_error_for_set(
                fixed_counts, "2q", EPS2, EPS1, EPS_RO, F_MEAN_MIN, False, "mean"),
            "eps2_required_virtual_rz": required_error_for_set(
                fixed_counts, "2q", EPS2, EPS1, EPS_RO, F_MEAN_MIN, True, "mean"),
            "recall_evidence": {c["name"]: c["value"] for c in load("validation/S2_fixed.json")["criteria"]
                                if "recall" in c["name"]},
            "price": ("a different generator: per-term deviation from exp(-i theta H) is ~1e-1, not "
                      "1e-14 (validation/S2_fixed.json per_term_max_deviation); it is justified by "
                      "the S1 recall criterion, not by Trotter accuracy")},
        "term_ablation": {
            "status": ("PARTLY UNSPENT -- dropping plaq1 keeps the S1 recall criterion in both "
                       "sectors; dropping both plaquettes breaks it in B = 1"),
            "variants": abl,
            "s1_recall_threshold": S1_RECALL_MIN,
            "recall_at_f_0.1": {k: {"B=0": esc_recall[f"B=0|{k}"]["f=0.1"]["recall"],
                                    "B=1": esc_recall[f"B=1|{k}"]["f=0.1"]["recall"],
                                    "meets_s1": bool(min(esc_recall[f"B=0|{k}"]["f=0.1"]["recall"],
                                                         esc_recall[f"B=1|{k}"]["f=0.1"]["recall"])
                                                     >= S1_RECALL_MIN)}
                                for k in ("full (S1 generator)", "no plaq1 (interior-corner plaquette)",
                                          "no plaquettes")},
            "evidence": "data/S2_escalation_experiments.json ablation_2x3 (2e5 shots per sector)"},
        "combined_fixed_angle_no_plaq1_virtual_rz": {
            "status": "UNSPENT but UNMEASURED as a combination",
            "counts_rzz_recomputed": comb_rec[0],
            "f_at_declared_inputs_virtual_rz": circuit_f(comb_counts[0], EPS2, EPS1, EPS_RO, True),
            "eps2_required_virtual_rz": required_error_for_set(
                comb_counts, "2q", EPS2, EPS1, EPS_RO, F_MEAN_MIN, True, "mean"),
            "caveat": ("the recall of the fixed-angle generator WITHOUT plaq1 has not been emulated; "
                       "each lever is measured alone.  Nothing may be claimed for the combination "
                       "until that emulation is run")},
        "shot_quota": {
            "status": "OPEN ITEM 5 of the amendment, decided separately -- not a device lever",
            "note": "raising the quota does not change f; it changes what f the run can afford"},
    }

    # ------------------------------------------------------------- 5: vendor summary
    best_row = next(c for c in cand if c["name"].startswith("R1:"))
    best_row_v = next(c for c in cand if c["name"].startswith("R1v:"))
    vendor = {
        "qubits": n,
        "connectivity": {
            "statement": ("all-to-all preferred; the requirement below is quoted at zero routing "
                          "overhead, and the tolerable overhead is tabulated"),
            "max_two_qubit_gates_at_eps2_5e-4": max_two_qubit_gates(
                F_MEAN_MIN, 5e-4, circuit_f(CircuitCounts(0, mean_counts.n_1q, mean_counts.n_rz, n),
                                            0.0, EPS1, EPS_RO)),
            "max_routing_overhead_at_eps2_5e-4": max_two_qubit_gates(
                F_MEAN_MIN, 5e-4, circuit_f(CircuitCounts(0, mean_counts.n_1q, mean_counts.n_rz, n),
                                            0.0, EPS1, EPS_RO)) / mean_counts.n_2q},
        "native_two_qubit_gate": ("RZZ(theta) with a continuous angle (the compilation measured "
                                 "here uses basis {rz, rx, ry, rzz}); a CZ-only device needs "
                                 f"{int(cz_a2a)} CZ instead of {mean_counts.n_2q} RZZ for the same step"),
        "two_qubit_error": {"required": req2, "required_with_virtual_rz": req2v,
                            "declared_in_the_amendment": EPS2,
                            "at_gate_counts": mean_counts.n_2q},
        "one_qubit_error": {"required_if_eps2_stays_at_declared": req1,
                            "declared": EPS1,
                            "gate_count_physical_rz": mean_counts.n_1q,
                            "gate_count_virtual_rz": mean_counts.one_qubit(True),
                            "note": "no requirement on rz if rz is a virtual frame change"},
        "readout_error": {
            "declared": EPS_RO, "measured_qubits": n,
            "marginal_requirement": region["physical_rz"]["marginal_requirements"]["ro"]["eps_for_mean_f_0.1"],
            "note": ("readout spends only "
                     f"{region['physical_rz']['at_declared_inputs']['budget_shares']['fraction_of_budget']['ro'] * 100:.1f} % "
                     "of the error budget at the declared 2e-3, so it is not the binding channel; "
                     "it becomes binding only once the two-qubit channel is inside the region"),
            "tolerable_at_the_R4_point": required_error_for_set(
                region_counts, "ro", 5e-4, EPS1, EPS_RO, F_MEAN_MIN, False, "mean")},
        "mid_circuit_measurement_or_reset": "not required: the circuits measure once, at the end",
        "depth": s2d["2x3"]["depth"],
        "today_heron_gap": {
            "live_ibm_fez": lh,
            "FakeFez_snapshot": {"patch_mean_edge_error": fez["patch_mean_edge_error"],
                                 "patch_mean_readout_error": fez["patch_mean_readout_error"],
                                 "snapshot_median_cz_error": fez["snapshot_median_cz_error"],
                                 "source": "validation/S2D.json data.2x2.snapshots.FakeFez"},
            "two_qubit_error_factor_to_close": lh["best_patch_mean_edge_error"] / req2,
            "two_qubit_error_factor_to_close_virtual_rz": lh["best_patch_mean_edge_error"] / req2v,
            "readout_factor_at_the_R4_point": None,
        },
    }
    ro_at_r4 = vendor["readout_error"]["tolerable_at_the_R4_point"]
    vendor["today_heron_gap"]["readout_factor_at_the_R4_point"] = (
        None if ro_at_r4 in (None, 0) else lh["best_patch_mean_readout_error"] / ro_at_r4)

    data = {
        "title": ("Device requirements for the 2x3 coarse-step circuits -- open item 4 of "
                  "proposal/amendment_01_devices_and_budgets.md"),
        "scope": ("a requirement, not a device claim: no vendor product is named and no vendor "
                  "specification is asserted anywhere in this file.  The owner matches a device "
                  "to the region below"),
        "produced_by": "scripts/s2d_2x3_device_requirements.py",
        "criterion": {"mean_f_min": F_MEAN_MIN, "worst_f_min": F_WORST_MIN,
                      "f_model": "f = (1-eps2)^n_2q (1-eps1)^n_1q (1-eps_ro)^n_meas "
                                 "(gate_S2D.analyse_rzz / skqd.device_req.clean_shot_fraction)",
                      "source": "amendment 01 section 1(c); gate S2D; manual Step 4.4"},
        "shot_rule_inputs": {"p": P_CONF, "k": K_MIN, "confidence": CONF,
                             "lambda_star": float(poisson_lambda_star(K_MIN, CONF)),
                             "yield": f"y = {YIELD_FACTOR} f (clean shots, manual Step 4.4)"},
        "counts": counts_block,
        "feasible_region": region,
        "candidate_error_sets": cand,
        "levers": levers,
        "vendor_summary": vendor,
        "sources": {
            "validation/S2.json": {"2x3 all-to-all CZ": s2["2x3"]["coarse_step"]["all_to_all"]["cz"],
                                   "2x3 routed heavy-hex CZ": s2["2x3"]["coarse_step"]["routed"]["cz"],
                                   "2x3 per-term CZ": s2["2x3"]["per_term_cz"]},
            "validation/S2D.json": {"2x3 mean f": s2d["2x3"]["f"]["mean"],
                                    "2x3 worst f": s2d["2x3"]["f"]["min"],
                                    "2x3 f virtual rz": s2d["2x3"]["f_virtual_rz"]["mean"],
                                    "2x3 eps2 required (mean counts)": s2d["2x3"]["eps2_required_for_f_0.1"],
                                    "declared inputs": s2d["assumed_inputs"]},
            "validation/S2_fixed.json": {"2x3 all-to-all CZ": s2f["2x3"]["coarse_step"]["all_to_all"]["cz"],
                                         "2x3 routed CZ": s2f["2x3"]["coarse_step"]["routed"]["cz"]},
            "data/S2_escalation_experiments.json": esc["coupling_maps"]["2x3|coarse step k=1"],
            "validation/H0P_ibm_fez.json": lh,
        },
        "runtime_s": time.time() - t0,
        "environment": environment(),
        "quick": bool(args.quick),
    }
    if not args.no_tests:
        tp = subprocess.run([sys.executable, "-m", "pytest", "-q", "--color=no", "tests"],
                            cwd=ROOT, capture_output=True, text=True)
        data["pytest"] = tp.stdout.strip().splitlines()[-1] if tp.stdout.strip() else "no output"
        data["pytest_returncode"] = tp.returncode
    path = os.path.join(ROOT, "data", "S2D_2x3_device_requirements.json")
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)
    write_report("S2D_2x3_device_requirements.md", report_text(data))
    print(f"wrote {path} and reports/S2D_2x3_device_requirements.md "
          f"({data['runtime_s']:.0f} s)", flush=True)
    for c in cand:
        print(f"  {c['name'][:52]:52s} mean f {c['mean_f']:.4f}  worst {c['worst_f']:.4f}  "
              f"{'meets' if c['meets_criterion'] else 'MISSES'} the criterion")
    return 0


# --------------------------------------------------------------------------- report
def report_text(D):
    C, R, V = D["counts"], D["feasible_region"], D["vendor_summary"]
    ph, vz = R["physical_rz"], R["virtual_rz"]
    chk = C["reproduction_checks"]
    L = D["levers"]

    term_rows = [[t, v["rzz"], v["n_1q"], v["n_rz"], v["depth"], v["cz_all_to_all"],
                  C["reproduction_checks"]["per_term_cz_all_to_all_vs_S2"]["S2_json"][t]]
                 for t, v in C["per_term"].items()]
    step = C["coarse_step"]
    step_rows = [["RZZ (native two-qubit)", f"{step['rzz']['mean']:.0f}", step["rzz"]["min"], step["rzz"]["max"]],
                 ["one-qubit gates (physical rz)", f"{step['n_1q']['mean']:.0f}", step["n_1q"]["min"], step["n_1q"]["max"]],
                 ["of which rz", f"{step['n_rz']['mean']:.0f}", step["n_rz"]["min"], step["n_rz"]["max"]],
                 ["one-qubit gates (virtual rz)", f"{step['n_1q_virtual_rz']['mean']:.0f}", "-", "-"],
                 ["depth", f"{step['depth']['mean']:.0f}", f"{step['depth']['min']:.0f}",
                  f"{step['depth']['max']:.0f}"],
                 ["measured qubits", C["measured_qubits"], C["measured_qubits"], C["measured_qubits"]]]

    def share_rows(block, weights):
        s = block["at_declared_inputs"]["budget_shares"]
        return [[ch, weights[ch], f"{s['spend'][ch]:.4f}",
                 f"{s['fraction_of_budget'][ch] * 100:.1f} %", f"{s['fraction_of_total'][ch] * 100:.1f} %"]
                for ch in ("2q", "1q", "ro")]

    grid_rows = []
    for row in ph["eps2_grid"]:
        v = next(r for r in vz["eps2_grid"]
                 if r["eps1"] == row["eps1"] and r["eps_ro"] == row["eps_ro"])
        grid_rows.append([f"{row['eps_ro']:.0e}", f"{row['eps1']:.0e}" if row["eps1"] else "0 (virtual/ideal)",
                          fmt(row["eps2_for_mean_f_0.1"]), fmt(row["eps2_for_worst_f_0.05"]),
                          fmt(v["eps2_for_mean_f_0.1"])])

    marg_rows = []
    for ch, label in (("2q", "two-qubit error eps2"), ("1q", "one-qubit error eps1"),
                      ("ro", "readout error eps_ro")):
        a, b = ph["marginal_requirements"][ch], vz["marginal_requirements"][ch]
        marg_rows.append([label, ph["half_space"]["weights"][ch], f"{a['declared']:.0e}",
                          fmt(a["eps_for_mean_f_0.1"]), fmt(a["eps_for_worst_f_0.05"]),
                          "-" if a["factor_improvement_needed"] is None
                          else f"{a['factor_improvement_needed']:.2f}x",
                          vz["half_space"]["weights"][ch], fmt(b["eps_for_mean_f_0.1"])])

    route_rows = [[f"{a['routing_overhead']:.2f}x", a["n_2q"], fmt(a["eps2_required"]),
                   fmt(next(b for b in vz["routing_overhead"]
                            if b["routing_overhead"] == a["routing_overhead"])["eps2_required"])]
                  for a in ph["routing_overhead"]]
    mp = R["measured_routed_heavy_hex_point"]
    route_rows.append([f"{mp['routing_overhead_vs_all_to_all']:.2f}x (measured, heavy-hex d = 5)",
                       mp["n_2q"], fmt(mp["eps2_required_for_f_0.1"]), "-"])

    cand_rows = [[c["name"], f"{c['eps2']:.3e}", f"{c['eps1']:.3e}", f"{c['eps_ro']:.3e}",
                  "yes" if c["virtual_rz"] else "no", ffmt(c["mean_f"]), ffmt(c["worst_f"]),
                  "PASS" if c["meets_criterion"] else "FAIL",
                  "-" if c["shot_budget"]["B=0"]["N_circuit"] is None
                  else f"{c['shot_budget']['B=0']['N_circuit']:d}",
                  "-" if c["shot_budget"]["B=0"]["N_sector"] is None
                  else f"{c['shot_budget']['B=0']['N_sector']:.3e}"]
                 for c in D["candidate_error_sets"]]

    fa, ab, cb = L["fixed_angle_generator"], L["term_ablation"], L["combined_fixed_angle_no_plaq1_virtual_rz"]
    lever_rows = [
        ["virtual rz (platform property)", L["virtual_rz"]["what_it_removes"],
         f"{L['virtual_rz']['mean_f_before']:.4f} -> {L['virtual_rz']['mean_f_after']:.4f}",
         f"{fmt(L['virtual_rz']['eps2_requirement_before'])} -> {fmt(L['virtual_rz']['eps2_requirement_after'])}",
         "UNSPENT"],
        ["fixed-angle generator (validation/S2_fixed.json)",
         f"{fa['cz_all_to_all_recomputed']} CZ / {fa['counts_rzz_recomputed']['rzz']} RZZ against "
         f"{fa['cz_all_to_all_exact_S2_json']} CZ / {int(step['rzz']['mean'])} RZZ exact",
         f"{fa['f_at_declared_inputs']:.4f} (virtual rz {fa['f_at_declared_inputs_virtual_rz']:.4f})",
         f"{fmt(fa['eps2_required_for_mean_f_0.1'])} (virtual rz {fmt(fa['eps2_required_virtual_rz'])})",
         "UNSPENT on an all-to-all device"],
    ]
    for name, v in ab["variants"].items():
        lever_rows.append([f"term ablation: {name}",
                           f"{v['cz_all_to_all']} CZ / {v['counts']['rzz']} RZZ",
                           f"{v['f_at_declared_inputs']:.4f} (virtual rz "
                           f"{v['f_at_declared_inputs_virtual_rz']:.4f})",
                           fmt(v["eps2_required_for_mean_f_0.1"]),
                           ("UNSPENT" if ab["recall_at_f_0.1"][name]["meets_s1"] else "SPENT")
                           + f" (recall at f = 0.1: B=0 {ab['recall_at_f_0.1'][name]['B=0']:.3f}, "
                           f"B=1 {ab['recall_at_f_0.1'][name]['B=1']:.3f} against the S1 "
                           f"criterion {ab['s1_recall_threshold']})"])
    lever_rows.append(["connectivity", f"all-to-all {L['connectivity']['all_to_all_cz']} CZ, "
                       f"grid best {L['connectivity']['grid_best_cz']}, heavy-hex best "
                       f"{L['connectivity']['heavy_hex_best_cz']}, line {L['connectivity']['line_cz']}",
                       "-", "-", "SPENT (all-to-all is the floor)"])
    lever_rows.append(["fixed angles + no plaq1 + virtual rz (combined)",
                       f"{cb['counts_rzz_recomputed']['rzz']} RZZ",
                       f"{cb['f_at_declared_inputs_virtual_rz']:.4f}",
                       fmt(cb["eps2_required_virtual_rz"]),
                       "UNSPENT but the recall of the combination is UNMEASURED"])

    lh = V["today_heron_gap"]["live_ibm_fez"]
    vendor_rows = [
        ["qubits", V["qubits"], "-", f"{lh['n_qubits']} frozen-set qubits on {lh['backend']}"],
        ["connectivity", V["connectivity"]["statement"],
         "-", f"heavy-hex: {mp['routing_overhead_vs_all_to_all']:.2f}x routing overhead measured "
              f"({mp['n_2q']} CZ)"],
        ["native two-qubit gate", "RZZ(theta), continuous angle",
         f"{int(step['rzz']['mean'])} per circuit",
         f"CZ only: {C['cz_basis_all_to_all']} per circuit all-to-all"],
        ["two-qubit error eps2", fmt(V["two_qubit_error"]["required"]),
         f"declared {V['two_qubit_error']['declared_in_the_amendment']:.0e}",
         f"{lh['best_patch_mean_edge_error']:.3e} (live {lh['backend']}, "
         f"{V['today_heron_gap']['two_qubit_error_factor_to_close']:.2f}x too high)"],
        ["two-qubit error eps2, virtual rz", fmt(V["two_qubit_error"]["required_with_virtual_rz"]),
         "-", f"{V['today_heron_gap']['two_qubit_error_factor_to_close_virtual_rz']:.2f}x too high"],
        ["one-qubit error eps1 (physical rz)", fmt(V["one_qubit_error"]["required_if_eps2_stays_at_declared"]),
         f"declared {V['one_qubit_error']['declared']:.0e}, "
         f"{V['one_qubit_error']['gate_count_physical_rz']} gates per circuit",
         "not resolved per gate in this repository's Heron measurements"],
        ["one-qubit error eps1 (virtual rz)", "no requirement on rz",
         f"{V['one_qubit_error']['gate_count_virtual_rz']} error-carrying gates per circuit", "-"],
        ["readout error eps_ro",
         f"{fmt(V['readout_error']['tolerable_at_the_R4_point'])} once eps2 = 5e-4 "
         f"(at eps1 = {V['one_qubit_error']['declared']:.0e})",
         f"declared {V['readout_error']['declared']:.0e}, "
         f"{V['readout_error']['measured_qubits']} measured qubits",
         f"{lh['best_patch_mean_readout_error']:.3e} (live {lh['backend']})"],
        ["mid-circuit measurement / reset", V["mid_circuit_measurement_or_reset"],
         f"{C['measured_qubits']} measurements and 1 barrier per circuit, at the end", "-"],
        ["circuit depth", f"{V['depth']['mean']:.0f} (mean), {V['depth']['max']:.0f} (max)",
         "-", "-"],
    ]

    d0 = next(c for c in D["candidate_error_sets"] if c["name"].startswith("D0:"))
    r1 = next(c for c in D["candidate_error_sets"] if c["name"].startswith("R1:"))
    r1v = next(c for c in D["candidate_error_sets"] if c["name"].startswith("R1v:"))
    h3 = next(c for c in D["candidate_error_sets"] if c["name"].startswith("H3:"))
    lam = ph["uniform_scale_for_mean_f_0.1"]
    shares = ph["at_declared_inputs"]["budget_shares"]

    return f"""# Device requirements for the 2x3 coarse-step circuits (20 qubits, all-to-all)

Open item 4 of `proposal/amendment_01_devices_and_budgets.md`.  Produced by
`scripts/s2d_2x3_device_requirements.py`; every number below is read from
`data/S2D_2x3_device_requirements.json`, which the same script wrote.  {env_block()}
Runtime {D['runtime_s']:.0f} s.  `pytest -q tests`: {D.get('pytest', 'not run')}.

**What this sheet is.**  A *requirement*: the region of device error rates in which the
preregistered 2x3 circuit set satisfies the amended budget criterion.  It names no vendor and
asserts no vendor specification -- there is no verified source for any product's error rates in
this repository, and an unsourced claim in a preregistration amendment would be worse than no
claim.  The owner matches a device to the region.

**What it replaces.**  The amendment currently states one number, "two-qubit error
{fmt(D['sources']['validation/S2D.json']['2x3 eps2 required (mean counts)'])} or better", which holds
eps1 and eps_ro at their declared values.  That number is reproduced below
({fmt(V['two_qubit_error']['required'])}, computed from the {C['n_circuits_production_set']}-circuit
set rather than from the mean gate counts) and is one point on a boundary, not the requirement.

## 0. The criterion and the model

Criterion (amendment 01 section 1(c), gate S2D): over the production circuit set of the lattice,

> mean f >= {D['criterion']['mean_f_min']} and worst-circuit f >= {D['criterion']['worst_f_min']},
> f = (1 - eps2)^n_2q x (1 - eps1)^n_1q x (1 - eps_ro)^n_meas.

The f model is gate S2D's (`gate_S2D.analyse_rzz`); this sheet only inverts it
(`skqd.device_req`, tested in `tests/test_device_req.py` against the recorded S2D numbers).
The circuit family is unchanged: the exact structured circuits of gate S2
(`skqd.circuits_ir.CircuitFactory`, `angle_mode="exact"`), coarse steps k = 1..4 of every
reference of both sectors -- {C['n_circuits_production_set']} circuits.

## 1. What the circuits need from the device

Per term of the coarse step (theta = dt of the B = 0 reference, all-to-all, no routing):

{md_table(["term", "RZZ", "1q gates", "of which rz", "depth", "CZ basis (all-to-all)",
           "CZ in validation/S2.json"], term_rows)}

The CZ column reproduces `validation/S2.json` `data.2x3.per_term_cz` exactly
({'match' if chk['per_term_cz_all_to_all_vs_S2']['match'] else 'MISMATCH -- STOP'}), which is the
check that this sheet is priced on the preregistered circuits.  The two plaquette terms and
`hop4` dominate; the diagonal term is negligible.  The per-term RZZ counts sum to
{C['per_term_rzz_sum']} against {step['rzz']['mean']:.0f} for the compiled step, so the two-qubit
cost is additive over terms: **removing a term removes its RZZ count, one for one** -- which is what
makes the ablation lever of section 4 priceable.

Per compiled circuit, over the {C['n_circuits_production_set']} circuits of the production set:

{md_table(["quantity", "mean", "min", "max"], step_rows)}

Reproduction checks: the k = 1 coarse step compiles to
{chk['k1_rzz_counts_vs_S2D']['recomputed']['rzz']} RZZ and
{chk['k1_rzz_counts_vs_S2D']['recomputed']['n_1q']} one-qubit gates, identical to
`validation/S2D.json` `data.2x3.per_circuit[0]`
({'match' if chk['k1_rzz_counts_vs_S2D']['match'] else 'MISMATCH -- STOP'}); in the CZ basis the
same step is {C['cz_basis_all_to_all']} CZ, identical to `validation/S2.json`
({'match' if chk['coarse_step_cz_all_to_all_vs_S2']['match'] else 'MISMATCH -- STOP'}).  The RZZ
count is the same, {step['rzz']['min']}, for every circuit of the set: k and the reference change
the angles, not the structure.  Only the one-qubit count moves
({step['n_1q']['min']}..{step['n_1q']['max']}), which is why the per-circuit spread of f is
{(1 - ph['at_declared_inputs']['min_over_mean']) * 100:.2f} % (section 3).

## 2. The feasible region

Take -log of the f model: the criterion `mean f >= {D['criterion']['mean_f_min']}` is, at the mean
gate counts, the half-space

> {ph['half_space']['weights']['2q']} x (-ln(1 - eps2)) + {ph['half_space']['weights']['1q']} x (-ln(1 - eps1)) + {ph['half_space']['weights']['ro']} x (-ln(1 - eps_ro)) <= ln(1/{D['criterion']['mean_f_min']}) = {ph['half_space']['budget_log']:.6f}

or, to first order in the errors,
{ph['half_space']['weights']['2q']} eps2 + {ph['half_space']['weights']['1q']} eps1 + {ph['half_space']['weights']['ro']} eps_ro <= {ph['half_space']['budget_log']:.4f}.
With a virtual-rz frame change the one-qubit weight drops to
{vz['half_space']['weights']['1q']}.  **This single inequality is the requirement**; everything
below is a slice of it.  A vendor can answer it with three numbers.

How the declared triple (eps2 = {R['declared_inputs']['eps2']:.0e}, eps1 =
{R['declared_inputs']['eps1']:.0e}, eps_ro = {R['declared_inputs']['eps_ro']:.0e}) spends that budget:

{md_table(["channel", "gates per circuit", "log-error spent", "share of the ln(1/0.1) budget",
           "share of the total loss"], share_rows(ph, ph['half_space']['weights']))}

Total spent {shares['total']:.4f} against a budget of {shares['budget_log']:.4f}: over by
{shares['over_budget_by']:.4f} in log terms, i.e. f is a factor
{d0['f_shortfall_factor']:.2f} too small.  The two-qubit channel alone spends
{shares['fraction_of_budget']['2q'] * 100:.1f} % of the budget and the one-qubit channel
{shares['fraction_of_budget']['1q'] * 100:.1f} %; readout spends
{shares['fraction_of_budget']['ro'] * 100:.1f} %.

### 2a. Required two-qubit error as a function of the other two channels

The eps2 that makes the criterion hold exactly, at each (eps1, eps_ro).  The mean and worst
columns are the two halves of the criterion; the binding one is the smaller.

{md_table(["eps_ro", "eps1", "eps2 for mean f >= 0.1", "eps2 for worst f >= 0.05",
           "eps2 for mean f >= 0.1, virtual rz"], grid_rows)}

Reading: eps_ro barely moves the requirement (20 measured qubits against
{ph['half_space']['weights']['2q']} two-qubit gates), eps1 moves it strongly (there are
{ph['half_space']['weights']['1q']} one-qubit gates, {step['n_rz']['min']}..{step['n_rz']['max']} of
them rz), and the mean criterion is always the binding half -- the worst-circuit column is looser
by construction, because the spread over the set is
{(1 - ph['at_declared_inputs']['min_over_mean']) * 100:.2f} %.

### 2b. Marginal requirement on each channel

Each channel at the criterion with the other two held at the declared values:

{md_table(["channel", "gates per circuit", "declared", "required for mean f >= 0.1",
           "required for worst f >= 0.05", "improvement needed", "gates (virtual rz)",
           "required, virtual rz"], marg_rows)}

Three facts a vendor should read off this table.

1. **Readout alone cannot satisfy the criterion.**  At the declared eps2 and eps1 the two-qubit
   and one-qubit factors already multiply to below {D['criterion']['mean_f_min']}, so no readout
   error, not even zero, reaches the criterion.  Readout is a constraint only once the other two
   channels are inside the region (section 2a).
2. **The one-qubit channel is a real requirement, not a rounding error.**  Holding eps2 at the
   declared {R['declared_inputs']['eps2']:.0e}, the criterion needs eps1 <=
   {fmt(ph['marginal_requirements']['1q']['eps_for_mean_f_0.1'])} -- a factor
   {ph['marginal_requirements']['1q']['factor_improvement_needed']:.1f} below the declared value.
   With virtual rz that relaxes to {fmt(vz['marginal_requirements']['1q']['eps_for_mean_f_0.1'])}.
3. **A uniform improvement of all three channels by a factor
   {1 / lam:.3f}** also satisfies the criterion (candidate R3 below); with virtual rz the factor is
   {1 / vz['uniform_scale_for_mean_f_0.1']:.3f}.

### 2c. Tolerable routing overhead

If the device is not all-to-all, the same step executes rho x
{ph['half_space']['weights']['2q']} two-qubit gates.  Holding the one-qubit count fixed (optimistic
-- routing adds one-qubit gates too, see the measured row):

{md_table(["routing overhead rho", "two-qubit gates", "eps2 required (physical rz)",
           "eps2 required (virtual rz)"], route_rows)}

The last row is the fully measured heavy-hex point of `validation/S2.json`
({mp['n_2q']} CZ and {mp['n_1q']} one-qubit gates after routing on a d = 5 map): a heavy-hex device
would need eps2 <= {fmt(mp['eps2_required_for_f_0.1'])}.  **Routing overhead is the most expensive
single property in this table.**  The pure two-qubit effect is the rho = 2.50 row above
({fmt(next(r['eps2_required'] for r in ph['routing_overhead'] if r['routing_overhead'] == 2.5))}),
but routing also multiplies the one-qubit count by
{mp['one_qubit_gate_overhead_vs_all_to_all']:.2f}x, so the measured requirement is a factor
{mp['requirement_tightens_by']:.1f} tighter than at all-to-all, not a factor
{mp['routing_overhead_vs_all_to_all']:.1f}.  **All-to-all connectivity is worth a factor
{mp['requirement_tightens_by']:.1f} in two-qubit error** for this circuit.

## 3. Candidate error sets: mean and worst f over the {C['n_circuits_production_set']} circuits

Both halves of the criterion, for every candidate, with the shot rule of manual Step 4.4
(p = {D['shot_rule_inputs']['p']:.0e}, k = {D['shot_rule_inputs']['k']}, confidence
{D['shot_rule_inputs']['confidence']}, {D['shot_rule_inputs']['yield']}) in the B = 0 sector:

{md_table(["error set", "eps2", "eps1", "eps_ro", "virtual rz", "mean f", "worst f",
           "criterion", "N per circuit (B=0)", "N per sector (B=0)"], cand_rows)}

The worst circuit is the same one throughout ({d0['worst_circuit']}) and sits
{(1 - ph['at_declared_inputs']['min_over_mean']) * 100:.2f} % below the mean, so the
worst >= {D['criterion']['worst_f_min']} half of the criterion is never the binding one at 2x3; at
the declared inputs it is in fact already satisfied (worst f = {d0['worst_f']:.4f}) while the mean
half fails.  The spread is small because every circuit of the set has the same
{step['rzz']['mean']:.0f} RZZ gates; it is reported here because the criterion constrains it, not
because it is at risk.  What a single number *does* hide is the trade-off: rows R1, R1v, R2 and R3
all satisfy the criterion on four devices with different two-qubit errors
({', '.join(f"{c['eps2']:.3e}" for c in D['candidate_error_sets'] if c['name'][:3] in ('R1:', 'R1v', 'R2:', 'R3:'))}).

The last three rows are the gap to today's hardware, from this repository's own measurements.
Row H3 is the honest one: a heavy-hex Heron must route, so it executes {mp['n_2q']} two-qubit
gates, and at the live edge error measured on {lh['backend']} it reaches mean f =
{h3['mean_f']:.3e} -- {D['criterion']['mean_f_min'] / h3['mean_f']:.0f} times below the criterion.
Rows H1 and H2 grant a Heron all-to-all connectivity it does not have and set eps1 = 0, and even
then reach only {ffmt(next(c for c in D['candidate_error_sets'] if c['name'].startswith('H1:'))['mean_f'])}
and {ffmt(next(c for c in D['candidate_error_sets'] if c['name'].startswith('H2:'))['mean_f'])}.

## 4. What would relax the requirement, and what is already spent

{md_table(["lever", "what it changes", "f at the declared inputs",
           "eps2 requirement for mean f >= 0.1", "status"], lever_rows)}

The f column is the {C['n_circuits_production_set']}-circuit mean in the virtual-rz row and the
single k = 1 circuit of the first B = 0 reference in the generator and ablation rows; the RZZ count
is identical across the set, so the two readings differ by under
{(1 - ph['at_declared_inputs']['min_over_mean']) * 100:.2f} %.  Plainly:

* **Connectivity: SPENT.**  The requirement in section 2 is already quoted at all-to-all,
  which is the floor ({L['connectivity']['all_to_all_cz']} CZ against
  {L['connectivity']['grid_best_cz']} on the best of {L['connectivity']['seeds']} grid seeds,
  {L['connectivity']['heavy_hex_best_cz']} heavy-hex, {L['connectivity']['line_cz']} on a line;
  `data/S2_escalation_experiments.json`).  There is nothing left to win here -- only to lose, by
  choosing a device that routes.
* **Virtual rz: UNSPENT, and cheap.**  It is a property of the platform, not of the circuits:
  {step['n_rz']['min']}..{step['n_rz']['max']} of the {step['n_1q']['min']}..{step['n_1q']['max']}
  one-qubit gates are rz.  It moves mean f from {L['virtual_rz']['mean_f_before']:.4f} to
  {L['virtual_rz']['mean_f_after']:.4f} and the two-qubit requirement from
  {fmt(L['virtual_rz']['eps2_requirement_before'])} to {fmt(L['virtual_rz']['eps2_requirement_after'])} -- a
  {(L['virtual_rz']['eps2_requirement_after'] / L['virtual_rz']['eps2_requirement_before'] - 1) * 100:.0f} %
  relaxation for free.  **It should be a line item in the specification.**
* **The fixed-angle generator: UNSPENT on an all-to-all device.**  Gate S2_fixed was stopped on
  cost, but the cost that stopped it was the *routed* heavy-hex count
  ({fa['cz_routed_heavy_hex_S2_fixed_json']} CZ against the old 500-CZ budget of manual Step 4.3).
  On an all-to-all device there is no routing: it compiles to
  {fa['counts_rzz_recomputed']['rzz']} RZZ against {int(step['rzz']['mean'])} for the exact
  generator, i.e. {(1 - fa['counts_rzz_recomputed']['rzz'] / step['rzz']['mean']) * 100:.0f} % fewer
  two-qubit gates, which relaxes the two-qubit requirement to
  {fmt(fa['eps2_required_for_mean_f_0.1'])} ({fmt(fa['eps2_required_virtual_rz'])} with virtual rz).
  Its price is that it is a *different generator*: per-term deviation from exp(-i theta H) is about
  1e-1 instead of 1e-14, and it is justified only by the S1 recall criterion, which it meets
  ({', '.join(f'{k.split(":")[0].strip()} {v}' for k, v in fa['recall_evidence'].items())}).
  Amendment 01 section 1(b) does not adopt it; this is an owner decision, and it is the single
  largest device-side relaxation available.
* **Term ablation: partly unspent.**  Dropping the interior-corner plaquette `plaq1` leaves
  {ab['variants']['no plaq1 (interior-corner plaquette)']['counts']['rzz']} RZZ and relaxes the
  requirement to
  {fmt(ab['variants']['no plaq1 (interior-corner plaquette)']['eps2_required_for_mean_f_0.1'])},
  at a measured recall of
  {ab['recall_at_f_0.1']['no plaq1 (interior-corner plaquette)']['B=0']:.3f} (B = 0) and
  {ab['recall_at_f_0.1']['no plaq1 (interior-corner plaquette)']['B=1']:.3f} (B = 1) against the S1
  criterion of 0.9 -- so it is still available.  Dropping *both* plaquettes gives
  {ab['variants']['no plaquettes']['counts']['rzz']} RZZ but recall
  {ab['recall_at_f_0.1']['no plaquettes']['B=1']:.3f} in B = 1, **below the S1 criterion**: that
  lever is spent.
* **Combined (fixed angles + no plaq1 + virtual rz): unmeasured.**  It would need only eps2 <=
  {fmt(cb['eps2_required_virtual_rz'])} at {cb['counts_rzz_recomputed']['rzz']} RZZ, but the recall
  of that *combination* has never been emulated -- each lever was measured alone.  Nothing may be
  claimed for it until that emulation is run (one S1-style run, about the cost of
  `scripts/s2_escalation_experiments.py`).
* **The shot quota is not a device lever.**  It is open item 5 of the amendment and is being
  decided separately; it changes what f the run can afford, not what f the device delivers.

## 5. Vendor-facing summary

{md_table(["what the device must deliver", "requirement", "at these circuit counts",
           "what this repository measures on today's Heron"], vendor_rows)}

Requirement in one paragraph, for a vendor who reads nothing else:

> 20 qubits; all-to-all connectivity (or a routing overhead of at most
> {V['connectivity']['max_routing_overhead_at_eps2_5e-4']:.2f}x if the two-qubit error is 5e-4, i.e.
> at most {V['connectivity']['max_two_qubit_gates_at_eps2_5e-4']} two-qubit gates in the circuit);
> a native two-qubit RZZ(theta) with a continuous angle; one
> circuit of {step['rzz']['mean']:.0f} two-qubit gates, {step['n_1q']['mean']:.0f} one-qubit gates
> and depth {V['depth']['mean']:.0f}, measured once at the end on all 20 qubits (no mid-circuit
> measurement, no reset).  Two-qubit error at most {fmt(V['two_qubit_error']['required'])}
> ({fmt(V['two_qubit_error']['required_with_virtual_rz'])} if rz is a virtual frame change);
> one-qubit error at most {fmt(V['one_qubit_error']['required_if_eps2_stays_at_declared'])} if the
> two-qubit error only reaches 1e-3, and no requirement on rz at all if rz is virtual; readout
> error at most {fmt(V['readout_error']['tolerable_at_the_R4_point'])} once the two-qubit error is
> 5e-4.  Any triple satisfying
> {ph['half_space']['weights']['2q']} eps2 + {ph['half_space']['weights']['1q']} eps1 + 20 eps_ro
> <= {ph['half_space']['budget_log']:.3f} qualifies.

The gap to today's hardware, from this repository's measurements only: the live {lh['backend']}
target of {lh['calibration_last_update']} (frozen patch, {lh['n_edges']} directed edges) gives a
mean CZ edge error of {lh['best_patch_mean_edge_error']:.3e} and a mean readout error of
{lh['best_patch_mean_readout_error']:.3e} on the patch its own layout preferred, against the
FakeFez snapshot values {V['today_heron_gap']['FakeFez_snapshot']['patch_mean_edge_error']:.3e} and
{V['today_heron_gap']['FakeFez_snapshot']['patch_mean_readout_error']:.3e} that the 2x2 row of the
amendment is built on.  The two-qubit error must therefore come down by a factor
{V['today_heron_gap']['two_qubit_error_factor_to_close']:.2f}
({V['today_heron_gap']['two_qubit_error_factor_to_close_virtual_rz']:.2f} with virtual rz) *and*
the routing overhead of {mp['routing_overhead_vs_all_to_all']:.2f}x must disappear, before a
Heron-class device meets the 2x3 requirement.  That is the whole content of the 2x3 device
question: it is not a marginal calibration improvement.

## 6. What this does not decide

* It does not adopt the fixed-angle generator or any term ablation (amendment 01 section 1(b);
  owner decision).  It prices them.
* It does not name a device, a vendor or a product, and asserts no vendor specification.
* It does not change gate S2D's status: S2D stays **FAIL** while the 2x3 device is unspecified,
  and `validation/S2.json`, `validation/S2D.json` and `validation/S2_fixed.json` are untouched.
* It does not touch open item 5 (the shot quota of manual Step 9.2).

## Provenance

Inputs read (values in `data/S2D_2x3_device_requirements.json` -> `sources`):
`validation/S2.json` (2x3 per-term and coarse-step CZ counts),
`validation/S2D.json` (declared inputs, the 44-circuit RZZ counts, the recorded f and the 2x2
FakeFez patch errors), `validation/S2_fixed.json` (the fixed-angle cost and recall),
`data/S2_escalation_experiments.json` (coupling-map and term ablations),
`validation/H0P_ibm_fez.json` (the live ibm_fez calibration of {lh['calibration_stamp']}, produced
by `gate_S2D.analyse_on_backend`).  The f model and the counts come from
`gate_S2D.analyse_rzz`; the inversion from `skqd.device_req`
({D.get('pytest', 'tests not run')}).  Counts used for the region:
{chk['region_counts_source']}.
"""


if __name__ == "__main__":
    sys.exit(main())
