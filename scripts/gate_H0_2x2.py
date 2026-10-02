#!/usr/bin/env python3
"""
Gate H0_2x2 (prompts/24 Stage R) -- the full 2x2 SKQD run on ibm_kingston below the signed
f >= 0.1 budget (owner decision 2026-10-02, `data/owner_decision_20261002_run_below_signed_budget.md`):
the signed family's 28 coarse-step circuits on the patch with Stage T's adopted DD configuration,
both sectors, rule D3' at the measured f, decoding, the SKQD subspace diagonalization, the Ritz
energies against the exact E0, the Weinstein / Kato-Temple certificates, and the garbage-only and
random-at-equal-size baselines.

A measurement gate: PASS iff R1-R8 (preregistered, measured, verified, consistent).  There is no
criterion on E_R(B_sig), on the baselines' percentile or on the recall -- they are the result.

Coordinator ruling on planner decision P8 (2026-10-02): the D3''-H0 lift of the seven k = 1
circuits is STRUCK; the shot plan is pure D3' at the adopted cell's f_pool.

Stages (all 0 QPU s; the submission is `scripts/h0_submit.py`, unchanged):
  plan       R.A2: the D3' shot plan at the adopted f on the day's record -> `<prep>/shot_plan.json`
             (exit 3 if 1.3 x total + 1.3 x largest job > the remaining seconds)
  predict    R.C1: `<prep>/prereg_<fp16>.json`
  prereg-md  R.C2: `reports/H0_2x2_prereg_<stamp>.md`
  assemble   R.D2 / R.F1: the analysis -> `validation/<out>.json` and the report
"""
import argparse
import glob
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gate_H0_ddtest as GT  # noqa: E402
import gate_H0_kpilot as GK  # noqa: E402

ROOT = GK.ROOT
PREP = os.path.join("data", "hardware", "H0_2x2_prep")
DDTEST = os.path.join("validation", "H0_ddtest.json")
OWNER_DECISION = os.path.join("data", "owner_decision_20261002_run_below_signed_budget.md")
DEVICE = "ibm_kingston"
G2 = 4.0
SECTORS = {"B=0": 0, "B=1": 2}
E2_ACCEPTANCE = {0: 0.00927734375, 2: 0.0048828125}     # gate E2 exhaustive (H0_kpilot.json data.circuits)
SIG_P = 1.35e-3                 # B_sig: one-sided 3 sigma Poisson level (planner's label)
GARBAGE_SEEDS = [11 + j for j in range(100)]
RANDOM_SEEDS = [23 + j for j in range(200)]
CAP_FACTOR = 1.1                # --max-qpu-seconds = ceil(1.1 x total estimate)
F_TOLERANCE = 0.30              # gate_H0.F_TOLERANCE (R5)
SIGMA_C3PRIME = 3.0             # gate_H0.SIGMA_C3PRIME (R5)
DRY_SHOTS = 1000
CRITERIA_TEXT = {
    "R1": "preregistration before data (as K1, over all jobs); the owner-decision file exists and is cited",
    "R2": ("every job DONE; usage per job and total recorded; total billed <= the reserve of R.A2; the counts files "
           "carry exactly the plan's shots; options record DD off / twirling off; the circuits carry the adopted DD "
           "(or none) as preregistered"),
    "R3": "readout: min diagonal >= DIAG_MIN",
    "R4": ("decoder round trip 0 mismatches; the sectors' random acceptance equals gate E2's exhaustive values "
           "(a_B=0 = 0.00927734375, a_B=1 = 0.0048828125)"),
    "R5": ("C3' per k = 1 circuit: reference hits >= 3 sigma above the garbage expectation; pooled f of the seven "
           "k = 1 circuits within F_TOLERANCE (0.30) of Stage T's adopted-cell f_pool"),
    "R6": "circuits: exactness of all 28 at build, schedule assertions, DD checks (i)-(v), durations; the shot plan reproduces rule D3'",
    "R7": ("data.energies, data.support, data.baselines complete with seeds; criterion 3 computed and labelled 'not a "
           "device test'; the Weinstein interval contains some exact eigenvalue of the sector"),
    "R8": "dry-run gate PASS; pytest -q tests; check_package.py OK",
}

p, rel, load_json, dump_json, now, git_commit, versions = (GK.p, GK.rel, GK.load_json, GK.dump_json, GK.now,
                                                          GK.git_commit, GK.versions)
_f, _iv = GT._f, GT._iv


def adopted_from_ddtest(path=DDTEST):
    d = load_json(p(path))
    dec = d["data"]["decision"]
    a = dec["adopted"]
    c = dec["cells"][a]
    return {"cell": a, "f_pool": c["f_pool"], "f_pool_68": c["f_pool_68"], "f_pool_95": c["f_pool_95"],
            "source": f"{path} data.decision.cells.{a}", "status": d["status"], "signed_bar": dec["signed_bar"]}


# --------------------------------------------------------------------------- pure: support / energies / baselines (tested)
def sig_support(n_by_state, mu_by_state, p_level=SIG_P):
    """{state: n}, {state: mu} -> (B_sig, per-state p-values): states whose count exceeds the
    uniform-garbage expectation at P(Poisson(mu) >= n) <= p_level."""
    from scipy.stats import poisson
    pv = {}
    for s, n in n_by_state.items():
        mu = float(mu_by_state[s])
        pv[s] = float(poisson.sf(int(n) - 1, mu)) if n > 0 else 1.0
    return sorted(s for s, v in pv.items() if v <= p_level and n_by_state[s] > 0), pv


def sector_tables(model, g2, twoB):
    """(H, sector indices, all sector eigenvalues, reference object, references list)."""
    from skqd.krylov import references
    ref = model.reference(g2, twoB)
    H = model.H(g2)
    idx = np.asarray(ref.indices, dtype=int)
    ev = np.linalg.eigvalsh(H[idx][:, idx].toarray())
    return H, idx, ev, ref, [int(x) for x in references(model.basis, twoB)]


def energy_block(H, B, refs, E0, E1, ev, dt=None):
    """Ritz energy on B u refs, certificates and the certificate properties of R7."""
    from skqd.skqd import certify, closure_diagnostic, ritz
    basis = sorted(set(int(b) for b in B) | set(int(r) for r in refs))
    res = ritz(H, basis)
    cert = certify(res, E0, E1)
    lo, hi = res.ER - res.rH, res.ER + res.rH
    contains = bool(np.any((ev >= lo - 1e-12) & (ev <= hi + 1e-12)))
    out = {"basis_size": len(basis), "E_R": float(res.ER), "E0": float(E0), "abs_error": float(abs(res.ER - E0)),
           "rH": float(res.rH), "weinstein_gap_assumed": [float(cert.weinstein[0]), float(cert.weinstein[1])],
           "weinstein_rigorous": [float(lo), float(hi)], "weinstein_contains_some_sector_eigenvalue": contains,
           "E0_inside_gap_assumed_weinstein": bool(cert.weinstein[0] - 1e-9 <= E0 <= cert.weinstein[1] + 1e-9),
           "kato_temple": None if cert.kato_temple is None else [float(x) for x in cert.kato_temple],
           "kato_temple_alpha_second_ritz": float(cert.alpha) if np.isfinite(cert.alpha) else None,
           "kato_temple_rigorous_exact_E1": None if cert.kt_rigorous is None else [float(x) for x in cert.kt_rigorous],
           "gap_assumption_holds": cert.gap_assumption_holds,
           "variational_ok": bool(res.ER >= E0 - 1e-10)}
    if dt is not None:
        out["closure_diagnostic"] = float(closure_diagnostic(H, res, float(dt)))
        out["closure_dt"] = float(dt)
    return out


def decode_table(codec, twoB):
    """int key (little-endian: bit k = qubit k) -> basis index or -1, over all 2^n strings."""
    from skqd.codec import Reject
    n = codec.n_qubits
    t = np.full(2 ** n, -1, dtype=np.int64)
    for x in range(2 ** n):
        bits = tuple((x >> k) & 1 for k in range(n))
        try:
            b, _ = codec.decode(bits, twoB)
            t[x] = int(b)
        except Reject:
            pass
    return t


