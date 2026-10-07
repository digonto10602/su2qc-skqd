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


def run(ctx):
    import gate_CF_traj as G
    from quantinuum_submit import A6_NOISE

    from campaign33 import add_table
    from . import stats as ST
    K = max(2, ctx.scaled(K_TARGET))
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
        seed = TK.chunk_seed(ctx.s0, i, 0, 1)
        arm, man, info = arm_run(ctx, cid, ch, K, seed, dl)
        infos[key] = info
        st = G.arm_statistics(cid, arm, man, A6_NOISE, predict)
        arms[key] = st
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
    owner_item = bool(not (old_iv[0] <= new_rnc <= old_iv[1]))
    if owner_item:
        ctx.notes.append(f"owner item (prompts/33 section 8): the new r_nc {new_rnc:.4f} lies outside the old pooled "
                         f"interval {old_iv}; no criterion or verdict is changed by this token")
    ctx.data.update({"arms": per_arm, "trajectory_runs": infos, "pooled": pooled, "r_nc_new": new_rnc,
                     "r_nc_old": float(old["r_nc"]), "r_nc_old_pooled_ci95": old_iv,
                     "owner_item_r_nc_outside_old_interval": owner_item,
                     "comparison": {k: ST.compare(per_arm[k]["r"]["value"], per_arm[k]["r"]["ci95"],
                                                  None, None) for k in per_arm},
                     "engine": "Aer statevector per trajectory (" + ctx.device + "), checkpoints in memory",
                     "seconds_per_shot": None,
                     "K_target_per_arm": K, "bootstrap_B": B})
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


def ctx_root():
    return C.ROOT
