"""
Hardware codewords and the per-shot decoder (Steps 2.4 and 2.5 of the SKQD manual).

Qubit layout: vertices own contiguous blocks of qubits in site order; a bit
string is a tuple of ints q_0 ... q_{N-1} (q_k = value of qubit k).  Within a
vertex the first bits are the flux bits of its link ends in canonical (link
index) order, j = 1/2 <=> 1.

Corner (2 ends), 3 qubits (q1,q2,q3):
    q1 = q2 -> n in {0,2}, q3 = n/2;    q1 != q2 -> n = 1, q3 = 0 (q3 = 1 is a leakage flag)
Interior (3 ends), 4 qubits:
    #flux ends even -> q4 = n/2;  one -> n = 1, q4 = 0 (q4 = 1 flag);  three -> n = 1, q4 = iota
Charged corner (static spin-1/2), 3 qubits:
    (0,0) -> n = 1, q3 = 0 (1 flag);  (1,1) -> n = 1, q3 = iota;  unequal -> n in {0,2}, q3 = n/2
Charged interior, 5 qubits (17 states; the manual fixes the count, the bit
assignment below is this package's choice):
    #flux 0 -> n = 1, (q4,q5) = (0,0);   #flux 1 -> n in {0,2}, (q4,q5) = (n/2, 0);
    #flux 2 -> n = 1, (q4,q5) = (iota, 0);  #flux 3 -> n in {0,2}, (q4,q5) = (n/2, iota);
    every other (q4,q5) is a flag.

Decoder: (i) split into vertex codewords, (ii) reject any flagged vertex,
(iii) reject any link whose flux bit differs between its two end vertices,
(iv) read ({j_l},{n_x},{iota_x}), (v) reject if sum_x n_x is not the target
sector, (vi) look the label up in the basis index.

Symbols: n = quark occupation, iota = intertwiner label, j = link spin.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .basis import Basis


class Reject(Exception):
    pass


@dataclass
class Codec:
    basis: Basis

    def __post_init__(self):
        lat = self.basis.lat
        self.ends = lat.ends()
        self.widths = []
        for s in range(lat.n_sites):
            k = len(self.ends[s])
            static = lat.is_static(s)
            if k == 2:
                self.widths.append(3)
            elif k == 3:
                self.widths.append(5 if static else 4)
            else:
                raise ValueError("only corner (2 ends) and interior (3 ends) vertices are encoded")
        self.offsets = np.concatenate([[0], np.cumsum(self.widths)[:-1]]).astype(int)
        self.n_qubits = int(sum(self.widths))

    # ------------------------------------------------------------------ encode
    def encode_vertex(self, s, flux: tuple, n: int, iota: int) -> tuple:
        static = self.basis.lat.is_static(s)
        k = len(flux)
        f = sum(flux)
        if k == 2 and not static:
            if flux[0] == flux[1]:
                assert n in (0, 2)
                return (*flux, n // 2)
            assert n == 1 and iota == 0
            return (*flux, 0)
        if k == 2 and static:
            if flux == (0, 0):
                assert n == 1 and iota == 0
                return (0, 0, 0)
            if flux == (1, 1):
                assert n == 1
                return (1, 1, iota)
            assert n in (0, 2)
            return (*flux, n // 2)
        if k == 3 and not static:
            if f % 2 == 0:
                assert n in (0, 2)
                return (*flux, n // 2)
            if f == 1:
                assert n == 1 and iota == 0
                return (*flux, 0)
            assert n == 1
            return (*flux, iota)
        # charged interior
        if f == 0:
            assert n == 1 and iota == 0
            return (*flux, 0, 0)
        if f == 1:
            assert n in (0, 2)
            return (*flux, n // 2, 0)
        if f == 2:
            assert n == 1
            return (*flux, iota, 0)
        assert n in (0, 2)
        return (*flux, n // 2, iota)

    def encode(self, label) -> tuple:
        j2, n, iota = label
        bits = []
        for s in range(self.basis.lat.n_sites):
            flux = tuple(j2[l] for l, _ in self.ends[s])
            bits.extend(self.encode_vertex(s, flux, n[s], iota[s]))
        return tuple(bits)

    # ------------------------------------------------------------------ decode
    def decode_vertex(self, s, bits: tuple):
        """Return (flux tuple, n, iota) or raise Reject('flag')."""
        static = self.basis.lat.is_static(s)
        k = len(self.ends[s])
        flux = tuple(bits[:k])
        f = sum(flux)
        if k == 2 and not static:
            q3 = bits[2]
            if flux[0] == flux[1]:
                return flux, 2 * q3, 0
            if q3 == 1:
                raise Reject("flag")
            return flux, 1, 0
        if k == 2 and static:
            q3 = bits[2]
            if flux == (0, 0):
                if q3 == 1:
                    raise Reject("flag")
                return flux, 1, 0
            if flux == (1, 1):
                return flux, 1, q3
            return flux, 2 * q3, 0
        if k == 3 and not static:
            q4 = bits[3]
            if f % 2 == 0:
                return flux, 2 * q4, 0
            if f == 1:
                if q4 == 1:
                    raise Reject("flag")
                return flux, 1, 0
            return flux, 1, q4
        q4, q5 = bits[3], bits[4]
        if f == 0:
            if (q4, q5) != (0, 0):
                raise Reject("flag")
            return flux, 1, 0
        if f == 1:
            if q5 == 1:
                raise Reject("flag")
            return flux, 2 * q4, 0
        if f == 2:
            if q5 == 1:
                raise Reject("flag")
            return flux, 1, q4
        return flux, 2 * q4, q5

    def decode(self, bits, target_twoB=None):
        """Decode one bit string.  Returns (index, label) or raises Reject with
        reason 'flag', 'link', 'sector' or 'unknown'."""
        lat = self.basis.lat
        seen = {}
        n, iota = [], []
        for s in range(lat.n_sites):
            o, w = self.offsets[s], self.widths[s]
            flux, ns, io = self.decode_vertex(s, tuple(bits[o:o + w]))
            n.append(ns)
            iota.append(io)
            for q, (l, _) in zip(flux, self.ends[s]):
                seen.setdefault(l, []).append(q)
        for l in range(lat.n_links):
            if seen[l][0] != seen[l][1]:
                raise Reject("link")
        j2 = tuple(seen[l][0] for l in range(lat.n_links))
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
        """counts: {bit tuple or 0/1 string: multiplicity}.  Returns
        (accepted {index: count}, rejection reasons {reason: count})."""
        acc, rej = {}, {"flag": 0, "link": 0, "sector": 0, "unknown": 0}
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
