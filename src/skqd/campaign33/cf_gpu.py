"""
C4_CF (prompts/33 1.5, P16/P17): the CF_traj trajectory decomposition redone on the GPU with K = 2000
faulty Pauli trajectories per arm (the CPU run had 720 / 240 / 240 / 120).

Everything physical is gate CF_traj's own code, imported: the A6 channel and its event probabilities,
the trajectory draw, the Pauli insertion, the exact readout convolution and the per-trajectory record
(scripts/cf_trajectories.py), the arm statistics with the bootstrap, the pooled r and the floor check
(scripts/gate_CF_traj.py).  What changes is only where the statevectors are computed (Aer on the GPU,
one trajectory after the other, from in-memory checkpoints) and where the circuit comes from: the
frozen NAT-O0 QPY (qiskit_to_ir of its measurement-free part), whose noise sites are checked against
the Q0P manifest counts exactly as cf_trajectories.cmd_chunk checks them.
"""
from __future__ import annotations

import math
import os
import time

import numpy as np

from . import circuits as C
from . import tokens as TK

ARMS = (("B0_ref25_k1", "depol"), ("B1_ref57_k1", "depol"), ("B0_ref25_k4", "depol"), ("B0_ref25_k1", "xx"))
K_TARGET = 2000
N_CKPT = 48


def _sim(device, threads):
    from qiskit_aer import AerSimulator
    kw = dict(method="statevector", precision="double", fusion_enable=True)
    if device == "GPU":
        kw.update(device="GPU", cuStateVec_enable=True)
    else:
        kw["max_parallel_threads"] = int(threads)
    return AerSimulator(**kw)


