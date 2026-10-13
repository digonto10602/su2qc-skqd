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
    from pytket import Circuit, OpType

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
        elif name == "cx":                     # prompts/35b R4: the structured IR source
            c.CX(int(qs[0]), int(qs[1]))
        elif name == "p":                      # p(l) = diag(1, e^{il}) = U1(l/pi)
            c.add_gate(OpType.U1, [float(par) / math.pi], [int(qs[0])])
        elif name == "cp":                     # cp(l) = diag(1, 1, 1, e^{il}) = CU1(l/pi), control qs[0]
            c.add_gate(OpType.CU1, [float(par) / math.pi], [int(qs[0]), int(qs[1])])
        elif name == "unitary":
            if len(qs) != 1:
                raise ValueError(f"ir_to_pytket: only one-qubit 'unitary' gates are supported, got {len(qs)} qubits")
            from pytket.circuit import Unitary1qBox
            c.add_unitary1qbox(Unitary1qBox(np.asarray(par, dtype=complex)), int(qs[0]))
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


def compile_native(circ, device_name: str = "H2-2", optimisation_level: int = 2, pure_rebase: bool = False):
    """QuantinuumBackend(device_name, api_handler=QuantinuumAPIOffline()).get_compiled_circuit
    with allow_implicit_swaps=False, ZZPhase as the two-qubit gate and the qubit names kept.
    Raises NativeCompileError if the result is not native or permutes the qubits.

    pure_rebase=True (prompts/35 3.3): no backend pass at all, only
    `AutoRebase({Rz, PhasedX, ZZPhase})` -- every gate is rewritten in place, nothing is reordered,
    merged or cancelled (the fallback when level 0 changes the two-qubit skeleton);
    `optimisation_level` and `device_name` are then not used."""
    _pytket()
    if pure_rebase:
        from pytket import OpType
        from pytket.passes import AutoRebase

        out = circ.copy()
        AutoRebase({OpType.Rz, OpType.PhasedX, OpType.ZZPhase}).apply(out)
    else:
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
        ps = [] if t in (OpType.Unitary1qBox, OpType.Measure, OpType.Barrier) else [_param(p) for p in cmd.op.params]
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
        elif t == OpType.CX:                   # prompts/35b R4 (the structured source written by ir_to_pytket)
            gates.append(("cx", qs, None))
        elif t == OpType.U1:
            gates.append(("p", qs, math.pi * ps[0]))
        elif t == OpType.CU1:
            gates.append(("cp", qs, math.pi * ps[0]))
        elif t == OpType.Unitary1qBox:
            gates.append(("unitary", qs, np.asarray(cmd.op.get_matrix(), dtype=complex)))
        elif t == OpType.Measure:
            qmap[qs[0]] = _bit_index(cmd.bits[0])
        elif t == OpType.Barrier:
            continue
        else:
            raise ValueError(f"pytket_to_ir: unsupported operation {t.name}")
    n = circ.n_qubits
    return gates, n, qmap


# --------------------------------------------------------------------------- local equivalence (prompts/35 Q1L)
_ONE_Q = ("rz", "rx", "ry", "x", "h", "unitary")


def _one_q_matrix(name, par):
    if name == "rz":
        return np.array([[np.exp(-0.5j * par), 0.0], [0.0, np.exp(0.5j * par)]], dtype=complex)
    if name == "rx":
        c, s = math.cos(par / 2.0), math.sin(par / 2.0)
        return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)
    if name == "ry":
        c, s = math.cos(par / 2.0), math.sin(par / 2.0)
        return np.array([[c, -s], [s, c]], dtype=complex)
    if name == "x":
        return np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    if name == "h":
        r = 1.0 / math.sqrt(2.0)
        return np.array([[r, r], [r, -r]], dtype=complex)
    if name == "unitary":
        return np.asarray(par, dtype=complex)
    raise ValueError(f"local_equivalence: unsupported one-qubit gate {name}")


