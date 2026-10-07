"""
Statistics of the 2x3 four-class campaign (prompts/33 section 2): clean-fraction estimators with
their intervals, the noiseless per-state agreement test, the bootstrap, and the comparison statistic
of every "redo".  numpy / scipy only; nothing here imports qiskit.
"""
from __future__ import annotations

import math

import numpy as np

CONF95 = 0.95


# --------------------------------------------------------------------------- intervals
def garwood(n: int, conf: float = CONF95):
    """Exact (Garwood) Poisson interval on a count n."""
    from scipy.stats import chi2
    a = 1.0 - conf
    lo = 0.0 if n <= 0 else float(chi2.ppf(a / 2.0, 2 * n) / 2.0)
    hi = float(chi2.ppf(1.0 - a / 2.0, 2 * n + 2) / 2.0)
    return lo, hi


def wilson(k: int, n: int, conf: float = CONF95):
    """Wilson score interval on a binomial proportion k/n."""
    from scipy.stats import norm
    if n <= 0:
        return None, None
    z = float(norm.ppf(0.5 + conf / 2.0))
    p = k / n
    den = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def poisson_two_sided(k: int, mu: float) -> float:
    """Two-sided probability of observing a count as extreme as k under Poisson(mu):
    sum of P(j) over all j with P(j) <= P(k) (the 'minimum-likelihood' rule)."""
    from scipy.stats import poisson
    if mu <= 0:
        return 1.0 if k == 0 else 0.0
    pk = poisson.pmf(k, mu)
    hi = int(max(k, mu) + 20 * math.sqrt(mu) + 50)
    j = np.arange(0, hi + 1)
    pj = poisson.pmf(j, mu)
    return float(min(1.0, pj[pj <= pk * (1 + 1e-9)].sum()))


def binomial_two_sided(k: int, n: int, p: float) -> float:
    from scipy.stats import binomtest
    return float(binomtest(int(k), int(n), float(p)).pvalue)


def binomial_band(n: int, p: float, conf: float = CONF95):
    """Central binomial band [lo, hi] on a count out of n at probability p."""
    from scipy.stats import binom
    a = 1.0 - conf
    return int(binom.ppf(a / 2.0, n, p)), int(binom.isf(a / 2.0, n, p))


def poisson_band(mu: float, conf: float = CONF95):
    from scipy.stats import poisson
    a = 1.0 - conf
    return int(poisson.ppf(a / 2.0, mu)), int(poisson.isf(a / 2.0, mu))


# --------------------------------------------------------------------------- clean fraction
def f_hit_cell(rows, kappa: float = 1.0, conf: float = CONF95, r_nc: float = None, r_nc_95=None) -> dict:
    """Pooled reference-hit fraction over circuits (prompts/33 2.1):
    f_hit = (sum n_ref - sum N a/dim) / (sum N p_ref kappa), Garwood interval on the pooled count;
    kappa = 1 on the Quantinuum path, 0.82 where the hardware convention is compared (class 2).
    rows: [(n_ref, N, p_ref, a, dim), ...].  With r_nc: f_hat_ideal = f_hit / r_nc, interval divided
    through (skqd.skqd.corrected_clean_fraction convention)."""
    from skqd.skqd import pooled_reference_string_test
    pooled = pooled_reference_string_test(rows, readout_factor=kappa, conf=conf)
    out = {"n_reference": pooled["n_reference"], "shots": pooled["shots"], "circuits": pooled["circuits"],
           "expected_from_garbage": pooled["expected_from_garbage"], "kappa": kappa, "confidence": conf,
           "f_hit": pooled["f_clean"], "f_hit_ci": pooled["f_clean_68"],
           "estimator": pooled["estimator"]}
    if r_nc is not None:
        out["r_nc"] = float(r_nc)
        out["f_hat_ideal"] = None if out["f_hit"] is None else out["f_hit"] / float(r_nc)
        out["f_hat_ideal_ci"] = [None if x is None else x / float(r_nc) for x in out["f_hit_ci"]]
        out["r_nc_95"] = None if r_nc_95 is None else [float(x) for x in r_nc_95]
    return out


# --------------------------------------------------------------------------- noiseless agreement
def per_state_test(counts: dict, probs: dict, n_shots: int, n_sigma: float = 5.0, p_min: float = 1e-3) -> dict:
    """|n_s/N - p_s| <= n_sigma sqrt(p_s (1-p_s)/N) for every state with p_s >= p_min (prompts/33 2.4).
    counts / probs keyed by the same state labels (ints)."""
    tested, worst, fails = 0, 0.0, []
    if n_shots <= 0:
        return {"n_shots": 0, "n_sigma": n_sigma, "p_min": p_min, "tested_states": 0, "max_z": 0.0,
                "failures": [], "ok": True, "fraction_outside_exact_support": 0.0, "note": "no shots"}
    for s, p in probs.items():
        if p < p_min:
            continue
        tested += 1
        sig = math.sqrt(p * (1.0 - p) / n_shots)
        z = abs(counts.get(s, 0) / n_shots - p) / sig if sig > 0 else 0.0
        worst = max(worst, z)
        if z > n_sigma:
            fails.append({"state": int(s), "p": float(p), "observed": int(counts.get(s, 0)), "z": float(z)})
    mass_out = float(sum(v for s, v in counts.items() if probs.get(s, 0.0) == 0.0)) / max(1, n_shots)
    return {"n_shots": int(n_shots), "n_sigma": n_sigma, "p_min": p_min, "tested_states": tested,
            "max_z": float(worst), "failures": fails, "ok": not fails,
            "fraction_outside_exact_support": mass_out}


