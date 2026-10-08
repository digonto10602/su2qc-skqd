"""
Noise scenarios of the 2x3 four-class campaign (prompts/33 section 1.2) as Qiskit Aer objects.

Every builder returns a `NoiseSpec`: the Aer `NoiseModel` (or None), a run-time circuit transform
(the parts a NoiseModel cannot express: the angle-dependent two-qubit error, initialisation flips,
memory dephasing sites, the Pauli-twirled delay channel), and a JSON-able `description` with the
channel classes, parameters, sources and what is NOT modelled.  The transforms are pure Python on
QuantumCircuit objects and run on the CI node (qiskit 1.4.3 + aer 0.15.1) as on the laptop
(qiskit 2.5.2 + aer 0.17.2); nothing here imports qiskit at module load.

Conventions (written once, used everywhere):
  * Aer `depolarizing_error(p, n)`: rho -> (1-p) rho + p I/2^n.  Its no-fault probability (the
    weight of the identity Pauli) is 1 - p (4^n - 1)/4^n: 1 - 15p/16 for n = 2, 1 - 3p/4 for n = 1.
    The published per-gate numbers are used as Aer's p (the project's A6 convention,
    `scripts/quantinuum_submit.A6_NOISE`, CF_traj); the vendor emulator's own convention (p = the
    probability of a NON-identity Pauli) differs by 16/15 and 4/3 and is recorded as a note.
  * "Rz virtual" = noiseless rz.  The native PhasedX of a frozen Quantinuum circuit reads back as
    rz . rx . rz (skqd.quantinuum_native.pytket_to_ir), so the one-qubit error on rx/ry is exactly
    one error per native one-qubit gate.
  * Readout: ReadoutError [[1 - p(1|0), p(1|0)], [p(0|1), 1 - p(0|1)]].
  * Pauli-twirled thermal relaxation (Geller & Zhou, PRA 88, 012314 (2013), arXiv:1305.2021):
    p_X = p_Y = (1 - e^{-t/T1})/4, p_Z = (1 - e^{-t/T2})/2 - (1 - e^{-t/T1})/4 (>= 0 iff T2 <= 2 T1);
    the total p_X + p_Y + p_Z = (1 - e^{-t/T1})/4 + (1 - e^{-t/T2})/2 is the per-window term of
    `skqd.idle.idle_budget`.
"""
from __future__ import annotations

import copy
import json
import math
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# --------------------------------------------------------------------------- parameters (sources in SOURCES)
E1 = {"p2": 8.3e-4, "p1": 2.8e-5, "p10": 6.7e-4, "p01": 1.2e-3}          # H2-2 performance validation (A6)
E2 = {"p2": 7.9e-4, "p1": 3.0e-5, "p10": 4.8e-4, "p01": 4.8e-4}          # Helios-1 row of the device table
E3 = {"p2": 1.29e-3, "p1": 7.3e-5, "p10": 9e-4, "p01": 1.8e-3, "p_init": 4e-5,
      "angle_a": 1.518, "angle_b": 0.241, "angle_power": 1.0}            # H2-2E emulator set (2025-07-16)
E4 = {"p2": 8e-4, "p1": 2.5e-5, "p10": 1e-6, "p01": 1e-6, "p_init": 5e-4,
      "angle_a": 1.518, "angle_b": 0.241, "angle_power": 1.0}            # Helios-1E emulator set (2025-11-18)
MEMORY_RATE_PER_S = 0.0028                                               # H2 emulator linear_dephasing_rate
T_ROUND_S = {"E5a": 0.5e-3, "E5b": 1.1e-3, "E5c": 4.4e-3}                # low / mid / high
SCALES = {"E6a": 0.5, "E6b": 2.0, "E6c": 4.0}
MATCHED_F = {"E7_0.05": 0.05, "E7_0.07": 0.07, "E7_0.10": 0.10, "E7_0.15": 0.15}
MEAN_COUNTS = {"n2": 2158, "n1": 3053, "nm": 20}                        # mean ZZPhase / PhasedX / measures (Q0P_2x3)
E8 = {"p2": 1e-3, "p1": 1e-4, "p_ro": 2e-3}                              # gate S3's declared model
T2_STAR_RATIO_SOURCE = "validation/S2D_idle.json data.t2_bracket.fallback_ratio"
COH_SOURCE = "validation/H0_ddrep.json data.trains.per_qubit.<q>.epsilon"

SOURCES = {
    "E1": "scripts/quantinuum_submit.A6_NOISE = data/quantinuum/devices_20261002.json specs.quantinuum_h2_2 "
          "(H2-2 performance-validation page, read 2026-10-02)",
    "E2": "data/quantinuum/devices_20261002.json rows.2x3|quantinuum_helios_1 (eps2, eps1, eps_ro)",
    "E3": ("docs.quantinuum.com/systems/user_guide/emulator_user_guide/emulators/h2_emulators.html and "
           ".../noise_model.html (read 2026-10-06 by the planner, prompts/33 1.2): H2-2E parameter set of 2025-07-16"),
    "E4": ".../helios_emulators.html (read 2026-10-06 by the planner, prompts/33 1.2): Helios-1E set of 2025-11-18",
    "E5": ("emulator noise_model.html linear_dephasing_rate (Pauli-Z with probability rate x duration); rate 0.0028 /s "
           "= data/quantinuum/devices_20261002.json memory_model.memory_rate_per_qubit_per_s.quantinuum_h2_1; "
           "t_round = memory_model.t_round_scenarios_s"),
    "E6": "emulator noise_model.html `scale` parameter applied to E1",
    "E7": "E1 with eps2 inverted from f_gate = (1-eps2)^n2 (1-eps1)^n1 (1-eps_ro)^nm at the mean counts (prompts/33 1.2)",
    "E8": "validation/S3.json data.declared_inputs (scripts/s3_device_model.py --eps2/--eps1/--eps-ro)",
    "I": ("data/hardware/K0_prep/ibm_kingston_full_20261006T0652Z.json through NoiseModel.from_backend on a target "
          "built from the record (no fake provider); qiskit_aer NoiseModel.from_backend docs (read 2026-10-06)"),
}


