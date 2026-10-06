#!/usr/bin/env python3
"""
prompts/32 A.1 -- the H0_ddrep circuit set on ibm_kingston (`data/hardware/H0_ddrep_prep/`):
seven DD cells x the two signed k = 1 circuits, four pulse-train pubs and the patch's two
readout pubs (20 pubs, one job).  Zero QPU seconds: every stage is a metadata read of the live
device or a local transpilation.  `h0_ddtest_circuits.py` is imported, never edited.

Cells (planner decision P3, parameters fixed before any data):
  T0  no DD                                    the committed H0_ddtest T0 QPY (byte for byte)
  T1  context-aware Walsh-X DD, 128 dt         the committed H0_ddtest T1 QPY
  T3  XY4 in windows >= 1.024 us               the committed H0_ddtest T3 QPY
  M1  CA +/-: T1 with every 2nd inserted x per qubit wrapped as rz(-pi) x rz(pi) (= -X)
  M2  XX: PadDynamicalDecoupling([X, X], ratio 4.0) on the runtime's window set (= T2's)
  M3  X(-X): M2 with alternating signs
  M4  T1 minus every inserted pulse on the two qubits with the most T1 pulses (x -> delay)
Trains (P4): on all 12 patch qubits from |0>, n back-to-back x then measure: XX-8, XX-32,
XX-128, XpXm-128 (alternating signs by the same rule).  Manifests of kind `idle_test`
(`test: "pulse_train"`): `gate_H0P.load_manifests` hands that kind to `h0_submit.py` at
`--shots` and `h0_qpu_time.estimate` times it; a kind `pulse_train` would be silently dropped.

Stages (all `--prep`-scoped):
  account   instance, usage, kingston status -> account_check_<stamp>.json (exit 3 below
            --min-remaining 345 s or if kingston is not `active`)
  record    the day's full-device record (or `--record <committed json>` for the offline
            prototype), its calibration_diff against the 2026-10-02 record (information)
  select    P2: the R1'-pilot search on the day's record; the committed patch is kept unless
            (a) one of its qubits / edges is uncalibrated or (b) its f_dd_off < 0.5 x the winner's
  build     the 20 pubs, every DD cell verified in memory (dd_checks (i)-(v), dd_exactness) and
            the three P3 identities asserted
  patchcal  the patch-scoped D9 record (live), or the committed patch record (offline prototype)
"""
import argparse
import gzip
import json
import math
import os
import shutil
import sys
import time
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import h0_ddtest_circuits as DT  # noqa: E402  (import only)
import h0_kpilot_circuits as KP  # noqa: E402  (import only)

ROOT = KP.ROOT
PREP = os.path.join("data", "hardware", "H0_ddrep_prep")
DDTEST_PREP = os.path.join("data", "hardware", "H0_ddtest_prep")
COMMITTED_FULL_RECORD = os.path.join(DDTEST_PREP, "ibm_kingston_full_20261002T1906Z.json")
COMMITTED_PATCH_RECORD = os.path.join(DDTEST_PREP, "calibration_20261002T1906Z.json")
DEVICE = "ibm_kingston"
BASE_IDS = DT.BASE_IDS
CELLS = ("T0", "T1", "T3", "M1", "M2", "M3", "M4")
REUSED_CELLS = ("T0", "T1", "T3")
NEW_CELLS = ("M1", "M2", "M3", "M4")
# ---- P3 / P4 parameters (fixed before data)
XX_RATIO = 4.0                      # 4.0 x (2 x 32 ns) = 256 ns = T2's threshold 2.0 x (4 x 32 ns)
N_HOT = 2
TRAINS = {"train_XX_8": (8, False), "train_XX_32": (32, False), "train_XX_128": (128, False),
          "train_XpXm_128": (128, True)}
P2_SCORE_FRACTION = 0.5             # P2 (b): keep unless f_dd_off < 0.5 x the winner's
MIN_REMAINING_S = 345.0             # A.1.1: 300 (B's cap) + 45 (A's billed cap)
CELL_DESCRIPTION = {
    "T0": DT.CELL_DESCRIPTION["T0"], "T1": DT.CELL_DESCRIPTION["T1"], "T3": DT.CELL_DESCRIPTION["T3"],
    "M1": "CA +/-: T1's pulse trains with alternating signs (every 2nd inserted x per qubit -> rz(-pi) x rz(pi) = -X); timing identical to T1",
    "M2": "XX: X-only CPMG pairs (qiskit_ibm_runtime PadDynamicalDecoupling [X, X], ratio 4.0) on T2's window set",
    "M3": "X(-X): M2 with alternating signs; timing identical to M2",
    "M4": "CA minus the two hottest qubits: T1 with every inserted pulse removed from the two qubits that carry the most T1 pulses (x -> delay of the x duration)",
}
PULSE_TRAIN_KIND = "idle_test"