def tv_distance(c1: dict, c2: dict) -> float:
    n1, n2 = sum(c1.values()), sum(c2.values())
    keys = set(c1) | set(c2)
    return 0.5 * float(sum(abs(c1.get(k, 0) / n1 - c2.get(k, 0) / n2) for k in keys))


def tv_expectation_multinomial(probs: dict, n1: int, n2: int, reps: int = 200, seed: int = 33) -> dict:
    """Mean and 95th percentile of the two-sample TV distance of two multinomial samples of sizes n1, n2
    from the same distribution (the null for the C3_LE / C3_SEL vs C3_AER comparison)."""
    rng = np.random.default_rng(seed)
    ks = list(probs)
    p = np.asarray([probs[k] for k in ks], float)
    p = p / p.sum()
    tv = []
    for _ in range(reps):
        a, b = rng.multinomial(n1, p), rng.multinomial(n2, p)
        tv.append(0.5 * float(np.abs(a / n1 - b / n2).sum()))
    return {"mean": float(np.mean(tv)), "p95": float(np.percentile(tv, 95)), "reps": reps, "seed": seed}


# --------------------------------------------------------------------------- bootstrap
def bootstrap_counts(counts_list, stat, B: int = 2000, seed: int = 33, conf: float = CONF95):
    """Percentile bootstrap: resample the shots within each circuit (multinomial on its own counts),
    evaluate stat(list of resampled {state: count}) B times.  Returns point, interval and B."""
    rng = np.random.default_rng(seed)
    keys = [list(c) for c in counts_list]
    probs = [np.asarray([c[k] for k in ks], float) for c, ks in zip(counts_list, keys)]
    N = [int(p.sum()) for p in probs]
    vals = []
    for _ in range(B):
        res = []
        for ks, p, n in zip(keys, probs, N):
            if n == 0:
                res.append({})
                continue
            draw = rng.multinomial(n, p / n)
            res.append({k: int(v) for k, v in zip(ks, draw) if v})
        v = stat(res)
        if v is not None:
            vals.append(float(v))
    a = (1.0 - conf) / 2.0
    point = stat(counts_list)
    return {"point": None if point is None else float(point),
            "ci": [float(np.quantile(vals, a)), float(np.quantile(vals, 1 - a))] if vals else [None, None],
            "B": B, "seed": seed, "valid": len(vals),
            "scheme": "percentile; shots resampled within each circuit (multinomial on its counts)"}


# --------------------------------------------------------------------------- the comparison statistic
def sigma_of(ci):
    """95 % half-width / 1.96 (prompts/33 2.5); None without an interval."""
    if ci is None or ci[0] is None or ci[1] is None:
        return None
    return (float(ci[1]) - float(ci[0])) / 2.0 / 1.96


def compare(new, new_ci, old, old_ci=None, old_sigma=None, old_sigma_label=None) -> dict:
    """Delta = new - old, sigma = sqrt(s_new^2 + s_old^2), verdict consistent (<= 2 sigma), tension
    (<= 4 sigma), inconsistent; `no_old_uncertainty` when the old value has none."""
    if new is None or old is None:
        return {"new": new, "old": old, "delta": None, "verdict": "not_comparable"}
    d = float(new) - float(old)
    sn = sigma_of(new_ci)
    so = old_sigma if old_sigma is not None else sigma_of(old_ci)
    out = {"new": float(new), "new_ci95": new_ci, "old": float(old), "old_ci95": old_ci, "delta": d,
           "sigma_new": sn, "sigma_old": so, "old_sigma_label": old_sigma_label}
    if so is None:
        out.update({"sigma": sn, "verdict": "no_old_uncertainty"})
        return out
    s = math.sqrt((sn or 0.0) ** 2 + so ** 2)
    out["sigma"] = s
    if s == 0:
        out["verdict"] = "consistent" if d == 0 else "inconsistent"
    else:
        z = abs(d) / s
        out["z"] = z
        out["verdict"] = "consistent" if z <= 2 else ("tension" if z <= 4 else "inconsistent")
    return out


def seed_spread_sigma(values) -> float:
    """Old uncertainty from a seed spread: (max - min)/2/1.96 (label `seed_spread`)."""
    v = [float(x) for x in values]
    return (max(v) - min(v)) / 2.0 / 1.96