# --------------------------------------------------------------------------- the spec object
@dataclass
class NoiseSpec:
    """An Aer noise model plus the run-time transform and a JSON-able description."""
    sid: str
    noise_model: object = None
    transform: Optional[Callable] = None
    description: dict = field(default_factory=dict)
    readout: Optional[tuple] = None          # (p(1|0), p(0|1)) per qubit for the analytic f0 (None = none)
    readout_per_qubit: Optional[dict] = None  # {qubit: (p(1|0), p(0|1))} (class 2)

    def apply(self, qc):
        return qc if self.transform is None else self.transform(qc)


# --------------------------------------------------------------------------- Pauli algebra helpers
def pauli_twirl_probs(error) -> dict:
    """{Pauli label: probability} of the Pauli twirl of an Aer QuantumError (any channel):
    p_P = sum_k |Tr(P K_k)|^2 / d^2 over the Kraus operators K_k.  Labels in qiskit's order
    (rightmost character = qubit 0)."""
    from qiskit.quantum_info import Kraus, pauli_basis

    error = getattr(error, "_quantum_error", error)      # a QuantumError appended to a circuit
    ch = Kraus(error.to_quantumchannel())
    n = int(round(math.log2(ch.dim[0])))
    d = 2 ** n
    out = {}
    for P in pauli_basis(n):
        m = P.to_matrix()
        out[P.to_label()] = float(sum(abs(np.trace(m @ K)) ** 2 for K in ch.data) / d ** 2)
    return out


def identity_probability(error) -> float:
    """Weight of the identity in the Pauli twirl: the no-fault probability of the channel."""
    p = pauli_twirl_probs(error)
    return p["I" * len(next(iter(p)))]


def twirled_error(error):
    """The Pauli-twirled QuantumError (stochastic Pauli channel) of any QuantumError."""
    from qiskit_aer.noise import pauli_error
    probs = {k: v for k, v in pauli_twirl_probs(error).items() if v > 0.0}
    tot = sum(probs.values())
    return pauli_error([(k, v / tot) for k, v in probs.items()])


def pta_relaxation_probs(t: float, t1: float, t2: float) -> dict:
    """Closed-form Pauli twirl of thermal relaxation over a window t (excited-state population 0)."""
    a = 1.0 - math.exp(-t / t1) if t1 and math.isfinite(t1) else 0.0
    b = 1.0 - math.exp(-t / t2) if t2 and math.isfinite(t2) else 0.0
    px = py = a / 4.0
    pz = b / 2.0 - a / 4.0
    return {"I": 1.0 - px - py - pz, "X": px, "Y": py, "Z": pz}


def pta_total(t: float, t1: float, t2: float) -> float:
    """(1 - e^{-t/T1})/4 + (1 - e^{-t/T2})/2: the idle.py per-window term."""
    p = pta_relaxation_probs(t, t1, t2)
    return p["X"] + p["Y"] + p["Z"]


def truncate_t2(t1, t2):
    """Aer's rule (`_truncate_t2_value`): T2 <= 2 T1."""
    if t1 is None or t2 is None:
        return t2
    return min(float(t2), 2.0 * float(t1))


# --------------------------------------------------------------------------- the Quantinuum-class scenarios
def angle_factor(theta: float, a: float, b: float, power: float = 1.0) -> float:
    """p2(theta)/p2 = a |theta/pi|^power + b with theta wrapped to (-pi, pi] (an rzz angle beyond pi is
    the same gate as theta - 2 pi up to a global phase).  1.0 at theta = pi/2 for the H2/Helios sets."""
    t = math.remainder(float(theta), 2.0 * math.pi)
    if t <= -math.pi:
        t += 2.0 * math.pi
    return a * (abs(t) / math.pi) ** power + b


def _readout_error(p10, p01):
    from qiskit_aer.noise import ReadoutError
    return ReadoutError([[1.0 - p10, p10], [p01, 1.0 - p01]])


def _model(p2, p1, p10, p01, two_q=("rzz",), one_q=("rx", "ry"), basis=("rz", "rx", "ry", "rzz", "id")):
    from qiskit_aer.noise import NoiseModel, depolarizing_error
    nm = NoiseModel(basis_gates=list(basis))
    if p2 is not None and p2 > 0 and two_q:
        nm.add_all_qubit_quantum_error(depolarizing_error(p2, 2), list(two_q))
    if p1 > 0 and one_q:
        nm.add_all_qubit_quantum_error(depolarizing_error(p1, 1), list(one_q))
    if p10 > 0 or p01 > 0:
        nm.add_all_qubit_readout_error(_readout_error(p10, p01))
    return nm


