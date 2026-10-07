"""
Analysis of the 2x3 campaign samples (prompts/33 section 2): decoding, clean-fraction cells, the SKQD
reference / CV readings on the order-kept chunks.  The SKQD and CV machinery is gate CV's own
(`scripts/gate_CV.py`: Sector, evaluate, cv3_block, h1_energy_tolerance) -- imported, never copied.
numpy / scipy and the package's physics core only (no qiskit).
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
G2 = 4.0
SECTORS = (("B=0", 0), ("B=1", 2))
TOL_VAR = 1e-9
TOL_MONO = 1e-12
E_TOL_ASSERT = 1e-12
CV_PLAN_JSON = os.path.join(ROOT, "validation", "CV_2x3_plan.json")
R_NC_JSON = os.path.join(ROOT, "data", "cf_trajectories", "r_nc.json")


def load_json(p):
    with open(p) as fh:
        return json.load(fh)


class Physics:
    """Model(3), the codec, the codeword table and gate CV's two Sector objects (built once)."""

    def __init__(self, with_sectors: bool = True):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        from skqd.codec import Codec
        from skqd.exact import Model
        from skqd.reference_sim import CodewordEmbedding
        self.M = Model(3)
        self.codec = Codec(self.M.basis)
        self.emb = CodewordEmbedding(self.M)
        self.n = int(self.emb.n)
        self.int_to_idx = {int(x): i for i, x in enumerate(self.emb.ints)}
        self.sector_of = {}
        for sec, tb in SECTORS:
            for i in self.M.basis.sector(tb):
                self.sector_of[int(i)] = tb
        self.S = {}
        if with_sectors:
            import gate_CV as CV
            acc = CV.acceptance_2x3(self.codec)
            for sec, tb in SECTORS:
                self.S[sec] = CV.Sector(self.M, "2x3", sec, tb, acc[sec]["fraction"])
            self.CV = CV

    def sector(self, twoB):
        return self.S["B=0" if twoB == 0 else "B=1"]


# --------------------------------------------------------------------------- decoding
def decode_counts(P: Physics, counts_int: dict, twoB: int, reasons: bool = False):
    """{string int: n} -> (accepted {full-basis index: n}, rejected count, reasons or None).  A string is
    accepted iff it is the codeword of a basis state of the target sector -- identical to Codec.decode
    with target_twoB (the exhaustive acceptance of gate CV accepts exactly dim strings per sector)."""
    acc, rej = {}, 0
    why = {"flag": 0, "link": 0, "sector": 0, "unknown": 0} if reasons else None
    for x, v in counts_int.items():
        i = P.int_to_idx.get(int(x))
        if i is not None and P.sector_of.get(i) == twoB:
            acc[i] = acc.get(i, 0) + int(v)
        else:
            rej += int(v)
            if reasons:
                from skqd.codec import Reject
                from skqd.reference_sim import int_to_bits
                try:
                    P.codec.decode(int_to_bits(int(x), P.n), target_twoB=twoB)
                    why["unknown"] += int(v)          # decodes but not via the table: never expected
                except Reject as exc:
                    why[str(exc)] = why.get(str(exc), 0) + int(v)
    return acc, rej, why


def roundtrip_check(P: Physics, accepted: dict) -> dict:
    """P6: every accepted basis index re-encodes to the string it was decoded from (0 mismatches)."""
    from skqd.reference_sim import bits_to_int
    bad = 0
    for i in accepted:
        if bits_to_int(P.codec.encode(P.M.basis.labels[int(i)])) != int(P.emb.ints[int(i)]):
            bad += 1
    return {"accepted_states": len(accepted), "mismatches": bad, "ok": bad == 0}


