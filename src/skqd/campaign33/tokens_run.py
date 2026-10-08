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
            d = load_json(p)["data"]
            dec = d.get("decision", {})
            m = dec.get("mode_by_representation", {}).get(rep) if rep else dec.get("mode")
            if m:
                return m, f"{os.path.relpath(p, ROOT)} decision"
            m = (d.get("ladder") or {}).get("fastest_mode")
            if m and m != "cpu":
                # C4_FCELLS_A records its ladder, not a decision block (prompts/33a R4: its ladder gives the mode)
                return m, f"{os.path.relpath(p, ROOT)} ladder.fastest_mode"
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
           max_chunk=None, phis=SM.PHI, min_rounds=None, plans=None):
    s = SM.Sampler(sim, ctx.s0, int(max_chunk or SM_chunk(ctx)),
                   deadline if deadline is not None else ctx.sampling_deadline(share), log=ctx.log, rate_hint=rate_hint,
                   min_rounds=(1 if ctx.dry else 0) if min_rounds is None else int(min_rounds), phis=phis)
    res, info = s.run(circuits, shots, labels, circuit_offset, plans=plans)
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
    return [{k: ch[k] for k in ("start", "shots", "seed", "seconds") if k in ch} for ch in res["chunks"]]


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
C2_CAL_ARCHIVE = "validation/archive/C2_CAL_job59491475.json"
C2_CAL_ARMS = (("pta", 512, False), ("rm", 1024, False), ("kraus", 1024, True))   # (representation, shots, stopped)
C2_CAL_KRAUS_MIN = 384
C2_CAL_CHUNK = 128
C2_CAL_KRAUS_SHARE = 0.9          # the Kraus arm runs to 0.9 of what is left (prompts/33a section 2)
C2_CAL_FIXED_GUARD = 0.6          # PTA / RM are fixed; this only stops a catastrophically slow arm (recorded)
C2_CAL_DRY = {"pta": 4, "rm": 8, "kraus": 4, "chunk": 2, "kraus_min": 4}
C2_CAL_SEED_OFFSET = 500          # run 1 used circuit indices 0..330 and 990..999: run 2's streams are disjoint
K1_COUNTS_DIR = os.path.join(ROOT, "data", "hardware", "K1_2x3_ibm_kingston", "counts")
K1_JSON = "validation/K1_2x3_fpilot.json"


def load_record():
    rec = load_json(RECORD)
    return rec


def clbit_physical(circ) -> list:
    """[physical qubit of clbit k] from the circuit's measurements (the IBM circuits are 156-qubit physical)."""
    mm = C.measure_map(circ)
    return [int(mm[k]) for k in range(len(mm))]


def k1_device_structure(cid, clbit_to_phys=None) -> dict:
    """The garbage structure of the K1 hardware strings of `cid` (data/hardware/K1_2x3_ibm_kingston/counts), read
    through the same function as the simulated arms.  The device flew IBM-T3."""
    d = load_json(os.path.join(K1_COUNTS_DIR, cid + ".json"))
    cnt = SM.counts_to_int(d["counts"])
    nb = len(next(iter(d["counts"])).replace(" ", ""))
    mm = {int(k): int(v) for k, v in d["measurement_map_clbit_to_physical"].items()}
    st = ST.garbage_structure(cnt, nb, [mm[k] for k in range(nb)])
    st.update({"source": os.path.relpath(os.path.join(K1_COUNTS_DIR, cid + ".json"), ROOT), "job_id": d.get("job_id"),
               "family_flown": "IBM-T3 (XY4 in the delays)",
               "map_matches_circuit": None if clbit_to_phys is None else
               [mm[k] for k in range(nb)] == [int(x) for x in clbit_to_phys]})
    return st


def k1_readout_means():
    """Mean P(0|0), P(1|1) over the K1 readout block's qubits (validation/K1_2x3_fpilot.json data.readout)."""
    ro = load_json(K1_JSON)["data"]["readout"]
    p00 = float(np.mean(ro["P_0_given_0"]))
    p11 = float(np.mean(ro["P_1_given_1"]))
    return p00, p11, f"{K1_JSON} data.readout (mean over {len(ro['P_0_given_0'])} qubits)"


def k1_measured(cid) -> dict:
    m = load_json(K1_JSON)["data"]["circuits"][cid]
    return {"accepted": int(m["accepted"]), "reference_hits": int(m["reference_hits"]), "shots": int(m["shots"]),
            "source": f"{K1_JSON} data.circuits.{cid}"}


def arm_observables(P, r0, man, clbit_to_phys, twoB) -> dict:
    """Per arm (prompts/33a step B): the garbage structure, accepted count, distinct accepted strings, reference
    hits, rejection reasons and the decoder round trip, from the raw counts of every chunk."""
    cnt = totals(r0)
    acc, rej, why = A.decode_counts(P, cnt, twoB, reasons=True)
    return {"structure": ST.garbage_structure(cnt, len(clbit_to_phys), clbit_to_phys),
            "accepted": int(sum(acc.values())), "distinct_accepted": len(acc),
            "reference_hits": int(cnt.get(int(man["reference_int"]), 0)), "rejected": int(rej), "rejections": why,
            "roundtrip": A.roundtrip_check(P, acc), "chunks": chunk_record(r0)}