def _insert_errors(qc, after: Callable = None, before_all=None):
    """A new circuit with QuantumError instructions inserted: `after(inst, qubit_indices)` returns a list
    of (error, qubits) to append right after `inst`; `before_all` a list of (error, qubits) at the start."""
    out = qc.copy_empty_like()
    for err, qs in (before_all or []):
        out.append(err, [out.qubits[q] for q in qs])
    for inst in qc.data:
        out.append(inst)
        if after is not None:
            for err, qs in after(inst, [qc.find_bit(q).index for q in inst.qubits]) or []:
                out.append(err, [out.qubits[q] for q in qs])
    return out


def angle_dependent_transform(p2, a, b, power=1.0):
    """The emulator's angle-dependent two-qubit depolarizing error after every rzz (LocalNoisePass form)."""
    from qiskit_aer.noise import depolarizing_error

    cache = {}

    def after(inst, qs):
        if inst.operation.name != "rzz":
            return None
        th = float(inst.operation.params[0])
        p = p2 * angle_factor(th, a, b, power)
        key = round(p, 15)
        if key not in cache:
            cache[key] = depolarizing_error(min(p, 16.0 / 15.0), 2)
        return [(cache[key], qs)]
    return after


def init_flip_errors(n, p_init):
    from qiskit_aer.noise import pauli_error
    e = pauli_error([("X", p_init), ("I", 1.0 - p_init)])
    return [(e, [q]) for q in range(n)]


def rzz_layers(qc) -> list:
    """ASAP two-qubit layer (1-based) of every rzz in circuit order: L = 1 + max(layer of its qubits so far)."""
    d, out = {}, []
    for inst in qc.data:
        if inst.operation.name == "rzz":
            qs = [qc.find_bit(q).index for q in inst.qubits]
            L = 1 + max(d.get(q, 0) for q in qs)
            for q in qs:
                d[q] = L
            out.append(L)
    return out


def memory_transform(p_mem: float):
    """E5: a Pauli-Z error with probability p_mem on EVERY qubit after EVERY two-qubit layer.

    Placement (documented choice, prompts/33 A3): layers are the ASAP depth over rzz; on a qubit q the
    site of layer L is appended right after q's own rzz of layer L when q takes part in it, and
    otherwise right before q's next rzz (after the one-qubit gates in between), the sites of layers
    after q's last rzz before the measurements.  Every qubit gets exactly one site per layer, so a
    circuit gets n_qubits x n_layers sites (Z flips of one qubit commute with each other)."""
    from qiskit_aer.noise import pauli_error
    zerr = pauli_error([("Z", p_mem), ("I", 1.0 - p_mem)])

    def transform(qc):
        n = qc.num_qubits
        layers = rzz_layers(qc)
        n_layers = max(layers) if layers else 0
        placed = {q: 0 for q in range(n)}           # last layer whose site is placed on q
        out = qc.copy_empty_like()
        li = iter(layers)
        sites = 0
        measured_started = False
        for inst in qc.data:
            name = inst.operation.name
            qs = [qc.find_bit(q).index for q in inst.qubits]
            if name in ("measure", "barrier") and not measured_started and name == "measure":
                measured_started = True
                for q in range(n):                  # remaining layers on every qubit
                    for _ in range(n_layers - placed[q]):
                        out.append(zerr, [out.qubits[q]])
                        sites += 1
                    placed[q] = n_layers
            if name == "rzz":
                L = next(li)
                for q in qs:                        # layers strictly before L not yet placed on q
                    for _ in range(L - 1 - placed[q]):
                        out.append(zerr, [out.qubits[q]])
                        sites += 1
                    placed[q] = L - 1
                out.append(inst)
                for q in qs:                        # the site of layer L itself
                    out.append(zerr, [out.qubits[q]])
                    sites += 1
                    placed[q] = L
                continue
            out.append(inst)
        if not measured_started:
            for q in range(n):
                for _ in range(n_layers - placed[q]):
                    out.append(zerr, [out.qubits[q]])
                    sites += 1
        out.metadata = dict(qc.metadata or {}, memory_sites=sites, memory_layers=n_layers)
        return out
    return transform


def _compose_transforms(*fs):
    fs = [f for f in fs if f is not None]
    if not fs:
        return None

    def t(qc):
        for f in fs:
            qc = f(qc)
        return qc
    return t


