"""Checks behind report 002 (f): native compilation is exact, routing cost on heavy-hex, native-form sparse blow-up.

Writes noise/data/checks/native_compile_check.json.
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits  # noqa: E402
import noise_models as nm  # noqa: E402
from provenance import provenance, dump  # noqa: E402


def probs(qc, mm=None, n=None):
    from qiskit_aer import AerSimulator
    c = qc.copy()
    c.save_probabilities()
    p = np.asarray(AerSimulator(method="statevector", precision="double", max_parallel_threads=4)
                   .run(c).result().data(0)["probabilities"])
    if mm is None:
        return p
    idx = np.arange(len(p))
    lg = np.zeros(len(p), dtype=np.int64)
    for l, cc in enumerate(mm):
        lg |= ((idx >> cc) & 1) << l
    return np.bincount(lg, weights=p, minlength=2 ** n)


def main():
    out = {}
    tag = "B0_ref117_k1"
    qc = circuits.circuit("2x3", "frozen", tag)
    p0 = probs(qc)
    for kind in ("quantinuum", "ibm"):
        nat, lay = nm.native_circuit(qc, kind, cache_key=f"2x3__frozen__{tag}")
        p = probs(nat, lay["measure_map"], qc.num_qubits)
        out[f"2x3|frozen|{tag}|{kind}"] = {"max_abs_dprob_native_vs_logical": float(np.abs(p - p0).max()),
                                           "native_ops": {k: int(v) for k, v in nat.count_ops().items()},
                                           "n_qubits_simulated": nat.num_qubits, "layout": lay["transpile"]}
    for fam in ("compressed_circuit_llm_2x4_classA", "compressed_circuit_llm_2x4_classB"):
        t = "B0_ref102_k1"
        q = circuits.circuit("2x4", fam, t)
        t0 = time.time()
        nat, lay = nm.native_circuit(q, "ibm", cache_key=f"2x4__{fam}__{t}")
        out[f"2x4|{fam}|{t}|ibm"] = {"native_ops": {k: int(v) for k, v in nat.count_ops().items()},
                                     "n_qubits_used": nat.num_qubits, "route_s": time.time() - t0}
    # native-form sparse simulation of the frozen 2x3 circuit (why the trajectory engine works at IR level)
    from qiskit import transpile
    from skqd.sparse_sim import SparseState, apply_ir
    t = transpile(qc, basis_gates=["rz", "rx", "ry", "rzz"], optimization_level=0)
    ir = [(ins.operation.name, [t.find_bit(x).index for x in ins.qubits],
           float(ins.operation.params[0]) if ins.operation.params else None) for ins in t.data]
    st = SparseState(qc.num_qubits)
    mx = 0
    t0 = time.time()
    for i in range(0, len(ir), 32):
        apply_ir(st, ir[i:i + 32])
        st.to_sparse()
        s = np.abs(st.amp) < 1e-12
        st.idx, st.amp = st.idx[~s], st.amp[~s]
        mx = max(mx, st.idx.size)
    out[f"2x3|frozen|{tag}|native_form_sparse"] = {"max_support": int(mx), "final_support": int(st.idx.size),
                                                   "wall_s": time.time() - t0}
    gates, n = circuits.ir_gates("2x3", "frozen", tag)
    st = SparseState(n)
    mx = 0
    t0 = time.time()
    for i in range(0, len(gates), 32):
        apply_ir(st, gates[i:i + 32])
        st.to_sparse()
        s = np.abs(st.amp) < 1e-12
        st.idx, st.amp = st.idx[~s], st.amp[~s]
        mx = max(mx, st.idx.size)
    out[f"2x3|frozen|{tag}|ir_form_sparse"] = {"max_support": int(mx), "wall_s": time.time() - t0}
    dump({"checks": out, "provenance": provenance()},
         os.path.join(circuits.NOISE, "data", "checks", "native_compile_check.json"))
    print(out)


if __name__ == "__main__":
    main()