def _skeleton(gates: list, n: int):
    """Per qubit: the ordered list of two-qubit gates touching it (partner, angle mod 2 pi, occurrence),
    and the 2x2 products of the one-qubit gates between them (n_2q(q) + 1 segments per qubit); the
    global order of the rzz gates; gphase gates are dropped (global)."""
    I2 = np.eye(2, dtype=complex)
    seg = {q: [I2.copy()] for q in range(n)}
    seq = {q: [] for q in range(n)}
    glob = []
    for name, qs, par in gates:
        if name == "gphase":
            continue
        if name == "rzz":
            a, b = int(qs[0]), int(qs[1])
            ang = float(par)
            glob.append((min(a, b), max(a, b), ang, (a, b)))
            for q, o in ((a, b), (b, a)):
                seq[q].append((o, ang))
                seg[q].append(I2.copy())
        elif name in _ONE_Q:
            q = int(qs[0])
            seg[q][-1] = _one_q_matrix(name, par if name == "unitary" else (None if par is None else float(par))) @ seg[q][-1]
        else:
            raise ValueError(f"local_equivalence: unsupported gate {name}")
    return seq, seg, glob


def _frame_equivalence(g_ir: dict, g_nat: dict, glob: list, n: int) -> dict:
    """prompts/35b R4: equivalence of two circuits with an identical per-qubit rzz skeleton whose one-qubit frames may
    differ by local unitaries that pass through rzz(t) exactly.  The frame C_q (native-so-far = (x_q C_q) .
    source-so-far) starts at I.  The source's rzz gates are visited in its time order `glob`; before each, the two
    qubits' frames absorb their segments, C <- N_j C R_j^dag, and must be diagonal ('D') or anti-diagonal ('A') (the
    other two entries are the residual):
      D x D, A x A pass through unchanged (diagonals and X x X commute with Z x Z);
      D x A, A x D flip the sign of the angle, rzz(-t) = rzz(t) rzz(-2t), local only for t = pi/2 mod pi, where
               rzz(-+pi) = phase . Z x Z: both frames are then multiplied by Z (any other angle fails).
    After the last segment C_q must be proportional to I (residual max|C - e^{i phi} I|).  Every step is an exact
    identity, so the check proves equal unitaries up to a global phase."""
    Z = np.diag([1.0, -1.0]).astype(complex)
    C = {q: np.eye(2, dtype=complex) for q in range(n)}
    jq = {q: 0 for q in range(n)}
    worst, wpos, flips = 0.0, None, 0

    def absorb(q):
        nonlocal worst, wpos
        j = jq[q]
        M = g_nat[q][j] @ C[q] @ g_ir[q][j].conj().T
        off, dia = max(abs(M[0, 1]), abs(M[1, 0])), max(abs(M[0, 0]), abs(M[1, 1]))
        if off <= dia:
            t, r, M = "D", off, np.diag(np.diag(M))
        else:
            t, r, M = "A", dia, np.array([[0.0, M[0, 1]], [M[1, 0], 0.0]], dtype=complex)
        if r > worst:
            worst, wpos = r, {"qubit": q, "segment": j, "kind": f"frame at an rzz not diagonal / anti-diagonal ({t})"}
        C[q] = M
        jq[q] = j + 1
        return t

    for (_lo, _hi, ang, (a, b)) in glob:
        ta, tb = absorb(a), absorb(b)
        if ta != tb:
            if abs(abs(math.remainder(2.0 * ang, 2.0 * math.pi)) - math.pi) > 1e-12:
                worst = max(worst, 1.0)
                wpos = wpos if (wpos and wpos.get("kind", "").startswith("D x A")) else {
                    "pair": [a, b], "angle": ang, "kind": "D x A frames at an rzz whose angle is not pi/2 mod pi"}
                continue
            C[a], C[b] = Z @ C[a], Z @ C[b]
            flips += 1
    nseg = 0
    step_worst = worst                          # the per-segment (local) residual: frames off the commutant at an rzz
    drift, drift_rate, dpos = 0.0, 0.0, None
    for q in range(n):
        j = jq[q]
        M = g_nat[q][j] @ C[q] @ g_ir[q][j].conj().T
        r = _phase_free_residual(M, np.eye(2, dtype=complex))
        nseg += j + 1
        if r / (j + 1) > drift_rate:
            drift_rate, dpos = r / (j + 1), {"qubit": q, "segments": j + 1, "final_drift": r}
        drift = max(drift, r)
    # The final frame carries the SUM of the per-segment differences along the qubit (the frames' diagonal phases are
    # only seen at the end): the image of the per-segment bar under the triangle inequality is final <= n_seg(q) x tol,
    # i.e. the per-segment average drift_rate, which is what is compared with the per-segment bar (prompts/35b R4).
    worst = max(step_worst, drift_rate)
    if drift_rate >= step_worst:
        wpos = dict(dpos or {}, kind="final frame drift per segment (accumulated over the qubit's segments)")
    return {"max_residual": float(worst), "segments": nseg, "worst": wpos, "n_sign_flips": flips,
            "step_max_residual": float(step_worst), "final_drift_max": float(drift),
            "final_drift_per_segment_max": float(drift_rate),
            "rule": ("per-segment residual = max(frame off the rzz commutant at any rzz, final drift / n_segments of the "
                     "qubit); the final drift is the triangle-inequality sum of the per-segment differences")}