def chunk_matrix(P: Physics, circ_result: dict, twoB: int):
    """Per-chunk decoded counts as an int array [n_chunks x sector_dim] over the sector's full-basis
    indices (Sector.sector_idx order), plus rejected counts per chunk."""
    S = P.sector(twoB)
    pos = {int(b): j for j, b in enumerate(S.sector_idx)}
    mat = np.zeros((len(circ_result["chunks"]), len(S.sector_idx)), dtype=np.int32)
    rej = np.zeros(len(circ_result["chunks"]), dtype=np.int64)
    for c, ch in enumerate(circ_result["chunks"]):
        acc, r, _ = decode_counts(P, ch["counts"], twoB)
        for i, v in acc.items():
            mat[c, pos[i]] += v
        rej[c] = r
    return mat, rej


class Prefixes:
    """Chunk bookkeeping of one sector's circuits: exact prefix sums."""

    def __init__(self, P: Physics, twoB: int, results: list):
        self.P, self.twoB = P, twoB
        self.S = P.sector(twoB)
        self.ids = [r["label"] for r in results]
        self.mats, self.rej, self.bounds, self.done = {}, {}, {}, {}
        for r in results:
            m, rj = chunk_matrix(P, r, twoB)
            self.mats[r["label"]], self.rej[r["label"]] = m, rj
            ends = np.cumsum([ch["shots"] for ch in r["chunks"]]).tolist()
            self.bounds[r["label"]] = [0] + [int(e) for e in ends]
            self.done[r["label"]] = int(r["shots_done"])

    def covered(self, cid, L):
        return int(L) in self.bounds[cid]

    def counts(self, lengths: dict):
        """n_full (M.basis.dim) and the shot total for prefix lengths {cid: L} (chunk boundaries)."""
        n = np.zeros(self.P.M.basis.dim, dtype=np.int64)
        shots = 0
        idx = np.asarray(self.S.sector_idx)
        for c, L in lengths.items():
            b = self.bounds[c]
            if int(L) not in b:
                raise ValueError(f"{c}: prefix {L} is not a chunk boundary {b[:8]}...")
            k = b.index(int(L))
            if k:
                n[idx] += self.mats[c][:k].sum(axis=0)
            shots += int(L)
        return n, shots

    def accepted_rejected(self, lengths: dict):
        acc = rej = 0
        for c, L in lengths.items():
            k = self.bounds[c].index(int(L))
            acc += int(self.mats[c][:k].sum())
            rej += int(self.rej[c][:k].sum())
        return acc, rej


# --------------------------------------------------------------------------- the clean-fraction cell
def r_nc():
    d = load_json(R_NC_JSON)
    return float(d["r_nc"]), [float(x) for x in d["pooled_r_ci95"]]


def fcell_stats(P: Physics, per_circuit: dict, manifests: dict, kappa: float = 1.0, f0: dict = None) -> dict:
    """f-cell outputs (prompts/33 1.3 / 2.1) from {cid: {state int: n}} with manifests {cid: manifest}:
    pooled f_hit over the k = 1 circuits (Garwood 95 %), f_hat_ideal = f_hit / r_nc, per-circuit accepted
    fraction (Wilson 95 %), reference hits, f0 analytic (given), GO rule v3 (information)."""
    from . import stats as ST
    rnc, rnc95 = r_nc()
    rows, per = [], {}
    for cid, counts in per_circuit.items():
        m = manifests[cid]
        twoB = int(m["twoB"])
        S = P.sector(twoB)
        N = int(sum(counts.values()))
        acc, rej, _ = decode_counts(P, counts, twoB)
        hits = int(counts.get(int(m["reference_int"]), 0))
        a_cnt = int(sum(acc.values()))
        lo, hi = ST.wilson(a_cnt, N)
        per[cid] = {"shots": N, "accepted": a_cnt, "accepted_fraction": a_cnt / N if N else None,
                    "accepted_fraction_wilson95": [lo, hi], "reference_hits": hits,
                    "p_reference": float(m["p_reference_exact"]), "garbage_acceptance": S.a, "dim": S.dim,
                    "distinct_accepted": len(acc), "rejected": rej,
                    "f0": None if f0 is None else f0.get(cid)}
        single = ST.f_hit_cell([(hits, N, float(m["p_reference_exact"]), S.a, S.dim)], kappa=kappa)
        per[cid]["f_hit"], per[cid]["f_hit_ci95"] = single["f_hit"], single["f_hit_ci"]
        if int(m["k"]) == 1:
            rows.append((hits, N, float(m["p_reference_exact"]), S.a, S.dim))
    pooled = ST.f_hit_cell(rows, kappa=kappa, r_nc=rnc, r_nc_95=rnc95) if rows else None
    go = None
    if pooled and pooled["f_hit"] is not None:
        import sys
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        from gate_Q0P_2x3 import go_rule_v3
        go = go_rule_v3(pooled["f_hat_ideal"], pooled["f_hat_ideal_ci"][0], pooled["f_hat_ideal_ci"][1])
    return {"per_circuit": per, "pooled_k1": pooled, "go_rule_v3_information": go,
            "r_nc_source": "data/cf_trajectories/r_nc.json", "kappa": kappa}


