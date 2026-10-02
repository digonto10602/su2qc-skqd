#!/usr/bin/env python3
"""
The ibm_kingston pilot of prompts/21 -- live reads, patch selection and the pilot circuit set
(`data/hardware/H0_kpilot_prep/`).  Zero QPU seconds: everything here is a metadata read of the
live target or a local transpilation.

Stages:

  account   A1/E4: instance, plan, usage of the open plan and the status of ibm_kingston
            (`--out <json>`; the API key is never read here, `ibm_account.open_service` opens
            the saved account).  Exit 3 if kingston is not operational or less than
            MIN_REMAINING_S seconds of allowance remain (the prompt's STOP).
  record    A2: `h0_device_survey.full_device_record("ibm_kingston")` (a NEW backend object,
            refreshed) -> `ibm_kingston_full_<stamp>.json`, its `calibration_diff` against the
            S2D_levers record of 2026-10-01, qubit 146's leaves as they are; `live.json` points
            at the record the later stages use.
  select    B1: rule R1'-pilot -- the exhaustive embedding search of
            `gate_S2D_levers.embedding_search` of the `L1_seed` candidate (default term order,
            seed 2) on the day's full record, run ONCE; the winner is the patch.
  build     B2: the 8 pubs in the `h0_build_circuits` manifest format: the three signed-family
            coarse circuits (B0_ref06_k1, B1_ref07_k1, B0_ref06_k4) placed by
            `family_on_patch`'s rule and scheduled ALAP with explicit delays, the windowed
            Ramsey pub at the circuit's duration and at half of it, the windowed T1 pub, and the
            all-0 / all-1 readout calibration of the patch.
  patchcal  B3: the patch-scoped calibration record for rule D9 (`fresh_calibration` over
            `frozen_qubits_and_edges(prep)`), every leaf asserted equal to the full record's.

Usage: python scripts/h0_kpilot_circuits.py --stage account --out data/hardware/H0_kpilot_prep/account_check_<stamp>.json
       python scripts/h0_kpilot_circuits.py --stage record | select | build | patchcal
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PREP = os.path.join("data", "hardware", "H0_kpilot_prep")
DEVICE = "ibm_kingston"
S2D_RECORD = os.path.join("data", "hardware", "S2D_levers_20261001T1902Z",
                          "ibm_kingston_20261001T1902Z.json")
ROW_MANIFEST = os.path.join("data", "S2D_levers", "circuits", "L1_seed_alap.json")
FAMILY_TAG = "diag-hop0-hop1-hop2-hop3-plaq0_s2"
CANDIDATE = {"order": ["diag", "hop0", "hop1", "hop2", "hop3", "plaq0"], "seed": 2}
COARSE_IDS = ("B0_ref06_k1", "B1_ref07_k1", "B0_ref06_k4")
DECIDING = "B0_ref06_k1"
WINDOW_DT_DEFAULT = 128            # prompts/21 Decisions: 128 dt if that is 512 ns (+- 1 ps)
WINDOW_TARGET_S = 512e-9
WINDOW_TOL_S = 1e-12
SEED_TRANSPILER = 7
STATEVECTOR_TOL = 1e-9
AMP_TOL = 1e-10
LEAK_TOL = 1e-9
MIN_REMAINING_S = 60.0             # prompts/21 escalation: less than 60 s of allowance -> STOP
EXIT_STOP = 3


def p(*parts):
    return os.path.join(ROOT, *parts)


def rel(path):
    return os.path.relpath(path, ROOT)


def load_json(path):
    with open(path if os.path.isabs(path) else p(path)) as fh:
        return json.load(fh)


def dump_json(obj, path):
    from skqd.report import _jsonable
    path = path if os.path.isabs(path) else p(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(_jsonable(obj), fh, indent=1)
    os.replace(tmp, path)
    return path


def sha256_of(path):
    with open(path if os.path.isabs(path) else p(path), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def utc_stamp():
    return time.strftime("%Y%m%dT%H%MZ", time.gmtime())


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def live_info(prep=PREP):
    path = p(prep, "live.json")
    if not os.path.exists(path):
        raise SystemExit(f"{rel(path)} missing: run --stage record first")
    return load_json(path)


def day_record(prep=PREP):
    info = live_info(prep)
    return load_json(info["record"]["path"]), info


# --------------------------------------------------------------------------- A1 / E4
def account_snapshot():
    """Instance, plan, usage and the device's status; never the key."""
    from ibm_account import open_service
    svc = open_service()
    out = {"created": now(), "qpu_seconds": 0, "device": DEVICE}
    try:
        u = svc.usage()
        out["usage"] = {k: u.get(k) for k in ("usage_consumed_seconds", "usage_limit_seconds",
                                              "usage_remaining_seconds", "usage_limit_reached",
                                              "usage_period")} if isinstance(u, dict) else str(u)
    except Exception as exc:
        out["usage"] = {"error": str(exc)}
    try:
        out["instances"] = [{k: v for k, v in i.items() if k in ("name", "plan", "pricing_type")}
                            for i in svc.instances()]
    except Exception as exc:
        out["instances"] = {"error": str(exc)}
    try:
        b = svc.backend(DEVICE)
        st = b.status()
        out["backend"] = {"name": b.name, "operational": bool(st.operational),
                          "pending_jobs": int(st.pending_jobs),
                          "status_msg": getattr(st, "status_msg", None),
                          "num_qubits": int(b.num_qubits)}
    except Exception as exc:
        out["backend"] = {"name": DEVICE, "reachable": False, "error": str(exc)}
    try:
        out["backends_visible"] = sorted(x.name for x in svc.backends())
    except Exception as exc:
        out["backends_visible"] = {"error": str(exc)}
    return out