def arm_run(ctx, cid, channel, K, seed, deadline):
    import cf_trajectories as cf
    from quantinuum_submit import A6_NOISE

    from skqd import quantinuum_native as qn
    q0p = __import__("json").load(open(os.path.join(cf.CIRC, cid + ".manifest.json")))
    circ = C.unitary_part(C.load_circuit("NAT-O0", cid))
    ir = qn.qiskit_to_ir(circ)
    n = circ.num_qubits
    sites = cf.noise_sites(ir)
    n2 = sum(s[1] == "2q" for s in sites)
    n1 = sum(s[1] == "1q" for s in sites)
    if n2 != int(q0p["counts"]["n_zz"]) or n1 != int(q0p["counts"]["n_phasedx"]):
        raise SystemExit(f"{cid}: noise sites {n2}/{n1} differ from the manifest counts")
    p2, p1 = A6_NOISE["depolarizing_2q_rzz"], A6_NOISE["depolarizing_1q_rx_ry"]
    p10, p01 = A6_NOISE["readout_p1_given_0"], A6_NOISE["readout_p0_given_1"]
    sec = cf.sector_context(q0p)
    sim = _sim(ctx.device, ctx.args.threads)
    t0 = time.time()
    bounds = np.unique(np.linspace(0, len(ir), N_CKPT + 1).astype(int)[:-1])
    ck = np.zeros((len(bounds), 2 ** n), dtype=np.complex128)
    sv = np.zeros(2 ** n, complex)
    sv[0] = 1.0
    ck[0] = sv
    for j in range(1, len(bounds)):
        sv = cf.evolve(sv, ir[bounds[j - 1]:bounds[j]], n, sim)
        ck[j] = sv
    final = cf.evolve(sv, ir[bounds[-1]:], n, sim)
    t_ckpt = time.time() - t0
    p_ideal = np.abs(final) ** 2
    ps = p_ideal[sec["ints"]]
    p_c = ps / ps.sum()
    tail_pos = [int(i) for i in np.nonzero(p_c >= cf.TAIL_P_MIN)[0] if int(i) != sec["ref_pos"]]
    rng = np.random.default_rng(int(seed))
    trajs, draws = cf.draw_trajectories(rng, sites, int(K), p2, p1, channel)
    ctx_d = {"n": n, "ints": sec["ints"], "ref_int": sec["ref_int"], "p10": p10, "p01": p01, "p_c": p_c,
             "tail_pos": tail_pos, "S999": sec["S999"]}
    dist = cf.hamming_distance_table(n, sec["ref_int"])
    recs = []
    t1 = time.time()
    stopped = None
    for i, events in enumerate(trajs):
        if deadline is not None and recs and time.time() + (time.time() - t1) / len(recs) > deadline:
            stopped = {"after": len(recs), "reason": "deadline"}
            break
        first = min(int(e[1]) for e in events)
        c = cf.checkpoint_index(bounds, first)
        start = int(bounds[c])
        gates = cf.insert_paulis(ir, events, start)
        out = cf.evolve(None if start == 0 else ck[c], gates, n, sim)
        rec = cf.trajectory_record(out, events, ctx_d, dist)
        rec.update({"index": i, "first_event_gate_pos": first, "checkpoint": c, "start_gate": start})
        if i == 0:
            full = cf.evolve(None, cf.insert_paulis(ir, events, 0), n, sim)
            rec["crosscheck_from_scratch_max_abs_dprob"] = float(np.max(np.abs(np.abs(full) ** 2 - np.abs(out) ** 2)))
        recs.append(rec)
    wall = time.time() - t0
    placement = cf.aer_error_placement_check()
    p_ideal_post = cf.readout_convolve(p_ideal, n, p10, p01)
    base = {"id": cid, "channel": channel, "chunk": 0, "seed": int(seed), "K": len(recs),
            "git_commit": "campaign33", "git_dirty_scripts_src": None, "workers": 1, "wall_s": wall,
            "n_draws": int(draws), "n_rejected_all_identity": int(draws - len(trajs)),
            "no_error_probability_g0": cf.no_error_probability(n2, n1, p2, p1),
            "readout_survival_reference": cf.readout_survival(q0p["reference_bits"], p10, p01),
            "aer_error_placement_check": placement,
            "sector": {"twoB": int(q0p["twoB"]), "dim": sec["dim"], "ints": [int(x) for x in sec["ints"]],
                       "ref_pos": sec["ref_pos"], "ref_int": sec["ref_int"], "S99": sec["S99"],
                       "S999": sec["S999"], "tail_pos": tail_pos, "tail_p_min": cf.TAIL_P_MIN},
            "ideal": {"p_c": [float(x) for x in p_c], "p_ref_post_readout": float(p_ideal_post[sec["ref_int"]]),
                      "p_sector_vs_verify_json_max_abs": None,
                      "p_ref_vs_manifest_abs": abs(float(p_ideal[sec["ref_int"]]) - float(q0p["p_reference"]))},
            "trajectories": recs}
    # the K actually reached: n_draws covers the full draw of K trajectories; scale the rejection count to
    # the simulated ones is not done -- the draw is recorded as made
    info = {"K_target": int(K), "K": len(recs), "seed": int(seed), "draws": int(draws), "stopped": stopped,
            "checkpoint_s": t_ckpt, "wall_s": wall, "seconds_per_trajectory": (wall - t_ckpt) / max(1, len(recs)),
            "placement_after_gate": placement["error_applied_after_gate"],
            "crosscheck_from_scratch_max_abs_dprob": recs[0].get("crosscheck_from_scratch_max_abs_dprob") if recs else None,
            "p_ref_vs_manifest_abs": base["ideal"]["p_ref_vs_manifest_abs"]}
    return {"chunks": [("in-memory (campaign33 C4_CF)", base)], "base": base, "trajs": recs}, q0p, info


