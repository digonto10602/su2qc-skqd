"""
CUDA-Q translation of the IR circuits (circuits_ir.py) for GPU statevector
sampling on the laptop (target 'nvidia', GTX 1060 Max-Q) or the desktop (RTX 3070).

NOT executed in the cloud sandbox where this package was assembled.  The laptop
gate scripts/laptop_L5_cudaq_check.py first establishes the qubit-order
convention of cudaq.register_operation for multi-qubit custom unitaries with a
CNOT test (register the CX matrix, compare with x.ctrl) and then compares the
sampled distribution of a 2x2 coarse-step circuit with the numpy reference.

Design.  CUDA-Q kernels are compiled from restricted Python, so the IR gate list
is turned into straight-line kernel SOURCE CODE (one line per gate) that is
exec'd; custom unitaries (the hopping block unitaries) are registered first with
cudaq.register_operation(name, matrix) and called by name inside the kernel, as
in the CUDA-Q documentation example

    cudaq.register_operation("custom_h", np.array([[1, 1], [1, -1]]) / np.sqrt(2))
    @cudaq.kernel
    def bell():
        q = cudaq.qvector(2)
        custom_h(q[0])
        x.ctrl(q[0], q[1])

If the convention test finds that the first qubit argument is the MOST
significant bit of the registered matrix, set BIG_ENDIAN = True: matrices are
then bit-reversed before registration.
"""
from __future__ import annotations

import numpy as np

BIG_ENDIAN = False  # set by scripts/laptop_L5_cudaq_check.py if the CNOT test says so


def _bit_reverse_perm(k: int) -> np.ndarray:
    return np.array([int(f"{s:0{k}b}"[::-1], 2) for s in range(2 ** k)])


def _maybe_permute(U: np.ndarray) -> np.ndarray:
    if not BIG_ENDIAN:
        return U
    k = int(round(np.log2(U.shape[0])))
    p = _bit_reverse_perm(k)
    return U[np.ix_(p, p)]


def kernel_source(gates: list, n: int, name: str = "circ") -> tuple:
    """Return (source code string, {op name: matrix}) for a @cudaq.kernel implementing
    the IR list with a final mz on all qubits."""
    lines = [f"@cudaq.kernel", f"def {name}():", f"    q = cudaq.qvector({n})"]
    ops = {}
    for gname, qs, par in gates:
        if gname == "x":
            lines.append(f"    x(q[{qs[0]}])")
        elif gname == "h":
            lines.append(f"    h(q[{qs[0]}])")
        elif gname == "rz":
            lines.append(f"    rz({float(par)!r}, q[{qs[0]}])")
        elif gname == "p":
            lines.append(f"    r1({float(par)!r}, q[{qs[0]}])")
        elif gname == "cp":
            lines.append(f"    r1.ctrl({float(par)!r}, q[{qs[0]}], q[{qs[1]}])")
        elif gname == "cx":
            lines.append(f"    x.ctrl(q[{qs[0]}], q[{qs[1]}])")
        elif gname == "unitary":
            U = _maybe_permute(np.asarray(par))
            key = f"u{abs(hash(U.tobytes())) % 10 ** 12}"
            ops[key] = U
            lines.append(f"    {key}({', '.join(f'q[{i}]' for i in qs)})")
        else:
            raise ValueError(gname)
    lines.append("    mz(q)")
    return "\n".join(lines) + "\n", ops


def build_kernel(gates: list, n: int):
    """Register the custom operations and exec the generated kernel source; returns the kernel."""
    import cudaq

    src, ops = kernel_source(gates, n)
    for key, U in ops.items():
        cudaq.register_operation(key, U)
    namespace = {"cudaq": cudaq}
    exec("from cudaq import *\n" + src, namespace)  # noqa: S102 - generated from our own IR
    return namespace["circ"]


def sample(gates: list, n: int, shots: int, target: str = "nvidia") -> dict:
    """Sample on a CUDA-Q target ('nvidia' = GPU statevector, 'qpp-cpu' = CPU).
    Returns {bit tuple: count}; CUDA-Q result strings list qubit 0 FIRST, which is
    already this package's order."""
    import cudaq

    cudaq.set_target(target)
    kernel = build_kernel(gates, n)
    res = cudaq.sample(kernel, shots_count=shots)
    return {tuple(int(ch) for ch in k): v for k, v in res.items()}
