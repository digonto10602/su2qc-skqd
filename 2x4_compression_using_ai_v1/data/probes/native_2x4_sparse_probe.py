import sys, os, time, math, json, gzip
sys.path[:0] = ["2x4_compression_using_ai_v1/src", "src"]
import numpy as np
from c2x4.families import get_family_ir
from c2x4.evaluate import certified_state_check
from skqd import quantinuum_native as qn
from skqd.reference_sim import CodewordEmbedding
from skqd.exact import Model, mass_default
from skqd.krylov import basis_vector, coarse_states, term_groups
fam, want = sys.argv[1], sys.argv[2]
M = Model(4); emb = CodewordEmbedding(M); ints = np.asarray(emb.ints, dtype=np.int64)
groups = term_groups(M.terms, 4.0, mass_default(4.0))
for cid, g, md in get_family_ir(fam):
    if cid != want: continue
    g = [("cp", qs, math.pi) if nm == "cz" else (nm, qs, par) for nm, qs, par in g]
    t = time.time(); cc = qn.compile_native(qn.ir_to_pytket(g, 28, measure=True), "H2-2", 0); tc = time.time() - t
    cnt = qn.native_counts(cc)
    t = time.time(); q1l = qn.local_equivalence_35a(g, cc, 28, structured=True); tq = time.time() - t
    js = json.dumps(qn.to_json(cc), sort_keys=True); qa = qn.to_qasm(cc)
    print(cid, cnt["n_zz"], cnt["n_phasedx"], "compile", round(tc,1), "q1l", q1l["ok"], round(tq,1),
          "json MB", len(js)/1e6, "gz", len(gzip.compress(js.encode(), 9))/1e6, "qasm MB", len(qa)/1e6, flush=True)
    t = time.time(); cq2 = qn.from_qasm(qa); q1lq = qn.local_equivalence_35a(g, cq2, 28, structured=True)
    print("qasm readback Q1L", q1lq["ok"], q1lq["iii_rounding"]["state_bound_B"], round(time.time()-t,1), flush=True)
    tgt = coarse_states(groups, basis_vector(M.basis.dim, md["reference"]), md["dt"], md["k"])[md["k"]]
    back = [x for x in qn.pytket_to_ir(cc)[0] if x[0] != "measure"]
    t = time.time(); chk = certified_state_check(back, 28, ints, tgt); print("sparse native", chk, round(time.time()-t,1), flush=True)