def garbage_baseline(tables, shots_by_circuit, twoB_by_circuit, seeds=GARBAGE_SEEDS):
    """{seed: {twoB: (accepted states set, accepted count)}}: uniformly random strings at the same
    per-circuit shot counts through the same decoder (one RNG per seed, circuits in sorted id order)."""
    out = {}
    for s in seeds:
        rng = np.random.default_rng(int(s))
        acc = {}
        for cid in sorted(shots_by_circuit):
            tb = int(twoB_by_circuit[cid])
            t = tables[tb]
            x = rng.integers(0, t.size, int(shots_by_circuit[cid]))
            dec = t[x]
            dec = dec[dec >= 0]
            st, cnt = acc.setdefault(tb, (set(), 0))
            acc[tb] = (st | set(int(v) for v in np.unique(dec)), cnt + int(dec.size))
        out[int(s)] = acc
    return out


def random_subsets(sector_idx, refs, size, seeds=RANDOM_SEEDS):
    """{seed: basis}: random subsets of the sector's codewords with |S u refs| = size (refs always in)."""
    pool = sorted(set(int(x) for x in sector_idx) - set(refs))
    k = max(0, min(len(pool), int(size) - len(set(refs))))
    out = {}
    for s in seeds:
        rng = np.random.default_rng(int(s))
        pick = rng.choice(len(pool), size=k, replace=False) if k else np.array([], dtype=int)
        out[int(s)] = sorted(set(refs) | {pool[i] for i in pick})
    return out


def dist_summary(vals):
    v = np.asarray(vals, dtype=float)
    return {"n": int(v.size), "mean": float(v.mean()), "std": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "p2_5": float(np.percentile(v, 2.5)), "p97_5": float(np.percentile(v, 97.5)),
            "min": float(v.min()), "max": float(v.max())}


def percentile_of(x, vals):
    """Percentage of the baseline values <= x (a lower energy is better)."""
    v = np.asarray(vals, dtype=float)
    return float(100.0 * np.mean(v <= x + 1e-12))


# --------------------------------------------------------------------------- R.A2 plan
def prep_manifests(prep):
    return GK.prep_manifests(prep)


def stage_plan(args):
    import gate_S2D_levers as G
    import h0_qpu_time as qt
    from gate_H0P import load_circuit, load_manifests
    from gate_S2D import analyse_on_backend
    from h0_backends import backend_from_record
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    t0 = time.time()
    prep = args.prep
    ad = adopted_from_ddtest(args.ddtest)
    info = load_json(p(prep, "live.json"))
    full = load_json(info["record"]["path"])
    prec = load_json(info["patch_record"]["path"])
    sel = load_json(p(prep, "select.json"))
    mp = {int(k): int(v) for k, v in sel["winner_mapping"].items()}
    mans, cals = load_manifests(p(prep))
    T = {m["id"]: float(m["scheduled_duration_s"]) for m in mans}
    from h0_qpu_time import circuit_duration_s
    bk, _ = backend_from_record(full, base=FakeKingston(), strict=True)
    cal_T = float(np.mean([circuit_duration_s(load_circuit(p(prep), c), bk.target.durations(), bk.target) for c in cals]))
    rep = float(full.get("default_rep_delay_s") or 250e-6)
    plan = GT.stage_r_plan(ad["f_pool"], full, mp, cal_T, rep, family_T=T)
    est = qt.estimate(p(prep), bk, {}, GT.STAGE_R_CAL_SHOTS, shots_by_circuit=plan["shots_by_circuit"])
    f_by = {m["id"]: float(analyse_on_backend(load_circuit(p(prep), m), bk)["f"]) for m in mans}
    accts = sorted(glob.glob(p(prep, "account_check_*.json")))
    remaining = float(load_json(accts[-1])["usage"]["usage_remaining_seconds"]) if accts else None
    reserve = GT.RESERVE_FACTOR * est["total_execution_s"] + GT.RESERVE_FACTOR * plan["largest_job"]["execution_s"]
    out = {"script": "scripts/gate_H0_2x2.py --stage plan", "created": now(), "commit": git_commit(),
           "rule": "D3' (prompts/16) at the adopted cell's f_pool; the D3''-H0 lift of P8 is struck (coordinator ruling)",
           "p8_ruling": GT.P8_RULING, "owner_decision": OWNER_DECISION,
           "shots_by_circuit": plan["shots_by_circuit"], "calibration_shots": GT.STAGE_R_CAL_SHOTS,
           "calibration": {"fingerprint": prec["fingerprint"], "last_update_date": prec["last_update_date"],
                           "stamp": prec["stamp"], "path": info["patch_record"]["path"]},
           "f_by_circuit": f_by,
           "f_by_circuit_note": ("gate-only clean fraction per coarse circuit on the day's record "
                                 "(gate_S2D.analyse_on_backend): the D9 identity field the preflight re-reads; NOT the "
                                 "sizing input"),
           "f_sizing_input": {"f_pool": ad["f_pool"], "interval_68": ad["f_pool_68"], "interval_95": ad["f_pool_95"],
                              "source": ad["source"], "adopted_cell": ad["cell"], "rule": "D3'-f"},
           "N4": plan["N4"], "total_coarse_shots": plan["total_coarse_shots"], "lambda_star": plan["lambda_star"],
           "margin": plan["margin"], "floor": plan["floor"], "groups": plan["groups"], "n_jobs": plan["n_jobs"],
           "plan_total_execution_s": plan["total_execution_s"], "largest_job": plan["largest_job"],
           "estimate": {"total_execution_s": est["total_execution_s"], "total_shots": est["total_shots"],
                        "groups": est["groups"], "rep_delay_s": est["rep_delay_s"]},
           "reserve_s": reserve, "reserve_rule": "1.3 x total estimate + 1.3 x the largest job",
           "cap_s": int(math.ceil(CAP_FACTOR * est["total_execution_s"])),
           "remaining_s": remaining, "account_check": rel(accts[-1]) if accts else None,
           "fits": remaining is not None and reserve <= remaining, "runtime_s": time.time() - t0}
    dump_json(out, p(prep, "shot_plan.json"))
    for g in plan["groups"]:
        print(f"  job: {g['n_pubs']} pubs x {g['shots']} (chunk {g['chunk']}): {g['execution_s']:.2f} s")
    print(f"f {ad['f_pool']:.4f} ({ad['cell']}); N4 {plan['N4']}; coarse shots {plan['total_coarse_shots']}; estimate "
          f"{est['total_execution_s']:.2f} s (plan {plan['total_execution_s']:.2f}); largest {plan['largest_job']['execution_s']:.2f} s; "
          f"reserve {reserve:.1f} s; cap {out['cap_s']} s; remaining {remaining}: fits {out['fits']}")
    if not out["fits"]:
        print("STOP (P1): 1.3 x total + 1.3 x largest exceeds the remaining seconds -- no resizing without the owner")
        return 3
    return 0


# --------------------------------------------------------------------------- R.C1 predict
def lambda_mu_tables(prep, plan, f):
    """Per sector state: lambda_s (D3' guarantee: sum_c N_c 0.82 0.7 f p_c(s)) and mu_s (garbage)."""
    import gate_S2D_levers as G
    from skqd.skqd import READOUT_FACTOR
    mans = prep_manifests(prep)
    out = {}
    for sec, twoB in SECTORS.items():
        ms = [m for m in mans.values() if m["kind"] == "coarse_step" and m["sector"] == sec]
        lam = None
        lam_f = None
        N = 0
        for m in ms:
            d = G.ideal_distribution(m["order"], m["twoB"], m["reference"], m["theta"])
            Nc = int(plan["shots_by_circuit"][m["id"]])
            N += Nc
            r = Nc * READOUT_FACTOR * np.asarray(d["p_unnormalised"], float) * float(f)
            lam = r * plan["margin"] if lam is None else lam + r * plan["margin"]
            lam_f = r if lam_f is None else lam_f + r
            idx = d["sector_indices"]
        a = G.garbage_acceptance(twoB)
        mu = N * a / len(idx)
        out[sec] = {"sector_indices": idx, "N_sector": N, "garbage_acceptance": a, "dim": len(idx),
                    "mu_per_state": mu, "lambda_at_margin": [float(x) for x in lam],
                    "lambda_at_f": [float(x) for x in lam_f], "min_lambda_at_margin": float(np.min(lam)),
                    "Na_over_dim": N * a / len(idx)}
    return out


