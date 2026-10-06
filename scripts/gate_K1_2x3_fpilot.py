#!/usr/bin/env python3
"""
Gate K1_2x3_fpilot (prompts/27 stage 0b; owner decision data/owner_decision_20261005_k1_2x3_fpilot.md)
-- the 2x3 clean-fraction pilot on ibm_kingston: the two signed k = 1 circuits with the largest
ideal reference-string probability (one per sector), routed on the day's record exactly as gate
K0 routes (scripts/gate_K0_2x3_2x4.py: route / alap / idle_terms), ALAP with explicit delays,
client-side XY4 in windows >= 1.024 us (cell T3 of H0_ddtest, inserted by
h0_ddtest_circuits.dd_variant), plus the two readout pubs; 1e5 shots per pub in ONE job.

A measurement gate: PASS = preregistered, measured, verified, consistent.  There is no criterion
on f or on the decision -- a NO-GO pilot is a PASS gate.

Decision (owner decision 1a of 2026-10-05, data/owner_decision_20261005_partB.md; thresholds of
prompts/27): the statistic is f_hat_ideal = f_hit / r_nc, with f_hit the pooled reference-string
clean fraction of the two k = 1 circuits (skqd.skqd.pooled_reference_string_test, readout factor
0.82, garbage expectation subtracted) and r_nc from data/cf_trajectories/r_nc.json.
GO-B if f_hat_ideal >= 1e-3, GO-A if 3e-4 <= f_hat_ideal < 1e-3, NO-GO below; the class of each
end of the 95 % interval is reported beside it (the decision is 'firm' when all three agree).

Stages (default --prep data/hardware/K1_2x3_prep; all 0 QPU s except `submit`):
  select     p_ref of every 2x3 k = 1 reference (exact Krylov state), the largest per sector;
             the exhaustive per-sector garbage acceptance (2^20 strings, cached in data/K1_2x3_fpilot/)
  record     the day's full record = gate K0's live record (validation/K0_2x3_2x4.json) -> live.json
  build      route (K0.route, 8 seeds, fewest CZ), ALAP (K0.alap), T3 XY4, checks (i)-(v) and the
             exactness against the exact Krylov state on 20-25 active qubits; the readout pubs
  patchcal   the patch-scoped D9 record (h0_ddtest_circuits.stage_patchcal)
  predict    the preregistration <prep>/prereg_<fp16>.json (bracket, estimate, decision rule)
  prereg-md  reports/K1_2x3_fpilot_prereg_<stamp>.md from that JSON
  dryrun     the local path check: h0_submit.py --dry-run at a few shots (30-minute rule)
  submit     --live only, and only if the owner decision file exists and every precondition holds:
             K0 PASS on the day's record, prereg committed, dry run PASS, calwatch / D9 match,
             estimate <= 300 s, enough seconds on the account; then h0_submit.py (unchanged)
  assemble   the analysis on a counts directory -> validation/K1_2x3_fpilot[_dryrun].json + report
"""
import argparse
import glob
import gzip
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gate_K0_2x3_2x4 as K0  # noqa: E402

ROOT = K0.ROOT
DEVICE = "ibm_kingston"
PREP = os.path.join("data", "hardware", "K1_2x3_prep")
OUT_LIVE = os.path.join("data", "hardware", "K1_2x3_ibm_kingston")
OUT_DRY = os.path.join("data", "hardware", "K1_2x3_dryrun")
DATA = os.path.join("data", "K1_2x3_fpilot")
OWNER_DECISION = os.path.join("data", "owner_decision_20261005_k1_2x3_fpilot.md")
OWNER_DECISION_1A = os.path.join("data", "owner_decision_20261005_partB.md")
R_NC_FILE = os.path.join("data", "cf_trajectories", "r_nc.json")
K0_JSON = os.path.join("validation", "K0_2x3_2x4.json")
# ---- preregistered constants (prompts/27 stage 0b and the coordinator's rulings of 2026-10-05)
SHOTS = 100000                 # per coarse circuit (prompts/27)
CAL_SHOTS = 100000             # the readout pubs at the same count: one shot count = ONE job
MAX_ESTIMATE_S = 300.0         # owner cap (billed); the execution estimate must not exceed it
MAX_BILLED_S = 300.0
GO_B, GO_A = 1e-3, 3e-4        # prompts/27 thresholds, read on f_hat_ideal (owner decision 1a)
CELL = "T3"                    # client XY4, windows >= 1.024 us (validation/H0_ddtest.json adopted cell)
K = 1
DRY_SHOTS_DEFAULT = 400
DRY_CAL_SHOTS_DEFAULT = 2000
DRY_SEED = 11
AMP_TOL, LEAK_TOL = 1e-10, 1e-9
CONF68, CONF95 = 0.6827, 0.95
BILLED_HISTORY = (("validation/H0_kpilot.json", "H0_kpilot"), ("validation/H0_ddtest.json", "H0_ddtest"),
                  ("validation/H0_2x2.json", "H0_2x2"))
DECISION_RULE = ("Statistic: f_hat_ideal = f_hit / r_nc (owner decision 1a, 2026-10-05), f_hit = the pooled "
                 "reference-string clean fraction of the two k = 1 circuits (pooled_reference_string_test, readout "
                 "factor 0.82, garbage expectation N a / dim subtracted), r_nc read from data/cf_trajectories/r_nc.json. "
                 "GO-B if f_hat_ideal >= 1e-3 (a Tier-B 2x3 run costs <= 2e7 shots per sector); GO-A if 3e-4 <= "
                 "f_hat_ideal < 1e-3 (Tier A only); NO-GO below 3e-4 (prompts/27 stage 0b).  The class is read on the "
                 "point value; the classes of the 95 % (Garwood) interval ends are reported beside it and the decision "
                 "is called firm when all three agree.  f_hit is reported beside f_hat_ideal.")
DRY_RUN_DESIGN = ("The 2x2 dry runs sent every pub through h0_submit.py --dry-run (Aer on the FakeKingston snapshot "
                  "noise).  At 2x3 the routed circuits occupy 21-25 active qubits and every gate and delay carries a "
                  "non-unitary noise op that breaks Aer's gate fusion: one noisy shot of one coarse pub costs minutes on "
                  "this laptop (measured: noisy_cost_measured), so the few hundred shots a path check of the statistic "
                  "needs are many hours, and at the device f ~ 1e-5 a noisy run would contain no reference hit anyway.  "
                  "The path check is therefore split: the readout pubs go through h0_submit.py --dry-run unchanged (the "
                  "submission path, session.json, the raw counts format, the dry-run K3); the coarse pubs are sampled "
                  "noiselessly from their exact output distribution (a few hundred shots), which checks that the decoder "
                  "and the reference-string statistic find the reference string with probability p_ref (bit order, "
                  "measurement map, sector) and return 0.82 f_hit = 1 for a clean run.  A noisy dry run of the coarse "
                  "pubs at a few hundred shots needs a GPU (RTX 3070 desktop or the Slurm GPU cluster); Perlmutter is not "
                  "available for this gate.")
R_NC_NOTE = ("r_nc is a gate-noise value (gate CF_traj, the A6 gate-only channel).  Under IBM idle dephasing the A5 "
             "model gives f_hit < f_ideal (r < 1 at both T2 ends), so dividing f_hit by r_nc = 1.115 can only LOWER "
             "the estimate there: the correction is conservative on this device.")

p, rel, load_json, dump_json, now = K0.p, K0.rel, K0.load_json, K0.dump_json, K0.now


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
            "qiskit_ibm_runtime": qiskit_ibm_runtime.__version__, "numpy": np.__version__}


def r_nc():
    d = load_json(p(R_NC_FILE))
    return float(d["r_nc"]), d


# --------------------------------------------------------------------------- pure (tested)
def classify(f):
    """The prompts/27 class of one value of f_hat_ideal."""
    if f is None:
        return None
    if f >= GO_B:
        return "GO-B"
    if f >= GO_A:
        return "GO-A"
    return "NO-GO"


def decide(f_ideal, f_ideal_95):
    """(decision, {point, lo95, hi95 classes}, firm)."""
    cls = {"point": classify(f_ideal), "lo95": classify(f_ideal_95[0]), "hi95": classify(f_ideal_95[1])}
    firm = len({cls["point"], cls["lo95"], cls["hi95"]}) == 1
    return cls["point"], cls, bool(firm)


def ideal_of(f_hit, rnc):
    return None if f_hit is None else float(f_hit) / float(rnc)


def readout_from_cal(c0, c1, n):
    """{P(0|0), P(1|1)} per clbit from the all-0 / all-1 counts ({bit tuple: count}, bit k = clbit k)."""
    s0, s1 = sum(c0.values()), sum(c1.values())
    p00 = [sum(v for b, v in c0.items() if b[i] == 0) / s0 for i in range(n)]
    p11 = [sum(v for b, v in c1.items() if b[i] == 1) / s1 for i in range(n)]
    return p00, p11, int(s0), int(s1)


def expected_hits(N, f, p_ref, a, dim, readout_factor):
    """Prediction of the reference-string count: N (rf f p_ref + a / dim) (manual Step 4.4 yield model)."""
    return float(N) * (float(readout_factor) * float(f) * float(p_ref) + float(a) / float(dim))


# --------------------------------------------------------------------------- 2x3 physics (gate K0's functions)
physics = K0.physics
exact_coarse = K0.exact_coarse
logical_state = K0.logical_state


def garbage_acceptance(force=False):
    """Exhaustive acceptance of the 2^20 strings into each sector (the 2x2 convention, gate_H0P.random_acceptance)."""
    path = p(DATA, "garbage_acceptance_2x3.json")
    if os.path.exists(path) and not force:
        return load_json(path)
    from gate_H0P import random_acceptance
    P = physics()
    t0 = time.time()
    out = {"created": now(), "script": "scripts/gate_K1_2x3_fpilot.py --stage select", "commit": git_commit(),
           "method": "gate_H0P.random_acceptance: Codec.decode of every one of the 2^20 strings into the sector",
           "n_qubits": P["n"]}
    for twoB in (0, 2):
        r = random_acceptance(P["codec"], twoB)
        out[f"B={twoB // 2}"] = {"accepted": r["accepted"], "strings": r["strings"], "fraction": r["fraction"]}
    out["runtime_s"] = time.time() - t0
    dump_json(out, path)
    return out


