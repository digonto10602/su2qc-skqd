"""Assemble per-run JSONs into the per-(lattice, family, device) test files and write data/results/index.json.

  accuracy        <- data/results/<lat>/<fam>/noiseless/accuracy_runs/*.json
  noise_behaviour <- data/results/<lat>/<fam>/<dev>/noisy_runs/*.json   (accepted_counts stay in the run files)
  skqd_energy     <- computed here from the accepted samples of the noisy runs (and seeded ideal samples of the
                     same size), with skqd.skqd.ritz on the package Hamiltonian Model(Lx).H(g2, m)
  analytic_f      <- written by scripts/analytic_f.py (only indexed here)
Reviewer-opus's 9 own-reference runs (reviews/001_runs) are attached to the 2x4 accuracy files as a CROSS-CHECK only.
"""
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits  # noqa: E402
from provenance import provenance, dump  # noqa: E402

RES = os.path.join(circuits.NOISE, "data", "results")
REVIEW = os.path.join(circuits.STUDY, "reviews", "001_runs")


def expected(lat, fam):
    if lat == "2x4" and fam in circuits.FAMILY_V1:
        return len(circuits.v1_ids())
    if lat == "2x3" and fam == "frozen":
        return len(circuits.frozen_2x3_ids())
    return None


def accuracy():
    for d in sorted(glob.glob(os.path.join(RES, "*", "*", "noiseless", "accuracy_runs"))):
        lat, fam = d.split(os.sep)[-4], d.split(os.sep)[-3]
        rows = {}
        for p in sorted(glob.glob(os.path.join(d, "*.json"))):
            r = json.load(open(p))
            rows[r["circuit"]] = {k: r[k] for k in ("max_abs_dpsi_phase_aligned", "l2_dpsi_phase_aligned_incl_leak",
                                                    "leakage_noncodeword", "leakage_other_sector_codewords",
                                                    "leakage_outside_sector", "global_phase_rad", "pass_bar")}
            rows[r["circuit"]].update({"n_2q": r["counts"]["n_2q"], "n_1q": r["counts"]["n_1q"],
                                       "depth_2q": r["counts"]["depth_2q"], "n_qubits": r["counts"]["n_qubits_circuit"],
                                       "n_qubits_touched": r["counts"]["n_qubits_touched"],
                                       "aer_s": r["timing_s"]["aer"], "git_commit": r["provenance"]["git_commit"]})
        R = list(rows.values())
        summ = {"n_done": len(R), "n_expected": expected(lat, fam), "n_pass": sum(r["pass_bar"] for r in R),
                "max_abs_dpsi_max": max(r["max_abs_dpsi_phase_aligned"] for r in R),
                "leakage_outside_sector_max": max(r["leakage_outside_sector"] for r in R),
                "n_2q_min": min(r["n_2q"] for r in R), "n_2q_max": max(r["n_2q"] for r in R),
                "n_2q_mean": float(np.mean([r["n_2q"] for r in R])),
                "depth_2q_min": min(r["depth_2q"] for r in R), "depth_2q_max": max(r["depth_2q"] for r in R),
                "n_1q_mean": float(np.mean([r["n_1q"] for r in R])),
                "n_qubits": sorted({r["n_qubits"] for r in R}),
                "aer_s_min": min(r["aer_s"] for r in R), "aer_s_max": max(r["aer_s"] for r in R)} if R else {}
        cross = {}
        if lat == "2x4" and fam in circuits.CLASS_LETTER:
            L = circuits.CLASS_LETTER[fam]
            for p in sorted(glob.glob(os.path.join(REVIEW, f"{L}_B*_ref*_k*.json"))):
                if "seed" in os.path.basename(p):
                    continue
                rv = json.load(open(p))
                t = circuits.tag(rv["twoB"], rv["reference"], rv["k"])
                cross[t] = {"reviewer_max_abs_dpsi": rv["max_abs_dpsi_phase_aligned"],
                            "reviewer_leakage_outside_sector": rv["leakage_outside_sector"],
                            "reviewer_n_2q": rv["counts_recount_from_qiskit_circuit"]["n_2q"],
                            "ours_max_abs_dpsi": rows.get(t, {}).get("max_abs_dpsi_phase_aligned"),
                            "ours_n_2q": rows.get(t, {}).get("n_2q")}
        rec = {"test": "accuracy", "lattice": lat, "family": fam, "device": "noiseless",
               "engine": "qiskit_aer statevector, precision double (complex128), fusion on",
               "target": "skqd.krylov.coarse_states(term_groups(Model(Lx).terms, 4.0, mass_default(4.0)), "
                         "basis_vector(ref), dt[E3.json], k)[k] on CodewordEmbedding codewords",
               "rows": rows, "summary": summ, "reviewer_001_cross_check": cross, "provenance": provenance()}
        dump(rec, os.path.join(RES, lat, fam, "noiseless", "accuracy.json"))
        print("accuracy", lat, fam, summ.get("n_done"), "/", summ.get("n_expected"), "pass", summ.get("n_pass"))


