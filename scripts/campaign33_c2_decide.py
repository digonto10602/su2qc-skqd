#!/usr/bin/env python3
"""
prompts/33f R1 / R2: the class-2 representation decision, written by a laptop script from committed JSONs only.

    python scripts/campaign33_c2_decide.py            # writes data/campaign33/c2_representation_decision.json
    python scripts/campaign33_c2_decide.py --check    # recompute and compare with the committed file (no write)

K2 (prompts/33d R3) asks whether the production candidate `rm_gpu_cusv` (GPU, cuStateVec, RM; C2_KCHK run 1, job
59780907, 512 shots) samples the same distribution as a trusted CPU reference.  prompts/33f R1 replaces the per-clbit
statistic: the two-sample Wald z is undefined when a small arm returns p = 0 or 1, so every clbit is judged by
Fisher's exact test on the 2 x 2 table (scipy.stats.fisher_exact, two-sided), flagged at the same per-test level
P(|Z| > 3) = 0.0027; the mean-weight statistic |z_w| <= 3 is unchanged.  R2: K2 is read on every CPU reference that
passed K4 -- the CI arms of C2_KCHK run 2 (job 59828887: Kraus 7, RM 12 shots) and the laptop arms of the qiskit 1.4.3 /
aer 0.15.1 twin (data/campaign33/c33c_diag/summary.json: Kraus 67, RM 78) -- and the decision is `rm` iff every
reference agrees (|z_w| <= 3 and no clbit flagged) and K4 says `agree` on both sides.  The Wald z and the pooled-p z
are kept beside Fisher as information; the power of each comparison is stated (33d R3's line).

Nothing harvested is edited: validation/C2_KCHK.json keeps `production_representation: blocked`; this file is the
decision of record that `run_c2_cell` reads (prompts/33f R2, S0 of prompts/33d).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from skqd.campaign33 import stats as ST  # noqa: E402

OUT = "data/campaign33/c2_representation_decision.json"
PROMPT = "prompts/33f_k2_exact_test_rm_production_and_upstream.md"
KCHK_RUN2 = "validation/C2_KCHK.json"
KCHK_RUN2_JOB = "59828887"
KCHK_RUN1 = "validation/archive/C2_KCHK_job59780907.json"
KCHK_RUN1_JOB = "59780907"
LAPTOP = "data/campaign33/c33c_diag/summary.json"
PRODUCTION_ARM = "rm_gpu_cusv"
N_SIGMA = 3.0
LEVEL = ST.THREE_SIGMA_TWO_SIDED
REPORT_DIR = "data/campaign33/aer_gpu_kraus_report"
REPRESENTATION_REASON = ("class-2 production is RM -- the Kraus channel of the record with T2 := min(T2, T1) on the four "
                         "qubits with T2 > T1 (identical super-operators on the other 17), no Kraus instruction -- because "
                         "aer 0.15.1's GPU Kraus path is unusable (C2_KCHK K1 bug_confirmed; GPU Kraus arms mutually "
                         "inconsistent across fusion / kernel options; prompts/33f R2, " + REPORT_DIR + ")")


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def load(p):
    with open(_abs(p)) as fh:
        return json.load(fh)


def sha256(p):
    with open(_abs(p), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def git_commit() -> str:
    try:
        c = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
        dirty = subprocess.call(["git", "-C", ROOT, "diff", "--quiet", "--", "src", "scripts"]) != 0
        return c + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def counts_structure(counts: dict, physical_by_clbit) -> dict:
    tot = {int(k): int(v) for k, v in counts.items()}
    return ST.garbage_structure(tot, len(physical_by_clbit), physical_by_clbit)


def wald_power(na: int, nb: int, n_sigma: float = N_SIGMA) -> float:
    """33d R3's power line: the smallest marginal difference visible at n_sigma with p = 1/2 (normal approximation)."""
    return n_sigma * math.sqrt(0.25 / na + 0.25 / nb)


def pooled_z(xa, na, xb, nb) -> list:
    out = []
    for a, b in zip(xa, xb):
        p = (a + b) / (na + nb)
        s = math.sqrt(p * (1 - p) * (1 / na + 1 / nb))
        out.append((a / na - b / nb) / s if s > 0 else 0.0)
    return out