def run_c2_cal(ctx):
    """C2_CAL run 2 (prompts/33a step B): PTA 512 / RM 1024 / Kraus (target 1024, minimum 384, deadline-stopped)
    on IBM-T0 B0_ref117_k1 under I-ECHO, cuStateVec only (the batched arm is closed by R1), compared on the
    garbage structure (mean Hamming weight + per-clbit marginals) -> decision.production_representation."""
    import hashlib
    from campaign33 import add_table
    P = A.Physics(with_sectors=False)
    rec = load_record()
    cid = "B0_ref117_k1"
    man = C.load_manifest("IBM-T0", cid)
    if rec["fingerprint"] != man["record_fingerprint"]:
        raise SystemExit("the record is not the one the IBM circuits were built on")
    circ = C.load_circuit("IBM-T0", cid)
    clb = clbit_physical(circ)
    # ---- the run-1 record (job 59491475): archived byte-identically, never edited
    arch = os.path.join(ROOT, C2_CAL_ARCHIVE)
    sha = hashlib.sha256(open(arch, "rb").read()).hexdigest() if os.path.exists(arch) else None
    supersedes = {"job": "59491475", "archived": C2_CAL_ARCHIVE, "sha256": sha,
                  "why": "prompts/33a R1: P5 failed on the ladder points only; the mode is decided from that record "
                         "(cuStateVec faster than batched at every measured point; batched closed) and the "
                         "representation question (does a cheap channel reproduce Kraus) was not answered: P4 "
                         "compared accepted fractions at 512 shots, which carry ~0.3 expected accepted strings"}
    ctx.R.add("P0 run-1 record archived unedited and referenced (supersedes + sha256)", sha,
              f"{C2_CAL_ARCHIVE} present", sha is not None)
    mode = ctx.args.gpu_mode if ctx.args.gpu_mode not in ("auto", "policy") else ("custatevec" if ctx.device == "GPU" else "cpu")
    if ctx.device != "GPU":
        mode = "cpu"
    ctx.data["gpu_mode_used"] = mode
    # ---- the three models and the RM build check
    t_b = time.time()
    specs = {rep: N.ibm_spec(rec, "I-ECHO", rep, "echo") for rep in ("pta", "rm", "kraus")}
    ctx.phases["noise_model_build_s"] = time.time() - t_b
    t_r = time.time()
    rm_chk = N.rm_vs_kraus_check(specs["kraus"], specs["rm"], rec, man["physical_qubits"],
                                 circuit=specs["rm"].apply(circ))
    ctx.phases["rm_check_s"] = time.time() - t_r
    ctx.R.add("P4r RM model: no Kraus instruction (to_dict and delay-pass errors); the T2 <= T1 qubits identical to "
              "the Kraus model", {"changed": sorted(int(q) for q in rm_chk["changed_qubits"]),
                                  "unchanged": rm_chk["n_unchanged"],
                                  "max_superop_diff": rm_chk["max_superop_diff_unchanged"],
                                  "kraus_in_rm": rm_chk["kraus_in_rm"]},
              "0 kraus; SuperOp / readout diff <= 1e-12 on unchanged sites", rm_chk["ok"])
    # ---- the arms, in order PTA, RM, Kraus (deadline-stopped last)
    dry = ctx.dry
    chunk = C2_CAL_DRY["chunk"] if dry else C2_CAL_CHUNK
    kmin = C2_CAL_DRY["kraus_min"] if dry else C2_CAL_KRAUS_MIN
    arms, rows = {}, []
    t_all = time.time()
    for i, (rep, target, stopped) in enumerate(C2_CAL_ARMS):
        n = C2_CAL_DRY[rep] if dry else int(math.ceil(target * ctx.args.shots_scale))
        spec = specs[rep]
        ct = spec.apply(circ)
        sim, kw = simulator(ctx, spec.noise_model, mode)
        rem = ctx.remaining()
        if stopped:
            deadline = None if rem is None else time.time() + C2_CAL_KRAUS_SHARE * max(0.0, rem)
            min_rounds = int(math.ceil(kmin / chunk)) if dry else 0
        else:
            # fixed arms: a guard only (expected 135 s / 270 s of a 2100 s budget); a dry run samples them in full
            deadline = None if rem is None else time.time() + C2_CAL_FIXED_GUARD * max(0.0, rem)
            min_rounds = 10 ** 6 if dry else 0
        t_a = time.time()
        res, info = sample(ctx, sim, [ct], [n], [cid], circuit_offset=C2_CAL_SEED_OFFSET + i, deadline=deadline,
                           max_chunk=chunk, phis=(1.0,), min_rounds=min_rounds)
        r0 = res[0]
        obs = arm_observables(P, r0, man, clb, 0)
        pts = [{"shots": ch["shots"], "seconds": ch["seconds"], "seconds_per_shot": ch["seconds"] / ch["shots"],
                "seed": ch["seed"], "start": ch["start"]} for ch in r0["chunks"]]
        big = max((p["shots"] for p in pts), default=0)
        at_big = [p for p in pts if p["shots"] == big]
        rate_big = (sum(p["seconds"] for p in at_big) / sum(p["shots"] for p in at_big)) if at_big else None
        arms[rep] = {"representation": rep, "mode": mode, "target_shots": n, "deadline_stopped": stopped,
                     "minimum_shots": kmin if stopped else n, "chunk": chunk, "shots_done": r0["shots_done"],
                     "points": pts, "calls": info["calls"], "stopped": info["stopped"], "warmup": info["warmup"],
                     "seconds": time.time() - t_a, "sampling_wall_s": info["wall_s"],
                     "seconds_per_shot_mean": info["seconds_per_shot"],
                     "seconds_per_shot_at_largest_point": rate_big, "largest_point_shots": big,
                     "simulator_options": kw, "noise": spec.description, **obs}
        rows.append([rep, n, r0["shots_done"], len(pts), rate_big, obs["structure"].get("mean_hamming_weight"),
                     obs["structure"].get("se_mean_hamming_weight"), obs["accepted"], obs["reference_hits"]])
        ctx.log(f"{rep}: {r0['shots_done']}/{n} shots in {len(pts)} chunks, {rate_big} s/shot at {big}, "
                f"w {obs['structure'].get('mean_hamming_weight')}, accepted {obs['accepted']}")
    ctx.phases["arms_s"] = time.time() - t_all
    # ---- comparisons
    st = {rep: arms[rep]["structure"] for rep in arms}
    p4a = ST.structure_compare(st["rm"], st["kraus"])
    p4b = ST.structure_compare(st["pta"], st["kraus"])
    device = k1_device_structure(cid, clb)
    p00, p11, ro_src = k1_readout_means()
    p4c = {rep: {"vs_K1": ST.structure_compare(st[rep], device), "readout_share": ST.readout_share(st[rep], p00, p11)}
           for rep in arms}
    p4c["K1_device"] = {"readout_share": ST.readout_share(device, p00, p11), "readout_source": ro_src,
                        "note": "information: the device flew IBM-T3 (XY4 in the delays), this calibration samples IBM-T0"}
    decided = p4a.get("pass") is not None
    prod = "rm" if p4a.get("pass") else "kraus"
    rates = {rep: {mode: arms[rep]["seconds_per_shot_at_largest_point"]} for rep in arms}
    decision = {"production_representation": prod, "representation": prod, "mode": mode,
                "mode_by_representation": {rep: mode for rep in arms}, "seconds_per_shot": rates,
                "p4a_pass": p4a.get("pass"), "p4a_evaluated": decided,
                "batched": "closed (prompts/33a R1: slower than cuStateVec at every point of job 59491475; do not retry)",
                "pta": "information only, never the production channel (prompts/33a R2: unital)",
                "rule": "production = rm iff P4a passes (RM vs Kraus: |z| <= 3 on the mean Hamming weight and on every "
                        "per-clbit marginal), else kraus; mode = cuStateVec (job 59491475's record)"}
    ctx.physics("P4a RM vs Kraus garbage structure: |z| <= 3 on the mean Hamming weight and every marginal "
                "(decides the production representation; PASS or FAIL are both a decision)",
                {"pass": p4a.get("pass"), "z_w": p4a.get("z_mean_hamming_weight"),
                 "max_abs_z_marginal": p4a.get("max_abs_z_marginal"), "production": prod},
                "decided (both arms sampled)", decided)
    ctx.physics("P4b PTA vs Kraus, same statistic (information; expected to fail: PTA is unital)",
                {"pass": p4b.get("pass"), "z_w": p4b.get("z_mean_hamming_weight"),
                 "max_abs_z_marginal": p4b.get("max_abs_z_marginal")}, "information", True)
    have_c = all("vs_K1" in p4c[rep] for rep in arms) and device.get("shots")
    ctx.physics("P4c each arm vs the K1 measurement (z of the weight and marginals, readout share; information)",
                {rep: p4c[rep]["vs_K1"].get("z_mean_hamming_weight") for rep in arms}, "fields present", bool(have_c))
    npts = {rep: len(arms[rep]["points"]) for rep in arms}
    kdone = arms["kraus"]["shots_done"]
    ctx.physics("P5' >= 2 ladder points per representation (cuStateVec) and Kraus shots_done >= the minimum",
                {"points": npts, "kraus_shots_done": kdone}, f">= 2 each; Kraus >= {kmin}",
                all(v >= 2 for v in npts.values()) and kdone >= kmin)
    fixed_ok = all(arms[rep]["shots_done"] == arms[rep]["target_shots"] for rep in ("pta", "rm"))
    ctx.min_shots_ok = bool(fixed_ok and kdone >= kmin)
    ctx.no_shots = any(arms[rep]["shots_done"] == 0 for rep in arms)
    if not ctx.min_shots_ok or kdone < arms["kraus"]["target_shots"]:
        ctx.shots_reduced_to = {rep: arms[rep]["shots_done"] for rep in arms}
    ctx.data.update({"run": 2, "supersedes": supersedes, "arms": arms, "rm_check": rm_chk,
                     "comparisons": {"P4a_rm_vs_kraus": p4a, "P4b_pta_vs_kraus": p4b, "P4c_vs_K1": p4c},
                     "K1_device_structure": device, "decision": decision,
                     "circuit": f"IBM-T0 {cid}", "model": "I-ECHO (record T2 echo)",
                     "seconds_per_shot": rates[prod][mode], "seed_circuit_offsets": {rep: C2_CAL_SEED_OFFSET + i
                                                                                    for i, (rep, _t, _s) in enumerate(C2_CAL_ARMS)},
                     "design": {"arms": [list(a) for a in C2_CAL_ARMS], "chunk": chunk, "kraus_minimum": kmin,
                                "kraus_share_of_remaining": C2_CAL_KRAUS_SHARE, "fixed_arm_guard": C2_CAL_FIXED_GUARD,
                                "dry_run_shots": C2_CAL_DRY if dry else None,
                                "source": "prompts/33a section 2"},
                     "record": {"path": os.path.relpath(RECORD, ROOT), "fingerprint": rec["fingerprint"]}})
    add_table(ctx, "C2_CAL run 2 arms (I-ECHO on IBM-T0 B0_ref117_k1, cuStateVec)",
              ["representation", "target", "shots done", "points", "s/shot (largest point)", "mean weight", "se",
               "accepted", "reference hits"], rows)
    add_table(ctx, "Garbage-structure comparisons", ["comparison", "z mean weight", "max |z| marginal",
                                                     "marginals outside", "pass"],
              [[k, v.get("z_mean_hamming_weight"), v.get("max_abs_z_marginal"), v.get("clbits_outside"), v.get("pass")]
               for k, v in (("P4a RM vs Kraus", p4a), ("P4b PTA vs Kraus (information)", p4b))]
              + [[f"P4c {rep} vs K1 (information)", p4c[rep]["vs_K1"].get("z_mean_hamming_weight"),
                  p4c[rep]["vs_K1"].get("max_abs_z_marginal"), p4c[rep]["vs_K1"].get("clbits_outside"),
                  p4c[rep]["vs_K1"].get("pass")] for rep in arms])


