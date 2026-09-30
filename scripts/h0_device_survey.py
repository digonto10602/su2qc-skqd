#!/usr/bin/env python3
"""
The free device survey of prompts/20 part E: full-device calibration records, the T2 geography
of each device, and the exhaustive patch search run on those records.

Decision D1' (signed 2026-09-30) makes patch selection part of the preparation: the patch is
chosen by the idle-aware objective from a FULL-DEVICE record, and the whole circuit set is then
re-frozen onto the winning twelve qubits.  The committed H0 records cover only the 30 qubits
the frozen set already touches, which admits 10 embeddings and a 1.41x gain; a full device
admits about 1500 and gave 3.31x on the FakeFez snapshot.  This script writes the records the
search needs and runs the search (`scripts/h0_patch_select.py`, imported as a subprocess and
NOT modified), so that the owner can pick the device and the patch before prompts/21.

**Zero QPU seconds.**  A live record is `backend.target` / `properties()` / `status()`, which
are metadata queries; an offline snapshot needs no account at all.  Nothing here submits,
freezes or transpiles a circuit for execution.

What is reported per device (part E2, the P12 statistics on the surveyed record):
  * T2 percentiles 10/25/50/75/90 and the fraction of qubits at or above 50, 100 and 150 us;
  * the largest connected components of the subgraph in which every qubit has readout error
    <= 3 % and T2 >= T2_min and every edge has CZ error <= 1 %, for
    T2_min in {40, 60, 80, 100, 120, 150} us (breadth-first search over the coupling map --
    no networkx dependency);
and per device (part E3): the winning patch, its f_gates, S_T1, S_T2 and PTA clean f, its
weakest three qubits by T2, and the two shot budgets at that f -- rule D3' as it stands, and
the D3''-H0 sizing the owner signed for gate H0 alone.  Both budgets are labelled as the
ECHO-T2 end: the score uses the record's Hahn-echo T2 because the free-induction T2* of the
selected patch is unknown until the pilot, and on the patch that flew the measured in-circuit
budget was 1.73x the echo estimate.

Usage:
  python scripts/h0_device_survey.py                       # the three reachable Heron r2 devices
  python scripts/h0_device_survey.py --devices FakeFez FakeMarrakesh FakeKingston
Runtime: seconds per record plus about 90 s per full-device patch search.
"""
import argparse
import collections
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd import idle  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import ideal_sector_distribution  # noqa: E402
from skqd.report import env_block, md_table, write_report  # noqa: E402
from skqd.skqd import READOUT_FACTOR, poisson_lambda_star  # noqa: E402

from gate_H0P import load_circuit, load_index, load_manifests  # noqa: E402
from h0_backends import (calibration_record, fresh_calibration, is_fake,  # noqa: E402
                         resolve_backend)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_DEVICES = ("ibm_fez", "ibm_marrakesh", "ibm_kingston")
DEFAULT_OUTDIR = os.path.join("data", "hardware", "device_survey_20260922")
DEFAULT_PREP = os.path.join("data", "hardware", "H0_prep")
T2_MINS_US = (40, 60, 80, 100, 120, 150)
READOUT_MAX = 0.03          # P12: the readout ceiling of the connected-component search
CZ_MAX = 0.01               # P12: the CZ-error ceiling
T2_FRACTION_LEVELS_US = (50, 100, 150)
PERCENTILES = (10, 25, 50, 75, 90)
REP_DELAY_DEFAULT = 250e-6
# rule D3' as it stands (prompts/16), unchanged by this script
D3_FLOOR, D3_MARGIN, D3_ROUND, D3_K, D3_CONF = 267, 0.7, 100, 3, 0.95
D3_REPS_SHOTS = {2: 130, 3: 92}
D3_CAL_SHOTS = 4000
# decision D3''-H0: the k = 1 circuits are sized for criterion 2's clean-f statistic
D3PP_SHOTS_PER_INVERSE_F = 140.0     # ~100 clean reference hits -> sigma_f / f ~ 0.10
D3PP_CAL_CIRCUITS = 14               # one shared patch (decision D1'), not 42
# P11 of the planner analysis: the D3' execution time against a uniform r = 1 clean f,
# at the frozen circuits' durations, 14 calibration circuits, 250 us rep delay.  Kept as the
# cross-check of the budget this script computes from scratch.
P11_TABLE = ((0.2103, 38.0), (0.10, 60.8), (0.05, 104.2), (0.03, 162.1),
             (0.02, 234.3), (0.0126, 361.6), (0.0076, 588.1))


