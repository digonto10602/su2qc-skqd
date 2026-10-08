"""
De-duplicated ("dedup", encoding E2 of reports/encodings_candidate_list_20261007.md) codewords
for uncharged vertices: one flux bit per LINK instead of one per link end, plus one bit per
vertex.  A CANDIDATE encoding measured by gate ENC_compare (prompts/34); the current codec
(`skqd.codec.Codec`) stays the default everywhere and every signed circuit uses it.  Circuits
built with this codec are UNSIGNED.

Qubit layout (qubit k = bit k, little-endian, as reference_sim):
    qubits 0 .. N_l - 1        : flux bit of link l (j_l = 1/2 <=> 1), stored ONCE
    qubit  N_l + s             : the vertex bit of site s
        corner (2 ends):   flux equal   -> bit = n/2
                           flux unequal -> n = 1, bit must be 0 (1 = flag)
        interior (3 ends): even flux parity -> bit = n/2
                           one flux end     -> n = 1, bit 0 (1 = flag)
                           three flux ends  -> n = 1, bit = iota

Decoder: (i) read the link register, (ii) read each vertex bit given its flux pattern,
rejecting a flagged vertex ("flag"), (iii) reject a wrong baryon number ("sector"),
(iv) look the label up in the basis index ("unknown").  There is no "link" check: the
duplicated link bit that carried it does not exist in this layout.

Charged (static-charge) vertices are out of scope here and raise NotImplementedError.

Symbols: n = quark occupation, iota = intertwiner label, j = link spin, f = flux parity.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .basis import Basis
from .codec import Reject

REASONS = ("flag", "sector", "unknown")


@dataclass
class DedupCodec:
    basis: Basis

    kind = "dedup"

    def __post_init__(self):
        lat = self.basis.lat
        self.ends = lat.ends()
        for s in range(lat.n_sites):
            if lat.is_static(s):
                raise NotImplementedError("DedupCodec: static-charge vertices are out of scope (prompts/34)")
            if len(self.ends[s]) not in (2, 3):
                raise ValueError("only corner (2 ends) and interior (3 ends) vertices are encoded")
        self.n_links = lat.n_links
        self.n_qubits = lat.n_links + lat.n_sites

    # ------------------------------------------------------------------ layout
    def vertex_qubit(self, s: int) -> int:
        return self.n_links + s

    def link_qubits(self, s: int) -> list:
        """The link-register qubits of the link ends of vertex s (canonical end order)."""
        return [l for l, _ in self.ends[s]]

    def layout(self) -> dict:
        lat = self.basis.lat
        return {
            "n_qubits": self.n_qubits,
            "links": {str(l): {"qubit": l, "x": int(x), "y": int(y), "dir": d}
                      for l, (x, y, d) in enumerate(lat.links)},
            "vertices": {str(s): {"qubit": self.vertex_qubit(s), "ends": len(self.ends[s]),
                                  "link_qubits": self.link_qubits(s)}
                         for s in range(lat.n_sites)},
        }

    # ------------------------------------------------------------------ encode
    def vertex_bit(self, s: int, flux: tuple, n: int, iota: int) -> int:
        k, f = len(flux), sum(flux)
        if k == 2:
            if flux[0] == flux[1]:
                assert n in (0, 2) and iota == 0
                return n // 2
            assert n == 1 and iota == 0
            return 0
        if f % 2 == 0:
            assert n in (0, 2) and iota == 0
            return n // 2
        if f == 1:
            assert n == 1 and iota == 0
            return 0
        assert n == 1
        return int(iota)

    def encode(self, label) -> tuple:
        j2, n, iota = label
        bits = [int(b) for b in j2]
        for s in range(self.basis.lat.n_sites):
            flux = tuple(j2[l] for l, _ in self.ends[s])
            bits.append(self.vertex_bit(s, flux, n[s], iota[s]))
        return tuple(bits)

    # ------------------------------------------------------------------ decode
    def decode(self, bits, target_twoB=None):
        """Decode one bit string.  Returns (index, label) or raises Reject with reason
        'flag', 'sector' or 'unknown'."""
        lat = self.basis.lat
        j2 = tuple(int(b) for b in bits[:self.n_links])
        n, iota = [], []
        for s in range(lat.n_sites):
            flux = tuple(j2[l] for l, _ in self.ends[s])
            b = int(bits[self.n_links + s])
            k, f = len(flux), sum(flux)
            if (k == 2 and flux[0] == flux[1]) or (k == 3 and f % 2 == 0):
                n.append(2 * b)
                iota.append(0)
            elif k == 2 or f == 1:
                if b:
                    raise Reject("flag")
                n.append(1)
                iota.append(0)
            else:
                n.append(1)
                iota.append(b)
        label = (j2, tuple(n), tuple(iota))
        if target_twoB is not None:
            twoB = sum(n[s] - lat.n_vac(s) for s in range(lat.n_sites))
            if twoB != target_twoB:
                raise Reject("sector")
        try:
            return self.basis.index[label], label
        except KeyError:
            raise Reject("unknown")

    def decode_counts(self, counts: dict, target_twoB=None):
        """counts: {bit tuple or 0/1 string: multiplicity}.  Returns (accepted {index: count},
        rejection reasons {reason: count}); the string convention is the one of Codec."""
        acc, rej = {}, {r: 0 for r in REASONS}
        for bits, c in counts.items():
            if isinstance(bits, str):
                bits = tuple(int(ch) for ch in bits)
            try:
                k, _ = self.decode(bits, target_twoB)
                acc[k] = acc.get(k, 0) + c
            except Reject as r:
                rej[str(r)] += c
        return acc, rej

    def all_codewords(self) -> np.ndarray:
        """(dim x n_qubits) array of the codewords of every basis state."""
        return np.array([self.encode(b) for b in self.basis.labels], dtype=np.int8)

    # ------------------------------------------------------------------ term supports
    def support(self, kind: str, index: int) -> list:
        """Qubits a term acts on.  hop: all link bits and the vertex bit of both end vertices plus
        the link bits of every site strictly between them (Jordan-Wigner parity); plaq: all link
        bits and vertex bits of the four corners; diag: all qubits."""
        lat = self.basis.lat
        q = set()
        if kind == "hop":
            x, y, _ = lat.links[index]
            for s in (x, y):
                q.update(self.link_qubits(s))
                q.add(self.vertex_qubit(s))
            for z in range(x + 1, y):
                q.update(self.link_qubits(z))
        elif kind == "plaq":
            pl = lat.plaquettes[index]
            for s in (pl["c00"], pl["c10"], pl["c11"], pl["c01"]):
                q.update(self.link_qubits(s))
                q.add(self.vertex_qubit(s))
        elif kind == "diag":
            q = set(range(self.n_qubits))
        else:
            raise ValueError(kind)
        return sorted(int(v) for v in q)
