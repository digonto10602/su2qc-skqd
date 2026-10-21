"""Circuit access for the C5 noise study (read-only use of genie-opus's builders and of the package).

Families (owner's naming, notes/008):
  compressed_circuit_llm_2x4_classA   = genie family arch:it5:operator:pp (v1, reviewer-verified)
  compressed_circuit_llm_2x4_classB   = genie family arch:it5:input:pp    (v1, reviewer-verified)
  frozen (2x4)                        = the package's frozen circuits (counts only: data/quantinuum/circuits_2x4)
  frozen (2x3)                        = the package's frozen 2x3 circuits (data/quantinuum/circuits_2x3/*.qasm)
  compressed_circuit_llm_2x3_class[A,B], *_v2: through genie's families.get_family(name) once it is published.

v1 circuits are built exactly as reviews/001_build_circuits.py builds them: c2x4.family.archive_family("it5", cls,
peephole=True) and c2x4.family.circuit(), with every module-level CACHE of genie's modules redirected to
noise/.cache/build (gitignored) so genie's data/cache is never read or written.

IR gate list: [(name, qubits, param)], qubit k = bit k (little-endian, reference_sim.bits_to_int).
"""
from __future__ import annotations

import glob
import gzip
import hashlib
import json
import os
import pickle
import sys

import numpy as np

NOISE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # .../noise
STUDY = os.path.dirname(NOISE)                                                 # .../2x4_compression_using_ai_v1
ROOT = os.path.dirname(STUDY)                                                  # package repository
CACHE = os.path.join(NOISE, ".cache")
for p in (os.path.join(ROOT, "src"), os.path.join(STUDY, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

FAMILY_V1 = {"compressed_circuit_llm_2x4_classA": ("it5", "operator"),
             "compressed_circuit_llm_2x4_classB": ("it5", "input")}
CLASS_LETTER = {"compressed_circuit_llm_2x4_classA": "A", "compressed_circuit_llm_2x4_classB": "B"}
V1_PKL = os.path.join(CACHE, "build", "circuits_v1.pkl")


def tag(twoB: int, ref: int, k: int) -> str:
    return f"B{twoB // 2}_ref{ref}_k{k}"


def parse_tag(t: str):
    b, r, k = t.split("_")
    return 2 * int(b[1:]), int(r[3:]), int(k[1:])


# ------------------------------------------------------------------ 2x4 v1 builders
def _redirect_genie_cache():
    d = os.path.join(CACHE, "build")
    os.makedirs(d, exist_ok=True)
    import c2x4.env as env
    env.CACHE = d
    import c2x4.problem as problem
    problem.CACHE = d
    import c2x4.family as family
    family.CACHE = d
    return d


def v1_ids():
    """The 75 (twoB, ref, k) of each v1 class: 15 references (krylov.references) x k = 1..5."""
    from skqd.exact import Model
    from skqd.krylov import references
    M = Model(4)
    return [(twoB, int(r), k) for twoB in (0, 2) for r in references(M.basis, twoB) for k in range(1, 6)]


def build_v1(only=None, log=print):
    """Build (resumably) all 150 v1 circuits into noise/.cache/build/circuits_v1.pkl."""
    import time
    _redirect_genie_cache()
    from c2x4.problem import get_problem
    from c2x4.family import archive_family, circuit
    P = get_problem()
    out = pickle.load(open(V1_PKL, "rb")) if os.path.exists(V1_PKL) else {}
    fams = {f: archive_family(lab, cls, peephole=True) for f, (lab, cls) in FAMILY_V1.items()}
    for fam in fams:
        for (twoB, ref, k) in v1_ids():
            key = (fam, tag(twoB, ref, k))
            if key in out or (only and key[1] not in only):
                continue
            t0 = time.time()
            out[key] = circuit(P, fams[fam], twoB, ref, k)
            with open(V1_PKL + ".tmp", "wb") as fh:
                pickle.dump(out, fh)
            os.replace(V1_PKL + ".tmp", V1_PKL)
            log(f"{fam} {key[1]} {len(out[key])} gates {time.time() - t0:.1f}s")
    return out


_V1 = None


def v1_gates(family: str, t: str) -> list:
    global _V1
    if _V1 is None:
        _V1 = pickle.load(open(V1_PKL, "rb"))
    return _V1[(family, t)]


# ------------------------------------------------------------------ genie's published API (when it appears)
def genie_family_api():
    """genie-opus's published loader (notes/009-family-api.md): module with get_family_ir, available_families."""
    if STUDY not in sys.path:
        sys.path.insert(0, STUDY)
    try:
        import families as F            # the shim 2x4_compression_using_ai_v1/families.py
    except ImportError:
        return None
    return F


_GENIE = {}


def genie_ir(name: str) -> dict:
    """{circuit_id: (IR gate list, metadata)} of a frozen genie family (sha256-checked by genie's loader)."""
    if name not in _GENIE:
        F = genie_family_api()
        if F is None:
            raise KeyError(f"family {name}: genie's loader not available")
        _GENIE[name] = {cid: (g, md) for cid, g, md in F.get_family_ir(name)}
    return _GENIE[name]


# ------------------------------------------------------------------ frozen circuits
def frozen_2x4_counts():
    """Gate counts of the package's frozen 2x4 circuits from their committed manifests (no simulation)."""
    d = os.path.join(ROOT, "data", "quantinuum", "circuits_2x4")
    rows = {}
    for m in sorted(glob.glob(os.path.join(d, "*.manifest.json"))):
        j = json.load(open(m))
        rows[os.path.basename(m).replace(".manifest.json", "")] = j
    return rows


def frozen_2x3_ids():
    d = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "B*_ref*_k*.qasm")))


