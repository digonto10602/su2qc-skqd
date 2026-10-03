"""
The Quantinuum native gate set {Rz, PhasedX, ZZPhase} for the IR circuits (prompts/26, gate Q0P_2x3).

pytket is NOT a dependency of this package: it lives in the isolated venv
~/.local/share/su2qc-quantinuum/venv (created with --system-site-packages from the `coding` env, so
the pinned qiskit / aer / numpy / scipy are the same objects), and every function that needs it
imports it lazily.  The functions that need no pytket (`qiskit_to_ir`, `hqc_per_shot`, `hqc_job`,
`ir_counts`, `counts_from_pytket_readouts`, `global_phase_residual`) work in `coding` too.

Conventions (https://docs.quantinuum.com/tket/api-docs/optype.html, read 2026-10-02; pytket angles
are in HALF-TURNS, 1 half-turn = pi rad):

    Rz(a)        = exp(-i pi a Z / 2)
    Rx(a)        = exp(-i pi a X / 2),   Ry(a) = exp(-i pi a Y / 2)
    PhasedX(a,b) = Rz(b) Rx(a) Rz(-b)                (operator product)
    ZZPhase(a)   = exp(-i pi a (Z x Z) / 2),   ZZMax = ZZPhase(1/2)

The IR (src/skqd/circuits_qiskit.ir_to_qiskit, qiskit convention): rz(l) = exp(-i l Z/2),
rx(t) = exp(-i t X/2), ry(t) = exp(-i t Y/2), rzz(p) = exp(-i p (Z x Z)/2).  Hence
rz(l) -> Rz(l/pi), rx(t) -> Rx(t/pi), ry -> Ry(t/pi), rzz(p) -> ZZPhase(p/pi), and PhasedX(a, b)
reads back as the TIME-ORDERED IR  rz(-pi b), rx(pi a), rz(pi b)  (the operator product read
right-to-left; fixed by tests/test_quantinuum_native.py against Circuit.get_unitary(), not from
memory).  The global phase of a pytket circuit (`Circuit.phase`, half-turns) becomes an IR
`gphase` of pi * phase.

Qubit order: IR qubit k = pytket qubit q[k] = classical bit c[k] (measure q[k] -> c[k]).  pytket's
`BackendResult.get_counts()` returns bit tuples "in increasing lexicographic order of bits"
(pytket.backends.backendresult.BasisOrder.ilo, the default), i.e. (c[0], c[1], ...): index k of the
tuple is bit c[k] = qubit k, which is this package's bit-tuple convention (reference_sim: qubit k =
bit k).  `counts_from_pytket_readouts` checks that ordering explicitly.

Billing (https://learn.microsoft.com/en-us/azure/quantum/provider-quantinuum, read 2026-10-02):
HQC = 5 + C (N_1q + 10 N_2q + 5 N_m) / 5000 per job; N_1q = PhasedX count (Rz is virtual and "Rz
operations excluded", https://docs.quantinuum.com/systems/trainings/helios/getting_started/costing.html),
N_2q = ZZPhase + ZZMax count, N_m = initialisations + measurements, C = shots.
"""
from __future__ import annotations

import math

import numpy as np

ALLOWED_NATIVE = ("Rz", "PhasedX", "ZZPhase", "ZZMax", "Measure", "Barrier")
HQC_JOB_BASE = 5.0
HQC_DIVISOR = 5000.0
HQC_WEIGHT_1Q, HQC_WEIGHT_2Q, HQC_WEIGHT_M = 1.0, 10.0, 5.0
MAX_SHOTS_PER_JOB = 10_000         # Azure provider page; offline machine list max_n_shots 10000
MAX_HQC_PER_JOB = 500_000.0        # Azure provider page


class NativeCompileError(RuntimeError):
    """The compiled circuit left the native gate set or permuted the qubits."""


