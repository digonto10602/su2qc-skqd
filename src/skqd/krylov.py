"""
Support-generating states (Step 4 of the SKQD manual), emulated exactly in
the gauge-invariant basis.

  * exact Krylov states      |psi_k> = exp(-i k H dt) |b0>,  k = 0 .. d-1
  * first-order Trotter      |psi_k> = [ prod_gamma exp(-i H_gamma dt) ]^k |b0>
  * coarse single-step       |psi_k> =   prod_gamma exp(-i H_gamma k dt)   |b0>   (one step per circuit)
with the term groups gamma = diagonal (mass + electric), one group per hopping
link, one per plaquette, applied in that order (the order is a convention of
this package; it matters for the Trotterised and coarse states, not for the
exact Krylov states).

Reference configurations (Step 4.2): the Dirac sea, the one-meson
configurations (quark on the even end, hole on the odd end, flux on the link),
the diquark on each even site (B = 1), and for static sectors the flux string
along the bottom row plus its one-plaquette deformations.

Symbols: dt = pi / W_B Krylov time step, d = number of Krylov states,
b0 = reference configuration, H_gamma = term group.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

from .basis import Basis
from .hamiltonian import Terms


def basis_vector(dim: int, k: int) -> np.ndarray:
    v = np.zeros(dim, dtype=complex)
    v[k] = 1.0
    return v


def exact_krylov_states(H: sp.csr_matrix, psi0: np.ndarray, dt: float, d: int) -> list:
    out = [psi0.astype(complex)]
    for _ in range(1, d):
        out.append(spl.expm_multiply(-1j * dt * H, out[-1]))
    return out


def apply_groups(groups: list, psi: np.ndarray, theta: float) -> np.ndarray:
    """prod_gamma exp(-i theta H_gamma) |psi> with the groups applied in list order
    (the first group acts first)."""
    for Hg in groups:
        psi = spl.expm_multiply(-1j * theta * Hg, psi)
    return psi


def trotter_states(groups: list, psi0: np.ndarray, dt: float, d: int) -> list:
    out = [psi0.astype(complex)]
    for _ in range(1, d):
        out.append(apply_groups(groups, out[-1], dt))
    return out


def coarse_states(groups: list, psi0: np.ndarray, dt: float, kmax: int) -> list:
    """k = 0 (reference itself), 1, ..., kmax."""
    out = [psi0.astype(complex)]
    for k in range(1, kmax + 1):
        out.append(apply_groups(groups, psi0.astype(complex), k * dt))
    return out


def term_groups(terms: Terms, g2: float, m: float) -> list:
    g = terms.groups(g2, m)
    return [sp.csr_matrix(v) for v in g.values()]


def sample_counts(psi: np.ndarray, shots: int, rng: np.random.Generator) -> dict:
    """Multinomial sampling in the configuration basis -> {basis index: count}."""
    p = np.abs(psi) ** 2
    p = p / p.sum()
    draws = rng.multinomial(shots, p)
    nz = np.nonzero(draws)[0]
    return {int(k): int(draws[k]) for k in nz}


# ---------------------------------------------------------------- references
def dirac_sea(basis: Basis) -> int:
    lat = basis.lat
    j2 = tuple(0 for _ in range(lat.n_links))
    n = tuple(lat.n_vac(s) for s in range(lat.n_sites))
    iota = tuple(0 for _ in range(lat.n_sites))
    return basis.index[(j2, n, iota)]


def one_meson_references(basis: Basis) -> list:
    """Quark on the even end, hole on the odd end, flux on that link (one per link)."""
    lat = basis.lat
    refs = []
    for l, (a, b, _) in enumerate(lat.links):
        even, odd = (a, b) if lat.parity(a) == 0 else (b, a)
        j2 = [0] * lat.n_links
        j2[l] = 1
        n = [lat.n_vac(s) for s in range(lat.n_sites)]
        n[even] = 1
        n[odd] = 1
        label = (tuple(j2), tuple(n), tuple(0 for _ in range(lat.n_sites)))
        refs.append(basis.index[label])
    return refs


def diquark_references(basis: Basis) -> list:
    """Diquark (n = 2) on each even site, no flux: the B = 1 references."""
    lat = basis.lat
    refs = []
    for s in range(lat.n_sites):
        if lat.parity(s) == 0:
            n = [lat.n_vac(x) for x in range(lat.n_sites)]
            n[s] = 2
            label = (tuple(0 for _ in range(lat.n_links)), tuple(n), tuple(0 for _ in range(lat.n_sites)))
            refs.append(basis.index[label])
    return refs


def string_references(basis: Basis) -> list:
    """Static sector: the flux string along the bottom row between the two static
    charges (Dirac-sea matter) plus its one-plaquette deformations (all iota)."""
    lat = basis.lat
    s0, s1 = sorted(lat.static_sites)
    (x0, y0), (x1, y1) = lat.coords(s0), lat.coords(s1)
    assert y0 == y1 == 0, "string references assume both charges on the bottom row"
    string_links = [lat.link_index(lat.site_index(x, 0), lat.site_index(x + 1, 0)) for x in range(x0, x1)]
    n = tuple(lat.n_vac(s) for s in range(lat.n_sites))
    j2_string = [0] * lat.n_links
    for l in string_links:
        j2_string[l] = 1
    candidates = [tuple(j2_string)]
    for pl in lat.plaquettes:
        j2 = list(j2_string)
        for key in ("b", "r", "t", "l"):
            j2[pl[key]] = 1 - j2[pl[key]]
        candidates.append(tuple(j2))
    refs = []
    for j2 in candidates:
        for k, (jj, nn, _) in enumerate(basis.labels):
            if jj == j2 and nn == n:
                refs.append(k)
    return sorted(set(refs))


def references(basis: Basis, twoB: int) -> list:
    if basis.lat.static_sites:
        return string_references(basis)
    if twoB == 0:
        return [dirac_sea(basis)] + one_meson_references(basis)
    if twoB == 2:
        return diquark_references(basis)
    raise ValueError("references are defined for B = 0, B = 1 and the static sectors")
