#!/usr/bin/env python3
"""
Gates CV_2x3_plan and CV_2x2_info (prompts/30, owner decision 2a of 2026-10-05; amended by prompts/31,
2026-10-05): energy convergence against shots and against Krylov k, and weighted coverage, of the signed
2x3 shot plan (rule D3'-R) in the S1 proxy emulation; the same curves from the recorded H0_2x2 hardware
counts as an information block ("not a device test (saturation)").

  --source emulated-plan [--f 0.05 0.10 0.15] [--seeds 20260914 1 2] [--quick]
        One fragment per f under data/cv/fragment_2x3_f<f>.json (run one background chunk per f,
        each <= 27 min), then --assemble writes validation/CV_2x3_plan.json + reports/CV_2x3_plan.md.
        The plan is read from validation/Q0P_2x3_plan.json (data.plan_table.<f>.D3R, gate
        Q0P_2x3_plan of prompts/29 B3) or, if that file does not exist, built in-process with
        scripts/h0_support_plan.d3r_plan from the same inputs; `data.plan.source` records which.
  --source counts data/hardware/H0_2x2_ibm_kingston/counts --model 2
        validation/CV_2x2_info.json + reports/CV_2x2_information_20261005.md.

Definitions (prompts/30 section 2): B_all = R u accepted strings; B_sig = R u {s : n_s one-sided 3 sigma
Poisson above mu_s = N a / dim} (gate_H0_2x2.sig_support, P9 unchanged; a = the sector's exhaustive
random-string acceptance); W = captured exact ground-state weight; E_tol = skqd.skqd.h1_energy_tolerance.
Nested sub-samples are prefixes of each circuit's shot sequence (skqd.noise.measure_and_decode_sequence;
8 N_c shots sampled once per (sector, f, seed)).  Random equal-size baselines: controls.random_support
with seeds 23..222 (gate_H0_2x2.RANDOM_SEEDS).

prompts/31 (ruling 1-4): at 2x3 the criteria CV1-CV5 and the certificates are evaluated on B_all | refs
(manual Step 5.1; Na/dim < 1 there), B_sig is information; at 2x2 (saturation) the P9 basis B_sig stays.
CV2 reads the H1 width (B=0) on the Kato-Temple interval with the exact E1 (certify(...).kt_rigorous,
owner confirmation data/owner_decision_20261005_kt_certificate.md) and the H2 width (B=1) on Weinstein,
both at N/2 and N.  CV3 is the k = 4 -> 5 step at equal shots per circuit (the k = 5 coarse circuit of
every reference, sampled on the same per-seed generator stream after the k <= 4 equal-shots circuits).
Re-sizing grid {1.5, 2, 3, 4, 6, 8}.  The oracle-width table (data.oracle_width) reproduces the planner
prototype scratch/planner/oracle_width_20261005.json.

Numerics: device bases use skqd.skqd.ritz (dense eigh); the 200 random baselines per basis size use
the lowest eigenpair of the sparse projected block from scipy.sparse.linalg.eigsh (Lanczos, tol 1e-12;
agrees with the dense eigh to ~3e-14 at |B| = 100..677, measured 2026-10-05) because the dense path
costs 145 ms per basis at |B| = 500.  BLAS is pinned to one thread (deterministic tie-breaking of the
oracle, prompts/30 CV0; and the parallel K1 executor is not starved), except inside the oracle-width
table, which runs under the planner prototype's BLAS order (12 threads, the laptop default) because its
eps <= 3e-4 rows cut through groups of equal-weight states whose order depends on the thread count; the
tie envelope of every row is reported beside it.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from skqd.report import ROOT, GateResult, env_block, md_table, write_report  # noqa: E402

PROMPT = ("prompts/30_convergence_and_coverage_criteria.md (with prompts/29 Part B'), amended by "
          "prompts/31_CV_2x3_plan_fix_20261005.md")
G2 = 4.0
SEEDS = (20260914, 1, 2)                       # scripts/s2d_recall_at_predicted_f.py
F_GRID = (0.05, 0.10, 0.15)                    # prompts/28 B3 plan table
PHI = (1 / 16, 1 / 8, 1 / 4, 1 / 2, 1.0)       # criteria sub-samples
PHI_RESIZE = (1.5, 2, 3, 4, 6, 8)              # re-sizing grid (prompts/31 ruling 4)
SAMPLE_MULT = 8                                # 8 N_c shots per circuit sampled once
P_RO = 0.01                                    # gate S1 proxy readout flip
MARGIN = 0.7                                   # clean fraction 0.7 f for the criteria (D3'-R sizing margin)
WIDTH = {"B=0": 0.1, "B=1": 0.15}              # H1 width (B=0), H2 cluster r_H (B=1)
W_TARGET = 0.99                                # the weight of S99
RAND_LO, RAND_HI = 2.5, 97.5                   # prompts/27 Tier A percentile
DRAW_SEEDS_2X2 = tuple(range(2030, 2050))      # section 5 hypergeometric draws
TOL_MONO = 1e-12
TOL_VAR = 1e-9
TOL_E0_REF = 1e-12
TOL_T3 = 1e-9
LABEL_2X2 = "not a device test (saturation)"
CV_DIR = os.path.join(ROOT, "data", "cv")
PLAN_JSON = os.path.join(ROOT, "validation", "Q0P_2x3_plan.json")
SECTORS = (("B=0", 0), ("B=1", 2))
BASIS_2X3 = "all"                              # prompts/31 ruling 1: B_all | refs at 2x3
BASIS_2X2 = "sig"                              # P9 basis kept in the 2x2 saturation regime
CV2_TYPE = {"B=0": "kato_temple_exact_E1", "B=1": "weinstein"}   # prompts/31 ruling 2
K_NEXT = 5                                     # prompts/31 ruling 3: the k = 4 -> 5 step
OWNER_KT = "data/owner_decision_20261005_kt_certificate.md"
ORACLE_PROTOTYPE = os.path.join(ROOT, "scratch", "planner", "oracle_width_20261005.json")
ORACLE_EPS = (1e-2, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5, 1e-6)
ORACLE_BLAS_THREADS = 12                       # the prototype's BLAS order (laptop default)
ORACLE_F_SCALE = 0.10                          # the k = 4-scaled shots column at y = 0.82 x 0.7 x 0.10
TOL_ORACLE = 1e-9
RANKED_SIZES = (40, 80, 160)                   # P1 ranked curve sizes (plus |B_sig| and |B_all|)
DENSE_CLUSTER_MAX = 2000                       # B=1 cluster eigenvectors: dense eigh up to this sector dim (2x3: 426)


def rel(p):
    return os.path.relpath(p, ROOT)


def load_json(p):
    with open(p) as fh:
        return json.load(fh)


def ftag(f):
    return f"f={f:.2f}"


# =========================================================================== sector context
class Sector:
    """Everything one sector needs: H, the exact ground state, supports, references, acceptance."""

    def __init__(self, model, lattice, sec, twoB, acceptance):
        from threadpoolctl import threadpool_limits

        from skqd.krylov import references
        from skqd.skqd import exact_support

        self.sec, self.twoB, self.lattice = sec, twoB, lattice
        self.M = model
        self.H = model.H(G2).tocsr()
        with threadpool_limits(1):
            self.r = model.reference(G2, twoB, k=4)
        self.sector_idx = np.asarray(model.basis.sector(twoB), dtype=int)
        self.dim = int(len(self.sector_idx))
        self.prob = np.zeros(model.basis.dim)
        self.prob[self.r.indices] = np.abs(self.r.ground) ** 2
        self.E0 = float(self.r.E0)
        self.E1 = float(self.r.energies[1])
        self.dt = float(self.r.dt)
        self.spread = math.pi / self.dt              # E_max - E_0 by the anti-aliasing rule (manual 1.4)
        self.refs = [int(x) for x in references(model.basis, twoB)]
        self.S999 = np.sort(exact_support(self.prob, 1e-3))
        self.S99 = np.sort(exact_support(self.prob, 1e-2))
        self.a = float(acceptance)
        self._rand = {}
        self.cluster = None
        if twoB == 2:                                 # B=1 near-degenerate cluster (manual 1.5): W_cl as information
            if self.dim <= DENSE_CLUSTER_MAX:         # 2x2 / 2x3: the dense path of prompts/30 (unchanged)
                h = self.H[self.sector_idx][:, self.sector_idx].toarray()
                with threadpool_limits(1):
                    w, v = np.linalg.eigh(h)
            else:                                     # 2x4 (dim 8934): the three lowest by Lanczos (prompts/36)
                import scipy.sparse.linalg as spl
                h = self.H[self.sector_idx][:, self.sector_idx]
                with threadpool_limits(1):
                    w, v = spl.eigsh(h, k=3, which="SA", tol=1e-12, v0=np.ones(self.dim))
                o = np.argsort(w)
                w, v = w[o], v[:, o]
            self.cluster_energies = [float(x) for x in w[:3]]
            self.cluster = v[:, :3]

    # ---------------------------------------------------------------- one basis
    def basis_metrics(self, B):
        from skqd.skqd import certify, ritz, support_metrics
        B = np.asarray(sorted(set(int(b) for b in B)), dtype=int)
        res = ritz(self.H, B)
        cert = certify(res, self.E0, self.E1)
        m3 = support_metrics(B, self.prob, 1e-3)
        m2 = support_metrics(B, self.prob, 1e-2)
        W = float(m3["captured_weight"])
        Wcl = None
        if self.cluster is not None:
            pos = np.isin(self.sector_idx, B)
            Wcl = float(np.mean([np.sum(np.abs(self.cluster[pos, j]) ** 2) for j in range(3)]))
        ktr = None if cert.kt_rigorous is None else [float(x) for x in cert.kt_rigorous]
        return {"W_cluster": Wcl, "size": int(len(B)), "E_R": float(res.ER), "err": float(res.ER - self.E0), "rH": float(res.rH),
                "weinstein": [float(cert.weinstein[0]), float(cert.weinstein[1])],
                "E0_in_weinstein": bool(cert.weinstein[0] - TOL_VAR <= self.E0 <= cert.weinstein[1] + TOL_VAR),
                # Kato-Temple with beta = the exact E1 (manual 5.3; rigorous whenever E_R < E1): prompts/31 ruling 2
                "E_R_below_E1": bool(res.ER < self.E1),
                "kt_rigorous": ktr, "kt_width": None if ktr is None else float(ktr[1] - ktr[0]),
                "E0_in_kt": (None if ktr is None else bool(ktr[0] - TOL_VAR <= self.E0 <= ktr[1] + TOL_VAR)),
                "kato_temple": None if cert.kato_temple is None else [float(x) for x in cert.kato_temple],
                "gap_assumption_holds": cert.gap_assumption_holds,
                "W": W, "eq6_bound": float((1.0 - W) * self.spread / W) if W > 0 else None,
                "recall_S999": float(m3["recall"]), "recall_S99": float(m2["recall"]),
                "false_positives": int(m3["false_positives"])}

    # ---------------------------------------------------------------- random equal-size baselines
    def random_at(self, size):
        """200 random bases of `size` (references in), cached per size: E_R, r_H, W arrays."""
        import scipy.sparse.linalg as spl

        from skqd.controls import random_support
        from gate_H0_2x2 import RANDOM_SEEDS

        size = int(size)
        if size in self._rand:
            return self._rand[size]
        E, rH, W, has_R, sizes = [], [], [], True, []
        Rs = set(self.refs)
        for s in RANDOM_SEEDS:
            B = random_support(self.sector_idx, self.refs, size, np.random.default_rng(int(s)))
            B = np.asarray(B, dtype=int)
            has_R = has_R and Rs.issubset(set(int(x) for x in B))
            sizes.append(len(B))
            HB = self.H[B][:, B]
            if len(B) <= 24:
                w, v = np.linalg.eigh(HB.toarray())
                e, vec = float(w[0]), v[:, 0]
            else:
                w, v = spl.eigsh(HB, k=1, which="SA", tol=1e-12, v0=np.ones(len(B)))
                e, vec = float(w[0]), v[:, 0]
            psi = np.zeros(self.H.shape[0], dtype=complex)
            psi[B] = vec
            r = self.H @ psi - e * psi
            E.append(e)
            rH.append(float(np.linalg.norm(r)))
            W.append(float(self.prob[B].sum()))
        out = {"E": np.array(E), "rH": np.array(rH), "W": np.array(W), "contains_R": bool(has_R),
               "sizes_ok": bool(all(x == size for x in sizes)), "min_E": float(min(E))}
        self._rand[size] = out
        return out

    # ---------------------------------------------------------------- one point from counts
    def random_block(self, size, metrics):
        from gate_H0_2x2 import dist_summary, percentile_of
        rd = self.random_at(size)
        return {"size": int(size), "n": int(len(rd["E"])), "contains_R": rd["contains_R"], "sizes_ok": rd["sizes_ok"],
                "E_R": dist_summary(rd["E"]), "rH": dist_summary(rd["rH"]), "W": dist_summary(rd["W"]),
                "device_E_R_percentile": percentile_of(metrics["E_R"], rd["E"]),
                "device_W_percentile": float(100.0 * np.mean(rd["W"] <= metrics["W"] + 1e-15)),
                "min_E_R": rd["min_E"]}

    def point(self, n_full, shots, with_random=True, crit="sig", random_other=False):
        """n_full: accepted counts per full-basis index; shots: all shots of the point (sector total).
        crit: the criterion basis ("all" at 2x3 by prompts/31 ruling 1, "sig" at 2x2); `random` holds the
        200 random equal-size baselines at the criterion basis's size, `random_sig` (random_other) those at
        |B_sig| as information."""
        from gate_H0_2x2 import sig_support

        acc = np.flatnonzero(n_full > 0)
        mu = float(shots) * self.a / self.dim
        nd = {int(s): int(n_full[s]) for s in acc}
        sig, _pv = sig_support(nd, {s: mu for s in nd})
        B_all = sorted(set(self.refs) | set(int(s) for s in acc))
        B_sig = sorted(set(self.refs) | set(int(s) for s in sig))
        out = {"shots": int(shots), "mu_s": mu, "accepted": int(n_full.sum()), "n_distinct": int(len(acc)),
               "B_sig_list": B_sig, "B_all_size": len(B_all), "basis": crit,
               # expected number of garbage-born distinct states, dim (1 - exp(-mu_s)) (prompts/31 fix (f))
               "expected_garbage_born": float(self.dim * (1.0 - math.exp(-mu))),
               "sig": self.basis_metrics(B_sig), "all": self.basis_metrics(B_all)}
        out["_B_all"] = B_all
        if with_random:
            out["random"] = self.random_block(out[crit]["size"], out[crit])
            if random_other and crit != "sig":
                out["random_sig"] = self.random_block(out["sig"]["size"], out["sig"])
        return out

    def ranked(self, n_full, B_sig_size, B_all_size):
        """P1 protocol (manual Tables 3-4; prompts/31 ruling 1): top-|B| states by count (references always in,
        count ties broken by basis index), at RANKED_SIZES and at the P9 cut |B_sig| and at |B_all|."""
        from skqd.skqd import ritz
        acc = np.flatnonzero(n_full > 0)
        order = sorted((int(s) for s in acc if int(s) not in set(self.refs)), key=lambda s: (-int(n_full[s]), s))
        rows = []
        sizes = sorted(set([x for x in RANKED_SIZES if x < B_all_size] + [int(B_sig_size), int(B_all_size)]))
        for n in sizes:
            B = sorted(set(self.refs) | set(order[: max(0, n - len(self.refs))]))
            res = ritz(self.H, np.asarray(B, dtype=int))
            rows.append({"size": len(B), "E_R_minus_E0": float(res.ER - self.E0), "rH": float(res.rH),
                         "W": float(self.prob[B].sum()), "is_P9_cut": bool(n == B_sig_size),
                         "is_B_all": bool(n == B_all_size)})
        return rows


def strip(p):
    return {k: v for k, v in p.items() if not k.startswith("_")}


# =========================================================================== 2x3: inputs
def acceptance_2x3(codec):
    """Exhaustive per-sector acceptance of uniformly random 20-bit strings (gate_H0P.random_acceptance),
    cached in data/cv/acceptance_2x3.json."""
    from gate_H0P import random_acceptance

    p = os.path.join(CV_DIR, "acceptance_2x3.json")
    if os.path.exists(p):
        return load_json(p)
    os.makedirs(CV_DIR, exist_ok=True)
    t0 = time.time()
    out = {}
    for sec, tb in SECTORS:
        out[sec] = random_acceptance(codec, tb)
    out["runtime_s"] = time.time() - t0
    out["function"] = "scripts/gate_H0P.random_acceptance (2^20 strings through Codec.decode with the sector target)"
    with open(p, "w") as fh:
        json.dump(out, fh, indent=1)
    return out


def circuits_2x3():
    idx = load_json(os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", "index.json"))
    return {c: load_json(os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", c + ".manifest.json"))
            for c in idx["circuits"]}


def plan_for(f, mans, sectors):
    """{cid: N_c} of D3'-R at f, from validation/Q0P_2x3_plan.json or in-process."""
    key = ftag(f)
    if os.path.exists(PLAN_JSON):
        d = load_json(PLAN_JSON)["data"]
        row = d.get("plan_table", {}).get(key, {}).get("D3R")
        if row:
            return {c: int(v) for c, v in row["shots_by_circuit"].items()}, f"{rel(PLAN_JSON)} data.plan_table.{key}.D3R"
    from h0_support_plan import d3r_plan
    V = load_json(os.path.join(ROOT, "data", "quantinuum", "q0p_stages", "verify.json"))["per_circuit"]
    shots = {}
    for S in sectors.values():
        ids = sorted(c for c, m in mans.items() if int(m["twoB"]) == S.twoB)
        k4 = [c for c in ids if int(mans[c]["k"]) == 4]
        pos = {int(b): i for i, b in enumerate(S.r.indices)}
        P = {c: np.asarray(V[c]["p_sector"], float) / np.sum(V[c]["p_sector"]) for c in ids}
        d = d3r_plan(P, {c: f for c in ids}, ids, k4, [pos[int(s)] for s in S.S99], [pos[int(s)] for s in S.S999])
        shots.update(d["shots"])
    return shots, "in-process scripts/h0_support_plan.d3r_plan (validation/Q0P_2x3_plan.json absent)"


def circuit_states(S, mans):
    """{cid: full-basis state} of the signed family: coarse_states at k*dt from the manifest's reference."""
    from skqd.exact import mass_default
    from skqd.krylov import basis_vector, coarse_states, term_groups

    groups = term_groups(S.M.terms, G2, mass_default(G2))
    ids = sorted(c for c, m in mans.items() if int(m["twoB"]) == S.twoB)
    out, dts = {}, []
    by_ref = {}
    for c in ids:
        by_ref.setdefault(int(mans[c]["reference"]), []).append(c)
        dts.append(abs(float(mans[c]["dt"]) - S.dt))
    for ref, cs in by_ref.items():
        st = coarse_states(groups, basis_vector(S.M.basis.dim, ref), S.dt, 4)
        for c in cs:
            out[c] = st[int(mans[c]["k"])]
    return out, float(max(dts))


def k_next_states(S, refs=None, k=K_NEXT, dt=None):
    """prompts/31 ruling 3: {id: state} of the k = 5 coarse circuit of every reference (simulator only; the same
    coarse step at angle k dt, coarse_states(groups, psi, dt, 5)[5]).  Ids '<B0|B1>_ref<r>_k5'.  dt defaults to the
    sector reference's (2x3); the 2x4 path passes the frozen manifests' dt (gate_S2_2x4.dt_of, prompts/36 R3)."""
    from skqd.exact import mass_default
    from skqd.krylov import basis_vector, coarse_states, term_groups

    groups = term_groups(S.M.terms, G2, mass_default(G2))
    refs = S.refs if refs is None else refs
    tag = S.sec.replace("=", "")
    dt = S.dt if dt is None else float(dt)
    return {f"{tag}_ref{int(r)}_k{k}": coarse_states(groups, basis_vector(S.M.basis.dim, int(r)), dt, k)[k]
            for r in refs}


def sample_sequences(S, states, plan, mult, f_proxy, seed, codec, cw, tag, p_ro=P_RO, dtype=np.int16, cache_dir=CV_DIR):
    """{cid: decoded index per shot (-1 rejected)} of mult x plan[c] shots, circuits in sorted
    order on one generator; cached in <cache_dir>/<tag>.npz.  int16 at 2x3 (dim 1727); the 2x4 path passes
    int32 (dim 37165), p_ro = 0 and its own cache directory (prompts/36)."""
    from skqd.noise import measure_and_decode_sequence

    ids = sorted(states)
    path = os.path.join(cache_dir, tag + ".npz")
    want = {c: int(mult * plan[c]) for c in ids}
    if os.path.exists(path):
        z = np.load(path, allow_pickle=False)
        meta = json.loads(str(z["__meta__"]))
        if (meta.get("want") == want and abs(meta.get("f_proxy", -1) - f_proxy) < 1e-15 and meta.get("seed") == seed
                and meta.get("p_ro", P_RO) == p_ro):
            return {c: z[c] for c in ids}, {"cache": rel(path), "hit": True, "sampling_s": meta.get("sampling_s")}
    rng = np.random.default_rng(int(seed))
    t0 = time.time()
    seqs = {}
    for c in ids:
        dec, _why = measure_and_decode_sequence(codec, cw, states[c], want[c], f_proxy, p_ro, rng, S.twoB)
        seqs[c] = dec.astype(dtype)
    dt = time.time() - t0
    os.makedirs(cache_dir, exist_ok=True)
    meta = {"want": want, "f_proxy": f_proxy, "seed": int(seed), "p_ro": p_ro, "sampling_s": dt,
            "sector": S.sec, "rng": "numpy default_rng(seed), circuits in sorted id order"}
    np.savez_compressed(path, __meta__=json.dumps(meta), **seqs)
    return seqs, {"cache": rel(path), "hit": False, "sampling_s": dt}