def stage_predict(args):
    import h0_qpu_time as qt
    from gate_H0P import DIAG_MIN
    from h0_backends import fresh_calibration, frozen_qubits_and_edges, resolve_backend
    from skqd.skqd import READOUT_FACTOR
    t0 = time.time()
    prep = args.prep
    rec, prinfo, info = GK.patch_record(prep)
    index = load_json(p(prep, "index.json"))
    sel = load_json(p(prep, "select.json"))
    plan = load_json(p(prep, "shot_plan.json"))
    mans = prep_manifests(prep)
    patch = index["patch"]
    ad = adopted_from_ddtest(args.ddtest)
    if not os.path.exists(p(OWNER_DECISION)):
        raise SystemExit(f"{OWNER_DECISION} is missing: write the owner's decision (R.0) first")
    if plan["calibration"]["fingerprint"] != rec["fingerprint"]:
        raise SystemExit("shot_plan.json was made on another patch record: re-run --stage plan")
    b = resolve_backend(DEVICE)
    qubits, edges = frozen_qubits_and_edges(p(prep))
    live = fresh_calibration(b, qubits, edges)
    if live["fingerprint"] != rec["fingerprint"]:
        print(f"STOP (D10): live {live['fingerprint'][:16]} != patch record {rec['fingerprint'][:16]}")
        return 3
    est = qt.estimate(p(prep), b, {}, GT.STAGE_R_CAL_SHOTS, shots_by_circuit=plan["shots_by_circuit"])
    cap = int(math.ceil(CAP_FACTOR * est["total_execution_s"]))
    refs_json = load_json(p("data", "references.json"))["references"]
    model_E0 = {sec: {"E0": float(refs_json[f"2x2|g2={G2}|2B={tb}"]["energies"][0]),
                      "dim": refs_json[f"2x2|g2={G2}|2B={tb}"]["dim"],
                      "support999": refs_json[f"2x2|g2={G2}|2B={tb}"]["support999"],
                      "dt": refs_json[f"2x2|g2={G2}|2B={tb}"]["dt"], "source": "data/references.json"}
                for sec, tb in SECTORS.items()}
    lm = lambda_mu_tables(prep, plan, ad["f_pool"])
    k1 = [m for m in mans.values() if m["kind"] == "coarse_step" and int(m["k"]) == 1]
    import gate_S2D_levers as G
    k1_exp = {m["id"]: {"shots": int(plan["shots_by_circuit"][m["id"]]), "p_reference": m["p_reference"],
                        "expected_reference_hits_at_f": int(plan["shots_by_circuit"][m["id"]]) * READOUT_FACTOR * ad["f_pool"] * m["p_reference"],
                        "expected_reference_hits_from_garbage": int(plan["shots_by_circuit"][m["id"]]) * G.garbage_acceptance(m["twoB"]) / m["dim"]}
              for m in k1}
    c22 = load_json(p("validation", "S2D_levers.json"))["data"]["information"]["C22_saturation"]
    pubs = [{"id": m["id"], "kind": m["kind"], "sector": m.get("sector"), "k": m.get("k"),
             "shots": int(plan["shots_by_circuit"][m["id"]]) if m["kind"] == "coarse_step" else GT.STAGE_R_CAL_SHOTS,
             "dd_cell": (m.get("dd") or {}).get("cell"), "qpy_gz_sha256": m["qpy_gz_sha256"]}
            for m in sorted(mans.values(), key=lambda m: m["id"])]
    fp16 = rec["fingerprint"][:16]
    pre = {
        "gate": "H0_2x2", "script": "scripts/gate_H0_2x2.py --stage predict", "created": now(), "commit": git_commit(),
        "versions": versions(), "qpu_seconds": 0, "prep": prep, "prep_created": index["created"],
        "owner_decision": {"path": OWNER_DECISION, "quote": open(p(OWNER_DECISION)).read().split("\n> ")[1].split("\n")[0]
                           if "\n> " in open(p(OWNER_DECISION)).read() else None},
        "calibration": {"backend": DEVICE, "fingerprint": rec["fingerprint"], "path": prinfo["path"],
                        "last_update_date": rec["last_update_date"], "stamp": rec["stamp"],
                        "full_record_path": info["record"]["path"], "full_record_fingerprint": info["record"]["fingerprint"],
                        "live_fingerprint_at_predict": live["fingerprint"],
                        "live_match_at_predict": live["fingerprint"] == rec["fingerprint"]},
        "patch": patch, "selection": {k: sel.get(k) for k in ("rule", "winner_mapping", "mapping_reproduced",
                                                               "pilot_mapping_reproduced", "patch_content_unchanged",
                                                               "patch_changed", "inherited_from")},
        "adopted_configuration": ad, "pubs": pubs, "total_shots": sum(x["shots"] for x in pubs),
        "groups": plan["groups"], "n_jobs": plan["n_jobs"], "shot_plan": rel(p(prep, "shot_plan.json")),
        "sampler_options": "--dd off --twirling off (runtime DD off; any adopted DD is in the circuits); raw bit strings",
        "execution_estimate": {"total_execution_s": est["total_execution_s"], "total_shots": est["total_shots"],
                               "rep_delay_s": est["rep_delay_s"], "groups": est["groups"],
                               "last_update_date": est["last_update_date"]},
        "reserve_s": plan["reserve_s"], "cap_s": cap, "remaining_s_at_plan": plan["remaining_s"],
        "p8_ruling": GT.P8_RULING,
        "k1_expected": k1_exp, "lambda_mu": lm,
        "C22_saturation": {"source": "validation/S2D_levers.json data.information.C22_saturation", "value": c22,
                           "day": {sec: {"N_sector": v["N_sector"], "Na_over_dim": v["Na_over_dim"],
                                         "saturates_from_noise": v["Na_over_dim"] >= 5.0} for sec, v in lm.items()}},
        "E0": model_E0, "baseline_seeds": {"garbage": GARBAGE_SEEDS, "random_equal_size": RANDOM_SEEDS},
        "B_sig_rule": (f"states whose accepted count n_s satisfies P(Poisson(mu_s) >= n_s) <= {SIG_P} with mu_s = "
                       "N_sector a / dim (planner's label: it excludes uniform noise, not near-clean false positives)"),
        "ritz_basis_convention": ("every Ritz basis is the set in question united with the sector's reference states "
                                  "(skqd.krylov.references), as gate_H0P.analyse_records does"),
        "criteria": CRITERIA_TEXT,
        "honest_reading": ("at these shot counts B_all saturates from noise and reproduces E0 whether the processor "
                           "works or not; B_sig and the baselines are where the device shows"),
        "runtime_s": time.time() - t0,
    }
    pre["readout_expected_live"] = GK.readout_expected_live(rec, patch)
    path = p(prep, f"prereg_{fp16}.json")
    if os.path.exists(path):
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel(path)], cwd=ROOT,
                                 capture_output=True).returncode == 0
        if tracked:
            raise SystemExit(f"{rel(path)} is committed as the preregistration: refusing to overwrite")
    if pre["readout_expected_live"]["min"] < DIAG_MIN:
        print(f"STOP: live readout expectation {pre['readout_expected_live']['min']:.4f} < {DIAG_MIN}")
        return 3
    dump_json(pre, path)
    print(f"wrote {rel(path)}: {len(pubs)} pubs, {pre['total_shots']} shots, estimate {est['total_execution_s']:.2f} s, "
          f"cap {cap} s, reserve {plan['reserve_s']:.1f} s, configuration {ad['cell']} (f {ad['f_pool']:.4f}); "
          f"min lambda at margin " + ", ".join(f"{s} {v['min_lambda_at_margin']:.2f}" for s, v in lm.items())
          + "; Na/dim " + ", ".join(f"{s} {v['Na_over_dim']:.1f}" for s, v in lm.items()))
    if plan["reserve_s"] > (plan["remaining_s"] or 0):
        print("STOP (P1): the reserve does not fit")
        return 3
    return 0


