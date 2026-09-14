#!/usr/bin/env python3
"""
Gate E3 — exact references (Table 1 of the manual), static-charge sectors,
derived quantities (Delta_0, M_B, V(1), V(2)), the Krylov step dt = pi/W per
sector, the B = 1 near-degenerate clusters, and the j_max = 1 truncation check
at 2x2.  Writes data/references.json used by every later gate.

Runtime: ~1-2 minutes (2x4 build 5 s, Lanczos per sector < 1 s).
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.report import ROOT, GateResult, env_block, md_table, write_report  # noqa: E402

# Table 1 of the manual (lattice, g2, 2B) -> (dim, E0, next levels, pi/W, support99, support999, PR)
TABLE1 = {
    ("2x2", 4.0, 0): (38, -3.6408, [-0.9622], 0.245, 9, 16, 1.5),
    ("2x2", 4.0, 2): (20, -1.8616, [-1.8197, 0.2082], 0.332, 8, 13, 2.6),
    ("2x3", 4.0, 0): (677, -5.6026, [-2.8886, -2.8652], 0.156, 31, 86, 1.9),
    ("2x3", 4.0, 2): (426, -3.8261, [-3.8017, -3.6687, -1.6529], 0.187, 42, 95, 3.6),
    ("2x3", 4.0, 4): (95, -2.0118, [-1.8622, -1.8439], 0.234, 15, 22, 1.5),
    ("2x3", 2.0, 0): (677, -4.2216, [-2.7236, -2.7032], 0.257, 137, 326, 5.9),
    ("2x3", 2.0, 2): (426, -3.0866, [-2.9730, -2.7940], 0.305, 136, 243, 11.9),
    ("2x3", 1.0, 0): (677, -4.3918, [-3.4201], 0.303, 396, 549, 33.8),
    ("2x4", 4.0, 0): (12843, -7.5652, [-4.8436, -4.8375], 0.115, 76, 305, 2.5),
    ("2x4", 4.0, 2): (8934, -5.7802, [-5.7741, -5.6541], None, 127, 470, 4.8),
}
DERIVED = {  # manual, "Derived quantities"
    ("2x3", 4.0): dict(D0=2.7140, MB=1.7765, binding=0.038, V1=1.3872, V2=2.5898),
    ("2x3", 2.0): dict(D0=1.4980, MB=1.1350, V1=0.7820, V2=1.3740),
    ("2x4", 4.0): dict(D0=2.7216, MB=1.7851),
    ("2x4", 2.0): dict(MB=1.1560),
}


def main():
    t0 = time.time()
    R = GateResult("E3", "Exact references (Table 1), static sectors, derived quantities, dt per sector")
    models = {}
    build_time = {}
    for Lx in (2, 3, 4):
        t = time.time()
        models[f"2x{Lx}"] = Model(Lx)
        build_time[f"2x{Lx}"] = time.time() - t
    for Lx, st in ((3, (0, 2)), (3, (0, 4))):
        t = time.time()
        models[f"2x{Lx}+static{st}"] = Model(Lx, static_sites=st)
        build_time[f"2x{Lx}+static{st}"] = time.time() - t

    refs = {}
    rows = []
    for (name, g2, twoB), (dim, E0, nxt, piW, s99, s999, pr) in TABLE1.items():
        M = models[name]
        r = M.reference(g2, twoB, k=6)
        key = f"{name}|g2={g2}|2B={twoB}"
        refs[key] = dict(lattice=name, g2=g2, m=mass_default(g2), twoB=twoB, dim=r.dim,
                         energies=r.energies.tolist(), emax=r.emax, W=r.W, dt=r.dt,
                         support99=r.support99, support999=r.support999, PR=r.pr)
        rows.append([name, g2, twoB // 2, r.dim, f"{r.E0:.4f}", ", ".join(f"{e:.4f}" for e in r.energies[1:1 + len(nxt)]),
                     f"{r.dt:.3f}", f"{r.support99} / {r.support999}", f"{r.pr:.1f}",
                     f"{E0:.4f}", ", ".join(f"{e:.4f}" for e in nxt), f"{piW}" if piW else "—", f"{s99} / {s999}", f"{pr}"])
        R.add(f"{key}: dim", r.dim, f"= {dim}", r.dim == dim)
        R.add(f"{key}: E0", round(r.E0, 4), f"manual {E0} (|diff| <= 5e-5)", abs(r.E0 - E0) <= 5e-5)
        for i, e in enumerate(nxt):
            R.add(f"{key}: level {i + 1}", round(float(r.energies[i + 1]), 4), f"manual {e} (|diff| <= 5e-5)",
                  abs(r.energies[i + 1] - e) <= 5e-5)
        if piW is not None:
            R.add(f"{key}: pi/W", round(r.dt, 3), f"manual {piW} (|diff| <= 5e-4)", abs(r.dt - piW) <= 5e-4)
        # support counts: allow +-3 (they depend on ties in tiny weights near the cut)
        R.add(f"{key}: support 99%/99.9%", f"{r.support99}/{r.support999}", f"manual {s99}/{s999} (each within 3)",
              abs(r.support99 - s99) <= 3 and abs(r.support999 - s999) <= 3)
        R.add(f"{key}: participation ratio", round(r.pr, 1), f"manual {pr} (|diff| <= 0.1)", abs(r.pr - pr) <= 0.1 + 1e-9)

    # static sectors and derived quantities
    drows = []
    derived = {}
    for name, g2 in (("2x3", 4.0), ("2x3", 2.0), ("2x4", 4.0), ("2x4", 2.0)):
        M = models[name]
        e0 = M.reference(g2, 0, k=3)
        e1 = M.reference(g2, 2, k=3)
        d = dict(D0=float(e0.energies[1] - e0.energies[0]), MB=float(e1.E0 - e0.E0))
        if name == "2x3":
            e2 = M.reference(g2, 4, k=3)
            d["binding"] = float(e2.E0 - e0.E0 - 2 * d["MB"])
            r1 = models["2x3+static(0, 2)"].reference(g2, 0, k=3)
            r2 = models["2x3+static(0, 4)"].reference(g2, 0, k=3)
            d["V1"] = float(r1.E0 - e0.E0)
            d["V2"] = float(r2.E0 - e0.E0)
            refs[f"2x3+static r=1|g2={g2}|2B=0"] = dict(lattice="2x3+static r=1", g2=g2, m=mass_default(g2), twoB=0, dim=r1.dim,
                                                       energies=r1.energies.tolist(), emax=r1.emax, W=r1.W, dt=r1.dt,
                                                       support99=r1.support99, support999=r1.support999, PR=r1.pr)
            refs[f"2x3+static r=2|g2={g2}|2B=0"] = dict(lattice="2x3+static r=2", g2=g2, m=mass_default(g2), twoB=0, dim=r2.dim,
                                                       energies=r2.energies.tolist(), emax=r2.emax, W=r2.W, dt=r2.dt,
                                                       support99=r2.support99, support999=r2.support999, PR=r2.pr)
        derived[f"{name}|g2={g2}"] = d
        man = DERIVED[(name, g2)]
        for q, v in d.items():
            if q in man:
                tol = 2e-4 if q != "binding" else 2e-3
                R.add(f"{name} g2={g2}: {q}", round(v, 4), f"manual {man[q]} (|diff| <= {tol})", abs(v - man[q]) <= tol)
        drows.append([name, g2] + [f"{d.get(q, float('nan')):.4f}" if q in d else "—" for q in ("D0", "MB", "binding", "V1", "V2")]
                     + [", ".join(f"{q}={man[q]}" for q in man)])

    # static sector sizes quoted in the report (also checked in E2)
    st1, st2 = models["2x3+static(0, 2)"], models["2x3+static(0, 4)"]
    st_counts = dict(r1=st1.basis.dim, r1_B0=int(len(st1.basis.sector(0))), r2=st2.basis.dim, r2_B0=int(len(st2.basis.sector(0))))
    R.add("2x3 static sectors: states (r=1, r=1 B=0, r=2, r=2 B=0)", str(st_counts), "= 2729, 1089, 2418, 978",
          (st_counts["r1"], st_counts["r1_B0"], st_counts["r2"], st_counts["r2_B0"]) == (2729, 1089, 2418, 978))

    # B = 1 clusters (near-degeneracies, Step 1.5)
    crow = []
    for name, exp in (("2x2", [0.042]), ("2x3", [0.024, 0.13]), ("2x4", [0.006, 0.12])):
        r = models[name].reference(4.0, 2, k=5)
        gaps = np.diff(r.energies[:len(exp) + 1])
        crow.append([name, ", ".join(f"{g:.3f}" for g in gaps), ", ".join(str(e) for e in exp)])
        ok = all(abs(g - e) <= 0.006 for g, e in zip(gaps, exp))
        R.add(f"{name} B=1 cluster splittings (g2=4)", ", ".join(f"{g:.3f}" for g in gaps), f"manual {exp} (within 0.006)", ok)

    # j_max = 1 truncation check at 2x2 (error budget)
    M1 = Model(2, jmax=1.0)
    R.add("2x2 with j_max = 1: states", M1.basis.dim, "= 152", M1.basis.dim == 152)
    trunc = {}
    for g2 in (4.0, 2.0, 1.0):
        a = models["2x2"].reference(g2, 0, k=2)
        b = M1.reference(g2, 0, k=2)
        trunc[g2] = dict(E0_half=a.E0, E0_one=b.E0, shift=b.E0 - a.E0, dim_half=a.dim, dim_one=b.dim)
    R.data = dict(references=refs, derived=derived, build_time_s=build_time, truncation_2x2=trunc)
    R.runtime_s = time.time() - t0
    path = R.save()
    with open(os.path.join(ROOT, "data", "references.json"), "w") as fh:
        json.dump(dict(references=refs, derived=derived, truncation_2x2=trunc), fh, indent=1)

    trows = [[g2, v["dim_half"], f"{v['E0_half']:.4f}", v["dim_one"], f"{v['E0_one']:.4f}", f"{v['shift']:.4f}"] for g2, v in trunc.items()]
    report = f"""# Gate E3 — exact references, static sectors, derived quantities, Krylov step

