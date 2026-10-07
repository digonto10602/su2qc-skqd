"""
The 33 token jobs of prompts/33 (section 1.5), called by scripts/campaign33.py with its Ctx.

run_ideal (C1_IDEAL, C3_AER), run_c2_cal, run_c2_cell (C2_GATE/ECHO/STAR/XY4/COH), run_c3_engine
(C3_LE, C3_SEL), run_fcells (C4_FCELLS_A/B), run_frun (C4_F1..F8), run_cf (C4_CF), write_exact_data.
Criteria numbering follows prompts/33 section 5 (S1-S6 are added by campaign33.finish).
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np

from . import analysis as A
from . import circuits as C
from . import noise as N
from . import sampling as SM
from . import stats as ST
from . import tokens as TK

ROOT = A.ROOT
G2 = 4.0
RECORD = os.path.join(ROOT, "data", "hardware", "K0_prep", "ibm_kingston_full_20261006T0652Z.json")
EXACT_DIR = os.path.join(ROOT, "data", "campaign33", "exact")
FCELL_SHOTS = {"B0_ref25_k1": 800, "B1_ref57_k1": 800, "B0_ref25_k4": 200, "B1_ref57_k4": 200}
K1_IDS = ("B0_ref117_k1", "B1_ref29_k1")
S3_RECALL_MIN, S3_EPS = 0.9, 1e-3
PRODUCTION_SHOTS_PER_SECTOR = 200000
TIERS = (0.05, 0.10, 0.15)


def load_json(p):
    with open(p if os.path.isabs(p) else os.path.join(ROOT, p)) as fh:
        return json.load(fh)


def jdump(path, obj):
    from skqd.report import _jsonable
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(_jsonable(obj), fh, indent=1)


def validation_path(ctx, token):
    """The JSON of another token: validation/dryrun/<T>.json in a dry run, else validation/<T>.json."""
    return os.path.join(ROOT, "validation", "dryrun" if ctx.dry else "", token + ".json")


# =========================================================================== circuits and exact states
def sector_of(cid):
    return 0 if cid.startswith("B0") else 2


def select_ids(ctx, ids, prefer=()):
    """All ids, or in a dry run at most --max-circuits per sector (the preferred ids first)."""
    m = int(ctx.args.max_circuits or 0)
    if m <= 0:
        return list(ids)
    out = []
    for sec in ("B0", "B1"):
        sid = [c for c in prefer if c in ids and c.startswith(sec)] + \
              [c for c in ids if c.startswith(sec) and c not in prefer]
        out += sid[:m]
    if len(out) < len(ids):
        ctx.notes.append(f"dry run: {len(out)} of {len(ids)} circuits used ({sorted(out)})")
    return out


def load_family(ids, family):
    return {cid: (C.load_circuit(family, cid), C.load_manifest(family, cid)) for cid in ids}


_EXACT = {}


def exact_state(P, twoB, ref, k, dt):
    """exp(-i k dt H_gamma)... |ref> in the signed group order (skqd.krylov.coarse_states), cached."""
    key = (twoB, int(ref), int(k), float(dt))
    if key not in _EXACT:
        from skqd.exact import mass_default
        from skqd.krylov import basis_vector, coarse_states, term_groups
        if "groups" not in _EXACT:
            _EXACT["groups"] = term_groups(P.M.terms, G2, mass_default(G2))
        st = coarse_states(_EXACT["groups"], basis_vector(P.M.basis.dim, int(ref)), float(dt), int(k))
        _EXACT[key] = st[int(k)]
    return _EXACT[key]


def exact_probs(P, psi_gauge) -> dict:
    """{codeword int: |amp|^2} of an exact state (full gauge basis -> qubit strings)."""
    p = np.abs(psi_gauge) ** 2
    return {int(P.emb.ints[i]): float(p[i]) for i in np.flatnonzero(p > 0)}


def cv_plan(f, sec):
    d = load_json(A.CV_PLAN_JSON)["data"]["plan"][f"f={f:.2f}"][sec]
    return {c: int(v) for c, v in d["final_shots_by_circuit"].items()}, d


def plan_tier(ctx, scenario, fixed=None):
    """prompts/33 1.3: the largest f in {0.05, 0.10, 0.15} not above the f-cell's lower 95 % end of
    f_hat_ideal for the scenario (C4_FCELLS_A/B), default 0.15 when that JSON is absent."""
    if fixed is not None:
        return fixed, f"fixed by design (prompts/33 1.5: F5 at the f = {fixed:.2f} plan)"
    for tok in ("C4_FCELLS_A", "C4_FCELLS_B"):
        p = validation_path(ctx, tok)
        if os.path.exists(p):
            tiers = load_json(p)["data"].get("plan_tiers", {})
            if scenario in tiers and tiers[scenario].get("tier") is not None:
                t = tiers[scenario]
                return float(t["tier"]), f"{os.path.relpath(p, ROOT)} plan_tiers.{scenario}: {t['reason']}"
    return 0.15, (f"default 0.15: no f-cell result for {scenario} in validation/C4_FCELLS_A.json or "
                  "C4_FCELLS_B.json at run time")


# =========================================================================== shared sampling helpers
def gpu_mode_for(ctx, cal_token=None, rep=None):
    """--gpu-mode, else the calibration's fastest mode, else the policy combination."""
    if ctx.args.gpu_mode != "auto":
        return ctx.args.gpu_mode, "--gpu-mode"
    if ctx.device != "GPU":
        return "cpu", "CPU run"
    if cal_token:
        p = validation_path(ctx, cal_token)
        if os.path.exists(p):
            dec = load_json(p)["data"].get("decision", {})
            m = dec.get("mode_by_representation", {}).get(rep) if rep else dec.get("mode")
            if m:
                return m, f"{os.path.relpath(p, ROOT)} decision"
    return "policy", "RUNBOOK policy (no calibration result at run time)"


def simulator(ctx, noise_model, mode):
    sim, kw = SM.make_simulator("GPU" if ctx.device == "GPU" else "CPU", mode if ctx.device == "GPU" else "policy",
                                noise_model, threads=ctx.args.threads)
    return sim, kw


C2_CHUNK = 4096        # class 2: a 21-qubit circuit with ~5600 delays has a large per-call set-up (laptop CPU, idle,
#                       12 threads, I-ECHO on IBM-T0: PTA 1 shot 48.4 s / 8 shots 217.2 s; Kraus 154.5 s / 635.8 s;
#                       under load PTA 1 shot 359 s / 4 shots 418 s); no prefix curve is read in class 2, so its
#                       chunks are as large as memory allows (cuStateVec: one 21-qubit state per shot).


def sample(ctx, sim, circuits, shots, labels, circuit_offset=0, share=0.75, deadline=None, rate_hint=None,
           max_chunk=None):
    s = SM.Sampler(sim, ctx.s0, int(max_chunk or SM_chunk(ctx)),
                   deadline if deadline is not None else ctx.sampling_deadline(share), log=ctx.log, rate_hint=rate_hint,
                   min_rounds=1 if ctx.dry else 0)
    res, info = s.run(circuits, shots, labels, circuit_offset)
    ctx.oom += info["oom_retries"]
    return res, info


def SM_chunk(ctx):
    return int(ctx.args.max_shots_per_run) if ctx.args.max_shots_per_run > 0 else 476


def totals(res):
    out = {}
    for ch in res["chunks"]:
        for k, v in ch["counts"].items():
            out[k] = out.get(k, 0) + v
    return out


def chunk_record(res):
    """Seeds and sizes of every chunk (S4), without the counts."""
    return [{"start": ch["start"], "shots": ch["shots"], "seed": ch["seed"]} for ch in res["chunks"]]