def circuit_id(twoB, ref, k=K):
    return f"B{twoB // 2}_ref{int(ref):02d}_k{int(k)}"


# --------------------------------------------------------------------------- statevectors
def exactness(circ, final, ex, phase_align, global_phase=None, psi=None):
    return K0.circuit_exactness(circ, final, ex, phase_align=phase_align, global_phase=global_phase, psi=psi)


def dd_checks(base, out, rec, target, final, psi0=None):
    """Checks (i)-(v) of prompts/24 T.B2 (h0_ddtest_circuits.dd_checks) for a 2x3 circuit: the
    statevector on the active qubits, the duration, the timeline (window_violations), the basis and
    the pulse cost on the day's record."""
    import h0_ddtest_circuits as DC
    from h0_qpu_time import circuit_duration_s
    dt = float(rec["dt_s"])
    if psi0 is None:
        psi0, _ = logical_state(base, final)
    psi, info = logical_state(out, final)
    ov = complex(np.vdot(psi0, psi))
    dpsi = float(np.max(np.abs(psi * np.exp(-1j * np.angle(ov)) - psi0)))
    d0 = circuit_duration_s(base, target.durations(), target)
    d1 = circuit_duration_s(out, target.durations(), target)
    win = DC.window_violations(base, out, rec)
    lead, trail, bad_kind, missing = win["lead"], win["trail"], win["bad_kind"], win["missing"]
    un0, un1 = win["unaligned"]
    per_q = win["pulses"]
    ops_after = {k: int(v) for k, v in out.count_ops().items()}
    s_dd = float(sum(n * float(rec["qubits"][str(q)]["x_error"]) for q, n in per_q.items()))
    act0 = sorted({base.find_bit(q).index for i in base.data for q in i.qubits if i.operation.name != "barrier"})
    act1 = sorted({out.find_bit(q).index for i in out.data for q in i.qubits if i.operation.name != "barrier"})
    res = {"statevector_max_abs_delta_up_to_phase": dpsi, "statevector_overlap_abs": abs(ov),
           "statevector_ok": dpsi < AMP_TOL,
           "duration_base_s": d0, "duration_s": d1, "duration_delta_dt": abs(d1 - d0) / dt,
           "duration_ok": abs(d1 - d0) <= dt * (1 + 1e-9),
           "base_ops_moved_or_missing": int(missing), "unaligned_multiqubit_gates": [un0, un1],
           "inserted_non_pulse_ops": dict(bad_kind),
           "pulses_in_leading_window": {str(k): v for k, v in sorted(lead.items())},
           "pulses_after_measure": {str(k): v for k, v in sorted(trail.items())},
           "windows_ok": (not lead and not trail and not bad_kind and not missing and un0 == 0 and un1 == 0),
           "ops": ops_after, "basis_ok": DC.in_basis(ops_after), "active_qubits_unchanged": act0 == act1,
           "pulses_per_physical_qubit": {str(k): int(v) for k, v in sorted(per_q.items())},
           "n_pulses": int(sum(per_q.values())), "n_rz_inserted": int(win["inserted"].get("rz", 0)),
           "pulse_cost_nats": s_dd, "null_ratio": math.exp(-s_dd),
           "pulse_cost_rule": "sum over inserted x pulses (a translated y is one x pulse) of the qubit's x_error on the day's record"}
    res["ok"] = bool(res["statevector_ok"] and res["duration_ok"] and res["windows_ok"] and res["basis_ok"]
                     and res["active_qubits_unchanged"])
    return res, (psi, info)


# --------------------------------------------------------------------------- stages
def stage_select(args):
    t0 = time.time()
    P = physics()
    rows = {}
    for twoB in (0, 2):
        for r in K0.references_2x3(twoB):
            ex = exact_coarse(twoB, r)
            cid = circuit_id(twoB, r)
            q0p = p("data", "quantinuum", "circuits_2x3", cid + ".manifest.json")
            x = {"twoB": twoB, "sector": f"B={twoB // 2}", "reference": r, "k": K, "dt": ex["dt"],
                 "p_reference": ex["p_reference"], "sector_mass": ex["sector_mass"], "dim": ex["dim"],
                 "reference_int": ex["reference_int"]}
            if os.path.exists(q0p):
                x["p_reference_Q0P_compiled_statevector"] = float(load_json(q0p)["p_reference"])
                x["abs_diff_vs_Q0P"] = abs(x["p_reference_Q0P_compiled_statevector"] - ex["p_reference_unnormalised"])
            rows[cid] = x
    chosen = {}
    for twoB in (0, 2):
        sec = {c: v for c, v in rows.items() if v["twoB"] == twoB}
        best = max(sec, key=lambda c: (sec[c]["p_reference"], -sec[c]["reference"]))
        chosen[f"B={twoB // 2}"] = best
    ga = garbage_acceptance(force=args.force)
    out = {"stage": "select", "created": now(), "commit": git_commit(), "qpu_seconds": 0,
           "rule": ("prompts/27 stage 0b: per sector, the signed k = 1 circuit with the largest ideal reference-string "
                    "probability p_ref (exact Krylov state, normalised on the sector; ties: the lower basis index)"),
           "candidates": rows, "chosen": chosen, "garbage_acceptance": ga,
           "n_qubits": P["n"], "runtime_s": time.time() - t0}
    dump_json(out, p(args.prep, "select.json"))
    for s, c in chosen.items():
        print(f"{s}: {c} p_ref {rows[c]['p_reference']:.6f} (dim {rows[c]['dim']}, a {ga[s]['fraction']:.4e})")
    return 0


def stage_record(args):
    """The day's record = gate K0's live record (so K1 routes on exactly the record K0 ran on)."""
    k0 = load_json(p(K0_JSON))
    live = (k0["data"].get("records") or {}).get("live")
    path = args.record or (live or {}).get("path")
    if not path:
        raise SystemExit("validation/K0_2x3_2x4.json has no live record: run gate_K0_2x3_2x4.py --live first")
    if live and not args.record and not live.get("usable", True):
        raise SystemExit(f"STOP: K0's live record {path} is unusable ({live.get('n_missing_errors')} missing error "
                         f"leaves {live.get('missing_by_instruction')}): no day's record to route on")
    rec = load_json(path)
    if live and rec["fingerprint"] != live["fingerprint"]:
        raise SystemExit("the record file's fingerprint is not the one K0 recorded")
    if rec.get("missing_errors"):
        raise SystemExit(f"STOP: the day's record has {len(rec['missing_errors'])} missing error leaves")
    info = {"stage": "record", "created": now(), "qpu_seconds": 0,
            "record": {"path": rel(p(path)) if not os.path.isabs(path) else rel(path), "stamp": rec["stamp"],
                       "last_update_date": rec["last_update_date"], "fingerprint": rec["fingerprint"],
                       "n_qubits": len(rec["qubits"]), "n_edges": len(rec["edges"]), "dt_s": rec["dt_s"],
                       "default_rep_delay_s": rec["default_rep_delay_s"], "status": rec.get("status")},
            "k0": {"path": K0_JSON, "status": k0["status"], "live_fingerprint": (live or {}).get("fingerprint"),
                   "commit": k0["environment"]["git_commit"]}}
    dump_json(info, p(args.prep, "live.json"))
    print(f"day's record {info['record']['path']} ({rec['fingerprint'][:16]}, {rec['last_update_date']}); K0 "
          f"status {k0['status']}")
    return 0


def day_record(prep):
    info = load_json(p(prep, "live.json"))
    return load_json(info["record"]["path"]), info


def common_block(rec):
    return {"backend": "FakeKingston", "backend_qubits": 156, "n_logical_qubits": 20, "lattice": "2x3",
            "g2": K0.G2, "device": DEVICE, "backend_calibration_last_update": rec["last_update_date"],
            "circuit_family": ("gate_S2D.circuit_set(3) signed exact structured circuits (CircuitFactory(Model(3), 4.0) "
                               "default), routed on the day's kingston record exactly as gate K0 (level 3, seeds 0..7, "
                               "fewest CZ, uncalibrated cz keys removed), ALAP with explicit delays, client XY4 (cell T3, "
                               "windows >= 1.024 us) in the delays"),
            "transpiler": {"note": "per circuit (see its manifest)"}}


