"""Planner prototype (prompts/31): certificate width of the oracle supports S_eps at 2x3, g2 = 4.
r_H, Weinstein and Kato-Temple (alpha = exact E1) widths, W, and the k <= 4 reachability of the states
S_eps needs beyond S999.  To be reproduced by gate CV_2x3_plan v2."""
import json, os, sys, time
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from skqd.exact import Model, mass_default
from skqd.krylov import basis_vector, coarse_states, references, term_groups
from skqd.skqd import certify, exact_support, poisson_lambda_star, ritz
t0 = time.time()
g2 = 4.0; m = mass_default(g2); M = Model(3); H = M.H(g2); groups = term_groups(M.terms, g2, m)
lam = poisson_lambda_star()
out = {}
for twoB in (0, 2):
    r = M.reference(g2, twoB, k=4)
    E0, E1 = float(r.E0), float(r.energies[1])
    prob = np.zeros(M.basis.dim); prob[r.indices] = np.abs(r.ground) ** 2
    refs = [int(x) for x in references(M.basis, twoB)]
    sts = [s for rr in refs for s in coarse_states(groups, basis_vector(M.basis.dim, rr), r.dt, 4)[1:]]
    P = np.array([np.abs(s) ** 2 for s in sts])  # circuits x dim
    Hd = H.diagonal()
    rows = {}
    for eps in (1e-2, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5, 1e-6):
        S = exact_support(prob, eps)
        B = sorted(set(int(x) for x in S) | set(refs))
        res = ritz(H, B); c = certify(res, E0, E1)
        W = float(prob[B].sum())
        outside = np.setdiff1d(np.arange(M.basis.dim), B)
        est = float(np.sqrt(np.sum((E0 - Hd[outside]) ** 2 * prob[outside])))
        new = np.setdiff1d(S, exact_support(prob, 1e-3))
        pmax = P[:, S].max(axis=0); psum = P[:, S].sum(axis=0)
        rows[f"{eps:g}"] = dict(size=len(B), ER_minus_E0=float(res.ER - E0), rH=float(res.rH), W=W,
                               one_minus_W=1 - W, rH_estimate_E0_minus_Hnn=est,
                               kt_width_exact_E1=(None if c.kt_rigorous is None else float(res.ER - c.kt_rigorous[0])),
                               gap_holds=c.gap_assumption_holds, alpha_second_ritz=float(res.ER1),
                               min_pmax=float(pmax.min()), min_psum=float(psum.min()),
                               n_states_pmax_below_1e4=int((pmax < 1e-4).sum()),
                               N_k4scaled_shots_at_y0574=float(lam / (0.0574 * pmax.min())),
                               states_beyond_S999=int(len(new)))
    out[f"B={twoB//2}"] = dict(E0=E0, E1=E1, dt=float(r.dt), rows=rows)
out["runtime_s"] = time.time() - t0
json.dump(out, open(os.path.join(ROOT, "scratch", "planner", "oracle_width_20261005.json"), "w"), indent=1)
for sec, v in out.items():
    if sec == "runtime_s": continue
    print(sec, "E0", v["E0"], "E1", v["E1"])
    for eps, row in v["rows"].items():
        print(f"  eps={eps:>6} |B|={row['size']:4d} ER-E0={row['ER_minus_E0']:.2e} rH={row['rH']:.4f} est={row['rH_estimate_E0_minus_Hnn']:.4f} 1-W={row['one_minus_W']:.2e} KT={row['kt_width_exact_E1']} gap={row['gap_holds']} min_pmax={row['min_pmax']:.2e} N_k4={row['N_k4scaled_shots_at_y0574']:.2e} beyond999={row['states_beyond_S999']}")
print("runtime", out["runtime_s"])
