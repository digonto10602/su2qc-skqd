import itertools

import numpy as np

from skqd.codec import Codec, Reject
from skqd.exact import Model


def test_round_trip_and_exhaustive_2x2():
    M = Model(2)
    C = Codec(M.basis)
    assert C.n_qubits == 12
    for k, b in enumerate(M.basis.labels):
        assert C.decode(C.encode(b))[0] == k
    acc = 0
    for bits in itertools.product((0, 1), repeat=12):
        try:
            C.decode(bits)
            acc += 1
        except Reject:
            pass
    assert acc == 82


def test_round_trip_2x3_and_random_acceptance():
    M = Model(3)
    C = Codec(M.basis)
    assert C.n_qubits == 20
    for k, b in enumerate(M.basis.labels):
        assert C.decode(C.encode(b))[0] == k
    rng = np.random.default_rng(0)
    acc = 0
    N = 20000
    for row in rng.integers(0, 2, size=(N, 20)):
        try:
            C.decode(tuple(int(x) for x in row))
            acc += 1
        except Reject:
            pass
    assert acc / N < 0.006  # ~0.16 % expected