def build_calibration_pubs(base, rec, union, cdir, common):
    """All-0 / all-1 readout pubs on the union of the measured physical qubits (clbit i = union[i])."""
    from h0_build_circuits import dump_qpy_gz
    from qiskit import QuantumCircuit, transpile

    from skqd.hardware import transpiled_layout
    n = len(union)
    mans = []
    for name_, bits in (("all0", (0,) * n), ("all1", (1,) * n)):
        cid = f"cal_patch_{name_}"
        qc = QuantumCircuit(n, n)
        for q, b in enumerate(bits):
            if b:
                qc.x(q)
        qc.barrier()
        qc.measure(range(n), range(n))
        tq = transpile(qc, backend=base, initial_layout=list(union), optimization_level=1, seed_transpiler=7)
        lay = transpiled_layout(tq, n)
        if not lay["measurement_consistent"] or lay["logical_to_physical"] != list(union):
            raise SystemExit(f"{cid}: measurement map / layout is not the union {union}")
        xs = sorted(tq.find_bit(i.qubits[0]).index for i in tq.data if i.operation.name == "x")
        ops = {k: int(v) for k, v in tq.count_ops().items()}
        if set(ops) - {"x", "measure", "barrier"} or xs != (list(union) if name_ == "all1" else []):
            raise SystemExit(f"{cid}: the transpiled preparation is not {name_} on the union ({ops}, x on {xs})")
        raw, sha = dump_qpy_gz(tq, os.path.join(cdir, cid + ".qpy.gz"))
        man = dict(common)
        man.update({"id": cid, "kind": "readout_calibration", "prep_bits": list(bits), "prep_name": name_,
                    "repetitions": None, "physical_qubits": lay["active_physical"],
                    "readout_patch": list(union), "logical_to_physical": lay["logical_to_physical"],
                    "measurement_map_clbit_to_physical": lay["measurement_map"],
                    "measurement_consistent": lay["measurement_consistent"],
                    "readout_error_record": [float(rec["qubits"][str(q)]["measure_error"]) for q in union],
                    "transpiler": {"optimization_level": 1, "seed_transpiler": 7, "initial_layout": list(union)},
                    "ops": ops, "record_fingerprint_full": rec["fingerprint"],
                    "qpy": cid + ".qpy.gz", "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha})
        mans.append(man)
        print(f"  {cid}: {ops}", flush=True)
    return mans


def stage_build(args):
    import h0_ddtest_circuits as DC
    from gate_S2D import analyse_on_backend
    from h0_build_circuits import dump_qpy_gz

    from skqd.hardware import transpiled_layout
    t0 = time.time()
    prep = args.prep
    rec, info = day_record(prep)
    sel = load_json(p(prep, "select.json"))
    base, binfo = K0.kingston_backend(rec)
    bad = K0.uncalibrated_pairs(rec)
    tgt, removed = K0.routing_target(base.target, bad)
    R, R95, Rsrc = K0.xy4_gain()
    cdir = p(prep, "circuits")
    os.makedirs(cdir, exist_ok=True)
    stale = os.listdir(cdir)
    if args.force:
        for f in stale:
            os.remove(os.path.join(cdir, f))
    elif os.path.exists(p(prep, "index.json")) and stale:
        raise SystemExit(f"{rel(cdir)} holds a finished build: a rebuild needs --force")
    common = common_block(rec)
    ga = sel["garbage_acceptance"]
    mans, finals = [], {}
    # resumable, one circuit per invocation if asked (--only): each circuit costs ~10-20 min of dense
    # 21-25-qubit statevectors on this laptop, two would break the 30-minute rule in one command
    for sector, cid0 in sorted(sel["chosen"].items()):
        mpath = os.path.join(cdir, cid0 + ".json")
        if os.path.exists(mpath):
            m = load_json(mpath)
            if m.get("record_fingerprint_full") != rec["fingerprint"]:
                raise SystemExit(f"{rel(mpath)} was built on another record: rebuild with --force")
            mans.append(m)
            finals[cid0] = m["logical_to_physical"]
            print(f"  {cid0}: kept (built {m.get('built')})", flush=True)
            continue
        if args.only and cid0 not in args.only:
            continue
        c = sel["candidates"][cid0]
        t1 = time.time()
        twoB, ref = int(c["twoB"]), int(c["reference"])
        qc, gates, n, dt = K0.circuit_2x3(twoB, ref, K)
        ex = exact_coarse(twoB, ref)
        tq, rinfo = K0.route(qc, tgt, ex=ex, log=print)
        seed, table = rinfo["seed"], rinfo["per_seed"]
        lay = transpiled_layout(tq, n)
        final = [int(x) for x in lay["logical_to_physical"]]
        if not lay["measurement_consistent"]:
            raise SystemExit(f"{cid0}: the routed circuit's measurement map is not its final layout")
        sched, sch = K0.alap(tq, base, rec)
        if not sch["k0_4_ok"]:
            raise SystemExit(f"{cid0}: ALAP check failed {sch}")
        ex_base, psi_base = exactness(sched, final, ex, phase_align=True, global_phase=tq.global_phase)
        if not ex_base["ok"]:
            raise SystemExit(f"{cid0}: exactness of the scheduled circuit failed {ex_base}")
        out, par = DC.dd_variant(CELL, sched, rec, base.target)
        chk, psi_out = dd_checks(sched, out, rec, base.target, final, psi0=psi_base)
        if not chk["ok"]:
            raise SystemExit(f"{cid0}: DD checks failed {json.dumps({k: chk[k] for k in chk if k != 'ops'})[:2000]}")
        ex_dd, _psi = exactness(out, final, ex, phase_align=True, psi=psi_out)
        if not ex_dd["ok"]:
            raise SystemExit(f"{cid0}: exactness of the T3 circuit failed {ex_dd}")
        a = analyse_on_backend(tq, base)
        idle_block = K0.idle_terms(sched, rec, a["f_including_1q_errors"], R, R95)
        name = cid0 + ".qpy.gz"
        raw, sha = dump_qpy_gz(out, os.path.join(cdir, name))
        man = dict(common)
        man.update({
            "id": cid0, "kind": "coarse_step", "sector": sector, "twoB": twoB, "reference": ref, "k": K,
            "repetitions": 1, "dt": dt, "theta": K * dt, "p_reference": ex["p_reference"], "dim": ex["dim"],
            "sector_mass": ex["sector_mass"], "reference_bits": ex["reference_bits"],
            "reference_int": ex["reference_int"], "garbage_acceptance": ga[sector]["fraction"],
            "routing": {"cz_keys_removed": removed, "uncalibrated_pairs": sorted(map(list, bad)), **rinfo,
                        "best_seed": seed, "routed_as": "gate_K0_2x3_2x4.route (the same function, the same rule)"},
            "routed": {"cz": int(tq.count_ops().get("cz", 0)), "ops": {k: int(v) for k, v in tq.count_ops().items()},
                       "depth": int(tq.depth()), "global_phase": float(tq.global_phase)},
            "logical_to_physical": final, "readout_patch": sorted(final),
            "measurement_map_clbit_to_physical": {str(k): v for k, v in sorted(
                __import__("h0_kpilot_circuits").measurement_map(out).items())},
            "physical_qubits": sorted({out.find_bit(q).index for i in out.data for q in i.qubits
                                       if i.operation.name != "barrier"}),
            "schedule": "alap", "schedule_info": sch["schedule_info"], "schedule_checks": sch,
            "T_s": sch["unscheduled_T_s"], "T_total_s": sch["unscheduled_T_total_s"],
            "scheduled_duration_s": chk["duration_s"],
            "ops": {k: int(v) for k, v in out.count_ops().items()}, "cz": int(out.count_ops().get("cz", 0)),
            "depth": int(out.depth()), "n_delays": int(out.count_ops().get("delay", 0)),
            "exactness_base": ex_base, "exactness": ex_dd, "measurement_consistent": ex_dd["measurement_consistent"],
            "f": {"f_gates_layout": a["f_including_1q_errors"], "f_cz_and_readout_only": a["f"],
                  "f_ceiling_2q": K0.f_ceiling_2q(K0.record_stats(rec)["cz_error_min"], int(tq.count_ops().get("cz", 0))),
                  "idle": idle_block, "xy4_gain": {"R": R, "R_95": R95, "source": Rsrc},
                  "record_fingerprint": rec["fingerprint"]},
            "dd": {"cell": CELL, "description": DC.CELL_DESCRIPTION[CELL], "pass": par["pass"],
                   "parameters": par["parameters"], "y_translated": par.get("y_translated", 0),
                   "idle_register_delays_removed_after_pass": par.get("idle_register_delays_removed_after_pass", 0),
                   "n_pulses": chk["n_pulses"], "pulse_cost_nats": chk["pulse_cost_nats"],
                   "null_ratio": chk["null_ratio"], "pulses_per_physical_qubit": chk["pulses_per_physical_qubit"],
                   "checks": chk},
            "record_fingerprint_full": rec["fingerprint"],
            "qpy": name, "qpy_bytes_uncompressed": raw, "qpy_gz_sha256": sha, "family_member": cid0,
            "built": now(), "build_s": time.time() - t1,
        })
        dump_json(man, mpath)
        mans.append(man)
        finals[cid0] = final
        print(f"  {cid0}: {rinfo['chosen']}, cz {man['cz']}, active {ex_dd['n_active']}, T {chk['duration_s'] * 1e6:.1f} us, "
              f"pulses {chk['n_pulses']} (S_DD {chk['pulse_cost_nats']:.3f}), |d| {ex_dd['max_abs_delta']:.1e} "
              f"(raw base {ex_base['max_abs_delta_raw_phase']:.1e}), leak {ex_dd['leakage']:.1e}, f_gates "
              f"{a['f_including_1q_errors']:.3e} ({time.time() - t1:.0f} s)", flush=True)
    missing = [c for c in sel["chosen"].values() if c not in finals]
    if missing:
        print(f"built {len(finals)} of {len(sel['chosen'])} circuits; still to build: {missing} (run again with --only)")
        return 0
    union = sorted(set().union(*[set(v) for v in finals.values()]))
    mans += build_calibration_pubs(base, rec, union, cdir, common)
    extra = {"created": now(), "script": "scripts/gate_K1_2x3_fpilot.py --stage build", "stage": "build",
             "purpose": ("prompts/27 stage 0b: the 2x3 clean-fraction pilot -- the two signed k = 1 circuits with the "
                         "largest p_ref, routed as gate K0, ALAP, client XY4 (T3), plus the readout pubs of the union of "
                         "the measured qubits"),
             "common": common, "record": info["record"],
             "base_backend": {k: v for k, v in binfo.items() if k not in ("qubits", "edges")},
             "patch": union, "readout_union": union, "chosen": sel["chosen"], "cell": CELL,
             "runtime_s": time.time() - t0}
    DC.write_index(prep, mans, extra)
    print(f"wrote {len(mans)} circuits to {rel(cdir)} (readout union {len(union)} qubits) in {time.time() - t0:.0f} s")
    return 0


def stage_patchcal(args):
    import h0_ddtest_circuits as DC
    return DC.stage_patchcal(args)


def patch_record(prep):
    info = load_json(p(prep, "live.json"))
    pr = info.get("patch_record")
    if not pr:
        raise SystemExit("live.json carries no patch_record: run --stage patchcal")
    return load_json(pr["path"]), pr, info


def billed_history():
    """(estimate, billed) of the earlier kingston jobs, read from their validation JSONs."""
    out = []
    for path, lab in BILLED_HISTORY:
        if not os.path.exists(p(path)):
            continue
        d = load_json(p(path))["data"]
        live = d.get("live") or {}
        est = (live.get("preflight_estimate_s") or d.get("execution_estimate_prereg_s")
               or (live.get("execution_estimate_s")))
        us = live.get("usage_s")
        if est and us:
            out.append({"gate": lab, "estimate_s": float(est), "billed_s": float(us), "ratio": float(us) / float(est)})
    return out


def stage_predict(args):
    import h0_qpu_time as qt
    import h0_kpilot_circuits as KP
    from gate_H0P import DIAG_MIN
    from h0_backends import fresh_calibration, frozen_qubits_and_edges, resolve_backend

    from skqd.skqd import READOUT_FACTOR
    t0 = time.time()
    prep = args.prep
    rec, prinfo, info = patch_record(prep)
    index = load_json(p(prep, "index.json"))
    sel = load_json(p(prep, "select.json"))
    from gate_H0P import load_manifests
    cm, cals = load_manifests(p(prep))
    b = resolve_backend(DEVICE)
    qubits, edges = frozen_qubits_and_edges(p(prep))
    live = fresh_calibration(b, qubits, edges)
    if live["fingerprint"] != rec["fingerprint"]:
        print(f"STOP (D10): the live patch fingerprint {live['fingerprint'][:16]} is not the patch record's "
              f"{rec['fingerprint'][:16]} -- re-run record / build / patchcal on the new content")
        return 3
    est = qt.estimate(p(prep), b, {}, CAL_SHOTS, shots_default=SHOTS)
    rnc, rnc_d = r_nc()
    hist = billed_history()
    ratios = [h["ratio"] for h in hist]
    acct = KP.account_snapshot()
    remaining = (acct.get("usage") or {}).get("usage_remaining_seconds")
    circuits = {}
    for m in cm:
        f = m["f"]
        ends = {"f_gates_layout (no idle)": f["f_gates_layout"],
                "f_idle_aware_xy4 echo (2x2 transfer)": f["idle"]["echo"]["f_idle_aware_xy4"],
                "f_idle_aware echo": f["idle"]["echo"]["f_idle_aware"],
                "f_idle_aware_xy4 0.174 (2x2 transfer)": f["idle"]["transferred_0.174"]["f_idle_aware_xy4"],
                "f_idle_aware 0.174": f["idle"]["transferred_0.174"]["f_idle_aware"]}
        a, dim, pref = m["garbage_acceptance"], m["dim"], m["p_reference"]
        circuits[m["id"]] = {
            "sector": m["sector"], "reference": m["reference"], "p_reference": pref, "dim": dim,
            "garbage_acceptance": a, "reference_int": m["reference_int"], "cz": m["cz"],
            "scheduled_duration_s": m["scheduled_duration_s"], "n_pulses": m["dd"]["n_pulses"],
            "pulse_cost_nats": m["dd"]["pulse_cost_nats"], "null_ratio": m["dd"]["null_ratio"],
            "f_bracket": ends, "f_ceiling_2q": f["f_ceiling_2q"],
            "S_idle": {"echo": f["idle"]["echo"]["S_idle"], "transferred_0.174": f["idle"]["transferred_0.174"]["S_idle"]},
            "expected_reference_hits_from_garbage": SHOTS * a / dim,
            "expected_reference_hits": {k: expected_hits(SHOTS, v, pref, a, dim, READOUT_FACTOR) for k, v in ends.items()},
            "f_hit_for_one_excess_hit": 1.0 / (SHOTS * pref * READOUT_FACTOR),
            "qpy_gz_sha256": m["qpy_gz_sha256"], "physical_qubits": m["physical_qubits"],
            "logical_to_physical": m["logical_to_physical"]}
    den = sum(SHOTS * c["p_reference"] * READOUT_FACTOR for c in circuits.values())
    garb = sum(c["expected_reference_hits_from_garbage"] for c in circuits.values())
    thresholds_hits = {"GO-B": GO_B * rnc * den + garb, "GO-A": GO_A * rnc * den + garb}
    union = index["readout_union"]
    pubs = [{"id": m["id"], "kind": m["kind"], "shots": SHOTS if m["kind"] == "coarse_step" else CAL_SHOTS}
            for m in sorted(cm + cals, key=lambda m: m["id"])]
    fp16 = rec["fingerprint"][:16]
    pre = {
        "gate": "K1_2x3_fpilot", "script": "scripts/gate_K1_2x3_fpilot.py --stage predict",
        "created": now(), "commit": git_commit(), "versions": versions(), "qpu_seconds": 0, "prep": prep,
        "prep_created": index["created"],
        "owner_decision": OWNER_DECISION, "owner_decision_1a": OWNER_DECISION_1A,
        "calibration": {"backend": DEVICE, "fingerprint": rec["fingerprint"], "path": prinfo["path"],
                        "last_update_date": rec["last_update_date"], "stamp": rec["stamp"],
                        "full_record_path": info["record"]["path"], "full_record_fingerprint": info["record"]["fingerprint"],
                        "live_fingerprint_at_predict": live["fingerprint"],
                        "live_match_at_predict": live["fingerprint"] == rec["fingerprint"]},
        "k0": info.get("k0"),
        "selection": {"rule": sel["rule"], "chosen": sel["chosen"],
                      "p_reference": {c: sel["candidates"][c]["p_reference"] for c in sel["chosen"].values()}},
        "patch": union, "pubs": pubs, "shots_per_coarse_pub": SHOTS, "shots_per_readout_pub": CAL_SHOTS,
        "total_shots": sum(x["shots"] for x in pubs),
        "one_job": ("all four pubs at the same shot count, so h0_submit.plan_groups makes ONE group = one job "
                    "(--max-pubs-per-job 4)"),
        "sampler_options": "--dd off --twirling off (runtime DD off: the XY4 pulses are in the circuits); raw bit strings",
        "execution_estimate": {"total_execution_s": est["total_execution_s"], "total_shots": est["total_shots"],
                               "rep_delay_s": est["rep_delay_s"], "groups": est["groups"],
                               "per_circuit": est["per_circuit"], "last_update_date": est["last_update_date"],
                               "cap_s": MAX_ESTIMATE_S, "within_cap": est["total_execution_s"] <= MAX_ESTIMATE_S,
                               "estimator": "scripts/h0_qpu_time.estimate on the live target"},
        "billed": {"history": hist, "ratio_min": min(ratios) if ratios else None,
                   "ratio_max": max(ratios) if ratios else None,
                   "expected_billed_s_range": ([est["total_execution_s"] * min(ratios), est["total_execution_s"] * max(ratios)]
                                               if ratios else None),
                   "cap_billed_s": MAX_BILLED_S,
                   "note": "information: billed / estimate of the earlier kingston jobs; the binding precondition is estimate <= 300 s"},
        "account": {"usage": acct.get("usage"), "backend": acct.get("backend"), "read": acct.get("created")},
        "circuits": circuits,
        "pooled": {"clean_denominator_N_p_ref_rf": den, "expected_from_garbage": garb,
                   "reference_hit_counts_at_thresholds": thresholds_hits,
                   "note": "pooled hits needed (garbage included) for f_hat_ideal to reach each threshold"},
        "r_nc": rnc, "r_nc_source": R_NC_FILE, "r_nc_definition": rnc_d.get("definition"), "r_nc_note": R_NC_NOTE,
        "decision_rule": {"text": DECISION_RULE, "thresholds": {"GO-B": GO_B, "GO-A": GO_A},
                          "statistic": "f_hat_ideal = pooled_reference_string_test(rows, conf).f_clean / r_nc",
                          "interval": "Garwood 95 % on the pooled reference count, propagated (and divided by r_nc)",
                          "readout_factor": READOUT_FACTOR},
        "planner_expectation": ("prompts/27: at f = 1e-4 and p_ref ~ 0.5 the expected reference hits are ~8 against ~0.1 "
                                "from garbage; gate K0 / prompts/25 expect f_gates ~1e-5-1e-4 and far less with idle time"),
        "runtime_s": time.time() - t0,
    }
    pre["readout_expected_live"] = {"per_qubit": {str(q): 1.0 - float(rec["qubits"][str(q)]["measure_error"]) for q in union}}
    mins = min(pre["readout_expected_live"]["per_qubit"].items(), key=lambda kv: kv[1])
    pre["readout_expected_live"].update({"min": mins[1], "min_qubit": int(mins[0]),
                                         "source": "1 - measure_error of the patch record"})
    path = p(prep, f"prereg_{fp16}.json")
    if os.path.exists(path):
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel(path)], cwd=ROOT,
                                 capture_output=True).returncode == 0
        if tracked:
            raise SystemExit(f"{rel(path)} is committed as the preregistration: refusing to overwrite")
    dump_json(pre, path)
    print(f"wrote {rel(path)}: estimate {est['total_execution_s']:.2f} s over {est['total_shots']} shots (cap "
          f"{MAX_ESTIMATE_S:.0f}); expected billed {pre['billed']['expected_billed_s_range']}; remaining {remaining} s; "
          f"readout min {mins[1]:.4f} (q{mins[0]})")
    for cid, c in circuits.items():
        print(f"  {cid}: p_ref {c['p_reference']:.4f}, garbage {c['expected_reference_hits_from_garbage']:.3f}, hits at "
              + ", ".join(f"{k} {v:.3g}" for k, v in c["expected_reference_hits"].items()))
    rc = 0
    if est["total_execution_s"] > MAX_ESTIMATE_S:
        print(f"STOP: the execution estimate {est['total_execution_s']:.1f} s exceeds {MAX_ESTIMATE_S:.0f} s")
        rc = 3
    if mins[1] < DIAG_MIN:
        print(f"STOP: the live readout expectation {mins[1]:.4f} < DIAG_MIN {DIAG_MIN}")
        rc = 3
    return rc


