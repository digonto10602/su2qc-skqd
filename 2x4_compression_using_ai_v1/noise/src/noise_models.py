"""C5 noise models built ONLY from internet-published device numbers (noise/data/device_specs_*.json).

No backend, no API call, no live calibration and no qiskit fake-backend snapshot is used.

Every model is a Pauli (stochastic) channel model, so a noisy shot is a pure-state trajectory with Pauli
insertions and the fault-free ("clean") probability of the model is exact:

  * gate error: after every native gate, a depolarizing Pauli channel whose total fault probability is the
    PROCESS infidelity r (d+1)/d of the published AVERAGE infidelity r (d = 2 for 1q, 4 for 2q):
        p_fault,1q = 3 r_1q / 2,  p_fault,2q = 5 r_2q / 4,
    each non-identity Pauli with probability p_fault/(d^2 - 1).
  * Quantinuum RZZ(theta): published emulator angle scaling r_2q(theta) = (a |theta|/pi + b) r_2q, a = 1.518,
    b = 0.241 (theta = pi/2 gives r_2q), with |theta| first reduced to [0, pi/2] (RZZ(pi - x) = (Z x Z) RZZ(-x)
    up to virtual Rz, so the compiler can always do this).
  * idle / memory error:
      - Quantinuum: memory error per qubit per depth-1 layer p_mem (Performance Validation); the circuit is
        charged D_eq = N_2q / floor(n/2) depth-1 layers (the number of maximally dense layers with the same
        2q-gate count); a Pauli-Z channel with probability p_mem on every active qubit after every floor(n/2)
        2q gates (dephasing, as the vendor's emulator memory noise is Z noise).
      - IBM, IonQ: thermal relaxation over the idle time tau of each qubit between its gates (ASAP schedule
        for IBM, serial for IonQ), in the Pauli-twirl approximation of the amplitude-damping + dephasing channel:
            p_X = p_Y = (1 - e^{-tau/T1})/4,   p_Z = (1 - e^{-tau/T2})/2 - (1 - e^{-tau/T1})/4.
        During a gate the RB error already contains decoherence, so only idle time is charged.
  * readout: classical asymmetric bit flips P(1|0), P(0|1) applied to each sampled bit string (equivalent to an
    Aer ReadoutError on every measured qubit, applied in post-processing so the flips can be counted).

Native gate sets: Quantinuum {Rz (virtual), PhasedX = qiskit RGate, RZZ(theta)}; IonQ Forte {virtual Rz,
GPi/GPi2 (a qiskit RGate with theta in {pi, pi/2} is one pulse, any other angle is charged two pulses),
ZZ(theta) = RZZ}; IBM Heron {cz, rz (virtual), sx, x}, routed on a 156-qubit heavy-hex coupling map.
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
import os
import pickle

import numpy as np

from circuits import NOISE

DATA = os.path.join(NOISE, "data")
NATIVE_CACHE = os.path.join(NOISE, ".cache", "native")

DEVICES = {
    # name: (vendor spec file, model_inputs key, kind)
    "quantinuum_h2_2": ("device_specs_quantinuum.json", "quantinuum_h2_2", "quantinuum"),
    "quantinuum_helios_1": ("device_specs_quantinuum.json", "quantinuum_helios_1", "quantinuum"),
    "ionq_forte": ("device_specs_ionq.json", "ionq_forte", "ionq"),
    "ionq_tempo": ("device_specs_ionq.json", "ionq_tempo", "ionq"),
    "ibm_heron_r2_fez": ("device_specs_ibm.json", "ibm_heron_r2_fez", "ibm"),
    "ibm_heron_r3_boston": ("device_specs_ibm.json", "ibm_heron_r3_boston", "ibm"),
}


def spec_path(device: str) -> str:
    return os.path.join(DATA, DEVICES[device][0])


def spec_sha256(device: str) -> str:
    with open(spec_path(device), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# Variants (same published numbers, one error source switched off, to show its weight):
#   *_nomem  : Quantinuum without the memory (depth-1) channel  -> gate + readout only
#   *_noidle : IonQ without idle thermal relaxation              -> gate + readout only (as IonQ's own simulator)
VARIANTS = {"quantinuum_h2_2_nomem": ("quantinuum_h2_2", {"mem_depth1": 0.0}),
            "quantinuum_helios_1_nomem": ("quantinuum_helios_1", {"mem_depth1": 0.0}),
            "ionq_forte_noidle": ("ionq_forte", {"no_idle": True}),
            "ionq_tempo_noidle": ("ionq_tempo", {"no_idle": True})}
for _v, (_b, _o) in VARIANTS.items():
    DEVICES[_v] = DEVICES[_b]


@functools.lru_cache(maxsize=None)
def params(device: str) -> dict:
    f, key, kind = DEVICES[device]
    j = json.load(open(os.path.join(DATA, f)))
    p = dict(j["model_inputs"][key])
    if device in VARIANTS:
        p.update(VARIANTS[device][1])
        p["variant_of"] = VARIANTS[device][0]
    p["kind"] = kind
    p["device"] = device
    return p


# ------------------------------------------------------------------ topology
@functools.lru_cache(maxsize=None)
def heavy_hex_156():
    """156-qubit heavy-hex graph: 8 rows of 16 qubits, 7 gaps with 4 bridge qubits each (alternating columns
    3,7,11,15 / 1,5,9,13) -> 128 + 28 = 156 qubits, 8*15 + 28*2 = 176 edges (IBM: Heron r2/r3, 156 qubits,
    heavy-hexagonal lattice, 176 two-qubit couplings). Exact bridge positions of the real chips are not used."""
    from qiskit.transpiler import CouplingMap
    rows, cols = 8, 16
    q = lambda r, c: r * cols + c                       # noqa: E731
    edges = []
    for r in range(rows):
        for c in range(cols - 1):
            edges.append((q(r, c), q(r, c + 1)))
    nxt = rows * cols
    for g in range(rows - 1):
        for c in ((3, 7, 11, 15) if g % 2 == 0 else (1, 5, 9, 13)):
            b = nxt
            nxt += 1
            edges += [(q(g, c), b), (b, q(g + 1, c))]
    assert nxt == 156 and len(edges) == 176
    both = edges + [(b, a) for a, b in edges]
    return CouplingMap(both)


# ------------------------------------------------------------------ native compilation
def _resynth_rz_r(qc):
    """Merge every run of 1q gates into (r(theta, -lam) then rz(phi + lam)); r dropped when theta ~ 0."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator
    from qiskit.synthesis import OneQubitEulerDecomposer
    dec = OneQubitEulerDecomposer("ZXZ")
    out = QuantumCircuit(qc.num_qubits, global_phase=qc.global_phase)
    pend = {}

    def flush(q):
        U = pend.pop(q, None)
        if U is None:
            return
        th, ph, lam, gp = dec.angles_and_phase(U)
        out.global_phase += gp
        if abs(th) > 1e-12:
            out.r(th, -lam, q)
            z = ph + lam
        else:
            z = ph + lam
        z = math.remainder(z, 2 * math.pi)
        if abs(z) > 1e-12:
            out.rz(z, q)
        # note: rz(z) differs from exp(-i z/2 Z) only by a global phase (accounted for exactly by qiskit)

    for ins in qc.data:
        qs = [qc.find_bit(x).index for x in ins.qubits]
        op = ins.operation
        if op.name in ("barrier", "measure"):
            continue
        if len(qs) == 1:
            U = Operator(op).data
            pend[qs[0]] = U @ pend[qs[0]] if qs[0] in pend else U
        else:
            for x in qs:
                flush(x)
            out.append(op, qs)
    for x in list(pend):
        flush(x)
    return out


