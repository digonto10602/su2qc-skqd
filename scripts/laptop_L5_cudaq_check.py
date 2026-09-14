#!/usr/bin/env python3
"""
Laptop gate L5 — CUDA-Q version of the 2x2 circuits: convention tests, sampled
distribution versus the numpy reference, GPU timing.

Convention tests (must run before anything else, they fix two unknowns):
  (a) result-string order: a kernel with X on qubit 0 only must return '1000...'
      (qubit 0 first); otherwise the string is reversed in circuits_cudaq.sample.
  (b) register_operation qubit order: register the 4x4 CNOT matrix in the
      little-endian convention (control = first qubit argument = least significant
      bit), apply it to |q0=1, q1=0> and compare with x.ctrl(q[0], q[1]); if the
      result differs, circuits_cudaq.BIG_ENDIAN is set to True and the test repeated.

Usage: python scripts/laptop_L5_cudaq_check.py [--target nvidia|qpp-cpu] [--shots 10000]
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd import circuits_cudaq as cc  # noqa: E402
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model, mass_default  # noqa: E402
from skqd.krylov import basis_vector, coarse_states, references, term_groups  # noqa: E402
from skqd.report import GateResult, env_block, write_report  # noqa: E402


def convention_tests():
    import cudaq

    @cudaq.kernel
    def x0():
        q = cudaq.qvector(3)
        x(q[0])
        mz(q)

    res = cudaq.sample(x0, shots_count=10)
    key = list(res.keys())[0]
    qubit0_first = key == "100"
    CX = np.array([[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0]], dtype=complex)  # little-endian CNOT(q0 -> q1)
    cudaq.register_operation("cx_le", CX)

    @cudaq.kernel
    def t1():
        q = cudaq.qvector(2)
        x(q[0])
        cx_le(q[0], q[1])
        mz(q)

    @cudaq.kernel
    def t2():
        q = cudaq.qvector(2)
        x(q[0])
        x.ctrl(q[0], q[1])
        mz(q)

    k1 = list(cudaq.sample(t1, shots_count=10).keys())[0]
    k2 = list(cudaq.sample(t2, shots_count=10).keys())[0]
    return qubit0_first, k1 == k2, k1, k2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="nvidia")
    ap.add_argument("--shots", type=int, default=10000)
    args = ap.parse_args()
    t0 = time.time()
    R = GateResult("L5", "CUDA-Q circuits versus the numpy reference at 2x2")
    try:
        import cudaq
        cudaq.set_target(args.target)
        R.add("cudaq importable", cudaq.__version__ if hasattr(cudaq, "__version__") else "yes", "installed", True)
    except Exception as e:  # pragma: no cover
        R.add("cudaq importable", str(e), "installed", False)
        R.save()
        print("cudaq not available:", e)
        return 1
    q0_first, le_ok, k1, k2 = convention_tests()
    R.add("result strings list qubit 0 first", q0_first, "expected True (else reverse in circuits_cudaq.sample)", True)
    if not le_ok:
        cc.BIG_ENDIAN = True
        q0_first, le_ok2, k1, k2 = convention_tests()
        R.add("register_operation convention", f"big-endian ({k1} vs {k2})", "determined", True)
    else:
        R.add("register_operation convention", "little-endian (first qubit = least significant)", "determined", True)

    g2 = 4.0
    m = mass_default(g2)
    M = Model(2)
    F = CircuitFactory(M, g2)
    codec = Codec(M.basis)
    n = codec.n_qubits
    ref = M.reference(g2, 0)
    r0 = references(M.basis, 0)[0]
    g = F.coarse_step(r0, 2, ref.dt)
    exact = np.abs(coarse_states(term_groups(M.terms, g2, m), basis_vector(M.basis.dim, r0), ref.dt, 2)[2]) ** 2
    ts = time.time()
    counts = cc.sample(g, n, args.shots, target=args.target)
    t_s = time.time() - ts
    if not q0_first:
        counts = {k[::-1]: v for k, v in counts.items()}
    acc, rej = codec.decode_counts(counts, target_twoB=0)
    n_acc = sum(acc.values())
    R.add("noiseless sampling: accepted shots", f"{n_acc}/{args.shots}", "= all shots", n_acc == args.shots)
    p_emp = np.zeros(M.basis.dim)
    for k, c in acc.items():
        p_emp[k] = c / args.shots
    tvd = 0.5 * np.abs(p_emp - exact).sum()
    bound = 3 * np.sqrt(M.basis.dim / args.shots)
    R.add("total-variation distance to the exact distribution", round(float(tvd), 4), f"< {bound:.3f}", tvd < bound)
    R.data = {"target": args.target, "sampling_time_s": t_s, "shots": args.shots}
    R.runtime_s = time.time() - t0
    R.save()
    write_report("L5_cudaq_check.md", f"""# Laptop gate L5 — CUDA-Q circuits versus the numpy reference (2x2)

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/laptop_L5_cudaq_check.py`, target {args.target}.  {env_block()}
Runtime {R.runtime_s:.0f} s; sampling {args.shots} shots took {t_s:.2f} s.

{R.criteria_table()}
""")
    print(R.criteria_table())
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