def find_prereg(prep, path=None):
    if path:
        return path
    info = load_json(p(prep, "live.json"))
    fp = (info.get("patch_record") or {}).get("fingerprint")
    cands = sorted(glob.glob(p(prep, f"prereg_{fp[:16]}.json"))) if fp else []
    if not cands:
        raise SystemExit("no preregistration for the current patch record: run --stage predict")
    return rel(cands[0])


def _f(x, spec="{:.4g}"):
    return "n/a" if x is None else spec.format(x)


def _iv(iv, spec="{:.3e}"):
    if not iv or iv[0] is None:
        return "n/a"
    return "[" + spec.format(iv[0]) + ", " + spec.format(iv[1]) + "]"


def stage_prereg_md(args):
    from skqd.report import md_table, write_report
    path = find_prereg(args.prep, args.prereg)
    pre = load_json(p(path))
    est = pre["execution_estimate"]
    cal = pre["calibration"]
    rows = []
    for cid, c in pre["circuits"].items():
        for k, v in c["f_bracket"].items():
            rows.append([cid, k, f"{v:.3e}", f"{c['expected_reference_hits'][k]:.3g}"])
    crow = [[cid, c["sector"], f"{c['p_reference']:.4f}", c["dim"], f"{c['garbage_acceptance']:.3e}",
             f"{c['expected_reference_hits_from_garbage']:.3f}", c["cz"], f"{c['scheduled_duration_s'] * 1e6:.1f}",
             c["n_pulses"], f"{c['null_ratio']:.3f}", f"{c['S_idle']['echo']:.1f} / {c['S_idle']['transferred_0.174']:.1f}",
             f"{c['f_ceiling_2q']:.3e}"] for cid, c in pre["circuits"].items()]
    grows = [[g["group"], g["circuits"], g["shots_per_circuit"], f"{g['execution_s']:.2f}"] for g in est["groups"]]
    hrows = [[h["gate"], f"{h['estimate_s']:.2f}", f"{h['billed_s']:.1f}", f"{h['ratio']:.3f}"] for h in pre["billed"]["history"]]
    u = (pre["account"].get("usage") or {})
    po = pre["pooled"]
    txt = f"""# K1_2x3_fpilot preregistration -- ibm_kingston, calibration `{cal['fingerprint'][:16]}`

Generated by `scripts/gate_K1_2x3_fpilot.py --stage prereg-md` from `{path}` (written {pre['created']} at commit
`{pre['commit']}`).  Every number below is read from that JSON.  Nothing was submitted when this was written; the commit
that adds this file and the JSON is what criterion K1 checks against the submission time.  Prompt in force:
`prompts/27_2x3_substantial_result_strategy.md` stage 0b; owner decision `{pre['owner_decision']}` (one submission, cap
300 s billed); decision statistic per `{pre['owner_decision_1a']}` (1a).

## Calibration and circuits

- Patch record `{cal['path']}`: fingerprint `{cal['fingerprint']}`, last update {cal['last_update_date']}; full-device record
  `{cal['full_record_path']}` (`{cal['full_record_fingerprint'][:16]}`), the record gate K0 ran on ({pre['k0']}); live content at
  the prediction identical: {cal['live_match_at_predict']}.
- Selection: {pre['selection']['rule']} -> {pre['selection']['chosen']}.
- Readout pubs: all-0 / all-1 on the union of the measured qubits {pre['patch']}; live expectation of the smallest diagonal
  {pre['readout_expected_live']['min']:.4f} (qubit {pre['readout_expected_live']['min_qubit']}).

{md_table(["circuit", "sector", "p_ref", "sector dim", "garbage acceptance a", "garbage hits N a/dim", "CZ",
           "ALAP duration (us)", "XY4 pulses", "pulse null e^-S_DD", "S_idle echo / 0.174 (nats)", "f_ceiling_2q"], crow)}

## Shots, job, execution estimate

{pre['total_shots']} shots: {pre['shots_per_coarse_pub']} per coarse pub, {pre['shots_per_readout_pub']} per readout pub; {pre['one_job']}.
Options: {pre['sampler_options']}.

{md_table(["group", "circuits", "shots per circuit", "execution (s)"], grows)}

Execution estimate **{est['total_execution_s']:.2f} s** ({est['estimator']}; cap {est['cap_s']:.0f} s; within: {est['within_cap']};
rep delay {est['rep_delay_s'] * 1e6:.0f} us).  Billed / estimate of the earlier kingston jobs (information):

{md_table(["job", "estimate (s)", "billed (s)", "ratio"], hrows)}

Expected billed {_iv(pre['billed']['expected_billed_s_range'], '{:.1f}')} s against the owner's cap {pre['billed']['cap_billed_s']:.0f} s.
Account at the prediction: {u.get('usage_consumed_seconds')} s used of {u.get('usage_limit_seconds')} s, {u.get('usage_remaining_seconds')} s remaining.

## Prediction bracket (gate K0's functions on the day's record; per circuit)

{md_table(["circuit", "f end", "f", "expected reference hits (N (0.82 f p_ref + a/dim))"], rows)}

The XY4 entries are the 2x2-measured gain (H0_ddtest T3) transferred multiplicatively to the idle part and capped by the
gate-only value -- not a 2x3 measurement.  Pooled: clean denominator sum N p_ref 0.82 = {po['clean_denominator_N_p_ref_rf']:.4g},
garbage expectation {po['expected_from_garbage']:.3f}; pooled reference hits at which f_hat_ideal reaches GO-B / GO-A:
{po['reference_hit_counts_at_thresholds']['GO-B']:.1f} / {po['reference_hit_counts_at_thresholds']['GO-A']:.1f}.

## Decision rule (verbatim)

{pre['decision_rule']['text']}

r_nc = {pre['r_nc']:.6f} (`{pre['r_nc_source']}`: {pre['r_nc_definition']}).  {pre['r_nc_note']}

{pre['planner_expectation']}.
"""
    out = write_report(f"K1_2x3_fpilot_prereg_{cal['stamp']}.md", txt)
    print(f"wrote {rel(out)}")
    return 0


