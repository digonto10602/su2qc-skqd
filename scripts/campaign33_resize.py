#!/usr/bin/env python3
"""
prompts/33a step D3 + prompts/33b step A: size every class-4 job of campaign 33 from the measured timings of the
f-cell tokens -- never by hand -- and lay the parts out on the 20 re-usable C4_PART slots.

    python scripts/campaign33_resize.py                      # generation 1: reads validation/C4_FCELLS_A.json (and
                                                             #   validation/C4_FCELLS_B.json once harvested)
    python scripts/campaign33_resize.py --reassign           # later generations: free slots (prompts/33b R4) get the
                                                             #   next deferred items of the slot queue
    python scripts/campaign33_resize.py --dry-run            # reads validation/dryrun/C4_FCELLS_A.json, writes
                                                             #   data/campaign33/dryrun/ (never ci/parts/)

Inputs (every number is named with its JSON path in the output): `data.ladder.points` of C4_FCELLS_A (one run()
call per point at chunks 476 / 952 / 1428 per GPU mode); `data.cells.<cell>.chunks[*].{shots, seconds}` and
`data.cells.<cell>.seconds` of every f-cell JSON present (C4_FCELLS_A, C4_FCELLS_B); `data.cells_dropped` of both;
`data.s3_redo.{seconds, shots}` of C4_FCELLS_B (the E8 rate, once harvested); validation/S3.json
`data.cost.seconds_per_shot_best_ladder` (the E8 upper-bound label); the plan of record (validation/CV_2x3_plan.json
via tokens_run.cv_plan at the tier tokens_run.plan_tier reads from the f-cell JSONs) and the S3 quota (2e5 per
sector).

Rules.
* Ladder (prompts/33a D3): t = c + b chunk (least squares, one point per call) on the fastest mode's ladder; the
  chunk is 476 unless a 952 / 1428 point succeeded with gpu_memory_bytes_model >= 1.6e10, then the largest
  successful; r_ladder = b + c / chunk.
* Scenario rates (prompts/33b R2): r_s = r_ladder x rho_s, rho_s = max over the measured families of
  b_{s,fam} / b_{E1,NAT-O0} (per-cell least-squares slopes over the recorded chunks), rho_E1 >= 1.  No cell:
  E6a/b/c and E7(f) take rho_E1 labelled `assumed: E1 (...)`; E8 takes rho_E1 labelled `upper bound: ...` until
  C4_FCELLS_B's s3_redo gives its measured seconds / shots.
* N_max(kind, s) = share x (budget - setup) / (1.25 r_s), share 0.6 (plan runs) or 0.75 (quota / f-cells / cv3);
  parts n = ceil(N / N_max), raised while a part exceeds N_max after rounding; the per-circuit part boundaries are
  the first chunk starts >= i N_c / n of the unsplit chunk plan (skqd.campaign33.sampling.split_ranges).
* Dropped f-cells (R5): cost of a cell = the measured seconds of the scenario's most expensive measured cell (per
  the 2 000 f-cell shots); capacity 0.75 x (budget - setup) / 1.25 per slot; first fit in the priority order
  scenario E1, E2, E3, E4, E5a, E5b, E5c, within a scenario O0, O1, O2, O3, O4, O6.  C4_FCELLS_B's dropped cells are
  packed after them as their own group (C33_fcellsB_part<i>of<n>).
* CV3 (R6): the equal-shots sample of every split NAT-O0 plan run is sized in ceil(shots / N_max(fcells, s))
  parts; only CV3_SLOTS are scheduled (and CV3_QUEUED_LAST at the end of the queue); the rest is recorded
  `not_evaluated: deferred by prompts/33b`.
* Seeds (R4): every frun / cv3 content seeds from the run's own F token (`seed_token_index`); an f-cell content from
  the slot's own index with the cells' global offset (`cell_index_offset`).
* Slots (R4, step A1e): the slot queue in SLOT_QUEUE order; generation 1 = the first 20 on C4_PART_01..20, the rest
  `deferred` (generation 2, no file).  `--reassign`: a slot is free when ci/status/<slot>.json says `done` and the
  content-named copy of its current content exists in validation/; free slots receive the next deferred items in
  queue order (their ci/parts files are overwritten); `slot_history` records every content a slot has held.

Outputs: data/campaign33/sizing_33a.json (name kept: the driver's load_sizing reads it) and ci/parts/C4_PART_NN.json.
Slot files this script wrote earlier and does not assign now are removed (the script owns ci/parts/C4_PART_*.json).
Exit 0 when every queue item is assigned or deferred; 2 on an item that is neither (or a refused plain re-run).
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
PROMPT = "prompts/33b"
CONTINGENCY = 1.25
SETUP_S = 120.0
BIG_CHUNK_MEMORY = 1.6e10
DEFAULT_CHUNK = 476
DRY_CHUNK = 16
REF_CELL = "E1|NAT-O0"                       # the slope every rho is measured against (prompts/33b R2)
SCEN_A = ("E1", "E2", "E3", "E4", "E5a", "E5b", "E5c")
SCEN_B = ("E6a", "E6b", "E6c", "E7_0.05", "E7_0.07", "E7_0.10", "E7_0.15")
ALL_SCENARIOS = SCEN_A + SCEN_B + ("E8",)
VARIANT_PRIORITY = ("NAT-O0", "NAT-O1", "NAT-O2", "NAT-O3", "NAT-O4", "NAT-O6")   # R5 (O0 first: none is dropped in A)
CV3_SLOTS = ("F5_B1", "F1_B1")               # prompts/33b R6: the two CV3 samples worth a slot
CV3_QUEUED_LAST = ("F2_B1",)                 # prompts/33b R6 / A1e: after the maintenance if the owner wants it
# prompts/33b step A1e: the slot queue (kind, run or f-cell group).  'frun' = the run's parts >= 2, 'cv3' = all
# parts of its cv3 content, ('fcells', 'A1') = the first f-cell slot of group A, ('fcells', 'A*') = the rest.
SLOT_QUEUE = (("frun", "F5_B1"), ("frun", "F4_B0a"), ("frun", "F4_B1a"), ("frun", "F4_B0b"), ("frun", "F4_B1b"),
              ("frun", "F8_B0a"), ("frun", "F8_B1a"), ("frun", "F8_B0b"), ("frun", "F8_B1b"),
              ("frun", "F1_B1"), ("frun", "F7_B1"), ("frun", "F2_B1"), ("fcells", "A1"),
              ("cv3", "F5_B1"), ("cv3", "F1_B1"), ("frun", "F3_B0"),
              ("frun", "F3_B1"), ("frun", "F6_B0"), ("frun", "F6_B1"), ("fcells", "A*"), ("cv3", "F2_B1"))
FCELL_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


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


def equal_fraction_split(plan: dict, chunk: int, n: int) -> list:
    """The 33a rule: every circuit cut at the first chunk starts >= i N_c / n of its unsplit chunk plan
    (sampling.split_ranges).  [ {cid: [a, b]} per part ]."""
    rng = {c: SM.split_ranges(int(v), chunk, n) for c, v in plan.items()}
    return [{c: [int(rng[c][i][0]), int(rng[c][i][1])] for c in plan} for i in range(n)]


def round_major_split(plan: dict, chunk: int, nmax: int) -> list:
    """prompts/33b fallback: the unsplit run's own call order (round j = chunk j of every circuit, as Sampler.run
    issues them) cut into consecutive windows of <= nmax shots (next fit: the fewest windows for that order).  Each
    circuit's chunks in a window are consecutive rounds, so every part holds one contiguous range per circuit
    (possibly empty) of the unsplit chunk plan, and the parts tile it exactly.  [ {cid: [a, b]} per part ]."""
    plans = {c: SM.chunk_plan(int(v), chunk) for c, v in plan.items()}
    R = max([len(p) for p in plans.values()] or [0])
    seq = [(c, plans[c][j]) for j in range(R) for c in plan if j < len(plans[c])]
    pos = {c: 0 for c in plan}
    start = dict(pos)
    parts, cur = [], 0
    for c, (a, s, _i) in seq:
        if cur + s > nmax and cur > 0:
            parts.append({k: [start[k], pos[k]] for k in plan})
            start, cur = dict(pos), 0
        pos[c] = a + s
        cur += s
    parts.append({k: [start[k], pos[k]] for k in plan})
    return parts


def chunk_packing_split(plan: dict, chunk: int, nmax: int) -> list:
    """prompts/33b last resort: the chunks of the unsplit plan packed first-fit-decreasing (ties in the run's call
    order) into parts of <= nmax shots; a part's piece of a circuit is then a list of ranges [[a, b], ...] (adjacent
    chunks merged), possibly empty.  The parts still tile the unsplit plan chunk for chunk."""
    plans = {c: SM.chunk_plan(int(v), chunk) for c, v in plan.items()}
    R = max([len(p) for p in plans.values()] or [0])
    order = [(c, j) for j in range(R) for c in plan if j < len(plans[c])]
    rank = {cj: k for k, cj in enumerate(order)}
    items = sorted(order, key=lambda cj: (-plans[cj[0]][cj[1]][1], rank[cj]))
    bins = []
    for c, j in items:
        s = plans[c][j][1]
        for b in bins:
            if b["load"] + s <= nmax:
                break
        else:
            b = {"load": 0, "js": {k: [] for k in plan}}
            bins.append(b)
        b["load"] += s
        b["js"][c].append(j)
    parts = []
    for b in bins:
        p = {}
        for c, js in b["js"].items():
            rr = []
            for j in sorted(js):
                a, s, _i = plans[c][j]
                if rr and rr[-1][1] == a:
                    rr[-1][1] = a + s
                else:
                    rr.append([a, a + s])
            p[c] = rr
        parts.append(p)
    return parts


def split_run(plan: dict, chunk: int, nmax: int, force_parts: int = None) -> dict:
    """{parts, ranges: [ {cid: [a, b] | [[a, b], ...]} per part ], part_shots, method} with every part <= nmax.

    n0 = ceil(N / N_max) (at least force_parts).  The 33a rule (equal per-circuit fractions, rounded up to chunk
    boundaries) is kept whenever it fits at n0.  When it does not -- at chunk 1428 the per-circuit rounding puts up
    to one whole chunk per circuit into one part, e.g. F6_B0 (E5b) never fits its 9754-shot N_max at any n -- the
    run is cut in its own call order (round_major_split, one contiguous range per circuit), and when that needs
    more than n0 parts the chunks are packed first-fit-decreasing (chunk_packing_split, lists of ranges); the 33a
    rule at a raised n is used instead if it needs fewer parts than either.  All of them keep every part a union
    of chunks of the unsplit plan, so every gate_CV prefix point is a boundary of the concatenated parts and the
    R4 seeds reproduce the unsplit run."""
    total = sum(int(v) for v in plan.values())
    n_ceil = parts_for(total, nmax)
    n0 = max(n_ceil, int(force_parts or 1))

    def pack(parts, method):
        shots = [sum(SM.range_shots(r) for r in p.values()) for p in parts]
        return {"parts": len(parts), "ranges": parts, "part_shots": shots, "method": method,
                "fits": max(shots) <= nmax, "n_ceil": n_ceil,
                "forced": bool(force_parts and len(parts) == int(force_parts) and len(parts) > n_ceil)}
    eq = pack(equal_fraction_split(plan, chunk, n0), "equal_fraction (33a rule)")
    if eq["fits"]:
        return eq
    best = pack(round_major_split(plan, chunk, nmax), "round_major (prompts/33b fallback: the 33a rule does not fit "
                                                       f"at n = {n0})")
    if best["parts"] > n0:
        cp = pack(chunk_packing_split(plan, chunk, nmax), "chunk_packing (prompts/33b fallback: first-fit-decreasing "
                                                          f"chunks; round_major needs {best['parts']} parts)")
        if cp["fits"] and cp["parts"] < best["parts"]:
            best = cp
    for n in range(n0 + 1, best["parts"]):
        e = pack(equal_fraction_split(plan, chunk, n), f"equal_fraction (33a rule, raised from {n0})")
        if e["fits"]:
            return e
    return best


def cell_fit(cell: dict) -> dict:
    """Least-squares t = c + b n over the recorded chunks of one f-cell (data.cells.<cell>.chunks[*])."""
    import numpy as np
    xs, ys = [], []
    for chs in (cell.get("chunks") or {}).values():
        for ch in chs:
            if "seconds" in ch and int(ch.get("shots", 0)) > 0:
                xs.append(float(ch["shots"]))
                ys.append(float(ch["seconds"]))
    if not xs:
        return None
    x, y = np.asarray(xs), np.asarray(ys)
    if len(set(xs)) < 2:
        b = float(np.mean(y / x))
        return {"b": b, "c": 0.0, "n_chunks": len(xs), "rms": 0.0, "single_size": True}
    Am = np.vstack([np.ones_like(x), x]).T
    (c, b), *_ = np.linalg.lstsq(Am, y, rcond=None)
    return {"b": float(b), "c": float(c), "n_chunks": len(xs),
            "rms": float(np.sqrt(np.mean((y - (c + b * x)) ** 2))), "single_size": False}


def scenario_rates(fcells_jsons: list, ladder_fit: dict, chunk: int, s3_rate: dict = None,
                   scenarios=ALL_SCENARIOS) -> dict:
    """prompts/33b R2.  fcells_jsons: [(path, json, job id)] of the f-cell JSONs present; ladder_fit: fit_ladder's
    dict; s3_rate: {"s_per_shot", "source"} of gate S3 (the E8 upper-bound label).  Returns {scenario_rates,
    rate_rule, cell_fits, r_ladder}."""
    r_lad = r_eff(ladder_fit["b_s_per_shot"], ladder_fit["c_s"], chunk)
    fits = {}
    for path, js, job in fcells_jsons:
        for key, cell in ((js or {}).get("data", {}).get("cells") or {}).items():
            f = cell_fit(cell)
            if f is not None:
                fits[key] = dict(f, source=f"{path} (job {job}) data.cells.{key}.chunks")
    ref = fits.get(REF_CELL)
    rates = {}
    if ref is None:
        rho_e1, e1_label = 1.0, (f"no {REF_CELL} cell timing in the input JSONs: rho := 1 for every scenario "
                                 "(the 33a single-rate rule)")
    by_s = {}
    if ref is not None:
        for key, f in fits.items():
            by_s.setdefault(key.split("|")[0], []).append((f["b"] / ref["b"], key, f))
        e1 = max(by_s.get("E1", [(1.0, REF_CELL, ref)]))
        rho_e1 = max(1.0, e1[0])
        e1_label = "measured (rho_E1 >= 1)"
    for s in scenarios:
        if ref is not None and s in by_s:
            rho, key, f = max(by_s[s])
            if s == "E1":
                rho = rho_e1
            fams = sorted(k.split("|")[1] for _r, k, _f in by_s[s])
            rates[s] = {"s_per_shot": r_lad * rho, "rho": rho, "source": f["source"],
                        "fit": {"b": f["b"], "c": f["c"], "n_chunks": f["n_chunks"], "rms": f["rms"], "cell": key},
                        "label": (f"measured: max over the families {fams} of b_cell / b({REF_CELL}) "
                                  f"(b_ref {ref['b']:.6g} s/shot)" + ("; rho_E1 >= 1" if s == "E1" else ""))}
            continue
        if s == "E8":
            p476 = [t / c for c, t in (ladder_fit.get("points") or []) if int(c) == 476]
            lad476 = (f"{p476[0]:.4g} (measured point)" if p476 else
                      f"{r_eff(ladder_fit['b_s_per_shot'], ladder_fit['c_s'], 476):.4g} (fit)")
            label = ("upper bound: gate S3 measured "
                     + (f"{s3_rate['s_per_shot']:.4g} s/shot at 476-shot calls on this family and model "
                        f"({s3_rate['source']})" if s3_rate else "(validation/S3.json absent)")
                     + f" against the E1 ladder's {lad476} at 476; rho_E1 until C4_FCELLS_B's s3_redo timing "
                       "replaces it")
        elif s in SCEN_B:
            label = "assumed: E1 (same channel classes, other parameters)"
        else:
            label = "assumed: E1 (no f-cell of this scenario in the input JSONs)"
        if ref is None:
            label = e1_label + "; " + label
        rates[s] = {"s_per_shot": r_lad * rho_e1, "rho": rho_e1, "source": "rho_E1", "fit": None, "label": label}
    # E8 measured by C4_FCELLS_B's s3_redo (its recorded seconds and shots)
    for path, js, job in fcells_jsons:
        s3r = ((js or {}).get("data") or {}).get("s3_redo")
        if s3r and s3r.get("seconds") and s3r.get("shots") and "E8" in rates:
            r = float(s3r["seconds"]) / float(s3r["shots"])
            rates["E8"] = {"s_per_shot": r, "rho": r / r_lad, "source": f"{path} (job {job}) data.s3_redo.seconds / "
                           "data.s3_redo.shots", "fit": None,
                           "label": (f"measured: the faithful S3 redo, {s3r['shots']} shots in {s3r['seconds']:.1f} s "
                                     f"(chunk {s3r.get('chunk')}, per-call set-up included)")}
    rule = ("r_s = r_ladder x rho_s, r_ladder = b + c / chunk (E1 ladder of C4_FCELLS_A), rho_s = max over the "
            f"measured families of b_(s,fam) / b_({REF_CELL}) from least-squares t = c + b n over the recorded "
            "chunks of every f-cell present, rho_E1 >= 1; no cell: E6/E7 rho_E1 (assumed), E8 rho_E1 (upper bound) "
            "until C4_FCELLS_B's s3_redo (prompts/33b R2)")
    return {"scenario_rates": rates, "rate_rule": rule, "cell_fits": fits, "r_ladder": r_lad}


def cell_costs(fcells_jsons: list, rates: dict, cell_shots: int) -> dict:
    """prompts/33b R5: the predicted seconds of one f-cell (cell_shots shots) per scenario = the measured seconds of
    the scenario's most expensive measured cell (scaled to cell_shots when a cell is incomplete); a scenario
    without a measured cell: the E1 cost x rho_s / rho_E1 (labelled)."""
    meas = {}
    for path, js, job in fcells_jsons:
        for key, cell in ((js or {}).get("data", {}).get("cells") or {}).items():
            if not cell.get("shots") or cell.get("seconds") is None:
                continue
            t = float(cell["seconds"]) * float(cell_shots) / float(cell["shots"])
            s = key.split("|")[0]
            if t > meas.get(s, (0.0,))[0]:
                meas[s] = (t, f"{path} (job {job}) data.cells.{key}.seconds")
    out = {}
    e1 = meas.get("E1")
    for s, r in rates.items():
        if s in meas:
            out[s] = {"seconds": meas[s][0], "source": meas[s][1]}
        elif e1 is not None:
            out[s] = {"seconds": e1[0] * r["rho"] / rates["E1"]["rho"],
                      "source": f"assumed: the E1 cell cost x rho_{s} / rho_E1 ({e1[1]})"}
        else:
            out[s] = {"seconds": float(cell_shots) * r["s_per_shot"], "source": "no measured cell: shots x r_s"}
    return out


def pack_fcells(cells: list, costs: dict, capacity: float) -> list:
    """First fit in the given (priority) order: [{cells, predicted_s}] with predicted_s <= capacity (a single cell
    above the capacity gets a slot of its own, flagged)."""
    slots = []
    for s, fam in cells:
        c = float(costs[s]["seconds"])
        for sl in slots:
            if sl["predicted_s"] + c <= capacity:
                sl["cells"].append([s, fam])
                sl["predicted_s"] += c
                break
        else:
            slots.append({"cells": [[s, fam]], "predicted_s": c, "over_capacity": c > capacity})
    return slots


def priority_sorted(cells: list, scen_order) -> list:
    so = {s: i for i, s in enumerate(scen_order)}
    vo = {v: i for i, v in enumerate(VARIANT_PRIORITY)}
    return sorted(cells, key=lambda x: (so.get(x[0], len(so)), vo.get(x[1], len(vo)), x[1]))


# --------------------------------------------------------------------------- the campaign
def _load(p):
    p = p if os.path.isabs(p) else os.path.join(ROOT, p)
    with open(p) as fh:
        return json.load(fh)


def _load_opt(p):
    p = p if os.path.isabs(p) else os.path.join(ROOT, p)
    try:
        with open(p) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _rel(p):
    return os.path.relpath(p, ROOT) if os.path.isabs(p) else p


def f_tokens():
    return [t for t in TK.campaign_tokens() if t.startswith("C4_F") and not t.startswith("C4_FCELLS")]


def _job(js):
    return ((((js or {}).get("data") or {}).get("run") or {}).get("ci") or {}).get("SLURM_JOB_ID")


def build(fcells_a: str, fcells_b: str, dry: bool, budget_s: float = None, force_parts: int = None,
          runs_only: list = None, prev: dict = None, assign: bool = True) -> dict:
    """The sizing (rates, runs, f-cell packing, cv3) and the slot queue; assign=True lays out generation 1
    (assign_generation1), assign=False leaves the queue in out['_queue'] for reassign()."""
    from campaign33 import DRY
    from skqd.campaign33 import circuits as C
    from skqd.campaign33 import tokens_run as TR
    fa = _load(fcells_a)
    pb = fcells_b if os.path.isabs(fcells_b) else os.path.join(ROOT, fcells_b)
    fb = _load_opt(pb) if os.path.exists(pb) else None
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
    src_a = f"{_rel(fcells_a)} job {_job(fa)}"
    src_b = f"{_rel(fcells_b)} job {_job(fb)}" if fb is not None else f"{_rel(fcells_b)} (absent: not yet harvested)"
    src = f"{src_a}; {src_b}"
    fjs = [(_rel(fcells_a), fa, _job(fa))] + ([(_rel(fcells_b), fb, _job(fb))] if fb is not None else [])
    s3 = _load_opt(os.path.join(ROOT, "validation", "S3.json"))
    s3_best = (((s3 or {}).get("data") or {}).get("cost") or {}).get("seconds_per_shot_best_ladder")
    s3_rate = ({"s_per_shot": float(s3_best), "source": "validation/S3.json data.cost.seconds_per_shot_best_ladder"}
               if s3_best else None)
    sr = scenario_rates(fjs, fit, chunk, s3_rate)
    rates = sr["scenario_rates"]
    shares = {"plan": TR.PLAN_SHARE, "s3quota": TR.QUOTA_SHARE, "fcells": TR.QUOTA_SHARE, "cv3": TR.QUOTA_SHARE}

    def nm(kind, s):
        return n_max(shares[kind], rates[s]["s_per_shot"], budget_s)
    nm_table = {k: {s: nm(k, s) for s in rates} for k in shares}
    ctx = SimpleNamespace(dry=dry)
    idx = C.load_index()
    old = (prev or {}).get("runs") or {}
    old_is_33a = "33a" in str((prev or {}).get("prompt", ""))
    runs, items = {}, {}
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
        s = spec["scenario"]
        cap = nm(spec["kind"], s)
        sp = split_run(plan, chunk, cap, force_parts)
        total = sum(plan.values())
        f010 = pl["plan_f010"]
        if dry and f010:
            f010 = {c: min(DRY["max_shots"], max(1, int(math.ceil(v * DRY["shots_scale"])))) for c, v in f010.items()}
        desc = []
        for i, rr in enumerate(sp["ranges"]):
            desc.append({"content": "frun", "run": run, "token": tok, "scenario": s,
                         "sector": spec["sector"].replace("=", ""), "family": spec["family"], "kind": spec["kind"],
                         "tier": pl["tier"], "tier_reason": pl["tier_reason"], "part": i + 1, "parts": sp["parts"],
                         "chunk": chunk, "stride": chunk, "seed_token_index": TK.token_index(tok, tokens),
                         "seed_rule": TK.SEED_RULE_PARTS, "plan_shots_by_circuit": plan,
                         "plan_f010_by_circuit": f010, "ranges_by_circuit": rr,
                         "shots_by_circuit": {c: SM.range_shots(x) for c, x in rr.items()},
                         "rate_s_per_shot": rates[s]["s_per_shot"], "N_max": cap,
                         "written_by": WRITTEN_BY, "from": src})
        r = {"token": tok, "kind": spec["kind"], "share": spec["share"], "scenario": s,
             "family": spec["family"], "sector": spec["sector"], "tier": pl["tier"],
             "tier_reason": pl["tier_reason"], "circuits": len(plan), "total_shots": total,
             "rate_s_per_shot": rates[s]["s_per_shot"], "rate_label": rates[s]["label"],
             "N_max": cap, "parts": sp["parts"], "part_shots": sp["part_shots"], "split_method": sp["method"],
             "parts_ceil_N_over_N_max": sp["n_ceil"],
             "max_part_seconds_at_rate_x1.25": max(sp["part_shots"]) * rates[s]["s_per_shot"] * CONTINGENCY,
             "part_budget_s": shares[spec["kind"]] * (budget_s - SETUP_S),
             "forced_parts": bool(sp.get("forced")), "part_descriptors": desc, "slots": [tok]}
        o = old.get(run)
        if o is not None:
            ref33a = o.get("sizing_33a") if not old_is_33a else {
                "parts": o.get("parts"), "N_max": o.get("N_max"), "part_shots": o.get("part_shots")}
            if ref33a and ref33a.get("part_shots"):
                ref33a = dict(ref33a)
                ref33a["part1_would_reach"] = min(1.0, (float(ref33a["N_max"]) * reff)
                                                  / (max(ref33a["part_shots"]) * rates[s]["s_per_shot"]))
                ref33a["rule"] = "(N_max_33a x r_ladder) / (largest 33a part x r_s), at most 1"
                r["sizing_33a"] = ref33a
        runs[run] = r
        items[("frun", run)] = [_item("frun", run, d, d["part"], d["parts"]) for d in desc[1:]]
    # ---- dropped f-cells (R5): cost-packed, C4_FCELLS_A's first, C4_FCELLS_B's as their own group
    cell_shots = sum((min(DRY["max_shots"], max(1, int(math.ceil(v * DRY["shots_scale"])))) if dry else v)
                     for v in TR.FCELL_SHOTS.values())
    costs = cell_costs(fjs, rates, cell_shots)
    capacity = shares["fcells"] * (budget_s - SETUP_S) / CONTINGENCY
    groups, offset = [], 0
    for gname, js, path, scen in (("A", fa, fcells_a, SCEN_A), ("B", fb, fcells_b, SCEN_B)):
        if js is None:
            continue
        dropped = [c.split("|") for c in (js["data"].get("cells_dropped") or [])]
        order = priority_sorted(dropped, scen + tuple(s for s in ALL_SCENARIOS if s not in scen))
        packed = pack_fcells(order, costs, capacity)
        for i, sl in enumerate(packed):
            label = FCELL_LABELS[i] if gname == "A" else f"FB{i + 1}"
            d = {"content": "fcells", "group": gname, "label": label, "cells": sl["cells"],
                 "predicted_s": sl["predicted_s"], "capacity_s": capacity, "over_capacity": sl["over_capacity"],
                 "cell_costs_s": {s: costs[s]["seconds"] for s in sorted({c[0] for c in sl["cells"]})},
                 "cell_index_offset": offset, "part": i + 1, "parts": len(packed), "cell_shots": TR.FCELL_SHOTS,
                 "seed_rule": TK.SEED_RULE_PARTS, "written_by": WRITTEN_BY, "from": src,
                 "dropped_by": f"{_rel(path)} data.cells_dropped"}
            offset += len(sl["cells"])
            groups.append(d)
    fc_items = [_item("fcells", None, d, d["part"], d["parts"]) for d in groups]
    if offset * 4 >= SM_WARMUP_INDEX():
        raise ValueError("f-cell circuit offsets would reach the warmup seed slot")
    # ---- CV3 (R6): the equal-shots sample of split NAT-O0 plan runs, in parts at the cv3 share
    cv3 = {}
    for run, r in runs.items():
        if r["parts"] < 2 or r["kind"] != "plan" or r["family"] != "NAT-O0":
            continue
        plan = r["part_descriptors"][0]["plan_shots_by_circuit"]
        ids = list(plan)
        n_eq = TR.cv3_n_eq(plan, dry)
        twoB = 0 if r["sector"] == "B=0" else 2
        mans = {c: C.load_manifest(r["family"], c) for c in ids}
        k5 = TR.cv3_k5_ids(mans, ids, twoB, r["sector"], idx)
        s = r["scenario"]
        cap = nm("cv3", s)
        both = dict({c: n_eq for c in ids}, **{c: n_eq for c in k5})
        sp = split_run(both, chunk, cap, force_parts)
        shots = n_eq * (len(ids) + len(k5))
        e = {"N_eq": n_eq, "k5_circuits": len(k5), "shots": shots, "rate_s_per_shot": rates[s]["s_per_shot"],
             "N_max": cap, "parts": sp["parts"], "part_shots": sp["part_shots"], "split_method": sp["method"],
             "parts_ceil_N_over_N_max": sp["n_ceil"], "sampling_s_at_rate": shots * rates[s]["s_per_shot"],
             "fits_one_slot": shots <= cap}
        if run in CV3_SLOTS or run in CV3_QUEUED_LAST:
            desc = []
            for i, rr in enumerate(sp["ranges"]):
                desc.append({"content": "cv3", "run": run, "token": r["token"], "scenario": s,
                             "sector": r["sector"].replace("=", ""), "family": r["family"], "kind": "cv3",
                             "part": i + 1, "parts": sp["parts"], "chunk": chunk, "stride": chunk,
                             "seed_token_index": TK.token_index(r["token"], tokens), "seed_rule": TK.SEED_RULE_PARTS,
                             "circuit_offsets": {"eq": 100, "k5": 200}, "N_eq": n_eq,
                             "plan_shots_by_circuit": plan, "k5_circuits": k5,
                             "eq_ranges_by_circuit": {c: rr[c] for c in ids},
                             "k5_ranges_by_circuit": {c: rr[c] for c in k5},
                             "shots_by_circuit": {c: SM.range_shots(x) for c, x in rr.items()},
                             "rate_s_per_shot": rates[s]["s_per_shot"], "N_max": cap,
                             "written_by": WRITTEN_BY, "from": src})
            items[("cv3", run)] = [_item("cv3", run, d, d["part"], d["parts"]) for d in desc]
            if run in CV3_SLOTS:
                e["status"] = f"slot: {sp['parts']} part(s) (prompts/33b R6)"
            else:
                e["status"] = (f"not_evaluated: deferred by prompts/33b ({sp['parts']} parts at r_{s} = "
                               f"{rates[s]['s_per_shot']:.5g} s/shot); queued last (R6: after the maintenance if the "
                               "owner wants it)")
            e["part_descriptors"] = desc
        else:
            e["status"] = (f"not_evaluated: deferred by prompts/33b ({sp['parts']} parts at r_{s} = "
                           f"{rates[s]['s_per_shot']:.5g} s/shot)")
        cv3[run] = e
    # ---- the slot queue (A1e)
    queue, seen = [], set()
    for kind, key in SLOT_QUEUE:
        if kind == "fcells":
            sel = [it for it in fc_items if it["descriptor"]["group"] == "A"]
            sel = sel[:1] if key == "A1" else sel[1:]
        else:
            sel = items.get((kind, key), [])
        for it in sel:
            if it["copy"] not in seen:
                queue.append(it)
                seen.add(it["copy"])
    for it in [x for v in items.values() for x in v] + fc_items:      # anything not named in SLOT_QUEUE: at the end
        if it["copy"] not in seen:
            queue.append(it)
            seen.add(it["copy"])
    slots = list(TK.slot_tokens(tokens))
    out = {"written_by": WRITTEN_BY, "prompt": PROMPT,
           "prompts": ["prompts/33a_campaign33_first_wave_reruling.md step D",
                       "prompts/33b_campaign33_scenario_aware_sizing_and_waves.md step A"],
           "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "dry_run": dry, "from": src,
           "from_jsons": {"C4_FCELLS_A": {"path": _rel(fcells_a), "job": _job(fa)},
                          "C4_FCELLS_B": {"path": _rel(fcells_b), "job": _job(fb), "present": fb is not None}},
           "inputs": {"ladder": f"{src_a}: data.ladder.points ({len(pts)} points)",
                      "fastest_mode": f"data.ladder.fastest_mode = {mode}",
                      "cell_timings": [f"{p} (job {j}) data.cells.<cell>.chunks / .seconds" for p, _js, j in fjs],
                      "cells_dropped": [f"{_rel(fcells_a)}: data.cells_dropped",
                                        f"{_rel(fcells_b)}: data.cells_dropped (if present)"],
                      "s3_rate": s3_rate,
                      "plan": "validation/CV_2x3_plan.json via tokens_run.cv_plan at tokens_run.plan_tier",
                      "quota": f"tokens_run.PRODUCTION_SHOTS_PER_SECTOR = {TR.PRODUCTION_SHOTS_PER_SECTOR}"},
           "fit": dict(fit, mode=mode, chunk=chunk, chunk_rule=chosen["rule"], r_eff_s_per_shot=reff,
                       rule="t = c + b chunk (least squares); r_eff = b + c / chunk"),
           "scenario_rates": rates, "rate_rule": sr["rate_rule"], "cell_fits": sr["cell_fits"],
           "budget": {"budget_s": budget_s, "setup_s": SETUP_S, "contingency": CONTINGENCY, "shares": shares,
                      "N_max": {k: nm(k, "E1") for k in ("plan", "s3quota", "fcells")},
                      "N_max_note": "N_max at the E1 rate (the 33a field); per scenario: N_max_by_scenario",
                      "N_max_by_scenario": nm_table,
                      "rule": "N_max(kind, s) = share x (budget - setup) / (1.25 r_s)"},
           "runs": runs,
           "fcells": {"dropped": [c for g in groups for c in g["cells"]], "cell_cost_s": costs,
                      "cells_per_slot": "variable: cost-packed into slot_capacity_s (prompts/33b R5)",
                      "slot_capacity_s": capacity, "cell_shots": cell_shots,
                      "rule": ("first fit in the priority order scenario E1, E2, E3, E4, E5a, E5b, E5c (then "
                               "C4_FCELLS_B's E6a..E7_0.15 as their own group), within a scenario O0, O1, O2, O3, O4, O6; "
                               "cost = the measured seconds of the scenario's most expensive measured cell (prompts/33b R5)"),
                      "slots": [{k: g[k] for k in ("group", "label", "cells", "predicted_s", "over_capacity",
                                                   "cell_index_offset", "part", "parts")} for g in groups]},
           "cv3": cv3, "cv3_rule": {"CV3_SLOTS": list(CV3_SLOTS), "CV3_QUEUED_LAST": list(CV3_QUEUED_LAST),
                                    "source": "prompts/33b R6"},
           "allowlist_33a": "ci/allowed_jobs.campaign33a", "slots_available": len(slots)}
    out["_queue"] = queue
    return assign_generation1(out) if assign else out


def SM_WARMUP_INDEX():
    return SM.Sampler.WARMUP_CIRCUIT_INDEX


def _item(kind, run, d, part, parts):
    from skqd.campaign33 import tokens_run as TR
    return {"kind": kind, "run": run, "label": d.get("label"), "part": int(part), "parts": int(parts),
            "copy": TR.part_copy_name(d), "descriptor": d}


def _slot_desc(d, slot, tokens=None):
    d = dict(d, slot=slot)
    if d["content"] == "fcells":
        d["seed_token_index"] = TK.token_index(slot, tokens)
    return d


def _summary(it, slot=None, gen=None):
    return {k: v for k, v in (("kind", it["kind"]), ("run", it["run"]), ("label", it["label"]), ("part", it["part"]),
                              ("parts", it["parts"]), ("copy", it["copy"]), ("slot", slot), ("generation", gen))
            if v is not None}


def assign_generation1(out: dict) -> dict:
    """Generation 1 (prompts/33b A1e): the first 20 queue items on C4_PART_01..20 in queue order; the rest deferred
    with generation 2 and no file."""
    slots = list(TK.slot_tokens())
    queue = out.pop("_queue")
    files, hist, sq, deferred = {}, {}, [], []
    stamp = out["created"]
    for k, it in enumerate(queue):
        if k < len(slots):
            s = slots[k]
            files[s] = _slot_desc(it["descriptor"], s)
            hist[s] = [dict(_summary(it, s, 1), assigned=stamp)]
            sq.append(dict(_summary(it, s, 1), position=k + 1))
        else:
            deferred.append(dict(_summary(it, None, 2), position=k + 1, status="deferred"))
            sq.append(dict(_summary(it, None, 2), position=k + 1, status="deferred"))
    _finish_slots(out, files, sq, deferred, hist, queue)
    return out


def slot_free(slot: str, current: dict, status_dir: str, validation_dir: str) -> dict:
    """prompts/33b R4: free when ci/status/<slot>.json says done AND the content-named copy of the slot's current
    content exists in validation/ (a slot without content is free unless a request on it is pending)."""
    from skqd.campaign33 import tokens_run as TR
    st = _load_opt(os.path.join(status_dir, slot + ".json"))
    state = (st or {}).get("state")
    if current is None:
        free = st is None or state == "done"
        return {"free": free, "state": state, "content": None,
                "reason": "no content" + ("" if free else f"; ci/status state {state}")}
    copy = TR.part_copy_name(current)
    cp = os.path.join(validation_dir, copy + ".json")
    have = os.path.exists(cp)
    res = None
    if have:
        res = (_load_opt(cp) or {}).get("status")
    free = state == "done" and have
    why = []
    if state != "done":
        why.append(f"ci/status state {state!r} (not done)")
    if not have:
        why.append(f"content-named copy validation/{copy}.json missing")
    return {"free": free, "state": state, "content": copy, "copy_present": have, "copy_status": res,
            "jobid": (st or {}).get("jobid"), "reason": "free" if free else "; ".join(why)}


def reassign(out: dict, prev: dict, parts_dir: str, status_dir: str, validation_dir: str) -> dict:
    """prompts/33b R4 / A1e --reassign: keep every busy slot's content; give each free slot the next deferred item in
    queue order (its file is overwritten); record slot_history.  An item counts as taken when any slot holds or
    has held it (by content-named copy)."""
    tokens = TK.load_tokens()
    slots = list(TK.slot_tokens(tokens))
    queue = out.pop("_queue")
    current = {s: _load_opt(os.path.join(parts_dir, s + ".json")) for s in slots}
    current = {s: d for s, d in current.items() if d is not None and d.get("written_by") == WRITTEN_BY}
    from skqd.campaign33 import tokens_run as TR
    hist = {s: list(v) for s, v in ((prev or {}).get("slot_history") or {}).items()}
    for s, d in current.items():                            # a pre-33b sizing: the current files are generation 1
        if not hist.get(s) or hist[s][-1].get("copy") != TR.part_copy_name(d):
            hist.setdefault(s, []).append({"kind": d["content"], "run": d.get("run"), "label": d.get("label"),
                                           "part": d.get("part"), "parts": d.get("parts"),
                                           "copy": TR.part_copy_name(d), "slot": s,
                                           "generation": len(hist.get(s, [])) + 1,
                                           "assigned": "before this --reassign (read from ci/parts)"})
    taken = {h["copy"] for v in hist.values() for h in v}
    pending = [it for it in queue if it["copy"] not in taken]
    files, freedom = {}, {}
    stamp = out["created"]
    for s in slots:
        cur = current.get(s)
        fr = slot_free(s, cur, status_dir, validation_dir)
        freedom[s] = fr
        if fr["free"] and pending:
            it = pending.pop(0)
            gen = len(hist.get(s, [])) + 1
            if hist.get(s):
                hist[s][-1]["result"] = {"copy_status": fr.get("copy_status"), "jobid": fr.get("jobid")}
            files[s] = _slot_desc(it["descriptor"], s, tokens)
            hist.setdefault(s, []).append(dict(_summary(it, s, gen), assigned=stamp))
            fr["assigned"] = it["copy"]
        elif cur is not None:
            files[s] = cur
    where = {}
    for s, v in hist.items():
        for h in v:
            where[h["copy"]] = (s, h.get("generation"))
    gen_next = 1 + max([len(v) for v in hist.values()] or [1])
    sq, deferred = [], []
    for k, it in enumerate(queue):
        if it["copy"] in where:
            s, g = where[it["copy"]]
            sq.append(dict(_summary(it, s, g), position=k + 1,
                           status="held" if files.get(s) is not None and TR.part_copy_name(files[s]) == it["copy"]
                           else "done (slot re-used)"))
        else:
            deferred.append(dict(_summary(it, None, gen_next), position=k + 1, status="deferred"))
            sq.append(dict(_summary(it, None, gen_next), position=k + 1, status="deferred"))
    out["reassign"] = {"slots": freedom, "rule": ("free = ci/status/<slot>.json state done AND the content-named copy "
                                                  "of the current content in validation/ (prompts/33b R4)"),
                       "status_dir": _rel(status_dir), "validation_dir": _rel(validation_dir)}
    _finish_slots(out, files, sq, deferred, hist, queue)
    return out


def _finish_slots(out, files, sq, deferred, hist, queue):
    from skqd.campaign33 import tokens_run as TR
    held = {TR.part_copy_name(d) for d in files.values()}
    done = {h["copy"] for v in hist.values() for h in v}
    dset = {d["copy"] for d in deferred}
    out["unassigned"] = [_summary(it) for it in queue if it["copy"] not in held | done | dset]
    out["slot_files"] = files
    out["slots"] = {s: dict({k: d.get(k) for k in ("content", "run", "label", "part", "parts", "cells",
                                                   "seed_token_index")}, copy=TR.part_copy_name(d))
                    for s, d in files.items()}
    out["slots_used"] = len(files)
    out["slot_queue"] = sq
    out["deferred"] = deferred
    out["slot_history"] = hist
    slot_of = {h["copy"]: h["slot"] for v in hist.values() for h in v}      # the last slot that held each content
    for run, r in out["runs"].items():                      # which slot holds / held each part >= 2
        for d in r["part_descriptors"][1:]:
            d["slot"] = slot_of.get(TR.part_copy_name(d))
        r["slots"] = [r["token"]] + [d["slot"] or "deferred" for d in r["part_descriptors"][1:]]
    for run, e in out["cv3"].items():
        if "part_descriptors" in e:
            e["slots"] = [slot_of.get(TR.part_copy_name(d), "deferred") for d in e["part_descriptors"]]


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


def print_tables(out):
    f = out["fit"]
    print(f"ladder ({f['mode']}): c {f['c_s']:.4g} s, b {f['b_s_per_shot']:.4g} s/shot, chunk {f['chunk']}, "
          f"r_ladder {f['r_eff_s_per_shot']:.5f} s/shot")
    print("scenario rates (s/shot): " + ", ".join(f"{s} {v['s_per_shot']:.5f} (rho {v['rho']:.3f})"
                                                  for s, v in out["scenario_rates"].items()))
    print(f"{'run':8s} {'scen':8s} {'kind':8s} {'shots':>7s} {'r_s':>8s} {'N_max':>6s} {'parts':>5s} part shots / slots")
    for run, r in out["runs"].items():
        print(f"{run:8s} {r['scenario']:8s} {r['kind']:8s} {r['total_shots']:7d} {r['rate_s_per_shot']:8.5f} "
              f"{r['N_max']:6d} {r['parts']:5d} {r['part_shots']} {r['slots']}")
    for run, e in out["cv3"].items():
        print(f"  cv3 {run:8s} {e['shots']:7d} shots, N_max {e['N_max']}, {e['parts']} part(s): {e['status']}"
              + (f" slots {e['slots']}" if "slots" in e else ""))
    for g in out["fcells"]["slots"]:
        print(f"  f-cells {g['group']}/{g['label']}: {len(g['cells'])} cells, predicted {g['predicted_s']:.1f} s of "
              f"{out['fcells']['slot_capacity_s']:.0f} s, offset {g['cell_index_offset']}")
    for s, d in out["slots"].items():
        print(f"  {s}: {d['copy']}")
    print(f"deferred ({len(out['deferred'])}): " + ", ".join(d["copy"] for d in out["deferred"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reassign", action="store_true",
                    help="prompts/33b R4: give free slots (ci/status done + content-named copy present) the next "
                         "deferred items of the slot queue")
    ap.add_argument("--fcells-a", default=None)
    ap.add_argument("--fcells-b", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--parts-dir", default=None)
    ap.add_argument("--status-dir", default=None, help="--reassign: ci/status (default)")
    ap.add_argument("--validation-dir", default=None, help="--reassign: validation/ (default; dryrun/ with --dry-run)")
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
    prev = _load_opt(out_path)
    if not a.reassign and prev and any(len(v) > 1 for v in (prev.get("slot_history") or {}).values()):
        print(f"refused: {_rel(out_path)} records re-used slots (slot_history); a plain run would reset them to "
              "generation 1 -- use --reassign")
        return 2
    out = build(fa, fb, a.dry_run, a.budget_s, a.force_parts, a.runs, prev=prev, assign=not a.reassign)
    if a.reassign:
        out = reassign(out, prev, parts_dir, a.status_dir or os.path.join(ROOT, "ci", "status"),
                       a.validation_dir or os.path.join(ROOT, "validation", sub))
    written = write(out, out_path, parts_dir)
    print_tables(out)
    print(f"slots used {out['slots_used']} of {out['slots_available']}; deferred {len(out['deferred'])}; "
          f"unassigned (neither assigned nor deferred) {len(out['unassigned'])}")
    print(f"wrote {_rel(out_path)} and {len(written)} slot file(s) in {_rel(parts_dir)}")
    return 0 if not out["unassigned"] else 2


if __name__ == "__main__":
    sys.exit(main())
