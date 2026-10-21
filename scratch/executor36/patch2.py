import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
a = s.index("def stage_regression_2x4():")
b = s.index("def noisy_information_2x4():")
new = open(os.path.join(os.path.dirname(__file__), "regression_block.py.txt")).read()
s = s[:a] + new + s[b:]
old = '''        if st == "regression":
            return stage_regression_2x4()'''
assert old in s
s = s.replace(old, '''        if st == "regression":
            return stage_regression_2x4(a.part or "all")''')
old = '''    ap.add_argument("--monte-carlo", type=int, default=MC_STRINGS_2X4, help="--stage acceptance: Monte-Carlo strings")'''
assert old in s
s = s.replace(old, old + '''
    ap.add_argument("--part", default=None, choices=("coding", "venv", "twin", "final", "all"),
                    help="--lattice 4 --stage regression: which part (each inside the 30-minute rule)")''')
open(p, "w").write(s)
print("ok")