C2_CELLS = {"C2_GATE": ("I-GATE", "IBM-U", ("echo",)), "C2_ECHO": ("I-ECHO", "IBM-T0", ("echo",)),
            "C2_STAR": ("I-STAR", "IBM-T0", ("star",)), "C2_XY4": ("I-XY4", "IBM-T3", ("echo", "star")),
            "C2_COH": ("I-COH", "IBM-T0", ("echo",))}
C2_KRAUS_REF_SHARE = 0.2            # prompts/33a step C: the in-cell Kraus reference arm takes 20 % of the window
C2_REF_CHUNK = 128
C2_MIN_SHOTS = {"rm": 1000, "kraus": 256}     # S6 of a C2 cell: production shots per circuit (prompts/33a step C3)
C2_UNDERPOWERED_BELOW = 5.0         # expected accepted strings at the device's rate below which counts are underpowered
C2_TARGET_PER_CIRCUIT = 100000      # the prompts/33 target, withdrawn as a goal by prompts/33a R3; kept as the cap


def c2_cal_decision(ctx):
    """(representation, mode, rates, source) for the production arm of a C2 cell: C2_CAL run 2's P4a decision
    (rm iff P4a passed, else kraus); kraus when only the run-1 record or no C2_CAL JSON exists.  PTA is never
    the production channel (prompts/33a R2)."""
    calp = validation_path(ctx, "C2_CAL")
    mode_default = "custatevec" if ctx.device == "GPU" else "cpu"
    if not os.path.exists(calp):
        return "kraus", mode_default, {}, "validation/C2_CAL.json absent at run time: kraus (prompts/33a R2 default)"
    d = load_json(calp)["data"]
    dec = d.get("decision", {})
    rates = dec.get("seconds_per_shot", {})
    src = os.path.relpath(calp, ROOT)
    if d.get("run") != 2:
        return "kraus", mode_default, rates, (f"{src} is the run-1 record (no P4a): kraus; the run-1 mode decision is "
                                              "superseded by prompts/33a R1 (cuStateVec)")
    rep = "rm" if dec.get("p4a_pass") else "kraus"
    if rep != dec.get("production_representation"):
        raise SystemExit(f"{src}: production_representation {dec.get('production_representation')} disagrees with P4a")
    mode = dec.get("mode_by_representation", {}).get(rep) or mode_default
    if ctx.device != "GPU":
        mode = "cpu"
    return rep, mode, rates, f"{src} run 2 decision: {rep} (P4a {'PASS' if dec.get('p4a_pass') else 'FAIL'})"


def _rate_of(rates, rep, mode):
    v = (rates.get(rep) or {}).get(mode)
    return float(v) if v else None


def _c2_run_record(P, r0, man, clb, cid, device, meas, scale_shots, like_for_like, f0, spec, family):
    """Per-run observables of one arm (prompts/33a step C4): the garbage structure, accepted / distinct / hits /
    rejections / round trip (P6), and P7': K1 measured values, Poisson probabilities scaled to 1e5, the z table
    of the weight and every marginal against the device strings, and comparison_power."""
    obs = arm_observables(P, r0, man, clb, int(man["twoB"]))
    Nn = r0["shots_done"]
    a_cnt, hits = obs["accepted"], obs["reference_hits"]
    scale = scale_shots / Nn if Nn else 0.0
    exp_acc, exp_hits = a_cnt * scale, hits * scale
    dev_rate = meas["accepted"] / meas["shots"]
    exp_dev = Nn * dev_rate
    z = ST.structure_compare(obs["structure"], device) if Nn else {"evaluated": False, "reason": "no shots"}
    obs.update({
        "circuit": cid, "family": family, "shots": Nn,
        "t2_convention": spec.description["t2_convention"], "representation": spec.description["representation"],
        "scaled_to_1e5": {"accepted": exp_acc, "reference_hits": exp_hits},
        "measured_K1": {**meas, "mean_hamming_weight": device.get("mean_hamming_weight"),
                        "se_mean_hamming_weight": device.get("se_mean_hamming_weight"),
                        "marginals_by_clbit": device.get("marginals_by_clbit"),
                        "structure_source": device.get("source")},
        "P_measured_accepted_under_model": ST.poisson_two_sided(int(meas["accepted"]), exp_acc * meas["shots"] / 1e5)
        if exp_acc > 0 else None,
        "P_measured_accepted_note": None if exp_acc > 0 else "no simulated accepted string: the scaled rate is 0",
        "P_measured_hits_under_model": ST.poisson_two_sided(int(meas["reference_hits"]), exp_hits * meas["shots"] / 1e5),
        "z_vs_K1": z,
        "comparison_power": {"counts": "underpowered" if exp_dev < C2_UNDERPOWERED_BELOW else "adequate",
                             "expected_accepted_at_device_rate": exp_dev,
                             "circuit": "like_for_like" if like_for_like else "different_circuit_variant",
                             "rule": (f"counts underpowered when N_sim x (K1 accepted / K1 shots) < {C2_UNDERPOWERED_BELOW}; "
                                      "like_for_like only for the T3 circuits the device flew (C2_XY4)")},
        "f0_twirled": f0, "seconds_per_shot": None})
    return obs


