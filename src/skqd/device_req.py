"""Device-requirement algebra for the amended budget criterion.

The amended criterion (amendment 01, section 1(c); gate S2D) is a condition on the
clean-shot fraction of a circuit executed on a device,

    f = prod_{2q gates} (1 - eps2) x prod_{1q gates} (1 - eps1) x prod_{measured} (1 - eps_ro)
      = (1 - eps2)^n_2q (1 - eps1)^n_1q (1 - eps_ro)^n_meas ,

with `mean f >= 0.1` over the circuit set and `worst f >= 0.05`.  Gate S2D evaluates f at
one declared error triple; this module inverts the same expression, so that a *requirement*
can be stated as a region in (eps2, eps1, eps_ro) instead of a single number.

Nothing here is a new physics model: `clean_shot_fraction` is the f of `gate_S2D.analyse_rzz`
written as a function of the gate counts, and every inversion is exact.

Two exact facts are used throughout.

* f depends on the error triple only through the *log-error budget*: taking -log of the
  expression above, f >= f_target is the half-space

      n_2q eps2~ + n_1q eps1~ + n_meas eps_ro~ <= log(1 / f_target),   eps~ := -log(1 - eps),

  linear in the log-errors eps~ (and, to first order in eps, in the errors themselves).
  `log_error_budget` returns the weights and the budget of that half-space.
* f is strictly decreasing in each error, so the requirement on one channel with the other
  two fixed has a closed form (`required_error`), and the requirement that a *statistic* of f
  over a circuit set reach a target is found by bisection (`required_error_for_set`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

CHANNELS = ("2q", "1q", "ro")


@dataclass(frozen=True)
class CircuitCounts:
    """The executed gate counts of one compiled circuit -- all f depends on."""
    n_2q: int
    n_1q: int
    n_rz: int
    n_meas: int
    label: str = ""

    def one_qubit(self, virtual_rz: bool = False) -> int:
        """One-qubit gates that carry an error; with a virtual-rz frame change the rz do not."""
        return int(self.n_1q - self.n_rz) if virtual_rz else int(self.n_1q)

    def weights(self, virtual_rz: bool = False) -> dict:
        return {"2q": int(self.n_2q), "1q": self.one_qubit(virtual_rz), "ro": int(self.n_meas)}

    @classmethod
    def from_analysis(cls, a: dict, n_meas: int, label: str = ""):
        """From a `gate_S2D.analyse_rzz` record (keys rzz, n_1q, n_rz) or a dict with n_2q."""
        n_2q = a["n_2q"] if "n_2q" in a else a.get("rzz", a.get("cz"))
        return cls(int(n_2q), int(a["n_1q"]), int(a.get("n_rz", 0)), int(n_meas), label)


def _check_eps(*eps):
    for e in eps:
        if not 0.0 <= float(e) < 1.0:
            raise ValueError(f"error rate {e} outside [0, 1)")


def clean_shot_fraction(n_2q: int, n_1q: int, n_meas: int,
                        eps2: float, eps1: float, eps_ro: float) -> float:
    """f = (1-eps2)^n_2q (1-eps1)^n_1q (1-eps_ro)^n_meas, computed in logs."""
    _check_eps(eps2, eps1, eps_ro)
    return math.exp(int(n_2q) * math.log1p(-eps2)
                    + int(n_1q) * math.log1p(-eps1)
                    + int(n_meas) * math.log1p(-eps_ro))


def circuit_f(counts: CircuitCounts, eps2: float, eps1: float, eps_ro: float,
              virtual_rz: bool = False) -> float:
    return clean_shot_fraction(counts.n_2q, counts.one_qubit(virtual_rz), counts.n_meas,
                               eps2, eps1, eps_ro)


def set_f(counts: list, eps2: float, eps1: float, eps_ro: float,
          virtual_rz: bool = False) -> dict:
    """mean / min / max of f over a circuit set, with the argmin labelled."""
    if not counts:
        raise ValueError("empty circuit set")
    vals = [circuit_f(c, eps2, eps1, eps_ro, virtual_rz) for c in counts]
    j = min(range(len(vals)), key=lambda i: vals[i])
    mean = sum(vals) / len(vals)
    return {"n_circuits": len(vals), "mean": mean,
            "min": vals[j], "max": max(vals), "worst_label": counts[j].label,
            "spread_min_over_mean": (vals[j] / mean) if mean > 0.0 else float("nan")}


def channel_factor(counts: CircuitCounts, channel: str, eps2: float, eps1: float,
                   eps_ro: float, virtual_rz: bool = False) -> float:
    """The product of the two channels other than `channel` ("the rest of the budget")."""
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {CHANNELS}")
    e = {"2q": (0.0, eps1, eps_ro), "1q": (eps2, 0.0, eps_ro), "ro": (eps2, eps1, 0.0)}[channel]
    return circuit_f(counts, *e, virtual_rz=virtual_rz)


def required_error(n_gates: int, f_target: float, other_factor: float) -> float | None:
    """Largest eps with other_factor x (1 - eps)^n_gates >= f_target.

    None when the channel carries no gates (no requirement) or when the other two channels
    alone already put f below the target (no eps, not even 0, satisfies it).
    """
    if not 0.0 < f_target < 1.0:
        raise ValueError("f_target must be in (0, 1)")
    if int(n_gates) <= 0:
        return None
    if other_factor <= f_target:
        return None
    return 1.0 - math.exp(math.log(f_target / other_factor) / int(n_gates))


def marginal_requirement(counts: CircuitCounts, channel: str, eps2: float, eps1: float,
                         eps_ro: float, f_target: float, virtual_rz: bool = False) -> float | None:
    """Requirement on one channel of one circuit with the other two held at their values."""
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {CHANNELS}")
    n = {"2q": counts.n_2q, "1q": counts.one_qubit(virtual_rz), "ro": counts.n_meas}[channel]
    return required_error(n, f_target, channel_factor(counts, channel, eps2, eps1, eps_ro, virtual_rz))


def _solve_decreasing(fn, lo: float, hi: float, iters: int = 200) -> float:
    """x in [lo, hi] with fn(x) = 0 for fn decreasing and fn(lo) >= 0 >= fn(hi).

    Returns the `lo` end of the final bracket, so that fn(x) >= 0 holds for the value
    returned: a requirement this function reports is always one the circuits actually meet
    (never a value that misses the criterion in the last bit).
    """
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if fn(mid) >= 0.0:
            lo = mid
        else:
            hi = mid
    return lo


def required_error_for_set(counts: list, channel: str, eps2: float, eps1: float, eps_ro: float,
                           f_target: float, virtual_rz: bool = False, stat: str = "mean",
                           eps_max: float = 0.5) -> float | None:
    """Largest error on `channel` for which `stat` of f over the set reaches `f_target`.

    stat is "mean" or "min" (the two statistics the amended criterion constrains).  Returns
    None when even a perfect channel cannot reach the target at the other two errors.
    """
    if stat not in ("mean", "min"):
        raise ValueError("stat must be 'mean' or 'min'")
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {CHANNELS}")

    def value(eps: float) -> float:
        e = {"2q": (eps, eps1, eps_ro), "1q": (eps2, eps, eps_ro), "ro": (eps2, eps1, eps)}[channel]
        return set_f(counts, *e, virtual_rz=virtual_rz)[stat]

    if value(0.0) < f_target:
        return None
    if value(eps_max) >= f_target:
        return float(eps_max)
    return _solve_decreasing(lambda e: value(e) - f_target, 0.0, eps_max)


def uniform_scale_for_set(counts: list, eps2: float, eps1: float, eps_ro: float,
                          f_target: float, virtual_rz: bool = False, stat: str = "mean",
                          scale_max: float = 1e6) -> float | None:
    """Factor lam by which all three errors may be scaled with `stat` of f still >= f_target.

    lam < 1 means every channel must improve by 1/lam; lam > 1 means there is headroom.
    """
    def value(lam: float) -> float:
        return set_f(counts, lam * eps2, lam * eps1, lam * eps_ro, virtual_rz=virtual_rz)[stat]

    if value(0.0) < f_target:
        return None
    hi = 1.0
    while value(hi) >= f_target:
        hi *= 2.0
        if hi > scale_max:
            return float(scale_max)
    return _solve_decreasing(lambda l: value(l) - f_target, 0.0, hi)


def target_with_idle(f_target: float, s_idle: float) -> float:
    """The gate-only target that is equivalent to `f_target` once idle time is charged.

    With idle-time relaxation (`skqd.idle`) the clean-shot fraction of a compiled circuit is
    f = f_gates x exp(-S_idle), so `f >= f_target` is exactly `f_gates >= f_target e^{S_idle}`:
    the idle budget shifts the half-space of `log_error_budget` by a constant,

        n_2q eps2~ + n_1q eps1~ + n_meas eps_ro~  <=  ln(1 / f_target) - S_idle .

    Every inversion in this module therefore applies unchanged to the idle-aware criterion
    when it is called with `target_with_idle(f_target, S_idle)` in place of `f_target`.  The
    bars themselves (mean 0.1, worst 0.05) are unchanged; only the f they are read on is.
    Raises when the idle term alone exhausts the budget (f_target e^{S_idle} >= 1): no device
    error rate, not even zero, can then meet the criterion on that schedule.
    """
    if not 0.0 < f_target < 1.0:
        raise ValueError("f_target must be in (0, 1)")
    if float(s_idle) < 0.0:
        raise ValueError("S_idle must be >= 0")
    t = float(f_target) * math.exp(float(s_idle))
    if t >= 1.0:
        raise ValueError(f"the idle budget S_idle = {s_idle} alone puts f below {f_target}: "
                         "the criterion is unreachable at any gate error on this schedule")
    return t


def log_error_budget(counts: CircuitCounts, f_target: float, virtual_rz: bool = False) -> dict:
    """The exact half-space form of f >= f_target for one circuit.

    Returns the budget log(1/f_target), the weights (gate counts) of the three log-errors,
    and, for each channel, the share of the budget it spends at a given error (filled in by
    `budget_shares`).
    """
    if not 0.0 < f_target < 1.0:
        raise ValueError("f_target must be in (0, 1)")
    return {"f_target": float(f_target), "budget_log": -math.log(f_target),
            "weights": counts.weights(virtual_rz), "virtual_rz": bool(virtual_rz),
            "statement": ("n_2q * (-ln(1-eps2)) + n_1q * (-ln(1-eps1)) + n_meas * (-ln(1-eps_ro)) "
                          "<= ln(1/f_target); to first order n_2q eps2 + n_1q eps1 + n_meas eps_ro "
                          "<= ln(1/f_target)")}


def budget_shares(counts: CircuitCounts, eps2: float, eps1: float, eps_ro: float,
                  f_target: float, virtual_rz: bool = False) -> dict:
    """How the log-error budget log(1/f_target) is spent by each channel at a given triple."""
    _check_eps(eps2, eps1, eps_ro)
    w = counts.weights(virtual_rz)
    spend = {"2q": w["2q"] * -math.log1p(-eps2), "1q": w["1q"] * -math.log1p(-eps1),
             "ro": w["ro"] * -math.log1p(-eps_ro)}
    total = sum(spend.values())
    budget = -math.log(f_target)
    return {"spend": spend, "total": total, "budget_log": budget,
            "over_budget_by": total - budget, "fraction_of_budget":
                {k: v / budget for k, v in spend.items()},
            "fraction_of_total": {k: (v / total if total > 0 else 0.0) for k, v in spend.items()},
            "f": math.exp(-total)}