p, rel, load_json, dump_json, sha256_of, utc_stamp, now = (KP.p, KP.rel, KP.load_json, KP.dump_json,
                                                           KP.sha256_of, KP.utc_stamp, KP.now)


# =========================================================================== pure circuit functions
def instruction_times(circ, rec):
    """[(start_dt, duration_dt) or None] aligned with circ.data (None for a barrier), with the
    same per-qubit clock as `h0_ddtest_circuits.timeline`."""
    dt = float(rec["dt_s"])
    t, out = {}, []
    for inst in circ.data:
        if inst.operation.name == "barrier":
            out.append(None)
            continue
        qs = [circ.find_bit(q).index for q in inst.qubits]
        st = max(t.get(q, 0) for q in qs)
        d = DT.op_duration_dt(inst, circ, rec, dt)
        for q in qs:
            t[q] = st + d
        out.append((st, d))
    return out


def inserted_flags(base, out, rec):
    """[bool] aligned with out.data: True for a non-delay, non-barrier operation of `out` that
    is not an operation of `base` at the same start time (the DD insertions)."""
    base_ops = Counter()
    for inst, tm in zip(base.data, instruction_times(base, rec)):
        nm = inst.operation.name
        if tm is None or nm == "delay":
            continue
        base_ops[(nm, tuple(base.find_bit(q).index for q in inst.qubits), tm[0])] += 1
    flags = []
    for inst, tm in zip(out.data, instruction_times(out, rec)):
        nm = inst.operation.name
        if tm is None or nm == "delay":
            flags.append(False)
            continue
        key = (nm, tuple(out.find_bit(q).index for q in inst.qubits), tm[0])
        if base_ops[key] > 0:
            base_ops[key] -= 1
            flags.append(False)
        else:
            flags.append(True)
    return flags


def inserted_multiset(base, out, rec, names=None):
    """Counter of (name, qubit, start) of the inserted operations of `out` (optionally only `names`)."""
    c = Counter()
    for inst, tm, f in zip(out.data, instruction_times(out, rec), inserted_flags(base, out, rec)):
        if f and (names is None or inst.operation.name in names):
            c[(inst.operation.name, out.find_bit(inst.qubits[0]).index, tm[0])] += 1
    return c


def wrap_negative(out_circ, qubits):
    """Append rz(-pi), x, rz(+pi) in circuit order: the matrix Rz(pi) X Rz(-pi) = -X exactly."""
    from qiskit.circuit.library import RZGate, XGate
    out_circ.append(RZGate(-math.pi), qubits)
    out_circ.append(XGate(), qubits)
    out_circ.append(RZGate(math.pi), qubits)


def alternate_signs(out, base, rec):
    """(circuit, n_wrapped): on every qubit every second INSERTED x of `out` (2nd, 4th, ...,
    circuit order) wrapped as rz(-pi) x rz(+pi); base operations untouched, timing identical
    (rz is virtual)."""
    flags = inserted_flags(base, out, rec)
    res = out.copy_empty_like()
    seen = Counter()
    n = 0
    for inst, f in zip(out.data, flags):
        if f and inst.operation.name == "x":
            q = out.find_bit(inst.qubits[0]).index
            seen[q] += 1
            if seen[q] % 2 == 0:
                wrap_negative(res, inst.qubits)
                n += 1
                continue
        res.append(inst)
    return res, n


def strip_pulses_on(out, base, rec, hot):
    """(circuit, n_removed): every INSERTED operation of `out` on a qubit of `hot` replaced by
    a delay of its own duration (an x is 8 dt on kingston), so every other start time is
    unchanged."""
    from qiskit.circuit import Delay
    flags = inserted_flags(base, out, rec)
    times = instruction_times(out, rec)
    res = out.copy_empty_like()
    hot = {int(q) for q in hot}
    n = 0
    for inst, f, tm in zip(out.data, flags, times):
        if f and out.find_bit(inst.qubits[0]).index in hot:
            if tm[1] > 0:
                res.append(Delay(int(tm[1]), unit="dt"), inst.qubits)
            n += 1
            continue
        res.append(inst)
    return res, n


def delay_windows(circ, rec):
    """[(qubit, start, end)] of the delay instructions of a padded circuit (dt)."""
    w = []
    for inst, tm in zip(circ.data, instruction_times(circ, rec)):
        if tm is not None and inst.operation.name == "delay":
            w.append((circ.find_bit(inst.qubits[0]).index, tm[0], tm[0] + tm[1]))
    return w


