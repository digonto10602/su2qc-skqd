#!/usr/bin/env python3
"""
prompts/33a step D3: size every class-4 job of campaign 33 from C4_FCELLS_A's measured ladder -- never by hand.

    python scripts/campaign33_resize.py                      # reads validation/C4_FCELLS_A.json (CI result)
    python scripts/campaign33_resize.py --dry-run            # reads validation/dryrun/C4_FCELLS_A.json, writes
                                                             #   data/campaign33/dryrun/ (never ci/parts/)

Inputs (every number is named with its JSON path in the output): `data.ladder.points` of C4_FCELLS_A (one
run() call per point at chunks 476 / 952 / 1428 per GPU mode), `data.cells_dropped` of C4_FCELLS_A and, once it
has run, C4_FCELLS_B, the plan of record (validation/CV_2x3_plan.json via tokens_run.cv_plan, at the tier
tokens_run.plan_tier reads from the f-cell JSONs) and the S3 quota (2e5 per sector).

Rule (prompts/33a step D3): fit t = c + b * chunk (least squares, one point per call) on the ladder of the mode
the F runs will use (C4_FCELLS_A's fastest mode); the chunk is 476 unless a 952 / 1428 point succeeded with
gpu_memory_bytes_model >= 1.6e10, then the largest successful; r_eff = b + c / chunk;
N_max = share * (budget_s - setup_s) / (1.25 * r_eff) with share 0.75 (quota / f-cells) or 0.6 (plan runs);
parts n = ceil(N / N_max), raised while a part exceeds N_max after rounding; the per-circuit part boundaries are
the first chunk starts >= i N_c / n of the unsplit chunk plan (skqd.campaign33.sampling.split_ranges), so every
gate_CV prefix point stays a chunk boundary of the concatenated parts.

Outputs: data/campaign33/sizing_33a.json and ci/parts/C4_PART_NN.json for the parts >= 2, the dropped f-cells and
the CV3 equal-shots samples of split NAT-O0 plan runs, assigned to the 20 slots in that order.  Slot files this
script wrote earlier and does not assign now are removed (the script owns ci/parts/C4_PART_*.json).
"""
import argparse
import glob
import json
import math
import os
import sys
import time
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.campaign33 import sampling as SM  # noqa: E402
from skqd.campaign33 import tokens as TK  # noqa: E402

WRITTEN_BY = "scripts/campaign33_resize.py"
CONTINGENCY = 1.25
SETUP_S = 120.0
BIG_CHUNK_MEMORY = 1.6e10
DEFAULT_CHUNK = 476
DRY_CHUNK = 16


# --------------------------------------------------------------------------- pure functions (tested)
def fit_ladder(points: list, mode: str = None) -> dict:
    """Least-squares t = c + b * chunk over the successful points of `mode` (one run() call each)."""
    import numpy as np
    pts = [p for p in points if "seconds" in p and p.get("success", True) and (mode is None or p.get("mode") == mode)]
    if not pts:
        raise ValueError("no successful ladder point")
    x = np.asarray([float(p["chunk"]) for p in pts])
    y = np.asarray([float(p["seconds"]) for p in pts])
    if len(set(x.tolist())) < 2:
        b = float(np.mean(y / x))
        return {"c_s": 0.0, "b_s_per_shot": b, "points_used": len(pts), "residual_rms_s": 0.0,
                "single_chunk": True, "note": "one chunk size only: c := 0, b = mean t / chunk"}
    Am = np.vstack([np.ones_like(x), x]).T
    (c, b), *_ = np.linalg.lstsq(Am, y, rcond=None)
    res = y - (c + b * x)
    return {"c_s": float(c), "b_s_per_shot": float(b), "points_used": len(pts),
            "residual_rms_s": float(np.sqrt(np.mean(res ** 2))), "single_chunk": False,
            "points": [[float(a), float(t)] for a, t in zip(x, y)]}


def choose_chunk(points: list, mode: str = None, default: int = DEFAULT_CHUNK) -> dict:
    ok = [p for p in points if "seconds" in p and p.get("success", True) and (mode is None or p.get("mode") == mode)
          and int(p["chunk"]) > default and float(p.get("gpu_memory_bytes_model", 0)) >= BIG_CHUNK_MEMORY]
    if ok:
        ch = max(int(p["chunk"]) for p in ok)
        return {"chunk": ch, "rule": f"largest successful point with gpu_memory_bytes_model >= {BIG_CHUNK_MEMORY:g}"}
    return {"chunk": int(default), "rule": f"{default}: no larger point succeeded at >= {BIG_CHUNK_MEMORY:g} bytes"}


def r_eff(b: float, c: float, chunk: int) -> float:
    return float(b) + float(c) / float(chunk)