def compare(prod: dict, ref: dict) -> dict:
    """K2 of prompts/33f R1 between the production arm and one reference: z_w (unchanged), Fisher per clbit (the
    test), the Wald and pooled z (information), the power line."""
    w = ST.structure_compare(prod, ref, N_SIGMA)
    xa, xb = ST.marginal_ones(prod), ST.marginal_ones(ref)
    na, nb = int(prod["shots"]), int(ref["shots"])
    fi = ST.fisher_marginals(xa, na, xb, nb, LEVEL)
    ok_w = abs(w["z_mean_hamming_weight"]) <= N_SIGMA
    ok_f = fi["min_p"] >= LEVEL and not fi["flagged_clbits"]
    dm = wald_power(na, nb)
    return {"shots": [na, nb],
            "mean_hamming_weight": [prod["mean_hamming_weight"], ref["mean_hamming_weight"]],
            "se_mean_hamming_weight": [prod["se_mean_hamming_weight"], ref["se_mean_hamming_weight"]],
            "z_w": w["z_mean_hamming_weight"],
            "z_w_convention": "(w_production - w_reference) / sqrt(se_production^2 + se_reference^2)",
            "weight_ok": bool(ok_w),
            "fisher": fi, "fisher_min_p": fi["min_p"], "fisher_argmin_clbit": fi["argmin_clbit"],
            "fisher_flagged_clbits": fi["flagged_clbits"], "fisher_ok": bool(ok_f),
            "wald_z_by_clbit_information": w["z_marginals_by_clbit"],
            "wald_clbits_outside_3sigma_information": w["clbits_outside"],
            "wald_note": ("information only (prompts/33f R1): the Wald z uses each arm's own variance and is undefined "
                          "where an arm has p in {0, 1} (its variance term is 0)"),
            "pooled_z_by_clbit_information": pooled_z(xa, na, xb, nb),
            "power": {"min_visible_marginal_diff": dm,
                      "line": (f"at N = {na} / {nb} shots a marginal difference below {dm:.3f} is invisible (p = 1/2, "
                               f"{N_SIGMA:g} sigma, normal approximation; prompts/33d R3's power line)")},
            "agrees": bool(ok_w and ok_f)}


def gather(kchk_run2=KCHK_RUN2, kchk_run1=KCHK_RUN1, laptop=LAPTOP) -> dict:
    """The production arm and the four CPU references, each recomputed from raw counts and checked against the
    structure its source JSON stores."""
    r1, r2, lap = load(kchk_run1), load(kchk_run2), load(laptop)
    D1, D2 = r1["data"], r2["data"]
    pa = D1["arms"][PRODUCTION_ARM]
    phys = pa["structure"]["physical_by_clbit"]
    prod = counts_structure(pa["raw_counts"]["total"], phys)
    checks = {}

    def check(name, s, stored):
        d = max([abs(s["mean_hamming_weight"] - stored["mean_hamming_weight"])]
                + [abs(a - b) for a, b in zip(s["marginals_by_clbit"], stored["marginals_by_clbit"])])
        if d > 1e-12 or s["shots"] != stored["shots"] or s["physical_by_clbit"] != stored["physical_by_clbit"]:
            raise SystemExit(f"{name}: the structure recomputed from raw counts differs from the stored one ({d})")
        checks[name] = d

    check(PRODUCTION_ARM, prod, pa["structure"])
    refs = {}
    for arm in ("kraus_cpu", "rm_cpu"):
        a = D2["arms"][arm]
        s = counts_structure(a["raw_counts"]["total"], phys)
        check(f"ci:{arm}", s, a["structure"])
        refs[f"ci_{arm}"] = {
            "kind": "CI CPU statevector (Perlmutter GPU node, separate process)", "representation": a["representation"],
            "job": KCHK_RUN2_JOB, "source": kchk_run2, "json_path": f"data.arms.{arm}.raw_counts.total",
            "sha256": sha256(kchk_run2), "versions": D2["run"].get("versions"),
            "aer_wheel": "qiskit-aer-gpu 0.15.1 (CPU statevector path)",
            "seconds_per_shot": a.get("seconds_per_shot"), "structure": s,
            "k4": {"status": (D2.get("k4") or {}).get("status"), "source": f"{kchk_run2} data.k4",
                   "against": "the laptop summary of the request commit (29 Kraus + 24 RM shots)"}}
    for arm, name in (("cpu_kraus", "kraus"), ("cpu_rm", "rm")):
        a = lap["arms"][arm]
        tot = {}
        srcs = [x.strip() for x in a["source"].split(",") if x.strip()]
        for sp in srcs:
            for k, v in load(sp)["counts"].items():
                tot[int(k)] = tot.get(int(k), 0) + int(v)
        s = counts_structure(tot, phys)
        check(f"laptop:{arm}", s, a["structure"])
        refs[f"laptop_{name}_cpu"] = {
            "kind": "laptop CPU statevector (qiskit 1.4.3 / aer 0.15.1 twin)", "representation": name,
            "job": None, "source": laptop, "json_path": f"arms.{arm} (raw counts: the segment JSONs of arms.{arm}.source)",
            "segments": srcs, "sha256": sha256(laptop), "versions": a.get("versions"),
            "aer_wheel": "qiskit-aer 0.15.1 (CPU wheel; same CPU statevector source as qiskit-aer-gpu)",
            "seconds_per_shot": a.get("seconds_per_shot"), "structure": s,
            "k4": {"status": (lap.get("k4") or {}).get("status"), "source": f"{laptop} k4",
                   "against": f"the CI CPU arms of job {KCHK_RUN2_JOB}"}}
    production = {"name": PRODUCTION_ARM, "representation": "rm", "gpu_mode": pa.get("gpu_mode"),
                  "simulator_options": pa.get("simulator_options"), "job": KCHK_RUN1_JOB, "source": kchk_run1,
                  "json_path": f"data.arms.{PRODUCTION_ARM}.raw_counts.total", "sha256": sha256(kchk_run1),
                  "versions": D1["run"].get("versions"), "seconds_per_shot": pa.get("seconds_per_shot"),
                  "structure": prod}
    return {"production": production, "references": refs, "recompute_max_abs_diff": checks, "run1": D1, "run2": D2,
            "laptop": lap}


