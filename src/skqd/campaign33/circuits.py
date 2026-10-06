"""
Frozen circuit families of the 2x3 campaign (prompts/33 section 1.1): QPY v13 I/O, manifests, the
canonical instruction digest used for round trips, and the logical exactness check against the exact
Krylov states.  Works on qiskit 1.4.3 (the CI) and 2.5.2 (the laptop); qiskit is imported lazily.

QPY version 13 is the newest that qiskit 1.4.3 reads (qiskit 2.5.2 writes 17 by default, which the
CI cannot load: the S2_2x4 lesson, data/S2_2x4/qpy13_3.json).  Files are gzip'ed with mtime 0 so
that the sha256 of a re-write of the same circuit is reproducible.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CIRC_DIR = os.path.join(ROOT, "data", "campaign33", "circuits")
INDEX = os.path.join(CIRC_DIR, "index.json")
QPY_VERSION = 13
AMP_TOL, LEAK_TOL = 1e-10, 1e-9          # the project's exactness bars

FAMILIES = ("IR-L0", "NAT-O0", "NAT-O0-k5", "NAT-O1", "NAT-O2", "NAT-O3", "NAT-O4", "NAT-O6", "IR-L3-RZZ",
            "IBM-T3", "IBM-T0", "IBM-U")
BASE_FAMILIES = ("IR-L0", "NAT-O0", "IBM-T3")          # a bar failure here is a STOP (prompts/33 section 8)
VARIANTS = ("NAT-O0", "NAT-O1", "NAT-O2", "NAT-O3", "NAT-O4", "NAT-O6")


def rel(p):
    return os.path.relpath(p, ROOT)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def family_dir(family):
    return os.path.join(CIRC_DIR, family)


def qpy_path(family, cid):
    return os.path.join(family_dir(family), cid + ".qpy.gz")


def manifest_path(family, cid):
    return os.path.join(family_dir(family), cid + ".json")


# --------------------------------------------------------------------------- QPY
def dump_qpy13(circ, path) -> dict:
    """Write `circ` as QPY version 13, gzip (mtime 0); return bytes, sha256 of the .gz and the header."""
    from qiskit import qpy
    buf = io.BytesIO()
    try:
        qpy.dump(circ, buf, version=QPY_VERSION)
    except TypeError:                       # a qiskit whose dump has no `version` argument writes its default
        qpy.dump(circ, buf)
    raw = buf.getvalue()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as gz:
            gz.write(raw)
    os.replace(tmp, path)
    return {"bytes_uncompressed": len(raw), "gz_sha256": sha256_file(path), "header": qpy_header(path)}


def qpy_header(path) -> dict:
    with gzip.open(path, "rb") as fh:
        b = fh.read(7)
    return {"magic": b[:6].decode("ascii", "replace"), "qpy_version": int(b[6])}


def load_qpy(path):
    from qiskit import qpy
    with gzip.open(path, "rb") as fh:
        return qpy.load(fh)


def load_circuit(family, cid):
    return load_qpy(qpy_path(family, cid))[0]


def load_manifest(family, cid):
    with open(manifest_path(family, cid)) as fh:
        return json.load(fh)


def load_index():
    with open(INDEX) as fh:
        return json.load(fh)


def family_ids(family, index=None):
    index = load_index() if index is None else index
    return list(index["families"][family]["circuits"])


# --------------------------------------------------------------------------- canonical digest
def _param_repr(p):
    try:
        return repr(float(p))
    except (TypeError, ValueError):
        a = np.asarray(p)
        if a.dtype.kind in "fc":
            return "arr:" + hashlib.sha256(np.ascontiguousarray(a.astype(complex)).tobytes()).hexdigest()[:16]
        return str(p)


def canonical_ops(circ) -> list:
    """[(name, qubits, clbits, params, duration, unit)] in circuit order -- what a round trip must keep."""
    out = []
    for inst in circ.data:
        op = inst.operation
        params = [_param_repr(p) for p in (op.params or [])]
        if op.name == "unitary":
            params = [_param_repr(op.to_matrix())]
        dur = getattr(op, "duration", None)
        unit = getattr(op, "unit", None)
        out.append([op.name, [circ.find_bit(q).index for q in inst.qubits],
                    [circ.find_bit(c).index for c in inst.clbits], params,
                    None if dur is None else repr(dur), unit if op.name == "delay" else None])
    return out


def structure_diff(a, b, tol: float = 1e-9) -> dict:
    """Instruction-by-instruction comparison of two circuits: names, qubits, clbits and delay durations
    exactly, parameters to `tol` (a routed circuit rebuilt from a dt that differs in the last digits has the
    same structure and angles equal to ~1e-15)."""
    da, db = a.data, b.data
    out = {"n_a": len(da), "n_b": len(db), "structure_equal": len(da) == len(db), "max_param_diff": 0.0,
           "first_mismatch": None}
    if not out["structure_equal"]:
        return out
    for i, (x, y) in enumerate(zip(da, db)):
        ox, oy = x.operation, y.operation
        same = (ox.name == oy.name and [a.find_bit(q).index for q in x.qubits] == [b.find_bit(q).index for q in y.qubits]
                and [a.find_bit(c).index for c in x.clbits] == [b.find_bit(c).index for c in y.clbits]
                and (ox.name != "delay" or (ox.duration == oy.duration and ox.unit == oy.unit)))
        if same and ox.name != "delay":
            for p, q in zip(ox.params or [], oy.params or []):
                try:
                    out["max_param_diff"] = max(out["max_param_diff"], abs(float(p) - float(q)))
                except (TypeError, ValueError):
                    same = same and (str(p) == str(q))
        if not same:
            out["structure_equal"] = False
            out["first_mismatch"] = {"index": i, "a": [ox.name, [a.find_bit(q).index for q in x.qubits]],
                                     "b": [oy.name, [b.find_bit(q).index for q in y.qubits]]}
            return out
    out["equal_within_tol"] = bool(out["max_param_diff"] <= tol)
    return out


def ops_digest(circ) -> str:
    blob = json.dumps({"ops": canonical_ops(circ), "num_qubits": circ.num_qubits, "num_clbits": circ.num_clbits,
                       "global_phase": repr(float(circ.global_phase))}, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def roundtrip(circ, path) -> dict:
    """Load `path` back and compare instruction by instruction with `circ`."""
    back = load_qpy(path)[0]
    a, b = canonical_ops(circ), canonical_ops(back)
    checks = {"num_qubits": circ.num_qubits == back.num_qubits, "num_clbits": circ.num_clbits == back.num_clbits,
              "global_phase": abs(float(circ.global_phase) - float(back.global_phase)) < 1e-15,
              "n_instructions": len(a) == len(b), "instruction_by_instruction": a == b,
              "count_ops": dict(circ.count_ops()) == dict(back.count_ops())}
    try:
        checks["circuit_equality"] = bool(circ == back)
    except Exception as exc:                                         # pragma: no cover
        checks["circuit_equality"] = f"not comparable: {exc}"
    return {"checks": checks, "identical": all(v is True for v in checks.values()),
            "digest": ops_digest(back)}


def counts_summary(circ) -> dict:
    ops = {k: int(v) for k, v in circ.count_ops().items()}
    n2 = sum(1 for inst in circ.data if len(inst.qubits) == 2 and inst.operation.name not in ("barrier",))
    n1 = sum(1 for inst in circ.data if len(inst.qubits) == 1
             and inst.operation.name not in ("measure", "barrier", "delay", "rz"))
    from .noise import rzz_layers
    layers = rzz_layers(circ)
    return {"ops": ops, "depth": int(circ.depth()), "n_2q": int(n2), "n_1q_nonvirtual": int(n1),
            "rzz_layers": int(max(layers)) if layers else 0, "num_qubits": int(circ.num_qubits),
            "global_phase": float(circ.global_phase)}


# --------------------------------------------------------------------------- statevectors and exactness
def unitary_part(circ):
    """The circuit without measure / barrier (global phase kept)."""
    from qiskit import QuantumCircuit
    cc = QuantumCircuit(circ.num_qubits)
    cc.global_phase = circ.global_phase
    for inst in circ.data:
        if inst.operation.name in ("measure", "barrier"):
            continue
        cc.append(inst.operation, [circ.find_bit(q).index for q in inst.qubits])
    return cc


def statevector(circ, threads: int = 0, fusion: bool = True, method: str = "aer", device: str = "CPU"):
    """Statevector of the unitary part, qubit k = bit k.  method 'aer' (double precision, fusion) or
    'quantum_info' (qiskit.quantum_info.Statevector, the independent cross-check)."""
    cc = unitary_part(circ)
    if method == "quantum_info":
        from qiskit.quantum_info import Statevector
        return np.asarray(Statevector(cc).data)
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    cc.save_statevector()
    kw = dict(method="statevector", precision="double", fusion_enable=bool(fusion),
              max_parallel_threads=int(threads))
    if device == "GPU":
        kw.update(device="GPU", cuStateVec_enable=True)
    sim = AerSimulator(**kw)
    names = {i.operation.name for i in cc.data}
    if not names <= set(sim.configuration().basis_gates) | {"save_statevector", "unitary"}:
        cc = transpile(cc, sim, optimization_level=0)
    return np.asarray(sim.run(cc, shots=1).result().data(0)["statevector"].data)


def exactness(psi_qubits, exact_psi, emb, measure_map_ok=True) -> dict:
    """max |amplitude difference| on the codewords against the exact Krylov state (raw and up to a global
    phase), leakage out of the codeword space -- the bars of gates Q0P (Q1) and K0/K1 (K5)."""
    proj = emb.project(psi_qubits)
    ov = complex(np.vdot(exact_psi, proj))
    raw = float(np.max(np.abs(proj - exact_psi)))
    dev = float(np.max(np.abs(proj * np.exp(-1j * np.angle(ov)) - exact_psi)))
    leak = float(emb.leakage(psi_qubits))
    return {"max_abs_dpsi_up_to_phase": dev, "max_abs_dpsi_raw_phase": raw, "overlap_abs": abs(ov),
            "leakage": leak, "measurement_consistent": bool(measure_map_ok),
            "ok": bool(dev < AMP_TOL and leak < LEAK_TOL and measure_map_ok)}


def measure_map(circ) -> dict:
    return {int(circ.find_bit(i.clbits[0]).index): int(circ.find_bit(i.qubits[0]).index)
            for i in circ.data if i.operation.name == "measure"}


def logical_probabilities(psi_qubits, threshold: float = 0.0) -> dict:
    """{qubit-string integer (bit k = qubit k): probability} for probabilities > threshold."""
    p = np.abs(psi_qubits) ** 2
    idx = np.flatnonzero(p > threshold)
    return {int(i): float(p[i]) for i in idx}
