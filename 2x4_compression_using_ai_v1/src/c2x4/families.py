"""Stable loader API for the compressed circuit families (owner naming rule, notes/008; API note notes/009).

    get_family(name, measure=False) -> list of (circuit_id, qiskit.QuantumCircuit, metadata)

Every family is a FROZEN file `<lattice folder>/data/families/<name>.json.gz` written once by
`scripts/freeze_family.py` from the construction code, with a content hash (sha256 over the canonical gate lists) that the loader re-checks.  The loader
imports nothing from the construction code and nothing from `skqd`: it only needs numpy and the caller's qiskit
(any qiskit >= 1.0; the conversion uses QuantumCircuit.x/ry/rz/rx/p/h/cx/cz/cp/rzz/unitary only).

Conventions (fixed by the package, not redefined here): IR qubit k = qiskit qubit k = bit k of the basis integer
(little-endian, `skqd.reference_sim`); the codec layout of `skqd.codec`; the term order of `krylov.apply_groups`.

Lattice folders (one per lattice since notes/012; the code stays in 2x4_compression_using_ai_v1/):
  2x4 -> 2x4_compression_using_ai_v1/data/families/   2x3 -> 2x3_compression_using_ai_v1/data/families/
  2x2 -> 2x2_compression_using_ai_v1/data/families/   (FAMILY_DIRS, family_dir(name))

Family names (owner rule, notes/008):
  compressed_circuit_llm_2x4_classA_v1  (= compressed_circuit_llm_2x4_classA) operator-exact, it5, reviewed (reviews/001)
  compressed_circuit_llm_2x4_classB_v1  (= compressed_circuit_llm_2x4_classB) exact on own reference input, it5, reviewed
  compressed_circuit_llm_2x4_classA_v2 / _classB_v2                             C4 round (notes/010), when frozen
  compressed_circuit_llm_2x3_classA / _classB                                   C3 (2x3)
  compressed_circuit_llm_2x2_classA / _classB                                   2x2 (owner 2026-10-28, notes/011)

Metadata keys per circuit (all plain Python types):
  circuit_id, lattice ("2x4" | "2x3" | "2x2"), family, class ("A" | "B"), version, twoB, reference (basis index),
  reference_bits (int, the qubit string the circuit prepares with X gates), k, dt, theta (= k dt),
  n_qubits, n_2q, n_1q, depth_2q, contract, valid_use, global_phase_vs_target (phi such that the noiseless
  output equals exp(i phi) * the package's exact coarse state; 0 for class A), content_sha256 (of this circuit's
  gate list), source (how it was built), verification (the file holding its verification record).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os

import numpy as np

_STUDY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # 2x4_compression_using_ai_v1
_ROOT = os.path.dirname(_STUDY)                                                           # the package repository
FAMILY_DIR = os.path.join(_STUDY, "data", "families")          # the 2x4 families (kept for existing imports)
FAMILY_DIRS = {"2x4": FAMILY_DIR,
               "2x3": os.path.join(_ROOT, "2x3_compression_using_ai_v1", "data", "families"),
               "2x2": os.path.join(_ROOT, "2x2_compression_using_ai_v1", "data", "families")}

ALIASES = {
    "compressed_circuit_llm_2x4_classA": "compressed_circuit_llm_2x4_classA_v1",
    "compressed_circuit_llm_2x4_classB": "compressed_circuit_llm_2x4_classB_v1",
}

FAMILY_NAMES = [
    "compressed_circuit_llm_2x4_classA_v1", "compressed_circuit_llm_2x4_classB_v1",
    "compressed_circuit_llm_2x4_classA_v2", "compressed_circuit_llm_2x4_classB_v2",
    "compressed_circuit_llm_2x3_classA", "compressed_circuit_llm_2x3_classB",
    "compressed_circuit_llm_2x2_classA", "compressed_circuit_llm_2x2_classB",
]

CONTRACTS = {
    "A": ("operator-exact: equals prod_gamma exp(-i k dt H_gamma) on every codeword (term by term, all local "
          "codewords), global phase included",
          "any input in the codeword space: own reference, other references, superpositions, repeated steps, "
          "controlled versions (after the usual control construction)"),
    "B": ("input-specific: equals exp(i phi) prod_gamma exp(-i k dt H_gamma)|ref> on its OWN reference basis state "
          "only (structural reachable set, no amplitude used); the diagonal group is dropped (pure global phase phi)",
          "ONLY 'prepare own reference with X gates, one coarse step, measure in the computational basis'. "
          "NOT valid for another input, for r > 1 repetitions, Hadamard tests or controlled versions "
          "(reviews/001 note 1)"),
}


def canonical_name(name: str) -> str:
    name = ALIASES.get(name, name)
    if name not in FAMILY_NAMES:
        raise KeyError(f"unknown family {name!r}; known: {FAMILY_NAMES + sorted(ALIASES)}")
    return name


def family_lattice(name: str) -> str:
    """'2x4' | '2x3' | '2x2', read from the canonical name compressed_circuit_llm_<lattice>_class..."""
    return canonical_name(name).split("_")[3]


def family_dir(name: str) -> str:
    """The data/families/ folder of the family's lattice folder (notes/012)."""
    return FAMILY_DIRS[family_lattice(name)]


def family_path(name: str) -> str:
    return os.path.join(family_dir(name), canonical_name(name) + ".json.gz")


def available_families() -> list:
    """Names whose frozen file exists (aliases not repeated)."""
    return [n for n in FAMILY_NAMES if os.path.exists(family_path(n))]