def decide(g: dict) -> dict:
    prod = g["production"]
    refs = {}
    for name, r in g["references"].items():
        c = compare(prod["structure"], r["structure"])
        k4_ok = r["k4"]["status"] == "agree"
        refs[name] = {k: v for k, v in r.items() if k != "structure"}
        refs[name].update({"shots": r["structure"]["shots"],
                           "mean_hamming_weight": r["structure"]["mean_hamming_weight"],
                           "se_mean_hamming_weight": r["structure"]["se_mean_hamming_weight"],
                           "k2": c, "fisher_min_p": c["fisher_min_p"], "z_w": c["z_w"],
                           "agrees": c["agrees"], "k4_ok": k4_ok})
    all_ok = all(r["agrees"] and r["k4_ok"] for r in refs.values())
    D2, D1 = g["run2"], g["run1"]
    dec2 = D2.get("decision") or {}
    k3 = dec2.get("validated_kraus_gpu_path") or "none"
    # information: Fisher between the two CPU stacks per representation (K4's marginals, where the Wald z of the 7-shot
    # arm has the same p in {0, 1} artefact)
    k4_fisher = {}
    for rep in ("kraus", "rm"):
        a, b = g["references"][f"ci_{rep}_cpu"]["structure"], g["references"][f"laptop_{rep}_cpu"]["structure"]
        fi = ST.fisher_marginals(ST.marginal_ones(a), a["shots"], ST.marginal_ones(b), b["shots"], LEVEL)
        k4_fisher[rep] = {"shots": fi["shots"], "min_p": fi["min_p"], "argmin_clbit": fi["argmin_clbit"],
                          "flagged_clbits": fi["flagged_clbits"], "p_by_clbit": fi["p_by_clbit"]}
    rate = dec2.get("production_seconds_per_shot") or prod["seconds_per_shot"]
    return {
        "title": "Class-2 representation decision (prompts/33f R1/R2): production = RM, judged by Fisher's exact test",
        "prompt": PROMPT, "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "git_commit": git_commit(), "command": "python scripts/campaign33_c2_decide.py",
        "versions": {"python": platform.python_version(), "scipy": __import__("scipy").__version__,
                     "numpy": __import__("numpy").__version__},
        "production_representation": "rm" if all_ok else "blocked",
        "reference_arm": "none" if k3 == "none" else k3,
        "reference_arm_source": f"{KCHK_RUN2} data.decision.validated_kraus_gpu_path = {k3!r} (K3, job {KCHK_RUN2_JOB})",
        "kraus_gpu": f"unusable (aer 0.15.1 GPU Kraus path, see {REPORT_DIR})",
        "representation_reason": REPRESENTATION_REASON,
        "production_gpu_mode": prod["gpu_mode"],
        "production_seconds_per_shot": rate,
        "production_seconds_per_shot_source": (f"{KCHK_RUN1} data.arms.{PRODUCTION_ARM}.seconds_per_shot "
                                               f"(job {KCHK_RUN1_JOB}, {prod['structure']['shots']} shots)"),
        "bug_confirmed": D2.get("bug_confirmed"),
        "bug_confirmed_source": f"{KCHK_RUN2} data.bug_confirmed (K1, job {KCHK_RUN2_JOB})",
        "production_arm": {k: v for k, v in prod.items() if k != "structure"} | {
            "shots": prod["structure"]["shots"], "mean_hamming_weight": prod["structure"]["mean_hamming_weight"],
            "se_mean_hamming_weight": prod["structure"]["se_mean_hamming_weight"]},
        "references": refs,
        "fisher_min_p_by_reference": {k: r["fisher_min_p"] for k, r in refs.items()},
        "z_w_by_reference": {k: r["z_w"] for k, r in refs.items()},
        "power_lines": {k: r["k2"]["power"]["line"] for k, r in refs.items()},
        "k4_fisher_information": k4_fisher,
        "rule": {"K2": (f"production_representation = rm iff, for every CPU reference that passed K4, |z_w| <= "
                        f"{N_SIGMA:g} against {PRODUCTION_ARM} and no clbit has Fisher p < {LEVEL:.4g} (= P(|Z| > 3), "
                        f"the per-test level of prompts/33a; Bonferroni 20 x {LEVEL:.4g} = {20 * LEVEL:.3f}); else "
                        "blocked"),
                 "why_fisher": ("prompts/33f R1: the Wald z estimates each arm's variance separately and is undefined "
                                "when a small arm has p in {0, 1}; Fisher's exact test is the test it approximates, "
                                "needs no variance estimate, and coincides with it at large N.  No tolerance changed."),
                 "reference_arm": "K3 of prompts/33d R3: none -> production RM at 100 % of the window"},
        "recompute_max_abs_diff": g["recompute_max_abs_diff"],
        "supersedes": {"file": KCHK_RUN2, "job": KCHK_RUN2_JOB, "field": "data.decision.production_representation",
                       "value": dec2.get("production_representation"),
                       "why": ("prompts/33f R1/R2: run 2's K2 was 'blocked' by the Wald statistic of a 7-shot arm; the "
                               "harvested JSON is not edited and stays FAIL on S3/S6")},
        "inputs": {"kchk_run1": {"path": KCHK_RUN1, "job": KCHK_RUN1_JOB, "sha256": sha256(KCHK_RUN1)},
                   "kchk_run2": {"path": KCHK_RUN2, "job": KCHK_RUN2_JOB, "sha256": sha256(KCHK_RUN2)},
                   "laptop_summary": {"path": LAPTOP, "sha256": sha256(LAPTOP),
                                      "git_commit": g["laptop"].get("git_commit")}},
        "no_third_c2_kchk": ("prompts/33f R2: a third C2_KCHK (about 40 Kraus shots at 28 threads) adds fewer shots than "
                             "the laptop's 67 and cannot change the decision; not requested"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--check", action="store_true", help="recompute; compare the decision with the committed file")
    a = ap.parse_args(argv)
    doc = decide(gather())
    for name, r in doc["references"].items():
        print(f"{name:20s} N {r['shots']:3d}  w {r['mean_hamming_weight']:.3f} +- {r['se_mean_hamming_weight']:.3f}  "
              f"z_w {r['z_w']:+.2f}  Fisher min p {r['fisher_min_p']:.3f} (clbit {r['k2']['fisher_argmin_clbit']})  "
              f"flagged {r['k2']['fisher_flagged_clbits']}  K4 {r['k4']['status']}  -> {'agrees' if r['agrees'] else 'DISAGREES'}")
    print(f"production_representation: {doc['production_representation']}; reference_arm: {doc['reference_arm']}")
    if a.check:
        old = load(a.out)
        same = all(old.get(k) == doc[k] for k in ("production_representation", "reference_arm",
                                                   "fisher_min_p_by_reference", "z_w_by_reference"))
        print("check:", "identical decision" if same else "DIFFERENT from the committed file")
        return 0 if same else 1
    with open(_abs(a.out), "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
