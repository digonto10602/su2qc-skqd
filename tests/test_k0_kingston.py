"""Gate K0_2x3_2x4 (prompts/25 Part A): the pure functions on a synthetic 3-edge record."""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import gate_K0_2x3_2x4 as K0  # noqa: E402


def synthetic_record():
    q = {str(i): {"sx_error": 2e-4 * (i + 1), "x_error": 2e-4 * (i + 1), "measure_error": 1e-2 * (i + 1),
                  "T1_s": 2e-4, "T2_s": 1e-4 * (i + 1)} for i in range(3)}
    e = {"0-1": {"target_key": [0, 1], "cz_error": 1e-3, "cz_duration_s": 6.8e-8},
         "1-2": {"target_key": [1, 2], "cz_error": 3e-3, "cz_duration_s": 8.0e-8},
         "2-0": {"target_key": [2, 0], "cz_error": 1.0, "cz_duration_s": 6.8e-8}}
    return {"qubits": q, "edges": e}


def test_record_stats_excludes_uncalibrated_marker():
    st = K0.record_stats(synthetic_record())
    assert st["n_calibrated"] == 2 and st["n_uncalibrated"] == 1
    assert st["uncalibrated_keys"] == ["2-0"]
    assert st["cz_error_min"] == pytest.approx(1e-3, abs=0)
    assert st["cz_error_median"] == pytest.approx(2e-3, rel=1e-15)
    assert st["cz_error_p10"] == pytest.approx(1e-3 + 0.1 * 2e-3, rel=1e-15)
    assert st["sx_error_min"] == pytest.approx(2e-4) and st["measure_error_min"] == pytest.approx(1e-2)
    assert K0.uncalibrated_pairs(synthetic_record()) == {(0, 2)}


def test_percentile_by_hand_matches_numpy():
    rng = np.random.default_rng(3)
    v = rng.random(343)
    for q in (0, 10, 50, 90, 100):
        assert abs(K0.percentile_by_hand(v, q) - float(np.percentile(v, q))) < 1e-15


def test_ceiling_formula_and_ordering():
    st = K0.record_stats(synthetic_record())
    n_cz, n_1q, n_meas = 50, 120, 3
    ceil = K0.f_ceiling_2q(st["cz_error_min"], n_cz)
    assert ceil == pytest.approx((1 - 1e-3) ** 50, rel=1e-15)
    bound = K0.f_best_patch_bound(st["cz_error_min"], st["sx_error_min"], st["measure_error_min"], n_cz, n_1q, n_meas)
    # a layout that uses the worse edge / worse qubits sits below the bound
    layout = (1 - 3e-3) ** 25 * (1 - 1e-3) ** 25 * (1 - 4e-4) ** n_1q * (1 - 2e-2) ** n_meas
    assert layout <= bound <= ceil
    e, ex = K0.eps2_needed(0.05, 5477)
    assert e == pytest.approx(-math.log(0.05) / 5477, rel=1e-15)
    assert (1 - ex) ** 5477 == pytest.approx(0.05, rel=1e-12)
    assert e == pytest.approx(5.4696e-4, rel=1e-4)        # the planner's 5.47e-4


def test_xy4_cap():
    assert K0.xy4_capped(1e-3, 1e-4, 2.8) == pytest.approx(2.8e-4)
    assert K0.xy4_capped(1e-3, 5e-4, 2.8) == 1e-3            # capped by the gate-only value
    for fi in (1e-30, 1e-6, 1e-3, 1.0):
        assert K0.xy4_capped(1e-3, fi, 3.2) <= 1e-3


def test_bars():
    assert K0.bars(0.1) == {"meets_mean_0.1": True, "meets_worst_0.05": True}
    assert K0.bars(0.06) == {"meets_mean_0.1": False, "meets_worst_0.05": True}
    assert K0.bars(1e-5) == {"meets_mean_0.1": False, "meets_worst_0.05": False}


def test_routing_target_drops_only_the_named_cz_keys():
    from qiskit.circuit.library import CZGate, SXGate
    from qiskit.transpiler import InstructionProperties, Target
    t = Target(num_qubits=3)
    t.add_instruction(SXGate(), {(i,): InstructionProperties(error=1e-4, duration=3.2e-8) for i in range(3)})
    t.add_instruction(CZGate(), {(0, 1): InstructionProperties(error=1e-3), (1, 0): InstructionProperties(error=1e-3),
                                 (1, 2): InstructionProperties(error=3e-3), (2, 1): InstructionProperties(error=3e-3)})
    new, removed = K0.routing_target(t, {(1, 2)})
    assert removed == 2
    assert set(new["cz"]) == {(0, 1), (1, 0)}
    assert set(new["sx"]) == {(0,), (1,), (2,)}
    assert new["cz"][(0, 1)].error == pytest.approx(1e-3)