def save_npz(ctx, name, P, results, twoB_of):
    """results/campaign33/<TOKEN>/<name>.npz: per circuit the per-chunk decoded counts over the sector's
    full-basis indices, the rejected counts and the chunk seeds/sizes (compact; stays in the job dir)."""
    arrays = {}
    for r in results:
        tb = twoB_of(r["label"])
        mat, rej = A.chunk_matrix(P, r, tb)
        arrays[r["label"] + "__chunks"] = mat
        arrays[r["label"] + "__rejected"] = rej
        arrays[r["label"] + "__seeds"] = np.asarray([ch["seed"] for ch in r["chunks"]], dtype=np.int64)
        arrays[r["label"] + "__shots"] = np.asarray([ch["shots"] for ch in r["chunks"]], dtype=np.int64)
        acc = sorted(k for k in totals(r) if P.int_to_idx.get(int(k)) is not None)
        arrays[r["label"] + "__accepted_strings"] = np.asarray(acc, dtype=np.int64)
    for sec, tb in A.SECTORS:
        arrays["sector_idx_" + sec.replace("=", "")] = np.asarray(P.sector(tb).sector_idx) if P.S else np.zeros(0)
    path = os.path.join(ctx.results_dir, name + ".npz")
    np.savez_compressed(path, **arrays)
    return os.path.relpath(path, ROOT)


def sparse_accepted(P, counts, twoB):
    acc, rej, _ = A.decode_counts(P, counts, twoB)
    return {int(k): int(v) for k, v in sorted(acc.items())}, int(rej)


