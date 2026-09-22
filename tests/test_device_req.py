"""skqd.device_req: the inversion of gate S2D's clean-shot-fraction model.

Every test either reproduces a number that gate S2D already recorded in
validation/S2D.json or checks an exact algebraic identity of the model.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import math

import pytest

from skqd.device_req import (CircuitCounts, budget_shares, circuit_f, clean_shot_fraction,
                             log_error_budget, marginal_requirement, required_error,
                             required_error_for_set, set_f, uniform_scale_for_set)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EPS2, EPS1, EPS_RO = 1e-3, 1e-4, 2e-3          # gate S2D's declared inputs
N_MEAS = 20                                     # 2x3 measured qubits


def s2d():
    with open(os.path.join(ROOT, "validation", "S2D.json")) as fh:
        return json.load(fh)["data"]


def counts_2x3():
    return [CircuitCounts(e["rzz"], e["n_1q"], e["n_rz"], N_MEAS,
                          f"{e['sector']} ref{e['reference']} k{e['k']}")
            for e in s2d()["2x3"]["per_circuit"]]


def test_reproduces_s2d_f_factors():
    d = s2d()["2x3"]
    k1 = d["f_factors_k1"]
    assert clean_shot_fraction(k1["rzz"], 0, 0, EPS2, EPS1, EPS_RO) == pytest.approx(k1["f_2q"], rel=1e-12)
    assert clean_shot_fraction(0, k1["n_1q"], 0, EPS2, EPS1, EPS_RO) == pytest.approx(k1["f_1q"], rel=1e-12)
    assert clean_shot_fraction(0, 0, N_MEAS, EPS2, EPS1, EPS_RO) == pytest.approx(k1["f_ro"], rel=1e-12)


def test_reproduces_s2d_per_circuit_and_set_statistics():
    d = s2d()["2x3"]
    cs = counts_2x3()
    for c, e in zip(cs, d["per_circuit"]):
        assert circuit_f(c, EPS2, EPS1, EPS_RO) == pytest.approx(e["f"], rel=1e-12)
        assert circuit_f(c, EPS2, EPS1, EPS_RO, virtual_rz=True) == pytest.approx(
            e["f_virtual_rz"], rel=1e-12)
    st = set_f(cs, EPS2, EPS1, EPS_RO)
    assert st["mean"] == pytest.approx(d["f"]["mean"], rel=1e-12)
    assert st["min"] == pytest.approx(d["f"]["min"], rel=1e-12)
    assert st["max"] == pytest.approx(d["f"]["max"], rel=1e-12)
    stv = set_f(cs, EPS2, EPS1, EPS_RO, virtual_rz=True)
    assert stv["mean"] == pytest.approx(d["f_virtual_rz"]["mean"], rel=1e-12)
    assert stv["min"] == pytest.approx(d["f_virtual_rz"]["min"], rel=1e-12)


def test_reproduces_s2d_required_eps2_at_the_mean_counts():
    """gate S2D's `eps2_required_for_f_0.1`: closed form at the mean gate counts."""
    d = s2d()["2x3"]
    mr, m1 = d["rzz"]["mean"], d["n_1q"]["mean"]
    rest = (1 - EPS1) ** m1 * (1 - EPS_RO) ** N_MEAS
    got = required_error(int(round(mr)), 0.1, rest)
    assert got == pytest.approx(d["eps2_required_for_f_0.1"], rel=1e-9)


def test_required_error_round_trip_and_edges():
    n, target = 2158, 0.1
    other = 0.5
    eps = required_error(n, target, other)
    assert other * (1 - eps) ** n == pytest.approx(target, rel=1e-12)
    # a channel with no gates carries no requirement
    assert required_error(0, target, other) is None
    # the other channels alone already below the target: unreachable at any eps, including 0
    assert required_error(n, target, 0.05) is None
    with pytest.raises(ValueError):
        required_error(n, 1.0, other)


def test_marginal_requirement_matches_the_model():
    c = CircuitCounts(2158, 7346, 4255, N_MEAS)
    e2 = marginal_requirement(c, "2q", EPS2, EPS1, EPS_RO, 0.1)
    assert circuit_f(c, e2, EPS1, EPS_RO) == pytest.approx(0.1, rel=1e-12)
    e1 = marginal_requirement(c, "1q", EPS2, EPS1, EPS_RO, 0.1)
    assert circuit_f(c, EPS2, e1, EPS_RO) == pytest.approx(0.1, rel=1e-12)
    # readout alone cannot repair the declared triple: 2q x 1q is already below 0.1
    assert marginal_requirement(c, "ro", EPS2, EPS1, EPS_RO, 0.1) is None
    with pytest.raises(ValueError):
        marginal_requirement(c, "3q", EPS2, EPS1, EPS_RO, 0.1)


