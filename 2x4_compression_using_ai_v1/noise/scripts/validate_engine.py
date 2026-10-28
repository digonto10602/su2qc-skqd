"""Validate the sparse trajectory engine against Qiskit Aer statevector (complex128) on FIXED fault patterns.

Usage: python validate_engine.py LATTICE FAMILY DEVICE TAG N_TRAJ [SEED]
For N_TRAJ trajectories with at least one fault (faults sampled with numpy default_rng(SEED) from the device model),
the IR circuit with the same Pauli gates inserted at the same positions is run (a) by traj_sparse.Engine and
(b) by AerSimulator(method="statevector", precision="double"); the two final states are compared after removing
the global phase: max |psi_sparse - psi_aer e^{-i phi}| over all 2^n strings (sparse entries outside its support = 0).
Also the noiseless state.  Writes <lattice folder>/noise/data/results/<LATTICE>/<FAMILY>/<DEVICE>/engine_validation.json (appends).
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits  # noqa: E402
import traj_sparse as ts  # noqa: E402
from provenance import provenance, dump  # noqa: E402

from results import lattice_results  # noqa: E402  (one folder per lattice, notes/012)


def aer_state(gates, n, threads=10):
    from qiskit_aer import AerSimulator
    qc = circuits.to_qiskit(gates, n)
    qc.save_statevector()
    sim = AerSimulator(method="statevector", precision="double", fusion_enable=True, max_parallel_threads=threads)
    r = sim.run(qc, shots=1, seed_simulator=1).result()
    return np.asarray(r.data(0)["statevector"].data)


def with_faults(gates, faults):
    ins = sorted([(pos, ts._pauli_ir(lab, qs)) for pos, qs, _, lab in faults], key=lambda x: x[0])
    out, j = [], 0
    for i, g in enumerate(gates):
        while j < len(ins) and ins[j][0] < i:
            out += ins[j][1]; j += 1
        out.append(g)
        while j < len(ins) and i <= ins[j][0] <= i + 0.25 + 1e-9:
            out += ins[j][1]; j += 1
    while j < len(ins):
        out += ins[j][1]; j += 1
    return out


def compare(idx, amp, psi):
    full = np.zeros_like(psi)
    full[idx] = amp
    ov = np.vdot(psi, full)
    ph = np.angle(ov)
    return float(np.abs(full * np.exp(-1j * ph) - psi).max()), float(abs(ov))


def main():
    lat, fam, dev, tag, ntraj = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
    seed = int(sys.argv[6]) if len(sys.argv) > 6 else 7
    gates, n = circuits.ir_gates(lat, fam, tag)
    E = ts.Engine(gates, n, dev)
    rows = []
    t0 = time.time()
    psi = aer_state(gates, n)
    dev0, ov0 = compare(E.clean.idx, E.clean.amp, psi)
    rows.append({"trajectory": "noiseless", "n_faults": 0, "max_abs_diff": dev0, "abs_overlap": ov0,
                 "aer_s": time.time() - t0})
    print(tag, "noiseless", dev0, flush=True)
    rng = np.random.default_rng(seed)
    done = 0
    while done < ntraj:
        f = E.sample_faults(rng)
        if not f:
            continue
        idx, amp, b, k = E.trajectory(f)
        t1 = time.time()
        psi = aer_state(with_faults(gates, f), n)
        d, ov = compare(idx, amp, psi)
        rows.append({"trajectory": done, "n_faults": k, "faults": [[float(p), list(q), kd, lab] for p, q, kd, lab in f],
                     "max_abs_diff": d, "abs_overlap": ov, "prune_bound": b, "aer_s": time.time() - t1})
        print(tag, done, "faults", k, "max|diff|", d, "prune", b, flush=True)
        done += 1
    out = os.path.join(lattice_results(lat), fam, dev, "engine_validation.json")
    old = json.load(open(out)) if os.path.exists(out) else {"test": "engine_validation", "lattice": lat,
                                                             "family": fam, "device": dev, "rows": {}}
    old["rows"][f"{tag}|seed{seed}"] = {"circuit": tag, "seed": seed, "trajectories": rows,
                                        "max_abs_diff_max": max(r["max_abs_diff"] for r in rows)}
    old["summary"] = {"n_checks": sum(len(v["trajectories"]) for v in old["rows"].values()),
                      "max_abs_diff_max": max(v["max_abs_diff_max"] for v in old["rows"].values())}
    old["method"] = __doc__
    old["provenance"] = provenance()
    dump(old, out)


if __name__ == "__main__":
    main()