def run_c2_cell(ctx):
    """A class-2 production cell (prompts/33a step C): the Kraus reference arm first (20 % of the sampling
    window, both K1 circuits, equal shots, chunk 128; information: the in-cell RM-vs-Kraus check), then the
    production arm (C2_CAL run 2's representation: RM, or Kraus if P4a failed) for the rest, equal shots per
    run.  Observables: garbage structure, accepted / hits, round trip, and P7' against the K1 strings."""
    from campaign33 import add_table
    cell, family, convs = C2_CELLS[ctx.token]
    P = A.Physics(with_sectors=False)
    rec = load_record()
    prod, mode, rates, dec_src = c2_cal_decision(ctx)
    if ctx.args.gpu_mode not in ("auto", "policy") and ctx.device == "GPU":
        mode = ctx.args.gpu_mode
    ref_rep = "kraus"
    if ctx.dry:
        # a 21-qubit noisy shot costs minutes on the laptop CPU (Kraus more than PTA): the dry run checks the path
        # with the Pauli-twirled representation standing in for both arms, 1 shot per run (labelled)
        ctx.notes.append(f"dry run: PTA stands in for both arms (kraus reference, {prod} production), 1 shot per run "
                         "-- a path check, not the CI's channels")
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
    like = cell == "I-XY4"
    t_b = time.time()
    specs = {}
    for conv in convs:
        for rep in sorted({ref_rep, prod}):
            specs[(rep, conv)] = N.ibm_spec(rec, cell, "pta" if ctx.dry else rep, conv, ratio, eps)
    ctx.phases["noise_model_build_s"] = time.time() - t_b
    clb = {cid: clbit_physical(circs[cid][0]) for cid in K1_IDS}
    device = {cid: k1_device_structure(cid, clb[cid]) for cid in K1_IDS}
    meas = {cid: k1_measured(cid) for cid in K1_IDS}
    prereg = load_json("data/hardware/K1_2x3_prep/prereg_99035ef05c36019e.json")["circuits"]
    # ---- the sampling window and the two arms
    rem = ctx.remaining()
    window = None if rem is None else 0.75 * max(0.0, rem)
    t_w = time.time()
    rk = _rate_of(rates, "kraus", mode)
    arms = {}
    for arm, rep in (("kraus_reference", ref_rep), ("production", prod)):
        t_a = time.time()
        if arm == "kraus_reference":
            deadline = None if window is None else t_w + C2_KRAUS_REF_SHARE * window
            budget = None if window is None else C2_KRAUS_REF_SHARE * window
            rate = rk
            chunk = C2_REF_CHUNK
            if budget is not None and rate:
                while chunk > 8 and chunk * rate * len(runs) > 0.9 * budget:
                    chunk //= 2
            n = 1 if ctx.dry else ctx.scaled(C2_TARGET_PER_CIRCUIT)
            phis, min_rounds = (1.0,), 1
            rule = (f"deadline-stopped at {C2_KRAUS_REF_SHARE:.0%} of the sampling window, equal shots per run at round "
                    f"boundaries, chunk {chunk} (128, halved while one round at the C2_CAL Kraus rate {rate} s/shot "
                    "would not fit 0.9 of the arm's budget); >= 1 round always")
        else:
            deadline = None if window is None else t_w + window
            left = None if deadline is None else max(0.0, deadline - time.time())
            rate = _rate_of(rates, prod, mode) or (arms["kraus_reference"]["seconds_per_shot"] if prod == "kraus" else None)
            if ctx.dry:
                n = 1
            elif left is not None and rate:
                n = max(1, min(ctx.scaled(C2_TARGET_PER_CIRCUIT), int(0.95 * left / (rate * len(runs)))))
            else:
                n = ctx.scaled(C2_TARGET_PER_CIRCUIT)
            chunk = 1 if ctx.dry else C2_CHUNK
            phis, min_rounds = SM.PHI, None
            rule = (f"equal shots per run = 0.95 x the window left / (rate {rate} s/shot x {len(runs)} runs), capped at "
                    f"{C2_TARGET_PER_CIRCUIT}; chunks <= {C2_CHUNK} at the gate_CV prefix points; deadline-stopped at a "
                    "round boundary (equal shots kept)")
        cts, sims, kws = [], [], []
        for cid, conv in runs:
            spec = specs[(rep, conv)]
            cts.append(spec.apply(circs[cid][0]))
            sim, kw = simulator(ctx, spec.noise_model, mode)
            sims.append(sim)
            kws.append(kw)
        labels = [f"{cid}|{conv}" for cid, conv in runs]
        off = 50 if arm == "kraus_reference" else 0
        s = SM.Sampler(sims, ctx.s0, chunk, deadline, log=ctx.log, rate_hint=rate,
                       min_rounds=(1 if ctx.dry else 0) if min_rounds is None else min_rounds, phis=phis)
        res, info = s.run(cts, [n] * len(runs), labels, off)
        ctx.oom += info["oom_retries"]
        per = {}
        for (cid, conv), r0, kw in zip(runs, res, kws):
            spec = specs[(rep, conv)]
            f0 = N.f0_ibm(circs[cid][0], specs[(ref_rep, conv)], circs[cid][1]["logical_to_physical"],
                          circs[cid][1]["reference_bits"])
            rr = _c2_run_record(P, r0, circs[cid][1], clb[cid], cid, device[cid], meas[cid], 1e5, like, f0, spec, family)
            rr.update({"simulator_options": kw, "noise": spec.description,
                       "prereg_expected_hits_1e5": prereg[cid]["expected_reference_hits"]})
            per[f"{cid}|{conv}"] = rr
        done = [r["shots_done"] for r in res]
        arms[arm] = {"representation": spec.description["representation"], "planned_representation": rep,
                     "mode": mode, "target_shots_per_run": n, "chunk": chunk, "rule": rule,
                     "shots_per_circuit": {lab: d for lab, d in zip(labels, done)},
                     "equal_shots": len(set(done)) <= 1, "per_run": per, "calls": info["calls"],
                     "stopped": info["stopped"], "warmup": info["warmup"], "seconds": time.time() - t_a,
                     "seconds_per_shot": info["seconds_per_shot"]}
        ctx.log(f"{arm} ({rep}): shots per run {done}, {info['seconds_per_shot']} s/shot")
    ctx.phases["sampling_and_decoding_s"] = time.time() - t_w
    pr = arms["production"]
    # ---- the in-cell RM-vs-Kraus check (information)
    incell = {}
    for lab in pr["per_run"]:
        if prod == "kraus":
            incell[lab] = {"evaluated": False, "reason": "production is Kraus (P4a failed or no run-2 decision)"}
        else:
            incell[lab] = ST.structure_compare(pr["per_run"][lab]["structure"],
                                               arms["kraus_reference"]["per_run"][lab]["structure"])
    # ---- criteria
    allruns = [v for a in arms.values() for v in a["per_run"].values()]
    ctx.physics("P6 decoder round trip on every accepted string (both arms)",
                {f"{a}:{k}": v["roundtrip"]["mismatches"] for a, d in arms.items() for k, v in d["per_run"].items()},
                "0 mismatches", all(v["roundtrip"]["ok"] for v in allruns))
    have = all(("comparison_power" in v and v["z_vs_K1"].get("evaluated") and "accepted" in v["scaled_to_1e5"])
               for v in pr["per_run"].values()) and bool(arms["kraus_reference"]["per_run"])
    ctx.physics("P7' K1 comparison per run: Poisson probabilities of the measured 58 / 45 accepted and 0 / 0 hits, the z "
                "table of the mean Hamming weight and every marginal, comparison_power; Kraus reference arm present",
                {k: v["comparison_power"]["counts"] + "/" + v["comparison_power"]["circuit"] for k, v in pr["per_run"].items()},
                "fields present (no threshold)", have)
    minimum = C2_MIN_SHOTS["rm" if prod == "rm" else "kraus"]
    pmin = min(pr["shots_per_circuit"].values()) if pr["shots_per_circuit"] else 0
    ctx.min_shots_ok = (pmin >= minimum) if not ctx.dry else True
    ctx.no_shots = any(v["shots"] == 0 for v in allruns)
    if pmin < pr["target_shots_per_run"] or not ctx.min_shots_ok:
        ctx.shots_reduced_to = {"production": pr["shots_per_circuit"],
                                "minimum_per_circuit": minimum, "kraus_reference": arms["kraus_reference"]["shots_per_circuit"]}
    tot = sum(v["shots"] for v in allruns)
    ctx.data["seconds_per_shot"] = pr["seconds_per_shot"]
    ctx.data.update({"cell": cell, "family": family, "conventions": list(convs),
                     "representation_used": prod, "representation_source": dec_src, "arms": arms,
                     "per_run": pr["per_run"], "shots_per_circuit": pr["shots_per_circuit"],
                     "minimum_shots_per_circuit": minimum, "rm_vs_kraus_in_cell": incell,
                     "K1_device_structure": device, "shots_total": tot,
                     "information_only": cell == "I-XY4", "f_point_estimate_claimed": False,
                     "class2_channels": "depolarizing + T1/T2 relaxation (gates; delays in idle-aware cells) + readout"
                                        + (" + coherent Rx(eps) after x" if cell == "I-COH" else ""),
                     "note": ("prompts/33a R3: the 1e5-per-circuit target is withdrawn; the cell reports the simulated "
                              "garbage structure against the K1 strings (like-for-like only in C2_XY4) and underpowered "
                              "count comparisons; no f point value is claimed")})
    rows = []
    for arm, d in arms.items():
        for k, v in d["per_run"].items():
            st = v["structure"]
            rows.append([arm, k, v["representation"], v["shots"], st.get("mean_hamming_weight"),
                         v["measured_K1"]["mean_hamming_weight"], v["z_vs_K1"].get("z_mean_hamming_weight"),
                         v["z_vs_K1"].get("max_abs_z_marginal"), v["accepted"], v["reference_hits"],
                         v["P_measured_accepted_under_model"], v["comparison_power"]["counts"],
                         v["roundtrip"]["mismatches"]])
    add_table(ctx, f"{cell} on {family}: arms vs the K1 strings",
              ["arm", "run", "representation", "shots", "mean weight", "K1 mean weight", "z weight", "max |z| marginal",
               "accepted", "hits", "P(K1 accepted | model)", "counts power", "roundtrip mismatches"], rows)
    add_table(ctx, "In-cell RM vs Kraus (information)", ["run", "z mean weight", "max |z| marginal", "pass"],
              [[k, v.get("z_mean_hamming_weight"), v.get("max_abs_z_marginal"), v.get("pass")] for k, v in incell.items()])


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
SIZING_JSON = os.path.join(ROOT, "data", "campaign33", "sizing_33a.json")
SIZING_JSON_DRY = os.path.join(ROOT, "data", "campaign33", "dryrun", "sizing_33a.json")
PLAN_SHARE, QUOTA_SHARE = 0.6, 0.75          # the driver's sampling shares (prompts/33a step D3: unchanged)