def sample_k_next(S, states_eq, eq_want, states_k5, k5_want, f_proxy, seed, codec, cw, cached_eq, tag, p_ro=P_RO,
                  dtype=np.int16, cache_dir=CV_DIR):
    """The k = 5 sequences on the SAME per-seed generator stream as the equal-shots k <= 4 circuits: replay the
    equal-shots sampling (circuits in sorted id order, as sample_sequences), check that the replay reproduces the
    cached sequences exactly (cache integrity, CV0), then sample the k = 5 circuits in sorted id order.  Cached in
    data/cv/<tag>.npz."""
    from skqd.noise import measure_and_decode_sequence

    ids5 = sorted(states_k5)
    path = os.path.join(cache_dir, tag + ".npz")
    want = {c: int(k5_want[c]) for c in ids5}
    if os.path.exists(path):
        z = np.load(path, allow_pickle=False)
        meta = json.loads(str(z["__meta__"]))
        if (meta.get("want") == want and abs(meta.get("f_proxy", -1) - f_proxy) < 1e-15 and meta.get("seed") == seed
                and meta.get("p_ro", P_RO) == p_ro):
            return {c: z[c] for c in ids5}, {"cache": rel(path), "hit": True, "sampling_s": meta.get("sampling_s"),
                                             "replay_identical": meta.get("replay_identical")}
    rng = np.random.default_rng(int(seed))
    t0 = time.time()
    replay_ok = True
    for c in sorted(states_eq):
        dec, _ = measure_and_decode_sequence(codec, cw, states_eq[c], int(eq_want[c]), f_proxy, p_ro, rng, S.twoB)
        replay_ok &= bool(np.array_equal(dec.astype(dtype), cached_eq[c]))
    seqs = {}
    for c in ids5:
        dec, _ = measure_and_decode_sequence(codec, cw, states_k5[c], want[c], f_proxy, p_ro, rng, S.twoB)
        seqs[c] = dec.astype(dtype)
    dt = time.time() - t0
    os.makedirs(cache_dir, exist_ok=True)
    meta = {"want": want, "f_proxy": f_proxy, "seed": int(seed), "p_ro": p_ro, "sampling_s": dt, "sector": S.sec,
            "replay_identical": bool(replay_ok),
            "rng": ("numpy default_rng(seed); the equal-shots k <= 4 circuits replayed in sorted id order first, then the "
                    "k = 5 circuits in sorted id order (one continued stream per seed)")}
    np.savez_compressed(path, __meta__=json.dumps(meta), **seqs)
    return seqs, {"cache": rel(path), "hit": False, "sampling_s": dt, "replay_identical": bool(replay_ok)}


def counts_of(S, seqs, lengths):
    n = np.zeros(S.M.basis.dim, dtype=np.int64)
    shots = 0
    for c, L in lengths.items():
        x = seqs[c][: int(L)]
        x = x[x >= 0].astype(np.int64)
        if x.size:
            n += np.bincount(x, minlength=S.M.basis.dim)
        shots += int(L)
    return n, shots


def rnd(x):
    return int(math.floor(float(x) + 0.5))


def resized_shots(N, s, floor=267, round_to=100):
    """Section 4: s x D3'-R per circuit, floor circuits 267 s rounded up to 100; other circuits ceil(s N)
    (integer for every integer s; s = 1.5 on an odd N rounds up, prompts/31 ruling 4)."""
    if int(N) == floor:
        return int(math.ceil(floor * s / round_to - 1e-9) * round_to)
    return int(math.ceil(int(N) * s - 1e-9))


def pick_resize(grid, ok_at):
    """The smallest s of the grid (in order) at which ok_at(s) holds; None if none does.  ok_at is called lazily,
    in grid order, and not beyond the first passing value."""
    for s in grid:
        if ok_at(s):
            return s
    return None


# =========================================================================== 2x3: one (sector, f, seed)
def run_seed(S, states, plan_sec, f, seed, codec, cw, mans, E_tol, ckeep, states_k5=None, basis=BASIS_2X3,
             f_proxy=None, p_ro=P_RO, dtype=np.int16, cache_dir=CV_DIR):
    """One (sector, f, seed) of the emulation.  The 2x3 call uses the defaults (f_proxy = MARGIN f, the S1 proxy
    readout P_RO, int16 sequences in data/cv); the 2x4 noiseless path (prompts/36 A4) passes f_proxy = 1, p_ro = 0,
    int32 and data/cv/2x4."""
    ids = sorted(states)
    kof = {c: int(mans[c]["k"]) for c in ids}
    f_proxy = MARGIN * f if f_proxy is None else float(f_proxy)
    skw = {"p_ro": p_ro, "dtype": dtype, "cache_dir": cache_dir}
    t0 = time.time()
    seqs, sinfo = sample_sequences(S, states, plan_sec, SAMPLE_MULT, f_proxy, seed, codec, cw,
                                   f"{S.sec.replace('=', '')}_{f:.2f}_{seed}", **skw)
    N_sec = int(sum(plan_sec.values()))
    N_eq = int(math.ceil(N_sec / len(ids) / 100.0) * 100)
    eq_plan = {c: N_eq for c in ids}
    seqs_eq, sinfo_eq = sample_sequences(S, states, eq_plan, 2, f_proxy, seed, codec, cw,
                                         f"{S.sec.replace('=', '')}_{f:.2f}_{seed}_eq", **skw)
    seqs_k5, sinfo_k5 = {}, None
    if states_k5:
        seqs_k5, sinfo_k5 = sample_k_next(S, states, {c: 2 * N_eq for c in ids}, states_k5,
                                          {c: 2 * N_eq for c in states_k5}, f_proxy, seed, codec, cw, seqs_eq,
                                          f"{S.sec.replace('=', '')}_{f:.2f}_{seed}_eq_k{K_NEXT}", **skw)
    t_sample = time.time() - t0
    out = {"seed": int(seed), "f": f, "f_proxy_clean_fraction": f_proxy, "N_sector": N_sec, "N_eq_per_circuit": N_eq,
           "basis": basis, "sampling": {"plan": sinfo, "equal": sinfo_eq, "equal_k5": sinfo_k5, "wall_s": t_sample}}
    # ---- shots curve
    shots_pts, B_all_prev, n_prev, mono = [], None, None, {"B_all_nested": True, "counts_nondecreasing": True,
                                                            "E_R_all_nonincreasing": True, "B_sig_not_nested": 0,
                                                            "E_R_sig_increases": 0}
    n_full = None
    for phi in PHI:
        L = {c: rnd(phi * plan_sec[c]) for c in ids}
        n, sh = counts_of(S, seqs, L)
        p = S.point(n, sh, crit=basis, random_other=True)
        p["phi"] = phi
        if n_prev is not None:
            mono["counts_nondecreasing"] &= bool(np.all(n >= n_prev))
            mono["B_all_nested"] &= set(B_all_prev).issubset(set(p["_B_all"]))
            mono["E_R_all_nonincreasing"] &= bool(p["all"]["E_R"] <= shots_pts[-1]["all"]["E_R"] + TOL_MONO)
            if not set(shots_pts[-1]["B_sig_list"]).issubset(set(p["B_sig_list"])):
                mono["B_sig_not_nested"] += 1
            if p["sig"]["E_R"] > shots_pts[-1]["sig"]["E_R"] + TOL_MONO:
                mono["E_R_sig_increases"] += 1
        n_prev, B_all_prev = n, p["_B_all"]
        shots_pts.append(p)
        n_full = n
    # P1 ranked curve at the plan (information; prompts/31 ruling 1)
    shots_pts[-1]["ranked_by_count"] = S.ranked(n_full, shots_pts[-1]["sig"]["size"], shots_pts[-1]["B_all_size"])

    # ---- Krylov curves
    def kcurve(sq, lengths_of_k, kmax=4, extra=None, with_random=True):
        pts, prev = [], None
        km = {"B_all_nested": True, "E_R_all_nonincreasing": True, "B_sig_not_nested": 0}
        for k in range(1, kmax + 1):
            L = {c: lengths_of_k[c] for c in ids if kof[c] <= k}
            n, sh = counts_of(S, sq, L)
            if k > 4 and extra:
                n5, sh5 = counts_of(S, extra[0], extra[1])
                n, sh = n + n5, sh + sh5
            p = S.point(n, sh, crit=basis, with_random=with_random and k <= 4, random_other=True)
            p["k"] = k
            if prev is not None:
                km["B_all_nested"] &= set(prev["_B_all"]).issubset(set(p["_B_all"]))
                km["E_R_all_nonincreasing"] &= bool(p["all"]["E_R"] <= prev["all"]["E_R"] + TOL_MONO)
                if not set(prev["B_sig_list"]).issubset(set(p["B_sig_list"])):
                    km["B_sig_not_nested"] += 1
            prev = p
            pts.append(p)
        return pts, km
    alloc, km_a = kcurve(seqs, plan_sec)
    kmax_eq = K_NEXT if states_k5 else 4
    eq1, km_e = kcurve(seqs_eq, {c: N_eq for c in ids}, kmax_eq, (seqs_k5, {c: N_eq for c in seqs_k5}))
    eq2, km_e2 = kcurve(seqs_eq, {c: 2 * N_eq for c in ids}, kmax_eq, (seqs_k5, {c: 2 * N_eq for c in seqs_k5}))
    # ---- CV0 (per seed): variational, random baselines contain R, the k = 5 replay reproduced the cache
    allpts = shots_pts + alloc + eq1 + eq2
    var_ok = all(p["sig"]["E_R"] >= S.E0 - TOL_VAR and p["all"]["E_R"] >= S.E0 - TOL_VAR
                 and (("random" not in p) or p["random"]["min_E_R"] >= S.E0 - TOL_VAR) for p in allpts)
    rand_R = all(p["random"]["contains_R"] and p["random"]["sizes_ok"] for p in allpts if "random" in p)
    replay_ok = bool(sinfo_k5 is None or sinfo_k5.get("replay_identical"))
    cv0 = {"monotone_shots": mono, "monotone_alloc": km_a, "monotone_equal": km_e, "monotone_equal_2x": km_e2,
           "variational_ok": var_ok, "random_contain_R": rand_R, "k5_stream_replay_identical": replay_ok}
    cv0["ok"] = bool(mono["B_all_nested"] and mono["counts_nondecreasing"] and mono["E_R_all_nonincreasing"]
                     and km_a["B_all_nested"] and km_a["E_R_all_nonincreasing"] and km_e["B_all_nested"]
                     and km_e["E_R_all_nonincreasing"] and km_e2["B_all_nested"] and km_e2["E_R_all_nonincreasing"]
                     and var_ok and rand_R and replay_ok)
    # ---- CV1-CV5 at the 1x plan
    half, full = shots_pts[3], shots_pts[4]
    crit = evaluate(S, half, full, shots_pts, eq1[:4], E_tol, basis,
                    k_step=(eq1[3], eq1[4]) if len(eq1) > 4 else None)
    if len(eq2) > 4:
        crit["CV3_at_2Nc_information"] = cv3_block(S, eq2[3], eq2[4], E_tol, basis)
    # slope of log(E_R - E0) vs log phi over the last three points (information)
    xs = np.log([p["phi"] for p in shots_pts[2:]])
    ys = [p[basis]["err"] for p in shots_pts[2:]]
    crit["slope_last3_information"] = (float(np.polyfit(xs, np.log(ys), 1)[0]) if all(y > 0 for y in ys) else None)
    out.update({"curves": {"shots": [strip(p) for p in shots_pts], "krylov_allocation": [strip(p) for p in alloc],
                           "krylov_equal": [strip(p) for p in eq1], "krylov_equal_2x": [strip(p) for p in eq2]},
                "cv0": cv0, "criteria_1x": crit, "_seqs": seqs, "_ids": ids, "runtime_s": time.time() - t0})
    if not ckeep:
        for p in out["curves"].values():
            for q in p:
                q.pop("B_sig_list", None)
    return out


def cv2_block(S, half, full, b):
    """prompts/31 ruling 2: B=0 the Kato-Temple width with the exact E1, r_H^2 / (E1 - E_R) <= 0.1 at N/2 and N with
    E_R < E1 and E0 in [E_R - delta_KT, E_R]; B=1 the Weinstein r_H <= 0.15 at N/2 and N with E0 in [E_R - r_H, E_R].
    Both intervals are recorded at both points."""
    w = WIDTH[S.sec]
    typ = CV2_TYPE[S.sec]
    h, f_ = half[b], full[b]
    out = {"type": typ, "width": w, "owner_confirmation": OWNER_KT if typ.startswith("kato") else None,
           "rH_half": h["rH"], "rH_full": f_["rH"], "weinstein_half": h["weinstein"], "weinstein_full": f_["weinstein"],
           "E0_in_weinstein_half": h["E0_in_weinstein"], "E0_in_weinstein_full": f_["E0_in_weinstein"],
           "kt_width_half": h["kt_width"], "kt_width_full": f_["kt_width"],
           "kt_rigorous_half": h["kt_rigorous"], "kt_rigorous_full": f_["kt_rigorous"],
           "E0_in_kt_half": h["E0_in_kt"], "E0_in_kt_full": f_["E0_in_kt"],
           "E_R_below_E1_half": h["E_R_below_E1"], "E_R_below_E1_full": f_["E_R_below_E1"],
           "gap_half": h["gap_assumption_holds"], "gap_full": f_["gap_assumption_holds"]}
    if typ == "kato_temple_exact_E1":
        out["width_half"], out["width_full"] = h["kt_width"], f_["kt_width"]
        out["E0_in_half"], out["E0_in_full"] = h["E0_in_kt"], f_["E0_in_kt"]
        out["ok"] = bool(h["E_R_below_E1"] and f_["E_R_below_E1"] and h["kt_width"] is not None
                         and f_["kt_width"] is not None and h["kt_width"] <= w and f_["kt_width"] <= w
                         and h["E0_in_kt"] and f_["E0_in_kt"])
    else:
        out["width_half"], out["width_full"] = h["rH"], f_["rH"]
        out["E0_in_half"], out["E0_in_full"] = h["E0_in_weinstein"], f_["E0_in_weinstein"]
        out["ok"] = bool(h["rH"] <= w and f_["rH"] <= w and h["E0_in_weinstein"] and f_["E0_in_weinstein"])
    return out


def cv3_block(S, p4, p5, E_tol, b):
    """prompts/31 ruling 3: E_R(B^(4)) - E_R(B^(5)) <= E_tol at equal shots per circuit; no width condition."""
    d = p4[b]["E_R"] - p5[b]["E_R"]
    return {"dE_k4_k5": d, "ratio": d / E_tol, "ok": bool(d <= E_tol), "E_R_k4": p4[b]["E_R"], "E_R_k5": p5[b]["E_R"],
            "size_k4": p4[b]["size"], "size_k5": p5[b]["size"], "rH_k4_information": p4[b]["rH"],
            "rH_k5_information": p5[b]["rH"], "shots_k4": p4["shots"], "shots_k5": p5["shots"]}


def evaluate(S, half, full, shots_pts, eq_pts, E_tol, basis, k_step=None, extra_cv4=()):
    """CV1-CV5 for one seed from the half / full points on `basis` ("all" at 2x3, "sig" at 2x2); CV3 from the
    equal-shots k = 4 -> 5 step when given (prompts/31)."""
    b = basis
    d1 = half[b]["E_R"] - full[b]["E_R"]
    cv1 = {"dE": d1, "ratio": d1 / E_tol, "ok": bool(d1 <= E_tol)}
    cv2 = cv2_block(S, half, full, b)
    out = {"CV1": cv1, "CV2": cv2}
    if k_step is not None:
        out["CV3"] = cv3_block(S, k_step[0], k_step[1], E_tol, b)
    pts = list(shots_pts) + list(eq_pts) + list(extra_cv4)
    below = [bool(p[b]["E_R"] < p["random"]["E_R"]["p2_5"]) for p in pts]
    margin = full["random"]["E_R"]["p2_5"] - full[b]["E_R"]
    cv4 = {"all_points_below_p2_5": bool(all(below)), "n_points": len(pts), "n_below": int(sum(below)),
           "margin_at_N": margin, "margin_over_E_tol": margin / E_tol,
           "W_at_N": full[b]["W"], "W_rand_p97_5": full["random"]["W"]["p97_5"]}
    cv4["ok"] = bool(cv4["all_points_below_p2_5"] and margin >= E_tol and cv4["W_at_N"] > cv4["W_rand_p97_5"])
    cv5 = {"W_at_N": full[b]["W"], "W_sig_at_N": full["sig"]["W"], "W_all_at_N": full["all"]["W"],
           "ok": bool(full[b]["W"] >= W_TARGET),
           "recall_S999_sig": full["sig"]["recall_S999"], "recall_S999_all": full["all"]["recall_S999"],
           "recall_S99_sig": full["sig"]["recall_S99"], "recall_S99_all": full["all"]["recall_S99"]}
    out.update({"CV4": cv4, "CV5": cv5, "basis": b})
    return out


def resize_points(S, seqs, ids, plan_sec, s, basis=BASIS_2X3):
    Ns = {c: resized_shots(plan_sec[c], s) for c in ids}
    avail = {c: int(len(seqs[c])) for c in ids}
    Lf = {c: min(Ns[c], avail[c]) for c in ids}
    Lh = {c: min(rnd(Ns[c] / 2.0), avail[c]) for c in ids}
    capped = sorted(c for c in ids if Ns[c] > avail[c])
    nh, sh_h = counts_of(S, seqs, Lh)
    nf, sh_f = counts_of(S, seqs, Lf)
    ph, pf = S.point(nh, sh_h, crit=basis, random_other=True), S.point(nf, sh_f, crit=basis, random_other=True)
    ph["s_point"], pf["s_point"] = f"{s}N/2", f"{s}N"
    return ph, pf, Ns, capped


# =========================================================================== 2x3 chunk (one f)
def chunk_2x3(f, seeds, quick=False):
    from skqd.codec import Codec
    from skqd.exact import Model
    from skqd.skqd import h1_energy_tolerance

    t0 = time.time()
    M = Model(3)
    codec = Codec(M.basis)
    cw = codec.all_codewords()
    acc = acceptance_2x3(codec)
    sectors = {sec: Sector(M, "2x3", sec, tb, acc[sec]["fraction"]) for sec, tb in SECTORS}
    if quick:
        from gate_H0_2x2 import RANDOM_SEEDS
        del RANDOM_SEEDS[50:]
    mans = circuits_2x3()
    plan, plan_src = plan_for(f, mans, sectors)
    frag = {"f": f, "seeds": list(seeds), "plan_source": plan_src, "quick": bool(quick), "sectors": {}}
    for sec, S in sectors.items():
        E_tol = h1_energy_tolerance(S.H, S.prob, S.refs, 0.8, 1e-3, sector_idx=S.sector_idx, E0=S.E0)["E_tol"]
        states, dt_dev = circuit_states(S, mans)
        ids = sorted(states)
        plan_sec = {c: int(plan[c]) for c in ids}
        # CV0: the sequence sampler's histogram = measure_and_decode's (first circuit, this seed, its 8 N_c draw)
        from skqd.noise import measure_and_decode, measure_and_decode_sequence
        c0 = ids[0]
        n0 = SAMPLE_MULT * plan_sec[c0]
        dec, _ = measure_and_decode_sequence(codec, cw, states[c0], n0, MARGIN * f, P_RO,
                                             np.random.default_rng(int(seeds[0])), S.twoB)
        a_ref, _ = measure_and_decode(codec, cw, states[c0], n0, MARGIN * f, P_RO,
                                      np.random.default_rng(int(seeds[0])), S.twoB)
        u, cnt = np.unique(dec[dec >= 0], return_counts=True)
        hist_ok = {int(k): int(v) for k, v in zip(u, cnt)} == {int(k): int(v) for k, v in a_ref.items()}
        states_k5 = k_next_states(S)
        per_seed, any_fail = {}, False
        for seed in seeds:
            rs = run_seed(S, states, plan_sec, f, seed, codec, cw, mans, E_tol, ckeep=False, states_k5=states_k5)
            c = rs["criteria_1x"]
            if not all(c[k]["ok"] for k in ("CV1", "CV2", "CV4", "CV5")):
                any_fail = True
            per_seed[str(seed)] = rs
            print(f"  [{sec} {ftag(f)} seed {seed}] " + " ".join(f"{k}:{'ok' if c[k]['ok'] else 'FAIL'}" for k in
                                                                  ("CV1", "CV2", "CV3", "CV4", "CV5"))
                  + f" cv0:{'ok' if rs['cv0']['ok'] else 'FAIL'} ({rs['runtime_s']:.0f} s)", flush=True)
        # ---- section 4 / prompts/31 ruling 4: lazy re-sizing on the prefixes of the same 8N samples
        resize, s_final = {}, 1
        if any_fail:
            def ok_at(s):
                res_s, ok_all = {}, True
                for seed in seeds:
                    rs = per_seed[str(seed)]
                    ph, pf, Ns, capped = resize_points(S, rs["_seqs"], ids, plan_sec, s)
                    crit = evaluate(S, ph, pf, rs["curves"]["shots"], rs["curves"]["krylov_equal"][:4], E_tol,
                                    BASIS_2X3, extra_cv4=(ph, pf))
                    ok = all(crit[k]["ok"] for k in ("CV1", "CV2", "CV4", "CV5"))
                    ok_all &= ok
                    res_s[str(seed)] = {"half": strip(ph), "full": strip(pf), "criteria": crit, "ok": ok,
                                        "capped_circuits": capped}
                    for q in (res_s[str(seed)]["half"], res_s[str(seed)]["full"]):
                        q.pop("B_sig_list", None)
                resize[str(s)] = {"shots_by_circuit": Ns, "shots_total": int(sum(Ns.values())), "seeds": res_s,
                                  "ok_all_seeds": ok_all}
                print(f"  [{sec} {ftag(f)}] resize s={s}: {'PASS' if ok_all else 'FAIL'}", flush=True)
                return ok_all
            s_final = pick_resize(PHI_RESIZE, ok_at)
        for rs in per_seed.values():
            rs.pop("_seqs", None)
            rs.pop("_ids", None)
        frag["sectors"][sec] = {"E_tol": E_tol, "ids": ids, "plan_1x": plan_sec, "N_sector_1x": int(sum(plan_sec.values())),
                                "manifest_dt_vs_reference_dt_max_abs": dt_dev, "sequence_histogram_identity": hist_ok,
                                "sequence_identity_circuit": c0, "seeds": per_seed, "resize": resize,
                                "k5_ids": sorted(states_k5),
                                "resized_by": s_final, "any_1x_failure": any_fail}
    frag["runtime_s"] = time.time() - t0
    frag["random_baseline_sizes_evaluated"] = {sec: len(S._rand) for sec, S in sectors.items()}
    os.makedirs(CV_DIR, exist_ok=True)
    p = os.path.join(CV_DIR, f"fragment_2x3_{ftag(f).replace('=', '')}{'_quick' if quick else ''}.json")
    with open(p, "w") as fh:
        json.dump(_j(frag), fh, indent=1)
    print(f"wrote {rel(p)} ({frag['runtime_s']:.0f} s)")
    return frag


