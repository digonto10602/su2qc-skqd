#!/usr/bin/env python3
"""
Watch the calibration CONTENT of the frozen H0 patch on a live backend (prompts/17 F5).

The H0 session may submit only while the live calibration of the 30 qubits and 54 edges
the frozen circuits use is identical to the one the prediction was made from (rule D9).
This script answers two questions and spends **zero QPU seconds** -- `backend.target`,
`backend.properties()` and `backend.status()` are metadata queries:

  * `--once`  : is the content the reference's right now?  Exit 0 if it is, 3 if it moved.
                That is the check step A''7 of prompts/17 branches on.
  * `--minutes M --every S` : how long does a given content hold?  One JSON line per poll
                into `<out>` (default every 300 s, M <= 25 so the invocation stays inside
                the 30-minute rule), and `--summary <jsonl>` turns the log into the stamp
                and fingerprint windows -- the timing data the next planning decision needs.

Every poll builds a NEW backend object and calls `h0_backends.fresh_calibration`, which
refreshes it: in qiskit-ibm-runtime 0.49.0 `IBMBackend.properties()` is cached per object
and `target` is rebuilt only `if refresh or not self._target`, so a watcher that holds one
backend object reports a stale timestamp forever (observed: 71 minutes).

Usage:
  python scripts/h0_calwatch.py --backend ibm_fez --once \\
      --reference data/hardware/H0_ibm_fez/calibration_20260922T0711Z.json \\
      --out data/hardware/H0_ibm_fez/calibration_watch.jsonl
  python scripts/h0_calwatch.py --backend ibm_fez --minutes 25 --every 300 \\
      --reference <the same file> --out <the same jsonl>
  python scripts/h0_calwatch.py --summary data/hardware/H0_ibm_fez/calibration_watch.jsonl
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from h0_backends import (calibration_diff, calibration_fingerprint,  # noqa: E402
                         fresh_calibration, frozen_qubits_and_edges, resolve_backend)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAX_MINUTES = 25.0          # one invocation stays inside the 30-minute rule
EXIT_MOVED = 3              # --once: the content is not the reference's


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_reference(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(p) as fh:
        rec = json.load(fh)
    return rec, calibration_fingerprint(rec), os.path.relpath(p, ROOT)


def last_line(path):
    if not path or not os.path.exists(path):
        return None
    prev = None
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    prev = json.loads(line)
                except Exception:
                    pass
    return prev


def poll(backend_name, qubits, edges, reference, reference_fp, reference_path, prev_line, prev_record):
    """One observation: a fresh backend object, a fresh record, one JSON line."""
    backend = resolve_backend(backend_name)
    rec = fresh_calibration(backend, qubits, edges)
    fp = rec["fingerprint"]
    base = prev_record if prev_record is not None else reference
    d = calibration_diff(base, rec)
    st = rec.get("status") or {}
    line = {
        "utc": utc_now(),
        "backend": backend_name,
        "last_update_date": rec["last_update_date"],
        "stamp": rec["stamp"],
        "fingerprint": fp,
        "operational": st.get("operational"),
        "pending_jobs": st.get("pending_jobs"),
        "reference": reference_path,
        "reference_fingerprint": reference_fp,
        "match_reference": fp == reference_fp,
        "stamp_changed": (None if prev_line is None
                          else prev_line.get("last_update_date") != rec["last_update_date"]),
        "content_changed": (None if prev_line is None
                            else prev_line.get("fingerprint") != fp),
        "diff_against": ("the previous poll of this invocation" if prev_record is not None
                         else reference_path),
        "n_leaves_changed": d["n_leaves"],
        "families": d["families"],
        "max_ratio": d["max_ratio"],
        "min_ratio": d["min_ratio"],
        "missing_errors": len(rec.get("missing_errors") or []),
    }
    return line, rec


def append_line(path, line):
    if not path:
        return
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as fh:
        fh.write(json.dumps(line) + "\n")


def print_line(line):
    print(f"{line['utc']}  {line['backend']}  last_update_date {line['last_update_date']} "
          f"({line['stamp']})  fingerprint {line['fingerprint'][:16]}  "
          f"match_reference {line['match_reference']}  stamp_changed {line['stamp_changed']}  "
          f"content_changed {line['content_changed']}  {line['n_leaves_changed']} leaf/leaves vs "
          f"{line['diff_against']} {line['families']}  operational {line['operational']}  "
          f"pending {line['pending_jobs']}", flush=True)


# ------------------------------------------------------------------ the summary
def _parse_utc(s):
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def windows(lines, key):
    """[(value, first utc, last utc, seconds, closed)] per run of equal `key`.

    The durations are bounded by the poll interval: a change is seen at the first poll
    after it, so a window measured here is the truth within one interval."""
    out = []
    for ln in lines:
        v = ln.get(key)
        if out and out[-1]["value"] == v:
            out[-1]["last_utc"] = ln["utc"]
        else:
            out.append({"value": v, "first_utc": ln["utc"], "last_utc": ln["utc"]})
    for i, w in enumerate(out):
        w["seconds"] = _parse_utc(w["last_utc"]) - _parse_utc(w["first_utc"])
        w["closed"] = i < len(out) - 1
        if w["closed"]:
            # the change was observed at the next poll: the window is at least this long
            w["seconds_upper_bound"] = _parse_utc(out[i + 1]["first_utc"]) - _parse_utc(w["first_utc"])
        else:
            w["seconds_upper_bound"] = w["seconds"]
    return out


def summarise(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    lines = []
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    if not lines:
        raise SystemExit(f"{path} has no lines")
    print(f"{len(lines)} poll(s) from {lines[0]['utc']} to {lines[-1]['utc']} "
          f"({(_parse_utc(lines[-1]['utc']) - _parse_utc(lines[0]['utc'])) / 60:.1f} min) on "
          f"{lines[0].get('backend')}")
    out = {"file": os.path.relpath(p, ROOT), "polls": len(lines),
           "first_utc": lines[0]["utc"], "last_utc": lines[-1]["utc"]}
    for key, label in (("last_update_date", "stamp"), ("fingerprint", "fingerprint")):
        ws = windows(lines, key)
        closed = [w["seconds"] for w in ws if w["closed"]]
        closed_ub = [w["seconds_upper_bound"] for w in ws if w["closed"]]
        med = None
        if closed:
            s = sorted(closed)
            med = s[len(s) // 2] if len(s) % 2 else 0.5 * (s[len(s) // 2 - 1] + s[len(s) // 2])
        print(f"  {label}: {len(ws)} value(s), {len(closed)} closed window(s)"
              + (f", min {min(closed) / 60:.1f} min, median {med / 60:.1f} min, "
                 f"max {max(closed) / 60:.1f} min (upper bounds "
                 f"{min(closed_ub) / 60:.1f} / {max(closed_ub) / 60:.1f} min)" if closed else "")
              + f"; the open one has held {ws[-1]['seconds'] / 60:.1f} min "
                f"(value {str(ws[-1]['value'])[:24]})")
        out[label] = {
            "values": len(ws), "closed_windows": len(closed),
            "min_s": min(closed) if closed else None,
            "median_s": med, "max_s": max(closed) if closed else None,
            "open_window_s": ws[-1]["seconds"], "open_value": ws[-1]["value"],
            "windows": [{k: w[k] for k in ("value", "first_utc", "last_utc", "seconds",
                                           "seconds_upper_bound", "closed")} for w in ws],
        }
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=None, help="live backend name (metadata queries only)")
    ap.add_argument("--reference", default=None, metavar="calibration_<stamp>.json",
                    help="the record the content is compared against (the prediction's)")
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--out", default=None, metavar="JSONL", help="append one line per poll")
    ap.add_argument("--once", action="store_true",
                    help="one poll; exit 0 if the content is the reference's, 3 if it moved")
    ap.add_argument("--minutes", type=float, default=None,
                    help=f"poll for this long (<= {MAX_MINUTES:.0f}, the 30-minute rule)")
    ap.add_argument("--every", type=float, default=300.0, help="seconds between polls")
    ap.add_argument("--summary", default=None, metavar="JSONL",
                    help="print the stamp and fingerprint windows of an existing log and exit")
    ap.add_argument("--summary-json", default=None, help="write the summary as JSON as well")
    args = ap.parse_args()

    if args.summary:
        out = summarise(args.summary)
        if args.summary_json:
            p = args.summary_json if os.path.isabs(args.summary_json) else \
                os.path.join(ROOT, args.summary_json)
            with open(p, "w") as fh:
                json.dump(out, fh, indent=1)
            print(f"wrote {p}")
        return 0
    if not args.backend:
        raise SystemExit("give --backend <name> (or --summary <jsonl>)")
    if not args.reference:
        raise SystemExit("give --reference <calibration_<stamp>.json>: the content to compare with")
    if not args.once and args.minutes is None:
        raise SystemExit("give --once or --minutes M")
    if args.minutes is not None and args.minutes > MAX_MINUTES:
        raise SystemExit(f"--minutes {args.minutes} > {MAX_MINUTES:.0f}: one invocation must stay "
                         f"inside the 30-minute rule; run the script again instead")

    reference, reference_fp, reference_path = load_reference(args.reference)
    prep = os.path.join(ROOT, args.prep)
    qubits, edges = frozen_qubits_and_edges(prep)
    outp = (args.out if args.out is None or os.path.isabs(args.out)
            else os.path.join(ROOT, args.out))
    prev_line, prev_record = last_line(outp), None

    t0 = time.time()
    line = None
    while True:
        line, rec = poll(args.backend, qubits, edges, reference, reference_fp, reference_path,
                         prev_line, prev_record)
        append_line(outp, line)
        print_line(line)
        prev_line, prev_record = line, rec
        if args.once or (time.time() - t0) >= args.minutes * 60 - args.every:
            break
        time.sleep(max(1.0, args.every))

    if args.once:
        return 0 if line["match_reference"] else EXIT_MOVED
    return 0


if __name__ == "__main__":
    sys.exit(main())
