"""
Backend-independent circuit description ("IR") of the support-generating
circuits, built from exact local block unitaries of the Hamiltonian terms.
The IR is a list of gates (name, qubits, params):

    ('x',  [q], None)                     Pauli X (state preparation)
    ('h',  [q], None)
    ('rz', [q], angle)                    Rz(angle) = exp(-i angle Z / 2)
    ('p',  [q], angle)                    phase gate diag(1, e^{i angle})
    ('cp', [c, t], angle)                 controlled phase diag(1,1,1,e^{i angle})
    ('cx', [c, t], None)
    ('unitary', qubits, U)                dense 2^k x 2^k unitary, qubits[0] = least significant bit

Everything in this file is executed and verified in numpy (reference_sim.py);
the Qiskit and CUDA-Q modules only translate the IR.

Term gates for exp(-i theta H_gamma), gamma in {diag, hop_l, plaq_P}:
  * diag: exact phases from n_x and j_l read from the codeword bits
      corner:   n = (q1 xor q2) + 2 q3            (valid codewords)
      interior: n = f + 2 q4 (1 - f), f = q1 xor q2 xor q3 (parity of the flux ends)
      electric: (g^2/2) * 3/4 per flux link, applied once, on the 'out' end's flux qubit
  * hop_l: dense local unitary on the support of reference_sim.term_support
  * plaq_P: structured gate at 2x2 (corner-only plaquettes) with a Gray-code
    uniformly controlled Rz; dense local unitary otherwise (only usable for
    statevector simulation when the support has <= 12 qubits; larger supports
    raise NotImplementedError until the S2-b decomposition exists).
    Note: the structured gate equals the dense block unitary on the codeword
    subspace but is NOT the identity on leaked (non-codeword) strings, whereas
    the dense local unitary is; with noise the two differ on leaked states.

Coarse single-step circuit (manual Step 4.3 b): X gates preparing the reference
codeword, then the term gates with theta = k dt in the order diag, hop_0, hop_1,
..., plaq_0, ...  (same order as krylov.term_groups).  First-order Trotter: the
same block repeated k times with theta = dt.

Symbols: theta = angle, dt = Krylov step, k = coarse-step multiplier.
"""
from __future__ import annotations

import numpy as np

from .codec import Codec
from .exact import Model, mass_default
from .krylov import references
from .reference_sim import (apply_local, bits_to_int, local_unitary, plaquette_pair_amplitudes,
                            term_support)


# ------------------------------------------------------------ uniformly controlled Rz
def gray(j: int) -> int:
    return j ^ (j >> 1)


def ucrz_gray(theta_list: list, controls: list, target: int) -> list:
    """Gray-code decomposition of  sum_c |c><c| (x) Rz(theta_c)  (c = sum_j c_j 2^j over
    `controls` in order) into 2^k Rz on the target and 2^k CNOTs (controls -> target)."""
    k = len(controls)
    N = 2 ** k
    theta = np.asarray(theta_list, dtype=float)
    assert len(theta) == N
    M = np.array([[(-1) ** bin(c & gray(j)).count("1") for j in range(N)] for c in range(N)], dtype=float)
    alpha = M.T @ theta / N
    gates = []
    for j in range(N):
        gates.append(("rz", [target], float(alpha[j])))
        nxt = j + 1
        if nxt == N:
            bit = k - 1
        else:
            bit = (nxt & -nxt).bit_length() - 1  # lowest set bit of j+1 = bit flipped from g_j to g_{j+1}
        gates.append(("cx", [controls[bit], target], None))
    return gates


