#!/usr/bin/env python3
"""
prompts/32 A.W.1 -- one free metadata poll of an IBM backend: is it back from maintenance with
a usable two-qubit calibration on the patch?  Zero QPU seconds (status, target, properties).

    python scripts/h0_devicewatch.py --backend ibm_kingston --once \
        --patch-from data/hardware/H0_ddtest_prep/calibration_20261002T1906Z.json \
        --out data/hardware/H0_ddrep_prep/devicewatch.jsonl

Appends ONE JSON line to --out:
  {when, backend, status_msg, operational, pending_jobs, last_update_date,
   n_cz_keys_with_error, n_cz_keys_total, n_cz_keys_source, n_2q_gates_in_properties,
   patch_edges_calibrated, patch_edges_total (cz target keys of the patch record),
   patch_qubits_calibrated, patch_qubits_total,
   patch_missing (first 20), ready, reasons}
and exits 0 iff ready, 2 otherwise:
  ready = status_msg == "active" and operational and every patch qubit and edge carries an
          error value and the target has cz errors on >= 90 % of its cz keys.

Why `account` of h0_ddtest_circuits is not enough: the record of 2026-10-06T0042Z shows
`operational: True` with `status_msg: maintenance` and zero cz errors on the target
(data/hardware/K0_prep/ibm_kingston_full_20261006T0042Z.json).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CZ_FRACTION_MIN = 0.90            # A.W.1: cz errors on >= 90 % of the target's cz keys
EXIT_READY, EXIT_WAIT = 0, 2


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def patch_of(path):
    """(qubits, directed pairs) of a committed patch calibration record."""
    with open(path if os.path.isabs(path) else os.path.join(ROOT, path)) as fh:
        rec = json.load(fh)
    qubits = sorted(int(q) for q in rec["qubits"])
    keys = sorted(tuple(int(x) for x in e["target_key"]) for e in rec["edges"].values())
    pairs = []
    for e in rec["edges"].values():
        pairs += [tuple(int(x) for x in d) for d in (e.get("directed_pairs_of_the_frozen_set") or [e["target_key"]])]
    return qubits, sorted(set(pairs)), keys, rec.get("fingerprint")


def cz_key_counts(target):
    """(with error, total) over the target's cz keys; (0, 0) when cz has no per-pair entries."""
    if "cz" not in target.operation_names:
        return 0, 0
    try:
        m = target["cz"]
    except Exception:
        return 0, 0
    keys = [k for k in m if k is not None]
    n_err = sum(1 for k in keys if m[k] is not None and m[k].error is not None)
    return n_err, len(keys)


def readiness(line):
    """(ready, reasons) of one poll line -- the pure rule of A.W.1 (tested)."""
    reasons = []
    if line.get("status_msg") != "active":
        reasons.append(f"status_msg {line.get('status_msg')!r} != 'active'")
    if not line.get("operational"):
        reasons.append("not operational")
    if line.get("patch_qubits_calibrated") != line.get("patch_qubits_total"):
        reasons.append(f"patch qubits calibrated {line.get('patch_qubits_calibrated')} of {line.get('patch_qubits_total')}")
    if line.get("patch_edges_calibrated") != line.get("patch_edges_total"):
        reasons.append(f"patch edges calibrated {line.get('patch_edges_calibrated')} of {line.get('patch_edges_total')}")
    tot = int(line.get("n_cz_keys_total") or 0)
    n = int(line.get("n_cz_keys_with_error") or 0)
    if tot <= 0 or n < CZ_FRACTION_MIN * tot:
        reasons.append(f"cz keys with error {n} of {tot} (< {CZ_FRACTION_MIN:.0%})")
    return (not reasons), reasons