def _j(x):
    from skqd.report import _jsonable
    return _jsonable(x)


# =========================================================================== oracle-width table (prompts/31 fix (e))
def oracle_width(M, twoB, blas_threads=ORACLE_BLAS_THREADS):
    """The certificate width of the oracle supports S_eps u R (prompts/31 D1), the planner prototype's computation
    (scratch/planner/oracle_width_20261005.py) with the reference eigenvector under its BLAS order (the order of
    equal-weight states at the S_eps boundary depends on it; everything else runs on one thread), with the tie envelope of each row: when the
    S_eps boundary cuts through a group of equal-weight states, E_R - E0, r_H and delta_KT over every equally valid
    choice of the tied states."""
    import itertools

    from threadpoolctl import threadpool_limits

    from skqd.exact import mass_default
    from skqd.krylov import basis_vector, coarse_states, references, term_groups
    from skqd.skqd import READOUT_FACTOR, certify, exact_support, poisson_lambda_star, ritz

    y = READOUT_FACTOR * MARGIN * ORACLE_F_SCALE
    lam = poisson_lambda_star()
    with threadpool_limits(blas_threads):           # the prototype's BLAS order fixes the eigenvector round-off
        r = M.reference(G2, twoB, k=4)
    with threadpool_limits(1):
        H = M.H(G2)
        groups = term_groups(M.terms, G2, mass_default(G2))
        E0, E1 = float(r.E0), float(r.energies[1])
        prob = np.zeros(M.basis.dim)
        prob[r.indices] = np.abs(r.ground) ** 2
        refs = [int(x) for x in references(M.basis, twoB)]
        sts = [st for rr in refs for st in coarse_states(groups, basis_vector(M.basis.dim, rr), r.dt, 4)[1:]]
        P = np.array([np.abs(st) ** 2 for st in sts])
        Hd = np.real(H.diagonal())
        S999 = exact_support(prob, 1e-3)
        order = np.argsort(prob)[::-1]
        rows = {}
        for eps in ORACLE_EPS:
            S = exact_support(prob, eps)
            B = sorted(set(int(x) for x in S) | set(refs))
            res = ritz(H, B)
            c = certify(res, E0, E1)
            W = float(prob[B].sum())
            outside = np.setdiff1d(np.arange(M.basis.dim), B)
            est = float(np.sqrt(np.sum((E0 - Hd[outside]) ** 2 * prob[outside])))
            new = np.setdiff1d(S, S999)
            pmax = P[:, S].max(axis=0)
            psum = P[:, S].sum(axis=0)
            row = dict(size=len(B), ER_minus_E0=float(res.ER - E0), rH=float(res.rH), W=W, one_minus_W=1 - W,
                       rH_estimate_E0_minus_Hnn=est,
                       kt_width_exact_E1=(None if c.kt_rigorous is None else float(res.ER - c.kt_rigorous[0])),
                       gap_holds=c.gap_assumption_holds, alpha_second_ritz=float(res.ER1),
                       min_pmax=float(pmax.min()), min_psum=float(psum.min()),
                       n_states_pmax_below_1e4=int((pmax < 1e-4).sum()),
                       N_k4scaled_shots_at_y0574=(float(lam / (y * pmax.min())) if pmax.min() > 0 else float("inf")),
                       states_beyond_S999=int(len(new)))
            # tie envelope at the S_eps boundary
            k = len(S)
            wb = prob[order[k - 1]]
            grp = [int(x) for x in np.flatnonzero(np.abs(prob - wb) <= 1e-9 * wb + 1e-15)]
            inside = [g for g in grp if g in set(int(x) for x in S)]
            tie = {"group_size": len(grp), "boundary_weight": float(wb), "straddles": bool(0 < len(inside) < len(grp))}
            if tie["straddles"]:
                base = sorted(set(int(x) for x in S) - set(grp))
                vals = []
                for cmb in itertools.combinations(grp, len(inside)):
                    Bc = sorted(set(base) | set(cmb) | set(refs))
                    rc = ritz(H, Bc)
                    kt = (rc.rH ** 2 / (E1 - rc.ER)) if E1 - rc.ER > 1e-6 else None
                    vals.append((float(rc.ER - E0), float(rc.rH), kt))
                tie.update({"n_choices": len(vals), "ER_minus_E0_range": [min(v[0] for v in vals), max(v[0] for v in vals)],
                            "rH_range": [min(v[1] for v in vals), max(v[1] for v in vals)],
                            "kt_width_range": (None if any(v[2] is None for v in vals) else
                                               [min(v[2] for v in vals), max(v[2] for v in vals)])})
            row["tie_envelope_information"] = tie
            rows[f"{eps:g}"] = row
    return {"E0": E0, "E1": E1, "dt": float(r.dt), "rows": rows, "y_k4_scaled": y, "lambda_star": lam,
            "blas_threads": blas_threads}


def oracle_reproduction(table, proto_path=ORACLE_PROTOTYPE):
    """CV0: every numeric field of every prototype row reproduced to TOL_ORACLE (relative to max(1, |value|)),
    integers / booleans / None exactly, inf = inf."""
    if not os.path.exists(proto_path):
        return {"ok": False, "reason": f"{rel(proto_path)} absent"}
    proto = load_json(proto_path)
    worst, n, bad = 0.0, 0, []
    for sec in ("B=0", "B=1"):
        for eps, pr in proto[sec]["rows"].items():
            gr = table[sec]["rows"].get(eps)
            if gr is None:
                bad.append(f"{sec} {eps} missing")
                continue
            for key, v in pr.items():
                g = gr.get(key)
                n += 1
                if isinstance(v, bool) or v is None or isinstance(v, int):
                    if g != v:
                        bad.append(f"{sec} {eps} {key}: {g} vs {v}")
                elif isinstance(v, float):
                    if math.isinf(v) or (g is not None and isinstance(g, float) and math.isinf(g)):
                        if not (g is not None and math.isinf(g) and math.isinf(v)):
                            bad.append(f"{sec} {eps} {key}: {g} vs {v}")
                        continue
                    d = abs(float(g) - v) / max(1.0, abs(v))
                    worst = max(worst, d)
                    if d > TOL_ORACLE:
                        bad.append(f"{sec} {eps} {key}: {g} vs {v}")
    return {"ok": not bad, "fields_compared": n, "max_scaled_diff": worst, "differing": bad[:20],
            "prototype": rel(proto_path), "tolerance": TOL_ORACLE,
            "rule": "|gate - prototype| <= 1e-9 max(1, |prototype|) on floats; exact on integers, booleans, None, inf"}


# =========================================================================== 2x3 assembly
def sector_info(S, H1tol):
    """E_tol (both recall targets), E0 vs references.json, Table 3 oracle reproduction, W_cl, supports."""
    from threadpoolctl import threadpool_limits

    from skqd.skqd import h1_energy_tolerance, ritz

    refj = load_json(os.path.join(ROOT, "data", "references.json"))["references"]
    rj = refj[f"{S.lattice}|g2={G2}|2B={S.twoB}"]
    et = h1_energy_tolerance(S.H, S.prob, S.refs, 0.8, 1e-3, sector_idx=S.sector_idx, E0=S.E0)
    et9 = h1_energy_tolerance(S.H, S.prob, S.refs, 0.9, 1e-3, sector_idx=S.sector_idx, E0=S.E0)
    info = {"dim": S.dim, "E0": S.E0, "E1": S.E1, "E0_references_json": float(rj["energies"][0]),
            "E0_abs_diff_references_json": abs(S.E0 - float(rj["energies"][0])), "dt": S.dt,
            "Emax_minus_E0_anti_aliasing_pi_over_dt": S.spread, "Emax_minus_E0_exact": float(S.r.emax - S.E0),
            "references": S.refs, "S999_size": int(len(S.S999)), "S99_size": int(len(S.S99)),
            "S999": [int(x) for x in S.S999], "S99": [int(x) for x in S.S99],
            "W_S99": float(S.prob[S.S99].sum()), "W_S999": float(S.prob[S.S999].sum()),
            "garbage_acceptance": S.a, "E_tol": et, "E_tol_recall_0.9_information": et9}
    if H1tol and S.lattice == "2x3":
        t3 = load_json(os.path.join(ROOT, "validation", "S1.json"))["data"]["table3"]
        rows = {}
        with threadpool_limits(1):
            for n in (40, 80):
                o = h1_energy_tolerance(S.H, S.prob, [], n / len(S.S999), 1e-3, sector_idx=S.sector_idx, E0=S.E0)
                ref = float(t3[f"{S.sec}|oracle|{n}"]["err"])
                rows[str(n)] = {"E_tol_code_path": o["E_tol"], "table3": ref, "abs_diff": abs(o["E_tol"] - ref),
                                "n_top": o["n_top"], "ok": bool(abs(o["E_tol"] - ref) <= TOL_T3)}
        # tie spread at the |B| boundary (information): states of equal weight to round-off
        o = S.sector_idx[np.argsort(S.prob[S.sector_idx])[::-1]]
        ties = {}
        for n in (40, 80):
            wb = S.prob[o[n - 1]]
            grp = [int(x) for x in o if abs(S.prob[x] - wb) <= 1e-12 * wb]
            if len(grp) > 1:
                base = [int(x) for x in o[:n] if int(x) not in grp]
                need = n - len(base)
                import itertools
                vals = [ritz(S.H, np.array(sorted(base + list(cmb)))).ER - S.E0 for cmb in itertools.combinations(grp, need)]
                ties[str(n)] = {"tied_states": grp, "weight": float(wb), "n_choices": len(vals),
                                "E_err_min": float(min(vals)), "E_err_max": float(max(vals))}
        info["table3_oracle"] = rows
        info["table3_oracle_tie_information"] = ties
    if S.cluster is not None:
        info["cluster_energies"] = S.cluster_energies
        info["W_cluster_definition"] = "W_cl(B) = (1/3) sum_{j=0..2} sum_{s in B} |c_s^(j)|^2 over the three cluster states"
    return info


def assemble_2x3(fs, seeds, quick=False):
    import gate_Q0P_2x3 as Q
    from skqd.codec import Codec
    from skqd.exact import Model

    t0 = time.time()
    frags = {}
    for f in fs:
        p = os.path.join(CV_DIR, f"fragment_2x3_{ftag(f).replace('=', '')}{'_quick' if quick else ''}.json")
        if os.path.exists(p):
            frags[ftag(f)] = load_json(p)
    M = Model(3)
    codec = Codec(M.basis)
    acc = acceptance_2x3(codec)
    sectors = {sec: Sector(M, "2x3", sec, tb, acc[sec]["fraction"]) for sec, tb in SECTORS}
    infos = {sec: sector_info(S, True) for sec, S in sectors.items()}
    owt = {sec: oracle_width(M, tb) for sec, tb in SECTORS}
    orep = oracle_reproduction(owt)
    _idx, mans, _cals = Q.manifests()
    hqc_by_id = {c: m["hqc_per_shot"] for c, m in mans.items()}
    table = load_json(Q.DEVICES)
    usd = table["billing"]["usd_per_hqc_ESTIMATE"]["value"]
    shot_s = table["rows"]["2x3|quantinuum_h2_2"]["memory_ESTIMATE"]["scenarios"]["mid"]["shot_time_s"]
    gate = "CV_2x3_plan" + ("_quick" if quick else "")
    R = GateResult(gate, "energy convergence (shots, Krylov k) and weighted coverage of the 2x3 D3'-R plan in the S1 "
                         "proxy emulation (owner decision 2a), on B_all | refs (prompts/31)")
    plan_out, crit_rows, E_tol = {}, {}, {}
    resize_summary, cv3_2x, stops, cv3_fail = {}, {}, [], []
    for sec, S in sectors.items():
        info = infos[sec]
        E_tol[sec] = {"value": info["E_tol"]["E_tol"], "states_top": info["E_tol"]["states_top"],
                      "n_top": info["E_tol"]["n_top"], "references": info["E_tol"]["references"],
                      "E_R": info["E_tol"]["E_R"], "recall_0.9_information": info["E_tol_recall_0.9_information"]["E_tol"]}
    R.add("CV0 oracle-width table (prompts/31 D1) reproduces the planner prototype scratch/planner/oracle_width_20261005.json",
          f"{orep.get('fields_compared')} fields; max scaled difference {orep.get('max_scaled_diff', float('nan')):.1e}; "
          f"differing {orep.get('differing') or 'none'}", f"<= {TOL_ORACLE:g}", orep["ok"])
    if not orep["ok"]:
        stops.append("CV0 oracle-width reproduction")
    for fk, fr in frags.items():
        for sec, S in sectors.items():
            sd = fr["sectors"][sec]
            info = infos[sec]
            et = sd["E_tol"]
            s_fin = sd["resized_by"]
            seeds_d = sd["seeds"]
            # ---- CV0
            t3_ok = all(r["ok"] for r in info["table3_oracle"].values())
            e0_ok = info["E0_abs_diff_references_json"] <= TOL_E0_REF
            etol_same = abs(et - info["E_tol"]["E_tol"]) <= 1e-15
            cv0_seed = all(rs["cv0"]["ok"] for rs in seeds_d.values())
            replay = all(rs["cv0"].get("k5_stream_replay_identical") for rs in seeds_d.values())
            cv0 = bool(cv0_seed and sd["sequence_histogram_identity"] and t3_ok and e0_ok and etol_same)
            nest_sig = sum(rs["cv0"]["monotone_shots"]["B_sig_not_nested"] for rs in seeds_d.values())
            R.add(f"CV0 {sec} {fk}: prefixes nested (B_all, counts), E_R(B_all) non-increasing (shots, k = 1..5), E_R >= E0 - "
                  f"1e-9 everywhere, sequence histogram = measure_and_decode, k = 5 stream replay = cache, E0 = references.json, "
                  f"Table 3 oracle 40/80, random bases contain R",
                  f"seeds {'ok' if cv0_seed else 'FAIL'}; histogram {'identical' if sd['sequence_histogram_identity'] else 'DIFFERS'}; "
                  f"k = 5 replay {'identical' if replay else 'DIFFERS'}; E0 diff {info['E0_abs_diff_references_json']:.1e}; "
                  f"Table 3 diffs " + "/".join(f"{r['abs_diff']:.1e}" for r in info["table3_oracle"].values())
                  + f"; B_sig non-nested steps {nest_sig} (information)",
                  f"structural; <= {TOL_E0_REF:g}; <= {TOL_T3:g}", cv0)
            if not cv0:
                stops.append(f"CV0 {sec} {fk}")

            # ---- CV1-CV5 at the final plan
            def final_crit(rs, seed):
                if s_fin in (1, None):
                    return rs["criteria_1x"]
                c = dict(sd["resize"][str(s_fin)]["seeds"][str(seed)]["criteria"])
                c["CV3"] = rs["criteria_1x"]["CV3"]
                return c
            cs = {seed: final_crit(rs, seed) for seed, rs in seeds_d.items()}
            tag = f"{sec} {fk}" + (f" (plan D3'-R x{s_fin})" if s_fin not in (1, None) else
                                   (" (1x; re-sizing up to x8 also fails: STOP)" if s_fin is None else " (1x plan)"))
            ladder = {}
            for s_, rz in sd["resize"].items():
                ladder[s_] = {"ok_all_seeds": rz["ok_all_seeds"], "shots_total": rz["shots_total"],
                              "criteria_ok": {k: all(v["criteria"][k]["ok"] for v in rz["seeds"].values())
                                              for k in ("CV1", "CV2", "CV4", "CV5")},
                              "width_half_max": max(v["criteria"]["CV2"]["width_half"] for v in rz["seeds"].values()),
                              "width_full_max": max(v["criteria"]["CV2"]["width_full"] for v in rz["seeds"].values()),
                              "rH_half_B_all_max": max(v["half"]["all"]["rH"] for v in rz["seeds"].values()),
                              "rH_half_B_sig_max": max(v["half"]["sig"]["rH"] for v in rz["seeds"].values()),
                              "size_B_sig_full": [v["full"]["sig"]["size"] for v in rz["seeds"].values()],
                              "size_B_all_full": [v["full"]["B_all_size"] for v in rz["seeds"].values()],
                              "mu_s_full": [v["full"]["mu_s"] for v in rz["seeds"].values()]}
            resize_summary.setdefault(fk, {})[sec] = ladder
            cv3x2 = {seed: rs["criteria_1x"].get("CV3_at_2Nc_information") for seed, rs in seeds_d.items()}
            cv3_2x.setdefault(fk, {})[sec] = cv3x2
            c3 = {seed: rs["criteria_1x"]["CV3"] for seed, rs in seeds_d.items()}
            if not all(c["ok"] for c in c3.values()):
                cv3_fail.append(f"CV3 {sec} {fk}")
            if s_fin is None:
                stops.append(f"re-sizing s = 8 fails {sec} {fk}")
            w = WIDTH[sec]
            typ = CV2_TYPE[sec]
            R.add(f"CV1 {tag}: E_R(N/2) - E_R(N) <= E_tol on B_all (all seeds)",
                  "; ".join(f"{c['CV1']['dE']:.2e} ({c['CV1']['ratio']:.2f} E_tol)" for c in cs.values()) + f"; E_tol {et:.4e}",
                  f"<= E_tol = {et:.4e}", all(c["CV1"]["ok"] for c in cs.values()))
            if typ == "kato_temple_exact_E1":
                R.add(f"CV2 {tag}: Kato-Temple (exact E1) delta_KT = r_H^2/(E1 - E_R) <= {w} at N/2 and N, E_R < E1, "
                      f"E0 in [E_R - delta_KT, E_R] on B_all (all seeds; H1 width, {OWNER_KT}); Weinstein beside",
                      "; ".join(f"delta_KT(N/2) {c['CV2']['width_half']:.4f}, delta_KT(N) {c['CV2']['width_full']:.4f}, inside "
                                f"{c['CV2']['E0_in_half']}/{c['CV2']['E0_in_full']} (Weinstein r_H {c['CV2']['rH_half']:.4f}/"
                                f"{c['CV2']['rH_full']:.4f})" for c in cs.values()),
                      f"<= {w}; inside", all(c["CV2"]["ok"] for c in cs.values()))
            else:
                R.add(f"CV2 {tag}: Weinstein r_H <= {w} at N/2 and N and E0 in [E_R - r_H, E_R] on B_all (all seeds; H2)",
                      "; ".join(f"r_H(N/2) {c['CV2']['width_half']:.4f}, r_H(N) {c['CV2']['width_full']:.4f}, inside "
                                f"{c['CV2']['E0_in_half']}/{c['CV2']['E0_in_full']}, gap {c['CV2']['gap_half']}/{c['CV2']['gap_full']}"
                                for c in cs.values()),
                      f"<= {w}; inside", all(c["CV2"]["ok"] for c in cs.values()))
            R.add(f"CV3 {sec} {fk}: equal shots per circuit, E_R(B^(4)) - E_R(B^(5)) <= E_tol on B_all (all seeds; k = 5 coarse "
                  f"circuit of every reference; a FAIL is an owner item, not a STOP)",
                  "; ".join(f"dE_k {c['dE_k4_k5']:.2e} ({c['ratio']:.2f} E_tol)" for c in c3.values())
                  + "; at 2 N_c (information) " + "; ".join(f"{v['dE_k4_k5']:.2e}" for v in cv3x2.values() if v),
                  "<= E_tol", all(c["ok"] for c in c3.values()))
            R.add(f"CV4 {tag}: E_R(B_all) < random 2.5th percentile (size |B_all|) at every point; margin at N >= E_tol; "
                  f"W > random 97.5th",
                  "; ".join(f"{c['CV4']['n_below']}/{c['CV4']['n_points']} below, margin {c['CV4']['margin_at_N']:.3e} "
                            f"({c['CV4']['margin_over_E_tol']:.1f} E_tol), W {c['CV4']['W_at_N']:.5f} vs {c['CV4']['W_rand_p97_5']:.5f}"
                            for c in cs.values()),
                  "all below; >= E_tol; >", all(c["CV4"]["ok"] for c in cs.values()))
            R.add(f"CV5 {tag}: W(B_all(N)) >= {W_TARGET} (all seeds)",
                  "; ".join(f"{c['CV5']['W_at_N']:.5f} (B_sig {c['CV5']['W_sig_at_N']:.5f})" for c in cs.values()),
                  f">= {W_TARGET}", all(c["CV5"]["ok"] for c in cs.values()))
            # ---- the plan used
            base = {c: int(v) for c, v in sd["plan_1x"].items()}
            cost_b = Q.cost_of_plan(base, mans, hqc_by_id)
            row = {"base_shots_by_circuit": base, "base_shots_total": int(sum(base.values())),
                   "base_hqc": cost_b["hqc_total"], "base_jobs": cost_b["jobs"],
                   "resized_by": s_fin, "plan_source": fr["plan_source"]}
            if s_fin not in (1, None):
                fin = {c: int(v) for c, v in sd["resize"][str(s_fin)]["shots_by_circuit"].items()}
                cost_f = Q.cost_of_plan(fin, mans, hqc_by_id)
                row.update({"final_shots_by_circuit": fin, "final_shots_total": int(sum(fin.values())),
                            "final_hqc": cost_f["hqc_total"], "final_jobs": cost_f["jobs"],
                            "final_usd_ESTIMATE": cost_f["hqc_total"] * usd,
                            "final_machine_hours_mid_ESTIMATE": sum(fin.values()) * shot_s / 3600.0,
                            "capped_circuits_information": sorted({c for v in sd["resize"][str(s_fin)]["seeds"].values()
                                                                   for c in v["capped_circuits"]})})
            else:
                row.update({"final_shots_by_circuit": base, "final_shots_total": int(sum(base.values())),
                            "final_hqc": cost_b["hqc_total"], "final_jobs": cost_b["jobs"]})
            row["base_usd_ESTIMATE"] = cost_b["hqc_total"] * usd
            row["base_machine_hours_mid_ESTIMATE"] = sum(base.values()) * shot_s / 3600.0
            row["delta_hqc"] = row["final_hqc"] - row["base_hqc"]
            plan_out.setdefault(fk, {})[sec] = row
            crit_rows.setdefault(fk, {})[sec] = cs
    complete = all(ftag(f) in frags for f in fs)
    campaign = {fk: {"base_hqc": sum(r["base_hqc"] for r in d.values()),
                     "final_hqc": sum(r["final_hqc"] for r in d.values()),
                     "resized_by": {sec: r["resized_by"] for sec, r in d.items()}} for fk, d in plan_out.items()}
    data = {"prompt": PROMPT, "basis": "B_all | refs", "owner_decision": "data/owner_decision_20261005_partB.md (2a)",
        "owner_confirmation_kt": OWNER_KT, "what_pass_means": (
        "the signed D3'-R plan (at the final resizing s per sector), emulated with the S1 proxy at clean fraction 0.7 f, "
        "converges on B_all | refs (manual Step 5.1, prompts/31 ruling 1): the last doubling of shots moves E_R by less "
        "than the energy error H1's recall target tolerates, the certificate meets H1 at B=0 (Kato-Temple with the exact "
        "E1, width <= 0.1) and H2 at B=1 (Weinstein r_H <= 0.15) at N/2 and at N and brackets E0, the equal-shots k = 4 -> 5 "
        "step moves E_R by less than E_tol, the basis beats random bases of its size by >= E_tol, and it carries >= 0.99 "
        "of the ground-state weight -- in all three seeds, both sectors, f = 0.05 / 0.10 / 0.15.  It is an emulation of "
        "the plan, not a device statement"),
        "constants": {"seeds": list(SEEDS), "f_grid": list(F_GRID), "phi": list(PHI), "phi_resize": list(PHI_RESIZE),
                      "sample_mult": SAMPLE_MULT, "p_ro": P_RO, "margin": MARGIN, "width": WIDTH, "cv2_type": CV2_TYPE,
                      "W_target": W_TARGET, "k_next": K_NEXT,
                      "random_percentiles": [RAND_LO, RAND_HI], "tol_monotone": TOL_MONO, "tol_variational": TOL_VAR,
                      "tol_E0_references": TOL_E0_REF, "tol_table3": TOL_T3, "tol_oracle": TOL_ORACLE,
                      "oracle_eps": list(ORACLE_EPS), "oracle_blas_threads": ORACLE_BLAS_THREADS,
                      "random_seeds": "23..222 (gate_H0_2x2.RANDOM_SEEDS)", "sig_p": 1.35e-3},
        "E_tol": E_tol, "sectors": infos, "plan": plan_out, "campaign_hqc": campaign, "criteria_by_seed": crit_rows,
        "oracle_width": owt, "oracle_width_reproduction": orep,
        "curves": {fk: {sec: {seed: rs["curves"] for seed, rs in fr["sectors"][sec]["seeds"].items()}
                        for sec in fr["sectors"]} for fk, fr in frags.items()},
        "cv0_by_seed": {fk: {sec: {seed: rs["cv0"] for seed, rs in fr["sectors"][sec]["seeds"].items()}
                             for sec in fr["sectors"]} for fk, fr in frags.items()},
        "resize": {fk: {sec: fr["sectors"][sec]["resize"] for sec in fr["sectors"]} for fk, fr in frags.items()},
        "resize_summary": resize_summary, "cv3_at_2Nc_information": cv3_2x,
        "stop": {"fired": bool(stops), "conditions": stops, "cv3_owner_items": cv3_fail,
                 "rule": ("prompts/31 fix (g): STOP (planner returns) only on a CV0 failure or if re-sizing to s = 8 still "
                          "fails; a CV3 (k = 4 -> 5) failure is an owner item (prompts/30 section 11.2), not a STOP")},
        "sampling": {fk: {sec: {seed: rs["sampling"] for seed, rs in fr["sectors"][sec]["seeds"].items()}
                          for sec in fr["sectors"]} for fk, fr in frags.items()},
        "fragments": {fk: {"runtime_s": fr["runtime_s"], "plan_source": fr["plan_source"],
                           "random_baseline_sizes_evaluated": fr.get("random_baseline_sizes_evaluated"),
                           "k5_ids": {sec: fr["sectors"][sec].get("k5_ids") for sec in fr["sectors"]}}
                      for fk, fr in frags.items()},
        "completed": complete,
        "notes": {
            "three_seeds": ("three seeds cannot establish the 95 % probability of the D3'-R rule; the conservative reading "
                            "(every one of the three seeds must pass) is used"),
            "basis": ("prompts/31 ruling 1: at 2x3 (N a / dim < 1 at the plan) the certificates and CV1-CV5 are evaluated "
                      "on B_all | refs, the manual's support (Step 5.1); the certificates are rigorous for any B.  The P9 "
                      "basis B_sig is kept in every point as information (its random baselines under 'random_sig'); its "
                      "uses are the 2x2 saturation regime and the M1 training labels.  'expected_garbage_born' = dim (1 - "
                      "exp(-mu_s)) and 'false_positives' (states of weight < 1e-8) are reported at every point; the P1 "
                      "ranked-by-count curve with the P9 cut marked is under 'ranked_by_count' at phi = 1"),
            "cv2_reading": ("prompts/31 ruling 2 (owner confirmation " + OWNER_KT + "): B=0 is read on the Kato-Temple "
                            "interval with beta = the exact E1 of the model (rigorous whenever E_R < E1, manual 5.3); "
                            "B=1 on Weinstein (cluster splitting 0.024 makes Kato-Temple wide).  Both intervals are "
                            "recorded at every point; the oracle-width table shows that the Weinstein width <= 0.1 at "
                            "B=0 needs W >= 0.9999, unreachable at this family and budget"),
            "cv3_definition": ("prompts/31 ruling 3: convergence in k is the next step, k = 4 -> 5, at equal shots per "
                               "circuit N_c (the plan's sector total over the circuits, rounded up to 100); the k = 5 coarse "
                               "circuit of every reference is sampled on the same per-seed generator stream after the "
                               "k <= 4 equal-shots circuits (the replay of that stream reproduces the cache, CV0).  "
                               "The 2 N_c step is information"),
            "width_no_plateau": ("no plateau constant is imposed on the certificate width: it must meet the H1/H2 target "
                                 "at N/2 and N; shrinking further with shots is not a requirement of H1/H2"),
            "B_sig_nesting": ("the prefixes nest B_all and the counts exactly; B_sig is NOT nested by construction, because "
                              "its threshold mu_s = N a / dim rises with N; the B_sig non-nested steps are information"),
            "gap_B1": ("at B=1 gap_assumption_holds is expected false (near-degenerate cluster, splitting 0.024, manual 1.5); "
                       "the rigorous statement is 'some eigenvalue in [E_R - r_H, E_R + r_H]' (manual 5.3)"),
            "random_baseline_solver": ("random baselines: lowest eigenpair of the sparse projected block by Lanczos "
                                       "(scipy eigsh, tol 1e-12), agreeing with the dense eigh to ~3e-14; device bases: "
                                       "skqd.skqd.ritz"),
            "cv4_points": ("CV4 is evaluated at every shots-curve point phi = 1/16..1 and every equal-shots k = 1..4, plus "
                           "the N/2 and N points of a re-sized plan, against 200 random bases of size |B_all|"),
            "oracle_blas": ("the oracle-width rows at eps <= 3e-4 cut through groups of 2-4 states of equal weight (round-"
                            "off ties); which members are kept depends on the BLAS thread count of the reference eigh.  "
                            "The table is computed with the reference eigenvector under the prototype's order (12 threads) "
                            "and every row carries its tie envelope ('tie_envelope_information'); S99 / S999 rows do not "
                            "straddle a tie"),
            "resize_floor": ("re-sized floor circuits get ceil100(267 s) shots; at s = 8 that is 2,200 > the 8 x 267 = 2,136 "
                             "sampled, so those circuits are evaluated at 2,136 (fewer shots: conservative) and listed; "
                             "non-floor circuits get ceil(s N)")}}
    R.data = data
    R.runtime_s = sum(fr["runtime_s"] for fr in frags.values()) + time.time() - t0
    if not complete:
        R.add("completeness: one fragment per f", f"present {sorted(frags)}", "all of " + str([ftag(f) for f in fs]), False)
    path = R.save()
    write_report(f"{gate}.md", report_2x3(R, data))
    print(f"{gate}: {'PASS' if R.passed else 'FAIL'} -> {rel(path)}")
    for c in R.criteria:
        print(f"  [{'PASS' if c.passed else 'FAIL'}] {c.name}: {c.value}")
    print("stop:", data["stop"])
    return 0 if R.passed else 1