def stage_prereg_md(args):
    from skqd.report import md_table, write_report
    path = args.prereg or sorted(glob.glob(p(args.prep, "prereg_*.json")))[-1]
    pre = load_json(path)
    cal = pre["calibration"]
    est = pre["execution_estimate"]
    ad = pre["adopted_configuration"]
    pubs = [[x["id"], x.get("sector") or "", x.get("k") or "", x["shots"], x.get("dd_cell") or ""] for x in pre["pubs"]]
    grows = [[g["n_pubs"], g["shots"], g["chunk"], f"{g['execution_s']:.2f}"] for g in pre["groups"]]
    k1 = [[c, v["shots"], f"{v['p_reference']:.4f}", f"{v['expected_reference_hits_at_f']:.1f}",
           f"{v['expected_reference_hits_from_garbage']:.2f}"] for c, v in sorted(pre["k1_expected"].items())]
    lam = []
    for sec, v in pre["lambda_mu"].items():
        lam.append([sec, v["N_sector"], f"{v['mu_per_state']:.2f}", f"{v['min_lambda_at_margin']:.2f}",
                    f"{min(v['lambda_at_f']):.2f}", f"{v['Na_over_dim']:.1f}", pre["E0"][sec]["E0"], pre["E0"][sec]["dim"],
                    pre["E0"][sec]["support999"]])
    crit = "\n".join(f"- **{k}** {v}" for k, v in pre["criteria"].items())
    txt = f"""# H0_2x2 preregistration -- ibm_kingston, calibration `{cal['fingerprint'][:16]}`

Generated by `scripts/gate_H0_2x2.py --stage prereg-md` from `{rel(path) if os.path.isabs(path) else path}` (written
{pre['created']} at commit `{pre['commit']}`).  Every number below is read from that JSON.  Nothing was submitted when this
was written.  Prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage R).

**Owner decision (`{pre['owner_decision']['path']}`):** this run is authorised by the owner's decision of 2026-10-02 to run the
full 2x2 SKQD whether or not the signed f >= 0.1 budget is met (Stage T's read of the signed bar on the adopted cell:
{pre['adopted_configuration']['signed_bar']}): "{pre['owner_decision']['quote']}"

## Calibration, patch, configuration

- Patch record `{cal['path']}` (fingerprint `{cal['fingerprint']}`, last update {cal['last_update_date']}); live content at
  the prediction identical: {cal['live_match_at_predict']}.
- Patch {pre['patch']}; selection: {pre['selection']['rule']}
- Adopted configuration (Stage T, `{ad['source']}`): **{ad['cell']}**, f_pool {ad['f_pool']:.4f} (68 % {_iv(ad['f_pool_68'])},
  95 % {_iv(ad['f_pool_95'])}); signed bar {ad['signed_bar']}.

## Shot plan (rule D3' at the adopted f; P8 lift struck)

{pre['p8_ruling']}

{md_table(["job: pubs", "shots", "chunk", "execution (s)"], grows)}

{pre['total_shots']} shots in {pre['n_jobs']} jobs; execution estimate **{est['total_execution_s']:.2f} s** on the live
durations; reserve {pre['reserve_s']:.1f} s; `--max-qpu-seconds` {pre['cap_s']}; remaining at the plan {pre['remaining_s_at_plan']} s.
Options: {pre['sampler_options']}.

{md_table(["pub", "sector", "k", "shots", "DD cell"], pubs)}

## Expected reference hits of the k = 1 circuits at the adopted f

{md_table(["circuit", "shots", "p_ref", "expected ref hits", "garbage expectation"], k1)}

## Per sector: garbage expectation, D3' guarantee, saturation, exact E0

{md_table(["sector", "shots", "mu_s per state", "min lambda_s (0.7 margin)", "min lambda_s (at f)", "N a / dim", "exact E0",
           "dim", "support999"], lam)}

C22 (`{pre['C22_saturation']['source']}`): {json.dumps(pre['C22_saturation']['value'])}.  Day: {json.dumps(pre['C22_saturation']['day'])}.

B_sig: {pre['B_sig_rule']}.  {pre['ritz_basis_convention']}.  Baseline seeds: garbage 11..110 (100), random-at-equal-size
23..222 (200).  Honest reading: {pre['honest_reading']}.

## Criteria (verbatim)

{crit}
"""
    out = write_report(f"H0_2x2_prereg_{cal['stamp']}.md", txt)
    print(f"wrote {rel(out)}")
    return 0


