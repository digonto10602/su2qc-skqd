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


# ------------------------------------------------------- the clean-yield statistic (prompts/20 A)
# Decision C2'/M4.4 (data/H0_replan_owner_decisions.md, signed 2026-09-30).  The accepted-shot
# yield of `yield_model` above has two terms -- clean shots that survive readout, and uniformly
# random garbage that happens to be a codeword -- and gate H0_diag measured a THIRD: strings
# carrying a few structured errors that still satisfy the link-consistency and vertex checks and
# therefore decode.  On the 2026-09-22 ibm_fez diagnostic 13 of J1's 35 accepted strings were
# codewords at Hamming distance 2 from the reference with ideal probability 0.000, and the
# accepted count overstated the clean fraction 15x (0.0101 by inversion against 6.7e-4 measured;
# `reports/H0_replan_planner_analysis_20260922.md` section 2).  The near-clean term is not a
# hardware artefact: Aer carries it too (34-42 % of its accepted shots on the calibration
# snapshot).  `clean_fraction_from_yield` above is therefore NOT a clean-shot estimator, and is
# kept only because gates S2D, L4, H0P, H0_canary and H0_diag are computed with it.
#
# The two estimators below separate the clean component from the rest WITHOUT modelling the
# near-clean term, by using the shape of the accepted histogram instead of its total:
#   * `clean_fraction_mixture`: one parameter w in P(s | accepted) = w p_c(s) + (1 - w)/dim,
#     by maximum likelihood with a profile-likelihood interval.  Uses the whole distribution;
#     the only assumption is that the non-clean part is flat over the sector's codewords, which
#     is exactly what the decoder's exhaustive random-string acceptance means (gate E2).
#   * `reference_string_test`: the count of the single most probable codeword against its
#     accidental-acceptance expectation.  Independent of any fit, and at the shortest Krylov
#     depth (p_max 0.883 / 0.889) it is the sharper of the two; it is also the bit-order test
#     of decision C3'.
# The two validate each other: at r = 1 the reference count checks the fit, at k = 4 (p_max
# 0.127 / 0.177) the fit uses the whole distribution where no single state carries the signal.


def near_clean_yield(y: float, f: float, a: float = 0.0,
                     readout_factor: float = READOUT_FACTOR) -> float:
    """The near-clean acceptance term of decision M4.4:  y - [readout_factor f + (1 - f) a].

    The amended Step-4.4 model is

        y = readout_factor * f_clean + (1 - f_clean) * a + n

    with `n` the fraction of shots that are neither clean nor uniformly random and are
    accepted anyway (a few structured errors that keep the link-parity and vertex flags).
    `n` is not predicted by a closed form -- it is produced by the scheduled simulation and
    measured on the device as the residual of this identity -- so this function returns the
    residual rather than modelling it.  Equation (5) of the manual takes `f_clean`, which is
    what `clean_fraction_mixture` / `reference_string_test` estimate, never `y / 0.82`.
    """
    return float(y) - yield_model(f, a, readout_factor)


def _mixture_logL(n_by_state, p_ideal, dim, w):
    """L(w) = sum_s n_s log(w p_s + (1 - w)/dim), with -inf where the mixture vanishes."""
    q = w * p_ideal + (1.0 - w) / dim
    pos = q > 0.0
    m = n_by_state > 0
    if np.any(m & ~pos):                 # a counted state with zero mixture probability
        return -np.inf
    # only the counted states are multiplied: 0 * log(0) is 0 here by definition, and
    # evaluating it would raise an invalid-value warning on every grid point at w = 1
    terms = np.zeros_like(q, dtype=float)
    terms[m] = n_by_state[m] * np.log(q[m])
    return float(np.sum(terms))


