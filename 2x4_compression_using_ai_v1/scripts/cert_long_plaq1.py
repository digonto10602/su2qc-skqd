"""Longer MILP (1 500 s) on the one class-A v2 multiplexor whose certificate hit the 300 s limit (plaq1, mux 6 of
data/cert_it6_operator.json).  Writes data/cert_it6_operator_plaq1_long.json."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from c2x4 import linsynth, sparsemux                         # noqa: E402
from c2x4.certify import min_walsh_support                   # noqa: E402
from c2x4.env import write_json                              # noqa: E402
from c2x4.problem import get_problem                         # noqa: E402
from c2x4.proposals import PROPOSALS                         # noqa: E402

t0 = time.time()
P = get_problem(4)
got = []
orig = linsynth.lin_two_level


def spy(*a, stats=None, **kw):
    st = []
    out = orig(*a, stats=st, **kw)
    got.extend(st)
    return out


linsynth.lin_two_level = spy
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "archive_it6.json")) as fh:
    lab = json.load(fh)["operator"]["plaq1"]["best"]["label"]
PROPOSALS[lab]["fn"](P, "plaq1", P.theta(0, 1), None, None)
big = max(got, key=lambda s: s["reduced_table"]["m"])
rt = big["reduced_table"]
r = min_walsh_support(rt["m"], rt["fixed_idx"], rt["fixed_val"], time_limit=1500.0)
out = {"proposal": lab, "m": rt["m"], "support_used": big["support_used"], "walk_cnots": big["walk_cnots"],
       "support_lb": r["support_lb"], "support_ub_found": r["support_ub"], "status": r["status"],
       "M_theta": r["M_theta"], "milp_wall_s": r["wall_s"]}
print(out)
write_json("data/cert_it6_operator_plaq1_long.json", out, produced_by="2x4_compression_using_ai_v1/scripts/cert_long_plaq1.py",
           parameters={"time_limit_s": 1500.0}, t_start=t0)