# --------------------------------------------------------------------------- no-pytket helpers
def qiskit_to_ir(qc) -> list:
    """A qiskit circuit in {rz, rx, ry, rzz, x, h} (+ global phase) -> IR list.  Measurements and
    barriers are dropped (the IR is the unitary part); anything else raises."""
    gates = []
    if abs(float(qc.global_phase)) > 0.0:
        gates.append(("gphase", [], float(qc.global_phase)))
    for inst in qc.data:
        nm = inst.operation.name
        qs = [qc.find_bit(q).index for q in inst.qubits]
        if nm in ("rz", "rx", "ry"):
            gates.append((nm, qs, float(inst.operation.params[0])))
        elif nm == "rzz":
            gates.append(("rzz", qs, float(inst.operation.params[0])))
        elif nm in ("x", "h"):
            gates.append((nm, qs, None))
        elif nm in ("measure", "barrier"):
            continue
        else:
            raise ValueError(f"qiskit_to_ir: unsupported operation {nm}")
    return gates


def ir_counts(gates: list) -> dict:
    """Gate counts of an IR list by name (gphase excluded)."""
    out = {}
    for name, _qs, _p in gates:
        if name != "gphase":
            out[name] = out.get(name, 0) + 1
    return out


def hqc_per_shot(counts: dict) -> float:
    """(N_1q + 10 N_2q + 5 N_m) / 5000 with N_m = initialisations + measurements.

    counts: `native_counts` output (n_phasedx, n_zz, n_qubits, n_meas)."""
    n_m = int(counts["n_qubits"]) + int(counts["n_meas"])
    return (HQC_WEIGHT_1Q * int(counts["n_phasedx"]) + HQC_WEIGHT_2Q * int(counts["n_zz"])
            + HQC_WEIGHT_M * n_m) / HQC_DIVISOR


def hqc_job(counts: dict, shots: int) -> float:
    """HQC of one job of `shots` shots of one circuit: 5 + C (N_1q + 10 N_2q + 5 N_m) / 5000."""
    return HQC_JOB_BASE + int(shots) * hqc_per_shot(counts)


def global_phase_residual(a: np.ndarray, b: np.ndarray) -> dict:
    """max |a - e^{i phi} b| with phi = arg <b|a> (global phase removed), plus 1 - |<a|b>|."""
    ov = complex(np.vdot(b, a))
    ph = ov / abs(ov) if abs(ov) > 0 else 1.0
    d = a - ph * b
    return {"max_abs_dpsi": float(np.max(np.abs(d))), "l2_dpsi": float(np.linalg.norm(d)),
            "one_minus_overlap": float(1.0 - abs(ov)), "phase_rad": float(np.angle(ph))}


def counts_from_pytket_readouts(counts: dict, bit_names: list) -> dict:
    """{bit tuple (index k = qubit k): n} from a pytket-style counts dict.

    counts: {tuple of 0/1 in the order of `bit_names`: n}, which is what
    `BackendResult.get_counts()` returns (BasisOrder.ilo: increasing lexicographic order of the
    bits).  bit_names: the bit order of the tuples, as [(register, index)], e.g.
    [("c", 0), ("c", 1), ...].  The function sorts by index within register "c" and refuses any
    other register, so a counts file read back from the cloud cannot silently reverse."""
    regs = {r for r, _ in bit_names}
    if regs != {"c"}:
        raise ValueError(f"expected one classical register 'c', found {sorted(regs)}")
    idx = [int(i) for _r, i in bit_names]
    order = np.argsort(idx)
    if sorted(idx) != list(range(len(idx))):
        raise ValueError(f"classical bits are not c[0..{len(idx) - 1}]: {idx}")
    out = {}
    for key, n in counts.items():
        bits = tuple(int(key[j]) for j in order)
        out[bits] = out.get(bits, 0) + int(n)
    return out


# --------------------------------------------------------------------------- pytket layer
def _pytket():
    try:
        import pytket  # noqa: F401
    except ImportError as exc:                                     # pragma: no cover
        raise ImportError("pytket is not installed in this interpreter; use the isolated venv "
                          "~/.local/share/su2qc-quantinuum/venv/bin/python (prompts/26 A1)") from exc
    import pytket
    return pytket


