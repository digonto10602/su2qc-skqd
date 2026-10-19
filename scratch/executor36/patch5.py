import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
old = '''        and all(v <= 1e-15 for d in et_same.values() for v in d.values())
    R.add("A2 E_tol per sector = E_R(R u top 80 % of S999) - E0 > 0 (h1_energy_tolerance(H, prob, refs, 0.8, 1e-3))",
          {sec: {"value": E_tol[sec]["value"], "n_top": E_tol[sec]["n_top"], "E_R": E_tol[sec]["E_R"],
                 "references": len(E_tol[sec]["references"])} for sec, _ in SECTORS},
          "> 0; chunk recomputation identical", a2)'''
new = '''        and all(v <= TOL_ETOL_PROCESS for d in et_same.values() for v in d.values())
    R.add("A2 E_tol per sector = E_R(R u top 80 % of S999) - E0 > 0 (h1_energy_tolerance(H, prob, refs, 0.8, 1e-3))",
          {sec: {"value": E_tol[sec]["value"], "n_top": E_tol[sec]["n_top"], "E_R": E_tol[sec]["E_R"],
                 "references": len(E_tol[sec]["references"]),
                 "max_abs_diff_chunk_recomputation": max(d[sec] for d in et_same.values()) if et_same else None}
           for sec, _ in SECTORS},
          f"> 0; chunk recomputation within {TOL_ETOL_PROCESS:g} (executor's consistency check)", a2)'''
assert old in s; s = s.replace(old, new)
old = '''REGRESSION_2X4 = os.path.join(CV4_DIR, "regression.json")'''
new = '''REGRESSION_2X4 = os.path.join(CV4_DIR, "regression.json")
# E_tol recomputed in another process differs by up to ~5e-9 at 2x4 B=0 (measured 2026-10-19): the sparse eigensolver's
# round-off in the ground-state weights moves equal-weight states across the top-80 % boundary.  Consistency check only.
TOL_ETOL_PROCESS = 1e-8'''
assert old in s; s = s.replace(old, new)
old = '''          {"sampled_shots": noisy["sampled_shots"], "statement": noisy["statement"],
           "max_expected_clean_at_1e6": max(v["expected_clean_shots"]["N=1e+06"] for v in noisy["scenarios"].values())},'''
new = '''          {"sampled_shots": noisy["sampled_shots"], "statement": noisy["statement"], "scenarios": len(noisy["scenarios"]),
           "E1_expected_clean_at_1e6_best_circuit": noisy["scenarios"]["E1"]["expected_clean_shots"]["N=1e+06"]
           if "E1" in noisy["scenarios"] else None},'''
assert old in s; s = s.replace(old, new)
old = '''    return {"sampled_shots": 0, "statement": "no noisy 2x4 cell; information only", "scenarios": rows,'''
new = '''    sc = load_json(os.path.join(ROOT, "validation", "QN_2x4.json"))["data"]["analytic"].get("scenarios")
    return {"sampled_shots": 0, "statement": "no noisy 2x4 cell; information only", "scenarios": rows,
            "scenario_definitions": sc,'''
assert old in s; s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