def pulsed_windows(base, out, rec):
    """Sorted [(qubit, start, end)] of the base's delay windows that contain the start of at
    least one inserted x of `out` (the window set the DD pass pulsed)."""
    wins = delay_windows(base, rec)
    by_q = {}
    for q, a, b in wins:
        by_q.setdefault(q, []).append((a, b))
    hit = set()
    for (nm, q, st), _n in inserted_multiset(base, out, rec, names=("x",)).items():
        for a, b in by_q.get(q, []):
            if a <= st < b:
                hit.add((q, a, b))
                break
        else:
            hit.add((q, None, st))          # an inserted pulse outside every base window (never expected)
    return sorted(hit, key=lambda x: (x[0], -1 if x[1] is None else x[1], x[2]))


def hot_qubits(pulses_per_qubit, k=N_HOT):
    """The k qubits with the most pulses (ties broken by the smaller physical index)."""
    items = sorted(((int(q), int(n)) for q, n in pulses_per_qubit.items()), key=lambda x: (-x[1], x[0]))
    return sorted(q for q, _n in items[:k])


def xx_variant(base_sched, rec, target):
    """(circuit, parameters) of cell M2 -- `dd_variant`'s T2 code path with [X, X] at ratio 4.0."""
    from qiskit.circuit.library import XGate
    from qiskit.transpiler import PassManager
    from qiskit_ibm_runtime.transpiler.passes.scheduling import ALAPScheduleAnalysis, PadDynamicalDecoupling
    align = int(getattr(target, "pulse_alignment", 1) or 1)
    dur = DT.record_durations(rec)
    pm = PassManager([ALAPScheduleAnalysis(durations=dur),
                      PadDynamicalDecoupling(durations=dur, dd_sequences=[XGate(), XGate()],
                                             sequence_min_length_ratios=[XX_RATIO], pulse_alignment=align)])
    out = pm.run(base_sched)
    out, nrem = KP.strip_register_delays(out)
    par = {"pass": ("qiskit_ibm_runtime.transpiler.passes.scheduling.ALAPScheduleAnalysis(durations) + "
                    "PadDynamicalDecoupling(durations, [X, X], ...)"),
           "parameters": {"sequence": "XX", "sequence_min_length_ratios": [XX_RATIO], "pulse_alignment": align,
                          "skip_reset_qubits": True, "durations_from": rec.get("stamp")},
           "y_translated": 0, "idle_register_delays_removed_after_pass": nrem}
    return out, par


def pulse_train(patch, n, alternating, num_qubits):
    """n back-to-back x on every patch qubit from |0>, then measure (clbit i <- patch[i])."""
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import XGate
    qc = QuantumCircuit(num_qubits, len(patch))
    for q in patch:
        for j in range(n):
            if alternating and j % 2 == 1:
                wrap_negative(qc, [qc.qubits[q]])
            else:
                qc.append(XGate(), [qc.qubits[q]])
    qc.barrier([qc.qubits[q] for q in patch])
    for i, q in enumerate(patch):
        qc.measure(q, i)
    return qc


def op_sequence(qc, q):
    """The per-qubit op tokens of a circuit (rz carries its angle in units of pi)."""
    seq = []
    for inst in qc.data:
        if inst.operation.name in ("barrier",):
            continue
        if q in [qc.find_bit(x).index for x in inst.qubits]:
            nm = inst.operation.name
            if nm == "rz":
                seq.append(f"rz({float(inst.operation.params[0]) / math.pi:+.0f}pi)")
            else:
                seq.append(nm)
    return seq


# =========================================================================== stages
def stage_account(args):
    rc = DT.stage_account(args)
    import glob
    fs = sorted(glob.glob(p(args.prep, "account_check_*.json")))
    if fs and not args.after:
        b = (load_json(fs[-1]).get("backend") or {})
        if b.get("status_msg") != "active":
            print(f"STOP: {DEVICE} status_msg {b.get('status_msg')!r} != 'active'")
            return KP.EXIT_STOP
    return rc


def stage_record(args):
    if not args.record:
        return DT.stage_record(args)
    from h0_backends import calibration_diff
    rec = load_json(args.record)
    ref = load_json(args.diff_against)
    d = calibration_diff(ref, rec)
    info = {"stage": "record", "created": now(), "qpu_seconds": 0, "offline_prototype": True,
            "note": ("prompts/32 A.1.3: the build runs on a COMMITTED record before kingston is read; nothing in this "
                     "prep directory is a preregistration of the day"),
            "record": {"path": rel(p(args.record)), "stamp": rec["stamp"], "last_update_date": rec["last_update_date"],
                       "fingerprint": rec["fingerprint"], "n_qubits": len(rec["qubits"]), "n_edges": len(rec["edges"]),
                       "missing_errors": rec["missing_errors"], "status": rec.get("status"), "dt_s": rec["dt_s"],
                       "default_rep_delay_s": rec["default_rep_delay_s"]},
            "diff_against": {"reference": args.diff_against, "reference_fingerprint": ref["fingerprint"],
                             "n_leaves": d["n_leaves"], "families": d["families"],
                             "identical_content": ref["fingerprint"] == rec["fingerprint"]}}
    os.makedirs(p(args.prep), exist_ok=True)
    dump_json(info, p(args.prep, "live.json"))
    print(f"offline record {info['record']['path']} ({rec['fingerprint'][:16]}) -> {rel(p(args.prep, 'live.json'))}")
    return 0


