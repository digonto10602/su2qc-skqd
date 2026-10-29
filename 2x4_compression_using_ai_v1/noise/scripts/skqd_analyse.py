"""Noisy SKQD campaign: the full SKQD pipeline on the noisy samples of one (lattice, family, device), side by side
with ideal (noiseless) samples of the same size.

Usage: python skqd_analyse.py LATTICE FAMILY DEVICE [--bootstrap B] [--allow-partial]
Writes <lattice results>/<FAMILY>/<DEVICE>/noisy_skqd.json (results.py test 'noisy_skqd').

Machinery reused, not reimplemented (src/skqd/campaign33/analysis.py, scripts/gate_CV.py):
  decoding          the codeword table of analysis.Physics (identical to skqd.codec.Codec.decode with target_twoB);
                    the decoder round trip (analysis.roundtrip_check) on every accepted state
  plan point        analysis.skqd_point on B_all = references + every accepted state, analysis.certificate_reading
                    (Kato-Temple with the exact E1 at B=0, Weinstein at B=1; E_R >= E0 - 1e-9)
  CV0-CV5           analysis.cv_reading: prefixes phi N_c (phi = 1/16 .. 1) of the order-kept sequences, CV3 at equal
                    shots N_eq per circuit (k <= 4 vs k <= 5), CV4 against 200 random bases, CV5 W >= 0.99
  E_tol             analysis.e_tol (asserted against validation/CV_2x{3,4}_plan.json; 2x2 recomputed)
  bootstrap         analysis.bootstrap_point (shots resampled within each circuit)
Plan: notes/campaign_budget.json (per-circuit plan shots N_c, N_eq per sector, shots sampled).
Noise quantities per circuit (as scripts/noisy_run.py): acceptance, f_hit = (reference hits / shots) / p_ref,
b_all(1e-3) = fraction of trajectories with TV_pre < 1e-3, f_ideal = readout survival of the reference x b_all,
r_nc = f_hit / f_ideal, f_model = f_gate (1 - mean readout error)^n.
"""
import os as _os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import glob
import json
import math
import os
import sys
import time
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NOISE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(NOISE, "src"))
import campaign as C  # noqa: E402
import targets  # noqa: E402
from circuits import ROOT  # noqa: E402
from provenance import provenance, dump  # noqa: E402
from results import lattice_results  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from skqd.campaign33 import analysis as A  # noqa: E402

SECTORS = (("B=0", 0), ("B=1", 2))


def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]


# --------------------------------------------------------------------------- loading
def load_sequence(lat, fam, dev, cid):
    """Concatenate the chunks of one circuit in chunk order; the chunks must tile [0, N) without gap."""
    files = sorted(glob.glob(os.path.join(C.sample_dir(lat, fam, dev, cid), "c[0-9][0-9][0-9].npz")))
    arrs = {k: [] for k in ("post", "nf", "tv_pre", "w", "p_ref")}
    metas, pos = [], 0
    for f in files:
        m = json.load(open(f[:-4] + ".json"))
        if int(m["start"]) != pos:
            raise ValueError(f"{cid}: chunk {m['chunk']} starts at {m['start']}, expected {pos}")
        z = np.load(f)
        for k in arrs:
            arrs[k].append(z[k])
        pos += int(m["shots"])
        metas.append(m)
    out = {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in arrs.items()}
    out["post"] = out["post"].astype(np.int64)
    return out, metas


def decode_seq(P, post, twoB):
    """Full-basis index per shot (-1 = rejected), via analysis.decode_counts on the unique strings."""
    if len(post) == 0:
        return np.zeros(0, dtype=np.int64)
    u, inv = np.unique(post, return_inverse=True)
    acc, _rej, _ = A.decode_counts(P, {int(x): 1 for x in u}, twoB)
    lut = np.full(len(u), -1, dtype=np.int64)
    pos = {int(x): j for j, x in enumerate(u)}
    for i in acc:
        lut[pos[int(P.emb.ints[int(i)])]] = int(i)
    return lut[inv]


def rows_of(dec, bounds):
    """Decoded sequence -> chunk rows {start, shots, accepted, rejected} split at the sorted boundaries."""
    rows = []
    b = sorted(set(int(x) for x in bounds if 0 < int(x) <= len(dec)) | {len(dec)})
    s = 0
    for e in b:
        seg = dec[s:e]
        ok = seg[seg >= 0]
        u, c = np.unique(ok, return_counts=True)
        rows.append({"start": s, "shots": int(e - s), "accepted": {int(x): int(n) for x, n in zip(u, c)},
                     "rejected": int((seg < 0).sum())})
        s = e
    return rows


