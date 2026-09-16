"""
HPC post-processing of a support: projected diagonalization, certification
and support-quality metrics (Step 5 of the SKQD manual).

Rigorous for any support B:
    E_R >= E_0                                  (variational)
    some exact eigenvalue lies in [E_R - r_H, E_R + r_H]     (Weinstein)
with the Hamiltonian residual r_H = || (H - E_R) psi_R ||, computed with the
exact H (support B u N(B)).
Gap-assumed two-sided intervals for E_0:
    Weinstein:   E_0 in [E_R - r_H, E_R]        if the level nearest E_R is E_0
    Kato-Temple: E_0 >= E_R - r_H^2 / (alpha - E_R)   if E_R < alpha <= E_1
The manual uses alpha = second Ritz value (an upper bound of E_1, so the
interval is labelled gap-assumed); on the simulator we also evaluate the
rigorous version with alpha = exact E_1 and check whether E_0 lies inside.

Support metrics against the exact ground state |Omega>:
    recall R_eps = |B n S_eps| / |S_eps|,  S_eps = smallest set carrying 1 - eps,
    false positives = |{ b in B : |<b|Omega>|^2 < 1e-8 }|,
    error = E_R - E_0.

Symbols: B = support (set of basis indices), H_B = P_B H P_B, psi_R = Ritz vector.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp


@dataclass
class RitzResult:
    B: np.ndarray
    energies: np.ndarray      # Ritz values ascending
    vectors: np.ndarray       # columns, in the local ordering of B
    rH: float                 # residual of the lowest Ritz vector with the exact H

    @property
    def ER(self):
        return float(self.energies[0])

    @property
    def ER1(self):
        return float(self.energies[1]) if len(self.energies) > 1 else np.inf

    def full_vector(self, dim: int, k: int = 0) -> np.ndarray:
        v = np.zeros(dim, dtype=complex)
        v[self.B] = self.vectors[:, k]
        return v


def ritz(H: sp.csr_matrix, B) -> RitzResult:
    B = np.asarray(sorted(set(int(b) for b in B)))
    HB = H[B][:, B].toarray()
    w, v = np.linalg.eigh((HB + HB.conj().T) / 2)
    psi = np.zeros(H.shape[0], dtype=complex)
    psi[B] = v[:, 0]
    r = H @ psi - w[0] * psi
    return RitzResult(B=B, energies=w, vectors=v, rH=float(np.linalg.norm(r)))


def closure_diagnostic(H: sp.csr_matrix, res: RitzResult, dt: float) -> float:
    """|| (1 - P_B) exp(-i H dt) psi_R ||  — the first version's 'Krylov residual',
    kept only as a subspace-closure monitor."""
    import scipy.sparse.linalg as spl
    psi = res.full_vector(H.shape[0])
    phi = spl.expm_multiply(-1j * dt * H, psi)
    phi[res.B] = 0.0
    return float(np.linalg.norm(phi))


@dataclass
class Certificate:
    ER: float
    rH: float
    weinstein: tuple          # [ER - rH, ER]  (gap-assumed lower end)
    kato_temple: tuple | None  # [ER - rH^2/(alpha-ER), ER] with alpha = second Ritz value, or None
    alpha: float
    exact_E0: float | None = None
    exact_E1: float | None = None
    kt_rigorous: tuple | None = None   # with alpha = exact E1 (simulator only)
    gap_assumption_holds: bool | None = None  # rH < E1 - ER  (Weinstein level identification)

    def as_dict(self):
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in self.__dict__.items()}


def certify(res: RitzResult, exact_E0=None, exact_E1=None) -> Certificate:
    ER, rH, alpha = res.ER, res.rH, res.ER1
    wein = (ER - rH, ER)
    # guard: a second Ritz value (numerically) equal to E_R makes the denominator vanish (near-degenerate
    # cluster, manual Step 1.5); the interval is then not reported instead of exploding
    kt = (ER - rH ** 2 / (alpha - ER), ER) if alpha - ER > 1e-6 else None
    cert = Certificate(ER=ER, rH=rH, weinstein=wein, kato_temple=kt, alpha=alpha,
                       exact_E0=exact_E0, exact_E1=exact_E1)
    if exact_E1 is not None:
        cert.gap_assumption_holds = bool(rH < exact_E1 - ER)
        if exact_E1 - ER > 1e-6:
            cert.kt_rigorous = (ER - rH ** 2 / (exact_E1 - ER), ER)
    return cert


def exact_support(prob: np.ndarray, eps: float) -> np.ndarray:
    """S_eps: indices (full basis) of the smallest set carrying 1 - eps of the weight."""
    order = np.argsort(prob)[::-1]
    cs = np.cumsum(prob[order])
    k = int(np.searchsorted(cs, 1.0 - eps, side="left") + 1)
    return order[:k]


def support_metrics(B, prob_full: np.ndarray, eps: float = 1e-3) -> dict:
    B = np.asarray(sorted(set(int(b) for b in B)))
    S = exact_support(prob_full, eps)
    recall = len(np.intersect1d(B, S)) / len(S)
    fp = int(np.sum(prob_full[B] < 1e-8))
    weight = float(prob_full[B].sum())
    return {"size": int(len(B)), "recall": float(recall), "false_positives": fp,
            "captured_weight": weight, "exact_support_size": int(len(S))}


def interval_difference(upper_interval, lower_interval):
    """Interval arithmetic for a difference  a - b  with a in [a0,a1], b in [b0,b1]."""
    (a0, a1), (b0, b1) = upper_interval, lower_interval
    return (a0 - b1, a1 - b0)


def poisson_lambda_star(k: int = 3, conf: float = 0.95) -> float:
    """Smallest Poisson mean lambda such that P(X >= k) >= conf, X ~ Poisson(lambda).

    Manual Step 4.4: "a configuration of ideal probability p is seen at least three
    times with 95 % probability".  For k = 3, conf = 0.95 this is lambda* = 6.296.
    """
    from scipy.optimize import brentq
    from scipy.stats import poisson

    if not 0.0 < conf < 1.0:
        raise ValueError("conf must be in (0, 1)")
    if k < 1:
        raise ValueError("k must be >= 1")

    def g(lam):
        return float(poisson.sf(k - 1, lam)) - conf       # sf(k-1) = P(X >= k)

    lo, hi = 1e-12, float(k)
    while g(hi) < 0.0:                                     # P(X >= k) increases with lambda
        hi *= 2.0
        if hi > 1e9:
            raise RuntimeError("no lambda found")
    return float(brentq(g, lo, hi, xtol=1e-12, rtol=1e-14))


def shot_rule(p: float, y: float, k: int = 3, conf: float = 0.95) -> int:
    """Shots per circuit so that a configuration of ideal probability `p`, observed
    through an accepted-shot yield `y`, is seen at least `k` times with probability
    >= `conf` (manual Step 4.4 / eq. 5).

    N = ceil(lambda* / (p y)) with lambda* = poisson_lambda_star(k, conf); the counts of
    one configuration over N shots are Poisson(N p y) in the rare-configuration limit.
    With k = 3, conf = 0.95, y = 0.82 f this is eq. (5) of the manual,
    S >= 6.3 / (0.82 f p).
    """
    if not 0.0 < p <= 1.0:
        raise ValueError("p must be in (0, 1]")
    if not 0.0 < y <= 1.0:
        raise ValueError("y must be in (0, 1]")
    return int(np.ceil(poisson_lambda_star(k, conf) / (p * y)))


# --------------------------------------------------------------------------- yield model
READOUT_FACTOR = 0.82   # manual Step 4.4: readout removes ~18 % of the clean shots


def yield_model(f: float, a: float = 0.0, readout_factor: float = READOUT_FACTOR) -> float:
    """Accepted-shot yield of manual Step 4.4, both terms:

        y = readout_factor * f + (1 - f) * a

    "The accepted-shot yield is ~ 0.82 f plus the garbage that decodes as valid"
    (manual Step 4.4, line 130).  The first term is the clean shots that survive readout;
    the second is the non-clean fraction (1 - f), whose bit strings are close to uniformly
    random after ~1000 two-qubit gates and are therefore accepted by the decoder with its
    random-string acceptance `a` (measured exhaustively per sector in gates E2/H0P; a =
    dim(sector)/2^n at 2x2).  With a = 0 this is the clean yield 0.82 f, which is what the
    shot rule uses (garbage acceptances add no support).
    """
    return float(readout_factor) * float(f) + (1.0 - float(f)) * float(a)


def clean_fraction_from_yield(y: float, a: float = 0.0,
                              readout_factor: float = READOUT_FACTOR) -> float:
    """Inverse of `yield_model` in f:  f = (y - a) / (readout_factor - a).

    The clean-shot fraction implied by an observed accepted-shot yield `y`.  With a = 0
    this is y / 0.82.  The inversion is ill-conditioned when y approaches a (the yield then
    carries no information about f), which is why gate H0 applies its 30 % criterion to the
    r = 1 circuits only.
    """
    den = float(readout_factor) - float(a)
    if den <= 0.0:
        raise ValueError("readout_factor must exceed the garbage acceptance a")
    return (float(y) - float(a)) / den
