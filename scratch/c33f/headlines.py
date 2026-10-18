"""Print the merged split-run headlines from validation/C33_<run>.json (prompts/33f hand-back; numbers read, not typed)."""
import glob
import json
import os
import re

for p in sorted(glob.glob("validation/C33_F*_B*.json")):
    if re.search(r"_part\d+of\d+\.json$|_cv3", p):
        continue
    d = json.load(open(p))
    fr = d["data"]["frun"]
    c = fr["at_N"]["certificate"]
    bad = [x["name"][:60] for x in d["criteria"] if not x["passed"]]
    print(os.path.basename(p)[:-5], d["status"], fr.get("kind"), "shots", fr["at_N"]["shots"], "B_all", fr["at_N"]["B_all_size"],
          "E_R-E0 %.3g" % c["E_R_minus_E0"], c["type"], "width %.4g" % c["width"] if c.get("width") is not None else c.get("width"),
          "E0in", c["E0_inside"], "recall %.4f" % c["recall_S999"], "CV", fr.get("CV1_CV5"),
          "cv3", (fr.get("cv3_status") or "")[:40], "merge_s %.0f" % d["data"].get("merge_seconds", -1), "fail", bad)
