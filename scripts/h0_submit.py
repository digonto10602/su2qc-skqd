#!/usr/bin/env python3
"""
The H0 submission path (prompts/07 step 2, split into phases by prompts/15 step A3).

Builds the SamplerV2 job(s) for the frozen circuit set of `scripts/h0_build_circuits.py`
with **dynamical decoupling and Pauli twirling enabled and no error mitigation**: SKQD
needs raw bit strings, so nothing that rewrites outcomes (resilience levels, readout
mitigation of expectation values) is switched on.  Measurement twirling is a bit flip
before the measurement that the runtime undoes classically, so it leaves the bit strings
interpretable; it is enabled and recorded in the session JSON.

Phases (prompts/15 D4 -- the raw counts are the one artefact of this project that cannot
be recomputed, so the pointers to them are written to disk before anything can be lost):

  --submit [--backend <name>]   preflight, then submit every group back-to-back so the
                                jobs queue in parallel; each job id is written to
                                <out>/session.json BEFORE the next submission.  Nothing
                                blocks on a result.  --resume submits only the groups
                                that have no job id yet.
  --retrieve [--wait S]         re-attaches to the job ids with
                                QiskitRuntimeService.job(<id>), polls every 30 s for up
                                to S seconds (S <= 1500, so one invocation respects the
                                30-minute rule) and turns finished jobs into counts files.
  --status                      refreshes status / usage of every job and prints them.
  --dry-run                     runs the same jobs on `AerSimulator.from_backend(<snapshot>)`
                                through the same SamplerV2 code path (local testing mode)
                                and writes the counts through the same function.  Local
                                jobs have no server-side ids, so --retrieve refuses them.

Counts are written to `<out>/counts/<circuit id>.json`, one file per circuit, each
carrying the manifest of the circuit it came from.  They are RAW DATA: the script
refuses to overwrite an existing file and --retrieve skips the ones that exist.

prompts/19 adds three flags for the diagnostic session, whose DEFAULTS reproduce the
production path (prompts/15 D8) exactly -- `tests/test_h0_scripts.py` pins the default
options record against the canary job's own record, field for field:

  --dd {XY4,XX,XpXm,off}   dynamical decoupling (default XY4; `--dd-sequence` is an alias)
  --twirling {on,off}      gate and measurement twirling (default on, `active-accum`)
  --prereg <json>          an `h0_idle_model.py` output: the preflight refuses to submit
                           unless the LIVE calibration fingerprint is the one the
                           predictions were written on (the D9 predicate, referred to the
                           preregistration instead of the day's H0P prediction, which
                           becomes optional).  `--job-tags` tags the jobs.

Usage: python scripts/h0_submit.py --dry-run [--shots 40] [--out data/hardware/H0_dryrun]
       python scripts/h0_submit.py --backend ibm_fez --shots-by-rep 1:267 2:130 3:92 \\
                                   --cal-shots 4000 --out data/hardware/H0_ibm_fez
       python scripts/h0_submit.py --retrieve --wait 1500 --out data/hardware/H0_ibm_fez
       python scripts/h0_submit.py --status --out data/hardware/H0_ibm_fez
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from gate_H0P import load_circuit, load_index, load_manifests  # noqa: E402
from h0_backends import (calibration_diff, calibration_fingerprint,  # noqa: E402
                         fresh_calibration, frozen_qubits_and_edges, is_fake,
                         last_update_date, resolve_backend)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POLL_S = 30
MAX_WAIT_S = 1500          # one --retrieve invocation stays inside the 30-minute rule
TERMINAL = ("DONE", "ERROR", "CANCELLED", "FAILED")
F_CROSSCHECK_TOL = 1e-9    # h0_support_plan.F_CROSSCHECK_TOL: f identity, not f agreement


# --------------------------------------------------------------------------- options
DD_CHOICES = ("XY4", "XX", "XpXm", "off")
TWIRLING_CHOICES = ("on", "off")


def sampler_options(shots: int, dd_sequence: str = "XY4", twirling: str = "on", job_tags=None):
    """SamplerV2 options: dynamical decoupling and Pauli twirling as asked, no mitigation.

    The defaults reproduce the production path of prompts/15 D8 exactly (DD XY4 on,
    gate and measurement twirling on with strategy `active-accum`, no error mitigation);
    prompts/19 C1 adds `off` for both so that the diagnostic factorial can be run, and
    makes `options_record` report what was actually set instead of hard-coding True."""
    from qiskit_ibm_runtime.options import SamplerOptions

    if dd_sequence not in DD_CHOICES:
        raise SystemExit(f"--dd must be one of {DD_CHOICES}, not {dd_sequence!r}")
    if twirling not in TWIRLING_CHOICES:
        raise SystemExit(f"--twirling must be one of {TWIRLING_CHOICES}, not {twirling!r}")
    o = SamplerOptions()
    o.default_shots = shots
    if dd_sequence == "off":
        o.dynamical_decoupling.enable = False
    else:
        o.dynamical_decoupling.enable = True
        o.dynamical_decoupling.sequence_type = dd_sequence
    if twirling == "off":
        o.twirling.enable_gates = False
        o.twirling.enable_measure = False
    else:
        o.twirling.enable_gates = True
        o.twirling.enable_measure = True
        o.twirling.strategy = "active-accum"
    if job_tags:
        o.environment.job_tags = list(job_tags)
    return o


def options_record(o, shots, dd_sequence, twirling="on"):
    """What the sampler was actually configured with -- field for field, no defaults."""
    if dd_sequence == "off":
        dd = {"enable": False}
    else:
        dd = {"enable": True, "sequence_type": dd_sequence}
    if twirling == "off":
        tw = {"enable_gates": False, "enable_measure": False}
    else:
        tw = {"enable_gates": True, "enable_measure": True, "strategy": "active-accum"}
    return {
        "default_shots": shots,
        "dynamical_decoupling": dd,
        "twirling": tw,
        "error_mitigation": ("none: SamplerV2 returns raw bit strings; no resilience level, no readout "
                             "mitigation of expectation values (prompts/07 step 2)"),
    }


def counts_of(pub_result):
    """{'0101...': n} from a SamplerV2 pub result (single classical register)."""
    db = pub_result.data
    names = list(db.keys()) if hasattr(db, "keys") else [f for f in dir(db) if not f.startswith("_")]
    if len(names) != 1:
        raise RuntimeError(f"expected one classical register, found {names}")
    return getattr(db, names[0]).get_counts()


# --------------------------------------------------------------------------- session state
def session_path(outdir):
    return os.path.join(outdir, "session.json")


def save_session(outdir, session):
    """Atomic: the job ids must survive a process that dies mid-write."""
    path = session_path(outdir)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(session, fh, indent=1)
    os.replace(tmp, path)
    return path


def load_session(outdir):
    path = session_path(outdir)
    if not os.path.exists(path):
        raise SystemExit(f"{path} does not exist: nothing was submitted from this directory")
    with open(path) as fh:
        return json.load(fh)


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


def usage_seconds(job):
    """(seconds, raw) of job.usage(); IBM reports 0 until its accounting completes."""
    try:
        u = job.usage()
    except Exception as exc:
        return None, f"unavailable: {exc}"
    if u is None:
        return None, None
    if isinstance(u, dict):
        for k in ("quantum_seconds", "seconds", "usage_seconds"):
            if u.get(k) is not None:
                return float(u[k]), u
        return None, u
    try:
        return float(u), u
    except Exception:
        return None, str(u)


def job_metrics(job):
    try:
        m = job.metrics()
    except Exception as exc:
        return {"unavailable": str(exc)}
    try:
        json.dumps(m)
        return m
    except Exception:
        return {"repr": str(m)}


def job_status(job):
    try:
        st = job.status()
    except Exception as exc:
        return f"UNKNOWN ({exc})"
    return getattr(st, "name", None) or str(st)


def shot_plan_shots(path):
    """(per-circuit shots, the plan's calibration block, the plan) of a shot-plan JSON."""
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(p) as fh:
        plan = json.load(fh)
    if "shots_by_circuit" not in plan:
        raise SystemExit(f"{path} is not a shot plan of scripts/h0_support_plan.py")
    return ({k: int(v) for k, v in plan["shots_by_circuit"].items()},
            plan.get("calibration") or {}, plan)


# --------------------------------------------------------------------------- job planning
def plan_groups(jobs, max_pubs):
    """[(shots, chunk index, [manifests])]: one group per distinct shot count
    (qiskit-ibm-runtime deprecates mixed shots in one job), chunked by --max-pubs-per-job."""
    groups = {}
    for m, sh in jobs:
        groups.setdefault(sh, []).append(m)
    plan = []
    for sh in sorted(groups):
        batch = groups[sh]
        for ci, start in enumerate(range(0, len(batch), max_pubs)):
            plan.append((sh, ci, batch[start:start + max_pubs]))
    return plan


def write_counts_for_job(cdir, session, entry, mans_by_id, result):
    """The counts files of one finished job, in the format gate_H0.py reads."""
    written, skipped = [], []
    for cid, pub_res in zip(entry["circuit_ids"], result):
        m = mans_by_id[cid]
        path = os.path.join(cdir, cid + ".json")
        if os.path.exists(path):
            skipped.append(cid)
            continue
        counts = counts_of(pub_res)
        rec = dict(m)
        rec.update({
            "counts": {str(k): int(v) for k, v in counts.items()},
            "counts_key_convention": ("qiskit counts key: the RIGHTMOST character is classical bit "
                                      "0 = logical qubit 0 (skqd.reference_sim.qiskit_key_to_bits)"),
            "shots": entry["group_shots"],
            "backend_manifest": m.get("backend"),
            "backend": session["backend"],
            "dry_run": bool(session["dry_run"]),
            "job_id": entry["job_id"], "sampler_options": session["sampler_options"],
            "submitted": entry["submitted"], "retrieved": now(),
            "usage_s": entry.get("usage_s"),
        })
        with open(path, "w") as fh:
            json.dump(rec, fh, indent=1)
        written.append(cid)
    entry["counts_written"] = (len(written) + len(skipped)) == len(entry["circuit_ids"])
    entry["counts_files_written"] = len(written)
    entry["counts_files_skipped_existing"] = len(skipped)
    entry["retrieved"] = now()
    if skipped:
        print(f"  warning: {len(skipped)} counts file(s) already existed and were kept "
              f"(raw data are never overwritten): {skipped[:3]}", flush=True)
    return written, skipped


# --------------------------------------------------------------------------- calibration gate
def calibration_gate(live_record, prediction, plan=None, f_live_by_circuit=None,
                     prediction_record=None, tol=F_CROSSCHECK_TOL):
    """Rule D9 of prompts/17: may these jobs be submitted on THIS calibration?

    The predicate is identity of the calibration CONTENT of the frozen patch -- the 30 x 9
    qubit leaves and 54 x 4 edge leaves the prediction reads -- with no tolerance, plus
    identity of the 84 live clean-shot fractions with the plan's and the prediction's to
    `tol`.  The calibration TIMESTAMP is recorded (`stamp_match`) and is never a problem:
    ibm_fez moved it three times in one night without changing one of these numbers
    (prompts/17, diagnosis), and in every such case re-running the prediction is a no-op.

    Pure: it takes the records and returns `(problems, record)`, so it is exercised on the
    committed calibration files in `tests/test_h0_scripts.py`.  `prediction_record` is the
    full record the prediction was made from; when it is None the function tries to load it
    from `prediction.data.calibration.path`, only to describe a refusal (`calibration_diff`).

    Returns (problems, record).  An empty `problems` is the go."""
    problems, rec = [], {}
    live_fp = live_record.get("fingerprint") or calibration_fingerprint(live_record)
    rec["calibration_fingerprint"] = live_fp
    rec["calibration_last_update_date"] = live_record.get("last_update_date")
    rec["calibration_stamp"] = live_record.get("stamp")

    pcal = ((prediction or {}).get("data", {}).get("calibration") or {})
    pred_fp = pcal.get("fingerprint")
    rec["prediction_calibration_fingerprint"] = pred_fp
    rec["prediction_calibration_last_update_date"] = pcal.get("last_update_date")
    rec["prediction_calibration_path"] = pcal.get("path")
    rec["stamp_match"] = (pcal.get("last_update_date") == live_record.get("last_update_date")
                          if pcal.get("last_update_date") else None)
    rec["calibration_diff"] = None
    if prediction is None:
        rec["fingerprint_match"] = None
    elif pred_fp is None:
        rec["fingerprint_match"] = False
        problems.append("the prediction carries no data.calibration.fingerprint: it was made "
                        "before prompts/17 F3.  Re-run gate_H0P.py on the live backend.")
    else:
        rec["fingerprint_match"] = (pred_fp == live_fp)
        if pred_fp != live_fp:
            if prediction_record is None and pcal.get("path"):
                p = pcal["path"] if os.path.isabs(pcal["path"]) else os.path.join(ROOT, pcal["path"])
                if os.path.isfile(p):
                    try:
                        with open(p) as fh:
                            prediction_record = json.load(fh)
                    except Exception:
                        prediction_record = None
            extra = ""
            if prediction_record is not None:
                d = calibration_diff(prediction_record, live_record)
                rec["calibration_diff"] = {k: d[k] for k in
                                           ("n_leaves", "families", "max_ratio", "min_ratio")}
                extra = (f" -- {d['n_leaves']} leaf/leaves moved ({', '.join(d['families']) or 'none'}), "
                         f"ratios {d['min_ratio']} .. {d['max_ratio']}")
            problems.append(
                f"the live calibration of the frozen patch (fingerprint {live_fp[:16]}, "
                f"{live_record.get('last_update_date')}) is not the one the prediction was made "
                f"from ({pred_fp[:16]}, {pcal.get('last_update_date')}){extra}: re-run the "
                f"prediction on this content (prompts/17 D10), commit, and submit again")

    plan_fp = ((plan or {}).get("calibration") or {}).get("fingerprint") if plan else None
    rec["shots_plan_calibration_fingerprint"] = plan_fp
    if plan is not None:
        if plan_fp is None:
            problems.append("the shot plan carries no calibration.fingerprint: it was written "
                            "before prompts/17 F2.  Re-run h0_support_plan.py.")
        elif plan_fp != live_fp:
            problems.append(
                f"the shot plan was built on the calibration fingerprint {plan_fp[:16]}, the live "
                f"target reports {live_fp[:16]}: re-run h0_support_plan.py on this content")

    # the 84 clean-shot fractions: what the prediction and the plan actually consumed
    rec["f_live_vs_plan_max_abs_diff"] = None
    rec["f_live_vs_prediction_max_abs_diff"] = None
    rec["f_live_circuits_checked"] = None if f_live_by_circuit is None else len(f_live_by_circuit)
    if f_live_by_circuit:
        pf = (plan or {}).get("f_by_circuit") or {}
        common = [c for c in f_live_by_circuit if c in pf]
        if plan is not None and common:
            d = max(abs(float(f_live_by_circuit[c]) - float(pf[c])) for c in common)
            rec["f_live_vs_plan_max_abs_diff"] = float(d)
            if d >= tol:
                worst = max(common, key=lambda c: abs(float(f_live_by_circuit[c]) - float(pf[c])))
                problems.append(
                    f"the live clean-shot fraction of {worst} is {f_live_by_circuit[worst]:.9f}, the "
                    f"shot plan sized its shots at {float(pf[worst]):.9f} (max |df| {d:.3e} >= "
                    f"{tol:g} over {len(common)} circuits): the plan is not this calibration's")
        ppc = ((prediction or {}).get("data", {}).get("f_recomputed_on_the_day") or {}).get("per_circuit") or {}
        common = [c for c in f_live_by_circuit if c in ppc and ppc[c].get("f_live") is not None]
        if common:
            d = max(abs(float(f_live_by_circuit[c]) - float(ppc[c]["f_live"])) for c in common)
            rec["f_live_vs_prediction_max_abs_diff"] = float(d)
            if d >= tol:
                worst = max(common, key=lambda c: abs(float(f_live_by_circuit[c]) - float(ppc[c]["f_live"])))
                problems.append(
                    f"the live clean-shot fraction of {worst} is {f_live_by_circuit[worst]:.9f}, the "
                    f"prediction used {float(ppc[worst]['f_live']):.9f} (max |df| {d:.3e} >= {tol:g} "
                    f"over {len(common)} circuits): the prediction is not this calibration's")
    return problems, rec


# --------------------------------------------------------------------------- preflight
def preflight(args, backend, prep, plan, index, outdir=None):
    """Everything that must hold before a single pub goes to the device (prompts/15 A3)."""
    from ibm_account import check_backend, frozen_requirements
    from h0_qpu_time import estimate

    problems, record = [], {}
    record["backend_name"] = backend.name
    if backend.name != args.backend:
        problems.append(f"the service returned backend '{backend.name}' for '{args.backend}'")
    try:
        st = backend.status()
        record["operational"] = bool(st.operational)
        record["pending_jobs"] = int(st.pending_jobs)
        if not st.operational:
            problems.append(f"{backend.name} is not operational ({getattr(st, 'status_msg', '')})")
    except Exception as exc:
        problems.append(f"backend.status() failed: {exc}")
    req = frozen_requirements(prep)
    probs = check_backend(backend, req)
    record["frozen_set_problems"] = probs
    record["frozen_set"] = {"qubits": req["qubits"], "n_edges": len(req["edges"]), "ops": req["ops"]}
    problems += [f"frozen set: {p}" for p in probs]
    largest = max(len(chunk) for _, _, chunk in plan)
    mc = getattr(backend, "max_circuits", None)
    record["max_circuits"] = None if mc is None else int(mc)
    record["largest_chunk"] = largest
    if mc is not None and largest > mc:
        problems.append(f"largest job has {largest} pubs > max_circuits {mc}")

    # ---- prompts/17 D9: the calibration CONTENT of the frozen patch, read fresh here.
    # The record is written to disk BEFORE the decision, so a refusal leaves its evidence.
    qubits, edges = frozen_qubits_and_edges(prep)
    live_record = fresh_calibration(backend, qubits, edges)
    live_date = live_record["last_update_date"]
    record["calibration_last_update_date"] = live_date
    record["calibration_stamp"] = live_record["stamp"]
    record["calibration_fingerprint"] = live_record["fingerprint"]
    record["calibration_missing_errors"] = live_record["missing_errors"]
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        capath = os.path.join(outdir, f"calibration_at_submission_{live_record['stamp']}.json")
        with open(capath, "w") as fh:
            json.dump(live_record, fh, indent=1)
        record["calibration_at_submission_file"] = os.path.relpath(capath, ROOT)
    if live_record["missing_errors"]:
        problems.append(f"{len(live_record['missing_errors'])} target entries of the frozen set "
                        f"carry no error on {backend.name}: f cannot be evaluated today")

    # ---- prompts/19 C3: the PREREGISTRATION.  The predicate is the same one as D9 -- the
    # live calibration content must be the one the predictions were written on -- but the
    # reference is the idle-model file whose numbers were committed before the submission.
    record["prereg"] = args.prereg
    record["prereg_fingerprint"] = None
    record["prereg_fingerprint_match"] = None
    if args.prereg:
        pp = args.prereg if os.path.isabs(args.prereg) else os.path.join(ROOT, args.prereg)
        if not os.path.exists(pp):
            problems.append(f"the preregistration {args.prereg} does not exist: run "
                            f"scripts/h0_idle_model.py --backend {args.backend} first")
        else:
            with open(pp) as fh:
                prereg = json.load(fh)
            pfp = ((prereg.get("calibration") or {}).get("fingerprint"))
            record["prereg_fingerprint"] = pfp
            record["prereg_created"] = prereg.get("created")
            record["prereg_commit"] = prereg.get("commit")
            record["prereg_calibration_last_update_date"] = \
                (prereg.get("calibration") or {}).get("last_update_date")
            if pfp is None:
                problems.append(f"{args.prereg} carries no calibration.fingerprint: it was not "
                                f"written by scripts/h0_idle_model.py")
            else:
                record["prereg_fingerprint_match"] = (pfp == live_record["fingerprint"])
                if pfp != live_record["fingerprint"]:
                    prec = (prereg.get("calibration") or {}).get("path")
                    extra = ""
                    if prec:
                        p = prec if os.path.isabs(prec) else os.path.join(ROOT, prec)
                        if os.path.isfile(p):
                            with open(p) as fh:
                                d = calibration_diff(json.load(fh), live_record)
                            record["prereg_calibration_diff"] = {
                                k: d[k] for k in ("n_leaves", "families", "max_ratio", "min_ratio")}
                            extra = (f" -- {d['n_leaves']} leaf/leaves moved "
                                     f"({', '.join(d['families']) or 'none'}), ratios "
                                     f"{d['min_ratio']} .. {d['max_ratio']}")
                    problems.append(
                        f"the live calibration of the patch (fingerprint "
                        f"{live_record['fingerprint'][:16]}, {live_record.get('last_update_date')}) "
                        f"is not the one the preregistration {args.prereg} was written on "
                        f"({pfp[:16]}){extra}: re-run scripts/h0_idle_model.py on this content, "
                        f"commit it, and submit again")

    pred_path = None if args.predict_from is None else os.path.join(ROOT, args.predict_from)
    record["prediction"] = args.predict_from
    pred, plan_json = None, None
    if args.predict_from is None:
        # prompts/19 C3: with a preregistration the day's H0P prediction is optional; without
        # either, nothing was written down first and nothing may be submitted.
        if not args.prereg:
            problems.append("no --predict-from and no --prereg: a submission must be made against "
                            "numbers that were written down first")
    elif not os.path.exists(pred_path):
        problems.append(f"the day's prediction {args.predict_from} does not exist: "
                        f"run gate_H0P.py --backend {args.backend} first")
    else:
        with open(pred_path) as fh:
            pred = json.load(fh)
        pd = (pred.get("data", {}).get("calibration") or {}).get("last_update_date")
        record["prediction_calibration_last_update_date"] = pd
        record["prediction_status"] = pred.get("status")
        record["prediction_commit"] = pred.get("environment", {}).get("git_commit")
        if pd is None:
            problems.append(f"{args.predict_from} carries no calibration date: it was not produced "
                            f"by gate_H0P.py --backend {args.backend}")
        if args.shots_plan:
            # prompts/16 F3: the plan that sizes the shots and the plan the PREDICTION was made
            # with must be the same file's content -- like for like, or the device is not being
            # compared against the numbers that were preregistered for it.
            pshots, pcal, plan_json = shot_plan_shots(args.shots_plan)
            record["shots_plan"] = args.shots_plan
            record["shots_plan_calibration_last_update_date"] = pcal.get("last_update_date")
            record["shots_plan_stamp"] = pcal.get("stamp")
            predshots = (pred.get("data", {}).get("sampling") or {}).get("shots_by_circuit")
            if predshots is None:
                problems.append(f"{args.predict_from} carries no data.sampling.shots_by_circuit: the "
                                f"prediction was not made with a shot plan (gate_H0P.py --shots-plan)")
            elif {k: int(v) for k, v in predshots.items()} != pshots:
                diff = [k for k in pshots if int(predshots.get(k, -1)) != pshots[k]]
                problems.append(f"the shot plan and the prediction disagree on the shots of "
                                f"{len(diff)} circuit(s) (e.g. {diff[:3]}): the prediction must be "
                                f"the one made with this plan")

    # the live clean-shot fraction of every frozen coarse circuit on the target just read
    # (about 10 s): the numbers the plan sized the shots with and the prediction consumed.
    from gate_S2D import analyse_on_backend
    circs, _cals = load_manifests(prep)
    # only the coarse-step circuits carry a clean-shot fraction: an idle-test circuit has no
    # cz instruction at all, so `f` is not defined for it (prompts/19 C2).
    f_live_by_circuit = {m["id"]: float(analyse_on_backend(load_circuit(prep, m), backend)["f"])
                         for m in circs if m["kind"] == "coarse_step"}
    gate_problems, gate_record = calibration_gate(live_record, pred, plan_json, f_live_by_circuit)
    problems += gate_problems
    record.update(gate_record)

    by_rep, by_circuit = {}, None
    if args.shots_by_rep:
        by_rep = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.shots_by_rep}
    if args.shots_plan:
        by_circuit = shot_plan_shots(args.shots_plan)[0]
    est = estimate(prep, backend, by_rep, args.cal_shots, only=args.only,
                   shots_default=args.shots, no_calibration=args.no_calibration,
                   shots_by_circuit=by_circuit)
    record["qpu_time_estimate"] = {"total_execution_s": est["total_execution_s"],
                                   "total_shots": est["total_shots"],
                                   "groups": est["groups"], "rep_delay_s": est["rep_delay_s"]}
    if est["total_execution_s"] > args.max_qpu_seconds:
        problems.append(f"execution estimate {est['total_execution_s']:.1f} s > "
                        f"--max-qpu-seconds {args.max_qpu_seconds:.0f}")
    return problems, record