def patch_calibrated(rec, mapping, pattern_edges):
    """P2 (a): every patch qubit has its error / coherence leaves and every pattern edge its cz error."""
    bad = []
    for q in sorted(mapping.values()):
        v = rec["qubits"].get(str(q))
        if v is None:
            bad.append(f"qubit {q} absent")
            continue
        for k in ("measure_error", "sx_error", "x_error", "T1_s", "T2_s"):
            if v.get(k) is None:
                bad.append(f"qubit {q} {k} None")
    for u, w in pattern_edges:
        a, b = mapping[int(u)], mapping[int(w)]
        e = rec["edges"].get(f"{a}-{b}") or rec["edges"].get(f"{b}-{a}")
        if e is None or e.get("cz_error") is None:
            bad.append(f"edge {a}-{b} uncalibrated")
    return bad


def p2_decision(committed_entry, winner, calib_problems):
    """(keep committed?, reasons) of P2."""
    reasons = []
    if calib_problems:
        reasons.append("(a) the committed patch is not fully calibrated: " + "; ".join(calib_problems[:5]))
    if committed_entry is None:
        reasons.append("(a) the committed mapping is not covered by the day's record")
    elif committed_entry["f_dd_off"] < P2_SCORE_FRACTION * winner["f_dd_off"]:
        reasons.append(f"(b) committed f_dd_off {committed_entry['f_dd_off']:.4g} < {P2_SCORE_FRACTION} x the winner's "
                       f"{winner['f_dd_off']:.4g}")
    return (not reasons), reasons


def stage_select(args):
    import gate_S2D_levers as G
    t0 = time.time()
    rec, info = DT.day_record(args.prep)
    row = load_json(KP.ROW_MANIFEST)
    cand, qc = KP.candidate()
    a0 = G.garbage_acceptance(0)
    s = G.embedding_search(qc, rec, a0, survey_set=row["physical_qubits"], top=10 ** 6)
    win = s["best"]
    wmap = {int(k): int(v) for k, v in win["mapping"].items()}
    dsel = load_json(p(DDTEST_PREP, "select.json"))
    cmap = {int(k): int(v) for k, v in dsel["winner_mapping"].items()}
    centry = next((e for e in s["top"] if {int(k): int(v) for k, v in e["mapping"].items()} == cmap), None)
    calib = patch_calibrated(rec, cmap, s["pattern"]["edges"])
    keep, reasons = p2_decision(centry, win, calib)
    used = cmap if keep else wmap
    out = {"stage": "select", "created": now(), "qpu_seconds": 0,
           "rule": ("P2 (prompts/32): run the R1'-pilot embedding search on the day's full record (information); keep the "
                    "committed H0_ddtest patch unless (a) a qubit or edge of it is uncalibrated or (b) its f_dd_off < 0.5 x "
                    "the winner's; in case (a)/(b) the winner is used and patch_reproduced is false"),
           "record_path": info["record"]["path"], "record_fingerprint": rec["fingerprint"],
           "candidate": cand, "candidate_ops": {k: int(v) for k, v in qc.count_ops().items()},
           "garbage_acceptance_B0": a0, "pattern": s["pattern"], "n_embeddings": s["n_embeddings"],
           "n_scored": s["n_scored"], "n_skipped": s["n_skipped"], "winner": win, "top5": s["top"][:5],
           "search_winner_mapping": {str(k): v for k, v in sorted(wmap.items())},
           "committed_source": rel(p(DDTEST_PREP, "select.json")),
           "committed_mapping": {str(k): v for k, v in sorted(cmap.items())},
           "committed_entry": centry, "committed_rank": None if centry is None else centry.get("rank"),
           "committed_calibration_problems": calib,
           "decision": {"keep_committed": keep, "reasons": reasons, "patch_reproduced": keep,
                        "score_ratio_committed_over_winner": (None if centry is None else centry["f_dd_off"] / win["f_dd_off"])},
           "winner_mapping": {str(k): v for k, v in sorted(used.items())},     # the mapping the build uses
           "winner_patch": sorted(used.values()),
           "mapping_reproduced": used == cmap, "pilot_mapping_reproduced": used == cmap,
           "runtime_s": time.time() - t0}
    dump_json(out, p(args.prep, "select.json"))
    print(f"search winner {sorted(wmap.values())} f_dd_off {win['f_dd_off']:.4f}; committed patch "
          f"{sorted(cmap.values())} f_dd_off {None if centry is None else round(centry['f_dd_off'], 4)} (rank "
          f"{None if centry is None else centry.get('rank')} of {s['n_scored']}); keep committed {keep} {reasons} "
          f"({time.time() - t0:.0f} s)")
    return 0