def boundaries(N_plan, N_eq, total, k):
    import gate_CV as CV
    if k == 5:
        return [N_eq, total]
    return [CV.rnd(phi * N_plan) for phi in CV.PHI] + [N_plan, N_eq, total]


# --------------------------------------------------------------------------- one sector, one sample set
def skqd_sector(P, sec, twoB, seqs, ks, plan, N_eq, E_tol, bootstrap=0, with_random=True):
    """seqs {cid: decoded sequence}; ks {cid: k}; plan {cid: N_c} (k <= 4).  Returns the plan point, the
    all-shots point, the certificate, CV0-CV5 and (optionally) the bootstrap."""
    ids4 = sorted(c for c in seqs if ks[c] <= 4)
    ids5 = sorted(c for c in seqs if ks[c] == 5)
    short = [c for c in ids4 if len(seqs[c]) < max(plan[c], N_eq)] + [c for c in ids5 if len(seqs[c]) < N_eq]
    if short:
        raise ValueError(f"{sec}: sequences shorter than the plan / N_eq: {short[:6]}")
    ch4 = {c: rows_of(seqs[c], boundaries(plan[c], N_eq, len(seqs[c]), ks[c])) for c in ids4}
    pre = A.Prefixes.from_chunks(P, twoB, ch4)
    n, sh = pre.counts({c: plan[c] for c in ids4})
    pt = A.skqd_point(P, sec, n, sh, with_random=False)
    cert = A.certificate_reading(sec, pt)
    nA, shA = pre.counts({c: len(seqs[c]) for c in ids4})
    ptA = A.skqd_point(P, sec, nA, shA, with_random=False)
    certA = A.certificate_reading(sec, ptA)
    eq = None
    if ids5:
        pk5 = A.Prefixes.from_chunks(P, twoB, {c: rows_of(seqs[c], boundaries(None, N_eq, len(seqs[c]), 5))
                                              for c in ids5})
        eq = (pre, N_eq, pk5)
    cv = A.cv_reading(P, sec, pre, {c: plan[c] for c in ids4}, E_tol, eq=eq, with_random=with_random,
                      k_of={c: ks[c] for c in ids4})
    S = P.S[sec]
    acc_states = np.flatnonzero(n > 0)
    out = {"plan_shots": int(sh), "all_shots": int(shA), "circuits_k4": len(ids4), "circuits_k5": len(ids5),
           "N_eq": int(N_eq), "plan_point": cert, "plan_point_full": {k: v for k, v in pt.items() if k != "B_all_list"},
           "all_shots_point": certA,
           "accepted_distinct_plan": int(len(acc_states)),
           "accepted_outside_S999_plan": int(len(set(int(x) for x in acc_states) - set(int(x) for x in S.S999))),
           "cv": cv}
    if bootstrap:
        per = [{int(i): int(v) for i, v in rows_to_counts(ch4[c], plan[c]).items()} for c in ids4]
        out["bootstrap_plan_point"] = A.bootstrap_point(P, sec, per, bootstrap)
    return out


def rows_to_counts(rows, L):
    cnt = {}
    for r in rows:
        if r["start"] + r["shots"] > L:
            break
        for i, v in r["accepted"].items():
            cnt[i] = cnt.get(i, 0) + v
    return cnt


def outside_ideal_support(P, sec, twoB, seqs, ks, plan, lat):
    """Accepted distinct states (plan point) whose ideal probability is < 1e-30 in every circuit of the sector:
    states that only noise can produce."""
    Lx = int(lat.split("x")[1])
    reach = np.zeros(P.M.basis.dim)
    for c in seqs:
        tb, ref, k = C.parse(c)
        reach += np.abs(targets.target(Lx, tb, ref, k)) ** 2
    acc = set()
    for c in seqs:
        if ks[c] <= 4:
            d = seqs[c][:plan[c]]
            acc.update(int(x) for x in np.unique(d[d >= 0]))
    bad = [i for i in acc if reach[i] < 1e-30]
    return {"accepted_distinct": len(acc), "outside_ideal_support": len(bad)}


