"""Sparse Pauli-trajectory engine for the C5 noise study (IR level; the package's exact sparse simulator).

Why: a 28-qubit dense statevector costs 4-15 min per trajectory on this laptop, but the coarse-step circuits keep
their state on O(1e4-1e5) basis strings when they are run in the IR form (skqd.sparse_sim; genie's notes/006 found
the same).  A Pauli fault maps basis strings to basis strings one-to-one, so it does not enlarge the support by
itself.  Every trajectory is simulated with skqd.sparse_sim.apply_ir, amplitudes |a| < TAU are pruned every 32 gates
and the pruned norm is recorded per trajectory (the same certified pruning as genie's evaluate.verify_circuit_pruned).

The device model is the one of noise_models.py, mapped onto the IR gate list:
  * one native 2q gate per IR 2q gate (cx, cz -> RZZ(pi/2); cp(l) -> RZZ(l/2); rzz(t) -> RZZ(t)) and the uniform
    2q depolarizing channel right after it.  A uniform depolarizing channel commutes with every unitary on its
    qubits, so placing it after the IR gate instead of after the native RZZ (which differs by local 1q gates on
    the same two qubits) gives the same channel;
  * one native 1q gate (PhasedX) per maximal run of non-diagonal IR 1q gates of a qubit between its 2q gates, with
    the 1q depolarizing channel after the run (exact for the same reason); diagonal runs are virtual Rz (free);
    IonQ: a run whose merged rotation angle is pi or pi/2 is one pulse, otherwise two;
  * Quantinuum memory: Z with probability p_mem on every active qubit after every floor(n_active/2) 2q gates;
  * IonQ idle: serial schedule, Pauli-twirled thermal relaxation over each qubit's idle time, applied before its
    next gate (and before measurement);
  * readout: classical bit flips on the sampled string (done by the caller).
IBM models need SWAP routing and are not run in this engine (their native routed circuits are not sparse).
"""
from __future__ import annotations

import math

import numpy as np

import noise_models as nm

TWO_Q = {"cx", "cz", "cp", "rzz"}
DIAG_1Q = {"rz", "p", "gphase"}
TAU = 1e-12
_H = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
EVERY = 32
_PAULI_GATES = {"X": [("x", None)], "Z": [("p", math.pi)], "Y": [("x", None), ("p", math.pi)]}


def _u1(name, par):
    c, s = math.cos, math.sin
    if name == "x":
        return np.array([[0, 1], [1, 0]], dtype=complex)
    if name == "h":
        return np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
    if name == "sx":
        return 0.5 * np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=complex)
    if name == "ry":
        return np.array([[c(par / 2), -s(par / 2)], [s(par / 2), c(par / 2)]], dtype=complex)
    if name == "rx":
        return np.array([[c(par / 2), -1j * s(par / 2)], [-1j * s(par / 2), c(par / 2)]], dtype=complex)
    if name == "rz":
        return np.diag([np.exp(-0.5j * par), np.exp(0.5j * par)])
    if name == "p":
        return np.diag([1.0, np.exp(1j * par)])
    if name == "unitary":
        return np.asarray(par, dtype=complex)
    raise ValueError(name)


def _theta_of(U):
    """Rotation angle of the merged 1q unitary (the PhasedX angle of U = Rz . R(theta, phi))."""
    a = abs(U[0, 0])
    return 2 * math.acos(min(1.0, a)) if a < 1 else 0.0