# ------------------------------------------------------------------ gate encoding (JSON-safe, exact floats)
def encode_gates(gates: list) -> list:
    out = []
    for name, qs, par in gates:
        qs = [int(q) for q in qs]
        if name == "unitary":
            U = np.asarray(par, dtype=complex)
            enc = {"u": [[[float(U[i, j].real), float(U[i, j].imag)] for j in range(U.shape[1])]
                          for i in range(U.shape[0])]}
        elif par is None:
            enc = None
        else:
            enc = float(par)
        out.append([str(name), qs, enc])
    return out


def decode_gates(enc: list) -> list:
    out = []
    for name, qs, par in enc:
        if isinstance(par, dict):
            par = np.array([[complex(re, im) for re, im in row] for row in par["u"]], dtype=complex)
        out.append((name, list(qs), par))
    return out


def gates_sha256(enc: list) -> str:
    return hashlib.sha256(json.dumps(enc, separators=(",", ":"), sort_keys=False).encode()).hexdigest()


# ------------------------------------------------------------------ qiskit conversion (own, checked)
def ir_to_qiskit(gates: list, n: int, measure: bool = False):
    """IR gate list -> qiskit.QuantumCircuit on n qubits (IR qubit k = qiskit qubit k).  Multi-qubit `unitary`
    gates are refused (a costed circuit has none); 1-qubit `unitary` must be unitary to 1e-12."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n, n) if measure else QuantumCircuit(n)
    for name, qs, par in gates:
        if name == "x":
            qc.x(qs[0])
        elif name == "h":
            qc.h(qs[0])
        elif name == "ry":
            qc.ry(float(par), qs[0])
        elif name == "rz":
            qc.rz(float(par), qs[0])
        elif name == "rx":
            qc.rx(float(par), qs[0])
        elif name == "p":
            qc.p(float(par), qs[0])
        elif name == "cx":
            qc.cx(qs[0], qs[1])
        elif name == "cz":
            qc.cz(qs[0], qs[1])
        elif name == "cp":
            qc.cp(float(par), qs[0], qs[1])
        elif name == "rzz":
            qc.rzz(float(par), qs[0], qs[1])
        elif name == "gphase":
            qc.global_phase += float(par)
        elif name == "unitary":
            U = np.asarray(par, dtype=complex)
            if len(qs) != 1 or U.shape != (2, 2):
                raise ValueError(f"multi-qubit unitary on {qs}: not allowed in a costed circuit")
            if np.abs(U.conj().T @ U - np.eye(2)).max() > 1e-12:
                raise ValueError("non-unitary 1-qubit matrix")
            qc.unitary(U, [qs[0]])
        else:
            raise ValueError(f"unknown IR gate {name!r}")
    if measure:
        qc.measure(range(n), range(n))
    return qc


# ------------------------------------------------------------------ loading
_LOADED = {}


def load_frozen(name: str) -> dict:
    """The frozen file as a dict, with every circuit's content hash re-checked."""
    cname = canonical_name(name)
    if cname in _LOADED:
        return _LOADED[cname]
    p = family_path(cname)
    if not os.path.exists(p):
        raise FileNotFoundError(f"family {cname} is not frozen yet (expected {p}); see notes/009 for its status")
    with gzip.open(p, "rt") as fh:
        d = json.load(fh)
    for c in d["circuits"]:
        h = gates_sha256(c["gates"])
        if h != c["metadata"]["content_sha256"]:
            raise ValueError(f"{cname}/{c['metadata']['circuit_id']}: content hash mismatch ({h})")
    _LOADED[cname] = d
    return d


def get_family_ir(name: str) -> list:
    """list of (circuit_id, IR gate list, metadata) -- the package's IR form, for simulators other than qiskit."""
    d = load_frozen(name)
    return [(c["metadata"]["circuit_id"], decode_gates(c["gates"]), dict(c["metadata"])) for c in d["circuits"]]


def get_family(name: str, measure: bool = False) -> list:
    """list of (circuit_id, qiskit.QuantumCircuit, metadata) for every circuit of the family, in a fixed order
    (twoB, reference, k).  `measure=True` appends a measurement of every qubit into a classical register of the
    same size (qiskit counts keys then have qubit 0 at the right end, see skqd.reference_sim.qiskit_key_to_bits)."""
    d = load_frozen(name)
    out = []
    for c in d["circuits"]:
        md = dict(c["metadata"])
        qc = ir_to_qiskit(decode_gates(c["gates"]), md["n_qubits"], measure=measure)
        qc.name = md["circuit_id"]
        out.append((md["circuit_id"], qc, md))
    return out


def family_header(name: str) -> dict:
    """Family-level record: provenance, contract, counts summary, verification file."""
    d = load_frozen(name)
    return {k: v for k, v in d.items() if k != "circuits"}


def exact_target(md: dict):
    """The package's exact coarse state for a circuit's metadata: (codeword ints, amplitudes), complex128.

    = krylov.apply_groups(Model(Lx).terms.groups(4, mass_default(4)), e_ref, k dt) on the dressed basis, embedded
    with skqd.reference_sim.CodewordEmbedding (qubit k = bit k).  The circuit's noiseless output equals
    exp(i * md['global_phase_vs_target']) times this state (class B: the dropped diagonal group).  Imports the
    package (`skqd`) and the study's Problem lazily."""
    from .problem import get_problem
    P = get_problem(int(md["lattice"].split("x")[1]))
    return np.asarray(P.ints, dtype=np.int64), P.target(int(md["twoB"]), int(md["reference"]), int(md["k"]))


__all__ = ["get_family", "exact_target", "get_family_ir", "family_header", "available_families", "FAMILY_NAMES", "ALIASES",
           "ir_to_qiskit", "encode_gates", "decode_gates", "gates_sha256", "canonical_name", "family_path",
           "family_dir", "family_lattice", "FAMILY_DIRS"]