# --------------------------------------------------------------------------- E1
def full_device_record(name):
    """A `calibration_record` over ALL qubits and ALL coupling edges of one device."""
    b = resolve_backend(name)                     # a NEW backend object per device
    edges = sorted({(int(a), int(c)) for a, c in b.coupling_map})
    qubits = list(range(int(b.num_qubits)))
    rec = (calibration_record(b, qubits, edges) if is_fake(name)
           else fresh_calibration(b, qubits, edges))
    rec["survey"] = {
        "kind": ("offline fake-provider snapshot (full device)" if is_fake(name)
                 else "live device target, read-only metadata (0 QPU seconds)"),
        "requested_name": name,
        "n_qubits_surveyed": len(qubits),
        "n_edges_surveyed": len(edges),
        "note": ("this record covers the WHOLE device, not only the 30 qubits the frozen set "
                 "touches: rule D1' needs the full candidate space"),
    }
    return rec


# --------------------------------------------------------------------------- E2
def host_edges(rec):
    out = set()
    for e in rec["edges"].values():
        a, b = (int(x) for x in e["target_key"])
        out.add((min(a, b), max(a, b)))
    return sorted(out)


def t2_statistics(rec):
    t2 = {int(q): v["T2_s"] for q, v in rec["qubits"].items()}
    t1 = {int(q): v["T1_s"] for q, v in rec["qubits"].items()}
    have = [v for v in t2.values() if v]
    n = len(t2)
    return {
        "n_qubits": n,
        "n_with_T2": len(have),
        "fraction_without_T2": (n - len(have)) / n if n else None,
        "T2_percentiles_us": {str(p): float(np.percentile(have, p) * 1e6) for p in PERCENTILES},
        "T2_min_us": float(min(have) * 1e6) if have else None,
        "T2_max_us": float(max(have) * 1e6) if have else None,
        "fraction_T2_at_least": {str(L): float(sum(1 for v in have if v * 1e-6 >= 0 and
                                                   v >= L * 1e-6) / len(have))
                                 for L in T2_FRACTION_LEVELS_US},
        "T1_percentiles_us": {str(p): float(np.percentile([v for v in t1.values() if v], p) * 1e6)
                              for p in PERCENTILES},
    }


def components(rec, t2_min_us, readout_max=READOUT_MAX, cz_max=CZ_MAX):
    """Largest connected components of the good subgraph, by breadth-first search.

    A qubit is good when its readout error is at most `readout_max` and its T2 at least
    `t2_min_us`; an edge is good when both its qubits are good and its CZ error is at most
    `cz_max`.  No networkx."""
    Q = rec["qubits"]
    good = {int(q) for q, v in Q.items()
            if v["measure_error"] is not None and v["measure_error"] <= readout_max
            and v["T2_s"] is not None and v["T2_s"] >= t2_min_us * 1e-6}
    adj = collections.defaultdict(set)
    for e in rec["edges"].values():
        a, b = (int(x) for x in e["target_key"])
        if a in good and b in good and e["cz_error"] is not None and e["cz_error"] <= cz_max:
            adj[a].add(b)
            adj[b].add(a)
    seen, comps = set(), []
    for q in sorted(good):
        if q in seen:
            continue
        stack, comp = [q], []
        seen.add(q)
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in sorted(adj[x]):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        comps.append(sorted(comp))
    comps.sort(key=lambda c: (-len(c), c))
    return {"t2_min_us": t2_min_us, "n_good_qubits": len(good),
            "n_components": len(comps),
            "largest_sizes": [len(c) for c in comps[:4]],
            "largest": comps[0] if comps else [],
            "components_of_at_least_12": sum(1 for c in comps if len(c) >= 12)}


# --------------------------------------------------------------------------- E3 budgets
def frozen_durations(prep, rec):
    """{circuit id: T_total_s} of every frozen circuit on this record's own durations.

    The frozen circuits sit on the patch the transpiler chose (117..146), which exists on
    every 156-qubit Heron r2, so the record covers them.  A re-freeze on the winning patch
    (decision D1', not done here) would move these durations by the difference in the
    patch's gate durations, which is why the budgets below are labelled as computed at the
    frozen set's durations."""
    mans, cals = load_manifests(prep)
    T = {}
    for m in mans + cals:
        qc = load_circuit(prep, m)
        T[m["id"]] = float(idle.schedule_asap(qc, rec)["T_total_s"])
    return T, mans, cals


def ideal_p(model, mans, g2):
    """{circuit id: ideal sector distribution} -- layout-independent, computed once."""
    cache, P = {}, {}
    for m in mans:
        key = (int(m["twoB"]), int(m["reference"]), int(m["k"]),
               round(float(m["dt"]), 15), int(m["repetitions"]))
        if key not in cache:
            cache[key] = ideal_sector_distribution(model, g2, int(m["twoB"]),
                                                   int(m["reference"]), int(m["k"]),
                                                   float(m["dt"]), int(m["repetitions"]))
        P[m["id"]] = cache[key]["p_unnormalised"]
    return P