def sample_noiseless(circ, final, shots, seed):
    """Noiseless sampling of a frozen circuit: its exact logical output distribution (Aer statevector
    on the active qubits) sampled `shots` times -> {qiskit key: count} (rightmost character = clbit 0
    = logical qubit 0, the convention of h0_submit's counts files)."""
    psi, info = logical_state(circ, final)
    prob = np.abs(psi) ** 2
    norm = float(prob.sum())
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(int(shots), prob / norm)
    nz = np.nonzero(draws)[0]
    n = len(final)
    return {format(int(i), f"0{n}b"): int(draws[i]) for i in nz}, norm, info


def stage_dryrun(args):
    """The local path check (the 30-minute rule; see DRY_RUN_DESIGN):
    (a) h0_submit.py --dry-run, unchanged, on the two readout pubs (AerSimulator.from_backend(FakeKingston));
    (b) the two coarse pubs sampled noiselessly from their exact output distribution, written as counts
        files of the same raw format into the same directory, and recorded in its session.json."""
    out = args.out or OUT_DRY
    outdir = p(out)
    cmd = [sys.executable, os.path.join("scripts", "h0_submit.py"), "--dry-run", "--prep", args.prep,
           "--out", out, "--shots", "1", "--cal-shots", str(args.dry_cal_shots), "--only", "cal_patch_all0",
           "cal_patch_all1", "--seed", str(DRY_SEED), "--max-pubs-per-job", "4"]
    print("$ " + " ".join(cmd), flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT)
    t_a = time.time() - t0
    if r.returncode != 0:
        return r.returncode
    from gate_H0P import load_circuit, load_manifests
    cm, _cals = load_manifests(p(args.prep))
    sess_path = os.path.join(outdir, "session.json")
    sess = load_json(sess_path)
    cdir = os.path.join(outdir, "counts")
    entries = []
    for i, m in enumerate(sorted(cm, key=lambda m: m["id"])):
        path = os.path.join(cdir, m["id"] + ".json")
        if os.path.exists(path):
            raise SystemExit(f"{rel(path)} exists: counts files are raw data and are never overwritten")
        t1 = time.time()
        qc = load_circuit(p(args.prep), m)
        counts, norm, info = sample_noiseless(qc, m["logical_to_physical"], args.dry_shots, DRY_SEED + 100 + i)
        rec = dict(m)
        rec.update({"counts": counts,
                    "counts_key_convention": ("qiskit counts key: the RIGHTMOST character is classical bit "
                                              "0 = logical qubit 0 (skqd.reference_sim.qiskit_key_to_bits)"),
                    "shots": int(args.dry_shots), "backend_manifest": m.get("backend"),
                    "backend": "noiseless exact sampling of the frozen circuit (Aer statevector on the active qubits)",
                    "dry_run": True, "job_id": f"local-noiseless-seed{DRY_SEED + 100 + i}",
                    "sampler_options": None, "submitted": now(), "retrieved": now(), "usage_s": None,
                    "noiseless_norm_on_logical_strings": norm, "n_active_qubits": info["n_active"]})
        with open(path, "w") as fh:
            json.dump(rec, fh, indent=1)
        entries.append({"circuit_id": m["id"], "shots": int(args.dry_shots), "seed": DRY_SEED + 100 + i,
                        "norm": norm, "seconds": time.time() - t1})
        print(f"  {m['id']}: {args.dry_shots} noiseless shots ({time.time() - t1:.0f} s)", flush=True)
    sess["noiseless_coarse_path_check"] = {
        "added_by": "scripts/gate_K1_2x3_fpilot.py --stage dryrun", "created": now(), "entries": entries,
        "readout_pubs_through_h0_submit_s": t_a, "design": DRY_RUN_DESIGN,
        "noisy_cost_measured": (load_json(p(DATA, "noisy_shot_timing.json"))
                                if os.path.exists(p(DATA, "noisy_shot_timing.json")) else None)}
    dump_json(sess, sess_path)
    print(f"dry run written to {rel(outdir)} in {time.time() - t0:.0f} s")
    return 0


def _noisy_one_shot(prep, cid, outpath):
    """Child process of stage noisy-timing: one shot of one frozen coarse pub through the dry-run sampler
    of h0_submit.py (SamplerV2 on AerSimulator.from_backend(FakeKingston), seed 11)."""
    from gate_H0P import load_circuit, load_manifests
    from h0_backends import resolve_backend
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime import SamplerV2
    cm, _c = load_manifests(p(prep))
    m = next(x for x in cm if x["id"] == cid)
    qc = load_circuit(p(prep), m)
    sim = AerSimulator.from_backend(resolve_backend("FakeKingston"), seed_simulator=DRY_SEED)
    t0 = time.time()
    SamplerV2(mode=sim).run([(qc,)], shots=1).result()
    dump_json({"circuit": cid, "shots": 1, "seconds": time.time() - t0, "completed": True}, outpath)


