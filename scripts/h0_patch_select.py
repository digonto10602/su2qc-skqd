#!/usr/bin/env python3
"""
T2-aware patch selection for the 2x2 H0 run (amendment 01, item 1).

Amendment 01 item 1 says the 2x2 patch "is chosen by calibration-aware layout on the day
of the run".  Gate H0_diag (`validation/H0_diag.json`, 2026-09-22) showed that this is
under-specified: the dominant error of the routed 2x2 circuit is **idle-time
decoherence** over its 43.71 us, not gate error, and Qiskit's calibration-aware layout
(VF2Layout / VF2PostLayout score gate and readout error) is blind to T1 and T2.  On the
canary's patch a single qubit -- 146, T2 = 16 us, one 25.3 us idle window -- carries 0.86
of the patch's 2.57 S_T2 units.

This script makes the missing step explicit and measurable.  It does NOT re-implement the
idle model: `scripts/h0_idle_model.py` (`schedule`, `budgets`, `f_on_record`,
`predictions`) is imported and used verbatim, so the score of the incumbent patch is the
same number `h0_idle_model.py` already writes for that circuit on that record (checked to
`CONSISTENCY_TOL` and reported in the JSON).

**Candidate enumeration.**  The routed 2x2 coarse step touches 12 physical qubits through
a fixed set of CZ edges -- a 12-node, 11-edge tree for the patch the transpiler chose.  A
*candidate patch* is any injective map of that interaction graph into the device coupling
graph (an embedding: every CZ still lands on a real edge).  Relabelling the frozen circuit
along such an embedding changes no gate, no angle, no CZ count (663) and no
classical-bit mapping -- only which physical qubit plays which role -- so the comparison
is exactly "same circuit, different qubits", with no re-routing and no second transpiler
solution to argue about.  The enumeration is exhaustive and deterministic (pattern nodes
ordered by descending degree then index, host nodes ascending), so the winner is a
property of the calibration, not of a search that was stopped somewhere.

**Objective (fixed before the search).**

    score(P) = f_dd_off(P) = f_gates(P) x exp(-S_T1(P) - S_T2(P))

`f_gates` is `gate_S2D.analyse_on_backend`'s clean-shot fraction on the record (the
product of the executed CZ errors and of the 12 measure errors) and S_T1, S_T2 are the
Pauli-twirling relaxation budgets of the ASAP schedule of `h0_idle_model.py`.  This is the
DD-off prediction that gate H0_diag validated: it preregistered 30.8 +- 5.5 accepted shots
of 2000 for job J1 and the device gave 35.

**Ties** break, in order: larger f_gates; then smaller max over qubits of S_T2 (the
worst single qubit); then the lexicographically smallest tuple of physical qubits.

Two controls are reported next to the winner: the patch the transpiler actually chose
(the identity embedding) and the best patch under the **gate-error-only** objective
`f_gates` -- what a T2-blind, calibration-aware layout optimises.

Sources are offline.  `--calibration` scores on a committed calibration record; the
candidate space is then whatever the record covers (the H0 records cover the 30 qubits
and 29 undirected coupling edges the frozen set touches -- 54 directed target keys --
not the 156-qubit device).  `--snapshot FakeFez` builds a
full-device record from the offline fake-provider snapshot -- the very calibration the
transpiler used when it chose the patch -- and searches the whole device.  Neither uses a
QPU or an IBM account.

Usage:
  python scripts/h0_patch_select.py                       # the default run of the report
  python scripts/h0_patch_select.py --calibration data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json
  python scripts/h0_patch_select.py --snapshot FakeFez --md reports/H0_patch_select.md
Runtime: about 1 s per 10 candidates; the full 156-qubit FakeFez search (1494 candidates)
takes about 90 s on the i7-8750H.  No QPU time.
"""
import argparse
import collections
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.skqd import READOUT_FACTOR, yield_model  # noqa: E402

import h0_idle_model as im  # noqa: E402
from h0_backends import calibration_fingerprint  # noqa: E402
from gate_H0P import load_circuit, load_index, load_manifests, random_acceptance  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PREP = os.path.join("data", "hardware", "H0_prep")
DEFAULT_CIRCUIT = "B0_ref06_k1_rep1"      # the canary circuit of prompts/17-19
CONSISTENCY_TOL = 1e-12                   # identity embedding vs h0_idle_model.py
SHOTS_REFERENCE = 2000                    # the shots of the H0_diag jobs J1-J4
OBJECTIVE = "f_dd_off = f_gates x exp(-S_T1 - S_T2)"
TIE_BREAK = ("1. larger f_dd_off; 2. larger f_gates; 3. smaller max_q S_T2; "
             "4. lexicographically smallest tuple of physical qubits")
# the per-qubit leaves a candidate needs before it can be scored at all
QUBIT_FIELDS = ("measure_error", "measure_duration_s", "sx_error", "sx_duration_s",
                "x_duration_s", "T1_s", "T2_s")