# --------------------------------------------------------------------------- main
def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--out", default=None, help="default: data/hardware/H0_dryrun for --dry-run")
    ap.add_argument("--shots", type=int, default=40)
    ap.add_argument("--shots-by-rep", nargs="*", default=None, metavar="R:SHOTS",
                    help="shots per coarse-step circuit by repetition, e.g. --shots-by-rep 1:267 2:130 3:92")
    ap.add_argument("--shots-plan", default=None, metavar="JSON",
                    help="a per-circuit shot plan written by scripts/h0_support_plan.py (rule D3' of "
                         "prompts/16); mutually exclusive with --shots-by-rep / --shots for the "
                         "coarse-step circuits")
    ap.add_argument("--cal-shots", type=int, default=4000)
    ap.add_argument("--dd", "--dd-sequence", dest="dd", default="XY4", choices=DD_CHOICES,
                    help="dynamical decoupling sequence, or 'off' (prompts/19 C1; the default "
                         "XY4 is the production path of prompts/15 D8).  --dd-sequence is the "
                         "old name of this flag and stays an alias.")
    ap.add_argument("--twirling", default="on", choices=TWIRLING_CHOICES,
                    help="Pauli twirling of gates and measurements (default on, strategy "
                         "active-accum); 'off' disables both (prompts/19 C1)")
    ap.add_argument("--job-tags", nargs="*", default=None, metavar="TAG",
                    help="extra job tags; the submitted list is ['su2qc-skqd', <tags>, <commit>, "
                         "<out dir name>] (prompts/19 C4).  Without this flag no tags are set.")
    ap.add_argument("--prereg", default=None, metavar="JSON",
                    help="a preregistration written by scripts/h0_idle_model.py: the preflight "
                         "refuses to submit unless the LIVE calibration fingerprint equals "
                         "JSON['calibration']['fingerprint'] (prompts/19 C3)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backend", default=None, help="IBM backend name (production path; implies --submit)")
    ap.add_argument("--submit", action="store_true", help="submission phase (implied by --backend/--dry-run)")
    ap.add_argument("--retrieve", action="store_true", help="retrieval phase: job ids -> counts files")
    ap.add_argument("--status", action="store_true", help="refresh and print the status of every job")
    ap.add_argument("--record-calibration", action="store_true",
                    help="write <out>/calibration_at_retrieval_<stamp>.json with a FRESH record of "
                         "the backend and store its fingerprint and its diff against the "
                         "prediction's in session.json (prompts/15 B7, scripted by prompts/17 F4)")
    ap.add_argument("--resume", action="store_true", help="--submit only the groups without a job id")
    ap.add_argument("--wait", type=float, default=0.0,
                    help=f"--retrieve: poll for up to this many seconds (<= {MAX_WAIT_S})")
    ap.add_argument("--reps", type=int, nargs="*", default=None, help="restrict to these repetitions")
    ap.add_argument("--only", nargs="*", default=None, help="restrict to these circuit ids (canary)")
    ap.add_argument("--no-calibration", action="store_true")
    ap.add_argument("--max-pubs-per-job", type=int, default=50)
    ap.add_argument("--max-qpu-seconds", type=float, default=120.0,
                    help="refuse to submit if the execution estimate exceeds this (prompts/15 D6)")
    ap.add_argument("--predict-from", default=None,
                    help="the day's prediction (default validation/H0P_<backend>.json)")
    ap.add_argument("--seed", type=int, default=11, help="Aer seed of the dry run")
    return ap


