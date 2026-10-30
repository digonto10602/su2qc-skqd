"""Unit tests of the CIPSI-type selected CI (skqd.selected_ci) used by scripts/selected_ci_baseline.py."""
import numpy as np
import pytest
import scipy.sparse as sp

from skqd import selected_ci as sci
from skqd.controls import cipsi as package_cipsi
from skqd.exact import Model
from skqd.krylov import references
from skqd.skqd import ritz


def _sector(L, twoB):
    M = Model(L)
    H = M.H(4.0).tocsr()
    idx = np.asarray(M.basis.sector(twoB), dtype=int)
    Hs = H[idx][:, idx].tocsr()
    diag = np.real(Hs.diagonal())
    E0 = float(np.linalg.eigvalsh(Hs.toarray())[0])
    refs = np.searchsorted(idx, references(M.basis, twoB))
    return M, H, idx, Hs, diag, E0, refs


def test_pt2_matches_brute_force_on_a_random_hermitian_matrix():
    rng = np.random.default_rng(7)
    n = 30
    A = rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))
    A[np.abs(A) < 1.2] = 0.0                       # sparse pattern: not every state is connected
    Hd = (A + A.conj().T) / 2 + np.diag(np.arange(n, dtype=float))
    Hs = sp.csr_matrix(Hd)
    diag = np.real(np.diag(Hd))
    S = np.array([0, 1, 2])
    it = sci.evaluate(Hs, diag, S)
    w, v = np.linalg.eigh(Hd[np.ix_(S, S)])
    assert it["E_var"] == pytest.approx(w[0], abs=1e-12)
    psi = np.zeros(n, dtype=complex)
    psi[S] = v[:, 0]
    num = np.abs(Hd @ psi) ** 2
    ext = [a for a in range(n) if a not in S and np.any(Hd[a, S] != 0)]
    e = {a: num[a] / (w[0] - diag[a]) for a in ext}
    assert it["E_pt2"] == pytest.approx(sum(e.values()), rel=1e-12, abs=1e-14)
    rk = it["_rank"]
    assert set(rk["ext"].tolist()) == set(ext)
    assert np.all(np.diff(np.abs(rk["e"])) <= 1e-12)          # ranked by |e_a| descending


def test_cipsi_is_variational_monotone_and_exact_at_full_sector():
    _, _, idx, Hs, diag, E0, refs = _sector(2, 0)
    path = sci.cipsi_path(Hs, diag, refs, 1.25, E0, stop_err=0.0)
    errs = [it["err_var"] for it in path]
    assert all(x >= -1e-12 for x in errs)                       # E_var >= E0
    assert all(b <= a + 1e-12 for a, b in zip(errs, errs[1:]))  # nested sets: non-increasing
    assert path[-1]["size"] == len(idx) and abs(errs[-1]) < 1e-12
    # the equal-size set is a prefix of the next main step (nested family), sizes exact
    for n in range(len(refs), len(idx) + 1):
        it = sci.cipsi_at(Hs, diag, path, n, E0, 1.25)
        assert it["size"] == n
        j = max(i for i, p in enumerate(path) if p["size"] <= n)
        assert set(path[j]["S"]).issubset(it["S"])
        if j + 1 < len(path) and n <= path[j + 1]["size"]:
            assert set(it["S"]).issubset(path[j + 1]["S"])


def test_size_to_reach_bisection():
    f = {n: 1.0 / n for n in range(1, 101)}
    assert sci.size_to_reach(f.__getitem__, 1, 100, 0.05) == 20
    assert sci.size_to_reach(f.__getitem__, 1, 100, 1e-3) is None


def test_fixed_batch_schedule_reproduces_package_cipsi_2x3():
    """Gate S1's skqd.controls.cipsi (batch 8) and the batch schedule here select the same set at 2x3 B=0."""
    _, H, idx, Hs, diag, E0, refs = _sector(3, 0)
    n = 160
    Bp = package_cipsi(H, idx[refs], n, batch=8)
    path = sci.cipsi_path(Hs, diag, refs, 1.0, E0, max_size=n, batch=8)
    Bm = idx[path[-1]["S"]]
    assert len(Bm) == n
    assert ritz(H, Bp).ER == pytest.approx(ritz(H, Bm).ER, abs=1e-10)
    assert path[-1]["err_var"] < 2e-3                           # gate S1 test_variational_and_certification bound