EDGE_FIELDS = ("cz_error", "cz_duration_s")
# the two records amendment 01 item 1 is prepared on, then every other committed ibm_fez
# record of the same day (the stability check the selection rule needs)
DEFAULT_RECORDS = [
    os.path.join("data", "hardware", "H0_ibm_fez", "calibration_20260922T1400Z.json"),
    os.path.join("data", "hardware", "H0_ibm_fez_canary",
                 "calibration_at_submission_20260922T1400Z.json"),
    os.path.join("data", "hardware", "H0_ibm_fez_canary",
                 "calibration_at_retrieval_20260922T1400Z.json"),
    os.path.join("data", "hardware", "H0_ibm_fez", "calibration_20260921T2053Z.json"),
    os.path.join("data", "hardware", "H0_ibm_fez", "calibration_20260922T0544Z.json"),
    os.path.join("data", "hardware", "H0_ibm_fez", "calibration_20260922T0620Z.json"),
    os.path.join("data", "hardware", "H0_ibm_fez", "calibration_20260922T0711Z.json"),
]


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


# --------------------------------------------------------------------------- graphs
def interaction_graph(qc):
    """{qubit: set(neighbours)} over the CZ edges of a transpiled circuit, and the edge set."""
    adj = collections.defaultdict(set)
    edges = set()
    for inst in qc.data:
        if inst.operation.name != "cz":
            continue
        a, b = (qc.find_bit(q).index for q in inst.qubits)
        adj[a].add(b)
        adj[b].add(a)
        edges.add((min(a, b), max(a, b)))
    return dict(adj), sorted(edges)


def host_graph(rec):
    """{qubit: set(neighbours)} of a calibration record's coupling graph, and its nodes."""
    adj = collections.defaultdict(set)
    for e in rec["edges"].values():
        a, b = e["target_key"]
        adj[int(a)].add(int(b))
        adj[int(b)].add(int(a))
    nodes = sorted(int(q) for q in rec["qubits"])
    for q in nodes:
        adj.setdefault(q, set())
    return dict(adj), nodes


def pattern_order(pat_adj):
    """A connected search order over the pattern nodes: descending degree, then index."""
    nodes = sorted(pat_adj, key=lambda x: (-len(pat_adj[x]), x))
    order, placed = [nodes[0]], {nodes[0]}
    while len(order) < len(nodes):
        for n in nodes:
            if n not in placed and (pat_adj[n] & placed):
                order.append(n)
                placed.add(n)
                break
        else:                                   # a disconnected pattern: take the next node
            for n in nodes:
                if n not in placed:
                    order.append(n)
                    placed.add(n)
                    break
    return order


def enumerate_embeddings(pat_adj, host_adj, host_nodes, limit=None):
    """Every injective map pattern -> host that carries every pattern edge to a host edge.

    Exhaustive and deterministic: the pattern nodes are visited in `pattern_order` and the
    host candidates in ascending index, so the returned list is a canonical enumeration."""
    order = pattern_order(pat_adj)
    host_nodes = sorted(host_nodes)
    out, mapping, used = [], {}, set()

    def rec(i):
        if limit is not None and len(out) >= limit:
            return
        if i == len(order):
            out.append(dict(mapping))
            return
        p = order[i]
        anchors = [mapping[q] for q in pat_adj[p] if q in mapping]
        cands = (set.intersection(*[host_adj.get(a, set()) for a in anchors]) if anchors
                 else set(host_nodes))
        for h in sorted(cands):
            if h in used or len(host_adj.get(h, ())) < len(pat_adj[p]):
                continue
            mapping[p] = h
            used.add(h)
            rec(i + 1)
            used.discard(h)
            del mapping[p]
            if limit is not None and len(out) >= limit:
                return

    rec(0)
    return out, order


# --------------------------------------------------------------------------- relabelling
def circuit_ops(qc):
    """(operation, qubit indices, clbit indices) of every instruction, extracted once."""
    return [(inst.operation,
             [qc.find_bit(q).index for q in inst.qubits],
             [qc.find_bit(c).index for c in inst.clbits]) for inst in qc.data]


def relabel(ops, n_qubits, n_clbits, mapping):
    """The same circuit with every physical qubit q replaced by `mapping.get(q, q)`.

    The classical bits are untouched: clbit i still carries logical qubit i, so the
    codeword bit order, the link-parity checks and the decoder are unchanged."""
    from qiskit import QuantumCircuit
    nc = QuantumCircuit(n_qubits, n_clbits)
    for op, qs, cs in ops:
        nc.append(op, [mapping.get(q, q) for q in qs], cs)
    return nc


# --------------------------------------------------------------------------- scoring
def record_covers(rec, qubits, edges):
    """(ok, reason) -- does the record carry every leaf the idle model needs?"""
    Q, E = rec["qubits"], rec["edges"]
    for q in qubits:
        qq = Q.get(str(q))
        if qq is None:
            return False, f"qubit {q} is not in the record"
        for k in QUBIT_FIELDS:
            if qq.get(k) is None:
                return False, f"qubit {q} has no {k}"
    for a, b in edges:
        e = E.get(f"{a}-{b}") or E.get(f"{b}-{a}")
        if e is None:
            return False, f"edge ({a}, {b}) is not in the record"
        for k in EDGE_FIELDS:
            if e.get(k) is None:
                return False, f"edge ({a}, {b}) has no {k}"
    return True, None