def poll(backend_name, patch_from):
    from h0_backends import calibration_record, last_update_date, resolve_backend
    t0 = time.time()
    b = resolve_backend(backend_name)            # a new backend object: target and properties are fresh
    line = {"when": now(), "backend": backend_name, "qpu_seconds": 0}
    try:
        st = b.status()
        line.update({"status_msg": getattr(st, "status_msg", None), "operational": bool(st.operational),
                     "pending_jobs": int(st.pending_jobs)})
    except Exception as exc:
        line.update({"status_msg": f"unavailable: {type(exc).__name__}", "operational": None, "pending_jobs": None})
    line["last_update_date"] = last_update_date(b)
    t = b.target
    n_err, n_tot = cz_key_counts(t)
    line["n_cz_keys_with_error"], line["n_cz_keys_total"] = n_err, n_tot
    line["n_cz_keys_source"] = "backend.target['cz'] keys (directed)"
    if n_tot == 0:
        try:
            cm = b.configuration().coupling_map or []
            line["n_cz_keys_total_configuration"] = len(cm)
        except Exception:
            line["n_cz_keys_total_configuration"] = None
    try:
        props = b.properties()
        line["n_2q_gates_in_properties"] = int(sum(1 for g in props.gates if len(g.qubits) == 2))
    except Exception:
        line["n_2q_gates_in_properties"] = None
    qubits, pairs, keys, pfp = patch_of(patch_from)
    rec = calibration_record(b, qubits, pairs)
    miss = rec["missing_errors"]
    bad_q = {int(m["qubits"][0]) for m in miss if len(m["qubits"]) == 1}
    # T1 / T2 are inputs of the idle terms: a qubit without them is not calibrated either
    for q, v in rec["qubits"].items():
        if v.get("T1_s") is None or v.get("T2_s") is None or v.get("x_error") is None or v.get("sx_error") is None:
            bad_q.add(int(q))
    # the patch's edges are its record's cz TARGET KEYS (directed: both directions are separate keys)
    live_keys = {tuple(v["target_key"]) for v in rec["edges"].values() if v.get("cz_error") is not None}
    line.update({"patch_from": os.path.relpath(patch_from if os.path.isabs(patch_from) else os.path.join(ROOT, patch_from), ROOT),
                 "patch_fingerprint_committed": pfp,
                 "patch_fingerprint_live": rec["fingerprint"],
                 "patch_content_identical_to_committed": rec["fingerprint"] == pfp,
                 "patch_qubits_total": len(qubits), "patch_qubits_calibrated": len(qubits) - len(bad_q & set(qubits)),
                 "patch_edges_total": len(keys), "patch_edges_calibrated": len([k for k in keys if k in live_keys]),
                 "patch_missing": miss[:20], "n_patch_missing": len(miss)})
    ready, reasons = readiness(line)
    line["ready"] = ready
    line["reasons"] = reasons
    line["runtime_s"] = time.time() - t0
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="ibm_kingston")
    ap.add_argument("--once", action="store_true", help="one poll (the only mode: the cadence is the caller's)")
    ap.add_argument("--patch-from", default=os.path.join("data", "hardware", "H0_ddtest_prep",
                                                         "calibration_20261002T1906Z.json"))
    ap.add_argument("--out", default=os.path.join("data", "hardware", "H0_ddrep_prep", "devicewatch.jsonl"))
    args = ap.parse_args()
    if not args.once:
        raise SystemExit("only --once is supported: at most one poll per hour, logged (prompts/32 A.W.2)")
    line = poll(args.backend, args.patch_from)
    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "a") as fh:
        fh.write(json.dumps(line, sort_keys=True) + "\n")
    print(f"{line['when']} {args.backend}: status {line.get('status_msg')!r}, operational {line.get('operational')}, "
          f"pending {line.get('pending_jobs')}, last update {line.get('last_update_date')}; cz keys with error "
          f"{line['n_cz_keys_with_error']}/{line['n_cz_keys_total']}; patch qubits {line['patch_qubits_calibrated']}/"
          f"{line['patch_qubits_total']}, edges {line['patch_edges_calibrated']}/{line['patch_edges_total']}; "
          f"patch content identical to the committed record: {line['patch_content_identical_to_committed']}")
    print(("READY" if line["ready"] else "WAITING: " + "; ".join(line["reasons"])) + f"  (logged to {os.path.relpath(out, ROOT)})")
    return EXIT_READY if line["ready"] else EXIT_WAIT


if __name__ == "__main__":
    sys.exit(main())