def _angle_diff(a: float, b: float) -> float:
    """|a - b| modulo 2 pi (rzz(t + 2 pi) = -rzz(t): a global phase)."""
    d = (float(a) - float(b)) % (2.0 * math.pi)
    return min(d, 2.0 * math.pi - d)


def _phase_free_residual(A, B) -> float:
    """max |A - e^{i phi} B| with phi = arg tr(B^dag A) (global phase of a 2x2 product removed)."""
    t = complex(np.trace(B.conj().T @ A))
    ph = t / abs(t) if abs(t) > 0 else 1.0
    return float(np.max(np.abs(A - ph * B)))


def local_equivalence(ir_gates: list, native_circ, n: int, tol: float = 1e-12, canonical: bool = False) -> dict:
    """Q1L of prompts/35 3.3: an exact (not statistical) equivalence proof of an IR gate list in
    {rz, rx, ry, rzz, x, h, gphase} (the circuit after the prototype transpile) and a compiled native
    pytket circuit, read back with `pytket_to_ir`.

    (i)  two-qubit skeleton: for every qubit, the ordered sequence of rzz gates touching it (partner and
         angle, angle compared modulo 2 pi to `tol`) is identical in both -- this is the circuit DAG of the
         two-qubit gates; all rzz gates commute with each other, so the per-qubit order is what fixes the
         unitary (the global order is recorded as information: pytket's command order is a topological
         order and may interleave commuting gates differently);
    (ii) for every qubit and every segment between its consecutive two-qubit gates, the 2x2 product of
         the one-qubit gates equals the IR's to `tol` after removing that segment's phase;
    (iii) measurement map q[k] -> c[k] and identity implicit permutation.
    Equal per-qubit segments around an identical skeleton give equal unitaries up to one global phase."""
    ir_n, nn, qmap = pytket_to_ir(native_circ)
    if nn != n:
        raise ValueError(f"local_equivalence: {nn} qubits in the native circuit, {n} expected")
    s_ir, g_ir, gl_ir = _skeleton(ir_gates, n)
    s_nat, g_nat, gl_nat = _skeleton(ir_n, n)
    first_diff = None
    max_angle = 0.0
    skel_ok = True
    for q in range(n):
        a, b = s_ir[q], s_nat[q]
        if len(a) != len(b):
            skel_ok = False
            first_diff = first_diff or {"qubit": q, "reason": f"{len(a)} rzz in the IR, {len(b)} native"}
            continue
        for j, ((pa, ta), (pb, tb)) in enumerate(zip(a, b)):
            d = _angle_diff(ta, tb)
            max_angle = max(max_angle, d) if pa == pb else max_angle
            if pa != pb or d >= tol:
                skel_ok = False
                if first_diff is None:
                    first_diff = {"qubit": q, "position": j, "ir": [pa, ta], "native": [pb, tb]}
    max_seg = 0.0
    n_seg = 0
    worst_seg = None
    frame_info = None
    if skel_ok:
        if canonical:                          # prompts/35b R4: frame tracking through the commutant of rzz (exact)
            fr = _frame_equivalence(g_ir, g_nat, gl_ir, n)
            max_seg, n_seg, worst_seg = fr["max_residual"], fr["segments"], fr["worst"]
            frame_info = {k: fr[k] for k in ("step_max_residual", "final_drift_max", "final_drift_per_segment_max",
                                             "n_sign_flips", "rule")}
        else:
            for q in range(n):
                for j, (A, B) in enumerate(zip(g_ir[q], g_nat[q])):
                    r = _phase_free_residual(A, B)
                    n_seg += 1
                    if r > max_seg:
                        max_seg, worst_seg = r, {"qubit": q, "segment": j}
    glob_same = (len(gl_ir) == len(gl_nat)
                 and all(x[:2] == y[:2] and _angle_diff(x[2], y[2]) < tol for x, y in zip(gl_ir, gl_nat)))
    orient_same = len(gl_ir) == len(gl_nat) and all(x[3] == y[3] for x, y in zip(gl_ir, gl_nat))
    meas_ok = qmap == {q: q for q in range(n)}
    perm_ok = all(a == b for a, b in native_circ.implicit_qubit_permutation().items())
    seg_ok = bool(skel_ok and max_seg < tol)
    return {"n_rzz_ir": len(gl_ir), "n_rzz_native": len(gl_nat),
            "skeleton_per_qubit_identical": bool(skel_ok), "skeleton_max_angle_diff": max_angle,
            "skeleton_global_order_identical": bool(glob_same), "pair_orientation_identical": bool(orient_same),
            "segments_compared": n_seg, "segments_max_residual": max_seg if skel_ok else None,
            "worst_segment": worst_seg, "first_difference": first_diff,
            "measure_map_identity": meas_ok, "implicit_permutation_identity": bool(perm_ok),
            "tol": tol, "frame_tracking": bool(canonical), "frame_info": frame_info,
            "ok": bool(seg_ok and meas_ok and perm_ok)}


