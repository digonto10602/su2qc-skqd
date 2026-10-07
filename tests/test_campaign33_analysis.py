"""
prompts/33 A4: the analysis layer of the campaign driver (src/skqd/campaign33/analysis.py) on synthetic
order-kept chunks drawn from the EXACT Krylov distributions of the frozen NAT-O0 circuits.

A laptop dry run rarely completes a plan of record (a noisy 20-qubit shot costs seconds here), so this
test drives the same code the CI runs after sampling: chunk bookkeeping and exact prefixes, CV0-CV5 through
gate_CV's own functions (CV3 from equal-shots + k = 5 prefixes, CV4 against random baselines), the
certificate reading of ruling 2, the bootstrap and the f-cell statistics.  Seeded; no simulator involved.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from skqd.campaign33 import analysis as A  # noqa: E402
from skqd.campaign33 import circuits as C  # noqa: E402
from skqd.campaign33 import sampling as SM  # noqa: E402
from skqd.campaign33 import tokens_run as TR  # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.exists(C.INDEX), reason="the freeze has not been run")


@pytest.fixture(scope="module")
def P():
    import gate_H0_2x2
    seeds = list(gate_H0_2x2.RANDOM_SEEDS)
    del gate_H0_2x2.RANDOM_SEEDS[20:]          # 20 random baselines instead of 200 (gate_CV's quick mode trims too)
    yield A.Physics()
    gate_H0_2x2.RANDOM_SEEDS[:] = seeds


def synthetic(P, cids, shots, max_chunk, rng, family="NAT-O0"):
    """Sampler-shaped results: per circuit the chunk plan, seeds and multinomial counts of the exact state."""
    out = []
    for c, n in zip(cids, shots):
        man = C.load_manifest(family, c)
        psi = TR.exact_state(P, int(man["twoB"]), int(man["reference"]), int(man["k"]), float(man["dt"]))
        pr = TR.exact_probs(P, psi)
        keys = np.asarray(list(pr), dtype=np.int64)
        p = np.asarray(list(pr.values()))
        p = p / p.sum()
        chunks = []
        for i, (a, s) in enumerate(SM.chunk_plan(n, max_chunk)):
            draw = rng.multinomial(s, p)
            chunks.append({"start": a, "shots": s, "seed": 1000 * i, "counts": {int(k): int(v) for k, v in zip(keys, draw) if v}})
        out.append({"label": c, "requested": n, "chunks": chunks, "shots_done": n})
    return out


def test_prefixes_are_exact_chunk_sums(P):
    rng = np.random.default_rng(33)
    ids = ["B0_ref25_k1", "B0_ref25_k4"]
    res = synthetic(P, ids, [267, 1367], 476, rng)
    pre = A.Prefixes(P, 0, res)
    for c, r in zip(ids, res):
        for phi in SM.PHI:
            assert pre.covered(c, SM.rnd(phi * r["requested"]))
    n_full, sh = pre.counts({c: r["requested"] for c, r in zip(ids, res)})
    tot = sum(sum(ch["counts"].values()) for r in res for ch in r["chunks"])
    assert sh == 267 + 1367 and int(n_full.sum()) == tot, "noiseless: every string decodes into the sector"
    with pytest.raises(ValueError):
        pre.counts({"B0_ref25_k1": 5})


def test_cv_reading_end_to_end_with_cv3_and_cv4(P):
    rng = np.random.default_rng(34)
    idx = C.load_index()
    ids = [c for c in idx["families"]["NAT-O0"]["circuits"] if c.startswith("B1_")]
    plan, _ = TR.cv_plan(0.10, "B=1")
    want = {c: max(16, plan[c] // 20) for c in ids}
    res = synthetic(P, ids, [want[c] for c in ids], 476, rng)
    pre = A.Prefixes(P, 2, res)
    N_eq = 200
    eq = synthetic(P, ids, [N_eq] * len(ids), 476, rng)
    k5 = [c for c in idx["families"]["NAT-O0-k5"]["circuits"] if c.startswith("B1_")]
    r5 = synthetic(P, k5, [N_eq] * len(k5), 476, rng, family="NAT-O0-k5")
    Et = A.e_tol(P, "B=1")
    assert Et["ok"], "E_tol recomputed = validation/CV_2x3_plan.json data.E_tol to 1e-12"
    cv = A.cv_reading(P, "B=1", pre, want, Et["value"], eq=(A.Prefixes(P, 2, eq), N_eq, A.Prefixes(P, 2, r5)),
                      with_random=True)
    assert cv["cv0"]["ok"], cv["cv0"]
    cr = cv["criteria"]
    for k in ("CV1", "CV2", "CV3", "CV4", "CV5"):
        assert k in cr and isinstance(cr[k].get("ok"), bool), k
    assert cr["CV2"]["type"] == "weinstein" and cr["CV3"]["size_k5"] >= cr["CV3"]["size_k4"]
    assert len(cv["shots_curve"]) == 5 and all(p["all"]["err"] >= -1e-9 for p in cv["shots_curve"])
    # the noiseless curve converges: the full plan reads a lower Ritz energy than its 1/16 prefix
    assert cv["shots_curve"][-1]["all"]["E_R"] <= cv["shots_curve"][0]["all"]["E_R"] + 1e-12


def test_certificate_bootstrap_and_fcell_on_synthetic_counts(P):
    rng = np.random.default_rng(35)
    ids = list(TR.FCELL_SHOTS)
    res = synthetic(P, ids, [TR.FCELL_SHOTS[c] for c in ids], 476, rng)
    per = {r["label"]: TR.totals(r) for r in res}
    mans = {c: C.load_manifest("NAT-O0", c) for c in ids}
    st = A.fcell_stats(P, per, mans, kappa=1.0)
    pk = st["pooled_k1"]
    assert 0.8 < pk["f_hit"] < 1.2, "noiseless counts: f_hit ~ 1 (the reference hits / (N p_ref))"
    assert pk["f_hat_ideal_ci"][0] < pk["f_hat_ideal"] < pk["f_hat_ideal_ci"][1]
    assert all(v["accepted_fraction"] == 1.0 for v in st["per_circuit"].values())
    b0 = [c for c in ids if c.startswith("B0")]
    pre = A.Prefixes(P, 0, [r for r in res if r["label"] in b0])
    n_full, sh = pre.counts({c: TR.FCELL_SHOTS[c] for c in b0})
    pt = A.skqd_point(P, "B=0", n_full, sh)
    cert = A.certificate_reading("B=0", pt)
    assert cert["type"] == "kato_temple_exact_E1" and cert["variational_ok"]
    acc = [TR.sparse_accepted(P, per[c], 0)[0] for c in b0]
    bs = A.bootstrap_point(P, "B=0", acc, B=30, seed=33)
    assert bs["B"] == 30 and bs["err"]["ci95"][0] <= bs["err"]["ci95"][1]


def test_decode_matches_codec_on_rejected_strings(P):
    from skqd.reference_sim import bits_to_int
    good = int(P.emb.ints[int(P.M.basis.sector(0)[0])])
    bad = bits_to_int((1,) * P.n)
    acc, rej, why = A.decode_counts(P, {good: 3, bad: 2}, 0, reasons=True)
    assert sum(acc.values()) == 3 and rej == 2 and sum(why.values()) == 2 and why["unknown"] == 0
    rt = A.roundtrip_check(P, acc)
    assert rt["ok"] and rt["mismatches"] == 0
