#!/usr/bin/env python3
"""
Backend resolution for the H0 scripts (prompts/15 step A1).

Before this module `h0_build_circuits.py`, `gate_H0P.py` and `h0_submit.py` each
hard-coded the two Heron calibration snapshots.  The H0 session needs the same three
scripts to talk to a LIVE backend as well, without changing anything about the fake
path: `resolve_backend("FakeFez")` returns exactly the object the old code built,
`resolve_backend("ibm_fez")` returns `QiskitRuntimeService().backend("ibm_fez")`
through `scripts/ibm_account.py` (which diagnoses a bad API key instead of raising).

`calibration_fingerprint(record)` (prompts/17 D9) is the sha256 of the four blocks of a
calibration record that the PREDICTION reads -- `dt_s`, `default_rep_delay_s`, `qubits`
(30 x 9 leaves) and `edges` (54 x 4 leaves) -- and nothing else: the device metadata
(`last_update_date`, `stamp`, `status`, `basis_gates`, `max_circuits`) is excluded.
`qiskit_aer.noise.NoiseModel.from_backend` builds its model from exactly those numbers
(readout error per measured qubit, depolarizing + thermal relaxation per instruction from
`.error`, `.duration` and the T1/T2 of `target.qubit_properties`), and
`gate_S2D.analyse_on_backend` multiplies exactly those cz and measure errors into f, so
two records with the same fingerprint give the same seeded prediction bit for bit.  The
timestamp does not: ibm_fez changed its `last_update_date` three times in one night
without moving a single one of these numbers (prompts/17, diagnosis).  Submission is
therefore keyed on the fingerprint, never on the stamp.

`calibration_record(backend, qubits, edges)` is the day's calibration as the
preregistration needs it: the measure/sx/x/cz errors and durations and the T1, T2 of
exactly the qubits and edges the frozen circuit set uses, plus the device metadata
(dt, rep delay, max_circuits, status) and `missing_errors` -- the list of target
entries whose `.error` is None.  `gate_S2D.analyse_on_backend` reads those same
fields, so a None there would silently poison the clean-shot fraction f; prompts/15
makes it a hard stop instead, and this function is where it is detected.

Nothing here touches a QPU: `backend.target`, `backend.properties()` and
`backend.status()` are metadata queries.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAKE_BACKENDS = ("FakeFez", "FakeTorino")
# prompts/20 E1: the survey needs FakeMarrakesh and FakeKingston too, and there is no reason
# to keep a hand-written list -- any `Fake*` class the installed fake_provider exposes is an
# OFFLINE snapshot and needs no account.  The two names above stay spelled out because the
# frozen circuit set and every committed H0 output name one of them.

# prompts/17 F1: the blocks of a calibration record that the prediction reads.  Everything
# else in the record is device metadata (timestamps, status, basis gates, max_circuits) and
# enters neither the Aer noise model nor f nor the execution-time estimate.
FINGERPRINT_FIELDS = ("dt_s", "default_rep_delay_s", "qubits", "edges")


def fake_backend_names():
    """Every `Fake*` class of the installed qiskit_ibm_runtime.fake_provider."""
    try:
        import qiskit_ibm_runtime.fake_provider as fp
    except Exception:
        return set(FAKE_BACKENDS)
    return {n for n in dir(fp) if n.startswith("Fake") and isinstance(getattr(fp, n), type)}


def is_fake(name: str) -> bool:
    """True for an offline fake-provider snapshot, False for a live device name.

    `FakeFez` and `FakeTorino` are answered without importing anything, so the behaviour of
    every committed H0 path is unchanged even if the fake provider is unavailable."""
    if name in FAKE_BACKENDS:
        return True
    return bool(name) and name.startswith("Fake") and name in fake_backend_names()


def resolve_backend(name: str):
    """A backend object from a name: the fake snapshots offline, anything else live."""
    if name == "FakeFez":
        from qiskit_ibm_runtime.fake_provider import FakeFez
        return FakeFez()
    if name == "FakeTorino":
        from qiskit_ibm_runtime.fake_provider import FakeTorino
        return FakeTorino()
    if is_fake(name):                     # any other offline snapshot (prompts/20 E1)
        import qiskit_ibm_runtime.fake_provider as fp
        return getattr(fp, name)()
    from ibm_account import open_service
    service = open_service()
    try:
        return service.backend(name)
    except Exception as exc:
        names = [b.name for b in service.backends()]
        raise SystemExit(f"backend '{name}' is not reachable with this account ({exc}); "
                         f"reachable: {', '.join(names) or '(none)'}")


def last_update_date(backend):
    """The calibration timestamp of the backend as an ISO string (None if it has none)."""
    try:
        props = backend.properties()
    except Exception:
        props = None
    d = getattr(props, "last_update_date", None)
    return None if d is None else d.isoformat()


def calibration_stamp(iso: str) -> str:
    """'2025-02-26T15:16:25-05:00' -> '20250226T1516Z' (the file-name stamp)."""
    from datetime import datetime, timezone
    if iso is None:
        from time import gmtime, strftime
        return strftime("%Y%m%dT%H%MZ", gmtime())
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%MZ")


def calibration_fingerprint(rec: dict) -> str:
    """sha256 of the four blocks of `rec` the prediction depends on (prompts/17 D9).

    The serialization is pinned by the pass criteria of prompts/17 and by
    `tests/test_h0_scripts.py:test_fingerprint_of_the_committed_records`: JSON with
    `sort_keys=True` and `separators=(",", ":")` over `FINGERPRINT_FIELDS`.  A record
    that carries a `fingerprint` key of its own does not feed it back in -- the key is
    not one of the four fields -- so the fingerprint of a record equals the fingerprint
    of the target it was read from."""
    missing = [k for k in FINGERPRINT_FIELDS if k not in rec]
    if missing:
        raise KeyError(f"not a calibration record of scripts/h0_backends.py: no {missing}")
    blob = json.dumps({k: rec[k] for k in FINGERPRINT_FIELDS},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flatten(v, f"{prefix}{k}/"))
        elif isinstance(v, list):
            out[f"{prefix}{k}"] = json.dumps(v, sort_keys=True)
        else:
            out[f"{prefix}{k}"] = v
    return out


def calibration_diff(a: dict, b: dict) -> dict:
    """What moved between two calibration records, over the fingerprinted blocks only.

    `families` are the leaf names (`measure_error`, `cz_error`, `T1_s`, ...), which is
    what a refusal message needs to say: the one content change on record between two
    ibm_fez calibrations was 30 leaves of the single family `measure_error`."""
    fa, fb = _flatten({k: a.get(k) for k in FINGERPRINT_FIELDS}), \
        _flatten({k: b.get(k) for k in FINGERPRINT_FIELDS})
    leaves = []
    for key in sorted(set(fa) | set(fb)):
        before, after = fa.get(key), fb.get(key)
        if before == after:
            continue
        ratio = None
        if isinstance(before, (int, float)) and isinstance(after, (int, float)) and before:
            ratio = float(after) / float(before)
        leaves.append({"path": key, "before": before, "after": after, "ratio": ratio})
    ratios = [v["ratio"] for v in leaves if v["ratio"] is not None]
    return {
        "n_leaves": len(leaves),
        "families": sorted({v["path"].split("/")[-1] for v in leaves}),
        "leaves": leaves,
        "max_ratio": max(ratios) if ratios else None,
        "min_ratio": min(ratios) if ratios else None,
    }


def _is_live_ibm_backend(backend) -> bool:
    """True only for a `qiskit_ibm_runtime.IBMBackend` (the object that has `refresh()`).

    A `FakeBackendV2` also has a `refresh()`, but it needs a `service` argument and there
    is nothing to refresh: calling it is an error, never a no-op (prompts/17 F1)."""
    try:
        from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2
        if isinstance(backend, FakeBackendV2):
            return False
    except Exception:
        pass
    try:
        from qiskit_ibm_runtime import IBMBackend
    except Exception:
        return False
    return isinstance(backend, IBMBackend)


def fresh_calibration(backend, qubits, edges) -> dict:
    """`calibration_record` on a target read in THIS invocation (prompts/17 D9, F1).

    In qiskit-ibm-runtime 0.49.0 `IBMBackend.target` calls `properties()` (cached per
    object) and rebuilds the target only `if refresh or not self._target`, so
    `properties(refresh=True)` alone leaves a stale target and a long-lived backend object
    can report a calibration that is over an hour old (observed: 71 min).  Every live read
    of the calibration in the H0 scripts goes through this function."""
    if _is_live_ibm_backend(backend):
        backend.refresh()
    return calibration_record(backend, qubits, edges)


def _prop(target, name, qubits):
    """InstructionProperties of `name` on `qubits`, or None if the target has none."""
    if name not in target.operation_names:
        return None
    try:
        return target[name].get(tuple(qubits))
    except Exception:
        return None


def _cz_key(target, edge):
    a, b = edge
    try:
        m = target["cz"]
    except Exception:
        return None
    if (a, b) in m:
        return (a, b)
    if (b, a) in m:
        return (b, a)
    return None


def calibration_record(backend, qubits, edges) -> dict:
    """The day's calibration of the qubits and edges the frozen set uses.

    `missing_errors` lists every entry whose `.error` is None -- the values
    `gate_S2D.analyse_on_backend` multiplies into f.  An empty list is the
    precondition of the prediction (prompts/15 D1, step A1)."""
    t = backend.target
    iso = last_update_date(backend)
    try:
        st = backend.status()
        status = {"operational": bool(st.operational), "pending_jobs": int(st.pending_jobs),
                  "status_msg": getattr(st, "status_msg", None)}
    except Exception as exc:
        status = {"operational": None, "pending_jobs": None, "status_msg": f"unavailable: {exc}"}

    missing = []
    qrec = {}
    for q in sorted(qubits):
        try:
            qp = backend.qubit_properties(q)
        except Exception:
            qp = None
        mp = _prop(t, "measure", (q,))
        sx = _prop(t, "sx", (q,))
        x = _prop(t, "x", (q,))
        rz = _prop(t, "rz", (q,))
        if mp is None or mp.error is None:
            missing.append({"instruction": "measure", "qubits": [int(q)]})
        for nm, pr in (("sx", sx), ("x", x)):
            if pr is not None and pr.error is None:
                missing.append({"instruction": nm, "qubits": [int(q)]})
        qrec[str(q)] = {
            "measure_error": None if mp is None or mp.error is None else float(mp.error),
            "measure_duration_s": None if mp is None or mp.duration is None else float(mp.duration),
            "sx_error": None if sx is None or sx.error is None else float(sx.error),
            "sx_duration_s": None if sx is None or sx.duration is None else float(sx.duration),
            "x_error": None if x is None or x.error is None else float(x.error),
            "x_duration_s": None if x is None or x.duration is None else float(x.duration),
            "rz_duration_s": None if rz is None or rz.duration is None else float(rz.duration),
            "T1_s": None if qp is None or qp.t1 is None else float(qp.t1),
            "T2_s": None if qp is None or qp.t2 is None else float(qp.t2),
        }

    # `edges` are the DIRECTED pairs the transpiled circuits use (ibm_account.frozen_requirements
    # counts 54 of them for the frozen set).  A cz entry of the target is symmetric and is listed
    # once, so every directed pair is resolved to its target key and each key is recorded once;
    # a pair with no entry at all lands in missing_errors.
    directed = sorted({(int(a), int(b)) for a, b in edges})
    erec, by_key = {}, {}
    for e in directed:
        key = _cz_key(t, e)
        if key is None:
            missing.append({"instruction": "cz", "qubits": [e[0], e[1]]})
            continue
        by_key.setdefault(key, []).append(e)
    for key, pairs in sorted(by_key.items()):
        pr = t["cz"].get(key)
        if pr is None or pr.error is None:
            missing.append({"instruction": "cz", "qubits": [int(key[0]), int(key[1])]})
        erec[f"{key[0]}-{key[1]}"] = {
            "target_key": [int(key[0]), int(key[1])],
            "directed_pairs_of_the_frozen_set": [list(p) for p in pairs],
            "cz_error": None if pr is None or pr.error is None else float(pr.error),
            "cz_duration_s": None if pr is None or pr.duration is None else float(pr.duration),
        }

    rec = {
        "backend": backend.name,
        "num_qubits": int(backend.num_qubits),
        "last_update_date": iso,
        "stamp": calibration_stamp(iso),
        "dt_s": None if backend.dt is None else float(backend.dt),
        "default_rep_delay_s": (None if getattr(backend, "default_rep_delay", None) is None
                                else float(backend.default_rep_delay)),
        "rep_delay_range_s": ([float(v) for v in backend.rep_delay_range]
                              if getattr(backend, "rep_delay_range", None) is not None else None),
        "max_circuits": (None if getattr(backend, "max_circuits", None) is None
                         else int(backend.max_circuits)),
        "basis_gates": sorted(t.operation_names),
        "status": status,
        "n_qubits_frozen_set": len(qrec),
        "n_edges_frozen_set": len(erec),
        "n_directed_pairs_frozen_set": len(directed),
        "qubits": qrec,
        "edges": erec,
        "missing_errors": missing,
        "missing_errors_note": ("entries of backend.target whose .error is None; "
                                "gate_S2D.analyse_on_backend multiplies these into the clean-shot "
                                "fraction f, so a non-empty list is a hard stop (prompts/15 A1), "
                                "never a defaulted value"),
    }
    # prompts/17 D9: the identity of the calibration CONTENT of the frozen patch.  It is
    # computed from the four blocks above and is therefore not a function of itself.
    rec["fingerprint"] = calibration_fingerprint(rec)
    rec["fingerprint_fields"] = list(FINGERPRINT_FIELDS)
    rec["fingerprint_note"] = (
        "sha256 of json.dumps({dt_s, default_rep_delay_s, qubits, edges}, sort_keys=True, "
        "separators=(',', ':')) -- exactly the numbers NoiseModel.from_backend, "
        "gate_S2D.analyse_on_backend and h0_qpu_time.estimate read.  The device metadata "
        "(last_update_date, stamp, status, basis_gates, max_circuits) is excluded: IBM moves "
        "the timestamp when it calibrates other parts of the 156-qubit device (prompts/17)")
    return rec


def frozen_qubits_and_edges(prep_dir):
    """(qubits, edges) of the frozen circuit set -- `ibm_account.frozen_requirements`."""
    from ibm_account import frozen_requirements
    req = frozen_requirements(prep_dir)
    return req["qubits"], req["edges"]


# --------------------------------------------------------------------------- prompts/20 C3
def backend_from_record(record: dict, base=None, strict: bool = True):
    """A backend object whose target carries the numbers of a committed calibration record.

    The post-diction of gate `H0_model` must run Aer against the calibration the device
    actually ran under -- `data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json`,
    fingerprint 7fd6d65e... -- and that record is a JSON, not a backend.  This function takes
    a base backend of the same family (default `FakeFez()`, the same 156-qubit Heron r2
    coupling map) and overwrites, for exactly the qubits and edges the record covers, the
    four blocks the prediction reads: the measure / sx / x errors and durations, the rz
    duration, the T1 and T2 of `target.qubit_properties`, and the cz error and duration of
    every target key.  Everything else of the base target is untouched, which is sound
    because the frozen circuits never leave the record's patch.

    `target.qubit_properties` is ASSIGNED as a new list: prompts/17 PC 3 established that
    editing the QubitProperties objects in place does not reach the target and therefore does
    not reach `AerSimulator.from_backend`'s relaxation pass.

    With `strict` (the default) the round trip is asserted: `calibration_record` of the
    returned backend over the record's own qubits and edges must carry the record's
    fingerprint.  That is the check that no leaf was missed.
    """
    from qiskit.providers.backend import QubitProperties
    from qiskit.transpiler.target import InstructionProperties

    if base is None:
        from qiskit_ibm_runtime.fake_provider import FakeFez
        base = FakeFez()
    t = base.target
    if record.get("dt_s") is not None and base.dt is not None:
        if abs(float(base.dt) - float(record["dt_s"])) > 1e-18:
            raise SystemExit(f"the base backend's dt {base.dt} is not the record's "
                             f"{record['dt_s']}: pick a base of the same family")
    rd = getattr(base, "default_rep_delay", None)
    if record.get("default_rep_delay_s") is not None and rd is not None:
        if abs(float(rd) - float(record["default_rep_delay_s"])) > 1e-18:
            raise SystemExit(f"the base backend's default rep delay {rd} is not the record's "
                             f"{record['default_rep_delay_s']}")

    def put(name, qargs, duration, error):
        pr = _prop(t, name, qargs)
        if pr is None:
            raise SystemExit(f"the base backend has no {name} on {tuple(qargs)}: the record "
                             f"does not fit this base target")
        t.update_instruction_properties(
            name, tuple(qargs),
            InstructionProperties(duration=pr.duration if duration is None else float(duration),
                                  error=pr.error if error is None else float(error)))

    qubits = sorted(int(q) for q in record["qubits"])
    qp = list(t.qubit_properties)
    for q in qubits:
        v = record["qubits"][str(q)]
        put("measure", (q,), v.get("measure_duration_s"), v.get("measure_error"))
        put("sx", (q,), v.get("sx_duration_s"), v.get("sx_error"))
        put("x", (q,), v.get("x_duration_s"), v.get("x_error"))
        if v.get("rz_duration_s") is not None and "rz" in t.operation_names:
            put("rz", (q,), v.get("rz_duration_s"), None)
        old = qp[q]
        qp[q] = QubitProperties(
            t1=(old.t1 if v.get("T1_s") is None else float(v["T1_s"])),
            t2=(old.t2 if v.get("T2_s") is None else float(v["T2_s"])),
            frequency=None if old is None else old.frequency)
    t.qubit_properties = qp                      # ASSIGNED, never mutated in place

    edges = set()
    for e in record["edges"].values():
        key = tuple(int(x) for x in e["target_key"])
        put("cz", key, e.get("cz_duration_s"), e.get("cz_error"))
        for pr in e.get("directed_pairs_of_the_frozen_set") or [list(key)]:
            edges.add(tuple(int(x) for x in pr))
    edges = sorted(edges)

    if strict:
        back = calibration_record(base, qubits, edges)
        if record.get("fingerprint") and back["fingerprint"] != record["fingerprint"]:
            d = calibration_diff(record, back)
            raise SystemExit(
                f"backend_from_record did not reproduce the record: fingerprint "
                f"{back['fingerprint'][:16]} against {record['fingerprint'][:16]}, "
                f"{d['n_leaves']} leaf/leaves differ ({', '.join(d['families'])})")
    return base, {"qubits": qubits, "edges": [list(e) for e in edges],
                  "base": type(base).__name__,
                  "fingerprint": record.get("fingerprint"),
                  "stamp": record.get("stamp"),
                  "last_update_date": record.get("last_update_date"),
                  "note": ("measure/sx/x error+duration, rz duration, T1/T2 and every cz "
                           "error+duration of the record's patch written into the base "
                           "target; qubit_properties assigned as a new list")}