CANON_TOL_HALF_TURNS = 1e-11      # pytket stores an angle within < 1e-11 half-turns of a multiple of 1/4 as that multiple
STATE_BAR = 1e-10                 # the Q1 state bar (prompts/26 Q1, unchanged by prompts/35a / 35b)
_HALF_PI = 0.5 * math.pi


def _wrap_half_turns(d: float) -> float:
    """A difference in half-turns reduced to (-1, 1]: a shift by 2 half-turns is a global sign of the rotation."""
    d = (float(d) + 1.0) % 2.0 - 1.0
    return 1.0 if d == -1.0 else d


def structured_to_rzz(gates: list) -> list:
    """prompts/35b R4: the structured IR (cx, p, cp, one-qubit unitary, ry, rz, rx, x, h, rzz) rewritten EXACTLY (up to a
    global phase) in {one-qubit gates, rzz}, in pytket's two-qubit convention (CX -> ZZPhase(+1/2), CU1(l) ->
    ZZPhase(+l/2), checked by tests/test_quantinuum_native.py against Circuit.get_unitary()):
        cx(c, t)  = h_t . rzz(pi/2)_{ct} . rz(-pi/2)_c rz(-pi/2)_t . h_t      (CZ = rzz(pi/2) rz(-pi/2) x rz(-pi/2))
        cp(l)(a, b) = x_a rzz(l/2) x_a . rz(l/2)_a rz(l/2)_b  for l in [0, pi]   (x_a rzz(t) x_a = rzz(-t)),
                    = rzz(-l/2) . rz(l/2)_a rz(l/2)_b            for l in (-pi, 0)  (l wrapped mod 2 pi first)
        p(l)      = rz(l)
    Every constant is an exact binary fraction of pi; nothing else is changed."""
    out = []
    for name, qs, par in gates:
        if name == "cx":
            c, t = int(qs[0]), int(qs[1])
            out += [("h", [t], None), ("rzz", [c, t], _HALF_PI), ("rz", [c], -_HALF_PI), ("rz", [t], -_HALF_PI),
                    ("h", [t], None)]
        elif name == "cp":
            a, b = int(qs[0]), int(qs[1])
            lam = math.remainder(float(par), 2.0 * math.pi)       # cp(l) = cp(l - 2 pi m): the same matrix
            if lam >= 0.0:                                         # pytket's choice: ZZPhase(|l| / 2) in [0, 1/2]
                out += [("x", [a], None), ("rzz", [a, b], 0.5 * lam), ("x", [a], None)]
            else:
                out.append(("rzz", [a, b], -0.5 * lam))
            out += [("rz", [a], 0.5 * lam), ("rz", [b], 0.5 * lam)]
        elif name == "p":
            out.append(("rz", qs, float(par)))
        else:
            out.append((name, qs, par))
    return out


