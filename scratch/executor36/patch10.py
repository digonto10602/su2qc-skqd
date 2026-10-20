import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
rep = [
    ('''def cluster_diag(S, seeds_B, n_states=4, oracle_ref=None):''',
     '''def cluster_diag(S, seeds_B, n_states=4, oracle_ref=None, oracle_prob=None, oracle_threads=1):'''),
    ('''    top-|B| set O of psi_0 weight with W_0 / W_j split over B \\\\ O and r_H(B), r_H(O)."""''',
     '''    top-|B| set O of psi_0 weight with W_0 / W_j split over B \\\\ O and r_H(B), r_H(O).  oracle_prob / oracle_threads: the
    ground-state weights that order O and the BLAS threads of its Ritz solve (the oracle set cuts through groups of
    near-equal weights whose order depends on the BLAS thread count of the reference eigensolve, as the 2x3 oracle-width
    table records); the one-thread O is recorded beside it."""'''),
    ('''        O = sorted(set(int(x) for x in oracle(S.prob, S.sector_idx, n)) | set(refs))
        Bs, Os = set(B), set(O)
        BmO, OmB = sorted(Bs - Os), sorted(Os - Bs)
        rb, ro = ritz(S.H, np.asarray(B)), ritz(S.H, np.asarray(O))''',
     '''        O1 = sorted(set(int(x) for x in oracle(S.prob, S.sector_idx, n)) | set(refs))
        O = (O1 if oracle_prob is None else sorted(set(int(x) for x in oracle(oracle_prob, S.sector_idx, n)) | set(refs)))
        Bs, Os = set(B), set(O)
        BmO, OmB = sorted(Bs - Os), sorted(Os - Bs)
        rb = ritz(S.H, np.asarray(B))
        with threadpool_limits(oracle_threads):
            ro = ritz(S.H, np.asarray(O))
        ro1 = ritz(S.H, np.asarray(O1))'''),
    ('''               "rH_B": float(rb.rH), "rH_O": float(ro.rH), "E_R_minus_E0_B": float(rb.ER - S.E0),''',
     '''               "rH_B": float(rb.rH), "rH_O": float(ro.rH), "rH_O_one_thread_order": float(ro1.rH),
               "O_equals_one_thread_O": O == O1, "oracle_blas_threads": int(oracle_threads),
               "E_R_minus_E0_B": float(rb.ER - S.E0),'''),
    ('''    out = cluster_diag(S, Bs, 4, oref)''',
     '''    from threadpoolctl import threadpool_limits
    with threadpool_limits(ORACLE_THREADS_2X4):    # the scratch prototype's BLAS order (oracle_b1.py ran at 4 threads)
        r4 = S.M.reference(G2, S.twoB, k=4)
    prob4 = np.zeros(S.M.basis.dim)
    prob4[r4.indices] = np.abs(r4.ground) ** 2
    out = cluster_diag(S, Bs, 4, oref, oracle_prob=prob4, oracle_threads=ORACLE_THREADS_2X4)
    out["oracle_order_note"] = (f"O is ordered by the ground state computed under {ORACLE_THREADS_2X4} BLAS threads, the "
                                "order of scratch/executor36/oracle_b1.py; at one thread the boundary of O cuts a group of "
                                "near-equal weights differently and r_H(O) moves by up to 1.7e-7 (rH_O_one_thread_order); "
                                "W_0 / W_j and B are read on the gate's one-thread ground state")'''),
    ('''TOL_E1 = 1e-12
''', '''TOL_E1 = 1e-12
ORACLE_THREADS_2X4 = 4                            # 3.5: the BLAS order of the executor's oracle_b1.py prototype
'''),
]
for a, b in rep:
    assert a in s, a[:70]
    s = s.replace(a, b)
open(p, "w").write(s)
print("ok")