# --------------------------------------------------------------------------- SKQD points and CV
def e_tol(P: Physics, sec: str) -> dict:
    """E_tol recomputed (h1_energy_tolerance, as gate_CV.chunk_2x3) and asserted against
    validation/CV_2x3_plan.json data.E_tol to 1e-12."""
    from skqd.skqd import h1_energy_tolerance
    S = P.S[sec]
    v = h1_energy_tolerance(S.H, S.prob, S.refs, 0.8, 1e-3, sector_idx=S.sector_idx, E0=S.E0)["E_tol"]
    ref = float(load_json(CV_PLAN_JSON)["data"]["E_tol"][sec]["value"])
    return {"value": float(v), "cv_2x3_plan": ref, "abs_diff": abs(float(v) - ref),
            "ok": abs(float(v) - ref) <= E_TOL_ASSERT}


def skqd_point(P: Physics, sec: str, n_full, shots, with_random=False) -> dict:
    """gate CV's Sector.point on B_all (references + every accepted state)."""
    S = P.S[sec]
    p = S.point(n_full, shots, with_random=with_random, crit="all", random_other=False)
    out = {k: v for k, v in p.items() if not k.startswith("_") and k != "B_sig_list"}
    out["B_all_list"] = [int(x) for x in p["_B_all"]]
    return out


def certificate_reading(sec: str, pt: dict) -> dict:
    """prompts/31 ruling 2: Kato-Temple (exact E1) at B=0, Weinstein at B=1; variational check."""
    a = pt["all"]
    if sec == "B=0":
        inside = a["E0_in_kt"]
        cert = {"type": "kato_temple_exact_E1", "interval": a["kt_rigorous"], "width": a["kt_width"]}
    else:
        inside = a["E0_in_weinstein"]
        cert = {"type": "weinstein", "interval": a["weinstein"], "width": a["rH"]}
    cert.update({"E0_inside": bool(inside) if inside is not None else False,
                 "variational_ok": bool(a["err"] >= -TOL_VAR), "E_R_minus_E0": a["err"],
                 "recall_S999": a["recall_S999"], "recall_S99": a["recall_S99"], "W": a["W"],
                 "B_all_size": pt["B_all_size"]})
    return cert