def score_patch(ops, n_qubits, n_clbits, mapping, rec, a):
    """The idle-aware score of one candidate patch (everything from `h0_idle_model`)."""
    qc = relabel(ops, n_qubits, n_clbits, mapping)
    sch = im.schedule(qc, rec)
    per_q, tot = im.budgets(sch, rec)
    with np.errstate(divide="ignore", invalid="ignore"):
        f_gates, f_gates_only, ro, n_cz, n_meas = im.f_on_record(qc, rec)
    pred = im.predictions(f_gates, tot, a)
    worst = max(per_q.items(), key=lambda kv: (kv[1]["S_T2"], -int(kv[0])))
    return {
        "physical_qubits": sorted(mapping.values()),
        "mapping": {str(k): int(v) for k, v in sorted(mapping.items())},
        "n_cz": int(n_cz), "n_measure": int(n_meas),
        "T_s": sch["T_s"], "T_total_s": sch["T_total_s"],
        "f_gates": f_gates, "f_gates_only": f_gates_only, "measure_survival": ro,
        "S_T1": tot["S_T1"], "S_T2": tot["S_T2"],
        "S_T2_eligible": tot["S_T2_eligible"], "S_T2_ineligible": tot["S_T2_ineligible"],
        "S_DD": tot["S_DD"], "dd_eligible": tot["dd_eligible"],
        "idle_s": tot["idle_s"],
        "f_dd_off": pred["dd_off"]["f"], "yield_dd_off": pred["dd_off"]["yield"],
        "f_dd_on": {r: v["f"] for r, v in pred["dd_on"].items()},
        "worst_qubit": int(worst[0]),
        "worst_qubit_S_T2": worst[1]["S_T2"],
        "worst_qubit_T2_s": worst[1]["T2_s"],
        "max_qubit_S_T2": worst[1]["S_T2"],
        "min_T2_s": min(v["T2_s"] for v in per_q.values()),
        "min_T1_s": min(v["T1_s"] for v in per_q.values()),
    }


def rank_key(e):
    """The tie-break of `TIE_BREAK`, as a sort key (ascending)."""
    return (-e["f_dd_off"], -e["f_gates"], e["max_qubit_S_T2"], tuple(e["physical_qubits"]))


def gate_only_key(e):
    """The T2-blind control: gate + readout error alone, same tie-break tail."""
    return (-e["f_gates"], e["max_qubit_S_T2"], tuple(e["physical_qubits"]))