def clean_fraction_mixture(n_by_state, p_ideal, dim, n_shots,
                           readout_factor: float = READOUT_FACTOR,
                           grid: int = 2001) -> dict:
    """Maximum-likelihood clean-shot fraction from the SHAPE of the accepted histogram.

    `n_by_state` are the accepted counts per sector position (length `dim`), `p_ideal` the
    ideal sector distribution of the same circuit in the same order (it must sum to 1 to
    1e-9).  The accepted shots are modelled as a two-component mixture

        P(s | accepted) = w p_ideal(s) + (1 - w) / dim,

    the second component being the decoder's uniform acceptance of random-looking strings
    (gate E2 establishes that acceptance exhaustively, so the flat component is a property of
    the code, not a fitted shape).  `w` is maximised on a `grid`-point grid refined by a
    bounded `scipy.optimize.minimize_scalar`, and `w_68` is the profile-likelihood interval
    at Delta log L = 0.5.

    The clean-shot fraction is then f = w * accepted / (n_shots * readout_factor): `w` splits
    the ACCEPTED shots, `readout_factor` undoes the readout survival of manual Step 4.4.
    Nothing here depends on the near-clean term -- near-clean strings are spread over the
    codewords at small Hamming distance, whose ideal probability is ~0, so they are absorbed
    by the flat component together with the true garbage.  That is the point of the statistic
    and the reason it is not biased where `clean_fraction_from_yield` is (decision C2').

    A zero-count circuit and a flat histogram both return w = 0 with the interval [0, 1]
    rather than raising: a circuit whose accepted shots carry no shape carries no clean signal.

    POOLING: `n_by_state` and `p_ideal` may be 2-D (one row per circuit, `dim` columns), in
    which case ONE w is fitted to the joint likelihood over all rows and `n_shots` is the total
    over those circuits.  That is how a (sector, repetition) class is estimated: the circuits
    have different ideal distributions, so their histograms cannot be added, but their
    log-likelihoods can.
    """
    from scipy.optimize import minimize_scalar

    n_by_state = np.atleast_2d(np.asarray(n_by_state, dtype=float))
    p_ideal = np.atleast_2d(np.asarray(p_ideal, dtype=float))
    dim = int(dim)
    if n_by_state.shape[1] != dim or p_ideal.shape[1] != dim:
        raise ValueError(f"n_by_state and p_ideal must both have {dim} columns (dim)")
    if n_by_state.shape[0] != p_ideal.shape[0]:
        raise ValueError("n_by_state and p_ideal must have the same number of rows (circuits)")
    sums = p_ideal.sum(axis=1)
    if np.any(np.abs(sums - 1.0) > 1e-9):
        raise ValueError(f"every row of p_ideal must sum to 1 to 1e-9 (worst {float(np.max(np.abs(sums - 1.0))):.3e}): "
                         f"pass the sector-conditional distribution, e.g. "
                         f"skqd.krylov.ideal_sector_distribution(...)['p']")
    if np.any(p_ideal < 0.0):
        raise ValueError("p_ideal must be non-negative")
    accepted = float(n_by_state.sum())
    n_shots = float(n_shots)
    n_circuits = int(n_by_state.shape[0])

    def mL(w):
        return _mixture_logL(n_by_state, p_ideal, dim, float(w))

    def out(w, lo, hi, gain):
        cy = (w * accepted / n_shots) if n_shots > 0 else 0.0
        cy_lo = (lo * accepted / n_shots) if n_shots > 0 else 0.0
        cy_hi = (hi * accepted / n_shots) if n_shots > 0 else 0.0
        rf = float(readout_factor)
        return {"w": float(w), "w_68": [float(lo), float(hi)],
                "accepted": accepted, "shots": n_shots, "dim": dim,
                "circuits": n_circuits,
                "clean_accepted": float(w * accepted),
                "clean_accepted_68": [float(lo * accepted), float(hi * accepted)],
                "clean_yield": float(cy), "f_clean": float(cy / rf),
                "f_clean_68": [float(cy_lo / rf), float(cy_hi / rf)],
                "logL_gain": float(gain), "readout_factor": rf,
                "estimator": ("maximum likelihood in P(s|accepted) = w p_ideal(s) + (1-w)/dim, "
                              "profile-likelihood 68 % interval at Delta log L = 0.5")}

    if accepted <= 0.0 or n_shots <= 0.0:
        return out(0.0, 0.0, 1.0, 0.0)

    ws = np.linspace(0.0, 1.0, int(grid))
    Ls = np.array([mL(w) for w in ws])
    j = int(np.argmax(Ls))
    lo_b, hi_b = ws[max(j - 1, 0)], ws[min(j + 1, len(ws) - 1)]
    w_hat, L_hat = float(ws[j]), float(Ls[j])
    if hi_b > lo_b:
        r = minimize_scalar(lambda w: -mL(w), bounds=(lo_b, hi_b), method="bounded",
                            options={"xatol": 1e-10})
        if np.isfinite(r.fun) and -float(r.fun) >= L_hat:
            w_hat, L_hat = float(np.clip(r.x, 0.0, 1.0)), -float(r.fun)
    L0 = mL(0.0)
    gain = L_hat - L0

    # profile-likelihood interval: g(w) = L(w) - L_hat + 0.5 changes sign at each end
    def g(w):
        v = mL(w)
        return (-1e300 if not np.isfinite(v) else v) - L_hat + 0.5

    lo, hi = 0.0, 1.0
    if w_hat > 0.0 and g(0.0) < 0.0:
        from scipy.optimize import brentq
        lo = float(brentq(g, 0.0, w_hat, xtol=1e-12))
    if w_hat < 1.0 and g(1.0) < 0.0:
        from scipy.optimize import brentq
        hi = float(brentq(g, w_hat, 1.0, xtol=1e-12))
    return out(w_hat, min(lo, w_hat), max(hi, w_hat), gain)