def load_qpy(path):
    from qiskit import qpy
    with gzip.open(path, "rb") as fh:
        return qpy.load(fh)[0]


def reuse_committed(cdir, mans, cid, cell, reproduced):
    """Byte-for-byte reuse of the committed H0_ddtest QPY for T1 / T3 when the rebuilt circuit
    equals it (T0 is handled by `build_coarse(force_reuse=...)`)."""
    man = next(m for m in mans if m["id"] == f"{cid}_{cell}")
    src = p(DDTEST_PREP, "circuits", f"{cid}_{cell}.qpy.gz")
    path = os.path.join(cdir, man["qpy"])
    if cell == "T0":
        return man, man.get("reuse")
    if not reproduced:
        man["reuse"] = {"source": rel(src), "byte_for_byte": False, "note": "patch not reproduced: rebuilt on the new patch"}
        return man, man["reuse"]
    committed = load_qpy(src)
    rebuilt = load_qpy(path)
    if committed == rebuilt:
        shutil.copyfile(src, path)
        man["qpy_gz_sha256"] = sha256_of(path)
        man["qpy_bytes_uncompressed"] = len(gzip.open(path, "rb").read())
        man["reuse"] = {"source": rel(src), "byte_for_byte": True}
    else:
        man["reuse"] = {"source": rel(src), "byte_for_byte": False,
                        "note": "the rebuilt circuit differs from the committed one on the day's record"}
    return man, man["reuse"]


def cell_manifest(t0man, cid, cell, out, par, chk, exd, path, raw, sha, extra):
    man = dict(t0man)
    man.update({
        "id": f"{cid}_{cell}",
        "physical_qubits": sorted({out.find_bit(q).index for i in out.data for q in i.qubits if i.operation.name != "barrier"}),
        "ops": {k: int(v) for k, v in out.count_ops().items()},
        "cz": int(out.count_ops().get("cz", 0)), "depth": int(out.depth()),
        "n_delays": int(out.count_ops().get("delay", 0)),
        "scheduled_duration_s": chk["duration_s"],
        "measurement_consistent": exd["measurement_consistent"],
        "exactness": {k: exd[k] for k in ("max_abs_delta", "leakage", "measurement_consistent", "ok",
                                          "global_phase_source", "global_phase_submitted")},
        "exactness_phase_aligned": True,
        "qpy": os.path.basename(path), "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha, "reuse": None,
        "dd": {"cell": cell, "description": CELL_DESCRIPTION[cell], "pass": par["pass"], "parameters": par["parameters"],
               "pulses_per_physical_qubit": chk["pulses_per_physical_qubit"], "n_pulses": chk["n_pulses"],
               "pulse_cost_nats": chk["pulse_cost_nats"], "null_ratio": chk["null_ratio"],
               "base_circuit_sha256": t0man["qpy_gz_sha256"], "y_translated": 0,
               "n_rz_inserted": chk["n_rz_inserted"],
               "idle_register_delays_removed_after_pass": par.get("idle_register_delays_removed_after_pass", 0),
               "checks": chk, **extra},
    })
    return man