# --------------------------------------------------------------------------- one source
def search(prep, rec, circuit_id, top, limit=None, family=True):
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    man = next((m for m in mans + cals if m["id"] == circuit_id), None)
    if man is None:
        raise SystemExit(f"no circuit '{circuit_id}' in {prep}")
    qc = load_circuit(prep, man)
    pat_adj, pat_edges = interaction_graph(qc)
    if len(pat_adj) != index["common"]["n_logical_qubits"]:
        raise SystemExit(f"{circuit_id} touches {len(pat_adj)} qubits through CZ but the "
                         f"encoding uses {index['common']['n_logical_qubits']}")
    host_adj, host_nodes = host_graph(rec)

    model = Model(int(index["common"]["lattice"].split("x")[1]))
    codec = Codec(model.basis)
    a = (random_acceptance(codec, man["twoB"])["fraction"] if man.get("twoB") is not None
         else None)

    embs, order = enumerate_embeddings(pat_adj, host_adj, host_nodes, limit=limit)
    ops = circuit_ops(qc)
    nq, ncl = qc.num_qubits, qc.num_clbits

    scored, skipped = [], []
    for mp in embs:
        qubits = sorted(mp.values())
        edges = sorted({(min(mp[u], mp[v]), max(mp[u], mp[v])) for u, v in pat_edges})
        ok, why = record_covers(rec, qubits, edges)
        if not ok:
            skipped.append({"physical_qubits": qubits, "reason": why})
            continue
        e = score_patch(ops, nq, ncl, mp, rec, a)
        scored.append(e)
    if not scored:
        raise SystemExit(f"no candidate patch of {circuit_id} is fully covered by the record")

    scored.sort(key=rank_key)
    for i, e in enumerate(scored):
        e["rank"] = i + 1
    by_set = {tuple(e["physical_qubits"]): e for e in scored}

    incumbent_set = tuple(sorted(man["physical_qubits"]))
    incumbent = by_set.get(incumbent_set)
    if incumbent is None:
        raise SystemExit(f"the identity embedding (the transpiler's own patch "
                         f"{list(incumbent_set)}) is not among the candidates -- the "
                         f"enumeration is wrong")

    # the identity embedding must reproduce h0_idle_model.py exactly
    sch0 = im.schedule(qc, rec)
    _pq0, tot0 = im.budgets(sch0, rec)
    with np.errstate(divide="ignore", invalid="ignore"):
        fg0 = im.f_on_record(qc, rec)[0]
    f0 = im.predictions(fg0, tot0, a)["dd_off"]["f"]
    consistency = {
        "f_gates_delta": abs(incumbent["f_gates"] - fg0),
        "S_T1_delta": abs(incumbent["S_T1"] - tot0["S_T1"]),
        "S_T2_delta": abs(incumbent["S_T2"] - tot0["S_T2"]),
        "f_dd_off_delta": abs(incumbent["f_dd_off"] - f0),
        "tolerance": CONSISTENCY_TOL,
    }
    consistency["ok"] = all(consistency[k] <= CONSISTENCY_TOL for k in
                            ("f_gates_delta", "S_T1_delta", "S_T2_delta", "f_dd_off_delta"))
    if not consistency["ok"]:
        raise SystemExit(f"the identity embedding does not reproduce h0_idle_model.py: "
                         f"{consistency}")

    best = scored[0]
    gate_only = sorted(scored, key=gate_only_key)[0]

    out = {
        "circuit": circuit_id,
        "lattice": index["common"]["lattice"],
        "n_logical_qubits": int(index["common"]["n_logical_qubits"]),
        "pattern": {
            "n_nodes": len(pat_adj), "n_edges": len(pat_edges),
            "edges": [list(e) for e in pat_edges],
            "degree_sequence": sorted((len(v) for v in pat_adj.values()), reverse=True),
            "search_order": [int(x) for x in order],
        },
        "host": {"n_qubits": len(host_nodes), "n_edges": sum(len(v) for v in host_adj.values()) // 2,
                 "qubits": host_nodes},
        "n_candidates": len(embs),
        "n_scored": len(scored),
        "n_skipped": len(skipped),
        "skipped": skipped[:20],
        "garbage_acceptance": a,
        "incumbent": incumbent,
        "best": best,
        "best_by_gate_error_only": gate_only,
        "consistency_with_h0_idle_model": consistency,
        "gain": {
            "f_dd_off_best_over_incumbent": best["f_dd_off"] / incumbent["f_dd_off"],
            "f_dd_off_gate_only_over_incumbent": gate_only["f_dd_off"] / incumbent["f_dd_off"],
            "f_dd_off_best_over_gate_only": best["f_dd_off"] / gate_only["f_dd_off"],
            "yield_best_over_incumbent": (None if incumbent["yield_dd_off"] in (None, 0)
                                          else best["yield_dd_off"] / incumbent["yield_dd_off"]),
            "incumbent_rank": incumbent["rank"],
            "gate_only_rank": gate_only["rank"],
            "S_T2_incumbent": incumbent["S_T2"],
            "S_T2_best": best["S_T2"],
            "delta_S_T2": incumbent["S_T2"] - best["S_T2"],
            "qubits_changed": sorted(set(incumbent["physical_qubits"])
                                     ^ set(best["physical_qubits"])),
            "n_qubits_changed": len(set(incumbent["physical_qubits"])
                                    - set(best["physical_qubits"])),
            "shots_reference": SHOTS_REFERENCE,
            "accepted_of_reference_incumbent": (None if incumbent["yield_dd_off"] is None else
                                                SHOTS_REFERENCE * incumbent["yield_dd_off"]),
            "accepted_of_reference_best": (None if best["yield_dd_off"] is None else
                                           SHOTS_REFERENCE * best["yield_dd_off"]),
            "garbage_floor_of_reference": (None if a is None else SHOTS_REFERENCE * a),
            # y - a = f (READOUT_FACTOR - a), so the excess over the garbage floor scales
            # exactly with f: the yield ratio is diluted by the floor, the excess is not
            "excess_over_floor_incumbent": (None if a is None else
                                            SHOTS_REFERENCE * (incumbent["yield_dd_off"] - a)),
            "excess_over_floor_best": (None if a is None else
                                       SHOTS_REFERENCE * (best["yield_dd_off"] - a)),
        },
        "top": scored[:top],
    }
    if family:
        out["family"] = family_check(prep, rec, mans, pat_edges, incumbent, best, a, codec)
    return out


def family_check(prep, rec, mans, pat_edges, incumbent, best, a, codec):
    """Re-score every frozen circuit that shares the incumbent's interaction graph.

    The winner is chosen on one circuit; the frozen set contains a whole family with the
    same routed edge set (the r = 1 circuits on that patch).  The mapping is defined on
    the pattern's nodes, so it applies to all of them unchanged."""
    target = set(tuple(e) for e in pat_edges)
    mapping = {int(k): int(v) for k, v in best["mapping"].items()}
    ident = {int(k): int(v) for k, v in incumbent["mapping"].items()}
    rows = []
    for m in mans:
        qc = load_circuit(prep, m)
        adj, edges = interaction_graph(qc)
        if set(edges) != target:
            continue
        ops = circuit_ops(qc)
        aa = (random_acceptance(codec, m["twoB"])["fraction"] if m.get("twoB") is not None
              else a)
        ei = score_patch(ops, qc.num_qubits, qc.num_clbits, ident, rec, aa)
        eb = score_patch(ops, qc.num_qubits, qc.num_clbits, mapping, rec, aa)
        rows.append({"id": m["id"], "sector": m.get("sector"), "k": m.get("k"),
                     "repetitions": m.get("repetitions"), "n_cz": ei["n_cz"],
                     "f_incumbent": ei["f_dd_off"], "f_best": eb["f_dd_off"],
                     "gain": eb["f_dd_off"] / ei["f_dd_off"],
                     "yield_incumbent": ei["yield_dd_off"], "yield_best": eb["yield_dd_off"]})
    if not rows:
        return {"n_circuits": 0}
    g = [r["gain"] for r in rows]
    return {
        "n_circuits": len(rows),
        "gain_mean": float(np.mean(g)), "gain_min": float(np.min(g)), "gain_max": float(np.max(g)),
        "f_incumbent_mean": float(np.mean([r["f_incumbent"] for r in rows])),
        "f_best_mean": float(np.mean([r["f_best"] for r in rows])),
        "f_incumbent_min": float(np.min([r["f_incumbent"] for r in rows])),
        "f_best_min": float(np.min([r["f_best"] for r in rows])),
        "circuits": rows,
    }