def quantinuum_spec(sid: str, n_qubits: int = 20) -> NoiseSpec:
    """E0-E8 (prompts/33 1.2) for circuits in {rz, rx, ry, rzz, measure, barrier}."""
    desc = {"id": sid, "class": None, "channel_classes": [], "parameters": {}, "source": None, "not_modelled": [],
            "aer_convention": ("depolarizing_error(p, n): rho -> (1-p) rho + p I/2^n; fault probability "
                               "15p/16 (n=2), 3p/4 (n=1); the published number is Aer's p (the A6 / CF_traj "
                               "convention).  The vendor emulator's p is the probability of a non-identity Pauli "
                               "(16/15 resp. 4/3 times larger fault rate in Aer's convention): not converted.")}
    if sid == "E0":
        desc.update({"class": "none", "channel_classes": [], "source": "ideal statevector sampling"})
        return NoiseSpec(sid, None, None, desc, readout=None)
    if sid in ("E1", "E2") or sid in SCALES or sid in MATCHED_F:
        base = dict(E1 if sid != "E2" else E2)
        if sid in SCALES:
            s = SCALES[sid]
            base = {k: v * s for k, v in E1.items()}
            desc["parameters"]["scale"] = s
        if sid in MATCHED_F:
            f = MATCHED_F[sid]
            base = dict(E1)
            base["p2"] = matched_f_eps2(f)
            desc["parameters"]["f_target"] = f
            desc["parameters"]["matched_f_rule"] = ("f_gate = (1-eps2)^n2 (1-eps1)^n1 (1-eps_ro)^nm at the mean counts "
                                                    f"{MEAN_COUNTS}, eps1 = {E1['p1']}, eps_ro = mean(p10, p01) = "
                                                    f"{(E1['p10'] + E1['p01']) / 2}")
        nm = _model(base["p2"], base["p1"], base["p10"], base["p01"])
        desc.update({"class": "depolarizing + readout",
                     "channel_classes": ["2q depolarizing on rzz", "1q depolarizing on rx/ry (= native PhasedX)",
                                         "asymmetric readout", "rz virtual (noiseless)"],
                     "source": SOURCES["E2" if sid == "E2" else ("E6" if sid in SCALES else
                                                                 ("E7" if sid in MATCHED_F else "E1"))]})
        desc["parameters"].update(base)
        desc["not_modelled"] = ["memory / transport dephasing", "leakage", "crosstalk", "initialisation error"]
        return NoiseSpec(sid, nm, None, desc, readout=(base["p10"], base["p01"]))
    if sid in ("E3", "E4"):
        P = E3 if sid == "E3" else E4
        nm = _model(None, P["p1"], P["p10"], P["p01"], two_q=())
        after = angle_dependent_transform(P["p2"], P["angle_a"], P["angle_b"], P["angle_power"])
        before = init_flip_errors(n_qubits, P["p_init"])

        def tr(qc, after=after, before=before):
            return _insert_errors(qc, after=after, before_all=before)
        desc.update({"class": "emulator parameter set (" + ("H2-2E 2025-07-16" if sid == "E3" else "Helios-1E 2025-11-18") + ")",
                     "channel_classes": ["2q depolarizing after every rzz with angle-dependent rate "
                                         "p2 (a |theta|/pi + b) (theta wrapped to (-pi, pi])",
                                         "1q depolarizing on rx/ry", "asymmetric readout",
                                         "initialisation X flip with p_init on every qubit at the start",
                                         "rz virtual (noiseless)"],
                     "parameters": dict(P), "source": SOURCES[sid]})
        desc["not_modelled"] = (["emission ratios (0.32 / 0.59)", "crosstalk (8.8e-6 / 9.6e-6)",
                                 "coherent quadratic dephasing", "memory / transport dephasing"]
                                if sid == "E3" else
                                ["leakage (p_prep_leak 0.75 of p_init, seepage 1/3): no leakage channel in Aer "
                                 "(vendor leak2depolar=False)", "crosstalk", "coherent dephasing",
                                 "memory / transport dephasing"])
        return NoiseSpec(sid, nm, tr, desc, readout=(P["p10"], P["p01"]))
    if sid in T_ROUND_S:
        p_mem = MEMORY_RATE_PER_S * T_ROUND_S[sid]
        nm = _model(E1["p2"], E1["p1"], E1["p10"], E1["p01"])
        desc.update({"class": "E1 + memory (transport/idle) dephasing",
                     "channel_classes": ["E1 channels", "Pauli Z with p_mem on every qubit after every 2q layer"],
                     "parameters": dict(E1, p_mem=p_mem, rate_per_s=MEMORY_RATE_PER_S, t_round_s=T_ROUND_S[sid]),
                     "source": SOURCES["E5"],
                     "placement": memory_transform.__doc__.split("Placement")[1].strip()})
        desc["not_modelled"] = ["the coherent quadratic dephasing sin^2(f d / 2), f = 0.043", "leakage", "crosstalk"]
        return NoiseSpec(sid, nm, memory_transform(p_mem), desc, readout=(E1["p10"], E1["p01"]))
    if sid == "E8":
        nm = _model(E8["p2"], E8["p1"], E8["p_ro"], E8["p_ro"], one_q=("rz", "rx", "ry"))
        desc.update({"class": "gate-S3 declared model", "channel_classes": [
            "2q depolarizing on rzz", "1q depolarizing on rz, rx, ry (rz NOT virtual)", "symmetric readout"],
            "parameters": dict(E8), "source": SOURCES["E8"]})
        desc["not_modelled"] = ["memory", "leakage", "crosstalk"]
        return NoiseSpec(sid, nm, None, desc, readout=(E8["p_ro"], E8["p_ro"]))
    raise ValueError(f"unknown scenario {sid}")


QUANTINUUM_SCENARIOS = ("E0", "E1", "E2", "E3", "E4", "E5a", "E5b", "E5c", "E6a", "E6b", "E6c",
                        "E7_0.05", "E7_0.07", "E7_0.10", "E7_0.15", "E8")


# --------------------------------------------------------------------------- matched f (E7)
def matched_f_eps2(f: float, n2: int = MEAN_COUNTS["n2"], n1: int = MEAN_COUNTS["n1"],
                   nm: int = MEAN_COUNTS["nm"], eps1: float = E1["p1"], eps_ro: float = None) -> float:
    """eps2 with (1-eps2)^n2 (1-eps1)^n1 (1-eps_ro)^nm = f (eps_ro default: mean of the H2-2 SPAM values)."""
    eps_ro = (E1["p10"] + E1["p01"]) / 2.0 if eps_ro is None else eps_ro
    rest = (1.0 - eps1) ** n1 * (1.0 - eps_ro) ** nm
    return 1.0 - (float(f) / rest) ** (1.0 / n2)