def main():
    args = build_parser().parse_args()

    if args.retrieve or args.status:
        if args.backend or args.dry_run or args.submit:
            raise SystemExit("--retrieve / --status are separate invocations from --submit")
        return retrieve_phase(args)
    if not args.dry_run and not args.backend:
        raise SystemExit("choose --dry-run, --backend <name>, --retrieve or --status")
    return submit_phase(args)


def submit_phase(args):
    out = args.out or os.path.join("data", "hardware",
                                   "H0_dryrun" if args.dry_run else f"H0_{args.backend}")
    outdir = os.path.join(ROOT, out) if not os.path.isabs(out) else out
    cdir = os.path.join(outdir, "counts")
    os.makedirs(cdir, exist_ok=True)
    t0 = time.time()

    prep = os.path.join(ROOT, args.prep)
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    if args.reps:
        mans = [m for m in mans if m.get("repetitions") in args.reps]
    if args.only:
        keep = set(args.only)
        mans = [m for m in mans if m["id"] in keep]
        cals = [m for m in cals if m["id"] in keep]
        missing = keep - {m["id"] for m in mans + cals}
        if missing:
            raise SystemExit(f"--only: no such circuit(s) in {args.prep}: {sorted(missing)}")
    by_rep, plan_shots, plan_cal = {}, None, {}
    if args.shots_plan:
        if args.shots_by_rep:
            raise SystemExit("--shots-plan and --shots-by-rep are mutually exclusive")
        plan_shots, plan_cal, _plan = shot_plan_shots(args.shots_plan)
        missing = [m["id"] for m in mans if m["id"] not in plan_shots]
        if missing:
            raise SystemExit(f"the shot plan {args.shots_plan} carries no shots for {len(missing)} "
                             f"selected circuit(s) (e.g. {missing[:3]})")
    if args.shots_by_rep:
        by_rep = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.shots_by_rep}
    jobs = [(m, plan_shots[m["id"]] if plan_shots
             else by_rep.get(m.get("repetitions"), args.shots))
            for m in mans] + \
           ([] if args.no_calibration else [(m, args.cal_shots) for m in cals])
    if not jobs:
        raise SystemExit("no circuits selected")
    mans_by_id = {m["id"]: m for m, _ in jobs}
    # raw data are never overwritten; this check runs BEFORE any sampler is built
    existing = [m["id"] for m, _ in jobs if os.path.exists(os.path.join(cdir, m["id"] + ".json"))]
    if existing and not args.resume:
        raise SystemExit(f"{len(existing)} counts file(s) already exist in {cdir} "
                         f"(e.g. {existing[:3]}); counts files are raw data and are never "
                         f"overwritten.  Choose another --out.")
    plan = plan_groups(jobs, args.max_pubs_per_job)

    from qiskit_ibm_runtime import SamplerV2
    # prompts/19 C4: tags only when asked for, so the production path's options are untouched
    tags = (["su2qc-skqd"] + list(args.job_tags) + [git_commit(), os.path.basename(outdir)]
            if args.job_tags else None)
    opts = sampler_options(args.shots, args.dd, args.twirling, job_tags=tags)
    preflight_record = None
    if args.dry_run:
        from qiskit_aer import AerSimulator
        snap = resolve_backend(index["common"]["backend"])
        mode = AerSimulator.from_backend(snap, seed_simulator=args.seed)
        backend_name = f"AerSimulator.from_backend({index['common']['backend']}) [local testing mode]"
        calibration_date = None
    else:
        backend = resolve_backend(args.backend)
        if args.predict_from is None and not args.prereg:
            args.predict_from = os.path.join("validation", f"H0P_{args.backend}.json")
        problems, preflight_record = preflight(args, backend, prep, plan, index, outdir=outdir)
        print("preflight:")
        for k in ("backend_name", "operational", "pending_jobs", "max_circuits", "largest_chunk",
                  "calibration_last_update_date", "calibration_fingerprint",
                  "prereg", "prereg_fingerprint", "prereg_fingerprint_match", "prediction",
                  "prediction_calibration_last_update_date",
                  "prediction_calibration_fingerprint", "fingerprint_match", "stamp_match",
                  "f_live_vs_plan_max_abs_diff", "f_live_vs_prediction_max_abs_diff",
                  "calibration_at_submission_file"):
            if k in preflight_record:
                print(f"  {k}: {preflight_record[k]}")
        print(f"  execution estimate: "
              f"{preflight_record['qpu_time_estimate']['total_execution_s']:.1f} s over "
              f"{preflight_record['qpu_time_estimate']['total_shots']} shots "
              f"(cap {args.max_qpu_seconds:.0f} s)")
        if problems:
            for p in problems:
                print(f"  x {p}", flush=True)
            raise SystemExit(f"preflight failed with {len(problems)} problem(s); nothing was submitted")
        print("  OK", flush=True)
        mode = backend
        backend_name = args.backend
        calibration_date = preflight_record["calibration_last_update_date"]
    sampler = SamplerV2(mode=mode, options=opts)

    if args.resume and os.path.exists(session_path(outdir)):
        session = load_session(outdir)
        print(f"resuming {session_path(outdir)}: {len(session['jobs'])} job(s) on record", flush=True)
    else:
        session = {
            "created": now(),
            "script": "scripts/h0_submit.py", "arguments": vars(args),
            "commit": git_commit(),
            "dry_run": bool(args.dry_run), "backend": backend_name,
            "calibration_last_update_date": calibration_date,
            "prediction": args.predict_from,
            "prep": args.prep, "prep_created": index["created"],
            "sampler": "qiskit_ibm_runtime.SamplerV2",
            "sampler_options": options_record(opts, args.shots, args.dd, args.twirling),
            "job_tags": tags,
            "prereg": args.prereg,
            "prereg_calibration_fingerprint": (preflight_record or {}).get("prereg_fingerprint"),
            "prereg_fingerprint_match": (preflight_record or {}).get("prereg_fingerprint_match"),
            "sampler_options_effective": (not args.dry_run),
            "sampler_options_note": ("qiskit-ibm-runtime local testing mode ignores dynamical decoupling "
                                     "and twirling ('Options ... have no effect in local testing mode'): "
                                     "the dry run exercises the submission path and the data format, not "
                                     "the pulse-level options, which apply only on the real backend"
                                     if args.dry_run else
                                     "applied by the runtime on the device"),
            "shots_by_repetition": by_rep or {"all": args.shots},
            "shots_plan": args.shots_plan,
            "shots_plan_calibration_last_update_date": plan_cal.get("last_update_date"),
            "shots_plan_stamp": plan_cal.get("stamp"),
            # prompts/17 D9: what was true of the calibration at the moment of submission.
            # A dry run has no live target, so the live-only keys are null.
            "calibration_fingerprint": (preflight_record or {}).get("calibration_fingerprint"),
            "prediction_calibration_fingerprint":
                (preflight_record or {}).get("prediction_calibration_fingerprint"),
            "shots_plan_calibration_fingerprint": plan_cal.get("fingerprint"),
            "fingerprint_match": (preflight_record or {}).get("fingerprint_match"),
            "stamp_match": (preflight_record or {}).get("stamp_match"),
            "f_live_vs_plan_max_abs_diff":
                (preflight_record or {}).get("f_live_vs_plan_max_abs_diff"),
            "f_live_vs_prediction_max_abs_diff":
                (preflight_record or {}).get("f_live_vs_prediction_max_abs_diff"),
            "calibration_at_submission_file":
                (preflight_record or {}).get("calibration_at_submission_file"),
            "shots_by_circuit": (None if plan_shots is None else
                                 {m["id"]: int(sh) for m, sh in jobs}),
            "calibration_shots": args.cal_shots,
            "n_circuits": len(jobs),
            "circuits": [{"id": m["id"], "kind": m["kind"], "shots": sh} for m, sh in jobs],
            "preflight": preflight_record,
            "jobs": [], "total_usage_s": None,
        }
        save_session(outdir, session)

    done_keys = {(j["group_shots"], j["chunk_index"]) for j in session["jobs"] if j.get("job_id")}
    local_jobs = []
    for sh, ci, chunk in plan:
        if (sh, ci) in done_keys:
            print(f"  group {sh} shots chunk {ci}: already submitted, skipped (--resume)", flush=True)
            continue
        pubs = [(load_circuit(prep, m),) for m in chunk]
        entry = {"group_shots": int(sh), "chunk_index": int(ci), "n_pubs": len(chunk),
                 "circuit_ids": [m["id"] for m in chunk], "job_id": None,
                 "submitted": now(), "status": "SUBMITTING", "usage_s": None, "usage_raw": None,
                 "metrics": None, "retrieved": None, "counts_written": False}
        try:
            job = sampler.run(pubs, shots=sh)
        except Exception as exc:
            entry["status"] = "SUBMISSION FAILED"
            entry["exception"] = f"{type(exc).__name__}: {exc}"
            session["jobs"].append(entry)
            save_session(outdir, session)
            print(f"  x submission of group {sh} shots chunk {ci} failed: {exc}", flush=True)
            raise SystemExit(f"submission failed after {len(session['jobs']) - 1} job(s); "
                             f"the ids on record are in {session_path(outdir)}")
        try:
            entry["job_id"] = job.job_id()
        except Exception:
            entry["job_id"] = None
        entry["status"] = "SUBMITTED"
        session["jobs"].append(entry)
        save_session(outdir, session)       # the id is on disk BEFORE the next submission
        local_jobs.append((entry, job))
        print(f"  submitted job {entry['job_id']} ({len(chunk)} pubs x {sh} shots, "
              f"{time.time() - t0:.0f} s)", flush=True)

    if args.dry_run:                        # local jobs: retrieve in the same process
        for entry, job in local_jobs:
            result = job.result()
            entry["status"] = job_status(job)
            if entry["status"].startswith("UNKNOWN"):
                entry["status"] = "DONE"
            us, raw = usage_seconds(job)
            entry["usage_s"], entry["usage_raw"] = us, raw
            entry["metrics"] = job_metrics(job)
            write_counts_for_job(cdir, session, entry, mans_by_id, result)
            save_session(outdir, session)
            print(f"  job {entry['job_id']}: {entry['counts_files_written']} counts files "
                  f"({time.time() - t0:.0f} s)", flush=True)
        n = len([f for f in os.listdir(cdir) if f.endswith(".json")])
        usages = [j["usage_s"] for j in session["jobs"] if j.get("usage_s") is not None]
        session["total_usage_s"] = float(sum(usages)) if usages else None
        session["runtime_s"] = time.time() - t0
        save_session(outdir, session)
        print(f"wrote {n} counts files to {cdir} in {time.time() - t0:.0f} s")
        print(f"analyse with: python scripts/gate_H0.py --counts {out}/counts --out H0_dryrun")
        return 0

    session["submitted_all"] = now()
    session["runtime_s"] = time.time() - t0
    save_session(outdir, session)
    print(f"{len(session['jobs'])} job(s) submitted to {backend_name}; ids in {session_path(outdir)}")
    print(f"commit session.json now, then: python scripts/h0_submit.py --retrieve --wait "
          f"{int(MAX_WAIT_S)} --out {out}")
    return 0