def parse_f_token(token):
    """C4_F4_B0a -> ('F4', 0, 'a')."""
    parts = token.split("_")
    f, sec = parts[1], parts[2]
    twoB = 0 if sec.startswith("B0") else 2
    half = sec[2:] or None
    return f, twoB, half


def run_key(token):
    """C4_F1_B0 -> F1_B0 (the run name of prompts/33a step D: the content-named JSONs are C33_<run>...)."""
    return token[3:] if token.startswith("C4_F") else token


def f_run_spec(run, idx=None) -> dict:
    """Scenario, family (CHOSEN / S3FAMILY resolved), kind, fixed tier and the sector's circuits of an F run."""
    idx = C.load_index() if idx is None else idx
    fkey, twoB, half = parse_f_token("C4_" + run)
    sid, fam, kind, fixed_tier = F_SPECS[fkey]
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
    return {"run": run, "token": "C4_" + run, "fkey": fkey, "twoB": twoB, "half": half,
            "sector": "B=0" if twoB == 0 else "B=1", "scenario": sid, "family": fam, "family_rule": fam_rule,
            "kind": kind, "fixed_tier": fixed_tier, "all_ids": all_ids,
            "share": PLAN_SHARE if kind == "plan" else QUOTA_SHARE}


def f_run_plan(ctx, spec, ids=None) -> dict:
    """The per-circuit shots of an F run at full scale (before any dry-run scaling): the plan of record at the
    run's tier (plan runs) or the S3-quota half (2e5 per sector / circuits, halved), and the f = 0.10 plan."""
    ids = spec["all_ids"] if ids is None else ids
    tier = tier_reason = None
    if spec["kind"] == "plan":
        tier, tier_reason = plan_tier(ctx, spec["scenario"], spec["fixed_tier"])
        plan_full, _meta = cv_plan(tier, spec["sector"])
        want = {c: int(plan_full[c]) for c in ids}
        plan_f010 = None
    else:
        u = PRODUCTION_SHOTS_PER_SECTOR // len(spec["all_ids"])
        h = u // 2 if spec["half"] == "a" else u - u // 2
        want = {c: int(h) for c in ids}
        plan_f010 = {c: int(v) for c, v in cv_plan(0.10, spec["sector"])[0].items() if c in ids}
    return {"want": want, "tier": tier, "tier_reason": tier_reason, "plan_f010": plan_f010}


def sizing_path(dry):
    return SIZING_JSON_DRY if dry else SIZING_JSON


def load_sizing(ctx):
    p = sizing_path(ctx.dry)
    return (load_json(p), os.path.relpath(p, ROOT)) if os.path.exists(p) else (None, os.path.relpath(p, ROOT))