def stage_account(args):
    out = account_snapshot()
    path = args.out or p(PREP, f"account_check_{utc_stamp()}.json")
    dump_json(out, path)
    u = out.get("usage") or {}
    b = out.get("backend") or {}
    print(f"wrote {rel(path) if os.path.isabs(path) else path}: instances "
          f"{out.get('instances')}; usage {u.get('usage_consumed_seconds')} s of "
          f"{u.get('usage_limit_seconds')} s (remaining {u.get('usage_remaining_seconds')} s, "
          f"period {u.get('usage_period')}); {DEVICE} operational {b.get('operational')}, "
          f"pending {b.get('pending_jobs')}")
    stop = []
    if not b.get("operational"):
        stop.append(f"{DEVICE} is not reachable or not operational")
    rem = u.get("usage_remaining_seconds")
    if rem is None or float(rem) < MIN_REMAINING_S:
        stop.append(f"usage remaining {rem} s < {MIN_REMAINING_S:.0f} s")
    if stop and not args.after:
        print("STOP: " + "; ".join(stop))
        return EXIT_STOP
    return 0


# --------------------------------------------------------------------------- A2
def stage_record(args):
    import h0_device_survey as ds
    from h0_backends import calibration_diff
    t0 = time.time()
    rec = ds.full_device_record(DEVICE)
    stamp = rec["stamp"]
    rpath = p(PREP, f"{DEVICE}_full_{stamp}.json")
    if os.path.exists(rpath):
        old = load_json(rpath)
        if old["fingerprint"] != rec["fingerprint"]:
            rpath = p(PREP, f"{DEVICE}_full_{stamp}_{rec['fingerprint'][:8]}.json")
            if os.path.exists(rpath):
                raise SystemExit(f"{rel(rpath)} exists: refusing to overwrite")
            dump_json(rec, rpath)
    else:
        dump_json(rec, rpath)
    ref = load_json(S2D_RECORD)
    d = calibration_diff(ref, rec)
    fam = {}
    for leaf in d["leaves"]:
        f = leaf["path"].split("/")[-1]
        x = fam.setdefault(f, {"n": 0, "ratios": []})
        x["n"] += 1
        if leaf["ratio"] is not None:
            x["ratios"].append(leaf["ratio"])
    fam = {f: {"n_leaves": v["n"],
               "ratio_median": (float(np.median(v["ratios"])) if v["ratios"] else None),
               "ratio_min": (float(min(v["ratios"])) if v["ratios"] else None),
               "ratio_max": (float(max(v["ratios"])) if v["ratios"] else None)}
           for f, v in sorted(fam.items())}
    info = {"stage": "record", "created": now(), "qpu_seconds": 0,
            "record": {"path": rel(rpath), "stamp": stamp, "last_update_date": rec["last_update_date"],
                       "fingerprint": rec["fingerprint"], "n_qubits": len(rec["qubits"]),
                       "n_edges": len(rec["edges"]), "missing_errors": rec["missing_errors"],
                       "status": rec.get("status"), "dt_s": rec["dt_s"],
                       "default_rep_delay_s": rec["default_rep_delay_s"]},
            "diff_vs_S2D_levers_record": {"reference": S2D_RECORD, "reference_fingerprint": ref["fingerprint"],
                                          "n_leaves": d["n_leaves"], "families": d["families"],
                                          "by_family": fam, "max_ratio": d["max_ratio"],
                                          "min_ratio": d["min_ratio"]},
            "qubit_146": rec["qubits"].get("146"),
            "runtime_s": time.time() - t0}
    dump_json(info, p(PREP, "live.json"))
    hist = p(PREP, "records_log.jsonl")
    with open(hist, "a") as fh:
        fh.write(json.dumps({"when": now(), "path": rel(rpath), "fingerprint": rec["fingerprint"],
                             "last_update_date": rec["last_update_date"]}) + "\n")
    print(f"full record {rel(rpath)}: fingerprint {rec['fingerprint'][:16]}, "
          f"{rec['last_update_date']}, status {rec.get('status')}; vs S2D_levers record "
          f"{d['n_leaves']} leaves moved over {d['families']}; qubit 146 {rec['qubits'].get('146')}")
    if not (rec.get("status") or {}).get("operational"):
        print("STOP: the device is not operational")
        return EXIT_STOP
    return 0


