"""Review 001, step 0: obtain genie's class-A / class-B circuits from its BUILDERS ONLY.

genie's on-disk cache (data/cache) is NOT read: every module-level CACHE is redirected to a fresh
directory under reviews/, so every term circuit is regenerated from source. genie's simulator and
verification code are not called by this script (the builders themselves call genie's sparse helpers
internally to construct frames; that is construction, not verification).
Output: reviews/001_cache/circuits.pkl = {(cls, twoB, ref, k): gate list}.
"""
import os, sys, pickle, time, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(STUDY, "src"))
NEWCACHE = os.path.join(HERE, "001_cache")
os.makedirs(NEWCACHE, exist_ok=True)
import c2x4.env as env
env.CACHE = NEWCACHE
import c2x4.problem as problem
problem.CACHE = NEWCACHE
import c2x4.family as family
family.CACHE = NEWCACHE
from c2x4.problem import get_problem
from c2x4.family import archive_family, circuit

def main(ids):
    P = get_problem()
    out_path = os.path.join(NEWCACHE, "circuits.pkl")
    out = pickle.load(open(out_path, "rb")) if os.path.exists(out_path) else {}
    fams = {"A": archive_family("it5", "operator", peephole=True),
            "B": archive_family("it5", "input", peephole=True)}
    for cls, twoB, ref, k in ids:
        if (cls, twoB, ref, k) in out:
            continue
        t0 = time.time()
        g = circuit(P, fams[cls], twoB, ref, k)
        out[(cls, twoB, ref, k)] = g
        pickle.dump(out, open(out_path, "wb"))
        print(cls, twoB, ref, k, len(g), f"{time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    ids = [tuple([s.split(":")[0]] + [int(v) for v in s.split(":")[1:]]) for s in sys.argv[1].split(",")]
    main(ids)
