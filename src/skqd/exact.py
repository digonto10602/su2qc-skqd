"""
Exact sector references (Step 1.3 / Table 1 of the SKQD manual).

For a sector block H_B (baryon number B) we report
    E0, the next levels, the spectral width W = Emax - Emin, the Krylov time
    step Delta_t = pi / W (anti-aliasing condition), the ground-state support
    sizes S_eps (smallest set of configurations carrying 1 - eps of the
    ground-state weight, eps = 1e-2 and 1e-3) and the participation ratio
    PR = 1 / sum_b |<b|Omega>|^4.

Dense diagonalization for dim <= DENSE_MAX, Lanczos (scipy eigsh) above.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

from .basis import enumerate_basis
from .hamiltonian import HamiltonianBuilder, Terms
from .lattice import Ladder

DENSE_MAX = 4000


def mass_default(g2: float) -> float:
    """The manual's parameter line m = 3 g^2 / 16."""
    return 3.0 * g2 / 16.0


@dataclass
class SectorReference:
    dim: int
    energies: np.ndarray        # lowest k levels (ascending)
    emax: float
    ground: np.ndarray          # ground-state vector in the sector basis
    support99: int
    support999: int
    pr: float
    indices: np.ndarray = field(repr=False)  # sector indices into the full basis

    @property
    def E0(self):
        return float(self.energies[0])

    @property
    def W(self):
        return float(self.emax - self.energies[0])

    @property
    def dt(self):
        return float(np.pi / self.W)


def support_size(prob: np.ndarray, eps: float) -> int:
    """Smallest number of configurations whose weights sum to >= 1 - eps."""
    ps = np.sort(prob)[::-1]
    cs = np.cumsum(ps)
    return int(np.searchsorted(cs, 1.0 - eps, side="left") + 1)


def sector_reference(H: sp.csr_matrix, idx: np.ndarray, k: int = 6, dense_max=DENSE_MAX) -> SectorReference:
    h = H[idx][:, idx]
    dim = len(idx)
    if dim <= dense_max:
        w, v = np.linalg.eigh(h.toarray())
        energies = w[:k]
        emax = float(w[-1])
        ground = v[:, 0]
    else:
        kk = min(k, dim - 2)
        w, v = spl.eigsh(h, k=kk, which="SA", tol=1e-10)
        o = np.argsort(w)
        energies, v = w[o], v[:, o]
        emax = float(spl.eigsh(h, k=1, which="LA", tol=1e-8)[0][0])
        ground = v[:, 0]
    # fix the phase of the ground state (largest component positive real)
    p = np.argmax(np.abs(ground))
    ground = ground * np.exp(-1j * np.angle(ground[p]))
    prob = np.abs(ground) ** 2
    return SectorReference(
        dim=dim, energies=np.asarray(energies, dtype=float), emax=emax, ground=ground,
        support99=support_size(prob, 1e-2), support999=support_size(prob, 1e-3),
        pr=float(1.0 / np.sum(prob ** 2)), indices=idx,
    )


class Model:
    """Convenience bundle: lattice, basis, term matrices."""

    def __init__(self, Lx: int, static_sites=(), jmax: float = 0.5, verbose=False):
        self.lat = Ladder(Lx, static_sites=tuple(static_sites))
        self.basis = enumerate_basis(self.lat, jmax)
        self.builder = HamiltonianBuilder(self.basis)
        self.terms: Terms = self.builder.build(verbose=verbose)

    def H(self, g2, m=None):
        return self.terms.H(g2, mass_default(g2) if m is None else m)

    def reference(self, g2, twoB, m=None, k=6) -> SectorReference:
        return sector_reference(self.H(g2, m), self.basis.sector(twoB), k=k)
