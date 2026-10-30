"""
Classical selected configuration interaction (CIPSI type) in the gauge-invariant basis of one sector.

Selected CI chooses a subset S of basis states, diagonalises H inside span(S), and grows S by the
external states that matter most to the current variational state.  CIPSI ("configuration interaction
by perturbation with multiconfigurational zeroth-order wave functions selected by iterative process",
Huron, Malrieu, Rancurel, J. Chem. Phys. 58, 5745 (1973), doi:10.1063/1.1679199) ranks every external
state a (a not in S, <a|H|psi_S> != 0 structurally) by its Epstein-Nesbet second-order energy

    e_a = |<a|H|psi_S>|^2 / (E_S - H_aa),

and the second-order (PT2) estimate of the remaining correlation energy is E_PT2 = sum_a e_a, so that
E_S + E_PT2 approximates E_0 (it is not a bound).

Conventions:
  * all indices here are SECTOR-LOCAL positions 0..dim-1 of `Hs = H[sector_idx][:, sector_idx]`;
  * the variational state of S is the lowest eigenvector of Hs[S][:, S] (dense eigh up to
    DENSE_MAX states, Lanczos `eigsh(k=2, which="SA", tol=1e-12)` above);
  * ranking key: |e_a| / max_a |e_a| rounded to TIE_DECIMALS = 10 decimals, descending, ties by the
    sector-local index ascending (symmetry-equivalent states have equal e_a up to round-off, whose
    sign depends on the BLAS thread count; the rounding makes the order thread-independent);
  * growth: one step goes from |S| to target = min(dim, max(|S| + 1, ceil(growth |S|))) states by
    adding the top (target - |S|) external states of the ranking of psi_S.  When fewer external
    states are connected than needed, all connected states are added and the step is short.

Nesting property used by `cipsi_at`: the set of size n is the last main-path iterate S_j with
|S_j| <= n plus the top (n - |S_j|) of S_j's ranking, i.e. a prefix of the next main-path step (a
short step adds S_j's whole ranking, so for n beyond it the next iterate is the largest set <= n).  The
family {S(n)} is therefore nested for every n <= |S_last| (the last main iterate), and E_var(n) is
non-increasing there (Cauchy interlacing); `size_to_reach` is applied on that range.
"""
from __future__ import annotations

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

DENSE_MAX = 500        # dense eigh up to here; Lanczos above (agrees to ~1e-14, measured at 2x4 n = 500..2500)
TIE_DECIMALS = 10      # |e_a| / max|e_a| rounded to 1e-10 before ranking: round-off ties go by index


def lowest_pair(Hs: sp.csr_matrix, S, dense_max: int = DENSE_MAX):
    """Two lowest eigenvalues of Hs restricted to S and the lowest eigenvector (local to S)."""
    S = np.asarray(S, dtype=int)
    h = Hs[S][:, S]
    if len(S) <= dense_max:
        hd = h.toarray()
        w, v = np.linalg.eigh((hd + hd.conj().T) / 2)
        return w[:2].astype(float), v[:, 0]
    w, v = spl.eigsh(h, k=2, which="SA", tol=1e-12, v0=np.ones(len(S)))
    o = np.argsort(w)
    return w[o].astype(float), v[:, o[0]]


def pt2_ranking(Hs: sp.csr_matrix, diag: np.ndarray, S, c: np.ndarray, E: float) -> dict:
    """Epstein-Nesbet importance of every external state structurally connected to S.

    Returns the external indices ranked by |e_a| (descending, ties by index), e_a in that order,
    E_PT2 = sum e_a, and the number of external states with H_aa <= E (e_a >= 0, 'intruders').
    """
    S = np.asarray(S, dtype=int)
    dim = Hs.shape[0]
    inS = np.zeros(dim, dtype=bool)
    inS[S] = True
    cfull = np.zeros(dim, dtype=complex)
    cfull[S] = c
    v = Hs @ cfull                                   # <a|H|psi_S> for every a
    conn = np.unique(Hs[S].indices)                  # Hs Hermitian: rows of S = columns connected to S
    ext = conn[~inS[conn]]
    num = np.abs(v[ext]) ** 2
    den = E - diag[ext]
    if np.any(den == 0.0):
        raise ZeroDivisionError("E_S equals a diagonal element H_aa of a connected external state")
    e = num / den
    a = np.abs(e)
    scale = float(a.max()) if a.size else 1.0
    key = np.round(a / scale, TIE_DECIMALS) if scale > 0 else a      # ties within 1e-10 relative -> by index
    order = np.lexsort((ext, -key))
    return {"ext": ext[order], "e": e[order], "E_pt2": float(np.sum(e)),
            "n_connected": int(len(ext)), "n_intruders": int(np.sum(den > 0))}


