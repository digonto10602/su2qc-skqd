"""
Gauge-invariant configuration basis  |b> = |{j_l}, {n_x}, {iota_x}>  of the
dressed-site construction (Step 2 of the SKQD manual), with baryon-number
sectors.

A label b is stored as (j2, n, iota): tuples of ints with j2 = 2 j_l per link,
n = occupation per site, iota = intertwiner index per site.  The basis is the
list of all labels for which every vertex has a non-empty singlet space, one
state per choice of the intertwiner indices.

Baryon number  B = 1/2 sum_x (n_x - n^vac_x),  n^vac_x = 0 on even sites and
2 on odd sites.  We store 2B as an int.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from .lattice import Ladder
from .vertex import kernel_dim


@dataclass
class Basis:
    lat: Ladder
    jmax: float
    labels: list          # list of (j2 tuple, n tuple, iota tuple)
    index: dict           # label -> position
    twoB: np.ndarray      # 2B per state

    @property
    def dim(self):
        return len(self.labels)

    def sector(self, twoB: int) -> np.ndarray:
        """Indices of the states with baryon number 2B = twoB."""
        return np.where(self.twoB == twoB)[0]

    def sector_dims(self) -> dict:
        vals, counts = np.unique(self.twoB, return_counts=True)
        return {int(v): int(c) for v, c in zip(vals, counts)}

    def vertex_ends(self, s: int, j2: tuple) -> tuple:
        """Signature (j, role) of the ends of site s for the flux labels j2."""
        return tuple((j2[l] / 2, role) for l, role in self.lat.ends()[s])


def enumerate_basis(lat: Ladder, jmax: float = 0.5) -> Basis:
    """Algorithm 1 (ENUMERATEBASIS): loop over flux assignments, per-vertex
    allowed (n, iota) options, product over vertices."""
    ends = lat.ends()
    spins2 = list(range(int(round(2 * jmax)) + 1))
    labels = []
    twoB = []
    nvac = [lat.n_vac(s) for s in range(lat.n_sites)]
    for j2 in itertools.product(spins2, repeat=lat.n_links):
        options = []
        ok = True
        for s in range(lat.n_sites):
            sig = tuple((j2[l] / 2, role) for l, role in ends[s])
            opts = []
            for n in (0, 1, 2):
                k = kernel_dim(sig, n, lat.is_static(s))
                for iota in range(k):
                    opts.append((n, iota))
            if not opts:
                ok = False
                break
            options.append(opts)
        if not ok:
            continue
        for choice in itertools.product(*options):
            n = tuple(c[0] for c in choice)
            iota = tuple(c[1] for c in choice)
            labels.append((tuple(j2), n, iota))
            twoB.append(sum(n[s] - nvac[s] for s in range(lat.n_sites)))
    index = {b: k for k, b in enumerate(labels)}
    return Basis(lat=lat, jmax=jmax, labels=labels, index=index, twoB=np.array(twoB, dtype=int))


def count_labels_without_intertwiner(basis: Basis) -> int:
    """Number of distinct ({j_l},{n_x}) labels (the first version's label set)."""
    return len({(j2, n) for (j2, n, _) in basis.labels})
