#!/usr/bin/env python3
"""
Gate K0_2x3_2x4 (prompts/25 Part A) -- the ibm_kingston verdict for 2x3 and 2x4 on a calibration
record, as a JSON: routed CZ count, gate-only f, idle-aware f and f with the XY4 gain measured at
2x2.  Zero QPU seconds (every live read is metadata).

  A1  record: the committed record of the H0_2x2 day (default) and, with --live, today's full
      record (saved under data/hardware/K0_prep/); every quantity on both, the verdict on the
      committed one, the live one beside it.
  A2  record statistics (cz_error over the calibrated keys, uncalibrated markers, qubit medians).
  A3  the 2x3 B = 0 ref0 k = 1 coarse step routed onto the kingston target built from the record
      (`backend_from_record(rec, FakeKingston())`, the cz keys carrying the uncalibrated marker
      1.0 removed from the target), optimization_level 3, seed_transpiler 0..7, fewest CZ kept.
  A4  f_ceiling_2q, f_gates_layout (analyse_on_backend, 1q errors included),
      f_gates_best_patch_bound; the ALAP schedule with explicit delays (as h0_2x2_circuits),
      S_idle on the record (echo T2 and the transferred ratio 0.174), f_idle_aware, and
      f_idle_aware_xy4 = min(f_gates_layout, f_idle_aware x R) with R from H0_ddtest T3 (a
      transfer from 2x2, not a 2x3 measurement).
  A5  2x4: ceilings and best-patch bounds from the committed counts (no re-routing here).
  A6  verdict fields (no criterion): meets_mean_0.1 / meets_worst_0.05, eps2 needed.

The routing and the f functions are imported by gate K1 (prompts/27 stage 0b), so the pilot's
circuits are routed exactly as this gate routes.

Usage: python scripts/gate_K0_2x3_2x4.py [--live | --live-record <json>] [--skip-tests]
"""
import argparse
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEVICE = "ibm_kingston"
COMMITTED_RECORD = os.path.join("data", "hardware", "H0_ddtest_prep", "ibm_kingston_full_20261002T1906Z.json")
K0_PREP = os.path.join("data", "hardware", "K0_prep")
G2 = 4.0
SEEDS = tuple(range(8))
UNCALIBRATED = 1.0                     # IBM's marker for an uncalibrated cz key
T2_RATIOS = {"echo": 1.0, "transferred_0.174": 0.174}   # prompts/21 / validation/S2D_idle.json fallback
F_MEAN_BAR, F_WORST_BAR = 0.1, 0.05
TOL = 1e-12
EXACT_TOL, LEAK_TOL = 1e-10, 1e-9      # the exactness bars of every submitted circuit (h0_kpilot_circuits AMP/LEAK_TOL)
# planner arithmetic on the committed record (reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md 2.2),
# quoted to the four significant figures the report prints
PLANNER_RECORD = {"min": 8.164e-4, "p10": 1.146e-3, "median": 1.804e-3, "n_calibrated": 342, "n_uncalibrated": 10}
PLANNER_SIG_TOL = 5e-4                 # relative: half a unit in the 4th significant figure
A2A_2X3_EXPECTED_SOURCE = ("validation/S2.json", "2x3", "coarse_step", "all_to_all", "cz")
COUNTS_2X4 = {
    "routed_fakefez": {"source": "validation/S2_2x4.json data.compile.compile_4_exact_routed_k1.circuits.B0_ref0_k1.maps"
                                 "['fakefez|measured']", "path": ("compile", "compile_4_exact_routed_k1", "circuits",
                                                                  "B0_ref0_k1", "maps", "fakefez|measured")},
    "all_to_all": {"source": "validation/S2_2x4.json data.schedule.schedule_4_exact.rows"
                             "['2x4|exact|B0_ref0_k1|all_to_all']",
                   "path": ("schedule", "schedule_4_exact", "rows", "2x4|exact|B0_ref0_k1|all_to_all")},
}

_MODEL = {}


def p(*parts):
    return os.path.join(ROOT, *parts)


def rel(path):
    return os.path.relpath(path, ROOT)


def load_json(path):
    import json
    with open(path if os.path.isabs(path) else p(path)) as fh:
        return json.load(fh)


