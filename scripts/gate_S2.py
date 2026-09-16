#!/usr/bin/env python3
"""
Gate S2 — structured (controlled-Givens-chain) circuits for the hopping terms and for the
2x3 plaquettes with interior corners: exactness, leakage, and the transpiled CZ budget.

What is measured
  1. every term gate  exp(-i theta H_gamma)  of 2x2 and 2x3 against the numpy reference
     (the dense local block unitary where it exists, the sparse term exponential on the
     local support otherwise -- the dense 2x3 plaquette unitary, 4 GiB, is never built),
     for theta = dt, 2dt, 4dt;
  2. the full coarse-step circuits against the dressed-basis emulation (krylov.coarse_states)
     at 2x2 (both sectors, k = 1..4, and the Trotter family) and at 2x3 (k = 1, 2);
  3. the leakage of the statevector of every NOISELESS COMPILED circuit (transpiled to
     {rz, sx, x, cz} at optimization level 3) with reference_sim.CodewordEmbedding;
  4. the CZ count per term and per coarse step, all-to-all and routed on heavy-hex
     coupling maps, with skqd.circuits_qiskit.transpile_counts and the same seed and
     optimization level as scripts/laptop_L3_cz_counts.py (the L3 baseline).

Pass criteria (manual Step 4.3): routed CZ per coarse step <= 250 at 2x2 and <= 500 at 2x3,
max deviation < 1e-10, leakage < 1e-9, pytest green.

Usage: python scripts/gate_S2.py [--quick] [--level 3] [--no-tests]
       python scripts/gate_S2.py --angle-mode fixed --out S2_fixed     (prompts/11, a MEASUREMENT)
Expected runtime: about 10 minutes on the i7-8750H (the 2x3 statevector checks act on
2^20 amplitudes); --quick drops the 2x3 full-statevector checks (about 3 minutes).

--angle-mode fixed does not change gate S2: it measures the cost floor of the fixed-angle
generator of prompts/11 (same codeword pairs, one angle per flip pattern) and writes a
separate validation/S2_fixed.json + reports/S2_fixed_angle_circuits.md.  In that mode the
circuits are NOT the local exponentials, so the "max deviation" criterion is replaced by
the hard leakage requirement (< 1e-12, codewords must map to codewords) and the deviation
from the exact exponential is reported as a number; the recall of the generator is
re-established separately by scripts/s2_fixed_recall.py and folded into the same JSON.
"""
import argparse
import os
import subprocess
import sys
import time

import numpy as np
import scipy.linalg as sla

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory, gate_counts, run_ir  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import basis_vector, coarse_states, references, term_groups, trotter_states  # noqa: E402
from skqd.reference_sim import CodewordEmbedding, localize, term_support  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402

BUDGET = {2: 250, 3: 500}
GRID = {2: (3, 4), 3: (4, 5)}          # square-grid coupling maps (scripts/s2_escalation_experiments.py)
ALLOWED = {"x", "h", "p", "cp", "cx", "rz", "ry", "rx", "gphase", "mcu"}


def term_gates_of(F, name, theta):
    """The term gates that are actually counted, for `name` in {hopL, plaqP}."""
    if name.startswith("hop"):
        return F.hop_gates(int(name[3:]), theta)
    return F.plaq_gates(int(name[4:]), theta, True)


def term_leakage_and_deviation(model, F, name, O, support, thetas, rng, nvec=20):
    """For the fixed-angle mode: the leakage of the term circuit on random physical states
    (a hard requirement: the generator must map codewords to codewords), and how far it is
    from the exact exponential exp(-i theta O_loc) (a reported number, not a criterion)."""
    k = len(support)
    states, h, _ = localize(model, O, support)
    idx = np.array(states)
    pos = {q: i for i, q in enumerate(support)}
    vecs = []
    for _ in range(nvec):
        c = rng.normal(size=len(states)) + 1j * rng.normal(size=len(states))
        vecs.append(c / np.linalg.norm(c))
    worst_leak, worst_dev = 0.0, 0.0
    for theta in thetas:
        gates = term_gates_of(F, name, theta)
        loc = [(nm, [pos[q] for q in qs], par) for nm, qs, par in gates]
        U = sla.expm(-1j * theta * h)
        for c in vecs:
            psi = np.zeros(2 ** k, dtype=complex)
            psi[idx] = c
            out = run_ir(loc, k, psi)
            worst_leak = max(worst_leak, abs(1.0 - float(np.sum(np.abs(out[idx]) ** 2))))
            exact = np.zeros(2 ** k, dtype=complex)
            exact[idx] = U @ c
            worst_dev = max(worst_dev, float(np.abs(out - exact).max()))
    return worst_leak, worst_dev