def native_circuit(qc, kind: str, cache_key: str | None = None):
    """Compile a logical circuit to the native gate set of the device kind.
    Returns (native QuantumCircuit on n_sim qubits, layout dict). For IBM the routed circuit is compacted
    to the physical qubits it touches; layout['measure_map'][logical q] = compact index of its final position."""
    if cache_key:
        p = os.path.join(NATIVE_CACHE, "v2", kind, cache_key + ".pkl")
        if os.path.exists(p):
            return pickle.load(open(p, "rb"))
    from qiskit import transpile
    if kind in ("quantinuum", "ionq"):
        t = transpile(qc, basis_gates=["rz", "rx", "ry", "rzz"], optimization_level=0, seed_transpiler=7)
        nat = _resynth_rz_r(t)
        lay = {"measure_map": list(range(qc.num_qubits)), "n_physical": qc.num_qubits,
               "transpile": {"basis_gates": ["rz", "rx", "ry", "rzz"], "optimization_level": 0,
                             "seed_transpiler": 7, "coupling_map": None,
                             "then": "every run of 1q gates merged into one r (PhasedX) + one virtual rz"}}
    elif kind == "ibm":
        cm = heavy_hex_156()
        t = transpile(qc, coupling_map=cm, basis_gates=["cz", "rz", "sx", "x"], optimization_level=1,
                      seed_transpiler=7, layout_method="sabre", routing_method="sabre")
        used = sorted({t.find_bit(x).index for ins in t.data for x in ins.qubits})
        fl = t.layout.final_index_layout()            # logical qubit -> physical qubit at the end
        for p_ in fl:
            if p_ not in used:
                used.append(p_)
        used = sorted(set(used))
        idx = {p_: i for i, p_ in enumerate(used)}
        from qiskit import QuantumCircuit
        nat = QuantumCircuit(len(used), global_phase=t.global_phase)
        for ins in t.data:
            if ins.operation.name in ("barrier", "measure"):
                continue
            nat.append(ins.operation, [idx[t.find_bit(x).index] for x in ins.qubits])
        lay = {"measure_map": [idx[p_] for p_ in fl], "n_physical": len(used), "physical_qubits": used,
               "transpile": {"coupling_map": "heavy_hex_156 (noise_models.heavy_hex_156)",
                             "basis_gates": ["cz", "rz", "sx", "x"], "optimization_level": 1,
                             "seed_transpiler": 7, "layout_method": "sabre", "routing_method": "sabre"}}
    else:
        raise ValueError(kind)
    res = (nat, lay)
    if cache_key:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        pickle.dump(res, open(p, "wb"))
    return res


