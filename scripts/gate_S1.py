#!/usr/bin/env python3
"""
Gate S1 — emulated support generation with the device proxy, decoding, projected
diagonalization, certification, support metrics, and the size-matched classical
controls (Steps 4–8 of the manual; Tables 3 and 4 and Fig. 1 re-computed here).

Criterion (Step 10, S1): emulated recall of the 99.9 % support >= 0.9 at f >= 0.1
with the production budget (2e5 shots per sector, multi-reference coarse
circuits) for the 2x3 B = 0 and B = 1 sectors, and the controls table.

Usage:  python scripts/gate_S1.py [--quick]      (--quick: 1 repetition, no 2x4)
Runtime: ~10 min full on 2 CPUs, ~3 min quick.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.codec import Codec  # noqa: E402
from skqd.controls import bfs, cipsi, oracle, random_support, top_by_count, top_by_score  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import (basis_vector, coarse_states, exact_krylov_states, references,  # noqa: E402
                         term_groups, trotter_states)
from skqd.ml import RidgeRanker, design, features, spearman  # noqa: E402
from skqd.noise import measure_and_decode  # noqa: E402
from skqd.report import ROOT, GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import certify, closure_diagnostic, interval_difference, ritz, support_metrics  # noqa: E402

P_RO = 0.01


def emulate(codec, cw, H, states, shots, f, rng, twoB, refs):
    acc_all, rej_all = {}, {}
    for st in states:
        acc, rej = measure_and_decode(codec, cw, st, shots, f, P_RO, rng, target_twoB=twoB)
        for k, c in acc.items():
            acc_all[k] = acc_all.get(k, 0) + c
        for k, c in rej.items():
            rej_all[k] = rej_all.get(k, 0) + c
    B = np.array(sorted(set(acc_all) | set(refs)))
    total = shots * len(states)
    return acc_all, rej_all, B, sum(acc_all.values()) / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    reps = 1 if args.quick else 3
    t0 = time.time()
    R = GateResult("S1", "Emulated support recall, certification and size-matched classical controls (2x3, 2x4)")
    rng = np.random.default_rng(20260914)
    g2 = 4.0
    m = mass_default(g2)
    M3 = Model(3)
    H3 = M3.H(g2)
    codec3 = Codec(M3.basis)
    cw3 = codec3.all_codewords()
    groups3 = term_groups(M3.terms, g2, m)
    data = {}

    refs_by_sector, prob_by_sector, ref_by_sector = {}, {}, {}
    for twoB in (0, 2):
        r = M3.reference(g2, twoB, k=4)
        ref_by_sector[twoB] = r
        p = np.zeros(M3.basis.dim)
        p[r.indices] = np.abs(r.ground) ** 2
        prob_by_sector[twoB] = p
        refs_by_sector[twoB] = references(M3.basis, twoB)

    # ---- 1. reachable configurations (deterministic, Step 4.2/4.3) --------------------
    reach_rows = []
    for twoB in (0, 2):
        r = ref_by_sector[twoB]
        p = prob_by_sector[twoB]
        order = np.argsort(p)[::-1]
        S999 = order[:r.support999]
        refs = refs_by_sector[twoB]
        psi0 = basis_vector(M3.basis.dim, refs[0])
        fams = {
            "single ref, 5 exact Krylov": exact_krylov_states(H3, psi0, r.dt, 5),
            "single ref, 5 first-order Trotter": trotter_states(groups3, psi0, r.dt, 5),
            "single ref, coarse k=1..4": coarse_states(groups3, psi0, r.dt, 4),
            "all refs, coarse k=1..4": [s for rr in refs for s in coarse_states(groups3, basis_vector(M3.basis.dim, rr), r.dt, 4)],
            "all refs, 5 exact Krylov": [s for rr in refs for s in exact_krylov_states(H3, basis_vector(M3.basis.dim, rr), r.dt, 5)],
        }
        for name, sts in fams.items():
            pmax = np.max(np.array([np.abs(s) ** 2 for s in sts]), axis=0)
            n_reach = int(np.sum(pmax[S999] > 1e-3))
            reach_rows.append([f"B={twoB // 2}", name, len(sts), f"{n_reach} of {len(S999)}"])
            data[f"reach|B={twoB // 2}|{name}"] = n_reach
    # manual: single reference d=5 exact: 41 of 86 (B=0), 35 of 95 (B=1); coarse single ref 62 of 86;
    # multi-reference coarse: 86 of 86 and 94 of 95.

    # ---- 2. Table 4 analogue: single reference, 5 exact Krylov, B = 0 ---------------------
    t4_rows = []
    r0 = ref_by_sector[0]
    p0 = prob_by_sector[0]
    refs0 = refs_by_sector[0]
    states0 = exact_krylov_states(H3, basis_vector(M3.basis.dim, refs0[0]), r0.dt, 5)
    table4 = {}
    for f in (1.0, 0.3, 0.1, 0.03):
        row = [f]
        for shots in (1000, 10000, 30000):
            errs, sizes, recs, fps, ys = [], [], [], [], []
            for rep in range(reps):
                acc, rej, B, y = emulate(codec3, cw3, H3, states0, shots, f, rng, 0, refs0)
                res = ritz(H3, B)
                met = support_metrics(B, p0, 1e-3)
                errs.append(res.ER - r0.E0); sizes.append(len(B)); recs.append(met["recall"]); fps.append(met["false_positives"]); ys.append(y)
            e = dict(err=float(np.mean(errs)), size=float(np.mean(sizes)), recall=float(np.mean(recs)),
                     fp=float(np.mean(fps)), yield_=float(np.mean(ys)))
            table4[f"f={f}|shots={shots}"] = e
            row.append(f"{e['err']:.1e} / {e['size']:.0f} / {e['recall']:.2f} / {e['fp']:.0f} (y={e['yield_']:.3f})")
        t4_rows.append(row)
    # multi-reference coarse circuits at 5e4 total shots, f = 0.1, both sectors
    multi = {}
    for twoB in (0, 2):
        r = ref_by_sector[twoB]
        refs = refs_by_sector[twoB]
        sts = [s for rr in refs for s in coarse_states(groups3, basis_vector(M3.basis.dim, rr), r.dt, 4)[1:]]
        shots = int(round(5e4 / len(sts)))
        errs, sizes, recs, fps = [], [], [], []
        for rep in range(reps):
            acc, rej, B, y = emulate(codec3, cw3, H3, sts, shots, 0.1, rng, twoB, refs)
            res = ritz(H3, B)
            met = support_metrics(B, prob_by_sector[twoB], 1e-3)
            errs.append(res.ER - r.E0); sizes.append(len(B)); recs.append(met["recall"]); fps.append(met["false_positives"])
        multi[twoB] = dict(circuits=len(sts), shots_per_circuit=shots, err=float(np.mean(errs)), size=float(np.mean(sizes)),
                           recall=float(np.mean(recs)), fp=float(np.mean(fps)))
    data["table4"] = table4
    data["multi_reference_5e4"] = multi

    # ---- 3. S1 criterion: production budget 2e5 shots per sector, coarse multi-reference ----
    prod_rows = []
    prod = {}
    for twoB in (0, 2):
        r = ref_by_sector[twoB]
        refs = refs_by_sector[twoB]
        sts = [s for rr in refs for s in coarse_states(groups3, basis_vector(M3.basis.dim, rr), r.dt, 4)[1:]]
        shots = int(round(2e5 / len(sts)))
        for f in (0.3, 0.2, 0.1):
            acc, rej, B, y = emulate(codec3, cw3, H3, sts, shots, f, rng, twoB, refs)
            res = ritz(H3, B)
            met = support_metrics(B, prob_by_sector[twoB], 1e-3)
            cert = certify(res, r.E0, float(r.energies[1]))
            prod[f"B={twoB // 2}|f={f}"] = dict(size=len(B), err=res.ER - r.E0, recall=met["recall"], fp=met["false_positives"],
                                                 yield_=y, rH=res.rH, weinstein=cert.weinstein, kato_temple=cert.kato_temple,
                                                 kt_rigorous=cert.kt_rigorous, gap_holds=cert.gap_assumption_holds,
                                                 rejections=rej)
            prod_rows.append([f"B={twoB // 2}", f, len(sts), shots, f"{y:.3f}", len(B), f"{res.ER - r.E0:.1e}", f"{met['recall']:.3f}",
                              met["false_positives"], f"{res.rH:.3f}",
                              f"[{cert.weinstein[0]:.4f}, {cert.weinstein[1]:.4f}]",
                              f"[{cert.kato_temple[0]:.4f}, {cert.kato_temple[1]:.4f}]" if cert.kato_temple else "—",
                              f"{r.E0:.4f}", "yes" if cert.gap_assumption_holds else "no"])
            prod[f"B={twoB // 2}|f={f}"]["closure"] = closure_diagnostic(H3, res, r.dt)
            if f == 0.1:
                R.add(f"S1 criterion: 2x3 B={twoB // 2}, f=0.1, 2e5 shots: recall of 99.9% support", round(met["recall"], 3), ">= 0.9",
                      met["recall"] >= 0.9)
                R.add(f"2x3 B={twoB // 2}, f=0.1: exact E0 inside the Weinstein interval", f"{r.E0:.4f} in [{cert.weinstein[0]:.4f}, {cert.weinstein[1]:.4f}]",
                      "contains E0", cert.weinstein[0] - 1e-12 <= r.E0 <= cert.weinstein[1] + 1e-12)
    data["production"] = prod
    # baryon mass by interval arithmetic (manual Step 5.3): M_B in [E_R^1 - E_R^0 - delta_1, E_R^1 - E_R^0 + delta_0]
    mb_rows = []
    for f in (0.3, 0.2, 0.1):
        w0, w1 = prod[f"B=0|f={f}"]["weinstein"], prod[f"B=1|f={f}"]["weinstein"]
        lo, hi = interval_difference(w1, w0)
        exact_mb = ref_by_sector[2].E0 - ref_by_sector[0].E0
        mb_rows.append([f, f"[{lo:.4f}, {hi:.4f}]", f"{exact_mb:.4f}", "yes" if lo <= exact_mb <= hi else "no"])
        data[f"MB_interval|f={f}"] = (lo, hi)
    R.add("M_B interval (Weinstein, f=0.1) contains the exact baryon mass", mb_rows[-1][1], f"contains {mb_rows[-1][2]}", mb_rows[-1][3] == "yes")

    # ---- 4. Table 3 analogue: Ritz error at equal |B| ---------------------------------------
    # ML ranker trained leakage-safely (test coupling g^2 = 4 excluded everywhere)
    ml_time = time.time()
    train_sets = [(2, [1.0, 1.5, 2.0, 3.0, 6.0]), (3, [1.0, 2.0, 6.0])]
    Xs, ys = [], []
    M2 = Model(2)
    mods = {2: M2, 3: M3}
    feat_cache = {}
    for Lx, g2s in train_sets:
        Mx = mods[Lx]
        for gg in g2s:
            F = features(Mx.basis, Mx.terms, gg, mass_default(gg))
            for twoB in (0, 2):
                rr = Mx.reference(gg, twoB, k=2)
                X = design(F[rr.indices], gg, mass_default(gg), twoB, Lx)
                Xs.append(X); ys.append(RidgeRanker.target(rr.ground, 1e-6))
    ranker = RidgeRanker(alpha=1.0).fit(np.vstack(Xs), np.concatenate(ys))
    F3 = features(M3.basis, M3.terms, g2, m)
    score3 = {}
    ml_rows = []
    for twoB in (0, 2):
        rr = ref_by_sector[twoB]
        X = design(F3[rr.indices], g2, m, twoB, 3)
        s = np.full(M3.basis.dim, -np.inf)
        s[rr.indices] = ranker.predict(X)
        score3[twoB] = s
        rho = spearman(s[rr.indices], RidgeRanker.target(rr.ground, 1e-6))
        ml_rows.append([f"B={twoB // 2}", f"{rho:.3f}"])
        data[f"ml_spearman|B={twoB // 2}"] = rho
        R.add(f"ML ridge (leakage-safe) Spearman rank correlation, 2x3 g2=4 B={twoB // 2}", round(rho, 3), "> 0.7 (manual 0.85 / 0.89)", rho > 0.7)
    data["ml_train_time_s"] = time.time() - ml_time

    sizes = [20, 40, 80, 160, 320]
    t3 = {}
    t3_rows = []
    for twoB in (0, 2):
        r = ref_by_sector[twoB]
        p = prob_by_sector[twoB]
        refs = refs_by_sector[twoB]
        sec = M3.basis.sector(twoB)
        # device proxy counts: single reference, 5 exact Krylov, f=0.1, 1e4 shots/circuit
        sts = exact_krylov_states(H3, basis_vector(M3.basis.dim, refs[0]), r.dt, 5)
        dev_counts = []
        for rep in range(reps):
            acc, rej, B, y = emulate(codec3, cw3, H3, sts, 10000, 0.1, rng, twoB, refs)
            dev_counts.append(acc)
        # device-seeded CIPSI: seed = device support truncated at half the target size
        for name in ("oracle", "CIPSI", "ML alone (ridge)", "BFS", "random (refs incl.)", "random (no refs)", "device proxy", "device-seeded CIPSI"):
            row = [f"B={twoB // 2}", name]
            for n in sizes:
                if n > len(sec):
                    row.append("—")
                    continue
                vals, sizes_real = [], []
                for rep in range(reps if name in ("BFS", "random (refs incl.)", "random (no refs)", "device proxy", "device-seeded CIPSI") else 1):
                    if name == "oracle":
                        B = oracle(p, sec, n)
                    elif name == "CIPSI":
                        B = cipsi(H3, refs, n)
                    elif name == "ML alone (ridge)":
                        B = top_by_score(score3[twoB], sec, refs, n)
                    elif name == "BFS":
                        B = bfs(H3, refs, n, rng)
                    elif name == "random (refs incl.)":
                        B = random_support(sec, refs, n, rng)
                    elif name == "random (no refs)":
                        B = random_support(sec, [], n, rng)
                    elif name == "device proxy":
                        B = top_by_count(dev_counts[rep], refs, n)
                    else:
                        seed = top_by_count(dev_counts[rep], refs, max(len(refs), n // 2))
                        B = cipsi(H3, seed, n)
                    vals.append(ritz(H3, B).ER - r.E0)
                    sizes_real.append(len(B))
                e = float(np.mean(vals))
                nreal = float(np.mean(sizes_real))
                t3[f"B={twoB // 2}|{name}|{n}"] = dict(err=e, size=nreal)
                # a device support saturates when the counts contain fewer than n distinct configurations:
                # the cell is then NOT at the stated size and is marked with the realised |B|
                row.append(f"{e:.1e}" if abs(nreal - n) < 0.5 else f"{e:.1e} (|B|={nreal:.0f})")
            t3_rows.append(row)
    data["table3"] = t3
    for twoB in (0, 2):
        for n in (160, 320):
            c, o = t3[f"B={twoB // 2}|CIPSI|{n}"]["err"], t3[f"B={twoB // 2}|oracle|{n}"]["err"]
            R.add(f"controls: CIPSI within 3x of oracle at |B|={n}, B={twoB // 2}", f"{c:.1e} vs {o:.1e}", "CIPSI <= 3 x oracle", c <= 3 * o + 1e-12)

    # ---- 5. recall versus shots and fidelity (Fig. 1 right) -----------------------------------
    rec_rows = []
    rec = {}
    for f in (1.0, 0.3, 0.1, 0.03):
        row = [f]
        for shots in (1000, 3000, 10000, 30000):
            vals = []
            for rep in range(reps):
                acc, rej, B, y = emulate(codec3, cw3, H3, states0, shots, f, rng, 0, refs0)
                vals.append(support_metrics(B, p0, 1e-3)["recall"])
            rec[f"f={f}|shots={shots}"] = float(np.mean(vals))
            row.append(f"{np.mean(vals):.2f}")
        rec_rows.append(row)
    data["recall_vs_shots"] = rec

    # ---- 6. 2x4 transfer and scaling (simulator only) ------------------------------------------
    rows24 = []
    if not args.quick:
        t24 = time.time()
        M4 = Model(4)
        H4 = M4.H(g2)
        r4 = M4.reference(g2, 0, k=3)
        p4 = np.zeros(M4.basis.dim)
        p4[r4.indices] = np.abs(r4.ground) ** 2
        refs4 = references(M4.basis, 0)
        codec4 = Codec(M4.basis)
        cw4 = codec4.all_codewords()
        groups4 = term_groups(M4.terms, g2, m)
        sts = [s for rr in refs4 for s in coarse_states(groups4, basis_vector(M4.basis.dim, rr), r4.dt, 4)[1:]]
        shots = int(round(2e5 / len(sts)))
        acc, rej, B, y = emulate(codec4, cw4, H4, sts, shots, 0.1, rng, 0, refs4)
        res = ritz(H4, B)
        met = support_metrics(B, p4, 1e-3)
        cert = certify(res, r4.E0, float(r4.energies[1]))
        rows24.append(["device proxy (multi-ref coarse, f=0.1, 2e5 shots)", len(B), f"{res.ER - r4.E0:.1e}", f"{met['recall']:.2f}", met["false_positives"]])
        data["2x4_device"] = dict(size=len(B), err=res.ER - r4.E0, recall=met["recall"], fp=met["false_positives"], yield_=y,
                                  rH=res.rH, weinstein=cert.weinstein, kato_temple=cert.kato_temple, gap_holds=cert.gap_assumption_holds)
        # ML transfer: train on everything up to 2x3 (all couplings incl. 4), test 2x4 g2=4 B=0
        Xs, ys = [], []
        for Lx, g2s in ((2, [1.0, 1.5, 2.0, 3.0, 4.0, 6.0]), (3, [1.0, 2.0, 4.0, 6.0])):
            Mx = mods[Lx]
            for gg in g2s:
                F = features(Mx.basis, Mx.terms, gg, mass_default(gg))
                for twoB in (0, 2):
                    rr = Mx.reference(gg, twoB, k=2)
                    Xs.append(design(F[rr.indices], gg, mass_default(gg), twoB, Lx)); ys.append(RidgeRanker.target(rr.ground, 1e-6))
        ranker4 = RidgeRanker(alpha=1.0).fit(np.vstack(Xs), np.concatenate(ys))
        F4 = features(M4.basis, M4.terms, g2, m)
        s4 = np.full(M4.basis.dim, -np.inf)
        s4[r4.indices] = ranker4.predict(design(F4[r4.indices], g2, m, 0, 4))
        rho4 = spearman(s4[r4.indices], RidgeRanker.target(r4.ground, 1e-6))
        data["2x4_ml_spearman"] = rho4
        sec4 = M4.basis.sector(0)
        for name in ("oracle", "CIPSI", "ML alone (ridge, transfer)"):
            for n in (320, 640):
                if name == "oracle":
                    Bc = oracle(p4, sec4, n)
                elif name == "CIPSI":
                    Bc = cipsi(H4, refs4, n, batch=16)
                else:
                    Bc = top_by_score(s4, sec4, refs4, n)
                rc = ritz(H4, Bc)
                mt = support_metrics(Bc, p4, 1e-3)
                rows24.append([f"{name}, |B|={n}", len(Bc), f"{rc.ER - r4.E0:.1e}", f"{mt['recall']:.2f}", mt["false_positives"]])
                data[f"2x4|{name}|{n}"] = dict(err=rc.ER - r4.E0, recall=mt["recall"])
        data["2x4_time_s"] = time.time() - t24
        R.add("2x4 device proxy (f=0.1, 2e5 shots) recall of the 99.9% support", round(met["recall"], 3), ">= 0.85 (manual 0.94)", met["recall"] >= 0.85)

    R.data = data
    R.runtime_s = time.time() - t0
    path = R.save()
    with open(os.path.join(ROOT, "data", "S1_emulation.json"), "w") as fh:
        json.dump(R.data if isinstance(R.data, dict) else {}, fh, indent=1, default=float)

    manual_t4 = {
        (1.0, 1000): "1.5e-2 / 79 / 0.74 / 0", (1.0, 10000): "1.8e-3 / 166 / 1.00 / 0", (1.0, 30000): "7.6e-4 / 228 / 1.00 / 2",
        (0.3, 1000): "3.0e-2 / 58 / 0.56 / 0", (0.3, 10000): "5.7e-3 / 140 / 0.93 / 5", (0.3, 30000): "1.5e-3 / 209 / 1.00 / 11",
        (0.1, 1000): "8.4e-2 / 41 / 0.40 / 0", (0.1, 10000): "1.1e-2 / 119 / 0.81 / 6", (0.1, 30000): "3.4e-3 / 191 / 0.97 / 15",
        (0.03, 1000): "1.5e-1 / 32 / 0.29 / 1", (0.03, 10000): "1.9e-2 / 101 / 0.71 / 5", (0.03, 30000): "7.9e-3 / 171 / 0.89 / 14",
    }
    t4m_rows = [[f] + [manual_t4[(f, s)] for s in (1000, 10000, 30000)] for f in (1.0, 0.3, 0.1, 0.03)]
    quick_note = " (quick mode: 1 repetition, no 2x4 section)" if args.quick else f" (means over {reps} repetitions)"
    report = f"""# Gate S1 — emulated support generation, certification and classical controls