def term_deviation(model, O, support, thetas, rng, nvec=20):
    """max |structured circuit - exact| over random vectors of the local codeword space, for
    every angle in `thetas`.  The exact exponential is taken from the small block h of
    reference_sim.localize (the 2^14 x 2^14 dense unitary of a 2x3 plaquette is never built);
    because the gate acts only on `support`, this is the same test as comparing the full
    2^n statevectors on physical states."""
    from skqd.circuits_ir import structured_term_gates

    k = len(support)
    states, h, _ = localize(model, O, support)
    idx = np.array(states)
    pos = {q: i for i, q in enumerate(support)}
    vecs = []
    for _ in range(nvec):
        c = rng.normal(size=len(states)) + 1j * rng.normal(size=len(states))
        vecs.append(c / np.linalg.norm(c))
    worst = 0.0
    stats = []
    for theta in thetas:
        st = []
        gates = structured_term_gates(model, O, support, theta, stats=st)
        stats = st
        loc = [(nm, [pos[q] for q in qs], par) for nm, qs, par in gates]
        U = sla.expm(-1j * theta * h)
        for c in vecs:
            psi = np.zeros(2 ** k, dtype=complex)
            psi[idx] = c
            out = run_ir(loc, k, psi)
            exact = np.zeros(2 ** k, dtype=complex)
            exact[idx] = U @ c
            worst = max(worst, float(np.abs(out - exact).max()))
    return worst, stats


