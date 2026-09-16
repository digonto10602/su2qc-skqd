"""
Hardware-session helpers (manual Step 9.1, prompts/07 and prompts/13).

Two independent jobs:

1. **Readout calibration.**  `confusion_matrix` turns the counts of the
   preparation circuits (all-0, all-1 and the single-qubit flips) into a
   *tensored* (independent-qubit) readout model C with
   ``C[q, m, p] = P(measure m on qubit q | prepared p)``, and `apply_inverse`
   unfolds a counts dictionary with the exact tensor inverse
   ``(C_0^{-1} x ... x C_{n-1}^{-1})``.  The tensored model ignores measurement
   crosstalk between qubits; it is the model the SKQD manual's Step 9.1 asks for
   ("per-qubit readout confusion") and it is the only one that can be calibrated
   with O(n) circuits.  Unfolded counts are quasi-counts: they may be negative.

2. **Layout bookkeeping of a transpiled circuit.**  A transpiled circuit lives on
   physical qubits and its routing permutes them, so its statevector is *not* in
   this package's logical bit order.  `transpiled_layout` reads the final layout
   and the measurement map off the circuit, and `logical_statevector` returns the
   noiseless statevector of the transpiled circuit permuted back to logical order
   (qubit k = bit k, `reference_sim`), which is what `CodewordEmbedding.leakage`
   expects.  A wrong layout permutation is exactly the mistake that makes a real
   hardware run decode to garbage, so it is checked before anything is submitted.

`codeword_bit_order` and `link_consistency_checks` export the decoder's own
bookkeeping (which qubit carries which vertex/link datum, and which qubit pairs
must agree) into the per-circuit manifests that travel with the job.

Nothing here changes a convention; `codec.py` and `reference_sim.py` are read only.
"""
from __future__ import annotations

import numpy as np

from .codec import Codec


# --------------------------------------------------------------- readout model
def _as_bits(key) -> tuple:
    """Accept a bit tuple/list or a '0101' string in this package's order (index k = qubit k)."""
    if isinstance(key, str):
        return tuple(int(ch) for ch in key.replace(" ", ""))
    return tuple(int(b) for b in key)


def confusion_matrix(counts_by_prep: dict, n_qubits: int | None = None) -> np.ndarray:
    """Per-qubit readout confusion matrices from calibration counts.

    counts_by_prep: {prepared bit tuple: {measured bit tuple or string: count}}.
    Returns C of shape (n, 2, 2) with C[q, m, p] = P(measure m | prepared p) on
    qubit q; every column sums to 1.  Every qubit must be prepared in both 0 and
    1 by at least one circuit (all-0 + all-1, or all-0 + the single-qubit flips).
    """
    preps = {_as_bits(k): v for k, v in counts_by_prep.items()}
    if not preps:
        raise ValueError("no calibration counts")
    n = n_qubits if n_qubits is not None else len(next(iter(preps)))
    tally = np.zeros((n, 2, 2), dtype=float)          # [q, measured, prepared]
    for prep, counts in preps.items():
        if len(prep) != n:
            raise ValueError(f"preparation {prep} does not have {n} qubits")
        for key, c in counts.items():
            bits = _as_bits(key)
            if len(bits) != n:
                raise ValueError(f"measured string {key} does not have {n} qubits")
            for q in range(n):
                tally[q, bits[q], prep[q]] += c
    col = tally.sum(axis=1)                            # [q, prepared]
    if np.any(col <= 0):
        bad = [(int(q), int(p)) for q in range(n) for p in (0, 1) if col[q, p] <= 0]
        raise ValueError(f"no calibration data for (qubit, prepared value) {bad}")
    return tally / col[:, None, :]


def apply_inverse(counts: dict, C: np.ndarray, tol: float = 1e-12) -> dict:
    """Unfold a counts dictionary with the tensored readout model C.

    counts: {bit tuple or string: count} in this package's order.  Returns
    {bit tuple: quasi-count} = (x_q C[q]^{-1}) applied to the counts vector;
    entries below `tol` in absolute value are dropped.  The total is preserved
    (each C[q] has unit column sums, so each inverse has unit column sums too).
    """
    C = np.asarray(C, dtype=float)
    if C.ndim != 3 or C.shape[1:] != (2, 2):
        raise ValueError("C must have shape (n, 2, 2)")
    n = C.shape[0]
    inv = np.stack([np.linalg.inv(C[q]) for q in range(n)])
    v = np.zeros(2 ** n, dtype=float)
    for key, c in counts.items():
        bits = _as_bits(key)
        if len(bits) != n:
            raise ValueError(f"string {key} does not have {n} qubits")
        v[sum(int(b) << q for q, b in enumerate(bits))] += c
    for q in range(n):
        v = np.einsum("ij,ajb->aib", inv[q], v.reshape(-1, 2, 2 ** q)).reshape(-1)
    out = {}
    for i in np.nonzero(np.abs(v) > tol)[0]:
        out[tuple((int(i) >> q) & 1 for q in range(n))] = float(v[i])
    return out


