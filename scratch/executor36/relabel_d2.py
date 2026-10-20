"""prompts/36a addendum A2: relabel the stored D2 record (no recomputation): drop the 1e-9 flag, add the 1e-5 one."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))
import gate_CV as CV  # noqa: E402

p = os.path.join(CV.CV4_DIR, "cluster_diag_B1.json")
d = CV.d2_scratch_flags(json.load(open(p)))
with open(p, "w") as fh:
    json.dump(d, fh, indent=1)
print(d["scratch_rH_reproduced_1e-5"])
