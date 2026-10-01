"""Exact SPARSE statevector simulation of the IR circuits and of transpiled circuits.

Why.  At 2x4 the coarse-step circuit acts on 28 qubits, where a dense statevector is
4.3 GB and `run_ir` costs 0.7-3.8 s per gate on the laptop CPU (the planner's P4 in
`reports/S2_2x4_planner_analysis_20260930.md`): one circuit would be 10-20 hours.  The
circuits, however, are not dense at all.  A coarse step starts on ONE codeword and every
term gate maps codewords to codewords (`circuits_ir._multiplexed_two_level` forces the
identity on any pair of local strings that contains a codeword and carries no rotation), so
between multiplexed rotations the state lives on at most the 37165 codewords of the 2x4
basis; inside one multiplexed rotation the Gray-code chain acts on ONE target qubit t, so
the support only has to be closed under the flip of t -- at most twice as large.

So the whole coarse step can be carried in a sorted index array of order 10^4-10^5 entries.
This module does exactly that, with **no truncation whatsoever**: an entry is dropped only
when its amplitude is identically 0.0 (an entry that was created by closing the support
under a flip and never rotated), which changes nothing about the state.  There is no
magnitude threshold anywhere in this file.

Representation.  Two equivalent modes, switched on demand:

* SPARSE  -- `idx` (sorted unique int64 basis integers, qubit k = bit k) and `amp`.
  Permutations (`x`, `cx`) and diagonal gates (`rz`, `p`, `cp`, `cz`, `gphase`) act here.
* PAIRED on a qubit t -- `base` (sorted unique int64 with bit t cleared) and two amplitude
  columns `c0`, `c1` for bit t = 0 and 1.  Every two-level gate on t (`ry`, `rx`, `h`, `sx`,
  one-qubit `unitary`) is then a 2x2 mix of two contiguous arrays, and `cx(c -> t)` with
  c != t is a swap of the two columns on the rows where bit c of `base` is set.  A
  uniformly controlled rotation -- 2^c rotations and 2^c CNOTs, all on the same target --
  therefore runs entirely in this mode at O(support) per gate with no re-sorting at all,
  which is what makes the 132554-gate `plaq1` term affordable.

The cost of switching modes is one sort; the switch happens once per multiplexed rotation,
not once per gate.

The result is checked against `circuits_ir.run_ir` at 2x2 and 2x3 and against one dense
2^28 `run_ir` of the smallest 2x4 term (`tests/test_sparse_sim.py`, gate S2_2x4 criterion C4).
"""
from __future__ import annotations

import numpy as np

_SQ = 1.0 / np.sqrt(2.0)
_H2 = np.array([[_SQ, _SQ], [_SQ, -_SQ]], dtype=complex)
_SX2 = 0.5 * np.array([[1.0 + 1.0j, 1.0 - 1.0j], [1.0 - 1.0j, 1.0 + 1.0j]], dtype=complex)
_X2 = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)

# Gate names this module executes.  `barrier`, `measure`, `delay` and `id` are accepted and
# ignored (they do not change the statevector); anything else raises.
IGNORED = ("barrier", "measure", "delay", "id")


