"""WORKED EXAMPLE (not a frozen family): the whole compression procedure on the 2x2 ladder, in a sandbox.

This is the smallest end-to-end run of MANUAL_lgt_circuit_compression.md §11.0.  It is a teaching example: its circuits
are NOT a `compressed_circuit_llm_2x2_*` family, are not registered in src/c2x4/families.py, and must not be used
anywhere; the owner decides whether 2x2 families are made.

Everything it writes goes to this folder (2x2_compression_using_ai_v1/examples/2x2_sandbox/; the code it imports stays
in 2x4_compression_using_ai_v1/src/, notes/012): the disk cache (cache/), the loop archive
(archive_L2_example.json), the circuits (circuits_L2_example.json.gz) and the results (results.json).  No file under
data/ is read for writing or overwritten.

Steps: sandbox redirection -> Problem(lx=2) -> structure tests -> loop over proposals for class A (per term) and
class B (per reference and term) -> assemble all 28 circuits per class with the pp2 finishing pass -> counts and
skeleton k-independence -> certified pruned verification (with the rounding term) -> independent qiskit-aer statevector
check against the package's own coarse states, own reference input for all circuits plus a random-superposition test
(class A must pass, class B is expected to fail).

Run (coding env, from the repository root or anywhere):
    python 2x2_compression_using_ai_v1/examples/2x2_sandbox/run_2x2_example.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))              # the package repository
STUDY = os.path.join(ROOT, "2x4_compression_using_ai_v1")                   # the shared study code (notes/012)
sys.path.insert(0, os.path.join(STUDY, "src"))
sys.path.insert(0, os.path.join(ROOT, "src"))

# ---------------------------------------------------------------- 1. sandbox: BEFORE importing any builder
import c2x4.env as env                                     # noqa: E402

SANDBOX_CACHE = os.path.join(HERE, "cache")
env.CACHE = SANDBOX_CACHE
env.archive_path = lambda label: os.path.join(HERE, f"archive_{label}.json")
import c2x4.problem as problem                             # noqa: E402
import c2x4.family as family                               # noqa: E402
problem.CACHE = SANDBOX_CACHE
family.CACHE = SANDBOX_CACHE

from c2x4.evaluate import counts, verify_circuit_pruned, verify_term_operator   # noqa: E402
from c2x4.families import ir_to_qiskit                                           # noqa: E402
from c2x4.family import family_from_spec, circuit, get_reach                     # noqa: E402
from c2x4.plaqfactor import corners_of, factorise                                # noqa: E402
from c2x4.problem import get_problem                                             # noqa: E402
from c2x4.proposals import PROPOSALS, applicable                                 # noqa: E402
from c2x4.reach import components, contract_states                               # noqa: E402

LX = 2
LABEL = "L2_example"
KMAX = 4                                    # the frozen 2x2 family uses k = 1..4 (28 circuits)
A1_DEV, A1_LEAK = 1e-10, 1e-12
PROPS_A = ["full_lin", "framed_lin", "bframed_lin", "bframed_lin_milp", "jwc_bframed", "jwc_framed",
           "cb0", "cb1", "cb0_jwc", "cb1_jwc", "cfg_lin", "cfg_t_lin", "cfg_lin_milp"]
PROPS_B = ["rpkg_lin", "cfg_lin", "cfg_t_lin", "cfg_lin_milp", "bframed_lin", "framed_lin", "jwc_bframed",
           "jwc_framed", "cb0", "cb1", "cb0_jwc", "cb1_jwc", "cb0p", "cb1p"]
SEEDS_SUPERPOSITION = (11, 12)


def try_candidate(P, label, nm, th, con, loc):
    try:
        g = PROPOSALS[label]["fn"](P, nm, th, con, loc)
    except Exception as exc:                 # recorded, never silently dropped
        return {"label": label, "error": repr(exc)[:200], "accepted": False}
    c = counts(g)
    r = verify_term_operator(P, nm, g, th, restrict_to=con)
    return {"label": label, "n_2q": c["n_2q"], "depth_2q": c["depth_2q"], "max_dev": r["max_dev"],
            "max_leak": r["max_leak"], "accepted": bool(r["max_dev"] <= A1_DEV and r["max_leak"] <= A1_LEAK)}


def best(rows):
    acc = [r for r in rows if r.get("accepted")]
    return min(acc, key=lambda r: (r["n_2q"], r["depth_2q"])) if acc else None


def structure_tests(P):
    """Blocks bipartite with zero diagonal (skqd.circuits_ir._bipartition), plaquette corner factorisation."""
    import scipy.sparse as sp
    from skqd.circuits_ir import _bipartition
    out = {"terms": {}}
    for nm in P.term_names():
        sup, states, h, pos = P.local(nm)
        h = np.asarray(h)
        A = np.abs(h) > 1e-12
        np.fill_diagonal(A, False)
        lab = components(sp.csr_matrix(h))
        ok, sizes = True, []
        for b in np.unique(lab):
            idx = np.flatnonzero(lab == b)
            sizes.append(len(idx))
            if len(idx) > 1 and (_bipartition(A[np.ix_(idx, idx)]) is None or np.abs(np.diag(h)[idx]).max() > 1e-12):
                ok = False
        out["terms"][nm] = {"support_qubits": len(sup), "local_codewords": len(states),
                            "blocks": len(sizes), "largest_block": int(max(sizes)),
                            "all_blocks_bipartite_zero_diagonal": ok}
    for p in range(len(P.M.lat.plaquettes)):
        nm = f"plaq{p}"
        fac = factorise(P, nm, corners_of(P, p))
        out["terms"][nm]["corner_factorisation"] = {"product_residual_all_rows": fac["product_residual_all_rows"],
                                                    "magnitude_residual": fac["magnitude_residual"],
                                                    "corners_without_third_link": sum(
                                                        1 for c in corners_of(P, p) if c["third"] is None)}
    return out


def aer_checks(fam_rows, P):
    """Independent check: qiskit-aer statevector (double, fusion off) of the qiskit circuit, target from the package's
    coarse_states with dt from Model(2).reference (not from the study's Problem)."""
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from skqd.exact import Model, mass_default
    from skqd.krylov import apply_groups, basis_vector, coarse_states, term_groups
    from skqd.reference_sim import CodewordEmbedding
    M = Model(LX)
    groups = term_groups(M.terms, 4.0, mass_default(4.0))
    ints = np.asarray(CodewordEmbedding(M).ints, dtype=np.int64)
    n = P.n
    dts = {tb: float(M.reference(4.0, tb).dt) for tb in (0, 2)}
    Hd = M.terms.groups(4.0, mass_default(4.0))["diag"]
    sim = AerSimulator(method="statevector", precision="double", fusion_enable=False)
    out = {}
    for cls, rows in fam_rows.items():
        res = {}
        for cid, (twoB, ref, k, g) in rows.items():
            qc = ir_to_qiskit(g, n)
            qc.save_statevector()
            psi = np.asarray(sim.run(qc).result().data(0)["statevector"].data)
            got = psi[ints].copy()
            psi[ints] = 0
            leak_nc = float(np.vdot(psi, psi).real)
            sector = np.asarray(M.basis.sector(twoB))
            other = np.setdiff1d(np.arange(M.basis.dim), sector)
            t = coarse_states(groups, basis_vector(M.basis.dim, ref), dts[twoB], k)[k]
            ov = np.vdot(t, got)
            ph = float(np.angle(ov))
            dev = float(np.abs(got * np.exp(-1j * ph) - t).max())
            pred = float(np.angle(np.exp(1j * k * dts[twoB] * float(np.real(Hd[ref, ref]))))) if cls == "B" else 0.0
            res[cid] = {"max_abs_dpsi": dev, "leak_noncodeword": leak_nc,
                        "leak_other_sector": float(np.sum(np.abs(got[other]) ** 2)),
                        "global_phase": ph, "phase_minus_predicted": float(np.angle(np.exp(1j * (ph - pred)))),
                        "pass": bool(dev < 1e-10 and leak_nc + float(np.sum(np.abs(got[other]) ** 2)) < 1e-9)}
        out[cls] = {"circuits": res, "n_pass": sum(r["pass"] for r in res.values()), "n": len(res),
                    "max_abs_dpsi": max(r["max_abs_dpsi"] for r in res.values()),
                    "max_leak": max(r["leak_noncodeword"] + r["leak_other_sector"] for r in res.values()),
                    "max_abs_phase_minus_predicted": max(abs(r["phase_minus_predicted"]) for r in res.values())}
    # random-superposition operator test on one circuit per class: (twoB=0, first reference, k=2)
    sup_rows = {}
    for cls, rows in fam_rows.items():
        cid = [c for c, v in rows.items() if v[0] == 0 and v[2] == 2][0]
        twoB, ref, k, g = rows[cid]
        sector = np.asarray(M.basis.sector(twoB))
        ref_int = int(ints[ref])
        for seed in SEEDS_SUPERPOSITION:
            rng = np.random.default_rng(seed)
            c = rng.normal(size=len(sector)) + 1j * rng.normal(size=len(sector))
            c /= np.linalg.norm(c)
            phi = np.zeros(M.basis.dim, dtype=complex)
            phi[sector] = c
            target = apply_groups(groups, phi.copy(), k * dts[twoB])
            init = np.zeros(2 ** n, dtype=complex)
            init[ints ^ ref_int] = phi        # Prep^-1 (the X-gate prefix) maps |cw> -> |cw ^ ref>
            pre = QuantumCircuit(n)
            pre.set_statevector(init)
            qc = pre.compose(ir_to_qiskit(g, n))
            qc.save_statevector()
            psi = np.asarray(sim.run(qc).result().data(0)["statevector"].data)
            got = psi[ints]
            ph = float(np.angle(np.vdot(target, got)))
            d = got * np.exp(-1j * ph) - target
            sup_rows[f"{cls}:{cid}:seed{seed}"] = {"l2_dpsi": float(np.linalg.norm(d)),
                                                   "max_abs_dpsi": float(np.abs(d).max()),
                                                   "n_components": int(len(sector))}
    out["random_superposition"] = sup_rows
    out["engine"] = {"method": "statevector", "precision": "double", "fusion": False}
    out["dt_package"] = dts
    return out


def main():
    t0 = time.time()
    P = get_problem(LX)
    R = get_reach(P)
    results = {"note": "WORKED EXAMPLE, not a frozen family; see the module docstring",
               "lattice": P.lattice, "n_qubits": P.n, "dim": int(P.M.basis.dim), "dt": P.dt,
               "dt_source": P.dt_source, "references": P.refs, "terms": P.term_names()}
    results["structure"] = structure_tests(P)
    # ---- loop (class A per term, class B per reference and term), selection angle = 1 * dt
    t_loop = time.time()
    arch = {"operator": {}, "input": {}}
    for nm in P.term_names():
        rows = [try_candidate(P, lb, nm, P.theta(0, 1), None, None) for lb in PROPS_A
                if applicable(lb, nm, P) and PROPOSALS[lb]["contract"] in ("operator", "both")]
        arch["operator"][nm] = {"candidates": rows, "best": best(rows)}
    for twoB in (0, 2):
        for ref in P.refs[twoB]:
            row = {"twoB": twoB}
            for nm in P.term_names():
                loc = R.local_reachable(ref, nm)
                con = contract_states(P, nm, loc)
                rows = [try_candidate(P, lb, nm, P.theta(twoB, 1), con, loc) for lb in PROPS_B
                        if applicable(lb, nm, P)]
                row[nm] = {"candidates": rows, "best": best(rows), "n_contract_states": len(con)}
            arch["input"][str(ref)] = row
    env.write_json(env.archive_path(LABEL), arch, produced_by="2x2_compression_using_ai_v1/examples/2x2_sandbox/run_2x2_example.py",
                   parameters={"label": LABEL, "proposals_A": PROPS_A, "proposals_B": PROPS_B,
                               "A1": {"max_dev": A1_DEV, "max_leak": A1_LEAK}}, t_start=t_loop)
    results["loop_wall_s"] = time.time() - t_loop
    results["per_term_class_A"] = {nm: {"best": v["best"]["label"], "n_2q": v["best"]["n_2q"]}
                                   for nm, v in arch["operator"].items()}
    # ---- assemble, verify (certified pruned, incl. rounding), skeleton check
    fam_rows, circ_dump = {}, {}
    for cls, spec in (("A", f"arch:{LABEL}:operator:pp2"), ("B", f"arch:{LABEL}:input:pp2")):
        fam = family_from_spec(spec, lx=LX)
        rows, ver = {}, {}
        for (twoB, ref, k) in P.circuit_ids(KMAX):
            cid = P.tag(twoB, ref, k)
            g = circuit(P, fam, twoB, ref, k)
            c = counts(g)
            v = verify_circuit_pruned(P, g, twoB, ref, k)
            skel = hashlib.sha256(repr([(a, list(b)) for a, b, _ in g]).encode()).hexdigest()
            rows[cid] = (twoB, ref, k, g)
            ver[cid] = {"n_2q": c["n_2q"], "depth_2q": c["depth_2q"], "n_1q": c["n_1q"],
                        "max_dev_measured": v["max_dev_phase_aligned"], "certified_max_dev": v["certified_max_dev"],
                        "certified_leakage": v["certified_leakage"], "rounding_bound": v["rounding"]["rounding_bound"],
                        "prune_bound": v["prune_bound"], "pass": v["pass"], "skeleton_sha256": skel}
            circ_dump[f"{cls}:{cid}"] = [[a, list(b), (None if p is None else
                                          (np.asarray(p).tolist() if np.ndim(p) else float(p)))]
                                         for a, b, p in g]
        by_ref = {}
        for cid, r in ver.items():
            by_ref.setdefault(cid.rsplit("_k", 1)[0], set()).add(r["skeleton_sha256"])
        n2 = [r["n_2q"] for r in ver.values()]
        d2 = [r["depth_2q"] for r in ver.values()]
        results[f"class_{cls}"] = {
            "spec": spec, "circuits": ver, "n": len(ver), "n_pass": sum(r["pass"] for r in ver.values()),
            "n_2q_min": min(n2), "n_2q_max": max(n2), "n_2q_mean": float(np.mean(n2)),
            "depth_2q_min": min(d2), "depth_2q_max": max(d2),
            "max_certified_dev": max(r["certified_max_dev"] for r in ver.values()),
            "max_certified_leakage": max(r["certified_leakage"] for r in ver.values()),
            "skeleton_k_independent": all(len(s) == 1 for s in by_ref.values())}
        fam_rows[cls] = rows
    def _enc(v):
        if isinstance(v, complex):
            return [v.real, v.imag]
        raise TypeError(type(v))
    with gzip.open(os.path.join(HERE, f"circuits_{LABEL}.json.gz"), "wt") as fh:
        json.dump(json.loads(json.dumps(circ_dump, default=lambda o: o.tolist() if hasattr(o, "tolist") else _enc(o))),
                  fh)
    # ---- independent Aer checks
    results["aer"] = aer_checks(fam_rows, P)
    frozen = json.load(open(os.path.join(ROOT, "data", "quantinuum", "circuits_2x2", "index.json")))["summary"]
    results["frozen_2x2_for_comparison"] = {"n_zz": frozen["n_zz"],
                                            "source": "data/quantinuum/circuits_2x2/index.json summary.n_zz"}
    p = env.write_json(os.path.join(HERE, "results.json"), results,
                       produced_by="2x2_compression_using_ai_v1/examples/2x2_sandbox/run_2x2_example.py",
                       parameters={"lx": LX, "label": LABEL, "kmax": KMAX, "g2": 4.0, "m": P.m,
                                   "prune_tau": 1e-15, "selection_theta": "1 * dt of the sector",
                                   "proposals_A": PROPS_A, "proposals_B": PROPS_B},
                       seed={"random_superposition": list(SEEDS_SUPERPOSITION)}, t_start=t0)
    for cls in ("A", "B"):
        r = results[f"class_{cls}"]
        print(cls, r["n_2q_min"], r["n_2q_max"], round(r["n_2q_mean"], 2), r["depth_2q_min"], r["depth_2q_max"],
              r["n_pass"], r["max_certified_dev"], r["skeleton_k_independent"], "aer", results["aer"][cls]["n_pass"],
              results["aer"][cls]["max_abs_dpsi"])
    print(results["per_term_class_A"])
    print(results["aer"]["random_superposition"])
    print("wrote", p, f"({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main()