def record_retrieval_calibration(args, session, outdir, prep):
    """The retrieval-time calibration record of prompts/15 B7, scripted (prompts/17 F4 iv).

    It is information, never a gate: a fingerprint that moved between submission and
    retrieval is the drift that prompts/15 D7 and escalation (d) were written for, and
    gate_H0.py keeps comparing the device against the PREDICTION's record."""
    jobs = [j for j in session["jobs"] if j.get("job_id")]
    if not args.status and jobs and not all(j.get("status") in TERMINAL for j in jobs):
        print("--record-calibration: not every job is terminal yet; nothing written", flush=True)
        return None
    backend = resolve_backend(session["backend"])
    qubits, edges = frozen_qubits_and_edges(prep)
    rec = fresh_calibration(backend, qubits, edges)
    path = os.path.join(outdir, f"calibration_at_retrieval_{rec['stamp']}.json")
    with open(path, "w") as fh:
        json.dump(rec, fh, indent=1)
    session["retrieval_calibration_file"] = os.path.relpath(path, ROOT)
    session["retrieval_calibration_last_update_date"] = rec["last_update_date"]
    session["retrieval_calibration_fingerprint"] = rec["fingerprint"]
    pred_fp = session.get("prediction_calibration_fingerprint")
    pred_path = None
    if session.get("prediction"):
        pp = os.path.join(ROOT, session["prediction"])
        if os.path.isfile(pp):
            with open(pp) as fh:
                pcal = (json.load(fh).get("data", {}).get("calibration") or {})
            pred_fp = pred_fp or pcal.get("fingerprint")
            pred_path = pcal.get("path")
    session["retrieval_fingerprint_match"] = (None if pred_fp is None else pred_fp == rec["fingerprint"])
    session["retrieval_calibration_diff"] = None
    if pred_path:
        p = pred_path if os.path.isabs(pred_path) else os.path.join(ROOT, pred_path)
        if os.path.isfile(p):
            with open(p) as fh:
                d = calibration_diff(json.load(fh), rec)
            session["retrieval_calibration_diff"] = {k: d[k] for k in
                                                     ("n_leaves", "families", "max_ratio", "min_ratio")}
    print(f"retrieval calibration {rec['last_update_date']} (fingerprint {rec['fingerprint'][:16]}, "
          f"match with the prediction: {session['retrieval_fingerprint_match']}, diff "
          f"{session['retrieval_calibration_diff']}) -> {session['retrieval_calibration_file']}",
          flush=True)
    return rec