def stage_noisy_timing(args):
    """Measure the cost of ONE noisy shot of the first coarse pub on the dry-run sampler, under a
    wall-clock cap (the 30-minute rule): the evidence for DRY_RUN_DESIGN."""
    from gate_H0P import load_manifests
    cm, _c = load_manifests(p(args.prep))
    cid = sorted(m["id"] for m in cm)[0]
    tmp = p(DATA, "noisy_shot_timing_child.json")
    if os.path.exists(tmp):
        os.remove(tmp)
    code = (f"import sys; sys.path.insert(0, {os.path.join(ROOT, 'scripts')!r}); "
            f"sys.path.insert(0, {os.path.join(ROOT, 'src')!r}); import gate_K1_2x3_fpilot as K1; "
            f"K1._noisy_one_shot({args.prep!r}, {cid!r}, {tmp!r})")
    t0 = time.time()
    try:
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, timeout=args.noisy_timeout,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        child = load_json(tmp) if os.path.exists(tmp) else None
    except subprocess.TimeoutExpired:
        child = None
    wall = time.time() - t0
    m = next(x for x in cm if x["id"] == cid)
    out = {"created": now(), "commit": git_commit(), "prep": args.prep,
           "record_fingerprint_full": m.get("record_fingerprint_full"),
           "circuit": cid, "n_active_qubits": m["exactness"]["n_active"],
           "sampler": "qiskit_ibm_runtime.SamplerV2(AerSimulator.from_backend(FakeKingston), seed 11) -- h0_submit's dry-run path",
           "shots": 1, "timeout_s": args.noisy_timeout, "completed": bool(child and child.get("completed")),
           "seconds_one_shot": (child or {}).get("seconds"), "wall_s_including_setup": wall,
           "machine": "laptop i7-8750H, 6 cores / 12 threads, 62 GiB",
           "reading": ("one noisy shot of one coarse pub did not finish inside the cap" if not child else
                       "one noisy shot of one coarse pub, measured")}
    dump_json(out, p(DATA, "noisy_shot_timing.json"))
    if os.path.exists(tmp):
        os.remove(tmp)
    print(json.dumps(out, indent=1))
    return 0


# --------------------------------------------------------------------------- submit (preconditions)
def preconditions(prep, prereg_path):
    """Every precondition of the coordinator's ruling 2, evaluated now; returns (ok, record)."""
    import h0_kpilot_circuits as KP
    rec_out, problems = {}, []
    if not os.path.exists(p(OWNER_DECISION)):
        problems.append(f"the owner decision file {OWNER_DECISION} does not exist")
    info = load_json(p(prep, "live.json"))
    k0 = load_json(p(K0_JSON))
    k0_live = (k0["data"].get("records") or {}).get("live") or {}
    rec_out["k0"] = {"status": k0["status"], "live_fingerprint": k0_live.get("fingerprint"),
                     "day_record_fingerprint": info["record"]["fingerprint"]}
    rec_out["k0"]["live_usable"] = k0_live.get("usable")
    if (k0["status"] != "PASS" or not k0_live.get("usable")
            or k0_live.get("fingerprint") != info["record"]["fingerprint"]):
        problems.append("gate K0 has not PASSED on the day's record")
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", prereg_path], cwd=ROOT, capture_output=True).returncode == 0
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", prereg_path], cwd=ROOT).returncode != 0
    rec_out["prereg"] = {"path": prereg_path, "committed": tracked, "modified_since_commit": dirty}
    if not tracked or dirty:
        problems.append(f"the preregistration {prereg_path} is not committed as it stands")
    dry = p("validation", "K1_2x3_fpilot_dryrun.json")
    dstat = load_json(dry)["status"] if os.path.exists(dry) else None
    rec_out["dry_run_status"] = dstat
    if dstat != "PASS":
        problems.append("validation/K1_2x3_fpilot_dryrun.json is not PASS")
    pre = load_json(p(prereg_path))
    est = pre["execution_estimate"]["total_execution_s"]
    rec_out["estimate_s"] = est
    if est > MAX_ESTIMATE_S:
        problems.append(f"the execution estimate {est:.1f} s > {MAX_ESTIMATE_S:.0f} s")
    cw = subprocess.run([sys.executable, os.path.join("scripts", "h0_calwatch.py"), "--backend", DEVICE, "--once",
                         "--reference", pre["calibration"]["path"], "--prep", prep,
                         "--out", os.path.join(prep, "calibration_watch.jsonl")], cwd=ROOT,
                        capture_output=True, text=True)
    rec_out["calwatch"] = {"returncode": cw.returncode, "tail": cw.stdout.strip().splitlines()[-2:]}
    if cw.returncode != 0:
        problems.append("calwatch: the live calibration content of the patch is not the preregistered one (D9)")
    acct = KP.account_snapshot()
    rem = (acct.get("usage") or {}).get("usage_remaining_seconds")
    rec_out["account"] = {"usage": acct.get("usage"), "backend": acct.get("backend")}
    if rem is None or float(rem) < MAX_BILLED_S:
        problems.append(f"usage remaining {rem} s < the {MAX_BILLED_S:.0f} s cap")
    if not (acct.get("backend") or {}).get("operational"):
        problems.append(f"{DEVICE} is not operational")
    ck = subprocess.run([sys.executable, os.path.join("scripts", "ibm_account.py"), "--check", "--prep", prep],
                        cwd=ROOT, capture_output=True, text=True)
    usable = [ln for ln in ck.stdout.splitlines() if ln.strip().startswith("usable as frozen")]
    rec_out["ibm_account_check"] = {"returncode": ck.returncode, "usable_line": usable,
                                    "kingston_ok": any(DEVICE in ln for ln in usable)}
    if not rec_out["ibm_account_check"]["kingston_ok"]:
        problems.append("ibm_account.py --check does not list ibm_kingston as usable for the frozen set")
    rec_out["problems"] = problems
    rec_out["checked"] = now()
    return not problems, rec_out


def stage_submit(args):
    if not args.live:
        raise SystemExit("--stage submit needs --live (the one QPU spend of this gate)")
    if not os.path.exists(p(OWNER_DECISION)):
        raise SystemExit(f"refused: {OWNER_DECISION} does not exist")
    prep = args.prep
    prereg = find_prereg(prep, args.prereg)
    ok, rec = preconditions(prep, prereg)
    dump_json(rec, p(prep, f"preconditions_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"))
    for k, v in rec.items():
        print(f"  {k}: {v}")
    if not ok:
        print("STOP: preconditions not met -- nothing submitted:")
        for x in rec["problems"]:
            print(f"   x {x}")
        return 3
    out = args.out or OUT_LIVE
    cmd = [sys.executable, os.path.join("scripts", "h0_submit.py"), "--backend", DEVICE, "--prep", prep,
           "--out", out, "--shots", str(SHOTS), "--cal-shots", str(CAL_SHOTS), "--dd", "off", "--twirling", "off",
           "--prereg", prereg, "--max-qpu-seconds", f"{MAX_ESTIMATE_S:.0f}", "--max-pubs-per-job", "4",
           "--job-tags", "K1_2x3_fpilot"]
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


# --------------------------------------------------------------------------- assemble
def decode_circuit(counts, man, codec):
    """Reference hits, accepted count (decoded into the circuit's sector) and the round-trip check
    of every accepted string, from {bit tuple: count}."""
    from skqd.codec import Reject
    ref = tuple(int(x) for x in man["reference_bits"])
    n_ref = int(sum(v for b, v in counts.items() if tuple(b) == ref))
    acc, bad, distinct = 0, [], 0
    for bits, v in counts.items():
        try:
            idx, label = codec.decode(bits, man["twoB"])
        except Reject:
            continue
        distinct += 1
        acc += int(v)
        if tuple(codec.encode(label)) != tuple(bits):
            bad.append("".join(map(str, bits)))
    return {"reference_hits": n_ref, "accepted": acc, "shots": int(sum(counts.values())),
            "distinct_accepted_strings": distinct, "roundtrip_mismatches": len(bad), "roundtrip_examples": bad[:5]}