# ---------------------------------------------------------------------- term gates
class CircuitFactory:
    def __init__(self, model: Model, g2: float, m: float | None = None):
        self.model = model
        self.g2 = g2
        self.m = mass_default(g2) if m is None else m
        self.codec = Codec(model.basis)
        self.n = self.codec.n_qubits
        self.lat = model.lat
        self.ends = self.lat.ends()
        self._hop_cache = {}

    # ----- state preparation
    def prepare(self, basis_index: int) -> list:
        bits = self.codec.encode(self.model.basis.labels[basis_index])
        return [("x", [q], None) for q, b in enumerate(bits) if b]

    # ----- diagonal term
    def diag_gates(self, theta: float) -> list:
        gates = []
        lat, codec = self.lat, self.codec
        for s in range(lat.n_sites):
            o = codec.offsets[s]
            sgn = 1.0 if lat.parity(s) == 0 else -1.0
            phi = theta * self.m * sgn                     # exp(-i phi n_x)
            k = len(self.ends[s])
            if k == 2 and not lat.is_static(s):
                q1, q2, q3 = o, o + 1, o + 2
                gates += [("cx", [q1, q2], None), ("p", [q2], -phi), ("cx", [q1, q2], None), ("p", [q3], -2 * phi)]
            elif k == 3 and not lat.is_static(s):
                q1, q2, q3, q4 = o, o + 1, o + 2, o + 3
                # parity f into q3, then exp(-i phi f) exp(-2 i phi q4 (1-f))
                gates += [("cx", [q1, q3], None), ("cx", [q2, q3], None),
                          ("p", [q3], -phi), ("p", [q4], -2 * phi), ("cp", [q3, q4], 2 * phi),
                          ("cx", [q2, q3], None), ("cx", [q1, q3], None)]
            else:
                raise NotImplementedError("diagonal gates for charged vertices: use the dense diagonal unitary")
        # electric term on the 'out' end of each link
        for l, (x, y, _) in enumerate(lat.links):
            pos = [ll for ll, _ in self.ends[x]].index(l)
            q = codec.offsets[x] + pos
            gates.append(("p", [q], -theta * self.g2 * 0.375))
        return gates

    # ----- hopping terms
    def hop_gates(self, l: int, theta: float) -> list:
        sup = term_support(self.model, "hop", l)
        key = (l, round(theta, 12))
        if key not in self._hop_cache:
            self._hop_cache[key] = local_unitary(self.model, self.model.terms.hop[l], sup, theta)
        return [("unitary", sup, self._hop_cache[key])]

    # ----- plaquette terms
    def plaq_gates(self, P: int, theta: float, structured: bool = True) -> list:
        pl = self.lat.plaquettes[P]
        corners = [pl["c00"], pl["c10"], pl["c11"], pl["c01"]]
        if structured and all(self.codec.widths[s] == 3 for s in corners):
            table = plaquette_pair_amplitudes(self.model, P)
            q1 = [self.codec.offsets[s] for s in corners]
            q2 = [self.codec.offsets[s] + 1 for s in corners]
            gates = [("cx", [a, b], None) for a, b in zip(q1, q2)]
            gates += [("h", [a], None) for a in q1]
            gates += [("cx", [a, b], None) for a, b in zip(q1[:-1], q1[1:])]
            angles = []
            for c in range(16):
                p = tuple((c >> j) & 1 for j in range(4))
                angles.append(-theta * table.get(p, 0.0) / self.g2)
            gates += ucrz_gray(angles, q2, q1[-1])
            gates += [("cx", [a, b], None) for a, b in reversed(list(zip(q1[:-1], q1[1:])))]
            gates += [("h", [a], None) for a in q1]
            gates += [("cx", [a, b], None) for a, b in zip(q1, q2)]
            return gates
        sup = term_support(self.model, "plaq", P)
        if len(sup) > 12:
            raise NotImplementedError(
                f"plaquette {P} acts on {len(sup)} qubits (interior corners): the dense local unitary would need "
                f"{(2 ** len(sup)) ** 2 * 16 / 2 ** 30:.1f} GiB; the structured decomposition is the S2-b work item "
                "(prompts/06). The dressed-basis emulation (krylov.coarse_states) remains exact for this lattice.")
        U = local_unitary(self.model, -self.model.terms.plaq[P] / (2 * self.g2), sup, theta)
        return [("unitary", sup, U)]

    # ----- circuits
    def coarse_step(self, ref_index: int, k: int, dt: float, structured_plaquette=True) -> list:
        theta = k * dt
        gates = self.prepare(ref_index)
        if k == 0:
            return gates
        gates += self.diag_gates(theta)
        for l in range(self.lat.n_links):
            gates += self.hop_gates(l, theta)
        for P in range(len(self.lat.plaquettes)):
            gates += self.plaq_gates(P, theta, structured_plaquette)
        return gates

    def trotter(self, ref_index: int, steps: int, dt: float, structured_plaquette=True) -> list:
        gates = self.prepare(ref_index)
        for _ in range(steps):
            gates += self.diag_gates(dt)
            for l in range(self.lat.n_links):
                gates += self.hop_gates(l, dt)
            for P in range(len(self.lat.plaquettes)):
                gates += self.plaq_gates(P, dt, structured_plaquette)
        return gates

    def circuit_set(self, twoB: int, dt: float, kmax: int = 4) -> dict:
        """{(ref index, k): gate list} for all references of the sector and k = 1..kmax."""
        out = {}
        for r in references(self.model.basis, twoB):
            for k in range(1, kmax + 1):
                out[(r, k)] = self.coarse_step(r, k, dt)
        return out


# ------------------------------------------------------------------ numpy execution
def run_ir(gates: list, n: int, state: np.ndarray | None = None) -> np.ndarray:
    """Statevector simulation of an IR gate list (qubit 0 = least significant bit)."""
    if state is None:
        state = np.zeros(2 ** n, dtype=complex)
        state[0] = 1.0
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    CX = np.array([[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0]], dtype=complex)
    for name, qs, par in gates:
        if name == "x":
            state = apply_local(state, X, qs, n)
        elif name == "h":
            state = apply_local(state, H, qs, n)
        elif name == "rz":
            state = apply_local(state, np.diag([np.exp(-1j * par / 2), np.exp(1j * par / 2)]), qs, n)
        elif name == "p":
            state = apply_local(state, np.diag([1.0, np.exp(1j * par)]), qs, n)
        elif name == "cp":
            state = apply_local(state, np.diag([1.0, 1.0, 1.0, np.exp(1j * par)]), qs, n)
        elif name == "cx":
            state = apply_local(state, CX, qs, n)
        elif name == "unitary":
            state = apply_local(state, par, qs, n)
        else:
            raise ValueError(name)
    return state


def gate_counts(gates: list) -> dict:
    out = {}
    for name, qs, _ in gates:
        key = name if name != "unitary" else f"unitary{len(qs)}q"
        out[key] = out.get(key, 0) + 1
    return out