def f_gate(eps2, n2=MEAN_COUNTS["n2"], n1=MEAN_COUNTS["n1"], nm=MEAN_COUNTS["nm"], eps1=E1["p1"], eps_ro=None):
    eps_ro = (E1["p10"] + E1["p01"]) / 2.0 if eps_ro is None else eps_ro
    return (1.0 - eps2) ** n2 * (1.0 - eps1) ** n1 * (1.0 - eps_ro) ** nm


def device_table_eps2_f010(path=None) -> float:
    path = path or os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")
    with open(path) as fh:
        return float(json.load(fh)["rows"]["2x3|quantinuum_h2_2"]["eps2_for_mean_f_0.1"])


# --------------------------------------------------------------------------- analytic fault-free fraction
def f0_quantinuum(qc, spec: NoiseSpec, ref_bits=None) -> dict:
    """The fault-free fraction of one circuit under a Quantinuum-class scenario: the product of the
    no-fault probabilities of every noisy site (Aer convention) and, separately, times the readout
    survival of `ref_bits` (bit k = clbit k = qubit k)."""
    sid = spec.sid
    d = spec.description["parameters"]
    if sid == "E0":
        return {"g0": 1.0, "f0": 1.0, "readout_survival": 1.0}
    names = [(inst.operation.name, inst.operation.params) for inst in qc.data]
    n2 = sum(1 for nm_, _ in names if nm_ == "rzz")
    one_q_names = ("rz", "rx", "ry") if sid == "E8" else ("rx", "ry")
    n1 = sum(1 for nm_, _ in names if nm_ in one_q_names)
    logg = n1 * math.log1p(-0.75 * d["p1"]) if d.get("p1") else 0.0
    if sid in ("E3", "E4"):
        for nm_, ps in names:
            if nm_ == "rzz":
                p = d["p2"] * angle_factor(float(ps[0]), d["angle_a"], d["angle_b"], d["angle_power"])
                logg += math.log1p(-15.0 / 16.0 * p)
        logg += qc.num_qubits * math.log1p(-d["p_init"])
    else:
        logg += n2 * math.log1p(-15.0 / 16.0 * d["p2"])
    if sid in T_ROUND_S:
        layers = rzz_layers(qc)
        L = max(layers) if layers else 0
        logg += qc.num_qubits * L * math.log1p(-d["p_mem"])
    g0 = math.exp(logg)
    rs = 1.0
    if ref_bits is not None and spec.readout is not None:
        p10, p01 = spec.readout
        n_one = int(sum(int(b) for b in ref_bits))
        n_zero = len(ref_bits) - n_one
        rs = (1.0 - p10) ** n_zero * (1.0 - p01) ** n_one
    return {"g0": g0, "f0": g0 * rs, "readout_survival": rs, "n_2q": n2, "n_1q_noisy": n1}


# --------------------------------------------------------------------------- class 2: the IBM record model
class _RecordBackend:
    """The four attributes `NoiseModel.from_backend` reads from a BackendV2 (version, target,
    operation_names, dt) -- nothing else, and no fake provider."""
    version = 2

    def __init__(self, target):
        self.target = target
        self.operation_names = list(target.operation_names)
        self.dt = target.dt

    def __repr__(self):
        return "<record backend>"


def rm_t2(t1, t2):
    """prompts/33a R2, representation RM ("reset mixture", the planner's label): T2 := min(T2, T1), so that
    Aer's thermal_relaxation_error takes its reset-mixture branch (T2 <= T1) instead of a Kraus channel."""
    if t1 is None or t2 is None:
        return t2
    return min(float(t2), float(t1))


def record_target(record: dict, t2_scale: float = 1.0, t2_cap_t1: bool = False):
    """A qiskit Target carrying the record's numbers: cz (every edge key), sx, x, rz (duration 0,
    error 0), measure, delay; qubit_properties T1 and T2 (T2 x t2_scale, then clipped to 2 T1 by Aer).
    t2_cap_t1: representation RM, T2 := min(T2 x t2_scale, T1) per qubit (prompts/33a R2)."""
    from qiskit.circuit import Delay, Measure, Parameter
    from qiskit.circuit.library import CZGate, RZGate, SXGate, XGate
    from qiskit.providers.backend import QubitProperties
    from qiskit.transpiler import InstructionProperties, Target

    n = int(record["num_qubits"])
    qp = []
    for q in range(n):
        v = record["qubits"].get(str(q)) or {}
        t1 = None if v.get("T1_s") is None else float(v["T1_s"])
        t2 = None if v.get("T2_s") is None else float(v["T2_s"]) * float(t2_scale)
        if t2_cap_t1:
            t2 = rm_t2(t1, t2)
        qp.append(QubitProperties(t1=t1, t2=t2, frequency=None))
    t = Target(num_qubits=n, dt=float(record["dt_s"]), qubit_properties=qp)
    qs = sorted(int(q) for q in record["qubits"])
    sx, x, rz, meas, dl = {}, {}, {}, {}, {}
    for q in qs:
        v = record["qubits"][str(q)]
        sx[(q,)] = InstructionProperties(duration=float(v["sx_duration_s"]), error=float(v["sx_error"]))
        x[(q,)] = InstructionProperties(duration=float(v["x_duration_s"]), error=float(v["x_error"]))
        rz[(q,)] = InstructionProperties(duration=float(v.get("rz_duration_s") or 0.0), error=0.0)
        meas[(q,)] = InstructionProperties(duration=float(v["measure_duration_s"]), error=float(v["measure_error"]))
        dl[(q,)] = None
    cz = {}
    for e in record["edges"].values():
        key = tuple(int(a) for a in e["target_key"])
        cz[key] = InstructionProperties(duration=float(e["cz_duration_s"]), error=float(e["cz_error"]))
    t.add_instruction(CZGate(), cz)
    t.add_instruction(SXGate(), sx)
    t.add_instruction(XGate(), x)
    t.add_instruction(RZGate(Parameter("theta")), rz)
    t.add_instruction(Measure(), meas)
    t.add_instruction(Delay(Parameter("t")), dl)
    return t