def _param_sequences(gates: list, n: int):
    """Per qubit, in order: (name, parameter (angle in rad, matrix or None), partner or None) of every non-gphase gate;
    a two-qubit gate (rzz, cx, cp) appears on both of its qubits."""
    seq = {q: [] for q in range(n)}
    for name, qs, par in gates:
        if name == "gphase":
            continue
        if name in ("rzz", "cx", "cp"):
            a, b = int(qs[0]), int(qs[1])
            p = None if par is None else float(par)
            seq[a].append((name, p, b))
            seq[b].append((name, p, a))
        elif name == "unitary":
            seq[int(qs[0])].append((name, np.asarray(par, dtype=complex), None))
        else:
            seq[int(qs[0])].append((name, None if par is None else float(par), None))
    return seq


# operator-norm change per half-turn of angle change: rotations exp(-i t P / 2) and rzz move by <= (pi/2)|Delta a|,
# phase gates diag(1, e^{il}) and cp by <= pi |Delta a| (prompts/35a R2, extended by 35b R4 to the structured gates)
_ROUND_FACTOR = {"rz": _HALF_PI, "rx": _HALF_PI, "ry": _HALF_PI, "rzz": _HALF_PI, "p": math.pi, "cp": math.pi}


def rounding_bound(ir_gates: list, n: int) -> dict:
    """The angles (and one-qubit matrices) pytket stores for the IR -- written by `ir_to_pytket`, read back by
    `pytket_to_ir` -- against the IR's, gate by gate along every qubit.  B = sum_g c_g |Delta a_g| + sum_u ||U - U'||_op
    (c_g = pi/2 for rotations and rzz, pi for p / cp; Delta a in half-turns) bounds ||U_pytket - U_IR||_op, hence
    max|Delta psi|.  Also the incoherent ESTIMATE (pi/2) sqrt(sum Delta a^2) of prompts/35b R1 (not a bound).
    Returns the record and the read-back IR."""
    pc = ir_to_pytket(ir_gates, n, measure=False)
    back, nn, _ = pytket_to_ir(pc)
    a, b = _param_sequences(ir_gates, n), _param_sequences(back, n)
    same = nn == n and all(len(a[q]) == len(b[q]) for q in range(n))
    deltas, weighted, unorm = [], 0.0, []
    if same:
        for q in range(n):
            for (na, ta, pa), (nb, tb, pb) in zip(a[q], b[q]):
                if na != nb or pa != pb:
                    same = False
                    break
                if na == "unitary":
                    unorm.append(float(np.linalg.norm(ta - tb, 2)))
                    continue
                if ta is None or (pa is not None and q > pa):      # each two-qubit gate counted once
                    continue
                d = abs(_wrap_half_turns((ta - tb) / math.pi))
                deltas.append(d)
                weighted += _ROUND_FACTOR.get(na, _HALF_PI) * d
    d = np.asarray(deltas, float) if deltas else np.zeros(0)
    u = np.asarray(unorm, float) if unorm else np.zeros(0)
    rec = {"structure_identical": bool(same), "n_gates_compared": int(d.size), "n_unitaries_compared": int(u.size),
           "n_rounded_gates": int(np.count_nonzero(d)), "max_abs_delta": float(d.max()) if d.size else 0.0,
           "sum_abs_delta": float(d.sum()), "unit": "half-turns",
           "max_unitary_opnorm_delta": float(u.max()) if u.size else 0.0,
           "state_bound_B": float(weighted + u.sum()) if same else None,
           "incoherent_estimate_not_a_bound": float(_HALF_PI * math.sqrt(float((d ** 2).sum()))) if same else None,
           "bound": ("B = sum_g c_g |Delta a_g| + sum_u ||Delta U||_op >= ||U_pytket - U_IR||_op >= max_s |Delta psi_s| "
                     "(prompts/35a R2, 35b R4)")}
    return rec, back