class SparseState:
    """Exact statevector on a sparse set of computational basis integers (qubit k = bit k)."""

    def __init__(self, n: int, idx=None, amp=None, init_int: int = 0):
        if int(n) > 62:
            raise ValueError(f"{n} qubits: the int64 basis index would overflow")
        self.n = int(n)
        if idx is None:
            idx = np.array([int(init_int)], dtype=np.int64)
            amp = np.array([1.0 + 0.0j], dtype=complex)
        self.idx = np.asarray(idx, dtype=np.int64)
        self.amp = np.asarray(amp, dtype=complex)
        self._t = None                  # the paired qubit, or None in sparse mode
        self._base = None
        self._c0 = None
        self._c1 = None
        self._masks = {}                # {control qubit: bool mask over base} while paired
        self.max_support = int(self.idx.size)
        self.n_pairings = 0
        self.n_sorts = 0

    # ---------------------------------------------------------------- modes
    @property
    def paired_on(self):
        return self._t

    def _track(self, m):
        if m > self.max_support:
            self.max_support = int(m)

    def to_sparse(self):
        """Collapse the paired mode back to (idx, amp), dropping exact zeros."""
        if self._t is None:
            return self
        t = self._t
        bit = np.int64(1) << np.int64(t)
        keep0 = self._c0 != 0.0
        keep1 = self._c1 != 0.0
        idx = np.concatenate([self._base[keep0], self._base[keep1] | bit])
        amp = np.concatenate([self._c0[keep0], self._c1[keep1]])
        o = np.argsort(idx, kind="stable")
        self.idx, self.amp = idx[o], amp[o]
        self.n_sorts += 1
        self._t = None
        self._base = self._c0 = self._c1 = None
        self._masks = {}
        self._track(self.idx.size)
        return self

    def to_paired(self, t: int):
        """Close the support under the flip of qubit t and split it into two columns."""
        t = int(t)
        if self._t == t:
            return self
        self.to_sparse()
        bit = np.int64(1) << np.int64(t)
        hi = ((self.idx >> np.int64(t)) & 1).astype(bool)
        lo_idx = self.idx[~hi]
        hi_idx = self.idx[hi] & ~bit          # both stay sorted: one bit is constant in each
        if lo_idx.size == hi_idx.size and np.array_equal(lo_idx, hi_idx):
            base = lo_idx
            c0 = self.amp[~hi].copy()
            c1 = self.amp[hi].copy()
        else:
            base = np.union1d(lo_idx, hi_idx)
            c0 = np.zeros(base.size, dtype=complex)
            c1 = np.zeros(base.size, dtype=complex)
            c0[np.searchsorted(base, lo_idx)] = self.amp[~hi]
            c1[np.searchsorted(base, hi_idx)] = self.amp[hi]
        self._t, self._base, self._c0, self._c1 = t, base, c0, c1
        self._masks = {}
        self.idx = self.amp = None
        self.n_pairings += 1
        self._track(2 * base.size)
        return self

    def _mask(self, c: int):
        """Bool mask over `base`: is bit c of the row set?  Cached for the current pairing."""
        c = int(c)
        m = self._masks.get(c)
        if m is None:
            m = ((self._base >> np.int64(c)) & 1).astype(bool)
            self._masks[c] = m
        return m

    # ---------------------------------------------------------------- views
    @property
    def support_size(self) -> int:
        return int(self.idx.size if self._t is None else 2 * self._base.size)

    def sorted_state(self):
        """(idx, amp) with exact zeros dropped and the indices sorted."""
        self.to_sparse()
        return self.idx, self.amp

    def dense_on(self, ints) -> np.ndarray:
        """The amplitudes on the given basis integers (in their order), zero where absent."""
        self.to_sparse()
        ints = np.asarray(ints, dtype=np.int64)
        out = np.zeros(ints.size, dtype=complex)
        pos = np.searchsorted(self.idx, ints)
        pos = np.clip(pos, 0, max(self.idx.size - 1, 0))
        if self.idx.size:
            found = self.idx[pos] == ints
            out[found] = self.amp[pos[found]]
        return out

    def dense(self) -> np.ndarray:
        """The full 2^n statevector (only for small n: the regressions against `run_ir`)."""
        self.to_sparse()
        out = np.zeros(2 ** self.n, dtype=complex)
        out[self.idx] = self.amp
        return out

    def norm(self) -> float:
        self.to_sparse()
        return float(np.sum(np.abs(self.amp) ** 2))

    def leakage(self, ints) -> float:
        """1 - the weight on the given basis integers (the codeword subspace)."""
        v = self.dense_on(ints)
        return float(1.0 - np.sum(np.abs(v) ** 2))

    # ---------------------------------------------------------------- gates
    def mix(self, t: int, U):
        """A 2x2 unitary on qubit t (`ry`, `rx`, `h`, `sx`, one-qubit `unitary`)."""
        U = np.asarray(U, dtype=complex)
        self.to_paired(t)
        a, b = self._c0, self._c1
        self._c0 = U[0, 0] * a + U[0, 1] * b
        self._c1 = U[1, 0] * a + U[1, 1] * b

    def mix_controlled(self, ctrls, cstate: int, t: int, U):
        """`mcu`: a 2x2 unitary on t, on the rows whose control bits match `cstate`."""
        U = np.asarray(U, dtype=complex)
        self.to_paired(t)
        sel = np.ones(self._base.size, dtype=bool)
        for j, c in enumerate(ctrls):
            m = self._mask(c)
            sel &= m if ((int(cstate) >> j) & 1) else ~m
        a, b = self._c0[sel], self._c1[sel]
        self._c0[sel] = U[0, 0] * a + U[0, 1] * b
        self._c1[sel] = U[1, 0] * a + U[1, 1] * b

    def x(self, t: int):
        t = int(t)
        if self._t == t:
            self._c0, self._c1 = self._c1, self._c0
            return
        self.to_sparse()
        self.idx = self.idx ^ (np.int64(1) << np.int64(t))
        o = np.argsort(self.idx, kind="stable")
        self.idx, self.amp = self.idx[o], self.amp[o]
        self.n_sorts += 1

    def cx(self, c: int, t: int):
        c, t = int(c), int(t)
        assert c != t, "cx needs two distinct qubits"
        if self._t == t:                       # the chain's case: a column swap on some rows
            m = self._mask(c)
            c0, c1 = self._c0, self._c1
            self._c0 = np.where(m, c1, c0)
            self._c1 = np.where(m, c0, c1)
            return
        self.to_sparse()
        sel = ((self.idx >> np.int64(c)) & 1).astype(bool)
        self.idx = np.where(sel, self.idx ^ (np.int64(1) << np.int64(t)), self.idx)
        o = np.argsort(self.idx, kind="stable")
        self.idx, self.amp = self.idx[o], self.amp[o]
        self.n_sorts += 1

    def phase(self, q: int, ang: float):
        """`p`: multiply by e^{i ang} where bit q is set."""
        f = np.exp(1j * float(ang))
        q = int(q)
        if self._t == q:                       # the paired qubit: a whole column
            self._c1 = self._c1 * f
            return
        if self._t is not None:
            m = self._mask(q)
            g = np.where(m, f, 1.0 + 0.0j)
            self._c0 = self._c0 * g
            self._c1 = self._c1 * g
            return
        sel = ((self.idx >> np.int64(q)) & 1).astype(bool)
        self.amp = self.amp * np.where(sel, f, 1.0 + 0.0j)

    def rz(self, q: int, ang: float):
        lo, hi = np.exp(-0.5j * float(ang)), np.exp(0.5j * float(ang))
        q = int(q)
        if self._t == q:
            self._c0 = self._c0 * lo
            self._c1 = self._c1 * hi
            return
        if self._t is not None:
            g = np.where(self._mask(q), hi, lo)
            self._c0 = self._c0 * g
            self._c1 = self._c1 * g
            return
        sel = ((self.idx >> np.int64(q)) & 1).astype(bool)
        self.amp = self.amp * np.where(sel, hi, lo)

    def cphase(self, a: int, b: int, ang: float):
        f = np.exp(1j * float(ang))
        a, b = int(a), int(b)
        if self._t is not None:
            if self._t == a or self._t == b:
                other = b if self._t == a else a
                self._c1 = self._c1 * np.where(self._mask(other), f, 1.0 + 0.0j)
                return
            g = np.where(self._mask(a) & self._mask(b), f, 1.0 + 0.0j)
            self._c0 = self._c0 * g
            self._c1 = self._c1 * g
            return
        sel = (((self.idx >> np.int64(a)) & 1) & ((self.idx >> np.int64(b)) & 1)).astype(bool)
        self.amp = self.amp * np.where(sel, f, 1.0 + 0.0j)

    def cz(self, a: int, b: int):
        self.cphase(a, b, np.pi)

    def gphase(self, ang: float):
        f = np.exp(1j * float(ang))
        if self._t is None:
            self.amp = self.amp * f
        else:
            self._c0 = self._c0 * f
            self._c1 = self._c1 * f