def fmt(x, nd=4):
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    x = float(x)
    return f"{x:.{nd}g}" if (abs(x) >= 1e-3 or x == 0) else f"{x:.3e}"


def oracle_reading(OW):
    """Computed reading of the oracle table: the largest eps whose support meets each sector's width target, on the
    Weinstein width and on Kato-Temple (exact E1)."""
    out = []
    for sec, t in OW.items():
        w = WIDTH[sec]
        wein = [e for e, r in t["rows"].items() if r["rH"] <= w]
        kt = [e for e, r in t["rows"].items() if r["kt_width_exact_E1"] is not None and r["kt_width_exact_E1"] <= w]
        def first(lst):
            return lst[0] if lst else None
        e1, e2 = first(wein), first(kt)
        r1 = t["rows"][e1] if e1 else None
        out.append(f"{sec} (target {w}): Weinstein r_H <= {w} first at eps = {e1}"
                   + (f" (|B| = {r1['size']}, 1 - W = {fmt(r1['one_minus_W'])}, hardest state min max p = "
                      f"{fmt(r1['min_pmax'])}, k = 4-scaled shots {fmt(r1['N_k4scaled_shots_at_y0574'])})" if r1 else "")
                   + f"; Kato-Temple (exact E1) <= {w} first at eps = {e2}"
                   + (f" (|B| = {t['rows'][e2]['size']})" if e2 else ""))
    return ("Reading (computed from the table, eps grid in decreasing order): " + "; ".join(out) + ".  At B=0 the H1 "
            "width is the Kato-Temple one (prompts/31 ruling 2); at B=1 H2 is Weinstein.")


def oracle_table_md(OW):
    rows = []
    for sec, t in OW.items():
        for eps, r in t["rows"].items():
            tie = r["tie_envelope_information"]
            rows.append([sec, eps, r["size"], fmt(r["ER_minus_E0"]), fmt(r["rH"]), fmt(r["rH_estimate_E0_minus_Hnn"]),
                         fmt(r["one_minus_W"]), fmt(r["kt_width_exact_E1"]), fmt(r["min_pmax"]),
                         ("inf" if r["N_k4scaled_shots_at_y0574"] == float("inf") else fmt(r["N_k4scaled_shots_at_y0574"])),
                         (f"{tie['n_choices']} choices, r_H {fmt(tie['rH_range'][0])}..{fmt(tie['rH_range'][1])}"
                          if tie["straddles"] else "no")])
    return md_table(["sector", "eps", "|S_eps u R|", "E_R - E0", "r_H (Weinstein width)",
                     "estimate sqrt(sum (E0 - H_nn)^2 |Omega_n|^2)", "1 - W", "delta_KT (exact E1)",
                     "min_s max_c p_c(s)", "k = 4-scaled shots lambda*/(y min max p)", "tie at the boundary"], rows)


def report_2x3(R, D):
    L = [f"# Gate {R.gate} — {R.title}", "",
         f"Status: **{'PASS' if R.passed else 'FAIL'}** ({sum(1 for c in R.criteria if c.passed)} of {len(R.criteria)} "
         f"criteria hold).  Generated by `scripts/gate_CV.py --assemble` from `validation/{R.gate}.json`; no number is typed "
         f"by hand.  Prompt: {D['prompt']}.  Basis of every criterion: **{D['basis']}** (prompts/31 ruling 1).  The B=0 "
         f"certificate is read on Kato-Temple with the exact E1 (owner confirmation `{D['owner_confirmation_kt']}`).  "
         f"{env_block()}", "",
         f"What PASS means: {D['what_pass_means']}.", "",
         f"STOP fired: **{D['stop']['fired']}**" + (f" ({'; '.join(D['stop']['conditions'])})" if D["stop"]["fired"] else "")
         + f".  Rule: {D['stop']['rule']}.  CV3 owner items: {', '.join(D['stop']['cv3_owner_items']) or 'none'}.", "",
         "## Criteria", "", R.criteria_table(), "",
         "## The plan and the re-sizing (prompts/31 ruling 4; the cost returns to the owner)", "",
         md_table(["f", "sector", "D3'-R shots", "D3'-R HQC", "resized_by s", "final shots", "final HQC", "HQC added",
                   "final USD (ESTIMATE)", "plan source"],
                  [[fk, sec, fmt(r["base_shots_total"]), fmt(r["base_hqc"]), r["resized_by"], fmt(r["final_shots_total"]),
                    fmt(r["final_hqc"]), fmt(r["delta_hqc"]), fmt(r.get("final_usd_ESTIMATE", r["base_usd_ESTIMATE"])),
                    r["plan_source"]]
                   for fk, d in D["plan"].items() for sec, r in d.items()]), "",
         md_table(["f", "campaign HQC at D3'-R (both sectors)", "campaign HQC at the final plan", "resized_by"],
                  [[fk, fmt(v["base_hqc"]), fmt(v["final_hqc"]), ", ".join(f"{s} x{x}" for s, x in v["resized_by"].items())]
                   for fk, v in D["campaign_hqc"].items()]), "",
         "## CV2 per seed: both certified intervals (B=0 criterion Kato-Temple, B=1 criterion Weinstein)", "",
         md_table(["f", "sector", "seed", "criterion", "width(N/2)", "width(N)", "Weinstein r_H(N/2)", "Weinstein r_H(N)",
                   "delta_KT(N/2)", "delta_KT(N)", "E0 inside (N/2 / N)", "pass"],
                  [[fk, sec, seed, c["CV2"]["type"], fmt(c["CV2"]["width_half"]), fmt(c["CV2"]["width_full"]),
                    fmt(c["CV2"]["rH_half"]), fmt(c["CV2"]["rH_full"]), fmt(c["CV2"]["kt_width_half"]),
                    fmt(c["CV2"]["kt_width_full"]), f"{c['CV2']['E0_in_half']} / {c['CV2']['E0_in_full']}", c["CV2"]["ok"]]
                   for fk, d in D["criteria_by_seed"].items() for sec, bys in d.items() for seed, c in bys.items()]), "",
         "## CV3: the k = 4 -> 5 step at equal shots per circuit (N_c; 2 N_c information)", "",
         md_table(["f", "sector", "seed", "E_R(B^(4)) - E_R(B^(5)) at N_c", "/ E_tol", "|B^(4)| -> |B^(5)|",
                   "at 2 N_c", "/ E_tol (2 N_c)", "pass"],
                  [[fk, sec, seed, fmt(c["CV3"]["dE_k4_k5"]), fmt(c["CV3"]["ratio"]),
                    f"{c['CV3']['size_k4']} -> {c['CV3']['size_k5']}",
                    fmt(D["cv3_at_2Nc_information"][fk][sec][seed]["dE_k4_k5"]),
                    fmt(D["cv3_at_2Nc_information"][fk][sec][seed]["ratio"]), c["CV3"]["ok"]]
                   for fk, d in D["criteria_by_seed"].items() for sec, bys in d.items() for seed, c in bys.items()]), "",
         "## The H1-derived energy tolerance E_tol (prompts/30 2.7)", "",
         md_table(["sector", "E_tol", "states (top 80 % of S999 by weight)", "E_R", "E_tol at recall 0.9 (information)",
                   "Table 3 oracle |B|=40 / 80 reproduction (abs diff)"],
                  [[sec, fmt(D["E_tol"][sec]["value"]), D["E_tol"][sec]["n_top"], fmt(D["E_tol"][sec]["E_R"], 8),
                    fmt(D["E_tol"][sec]["recall_0.9_information"]),
                    " / ".join(fmt(r["abs_diff"]) for r in D["sectors"][sec]["table3_oracle"].values())]
                   for sec in D["E_tol"]]), "",
         "## Oracle-width table (prompts/31 D1; reproduces `" + D["oracle_width_reproduction"].get("prototype", "") + "`)", "",
         f"Reproduction: {D['oracle_width_reproduction'].get('fields_compared')} fields, max scaled difference "
         f"{fmt(D['oracle_width_reproduction'].get('max_scaled_diff'))} (tolerance {fmt(TOL_ORACLE)}).  "
         + oracle_reading(D["oracle_width"]), "",
         oracle_table_md(D["oracle_width"]), ""]
    for sec, inf in D["sectors"].items():
        for n, t in inf.get("table3_oracle_tie_information", {}).items():
            L.append(f"{sec}, |B| = {n} (Table 3): the boundary of the oracle sits on {len(t['tied_states'])} states of equal "
                     f"weight ({fmt(t['weight'])} to round-off); the {t['n_choices']} equally valid choices give E_R - E0 in "
                     f"[{fmt(t['E_err_min'])}, {fmt(t['E_err_max'])}].  The reproduction above is the single-thread BLAS "
                     f"order (the gate pins BLAS to one thread).")
    L += ["", "## Re-sizing ladder (prefixes of the same 8 N samples, B_all; B_sig beside)", "",
          md_table(["f", "sector", "s", "shots", "all seeds pass", "CV1 / CV2 / CV4 / CV5", "max width(sN/2)",
                    "max width(sN)", "max r_H(sN/2) B_all", "max r_H(sN/2) B_sig", "size B_sig at sN", "size B_all at sN",
                    "mu_s at sN"],
                   [[fk, sec, s_, fmt(v["shots_total"]), v["ok_all_seeds"],
                     " / ".join(str(v["criteria_ok"][k]) for k in ("CV1", "CV2", "CV4", "CV5")),
                     fmt(v["width_half_max"]), fmt(v["width_full_max"]), fmt(v["rH_half_B_all_max"]),
                     fmt(v["rH_half_B_sig_max"]),
                     ", ".join(str(x) for x in v["size_B_sig_full"]), ", ".join(str(x) for x in v["size_B_all_full"]),
                     ", ".join(fmt(x) for x in v["mu_s_full"])]
                    for fk, d in D["resize_summary"].items() for sec, ld in d.items() for s_, v in ld.items()]) or "(no re-sizing needed)", ""]
    L += ["## P1 ranked-by-count curve at the 1x plan (phi = 1; information, prompts/31 ruling 1)", ""]
    rows = []
    for fk, d in D["curves"].items():
        for sec, bys in d.items():
            for seed, cv in bys.items():
                p = cv["shots"][-1]
                for q in p.get("ranked_by_count", []):
                    rows.append([fk, sec, seed, q["size"], fmt(q["E_R_minus_E0"]), fmt(q["rH"]), fmt(q["W"], 6),
                                 ("P9 cut" if q["is_P9_cut"] else "") + (" B_all" if q["is_B_all"] else ""),
                                 fmt(p["expected_garbage_born"]), p["all"]["false_positives"]])
    L += [md_table(["f", "sector", "seed", "top-|B| by count", "E_R - E0", "r_H", "W", "mark",
                    "expected garbage-born states dim(1 - e^-mu_s)", "false positives in B_all (weight < 1e-8)"], rows), "",
          "## Curves (B_all criterion basis, B_sig information; every seed must pass)", ""]
    for fk, d in D["curves"].items():
        for sec, bys in d.items():
            rows = []
            for seed, cv in bys.items():
                for p in cv["shots"]:
                    rows.append([seed, f"phi {fmt(p['phi'])}", fmt(p["shots"]), p["B_all_size"], p["sig"]["size"],
                                 fmt(p["all"]["err"]), fmt(p["all"]["rH"]), fmt(p["all"]["kt_width"]), fmt(p["all"]["W"], 6),
                                 fmt(p["sig"]["err"]), fmt(p["all"]["recall_S999"]), fmt(p["sig"]["recall_S999"]),
                                 fmt(p["random"]["E_R"]["p2_5"] - p["all"]["E_R"] if p.get("random") else None),
                                 fmt(p["all"]["eq6_bound"])])
                for name in ("krylov_equal", "krylov_allocation", "krylov_equal_2x"):
                    for p in cv[name]:
                        rows.append([seed, f"{name} k={p['k']}", fmt(p["shots"]), p["B_all_size"], p["sig"]["size"],
                                     fmt(p["all"]["err"]), fmt(p["all"]["rH"]), fmt(p["all"]["kt_width"]),
                                     fmt(p["all"]["W"], 6), fmt(p["sig"]["err"]), fmt(p["all"]["recall_S999"]),
                                     fmt(p["sig"]["recall_S999"]),
                                     fmt(p["random"]["E_R"]["p2_5"] - p["all"]["E_R"] if p.get("random") else None),
                                     fmt(p["all"]["eq6_bound"])])
            L += [f"### {sec}, {fk}", "",
                  md_table(["seed", "point", "shots", "size B_all", "size B_sig", "E_R - E0 (B_all)", "r_H (B_all)",
                            "delta_KT (B_all)", "W (B_all)", "E_R - E0 (B_sig)", "recall S999 (all)", "recall S999 (sig)",
                            "random 2.5 % - E_R (B_all size)", "eq. (6) bound"], rows), ""]
    L += ["## Notes", ""] + [f"- **{k}**: {v}" for k, v in D["notes"].items()] + [""]
    return "\n".join(L)


