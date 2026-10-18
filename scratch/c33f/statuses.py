import glob
import json
import os

fs = sorted(glob.glob("validation/C[1-4]_*.json") + glob.glob("validation/C33_*.json"))
for f in fs:
    d = json.load(open(f))
    bad = [c["name"][:60] for c in d.get("criteria", []) if not c.get("passed")]
    D = d.get("data", {})
    fr = D.get("frun") or {}
    part = fr.get("part") or {}
    print(os.path.basename(f), d.get("status"), bad, part.get("part"), part.get("parts"), fr.get("run"),
          D.get("content") if isinstance(D.get("content"), str) else "", (D.get("run") or {}).get("wall_seconds"))
