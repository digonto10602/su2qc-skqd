"""
prompts/33 A7: assemble the campaign -- validation/C33_campaign.json and reports/C33_campaign_report.md
(validation/dryrun/... and reports/dryrun/... for the laptop dry run), generated from the token JSONs and
the old results' JSONs only.  Nothing is typed by hand.

* the campaign matrix: class x scenario x variant -> f_hit, f_hat_ideal, f0, accepted, |B|, recall,
  E_R - E0, certificate width, CV flags, s/shot, node-hours;
* the a/b merges of the S3-quota runs (C4_F4_*, C4_F8_*): the per-circuit accepted counts summed, then
  B_all, Ritz, recall of S999 and Weinstein at 2e5 shots per sector -> P15 (the gate-S3 criterion) for F8
  and the S1 redo for F4;
* the comparison table of section 6 (one row per old result, Delta, sigma, verdict).
"""
from __future__ import annotations

import json
import os
import time

import numpy as np

from . import stats as ST
from . import tokens as TK

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GATE = "C33_campaign"


def load(p):
    p = p if os.path.isabs(p) else os.path.join(ROOT, p)
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def token_json(tok, dry):
    return load(os.path.join("validation", "dryrun" if dry else "", tok + ".json"))


def _g(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


# --------------------------------------------------------------------------- prompts/33a step D4: split runs
def vpath(name, dry):
    return os.path.join(ROOT, "validation", "dryrun" if dry else "", name + ".json")


def split_runs(dry) -> dict:
    """{run: {token, parts, files, present}} for every F token whose JSON says part 1 of n > 1."""
    out = {}
    for tok in TK.campaign_tokens():
        if not tok.startswith("C4_F") or tok.startswith("C4_FCELLS"):
            continue
        d = token_json(tok, dry)
        p = _g(d, "data", "frun", "part")
        if not p or int(p["parts"]) < 2:
            continue
        run = d["data"]["frun"]["run"]
        n = int(p["parts"])
        files = [vpath(tok, dry)] + [vpath(f"C33_{run}_part{i}of{n}", dry) for i in range(2, n + 1)]
        out[run] = {"token": tok, "parts": n, "files": [os.path.relpath(f, ROOT) for f in files],
                    "present": [os.path.exists(f) for f in files],
                    "cv3": cv3_files(run, dry)}
    return out


def cv3_files(run, dry) -> dict:
    """prompts/33b R6: the cv3 content of a run -- C33_<run>_cv3.json (one part) or C33_<run>_cv3_part<i>of<n>.json
    (n > 1 parts; the largest n found is the sizing in force).  {files, parts, present, complete}."""
    import glob
    import re
    single = vpath(f"C33_{run}_cv3", dry)
    if os.path.exists(single):
        return {"files": [os.path.relpath(single, ROOT)], "parts": 1, "present": [True], "complete": True}
    found = {}
    for f in glob.glob(vpath(f"C33_{run}_cv3_part*of*", dry)):
        m = re.search(r"_cv3_part(\d+)of(\d+)\.json$", f)
        if m:
            found.setdefault(int(m.group(2)), {})[int(m.group(1))] = f
    if not found:
        return {"files": [], "parts": 0, "present": [], "complete": False}
    n = max(found)
    files = [vpath(f"C33_{run}_cv3_part{i}of{n}", dry) for i in range(1, n + 1)]
    present = [os.path.exists(f) for f in files]
    return {"files": [os.path.relpath(f, ROOT) for f in files], "parts": n, "present": present,
            "complete": all(present)}


def cf_files(dry) -> dict:
    """prompts/33c step 3: the `cf` parts C33_CF_part<i>of<n>.json (the largest n found is the sizing in force)."""
    import glob
    import re
    found = {}
    for f in glob.glob(vpath("C33_CF_part*of*", dry)):
        m = re.search(r"C33_CF_part(\d+)of(\d+)\.json$", f)
        if m:
            found.setdefault(int(m.group(2)), {})[int(m.group(1))] = f
    if not found:
        return {"files": [], "parts": 0, "present": [], "complete": False}
    n = max(found)
    files = [vpath(f"C33_CF_part{i}of{n}", dry) for i in range(1, n + 1)]
    present = [os.path.exists(f) for f in files]
    return {"files": [os.path.relpath(f, ROOT) for f in files], "parts": n, "present": present,
            "complete": all(present)}


def merge_cf(dry, n_boot=None) -> dict:
    """Merge the `cf` parts (prompts/33c step 3) -> validation/C33_CF.json: per-arm r(1e-3) with the bootstrap
    interval, P16 / P17 as C4_CF evaluates them, the pooled k = 1 r, r_nc = its upper end, and the owner item
    (cf_gpu.owner_item_r_nc against data/cf_trajectories/r_nc.json).  Pending while a part is missing."""
    from skqd.report import GateResult

    from .cf_gpu import merge_cf_parts, owner_item_r_nc
    info = cf_files(dry)
    if not info["parts"] or not info["complete"]:
        return {"status": "pending" if info["parts"] else "absent", **info}
    t0 = time.time()
    docs = [load(f) for f in info["files"]]
    comp = [d["data"]["merge_arrays"] for d in docs]
    m = merge_cf_parts(comp, n_boot=n_boot if n_boot is not None else (20 if dry else None))
    rnc = load("data/cf_trajectories/r_nc.json")
    gate = ("dryrun/" if dry else "") + "C33_CF"
    R = GateResult(gate, ("DRY RUN: " if dry else "") + f"Campaign 33 C4_CF re-request: the {info['parts']} cf parts "
                   "merged (prompts/33c step 3)")
    seeds = [sorted(d["data"]["seeds_by_arm"].values()) for d in docs]
    flat = [s for ss in seeds for s in ss]
    R.add("every part present, its K reached (S6 of each part) and the seeds of all parts disjoint",
          {"parts": len(docs), "status": [d.get("status") for d in docs], "distinct_seeds": len(set(flat)),
           "seeds": len(flat)}, f"{info['parts']} parts PASS, seeds distinct",
          all(d.get("status") == "PASS" for d in docs) and len(set(flat)) == len(flat))
    arms = m["arms"]
    tb = "r_d1e-03"
    R.add("P16 r per arm with 95 % bootstrap intervals; pooled r; new r_nc = its upper end",
          {k: v["r"]["value"] for k, v in arms.items()}, "fields present",
          all("ci95" in v["r"] for v in arms.values()) and m["pooled"] is not None and "ci95" in m["pooled"][tb])
    R.add(f"P17 floor theorem (CF_traj C4'): min_S99 f_eff / f_ideal(1e-3) >= {m['floor_min']} on every arm",
          {k: v["floor_min_feff_over_fideal_S99"]["value"] for k, v in arms.items()}, f">= {m['floor_min']}",
          all(v["floor_min_feff_over_fideal_S99"]["value"] >= m["floor_min"] for v in arms.values()))
    oi = owner_item_r_nc(m["pooled"][tb]["ci95"], rnc["r_nc"], rnc["pooled_r_ci95"]) if m["pooled"] else None
    R.data = {"parts": info["files"], "dry_run": dry, **m, "owner_item_r_nc": oi,
              "r_nc_in_use": rnc["r_nc"], "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    R.runtime_s = time.time() - t0
    R.save()
    return {"status": "PASS" if R.passed else "FAIL", "json": os.path.relpath(vpath("C33_CF", dry), ROOT), **info}


def merge_cv3(info: dict) -> tuple:
    """Merge the cv3 parts of a run (prompts/33b step A3): the equal-shots totals per circuit summed over the
    parts, after checking that every part has the same N_eq and circuits and that the parts' ranges tile
    [0, N_eq) of every circuit.  Returns (d3 or None, note); d3 has the fields of a single-part cv3 JSON
    (N_eq, eq_/k5_accepted_by_circuit, eq_/k5_rejected_by_circuit, shots_done, full) plus `parts_files`."""
    if not info or not info.get("complete"):
        return None, ("not_evaluated: no cv3 slot result" if not info or not info.get("files") else
                      f"not_evaluated: cv3 parts missing ({sum(info['present'])} of {info['parts']} present)")
    ds = [_g(load(f), "data", "cv3") for f in info["files"]]
    if any(d is None for d in ds):
        return None, "not_evaluated: a cv3 part JSON has no data.cv3"
    if len(ds) == 1:
        return ds[0], f"evaluated from {info['files'][0]}"
    N_eq = int(ds[0]["N_eq"])
    eq_ids, k5_ids = list(ds[0]["eq_accepted_by_circuit"]), list(ds[0]["k5_ids"])
    same = all(int(d["N_eq"]) == N_eq and list(d["k5_ids"]) == k5_ids and list(d["eq_accepted_by_circuit"]) == eq_ids
               for d in ds)
    if not same:
        return None, "not_evaluated: the cv3 parts disagree on N_eq or the circuits (re-sized between parts?)"
    from .sampling import ranges_list
    tiles = True
    for key, cids in (("eq_ranges_by_circuit", eq_ids), ("k5_ranges_by_circuit", k5_ids)):
        for c in cids:
            rr = sorted(tuple(x) for d in ds for x in ranges_list(d[key][c]) if x[1] > x[0])
            tiles &= bool(rr) and rr[0][0] == 0 and rr[-1][1] == N_eq and all(rr[i][1] == rr[i + 1][0]
                                                                             for i in range(len(rr) - 1))
    m = {"N_eq": N_eq, "k5_ids": k5_ids, "parts_files": info["files"], "ranges_tile": bool(tiles),
         "full": bool(tiles and all(d.get("full") for d in ds))}
    for side in ("eq", "k5"):
        acc, rej = {}, {}
        for d in ds:
            for c, a in d[f"{side}_accepted_by_circuit"].items():
                t = acc.setdefault(c, {})
                for i, v in a.items():
                    t[str(i)] = t.get(str(i), 0) + int(v)
            for c, r in d[f"{side}_rejected_by_circuit"].items():
                rej[c] = rej.get(c, 0) + int(r)
        m[f"{side}_accepted_by_circuit"], m[f"{side}_rejected_by_circuit"] = acc, rej
    done = {}
    for d in ds:
        for c, v in d["shots_done"].items():
            done[c] = done.get(c, 0) + int(v)
    m["shots_done"] = done
    m["full"] = m["full"] and all(v == N_eq for v in done.values())
    note = (f"evaluated from {len(ds)} merged cv3 parts" if m["full"] else
            "not_evaluated: the merged cv3 parts do not cover N_eq on every circuit (a part was cut or the ranges "
            "do not tile)")
    return m, note


def _pseudo_counts(P, acc: dict, rejected: int) -> dict:
    """Raw-count stand-in for fcell_stats from decoded counts: {codeword int: n} plus key -1 (never a codeword:
    decoded as rejected) for the rejected strings.  Exact for every quantity fcell_stats reads."""
    out = {int(P.emb.ints[int(i)]): int(v) for i, v in acc.items()}
    if rejected:
        out[-1] = int(rejected)
    return out


def merge_run(run, info, dry, P, B=None):
    """Concatenate the parts of a split F run in order, rebuild the order-kept prefixes and evaluate what run_frun
    evaluates in-job (CV0-CV5, the certificate of ruling 2, recall, bootstrap, P13 / P14 / P15) ->
    validation/C33_<run>.json (dry: validation/dryrun/), listing the part JSONs it came from."""
    from skqd.report import GateResult, md_table, write_report

    from . import analysis as A
    from . import circuits as C
    from . import tokens_run as TR
    t0 = time.time()
    parts = [load(f) for f in info["files"]]
    fr = [p["data"]["frun"] for p in parts]
    p1 = fr[0]["part"]
    spec = TR.f_run_spec(run)
    twoB, sec = spec["twoB"], spec["sector"]
    plan = {c: int(v) for c, v in p1["plan_shots_by_circuit"].items()}
    ids = list(plan)
    chunks = {c: [] for c in ids}
    for f in fr:
        for c, rows in f["chunks_accepted"].items():
            chunks[c] += rows
    pre = A.Prefixes.from_chunks(P, twoB, chunks)
    done = {c: pre.done[c] for c in ids}
    acc = {c: {} for c in ids}
    rej = {c: 0 for c in ids}
    for c, rows in chunks.items():
        for r in rows:
            for i, v in r["accepted"].items():
                acc[c][int(i)] = acc[c].get(int(i), 0) + int(v)
            rej[c] += int(r["rejected"])
    per_counts = {c: _pseudo_counts(P, acc[c], rej[c]) for c in ids}
    mans = {c: C.load_manifest(spec["family"], c) for c in ids}
    eq, cv3_src = None, None
    d3, cv3_note = merge_cv3(info.get("cv3"))
    if d3 is not None and d3.get("full"):
        N_eq = int(d3["N_eq"])

        def tot(a, r):
            return A.Prefixes.from_chunks(P, twoB, {c: [{"start": 0, "shots": N_eq, "accepted": a[c], "rejected": r[c]}]
                                                    for c in a})
        eq = (tot(d3["eq_accepted_by_circuit"], d3["eq_rejected_by_circuit"]), N_eq,
              tot(d3["k5_accepted_by_circuit"], d3["k5_rejected_by_circuit"]))
        cv3_src = ", ".join(info["cv3"]["files"])
    plan_s = {c: int(v) for c, v in (p1.get("plan_f010_by_circuit") or {}).items()} or None
    B = B if B is not None else (20 if dry else 2000)
    rd, crit, var_ok, pt = TR.frun_readout(P, spec, pre, plan, done, plan_s, per_counts, acc, mans, eq, B,
                                           fr[0]["plan_tier"])
    gate = ("dryrun/" if dry else "") + f"C33_{run}"
    R = GateResult(gate, ("DRY RUN: " if dry else "") + f"Campaign 33 split run {run}: the {info['parts']} parts merged "
                   "(prompts/33a step D4)")
    full = all(f["full"] for f in fr)
    R.add("every part JSON present and full (S6 of each part)", {"present": len(parts), "full": [f["full"] for f in fr]},
          f"{info['parts']} parts, full: true", len(parts) == info["parts"] and full)
    tiles = all(pre.bounds[c][-1] == plan[c] for c in ids)
    pfx = all(SM_rnd(phi * plan[c]) in pre.bounds[c] for c in ids for phi in PHI)
    R.add("the concatenated chunks tile the plan and every gate_CV prefix point is a chunk boundary",
          {"tile": tiles, "prefix_points": pfx}, "both true", tiles and pfx)
    for name, value, thr, passed, _gating in crit:
        R.add(name, value, thr, passed)
    R.data = {"run": run, "token": info["token"], "parts": info["files"], "cv3_slot": cv3_src, "dry_run": dry,
              "scenario": spec["scenario"], "family": spec["family"], "sector": sec, "kind": spec["kind"],
              "plan_tier": fr[0]["plan_tier"], "plan_shots_by_circuit": plan, "shots_done": done,
              "bounds": pre.bounds, "frun": dict(rd, run=run, scenario=spec["scenario"], family=spec["family"],
                                                 kind=spec["kind"], half=spec["half"], sector=sec,
                                                 plan_tier=fr[0]["plan_tier"], shots_done=done, full=full,
                                                 accepted_counts_by_circuit=acc, rejected_by_circuit=rej,
                                                 cv3_status=("evaluated from " + cv3_src) if cv3_src else cv3_note),
              "cv3_parts": (info.get("cv3") or {}).get("parts"),
              "variational_ok": var_ok, "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    R.runtime_s = time.time() - t0
    R.save()
    cert = rd["at_N"]["certificate"]
    write_report(("dryrun/" if dry else "") + f"C33_{run}.md", "\n".join([
        f"# {R.title}", "", f"**Status: {'PASS' if R.passed else 'FAIL'}** — `python scripts/campaign33.py --stage assemble"
        f"{' --dry-run' if dry else ''}`; parts: {', '.join(info['files'])}.", "",
        md_table(["shots", "|B_all|", "E_R - E0", "certificate", "E0 inside", "recall S999"],
                 [[rd["at_N"]["shots"], pt["B_all_size"], cert["E_R_minus_E0"], cert["type"], cert["E0_inside"],
                   cert["recall_S999"]]]), "", "## Criteria", "", R.criteria_table(), "",
        f"Every number above is computed by `src/skqd/campaign33/assemble.py` and stored in `validation/{gate}.json`.",
        ""]))
    return {"status": "PASS" if R.passed else "FAIL", "json": os.path.relpath(vpath(f"C33_{run}", dry), ROOT)}


def SM_rnd(x):
    from .sampling import rnd
    return rnd(x)


PHI = (1 / 16, 1 / 8, 1 / 4, 1 / 2, 1.0)


def assemble_split_runs(dry, P=None):
    """Merge every split run whose parts are all present; {run: status} (pending when a part is missing)."""
    out = {}
    runs = split_runs(dry)
    for run, info in runs.items():
        if not all(info["present"]):
            out[run] = {"status": "pending", "present": info["present"], "files": info["files"]}
            continue
        if P is None:
            from .analysis import Physics
            P = Physics()
        out[run] = merge_run(run, info, dry, P)
    return out, P


def frun_of(tok, dry):
    """The F run's reading: the merged C33_<run>.json when the run was split, else the token's own frun."""
    d = token_json(tok, dry)
    fr = _g(d, "data", "frun")
    if fr and fr.get("part") and int(fr["part"]["parts"]) > 1:
        m = load(vpath(f"C33_{fr['run']}", dry))
        return (m["data"]["frun"], m) if m else (None, None)
    return fr, d


# --------------------------------------------------------------------------- the S3-quota merges
def merge_halves(tokens, dry, P=None):
    """{F4|F8: {sector: merged reading}} from the a/b halves' accepted_counts_by_circuit (each half merged over
    its parts first when it was split, prompts/33a step D4)."""
    out = {}
    for f in ("F4", "F8"):
        for sec, tb in (("B=0", 0), ("B=1", 2)):
            fa, a = frun_of(f"C4_{f}_B{tb // 2}a", dry)
            fb, b = frun_of(f"C4_{f}_B{tb // 2}b", dry)
            key = f"{f}|{sec}"
            if fa is None or fb is None:
                out[key] = {"status": "pending", "halves_present": [fa is not None, fb is not None]}
                continue
            n_full = None
            if P is None:
                from .analysis import Physics
                P = Physics()
            S = P.S[sec]
            n_full = np.zeros(P.M.basis.dim, dtype=np.int64)
            shots = 0
            for fr in (fa, fb):
                for c, acc in fr["accepted_counts_by_circuit"].items():
                    for i, v in acc.items():
                        n_full[int(i)] += int(v)
                shots += int(sum(fr["shots_done"].values()))
            from .analysis import certificate_reading, skqd_point
            pt = skqd_point(P, sec, n_full, shots, with_random=False)
            cert = certificate_reading(sec, pt)
            w = pt["all"]["weinstein"]
            inside_w = bool(pt["all"]["E0_in_weinstein"])
            p15 = bool(pt["all"]["recall_S999"] >= 0.9 and inside_w)
            out[key] = {"status": "merged", "shots": shots, "family": fa["family"], "scenario": fa["scenario"],
                        "B_all_size": pt["B_all_size"], "recall_S999": pt["all"]["recall_S999"],
                        "W": pt["all"]["W"], "E_R_minus_E0": pt["all"]["err"], "weinstein": w,
                        "E0_in_weinstein": inside_w, "kt_rigorous": pt["all"]["kt_rigorous"],
                        "certificate_ruling2": cert,
                        "P15_gate_S3_criterion": {"recall_min": 0.9, "pass": p15,
                                                  "rule": "recall of the 99.9 % support >= 0.9 with 2e5 shots per sector "
                                                          "and E0 inside the Weinstein interval (s3_device_model.RECALL_MIN, "
                                                          "EPS_SUPPORT)"} if f == "F8" else None,
                        "dry_run_inputs": bool(a["data"].get("dry_run") or b["data"].get("dry_run"))}
    return out, P


# --------------------------------------------------------------------------- the matrix
def matrix_rows(tokens, dry):
    rows = []
    for tok in tokens:
        d = token_json(tok, dry)
        if d is None:
            rows.append({"token": tok, "status": "pending"})
            continue
        D = d["data"]
        run = D.get("run", {})
        base = {"token": tok, "class": D.get("class"), "status": d["status"],
                "s_per_shot": run.get("seconds_per_shot"), "wall_s": run.get("wall_seconds"),
                "node_hours": run.get("node_hours_charged_shared_qos"), "dry_run": D.get("dry_run")}
        if tok.startswith("C4_FCELLS"):
            for key, c in (D.get("cells") or {}).items():
                pk = _g(c, "stats", "pooled_k1") or {}
                r = dict(base)
                r.update({"scenario": c["scenario"], "variant": c["family"], "f_hit": pk.get("f_hit"),
                          "f_hit_ci95": pk.get("f_hit_ci"), "f_hat_ideal": pk.get("f_hat_ideal"),
                          "f_hat_ideal_ci95": pk.get("f_hat_ideal_ci"),
                          "f0_B0_k1": _g(c, "f0", "B0_ref25_k1", "f0"),
                          "accepted_fraction_B0_k1": _g(c, "stats", "per_circuit", "B0_ref25_k1", "accepted_fraction")})
                rows.append(r)
        elif "frun" in D:
            fr, src = frun_of(tok, dry)           # a split run reads its merged C33_<run>.json (prompts/33a D4)
            if fr is None:
                r = dict(base)
                r.update({"status": "pending (split run: parts missing)", "split": D["frun"].get("part")})
                rows.append(r)
                continue
            if src is not d:
                base["status"] = src["status"]
                base["merged_from"] = src["data"].get("parts")
            cert = fr["at_N"]["certificate"]
            pk = _g(fr, "clean_fraction", "pooled_k1") or {}
            r = dict(base)
            r.update({"scenario": fr["scenario"], "variant": fr["family"], "sector": fr["sector"],
                      "kind": fr["kind"], "half": fr["half"], "plan_tier": fr["plan_tier"],
                      "shots": fr["at_N"]["shots"], "B_all": fr["at_N"]["B_all_size"],
                      "recall_S999": cert["recall_S999"], "E_R_minus_E0": cert["E_R_minus_E0"],
                      "certificate": cert["type"], "width": cert["width"], "E0_inside": cert["E0_inside"],
                      "f_hit": pk.get("f_hit"), "f_hat_ideal": pk.get("f_hat_ideal"),
                      "f_hat_ideal_ci95": pk.get("f_hat_ideal_ci"), "CV": fr.get("CV1_CV5"),
                      "cv3": fr.get("cv3_status")})
            rows.append(r)
        elif tok.startswith("C2_") and tok != "C2_CAL":
            for k, v in (D.get("per_run") or {}).items():
                r = dict(base)
                r.update({"scenario": D.get("cell"), "variant": D.get("family"), "run": k,
                          "accepted": v["accepted"], "reference_hits": v["reference_hits"], "shots": v["shots"],
                          "f0_twirled": _g(v, "f0_twirled", "f0"),
                          "P_K1_accepted": v.get("P_measured_accepted_under_model"),
                          "P_K1_hits": v.get("P_measured_hits_under_model")})
                rows.append(r)
        else:
            rows.append(base)
    return rows


# --------------------------------------------------------------------------- the comparison table (section 6)
def comparisons(dry, merged):
    rows = []

    def tj(t):
        return token_json(t, dry)

    s1 = load("validation/S1.json")["data"]
    s3 = load("validation/S3.json")["data"]
    # S1 -> F4 (E7(0.10), 2e5 per sector)
    for sec, tb in (("B=0", 0), ("B=1", 2)):
        old = s1["production"].get(f"{sec}|f=0.1", {})
        new = merged.get(f"F4|{sec}", {})
        rows.append({"old": f"S1 production {sec} f=0.1 (proxy noise, 2e5/sector)", "redo": "C4_F4_* (merged a+b)",
                     "status": new.get("status", "pending"),
                     "recall": ST.compare(new.get("recall_S999"), None, old.get("recall"), None),
                     "B_size": ST.compare(new.get("B_all_size"), None, old.get("size"), None),
                     "E_R_minus_E0": ST.compare(new.get("E_R_minus_E0"), None, old.get("err"), None),
                     "weinstein_width": ST.compare(None if new.get("weinstein") is None else
                                                   new["weinstein"][1] - new["weinstein"][0], None,
                                                   None if old.get("weinstein") is None else
                                                   old["weinstein"][1] - old["weinstein"][0], None),
                     "note": "old value has one seed: no_old_uncertainty"})
    # S3 -> C4_FCELLS_B faithful redo and C4_F8
    fb = tj("C4_FCELLS_B")
    redo = _g(fb, "data", "s3_redo") or {}
    if redo:
        lo, hi = ST.wilson(redo["accepted"], redo["shots"])
    rows.append({"old": "S3 (job 58771538): E8 on IR-L3-RZZ, B=0, 32 x 100, seed 11", "redo": "C4_FCELLS_B s3_redo",
                 "status": "done" if redo else "pending",
                 "yield": ST.compare(redo.get("yield"), [lo, hi] if redo else None, s3["yield"],
                                     list(ST.wilson(s3["accepted"], s3["total_shots"]))) if redo else None,
                 "accepted_in_binomial_band": redo.get("inside"), "same_count_as_S3": redo.get("equal_to_s3_count"),
                 "s3_s_per_shot": s3["cost"]["seconds_per_shot_best_ladder"],
                 "new_s_per_shot": _g(fb, "data", "run", "seconds_per_shot"),
                 "s3_peak_mib": s3["run"]["gpu_telemetry"]["peak_memory_mib"],
                 "s3_mean_util": s3["run"]["gpu_telemetry"]["mean_utilization_pct"]})
    rows.append({"old": "S3 criterion (never evaluated)", "redo": "C4_F8_* merged",
                 "status": merged.get("F8|B=0", {}).get("status", "pending"),
                 "P15": {sec: _g(merged.get(f"F8|{sec}", {}), "P15_gate_S3_criterion", "pass") for sec in ("B=0", "B=1")}})
    sm = load("validation/S3_smoke.json")["data"]
    rows.append({"old": f"S3_smoke: B=1, {sm['total_shots']} shots, recall {sm['support']['recall_99.9pct']:.4f}",
                 "redo": "C4_F8_B1*", "status": "superseded",
                 "note": "the 24-shot pipeline smoke number has no comparison value; the 2e5-shot criterion replaces it"})
    for f in ("1e-3", "3e-3"):
        d = load(f"validation/L4_p2_{f}.json")
        rows.append({"old": f"L4_p2_{f}: {(d or {}).get('title', 'absent')}", "redo": "not redone",
                     "status": "not_applicable", "note": "these are 2x2 runs, not 2x3"})
    # Q0P A6 dry run -> C4_FCELLS_A E1 x O0
    pr = load("data/quantinuum/q0p_stages/predict.json")["dryrun"]
    fa = tj("C4_FCELLS_A")
    cell = _g(fa, "data", "cells", "E1|NAT-O0", "stats", "pooled_k1") or {}
    rows.append({"old": f"Q0P A6 dry run: {pr['reference_hits_total']} hits / {pr['shots_used']}, f_hit "
                        f"{pr['pooled_f_estimate']:.4f}", "redo": "C4_FCELLS_A E1 x NAT-O0 (k = 1 circuits)",
                 "status": "done" if cell else "pending",
                 "f_hit": ST.compare(cell.get("f_hit"), cell.get("f_hit_ci"), pr["pooled_f_estimate"], pr["pooled_f_95"]),
                 "P11_vs_CF_traj": _g(fa, "data", "P11")})
    # CF_traj -> C4_CF
    cf = load("validation/CF_traj.json")["data"]
    rnc = load("data/cf_trajectories/r_nc.json")
    new = tj("C4_CF")
    cfm = cf_files(dry)
    cfm_d = load(vpath("C33_CF", dry)) if cfm["complete"] else None
    cfm["status"] = (cfm_d or {}).get("status") or ("pending" if cfm["parts"] else "absent")
    new_iv = _g(new, "data", "pooled", "r_d1e-03", "ci95")
    from .cf_gpu import owner_item_r_nc
    oi = owner_item_r_nc(new_iv, rnc["r_nc"], rnc["pooled_r_ci95"]) if new_iv else None
    rows.append({"old": f"CF_traj pooled r(1e-3) {rnc['pooled_r_point']:.4f} {rnc['pooled_r_ci95']}, r_nc {rnc['r_nc']:.4f}",
                 "redo": "C4_CF (K = 2000 per arm)", "status": "done" if new else "pending",
                 "pooled_r": ST.compare(_g(new, "data", "pooled", "r_d1e-03", "value"), new_iv,
                                        rnc["pooled_r_point"], rnc["pooled_r_ci95"]),
                 "r_nc_new": _g(new, "data", "r_nc_new"),
                 # prompts/33c R4 (b): evaluated here from the stored intervals; the harvested JSON is not rewritten
                 "owner_item": oi["fires"] if oi else None, "owner_item_rules": oi,
                 "owner_item_field_as_harvested": _g(new, "data", "owner_item_r_nc_outside_old_interval"),
                 "r_nc_in_use": rnc["r_nc"], "r_nc_in_use_source": "data/cf_trajectories/r_nc.json (owner item: "
                 "replacement is the owner's decision, prompts/33c section 5)",
                 "k4_note": oi["k4_note"] if oi else None,
                 "k4_r": _g(new, "data", "arms", "B0_ref25_k4", "r"),
                 "merged_cf_parts": ({"json": "validation/C33_CF.json", "status": cfm.get("status"),
                                      "pooled_r": _g(cfm_d, "data", "pooled", "r_d1e-03"),
                                      "r_nc_new": _g(cfm_d, "data", "r_nc_new"),
                                      "owner_item": _g(cfm_d, "data", "owner_item_r_nc", "fires")}
                                     if cfm_d else None)})
    # CV_2x3_plan / Q0P_2x3_plan P3 -> C4_F5
    cvp = load("validation/CV_2x3_plan.json")["data"]["criteria_by_seed"]["f=0.10"]
    q3 = load("validation/Q0P_2x3_plan.json")["data"]["emulated_check"]["per_seed"]
    for sec, tb in (("B=0", 0), ("B=1", 2)):
        f5 = tj(f"C4_F5_B{tb // 2}")
        fr = _g(f5, "data", "frun") or {}
        old_rec = [v["all"]["recall_S999"] for v in q3[sec].values()]
        old_cv1 = [v["CV1"]["dE"] for v in cvp[sec].values()]
        new_cv1 = _g(fr, "cv", "criteria", "CV1", "dE")
        rows.append({"old": f"CV_2x3_plan / Q0P_2x3_plan P3 {sec} f=0.10 (proxy at 0.7 f, 3 seeds)",
                     "redo": f"C4_F5_B{tb // 2}", "status": "done" if fr else "pending",
                     "recall_S999": ST.compare(_g(fr, "at_N", "certificate", "recall_S999"), None,
                                               float(np.mean(old_rec)), None, old_sigma=ST.seed_spread_sigma(old_rec),
                                               old_sigma_label="seed_spread"),
                     "CV1_dE": ST.compare(new_cv1, None, float(np.mean(old_cv1)), None,
                                          old_sigma=ST.seed_spread_sigma(old_cv1), old_sigma_label="seed_spread")})
    # K0 / K1 -> C2_*
    k1 = load("validation/K1_2x3_fpilot.json")["data"]["circuits"]
    for tok in ("C2_GATE", "C2_ECHO", "C2_STAR", "C2_XY4", "C2_COH"):
        d = tj(tok)
        per = _g(d, "data", "per_run") or {}
        rows.append({"old": "K1 measured 0 / 0 hits, " + " / ".join(str(k1[c]["accepted"]) for c in k1)
                            + " accepted of 1e5; K0/K1 analytic predictions", "redo": tok,
                     "status": "done" if per else "pending",
                     "per_run": {k: {"accepted_per_1e5": v["scaled_to_1e5"]["accepted"],
                                     "hits_per_1e5": v["scaled_to_1e5"]["reference_hits"],
                                     "P_K1_accepted": v["P_measured_accepted_under_model"],
                                     "P_K1_hits": v["P_measured_hits_under_model"],
                                     "prereg_expected_hits_1e5": v["prereg_expected_hits_1e5"]} for k, v in per.items()}})
    # class 3 engines vs C3_AER: two-sample TV distance with its multinomial null (prompts/33 2.4)
    aer = _g(tj("C3_AER"), "data", "noiseless", "stage_e_counts") or {}
    ex = load("data/campaign33/exact/stage_e.json") or {}
    for tok in ("C3_LE", "C3_SEL"):
        d = tj(tok)
        cnt = _g(d, "data", "counts") or {}
        per = {}
        for cid, c in cnt.items():
            if cid not in aer:
                continue
            a = {int(k): v for k, v in aer[cid].items()}
            b = {int(k): v for k, v in c.items()}
            probs = {int(k): v for k, v in ex["circuits"][cid]["probabilities"].items()}
            null = ST.tv_expectation_multinomial(probs, sum(a.values()), sum(b.values()))
            tv = ST.tv_distance(a, b)
            per[cid] = {"tv": tv, "null_mean": null["mean"], "null_p95": null["p95"],
                        "within_null_p95": bool(tv <= null["p95"])}
        rows.append({"old": "C3_AER (Aer, noiseless, NAT-O0)", "redo": tok, "status": "done" if per else "pending",
                     "tv_vs_C3_AER": per})
    s2d = load("validation/S2D.json")["data"]["2x3"]
    e8 = _g(tj("C4_FCELLS_B"), "data", "cells") or {}
    rows.append({"old": f"S2D 2x3 declared-model f {s2d['f']['mean']:.4f} (virtual Rz {s2d['f_virtual_rz']['mean']:.4f})",
                 "redo": "C4_FCELLS_B E7 cells (and E8 on IR-L3-RZZ in the S3 redo)",
                 "status": "done" if e8 else "pending",
                 "f_hit_E7_0.10_O0": _g(e8, "E7_0.10|NAT-O0", "stats", "pooled_k1", "f_hit"),
                 "analytic_f_virtual_rz_mean": s2d["f_virtual_rz"]["mean"],
                 "note": "f_hit vs the analytic f: the near-clean excess (expected r ~ 1.07)"})
    return rows


def main(dry=False):
    from skqd.report import GateResult, md_table, write_report
    t0 = time.time()
    tokens = list(TK.campaign_tokens())        # the 33 tokens; the C4_PART_NN slots are read through their runs
    split, P0 = assemble_split_runs(dry)
    present = {t: token_json(t, dry) is not None for t in tokens}
    statuses = {}
    for t in tokens:
        d = token_json(t, dry) or {}
        # an engine token dropped by data/campaign33/engines.json (its engine cannot run) is DROPPED, not failing
        statuses[t] = ("DROPPED" if (d.get("data") or {}).get("dropped") else d.get("status"))
    for run, v in split.items():
        statuses[f"C33_{run}"] = v["status"] if v["status"] != "pending" else None
    cfm = merge_cf(dry)                      # prompts/33c step 3 (absent until the owner's re-request has run)
    if cfm["status"] not in ("absent", "pending"):
        statuses["C33_CF"] = cfm["status"]
    merged, P = merge_halves(tokens, dry, P0)
    rows = matrix_rows(tokens, dry)
    comp = comparisons(dry, merged)
    gate = ("dryrun/" if dry else "") + GATE
    R = GateResult(gate, ("DRY RUN skeleton: " if dry else "") +
                   "2x3 four-class campaign: matrix, S3-quota merges and the comparison with every earlier 2x3 result")
    R.add("every token JSON present", f"{sum(present.values())} of {len(tokens)}", f"{len(tokens)} of {len(tokens)}", all(present.values()))
    R.add("every present token PASS (tokens dropped by data/campaign33/engines.json excluded)",
          {t: s for t, s in statuses.items() if s and s != "PASS"} or "all PASS",
          "no FAIL", all(s in ("PASS", "DROPPED") for s in statuses.values() if s))
    R.add("comparison table generated (section 6 rows)", len(comp), ">= 10 rows", len(comp) >= 10)
    if not dry:
        for sec in ("B=0", "B=1"):
            m = merged.get(f"F8|{sec}", {})
            if m.get("status") == "merged":
                R.add(f"P15 gate-S3 criterion {sec}: recall S999 >= 0.9 at 2e5 and E0 inside Weinstein",
                      [m["recall_S999"], m["E0_in_weinstein"]], ">= 0.9 and inside", m["P15_gate_S3_criterion"]["pass"])
    R.data = {"dry_run": dry, "tokens": tokens, "present": present, "statuses": statuses, "merged_s3_quota": merged,
              "split_runs": split, "cf_parts": cfm,
              "matrix": rows, "comparison": comp, "prompt": "prompts/33 A7 / section 6",
              "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    R.runtime_s = time.time() - t0
    R.save()
    banner = ("\n> **DRY RUN SKELETON** — assembled from the laptop dry-run JSONs (validation/dryrun/), every number "
              "is a reduced-size path check, not a campaign result.\n" if dry else "")
    mat = [[r.get("token"), r.get("status"), r.get("scenario"), r.get("variant"), r.get("sector"), r.get("f_hit"),
            r.get("f_hat_ideal"), r.get("recall_S999"), r.get("E_R_minus_E0"), r.get("s_per_shot"), r.get("node_hours")]
           for r in rows]

    def f(x):
        return f"{x:.4g}" if isinstance(x, float) else str(x)
    comp_rows = [[c["old"], c["redo"], c["status"],
                  "; ".join(f"{k}: {v.get('verdict')} (Delta {f(v.get('delta'))})" for k, v in c.items()
                            if isinstance(v, dict) and "verdict" in v) or "-"] for c in comp]
    merged_rows = [[k, v.get("status"), v.get("shots"), v.get("recall_S999"), v.get("E0_in_weinstein"),
                    _g(v, "P15_gate_S3_criterion", "pass")] for k, v in merged.items()]
    text = "\n".join([
        f"# {R.title}", "", f"**Status: {'PASS' if R.passed else 'FAIL'}** — `python scripts/campaign33.py --stage "
        f"assemble{' --dry-run' if dry else ''}`; prompt prompts/33 (A7, section 6).", banner,
        "## Campaign matrix", "", md_table(["token", "status", "scenario", "variant", "sector", "f_hit", "f_hat_ideal",
                                           "recall S999", "E_R - E0", "s/shot", "node-hours"],
                                          [[f(x) for x in r] for r in mat]), "",
        "## S3-quota merges (a + b halves)", "",
        md_table(["run|sector", "status", "shots", "recall S999", "E0 in Weinstein", "P15"],
                 [[f(x) for x in r] for r in merged_rows]), "",
        "## Comparison with the earlier 2x3 results (prompts/33 section 6)", "",
        md_table(["old result", "redo", "status", "difference (verdict)"], comp_rows), "",
        "## Criteria", "", R.criteria_table(), "",
        f"Every number above is read from validation/*.json and data/*.json by "
        f"`src/skqd/campaign33/assemble.py` and stored in `validation/{gate}.json`.", ""])
    write_report(("dryrun/" if dry else "") + "C33_campaign_report.md", text)
    print(R.criteria_table())
    return 0 if R.passed else 1
