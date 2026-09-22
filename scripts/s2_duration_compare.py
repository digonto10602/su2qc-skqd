#!/usr/bin/env python3
"""
Circuit-family comparison under DURATION, not two-qubit gate count (prompts/20).

Gate H0_diag (`validation/H0_diag.json`, 2026-09-22) established that the dominant error of
the 2x2 circuits on ibm_fez is idle-time decoherence over the circuit's wall-clock duration,
not the two-qubit gate count: the frozen canary runs 43.71 us at depth 1328 for only 663 CZ
(nearly serial), each of its 12 qubits idles 19-42 us, and the idle relaxation budget is
3.323 error units against the 2.153 missing from the gate-only prediction.  Item 3 of
`proposal/amendment_01_devices_and_budgets.md` ("the circuit family stays the exact
structured circuits of gate S2") was decided on ROUTED CZ COUNT, which is no longer the
figure of merit.  This script re-evaluates the choice on the corrected objective.

For each candidate family at 2x2 --

  * `exact`  -- `CircuitFactory(angle_mode="exact")`, the family of gate S2
                (`validation/S2.json`, 2x2: 256 all-to-all / 618 routed CZ per coarse step;
                the 2164 that item 3 of the amendment quotes is the 2x3 all-to-all count,
                `validation/S2D.json:data.2x3.all_to_all_cz_k1`),
  * `fixed`  -- `CircuitFactory(angle_mode="fixed")`, the fixed-angle generator of
                `validation/S2_fixed.json` (2x2: 240 all-to-all / 671 routed), rejected on
                routed cost in 2026-09-15 --

it transpiles the SAME circuits (reference, k, r) with the SAME transpiler settings as the
frozen set (`scripts/h0_build_circuits.py`: optimization_level 3, seed 7) in two layout
regimes, pinned (both families on the canary's 12 physical qubits, so the only difference is
the family) and free (each family on its own calibration-aware layout), and schedules every
one of them with `scripts/h0_idle_model.py` -- the module is IMPORTED, not reimplemented, so
the schedule, the idle windows, the PTA relaxation budget, the DD eligibility rule and the
yield model are bit-for-bit the ones gate H0_diag was preregistered with.

It also measures the RE-SCHEDULING HEADROOM inside the exact family: for any reordering of
the same gates on the same layout, no qubit can run faster than its own busy time, so

    T_min = max_q busy_q   <=   T   (the ASAP critical path)

is a rigorous lower bound on the duration, and the idle budget evaluated on the perfectly
packed schedule (one window of T_min - busy_q per qubit, the window structure that MINIMISES
the PTA budget at fixed total idle time) is a rigorous lower bound on S_T1 + S_T2.  Nothing
is fitted and no new decomposition is implemented: this is a measurement.

No QPU time; offline on committed calibration records.

Usage:
  python scripts/s2_duration_compare.py
  python scripts/s2_duration_compare.py --quick        # the canary parameters only
Runtime: about 3 minutes on the i7-8750H (CPU only).
"""
import argparse
import gzip
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.report import _jsonable, environment  # noqa: E402

import h0_idle_model as idle  # noqa: E402  (schedule / budgets / f_on_record / predictions)
from gate_H0P import random_acceptance  # noqa: E402
from h0_backends import calibration_record, resolve_backend  # noqa: E402
from h0_build_circuits import repeated_coarse_step  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FROZEN = os.path.join(ROOT, "data", "hardware", "H0_prep")
CANARY = "B0_ref06_k1_rep1"
REAL_RECORD = os.path.join(ROOT, "data", "hardware", "H0_diag_prep",
                           "calibration_20260922T1400Z.json")
LATTICE, G2, LEVEL, SEED = 2, 4.0, 3, 7
FAMILIES = {
    "exact": "exact structured circuits of gate S2 (validation/S2.json), angle_mode='exact'",
    "fixed": "fixed-angle generator (validation/S2_fixed.json), angle_mode='fixed'",
}


