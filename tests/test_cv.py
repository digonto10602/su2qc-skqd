"""prompts/30: the sequence sampler, the H1-derived energy tolerance, nested prefixes, the re-sizing rule."""
import hashlib
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import basis_vector, coarse_states, references, term_groups  # noqa: E402
from skqd.noise import SEQUENCE_REASONS, measure_and_decode, measure_and_decode_sequence  # noqa: E402

# sha256 of measure_and_decode's output on the fixed 2x2 input below, recorded on 2026-10-05 BEFORE
# measure_and_decode_sequence was added (prompts/30 step 1: the default path must stay byte-identical)
MAD_FINGERPRINT = "5a3cbbf27a25289a4eefa01a9c3c23e54f637d6724414a3e61007801be5d7857"


@pytest.fixture(scope="module")
def m2():
    M = Model(2)
    g2 = 4.0
    codec = Codec(M.basis)
    cw = codec.all_codewords()
    r = M.reference(g2, 0, k=4)
    refs = references(M.basis, 0)
    groups = term_groups(M.terms, g2, mass_default(g2))
    psi = coarse_states(groups, basis_vector(M.basis.dim, refs[0]), r.dt, 2)[2]
    return M, codec, cw, psi


def test_measure_and_decode_unchanged(m2):
    M, codec, cw, psi = m2
    acc, rej = measure_and_decode(codec, cw, psi, 5000, 0.3, 0.01, np.random.default_rng(7), target_twoB=0)
    s = json.dumps([sorted(acc.items()), sorted(rej.items())])
    assert hashlib.sha256(s.encode()).hexdigest() == MAD_FINGERPRINT


def test_sequence_histogram_identity_seed7(m2):
    M, codec, cw, psi = m2
    acc, rej = measure_and_decode(codec, cw, psi, 5000, 0.3, 0.01, np.random.default_rng(7), target_twoB=0)
    dec, why = measure_and_decode_sequence(codec, cw, psi, 5000, 0.3, 0.01, np.random.default_rng(7), target_twoB=0)
    assert len(dec) == 5000 and len(why) == 5000
    u, c = np.unique(dec[dec >= 0], return_counts=True)
    assert {int(k): int(v) for k, v in zip(u, c)} == acc
    seq_rej = {r: int(np.sum(why == i)) for i, r in enumerate(SEQUENCE_REASONS) if i > 0}
    assert seq_rej == rej
    assert np.all((dec >= 0) == (why == 0))


def test_nested_prefixes_are_subsets(m2):
    M, codec, cw, psi = m2
    dec, _ = measure_and_decode_sequence(codec, cw, psi, 4000, 0.2, 0.01, np.random.default_rng(3), target_twoB=0)
    prev = set()
    for n in (250, 500, 1000, 2000, 4000):
        cur = set(int(x) for x in dec[:n] if x >= 0)
        assert prev.issubset(cur)
        prev = cur


@pytest.fixture(scope="module")
def m3():
    from threadpoolctl import threadpool_limits
    M = Model(3)
    H = M.H(4.0)
    out = {}
    with threadpool_limits(1):
        for twoB in (0, 2):
            r = M.reference(4.0, twoB, k=4)
            p = np.zeros(M.basis.dim)
            p[r.indices] = np.abs(r.ground) ** 2
            out[twoB] = (r, p, M.basis.sector(twoB), references(M.basis, twoB))
    return M, H, out


def test_h1_energy_tolerance_full_support(m3):
    from skqd.skqd import exact_support, h1_energy_tolerance, ritz
    M, H, out = m3
    for twoB, (r, p, sec, refs) in out.items():
        e = h1_energy_tolerance(H, p, refs, recall_target=1.0, sector_idx=sec, E0=r.E0)
        S = exact_support(p, 1e-3)
        assert e["n_top"] == len(S)
        assert abs(e["E_tol"] - (ritz(H, np.union1d(S, refs)).ER - r.E0)) < 1e-12
        # the E0 default (Ritz on the support of the exact ground state) equals E0
        e2 = h1_energy_tolerance(H, p, refs, recall_target=0.8, sector_idx=sec)
        assert abs(e2["E0"] - r.E0) < 1e-10


def test_h1_energy_tolerance_reproduces_table3_oracle(m3):
    """Table 3's oracle rows of gate S1 through controls.oracle (refs = [], recall_target = n / |S999|).
    BLAS pinned to one thread: the |B| = 80, B=0 boundary sits on 4 states of equal weight (round-off tie)."""
    from threadpoolctl import threadpool_limits

    from skqd.skqd import exact_support, h1_energy_tolerance
    M, H, out = m3
    t3 = json.load(open(os.path.join(ROOT, "validation", "S1.json")))["data"]["table3"]
    with threadpool_limits(1):
        for twoB, (r, p, sec, refs) in out.items():
            S = exact_support(p, 1e-3)
            for n in (40, 80):
                e = h1_energy_tolerance(H, p, [], recall_target=n / len(S), sector_idx=sec, E0=r.E0)
                assert e["n_top"] == n
                assert abs(e["E_tol"] - t3[f"B={twoB // 2}|oracle|{n}"]["err"]) < 1e-9


def test_resized_shots_rule():
    from gate_CV import resized_shots
    assert resized_shots(267, 2) == 600 and resized_shots(267, 4) == 1100 and resized_shots(267, 8) == 2200
    assert resized_shots(17600, 2) == 35200 and resized_shots(1000, 8) == 8000


def test_sig_support_reused_and_B_all_nested(m2):
    """The CV point uses gate_H0_2x2.sig_support (P9 unchanged); B_all of nested prefixes is nested."""
    import gate_CV as G
    M, codec, cw, psi = m2
    S = G.Sector(M, "2x2", "B=0", 0, 38 / 4096)
    dec, _ = measure_and_decode_sequence(codec, cw, psi, 3000, 0.2, 0.01, np.random.default_rng(5), target_twoB=0)
    prev = None
    for n in (500, 1500, 3000):
        x = dec[:n]
        cnt = np.bincount(x[x >= 0], minlength=M.basis.dim)
        pt = S.point(cnt, n, with_random=False)
        assert set(S.refs).issubset(pt["_B_all"]) and set(S.refs).issubset(pt["B_sig_list"])
        if prev is not None:
            assert set(prev).issubset(set(pt["_B_all"]))
        prev = pt["_B_all"]
        assert pt["sig"]["E_R"] >= S.E0 - 1e-9