def run(ctx, part=None):
    """The C4_CF token (part None), or a `cf` part content of a C4_PART slot (prompts/33c step 3): K_per_arm
    trajectories per arm, seeds from C4_CF's own base seed with chunk index = the part's seed_chunk_index (>= 1; the
    harvested job 59736866 is index 0), and the compact per-trajectory arrays the assembly merges (merge_cf_parts)."""
    import gate_CF_traj as G
    from quantinuum_submit import A6_NOISE

    from campaign33 import add_table
    from . import stats as ST
    if part is None:
        K = max(2, ctx.scaled(K_TARGET))
        s0, j_seed = ctx.s0, 0
    else:
        K = max(2, ctx.scaled(int(part["K_per_arm"])))
        s0, j_seed = TK.base_seed(CF_TOKEN), int(part["seed_chunk_index"])
        if j_seed < 1:
            raise SystemExit("a cf part must use seed_chunk_index >= 1 (index 0 is the harvested C4_CF job)")
    merge = {}
    arms, infos, stats = {}, {}, {}
    t_all = time.time()
    end = ctx.sampling_deadline(0.8)
    predict = None
    pp = os.path.join(ctx_root(), "data", "quantinuum", "q0p_stages", "predict.json")
    if os.path.exists(pp):
        predict = __import__("json").load(open(pp))
    for i, (cid, ch) in enumerate(ARMS):
        key = cid if ch == "depol" else f"{cid}__xx"
        left = len(ARMS) - i
        dl = None if end is None else time.time() + (end - time.time()) / left
        seed = TK.chunk_seed(s0, i, j_seed, 1)
        arm, man, info = arm_run(ctx, cid, ch, K, seed, dl)
        infos[key] = info
        st = G.arm_statistics(cid, arm, man, A6_NOISE, predict)
        arms[key] = st
        merge[key] = compact_arm(arm, st)
        ctx.log(f"arm {key}: K {info['K']} of {K}, {info['seconds_per_trajectory']:.2f} s/trajectory, "
                f"r(1e-3) {st['stats']['r_d1e-03']['value']:.4f}")
    ctx.phases["trajectories_s"] = time.time() - t_all
    tb = G.delta_tag(G.DELTA_BAR)
    parts = [{"id": c, "f0": arms[c]["f0_prime"], "p_ref": arms[c]["p_ref"], "h": arms[c]["_h"],
              "tv": arms[c]["_tv"], "shots": G.POOL_SHOTS[c]} for c in G.POOL_SHOTS]
    B = int(ctx.args.bootstrap)
    pooled = G.pooled_ratio(parts, n_boot=B)
    new_rnc = pooled[f"r_{tb}"]["ci95"][1]
    old = __import__("json").load(open(os.path.join(ctx_root(), "data", "cf_trajectories", "r_nc.json")))
    per_arm = {k: {"K": infos[k]["K"], "r": v["stats"][f"r_{tb}"], "f_hit": v["stats"]["f_hit"],
                   "b": v["stats"][f"b_{tb}"], "f_ideal": v["stats"][f"f_ideal_{tb}"],
                   "floor_min_feff_over_fideal_S99": v["stats"][f"min_feff_over_fideal_S99_{tb}"],
                   "floor_theorem_S99": v["floor_theorem_S99"]} for k, v in arms.items()}
    fields = all("ci95" in v["r"] for v in per_arm.values()) and "ci95" in pooled[f"r_{tb}"]
    ctx.physics("P16 r per arm with 95 % bootstrap intervals; pooled r; new r_nc = its upper end",
                {k: v["r"]["value"] for k, v in per_arm.items()}, "fields present", fields)
    floor_ok = all(v["floor_min_feff_over_fideal_S99"]["value"] >= G.FLOOR_MIN for v in per_arm.values())
    ctx.physics(f"P17 floor theorem (CF_traj C4'): min_S99 f_eff / f_ideal(1e-3) >= {G.FLOOR_MIN} on every arm",
                {k: v["floor_min_feff_over_fideal_S99"]["value"] for k, v in per_arm.items()}, f">= {G.FLOOR_MIN}",
                floor_ok)
    old_iv = [float(x) for x in old["pooled_r_ci95"]]
    oi = owner_item_r_nc(pooled[f"r_{tb}"]["ci95"], float(old["r_nc"]), old_iv)
    owner_item = oi["fires"]
    if owner_item:
        ctx.notes.append(f"owner item (prompts/33 sections 6 and 8, prompts/33c R4): {oi['why']}; no criterion or "
                         "verdict is changed by this token")
    ctx.data.update({"arms": per_arm, "trajectory_runs": infos, "pooled": pooled, "r_nc_new": new_rnc,
                     "r_nc_old": float(old["r_nc"]), "r_nc_old_pooled_ci95": old_iv,
                     "owner_item_r_nc_outside_old_interval": owner_item, "owner_item_r_nc": oi,
                     "comparison": {k: ST.compare(per_arm[k]["r"]["value"], per_arm[k]["r"]["ci95"],
                                                  None, None) for k in per_arm},
                     "engine": "Aer statevector per trajectory (" + ctx.device + "), checkpoints in memory",
                     "seconds_per_shot": None,
                     "K_target_per_arm": K, "bootstrap_B": B})
    if part is not None:
        ctx.data.update({"cf_part": {k: part.get(k) for k in ("part", "parts", "K_per_arm", "seed_chunk_index", "token",
                                                              "slot", "seed_token_index", "sizing")},
                         "merge_arrays": merge, "seeds_by_arm": {k: infos[k]["seed"] for k in infos},
                         "part_note": (f"part {part['part']} of {part['parts']}: P16 / P17 and the owner item above are "
                                       "this part's alone (information); the assembly merges the parts "
                                       "(assemble.merge_cf -> validation/C33_CF.json)")})
    ctx.data["seconds_per_shot"] = float(np.mean([v["seconds_per_trajectory"] for v in infos.values()]))
    ctx.data["seconds_per_shot_note"] = "for C4_CF this is seconds per simulated trajectory"
    ctx.min_shots_ok = all(v["K"] >= K for v in infos.values())
    ctx.no_shots = any(v["K"] == 0 for v in infos.values())
    if not all(v["K"] >= K for v in infos.values()):
        ctx.shots_reduced_to = {k: v["K"] for k, v in infos.items()}
    add_table(ctx, "Arms (r at delta 1e-3)", ["arm", "K", "r", "r 95 %", "f_hit", "f_ideal", "floor min"],
              [[k, v["K"], v["r"]["value"], v["r"]["ci95"], v["f_hit"]["value"], v["f_ideal"]["value"],
                v["floor_min_feff_over_fideal_S99"]["value"]] for k, v in per_arm.items()])
    add_table(ctx, "Pooled k = 1 r(1e-3) and r_nc", ["pooled r", "95 %", "new r_nc", "old r_nc", "old pooled 95 %"],
              [[pooled[f"r_{tb}"]["value"], pooled[f"r_{tb}"]["ci95"], new_rnc, float(old["r_nc"]), old_iv]])


