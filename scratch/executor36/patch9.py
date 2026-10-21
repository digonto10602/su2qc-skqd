import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
blk = open(os.path.join(os.path.dirname(__file__), "block36a.py.txt")).read()
anchor = "\n\ndef _" + "git(*args):"
assert anchor in s and "PROMPT_36A" not in s
s = s.replace(anchor, blk.rstrip("\n") + "\n" + anchor, 1)
old = '''    ap.add_argument("--stage", default=None,
                    choices=("acceptance", "etol", "plan", "chunk", "resize", "regression", "assemble"))'''
new = '''    ap.add_argument("--stage", default=None,
                    choices=("acceptance", "etol", "plan", "chunk", "resize", "regression", "assemble",
                             "extend", "ladder-ext", "cv3-final", "cluster"))'''
assert old in s
s = s.replace(old, new)
old = '''        if st == "regression":'''
new = '''        if st == "extend":
            return stage_extend_2x4(list(a.seeds), quick=a.quick)
        if st == "ladder-ext":
            print("s_star_information:", stage_ladder_ext_2x4(list(a.seeds), quick=a.quick))
            return 0
        if st == "cv3-final":
            s_star = None
            for s in GRID_EXT_2X4:
                p = os.path.join(CV4_DIR, f"resize_s{s:g}.json")
                if os.path.exists(p) and load_json(p)["sectors"]["B=1"]["ok_all_seeds"]:
                    s_star = s
                    break
            return stage_cv3_final_2x4(s_star, list(a.seeds), quick=a.quick)
        if st == "cluster":
            return stage_cluster_2x4(list(a.seeds), quick=a.quick)
        if st == "regression":'''
assert old in s
s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