def retrieve_phase(args):
    if not args.out:
        raise SystemExit("--retrieve / --status need --out <session directory>")
    outdir = os.path.join(ROOT, args.out) if not os.path.isabs(args.out) else args.out
    cdir = os.path.join(outdir, "counts")
    os.makedirs(cdir, exist_ok=True)
    session = load_session(outdir)
    if session.get("dry_run"):
        raise SystemExit("local jobs cannot be retrieved by id: this session was a --dry-run "
                         "(qiskit-ibm-runtime local testing mode), its counts were written in the "
                         "same process")
    prep = os.path.join(ROOT, session["prep"])
    mans, cals = load_manifests(prep)
    mans_by_id = {m["id"]: m for m in mans + cals}
    wait = min(max(args.wait, 0.0), MAX_WAIT_S)
    t0 = time.time()

    from ibm_account import open_service
    service = open_service()

    pending = [j for j in session["jobs"] if j.get("job_id") and not j.get("counts_written")]
    if args.status:
        pending = [j for j in session["jobs"] if j.get("job_id")]
    while True:
        still = []
        for entry in pending:
            try:
                job = service.job(entry["job_id"])
            except Exception as exc:
                entry["status"] = f"UNREACHABLE ({exc})"
                print(f"  job {entry['job_id']}: {entry['status']}", flush=True)
                continue
            entry["status"] = job_status(job)
            us, raw = usage_seconds(job)
            if us is not None:
                entry["usage_s"], entry["usage_raw"] = us, raw
            entry["metrics"] = job_metrics(job)
            print(f"  job {entry['job_id']}: {entry['status']} "
                  f"({entry['n_pubs']} pubs x {entry['group_shots']} shots, usage "
                  f"{entry['usage_s']} s)", flush=True)
            if entry["status"] == "DONE" and not entry.get("counts_written") and not args.status:
                write_counts_for_job(cdir, session, entry, mans_by_id, job.result())
                print(f"    -> {entry['counts_files_written']} counts files", flush=True)
            elif entry["status"] not in TERMINAL:
                still.append(entry)
        usages = [j["usage_s"] for j in session["jobs"] if j.get("usage_s") is not None]
        session["total_usage_s"] = float(sum(usages)) if usages else None
        session["last_polled"] = now()
        save_session(outdir, session)
        if args.status or not still or (time.time() - t0) >= wait:
            break
        time.sleep(min(POLL_S, max(1.0, wait - (time.time() - t0))))
        pending = still

    if args.record_calibration:
        record_retrieval_calibration(args, session, outdir, prep)
        save_session(outdir, session)

    n = len([f for f in os.listdir(cdir) if f.endswith(".json")])
    done = [j for j in session["jobs"] if j.get("counts_written")]
    print(f"{len(done)}/{len(session['jobs'])} job(s) retrieved, {n} counts files in {cdir}, "
          f"total usage {session['total_usage_s']} s")
    unfinished = [j for j in session["jobs"] if j.get("job_id") and not j.get("counts_written")]
    if unfinished and not args.status:
        print(f"{len(unfinished)} job(s) not finished yet; run --retrieve again "
              f"(queue waits are not compute time)")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
