#!/usr/bin/env python3
"""
Classical selected-CI baseline for SKQD (owner request 2026-10-29: "do classical selected-CI baseline
comparison for all lattices"; paper referee weakness "no classical baseline was computed").

For the 2x2, 2x3, 2x4 ladders at g^2 = 4, m = 3 g^2 / 16 (skqd.exact.Model(Lx)), sectors 2B = 0, 2:

  * CIPSI-type selected CI in the gauge-invariant basis (skqd.selected_ci): start from the SKQD
    references (skqd.krylov.references), diagonalise, rank every connected external state by the
    Epstein-Nesbet importance e_a = |<a|H|psi_S>|^2 / (E_S - H_aa), add the top ones; main growth
    factor 1.25 per iteration (information: factor 2, "doubling"), until E_var - E0 <= 1e-10.
  * Curves |S| -> E_var - E0, E_var + E_PT2 - E0, captured exact ground-state weight W, the Hamiltonian
    residual r_H, the Weinstein width r_H and the Kato-Temple width with the exact E1, r_H^2/(E1 - E_var)
    (skqd.skqd.certify, the same functions the SKQD gates use), for CIPSI, for the "oracle" (top-|S| states
    by exact ground-state weight, skqd.controls.oracle) and for random subspaces (skqd.controls.random_support,
    references always in; first 20 of gate_H0_2x2.RANDOM_SEEDS on the curve).
  * Equal-size comparison at every SKQD subspace size recorded in validation/: the CIPSI set of exactly that
    size, the oracle set, and 200 random sets (gate_CV.Sector.random_at, seeds 23..222, the CV4 baseline),
    all evaluated with gate_CV.Sector.basis_metrics (the SKQD certificate code path), plus the smallest
    CIPSI / oracle size that reaches SKQD's own error.

  python scripts/selected_ci_baseline.py --lattice 2 3 4       -> data/baselines/selected_ci_2x<L>.json
  python scripts/selected_ci_baseline.py --report              -> reports/selected_ci_baseline.md

Threads: BLAS at 5 threads (owner rule while another agent runs); the CIPSI ranking is made
thread-independent by skqd.selected_ci.TIE_DECIMALS, which is checked at 2x2 and 2x3 by re-running the main
path at one BLAS thread (block `determinism`).  The exact ground state and the oracle order come from
gate_CV.Sector, computed at one thread exactly as in the gates.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "5"

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from skqd.report import ROOT, env_block, environment, md_table, write_report  # noqa: E402

G2 = 4.0
SECTORS = (("B=0", 0), ("B=1", 2))
GROWTH_MAIN = 1.25
GROWTH_INFO = 2.0
BATCH_S1 = {2: 8, 3: 8, 4: 16}                 # gate S1's fixed batch of skqd.controls.cipsi (information schedule)
STOP_ERR = 1e-10
N_RANDOM_CURVE = 20
RANDOM_CURVE_MAX = 2500                        # random curve only up to this size (cost at 2x4)
RANDOM_DENSE_MAX = 300                         # random curve: Lanczos above 300 states (as gate_CV.random_at above 24)
CV2_TYPE = {"B=0": "kato_temple_exact_E1", "B=1": "weinstein"}
OUT_DIR = os.path.join(ROOT, "data", "baselines")
COMMAND = "python scripts/selected_ci_baseline.py --lattice {L}"


def J(p):
    with open(os.path.join(ROOT, p)) as fh:
        return json.load(fh)


# =========================================================================== SKQD points from validation/
def skqd_points(L):
    """Every SKQD subspace with its size, error and certificate, read from the gate JSONs."""
    pts = {"B=0": [], "B=1": []}
    if L == 2:
        H0 = J("validation/H0_2x2.json")["data"]["energies"]
        for sec in pts:
            for basis in ("B_sig", "B_all"):
                b = H0[sec][basis]
                kt = b["kato_temple_rigorous_exact_E1"]
                width = (kt[1] - kt[0]) if CV2_TYPE[sec].startswith("kato") else b["rH"]
                pts[sec].append({
                    "label": f"H0_2x2 ibm_kingston hardware, {basis}", "source": "validation/H0_2x2.json",
                    "path": f"data.energies['{sec}'].{basis}", "kind": "hardware (ibm_kingston, 2x2 saturation)",
                    "size": int(b["basis_size"]), "err": float(b["abs_error"]), "rH": float(b["rH"]),
                    "width": float(width), "W": None, "shots": None})
        et = J("validation/CV_2x2_info.json")["data"]["information"]
        etol = {sec: (float(et[sec]["sector"]["E_tol"]["E_tol"]), "validation/CV_2x2_info.json",
                      f"data.information['{sec}'].sector.E_tol.E_tol") for sec in pts}
    elif L == 3:
        for fn, fam in (("C1_IDEAL", "frozen IR family"), ("C3_AER", "native family")):
            d = J(f"validation/{fn}.json")["data"]["skqd_f1_reference"]
            for sec in pts:
                for key, lab in (("plan_f010", "plan f=0.10"), ("uniform_2e5", "uniform 2e5")):
                    c = d[sec][key]["certificate"]
                    pts[sec].append({
                        "label": f"{fn} {lab}", "source": f"validation/{fn}.json",
                        "path": f"data.skqd_f1_reference['{sec}'].{key}.certificate",
                        "kind": f"noiseless Aer sampling, {fam}", "size": int(c["B_all_size"]),
                        "err": float(c["E_R_minus_E0"]), "rH": None, "width": float(c["width"]), "W": float(c["W"]),
                        "shots": int(d[sec][key]["shots"])})
        cv = J("validation/CV_2x3_plan.json")["data"]
        for f in sorted(cv["curves"]):
            for sec in pts:
                for seed, v in cv["curves"][f][sec].items():
                    full = max(v["shots"], key=lambda p: p["shots"])
                    a = full["all"]
                    width = a["kt_width"] if CV2_TYPE[sec].startswith("kato") else a["rH"]
                    pts[sec].append({
                        "label": f"CV_2x3_plan {f} seed {seed}", "source": "validation/CV_2x3_plan.json",
                        "path": f"data.curves['{f}']['{sec}']['{seed}'].shots[-1].all",
                        "kind": "S1 proxy emulation at clean fraction 0.7 f (garbage + readout), base plan",
                        "size": int(a["size"]), "err": float(a["err"]), "rH": float(a["rH"]),
                        "width": None if width is None else float(width), "W": float(a["W"]),
                        "shots": int(full["shots"])})
        etol = {sec: (float(cv["E_tol"][sec]["value"]), "validation/CV_2x3_plan.json",
                      f"data.E_tol['{sec}'].value") for sec in pts}
    elif L == 4:
        sk = J("validation/SKQD_2x4.json")["data"]["sectors"]
        for sec in pts:
            for key, skey, lab in (("plan_point", "plan_shots", "plan"), ("uniform_point", "uniform_shots", "uniform 2e5")):
                c = sk[sec][key]
                pts[sec].append({
                    "label": f"SKQD_2x4 {lab}", "source": "validation/SKQD_2x4.json",
                    "path": f"data.sectors['{sec}'].{key}", "kind": "noiseless Aer GPU sampling, frozen IR family",
                    "size": int(c["B_all_size"]), "err": float(c["E_R_minus_E0"]), "rH": None,
                    "width": float(c["width"]), "W": float(c["W"]), "shots": int(sk[sec][skey])})
        cv = J("validation/CV_2x4_plan.json")["data"]
        etol = {sec: (float(cv["E_tol"][sec]["value"]), "validation/CV_2x4_plan.json",
                      f"data.E_tol['{sec}'].value") for sec in pts}
    else:
        raise ValueError(L)
    return pts, etol


# =========================================================================== metrics
def curve_metrics(S, it, B_local):
    """Certificates of a CIPSI / oracle / random iterate through skqd.skqd.certify."""
    from skqd.skqd import RitzResult, certify
    B = S.sector_idx[np.asarray(B_local, dtype=int)]
    order = np.argsort(B)
    B, c = B[order], np.asarray(it["c"])[order]
    psi = np.zeros(S.H.shape[0], dtype=complex)
    psi[B] = c
    E = it["E_var"]
    rH = float(np.linalg.norm(S.H @ psi - E * psi))
    en = np.array([E] + ([it["E_var2"]] if it.get("E_var2") is not None else []))
    cert = certify(RitzResult(B=B, energies=en, vectors=c[:, None], rH=rH), S.E0, S.E1)
    kt = cert.kt_rigorous
    return {"size": int(len(B)), "err_var": float(E - S.E0),
            "err_var_plus_pt2": None if "E_pt2" not in it else float(E + it["E_pt2"] - S.E0),
            "E_pt2": it.get("E_pt2"), "W": float(S.prob[B].sum()), "rH": rH,
            "weinstein_width": rH, "kt_width": None if kt is None else float(kt[1] - kt[0]),
            "cert_width": (None if kt is None else float(kt[1] - kt[0])) if CV2_TYPE[S.sec].startswith("kato") else rH,
            "E0_in_weinstein": bool(cert.weinstein[0] - 1e-9 <= S.E0 <= cert.weinstein[1] + 1e-9),
            "E0_in_kt": None if kt is None else bool(kt[0] - 1e-9 <= S.E0 <= kt[1] + 1e-9),
            "n_connected": it.get("n_connected"), "n_intruders": it.get("n_intruders"),
            # B=1: |<k|psi_S>|^2 with the three lowest exact sector states k = 0, 1, 2 (gate_CV.Sector.cluster)
            "overlap_cluster": None if S.cluster is None else
            [float(abs(np.vdot(S.cluster[np.asarray(B_local, dtype=int), j], np.asarray(it["c"]))) ** 2)
             for j in range(S.cluster.shape[1])]}


def oracle_local(S, n):
    from skqd.controls import oracle
    top = oracle(S.prob, S.sector_idx, int(n))
    pos = np.searchsorted(S.sector_idx, top)
    assert np.all(S.sector_idx[pos] == top)
    return np.sort(pos)


def random_curve_point(S, Hs, diag, n, seeds):
    from skqd import selected_ci as sci
    from skqd.controls import random_support
    rows = []
    for s in seeds:
        B = random_support(S.sector_idx, S.refs, int(n), np.random.default_rng(int(s)))
        pos = np.searchsorted(S.sector_idx, B)
        it = sci.evaluate(Hs, diag, pos, S.E0, dense_max=RANDOM_DENSE_MAX)
        rows.append(curve_metrics(S, it, pos))
    keys = ("err_var", "err_var_plus_pt2", "W", "rH", "kt_width", "cert_width")
    out = {"size": int(n), "n_seeds": len(seeds)}
    for k in keys:
        v = np.array([r[k] for r in rows if r[k] is not None], dtype=float)
        out[k + "_median"] = float(np.median(v)) if v.size else None
        if k == "err_var":
            out["err_var_p2_5"], out["err_var_p97_5"] = float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
    return out


def ties_at_cut(path):
    """Steps whose cut (the last added state vs the first not added) falls inside a group of equal ranking
    keys (|e_a|/max|e_a| rounded to TIE_DECIMALS), and how many of them are ties among exact zeros."""
    from skqd.selected_ci import TIE_DECIMALS
    out = {"steps": 0, "steps_tie_at_cut": 0, "steps_tie_at_zero_importance": 0, "first_tie_size": None}
    for it in path:
        if it.get("_target") is None:
            continue
        k = it["_target"] - it["size"]
        a = np.abs(it["_rank"]["e"])
        out["steps"] += 1
        if k < len(a):
            key = np.round(a / a.max(), TIE_DECIMALS) if a.max() > 0 else a
            if key[k - 1] == key[k]:
                out["steps_tie_at_cut"] += 1
                out["steps_tie_at_zero_importance"] += int(a[k] == 0.0)
                if out["first_tie_size"] is None:
                    out["first_tie_size"] = int(it["size"])
    return out


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def nanmed(v):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else None


def strip_it(m):
    return {k: v for k, v in m.items() if not k.startswith("_")}


# =========================================================================== one sector
def run_sector(S, points, etol, L, determinism=False):
    from threadpoolctl import threadpool_limits

    from gate_H0_2x2 import RANDOM_SEEDS, percentile_of
    from skqd import selected_ci as sci
    from skqd.skqd import h1_energy_tolerance

    t0 = time.time()
    tim = {}
    Hs = S.H[S.sector_idx][:, S.sector_idx].tocsr()
    diag = np.real(Hs.diagonal())
    assert np.all(np.diff(S.sector_idx) > 0), "sector indices must be sorted"
    refs_local = np.searchsorted(S.sector_idx, S.refs)
    assert np.all(S.sector_idx[refs_local] == np.asarray(S.refs))

    # E_tol through the gate's call, checked against the gate JSON
    et = h1_energy_tolerance(S.H, S.prob, S.refs, 0.8, 1e-3, sector_idx=S.sector_idx, E0=S.E0)["E_tol"]
    etol_rec = {"value": float(et), "gate_value": etol[0], "gate_file": etol[1], "gate_path": etol[2],
                "abs_diff": abs(float(et) - etol[0])}

    # ---- main and information CIPSI paths
    paths = {}
    nmax = max(p["size"] for p in points)
    for name, g, bt, cap in (("main", GROWTH_MAIN, None, None), ("doubling", GROWTH_INFO, None, None),
                             ("batch", 1.0, BATCH_S1[L], nmax)):
        ts = time.time()
        paths[name] = sci.cipsi_path(Hs, diag, refs_local, g, S.E0, STOP_ERR, max_size=cap, batch=bt)
        tim[f"cipsi_path_{name}_s"] = time.time() - ts
        log(f"{S.lattice} {S.sec}: CIPSI path {name}: {len(paths[name])} iterates, last |S| = "
            f"{paths[name][-1]['size']}, {tim[f'cipsi_path_{name}_s']:.1f} s")

    # cross-check: the package's skqd.controls.cipsi (gate S1) at the smallest SKQD size, same batch
    ts = time.time()
    from skqd.controls import cipsi as package_cipsi
    nchk = min(p["size"] for p in points)
    Bp = package_cipsi(S.H, S.refs, nchk, batch=BATCH_S1[L])
    Bm = S.sector_idx[sci.cipsi_at(Hs, diag, paths["batch"], nchk, S.E0, batch=BATCH_S1[L])["S"]]
    from skqd.skqd import ritz
    xchk = {"size": int(nchk), "batch": BATCH_S1[L], "same_set": bool(np.array_equal(np.sort(Bp), np.sort(Bm))),
            "E_R_package_minus_this": float(ritz(S.H, Bp).ER - ritz(S.H, Bm).ER),
            "note": "skqd.controls.cipsi ranks by |<c|H|psi>|^2 / max(|H_cc - E_R|, 1e-12) with an unstable argsort; "
                    "a set difference with E_R equal to round-off is a tie-breaking difference, not a different selection rule", "seconds": time.time() - ts}
    log(f"{S.lattice} {S.sec}: controls.cipsi cross-check {xchk}")
    ties = {name: ties_at_cut(pa) for name, pa in paths.items()}
    xchk["batch_path_ties_at_cut"] = ties["batch"]
    curve = []
    for it in paths["main"]:
        m = curve_metrics(S, it, it["S"])
        m["short_step"] = bool(it["short_step"])
        curve.append(m)
    curve_dbl = [dict(curve_metrics(S, it, it["S"]), short_step=bool(it["short_step"])) for it in paths["doubling"]]
    log(f"{S.lattice} {S.sec}: curves done ({time.time() - t0:.1f} s)")
    # nesting: CIPSI(n) = S_j + a prefix of S_j's ranking for every n <= |S_last| (a short step adds the whole
    # ranking, so the next iterate is again the largest set <= n); E_var(n) is non-increasing on [|R|, |S_last|]
    n_last = int(paths["main"][-1]["size"])

    # ---- oracle and random curves at the main-path sizes
    ts = time.time()
    sizes = [m["size"] for m in curve]
    oracle_curve = []
    for n in sizes:
        pos = oracle_local(S, n)
        oracle_curve.append(curve_metrics(S, sci.evaluate(Hs, diag, pos, S.E0), pos))
    tim["oracle_curve_s"] = time.time() - ts
    log(f"{S.lattice} {S.sec}: oracle curve {tim['oracle_curve_s']:.1f} s")
    ts = time.time()
    rseeds = RANDOM_SEEDS[:N_RANDOM_CURVE]
    random_curve = [random_curve_point(S, Hs, diag, n, rseeds) for n in sizes if len(S.refs) <= n <= RANDOM_CURVE_MAX]
    tim["random_curve_s"] = time.time() - ts
    log(f"{S.lattice} {S.sec}: random curve {tim['random_curve_s']:.1f} s")

    # ---- equal-size comparison
    ts = time.time()
    cache_c, cache_o = {}, {}

    def cipsi_err(n):
        if n not in cache_c:
            cache_c[n] = sci.cipsi_at(Hs, diag, paths["main"], n, S.E0, GROWTH_MAIN)["err_var"]
        return cache_c[n]

    def oracle_err(n):
        if n not in cache_o:
            cache_o[n] = sci.evaluate(Hs, diag, oracle_local(S, n), S.E0)["err_var"]
        return cache_o[n]

    rows = []
    for p in points:
        n = p["size"]
        row = {"skqd": p, "E_tol": float(et)}
        it = sci.cipsi_at(Hs, diag, paths["main"], n, S.E0, GROWTH_MAIN)
        B = S.sector_idx[it["S"]]
        bm = S.basis_metrics(B)
        row["cipsi"] = {**bm, "err_var_plus_pt2": float(it["E_var_plus_pt2"] - S.E0), "E_pt2": it["E_pt2"],
                        "branch_from_size": it["branch_from_size"], "branch_steps": it["branch_steps"],
                        "E_var_selected_ci_minus_ritz": float(it["E_var"] - bm["E_R"]),
                        "cert_width": bm["kt_width"] if CV2_TYPE[S.sec].startswith("kato") else bm["rH"]}
        itd = sci.cipsi_at(Hs, diag, paths["doubling"], n, S.E0, GROWTH_INFO)
        row["cipsi_doubling_information"] = {"err_var": itd["err_var"],
                                             "err_var_plus_pt2": float(itd["E_var_plus_pt2"] - S.E0)}
        itb = sci.cipsi_at(Hs, diag, paths["batch"], n, S.E0, batch=BATCH_S1[L])
        row["cipsi_batch_information"] = {"batch": BATCH_S1[L], "err_var": itb["err_var"],
                                          "err_var_plus_pt2": float(itb["E_var_plus_pt2"] - S.E0)}
        log(f"{S.lattice} {S.sec}: equal-size {p['label']} |B| = {n}: CIPSI {row['cipsi']['err']:.3e}, "
            f"SKQD {p['err']:.3e} ({time.time() - ts:.1f} s)")
        om = S.basis_metrics(S.sector_idx[oracle_local(S, n)])
        row["oracle"] = {**om, "cert_width": om["kt_width"] if CV2_TYPE[S.sec].startswith("kato") else om["rH"]}
        rd = S.random_at(n)
        E, rH, W = rd["E"], rd["rH"], rd["W"]
        kt = np.where(E < S.E1, rH ** 2 / np.maximum(S.E1 - E, 1e-300), np.nan)
        cw = kt if CV2_TYPE[S.sec].startswith("kato") else rH
        row["random"] = {"n": int(len(E)), "seeds": f"{RANDOM_SEEDS[0]}..{RANDOM_SEEDS[-1]}",
                         "function": "gate_CV.Sector.random_at (skqd.controls.random_support, references in)",
                         "contains_R": rd["contains_R"], "sizes_ok": rd["sizes_ok"],
                         "err_median": float(np.median(E) - S.E0), "err_p2_5": float(np.percentile(E, 2.5) - S.E0),
                         "err_p97_5": float(np.percentile(E, 97.5) - S.E0), "err_min": float(np.min(E) - S.E0),
                         "rH_median": float(np.median(rH)), "kt_width_median": nanmed(kt),
                         "kt_defined_fraction": float(np.mean(np.isfinite(kt))),
                         "cert_width_median": nanmed(cw), "W_median": float(np.median(W)),
                         "skqd_err_percentile": percentile_of(S.E0 + p["err"], E)}
        if p["err"] > STOP_ERR:
            row["cipsi_size_to_reach_skqd_err"] = sci.size_to_reach(cipsi_err, int(len(S.refs)), n_last, p["err"])
            row["oracle_size_to_reach_skqd_err"] = sci.size_to_reach(oracle_err, 1, int(S.dim), p["err"])
        else:                                          # SKQD exact to round-off (2x2 B_all = the whole sector)
            row["cipsi_size_to_reach_skqd_err"] = row["oracle_size_to_reach_skqd_err"] = None
        rows.append(row)
    tim["equal_size_s"] = time.time() - ts

    det = None
    if determinism:
        ts = time.time()
        with threadpool_limits(1):
            p1 = sci.cipsi_path(Hs, diag, refs_local, GROWTH_MAIN, S.E0, STOP_ERR)
        same_sets = len(p1) == len(paths["main"]) and all(
            np.array_equal(a["S"], b["S"]) for a, b in zip(p1, paths["main"]))
        dmax = max(abs(a["E_var"] - b["E_var"]) for a, b in zip(p1, paths["main"]))
        det = {"blas_threads": [5, 1], "same_sets_every_iterate": bool(same_sets), "max_abs_dE_var": float(dmax),
               "seconds": time.time() - ts}

    tim["sector_total_s"] = time.time() - t0
    return {"dim": S.dim, "E0": S.E0, "E1": S.E1, "references": [int(r) for r in S.refs],
            "cluster_energies": getattr(S, "cluster_energies", None),
            "S999_size": int(len(S.S999)), "certificate_type": CV2_TYPE[S.sec], "E_tol": etol_rec,
            "cipsi_main_last_size": n_last, "ties_at_cut": ties,
            "cipsi_main_short_steps": [int(it["size"]) for it in paths["main"] if it["short_step"]],
            "curves": {"cipsi": curve, "cipsi_doubling_information": curve_dbl,
                       "cipsi_batch_information": [dict(size=int(it["size"]), err_var=it["err_var"],
                                                        err_var_plus_pt2=it["err_pt2"]) for it in paths["batch"]],
                       "oracle": oracle_curve, "random": random_curve},
            "equal_size": rows, "package_cipsi_crosscheck": xchk, "determinism": det, "timing": tim}


def run_lattice(L):
    from threadpoolctl import threadpool_info

    import gate_CV as GC
    from skqd.exact import Model
    t0 = time.time()
    M = Model(L)
    t_build = time.time() - t0
    points, etol = skqd_points(L)
    out = {"lattice": f"2x{L}", "g2": G2, "m": "3 g^2 / 16 (skqd.exact.mass_default)",
           "what": "classical selected-CI (CIPSI-type) baseline vs SKQD subspaces, with oracle and random references",
           "owner_request": "2026-10-29: classical selected-CI baseline comparison for all lattices, for the paper",
           "method": {
               "module": "src/skqd/selected_ci.py",
               "importance": "Epstein-Nesbet e_a = |<a|H|psi_S>|^2 / (E_S - H_aa) over external states structurally "
                             "connected to S; E_PT2 = sum_a e_a",
               "ranking": "|e_a|/max|e_a| rounded to 1e-10 (TIE_DECIMALS), descending, ties by sector-local index",
               "start": "the SKQD references skqd.krylov.references(basis, 2B)",
               "growth_main": GROWTH_MAIN, "growth_information": GROWTH_INFO,
               "batch_information": f"fixed batch {BATCH_S1[L]} per iteration (gate S1's skqd.controls.cipsi setting), "
                                    "path capped at the largest SKQD size",
               "step_rule": "target = min(dim, max(|S|+1, ceil(growth |S|))); add the top (target - |S|) of the ranking",
               "stop": f"E_var - E0 <= {STOP_ERR} or |S| = dim",
               "equal_size_rule": "CIPSI(n) = last main iterate S_j with |S_j| <= n plus the top (n - |S_j|) of its "
                                  "ranking (a prefix of the next main step)",
               "eigensolver": "dense numpy eigh up to 500 states, scipy eigsh(k=2, SA, tol 1e-12) above",
               "certificates": "skqd.skqd.certify via gate_CV.Sector.basis_metrics at the equal-size points; "
                               "B=0 Kato-Temple with the exact E1 (width r_H^2/(E1 - E_R)), B=1 Weinstein (width r_H)",
               "oracle": "skqd.controls.oracle: top-|S| states by exact ground-state weight (no references forced)",
               "random_equal_size": "gate_CV.Sector.random_at: 200 sets, seeds 23..222 (gate_H0_2x2.RANDOM_SEEDS), "
                                    "references always in",
               "random_curve": f"first {N_RANDOM_CURVE} of the same seeds, at the CIPSI main-path sizes <= {RANDOM_CURVE_MAX}",
               "kt_width_random": "per random set r_H^2/(E1 - E_R) when E_R < E1, median over the sets where it is defined",
               "size_to_reach": "smallest n with E_var(n) - E0 <= SKQD's E_R - E0, bisection on the nested family"},
           "seeds": {"random_equal_size": "23..222", "random_curve": f"23..{23 + N_RANDOM_CURVE - 1}",
                     "cipsi": "deterministic (no random numbers)"},
           "sectors": {}}
    for sec, tb in SECTORS:
        S = GC.Sector(M, f"2x{L}", sec, tb, 0.0)
        out["sectors"][sec] = run_sector(S, points[sec], etol[sec], L, determinism=True)
        print(f"2x{L} {sec}: done in {out['sectors'][sec]['timing']['sector_total_s']:.1f} s", flush=True)
    env = environment()
    out["provenance"] = {"git_commit": env.get("git_commit"), "command": COMMAND.format(L=L), "machine": env,
                         "blas": [{k: d.get(k) for k in ("internal_api", "num_threads")} for d in threadpool_info()],
                         "taskset": "taskset -c 0-4 nice -n 10 (owner rule: at most 5 threads)",
                         "model_build_s": t_build, "wall_s": time.time() - t0}
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"selected_ci_2x{L}.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print("wrote", os.path.relpath(path, ROOT))
    return out


# =========================================================================== report
def e(x, d=2):
    if x is None:
        return "n/a"
    if x == 0:
        return "$0$"
    s = f"{x:.{d}e}"
    m, ex = s.split("e")
    return f"${m}\\times10^{{{int(ex)}}}$"


def f3(x):
    return "n/a" if x is None else f"{x:.6f}"


def load_all():
    data = {}
    for L in (2, 3, 4):
        p = os.path.join(OUT_DIR, f"selected_ci_2x{L}.json")
        if os.path.exists(p):
            with open(p) as fh:
                data[L] = json.load(fh)
    return data


def all_rows(data, table_only=False):
    """(lattice, sector, sector data, row) over every equal-size row; table_only drops the CV_2x3_plan
    f = 0.05 / 0.15 rows (kept in the JSON and in the counts)."""
    for L, d in data.items():
        for sec, sd in d["sectors"].items():
            for r in sd["equal_size"]:
                p = r["skqd"]
                if table_only and p["source"].endswith("CV_2x3_plan.json") and "f=0.10" not in p["label"]:
                    continue
                yield d["lattice"], sec, sd, r


def best_cipsi(r):
    """The best variational error over the three schedules (main 1.25x, doubling, fixed batch)."""
    return min(r["cipsi"]["err"], r["cipsi_doubling_information"]["err_var"], r["cipsi_batch_information"]["err_var"])


def report():
    data = load_all()
    lines = []
    A = lines.append
    commits = sorted({d["provenance"]["git_commit"] for d in data.values()})
    d0 = next(iter(data.values()))["method"]
    A("# Classical selected-CI baseline for SKQD (2x2, 2x3, 2x4)\n")
    A(f"Date: 2026-10-29.  Code commit of the data run(s): {', '.join(commits)} (the data files carry their own "
      "commit; the code that wrote them is committed together with them).  Prompt: owner request of 2026-10-29 "
      "via the coordinator (\"do classical selected-CI baseline comparison for all lattices ... add all these to "
      "the paper\"); paper referee weakness \"No classical baseline was computed\".  Generated by "
      "`python scripts/selected_ci_baseline.py --report` from `data/baselines/selected_ci_2x{2,3,4}.json`; every "
      "number below is read from those files.  Related: `reports/S1_support_emulation_controls.md` (gate S1, which already contained a "
      "fixed-batch CIPSI control at a few sizes), `validation/C1_IDEAL.json`, `validation/SKQD_2x4.json`, "
      "`validation/CV_2x3_plan.json`, `validation/H0_2x2.json`.\n")

    # ------------------------------------------------------------------ 1. asked
    A("## 1. What was asked\n")
    A("Compare the subspaces that SKQD built from sampled bit strings with subspaces chosen by a purely "
      "classical method, at the same subspace size, on every ladder SKQD was run on: $2\\times2$, $2\\times3$ and "
      "$2\\times4$, coupling $g^2=4$, mass $m=3g^2/16$, sectors $B=0$ and $B=1$ (twice the baryon number "
      "$2B=0,2$).  Energies are in lattice units ($a=1$).\n")
    A("**Words used.**  A *basis state* is one gauge-invariant configuration of the sector (one bit string that "
      "SKQD can measure).  *Selected configuration interaction* (selected CI) keeps a chosen set $S$ of basis "
      "states, diagonalises the Hamiltonian $H$ inside the span of $S$, and grows $S$ by states judged important. "
      "The lowest eigenvalue of $H$ restricted to $S$ is the *variational energy* $E_{\\rm var}(S)$; it is never "
      "below the true ground energy $E_0$.  *CIPSI* (configuration interaction by perturbation with "
      "multiconfigurational zeroth-order wave functions selected by iterative process; B. Huron, J.-P. Malrieu and "
      "P. Rancurel, J. Chem. Phys. 58, 5745 (1973), doi:10.1063/1.1679199) is the selection rule used here: every "
      "basis state $a\\notin S$ that $H$ connects to $S$ gets the second-order perturbation-theory (*PT2*, "
      "Epstein-Nesbet form) importance\n")
    A("$$e_a=\\frac{|\\langle a|H|\\psi_S\\rangle|^2}{E_{\\rm var}(S)-H_{aa}},$$\n")
    A("where $\\psi_S$ is the lowest eigenvector in $S$ and $H_{aa}$ the diagonal matrix element; the states with "
      "the largest $|e_a|$ are added and the step repeats.  The sum $E_{\\rm PT2}=\\sum_a e_a$ estimates the energy "
      "still missing, so $E_{\\rm var}+E_{\\rm PT2}$ is an improved estimate of $E_0$ (an estimate, not a bound).  "
      "$W(S)=\\sum_{b\\in S}|\\langle b|\\Omega\\rangle|^2$ is the exact ground-state weight captured by $S$ "
      "($|\\Omega\\rangle$ the exact ground state).  The *certificate width* is the length of the interval that "
      "provably (under the gap condition of the gates) contains $E_0$: for $B=0$ the Kato-Temple width "
      "$r_H^2/(E_1-E_R)$ with the exact first excited energy $E_1$, for $B=1$ the Weinstein width $r_H$, where "
      "$r_H=\\lVert(H-E_R)\\psi_R\\rVert$ is the residual of the Ritz vector (the lowest eigenvector in the "
      "subspace, energy $E_R$) with the exact $H$.\n")
    A("**Two reference curves.**  *Oracle*: the $|S|$ basis states with the largest exact ground-state weight. "
      "It maximises $W$ at fixed size (it is not guaranteed to minimise the energy) and it needs the exact answer. "
      "*Random*: 200 random subsets of the sector of the same size that always contain the SKQD reference states "
      "(the package's CV4 baseline, seeds 23 to 222).\n")

    # ------------------------------------------------------------------ 2. done
    A("## 2. What was done\n")
    A(f"* CIPSI starts from the SKQD reference states (`skqd.krylov.references`) and grows by a factor "
      f"{d0['growth_main']} per iteration (target size $\\lceil {d0['growth_main']}\\,|S|\\rceil$) until "
      "$E_{\\rm var}-E_0\\le10^{-10}$ or the whole sector.  Two other schedules are recorded at every comparison "
      "point: doubling (factor 2), and a fixed batch of 8 ($2\\times2$, $2\\times3$) or 16 ($2\\times4$) states per "
      "iteration, the setting of the package's existing `skqd.controls.cipsi` in gate S1.  Code: "
      "`src/skqd/selected_ci.py`; driver `scripts/selected_ci_baseline.py`; tests `tests/test_selected_ci.py`.\n")
    A("* The CIPSI set of exactly $n$ states is the last iterate with at most $n$ states plus the top of its "
      "ranking, i.e. a prefix of the next CIPSI step, so CIPSI sets are nested in $n$ and $E_{\\rm var}$ falls "
      "monotonically with $n$.  CIPSI, oracle and random sets are evaluated with `gate_CV.Sector.basis_metrics` "
      "and `skqd.skqd.certify`, the code path of the SKQD gates.\n")
    A("* \"Size to reach SKQD\": the smallest CIPSI (main schedule) or oracle subspace whose $E_{\\rm var}-E_0$ "
      "is at or below SKQD's own $E_R-E_0$ at that row (bisection on the nested family).\n")
    A("* SKQD rows: $2\\times2$ = the ibm_kingston hardware session (`validation/H0_2x2.json`, significance-"
      "filtered basis $B_{\\rm sig}$ and the full accepted basis $B_{\\rm all}$); $2\\times3$ = noiseless Aer "
      "sampling of the frozen circuits (`validation/C1_IDEAL.json`, the paper's Table of noiseless SKQD) and of the "
      "native circuits (`validation/C3_AER.json`) at the $f=0.10$ plan and at $2\\times10^5$ shots, plus the noisy "
      "proxy emulation of the plan (`validation/CV_2x3_plan.json`, three seeds at each of $f=0.05,0.10,0.15$); "
      "$2\\times4$ = `validation/SKQD_2x4.json` (plan and $2\\times10^5$ points).\n")
    A("* Runs: " + "; ".join(f"{d['lattice']} `{d['provenance']['command']}` {d['provenance']['wall_s']:.0f} s wall"
                             for d in data.values())
      + ", BLAS 5 threads under `taskset -c 0-4 nice -n 10` on the laptop (i7-8750H).\n")

    # ------------------------------------------------------------------ 3. results
    A("## 3. Results\n")
    A("### Table 1. Energy error at equal subspace size\n")
    hdr = ["Lattice", "$B$", "SKQD subspace", "$\\lvert B\\rvert$", "SKQD $E_R-E_0$", "CIPSI $E_{\\rm var}-E_0$",
           "CIPSI $E_{\\rm var}+E_{\\rm PT2}-E_0$", "CIPSI doubling", "CIPSI fixed batch", "Oracle $E_R-E_0$",
           "Random median [2.5, 97.5 %]"]
    rows = []
    for lat, sec, sd, r in all_rows(data, table_only=True):
        p, rd = r["skqd"], r["random"]
        rows.append([lat, sec[-1], p["label"], p["size"], e(p["err"]), e(r["cipsi"]["err"]),
                     e(r["cipsi"]["err_var_plus_pt2"]), e(r["cipsi_doubling_information"]["err_var"]),
                     e(r["cipsi_batch_information"]["err_var"]), e(r["oracle"]["err"]),
                     f"{e(rd['err_median'])} [{e(rd['err_p2_5'])}, {e(rd['err_p97_5'])}]"])
    A(md_table(hdr, rows) + "\n")
    A("The $2\\times2$ $B_{\\rm all}$ rows are the whole sector (hardware noise filled it), where every method is "
      "exact; they are listed for completeness.  The CV_2x3_plan rows at $f=0.05$ and $f=0.15$ are in the JSON "
      "and enter the counts of Section 4.\n")
    A("### Table 2. Certificates, captured weight and the size each method needs for SKQD's error\n")
    hdr = ["Lattice", "$B$", "SKQD subspace", "$\\lvert B\\rvert$", "Cert.", "SKQD width", "CIPSI width",
           "Oracle width", "Random median width", "SKQD $1-W$", "CIPSI $1-W$", "Oracle $1-W$",
           "CIPSI size for SKQD error", "Oracle size for SKQD error"]
    rows = []
    for lat, sec, sd, r in all_rows(data, table_only=True):
        p, rd = r["skqd"], r["random"]
        cert = "KT" if sd["certificate_type"].startswith("kato") else "W"
        rows.append([lat, sec[-1], p["label"], p["size"], cert, e(p["width"]), e(r["cipsi"]["cert_width"]),
                     e(r["oracle"]["cert_width"]), e(rd["cert_width_median"]),
                     e(None if p["W"] is None else max(0.0, 1 - p["W"]), 1), e(max(0.0, 1 - r["cipsi"]["W"]), 1),
                     e(max(0.0, 1 - r["oracle"]["W"]), 1), r["cipsi_size_to_reach_skqd_err"] or "n/a",
                     r["oracle_size_to_reach_skqd_err"] or "n/a"])
    A(md_table(hdr, rows) + "\n")
    A("KT = Kato-Temple with the exact $E_1$ ($B=0$), W = Weinstein ($B=1$).  SKQD $1-W$ is \"n/a\" for the "
      "$2\\times2$ hardware rows because `validation/H0_2x2.json` does not record $W$ for them.  For $B=1$ "
      "random sets the Kato-Temple interval is mostly undefined ($E_R$ above $E_1$); the Weinstein width is used "
      "as for SKQD.  \"n/a\" in the size columns: SKQD is exact to round-off.\n")

    A("### Table 3. Sector data and checks\n")
    hdr = ["Lattice", "$B$", "dim", "$\\lvert S_{99.9}\\rvert$", "$E_{\\rm tol}$", "$E_{\\rm tol}$ vs gate",
           "CIPSI size at $E_{\\rm var}-E_0\\le E_{\\rm tol}$", "CIPSI size at $10^{-10}$",
           "BLAS 5 vs 1 thread: same sets", "package `controls.cipsi` same set (size, $\\Delta E_R$)",
           "fixed-batch steps cut inside a tie (at zero importance)"]
    rows = []
    for L, d in data.items():
        for sec, sd in d["sectors"].items():
            c = sd["curves"]["cipsi"]
            first = next((m["size"] for m in c if m["err_var"] <= sd["E_tol"]["value"]), None)
            det, x = sd["determinism"], sd["package_cipsi_crosscheck"]
            tb = x["batch_path_ties_at_cut"]
            rows.append([d["lattice"], sec[-1], sd["dim"], sd["S999_size"], e(sd["E_tol"]["value"], 3),
                         f"diff {e(sd['E_tol']['abs_diff'], 1)}", first, c[-1]["size"],
                         "n/a" if det is None else ("yes" if det["same_sets_every_iterate"] else "NO"),
                         f"{'yes' if x['same_set'] else 'no'} ({x['size']}, {e(x['E_R_package_minus_this'], 1)})",
                         f"{tb['steps_tie_at_cut']} of {tb['steps']} ({tb['steps_tie_at_zero_importance']})"])
    A(md_table(hdr, rows) + "\n")
    A("\"CIPSI size at $E_{\\rm var}-E_0\\le E_{\\rm tol}$\" is read on the main-schedule iterates, so it is an "
      "upper bound of the exact crossing size.  $E_{\\rm tol}$ is recomputed with `skqd.skqd.h1_energy_tolerance` "
      "as in the gates and compared with the gate files' value.  The package cross-check runs gate S1's "
      "`skqd.controls.cipsi` with the same fixed batch to the smallest SKQD size of the sector; where the sets "
      "differ, the fixed-batch path had cuts inside groups of equal importance (last column), which the two codes "
      "break differently (here by index, there by `argsort`).\n")

    A("### Table 4. CIPSI curves (main schedule) with the oracle and random sets at the same sizes\n")
    for L, d in data.items():
        for sec, sd in d["sectors"].items():
            A(f"**{d['lattice']}, $B={sec[-1]}$** (dimension {sd['dim']}):\n")
            hdr = ["$\\lvert S\\rvert$", "CIPSI $E_{\\rm var}-E_0$", "CIPSI $E_{\\rm var}+E_{\\rm PT2}-E_0$",
                   "CIPSI $1-W$", "CIPSI width", "Oracle $E_R-E_0$", "Oracle $1-W$",
                   f"Random median $E_R-E_0$ ({N_RANDOM_CURVE} sets)"]
            rnd = {r["size"]: r for r in sd["curves"]["random"]}
            rows = []
            for m, o in zip(sd["curves"]["cipsi"], sd["curves"]["oracle"]):
                rr = rnd.get(m["size"])
                rows.append([m["size"], e(m["err_var"]), e(m["err_var_plus_pt2"]), e(max(0.0, 1 - m["W"]), 1),
                             e(m["cert_width"]), e(o["err_var"]), e(max(0.0, 1 - o["W"]), 1),
                             e(None if rr is None else rr["err_var_median"])])
            A(md_table(hdr, rows) + "\n")
    A(f"Random sets are evaluated only up to {RANDOM_CURVE_MAX} states.\n")

    A("## 4. What the result means\n")
    A(_reading(data))
    A("## 5. Problems and assumptions\n")
    A("* At these sizes (at most 12843 basis states per sector) the whole sector can be diagonalised exactly in "
      "seconds, so this comparison is about the *quality of the subspace*, not about cost.  CIPSI needs the matrix "
      "elements of $H$ to every connected state and runs entirely classically; SKQD's point is to obtain the "
      "subspace from quantum samples when the sector is too large to enumerate.  Nothing here tests that regime, "
      "and no statement about quantum advantage or disadvantage at scale follows from it.\n")
    A("* CIPSI depends on its growth schedule and, in sectors with symmetry-equivalent or zero-importance "
      "states, on how ties are broken.  Both effects are reported (three schedules in Table 1; tie counts and the "
      "gate S1 cross-check in Table 3) rather than tuned away.  A state-averaged selection over the lowest few "
      "roots, the usual remedy for near-degenerate levels such as the $B=1$ cluster, was not tried.\n")
    A("* The oracle maximises captured weight, not energy, so CIPSI can match or beat it in energy at equal size. "
      "Both CIPSI and the oracle use information SKQD does not have (the exact $H$ applied to the current vector, "
      "or the exact ground state).\n")
    A("* $E_{\\rm PT2}$ is an estimate, not a bound; $E_{\\rm var}+E_{\\rm PT2}-E_0$ can be negative.\n")
    A("* The $2\\times2$ SKQD subspaces come from a hardware session whose noise saturated the sector "
      "(`validation/H0_2x2.json`, labelled \"not a device test (saturation)\"); only $B_{\\rm sig}$ is a "
      "non-trivial $2\\times2$ comparison.  The SKQD rows of $2\\times3$ and $2\\times4$ are emulations "
      "(noiseless Aer sampling, or the S1 noise proxy), not hardware.\n")
    sk_et = J("validation/SKQD_2x4.json")["data"]["sectors"]["B=0"]["E_tol"]["abs_diff"]
    A("* The $2\\times4$ exact ground states come from `scipy.sparse.linalg.eigsh` at tolerance $10^{-10}$ without a "
      "fixed start vector (`skqd.exact.sector_reference`), so $E_0$, the weights and $E_{\\rm tol}$ there are "
      "reproducible only to about that tolerance (`validation/SKQD_2x4.json` itself records a $B=0$ "
      f"$E_{{\\rm tol}}$ difference of {e(sk_et, 1)} between its two evaluations).  This is far below every "
      "energy difference compared here.\n")
    A("* The ranking rounds $|e_a|/\\max|e_a|$ to $10^{-10}$ before breaking ties by index, so the CIPSI sets do "
      "not depend on the BLAS thread count (Table 3, re-run at one thread).\n")
    A("\n" + env_block() + "\n")
    path = write_report("selected_ci_baseline.md", "\n".join(lines))
    print("wrote", os.path.relpath(path, ROOT))


def _reading(data):
    """Plain-English reading; every number is computed here from the data."""
    rows = [(lat, sec, sd, r) for lat, sec, sd, r in all_rows(data) if r["skqd"]["err"] > STOP_ERR]
    n = len(rows)
    c_main = [x for x in rows if x[3]["cipsi"]["err"] < x[3]["skqd"]["err"]]
    c_best = [x for x in rows if best_cipsi(x[3]) < x[3]["skqd"]["err"]]
    orc = [x for x in rows if x[3]["oracle"]["err"] < x[3]["skqd"]["err"]]
    beat_rand = [x for x in rows if x[3]["skqd"]["err"] < x[3]["random"]["err_median"]]
    all_rand = [x for x in rows if x[3]["random"]["skqd_err_percentile"] == 0.0]
    out = []
    out.append(f"* **Count.**  There are {n} equal-size rows in which SKQD is not exact to round-off (all lattices, "
               f"sectors and SKQD runs in the JSON files).  CIPSI with the main schedule has a lower variational "
               f"energy than SKQD in {len(c_main)} of them; the best of the three CIPSI schedules in {len(c_best)}; "
               f"the oracle in {len(orc)}.  SKQD is below the median random subset in {len(beat_rand)} and below "
               f"all 200 random subsets in {len(all_rand)}.\n")
    for lat, sec, sd, r in rows:
        if r["cipsi"]["err"] >= r["skqd"]["err"]:
            p = r["skqd"]
            out.append(f"* **Exception: {lat} {sec}, {p['label']} ($|B|={p['size']}$).**  SKQD's error "
                       f"{e(p['err'])} is below CIPSI's {e(r['cipsi']['err'])} with the main schedule (CIPSI "
                       f"needs {r['cipsi_size_to_reach_skqd_err']} states to match it), but the fixed-batch schedule "
                       f"gives {e(r['cipsi_batch_information']['err_var'])} and the oracle {e(r['oracle']['err'])}. "
                       f"SKQD captures $1-W$ = {e(1 - p['W'], 1)} against CIPSI's "
                       f"{e(1 - r['cipsi']['W'], 1)}.\n")
    ratios = [(x[3]["cipsi_size_to_reach_skqd_err"] / x[3]["skqd"]["size"]) for x in rows
              if x[3]["cipsi_size_to_reach_skqd_err"]]
    if ratios:
        out.append(f"* **Size for equal accuracy.**  The CIPSI subspace (main schedule) that reaches SKQD's error "
                   f"has between {min(ratios):.2f} and {max(ratios):.2f} times SKQD's number of states (median "
                   f"{np.median(ratios):.2f}) over these {len(ratios)} rows.\n")
    # sector-level statements for the B=1 sectors (near-degenerate cluster), from the measured overlaps
    for L, d in data.items():
        sd = d["sectors"].get("B=1")
        if sd is None or sd["curves"]["cipsi"][0].get("overlap_cluster") is None:
            continue
        gap = sd["E1"] - sd["E0"]
        cur = sd["curves"]["cipsi"]
        mix = [m for m in cur if m["overlap_cluster"][1] > 0.01]
        if mix:
            worst = max(mix, key=lambda m: m["overlap_cluster"][1])
            out.append(f"* **{d['lattice']} $B=1$ (gap $E_1-E_0$ = {e(gap, 3)}).**  The overlap of the main-path CIPSI "
                       f"vector with the exact first excited state, $|\\langle 1|\\psi_S\\rangle|^2$, exceeds 0.01 at "
                       f"{len(mix)} of {len(cur)} iterates (sizes {mix[0]['size']} to {mix[-1]['size']}; largest "
                       f"{worst['overlap_cluster'][1]:.3f} at $|S|={worst['size']}$, where the overlap with the ground "
                       f"state is {worst['overlap_cluster'][0]:.3f}).  In that range the selection follows a mixture "
                       f"of the two nearly degenerate levels (see the schedule dependence below).\n")
    rest = [x for x in rows if x not in all_rand]
    if rest:
        out.append("* SKQD rows not below all 200 random subsets: " + "; ".join(
            f"{lat} {sec} {r['skqd']['label']} ($|B|={r['skqd']['size']}$, {r['random']['skqd_err_percentile']:.1f} % "
            f"of the random subsets at or below SKQD)" for lat, sec, sd, r in rest) + ".\n")
    spread = {}
    for lat, sec, sd, r in rows:
        v = [r["cipsi"]["err"], r["cipsi_doubling_information"]["err_var"], r["cipsi_batch_information"]["err_var"]]
        spread.setdefault(sec, []).append(max(v) / min(v))
    out.append("* **Schedule dependence.**  The ratio between the worst and the best of the three CIPSI schedules "
               "at an SKQD size reaches " + ", ".join(f"{max(v):.1f} in the {k} rows (median {np.median(v):.2f})"
                                                     for k, v in sorted(spread.items())) + ".\n")
    med = f"{np.median(ratios):.2f}" if ratios else "n/a"
    out.append(f"* **Plain reading.**  At every lattice size reached here, a classical selection that may apply $H$ "
               f"to its current vector finds a lower-energy subspace than SKQD's sampled one at the same size in "
               f"{len(c_main)} of {n} rows (main schedule; {len(c_best)} of {n} with the best schedule), and reaches "
               f"SKQD's accuracy with a median {med} times SKQD's number of states.  SKQD's subspaces are far better "
               f"than random subsets of the same size.  This is the expected outcome in sectors small enough to "
               f"enumerate, and the paper should say so plainly: the comparison measures how close quantum "
               f"sampling comes to a good classical selection; it is not evidence of an advantage over it, and it "
               f"says nothing about the regime SKQD is designed for.\n")
    return "".join(out)



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lattice", type=int, nargs="*", default=[])
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    for L in a.lattice:
        run_lattice(L)
    if a.report:
        report()


if __name__ == "__main__":
    main()