def dump_json(obj, path):
    import json

    from skqd.report import _jsonable
    path = path if os.path.isabs(path) else p(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(_jsonable(obj), fh, indent=1)
    os.replace(tmp, path)
    return path


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


# --------------------------------------------------------------------------- pure (tested)
def record_stats(rec):
    """A2: cz_error statistics over the calibrated cz keys of a record, the uncalibrated
    markers, the qubit medians and the set of cz durations."""
    errs = [float(e["cz_error"]) for e in rec["edges"].values()
            if e.get("cz_error") is not None and float(e["cz_error"]) < UNCALIBRATED]
    n_unc = sum(1 for e in rec["edges"].values()
                if e.get("cz_error") is not None and float(e["cz_error"]) >= UNCALIBRATED)
    a = np.asarray(errs, dtype=float)

    def med(key):
        v = [float(q[key]) for q in rec["qubits"].values() if q.get(key) is not None]
        return float(np.median(v)) if v else None

    def qmin(key):
        v = [float(q[key]) for q in rec["qubits"].values() if q.get(key) is not None]
        return float(min(v)) if v else None

    best_key = min(((float(e["cz_error"]), k) for k, e in rec["edges"].items()
                    if e.get("cz_error") is not None and float(e["cz_error"]) < UNCALIBRATED))[1]
    return {"n_cz_keys": len(rec["edges"]), "n_calibrated": len(errs), "n_uncalibrated": int(n_unc),
            "uncalibrated_keys": sorted(k for k, e in rec["edges"].items()
                                        if e.get("cz_error") is not None and float(e["cz_error"]) >= UNCALIBRATED),
            "cz_error_min": float(a.min()), "cz_error_p10": float(np.percentile(a, 10)),
            "cz_error_median": float(np.median(a)), "cz_error_mean": float(a.mean()),
            "cz_error_min_key": best_key,
            "sx_error_median": med("sx_error"), "measure_error_median": med("measure_error"),
            "T1_s_median": med("T1_s"), "T2_s_median": med("T2_s"),
            "sx_error_min": qmin("sx_error"), "x_error_min": qmin("x_error"),
            "measure_error_min": qmin("measure_error"),
            "cz_duration_s_values": sorted({float(e["cz_duration_s"]) for e in rec["edges"].values()
                                            if e.get("cz_duration_s") is not None}),
            "percentile_method": "numpy.percentile, linear interpolation (numpy default)"}


def percentile_by_hand(values, q):
    """numpy's default 'linear' percentile, written out (an independent path for K0.2)."""
    v = sorted(float(x) for x in values)
    h = (len(v) - 1) * q / 100.0
    lo = int(math.floor(h))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (h - lo) * (v[hi] - v[lo])


def f_ceiling_2q(eps2_min, n_cz):
    """(1 - eps2_min)^n_cz: the bound no DD / schedule / patch choice can beat."""
    return float((1.0 - float(eps2_min)) ** int(n_cz))


def f_best_patch_bound(eps2_min, eps1_min, eps_ro_min, n_cz, n_1q, n_meas):
    """Every gate on the best element of the record: an upper bound on any patch selection."""
    return float((1.0 - eps2_min) ** int(n_cz) * (1.0 - eps1_min) ** int(n_1q) * (1.0 - eps_ro_min) ** int(n_meas))


def eps2_needed(f_target, n_cz):
    """(-ln f_target / n_cz, the exact 1 - f_target^(1/n_cz))."""
    return float(-math.log(f_target) / n_cz), float(1.0 - f_target ** (1.0 / n_cz))


def xy4_capped(f_gates, f_idle, R):
    """f_idle_aware_xy4 = min(f_gates, f_idle x R): the 2x2 XY4 gain on the idle part, capped
    by the gate-only value (the DD ceiling)."""
    return float(min(float(f_gates), float(f_idle) * float(R)))


def bars(f):
    return {"meets_mean_0.1": bool(f >= F_MEAN_BAR), "meets_worst_0.05": bool(f >= F_WORST_BAR)}


def uncalibrated_pairs(rec):
    return {tuple(sorted(int(x) for x in e["target_key"])) for e in rec["edges"].values()
            if e.get("cz_error") is not None and float(e["cz_error"]) >= UNCALIBRATED}


# --------------------------------------------------------------------------- circuits
def model_2x3():
    if "M" not in _MODEL:
        from skqd.circuits_ir import CircuitFactory
        from skqd.codec import Codec
        from skqd.exact import Model
        M = Model(3)
        _MODEL["M"] = M
        _MODEL["F"] = CircuitFactory(M, G2)
        _MODEL["n"] = Codec(M.basis).n_qubits
    return _MODEL["M"], _MODEL["F"], _MODEL["n"]


def circuit_2x3(twoB, ref, k, measure=True):
    """The signed 2x3 coarse step of `gate_S2D.circuit_set(3)` for one (sector, reference, k),
    built alone (same factory, same dt) -> (qiskit circuit, IR gates, n, dt)."""
    from skqd import circuits_qiskit as cq
    M, F, n = model_2x3()
    dt = M.reference(G2, twoB).dt
    gates = F.coarse_step(int(ref), int(k), dt)
    return cq.ir_to_qiskit(gates, n, measure=measure), gates, n, float(dt)


def references_2x3(twoB):
    from skqd.krylov import references
    M, _F, _n = model_2x3()
    return [int(r) for r in references(M.basis, twoB)]


def kingston_backend(rec):
    """(backend carrying the record's numbers, info) on the FakeKingston coupling map."""
    from h0_backends import backend_from_record
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    return backend_from_record(rec, base=FakeKingston(), strict=True)


def routing_target(target, bad_pairs):
    """A copy of `target` without the cz keys of `bad_pairs` (undirected) -- the live coupling
    map minus the uncalibrated edges.  Control-flow entries are not copied (none is used)."""
    from qiskit.transpiler import Target
    new = Target(description=target.description, num_qubits=target.num_qubits, dt=target.dt,
                 granularity=target.granularity, min_length=target.min_length,
                 pulse_alignment=target.pulse_alignment, acquire_alignment=target.acquire_alignment,
                 qubit_properties=target.qubit_properties,
                 concurrent_measurements=target.concurrent_measurements)
    removed = 0
    for name in target.operation_names:
        if name in ("if_else", "while_loop", "for_loop", "switch_case"):
            continue
        props = {}
        for qargs, pr in target[name].items():
            if name == "cz" and qargs is not None and tuple(sorted(qargs)) in bad_pairs:
                removed += 1
                continue
            props[qargs] = pr
        new.add_instruction(target.operation_from_name(name), props, name=name)
    return new, removed


PEEPHOLE = "TwoQubitPeepholeOptimization"
VARIANTS = ("L3", "L3_peephole_replaced")
VARIANT_TEXT = {
    "L3": "qiskit level-3 preset pass manager on the target (= transpile(qc, target, optimization_level=3, seed))",
    "L3_peephole_replaced": ("the level-3 preset with TwoQubitPeepholeOptimization replaced by ConsolidateBlocks + "
                             "UnitarySynthesis (approximation_degree 1.0) in the optimization loop"),
}
ROUTE_RULE = ("transpile with each variant in order (L3 first) for seeds 0..7; among the seeds of the first variant that "
              "has any EXACT circuit (max |dpsi| < 1e-10 up to a global phase against the exact Krylov state, leakage "
              "< 1e-9), keep the fewest CZ (ties: the lower seed).  Exactness is checked in increasing CZ order and stops "
              "at the first exact seed.  Measured reason (2026-10-05, qiskit 2.5.2): the level-3 optimization loop's "
              "TwoQubitPeepholeOptimization is not exact on routed 2x3 circuits at approximation_degree 1.0 (B0_ref117_k1, "
              "seed 6: max |dpsi| 1.6e-5, leakage 6e-9), so the fewest-CZ seed alone can fail the exactness bar of every "
              "submitted circuit; the plain fewest-CZ level-3 count is recorded beside the chosen one")


def pass_manager(target, seed, variant="L3"):
    from qiskit.passmanager.flow_controllers import DoWhileController
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import ConsolidateBlocks, UnitarySynthesis
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    pm = generate_preset_pass_manager(optimization_level=3, target=target, seed_transpiler=int(seed))
    if variant == "L3":
        return pm
    if variant != "L3_peephole_replaced":
        raise ValueError(variant)
    new, replaced = [], 0
    for t in pm.optimization.to_flow_controller().tasks:
        if isinstance(t, DoWhileController):
            tasks = []
            for x in t.tasks:
                if type(x).__name__ == PEEPHOLE:
                    tasks += [ConsolidateBlocks(target=target, approximation_degree=1.0),
                              UnitarySynthesis(target=target, approximation_degree=1.0)]
                    replaced += 1
                else:
                    tasks.append(x)
            t = DoWhileController(tasks, do_while=t.do_while)
        new.append(t)
    if replaced != 1:
        raise SystemExit(f"expected one {PEEPHOLE} in the level-3 optimization loop, found {replaced}")
    pm.optimization = PassManager(new)
    return pm


def route(qc, target, ex=None, seeds=SEEDS, log=None):
    """A3: level-3 routing onto `target`, seeds 0..7, the fewest-CZ EXACT circuit (ROUTE_RULE).

    Returns (circuit, info) with info = {chosen, variant, seed, per_seed, plain_l3_fewest_cz, rule}.
    With `ex=None` no exactness is checked and the plain fewest-CZ level-3 seed is returned."""
    from skqd.hardware import transpiled_layout
    n = qc.num_clbits or qc.num_qubits
    table, circs = {}, {}
    chosen = None
    for variant in VARIANTS:
        for s in seeds:
            t0 = time.time()
            tq = pass_manager(target, s, variant).run(qc)
            ops = {k: int(v) for k, v in tq.count_ops().items()}
            lay = transpiled_layout(tq, n)
            key = f"{variant}|{s}"
            circs[key] = tq
            table[key] = {"variant": variant, "seed": int(s), "cz": ops.get("cz", 0),
                          "n_1q": ops.get("sx", 0) + ops.get("x", 0), "n_rz": ops.get("rz", 0), "ops": ops,
                          "depth": int(tq.depth()), "physical_qubits": lay["active_physical"],
                          "logical_to_physical": lay["logical_to_physical"],
                          "measurement_consistent": lay["measurement_consistent"], "transpile_s": time.time() - t0,
                          "exactness": None}
        if ex is None:
            break
        order = sorted((table[f"{variant}|{s}"]["cz"], int(s)) for s in seeds)
        for _cz, s in order:
            key = f"{variant}|{s}"
            r, _psi = circuit_exactness(circs[key], table[key]["logical_to_physical"], ex, phase_align=True)
            table[key]["exactness"] = {k: r[k] for k in ("max_abs_delta_up_to_phase", "max_abs_delta_raw_phase",
                                                          "leakage", "measurement_consistent", "n_active", "ok")}
            if log:
                log(f"    {key}: cz {table[key]['cz']}, |dpsi| {r['max_abs_delta_up_to_phase']:.1e}, leak "
                    f"{r['leakage']:.1e} -> {'exact' if r['ok'] else 'NOT exact'}")
            if r["ok"]:
                chosen = key
                break
        if chosen:
            break
    l3 = sorted((v["cz"], v["seed"]) for k, v in table.items() if v["variant"] == "L3")
    plain = f"L3|{l3[0][1]}"
    if ex is None:
        chosen = plain
    if chosen is None:
        raise SystemExit("no routed circuit passes the exactness bar in any variant (STOP: the circuit cannot be submitted)")
    info = {"chosen": chosen, "variant": table[chosen]["variant"], "seed": table[chosen]["seed"],
            "per_seed": table, "plain_l3_fewest_cz": {"key": plain, "cz": table[plain]["cz"],
                                                      "exactness": table[plain]["exactness"]},
            "rule": ROUTE_RULE if ex is not None else "fewest CZ over the level-3 seeds (no exactness check)",
            "variants": {v: VARIANT_TEXT[v] for v in VARIANTS}}
    return circs[chosen], info


# --------------------------------------------------------------------------- 2x3 exact states
_PHYS = {}


def physics():
    if not _PHYS:
        from skqd.codec import Codec
        from skqd.exact import mass_default
        from skqd.krylov import term_groups
        from skqd.reference_sim import CodewordEmbedding
        M, F, n = model_2x3()
        _PHYS.update(M=M, F=F, n=n, codec=Codec(M.basis), emb=CodewordEmbedding(M),
                     groups=term_groups(M.terms, G2, mass_default(G2)))
    return _PHYS


def exact_coarse(twoB, ref, k=1):
    """The exact Krylov state exp(-i k dt H_gamma)... |ref> in the signed group order (`krylov.coarse_states`,
    the state gate S2 checks the circuits against) and its sector distribution."""
    from skqd.krylov import basis_vector, coarse_states
    P = physics()
    M = P["M"]
    sec = M.reference(G2, twoB)
    dt = float(sec.dt)
    psi = coarse_states(P["groups"], basis_vector(M.basis.dim, int(ref)), dt, k)[k]
    idx = np.asarray(sec.indices, dtype=int)
    prob = np.abs(psi) ** 2
    pp = prob[idx]
    mass = float(pp.sum())
    pos = {int(b): i for i, b in enumerate(idx)}
    bits = tuple(int(x) for x in P["codec"].encode(M.basis.labels[int(ref)]))
    return {"psi": psi, "dt": dt, "theta": k * dt, "dim": int(len(idx)), "sector_mass": mass,
            "p_reference": float(pp[pos[int(ref)]] / mass), "p_reference_unnormalised": float(pp[pos[int(ref)]]),
            "reference_bits": list(bits), "reference_int": int(sum(b << q for q, b in enumerate(bits))),
            "sector_indices": [int(b) for b in idx]}


def logical_state(circ, final, global_phase=None):
    """Noiseless statevector of a physical (156-qubit register) circuit compacted onto its active
    qubits (Aer statevector, double precision), in logical order (bit i = logical qubit i, carried at
    the end by physical final[i]); ancillas must be back in |0> (else: missing norm = leakage)."""
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    n = len(final)
    active = sorted({circ.find_bit(q).index for inst in circ.data for q in inst.qubits
                     if inst.operation.name not in ("barrier", "delay", "measure")})
    phys = sorted(set(active) | set(final))
    pos = {q: i for i, q in enumerate(phys)}
    cc = QuantumCircuit(len(phys))
    cc.global_phase = circ.global_phase if global_phase is None else global_phase
    for inst in circ.data:
        if inst.operation.name in ("measure", "barrier", "delay"):
            continue
        cc.append(inst.operation, [pos[circ.find_bit(q).index] for q in inst.qubits])
    cc.save_statevector()
    sim = AerSimulator(method="statevector", precision="double")
    psi = np.asarray(sim.run(transpile(cc, sim, optimization_level=0)).result().get_statevector(), dtype=complex)
    idx = np.arange(psi.size, dtype=np.int64)
    keep = np.ones(psi.size, dtype=bool)
    fs = set(final)
    for q in phys:
        if q not in fs:
            keep &= ((idx >> pos[q]) & 1) == 0
    li = np.zeros(psi.size, dtype=np.int64)
    for i in range(n):
        li |= ((idx >> pos[final[i]]) & 1) << i
    out = np.zeros(2 ** n, dtype=complex)
    out[li[keep]] = psi[keep]
    return out, {"n_active": len(active), "n_simulated": len(phys)}


def circuit_exactness(circ, final, ex, phase_align=True, global_phase=None, psi=None):
    """Max |amplitude difference| on the codewords against the exact Krylov state (raw and up to a
    global phase), leakage out of the codeword space, measurement map = the final layout.  `psi`: a
    logical state already computed for this circuit (logical_state), to avoid a second simulation."""
    P = physics()
    if psi is None:
        psi, info = logical_state(circ, final, global_phase)
    else:
        psi, info = psi
    proj = P["emb"].project(psi)
    exact = ex["psi"]
    raw = float(np.max(np.abs(proj - exact)))
    ov = complex(np.vdot(exact, proj))
    dev = float(np.max(np.abs(proj * np.exp(-1j * np.angle(ov)) - exact)))
    leak = float(P["emb"].leakage(psi))
    mm = {}
    for inst in circ.data:
        if inst.operation.name == "measure":
            mm[int(circ.find_bit(inst.clbits[0]).index)] = int(circ.find_bit(inst.qubits[0]).index)
    cons = (not mm) or (len(mm) == len(final) and all(mm.get(i) == final[i] for i in range(len(final))))
    use = dev if phase_align else raw
    return {"max_abs_delta": use, "max_abs_delta_raw_phase": raw, "max_abs_delta_up_to_phase": dev,
            "phase_aligned": bool(phase_align), "overlap_abs": abs(ov), "leakage": leak,
            "measurement_consistent": bool(cons), "n_active": info["n_active"],
            "ok": bool(use < EXACT_TOL and leak < LEAK_TOL and cons)}, psi


def per_qubit_order(circ, drop=("delay", "barrier")):
    """{qubit: [(name, params)]} in circuit order (what a schedule must not change)."""
    out = {}
    for inst in circ.data:
        nm = inst.operation.name
        if nm in drop:
            continue
        key = (nm, tuple(round(float(x), 15) for x in getattr(inst.operation, "params", []) or []
                         if isinstance(x, (int, float))),
               tuple(circ.find_bit(q).index for q in inst.qubits))
        for q in inst.qubits:
            out.setdefault(circ.find_bit(q).index, []).append(key)
    return out


def alap(tq, backend, rec):
    """The ALAP schedule with explicit delays, exactly as `h0_kpilot_circuits` / `h0_2x2_circuits`
    build it (gate_S2D_levers.scheduled + strip_register_delays), and the K0.4 checks."""
    import gate_S2D_levers as G
    import h0_kpilot_circuits as KP
    from h0_qpu_time import circuit_duration_s

    from skqd import idle
    sched_full, sinfo = G.scheduled(tq, backend, "alap")
    sched, nrem = KP.strip_register_delays(sched_full)
    sinfo["idle_register_delays_removed"] = nrem
    tgt = backend.target
    d_sched = circuit_duration_s(sched, tgt.durations(), tgt)
    asap = idle.schedule_asap(tq, rec)
    moved = per_qubit_order(tq) != per_qubit_order(sched)
    return sched, {"schedule_info": sinfo, "scheduled_duration_s": d_sched,
                   "unscheduled_T_total_s": asap["T_total_s"], "unscheduled_T_s": asap["T_s"],
                   "duration_delta_s": abs(d_sched - asap["T_total_s"]),
                   "non_delay_ops_moved": bool(moved),
                   "k0_4_ok": bool((not moved) and abs(d_sched - asap["T_total_s"]) <= TOL)}


def idle_terms(sched, rec, f_gates, R, R95):
    """S_idle on the explicit ALAP delays (leading windows excluded, as C7 of S2D_levers) at
    each T2 end; f_idle_aware and the capped XY4 transfer."""
    import gate_S2D_levers as G

    from skqd import idle
    dsch = G.delay_schedule(sched, rec, include_leading=False)
    out = {"windows": {"n_windows": int(sum(len(v["windows_s"]) for v in dsch["per_qubit"].values())),
                       "idle_s_total": float(sum(v["idle_s"] for v in dsch["per_qubit"].values())),
                       "active": dsch["active"]}}
    for lab, r in T2_RATIOS.items():
        t2 = G.t2_scaled(rec, dsch["active"], r)
        _pq, tot = idle.idle_budget(dsch, rec, t2_s=t2)
        S = tot["S_T1"] + tot["S_T2"]
        fi = float(f_gates) * math.exp(-S)
        out[lab] = {"t2_ratio": r, "S_T1": tot["S_T1"], "S_T2": tot["S_T2"], "S_idle": S,
                    "f_idle_aware": fi,
                    "f_idle_aware_xy4": xy4_capped(f_gates, fi, R),
                    "f_idle_aware_xy4_95": [xy4_capped(f_gates, fi, R95[0]), xy4_capped(f_gates, fi, R95[1])],
                    "xy4_cap_binding": bool(fi * R >= f_gates)}
    return out


def xy4_gain():
    d = load_json(p("validation", "H0_ddtest.json"))["data"]["decision"]["cells"]["T3"]
    return float(d["R"]), [float(x) for x in d["R_95"]], "validation/H0_ddtest.json data.decision.cells.T3"


def evaluate_2x3(rec, label, twoB=0, ref=None, k=1, seeds=SEEDS, log=print):
    """A3 + A4 on one record -> (data block, best routed circuit, scheduled circuit, backend)."""
    from gate_S2D import analyse_on_backend
    t0 = time.time()
    if ref is None:
        ref = references_2x3(twoB)[0]
    qc, _gates, n, dt = circuit_2x3(twoB, ref, k)
    ex = exact_coarse(twoB, ref, k)
    base, binfo = kingston_backend(rec)
    bad = uncalibrated_pairs(rec)
    tgt, removed = routing_target(base.target, bad)
    tq, rinfo = route(qc, tgt, ex=ex, seeds=seeds, log=log)
    seed, table, chosen = rinfo["seed"], rinfo["per_seed"], rinfo["chosen"]
    st = record_stats(rec)
    a = analyse_on_backend(tq, base)
    ops = {kk: int(v) for kk, v in tq.count_ops().items()}
    n_cz, n_1q, n_meas = ops.get("cz", 0), ops.get("sx", 0) + ops.get("x", 0), ops.get("measure", 0)
    eps1_min = min(st["sx_error_min"], st["x_error_min"])
    ceil = f_ceiling_2q(st["cz_error_min"], n_cz)
    bound = f_best_patch_bound(st["cz_error_min"], eps1_min, st["measure_error_min"], n_cz, n_1q, n_meas)
    sched, sch = alap(tq, base, rec)
    R, R95, Rsrc = xy4_gain()
    idle_block = idle_terms(sched, rec, a["f_including_1q_errors"], R, R95)
    e_need, e_need_exact = eps2_needed(F_WORST_BAR, n_cz)
    e_need_01, _ = eps2_needed(F_MEAN_BAR, n_cz)
    block = {
        "record_label": label, "record_fingerprint": rec["fingerprint"],
        "record_last_update_date": rec.get("last_update_date"),
        "circuit": {"lattice": "2x3", "twoB": int(twoB), "reference": int(ref), "k": int(k), "dt": dt,
                    "id": f"B{twoB // 2}_ref{int(ref):02d}_k{int(k)}", "n_logical_qubits": n},
        "routing": {"target": "backend_from_record(record, FakeKingston()) minus the uncalibrated cz keys",
                    "cz_keys_removed": removed, "uncalibrated_pairs": sorted(map(list, bad)),
                    "optimization_level": 3, "seeds": list(seeds), **rinfo, "best_seed": seed},
        "n_cz": n_cz, "n_1q": n_1q, "n_rz": ops.get("rz", 0), "n_meas": n_meas, "ops": ops,
        "depth": int(tq.depth()), "physical_qubits": table[chosen]["physical_qubits"],
        "n_active_qubits": len(table[chosen]["physical_qubits"]),
        "exactness": table[chosen]["exactness"],
        "f_ceiling_2q": ceil,
        "f_ceiling_2q_formula": "(1 - eps2_min)^n_cz, eps2_min = the record's best calibrated cz key",
        "eps2_min": st["cz_error_min"], "eps1_min": eps1_min, "eps_ro_min": st["measure_error_min"],
        "f_gates_layout": a["f_including_1q_errors"],
        "f_gates_layout_formula": ("gate_S2D.analyse_on_backend(tq, backend_from_record(record)): prod over the "
                                   "circuit's cz (per key), sx/x (per qubit) and measure (per qubit) of (1 - error)"),
        "f_gates_layout_cz_and_readout_only": a["f"],
        "layout_mean_edge_error": a["mean_edge_error_per_gate"], "layout_mean_readout_error": a["mean_readout_error"],
        "f_gates_best_patch_bound": bound,
        "f_gates_best_patch_bound_formula": "(1-eps2_min)^n_cz (1-eps1_min)^n_1q (1-eps_ro_min)^n_meas, n_1q = sx + x",
        "schedule": sch, "idle": idle_block,
        "xy4_gain": {"R": R, "R_95": R95, "source": Rsrc,
                     "label": ("a TRANSFER of the 2x2-measured XY4 gain (cell T3, client XY4 in windows >= 1.024 us) "
                               "applied multiplicatively to the idle part and capped by the gate-only value -- "
                               "not a 2x3 measurement")},
        "eps2_needed_for_f_0.05_nothing_else_wrong": e_need,
        "eps2_needed_for_f_0.05_exact": e_need_exact,
        "eps2_needed_for_f_0.1_nothing_else_wrong": e_need_01,
        "best_edge_misses_by_factor": st["cz_error_min"] / e_need,
        "verdict": {"f_ceiling_2q": bars(ceil), "f_gates_layout": bars(a["f_including_1q_errors"]),
                    "f_gates_best_patch_bound": bars(bound),
                    **{f"f_idle_aware[{lab}]": bars(idle_block[lab]["f_idle_aware"]) for lab in T2_RATIOS},
                    **{f"f_idle_aware_xy4[{lab}]": bars(idle_block[lab]["f_idle_aware_xy4"]) for lab in T2_RATIOS}},
        "runtime_s": time.time() - t0,
    }
    log(f"[{label}] 2x3 {block['circuit']['id']}: {chosen} cz {n_cz} (plain L3 fewest "
        f"{rinfo['plain_l3_fewest_cz']['cz']}), 1q {n_1q}, active {block['n_active_qubits']}, ceiling {ceil:.3e}, "
        f"f_gates_layout {a['f_including_1q_errors']:.3e}, bound {bound:.3e}, T {sch['scheduled_duration_s'] * 1e6:.1f} us, "
        f"f_idle echo {idle_block['echo']['f_idle_aware']:.3e} / 0.174 {idle_block['transferred_0.174']['f_idle_aware']:.3e} "
        f"({time.time() - t0:.0f} s)", flush=True)
    return block, tq, sched, base


def counts_2x4():
    d = load_json(p("validation", "S2_2x4.json"))["data"]
    out = {}
    for lab, spec in COUNTS_2X4.items():
        x = d
        for k in spec["path"]:
            x = x[k]
        ops = x["ops"]
        out[lab] = {"n_cz": int(ops.get("cz", x.get("n_2q", 0))),
                    "n_1q": int(ops.get("sx", 0) + ops.get("x", 0)),
                    "n_meas": int(x.get("n_measure", ops.get("measure", 0)) or 28),
                    "source": spec["source"]}
    return out


def evaluate_2x4(st):
    eps1_min = min(st["sx_error_min"], st["x_error_min"])
    out = {}
    for lab, c in counts_2x4().items():
        ceil = f_ceiling_2q(st["cz_error_min"], c["n_cz"])
        bound = f_best_patch_bound(st["cz_error_min"], eps1_min, st["measure_error_min"], c["n_cz"], c["n_1q"],
                                   c["n_meas"])
        e, ex = eps2_needed(F_WORST_BAR, c["n_cz"])
        out[lab] = {**c, "f_ceiling_2q": ceil, "f_gates_best_patch_bound": bound,
                    "log10_f_ceiling_2q": c["n_cz"] * math.log10(1.0 - st["cz_error_min"]),
                    "eps2_needed_for_f_0.05_nothing_else_wrong": e, "eps2_needed_for_f_0.05_exact": ex,
                    "best_edge_misses_by_factor": st["cz_error_min"] / e,
                    "f_gates_layout": None, "f_idle_aware": None,
                    "not_computed": ("no 2x4 circuit is re-routed on the laptop (prompts/25 A5); the 2x4 transpile is "
                                     "recorded in validation/S2_2x4.json"),
                    "verdict": {"f_ceiling_2q": bars(ceil), "f_gates_best_patch_bound": bars(bound)}}
    return out


# --------------------------------------------------------------------------- gate
def fetch_live():
    """Today's full-device record (metadata, 0 QPU s), as `h0_device_survey.full_device_record` builds it,
    except that the edge list falls back to the configuration's coupling map when the live target carries
    no cz entries (then every cz leaf is a missing error and the record is unusable -- recorded, not hidden)."""
    from h0_backends import fresh_calibration, resolve_backend
    b = resolve_backend(DEVICE)
    cm, src = b.coupling_map, "backend.coupling_map"
    if cm is None:
        cm = b.configuration().coupling_map
        src = "backend.configuration().coupling_map (backend.coupling_map is None: the live target has no cz entries)"
    edges = sorted({(int(a), int(c)) for a, c in cm})
    rec = fresh_calibration(b, list(range(int(b.num_qubits))), edges)
    rec["survey"] = {"kind": "live device target, read-only metadata (0 QPU seconds)", "requested_name": DEVICE,
                     "n_qubits_surveyed": int(b.num_qubits), "n_edges_surveyed": len(edges), "edge_source": src}
    path = p(K0_PREP, f"{DEVICE}_full_{rec['stamp']}.json")
    if os.path.exists(path) and load_json(path)["fingerprint"] != rec["fingerprint"]:
        path = p(K0_PREP, f"{DEVICE}_full_{rec['stamp']}_{rec['fingerprint'][:8]}.json")
    if not os.path.exists(path):
        dump_json(rec, path)
    return rec, path


def a2a_2x3_count():
    from qiskit import transpile
    qc, _g, _n, _dt = circuit_2x3(0, references_2x3(0)[0], 1)
    tq = transpile(qc, basis_gates=["rz", "sx", "x", "cz"], optimization_level=3, seed_transpiler=0)
    d = load_json(p(A2A_2X3_EXPECTED_SOURCE[0]))["data"]
    exp = d["2x3"]["coarse_step"]["all_to_all"]["cz"]
    return int(tq.count_ops().get("cz", 0)), int(exp)


def main():
    from skqd.report import GateResult, write_report
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="also fetch today's full record (metadata, 0 QPU s)")
    ap.add_argument("--live-record", default=None, help="use this saved full record as the live one")
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    R_ = GateResult("K0_2x3_2x4", "ibm_kingston readiness of 2x3 and 2x4 on a calibration record: routed CZ, "
                                  "gate-only, idle-aware and XY4-transfer f (prompts/25 Part A)")
    recs = {"committed": (load_json(p(COMMITTED_RECORD)), COMMITTED_RECORD)}
    if args.live_record:
        recs["live"] = (load_json(args.live_record), rel(p(args.live_record)) if not os.path.isabs(args.live_record)
                        else rel(args.live_record))
    elif args.live:
        lr, lp = fetch_live()
        recs["live"] = (lr, rel(lp))
    data = {"what_pass_means": ("the counts, statistics and formulas are reproduced and self-consistent; the verdict "
                                "fields carry no criterion -- they are the result"),
            "records": {}, "2x3": {}, "2x4": {}, "qpu_seconds": 0}
    stop = []
    for lab, (rec, path) in recs.items():
        miss = rec.get("missing_errors") or []
        if miss:
            from collections import Counter
            data["records"][lab] = {"path": path, "fingerprint": rec["fingerprint"],
                                    "last_update_date": rec.get("last_update_date"), "stamp": rec.get("stamp"),
                                    "usable": False, "n_missing_errors": len(miss),
                                    "missing_by_instruction": dict(Counter(m["instruction"] for m in miss)),
                                    "edge_source": (rec.get("survey") or {}).get("edge_source"),
                                    "reason": ("the record carries entries with no error (missing_errors): f, the D9 "
                                               "fingerprint and the routing cannot be evaluated on it (prompts/15 A1 hard stop)")}
            log_line = f"[{lab}] record {path}: UNUSABLE, {len(miss)} missing error leaves {data['records'][lab]['missing_by_instruction']}"
            print(log_line, flush=True)
            continue
        st = record_stats(rec)
        data["records"][lab] = {"path": path, "fingerprint": rec["fingerprint"],
                                "last_update_date": rec.get("last_update_date"), "stamp": rec.get("stamp"),
                                "usable": True, "stats": st}
        block, _tq, _s, _b = evaluate_2x3(rec, lab)
        data["2x3"][lab] = block
        data["2x4"][lab] = evaluate_2x4(st)
        if block["f_ceiling_2q"] >= F_WORST_BAR:
            stop.append(f"{lab}: f_ceiling_2q {block['f_ceiling_2q']:.4f} >= 0.05 (best edge "
                        f"{st['cz_error_min']:.3e}) -- the record changed qualitatively")
    # K0.1
    a2a, a2a_exp = a2a_2x3_count()
    data["a2a_2x3"] = {"cz": a2a, "expected": a2a_exp, "source": "validation/S2.json data.2x3.coarse_step.all_to_all.cz",
                       "transpile": "basis rz/sx/x/cz, coupling_map None, optimization_level 3, seed 0"}
    R_.add("K0.1 all-to-all 2x3 CZ count reproduces validation/S2.json", a2a, f"== {a2a_exp}", a2a == a2a_exp)
    # K0.2
    st = data["records"]["committed"]["stats"]
    rec_c = recs["committed"][0]
    errs = [float(e["cz_error"]) for e in rec_c["edges"].values() if float(e["cz_error"]) < UNCALIBRATED]
    by_hand = {"min": min(errs), "p10": percentile_by_hand(errs, 10), "median": percentile_by_hand(errs, 50)}
    np_vals = {"min": st["cz_error_min"], "p10": st["cz_error_p10"], "median": st["cz_error_median"]}
    two_paths = max(abs(by_hand[k] - np_vals[k]) for k in by_hand)
    planner_rel = {k: abs(np_vals[k] - PLANNER_RECORD[k]) / PLANNER_RECORD[k] for k in np_vals}
    counts_ok = (st["n_calibrated"] == PLANNER_RECORD["n_calibrated"]
                 and st["n_uncalibrated"] == PLANNER_RECORD["n_uncalibrated"])
    data["k0_2"] = {"numpy": np_vals, "by_hand": by_hand, "two_path_max_abs_diff": two_paths,
                    "planner": PLANNER_RECORD, "planner_relative_diff": planner_rel,
                    "note": ("the planner's values are printed to 4 significant figures, so the 1e-12 identity is "
                             "checked between two independent computations on the record (numpy and a hand-written "
                             "linear percentile) and the planner's printed values to half a unit in their 4th figure")}
    R_.add("K0.2 committed-record statistics: min / p10 / median of cz_error two ways to 1e-12 and = the planner's "
           "printed values; 342 calibrated / 10 uncalibrated keys",
           f"two-path max diff {two_paths:.1e}; planner rel diff max {max(planner_rel.values()):.1e}; counts "
           f"{st['n_calibrated']}/{st['n_uncalibrated']}",
           f"<= 1e-12; <= {PLANNER_SIG_TOL}; 342/10",
           two_paths <= TOL and max(planner_rel.values()) <= PLANNER_SIG_TOL and counts_ok)
    # K0.3 / K0.4 / K0.5 on every record
    k3, k4, k5 = [], [], []
    for lab, b in data["2x3"].items():
        recomputed = (1.0 - b["eps2_min"]) ** b["n_cz"]
        k3.append(abs(recomputed - b["f_ceiling_2q"]) <= TOL * max(1.0, recomputed)
                  and b["f_gates_layout"] <= b["f_gates_best_patch_bound"] <= b["f_ceiling_2q"])
        k4.append(b["schedule"]["k0_4_ok"])
        k5.append(all(b["idle"][x]["f_idle_aware_xy4"] <= b["f_gates_layout"]
                      and max(b["idle"][x]["f_idle_aware_xy4_95"]) <= b["f_gates_layout"] for x in T2_RATIOS))
    R_.add("K0.3 f_ceiling_2q = (1-eps2_min)^n_CZ from the JSON's own fields to 1e-12; f_gates_layout <= "
           "best-patch bound <= ceiling (every record)", f"{sum(k3)}/{len(k3)} records", "all", all(k3))
    R_.add("K0.4 the ALAP schedule moves no non-delay operation (per-qubit order) and its duration equals the "
           "unscheduled T_total (h0_qpu_time.circuit_duration_s vs idle.schedule_asap) to 1e-12",
           "; ".join(f"{lab}: moved {b['schedule']['non_delay_ops_moved']}, |dT| {b['schedule']['duration_delta_s']:.1e} s"
                     for lab, b in data["2x3"].items()), "no move, <= 1e-12 s", all(k4))
    R_.add("K0.5 f_idle_aware_xy4 <= f_gates_layout (the cap applied, both T2 ends, R's 95 % ends)",
           f"{sum(k5)}/{len(k5)} records", "all", all(k5))
    if args.skip_tests:
        checks = {"skipped": True, "ok": None}
        R_.add("K0.6 pytest -q tests and scripts/check_package.py", "n/a (--skip-tests)", "all pass", False)
    else:
        import gate_S2D_levers as G
        checks = G.run_checks(False)
        R_.add("K0.6 pytest -q tests and scripts/check_package.py",
               f"pytest: {checks.get('pytest_summary')}; check_package rc {checks.get('check_package_returncode')}",
               "all pass", checks["ok"])
    data["checks"] = checks
    data["stop"] = stop
    data["verdict_record"] = "committed"
    R_.data = data
    R_.runtime_s = time.time() - t0
    path = R_.save()
    saved = load_json(path)
    write_report("K0_2x3_2x4.md", report_text(saved, R_))
    print(R_.criteria_table())
    print(f"status {saved['status']}")
    if stop:
        print("STOP: " + "; ".join(stop))
        return 3
    return 0 if saved["status"] == "PASS" else 1