# --------------------------------------------------------------------------- B1
def candidate():
    import gate_S2D_levers as G
    cand = {"id": G.cand_id(CANDIDATE["order"], CANDIDATE["seed"]), **CANDIDATE}
    return cand, G.candidate_circuit(cand)


def stage_select(args):
    import gate_S2D_levers as G
    t0 = time.time()
    rec, info = day_record()
    row = load_json(ROW_MANIFEST)
    cand, qc = candidate()
    a0 = G.garbage_acceptance(0)
    s = G.embedding_search(qc, rec, a0, survey_set=row["physical_qubits"], top=5)
    mp = {int(k): int(v) for k, v in s["best"]["mapping"].items()}
    committed = {int(k): int(v) for k, v in row["mapping_transpiled_to_kingston"].items()}
    out = {"stage": "select", "created": now(), "rule": "R1'-pilot (prompts/21): exhaustive "
           "embedding search of the L1_seed candidate on the day's full record, run once; the "
           "winner is the patch",
           "record_path": info["record"]["path"], "record_fingerprint": rec["fingerprint"],
           "candidate": cand, "candidate_ops": {k: int(v) for k, v in qc.count_ops().items()},
           "garbage_acceptance_B0": a0,
           "pattern": s["pattern"], "n_embeddings": s["n_embeddings"], "n_scored": s["n_scored"],
           "n_skipped": s["n_skipped"], "winner": s["best"], "top5": s["top"],
           "winner_mapping": {str(k): v for k, v in sorted(mp.items())},
           "winner_patch": sorted(mp.values()),
           "committed_row": ROW_MANIFEST,
           "committed_mapping": {str(k): v for k, v in sorted(committed.items())},
           "mapping_reproduced": mp == committed,
           "on_survey_patch": s["on_survey_patch"],
           "runtime_s": time.time() - t0}
    dump_json(out, p(PREP, "select.json"))
    print(f"winner {sorted(mp.values())} f_dd_off {s['best']['f_dd_off']:.4f} T {s['best']['T_s'] * 1e6:.2f} us "
          f"({s['n_scored']} of {s['n_embeddings']} embeddings scored); mapping reproduced: "
          f"{mp == committed}; committed set's rank "
          f"{(s['on_survey_patch'] or {}).get('rank')} ({time.time() - t0:.0f} s)")
    return 0


# --------------------------------------------------------------------------- B2
def window_rule(dt, granularity, pulse_alignment):
    """window = 128 dt if that is 512 ns (+- 1 ps), else the multiple of
    max(granularity, pulse_alignment) nearest 512 ns."""
    if abs(WINDOW_DT_DEFAULT * dt - WINDOW_TARGET_S) <= WINDOW_TOL_S:
        w = WINDOW_DT_DEFAULT
        how = "128 dt = 512 ns"
    else:
        m = max(int(granularity or 1), int(pulse_alignment or 1))
        w = int(round(WINDOW_TARGET_S / dt / m)) * m
        how = f"multiple of {m} dt nearest 512 ns"
    return w, how


def n_windows(T_s, window_s):
    n_long = int(round(T_s / window_s))
    return n_long, int(round(n_long / 2))


def expected_idle_ops(test, n, N):
    base = {"delay": N * n, "barrier": N + 1, "measure": n}
    if test == "t1w":
        base["x"] = n
    else:
        base["sx"] = 2 * n
        base["rz"] = 2 * n
    return base


def build_idle(test, n, N, window_dt):
    """`h0_diag_circuits.build_t1w` / `build_ramw` with N windows of `window_dt`."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n, n)
    if test == "t1w":
        for q in range(n):
            qc.x(q)
    else:
        for q in range(n):
            qc.sx(q)
    for _ in range(N):
        for q in range(n):
            qc.delay(window_dt, q, unit="dt")
        qc.barrier()
    if test == "t1w":
        expected = tuple([1] * n)
    else:
        for q in range(n):                  # rz(pi) sx rz(pi) = sx^dagger up to a global phase
            qc.rz(np.pi, q)
            qc.sx(q)
            qc.rz(np.pi, q)
        expected = tuple([0] * n)
    qc.barrier()
    qc.measure(range(n), range(n))
    return qc, expected


def logical_state_explicit(sched, final, global_phase=None):
    """Noiseless statevector of a relabelled / scheduled circuit with an EXPLICIT final layout
    (`skqd.hardware.logical_statevector` with the layout given rather than read: a relabelled
    circuit carries none).  Delays, barriers and measurements are dropped."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    n = len(final)
    active = sorted({sched.find_bit(q).index for inst in sched.data for q in inst.qubits
                     if inst.operation.name not in ("barrier", "delay")})
    phys = sorted(set(active) | set(final))
    pos = {q: i for i, q in enumerate(phys)}
    cc = QuantumCircuit(len(phys))
    cc.global_phase = sched.global_phase if global_phase is None else global_phase
    for inst in sched.data:
        if inst.operation.name in ("measure", "barrier", "delay"):
            continue
        cc.append(inst.operation, [pos[sched.find_bit(q).index] for q in inst.qubits])
    psi = np.asarray(Statevector(cc).data)
    idx = np.arange(psi.size)
    keep = np.ones(psi.size, dtype=bool)
    for q in phys:
        if q not in set(final):
            keep &= ((idx >> pos[q]) & 1) == 0
    li = np.zeros(psi.size, dtype=np.int64)
    for i in range(n):
        li |= ((idx >> pos[final[i]]) & 1) << i
    out = np.zeros(2 ** n, dtype=complex)
    out[li[keep]] = psi[keep]
    return out