# =========================================================================== 2x2 information block
def run_2x2(counts_dir):
    from skqd.codec import Codec
    from skqd.exact import Model
    from skqd.reference_sim import qiskit_key_to_bits

    import gate_H0_2x2 as G

    t0 = time.time()
    M = Model(2)
    codec = Codec(M.basis)
    rec = load_json(os.path.join(ROOT, "validation", "H0_2x2.json"))
    rd = rec["data"]
    sectors = {sec: Sector(M, "2x2", sec, tb, G.E2_ACCEPTANCE[tb]) for sec, tb in SECTORS}
    files = sorted(glob.glob(os.path.join(ROOT, counts_dir, "*.json")))
    circ = {}
    for fpath in files:
        r = load_json(fpath)
        if r.get("kind") != "coarse_step":
            continue
        circ[r["id"]] = r
    gate = "CV_2x2_info"
    R = GateResult(gate, "the CV curves on the recorded H0_2x2 ibm_kingston counts (information; " + LABEL_2X2 + ")")
    info, curves, cv0_rows = {}, {}, {}
    for sec, S in sectors.items():
        ids = sorted(c for c, r in circ.items() if int(r["twoB"]) == S.twoB)
        kof = {c: int(circ[c]["k"]) for c in ids}
        # decode every circuit's histogram into a shot array (outcome = basis index or -1)
        shots_arr, n_full_rec = {}, np.zeros(M.basis.dim, dtype=np.int64)
        for c in ids:
            cnt = circ[c]["counts"]
            outs = []
            for k, v in sorted(cnt.items()):
                acc, _rej = codec.decode_counts({qiskit_key_to_bits(k): int(v)}, S.twoB)
                o = int(next(iter(acc))) if acc else -1
                outs.append(np.full(int(v), o, dtype=np.int64))
            arr = np.concatenate(outs) if outs else np.zeros(0, dtype=np.int64)
            shots_arr[c] = arr
            x = arr[arr >= 0]
            if x.size:
                n_full_rec += np.bincount(x, minlength=M.basis.dim)
        N_c = {c: int(len(shots_arr[c])) for c in ids}
        inf = sector_info(S, False)
        E_tol = inf["E_tol"]["E_tol"]
        # recorded cross-checks
        sup = rd["support"][sec]
        full_pt = S.point(n_full_rec, sum(N_c.values()))
        rec_sig_same = sorted(set(int(x) for x in sup["B_sig"]) | set(S.refs)) == sorted(full_pt["B_sig_list"])
        rec_ok = bool(sorted(int(x) for x in sup["B_all"]) == sorted(full_pt["_B_all"]) and rec_sig_same)
        per_state_ok = all(int(n_full_rec[int(ps["basis_index"])]) == int(ps["n_s"]) for ps in sup["per_state"])
        # Krylov at the allocation (recorded k_growth structure)
        kpts = []
        for k in (1, 2, 3, 4):
            L = [c for c in ids if kof[c] <= k]
            n = np.zeros(M.basis.dim, dtype=np.int64)
            for c in L:
                x = shots_arr[c][shots_arr[c] >= 0]
                if x.size:
                    n += np.bincount(x, minlength=M.basis.dim)
            p = S.point(n, sum(N_c[c] for c in L))
            p["k"] = k
            kpts.append(p)
        kg = sup["k_growth"]
        kg_ok = all(int(g["shots"]) == kpts[i]["shots"] and int(g["B_all"]) == kpts[i]["B_all_size"]
                    for i, g in enumerate(kg))
        kg_sig_info = [{"k": i + 1, "recorded_B_sig": int(g["B_sig"]), "recomputed_B_sig_incl_refs": kpts[i]["sig"]["size"],
                        "recomputed_sig_states_excl_refs": len(set(kpts[i]["B_sig_list"]) - set(S.refs))}
                       for i, g in enumerate(kg)]
        # hypergeometric nested sub-samples: one permutation per circuit per draw seed
        draws, nest_ok, var_ok, randR = [], True, True, True
        for ds in DRAW_SEEDS_2X2:
            rng = np.random.default_rng(int(ds))
            perm = {c: rng.permutation(shots_arr[c]) for c in ids}
            pts, prevB, prevn = [], None, None
            for phi in PHI:
                L = {c: rnd(phi * N_c[c]) for c in ids}
                n = np.zeros(M.basis.dim, dtype=np.int64)
                for c, l in L.items():
                    x = perm[c][:l]
                    x = x[x >= 0]
                    if x.size:
                        n += np.bincount(x, minlength=M.basis.dim)
                p = S.point(n, sum(L.values()))
                p["phi"] = phi
                if prevB is not None:
                    nest_ok &= set(prevB).issubset(set(p["_B_all"])) and bool(np.all(n >= prevn))
                    nest_ok &= bool(p["all"]["E_R"] <= pts[-1]["all"]["E_R"] + TOL_MONO)
                prevB, prevn = p["_B_all"], n
                var_ok &= p["sig"]["E_R"] >= S.E0 - TOL_VAR and p["all"]["E_R"] >= S.E0 - TOL_VAR
                var_ok &= p["random"]["min_E_R"] >= S.E0 - TOL_VAR
                randR &= p["random"]["contains_R"] and p["random"]["sizes_ok"]
                pts.append(p)
            crit = evaluate(S, pts[3], pts[4], pts, kpts, E_tol, BASIS_2X2)   # no CV3: no equal-shots curve on hardware
            draws.append({"seed": ds, "points": [strip(q) for q in pts], "criteria_information": crit})
        for d in draws:
            for q in d["points"]:
                q.pop("B_sig_list", None)
        kalloc = {"dE_k3_k4": kpts[2]["sig"]["E_R"] - kpts[3]["sig"]["E_R"], "rH_k4": kpts[3]["sig"]["rH"],
                  "note": "allocation curve (recorded k_growth); CV3's equal-shots version does not exist on hardware"}
        e0_ok = inf["E0_abs_diff_references_json"] <= TOL_E0_REF
        cv0 = nest_ok and var_ok and randR and e0_ok and rec_ok and per_state_ok and kg_ok
        R.add(f"CV0 {sec}: nested hypergeometric prefixes (B_all, counts, E_R(B_all)), E_R >= E0 - 1e-9, E0 = references.json, "
              f"random bases contain R, recorded per-state counts / B_all / B_sig / k_growth reproduced",
              f"nested {nest_ok}; variational {var_ok}; random R {randR}; E0 diff {inf['E0_abs_diff_references_json']:.1e}; "
              f"per-state counts {per_state_ok}; B_all/B_sig {rec_ok}/{rec_sig_same}; k_growth {kg_ok}",
              "structural", cv0)

        def summ(key):
            v = [key(d) for d in draws]
            return {"mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}
        inf_cv = {
            "CV1_dE": summ(lambda d: d["criteria_information"]["CV1"]["dE"]),
            "CV1_ratio": summ(lambda d: d["criteria_information"]["CV1"]["ratio"]),
            "CV2_rH_half": summ(lambda d: d["criteria_information"]["CV2"]["rH_half"]),
            "CV2_rH_full": summ(lambda d: d["criteria_information"]["CV2"]["rH_full"]),
            "CV2_type": CV2_TYPE[sec],
            "CV2_kt_width_half": summ(lambda d: d["criteria_information"]["CV2"]["kt_width_half"] if
                                      d["criteria_information"]["CV2"]["kt_width_half"] is not None else float("nan")),
            "CV2_kt_width_full": summ(lambda d: d["criteria_information"]["CV2"]["kt_width_full"] if
                                      d["criteria_information"]["CV2"]["kt_width_full"] is not None else float("nan")),
            "CV2_E0_in_weinstein_all_draws": all(d["criteria_information"]["CV2"]["E0_in_weinstein_half"] and
                                                 d["criteria_information"]["CV2"]["E0_in_weinstein_full"] for d in draws),
            "CV2_E0_in_kt_all_draws": all(bool(d["criteria_information"]["CV2"]["E0_in_kt_half"]) and
                                          bool(d["criteria_information"]["CV2"]["E0_in_kt_full"]) for d in draws),
            "CV2_E0_inside_all_draws": all(d["criteria_information"]["CV2"]["E0_in_half"] and
                                           d["criteria_information"]["CV2"]["E0_in_full"] for d in draws),
            "CV3_allocation": kalloc,
            "CV4_margin_at_N": summ(lambda d: d["criteria_information"]["CV4"]["margin_at_N"]),
            "CV4_margin_over_E_tol": summ(lambda d: d["criteria_information"]["CV4"]["margin_over_E_tol"]),
            "CV4_points_below": summ(lambda d: d["criteria_information"]["CV4"]["n_below"]),
            "CV4_n_points": draws[0]["criteria_information"]["CV4"]["n_points"],
            "CV5_W_at_N": summ(lambda d: d["criteria_information"]["CV5"]["W_at_N"]),
            "would_pass": {k: int(sum(d["criteria_information"][k]["ok"] for d in draws)) for k in ("CV1", "CV2", "CV4", "CV5")},
            "n_draws": len(draws)}
        info[sec] = {"sector": {k: v for k, v in inf.items() if not k.startswith("_")}, "E_tol": E_tol,
                     "N_by_circuit": N_c, "N_sector": int(sum(N_c.values())),
                     "Na_over_dim_recomputed": sum(N_c.values()) * S.a / S.dim,
                     "Na_over_dim_record": sup["Na_over_dim"], "saturates_from_noise": bool(sup["Na_over_dim"] >= 5),
                     "B_all_equals_dim": bool(full_pt["B_all_size"] == S.dim),
                     "garbage_only_E_R_mean_record": rd["baselines"][sec]["garbage_only"]["E_R"]["mean"],
                     "garbage_only_minus_E0": rd["baselines"][sec]["garbage_only"]["E_R"]["mean"] - S.E0,
                     "full_point": strip({k: v for k, v in full_pt.items() if k != "B_sig_list"}),
                     "k_growth_sig_information": kg_sig_info,
                     "information": inf_cv}
        curves[sec] = {"draws": draws, "krylov_allocation": [strip({k: v for k, v in p.items() if k != "B_sig_list"})
                                                             for p in kpts]}
        cv0_rows[sec] = {"nested": nest_ok, "variational": var_ok, "random_R": randR, "E0_ok": e0_ok,
                         "recorded_B_all_B_sig": rec_ok, "recorded_B_sig_incl_refs_equal": rec_sig_same,
                         "per_state_counts": per_state_ok, "k_growth": kg_ok}
    owt2 = {sec: oracle_width(M, tb) for sec, tb in SECTORS}
    R.data = {"prompt": PROMPT, "label": LABEL_2X2, "counts_dir": counts_dir, "record": "validation/H0_2x2.json (never edited)",
              "basis": "B_sig (P9; the 2x2 saturation regime keeps it, prompts/31 ruling 1)",
              "cv2_reading": ("the same pair as CV_2x3_plan (prompts/31 ruling 2): B=0 Kato-Temple with the exact E1, B=1 "
                              "Weinstein; both intervals recorded (" + OWNER_KT + ")"),
              "oracle_width": owt2,
              "oracle_width_note": "the prompts/31 D1 oracle-width table at 2x2, for completeness (no reproduction target)",
              "draw_seeds": list(DRAW_SEEDS_2X2), "random_seeds": "23..222 (gate_H0_2x2.RANDOM_SEEDS)",
              "information": info, "curves": curves, "cv0": cv0_rows,
              "reading": ("the 2x2 curves are flat because the sector saturates from garbage (N a / dim >= 5, |B_all| = dim, "
                          "the garbage-only baseline reaches E0): random bases of the B_sig size already reach E0, so CV4's "
                          "margin is below E_tol.  That is why the 2x3 criteria are needed and why CV4 exists.  CV1-CV5 "
                          "carry no verdict here; the recorded H0_2x2 verdicts are not touched"),
              "what_pass_means": "CV0 only (structural): the 2x2 block was computed correctly from the unedited record; "
                                 "no device or convergence verdict"}
    R.runtime_s = time.time() - t0
    path = R.save()
    write_report("CV_2x2_information_20261005.md", report_2x2(R, R.data))
    print(f"{gate}: {'PASS' if R.passed else 'FAIL'} -> {rel(path)}")
    for c in R.criteria:
        print(f"  [{'PASS' if c.passed else 'FAIL'}] {c.name}: {c.value}")
    return 0 if R.passed else 1


def report_2x2(R, D):
    L = [f"# Gate {R.gate} — {R.title}", "",
         f"Status: **{'PASS' if R.passed else 'FAIL'}** (CV0 only).  Label: **{D['label']}**.  Generated by "
         f"`scripts/gate_CV.py --source counts {D['counts_dir']} --model 2` from `validation/{R.gate}.json`; no number is "
         f"typed by hand.  {env_block()}", "",
         "## Criteria (structural only)", "", R.criteria_table(), "",
         "## Saturation evidence", "",
         md_table(["sector", "N a / dim (record)", "saturates from noise", "|B_all| = dim", "garbage-only E_R - E0 (record)",
                   "E_tol", "CV4 margin at N (mean / min / max over 20 draws)", "margin / E_tol (mean)"],
                  [[sec, fmt(v["Na_over_dim_record"]), v["saturates_from_noise"], v["B_all_equals_dim"],
                    fmt(v["garbage_only_minus_E0"]), fmt(v["E_tol"]),
                    " / ".join(fmt(v["information"]["CV4_margin_at_N"][k]) for k in ("mean", "min", "max")),
                    fmt(v["information"]["CV4_margin_over_E_tol"]["mean"])] for sec, v in D["information"].items()]), "",
         "## CV1-CV5 as information (no verdict)", "",
         md_table(["sector", "CV1 dE (mean)", "CV1 ratio (max)", "r_H(N/2) (mean)", "r_H(N) (mean)", "E0 inside (all draws)",
                   "allocation dE k3-k4", "W(N) (min)", "draws that would pass CV1/CV2/CV4/CV5"],
                  [[sec, fmt(v["information"]["CV1_dE"]["mean"]), fmt(v["information"]["CV1_ratio"]["max"]),
                    fmt(v["information"]["CV2_rH_half"]["mean"]), fmt(v["information"]["CV2_rH_full"]["mean"]),
                    v["information"]["CV2_E0_inside_all_draws"], fmt(v["information"]["CV3_allocation"]["dE_k3_k4"]),
                    fmt(v["information"]["CV5_W_at_N"]["min"], 6),
                    " / ".join(str(v["information"]["would_pass"][k]) for k in ("CV1", "CV2", "CV4", "CV5"))]
                   for sec, v in D["information"].items()]), "",
         "## CV2 on both certified intervals (information; B=0 criterion type Kato-Temple with the exact E1, B=1 Weinstein)", "",
         md_table(["sector", "type", "Weinstein r_H(N/2) / r_H(N) (mean)", "delta_KT(N/2) / delta_KT(N) (mean)",
                   "E0 in Weinstein (all draws)", "E0 in Kato-Temple (all draws)"],
                  [[sec, v["information"]["CV2_type"],
                    f"{fmt(v['information']['CV2_rH_half']['mean'])} / {fmt(v['information']['CV2_rH_full']['mean'])}",
                    f"{fmt(v['information']['CV2_kt_width_half']['mean'])} / {fmt(v['information']['CV2_kt_width_full']['mean'])}",
                    v["information"]["CV2_E0_in_weinstein_all_draws"], v["information"]["CV2_E0_in_kt_all_draws"]]
                   for sec, v in D["information"].items()]), "",
         "## Oracle-width table at 2x2 (prompts/31 D1, for completeness)", "", oracle_table_md(D["oracle_width"]), "",
         oracle_reading(D["oracle_width"]), "",
         "## Shots curve (mean over the 20 hypergeometric draws, B_sig)", ""]
    for sec, cv in D["curves"].items():
        rows = []
        for i, phi in enumerate(PHI):
            pts = [d["points"][i] for d in cv["draws"]]
            rows.append([fmt(phi), fmt(float(np.mean([p["shots"] for p in pts]))),
                         fmt(float(np.mean([p["sig"]["size"] for p in pts]))),
                         fmt(float(np.mean([p["B_all_size"] for p in pts]))),
                         fmt(float(np.mean([p["sig"]["err"] for p in pts]))),
                         fmt(float(np.mean([p["sig"]["rH"] for p in pts]))),
                         fmt(float(np.mean([p["sig"]["W"] for p in pts])), 6),
                         fmt(float(np.mean([p["random"]["E_R"]["p2_5"] - p["sig"]["E_R"] for p in pts])))])
        L += [f"### {sec}", "", md_table(["phi", "shots", "size B_sig", "size B_all", "E_R - E0", "r_H", "W",
                                          "random 2.5 % - E_R"], rows), "",
              md_table(["k (allocation)", "shots", "size B_sig", "size B_all", "E_R - E0", "r_H", "W"],
                       [[p["k"], fmt(p["shots"]), p["sig"]["size"], p["B_all_size"], fmt(p["sig"]["err"]),
                         fmt(p["sig"]["rH"]), fmt(p["sig"]["W"], 6)] for p in cv["krylov_allocation"]]), ""]
    L += ["## Reading", "", D["reading"] + ".", ""]
    return "\n".join(L)


# =========================================================================== 2x4 (prompts/36): the noiseless plan
PROMPT_36 = "prompts/36_2x4_full_pipeline.md"
CV4_DIR = os.path.join(CV_DIR, "2x4")
ACC_FILE = {3: os.path.join(CV_DIR, "acceptance_2x3.json"), 4: os.path.join(CV_DIR, "acceptance_2x4.json")}
MC_STRINGS_2X4, MC_SEED_2X4 = 10_000_000, 36      # prompts/36 R2 Monte-Carlo cross-check
F_INFO_2X4 = (0.10, 0.05)                         # R3 information columns (no device exists for this)
GRID_2X4 = (1,) + PHI_RESIZE                      # R3 (iii): s in {1, 1.5, 2, 3, 4, 6, 8}
GPU_MULT, GPU_MIN_SHOTS, UNIFORM_PER_SECTOR = 8, 6250, 200_000   # R5
FLOOR_2X4, ROUND_TO_2X4 = 267, 100
IR_L0_PER_STEP = 142288                           # prompts/36 A7 as written (QV_2x4_01 B0_ref102_k1 structured source)
BUNDLE_CAP_BYTES = 60_000_000                     # A7: 60 MB
SLOT_BUDGET_S = 2700.0                            # A6: 0.75 x 3600 s
INFO_LABEL = "no device exists for this"
SLOTS_2X4 = tuple(f"QV_2x4_{k:02d}" for k in range(2, 8))
ACC_REASONS = ("flag", "link", "sector", "unknown")


def acceptance_L(codec, lat):
    """The per-sector decoder acceptance of uniformly random strings: 2x3 the exhaustive file (acceptance_2x3),
    2x4 data/cv/acceptance_2x4.json (the factorised count of prompts/36 R2, --stage acceptance), 2x2 the factorised
    count in-process."""
    if lat == 3:
        return acceptance_2x3(codec)
    if lat == 4:
        if not os.path.exists(ACC_FILE[4]):
            raise SystemExit("data/cv/acceptance_2x4.json missing: run scripts/gate_CV.py --lattice 4 --stage acceptance")
        return load_json(ACC_FILE[4])
    from gate_H0P import random_acceptance_factorised
    return {sec: random_acceptance_factorised(codec, tb) for sec, tb in SECTORS}


def circuits_L(lat):
    """{base id: manifest summary} of the signed family: 2x3 the frozen manifests (circuits_2x3); 2x4 the structured
    (IR-L0) entries of data/quantinuum/circuits_2x4/index.json in index order (base_id, twoB, reference, k, dt) with
    `family_index` = the position in that order (the global circuit index of the slot seeds); 2x2 the same reader."""
    if lat == 3:
        return circuits_2x3()
    d = os.path.join(ROOT, "data", "quantinuum", f"circuits_2x{lat}")
    idx = load_json(os.path.join(d, "index.json"))
    out = {}
    for c in idx["circuits"]:
        m = load_json(os.path.join(d, c + ".manifest.json"))
        if lat == 4 and m.get("source") != "structured":
            continue
        bid = m.get("base_id") or m["id"]
        out[bid] = {"base_id": bid, "id": m["id"], "twoB": int(m["twoB"]), "reference": int(m["reference"]),
                    "k": int(m["k"]), "dt": float(m["dt"]), "sector": m["sector"], "hqc_per_shot": m.get("hqc_per_shot"),
                    "counts": m.get("counts"), "family_index": len(out)}
    return out


def k5_ids_L(sectors):
    """The k = 5 circuit ids (one per reference, B=0 refs then B=1 refs in references order) and their global circuit
    index (after the family)."""
    out = []
    for sec, tb in SECTORS:
        S = sectors[sec]
        out += [f"{sec.replace('=', '')}_ref{int(r)}_k{K_NEXT}" for r in S.refs]
    return out


def sectors_L(lat):
    from skqd.codec import Codec
    from skqd.exact import Model
    M = Model(lat)
    codec = Codec(M.basis)
    acc = acceptance_L(codec, lat)
    return M, codec, acc, {sec: Sector(M, f"2x{lat}", sec, tb, acc[sec]["fraction"]) for sec, tb in SECTORS}


def circuit_states_L(S, mans):
    """{cid: full-basis state} of the family at the manifests' dt (one dt per sector: gate_S2_2x4.dt_of at 2x4)."""
    from skqd.exact import mass_default
    from skqd.krylov import basis_vector, coarse_states, term_groups

    groups = term_groups(S.M.terms, G2, mass_default(G2))
    ids = sorted(c for c, m in mans.items() if int(m["twoB"]) == S.twoB)
    dts = sorted({float(mans[c]["dt"]) for c in ids})
    if len(dts) != 1:
        raise SystemExit(f"{S.sec}: the manifests carry {len(dts)} different dt values")
    dt = dts[0]
    out, by_ref = {}, {}
    for c in ids:
        by_ref.setdefault(int(mans[c]["reference"]), []).append(c)
    for ref, cs in by_ref.items():
        st = coarse_states(groups, basis_vector(S.M.basis.dim, ref), dt, 4)
        for c in cs:
            out[c] = st[int(mans[c]["k"])]
    return out, dt, abs(dt - S.dt)


def mc_acceptance(codec, n_strings, seed, chunk=200_000):
    """prompts/36 R2 cross-check: n uniformly random strings (numpy default_rng(seed).integers(0, 2^n), bit k = qubit k)
    through Codec.decode with each sector's target.  'flag' and 'link' are decided before the sector test, so a string
    rejected for them in the first sector is counted with the same reason in the second without a second call (the
    call would raise the same reason); every other string is decoded once per sector."""
    from skqd.codec import Reject
    rng = np.random.default_rng(int(seed))
    nq = int(codec.n_qubits)
    shifts = np.arange(nq, dtype=np.int64)
    acc = {sec: 0 for sec, _ in SECTORS}
    why = {sec: {r: 0 for r in ACC_REASONS} for sec, _ in SECTORS}
    done, t0 = 0, time.time()
    while done < n_strings:
        m = min(chunk, n_strings - done)
        x = rng.integers(0, 2 ** nq, size=m, dtype=np.int64)
        for row in ((x[:, None] >> shifts) & 1).tolist():
            b = tuple(row)
            shared = None
            for sec, tb in SECTORS:
                if shared is not None:
                    why[sec][shared] += 1
                    continue
                try:
                    codec.decode(b, tb)
                    acc[sec] += 1
                except Reject as r:
                    w = str(r)
                    why[sec][w] += 1
                    if w in ("flag", "link"):
                        shared = w
        done += m
    return {"strings": int(n_strings), "seed": int(seed), "accepted": acc, "reasons": why, "seconds": time.time() - t0,
            "rng": "numpy default_rng(seed).integers(0, 2^n_qubits, int64) in chunks of 200000; bit k = qubit k"}


def stage_acceptance_2x4(n_mc=MC_STRINGS_2X4, seed=MC_SEED_2X4):
    """prompts/36 R2 / 3.2: data/cv/acceptance_2x4.json (factorised exact count, cross-checked against the exhaustive
    loop at 2x2 and the exhaustive 2x3 file, Monte-Carlo at 2x4)."""
    from gate_H0P import random_acceptance, random_acceptance_factorised
    from skqd.codec import Codec
    from skqd.exact import Model

    t0 = time.time()
    cross = {}
    M2 = Model(2)
    c2 = Codec(M2.basis)
    M3 = Model(3)
    c3 = Codec(M3.basis)
    ex3 = load_json(ACC_FILE[3])
    for lat, codec, ref_of in ((2, c2, lambda tb: random_acceptance(c2, tb)), (3, c3, None)):
        rows = {}
        for sec, tb in SECTORS:
            fa = random_acceptance_factorised(codec, tb)
            ex = ref_of(tb) if ref_of else ex3[sec]
            same = (fa["accepted"] == int(ex["accepted"]) and fa["strings"] == int(ex["strings"])
                    and all(fa["reasons"][r] == int(ex["reasons"].get(r, 0)) for r in ACC_REASONS))
            rows[sec] = {"factorised": {k: fa[k] for k in ("accepted", "strings", "reasons")},
                         "exhaustive": {"accepted": int(ex["accepted"]), "strings": int(ex["strings"]),
                                        "reasons": {r: int(ex["reasons"].get(r, 0)) for r in ACC_REASONS}},
                         "equal": bool(same)}
        cross[f"2x{lat}"] = {"sectors": rows, "factorised_equals_exhaustive": all(v["equal"] for v in rows.values()),
                             "exhaustive_source": ("gate_H0P.random_acceptance re-run now (2^12 strings)" if lat == 2
                                                   else rel(ACC_FILE[3]))}
    M = Model(4)
    codec = Codec(M.basis)
    out = {"prompt": PROMPT_36, "lattice": "2x4", "n_qubits": int(codec.n_qubits), "cross_checks": cross}
    t1 = time.time()
    fac = {sec: random_acceptance_factorised(codec, tb) for sec, tb in SECTORS}
    t_fac = time.time() - t1
    mc = mc_acceptance(codec, n_mc, seed)
    for sec, tb in SECTORS:
        fa = fac[sec]
        dim = int(len(M.basis.sector(tb)))
        p = fa["fraction"]
        exp = n_mc * p
        sig = math.sqrt(n_mc * p * (1.0 - p))
        acc = int(mc["accepted"][sec])
        out[sec] = {"accepted": int(fa["accepted"]), "strings": int(fa["strings"]), "fraction": float(fa["fraction"]),
                    "reasons": fa["reasons"], "method": fa["method"], "dimension": dim,
                    "equals_dimension": bool(fa["accepted"] == dim),
                    "per_vertex_accepted_patterns": fa["per_vertex_accepted_patterns"],
                    "unflagged_strings": fa["unflagged_strings"], "link_consistent_strings": fa["link_consistent_strings"],
                    "monte_carlo": {"strings": int(n_mc), "accepted": acc, "expected": exp, "sigma": sig,
                                    "z": (acc - exp) / sig if sig > 0 else None, "seed": int(seed),
                                    "reasons": mc["reasons"][sec], "within_3_sigma": bool(abs(acc - exp) <= 3 * sig)}}
    out.update({"runtime_s": time.time() - t0, "factorised_runtime_s": t_fac, "monte_carlo_runtime_s": mc["seconds"],
                "monte_carlo_rng": mc["rng"],
                "function": "scripts/gate_H0P.random_acceptance_factorised (prompts/36 R2); Monte-Carlo through Codec.decode",
                "assumption_replaced": ("scripts/quantinuum_lattice_tests.Phys used a = dim / 2^n_qubits (assumed); it now "
                                        "reads this file")})
    os.makedirs(CV_DIR, exist_ok=True)
    with open(ACC_FILE[4], "w") as fh:
        json.dump(_j(out), fh, indent=1)
    print(f"wrote {rel(ACC_FILE[4])}: " + "; ".join(
        f"{sec} accepted {out[sec]['accepted']} (dim {out[sec]['dimension']}), MC z {out[sec]['monte_carlo']['z']:.2f}"
        for sec, _ in SECTORS) + f" ({out['runtime_s']:.0f} s)")
    return 0


def stage_etol_2x4():
    """E_tol per sector and the sector data (prompts/36 R4, A2) -> data/cv/2x4/etol.json."""
    t0 = time.time()
    M, codec, acc, sectors = sectors_L(4)
    out = {"prompt": PROMPT_36, "sectors": {}, "E_tol": {}}
    for sec, S in sectors.items():
        info = sector_info(S, False)
        et = info["E_tol"]
        out["sectors"][sec] = info
        out["E_tol"][sec] = {"value": et["E_tol"], "states_top": et["states_top"], "n_top": et["n_top"],
                             "references": et["references"], "E_R": et["E_R"], "E0": et["E0"],
                             "basis_size": et["basis_size"], "captured_weight": et["captured_weight"],
                             "recall_0.9_information": info["E_tol_recall_0.9_information"]["E_tol"]}
    out["runtime_s"] = time.time() - t0
    os.makedirs(CV4_DIR, exist_ok=True)
    p = os.path.join(CV4_DIR, "etol.json")
    with open(p, "w") as fh:
        json.dump(_j(out), fh, indent=1)
    print(f"wrote {rel(p)}: " + "; ".join(f"{s} E_tol {v['value']:.6g}" for s, v in out["E_tol"].items()))
    return 0


def _trim_plan(d):
    return {k: v for k, v in d.items() if k != "lambda_by_state"}


def plan_noiseless_L(M, sectors, mans, f_info=F_INFO_2X4):
    """prompts/36 R3: D3'-R at y_c = 1 (f = 1, margin 1, readout 1) per sector on the exact sector distributions of the
    family (krylov.ideal_sector_distribution at the manifests' dt), plus the information columns at y = 0.82 x 0.7 x f.
    An infeasible LP raises (a STOP, never a default)."""
    from h0_support_plan import d3r_plan
    from skqd.krylov import ideal_sector_distribution
    from skqd.skqd import READOUT_FACTOR

    out = {"noiseless": {}, "information": {ftag(f): {} for f in f_info}, "p_by_circuit": {}}
    for sec, S in sectors.items():
        ids = sorted(c for c, m in mans.items() if int(m["twoB"]) == S.twoB)
        k4 = [c for c in ids if int(mans[c]["k"]) == 4]
        P, mass, sidx = {}, {}, None
        for c in ids:
            d = ideal_sector_distribution(M, G2, S.twoB, int(mans[c]["reference"]), int(mans[c]["k"]),
                                          float(mans[c]["dt"]), 1)
            P[c], mass[c] = np.asarray(d["p"], float), float(d["sector_mass"])
            if sidx is None:
                sidx = [int(b) for b in d["sector_indices"]]
        pos = {b: i for i, b in enumerate(sidx)}
        S99 = [pos[int(s)] for s in S.S99]
        S999 = [pos[int(s)] for s in S.S999]
        nl = d3r_plan(P, {c: 1.0 for c in ids}, ids, k4, S99, S999, floor=FLOOR_2X4, round_to=ROUND_TO_2X4,
                      margin=1.0, readout_factor=1.0)
        nl = _trim_plan(nl)
        nl.update({"y_c": 1.0, "f": 1.0, "ids": ids, "sector_mass_min": min(mass.values()),
                   "S99_size": len(S99), "S999_size": len(S999)})
        out["noiseless"][sec] = nl
        out["p_by_circuit"][sec] = P
        for f in f_info:
            inf = _trim_plan(d3r_plan(P, {c: f for c in ids}, ids, k4, S99, S999, floor=FLOOR_2X4,
                                      round_to=ROUND_TO_2X4, margin=MARGIN, readout_factor=READOUT_FACTOR))
            inf.update({"y_c": READOUT_FACTOR * MARGIN * f, "f": f, "label": INFO_LABEL})
            out["information"][ftag(f)][sec] = inf
    return out


def hqc_columns(shots_by_circuit, mans):
    """HQC of a shot plan (information): (a) the k = 1 HQC/shot of each source (B0_ref102_k1 manifests: structured,
    opt3) times the shots, as prompts/36 A3 states; (b) the per-circuit structured manifests through
    gate_Q0P_2x3.cost_of_plan (5 HQC per job of <= 10 000 shots + the circuit's own HQC/shot)."""
    import gate_Q0P_2x3 as Q
    d = os.path.join(ROOT, "data", "quantinuum", "circuits_2x4")
    rate = {src: float(load_json(os.path.join(d, f"B0_ref102_k1.{src}.manifest.json"))["hqc_per_shot"])
            for src in ("structured", "opt3")}
    tot = int(sum(shots_by_circuit.values()))
    m2 = {c: {"counts": mans[c]["counts"], "sector": mans[c]["sector"]} for c in shots_by_circuit}
    cp = Q.cost_of_plan(shots_by_circuit, m2, {c: mans[c]["hqc_per_shot"] for c in shots_by_circuit})
    return {"shots": tot, "hqc_at_k1_rate": {src: tot * r for src, r in rate.items()}, "k1_rate_hqc_per_shot": rate,
            "k1_rate_source": "data/quantinuum/circuits_2x4/B0_ref102_k1.<source>.manifest.json hqc_per_shot",
            "hqc_structured_per_circuit_manifests": cp["hqc_total"], "jobs_structured": cp["jobs"],
            "label": INFO_LABEL}


def stage_plan_2x4():
    t0 = time.time()
    M, codec, acc, sectors = sectors_L(4)
    mans = circuits_L(4)
    pl = plan_noiseless_L(M, sectors, mans)
    pl.pop("p_by_circuit")
    for fk, d in pl["information"].items():
        allc = {}
        for sec, v in d.items():
            allc.update(v["shots"])
            v["hqc"] = hqc_columns(v["shots"], mans)
        d["campaign"] = hqc_columns(allc, mans)
    pl.update({"prompt": PROMPT_36, "runtime_s": time.time() - t0, "n_circuits": len(mans),
               "rule": ("D3'-R (h0_support_plan.d3r_plan) at f = 1, margin 1, readout factor 1 (y_c = 1): LP lambda* on S99 "
                        "with floor 267 (round to 100), then the k = 4 top-up until P(recall S999 >= 0.9) >= 0.95")})
    os.makedirs(CV4_DIR, exist_ok=True)
    p = os.path.join(CV4_DIR, "plan.json")
    with open(p, "w") as fh:
        json.dump(_j(pl), fh, indent=1)
    print(f"wrote {rel(p)}: " + "; ".join(f"{s} {v['shots_total']} shots ({v['lp_status']})"
                                          for s, v in pl["noiseless"].items()))
    return 0


def _stage_file(name):
    p = os.path.join(CV4_DIR, name)
    if not os.path.exists(p):
        raise SystemExit(f"{rel(p)} missing: run the earlier --lattice 4 stage first")
    return load_json(p)


def chunk_2x4(seed, quick=False):
    """One emulation seed, both sectors (prompts/36 A4): 8 N_c exact samples per circuit at f_proxy = 1, p_ro = 0 (no
    readout flip at f = 1), CV0-CV5 at the 1x plan on B_all | refs, CV3 = the k = 4 -> 5 step at equal shots.
    -> data/cv/2x4/chunk_<seed>[_quick].json"""
    from skqd.noise import measure_and_decode, measure_and_decode_sequence
    from skqd.skqd import h1_energy_tolerance

    t0 = time.time()
    M, codec, acc, sectors = sectors_L(4)
    cw = codec.all_codewords()
    if quick:
        from gate_H0_2x2 import RANDOM_SEEDS
        del RANDOM_SEEDS[50:]
    mans = circuits_L(4)
    plan = _stage_file("plan.json")["noiseless"]
    et_file = _stage_file("etol.json")["E_tol"]
    frag = {"seed": int(seed), "quick": bool(quick), "prompt": PROMPT_36, "sectors": {}}
    for sec, S in sectors.items():
        E_tol = h1_energy_tolerance(S.H, S.prob, S.refs, 0.8, 1e-3, sector_idx=S.sector_idx, E0=S.E0)["E_tol"]
        states, dt, dt_dev = circuit_states_L(S, mans)
        ids = sorted(states)
        plan_sec = {c: int(plan[sec]["shots"][c]) for c in ids}
        c0 = ids[0]
        n0 = SAMPLE_MULT * plan_sec[c0]
        dec, _ = measure_and_decode_sequence(codec, cw, states[c0], n0, 1.0, 0.0, np.random.default_rng(int(seed)), S.twoB)
        a_ref, _ = measure_and_decode(codec, cw, states[c0], n0, 1.0, 0.0, np.random.default_rng(int(seed)), S.twoB)
        u, cnt = np.unique(dec[dec >= 0], return_counts=True)
        hist_ok = {int(k): int(v) for k, v in zip(u, cnt)} == {int(k): int(v) for k, v in a_ref.items()}
        states_k5 = k_next_states(S, dt=dt)
        rs = run_seed(S, states, plan_sec, 1.0, seed, codec, cw, mans, E_tol, ckeep=False, states_k5=states_k5,
                      f_proxy=1.0, p_ro=0.0, dtype=np.int32, cache_dir=CV4_DIR)
        rs.pop("_seqs", None)
        rs.pop("_ids", None)
        c = rs["criteria_1x"]
        print(f"  [{sec} seed {seed}] " + " ".join(f"{k}:{'ok' if c[k]['ok'] else 'FAIL'}" for k in
                                                   ("CV1", "CV2", "CV3", "CV4", "CV5"))
              + f" cv0:{'ok' if rs['cv0']['ok'] else 'FAIL'} ({rs['runtime_s']:.0f} s)", flush=True)
        frag["sectors"][sec] = {"E_tol": E_tol, "E_tol_stage_file": et_file[sec]["value"], "ids": ids, "plan_1x": plan_sec,
                                "N_sector_1x": int(sum(plan_sec.values())), "dt": dt,
                                "manifest_dt_vs_reference_dt_max_abs": dt_dev, "sequence_histogram_identity": bool(hist_ok),
                                "sequence_identity_circuit": c0, "k5_ids": sorted(states_k5), "seed_result": rs,
                                "pass_1x": bool(all(c[k]["ok"] for k in ("CV1", "CV2", "CV4", "CV5")))}
    frag["runtime_s"] = time.time() - t0
    frag["random_baseline_sizes_evaluated"] = {sec: len(S._rand) for sec, S in sectors.items()}
    os.makedirs(CV4_DIR, exist_ok=True)
    p = os.path.join(CV4_DIR, f"chunk_{int(seed)}{'_quick' if quick else ''}.json")
    with open(p, "w") as fh:
        json.dump(_j(frag), fh, indent=1)
    print(f"wrote {rel(p)} ({frag['runtime_s']:.0f} s)")
    return frag


def resize_2x4(s, seeds=SEEDS, quick=False):
    """The re-sizing point s (> 1) for every seed and both sectors on prefixes of the cached 8 N samples (prompts/31
    ruling 4 / prompts/36 R3 (iii)) -> data/cv/2x4/resize_s<s>.json."""
    t0 = time.time()
    M, codec, acc, sectors = sectors_L(4)
    cw = codec.all_codewords()
    if quick:
        from gate_H0_2x2 import RANDOM_SEEDS
        del RANDOM_SEEDS[50:]
    mans = circuits_L(4)
    out = {"s": s, "seeds": [int(x) for x in seeds], "sectors": {}}
    for sec, S in sectors.items():
        states, dt, _ = circuit_states_L(S, mans)
        ids = sorted(states)
        res_s, ok_all = {}, True
        for seed in seeds:
            ch = load_json(os.path.join(CV4_DIR, f"chunk_{int(seed)}{'_quick' if quick else ''}.json"))["sectors"][sec]
            plan_sec = {c: int(v) for c, v in ch["plan_1x"].items()}
            seqs, sinfo = sample_sequences(S, states, plan_sec, SAMPLE_MULT, 1.0, int(seed), codec, cw,
                                           f"{sec.replace('=', '')}_{1.0:.2f}_{int(seed)}", p_ro=0.0, dtype=np.int32,
                                           cache_dir=CV4_DIR)
            if not sinfo["hit"]:
                raise SystemExit(f"{sec} seed {seed}: the 8 N sample cache was not found (run the chunk first)")
            rs = ch["seed_result"]
            ph, pf, Ns, capped = resize_points(S, seqs, ids, plan_sec, s)
            crit = evaluate(S, ph, pf, rs["curves"]["shots"], rs["curves"]["krylov_equal"][:4], ch["E_tol"],
                            BASIS_2X3, extra_cv4=(ph, pf))
            ok = all(crit[k]["ok"] for k in ("CV1", "CV2", "CV4", "CV5"))
            ok_all &= ok
            res_s[str(seed)] = {"half": strip({k: v for k, v in ph.items() if k != "B_sig_list"}),
                                "full": strip({k: v for k, v in pf.items() if k != "B_sig_list"}),
                                "criteria": crit, "ok": ok, "capped_circuits": capped}
        out["sectors"][sec] = {"shots_by_circuit": Ns, "shots_total": int(sum(Ns.values())), "seeds": res_s,
                               "ok_all_seeds": ok_all}
        print(f"  [{sec}] resize s={s}: {'PASS' if ok_all else 'FAIL'}", flush=True)
    out["runtime_s"] = time.time() - t0
    p = os.path.join(CV4_DIR, f"resize_s{s:g}{'_quick' if quick else ''}.json")
    with open(p, "w") as fh:
        json.dump(_j(out), fh, indent=1)
    return out


def gpu_plan(final, mans, n_eq):
    """prompts/36 R5: per circuit N_c^GPU = max(8 N_c^final, 6250) + U_c, U_c = ceil(2e5 / circuits of the sector);
    prefix lengths {round(phi N_c^final)} u {8 N_c^final} u {N_eq, 2 N_eq} (the CV3 equal-shots prefixes), all inside
    the first max(8 N_c^final, 6250) shots; the uniform block is the last U_c shots."""
    n_by_tb = {}
    for c in final:
        n_by_tb[int(mans[c]["twoB"])] = n_by_tb.get(int(mans[c]["twoB"]), 0) + 1
    U = {tb: int(math.ceil(UNIFORM_PER_SECTOR / n)) for tb, n in n_by_tb.items()}
    out = {}
    for c, N in final.items():
        tb = int(mans[c]["twoB"])
        cv = max(GPU_MULT * int(N), GPU_MIN_SHOTS)
        ne = int(n_eq[tb])
        pref = sorted({rnd(phi * int(N)) for phi in PHI} | {GPU_MULT * int(N), ne, 2 * ne})
        if max(pref) > cv:
            raise SystemExit(f"{c}: a prefix ({max(pref)}) exceeds the order-kept CV block ({cv})")
        out[c] = {"shots": cv + U[tb], "plan_shots": int(N), "cv_block": cv, "uniform_shots": U[tb],
                  "prefix_lengths": pref}
    return out, U


def k5_plan(sectors, n_eq):
    """The k = 5 runs of slots 05 / 06 (CV3 on the GPU): the equal-shots sample N_eq of the sector (2 N_eq kept as
    information), sampled at max(2 N_eq, 6250) shots so that the per-state test K2 has C1_IDEAL's minimum."""
    out = {}
    for sec, tb in SECTORS:
        for r in sectors[sec].refs:
            c = f"{sec.replace('=', '')}_ref{int(r)}_k{K_NEXT}"
            ne = int(n_eq[tb])
            out[c] = {"shots": max(2 * ne, GPU_MIN_SHOTS), "plan_shots": ne, "prefix_lengths": [ne, 2 * ne],
                      "uniform_shots": 0, "twoB": tb, "reference": int(r), "k": K_NEXT}
    return out


def ensure_resize(s, seeds, quick):
    p = os.path.join(CV4_DIR, f"resize_s{s:g}{'_quick' if quick else ''}.json")
    if os.path.exists(p):
        d = load_json(p)
        if d.get("seeds") == [int(x) for x in seeds]:
            return d
    return _j(resize_2x4(s, seeds, quick))


def _git(*args):
    import subprocess
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True)