# ------------------------------------------------------------------ IR execution
def apply_ir(state: SparseState, gates: list) -> SparseState:
    """Apply an IR gate list (`circuits_ir`) to a sparse state, in order."""
    for name, qs, par in gates:
        if name == "x":
            state.x(qs[0])
        elif name == "cx":
            state.cx(qs[0], qs[1])
        elif name == "p":
            state.phase(qs[0], par)
        elif name == "rz":
            state.rz(qs[0], par)
        elif name == "cp":
            state.cphase(qs[0], qs[1], par)
        elif name == "cz":
            state.cz(qs[0], qs[1])
        elif name == "gphase":
            state.gphase(par)
        elif name == "h":
            state.mix(qs[0], _H2)
        elif name == "sx":
            state.mix(qs[0], _SX2)
        elif name == "ry":
            c, s = np.cos(par / 2), np.sin(par / 2)
            state.mix(qs[0], np.array([[c, -s], [s, c]], dtype=complex))
        elif name == "rx":
            c, s = np.cos(par / 2), np.sin(par / 2)
            state.mix(qs[0], np.array([[c, -1j * s], [-1j * s, c]], dtype=complex))
        elif name == "unitary":
            if len(qs) != 1:
                raise NotImplementedError(f"sparse_sim: 'unitary' on {len(qs)} qubits")
            state.mix(qs[0], par)
        elif name == "mcu":
            U2, cstate = par
            state.mix_controlled(list(qs[:-1]), int(cstate), qs[-1], U2)
        elif name in IGNORED:
            continue
        else:
            raise ValueError(f"sparse_sim: unknown IR gate '{name}'")
    return state


