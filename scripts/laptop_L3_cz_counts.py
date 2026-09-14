#!/usr/bin/env python3
"""
Laptop gate L3 (= measurement for gate S2) — transpiled CZ counts of the exact
block-unitary circuits at 2x2, per term and per coarse step, all-to-all and on a
heavy-hex coupling map.

Budget (manual Step 4.3): <= 250 CZ per first-order step at 2x2, <= 500 at 2x3;
gate S2 = "routed CZ per coarse step <= 500 on the target map; noiseless compiled
circuits leak-free".  The exact hopping unitaries are synthesized generically by
Qiskit (quantum Shannon decomposition), which is expected to be far above the
budget: this script MEASURES the baseline and records it; reducing it (structured
hopping gates, see reports/circuit_structure.md) is the planner's S2 task.

Usage: python scripts/laptop_L3_cz_counts.py [--heavy-hex 3] [--level 3]
Expected runtime: minutes (an 8-qubit UnitaryGate can take a while at level 3).
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402

BUDGET_2x2 = 250


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heavy-hex", type=int, default=3, help="heavy-hex distance for the routed count (0 = skip)")
    ap.add_argument("--level", type=int, default=3)
    args = ap.parse_args()
    t0 = time.time()
    R = GateResult("L3", "Transpiled CZ counts of the exact 2x2 circuits (S2 measurement)")
    from skqd import circuits_qiskit as cq
    M = Model(2)
    F = CircuitFactory(M, 4.0)
    n = Codec(M.basis).n_qubits
    ref = M.reference(4.0, 0)
    theta = ref.dt
    rows = []
    per_term = {}
    for name, gates in (("diag", F.diag_gates(theta)),) + tuple((f"hop{l}", F.hop_gates(l, theta)) for l in range(4)) \
            + (("plaq0 (structured)", F.plaq_gates(0, theta, True)),):
        res = cq.transpile_counts(gates, n, optimization_level=args.level)
        per_term[name] = res["cz"]
        rows.append([name, res["cz"], res["depth"]])
    step_gates = F.coarse_step(references(M.basis, 0)[0], 1, theta)
    res_all = cq.transpile_counts(step_gates, n, optimization_level=args.level)
    rows.append(["coarse step k=1 (all-to-all)", res_all["cz"], res_all["depth"]])
    routed = None
    if args.heavy_hex:
        from qiskit.transpiler import CouplingMap
        cmap = CouplingMap.from_heavy_hex(args.heavy_hex)
        routed = cq.transpile_counts(step_gates, n, coupling_map=cmap, optimization_level=args.level)
        rows.append([f"coarse step k=1 (heavy-hex d={args.heavy_hex}, routed)", routed["cz"], routed["depth"]])
    R.add("CZ per coarse step, all-to-all", res_all["cz"], f"<= {BUDGET_2x2} (manual budget)", res_all["cz"] <= BUDGET_2x2)
    if routed:
        R.add("CZ per coarse step, routed on heavy-hex", routed["cz"], f"<= {BUDGET_2x2}", routed["cz"] <= BUDGET_2x2)
    R.data = {"per_term_cz": per_term, "all_to_all": res_all, "routed": routed}
    R.runtime_s = time.time() - t0
    R.save()
    write_report("L3_cz_counts.md", f"""# Laptop gate L3 — transpiled CZ counts at 2x2 (gate S2 measurement)

**Status: {'PASS' if R.passed else 'FAIL (expected for the generic baseline — this is the S2 work item)'}** —
`scripts/laptop_L3_cz_counts.py`, optimization level {args.level}.  {env_block()}  Runtime {R.runtime_s:.0f} s.

{md_table(["circuit", "CZ", "depth"], rows)}

{R.criteria_table()}

Interpretation: the diagonal and the structured plaquette gates are cheap; the four exact hopping block
unitaries (6- and 8-qubit `UnitaryGate`s) dominate.  Their internal structure (chains of at most three
configurations, four flip patterns per link, angles depending on a handful of control bits — see
`reports/circuit_structure.md`) is what a structured decomposition must exploit to reach the budget.
""")
    print(R.criteria_table())
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