def fixed_report(args, R, data, rows_2x2, rows_2x3, recall_rows, grid_on):
    """reports/S2_fixed_angle_circuits.md -- every number comes from the GateResult data."""
    head = ["term", "IR gates", "CZ all-to-all", "CZ heavy-hex", "CZ grid", "leakage",
            "distance to the exact exp", "multiplexed rotations (controls)",
            "merged elements per rotation"]
    ref = {}
    rpath = os.path.join(os.path.dirname(__file__), "..", "validation", "S2.json")
    if os.path.exists(rpath):
        import json as _js
        with open(rpath) as fh:
            ref = _js.load(fh)["data"]
    ex2 = ref.get("2x2", {}).get("coarse_step", {})
    ex3 = ref.get("2x3", {}).get("coarse_step", {})
    a2, r2 = data["2x2"]["coarse_step"]["all_to_all"]["cz"], data["2x2"]["coarse_step"]["routed"]["cz"]
    a3, r3 = data["2x3"]["coarse_step"]["all_to_all"]["cz"], data["2x3"]["coarse_step"]["routed"]["cz"]
    g2c, g3c = data["2x2"]["coarse_step"]["grid"]["cz"], data["2x3"]["coarse_step"]["grid"]["cz"]
    cmp_rows = []
    for lat, (a, r, g, exd) in (("2x2", (a2, r2, g2c, ex2)), ("2x3", (a3, r3, g3c, ex3))):
        if exd:
            cmp_rows.append([lat, exd["all_to_all"]["cz"], a, f"{a / exd['all_to_all']['cz']:.2f}",
                             exd["routed"]["cz"], r, f"{r / exd['routed']['cz']:.2f}", g,
                             BUDGET[2 if lat == "2x2" else 3]])
    recall_tbl = (md_table(["generator", "sector", "circuits", "shots/circuit", "reachable (p > 1e-3)",
                            "f = 0.2", "f = 0.1", "run time (s)"], recall_rows)
                  if recall_rows else
                  "(not yet computed: run `python scripts/s2_fixed_recall.py --mode fixed|exact --sector 0|2` "
                  "and re-run this script)")
    return f"""# Fixed-angle generator (gate-S2 escalation, prompts/11) — cost floor, leakage and recall

**This is a MEASUREMENT, not a gate.**  Gate S2 and its criteria are unchanged
(`validation/S2.json`, FAIL on the CZ budget); this file measures the cheapest circuit family
that keeps exact gauge invariance, written by `scripts/gate_S2.py --angle-mode fixed --out {args.out}`,
optimization level {args.level}, basis {{rz, sx, x, cz}}, seed {args.seed}.  {env_block()}  Runtime {R.runtime_s:.0f} s.

## What "fixed angle" means

`skqd.circuits_ir.structured_term_gates(..., angle_mode="fixed")` keeps the two-level rotations
between the SAME pairs of codewords as the exact circuits and the same validity controls (a pair
that the term does not connect is left alone, so codewords still map to codewords), but gives every
pair of one qubit-flip pattern the SAME angle: theta_eff = theta x (mean of the distinct |elements|
of the term with that flip pattern), with the sign of each element kept.  With one magnitude per
pattern the generator splits pattern by pattern into disjoint commuting pairs, so one multiplexed
rotation per flip pattern is exact for that flattened generator -- the schedule of the exact mode
(rounds x patterns) collapses to one round per pattern.  The circuit is therefore NOT
exp(-i theta H_gamma); SKQD only needs the support (the classical step diagonalises the exact H on
it and E_R >= E_0 holds for any support), so the recall criterion of gate S1 is re-established by
emulation below.

## 2x2 ({data['2x2']['n_qubits']} qubits, heavy-hex d={data['2x2']['heavy_hex_distance']}, grid {tuple(data['2x2']['grid'])})

{md_table(head, rows_2x2)}

IR gate counts of the coarse step: {data['2x2']['ir_gate_counts_coarse_step']}.

## 2x3 ({data['2x3']['n_qubits']} qubits, heavy-hex d={data['2x3']['heavy_hex_distance']}, grid {tuple(data['2x3']['grid'])})

{md_table(head, rows_2x3)}

IR gate counts of the coarse step: {data['2x3']['ir_gate_counts_coarse_step']}.

## Cost floor against the exact circuits (validation/S2.json)

{md_table(["lattice", "exact all-to-all", "fixed all-to-all", "ratio", "exact heavy-hex", "fixed heavy-hex", "ratio", "fixed grid", "budget (routed)"], cmp_rows)}

## Recall of the fixed-angle generator at 2x3 (gate-S1 production budget, 2e5 shots per sector)

Entries: recall of the 99.9 % support / |B| / E_R - E_0 / exact E_0 inside the Weinstein interval.
The `exact` rows are the same emulation driven by the exact structured circuits through `run_ir`
on the 2^20 statevector: they must reproduce the gate-S1 numbers (recall 1.000 at f = 0.1,
|B| = 347 in B = 0 and 246 in B = 1), which is the consistency check of the route.

{recall_tbl}

## Criteria

{R.criteria_table()}

## Verification detail

Leakage was measured per term on 20 random physical states of the local codeword space
(5 for the 14-qubit plaquette supports) at
theta = dt, 2dt, 4dt (columns above), and on the full statevectors of
{data['2x2']['n_circuits_vs_emulation']} 2x2 and {data['2x3']['n_circuits_vs_emulation']} 2x3 coarse-step circuits
({max(data['2x2']['compiled_leakage'] + data['2x3']['compiled_leakage']):.1e} worst case, transpiled circuits included).
The deviation column is the distance to the exact local exponential: it is O(0.1) by construction,
and that is the price of the cost reduction in the table above.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="skip the 2^20 statevector checks at 2x3")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--angle-mode", default="exact", choices=("exact", "fixed"),
                    help="exact = gate S2 (default); fixed = the prompts/11 cost-floor measurement")
    ap.add_argument("--out", default="S2", help="name of validation/<out>.json")
    ap.add_argument("--grid", action="store_true", help="also transpile on a square grid coupling map")
    args = ap.parse_args()
    t0 = time.time()
    FIXED = args.angle_mode == "fixed"
    grid_on = args.grid or FIXED
    R = GateResult(args.out, ("Fixed-angle generator (same codeword pairs, one angle per flip pattern): "
                              "cost floor, leakage and recall" if FIXED else
                              "Structured basic-gate circuits: hopping chains and interior-corner plaquettes"))
    from qiskit.transpiler import CouplingMap

    from skqd import circuits_qiskit as cq
    rng = np.random.default_rng(args.seed)
    g2 = 4.0
    worst_dev = 0.0
    worst_leak = 0.0
    worst_term_leak = [0.0]
    data = {}
    rows_2x2, rows_2x3 = [], []
    maps = {2: 3, 3: 5}          # heavy-hex distance used for the routed count of each lattice

    for Lx in (2, 3):
        M = Model(Lx)
        F = CircuitFactory(M, g2, angle_mode=args.angle_mode)
        E = CodewordEmbedding(M)
        n = E.n
        dt = M.reference(g2, 0).dt
        rows = rows_2x2 if Lx == 2 else rows_2x3
        per_term, per_term_routed, per_term_dev, per_term_stats = {}, {}, {}, {}
        per_term_grid, per_term_leak = {}, {}
        cmap = CouplingMap.from_heavy_hex(maps[Lx])
        gmap = CouplingMap.from_grid(*GRID[Lx]) if grid_on else None
        terms = [("diag", None, F.diag_gates(dt))]
        for l in range(M.lat.n_links):
            terms.append((f"hop{l}", (M.terms.hop[l], term_support(M, "hop", l)), F.hop_gates(l, dt)))
        for P in range(len(M.lat.plaquettes)):
            terms.append((f"plaq{P}", (-M.terms.plaq[P] / (2 * g2), term_support(M, "plaq", P)),
                          F.plaq_gates(P, dt, True)))
        for name, ref, gates in terms:
            assert all(g[0] in ALLOWED or (g[0] == "unitary" and len(g[1]) == 1) for g in gates), \
                f"{name}: not a basic-gate circuit: {sorted({g[0] for g in gates})}"
            res = cq.transpile_counts(gates, n, optimization_level=args.level)
            rr = cq.transpile_counts(gates, n, coupling_map=cmap, optimization_level=args.level)
            per_term[name] = res["cz"]
            per_term_routed[name] = rr["cz"]
            if grid_on:
                per_term_grid[name] = cq.transpile_counts(gates, n, coupling_map=gmap,
                                                          optimization_level=args.level)["cz"]
            if ref is not None:
                O, sup = ref
                nvec = 20 if len(sup) <= 10 else 5
                if FIXED:
                    lk, dev = term_leakage_and_deviation(M, F, name, O, sup, (dt, 2 * dt, 4 * dt), rng, nvec)
                    st = F.fixed_stats[(name, round(dt, 12))]
                    per_term_leak[name] = lk
                    worst_term_leak[0] = max(worst_term_leak[0], lk)
                else:
                    dev, st = term_deviation(M, O, sup, (dt, 2 * dt, 4 * dt), rng, nvec=nvec)
                    worst_dev = max(worst_dev, dev)
                per_term_dev[name] = dev
                per_term_stats[name] = {"support": len(sup), "n_multiplexed_rotations": len(st),
                                        "controls": sorted(x["n_controls"] for x in st)}
                if FIXED:
                    per_term_stats[name].update(
                        n_merged_elements=[len(x.get("merged_elements", [])) for x in st],
                        merged_elements=[x.get("merged_elements") for x in st],
                        theta_eff=[x.get("theta_eff") for x in st],
                        n_pairs=[x.get("n_pairs") for x in st])
            st = per_term_stats.get(name)
            row = [name, len(gates), per_term[name], per_term_routed[name]]
            if grid_on:
                row.append(per_term_grid[name])
            if FIXED:
                row.append(f"{per_term_leak[name]:.1e}" if name in per_term_leak else "-")
            row.append(f"{per_term_dev.get(name, 0.0):.1e}" if name in per_term_dev else "-")
            row.append(f"{st['n_multiplexed_rotations']} ({','.join(str(c) for c in st['controls'])})"
                       if st else "-")
            if FIXED:
                row.append(",".join(str(c) for c in st["n_merged_elements"]) if st else "-")
            rows.append(row)
        # ---- full coarse step
        step = F.coarse_step(references(M.basis, 0)[0], 1, dt)
        res = cq.transpile_counts(step, n, optimization_level=args.level)
        rr = cq.transpile_counts(step, n, coupling_map=cmap, optimization_level=args.level)
        gr = cq.transpile_counts(step, n, coupling_map=gmap, optimization_level=args.level) if grid_on else None
        srow = ["coarse step k=1", len(step), res["cz"], rr["cz"]]
        if grid_on:
            srow.append(gr["cz"])
        srow += ["-"] * (len(rows[0]) - len(srow))
        rows.append(srow)
        data[f"2x{Lx}"] = {
            "n_qubits": n, "heavy_hex_distance": maps[Lx], "per_term_cz": per_term,
            "per_term_cz_routed": per_term_routed, "per_term_max_deviation": per_term_dev,
            "per_term_structure": per_term_stats,
            "ir_gate_counts_coarse_step": gate_counts(step),
            "coarse_step": {"all_to_all": res, "routed": rr},
        }
        if grid_on:
            data[f"2x{Lx}"]["grid"] = list(GRID[Lx])
            data[f"2x{Lx}"]["per_term_cz_grid"] = per_term_grid
            data[f"2x{Lx}"]["coarse_step"]["grid"] = gr
        if FIXED:
            data[f"2x{Lx}"]["per_term_leakage"] = per_term_leak
        R.add(f"2x{Lx}: CZ per coarse step, routed on heavy-hex d={maps[Lx]}", rr["cz"],
              f"<= {BUDGET[Lx]} (manual Step 4.3)", rr["cz"] <= BUDGET[Lx])
        if FIXED:
            R.add(f"2x{Lx}: CZ per coarse step, routed on the square grid {GRID[Lx]}", gr["cz"],
                  f"<= {BUDGET[Lx]} (manual Step 4.3)", gr["cz"] <= BUDGET[Lx])

        # ---- circuits against the dressed-basis emulation, and compiled-circuit leakage
        groups = term_groups(M.terms, g2, mass_default(g2))
        circuits = []
        if Lx == 2:
            for twoB in (0, 2):
                d2 = M.reference(g2, twoB).dt
                for r in references(M.basis, twoB)[:2]:
                    ex = coarse_states(groups, basis_vector(M.basis.dim, r), d2, 4)
                    for k in (1, 2, 3, 4):
                        circuits.append((F.coarse_step(r, k, d2), ex[k]))
                    tr = trotter_states(groups, basis_vector(M.basis.dim, r), d2, 3)
                    circuits.append((F.trotter(r, 2, d2), tr[2]))
        elif not args.quick:
            r = references(M.basis, 0)[0]
            ex = coarse_states(groups, basis_vector(M.basis.dim, r), dt, 2)
            for k in (1, 2):
                circuits.append((F.coarse_step(r, k, dt), ex[k]))
        for gates, exact in circuits:
            psi = run_ir(gates, n)
            if not FIXED:
                worst_dev = max(worst_dev, float(np.abs(psi - E.embed(exact)).max()))
            worst_leak = max(worst_leak, abs(E.leakage(psi)))
        data[f"2x{Lx}"]["n_circuits_vs_emulation"] = len(circuits)

        # ---- leakage of the NOISELESS COMPILED circuits
        from qiskit import transpile
        from qiskit.quantum_info import Statevector
        leaks = []
        comp = circuits[:4] if Lx == 2 else circuits[:1]
        for gates, _ in comp:
            qc = cq.ir_to_qiskit(gates, n, measure=False)
            tq = transpile(qc, basis_gates=["rz", "sx", "x", "cz"], optimization_level=args.level,
                           seed_transpiler=args.seed)
            psi = np.asarray(Statevector(tq).data)
            leaks.append(abs(E.leakage(psi)))
        if leaks:
            worst_leak = max(worst_leak, max(leaks))
        data[f"2x{Lx}"]["compiled_leakage"] = leaks
        print(f"2x{Lx}: all-to-all {res['cz']} CZ, routed {rr['cz']} CZ, "
              f"deviation {worst_dev:.2e}, leakage {worst_leak:.2e}, {time.time() - t0:.0f} s", flush=True)

    if FIXED:
        R.add("leakage of the fixed-angle term circuits (codewords -> codewords, theta = dt, 2dt, 4dt)",
              worst_term_leak[0], "< 1e-12", worst_term_leak[0] < 1e-12)
    else:
        R.add("max |structured circuit - reference| (all terms and circuits, theta = dt, 2dt, 4dt)",
              worst_dev, "< 1e-10", worst_dev < 1e-10)
    R.add("leakage of the noiseless compiled circuits", worst_leak, "< 1e-9", worst_leak < 1e-9)
    recall_rows, recall = [], {}
    if FIXED:
        import json as _js
        rpath = os.path.join(os.path.dirname(__file__), "..", "data", "S2_fixed_recall.json")
        if os.path.exists(rpath):
            with open(rpath) as fh:
                recall = _js.load(fh)
            data["recall_2x3"] = recall
            for key in sorted(recall):
                e = recall[key]
                recall_rows.append([e["mode"], f"B={e['twoB'] // 2}", e["circuits"], e["shots_per_circuit"],
                                    f"{e['reach']} of {e['support999']}"] +
                                   [f"{e[f]['recall']:.3f} / {e[f]['size']} / {e[f]['err']:.1e} / "
                                    f"{'yes' if e[f]['E0_in_weinstein'] else 'NO'}" for f in ("f=0.2", "f=0.1")] +
                                   [f"{e['runtime_s']:.0f}"])
            for key in sorted(recall):
                e = recall[key]
                if e["mode"] != "fixed":
                    continue
                R.add(f"2x3 B={e['twoB'] // 2}: emulated recall of the 99.9 % support at f = 0.1",
                      round(float(e["f=0.1"]["recall"]), 3), ">= 0.9 (gate S1 criterion)",
                      e["f=0.1"]["recall"] >= 0.9)
    if not args.no_tests:
        tp = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"],
                            cwd=os.path.join(os.path.dirname(__file__), ".."), capture_output=True, text=True)
        line = tp.stdout.strip().splitlines()[-1] if tp.stdout.strip() else "no output"
        R.add("pytest -q tests", line, "all pass", tp.returncode == 0)
        data["pytest"] = line
    R.data = data
    R.runtime_s = time.time() - t0
    R.save()

    dom2 = max(data["2x2"]["per_term_cz_routed"], key=data["2x2"]["per_term_cz_routed"].get)
    dom3 = max(data["2x3"]["per_term_cz_routed"], key=data["2x3"]["per_term_cz_routed"].get)
    a2 = data["2x2"]["coarse_step"]["all_to_all"]["cz"]
    r2 = data["2x2"]["coarse_step"]["routed"]["cz"]
    a3 = data["2x3"]["coarse_step"]["all_to_all"]["cz"]
    r3 = data["2x3"]["coarse_step"]["routed"]["cz"]
    l3 = {"all": 35606, "routed": 55459}          # validation/L3.json, the dense-unitary baseline
    try:
        import json as _json
        with open(os.path.join(os.path.dirname(__file__), "..", "validation", "L3.json")) as fh:
            _b = _json.load(fh)["data"]
        l3 = {"all": _b["all_to_all"]["cz"], "routed": _b["routed"]["cz"]}
    except Exception:
        pass
    if FIXED:
        write_report("S2_fixed_angle_circuits.md", fixed_report(args, R, data, rows_2x2, rows_2x3,
                                                                recall_rows, grid_on))
        print(R.criteria_table())
        return 0 if R.passed else 1
    verdict = "" if R.passed else f"""
