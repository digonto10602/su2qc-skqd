#!/usr/bin/env python3
"""
Insert the H0_ddrep context into section 6 ("Honest limits") of a generated K1_2x3_fpilot report
(prompts/32 part B; the coordinator's instruction of 2026-10-06: "State the H0_ddrep result in the K1
report's honest-limits section").

gate_K1_2x3_fpilot.py is on the do-not-touch list of prompts/32, so the bullet is added here, after
`--stage assemble`, with every number read from validation/H0_ddrep.json and validation/H0_ddtest.json
(rule 1: no number typed by hand).  Idempotent: an existing bullet (marked by MARK) is replaced.

Usage: python scripts/k1_ddrep_note.py reports/K1_2x3_fpilot_ibm_kingston.md
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MARK = "<!-- k1_ddrep_note -->"


def load(path):
    with open(os.path.join(ROOT, path)) as fh:
        return json.load(fh)


def note():
    rep = load("validation/H0_ddrep.json")
    cells_old = load("validation/H0_ddtest.json")["data"]["decision"]["cells"]
    old, old0 = cells_old["T3"], cells_old["T0"]
    d = rep["data"]
    t3, t0 = d["cells"]["T3"], d["cells"]["T0"]
    r2 = d["replication"]["R2_detail"]
    job = ", ".join(d["live"]["job_ids"])
    lo, hi = t3["R_95"]
    verdict = ("on 2026-10-06 T3 sat below the no-DD baseline: the 95 % interval of R excludes 1 from above" if hi < 1
               else "on 2026-10-06 the 95 % interval of R contains 1: no gain shown" if lo <= 1
               else "on 2026-10-06 a gain smaller than the 10-02 one")
    return (f"- {MARK} **The XY4 cell this job carries did not replicate on 2026-10-06** (gate H0_ddrep, status "
            f"{rep['status']}, job {job}, `validation/H0_ddrep.json`): on the 2x2 patch the T3 (client XY4) gain was "
            f"R = {t3['R']:.3f} [{t3['R_95'][0]:.3f}, {t3['R_95'][1]:.3f}] (95 %, class {t3['class']}) against "
            f"R = {old['R']:.3f} [{old['R_95'][0]:.3f}, {old['R_95'][1]:.3f}] on 2026-10-02 (`validation/H0_ddtest.json`); "
            f"R1 {d['replication']['R1']}, R2 {d['replication']['R2']} (|ln R_new - ln R_old| = "
            f"{abs(r2['difference']):.3f} > {r2['tolerance']:.3f}), and the no-DD baseline f_T0 = {t0['f_pool']:.4f} "
            f"[{t0['f_pool_95'][0]:.4f}, {t0['f_pool_95'][1]:.4f}] against {old0['f_pool']:.4f} on 2026-10-02, on the same QPYs.  K1 is run as built "
            f"(owner decision: cell T3, unchanged), so the 'XY4 transfer' ends of the bracket in section 4, which "
            f"multiply by the 2026-10-02 R, are not supported by that day's data ({verdict}).  The decision "
            f"statistic f_hit does not use R.\n")


def main(path):
    with open(path) as fh:
        txt = fh.read()
    txt = re.sub(r"- " + re.escape(MARK) + r".*?\n(?=- |\n## )", "", txt, flags=re.S)
    head = "## 6. Honest limits\n\n"
    if head not in txt:
        raise SystemExit(f"{path}: no '## 6. Honest limits' section")
    txt = txt.replace(head, head + note(), 1)
    with open(path, "w") as fh:
        fh.write(txt)
    print(f"{path}: H0_ddrep note inserted into section 6")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1]))
