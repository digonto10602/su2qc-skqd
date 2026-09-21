#!/usr/bin/env python3
"""
QPU execution-time estimate for the frozen H0 circuit set (prompts/15 step A4).

The open plan is billed in seconds of QPU execution, so the session is budgeted from
the repository before anything is submitted: for every frozen circuit an ASAP schedule
on the target's instruction durations gives the circuit duration (the critical path --
each instruction starts as soon as all its qubits are free), and the group total is

    circuits x shots x (duration + rep_delay)

with rep_delay the backend's default (the delay between shots, 250 us on ibm_fez;
prompts/15 D2 keeps it at the default because a shorter delay changes the initial
state, i.e. the physics).  The estimate ignores queue time and the runtime's own
per-job overhead, which are not QPU execution and are not billed as such.

`--backend FakeFez` is the offline test (no account needed); on a live backend the
same computation uses that day's durations, which is what `h0_submit.py --submit`
checks against `--max-qpu-seconds` before it submits anything.

Usage: python scripts/h0_qpu_time.py --backend FakeFez --shots-by-rep 1:267 2:130 3:92 \
                                     --cal-shots 4000 [--out <json>]
Runtime: about 1 minute (it loads 126 QPY circuits); no QPU time is used.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from gate_H0P import load_circuit, load_index, load_manifests  # noqa: E402
from h0_backends import last_update_date, resolve_backend  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ZERO_DURATION_OPS = ("barrier", "rz", "delay_zero")


def instruction_duration_s(durations, target, name, qubits):
    """Duration of `name` on `qubits` in seconds; 0 for barriers and virtual gates."""
    if name in ("barrier",):
        return 0.0
    try:
        d = durations.get(name, list(qubits), unit="s")
        if d is not None:
            return float(d)
    except Exception:
        pass
    try:
        props = target[name].get(tuple(qubits))
        if props is not None and props.duration is not None:
            return float(props.duration)
    except Exception:
        pass
    return 0.0


def circuit_duration_s(qc, durations, target):
    """ASAP critical path: every instruction starts when all its qubits are free."""
    free = [0.0] * qc.num_qubits
    for inst in qc.data:
        name = inst.operation.name
        idx = [qc.find_bit(q).index for q in inst.qubits]
        if name == "delay":
            try:
                dur = float(inst.operation.duration) * (float(target.dt) if target.dt else 1.0)
            except Exception:
                dur = 0.0
        else:
            dur = instruction_duration_s(durations, target, name, idx)
        start = max((free[i] for i in idx), default=0.0)
        for i in idx:
            free[i] = start + dur
    return max(free) if free else 0.0


def basis_durations(target, durations):
    """min/max duration of each basis instruction over the whole device (for the record)."""
    out = {}
    for name in sorted(target.operation_names):
        vals = []
        try:
            for qs, props in target[name].items():
                if props is not None and props.duration is not None:
                    vals.append(float(props.duration))
        except Exception:
            continue
        if vals:
            out[name] = {"min_s": min(vals), "max_s": max(vals), "n_entries": len(vals)}
    return out


def estimate(prep, backend, shots_by_rep, cal_shots, only=None, shots_default=None,
             rep_delay=None, no_calibration=False):
    """The per-group execution-time table of the frozen set on this backend."""
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    if only:
        keep = set(only)
        mans = [m for m in mans if m["id"] in keep]
        cals = [m for m in cals if m["id"] in keep]
    if no_calibration:
        cals = []
    target = backend.target
    durations = target.durations()
    rd = rep_delay
    if rd is None:
        rd = getattr(backend, "default_rep_delay", None)
    rd = 0.0 if rd is None else float(rd)

    groups, per_circuit = {}, []
    for m in mans + cals:
        qc = load_circuit(prep, m)
        dur = circuit_duration_s(qc, durations, target)
        if m["kind"] == "coarse_step":
            r = m["repetitions"]
            sh = shots_by_rep.get(r, shots_default)
            key = f"r={r}"
        else:
            sh = cal_shots
            key = "readout calibration"
        if sh is None:
            raise SystemExit(f"no shot count for {m['id']}: give --shots-by-rep or --shots")
        g = groups.setdefault(key, {"group": key, "circuits": 0, "shots_per_circuit": int(sh),
                                    "durations_s": [], "total_shots": 0, "execution_s": 0.0})
        if g["shots_per_circuit"] != int(sh):
            raise SystemExit(f"group {key} has mixed shot counts")
        g["circuits"] += 1
        g["durations_s"].append(dur)
        g["total_shots"] += int(sh)
        g["execution_s"] += int(sh) * (dur + rd)
        per_circuit.append({"id": m["id"], "kind": m["kind"], "group": key,
                            "duration_s": dur, "shots": int(sh),
                            "execution_s": int(sh) * (dur + rd)})
    table = []
    for key in sorted(groups, key=lambda k: (k == "readout calibration", k)):
        g = groups[key]
        d = g.pop("durations_s")
        g["duration_mean_s"] = sum(d) / len(d)
        g["duration_min_s"] = min(d)
        g["duration_max_s"] = max(d)
        table.append(g)
    total_shots = sum(g["total_shots"] for g in table)
    total_s = sum(g["execution_s"] for g in table)
    return {
        "backend": backend.name,
        "last_update_date": last_update_date(backend),
        "prep": os.path.relpath(prep, ROOT),
        "prep_created": index["created"],
        "schedule": ("ASAP critical path over backend.target.durations(); one shot costs "
                     "circuit duration + rep_delay"),
        "dt_s": None if backend.dt is None else float(backend.dt),
        "rep_delay_s": rd,
        "rep_delay_source": ("--rep-delay" if rep_delay is not None else
                             "backend.default_rep_delay"),
        "shots_by_repetition": {str(k): int(v) for k, v in sorted(shots_by_rep.items())},
        "calibration_shots": int(cal_shots),
        "basis_durations": basis_durations(target, durations),
        "groups": table,
        "per_circuit": per_circuit,
        "n_circuits": len(per_circuit),
        "total_shots": int(total_shots),
        "total_execution_s": float(total_s),
        "total_execution_min": float(total_s / 60.0),
    }


def table_text(est):
    lines = ["| group | circuits | shots/circuit | duration mean | total shots | execution |",
             "|---|---|---|---|---|---|"]
    for g in est["groups"]:
        lines.append(f"| {g['group']} | {g['circuits']} | {g['shots_per_circuit']} | "
                     f"{g['duration_mean_s'] * 1e6:.1f} us | {g['total_shots']} | "
                     f"{g['execution_s']:.1f} s |")
    lines.append(f"| **total** | {est['n_circuits']} | | | {est['total_shots']} | "
                 f"**{est['total_execution_s']:.1f} s** |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--backend", default="FakeFez")
    ap.add_argument("--shots", type=int, default=None, help="shots for repetitions not in --shots-by-rep")
    ap.add_argument("--shots-by-rep", nargs="*", default=None, metavar="R:SHOTS")
    ap.add_argument("--cal-shots", type=int, default=4000)
    ap.add_argument("--rep-delay", type=float, default=None, help="seconds (default: the backend's)")
    ap.add_argument("--only", nargs="*", default=None, help="restrict to these circuit ids")
    ap.add_argument("--no-calibration", action="store_true")
    ap.add_argument("--out", default=None, help="write the estimate to this JSON path")
    args = ap.parse_args()
    t0 = time.time()

    prep = os.path.join(ROOT, args.prep)
    by_rep = {}
    if args.shots_by_rep:
        by_rep = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.shots_by_rep}
    backend = resolve_backend(args.backend)
    est = estimate(prep, backend, by_rep, args.cal_shots, only=args.only,
                   shots_default=args.shots, rep_delay=args.rep_delay,
                   no_calibration=args.no_calibration)
    est["runtime_s"] = time.time() - t0
    print(f"{est['backend']} (calibration {est['last_update_date']}), rep_delay "
          f"{est['rep_delay_s'] * 1e6:.0f} us, dt {est['dt_s']}")
    print(table_text(est))
    print(f"total {est['total_execution_s']:.1f} s = {est['total_execution_min']:.2f} min "
          f"of QPU execution over {est['total_shots']} shots")
    if args.out:
        path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(est, fh, indent=1)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