# ------------------------------------------------------------------ channels
def _pauli_probs_depol(p_fault: float, nq: int) -> list:
    from itertools import product
    labels = ["".join(s) for s in product("IXYZ", repeat=nq)][1:]
    return [(lab, p_fault / len(labels)) for lab in labels]


def _pta(tau: float, T1: float, T2: float):
    a = 1.0 - math.exp(-tau / T1)
    pz = (1.0 - math.exp(-tau / T2)) / 2.0 - a / 4.0
    if pz < -1e-15:
        raise ValueError("T2 > 2 T1")
    return a / 4.0, a / 4.0, max(pz, 0.0)


def rzz_angle(theta: float) -> float:
    t = abs(math.remainder(theta, math.pi))       # in [0, pi/2]
    return t


def _is_pulse_angle(th: float) -> int:
    a = abs(math.remainder(th, 2 * math.pi))
    if abs(a - math.pi) < 1e-9 or abs(a - math.pi / 2) < 1e-9:
        return 1
    return 2


def gate_events(nat, device: str):
    """List of noise events of the native circuit under the device model, in circuit order.
    Each event: (position index in nat.data after which it acts, qubits tuple, kind, pauli list [(label,p)]).
    Also returns the budget (counts, durations, sums of fault probabilities)."""
    P = params(device)
    kind = P["kind"]
    n = nat.num_qubits
    ev = []
    bud = {"n_2q": 0, "n_1q_native": 0, "n_1q_pulses": 0, "n_rz_virtual": 0, "log_clean": {"gate_1q": 0.0,
           "gate_2q": 0.0, "idle": 0.0, "memory": 0.0}, "n_events": {"gate_1q": 0, "gate_2q": 0, "idle": 0,
           "memory": 0}}

    def add(pos, qs, k, plist):
        tot = sum(p for _, p in plist)
        if tot <= 0:
            return
        ev.append((pos, tuple(qs), k, plist))
        bud["log_clean"][k] += math.log1p(-tot)
        bud["n_events"][k] += 1

    active = sorted({nat.find_bit(x).index for ins in nat.data for x in ins.qubits})
    n_act = len(active)
    # schedule for idle (IBM ASAP, IonQ serial)
    free = {q: None for q in range(n)}            # end time of last gate on q (None = not started)
    tnow = 0.0
    half = max(1, n_act // 2)
    n2_since = 0
    for pos, ins in enumerate(nat.data):
        op = ins.operation
        qs = [nat.find_bit(x).index for x in ins.qubits]
        name = op.name
        if name in ("barrier", "measure"):
            continue
        if name == "rz":
            bud["n_rz_virtual"] += 1
            continue
        # gate duration and error
        if len(qs) == 2:
            bud["n_2q"] += 1
            if kind == "quantinuum":
                r2 = P["p2"] * (P["rzz_angle_scaling"]["a"] * (rzz_angle(float(op.params[0])) / math.pi)
                                ** P["rzz_angle_scaling"]["power"] + P["rzz_angle_scaling"]["b"])
                if name != "rzz":
                    raise ValueError(name)
            else:
                r2 = P["p2"]
            pre_err = (pos, qs, "gate_2q", _pauli_probs_depol(1.25 * r2, 2))
            dur = P.get("t2q", 0.0)
        else:
            bud["n_1q_native"] += 1
            npulse = 1
            if kind == "ionq":
                if name != "r":
                    raise ValueError(name)
                npulse = _is_pulse_angle(float(op.params[0]))
            elif kind == "quantinuum" and name != "r":
                raise ValueError(name)
            bud["n_1q_pulses"] += npulse
            r1 = 1.0 - (1.0 - P["p1"]) ** npulse
            pre_err = (pos, qs, "gate_1q", _pauli_probs_depol(1.5 * r1, 1))
            dur = P.get("t1q", 0.0) * npulse
        # idle before this gate
        if kind == "ibm" and not P.get("no_idle"):
            start = max([free[q] if free[q] is not None else 0.0 for q in qs])
            for q in qs:
                if free[q] is not None and start - free[q] > 0:
                    add(pos - 0.5, (q,), "idle", list(zip("XYZ", _pta(start - free[q], P["T1"], P["T2"]))))
                free[q] = start + dur
        elif kind == "ionq":
            for q in qs:
                if free[q] is not None and tnow - free[q] > 0 and not P.get("no_idle"):
                    add(pos - 0.5, (q,), "idle", list(zip("XYZ", _pta(tnow - free[q], P["T1"], P["T2"]))))
            tnow += dur
            for q in qs:
                free[q] = tnow
        add(*pre_err)
        if kind == "quantinuum" and len(qs) == 2:
            n2_since += 1
            if n2_since == half:
                n2_since = 0
                for q in active:
                    add(pos + 0.25, (q,), "memory", [("Z", P["mem_depth1"])])
    # idle until the end (measurement) for IBM / IonQ
    if kind in ("ibm", "ionq"):
        tend = tnow if kind == "ionq" else max([v for v in free.values() if v is not None] + [0.0])
        for q in range(n):
            if free[q] is not None and tend - free[q] > 0 and not P.get("no_idle"):
                add(len(nat.data) + 0.5, (q,), "idle", list(zip("XYZ", _pta(tend - free[q], P["T1"], P["T2"]))))
        bud["duration_s"] = tend
    else:
        bud["depth1_equivalent_layers"] = bud["n_2q"] / half
    bud["n_active_qubits"] = n_act
    bud["f_gate"] = math.exp(sum(bud["log_clean"].values()))
    bud["f_parts"] = {k: math.exp(v) for k, v in bud["log_clean"].items()}
    return ev, bud


def readout_probs(device: str):
    """(P(1|0), P(0|1)) per measured qubit."""
    P = params(device)
    if P["kind"] == "quantinuum":
        return P["spam0"], P["spam1"]
    if P["kind"] == "ionq":
        return P["spam"], P["spam"]
    return P["ro_p10"], P["ro_p01"]


def noisy_circuit(nat, device: str, measure_map=None):
    """Native circuit with the model's Pauli channels inserted as Aer QuantumError instructions."""
    from qiskit import QuantumCircuit
    from qiskit_aer.noise import pauli_error
    ev, bud = gate_events(nat, device)
    by_pos = {}
    for e in ev:
        by_pos.setdefault(e[0], []).append(e)
    out = QuantumCircuit(nat.num_qubits, global_phase=nat.global_phase)
    cache = {}

    def emit(e):
        _, qs, k, plist = e
        key = (len(qs), tuple((lab, round(p, 15)) for lab, p in plist))
        if key not in cache:
            tot = sum(p for _, p in plist)
            cache[key] = pauli_error([(lab, p) for lab, p in plist] + [("I" * len(qs), 1.0 - tot)])
        # qiskit Pauli labels are little-endian (rightmost = first qubit); depolarizing set is symmetric,
        # single-qubit labels are unambiguous.
        out.append(cache[key], list(qs))

    for pos, ins in enumerate(nat.data):
        for e in sorted(by_pos.get(pos - 0.5, []), key=lambda e: e[1]):
            emit(e)
        if ins.operation.name in ("barrier", "measure"):
            continue
        out.append(ins.operation, [nat.find_bit(x).index for x in ins.qubits])
        for e in by_pos.get(pos, []):
            emit(e)
        for e in by_pos.get(pos + 0.25, []):
            emit(e)
    for e in by_pos.get(len(nat.data) + 0.5, []):
        emit(e)
    return out, bud


def analytic_f(nat, device: str, n_measured: int) -> dict:
    """Clean-shot fraction of the model: f = f_gate * (1 - eps_ro_mean)^n_measured, plus its parts."""
    _, bud = gate_events(nat, device)
    p10, p01 = readout_probs(device)
    ro = (1 - 0.5 * (p10 + p01)) ** n_measured
    return {"f": bud["f_gate"] * ro, "f_gate": bud["f_gate"], "f_readout": ro, "budget": bud}
