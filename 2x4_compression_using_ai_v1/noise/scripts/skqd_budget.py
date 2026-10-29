"""Shot budget of the noisy SKQD campaign -> notes/campaign_budget.json (+ the table of notes/campaign_budget.md).

Rule (stated in notes/campaign_budget.md):
  1. plan of record at f = 1 (noiseless), per circuit N_c and the CV3 equal-shots N_eq per sector:
       2x4  validation/CV_2x4_plan.json data.plan.final (D3'-R at y = 1, CV re-size B=0 x1, B=1 x12; N_eq_by_sector)
            and data.plan.noiseless (the 1x D3'-R, before the CV re-size)
       2x3  gate_CV.plan_noiseless_L(Model(3)) (D3'-R at y = 1 on the frozen manifests' references / dt), re-sized by
            the factor of validation/CV_2x3_plan.json (B=0 x1, B=1 x2 at every f of its grid); N_eq = n_eq_of
       2x2  gate_CV.plan_noiseless_L(Model(2)), no re-size (CV_2x2 is the saturation regime); N_eq = n_eq_of
  2. noisy plan: N_c / f_c rounded up to 100, f_c = the model clean fraction of circuit c on the device,
     f_gate (traj_sparse.ir_events) x (1 - mean readout error)^n; N_eq / mean_c f_c rounded up to 100;
  3. sampled shots per circuit: k <= 4 max(N_c', N_eq'), k = 5 N_eq';
  4. cost = sampled shots x measured seconds per trajectory (data/checks/skqd_timing.json, mean over the family's
     probes x 1.15 margin) + 10 s start-up per chunk;
  5. CUTS (below) where the total exceeds the 24 h target; every cut is listed in the JSON and the .md.
Chunks: shots per chunk = floor(CHUNK_S / s_per_shot) (CHUNK_S = 900 s, half of the 30-minute cap).

Usage: python scripts/skqd_budget.py [--write]
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NOISE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(NOISE, "src"))
import campaign as C  # noqa: E402
import circuits  # noqa: E402
import noise_models as nm  # noqa: E402
import traj_sparse as ts  # noqa: E402
from circuits import ROOT  # noqa: E402
from provenance import provenance, dump  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "scripts"))
TIMING = os.path.join(NOISE, "data", "checks", "skqd_timing.json")
PLANS_CACHE = os.path.join(NOISE, ".cache", "noiseless_plans.json")
CHUNK_S = 900.0
MARGIN_T = 1.15
STARTUP_S = 10.0
THREADS_FULL = 10
HT_EFF_10 = 0.68     # ASSUMPTION (not measured): per-thread throughput at 10 threads on 6 physical cores, relative
                     # to the 5-thread probes; 4 of the 6 cores carry two threads at ~0.6 each -> (4*2*0.6+2)/10


def load(p):
    with open(p) as fh:
        return json.load(fh)


def rnd100(x):
    return int(math.ceil(x / 100.0 - 1e-12) * 100)


# --------------------------------------------------------------------------- 1. plans of record (f = 1)
def plans_of_record():
    if os.path.exists(PLANS_CACHE):
        return load(PLANS_CACHE)
    import gate_CV as CV
    from skqd.campaign33.analysis import Physics
    out = {}
    d4 = load(os.path.join(ROOT, "validation", "CV_2x4_plan.json"))["data"]["plan"]
    fin = d4["final"]
    out["2x4"] = {}
    for sec, tb in (("B=0", 0), ("B=1", 2)):
        pre = f"B{tb // 2}_"
        out["2x4"][sec] = {"plan": {c: int(v) for c, v in fin["shots_by_circuit"].items() if c.startswith(pre)},
                           "N_eq": int(fin["N_eq_by_sector"][sec]), "resize": int(fin["resized_by"][sec]),
                           "plan_1x": {c: int(v) for c, v in d4["noiseless"][sec]["shots"].items()},
                           "source": "validation/CV_2x4_plan.json data.plan.final (shots_by_circuit, N_eq_by_sector); "
                                     "plan_1x = data.plan.noiseless (before the CV re-size)"}
    d3 = load(os.path.join(ROOT, "validation", "CV_2x3_plan.json"))["data"]["plan"]
    for lat in (2, 3):
        P = Physics(lat=lat)
        mans = CV.circuits_L(lat)
        res = CV.plan_noiseless_L(P.M, P.S, mans, f_info=())
        L = f"2x{lat}"
        out[L] = {}
        for sec in ("B=0", "B=1"):
            base = {c: int(v) for c, v in res["noiseless"][sec]["shots"].items()}
            s = int(d3["f=0.05"][sec]["resized_by"]) if lat == 3 else 1
            if lat == 3:
                assert all(int(d3[f][sec]["resized_by"]) == s for f in d3), "2x3 re-size differs across f"
            plan = {c: CV.resized_shots(v, s) for c, v in base.items()} if s != 1 else base
            out[L][sec] = {"plan": plan, "N_eq": CV.n_eq_of(sum(plan.values()), len(plan)), "resize": s,
                           "plan_1x": base,
                           "source": f"gate_CV.plan_noiseless_L(Model({lat})) D3'-R at y = 1"
                                     + (f", re-sized x{s} (validation/CV_2x3_plan.json resized_by)" if lat == 3 else "")}
    os.makedirs(os.path.dirname(PLANS_CACHE), exist_ok=True)
    with open(PLANS_CACHE, "w") as fh:
        json.dump(out, fh, indent=1)
    return out


# --------------------------------------------------------------------------- 2. clean fractions
def clean_fractions(lat, fam, dev):
    p10, p01 = nm.readout_probs(dev)
    out = {}
    for cid, src in C.circuits(lat, fam).items():
        if src == "frozen":
            g, n = circuits.ir_gates(lat, "frozen", cid)
        else:
            g, md = circuits.genie_ir(src)[cid]
            n = int(md["n_qubits"])
        _, bud = ts.ir_events(g, n, dev)
        out[cid] = bud["f_gate"] * (1 - 0.5 * (p10 + p01)) ** n
    return out


def per_shot(lat, fam, dev, T):
    rows = [r for r in T["rows"] if (r["lattice"], r["family"], r["device"]) == (lat, fam, dev)]
    if not rows:
        return None, 0
    return MARGIN_T * sum(r["per_shot_s"] for r in rows) / len(rows), len(rows)


# --------------------------------------------------------------------------- CUTS (decided after the full table)
# (lattice, family-pattern or "*", device or "*", sector) -> {"plan": "1x" | "record", "shot_scale": s}
CUTS = {
    # 2x4 B=1: the 1x D3'-R plan (24 404 noiseless shots, N_eq 1 600) instead of the CV re-sized x12 plan of record
    # (294 000, N_eq 18 400): the x12 plan costs 774 thread-h (classA_v2) / 114 thread-h (classB_v2) on H2-2 alone.
    ("2x4", "*", "*", "B=1"): {"plan": "1x"},
    # Helios 2x4 classB_v2 (secondary model): half of the f-scaled shots (34.7 -> ~17 thread-h) to fit 24 h
    ("2x4", "compressed_circuit_llm_2x4_classB_v2", "quantinuum_helios_1", "B=0"): {"shot_scale": 0.5},
    ("2x4", "compressed_circuit_llm_2x4_classB_v2", "quantinuum_helios_1", "B=1"): {"plan": "1x", "shot_scale": 0.5},
}
# whole (lattice, family, device) cells not sampled in this campaign (reason in notes/campaign_budget.md)
SKIP = {
    ("2x3", "frozen", "quantinuum_helios_1"): "lowest clean fraction of the campaign (f_mean in the uncut table): the f-scaled plan alone exceeds the 24 h budget; existing noise_behaviour + analytic_f only",
    ("2x4", "compressed_circuit_llm_2x4_classA_v2", "quantinuum_helios_1"):
        "f_mean < 0.05: the f-scaled plan exceeds the 24 h budget even at the 1x B=1 plan; existing noise_behaviour + analytic_f only",
    ("2x4", "compressed_circuit_llm_2x4_classA_v1", "quantinuum_h2_2"):
        "v1 'only if time allows': classA_v1 has a lower clean fraction than classA_v2 and costs more; not queued",
}
# queue priority (lower first); anything not listed comes last
PRIORITY = [
    ("2x2", "*", "quantinuum_h2_2"),
    ("2x3", "compressed_circuit_llm_2x3_classB", "quantinuum_h2_2"),
    ("2x3", "compressed_circuit_llm_2x3_classA", "quantinuum_h2_2"),
    ("2x4", "compressed_circuit_llm_2x4_classB_v2", "quantinuum_h2_2"),
    ("2x3", "frozen", "quantinuum_h2_2"),
    ("2x4", "compressed_circuit_llm_2x4_classA_v2", "quantinuum_h2_2"),
    ("2x2", "*", "quantinuum_helios_1"),
    ("2x3", "*", "quantinuum_helios_1"),
    ("2x4", "compressed_circuit_llm_2x4_classB_v2", "quantinuum_helios_1"),
    ("2x4", "compressed_circuit_llm_2x4_classB_v1", "quantinuum_h2_2"),     # v1: only if time allows (last)
]


def prio_of(lat, fam, dev):
    for i, (l, f, d) in enumerate(PRIORITY):
        if l == lat and (f == "*" or f == fam) and d == dev:
            return i
    return len(PRIORITY)


def entry(lat, fam, dev, rec, fc, cut):
    e = {}
    for sec in ("B=0", "B=1"):
        r = rec[lat][sec]
        c = cut.get(sec, {})
        base = r["plan_1x"] if c.get("plan") == "1x" else r["plan"]
        sc = float(c.get("shot_scale", 1.0))
        n_eq0 = (int(math.ceil(sum(base.values()) / len(base) / 100.0) * 100)) if c.get("plan") == "1x" else r["N_eq"]
        ids = sorted(base)
        fbar = sum(fc[x] for x in ids) / len(ids)
        plan = {x: rnd100(sc * base[x] / fc[x]) for x in ids}
        N_eq = rnd100(sc * n_eq0 / fbar)
        tb = 0 if sec == "B=0" else 2
        k5 = sorted(x for x in fc if C.parse(x)[0] == tb and C.parse(x)[2] == 5)
        sampled = {x: max(plan[x], N_eq) for x in ids}
        sampled.update({x: N_eq for x in k5})
        e[sec] = {"plan": plan, "N_eq": N_eq, "sampled": sampled, "sampled_total": sum(sampled.values()),
                  "plan_total": sum(plan.values()), "f_mean": fbar, "f_min": min(fc[x] for x in ids),
                  "base_plan": "1x D3'-R (before the CV re-size)" if c.get("plan") == "1x" else "plan of record",
                  "base_total": sum(base.values()), "base_N_eq": n_eq0, "shot_scale": sc}
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    T = load(TIMING)
    rec = plans_of_record()
    families = []
    for dev in (C.PRIMARY, C.SECONDARY):
        for lat in ("2x2", "2x3", "2x4"):
            for fam in C.FAMILIES[lat]:
                if dev == C.SECONDARY and fam.endswith("_v1"):
                    continue
                families.append((lat, fam, dev))
    plans, table, jobs = {}, [], []
    skipped, uncut = [], []
    for lat, fam, dev in families:
        sps, nprobe = per_shot(lat, fam, dev, T)
        if sps is None:
            continue
        fc = clean_fractions(lat, fam, dev)
        u = entry(lat, fam, dev, rec, fc, {})
        ush = sum(u[s]["sampled_total"] for s in ("B=0", "B=1"))
        uch = ush / max(50, int(CHUNK_S / sps))
        uncut.append({"lattice": lat, "family": C.short(fam), "device": dev, "shots": ush, "f_mean_B0": u["B=0"]["f_mean"], "f_mean_B1": u["B=1"]["f_mean"],
                      "thread_hours": (ush * sps + uch * STARTUP_S) / 3600.0})
        if (lat, fam, dev) in SKIP:
            skipped.append({"lattice": lat, "family": C.short(fam), "device": dev, "reason": SKIP[(lat, fam, dev)],
                            "uncut_thread_hours": uncut[-1]["thread_hours"]})
            continue
        cut = {}
        for (cl, cf, cd, cs), v in CUTS.items():
            if cl == lat and (cf == "*" or cf == fam) and (cd == "*" or cd == dev):
                cut[cs] = v
        e = entry(lat, fam, dev, rec, fc, cut)
        e["seconds_per_shot"] = sps
        e["timing_probes"] = nprobe
        e["cuts"] = cut
        plans.setdefault(lat, {}).setdefault(fam, {})[dev] = e
        shots = sum(e[s]["sampled_total"] for s in ("B=0", "B=1"))
        chunk = max(50, int(CHUNK_S / sps))
        nch = 0
        for sec in ("B=0", "B=1"):
            for cid, N in sorted(e[sec]["sampled"].items()):
                s, i = 0, 0
                while s < N:
                    m = min(chunk, N - s)
                    jobs.append([lat, fam, dev, cid, i, s, m])
                    s += m
                    i += 1
                    nch += 1
        cost = shots * sps + nch * STARTUP_S
        table.append({"lattice": lat, "family": C.short(fam), "family_full": fam, "device": dev, "s_per_shot": sps,
                      "f_mean_B0": e["B=0"]["f_mean"], "f_mean_B1": e["B=1"]["f_mean"],
                      "shots_B0": e["B=0"]["sampled_total"], "shots_B1": e["B=1"]["sampled_total"],
                      "plan_B0": e["B=0"]["plan_total"], "plan_B1": e["B=1"]["plan_total"],
                      "N_eq_B0": e["B=0"]["N_eq"], "N_eq_B1": e["B=1"]["N_eq"],
                      "chunks": nch, "thread_hours": cost / 3600.0, "cuts": cut})
    # priority: H2-2 before Helios; within a device 2x2, 2x3, 2x4 v2, then v1; cheap first within a lattice
    def prio(j):
        return (prio_of(j[0], j[1], j[2]), j[1], j[4], j[3])     # chunk index before circuit: all circuits advance
    jobs.sort(key=prio)
    for r in table:
        r["priority"] = prio_of(r["lattice"], r["family_full"], r["device"])
    table.sort(key=lambda r: r["priority"])
    cum = 0.0
    for r in table:
        cum += r["thread_hours"]
        r["cumulative_thread_hours"] = cum
    tot = sum(r["thread_hours"] for r in table)
    for r in table:
        print(f"{r['lattice']} {r['family']:>12} {r['device']:>20} {r['s_per_shot']:.4f} s/shot  f {r['f_mean_B0']:.3f}/"
              f"{r['f_mean_B1']:.3f}  shots {r['shots_B0']:>8}/{r['shots_B1']:>8}  N_eq {r['N_eq_B0']}/{r['N_eq_B1']}"
              f"  {r['thread_hours']:7.1f} thread-h (cum {r['cumulative_thread_hours']:6.1f})  {r['cuts'] or ''}")
    for k in skipped:
        print("SKIP", k)
    print(f"TOTAL {tot:.1f} thread-h; at 10 threads x {HT_EFF_10} = {tot / (THREADS_FULL * HT_EFF_10):.1f} h wall;"
          f" at 5 threads {tot / 5:.1f} h wall; jobs {len(jobs)}")
    if a.write:
        dump({"what": "noisy SKQD campaign shot budget (scripts/skqd_budget.py)", "rule": __doc__,
              "chunk_target_s": CHUNK_S, "timing_margin": MARGIN_T, "startup_s_per_chunk": STARTUP_S,
              "ht_efficiency_10_threads_ASSUMED": HT_EFF_10, "cuts": {"|".join(k): v for k, v in CUTS.items()},
              "plans_of_record": rec, "plans": plans, "table": table, "total_thread_hours": tot, "skipped": skipped,
              "uncut": uncut, "uncut_total_thread_hours": sum(x["thread_hours"] for x in uncut),
              "jobs": jobs, "provenance": provenance()}, C.BUDGET_JSON)
        print("wrote", C.BUDGET_JSON)


if __name__ == "__main__":
    main()