def strip_register_delays(sched):
    """(circuit, n removed): drop the delays on qubits that carry no other operation."""
    used = {sched.find_bit(q).index for inst in sched.data for q in inst.qubits
            if inst.operation.name not in ("delay", "barrier")}
    out = sched.copy_empty_like()
    n = 0
    for inst in sched.data:
        if inst.operation.name == "delay" and sched.find_bit(inst.qubits[0]).index not in used:
            n += 1
            continue
        out.append(inst)
    return out, n


def measurement_map(sched):
    m = {}
    for inst in sched.data:
        if inst.operation.name == "measure":
            m[int(sched.find_bit(inst.clbits[0]).index)] = int(sched.find_bit(inst.qubits[0]).index)
    return m


def coarse_exactness(sched, final, order, ref, theta, global_phase=None):
    """C4 of prompts/23 on the circuit that is SUBMITTED (relabelled, ALAP-scheduled).
    `h0_patch_select.relabel` builds a new QuantumCircuit and does not carry the transpiled
    circuit's global phase (unobservable in sampling); the source circuit's phase is passed in
    so that the amplitudes are compared exactly, and the phase actually carried is recorded."""
    import gate_S2D_levers as G
    from skqd.reference_sim import CodewordEmbedding
    fx = G.factory()
    emb = CodewordEmbedding(fx["M"])
    psi = logical_state_explicit(sched, final, global_phase)
    exact = G.exact_state(order, ref, theta)
    dev = float(np.max(np.abs(emb.project(psi) - exact)))
    leak = float(emb.leakage(psi))
    mm = measurement_map(sched)
    cons = len(mm) == len(final) and all(mm.get(i) == final[i] for i in range(len(final)))
    return {"max_abs_delta": dev, "leakage": leak, "measurement_consistent": bool(cons),
            "ok": bool(dev < AMP_TOL and leak < LEAK_TOL and cons)}


def place_family(rec, mp, row_pattern, patch):
    """`gate_S2D_levers.family_on_patch`'s rule with the day's winner: the winner's mapping
    for an identical pattern, else the best embedding onto the SAME qubit set."""
    import gate_S2D_levers as G
    from qiskit import qpy
    fam = load_json(p("data", "S2D_levers", "family.json"))["families"][FAMILY_TAG]
    by_id = {c["id"]: c for c in fam["circuits"]}
    a = {0: G.garbage_acceptance(0), 2: G.garbage_acceptance(2)}
    out = {}
    for cid in COARSE_IDS:
        c = by_id[cid]
        qpath = p(fam["qpy_dir"], cid + ".qpy.gz")
        with gzip.open(qpath, "rb") as fh:
            tq = qpy.load(fh)[0]
        pat = sorted(tuple(sorted(e)) for e in c["pattern_edges"])
        if pat == row_pattern:
            mapping, how = mp, "the winner's mapping (identical pattern)"
        else:
            s = G.embedding_search(tq, rec, a[c["twoB"]], top=10 ** 6)
            same = [e for e in s["top"] if set(e["physical_qubits"]) == set(patch)]
            if not same:
                raise SystemExit(f"{cid}: no embedding onto the patch {sorted(patch)} -- the family "
                                 f"circuit cannot share the pilot's readout calibration (STOP)")
            mapping, how = G.mapping_of(same[0]), "best embedding onto the patch's qubit set"
        out[cid] = {"member": c, "tq": tq, "mapping": mapping, "placement": how,
                    "source_qpy": rel(qpath), "source_qpy_sha256": sha256_of(qpath)}
    return out