def ir_to_pytket(gates: list, n: int, measure: bool = True):
    """Direct IR -> pytket.Circuit writer (no pytket-qiskit).  Gates rz, rx, ry, x, h, rzz,
    gphase; with `measure`, Measure q[k] -> c[k] for every k."""
    _pytket()
    from pytket import Circuit

    c = Circuit(n, n if measure else 0)
    for name, qs, par in gates:
        if name == "rz":
            c.Rz(float(par) / math.pi, int(qs[0]))
        elif name == "rx":
            c.Rx(float(par) / math.pi, int(qs[0]))
        elif name == "ry":
            c.Ry(float(par) / math.pi, int(qs[0]))
        elif name == "rzz":
            c.ZZPhase(float(par) / math.pi, int(qs[0]), int(qs[1]))
        elif name == "x":
            c.X(int(qs[0]))
        elif name == "h":
            c.H(int(qs[0]))
        elif name == "gphase":
            c.add_phase(float(par) / math.pi)
        else:
            raise ValueError(f"ir_to_pytket: unsupported IR gate {name}")
    if measure:
        for k in range(n):
            c.Measure(k, k)
    return c


def compile_config(allow_implicit_swaps: bool = False):
    from pytket import OpType
    from pytket.extensions.quantinuum import QuantinuumBackendCompilationConfig

    return QuantinuumBackendCompilationConfig(allow_implicit_swaps=allow_implicit_swaps,
                                              target_2qb_gate=OpType.ZZPhase,
                                              preserve_qubit_names=True)


def offline_backend(device_name: str = "H2-2"):
    """QuantinuumBackend on the offline API handler: no login, no network.  Raises
    DeviceNotAvailable for a device the installed pytket-quantinuum's offline machine list does
    not carry (Helios-1 in 0.59.3)."""
    from pytket.extensions.quantinuum import QuantinuumAPIOffline, QuantinuumBackend

    be = QuantinuumBackend(device_name, api_handler=QuantinuumAPIOffline(),
                           compilation_config=compile_config(False))
    _ = be.backend_info          # the device lookup is lazy; force it so a missing entry raises here
    return be


def check_native(circ) -> None:
    """Raise NativeCompileError unless every op is in ALLOWED_NATIVE and the implicit qubit
    permutation is the identity."""
    bad = sorted({cmd.op.type.name for cmd in circ.get_commands()} - set(ALLOWED_NATIVE))
    if bad:
        raise NativeCompileError(f"non-native operations after compilation: {bad}")
    perm = circ.implicit_qubit_permutation()
    moved = {str(a): str(b) for a, b in perm.items() if a != b}
    if moved:
        raise NativeCompileError(f"non-identity implicit qubit permutation: {moved}")


def compile_native(circ, device_name: str = "H2-2", optimisation_level: int = 2):
    """QuantinuumBackend(device_name, api_handler=QuantinuumAPIOffline()).get_compiled_circuit
    with allow_implicit_swaps=False, ZZPhase as the two-qubit gate and the qubit names kept.
    Raises NativeCompileError if the result is not native or permutes the qubits."""
    _pytket()
    be = offline_backend(device_name)
    out = be.get_compiled_circuit(circ.copy(), optimisation_level=int(optimisation_level))
    check_native(out)
    return out


def _qubit_index(q) -> int:
    if q.reg_name != "q" or len(q.index) != 1:
        raise ValueError(f"expected qubits q[k], found {q}")
    return int(q.index[0])


def _bit_index(b) -> int:
    if b.reg_name != "c" or len(b.index) != 1:
        raise ValueError(f"expected bits c[k], found {b}")
    return int(b.index[0])


def _param(p) -> float:
    try:
        return float(p)
    except TypeError as exc:
        raise ValueError(f"symbolic parameter {p}") from exc


