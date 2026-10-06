"""Gate K1_2x3_fpilot (prompts/27 stage 0b): the preregistered decision rule and the analysis helpers."""
import math
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import gate_K1_2x3_fpilot as K1  # noqa: E402


def test_thresholds_are_the_prompts27_ones():
    assert K1.GO_B == 1e-3 and K1.GO_A == 3e-4
    assert K1.SHOTS == 100000 and K1.CAL_SHOTS == K1.SHOTS          # one shot count -> one job
    assert K1.MAX_ESTIMATE_S == 300.0 and K1.CELL == "T3"


def test_classify_boundaries():
    assert K1.classify(1e-3) == "GO-B"
    assert K1.classify(9.999e-4) == "GO-A"
    assert K1.classify(3e-4) == "GO-A"
    assert K1.classify(2.999e-4) == "NO-GO"
    assert K1.classify(-1e-5) == "NO-GO"
    assert K1.classify(None) is None


def test_decide_reads_the_point_and_reports_the_interval():
    d, cls, firm = K1.decide(5e-4, [2e-4, 1.2e-3])
    assert d == "GO-A" and cls == {"point": "GO-A", "lo95": "NO-GO", "hi95": "GO-B"} and not firm
    d, cls, firm = K1.decide(2e-3, [1.5e-3, 3e-3])
    assert d == "GO-B" and firm
    d, cls, firm = K1.decide(1e-5, [-1e-6, 5e-5])
    assert d == "NO-GO" and firm


def test_ideal_fraction_uses_r_nc_from_the_data_file():
    rnc, d = K1.r_nc()
    assert rnc == d["r_nc"] and 1.0 < rnc < 1.3
    assert K1.ideal_of(1.115e-3, 1.115) == pytest.approx(1e-3)
    assert K1.ideal_of(None, rnc) is None


def test_readout_from_cal():
    c0 = {(0, 0, 0): 90, (1, 0, 0): 10}
    c1 = {(1, 1, 1): 80, (1, 0, 1): 20}
    p00, p11, s0, s1 = K1.readout_from_cal(c0, c1, 3)
    assert p00 == [0.9, 1.0, 1.0] and p11 == [1.0, 0.8, 1.0] and (s0, s1) == (100, 100)


def test_expected_hits_and_pooled_statistic_round_trip():
    from skqd.skqd import READOUT_FACTOR, pooled_reference_string_test
    N, f, pref, a, dim = 100000, 2e-3, 0.93, 677 / 2 ** 20, 677
    h = K1.expected_hits(N, f, pref, a, dim, READOUT_FACTOR)
    assert h == pytest.approx(N * (0.82 * f * pref + 2 ** -20))
    res = pooled_reference_string_test([(round(h), N, pref, a, dim)], conf=0.95)
    assert res["f_clean"] == pytest.approx(f, rel=0.01)


def test_decode_circuit_counts_reference_and_garbage():
    P = K1.physics()
    M, codec = P["M"], P["codec"]
    ex = K1.exact_coarse(0, 117)
    ref = tuple(ex["reference_bits"])
    other = tuple(1 - b if i == 0 else b for i, b in enumerate(ref))     # one flipped bit: not a codeword
    man = {"reference_bits": list(ref), "twoB": 0}
    d = K1.decode_circuit({ref: 7, other: 3}, man, codec)
    assert d["reference_hits"] == 7 and d["shots"] == 10
    assert d["accepted"] == 7 and d["roundtrip_mismatches"] == 0
    assert 0.9 < ex["p_reference"] < 1.0 and ex["dim"] == len(M.reference(4.0, 0).indices)
    assert math.isclose(ex["sector_mass"], 1.0, rel_tol=1e-9)
