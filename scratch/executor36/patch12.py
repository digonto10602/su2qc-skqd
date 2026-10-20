import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
a = s.index("def reference_prob_threads(")
b = s.index("def stage_cluster_2x4(")
s = s[:a] + s[b:]
old = '''    prob4 = reference_prob_threads(4, S.twoB, ORACLE_THREADS_2X4)   # the scratch prototype's BLAS order
    out = cluster_diag(S, Bs, 4, oref, oracle_prob=prob4, oracle_threads=ORACLE_THREADS_2X4)
    out["oracle_order_note"] = (f"O is ordered by the ground state computed under {ORACLE_THREADS_2X4} BLAS threads, the "
                                "order of scratch/executor36/oracle_b1.py; at one thread the boundary of O cuts a group of "
                                "near-equal weights differently and r_H(O) moves by up to 1.7e-7 (rH_O_one_thread_order); "
                                "W_0 / W_j and B are read on the gate's one-thread ground state")'''
new = '''    out = cluster_diag(S, Bs, 4, oref)
    out["oracle_order_note"] = (
        "O is ordered by the gate's ground state (BLAS one thread: identical in repeated gate processes, checked "
        "2026-10-19).  scratch/executor36/oracle_b1.py ran with a 4-thread BLAS pool, and the top-|B| boundary of O cuts "
        "groups of near-equal weights whose order depends on the round-off of the reference eigensolve; multi-thread "
        "reductions are not bit-reproducible, so the scratch values are reproduced to 1e-9 only where the boundary does "
        "not cut such a group (scratch/executor36/oracle_threads.py: a 4-thread run reproduced 1583 / 1538 to 1e-15, a "
        "later 4-thread child process did not).  The r_H(O) differences are recorded per seed; they do not touch any "
        "criterion (D2 is information)")'''
assert old in s
s = s.replace(old, new)
s = s.replace('''ORACLE_THREADS_2X4 = 4                            # 3.5: the BLAS order of the executor's oracle_b1.py prototype
''', "")
open(p, "w").write(s)
print("ok")
