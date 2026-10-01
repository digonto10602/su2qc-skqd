#!/usr/bin/env python3
"""
Gate S2D_levers (prompts/23) -- the 2x2 coarse step on ibm_kingston: measure the duration levers
and decide what the signed f >= 0.1 criterion needs.

A MEASUREMENT gate.  PASS means *measured, verified, consistent* (criteria C1-C9 of the prompt);
it never means *affordable*.  Whether the 2x2 step meets f >= 0.1 is a data block
(`data.verdict`), not a criterion: no criterion is placed on any f, duration ratio or r_crit.

The levers, each judged by what it does to the SCHEDULED duration and the idle budget (the
gate-only cost model of the literature catalogue was 15-50x optimistic here, gate H0_model):

  L0_asis_asap / L0_asis_alap   the frozen canary relabelled onto its best kingston embedding,
                                scheduled ASAP / ALAP with explicit delays
  L1_seed                       default term order, best transpiler seed (best-of-N, lever B4)
  L2_order                      best (term order, seed) -- a NEW coarse-step operator (the terms
                                do not commute): verified here, adopted only by the owner
  L3_rx                         L2's (or L1's) circuit with the live fractional rx / rzz gates (B3)
  L4_all                        the best of L1-L3, scheduled ALAP
  L0_asis_dd_ceiling            PTA only, DD at rho = 0: a ceiling, not a prediction

Every prediction row carries the PTA bound (`skqd.idle`) and Aer on the scheduled circuit
(`AerSimulator.from_backend` of a FakeKingston base carrying the fresh live record), at the
record's echo T2 (r = 1) and at uniform transferred ratios r = 0.5, 0.25, 0.174 of it, read with
the clean-yield statistic (`reference_string_test` and `clean_fraction_mixture`).  The
transferred ratios are a planner construction; nothing here fits or chooses a T2*.

Stages (each command stays far below the 30-minute rule; --help lists the options):
  live        B1-B3: fresh full-device kingston record + the fractional target (metadata only)
  scan        C1:   720 term orders x N seeds, transpiled and scheduled on a uniform record
  scan-merge  C1:   the per-seed fragments -> data/S2D_levers/scan.json
  select      C2:   exhaustive embedding search per candidate on the fresh record
  rows        C3:   the lever rows, their circuits (QPY v13) and manifests
  fractional  D:    the fractional transpilation of the L2 (or L1) circuit
  aer         E2:   one Aer cell (row, ratio, chunk) -- counts written once, never re-drawn
  family      F:    the reordered family check (28 r = 1 circuits per order)
  e4          E4:   PTA over the 28 r = 1 circuits of the recommended row's family
  assemble    G:    validation/S2D_levers.json + reports/S2D_levers_2x2_kingston.md

0 QPU seconds.  `sampler.run` against a real backend appears nowhere in this file.
"""
import argparse
import glob
import gzip
import hashlib
import io
import itertools
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PREP = os.path.join(ROOT, "data", "hardware", "H0_prep")
CANARY = "B0_ref06_k1_rep1"
COMMITTED_KINGSTON = os.path.join("data", "hardware", "device_survey_20260922",
                                  "ibm_kingston_20260930T2255Z.json")
FEZ_RECORD = os.path.join("data", "hardware", "H0_ibm_fez", "calibration_20260922T1400Z.json")
SURVEY = os.path.join("data", "H0_device_survey_live_20260930.json")
OUT = os.path.join("data", "S2D_levers")
DEVICE = "ibm_kingston"

TERMS = ("diag", "hop0", "hop1", "hop2", "hop3", "plaq0")
DEFAULT_ORDER = TERMS
G2 = 4.0
RATIOS = (1.0, 0.5, 0.25, 0.174)          # T2 used / T2 echo of the record (planner construction)
FEZ_FALLBACK_RATIO = 0.174                # validation/S2D_idle.json: data.t2_bracket fallback
BARS = (0.1, 0.05)                        # amendment 01 section 1(c): read, never changed
BASIS = ["rz", "sx", "x", "cz"]
N_SEEDS = 8                               # prompts/23 C1
K_SELECT = 8                              # prompts/23 C2
SEED_BASE = 11                            # P7's seed_simulator
SCHEDULE_SEED = 7                         # gate_H0P.SCHEDULE_SEED
SHOTS_PER_CHUNK = 2000
CHUNKS = 2                                # 4000 shots per cell
EXTRA_CHUNKS = 2                          # when the clean reference hits are below MIN_REF_HITS
MIN_REF_HITS = 20
C6_TOL = 0.25                             # the H0_model C1 tolerance
AMP_TOL = 1e-10
LEAK_TOL = 1e-9
ANCHOR_REL = 1e-9                         # C3(i)
FRACTIONAL_MIN_GAIN = 0.95                # D: dropped unless T_frac / T_plain <= 0.95
QPY_VERSION = 13                          # prompts/22: the CI's qiskit 1.4.3 reads v13

# P2/P5 of the planner analysis, reproduced by C3(ii)
P5_DEFAULT = {"order": list(DEFAULT_ORDER), "seed": 2, "n_cz": 588, "T_us": 44.24, "active": 12}
P5_SHORTEST = {"order": ["plaq0", "hop2", "diag", "hop1", "hop3", "hop0"], "seed": 2,
               "n_cz": 629, "T_us": 35.78, "active": 15}
# P7 on the committed record (2000 shots, seed 11), reproduced by C3(iii)
P7_CELLS = {"asap": {"accepted": 221, "reference_hits": 116, "f_clean": 0.0797},
            "alap": {"accepted": 309, "reference_hits": 151, "f_clean": 0.1039}}
P7_TOL = 0.25
# C3(i): the survey winner on the committed record
C3_ANCHOR = {"T_total_s": 5.0144e-05, "S_T1": 0.49389348458842963,
             "S_T2": 0.9954977738711279, "f": 0.05622012608266227}

ROWS = ("L0_asis_asap", "L0_asis_alap", "L1_seed", "L2_order", "L3_rx", "L4_all")


def p(*parts):
    return os.path.join(ROOT, *parts)


def rel(path):
    return os.path.relpath(path, ROOT)


def load_json(path):
    with open(path if os.path.isabs(path) else p(path)) as fh:
        return json.load(fh)