# ------------------------------------------------------------------ circuits
def build(family, ref_index, k, r, dt, model, backend, initial_layout=None):
    """Transpile one coarse-step circuit of `family` exactly as h0_build_circuits does."""
    from qiskit import transpile

    from skqd import circuits_qiskit as cq
    F = CircuitFactory(model, G2, angle_mode=family)
    gates = repeated_coarse_step(F, ref_index, k, dt, r)
    qc = cq.ir_to_qiskit(gates, Codec(model.basis).n_qubits, measure=True)
    kw = {} if initial_layout is None else {"initial_layout": list(initial_layout)}
    return transpile(qc, backend=backend, optimization_level=LEVEL, seed_transpiler=SEED, **kw)


def load_frozen_canary():
    from qiskit import qpy
    with open(os.path.join(FROZEN, "circuits", CANARY + ".json")) as fh:
        man = json.load(fh)
    with gzip.open(os.path.join(FROZEN, "circuits", man["qpy"]), "rb") as fh:
        return qpy.load(fh)[0], man


def cz_depth(tq):
    """Number of CZ LAYERS in the circuit DAG (qiskit's own filtered depth)."""
    return int(tq.depth(filter_function=lambda i: i.operation.name == "cz"))


# ------------------------------------------------------------------ measurement
def measure(tq, rec, a):
    """Schedule + idle budget + f + predictions of one transpiled circuit, via h0_idle_model."""
    sch = idle.schedule(tq, rec)
    per_q, tot = idle.budgets(sch, rec)
    f_gates, f_gates_only, ro, n_cz, n_meas = idle.f_on_record(tq, rec)
    pred = idle.predictions(f_gates, tot, a)
    busy = {q: sch["per_qubit"][q]["busy_s"] for q in sch["active"]}
    ops = {k: int(v) for k, v in tq.count_ops().items()}
    return {
        "n_cz": n_cz, "n_measure": n_meas, "depth": int(tq.depth()), "cz_depth": cz_depth(tq),
        "cz_per_cz_layer": n_cz / cz_depth(tq) if cz_depth(tq) else None,
        "n_1q": int(sum(v for k, v in ops.items() if k in ("sx", "x", "rz"))),
        "ops": ops, "active_qubits": sch["active"], "n_active": len(sch["active"]),
        "T_s": sch["T_s"], "T_total_s": sch["T_total_s"],
        "idle_total_s": tot["idle_s"], "busy_total_s": tot["busy_s"],
        "busy_max_s": max(busy.values()), "busy_min_s": min(busy.values()),
        "idle_max_s": max(sch["per_qubit"][q]["idle_s"] for q in sch["active"]),
        "idle_min_s": min(sch["per_qubit"][q]["idle_s"] for q in sch["active"]),
        "n_windows": tot["n_windows"], "dd_eligible": tot["dd_eligible"],
        "S_T1": tot["S_T1"], "S_T2": tot["S_T2"], "S_DD": tot["S_DD"],
        "S_T2_eligible": tot["S_T2_eligible"], "S_T2_ineligible": tot["S_T2_ineligible"],
        "f_gates": f_gates, "f_gates_only": f_gates_only, "measure_survival": ro,
        "f_idle_dd_off": pred["dd_off"]["f"], "yield_idle_dd_off": pred["dd_off"]["yield"],
        "f_idle_dd_on": {k: v["f"] for k, v in pred["dd_on"].items()},
        "yield_idle_dd_on": {k: v["yield"] for k, v in pred["dd_on"].items()},
        "_sch": sch, "_per_q": per_q,
    }