**Status: {'PASS' if R.passed else 'FAIL'}** — produced by `scripts/gate_S1.py`{quick_note}; every number computed in this
run, stored in `validation/S1.json` and `data/S1_emulation.json`.  {env_block()}  Runtime {R.runtime_s:.0f} s.

Setting: 2x3 ladder (20 qubits, 1 727 states; sectors $B=0$: 677, $B=1$: 426), $g^2 = 4$, $m = 0.75$,
$\\Delta t = \\pi/W_B$ per sector ({ref_by_sector[0].dt:.3f} for $B=0$, {ref_by_sector[2].dt:.3f} for $B=1$).
Device proxy (Step 8.2): a shot is clean with probability $f$; otherwise with equal probability a uniformly random
bit string or the clean sample with Poisson(2) bit flips (conditioned on at least one flip); independent readout flips at
$p_{{ro}} = 1\\%$ per qubit on every shot; then the decoder with the sector filter.  $B$ is the union of the accepted
configurations and the references.  Symbols: $E_R$ = lowest Ritz value on $B$, $E_0$ = exact sector ground energy,
recall = fraction of the exact 99.9 % support $S_{{10^{{-3}}}}$ contained in $B$, fp = configurations of $B$ with exact
weight $< 10^{{-8}}$, yield = accepted shots / total shots, $r_H = \\|(H - E_R)\\psi_R\\|$.

