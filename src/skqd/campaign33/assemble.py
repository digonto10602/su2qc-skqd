"""
prompts/33 A7: assemble the campaign -- validation/C33_campaign.json and reports/C33_campaign_report.md
(validation/dryrun/... and reports/dryrun/... for the laptop dry run), generated from the token JSONs and
the old results' JSONs only.  Nothing is typed by hand.

* the campaign matrix: class x scenario x variant -> f_hit, f_hat_ideal, f0, accepted, |B|, recall,
  E_R - E0, certificate width, CV flags, s/shot, node-hours;
* the a/b merges of the S3-quota runs (C4_F4_*, C4_F8_*): the per-circuit accepted counts summed, then
  B_all, Ritz, recall of S999 and Weinstein at 2e5 shots per sector -> P15 (the gate-S3 criterion) for F8
  and the S1 redo for F4;
* the comparison table of section 6 (one row per old result, Delta, sigma, verdict).
"""
from __future__ import annotations

import json
import os
import time

import numpy as np

from . import stats as ST
from . import tokens as TK

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GATE = "C33_campaign"


def load(p):
    p = p if os.path.isabs(p) else os.path.join(ROOT, p)
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def token_json(tok, dry):
    return load(os.path.join("validation", "dryrun" if dry else "", tok + ".json"))