# --------------------------------------------------------------------------- assemble
def stage_assemble(args):
    import gate_S2D_levers as G
    from gate_H0 import codeword_roundtrip, read_counts_dir
    from gate_H0_diag import readout_reference
    from gate_H0P import DIAG_MIN, E0_TOL, random_acceptance
    from h0_backends import calibration_diff
    from skqd.codec import Codec, Reject
    from skqd.report import GateResult, write_report
    from skqd.skqd import pooled_reference_string_test, support_metrics
    t0 = time.time()
    dry = bool(args.dry_run)
    out = args.out or ("H0_2x2_dryrun" if dry else "H0_2x2")
    prep = args.prep
    pre_path = args.prereg or GK.find_prereg(prep)
    pre = load_json(pre_path)
    plan = load_json(p(prep, "shot_plan.json"))
    missing_keys = GK.prereg_keys_ok(pre)
    mans = prep_manifests(prep)
    index = load_json(p(prep, "index.json"))
    patch = index["patch"]
    cdir = p(args.counts) if not os.path.isabs(args.counts) else args.counts
    records = read_counts_dir(cdir)
    spath = os.path.join(os.path.dirname(os.path.normpath(cdir)), "session.json")
    session = load_json(spath) if os.path.exists(spath) else None
    GK.check_mixing(dry, session, records)
    by_id = {m["id"]: (m, c) for m, c in records}
    prereg_rec = load_json(pre["calibration"]["path"])
    fx = G.factory()
    M = fx["M"]
    codec = Codec(M.basis)
    n = codec.n_qubits
    coarse = sorted(c for c, m in mans.items() if m["kind"] == "coarse_step")
    ad = pre["adopted_configuration"]

    # ---- readout (R3)
    ro = readout_reference({"records": records}, n)
    ro_survival = float(np.prod([1.0 - e for e in ro["measured_error"]])) if ro else None
    ro_live = GK.readout_expected_live(prereg_rec, patch)
    dry_k3_block = None
    if dry and ro:
        cal_phys = mans["cal_patch_all0"]["logical_to_physical"]
        exp_model = GK.snapshot_readout_model(index["common"]["backend"], cal_phys)
        meas = {int(q): (ro["P_measure_0_given_0"][i], ro["P_measure_1_given_1"][i]) for i, q in enumerate(cal_phys)}
        k3_ok, k3_rows = GK.dry_k3(meas, exp_model, int(sum(by_id["cal_patch_all0"][1].values())))
        dry_k3_block = {"ok": k3_ok, "per_qubit": k3_rows, "sigma_k": 3.0,
                        "ruling": "prompts/21a option (a): the dry-run readout form"}

    # ---- R4: round trip and random acceptance
    rt = codeword_roundtrip([(mans[c], by_id[c][1]) for c in coarse], codec)
    racc = {sec: random_acceptance(codec, tb)["fraction"] for sec, tb in SECTORS.items()}
    racc_ok = all(abs(racc[sec] - E2_ACCEPTANCE[tb]) < 1e-15 for sec, tb in SECTORS.items())

    # ---- per circuit decoding (both statistics) and the clean fraction (R5)
    circ = {c: GK.decode_counts([by_id[c][1]], mans[c]) for c in coarse}
    k1 = [c for c in coarse if int(mans[c]["k"]) == 1]
    rows = [circ[c]["row"] for c in k1]
    pool68 = pooled_reference_string_test(rows, conf=GK.CONF68)
    pool95 = pooled_reference_string_test(rows, conf=GK.CONF95)
    c3p = {c: {"reference_hits": circ[c]["reference_hits"], "garbage_expectation": circ[c]["expected_reference_hits_from_garbage"],
               "z": circ[c]["z"], "ok": circ[c]["z"] is not None and circ[c]["z"] >= SIGMA_C3PRIME} for c in k1}
    f_T = ad["f_pool"]
    f_R = pool68["f_clean"]
    rel_dev = abs(f_R - f_T) / f_T if (f_R is not None and f_T) else None
    cf = {"per_k1_circuit": {c: {k: circ[c][k] for k in ("shots", "accepted", "reference_hits", "p_reference",
                                                           "expected_reference_hits_from_garbage", "z", "P_ge",
                                                           "f_clean_reference", "f_clean_reference_68",
                                                           "f_clean_reference_95", "f_clean_mixture", "f_clean_mixture_68",
                                                           "c6_relative_deviation")} for c in k1},
          "pooled": {"f": f_R, "f_68": pool68["f_clean_68"], "f_95": pool95["f_clean_68"],
                     "n_reference": pool68["n_reference"], "expected_from_garbage": pool68["expected_from_garbage"]},
          "stage_T": {"cell": ad["cell"], "f": f_T, "f_68": ad["f_pool_68"], "f_95": ad["f_pool_95"]},
          "relative_deviation": rel_dev, "tolerance": F_TOLERANCE,
          "consistent": rel_dev is not None and rel_dev <= F_TOLERANCE, "C3prime": c3p,
          "other_k_information": {c: {k: circ[c][k] for k in ("shots", "accepted", "reference_hits", "f_clean_reference",
                                                                "f_clean_mixture")} for c in coarse if c not in k1}}

    # ---- support per sector
    support, energies, k_growth = {}, {}, {}
    tables, shots_by, twoB_by = {}, {}, {}
    ref_json = load_json(p("data", "references.json"))["references"]
    for sec, twoB in SECTORS.items():
        H, idx, ev, refobj, refs = sector_tables(M, G2, twoB)
        E0 = float(refobj.E0)
        E1 = float(refobj.energies[1])
        rj = ref_json[f"2x2|g2={G2}|2B={twoB}"]
        sec_c = [c for c in coarse if mans[c]["sector"] == sec]
        N = sum(int(sum(by_id[c][1].values())) for c in sec_c)
        a = G.garbage_acceptance(twoB)
        mu = N * a / len(idx)
        nstate = {int(s): 0 for s in idx}
        by_k = {}
        for c in sec_c:
            for bits, cnt in by_id[c][1].items():
                try:
                    b, _ = codec.decode(bits, twoB)
                except Reject:
                    continue
                nstate[int(b)] += int(cnt)
                by_k.setdefault(int(mans[c]["k"]), {}).setdefault(int(b), 0)
                by_k[int(mans[c]["k"])][int(b)] += int(cnt)
        B_all = sorted(s for s, v in nstate.items() if v > 0)
        B_sig, pv = sig_support(nstate, {s: mu for s in nstate})
        lam_tab = pre["lambda_mu"][sec]
        pos = {int(s): i for i, s in enumerate(lam_tab["sector_indices"])}
        prob = np.zeros(M.basis.dim)
        prob[refobj.indices] = np.abs(refobj.ground) ** 2
        per_state = [{"basis_index": s, "label": __import__("gate_H0P").label_of(M, s), "n_s": nstate[s], "mu_s": mu,
                      "lambda_s_margin": lam_tab["lambda_at_margin"][pos[s]], "lambda_s_at_f": lam_tab["lambda_at_f"][pos[s]],
                      "z": (nstate[s] - mu) / math.sqrt(mu) if mu > 0 else None, "p_value": pv[s],
                      "in_B_all": s in B_all, "in_B_sig": s in B_sig, "ground_state_weight": float(prob[s]),
                      "is_reference": s in refs} for s in sorted(nstate)]
        growth = []
        cum_all, cum_n = set(), {s: 0 for s in nstate}
        Ncum = 0
        for K in sorted(by_k):
            for s, v in by_k[K].items():
                cum_n[s] += v
            Ncum += sum(int(sum(by_id[c][1].values())) for c in sec_c if int(mans[c]["k"]) == K)
            sigK, _ = sig_support(cum_n, {s: Ncum * a / len(idx) for s in cum_n})
            growth.append({"k_max": K, "shots": Ncum, "B_all": sum(1 for v in cum_n.values() if v > 0),
                           "B_sig": len(sigK)})
        support[sec] = {"twoB": twoB, "dim": len(idx), "shots": N, "accepted": int(sum(nstate.values())),
                        "garbage_acceptance": a, "mu_per_state": mu, "Na_over_dim": N * a / len(idx),
                        "B_all": B_all, "B_all_size": len(B_all), "B_sig": B_sig, "B_sig_size": len(B_sig),
                        "references": refs,
                        "recall_B_all": support_metrics(sorted(set(B_all) | set(refs)), prob, 1e-3),
                        "recall_B_sig": support_metrics(sorted(set(B_sig) | set(refs)), prob, 1e-3),
                        "support999_references_json": rj["support999"],
                        "per_state": per_state, "k_growth": growth}
        dt = float(mans[sec_c[0]]["dt"])
        e_all = energy_block(H, B_all, refs, E0, E1, ev, dt)
        e_sig = energy_block(H, B_sig, refs, E0, E1, ev, dt)
        energies[sec] = {"E0_exact": E0, "E0_references_json": float(rj["energies"][0]),
                         "E0_matches_references_json": abs(float(rj["energies"][0]) - E0) < 1e-12,
                         "E1_exact": E1, "sector_eigenvalues_lowest5": [float(x) for x in ev[:5]],
                         "B_all": e_all, "B_sig": e_sig,
                         "criterion3_not_a_device_test": {"value": e_all["abs_error"], "tolerance": E0_TOL,
                                                          "holds": e_all["abs_error"] <= E0_TOL,
                                                          "label": "not a device test (C3'): B_all saturates from noise"}}
        tables[twoB] = decode_table(codec, twoB)
        for c in sec_c:
            shots_by[c] = int(sum(by_id[c][1].values()))
            twoB_by[c] = twoB

    # ---- baselines
    gb = garbage_baseline(tables, shots_by, twoB_by)
    baselines = {}
    for sec, twoB in SECTORS.items():
        H, idx, ev, refobj, refs = sector_tables(M, G2, twoB)
        E0, E1 = float(refobj.E0), float(refobj.energies[1])
        gE, gS = [], []
        for s in GARBAGE_SEEDS:
            st, _cnt = gb[s].get(twoB, (set(), 0))
            gS.append(len(st))
            gE.append(energy_block(H, sorted(st), refs, E0, E1, ev)["E_R"])
        size = energies[sec]["B_sig"]["basis_size"]
        rs = random_subsets(idx, refs, size)
        rE = [energy_block(H, rs[s], refs, E0, E1, ev)["E_R"] for s in RANDOM_SEEDS]
        e_sig = energies[sec]["B_sig"]["E_R"]
        e_all = energies[sec]["B_all"]["E_R"]
        baselines[sec] = {
            "garbage_only": {"seeds": [GARBAGE_SEEDS[0], GARBAGE_SEEDS[-1]], "n_seeds": len(GARBAGE_SEEDS),
                             "rule": "uniform random 12-bit strings at the same per-circuit shot counts through the same decoder",
                             "E_R": dist_summary(gE), "B_size": dist_summary(gS),
                             "hardware_E_R_B_all_percentile": percentile_of(e_all, gE),
                             "hardware_E_R_B_sig_percentile": percentile_of(e_sig, gE),
                             "hardware_B_all_size_percentile": percentile_of(len(support[sec]["B_all"]), gS)},
            "random_equal_size": {"seeds": [RANDOM_SEEDS[0], RANDOM_SEEDS[-1]], "n_seeds": len(RANDOM_SEEDS),
                                  "basis_size": size,
                                  "rule": "random subsets of the sector's codewords with |S u refs| = |B_sig u refs|",
                                  "E_R": dist_summary(rE), "hardware_E_R_B_sig_percentile": percentile_of(e_sig, rE)}}

    c22 = {sec: {"N": support[sec]["shots"], "Na_over_dim": support[sec]["Na_over_dim"],
                 "saturates_from_noise": support[sec]["Na_over_dim"] >= 5.0} for sec in SECTORS}

    # ---- live
    usage_s, job_ids, statuses, usage_per = None, [], [], {}
    if session:
        jobs = [j for j in session.get("jobs", []) if j.get("job_id")]
        job_ids = [j["job_id"] for j in jobs]
        statuses = [j.get("status") for j in jobs]
        usage_per = {j["job_id"]: j.get("usage_s") for j in jobs}
        us = [j.get("usage_s") for j in jobs if j.get("usage_s") is not None]
        usage_s = float(sum(us)) if us else None
    ret_fp = (session or {}).get("retrieval_calibration_fingerprint")
    ret_diff = None
    if ret_fp and ret_fp != pre["calibration"]["fingerprint"] and (session or {}).get("retrieval_calibration_file"):
        d = calibration_diff(prereg_rec, load_json(session["retrieval_calibration_file"]))
        ret_diff = {k: d[k] for k in ("n_leaves", "families", "max_ratio", "min_ratio")}
    acct = {}
    for lab, pat in (("before", p(prep, "account_check_*.json")),
                     ("after", p(os.path.dirname(os.path.normpath(cdir)), "account_check_after_*.json"))):
        fs = sorted(glob.glob(pat))
        if fs:
            a_ = load_json(fs[-1])
            acct[lab] = {"file": rel(fs[-1]), "usage": a_.get("usage")}

    # ---- criteria
    R = GateResult(out, ("the full 2x2 SKQD run on ibm_kingston below the signed budget (owner decision 2026-10-02): "
                         "both sectors, D3' at the measured f, decoding, Ritz energies vs exact E0, certificates, garbage "
                         "and random baselines (measurement gate)") + (" -- DRY RUN" if dry else ""))
    owner_ok = os.path.exists(p(OWNER_DECISION)) and (pre.get("owner_decision") or {}).get("path") == OWNER_DECISION
    k1_info = {}
    if dry:
        R.add("R1 " + CRITERIA_TEXT["R1"], f"n/a (dry run); owner file cited {owner_ok}", "device run only", owner_ok)
        shots_ok = all(int(sum(by_id[c][1].values())) == DRY_SHOTS for c in coarse)
        dd_ok = all((mans[c].get("dd") or {}).get("cell") == ad["cell"] for c in coarse)
        R.add("R2 (dry run form: the counts carry the dry run's 1000 shots; the plan's shots are checked by the preflight)",
              f"counts at {DRY_SHOTS}: {shots_ok}; circuits carry cell {ad['cell']}: {dd_ok}", "all hold", shots_ok and dd_ok)
    else:
        subs = [j.get("submitted") for j in session.get("jobs", []) if j.get("job_id")]
        first = min(subs, key=GK._utc) if subs else None
        h, tc = GK.git_commit_time(pre["commit"])
        ha, ta = GK.git_added(pre_path)
        fp_ok = (session.get("prereg_calibration_fingerprint") == pre["calibration"]["fingerprint"]
                 == session.get("calibration_fingerprint"))
        before = (tc is not None and first is not None and GK._utc(tc) < GK._utc(first)
                  and ta is not None and GK._utc(ta) < GK._utc(first))
        k1_info = {"prereg_commit": pre["commit"], "prereg_commit_time": tc, "prereg_added_in": ha,
                   "prereg_added_time": ta, "first_submitted": first, "fingerprints_equal": fp_ok,
                   "retrieval_fingerprint": ret_fp,
                   "retrieval_match": None if ret_fp is None else ret_fp == pre["calibration"]["fingerprint"],
                   "retrieval_diff": ret_diff}
        R.add("R1 " + CRITERIA_TEXT["R1"],
              f"prereg {tc} (added {ta}), first submission {first}; fingerprints equal {fp_ok}; retrieval match "
              f"{k1_info['retrieval_match']}; owner file cited {owner_ok}", "all hold",
              before and fp_ok and ret_fp is not None and not missing_keys and owner_ok)
        so = session.get("sampler_options") or {}
        opts_ok = (so.get("dynamical_decoupling") == {"enable": False}
                   and so.get("twirling") == {"enable_gates": False, "enable_measure": False})
        shots_ok = (all(int(sum(by_id[c][1].values())) == int(plan["shots_by_circuit"][c]) for c in coarse)
                    and all(int(sum(by_id[c][1].values())) == GT.STAGE_R_CAL_SHOTS for c in ("cal_patch_all0", "cal_patch_all1")))
        sha_pre = {x["id"]: x["qpy_gz_sha256"] for x in pre["pubs"]}
        dd_ok = all((mans[c].get("dd") or {}).get("cell") == ad["cell"] and mans[c]["qpy_gz_sha256"] == sha_pre[c]
                    for c in coarse)
        all_done = bool(job_ids) and all(s == "DONE" for s in statuses)
        billed_ok = usage_s is not None and usage_s <= plan["reserve_s"]
        R.add("R2 " + CRITERIA_TEXT["R2"],
              f"jobs {len(job_ids)} {statuses}; usage {usage_per} total {usage_s} s vs reserve {plan['reserve_s']:.1f}; "
              f"shots as planned {shots_ok}; options off {opts_ok}; circuits {ad['cell']} as preregistered {dd_ok}",
              "all hold", all_done and billed_ok and shots_ok and opts_ok and dd_ok)
    if dry:
        R.add("R3 readout (dry-run form, prompts/21a: within 3 sigma of the snapshot's readout model)",
              f"ok {bool(dry_k3_block and dry_k3_block['ok'])}; min diagonal {_f(None if not ro else ro['min_diagonal'])} "
              f"(information); live expectation min {ro_live['min']:.4f}", "all within 3 sigma",
              bool(dry_k3_block and dry_k3_block["ok"]) and ro_live["min"] >= DIAG_MIN)
    else:
        R.add("R3 " + CRITERIA_TEXT["R3"], None if not ro else round(ro["min_diagonal"], 4), f">= {DIAG_MIN}",
              bool(ro) and GK.device_k3(ro["min_diagonal"]))
    R.add("R4 " + CRITERIA_TEXT["R4"],
          f"{rt['mismatches']} mismatches over {rt['distinct_accepted_strings']} strings; acceptance {racc}",
          "0 and equal to E2", rt["mismatches"] == 0 and racc_ok)
    c3_ok = all(v["ok"] for v in c3p.values())
    if dry:
        R.add("R5 (dry-run form: C3' only; the consistency with Stage T's device f is evaluated on device counts)",
              f"C3' {sum(v['ok'] for v in c3p.values())}/{len(c3p)}; pooled f {_f(f_R)} vs Stage T {_f(f_T)} (information)",
              ">= 3 sigma each", c3_ok)
    else:
        R.add("R5 " + CRITERIA_TEXT["R5"],
              f"C3' {sum(v['ok'] for v in c3p.values())}/{len(c3p)} (min z {min(v['z'] for v in c3p.values()):.1f}); pooled f "
              f"{_f(f_R)} {_iv(pool95['f_clean_68'])} vs Stage T {_f(f_T)} {_iv(ad['f_pool_95'])}: deviation "
              f"{_f(rel_dev, '{:.3f}')}", f">= 3 sigma each; deviation <= {F_TOLERANCE}", c3_ok and cf["consistent"])
    ex_ok = all(mans[c]["exactness"]["ok"] and mans[c]["exactness"]["max_abs_delta"] < 1e-10
                and mans[c]["exactness"]["leakage"] < 1e-9 for c in coarse)
    sch_ok = all((mans[c].get("schedule_info") or {}).get("method") == "alap" for c in coarse)
    dd_chk_ok = all((mans[c]["dd"]["cell"] == "T0") or (mans[c]["dd"].get("checks") or {}).get("ok") is True for c in coarse)
    dur_ok = all(abs(mans[c]["scheduled_duration_s"] - mans[c]["T_total_s"]) <= 4e-9 * (1 + 1e-9) for c in coarse)
    re_shots = d3_reproduce(plan, mans)
    plan_ok = re_shots == {k: int(v) for k, v in plan["shots_by_circuit"].items()}
    R.add("R6 " + CRITERIA_TEXT["R6"],
          f"exact {ex_ok} (max |d| {max(mans[c]['exactness']['max_abs_delta'] for c in coarse):.1e}); alap {sch_ok}; "
          f"DD checks {dd_chk_ok}; durations {dur_ok}; D3' reproduced {plan_ok}", "all hold",
          ex_ok and sch_ok and dd_chk_ok and dur_ok and plan_ok)
    seeds_ok = all(baselines[s]["garbage_only"]["n_seeds"] == 100 and baselines[s]["random_equal_size"]["n_seeds"] == 200
                   for s in SECTORS)
    wein_ok = all(energies[s][b]["weinstein_contains_some_sector_eigenvalue"] for s in SECTORS for b in ("B_all", "B_sig"))
    R.add("R7 " + CRITERIA_TEXT["R7"],
          f"blocks complete; seeds {seeds_ok}; criterion 3 " + ", ".join(
              f"{s} |E_R - E0| {energies[s]['criterion3_not_a_device_test']['value']:.2e}" for s in SECTORS)
          + f" (not a device test); Weinstein contains a sector eigenvalue {wein_ok}", "all hold", seeds_ok and wein_ok)
    if dry:
        if args.skip_tests:
            R.add("R8 pytest / check_package (dry run: run before the device assembly)", "n/a (--skip-tests)", "-", True)
            checks = {"skipped": True}
        else:
            checks = G.run_checks(False)
            R.add("R8 pytest -q tests and check_package.py", f"{checks.get('pytest_summary')}; rc "
                  f"{checks.get('check_package_returncode')}", "all pass", checks["ok"])
    else:
        dp = p("validation", "H0_2x2_dryrun.json")
        dg = load_json(dp)["status"] if os.path.exists(dp) else None
        if args.skip_tests:
            checks = {"skipped": True, "ok": None}
            R.add("R8 " + CRITERIA_TEXT["R8"], f"dry run {dg}; tests skipped", "all", False)
        else:
            checks = G.run_checks(False)
            R.add("R8 " + CRITERIA_TEXT["R8"], f"dry run {dg}; pytest: {checks.get('pytest_summary')}; check_package rc "
                  f"{checks.get('check_package_returncode')}", "all pass", dg == "PASS" and checks["ok"])

    R.data = {
        "what_pass_means": ("preregistered, measured, verified, consistent; there is no criterion on E_R(B_sig), the "
                            "baselines' percentile or the recall -- they are the result"),
        "owner_decision": pre.get("owner_decision"), "dry_run": dry, "versions": versions(),
        "prereg": rel(pre_path) if os.path.isabs(pre_path) else pre_path, "prereg_created": pre["created"],
        "prereg_commit": pre["commit"], "prereg_keys_missing": missing_keys, "p8_ruling": GT.P8_RULING,
        "calibration_prereg": pre["calibration"], "patch": patch, "adopted_configuration": ad,
        "shot_plan": {"path": rel(p(prep, "shot_plan.json")), "N4": plan["N4"], "total_coarse_shots": plan["total_coarse_shots"],
                      "estimate_s": plan["estimate"]["total_execution_s"], "reserve_s": plan["reserve_s"], "cap_s": plan["cap_s"],
                      "groups": plan["groups"]},
        "counts_dir": rel(cdir), "session_file": rel(spath) if session else None,
        "live": {"job_ids": job_ids, "statuses": statuses, "usage_per_job_s": usage_per, "usage_s": usage_s,
                 "submission_fingerprint": (session or {}).get("calibration_fingerprint"),
                 "prereg_fingerprint_match": (session or {}).get("prereg_fingerprint_match"),
                 "retrieval_fingerprint": ret_fp, "retrieval_diff": ret_diff,
                 "preflight_estimate_s": (((session or {}).get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s"),
                 "sampler_options": (session or {}).get("sampler_options"), "account": acct, "R1": k1_info},
        "readout": {"block": ro, "survival_product": ro_survival, "expected_live": ro_live, "dry_run_form": dry_k3_block},
        "roundtrip": rt, "random_acceptance": racc, "clean_fraction": cf, "support": support,
        "energies": energies, "baselines": baselines, "C22": c22, "checks": checks,
    }
    R.runtime_s = time.time() - t0
    path = R.save()
    saved = load_json(path)
    name = "H0_2x2_dryrun.md" if dry else "H0_2x2_ibm_kingston.md"
    write_report(name, report_text(saved, R))
    print(R.criteria_table())
    for sec in SECTORS:
        e = energies[sec]
        print(f"{sec}: B_all {support[sec]['B_all_size']}/{support[sec]['dim']}, B_sig {support[sec]['B_sig_size']}; "
              f"E_R(B_all) {e['B_all']['E_R']:.10f}, E_R(B_sig) {e['B_sig']['E_R']:.10f}, E0 {e['E0_exact']:.10f}; "
              f"garbage pct {baselines[sec]['garbage_only']['hardware_E_R_B_sig_percentile']:.1f}, random pct "
              f"{baselines[sec]['random_equal_size']['hardware_E_R_B_sig_percentile']:.1f}")
    print(f"status {saved['status']}; f_pool {_f(f_R)} {_iv(pool95['f_clean_68'])} vs Stage T {_f(f_T)}")
    return 0 if saved["status"] == "PASS" else 1


def d3_reproduce(plan, mans):
    """R6 / R.F2: rule D3' recomputed from the plan's f and the built circuits' ideal distributions."""
    import gate_S2D_levers as G
    import h0_device_survey as ds
    from skqd.skqd import READOUT_FACTOR, poisson_lambda_star
    coarse = [m for m in mans.values() if m["kind"] == "coarse_step"]
    P = {m["id"]: G.ideal_distribution(list(G.DEFAULT_ORDER), m["twoB"], m["reference"], m["theta"])["p_unnormalised"]
         for m in coarse}
    ms = [{"id": m["id"], "sector": m["sector"], "repetitions": 1, "k": m["k"]} for m in coarse]
    shots, _n4 = GT.d3_shots(P, ms, plan["f_sizing_input"]["f_pool"], poisson_lambda_star(ds.D3_K, ds.D3_CONF),
                             ds.D3_FLOOR, ds.D3_MARGIN, READOUT_FACTOR, ds.D3_ROUND)
    return shots


def report_text(saved, R):
    from skqd.report import md_table
    D = saved["data"]
    dry = D["dry_run"]
    live = D["live"]
    cf = D["clean_fraction"]
    ro = D["readout"]["block"] or {}
    ad = D["adopted_configuration"]
    k1rows = [[c, v["shots"], v["reference_hits"], f"{v['expected_reference_hits_from_garbage']:.2f}", _f(v["z"], "{:.1f}"),
               f"{_f(v['f_clean_reference'])} {_iv(v['f_clean_reference_68'])} {_iv(v['f_clean_reference_95'])}",
               f"{_f(v['f_clean_mixture'])} {_iv(v['f_clean_mixture_68'])}"] for c, v in cf["per_k1_circuit"].items()]
    sup_rows, en_rows, base_rows, st_rows, gr_rows = [], [], [], [], []
    for sec, s in D["support"].items():
        sup_rows.append([sec, s["shots"], s["accepted"], f"{s['mu_per_state']:.2f}", f"{s['Na_over_dim']:.1f}",
                         f"{s['B_all_size']}/{s['dim']}", f"{s['B_sig_size']}/{s['dim']}",
                         f"{s['recall_B_all']['recall']:.3f}", f"{s['recall_B_sig']['recall']:.3f}",
                         s["recall_B_sig"]["exact_support_size"]])
        for b in ("B_all", "B_sig"):
            e = D["energies"][sec][b]
            en_rows.append([sec, b, e["basis_size"], f"{e['E_R']:.10f}", f"{e['E0']:.10f}", f"{e['abs_error']:.3e}",
                            f"{e['rH']:.3e}", _iv(e["weinstein_gap_assumed"], "{:.6f}"), _iv(e["kato_temple"], "{:.6f}"),
                            e["weinstein_contains_some_sector_eigenvalue"], _f(e.get("closure_diagnostic"), "{:.3e}")])
        bg = D["baselines"][sec]
        g = bg["garbage_only"]
        r = bg["random_equal_size"]
        base_rows.append([sec, "garbage-only (100 seeds 11..110)", f"{g['E_R']['mean']:.6f} +- {g['E_R']['std']:.6f}",
                          f"[{g['E_R']['p2_5']:.6f}, {g['E_R']['p97_5']:.6f}]",
                          f"{g['B_size']['mean']:.1f} [{g['B_size']['p2_5']:.0f}, {g['B_size']['p97_5']:.0f}]",
                          f"B_all {g['hardware_E_R_B_all_percentile']:.1f} / B_sig {g['hardware_E_R_B_sig_percentile']:.1f}"])
        base_rows.append([sec, f"random at |B| = {r['basis_size']} (200 seeds 23..222)",
                          f"{r['E_R']['mean']:.6f} +- {r['E_R']['std']:.6f}", f"[{r['E_R']['p2_5']:.6f}, {r['E_R']['p97_5']:.6f}]",
                          r["basis_size"], f"B_sig {r['hardware_E_R_B_sig_percentile']:.1f}"])
        for x in s["per_state"]:
            st_rows.append([sec, x["basis_index"], x["label"], x["n_s"], f"{x['mu_s']:.2f}", f"{x['lambda_s_margin']:.2f}",
                            _f(x["z"], "{:.1f}"), f"{x['p_value']:.2e}", "yes" if x["in_B_sig"] else "", f"{x['ground_state_weight']:.2e}",
                            "ref" if x["is_reference"] else ""])
        for gq in s["k_growth"]:
            gr_rows.append([sec, gq["k_max"], gq["shots"], gq["B_all"], gq["B_sig"]])
    acct = live.get("account") or {}
    ub = (acct.get("before") or {}).get("usage") or {}
    ua = (acct.get("after") or {}).get("usage") or {}
    od = D.get("owner_decision") or {}
    title = "dry run (local Aer on the FakeKingston snapshot at 1000 shots per pub; a path check)" if dry else "ibm_kingston"
    return f"""# Gate {saved['gate']} -- the full 2x2 SKQD run, {title}

**Status: {saved['status']}** -- `scripts/gate_H0_2x2.py --stage assemble --counts {D['counts_dir']}{' --dry-run' if dry else ''} --out {saved['gate']}`.
Runtime {saved['runtime_s']:.0f} s.  Every number below is computed by the script from the raw counts and `{D['prereg']}` and is stored
in `validation/{saved['gate']}.json`.  Prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (Stage R).

**Owner decision (`{od.get('path')}`):** this run is authorised by the owner's decision of 2026-10-02 to run the full 2x2
SKQD whether or not the signed f >= 0.1 budget is met (Stage T's read of the signed bar on the adopted cell: {ad['signed_bar']}):
"{od.get('quote')}"

## 0. What PASS means

{D['what_pass_means']}.  {D['p8_ruling']}

## 1. Live

| item | value |
|---|---|
| jobs / status | {live['job_ids']} / {live['statuses']} |
| usage per job (s) / total | {live['usage_per_job_s']} / {live['usage_s']} |
| preflight estimate (s) / reserve / cap | {live['preflight_estimate_s']} / {D['shot_plan']['reserve_s']:.1f} / {D['shot_plan']['cap_s']} |
| fingerprint at prereg / submission / retrieval | `{D['calibration_prereg']['fingerprint'][:16]}` / `{(live['submission_fingerprint'] or 'n/a')[:16]}` / `{(live['retrieval_fingerprint'] or 'n/a')[:16]}` |
| retrieval diff | {live['retrieval_diff']} |
| account before / after | {ub.get('usage_consumed_seconds')} s used ({ub.get('usage_remaining_seconds')} left) / {ua.get('usage_consumed_seconds')} s used ({ua.get('usage_remaining_seconds')} left) |
| options | {live['sampler_options']} |
| configuration | Stage T cell {ad['cell']} (f {ad['f_pool']:.4f}, 95 % {_iv(ad['f_pool_95'])}) |
| shot plan | N4 {D['shot_plan']['N4']}, {D['shot_plan']['total_coarse_shots']} coarse shots, estimate {D['shot_plan']['estimate_s']:.2f} s |

## 2. Readout

Smallest confusion diagonal {_f(ro.get('min_diagonal'))}; survival product {_f(D['readout']['survival_product'])}; live expectation min
{D['readout']['expected_live']['min']:.4f}.

## 3. Decoder round trip and random acceptance

{D['roundtrip']['mismatches']} mismatches over {D['roundtrip']['distinct_accepted_strings']} accepted strings; random acceptance
{D['random_acceptance']} (gate E2: 0.00927734375 / 0.0048828125).

## 4. Clean fraction (the seven k = 1 circuits)

{md_table(["circuit", "shots", "ref hits", "garbage exp.", "z", "f reference [68 %] [95 %]", "f mixture [68 %]"], k1rows)}

Pooled f = **{_f(cf['pooled']['f'])}** (68 % {_iv(cf['pooled']['f_68'])}, 95 % {_iv(cf['pooled']['f_95'])}); Stage T's adopted cell
{cf['stage_T']['cell']}: {_f(cf['stage_T']['f'])} (95 % {_iv(cf['stage_T']['f_95'])}); relative deviation {_f(cf['relative_deviation'], '{:.3f}')}
(tolerance {cf['tolerance']}).

## 5. Support per sector

{md_table(["sector", "shots", "accepted", "mu_s", "N a / dim", "B_all", "B_sig", "recall B_all", "recall B_sig", "|S_0.999|"], sup_rows)}

k-resolved growth (cumulative over k <= k_max):

{md_table(["sector", "k_max", "shots", "B_all", "B_sig"], gr_rows)}

Per state:

{md_table(["sector", "basis", "label", "n_s", "mu_s", "lambda_s (0.7)", "z", "P(Poisson(mu) >= n)", "in B_sig", "|<s|Omega>|^2", ""], st_rows)}

## 6. Energies (Ritz basis = set u sector references)

{md_table(["sector", "set", "|basis|", "E_R", "E0 exact", "|E_R - E0|", "r_H", "Weinstein (gap-assumed)", "Kato-Temple",
           "Weinstein contains an eigenvalue", "closure"], en_rows)}

Criterion 3 of prompts/07 on B_all: """ + "; ".join(
        f"{s} |E_R - E0| = {D['energies'][s]['criterion3_not_a_device_test']['value']:.2e} (holds "
        f"{D['energies'][s]['criterion3_not_a_device_test']['holds']})" for s in D["energies"]) + f""" -- **not a device test** (C3').

## 7. Baselines

{md_table(["sector", "baseline", "E_R mean +- std", "E_R 2.5-97.5 %", "|B|", "hardware percentile (E_R <= hardware)"], base_rows)}

## 8. C22 saturation

{json.dumps(D['C22'])} (rule: N a / dim >= 5 fills the sector from accidentally-valid noise alone).

## 9. Honest limits

- Stage R runs under the owner's decision whatever the signed budget says; the signed bar was read only on Stage T's two
  k = 1 circuits, never on the family (k = 2-4 are information); the sectors saturate from accidentally-valid noise at these
  shot counts (C22 above), so E_R(B_all) reproducing E0 is a property of the decoder (gate E2), not of the device; B_sig
  excludes uniform noise but not near-clean false positives (M4.4); the garbage and random baselines are the controls that
  make the number readable.
- Seven k = 1 circuits are not a family-level statement at other k; the k = 2-4 cells' f is information (C6 ruling).
- One calibration content; drift between submission and retrieval is reported, not corrected.

## 10. Criteria

{R.criteria_table()}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("plan", "predict", "prereg-md", "assemble"))
    ap.add_argument("--prep", default=PREP)
    ap.add_argument("--ddtest", default=DDTEST)
    ap.add_argument("--prereg", default=None)
    ap.add_argument("--counts", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    return {"plan": stage_plan, "predict": stage_predict, "prereg-md": stage_prereg_md,
            "assemble": stage_assemble}[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