def ir_events(gates: list, n: int, device: str):
    """Noise events attached to IR positions: list of (after_index, qubits, kind, [(pauli, p), ...]) and budget."""
    P = nm.params(device)
    kind = P["kind"]
    if kind == "ibm":
        raise ValueError("IBM models need routing; not run in the IR engine")
    ev = []
    bud = {"n_2q": 0, "n_1q_native": 0, "n_1q_pulses": 0,
           "log_clean": {"gate_1q": 0.0, "gate_2q": 0.0, "idle": 0.0, "memory": 0.0},
           "n_events": {"gate_1q": 0, "gate_2q": 0, "idle": 0, "memory": 0}}

    def add(pos, qs, k, plist):
        tot = sum(p for _, p in plist)
        if tot <= 0:
            return
        ev.append((pos, tuple(qs), k, plist))
        bud["log_clean"][k] += math.log1p(-tot)
        bud["n_events"][k] += 1

    active = sorted({q for _, qs, _ in gates for q in qs})
    half = max(1, len(active) // 2)
    run_U = {}            # qubit -> (merged unitary, last position, nondiag flag)
    free = {}             # IonQ serial: end time of last gate on q
    tnow = 0.0
    n2_since = 0

    def close_run(q):
        nonlocal tnow
        if q not in run_U:
            return
        U, pos, nondiag = run_U.pop(q)
        if not nondiag:
            return
        th = _theta_of(U)
        if th < 1e-12:
            return
        npulse = 1
        if kind == "ionq":
            npulse = 1 if (abs(th - math.pi) < 1e-9 or abs(th - math.pi / 2) < 1e-9) else 2
            dur = P["t1q"] * npulse
            if q in free and tnow - free[q] > 0 and not P.get("no_idle"):
                add(pos - 0.5, (q,), "idle", list(zip("XYZ", nm._pta(tnow - free[q], P["T1"], P["T2"]))))
            tnow += dur
            free[q] = tnow
        bud["n_1q_native"] += 1
        bud["n_1q_pulses"] += npulse
        r1 = 1.0 - (1.0 - P["p1"]) ** npulse
        add(pos, (q,), "gate_1q", nm._pauli_probs_depol(1.5 * r1, 1))

    for pos, (name, qs, par) in enumerate(gates):
        if name in ("gphase", "barrier"):
            continue
        if len(qs) == 1:
            q = qs[0]
            U = _u1(name, par)
            prev = run_U.get(q)
            nd = name not in DIAG_1Q
            if prev is None:
                run_U[q] = (U, pos, nd)
            else:
                run_U[q] = (U @ prev[0], pos, prev[2] or nd)
            continue
        if name not in TWO_Q:
            raise ValueError(f"IR gate {name} on {len(qs)} qubits")
        if name == "cx":
            # native form of cx(c, t): H(t) . RZZ(pi/2) . H(t) up to virtual Rz -> the target's 1q runs get an H
            # on each side (merged with the neighbouring IR 1q gates, as a compiler would)
            t_ = qs[1]
            prev = run_U.get(t_)
            run_U[t_] = (_H @ prev[0], prev[1], True) if prev is not None else (_H, pos - 0.5, True)
        for q in qs:
            close_run(q)
        if name == "cx":
            run_U[qs[1]] = (_H, pos, True)
        if name in ("cx", "cz"):
            th = math.pi / 2
        elif name == "cp":
            th = abs(float(par)) / 2
        else:
            th = float(par)
        if kind == "quantinuum":
            s = P["rzz_angle_scaling"]
            r2 = P["p2"] * (s["a"] * (nm.rzz_angle(th) / math.pi) ** s["power"] + s["b"])
        else:
            r2 = P["p2"]
            for q in qs:
                if q in free and tnow - free[q] > 0 and not P.get("no_idle"):
                    add(pos - 0.5, (q,), "idle", list(zip("XYZ", nm._pta(tnow - free[q], P["T1"], P["T2"]))))
            tnow += P["t2q"]
            for q in qs:
                free[q] = tnow
        bud["n_2q"] += 1
        add(pos, tuple(qs), "gate_2q", nm._pauli_probs_depol(1.25 * r2, 2))
        if kind == "quantinuum":
            n2_since += 1
            if n2_since == half:
                n2_since = 0
                for q in active:
                    add(pos + 0.25, (q,), "memory", [("Z", P["mem_depth1"])])
    for q in list(run_U):
        close_run(q)
    if kind == "ionq":
        for q in active:
            if q in free and tnow - free[q] > 0 and not P.get("no_idle"):
                add(len(gates) + 0.5, (q,), "idle", list(zip("XYZ", nm._pta(tnow - free[q], P["T1"], P["T2"]))))
        bud["duration_s"] = tnow
    else:
        bud["depth1_equivalent_layers"] = bud["n_2q"] / half
    ev.sort(key=lambda e: e[0])
    bud["n_active_qubits"] = len(active)
    bud["f_gate"] = math.exp(sum(bud["log_clean"].values()))
    bud["f_parts"] = {k: math.exp(v) for k, v in bud["log_clean"].items()}
    return ev, bud


def _pauli_ir(label: str, qs) -> list:
    """IR gates for a Pauli string (qiskit label order: rightmost character acts on qs[0])."""
    out = []
    for i, q in enumerate(qs):
        ch = label[len(qs) - 1 - i]
        for g, par in _PAULI_GATES.get(ch, []):
            out.append((g, [q], par))
    return out


class Engine:
    """Trajectories of one IR circuit under one device model."""

    def __init__(self, gates: list, n: int, device: str, checkpoint_every: int = 400):
        from skqd.sparse_sim import SparseState, apply_ir
        self.SparseState, self.apply_ir = SparseState, apply_ir
        self.gates, self.n, self.device = gates, n, device
        self.events, self.budget = ir_events(gates, n, device)
        self.ev_pos = np.array([e[0] for e in self.events])
        self.ev_p = np.array([sum(p for _, p in e[3]) for e in self.events])
        # noiseless run with checkpoints (state BEFORE gate index c, for c in checkpoints)
        st, self.clean_prune, self.ck = self._run(SparseState(n), 0, len(gates), [], record_every=checkpoint_every)
        self.clean = st

    def _copy(self, st):
        st.to_sparse()
        c = self.SparseState(self.n, idx=st.idx.copy(), amp=st.amp.copy())
        return c

    def _run(self, st, start, stop, inserts, record_every=None):
        """Apply gates[start:stop] with Pauli insertions [(after_pos, ir_gates)], pruning every EVERY gates."""
        ck = {}
        bound = 0.0
        ins = sorted(inserts, key=lambda x: x[0])
        j = 0
        i = start
        count = 0
        while i < stop:
            if record_every and (i - start) % record_every == 0:
                ck[i] = self._copy(st)
            # insertions positioned before gate i (pos = i - 0.5)
            while j < len(ins) and ins[j][0] < i:
                self.apply_ir(st, ins[j][1])
                j += 1
            self.apply_ir(st, [self.gates[i]])
            while j < len(ins) and ins[j][0] <= i + 0.25 + 1e-9 and ins[j][0] >= i:
                self.apply_ir(st, ins[j][1])
                j += 1
            i += 1
            count += 1
            if count % EVERY == 0:
                st.to_sparse()
                small = np.abs(st.amp) < TAU
                if small.any():
                    bound += float(np.sqrt(np.sum(np.abs(st.amp[small]) ** 2)))
                    st.idx, st.amp = st.idx[~small], st.amp[~small]
        while j < len(ins):
            self.apply_ir(st, ins[j][1])
            j += 1
        st.to_sparse()
        return st, bound, ck

    def sample_faults(self, rng):
        hit = rng.random(len(self.events)) < self.ev_p
        out = []
        for e_i in np.nonzero(hit)[0]:
            pos, qs, kind, plist = self.events[e_i]
            labs = [lab for lab, _ in plist]
            pr = np.array([p for _, p in plist])
            lab = labs[rng.choice(len(labs), p=pr / pr.sum())]
            out.append((pos, qs, kind, lab))
        return out

    def trajectory(self, faults):
        """Final sparse state (idx, amp) and the pruned norm for a given fault list."""
        if not faults:
            return self.clean.idx, self.clean.amp, self.clean_prune, 0
        first = min(f[0] for f in faults)
        starts = [c for c in self.ck if c <= first]
        c0 = max(starts) if starts else 0
        st = self._copy(self.ck[c0]) if c0 in self.ck else self.SparseState(self.n)
        inserts = [(pos, _pauli_ir(lab, qs)) for pos, qs, _, lab in faults]
        st, bound, _ = self._run(st, c0, len(self.gates), inserts)
        return st.idx, st.amp, bound + self.clean_prune, len(faults)   # clean_prune: conservative bound for the prefix