# ------------------------------------------------------- transpiled-circuit layout
def transpiled_layout(tq, n_logical: int | None = None) -> dict:
    """Layout bookkeeping of a transpiled circuit.

    Returns {'logical_to_physical': list (index = logical qubit, value = the physical
    qubit that carries it at the END of the circuit), 'active_physical': sorted list
    of the physical qubits any instruction touches, 'measurement_map': {clbit:
    physical qubit}, 'measurement_consistent': bool}.  `measurement_consistent` is
    True when clbit i measures the physical qubit that carries logical qubit i, i.e.
    when classical bit i of the counts key is logical qubit i (the assumption of
    `reference_sim.qiskit_key_to_bits` and of `codec.decode_counts`).
    """
    n = n_logical if n_logical is not None else (tq.num_clbits or tq.num_qubits)
    if tq.layout is None:
        final = list(range(n))
    else:
        final = [int(q) for q in tq.layout.final_index_layout()]
    active, meas = set(), {}
    for inst in tq.data:
        name = inst.operation.name
        if name == "barrier":
            continue
        for q in inst.qubits:
            active.add(int(tq.find_bit(q).index))
        if name == "measure":
            meas[int(tq.find_bit(inst.clbits[0]).index)] = int(tq.find_bit(inst.qubits[0]).index)
    ok = len(meas) == n and all(meas.get(i) == final[i] for i in range(n))
    return {"logical_to_physical": final, "active_physical": sorted(active),
            "measurement_map": {str(k): v for k, v in sorted(meas.items())},
            "measurement_consistent": bool(ok)}


def logical_statevector(tq, n_logical: int | None = None) -> np.ndarray:
    """Noiseless statevector of a TRANSPILED circuit, permuted back to logical order.

    Measurements and barriers are dropped, the circuit is compacted onto the physical
    qubits it actually uses (a transpiled circuit carries the whole device register,
    which cannot be simulated), and the amplitudes are permuted with the circuit's own
    final layout so that bit k of the returned index is logical qubit k.

    Routing may have swapped logical qubits through ancillas; those qubits start in
    |0> and, if the routing is a genuine permutation, end in |0>.  The returned vector
    is the ancilla-all-zero slice, so it is normalised to 1 only if that is the case:
    any weight left on an ancilla (or any entanglement with one) shows up as missing
    norm and therefore as leakage in `CodewordEmbedding.leakage`, which is exactly how
    it should be treated before a hardware run.
    """
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    lay = transpiled_layout(tq, n_logical)
    final = lay["logical_to_physical"]
    n = len(final)
    phys = sorted(set(lay["active_physical"]) | set(final))
    pos = {p: i for i, p in enumerate(phys)}
    cc = QuantumCircuit(len(phys))
    cc.global_phase = tq.global_phase
    for inst in tq.data:
        if inst.operation.name in ("measure", "barrier"):
            continue
        cc.append(inst.operation, [pos[int(tq.find_bit(q).index)] for q in inst.qubits])
    psi = np.asarray(Statevector(cc).data)
    idx = np.arange(psi.size)
    keep = np.ones(psi.size, dtype=bool)
    for p in phys:                                  # ancillas must be back in |0>
        if p not in set(final):
            keep &= ((idx >> pos[p]) & 1) == 0
    logical_index = np.zeros(psi.size, dtype=np.int64)
    for i in range(n):
        logical_index |= ((idx >> pos[final[i]]) & 1) << i
    out = np.zeros(2 ** n, dtype=complex)
    out[logical_index[keep]] = psi[keep]
    return out


# ------------------------------------------------------------- decoder bookkeeping
def codeword_bit_order(codec: Codec) -> list:
    """[{qubit, site, role, link, end}] — which datum of the codeword each qubit carries.

    `role` is 'flux' for a link-end flux bit (with its link index and 'out'/'in' role),
    'n/iota' for the quark-occupation / intertwiner bit of the vertex and 'iota' for the
    second bit of a charged interior vertex; the meaning of the last bits depends on the
    flux pattern exactly as `Codec.decode_vertex` prescribes."""
    lat = codec.basis.lat
    ends = codec.ends
    out = []
    for s in range(lat.n_sites):
        o, w = int(codec.offsets[s]), int(codec.widths[s])
        k = len(ends[s])
        for i in range(k):
            link, end = ends[s][i]
            out.append({"qubit": o + i, "site": s, "role": "flux", "link": int(link), "end": str(end)})
        extra = ["n/iota", "iota"] if w - k == 2 else ["n/iota"]
        for j, role in enumerate(extra):
            out.append({"qubit": o + k + j, "site": s, "role": role, "link": None, "end": None,
                        "static": bool(lat.is_static(s)), "n_ends": k})
    return out


def link_consistency_checks(codec: Codec) -> list:
    """[{link, qubits: [a, b]}] — the flux-bit pairs `Codec.decode` requires to agree."""
    lat = codec.basis.lat
    ends = codec.ends
    where = {l: [] for l in range(lat.n_links)}
    for s in range(lat.n_sites):
        o = int(codec.offsets[s])
        for i, (link, _end) in enumerate(ends[s]):
            where[int(link)].append(o + i)
    return [{"link": l, "qubits": sorted(where[l])} for l in range(lat.n_links)]