def unchanged_files(paths, ref="HEAD"):
    """git diff --quiet <ref> -- path for each path (True = unchanged against ref, working tree included)."""
    return {p: _git("diff", "--quiet", ref, "--", p).returncode == 0 for p in paths}


BUNDLE_INDEX_2X4 = os.path.join(ROOT, "data", "quantinuum", "circuits_2x4_qpy", "index.json")
CHECK143_2X4 = os.path.join(ROOT, "data", "quantinuum", "circuits_2x4_qpy", "irl0_check_qiskit143.json")
REGRESSION_2X4 = os.path.join(CV4_DIR, "regression.json")
SLOT01_COMMIT = "6b8f8fc"
REGRESSION_FILES = ("validation/CV_2x3_plan.json", "validation/Q0P_2x3.json", "validation/C1_IDEAL.json",
                    "validation/QN_2x2.json", "validation/QN_2x4.json", "validation/Q0P_2x4.json",
                    "data/cv/acceptance_2x3.json")


def a6_slots(final_gpu, k5, mans):
    """A6: the part files QV_2x4_02..07 against the plan, the bundles, the seed rule and the 2700 s budget."""
    from skqd.campaign33 import tokens as T
    from skqd.campaign33.circuits import sha256_file
    import gate_Q0P_2x3 as Q
    import quantinuum_lattice_tests as QL
    bidx = load_json(BUNDLE_INDEX_2X4).get("irl0", {}) if os.path.exists(BUNDLE_INDEX_2X4) else {}
    spi = QL.s_per_instruction()
    toks = T.load_tokens()
    want = dict(final_gpu)
    want.update(k5)
    out, ok_all = {}, True
    for slot in SLOTS_2X4:
        p = os.path.join(QL.PARTS_DIR, slot + ".json")
        if not os.path.exists(p):
            out[slot] = {"exists": False, "ok": False}
            ok_all = False
            continue
        part = load_json(p)
        withheld = str(part.get("status", "")).startswith("withheld")
        s0 = T.base_seed(slot, toks)
        bad = []
        for r in part.get("runs", []):
            if r.get("kind") == "sample":
                c = r["base_id"]
                w = want.get(c)
                e = bidx.get(c)
                if w is None or e is None:
                    bad.append(f"{c}: not in the plan or not in the bundle index")
                    continue
                if (int(r["shots"]) != int(w["shots"]) or int(r["plan_shots"]) != int(w["plan_shots"])
                        or list(r["prefix_lengths"]) != list(w["prefix_lengths"])
                        or int(r["uniform_shots"]) != int(w["uniform_shots"])):
                    bad.append(f"{c}: shots / prefixes differ from the plan")
                if int(r["seed"]) != T.chunk_seed(s0, int(r["circuit_index"]), 0, int(r["shots"])):
                    bad.append(f"{c}: seed rule")
                if int(r["circuit_index"]) != int(e["circuit_index"]):
                    bad.append(f"{c}: circuit index")
                path = os.path.join(ROOT, r["qpy"])
                if r["gz_sha256"] != e["gz_sha256"] or not os.path.exists(path) or sha256_file(path) != r["gz_sha256"]:
                    bad.append(f"{c}: gz sha256")
                if int(r["n_instructions"]) != int(e["n_instructions"]):
                    bad.append(f"{c}: n_instructions")
        pred = part.get("prediction") or {}
        n_sample = sum(1 for r in part.get("runs", []) if r.get("kind") == "sample")
        rec = {"exists": True, "status": part.get("status"), "withheld": withheld, "n_runs": len(part.get("runs", [])),
               "n_sample_runs": n_sample, "native_status": part.get("native_status"),
               "prediction": pred, "s0": s0, "token_index": T.token_index(slot, toks), "mismatches": bad[:20],
               "s_per_instruction_equals_S2_2x4": (pred.get("s_per_instruction") == spi) if pred else None}
        if withheld:
            rec["ok"] = not bad and n_sample == 0
        else:
            rec["ok"] = bool(not bad and pred and pred.get("fits") and float(pred["predicted_s"]) <= SLOT_BUDGET_S
                             and rec["s_per_instruction_equals_S2_2x4"])
        ok_all &= rec["ok"]
        out[slot] = rec
    covered = sorted(r["base_id"] for slot in SLOTS_2X4
                     for r in (load_json(os.path.join(QL.PARTS_DIR, slot + ".json")).get("runs", [])
                               if os.path.exists(os.path.join(QL.PARTS_DIR, slot + ".json")) else [])
                     if r.get("kind") == "sample")
    cover_ok = covered == sorted(want)
    s01 = _git("show", f"{SLOT01_COMMIT}:ci/parts/QV_2x4_01.json")
    with open(os.path.join(QL.PARTS_DIR, "QV_2x4_01.json"), "rb") as fh:
        s01_same = s01.returncode == 0 and fh.read() == s01.stdout
    tk = Q.token_index_check()
    return {"slots": out, "every_sampled_circuit_in_exactly_one_slot": cover_ok, "n_sampled_circuits": len(covered),
            "slot01_byte_identical_to": SLOT01_COMMIT, "slot01_byte_identical": bool(s01_same),
            "token_indices": tk, "ok": bool(ok_all and cover_ok and s01_same and tk.get("ok"))}


