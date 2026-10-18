"""
prompts/33f R1 / R2: K2 judged by Fisher's exact test per clbit, and the class-2 representation decision file.

- the synthetic case of R1: a 7-shot arm with 0 ones against a 512-shot arm at p = 0.15 -- the Wald z is 7-12 (the
  7-shot arm's variance term is 0), Fisher's exact test gives p = 0.60 (not flagged at 0.0027);
- the committed JSONs (C2_KCHK run 1 / run 2, the laptop summary) give `rm`, flag nothing, and reproduce the planner's
  per-clbit values (clbit 2: 0.60, 3: 0.35, 5: 1.0, 8: 0.045, 17: 0.046 against the CI Kraus arm; minimum 0.074
  against the CI RM arm);
- the committed decision file says what the script computes, with the four references, their job ids / paths and the
  power lines (section 2 of prompts/33f).
"""
import json
import math
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")]

from skqd.campaign33 import stats as ST  # noqa: E402

pytest.importorskip("scipy")
import campaign33_c2_decide as DEC  # noqa: E402

DECISION = os.path.join(ROOT, DEC.OUT)


def test_fisher_on_the_synthetic_zero_of_seven_case():
    n_big, p_big = 512, 0.15
    x_big = round(p_big * n_big)                         # 77 ones of 512
    fi = ST.fisher_marginals([x_big], n_big, [0], 7)
    assert fi["p_by_clbit"][0] == pytest.approx(0.60, abs=0.005)
    assert fi["flagged_clbits"] == [] and fi["per_test_level"] == pytest.approx(0.0026998, abs=1e-7)
    # the Wald z the K2 statistic of 33d used: the 7-shot arm's term is 0, so z = p / sqrt(p (1 - p) / 512)
    p = x_big / n_big
    wald = p / math.sqrt(p * (1 - p) / n_big)
    assert 7.0 < wald < 12.0
    a = {"shots": n_big, "n_bits": 1, "mean_hamming_weight": p, "se_mean_hamming_weight": math.sqrt(p * (1 - p) / n_big),
         "marginals_by_clbit": [p], "se_marginals_by_clbit": [math.sqrt(p * (1 - p) / n_big)]}
    b = {"shots": 7, "n_bits": 1, "mean_hamming_weight": 0.0, "se_mean_hamming_weight": 0.0,
         "marginals_by_clbit": [0.0], "se_marginals_by_clbit": [0.0]}
    w = ST.structure_compare(a, b)
    assert w["clbits_outside"] == [0] and 7.0 < w["z_marginals_by_clbit"][0] < 12.0, "the Wald flag Fisher removes"


def test_fisher_still_flags_a_real_difference():
    fi = ST.fisher_marginals([256], 512, [0], 60)          # 0.5 against 0 of 60
    assert fi["flagged_clbits"] == [0] and fi["min_p"] < 1e-10


def test_marginal_ones_refuses_non_counts():
    with pytest.raises(ValueError):
        ST.marginal_ones({"shots": 7, "marginals_by_clbit": [0.3]})


def test_decision_on_the_committed_jsons():
    doc = DEC.decide(DEC.gather())
    assert doc["production_representation"] == "rm" and doc["reference_arm"] == "none"
    refs = doc["references"]
    assert set(refs) == {"ci_kraus_cpu", "ci_rm_cpu", "laptop_kraus_cpu", "laptop_rm_cpu"}
    assert [refs[k]["shots"] for k in ("ci_kraus_cpu", "ci_rm_cpu", "laptop_kraus_cpu", "laptop_rm_cpu")] == [7, 12, 67, 78]
    for r in refs.values():
        assert r["fisher_min_p"] >= ST.THREE_SIGMA_TWO_SIDED and r["k2"]["fisher_flagged_clbits"] == []
        assert abs(r["z_w"]) <= 3.0 and r["k4"]["status"] == "agree" and r["agrees"]
    p = refs["ci_kraus_cpu"]["k2"]["fisher"]["p_by_clbit"]
    for clbit, want, tol in ((2, 0.60, 0.005), (3, 0.35, 0.005), (5, 1.0, 1e-9), (8, 0.045, 0.0005), (17, 0.046, 0.0005)):
        assert p[clbit] == pytest.approx(want, abs=tol), clbit
    assert refs["ci_kraus_cpu"]["fisher_min_p"] == pytest.approx(0.045, abs=0.0005)
    assert refs["ci_rm_cpu"]["fisher_min_p"] == pytest.approx(0.074, abs=0.0005)
    # the Wald artefact this replaces: clbits 2, 3, 5 of the 7-shot Kraus arm were outside 3 sigma
    assert {2, 3, 5} <= set(refs["ci_kraus_cpu"]["k2"]["wald_clbits_outside_3sigma_information"])
    assert refs["ci_kraus_cpu"]["k2"]["power"]["min_visible_marginal_diff"] == pytest.approx(0.571, abs=0.001)
    assert refs["ci_rm_cpu"]["k2"]["power"]["min_visible_marginal_diff"] == pytest.approx(0.438, abs=0.001)
    assert all(v == 0.0 for v in doc["recompute_max_abs_diff"].values())


def test_the_committed_decision_file():
    assert os.path.exists(DECISION), "run scripts/campaign33_c2_decide.py"
    d = json.load(open(DECISION))
    assert d["production_representation"] == "rm" and d["reference_arm"] == "none"
    assert d["kraus_gpu"].startswith("unusable (aer 0.15.1 GPU Kraus path")
    assert len(d["references"]) == 4 and len(d["power_lines"]) == 4
    assert all(v >= 0.0027 for v in d["fisher_min_p_by_reference"].values())
    assert {r["job"] for r in d["references"].values()} == {"59828887", None}
    assert d["production_arm"]["job"] == "59780907" and d["production_arm"]["shots"] == 512
    assert d["supersedes"]["value"] == "blocked"
    for r in d["references"].values():
        assert r["source"] in ("validation/C2_KCHK.json", "data/campaign33/c33c_diag/summary.json") and r["json_path"]
    # the file is what the script computes from the committed inputs (only the provenance fields may differ)
    doc = DEC.decide(DEC.gather())
    for k in ("production_representation", "reference_arm", "fisher_min_p_by_reference", "z_w_by_reference",
              "power_lines", "inputs", "production_seconds_per_shot"):
        assert d[k] == doc[k], k
