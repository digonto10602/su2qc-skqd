"""
Classical-support controls at prescribed support size (Step 6 of the SKQD manual).

  (a) CIPSI selected CI: start from the references; iterate {diagonalize on B,
      score every Hamiltonian neighbour c not in B by |<c|H|psi_R>|^2 / (H_cc - E_R),
      add the top batch} until |B| reaches the target.
  (b) BFS neighbour growth, truncated at random when the next layer overshoots.
  (c) random configurations of the sector (references always included).
  (d) oracle: the top-|B| configurations by exact ground-state weight (simulator only).
  (e) ML-alone: the top-|B| configurations by a learned score (ml.py).
  (f) device-seeded CIPSI: CIPSI growth starting from a device support.

All functions return sorted arrays of full-basis indices of exactly the target size
(when the sector allows it).

Symbols: B = support, N(B) = Hamiltonian neighbours, psi_R = Ritz vector,
E_R = Ritz value, H_cc = diagonal element.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from .hamiltonian import neighbours
from .skqd import ritz


def cipsi(H: sp.csr_matrix, B0, target: int, batch: int = 8) -> np.ndarray:
    B = np.asarray(sorted(set(int(b) for b in B0)))
    diag = H.diagonal().real
    while len(B) < target:
        res = ritz(H, B)
        psi = res.full_vector(H.shape[0])
        N = neighbours(H, B)
        if len(N) == 0:
            break
        Hpsi = H @ psi
        # Epstein-Nesbet second-order importance |<c|H|psi>|^2 / (H_cc - E_R); the denominator is positive
        # for the ground-state Ritz value in all cases met here, and its magnitude is used (with a floor)
        # so that a candidate below E_R is scored by |H_cc - E_R| rather than silently promoted
        score = np.abs(Hpsi[N]) ** 2 / np.maximum(np.abs(diag[N] - res.ER), 1e-12)
        k = min(batch, target - len(B), len(N))
        top = N[np.argsort(score)[::-1][:k]]
        B = np.union1d(B, top)
    return B


def bfs(H: sp.csr_matrix, B0, target: int, rng: np.random.Generator) -> np.ndarray:
    B = np.asarray(sorted(set(int(b) for b in B0)))
    while len(B) < target:
        N = neighbours(H, B)
        if len(N) == 0:
            break
        need = target - len(B)
        if len(N) > need:
            N = rng.choice(N, size=need, replace=False)
        B = np.union1d(B, N)
    return B


def random_support(sector_idx: np.ndarray, B0, target: int, rng: np.random.Generator) -> np.ndarray:
    B = np.asarray(sorted(set(int(b) for b in B0)))
    rest = np.setdiff1d(sector_idx, B)
    need = min(target - len(B), len(rest))
    if need > 0:
        B = np.union1d(B, rng.choice(rest, size=need, replace=False))
    return B


def oracle(prob_full: np.ndarray, sector_idx: np.ndarray, target: int) -> np.ndarray:
    order = sector_idx[np.argsort(prob_full[sector_idx])[::-1]]
    return np.sort(order[:target])


def top_by_score(score_full: np.ndarray, sector_idx: np.ndarray, B0, target: int) -> np.ndarray:
    """ML-alone proposal: references plus the top configurations by score."""
    B = np.asarray(sorted(set(int(b) for b in B0)))
    order = sector_idx[np.argsort(score_full[sector_idx])[::-1]]
    for c in order:
        if len(B) >= target:
            break
        if c not in B:
            B = np.append(B, c)
    return np.sort(B)


def top_by_count(acc: dict, B0, target: int) -> np.ndarray:
    """Device support truncated to the target size: references plus the most
    frequently observed configurations."""
    B = list(sorted(set(int(b) for b in B0)))
    for k, _ in sorted(acc.items(), key=lambda kv: -kv[1]):
        if len(B) >= target:
            break
        if k not in B:
            B.append(int(k))
    return np.array(sorted(B))
