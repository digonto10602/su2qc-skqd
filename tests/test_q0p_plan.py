"""prompts/29 Part B' / prompts/28 B2-B3: corrected_clean_fraction, GO rule v3, d3r_plan, the prereg v2 grep test."""
import itertools
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.skqd import corrected_clean_fraction, pooled_reference_string_test  # noqa: E402


def test_corrected_clean_fraction_synthetic():
    rows = [(260, 800, 0.915, 0.00065, 677), (250, 800, 0.92, 0.0004, 426)]
    pooled = pooled_reference_string_test(rows, readout_factor=1.0, conf=0.95)
    c = corrected_clean_fraction(pooled, 1.2, [1.1, 1.3])
    assert abs(c["f_hat_ideal"] - pooled["f_clean"] / 1.2) < 1e-15
    lo, hi = c["f_hat_ideal_interval"]
    assert lo < c["f_hat_ideal"] < hi
    # a degenerate r interval reduces to the Garwood interval divided by r_nc
    d = corrected_clean_fraction(pooled, 1.2, [1.2, 1.2])
    assert abs(d["f_hat_ideal_interval"][0] - pooled["f_clean_68"][0] / 1.2) < 1e-12
    assert abs(d["f_hat_ideal_interval"][1] - pooled["f_clean_68"][1] / 1.2) < 1e-12
    # a wider r interval widens the result on both ends
    assert lo < d["f_hat_ideal_interval"][0] and hi > d["f_hat_ideal_interval"][1]
    # no significant excess: the lower end is 0
    z = pooled_reference_string_test([(0, 800, 0.9, 0.00065, 677)], readout_factor=1.0, conf=0.95)
    e = corrected_clean_fraction(z, 1.2, [1.1, 1.3])
    assert e["f_hat_ideal_interval"][0] == 0.0 and e["lower_bound_at_zero"]
    with pytest.raises(ValueError):
        corrected_clean_fraction(pooled, -1.0, [1.1, 1.3])


def test_corrected_clean_fraction_coverage():
    """Synthetic hit counts at a known f: the combined interval covers f_true / r_true in >= 90 of 100 seeds."""
    rng = np.random.default_rng(2028)
    f_true, r_true, N, p_ref = 0.2, 1.07, 1600, 0.915
    cover = 0
    for _ in range(100):
        n = rng.poisson(N * p_ref * f_true * r_true)
        pooled = pooled_reference_string_test([(n, N, p_ref, 0.0, 677)], readout_factor=1.0, conf=0.95)
        rb = r_true * np.exp(rng.normal(0, 0.02, 2000))
        c = corrected_clean_fraction(pooled, r_true, [float(np.percentile(rb, 2.5)), float(np.percentile(rb, 97.5))])
        lo, hi = c["f_hat_ideal_interval"]
        cover += int(lo <= f_true <= hi)
    assert cover >= 90


def test_go_rule_v3():
    from gate_Q0P_2x3 import go_rule_v3
    assert go_rule_v3(0.12, 0.06, 0.2) == "GO"
    assert go_rule_v3(0.12, 0.04, 0.2) == "AMBIGUOUS"
    assert go_rule_v3(0.09, 0.06, 0.12) == "AMBIGUOUS"
    assert go_rule_v3(0.05, 0.03, 0.099) == "NO-GO"


def test_recall_tail_prob_brute_force():
    from h0_support_plan import recall_tail_prob
    q = [0.9, 0.5, 0.3, 0.99, 0.1]
    for k in range(0, 6):
        brute = sum(np.prod([qi if b else 1 - qi for qi, b in zip(q, bits)])
                    for bits in itertools.product((0, 1), repeat=5) if sum(bits) >= k)
        assert abs(recall_tail_prob(q, k) - brute) < 1e-14