def frun_criteria(P, sec, kind, tier, cert, cv, fc, part_info=None):
    """The physics criteria of an F run (prompts/33 P13 / P14), shared by the in-job analysis and the assembly
    of a split run: [(name, value, threshold, passed, gating)].  A part of a split run (part_info) gates only on
    the variational bound (a STOP condition on any subset of shots); the rest is information ('part i of n')."""
    out = []
    cv0_ok = cv["cv0"]["ok"] if cv else True
    var_ok = cert["variational_ok"] and (cv["cv0"]["variational_ok"] if cv else True)
    if part_info is None:
        out.append(("P13 E_R >= E0 - 1e-9 everywhere, prefixes nested (CV0), E0 inside the certificate of ruling 2 at N",
                    {"variational": var_ok, "cv0": cv0_ok, "E0_inside": cert["E0_inside"], "certificate": cert["type"]},
                    "all true", var_ok and cv0_ok and cert["E0_inside"], True))
    else:
        out.append((f"P13 (part {part_info}) E_R >= E0 - 1e-9 on this part's shots (CV0 and the certificate are read at "
                    "assembly on the merged parts)", {"variational": var_ok, "E0_inside_information": cert["E0_inside"]},
                    "variational", var_ok, True))
    pk = fc["pooled_k1"]
    lo = pk["f_hat_ideal_ci"][0] if pk else None
    p14 = None
    if kind == "plan":
        gating = lo is not None and tier is not None and lo >= tier and part_info is None
        name = (f"P14 recall of S999 >= 0.9 on B_all at N ({'criterion' if gating else 'information'}: f_hat_ideal "
                f"lower end {lo} vs tier {tier}" + (f"; part {part_info}" if part_info else "") + ")")
        if gating:
            out.append((name, cert["recall_S999"], ">= 0.9", cert["recall_S999"] >= 0.9, True))
        else:
            p14 = {"recall_S999": cert["recall_S999"], "reason": name}
    return out, p14, var_ok


def frun_readout(P, spec, pre, want, done, plan_s, per_counts, acc_counts, mans, eq, B, tier, part_info=None,
                 kind=None):
    """The analysis of an F run on order-kept chunks (prompts/33 P13-P15; prompts/33a: the same function reads part 1
    in-job and the merged parts at assembly).  want: the per-circuit plan the run samples in full; done: shots done."""
    sec, kind = spec["sector"], kind or spec["kind"]
    ids = list(want)
    Et = A.e_tol(P, sec)
    out = {"E_tol": Et}

    def on_bounds(plan):
        return all(SM.rnd(phi * plan[c]) in pre.bounds[c] for c in ids for phi in SM.PHI)
    full = all(done[c] == want[c] for c in ids)
    if part_info is not None:
        out["cv"] = None
        out["plan_prefix"] = f"part {part_info}: CV0-CV5 are read at assembly on the merged parts (validation/C33_{spec['run']}.json)"
    elif kind == "plan":
        if full and on_bounds(want):
            out["cv"] = A.cv_reading(P, sec, pre, want, Et["value"], eq=eq, with_random=True)
            out["plan_prefix"] = "the whole run (plan of record)"
        else:
            out["cv"] = None
            out["plan_prefix"] = ("incomplete: the budget cut the plan of record (shots_reduced_to); the CV reading "
                                  "is not evaluated on a partial plan")
    else:
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
    fc = A.fcell_stats(P, per_counts, mans, kappa=1.0)
    out["clean_fraction"] = fc
    out["bootstrap_at_N"] = A.bootstrap_point(P, sec, [acc_counts[c] for c in ids], B, 33)
    crit, p14, var_ok = frun_criteria(P, sec, kind, tier, cert, out["cv"], fc, part_info)
    if p14:
        out["P14_information"] = p14
    if kind == "plan":
        out["CV1_CV5"] = {k: (v.get("ok") if isinstance(v, dict) else None)
                          for k, v in (out["cv"]["criteria"] if out.get("cv") else {}).items() if k.startswith("CV")}
    else:
        out["P15"] = ("evaluated at assembly on the merged a + b halves (2e5 shots per sector): "
                      "validation/C33_campaign.json")
    return out, crit, var_ok, pt


def chunks_accepted(P, res, twoB) -> dict:
    """{cid: [{start, shots, seed, accepted {full-basis index: n}, rejected}]} -- what a split run's assembly needs
    to rebuild the order-kept prefixes on the laptop (the results npz stays in the job directory)."""
    out = {}
    for r in res:
        rows = []
        for ch in r["chunks"]:
            acc, rej = sparse_accepted(P, ch["counts"], twoB)
            rows.append({"start": int(ch["start"]), "shots": int(ch["shots"]), "seed": int(ch["seed"]),
                         "accepted": acc, "rejected": rej})
        out[r["label"]] = rows
    return out