def a7_bundles(mans, k5):
    """A7: the 75 IR-L0 bundles in data/quantinuum/circuits_2x4_qpy/index.json ("irl0"), checked as written."""
    from skqd.campaign33.circuits import sha256_file
    if not os.path.exists(BUNDLE_INDEX_2X4) or "irl0" not in load_json(BUNDLE_INDEX_2X4):
        return {"ok": False, "reason": "no irl0 bundle index (run quantinuum_lattice_tests.py --lattice 4 --tier bundles-2x4)"}
    idx = load_json(BUNDLE_INDEX_2X4)
    ir = idx["irl0"]
    want = sorted(list(mans) + list(k5))
    bad_sha, count_rule = [], {}
    total = 0
    for c in want:
        e = ir.get(c)
        if e is None:
            bad_sha.append(f"{c}: missing")
            continue
        p = os.path.join(ROOT, e["file"])
        if not os.path.exists(p) or sha256_file(p) != e["gz_sha256"]:
            bad_sha.append(f"{c}: sha256")
        total += os.path.getsize(p) if os.path.exists(p) else 0
        k = int(e["k"])
        count_rule[c] = {"k": k, "n_unitary_instructions": int(e["n_unitary_instructions"]),
                         "expected_as_written": k * IR_L0_PER_STEP,
                         "holds": int(e["n_unitary_instructions"]) == k * IR_L0_PER_STEP}
    by_k = {}
    for c, v in count_rule.items():
        by_k.setdefault(v["k"], set()).add(v["n_unitary_instructions"])
    chk = load_json(CHECK143_2X4) if os.path.exists(CHECK143_2X4) else None
    same = idx.get("irl0_vs_slot01_sources", {})
    rule_ok = all(v["holds"] for v in count_rule.values()) and len(count_rule) == len(want)
    same_ok = bool(same) and all(v.get("byte_identical") or v.get("gate_for_gate_identical_unitary_part")
                                 for v in same.values())
    rt_ok = bool(chk and chk.get("ok"))
    return {"n_bundles": len(ir), "expected": len(want), "missing_or_bad_sha": bad_sha[:20], "total_bytes": total,
            "cap_bytes": BUNDLE_CAP_BYTES, "within_cap": total <= BUNDLE_CAP_BYTES,
            "n_instructions_rule_as_written": f"n_unitary_instructions == k x {IR_L0_PER_STEP}",
            "n_instructions_rule_holds": rule_ok,
            "n_instructions_rule_failures": sorted(c for c, v in count_rule.items() if not v["holds"]),
            "n_unitary_instructions_by_k": {str(k): sorted(v) for k, v in sorted(by_k.items())},
            "slot01_sources": same, "slot01_sources_ok": same_ok, "roundtrip_qiskit143": chk,
            "roundtrip_ok": rt_ok,
            "ok": bool(not bad_sha and len(ir) >= len(want) and total <= BUNDLE_CAP_BYTES and rule_ok and same_ok and rt_ok)}