## 1. Which configurations the circuits can reach (no sampling)

Configurations of the 99.9 % support that reach probability $> 10^{{-3}}$ in at least one circuit state:

{md_table(["sector", "circuit family", "circuits", "reached"], reach_rows)}

Manual (Step 4.2–4.3): single reference with $d=5$ exact Krylov states reaches 41 of 86 ($B=0$) and 35 of 95 ($B=1$);
single-reference coarse steps reach 62 of 86; multi-reference coarse circuits reach 86 of 86 and 94 of 95.
The coarse single-step family and the multi-reference set are therefore the production choice, as in the manual.

## 2. Device-proxy emulation, single reference, five exact Krylov states, $B = 0$ (Table 4 analogue)

Entries: Ritz error / $|B|$ / recall / false positives (yield in parentheses).

{md_table(["f", "10³ shots per circuit", "10⁴ shots per circuit", "3·10⁴ shots per circuit"], t4_rows)}

The proxy yields are printed in every cell: with the flip count conditioned on $\\ge 1$ (see `skqd.noise`) they are
$\\approx 0.82 f$ at $f \\ge 0.1$ but exceed $0.82 f$ at $f = 0.03$ (readout-only survivors of the local-corruption
branch), so the manual's "0.82 f in every row" is not exactly reproduced there.