def packing_bound(m, rec, a):
    """The best duration and idle budget ANY reordering of the same gates on the same layout
    can reach: T_min = max_q busy_q, one idle window of T_min - busy_q per qubit.

    Lower bound on the duration because a qubit executes its own instructions serially; lower
    bound on the PTA budget because 1 - e^{-w/T} is concave, so splitting a fixed total idle
    time into several windows can only increase the sum.  Evaluated with h0_idle_model.budgets
    so that the formula is the preregistered one."""
    sch = m["_sch"]
    T_min = m["busy_max_s"]
    per_qubit = {}
    for q in sch["active"]:
        b = sch["per_qubit"][q]["busy_s"]
        w = max(T_min - b, 0.0)
        per_qubit[q] = {"busy_s": b, "delay_s": 0.0, "idle_s": w,
                        "windows_s": [w] if w > 1e-15 else []}
    ideal = {"active": sch["active"], "per_qubit": per_qubit, "T_s": T_min,
             "T_total_s": T_min + sch["measure_duration_s"],
             "measured_qubits": sch["measured_qubits"],
             "measure_duration_s": sch["measure_duration_s"]}
    _, tot = idle.budgets(ideal, rec)
    pred = idle.predictions(m["f_gates"], tot, a)
    return {
        "T_min_s": T_min, "T_s": m["T_s"], "speedup_available": m["T_s"] / T_min,
        "idle_total_s": tot["idle_s"], "idle_total_now_s": m["idle_total_s"],
        "S_T1": tot["S_T1"], "S_T2": tot["S_T2"],
        "S_T1_now": m["S_T1"], "S_T2_now": m["S_T2"],
        "f_idle_dd_off": pred["dd_off"]["f"], "yield_idle_dd_off": pred["dd_off"]["yield"],
        "f_gain": pred["dd_off"]["f"] / m["f_idle_dd_off"] if m["f_idle_dd_off"] else None,
        "qubit_time_utilisation": m["busy_total_s"] / (m["n_active"] * m["T_s"]),
    }