KEEP = ("shots", "acceptance", "acceptance_ci95", "acceptance_random_level", "f_model", "f_gate", "f0_prime",
        "readout_survival_ref", "p_ref", "ref_hits", "f_hit", "f_hit_ci95", "f_hit_traj", "f_ideal",
        "f_ideal_1e-3_ci95", "b_all", "r_nc", "r_nc_ci95", "tv_accepted", "tv_accepted_floor_mean",
        "tv_accepted_floor_sd", "tv_population_pre_readout", "mean_sector_weight_pre_readout", "seed_simulator",
        "n_qubits_simulated", "sector_size")


def noise_behaviour():
    for d in sorted(glob.glob(os.path.join(RES, "*", "*", "*", "noisy_runs"))):
        parts = d.split(os.sep)
        lat, fam, dev = parts[-4], parts[-3], parts[-2]
        runs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(d, "*.json")))]
        if not runs:
            continue
        rows = {}
        for r in runs:
            row = {k: r[k] for k in KEEP}
            row["n_2q_native"] = r["budget"]["n_2q"]
            row["aer_s"] = r["timing_s"]["aer"]
            rows[r["circuit"]] = row
        S = sum(r["shots"] for r in runs)
        hits = sum(r["ref_hits"] for r in runs)
        exp_ref = sum(r["shots"] * r["p_ref"] for r in runs)
        fi = sum(r["shots"] * r["f_ideal"]["0.001"] for r in runs) / S
        summ = {"n_circuits": len(runs), "shots_total": S,
                "acceptance_mean": float(np.mean([r["acceptance"] for r in runs])),
                "f_model_mean": float(np.mean([r["f_model"] for r in runs])),
                "f0_prime_mean": float(np.mean([r["f0_prime"] for r in runs])),
                "f_hit_pooled": hits / exp_ref, "f_ideal_1e-3_pooled": fi,
                "r_nc_pooled": (hits / exp_ref) / fi if fi > 0 else None,
                "f_hit_over_f_model_pooled": (hits / exp_ref) / float(np.mean([r["f0_prime"] for r in runs])),
                "tv_accepted_mean": float(np.nanmean([r["tv_accepted"] for r in runs])),
                "tv_accepted_floor_mean": float(np.mean([r["tv_accepted_floor_mean"] for r in runs])),
                "tv_population_pre_readout_mean": float(np.mean([r["tv_population_pre_readout"] for r in runs])),
                "definitions": "pooled f_hit = sum hits / sum shots p_ref; pooled f_ideal = shot-weighted mean of "
                               "f_ideal(1e-3); r_nc_pooled = their ratio (CF_traj pooled estimator without garbage term)"}
        r0 = runs[0]
        rec = {"test": "noise_behaviour", "lattice": lat, "family": fam, "device": dev, "rows": rows, "summary": summ,
               "noise_spec_file": r0["noise_spec_file"], "noise_spec_sha256": sorted({r["noise_spec_sha256"] for r in runs}),
               "noise_model_params": r0["noise_model_params"], "engine": r0["engine"],
               "run_commits": sorted({r["provenance"]["git_commit"] for r in runs}),
               "definitions": open(os.path.join(circuits.NOISE, "scripts", "noisy_run.py")).read().split('"""')[1],
               "provenance": provenance()}
        dump(rec, os.path.join(RES, lat, fam, dev, "noise_behaviour.json"))
        print("noise_behaviour", lat, fam, dev, len(runs))
        skqd_energy(lat, fam, dev, runs)