def kraus_record_model(record: dict, t2_scale: float = 1.0, t2_cap_t1: bool = False):
    """`NoiseModel.from_backend` (depolarizing + thermal relaxation on gates, readout, relaxation on
    delays) on the record's target: exactly Aer's own construction, version by version.  t2_cap_t1: the
    RM representation (T2 := min(T2, T1) on the target, prompts/33a R2)."""
    from qiskit_aer.noise import NoiseModel
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return NoiseModel.from_backend(_RecordBackend(record_target(record, t2_scale, t2_cap_t1)))


def _local_errors(nm) -> dict:
    """{(instruction, qubits): QuantumError} of a NoiseModel (Aer keeps them in _local_quantum_errors in
    0.15.1 and 0.17.2)."""
    out = {}
    for name, d in nm._local_quantum_errors.items():
        for qs, err in d.items():
            out[(name, tuple(qs))] = err
    return out


def t1_t2_lists(record: dict, t2_scale: float = 1.0, t2_cap_t1: bool = False):
    n = int(record["num_qubits"])
    t1s, t2s = [], []
    for q in range(n):
        v = record["qubits"].get(str(q)) or {}
        if v.get("T1_s") is None or v.get("T2_s") is None:      # no relaxation data (kingston q146)
            t1s.append(float("inf"))
            t2s.append(float("inf"))
        else:
            t1 = float(v["T1_s"])
            t1s.append(t1)
            t2 = truncate_t2(t1, float(v["T2_s"]) * float(t2_scale))
            t2s.append(rm_t2(t1, t2) if t2_cap_t1 else t2)
    return t1s, t2s


def rm_changed_qubits(record: dict, qubits, t2_scale: float = 1.0) -> dict:
    """{qubit: [T2 of the Kraus model s, T2 of RM s, T1 s]} for the qubits of `qubits` whose T2 (x t2_scale,
    clipped to 2 T1) exceeds T1 -- the only sites where RM differs from the Kraus model."""
    t1s, t2s = t1_t2_lists(record, t2_scale)
    _t1, t2r = t1_t2_lists(record, t2_scale, t2_cap_t1=True)
    return {int(q): [t2s[q], t2r[q], t1s[q]] for q in sorted(int(x) for x in qubits) if t2s[q] > t1s[q]}


def rm_vs_kraus_check(kraus_spec, rm_spec, record, active_qubits, circuit=None, t2_scale: float = 1.0) -> dict:
    """prompts/33a step B arm 2: (i) no Kraus instruction in the RM model (to_dict, and in the delay errors its
    custom pass inserts into `circuit`); (ii) on every gate site whose qubits all have T2 <= T1 (the active
    qubits outside rm_changed_qubits) the RM error equals the Kraus error (SuperOp max |diff| <= 1e-12), the
    readout errors are identical and the delay-pass T1/T2 of those qubits are identical."""
    from qiskit.quantum_info import SuperOp
    changed = rm_changed_qubits(record, active_qubits, t2_scale)
    same = sorted(int(q) for q in active_qubits if int(q) not in changed)
    ek, er = kraus_spec.local_errors, rm_spec.local_errors
    keys = [k for k in ek if all(q in same for q in k[1])]
    worst = 0.0
    for k in keys:
        a = SuperOp(ek[k].to_quantumchannel()).data
        b = SuperOp(er[k].to_quantumchannel()).data
        worst = max(worst, float(np.max(np.abs(a - b))))
    ro = max((float(np.max(np.abs(np.asarray(kraus_spec.readout_per_qubit[q]) - np.asarray(rm_spec.readout_per_qubit[q]))))
              for q in same if q in kraus_spec.readout_per_qubit), default=0.0)
    d_t = max(max(abs(kraus_spec.t1s[q] - rm_spec.t1s[q]), abs(kraus_spec.t2s[q] - rm_spec.t2s[q])) for q in same)
    pk, pr = kraus_spec.noise_model._custom_noise_passes, rm_spec.noise_model._custom_noise_passes
    d_pass = max((max(abs(float(a._t1s[q]) - float(b._t1s[q])), abs(float(a._t2s[q]) - float(b._t2s[q])))
                  for a, b in zip(pk, pr) for q in same), default=0.0)
    kr_rm = kraus_instructions(rm_spec.noise_model, circuit)
    kr_k = kraus_instructions(kraus_spec.noise_model, circuit)
    ok_same = bool(worst <= 1e-12 and ro <= 1e-12 and d_t <= 1e-15 and d_pass <= 1e-15 and len(pk) == len(pr))
    no_kraus = kr_rm["to_dict"] == 0 and kr_rm.get("custom_pass_sites", 0) == 0
    return {"changed_qubits": {str(q): {"T2_kraus_s": v[0], "T2_rm_s": v[1], "T1_s": v[2]} for q, v in changed.items()},
            "n_changed": len(changed), "unchanged_qubits": same, "n_unchanged": len(same),
            "gate_sites_compared": len(keys), "max_superop_diff_unchanged": worst, "max_readout_diff_unchanged": ro,
            "max_t1_t2_diff_unchanged_s": d_t, "max_delay_pass_t1_t2_diff_unchanged_s": d_pass,
            "kraus_in_rm": kr_rm, "kraus_in_kraus_model": kr_k,
            "identical_on_unchanged": ok_same, "rm_has_no_kraus": bool(no_kraus), "ok": bool(ok_same and no_kraus),
            "rule": "SuperOp max |diff| <= 1e-12 on every gate site whose qubits all have T2 <= T1; readout <= 1e-12; "
                    "delay T1/T2 <= 1e-15; 0 kraus instructions in RM's to_dict and in its delay-pass errors"}