def test_required_error_for_set_is_consistent_and_conservative():
    cs = counts_2x3()
    for stat, target in (("mean", 0.1), ("min", 0.05)):
        e2 = required_error_for_set(cs, "2q", EPS2, EPS1, EPS_RO, target, stat=stat)
        assert set_f(cs, e2, EPS1, EPS_RO)[stat] == pytest.approx(target, rel=1e-9)
    # identical circuits: the set solution equals the single-circuit closed form
    one = [CircuitCounts(2158, 7346, 4255, N_MEAS)] * 3
    a = required_error_for_set(one, "2q", EPS2, EPS1, EPS_RO, 0.1, stat="mean")
    b = marginal_requirement(one[0], "2q", EPS2, EPS1, EPS_RO, 0.1)
    assert a == pytest.approx(b, rel=1e-9)
    # unreachable channel -> None
    assert required_error_for_set(cs, "ro", EPS2, EPS1, EPS_RO, 0.1, stat="mean") is None
    # virtual rz relaxes the two-qubit requirement (fewer error-carrying one-qubit gates)
    phys = required_error_for_set(cs, "2q", EPS2, EPS1, EPS_RO, 0.1)
    virt = required_error_for_set(cs, "2q", EPS2, EPS1, EPS_RO, 0.1, virtual_rz=True)
    assert virt > phys


def test_monotonicity_in_every_channel():
    c = CircuitCounts(2158, 7346, 4255, N_MEAS)
    base = circuit_f(c, EPS2, EPS1, EPS_RO)
    assert circuit_f(c, 2 * EPS2, EPS1, EPS_RO) < base
    assert circuit_f(c, EPS2, 2 * EPS1, EPS_RO) < base
    assert circuit_f(c, EPS2, EPS1, 2 * EPS_RO) < base
    assert circuit_f(c, 0.0, 0.0, 0.0) == pytest.approx(1.0)


def test_uniform_scale_for_set():
    cs = counts_2x3()
    lam = uniform_scale_for_set(cs, EPS2, EPS1, EPS_RO, 0.1)
    assert 0.0 < lam < 1.0          # the declared triple misses 0.1, so all errors must shrink
    assert set_f(cs, lam * EPS2, lam * EPS1, lam * EPS_RO)["mean"] == pytest.approx(0.1, rel=1e-9)
    # a triple that already passes has headroom lam > 1
    assert uniform_scale_for_set(cs, EPS2 / 10, EPS1 / 10, EPS_RO / 10, 0.1) > 1.0


def test_log_error_budget_is_the_exact_half_space():
    c = CircuitCounts(2158, 7346, 4255, N_MEAS)
    b = log_error_budget(c, 0.1)
    assert b["budget_log"] == pytest.approx(math.log(10.0))
    assert b["weights"] == {"2q": 2158, "1q": 7346, "ro": 20}
    assert log_error_budget(c, 0.1, virtual_rz=True)["weights"]["1q"] == 7346 - 4255
    sh = budget_shares(c, EPS2, EPS1, EPS_RO, 0.1)
    assert sh["f"] == pytest.approx(circuit_f(c, EPS2, EPS1, EPS_RO), rel=1e-12)
    assert sum(sh["spend"].values()) == pytest.approx(sh["total"], rel=1e-12)
    assert sh["over_budget_by"] > 0           # the declared triple is over budget
    # a point exactly on the boundary spends exactly the budget
    e2 = marginal_requirement(c, "2q", EPS2, EPS1, EPS_RO, 0.1)
    on = budget_shares(c, e2, EPS1, EPS_RO, 0.1)
    assert on["over_budget_by"] == pytest.approx(0.0, abs=1e-12)


def test_counts_from_analysis_record():
    a = {"rzz": 2158, "n_1q": 7346, "n_rz": 4255}
    c = CircuitCounts.from_analysis(a, N_MEAS, "k1")
    assert (c.n_2q, c.n_1q, c.n_rz, c.n_meas, c.label) == (2158, 7346, 4255, 20, "k1")
    assert c.one_qubit() == 7346 and c.one_qubit(True) == 3091
    with pytest.raises(ValueError):
        clean_shot_fraction(1, 1, 1, 1.0, 0.0, 0.0)