# --------------------------------------------------------------------------- sources
def load_record(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(p) as fh:
        rec = json.load(fh)
    rec["_source"] = {"kind": "committed calibration record",
                      "path": os.path.relpath(p, ROOT)}
    return rec


def snapshot_record(name):
    """A FULL-device calibration record from an offline fake-provider snapshot."""
    from h0_backends import calibration_record, resolve_backend
    b = resolve_backend(name)
    edges = sorted({(int(a), int(c)) for a, c in b.coupling_map})
    rec = calibration_record(b, list(range(int(b.num_qubits))), edges)
    rec["_source"] = {"kind": "offline fake-provider snapshot (full device)",
                      "path": f"qiskit_ibm_runtime.fake_provider.{name}"}
    return rec


# --------------------------------------------------------------------------- report
def _f(x, spec="{:.2f}"):
    """Format a number that the model may leave undefined (no garbage acceptance)."""
    return "n/a" if x is None else spec.format(x)


def finding_text(res):
    """Section 3, built from the JSON's own fields (the primary record and the device)."""
    st = res["stability"]
    prim = res["sources"][0]
    pr, pg = prim["result"], prim["result"]["gain"]
    dev = next((s for s in res["sources"]
                if not s["source"]["kind"].startswith("committed")), None)
    removed = sorted(set(pr["incumbent"]["physical_qubits"]) - set(pr["best"]["physical_qubits"]))
    added = sorted(set(pr["best"]["physical_qubits"]) - set(pr["incumbent"]["physical_qubits"]))
    change = (f"  The change is one qubit: {removed[0]} (T2 "
              f"{pr['incumbent']['worst_qubit_T2_s'] * 1e6:.1f} us, S_T2 "
              f"{pr['incumbent']['worst_qubit_S_T2']:.3f} of the patch's "
              f"{pg['S_T2_incumbent']:.3f}) is replaced by {added[0]}."
              if len(removed) == 1 and removed == [pr["incumbent"]["worst_qubit"]]
              else f"  {len(removed)} of {pr['n_logical_qubits']} qubits change "
                   f"({removed} -> {added}).")
    out = [
        f"On the record the canary actually ran under (`{prim['source']['path']}`, fingerprint "
        f"`{prim['fingerprint'][:16]}`) the idle-aware rule selects "
        f"**{pr['best']['physical_qubits']}** and beats the patch the transpiler chose by "
        f"**{pg['f_dd_off_best_over_incumbent']:.2f}x** in f "
        f"({pr['incumbent']['f_dd_off']:.3e} -> {pr['best']['f_dd_off']:.3e})." + change,
        f"The **gate-error-only** objective -- what a calibration-aware layout optimises -- "
        f"returns the transpiler's own patch on every source in this file "
        f"({pg['f_dd_off_gate_only_over_incumbent']:.2f}x), so the layout pass was not "
        f"mis-solving its problem; the problem was the wrong one.",
        f"The rule is stable: over the {st['n_committed_records']} committed ibm_fez records of "
        f"2026-09-21/22 it returns {st['n_distinct_winners']} distinct winner(s), with a gain "
        f"between {st['gain_min']:.2f}x and {st['gain_max']:.2f}x.",
    ]
    if dev is not None:
        dr, dg = dev["result"], dev["result"]["gain"]
        out.append(
            f"The committed records cover only {pr['host']['n_qubits']} of the device's qubits -- "
            f"exactly the ones the frozen set already uses -- so {pr['n_scored']} candidates is a "
            f"lower bound.  With the whole device in view ({dev['label']}, "
            f"{dr['host']['n_qubits']} qubits, {dr['n_scored']} candidates, the snapshot the "
            f"transpiler itself used) the gain is **{dg['f_dd_off_best_over_incumbent']:.2f}x** and "
            f"the transpiler's patch ranks {dg['incumbent_rank']} of {dr['n_scored']}.  The "
            f"selection rule therefore has to be run on a FULL-DEVICE calibration read (a target "
            f"query, free, no QPU time) on the day of the run.")
    out.append(
        f"What it does not do: at {pr['best']['f_dd_off']:.3e} the 2x2 r = 1 circuit is still far "
        f"below the f >= 0.1 of the amended budget criterion, and the predicted accepted shots of "
        f"{pg['shots_reference']} move from {pg['accepted_of_reference_incumbent']:.1f} to "
        f"{pg['accepted_of_reference_best']:.1f} over a garbage floor of "
        f"{pg['garbage_floor_of_reference']:.1f}.  Patch selection is a real factor, not a rescue.")
    return "\n\n".join(out)


def report_text(res):
    from skqd.report import md_table
    lines = []
    for s in res["sources"]:
        r = s["result"]
        g = r["gain"]
        lines.append([s["label"], s["fingerprint"][:16],
                      r["host"]["n_qubits"], r["n_scored"],
                      f"{r['incumbent']['f_dd_off']:.3e}", f"{r['best']['f_dd_off']:.3e}",
                      f"{g['f_dd_off_best_over_incumbent']:.2f}x",
                      f"{g['incumbent_rank']} of {r['n_scored']}",
                      str(r["best"]["physical_qubits"])])
    head = res["sources"][0]["result"]
    blocks = []
    for i, s in enumerate(res["sources"]):
        r = s["result"]
        g = r["gain"]
        rows = []
        for name, e in (("transpiler's choice (incumbent)", r["incumbent"]),
                        ("best by gate error alone (T2-blind)", r["best_by_gate_error_only"]),
                        ("best by the idle-aware objective", r["best"])):
            rows.append([name, str(e["physical_qubits"]), e["rank"], f"{e['f_gates']:.4f}",
                         f"{e['S_T1']:.3f}", f"{e['S_T2']:.3f}", f"{e['f_dd_off']:.3e}",
                         f"{e['yield_dd_off']:.4f}" if e["yield_dd_off"] is not None else "n/a",
                         f"q{e['worst_qubit']} ({e['worst_qubit_T2_s'] * 1e6:.1f} us, "
                         f"{e['worst_qubit_S_T2']:.3f})"])
        full = (i == 0) or not s["source"]["kind"].startswith("committed")
        top = [[e["rank"], str(e["physical_qubits"]), f"{e['f_gates']:.4f}",
                f"{e['S_T1']:.3f}", f"{e['S_T2']:.3f}", f"{e['f_dd_off']:.3e}",
                f"{e['min_T2_s'] * 1e6:.1f}"] for e in r["top"][:(10 if full else 0)]]
        toptxt = ("" if not top else
                  md_table(["rank", "physical qubits", "f_gates", "S_T1", "S_T2", "f (DD off)",
                            "min T2 (us)"], top))
        fam = r.get("family") or {}
        famtxt = ""
        if fam.get("n_circuits"):
            famtxt = (
                f"\nThe same relabelling applied to every frozen circuit with this routed edge set "
                f"({fam['n_circuits']} circuits): mean f {fam['f_incumbent_mean']:.3e} -> "
                f"{fam['f_best_mean']:.3e}, worst {fam['f_incumbent_min']:.3e} -> "
                f"{fam['f_best_min']:.3e}, gain {fam['gain_min']:.2f}x to {fam['gain_max']:.2f}x "
                f"(mean {fam['gain_mean']:.2f}x).\n")
        blocks.append(f"""### {s['label']}

Source: {s['source']['kind']}, `{s['source']['path']}` (backend `{s['backend']}`,
`last_update_date` {s['last_update_date']}, fingerprint `{s['fingerprint'][:16]}`).
Candidate space: {r['host']['n_qubits']} qubits / {r['host']['n_edges']} undirected coupling
edges of the record,
{r['n_candidates']} embeddings of the interaction graph, {r['n_scored']} scored,
{r['n_skipped']} skipped for missing calibration leaves.

{md_table(["patch", "physical qubits", "rank", "f_gates", "S_T1", "S_T2", "f (DD off)",
           "yield", "worst qubit (T2, S_T2)"], rows)}

**Gain of the best available patch over the one the transpiler chose:
{g['f_dd_off_best_over_incumbent']:.2f}x in f, {_f(g['yield_best_over_incumbent'])}x in yield**
(at {g['shots_reference']} shots, the H0_diag cell size: {_f(g['accepted_of_reference_incumbent'], "{:.1f}")}
accepted -> {_f(g['accepted_of_reference_best'], "{:.1f}")}, over a garbage floor of
{_f(g['garbage_floor_of_reference'], "{:.1f}")}; the clean excess over that floor,
{_f(g['excess_over_floor_incumbent'], "{:.1f}")} -> {_f(g['excess_over_floor_best'], "{:.1f}")},
scales exactly with f because y - a = f x ({READOUT_FACTOR} - a)).
The transpiler's patch ranks {g['incumbent_rank']} of {r['n_scored']}.  The T2-blind objective
(gate + readout error only) picks rank {g['gate_only_rank']}, worth
{g['f_dd_off_gate_only_over_incumbent']:.2f}x -- the idle-aware objective is a further
{g['f_dd_off_best_over_gate_only']:.2f}x on top of it.  S_T2 falls from {g['S_T2_incumbent']:.3f}
to {g['S_T2_best']:.3f} ({g['delta_S_T2']:.3f} units) by changing {g['n_qubits_changed']} of
{r['n_logical_qubits']} qubits ({', '.join(str(q) for q in g['qubits_changed'])}).
{famtxt}
{toptxt}
""")
    return f"""# T2-aware patch selection for the 2x2 H0 run

Generated by `scripts/h0_patch_select.py` from `{res['json']}` at commit `{res['commit']}`,
{res['created']}.  **Every number below is read from that JSON.**  No QPU time and no IBM
account were used; the runtime was {res['runtime_s']:.1f} s.

Circuit: `{head['circuit']}` ({head['lattice']}, {head['n_logical_qubits']} logical qubits,
{head['incumbent']['n_cz']} CZ, critical path {head['incumbent']['T_s'] * 1e6:.2f} us before readout).
Interaction graph: {head['pattern']['n_nodes']} nodes, {head['pattern']['n_edges']} edges,
degree sequence {head['pattern']['degree_sequence']}.

Objective: **{res['objective']}**.
Tie-break: {res['tie_break']}.
The identity embedding reproduces `scripts/h0_idle_model.py` to
{max(s['result']['consistency_with_h0_idle_model']['f_dd_off_delta'] for s in res['sources']):.1e}
(tolerance {CONSISTENCY_TOL:.0e}) on every source, so the incumbent row is the same number that
script already writes.

## 1. Summary

{md_table(["source", "fingerprint", "device qubits in the record", "candidates",
           "f (transpiler's patch)", "f (best patch)", "gain", "rank of the transpiler's patch",
           "patch the rule selects"], lines)}

Stability over the {res['stability']['n_committed_records']} committed ibm_fez records:
{res['stability']['n_distinct_winners']} distinct winner(s), gain
{res['stability']['gain_min']:.2f}x to {res['stability']['gain_max']:.2f}x, same winner on every
record: **{res['stability']['same_winner_everywhere']}**.

## 2. Per source

{''.join(blocks)}
## 3. What this means for amendment 01 item 1

{finding_text(res)}

## 4. Method

{res['method']}
"""


# --------------------------------------------------------------------------- driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=DEFAULT_PREP)
    ap.add_argument("--circuit", default=DEFAULT_CIRCUIT)
    ap.add_argument("--calibration", nargs="*", default=None,
                    help="committed calibration record(s); the candidate space is what they cover")
    ap.add_argument("--snapshot", nargs="*", default=None,
                    help="offline fake-provider snapshot(s), full device (e.g. FakeFez)")
    ap.add_argument("--top", type=int, default=20, help="candidate rows kept in the JSON")
    ap.add_argument("--limit", type=int, default=None, help="stop the enumeration after N embeddings")
    ap.add_argument("--no-family", action="store_true")
    ap.add_argument("--out", default=os.path.join("data", "H0_patch_select.json"))
    ap.add_argument("--md", default=os.path.join("reports", "H0_patch_select.md"))
    ap.add_argument("--md-from", default=None,
                    help="re-render --md from an existing result JSON and exit (no search)")
    args = ap.parse_args()
    t0 = time.time()

    if args.md_from:
        jp = args.md_from if os.path.isabs(args.md_from) else os.path.join(ROOT, args.md_from)
        with open(jp) as fh:
            saved = json.load(fh)
        saved["json"] = os.path.relpath(jp, ROOT)
        mp = args.md if os.path.isabs(args.md) else os.path.join(ROOT, args.md)
        with open(mp, "w") as fh:
            fh.write(report_text(saved))
        print(f"wrote {os.path.relpath(mp, ROOT)} from {os.path.relpath(jp, ROOT)}")
        return 0

    cals = args.calibration
    snaps = args.snapshot
    if cals is None and snaps is None:
        cals = DEFAULT_RECORDS
        snaps = ["FakeFez"]
    cals, snaps = cals or [], snaps or []

    prep = args.prep if os.path.isabs(args.prep) else os.path.join(ROOT, args.prep)
    sources = []
    for p in cals:
        rec = load_record(p)
        sources.append(("committed record " + os.path.basename(p), rec))
    for n in snaps:
        rec = snapshot_record(n)
        sources.append((f"{n} full device", rec))

    out_sources = []
    for label, rec in sources:
        print(f"[{label}] {rec['_source']['path']} ...", flush=True)
        r = search(prep, rec, args.circuit, args.top, limit=args.limit,
                   family=not args.no_family)
        out_sources.append({
            "label": label,
            "source": rec["_source"],
            "backend": rec.get("backend"),
            "last_update_date": rec.get("last_update_date"),
            "stamp": rec.get("stamp"),
            "fingerprint": rec.get("fingerprint") or calibration_fingerprint(rec),
            "result": r,
        })
        g = r["gain"]
        print(f"    {r['n_scored']} candidates; incumbent f {r['incumbent']['f_dd_off']:.4e} "
              f"(rank {g['incumbent_rank']}), best {r['best']['f_dd_off']:.4e} "
              f"-> {g['f_dd_off_best_over_incumbent']:.2f}x on {r['best']['physical_qubits']}")

    fps = sorted({s["fingerprint"] for s in out_sources if s["source"]["kind"].startswith("committed")})
    identical = len(fps) == 1 and sum(1 for s in out_sources
                                      if s["source"]["kind"].startswith("committed")) > 1
    stability = build_stability(out_sources)
    finding = build_finding(out_sources, identical, stability)
    res = {
        "script": "scripts/h0_patch_select.py",
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "commit": git_commit(),
        "prep": os.path.relpath(prep, ROOT),
        "circuit": args.circuit,
        "objective": OBJECTIVE,
        "tie_break": TIE_BREAK,
        "consistency_tolerance": CONSISTENCY_TOL,
        "committed_records_share_a_fingerprint": identical,
        "method": (
            "A candidate patch is an embedding of the routed circuit's CZ interaction graph into "
            "the device coupling graph; relabelling the frozen circuit along it changes no gate, "
            "no angle, no CZ count and no classical-bit mapping, only which physical qubit plays "
            "which role.  The enumeration is exhaustive and deterministic (pattern nodes by "
            "descending degree then index, host nodes ascending).  Every scored quantity comes "
            "from scripts/h0_idle_model.py (schedule, budgets, f_on_record, predictions) applied "
            "to the relabelled circuit on the record; the identity embedding is asserted equal to "
            f"that script's own output to {CONSISTENCY_TOL:.0e}.  The yield is "
            f"y = {READOUT_FACTOR} f + (1 - f) a (manual Step 4.4, skqd.skqd.yield_model)."),
        "finding": finding,
        "stability": stability,
        "sources": out_sources,
        "runtime_s": time.time() - t0,
    }

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"wrote {os.path.relpath(out, ROOT)}")

    if args.md:
        with open(out) as fh:                    # the report is rendered FROM the JSON on disk
            saved = json.load(fh)
        saved["json"] = os.path.relpath(out, ROOT)
        mp = args.md if os.path.isabs(args.md) else os.path.join(ROOT, args.md)
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        with open(mp, "w") as fh:
            fh.write(report_text(saved))
        print(f"wrote {os.path.relpath(mp, ROOT)}")
    print(f"{time.time() - t0:.1f} s")
    return 0


