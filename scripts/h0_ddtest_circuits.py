#!/usr/bin/env python3
"""
Stage T of prompts/24 -- live reads, patch selection and the four-cell dynamical-decoupling
A/B circuit set on ibm_kingston (`data/hardware/H0_ddtest_prep/`).  Zero QPU seconds: every
stage is a metadata read of the live target or a local transpilation.

The four cells (planner decision P4, parameters FIXED, never tuned on data) are applied to the
pilot's two k = 1 circuits (`B0_ref06_k1`, `B1_ref07_k1`), each ALAP-scheduled with explicit
delays exactly as `scripts/h0_kpilot_circuits.py --stage build` makes them:

  T0  no DD (the pilot's configuration; the same-job, same-patch control)
  T1  qiskit ALAPScheduleAnalysis(target) + ContextAwareDynamicalDecoupling(target,
      min_duration=128, skip_reset_qubits=True, pulse_alignment=<target's>)   (arXiv:2403.06852)
  T2  qiskit_ibm_runtime ALAPScheduleAnalysis(durations) + PadDynamicalDecoupling(durations,
      [X, Y, X, Y], sequence_min_length_ratios=[2.0], pulse_alignment=<target's>), then
      Y -> rz(-pi/2) x rz(pi/2) (= Y exactly) so the circuit is in kingston's basis
  T3  as T2 with sequence_min_length_ratios=[8.0] (windows >= 1.024 us)

Every DD circuit is verified IN MEMORY before it is dumped (checks (i)-(v) of T.B2):
(i) the 12-qubit statevector equals the base circuit's up to a global phase to 1e-10;
(ii) the scheduled duration equals the base's to 1 dt; (iii) every non-delay operation of the
base keeps its start time, and no inserted pulse sits in a qubit's leading window (before its
first gate) or after its measurement; (iv) the op multiset is recorded and the basis is
{rz, sx, x, cz, delay, measure, barrier}; (v) per-qubit pulses, S_DD on the day's record and
the null ratio exp(-S_DD).  `dd_variant` and `dd_checks` are imported by Stage R
(`scripts/h0_2x2_circuits.py`), so both stages insert the same pulses by the same code path.

Stages (all `--prep`-scoped; default `data/hardware/H0_ddtest_prep`):
  account   instance, plan, usage, kingston status -> account_check_<stamp>.json (exit 3 below
            --min-remaining seconds or if kingston is not operational)
  record    `h0_device_survey.full_device_record` -> ibm_kingston_full_<stamp>.json, its
            `calibration_diff` against --diff-against (information); live.json
  select    rule R1'-pilot (prompts/21): the exhaustive `embedding_search` of the L1_seed
            candidate on the day's full record, run once
  build     the 8 coarse pubs (2 bases x 4 cells) + the patch's all-0 / all-1 readout pubs
  patchcal  the patch-scoped D9 record, every leaf asserted equal to the full record's
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

import h0_kpilot_circuits as KP  # noqa: E402  (import only; the pilot script is not changed)

ROOT = KP.ROOT
PREP = os.path.join("data", "hardware", "H0_ddtest_prep")
PILOT_PREP = os.path.join("data", "hardware", "H0_kpilot_prep")
PILOT_FULL_RECORD = os.path.join(PILOT_PREP, "ibm_kingston_full_20261002T1627Z.json")
DEVICE = "ibm_kingston"
BASE_IDS = ("B0_ref06_k1", "B1_ref07_k1")
CELLS = ("T0", "T1", "T2", "T3")
# ---- P4: the pass parameters, fixed before any data
CA_MIN_DURATION = 128                 # dt (512 ns on kingston)
XY4_RATIO = {"T2": 2.0, "T3": 8.0}
CELL_DESCRIPTION = {
    "T0": "baseline: no DD (the pilot's configuration)",
    "T1": "context-aware staggered X-DD (qiskit ContextAwareDynamicalDecoupling, min_duration 128 dt)",
    "T2": "XY4 in every window >= 2 x the sequence (qiskit_ibm_runtime PadDynamicalDecoupling, ratio 2.0)",
    "T3": "XY4 in windows >= 8 x the sequence only (ratio 8.0, >= 1.024 us)",
}
BASIS_ALLOWED = ("rz", "sx", "x", "cz", "delay", "measure", "barrier")
PULSE_OPS = ("x", "y")
SV_TOL = 1e-10
MIN_REMAINING_S = 275.0               # T.A1: STOP below 275 s

p, rel, load_json, dump_json, sha256_of, utc_stamp, now = (KP.p, KP.rel, KP.load_json, KP.dump_json,
                                                           KP.sha256_of, KP.utc_stamp, KP.now)


def live_info(prep):
    path = p(prep, "live.json")
    if not os.path.exists(path):
        raise SystemExit(f"{rel(path)} missing: run --stage record first")
    return load_json(path)


def day_record(prep):
    info = live_info(prep)
    return load_json(info["record"]["path"]), info


# --------------------------------------------------------------------------- account / record
def stage_account(args):
    out = KP.account_snapshot()
    path = args.out or p(args.prep, f"account_check_{utc_stamp()}.json")
    dump_json(out, path)
    u = out.get("usage") or {}
    b = out.get("backend") or {}
    print(f"wrote {rel(path)}: instances {out.get('instances')}; usage {u.get('usage_consumed_seconds')} s "
          f"of {u.get('usage_limit_seconds')} s (remaining {u.get('usage_remaining_seconds')} s, period "
          f"{u.get('usage_period')}); {DEVICE} operational {b.get('operational')}, pending {b.get('pending_jobs')}")
    stop = []
    if not b.get("operational"):
        stop.append(f"{DEVICE} is not reachable or not operational")
    rem = u.get("usage_remaining_seconds")
    if rem is None or float(rem) < float(args.min_remaining):
        stop.append(f"usage remaining {rem} s < {float(args.min_remaining):.0f} s")
    if stop and not args.after:
        print("STOP: " + "; ".join(stop))
        return KP.EXIT_STOP
    return 0


def stage_record(args):
    import h0_device_survey as ds
    from h0_backends import calibration_diff
    t0 = time.time()
    prep = args.prep
    rec = ds.full_device_record(DEVICE)
    stamp = rec["stamp"]
    rpath = p(prep, f"{DEVICE}_full_{stamp}.json")
    if os.path.exists(rpath) and load_json(rpath)["fingerprint"] != rec["fingerprint"]:
        rpath = p(prep, f"{DEVICE}_full_{stamp}_{rec['fingerprint'][:8]}.json")
    if not os.path.exists(rpath):
        dump_json(rec, rpath)
    ref = load_json(args.diff_against)
    d = calibration_diff(ref, rec)
    info = {"stage": "record", "created": now(), "qpu_seconds": 0,
            "record": {"path": rel(rpath), "stamp": stamp, "last_update_date": rec["last_update_date"],
                       "fingerprint": rec["fingerprint"], "n_qubits": len(rec["qubits"]),
                       "n_edges": len(rec["edges"]), "missing_errors": rec["missing_errors"],
                       "status": rec.get("status"), "dt_s": rec["dt_s"],
                       "default_rep_delay_s": rec["default_rep_delay_s"]},
            "diff_against": {"reference": args.diff_against, "reference_fingerprint": ref["fingerprint"],
                             "n_leaves": d["n_leaves"], "families": d["families"],
                             "max_ratio": d["max_ratio"], "min_ratio": d["min_ratio"],
                             "identical_content": ref["fingerprint"] == rec["fingerprint"]},
            "runtime_s": time.time() - t0}
    old = p(prep, "live.json")
    if os.path.exists(old):
        prev = load_json(old)
        if prev.get("patch_record"):
            info["previous_patch_record"] = prev["patch_record"]
    dump_json(info, old)
    with open(p(prep, "records_log.jsonl"), "a") as fh:
        fh.write(json.dumps({"when": now(), "path": rel(rpath), "fingerprint": rec["fingerprint"],
                             "last_update_date": rec["last_update_date"]}) + "\n")
    print(f"full record {rel(rpath)}: fingerprint {rec['fingerprint'][:16]}, {rec['last_update_date']}, "
          f"status {rec.get('status')}; vs {args.diff_against}: {d['n_leaves']} leaves moved over "
          f"{d['families']} (identical content: {ref['fingerprint'] == rec['fingerprint']})")
    if not (rec.get("status") or {}).get("operational"):
        print("STOP: the device is not operational")
        return KP.EXIT_STOP
    return 0


# --------------------------------------------------------------------------- R1'-pilot
def stage_select(args):
    import gate_S2D_levers as G
    t0 = time.time()
    rec, info = day_record(args.prep)
    row = load_json(KP.ROW_MANIFEST)
    cand, qc = KP.candidate()
    a0 = G.garbage_acceptance(0)
    s = G.embedding_search(qc, rec, a0, survey_set=row["physical_qubits"], top=5)
    mp = {int(k): int(v) for k, v in s["best"]["mapping"].items()}
    committed = {int(k): int(v) for k, v in row["mapping_transpiled_to_kingston"].items()}
    pilot = load_json(p(PILOT_PREP, "select.json"))
    pilot_map = {int(k): int(v) for k, v in pilot["winner_mapping"].items()}
    out = {"stage": "select", "created": now(),
           "rule": ("R1'-pilot (prompts/21, unchanged by prompts/24 P3): exhaustive embedding search of the "
                    "L1_seed candidate on the day's full record, run once; the winner is the patch"),
           "record_path": info["record"]["path"], "record_fingerprint": rec["fingerprint"],
           "candidate": cand, "candidate_ops": {k: int(v) for k, v in qc.count_ops().items()},
           "garbage_acceptance_B0": a0, "pattern": s["pattern"], "n_embeddings": s["n_embeddings"],
           "n_scored": s["n_scored"], "n_skipped": s["n_skipped"], "winner": s["best"], "top5": s["top"],
           "winner_mapping": {str(k): v for k, v in sorted(mp.items())},
           "winner_patch": sorted(mp.values()),
           "committed_row": KP.ROW_MANIFEST,
           "committed_mapping": {str(k): v for k, v in sorted(committed.items())},
           "mapping_reproduced": mp == committed,
           "pilot_mapping_reproduced": mp == pilot_map,
           "on_survey_patch": s["on_survey_patch"], "runtime_s": time.time() - t0}
    dump_json(out, p(args.prep, "select.json"))
    print(f"winner {sorted(mp.values())} f_dd_off {s['best']['f_dd_off']:.4f} T {s['best']['T_s'] * 1e6:.2f} us "
          f"({s['n_scored']} of {s['n_embeddings']} scored); committed L1_seed_alap mapping reproduced "
          f"{mp == committed}; pilot's mapping reproduced {mp == pilot_map} ({time.time() - t0:.0f} s)")
    return 0


# --------------------------------------------------------------------------- DD insertion
def record_durations(rec):
    """InstructionDurations from a calibration record, as `h0_diag_circuits.dd_padding_check`
    builds them (y carries the x pulse's duration; rz is virtual)."""
    from qiskit.transpiler import InstructionDurations
    entries = []
    for q, v in rec["qubits"].items():
        q = int(q)
        entries += [("sx", [q], v["sx_duration_s"], "s"), ("x", [q], v["x_duration_s"], "s"),
                    ("y", [q], v["x_duration_s"], "s"), ("rz", [q], 0.0, "s"),
                    ("measure", [q], v["measure_duration_s"], "s")]
    for v in rec["edges"].values():
        a, b = v["target_key"]
        entries.append(("cz", [a, b], v["cz_duration_s"], "s"))
    return InstructionDurations(entries, dt=rec["dt_s"])


def translate_y(qc):
    """Y -> rz(-pi/2) x rz(pi/2) (matrix Rz(pi/2) X Rz(-pi/2) = Y exactly, no phase); rz is
    virtual (zero duration), so the schedule is unchanged."""
    from qiskit.circuit.library import RZGate, XGate
    out = qc.copy_empty_like()
    n = 0
    for inst in qc.data:
        if inst.operation.name == "y":
            q = inst.qubits
            out.append(RZGate(-math.pi / 2), q)
            out.append(XGate(), q)
            out.append(RZGate(math.pi / 2), q)
            n += 1
        else:
            out.append(inst)
    return out, n


def dd_variant(cell, base_sched, rec, target):
    """(circuit, parameters) of one P4 cell applied to an ALAP circuit with explicit delays.

    `rec` is the day's record (durations of the runtime passes), `target` the record's
    backend target (the context-aware pass).  T0 returns the base circuit unchanged."""
    from qiskit.circuit.library import XGate, YGate
    from qiskit.transpiler import PassManager
    align = int(getattr(target, "pulse_alignment", 1) or 1)
    if cell == "T0":
        return base_sched, {"pass": None, "parameters": {}}
    if cell == "T1":
        from qiskit.transpiler.passes import ALAPScheduleAnalysis as QALAP
        from qiskit.transpiler.passes import ContextAwareDynamicalDecoupling
        pm = PassManager([QALAP(target=target),
                          ContextAwareDynamicalDecoupling(target=target, min_duration=CA_MIN_DURATION,
                                                          skip_reset_qubits=True, pulse_alignment=align)])
        out = pm.run(base_sched)
        par = {"pass": "qiskit.transpiler.passes.ALAPScheduleAnalysis(target) + "
                       "ContextAwareDynamicalDecoupling(target, ...)",
               "parameters": {"min_duration_dt": CA_MIN_DURATION, "skip_reset_qubits": True,
                              "pulse_alignment": align}, "y_translated": 0}
    elif cell in XY4_RATIO:
        from qiskit_ibm_runtime.transpiler.passes.scheduling import (ALAPScheduleAnalysis,
                                                                     PadDynamicalDecoupling)
        dur = record_durations(rec)
        pm = PassManager([ALAPScheduleAnalysis(durations=dur),
                          PadDynamicalDecoupling(durations=dur, dd_sequences=[XGate(), YGate(), XGate(), YGate()],
                                                 sequence_min_length_ratios=[XY4_RATIO[cell]],
                                                 pulse_alignment=align)])
        out, ny = translate_y(pm.run(base_sched))
        par = {"pass": "qiskit_ibm_runtime.transpiler.passes.scheduling.ALAPScheduleAnalysis(durations) + "
                       "PadDynamicalDecoupling(durations, [X, Y, X, Y], ...); Y -> rz(-pi/2) x rz(pi/2)",
               "parameters": {"sequence": "XY4", "sequence_min_length_ratios": [XY4_RATIO[cell]],
                              "pulse_alignment": align, "skip_reset_qubits": True,
                              "durations_from": rec.get("stamp")},
               "y_translated": ny}
    else:
        raise SystemExit(f"unknown cell {cell}")
    out, nrem = KP.strip_register_delays(out)
    par["idle_register_delays_removed_after_pass"] = nrem
    return out, par


def op_duration_dt(inst, circ, rec, dt):
    nm = inst.operation.name
    qs = [circ.find_bit(q).index for q in inst.qubits]
    if nm == "delay":
        d = inst.operation.duration
        unit = getattr(inst.operation, "unit", "dt")
        return int(d) if unit == "dt" else int(round(float(d) / dt))
    if nm in ("rz", "barrier"):
        return 0
    if nm in ("sx", "x", "y"):
        return int(round(float(rec["qubits"][str(qs[0])]["x_duration_s" if nm != "sx" else "sx_duration_s"]) / dt))
    if nm == "measure":
        return int(round(float(rec["qubits"][str(qs[0])]["measure_duration_s"]) / dt))
    if nm == "cz":
        a, b = sorted(qs)
        e = rec["edges"].get(f"{a}-{b}") or rec["edges"].get(f"{b}-{a}")
        if e is None:
            raise SystemExit(f"no cz entry for {qs} in the record")
        return int(round(float(e["cz_duration_s"]) / dt))
    raise SystemExit(f"no duration rule for {nm}")


def timeline(circ, rec):
    """Per-qubit start times (dt) of every operation of a delay-padded circuit.

    Returns (ops, end, n_unaligned): ops = [(name, qubits tuple, start)] of the non-delay,
    non-barrier operations; end = {qubit: end time}; n_unaligned counts multi-qubit gates whose
    qubits were not all free at the same time (0 for a fully padded schedule)."""
    dt = float(rec["dt_s"])
    t = {}
    ops = []
    unaligned = 0
    for inst in circ.data:
        nm = inst.operation.name
        qs = tuple(circ.find_bit(q).index for q in inst.qubits)
        if nm == "barrier":
            continue
        starts = [t.get(q, 0) for q in qs]
        st = max(starts)
        if len(set(starts)) > 1:
            unaligned += 1
        d = op_duration_dt(inst, circ, rec, dt)
        for q in qs:
            t[q] = st + d
        if nm != "delay":
            ops.append((nm, qs, st, d))
    return ops, t, unaligned


def in_basis(ops):
    """The circuit's op names are within kingston's basis plus delay / measure / barrier."""
    return set(ops) <= set(BASIS_ALLOWED)


def window_violations(base, out, rec):
    """Check (iii) of T.B2 as a pure function of two delay-padded circuits and a record.

    Every non-delay operation of `base` must appear in `out` with the same start time; the
    inserted operations must be single-qubit x / rz, none may start before the end of the
    qubit's first base gate (its leading window, where it is still in |0>) and none may end
    after the start of its measurement."""
    ops0, _e0, un0 = timeline(base, rec)
    ops1, _e1, un1 = timeline(out, rec)
    c0 = Counter((nm, qs, st) for nm, qs, st, _d in ops0)
    c1 = Counter((nm, qs, st) for nm, qs, st, _d in ops1)
    missing = c0 - c1
    inserted = c1 - c0
    first_end, meas_start = {}, {}
    for nm, qs, st, d in ops0:
        for q in qs:
            if nm != "measure" and q not in first_end:
                first_end[q] = st + d
            if nm == "measure":
                meas_start[q] = st
    durs = {(nm, qs, st): d for nm, qs, st, d in ops1}
    lead, trail, bad_kind, pulses, kinds = Counter(), Counter(), Counter(), Counter(), Counter()
    for (nm, qs, st), n in inserted.items():
        kinds[nm] += n
        q = qs[0]
        if nm not in ("x", "rz") or len(qs) != 1:
            bad_kind[nm] += n
            continue
        if nm == "x":
            pulses[q] += n
        if q not in first_end or st < first_end[q]:
            lead[q] += n
        if q in meas_start and st + durs[(nm, qs, st)] > meas_start[q]:
            trail[q] += n
    return {"lead": lead, "trail": trail, "bad_kind": bad_kind, "missing": int(sum(missing.values())),
            "unaligned": (un0, un1), "pulses": pulses, "inserted": kinds}


def dd_checks(base, out, rec, target, final):
    """Checks (i)-(v) of T.B2 on one DD circuit against its base (both in memory)."""
    from h0_qpu_time import circuit_duration_s
    dt = float(rec["dt_s"])
    # (i) statevector up to a global phase
    psi0 = KP.logical_state_explicit(base, final)
    psi = KP.logical_state_explicit(out, final)
    ov = complex(np.vdot(psi0, psi))
    dpsi = float(np.max(np.abs(psi * np.exp(-1j * np.angle(ov)) - psi0)))
    # (ii) duration
    d0 = circuit_duration_s(base, target.durations(), target)
    d1 = circuit_duration_s(out, target.durations(), target)
    # (iii) timeline: base ops keep their starts; inserted pulses inside [first gate end, measure start]
    win = window_violations(base, out, rec)
    lead, trail, bad_kind, missing = win["lead"], win["trail"], win["bad_kind"], win["missing"]
    un0, un1 = win["unaligned"]
    per_q_pulses = win["pulses"]
    inserted = win["inserted"]
    # (iv) op multiset / basis
    ops_after = {k: int(v) for k, v in out.count_ops().items()}
    basis_ok = in_basis(ops_after)
    # (v) pulse cost on the record
    s_dd = float(sum(n * float(rec["qubits"][str(q)]["x_error"]) for q, n in per_q_pulses.items()))
    active0 = sorted({base.find_bit(q).index for i in base.data for q in i.qubits if i.operation.name != "barrier"})
    active1 = sorted({out.find_bit(q).index for i in out.data for q in i.qubits if i.operation.name != "barrier"})
    res = {
        "statevector_max_abs_delta_up_to_phase": dpsi, "statevector_overlap_abs": abs(ov),
        "statevector_ok": dpsi < SV_TOL,
        "duration_base_s": d0, "duration_s": d1, "duration_delta_dt": abs(d1 - d0) / dt,
        "duration_ok": abs(d1 - d0) <= dt * (1 + 1e-9),
        "base_ops_moved_or_missing": int(missing),
        "unaligned_multiqubit_gates": [un0, un1],
        "inserted_non_pulse_ops": dict(bad_kind),
        "pulses_in_leading_window": {str(k): v for k, v in sorted(lead.items())},
        "pulses_after_measure": {str(k): v for k, v in sorted(trail.items())},
        "windows_ok": (not lead and not trail and not bad_kind and not missing and un0 == 0 and un1 == 0),
        "ops": ops_after, "basis_ok": basis_ok,
        "active_qubits_unchanged": active0 == active1,
        "pulses_per_physical_qubit": {str(k): int(v) for k, v in sorted(per_q_pulses.items())},
        "n_pulses": int(sum(per_q_pulses.values())),
        "n_rz_inserted": int(inserted.get("rz", 0)),
        "pulse_cost_nats": s_dd, "null_ratio": math.exp(-s_dd),
        "pulse_cost_rule": "sum over inserted x pulses (a translated y is one x pulse) of the qubit's x_error on the day's record",
    }
    res["ok"] = bool(res["statevector_ok"] and res["duration_ok"] and res["windows_ok"] and basis_ok
                     and res["active_qubits_unchanged"])
    return res


def dd_exactness(out, final, member, order, src_phase):
    """C4 on a DD circuit: the base's exactness with the global phase aligned to the exact
    state (DD inserts identities up to a global phase; the phase is unobservable)."""
    import gate_S2D_levers as G
    from skqd.reference_sim import CodewordEmbedding
    fx = G.factory()
    emb = CodewordEmbedding(fx["M"])
    psi = KP.logical_state_explicit(out, final, 0.0)
    exact = G.exact_state(order, member["reference"], member["theta"])
    proj = emb.project(psi)
    ov = complex(np.vdot(exact, proj))
    proj_al = proj * np.exp(-1j * np.angle(ov))
    dev = float(np.max(np.abs(proj_al - exact)))
    leak = float(emb.leakage(psi))
    mm = KP.measurement_map(out)
    cons = len(mm) == len(final) and all(mm.get(i) == final[i] for i in range(len(final)))
    return {"max_abs_delta": dev, "leakage": leak, "measurement_consistent": bool(cons),
            "phase_aligned": True, "global_phase_source": float(src_phase),
            "global_phase_submitted": float(out.global_phase),
            "ok": bool(dev < KP.AMP_TOL and leak < KP.LEAK_TOL and cons)}


# --------------------------------------------------------------------------- build
def base_manifest(common, cid, c, x, final, sched, sinfo, ex, sch_unsched, dsch, d_sched, fg, f1, d, rec):
    man = dict(common)
    man.update({
        "kind": "coarse_step", "test": None, "sector": c["sector"], "twoB": int(c["twoB"]),
        "reference": int(c["reference"]), "k": int(c["k"]), "repetitions": 1,
        "dt": float(c["dt"]), "theta": float(c["theta"]),
        "order": KP.CANDIDATE["order"], "seed": KP.CANDIDATE["seed"],
        "placement": x["placement"],
        "mapping_transpiled_to_kingston": {str(k): int(v) for k, v in sorted(x["mapping"].items())},
        "readout_patch": sorted(final), "logical_to_physical": final,
        "measurement_map_clbit_to_physical": {str(k): v for k, v in sorted(KP.measurement_map(sched).items())},
        "schedule": "alap", "schedule_info": sinfo,
        "T_s": sch_unsched["T_s"], "T_total_s": sch_unsched["T_total_s"],
        "base_scheduled_duration_s": d_sched,
        "leading_delay_s": {str(k): v for k, v in sorted(dsch["leading_s"].items())},
        "f_gates_record": fg, "f_including_1q_errors_record": f1,
        "p_reference": d["p_reference"], "dim": d["dim"], "sector_mass": d["sector_mass"],
        "record_fingerprint_full": rec["fingerprint"],
        "source_qpy": x["source_qpy"], "source_qpy_sha256": x["source_qpy_sha256"],
        "family_member": cid,
    })
    return man


def build_coarse(prep, rec, base, ids, cells, cdir, common, sel, mp, patch, log=print, force_reuse=None,
                 id_suffix=True):
    """Place, schedule, verify and dump the coarse circuits `ids` x `cells` (Stage T and R).

    Returns the list of manifests.  `force_reuse` = {id: committed scheduled QPY path} whose
    bytes are reused when the rebuilt T0 circuit equals the committed one."""
    import gate_S2D_levers as G
    from h0_build_circuits import dump_qpy_gz
    from h0_qpu_time import circuit_duration_s
    from qiskit import qpy
    from skqd import idle
    from skqd.hardware import transpiled_layout
    tgt = base.target
    fx = G.factory()
    n = fx["n"]
    cand, cand_qc = KP.candidate()
    row_pattern = sorted(tuple(sorted(int(x) for x in e)) for e in G.interaction_graph_2q(cand_qc)[1])
    placed = place_members(rec, mp, row_pattern, patch, ids)
    manifests = []
    for cid in ids:
        x = placed[cid]
        c = x["member"]
        rc = G.relabelled(x["tq"], x["mapping"])
        lay0 = transpiled_layout(x["tq"], n)
        final = [int(x["mapping"].get(int(q), int(q))) for q in lay0["logical_to_physical"]]
        if sorted(final) != list(patch):
            raise SystemExit(f"{cid}: logical qubits land on {sorted(final)}, not the patch {list(patch)}")
        sched_full, sinfo = G.scheduled(rc, base, "alap")
        sched, n_removed = KP.strip_register_delays(sched_full)
        sinfo["idle_register_delays_removed"] = n_removed
        ex = KP.coarse_exactness(sched, final, KP.CANDIDATE["order"], c["reference"], c["theta"],
                                 global_phase=x["tq"].global_phase)
        ex["global_phase_source"] = float(x["tq"].global_phase)
        ex["global_phase_submitted"] = float(sched.global_phase)
        if not ex["ok"]:
            raise SystemExit(f"{cid}: exactness failed {ex}")
        sch_unsched = idle.schedule_asap(rc, rec)
        dsch = G.delay_schedule(sched, rec, include_leading=False)
        d_sched = circuit_duration_s(sched, tgt.durations(), tgt)
        if abs(d_sched - sch_unsched["T_total_s"]) > 1e-12:
            raise SystemExit(f"{cid}: ALAP duration {d_sched} != unscheduled T_total {sch_unsched['T_total_s']}")
        fg, _n2, f1 = G.f_gates_on_record(rc, rec)
        d = G.ideal_distribution(KP.CANDIDATE["order"], c["twoB"], c["reference"], c["theta"])
        bman = base_manifest(common, cid, c, x, final, sched, sinfo, ex, sch_unsched, dsch, d_sched, fg, f1, d, rec)
        base_sha = None
        for cell in cells:
            t1 = time.time()
            out, par = dd_variant(cell, sched, rec, tgt)
            chk = dd_checks(sched, out, rec, tgt, final) if cell != "T0" else None
            if chk is not None and not chk["ok"]:
                raise SystemExit(f"{cid} {cell}: DD checks failed: "
                                 f"{ {k: chk[k] for k in ('statevector_max_abs_delta_up_to_phase', 'duration_delta_dt', 'windows_ok', 'basis_ok', 'active_qubits_unchanged', 'pulses_in_leading_window', 'pulses_after_measure', 'base_ops_moved_or_missing', 'inserted_non_pulse_ops')} }")
            exd = ex if cell == "T0" else dd_exactness(out, final, c, KP.CANDIDATE["order"], x["tq"].global_phase)
            if not exd["ok"]:
                raise SystemExit(f"{cid} {cell}: exactness failed {exd}")
            vid = f"{cid}_{cell}" if id_suffix else cid
            name = vid + ".qpy.gz"
            path = os.path.join(cdir, name)
            reuse = None
            if cell == "T0" and force_reuse and cid in force_reuse:
                with gzip.open(p(force_reuse[cid]), "rb") as fh:
                    committed = qpy.load(fh)[0]
                if committed == out:
                    shutil.copyfile(p(force_reuse[cid]), path)
                    raw = len(gzip.open(path, "rb").read())
                    sha = sha256_of(path)
                    reuse = {"source": force_reuse[cid], "byte_for_byte": True}
                else:
                    reuse = {"source": force_reuse[cid], "byte_for_byte": False,
                             "note": "the rebuilt circuit differs from the committed one: rebuilt bytes used"}
            if reuse is None or not reuse["byte_for_byte"]:
                raw, sha = dump_qpy_gz(out, path)
            if cell == "T0":
                base_sha = sha
            man = dict(bman)
            man.update({
                "id": vid, "physical_qubits": sorted({out.find_bit(q).index for i in out.data for q in i.qubits
                                                      if i.operation.name != "barrier"}),
                "ops": {k: int(v) for k, v in out.count_ops().items()},
                "cz": int(out.count_ops().get("cz", 0)), "depth": int(out.depth()),
                "n_delays": int(out.count_ops().get("delay", 0)),
                "scheduled_duration_s": (d_sched if chk is None else chk["duration_s"]),
                "measurement_consistent": exd["measurement_consistent"],
                "exactness": {k: exd[k] for k in ("max_abs_delta", "leakage", "measurement_consistent", "ok",
                                                  "global_phase_source", "global_phase_submitted")},
                "exactness_phase_aligned": cell != "T0",
                "qpy": name, "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha,
                "reuse": reuse,
                "dd": {"cell": cell, "description": CELL_DESCRIPTION[cell], "pass": par["pass"],
                       "parameters": par["parameters"],
                       "pulses_per_physical_qubit": ({} if chk is None else chk["pulses_per_physical_qubit"]),
                       "n_pulses": 0 if chk is None else chk["n_pulses"],
                       "pulse_cost_nats": 0.0 if chk is None else chk["pulse_cost_nats"],
                       "null_ratio": 1.0 if chk is None else chk["null_ratio"],
                       "base_circuit_sha256": base_sha,
                       "y_translated": par.get("y_translated", 0),
                       "idle_register_delays_removed_after_pass": par.get("idle_register_delays_removed_after_pass", 0),
                       "checks": chk},
            })
            manifests.append(man)
            print(f"  {vid}: cz {man['cz']}, delays {man['n_delays']}, pulses {man['dd']['n_pulses']}, "
                f"S_DD {man['dd']['pulse_cost_nats']:.4f} (null {man['dd']['null_ratio']:.3f}), "
                f"|d| {exd['max_abs_delta']:.1e}, leak {exd['leakage']:.1e}"
                + ("" if chk is None else f", dpsi {chk['statevector_max_abs_delta_up_to_phase']:.1e}, "
                   f"dur {chk['duration_s'] * 1e6:.3f} us") + (f", reused {reuse}" if reuse else "")
                + f" ({time.time() - t1:.1f} s)", flush=True)
    return manifests


def place_members(rec, mp, row_pattern, patch, ids):
    """`h0_kpilot_circuits.place_family` for any members of the signed family (the winner's
    mapping for an identical pattern, else the best embedding onto the SAME qubit set)."""
    import gate_S2D_levers as G
    from qiskit import qpy
    fam = load_json(p("data", "S2D_levers", "family.json"))["families"][KP.FAMILY_TAG]
    by_id = {c["id"]: c for c in fam["circuits"]}
    a = {0: G.garbage_acceptance(0), 2: G.garbage_acceptance(2)}
    out = {}
    for cid in ids:
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
                raise SystemExit(f"{cid}: no embedding onto the patch {sorted(patch)} (STOP)")
            mapping, how = G.mapping_of(same[0]), "best embedding onto the patch's qubit set"
        out[cid] = {"member": c, "tq": tq, "mapping": mapping, "placement": how,
                    "source_qpy": rel(qpath), "source_qpy_sha256": sha256_of(qpath)}
    return out


def build_calibration_pubs(base, rec, patch, n, cdir, common, log=print):
    """The all-0 / all-1 readout pubs of the patch, exactly as the pilot builds them."""
    from h0_build_circuits import dump_qpy_gz
    from qiskit import QuantumCircuit, transpile
    from skqd.hardware import logical_statevector, transpiled_layout
    mans = []
    for name_, bits in (("all0", (0,) * n), ("all1", (1,) * n)):
        cid = f"cal_patch_{name_}"
        qc = QuantumCircuit(n, n)
        for q, b in enumerate(bits):
            if b:
                qc.x(q)
        qc.barrier()
        qc.measure(range(n), range(n))
        tq = transpile(qc, backend=base, initial_layout=list(patch), optimization_level=1,
                       seed_transpiler=KP.SEED_TRANSPILER)
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
                    "physical_qubits": lay["active_physical"], "readout_patch": sorted(lay["logical_to_physical"]),
                    "logical_to_physical": lay["logical_to_physical"],
                    "measurement_map_clbit_to_physical": lay["measurement_map"],
                    "measurement_consistent": lay["measurement_consistent"],
                    "transpiler": {"optimization_level": 1, "seed_transpiler": KP.SEED_TRANSPILER,
                                   "initial_layout": list(patch)},
                    "ops": {kk: int(v) for kk, v in tq.count_ops().items()},
                    "record_fingerprint_full": rec["fingerprint"],
                    "qpy": cid + ".qpy.gz", "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha})
        mans.append(man)
        log(f"  {cid}: {man['ops']}")
    return mans


def write_index(prep, manifests, extra):
    from qiskit import qpy
    cdir = p(prep, "circuits")
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
    index = dict(extra)
    index.update({
        "frozen_set": {"qubits": sorted(qubits), "edges": sorted(map(list, edges)), "n_edges": len(edges)},
        "n_circuits": len([m for m in manifests if m["kind"] != "readout_calibration"]),
        "n_calibration_circuits": len([m for m in manifests if m["kind"] == "readout_calibration"]),
        "circuits": [{k: m.get(k) for k in ("id", "kind", "sector", "k", "physical_qubits", "logical_to_physical",
                                            "ops", "qpy", "qpy_gz_sha256", "T_s")} | {"dd_cell": (m.get("dd") or {}).get("cell")}
                     for m in manifests]})
    dump_json(index, p(prep, "index.json"))
    return index, qubits, edges


def common_block(rec):
    index_common = dict(load_json(p("data", "hardware", "H0_prep", "index.json"))["common"])
    common = dict(index_common)
    common.update({"backend": "FakeKingston", "backend_qubits": 156, "n_logical_qubits": 12,
                   "backend_calibration_last_update": rec["last_update_date"],
                   "transpiler": {"note": "per circuit (see its manifest)"},
                   "circuit_family": ("exact structured circuits, signed default term order, transpiled at "
                                      f"seed 2 (gate S2D_levers L1_seed / family {KP.FAMILY_TAG}), relabelled onto "
                                      "the day's patch and scheduled ALAP with explicit delays; client-side DD "
                                      "(prompts/24 P4) inserted into the explicit delays where the cell says so")})
    return common


def prepare_build(prep, force):
    import gate_S2D_levers as G
    from h0_backends import backend_from_record
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    rec, info = day_record(prep)
    sel = load_json(p(prep, "select.json"))
    if sel["record_fingerprint"] != rec["fingerprint"]:
        raise SystemExit("select.json was made on another record than live.json points at: re-run --stage select (D10)")
    base, binfo = backend_from_record(rec, base=FakeKingston(), strict=True)
    mp = {int(k): int(v) for k, v in sel["winner_mapping"].items()}
    patch = sorted(mp.values())
    cdir = p(prep, "circuits")
    os.makedirs(cdir, exist_ok=True)
    stale = os.listdir(cdir)
    if stale and not force:
        raise SystemExit(f"{rel(cdir)} is not empty ({len(stale)} files): a rebuild (D10) needs --force")
    for f in stale:
        os.remove(os.path.join(cdir, f))
    return rec, info, sel, base, binfo, mp, patch, cdir, G.factory()["n"]


def stage_build(args):
    t0 = time.time()
    rec, info, sel, base, binfo, mp, patch, cdir, n = prepare_build(args.prep, args.force)
    common = common_block(rec)
    reuse = None
    if sel.get("pilot_mapping_reproduced"):
        reuse = {cid: os.path.join(PILOT_PREP, "circuits", cid + ".qpy.gz") for cid in BASE_IDS}
    mans = build_coarse(args.prep, rec, base, BASE_IDS, CELLS, cdir, common, sel, mp, patch,
                        force_reuse=reuse)
    mans += build_calibration_pubs(base, rec, patch, n, cdir, common)
    extra = {"created": now(), "script": "scripts/h0_ddtest_circuits.py", "stage": "build",
             "purpose": ("prompts/24 Stage T: the four-cell DD A/B test (T0 none, T1 context-aware, T2 XY4, "
                         "T3 XY4 long windows) on the pilot's two k = 1 circuits, plus the patch's readout pubs"),
             "common": common, "record": info["record"],
             "base_backend": {k: v for k, v in binfo.items() if k not in ("qubits", "edges")},
             "patch": patch, "winner_mapping": sel["winner_mapping"],
             "mapping_reproduced": sel["mapping_reproduced"],
             "pilot_mapping_reproduced": sel.get("pilot_mapping_reproduced"),
             "cells": {c: CELL_DESCRIPTION[c] for c in CELLS}, "base_ids": list(BASE_IDS),
             "runtime_s": time.time() - t0}
    index, qubits, edges = write_index(args.prep, mans, extra)
    print(f"wrote {len(mans)} circuits to {rel(cdir)} ({len(qubits)} qubits, {len(edges)} directed edges) "
          f"in {time.time() - t0:.0f} s")
    return 0


def stage_patchcal(args):
    from h0_backends import fresh_calibration, frozen_qubits_and_edges, resolve_backend
    rec, info = day_record(args.prep)
    qubits, edges = frozen_qubits_and_edges(p(args.prep))
    b = resolve_backend(DEVICE)
    prec = fresh_calibration(b, qubits, edges)
    diffs = KP.leaves_equal(prec, rec)
    path = p(args.prep, f"calibration_{prec['stamp']}.json")
    if os.path.exists(path) and load_json(path)["fingerprint"] != prec["fingerprint"]:
        path = p(args.prep, f"calibration_{prec['stamp']}_{prec['fingerprint'][:8]}.json")
    prec["full_record"] = info["record"]["path"]
    prec["full_record_fingerprint"] = rec["fingerprint"]
    prec["leaves_equal_full_record"] = not diffs
    prec["leaf_differences"] = diffs[:50]
    dump_json(prec, path)
    info["patch_record"] = {"path": rel(path), "fingerprint": prec["fingerprint"], "stamp": prec["stamp"],
                            "last_update_date": prec["last_update_date"], "leaves_equal_full_record": not diffs,
                            "n_differences": len(diffs), "missing_errors": prec["missing_errors"],
                            "n_qubits": len(prec["qubits"]), "n_edges": len(prec["edges"])}
    dump_json(info, p(args.prep, "live.json"))
    print(f"patch record {rel(path)}: fingerprint {prec['fingerprint']} ({len(prec['qubits'])} qubits, "
          f"{len(prec['edges'])} edges), missing_errors {len(prec['missing_errors'])}, leaves equal to the full "
          f"record: {not diffs} ({len(diffs)} differences)")
    if diffs:
        print("the calibration moved between the full read and the patch read: repeat record-patchcal (D10)")
        for d in diffs[:10]:
            print("   ", d)
        return KP.EXIT_STOP
    if prec["missing_errors"]:
        print("STOP: missing error leaves on the selected patch")
        return KP.EXIT_STOP
    return 0


STAGES = {"account": stage_account, "record": stage_record, "select": stage_select,
          "build": stage_build, "patchcal": stage_patchcal}


def build_parser(default_prep=PREP, default_diff=PILOT_FULL_RECORD):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--prep", default=default_prep)
    ap.add_argument("--out", default=None)
    ap.add_argument("--after", action="store_true", help="account: the post-submission read (no STOP)")
    ap.add_argument("--min-remaining", type=float, default=MIN_REMAINING_S)
    ap.add_argument("--diff-against", default=default_diff)
    ap.add_argument("--force", action="store_true", help="build: clear circuits/ first (D10 rebuild)")
    return ap


def main():
    args = build_parser().parse_args()
    return STAGES[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