def reference_string_test(n_ref: int, n_shots: int, p_ref: float, acceptance: float, dim: int,
                          readout_factor: float = READOUT_FACTOR, conf: float = 0.6827) -> dict:
    """Is the circuit's most probable codeword seen more often than accidental acceptance?

    The bit-order test of decision C3' and the clean-yield estimator that needs no fit.  A
    non-clean shot is accepted with the decoder's exhaustive random-string acceptance
    `acceptance` and then lands uniformly on one of the `dim` codewords, so the accidental
    expectation for one named codeword is `n_shots * acceptance / dim`.  Under the null the
    count is Poisson with that mean, which gives both the significance (`z`, `P_ge`) and the
    clean-yield estimate `excess / (n_shots * p_ref)`.

    Poisson (Garwood) interval on `n_ref` at `conf`, propagated to the clean yield and to f.
    """
    from scipy.stats import chi2, poisson

    n_ref = int(n_ref)
    n_shots = int(n_shots)
    expected = float(n_shots) * float(acceptance) / float(dim)
    sigma = float(np.sqrt(expected)) if expected > 0 else None
    excess = float(n_ref) - expected
    alpha = 1.0 - float(conf)
    lo_n = 0.0 if n_ref == 0 else float(chi2.ppf(alpha / 2.0, 2 * n_ref) / 2.0)
    hi_n = float(chi2.ppf(1.0 - alpha / 2.0, 2 * n_ref + 2) / 2.0)
    rf = float(readout_factor)
    den = float(n_shots) * float(p_ref)

    def cy(x):
        return (x - expected) / den if den > 0 else None

    y, y_lo, y_hi = cy(float(n_ref)), cy(lo_n), cy(hi_n)
    # the Gaussian approximation n_ref +- sqrt(n_ref) as well: it is the band quoted in
    # reports/H0_replan_planner_analysis_20260922.md section 2 (f_clean 2.6e-4 .. 1.07e-3
    # for the pooled count), and the exact Garwood interval above is wider on the upper end
    s_lo, s_hi = float(n_ref) - np.sqrt(n_ref), float(n_ref) + np.sqrt(n_ref)
    g_lo, g_hi = cy(s_lo), cy(s_hi)
    return {
        "n_reference": n_ref, "shots": n_shots, "p_reference": float(p_ref),
        "garbage_acceptance": float(acceptance), "dim": int(dim),
        "expected_from_garbage": expected, "sigma": sigma, "excess": excess,
        "z": (excess / sigma) if sigma else None,
        "P_ge": float(poisson.sf(n_ref - 1, expected)) if expected > 0 else None,
        "n_reference_68": [lo_n, hi_n], "confidence": float(conf),
        "clean_yield": y, "clean_yield_68": [y_lo, y_hi],
        "f_clean": (None if y is None else y / rf),
        "f_clean_68": ([None if y_lo is None else y_lo / rf,
                        None if y_hi is None else y_hi / rf]),
        "n_reference_68_sqrt_n": [s_lo, s_hi],
        "f_clean_68_sqrt_n": ([None if g_lo is None else g_lo / rf,
                               None if g_hi is None else g_hi / rf]),
        "readout_factor": rf,
        "estimator": ("(n_ref - n_shots a / dim) / (n_shots p_ref readout_factor); Poisson "
                      "(Garwood) interval on n_ref at the stated confidence"),
    }


