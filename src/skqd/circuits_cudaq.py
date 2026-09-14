"""
CUDA-Q translation of the IR circuits (circuits_ir.py) for GPU statevector
sampling on the laptop (target 'nvidia', GTX 1060 Max-Q) or the desktop (RTX 3070).

NOT executed in the cloud sandbox where this package was assembled.  The laptop
gate scripts/laptop_L5_cudaq_check.py first establishes the two conventions that
cannot be known without running CUDA-Q — the order of the result strings and the
qubit order of cudaq.register_operation for multi-qubit matrices — with a CNOT
test, and only then compares a sampled 2x2 circuit with the numpy reference.

Design.  CUDA-Q compiles @cudaq.kernel functions from their Python source
(inspect.getsource), so the IR gate list is turned into straight-line kernel
SOURCE CODE written to a real .py file in a temporary directory and imported;
custom unitaries (the hopping block unitaries) are registered first with
cudaq.register_operation(name, matrix) and called by name inside the kernel, as
in the CUDA-Q documentation example

    cudaq.register_operation("custom_h", np.array([[1, 1], [1, -1]]) / np.sqrt(2))
    @cudaq.kernel
    def bell():
        q = cudaq.qvector(2)
        custom_h(q[0])
        x.ctrl(q[0], q[1])

Endianness.  BIG_ENDIAN = True means the first qubit argument of a registered
operation is the MOST significant bit of its matrix; the matrices of this
package are little-endian (first qubit = least significant bit, see
reference_sim.py), so they are bit-reversed before registration when
BIG_ENDIAN is True.  The convention test in the L5 script sets this flag from
a measurement; the default below is only a guess.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import tempfile

import numpy as np

BIG_ENDIAN = True  # CUDA-Q's documented state-vector convention is qubit 0 = most significant; verified by L5


def _bit_reverse_perm(k: int) -> np.ndarray:
    return np.array([int(f"{s:0{k}b}"[::-1], 2) for s in range(2 ** k)])


def _maybe_permute(U: np.ndarray) -> np.ndarray:
    """Return the matrix in the convention CUDA-Q expects for register_operation."""
    if not BIG_ENDIAN:
        return U
    k = int(round(np.log2(U.shape[0])))
    p = _bit_reverse_perm(k)
    return U[np.ix_(p, p)]


def _opname(U: np.ndarray) -> str:
    return "u" + hashlib.sha1(np.ascontiguousarray(U).tobytes()).hexdigest()[:12]


def kernel_source(gates: list, n: int, name: str = "circ") -> tuple:
    """Return (module source code, {op name: matrix in this package's little-endian convention})
    for a module defining a @cudaq.kernel `name` that implements the IR list and measures all qubits."""
    lines = ["import cudaq", "from cudaq import *", "", "@cudaq.kernel", f"def {name}():", f"    q = cudaq.qvector({n})"]
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
            U = np.asarray(par)
            key = _opname(U)
            ops[key] = U
            lines.append(f"    {key}({', '.join(f'q[{i}]' for i in qs)})")
        else:
            raise ValueError(gname)
    lines.append("    mz(q)")
    return "\n".join(lines) + "\n", ops


_registered = set()


def build_kernel(gates: list, n: int):
    """Register the custom operations (permuted to CUDA-Q's convention), write the generated
    module to a temporary file, import it, and return the kernel."""
    import cudaq

    src, ops = kernel_source(gates, n)
    for key, U in ops.items():
        if key not in _registered:
            cudaq.register_operation(key, _maybe_permute(U))
            _registered.add(key)
    d = tempfile.mkdtemp(prefix="skqd_cudaq_")
    path = os.path.join(d, "skqd_generated_kernel.py")
    with open(path, "w") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("skqd_generated_kernel_" + hashlib.sha1(src.encode()).hexdigest()[:8], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.circ


def sample(gates: list, n: int, shots: int, target: str = "nvidia", qubit0_first: bool = True) -> dict:
    """Sample on a CUDA-Q target ('nvidia' = GPU statevector, 'qpp-cpu' = CPU).  Returns
    {bit tuple: count} in this package's order (qubit k = position k); set qubit0_first=False if
    the L5 convention test found that CUDA-Q lists qubit 0 last."""
    import cudaq

    cudaq.set_target(target)
    kernel = build_kernel(gates, n)
    res = cudaq.sample(kernel, shots_count=shots)
    out = {}
    for k, v in res.items():
        bits = tuple(int(ch) for ch in k)
        if not qubit0_first:
            bits = bits[::-1]
        out[bits] = out.get(bits, 0) + v
    return out