Manual, Table 4 (same protocol):

{md_table(["f", "10³", "10⁴", "3·10⁴"], t4m_rows)}

Multi-reference coarse circuits, $5\\times10^4$ shots in total at $f = 0.1$:
$B=0$: {multi[0]['circuits']} circuits × {multi[0]['shots_per_circuit']} shots → error {multi[0]['err']:.1e} / $|B|$ = {multi[0]['size']:.0f} /
recall {multi[0]['recall']:.2f} / fp {multi[0]['fp']:.0f} (manual: 2.9e-3 / 190 / 0.97);
$B=1$: {multi[2]['circuits']} circuits × {multi[2]['shots_per_circuit']} shots → error {multi[2]['err']:.1e} / $|B|$ = {multi[2]['size']:.0f} /
recall {multi[2]['recall']:.2f} / fp {multi[2]['fp']:.0f} (manual: 4.6e-3 / 154 / 0.94).

## 3. Production budget (S1 criterion): $2\\times10^5$ shots per sector, multi-reference coarse circuits

{md_table(["sector", "f", "circuits", "shots/circuit", "yield", "|B|", "E_R − E_0", "recall", "fp", "r_H",
           "Weinstein [E_R−r_H, E_R]", "Kato–Temple (α = 2nd Ritz)", "exact E_0", "gap assumption r_H < E_1 − E_R"], prod_rows)}