def d3_budget(P, T, mans, cals, f_r1, rep_delay, cal_shots=D3_CAL_SHOTS,
              cal_circuits=D3PP_CAL_CIRCUITS):
    """Rule D3' at a uniform r = 1 clean f: N4 per sector, the shots and the execution time.

    Exactly `scripts/h0_support_plan.n4_of_sector` with the rule's own constants -- floor 267,
    margin 0.7, lambda* = poisson_lambda_star(3, 0.95), rounded to 100 -- and the r = 2 / 3
    circuits at their frozen 130 / 92.  Nothing of the rule is changed; only its f input is
    the patch's idle-aware bound instead of the gate-only product (decision D3'-f)."""
    import h0_support_plan as sp
    ls = poisson_lambda_star(D3_K, D3_CONF)
    f_by = {m["id"]: (float(f_r1) if int(m["repetitions"]) == 1 else float(f_r1) ** int(m["repetitions"]))
            for m in mans}
    shots, n4 = {}, {}
    for sec in sorted({m["sector"] for m in mans}):
        sm = [m for m in mans if m["sector"] == sec]
        r1 = [m["id"] for m in sm if int(m["repetitions"]) == 1]
        k4 = [m["id"] for m in sm if int(m["repetitions"]) == 1 and int(m["k"]) == 4]
        n4[sec] = sp.n4_of_sector({c: P[c] for c in r1}, f_by, r1, k4, D3_FLOOR, ls,
                                  margin=D3_MARGIN, readout_factor=READOUT_FACTOR,
                                  round_to=D3_ROUND)
        for m in sm:
            r = int(m["repetitions"])
            shots[m["id"]] = (n4[sec] if m["id"] in k4 else D3_FLOOR) if r == 1 \
                else D3_REPS_SHOTS[r]
    T_cal = float(np.mean([T[m["id"]] for m in cals])) if cals else 0.0
    ex = sum(shots[c] * (T[c] + rep_delay) for c in shots) + \
        cal_circuits * cal_shots * (T_cal + rep_delay)
    return {"rule": "D3' (prompts/16), unchanged; f input = the patch's PTA clean f at the "
                    "record's echo T2 (decision D3'-f)",
            "f_r1": float(f_r1), "lambda_star": ls, "margin": D3_MARGIN, "floor": D3_FLOOR,
            "N4": n4,
            "r1_shots_by_sector": {sec: sum(shots[m["id"]] for m in mans
                                            if m["sector"] == sec and int(m["repetitions"]) == 1)
                                   for sec in n4},
            "total_coarse_shots": int(sum(shots.values())),
            "calibration_circuits": cal_circuits, "calibration_shots": cal_shots,
            "calibration_circuit_duration_s": T_cal,
            "rep_delay_s": rep_delay,
            "execution_s": float(ex)}


def p11_interpolated(f):
    """The P11 table interpolated linearly in 1/f (the planner's own figure, as cross-check)."""
    xs = np.array([1.0 / v[0] for v in P11_TABLE])
    ys = np.array([v[1] for v in P11_TABLE])
    x = 1.0 / float(f)
    if x <= xs[0]:
        return float(ys[0] + (ys[1] - ys[0]) * (x - xs[0]) / (xs[1] - xs[0]))
    if x >= xs[-1]:
        return float(ys[-1] + (ys[-1] - ys[-2]) * (x - xs[-1]) / (xs[-1] - xs[-2]))
    return float(np.interp(x, xs, ys))


def d3pp_budget(T, mans, cals, f_clean, rep_delay, cal_shots=D3_CAL_SHOTS,
                cal_circuits=D3PP_CAL_CIRCUITS):
    """Decision D3''-H0: the k = 1 circuits sized for criterion 2's clean-f statistic.

    ~140/f_clean shots each (about 100 clean reference hits, sigma_f/f ~ 0.10), the other r = 1
    circuits at the 267 floor, r = 2 / 3 at their frozen 130 / 92, 14 readout-calibration
    circuits at 4000.  Rule D3' is NOT repealed by this -- it stays the rule for the 2x3
    physics gates -- and what is given up is the full-subspace-collection claim, which
    criterion 3 was passing on accidentally-valid noise anyway."""
    k1 = [m for m in mans if int(m["repetitions"]) == 1 and int(m["k"]) == 1]
    other_r1 = [m for m in mans if int(m["repetitions"]) == 1 and int(m["k"]) != 1]
    deep = [m for m in mans if int(m["repetitions"]) in D3_REPS_SHOTS]
    n_k1 = int(np.ceil(D3PP_SHOTS_PER_INVERSE_F / float(f_clean)))
    shots = {m["id"]: n_k1 for m in k1}
    shots.update({m["id"]: D3_FLOOR for m in other_r1})
    shots.update({m["id"]: D3_REPS_SHOTS[int(m["repetitions"])] for m in deep})
    T_cal = float(np.mean([T[m["id"]] for m in cals])) if cals else 0.0
    ex = sum(shots[c] * (T[c] + rep_delay) for c in shots) + \
        cal_circuits * cal_shots * (T_cal + rep_delay)
    return {"rule": "D3''-H0 (owner, 2026-09-30): gate H0's k = 1 circuits are sized for "
                    "criterion 2's clean-f statistic, not for clean saturation",
            "f_clean": float(f_clean),
            "shots_per_k1_circuit": n_k1, "n_k1_circuits": len(k1),
            "shots_per_other_r1_circuit": D3_FLOOR, "n_other_r1_circuits": len(other_r1),
            "deep_shots": {str(r): s for r, s in D3_REPS_SHOTS.items()},
            "n_deep_circuits": len(deep),
            "calibration_circuits": cal_circuits, "calibration_shots": cal_shots,
            "total_coarse_shots": int(sum(shots.values())),
            "rep_delay_s": rep_delay,
            "execution_s": float(ex),
            "execution_breakdown_s": {
                "k1_circuits": float(sum(shots[m["id"]] * (T[m["id"]] + rep_delay) for m in k1)),
                "other_r1_circuits": float(sum(shots[m["id"]] * (T[m["id"]] + rep_delay)
                                               for m in other_r1)),
                "r2_r3_circuits": float(sum(shots[m["id"]] * (T[m["id"]] + rep_delay)
                                            for m in deep)),
                "readout_calibration": float(cal_circuits * cal_shots * (T_cal + rep_delay)),
            }}