def step_target(size: int, dim: int, growth: float, batch: int | None = None) -> int:
    """Next target size: geometric (ceil(growth |S|)) or, with `batch`, |S| + batch (the fixed-batch
    schedule of skqd.controls.cipsi, gate S1)."""
    if batch is not None:
        return int(min(dim, size + int(batch)))
    return int(min(dim, max(size + 1, math.ceil(growth * size - 1e-12))))


def evaluate(Hs, diag, S, E0=None, dense_max: int = DENSE_MAX) -> dict:
    """Variational energy, PT2 correction and the ranking of the external space of S."""
    S = np.asarray(sorted(set(int(x) for x in S)), dtype=int)
    w, c = lowest_pair(Hs, S, dense_max)
    rk = pt2_ranking(Hs, diag, S, c, float(w[0]))
    out = {"S": S, "size": int(len(S)), "E_var": float(w[0]),
           "E_var2": float(w[1]) if len(w) > 1 else None,
           "E_pt2": rk["E_pt2"], "E_var_plus_pt2": float(w[0] + rk["E_pt2"]),
           "n_connected": rk["n_connected"], "n_intruders": rk["n_intruders"],
           "c": c, "_rank": rk}
    if E0 is not None:
        out["err_var"] = float(w[0] - E0)
        out["err_pt2"] = float(w[0] + rk["E_pt2"] - E0)
    return out


def grow(S, rank: dict, target: int) -> np.ndarray:
    """S plus the top (target - |S|) external states of `rank` (all of them when fewer exist)."""
    S = np.asarray(S, dtype=int)
    add = rank["ext"][: max(0, target - len(S))]
    return np.union1d(S, add)


def cipsi_path(Hs, diag, refs, growth: float, E0=None, stop_err: float = 1e-10,
               max_size: int | None = None, dense_max: int = DENSE_MAX, batch: int | None = None) -> list:
    """Main CIPSI path from the reference states: a list of `evaluate` dicts, one per iterate.

    Stops when E_var - E0 <= stop_err (E0 given), when |S| = dim (or max_size), or when S has no
    connected external state left.
    """
    dim = Hs.shape[0]
    cap = dim if max_size is None else min(dim, int(max_size))
    S = np.asarray(sorted(set(int(r) for r in refs)), dtype=int)
    path = []
    while True:
        it = evaluate(Hs, diag, S, E0, dense_max)
        it["short_step"] = False
        if path:
            it["short_step"] = bool(it["size"] < path[-1]["_target"])
        path.append(it)
        done = (len(S) >= cap or it["n_connected"] == 0
                or (E0 is not None and it["err_var"] <= stop_err))
        if done:
            it["_target"] = None
            break
        it["_target"] = step_target(len(S), cap, growth, batch)
        S = grow(S, it["_rank"], it["_target"])
    return path


def cipsi_at(Hs, diag, path: list, n: int, E0=None, growth: float = 2.0,
             dense_max: int = DENSE_MAX, batch: int | None = None) -> dict:
    """The CIPSI set of exactly n states (module docstring): branch from the last iterate with
    |S_j| <= n, adding the top of its ranking; if the ranking holds fewer than n - |S_j| states, keep
    stepping (target min(n, ceil(growth |S|))) until n is reached."""
    n = int(n)
    dim = Hs.shape[0]
    if n > dim:
        raise ValueError(f"n = {n} exceeds the sector dimension {dim}")
    j = max(i for i, it in enumerate(path) if it["size"] <= n)
    it = path[j]
    steps = 0
    while it["size"] < n:
        if it["n_connected"] == 0:
            raise RuntimeError("the connected component of S is exhausted before n states")
        target = n if steps == 0 else min(n, step_target(it["size"], dim, growth, batch))
        it = evaluate(Hs, diag, grow(it["S"], it["_rank"], target), E0, dense_max)
        steps += 1
    it["branch_from_size"] = int(path[j]["size"])
    it["branch_steps"] = steps
    return it


def size_to_reach(energy_of_size, lo: int, hi: int, err_target: float) -> int | None:
    """Smallest n in [lo, hi] with energy_of_size(n) <= err_target, by bisection on a non-increasing
    function; None if not reached at hi."""
    if energy_of_size(hi) > err_target:
        return None
    if energy_of_size(lo) <= err_target:
        return lo
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if energy_of_size(mid) <= err_target:
            hi = mid
        else:
            lo = mid
    return hi