def stage_assemble(args):
    import h0_kpilot_circuits as KP  # noqa: F401
    import gate_H0_kpilot as GK
    from gate_H0 import read_counts_dir
    from gate_H0P import DIAG_MIN
    from h0_backends import calibration_diff
    from scipy.stats import poisson

    from skqd.report import GateResult, write_report
    from skqd.skqd import READOUT_FACTOR, pooled_reference_string_test, reference_string_test
    t0 = time.time()
    dry = bool(args.dry_run)
    gate = args.gate_name or ("K1_2x3_fpilot_dryrun" if dry else "K1_2x3_fpilot")
    prep = args.prep
    pre_path = find_prereg(prep, args.prereg)
    pre = load_json(p(pre_path))
    missing_keys = GK.prereg_keys_ok(pre)
    from gate_H0P import load_manifests
    cm, cals = load_manifests(p(prep))
    mans = {m["id"]: m for m in cm + cals}
    index = load_json(p(prep, "index.json"))
    union = index["readout_union"]
    cdir = p(args.counts) if not os.path.isabs(args.counts) else args.counts
    records = read_counts_dir(cdir)
    spath = os.path.join(os.path.dirname(os.path.normpath(cdir)), "session.json")
    session = load_json(spath) if os.path.exists(spath) else None
    GK.check_mixing(dry, session, records)
    by_id = {m["id"]: (m, c) for m, c in records}
    P = physics()
    rnc, _rd = r_nc()
    coarse = sorted(m["id"] for m in cm)

    # ---- readout (K3)
    c0, c1 = by_id["cal_patch_all0"][1], by_id["cal_patch_all1"][1]
    p00, p11, s0, s1 = readout_from_cal(c0, c1, len(union))
    diag_min = float(min(min(p00), min(p11)))
    ro = {"qubits": union, "P_0_given_0": p00, "P_1_given_1": p11, "shots": [s0, s1], "min_diagonal": diag_min,
          "min_qubit": int(union[int(np.argmin([min(a, b) for a, b in zip(p00, p11)]))]),
          "survival_product": float(np.prod([0.5 * (a + b) for a, b in zip(p00, p11)]))}
    dry_k3 = None
    if dry:
        model = GK.snapshot_readout_model(index["common"]["backend"], union)
        meas = {int(q): (p00[i], p11[i]) for i, q in enumerate(union)}
        k3ok, k3rows = GK.dry_k3(meas, model, s0)
        dry_k3 = {"ok": k3ok, "per_qubit": k3rows, "shots": s0, "sigma_k": 3.0,
                  "model": f"NoiseModel.from_backend({index['common']['backend']}) local readout errors"}

    # ---- per circuit and pooled
    circ, rows68 = {}, []
    for cid in coarse:
        m, counts = by_id[cid]
        man = mans[cid]
        d = decode_circuit(counts, man, P["codec"])
        row = [d["reference_hits"], d["shots"], man["p_reference"], man["garbage_acceptance"], man["dim"]]
        r68 = reference_string_test(*row, conf=CONF68)
        r95 = reference_string_test(*row, conf=CONF95)
        f_hit, f68, f95 = r68["f_clean"], r68["f_clean_68"], r95["f_clean_68"]
        circ[cid] = {**d, "p_reference": man["p_reference"], "dim": man["dim"],
                     "garbage_acceptance": man["garbage_acceptance"],
                     "expected_from_garbage": r68["expected_from_garbage"], "z": r68["z"], "P_ge": r68["P_ge"],
                     "f_hit": f_hit, "f_hit_68": f68, "f_hit_95": f95,
                     "f_hat_ideal": ideal_of(f_hit, rnc), "f_hat_ideal_95": [ideal_of(x, rnc) for x in f95],
                     "f_hat_ideal_68": [ideal_of(x, rnc) for x in f68],
                     "accepted_yield": d["accepted"] / d["shots"] if d["shots"] else None,
                     "row": row, "prediction": pre["circuits"].get(cid)}
        rows68.append(row)
    p68 = pooled_reference_string_test(rows68, conf=CONF68)
    p95 = pooled_reference_string_test(rows68, conf=CONF95)
    f_hit = p68["f_clean"]
    f_ideal = ideal_of(f_hit, rnc)
    f_ideal_95 = [ideal_of(x, rnc) for x in p95["f_clean_68"]]
    decision, classes, firm = decide(f_ideal, f_ideal_95)
    n_hits = int(sum(r[0] for r in rows68))
    exp_g = float(p68["expected_from_garbage"])
    pooled = {"reference_hits": n_hits, "shots": p68["shots"], "expected_from_garbage": exp_g,
              "P_hits_ge_observed_from_garbage_alone": float(poisson.sf(n_hits - 1, exp_g)) if exp_g > 0 else None,
              "z": p68["z"], "excess": p68["excess"], "clean_denominator": p68["clean_denominator_shots_x_p_ref"],
              "f_hit": f_hit, "f_hit_68": p68["f_clean_68"], "f_hit_95": p95["f_clean_68"],
              "f_hat_ideal": f_ideal, "f_hat_ideal_68": [ideal_of(x, rnc) for x in p68["f_clean_68"]],
              "f_hat_ideal_95": f_ideal_95, "readout_factor": READOUT_FACTOR, "r_nc": rnc}
    dec = {"dry_run": dry, "statistic": "f_hat_ideal = f_hit / r_nc", "decision": decision, "classes": classes,
           "firm": firm, "f_hat_ideal": f_ideal, "f_hat_ideal_95": f_ideal_95, "f_hit": f_hit,
           "f_hit_95": p95["f_clean_68"], "thresholds": {"GO-B": GO_B, "GO-A": GO_A}, "r_nc": rnc,
           "r_nc_note": R_NC_NOTE, "rule": DECISION_RULE}

    # ---- live block
    usage_s, job_ids, statuses = None, [], []
    if session:
        jobs = [j for j in session.get("jobs", []) if j.get("job_id")]
        job_ids = [j["job_id"] for j in jobs]
        statuses = [j.get("status") for j in jobs]
        us = [j.get("usage_s") for j in jobs if j.get("usage_s") is not None]
        usage_s = float(sum(us)) if us else None
    ret_fp = (session or {}).get("retrieval_calibration_fingerprint")
    ret_diff = None
    prereg_rec = load_json(pre["calibration"]["path"])
    if ret_fp and ret_fp != pre["calibration"]["fingerprint"] and (session or {}).get("retrieval_calibration_file"):
        dd = calibration_diff(prereg_rec, load_json(session["retrieval_calibration_file"]))
        ret_diff = {k: dd[k] for k in ("n_leaves", "families", "max_ratio", "min_ratio")}
    acct = {}
    for lab, pat in (("after", os.path.join(os.path.dirname(os.path.normpath(cdir)), "account_check_after_*.json")),):
        fs = sorted(glob.glob(pat))
        if fs:
            a = load_json(fs[-1])
            acct[lab] = {"file": rel(fs[-1]), "usage": a.get("usage"), "backend": a.get("backend")}
    acct["at_prediction"] = pre.get("account")

    R_ = GateResult(gate, ("the 2x3 clean-fraction pilot on ibm_kingston: two signed k = 1 circuits (largest p_ref per "
                           "sector), routed as gate K0, ALAP + client XY4 (T3), 1e5 shots each, read by the preregistered "
                           "GO-B / GO-A / NO-GO rule on f_hat_ideal = f_hit / r_nc (measurement gate)")
                    + (" -- DRY RUN (path check)" if dry else ""))
    k1_info = {}
    if dry:
        R_.add("K1 preregistration before data", "n/a (dry run)", "device run only", True)
        R_.add("K2 one job DONE, usage <= 300 s, estimate <= 300 s, 4 counts files x 1e5 shots, DD/twirling off",
               "n/a (dry run)", "device run only", True)
    else:
        sub = (session.get("jobs") or [{}])[0].get("submitted")
        h, tc = GK.git_commit_time(pre["commit"])
        ha, ta = GK.git_added(pre_path)
        fp_ok = (session.get("prereg_calibration_fingerprint") == pre["calibration"]["fingerprint"]
                 == session.get("calibration_fingerprint"))
        before = (tc is not None and sub is not None and GK._utc(tc) < GK._utc(sub)
                  and ta is not None and GK._utc(ta) < GK._utc(sub))
        k1_info = {"prereg_commit": pre["commit"], "prereg_commit_full": h, "prereg_commit_time": tc,
                   "prereg_added_in": ha, "prereg_added_time": ta, "submitted": sub, "fingerprints_equal": fp_ok,
                   "retrieval_fingerprint": ret_fp,
                   "retrieval_match": (None if ret_fp is None else ret_fp == pre["calibration"]["fingerprint"]),
                   "retrieval_diff": ret_diff}
        R_.add("K1 preregistration committed before the submission; prereg = session = submission fingerprint; "
               "retrieval fingerprint recorded (a move is information)",
               f"prereg added {ha and ha[:7]} {ta}, submitted {sub}; fingerprints equal {fp_ok}; retrieval match "
               f"{k1_info['retrieval_match']}", "commit < submission, equal fingerprints, retrieval recorded",
               before and fp_ok and ret_fp is not None and not missing_keys)
        est = ((session.get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s")
        so = session.get("sampler_options") or {}
        opts_ok = (so.get("dynamical_decoupling") == {"enable": False}
                   and so.get("twirling") == {"enable_gates": False, "enable_measure": False})
        shots_ok = (len(records) == len(coarse) + 2
                    and all(int(sum(c.values())) == (SHOTS if m["kind"] == "coarse_step" else CAL_SHOTS)
                            for m, c in records))
        k2 = (len(job_ids) == 1 and statuses == ["DONE"] and usage_s is not None and usage_s <= MAX_BILLED_S
              and est is not None and est <= MAX_ESTIMATE_S and shots_ok and opts_ok)
        R_.add("K2 one job DONE, usage_s <= 300, preflight estimate <= 300 s, 4 counts files x 1e5 shots, DD off and "
               "twirling off", f"jobs {job_ids} {statuses}, usage {usage_s} s, estimate {_f(est, '{:.2f}')} s, counts ok "
               f"{shots_ok}, options off {opts_ok}", "all hold", k2)
    if dry:
        nz = sum(1 for v in (dry_k3 or {}).get("per_qubit", {}).values()
                 if abs(v["d00"]["z"]) <= 3 and abs(v["d11"]["z"]) <= 3)
        R_.add("K3 readout (dry run: agreement with the snapshot's readout model within 3 binomial sigma, the prompts/21a "
               "form; the device criterion >= 0.9 is evaluated only on device counts)",
               f"{nz}/{len(union)} qubits within 3 sigma; min diagonal {diag_min:.4f} (information)",
               "all within 3 sigma", bool(dry_k3 and dry_k3["ok"]))
    else:
        R_.add("K3 readout confusion of the measured qubits (all-0 / all-1 pubs): smallest diagonal",
               round(diag_min, 4), f">= {DIAG_MIN}", GK.device_k3(diag_min))
    mism = sum(c["roundtrip_mismatches"] for c in circ.values())
    R_.add("K4 decoder round trip over every accepted string of the coarse pubs",
           f"{mism} mismatches over {sum(c['distinct_accepted_strings'] for c in circ.values())} strings", "0", mism == 0)
    k5 = {}
    for cid in coarse:
        m = mans[cid]
        ex, chk = m["exactness"], m["dd"]["checks"]
        k5[cid] = bool(ex["ok"] and ex["max_abs_delta"] < AMP_TOL and ex["leakage"] < LEAK_TOL
                       and m["exactness_base"]["ok"] and (m.get("schedule_info") or {}).get("method") == "alap"
                       and m["schedule_checks"]["k0_4_ok"] and chk.get("ok") is True and chk.get("ops") == m["ops"]
                       and set(m["ops"]) <= {"rz", "sx", "x", "cz", "delay", "measure", "barrier"}
                       and m["dd"]["cell"] == CELL)
    R_.add("K5 circuits: exactness vs the exact Krylov state (< 1e-10, leakage < 1e-9) before and after T3, ALAP with no "
           "moved op and duration = unscheduled T_total, DD statevector = base, no pulses in leading / trailing windows, "
           "kingston basis", f"{sum(k5.values())}/{len(k5)}; max |d| "
           f"{max(mans[c]['exactness']['max_abs_delta'] for c in coarse):.1e}, max leak "
           f"{max(mans[c]['exactness']['leakage'] for c in coarse):.1e}", "all hold", all(k5.values()))
    if dry:
        R_.add("K6 dry-run gate PASS", "n/a (this is the dry run)", "device run only", True)
        kd = {}
        for cid in coarse:
            c, man = circ[cid], mans[cid]
            pu = float(man["p_reference"]) * float(man["sector_mass"])
            sig = math.sqrt(c["shots"] * pu * (1.0 - pu))
            z = (c["reference_hits"] - c["shots"] * pu) / sig if sig > 0 else 0.0
            kd[cid] = {"p_reference_unnormalised": pu, "z": z, "accepted_all": c["accepted"] == c["shots"],
                       "ok": abs(z) <= 3.0 and c["accepted"] == c["shots"]}
        lo, hi = (x * READOUT_FACTOR for x in p95["f_clean_68"])
        kd_pool = bool(lo <= 1.0 <= hi)
        R_.add("KD noiseless path check of the coarse pubs: every shot accepted into its sector, reference hits within 3 "
               "binomial sigma of N p_ref, pooled 0.82 x f_hit 95 % interval contains 1 (a clean run)",
               "; ".join(f"{c}: z {v['z']:.2f}, all accepted {v['accepted_all']}" for c, v in kd.items())
               + f"; 0.82 f_hit 95 % [{lo:.3f}, {hi:.3f}]", "all hold",
               all(v["ok"] for v in kd.values()) and kd_pool)
    else:
        dp = p("validation", "K1_2x3_fpilot_dryrun.json")
        dg = load_json(dp)["status"] if os.path.exists(dp) else None
        R_.add("K6 dry-run gate validation/K1_2x3_fpilot_dryrun.json PASS", dg, "PASS", dg == "PASS")
    re_dec, _c, _f2 = decide(ideal_of(pooled_reference_string_test(rows68, conf=CONF68)["f_clean"], rnc),
                             [ideal_of(x, rnc) for x in pooled_reference_string_test(rows68, conf=CONF95)["f_clean_68"]])
    complete = all(v is not None for v in (f_hit, f_ideal, f_ideal_95[0], f_ideal_95[1], decision))
    R_.add("K7 data.decision complete and the decision recomputed from the recorded rows",
           f"complete {complete}; decision {decision} (recomputed {re_dec})", "complete and equal",
           complete and re_dec == decision)
    if args.skip_tests:
        checks = {"skipped": True, "ok": None}
        R_.add("K8 pytest -q tests and scripts/check_package.py", "n/a (--skip-tests)", "all pass", dry)
    else:
        import gate_S2D_levers as G
        checks = G.run_checks(False)
        R_.add("K8 pytest -q tests and scripts/check_package.py",
               f"pytest: {checks.get('pytest_summary')}; check_package rc {checks.get('check_package_returncode')}",
               "all pass", checks["ok"])
    R_.data = {
        "what_pass_means": ("preregistered, measured, verified, consistent; there is no criterion on f or on the "
                            "decision (a NO-GO pilot is a PASS gate)"),
        "dry_run": dry, "versions": versions(), "prereg": pre_path, "prereg_created": pre["created"],
        "prereg_commit": pre["commit"], "prereg_keys_missing": missing_keys,
        "calibration_prereg": pre["calibration"], "patch": union, "pubs": pre["pubs"],
        "execution_estimate_prereg_s": pre["execution_estimate"]["total_execution_s"],
        "counts_dir": rel(cdir), "session_file": rel(spath) if session else None,
        "live": {"job_ids": job_ids, "statuses": statuses, "usage_s": usage_s,
                 "submission_fingerprint": (session or {}).get("calibration_fingerprint"),
                 "prereg_fingerprint_match": (session or {}).get("prereg_fingerprint_match"),
                 "retrieval_fingerprint": ret_fp, "retrieval_diff": ret_diff,
                 "preflight_estimate_s": (((session or {}).get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s"),
                 "sampler_options": (session or {}).get("sampler_options"), "account": acct, "K1": k1_info},
        "readout": ro, "dry_run_K3": dry_k3, "circuits": circ, "pooled": pooled, "decision": dec,
        "prediction_prereg": {cid: pre["circuits"][cid] for cid in coarse},
        "dry_run_note": ("a PATH CHECK, not a prediction: local Aer on the FakeKingston snapshot "
                         "(AerSimulator.from_backend through h0_submit.py's dry-run path) at a few shots per coarse pub "
                         "under the 30-minute rule; its f numbers carry no information about the device") if dry else None,
        "checks": checks,
    }
    R_.runtime_s = time.time() - t0
    path = R_.save()
    saved = load_json(path)
    write_report(f"{gate}.md", report_text(saved, R_))
    print(R_.criteria_table())
    print(f"status {saved['status']}; pooled hits {n_hits} vs garbage {exp_g:.3f}; f_hit {_f(f_hit, '{:.3e}')} "
          f"{_iv(p95['f_clean_68'])}; f_hat_ideal {_f(f_ideal, '{:.3e}')} {_iv(f_ideal_95)}; decision {decision} "
          f"(firm {firm})")
    return 0 if saved["status"] == "PASS" else 1


def report_text(saved, R_):
    from skqd.report import md_table
    D = saved["data"]
    dec, po, live = D["decision"], D["pooled"], D["live"]
    k1 = live.get("K1") or {}
    rows = []
    for cid, c in D["circuits"].items():
        rows.append([cid, c["shots"], c["accepted"], c["reference_hits"], f"{c['expected_from_garbage']:.3f}",
                     _f(c["P_ge"], "{:.3g}"), f"{_f(c['f_hit'], '{:.3e}')} {_iv(c['f_hit_95'])}",
                     f"{_f(c['f_hat_ideal'], '{:.3e}')} {_iv(c['f_hat_ideal_95'])}"])
    prow = []
    for cid, c in D["prediction_prereg"].items():
        for k, v in c["f_bracket"].items():
            prow.append([cid, k, f"{v:.3e}", f"{c['expected_reference_hits'][k]:.3g}"])
    ro = D["readout"]
    acct = live.get("account") or {}
    ua = ((acct.get("after") or {}).get("usage") or {})
    title = "dry run (path check on the FakeKingston snapshot)" if D["dry_run"] else "ibm_kingston"
    return f"""# Gate {saved['gate']} -- the 2x3 clean-fraction pilot, {title}

**Status: {saved['status']}** -- `scripts/gate_K1_2x3_fpilot.py --stage assemble --counts {D['counts_dir']}{' --dry-run' if D['dry_run'] else ''}`.
Runtime {saved['runtime_s']:.0f} s.  Every number below is computed by the script from the raw counts and from `{D['prereg']}`
and is stored in `validation/{saved['gate']}.json`.  Prompt in force: `prompts/27_2x3_substantial_result_strategy.md`
stage 0b; owner decision `data/owner_decision_20261005_k1_2x3_fpilot.md`.

## 0. What PASS means

{D['what_pass_means']}.{(' ' + D['dry_run_note'] + '.') if D.get('dry_run_note') else ''}

## 1. Live block

| item | value |
|---|---|
| job id(s) / status | {live['job_ids']} / {live['statuses']} |
| usage (s) | {live['usage_s']} |
| preflight estimate (s) | {live['preflight_estimate_s']} (preregistered {D['execution_estimate_prereg_s']:.2f}) |
| fingerprint at prereg / submission / retrieval | `{D['calibration_prereg']['fingerprint'][:16]}` / `{(live['submission_fingerprint'] or 'n/a')[:16]}` / `{(live['retrieval_fingerprint'] or 'n/a')[:16]}` |
| prereg match at submission / retrieval | {live['prereg_fingerprint_match']} / {k1.get('retrieval_match')} |
| retrieval diff | {live['retrieval_diff']} |
| prereg added / submitted | {k1.get('prereg_added_in')} {k1.get('prereg_added_time')} / {k1.get('submitted')} |
| account after | {ua.get('usage_consumed_seconds')} s used, {ua.get('usage_remaining_seconds')} s left |
| sampler options | {live['sampler_options']} |

## 2. Reference hits and the clean fraction

{md_table(["circuit", "shots", "accepted", "reference hits", "garbage expectation N a/dim", "P(>= hits | garbage)",
           "f_hit [95 %]", "f_hat_ideal [95 %]"], rows)}

Pooled over the two circuits: **{po['reference_hits']} reference hits against {po['expected_from_garbage']:.3f} expected from
garbage** (P(>= observed | garbage only) = {_f(po['P_hits_ge_observed_from_garbage_alone'], '{:.3g}')}); f_hit =
{_f(po['f_hit'], '{:.3e}')} (68 % {_iv(po['f_hit_68'])}, 95 % {_iv(po['f_hit_95'])}); f_hat_ideal = f_hit / r_nc =
{_f(po['f_hat_ideal'], '{:.3e}')} (95 % {_iv(po['f_hat_ideal_95'])}), r_nc = {po['r_nc']:.4f}.

## 3. Decision (preregistered)

**{dec['decision']}** (point class {dec['classes']['point']}; 95 % ends {dec['classes']['lo95']} / {dec['classes']['hi95']};
firm: {dec['firm']}).  Rule: {dec['rule']}

{dec['r_nc_note']}

## 4. The preregistered prediction bracket

{md_table(["circuit", "f end", "f", "expected reference hits"], prow)}

## 5. Readout

Smallest confusion diagonal {ro['min_diagonal']:.4f} (qubit {ro['min_qubit']}) over the {len(ro['qubits'])} measured qubits;
survival product {ro['survival_product']:.4f}.

## 6. Honest limits

- Two circuits, one calibration content, one job: the number is a pilot reading for this day's patch, not a device constant.
- The XY4 entries of the bracket are a 2x2 transfer; the f_hit statistic counts near-clean shots as well as clean ones
  (gate CF_traj), which the r_nc division corrects for gate noise only.
- At the expected f the counts are dominated by Poisson noise on a handful of hits; the 95 % interval, not the point, says
  what the data exclude.

## 7. Criteria

{R_.criteria_table()}
"""


STAGES = {"select": stage_select, "record": stage_record, "build": stage_build, "patchcal": stage_patchcal,
          "predict": stage_predict, "prereg-md": stage_prereg_md, "dryrun": stage_dryrun, "submit": stage_submit,
          "noisy-timing": stage_noisy_timing,
          "assemble": stage_assemble}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--prep", default=PREP)
    ap.add_argument("--record", default=None, help="record: the day's full record (default: K0's live record)")
    ap.add_argument("--prereg", default=None)
    ap.add_argument("--counts", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dry-shots", type=int, default=DRY_SHOTS_DEFAULT)
    ap.add_argument("--dry-cal-shots", type=int, default=DRY_CAL_SHOTS_DEFAULT)
    ap.add_argument("--gate-name", default=None)
    ap.add_argument("--noisy-timeout", type=float, default=1500.0, help="noisy-timing: wall-clock cap (s)")
    ap.add_argument("--live", action="store_true", help="submit: the one QPU spend (owner decision file required)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", default=None, help="build: only these circuit ids in this invocation")
    ap.add_argument("--skip-tests", action="store_true")
    # stage_patchcal (h0_ddtest_circuits) reads these
    ap.add_argument("--after", action="store_true")
    ap.add_argument("--min-remaining", type=float, default=MAX_BILLED_S)
    ap.add_argument("--diff-against", default=None)
    args = ap.parse_args()
    return STAGES[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