def run_frun(ctx, part=None):
    """An F run (prompts/33 1.5).  prompts/33a step D: the F token runs part 1 of n (n and the per-circuit
    ranges from data/campaign33/sizing_33a.json; n = 1 as prompts/33 sized it when that file or the run is
    absent); a C4_PART_NN slot runs part i >= 2 from its ci/parts file (`part`)."""
    from campaign33 import add_table
    P = A.Physics()
    idx = C.load_index()
    run = part["run"] if part else run_key(ctx.token)
    spec = f_run_spec(run, idx)
    sid, fam, kind, sec, twoB, half = (spec["scenario"], spec["family"], spec["kind"], spec["sector"], spec["twoB"],
                                       spec["half"])
    sizing_note = None
    if part is None:
        sizing, spath = load_sizing(ctx)
        entry = (sizing or {}).get("runs", {}).get(run)
        if entry and int(entry["parts"]) > 1:
            part = entry["part_descriptors"][0]
            sizing_note = f"part 1 of {entry['parts']} per {spath} (written from {sizing.get('from')})"
        elif entry:
            sizing_note = f"{spath}: n = 1 for {run} (the run fits one job)"
        else:
            sizing_note = (f"{spath} absent or without {run} at run time: n = 1, sized as prompts/33 sized it "
                           "(prompts/33a step D2)")
        ctx.notes.append(sizing_note)
    if part is not None:
        ids = list(part["ranges_by_circuit"])
        tier, tier_reason = part.get("tier"), part.get("tier_reason")
        plan_full = {c: int(part["plan_shots_by_circuit"][c]) for c in ids}
        chunk = int(part["chunk"])
        ranges = {c: [int(x) for x in part["ranges_by_circuit"][c]] for c in ids}
        plans = [SM.part_plan(plan_full[c], chunk, ranges[c][0], ranges[c][1]) for c in ids]
        want = {c: ranges[c][1] - ranges[c][0] for c in ids}
        target = plan_full
        plan_f010 = part.get("plan_f010_by_circuit")
        part_info = f"{part['part']} of {part['parts']}"
    else:
        ids = select_ids(ctx, spec["all_ids"], tuple(FCELL_SHOTS))
        pl = f_run_plan(ctx, spec, ids)
        tier, tier_reason = pl["tier"], pl["tier_reason"]
        want = {c: ctx.scaled(pl["want"][c]) for c in ids}
        target = want
        plan_f010 = pl["plan_f010"]
        chunk, plans, part_info = SM_chunk(ctx), None, None
    sm = N.quantinuum_spec(sid)
    mode, mode_src = gpu_mode_for(ctx, "C4_FCELLS_A")
    ctx.data["gpu_mode_used"] = mode
    ctx.data["gpu_mode_source"] = mode_src
    sim, kw = simulator(ctx, sm.noise_model, mode)
    circs = {c: C.load_circuit(fam, c) for c in ids}
    mans = {c: C.load_manifest(fam, c) for c in ids}
    t_s = time.time()
    res, info = sample(ctx, sim, [sm.apply(circs[c]) for c in ids], [want[c] for c in ids], ids,
                       circuit_offset=0, share=spec["share"], max_chunk=chunk,
                       plans=None if plans is None else plans)
    ctx.phases["sampling_s"] = time.time() - t_s
    done = {r["label"]: r["shots_done"] for r in res}
    ctx.data["seconds_per_shot"] = info["seconds_per_shot"]
    full = all(done[c] == want[c] for c in ids)
    if not full:
        ctx.min_shots_ok = False
        ctx.shots_reduced_to = {c: done[c] for c in ids if done[c] < want[c]}
    ctx.no_shots = any(done[c] == 0 for c in ids)
    # ---- CV3 extra samples (NAT-O0 plan runs in one job only, and only if the budget covers them in full)
    eq = None
    if part_info is not None:
        cv3_status = ("not_evaluated in a part: the equal-shots sample is its own slot content (cv3) when "
                      "data/campaign33/sizing_33a.json assigns one; read at assembly")
    elif not (kind == "plan" and fam == "NAT-O0"):
        cv3_status = "not_evaluated: not a NAT-O0 plan-of-record run"
    else:
        cv3_status = None
    if cv3_status is None:
        r_eq, r_k5, N_eq, k5_ids, cv3_status = cv3_sample(ctx, sim, sm, circs, mans, ids, want, twoB, sec, idx,
                                                          info["seconds_per_shot"] or 0.0)
        if r_eq is not None:
            eq = (A.Prefixes(P, twoB, r_eq), N_eq, A.Prefixes(P, twoB, r_k5))
    t_a = time.time()
    pre = A.Prefixes(P, twoB, res)
    per_counts = {r["label"]: totals(r) for r in res}
    acc_counts = {c: sparse_accepted(P, per_counts[c], twoB)[0] for c in ids}
    plan_s = None
    if kind != "plan":
        plan_s = {c: ctx.scaled(plan_f010[c]) for c in ids} if part is None else plan_f010
    t_b = time.time()
    rd, crit, var_ok, pt = frun_readout(P, spec, pre, want, done, plan_s, per_counts, acc_counts, mans, eq,
                                        ctx.args.bootstrap, tier, part_info=part_info)
    ctx.phases["bootstrap_and_readout_s"] = time.time() - t_b
    out = {"run": run, "scenario": sid, "family": fam, "family_rule": spec["family_rule"], "kind": kind, "half": half,
           "sector": sec, "plan_tier": tier, "plan_tier_reason": tier_reason, "shots_requested": want,
           "shots_done": done, "full": full, "cv3_status": cv3_status, "noise": sm.description,
           "chunks": {r["label"]: chunk_record(r) for r in res}, "sampling": {k: v for k, v in info.items()},
           "chunk": chunk, "sizing_note": sizing_note}
    out.update(rd)
    out["accepted_counts_by_circuit"] = acc_counts
    out["rejected_by_circuit"] = {c: sparse_accepted(P, per_counts[c], twoB)[1] for c in ids}
    out["reference_hits_by_circuit"] = {c: int(per_counts[c].get(int(mans[c]["reference_int"]), 0)) for c in ids}
    if part is not None:
        out["part"] = {"part": int(part["part"]), "parts": int(part["parts"]), "ranges_by_circuit": part["ranges_by_circuit"],
                       "plan_shots_by_circuit": target, "chunk": chunk, "plan_f010_by_circuit": plan_f010,
                       "source": part.get("source") or sizing_note, "from": part.get("from")}
        out["chunks_accepted"] = chunks_accepted(P, res, twoB)
    out["results_npz"] = save_npz(ctx, "chunks", P, res, lambda c: twoB)
    ctx.phases["analysis_s"] = time.time() - t_a
    for name, value, thr, passed, _g in crit:
        ctx.physics(name, value, thr, passed)
    if not var_ok:
        ctx.notes.append("STOP (prompts/33 section 8): E_R < E0 - 1e-9 (variational violation)")
    ctx.data["frun"] = out
    ctx.seeds_recorded = all(all("seed" in ch for ch in v) for v in out["chunks"].values())
    cert = rd["at_N"]["certificate"]
    pk = rd["clean_fraction"]["pooled_k1"]
    add_table(ctx, f"{ctx.token}: {sid} x {fam}, {sec}, {kind}" + (f" half {half}" if half else "")
              + (f", part {part_info}" if part_info else ""),
              ["shots", "|B_all|", "E_R - E0", "certificate", "width", "E0 inside", "recall S999", "W",
               "f_hit (k=1)", "f_hat_ideal 95 %"],
              [[rd["at_N"]["shots"], pt["B_all_size"], cert["E_R_minus_E0"], cert["type"], cert["width"],
                cert["E0_inside"], cert["recall_S999"], cert["W"], pk["f_hit"] if pk else None,
                pk["f_hat_ideal_ci"] if pk else None]])
    if rd.get("cv"):
        cr = rd["cv"]["criteria"]
        add_table(ctx, "CV0-CV5 (information; the plan-of-record check is CV_2x3_plan)",
                  ["CV0", "CV1", "CV2", "CV3", "CV4", "CV5"],
                  [[rd["cv"]["cv0"]["ok"]] + [cr.get(k, {}).get("ok") if isinstance(cr.get(k), dict) else None
                                              for k in ("CV1", "CV2", "CV3", "CV4", "CV5")]])
    return out


def cv3_sample(ctx, sim, sm, circs, mans, ids, want, twoB, sec, idx, rate, budget_share=0.75, force=False):
    """The CV3 equal-shots sample (N_eq per k <= 4 circuit) and the k = 5 circuits; None when the budget does not
    cover it in full (force: a cv3 slot runs it regardless and records what it reached)."""
    n_sec = sum(want.values())
    N_eq = int(math.ceil(n_sec / len(ids) / 100.0) * 100) if not ctx.dry else max(2, int(math.ceil(n_sec / len(ids))))
    k5_all = [c for c in idx["families"].get("NAT-O0-k5", {}).get("circuits", []) if sector_of(c) == twoB]
    k5_ids = [f"{sec.replace('=', '')}_ref{int(mans[c]['reference']):02d}_k5" for c in ids if int(mans[c]["k"]) == 1]
    k5_ids = [c for c in k5_ids if c in k5_all]
    extra = N_eq * (len(ids) + len(k5_ids))
    rem = budget_share * (ctx.remaining() or 1e9)
    if not k5_ids:
        return None, None, N_eq, k5_ids, "not_evaluated: no NAT-O0-k5 circuits frozen for this sector"
    if not force and rate * extra > rem:
        return None, None, N_eq, k5_ids, (f"not_evaluated: the equal-shots ({N_eq} per circuit) and k = 5 samples need "
                                          f"{extra} shots ~ {rate * extra:.0f} s, more than the {rem:.0f} s left (budget)")
    t_e = time.time()
    r_eq, _i_eq = sample(ctx, sim, [sm.apply(circs[c]) for c in ids], [N_eq] * len(ids), ids,
                         circuit_offset=100, rate_hint=rate or None)
    k5c = [sm.apply(C.load_circuit("NAT-O0-k5", c)) for c in k5_ids]
    r_k5, _i_k5 = sample(ctx, sim, k5c, [N_eq] * len(k5_ids), k5_ids, circuit_offset=200, rate_hint=rate or None)
    ctx.phases["cv3_sampling_s"] = time.time() - t_e
    if all(r["shots_done"] == N_eq for r in r_eq + r_k5):
        return r_eq, r_k5, N_eq, k5_ids, f"evaluated at N_eq = {N_eq} per circuit (k <= 4) + {len(k5_ids)} k = 5 circuits"
    return (r_eq, r_k5, N_eq, k5_ids, "not_evaluated: the equal-shots sample was cut by the deadline") if force else \
        (None, None, N_eq, k5_ids, "not_evaluated: the equal-shots sample was cut by the deadline")