def frozen_2x3_circuit(t: str):
    """The frozen 2x3 circuit as a qiskit QuantumCircuit (from the committed OpenQASM 2 file, measurements removed)."""
    from qiskit import qasm2
    from qiskit.circuit.library import RGate, RZZGate
    p = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", t + ".qasm")
    src = open(p).read()
    if 'include "hqslib1.inc";' in src:
        # Quantinuum native: U1q(theta, phi) = exp(-i theta/2 (cos phi X + sin phi Y)) = qiskit RGate;
        # RZZ(theta) = exp(-i theta/2 ZZ) = qiskit RZZGate; rz standard.
        import re
        src = src.replace('include "hqslib1.inc";', 'include "qelib1.inc";')
        src = re.sub(r"\bU1q\(", "rgate(", src)
        src = re.sub(r"\bRZZ\(", "rzzgate(", src)
        custom = list(qasm2.LEGACY_CUSTOM_INSTRUCTIONS) + [
            qasm2.CustomInstruction("rgate", 2, 1, RGate, builtin=True),
            qasm2.CustomInstruction("rzzgate", 1, 2, RZZGate, builtin=True)]
        qc = qasm2.loads(src, custom_instructions=custom)
    else:
        qc = qasm2.loads(src, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    j = json.load(open(p[:-5] + ".json"))
    perm = j.get("implicit_permutation", [])
    if any(a != b for a, b in perm):
        raise ValueError(f"{t}: non-identity implicit permutation")
    return qc.remove_final_measurements(inplace=False)


# ------------------------------------------------------------------ IR -> qiskit (same rules as reviews/001)
def to_qiskit(gates, n):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n)
    for name, qs, par in gates:
        if name == "x": qc.x(qs[0])
        elif name == "h": qc.h(qs[0])
        elif name == "ry": qc.ry(float(par), qs[0])
        elif name == "rz": qc.rz(float(par), qs[0])
        elif name == "rx": qc.rx(float(par), qs[0])
        elif name == "p": qc.p(float(par), qs[0])
        elif name == "cx": qc.cx(qs[0], qs[1])
        elif name == "cz": qc.cz(qs[0], qs[1])
        elif name == "cp": qc.cp(float(par), qs[0], qs[1])
        elif name == "rzz": qc.rzz(float(par), qs[0], qs[1])
        elif name == "gphase": qc.global_phase += float(par)
        elif name == "unitary":
            U = np.asarray(par, dtype=complex)
            if len(qs) != 1 or U.shape != (2, 2):
                raise ValueError(f"multi-qubit unitary on {qs}: not allowed in a costed circuit")
            qc.unitary(U, [qs[0]])
        else:
            raise ValueError(f"unknown IR gate {name}")
    return qc


def circuit(lattice: str, family: str, t: str):
    """qiskit QuantumCircuit (no measurements) for (lattice, family, circuit tag)."""
    if lattice == "2x4" and family in FAMILY_V1:
        return to_qiskit(v1_gates(family, t), 28)
    if lattice == "2x3" and family == "frozen":
        return frozen_2x3_circuit(t)
    g, md = genie_ir(family)[t]
    assert md["lattice"] == lattice, (md["lattice"], lattice)
    return to_qiskit(g, int(md["n_qubits"]))


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ IR gate lists (for the sparse trajectory engine)
def ir_gates(lattice: str, family: str, t: str):
    """(IR gate list, n_qubits) of a circuit.  2x4 v1: genie's builders (this module); 2x3 frozen: the package's
    CircuitFactory(Model(3), 4.0).coarse_step(ref, k, dt) -- the IR the frozen native circuits were compiled from
    (manifest 'family' field), dt = Model(3).reference(4.0, twoB).dt as in gate_S2D.circuit_set(3)."""
    if lattice == "2x4" and family in FAMILY_V1:
        return v1_gates(family, t), 28
    twoB, ref, k = parse_tag(t)
    if lattice == "2x3" and family == "frozen":
        cp = os.path.join(CACHE, "ir", f"2x3_frozen_{t}.pkl")
        if os.path.exists(cp):
            return pickle.load(open(cp, "rb"))
        from skqd.exact import Model
        from skqd.circuits_ir import CircuitFactory
        M = Model(3)
        F = CircuitFactory(M, 4.0)
        res = (F.coarse_step(ref, k, M.reference(4.0, twoB).dt), int(F.codec.n_qubits))
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        pickle.dump(res, open(cp + ".tmp", "wb"))
        os.replace(cp + ".tmp", cp)
        return res
    g, md = genie_ir(family)[t]
    assert md["lattice"] == lattice, (md["lattice"], lattice)
    return g, int(md["n_qubits"])