def _e(x, spec="{:.3e}"):
    return "n/a" if x is None else spec.format(x)


def report_text(saved, R_):
    from skqd.report import md_table
    D = saved["data"]
    rrows = []
    for lab, r in D["records"].items():
        if not r.get("usable", True):
            rrows.append([lab, f"`{r['path']}`", f"`{r['fingerprint'][:16]}`", r["last_update_date"],
                          f"UNUSABLE: {r['n_missing_errors']} missing error leaves {r['missing_by_instruction']}"]
                         + [""] * 9)
            continue
        s = r["stats"]
        rrows.append([lab, f"`{r['path']}`", f"`{r['fingerprint'][:16]}`", r["last_update_date"],
                      _e(s["cz_error_min"]), _e(s["cz_error_p10"]), _e(s["cz_error_median"]), _e(s["cz_error_mean"]),
                      f"{s['n_calibrated']}/{s['n_uncalibrated']}", _e(s["sx_error_median"]),
                      _e(s["measure_error_median"]), _e(s["T1_s_median"] * 1e6, "{:.1f}"),
                      _e(s["T2_s_median"] * 1e6, "{:.1f}"),
                      ", ".join(f"{x * 1e9:.0f}" for x in s["cz_duration_s_values"])])
    frows, srows = [], []
    for lab, b in D["2x3"].items():
        i = b["idle"]
        frows.append([lab, b["circuit"]["id"], b["routing"]["best_seed"], b["n_cz"], b["n_1q"], b["depth"],
                      b["n_active_qubits"], _e(b["f_ceiling_2q"]), _e(b["f_gates_best_patch_bound"]),
                      _e(b["f_gates_layout"]), _e(b["schedule"]["scheduled_duration_s"] * 1e6, "{:.1f}"),
                      f"{i['echo']['S_idle']:.2f} / {i['transferred_0.174']['S_idle']:.2f}",
                      f"{_e(i['echo']['f_idle_aware'])} / {_e(i['transferred_0.174']['f_idle_aware'])}",
                      f"{_e(i['echo']['f_idle_aware_xy4'])} / {_e(i['transferred_0.174']['f_idle_aware_xy4'])}"])
        for var in VARIANTS:
            vv = {v["seed"]: v for v in b["routing"]["per_seed"].values() if v["variant"] == var}
            if vv:
                srows.append([lab, var] + [f"{vv[s]['cz']}" + ("" if vv[s]["exactness"] is None else
                                                              (" (exact)" if vv[s]["exactness"]["ok"] else
                                                               f" (|dpsi| {vv[s]['exactness']['max_abs_delta_up_to_phase']:.1e})"))
                                           for s in sorted(vv)])
    v4 = []
    for lab, blk in D["2x4"].items():
        for c, x in blk.items():
            v4.append([lab, c, x["n_cz"], x["n_1q"], f"{x['log10_f_ceiling_2q']:.1f}", _e(x["f_gates_best_patch_bound"]),
                       _e(x["eps2_needed_for_f_0.05_nothing_else_wrong"]), f"{x['best_edge_misses_by_factor']:.1f}"])
    vrows = []
    for lab, b in D["2x3"].items():
        for name, v in b["verdict"].items():
            vrows.append([lab, name, v["meets_mean_0.1"], v["meets_worst_0.05"]])
    c = D["2x3"]["committed"]
    return f"""# Gate {saved['gate']} -- ibm_kingston readiness of 2x3 and 2x4

**Status: {saved['status']}** -- `scripts/gate_K0_2x3_2x4.py{' --live' if 'live' in D['records'] else ''}`.  Runtime
{saved['runtime_s']:.0f} s, 0 QPU seconds (live reads are metadata).  Every number below is computed by the script and stored
in `validation/{saved['gate']}.json`.  Prompt in force: `prompts/25_2x3_2x4_kingston_check_and_ionq_prep.md` (Part A).

## 0. What PASS means

{D['what_pass_means']}.  The verdict is read on the **{D['verdict_record']}** record; any live record is reported beside it.

## 1. Records (A1, A2)

{md_table(["record", "path", "fingerprint", "last update", "cz min", "cz p10", "cz median", "cz mean",
           "calibrated / uncalibrated keys", "sx median", "readout median", "T1 median (us)", "T2 median (us)",
           "cz durations (ns)"], rrows)}

K0.2 detail: {D['k0_2']['note']}.

## 2. The routed 2x3 circuit and its f (A3, A4)

All-to-all CZ of the same IR: {D['a2a_2x3']['cz']} (expected {D['a2a_2x3']['expected']}, {D['a2a_2x3']['source']}).

CZ per transpiler seed:

{md_table(["record", "variant"] + [f"seed {s}" for s in range(len(srows[0]) - 2)], srows)}

Routing rule: {c['routing']['rule']}.  Chosen on the committed record: `{c['routing']['chosen']}` ({c['n_cz']} CZ, |dpsi|
{_e(c['exactness']['max_abs_delta_up_to_phase'], '{:.1e}')}, leakage {_e(c['exactness']['leakage'], '{:.1e}')}); the plain
level-3 fewest-CZ seed `{c['routing']['plain_l3_fewest_cz']['key']}` has {c['routing']['plain_l3_fewest_cz']['cz']} CZ.

{md_table(["record", "circuit", "seed", "CZ", "1q (sx+x)", "depth", "active qubits", "f_ceiling_2q",
           "f_best_patch_bound", "f_gates_layout", "ALAP duration (us)", "S_idle echo / 0.174 (nats)",
           "f_idle_aware echo / 0.174", "f_idle_aware_xy4 echo / 0.174"], frows)}

Formulas: f_ceiling_2q = {c['f_ceiling_2q_formula']}; f_gates_layout = {c['f_gates_layout_formula']};
best-patch bound = {c['f_gates_best_patch_bound_formula']}.  S_idle = S_T1 + S_T2 over the explicit ALAP delay windows
(leading windows excluded) in the Pauli-twirled thermal-relaxation approximation (`skqd.idle.idle_budget`), T2 = the
record's echo T2 times 1 or 0.174.  XY4: R = {c['xy4_gain']['R']:.4f} (95 % {_e(c['xy4_gain']['R_95'][0], '{:.4f}')} ..
{_e(c['xy4_gain']['R_95'][1], '{:.4f}')}, {c['xy4_gain']['source']}); {c['xy4_gain']['label']}.

## 3. 2x4 (A5; ceilings only)

{md_table(["record", "count", "CZ", "1q", "log10 f_ceiling_2q", "best-patch bound", "eps2 needed (f = 0.05)",
           "best edge misses by"], v4)}

## 4. Verdict fields (A6; the result, no criterion)

2x3 on the committed record: eps2 needed for f = 0.05 with nothing else wrong {_e(c['eps2_needed_for_f_0.05_nothing_else_wrong'])}
(exact {_e(c['eps2_needed_for_f_0.05_exact'])}); the record's best edge {_e(c['eps2_min'])} misses it by a factor
{c['best_edge_misses_by_factor']:.2f}.

{md_table(["record", "f", "meets mean 0.1", "meets worst 0.05"], vrows)}

STOP conditions: {D['stop'] or 'none (f_ceiling_2q < 0.05 on every record)'}.

## 5. Criteria

{R_.criteria_table()}
"""


if __name__ == "__main__":
    sys.exit(main())