def patch_search_without_the_incumbent(rec, prep, circuit_id, top):
    """The same exhaustive search, when `h0_patch_select.search()` refuses on this record.

    `search()` asserts that the identity embedding -- the patch the transpiler chose for the
    frozen set -- is among the scored candidates, because that is how it checks its own
    enumeration and reproduces `h0_idle_model.py` to 1e-12.  On a device whose record does not
    fully characterise those twelve qubits the assertion cannot be met (the FakeKingston
    snapshot has no T1 and no T2 for qubit 146, one of the twelve), and the script refuses --
    correctly.

    This function calls that script's OWN `enumerate_embeddings`, `score_patch` and `rank_key`
    verbatim, so the ranking is the same computation; what is missing is the incumbent
    consistency check and the incumbent comparison, both of which are recorded as unavailable.
    Nothing is invented: the uncharacterised qubit is skipped like any other candidate the
    record does not cover, never given a defaulted T1 or T2."""
    import h0_patch_select as ps
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    man = next(m for m in mans + cals if m["id"] == circuit_id)
    qc = load_circuit(prep, man)
    pat_adj, pat_edges = ps.interaction_graph(qc)
    host_adj, host_nodes = ps.host_graph(rec)
    from skqd.codec import Codec
    a = ps.random_acceptance(Codec(Model(int(index["common"]["lattice"].split("x")[1])).basis),
                             man["twoB"])["fraction"]
    embs, _order = ps.enumerate_embeddings(pat_adj, host_adj, host_nodes)
    ops = ps.circuit_ops(qc)
    scored, skipped = [], []
    for mp in embs:
        qubits = sorted(mp.values())
        edges = sorted({(min(mp[u], mp[v]), max(mp[u], mp[v])) for u, v in pat_edges})
        ok, why = ps.record_covers(rec, qubits, edges)
        if not ok:
            skipped.append({"physical_qubits": qubits, "reason": why})
            continue
        scored.append(ps.score_patch(ops, qc.num_qubits, qc.num_clbits, mp, rec, a))
    if not scored:
        return None
    scored.sort(key=ps.rank_key)
    for i, e in enumerate(scored):
        e["rank"] = i + 1
    return {"n_embeddings": len(embs), "n_scored": len(scored), "n_skipped": len(skipped),
            "best": scored[0], "incumbent": None,
            "gain": {"f_dd_off_best_over_incumbent": None, "incumbent_rank": None},
            "candidates": scored[:top],
            "skipped_examples": skipped[:5],
            "objective": ps.OBJECTIVE, "tie_break": ps.TIE_BREAK}