def dump_json(obj, path, indent=1):
    from skqd.report import _jsonable
    path = path if os.path.isabs(path) else p(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(_jsonable(obj), fh, indent=indent)
    os.replace(tmp, path)
    return path


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


def versions():
    import qiskit
    import qiskit_aer
    import qiskit_ibm_runtime
    return {"qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__,
            "qiskit_ibm_runtime": qiskit_ibm_runtime.__version__}


# --------------------------------------------------------------------------- the physics
_FACTORY = {}


def factory():
    """(Model, CircuitFactory, n qubits, canary manifest) -- built once per process."""
    if not _FACTORY:
        from gate_H0P import load_manifests
        from skqd.circuits_ir import CircuitFactory
        from skqd.codec import Codec
        from skqd.exact import Model
        M = Model(2)
        F = CircuitFactory(M, G2)
        mans, _ = load_manifests(PREP)
        man = next(m for m in mans if m["id"] == CANARY)
        _FACTORY.update(M=M, F=F, n=Codec(M.basis).n_qubits, man=man, mans=mans)
    return _FACTORY


def term_parts(F, theta):
    """{term name: IR gate list at angle theta} -- the names of `Terms.groups`."""
    parts = {"diag": F.diag_gates(theta)}
    for l in range(F.lat.n_links):
        parts[f"hop{l}"] = F.hop_gates(l, theta)
    for P in range(len(F.lat.plaquettes)):
        parts[f"plaq{P}"] = F.plaq_gates(P, theta, True)
    assert tuple(parts) == TERMS, f"the term names changed: {tuple(parts)}"
    return parts


def ir_circuit(order, ref, theta, measure=True):
    """prepare(ref) + the coarse step at angle theta with the terms in `order`."""
    from skqd import circuits_qiskit as cq
    fx = factory()
    parts = term_parts(fx["F"], theta)
    gates = fx["F"].prepare(int(ref)) + sum((parts[k] for k in order), [])
    return cq.ir_to_qiskit(gates, fx["n"], measure=measure)


def exact_state(order, ref, theta):
    """prod_gamma exp(-i theta H_gamma) |ref> with the groups applied in `order` (full basis)."""
    import scipy.sparse as sp
    from skqd.exact import mass_default
    from skqd.krylov import apply_groups, basis_vector
    M = factory()["M"]
    g = M.terms.groups(G2, mass_default(G2))
    assert set(g) == set(TERMS) and sorted(order) == sorted(TERMS), (sorted(g), order)
    return apply_groups([sp.csr_matrix(g[k]) for k in order], basis_vector(M.basis.dim, int(ref)),
                        float(theta))


def ideal_distribution(order, twoB, ref, theta):
    """The ideal sector distribution of one coarse-step circuit in a given term order.

    `skqd.krylov.ideal_sector_distribution` in the default order (asserted equal to it there)."""
    M = factory()["M"]
    idx = np.asarray(M.reference(G2, twoB).indices, dtype=int)
    psi = exact_state(order, ref, theta)
    prob = np.abs(psi) ** 2
    pp = prob[idx]
    mass = float(pp.sum())
    pos = {int(b): i for i, b in enumerate(idx)}
    return {"p": pp / mass, "p_unnormalised": pp, "sector_indices": [int(b) for b in idx],
            "dim": int(len(idx)), "sector_mass": mass, "reference_position": pos.get(int(ref)),
            "p_reference": float(pp[pos[int(ref)]] / mass)}


# --------------------------------------------------------------------------- records
def committed_kingston():
    return load_json(COMMITTED_KINGSTON)


def live_info():
    path = p(OUT, "live.json")
    if not os.path.exists(path):
        raise SystemExit(f"{rel(path)} missing: run --stage live first")
    return load_json(path)


def fresh_record():
    info = live_info()
    return load_json(info["record"]["path"]), info


def fractional_json():
    info = live_info()
    fr = info.get("fractional") or {}
    if not fr.get("path"):
        return None
    return load_json(fr["path"])


def undirected_edges(rec):
    out = set()
    for e in rec["edges"].values():
        a, b = (int(x) for x in e["target_key"])
        out.add((min(a, b), max(a, b)))
    return sorted(out)


def record_medians(rec):
    t1 = [v["T1_s"] for v in rec["qubits"].values() if v.get("T1_s")]
    t2 = [v["T2_s"] for v in rec["qubits"].values() if v.get("T2_s")]
    cz = [e["cz_error"] for e in rec["edges"].values() if e.get("cz_error") is not None]
    ro = [v["measure_error"] for v in rec["qubits"].values() if v.get("measure_error") is not None]
    return {"T1_median_s": float(np.median(t1)), "T2_median_s": float(np.median(t2)),
            "cz_error_mean": float(np.mean(cz)), "measure_error_mean": float(np.mean(ro)),
            "n_T1": len(t1), "n_T2": len(t2), "n_cz": len(cz), "n_measure": len(ro)}


def uniform_scan_record(rec):
    """C1: `coherence.uniform_record` with kingston-like durations and the record's medians."""
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    from skqd import coherence
    edges = sorted({(min(int(a), int(b)), max(int(a), int(b)))
                    for a, b in FakeKingston().coupling_map})
    if edges != undirected_edges(rec):
        raise SystemExit("the FakeKingston coupling map is not the live record's edge set "
                         "(prompts/23 C1 assertion)")
    med = record_medians(rec)
    u = coherence.uniform_record(156, edges, t_2q=68e-9, t_1q=32e-9, t_ro=2.18e-6,
                                 T1=med["T1_median_s"], T2=med["T2_median_s"])
    return u, med, edges


# --------------------------------------------------------------------------- stage: live
def stage_live(args):
    """B1-B3.  Metadata reads only: the target, properties and status of ibm_kingston."""
    import h0_device_survey as ds
    from h0_backends import (backend_from_record, calibration_diff, calibration_fingerprint,
                             calibration_record)
    t0 = time.time()
    committed = committed_kingston()
    rec = ds.full_device_record(DEVICE)          # resolve_backend -> NEW object, refresh()
    stamp = rec["stamp"]
    hdir = p("data", "hardware", f"S2D_levers_{stamp}")
    rpath = os.path.join(hdir, f"{DEVICE}_{stamp}.json")
    if os.path.exists(rpath):
        old = load_json(rpath)
        if old["fingerprint"] != rec["fingerprint"]:
            raise SystemExit(f"{rel(rpath)} exists with another fingerprint: refusing to overwrite")
    else:
        dump_json(rec, rpath)
    diff = calibration_diff(committed, rec)
    fam = {}
    for leaf in diff["leaves"]:
        f = leaf["path"].split("/")[-1]
        d = fam.setdefault(f, {"n": 0, "ratios": []})
        d["n"] += 1
        if leaf["ratio"] is not None:
            d["ratios"].append(leaf["ratio"])
    fam = {f: {"n_leaves": v["n"],
               "ratio_median": (float(np.median(v["ratios"])) if v["ratios"] else None),
               "ratio_min": (float(min(v["ratios"])) if v["ratios"] else None),
               "ratio_max": (float(max(v["ratios"])) if v["ratios"] else None)}
           for f, v in sorted(fam.items())}
    q146 = {"committed": committed["qubits"]["146"], "fresh": rec["qubits"]["146"]}

    # the strict round trip on a FakeKingston base (prompts/23 escalation clause)
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    rt = {"ok": None}
    try:
        _b, binfo = backend_from_record(rec, base=FakeKingston(), strict=True)
        rt = {"ok": True, "info": {k: v for k, v in binfo.items() if k not in ("qubits", "edges")}}
    except SystemExit as exc:
        rt = {"ok": False, "error": str(exc)}

    # B3: the fractional target, a SEPARATE backend object
    from ibm_account import open_service
    frac = {"present": False}
    fpath = None
    try:
        svc = open_service()
        fb = svc.backend(DEVICE, use_fractional_gates=True)
        try:
            fb.refresh()
        except Exception:
            pass
        t = fb.target
        ops = sorted(t.operation_names)
        has = {"rx": "rx" in ops, "rzz": "rzz" in ops}
        qubits = list(range(int(fb.num_qubits)))
        edges_dir = sorted({(int(a), int(c)) for a, c in fb.coupling_map})
        plain = calibration_record(fb, qubits, edges_dir)
        fq, fe = {}, {}
        for q in qubits:
            pr = t["rx"].get((q,)) if has["rx"] else None
            fq[str(q)] = {"rx_duration_s": None if pr is None or pr.duration is None else float(pr.duration),
                          "rx_error": None if pr is None or pr.error is None else float(pr.error)}
        for key, e in plain["edges"].items():
            a, b = e["target_key"]
            pr = None
            if has["rzz"]:
                pr = t["rzz"].get((a, b))
                if pr is None:
                    pr = t["rzz"].get((b, a))
            fe[key] = {"target_key": [int(a), int(b)],
                       "rzz_duration_s": None if pr is None or pr.duration is None else float(pr.duration),
                       "rzz_error": None if pr is None or pr.error is None else float(pr.error)}
        fstamp = plain["stamp"]
        fr = {"backend": DEVICE, "use_fractional_gates": True,
              "last_update_date": plain["last_update_date"], "stamp": fstamp,
              "basis_gates": ops, "has": has,
              "plain_block_fingerprint": plain["fingerprint"],
              "plain_block_equal_to_fresh_record": plain["fingerprint"] == rec["fingerprint"],
              "plain_block_diff_vs_fresh": (None if plain["fingerprint"] == rec["fingerprint"]
                                            else {k: v for k, v in calibration_diff(rec, plain).items()
                                                  if k != "leaves"}),
              "cz_durations_s": sorted({e["cz_duration_s"] for e in plain["edges"].values()
                                        if e["cz_duration_s"] is not None}),
              "sx_durations_s": sorted({v["sx_duration_s"] for v in plain["qubits"].values()
                                        if v["sx_duration_s"] is not None}),
              "qubits": fq, "edges": fe,
              "n_rx_none": sum(1 for v in fq.values() if v["rx_error"] is None or v["rx_duration_s"] is None),
              "n_rzz_none": sum(1 for v in fe.values() if v["rzz_error"] is None or v["rzz_duration_s"] is None),
              "note": ("read from QiskitRuntimeService().backend('ibm_kingston', "
                       "use_fractional_gates=True), a separate object from the plain read; None "
                       "is recorded as None, never defaulted")}
        fpath = os.path.join(hdir, f"{DEVICE}_fractional_{fstamp}.json")
        dump_json(fr, fpath)
        frac = {"present": has["rx"] and has["rzz"], "has": has, "path": rel(fpath),
                "stamp": fstamp, "basis_gates": ops,
                "plain_block_fingerprint": fr["plain_block_fingerprint"],
                "plain_block_equal_to_fresh_record": fr["plain_block_equal_to_fresh_record"],
                "plain_block_diff_vs_fresh": fr["plain_block_diff_vs_fresh"],
                "cz_durations_s": fr["cz_durations_s"], "sx_durations_s": fr["sx_durations_s"],
                "n_rx_none": fr["n_rx_none"], "n_rzz_none": fr["n_rzz_none"]}
    except SystemExit as exc:
        frac = {"present": False, "error": str(exc), "status": "not measured"}

    info = {
        "stage": "live", "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "commit": git_commit(), "versions": versions(),
        "qpu_seconds": 0,
        "record": {"path": rel(rpath), "stamp": stamp, "last_update_date": rec["last_update_date"],
                   "fingerprint": rec["fingerprint"],
                   "n_qubits": len(rec["qubits"]), "n_edges": len(rec["edges"]),
                   "missing_errors": rec["missing_errors"], "status": rec.get("status")},
        "committed": {"path": COMMITTED_KINGSTON, "fingerprint": committed["fingerprint"],
                      "stamp": committed["stamp"]},
        "diff_vs_committed": {"n_leaves": diff["n_leaves"], "families": diff["families"],
                              "by_family": fam, "max_ratio": diff["max_ratio"],
                              "min_ratio": diff["min_ratio"]},
        "qubit_146": q146,
        "backend_from_record_strict": rt,
        "fractional": frac,
        "runtime_s": time.time() - t0,
    }
    dump_json(info, p(OUT, "live.json"))
    print(f"fresh record {rel(rpath)} fingerprint {rec['fingerprint'][:16]} "
          f"(committed {committed['fingerprint'][:16]}): {diff['n_leaves']} leaves moved over "
          f"{diff['families']}; missing_errors {len(rec['missing_errors'])}")
    print(f"qubit 146 fresh: T1 {q146['fresh']['T1_s']} T2 {q146['fresh']['T2_s']} "
          f"sx {q146['fresh']['sx_error']} ro {q146['fresh']['measure_error']}")
    print(f"backend_from_record strict: {rt['ok']} {rt.get('error', '')}")
    print(f"fractional: {json.dumps({k: frac.get(k) for k in ('present', 'has', 'path', 'plain_block_equal_to_fresh_record', 'cz_durations_s', 'sx_durations_s', 'n_rx_none', 'n_rzz_none')})}")
    return 0


# --------------------------------------------------------------------------- stage: scan
def transpile_plain(qc, seed, cmap=None):
    from qiskit import transpile
    if cmap is None:
        from qiskit_ibm_runtime.fake_provider import FakeKingston
        cmap = FakeKingston().coupling_map
    return transpile(qc, coupling_map=cmap, basis_gates=BASIS, optimization_level=3,
                     seed_transpiler=int(seed))


def twoq_layers(tq):
    return int(tq.depth(filter_function=lambda i: i.operation.num_qubits == 2
                        and i.operation.name not in ("barrier",)))


def compile_stats(tq, rec):
    """Counts, depth, layers and the ASAP schedule of a transpiled circuit on `rec`."""
    from skqd import coherence, idle
    ops = {k: int(v) for k, v in tq.count_ops().items()}
    sch = idle.schedule_asap(tq, rec)
    pb = coherence.packing_bound(sch)
    return {"n_cz": ops.get("cz", 0), "n_rzz": ops.get("rzz", 0),
            "n_1q": ops.get("sx", 0) + ops.get("x", 0) + ops.get("rx", 0),
            "ops": ops, "depth": int(tq.depth()), "twoq_layers": twoq_layers(tq),
            "n_active": len(sch["active"]), "active": sch["active"],
            "T_s": sch["T_s"], "T_total_s": sch["T_total_s"], "busy_max_s": pb["T_min_s"],
            "idle_s": float(sum(sch["per_qubit"][q]["idle_s"] for q in sch["active"]))}, sch


_SCAN = {}


def _scan_init(dt, ref):
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    rec, _info = fresh_record()
    u, med, _edges = uniform_scan_record(rec)
    _SCAN.update(dt=dt, ref=ref, cmap=FakeKingston().coupling_map, u=u, med=med)
    factory()


def _scan_one(job):
    from skqd import idle
    order, seed = job
    t0 = time.time()
    qc = ir_circuit(order, _SCAN["ref"], _SCAN["dt"])
    tq = transpile_plain(qc, seed, _SCAN["cmap"])
    st, sch = compile_stats(tq, _SCAN["u"])
    _pq, tot = idle.idle_budget(sch, _SCAN["u"])
    med = _SCAN["med"]
    n_meas = int(tq.count_ops().get("measure", 0))
    f_gates = (1.0 - med["cz_error_mean"]) ** st["n_cz"] * (1.0 - med["measure_error_mean"]) ** n_meas
    return {"order": list(order), "seed": int(seed), "n_cz": st["n_cz"], "n_1q": st["n_1q"],
            "depth": st["depth"], "cz_layers": st["twoq_layers"], "n_active": st["n_active"],
            "T_s": st["T_s"], "busy_max_s": st["busy_max_s"], "S_T1": tot["S_T1"],
            "S_T2": tot["S_T2"], "f_gates_proxy": f_gates,
            "f_proxy": f_gates * math.exp(-tot["S_T1"] - tot["S_T2"]),
            "seconds": time.time() - t0}


def stage_scan(args):
    from multiprocessing import Pool
    fx = factory()
    man = fx["man"]
    seeds = list(range(args.seeds[0], args.seeds[1])) if args.seeds else list(range(N_SEEDS))
    orders = list(itertools.permutations(TERMS))
    t0 = time.time()
    for seed in seeds:
        path = p(OUT, "scan_parts", f"seed{seed}.json")
        if os.path.exists(path):
            print(f"{rel(path)} exists, skipped")
            continue
        jobs = [(o, seed) for o in orders]
        with Pool(args.workers, initializer=_scan_init,
                  initargs=(float(man["dt"]), int(man["reference"]))) as pool:
            rows = pool.map(_scan_one, jobs, chunksize=8)
        dump_json({"seed": seed, "n": len(rows), "rows": rows,
                   "dt": float(man["dt"]), "reference": int(man["reference"]),
                   "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "versions": versions()},
                  path, indent=None)
        best = min(rows, key=lambda r: r["T_s"])
        print(f"seed {seed}: {len(rows)} orders in {time.time() - t0:.0f} s; shortest "
              f"{best['T_s'] * 1e6:.2f} us {best['order']}", flush=True)
    return 0


def stage_scan_merge(args):
    rows, meta = [], None
    for path in sorted(glob.glob(p(OUT, "scan_parts", "seed*.json"))):
        d = load_json(path)
        meta = meta or {k: d[k] for k in ("dt", "reference", "versions")}
        rows.extend(d["rows"])
    rec, info = fresh_record()
    u, med, _ = uniform_scan_record(rec)
    seeds = sorted({r["seed"] for r in rows})
    res = {"stage": "scan", "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
           "commit": git_commit(), **(meta or {}),
           "uniform_record": u["uniform"], "record_medians": med,
           "record_fingerprint": info["record"]["fingerprint"],
           "basis": BASIS, "optimization_level": 3, "seeds": seeds,
           "n_orders": len({tuple(r["order"]) for r in rows}), "n_rows": len(rows),
           "fields": ["order", "seed", "n_cz", "n_1q", "depth", "cz_layers", "n_active", "T_s",
                      "busy_max_s", "S_T1", "S_T2", "f_gates_proxy", "f_proxy"],
           "rows": [{k: r[k] for k in ("order", "seed", "n_cz", "n_1q", "depth", "cz_layers",
                                       "n_active", "T_s", "busy_max_s", "S_T1", "S_T2",
                                       "f_gates_proxy", "f_proxy")} for r in rows],
           "compute_seconds": float(sum(r["seconds"] for r in rows))}
    dump_json(res, p(OUT, "scan.json"), indent=None)
    for key, lab, rev in (("f_proxy", "f_proxy", True), ("T_s", "T_s", False), ("n_cz", "n_cz", False)):
        top = sorted(rows, key=lambda r: (-r[key] if rev else r[key], r["seed"], r["order"]))[:20]
        print(f"top 20 by {lab}:")
        for r in top:
            print(f"   {r['order']} seed {r['seed']}: T {r['T_s'] * 1e6:6.2f} us  CZ {r['n_cz']}  "
                  f"active {r['n_active']}  S_T1 {r['S_T1']:.3f} S_T2 {r['S_T2']:.3f}  "
                  f"f_proxy {r['f_proxy']:.4f}")
    for want in (P5_DEFAULT, P5_SHORTEST):
        r = next((x for x in rows if x["order"] == want["order"] and x["seed"] == want["seed"]), None)
        print(f"P2/P5 anchor {want['order']} seed {want['seed']}: "
              + ("missing" if r is None else
                 f"{r['n_cz']} CZ, {r['T_s'] * 1e6:.2f} us, {r['n_active']} active "
                 f"(expected {want['n_cz']}, {want['T_us']}, {want['active']})"))
    print(f"wrote {rel(p(OUT, 'scan.json'))}: {len(rows)} rows")
    return 0


# --------------------------------------------------------------------------- stage: select
def interaction_graph_2q(qc):
    """{qubit: neighbours} over EVERY two-qubit instruction (cz and rzz), and the edge set."""
    import collections
    adj = collections.defaultdict(set)
    edges = set()
    for inst in qc.data:
        if inst.operation.num_qubits != 2 or inst.operation.name in ("barrier",):
            continue
        a, b = (qc.find_bit(q).index for q in inst.qubits)
        adj[a].add(b)
        adj[b].add(a)
        edges.add((min(a, b), max(a, b)))
    return dict(adj), sorted(edges)


def garbage_acceptance(twoB=0):
    from gate_H0P import random_acceptance
    from skqd.codec import Codec
    return random_acceptance(Codec(factory()["M"].basis), twoB)["fraction"]


def fractional_tables(rec):
    """(cz errors, rzz errors, measure errors) of a record for `f_from_calibration`."""
    cz, rzz = {}, {}
    for e in rec["edges"].values():
        key = tuple(int(x) for x in e["target_key"])
        for k in (key, key[::-1]):
            cz[k] = e["cz_error"]
            if e.get("rzz_error") is not None:
                rzz[k] = e["rzz_error"]
    meas = {int(q): v["measure_error"] for q, v in rec["qubits"].items()}
    return cz, rzz, meas


def f_gates_on_record(qc, rec):
    """(f_gates, n_2q, f_including_1q_errors): the gate S2D product, rzz edges included."""
    import h0_support_plan as sp
    cz, rzz, meas = fractional_tables(rec)
    tables = {"cz": cz}
    if rzz:
        tables["rzz"] = rzz
    with np.errstate(divide="ignore", invalid="ignore"):
        f, n2, _nm = sp.f_from_calibration(qc, cz, meas, two_qubit_errors=tables)
    log1 = 0.0
    for inst in qc.data:
        nm = inst.operation.name
        if nm in ("sx", "x", "rx"):
            q = qc.find_bit(inst.qubits[0]).index
            key = {"sx": "sx_error", "x": "x_error", "rx": "rx_error"}[nm]
            e = rec["qubits"][str(q)].get(key)
            if e is None:
                raise SystemExit(f"the record has no {key} for qubit {q}")
            if float(e) >= 1.0:              # IBM's uncalibrated marker: no clean shot
                log1 = -math.inf
                continue
            log1 += math.log1p(-float(e))
    return float(f), int(n2), (0.0 if log1 == -math.inf else float(f) * math.exp(log1))


FRACTIONAL_QUBIT_FIELDS = ("rx_duration_s", "rx_error")
FRACTIONAL_EDGE_FIELDS = ("rzz_duration_s", "rzz_error")


def covers(rec, qubits, edges, fractional=False):
    import h0_patch_select as ps
    ok, why = ps.record_covers(rec, qubits, edges)
    if not ok or not fractional:
        return ok, why
    for q in qubits:
        for k in FRACTIONAL_QUBIT_FIELDS:
            if rec["qubits"][str(q)].get(k) is None:
                return False, f"qubit {q} has no {k}"
    for a, b in edges:
        e = rec["edges"].get(f"{a}-{b}") or rec["edges"].get(f"{b}-{a}")
        for k in FRACTIONAL_EDGE_FIELDS:
            if e.get(k) is None:
                return False, f"edge ({a}, {b}) has no {k}"
    return True, None


def score_embedding(ops, nq, ncl, mapping, rec, a, fractional=False):
    """`h0_patch_select.score_patch` -- verbatim for a plain circuit; for a fractional one the
    same schedule and budget (skqd.idle reads the rx / rzz durations) with f_gates multiplying
    the rzz edge errors too."""
    import h0_idle_model as im
    import h0_patch_select as ps
    if not fractional:
        return ps.score_patch(ops, nq, ncl, mapping, rec, a)
    qc = ps.relabel(ops, nq, ncl, mapping)
    sch = im.schedule(qc, rec)
    per_q, tot = im.budgets(sch, rec)
    f_gates, n2, f1 = f_gates_on_record(qc, rec)
    pred = im.predictions(f_gates, tot, a)
    worst = max(per_q.items(), key=lambda kv: (kv[1]["S_T2"], -int(kv[0])))
    return {"physical_qubits": sorted(mapping.values()),
            "mapping": {str(k): int(v) for k, v in sorted(mapping.items())},
            "n_cz": int(n2), "n_measure": int(qc.count_ops().get("measure", 0)),
            "T_s": sch["T_s"], "T_total_s": sch["T_total_s"],
            "f_gates": f_gates, "f_including_1q_errors": f1,
            "S_T1": tot["S_T1"], "S_T2": tot["S_T2"],
            "S_T2_eligible": tot["S_T2_eligible"], "S_T2_ineligible": tot["S_T2_ineligible"],
            "S_DD": tot["S_DD"], "dd_eligible": tot["dd_eligible"], "idle_s": tot["idle_s"],
            "f_dd_off": pred["dd_off"]["f"], "yield_dd_off": pred["dd_off"]["yield"],
            "f_dd_on": {r: v["f"] for r, v in pred["dd_on"].items()},
            "worst_qubit": int(worst[0]), "worst_qubit_S_T2": worst[1]["S_T2"],
            "worst_qubit_T2_s": worst[1]["T2_s"], "max_qubit_S_T2": worst[1]["S_T2"],
            "min_T2_s": min(v["T2_s"] for v in per_q.values()),
            "min_T1_s": min(v["T1_s"] for v in per_q.values())}


def embedding_search(qc, rec, a, fractional=False, survey_set=None, top=5):
    """The exhaustive search of `h0_patch_select` (enumerate_embeddings / record_covers /
    score_patch / rank_key, objective and tie-break unchanged) on any transpiled circuit."""
    import h0_patch_select as ps
    pat_adj, pat_edges = interaction_graph_2q(qc)
    active = sorted({qc.find_bit(q).index for inst in qc.data for q in inst.qubits
                     if inst.operation.name != "barrier"})
    if sorted(pat_adj) != active:
        raise SystemExit(f"active qubits {active} are not all in the two-qubit pattern "
                         f"{sorted(pat_adj)}: the relabelling would leave a qubit unmapped")
    host_adj, host_nodes = ps.host_graph(rec)
    embs, order = ps.enumerate_embeddings(pat_adj, host_adj, host_nodes)
    ops = ps.circuit_ops(qc)
    scored, skipped = [], 0
    for mp in embs:
        qubits = sorted(mp.values())
        edges = sorted({(min(mp[u], mp[v]), max(mp[u], mp[v])) for u, v in pat_edges})
        ok, _why = covers(rec, qubits, edges, fractional)
        if not ok:
            skipped += 1
            continue
        scored.append(score_embedding(ops, qc.num_qubits, qc.num_clbits, mp, rec, a, fractional))
    if not scored:
        raise SystemExit("no embedding of the candidate is covered by the record")
    scored.sort(key=ps.rank_key)
    for i, e in enumerate(scored):
        e["rank"] = i + 1
    on_survey = None
    if survey_set is not None:
        on_survey = next((e for e in scored if e["physical_qubits"] == sorted(survey_set)), None)
    degs = sorted((len(v) for v in pat_adj.values()), reverse=True)
    return {"pattern": {"n_nodes": len(pat_adj), "n_edges": len(pat_edges),
                        "edges": [list(e) for e in pat_edges], "degree_sequence": degs,
                        "is_tree": len(pat_edges) == len(pat_adj) - 1},
            "n_embeddings": len(embs), "n_scored": len(scored), "n_skipped": skipped,
            "best": scored[0], "on_survey_patch": on_survey, "top": scored[:top]}


def survey_winner():
    d = load_json(SURVEY)
    w = d["devices"][2]["patch_select"]["winner"]
    assert d["devices"][2]["backend"] == DEVICE or d["devices"][2]["device"] == DEVICE
    return w


def canary_circuit():
    from gate_H0P import load_circuit
    return load_circuit(PREP, factory()["man"])


def candidate_circuit(cand):
    """The transpiled circuit of a candidate: the frozen canary, or (order, seed) re-transpiled."""
    if cand["id"] == "asis":
        return canary_circuit()
    man = factory()["man"]
    return transpile_plain(ir_circuit(cand["order"], man["reference"], man["dt"]), cand["seed"])


def cand_id(order, seed):
    return "o_" + "-".join(order) + f"_s{seed}"


def f_proxy_median(row, med):
    return ((1.0 - med["cz_error_median"]) ** row["n_cz"] * (1.0 - med["measure_error_median"]) ** 12
            * math.exp(-row["S_T1"] - row["S_T2"]))


def error_medians(rec):
    cz = [e["cz_error"] for e in rec["edges"].values() if e.get("cz_error") is not None]
    ro = [v["measure_error"] for v in rec["qubits"].values() if v.get("measure_error") is not None]
    return {"cz_error_median": float(np.median(cz)), "measure_error_median": float(np.median(ro)),
            "cz_error_mean": float(np.mean(cz)), "measure_error_mean": float(np.mean(ro)),
            "n_cz_at_1": int(sum(1 for x in cz if x >= 0.999)),
            "n_measure_ge_0_2": int(sum(1 for x in ro if x >= 0.2))}


def select_candidates(scan, rec):
    """C2: the frozen canary, the top K by f_proxy (the prompt's mean-error proxy), the best by
    T_s and by n_cz, every default-order seed (L1 needs them), and -- an executor addition,
    recorded as such -- the top K by the median-error proxy."""
    rows = scan["rows"]
    med = error_medians(rec)
    for r in rows:
        r["f_proxy_median"] = f_proxy_median(r, med)
    picks = [("asis", None)]
    by = lambda key, rev: sorted(rows, key=lambda r: ((-r[key]) if rev else r[key], r["seed"], r["order"]))
    for r in by("f_proxy", True)[:K_SELECT]:
        picks.append(("top_f_proxy", r))
    picks.append(("best_T_s", by("T_s", False)[0]))
    picks.append(("best_n_cz", by("n_cz", False)[0]))
    for r in sorted((r for r in rows if r["order"] == list(DEFAULT_ORDER)), key=lambda r: r["seed"]):
        picks.append(("default_order_seed", r))
    for r in by("f_proxy_median", True)[:K_SELECT]:
        picks.append(("top_f_proxy_median (executor addition)", r))
    out, seen = [], {}
    for why, r in picks:
        cid = "asis" if r is None else cand_id(r["order"], r["seed"])
        if cid in seen:
            seen[cid]["why"].append(why)
            continue
        c = {"id": cid, "why": [why], "order": list(DEFAULT_ORDER) if r is None else r["order"],
             "seed": None if r is None else r["seed"], "scan_row": r}
        seen[cid] = c
        out.append(c)
    return out, med


_SEL = {}


def _select_init():
    rec, _ = fresh_record()
    _SEL.update(rec=rec, a=garbage_acceptance(0), survey=survey_winner()["physical_qubits"],
                u=uniform_scan_record(rec)[0])
    factory()


def _select_one(cand):
    t0 = time.time()
    qc = candidate_circuit(cand)
    det = None
    if cand["scan_row"] is not None:          # the transpiler is deterministic at a fixed seed
        st, _ = compile_stats(qc, _SEL["u"])
        det = {"n_cz": st["n_cz"] == cand["scan_row"]["n_cz"],
               "T_s": abs(st["T_s"] - cand["scan_row"]["T_s"]) <= 1e-15}
    res = embedding_search(qc, _SEL["rec"], _SEL["a"], survey_set=_SEL["survey"])
    res.update({k: cand[k] for k in ("id", "why", "order", "seed")})
    res["deterministic_retranspile"] = det
    res["seconds"] = time.time() - t0
    return res


def stage_select(args):
    from multiprocessing import Pool
    scan = load_json(p(OUT, "scan.json"))
    rec, info = fresh_record()
    cands, med = select_candidates(scan, rec)
    if args.candidates:
        cands = [c for c in cands if c["id"] in set(args.candidates)]
    pdir = p(OUT, "select_parts")
    todo = [c for c in cands if not os.path.exists(os.path.join(pdir, c["id"] + ".json"))]
    print(f"{len(cands)} candidates, {len(todo)} to search", flush=True)
    t0 = time.time()
    with Pool(args.workers, initializer=_select_init) as pool:
        for res in pool.imap_unordered(_select_one, todo):
            dump_json(res, os.path.join(pdir, res["id"] + ".json"))
            b = res["best"]
            print(f"  {res['id']} ({', '.join(res['why'])}): {res['n_scored']}/{res['n_embeddings']} "
                  f"scored; best f {b['f_dd_off']:.4e} T {b['T_s'] * 1e6:.2f} us on "
                  f"{b['physical_qubits']} [{res['seconds']:.0f} s, {time.time() - t0:.0f} s total]",
                  flush=True)
    parts = [load_json(os.path.join(pdir, c["id"] + ".json")) for c in cands
             if os.path.exists(os.path.join(pdir, c["id"] + ".json"))]
    res = {"stage": "select", "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
           "commit": git_commit(), "record": info["record"]["path"],
           "record_fingerprint": info["record"]["fingerprint"],
           "objective": "f_dd_off = f_gates x exp(-S_T1 - S_T2) (h0_patch_select, PTA echo end)",
           "error_statistics": med,
           "proxy_note": ("f_proxy uses the record's MEAN cz / readout error as prompts/23 C1 "
                          f"specifies; {med['n_cz_at_1']} edges carry IBM's uncalibrated marker "
                          f"1.0, so the mean cz error is {med['cz_error_mean']:.4f} against a median "
                          f"of {med['cz_error_median']:.5f} and the mean proxy ranks almost by CZ "
                          f"count alone.  The executor therefore ALSO admitted the top "
                          f"{K_SELECT} by the median-error proxy; the selection objective "
                          f"(PTA f on the fresh record) is unchanged."),
           "survey_patch": survey_winner()["physical_qubits"],
           "n_candidates": len(cands), "n_done": len(parts),
           "candidates": sorted(parts, key=lambda r: -r["best"]["f_dd_off"])}
    dump_json(res, p(OUT, "select.json"))
    print(f"wrote {rel(p(OUT, 'select.json'))}: {len(parts)} of {len(cands)} candidates")
    for r in res["candidates"][:12]:
        b = r["best"]
        print(f"  {r['id']:<60} f {b['f_dd_off']:.4e} f_gates {b['f_gates']:.4f} S_T1 {b['S_T1']:.3f} "
              f"S_T2 {b['S_T2']:.3f} T {b['T_s'] * 1e6:.2f} us n_cz {b['n_cz']} "
              f"active {r['pattern']['n_nodes']}")
    return 0


# --------------------------------------------------------------------------- row choice
def best_of(cands):
    """The best candidate by the selected PTA f (h0_patch_select.rank_key), ties broken by the
    term order then the seed -- e.g. hop1 / hop3 act on disjoint qubits, so swapping them gives
    the same circuit and the same score."""
    import h0_patch_select as ps
    return sorted(cands, key=lambda c: (ps.rank_key(c["best"]), tuple(c["order"]),
                                        -1 if c["seed"] is None else c["seed"]))[0]


def choose(select):
    cs = select["candidates"]
    asis = next(c for c in cs if c["id"] == "asis")
    l1 = best_of([c for c in cs if c["id"] != "asis" and c["order"] == list(DEFAULT_ORDER)])
    l2 = best_of([c for c in cs if c["id"] != "asis"])
    return {"L0": asis, "L1": l1, "L2": l2,
            "L2_is_reordered": l2["order"] != list(DEFAULT_ORDER),
            "L2_beats_L1": l2["best"]["f_dd_off"] > l1["best"]["f_dd_off"]}


def mapping_of(entry):
    return {int(k): int(v) for k, v in entry["mapping"].items()}


def relabelled(qc, mapping):
    import h0_patch_select as ps
    return ps.relabel(ps.circuit_ops(qc), qc.num_qubits, qc.num_clbits, mapping)


# --------------------------------------------------------------------------- verification (C4)
def exactness(tq, order, ref, theta):
    """C4: noiseless statevector of a TRANSPILED circuit (its own layout) against the exact
    coarse state in `order`, on the codewords; leakage outside them; ancillas back in |0>."""
    from skqd.hardware import logical_statevector, transpiled_layout
    from skqd.reference_sim import CodewordEmbedding
    fx = factory()
    emb = CodewordEmbedding(fx["M"])
    lay = transpiled_layout(tq, fx["n"])
    psi = logical_statevector(tq, fx["n"])
    exact = exact_state(order, ref, theta)
    dev = float(np.max(np.abs(emb.project(psi) - exact)))
    ov = complex(np.vdot(exact, emb.project(psi)))
    return {"max_abs_delta": dev, "leakage": float(emb.leakage(psi)),
            "overlap_abs": abs(ov), "measurement_consistent": bool(lay["measurement_consistent"]),
            "logical_to_physical": lay["logical_to_physical"],
            "ok": dev < AMP_TOL and emb.leakage(psi) < LEAK_TOL and lay["measurement_consistent"]}


# --------------------------------------------------------------------------- fractional (D)
def augment_target(base, fj):
    """D1: add rx(t) on every qubit and rzz(t) on every edge of the fractional read to a base
    target that already carries the record (`backend_from_record`).  None stays None."""
    from qiskit.circuit import Parameter
    from qiskit.circuit.library import RXGate, RZZGate
    from qiskit.transpiler import InstructionProperties
    t = base.target
    if "rx" in t.operation_names or "rzz" in t.operation_names:
        raise SystemExit("the base target already has rx / rzz: augment a plain base only")
    t.add_instruction(RXGate(Parameter("t")),
                      {(int(q),): InstructionProperties(duration=v["rx_duration_s"], error=v["rx_error"])
                       for q, v in fj["qubits"].items()})
    props = {}
    for e in fj["edges"].values():
        a, b = (int(x) for x in e["target_key"])
        for k in ((a, b), (b, a)):
            props[k] = InstructionProperties(duration=e["rzz_duration_s"], error=e["rzz_error"])
    t.add_instruction(RZZGate(Parameter("t")), props)
    return base


def fractional_record(record, fj):
    """D1: the plain record plus rx / rzz leaves -- a different record, with its own fingerprint
    (the plain record's fingerprint and rule D9 are untouched)."""
    from h0_backends import calibration_fingerprint
    rec = json.loads(json.dumps(record))
    for q, v in rec["qubits"].items():
        f = fj["qubits"].get(q) or {}
        v["rx_duration_s"] = f.get("rx_duration_s")
        v["rx_error"] = f.get("rx_error")
    by_pair = {}
    for e in fj["edges"].values():
        a, b = (int(x) for x in e["target_key"])
        by_pair[(min(a, b), max(a, b))] = e
    for e in rec["edges"].values():
        a, b = (int(x) for x in e["target_key"])
        f = by_pair.get((min(a, b), max(a, b))) or {}
        e["rzz_duration_s"] = f.get("rzz_duration_s")
        e["rzz_error"] = f.get("rzz_error")
    rec["record_kind"] = "fractional"
    rec["plain_fingerprint"] = record.get("fingerprint")
    rec["fingerprint"] = calibration_fingerprint(rec)
    rec["fractional_source"] = {"stamp": fj.get("stamp"), "last_update_date": fj.get("last_update_date")}
    return rec


def fresh_base(rec=None, fractional=False):
    from h0_backends import backend_from_record
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    if rec is None:
        rec, _ = fresh_record()
    base, binfo = backend_from_record(rec, base=FakeKingston(), strict=True)
    if fractional:
        augment_target(base, fractional_json())
    return base, binfo


def _absorb_pass():
    from qiskit.transpiler.basepasses import TransformationPass

    class AbsorbGlobalPhaseGates(TransformationPass):
        """Move the zero-qubit `global_phase` instructions FoldRzzAngle inserts into the
        circuit's global phase (they cost no time and carry no qubit)."""

        def run(self, dag):
            for node in list(dag.op_nodes()):
                if node.op.name == "global_phase":
                    dag.global_phase += node.op.params[0]
                    dag.remove_op_node(node)
            return dag
    return AbsorbGlobalPhaseGates()


def transpile_fractional(qc, base, seed):
    """D3: level 3 with the `ibm_dynamic_and_fractional` translation plugin.

    The plugin folds rzz angles into the calibrated [0, pi/2] (FoldRzzAngle) right after the
    translation stage, but the level-3 optimization loop re-synthesises two-qubit blocks AFTER
    it and re-emits rzz(-pi/2), which `qiskit_ibm_runtime.utils.validations.validate_rzz_pubs`
    rejects.  So FoldRzzAngle runs once more as the post-optimization stage of the SAME staged
    pass manager (the layout is kept), followed by the target's one-qubit re-merge and the
    absorption of the zero-qubit global-phase gates the fold inserts."""
    from qiskit.transpiler import PassManager, generate_preset_pass_manager
    from qiskit.transpiler.passes import Optimize1qGatesDecomposition
    from qiskit_ibm_runtime.transpiler.passes import FoldRzzAngle
    pm = generate_preset_pass_manager(optimization_level=3, backend=base, seed_transpiler=int(seed),
                                      translation_method="ibm_dynamic_and_fractional")
    pm.post_optimization = PassManager([FoldRzzAngle(),
                                        Optimize1qGatesDecomposition(target=base.target),
                                        _absorb_pass()])
    return pm.run(qc)


def rzz_valid_for_runtime(tq):
    """The runtime's own check (`is_valid_rzz_pub`): '' when every rzz angle is in [0, pi/2]."""
    from qiskit.primitives.containers.sampler_pub import SamplerPub
    from qiskit_ibm_runtime.utils.utils import is_valid_rzz_pub
    return is_valid_rzz_pub(SamplerPub.coerce(tq))


def rzz_angles(tq):
    return [float(i.operation.params[0]) for i in tq.data if i.operation.name == "rzz"]


def stage_fractional(args):
    from qiskit import transpile
    t0 = time.time()
    select = load_json(p(OUT, "select.json"))
    ch = choose(select)
    rec, info = fresh_record()
    fj = fractional_json()
    out = {"stage": "fractional", "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
           "commit": git_commit(), "versions": versions()}
    if fj is None or not (fj["has"]["rx"] and fj["has"]["rzz"]):
        out.update({"measured": False, "reason": "the fractional target lacks rx or rzz",
                    "carried": False})
        dump_json(out, p(OUT, "fractional.json"))
        print(out["reason"])
        return 0
    src = ch["L2"] if (ch["L2_is_reordered"] and ch["L2_beats_L1"]) else ch["L1"]
    src_label = "L2_order" if src is ch["L2"] else "L1_seed"
    man = factory()["man"]
    qc = ir_circuit(src["order"], man["reference"], man["dt"])
    frec = fractional_record(rec, fj)
    fbase, _ = fresh_base(rec, fractional=True)
    pbase, _ = fresh_base(rec, fractional=False)
    tf_raw = transpile(qc, backend=fbase, optimization_level=3, seed_transpiler=int(src["seed"]),
                       translation_method="ibm_dynamic_and_fractional")
    raw_angles = rzz_angles(tf_raw)
    tf = transpile_fractional(qc, fbase, src["seed"])
    runtime_msg = rzz_valid_for_runtime(tf)
    tp = transpile(qc, backend=pbase, optimization_level=3, seed_transpiler=int(src["seed"]))
    sf, _ = compile_stats(tf, frec)
    sp_, _ = compile_stats(tp, rec)
    angs = rzz_angles(tf)
    in_range = all(0.0 <= abs(x) <= math.pi / 2 + 1e-12 for x in angs) and \
        all(0.0 <= x <= math.pi / 2 + 1e-12 for x in angs)
    hist = {}
    for x in angs:
        k = f"{x / math.pi:.4f}"
        hist[k] = hist.get(k, 0) + 1
    fg_f = f_gates_on_record(tf, frec)
    fg_p = f_gates_on_record(tp, rec)
    ratio = sf["T_s"] / sp_["T_s"]
    ex_f = exactness(tf, src["order"], man["reference"], man["dt"])
    ex_p = exactness(tp, src["order"], man["reference"], man["dt"])
    a = garbage_acceptance(0)
    carried = ratio <= FRACTIONAL_MIN_GAIN
    sel_f = embedding_search(tf, frec, a, fractional=True)
    sel_p = embedding_search(tp, rec, a, fractional=False)
    ratio_sel = sel_f["best"]["T_s"] / sel_p["best"]["T_s"]
    from qiskit import qpy
    cdir = p(OUT, "circuits")
    os.makedirs(cdir, exist_ok=True)
    for name, c in (("D3_fractional_transpiled", tf), ("D3_plain_control_transpiled", tp)):
        buf = io.BytesIO()
        qpy.dump(c, buf, version=QPY_VERSION)
        with gzip.open(os.path.join(cdir, name + ".qpy.gz"), "wb") as fh:
            fh.write(buf.getvalue())
    out.update({
        "measured": True, "source_row": src_label, "source_candidate": src["id"],
        "order": src["order"], "seed": src["seed"],
        "translation_method": "ibm_dynamic_and_fractional + post-optimization FoldRzzAngle",
        "fractional_record_fingerprint": frec["fingerprint"],
        "plain_record_fingerprint": rec["fingerprint"],
        "fractional": {**{k: v for k, v in sf.items() if k != "active"}, "active": sf["active"],
                       "f_gates": fg_f[0], "n_2q": fg_f[1], "f_including_1q_errors": fg_f[2],
                       "rzz_angle_histogram_pi": dict(sorted(hist.items())),
                       "rzz_angles_in_0_pi_over_2": in_range, "n_rzz": len(angs),
                       "runtime_rzz_validation": runtime_msg or "valid (is_valid_rzz_pub returned '')",
                       "without_the_post_fold": {
                           "note": ("plain transpile(..., translation_method="
                                    "'ibm_dynamic_and_fractional'): the level-3 optimization "
                                    "loop re-emits rzz outside [0, pi/2] after the plugin's fold"),
                           "n_rzz": len(raw_angles),
                           "n_outside_0_pi_over_2": sum(1 for x in raw_angles
                                                        if not 0.0 <= x <= math.pi / 2 + 1e-12),
                           "ops": {k: int(v) for k, v in tf_raw.count_ops().items()}},
                       "exactness": ex_f, "selected": sel_f},
        "plain_control": {**{k: v for k, v in sp_.items() if k != "active"}, "active": sp_["active"],
                          "f_gates": fg_p[0], "n_2q": fg_p[1], "f_including_1q_errors": fg_p[2],
                          "exactness": ex_p, "selected": sel_p},
        "duration_ratio_fractional_over_plain": ratio,
        "duration_ratio_after_patch_selection": ratio_sel,
        "threshold": FRACTIONAL_MIN_GAIN,
        "carried": carried,
        "reason": (f"T_frac / T_plain = {ratio:.4f} {'<=' if carried else '>'} "
                   f"{FRACTIONAL_MIN_GAIN} on the live durations: the fractional rows are "
                   f"{'carried into the Aer table' if carried else 'recorded in the compile table and dropped from the Aer table'}"),
        "runtime_s": time.time() - t0})
    dump_json(out, p(OUT, "fractional.json"))
    print(f"source {src_label} {src['id']}: plain {sp_['n_cz']} CZ / {sp_['n_1q']} pulses / "
          f"T {sp_['T_s'] * 1e6:.2f} us; fractional {sf['n_cz']} CZ + {sf['n_rzz']} RZZ / "
          f"{sf['n_1q']} pulses / T {sf['T_s'] * 1e6:.2f} us -> ratio {ratio:.4f}; after "
          f"selection {ratio_sel:.4f}")
    print(f"f_gates plain {fg_p[0]:.4f} fractional {fg_f[0]:.4f}; selected PTA f plain "
          f"{sel_p['best']['f_dd_off']:.4e} fractional {sel_f['best']['f_dd_off']:.4e}")
    print(f"C4 fractional {ex_f['max_abs_delta']:.2e} / {ex_f['leakage']:.2e}; plain "
          f"{ex_p['max_abs_delta']:.2e}; rzz angles in [0, pi/2]: {in_range} {hist}")
    print(out["reason"])
    return 0


# --------------------------------------------------------------------------- rows (C3)
def scheduled(circ, backend, method):
    """`gate_H0P.schedule_circuit` for ASAP or ALAP: explicit delays, no non-delay op moved."""
    from qiskit import transpile
    before = {k: v for k, v in circ.count_ops().items() if k != "delay"}
    sched = transpile(circ, backend=backend, optimization_level=0, scheduling_method=method,
                      seed_transpiler=SCHEDULE_SEED)
    after = {k: v for k, v in sched.count_ops().items() if k != "delay"}
    if before != after:
        raise SystemExit(f"scheduling changed the operations: before {before}, after {after}")
    return sched, {"method": method, "n_delays": int(sched.count_ops().get("delay", 0)),
                   "ops_non_delay": {k: int(v) for k, v in sorted(after.items())},
                   "seed_transpiler": SCHEDULE_SEED}


def delay_schedule(sched, rec, include_leading):
    """The idle windows of a scheduled circuit read from its explicit delays (C7).

    Per qubit: a delay before the qubit's first gate is LEADING (the qubit is still in |0>,
    where neither T1 nor T2 acts), a delay after its measure is trailing and is never counted;
    every other delay is a window.  Returned in `skqd.idle.schedule_asap`'s format so that
    `idle.idle_budget` evaluates it unchanged."""
    dt = float(rec["dt_s"])
    nq = sched.num_qubits
    seen = [False] * nq
    measured = [False] * nq
    windows = {}
    leading = {}
    active = set()
    for inst in sched.data:
        nm = inst.operation.name
        qs = [sched.find_bit(q).index for q in inst.qubits]
        if nm == "barrier":
            continue
        if nm == "delay":
            q = qs[0]
            d = float(inst.operation.duration) * dt
            if measured[q] or d <= 0.0:
                continue
            if not seen[q]:
                leading.setdefault(q, []).append(d)
                if include_leading:
                    windows.setdefault(q, []).append(d)
            else:
                windows.setdefault(q, []).append(d)
            continue
        for q in qs:
            active.add(q)
            if nm == "measure":
                measured[q] = True
            else:
                seen[q] = True
    act = sorted(active)
    per_q = {q: {"busy_s": 0.0, "delay_s": float(sum(windows.get(q, []))),
                 "idle_s": float(sum(windows.get(q, []))), "windows_s": windows.get(q, [])}
             for q in act}
    return {"active": act, "per_qubit": per_q,
            "leading_s": {q: float(sum(v)) for q, v in leading.items()}}


def t2_scaled(rec, qubits, r):
    return {int(q): float(rec["qubits"][str(q)]["T2_s"]) * float(r) for q in qubits}


def pta_at(sch, rec, f_gates, r=1.0, t2=None):
    from skqd import idle
    t2 = t2 if t2 is not None else t2_scaled(rec, sch["active"], r)
    _pq, tot = idle.idle_budget(sch, rec, t2_s=t2)
    return {"S_T1": tot["S_T1"], "S_T2": tot["S_T2"], "S_DD": tot["S_DD"],
            "S_T2_eligible": tot["S_T2_eligible"], "S_T2_ineligible": tot["S_T2_ineligible"],
            "dd_eligible": tot["dd_eligible"],
            "f": f_gates * math.exp(-tot["S_T1"] - tot["S_T2"]),
            "f_dd_ceiling_rho0": f_gates * math.exp(-tot["S_T1"] - tot["S_T2_ineligible"] - tot["S_DD"])}


def r_crit_pta(sch, rec, f_gates, target):
    """Bisection on log r of f_PTA(r) = target; None when f(r = 1) < target."""
    f1 = pta_at(sch, rec, f_gates, 1.0)["f"]
    if f1 < target:
        return None
    lo, hi = math.log(1e-4), 0.0
    if pta_at(sch, rec, f_gates, math.exp(lo))["f"] >= target:
        return math.exp(lo)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if pta_at(sch, rec, f_gates, math.exp(mid))["f"] >= target:
            hi = mid
        else:
            lo = mid
    return math.exp(hi)


def fez_ratio_table():
    d = load_json(p("validation", "S2D_idle.json"))["data"]["t2_bracket"]
    return {int(k): float(v) for k, v in d["per_qubit_ratio"].items()}, float(d["fallback_ratio"])


def fez_transfer_t2(rec, row_l2p, active):
    """The fez per-qubit ratio table transferred by LOGICAL role (information only): logical
    qubit i sat on fez physical canary_l2p[i]; its measured ratio goes to the row's physical
    qubit of logical i; routing ancillas take the fallback."""
    table, fb = fez_ratio_table()
    canary_l2p = factory()["man"]["logical_to_physical"]
    ratio = {int(q): fb for q in active}
    for i, q in enumerate(row_l2p):
        ratio[int(q)] = table.get(int(canary_l2p[i]), fb)
    return {q: float(rec["qubits"][str(q)]["T2_s"]) * ratio[q] for q in active}, ratio


def row_specs(select, frac):
    """The rows of C3: (id, candidate, schedule, fractional?)."""
    ch = choose(select)
    specs = [("L0_asis_asap", ch["L0"], "asap", False), ("L0_asis_alap", ch["L0"], "alap", False),
             ("L1_seed", ch["L1"], "asap", False), ("L2_order", ch["L2"], "asap", False)]
    if frac and frac.get("measured"):
        specs.append(("L3_rx", None, "asap", True))
    return specs, ch


def stage_rows(args):
    """C3: every row's circuit (relabelled onto its winning embedding), QPY v13 + manifest,
    compile statistics, C4 exactness, C7 scheduling checks and the PTA rows of E1."""
    from h0_qpu_time import circuit_duration_s
    from qiskit import qpy
    from skqd import idle
    t0 = time.time()
    select = load_json(p(OUT, "select.json"))
    frac = load_json(p(OUT, "fractional.json")) if os.path.exists(p(OUT, "fractional.json")) else None
    rec, info = fresh_record()
    frec = fractional_record(rec, fractional_json()) if frac and frac.get("measured") else None
    specs, ch = row_specs(select, frac)
    man = factory()["man"]
    cdir = p(OUT, "circuits")
    os.makedirs(cdir, exist_ok=True)
    built = {}
    rows = {}
    for rid, cand, method, is_frac in specs:
        if is_frac:
            with gzip.open(os.path.join(cdir, "D3_fractional_transpiled.qpy.gz"), "rb") as fh:
                tq = qpy.load(fh)[0]
            entry = frac["fractional"]["selected"]["best"]
            order, seed, cid = frac["order"], frac["seed"], frac["source_candidate"]
            r_rec = frec
        else:
            key = cand["id"]
            if key not in built:
                built[key] = candidate_circuit(cand)
            tq = built[key]
            entry = cand["best"]
            order, seed, cid = cand["order"], cand["seed"], cand["id"]
            r_rec = rec
        rows[rid] = {"tq": tq, "entry": entry, "order": order, "seed": seed, "candidate": cid,
                     "schedule": method, "fractional": is_frac, "rec": r_rec}
    # L4_all: the best of L1-L3 by the selected PTA f, scheduled ALAP
    pool = [k for k in ("L1_seed", "L2_order", "L3_rx") if k in rows
            and not (k == "L3_rx" and not frac.get("carried"))]
    best4 = max(pool, key=lambda k: rows[k]["entry"]["f_dd_off"])
    rows["L4_all"] = dict(rows[best4], schedule="alap", built_from=best4)
    # executor addition: the best the SIGNED family can do (default order) scheduled ALAP
    rows["L1_seed_alap"] = dict(rows["L1_seed"], schedule="alap", built_from="L1_seed",
                                executor_addition=True)

    out_rows = {}
    for rid in list(rows):
        r = rows[rid]
        mp = mapping_of(r["entry"])
        rc = relabelled(r["tq"], mp)
        r_rec = r["rec"]
        st, sch = compile_stats(rc, r_rec)
        ex = exactness(r["tq"], r["order"], man["reference"], man["dt"])
        fg, n2, f1 = f_gates_on_record(rc, r_rec)
        base, _ = fresh_base(rec, fractional=r["fractional"])
        sched, sinfo = scheduled(rc, base, r["schedule"])
        tgt = base.target
        d_sched = circuit_duration_s(sched, tgt.durations(), tgt)
        d_unsched = circuit_duration_s(rc, tgt.durations(), tgt)
        dsch_in = delay_schedule(sched, r_rec, include_leading=True)
        dsch_ex = delay_schedule(sched, r_rec, include_leading=False)
        _pq, tot_unsched = idle.idle_budget(sch, r_rec)
        _pq, tot_in = idle.idle_budget(dsch_in, r_rec)
        _pq, tot_ex = idle.idle_budget(dsch_ex, r_rec)
        c7 = {"no_non_delay_op_changed": True,
              "scheduled_duration_s": d_sched, "unscheduled_duration_s": d_unsched,
              "idle_T_total_s": sch["T_total_s"],
              "duration_agreement_s": max(abs(d_sched - sch["T_total_s"]),
                                          abs(d_unsched - sch["T_total_s"])),
              "budget_unscheduled": {"S_T1": tot_unsched["S_T1"], "S_T2": tot_unsched["S_T2"]},
              "budget_delays_leading_included": {"S_T1": tot_in["S_T1"], "S_T2": tot_in["S_T2"]},
              "budget_delays_leading_excluded": {"S_T1": tot_ex["S_T1"], "S_T2": tot_ex["S_T2"]},
              "leading_delay_s": dsch_ex["leading_s"]}
        if r["schedule"] == "asap":
            c7["asap_budget_match"] = max(abs(tot_in["S_T1"] - tot_unsched["S_T1"]),
                                          abs(tot_in["S_T2"] - tot_unsched["S_T2"]))
        # E1: the PTA on the windows this row actually has (ASAP: the idle schedule; ALAP:
        # the explicit delay windows with the leading |0> delays excluded)
        psch = sch if r["schedule"] == "asap" else dsch_ex
        pta = {str(x): pta_at(psch, r_rec, fg, x) for x in RATIOS}
        rc01 = {str(t): r_crit_pta(psch, r_rec, fg, t) for t in BARS}
        l2p = [mp.get(int(q), int(q)) for q in ex["logical_to_physical"]]
        t2f, ratios_f = fez_transfer_t2(r_rec, l2p, psch["active"])
        pta_fez = pta_at(psch, r_rec, fg, t2=t2f)
        name = f"{rid}.qpy.gz"
        buf = io.BytesIO()
        qpy.dump(rc, buf, version=QPY_VERSION)
        with gzip.open(os.path.join(cdir, name), "wb") as fh:
            fh.write(buf.getvalue())
        sha = hashlib.sha256(open(os.path.join(cdir, name), "rb").read()).hexdigest()
        pat_adj, pat_edges = interaction_graph_2q(rc)
        manifest = {"row": rid, "candidate": r["candidate"], "order": r["order"], "seed": r["seed"],
                    "schedule": r["schedule"], "fractional": r["fractional"],
                    "built_from": r.get("built_from"),
                    "executor_addition": bool(r.get("executor_addition")),
                    "mapping_transpiled_to_kingston": {str(k): v for k, v in sorted(mp.items())},
                    "physical_qubits": r["entry"]["physical_qubits"],
                    "logical_to_physical": l2p, "n_2q": n2, "n_cz": st["n_cz"],
                    "n_rzz": st["n_rzz"], "T_s": st["T_s"],
                    "pattern_edges": [list(e) for e in pat_edges],
                    "reference": int(man["reference"]), "twoB": int(man["twoB"]), "k": 1,
                    "dt": float(man["dt"]), "qpy": f"{rel(cdir)}/{name}",
                    "qpy_version": QPY_VERSION, "qpy_gz_sha256": sha,
                    "record_fingerprint": r_rec["fingerprint"]}
        dump_json(manifest, os.path.join(cdir, f"{rid}.json"))
        out_rows[rid] = {
            "manifest": manifest, "compile": st, "f_gates": fg, "f_including_1q_errors": f1,
            "selected_pta_echo": r["entry"]["f_dd_off"],
            "exactness": ex, "c7": c7, "schedule_info": sinfo,
            "pta": pta, "r_crit_pta": rc01,
            "pta_fez_table_transferred": {**pta_fez, "ratios": {str(k): v for k, v in ratios_f.items()},
                                          "label": "fez table transferred, information"},
            "dd_ceiling_rho0_echo": pta["1.0"]["f_dd_ceiling_rho0"],
        }
        print(f"{rid:<14} {r['schedule']} T {st['T_s'] * 1e6:6.2f} us  2q {n2}  f_gates {fg:.4f}  "
              f"PTA r=1 {pta['1.0']['f']:.4e} (S_T1 {pta['1.0']['S_T1']:.3f} S_T2 {pta['1.0']['S_T2']:.3f})"
              f"  r=0.174 {pta['0.174']['f']:.4e}  r_crit(0.1) {rc01['0.1']}  C4 {ex['max_abs_delta']:.1e}/"
              f"{ex['leakage']:.1e}  C7 dur {c7['duration_agreement_s']:.1e} "
              f"asap-match {c7.get('asap_budget_match')}", flush=True)
    for rid, v in out_rows.items():
        v["duration_ratio_to_L0"] = v["compile"]["T_s"] / out_rows["L0_asis_asap"]["compile"]["T_s"]
    # the DD ceiling row (PTA only)
    ceiling = {"row": "L0_asis_dd_ceiling", "f_dd_ceiling_rho0": out_rows["L0_asis_asap"]["dd_ceiling_rho0_echo"],
               "S_DD": out_rows["L0_asis_asap"]["pta"]["1.0"]["S_DD"],
               "dd_eligible": out_rows["L0_asis_asap"]["pta"]["1.0"]["dd_eligible"],
               "label": "ceiling, not a prediction (DD at rho = 0 with the record's XY4 pulse cost)"}
    res = {"stage": "rows", "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "commit": git_commit(),
           "record_fingerprint": rec["fingerprint"], "choice": {
               "L0": ch["L0"]["id"], "L1": ch["L1"]["id"], "L2": ch["L2"]["id"],
               "L2_is_reordered": ch["L2_is_reordered"], "L2_beats_L1": ch["L2_beats_L1"],
               "L4_built_from": rows["L4_all"]["built_from"]},
           "rows": out_rows, "dd_ceiling": ceiling, "runtime_s": time.time() - t0}
    dump_json(res, p(OUT, "rows.json"))
    print(f"wrote {rel(p(OUT, 'rows.json'))} ({time.time() - t0:.0f} s)")
    return 0


# --------------------------------------------------------------------------- Aer cells (E2)
def aer_dir():
    _rec, info = fresh_record()
    return p("data", "hardware", f"S2D_levers_{info['record']['stamp']}", "aer")


def chunk_seed(chunk, shots=SHOTS_PER_CHUNK, base=SEED_BASE):
    from gate_H0_model import chunk_seed as cs
    return cs(base, chunk, shots)


def cell_path(row, ratio, sched, chunk):
    return os.path.join(aer_dir(), f"{row}_r{ratio}_{sched}_chunk{chunk}.json")


def load_row_circuit(rid):
    from qiskit import qpy
    man = load_json(p(OUT, "circuits", f"{rid}.json"))
    with gzip.open(p(man["qpy"]), "rb") as fh:
        return qpy.load(fh)[0], man


def run_cell(qc, base, rec, active, ratio, method, seed, shots, path, meta):
    """One seeded Aer chunk on the scheduled circuit; written once, refused rather than re-drawn."""
    from gate_H0P import apply_t2_override
    from qiskit_aer import AerSimulator
    if os.path.exists(path):
        print(f"{rel(path)} exists: counts files are write-once, not re-drawn")
        return load_json(path)
    t0 = time.time()
    t2 = None
    if abs(float(ratio) - 1.0) > 1e-15:
        ov = {"source": f"uniform ratio {ratio} x the record's echo T2 (planner construction)",
              "per_qubit": {str(q): {"T2_s": float(rec["qubits"][str(q)]["T2_s"]) * float(ratio),
                                     "provenance": f"{ratio} x record T2"} for q in active}}
        t2 = apply_t2_override(base, ov)
    sched, sinfo = scheduled(qc, base, method)
    sim = AerSimulator.from_backend(base, seed_simulator=int(seed))
    ts = time.time()
    counts = sim.run(sched, shots=int(shots)).result().get_counts()
    secs = time.time() - ts
    rec_out = {**meta, "ratio": float(ratio), "schedule": method, "seed_simulator": int(seed),
               "shots": int(shots), "t2_override": t2, "schedule_info": sinfo,
               "versions": versions(), "seconds": secs, "total_seconds": time.time() - t0,
               "when": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
               "counts": {str(k): int(v) for k, v in counts.items()}}
    dump_json(rec_out, path)
    print(f"  {rel(path)}: {shots} shots in {secs:.0f} s", flush=True)
    return rec_out


def decode_cell(counts_list, order, twoB=0, ref=None, theta=None):
    """Pool chunks and read them with both clean-yield statistics."""
    from gate_H0_model import decode_histogram
    from skqd.codec import Codec
    from skqd.skqd import clean_fraction_mixture, reference_string_test
    fx = factory()
    man = fx["man"]
    ref = int(man["reference"]) if ref is None else int(ref)
    theta = float(man["dt"]) if theta is None else float(theta)
    codec = Codec(fx["M"].basis)
    d = ideal_distribution(order, twoB, ref, theta)
    pos = {int(b): i for i, b in enumerate(d["sector_indices"])}
    refbits = tuple(int(x) for x in codec.encode(fx["M"].basis.labels[ref]))
    dist = {int(b): int(sum(x != y for x, y in zip(codec.encode(fx["M"].basis.labels[int(b)]), refbits)))
            for b in d["sector_indices"]}
    a = garbage_acceptance(twoB)
    n_bins = max(max(dist.values()) + 1, 9)
    tot = np.zeros(d["dim"])
    shots = 0
    per = []
    for c in counts_list:
        n, _h, sh = decode_histogram(c["counts"], codec, dist, pos, twoB, n_bins)
        tot += n
        shots += sh
        per.append({"seed_simulator": c.get("seed_simulator"), "shots": sh, "accepted": int(n.sum()),
                    "reference_hits": int(round(float(n[d["reference_position"]])))})
    n_ref = int(round(float(tot[d["reference_position"]])))
    rst = reference_string_test(n_ref, shots, d["p_reference"], a, d["dim"])
    mix = clean_fraction_mixture(tot, d["p"], d["dim"], shots)
    fr, fm = rst["f_clean"], mix["f_clean"]
    return {"shots": shots, "accepted": int(tot.sum()), "reference_hits": n_ref,
            "p_reference": d["p_reference"], "garbage_acceptance": a, "dim": d["dim"],
            "expected_reference_hits_from_garbage": rst["expected_from_garbage"],
            "f_clean_reference": fr, "f_clean_reference_68": rst["f_clean_68"],
            "f_clean_mixture": fm, "f_clean_mixture_68": mix["f_clean_68"], "w": mix["w"],
            "c6_relative_deviation": (abs(fm - fr) / fr) if fr else None,
            "chunks": per}


def stage_aer(args):
    """E2: `--row R --ratio r [--chunk i]` (all base chunks when --chunk is omitted)."""
    rid = args.row
    if rid == "P7":
        return stage_p7(args)
    if rid.startswith("E4:"):
        return stage_e4_aer(args)
    rows = load_json(p(OUT, "rows.json"))["rows"]
    if rid not in rows:
        raise SystemExit(f"no row {rid}; rows: {sorted(rows)}")
    rv = rows[rid]
    qc, man = load_row_circuit(rid)
    rec, _info = fresh_record()
    ratios = [args.ratio] if args.ratio is not None else list(RATIOS)
    chunks = [args.chunk] if args.chunk is not None else list(range(CHUNKS))
    for r in ratios:
        for c in chunks:
            path = cell_path(rid, r, man["schedule"], c)
            if os.path.exists(path):
                print(f"{rel(path)} exists, skipped")
                continue
            base, _ = fresh_base(rec, fractional=man["fractional"])
            run_cell(qc, base, rec, rv["compile"]["active"], r, man["schedule"], chunk_seed(c),
                     SHOTS_PER_CHUNK, path,
                     {"gate": "S2D_levers", "row": rid, "chunk": int(c),
                      "circuit": man["qpy"], "record_fingerprint": man["record_fingerprint"],
                      "simulator": "AerSimulator.from_backend(backend_from_record(fresh record, "
                                   "FakeKingston(), strict=True)" + (" + augment_target" if man["fractional"] else "") + ")"})
    return 0


def cells_of(rid, sched, ratio):
    out = []
    c = 0
    while True:
        path = cell_path(rid, ratio, sched, c)
        if not os.path.exists(path):
            break
        out.append(load_json(path))
        c += 1
    return out


def stage_p7(args):
    """C3(iii): the two P7 cells on the COMMITTED record, survey mapping, 2000 shots, seed 11."""
    rec = committed_kingston()
    w = survey_winner()
    qc = relabelled(canary_circuit(), {int(k): int(v) for k, v in w["mapping"].items()})
    from h0_backends import backend_from_record
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    for method in ("asap", "alap"):
        path = os.path.join(aer_dir(), f"P7_committed_{method}_seed{SEED_BASE}.json")
        base, _ = backend_from_record(rec, base=FakeKingston(), strict=True)
        run_cell(qc, base, rec, w["physical_qubits"], 1.0, method, SEED_BASE, SHOTS_PER_CHUNK, path,
                 {"gate": "S2D_levers", "row": "P7", "record": COMMITTED_KINGSTON,
                  "record_fingerprint": rec["fingerprint"]})
    return 0


# --------------------------------------------------------------------------- family (F)
def family_members():
    """Every (sector, reference, k = 1..4) r = 1 circuit of the frozen set's parameters."""
    out = []
    for m in factory()["mans"]:
        if int(m["repetitions"]) != 1:
            continue
        out.append({"id": m["id"].replace("_rep1", ""), "frozen_id": m["id"], "sector": m["sector"],
                    "twoB": int(m["twoB"]), "reference": int(m["reference"]), "k": int(m["k"]),
                    "dt": float(m["dt"]), "theta": int(m["k"]) * float(m["dt"])})
    return sorted(out, key=lambda x: x["id"])


def family_tag(order, seed, fractional):
    return "-".join(order) + f"_s{seed}" + ("_frac" if fractional else "")


def reach(order):
    """Reach of the exact 99.9 % support per sector: the support states (exact_support of
    |ground state|^2 at eps = 1e-3) that have p >= 1e-3 in at least one family circuit."""
    from skqd.skqd import exact_support
    M = factory()["M"]
    out = {}
    for sec, twoB in (("B=0", 0), ("B=1", 2)):
        ref = M.reference(G2, twoB)
        prob = np.abs(ref.ground) ** 2
        S = set(int(i) for i in exact_support(prob, 1e-3))
        seen = set()
        for c in family_members():
            if c["twoB"] != twoB:
                continue
            d = ideal_distribution(order, twoB, c["reference"], c["theta"])
            seen |= {i for i, x in enumerate(d["p"]) if x >= 1e-3}
        out[sec] = {"support_size": len(S), "reached": len(S & seen),
                    "reach": len(S & seen) / len(S), "missing_positions": sorted(S - seen),
                    "n_states_p_ge_1e-3_in_family": len(seen)}
    return out


def stage_family(args):
    """F1: the family of each order the rows use, transpiled with the row's seed."""
    from qiskit import qpy
    t0 = time.time()
    rows = load_json(p(OUT, "rows.json"))
    rec, _info = fresh_record()
    fbase = None
    jobs = []
    for rid in ("L1_seed", "L2_order", "L3_rx"):
        if rid not in rows["rows"]:
            continue
        m = rows["rows"][rid]["manifest"]
        key = (tuple(m["order"]), int(m["seed"]), bool(m["fractional"]))
        if key not in [j[0] for j in jobs]:
            jobs.append((key, rid))
    out = {"stage": "family", "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
           "commit": git_commit(), "families": {}}
    reaches = {}
    for (order, seed, is_frac), rid in jobs:
        tag = family_tag(order, seed, is_frac)
        fdir = p(OUT, "family", tag)
        os.makedirs(fdir, exist_ok=True)
        if is_frac and fbase is None:
            fbase, _ = fresh_base(rec, fractional=True)
        circs = []
        for c in family_members():
            qc = ir_circuit(list(order), c["reference"], c["theta"])
            tq = (transpile_fractional(qc, fbase, seed) if is_frac else transpile_plain(qc, seed))
            ex = exactness(tq, list(order), c["reference"], c["theta"])
            d = ideal_distribution(list(order), c["twoB"], c["reference"], c["theta"])
            _adj, edges = interaction_graph_2q(tq)
            ops = {k: int(v) for k, v in tq.count_ops().items()}
            entry = {**c, "n_2q": ops.get("cz", 0) + ops.get("rzz", 0), "n_cz": ops.get("cz", 0),
                     "n_rzz": ops.get("rzz", 0), "depth": int(tq.depth()),
                     "pattern_edges": [list(e) for e in edges],
                     "max_abs_delta": ex["max_abs_delta"], "leakage": ex["leakage"],
                     "measurement_consistent": ex["measurement_consistent"],
                     "exact_ok": ex["ok"], "p_reference": d["p_reference"],
                     "ideal_p": [float(x) for x in d["p"]]}
            if is_frac:
                entry["rzz_angles_ok"] = rzz_valid_for_runtime(tq) == ""
            buf = io.BytesIO()
            qpy.dump(tq, buf, version=QPY_VERSION)
            with gzip.open(os.path.join(fdir, c["id"] + ".qpy.gz"), "wb") as fh:
                fh.write(buf.getvalue())
            circs.append(entry)
        if tuple(order) not in reaches:
            reaches[tuple(order)] = reach(list(order))
        pats = {json.dumps(x["pattern_edges"]) for x in circs}
        n2 = {x["n_2q"] for x in circs}
        deps = {x["depth"] for x in circs}
        out["families"][tag] = {
            "row": rid, "order": list(order), "seed": seed, "fractional": is_frac,
            "n_circuits": len(circs),
            "structure_identical": {"pattern": len(pats) == 1, "n_2q": len(n2) == 1,
                                    "depth": len(deps) == 1, "n_distinct_patterns": len(pats),
                                    "n_2q_values": sorted(n2), "depth_values": sorted(deps)},
            "max_abs_delta": max(x["max_abs_delta"] for x in circs),
            "max_leakage": max(x["leakage"] for x in circs),
            "all_measurement_consistent": all(x["measurement_consistent"] for x in circs),
            "all_exact_ok": all(x["exact_ok"] for x in circs),
            "all_rzz_angles_ok": (all(x["rzz_angles_ok"] for x in circs) if is_frac else None),
            "p_ref_k1": {x["id"]: x["p_reference"] for x in circs if x["k"] == 1},
            "reach": reaches[tuple(order)], "circuits": circs, "qpy_dir": rel(fdir)}
        f = out["families"][tag]
        print(f"{tag}: {len(circs)} circuits; max |d| {f['max_abs_delta']:.1e}, leakage "
              f"{f['max_leakage']:.1e}; patterns {f['structure_identical']['n_distinct_patterns']}, "
              f"n_2q {f['structure_identical']['n_2q_values']}; reach "
              f"{ {s: round(v['reach'], 4) for s, v in f['reach'].items()} }; p_ref k=1 "
              f"{ {k: round(v, 4) for k, v in f['p_ref_k1'].items()} }", flush=True)
    if tuple(DEFAULT_ORDER) not in reaches:
        reaches[tuple(DEFAULT_ORDER)] = reach(list(DEFAULT_ORDER))
    out["reach_default_order"] = reaches[tuple(DEFAULT_ORDER)]
    out["p_ref_default_order_k1"] = {c["id"]: ideal_distribution(list(DEFAULT_ORDER), c["twoB"], c["reference"],
                                                                 c["theta"])["p_reference"]
                                     for c in family_members() if c["k"] == 1}
    out["runtime_s"] = time.time() - t0
    dump_json(out, p(OUT, "family.json"))
    print(f"default-order reach {out['reach_default_order']['B=0']['reach']:.4f} / "
          f"{out['reach_default_order']['B=1']['reach']:.4f}; wrote {rel(p(OUT, 'family.json'))} "
          f"({time.time() - t0:.0f} s)")
    return 0


# --------------------------------------------------------------------------- E4
def family_on_patch(rid, rows, rec, frec):
    """Every r = 1 circuit of row `rid`'s family placed on the row's patch: the row's mapping
    when the circuit's pattern is the row's, else the best embedding onto the SAME qubit set,
    else (recorded) the best embedding anywhere."""
    from qiskit import qpy
    fam = load_json(p(OUT, "family.json"))
    m = rows["rows"][rid]["manifest"]
    tag = family_tag(m["order"], m["seed"], m["fractional"])
    F = fam["families"][tag]
    r_rec = frec if m["fractional"] else rec
    row_qc, _ = load_row_circuit(rid)
    mp = {int(k): int(v) for k, v in m["mapping_transpiled_to_kingston"].items()}
    row_pattern = sorted(tuple(sorted(int(x) for x in e)) for e in
                         interaction_graph_2q(_unrelabelled_row(rid))[1])
    patch = set(m["physical_qubits"])
    a = {0: garbage_acceptance(0), 2: garbage_acceptance(2)}
    out = []
    for c in F["circuits"]:
        with gzip.open(p(F["qpy_dir"], c["id"] + ".qpy.gz"), "rb") as fh:
            tq = qpy.load(fh)[0]
        pat = sorted(tuple(e) for e in c["pattern_edges"])
        how = None
        if pat == row_pattern:
            mapping, how = mp, "the row's mapping (identical pattern)"
        else:
            s = embedding_search(tq, r_rec, a[c["twoB"]], fractional=m["fractional"], top=10 ** 6)
            same = [e for e in s["top"] if set(e["physical_qubits"]) == patch]
            if same:
                mapping, how = mapping_of(same[0]), "best embedding onto the row's qubit set"
            else:
                mapping, how = mapping_of(s["best"]), "best embedding anywhere (the row's set admits none)"
        rc = relabelled(tq, mapping)
        out.append({"member": c, "circuit": rc, "placement": how, "mapping": mapping, "rec": r_rec})
    return out, tag


_UNREL = {}


def _unrelabelled_row(rid):
    """The row's transpiled circuit before relabelling (for its pattern on the transpiler's qubits)."""
    if rid not in _UNREL:
        rows = load_json(p(OUT, "rows.json"))["rows"]
        m = rows[rid]["manifest"]
        if m["fractional"]:
            from qiskit import qpy
            with gzip.open(p(OUT, "circuits", "D3_fractional_transpiled.qpy.gz"), "rb") as fh:
                _UNREL[rid] = qpy.load(fh)[0]
        else:
            sel = load_json(p(OUT, "select.json"))
            cand = next(c for c in sel["candidates"] if c["id"] == m["candidate"])
            _UNREL[rid] = candidate_circuit(cand)
    return _UNREL[rid]


E4_AER = ("B0_ref06_k4", "B1_ref07_k1", "B1_ref07_k4")   # prompts/23 names B1_ref00: see NOTES
E4_RATIOS = (1.0, 0.174)


def stage_e4(args):
    """E4 PTA: all 28 r = 1 circuits of the recommended row's family on the selected patch."""
    from skqd import idle
    rid = args.row
    rows = load_json(p(OUT, "rows.json"))
    rec, _ = fresh_record()
    m = rows["rows"][rid]["manifest"]
    frec = fractional_record(rec, fractional_json()) if m["fractional"] else None
    placed, tag = family_on_patch(rid, rows, rec, frec)
    from qiskit import qpy
    edir = p(OUT, "e4", rid)
    os.makedirs(edir, exist_ok=True)
    per = []
    for x in placed:
        c, rc, r_rec = x["member"], x["circuit"], x["rec"]
        fg, n2, f1 = f_gates_on_record(rc, r_rec)
        sch = idle.schedule_asap(rc, r_rec)
        if m["schedule"] == "alap":
            base, _ = fresh_base(rec, fractional=m["fractional"])
            sched, _ = scheduled(rc, base, "alap")
            psch = delay_schedule(sched, r_rec, include_leading=False)
        else:
            psch = sch
        pt = {str(r): pta_at(psch, r_rec, fg, r)["f"] for r in E4_RATIOS}
        buf = io.BytesIO()
        qpy.dump(rc, buf, version=QPY_VERSION)
        with gzip.open(os.path.join(edir, c["id"] + ".qpy.gz"), "wb") as fh:
            fh.write(buf.getvalue())
        per.append({"id": c["id"], "sector": c["sector"], "k": c["k"], "reference": c["reference"],
                    "placement": x["placement"], "physical_qubits": sorted(set(x["mapping"].values())),
                    "n_2q": n2, "T_s": sch["T_s"], "T_total_s": sch["T_total_s"], "f_gates": fg,
                    "pta": pt})
        print(f"  {c['id']:<14} {x['placement'][:40]:<40} T {sch['T_s'] * 1e6:6.2f} us f_gates "
              f"{fg:.4f} PTA r=1 {pt['1.0']:.4e} r=0.174 {pt['0.174']:.4e}", flush=True)
    summ = {}
    for r in E4_RATIOS:
        v = [x["pta"][str(r)] for x in per]
        summ[str(r)] = {"mean": float(np.mean(v)), "worst": float(np.min(v)),
                        "meets_0.1_mean": float(np.mean(v)) >= 0.1, "meets_0.05_worst": float(np.min(v)) >= 0.05}
    out = {"stage": "e4", "row": rid, "family": tag, "schedule": m["schedule"],
           "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "commit": git_commit(),
           "circuits": per, "pta_summary": summ, "qpy_dir": rel(edir)}
    dump_json(out, p(OUT, f"e4_{rid}.json"))
    print(f"E4 {rid}: " + "; ".join(f"r={r}: mean {v['mean']:.4e} worst {v['worst']:.4e}" for r, v in summ.items()))
    return 0


def stage_e4_aer(args):
    """E4 Aer: `--row E4:<row>` -> the three named circuits at r = 1 and 0.174, 4000 shots."""
    from qiskit import qpy
    rid = args.row.split(":", 1)[1]
    e4 = load_json(p(OUT, f"e4_{rid}.json"))
    rows = load_json(p(OUT, "rows.json"))
    m = rows["rows"][rid]["manifest"]
    rec, _ = fresh_record()
    for cid in E4_AER:
        c = next(x for x in e4["circuits"] if x["id"] == cid)
        with gzip.open(p(e4["qpy_dir"], cid + ".qpy.gz"), "rb") as fh:
            rc = qpy.load(fh)[0]
        n_chunks = CHUNKS + (EXTRA_CHUNKS if args.extend else 0)
        for r in ([args.ratio] if args.ratio is not None else E4_RATIOS):
            for ch in range(n_chunks):
                path = cell_path(f"E4_{rid}_{cid}", r, m["schedule"], ch)
                if os.path.exists(path):
                    print(f"{rel(path)} exists, skipped")
                    continue
                base, _ = fresh_base(rec, fractional=m["fractional"])
                run_cell(rc, base, rec, c["physical_qubits"], r, m["schedule"], chunk_seed(ch),
                         SHOTS_PER_CHUNK, path, {"gate": "S2D_levers", "row": f"E4:{rid}",
                                                 "circuit": cid, "chunk": ch,
                                                 "record_fingerprint": rec["fingerprint"]})
    return 0


# --------------------------------------------------------------------------- top-up (E2)
def stage_aer_topup(args):
    """E2: every cell whose pooled clean reference hits are below MIN_REF_HITS gets
    EXTRA_CHUNKS more chunks (seeds continue the strided sequence)."""
    rows = load_json(p(OUT, "rows.json"))["rows"]
    rec, _ = fresh_record()
    todo = [args.row] if args.row else list(rows)
    for rid in todo:
        rv = rows[rid]
        m = rv["manifest"]
        qc = None
        for r in RATIOS:
            cells = cells_of(rid, m["schedule"], r)
            if len(cells) < CHUNKS:
                print(f"{rid} r={r}: {len(cells)} of {CHUNKS} base chunks, run --stage aer first")
                continue
            d = decode_cell(cells, m["order"])
            if d["reference_hits"] >= MIN_REF_HITS or len(cells) >= CHUNKS + EXTRA_CHUNKS:
                continue
            print(f"{rid} r={r}: {d['reference_hits']} reference hits < {MIN_REF_HITS}: +{EXTRA_CHUNKS} chunks")
            if qc is None:
                qc, _ = load_row_circuit(rid)
            for c in range(len(cells), CHUNKS + EXTRA_CHUNKS):
                base, _ = fresh_base(rec, fractional=m["fractional"])
                run_cell(qc, base, rec, rv["compile"]["active"], r, m["schedule"], chunk_seed(c),
                         SHOTS_PER_CHUNK, cell_path(rid, r, m["schedule"], c),
                         {"gate": "S2D_levers", "row": rid, "chunk": int(c), "circuit": m["qpy"],
                          "record_fingerprint": m["record_fingerprint"], "extra_chunk": True})
    return 0


# --------------------------------------------------------------------------- verdict logic
def aer_r_crit(f_by_ratio, target):
    """r_crit by log-linear interpolation of ln f against ln r on the grid ("interpolated").

    `f_by_ratio` = {r: f}.  None with a status when f(r = 1) < target (no r <= 1 reaches it)
    or when even the smallest r of the grid meets it (the crossing is below the grid)."""
    pts = sorted((float(r), float(f)) for r, f in f_by_ratio.items() if f is not None)
    if not pts:
        return {"value": None, "status": "no data"}
    if pts[-1][1] < target:
        return {"value": None, "status": f"none: f(r = {pts[-1][0]:g}) = {pts[-1][1]:.4g} < {target}"}
    if pts[0][1] >= target:
        return {"value": None, "status": f"below the grid: f(r = {pts[0][0]:g}) = {pts[0][1]:.4g} >= {target}"}
    for (r0, f0), (r1, f1) in zip(pts, pts[1:]):
        if f0 < target <= f1:
            if f0 <= 0.0:
                return {"value": r1, "status": "interpolated (upper grid point: f = 0 below it)"}
            x0, x1, y0, y1 = math.log(r0), math.log(r1), math.log(f0), math.log(f1)
            x = x0 + (math.log(target) - y0) * (x1 - x0) / (y1 - y0)
            return {"value": math.exp(x), "status": "interpolated"}
    return {"value": None, "status": "non-monotone grid"}


def recommendation_context():
    """The numbers the recommendation quotes, read from committed JSON (never typed)."""
    t = load_json(p("validation", "H0_model.json"))["data"]["t2_override_table"]
    ratios = [x["T2_used_s"] / x["T2_record_echo_s"] for x in t]
    _tab, fb = fez_ratio_table()
    ion = load_json(p("data", "ionq_2x3_feasibility_20261001.json"))["results"]
    i2 = {k: v for k, v in ion.items() if k.startswith("2x2")}
    go = [v["gate_only"]["f_gates"] for v in i2.values()]
    aria = [v["gate_only"]["f_with_idle_estimate"] for k, v in i2.items() if "aria" in k
            and v["gate_only"].get("f_with_idle_estimate") is not None]
    forte = [v for k, v in i2.items() if "forte" in k]
    return {"fez_ratio_min": min(ratios), "fez_ratio_max": max(ratios),
            "fez_ratio_median": float(np.median(ratios)), "fez_fallback": fb,
            "ionq_gate_only": [min(go), max(go)], "aria_idle": [min(aria), max(aria)] if aria else None,
            "forte_idle_computable": any(v["gate_only"].get("f_with_idle_estimate") is not None for v in forte)}


def build_verdict(summary, signed_rows=("L0_asis_asap", "L0_asis_alap", "L1_seed", "L1_seed_alap"),
                  ctx=None):
    """G2 from a row summary {row: {T_s, T_s_L0, aer: {ratio: f}, aer_68, pta_r_crit,
    order_is_default, executor_addition}} -- a pure function, tested on a synthetic table."""
    main = {k: v for k, v in summary.items() if not v.get("executor_addition")}
    have = {k: v for k, v in main.items() if v["aer"].get("1.0") is not None}
    best = max(have, key=lambda k: (have[k]["aer"]["1.0"], -have[k]["T_s"]))
    bv = summary[best]
    T0 = bv["T_s_L0"]
    ratios = {k: v["T_s"] / T0 for k, v in summary.items()}
    f_echo = bv["aer"].get("1.0")
    f_tr = bv["aer"].get("0.174")
    signed = {k: v for k, v in summary.items() if k in signed_rows and v["aer"].get("1.0") is not None}
    best_signed = (max(signed, key=lambda k: (signed[k]["aer"]["1.0"], -signed[k]["T_s"]))
                   if signed else None)
    v = {
        "best_row": best,
        "best_row_rule": "the row with the largest Aer f_clean (mixture) at the echo end (r = 1)",
        "duration_ratio_best": ratios[best],
        "duration_ratio_min_over_rows": min(ratios.values()),
        "duration_halved_reachable": min(ratios.values()) <= 0.5,
        "f_aer_echo_best": f_echo,
        "f_aer_transfer_0.174_best": f_tr,
        "f_aer_echo_best_68": bv.get("aer_68", {}).get("1.0"),
        "f_aer_transfer_0.174_best_68": bv.get("aer_68", {}).get("0.174"),
        "meets_0.1_at_echo": f_echo is not None and f_echo >= 0.1,
        "meets_0.05_at_echo": f_echo is not None and f_echo >= 0.05,
        "meets_0.1_at_transfer_0.174": f_tr is not None and f_tr >= 0.1,
        "meets_0.05_at_transfer_0.174": f_tr is not None and f_tr >= 0.05,
        "r_crit_0.1": {"pta": bv["pta_r_crit"].get("0.1"),
                       "aer_interpolated": aer_r_crit(bv["aer"], 0.1)},
        "r_crit_0.05": {"pta": bv["pta_r_crit"].get("0.05"),
                        "aer_interpolated": aer_r_crit(bv["aer"], 0.05)},
        "family_changes": not bv["order_is_default"],
        "best_row_in_the_signed_family": best_signed,
        "f_aer_echo_signed_family": None if best_signed is None else summary[best_signed]["aer"]["1.0"],
        "f_aer_transfer_0.174_signed_family": (None if best_signed is None
                                               else summary[best_signed]["aer"].get("0.174")),
        "r_crit_0.1_signed_family": (None if best_signed is None else
                                     {"pta": summary[best_signed]["pta_r_crit"].get("0.1"),
                                      "aer_interpolated": aer_r_crit(summary[best_signed]["aer"], 0.1)}),
    }
    v["recommendation"] = recommendation_text(v, summary, ctx)
    return v


def _fmt(x, spec="{:.3f}"):
    return "n/a" if x is None else spec.format(x)


def recommendation_text(v, summary, ctx=None):
    b = v["best_row"]
    bv = summary[b]
    rc = v["r_crit_0.1"]
    rca = rc["aer_interpolated"]
    txt = (f"Recommended row: **{b}** ({bv.get('description', '')}), scheduled "
           f"{bv.get('schedule', 'ALAP').upper()} with explicit delays in the submitted circuit.  "
           f"Its scheduled duration is {v['duration_ratio_best']:.3f}x the as-is canary's on the "
           f"fresh record (halving reached by any row: {v['duration_halved_reachable']}).  "
           f"Aer predicts f_clean {_fmt(v['f_aer_echo_best'])} at the record's echo T2 and "
           f"{_fmt(v['f_aer_transfer_0.174_best'])} at the transferred r = 0.174; f >= 0.1 is met at "
           f"the echo end: {v['meets_0.1_at_echo']}, at r = 0.174: {v['meets_0.1_at_transfer_0.174']}.  "
           f"The break-even ratio T2*/T2_echo above which f >= 0.1 is r_crit = "
           f"{_fmt(rca['value'])} (Aer, {rca['status']}) and {_fmt(rc['pta'])} (PTA bound).  ")
    if v["family_changes"]:
        txt += (f"This row uses the term order {bv.get('order')}, a NEW coarse-step operator: it is "
                f"verified here (C4, C8) but adopting it is the owner's signature (amendment), not this "
                f"gate's.  Within the signed (default-order) family the best row is "
                f"{v['best_row_in_the_signed_family']} with Aer f_clean "
                f"{_fmt(v['f_aer_echo_signed_family'])} at the echo end and "
                f"{_fmt(v['f_aer_transfer_0.174_signed_family'])} at r = 0.174.  ")
    else:
        txt += "The family does not change (default term order).  "
    txt += ("The pilot's `ramw` pub on the selected patch (about 1 s of QPU, prompts/21) measures "
            "the in-circuit T2* and is read against r_crit.  ")
    if not v["meets_0.1_at_transfer_0.174"]:
        c = ctx or {}
        fez = ("" if not c else
               f" (the fez patch-1 measurements span {c['fez_ratio_min']:.3f}-{c['fez_ratio_max']:.3f}, "
               f"median {c['fez_ratio_median']:.3f}, fallback {c['fez_fallback']:.3f})")
        ion = ("" if not c else
               f" (all-to-all, gate-only f {c['ionq_gate_only'][0]:.3f}-{c['ionq_gate_only'][1]:.3f} at 2x2)")
        aria = ("" if not c or not c.get("aria_idle") else
                f": the serial-idle estimate puts Aria at {c['aria_idle'][0]:.4f}-{c['aria_idle'][1]:.4f}"
                + ("" if c.get("forte_idle_computable") else
                   " and Forte is not computable without published gate times"))
        txt += ("Plainly: f >= 0.1 for the 2x2 step on IBM is CONDITIONAL on a T2*/T2_echo ratio above "
                f"r_crit on that patch{fez}; at the transferred ratio 0.174 it is not met.  The "
                f"alternative is IonQ{ion}, with its own idle caveat{aria} -- the vendor specification "
                "of amendment 01 item 4 decides.")
    return txt


# --------------------------------------------------------------------------- assemble (G)
def c1_patch_selection():
    import h0_patch_select as ps
    out = {}
    king = committed_kingston()
    r = ps.search(PREP, king, CANARY, top=5, family=False)
    w = survey_winner()
    u = r.get("incumbent_unscorable") or {}
    out["kingston"] = {
        "incumbent_is_none": r["incumbent"] is None, "reason": u.get("reason"),
        "reason_names_146_and_T1_s": bool(u.get("reason")) and "146" in u["reason"] and "T1_s" in u["reason"],
        "best_physical_qubits": r["best"]["physical_qubits"], "best_f_dd_off": r["best"]["f_dd_off"],
        "survey_physical_qubits": w["physical_qubits"], "survey_f": w["f_pta_clean"],
        "f_delta": abs(r["best"]["f_dd_off"] - w["f_pta_clean"]),
        "ok": (r["incumbent"] is None and bool(u.get("reason")) and "146" in u["reason"]
               and "T1_s" in u["reason"] and r["best"]["physical_qubits"] == w["physical_qubits"]
               and abs(r["best"]["f_dd_off"] - w["f_pta_clean"]) <= 1e-12)}
    fez = load_json(FEZ_RECORD)
    rf = ps.search(PREP, fez, CANARY, top=20, family=False)
    saved = load_json(p("data", "H0_patch_select.json"))
    src = next(s for s in saved["sources"]
               if s["source"]["path"].endswith("H0_ibm_fez/calibration_20260922T1400Z.json"))["result"]
    d_inc = abs(rf["incumbent"]["f_dd_off"] - src["incumbent"]["f_dd_off"])
    d_gain = abs(rf["gain"]["f_dd_off_best_over_incumbent"] - src["gain"]["f_dd_off_best_over_incumbent"])
    out["fez"] = {"best_physical_qubits": rf["best"]["physical_qubits"],
                  "committed_best": src["best"]["physical_qubits"],
                  "incumbent_f_delta": d_inc, "gain_delta": d_gain,
                  "ok": rf["best"]["physical_qubits"] == src["best"]["physical_qubits"]
                  and d_inc <= 1e-12 and d_gain <= 1e-12}
    return out


def c3_anchor():
    """C3(i): the frozen canary on the survey mapping, scheduled on the COMMITTED record."""
    import h0_idle_model as im
    king = committed_kingston()
    w = survey_winner()
    rc = relabelled(canary_circuit(), {int(k): int(v) for k, v in w["mapping"].items()})
    sch = im.schedule(rc, king)
    _pq, tot = im.budgets(sch, king)
    with np.errstate(divide="ignore", invalid="ignore"):
        fg = im.f_on_record(rc, king)[0]
    f = fg * math.exp(-tot["S_T1"] - tot["S_T2"])
    got = {"T_total_s": sch["T_total_s"], "S_T1": tot["S_T1"], "S_T2": tot["S_T2"], "f": f}
    rel_dev = {k: abs(got[k] - C3_ANCHOR[k]) / abs(C3_ANCHOR[k]) for k in C3_ANCHOR}
    return {"computed": got, "expected": C3_ANCHOR, "relative_deviation": rel_dev,
            "ok": all(x <= ANCHOR_REL for x in rel_dev.values())}


def c3_scan_anchors(scan):
    out = {}
    for name, want in (("default_seed2", P5_DEFAULT), ("shortest_seed2", P5_SHORTEST)):
        r = next((x for x in scan["rows"] if x["order"] == want["order"] and x["seed"] == want["seed"]), None)
        ok = (r is not None and r["n_cz"] == want["n_cz"] and r["n_active"] == want["active"]
              and round(r["T_s"] * 1e6, 2) == want["T_us"])
        out[name] = {"expected": want, "found": None if r is None else
                     {"n_cz": r["n_cz"], "T_us": r["T_s"] * 1e6, "active": r["n_active"]}, "ok": ok}
    return out


def c3_p7():
    out = {}
    for m in ("asap", "alap"):
        path = os.path.join(aer_dir(), f"P7_committed_{m}_seed{SEED_BASE}.json")
        if not os.path.exists(path):
            out[m] = {"ok": False, "reason": "cell not run"}
            continue
        c = load_json(path)
        d = decode_cell([c], list(DEFAULT_ORDER))
        want = P7_CELLS[m]
        ident = d["accepted"] == want["accepted"] and d["reference_hits"] == want["reference_hits"]
        within = abs(d["f_clean_reference"] - want["f_clean"]) / want["f_clean"] <= P7_TOL
        out[m] = {"accepted": d["accepted"], "reference_hits": d["reference_hits"],
                  "f_clean_reference": d["f_clean_reference"], "f_clean_mixture": d["f_clean_mixture"],
                  "expected": want, "identical_counts": ident, "ok": ident or within,
                  "versions": c.get("versions"), "file": rel(path)}
    return out


def aer_table(rows):
    """Every row x ratio cell, pooled over its chunks and read with both statistics."""
    tab = {}
    for rid, rv in rows.items():
        m = rv["manifest"]
        tab[rid] = {}
        for r in RATIOS:
            cells = cells_of(rid, m["schedule"], r)
            if not cells:
                tab[rid][str(r)] = None
                continue
            d = decode_cell(cells, m["order"])
            seeds = [c["seed_simulator"] for c in cells]
            d["strided_seeds"] = seeds == [chunk_seed(i) for i in range(len(cells))]
            d["files"] = [rel(cell_path(rid, r, m["schedule"], i)) for i in range(len(cells))]
            d["seconds"] = [c.get("seconds") for c in cells]
            tab[rid][str(r)] = d
    return tab


def e4_aer_table(rid):
    e4p = p(OUT, f"e4_{rid}.json")
    if not os.path.exists(e4p):
        return None
    e4 = load_json(e4p)
    m = load_json(p(OUT, "rows.json"))["rows"][rid]["manifest"]
    fam = {c["id"]: c for c in family_members()}
    out = {}
    for cid in E4_AER:
        c = fam[cid]
        out[cid] = {}
        for r in E4_RATIOS:
            cells = cells_of(f"E4_{rid}_{cid}", m["schedule"], r)
            if not cells:
                out[cid][str(r)] = None
                continue
            d = decode_cell(cells, m["order"], twoB=c["twoB"], ref=c["reference"], theta=c["theta"])
            d["strided_seeds"] = [x["seed_simulator"] for x in cells] == [chunk_seed(i) for i in range(len(cells))]
            if len(cells) > CHUNKS:
                # the first attempt (the E4 prescription, 4000 shots), kept next to the extension
                f = decode_cell(cells[:CHUNKS], m["order"], twoB=c["twoB"], ref=c["reference"], theta=c["theta"])
                d["first_attempt_4000_shots"] = {k: f[k] for k in (
                    "shots", "accepted", "reference_hits", "f_clean_reference", "f_clean_mixture",
                    "f_clean_reference_68", "f_clean_mixture_68", "c6_relative_deviation")}
            out[cid][str(r)] = d
    return {"pta": e4, "aer": out}


def run_checks(skip):
    if skip:
        return {"skipped": True, "ok": False}
    t0 = time.time()
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT,
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    c = subprocess.run([sys.executable, os.path.join("scripts", "check_package.py")], cwd=ROOT,
                       capture_output=True, text=True)
    return {"pytest_returncode": r.returncode, "pytest_summary": tail,
            "check_package_returncode": c.returncode,
            "check_package_tail": "\n".join(c.stdout.strip().splitlines()[-3:]),
            "seconds": time.time() - t0, "ok": r.returncode == 0 and c.returncode == 0}


DESCRIPTIONS = {
    "L0_asis_asap": "the frozen canary relabelled onto its best embedding, ASAP",
    "L0_asis_alap": "the frozen canary relabelled onto its best embedding, ALAP",
    "L1_seed": "default term order, best transpiler seed, ASAP",
    "L2_order": "best (term order, seed), ASAP",
    "L3_rx": "L2's circuit with the live fractional rx / rzz gates, ASAP",
    "L4_all": "the best of L1-L3, ALAP",
    "L1_seed_alap": "default order, best seed, ALAP (executor addition: the signed family's best)",
}


def stage_assemble(args):
    from skqd.report import GateResult
    t0 = time.time()
    R = GateResult("S2D_levers", "2x2 duration levers on ibm_kingston: compile/schedule levers "
                                 "measured, f predicted at both T2 ends, r_crit (measurement gate)")
    live = live_info()
    scan = load_json(p(OUT, "scan.json"))
    select = load_json(p(OUT, "select.json"))
    frac = load_json(p(OUT, "fractional.json"))
    rowsj = load_json(p(OUT, "rows.json"))
    fam = load_json(p(OUT, "family.json"))
    rows = rowsj["rows"]
    rec, _ = fresh_record()

    # C1
    c1 = c1_patch_selection()
    R.add("C1 patch selection: kingston committed record completes with incumbent None (146, T1_s) and the survey winner to 1e-12; fez result identical to data/H0_patch_select.json",
          f"kingston f delta {c1['kingston']['f_delta']:.1e}, fez gain delta {c1['fez']['gain_delta']:.1e}",
          "both ok", c1["kingston"]["ok"] and c1["fez"]["ok"])
    # C2
    fr = live["fractional"]
    c2_ok = (live["record"]["missing_errors"] == [] and bool(live["record"]["fingerprint"])
             and live["diff_vs_committed"] is not None
             and (fr.get("plain_block_equal_to_fresh_record") or fr.get("plain_block_diff_vs_fresh") is not None
                  or fr.get("status") == "not measured"))
    R.add("C2 live reads: fresh record missing_errors == [], fingerprint + diff recorded; fractional read recorded with the plain-block fingerprint check",
          f"missing {len(live['record']['missing_errors'])}, {live['diff_vs_committed']['n_leaves']} leaves moved, fractional present {fr.get('present')}, plain blocks equal {fr.get('plain_block_equal_to_fresh_record')}",
          "missing_errors == [] and both reads recorded", c2_ok)
    # C3
    a3 = c3_anchor()
    s3 = c3_scan_anchors(scan)
    p7 = c3_p7()
    c3_ok = a3["ok"] and all(v["ok"] for v in s3.values()) and all(v["ok"] for v in p7.values())
    R.add("C3 anchors: (i) survey-mapping canary on the committed record to 1e-9; (ii) P2/P5 scan rows; (iii) the two P7 Aer cells",
          f"(i) max rel {max(a3['relative_deviation'].values()):.1e}; (ii) {all(v['ok'] for v in s3.values())}; "
          f"(iii) ASAP {p7['asap'].get('accepted')}/{p7['asap'].get('reference_hits')}, ALAP {p7['alap'].get('accepted')}/{p7['alap'].get('reference_hits')}",
          "(i) <= 1e-9; (ii) exact; (iii) identical counts or f_clean within 25 %", c3_ok)
    # C4
    c4_rows = {rid: rv["exactness"] for rid, rv in rows.items()}
    c4_fam = {t: {"max_abs_delta": f["max_abs_delta"], "max_leakage": f["max_leakage"],
                  "all_ok": f["all_exact_ok"]} for t, f in fam["families"].items()}
    worst_d = max([v["max_abs_delta"] for v in c4_rows.values()] + [v["max_abs_delta"] for v in c4_fam.values()])
    worst_l = max([v["leakage"] for v in c4_rows.values()] + [v["max_leakage"] for v in c4_fam.values()])
    c4_ok = all(v["ok"] for v in c4_rows.values()) and all(v["all_ok"] for v in c4_fam.values())
    R.add("C4 exactness of every row and family circuit (max |delta| on the codewords in the row's term order; leakage; measurement map)",
          f"max |delta| {worst_d:.2e}, leakage {worst_l:.2e}",
          f"< {AMP_TOL:g} and < {LEAK_TOL:g}", c4_ok)
    # C5
    if frac.get("measured"):
        ff = frac["fractional"]
        l3 = rows.get("L3_rx")
        frec = fractional_record(rec, fractional_json())
        leaves_ok = True
        if l3 is not None:
            act = l3["compile"]["active"]
            for q in act:
                if any(frec["qubits"][str(q)].get(k) is None for k in FRACTIONAL_QUBIT_FIELDS):
                    leaves_ok = False
            for a, b in l3["manifest"]["pattern_edges"]:
                e = frec["edges"].get(f"{a}-{b}") or frec["edges"].get(f"{b}-{a}")
                if e is None or any(e.get(k) is None for k in FRACTIONAL_EDGE_FIELDS):
                    leaves_ok = False
        fam_frac_ok = all(f["all_rzz_angles_ok"] for f in fam["families"].values() if f["fractional"])
        c5_ok = (ff["rzz_angles_in_0_pi_over_2"] and ff["exactness"]["ok"] and leaves_ok
                 and ff["runtime_rzz_validation"].startswith("valid") and fam_frac_ok)
        c5_val = (f"{ff['n_rzz']} rzz all in [0, pi/2]: {ff['rzz_angles_in_0_pi_over_2']}; runtime check "
                  f"{ff['runtime_rzz_validation'][:5]}; C4 {ff['exactness']['max_abs_delta']:.1e}; leaves {leaves_ok}")
    else:
        c5_ok, c5_val = True, "fractional rows not measured (not a failure)"
    R.add("C5 fractional rows: rzz angles in [0, pi/2], the fractional circuit passes C4, rx/rzz leaves non-None on the row's qubits and edges",
          c5_val, "all hold (or not measured)", c5_ok)
    # C6
    tab = aer_table(rows)
    c6 = []
    for rid, cells in tab.items():
        for r, d in cells.items():
            if d is None:
                continue
            if d["reference_hits"] >= MIN_REF_HITS:
                c6.append({"row": rid, "ratio": r, "dev": d["c6_relative_deviation"],
                           "strided": d["strided_seeds"], "ok": d["c6_relative_deviation"] <= C6_TOL and d["strided_seeds"]})
    e4 = None
    rec_row = None
    n_cells = sum(1 for cells in tab.values() for d in cells.values() if d is not None)
    n_expected = len(tab) * len(RATIOS)
    # the verdict summary
    summary = {}
    for rid, rv in rows.items():
        m = rv["manifest"]
        summary[rid] = {
            "T_s": rv["compile"]["T_s"], "T_s_L0": rows["L0_asis_asap"]["compile"]["T_s"],
            "aer": {r: (None if d is None else d["f_clean_mixture"]) for r, d in tab[rid].items()},
            "aer_68": {r: (None if d is None else d["f_clean_mixture_68"]) for r, d in tab[rid].items()},
            "pta_r_crit": rv["r_crit_pta"], "order_is_default": m["order"] == list(DEFAULT_ORDER),
            "executor_addition": bool(m.get("executor_addition")), "schedule": m["schedule"],
            "order": m["order"], "description": DESCRIPTIONS.get(rid, "")}
    verdict = build_verdict(summary, ctx=recommendation_context())
    rec_row = verdict["best_row"]
    e4 = e4_aer_table(rec_row)
    if e4 is not None:
        for cid, cells in e4["aer"].items():
            for r, d in cells.items():
                if d is not None and d["reference_hits"] >= MIN_REF_HITS:
                    c6.append({"row": f"E4:{cid}", "ratio": r, "dev": d["c6_relative_deviation"],
                               "strided": d["strided_seeds"],
                               "ok": d["c6_relative_deviation"] <= C6_TOL and d["strided_seeds"]})
    c6_first = []
    if e4 is not None:
        for cid, cells in e4["aer"].items():
            for r, d in cells.items():
                fa = (d or {}).get("first_attempt_4000_shots")
                if fa is not None and fa["reference_hits"] >= MIN_REF_HITS:
                    c6_first.append({"row": f"E4:{cid}", "ratio": r, "dev": fa["c6_relative_deviation"],
                                     "reference_hits": fa["reference_hits"],
                                     "f_clean_reference": fa["f_clean_reference"],
                                     "f_clean_reference_68": fa["f_clean_reference_68"],
                                     "f_clean_mixture": fa["f_clean_mixture"],
                                     "f_clean_mixture_68": fa["f_clean_mixture_68"],
                                     "ok": fa["c6_relative_deviation"] <= C6_TOL})
    c6_ok = all(x["ok"] for x in c6) and n_cells == n_expected
    R.add("C6 estimator consistency on every Aer cell with >= 20 reference hits (mixture vs reference f_clean), chunks strided",
          f"{len(c6)} cells checked, worst {max((x['dev'] for x in c6), default=0):.3f}; {n_cells}/{n_expected} row cells present",
          f"<= {C6_TOL} and every row x ratio cell present", c6_ok)
    # C7
    c7 = {rid: rv["c7"] for rid, rv in rows.items()}
    c7_ok = all(v["duration_agreement_s"] <= 1e-12 for v in c7.values()) and \
        all(v.get("asap_budget_match", 0.0) <= 1e-9 for rid, v in c7.items() if rows[rid]["manifest"]["schedule"] == "asap") and \
        all("budget_delays_leading_excluded" in v and "budget_delays_leading_included" in v for v in c7.values())
    R.add("C7 scheduling: no non-delay op moved; scheduled duration = h0_qpu_time.circuit_duration_s to 1e-12; ASAP delay-window budget = idle_budget to 1e-9; ALAP budgets recorded both ways",
          f"worst duration {max(v['duration_agreement_s'] for v in c7.values()):.1e} s, worst ASAP budget {max(v.get('asap_budget_match', 0.0) for v in c7.values()):.1e}",
          "<= 1e-12 s and <= 1e-9", c7_ok)
    # C8
    dr = fam["reach_default_order"]
    c8 = {}
    for t, f in fam["families"].items():
        c8[t] = {"reach": {s: v["reach"] for s, v in f["reach"].items()},
                 "default_reach": {s: v["reach"] for s, v in dr.items()},
                 "reach_ge_default": all(f["reach"][s]["reach"] >= dr[s]["reach"] for s in dr),
                 "max_abs_delta": f["max_abs_delta"],
                 "p_ref_k1_min": min(f["p_ref_k1"].values()),
                 "weakens_C3prime": min(f["p_ref_k1"].values()) < 0.5}
    c8_ok = all(v["reach_ge_default"] for v in c8.values()) and all(f["all_exact_ok"] for f in fam["families"].values())
    R.add("C8 family: reordered family's reach of the exact 99.9 % support >= the default family's, per sector; C4 over all its circuits; p_ref reported",
          "; ".join(f"{t}: {v['reach']}" for t, v in c8.items()), ">= default reach", c8_ok)
    # C9
    checks = run_checks(args.skip_tests)
    R.add("C9 pytest -q tests and scripts/check_package.py", f"pytest: {checks.get('pytest_summary')}; check_package rc {checks.get('check_package_returncode')}",
          "all pass", checks["ok"])

    # the deciding table, budgets and the information lines
    info_lines = information_lines(rec, rows, fam, verdict)
    R.data = {
        "what_pass_means": ("measured, verified, consistent -- never affordable; there is no criterion "
                            "on any f, duration ratio or r_crit: those are the verdict fields"),
        "qpu_seconds": 0,
        "versions": versions(),
        "live": live, "C1": c1, "C3": {"anchor_i": a3, "scan_ii": s3, "p7_iii": p7},
        "scan_summary": {k: scan[k] for k in ("n_rows", "n_orders", "seeds", "uniform_record", "record_medians", "compute_seconds")},
        "select_summary": {"n_candidates": select["n_candidates"], "proxy_note": select["proxy_note"],
                           "error_statistics": select["error_statistics"],
                           "candidates": [{"id": c["id"], "why": c["why"], "order": c["order"], "seed": c["seed"],
                                           "n_embeddings": c["n_embeddings"], "n_scored": c["n_scored"],
                                           "best_physical_qubits": c["best"]["physical_qubits"],
                                           "f_dd_off": c["best"]["f_dd_off"], "T_s": c["best"]["T_s"],
                                           "n_cz": c["best"]["n_cz"], "n_active": c["pattern"]["n_nodes"],
                                           "on_survey_patch_f": (c["on_survey_patch"] or {}).get("f_dd_off")}
                                          for c in select["candidates"]]},
        "choice": rowsj["choice"],
        "fractional": {k: v for k, v in frac.items() if k not in ("fractional", "plain_control")} | (
            {"fractional_summary": {k: frac["fractional"][k] for k in ("n_cz", "n_rzz", "n_1q", "T_s", "f_gates", "f_including_1q_errors", "rzz_angle_histogram_pi", "rzz_angles_in_0_pi_over_2", "runtime_rzz_validation", "without_the_post_fold")},
             "plain_control_summary": {k: frac["plain_control"][k] for k in ("n_cz", "n_1q", "T_s", "f_gates", "f_including_1q_errors")},
             "selected_f_fractional": frac["fractional"]["selected"]["best"]["f_dd_off"],
             "selected_f_plain": frac["plain_control"]["selected"]["best"]["f_dd_off"]} if frac.get("measured") else {}),
        "rows": {rid: {k: v for k, v in rv.items()} for rid, rv in rows.items()},
        "dd_ceiling": rowsj["dd_ceiling"],
        "aer": tab, "C6": c6, "C6_first_attempt_E4_4000_shots": c6_first, "C7": c7, "C8": c8, "C9": checks,
        "family": {t: {k: v for k, v in f.items() if k != "circuits"} for t, f in fam["families"].items()},
        "family_reach_default_order": dr, "family_p_ref_default_order_k1": fam["p_ref_default_order_k1"],
        "e4": e4, "information": info_lines, "verdict": verdict,
        "notes": build_notes(select, fam) + ([c6_note(c6_first, e4)] if e4 is not None and c6_note(c6_first, e4) else []),
    }
    R.runtime_s = time.time() - t0
    path = R.save()
    with open(path) as fh:
        saved = json.load(fh)
    from skqd.report import write_report
    write_report("S2D_levers_2x2_kingston.md", report_text(saved, R))
    print(R.criteria_table())
    print(f"status {saved['status']}; best row {verdict['best_row']}, duration ratio "
          f"{verdict['duration_ratio_best']:.3f}, f_aer echo {_fmt(verdict['f_aer_echo_best'], '{:.4f}')}, "
          f"transfer {_fmt(verdict['f_aer_transfer_0.174_best'], '{:.4f}')}, r_crit "
          f"{verdict['r_crit_0.1']}")
    return 0 if saved["status"] == "PASS" else 1


PROMPT_B1_PREF = 0.8894      # the value prompts/23 F1 quotes for the default family's B = 1 p_ref


def build_notes(select, fam):
    """The executor's notes, every number read from the stage outputs."""
    es = select["error_statistics"]
    b1 = sorted({c["reference"] for c in family_members() if c["twoB"] == 2})
    pb1 = [v for k, v in fam["p_ref_default_order_k1"].items() if k.startswith("B1")]
    return [
        f"f_proxy of the scan uses the record's MEAN cz / readout error (prompts/23 C1).  {es['n_cz_at_1']} "
        f"edges of the fresh kingston record carry IBM's uncalibrated marker 1.0, so the mean cz error is "
        f"{es['cz_error_mean']:.4f} against a median of {es['cz_error_median']:.5f} and the proxy ranks by CZ "
        f"count alone; the executor admitted the top {K_SELECT} by the MEDIAN-error proxy into the selection "
        f"as well (the selection objective is unchanged).  The best rows came from that set.",
        f"The prompt names B1_ref00_k1 / B1_ref00_k4 for E4; the frozen set's B = 1 references are "
        f"{', '.join(f'{x:02d}' for x in b1)} (skqd.krylov.references), so the first, B1_ref{b1[0]:02d}, is used.",
        f"The prompt quotes the default family's B = 1 p_ref as {PROMPT_B1_PREF}; the computed value is "
        f"{min(pb1):.6f} (the committed validation/H0P_ibm_fez.json carries the same best_r1_p).",
        "The fractional transpilation needs FoldRzzAngle once more AFTER the level-3 optimization loop: the "
        "plugin folds right after translation, and the optimization loop then re-emits rzz(-pi/2), which the "
        "runtime's validate_rzz_pubs rejects.  The extra fold is part of the same staged pass manager.",
        "L1_seed_alap is an executor addition: the best the SIGNED (default-order) family can do, scheduled "
        "ALAP, so that the owner can read the gain of a family change separately from the rest.",
    ]


def c6_note(c6_first, e4):
    """The C6 history, generated from the first-attempt records (no typed number)."""
    bad = [x for x in c6_first if not x["ok"]]
    if not bad:
        return None
    parts = []
    for x in bad:
        cid = x["row"].split(":", 1)[1]
        pr = e4["aer"][cid][x["ratio"]]["p_reference"]
        parts.append(f"{cid} at r = {x['ratio']} ({x['reference_hits']} reference hits at p_ref {pr:.3f}: "
                     f"reference-string f_clean {x['f_clean_reference']:.4f} [68 %: "
                     f"{x['f_clean_reference_68'][0]:.3f}, {x['f_clean_reference_68'][1]:.3f}] against the "
                     f"mixture's {x['f_clean_mixture']:.4f} [{x['f_clean_mixture_68'][0]:.3f}, "
                     f"{x['f_clean_mixture_68'][1]:.3f}], relative deviation {x['dev']:.3f} > {C6_TOL})")
    return ("C6 first attempt: at the 4000 shots E4 prescribes, " + "; ".join(parts) + " failed C6.  The "
            "escalation re-check found the chunk seeds strided, the chunks' raw samples distinct and the T2 "
            "override on every qubit of the patch at exactly the cell's ratio with no clipping.  The second "
            "attempt -- decided AFTER seeing the failure, and applied to all E4 cells, not only the failing "
            "one -- extends every E4 cell to 8000 shots with the same strided seed sequence (the E2 top-up "
            "mechanism).  The 4000-shot values are kept in data.C6_first_attempt_E4_4000_shots and in "
            "data.e4.aer[*][*].first_attempt_4000_shots.")


def information_lines(rec, rows, fam, verdict):
    """The C22, 2x3 and IonQ lines and the D3' / D3''-H0 budgets, all computed here."""
    from skqd.skqd import poisson_lambda_star  # noqa: F401  (the budgets below import it)
    out = {}
    a0, a2 = garbage_acceptance(0), garbage_acceptance(2)
    M = factory()["M"]
    d0, d2 = len(M.reference(G2, 0).indices), len(M.reference(G2, 2).indices)
    out["C22_saturation"] = {"B=0": {"acceptance": a0, "dim": d0, "N_saturation": 5 * d0 / a0},
                             "B=1": {"acceptance": a2, "dim": d2, "N_saturation": 5 * d2 / a2},
                             "rule": "N a / dim >= 5: the sector fills from accidentally-valid noise alone"}
    s2 = load_json(p("validation", "S2.json"))["data"]["2x3"]
    n_cz_2x3 = int(s2["coarse_step"]["routed"]["cz"])
    med = error_medians(rec)
    out["2x3_on_ibm"] = {"n_cz_routed": n_cz_2x3, "source": "validation/S2.json data.2x3.coarse_step.routed.cz",
                         "cz_error_mean": med["cz_error_mean"], "cz_error_median": med["cz_error_median"],
                         "f_gates_mean": None if n_cz_2x3 is None else (1 - med["cz_error_mean"]) ** n_cz_2x3,
                         "f_gates_median": None if n_cz_2x3 is None else (1 - med["cz_error_median"]) ** n_cz_2x3}
    ion = load_json(p("data", "ionq_2x3_feasibility_20261001.json"))
    out["ionq_2x2"] = {k: v for k, v in ion["results"].items() if k.startswith("2x2")}
    # budgets of the recommended row's family at its f (information)
    try:
        out["budgets"] = family_budgets(verdict["best_row"], rows, rec, verdict)
    except Exception as exc:                      # pragma: no cover - reported, never silent
        out["budgets"] = {"error": str(exc)}
    return out


def family_budgets(rid, rows, rec, verdict):
    import h0_device_survey as ds
    from gate_H0P import load_circuit, load_manifests
    from skqd import idle
    e4p = p(OUT, f"e4_{rid}.json")
    if not os.path.exists(e4p):
        return {"status": "E4 not run for this row"}
    e4 = load_json(e4p)
    T = {c["id"]: c["T_total_s"] for c in e4["circuits"]}
    mans = [{"id": c["id"], "sector": c["sector"], "repetitions": 1, "k": c["k"]} for c in e4["circuits"]]
    _m, cals = load_manifests(PREP)
    cal_entries = []
    for c in cals:
        qc = load_circuit(PREP, c)
        T[c["id"]] = float(idle.schedule_asap(qc, rec)["T_total_s"])
        cal_entries.append({"id": c["id"]})
    m = rows[rid]["manifest"]
    fam = {c["id"]: c for c in family_members()}
    P = {c["id"]: ideal_distribution(m["order"], fam[c["id"]]["twoB"], fam[c["id"]]["reference"],
                                     fam[c["id"]]["theta"])["p_unnormalised"] for c in e4["circuits"]}
    rep = float(rec.get("default_rep_delay_s") or ds.REP_DELAY_DEFAULT)
    out = {"note": ("information: the 28 r = 1 circuits of the row's family at their own durations on the "
                    "fresh record; the r = 2, 3 circuits of the frozen plan are NOT rebuilt in this family, so "
                    "both budgets below exclude them (their D3' shots are 130 / 92 per circuit)"),
           "rep_delay_s": rep}
    for label, f in (("echo_r1", verdict["f_aer_echo_best"]), ("transfer_r0.174", verdict["f_aer_transfer_0.174_best"])):
        if f is None or f <= 0:
            out[label] = {"f": f, "status": "no positive f"}
            continue
        d3 = ds.d3_budget(P, T, mans, cal_entries, f, rep)
        dpp = ds.d3pp_budget(T, mans, cal_entries, f, rep)
        out[label] = {"f": f, "D3prime_N4": d3["N4"], "D3prime_execution_s": d3["execution_s"],
                      "D3prime_total_coarse_shots": d3["total_coarse_shots"],
                      "D3pp_H0_shots_per_k1": dpp["shots_per_k1_circuit"],
                      "D3pp_H0_execution_s": dpp["execution_s"]}
        if m["order"] != list(DEFAULT_ORDER):
            # N4 depends only on the ideal distributions and f: the same f in the default order
            P0 = {c["id"]: ideal_distribution(list(DEFAULT_ORDER), fam[c["id"]]["twoB"], fam[c["id"]]["reference"],
                                              fam[c["id"]]["theta"])["p_unnormalised"] for c in e4["circuits"]}
            d30 = ds.d3_budget(P0, T, mans, cal_entries, f, rep)
            out[label]["D3prime_N4_default_order_same_f"] = d30["N4"]
    if m["order"] != list(DEFAULT_ORDER):
        mins = {}
        for lab_o, o in (("row_order", m["order"]), ("default_order", list(DEFAULT_ORDER))):
            for sec in ("B=0", "B=1"):
                k4 = [c["id"] for c in e4["circuits"] if c["sector"] == sec and c["k"] == 4]
                s_ = np.sum([ideal_distribution(o, fam[c]["twoB"], fam[c]["reference"], fam[c]["theta"])
                             ["p_unnormalised"] for c in k4], axis=0)
                mins[f"{lab_o}|{sec}"] = {"min_summed_p_over_k4": float(s_.min()), "sector_position": int(s_.argmin())}
        out["weakest_state_k4"] = mins
    return out


def report_text(saved, R):
    return render_report(saved, R)


def _bars(f):
    if f is None:
        return "n/a"
    return f"{'yes' if f >= 0.1 else 'no'} / {'yes' if f >= 0.05 else 'no'}"


def _iv(x68):
    return "" if not x68 else f" [{x68[0]:.3f}, {x68[1]:.3f}]"


def _rc(x):
    if isinstance(x, dict):
        return _fmt(x.get("value")) if x.get("value") is not None else x.get("status", "n/a")
    return "none (f(r=1) < bar)" if x is None else f"{x:.3f}"


def render_report(saved, R):
    from skqd.report import md_table
    D = saved["data"]
    rows, aer, v = D["rows"], D["aer"], D["verdict"]
    live, fr = D["live"], D["fractional"]
    order_ids = [r for r in ("L0_asis_asap", "L0_asis_alap", "L1_seed", "L2_order", "L3_rx", "L4_all",
                             "L1_seed_alap") if r in rows]
    short = lambda o: "default" if o == list(DEFAULT_ORDER) else "(" + ", ".join(o) + ")"
    # compile table
    ct = []
    for rid in order_ids:
        r = rows[rid]
        c, m = r["compile"], r["manifest"]
        ct.append([rid, short(m["order"]), m["seed"] if m["seed"] is not None else "frozen (7)",
                   m["schedule"].upper(), f"{c['n_cz']}" + (f" + {c['n_rzz']} rzz" if c["n_rzz"] else ""),
                   c["n_1q"], c["depth"], c["twoq_layers"], c["n_active"], f"{c['T_s'] * 1e6:.2f}",
                   f"{c['busy_max_s'] * 1e6:.2f}", f"{c['idle_s'] * 1e6:.1f}",
                   f"{r['duration_ratio_to_L0']:.3f}", str(m["physical_qubits"])])
    # deciding table
    dt_rows = []
    for rid in order_ids:
        r = rows[rid]
        a1, a2 = aer[rid].get("1.0"), aer[rid].get("0.174")
        f1 = None if a1 is None else a1["f_clean_mixture"]
        f2 = None if a2 is None else a2["f_clean_mixture"]
        rc_aer = aer_r_crit({k: (None if d is None else d["f_clean_mixture"]) for k, d in aer[rid].items()}, 0.1)
        dt_rows.append([rid, DESCRIPTIONS.get(rid, ""), f"{r['compile']['T_s'] * 1e6:.2f}",
                        f"{r['duration_ratio_to_L0']:.3f}",
                        f"{r['pta']['1.0']['S_T1']:.3f}", f"{r['pta']['1.0']['S_T2']:.3f}",
                        f"{r['pta']['0.174']['S_T2']:.3f}",
                        (_fmt(f1, "{:.4f}") + _iv(None if a1 is None else a1["f_clean_mixture_68"])),
                        (_fmt(f2, "{:.4f}") + _iv(None if a2 is None else a2["f_clean_mixture_68"])),
                        f"{r['pta']['1.0']['f']:.4f}", f"{r['pta']['0.174']['f']:.2e}",
                        _bars(f1), _bars(f2),
                        f"{_rc(rc_aer)} / {_rc(r['r_crit_pta']['0.1'])}"])
    # full grid
    grid = []
    for rid in order_ids:
        r = rows[rid]
        for x in RATIOS:
            d = aer[rid].get(str(x))
            grid.append([rid, x, f"{r['pta'][str(x)]['S_T2']:.3f}", f"{r['pta'][str(x)]['f']:.3e}",
                         "n/a" if d is None else d["shots"], "n/a" if d is None else d["accepted"],
                         "n/a" if d is None else d["reference_hits"],
                         "n/a" if d is None else f"{d['f_clean_reference']:.4f}",
                         "n/a" if d is None else f"{d['f_clean_mixture']:.4f}{_iv(d['f_clean_mixture_68'])}",
                         "n/a" if d is None else _fmt(d["c6_relative_deviation"])])
    # family
    fam_rows = []
    for t, f in D["family"].items():
        si = f["structure_identical"]
        fam_rows.append([t, f["n_circuits"], si["n_distinct_patterns"], str(si["n_2q_values"]),
                         str(si["depth_values"][:3]) + ("..." if len(si["depth_values"]) > 3 else ""),
                         f"{f['max_abs_delta']:.1e}", f"{f['max_leakage']:.1e}",
                         " / ".join(f"{s} {x['reached']}/{x['support_size']}" for s, x in f["reach"].items()),
                         f"{min(f['p_ref_k1'].values()):.4f}-{max(f['p_ref_k1'].values()):.4f}"])
    dr = D["family_reach_default_order"]
    # select
    sel_rows = [[c["id"], ", ".join(c["why"]), c["n_active"], c["n_cz"], f"{c['T_s'] * 1e6:.2f}",
                 f"{c['f_dd_off']:.4e}", str(c["best_physical_qubits"])]
                for c in D["select_summary"]["candidates"]]
    # e4
    e4 = D.get("e4")
    e4txt = "E4 was not run."
    if e4:
        ps_ = e4["pta"]["pta_summary"]
        e4rows = [[cid, r, d["shots"], d["accepted"], d["reference_hits"], f"{d['f_clean_reference']:.4f}",
                   f"{d['f_clean_mixture']:.4f}{_iv(d['f_clean_mixture_68'])}"]
                  for cid, cells in e4["aer"].items() for r, d in cells.items() if d is not None]
        e4txt = (f"PTA over the {len(e4['pta']['circuits'])} r = 1 circuits of `{v['best_row']}`'s family on "
                 f"its patch ({e4['pta']['schedule'].upper()}): " +
                 "; ".join(f"r = {r}: mean {x['mean']:.4f} (0.1 bar {'met' if x['meets_0.1_mean'] else 'not met'}), "
                           f"worst {x['worst']:.4f} (0.05 bar {'met' if x['meets_0.05_worst'] else 'not met'})"
                           for r, x in ps_.items()) +
                 f".  Placement: {sorted({c['placement'] for c in e4['pta']['circuits']})}.\n\n" +
                 md_table(["circuit", "r", "shots", "accepted", "reference hits", "f_clean (reference)",
                           "f_clean (mixture) [68 %]"], e4rows))
    info = D["information"]
    c22 = info["C22_saturation"]
    x23 = info["2x3_on_ibm"]
    ion = info["ionq_2x2"]
    bud = info.get("budgets", {})
    ionrows = [[k, f"{x['gate_only']['f_gates']:.3f}",
                _fmt(x["gate_only"].get("f_with_idle_estimate"), "{:.4f}"),
                _fmt((x.get("idle") or {}).get("duration_s"), "{:.3f}")] for k, x in ion.items()]
    budtxt = ""
    if bud and "note" in bud:
        budtxt = "\n".join(f"- {lab}: f = {b.get('f'):.4f}: D3' N4 {b.get('D3prime_N4')}, execution "
                           f"{b.get('D3prime_execution_s', float('nan')):.1f} s; D3''-H0 {b.get('D3pp_H0_shots_per_k1')} "
                           f"shots per k = 1 circuit, execution {b.get('D3pp_H0_execution_s', float('nan')):.1f} s"
                           + (f"; **the default-order family at the same f needs D3' N4 "
                              f"{b['D3prime_N4_default_order_same_f']}**" if "D3prime_N4_default_order_same_f" in b else "")
                           for lab, b in bud.items() if isinstance(b, dict) and "D3prime_N4" in b)
        wk = bud.get("weakest_state_k4")
        if wk:
            budtxt += ("\n- Why: rule D3' sizes N4 on the sector state with the least probability summed over the "
                       "k = 4 circuits; " + "; ".join(f"{k}: {x['min_summed_p_over_k4']:.2e} (position "
                                                      f"{x['sector_position']})" for k, x in wk.items()) +
                       ".  A family change therefore also moves the D3' shot cost, not only f.")
        budtxt = f"{bud['note']}.\n\n{budtxt}"
    fsum = fr.get("fractional_summary") or {}
    psum = fr.get("plain_control_summary") or {}
    ceil = D["dd_ceiling"]
    p7 = D["C3"]["p7_iii"]
    vrows = [[k, json.dumps(x) if isinstance(x, (dict, list)) else x] for k, x in v.items() if k != "recommendation"]
    best = v["best_row"]
    brow = rows[best]
    return f"""# Gate S2D_levers -- the 2x2 coarse step on ibm_kingston: duration levers, f at both T2 ends, r_crit

Generated by `scripts/gate_S2D_levers.py --stage assemble` (prompts/23) from `validation/S2D_levers.json`
(status **{saved['status']}**, commit `{saved['environment']['git_commit']}`, {saved['environment']['timestamp']}).
**Every number below is read from that JSON.**  0 QPU seconds; the live IBM reads are target metadata.
Stack: qiskit {D['versions']['qiskit']}, qiskit-aer {D['versions']['qiskit_aer']}, qiskit-ibm-runtime {D['versions']['qiskit_ibm_runtime']}.

## 0. What PASS means

{D['what_pass_means']}.  Criteria C1-C9 check that the levers were measured on the signed chain and that
every circuit is exact; the answer to "can the 2x2 step meet f >= 0.1 on IBM" is the verdict block
(sections 1 and 9), not a criterion.

## 1. The answer

{v['recommendation']}

| verdict field | value |
|---|---|
| best row | `{best}` ({DESCRIPTIONS.get(best, '')}) |
| duration ratio (best / as-is) | {v['duration_ratio_best']:.3f} (min over rows {v['duration_ratio_min_over_rows']:.3f}) |
| `duration_halved_reachable` | **{v['duration_halved_reachable']}** |
| Aer f_clean at the echo end (r = 1) | **{_fmt(v['f_aer_echo_best'], '{:.4f}')}**{_iv(v['f_aer_echo_best_68'])} |
| Aer f_clean at the transferred r = 0.174 | **{_fmt(v['f_aer_transfer_0.174_best'], '{:.4f}')}**{_iv(v['f_aer_transfer_0.174_best_68'])} |
| meets 0.1 / 0.05 at the echo end | {v['meets_0.1_at_echo']} / {v['meets_0.05_at_echo']} |
| meets 0.1 / 0.05 at r = 0.174 | {v['meets_0.1_at_transfer_0.174']} / {v['meets_0.05_at_transfer_0.174']} |
| r_crit(0.1): Aer interpolated / PTA | {_rc(v['r_crit_0.1']['aer_interpolated'])} / {_rc(v['r_crit_0.1']['pta'])} |
| r_crit(0.05): Aer interpolated / PTA | {_rc(v['r_crit_0.05']['aer_interpolated'])} / {_rc(v['r_crit_0.05']['pta'])} |
| family changes | {v['family_changes']} |
| best row in the signed (default-order) family | `{v['best_row_in_the_signed_family']}`: Aer {_fmt(v['f_aer_echo_signed_family'], '{:.4f}')} (r = 1), {_fmt(v['f_aer_transfer_0.174_signed_family'], '{:.4f}')} (r = 0.174), r_crit(0.1) {_rc((v['r_crit_0.1_signed_family'] or {}).get('aer_interpolated'))} / {_rc((v['r_crit_0.1_signed_family'] or {}).get('pta'))} |

## 2. Live reads (B1-B3; metadata only)

- Fresh full-device record `{live['record']['path']}`: stamp {live['record']['stamp']}, fingerprint
  `{live['record']['fingerprint']}`, {live['record']['n_qubits']} qubits / {live['record']['n_edges']} edges,
  `missing_errors` {live['record']['missing_errors']}.
- Against the committed `{live['committed']['path']}` (fingerprint `{live['committed']['fingerprint'][:16]}`):
  **{live['diff_vs_committed']['n_leaves']} leaves moved** over {live['diff_vs_committed']['families']}.
- Qubit 146: committed T1 {live['qubit_146']['committed']['T1_s']}, T2 {live['qubit_146']['committed']['T2_s']};
  fresh T1 {live['qubit_146']['fresh']['T1_s']}, T2 {live['qubit_146']['fresh']['T2_s']}, sx_error
  {live['qubit_146']['fresh']['sx_error']}, measure_error {live['qubit_146']['fresh']['measure_error']} (still uncalibrated;
  recorded, never defaulted).
- `backend_from_record(fresh, FakeKingston(), strict=True)`: {live['backend_from_record_strict']['ok']}.
- Fractional target (`use_fractional_gates=True`, a separate object): present {live['fractional'].get('present')},
  `{live['fractional'].get('path')}`; plain-block fingerprint equal to the fresh record's:
  **{live['fractional'].get('plain_block_equal_to_fresh_record')}**; cz durations {live['fractional'].get('cz_durations_s')} s,
  sx durations {live['fractional'].get('sx_durations_s')} s; rx / rzz leaves without a value: {live['fractional'].get('n_rx_none')} / {live['fractional'].get('n_rzz_none')}.

## 3. Scan, selection and the fractional transpilation

Scan (C1): {D['scan_summary']['n_rows']} transpilations ({D['scan_summary']['n_orders']} term orders x seeds
{D['scan_summary']['seeds']}), uniform record T1 {D['scan_summary']['record_medians']['T1_median_s'] * 1e6:.1f} us,
T2 {D['scan_summary']['record_medians']['T2_median_s'] * 1e6:.1f} us (the fresh record's medians).  P2/P5 anchors:
{json.dumps({k: x['found'] for k, x in D['C3']['scan_ii'].items()})}.

{D['select_summary']['proxy_note']}

Selection (C2): {D['select_summary']['n_candidates']} candidates, each searched exhaustively on the fresh record
(`h0_patch_select`'s objective and tie-break, PTA at the echo end):

{md_table(["candidate", "why", "active", "CZ", "T (us)", "best PTA f", "best patch"], sel_rows)}

Fractional (D, source `{fr.get('source_row')}`): {fsum.get('n_cz')} CZ + {fsum.get('n_rzz')} RZZ and {fsum.get('n_1q')} one-qubit
pulses against {psum.get('n_cz')} CZ / {psum.get('n_1q')} pulses for the plain control; T {_fmt(fsum.get('T_s', 0) * 1e6, '{:.2f}')} us against
{_fmt(psum.get('T_s', 0) * 1e6, '{:.2f}')} us: ratio **{_fmt(fr.get('duration_ratio_fractional_over_plain'), '{:.4f}')}** (threshold
{fr.get('threshold')}; {fr.get('reason')}).  f_gates {_fmt(fsum.get('f_gates'), '{:.4f}')} against {_fmt(psum.get('f_gates'), '{:.4f}')}
(rzz edge errors multiplied); rzz angles (units of pi) {fsum.get('rzz_angle_histogram_pi')}, all in [0, pi/2]:
{fsum.get('rzz_angles_in_0_pi_over_2')}; runtime validation: {fsum.get('runtime_rzz_validation')}.  Without the
post-optimization fold {(fsum.get('without_the_post_fold') or {}).get('n_outside_0_pi_over_2')} of
{(fsum.get('without_the_post_fold') or {}).get('n_rzz')} rzz angles were outside [0, pi/2].

## 4. Compile table (fresh record; T before readout)

{md_table(["row", "order", "seed", "schedule", "2q gates", "1q pulses", "depth", "2q layers", "active", "T (us)",
           "busy max (us)", "idle summed (us)", "T / T(L0)", "patch"], ct)}

## 5. The deciding table

f_clean is Aer on the scheduled circuit read with the clean-yield mixture statistic (68 % profile
interval); PTA is the analytic bound; r = T2 used / T2 echo of the record (the transferred ratios are a planner
construction).  ALAP rows' PTA is read on the explicit delay windows with the leading |0> delays excluded.

{md_table(["row", "lever combination", "T (us)", "T / T(L0)", "S_T1", "S_T2 r=1", "S_T2 r=0.174",
           "Aer f r=1", "Aer f r=0.174", "PTA f r=1", "PTA f r=0.174", "0.1 / 0.05 at r=1",
           "0.1 / 0.05 at r=0.174", "r_crit(0.1) Aer / PTA"], dt_rows)}

The full grid (every r, both statistics; C6 is the relative deviation between them):

{md_table(["row", "r", "S_T2", "PTA f", "shots", "accepted", "reference hits", "f_clean (reference)",
           "f_clean (mixture) [68 %]", "C6 deviation"], grid)}

DD ceiling (`{ceil['row']}`): f = {ceil['f_dd_ceiling_rho0']:.4f} with S_DD {ceil['S_DD']:.3f} over
{ceil['dd_eligible']} eligible windows -- **{ceil['label']}**.

Fez per-qubit ratio table transferred by logical role (information): PTA f on `{best}` =
{brow['pta_fez_table_transferred']['f']:.3e}.

Recommended row on the whole family (E4): {e4txt}

## 6. Family check (F)

{md_table(["family", "circuits", "distinct patterns", "2q gates", "depths", "max |delta|", "max leakage",
           "reach of the exact 99.9 % support", "p_ref (k = 1)"], fam_rows)}

Default family's reach: {' / '.join(f"{s} {x['reached']}/{x['support_size']}" for s, x in dr.items())}.  p_ref of the
default family's k = 1 circuits: {json.dumps({k: round(x, 4) for k, x in D['family_p_ref_default_order_k1'].items()})}.

Budgets at the best row's f (information): {budtxt or 'not computed'}

## 7. C22, 2x3 and IonQ

**C22 (garbage saturation at 2x2).**  With N a / dim >= 5 a sector fills from accidentally-valid noise alone:
B = 0 (a = {c22['B=0']['acceptance']:.5f}, dim {c22['B=0']['dim']}) at N >= {c22['B=0']['N_saturation']:.0f} shots,
B = 1 (a = {c22['B=1']['acceptance']:.5f}, dim {c22['B=1']['dim']}) at N >= {c22['B=1']['N_saturation']:.0f}.  No SKQD
energy at 2x2 is a hardware claim, and configuration recovery stays out of any 2x2 hardware claim.

**2x3 on IBM.**  The gate-only product over the {x23['n_cz_routed']} routed CZ (`{x23['source']}`) on this record:
(1 - {x23['cz_error_mean']:.5f})^{x23['n_cz_routed']} = {x23['f_gates_mean']:.3e} at the record's MEAN CZ error (as the
prompt specifies; the mean carries the uncalibrated 1.0 edges), and (1 - {x23['cz_error_median']:.5f})^{x23['n_cz_routed']} =
{x23['f_gates_median']:.3e} at the median.  Neither leaves a duration lever anything to rescue.

**IonQ for 2x2** (`data/ionq_2x3_feasibility_20261001.json`):

{md_table(["device / rz", "gate-only f", "f with the serial-idle estimate", "duration (s)"], ionrows)}

## 8. Honest limits

- The transferred-T2* rows are a planner construction (uniform ratios {list(RATIOS)}; the fez table by logical
  role, PTA {brow['pta_fez_table_transferred']['f']:.3e} on `{best}`); T2* is qubit-specific and need not scale with the
  echo T2.  Only the `ramw` pub of the pilot on the selected patch (prompts/21, D5') replaces it.
- Aer's dephasing on a delay is exponential; the free-induction decay over short windows may be closer to
  Gaussian -- the pilot's two window lengths exist for that reason.
- The H0_model post-diction (1.05x) used ASAP scheduling against a hardware run whose server-side schedule is
  not on record; explicit delays in the submitted circuits remove that ambiguity for the next run.
- A reordered coarse step is a new family; this gate verifies it (C4 max |delta| over the family
  {max(f['max_abs_delta'] for f in D['family'].values()):.1e}, C8 reach), the owner signs it (amendment), and no freeze happens here.
- 2x3 on IBM: the gate-only product over the {x23['n_cz_routed']} routed CZ at this record's mean CZ error is
  {x23['f_gates_mean']:.3e} (median: {x23['f_gates_median']:.3e}) and leaves no duration lever anything to rescue.  IonQ for
  2x2: gate-only {min(x['gate_only']['f_gates'] for x in ion.values()):.3f}-{max(x['gate_only']['f_gates'] for x in ion.values()):.3f}
  meets the bar; the serial-idle estimate puts Aria at {ion['2x2|ionq_aria|physical_rz']['gate_only']['f_with_idle_estimate']:.4f} /
  {ion['2x2|ionq_aria|virtual_rz']['gate_only']['f_with_idle_estimate']:.4f} (below 0.1, at the 0.05 worst bar) and Forte is
  not computable without gate times -- the vendor spec of amendment 01 item 4 decides.
- At 2x2 the sectors saturate from garbage above about {min(c22['B=0']['N_saturation'], c22['B=1']['N_saturation']):.0f}
  shots (C22): no SKQD energy at 2x2 is a hardware claim; configuration recovery is excluded at 2x2.
- The candidate set of the selection is a proxy-filtered subset ({D['select_summary']['n_candidates']} of
  {D['scan_summary']['n_rows']} transpilations); the best row is the best of that set, not a proven optimum over all
  orders, seeds and patches.

## 9. Verdict block (`data.verdict`)

{md_table(["field", "value"], vrows)}

## 10. Notes

{chr(10).join('- ' + n for n in D['notes'])}

## 11. Criteria

{R.criteria_table()}

P7 reproduction (C3(iii)): ASAP {p7['asap'].get('accepted')} accepted / {p7['asap'].get('reference_hits')} reference hits,
ALAP {p7['alap'].get('accepted')} / {p7['alap'].get('reference_hits')} (identical counts: {p7['asap'].get('identical_counts')} / {p7['alap'].get('identical_counts')}).
"""


# --------------------------------------------------------------------------- driver
STAGES = {"live": stage_live, "scan": stage_scan, "scan-merge": stage_scan_merge,
          "select": stage_select, "fractional": stage_fractional, "rows": stage_rows,
          "aer": stage_aer, "aer-topup": stage_aer_topup, "family": stage_family, "e4": stage_e4,
          "assemble": stage_assemble}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="assemble")
    ap.add_argument("--seeds", type=int, nargs=2, default=None, help="scan: seed range [a, b)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--row", default=None)
    ap.add_argument("--ratio", type=float, default=None)
    ap.add_argument("--chunk", type=int, default=None)
    ap.add_argument("--candidates", nargs="*", default=None)
    ap.add_argument("--extend", action="store_true",
                    help="aer E4: run the EXTRA_CHUNKS too (the C6 second attempt, applied to every E4 cell)")
    ap.add_argument("--skip-tests", action="store_true",
                    help="assemble: do not run pytest / check_package (C9 then FAILS)")
    args = ap.parse_args()
    if args.stage not in STAGES:
        raise SystemExit(f"unknown stage {args.stage}; one of {sorted(STAGES)}")
    return STAGES[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
