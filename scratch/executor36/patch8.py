import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
old = '''          {"pytest_coding": (reg or {}).get("pytest_coding", {}).get("summary"),
           "pytest_qiskit143": (reg or {}).get("pytest_qiskit143", {}).get("summary"),'''
new = '''          {"pytest_coding": _noansi((reg or {}).get("pytest_coding", {}).get("summary")),
           "pytest_venv": _noansi((reg or {}).get("pytest_venv", {}).get("summary")),
           "pytest_qiskit143": _noansi((reg or {}).get("pytest_qiskit143", {}).get("summary")),'''
assert old in s; s = s.replace(old, new)
old = '''def a6_slots(final_gpu, k5, mans):'''
new = '''def _noansi(t):
    import re
    return None if t is None else re.sub(r"\\x1b\\[[0-9;]*m", "", t)


def a6_slots(final_gpu, k5, mans):'''
assert old in s; s = s.replace(old, new)
old = '''    a8 = bool(reg and reg["pytest_coding"]["returncode"] == 0 and reg["pytest_qiskit143"]["returncode"] == 0'''
new = '''    a8 = bool(reg and reg["pytest_coding"]["returncode"] == 0 and reg["pytest_qiskit143"]["returncode"] == 0
              and reg.get("pytest_venv", {}).get("returncode") == 0'''
assert old in s; s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
