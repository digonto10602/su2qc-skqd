"""
Minimal gauge-invariant importance model (Step 7.4 of the SKQD manual): a ridge
regression on hand-built gauge-invariant configuration features, conditioned on
lambda = (g^2, m, B, Lx), trained leakage-safely (splits by (lambda, lattice),
never by row; the test coupling is excluded from training on every lattice).

Target: f(b; lambda) ~ log max(|<b|Omega_lambda>|, 1e-6).
Score usage: ranking configurations of a sector (ML-alone proposal, Step 7.3 iii).

The sixteen features of one configuration b = ({j_l},{n_x},{iota_x}):
  1 flux x-links, 2 flux y-links, 3 quarks on even sites, 4 holes on odd sites,
  5 'meson' links (flux link, quark on its even end, hole on its odd end),
  6 flux loops (plaquettes with four flux links), 7 vertices with two flux ends,
  8 vertices with three flux ends, 9 sum of intertwiner labels,
  10 diagonal energy H_bb - H_sea,sea, 11 total flux links, 12 sites with n = 1,
  13 even sites with n = 2, 14 odd sites with n = 0, 15 flux links with n = 1 at both ends,
  16 (H_bb - H_sea,sea)^2.
The design matrix is [F, F / g^2, g^2, 1/g^2, m, 2B, Lx, 1].

Symbols: F = feature matrix, w = ridge weights, alpha = ridge penalty.
"""
from __future__ import annotations

import numpy as np

from .basis import Basis
from .hamiltonian import Terms
from .krylov import dirac_sea
from .lattice import Ladder


def features(basis: Basis, terms: Terms, g2: float, m: float) -> np.ndarray:
    lat: Ladder = basis.lat
    links = lat.links
    plaqs = lat.plaquettes
    ends = lat.ends()
    diag = (m * terms.mass.diagonal() + 0.5 * g2 * terms.electric.diagonal()).real
    d_sea = diag[dirac_sea(basis)]
    F = np.zeros((basis.dim, 16))
    for k, (j2, n, iota) in enumerate(basis.labels):
        fx = sum(j2[l] for l, (_, _, d) in enumerate(links) if d == "x")
        fy = sum(j2[l] for l, (_, _, d) in enumerate(links) if d == "y")
        q_even = sum(n[s] for s in range(lat.n_sites) if lat.parity(s) == 0)
        h_odd = sum(2 - n[s] for s in range(lat.n_sites) if lat.parity(s) == 1)
        meson = 0
        both1 = 0
        for l, (a, b, _) in enumerate(links):
            if j2[l]:
                even, odd = (a, b) if lat.parity(a) == 0 else (b, a)
                if n[even] >= 1 and n[odd] <= 1:
                    meson += 1
                if n[a] == 1 and n[b] == 1:
                    both1 += 1
        loops = sum(1 for pl in plaqs if all(j2[pl[key]] for key in ("b", "r", "t", "l")))
        v2 = sum(1 for s in range(lat.n_sites) if sum(j2[l] for l, _ in ends[s]) == 2)
        v3 = sum(1 for s in range(lat.n_sites) if sum(j2[l] for l, _ in ends[s]) == 3)
        dE = diag[k] - d_sea
        F[k] = [fx, fy, q_even, h_odd, meson, loops, v2, v3, sum(iota), dE, sum(j2),
                sum(1 for s in range(lat.n_sites) if n[s] == 1),
                sum(1 for s in range(lat.n_sites) if lat.parity(s) == 0 and n[s] == 2),
                sum(1 for s in range(lat.n_sites) if lat.parity(s) == 1 and n[s] == 0),
                both1, dE ** 2]
    return F


def design(F: np.ndarray, g2: float, m: float, twoB: int, Lx: int) -> np.ndarray:
    N = F.shape[0]
    lam = np.tile([g2, 1.0 / g2, m, twoB, Lx, 1.0], (N, 1))
    return np.hstack([F, F / g2, lam])


class RidgeRanker:
    def __init__(self, alpha: float = 1.0, floor: float = 1e-6):
        self.alpha = alpha
        self.floor = floor
        self.w = None
        self.mu = None
        self.sd = None

    @staticmethod
    def target(ground: np.ndarray, floor: float) -> np.ndarray:
        return np.log(np.maximum(np.abs(ground), floor))

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.mu = X.mean(axis=0)
        self.sd = X.std(axis=0) + 1e-12
        Z = (X - self.mu) / self.sd
        A = Z.T @ Z + self.alpha * np.eye(Z.shape[1])
        self.w = np.linalg.solve(A, Z.T @ (y - y.mean()))
        self.b = y.mean()
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        Z = (X - self.mu) / self.sd
        return Z @ self.w + self.b


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])