def local_equivalence_35a(ir_gates: list, native_circ, n: int, structured: bool = False) -> dict:
    """Q1L.  prompts/35b R2 (binding): the conversion proof is
    (i)  the two-qubit skeleton per qubit (partners, order) of the native circuit equals the source's, every two-qubit
         angle within CANON_TOL_HALF_TURNS of the source's;
    (ii) per-qubit one-qubit segment products equal to 1e-12 against the source with pytket's stored angles substituted
         (`rounding_bound` read-back);
    plus q[k] -> c[k] and the identity permutation -> `ok`.  35a's (iii) B < STATE_BAR is RECORDED (`iii_rounding`,
    `ok_35a`) and becomes the GPU consistency criterion native-vs-source <= B + 1e-12 (35b R2).
    structured=True (35b R4): the source is the structured IR (cx, p, cp, unitary, ...); it is compared through the
    exact rewrite `structured_to_rzz`.  The raw residual against the unrounded source is `segment_residual_raw`."""
    rnd, back = rounding_bound(ir_gates, n)
    ref = structured_to_rzz(ir_gates) if structured else ir_gates
    ref_back = structured_to_rzz(back) if structured else back
    ir_n, nn, qmap = pytket_to_ir(native_circ)
    sa, sn = _param_sequences(ref, n), _param_sequences(ir_n, n)
    skel_ok, max2q, first = True, 0.0, None
    for q in range(n):
        A = [(t, p) for nm, t, p in sa[q] if nm == "rzz"]
        Bq = [(t, p) for nm, t, p in sn[q] if nm == "rzz"]
        if len(A) != len(Bq):
            skel_ok = False
            first = first or {"qubit": q, "reason": f"{len(A)} rzz in the source, {len(Bq)} native"}
            continue
        for j, ((ta, pa), (tb, pb)) in enumerate(zip(A, Bq)):
            d = abs(_wrap_half_turns((ta - tb) / math.pi))
            if pa != pb or d > CANON_TOL_HALF_TURNS:
                skel_ok = False
                first = first or {"qubit": q, "position": j, "ir": [pa, ta], "native": [pb, tb], "delta_half_turns": d}
            max2q = max(max2q, d)
    seg = local_equivalence(ref_back, native_circ, n, tol=1e-12, canonical=structured)
    raw = local_equivalence(ref, native_circ, n, tol=1e-12, canonical=structured)
    B = rnd["state_bound_B"]
    maps = qmap == {q: q for q in range(n)}
    ok = bool(skel_ok and seg["ok"] and rnd["structure_identical"] and maps)
    return {"ok": ok, "rule": "prompts/35b R2: (i) + (ii) + maps", "source": "structured" if structured else "ir",
            "ok_35a": bool(ok and B is not None and B < STATE_BAR),
            "i_skeleton": {"ok": bool(skel_ok), "max_abs_delta_2q_half_turns": max2q, "tol_half_turns": CANON_TOL_HALF_TURNS,
                           "tol_source": "pytket's own canonicalisation tolerance (prompts/35a R2)", "first_difference": first},
            "ii_segments_vs_readback": {"ok": bool(seg["ok"]), "segments_max_residual": seg["segments_max_residual"],
                                        "segments_compared": seg["segments_compared"], "tol": 1e-12,
                                        "skeleton_identical": seg["skeleton_per_qubit_identical"],
                                        "worst": seg["worst_segment"], "frame_info": seg["frame_info"]},
            "iii_rounding": dict(rnd, bar=STATE_BAR, ok=bool(B is not None and B < STATE_BAR),
                                 status="recorded (prompts/35b R2: GPU consistency criterion, not a Q1L criterion)"),
            "rounding": {k: rnd[k] for k in ("n_rounded_gates", "max_abs_delta", "sum_abs_delta", "state_bound_B",
                                             "incoherent_estimate_not_a_bound", "max_unitary_opnorm_delta")},
            "segment_residual_raw": raw["segments_max_residual"], "raw_check_of_prompts_35": raw["ok"],
            "measure_map_identity": maps,
            "implicit_permutation_identity": bool(seg["implicit_permutation_identity"]),
            "n_rzz_ir": raw["n_rzz_ir"], "n_rzz_native": raw["n_rzz_native"]}


