import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
old = '''    a7 = a7_bundles(mans, k5) if final else {"ok": False, "reason": "no final plan"}'''
new = '''    a7 = a7_bundles(mans, {c: None for c in k5_ids_L(sectors)})'''
assert old in s; s = s.replace(old, new)
old = '''        "resize_ladder": {s_: {sec: {"ok_all_seeds": v["sectors"][sec]["ok_all_seeds"],
                                     "shots_total": v["sectors"][sec]["shots_total"]} for sec, _ in SECTORS}
                          for s_, v in ladder.items()},'''
new = '''        "resize_ladder": {s_: {sec: {"ok_all_seeds": v["sectors"][sec]["ok_all_seeds"],
                                     "shots_total": v["sectors"][sec]["shots_total"],
                                     "criteria_ok": {k: all(x["criteria"][k]["ok"] for x in v["sectors"][sec]["seeds"].values())
                                                     for k in ("CV1", "CV2", "CV4", "CV5")},
                                     "width_half_max": max(x["criteria"]["CV2"]["width_half"]
                                                           for x in v["sectors"][sec]["seeds"].values()),
                                     "width_full_max": max(x["criteria"]["CV2"]["width_full"]
                                                           for x in v["sectors"][sec]["seeds"].values()),
                                     "B_all_full": [x["full"]["B_all_size"] for x in v["sectors"][sec]["seeds"].values()],
                                     "capped_circuits": sorted({c for x in v["sectors"][sec]["seeds"].values()
                                                                for c in x["capped_circuits"]})}
                               for sec, _ in SECTORS}
                          for s_, v in ladder.items()},'''
assert old in s; s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
