#!/usr/bin/env python3
"""
prompts/26 A7: the Quantinuum submission path for the frozen 2x3 circuits, mirroring scripts/h0_submit.py
(phases, `session.json`, counts files as raw data that are never overwritten).

Runs in the isolated venv ~/.local/share/su2qc-quantinuum/venv (pytket, qnexus).

Phases
  --dry-run       builds every job record (device, shots, the QuantinuumConfig fields, max_cost), writes
                  <out>/session.json with job_id null, runs the circuits LOCALLY on Aer with the gate-only
                  H2-2 noise model of prompts/26 A6 and writes the counts files.  No account, no network.
  --syntax-check  H2-2SC (free; needs a Nexus login).                  NOT run under prompts/26.
  --emulate       H2-2E (noise model on; eHQC); refuses without --max-cost.   NOT run under prompts/26.
  --preflight     device status, the cost of every job against --max-cost and the sum against --cap-hqc,
                  the preregistration file present and its sha256 recorded -> <out>/preflight.json.
  --submit        hardware (H2-2): requires --prereg, the preflight record of the same plan and --cap-hqc;
                  refuses otherwise.                                     NOT run under prompts/26.
  --retrieve      polls qnx.jobs.status / qnx.jobs.results and writes the counts files.
  --status        refreshes and prints the status of every job on record.

Credentials: none of them ever passes through this script.  `scripts/quantinuum_account.py --login` lets
qnexus store its own tokens (~/.qnx/auth/); there is no password, token or key argument here.

Counts files: `counts` in the qiskit key convention of scripts/h0_submit.py (the RIGHTMOST character is
c[0] = qubit 0; skqd.reference_sim.qiskit_key_to_bits), converted from pytket's
`BackendResult.get_counts()` tuples, which are in BasisOrder.ilo (c[0], c[1], ...) -- pytket 2.18.4
docstring: "Toggle between ILO (increasing lexicographic order of bit ids) and DLO (decreasing
lexicographic order) for column ordering if cbits is None. Defaults to BasisOrder.ilo."

Usage (dry run, the only phase run under prompts/26):
  ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/quantinuum_submit.py --dry-run --shots 200
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from skqd import quantinuum_native as qn  # noqa: E402

CIRCUITS = os.path.join("data", "quantinuum", "circuits_2x3")
HARDWARE = ("H2-2", "H2-1", "H1-1", "Helios-1")
EMULATORS = ("H2-2E", "H2-1E", "H1-1E", "Helios-1E")
SYNTAX_CHECKERS = ("H2-2SC", "H2-1SC", "H1-1SC", "Helios-1SC")
MAX_COST_MARGIN = 1.10           # prompts/26 E2: max_cost per job = formula + 10 %
TERMINAL = ("COMPLETED", "ERROR", "CANCELLED", "DEPLETED")
# prompts/26 A6: the gate-only H2-2 path check (no memory term).  rz is virtual and noiseless.
A6_NOISE = {"source": "data/quantinuum/devices_20261002.json specs.quantinuum_h2_2 (H2-2 row, read 2026-10-02)",
            "depolarizing_2q_rzz": 8.3e-4, "depolarizing_1q_rx_ry": 2.8e-5, "rz": "noiseless (virtual)",
            "readout_p1_given_0": 6.7e-4, "readout_p0_given_1": 1.2e-3, "memory_term": "none",
            "label": "gate-only path check (no memory/transport term)",
            "channel": "qiskit_aer depolarizing_error(p, n): rho -> (1-p) rho + p I/2^n"}


# --------------------------------------------------------------------------- small helpers
def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def bits_to_qiskit_key(bits):
    """(b0, b1, ...) with b_k = qubit k  ->  qiskit key (qubit 0 rightmost)."""
    return "".join(str(int(b)) for b in reversed(tuple(bits)))


def session_path(outdir):
    return os.path.join(outdir, "session.json")


def save_session(outdir, session):
    path = session_path(outdir)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(session, fh, indent=1)
    os.replace(tmp, path)
    return path


def load_session(outdir):
    path = session_path(outdir)
    if not os.path.exists(path):
        raise SystemExit(f"{path} does not exist: nothing was planned from this directory")
    with open(path) as fh:
        return json.load(fh)


def load_index(cdir):
    with open(os.path.join(cdir, "index.json")) as fh:
        return json.load(fh)


def load_manifest(cdir, cid):
    with open(os.path.join(cdir, cid + ".manifest.json")) as fh:
        return json.load(fh)


def load_frozen(cdir, man):
    """The frozen pytket circuit from its JSON; the sha256 must match the manifest."""
    path = os.path.join(cdir, man["files"]["json"])
    with open(path) as fh:
        text = fh.read()
    if hashlib.sha256(text.encode()).hexdigest() != man["json_sha256"]:
        raise SystemExit(f"{path}: sha256 differs from the manifest -- the frozen circuit was changed")
    return qn.from_json(json.loads(text))


def pilot_ids(index):
    """The two k = 1 circuits of the pilot: the first reference of each sector in build order."""
    out = []
    for sec in ("B0", "B1"):
        out.append(next(c for c in index["circuits"] if c.startswith(sec + "_") and c.endswith("_k1")))
    return out


# --------------------------------------------------------------------------- job planning
def backend_config_fields(device, args, max_cost):
    """The QuantinuumConfig fields of one job (prompts/26 A7), as plain JSON."""
    return {"type": "QuantinuumConfig", "device_name": device,
            "noisy_simulation": (True if device.endswith("E") else None),
            "no_opt": True, "allow_implicit_swaps": False,
            "attempt_batching": bool(args.attempt_batching), "user_group": args.user_group,
            "max_cost": max_cost}


def plan_jobs(args, cdir, index, device):
    """[(job record)] -- one job per circuit and per chunk of at most 10,000 shots."""
    ids = list(args.only) if args.only else (pilot_ids(index) + list(index.get("calibration", [])))
    plan_shots = None
    if args.shots_plan:
        with open(args.shots_plan if os.path.isabs(args.shots_plan) else os.path.join(ROOT, args.shots_plan)) as fh:
            plan_shots = {k: int(v) for k, v in json.load(fh)["shots_by_circuit"].items()}
        missing = [c for c in ids if c not in plan_shots]
        if missing:
            raise SystemExit(f"the shot plan carries no shots for {missing}")
    jobs = []
    for cid in ids:
        man = load_manifest(cdir, cid)
        shots = plan_shots[cid] if plan_shots else (args.cal_shots if man["kind"] == "calibration" else args.shots)
        n_chunks = int(math.ceil(shots / qn.MAX_SHOTS_PER_JOB))
        for ch in range(n_chunks):
            s = min(qn.MAX_SHOTS_PER_JOB, shots - ch * qn.MAX_SHOTS_PER_JOB)
            est = qn.hqc_job(man["counts"], s)
            cap = float(args.max_cost) if args.max_cost is not None else round(est * MAX_COST_MARGIN, 2)
            if est > cap:
                raise SystemExit(f"{cid} chunk {ch}: the formula estimate {est:.2f} HQC exceeds "
                                 f"--max-cost {cap}: the job would be cut off; raise --max-cost")
            if est > qn.MAX_HQC_PER_JOB:
                raise SystemExit(f"{cid}: {est:.0f} HQC per job exceeds the 500,000 HQC job limit")
            jobs.append({"circuit_id": cid, "chunk": ch, "n_shots": int(s), "device_name": device,
                         "qasm_sha256": man["qasm_sha256"], "json_sha256": man["json_sha256"],
                         "hqc_estimate": est, "max_cost": cap,
                         "backend_config": backend_config_fields(device, args, cap),
                         "aer_seed": int(args.seed + ch * qn.MAX_SHOTS_PER_JOB),
                         "job_id": None, "submitted": None, "status": None})
    return jobs


def counts_dir(outdir):
    return os.path.join(outdir, "counts")


def counts_file(outdir, cid, chunk):
    return os.path.join(counts_dir(outdir), f"{cid}.json" if chunk == 0 else f"{cid}__chunk{chunk}.json")


def write_counts(outdir, session, job, man, counts_bits, how):
    """One counts file per job (raw data: never overwritten)."""
    path = counts_file(outdir, job["circuit_id"], job["chunk"])
    if os.path.exists(path):
        raise SystemExit(f"{path} exists: counts files are raw data and are never overwritten")
    rec = {k: man.get(k) for k in ("id", "kind", "sector", "twoB", "reference", "k", "repetitions",
                                   "dt", "g2", "n_qubits", "qasm_sha256", "json_sha256", "counts",
                                   "hqc_per_shot", "p_reference", "reference_int")}
    rec["native_counts"] = rec.pop("counts")
    rec.update({
        "counts": {bits_to_qiskit_key(b): int(v) for b, v in sorted(counts_bits.items())},
        "counts_key_convention": ("qiskit counts key: the RIGHTMOST character is classical bit 0 = "
                                  "logical qubit 0 (skqd.reference_sim.qiskit_key_to_bits)"),
        "source_convention": how,
        "shots": int(job["n_shots"]), "chunk": int(job["chunk"]), "device_name": job["device_name"],
        "dry_run": bool(session["dry_run"]), "job_id": job["job_id"],
        "backend_config": job["backend_config"], "submitted": job["submitted"], "retrieved": now(),
    })
    os.makedirs(counts_dir(outdir), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(tmp, path)
    return path


# --------------------------------------------------------------------------- the local Aer path
def a6_noise_model():
    from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

    nm = NoiseModel(basis_gates=["rz", "rx", "ry", "rzz"])
    nm.add_all_qubit_quantum_error(depolarizing_error(A6_NOISE["depolarizing_2q_rzz"], 2), ["rzz"])
    nm.add_all_qubit_quantum_error(depolarizing_error(A6_NOISE["depolarizing_1q_rx_ry"], 1), ["rx", "ry"])
    p10, p01 = A6_NOISE["readout_p1_given_0"], A6_NOISE["readout_p0_given_1"]
    nm.add_all_qubit_readout_error(ReadoutError([[1 - p10, p10], [p01, 1 - p01]]))
    return nm


def run_aer(circuits, jobs, threads=0):
    """All jobs of one shot count in one Aer call (memory: batching beats separate calls)."""
    from qiskit_aer import AerSimulator

    from skqd import circuits_qiskit as cq
    from skqd.reference_sim import qiskit_key_to_bits

    nm = a6_noise_model()
    out = {}
    by_shots = {}
    for j in jobs:
        by_shots.setdefault((j["n_shots"], j["aer_seed"]), []).append(j)
    for (shots, seed), js in sorted(by_shots.items()):
        qcs = []
        for j in js:
            ir, n, qmap = qn.pytket_to_ir(circuits[j["circuit_id"]])
            if qmap != {q: q for q in range(n)}:
                raise SystemExit(f"{j['circuit_id']}: measurement map is not q[k] -> c[k]")
            qcs.append(cq.ir_to_qiskit(ir, n, measure=True))
        sim = AerSimulator(noise_model=nm, method="statevector", seed_simulator=seed,
                           max_parallel_threads=int(threads))
        t0 = time.time()
        res = sim.run(qcs, shots=shots).result()
        dt = time.time() - t0
        for i, j in enumerate(js):
            out[(j["circuit_id"], j["chunk"])] = (
                {qiskit_key_to_bits(k): int(v) for k, v in res.get_counts(i).items()}, dt / len(js))
        print(f"  Aer: {len(js)} circuit(s) x {shots} shots in {dt:.0f} s", flush=True)
    return out


# --------------------------------------------------------------------------- phases
def phase_dry_run(args):
    cdir = os.path.join(ROOT, args.circuits)
    index = load_index(cdir)
    out = args.out or os.path.join("data", "hardware", "Q0P_2x3_dryrun")
    outdir = out if os.path.isabs(out) else os.path.join(ROOT, out)
    device = args.device or "H2-2"
    jobs = plan_jobs(args, cdir, index, device)
    existing = [j["circuit_id"] for j in jobs if os.path.exists(counts_file(outdir, j["circuit_id"], j["chunk"]))]
    if existing or os.path.exists(session_path(outdir)):
        raise SystemExit(f"{outdir} already holds a session or counts ({existing[:3]}); counts files are raw "
                         f"data and are never overwritten.  Choose another --out.")
    os.makedirs(outdir, exist_ok=True)
    session = {"created": now(), "script": "scripts/quantinuum_submit.py", "phase": "dry-run",
               "arguments": {k: v for k, v in vars(args).items()}, "dry_run": True,
               "device_name": device, "executed_on": "local AerSimulator (statevector, CPU)",
               "noise_model": A6_NOISE, "git_commit": git_commit(), "versions": qn.versions(),
               "index_sha256": sha256_file(os.path.join(cdir, "index.json")),
               "jobs": jobs, "hqc_estimate_total": float(sum(j["hqc_estimate"] for j in jobs)),
               "bit_order": ("pytket BackendResult.get_counts() tuples are BasisOrder.ilo (c[0], c[1], ...); "
                             "written as qiskit keys (c[0] rightmost)")}
    save_session(outdir, session)
    circuits = {j["circuit_id"]: load_frozen(cdir, load_manifest(cdir, j["circuit_id"])) for j in jobs}
    t0 = time.time()
    results = run_aer(circuits, jobs, args.threads)
    for j in jobs:
        counts, sec = results[(j["circuit_id"], j["chunk"])]
        j["status"] = "COMPLETED (local Aer)"
        j["aer_seconds_share"] = sec
        write_counts(outdir, session, j, load_manifest(cdir, j["circuit_id"]), counts,
                     "qiskit_aer get_counts() keys (qubit 0 rightmost) -> bit tuples")
    session["sampling_wall_s"] = time.time() - t0
    session["completed"] = now()
    save_session(outdir, session)
    print(f"dry run: {len(jobs)} job(s), {sum(j['n_shots'] for j in jobs)} shots, "
          f"{session['sampling_wall_s']:.0f} s -> {os.path.relpath(outdir, ROOT)}")
    return 0


def _qnx():
    try:
        import qnexus as qnx
    except ImportError as exc:                                   # pragma: no cover
        raise SystemExit("qnexus is not installed in this interpreter (use the su2qc-quantinuum venv)") from exc
    return qnx


def _require_login(qnx):
    """Any authenticated call; qnexus raises when no token is stored.  Nothing is printed of it."""
    try:
        qnx.users.get_self()
    except Exception as exc:
        raise SystemExit(f"no usable Nexus login ({type(exc).__name__}); run "
                         f"scripts/quantinuum_account.py --login first") from None


def phase_remote(args, kind):
    """--syntax-check / --emulate / --submit: one Nexus execute job per planned job."""
    cdir = os.path.join(ROOT, args.circuits)
    index = load_index(cdir)
    if kind == "syntax-check":
        device = args.device or "H2-2SC"
        if device not in SYNTAX_CHECKERS:
            raise SystemExit(f"--syntax-check takes a syntax checker {SYNTAX_CHECKERS}, not {device}")
    elif kind == "emulate":
        device = args.device or "H2-2E"
        if device not in EMULATORS:
            raise SystemExit(f"--emulate takes an emulator {EMULATORS}, not {device}")
        if args.max_cost is None:
            raise SystemExit("--emulate refuses to run without --max-cost (eHQC per job)")
        if device.startswith("Helios"):
            raise SystemExit("Helios-1E takes Guppy/HUGR programs; the pytket route (prompts/26 A9) is not built")
    else:
        device = args.device or "H2-2"
        if device not in HARDWARE:
            raise SystemExit(f"--submit takes a hardware device {HARDWARE}, not {device}")
        if not (args.prereg and args.cap_hqc is not None and args.max_cost is not None):
            raise SystemExit("--submit refuses: it requires --prereg, --cap-hqc and --max-cost")
        if device.startswith("Helios"):
            raise SystemExit("Helios-1 takes Guppy/HUGR programs; the pytket route (prompts/26 A9) is not built")
    out = args.out or os.path.join("data", "hardware", f"Q0P_2x3_{device}")
    outdir = out if os.path.isabs(out) else os.path.join(ROOT, out)
    jobs = plan_jobs(args, cdir, index, device)
    if kind == "submit":
        pre_path = os.path.join(outdir, "preflight.json")
        if not os.path.exists(pre_path):
            raise SystemExit(f"--submit refuses: no preflight record {pre_path} (run --preflight first)")
        pre = json.load(open(pre_path))
        if pre.get("prereg_sha256") != sha256_file(args.prereg):
            raise SystemExit("--submit refuses: the preregistration changed since the preflight")
        if pre.get("plan_sha256") != plan_digest(jobs) or not pre.get("ok"):
            raise SystemExit("--submit refuses: the preflight record is for another plan or did not pass")
    if args.cap_hqc is not None and sum(j["hqc_estimate"] for j in jobs) > args.cap_hqc:
        raise SystemExit(f"the plan costs {sum(j['hqc_estimate'] for j in jobs):.1f} HQC > --cap-hqc {args.cap_hqc}")
    if os.path.exists(session_path(outdir)):
        raise SystemExit(f"{session_path(outdir)} exists: one session per directory")
    qnx = _qnx()
    _require_login(qnx)
    os.makedirs(outdir, exist_ok=True)
    session = {"created": now(), "script": "scripts/quantinuum_submit.py", "phase": kind, "dry_run": False,
               "arguments": vars(args), "device_name": device, "git_commit": git_commit(),
               "versions": qn.versions(), "jobs": jobs,
               "hqc_estimate_total": float(sum(j["hqc_estimate"] for j in jobs))}
    save_session(outdir, session)
    from qnexus import QuantinuumConfig

    project = qnx.projects.get_or_create(name=args.project)
    for j in jobs:
        man = load_manifest(cdir, j["circuit_id"])
        circ = load_frozen(cdir, man)
        ref = qnx.circuits.upload(circuit=circ, name=f"{j['circuit_id']}", project=project)
        cfg = QuantinuumConfig(**{k: v for k, v in j["backend_config"].items() if k != "type" and v is not None})
        job = qnx.start_execute_job(programs=[ref], n_shots=[j["n_shots"]], backend_config=cfg,
                                    name=f"su2qc-{j['circuit_id']}-c{j['chunk']}-{kind}", project=project,
                                    max_cost=[j["max_cost"]])
        j["job_id"] = str(job.id)
        j["submitted"] = now()
        save_session(outdir, session)                     # the job id survives a crash
        print(f"  {j['circuit_id']} chunk {j['chunk']}: job {j['job_id']}", flush=True)
    return 0


def plan_digest(jobs):
    keys = ("circuit_id", "chunk", "n_shots", "device_name", "qasm_sha256", "max_cost")
    return hashlib.sha256(json.dumps([{k: j[k] for k in keys} for j in jobs], sort_keys=True).encode()).hexdigest()


def preflight_record(args, jobs, device_status=None):
    """The offline part of the preflight (no network): costs, caps, the prereg digest."""
    problems = []
    tot = float(sum(j["hqc_estimate"] for j in jobs))
    if args.max_cost is None:
        problems.append("--max-cost missing")
    else:
        over = [j["circuit_id"] for j in jobs if j["hqc_estimate"] > float(args.max_cost)]
        if over:
            problems.append(f"jobs above --max-cost: {over}")
    if args.cap_hqc is None:
        problems.append("--cap-hqc missing")
    elif tot > float(args.cap_hqc):
        problems.append(f"plan total {tot:.1f} HQC > --cap-hqc {args.cap_hqc}")
    pre_sha = None
    if not args.prereg:
        problems.append("--prereg missing")
    elif not os.path.exists(args.prereg):
        problems.append(f"preregistration {args.prereg} not found")
    else:
        pre_sha = sha256_file(args.prereg)
    if device_status is not None and not device_status.get("online", False):
        problems.append(f"device not online: {device_status}")
    return {"created": now(), "jobs": len(jobs), "hqc_estimate_total": tot,
            "max_cost": args.max_cost, "cap_hqc": args.cap_hqc, "prereg": args.prereg,
            "prereg_sha256": pre_sha, "plan_sha256": plan_digest(jobs), "device_status": device_status,
            "problems": problems, "ok": not problems,
            "calibration_record_note": ("Quantinuum publishes no per-job calibration record: the D9 "
                                        "content-fingerprint check of the IBM path has no analogue here; the "
                                        "device list fingerprint of quantinuum_account.py --check is the "
                                        "closest record")}


def phase_preflight(args):
    cdir = os.path.join(ROOT, args.circuits)
    device = args.device or "H2-2"
    jobs = plan_jobs(args, cdir, load_index(cdir), device)
    status = None
    if not args.offline:
        qnx = _qnx()
        _require_login(qnx)
        devs = qnx.devices.get_all()
        df = devs.df() if hasattr(devs, "df") else None
        status = {"device_name": device, "listed": None, "online": None}
        if df is not None and "device_name" in df.columns:
            row = df[df["device_name"] == device]
            status["listed"] = bool(len(row))
            status["online"] = bool(len(row))
    rec = preflight_record(args, jobs, status)
    rec["device_name"] = device
    out = args.out or os.path.join("data", "hardware", f"Q0P_2x3_{device}")
    outdir = out if os.path.isabs(out) else os.path.join(ROOT, out)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "preflight.json"), "w") as fh:
        json.dump(rec, fh, indent=1)
    print(json.dumps({k: rec[k] for k in ("jobs", "hqc_estimate_total", "problems", "ok")}, indent=1))
    return 0 if rec["ok"] else 2


def phase_retrieve(args, status_only=False):
    out = args.out
    if not out:
        raise SystemExit("--retrieve/--status need --out <session directory>")
    outdir = out if os.path.isabs(out) else os.path.join(ROOT, out)
    session = load_session(outdir)
    if session.get("dry_run"):
        raise SystemExit("a dry-run session has no jobs to retrieve")
    cdir = os.path.join(ROOT, args.circuits)
    qnx = _qnx()
    _require_login(qnx)
    from qnexus.models.references import ExecuteJobRef  # noqa: F401  (type of qnx.jobs.get)

    for j in session["jobs"]:
        if not j.get("job_id"):
            continue
        ref = qnx.jobs.get(id=j["job_id"])
        st = qnx.jobs.status(ref)
        j["status"] = getattr(st.status, "value", str(st.status))
        if status_only or j["status"] not in ("COMPLETED",):
            print(f"  {j['circuit_id']} chunk {j['chunk']}: {j['status']}")
            continue
        if os.path.exists(counts_file(outdir, j["circuit_id"], j["chunk"])):
            continue
        res = qnx.jobs.results(ref)[0].download_result()
        cbits = [(b.reg_name, int(b.index[0])) for b in sorted(res.c_bits)]
        counts = qn.counts_from_pytket_readouts(dict(res.get_counts()), cbits)
        j["result_kind"] = "shots" if getattr(res, "contains_measured_results", False) else "counts"
        j["cost_hqc"] = qnx.jobs.cost(ref)
        write_counts(outdir, session, j, load_manifest(cdir, j["circuit_id"]), counts,
                     "pytket BackendResult.get_counts() (BasisOrder.ilo: c[0], c[1], ...) -> bit tuples")
    save_session(outdir, session)
    return 0


# --------------------------------------------------------------------------- parser
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--syntax-check", action="store_true")
    g.add_argument("--emulate", action="store_true")
    g.add_argument("--preflight", action="store_true")
    g.add_argument("--submit", action="store_true")
    g.add_argument("--retrieve", action="store_true")
    g.add_argument("--status", action="store_true")
    ap.add_argument("--circuits", default=CIRCUITS)
    ap.add_argument("--out", default=None)
    ap.add_argument("--device", default=None, help="H2-2 / H2-2E / H2-2SC / H1-1 ... (phase default)")
    ap.add_argument("--only", nargs="*", default=None, help="circuit ids (default: the two pilot k=1 + calibration)")
    ap.add_argument("--shots", type=int, default=200)
    ap.add_argument("--cal-shots", type=int, default=200)
    ap.add_argument("--shots-plan", default=None, metavar="JSON", help="{'shots_by_circuit': {id: shots}}")
    ap.add_argument("--max-cost", type=float, default=None, help="HQC (or eHQC) cap per job")
    ap.add_argument("--cap-hqc", type=float, default=None, help="HQC cap for the whole plan")
    ap.add_argument("--prereg", default=None, metavar="JSON", help="the committed preregistration file")
    ap.add_argument("--user-group", default=None)
    ap.add_argument("--attempt-batching", action="store_true")
    ap.add_argument("--project", default="su2qc-skqd-2x3")
    ap.add_argument("--offline", action="store_true", help="--preflight without the device-status call")
    ap.add_argument("--seed", type=int, default=11, help="Aer seed of the dry run")
    ap.add_argument("--threads", type=int, default=0, help="Aer max_parallel_threads (0 = all)")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.dry_run:
        return phase_dry_run(args)
    if args.syntax_check:
        return phase_remote(args, "syntax-check")
    if args.emulate:
        return phase_remote(args, "emulate")
    if args.submit:
        return phase_remote(args, "submit")
    if args.preflight:
        return phase_preflight(args)
    if args.retrieve:
        return phase_retrieve(args)
    return phase_retrieve(args, status_only=True)


if __name__ == "__main__":
    sys.exit(main())
