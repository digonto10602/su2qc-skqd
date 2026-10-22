"""Engine choice record: Aer matrix_product_state (noiseless, complex128) vs the sparse IR engine on the same circuits.
Samples 4000 shots from the MPS state and compares the empirical distribution with the exact one (TV and the
finite-shot floor), and times both engines.  Writes noise/data/checks/mps_probe.json."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits, targets, traj_sparse as ts
from provenance import provenance, dump
from qiskit_aer import AerSimulator
out = {}
for fam, tag in (("compressed_circuit_llm_2x4_classB", "B1_ref230_k1"), ("compressed_circuit_llm_2x4_classA", "B1_ref230_k1")):
    twoB, ref, k = circuits.parse_tag(tag)
    qc = circuits.circuit("2x4", fam, tag)
    qc.measure_all()
    sim = AerSimulator(method="matrix_product_state", precision="double", max_parallel_threads=2)
    t0 = time.time()
    r = sim.run(qc, shots=4000, seed_simulator=11).result()
    t_mps = time.time() - t0
    cnt = r.get_counts()
    d = targets.model(4); ints = d["ints"]
    tg = targets.target(4, twoB, ref, k)
    p = np.abs(tg) ** 2
    pos = {int(x): i for i, x in enumerate(ints)}
    q = np.zeros(len(ints)); out_of = 0
    for key, c in cnt.items():
        x = int(key.replace(" ", ""), 2)
        if x in pos: q[pos[x]] += c
        else: out_of += c
    q /= 4000
    rng = np.random.default_rng(12)
    floor = float(np.mean([0.5 * np.abs(rng.multinomial(4000, p / p.sum()) / 4000 - p).sum() for _ in range(20)]))
    gates, n = circuits.ir_gates("2x4", fam, tag)
    t1 = time.time(); E = ts.Engine(gates, n, "quantinuum_h2_2"); t_sp = time.time() - t1
    out[f"{fam}|{tag}"] = {"mps_seconds_4000_shots": t_mps, "tv_mps_samples_vs_exact": 0.5 * float(np.abs(q - p).sum()) + 0.5 * out_of / 4000,
                           "tv_floor_4000_exact_samples": floor, "shots_outside_codewords": out_of,
                           "sparse_engine_clean_run_seconds": t_sp, "sparse_clean_support": int(E.clean.idx.size),
                           "mps_metadata_max_bond_dim": r.results[0].metadata.get("matrix_product_state_max_bond_dimension")}
    print(fam, out[f"{fam}|{tag}"], flush=True)
dump({"checks": out, "provenance": provenance()}, os.path.join(circuits.NOISE, "data", "checks", "mps_probe.json"))
