import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
old = '''    from threadpoolctl import threadpool_limits
    with threadpool_limits(ORACLE_THREADS_2X4):    # the scratch prototype's BLAS order (oracle_b1.py ran at 4 threads)
        r4 = S.M.reference(G2, S.twoB, k=4)
    prob4 = np.zeros(S.M.basis.dim)
    prob4[r4.indices] = np.abs(r4.ground) ** 2
'''
new = '''    prob4 = reference_prob_threads(4, S.twoB, ORACLE_THREADS_2X4)   # the scratch prototype's BLAS order
'''
assert old in s
s = s.replace(old, new)
old = '''def stage_cluster_2x4(seeds=SEEDS, quick=False):'''
new = '''def reference_prob_threads(lat, twoB, threads):
    """The sector ground-state weights computed in a child process whose BLAS pool has `threads` threads (this process
    pins BLAS to one thread at import, so threadpool_limits cannot raise it)."""
    import subprocess
    import tempfile
    code = ("import sys, numpy as np; sys.path.insert(0, {src!r}); from skqd.exact import Model; M = Model({lat}); "
            "r = M.reference({g2}, {tb}, k=4); p = np.zeros(M.basis.dim); p[r.indices] = np.abs(r.ground) ** 2; "
            "np.save(sys.argv[1], p)").format(src=os.path.join(ROOT, "src"), lat=int(lat), g2=G2, tb=int(twoB))
    env = dict(os.environ, OMP_NUM_THREADS=str(threads), OPENBLAS_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads))
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "p.npy")
        r = subprocess.run([sys.executable, "-c", code, f], env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-800:])
        return np.load(f)


def stage_cluster_2x4(seeds=SEEDS, quick=False):'''
assert old in s
s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