def term_supports(model):
    """Qubit support of every Hamiltonian term of the coarse step (both families share it:
    the fixed-angle generator keeps the same codeword pairs and the same validity controls)."""
    F = CircuitFactory(model, G2)
    dt = float(model.reference(G2, 0).dt)
    terms = {"diag": F.diag_gates(dt)}
    for l in range(F.lat.n_links):
        terms[f"hop{l}"] = F.hop_gates(l, dt)
    for P in range(len(F.lat.plaquettes)):
        terms[f"plaq{P}"] = F.plaq_gates(P, dt, True)
    sup = {}
    for name, gates in terms.items():
        s = set()
        for g in gates:
            s.update(g[1])
        sup[name] = sorted(s)
    names = sorted(sup)
    disjoint = [[a, b] for i, a in enumerate(names) for b in names[i + 1:]
                if not set(sup[a]) & set(sup[b])]
    return {"supports": sup, "support_sizes": {k: len(v) for k, v in sup.items()},
            "n_terms": len(sup), "disjoint_pairs": disjoint,
            "n_disjoint_pairs": len(disjoint),
            "n_pairs": len(names) * (len(names) - 1) // 2}


# ------------------------------------------------------------------ driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="the canary parameters only (ref 6, k = 1)")
    ap.add_argument("--extra-reps", type=int, nargs="+", default=[2, 3],
                    help="repetitions of the canary circuit added to the r = 1 grid")
    ap.add_argument("--out", default=os.path.join("data", "S2_duration_compare.json"))
    ap.add_argument("--md", default=os.path.join("reports", "S2_duration_and_idle_2x2.md"))
    args = ap.parse_args()
    t0 = time.time()

    with open(REAL_RECORD) as fh:
        real = json.load(fh)
    model = Model(LATTICE)
    codec = Codec(model.basis)
    acc = {0: random_acceptance(codec, 0)["fraction"], 2: random_acceptance(codec, 2)["fraction"]}
    backend = resolve_backend("FakeFez")

    # the FakeFez snapshot as a full-device record, so the FREE layouts (which land on
    # different patches) can be scheduled at all; the real ibm_fez record covers only the
    # canary's 12 qubits.
    fez_edges = sorted({tuple(sorted(e)) for e in backend.coupling_map.get_edges()})
    fake = calibration_record(backend, list(range(backend.num_qubits)), fez_edges)

    frozen_qc, frozen_man = load_frozen_canary()
    pin = frozen_man["logical_to_physical"]

    refs = [6] if args.quick else references(model.basis, 0)
    ks = [1] if args.quick else [1, 2, 3, 4]
    dt = float(model.reference(G2, 0).dt)
    # the production grid at r = 1, plus the canary parameters at r = 2, 3 (the repetition axis
    # of manual Step 9.1) so that the family comparison is seen to hold as the circuit grows
    grid = [(ri, k, 1) for ri in refs for k in ks]
    if not args.quick:
        grid += [(6, 1, r) for r in args.extra_reps]

    circuits = {}
    # the ground truth: the frozen canary circuit itself, on the record the device ran under
    m = measure(frozen_qc, real, acc[0])
    circuits["exact|frozen|B0_ref06_k1_rep1"] = {
        "family": "exact", "regime": "frozen (the submitted QPY of data/hardware/H0_prep)",
        "record": "ibm_fez 2026-09-22T08:00:30-06:00", "reference": 6, "k": 1, "repetitions": 1,
        **m}
    frozen_key = "exact|frozen|B0_ref06_k1_rep1"

    real_qubits = {int(q) for q in real["qubits"]}
    escaped = []

    def add(key, family, regime, tq, ref_index, k, r):
        """Schedule on the real ibm_fez record when the circuit stays inside the 12 qubits it
        covers, otherwise on the full FakeFez snapshot.  The record is part of the record."""
        act = sorted({tq.find_bit(q).index for inst in tq.data for q in inst.qubits
                      if inst.operation.name != "barrier"})
        pinned = regime.startswith("pinned")
        # the real ibm_fez record covers only the canary's 12 qubits, so it can carry the
        # PINNED circuits (when routing stays inside the patch); the FREE layouts of the two
        # families land on different patches and are compared on the full FakeFez snapshot,
        # which covers every patch -- a pair is always scheduled on ONE record.
        on_real = pinned and set(act) <= real_qubits
        if pinned and not on_real:
            escaped.append({"circuit": key, "outside_the_patch":
                            sorted(set(act) - real_qubits)})
        rec, name = ((real, f"ibm_fez {real['last_update_date']}") if on_real
                     else (fake, f"FakeFez snapshot {fake['last_update_date']}"))
        circuits[key] = {"family": family, "regime": regime, "record": name,
                         "on_ibm_fez_record": bool(on_real), "reference": ref_index,
                         "k": k, "repetitions": r, **measure(tq, rec, acc[0])}

    for family in FAMILIES:
        for ref_index, k, r in grid:
            tag = f"ref{ref_index:02d}_k{k}_rep{r}"
            add(f"{family}|pinned|{tag}", family, "pinned to the canary patch",
                build(family, ref_index, k, r, dt, model, backend, initial_layout=pin),
                ref_index, k, r)
            add(f"{family}|free|{tag}", family, "free (calibration-aware layout)",
                build(family, ref_index, k, r, dt, model, backend), ref_index, k, r)
        print(f"{family}: done ({time.time() - t0:.0f} s)", flush=True)

    # the free-layout exact circuit at the canary's parameters must BE the frozen QPY:
    # same transpiler, same seed, same backend (scripts/h0_build_circuits.py)
    fk = "exact|free|ref06_k1_rep1"
    reproduces = (fk in circuits
                  and circuits[fk]["n_cz"] == circuits[frozen_key]["n_cz"]
                  and circuits[fk]["depth"] == circuits[frozen_key]["depth"]
                  and circuits[fk]["active_qubits"] == circuits[frozen_key]["active_qubits"])

    # the re-scheduling headroom, on the circuit the hardware actually ran
    head = packing_bound(circuits[frozen_key], real, acc[0])
    head["terms"] = term_supports(model)
    head["cz_depth"] = circuits[frozen_key]["cz_depth"]
    head["n_cz"] = circuits[frozen_key]["n_cz"]
    head["per_qubit"] = {
        str(q): {"busy_s": circuits[frozen_key]["_sch"]["per_qubit"][q]["busy_s"],
                 "idle_s": circuits[frozen_key]["_sch"]["per_qubit"][q]["idle_s"],
                 "T1_s": circuits[frozen_key]["_per_q"][str(q)]["T1_s"],
                 "T2_s": circuits[frozen_key]["_per_q"][str(q)]["T2_s"],
                 "S_T1": circuits[frozen_key]["_per_q"][str(q)]["S_T1"],
                 "S_T2": circuits[frozen_key]["_per_q"][str(q)]["S_T2"]}
        for q in circuits[frozen_key]["_sch"]["active"]}

    for c in circuits.values():                      # the schedules are not part of the record
        c.pop("_sch", None)
        c.pop("_per_q", None)

    # per (family, layout regime, calibration record) aggregates -- a group never mixes records
    def short(c):
        return "ibm_fez" if c["on_ibm_fez_record"] else "FakeFez"

    agg = {}
    for key, c in circuits.items():
        if c["regime"].startswith("frozen"):
            continue
        agg.setdefault(f"{c['family']}|{c['regime'].split(' ')[0]}|{short(c)}", []).append(c)
    summary = {}
    for g, cs in sorted(agg.items()):
        def st(field):
            v = [c[field] for c in cs]
            return {"mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}
        summary[g] = {
            "family": cs[0]["family"], "regime": cs[0]["regime"], "record": cs[0]["record"],
            "n_circuits": len(cs),
            "T_s": st("T_s"), "T_total_s": st("T_total_s"), "depth": st("depth"),
            "cz_depth": st("cz_depth"), "n_cz": st("n_cz"), "n_1q": st("n_1q"),
            "idle_total_s": st("idle_total_s"), "idle_max_s": st("idle_max_s"),
            "S_T1": st("S_T1"), "S_T2": st("S_T2"), "S_DD": st("S_DD"),
            "f_gates": st("f_gates"), "f_idle_dd_off": st("f_idle_dd_off"),
            "yield_idle_dd_off": st("yield_idle_dd_off"),
        }

    # the family verdict: PAIRED, circuit by circuit -- same (reference, k, r), same layout
    # regime and same calibration record on both sides, so the only difference is the family
    verdict = {}
    groups = {}
    for key, c in circuits.items():
        f_, reg, tag = key.split("|")
        if f_ != "exact" or reg == "frozen":
            continue
        o = circuits.get(f"fixed|{reg}|{tag}")
        if o is None or o["on_ibm_fez_record"] != c["on_ibm_fez_record"]:
            continue
        groups.setdefault(f"{reg} / {short(c)}", []).append((tag, c, o))
    for gkey, pairs in sorted(groups.items()):
        regime = gkey

        def ratio(field, invert=False):
            v = [(o[field] / c[field]) if not invert else (c[field] / o[field])
                 for _, c, o in pairs if c[field]]
            return {"mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}
        exact_f = float(np.mean([c["f_idle_dd_off"] for _, c, _ in pairs]))
        fixed_f = float(np.mean([o["f_idle_dd_off"] for _, _, o in pairs]))
        verdict[regime] = {
            "n_pairs": len(pairs), "circuits": sorted(t for t, _, _ in pairs),
            "records": sorted({short(c) for _, c, _ in pairs}),
            "T_ratio_fixed_over_exact": ratio("T_s"),
            "depth_ratio": ratio("depth"), "cz_ratio": ratio("n_cz"),
            "idle_ratio": ratio("idle_total_s"),
            "S_T1_T2_ratio": {"mean": float(np.mean([(o["S_T1"] + o["S_T2"])
                                                     / (c["S_T1"] + c["S_T2"])
                                                     for _, c, o in pairs]))},
            "f_gates_ratio": ratio("f_gates"),
            "f_idle_ratio_fixed_over_exact": ratio("f_idle_dd_off"),
            "yield_ratio": ratio("yield_idle_dd_off"),
            "mean_f_idle_exact": exact_f, "mean_f_idle_fixed": fixed_f,
            "winner": "fixed" if fixed_f > exact_f else "exact",
            "win_margin_f": max(exact_f, fixed_f) / min(exact_f, fixed_f),
        }

    # every number the report puts in prose comes from a JSON: collect the ones it cites
    def load_val(name):
        with open(os.path.join(ROOT, "validation", name)) as fh:
            return json.load(fh)

    diag, s2, s2f = load_val("H0_diag.json"), load_val("S2.json"), load_val("S2_fixed.json")

    def crit(d, sub):
        return next(c for c in d["criteria"] if sub in c["name"])
    context = {
        "H0_diag": {"source": "validation/H0_diag.json", "status": diag["status"],
                    "total_usage_s": diag["data"]["total_usage_s"],
                    "N1": crit(diag, "decisive J1 count")["value"]},
        "S2": {"source": "validation/S2.json", "status": s2["status"],
               "max_deviation": crit(s2, "max |structured circuit")["value"],
               "cz_routed_2x2": crit(s2, "2x2: CZ per coarse step, routed on heavy-hex")["value"],
               "cz_all_to_all_2x2": s2["data"]["2x2"]["coarse_step"]["all_to_all"]["cz"]},
        "S2_fixed": {"source": "validation/S2_fixed.json", "status": s2f["status"],
                     "max_per_term_deviation_2x2":
                         max(s2f["data"]["2x2"]["per_term_max_deviation"].values()),
                     "cz_routed_2x2":
                         crit(s2f, "2x2: CZ per coarse step, routed on heavy-hex")["value"],
                     "cz_all_to_all_2x2":
                         s2f["data"]["2x2"]["coarse_step"]["all_to_all"]["cz"],
                     "recall_2x3_B0": crit(s2f, "2x3 B=0: emulated recall")["value"],
                     "recall_2x3_B1": crit(s2f, "2x3 B=1: emulated recall")["value"]},
    }

    out = {
        "script": "scripts/s2_duration_compare.py",
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "question": ("item 3 of proposal/amendment_01_devices_and_budgets.md re-evaluated on "
                     "duration and idle budget instead of two-qubit gate count (gate H0_diag, "
                     "validation/H0_diag.json)"),
        "families": FAMILIES,
        "method": {
            "schedule": "scripts/h0_idle_model.py (imported): ASAP on the record's durations",
            "idle_budget": ("per idle window w on qubit q: (1 - e^{-w/T1})/4 + (1 - e^{-w/T2})/2 "
                            "(Pauli-twirling approximation of thermal relaxation, "
                            "h0_idle_model.budgets)"),
            "transpiler": {"backend": "FakeFez", "optimization_level": LEVEL,
                           "seed_transpiler": SEED,
                           "pinned_initial_layout": pin,
                           "note": ("pinned = both families on the canary's 12 physical qubits "
                                    "(the only difference is then the family); free = each "
                                    "family on its own calibration-aware layout")},
            "records": {
                "ibm_fez": {"path": os.path.relpath(REAL_RECORD, ROOT),
                            "last_update_date": real["last_update_date"],
                            "fingerprint": real["fingerprint"],
                            "covers_qubits": sorted(int(q) for q in real["qubits"])},
                "FakeFez": {"source": "qiskit_ibm_runtime.fake_provider.FakeFez (offline snapshot)",
                            "last_update_date": fake["last_update_date"],
                            "n_qubits": fake["num_qubits"]}},
            "packing_bound": packing_bound.__doc__.strip(),
            "qpu_time_used_s": 0.0,
        },
        "garbage_acceptance": {"B=0": acc[0], "B=1": acc[2]},
        "context": context,
        "n_circuits": len(circuits),
        "free_layout_exact_reproduces_the_frozen_canary": bool(reproduces),
        "pinned_circuits_that_left_the_patch": escaped,
        "summary": summary,
        "verdict": verdict,
        "rescheduling_headroom": head,
        "circuits": circuits,
        "runtime_s": time.time() - t0,
        "environment": environment(),
    }
    p = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        json.dump(_jsonable(out), fh, indent=1)
    print(f"wrote {os.path.relpath(p, ROOT)} ({len(circuits)} circuits, {time.time() - t0:.0f} s)")
    if args.md:
        from s2_duration_report import report_text
        mp = args.md if os.path.isabs(args.md) else os.path.join(ROOT, args.md)
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        with open(mp, "w") as fh:
            fh.write(report_text(out))
        print(f"wrote {os.path.relpath(mp, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
