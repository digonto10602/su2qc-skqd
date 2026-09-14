"""
numpy reference for the circuit layer: codeword embedding of the gauge-invariant
basis into the 2^n computational space, exact local block unitaries of every
Hamiltonian term, and a plain statevector simulator that applies those local
gates.  Everything here runs without Qiskit or CUDA-Q and is what the laptop
gates compare the Qiskit / CUDA-Q circuits against.

Bit order.  Qubit k is bit k of the computational-basis integer
(index = sum_k q_k 2^k, little-endian), which is Qiskit's convention for
Statevector indices; a Qiskit counts key (a string with qubit 0 at the RIGHT
end) is converted to this package's bit tuple by reversing the string.

Local block unitaries.  For a term gamma with matrix O in the dressed-site basis
the local support is: the qubits of the touched vertices (x, y for a hopping
link; the four corners for a plaquette) plus, for a hopping term, the flux
qubits of the Jordan-Wigner sites strictly between x and y (whose parity
(-1)^{n_z} is the XOR of their flux bits).  O is local on that support (checked
by assertion: matrix elements agree for every extension of the local bits).
The gate is  U_loc = exp(-i theta O_loc) = 1 + V (exp(-i theta h) - 1) V^dag  with
V the isometry onto the valid local codewords (h = O restricted to them), so it
acts as the identity on flagged / link-inconsistent local strings and is exactly
gauge invariant on the physical subspace.

Plaquette at 2x2.  W + W^dag = D X^{(x)8}: every physical state is paired with
the state with all four link spins flipped (all eight flux bits), and the pair
amplitude w in {-2, +-1, 1/2} depends only on which corners carry one quark
(the four corner parities p_c = q1 XOR q2); plaquette_pair_amplitudes checks
this structure and returns the table.  The structured circuit that uses it
(CNOT(q1_c -> q2_c) per corner, H on the q1's, CNOT ladder, Gray-code
uniformly controlled Rz on the last q1 controlled by the parities, inverse)
lives in circuits_ir.CircuitFactory.plaq_gates and is verified against the
dense exponential by scripts/report_circuit_structure.py and tests/.

Symbols: theta = angle (k dt for a coarse step), O_loc = local term operator,
V = codeword isometry, w(p) = plaquette pair amplitude.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.linalg as sla

from .codec import Codec
from .exact import Model


def bits_to_int(bits) -> int:
    return int(sum(int(b) << k for k, b in enumerate(bits)))


def int_to_bits(x: int, n: int) -> tuple:
    return tuple((x >> k) & 1 for k in range(n))


def qiskit_key_to_bits(key: str) -> tuple:
    """Qiskit counts key (qubit 0 rightmost) -> bit tuple (index k = qubit k)."""
    key = key.replace(" ", "")
    return tuple(int(ch) for ch in key[::-1])


@dataclass
class CodewordEmbedding:
    model: Model

    def __post_init__(self):
        self.codec = Codec(self.model.basis)
        self.n = self.codec.n_qubits
        self.codewords = self.codec.all_codewords()
        self.ints = np.array([bits_to_int(row) for row in self.codewords], dtype=np.int64)

    def embed(self, psi_basis: np.ndarray) -> np.ndarray:
        full = np.zeros(2 ** self.n, dtype=complex)
        full[self.ints] = psi_basis
        return full

    def project(self, full: np.ndarray) -> np.ndarray:
        return full[self.ints]

    def leakage(self, full: np.ndarray) -> float:
        """Weight outside the codeword subspace."""
        return float(1.0 - np.sum(np.abs(full[self.ints]) ** 2))


# ------------------------------------------------------------------ local gates
def term_support(model: Model, kind: str, index: int) -> list:
    """Sorted list of qubits on which the term acts (touched vertices + JW flux bits)."""
    lat = model.lat
    codec = Codec(model.basis)
    ends = lat.ends()
    qubits = set()
    if kind == "hop":
        x, y, _ = lat.links[index]
        for s in (x, y):
            qubits.update(range(codec.offsets[s], codec.offsets[s] + codec.widths[s]))
        for z in range(x + 1, y):
            qubits.update(range(codec.offsets[z], codec.offsets[z] + len(ends[z])))  # flux bits only
    elif kind == "plaq":
        pl = lat.plaquettes[index]
        for s in (pl["c00"], pl["c10"], pl["c11"], pl["c01"]):
            qubits.update(range(codec.offsets[s], codec.offsets[s] + codec.widths[s]))
    elif kind == "diag":
        qubits.update(range(codec.n_qubits))
    return sorted(qubits)


def localize(model: Model, O, support: list):
    """Restrict a term matrix O (dressed basis) to its local support.  Returns
    (local_states as sorted int list, h as dense matrix over them, local index map).

    Locality is CHECKED, not assumed: the global states are grouped by their
    environment (the bits outside the support); O must connect only states of the
    same environment, and within every environment the block of O must equal h on
    the local states present (including the zeros).  Any violation raises."""
    codec = Codec(model.basis)
    cw = codec.all_codewords()
    env_qubits = [q for q in range(codec.n_qubits) if q not in set(support)]
    loc_int = np.array([bits_to_int(cw[k][support]) for k in range(model.basis.dim)])
    env_int = np.array([bits_to_int(cw[k][env_qubits]) for k in range(model.basis.dim)])
    states = sorted(set(loc_int.tolist()))
    pos = {s: i for i, s in enumerate(states)}
    h = np.zeros((len(states), len(states)), dtype=complex)
    Oc = O.tocoo()
    for r, c, v in zip(Oc.row, Oc.col, Oc.data):
        assert env_int[r] == env_int[c], "term connects states with different environments: not local on the support"
        key = (pos[loc_int[r]], pos[loc_int[c]])
        if h[key] != 0 and abs(h[key] - v) > 1e-10:
            raise AssertionError(f"term is not local on the chosen support: {key} {h[key]} {v}")
        h[key] = v
    # every environment block must reproduce h on its local states (zeros included)
    Od = O.tocsr()
    for e in np.unique(env_int):
        idx = np.where(env_int == e)[0]
        block = Od[idx][:, idx].toarray()
        li = np.array([pos[loc_int[k]] for k in idx])
        if np.abs(block - h[np.ix_(li, li)]).max() > 1e-10:
            raise AssertionError("term is not local on the chosen support (environment block mismatch)")
    return states, h, pos


def local_unitary(model: Model, O, support: list, theta: float) -> np.ndarray:
    """Dense 2^k x 2^k unitary exp(-i theta O_loc) on the support qubits (k = len(support))."""
    states, h, pos = localize(model, O, support)
    k = len(support)
    U = np.eye(2 ** k, dtype=complex)
    u = sla.expm(-1j * theta * h)
    idx = np.array(states)
    U[np.ix_(idx, idx)] += u - np.eye(len(states))
    return U


def apply_local(full: np.ndarray, U: np.ndarray, support: list, n: int) -> np.ndarray:
    """Apply a 2^k x 2^k unitary on qubits `support` to an n-qubit statevector."""
    k = len(support)
    psi = full.reshape([2] * n)  # axis j <-> qubit n-1-j ... use explicit axis mapping instead
    # axes: numpy reshape puts qubit 0 (least significant) on the LAST axis
    axes = [n - 1 - q for q in support]
    psi = np.moveaxis(psi, axes, list(range(k)))  # bring support qubits first (support[0] -> axis 0)
    shape = psi.shape
    psi = psi.reshape(2 ** k, -1)
    # local index of the support qubits: support[0] is the least significant bit of U's index
    # but axis 0 is the most significant of the reshaped block -> reorder U accordingly
    perm = np.array([sum(((s >> j) & 1) << (k - 1 - j) for j in range(k)) for s in range(2 ** k)])
    Uperm = U[np.ix_(perm, perm)]
    psi = Uperm @ psi
    psi = psi.reshape(shape)
    psi = np.moveaxis(psi, list(range(k)), axes)
    return psi.reshape(-1)


# -------------------------------------------------------- structured plaquette (2x2)
def plaquette_pair_amplitudes(model: Model, P: int) -> dict:
    """{corner parity tuple (p_c00, p_c10, p_c11, p_c01): w} for the 2x2 plaquette;
    asserts the pair structure (degree 1, real symmetric, w depends only on the parities)."""
    W = model.terms.plaq[P].tocoo()
    pl = model.lat.plaquettes[P]
    corners = [pl["c00"], pl["c10"], pl["c11"], pl["c01"]]
    table = {}
    deg = np.bincount(W.col, minlength=model.basis.dim)
    assert deg.max() == 1, "pair structure requires one partner per state (true at 2x2)"
    for r, c, v in zip(W.row, W.col, W.data):
        assert abs(v.imag) < 1e-12
        n = model.basis.labels[c][1]
        key = tuple(int(n[s] == 1) for s in corners)
        if key in table:
            assert abs(table[key] - v.real) < 1e-12, "w must depend on the corner parities only"
        table[key] = float(v.real)
    return table