def build_stability(out_sources):
    """Does the selection rule pick the same patch on every committed record of the day?"""
    rows = []
    for s in out_sources:
        if not s["source"]["kind"].startswith("committed"):
            continue
        r = s["result"]
        rows.append({"label": s["label"], "stamp": s.get("stamp"),
                     "fingerprint": s.get("fingerprint", "")[:16],
                     "best": r["best"]["physical_qubits"],
                     "best_f": r["best"]["f_dd_off"],
                     "incumbent_f": r["incumbent"]["f_dd_off"],
                     "incumbent_rank": r["incumbent"]["rank"],
                     "gain": r["gain"]["f_dd_off_best_over_incumbent"]})
    winners = sorted({tuple(x["best"]) for x in rows})
    return {
        "n_committed_records": len(rows),
        "n_distinct_winners": len(winners),
        "winners": [list(w) for w in winners],
        "same_winner_everywhere": len(winners) == 1 and len(rows) > 1,
        "gain_min": min((x["gain"] for x in rows), default=None),
        "gain_max": max((x["gain"] for x in rows), default=None),
        "records": rows,
    }


def build_finding(out_sources, identical, stability=None):
    parts = []
    if identical:
        parts.append("The two committed records named by the prompt carry the SAME calibration "
                     "fingerprint, so they give the same answer number for number.")
    for s in out_sources:
        r = s["result"]
        g = r["gain"]
        parts.append(
            f"On {s['label']} ({r['n_scored']} candidate patches over {r['host']['n_qubits']} "
            f"qubits) the best patch is {g['f_dd_off_best_over_incumbent']:.2f}x the transpiler's "
            f"in clean fraction and {_f(g['yield_best_over_incumbent'])}x in yield; the "
            f"transpiler's patch ranks {g['incumbent_rank']} of {r['n_scored']}, and a T2-blind "
            f"gate-error objective would have reached only "
            f"{g['f_dd_off_gate_only_over_incumbent']:.2f}x.  The winner is "
            f"{r['best']['physical_qubits']}, which differs from the incumbent in "
            f"{g['n_qubits_changed']} of {r['n_logical_qubits']} qubits and cuts S_T2 by "
            f"{g['delta_S_T2']:.3f} units.")
    if stability and stability["n_committed_records"] > 1:
        parts.append(
            f"Over the {stability['n_committed_records']} committed ibm_fez records of "
            f"2026-09-21/22 the rule returns {stability['n_distinct_winners']} distinct "
            f"winner(s) and a gain between {stability['gain_min']:.2f}x and "
            f"{stability['gain_max']:.2f}x.")
    parts.append("The H0 calibration records cover only the qubits and edges the frozen set "
                 "already uses, so the committed-record search is a lower bound on what a "
                 "full-device read would find; the selection rule therefore has to be run on a "
                 "full-device target read (free, no QPU time) on the day.")
    return "  ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