# --------------------------------------------------------------------------- prompts/33c step 3: the `cf` part content
CF_TOKEN = "C4_CF"
CF_PART_MARGIN = 0.95      # K per part = floor(margin x the fewest trajectories an arm of the harvested job reached)


def compact_arm(arm: dict, st: dict) -> dict:
    """What the assembly needs to merge an arm over parts: per trajectory p_tau(ref) post-readout (h) and TV_pre (tv)
    (r(delta) and its bootstrap, gate_CF_traj.ideal_fraction / pooled_ratio), and the SUM over trajectories of the
    post-readout sector probabilities on S99 (the point value of the P17 floor is linear in their mean)."""
    P = np.asarray(st["_P"], float)
    sec = arm["base"]["sector"]
    S99 = [int(s) for s in sec["S99"]]
    return {"K": int(len(st["_h"])), "h": [float(x) for x in st["_h"]], "tv_pre": [float(x) for x in st["_tv"]],
            "f0_prime": float(st["f0_prime"]), "p_ref": float(st["p_ref"]), "S99": S99,
            "pc_S99": [float(x) for x in np.asarray(st["_pc"], float)[S99]],
            "sum_p_post_S99": [float(x) for x in P[:, S99].sum(axis=0)]}


def merge_cf_parts(compacts: list, n_boot: int = None) -> dict:
    """Merge the compact arms of the `cf` parts (list of {arm: compact_arm}) -> per-arm r(delta) with the bootstrap of
    gate_CF_traj.arm_statistics (multinomial weights, BOOT_SEED, N_BOOT), the P17 floor point value, the pooled
    k = 1 r (gate_CF_traj.pooled_ratio) and r_nc = its upper end.  A single part reproduces the in-job numbers."""
    import gate_CF_traj as G
    B = G.N_BOOT if n_boot is None else int(n_boot)
    tb = G.delta_tag(G.DELTA_BAR)
    keys = list(compacts[0])
    merged, per_arm = {}, {}
    for k in keys:
        ps = [c[k] for c in compacts]
        for f in ("f0_prime", "p_ref"):
            if max(abs(p[f] - ps[0][f]) for p in ps) > 1e-15:
                raise ValueError(f"arm {k}: {f} differs between parts")
        if any(p["S99"] != ps[0]["S99"] for p in ps):
            raise ValueError(f"arm {k}: S99 differs between parts")
        h = np.concatenate([np.asarray(p["h"], float) for p in ps])
        tv = np.concatenate([np.asarray(p["tv_pre"], float) for p in ps])
        K = len(h)
        f0, p_ref = ps[0]["f0_prime"], ps[0]["p_ref"]
        sumP = np.sum([np.asarray(p["sum_p_post_S99"], float) for p in ps], axis=0)
        pc = np.asarray(ps[0]["pc_S99"], float)
        point = G.ideal_fraction(f0, np.full(K, 1.0 / K), h, tv, p_ref)
        rng = np.random.default_rng(G.BOOT_SEED)
        W = rng.multinomial(K, np.full(K, 1.0 / K), size=B) / K
        boots = [G.ideal_fraction(f0, w, h, tv, p_ref) for w in W]
        with np.errstate(divide="ignore", invalid="ignore"):
            feff = np.where(pc > 0, f0 + (1 - f0) * (sumP / K) / np.where(pc > 0, pc, 1.0), np.nan)
        floor = float(np.nanmin(feff) / point[f"f_ideal_{tb}"])
        per_arm[k] = {"K": K, "K_by_part": [p["K"] for p in ps],
                      "r": G.ival(point[f"r_{tb}"], [b[f"r_{tb}"] for b in boots]),
                      "f_hit": G.ival(point["f_hit"], [b["f_hit"] for b in boots]),
                      "f_ideal": G.ival(point[f"f_ideal_{tb}"], [b[f"f_ideal_{tb}"] for b in boots]),
                      "floor_min_feff_over_fideal_S99": {"value": floor}}
        merged[k] = {"h": h, "tv": tv, "f0": f0, "p_ref": p_ref}
    parts = [{"id": c, "f0": merged[c]["f0"], "p_ref": merged[c]["p_ref"], "h": merged[c]["h"], "tv": merged[c]["tv"],
              "shots": G.POOL_SHOTS[c]} for c in G.POOL_SHOTS if c in merged]
    pooled = G.pooled_ratio(parts, n_boot=B) if len(parts) == len(G.POOL_SHOTS) else None
    return {"arms": per_arm, "pooled": pooled, "r_nc_new": pooled[f"r_{tb}"]["ci95"][1] if pooled else None,
            "bootstrap_B": B, "floor_min": G.FLOOR_MIN,
            "rule": "trajectories concatenated per arm in part order; bootstrap and pooling as gate_CF_traj"}