def run_sparse(gates: list, n: int, init_int: int = 0) -> SparseState:
    """Exact sparse statevector of an IR gate list, starting from |init_int>."""
    st = SparseState(n, init_int=int(init_int))
    apply_ir(st, gates)
    st.to_sparse()
    return st


# ------------------------------------------------------------------ transpiled circuits
def qiskit_to_ir(tq) -> list:
    """A transpiled QuantumCircuit ({rz, sx, x, cz} + barrier/measure) as an IR gate list.

    Only the names this module executes are accepted; `barrier`, `measure`, `delay` and `id`
    are kept in the list and ignored by `apply_ir`, so the instruction order is visible.  The
    circuit's global phase is appended as a `gphase`.
    """
    out = []
    for inst in tq.data:
        name = inst.operation.name
        qs = [tq.find_bit(q).index for q in inst.qubits]
        if name in IGNORED:
            out.append((name, qs, None))
            continue
        if name in ("rz", "p"):
            out.append((name, qs, float(inst.operation.params[0])))
        elif name in ("ry", "rx"):
            out.append((name, qs, float(inst.operation.params[0])))
        elif name in ("x", "sx", "h"):
            out.append((name, qs, None))
        elif name == "cz":
            out.append(("cz", qs, None))
        elif name == "cx":
            out.append(("cx", qs, None))
        elif name == "cp":
            out.append(("cp", qs, float(inst.operation.params[0])))
        else:
            raise ValueError(f"sparse_sim: transpiled circuit contains '{name}'")
    gp = float(tq.global_phase)
    if gp:
        out.append(("gphase", [], gp))
    return out


def run_sparse_qiskit(tq, init_int: int = 0) -> SparseState:
    """Exact sparse statevector of a transpiled circuit (qubit k = Qiskit qubit k)."""
    st = SparseState(tq.num_qubits, init_int=int(init_int))
    apply_ir(st, qiskit_to_ir(tq))
    st.to_sparse()
    return st


def project(state: SparseState, ints):
    """(amplitudes on `ints`, leakage outside them)."""
    v = state.dense_on(ints)
    return v, float(1.0 - np.sum(np.abs(v) ** 2))