# --------------------------------------------------------------------------- noise quantities
def noise_block(P, twoB, seq, metas, dec):
    m0 = metas[0]
    n = int(m0["n_qubits"])
    p10, p01 = m0["readout_p10_p01"]
    ref_int, p_ref = int(m0["reference_int"]), float(m0["p_ref"])
    N = len(seq["post"])
    hits = int((seq["post"] == ref_int).sum())
    acc = int((dec >= 0).sum())
    rb = [(ref_int >> q) & 1 for q in range(n)]
    rho = float(np.prod([(1 - p01) if b else (1 - p10) for b in rb]))
    b1 = float(np.mean(seq["tv_pre"] < 1e-3)) if N else None
    f_ideal = rho * b1 if b1 is not None else None
    f_hit = hits / N / p_ref if N else None
    return {"shots": N, "accepted": acc, "acceptance": acc / N if N else None, "acceptance_ci95": wilson(acc, N),
            "acceptance_random_level": m0["sector_size"] / 2 ** n,
            "ref_hits": hits, "p_ref": p_ref, "f_hit": f_hit, "f_hit_ci95": [None if x is None else x / p_ref
                                                                              for x in wilson(hits, N)],
            "b_all_1e-3": b1, "readout_survival_ref": rho, "f_ideal_1e-3": f_ideal,
            "r_nc": (f_hit / f_ideal) if (f_ideal and f_ideal > 0) else None,
            "f_gate": float(m0["f_gate"]), "f_model": float(m0["f_gate"]) * (1 - 0.5 * (p10 + p01)) ** n,
            "fault_free_fraction": float(np.mean(seq["nf"] == 0)) if N else None,
            "mean_sector_weight_pre_readout": float(np.mean(seq["w"])) if N else None,
            "clean_state_max_abs_dpsi": max(m["clean_state_max_abs_dpsi"] for m in metas),
            "clean_state_leakage": max(m["clean_state_leakage"] for m in metas),
            "prune_bound_max": max(m["prune_bound_max"] for m in metas),
            "seconds_per_shot": float(sum(m["timing_s"]["simulate"] for m in metas) / max(N, 1)),
            "chunks": len(metas), "seeds_simulator": [m["seed_simulator"] for m in metas],
            "noise_spec_sha256": m0["noise_spec_sha256"], "source_family": m0["source_family"]}


def pooled(rows, only_k=None):
    sel = [r for r in rows if only_k is None or r["k"] == only_k]
    N = sum(r["shots"] for r in sel)
    if not N:
        return None
    hits = sum(r["ref_hits"] for r in sel)
    exp_ref = sum(r["shots"] * r["p_ref"] for r in sel)
    acc = sum(r["accepted"] for r in sel)
    fi = sum(r["shots"] * r["f_ideal_1e-3"] for r in sel) / N
    fh = hits / exp_ref
    return {"circuits": len(sel), "shots": N, "acceptance": acc / N, "acceptance_ci95": wilson(acc, N),
            "f_hit": fh, "f_ideal_1e-3": fi, "r_nc": fh / fi if fi > 0 else None,
            "f_model_mean": float(np.mean([r["f_model"] for r in sel])),
            "f_gate_mean": float(np.mean([r["f_gate"] for r in sel])),
            "fault_free_fraction": sum(r["fault_free_fraction"] * r["shots"] for r in sel) / N}