def pytket_to_ir(circ):
    """Independent reader of `circ.get_commands()` -> (IR gates, n qubits, {qubit k: bit j}).

    Rz(a) -> rz(pi a); Rx(a) -> rx(pi a); Ry(a) -> ry(pi a);
    PhasedX(a, b) -> rz(-pi b), rx(pi a), rz(pi b)  (time order);
    ZZPhase(a) -> rzz(pi a); ZZMax -> rzz(pi/2); Measure q[k] -> c[j] recorded in the map;
    Barrier skipped; the circuit's global phase (half-turns) -> gphase(pi * phase)."""
    from pytket import OpType

    gates = []
    ph = _param(circ.phase)
    if ph != 0.0:
        gates.append(("gphase", [], math.pi * ph))
    qmap = {}
    for cmd in circ.get_commands():
        t = cmd.op.type
        qs = [_qubit_index(q) for q in cmd.qubits]
        ps = [_param(p) for p in cmd.op.params]
        if t == OpType.Rz:
            gates.append(("rz", qs, math.pi * ps[0]))
        elif t == OpType.Rx:
            gates.append(("rx", qs, math.pi * ps[0]))
        elif t == OpType.Ry:
            gates.append(("ry", qs, math.pi * ps[0]))
        elif t == OpType.PhasedX:
            a, b = ps
            gates.append(("rz", qs, -math.pi * b))
            gates.append(("rx", qs, math.pi * a))
            gates.append(("rz", qs, math.pi * b))
        elif t == OpType.ZZPhase:
            gates.append(("rzz", qs, math.pi * ps[0]))
        elif t == OpType.ZZMax:
            gates.append(("rzz", qs, math.pi / 2.0))
        elif t == OpType.X:
            gates.append(("x", qs, None))
        elif t == OpType.H:
            gates.append(("h", qs, None))
        elif t == OpType.Measure:
            qmap[qs[0]] = _bit_index(cmd.bits[0])
        elif t == OpType.Barrier:
            continue
        else:
            raise ValueError(f"pytket_to_ir: unsupported operation {t.name}")
    n = circ.n_qubits
    return gates, n, qmap


def native_counts(circ) -> dict:
    """{n_phasedx, n_rz, n_zz, n_zzphase, n_zzmax, n_meas, n_qubits, depth, depth_2q, ops}."""
    from pytket import OpType

    ops = {}
    for cmd in circ.get_commands():
        nm = cmd.op.type.name
        ops[nm] = ops.get(nm, 0) + 1
    n_zzp, n_zzm = ops.get("ZZPhase", 0), ops.get("ZZMax", 0)
    return {"n_phasedx": int(ops.get("PhasedX", 0)), "n_rz": int(ops.get("Rz", 0)),
            "n_zz": int(n_zzp + n_zzm), "n_zzphase": int(n_zzp), "n_zzmax": int(n_zzm),
            "n_meas": int(ops.get("Measure", 0)), "n_qubits": int(circ.n_qubits),
            "depth": int(circ.depth()),
            "depth_2q": int(circ.depth_by_type({OpType.ZZPhase, OpType.ZZMax})),
            "ops": {k: int(v) for k, v in sorted(ops.items())}}


def to_qasm(circ) -> str:
    from pytket.qasm import circuit_to_qasm_str

    return circuit_to_qasm_str(circ, header="hqslib1")


def from_qasm(s: str):
    from pytket.qasm import circuit_from_qasm_str

    return circuit_from_qasm_str(s)


def to_json(circ) -> dict:
    return circ.to_dict()


def from_json(d: dict):
    from pytket import Circuit

    return Circuit.from_dict(d)


def versions() -> dict:
    """Installed versions of the Quantinuum stack (None when absent)."""
    from importlib import metadata

    out = {}
    for pkg in ("pytket", "pytket-quantinuum", "pytket-qiskit", "qnexus", "quantinuum-schemas"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out