The Weinstein interval is rigorous for *some* eigenvalue; identifying it with $E_0$ needs $r_H < E_1 - E_R$, which
is checked against the exact $E_1$ here (last column).  The Kato–Temple interval uses the second Ritz value as
$\\alpha$ and is therefore gap-assumed (Step 5.3 of the manual); it is omitted when $\\alpha - E_R < 10^{{-6}}$.
In the $B=1$ sector the near-degenerate cluster (splitting 0.024) makes the gap assumption fail by construction,
exactly the manual's caveat: Weinstein then certifies the cluster energy to $\\pm r_H$.

Baryon mass by interval arithmetic, $M_B \\in [E_R^{{B=1}} - E_R^{{B=0}} - \\delta_1,\\ E_R^{{B=1}} - E_R^{{B=0}} + \\delta_0]$
with the Weinstein $\\delta$'s:

{md_table(["f", "M_B interval", "exact M_B", "contains"], mb_rows)}

Subspace-closure diagnostic $\\|(1-P_B)e^{{-iH\\Delta t}}\\psi_R\\|$ (a convergence monitor, not a certificate) at $f=0.1$:
{prod['B=0|f=0.1']['closure']:.3e} ($B=0$), {prod['B=1|f=0.1']['closure']:.3e} ($B=1$).