def n_max(share: float, reff: float, budget_s: float = 3000.0, setup_s: float = SETUP_S,
          contingency: float = CONTINGENCY) -> int:
    """N_max = share x (budget - set-up) / (1.25 x r_eff) (prompts/33a step D3)."""
    return int(math.floor(share * (budget_s - setup_s) / (contingency * reff)))


def parts_for(n_total: int, nmax: int) -> int:
    return max(1, int(math.ceil(float(n_total) / float(nmax))))


def split_run(plan: dict, chunk: int, nmax: int) -> dict:
    """{parts, ranges: [ {cid: [a, b]} per part ], part_shots} with every part <= nmax (n raised if needed)."""
    total = sum(int(v) for v in plan.values())
    n = parts_for(total, nmax)
    while True:
        rng = {c: SM.split_ranges(int(v), chunk, n) for c, v in plan.items()}
        parts = [{c: [int(rng[c][i][0]), int(rng[c][i][1])] for c in plan} for i in range(n)]
        shots = [sum(b - a for a, b in p.values()) for p in parts]
        if max(shots) <= nmax or n >= total:
            return {"parts": n, "ranges": parts, "part_shots": shots}
        n += 1


# --------------------------------------------------------------------------- the campaign
def _load(p):
    p = p if os.path.isabs(p) else os.path.join(ROOT, p)
    with open(p) as fh:
        return json.load(fh)


def f_tokens():
    return [t for t in TK.campaign_tokens() if t.startswith("C4_F") and not t.startswith("C4_FCELLS")]


