#!/usr/bin/env python3
"""
The 2x2 clean-fraction information block (prompts/28 B4 as amended by prompts/29 3(3) and Part B'; owner
decision 3a of 2026-10-05: "the 2x2 qualification is accepted").

Reads every recorded 2x2 clean-fraction value (never edits a record) and labels the statistic it is:
f_hit, the reference-hit fraction, an estimator of the ideal-sample fraction f_ideal with a gate-noise bias
of 1.05-1.12 (gate CF_traj, A6 channel) and an unknown bias under idle dephasing (the A5 arm of CF_traj,
a Markovian 2x2 model at both ends of the T2 bracket, is the only model estimate).  Applies the corrected
statistic f_hat_ideal = f_hit / r_nc (skqd.skqd.corrected_clean_fraction, r_nc of
data/cf_trajectories/r_nc.json) to every value that carries a 95 % interval, and reads the 2x2 signed bar
under both the recorded rule of H0_ddtest / H0_2x2 (GO iff the lower 95 % bound >= 0.1) and the v3 rule
of the 2x3 Stage E / P (GO iff lower >= 0.05 and point >= 0.10).

Writes validation/CF_estimator_2x2_info.json + reports/CF_estimator_2x2_information_20261003.md (the file
name prompts/28 B4 gives).  Runtime: seconds.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from skqd.report import ROOT, GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import corrected_clean_fraction  # noqa: E402

GATE = "CF_estimator_2x2_info"
PROMPT = ("prompts/28_2x3_shot_rule_and_clean_fraction_estimator.md B4 as amended by "
          "prompts/29_cf_traj_reruling_ideal_sample_fraction.md 3(3) and Part B'")
RECORDS = ("validation/H0_kpilot.json", "validation/H0_ddtest.json", "validation/H0_2x2.json",
           "validation/H0_model.json", "validation/CF_traj.json", "data/cf_trajectories/r_nc.json")
BAR, BAR_LO = 0.10, 0.05
PLANNER_R_NC = 1.10                 # prompts/29 3(3): the planner's arithmetic used r_nc = 1.10 before CF_traj completed
LABEL_HIT = ("f_hit (reference-hit fraction): an estimator of the ideal-sample fraction f_ideal with a gate-noise bias "
             "of 1.05-1.12 (CF_traj, A6 channel) and an unknown bias under idle dephasing (CF_traj A5, both T2 ends, is "
             "the model bracket); an upper end of the fault-free fraction f_0")
LABEL_MIX = ("mixture estimate (clean_fraction_mixture): the shape statistic; at k = 4 under the A6 channel it "
             "over-estimates f_ideal by the CF_traj C7 factor")


def load(p):
    with open(os.path.join(ROOT, p)) as fh:
        return json.load(fh)


def sha(p):
    with open(os.path.join(ROOT, p), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def signed_bar_recorded(lo, hi, bar=BAR):
    """The H0_ddtest / H0_2x2 rule (gate_H0_ddtest.signed_bar): GO iff lo >= bar, NO-GO iff hi < bar."""
    if lo >= bar:
        return "GO"
    if hi < bar:
        return "NO-GO"
    return "AMBIGUOUS"


def go_rule_v3(f, lo, hi):
    if lo >= BAR_LO and f >= BAR:
        return "GO"
    if hi < BAR:
        return "NO-GO"
    return "AMBIGUOUS"


def main():
    t0 = time.time()
    rnc = load("data/cf_trajectories/r_nc.json")
    r_nc, r95 = float(rnc["r_nc"]), [float(x) for x in rnc["pooled_r_ci95"]]
    kp = load("validation/H0_kpilot.json")["data"]["decision"]
    dd = load("validation/H0_ddtest.json")["data"]["decision"]
    h2 = load("validation/H0_2x2.json")["data"]
    hm = load("validation/H0_model.json")
    cf = load("validation/CF_traj.json")["data"]
    rows = []

    def add(record, field, statistic, f, f95, recorded_verdict=None):
        row = {"record": record, "field": field, "statistic": statistic, "f": float(f),
               "f_95": None if f95 is None else [float(f95[0]), float(f95[1])], "recorded_verdict": recorded_verdict}
        if f95 is not None and statistic == "f_hit":
            pooled = {"f_clean": float(f), "f_clean_68": [float(f95[0]), float(f95[1])], "confidence": 0.95}
            c = corrected_clean_fraction(pooled, r_nc, r95)
            row["f_hat_ideal"] = c["f_hat_ideal"]
            row["f_hat_ideal_95"] = c["f_hat_ideal_interval"]
            row["signed_bar_recorded_rule_on_f_hat_ideal"] = signed_bar_recorded(*c["f_hat_ideal_interval"])
            row["go_rule_v3_on_f_hat_ideal"] = go_rule_v3(c["f_hat_ideal"], *c["f_hat_ideal_interval"])
        rows.append(row)

    add("validation/H0_kpilot.json", "data.decision.f_pool", "f_hit", kp["f_pool"], kp["f_pool_95"], "NO-GO (kpilot)")
    for cell in ("T0", "T1", "T2", "T3"):
        c = dd["cells"][cell]
        add("validation/H0_ddtest.json", f"data.decision.cells.{cell}.f_pool", "f_hit", c["f_pool"], c["f_pool_95"],
            (f"signed bar {dd['signed_bar']} (adopted)" if cell == dd["adopted"] else None))
    add("validation/H0_2x2.json", "data.clean_fraction.pooled.f", "f_hit", h2["clean_fraction"]["pooled"]["f"],
        h2["clean_fraction"]["pooled"]["f_95"])
    ad = h2["adopted_configuration"]
    add("validation/H0_2x2.json", "data.adopted_configuration.f_pool", "f_hit", ad["f_pool"], ad["f_pool_95"],
        f"signed bar {ad['signed_bar']}")
    c2 = hm["data"]["C2_pooled_device_clean_count"]
    add("validation/H0_model.json", "data.C2_pooled_device_clean_count.pooled_reference_test.f_clean", "f_hit",
        c2["pooled_reference_test"]["f_clean"], None)
    add("validation/H0_model.json", "data.C2_pooled_device_clean_count.pooled_mixture.f_clean", "mixture",
        c2["pooled_mixture"]["f_clean"], None)
    h0m = [{"criterion": c["name"], "value": c["value"], "passed": c["passed"]} for c in hm["criteria"]
           if c["name"].startswith(("C1", "C2", "C3"))]
    # the 2x2 signed bar under v3 (prompts/29 3(3), owner decision 3a)
    pooled_ad = {"f_clean": ad["f_pool"], "f_clean_68": ad["f_pool_95"], "confidence": 0.95}
    ad_corr = corrected_clean_fraction(pooled_ad, r_nc, r95)
    planner = {"r_nc": PLANNER_R_NC, "f_hat_ideal": ad["f_pool"] / PLANNER_R_NC,
               "lower_garwood_only": ad["f_pool_95"][0] / PLANNER_R_NC}
    # the A5 bracket (CF_traj, 2x2 Markovian model, both T2 ends): r(1e-3) = f_hit / f_ideal
    a5 = {}
    for end, v in cf["A5_2x2_arm"]["ends"].items():
        r = v["stats"]["r_d1e-03"]
        a5[end] = {"r_d1e-03": r["value"], "r_ci95": r["ci95"], "f_hit_model": v["stats"]["f_hit"]["value"],
                   "f_ideal_model": v["stats"]["f_ideal_d1e-03"]["value"],
                   "adopted_f_pool_over_r": ad["f_pool"] / r["value"],
                   "adopted_f_pool_over_r_ci95": [ad["f_pool"] / r["ci95"][1], ad["f_pool"] / r["ci95"][0]]}
    unchanged = [
        "every H0_* criterion: the same statistic on both sides of each comparison, or f-independent",
        "the H0_kpilot NO-GO (strengthened: f_hit = 0.041 is an upper end of f_0, and f_hat_ideal is lower still)",
        "the H0_ddtest adoption of T3: R is a ratio of hit statistics (information: DD changes the error composition, "
        "so R is not exactly the ratio of f_0 or of f_ideal)",
        "the H0_2x2 energies (sector saturation; f-independent) and recall (1.0 from the observed per-state counts)"]
    rec_bar = signed_bar_recorded(*ad_corr["f_hat_ideal_interval"])
    v3_bar = go_rule_v3(ad_corr["f_hat_ideal"], *ad_corr["f_hat_ideal_interval"])
    qualified = (f"'signed bar GO on f_pool >= 0.1' in H0_ddtest and H0_2x2 is a GO on f_hit.  On the corrected statistic "
                 f"f_hat_ideal = f_hit / r_nc (r_nc = {r_nc:.4f}) the recorded rule (lower 95 % bound >= 0.1) reads "
                 f"{rec_bar}; the v3 rule of the 2x3 stages (lower >= 0.05 and point >= 0.10) reads {v3_bar}.  The "
                 f"gate-noise correction is not established for ibm_kingston (idle dephasing); the A5 model bracket has "
                 f"r < 1 at both T2 ends, i.e. f_hit would UNDER-estimate f_ideal there.  External citations carry this "
                 f"qualification (owner decision 3a); no recorded verdict is edited")
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *RECORDS], cwd=ROOT).returncode
    R = GateResult(GATE, "the recorded 2x2 clean-fraction values labelled by statistic, the corrected f_hat_ideal and "
                         "the 2x2 signed-bar qualification (information)")
    R.add("I1 every cited record read unedited (no working-tree change against HEAD); sha256 recorded",
          f"{len(RECORDS)} records; git diff {'clean' if dirty == 0 else 'NOT clean'}", "clean", dirty == 0)
    R.add("I2 r_nc read from data/cf_trajectories/r_nc.json and equal to the upper end of its bootstrap interval",
          f"r_nc {r_nc:.6f}, interval [{r95[0]:.6f}, {r95[1]:.6f}]", "r_nc = interval upper end", abs(r_nc - r95[1]) < 1e-15)
    R.data = {"prompt": PROMPT, "owner_decision": "data/owner_decision_20261005_partB.md (3a: the 2x2 qualification is accepted)",
              "records_sha256": {p: sha(p) for p in RECORDS}, "r_nc": r_nc, "r_nc_95": r95,
              "r_nc_caveat": rnc["caveat"], "label_f_hit": LABEL_HIT, "label_mixture": LABEL_MIX,
              "rows": rows, "H0_model_C1_C3": h0m,
              "adopted_2x2": {"f_pool": ad["f_pool"], "f_pool_95": ad["f_pool_95"], "corrected": ad_corr,
                              "recorded_rule_on_f_hat_ideal": rec_bar, "go_rule_v3_on_f_hat_ideal": v3_bar,
                              "planner_arithmetic_r_1.10": planner},
              "A5_bracket": a5, "A5_note": cf["A5_2x2_arm"]["model_note"],
              "unchanged": unchanged, "qualified": qualified,
              "k4_mixture_bias_CF_traj": cf["C7_k4_mixture"]["bias_ratio"]}
    R.runtime_s = time.time() - t0
    path = R.save()
    D = R.data
    lines = [f"# {GATE} — the recorded 2x2 clean-fraction values, by statistic (information)", "",
             f"Status: **{'PASS' if R.passed else 'FAIL'}** (structural criteria only).  Generated by "
             f"`scripts/cf_estimator_information.py` from `validation/{GATE}.json`; no number is typed.  {env_block()}", "",
             f"Prompt: {PROMPT}.  Owner decision: {D['owner_decision']}.", "",
             "## Criteria", "", R.criteria_table(), "",
             "## Every recorded value", "",
             f"Label of every f_hit row: {LABEL_HIT}.", "",
             md_table(["record", "field", "statistic", "f", "95 %", "recorded verdict", "f_hat_ideal = f_hit / r_nc",
                       "95 % (Garwood x bootstrap, log scale)", "recorded rule on f_hat_ideal", "v3 rule on f_hat_ideal"],
                      [[f"`{r['record']}`", f"`{r['field']}`", r["statistic"], f"{r['f']:.4g}",
                        "-" if r["f_95"] is None else f"[{r['f_95'][0]:.4g}, {r['f_95'][1]:.4g}]",
                        r["recorded_verdict"] or "-", f"{r['f_hat_ideal']:.4g}" if "f_hat_ideal" in r else "-",
                        (f"[{r['f_hat_ideal_95'][0]:.4g}, {r['f_hat_ideal_95'][1]:.4g}]" if "f_hat_ideal" in r else "-"),
                        r.get("signed_bar_recorded_rule_on_f_hat_ideal", "-"), r.get("go_rule_v3_on_f_hat_ideal", "-")]
                       for r in rows]), "",
             "H0_model C1-C3 (cited; C1 compares the mixture and reference-count estimates on Aer samples, C2/C3 are "
             "reference-hit statistics on the ibm_fez counts):", ""]
    lines += [f"- {c['criterion']}: value {c['value']} ({'PASS' if c['passed'] else 'FAIL'})" for c in h0m]
    a = D["adopted_2x2"]
    lines += ["", "## The 2x2 signed bar under the corrected statistic", "",
              f"H0_2x2 adopted cell f_pool = {a['f_pool']:.4f}, 95 % [{a['f_pool_95'][0]:.4f}, {a['f_pool_95'][1]:.4f}] "
              f"(f_hit).  With r_nc = {r_nc:.4f} (95 % [{r95[0]:.4f}, {r95[1]:.4f}]): f_hat_ideal = "
              f"{a['corrected']['f_hat_ideal']:.4f}, 95 % [{a['corrected']['f_hat_ideal_interval'][0]:.4f}, "
              f"{a['corrected']['f_hat_ideal_interval'][1]:.4f}].  Recorded rule (lower >= 0.1): **{rec_bar}**.  v3 rule "
              f"(lower >= 0.05 and point >= 0.10): **{v3_bar}**.  Planner arithmetic with r_nc = 1.10 (prompts/29 3(3)): "
              f"{a['planner_arithmetic_r_1.10']['f_hat_ideal']:.4f}, lower {a['planner_arithmetic_r_1.10']['lower_garwood_only']:.4f}.", "",
              "## The A5 model bracket (CF_traj, 2x2 Markovian idle-dephasing model of the adopted circuit)", "",
              md_table(["T2 end", "r(1e-3) = f_hit / f_ideal", "95 %", "model f_hit", "model f_ideal",
                        "adopted f_pool / r", "95 %"],
                       [[e, f"{v['r_d1e-03']:.4f}", f"[{v['r_ci95'][0]:.4f}, {v['r_ci95'][1]:.4f}]", f"{v['f_hit_model']:.4g}",
                         f"{v['f_ideal_model']:.4g}", f"{v['adopted_f_pool_over_r']:.4f}",
                         f"[{v['adopted_f_pool_over_r_ci95'][0]:.4f}, {v['adopted_f_pool_over_r_ci95'][1]:.4f}]"]
                        for e, v in a5.items()]), "",
              f"Model note (CF_traj): {D['A5_note']}.", "",
              "## What does not change", ""] + [f"- {u}" for u in unchanged] + [
              "", "## What is qualified", "", qualified + ".", ""]
    write_report("CF_estimator_2x2_information_20261003.md", "\n".join(lines))
    print(f"{GATE}: {'PASS' if R.passed else 'FAIL'} -> {os.path.relpath(path, ROOT)}")
    for c in R.criteria:
        print(f"  [{'PASS' if c.passed else 'FAIL'}] {c.name}: {c.value}")
    print("adopted:", a["corrected"]["f_hat_ideal"], a["corrected"]["f_hat_ideal_interval"], rec_bar, v3_bar)
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