def build_trains(patch, cdir, common, rec, num_qubits):
    from h0_build_circuits import dump_qpy_gz
    mans = []
    for tid, (n, alt) in TRAINS.items():
        qc = pulse_train(patch, n, alt, num_qubits)
        seqs = {str(q): op_sequence(qc, q) for q in patch}
        n_x = {q: s.count("x") for q, s in seqs.items()}
        if any(v != n for v in n_x.values()) or len(set(map(tuple, seqs.values()))) != 1:
            raise SystemExit(f"{tid}: the per-qubit op lists are not the declared train")
        want = []
        for j in range(n):
            want += (["rz(-1pi)", "x", "rz(+1pi)"] if (alt and j % 2 == 1) else ["x"])
        want = want + ["measure"]
        if any(s != want for s in seqs.values()):
            raise SystemExit(f"{tid}: op sequence differs from the declared train")
        raw, sha = dump_qpy_gz(qc, os.path.join(cdir, tid + ".qpy.gz"))
        dur = sum(n * float(rec["qubits"][str(q)]["x_duration_s"]) for q in patch[:1])
        man = dict(common)
        man.update({"id": tid, "kind": PULSE_TRAIN_KIND, "test": "pulse_train", "repetitions": None,
                    "sector": None, "twoB": None, "k": None,
                    "train": {"n_pulses": n, "alternating_signs": alt,
                              "sign_pattern": ("+ - + - ... (every 2nd x wrapped as rz(-pi) x rz(+pi) = -X)" if alt
                                               else "+ + + ... (n identical x)"),
                              "per_qubit_ops": seqs[str(patch[0])], "per_qubit_ops_identical_on_all_qubits": True,
                              "train_duration_s_record": dur, "ideal_outcome": "all 0 (n even)"},
                    "physical_qubits": list(patch), "readout_patch": list(patch), "logical_to_physical": list(patch),
                    "measurement_map_clbit_to_physical": {str(i): int(q) for i, q in enumerate(patch)},
                    "measurement_consistent": True,
                    "ops": {k: int(v) for k, v in qc.count_ops().items()},
                    "record_fingerprint_full": rec["fingerprint"],
                    "qpy": tid + ".qpy.gz", "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha,
                    "kind_note": ("kind idle_test: gate_H0P.load_manifests hands it to h0_submit.py at --shots and "
                                  "h0_qpu_time.estimate times it; no cz, so the preflight computes no f for it")})
        mans.append(man)
        print(f"  {tid}: {man['ops']}")
    return mans


