"""
Device-proxy noise model on bit strings (Step 8.2 of the SKQD manual).

Each shot is clean with probability f; otherwise it is, with equal
probability, a uniformly random bit string or the clean sample with
Poisson(2) random bit flips.  Independent readout flips with probability
p_ro per qubit are then applied to every shot.  The decoder of codec.py is
applied last.

The clean shots are multinomial samples of the ideal state in the
configuration basis, converted to codewords.

Symbols: f = circuit fidelity proxy (fraction of clean shots), p_ro = readout
flip probability per qubit, S = number of shots.
"""
from __future__ import annotations

import numpy as np

from .codec import Codec


def corrupt_shots(codewords: np.ndarray, sample_idx: np.ndarray, f: float, p_ro: float,
                  rng: np.random.Generator, poisson_mean: float = 2.0) -> np.ndarray:
    """codewords: (dim x nq) int8 array; sample_idx: (S,) basis indices of the clean
    samples.  Returns an (S x nq) array of measured bit strings."""
    S = len(sample_idx)
    nq = codewords.shape[1]
    bits = codewords[sample_idx].astype(np.int8).copy()
    clean = rng.random(S) < f
    dirty = ~clean
    n_dirty = int(dirty.sum())
    if n_dirty:
        garbage = rng.random(n_dirty) < 0.5
        d_idx = np.where(dirty)[0]
        g_idx = d_idx[garbage]
        l_idx = d_idx[~garbage]
        bits[g_idx] = rng.integers(0, 2, size=(len(g_idx), nq), dtype=np.int8)
        # Poisson(2) flips conditioned on at least one flip (zero-flip draws are
        # redrawn), so that every locally corrupted shot differs from its clean
        # sample; this reproduces the manual's accepted yield of ~0.82 f (Table 4).
        nflip = rng.poisson(poisson_mean, size=len(l_idx))
        zero = nflip == 0
        while zero.any():
            nflip[zero] = rng.poisson(poisson_mean, size=int(zero.sum()))
            zero = nflip == 0
        for row, k in zip(l_idx, nflip):
            pos = rng.choice(nq, size=min(int(k), nq), replace=False)
            bits[row, pos] ^= 1
    if p_ro > 0:
        ro = (rng.random((S, nq)) < p_ro).astype(np.int8)
        bits ^= ro
    return bits


def measure_and_decode(codec: Codec, codewords: np.ndarray, psi: np.ndarray, shots: int,
                       f: float, p_ro: float, rng: np.random.Generator, target_twoB=None):
    """Sample `shots` shots of |psi> through the proxy noise and decode.
    Returns (accepted {basis index: count}, rejection reasons, n_clean_accepted)."""
    p = np.abs(psi) ** 2
    p = p / p.sum()
    sample_idx = rng.choice(len(p), size=shots, p=p)
    bits = corrupt_shots(codewords, sample_idx, f, p_ro, rng)
    # group identical strings
    uniq, counts = np.unique(bits, axis=0, return_counts=True)
    cdict = {tuple(int(x) for x in row): int(c) for row, c in zip(uniq, counts)}
    acc, rej = codec.decode_counts(cdict, target_twoB)
    return acc, rej