def cf_part_plan(cf_json: dict, k_target: int = K_TARGET, margin: float = CF_PART_MARGIN, tokens: dict = None) -> dict:
    """The post-maintenance `cf` re-request (prompts/33c R4/step 3), sized from the harvested C4_CF: K per part =
    floor(margin x min over arms of the trajectories reached in one job), parts n = ceil(k_target / K), so that the
    merged parts reach >= k_target per arm.  Seeds: C4_CF's own base seed (33b R4: a part seeds from its run's own
    token), chunk index = the part number 1..n (index 0 is the harvested job, so a later merge with it stays
    disjoint)."""
    runs = cf_json["data"]["trajectory_runs"]
    k_min = min(int(v["K"]) for v in runs.values())
    K = int(math.floor(margin * k_min))
    n = int(math.ceil(k_target / K))
    idx = TK.token_index(CF_TOKEN, tokens)
    job = (((cf_json.get("run") or {}).get("ci") or {}).get("SLURM_JOB_ID")
           or ((((cf_json.get("data") or {}).get("run") or {}).get("ci")) or {}).get("SLURM_JOB_ID"))
    desc = [{"content": "cf", "token": CF_TOKEN, "run": "CF", "part": i, "parts": n, "K_per_arm": K,
             "seed_chunk_index": i, "seed_token_index": idx,
             "sizing": {"K_reached_by_arm": {k: int(v["K"]) for k, v in runs.items()}, "margin": margin,
                        "k_target": k_target,
                        "s_per_trajectory_by_arm": {k: v.get("seconds_per_trajectory") for k, v in runs.items()},
                        "rule": "K = floor(margin x min_arm K reached); n = ceil(k_target / K)"},
             "owner_gated": "prompts/33c section 4: only if the owner wants K = 2000 (after the maintenance)",
             "written_by": "scripts/campaign33_resize.py", "from": f"validation/C4_CF.json job {job}"}
            for i in range(1, n + 1)]
    return {"K_per_part": K, "parts": n, "K_total": K * n, "descriptors": desc, "k_min_reached": k_min}


