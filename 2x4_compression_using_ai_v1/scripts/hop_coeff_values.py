"""Evidence for report 004 §2.4: the distinct |coefficients| of every theta-multiplexor table of every hop in the
bright vertex frame (angle-linear synthesis, operator class, k = 1), for 2x4 and 2x3.  The slot rotation is
R(theta c), c = 2 d with d the pair coupling.  Writes data/hop_coefficient_values.json."""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from c2x4 import linsynth                                           # noqa: E402
from c2x4.env import write_json                                     # noqa: E402
from c2x4.hopframe import framed_gates, vertex_bright_frame         # noqa: E402
from c2x4.problem import get_problem                                # noqa: E402

t0 = time.time()
out = {}
for lx in (4, 3):
    P = get_problem(lx)
    for nm in [t for t in P.term_names() if t.startswith("hop")]:
        st = []
        with linsynth.use_linear("lp"):
            framed_gates(P, nm, P.theta(0, 1), vertex_bright_frame(P, nm), stats=st)
        vals = sorted({round(abs(v), 10) for s in st if s.get("theta_linear")
                       for v in s["reduced_table"]["fixed_val"]})
        h = np.asarray(P.local(nm)[2])
        hv = sorted({round(float(v), 8) for v in np.abs(h[np.abs(h) > 1e-12])})
        out[f"2x{lx}:{nm}"] = {"distinct_abs_coefficients_c": vals, "distinct_abs_hamiltonian_elements": hv,
                               "pair_couplings_d": sorted({round(v / 2, 10) for v in vals if v > 0})}
        print(lx, nm, vals)
write_json("data/hop_coefficient_values.json", out, produced_by="2x4_compression_using_ai_v1/scripts/hop_coeff_values.py",
           parameters={"frame": "vertex_bright_frame", "synthesis": "linsynth lp", "theta": "dt of B=0, k=1"},
           t_start=t0)
