import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
old = '''        pref = sorted({rnd(phi * int(N)) for phi in PHI} | {GPU_MULT * int(N), ne, 2 * ne})
        if max(pref) > cv:
            raise SystemExit(f"{c}: a prefix ({max(pref)}) exceeds the order-kept CV block ({cv})")'''
new = '''        pref = {rnd(phi * int(N)) for phi in PHI} | {GPU_MULT * int(N), ne}
        if max(pref) > cv:
            raise SystemExit(f"{c}: a prefix ({max(pref)}) exceeds the order-kept CV block ({cv})")
        if 2 * ne <= cv:                               # the 2 N_eq CV3 point is information: kept where it fits
            pref.add(2 * ne)
        pref = sorted(pref)'''
assert old in s; s = s.replace(old, new)
old = '''    prefix lengths {round(phi N_c^final)} u {8 N_c^final} u {N_eq, 2 N_eq} (the CV3 equal-shots prefixes), all inside
    the first max(8 N_c^final, 6250) shots; the uniform block is the last U_c shots."""'''
new = '''    prefix lengths {round(phi N_c^final)} u {8 N_c^final} u {N_eq} (the CV3 equal-shots prefix; 2 N_eq, information, where
    it fits), all inside the first max(8 N_c^final, 6250) shots; the uniform block is the last U_c shots."""'''
assert old in s; s = s.replace(old, new)
open(p, "w").write(s)
p = os.path.join(ROOT, "tests", "test_qv_2x4_pipeline.py")
s = open(p).read()
old = '''    with pytest.raises(SystemExit):
        CV.gpu_plan({"a": 267}, mans, {0: 4000})          # 2 N_eq beyond the CV block'''
new = '''    g2, _ = CV.gpu_plan({"a": 267}, mans, {0: 4000})     # 2 N_eq beyond the CV block: dropped (information only)
    assert 4000 in g2["a"]["prefix_lengths"] and 8000 not in g2["a"]["prefix_lengths"]
    with pytest.raises(SystemExit):
        CV.gpu_plan({"a": 267}, mans, {0: 7000})          # N_eq itself beyond the CV block'''
assert old in s; s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