# =========================================================================== class 1 / C3_AER
def run_ideal(ctx):
    P = A.Physics()
    idx = C.load_index()
    c1 = ctx.token == "C1_IDEAL"
    main = "IR-L0" if c1 else "NAT-O0"
    fams = ["IR-L0", "NAT-O0", "IBM-U", "IBM-T0", "IBM-T3"] if c1 else ["NAT-O0"]
    ibm_fams = ("IBM-U", "IBM-T0", "IBM-T3")
    if ctx.dry and c1:            # 21-qubit statevectors cost ~30 s each on the laptop: one IBM family in a dry run
        fams = ["IR-L0", "NAT-O0", "IBM-T0"]
        ibm_fams = ("IBM-T0",)
        ctx.notes.append("dry run: the IBM exactness and per-state checks use IBM-T0 only (the CI runs U, T0, T3)")
    prefer = tuple(FCELL_SHOTS)
    ex_rows, exact_ok, t_ex = {}, {}, time.time()
    for fam in fams:
        ids = list(idx["families"][fam]["circuits"])
        ids = ids if fam.startswith("IBM") else select_ids(ctx, ids, prefer)
        rows = {}
        for cid in ids:
            circ, man = C.load_circuit(fam, cid), C.load_manifest(fam, cid)
            if fam.startswith("IBM"):
                import gate_K0_2x3_2x4 as K0
                ex = K0.exact_coarse(int(man["twoB"]), int(man["reference"]), int(man["k"]))
                r, _ = K0.circuit_exactness(circ, man["logical_to_physical"], ex, phase_align=True)
                e = {"max_abs_dpsi_up_to_phase": r["max_abs_delta_up_to_phase"], "leakage": r["leakage"],
                     "measurement_consistent": r["measurement_consistent"], "ok": r["ok"],
                     "engine": "gate_K0_2x3_2x4.circuit_exactness (Aer CPU, active qubits)"}
            else:
                psi = C.statevector(circ, threads=ctx.args.threads, device=ctx.device)
                ex = exact_state(P, int(man["twoB"]), int(man["reference"]), int(man["k"]), float(man["dt"]))
                e = C.exactness(psi, ex, P.emb, C.measure_map(circ) == {i: i for i in range(P.n)})
                e["engine"] = f"Aer statevector {ctx.device}"
            e["laptop_manifest_dpsi"] = man["exactness"]["max_abs_dpsi_up_to_phase"]
            rows[cid] = e
            ctx.log(f"exactness {fam} {cid}: {e['ok']} |dpsi| {e['max_abs_dpsi_up_to_phase']:.2e}")
        ex_rows[fam] = rows
        exact_ok[fam] = all(r["ok"] for r in rows.values())
    ctx.phases["exactness_s"] = time.time() - t_ex
    allowed = [f for f in fams if f in C.BASE_FAMILIES or f.startswith("IBM") or
               idx.get("variants", {}).get(f, {}).get("allowed")]
    worst = {f: max(r["max_abs_dpsi_up_to_phase"] for r in ex_rows[f].values()) for f in fams}
    leak = {f: max(r["leakage"] for r in ex_rows[f].values()) for f in fams}
    ctx.physics("P1 max |dpsi| < 1e-10 and leakage < 1e-9 on every circuit of every allowed family",
                {f: [worst[f], leak[f]] for f in allowed}, "< 1e-10 / < 1e-9", all(exact_ok[f] for f in allowed))
    ctx.data["exactness"] = {"families": fams, "per_circuit": ex_rows, "all_ok": exact_ok, "allowed_families": allowed}

    # ---- noiseless sampling of the main family (and a per-state sample of the IBM circuits in C1)
    t_s = time.time()
    plans, unif = {}, {}
    ids_main = select_ids(ctx, list(idx["families"][main]["circuits"]), prefer)
    for sec, tb in A.SECTORS:
        pl, _d = cv_plan(0.10, sec)
        sec_ids = [c for c in idx["families"][main]["circuits"] if sector_of(c) == tb]
        for c in sec_ids:
            if c in ids_main:
                plans[c] = ctx.scaled(pl[c])
                unif[c] = ctx.scaled(PRODUCTION_SHOTS_PER_SECTOR // len(sec_ids))
    sim, kw = SM.make_simulator(ctx.device, "custatevec" if ctx.device == "GPU" else "policy", None,
                                threads=ctx.args.threads)
    ctx.data["gpu_mode_used"] = "custatevec (noiseless)" if ctx.device == "GPU" else "cpu"
    seqs, p2, stage_e = {}, {}, {}
    for i, cid in enumerate(ids_main):
        circ, man = C.load_circuit(main, cid), C.load_manifest(main, cid)
        n = max(plans[cid], unif[cid])
        seed = TK.chunk_seed(ctx.s0, i, 0, n)
        mem = SM.sample_noiseless_memory(sim, circ, n, seed)
        ex = exact_state(P, int(man["twoB"]), int(man["reference"]), int(man["k"]), float(man["dt"]))
        cnt = {}
        for x in mem.tolist():
            cnt[x] = cnt.get(x, 0) + 1
        p2[cid] = ST.per_state_test(cnt, exact_probs(P, ex), n, 5.0, 1e-3)
        p2[cid]["seed"] = int(seed)
        dec = np.asarray([P.int_to_idx.get(int(x), -1) if P.sector_of.get(P.int_to_idx.get(int(x), -1)) == int(man["twoB"])
                          else -1 for x in mem.tolist()], dtype=np.int32)
        seqs[cid] = dec
        if cid in FCELL_SHOTS:
            stage_e[cid] = {str(k): int(v) for k, v in sorted(cnt.items())}
    if c1:
        for i, cid in enumerate(K1_IDS):
            for fam in ibm_fams:
                circ, man = C.load_circuit(fam, cid), C.load_manifest(fam, cid)
                n = ctx.scaled(10000)
                seed = TK.chunk_seed(ctx.s0, 900 + 3 * i + ("IBM-U", "IBM-T0", "IBM-T3").index(fam), 0, n)
                res = sim.run(circ, shots=n, seed_simulator=seed).result()
                cnt = SM.counts_to_int(res.get_counts(0))
                ex = exact_state(P, int(man["twoB"]), int(man["reference"]), int(man["k"]), float(man["dt"]))
                p2[f"{fam}:{cid}"] = ST.per_state_test(cnt, exact_probs(P, ex), n, 5.0, 1e-3)
                p2[f"{fam}:{cid}"]["seed"] = int(seed)
    ctx.phases["noiseless_sampling_s"] = time.time() - t_s
    tested = sum(v["tested_states"] for v in p2.values())
    maxz = max(v["max_z"] for v in p2.values())
    nfail = sum(len(v["failures"]) for v in p2.values())
    ctx.physics("P2 per-state 5 sigma test |n_s/N - p_s| <= 5 sqrt(p_s(1-p_s)/N), p_s >= 1e-3, every sampled circuit",
                {"circuits": len(p2), "states_tested": tested, "max_z": maxz, "failures": nfail},
                "0 failures (Bonferroni false-alarm < 1e-2 over <= 9000 states)", nfail == 0)
    ctx.data["noiseless"] = {"family": main, "per_state": p2, "plan_f010_shots": plans, "uniform_2e5_shots": unif,
                             "stage_e_counts": stage_e}

    # ---- the f = 1 SKQD reference per sector, at the f = 0.10 plan prefix and at the 2e5 uniform prefix
    t_a = time.time()
    ref = {}
    for sec, tb in A.SECTORS:
        sid = [c for c in ids_main if sector_of(c) == tb]
        out = {}
        for label, L in (("plan_f010", plans), ("uniform_2e5", unif)):
            n_full = np.zeros(P.M.basis.dim, dtype=np.int64)
            shots = 0
            for c in sid:
                x = seqs[c][:L[c]]
                x = x[x >= 0]
                if x.size:
                    n_full += np.bincount(x, minlength=P.M.basis.dim)
                shots += L[c]
            pt = A.skqd_point(P, sec, n_full, shots, with_random=False)
            out[label] = {"shots": shots, "point": {k: v for k, v in pt.items() if k != "B_all_list"},
                          "certificate": A.certificate_reading(sec, pt)}
        ref[sec] = out
    ctx.phases["analysis_s"] = time.time() - t_a
    rec_ok = all(ref[s]["plan_f010"]["certificate"]["recall_S999"] >= 0.9 for s in ref)
    in_ok = all(ref[s]["plan_f010"]["certificate"]["E0_inside"] for s in ref)
    var_ok = all(ref[s][lab]["certificate"]["variational_ok"] for s in ref for lab in ref[s])
    ctx.physics("P3 noiseless SKQD at the f = 0.10 plan: recall of S999 >= 0.9 in both sectors",
                {s: ref[s]["plan_f010"]["certificate"]["recall_S999"] for s in ref}, ">= 0.9", rec_ok)
    ctx.physics("P3 E0 inside the Kato-Temple (B=0) / Weinstein (B=1) interval at the plan; E_R >= E0 - 1e-9",
                {s: [ref[s]["plan_f010"]["certificate"]["interval"], ref[s]["plan_f010"]["certificate"]["E_R_minus_E0"]]
                 for s in ref}, "inside; variational", in_ok and var_ok)
    ctx.data["skqd_f1_reference"] = ref
    ctx.data["seconds_per_shot"] = ctx.phases["noiseless_sampling_s"] / max(1, sum(max(plans[c], unif[c]) for c in plans))
    path = os.path.join(ctx.results_dir, "noiseless_sequences.npz")
    np.savez_compressed(path, **{c: v.astype(np.int16) for c, v in seqs.items()})
    ctx.data["results_npz"] = os.path.relpath(path, ROOT)
    ctx.seeds_recorded = all("seed" in v for v in p2.values())
    from campaign33 import add_table
    add_table(ctx, "Exactness (vs the exact Krylov states)", ["family", "circuits", "max |dpsi|", "max leakage", "all ok"],
              [[f, len(ex_rows[f]), worst[f], leak[f], exact_ok[f]] for f in fams])
    add_table(ctx, "Noiseless f = 1 SKQD reference", ["sector", "prefix", "shots", "|B_all|", "recall S999", "E_R - E0",
                                                       "certificate", "E0 inside"],
              [[s, lab, ref[s][lab]["shots"], ref[s][lab]["certificate"]["B_all_size"],
                ref[s][lab]["certificate"]["recall_S999"], ref[s][lab]["certificate"]["E_R_minus_E0"],
                ref[s][lab]["certificate"]["type"], ref[s][lab]["certificate"]["E0_inside"]]
               for s in ref for lab in ref[s]])


# =========================================================================== class 2
def load_record():
    rec = load_json(RECORD)
    return rec


def run_c2_cal(ctx):
    from campaign33 import add_table
    P = A.Physics(with_sectors=False)
    rec = load_record()
    man = C.load_manifest("IBM-T0", "B0_ref117_k1")
    if rec["fingerprint"] != man["record_fingerprint"]:
        raise SystemExit("the record is not the one the IBM circuits were built on")
    circ = C.load_circuit("IBM-T0", "B0_ref117_k1")
    modes = ["custatevec", "batched"] if ctx.device == "GPU" else ["cpu"]
    reps = ["kraus", "pta"]
    ladder = [ctx.scaled(x) for x in (8, 32, 128, 512)]
    ladder = sorted(set(ladder))
    combos = [(r, m) for r in reps for m in modes]
    t_all = time.time()
    total_share = 0.75 * (ctx.remaining() or 1e9)
    per = total_share / len(combos)
    out, rates = {}, {}
    for ci, (rep, mode) in enumerate(combos):
        spec = N.ibm_spec(rec, "I-ECHO", rep, "echo")
        ct = spec.apply(circ)
        sim, kw = simulator(ctx, spec.noise_model, mode)
        t_c = time.time()
        end = t_c + per
        tw = time.time()
        _ = sim.run(ct, shots=1, seed_simulator=TK.chunk_seed(ctx.s0, 990 + ci, 0, 1)).result()
        warm = time.time() - tw
        pts, sps = [], None
        for j, n in enumerate(ladder):
            est = n * (sps if sps else warm)
            if time.time() + est > end:
                pts.append({"shots": n, "skipped": "predicted to overrun this mode's budget share",
                            "predicted_s": est})
                continue
            res, info = sample(ctx, sim, [ct], [n], ["B0_ref117_k1"], circuit_offset=100 * ci + 10 * j,
                               deadline=end, rate_hint=sps if sps else warm, max_chunk=n)
            r0 = res[0]
            cnt = totals(r0)
            acc, rej, _ = A.decode_counts(P, cnt, 0)
            el = info["wall_s"]
            sps = el / max(1, r0["shots_done"])
            pts.append({"shots": n, "shots_done": r0["shots_done"], "seconds": el, "seconds_per_shot": sps,
                        "accepted": int(sum(acc.values())), "reference_hits": int(cnt.get(int(man["reference_int"]), 0)),
                        "calls": info["calls"], "chunks": chunk_record(r0)})
        out[f"{rep}|{mode}"] = {"representation": rep, "mode": mode, "simulator_options": kw,
                                "warmup_s": warm, "ladder": pts, "noise": spec.description}
        done = [p for p in pts if "seconds_per_shot" in p]
        rates.setdefault(rep, {})[mode] = done[-1]["seconds_per_shot"] if done else None
        ctx.log(f"{rep}|{mode}: {[(p['shots'], round(p.get('seconds_per_shot') or -1, 4)) for p in pts]}")
    ctx.phases["ladder_s"] = time.time() - t_all
    # ---- agreement Kraus vs PTA at the largest common ladder point >= 512 (scaled)
    agree, agree_rows = {}, []
    need = ctx.scaled(512)
    for mode in modes:
        a = [p for p in out[f"kraus|{mode}"]["ladder"] if p.get("shots_done", 0) >= need]
        b = [p for p in out[f"pta|{mode}"]["ladder"] if p.get("shots_done", 0) >= need]
        if a and b:
            pa, pb = a[-1], b[-1]
            n1, n2 = pa["shots_done"], pb["shots_done"]
            x1, x2 = pa["accepted"], pb["accepted"]
            pool = (x1 + x2) / (n1 + n2)
            se = math.sqrt(max(pool * (1 - pool), 1e-300) * (1 / n1 + 1 / n2))
            z = abs(x1 / n1 - x2 / n2) / se if se > 0 else 0.0
            agree[mode] = {"kraus": [x1, n1], "pta": [x2, n2], "z": z, "agree_3sigma": bool(z <= 3.0)}
        else:
            agree[mode] = {"agree_3sigma": None, "reason": f"no ladder point with >= {need} shots in both representations"}
        agree_rows.append([mode, agree[mode].get("kraus"), agree[mode].get("pta"), agree[mode].get("z"),
                           agree[mode].get("agree_3sigma")])
    any_agree = any(v.get("agree_3sigma") for v in agree.values())
    representation = "pta" if any_agree else "kraus_only"
    use = "pta" if any_agree else "kraus"
    best_mode = min((m for m in modes if rates.get(use, {}).get(m)), key=lambda m: rates[use][m], default=modes[0])
    decision = {"representation": representation, "production_representation": use, "mode": best_mode,
                "mode_by_representation": {r: min((m for m in modes if rates.get(r, {}).get(m)),
                                                  key=lambda m: rates[r][m], default=None) for r in reps},
                "seconds_per_shot": rates, "rule": ("PTA for production iff the accepted fractions of Kraus and PTA "
                                                    "agree within 3 sigma (binomial) at >= 512 shots in some mode; "
                                                    "else Kraus only; mode = the fastest measured for that representation")}
    ctx.physics("P4 Kraus vs PTA accepted fractions within 3 sigma at >= 512 shots (else kraus_only, still PASS)",
                {m: agree[m].get("z") for m in modes}, "<= 3 sigma, or representation kraus_only", True)
    p5 = {k: sum(1 for p in v["ladder"] if "seconds_per_shot" in p) for k, v in out.items()}
    ctx.physics("P5 timing ladder >= 2 points per mode", p5, ">= 2 per (representation, mode)",
                all(v >= 2 for v in p5.values()))
    ctx.data.update({"cells": out, "agreement": agree, "decision": decision,
                     "circuit": "IBM-T0 B0_ref117_k1", "model": "I-ECHO (record T2 echo)",
                     "seconds_per_shot": rates.get(use, {}).get(best_mode), "gpu_mode_used": best_mode,
                     "record": {"path": os.path.relpath(RECORD, ROOT), "fingerprint": rec["fingerprint"]}})
    add_table(ctx, "Timing ladder (I-ECHO on IBM-T0 B0_ref117_k1)", ["representation|mode", "shots", "s", "s/shot",
                                                                      "accepted"],
              [[k, p["shots"], p.get("seconds"), p.get("seconds_per_shot"), p.get("accepted")]
               for k, v in out.items() for p in v["ladder"]])
    add_table(ctx, "Kraus vs PTA agreement", ["mode", "kraus [acc, N]", "pta [acc, N]", "z", "agree 3 sigma"], agree_rows)


C2_CELLS = {"C2_GATE": ("I-GATE", "IBM-U", ("echo",)), "C2_ECHO": ("I-ECHO", "IBM-T0", ("echo",)),
            "C2_STAR": ("I-STAR", "IBM-T0", ("star",)), "C2_XY4": ("I-XY4", "IBM-T3", ("echo", "star")),
            "C2_COH": ("I-COH", "IBM-T0", ("echo",))}


def run_c2_cell(ctx):
    from campaign33 import add_table
    cell, family, convs = C2_CELLS[ctx.token]
    P = A.Physics(with_sectors=False)
    rec = load_record()
    calp = validation_path(ctx, "C2_CAL")
    if os.path.exists(calp):
        cal = load_json(calp)["data"]["decision"]
        rep = cal["production_representation"]
        mode = cal["mode_by_representation"].get(rep) or cal.get("mode")
        rate = cal["seconds_per_shot"].get(rep, {}).get(mode)
        sizing = f"{os.path.relpath(calp, ROOT)}: {rep}/{mode} at {rate} s/shot"
    else:
        rep, mode, rate = "kraus", ("policy" if ctx.device == "GPU" else "cpu"), None
        sizing = "validation/C2_CAL.json absent at run time: Kraus, policy mode, 20 000 shots per circuit fallback"
    if ctx.args.gpu_mode != "auto":
        mode = ctx.args.gpu_mode
    if ctx.dry:
        # a 21-qubit noisy shot costs minutes on the laptop CPU (Kraus more than PTA): the dry run checks the
        # path with the Pauli-twirled representation and 1 shot per run, at the dry C2_CAL's PTA rate if known
        rep = "pta"
        rate = (cal.get("seconds_per_shot", {}).get("pta", {}).get(mode) if os.path.exists(calp) else None)
        sizing = f"dry run: PTA at {rate} s/shot ({os.path.relpath(calp, ROOT) if os.path.exists(calp) else 'no C2_CAL'})"
        ctx.notes.append("dry run: PTA representation and 1 shot per run (path check); the CI uses C2_CAL's decision")
    ctx.data["gpu_mode_used"] = mode
    ratio = N.t2_star_ratio()
    eps = None
    circs = {cid: (C.load_circuit(family, cid), C.load_manifest(family, cid)) for cid in K1_IDS}
    if cell == "I-COH":
        qubits = sorted({q for cid in K1_IDS for q in circs[cid][1]["physical_qubits"]})
        eps, eps_info = N.coherent_eps_for(qubits)
        ctx.data["coherent_eps"] = {"per_qubit": eps, **eps_info}
    runs = [(cid, conv) for conv in convs for cid in K1_IDS]
    if ctx.dry:
        runs = [(K1_IDS[0], conv) for conv in convs]
        ctx.notes.append("dry run: one circuit (B0_ref117_k1) per T2 convention (the CI runs both K1 circuits)")
    target = ctx.scaled(100000)
    if rate:
        fit = int(0.75 * (ctx.remaining() or 1e9) / (rate * len(runs)))
        shots = max(ctx.args.min_shots, min(target, fit))
        why = f"target 1e5 per circuit, fitted to the budget at {rate:.4g} s/shot ({sizing})"
    else:
        shots = min(target, ctx.scaled(20000))
        why = sizing
    if ctx.dry:
        shots = 1
        why += "; dry run: 1 shot per run (path check)"
    if shots < target:
        ctx.notes.append(f"shots per circuit {shots} below the 1e5 target ({why})")
    k1 = load_json("validation/K1_2x3_fpilot.json")["data"]["circuits"]
    prereg = load_json("data/hardware/K1_2x3_prep/prereg_99035ef05c36019e.json")["circuits"]
    rows, per = [], {}
    t_s = time.time()
    shots_total = 0
    specs, t_b = {}, time.time()
    for conv in convs:
        specs[conv] = N.ibm_spec(rec, cell, "kraus" if rep != "pta" else "pta", conv, ratio, eps)
    ctx.phases["noise_model_build_s"] = time.time() - t_b
    chunk = 1 if ctx.dry else max(SM_chunk(ctx), C2_CHUNK)
    for i, (cid, conv) in enumerate(runs):
        spec = specs[conv]
        circ, man = circs[cid]
        ct = spec.apply(circ)
        sim, kw = simulator(ctx, spec.noise_model, mode)
        res, info = sample(ctx, sim, [ct], [shots], [cid], circuit_offset=i,
                           share=0.75 / max(1, len(runs) - i), rate_hint=rate, max_chunk=chunk)
        if info.get("seconds_per_shot"):
            rate = info["seconds_per_shot"]
        r0 = res[0]
        cnt = totals(r0)
        shots_total += r0["shots_done"]
        tb = int(man["twoB"])
        acc, rej, why_rej = A.decode_counts(P, cnt, tb, reasons=True)
        rt = A.roundtrip_check(P, acc)
        hits = int(cnt.get(int(man["reference_int"]), 0))
        Nn = r0["shots_done"]
        a_cnt = int(sum(acc.values()))
        dim, a_g = int(man["dim"]), float(man["garbage_acceptance"])
        fh = ST.f_hit_cell([(hits, Nn, float(man["p_reference_exact"]), a_g, dim)], kappa=0.82)
        scale = 1e5 / Nn if Nn else 0.0
        meas = k1[cid]
        f0 = N.f0_ibm(circ if cell == "I-GATE" else circ, spec, man["logical_to_physical"], man["reference_bits"])
        exp_acc, exp_hits = a_cnt * scale, hits * scale
        pre = prereg[cid]["expected_reference_hits"]
        per[f"{cid}|{conv}"] = {
            "circuit": cid, "family": family, "t2_convention": spec.description["t2_convention"],
            "representation": spec.description["representation"], "shots": Nn, "chunks": chunk_record(r0),
            "accepted": a_cnt, "distinct_accepted": len(acc), "reference_hits": hits, "rejections": why_rej,
            "roundtrip": rt, "f_hit_kappa_0.82": fh, "f0_twirled": f0,
            "scaled_to_1e5": {"accepted": exp_acc, "reference_hits": exp_hits},
            "measured_K1": {"accepted": meas["accepted"], "reference_hits": meas["reference_hits"],
                            "shots": meas["shots"], "source": "validation/K1_2x3_fpilot.json data.circuits"},
            "P_measured_accepted_under_model": ST.poisson_two_sided(int(meas["accepted"]), exp_acc * meas["shots"] / 1e5)
            if exp_acc > 0 else None,
            "P_measured_hits_under_model": ST.poisson_two_sided(int(meas["reference_hits"]),
                                                                exp_hits * meas["shots"] / 1e5),
            "prereg_expected_hits_1e5": pre, "seconds": info["wall_s"], "simulator_options": kw,
            "noise": spec.description}
        rows.append([cid, conv, Nn, a_cnt, hits, exp_acc, exp_hits, meas["accepted"], meas["reference_hits"],
                     per[f"{cid}|{conv}"]["P_measured_accepted_under_model"], rt["mismatches"]])
        ctx.log(f"{cid} {conv}: {Nn} shots, accepted {a_cnt}, hits {hits}, roundtrip {rt['ok']}")
    ctx.no_shots = any(v["shots"] == 0 for v in per.values())
    if any(v["shots"] < shots for v in per.values()):
        ctx.shots_reduced_to = {k: v["shots"] for k, v in per.items()}
    ctx.phases["sampling_and_decoding_s"] = time.time() - t_s
    ctx.data["seconds_per_shot"] = ctx.phases["sampling_and_decoding_s"] / max(1, shots_total)
    ctx.physics("P6 decoder round trip on every accepted string", {k: v["roundtrip"]["mismatches"] for k, v in per.items()},
                "0 mismatches", all(v["roundtrip"]["ok"] for v in per.values()))
    have = all(v["P_measured_hits_under_model"] is not None and "accepted" in v["scaled_to_1e5"] for v in per.values())
    ctx.physics("P7 simulated accepted counts and reference hits reported with the two-sided Poisson probability of the "
                "measured K1 values (58 / 45 accepted, 0 / 0 hits at 1e5)", have, "fields exist (no threshold)", have)
    ctx.data.update({"cell": cell, "family": family, "conventions": list(convs), "shots_per_circuit": shots,
                     "chunk_shots_per_call": chunk,
                     "shots_reason": why, "representation_used": rep, "per_run": per,
                     "class2_channels": "depolarizing + T1/T2 relaxation (gates; delays in idle-aware cells) + readout"
                                        + (" + coherent Rx(eps) after x" if cell == "I-COH" else ""),
                     "information_only": cell == "I-XY4",
                     "f_point_estimate_claimed": False,
                     "note": "class 2 gives consistency with the K1 measurement and the K0/K1 analytic numbers; no f point "
                             "value is claimed (at f ~ 1e-5, 1e5 shots give ~1 expected hit)"})
    ctx.min_shots_ok = True
    add_table(ctx, f"{cell} on {family}", ["circuit", "T2", "shots", "accepted", "hits", "accepted per 1e5",
                                            "hits per 1e5", "K1 accepted", "K1 hits", "P(K1 accepted | model)",
                                            "roundtrip mismatches"], rows)


# =========================================================================== class 3 engines
def run_c3_engine(ctx):
    from . import engines as EN
    EN.run(ctx)


# =========================================================================== class 4: f-cells
def fcell_ids():
    return list(FCELL_SHOTS)


def variant_families():
    return ["NAT-O0", "NAT-O1", "NAT-O2", "NAT-O3", "NAT-O4", "NAT-O6"]


def run_one_fcell(ctx, P, sid, fam, cell_index, deadline, rate_hint=None):
    spec = N.quantinuum_spec(sid, 20)
    ids = fcell_ids()
    circs, mans, f0 = [], {}, {}
    for cid in ids:
        c, m = C.load_circuit(fam, cid), C.load_manifest(fam, cid)
        circs.append(spec.apply(c))
        mans[cid] = m
        f0[cid] = N.f0_quantinuum(c, spec, m["reference_bits"])
    mode = ctx.data.get("gpu_mode_used") or "policy"
    sim, kw = simulator(ctx, spec.noise_model, mode)
    shots = [ctx.scaled(FCELL_SHOTS[c]) for c in ids]
    res, info = sample(ctx, sim, circs, shots, ids, circuit_offset=4 * cell_index, deadline=deadline,
                       rate_hint=rate_hint)
    per = {r["label"]: totals(r) for r in res}
    st = A.fcell_stats(P, per, mans, kappa=1.0, f0={c: f0[c]["f0"] for c in ids})
    complete = all(r["shots_done"] == s for r, s in zip(res, shots))
    return {"scenario": sid, "family": fam, "complete": complete, "stats": st, "f0": f0,
            "chunks": {r["label"]: chunk_record(r) for r in res}, "seconds": info["wall_s"],
            "shots": int(sum(r["shots_done"] for r in res)), "noise": spec.description,
            "accepted_counts": {r["label"]: sparse_accepted(P, per[r["label"]], sector_of(r["label"]))[0] for r in res},
            "reference_hits": {c: st["per_circuit"][c]["reference_hits"] for c in ids}}


def cf_prediction():
    d = load_json("validation/CF_traj.json")["data"]["C2"]
    shots = sum(v["shots"] for v in d["observed_per_circuit"].values())
    return float(d["predicted_total"]), float(d["predicted_total_se"]), int(shots)


def run_fcells(ctx):
    from campaign33 import add_table
    from scipy.stats import poisson
    P = A.Physics()
    idx = C.load_index()
    part = ctx.token[-1]
    fams = [f for f in variant_families() if f in idx["families"]]
    if part == "A":
        scen = ["E1", "E2", "E3", "E4", "E5a", "E5b", "E5c"]
    else:
        scen = ["E6a", "E6b", "E6c", "E7_0.05", "E7_0.07", "E7_0.10", "E7_0.15"]
        fams = [f for f in fams if f != "NAT-O6"]
    mode, mode_src = gpu_mode_for(ctx)
    t_l = time.time()
    if part == "A":
        lad = fcell_ladder(ctx, P)
        ctx.data["ladder"] = lad
        if ctx.device == "GPU" and ctx.args.gpu_mode == "auto" and lad.get("fastest_mode"):
            mode, mode_src = lad["fastest_mode"], "this token's ladder"
    ctx.phases["ladder_s"] = time.time() - t_l
    ctx.data["gpu_mode_used"] = mode
    ctx.data["gpu_mode_source"] = mode_src
    cells = [(s, "NAT-O0") for s in scen] + [(s, f) for f in fams if f != "NAT-O0" for s in scen]
    if ctx.dry:
        # a budget-limited path check: one cell per scenario with a different variant first, so the few cells a
        # laptop can afford touch every noise transform and several variants
        diag = [(sc, fams[i % len(fams)]) for i, sc in enumerate(scen)]
        cells = diag + [c for c in cells if c not in diag]
    s3_reserve = 0.0
    if part == "B":
        s3_reserve = 0.15 * (ctx.remaining() or 0)
    deadline = None if ctx.deadline is None else time.time() + 0.75 * max(0.0, ctx.deadline - time.time() - s3_reserve)
    out, dropped, rate = {}, [], None
    t_c = time.time()
    for i, (sid, fam) in enumerate(cells):
        nshots = sum(ctx.scaled(v) for v in FCELL_SHOTS.values())
        if deadline is not None and rate is not None and time.time() + rate * nshots > deadline:
            dropped.append(f"{sid}|{fam}")
            continue
        r = run_one_fcell(ctx, P, sid, fam, i, deadline, rate_hint=rate)
        out[f"{sid}|{fam}"] = r
        rate = (time.time() - t_c) / max(1, sum(v["shots"] for v in out.values()))
        pk = r["stats"]["pooled_k1"]
        ctx.log(f"cell {sid}|{fam}: f_hit {pk['f_hit']}, hits {r['reference_hits']}, complete {r['complete']}")
    ctx.phases["cells_s"] = time.time() - t_c
    ctx.data["seconds_per_shot"] = rate
    if dropped:
        ctx.notes.append(f"{len(dropped)} cells dropped for the budget: {dropped}")
    # ---- P10: every variant vs the O0 cell of the same scenario
    p10 = {}
    for key, r in out.items():
        sid, fam = key.split("|")
        o0 = out.get(f"{sid}|NAT-O0")
        if fam == "NAT-O0" or o0 is None:
            continue
        a, b = r["stats"]["pooled_k1"], o0["stats"]["pooled_k1"]
        p10[key] = ST.compare(a["f_hit"], a["f_hit_ci"], b["f_hit"], b["f_hit_ci"])
        p10[key]["variant_status"] = idx["variants"].get(fam, {}).get("status")
    ctx.physics("P10 each variant's f_hit vs the O0 cell (Delta, sigma, verdict reported; an exact optimisation may "
                "move f)", len(p10), "fields present", all("delta" in v for v in p10.values()))
    # ---- tiers for the F runs
    tiers = {}
    for sid in scen:
        r = out.get(f"{sid}|NAT-O0")
        if r is None:
            tiers[sid] = {"tier": None, "reason": "O0 cell not run (budget)"}
            continue
        lo = r["stats"]["pooled_k1"]["f_hat_ideal_ci"][0]
        ok = [f for f in TIERS if lo is not None and f <= lo]
        tiers[sid] = {"tier": max(ok) if ok else 0.05, "f_hat_ideal_lo95": lo,
                      "reason": (f"largest of {list(TIERS)} not above the lower 95 % end {lo:.4g} of f_hat_ideal"
                                 if ok else f"lower 95 % end {lo} below 0.05: the lowest tier 0.05 is used")}
    ctx.data["plan_tiers"] = tiers
    # ---- P11 (A): the E1 x O0 hits vs the CF_traj prediction
    if part == "A" and "E1|NAT-O0" in out:
        r = out["E1|NAT-O0"]
        k1 = [c for c in fcell_ids() if c.endswith("_k1")]
        hits = int(sum(r["reference_hits"][c] for c in k1))
        nk1 = int(sum(r["stats"]["per_circuit"][c]["shots"] for c in k1))
        mu0, se0, sh0 = cf_prediction()
        mu, se = mu0 * nk1 / sh0, se0 * nk1 / sh0
        band_poisson = [int(poisson.ppf(0.025, mu)), int(poisson.isf(0.025, mu))]
        band = [int(poisson.ppf(0.025, max(0.0, mu - 1.96 * se))), int(poisson.isf(0.025, mu + 1.96 * se))]
        ok = band[0] <= hits <= band[1]
        ctx.data["P11"] = {"hits": hits, "k1_shots": nk1, "prediction": mu, "prediction_se": se,
                           "poisson_95_band_at_prediction": band_poisson,
                           "band_including_prediction_uncertainty": band, "inside": ok,
                           "source": "validation/CF_traj.json data.C2 (predicted_total, predicted_total_se per 280 shots)",
                           "rule": "Poisson 95 % band widened by +-1.96 x the trajectory prediction's standard error"}
        ctx.physics("P11 E1 x O0 reference hits on the k = 1 circuits inside the 95 % band of the CF_traj prediction "
                    "(a physics criterion: STOP on FAIL)", hits, f"in {band} (prediction {mu:.1f} +- {se:.1f})", ok)
    # ---- the faithful S3 redo (B)
    if part == "B":
        ctx.data["s3_redo"] = s3_redo(ctx, P)
        s = ctx.data["s3_redo"]
        ctx.physics("P12 faithful S3 redo: accepted count inside the binomial 95 % band of S3's 695 / 3200",
                    s["accepted"], f"in {s['band']} at {s['shots']} shots (yield {s['s3_yield']:.4f})", s["inside"])
    ctx.data["cells"] = {k: {kk: vv for kk, vv in v.items() if kk != "noise"} for k, v in out.items()}
    ctx.data["noise_descriptions"] = {s: N.quantinuum_spec(s).description for s in scen}
    ctx.data["cells_dropped"] = dropped
    ctx.data["P10"] = p10
    ctx.data["fcell_circuits"] = {"shots": FCELL_SHOTS, "source": "validation/Q0P_2x3_plan.json data.stage_E_v3",
                                  "note": ("the f-cell circuits are the Q0P_2x3_plan Stage-E v3 set (B0_ref25 / B1_ref57); "
                                           "prompts/33 1.3 names B0_ref117 / B1_ref29 but cites this JSON, which is "
                                           "authoritative (rule 1); the A6 dry-run circuits are its k = 1 members")}
    ctx.min_shots_ok = not dropped
    ctx.no_shots = not out or any(v["shots"] == 0 for v in out.values())
    if dropped and not ctx.dry:
        ctx.shots_reduced_to = f"{len(cells) - len(dropped)} of {len(cells)} cells"
    add_table(ctx, "f-cells", ["scenario", "variant", "shots", "f_hit (k=1 pooled)", "f_hit 95 %", "f_hat_ideal",
                               "GO v3 (info)", "accepted B0_k1", "f0 B0_k1"],
              [[v["scenario"], v["family"], v["shots"], v["stats"]["pooled_k1"]["f_hit"],
                v["stats"]["pooled_k1"]["f_hit_ci"], v["stats"]["pooled_k1"]["f_hat_ideal"],
                v["stats"]["go_rule_v3_information"],
                v["stats"]["per_circuit"]["B0_ref25_k1"]["accepted_fraction"], v["f0"]["B0_ref25_k1"]["f0"]]
               for v in out.values()])


def fcell_ladder(ctx, P):
    """C4_FCELLS_A's 10-minute ladder: chunk 476 / 952 / 1428 (gpu-memory-bytes 8e9 / 1.6e10 / 2.4e10) x
    {custatevec, batched} on NAT-O0 B0_ref25_k1 under E1 (CPU: the chunks scaled, one mode)."""
    spec = N.quantinuum_spec("E1")
    circ = spec.apply(C.load_circuit("NAT-O0", "B0_ref25_k1"))
    chunks = [476, 952, 1428] if not ctx.dry else [ctx.args.max_shots_per_run, 2 * ctx.args.max_shots_per_run]
    modes = ["custatevec", "batched"] if ctx.device == "GPU" else ["cpu"]
    end = time.time() + min(600.0, 0.2 * (ctx.remaining() or 3000))
    pts = []
    for mode in modes:
        sim, kw = simulator(ctx, spec.noise_model, mode)
        for ch in chunks:
            if time.time() > end:
                pts.append({"mode": mode, "chunk": ch, "skipped": "ladder budget spent"})
                continue
            t0 = time.time()
            try:
                r = sim.run(circ, shots=ch, seed_simulator=TK.chunk_seed(ctx.s0, 800 + len(pts), 0, ch)).result()
                ok = bool(r.success)
            except Exception as exc:
                pts.append({"mode": mode, "chunk": ch, "error": str(exc)[:200]})
                continue
            el = time.time() - t0
            pts.append({"mode": mode, "chunk": ch, "gpu_memory_bytes_model": ch / 476 * 8e9, "seconds": el,
                        "seconds_per_shot": el / ch, "success": ok})
    good = [p for p in pts if "seconds_per_shot" in p]
    best = min(good, key=lambda p: p["seconds_per_shot"]) if good else None
    return {"points": pts, "fastest_mode": best["mode"] if best else None,
            "fastest_chunk": best["chunk"] if best else None,
            "note": "one run() call per point; s/shot includes the per-call set-up"}


def s3_redo(ctx, P):
    """The faithful S3 redo: IR-L3-RZZ B=0 (32 circuits in S3's order), the declared E8 model, 100 shots per
    circuit, seed_simulator 11, gate S3's chunking (`sample_many`, chunk shot_chunk_for(20, 32, 8e9) on the GPU)."""
    from skqd import circuits_qiskit as cq
    from skqd.krylov import references
    s3 = load_json("validation/S3.json")["data"]
    refs = [int(r) for r in references(P.M.basis, 0)]
    order = [f"B0_ref{r:02d}_k{k}" for r in refs for k in range(1, 5)]
    order = select_ids(ctx, order) if ctx.args.max_circuits else order
    tqs = [C.load_circuit("IR-L3-RZZ", c) for c in order]
    spec = N.quantinuum_spec("E8")
    shots = ctx.scaled(100)
    chunk = (cq.shot_chunk_for(20, len(tqs), 8e9) if ctx.device == "GPU" else
             (ctx.args.max_shots_per_run or None))
    t0 = time.time()
    counts_list, binfo = cq.sample_many(None, 20, shots, noise_model=spec.noise_model, device=ctx.device,
                                        batched_shots_gpu=ctx.device == "GPU", seed=11, transpiled=tqs,
                                        max_shots_per_run=chunk, return_info=True)
    acc_tot = 0
    for counts in counts_list:
        cint = {sum(int(b) << k for k, b in enumerate(key)): v for key, v in counts.items()}
        a, _r, _ = A.decode_counts(P, cint, 0)
        acc_tot += int(sum(a.values()))
    n = shots * len(tqs)
    y = float(s3["accepted"]) / float(s3["total_shots"])
    band = ST.binomial_band(n, y)
    return {"circuits": order, "shots_per_circuit": shots, "shots": n, "accepted": acc_tot, "yield": acc_tot / n,
            "s3_accepted": s3["accepted"], "s3_total_shots": s3["total_shots"], "s3_yield": y, "band": band,
            "inside": bool(band[0] <= acc_tot <= band[1]),
            "equal_to_s3_count": bool(acc_tot == s3["accepted"] and n == s3["total_shots"]),
            "seed_simulator": 11, "chunk": chunk, "batching": binfo, "seconds": time.time() - t0,
            "source": "validation/S3.json data (accepted, total_shots); scripts/s3_device_model.py path"}


# =========================================================================== class 4: plan-of-record / S3-quota runs
F_SPECS = {"F1": ("E1", "NAT-O0", "plan", None), "F2": ("E2", "NAT-O0", "plan", None),
           "F3": ("E3", "NAT-O0", "plan", None), "F4": ("E7_0.10", "NAT-O0", "s3quota", None),
           "F5": ("E7_0.07", "NAT-O0", "plan", 0.10), "F6": ("E5b", "NAT-O0", "plan", None),
           "F7": ("E1", "CHOSEN", "plan", None), "F8": ("E8", "S3FAMILY", "s3quota", None)}


def parse_f_token(token):
    """C4_F4_B0a -> ('F4', 0, 'a')."""
    parts = token.split("_")
    f, sec = parts[1], parts[2]
    twoB = 0 if sec.startswith("B0") else 2
    half = sec[2:] or None
    return f, twoB, half


def run_frun(ctx):
    from campaign33 import add_table
    P = A.Physics()
    idx = C.load_index()
    fkey, twoB, half = parse_f_token(ctx.token)
    sid, fam, kind, fixed_tier = F_SPECS[fkey]
    sec = "B=0" if twoB == 0 else "B=1"
    if fam == "CHOSEN":
        fam = idx.get("chosen_variant") or "NAT-O0"
        fam_rule = f"index chosen_variant = {idx.get('chosen_variant')}"
    elif fam == "S3FAMILY":
        ok = idx["families"].get("IR-L3-RZZ", {}).get("all_exact")
        fam = "IR-L3-RZZ" if ok else "NAT-O0"
        fam_rule = ("IR-L3-RZZ (the circuits gate S3 sampled) because it passes the exactness bar on all 44: E8 puts "
                    "its one-qubit error on rz as well, and NAT-O0 writes each native PhasedX as rz.rx.rz, which would "
                    "triple-count the native one-qubit gates" if ok else
                    "NAT-O0: IR-L3-RZZ fails the exactness bar, so the exact family is used (E8 then also charges the "
                    "rz pair of every PhasedX: recorded)")
    else:
        fam_rule = "prompts/33 1.5"
    all_ids = [c for c in idx["families"][fam]["circuits"] if sector_of(c) == twoB]
    ids = select_ids(ctx, all_ids, tuple(FCELL_SHOTS))
    tier, tier_reason = (None, None)
    if kind == "plan":
        tier, tier_reason = plan_tier(ctx, sid, fixed_tier)
        plan_full, plan_meta = cv_plan(tier, sec)
        want = {c: ctx.scaled(plan_full[c]) for c in ids}
    else:
        u = PRODUCTION_SHOTS_PER_SECTOR // len(all_ids)
        h = u // 2 if half == "a" else u - u // 2
        want = {c: ctx.scaled(h) for c in ids}
        plan_full, _ = cv_plan(0.10, sec)
    spec = N.quantinuum_spec(sid)
    mode, mode_src = gpu_mode_for(ctx, "C4_FCELLS_A")
    ctx.data["gpu_mode_used"] = mode
    sim, kw = simulator(ctx, spec.noise_model, mode)
    circs = {c: C.load_circuit(fam, c) for c in ids}
    mans = {c: C.load_manifest(fam, c) for c in ids}
    t_s = time.time()
    res, info = sample(ctx, sim, [spec.apply(circs[c]) for c in ids], [want[c] for c in ids], ids,
                       circuit_offset=0, share=0.6 if kind == "plan" else 0.75)
    ctx.phases["sampling_s"] = time.time() - t_s
    done = {r["label"]: r["shots_done"] for r in res}
    ctx.data["seconds_per_shot"] = info["seconds_per_shot"]
    full = all(done[c] == want[c] for c in ids)
    if not full:
        ctx.min_shots_ok = False
        ctx.shots_reduced_to = {c: done[c] for c in ids if done[c] < want[c]}
    ctx.no_shots = any(done[c] == 0 for c in ids)
    # ---- CV3 extra samples (NAT-O0 plan runs only, and only if the budget covers them in full)
    eq = None
    cv3_status = "not_evaluated: not a NAT-O0 plan-of-record run" if not (kind == "plan" and fam == "NAT-O0") else None
    if cv3_status is None:
        n_sec = sum(want.values())
        N_eq = int(math.ceil(n_sec / len(ids) / 100.0) * 100) if not ctx.dry else max(2, int(math.ceil(n_sec / len(ids))))
        k5_all = [c for c in idx["families"].get("NAT-O0-k5", {}).get("circuits", []) if sector_of(c) == twoB]
        k5_ids = [f"{sec.replace('=', '')}_ref{int(mans[c]['reference']):02d}_k5" for c in ids if int(mans[c]["k"]) == 1]
        k5_ids = [c for c in k5_ids if c in k5_all]
        extra = N_eq * (len(ids) + len(k5_ids))
        rate = info["seconds_per_shot"] or 0.0
        rem = 0.75 * (ctx.remaining() or 1e9)
        if not k5_ids:
            cv3_status = "not_evaluated: no NAT-O0-k5 circuits frozen for this sector"
        elif rate * extra > rem:
            cv3_status = (f"not_evaluated: the equal-shots ({N_eq} per circuit) and k = 5 samples need "
                          f"{extra} shots ~ {rate * extra:.0f} s, more than the {rem:.0f} s left (budget)")
        else:
            t_e = time.time()
            r_eq, i_eq = sample(ctx, sim, [spec.apply(circs[c]) for c in ids], [N_eq] * len(ids), ids,
                                circuit_offset=100, rate_hint=rate)
            k5c = [spec.apply(C.load_circuit("NAT-O0-k5", c)) for c in k5_ids]
            r_k5, i_k5 = sample(ctx, sim, k5c, [N_eq] * len(k5_ids), k5_ids, circuit_offset=200, rate_hint=rate)
            ctx.phases["cv3_sampling_s"] = time.time() - t_e
            if all(r["shots_done"] == N_eq for r in r_eq + r_k5):
                eq = (A.Prefixes(P, twoB, r_eq), N_eq, A.Prefixes(P, twoB, r_k5))
                cv3_status = f"evaluated at N_eq = {N_eq} per circuit (k <= 4) + {len(k5_ids)} k = 5 circuits"
            else:
                cv3_status = "not_evaluated: the equal-shots sample was cut by the deadline"
    t_a = time.time()
    pre = A.Prefixes(P, twoB, res)
    Et = A.e_tol(P, sec)
    out = {"scenario": sid, "family": fam, "family_rule": fam_rule, "kind": kind, "half": half, "sector": sec,
           "plan_tier": tier, "plan_tier_reason": tier_reason, "shots_requested": want, "shots_done": done,
           "full": full, "E_tol": Et, "cv3_status": cv3_status, "noise": spec.description,
           "chunks": {r["label"]: chunk_record(r) for r in res}, "sampling": {k: v for k, v in info.items()}}
    # the plan-of-record prefix where it is covered (every gate_CV prefix point must be a chunk boundary)
    def on_bounds(plan):
        return all(SM.rnd(phi * plan[c]) in pre.bounds[c] for c in ids for phi in SM.PHI)
    if kind == "plan":
        if full and on_bounds(want):
            out["cv"] = A.cv_reading(P, sec, pre, want, Et["value"], eq=eq, with_random=True)
            out["plan_prefix"] = "the whole run (plan of record)"
        else:
            out["cv"] = None
            out["plan_prefix"] = ("incomplete: the budget cut the plan of record (shots_reduced_to); the CV reading "
                                  "is not evaluated on a partial plan")
    else:
        plan_s = {c: ctx.scaled(plan_full[c]) for c in ids}
        covered = all(plan_s[c] <= done[c] for c in ids) and on_bounds(plan_s)
        out["plan_prefix"] = ("covered" if covered else "prefix_not_covered: some per-circuit plan shots exceed the "
                              "uniform half's count (or its prefixes are not chunk boundaries); the CV reading of this "
                              "sector comes from the F1-F3/F5 runs")
        out["cv"] = A.cv_reading(P, sec, pre, plan_s, Et["value"], with_random=True) if covered else None
    n_full, shots = pre.counts(done)
    pt = A.skqd_point(P, sec, n_full, shots, with_random=False)
    cert = A.certificate_reading(sec, pt)
    out["at_N"] = {"shots": shots, "certificate": cert, "B_all_size": pt["B_all_size"],
                   "accepted": pt["accepted"], "n_distinct": pt["n_distinct"]}
    per_counts = {r["label"]: totals(r) for r in res}
    fc = A.fcell_stats(P, per_counts, mans, kappa=1.0)
    out["clean_fraction"] = fc
    acc_counts = {c: sparse_accepted(P, per_counts[c], twoB)[0] for c in ids}
    out["accepted_counts_by_circuit"] = acc_counts
    out["rejected_by_circuit"] = {c: sparse_accepted(P, per_counts[c], twoB)[1] for c in ids}
    out["reference_hits_by_circuit"] = {c: int(per_counts[c].get(int(mans[c]["reference_int"]), 0)) for c in ids}
    t_b = time.time()
    out["bootstrap_at_N"] = A.bootstrap_point(P, sec, [acc_counts[c] for c in ids], ctx.args.bootstrap, 33)
    ctx.phases["bootstrap_s"] = time.time() - t_b
    out["results_npz"] = save_npz(ctx, "chunks", P, res, lambda c: twoB)
    ctx.phases["analysis_s"] = time.time() - t_a
    # ---- criteria
    cv0_ok = out["cv"]["cv0"]["ok"] if out.get("cv") else True
    var_ok = cert["variational_ok"] and (out["cv"]["cv0"]["variational_ok"] if out.get("cv") else True)
    ctx.physics("P13 E_R >= E0 - 1e-9 everywhere, prefixes nested (CV0), E0 inside the certificate of ruling 2 at N",
                {"variational": var_ok, "cv0": cv0_ok, "E0_inside": cert["E0_inside"], "certificate": cert["type"]},
                "all true", var_ok and cv0_ok and cert["E0_inside"])
    if not var_ok:
        ctx.notes.append("STOP (prompts/33 section 8): E_R < E0 - 1e-9 (variational violation)")
    pk = fc["pooled_k1"]
    lo = pk["f_hat_ideal_ci"][0] if pk else None
    if kind == "plan":
        gating = lo is not None and tier is not None and lo >= tier
        name = (f"P14 recall of S999 >= 0.9 on B_all at N ({'criterion' if gating else 'information'}: f_hat_ideal "
                f"lower end {lo} vs tier {tier})")
        if gating:
            ctx.physics(name, cert["recall_S999"], ">= 0.9", cert["recall_S999"] >= 0.9)
        else:
            out["P14_information"] = {"recall_S999": cert["recall_S999"], "reason": name}
        out["CV1_CV5"] = {k: (v.get("ok") if isinstance(v, dict) else None)
                          for k, v in (out["cv"]["criteria"] if out.get("cv") else {}).items() if k.startswith("CV")}
    else:
        out["P15"] = ("evaluated at assembly on the merged a + b halves (2e5 shots per sector): "
                      "validation/C33_campaign.json")
    ctx.data["frun"] = out
    ctx.seeds_recorded = all(all("seed" in ch for ch in v) for v in out["chunks"].values())
    add_table(ctx, f"{ctx.token}: {sid} x {fam}, {sec}, {kind}" + (f" half {half}" if half else ""),
              ["shots", "|B_all|", "E_R - E0", "certificate", "width", "E0 inside", "recall S999", "W",
               "f_hit (k=1)", "f_hat_ideal 95 %"],
              [[shots, pt["B_all_size"], cert["E_R_minus_E0"], cert["type"], cert["width"], cert["E0_inside"],
                cert["recall_S999"], cert["W"], pk["f_hit"] if pk else None,
                pk["f_hat_ideal_ci"] if pk else None]])
    if out.get("cv"):
        cr = out["cv"]["criteria"]
        add_table(ctx, "CV0-CV5 (information; the plan-of-record check is CV_2x3_plan)",
                  ["CV0", "CV1", "CV2", "CV3", "CV4", "CV5"],
                  [[out["cv"]["cv0"]["ok"]] + [cr.get(k, {}).get("ok") if isinstance(cr.get(k), dict) else None
                                               for k in ("CV1", "CV2", "CV3", "CV4", "CV5")]])


# =========================================================================== class 4: C4_CF
CF_ARMS = (("B0_ref25_k1", "depol"), ("B1_ref57_k1", "depol"), ("B0_ref25_k4", "depol"), ("B0_ref25_k1", "xx"))


def run_cf(ctx):
    from . import cf_gpu
    cf_gpu.run(ctx)


# =========================================================================== laptop data stage
def write_exact_data():
    """data/campaign33/exact/: the sector codeword tables and the exact distributions of the Stage-E
    circuits (C3_LE / C3_SEL need only numpy + json in their own envs)."""
    P = A.Physics(with_sectors=False)
    out = {"produced_by": "scripts/campaign33.py --stage exact-data", "prompt": "prompts/33 A6",
           "convention": "string int: bit k = qubit k = clbit k (skqd.reference_sim)",
           "sectors": {}, "circuits": {}}
    for sec, tb in A.SECTORS:
        idx = list(P.M.basis.sector(tb))
        out["sectors"][sec] = {"codeword_ints": [int(P.emb.ints[i]) for i in idx], "basis_indices": [int(i) for i in idx]}
    for cid in FCELL_SHOTS:
        man = load_json(os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", cid + ".manifest.json"))
        psi = exact_state(P, int(man["twoB"]), int(man["reference"]), int(man["k"]), float(man["dt"]))
        pr = exact_probs(P, psi)
        out["circuits"][cid] = {"twoB": int(man["twoB"]), "reference_int": int(man["reference_int"]),
                                "probabilities": {str(k): v for k, v in sorted(pr.items()) if v > 1e-15},
                                "sum": float(sum(pr.values()))}
    path = os.path.join(EXACT_DIR, "stage_e.json")
    jdump(path, out)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0
