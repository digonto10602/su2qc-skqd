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
from h0_backends import is_fake, last_update_date, resolve_backend  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POLL_S = 30
MAX_WAIT_S = 1500          # one --retrieve invocation stays inside the 30-minute rule
TERMINAL = ("DONE", "ERROR", "CANCELLED", "FAILED")


# --------------------------------------------------------------------------- options
def sampler_options(shots: int, dd_sequence: str = "XY4"):
    """SamplerV2 options: dynamical decoupling on, Pauli twirling on, no mitigation."""
    from qiskit_ibm_runtime.options import SamplerOptions

    o = SamplerOptions()
    o.default_shots = shots
    o.dynamical_decoupling.enable = True
    o.dynamical_decoupling.sequence_type = dd_sequence
    o.twirling.enable_gates = True
    o.twirling.enable_measure = True
    o.twirling.strategy = "active-accum"
    return o


def options_record(o, shots, dd_sequence):
    return {
        "default_shots": shots,
        "dynamical_decoupling": {"enable": True, "sequence_type": dd_sequence},
        "twirling": {"enable_gates": True, "enable_measure": True, "strategy": "active-accum"},
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


# --------------------------------------------------------------------------- preflight
def preflight(args, backend, prep, plan, index):
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

    live_date = last_update_date(backend)
    record["calibration_last_update_date"] = live_date
    pred_path = os.path.join(ROOT, args.predict_from)
    record["prediction"] = args.predict_from
    if not os.path.exists(pred_path):
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
        elif pd != live_date:
            problems.append(f"the live calibration ({live_date}) is not the one the prediction was "
                            f"made from ({pd}): re-run gate_H0P.py --backend {args.backend}")

    by_rep = {}
    if args.shots_by_rep:
        by_rep = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.shots_by_rep}
    est = estimate(prep, backend, by_rep, args.cal_shots, only=args.only,
                   shots_default=args.shots, no_calibration=args.no_calibration)
    record["qpu_time_estimate"] = {"total_execution_s": est["total_execution_s"],
                                   "total_shots": est["total_shots"],
                                   "groups": est["groups"], "rep_delay_s": est["rep_delay_s"]}
    if est["total_execution_s"] > args.max_qpu_seconds:
        problems.append(f"execution estimate {est['total_execution_s']:.1f} s > "
                        f"--max-qpu-seconds {args.max_qpu_seconds:.0f}")
    return problems, record


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--out", default=None, help="default: data/hardware/H0_dryrun for --dry-run")
    ap.add_argument("--shots", type=int, default=40)
    ap.add_argument("--shots-by-rep", nargs="*", default=None, metavar="R:SHOTS",
                    help="shots per coarse-step circuit by repetition, e.g. --shots-by-rep 1:267 2:130 3:92")
    ap.add_argument("--cal-shots", type=int, default=4000)
    ap.add_argument("--dd-sequence", default="XY4")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backend", default=None, help="IBM backend name (production path; implies --submit)")
    ap.add_argument("--submit", action="store_true", help="submission phase (implied by --backend/--dry-run)")
    ap.add_argument("--retrieve", action="store_true", help="retrieval phase: job ids -> counts files")
    ap.add_argument("--status", action="store_true", help="refresh and print the status of every job")
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
    args = ap.parse_args()

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
        mans = [m for m in mans if m["repetitions"] in args.reps]
    if args.only:
        keep = set(args.only)
        mans = [m for m in mans if m["id"] in keep]
        cals = [m for m in cals if m["id"] in keep]
        missing = keep - {m["id"] for m in mans + cals}
        if missing:
            raise SystemExit(f"--only: no such circuit(s) in {args.prep}: {sorted(missing)}")
    by_rep = {}
    if args.shots_by_rep:
        by_rep = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.shots_by_rep}
    jobs = [(m, by_rep.get(m["repetitions"], args.shots)) for m in mans] + \
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
    opts = sampler_options(args.shots, args.dd_sequence)
    preflight_record = None
    if args.dry_run:
        from qiskit_aer import AerSimulator
        snap = resolve_backend(index["common"]["backend"])
        mode = AerSimulator.from_backend(snap, seed_simulator=args.seed)
        backend_name = f"AerSimulator.from_backend({index['common']['backend']}) [local testing mode]"
        calibration_date = None
    else:
        backend = resolve_backend(args.backend)
        if args.predict_from is None:
            args.predict_from = os.path.join("validation", f"H0P_{args.backend}.json")
        problems, preflight_record = preflight(args, backend, prep, plan, index)
        print("preflight:")
        for k in ("backend_name", "operational", "pending_jobs", "max_circuits", "largest_chunk",
                  "calibration_last_update_date", "prediction",
                  "prediction_calibration_last_update_date"):
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
            "sampler_options": options_record(opts, args.shots, args.dd_sequence),
            "sampler_options_effective": (not args.dry_run),
            "sampler_options_note": ("qiskit-ibm-runtime local testing mode ignores dynamical decoupling "
                                     "and twirling ('Options ... have no effect in local testing mode'): "
                                     "the dry run exercises the submission path and the data format, not "
                                     "the pulse-level options, which apply only on the real backend"
                                     if args.dry_run else
                                     "applied by the runtime on the device"),
            "shots_by_repetition": by_rep or {"all": args.shots},
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