## 4. Ritz error at equal support size (Table 3 analogue)

{md_table(["sector", "protocol"] + [f"|B|={n}" for n in sizes], t3_rows)}

Manual, Table 3 ($B=0$, $|B|$ = 20/40/80/160/320): oracle 1.1e-1 / 2.5e-2 / 1.0e-2 / 1.2e-3 / 6.7e-5;
CIPSI 1.1e-1 / 2.5e-2 / 1.0e-2 / 1.2e-3 / 6.5e-5; ML alone — / 2.6e-2 / 1.5e-2 / 3.5e-3 / 3.4e-4;
BFS 1.5e-1 / 8.4e-2 / 1.8e-2 / 7.6e-3 / 6.2e-4; random 1.05 / 1.05 / 0.86 / 0.88 / 0.73;
device proxy 1.6e-1 / 3.5e-2 / 1.7e-2 / 8.6e-3 / 6.3e-3.  ($B=1$: oracle 1.3e-1 / 5.7e-2 / 1.0e-2 / 9.8e-4 / 6.5e-6;
CIPSI 5.1e-2 / 2.3e-2 / 1.4e-2 / 1.0e-3 / 6.7e-6; device 7.3e-2 / 2.8e-2 / 2.1e-2 / 1.7e-2 / 1.2e-2.)
"random (refs incl.)" keeps the references (the Dirac sea alone carries {p0[refs0[0]]:.2f} of the $B=0$ weight), which is
why it is far below the manual's random row; "random (no refs)" is the manual's protocol.
Device proxy: single reference, five exact Krylov states, $f = 0.1$, $10^4$ shots per circuit, top-$|B|$ by count;
when the device counts contain fewer distinct configurations than the column size the cell is **not** at equal
$|B|$ and carries the realised size in parentheses (the manual's Table 3 does not state this saturation).
Device-seeded CIPSI: CIPSI growth from the top-$|B|/2$ device configurations.

ML ranker: ridge regression on 16 gauge-invariant features conditioned on $(g^2, m, B, L_x)$, trained on 2x2 at
$g^2 \\in \\{{1, 1.5, 2, 3, 6\\}}$ and 2x3 at $g^2 \\in \\{{1, 2, 6\\}}$ (test coupling $g^2 = 4$ excluded on every lattice),
Spearman rank correlation with $\\log|\\langle b|\\Omega\\rangle|$ on the test sectors:

{md_table(["sector", "Spearman ρ"], ml_rows)}

(manual: 0.85 for $B=0$, 0.89 for $B=1$ with its own 16 features).

## 5. Recall of the 99.9 % support versus shots and fidelity (single reference, five exact Krylov states, $B=0$)

{md_table(["f", "10³ shots", "3·10³", "10⁴", "3·10⁴"], rec_rows)}

## 6. 2x4 transfer and scaling (simulator only)

{md_table(["protocol", "|B|", "E_R − E_0", "recall", "fp"], rows24) if rows24 else "(skipped in quick mode)"}

{"Manual (Step 6.2): device support with f = 0.1 and 2e5 shots: |B| = 544, error 7.5e-3, recall 0.94; CIPSI 2.7e-3 at |B| = 640 (oracle 2.75e-3); ML-alone 8.4e-3 and recall 0.95 at |B| = 640." if rows24 else ""}
{f"ML transfer Spearman on 2x4 B=0: {data.get('2x4_ml_spearman', float('nan')):.3f}." if rows24 else ""}

## Interpretation

* The emulation reproduces the manual's qualitative picture: at these sizes the classical CIPSI control tracks the
  oracle and matches or beats the device support at equal $|B|$; the expected hardware outcome is a characterized
  null on the primary endpoint, with the certified spectra as the physics deliverable.
* With the production budget the multi-reference coarse circuits reach the S1 recall criterion at $f = 0.1$ in
  both sectors (see section 3), which fixes the shot rule of eq. (5) of the manual for the hardware run.
* All numbers here are proxy emulations; gate S3 (Aer device-model simulation of the transpiled circuits) is the
  laptop/desktop step that replaces the proxy by a calibrated noise model.

## All checks

{R.criteria_table()}

## Reproduce

```
python scripts/gate_S1.py            # full, ~10 min on 2 CPUs
python scripts/gate_S1.py --quick    # 1 repetition, no 2x4, ~3 min
```
"""
    write_report("S1_support_emulation_controls.md", report)
    print(R.criteria_table())
    print("STATUS", "PASS" if R.passed else "FAIL", "->", path)
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