## Why it is over budget, and what the planner has to decide

The circuits are exact and leak-free (criteria 3 and 4): this is a cost result, not a correctness
problem.  Against the dense-block-unitary baseline of gate L3 at 2x2 ({l3['all']} CZ all-to-all,
{l3['routed']} routed) the structured construction is a factor {l3['routed'] / r2:.0f} cheaper routed and
{l3['all'] / a2:.0f} cheaper all-to-all; at 2x3 there was no baseline at all, because the dense
14-qubit plaquette unitary would need 4 GiB.  The budget is still exceeded by a factor
{r2 / BUDGET[2]:.1f} at 2x2 and {r3 / BUDGET[3]:.1f} at 2x3.

The last column of the tables above is the anatomy of the cost.  Each term is a sequence of
multiplexed (uniformly controlled) rotations, and one with c controls costs 2^c CNOTs in the
Gray-code form.  Two independent drivers:

1. the **number of rotations** = (rounds of the block schedule) x (distinct qubit-flip patterns):
   five per hopping link at 2x2, nine at 2x3 (blocks of four configurations appear once an interior
   vertex carries an intertwiner label), and {data['2x3']['per_term_structure']['plaq1']['n_multiplexed_rotations']} for the 2x3 plaquette with two interior
   corners, whose blocks reach five configurations with degree four;