def kraus_instructions(noise_model, circuit=None) -> dict:
    """Where a Kraus channel appears: in `noise_model.to_dict()` (gate and readout errors) and, when a
    circuit is given, in the errors the model's custom passes (RelaxationNoisePass on delays) insert into
    it -- the passes are not part of to_dict.  Returns {"to_dict": n, "custom_pass_sites": n_kraus,
    "custom_pass_sites_total": n}."""
    from qiskit_aer.noise import QuantumError
    d = json.dumps(noise_model.to_dict(serializable=True))
    out = {"to_dict": d.count('"kraus"')}
    if circuit is not None:
        pm = noise_model._pass_manager()
        n_k, n_tot = 0, 0
        if pm is not None:
            qc = pm.run(circuit)
            for inst in qc.data:
                op = inst.operation
                # the pass appends QuantumChannelInstruction(QuantumError) (aer 0.15.1 and 0.17.2)
                err = op if isinstance(op, QuantumError) else getattr(op, "_quantum_error", None)
                if err is not None:
                    n_tot += 1
                    if '"kraus"' in json.dumps(err.to_dict(), default=str):
                        n_k += 1
        out.update({"custom_pass_sites": n_k, "custom_pass_sites_total": n_tot})
    return out


def delay_seconds(inst, dt: float) -> float:
    op = inst.operation
    unit = getattr(op, "unit", "dt")
    dur = float(op.duration if getattr(op, "duration", None) is not None else op.params[0])
    if unit == "dt":
        return dur * float(dt)
    scale = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12}[unit]
    return dur * scale


def pta_delay_transform(t1s, t2s, dt):
    """Pauli-twirled relaxation after every delay (LocalNoisePass semantics, method append)."""
    from qiskit_aer.noise import pauli_error
    cache = {}

    def after(inst, qs):
        if inst.operation.name != "delay":
            return None
        t = delay_seconds(inst, dt)
        q = qs[0]
        key = (q, round(t, 15))
        if key not in cache:
            p = pta_relaxation_probs(t, t1s[q], t2s[q])
            terms = [(k, v) for k, v in p.items() if v > 0.0]
            cache[key] = pauli_error(terms) if len(terms) > 1 or terms[0][0] != "I" else None
        e = cache[key]
        return None if e is None else [(e, [q])]
    return after


