#!/usr/bin/env python3
"""Planner prototype (prompts/27): the only "amplifier" that exists for sampling is counting
statistics -- signal counts grow as N f p, uniform-noise counts per state as N a / 2^20.
This runs the manual's Step-8.2 proxy emulator (gate_S1.emulate) at 2x3, B = 0, for clean
fractions f from 0.17 (Helios gate-only estimate) down to 1e-3, and asks, per budget:
  * |B_all|, |B_sig| (counts above the one-sided 3-sigma Poisson line of UNIFORM noise),
  * recall of the 99.9 % support (86 states) and the 99 % support (31 states) by B_sig,
  * E_R(B_sig) - E0, and the random-equal-size baseline percentile (controls.random_support),
  * CIPSI and BFS at |B_sig| (controls.cipsi / controls.bfs).
Everything here is a PROXY estimate (the Step-8.2 noise model, not a device model); the
plan's simulator stage repeats it with the Aer/CUDA-Q device model on Perlmutter.
Output: scratch/planner/lowf_counting_amplifier_20261002.json
"""
import json
import os
import sys
import time

import numpy as np
from scipy.stats import poisson

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from gate_S1 import emulate  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.controls import bfs, cipsi, random_support  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import basis_vector, coarse_states, references, term_groups  # noqa: E402
from skqd.skqd import exact_support, ritz, support_metrics  # noqa: E402


def sig_threshold(mu, alpha=0.00135):
    """Smallest count c with P(Poisson(mu) >= c) < alpha (one-sided 3 sigma)."""
    c = 0
    while poisson.sf(c - 1, mu) >= alpha:
        c += 1
    return c


def main():
    t0 = time.time()
    g2 = 4.0
    m = mass_default(g2)
    M = Model(3)
    H = M.H(g2)
    codec = Codec(M.basis)
    cw = codec.all_codewords()
    nq = cw.shape[1]
    groups = term_groups(M.terms, g2, m)
    twoB = 0
    r = M.reference(g2, twoB, k=4)
    refs = references(M.basis, twoB)
    p = np.zeros(M.basis.dim)
    p[r.indices] = np.abs(r.ground) ** 2
    S999 = exact_support(p, 1e-3)
    S99 = exact_support(p, 1e-2)
    sector_idx = np.asarray(r.indices)
    sts = [s for rr in refs for s in coarse_states(groups, basis_vector(M.basis.dim, rr), r.dt, 4)[1:]]
    ncirc = len(sts)
    E0 = float(r.E0)
    cells = []
    for f, N_total in [(0.17, 2e5), (0.17, 1e6), (0.05, 1e6), (0.01, 1e6), (0.01, 4e6),
                       (0.003, 4e6), (0.001, 4e6)]:
        shots = int(round(N_total / ncirc))
        rng = np.random.default_rng(20261002)
        acc, rej, B_all, y = emulate(codec, cw, H, sts, shots, f, rng, twoB, refs)
        N = shots * ncirc
        # uniform-noise expectation per codeword: garbage shots x 2^-nq (proxy: half the dirty shots)
        mu = N * (1.0 - f) * 0.5 / 2 ** nq
        c_sig = sig_threshold(mu)
        B_sig = np.array(sorted(set(k for k, c in acc.items() if c >= c_sig) | set(refs)))
        res_all = ritz(H, B_all)
        res_sig = ritz(H, B_sig)
        met_all = support_metrics(B_all, p, 1e-3)
        met_sig = support_metrics(B_sig, p, 1e-3)
        rec99_sig = len(set(B_sig) & set(S99)) / len(S99)
        # random equal-size baseline (100 seeds), CIPSI and BFS at |B_sig|
        size = len(B_sig)
        rnd = []
        for s in range(100):
            Br = random_support(sector_idx, refs, size, np.random.default_rng(1000 + s))
            rnd.append(ritz(H, Br).ER)
        rnd = np.array(rnd)
        pct = float(np.mean(rnd <= res_sig.ER + 1e-12) * 100)
        e_cipsi = float(ritz(H, cipsi(H, refs, size)).ER) if size > len(refs) else float("nan")
        e_bfs = float(ritz(H, bfs(H, refs, size, np.random.default_rng(7))).ER) if size > len(refs) else float("nan")
        cell = dict(f=f, N_total=N, circuits=ncirc, shots_per_circuit=shots, accepted=int(sum(acc.values())),
                    yield_=y, mu_uniform_per_state=mu, c_sig=c_sig,
                    B_all=int(len(B_all)), B_sig=int(size),
                    err_all=float(res_all.ER - E0), err_sig=float(res_sig.ER - E0),
                    recall999_all=met_all["recall"], recall999_sig=met_sig["recall"], recall99_sig=rec99_sig,
                    fp_all=met_all.get("false_positives", None), fp_sig=met_sig.get("false_positives", None),
                    random_equal_size_mean_err=float(rnd.mean() - E0), random_equal_size_min_err=float(rnd.min() - E0),
                    percentile_of_sig_in_random=pct, cipsi_err_at_size=e_cipsi - E0, bfs_err_at_size=e_bfs - E0,
                    t_s=time.time() - t0)
        cells.append(cell)
        print(json.dumps(cell))
        sys.stdout.flush()
    out = dict(lattice="2x3", sector="B=0", g2=g2, m=m, E0=E0, dim=int(len(sector_idx)), n_qubits=int(nq),
               support999=int(len(S999)), support99=int(len(S99)), seed=20261002,
               noise_model="manual Step 8.2 proxy (skqd.noise.corrupt_shots), p_ro = gate_S1.P_RO",
               cells=cells, runtime_s=time.time() - t0)
    with open(os.path.join(ROOT, "scratch", "planner", "lowf_counting_amplifier_20261002.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