# =========================================================================== prompts/33a step D: the part slots
def load_part(ctx):
    """The slot's content: --parts-file, else ci/parts/<TOKEN>.json in the requested commit."""
    p = ctx.args.parts_file or TK.part_file(ctx.token)
    p = p if os.path.isabs(p) else os.path.join(ROOT, p)
    return (load_json(p), os.path.relpath(p, ROOT)) if os.path.exists(p) else (None, os.path.relpath(p, ROOT))


def part_copy_name(part):
    """The content-named copy of a slot's JSON (prompts/33a step D1)."""
    c = part["content"]
    if c == "frun":
        return f"C33_{part['run']}_part{int(part['part'])}of{int(part['parts'])}"
    if c == "cv3":
        return f"C33_{part['run']}_cv3"
    return f"C33_fcells_part{int(part['part'])}of{int(part['parts'])}"


def run_part(ctx):
    """C4_PART_NN: run the content of ci/parts/C4_PART_NN.json (frun part i of n | fcells | cv3) and name a copy
    of the JSON after the content."""
    part, path = load_part(ctx)
    ctx.data["part_file"] = path
    if part is None:
        ctx.notes.append(f"no slot content: {path} is absent in this commit (a slot runs only what "
                         "scripts/campaign33_resize.py assigned to it)")
        ctx.R.add("P0 slot content present", path, "ci/parts/<TOKEN>.json exists", False)
        ctx.min_shots_ok = False
        return
    want_idx = TK.token_index(ctx.token)
    ok_slot = int(part.get("seed_token_index", -1)) == want_idx and part.get("slot", ctx.token) == ctx.token
    ctx.R.add("P0 slot content written for this slot (seed_token_index = the slot's own index)",
              {"seed_token_index": part.get("seed_token_index"), "slot_index": want_idx, "content": part.get("content")},
              "equal", ok_slot)
    ctx.data["part"] = {k: v for k, v in part.items() if k not in ("ranges_by_circuit",)}
    name = part_copy_name(part)
    ctx.copy_to = name
    rname = name if part["content"] == "cv3" else name[:name.rindex("of")]       # C33_<run>_part<i>
    ctx.results_dir = os.path.join(ROOT, "results", "campaign33", "dryrun" if ctx.dry else "", rname)
    os.makedirs(ctx.results_dir, exist_ok=True)
    if not ok_slot:
        ctx.min_shots_ok = False
        return
    if part["content"] == "frun":
        run_frun(ctx, part=part)
    elif part["content"] == "fcells":
        run_fcell_slot(ctx, part)
    elif part["content"] == "cv3":
        run_cv3_slot(ctx, part)
    else:
        raise SystemExit(f"unknown slot content {part['content']}")


def run_fcell_slot(ctx, part):
    """Dropped f-cells as a slot's content: the same run_one_fcell as C4_FCELLS_A/B, one cell after another."""
    from campaign33 import add_table
    P = A.Physics()
    mode, mode_src = gpu_mode_for(ctx, "C4_FCELLS_A")
    ctx.data["gpu_mode_used"], ctx.data["gpu_mode_source"] = mode, mode_src
    deadline = ctx.sampling_deadline(QUOTA_SHARE)
    out, dropped, rate = {}, [], None
    t_c = time.time()
    for i, (sid, fam) in enumerate(part["cells"]):
        nshots = sum(ctx.scaled(v) for v in FCELL_SHOTS.values())
        if deadline is not None and rate is not None and time.time() + rate * nshots > deadline:
            dropped.append(f"{sid}|{fam}")
            continue
        r = run_one_fcell(ctx, P, sid, fam, i, deadline, rate_hint=rate)
        out[f"{sid}|{fam}"] = r
        rate = (time.time() - t_c) / max(1, sum(v["shots"] for v in out.values()))
    ctx.phases["cells_s"] = time.time() - t_c
    ctx.data["seconds_per_shot"] = rate
    ctx.data["cells"] = {k: {kk: vv for kk, vv in v.items() if kk != "noise"} for k, v in out.items()}
    ctx.data["cells_dropped"] = dropped
    ctx.min_shots_ok = not dropped and all(v["complete"] for v in out.values())
    ctx.no_shots = not out or any(v["shots"] == 0 for v in out.values())
    if dropped:
        ctx.shots_reduced_to = f"{len(out)} of {len(part['cells'])} cells"
    add_table(ctx, "f-cells (slot)", ["scenario", "variant", "shots", "f_hit (k=1 pooled)", "f_hit 95 %"],
              [[v["scenario"], v["family"], v["shots"], v["stats"]["pooled_k1"]["f_hit"],
                v["stats"]["pooled_k1"]["f_hit_ci"]] for v in out.values()])


def run_cv3_slot(ctx, part):
    """The CV3 equal-shots sample of a split plan run as a slot's content: the totals at N_eq per circuit (k <= 4)
    and per k = 5 circuit, read at assembly."""
    P = A.Physics()
    idx = C.load_index()
    spec = f_run_spec(part["run"], idx)
    ids = list(part["plan_shots_by_circuit"])
    want = {c: int(part["plan_shots_by_circuit"][c]) for c in ids}
    sm = N.quantinuum_spec(spec["scenario"])
    mode, mode_src = gpu_mode_for(ctx, "C4_FCELLS_A")
    ctx.data["gpu_mode_used"], ctx.data["gpu_mode_source"] = mode, mode_src
    sim, _kw = simulator(ctx, sm.noise_model, mode)
    circs = {c: C.load_circuit(spec["family"], c) for c in ids}
    mans = {c: C.load_manifest(spec["family"], c) for c in ids}
    r_eq, r_k5, N_eq, k5_ids, status = cv3_sample(ctx, sim, sm, circs, mans, ids, want, spec["twoB"], spec["sector"],
                                                  idx, 0.0, force=True)
    full = r_eq is not None and all(r["shots_done"] == N_eq for r in r_eq + r_k5)
    ctx.min_shots_ok = bool(full)
    ctx.no_shots = r_eq is None
    tb = spec["twoB"]
    ctx.data["cv3"] = {"run": part["run"], "N_eq": N_eq, "k5_ids": k5_ids, "status": status, "full": full,
                       "eq_accepted_by_circuit": {r["label"]: sparse_accepted(P, totals(r), tb)[0] for r in (r_eq or [])},
                       "eq_rejected_by_circuit": {r["label"]: sparse_accepted(P, totals(r), tb)[1] for r in (r_eq or [])},
                       "k5_accepted_by_circuit": {r["label"]: sparse_accepted(P, totals(r), tb)[0] for r in (r_k5 or [])},
                       "k5_rejected_by_circuit": {r["label"]: sparse_accepted(P, totals(r), tb)[1] for r in (r_k5 or [])},
                       "shots_done": {r["label"]: r["shots_done"] for r in (r_eq or []) + (r_k5 or [])},
                       "chunks": {r["label"]: chunk_record(r) for r in (r_eq or []) + (r_k5 or [])}}
    tot = sum(r["shots_done"] for r in (r_eq or []) + (r_k5 or []))
    ctx.data["seconds_per_shot"] = ctx.phases.get("cv3_sampling_s", 0.0) / tot if tot else None


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