def skqd_energy(lat, fam, dev, runs):
    """Projected (Ritz) ground energy on the union of accepted samples, per sector; noisy vs ideal samples of the
    same size (seeded), vs the exact sector ground energy (Model.reference)."""
    import targets
    from skqd.skqd import ritz
    Lx = int(lat.split("x")[1])
    m = targets.model(Lx)
    H = m["M"].H(targets.G2, m["m"])
    out = {}
    for twoB in sorted({r["twoB"] for r in runs}):
        rs = [r for r in runs if r["twoB"] == twoB]
        Bn = sorted({int(s) for r in rs for s in r["accepted_counts"]})
        rng = np.random.default_rng(4242 + twoB)
        Bi = set()
        sector = targets.sector(Lx, twoB)
        for r in rs:
            tg = targets.target(Lx, twoB, r["reference"], r["k"])
            pc = np.abs(tg[sector]) ** 2
            pc /= pc.sum()
            n_acc = int(sum(r["accepted_counts"].values()))
            draw = rng.multinomial(n_acc, pc)
            Bi |= {int(sector[i]) for i in np.nonzero(draw)[0]}
        Bi = sorted(Bi)
        E0 = float(m["M"].reference(targets.G2, twoB, m=m["m"]).E0)
        en = ritz(H, Bn).ER if Bn else None
        ei = ritz(H, Bi).ER if Bi else None
        out[f"twoB={twoB}"] = {"n_circuits": len(rs), "dim_noisy": len(Bn), "dim_ideal_samples": len(Bi),
                               "E_ritz_noisy": en, "E_ritz_ideal_samples": ei, "E0_exact": E0,
                               "dE_noisy": None if en is None else en - E0,
                               "dE_ideal_samples": None if ei is None else ei - E0,
                               "sector_dim": int(len(sector))}
    rec = {"test": "skqd_energy", "lattice": lat, "family": fam, "device": dev, "rows": out,
           "summary": {k: {kk: v[kk] for kk in ("dE_noisy", "dE_ideal_samples", "dim_noisy", "dim_ideal_samples")}
                       for k, v in out.items()},
           "method": "B = union over the family's circuits of the sector of every accepted (decoded) basis state; "
                     "E_ritz = lowest eigenvalue of H restricted to B (skqd.skqd.ritz); the ideal comparison draws, per "
                     "circuit, as many samples from the exact coarse-state distribution as the noisy run accepted "
                     "(numpy default_rng(4242 + twoB)); E0 from Model(Lx).reference(4.0, twoB)",
           "provenance": provenance()}
    dump(rec, os.path.join(RES, lat, fam, dev, "skqd_energy.json"))


def index():
    import results
    items = []
    for lat, fam, dev, test in results.list_available():
        d = results.load(lat, fam, dev, test)
        items.append({"lattice": lat, "family": fam, "device": dev, "test": test,
                      "path": os.path.relpath(os.path.join(RES, lat, fam, dev, test + ".json"), circuits.NOISE),
                      "n_rows": len(d.get("rows", {})), "created_utc": d.get("provenance", {}).get("created_utc"),
                      "git_commit": d.get("provenance", {}).get("git_commit"),
                      "noise_spec_sha256": d.get("noise_spec_sha256")})
    dump({"generated_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "items": items,
          "loader": "noise/src/results.py: load(lattice, family, device, test), table(test, lattice), list_available()"},
         os.path.join(RES, "index.json"))
    print("index", len(items))


if __name__ == "__main__":
    accuracy()
    noise_behaviour()
    index()