def stage_build(args):
    import gate_S2D_levers as G
    from h0_backends import backend_from_record
    from h0_build_circuits import dump_qpy_gz
    from qiskit import qpy, transpile
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    from skqd import idle
    from skqd.hardware import logical_statevector, transpiled_layout
    t0 = time.time()
    rec, info = day_record()
    sel = load_json(p(PREP, "select.json"))
    if sel["record_fingerprint"] != rec["fingerprint"]:
        raise SystemExit("select.json was made on another record than live.json points at: "
                         "re-run --stage select (D10)")
    base, binfo = backend_from_record(rec, base=FakeKingston(), strict=True)
    tgt = base.target
    dt = float(base.dt)
    gran = int(getattr(tgt, "granularity", 1) or 1)
    align = int(getattr(tgt, "pulse_alignment", 1) or 1)
    window_dt, how = window_rule(dt, gran, align)
    window_s = window_dt * dt
    mp = {int(k): int(v) for k, v in sel["winner_mapping"].items()}
    patch = sorted(mp.values())
    row = load_json(ROW_MANIFEST)
    cand, cand_qc = candidate()
    row_pattern = sorted(tuple(sorted(int(x) for x in e)) for e in G.interaction_graph_2q(cand_qc)[1])
    fx = G.factory()
    n = fx["n"]
    index_common = dict(load_json(p("data", "hardware", "H0_prep", "index.json"))["common"])
    common = dict(index_common)
    common.update({"backend": "FakeKingston", "backend_qubits": 156, "n_logical_qubits": n,
                   "backend_calibration_last_update": rec["last_update_date"],
                   "transpiler": {"note": "per circuit (see its manifest)"},
                   "circuit_family": ("exact structured circuits, signed default term order, "
                                      "transpiled at seed 2 (gate S2D_levers L1_seed / family "
                                      f"{FAMILY_TAG}), relabelled onto the day's patch and "
                                      "scheduled ALAP with explicit delays")})
    outdir = p(PREP)
    cdir = os.path.join(outdir, "circuits")
    os.makedirs(cdir, exist_ok=True)
    stale = [f for f in os.listdir(cdir)] if os.path.isdir(cdir) else []
    if stale and not args.force:
        raise SystemExit(f"{rel(cdir)} is not empty ({len(stale)} files): a rebuild on new content "
                         f"(D10) needs --force, which clears it first")
    for f in stale:
        os.remove(os.path.join(cdir, f))

    placed = place_family(rec, mp, row_pattern, patch)
    # B0_ref06_k1: the committed L1_seed_alap QPY byte for byte when the mapping is reproduced
    src_note = {}
    if sel["mapping_reproduced"]:
        qp = p(row["qpy"])
        sha = sha256_of(qp)
        if sha != row["qpy_gz_sha256"]:
            raise SystemExit(f"{row['qpy']} hashes to {sha}, the manifest records {row['qpy_gz_sha256']}")
        with gzip.open(qp, "rb") as fh:
            rc0 = qpy.load(fh)[0]
        alt = G.relabelled(placed[DECIDING]["tq"], mp)
        src_note = {"source": row["qpy"], "source_qpy_sha256": sha, "byte_for_byte": True,
                    "equals_relabelled_family_circuit": bool(rc0 == alt)}
        if not src_note["equals_relabelled_family_circuit"]:
            raise SystemExit("the committed L1_seed_alap circuit is not the family's B0_ref06_k1 "
                             "relabelled by the same mapping: its logical layout cannot be read")
    else:
        rc0 = G.relabelled(cand_qc, mp)
        src_note = {"source": f"candidate {cand['id']} relabelled onto the winner",
                    "source_qpy_sha256": None, "byte_for_byte": False}

    manifests = []
    coarse_T = {}
    for cid in COARSE_IDS:
        x = placed[cid]
        c = x["member"]
        rc = rc0 if cid == DECIDING else G.relabelled(x["tq"], x["mapping"])
        lay0 = transpiled_layout(x["tq"], n)
        final = [int(x["mapping"].get(int(q), int(q))) for q in lay0["logical_to_physical"]]
        if sorted(final) != patch:
            raise SystemExit(f"{cid}: logical qubits land on {sorted(final)}, not the patch {patch}")
        sched_full, sinfo = G.scheduled(rc, base, "alap")
        sched, n_removed = strip_register_delays(sched_full)
        sinfo["idle_register_delays_removed"] = n_removed
        sinfo["idle_register_delays_note"] = (
            "the transpiler pads every qubit of the 156-qubit register with a full-length delay; "
            "delays on qubits that carry no gate and no measurement are no-ops and are removed so "
            "that the pubs (and the D9 fingerprint scope) touch only the patch")
        ex = coarse_exactness(sched, final, CANDIDATE["order"], c["reference"], c["theta"],
                              global_phase=x["tq"].global_phase)
        ex["global_phase_source"] = float(x["tq"].global_phase)
        ex["global_phase_submitted"] = float(sched.global_phase)
        if not ex["ok"]:
            raise SystemExit(f"{cid}: exactness failed {ex}")
        sch_unsched = idle.schedule_asap(rc, rec)
        dsch = G.delay_schedule(sched, rec, include_leading=False)
        from h0_qpu_time import circuit_duration_s
        d_sched = circuit_duration_s(sched, tgt.durations(), tgt)
        fg, n2, f1 = G.f_gates_on_record(rc, rec)
        d = G.ideal_distribution(CANDIDATE["order"], c["twoB"], c["reference"], c["theta"])
        name = f"{cid}.qpy.gz"
        raw, sha = dump_qpy_gz(sched, os.path.join(cdir, name))
        active = sorted({sched.find_bit(q).index for inst in sched.data for q in inst.qubits
                         if inst.operation.name not in ("barrier",)})
        man = dict(common)
        man.update({
            "id": cid, "kind": "coarse_step", "test": None, "sector": c["sector"], "twoB": int(c["twoB"]),
            "reference": int(c["reference"]), "k": int(c["k"]), "repetitions": 1,
            "dt": float(c["dt"]), "theta": float(c["theta"]),
            "order": CANDIDATE["order"], "seed": CANDIDATE["seed"],
            "placement": x["placement"] if cid != DECIDING else
            ("the committed L1_seed_alap circuit (mapping reproduced)" if sel["mapping_reproduced"]
             else "the candidate relabelled onto the winner"),
            "mapping_transpiled_to_kingston": {str(k): int(v) for k, v in sorted(x["mapping"].items())},
            "physical_qubits": active, "readout_patch": sorted(final),
            "logical_to_physical": final,
            "measurement_map_clbit_to_physical": {str(k): v for k, v in sorted(measurement_map(sched).items())},
            "measurement_consistent": ex["measurement_consistent"],
            "ops": {k: int(v) for k, v in sched.count_ops().items()},
            "cz": int(sched.count_ops().get("cz", 0)), "depth": int(sched.depth()),
            "schedule": "alap", "schedule_info": sinfo,
            "T_s": sch_unsched["T_s"], "T_total_s": sch_unsched["T_total_s"],
            "T_s_note": ("critical path before the readout of the unscheduled circuit on the day's record "
                         "(gate_S2D_levers.compile_stats); the ALAP circuit's duration equals T_total_s"),
            "scheduled_duration_s": d_sched,
            "n_delays": int(sched.count_ops().get("delay", 0)),
            "leading_delay_s": {str(k): v for k, v in sorted(dsch["leading_s"].items())},
            "exactness": {k: ex[k] for k in ("max_abs_delta", "leakage", "measurement_consistent", "ok",
                                             "global_phase_source", "global_phase_submitted")},
            "f_gates_record": fg, "f_including_1q_errors_record": f1,
            "p_reference": d["p_reference"], "dim": d["dim"], "sector_mass": d["sector_mass"],
            "record_fingerprint_full": rec["fingerprint"],
            "source_qpy": src_note.get("source") if cid == DECIDING else x["source_qpy"],
            "source_qpy_sha256": (src_note.get("source_qpy_sha256") if cid == DECIDING
                                  else x["source_qpy_sha256"]),
            "source_note": src_note if cid == DECIDING else {"family": FAMILY_TAG},
            "qpy": name, "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha,
        })
        # C7 of S2D_levers: the scheduled duration equals the unscheduled critical path + readout
        if abs(d_sched - sch_unsched["T_total_s"]) > 1e-12:
            raise SystemExit(f"{cid}: ALAP duration {d_sched} != unscheduled T_total {sch_unsched['T_total_s']}")
        coarse_T[cid] = sch_unsched["T_s"]
        manifests.append(man)
        print(f"  {cid}: {man['placement']}; cz {man['cz']}, delays {man['n_delays']}, T_s "
              f"{sch_unsched['T_s'] * 1e6:.2f} us, |d| {ex['max_abs_delta']:.1e}, leak {ex['leakage']:.1e}, "
              f"p_ref {d['p_reference']:.4f}", flush=True)

    T_s = coarse_T[DECIDING]
    N_long, N_half = n_windows(T_s, window_s)
    windows = {"dt_s": dt, "granularity": gran, "pulse_alignment": align, "window_dt": window_dt,
               "window_rule": how, "window_s": window_s, "T_s_matched": T_s,
               "T_s_matched_circuit": DECIDING, "N_long": N_long, "N_half": N_half,
               "total_delay_long_s": N_long * window_s, "total_delay_half_s": N_half * window_s}
    print(f"windows: dt {dt:.3e} s, granularity {gran}, pulse_alignment {align}, window {window_dt} dt = "
          f"{window_s * 1e9:.1f} ns ({how}); T_s {T_s * 1e6:.2f} us -> N_long {N_long} "
          f"({N_long * window_s * 1e6:.2f} us), N_half {N_half} ({N_half * window_s * 1e6:.2f} us)")

    for cid, test, N, wlabel in (("kpilot_ramw_long", "ramw", N_long, "long"),
                                 ("kpilot_ramw_half", "ramw", N_half, "half"),
                                 ("kpilot_t1w_long", "t1w", N_long, "long")):
        qc, expected = build_idle(test, n, N, window_dt)
        tq = transpile(qc, backend=base, initial_layout=list(patch), optimization_level=0,
                       seed_transpiler=SEED_TRANSPILER)
        ops = {k: int(v) for k, v in tq.count_ops().items()}
        want = expected_idle_ops(test, n, N)
        if ops != want:
            raise SystemExit(f"{cid}: transpiled ops {ops} != the intended {want}")
        lay = transpiled_layout(tq, n)
        if lay["logical_to_physical"] != list(patch) or not lay["measurement_consistent"]:
            raise SystemExit(f"{cid}: layout {lay['logical_to_physical']} / measurement map not the patch")
        psi = logical_statevector(tq, n)
        want_index = sum(int(b) << q for q, b in enumerate(expected))
        pexp = float(abs(psi[want_index]) ** 2)
        if pexp < 1.0 - STATEVECTOR_TOL:
            raise SystemExit(f"{cid}: noiseless P(expected) = {pexp!r}")
        name = cid + ".qpy.gz"
        raw, sha = dump_qpy_gz(tq, os.path.join(cdir, name))
        man = dict(common)
        man.update({
            "id": cid, "kind": "idle_test", "test": test, "window": wlabel, "sector": None,
            "twoB": None, "reference": None, "k": None, "repetitions": 1,
            "expected_bits": list(expected), "expected_key": "".join(str(b) for b in reversed(expected)),
            "n_windows": N, "window_dt": window_dt, "window_s": window_s, "total_delay_s": N * window_s,
            "noiseless_probability_of_the_expected_string": pexp,
            "physical_qubits": lay["active_physical"], "readout_patch": sorted(lay["logical_to_physical"]),
            "logical_to_physical": lay["logical_to_physical"],
            "measurement_map_clbit_to_physical": lay["measurement_map"],
            "measurement_consistent": lay["measurement_consistent"],
            "transpiler": {"optimization_level": 0, "seed_transpiler": SEED_TRANSPILER,
                           "initial_layout": list(patch)},
            "depth": int(tq.depth()), "ops": ops, "expected_ops": want, "ops_as_intended": ops == want,
            "record_fingerprint_full": rec["fingerprint"],
            "qpy": name, "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha})
        manifests.append(man)
        print(f"  {cid}: {ops}, P(expected) {pexp:.12f}", flush=True)

    from qiskit import QuantumCircuit
    for name_, bits in (("all0", (0,) * n), ("all1", (1,) * n)):
        cid = f"cal_patch_{name_}"
        qc = QuantumCircuit(n, n)
        for q, b in enumerate(bits):
            if b:
                qc.x(q)
        qc.barrier()
        qc.measure(range(n), range(n))
        tq = transpile(qc, backend=base, initial_layout=list(patch), optimization_level=1,
                       seed_transpiler=SEED_TRANSPILER)
        lay = transpiled_layout(tq, n)
        if not lay["measurement_consistent"] or lay["logical_to_physical"] != list(patch):
            raise SystemExit(f"{cid}: measurement map / layout not the patch")
        psi = logical_statevector(tq, n)
        want = sum(int(b) << q for q, b in enumerate(bits))
        if abs(abs(psi[want]) - 1.0) > 1e-9:
            raise SystemExit(f"{cid}: transpiled preparation does not produce {bits}")
        raw, sha = dump_qpy_gz(tq, os.path.join(cdir, cid + ".qpy.gz"))
        man = dict(common)
        man.update({"id": cid, "kind": "readout_calibration", "patch_index": 0,
                    "readout_error_record": [float(rec["qubits"][str(q)]["measure_error"])
                                             for q in lay["logical_to_physical"]],
                    "prep_bits": list(bits), "prep_name": name_, "repetitions": None,
                    "physical_qubits": lay["active_physical"],
                    "readout_patch": sorted(lay["logical_to_physical"]),
                    "logical_to_physical": lay["logical_to_physical"],
                    "measurement_map_clbit_to_physical": lay["measurement_map"],
                    "measurement_consistent": lay["measurement_consistent"],
                    "transpiler": {"optimization_level": 1, "seed_transpiler": SEED_TRANSPILER,
                                   "initial_layout": list(patch)},
                    "ops": {kk: int(v) for kk, v in tq.count_ops().items()},
                    "record_fingerprint_full": rec["fingerprint"],
                    "qpy": cid + ".qpy.gz", "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha})
        manifests.append(man)
        print(f"  {cid}: {man['ops']}", flush=True)

    for m in manifests:
        dump_json(m, os.path.join(cdir, m["id"] + ".json"))
    qubits, edges = set(), set()
    for m in manifests:
        with gzip.open(os.path.join(cdir, m["qpy"]), "rb") as fh:
            qc = qpy.load(fh)[0]
        for inst in qc.data:
            if len(inst.qubits) == 2 and inst.operation.name != "barrier":
                a, b = (qc.find_bit(q).index for q in inst.qubits)
                edges.add((a, b))
            for q in inst.qubits:
                qubits.add(qc.find_bit(q).index)
    index = {
        "created": now(), "script": "scripts/h0_kpilot_circuits.py", "stage": "build",
        "purpose": ("prompts/21: the ibm_kingston pilot -- windowed Ramsey at the circuit's duration "
                    "and at half of it, windowed T1, readout reference, and the signed family's "
                    "k = 1 (and one k = 4) circuits on the patch the day's calibration selects"),
        "common": common, "record": info["record"], "base_backend": {k: v for k, v in binfo.items()
                                                                     if k not in ("qubits", "edges")},
        "patch": patch, "winner_mapping": sel["winner_mapping"],
        "mapping_reproduced": sel["mapping_reproduced"], "windows": windows,
        "frozen_set": {"qubits": sorted(qubits), "edges": sorted(map(list, edges)), "n_edges": len(edges)},
        "n_circuits": len([m for m in manifests if m["kind"] != "readout_calibration"]),
        "n_calibration_circuits": len([m for m in manifests if m["kind"] == "readout_calibration"]),
        "circuits": [{k: m.get(k) for k in ("id", "kind", "test", "window", "sector", "k",
                                            "physical_qubits", "logical_to_physical", "ops", "qpy",
                                            "qpy_gz_sha256", "T_s", "n_windows")} for m in manifests],
        "runtime_s": time.time() - t0}
    dump_json(index, os.path.join(outdir, "index.json"))
    print(f"wrote {len(manifests)} circuits to {rel(cdir)} ({len(qubits)} qubits, {len(edges)} directed "
          f"edges) in {time.time() - t0:.0f} s")
    return 0


# --------------------------------------------------------------------------- B3
def leaves_equal(patch_rec, full_rec):
    """Every qubit leaf and every edge (cz error/duration) leaf of the patch record equals the
    full record's.  Returns the list of differences."""
    diffs = []
    for q, v in patch_rec["qubits"].items():
        fv = full_rec["qubits"].get(q)
        if fv is None:
            diffs.append(f"qubit {q} missing in the full record")
            continue
        for k, x in v.items():
            if fv.get(k) != x:
                diffs.append(f"qubit {q} {k}: {x} vs {fv.get(k)}")
    for key, e in patch_rec["edges"].items():
        fe = full_rec["edges"].get(key)
        if fe is None:
            diffs.append(f"edge {key} missing in the full record")
            continue
        for k in ("cz_error", "cz_duration_s"):
            if fe.get(k) != e.get(k):
                diffs.append(f"edge {key} {k}: {e.get(k)} vs {fe.get(k)}")
    for k in ("dt_s", "default_rep_delay_s"):
        if patch_rec.get(k) != full_rec.get(k):
            diffs.append(f"{k}: {patch_rec.get(k)} vs {full_rec.get(k)}")
    return diffs


def stage_patchcal(args):
    from h0_backends import fresh_calibration, frozen_qubits_and_edges, resolve_backend
    rec, info = day_record()
    qubits, edges = frozen_qubits_and_edges(p(PREP))
    b = resolve_backend(DEVICE)
    prec = fresh_calibration(b, qubits, edges)
    diffs = leaves_equal(prec, rec)
    path = p(PREP, f"calibration_{prec['stamp']}.json")
    if os.path.exists(path) and load_json(path)["fingerprint"] != prec["fingerprint"]:
        path = p(PREP, f"calibration_{prec['stamp']}_{prec['fingerprint'][:8]}.json")
    prec["full_record"] = info["record"]["path"]
    prec["full_record_fingerprint"] = rec["fingerprint"]
    prec["leaves_equal_full_record"] = not diffs
    prec["leaf_differences"] = diffs[:50]
    dump_json(prec, path)
    info["patch_record"] = {"path": rel(path), "fingerprint": prec["fingerprint"],
                            "stamp": prec["stamp"], "last_update_date": prec["last_update_date"],
                            "leaves_equal_full_record": not diffs, "n_differences": len(diffs),
                            "missing_errors": prec["missing_errors"],
                            "n_qubits": len(prec["qubits"]), "n_edges": len(prec["edges"])}
    dump_json(info, p(PREP, "live.json"))
    print(f"patch record {rel(path)}: fingerprint {prec['fingerprint']} ({len(prec['qubits'])} qubits, "
          f"{len(prec['edges'])} edges), missing_errors {len(prec['missing_errors'])}, leaves equal to "
          f"the full record: {not diffs} ({len(diffs)} differences)")
    if diffs:
        print("the calibration moved between the full read and the patch read: repeat A2-B3 (D10)")
        for d in diffs[:10]:
            print("   ", d)
        return EXIT_STOP
    if prec["missing_errors"]:
        print("STOP: missing error leaves on the selected patch")
        return EXIT_STOP
    return 0


STAGES = {"account": stage_account, "record": stage_record, "select": stage_select,
          "build": stage_build, "patchcal": stage_patchcal}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--out", default=None)
    ap.add_argument("--after", action="store_true", help="account: the post-pilot read (no STOP)")
    ap.add_argument("--force", action="store_true", help="build: clear circuits/ first (D10 rebuild)")
    args = ap.parse_args()
    return STAGES[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
