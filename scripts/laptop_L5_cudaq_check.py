#!/usr/bin/env python3
"""
Laptop gate L5 — CUDA-Q version of the 2x2 circuits: convention tests, sampled
distribution versus the numpy reference, GPU timing.

Convention tests (run first; they fix two unknowns and are real pass/fail checks):
  (a) result-string order: a kernel with X on qubit 0 of three must return '100'
      (qubit 0 first) or '001' (qubit 0 last); anything else fails.
  (b) register_operation qubit order: the little-endian CNOT matrix (control = first
      qubit argument = least significant bit) is registered through
      circuits_cudaq._maybe_permute under the current BIG_ENDIAN flag and applied to
      |q0 = 1, q1 = 0>; the result must equal x.ctrl(q[0], q[1]).  If it does not,
      the flag is flipped, the test repeated with a fresh operation name, and it must
      then agree — otherwise the gate fails.

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

CX_LE = np.array([[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0]], dtype=complex)  # little-endian CNOT(q0 -> q1)


def string_order_test():
    import cudaq

    @cudaq.kernel
    def x0():
        q = cudaq.qvector(3)
        x(q[0])
        mz(q)

    key = cudaq.sample(x0, shots_count=10).most_probable()
    return key  # '100' -> qubit 0 first, '001' -> qubit 0 last


def endian_test(tag: str):
    """Register CX through _maybe_permute under the current flag; True if it acts as x.ctrl."""
    import cudaq

    name = f"cx_test_{tag}"
    cudaq.register_operation(name, cc._maybe_permute(CX_LE))
    src = f"""
import cudaq
from cudaq import *
@cudaq.kernel
def t_custom():
    q = cudaq.qvector(2)
    x(q[0])
    {name}(q[0], q[1])
    mz(q)
@cudaq.kernel
def t_native():
    q = cudaq.qvector(2)
    x(q[0])
    x.ctrl(q[0], q[1])
    mz(q)
"""
    import importlib.util
    import tempfile
    d = tempfile.mkdtemp(prefix="skqd_cudaq_test_")
    path = os.path.join(d, f"t_{tag}.py")
    open(path, "w").write(src)
    spec = importlib.util.spec_from_file_location(f"skqd_cudaq_t_{tag}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    k1 = cudaq.sample(mod.t_custom, shots_count=10).most_probable()
    k2 = cudaq.sample(mod.t_native, shots_count=10).most_probable()
    return k1 == k2, k1, k2


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
        R.add("cudaq importable", getattr(cudaq, "__version__", "yes"), "installed", True)
    except Exception as e:  # pragma: no cover
        R.add("cudaq importable", str(e), "installed", False)
        R.save()
        print("cudaq not available:", e)
        return 1

    key = string_order_test()
    qubit0_first = key == "100"
    R.add("result-string order test (X on qubit 0 of 3)", key, "'100' (qubit 0 first) or '001' (qubit 0 last)", key in ("100", "001"))

    ok, k1, k2 = endian_test("a")
    if not ok:
        cc.BIG_ENDIAN = not cc.BIG_ENDIAN
        ok, k1, k2 = endian_test("b")
    R.add("register_operation convention determined (custom CNOT = x.ctrl)", f"BIG_ENDIAN={cc.BIG_ENDIAN}, {k1} vs {k2}",
          "custom CNOT acts like x.ctrl under the chosen flag", ok)

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
    counts = cc.sample(g, n, args.shots, target=args.target, qubit0_first=qubit0_first)
    t_s = time.time() - ts
    acc, rej = codec.decode_counts(counts, target_twoB=0)
    n_acc = sum(acc.values())
    R.add("noiseless sampling: accepted shots", f"{n_acc}/{args.shots}", "= all shots", n_acc == args.shots)
    p_emp = np.zeros(M.basis.dim)
    for k, c in acc.items():
        p_emp[k] = c / args.shots
    tvd = 0.5 * np.abs(p_emp - exact).sum()
    bound = 3 * np.sqrt(M.basis.dim / args.shots)
    R.add("total-variation distance to the exact distribution", round(float(tvd), 4), f"< {bound:.3f}", tvd < bound)
    R.data = {"target": args.target, "sampling_time_s": t_s, "shots": args.shots, "BIG_ENDIAN": cc.BIG_ENDIAN,
              "qubit0_first": qubit0_first, "rejections": rej}
    R.runtime_s = time.time() - t0
    R.save()
    write_report("L5_cudaq_check.md", f"""# Laptop gate L5 — CUDA-Q circuits versus the numpy reference (2x2)

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/laptop_L5_cudaq_check.py`, target {args.target}.  {env_block()}
Runtime {R.runtime_s:.0f} s; sampling {args.shots} shots took {t_s:.2f} s.  Conventions found: result strings list
qubit 0 {'first' if qubit0_first else 'last'}; register_operation BIG_ENDIAN = {cc.BIG_ENDIAN} (make this the default in
`src/skqd/circuits_cudaq.py` if it differs).

{R.criteria_table()}
""")
    print(R.criteria_table())
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())