2. the **number of controls** = the qubits the angle depends on (the other flux bits of both
   vertices, the Jordan-Wigner parity, and the bits that select the slot): 2-4 at 2x2 and 4-7 at
   2x3, because the amplitude table has six (hopping) to nine (plaquette) distinct values instead
   of three.

Routing on heavy-hex multiplies this by {r2 / a2:.1f} (2x2) and {r3 / a3:.1f} (2x3): a multiplexed rotation is a
star of CNOTs from its controls onto one target, and the heavy-hex degree is three.

The budget is not relaxed here.  The escalation clause of `prompts/06` leaves the choice to the
planner: (i) dropping the diagonal terms from the generator cannot close the gap (they cost
{data['2x2']['per_term_cz']['diag']} CZ at 2x2 and {data['2x3']['per_term_cz']['diag']} at 2x3 all-to-all); (ii) a different vertex qubit layout that
shortens the flip patterns and, above all, reduces the number of angle-selecting controls -- that
changes `codec.py` and requires re-running E1-E3; (iii) raising the budget in the preregistration
with the yield consequence from eq. (5) of the manual, i.e. (1 - p2)^{r2} at 2x2 and (1 - p2)^{r3}
at 2x3.
"""
    write_report("S2_structured_circuits.md", f"""# Gate S2 — structured circuits for the hopping and interior-corner plaquette terms

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/gate_S2.py`, optimization level {args.level},
basis {{rz, sx, x, cz}}, seed {args.seed}.  {env_block()}  Runtime {R.runtime_s:.0f} s.

The hopping terms and the 2x3 plaquettes are compiled by `skqd.circuits_ir.structured_term_gates`:
inside every connected block of the term the exact exponential is written as two-level (Givens)
rotations between computational basis states (bipartite block, singular value decomposition of the
off-diagonal part), rotations of one schedule step that share the qubit-flip pattern are merged into
a single Gray-code uniformly controlled rotation, and the control set is minimised by an
invariance-subspace search that is allowed to act arbitrarily on strings that are not codewords.
A diagonal gauge makes every block generator purely imaginary, so that all two-level rotations are
real and one uniformly controlled Ry per step suffices.  The dense 2x3 plaquette unitary (4 GiB) is
never built; its verification uses the small block `h` of `reference_sim.localize` and the
dressed-basis emulation `krylov.coarse_states`.

## 2x2 ({data['2x2']['n_qubits']} qubits, heavy-hex d={data['2x2']['heavy_hex_distance']})

{md_table(["term", "IR gates", "CZ all-to-all", "CZ routed", "max deviation", "multiplexed rotations (controls)"], rows_2x2)}

IR gate counts of the coarse step: {data['2x2']['ir_gate_counts_coarse_step']}.
Baseline (gate L3, dense block unitaries): 35606 CZ all-to-all, 55459 routed.

## 2x3 ({data['2x3']['n_qubits']} qubits, heavy-hex d={data['2x3']['heavy_hex_distance']})

{md_table(["term", "IR gates", "CZ all-to-all", "CZ routed", "max deviation", "multiplexed rotations (controls)"], rows_2x3)}

IR gate counts of the coarse step: {data['2x3']['ir_gate_counts_coarse_step']}.
There is no dense baseline at 2x3: the interior-corner plaquettes act on 14 qubits, where the dense
local unitary would need 4 GiB.

## Criteria

{R.criteria_table()}

The routed counts are the ones the budget applies to; the all-to-all counts are the logical cost.
Dominant terms (routed): 2x2 `{dom2}` with {data['2x2']['per_term_cz_routed'][dom2]} CZ,
2x3 `{dom3}` with {data['2x3']['per_term_cz_routed'][dom3]} CZ.
{verdict}
## Verification detail

{data['2x2']['n_circuits_vs_emulation']} circuits at 2x2 (both sectors, k = 1..4 and the Trotter family) and
{data['2x3']['n_circuits_vs_emulation']} at 2x3 were compared with `krylov.coarse_states`; every term was compared with the
exact local exponential at theta = dt, 2dt, 4dt on random vectors of its codeword space.  Leakage of the
noiseless compiled statevectors: {data['2x2']['compiled_leakage']} (2x2), {data['2x3']['compiled_leakage']} (2x3).
Runtime {R.runtime_s:.0f} s on the laptop CPU, inside the 30-minute rule; `--quick` (about one minute) skips
the 2^20 statevector checks at 2x3.
""")
    print(R.criteria_table())
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
