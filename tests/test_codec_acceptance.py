"""prompts/36 R2: the factorised random-string acceptance of the decoder equals the exhaustive loop."""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.codec import Codec, Reject  # noqa: E402
from skqd.exact import Model  # noqa: E402

REASONS = ("flag", "link", "sector", "unknown")


def test_factorised_equals_exhaustive_2x2():
    from gate_H0P import random_acceptance, random_acceptance_factorised
    c = Codec(Model(2).basis)
    for tb in (0, 2):
        fa = random_acceptance_factorised(c, tb)
        ex = random_acceptance(c, tb)
        assert fa["accepted"] == ex["accepted"] and fa["strings"] == ex["strings"] == 2 ** 12
        assert all(fa["reasons"][r] == ex["reasons"].get(r, 0) for r in REASONS)
        assert fa["accepted"] + sum(fa["reasons"].values()) == fa["strings"]


def test_factorised_equals_exhaustive_file_2x3():
    from gate_H0P import random_acceptance_factorised
    ex = json.load(open(os.path.join(ROOT, "data", "cv", "acceptance_2x3.json")))
    c = Codec(Model(3).basis)
    for sec, tb in (("B=0", 0), ("B=1", 2)):
        fa = random_acceptance_factorised(c, tb)
        assert fa["accepted"] == ex[sec]["accepted"]
        assert all(fa["reasons"][r] == ex[sec]["reasons"].get(r, 0) for r in REASONS)


def test_monte_carlo_matches_direct_decode_2x2():
    """gate_CV.mc_acceptance's shortcut (flag / link counted once for both sectors) equals two plain decode calls."""
    import gate_CV as CV
    c = Codec(Model(2).basis)
    mc = CV.mc_acceptance(c, 3000, 5, chunk=700)
    rng = np.random.default_rng(5)
    acc = {"B=0": 0, "B=1": 0}
    why = {s: {r: 0 for r in REASONS} for s in acc}
    done = 0
    while done < 3000:
        m = min(700, 3000 - done)
        x = rng.integers(0, 2 ** 12, size=m, dtype=np.int64)
        for v in x:
            b = tuple((int(v) >> k) & 1 for k in range(12))
            for sec, tb in (("B=0", 0), ("B=1", 2)):
                try:
                    c.decode(b, tb)
                    acc[sec] += 1
                except Reject as r:
                    why[sec][str(r)] += 1
        done += m
    assert mc["accepted"] == acc and mc["reasons"] == why


def test_acceptance_2x4_file_if_present():
    p = os.path.join(ROOT, "data", "cv", "acceptance_2x4.json")
    if not os.path.exists(p):
        return
    d = json.load(open(p))
    for sec in ("B=0", "B=1"):
        assert d[sec]["strings"] == 2 ** 28
        assert d[sec]["accepted"] + sum(d[sec]["reasons"].values()) == 2 ** 28
        assert abs(d[sec]["monte_carlo"]["z"]) <= 3
    assert d["cross_checks"]["2x2"]["factorised_equals_exhaustive"] and d["cross_checks"]["2x3"]["factorised_equals_exhaustive"]