def pooled_reference_string_test(rows, readout_factor: float = READOUT_FACTOR,
                                 conf: float = 0.6827) -> dict:
    """The reference-string test pooled over circuits with different ideal distributions.

    `rows` = [(n_reference, n_shots, p_reference, acceptance, dim), ...].  The accidental
    expectation adds (each circuit contributes N_c a_c / dim_c) and so does the clean
    denominator (N_c p_ref,c), which is why the pooled clean yield is

        (sum_c n_ref,c - sum_c N_c a_c / dim_c) / sum_c N_c p_ref,c

    -- the pooled row of section 2 of `reports/H0_replan_planner_analysis_20260922.md`
    (5 pubs, 8267 shots, 6 hits, 2.018 expected, P = 0.017, f_clean 6.65e-4).
    """
    from scipy.stats import chi2, poisson

    n_ref = int(sum(int(r[0]) for r in rows))
    shots = int(sum(int(r[1]) for r in rows))
    expected = float(sum(float(r[1]) * float(r[3]) / float(r[4]) for r in rows))
    den = float(sum(float(r[1]) * float(r[2]) for r in rows))
    sigma = float(np.sqrt(expected)) if expected > 0 else None
    excess = float(n_ref) - expected
    alpha = 1.0 - float(conf)
    lo_n = 0.0 if n_ref == 0 else float(chi2.ppf(alpha / 2.0, 2 * n_ref) / 2.0)
    hi_n = float(chi2.ppf(1.0 - alpha / 2.0, 2 * n_ref + 2) / 2.0)
    rf = float(readout_factor)

    def f(x):
        return ((x - expected) / den / rf) if den > 0 else None

    return {"n_reference": n_ref, "shots": shots, "circuits": len(rows),
            "expected_from_garbage": expected, "sigma": sigma, "excess": excess,
            "z": (excess / sigma) if sigma else None,
            "P_ge": float(poisson.sf(n_ref - 1, expected)) if expected > 0 else None,
            "clean_denominator_shots_x_p_ref": den,
            "clean_yield": ((excess / den) if den > 0 else None),
            "f_clean": f(float(n_ref)),
            "f_clean_68": [f(lo_n), f(hi_n)],
            "f_clean_68_sqrt_n": [f(float(n_ref) - np.sqrt(n_ref)),
                                  f(float(n_ref) + np.sqrt(n_ref))],
            "readout_factor": rf, "confidence": float(conf),
            "estimator": ("(sum n_ref - sum N a / dim) / (sum N p_ref readout_factor); "
                          "Poisson (Garwood) interval on the pooled count")}


# ------------------------------------------------- the ideal-sample fraction (prompts/29 3(1), Part B')
R_NC_SOURCE = "data/cf_trajectories/r_nc.json"