def cv_reading(P: Physics, sec: str, prefixes: Prefixes, plan: dict, E_tol: float, eq=None,
               with_random=True) -> dict:
    """CV0-CV5 on the order-kept chunks (gate_CV.run_seed's shots curve at the plan; CV3 only when the
    equal-shots k <= 4 and k = 5 prefixes are given: eq = (Prefixes_eq, N_eq, Prefixes_k5))."""
    CV = P.CV
    S = P.S[sec]
    ids = [c for c in plan]
    pts, prev_n, prev_B = [], None, None
    mono = {"B_all_nested": True, "counts_nondecreasing": True, "E_R_all_nonincreasing": True}
    for phi in CV.PHI:
        L = {c: CV.rnd(phi * plan[c]) for c in ids}
        n, sh = prefixes.counts(L)
        p = S.point(n, sh, with_random=with_random, crit="all", random_other=False)
        p["phi"] = phi
        if prev_n is not None:
            mono["counts_nondecreasing"] &= bool(np.all(n >= prev_n))
            mono["B_all_nested"] &= set(prev_B).issubset(set(p["_B_all"]))
            mono["E_R_all_nonincreasing"] &= bool(p["all"]["E_R"] <= pts[-1]["all"]["E_R"] + TOL_MONO)
        prev_n, prev_B = n, p["_B_all"]
        pts.append(p)
    var_ok = all(p["all"]["E_R"] >= S.E0 - TOL_VAR for p in pts)
    cv0 = dict(mono, variational_ok=var_ok)
    cv0["ok"] = bool(all(mono.values()) and var_ok)
    k_step, cv3_reason = None, None
    if eq is not None:
        pe, N_eq, pk5 = eq
        n4, s4 = pe.counts({c: N_eq for c in pe.ids})
        n5, s5 = pk5.counts({c: N_eq for c in pk5.ids})
        p4 = S.point(n4, s4, with_random=False, crit="all")
        p5 = S.point(n4 + n5, s4 + s5, with_random=False, crit="all")
        k_step = (p4, p5)
    else:
        cv3_reason = "not_evaluated: the equal-shots k <= 4 and k = 5 samples were not taken (budget)"
    crit = CV.evaluate(S, pts[3], pts[4], pts, [], E_tol, "all", k_step=k_step) if with_random else None
    if crit is None:
        crit = {"CV1": {"dE": pts[3]["all"]["E_R"] - pts[4]["all"]["E_R"],
                        "ok": bool(pts[3]["all"]["E_R"] - pts[4]["all"]["E_R"] <= E_tol)},
                "CV2": CV.cv2_block(S, pts[3], pts[4], "all"),
                "CV3": CV.cv3_block(S, k_step[0], k_step[1], E_tol, "all") if k_step else None,
                "CV4": {"ok": None, "note": "random baselines not computed"},
                "CV5": {"W_at_N": pts[4]["all"]["W"], "ok": bool(pts[4]["all"]["W"] >= CV.W_TARGET)}}
    if "CV3" not in crit or crit.get("CV3") is None:
        crit["CV3"] = {"ok": None, "status": cv3_reason}
    strip = [{k: v for k, v in p.items() if not k.startswith("_") and k != "B_sig_list"} for p in pts]
    return {"cv0": cv0, "criteria": crit, "shots_curve": strip}


def bootstrap_point(P: Physics, sec: str, per_circuit_counts: list, B: int, seed: int = 33) -> dict:
    """2000 resamples over shots within each circuit (prompts/33 2.2): E_R - E0, recall S999, W."""
    S = P.S[sec]
    from skqd.skqd import ritz, support_metrics
    rng = np.random.default_rng(seed)
    keys = [np.asarray(list(c.keys()), dtype=np.int64) for c in per_circuit_counts]
    vals = [np.asarray(list(c.values()), dtype=float) for c in per_circuit_counts]
    res = {"err": [], "recall_S999": [], "W": []}
    refs = set(S.refs)
    for _ in range(int(B)):
        seen = set(refs)
        for k, v in zip(keys, vals):
            n = int(v.sum())
            if n == 0:
                continue
            d = rng.multinomial(n, v / n)
            seen.update(int(x) for x in k[d > 0])
        Bv = np.asarray(sorted(seen), dtype=int)
        r = ritz(S.H, Bv)
        m = support_metrics(Bv, S.prob, 1e-3)
        res["err"].append(float(r.ER - S.E0))
        res["recall_S999"].append(float(m["recall"]))
        res["W"].append(float(m["captured_weight"]))
    out = {}
    for k, v in res.items():
        v = np.asarray(v)
        out[k] = {"ci95": [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if len(v) else None,
                  "mean": float(v.mean()) if len(v) else None}
    out.update({"B": int(B), "seed": int(seed), "scheme": "shots resampled within each circuit (multinomial)"})
    return out
