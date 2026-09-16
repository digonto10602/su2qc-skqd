#!/usr/bin/env python3
"""
Step 3 of prompts/13 — the H0 submission path (prompts/07 step 2).

Builds the SamplerV2 job(s) for the frozen circuit set of `scripts/h0_build_circuits.py`
with **dynamical decoupling and Pauli twirling enabled and no error mitigation**: SKQD
needs raw bit strings, so nothing that rewrites outcomes (resilience levels, readout
mitigation of expectation values) is switched on.  Measurement twirling is a bit flip
before the measurement that the runtime undoes classically, so it leaves the bit strings
interpretable; it is enabled and recorded in the session JSON.

  --dry-run            runs the same jobs on `AerSimulator.from_backend(<snapshot>())`
                       through the same SamplerV2 code path (qiskit-ibm-runtime local
                       testing mode) and writes the counts in the exact format the real
                       run uses.
  --backend <name>     production: the named IBM backend through QiskitRuntimeService.
                       Not called here; no IBM account is assumed by this repository.

Counts are written to `<out>/counts/<circuit id>.json`, one file per circuit, each
carrying the manifest of the circuit it came from.  They are RAW DATA: the script
refuses to overwrite an existing file.

Usage: python scripts/h0_submit.py --dry-run [--shots 40] [--out data/hardware/H0_dryrun]
       python scripts/h0_submit.py --backend ibm_fez --shots 4096 --out data/hardware/H0_<date>
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from gate_H0P import load_circuit, load_index, load_manifests  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--out", default=None, help="default: data/hardware/H0_dryrun for --dry-run")
    ap.add_argument("--shots", type=int, default=40)
    ap.add_argument("--shots-by-rep", nargs="*", default=None, metavar="R:SHOTS",
                    help="shots per coarse-step circuit by repetition, e.g. --shots-by-rep 1:150 2:80 3:50")
    ap.add_argument("--cal-shots", type=int, default=4000)
    ap.add_argument("--dd-sequence", default="XY4")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backend", default=None, help="IBM backend name (production path)")
    ap.add_argument("--reps", type=int, nargs="*", default=None, help="restrict to these repetitions")
    ap.add_argument("--no-calibration", action="store_true")
    ap.add_argument("--max-pubs-per-job", type=int, default=50)
    ap.add_argument("--seed", type=int, default=11, help="Aer seed of the dry run")
    args = ap.parse_args()
    if not args.dry_run and not args.backend:
        raise SystemExit("choose --dry-run or --backend <name>")
    out = args.out or os.path.join("data", "hardware", "H0_dryrun" if args.dry_run else f"H0_{args.backend}")
    outdir = os.path.join(ROOT, out)
    cdir = os.path.join(outdir, "counts")
    os.makedirs(cdir, exist_ok=True)
    t0 = time.time()

    prep = os.path.join(ROOT, args.prep)
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    if args.reps:
        mans = [m for m in mans if m["repetitions"] in args.reps]
    by_rep = {}
    if args.shots_by_rep:
        by_rep = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.shots_by_rep}
    jobs = [(m, by_rep.get(m["repetitions"], args.shots)) for m in mans] + \
           ([] if args.no_calibration else [(m, args.cal_shots) for m in cals])
    for m, _ in jobs:
        p = os.path.join(cdir, m["id"] + ".json")
        if os.path.exists(p):
            raise SystemExit(f"{p} exists; counts files are raw data and are never overwritten. "
                             f"Choose another --out.")

    from qiskit_ibm_runtime import SamplerV2
    opts = sampler_options(args.shots, args.dd_sequence)
    if args.dry_run:
        from qiskit_aer import AerSimulator
        from qiskit_ibm_runtime.fake_provider import FakeFez, FakeTorino
        snap = {"FakeFez": FakeFez, "FakeTorino": FakeTorino}[index["common"]["backend"]]()
        mode = AerSimulator.from_backend(snap, seed_simulator=args.seed)
        backend_name = f"AerSimulator.from_backend({index['common']['backend']}) [local testing mode]"
    else:                                    # production; requires an IBM account
        from qiskit_ibm_runtime import QiskitRuntimeService
        mode = QiskitRuntimeService().backend(args.backend)
        backend_name = args.backend
    sampler = SamplerV2(mode=mode, options=opts)

    session = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "script": "scripts/h0_submit.py", "arguments": vars(args),
        "dry_run": bool(args.dry_run), "backend": backend_name,
        "prep": args.prep, "prep_created": index["created"],
        "sampler": "qiskit_ibm_runtime.SamplerV2",
        "sampler_options": options_record(opts, args.shots, args.dd_sequence),
        "sampler_options_effective": (not args.dry_run),
        "sampler_options_note": ("qiskit-ibm-runtime local testing mode ignores dynamical decoupling and "
                                 "twirling ('Options ... have no effect in local testing mode'): the dry run "
                                 "exercises the submission path and the data format, not the pulse-level "
                                 "options, which apply only on the real backend"
                                 if args.dry_run else
                                 "applied by the runtime on the device"),
        "shots_by_repetition": by_rep or {"all": args.shots},
        "n_circuits": len(jobs), "jobs": [],
    }
    # one job per shot count (qiskit-ibm-runtime 0.48 deprecates mixed shots in one job),
    # chunked so that a job never carries more than --max-pubs-per-job circuits
    groups = {}
    for m, sh in jobs:
        groups.setdefault(sh, []).append(m)
    done = 0
    for sh in sorted(groups):
        batch = groups[sh]
        for start in range(0, len(batch), args.max_pubs_per_job):
            chunk = batch[start:start + args.max_pubs_per_job]
            pubs = [(load_circuit(prep, m),) for m in chunk]
            job = sampler.run(pubs, shots=sh)
            result = job.result()
            try:
                jid = job.job_id()
            except Exception:
                jid = None
            for m, pub_res in zip(chunk, result):
                counts = counts_of(pub_res)
                rec = dict(m)
                rec.update({
                    "counts": {str(k): int(v) for k, v in counts.items()},
                    "counts_key_convention": ("qiskit counts key: the RIGHTMOST character is classical bit "
                                              "0 = logical qubit 0 (skqd.reference_sim.qiskit_key_to_bits)"),
                    "shots": sh, "backend": backend_name, "dry_run": bool(args.dry_run),
                    "job_id": jid, "sampler_options": session["sampler_options"],
                    "submitted": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                })
                with open(os.path.join(cdir, m["id"] + ".json"), "w") as fh:
                    json.dump(rec, fh, indent=1)
                session["jobs"].append({"id": m["id"], "kind": m["kind"], "shots": sh, "job_id": jid})
            done += len(chunk)
            print(f"  {done}/{len(jobs)} circuits, job {jid} ({len(chunk)} pubs x {sh} shots, "
                  f"{time.time() - t0:.0f} s)", flush=True)
    session["runtime_s"] = time.time() - t0
    with open(os.path.join(outdir, "session.json"), "w") as fh:
        json.dump(session, fh, indent=1)
    print(f"wrote {len(jobs)} counts files to {cdir} in {time.time() - t0:.0f} s "
          f"({by_rep or args.shots} shots per coarse-step circuit, {args.cal_shots} per calibration circuit)")
    print(f"analyse with: python scripts/gate_H0.py --counts {out}/counts --out "
          f"{'H0_dryrun' if args.dry_run else 'H0'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