def stage_build(args):
    from h0_backends import backend_from_record
    from h0_build_circuits import dump_qpy_gz
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    t0 = time.time()
    rec, info = DT.day_record(args.prep)
    sel = load_json(p(args.prep, "select.json"))
    if sel["record_fingerprint"] != rec["fingerprint"]:
        raise SystemExit("select.json was made on another record than live.json points at: re-run --stage select (D10)")
    base, binfo = backend_from_record(rec, base=FakeKingston(), strict=True)
    tgt = base.target
    mp = {int(k): int(v) for k, v in sel["winner_mapping"].items()}
    patch = sorted(mp.values())
    reproduced = bool(sel["decision"]["patch_reproduced"])
    cdir = p(args.prep, "circuits")
    os.makedirs(cdir, exist_ok=True)
    stale = os.listdir(cdir)
    if stale and not args.force:
        raise SystemExit(f"{rel(cdir)} is not empty ({len(stale)} files): a rebuild (D10) needs --force")
    for f in stale:
        os.remove(os.path.join(cdir, f))
    common = DT.common_block(rec)
    common["circuit_family"] = common["circuit_family"].replace("prompts/24 P4", "prompts/24 P4 / prompts/32 P3")
    reuse = ({cid: os.path.join(DDTEST_PREP, "circuits", cid + "_T0.qpy.gz") for cid in BASE_IDS}
             if reproduced else None)
    mans = DT.build_coarse(args.prep, rec, base, BASE_IDS, REUSED_CELLS, cdir, common, sel, mp, patch,
                           force_reuse=reuse)
    reuse_log = {}
    for cid in BASE_IDS:
        for cell in REUSED_CELLS:
            _m, r = reuse_committed(cdir, mans, cid, cell, reproduced)
            reuse_log[f"{cid}_{cell}"] = r
    if reproduced and not all((r or {}).get("byte_for_byte") for r in reuse_log.values()):
        bad = [k for k, r in reuse_log.items() if not (r or {}).get("byte_for_byte")]
        dump_json({"stage": "build", "created": now(), "reuse": reuse_log}, p(args.prep, "build_stop.json"))
        print(f"STOP: the patch is reproduced but {bad} are not byte-identical to the H0_ddtest QPYs (P2 / D5)")
        return KP.EXIT_STOP
    # ---- the hot qubits of M4: the two qubits with the most T1 pulses (pooled over both circuits)
    pooled = Counter()
    per_circ_hot = {}
    for cid in BASE_IDS:
        m1 = next(m for m in mans if m["id"] == f"{cid}_T1")
        pooled.update({int(q): int(n) for q, n in m1["dd"]["pulses_per_physical_qubit"].items()})
        per_circ_hot[cid] = hot_qubits(m1["dd"]["pulses_per_physical_qubit"])
    hot = hot_qubits(pooled)
    identities = {}
    new = []
    for cid in BASE_IDS:
        t0man = next(m for m in mans if m["id"] == f"{cid}_T0")
        final = t0man["logical_to_physical"]
        member = {"reference": t0man["reference"], "theta": t0man["theta"]}
        src_phase = t0man["exactness"]["global_phase_source"]
        T0c = load_qpy(os.path.join(cdir, f"{cid}_T0.qpy.gz"))
        T1c = load_qpy(os.path.join(cdir, f"{cid}_T1.qpy.gz"))
        T2c, _ = DT.dd_variant("T2", T0c, rec, tgt)
        M2c, par2 = xx_variant(T0c, rec, tgt)
        M1c, nw1 = alternate_signs(T1c, T0c, rec)
        M3c, nw3 = alternate_signs(M2c, T0c, rec)
        M4c, nrm = strip_pulses_on(T1c, T0c, rec, hot)
        # ---- the P3 identities
        x_T1 = inserted_multiset(T0c, T1c, rec, names=("x",))
        x_M1 = inserted_multiset(T0c, M1c, rec, names=("x",))
        x_M2 = inserted_multiset(T0c, M2c, rec, names=("x",))
        x_M3 = inserted_multiset(T0c, M3c, rec, names=("x",))
        ins_T1 = inserted_multiset(T0c, T1c, rec)
        ins_M4 = inserted_multiset(T0c, M4c, rec)
        want_M4 = Counter({k: v for k, v in ins_T1.items() if k[1] not in set(hot)})
        w_M2 = pulsed_windows(T0c, M2c, rec)
        w_T2 = pulsed_windows(T0c, T2c, rec)
        w_T2c = None
        if reproduced:
            w_T2c = pulsed_windows(T0c, load_qpy(p(DDTEST_PREP, "circuits", f"{cid}_T2.qpy.gz")), rec)
        n_T2 = sum(inserted_multiset(T0c, T2c, rec, names=("x",)).values())
        ident = {
            "M1_x_starts_equal_T1": x_M1 == x_T1, "M1_wrapped": nw1,
            "M3_x_starts_equal_M2": x_M3 == x_M2, "M3_wrapped": nw3,
            "M2_windows_equal_T2_rebuilt": w_M2 == w_T2,
            "M2_windows_equal_T2_committed": (None if w_T2c is None else w_M2 == w_T2c),
            "M2_n_windows": len(w_M2), "T2_n_windows": len(w_T2), "M2_pulses": sum(x_M2.values()),
            "T2_pulses": n_T2, "M2_pulses_equal_half_T2": 2 * sum(x_M2.values()) == n_T2,
            "M4_inserted_equal_T1_minus_hot": ins_M4 == want_M4, "M4_removed": nrm, "hot": hot,
        }
        ident["ok"] = bool(ident["M1_x_starts_equal_T1"] and ident["M3_x_starts_equal_M2"]
                           and ident["M2_windows_equal_T2_rebuilt"] and ident["M2_windows_equal_T2_committed"] is not False
                           and ident["M4_inserted_equal_T1_minus_hot"])
        identities[cid] = ident
        if not ident["ok"]:
            dump_json({"stage": "build", "created": now(), "identities": identities}, p(args.prep, "build_stop.json"))
            raise SystemExit(f"{cid}: a P3 identity fails: {ident}")
        for cell, out, par, extra in (
                ("M1", M1c, {"pass": "alternate_signs(T1, T0)", "parameters": {"rule": "every 2nd inserted x per qubit -> rz(-pi) x rz(+pi)"}},
                 {"derived_from": f"{cid}_T1", "n_wrapped": nw1}),
                ("M2", M2c, par2, {"window_set": "T2's (asserted)", "n_windows": len(w_M2)}),
                ("M3", M3c, {"pass": "alternate_signs(M2, T0)", "parameters": {"rule": "every 2nd inserted x per qubit -> rz(-pi) x rz(+pi)"}},
                 {"derived_from": f"{cid}_M2", "n_wrapped": nw3}),
                ("M4", M4c, {"pass": "strip_pulses_on(T1, T0, hot)", "parameters": {"hot_qubits": hot, "replacement": "delay of the op's duration"}},
                 {"derived_from": f"{cid}_T1", "hot_qubits": hot, "n_removed": nrm})):
            t1 = time.time()
            chk = DT.dd_checks(T0c, out, rec, tgt, final)
            if not chk["ok"]:
                raise SystemExit(f"{cid} {cell}: DD checks failed: { {k: chk[k] for k in ('statevector_max_abs_delta_up_to_phase', 'duration_delta_dt', 'windows_ok', 'basis_ok', 'active_qubits_unchanged')} }")
            exd = DT.dd_exactness(out, final, member, KP.CANDIDATE["order"], src_phase)
            if not exd["ok"]:
                raise SystemExit(f"{cid} {cell}: exactness failed {exd}")
            path = os.path.join(cdir, f"{cid}_{cell}.qpy.gz")
            raw, sha = dump_qpy_gz(out, path)
            man = cell_manifest(t0man, cid, cell, out, par, chk, exd, path, raw, sha, extra)
            new.append(man)
            print(f"  {cid}_{cell}: pulses {chk['n_pulses']} (rz inserted {chk['n_rz_inserted']}), S_DD "
                  f"{chk['pulse_cost_nats']:.4f} (null {chk['null_ratio']:.3f}), dpsi "
                  f"{chk['statevector_max_abs_delta_up_to_phase']:.1e}, |d| {exd['max_abs_delta']:.1e}, dur "
                  f"{chk['duration_s'] * 1e6:.3f} us ({time.time() - t1:.1f} s)", flush=True)
    num_qubits = load_qpy(os.path.join(cdir, f"{BASE_IDS[0]}_T0.qpy.gz")).num_qubits
    trains = build_trains(patch, cdir, common, rec, num_qubits)
    cals = DT.build_calibration_pubs(base, rec, patch, len(patch), cdir, common)
    allm = mans + new + trains + cals
    for m in allm:
        if m.get("dd"):
            m["dd"]["description"] = CELL_DESCRIPTION[m["dd"]["cell"]]
    extra = {"created": now(), "script": "scripts/h0_ddrep_circuits.py", "stage": "build", "qpu_seconds": 0,
             "purpose": ("prompts/32 A.1: seven DD cells (T0, T1, T3 reused; M1 CA+/-, M2 XX, M3 X(-X), M4 CA minus the two "
                         "hottest qubits) on the two signed k = 1 circuits, four pulse-train pubs and the patch's readout pubs"),
             "offline_prototype": bool(info.get("offline_prototype")),
             "common": common, "record": info["record"],
             "base_backend": {k: v for k, v in binfo.items() if k not in ("qubits", "edges")},
             "patch": patch, "winner_mapping": sel["winner_mapping"], "patch_reproduced": reproduced,
             "p2_decision": sel["decision"], "mapping_reproduced": sel["mapping_reproduced"],
             "pilot_mapping_reproduced": sel.get("pilot_mapping_reproduced"),
             "cells": {c: CELL_DESCRIPTION[c] for c in CELLS}, "base_ids": list(BASE_IDS),
             "trains": {k: {"n_pulses": v[0], "alternating_signs": v[1]} for k, v in TRAINS.items()},
             "hot_qubits": hot, "hot_qubits_per_circuit": per_circ_hot,
             "hot_rule": "the two physical qubits with the most inserted T1 pulses (pooled over both circuits; ties -> smaller index)",
             "identities": identities, "reuse": reuse_log, "n_pubs": len(allm), "runtime_s": time.time() - t0}
    index, qubits, edges = DT.write_index(args.prep, allm, extra)
    print(f"wrote {len(allm)} pubs to {rel(cdir)} ({len(qubits)} qubits, {len(edges)} directed edges); patch reproduced "
          f"{reproduced}; hot {hot}; identities ok {all(v['ok'] for v in identities.values())} in {time.time() - t0:.0f} s")
    return 0