def corrected_clean_fraction(pooled: dict, r_nc: float, r_nc_95) -> dict:
    """The corrected reference-hit fraction  f_hat_ideal = f_hit / r_nc  (prompts/29 3(1)).

    `pooled` is the output of `pooled_reference_string_test` (its `f_clean` is f_hit, its
    `f_clean_68` the Garwood interval at `pooled["confidence"]` -- the key name is the module's,
    the confidence is whatever the caller asked for, 0.95 for the GO rules).  `r_nc` is the
    near-clean correction of gate CF_traj (the UPPER end of the 95 % bootstrap interval of the
    pooled f_hit / f_ideal(1e-3), `data/cf_trajectories/r_nc.json`), `r_nc_95` that bootstrap
    interval [lo, hi].

    What it measures: f_ideal, the fraction of shots whose output distribution is the ideal one
    (fault-free plus benign-fault shots).  f_hit over-estimates it under gate noise by the factor
    r(1e-3) of CF_traj (1.03-1.12); dividing by the upper bound r_nc makes the bar harder, never
    looser.  Caveat (prompts/29 3(1)): r_nc is a gate-noise (A6 channel) value; on IBM devices
    (idle dephasing) it is unknown and the A5 arm of CF_traj is the only model estimate.

    Interval: the Garwood interval of the hit count and the bootstrap interval of r_nc combined
    on the log scale (sum of variances, each end separately):
        s_r   = (ln r_hi - ln r_lo) / (2 z)                     (bootstrap, symmetric in ln r)
        lo    = f_hat exp(-sqrt(ln(f_hit / f_lo)^2 + (z s_r)^2))
        hi    = f_hat exp(+sqrt(ln(f_hi / f_hit)^2 + (z s_r)^2))
    with z the normal quantile of `pooled["confidence"]`.  A non-positive Garwood lower end
    (no significant excess) gives lo = 0.
    """
    from scipy.stats import norm

    conf = float(pooled.get("confidence", 0.95))
    z = float(norm.ppf(0.5 + conf / 2.0))
    r_nc = float(r_nc)
    r_lo, r_hi = float(r_nc_95[0]), float(r_nc_95[1])
    if not (r_nc > 0 and 0 < r_lo <= r_hi):
        raise ValueError("r_nc and its interval must be positive with lo <= hi")
    f_hit = pooled["f_clean"]
    f_lo, f_hi = pooled["f_clean_68"]
    s_r = (np.log(r_hi) - np.log(r_lo)) / (2.0 * z)
    if f_hit is None:
        raise ValueError("pooled f_clean is None (no clean denominator)")
    f_hat = float(f_hit) / r_nc
    if f_hit > 0 and f_lo is not None and f_lo > 0:
        lo = f_hat * float(np.exp(-np.sqrt(np.log(f_hit / f_lo) ** 2 + (z * s_r) ** 2)))
    else:
        lo = 0.0
    if f_hit > 0 and f_hi is not None and f_hi > 0:
        hi = f_hat * float(np.exp(np.sqrt(np.log(f_hi / f_hit) ** 2 + (z * s_r) ** 2)))
    else:
        hi = (float(f_hi) / r_nc * float(np.exp(z * s_r))) if (f_hi is not None and f_hi > 0) else 0.0
    return {"f_hit": float(f_hit), "f_hit_interval": [f_lo, f_hi], "confidence": conf, "z": z,
            "r_nc": r_nc, "r_nc_95": [r_lo, r_hi], "sigma_ln_r_bootstrap": float(s_r),
            "f_hat_ideal": f_hat, "f_hat_ideal_interval": [float(lo), float(hi)],
            "lower_bound_at_zero": bool(lo == 0.0),
            "estimator": ("f_hat_ideal = f_hit / r_nc; interval = Garwood (hit count) and bootstrap (r_nc) "
                          "combined on the log scale, each end separately"),
            "r_nc_source": R_NC_SOURCE}


# ----------------------------------------------- the H1-derived energy tolerance (prompts/30 2.7)
def h1_energy_tolerance(H, prob_full: np.ndarray, refs, recall_target: float = 0.8, eps: float = 1e-3,
                        sector_idx=None, E0=None) -> dict:
    """E_tol = E_R(R u S_eps^{top}) - E_0, the Ritz error of the best support that just meets a
    recall target of S_eps (gate H1, manual Step 10: recall >= 0.8 of S_999).

    The top ceil(recall_target |S_eps|) states by exact ground-state weight are selected with
    `controls.oracle` (the function of gate S1's Table 3; `sector_idx` defaults to the states of
    positive weight, which gives the same order), the references `refs` are added, and the
    Ritz energy is taken with `ritz`.  E_0 defaults to the Ritz energy on the support of the
    exact ground state (prob_full > 0), which contains the ground state and therefore equals
    E_0 to round-off.  With refs = [] and recall_target = n / |S_eps| this is Table 3's oracle
    row at |B| = n.
    """
    import math

    from .controls import oracle

    prob_full = np.asarray(prob_full, dtype=float)
    S = exact_support(prob_full, eps)
    n = int(math.ceil(float(recall_target) * len(S) - 1e-9))
    n = max(0, min(n, len(S)))
    if sector_idx is None:
        sector_idx = np.flatnonzero(prob_full > 0)
    top = oracle(prob_full, np.asarray(sector_idx, dtype=int), n)
    basis = np.asarray(sorted(set(int(b) for b in top) | set(int(r) for r in refs)))
    res = ritz(H, basis)
    if E0 is None:
        E0 = ritz(H, np.flatnonzero(prob_full > 0)).ER
    return {"E_tol": float(res.ER - float(E0)), "E_R": float(res.ER), "E0": float(E0), "rH": float(res.rH),
            "n_top": n, "support_size": int(len(S)), "eps": float(eps), "recall_target": float(recall_target),
            "states_top": [int(b) for b in sorted(int(x) for x in top)], "references": [int(r) for r in refs],
            "basis_size": int(len(basis)), "captured_weight": float(prob_full[basis].sum()),
            "definition": "E_R(R u top ceil(recall_target |S_eps|) states of S_eps by weight) - E_0 (controls.oracle, ritz)"}