**Status: {'PASS' if R.passed else 'FAIL'}** — produced by `scripts/gate_E3.py`; all numbers computed in this run, stored in
`validation/E3.json` and `data/references.json`.  {env_block()}  Runtime {R.runtime_s:.0f} s.

Parameters: $m = 3g^2/16$ (the manual's line), $j_{{\\max}} = \\tfrac12$.  Dense diagonalization for sectors up to
4 000 states, Lanczos (`scipy.sparse.linalg.eigsh`) above.  $W = E_{{\\max}} - E_{{\\min}}$ is the spectral width of the
sector block and $\\Delta t = \\pi/W$ the anti-aliasing Krylov step; the support $S_\\epsilon$ is the smallest set of
configurations carrying $1-\\epsilon$ of the ground-state weight; $\\mathrm{{PR}} = 1/\\sum_b |\\langle b|\\Omega\\rangle|^4$
is the participation ratio.  Builder times: {', '.join(f'{k} {v:.1f} s' for k, v in build_time.items())}
(the manual quotes 22 s for 2x3 and 17 min for 2x4 in plain numpy; this builder caches matrix elements by local
signature).

## Table 1 reproduced

{md_table(["lattice", "g²", "B", "dim", "E0", "next levels", "π/W", "support 99% / 99.9%", "PR",
           "manual E0", "manual next", "manual π/W", "manual support", "manual PR"], rows)}

## Derived quantities

{md_table(["lattice", "g²", "Δ0", "M_B", "E(B=2)−E(B=0)−2M_B", "V(1)", "V(2)", "manual"], drows)}

$\\Delta_0 = E_1^{{B=0}} - E_0^{{B=0}}$ (meson-like gap), $M_B = E_0^{{B=1}} - E_0^{{B=0}}$ (baryon mass),
$V(r) = E_0^{{\\text{{static pair at distance }} r, B=0}} - E_0^{{B=0}}$ (static potential, charges on the bottom row).
The static sectors have {st_counts['r1']} ($r=1$, $B=0$: {st_counts['r1_B0']}) and {st_counts['r2']} ($r=2$, $B=0$: {st_counts['r2_B0']}) states (computed here).

## $B = 1$ near-degenerate clusters (Step 1.5)

{md_table(["lattice", "lowest splittings at g²=4", "manual"], crow)}

The diquark can sit on any even site, so the lowest $B=1$ levels form a cluster of $L_x$ states; the baryon mass is
defined from the lowest level with the cluster reported, and certification treats the cluster as a whole.

## Truncation check at 2x2 ($j_{{\\max}} = \\tfrac12 \\to 1$, error budget of Step 10)

{md_table(["g²", "states (j_max=1/2)", "E0 (j_max=1/2)", "states (j_max=1)", "E0 (j_max=1)", "shift"], trows)}

With $j_{{\\max}} = 1$ the one-plaquette model has 152 states (manual: 82 → 152).  The ground-state shift is the
truncation entry of the error budget at 2x2; it is computed exactly here and is not a gate criterion.

## All checks

{R.criteria_table()}

## Reproduce

```
python scripts/gate_E3.py     # ~1-2 min
```
"""
    write_report("E3_exact_references.md", report)
    print(R.criteria_table())
    print("STATUS", "PASS" if R.passed else "FAIL", "->", path)
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
