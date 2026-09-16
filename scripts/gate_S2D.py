#!/usr/bin/env python3
"""
Gate S2D — device-resolved budgets for the EXACT structured circuits of gate S2
(prompts/12, owner decision of 2026-09-16: options (b) + (c) of prompts/11 together).

Circuit family: unchanged.  `CircuitFactory` default (angle_mode="exact",
structured_hopping=True), coarse steps k = 1..4 of every reference of both sectors --
the production set of manual Step 9.2.  Gate S2 keeps its recorded FAIL; this gate
replaces the fixed CZ numbers of manual Step 4.3 (250 / 500) by the physical condition
they were derived from (Step 4.4): the clean-shot fraction

    f = prod_{executed 2q gates} (1 - eps_gate) x prod_{measured qubits} (1 - eps_ro)

of one coarse-step circuit on the chosen device must be >= 0.1 -- the condition under
which gate S1 established recall >= 0.9 with the production shot budget.

What is measured
  a. 2x2 on a Heron-class device: transpile(qc, backend=FakeFez()/FakeTorino(),
     optimization_level=3, seed_transpiler=7); f from the per-edge CZ errors and the
     per-qubit readout errors of that CALIBRATION SNAPSHOT (a measurement of the
     snapshot, not a vendor specification).  The routed count on the ideal heavy-hex
     map must reproduce validation/S2.json.
  b. 2x3 on an all-to-all trapped-ion device: transpile(qc, basis_gates=
     ['rz','rx','ry','rzz'], coupling_map=None, optimization_level=3); f from the
     DECLARED INPUTS eps2, eps1, eps_ro (vendor-class specifications, recorded in the
     JSON under `assumed_inputs`).  The all-to-all CZ-basis count must reproduce S2.json.
  c. Shot budget from the manual's shot rule (skqd.skqd.shot_rule, eq. 5).
  d. Per-shot cost of the 2x3 noisy simulation in the RZZ basis (fixes the desktop job for S3).

Usage: python scripts/gate_S2D.py [--eps2 1e-3] [--eps1 1e-4] [--eps-ro 2e-3]
                                  [--p 1e-3] [--k 3] [--conf 0.95] [--level 3] [--seed 7]
                                  [--cost-shots 10] [--no-cost] [--no-tests] [--quick]
Expected runtime: about 6 minutes on the i7-8750H (CPU only), inside the 30-minute rule.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import poisson_lambda_star, shot_rule  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANUAL_SECTOR_BUDGET = 2e5          # manual Step 9.2
YIELD_FACTOR = 0.82                 # manual Step 4.4: accepted-shot yield ~ 0.82 f
F_MEAN_MIN, F_WORST_MIN = 0.1, 0.05
HEAVY_HEX_D = {2: 3, 3: 5}
G2 = 4.0
THROUGHPUTS = (100, 300, 1000)      # shots per minute, ILLUSTRATIVE (not device numbers)


# --------------------------------------------------------------------------- helpers
def s2_reference(lattice: str, key: str):
    """The k = 1 counts recorded by gate S2 (validation/S2.json) -- the reproduction check."""
    with open(os.path.join(ROOT, "validation", "S2.json")) as fh:
        d = json.load(fh)["data"]
    return int(d[lattice]["coarse_step"][key]["cz"])


def circuit_set(Lx: int):
    """The production circuit set of manual Step 9.2: references x coarse steps k = 1..4."""
    M = Model(Lx)
    F = CircuitFactory(M, G2)                      # exact structured circuits (the S2 default)
    out = []
    for twoB in (0, 2):
        dt = M.reference(G2, twoB).dt
        for r in references(M.basis, twoB):
            for k in (1, 2, 3, 4):
                out.append((twoB, r, k, F.coarse_step(r, k, dt)))
    return M, F, out


def analyse_on_backend(tq, backend):
    """f and the calibration numbers of the edges/qubits the transpiled circuit actually uses."""
    t = backend.target
    log_f, log_f_1q = 0.0, 0.0
    edges, meas, n_1q = {}, {}, 0
    for inst in tq.data:
        nm = inst.operation.name
        qs = tuple(tq.find_bit(q).index for q in inst.qubits)
        if nm == "cz":
            key = qs if qs in t["cz"] else qs[::-1]
            e = float(t["cz"][key].error)
            edges.setdefault(tuple(sorted(qs)), [0, e])[0] += 1
            log_f += np.log1p(-e)
        elif nm == "measure":
            e = float(t["measure"][(qs[0],)].error)
            meas[qs[0]] = e
            log_f += np.log1p(-e)
        elif nm in ("rz", "sx", "x", "id"):
            n_1q += 1
            props = t[nm].get((qs[0],)) if nm in t else None
            err = getattr(props, "error", None)
            if err:
                log_f_1q += np.log1p(-float(err))
    n_cz = sum(v[0] for v in edges.values())
    per_edge = [v[1] for v in edges.values()]
    per_gate = [v[1] for v in edges.values() for _ in range(v[0])]
    return {
        "cz": int(n_cz), "n_1q": int(n_1q), "f": float(np.exp(log_f)),
        "f_including_1q_errors": float(np.exp(log_f + log_f_1q)),
        "n_edges": len(edges), "mean_edge_error": float(np.mean(per_edge)),
        "max_edge_error": float(max(per_edge)), "mean_edge_error_per_gate": float(np.mean(per_gate)),
        "mean_readout_error": float(np.mean(list(meas.values()))),
        "max_readout_error": float(max(meas.values())),
        "measured_qubits": sorted(meas), "edges": {f"{a}-{b}": v[0] for (a, b), v in edges.items()},
    }


def analyse_rzz(tq, eps2, eps1, eps_ro, n_meas):
    n_rzz = int(tq.count_ops().get("rzz", 0))
    ops = dict(tq.count_ops())
    n_1q = int(sum(v for k, v in ops.items() if k in ("rz", "rx", "ry", "h", "x", "sx", "p", "u")))
    n_rz = int(ops.get("rz", 0))
    f = (1 - eps2) ** n_rzz * (1 - eps1) ** n_1q * (1 - eps_ro) ** n_meas
    f_vz = (1 - eps2) ** n_rzz * (1 - eps1) ** (n_1q - n_rz) * (1 - eps_ro) ** n_meas
    return {"rzz": n_rzz, "n_1q": n_1q, "n_rz": n_rz, "depth": int(tq.depth()),
            "f": float(f), "f_virtual_rz": float(f_vz),
            "f_2q": float((1 - eps2) ** n_rzz), "f_1q": float((1 - eps1) ** n_1q),
            "f_ro": float((1 - eps_ro) ** n_meas), "ops": ops}


def agg(entries, key="f"):
    v = [e[key] for e in entries]
    return {"mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eps2", type=float, default=1e-3, help="DECLARED two-qubit error of the all-to-all device")
    ap.add_argument("--eps1", type=float, default=1e-4, help="DECLARED one-qubit error")
    ap.add_argument("--eps-ro", type=float, default=2e-3, help="DECLARED readout error")
    ap.add_argument("--p", type=float, default=1e-3, help="ideal probability of the configuration to be seen")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--conf", type=float, default=0.95)
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cost-shots", type=int, default=10, help="noisy shots timed at 2x3")
    ap.add_argument("--no-cost", action="store_true")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--quick", action="store_true", help="k = 1 only (smoke test, not the gate)")
    args = ap.parse_args()
    t0 = time.time()
    from qiskit import transpile
    from qiskit.transpiler import CouplingMap
    from qiskit_ibm_runtime.fake_provider import FakeFez, FakeTorino

    from skqd import circuits_qiskit as cq

    R = GateResult("S2D", "Device-resolved budgets for the exact circuits: 2x2 on Heron, "
                          "2x3 on an all-to-all RZZ device, shot rule and S3 job size")
    lam = poisson_lambda_star(args.k, args.conf)
    data = {"assumed_inputs": {
        "eps2_two_qubit_all_to_all": args.eps2, "eps1_one_qubit_all_to_all": args.eps1,
        "eps_ro_readout_all_to_all": args.eps_ro, "p_configuration_probability": args.p,
        "k_min_counts": args.k, "confidence": args.conf, "lambda_star": float(lam),
        "yield_model": f"y = {YIELD_FACTOR} f (manual Step 4.4)",
        "note": ("eps2, eps1, eps_ro are vendor-class SPECIFICATIONS for the all-to-all trapped-ion "
                 "device, declared inputs of this gate, not measurements; p, k and the confidence are "
                 "the preregistered shot rule of manual Step 4.4.  The 2x2/Heron f is NOT in this "
                 "list: it is computed from the per-edge and per-qubit errors of a calibration "
                 "snapshot (FakeFez / FakeTorino)."),
        "calibration_snapshots": "qiskit_ibm_runtime.fake_provider FakeFez (Heron r2), FakeTorino (Heron r1)",
    }, "circuit_family": "exact structured circuits, CircuitFactory default (validation/S2.json)"}

    # ------------------------------------------------------------------ 2a: 2x2 on Heron
    M2, F2, set2 = circuit_set(2)
    if args.quick:
        set2 = [c for c in set2 if c[2] == 1]
    n2 = F2.n
    print(f"2x2: {len(set2)} circuits, {n2} qubits ({time.time() - t0:.0f} s)", flush=True)
    heron = {}
    for BK, bname in ((FakeFez, "FakeFez"), (FakeTorino, "FakeTorino")):
        backend = BK()
        per, layouts = [], []
        for twoB, r, k, gates in set2:
            qc = cq.ir_to_qiskit(gates, n2, measure=True)
            tq = transpile(qc, backend=backend, optimization_level=args.level, seed_transpiler=args.seed)
            a = analyse_on_backend(tq, backend)
            a.update(sector=f"B={twoB // 2}", reference=int(r), k=int(k))
            try:
                a["layout"] = [int(q) for q in tq.layout.final_index_layout()]
            except Exception:
                a["layout"] = sorted(a["measured_qubits"])
            layouts.append(tuple(sorted(a["layout"])))
            per.append(a)
        worst = min(per, key=lambda e: e["f"])
        best = max(per, key=lambda e: e["f"])
        patches = sorted({p for p in layouts})
        tgt = backend.target
        heron[bname] = {
            "backend_qubits": int(backend.num_qubits),
            "n_circuits": len(per), "f": agg(per, "f"), "cz": agg(per, "cz"), "n_1q": agg(per, "n_1q"),
            "f_including_1q_errors": agg(per, "f_including_1q_errors"),
            "worst_circuit": {kk: worst[kk] for kk in
                              ("sector", "reference", "k", "f", "cz", "mean_edge_error", "layout")},
            "best_circuit": {kk: best[kk] for kk in ("sector", "reference", "k", "f", "cz", "layout")},
            "k1_circuit": next(e for e in per if e["k"] == 1),
            "distinct_patches": [list(p) for p in patches],
            "patch": sorted(per[0]["layout"]),
            "patch_mean_edge_error": float(np.mean([e["mean_edge_error"] for e in per])),
            "patch_mean_edge_error_per_gate": float(np.mean([e["mean_edge_error_per_gate"] for e in per])),
            "patch_mean_readout_error": float(np.mean([e["mean_readout_error"] for e in per])),
            "snapshot_median_cz_error": float(np.median([p.error for p in tgt["cz"].values()])),
            "snapshot_median_readout_error": float(np.median(
                [tgt["measure"][(q,)].error for q in range(backend.num_qubits)])),
            "per_circuit": per,
        }
        print(f"  {bname}: mean f {heron[bname]['f']['mean']:.4f}, worst {heron[bname]['f']['min']:.4f}, "
              f"CZ {heron[bname]['cz']['mean']:.0f}, {time.time() - t0:.0f} s", flush=True)
    best_snap = max(heron, key=lambda b: heron[b]["f"]["mean"])
    # reproduction check: ideal heavy-hex routing of the k = 1 coarse step (gate S2's number)
    k1_gates = next(g for tb, r, k, g in set2 if k == 1)
    ideal = cq.transpile_counts(k1_gates, n2, coupling_map=CouplingMap.from_heavy_hex(HEAVY_HEX_D[2]),
                                optimization_level=args.level, seed=args.seed)["cz"]
    data["2x2"] = {"device": "Heron-class superconducting (heavy-hex, native CZ)",
                   "n_qubits": n2, "n_circuits": len(set2), "snapshots": heron,
                   "best_snapshot": best_snap,
                   "ideal_heavy_hex_cz_k1": int(ideal), "S2_heavy_hex_cz_k1": s2_reference("2x2", "routed")}

    # ------------------------------------------------------------------ 2b: 2x3 all-to-all RZZ
    M3, F3, set3 = circuit_set(3)
    if args.quick:
        set3 = [c for c in set3 if c[2] == 1]
    n3 = F3.n
    print(f"2x3: {len(set3)} circuits, {n3} qubits ({time.time() - t0:.0f} s)", flush=True)
    per3, tq_cost = [], None
    for twoB, r, k, gates in set3:
        qc = cq.ir_to_qiskit(gates, n3, measure=True)
        tq = transpile(qc, basis_gates=["rz", "rx", "ry", "rzz"], coupling_map=None,
                       optimization_level=args.level, seed_transpiler=args.seed)
        a = analyse_rzz(tq, args.eps2, args.eps1, args.eps_ro, n3)
        a.update(sector=f"B={twoB // 2}", reference=int(r), k=int(k))
        if tq_cost is None:
            tq_cost = tq
        per3.append(a)
    worst3 = min(per3, key=lambda e: e["f"])
    a2a = cq.transpile_counts(next(g for tb, r, k, g in set3 if k == 1), n3,
                              optimization_level=args.level, seed=args.seed)["cz"]
    data["2x3"] = {
        "device": "all-to-all trapped ion, native RZZ, declared two-qubit error eps2",
        "n_qubits": n3, "n_circuits": len(set3),
        "f": agg(per3, "f"), "f_virtual_rz": agg(per3, "f_virtual_rz"),
        "rzz": agg(per3, "rzz"), "n_1q": agg(per3, "n_1q"), "depth": agg(per3, "depth"),
        "f_factors_k1": {kk: per3[0][kk] for kk in ("f_2q", "f_1q", "f_ro", "rzz", "n_1q")},
        "worst_circuit": {kk: worst3[kk] for kk in ("sector", "reference", "k", "f", "rzz", "n_1q")},
        "all_to_all_cz_k1": int(a2a), "S2_all_to_all_cz_k1": s2_reference("2x3", "all_to_all"),
        "per_circuit": per3,
    }
    # eps2 that WOULD give mean f = 0.1 at the measured counts (derived, not a criterion)
    mr, m1 = data["2x3"]["rzz"]["mean"], data["2x3"]["n_1q"]["mean"]
    rest = (1 - args.eps1) ** m1 * (1 - args.eps_ro) ** n3
    data["2x3"]["eps2_required_for_f_0.1"] = float(1 - (F_MEAN_MIN / rest) ** (1.0 / mr)) if rest > F_MEAN_MIN else None
    print(f"  2x3: mean f {data['2x3']['f']['mean']:.4f}, RZZ {mr:.0f}, 1q {m1:.0f}, "
          f"{time.time() - t0:.0f} s", flush=True)

    # ------------------------------------------------------------------ 3: shot budget
    budget = {}
    for tag, per in (("2x3 / all-to-all", per3),
                     ("2x2 / Heron " + best_snap, heron[best_snap]["per_circuit"])):
        rows = {}
        for sec in sorted({e["sector"] for e in per}):
            es = [e for e in per if e["sector"] == sec]
            fm = float(np.mean([e["f"] for e in es]))
            y = YIELD_FACTOR * fm
            nc = shot_rule(args.p, y, args.k, args.conf)
            rows[sec] = {"n_circuits": len(es), "mean_f": fm, "yield": float(y),
                         "N_circuit": int(nc), "N_sector": int(nc * len(es)),
                         "manual_sector_budget": MANUAL_SECTOR_BUDGET,
                         "within_manual_budget": bool(nc * len(es) <= MANUAL_SECTOR_BUDGET)}
        budget[tag] = rows
    # what the manual's own example costs, for reference (f = 0.2, its design point)
    budget["manual design point f = 0.2 (manual eq. 5)"] = {
        "any sector": {"n_circuits": len(per3), "mean_f": 0.2, "yield": YIELD_FACTOR * 0.2,
                       "N_circuit": shot_rule(args.p, YIELD_FACTOR * 0.2, args.k, args.conf),
                       "N_sector": shot_rule(args.p, YIELD_FACTOR * 0.2, args.k, args.conf) * len(per3),
                       "manual_sector_budget": MANUAL_SECTOR_BUDGET,
                       "within_manual_budget": bool(
                           shot_rule(args.p, YIELD_FACTOR * 0.2, args.k, args.conf) * len(per3)
                           <= MANUAL_SECTOR_BUDGET)}}
    data["shot_budget"] = budget
    worst_sector = max((v["N_sector"] for v in budget["2x3 / all-to-all"].values()))
    data["device_time_illustrative"] = {
        "formula": "device time [min] = N_sector / throughput [shots per minute]",
        "label": "ILLUSTRATIVE: the throughputs below are round numbers, NOT device specifications",
        "table": {str(th): {sec: round(v["N_sector"] / th, 1)
                            for sec, v in budget["2x3 / all-to-all"].items()} for th in THROUGHPUTS},
    }

    # ------------------------------------------------------------------ 5: 2x3 per-shot cost
    if not args.no_cost:
        from qiskit_aer import AerSimulator
        from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
        nm = NoiseModel(basis_gates=["rz", "rx", "ry", "rzz"])
        nm.add_all_qubit_quantum_error(depolarizing_error(args.eps2, 2), ["rzz"])
        nm.add_all_qubit_quantum_error(depolarizing_error(args.eps1, 1), ["rz", "rx", "ry"])
        nm.add_all_qubit_readout_error(ReadoutError([[1 - args.eps_ro, args.eps_ro],
                                                     [args.eps_ro, 1 - args.eps_ro]]))
        sim = AerSimulator(noise_model=nm, method="statevector", device="CPU", seed_simulator=11)
        tc = time.time()
        sim.run(tq_cost, shots=args.cost_shots).result()
        dtc = time.time() - tc
        cps = dtc / args.cost_shots
        job = {sec: v["N_sector"] * cps / 3600.0 for sec, v in budget["2x3 / all-to-all"].items()}
        data["per_shot_cost_2x3"] = {
            "shots_timed": args.cost_shots, "seconds": float(dtc), "seconds_per_shot": float(cps),
            "simulator": "AerSimulator(method='statevector', CPU), depolarizing model of the "
                         "declared inputs applied to rzz, rz, rx, ry plus readout flips",
            "circuit": {"rzz": per3[0]["rzz"], "n_1q": per3[0]["n_1q"], "qubits": n3},
            "desktop_job_hours_per_sector_this_cpu": {s: float(v) for s, v in job.items()},
            "note": ("single-shot trajectory sampling on this laptop CPU; the intended executor is "
                     "Aer GPU with batched shots on the RTX 3070 desktop (the GTX 1060 Max-Q of this "
                     "laptop is compute capability 6.1 and no compatible qiskit-aer-gpu wheel exists "
                     "for qiskit 2.5.2, see prompts/LOG.md)"),
        }
        print(f"  2x3 noisy sampling: {cps:.2f} s/shot ({args.cost_shots} shots, {dtc:.0f} s)", flush=True)

    # ------------------------------------------------------------------ criteria
    hb = heron[best_snap]
    R.add(f"2x2/Heron ({best_snap} snapshot): mean clean-shot fraction f over the {len(set2)}-circuit set",
          round(hb["f"]["mean"], 4), f">= {F_MEAN_MIN}", hb["f"]["mean"] >= F_MEAN_MIN)
    R.add(f"2x2/Heron ({best_snap} snapshot): worst-circuit f", round(hb["f"]["min"], 4),
          f">= {F_WORST_MIN}", hb["f"]["min"] >= F_WORST_MIN)
    R.add(f"2x3/all-to-all at the declared eps2 = {args.eps2}: mean f over the {len(set3)}-circuit set",
          round(data["2x3"]["f"]["mean"], 4), f">= {F_MEAN_MIN}", data["2x3"]["f"]["mean"] >= F_MEAN_MIN)
    R.add("2x3/all-to-all: worst-circuit f", round(data["2x3"]["f"]["min"], 4),
          f">= {F_WORST_MIN}", data["2x3"]["f"]["min"] >= F_WORST_MIN)
    R.add("2x2: CZ of the k = 1 coarse step routed on the ideal heavy-hex d=3 map",
          int(ideal), f"= {data['2x2']['S2_heavy_hex_cz_k1']} (validation/S2.json)",
          ideal == data["2x2"]["S2_heavy_hex_cz_k1"])
    R.add("2x3: CZ of the k = 1 coarse step, all-to-all CZ basis",
          int(a2a), f"= {data['2x3']['S2_all_to_all_cz_k1']} (validation/S2.json)",
          a2a == data["2x3"]["S2_all_to_all_cz_k1"])
    R.add("2x3: shots per sector from the shot rule (worst sector)", int(worst_sector),
          f"<= {MANUAL_SECTOR_BUDGET:.0e} (manual Step 9.2)", worst_sector <= MANUAL_SECTOR_BUDGET)
    if not args.no_tests:
        tp = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT,
                            capture_output=True, text=True)
        line = tp.stdout.strip().splitlines()[-1] if tp.stdout.strip() else "no output"
        R.add("pytest -q tests", line, "all pass", tp.returncode == 0)
        data["pytest"] = line
    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report("S2D_device_budgets.md", report_text(args, R, data))
    print(R.criteria_table())
    return 0 if R.passed else 1


# --------------------------------------------------------------------------- report
def report_text(args, R, D):
    ai = D["assumed_inputs"]
    heron, best = D["2x2"]["snapshots"], D["2x2"]["best_snapshot"]
    hrows = [[b, h["backend_qubits"], h["n_circuits"], f"{h['cz']['mean']:.0f}", h["cz"]["min"],
              h["cz"]["max"], f"{h['f']['mean']:.4f}", f"{h['f']['min']:.4f}", f"{h['f']['max']:.4f}",
              f"{h['patch_mean_edge_error']:.2e}", f"{h['snapshot_median_cz_error']:.2e}",
              f"{h['patch_mean_readout_error']:.2e}", f"{h['f_including_1q_errors']['mean']:.4f}"]
             for b, h in heron.items()]
    patch_rows = [[b, len(h["distinct_patches"]), str(h["patch"]),
                   f"{h['patch_mean_edge_error']:.3e}", f"{h['patch_mean_edge_error_per_gate']:.3e}",
                   f"{h['snapshot_median_cz_error']:.3e}",
                   f"{h['patch_mean_readout_error']:.3e}", f"{h['snapshot_median_readout_error']:.3e}"]
                  for b, h in heron.items()]
    T = D["2x3"]
    t3rows = [["2x3 coarse step, RZZ basis, all-to-all", T["n_circuits"], f"{T['rzz']['mean']:.0f}",
               f"{T['n_1q']['mean']:.0f}", f"{T['depth']['mean']:.0f}", f"{T['f']['mean']:.4f}",
               f"{T['f']['min']:.4f}", f"{T['f_factors_k1']['f_2q']:.4f}",
               f"{T['f_factors_k1']['f_1q']:.4f}", f"{T['f_factors_k1']['f_ro']:.4f}",
               f"{T['f_virtual_rz']['mean']:.4f}"]]
    brows = []
    for tag, rows in D["shot_budget"].items():
        for sec, v in rows.items():
            brows.append([tag, sec, v["n_circuits"], f"{v['mean_f']:.4f}", f"{v['yield']:.4f}",
                          f"{v['N_circuit']:.0f}", f"{v['N_sector']:.3e}",
                          f"{v['manual_sector_budget']:.0e}", "yes" if v["within_manual_budget"] else "NO"])
    dt_tbl = D["device_time_illustrative"]["table"]
    drows = [[th] + [f"{dt_tbl[th][sec]:.0f}" for sec in sorted(dt_tbl[th])] for th in sorted(dt_tbl, key=int)]
    dhead = ["throughput (shots/min)"] + [f"{sec} (min)" for sec in sorted(dt_tbl[list(dt_tbl)[0]])]
    cost = D.get("per_shot_cost_2x3")
    cost_txt = ("(not measured in this run: --no-cost)" if cost is None else f"""
{cost['shots_timed']} noisy shots of one 2x3 coarse-step circuit ({cost['circuit']['rzz']} RZZ,
{cost['circuit']['n_1q']} one-qubit gates, {cost['circuit']['qubits']} qubits) took {cost['seconds']:.0f} s on this
laptop CPU: **{cost['seconds_per_shot']:.2f} s per shot** ({cost['simulator']}).  At the shot budget above, one
sector of the S3 device-model simulation is
{md_table(["sector", "hours on this laptop CPU (measured cost x N_sector)"],
          [[s, f"{v:.3e}"] for s, v in cost['desktop_job_hours_per_sector_this_cpu'].items()])}
{cost['note']}.""")
    return f"""# Gate S2D — device-resolved budgets for the exact circuits (2x2 Heron, 2x3 all-to-all RZZ)

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/gate_S2D.py`, optimization level {args.level},
seed {args.seed}.  {env_block()}  Runtime {R.runtime_s:.0f} s.

Owner decision of 2026-09-16 (prompts/12, options (b) + (c) of prompts/11): the circuit family stays the
**exact structured circuits of gate S2** (`{D['circuit_family']}`); 2x2 runs on a Heron-class device
(heavy-hex, native CZ) and 2x3 on an all-to-all trapped-ion device with native RZZ.  The fixed CZ numbers of
manual Step 4.3 (250 / 500) are replaced by the physical condition of Step 4.4 they were derived from:
the clean-shot fraction f of one coarse-step circuit must be >= {F_MEAN_MIN} (worst circuit >= {F_WORST_MIN}),
the condition under which gate S1 established recall >= 0.9 with the production shot budget.
Gate S2 keeps its recorded FAIL; `validation/S2.json` is untouched.

## Declared inputs (NOT measurements)

{md_table(["symbol", "value", "what it is"],
          [["eps2", ai["eps2_two_qubit_all_to_all"], "two-qubit (RZZ) error of the all-to-all device — vendor-class specification"],
           ["eps1", ai["eps1_one_qubit_all_to_all"], "one-qubit error of the all-to-all device — vendor-class specification"],
           ["eps_ro", ai["eps_ro_readout_all_to_all"], "readout error per qubit of the all-to-all device — vendor-class specification"],
           ["p", ai["p_configuration_probability"], "ideal probability of the configuration that must be seen (gate S1's 99.9 % support threshold)"],
           ["k", ai["k_min_counts"], "minimum number of times it must be seen (manual Step 4.4)"],
           ["confidence", ai["confidence"], "probability with which that must happen (manual Step 4.4)"],
           ["lambda*", f"{ai['lambda_star']:.6f}", "smallest Poisson mean with P(X >= k) >= confidence (skqd.skqd.poisson_lambda_star)"],
           ["yield model", ai["yield_model"], "accepted-shot yield of manual Step 4.4"]])}

The 2x2/Heron numbers below are **not** in this list: they are computed from the per-edge CZ errors and
per-qubit readout errors of the calibration snapshots {ai['calibration_snapshots']}.

## 2a. 2x2 on a Heron-class device ({D['2x2']['n_qubits']} qubits, {D['2x2']['n_circuits']} circuits = references x k = 1..4)

`transpile(qc, backend=<snapshot>, optimization_level={args.level}, seed_transpiler={args.seed})`; f is the
product of (1 - error) over the CZ gates actually executed on their physical edges and over the readout of
the measured physical qubits.

{md_table(["snapshot", "device qubits", "circuits", "CZ mean", "CZ min", "CZ max", "f mean", "f worst",
            "f best", "mean error of the used edges", "snapshot median CZ error", "mean readout error of the patch",
            "f mean incl. 1q errors"], hrows)}

Best snapshot: **{best}** (mean f {heron[best]['f']['mean']:.4f}).  The last column is a *diagnostic*, not the
criterion: the criterion's f follows manual Step 4.4 and counts CZ and readout only, while the transpiled
circuits also contain {heron[best]['n_1q']['mean']:.0f} one-qubit gates on average, whose snapshot errors reduce f further.

### The patch the transpiler chose

{md_table(["snapshot", "distinct patches over the circuit set", "physical qubits (first circuit)",
            "mean error over the used edges", "same, weighted by CZ count", "snapshot median CZ error",
            "mean readout error of the patch", "snapshot median readout error"], patch_rows)}

Reproduction check: the k = 1 coarse step routed on the **ideal** heavy-hex d = {HEAVY_HEX_D[2]} coupling map gives
{D['2x2']['ideal_heavy_hex_cz_k1']} CZ, against {D['2x2']['S2_heavy_hex_cz_k1']} in `validation/S2.json`.  The real
snapshots cost {heron[best]['cz']['mean']:.0f} CZ on average because their heavy-hex patch is not the ideal d = 3 tile.

## 2b. 2x3 on the all-to-all trapped-ion device ({D['2x3']['n_qubits']} qubits, {D['2x3']['n_circuits']} circuits)

`transpile(qc, basis_gates=['rz','rx','ry','rzz'], coupling_map=None, optimization_level={args.level})`.

{md_table(["circuit set", "circuits", "RZZ mean", "1q mean", "depth mean", "f mean", "f worst",
            "f factor: 2q (k=1)", "f factor: 1q (k=1)", "f factor: readout (k=1)",
            "f mean if rz are virtual"], t3rows)}

The last column is a *diagnostic*: on trapped-ion hardware the {D['2x3']['per_circuit'][0]['n_rz']} rz of the k = 1 circuit (of {T['f_factors_k1']['n_1q']} one-qubit gates) are frame
changes with no physical error; the criterion's f charges eps1 to every one-qubit gate, as declared.
Reproduction check: the same k = 1 circuit in the CZ basis all-to-all gives {D['2x3']['all_to_all_cz_k1']} CZ,
against {D['2x3']['S2_all_to_all_cz_k1']} in `validation/S2.json`.
Two-qubit error that would be needed for mean f = {F_MEAN_MIN} at these counts (derived, holding eps1 and eps_ro):
**{D['2x3']['eps2_required_for_f_0.1']:.2e}** instead of the declared {args.eps2:.0e}.

## 3. Shot budget (manual Step 4.4 / eq. 5, `skqd.skqd.shot_rule`)

N_circuit = ceil(lambda* / (p y)) with y = {YIELD_FACTOR} f; N_sector = N_circuit x (number of circuits).

{md_table(["circuit set / device", "sector", "circuits", "mean f", "yield y = 0.82 f",
            "N_circuit", "N_sector", "manual Step 9.2", "within budget"], brows)}

The last block is the manual's own design point (f = 0.2): eq. (5) already asks for
{D['shot_budget']['manual design point f = 0.2 (manual eq. 5)']['any sector']['N_circuit']:.0f} shots per circuit there, i.e.
{D['shot_budget']['manual design point f = 0.2 (manual eq. 5)']['any sector']['N_sector']:.2e} per sector over
{D['shot_budget']['manual design point f = 0.2 (manual eq. 5)']['any sector']['n_circuits']} circuits — so the 2x10^5 per-sector quota of Step 9.2 and eq. (5) at
p = {args.p:.0e} are inconsistent *in the manual itself*, independently of any device.  Neither p nor the
confidence was lowered here.

### Device time (ILLUSTRATIVE — the throughputs are round numbers, not device specifications)

{D['device_time_illustrative']['formula']}

{md_table(dhead, drows)}

## 5. Cost of the 2x3 noisy simulation (fixes the S3 desktop job)
{cost_txt}

## Criteria

{R.criteria_table()}

## Scope

Every number above is computed by `scripts/gate_S2D.py` and stored in `validation/S2D.json`; the reports and
`proposal/amendment_01_devices_and_budgets.md` are generated from that file.  The 2x2 numbers use two public
calibration snapshots, not a reservation on a specific device; the 2x3 numbers use declared vendor-class
inputs.  Nothing here changes the circuit family, `validation/S2.json`, or any preregistered threshold.
"""


if __name__ == "__main__":
    sys.exit(main())