def owner_item_r_nc(new_pooled_ci95, old_r_nc: float, old_pooled_ci95) -> dict:
    """The r_nc owner item (prompts/33c R4 step 3).  prompts/33 section 6: the item fires when the NEW pooled 95 %
    interval of r(1e-3) excludes the old r_nc (1.115, the upper end of CF_traj's pooled interval: "excludes 1.115's
    derivation"); section 8: when the new r_nc (the new interval's upper end) lies outside the OLD pooled interval.
    Job 59736866 evaluated only the section-8 comparison under the field name
    `owner_item_r_nc_outside_old_interval`; the field now carries the union of both rules, each recorded.  Reads
    only stored intervals, so the assembly applies it to a harvested JSON without rewriting that JSON."""
    lo, hi = float(new_pooled_ci95[0]), float(new_pooled_ci95[1])
    olo, ohi = float(old_pooled_ci95[0]), float(old_pooled_ci95[1])
    s6 = bool(not (lo <= float(old_r_nc) <= hi))
    s8 = bool(not (olo <= hi <= ohi))
    why = []
    if s6:
        why.append(f"the new pooled interval [{lo:.4f}, {hi:.4f}] excludes the old r_nc {float(old_r_nc):.4f} (section 6)")
    if s8:
        why.append(f"the new r_nc {hi:.4f} lies outside the old pooled interval [{olo:.4f}, {ohi:.4f}] (section 8)")
    return {"fires": bool(s6 or s8), "section6_new_interval_excludes_old_r_nc": s6,
            "section8_new_r_nc_outside_old_interval": s8, "new_pooled_ci95": [lo, hi], "old_r_nc": float(old_r_nc),
            "old_pooled_ci95": [olo, ohi], "why": "; ".join(why) or "neither rule fires",
            "rule": ("fires iff (prompts/33 section 6) old r_nc is outside the new pooled 95 % interval of r(1e-3) OR "
                     "(section 8) the new r_nc = that interval's upper end is outside the old pooled interval; no "
                     "criterion, verdict or r_nc value changes (the replacement is the owner's decision)"),
            "k4_note": ("r_nc bounds the k = 1 excess only (the campaign's pooled statistic is the k = 1 pool); the "
                        "k = 4 arm's r(1e-3) interval is not covered by r_nc (prompts/33c R4 (c))")}


def ctx_root():
    return C.ROOT