def pytket_json_to_ir(d: dict):
    """pytket-free reader of a frozen pytket JSON (`Circuit.to_dict()`): the same IR as `pytket_to_ir` of
    `Circuit.from_dict(d)` (tests/test_quantinuum_native.py checks the equality), for environments without pytket --
    the Perlmutter `skqd` env of tokens QV_2x4_K2..K4 (prompts/35a R1).  Gates Rz, Rx, Ry, PhasedX, ZZPhase, ZZMax,
    X, H, Measure, Barrier; anything else raises."""
    def reg(a):
        name, idx = a[0], a[1]
        if len(idx) != 1:
            raise ValueError(f"expected a one-index register element, found {a}")
        return name, int(idx[0])

    def par(p):
        return float(p) if not isinstance(p, str) else float(p.strip())

    gates, qmap = [], {}
    ph = par(d.get("phase", "0"))
    if ph != 0.0:
        gates.append(("gphase", [], math.pi * ph))
    nq = 0
    for q in d.get("qubits", []):
        if q[0] != "q":
            raise ValueError(f"expected qubits q[k], found {q}")
        nq += 1
    for cmd in d["commands"]:
        t = cmd["op"]["type"]
        args = [reg(a) for a in cmd["args"]]
        ps = [par(p) for p in cmd["op"].get("params", [])]
        qs = [i for r, i in args if r == "q"]
        if t == "Rz":
            gates.append(("rz", qs, math.pi * ps[0]))
        elif t == "Rx":
            gates.append(("rx", qs, math.pi * ps[0]))
        elif t == "Ry":
            gates.append(("ry", qs, math.pi * ps[0]))
        elif t == "PhasedX":
            a, b = ps
            gates += [("rz", qs, -math.pi * b), ("rx", qs, math.pi * a), ("rz", qs, math.pi * b)]
        elif t == "ZZPhase":
            gates.append(("rzz", qs, math.pi * ps[0]))
        elif t == "ZZMax":
            gates.append(("rzz", qs, math.pi / 2.0))
        elif t == "X":
            gates.append(("x", qs, None))
        elif t == "H":
            gates.append(("h", qs, None))
        elif t == "Measure":
            (rq, iq), (rc, ic) = args
            if rq != "q" or rc != "c":
                raise ValueError(f"unexpected measure {cmd}")
            qmap[iq] = ic
        elif t == "Barrier":
            continue
        else:
            raise ValueError(f"pytket_json_to_ir: unsupported operation {t}")
    return gates, nq, qmap


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
