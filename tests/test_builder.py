import numpy as np

from skqd.basis import count_labels_without_intertwiner, enumerate_basis
from skqd.exact import Model
from skqd.lattice import Ladder
from skqd.vertex import kernel_dim


def test_vertex_tables():
    assert kernel_dim(((0.5, "out"), (0.5, "out"), (0.5, "in")), 1) == 2
    assert kernel_dim(((0.5, "out"), (0.5, "out")), 1) == 0
    assert kernel_dim(((0.5, "out"), (0.5, "out")), 1, True) == 2


def test_counts():
    for Lx, st, n, lab in ((2, (), 82, 82), (3, (), 1727, 1460), (2, (0, 2), 113, 82), (2, (0, 3), 112, 82)):
        B = enumerate_basis(Ladder(Lx, static_sites=st))
        assert B.dim == n
        assert count_labels_without_intertwiner(B) == lab


def test_2x2_spectrum_matches_manual():
    M = Model(2)
    H = M.H(4.0, 0.75).toarray()
    assert abs(H - H.conj().T).max() < 1e-12
    w0 = np.linalg.eigvalsh(H[np.ix_(M.basis.sector(0), M.basis.sector(0))])
    w1 = np.linalg.eigvalsh(H[np.ix_(M.basis.sector(2), M.basis.sector(2))])
    assert abs(w0[0] + 3.6408) < 5e-5 and abs(w0[1] + 0.9622) < 5e-5
    assert abs(w1[0] + 1.8616) < 5e-5 and abs(w1[1] + 1.8197) < 5e-5 and abs(w1[2] - 0.2082) < 5e-5
    assert abs(np.pi / (w0[-1] - w0[0]) - 0.245) < 5e-4


def test_2x3_references_match_manual():
    M = Model(3)
    r0 = M.reference(4.0, 0)
    r1 = M.reference(4.0, 2)
    assert r0.dim == 677 and r1.dim == 426
    assert abs(r0.E0 + 5.6026) < 5e-5 and abs(r0.energies[1] + 2.8886) < 5e-5
    assert abs(r1.E0 + 3.8261) < 5e-5
    assert abs(r0.dt - 0.156) < 5e-4
    assert (r0.support99, r0.support999) == (31, 86)


def test_static_potential():
    e0 = Model(3).reference(4.0, 0).E0
    v1 = Model(3, static_sites=(0, 2)).reference(4.0, 0).E0 - e0
    assert abs(v1 - 1.3872) < 2e-4
