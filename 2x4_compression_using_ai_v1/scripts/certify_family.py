"""MWS certificates (C4 step 2, notes/010): for every walk-form multiplexor of the best proposal of every (reference,
term) [class B] or term [class A] of an archive, the exact minimum Walsh support of its reduced angle table by MILP
(src/c2x4/certify.py) against the support the circuit uses.  Tables are theta-free in the angle-linear synthesis, so
one build per (reference, term) at k = 1 covers every k.

Writes data/cert_<archive>_<class>[_<label>].json.

Usage: python scripts/certify_family.py --archive it6 --cls operator [--refs 102,230] [--time-limit 120] [--lx 4]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4 import linsynth, sparsemux                                   # noqa: E402
from c2x4.certify import cached_min_walsh_support                      # noqa: E402
from c2x4.env import STUDY, write_json                                 # noqa: E402
from c2x4.family import get_reach                                      # noqa: E402
from c2x4.problem import get_problem                                   # noqa: E402
from c2x4.proposals import PROPOSALS                                   # noqa: E402
from c2x4.reach import contract_states                                 # noqa: E402

COLLECT = []


def _wrap(fn):
    def g(*a, stats=None, **kw):
        st = [] if stats is None else stats
        n0 = len(st)
        out = fn(*a, stats=st, **kw)
        COLLECT.extend(st[n0:])
        return out
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True)
    ap.add_argument("--cls", required=True, choices=["operator", "input"])
    ap.add_argument("--refs", default="all")
    ap.add_argument("--time-limit", type=float, default=120.0)
    ap.add_argument("--lx", type=int, default=4)
    ap.add_argument("--label", default="")
    ap.add_argument("--max-wall", type=float, default=1700.0)
    args = ap.parse_args()
    t0 = time.time()
    linsynth.lin_two_level = _wrap(linsynth.lin_two_level)
    linsynth.sw_two_level = _wrap(linsynth.sw_two_level)
    sparsemux.sw_two_level = _wrap(sparsemux.sw_two_level)
    P = get_problem(args.lx)
    from c2x4.env import archive_path
    with open(archive_path(args.archive)) as fh:
        arch = json.load(fh)
    jobs = []
    if args.cls == "operator":
        for nm in P.term_names():
            jobs.append((None, None, nm, arch["operator"][nm]["best"]["label"]))
    else:
        want = None if args.refs == "all" else {int(v) for v in args.refs.split(",")}
        for key, row in arch["input"].items():
            if want is not None and int(key) not in want:
                continue
            for nm in P.term_names():
                jobs.append((int(row["twoB"]), int(key), nm, row[nm]["best"]["label"]))
    R = get_reach(P)
    rows = []
    truncated = False
    for twoB, ref, nm, lab in jobs:
        if time.time() - t0 > args.max_wall:
            truncated = True
            break
        th = P.theta(0 if twoB is None else twoB, 1)
        con = loc = None
        if ref is not None:
            loc = R.local_reachable(ref, nm)
            con = contract_states(P, nm, loc)
        COLLECT.clear()
        PROPOSALS[lab]["fn"](P, nm, th, con, loc)
        for j, s in enumerate(COLLECT):
            rt = s.get("reduced_table")
            row = {"reference": ref, "term": nm, "proposal": lab, "mux": j, "flip_pattern": s["flip_pattern"],
                   "n_controls": s["n_controls"], "walk_cnots": s["walk_cnots"], "support_used": s.get("support_used"),
                   "frame_cnots": s["frame_cnots"], "flag_cnots": s.get("flag_cnots", 0)}
            if rt is None:
                row["status"] = "no reduced table (package Gray chain fallback)"
                rows.append(row)
                continue
            c = cached_min_walsh_support(rt["m"], rt["fixed_idx"], rt["fixed_val"], time_limit=args.time_limit)
            row.update({"m": rt["m"], "n_fixed": c["n_fixed"], "n_free": c["n_free"], "support_lb": c["support_lb"],
                        "support_ub_found": c["support_ub"], "milp_status": c["status"], "M_theta": c["M_theta"],
                        "certified_optimal": bool(c["support_lb"] is not None and s.get("support_used") is not None
                                                  and c["support_lb"] == s["support_used"]),
                        "walk_lower_bound": (c["support_lb"] + 1) if c["support_lb"] else 0,
                        "walk_optimal": bool(c["support_lb"] is not None and c["support_lb"] == s.get("support_used")
                                             and s["walk_cnots"] == c["support_lb"] + 1)})
            rows.append(row)
        print(f"{ref} {nm} {lab}: {len(COLLECT)} mux, certified "
              f"{sum(1 for r in rows if r['term'] == nm and r['reference'] == ref and r.get('certified_optimal'))}",
              flush=True)
    cert = [r for r in rows if "support_lb" in r]
    summary = {"n_multiplexors": len(rows), "n_with_table": len(cert),
               "n_certified_optimal_support": sum(1 for r in cert if r["certified_optimal"]),
               "n_walk_optimal": sum(1 for r in cert if r["walk_optimal"]),
               "n_milp_not_optimal_status": sum(1 for r in cert if "optimal" not in r["milp_status"]
                                                and "unique" not in r["milp_status"]),
               "support_used_total": sum(r["support_used"] or 0 for r in cert),
               "support_lb_total": sum(r["support_lb"] or 0 for r in cert),
               "walk_used_total": sum(r["walk_cnots"] for r in cert),
               "walk_lb_total": sum(r["walk_lower_bound"] for r in cert),
               "gap_support": [r for r in cert if not r["certified_optimal"]][:50],
               "truncated": truncated}
    lab = f"_{args.label}" if args.label else ""
    sub = "c2x3/" if args.lx == 3 else ""
    p = write_json(f"data/{sub}cert_{args.archive}_{args.cls}{lab}.json", {"rows": rows, "summary": summary},
                   produced_by="2x4_compression_using_ai_v1/scripts/certify_family.py",
                   parameters=vars(args), t_start=t0)
    print({k: v for k, v in summary.items() if k != "gap_support"})
    print("wrote", p)


if __name__ == "__main__":
    main()