def stage_regression_2x4():
    """A8 inputs: pytest -q tests (coding), the campaign-33 / ci_gpu_mode / prompts/36 tests on the qiskit 1.4.3 twin,
    check_package.py, the Q0P_2x3 criterion-by-criterion reproduction in memory (Q7 of prompts/35, without rewriting
    the file), and the git state of the 2x3 / 2x2 records -> data/cv/2x4/regression.json."""
    import subprocess

    import gate_Q0P_2x3 as Q
    t0 = time.time()
    twin = os.path.join(os.path.expanduser("~"), ".local", "share", "su2qc-qiskit143", "venv", "bin", "python")
    twin_tests = sorted(glob.glob(os.path.join(ROOT, "tests", "test_campaign33_*.py"))) + [
        os.path.join(ROOT, "tests", t) for t in ("test_ci_gpu_mode.py", "test_codec_acceptance.py", "test_qv_2x4_pipeline.py")]
    out = {}
    r = subprocess.run([Q.CODING_PY, "-m", "pytest", "-q", "tests", "-p", "no:cacheprovider"], cwd=ROOT,
                       capture_output=True, text=True)
    out["pytest_coding"] = {"python": Q.CODING_PY, "returncode": r.returncode,
                            "summary": (r.stdout.strip().splitlines() or [""])[-1]}
    r = subprocess.run([twin, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + [rel(t) for t in twin_tests if os.path.exists(t)],
                       cwd=ROOT, capture_output=True, text=True)
    out["pytest_qiskit143"] = {"python": twin, "returncode": r.returncode, "files": [rel(t) for t in twin_tests],
                               "summary": (r.stdout.strip().splitlines() or [""])[-1]}
    c = subprocess.run([Q.CODING_PY, os.path.join("scripts", "check_package.py")], cwd=ROOT, capture_output=True, text=True)
    out["check_package"] = {"returncode": c.returncode, "tail": "\n".join(c.stdout.strip().splitlines()[-3:]),
                            "package_ok": "PACKAGE OK" in c.stdout}
    ch = Q.run_tests()
    out["q0p_2x3_reproduction"] = Q.reproduce_2x3(ch)
    out["q0p_2x3_reproduction_tests"] = ch
    out["unchanged_vs_HEAD"] = unchanged_files(REGRESSION_FILES, "HEAD")
    out["unchanged_vs_prompt36_commit"] = unchanged_files(REGRESSION_FILES, "3c8afa6")
    out["git_head"] = _git("rev-parse", "--short", "HEAD").stdout.decode().strip()
    out["runtime_s"] = time.time() - t0
    os.makedirs(CV4_DIR, exist_ok=True)
    with open(REGRESSION_2X4, "w") as fh:
        json.dump(_j(out), fh, indent=1)
    print(json.dumps({k: (v.get("summary") if isinstance(v, dict) and "summary" in v else v)
                      for k, v in out.items() if k != "q0p_2x3_reproduction_tests"}, default=str)[:2000])
    return 0


def noisy_information_2x4():
    """R8 / A9: N x f0 for N in {1e2, 1e4, 1e6} per Quantinuum scenario from validation/QN_2x4.json (the best circuit and
    B0_ref102_k1.opt3), the per-shot cost floor, no shot sampled."""
    import quantinuum_lattice_tests as QL
    q = load_json(os.path.join(ROOT, "validation", "QN_2x4.json"))["data"]["analytic"]["f0"]
    spi = QL.s_per_instruction()
    scen = sorted({s for v in q.values() for s in v})
    rows = {}
    for s in scen:
        vals = {c: float(v[s]["f0"]) for c, v in q.items() if s in v}
        best = max(vals, key=vals.get)
        ref = vals.get("B0_ref102_k1.opt3")
        rows[s] = {"f0_max_over_circuits": vals[best], "f0_max_circuit": best, "f0_B0_ref102_k1_opt3": ref,
                   "expected_clean_shots": {f"N={n:.0e}": n * vals[best] for n in (1e2, 1e4, 1e6)},
                   "expected_clean_shots_B0_ref102_k1_opt3": ({f"N={n:.0e}": n * ref for n in (1e2, 1e4, 1e6)}
                                                              if ref is not None else None)}
    return {"sampled_shots": 0, "statement": "no noisy 2x4 cell; information only", "scenarios": rows,
            "n_circuits": len(q), "source": "validation/QN_2x4.json data.analytic.f0",
            "per_shot_cost_floor_s": spi * IR_L0_PER_STEP,
            "per_shot_cost_floor_rule": ("one noisy trajectory is at least one statevector pass of a k = 1 IR-L0 circuit: "
                                         "s_per_instruction (validation/S2_2x4.json) x 142288 instructions; a 28-qubit "
                                         "density matrix does not fit"),
            "ruling": "prompts/36 R8"}


def assemble_2x4(seeds=SEEDS, quick=False):
    """validation/CV_2x4_plan.json + reports/CV_2x4_plan.md (prompts/36 section 2.1, criteria A1-A9)."""
    import quantinuum_lattice_tests as QL
    t0 = time.time()
    gate = "CV_2x4_plan" + ("_quick" if quick else "")
    R = GateResult(gate, "the 2x4 noiseless shot plan (D3'-R at y = 1), its convergence in the exact emulation, the "
                         "decoder acceptance, the IR-L0 bundles and the GPU slot contents (prompts/36)")
    acc = load_json(ACC_FILE[4])
    et = _stage_file("etol.json")
    pl = _stage_file("plan.json")
    sfx = "_quick" if quick else ""
    chunks = {}
    for sd in seeds:
        p = os.path.join(CV4_DIR, f"chunk_{int(sd)}{sfx}.json")
        if os.path.exists(p):
            chunks[str(sd)] = load_json(p)
    complete = len(chunks) == len(seeds)
    M, codec, _acc, sectors = sectors_L(4)
    mans = circuits_L(4)
    stops = []
    # ---- A1
    P = QL.Phys(4)
    phys = {sec: {"a_phys": P.sector[tb]["a"], "a_file": acc[sec]["fraction"], "source": P.sector[tb].get("a_source")}
            for sec, tb in SECTORS}
    phys_ok = all(v["a_phys"] == v["a_file"] and v["source"] == rel(ACC_FILE[4]) for v in phys.values())
    cc = acc["cross_checks"]
    a1 = (cc["2x2"]["factorised_equals_exhaustive"] and cc["2x3"]["factorised_equals_exhaustive"] and phys_ok
          and all(isinstance(acc[sec]["accepted"], int) and acc[sec]["monte_carlo"]["within_3_sigma"] for sec, _ in SECTORS))
    R.add("A1 acceptance: factorised = exhaustive at 2x2 and 2x3 (counts and the four reasons), 2x4 counted, Monte-Carlo "
          "1e7 strings (seed 36) within 3 sigma, Phys reads the file",
          {"2x2_equal": cc["2x2"]["factorised_equals_exhaustive"], "2x3_equal": cc["2x3"]["factorised_equals_exhaustive"],
           **{sec: {"accepted": acc[sec]["accepted"], "dimension": acc[sec]["dimension"],
                    "equals_dimension": acc[sec]["equals_dimension"], "fraction": acc[sec]["fraction"],
                    "mc_accepted": acc[sec]["monte_carlo"]["accepted"], "mc_z": acc[sec]["monte_carlo"]["z"]}
              for sec, _ in SECTORS}, "phys_a_matches_file": phys_ok},
          "equal; |z| <= 3; Phys a = file", a1)
    # ---- A2
    E_tol = et["E_tol"]
    et_same = {sd: {sec: abs(ch["sectors"][sec]["E_tol"] - E_tol[sec]["value"]) for sec, _ in SECTORS}
               for sd, ch in chunks.items()}
    a2 = all(E_tol[sec]["value"] > 0 and E_tol[sec]["states_top"] and E_tol[sec]["n_top"] > 0 for sec, _ in SECTORS) \
        and all(v <= 1e-15 for d in et_same.values() for v in d.values())
    R.add("A2 E_tol per sector = E_R(R u top 80 % of S999) - E0 > 0 (h1_energy_tolerance(H, prob, refs, 0.8, 1e-3))",
          {sec: {"value": E_tol[sec]["value"], "n_top": E_tol[sec]["n_top"], "E_R": E_tol[sec]["E_R"],
                 "references": len(E_tol[sec]["references"])} for sec, _ in SECTORS},
          "> 0; chunk recomputation identical", a2)
    # ---- A3
    nl = pl["noiseless"]
    n_all = sum(len(v["shots"]) for v in nl.values())
    a3_rows = {sec: {"lp_status": v["lp_status"], "shots_total": v["shots_total"], "n_circuits": len(v["shots"]),
                     "min_shots": min(v["shots"].values()), "k4_extra_per_circuit": v["k4_extra_per_circuit"],
                     "P_recall_S999_ge_0.9": v["P_recall_S999_ge_target"], "floor_circuits": v["floor_circuits"]}
               for sec, v in nl.items()}
    info_ok = all(ftag(f) in pl["information"] and all(sec in pl["information"][ftag(f)] and
                                                      "hqc" in pl["information"][ftag(f)][sec] for sec, _ in SECTORS)
                  for f in F_INFO_2X4)
    a3 = (all(r["lp_status"] == "optimal" and r["min_shots"] >= FLOOR_2X4 and r["P_recall_S999_ge_0.9"] >= 0.95
              for r in a3_rows.values()) and n_all == len(mans) == 60 and info_ok)
    R.add("A3 plan: D3'-R at y = 1 feasible (LP optimal), 60 circuits each >= 267, k = 4 top-up recorded, P(recall S999 >= "
          "0.9) >= 0.95 per sector; information columns f = 0.10 / 0.05 with HQC (" + INFO_LABEL + ")",
          {**a3_rows, "information": {ftag(f): {sec: pl["information"][ftag(f)][sec]["shots_total"] for sec, _ in SECTORS}
                                      for f in F_INFO_2X4}},
          "optimal; >= 267; >= 0.95; columns present", a3)
    # ---- A4 (CV on the emulation)
    cv3_by_seed, cv0_rows, crit1 = {}, {}, {}
    for sd, ch in chunks.items():
        for sec, _ in SECTORS:
            sdd = ch["sectors"][sec]
            rs = sdd["seed_result"]
            cv3_by_seed.setdefault(sd, {})[sec] = rs["criteria_1x"]["CV3"]
            cv0_rows.setdefault(sd, {})[sec] = {"cv0": rs["cv0"]["ok"], "histogram": sdd["sequence_histogram_identity"],
                                                "k5_replay": rs["cv0"].get("k5_stream_replay_identical")}
            crit1.setdefault(sd, {})[sec] = rs["criteria_1x"]
    cv3_ok = bool(chunks) and all(c["ok"] for d in cv3_by_seed.values() for c in d.values())
    if chunks and not cv3_ok:
        stops.append("CV3 (k = 4 -> 5 at equal shots) > E_tol in the emulation (prompts/36 A4: STOP, family question)")
    cv0_ok = bool(chunks) and all(v["cv0"] and v["histogram"] and v["k5_replay"] for d in cv0_rows.values() for v in d.values())
    R.add("A4.0 CV0 structural (prompts/30): nested prefixes, E_R(B_all) non-increasing, E_R >= E0 - 1e-9, the sequence "
          "histogram = measure_and_decode, the k = 5 stream replay = cache",
          cv0_rows, "all true", cv0_ok)
    s_final, ladder = None, {}
    if complete:
        if all(ch["sectors"][sec]["pass_1x"] for ch in chunks.values() for sec, _ in SECTORS):
            s_final = 1
        else:
            for s in PHI_RESIZE:
                rz = ensure_resize(s, seeds, quick)
                ladder[f"{s:g}"] = rz
                if all(rz["sectors"][sec]["ok_all_seeds"] for sec, _ in SECTORS):
                    s_final = s
                    break
            if s_final is None:
                stops.append("re-sizing to s = 8 still fails CV1/CV2/CV4/CV5 (prompts/31 fix (g))")
    final, crit_final, cert = {}, {}, {}
    if s_final is not None:
        for sec, _ in SECTORS:
            if s_final == 1:
                final.update({c: int(v) for c, v in nl[sec]["shots"].items()})
            else:
                final.update({c: int(v) for c, v in ladder[f"{s_final:g}"]["sectors"][sec]["shots_by_circuit"].items()})
        for sd, ch in chunks.items():
            for sec, _ in SECTORS:
                if s_final == 1:
                    c = crit1[sd][sec]
                    pt = ch["sectors"][sec]["seed_result"]["curves"]["shots"][-1]
                else:
                    z = ladder[f"{s_final:g}"]["sectors"][sec]["seeds"][sd]
                    c = dict(z["criteria"])
                    c["CV3"] = crit1[sd][sec]["CV3"]
                    pt = z["full"]
                crit_final.setdefault(sd, {})[sec] = c
                a = pt["all"]
                inside = a["E0_in_kt"] if sec == "B=0" else a["E0_in_weinstein"]
                cert.setdefault(sd, {})[sec] = {
                    "shots": pt["shots"], "B_all_size": pt["B_all_size"], "recall_S999": a["recall_S999"],
                    "E_R_minus_E0": a["err"], "W": a["W"], "type": CV2_TYPE[sec],
                    "interval": a["kt_rigorous"] if sec == "B=0" else a["weinstein"], "E0_inside": bool(inside),
                    "rH": a["rH"], "kt_width": a["kt_width"],
                    "kt_exact_E1_information": {"interval": a["kt_rigorous"], "rigorous": a["E_R_below_E1"]},
                    "ok": bool(a["recall_S999"] >= 0.9 and inside and a["err"] >= -TOL_VAR and a["W"] >= W_TARGET)}
    n_eq = {}
    for sec, tb in SECTORS:
        ids = sorted(c for c in final if int(mans[c]["twoB"]) == tb)
        if ids:
            n_eq[tb] = int(math.ceil(sum(final[c] for c in ids) / len(ids) / 100.0) * 100)
    gpu, U = gpu_plan(final, mans, n_eq) if final else ({}, {})
    k5 = k5_plan(sectors, n_eq) if final else {}
    final_ok = bool(s_final is not None and all(all(c[k]["ok"] for k in ("CV1", "CV2", "CV4", "CV5"))
                                                 for d in crit_final.values() for c in d.values()))
    R.add("A4 CV on the exact emulation (3 seeds, prefixes of 8 N samples at f = 1, p_ro = 0): the smallest s in {1, 1.5, "
          "2, 3, 4, 6, 8} at which CV1, CV2, CV4, CV5 hold in all seeds and both sectors; CV3 (k = 4 -> 5, equal shots) "
          "<= E_tol in every seed (STOP otherwise)",
          {"resized_by": s_final, "seeds": sorted(chunks), "complete": complete,
           "CV3": {sd: {sec: f"{v['dE_k4_k5']:.3e} ({v['ratio']:.2f} E_tol)" for sec, v in d.items()}
                   for sd, d in cv3_by_seed.items()},
           "final_shots_total": int(sum(final.values())) if final else None,
           "gpu_shots_total": int(sum(v["shots"] for v in gpu.values())) if gpu else None},
          "s in grid; CV3 ok", bool(complete and final_ok and cv3_ok))
    # ---- A5
    a5 = bool(cert) and all(v["ok"] for d in cert.values() for v in d.values()) and complete
    R.add("A5 certificates at the final plan (every seed): recall S999 >= 0.9; E0 inside Kato-Temple (exact E1) at B=0 / "
          "Weinstein at B=1; E_R >= E0 - 1e-9; W >= 0.99",
          {sd: {sec: {k: v[k] for k in ("recall_S999", "E_R_minus_E0", "W", "E0_inside", "B_all_size")}
                for sec, v in d.items()} for sd, d in cert.items()},
          ">= 0.9; inside; >= -1e-9; >= 0.99", a5)
    # ---- A6
    a6 = a6_slots(gpu, k5, mans) if gpu else {"ok": False, "reason": "no final plan"}
    R.add("A6 slot contents ci/parts/QV_2x4_02..07: plan shots, seeds chunk_seed(s0(token), circuit index, 0, shots), QPY "
          "gz sha256, n_instructions, predicted_s <= 2700 at the S2_2x4 rate (06 native / 07 may be withheld, R7); token "
          "indices unchanged; slot 01 byte-identical to 6b8f8fc",
          {"slots": {s_: {k: v.get(k) for k in ("ok", "status", "n_runs", "withheld")} | {
              "predicted_s": (v.get("prediction") or {}).get("predicted_s")} for s_, v in a6.get("slots", {}).items()},
           "coverage": a6.get("every_sampled_circuit_in_exactly_one_slot"),
           "slot01_byte_identical": a6.get("slot01_byte_identical"),
           "token_indices_unchanged": (a6.get("token_indices") or {}).get("ok")},
          "all ok", a6["ok"])
    # ---- A7
    a7 = a7_bundles(mans, k5) if final else {"ok": False, "reason": "no final plan"}
    R.add(f"A7 bundles: 75 IR-L0 qpy13 bundles (60 family + 15 k = 5) with gz sha256 and n_instructions in the index; "
          f"n_instructions == k x {IR_L0_PER_STEP} (as written in prompts/36 A7); the two slot-01 structured sources "
          f"byte- or gate-for-gate identical; total <= 60 MB; round trip on qiskit 1.4.3",
          {k: a7.get(k) for k in ("n_bundles", "total_bytes", "within_cap", "n_instructions_rule_holds",
                                  "n_unitary_instructions_by_k", "slot01_sources_ok", "roundtrip_ok", "reason")},
          "all hold", a7["ok"])
    # ---- A8
    reg = load_json(REGRESSION_2X4) if os.path.exists(REGRESSION_2X4) else None
    dry = {}
    for s_ in SLOTS_2X4:
        p = os.path.join(ROOT, "validation", "dryrun", s_ + ".json")
        dry[s_] = load_json(p)["status"] if os.path.exists(p) else None
    unch = unchanged_files(REGRESSION_FILES, "HEAD")
    a8 = bool(reg and reg["pytest_coding"]["returncode"] == 0 and reg["pytest_qiskit143"]["returncode"] == 0
              and reg["check_package"]["package_ok"] and reg["q0p_2x3_reproduction"]["q0p_2x3_reproduced"]
              and all(unch.values()) and all(reg["unchanged_vs_prompt36_commit"].values())
              and all(v == "PASS" for v in dry.values()))
    R.add("A8 regression: pytest (coding) and the 1.4.3 twin tests pass, check_package PACKAGE OK, Q0P_2x3 reproduced "
          "criterion by criterion (in memory), the 2x3 / 2x2 records unchanged, dry runs QV_2x4_02..07 PASS",
          {"pytest_coding": (reg or {}).get("pytest_coding", {}).get("summary"),
           "pytest_qiskit143": (reg or {}).get("pytest_qiskit143", {}).get("summary"),
           "check_package": (reg or {}).get("check_package", {}).get("package_ok"),
           "q0p_2x3_reproduced": ((reg or {}).get("q0p_2x3_reproduction") or {}).get("q0p_2x3_reproduced"),
           "unchanged_vs_HEAD": all(unch.values()), "dry_runs": dry},
          "all pass", a8)
    # ---- A9
    noisy = noisy_information_2x4()
    R.add("A9 noisy information (R8): N x f0 for N in 1e2 / 1e4 / 1e6 per scenario, no shot sampled",
          {"sampled_shots": noisy["sampled_shots"], "statement": noisy["statement"],
           "max_expected_clean_at_1e6": max(v["expected_clean_shots"]["N=1e+06"] for v in noisy["scenarios"].values())},
          "sampled_shots == 0", noisy["sampled_shots"] == 0 and bool(noisy["scenarios"]))
    if not complete:
        R.add("completeness: one emulation chunk per seed", sorted(chunks), str([str(s) for s in seeds]), False)
    data = {
        "prompt": PROMPT_36, "lattice": "2x4", "basis": "B_all | refs",
        "what_pass_means": ("the 2x4 noiseless shot plan exists and converges in the exact emulation; the GPU slots are "
                            "sized; nothing has been sampled from a circuit yet"),
        "acceptance": acc, "phys_acceptance": phys, "E_tol": E_tol, "sectors": et["sectors"],
        "plan": {"noiseless": nl, "information": pl["information"], "rule": pl["rule"],
                 "final": {"resized_by": s_final, "shots_by_circuit": final, "shots_total": int(sum(final.values())),
                           "by_sector": {sec: int(sum(v for c, v in final.items() if int(mans[c]["twoB"]) == tb))
                                         for sec, tb in SECTORS},
                           "gpu_shots_by_circuit": {c: v["shots"] for c, v in gpu.items()},
                           "gpu_shots_total": int(sum(v["shots"] for v in gpu.values())),
                           "gpu": gpu, "uniform_shots_by_sector": {("B=0" if tb == 0 else "B=1"): u for tb, u in U.items()},
                           "N_eq_by_sector": {("B=0" if tb == 0 else "B=1"): v for tb, v in n_eq.items()},
                           "cv3_at_equal_shots": k5,
                           "gpu_rule": ("N_c^GPU = max(8 N_c^final, 6250) + U_c, U_c = ceil(2e5 / circuits of the sector); "
                                        "the first N_c^final shots are the plan point, the first 8 N_c^final the CV "
                                        "sequence, the last U_c the uniform 2e5-per-sector point; k = 5 runs: "
                                        "max(2 N_eq, 6250) shots, prefixes N_eq / 2 N_eq (prompts/36 R5, section 4)")}},
        "cv3": {"ok": cv3_ok, "by_seed": cv3_by_seed},
        "criteria_by_seed_1x": crit1, "criteria_by_seed_final": crit_final, "certificates": cert,
        "cv0_by_seed": cv0_rows, "E_tol_chunk_vs_stage_abs_diff": et_same,
        "resize_ladder": {s_: {sec: {"ok_all_seeds": v["sectors"][sec]["ok_all_seeds"],
                                     "shots_total": v["sectors"][sec]["shots_total"]} for sec, _ in SECTORS}
                          for s_, v in ladder.items()},
        "curves": {sd: {sec: ch["sectors"][sec]["seed_result"]["curves"] for sec, _ in SECTORS} for sd, ch in chunks.items()},
        "sampling": {sd: {sec: ch["sectors"][sec]["seed_result"]["sampling"] for sec, _ in SECTORS} for sd, ch in chunks.items()},
        "chunks": {sd: {"runtime_s": ch["runtime_s"], "random_baseline_sizes_evaluated": ch.get("random_baseline_sizes_evaluated"),
                        "k5_ids": {sec: ch["sectors"][sec]["k5_ids"] for sec, _ in SECTORS}} for sd, ch in chunks.items()},
        "slots": (a6 or {}).get("slots", {}), "slots_check": {k: v for k, v in a6.items() if k != "slots"},
        "bundles": a7, "regression": reg, "regression_unchanged_vs_HEAD": unch,
        "noisy_information": noisy,
        "stop": {"fired": bool(stops), "conditions": stops,
                 "rule": "prompts/36 section 9: D3'-R infeasible, CV3 failure in the emulation, or re-sizing to 8 failing"},
        "constants": {"seeds": list(seeds), "phi": list(PHI), "grid": list(GRID_2X4), "sample_mult": SAMPLE_MULT,
                      "f_proxy": 1.0, "p_ro": 0.0, "width": WIDTH, "cv2_type": CV2_TYPE, "W_target": W_TARGET,
                      "k_next": K_NEXT, "floor": FLOOR_2X4, "round_to": ROUND_TO_2X4, "gpu_mult": GPU_MULT,
                      "gpu_min_shots": GPU_MIN_SHOTS, "uniform_per_sector": UNIFORM_PER_SECTOR,
                      "random_seeds": "23..222 (gate_H0_2x2.RANDOM_SEEDS)" + (" (first 50: quick)" if quick else ""),
                      "slot_budget_s": SLOT_BUDGET_S, "bundle_cap_bytes": BUNDLE_CAP_BYTES,
                      "mc_strings": MC_STRINGS_2X4, "mc_seed": MC_SEED_2X4},
        "completed": complete}
    R.data = data
    R.runtime_s = sum(ch["runtime_s"] for ch in chunks.values()) + time.time() - t0
    path = R.save()
    write_report(f"{gate}.md", report_2x4(R, data))
    print(f"{gate}: {'PASS' if R.passed else 'FAIL'} -> {rel(path)}")
    for c in R.criteria:
        print(f"  [{'PASS' if c.passed else 'FAIL'}] {c.name[:90]}: {str(c.value)[:300]}")
    print("stop:", data["stop"])
    return 0 if R.passed else 1


def report_2x4(R, D):
    pl = D["plan"]
    fin = pl["final"]
    L = [f"# Gate {R.gate} — {R.title}", "",
         f"Status: **{'PASS' if R.passed else 'FAIL'}** ({sum(1 for c in R.criteria if c.passed)} of {len(R.criteria)} "
         f"criteria hold).  Generated by `scripts/gate_CV.py --lattice 4 --stage assemble` from `validation/{R.gate}.json`; "
         f"no number is typed by hand.  Prompt: {D['prompt']}.  Basis: **{D['basis']}**.  {env_block()}", "",
         f"What PASS means: {D['what_pass_means']}.", "",
         f"STOP fired: **{D['stop']['fired']}**" + (f" ({'; '.join(D['stop']['conditions'])})" if D["stop"]["fired"] else "")
         + f".  Rule: {D['stop']['rule']}.", "",
         "## Criteria", "", R.criteria_table(), "",
         "## A1 the decoder's random acceptance (exact, factorised; prompts/36 R2)", "",
         md_table(["sector", "accepted", "dimension", "equals dimension", "fraction", "flag", "link", "sector", "unknown",
                   "Monte-Carlo accepted / 1e7", "expected", "z"],
                  [[sec, fmt(D["acceptance"][sec]["accepted"]), fmt(D["acceptance"][sec]["dimension"]),
                    D["acceptance"][sec]["equals_dimension"], fmt(D["acceptance"][sec]["fraction"])]
                   + [fmt(D["acceptance"][sec]["reasons"][r]) for r in ACC_REASONS]
                   + [fmt(D["acceptance"][sec]["monte_carlo"]["accepted"]), fmt(D["acceptance"][sec]["monte_carlo"]["expected"]),
                      fmt(D["acceptance"][sec]["monte_carlo"]["z"])] for sec, _ in SECTORS]), "",
         "Cross-checks: " + "; ".join(f"{lat}: factorised = exhaustive {v['factorised_equals_exhaustive']} ({v['exhaustive_source']})"
                                      for lat, v in D["acceptance"]["cross_checks"].items()) + ".", "",
         "## A2 E_tol", "",
         md_table(["sector", "E_tol", "n_top (80 % of S999)", "E_R", "E_tol at recall 0.9 (information)"],
                  [[sec, fmt(v["value"]), v["n_top"], fmt(v["E_R"], 10), fmt(v["recall_0.9_information"])]
                   for sec, v in D["E_tol"].items()]), "",
         "## A3 / A4 the plan (noiseless D3'-R at y = 1; information columns: " + INFO_LABEL + ")", "",
         md_table(["sector", "noiseless shots", "LP shots", "k = 4 top-up per circuit", "P(recall S999 >= 0.9)",
                   "floor circuits", "final shots (x s)", "GPU shots", "uniform U_c", "N_eq (CV3)"],
                  [[sec, fmt(v["shots_total"]), fmt(v["lp_shots_total"]), fmt(v["k4_extra_per_circuit"]),
                    fmt(v["P_recall_S999_ge_target"]), v["floor_circuits"], fmt(fin["by_sector"].get(sec)),
                    fmt(sum(g for c, g in fin["gpu_shots_by_circuit"].items() if c.startswith(sec.replace("=", "")))),
                    fmt(fin["uniform_shots_by_sector"].get(sec)), fmt(fin["N_eq_by_sector"].get(sec))]
                   for sec, v in pl["noiseless"].items()]), "",
         f"Re-sizing: s = {fin['resized_by']}.  Final total {fmt(fin['shots_total'])} shots; GPU total "
         f"{fmt(fin['gpu_shots_total'])} shots ({fin['gpu_rule']}).", "",
         md_table(["column", "sector", "y_c", "shots", "HQC at the structured k = 1 rate", "HQC at the opt3 k = 1 rate",
                   "HQC structured per-circuit manifests", "label"],
                  [[fk, sec, fmt(v["y_c"]), fmt(v["shots_total"]), fmt(v["hqc"]["hqc_at_k1_rate"]["structured"]),
                    fmt(v["hqc"]["hqc_at_k1_rate"]["opt3"]), fmt(v["hqc"]["hqc_structured_per_circuit_manifests"]),
                    v["label"]] for fk, d in pl["information"].items() for sec, v in d.items() if sec != "campaign"]), "",
         "## A4 CV per seed at the final plan (B_all | refs)", "",
         md_table(["seed", "sector", "CV1 dE (/E_tol)", "CV2 width N/2 / N", "E0 inside", "CV3 dE (/E_tol)",
                   "CV4 margin (/E_tol)", "CV4 points below", "CV5 W", "pass"],
                  [[sd, sec, f"{fmt(c['CV1']['dE'])} ({fmt(c['CV1']['ratio'])})",
                    f"{fmt(c['CV2']['width_half'])} / {fmt(c['CV2']['width_full'])}",
                    f"{c['CV2']['E0_in_half']} / {c['CV2']['E0_in_full']}",
                    f"{fmt(c['CV3']['dE_k4_k5'])} ({fmt(c['CV3']['ratio'])})",
                    f"{fmt(c['CV4']['margin_at_N'])} ({fmt(c['CV4']['margin_over_E_tol'])})",
                    f"{c['CV4']['n_below']}/{c['CV4']['n_points']}", fmt(c["CV5"]["W_at_N"], 6),
                    all(c[k]["ok"] for k in ("CV1", "CV2", "CV3", "CV4", "CV5"))]
                   for sd, d in D["criteria_by_seed_final"].items() for sec, c in d.items()]), "",
         "## A5 certificates at the final plan", "",
         md_table(["seed", "sector", "shots", "|B_all|", "recall S999", "E_R - E0", "W", "certificate", "interval",
                   "E0 inside", "B=1 Kato-Temple (exact E1) information", "ok"],
                  [[sd, sec, fmt(v["shots"]), v["B_all_size"], fmt(v["recall_S999"]), fmt(v["E_R_minus_E0"]), fmt(v["W"], 6),
                    v["type"], "n/a" if v["interval"] is None else f"[{fmt(v['interval'][0], 8)}, {fmt(v['interval'][1], 8)}]",
                    v["E0_inside"], (f"rigorous {v['kt_exact_E1_information']['rigorous']}" if sec == "B=1" else ""), v["ok"]]
                   for sd, d in D["certificates"].items() for sec, v in d.items()]), "",
         "## A6 slots", "",
         md_table(["slot", "status", "runs", "sample runs", "predicted s", "budget s", "fits", "ok"],
                  [[s_, v.get("status"), v.get("n_runs"), v.get("n_sample_runs"),
                    fmt((v.get("prediction") or {}).get("predicted_s")), fmt((v.get("prediction") or {}).get("budget_s")),
                    (v.get("prediction") or {}).get("fits"), v.get("ok")] for s_, v in D["slots"].items()]), "",
         "## A7 bundles", "",
         f"{D['bundles'].get('n_bundles')} bundles, {fmt(D['bundles'].get('total_bytes'))} bytes (cap "
         f"{fmt(BUNDLE_CAP_BYTES)}); unitary instruction counts by k {D['bundles'].get('n_unitary_instructions_by_k')}; "
         f"rule as written `{D['bundles'].get('n_instructions_rule_as_written')}` holds: "
         f"{D['bundles'].get('n_instructions_rule_holds')}; slot-01 sources {D['bundles'].get('slot01_sources')}; "
         f"1.4.3 round trip ok {D['bundles'].get('roundtrip_ok')}.", "",
         "## A9 noisy information (R8: " + D["noisy_information"]["statement"] + ")", "",
         md_table(["scenario", "max f0 (circuit)", "N f0 at 1e2 / 1e4 / 1e6", "f0 B0_ref102_k1.opt3"],
                  [[s, f"{fmt(v['f0_max_over_circuits'])} ({v['f0_max_circuit']})",
                    " / ".join(fmt(x) for x in v["expected_clean_shots"].values()), fmt(v["f0_B0_ref102_k1_opt3"])]
                   for s, v in D["noisy_information"]["scenarios"].items()]), "",
         f"Per-shot cost floor of a noisy trajectory: {fmt(D['noisy_information']['per_shot_cost_floor_s'])} s "
         f"({D['noisy_information']['per_shot_cost_floor_rule']}).", ""]
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", nargs="+", default=["emulated-plan"],
                    help="emulated-plan | counts <dir>")
    ap.add_argument("--model", type=int, default=3)
    ap.add_argument("--f", type=float, nargs="+", default=list(F_GRID))
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    ap.add_argument("--quick", action="store_true", help="one seed, f = 0.10, 50 random seeds")
    ap.add_argument("--assemble", action="store_true", help="assemble validation/CV_2x3_plan.json from the fragments")
    ap.add_argument("--chunk-only", action="store_true", help="write the fragments, do not assemble")
    ap.add_argument("--lattice", type=int, default=3, choices=(3, 4),
                    help="4: the prompts/36 path (--stage acceptance | etol | plan | chunk --seed S | resize --s S | "
                         "regression | assemble)")
    ap.add_argument("--stage", default=None,
                    choices=("acceptance", "etol", "plan", "chunk", "resize", "regression", "assemble"))
    ap.add_argument("--seed", type=int, default=None, help="--lattice 4 --stage chunk: the emulation seed")
    ap.add_argument("--s", type=float, default=None, help="--lattice 4 --stage resize: the re-sizing factor")
    ap.add_argument("--monte-carlo", type=int, default=MC_STRINGS_2X4, help="--stage acceptance: Monte-Carlo strings")
    a = ap.parse_args()
    if a.lattice == 4:
        st = a.stage or "assemble"
        if st == "acceptance":
            return stage_acceptance_2x4(a.monte_carlo, MC_SEED_2X4)
        if st == "etol":
            return stage_etol_2x4()
        if st == "plan":
            return stage_plan_2x4()
        if st == "chunk":
            for sd in ([a.seed] if a.seed is not None else (list(a.seeds) if not a.quick else [SEEDS[0]])):
                chunk_2x4(sd, quick=a.quick)
            return 0
        if st == "resize":
            s = a.s if a.s is None or a.s != int(a.s) else int(a.s)
            resize_2x4(s, list(a.seeds), quick=a.quick)
            return 0
        if st == "regression":
            return stage_regression_2x4()
        return assemble_2x4(list(a.seeds) if not a.quick else [SEEDS[0]], quick=a.quick)
    if a.stage is not None:
        raise SystemExit("--stage is the --lattice 4 path (prompts/36); the 2x3 path keeps its flags")
    if a.source[0] == "counts":
        if len(a.source) < 2 or a.model != 2:
            raise SystemExit("--source counts <dir> --model 2")
        return run_2x2(a.source[1])
    fs, seeds = (([0.10], [SEEDS[0]]) if a.quick else (a.f, a.seeds))
    if a.assemble:
        return assemble_2x3(F_GRID if not a.quick else fs, seeds, a.quick)
    for f in fs:
        chunk_2x3(f, seeds, quick=a.quick)
    if a.chunk_only:
        return 0
    return assemble_2x3(F_GRID if not a.quick else fs, seeds, a.quick)


if __name__ == "__main__":
    sys.exit(main())