def run_patch_select(record_path, name, top, limit, md_path, json_path):
    """`scripts/h0_patch_select.py` as a subprocess: the in-flight script, unmodified."""
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "h0_patch_select.py"),
           "--calibration", record_path, "--top", str(top),
           "--out", json_path, "--md", md_path]
    if limit:
        cmd += ["--limit", str(limit)]
    print("    " + " ".join(os.path.relpath(c, ROOT) if c.startswith(ROOT) else c for c in cmd),
          flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stdout + r.stderr)[-2000:]
    with open(os.path.join(ROOT, json_path)) as fh:
        return json.load(fh), None


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--devices", nargs="*", default=list(DEFAULT_DEVICES))
    ap.add_argument("--outdir", default=DEFAULT_OUTDIR)
    ap.add_argument("--prep", default=DEFAULT_PREP)
    ap.add_argument("--circuit", default="B0_ref06_k1_rep1",
                    help="the frozen circuit whose interaction tree is embedded")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-patch-select", action="store_true")
    ap.add_argument("--not-attempted", nargs="*", default=None, metavar="DEVICE",
                    help="device names this run did NOT try to read, recorded with "
                         "--not-attempted-reason so that the survey says what is still owed")
    ap.add_argument("--not-attempted-reason", default="not attempted in this run")
    ap.add_argument("--out", default=os.path.join("data", "H0_device_survey_20260922.json"))
    ap.add_argument("--md", default=os.path.join("reports", "H0_device_survey_20260922.md"))
    args = ap.parse_args()
    t0 = time.time()

    prep = args.prep if os.path.isabs(args.prep) else os.path.join(ROOT, args.prep)
    outdir = args.outdir if os.path.isabs(args.outdir) else os.path.join(ROOT, args.outdir)
    os.makedirs(outdir, exist_ok=True)
    index = load_index(prep)
    g2 = index["common"]["g2"]
    M = Model(int(index["common"]["lattice"].split("x")[1]))

    devices, unreachable = [], []
    for name in (args.not_attempted or []):
        unreachable.append({"device": name, "attempted": False,
                            "reason": args.not_attempted_reason})
    for name in args.devices:
        print(f"[{name}] full-device calibration record ...", flush=True)
        try:
            rec = full_device_record(name)
        except BaseException as exc:                # SystemExit included: a name we cannot read
            print(f"    UNREACHABLE: {exc}", flush=True)
            unreachable.append({"device": name, "attempted": True,
                                "reason": str(exc)[:600]})
            continue
        path = os.path.join(outdir, f"{rec['backend']}_{rec['stamp']}.json")
        with open(path, "w") as fh:
            json.dump(rec, fh, indent=1)
        rel = os.path.relpath(path, ROOT)
        stats = t2_statistics(rec)
        comps = [components(rec, L) for L in T2_MINS_US]
        # the same search WITHOUT the CZ ceiling: that is the variant P12 of the planner
        # analysis reported ([41, 33, 19] at 40 us on the FakeFez snapshot, etc.), and it is
        # kept next to the prompt's readout+CZ variant so that the two can be told apart
        comps_ro = [components(rec, L, cz_max=1.0) for L in T2_MINS_US]
        print(f"    {rec['survey']['kind']}; {stats['n_qubits']} qubits, "
              f"{len(host_edges(rec))} undirected edges, T2 median "
              f"{stats['T2_percentiles_us']['50']:.1f} us -> {rel}", flush=True)
        entry = {"device": name, "backend": rec["backend"],
                 "record": rel, "fingerprint": rec["fingerprint"],
                 "stamp": rec["stamp"], "last_update_date": rec["last_update_date"],
                 "source": rec["survey"], "num_qubits": rec["num_qubits"],
                 "n_undirected_edges": len(host_edges(rec)),
                 "dt_s": rec["dt_s"], "default_rep_delay_s": rec["default_rep_delay_s"],
                 "n_missing_errors": len(rec["missing_errors"]),
                 "t2_statistics": stats, "components": comps,
                 "components_readout_only": comps_ro,
                 "components_note": ("`components` applies the prompt's E2 criteria (readout "
                                     "error <= 3 %, CZ error <= 1 %, T2 >= the floor); "
                                     "`components_readout_only` drops the CZ ceiling and is "
                                     "the variant P12 of the planner analysis reported")}
        if stats["fraction_without_T2"] and stats["fraction_without_T2"] > 0.10:
            entry["warning"] = (f"{100 * stats['fraction_without_T2']:.0f} % of the qubits have "
                                f"no T2 in this target: prompts/20 E1 escalation")

        if not args.no_patch_select:
            md = os.path.join("reports", f"H0_patch_select_{rec['backend']}_20260922.md")
            js = os.path.join("data", f"H0_patch_select_{rec['backend']}_20260922.json")
            res, err = run_patch_select(rel, rec["backend"], args.top, args.limit, md, js)
            fallback = None
            if res is None:
                entry["patch_select_error"] = err
                fallback = patch_search_without_the_incumbent(rec, prep, args.circuit, args.top)
                if fallback is not None:
                    print(f"    h0_patch_select.py refused on this record; its own search "
                          f"functions were called directly instead (no incumbent check)",
                          flush=True)
            if res is not None or fallback is not None:
                src = res["sources"][0]["result"] if res is not None else fallback
                best, inc = src["best"], src["incumbent"]
                rep_delay = rec["default_rep_delay_s"] or REP_DELAY_DEFAULT
                T, mans, cals = frozen_durations(prep, rec)
                P = ideal_p(M, mans, g2)
                f = float(best["f_dd_off"])
                b3 = d3_budget(P, T, mans, cals, f, rep_delay)
                b3["p11_interpolated_execution_s"] = p11_interpolated(f)
                b3pp = d3pp_budget(T, mans, cals, f, rep_delay)
                qt2 = sorted(((int(q), rec["qubits"][str(q)]["T2_s"])
                              for q in best["physical_qubits"]), key=lambda kv: kv[1])
                entry["patch_select"] = {
                    "json": (js if res is not None else None),
                    "md": (md if res is not None else None),
                    "n_candidates": src["n_scored"],
                    "n_skipped_not_covered_by_the_record": src.get("n_skipped"),
                    "objective": (res["objective"] if res is not None else src["objective"]),
                    "tie_break": (res["tie_break"] if res is not None else src["tie_break"]),
                    "method": ("scripts/h0_patch_select.py, run unmodified as a subprocess"
                               if res is not None else
                               "scripts/h0_patch_select.py's own enumerate_embeddings / "
                               "score_patch / rank_key called directly, because search() "
                               "refused on this record (see patch_select_error): the identity "
                               "embedding cannot be scored, so the incumbent comparison and "
                               "the h0_idle_model consistency check are NOT available"),
                    "incumbent_is_the_patch_this_set_was_transpiled_onto": bool(
                        str(rec["backend"]).replace("fake_", "").replace("ibm_", "") ==
                        str(index["common"]["backend"]).replace("Fake", "").lower()),
                    "winner": {
                        "physical_qubits": best["physical_qubits"],
                        "mapping": best["mapping"],
                        "f_gates": best["f_gates"], "f_pta_clean": f,
                        "S_T1": best["S_T1"], "S_T2": best["S_T2"],
                        "S_idle": best["S_T1"] + best["S_T2"],
                        "T_total_s": best["T_total_s"], "idle_s": best["idle_s"],
                        "min_T2_s": best["min_T2_s"], "min_T1_s": best["min_T1_s"],
                        "worst_qubit": best["worst_qubit"],
                        "weakest_three_qubits_by_T2": [
                            {"qubit": q, "T2_us": (v * 1e6 if v else None)} for q, v in qt2[:3]],
                    },
                    "incumbent_patch_of_the_transpiler": (None if inc is None else {
                        "physical_qubits": inc["physical_qubits"],
                        "f_pta_clean": inc["f_dd_off"], "f_gates": inc["f_gates"],
                        "rank": src["gain"]["incumbent_rank"],
                        "meaning": ("the gain is a like-for-like comparison only on the device "
                                    "the frozen set was transpiled onto; on any other device "
                                    "the identity embedding is just the same twelve qubit "
                                    "NUMBERS, not a layout that device's transpiler chose"),
                    }),
                    "gain_over_incumbent": src["gain"]["f_dd_off_best_over_incumbent"],
                    "budget_D3prime_echo_end": b3,
                    "budget_D3primeprime_H0_echo_end": b3pp,
                    "budgets_note": (
                        "both budgets are the ECHO-T2 end: the patch score uses the record's "
                        "Hahn-echo T2 because the free-induction T2* of the selected patch is "
                        "unknown before the pilot.  On patch 1 the measured in-circuit budget "
                        "was 1.73x the echo-PTA value (S_eff 5.76 against S_echo 3.32), and "
                        "whether that ratio transfers to a high-T2 patch is not known.  The "
                        "durations are the frozen circuits' own on this record; a re-freeze on "
                        "the winning patch (decision D1') would move them."),
                }
                g = src["gain"]["f_dd_off_best_over_incumbent"]
                print(f"    winner {best['physical_qubits']} f {f:.4e} "
                      + (f"({g:.2f}x over the transpiler's, rank "
                         f"{src['gain']['incumbent_rank']})" if g else
                         "(no incumbent comparison on this record)")
                      + f"; D3' {b3['execution_s']:.0f} s, "
                        f"D3''-H0 {b3pp['execution_s']:.0f} s", flush=True)
        devices.append(entry)

    res = {
        "script": "scripts/h0_device_survey.py",
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "qpu_seconds": 0,
        "requested_devices": list(args.devices),
        "outdir": os.path.relpath(outdir, ROOT),
        "prep": os.path.relpath(prep, ROOT),
        "criteria_of_the_component_search": {
            "readout_error_max": READOUT_MAX, "cz_error_max": CZ_MAX,
            "T2_min_us": list(T2_MINS_US),
            "method": "breadth-first search over the coupling map; no networkx",
        },
        "budget_inputs": {
            "D3prime": {"floor": D3_FLOOR, "margin": D3_MARGIN, "round_to": D3_ROUND,
                        "lambda_star": poisson_lambda_star(D3_K, D3_CONF),
                        "reps_shots": {str(k): v for k, v in D3_REPS_SHOTS.items()},
                        "calibration_circuits": D3PP_CAL_CIRCUITS,
                        "calibration_shots": D3_CAL_SHOTS},
            "D3primeprime_H0": {"shots_per_k1_circuit": f"{D3PP_SHOTS_PER_INVERSE_F:.0f} / f_clean",
                                "other_r1_shots": D3_FLOOR,
                                "reps_shots": {str(k): v for k, v in D3_REPS_SHOTS.items()},
                                "calibration_circuits": D3PP_CAL_CIRCUITS,
                                "calibration_shots": D3_CAL_SHOTS},
            "readout_factor": READOUT_FACTOR,
        },
        "devices": devices,
        "unreachable": unreachable,
        "runtime_s": time.time() - t0,
    }
    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"wrote {os.path.relpath(out, ROOT)}")
    if args.md:
        with open(out) as fh:                      # the report is rendered FROM the JSON
            saved = json.load(fh)
        saved["json"] = os.path.relpath(out, ROOT)
        write_report(os.path.basename(args.md), report_text(saved))
    print(f"{time.time() - t0:.0f} s, 0 QPU seconds")
    return 0