def build(fcells_a: str, fcells_b: str, dry: bool, budget_s: float = None, force_parts: int = None,
          runs_only: list = None) -> dict:
    from campaign33 import DRY
    from skqd.campaign33 import circuits as C
    from skqd.campaign33 import tokens_run as TR
    fa = _load(fcells_a)
    lad = fa["data"].get("ladder") or {}
    mode = lad.get("fastest_mode")
    pts = lad.get("points") or []
    fit = fit_ladder(pts, mode)
    chosen = choose_chunk(pts, mode, DRY_CHUNK if dry else DEFAULT_CHUNK)
    chunk = chosen["chunk"]
    reff = r_eff(fit["b_s_per_shot"], fit["c_s"], chunk)
    tokens = TK.load_tokens()
    if budget_s is None:
        wall = TK.walltime_seconds(tokens["C4_F1_B0"]["walltime"])
        budget_s = 60.0 * min(50.0, wall / 60.0 - 10.0)          # the driver's CI budget (campaign33.build_parser)
    nm = {"plan": n_max(TR.PLAN_SHARE, reff, budget_s), "s3quota": n_max(TR.QUOTA_SHARE, reff, budget_s),
          "fcells": n_max(TR.QUOTA_SHARE, reff, budget_s)}
    job = (fa["data"].get("run") or {}).get("ci") or {}
    src = f"{os.path.relpath(fcells_a, ROOT) if os.path.isabs(fcells_a) else fcells_a} job {job.get('SLURM_JOB_ID')}"
    ctx = SimpleNamespace(dry=dry)
    idx = C.load_index()
    runs, slot_queue = {}, []
    for tok in f_tokens():
        run = TR.run_key(tok)
        if runs_only and run not in runs_only:
            continue
        spec = TR.f_run_spec(run, idx)
        ids = spec["all_ids"]
        if dry:
            ids = TR.select_ids(SimpleNamespace(args=SimpleNamespace(max_circuits=DRY["max_circuits"]), notes=[]),
                                ids, tuple(TR.FCELL_SHOTS))
        pl = TR.f_run_plan(ctx, spec, ids)
        plan = pl["want"]
        if dry:
            plan = {c: min(DRY["max_shots"], max(1, int(math.ceil(v * DRY["shots_scale"])))) for c, v in plan.items()}
        cap = nm[spec["kind"]]
        sp = split_run(plan, chunk, cap)
        if force_parts and sp["parts"] < force_parts:
            rng = {c: SM.split_ranges(int(v), chunk, force_parts) for c, v in plan.items()}
            parts = [{c: list(rng[c][i]) for c in plan} for i in range(force_parts)]
            sp = {"parts": force_parts, "ranges": parts, "part_shots": [sum(b - a for a, b in p.values()) for p in parts],
                  "forced": True}
        total = sum(plan.values())
        f010 = pl["plan_f010"]
        if dry and f010:
            f010 = {c: min(DRY["max_shots"], max(1, int(math.ceil(v * DRY["shots_scale"])))) for c, v in f010.items()}
        desc = []
        for i, rr in enumerate(sp["ranges"]):
            desc.append({"content": "frun", "run": run, "token": tok, "scenario": spec["scenario"],
                         "sector": spec["sector"].replace("=", ""), "family": spec["family"], "kind": spec["kind"],
                         "tier": pl["tier"], "tier_reason": pl["tier_reason"], "part": i + 1, "parts": sp["parts"],
                         "chunk": chunk, "plan_shots_by_circuit": plan, "plan_f010_by_circuit": f010,
                         "ranges_by_circuit": rr, "shots_by_circuit": {c: b - a for c, (a, b) in rr.items()},
                         "written_by": WRITTEN_BY, "from": src})
        runs[run] = {"token": tok, "kind": spec["kind"], "share": spec["share"], "scenario": spec["scenario"],
                     "family": spec["family"], "sector": spec["sector"], "tier": pl["tier"],
                     "tier_reason": pl["tier_reason"], "circuits": len(plan), "total_shots": total,
                     "N_max": cap, "parts": sp["parts"], "part_shots": sp["part_shots"],
                     "forced_parts": bool(sp.get("forced")), "part_descriptors": desc, "slots": [tok]}
        for d in desc[1:]:
            slot_queue.append(("frun", run, d))
    # ---- dropped f-cells (C4_FCELLS_A now; C4_FCELLS_B once it has run)
    dropped = []
    for path in (fcells_a, fcells_b):
        p = path if os.path.isabs(path) else os.path.join(ROOT, path)
        if os.path.exists(p):
            dropped += [c.split("|") for c in (_load(p)["data"].get("cells_dropped") or [])]
    cell_shots = sum((min(DRY["max_shots"], max(1, int(math.ceil(v * DRY["shots_scale"])))) if dry else v)
                     for v in TR.FCELL_SHOTS.values())
    per_slot = max(1, nm["fcells"] // cell_shots)
    groups = [dropped[i:i + per_slot] for i in range(0, len(dropped), per_slot)]
    for i, g in enumerate(groups):
        slot_queue.append(("fcells", None, {"content": "fcells", "cells": g, "part": i + 1, "parts": len(groups),
                                            "cell_shots": TR.FCELL_SHOTS, "written_by": WRITTEN_BY, "from": src}))
    # ---- CV3 equal-shots samples of split NAT-O0 plan runs (the in-job path has no room for them)
    cv3 = {}
    for run, r in runs.items():
        if r["parts"] < 2 or r["kind"] != "plan" or r["family"] != "NAT-O0":
            continue
        plan = r["part_descriptors"][0]["plan_shots_by_circuit"]
        ids = list(plan)
        n_eq = (int(math.ceil(sum(plan.values()) / len(ids) / 100.0) * 100) if not dry
                else max(2, int(math.ceil(sum(plan.values()) / len(ids)))))
        twoB = 0 if r["sector"] == "B=0" else 2
        k5_all = [c for c in idx["families"].get("NAT-O0-k5", {}).get("circuits", []) if TR.sector_of(c) == twoB]
        mans = {c: C.load_manifest(r["family"], c) for c in ids}
        k5 = [f"{r['sector'].replace('=', '')}_ref{int(mans[c]['reference']):02d}_k5" for c in ids if int(mans[c]["k"]) == 1]
        k5 = [c for c in k5 if c in k5_all]
        shots = n_eq * (len(ids) + len(k5))
        fits = shots <= nm["fcells"]
        cv3[run] = {"N_eq": n_eq, "k5_circuits": len(k5), "shots": shots, "N_max": nm["fcells"], "fits_one_slot": fits,
                    "status": "slot" if fits else (f"not_evaluated: N_eq x ({len(ids)} + {len(k5)}) = {shots} shots exceed "
                                                   f"one slot's N_max {nm['fcells']}")}
        if fits:
            slot_queue.append(("cv3", run, {"content": "cv3", "run": run, "token": r["token"], "scenario": r["scenario"],
                                            "sector": r["sector"].replace("=", ""), "family": r["family"],
                                            "plan_shots_by_circuit": plan, "N_eq": n_eq, "part": 1, "parts": 1,
                                            "written_by": WRITTEN_BY, "from": src}))
    # ---- slots
    slots = list(TK.slot_tokens(tokens))
    assigned, unassigned = {}, []
    for k, (kind, run, d) in enumerate(slot_queue):
        if k < len(slots):
            s = slots[k]
            d = dict(d, slot=s, seed_token_index=TK.token_index(s, tokens))
            assigned[s] = d
            if kind == "frun":
                runs[run]["slots"].append(s)
                runs[run]["part_descriptors"][d["part"] - 1]["slot"] = s
            elif kind == "cv3":
                cv3[run]["slot"] = s
        else:
            unassigned.append({"kind": kind, "run": run, "part": d.get("part")})
    return {"written_by": WRITTEN_BY, "prompt": "prompts/33a_campaign33_first_wave_reruling.md step D",
            "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "dry_run": dry, "from": src,
            "inputs": {"ladder": f"{src}: data.ladder.points ({len(pts)} points)",
                       "fastest_mode": f"data.ladder.fastest_mode = {mode}",
                       "cells_dropped": [f"{fcells_a}: data.cells_dropped", f"{fcells_b}: data.cells_dropped (if present)"],
                       "plan": "validation/CV_2x3_plan.json via tokens_run.cv_plan at tokens_run.plan_tier",
                       "quota": f"tokens_run.PRODUCTION_SHOTS_PER_SECTOR = {TR.PRODUCTION_SHOTS_PER_SECTOR}"},
            "fit": dict(fit, mode=mode, chunk=chunk, chunk_rule=chosen["rule"], r_eff_s_per_shot=reff,
                        rule="t = c + b chunk (least squares); r_eff = b + c / chunk"),
            "budget": {"budget_s": budget_s, "setup_s": SETUP_S, "contingency": CONTINGENCY,
                       "shares": {"plan": TR.PLAN_SHARE, "s3quota": TR.QUOTA_SHARE, "fcells": TR.QUOTA_SHARE},
                       "N_max": nm, "rule": "N_max = share x (budget - setup) / (1.25 r_eff)"},
            "runs": runs, "fcells": {"dropped": dropped, "cells_per_slot": per_slot, "slots": len(groups)},
            "cv3": cv3, "slots": {s: {k: d.get(k) for k in ("content", "run", "part", "parts", "cells")}
                                  for s, d in assigned.items()},
            "slot_files": assigned, "slots_used": len(assigned), "slots_available": len(slots),
            "unassigned": unassigned, "allowlist_33a": "ci/allowed_jobs.campaign33a"}


def write(out: dict, sizing_path: str, parts_dir: str) -> list:
    os.makedirs(os.path.dirname(sizing_path), exist_ok=True)
    files = out.pop("slot_files")
    with open(sizing_path, "w") as fh:
        json.dump(out, fh, indent=1)
    os.makedirs(parts_dir, exist_ok=True)
    written = []
    for s, d in files.items():
        p = os.path.join(parts_dir, s + ".json")
        with open(p, "w") as fh:
            json.dump(d, fh, indent=1)
        written.append(p)
    for p in glob.glob(os.path.join(parts_dir, TK.SLOT_PREFIX + "*.json")):
        if p in written:
            continue
        try:
            mine = _load(p).get("written_by") == WRITTEN_BY
        except (OSError, ValueError):
            mine = False
        if mine:
            os.remove(p)
    out["slot_files"] = files
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fcells-a", default=None)
    ap.add_argument("--fcells-b", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--parts-dir", default=None)
    ap.add_argument("--budget-s", type=float, default=None)
    ap.add_argument("--force-parts", type=int, default=None, help="testing / dry runs: split every run into >= n parts")
    ap.add_argument("--runs", nargs="*", default=None, help="only these runs (e.g. F1_B1)")
    a = ap.parse_args(argv)
    sub = "dryrun" if a.dry_run else ""
    fa = a.fcells_a or os.path.join("validation", sub, "C4_FCELLS_A.json")
    fb = a.fcells_b or os.path.join("validation", sub, "C4_FCELLS_B.json")
    out_path = a.out or os.path.join(ROOT, "data", "campaign33", sub, "sizing_33a.json")
    parts_dir = a.parts_dir or (os.path.join(ROOT, "data", "campaign33", "dryrun", "parts") if a.dry_run
                                else TK.PARTS_DIR)
    out = build(fa, fb, a.dry_run, a.budget_s, a.force_parts, a.runs)
    written = write(out, out_path, parts_dir)
    print(f"fit ({out['fit']['mode']}): c {out['fit']['c_s']:.4g} s, b {out['fit']['b_s_per_shot']:.4g} s/shot, chunk "
          f"{out['fit']['chunk']}, r_eff {out['fit']['r_eff_s_per_shot']:.4g} s/shot; N_max {out['budget']['N_max']}")
    for run, r in out["runs"].items():
        print(f"  {run:8s} {r['kind']:8s} {r['total_shots']:7d} shots -> {r['parts']} part(s) {r['part_shots']} "
              f"slots {r['slots']}")
    un = {}
    for u in out["unassigned"]:
        un[u["kind"]] = un.get(u["kind"], 0) + 1
    print(f"slots used {out['slots_used']} of {out['slots_available']}; unassigned by kind {un or 'none'}")
    print(f"wrote {os.path.relpath(out_path, ROOT)} and {len(written)} slot file(s) in {os.path.relpath(parts_dir, ROOT)}")
    return 0 if not out["unassigned"] else 2


if __name__ == "__main__":
    sys.exit(main())