@pytest.fixture(scope="module")
def frozen_2x3():
    proto_p = os.path.join(ROOT, "scratch", "planner", "d3s_2x3_shot_rule_20261003.json")
    ver_p = os.path.join(ROOT, "data", "quantinuum", "q0p_stages", "verify.json")
    if not (os.path.exists(proto_p) and os.path.exists(ver_p)):
        pytest.skip("prototype or verify fragment absent")
    from skqd.exact import Model
    V = json.load(open(ver_p))["per_circuit"]
    idx = json.load(open(os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", "index.json")))
    mans = {c: json.load(open(os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", c + ".manifest.json")))
            for c in idx["circuits"]}
    return json.load(open(proto_p)), V, mans, Model(3)


def test_d3r_plan_reproduces_prototype(frozen_2x3):
    from gate_Q0P_2x3 import sector_sets
    from h0_support_plan import d3r_plan
    proto, V, mans, M = frozen_2x3
    for sec, tb in (("B=0", 0), ("B=1", 2)):
        r, w, S99, S999, same = sector_sets(M, tb)
        assert same
        ids = sorted(c for c, m in mans.items() if int(m["twoB"]) == tb)
        k4 = [c for c in ids if int(mans[c]["k"]) == 4]
        P = {c: np.asarray(V[c]["p_sector"]) / np.sum(V[c]["p_sector"]) for c in ids}
        d = d3r_plan(P, {c: 0.10 for c in ids}, ids, k4, S99, S999)
        pr = proto["plans"][f"{sec}|f=0.10"]["D3R"]
        assert d["shots_total"] == pr["shots_total"]
        assert d["k4_extra_per_circuit"] == pr["k4_extra_per_circuit"]
        assert all(d["shots"][c] == pr["shots"][c] for c in ids)
        assert d["P_recall_S999_ge_target"] >= 0.95 and d["lambda_min_S99"] >= d["constants"]["lambda_star"]


def test_d3r_plan_2x2_consistency():
    from gate_Q0P_2x3 import d3r_2x2_check
    if not os.path.exists(os.path.join(ROOT, "data", "hardware", "H0_2x2_prep", "shot_plan.json")):
        pytest.skip("H0_2x2 prep absent")
    chk = d3r_2x2_check()
    assert chk["ok"], chk


def test_d3r_plan_infeasible_raises():
    from h0_support_plan import d3r_plan
    P = {"a": np.array([1.0, 0.0]), "b": np.array([1.0, 0.0])}
    with pytest.raises(ValueError):
        d3r_plan(P, {"a": 0.1, "b": 0.1}, ["a", "b"], ["b"], [0, 1], [0, 1])


def test_prereg_v2_numbers_trace_to_json():
    """P5: every number in reports/Q0P_2x3_prereg.md is a number of the plan / CV JSON (renderer formats)."""
    from gate_Q0P_2x3 import PREREG_V2_FIRST_LINE, md_numbers_untraceable
    plan_p = os.path.join(ROOT, "validation", "Q0P_2x3_plan.json")
    md_p = os.path.join(ROOT, "reports", "Q0P_2x3_prereg.md")
    if not os.path.exists(plan_p):
        pytest.skip("gate Q0P_2x3_plan not run")
    md = open(md_p).read()
    assert md.split("\n")[0] == PREREG_V2_FIRST_LINE
    assert "## Convergence and coverage (decision 2a)" in md
    cv_p = os.path.join(ROOT, "validation", "CV_2x3_plan.json")
    cv = json.load(open(cv_p)) if os.path.exists(cv_p) else {}
    assert md_numbers_untraceable(md, json.load(open(plan_p))["data"], cv) == []


def test_md_numbers_untraceable_flags_typed_numbers():
    from gate_Q0P_2x3 import md_numbers_untraceable
    md = "first line\nvalue 0.1234 and 17,600 shots, `B0_ref25_k4` and typed 3.1416."
    assert md_numbers_untraceable(md, {"a": 0.1234, "b": 17600}) == ["3.1416"]