# --------------------------------------------------------------------------- main
def ideal_sequence(lat, fam, dev, cid, N):
    """N ideal (noiseless, no readout error) samples of the circuit's exact target, decoded = sector indices."""
    Lx = int(lat.split("x")[1])
    tb, ref, k = C.parse(cid)
    sector = targets.sector(Lx, tb)
    p = np.abs(targets.target(Lx, tb, ref, k)[sector]) ** 2
    seed = zlib.crc32(f"{lat}|{fam}|{dev}|{cid}|ideal".encode()) % 2 ** 31
    rng = np.random.default_rng(seed)
    return sector[rng.choice(len(sector), size=int(N), p=p / p.sum())].astype(np.int64), seed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lattice"); ap.add_argument("family"); ap.add_argument("device")
    ap.add_argument("--bootstrap", type=int, default=200)
    ap.add_argument("--no-random", action="store_true", help="skip the 200 random bases of CV4 (quick checks)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    t0 = time.time()
    lat, fam, dev = a.lattice, a.family, a.device
    Lx = int(lat.split("x")[1])
    bud = C.load_budget()
    entry = bud["plans"][lat][fam][dev]
    P = A.Physics(lat=Lx)
    out = {"lattice": lat, "family": fam, "device": dev, "budget_entry": entry, "sectors": {}, "ideal": {},
           "noise": {}, "noise_pooled": {}}
    for sec, tb in SECTORS:
        e = entry[sec]
        plan, N_eq = {c: int(v) for c, v in e["plan"].items()}, int(e["N_eq"])
        cids = sorted(e["sampled"])
        ks = {c: C.parse(c)[2] for c in cids}
        seqs, rows, seq_ideal, ideal_seeds = {}, [], {}, {}
        rt_bad = 0
        for c in cids:
            seq, metas = load_sequence(lat, fam, dev, c)
            if len(seq["post"]) < int(e["sampled"][c]):
                raise ValueError(f"{c}: {len(seq['post'])} shots on disk < {e['sampled'][c]} planned")
            seq = {k: v[:int(e["sampled"][c])] for k, v in seq.items()}
            dec = decode_seq(P, seq["post"], tb)
            seqs[c] = dec
            r = noise_block(P, tb, seq, metas, dec)
            r["k"] = ks[c]
            rows.append(dict(r, circuit=c))
            rt = A.roundtrip_check(P, {int(i): 1 for i in np.unique(dec[dec >= 0])})
            rt_bad += rt["mismatches"]
            seq_ideal[c], ideal_seeds[c] = ideal_sequence(lat, fam, dev, c, len(dec))
        et = A.e_tol(P, sec)
        res = skqd_sector(P, sec, tb, seqs, ks, plan, N_eq, et["value"], bootstrap=a.bootstrap,
                          with_random=not a.no_random)
        res["E_tol"] = et
        res["decoder_roundtrip_mismatches"] = rt_bad
        res["support_check"] = outside_ideal_support(P, sec, tb, seqs, ks, plan, lat)
        out["sectors"][sec] = res
        ri = skqd_sector(P, sec, tb, seq_ideal, ks, plan, N_eq, et["value"], bootstrap=a.bootstrap,
                         with_random=not a.no_random)
        ri["seeds"] = ideal_seeds
        out["ideal"][sec] = ri
        out["noise"][sec] = {r["circuit"]: r for r in rows}
        out["noise_pooled"][sec] = {"all": pooled(rows), "k1": pooled(rows, 1)}
        print(sec, "noisy", {k: res["plan_point"][k] for k in ("E_R_minus_E0", "width", "E0_inside", "recall_S999", "W",
                                                               "B_all_size")},
              "ideal", {k: ri["plan_point"][k] for k in ("E_R_minus_E0", "width", "E0_inside", "recall_S999")},
              f"{time.time() - t0:.0f}s", flush=True)
    out["summary"] = summary_rows(out)
    out["runtime_s"] = time.time() - t0
    out["provenance"] = provenance(engine="noise/src/traj_sparse.py (sparse Pauli trajectories)",
                                   noise_spec_sha256=next(iter(next(iter(out["noise"].values())).values()))[
                                       "noise_spec_sha256"])
    path = a.out or os.path.join(lattice_results(lat), fam, dev, "noisy_skqd.json")
    dump(out, path)
    print("wrote", path)


def summary_rows(out):
    S = {}
    for sec in out["sectors"]:
        r, i, pl = out["sectors"][sec], out["ideal"][sec], out["noise_pooled"][sec]["all"]
        crit = r["cv"]["criteria"]
        S[sec] = {"plan_shots": r["plan_shots"], "all_shots": r["all_shots"],
                  "acceptance": pl["acceptance"], "f_hit": pl["f_hit"], "r_nc": pl["r_nc"],
                  "f_hit_k1": (out["noise_pooled"][sec]["k1"] or {}).get("f_hit"),
                  "r_nc_k1": (out["noise_pooled"][sec]["k1"] or {}).get("r_nc"),
                  "E_R_minus_E0": r["plan_point"]["E_R_minus_E0"], "width": r["plan_point"]["width"],
                  "certificate": r["plan_point"]["type"], "E0_inside": r["plan_point"]["E0_inside"],
                  "recall_S999": r["plan_point"]["recall_S999"], "W": r["plan_point"]["W"],
                  "B_all_size": r["plan_point"]["B_all_size"],
                  "CV": {k: (crit.get(k) or {}).get("ok") for k in ("CV1", "CV2", "CV3", "CV4", "CV5")},
                  "CV0_ok": r["cv"]["cv0"]["ok"],
                  "ideal_E_R_minus_E0": i["plan_point"]["E_R_minus_E0"], "ideal_width": i["plan_point"]["width"],
                  "ideal_E0_inside": i["plan_point"]["E0_inside"], "ideal_recall_S999": i["plan_point"]["recall_S999"],
                  "ideal_W": i["plan_point"]["W"], "ideal_B_all_size": i["plan_point"]["B_all_size"],
                  "ideal_CV": {k: (i["cv"]["criteria"].get(k) or {}).get("ok") for k in ("CV1", "CV2", "CV3", "CV4", "CV5")},
                  "outside_ideal_support": r["support_check"]["outside_ideal_support"]}
    return S


if __name__ == "__main__":
    main()