def ibm_spec(record: dict, cell: str, representation: str = "kraus", t2_convention: str = "echo",
             t2_star_ratio: float = None, coherent_eps: dict = None) -> NoiseSpec:
    """Class 2 (prompts/33 1.2): I-GATE, I-ECHO, I-STAR, I-XY4, I-COH on the committed record.

    representation: "kraus" (from_backend as is: Kraus relaxation on gates, RelaxationNoisePass on delays),
    "rm" (prompts/33a R2: the same construction with T2 := min(T2, T1) per qubit, so every relaxation site
    is Aer's reset mixture and no Kraus channel exists; non-unital like Kraus, overstates dephasing where
    T2 > T1) or "pta" (every gate error replaced by its Pauli twirl, the delays by the closed-form twirl).
    t2_convention: "echo" (the record's Hahn-echo T2) or "star" (T2* = ratio x T2_echo on every qubit,
    gates and delays alike, as gate_H0P.apply_t2_override).  coherent_eps: {qubit: eps rad} for I-COH:
    Rx(eps) composed after the x error of that qubit (coherent, never twirled)."""
    from qiskit_aer.noise import NoiseModel, coherent_unitary_error
    from qiskit.circuit.library import RXGate

    if representation not in ("kraus", "rm", "pta"):
        raise ValueError(representation)
    scale = 1.0 if t2_convention == "echo" else float(t2_star_ratio)
    cap = representation == "rm"
    kraus = kraus_record_model(record, scale, t2_cap_t1=cap)
    t1s, t2s = t1_t2_lists(record, scale, t2_cap_t1=cap)
    dt = float(record["dt_s"])
    errs = _local_errors(kraus)
    nm = NoiseModel(basis_gates=list(kraus.basis_gates))
    for (name, qs), err in errs.items():
        e = twirled_error(err) if representation == "pta" else err
        if coherent_eps and name == "x" and qs[0] in coherent_eps:
            e = e.compose(coherent_unitary_error(RXGate(float(coherent_eps[qs[0]])).to_matrix()))
        nm.add_quantum_error(e, name, list(qs), warnings=False)
    ro = {}
    for qs, rerr in kraus._local_readout_errors.items():
        nm.add_readout_error(rerr, list(qs), warnings=False)
        p = np.asarray(rerr.probabilities)
        ro[int(qs[0])] = (float(p[0][1]), float(p[1][0]))
    transform = None
    if representation in ("kraus", "rm"):
        nm._custom_noise_passes = list(kraus._custom_noise_passes)     # RelaxationNoisePass on Delay
    elif representation == "pta":
        after = pta_delay_transform(t1s, t2s, dt)

        def transform(qc, after=after):
            return _insert_errors(qc, after=after)
    else:
        raise ValueError(representation)
    has_delay_noise = cell != "I-GATE"
    desc = {"id": cell, "class": "IBM Heron (ibm_kingston record)", "representation": representation,
            "t2_convention": "echo" if t2_convention == "echo" else f"star_{scale:.3f}",
            "t2_star_ratio": None if t2_convention == "echo" else scale,
            "t2_star_ratio_source": None if t2_convention == "echo" else T2_STAR_RATIO_SOURCE,
            "dt_s": dt, "record_fingerprint": record.get("fingerprint"), "record_stamp": record.get("stamp"),
            "channel_classes": ["depolarizing gate error (cz, sx, x)", "thermal relaxation T1/T2 on every gate for "
                                "its duration", "readout confusion per qubit"]
            + (["thermal relaxation on every explicit delay (idle-aware)"] if has_delay_noise else [])
            + (["coherent over-rotation Rx(eps_q) after every x"] if coherent_eps else []),
            "coherent_eps_rad": ({str(k): v for k, v in sorted(coherent_eps.items())} if coherent_eps else None),
            "coherent_eps_source": COH_SOURCE if coherent_eps else None,
            "not_modelled": ["ZZ crosstalk", "measurement crosstalk", "leakage", "non-Markovian dephasing"]
            + (["a dynamical-decoupling gain: Aer's relaxation on a delay is Markovian (information cell)"]
               if cell == "I-XY4" else []),
            "source": SOURCES["I"],
            "pta_rule": ("p_X = p_Y = (1 - e^{-t/T1})/4, p_Z = (1 - e^{-t/T2})/2 - (1 - e^{-t/T1})/4 on delays; "
                         "every gate error twirled numerically (sum_k |Tr P K_k|^2 / d^2)") if representation == "pta" else None,
            "rm_rule": ("T2 := min(T2, T1) per qubit on the target and on the delays (after the T2 convention and Aer's "
                        "2 T1 clip), so thermal_relaxation_error is Aer's reset mixture {I, Z, reset0, reset1} "
                        "everywhere (no Kraus); non-unital like Kraus; overstates dephasing where T2 > T1 "
                        "(prompts/33a R2)") if representation == "rm" else None}
    spec = NoiseSpec(cell, nm, transform, desc, readout=None, readout_per_qubit=ro)
    spec.t1s, spec.t2s, spec.dt = t1s, t2s, dt
    spec.local_errors = {k: v for k, v in _local_errors(nm).items()}
    return spec


def f0_ibm(qc, spec: NoiseSpec, final_layout, ref_bits=None) -> dict:
    """Twirled fault-free fraction of a physical circuit: product of the identity weights of every gate
    error and every delay window (closed form), times the readout survival of `ref_bits` on the
    measured physical qubits (`final_layout[i]` carries logical/clbit i)."""
    cache = {}
    logg = 0.0
    n_sites = 0
    for inst in qc.data:
        name = inst.operation.name
        qs = tuple(qc.find_bit(q).index for q in inst.qubits)
        if name == "delay" and spec.description["id"] != "I-GATE":
            t = delay_seconds(inst, spec.dt)
            q = qs[0]
            p = pta_relaxation_probs(t, spec.t1s[q], spec.t2s[q])
            logg += math.log(max(p["I"], 1e-300))
            n_sites += 1
            continue
        err = spec.local_errors.get((name, qs))
        if err is None:
            continue
        if (name, qs) not in cache:
            cache[(name, qs)] = identity_probability(err)
        logg += math.log(cache[(name, qs)])
        n_sites += 1
    g0 = math.exp(logg)
    rs = 1.0
    if ref_bits is not None:
        for i, b in enumerate(ref_bits):
            p10, p01 = spec.readout_per_qubit.get(int(final_layout[i]), (0.0, 0.0))
            rs *= (1.0 - p01) if int(b) else (1.0 - p10)
    return {"g0": g0, "f0": g0 * rs, "readout_survival": rs, "noisy_sites": n_sites,
            "rule": "identity weight of the Pauli twirl of every gate error and delay window, x readout survival"}


def coherent_eps_for(qubits, ddrep_path=None) -> dict:
    """{physical qubit: eps} for I-COH: the H0_ddrep per-qubit value where measured, else the median."""
    ddrep_path = ddrep_path or os.path.join(ROOT, "validation", "H0_ddrep.json")
    with open(ddrep_path) as fh:
        per = json.load(fh)["data"]["trains"]["per_qubit"]
    meas = {int(q): float(v["epsilon"]) for q, v in per.items() if v.get("epsilon") is not None}
    med = float(np.median(list(meas.values())))
    return {int(q): meas.get(int(q), med) for q in qubits}, {"median_rad": med, "measured_qubits": sorted(meas),
                                                              "source": COH_SOURCE}


def t2_star_ratio(path=None) -> float:
    path = path or os.path.join(ROOT, "validation", "S2D_idle.json")
    with open(path) as fh:
        return float(json.load(fh)["data"]["t2_bracket"]["fallback_ratio"])


def describe(spec: NoiseSpec) -> dict:
    return copy.deepcopy(spec.description)