def _g(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


# --------------------------------------------------------------------------- the S3-quota merges
def merge_halves(tokens, dry, P=None):
    """{F4|F8: {sector: merged reading}} from the a/b halves' accepted_counts_by_circuit."""
    out = {}
    for f in ("F4", "F8"):
        for sec, tb in (("B=0", 0), ("B=1", 2)):
            a = token_json(f"C4_{f}_B{tb // 2}a", dry)
            b = token_json(f"C4_{f}_B{tb // 2}b", dry)
            key = f"{f}|{sec}"
            if a is None or b is None:
                out[key] = {"status": "pending", "halves_present": [a is not None, b is not None]}
                continue
            fa, fb = a["data"]["frun"], b["data"]["frun"]
            n_full = None
            if P is None:
                from .analysis import Physics
                P = Physics()
            S = P.S[sec]
            n_full = np.zeros(P.M.basis.dim, dtype=np.int64)
            shots = 0
            for fr in (fa, fb):
                for c, acc in fr["accepted_counts_by_circuit"].items():
                    for i, v in acc.items():
                        n_full[int(i)] += int(v)
                shots += int(sum(fr["shots_done"].values()))
            from .analysis import certificate_reading, skqd_point
            pt = skqd_point(P, sec, n_full, shots, with_random=False)
            cert = certificate_reading(sec, pt)
            w = pt["all"]["weinstein"]
            inside_w = bool(pt["all"]["E0_in_weinstein"])
            p15 = bool(pt["all"]["recall_S999"] >= 0.9 and inside_w)
            out[key] = {"status": "merged", "shots": shots, "family": fa["family"], "scenario": fa["scenario"],
                        "B_all_size": pt["B_all_size"], "recall_S999": pt["all"]["recall_S999"],
                        "W": pt["all"]["W"], "E_R_minus_E0": pt["all"]["err"], "weinstein": w,
                        "E0_in_weinstein": inside_w, "kt_rigorous": pt["all"]["kt_rigorous"],
                        "certificate_ruling2": cert,
                        "P15_gate_S3_criterion": {"recall_min": 0.9, "pass": p15,
                                                  "rule": "recall of the 99.9 % support >= 0.9 with 2e5 shots per sector "
                                                          "and E0 inside the Weinstein interval (s3_device_model.RECALL_MIN, "
                                                          "EPS_SUPPORT)"} if f == "F8" else None,
                        "dry_run_inputs": bool(a["data"].get("dry_run") or b["data"].get("dry_run"))}
    return out, P


# --------------------------------------------------------------------------- the matrix
def matrix_rows(tokens, dry):
    rows = []
    for tok in tokens:
        d = token_json(tok, dry)
        if d is None:
            rows.append({"token": tok, "status": "pending"})
            continue
        D = d["data"]
        run = D.get("run", {})
        base = {"token": tok, "class": D.get("class"), "status": d["status"],
                "s_per_shot": run.get("seconds_per_shot"), "wall_s": run.get("wall_seconds"),
                "node_hours": run.get("node_hours_charged_shared_qos"), "dry_run": D.get("dry_run")}
        if tok.startswith("C4_FCELLS"):
            for key, c in (D.get("cells") or {}).items():
                pk = _g(c, "stats", "pooled_k1") or {}
                r = dict(base)
                r.update({"scenario": c["scenario"], "variant": c["family"], "f_hit": pk.get("f_hit"),
                          "f_hit_ci95": pk.get("f_hit_ci"), "f_hat_ideal": pk.get("f_hat_ideal"),
                          "f_hat_ideal_ci95": pk.get("f_hat_ideal_ci"),
                          "f0_B0_k1": _g(c, "f0", "B0_ref25_k1", "f0"),
                          "accepted_fraction_B0_k1": _g(c, "stats", "per_circuit", "B0_ref25_k1", "accepted_fraction")})
                rows.append(r)
        elif "frun" in D:
            fr = D["frun"]
            cert = fr["at_N"]["certificate"]
            pk = _g(fr, "clean_fraction", "pooled_k1") or {}
            r = dict(base)
            r.update({"scenario": fr["scenario"], "variant": fr["family"], "sector": fr["sector"],
                      "kind": fr["kind"], "half": fr["half"], "plan_tier": fr["plan_tier"],
                      "shots": fr["at_N"]["shots"], "B_all": fr["at_N"]["B_all_size"],
                      "recall_S999": cert["recall_S999"], "E_R_minus_E0": cert["E_R_minus_E0"],
                      "certificate": cert["type"], "width": cert["width"], "E0_inside": cert["E0_inside"],
                      "f_hit": pk.get("f_hit"), "f_hat_ideal": pk.get("f_hat_ideal"),
                      "f_hat_ideal_ci95": pk.get("f_hat_ideal_ci"), "CV": fr.get("CV1_CV5"),
                      "cv3": fr.get("cv3_status")})
            rows.append(r)
        elif tok.startswith("C2_") and tok != "C2_CAL":
            for k, v in (D.get("per_run") or {}).items():
                r = dict(base)
                r.update({"scenario": D.get("cell"), "variant": D.get("family"), "run": k,
                          "accepted": v["accepted"], "reference_hits": v["reference_hits"], "shots": v["shots"],
                          "f0_twirled": _g(v, "f0_twirled", "f0"),
                          "P_K1_accepted": v.get("P_measured_accepted_under_model"),
                          "P_K1_hits": v.get("P_measured_hits_under_model")})
                rows.append(r)
        else:
            rows.append(base)
    return rows


# --------------------------------------------------------------------------- the comparison table (section 6)
def comparisons(dry, merged):
    rows = []

    def tj(t):
        return token_json(t, dry)

    s1 = load("validation/S1.json")["data"]
    s3 = load("validation/S3.json")["data"]
    # S1 -> F4 (E7(0.10), 2e5 per sector)
    for sec, tb in (("B=0", 0), ("B=1", 2)):
        old = s1["production"].get(f"{sec}|f=0.1", {})
        new = merged.get(f"F4|{sec}", {})
        rows.append({"old": f"S1 production {sec} f=0.1 (proxy noise, 2e5/sector)", "redo": "C4_F4_* (merged a+b)",
                     "status": new.get("status", "pending"),
                     "recall": ST.compare(new.get("recall_S999"), None, old.get("recall"), None),
                     "B_size": ST.compare(new.get("B_all_size"), None, old.get("size"), None),
                     "E_R_minus_E0": ST.compare(new.get("E_R_minus_E0"), None, old.get("err"), None),
                     "weinstein_width": ST.compare(None if new.get("weinstein") is None else
                                                   new["weinstein"][1] - new["weinstein"][0], None,
                                                   None if old.get("weinstein") is None else
                                                   old["weinstein"][1] - old["weinstein"][0], None),
                     "note": "old value has one seed: no_old_uncertainty"})
    # S3 -> C4_FCELLS_B faithful redo and C4_F8
    fb = tj("C4_FCELLS_B")
    redo = _g(fb, "data", "s3_redo") or {}
    if redo:
        lo, hi = ST.wilson(redo["accepted"], redo["shots"])
    rows.append({"old": "S3 (job 58771538): E8 on IR-L3-RZZ, B=0, 32 x 100, seed 11", "redo": "C4_FCELLS_B s3_redo",
                 "status": "done" if redo else "pending",
                 "yield": ST.compare(redo.get("yield"), [lo, hi] if redo else None, s3["yield"],
                                     list(ST.wilson(s3["accepted"], s3["total_shots"]))) if redo else None,
                 "accepted_in_binomial_band": redo.get("inside"), "same_count_as_S3": redo.get("equal_to_s3_count"),
                 "s3_s_per_shot": s3["cost"]["seconds_per_shot_best_ladder"],
                 "new_s_per_shot": _g(fb, "data", "run", "seconds_per_shot"),
                 "s3_peak_mib": s3["run"]["gpu_telemetry"]["peak_memory_mib"],
                 "s3_mean_util": s3["run"]["gpu_telemetry"]["mean_utilization_pct"]})
    rows.append({"old": "S3 criterion (never evaluated)", "redo": "C4_F8_* merged",
                 "status": merged.get("F8|B=0", {}).get("status", "pending"),
                 "P15": {sec: _g(merged.get(f"F8|{sec}", {}), "P15_gate_S3_criterion", "pass") for sec in ("B=0", "B=1")}})
    sm = load("validation/S3_smoke.json")["data"]
    rows.append({"old": f"S3_smoke: B=1, {sm['total_shots']} shots, recall {sm['support']['recall_99.9pct']:.4f}",
                 "redo": "C4_F8_B1*", "status": "superseded",
                 "note": "the 24-shot pipeline smoke number has no comparison value; the 2e5-shot criterion replaces it"})
    for f in ("1e-3", "3e-3"):
        d = load(f"validation/L4_p2_{f}.json")
        rows.append({"old": f"L4_p2_{f}: {(d or {}).get('title', 'absent')}", "redo": "not redone",
                     "status": "not_applicable", "note": "these are 2x2 runs, not 2x3"})
    # Q0P A6 dry run -> C4_FCELLS_A E1 x O0
    pr = load("data/quantinuum/q0p_stages/predict.json")["dryrun"]
    fa = tj("C4_FCELLS_A")
    cell = _g(fa, "data", "cells", "E1|NAT-O0", "stats", "pooled_k1") or {}
    rows.append({"old": f"Q0P A6 dry run: {pr['reference_hits_total']} hits / {pr['shots_used']}, f_hit "
                        f"{pr['pooled_f_estimate']:.4f}", "redo": "C4_FCELLS_A E1 x NAT-O0 (k = 1 circuits)",
                 "status": "done" if cell else "pending",
                 "f_hit": ST.compare(cell.get("f_hit"), cell.get("f_hit_ci"), pr["pooled_f_estimate"], pr["pooled_f_95"]),
                 "P11_vs_CF_traj": _g(fa, "data", "P11")})
    # CF_traj -> C4_CF
    cf = load("validation/CF_traj.json")["data"]
    rnc = load("data/cf_trajectories/r_nc.json")
    new = tj("C4_CF")
    rows.append({"old": f"CF_traj pooled r(1e-3) {rnc['pooled_r_point']:.4f} {rnc['pooled_r_ci95']}, r_nc {rnc['r_nc']:.4f}",
                 "redo": "C4_CF (K = 2000 per arm)", "status": "done" if new else "pending",
                 "pooled_r": ST.compare(_g(new, "data", "pooled", "r_d1e-03", "value"),
                                        _g(new, "data", "pooled", "r_d1e-03", "ci95"),
                                        rnc["pooled_r_point"], rnc["pooled_r_ci95"]),
                 "r_nc_new": _g(new, "data", "r_nc_new"),
                 "owner_item": _g(new, "data", "owner_item_r_nc_outside_old_interval")})
    # CV_2x3_plan / Q0P_2x3_plan P3 -> C4_F5
    cvp = load("validation/CV_2x3_plan.json")["data"]["criteria_by_seed"]["f=0.10"]
    q3 = load("validation/Q0P_2x3_plan.json")["data"]["emulated_check"]["per_seed"]
    for sec, tb in (("B=0", 0), ("B=1", 2)):
        f5 = tj(f"C4_F5_B{tb // 2}")
        fr = _g(f5, "data", "frun") or {}
        old_rec = [v["all"]["recall_S999"] for v in q3[sec].values()]
        old_cv1 = [v["CV1"]["dE"] for v in cvp[sec].values()]
        new_cv1 = _g(fr, "cv", "criteria", "CV1", "dE")
        rows.append({"old": f"CV_2x3_plan / Q0P_2x3_plan P3 {sec} f=0.10 (proxy at 0.7 f, 3 seeds)",
                     "redo": f"C4_F5_B{tb // 2}", "status": "done" if fr else "pending",
                     "recall_S999": ST.compare(_g(fr, "at_N", "certificate", "recall_S999"), None,
                                               float(np.mean(old_rec)), None, old_sigma=ST.seed_spread_sigma(old_rec),
                                               old_sigma_label="seed_spread"),
                     "CV1_dE": ST.compare(new_cv1, None, float(np.mean(old_cv1)), None,
                                          old_sigma=ST.seed_spread_sigma(old_cv1), old_sigma_label="seed_spread")})
    # K0 / K1 -> C2_*
    k1 = load("validation/K1_2x3_fpilot.json")["data"]["circuits"]
    for tok in ("C2_GATE", "C2_ECHO", "C2_STAR", "C2_XY4", "C2_COH"):
        d = tj(tok)
        per = _g(d, "data", "per_run") or {}
        rows.append({"old": "K1 measured 0 / 0 hits, " + " / ".join(str(k1[c]["accepted"]) for c in k1)
                            + " accepted of 1e5; K0/K1 analytic predictions", "redo": tok,
                     "status": "done" if per else "pending",
                     "per_run": {k: {"accepted_per_1e5": v["scaled_to_1e5"]["accepted"],
                                     "hits_per_1e5": v["scaled_to_1e5"]["reference_hits"],
                                     "P_K1_accepted": v["P_measured_accepted_under_model"],
                                     "P_K1_hits": v["P_measured_hits_under_model"],
                                     "prereg_expected_hits_1e5": v["prereg_expected_hits_1e5"]} for k, v in per.items()}})
    # class 3 engines vs C3_AER: two-sample TV distance with its multinomial null (prompts/33 2.4)
    aer = _g(tj("C3_AER"), "data", "noiseless", "stage_e_counts") or {}
    ex = load("data/campaign33/exact/stage_e.json") or {}
    for tok in ("C3_LE", "C3_SEL"):
        d = tj(tok)
        cnt = _g(d, "data", "counts") or {}
        per = {}
        for cid, c in cnt.items():
            if cid not in aer:
                continue
            a = {int(k): v for k, v in aer[cid].items()}
            b = {int(k): v for k, v in c.items()}
            probs = {int(k): v for k, v in ex["circuits"][cid]["probabilities"].items()}
            null = ST.tv_expectation_multinomial(probs, sum(a.values()), sum(b.values()))
            tv = ST.tv_distance(a, b)
            per[cid] = {"tv": tv, "null_mean": null["mean"], "null_p95": null["p95"],
                        "within_null_p95": bool(tv <= null["p95"])}
        rows.append({"old": "C3_AER (Aer, noiseless, NAT-O0)", "redo": tok, "status": "done" if per else "pending",
                     "tv_vs_C3_AER": per})
    s2d = load("validation/S2D.json")["data"]["2x3"]
    e8 = _g(tj("C4_FCELLS_B"), "data", "cells") or {}
    rows.append({"old": f"S2D 2x3 declared-model f {s2d['f']['mean']:.4f} (virtual Rz {s2d['f_virtual_rz']['mean']:.4f})",
                 "redo": "C4_FCELLS_B E7 cells (and E8 on IR-L3-RZZ in the S3 redo)",
                 "status": "done" if e8 else "pending",
                 "f_hit_E7_0.10_O0": _g(e8, "E7_0.10|NAT-O0", "stats", "pooled_k1", "f_hit"),
                 "analytic_f_virtual_rz_mean": s2d["f_virtual_rz"]["mean"],
                 "note": "f_hit vs the analytic f: the near-clean excess (expected r ~ 1.07)"})
    return rows


def main(dry=False):
    from skqd.report import GateResult, md_table, write_report
    t0 = time.time()
    tokens = list(TK.load_tokens())
    present = {t: token_json(t, dry) is not None for t in tokens}
    statuses = {}
    for t in tokens:
        d = token_json(t, dry) or {}
        # an engine token dropped by data/campaign33/engines.json (its engine cannot run) is DROPPED, not failing
        statuses[t] = ("DROPPED" if (d.get("data") or {}).get("dropped") else d.get("status"))
    merged, P = merge_halves(tokens, dry)
    rows = matrix_rows(tokens, dry)
    comp = comparisons(dry, merged)
    gate = ("dryrun/" if dry else "") + GATE
    R = GateResult(gate, ("DRY RUN skeleton: " if dry else "") +
                   "2x3 four-class campaign: matrix, S3-quota merges and the comparison with every earlier 2x3 result")
    R.add("every token JSON present", f"{sum(present.values())} of {len(tokens)}", "33 of 33", all(present.values()))
    R.add("every present token PASS (tokens dropped by data/campaign33/engines.json excluded)",
          {t: s for t, s in statuses.items() if s and s != "PASS"} or "all PASS",
          "no FAIL", all(s in ("PASS", "DROPPED") for s in statuses.values() if s))
    R.add("comparison table generated (section 6 rows)", len(comp), ">= 10 rows", len(comp) >= 10)
    if not dry:
        for sec in ("B=0", "B=1"):
            m = merged.get(f"F8|{sec}", {})
            if m.get("status") == "merged":
                R.add(f"P15 gate-S3 criterion {sec}: recall S999 >= 0.9 at 2e5 and E0 inside Weinstein",
                      [m["recall_S999"], m["E0_in_weinstein"]], ">= 0.9 and inside", m["P15_gate_S3_criterion"]["pass"])
    R.data = {"dry_run": dry, "tokens": tokens, "present": present, "statuses": statuses, "merged_s3_quota": merged,
              "matrix": rows, "comparison": comp, "prompt": "prompts/33 A7 / section 6",
              "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    R.runtime_s = time.time() - t0
    R.save()
    banner = ("\n> **DRY RUN SKELETON** — assembled from the laptop dry-run JSONs (validation/dryrun/), every number "
              "is a reduced-size path check, not a campaign result.\n" if dry else "")
    mat = [[r.get("token"), r.get("status"), r.get("scenario"), r.get("variant"), r.get("sector"), r.get("f_hit"),
            r.get("f_hat_ideal"), r.get("recall_S999"), r.get("E_R_minus_E0"), r.get("s_per_shot"), r.get("node_hours")]
           for r in rows]

    def f(x):
        return f"{x:.4g}" if isinstance(x, float) else str(x)
    comp_rows = [[c["old"], c["redo"], c["status"],
                  "; ".join(f"{k}: {v.get('verdict')} (Delta {f(v.get('delta'))})" for k, v in c.items()
                            if isinstance(v, dict) and "verdict" in v) or "-"] for c in comp]
    merged_rows = [[k, v.get("status"), v.get("shots"), v.get("recall_S999"), v.get("E0_in_weinstein"),
                    _g(v, "P15_gate_S3_criterion", "pass")] for k, v in merged.items()]
    text = "\n".join([
        f"# {R.title}", "", f"**Status: {'PASS' if R.passed else 'FAIL'}** — `python scripts/campaign33.py --stage "
        f"assemble{' --dry-run' if dry else ''}`; prompt prompts/33 (A7, section 6).", banner,
        "## Campaign matrix", "", md_table(["token", "status", "scenario", "variant", "sector", "f_hit", "f_hat_ideal",
                                           "recall S999", "E_R - E0", "s/shot", "node-hours"],
                                          [[f(x) for x in r] for r in mat]), "",
        "## S3-quota merges (a + b halves)", "",
        md_table(["run|sector", "status", "shots", "recall S999", "E0 in Weinstein", "P15"],
                 [[f(x) for x in r] for r in merged_rows]), "",
        "## Comparison with the earlier 2x3 results (prompts/33 section 6)", "",
        md_table(["old result", "redo", "status", "difference (verdict)"], comp_rows), "",
        "## Criteria", "", R.criteria_table(), "",
        f"Every number above is read from validation/*.json and data/*.json by "
        f"`src/skqd/campaign33/assemble.py` and stored in `validation/{gate}.json`.", ""])
    write_report(("dryrun/" if dry else "") + "C33_campaign_report.md", text)
    print(R.criteria_table())
    return 0 if R.passed else 1
