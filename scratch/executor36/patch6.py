import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
old = '''            "scenario_definitions": sc,'''
new = '''            "scenario_definitions": sc,
            "scenario_note": ("E1-E6c are the Quantinuum-based scenarios of prompts/33 section 1.2 / prompts/35; E7_0.10_lat "
                              "is the matched-f scenario (error rates scaled so that a reference lattice's own counts give "
                              "f = 0.10): a hypothetical device, not an existing one"),'''
assert old in s; s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
