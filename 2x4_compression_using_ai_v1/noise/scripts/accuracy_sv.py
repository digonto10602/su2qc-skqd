"""C5 test 1: noiseless accuracy of one circuit, Qiskit Aer statevector, complex128.

Usage: python accuracy_sv.py LATTICE FAMILY TAG      (LATTICE 2x4 | 2x3; TAG like B0_ref102_k1)
Writes noise/data/results/<LATTICE>/<FAMILY>/noiseless/accuracy_runs/<TAG>.json (skips if present).

Target: the package's krylov.coarse_states(...)[k] (src/targets.py), dt from validation/E3.json, embedded on
CodewordEmbedding codewords (qubit k = bit k). Deviation after removing the global phase phi = arg<t|g>:
max_s |g_s e^{-i phi} - t_s|; leakage L_nc (weight on non-codeword strings, summed directly) and L_sec
(weight on codewords of the other baryon sector). Bar (package): max|dpsi| < 1e-10 and L_nc + L_sec < 1e-9.
"""
import os
import resource
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits  # noqa: E402
import targets  # noqa: E402
from provenance import provenance, dump  # noqa: E402

RES = os.path.join(circuits.NOISE, "data", "results")


def counts(qc):
    n2 = sum(1 for ins in qc.data if ins.operation.num_qubits == 2)
    n1 = sum(1 for ins in qc.data if ins.operation.num_qubits == 1)
    ngt = sum(1 for ins in qc.data if ins.operation.num_qubits > 2)
    d2 = qc.depth(filter_function=lambda ins: ins.operation.num_qubits == 2)
    touched = {qc.find_bit(q).index for ins in qc.data for q in ins.qubits}
    return {"n_2q": n2, "n_1q": n1, "n_gt2q": ngt, "depth_2q": d2, "depth": qc.depth(),
            "n_qubits_circuit": qc.num_qubits, "n_qubits_touched": len(touched),
            "ops": {k: int(v) for k, v in qc.count_ops().items()}}


def main():
    lattice, family, tag = sys.argv[1], sys.argv[2], sys.argv[3]
    out = os.path.join(RES, lattice, family, "noiseless", "accuracy_runs", tag + ".json")
    if os.path.exists(out):
        print("exists", out)
        return
    Lx = int(lattice.split("x")[1])
    threads = int(os.environ.get("AER_THREADS", "10"))
    t0 = time.time()
    twoB, ref, k = circuits.parse_tag(tag)
    qc = circuits.circuit(lattice, family, tag)
    cnt = counts(qc)
    d = targets.model(Lx)
    ints, n, dim = d["ints"], d["n"], d["dim"]
    assert qc.num_qubits == n, (qc.num_qubits, n)
    tgt = targets.target(Lx, twoB, ref, k)
    sector = targets.sector(Lx, twoB)
    t_target = time.time() - t0

    from qiskit_aer import AerSimulator
    qc2 = qc.copy()
    qc2.save_statevector()
    sim = AerSimulator(method="statevector", precision="double", fusion_enable=True, max_parallel_threads=threads)
    t1 = time.time()
    res = sim.run(qc2, shots=1, seed_simulator=1).result()
    t_sim = time.time() - t1
    if not res.success:
        raise RuntimeError(res.status)
    psi = np.asarray(res.data(0)["statevector"].data)
    del res
    assert psi.dtype == np.complex128 and psi.size == 2 ** n
    norm_total = float(np.vdot(psi, psi).real)
    got = psi[ints].copy()
    psi[ints] = 0
    leak_nc = float(np.vdot(psi, psi).real)
    del psi
    nonsector = np.setdiff1d(np.arange(dim), sector)
    leak_sec = float(np.sum(np.abs(got[nonsector]) ** 2))
    ov = np.vdot(tgt, got)
    ph = float(np.angle(ov))
    diff = got * np.exp(-1j * ph) - tgt
    rec = {"lattice": lattice, "family": family, "circuit": tag, "twoB": twoB, "reference": ref, "k": k,
           "dt": targets.dt_of(Lx, twoB), "theta": k * targets.dt_of(Lx, twoB),
           "counts": cnt, "norm_total": norm_total,
           "max_abs_dpsi_phase_aligned": float(np.abs(diff).max()),
           "l2_dpsi_phase_aligned_incl_leak": float(np.sqrt(np.sum(np.abs(diff) ** 2) + leak_nc)),
           "global_phase_rad": ph, "abs_overlap": float(abs(ov)),
           "leakage_noncodeword": leak_nc, "leakage_other_sector_codewords": leak_sec,
           "leakage_outside_sector": leak_nc + leak_sec,
           "pass_bar": bool(np.abs(diff).max() < 1e-10 and leak_nc + leak_sec < 1e-9),
           "bar": "max|dpsi| < 1e-10 and L_nc + L_sec < 1e-9 (package bar)",
           "timing_s": {"target": t_target, "aer": t_sim, "total": time.time() - t0},
           "peak_rss_GiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 20,
           "engine": {"simulator": "qiskit_aer.AerSimulator", "method": "statevector", "precision": "double",
                      "dtype": "complex128", "fusion": True, "threads": threads, "seed_simulator": 1},
           "provenance": provenance()}
    dump(rec, out)
    print(tag, family, f"dpsi {rec['max_abs_dpsi_phase_aligned']:.2e} leak {rec['leakage_outside_sector']:.1e}",
          f"zz {cnt['n_2q']} aer {t_sim:.0f}s", "PASS" if rec["pass_bar"] else "FAIL", flush=True)


if __name__ == "__main__":
    main()
