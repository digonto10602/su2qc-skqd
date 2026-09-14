#!/usr/bin/env python3
"""
Laptop gate L2 — Qiskit circuits reproduce the numpy reference (2x2, 12 qubits).

Checks
  1. Statevector of every coarse-step circuit (all references of B = 0 and B = 1,
     k = 1..4) and of a 3-step Trotter circuit equals the numpy IR simulation and
     the dressed-basis emulation (max |diff| < 1e-9).
  2. Noiseless Aer sampling of one circuit: every shot decodes (acceptance 100 %),
     and the sampled distribution has total-variation distance to the exact
     distribution consistent with the shot noise.
  3. Timing of statevector construction and of 1e4-shot sampling (CPU, and GPU if
     qiskit-aer-gpu is installed).

Pass criteria are written to validation/L2.json and reports/L2_qiskit_check.md.
Expected runtime: < 5 min on the i7-8750H.
Usage: python scripts/laptop_L2_qiskit_check.py [--shots 10000] [--gpu]
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory, gate_counts, run_ir  # noqa: E402
from skqd.codec import Codec, Reject  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import basis_vector, coarse_states, references, term_groups, trotter_states  # noqa: E402
from skqd.reference_sim import CodewordEmbedding  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=10000)
    ap.add_argument("--gpu", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    R = GateResult("L2", "Qiskit circuits reproduce the numpy reference at 2x2")
    try:
        import qiskit  # noqa: F401
        from skqd import circuits_qiskit as cq
        R.add("qiskit importable", qiskit.__version__, "installed", True)
    except Exception as e:  # pragma: no cover
        R.add("qiskit importable", str(e), "installed", False)
        R.save()
        print("qiskit not available:", e)
        return 1

    g2 = 4.0
    m = mass_default(g2)
    M = Model(2)
    E = CodewordEmbedding(M)
    n = E.n
    F = CircuitFactory(M, g2)
    groups = term_groups(M.terms, g2, m)
    worst = 0.0
    n_circ = 0
    tsv = time.time()
    for twoB in (0, 2):
        ref = M.reference(g2, twoB)
        for r in references(M.basis, twoB):
            for k in (1, 2, 3, 4):
                g = F.coarse_step(r, k, ref.dt)
                sv = cq.statevector(g, n)
                ex = E.embed(coarse_states(groups, basis_vector(M.basis.dim, r), ref.dt, k)[k])
                ir = run_ir(g, n)
                worst = max(worst, abs(sv - ex).max(), abs(sv - ir).max())
                n_circ += 1
            g = F.trotter(r, 3, ref.dt)
            sv = cq.statevector(g, n)
            ex = E.embed(trotter_states(groups, basis_vector(M.basis.dim, r), ref.dt, 4)[3])
            worst = max(worst, abs(sv - ex).max())
            n_circ += 1
    t_sv = time.time() - tsv
    R.add(f"max |Qiskit statevector - reference| over {n_circ} circuits", worst, "< 1e-9", worst < 1e-9)

    # sampling
    ref = M.reference(g2, 0)
    r0 = references(M.basis, 0)[0]
    g = F.coarse_step(r0, 2, ref.dt)
    codec = Codec(M.basis)
    exact = np.abs(coarse_states(groups, basis_vector(M.basis.dim, r0), ref.dt, 2)[2]) ** 2
    ts = time.time()
    counts = cq.sample(g, n, args.shots)
    t_cpu = time.time() - ts
    acc, rej = codec.decode_counts(counts, target_twoB=0)
    n_acc = sum(acc.values())
    R.add("noiseless sampling: accepted shots", f"{n_acc}/{args.shots}", "= all shots", n_acc == args.shots)
    p_emp = np.zeros(M.basis.dim)
    for k, c in acc.items():
        p_emp[k] = c / args.shots
    tvd = 0.5 * np.abs(p_emp - exact).sum()
    bound = 3 * np.sqrt(M.basis.dim / args.shots)  # loose shot-noise bound
    R.add("total-variation distance to the exact distribution", round(float(tvd), 4), f"< {bound:.3f} (shot noise)", tvd < bound)
    timing = [["statevector, all circuits", f"{t_sv:.1f} s"], [f"Aer CPU sampling, {args.shots} shots", f"{t_cpu:.2f} s"]]
    if args.gpu:
        try:
            ts = time.time()
            cq.sample(g, n, args.shots, device="GPU")
            timing.append([f"Aer GPU sampling, {args.shots} shots", f"{time.time() - ts:.2f} s"])
        except Exception as e:  # pragma: no cover
            timing.append(["Aer GPU sampling", f"failed: {e}"])
    R.data = {"gate_counts_coarse_k2": gate_counts(g), "timing": timing}
    R.runtime_s = time.time() - t0
    R.save()
    write_report("L2_qiskit_check.md", f"""# Laptop gate L2 — Qiskit circuits versus the numpy reference (2x2)

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/laptop_L2_qiskit_check.py`.  {env_block()}  Runtime {R.runtime_s:.0f} s.

{R.criteria_table()}

Gate counts of the k = 2 coarse-step circuit (IR): {gate_counts(g)}

{md_table(["timing", "value"], timing)}
""")
    print(R.criteria_table())
    print("STATUS", "PASS" if R.passed else "FAIL")
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