def report_text(D):
    trows = []
    for d in D["devices"]:
        s = d["t2_statistics"]
        trows.append([d["backend"], d["source"]["kind"].split("(")[0].strip(),
                      d["last_update_date"], s["n_qubits"], d["n_undirected_edges"],
                      *[f"{s['T2_percentiles_us'][str(p)]:.1f}" for p in PERCENTILES],
                      *[f"{100 * s['fraction_T2_at_least'][str(L)]:.0f} %"
                        for L in T2_FRACTION_LEVELS_US],
                      d["n_missing_errors"]])
    crows = []
    for d in D["devices"]:
        for c, cro in zip(d["components"], d.get("components_readout_only") or d["components"]):
            crows.append([d["backend"], c["t2_min_us"], c["n_good_qubits"], c["n_components"],
                          str(c["largest_sizes"]), c["components_of_at_least_12"],
                          str(cro["largest_sizes"]), cro["components_of_at_least_12"]])
    wrows, brows = [], []
    for d in D["devices"]:
        ps = d.get("patch_select")
        if not ps:
            wrows.append([d["backend"], "-", "-", "-", "-", "-", "-", "-", "-",
                          d.get("patch_select_error", "not run")[:40]])
            continue
        w = ps["winner"]
        wrows.append([d["backend"], ps["n_candidates"], str(w["physical_qubits"]),
                      f"{w['f_gates']:.4e}", f"{w['f_pta_clean']:.4e}",
                      f"{w['S_T1']:.3f}", f"{w['S_T2']:.3f}", f"{w['S_idle']:.3f}",
                      f"{w['T_total_s'] * 1e6:.2f}",
                      ", ".join(f"{x['qubit']} ({x['T2_us']:.1f})"
                                for x in w["weakest_three_qubits_by_T2"])])
        b3, bp = ps["budget_D3prime_echo_end"], ps["budget_D3primeprime_H0_echo_end"]
        brows.append([d["backend"], f"{w['f_pta_clean']:.4e}",
                      ("-" if not ps.get("incumbent_patch_of_the_transpiler") else
                       f"{ps['incumbent_patch_of_the_transpiler']['f_pta_clean']:.4e}"),
                      ("-" if not ps.get("gain_over_incumbent") else
                       f"{ps['gain_over_incumbent']:.2f}x"),
                      str(b3["N4"]), b3["total_coarse_shots"], f"{b3['execution_s']:.0f}",
                      f"{b3['p11_interpolated_execution_s']:.0f}",
                      bp["shots_per_k1_circuit"], bp["total_coarse_shots"],
                      f"{bp['execution_s']:.0f}"])
    best = None
    for d in D["devices"]:
        ps = d.get("patch_select")
        if ps and (best is None or
                   ps["winner"]["f_pta_clean"] > best[1]["winner"]["f_pta_clean"]):
            best = (d, ps)
    if best is None:
        sentence = ("No device could be searched in this run, so there is no recommendation: "
                    "see the unreachable table above.")
    else:
        d, ps = best
        b3, bp = ps["budget_D3prime_echo_end"], ps["budget_D3primeprime_H0_echo_end"]
        gtxt = (f", {ps['gain_over_incumbent']:.2f}x the patch the transpiler picked on the "
                f"same record" if ps.get("gain_over_incumbent") else
                ", with no incumbent comparison available on that record")
        sentence = (
            f"**The best patch of the surveyed records is `{d['backend']}` "
            f"{ps['winner']['physical_qubits']}**, with an echo-end PTA clean f of "
            f"**{ps['winner']['f_pta_clean']:.4e}** (S_idle {ps['winner']['S_idle']:.2f}"
            f"{gtxt}).  At that f the plan costs **{b3['execution_s']:.0f} s** of execution "
            f"under rule D3' as it stands and **{bp['execution_s']:.0f} s** under the owner's "
            f"D3''-H0 sizing ({bp['shots_per_k1_circuit']} shots per k = 1 circuit).  Both "
            f"figures are the ECHO-T2 end.  On the patch that flew, the measured in-circuit "
            f"error budget was **1.73x** the echo-PTA value (S_eff 5.76 against S_echo 3.32, "
            f"`reports/H0_replan_planner_analysis_20260922.md` section 2), and the "
            f"free-induction T2* of any of these patches is **unknown until the pilot** "
            f"measures it.  Nothing here narrows that: T2* need not scale with the echo T2.")
    urows = [[u["device"], "yes" if u.get("attempted") else "no", u["reason"][:260]]
             for u in D["unreachable"]]
    methods = "\n".join(
        f"* `{d['backend']}`: {d['patch_select']['method']}"
        + (f"  Refusal: `{(d.get('patch_select_error') or '').strip().splitlines()[-1]}`"
           if d.get("patch_select_error") else "")
        for d in D["devices"] if d.get("patch_select"))
    return f"""# Device survey for the 2x2 H0 patch (prompts/20 part E)

`scripts/h0_device_survey.py`, {D['created']}.  {env_block()}
**{D['qpu_seconds']} QPU seconds**: a calibration record is target / properties / status
metadata, and an offline snapshot needs no account at all.  Runtime {D['runtime_s']:.0f} s.
Every number below is in `{D.get('json')}` or in the per-device records under
`{D['outdir']}`.  The patch searches are `scripts/h0_patch_select.py` run unmodified; each
device for which it produced a result has its own JSON and report, and the `method` field of
every entry says which route was taken.

Requested devices: {', '.join(D['requested_devices'])}.

{('## Devices that could not be surveyed' + chr(10) + chr(10) + md_table(["device", "attempted", "reason"], urows) + chr(10)) if urows else ''}
## 1. T2 geography (part E2)

{md_table(["device", "record", "calibration", "qubits", "edges",
           *[f"T2 p{p} (us)" for p in PERCENTILES],
           *[f"T2 >= {L} us" for L in T2_FRACTION_LEVELS_US], "missing errors"], trows)}

## 2. Where a twelve-qubit tree can live (part E2)

Connected components of the subgraph with readout error <=
{100 * D['criteria_of_the_component_search']['readout_error_max']:.0f} %, CZ error <=
{100 * D['criteria_of_the_component_search']['cz_error_max']:.0f} % and T2 above the stated
floor.  The frozen coarse step needs a connected 12-qubit region, so the last column is the
one that decides whether a floor is reachable at all.

{md_table(["device", "T2 floor (us)", "good qubits", "components", "four largest",
           "components >= 12", "four largest, readout filter only",
           ">= 12, readout filter only"], crows)}

The last two columns drop the CZ ceiling and keep only the readout and T2 filters: that is the
variant P12 of `reports/H0_replan_planner_analysis_20260922.md` reported, and reproducing it
([41, 33, 19] at 40 us on the FakeFez snapshot, [21, 11, 11, 11] at 60, [17, 8, 7] at 80,
[6, 5, 4] at 100, [5, 4, 4] at 120, [3, 3, 2] at 150) is the check that the search is the same
one.  The columns before them are the prompt's stricter criteria.

## 3. The winning patch per device (part E3)

The exhaustive embedding search of `scripts/h0_patch_select.py`: every injective map of the
frozen coarse step's 12-node CZ interaction tree into the device coupling graph, scored by
f_gates x exp(-S_T1 - S_T2) on the record's T1 and Hahn-echo T2.  Same circuit, different
qubits: no re-routing and no second transpiler solution.

{methods}

{md_table(["device", "candidates", "winning qubits", "f_gates", "PTA clean f", "S_T1", "S_T2",
           "S_idle", "duration (us)", "weakest three qubits by T2 (us)"], wrows)}

## 4. The two budgets at the winner's f (part E3)

{md_table(["device", "PTA clean f (winner)", "PTA clean f (transpiler's patch)", "gain",
           "D3' N4 per sector", "D3' coarse shots", "D3' execution (s)",
           "D3' execution, P11 interpolated (s)", "D3''-H0 shots per k = 1 circuit",
           "D3''-H0 coarse shots", "D3''-H0 execution (s)"], brows)}

The "P11 interpolated" column is the planner's own table of
`reports/H0_replan_planner_analysis_20260922.md` interpolated linearly in 1/f; the column
before it is computed here from the rule itself (`h0_support_plan.n4_of_sector`, floor
{D['budget_inputs']['D3prime']['floor']}, margin {D['budget_inputs']['D3prime']['margin']},
lambda* {D['budget_inputs']['D3prime']['lambda_star']:.4f}) on this record's own durations.
The two agreeing is the check that neither is a typing error.

## 5. What the owner needs in one paragraph

{sentence}
"""


if __name__ == "__main__":
    sys.exit(main())