def stage_patchcal(args):
    info = DT.live_info(args.prep)
    if not info.get("offline_prototype"):
        return DT.stage_patchcal(args)
    from h0_backends import frozen_qubits_and_edges
    qubits, edges = frozen_qubits_and_edges(p(args.prep))
    prec = load_json(COMMITTED_PATCH_RECORD)
    keys = sorted(tuple(v["target_key"]) for v in prec["edges"].values())
    pairs = sorted({tuple(x) for v in prec["edges"].values() for x in v["directed_pairs_of_the_frozen_set"]})
    if sorted(map(int, prec["qubits"])) != sorted(qubits) or pairs != sorted(map(tuple, edges)):
        raise SystemExit("the committed patch record's qubits / directed pairs are not this prep's frozen set")
    info["patch_record"] = {"path": COMMITTED_PATCH_RECORD, "fingerprint": prec["fingerprint"], "stamp": prec["stamp"],
                            "last_update_date": prec["last_update_date"], "leaves_equal_full_record": True,
                            "n_differences": 0, "missing_errors": prec["missing_errors"],
                            "n_qubits": len(prec["qubits"]), "n_edges": len(keys), "offline_prototype": True}
    dump_json(info, p(args.prep, "live.json"))
    print(f"offline patch record {COMMITTED_PATCH_RECORD} ({prec['fingerprint'][:16]}): frozen set identical")
    return 0


STAGES = {"account": stage_account, "record": stage_record, "select": stage_select,
          "build": stage_build, "patchcal": stage_patchcal}


def main():
    ap = DT.build_parser(default_prep=PREP, default_diff=COMMITTED_FULL_RECORD)
    ap.set_defaults(min_remaining=MIN_REMAINING_S)
    ap.add_argument("--record", default=None, help="record: use this COMMITTED full record (offline prototype, A.1.3)")
    args = ap.parse_args()
    return STAGES[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
