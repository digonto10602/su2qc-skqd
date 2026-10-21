"""Review 001: independent full 28-qubit verification of genie's compressed 2x4 circuits.

Engine: qiskit-aer AerSimulator, method=statevector, precision=double (complex128), on CPU.
IR -> qiskit conversion: written here (not genie's, not the package's).
Target: the package's own skqd.krylov.coarse_states(term_groups(Model(4).terms, 4, mass_default(4)),
basis_vector(ref), dt, 5)[k], with dt read from the committed validation/E3.json, embedded with the
package's Codec codewords (skqd.reference_sim.CodewordEmbedding, qubit k = bit k, little-endian).
Nothing of genie's evaluator / simulator / cached targets is used.

Usage: python 001_verify_aer.py CLS TWOB REF K [SEED]
  without SEED: circuit applied to |0..0> (it prepares its own reference), compared with coarse state.
  with SEED (class A only): circuit applied to Prep|phi>, phi a random normalised superposition of the
  sector's codewords (numpy default_rng(SEED), complex Gaussian), compared with the package's exact
  prod_gamma exp(-i k dt H_gamma) phi (krylov.apply_groups).
"""
import json, os, pickle, sys, time, platform, subprocess, resource
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(ROOT, "src"))

from skqd.exact import Model, mass_default
from skqd.krylov import term_groups, basis_vector, coarse_states, apply_groups
from skqd.reference_sim import CodewordEmbedding

TWO_Q = {"cx", "cz", "cp", "rzz"}


def to_qiskit(gates, n):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n)
    for name, qs, par in gates:
        if name == "x": qc.x(qs[0])
        elif name == "h": qc.h(qs[0])
        elif name == "ry": qc.ry(float(par), qs[0])
        elif name == "rz": qc.rz(float(par), qs[0])
        elif name == "rx": qc.rx(float(par), qs[0])
        elif name == "p": qc.p(float(par), qs[0])
        elif name == "cx": qc.cx(qs[0], qs[1])
        elif name == "cz": qc.cz(qs[0], qs[1])
        elif name == "cp": qc.cp(float(par), qs[0], qs[1])
        elif name == "rzz": qc.rzz(float(par), qs[0], qs[1])
        elif name == "gphase": qc.global_phase += float(par)
        elif name == "unitary":
            U = np.asarray(par, dtype=complex)
            if len(qs) != 1 or U.shape != (2, 2):
                raise ValueError(f"multi-qubit unitary on {qs}: not allowed in a costed circuit")
            if np.abs(U.conj().T @ U - np.eye(2)).max() > 1e-12:
                raise ValueError("non-unitary 1q matrix")
            qc.unitary(U, [qs[0]])
        else:
            raise ValueError(f"unknown IR gate {name}")
    return qc


def recount(qc):
    """Counts from the qiskit circuit object: 2q gates, 2q depth (1q gates free), qubits touched."""
    ops = dict(qc.count_ops())
    n2 = sum(1 for ins in qc.data if ins.operation.num_qubits == 2)
    nbig = sum(1 for ins in qc.data if ins.operation.num_qubits > 2)
    lev = {}
    d2 = 0
    for ins in qc.data:
        if ins.operation.num_qubits == 2:
            a, b = (qc.find_bit(q).index for q in ins.qubits)
            l = max(lev.get(a, 0), lev.get(b, 0)) + 1
            lev[a] = lev[b] = l
            d2 = max(d2, l)
    qiskit_d2 = qc.depth(filter_function=lambda ins: ins.operation.num_qubits == 2)
    touched = sorted({qc.find_bit(q).index for ins in qc.data for q in ins.qubits})
    n1 = sum(1 for ins in qc.data if ins.operation.num_qubits == 1)
    return {"n_2q": n2, "n_gt2q": nbig, "depth_2q": d2, "depth_2q_qiskit": qiskit_d2, "n_1q": n1,
            "ops": {k: int(v) for k, v in ops.items()}, "n_qubits_circuit": qc.num_qubits,
            "n_qubits_touched": len(touched), "global_phase": float(qc.global_phase)}


def main():
    cls, twoB, ref, k = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else None
    threads = int(os.environ.get("AER_THREADS", "12"))
    t0 = time.time()
    circs = pickle.load(open(os.path.join(HERE, "001_cache", "circuits.pkl"), "rb"))
    gates = circs[(cls, twoB, ref, k)]
    M = Model(4)
    g2 = 4.0
    m = mass_default(g2)
    E3 = json.load(open(os.path.join(ROOT, "validation", "E3.json")))["data"]["references"]
    dt = float(E3[f"2x4|g2={g2}|2B={twoB}"]["dt"])
    groups_d = M.terms.groups(g2, m)
    names = list(groups_d)
    groups = term_groups(M.terms, g2, m)
    E = CodewordEmbedding(M)
    ints = np.asarray(E.ints, dtype=np.int64)
    n = int(E.n)
    sector = np.asarray(M.basis.sector(twoB))
    dim = M.basis.dim
    ref_int = int(ints[ref])
    theta = k * dt

    # leading X gates must be exactly prepare(ref)
    lead = []
    for g in gates:
        if g[0] == "x":
            lead.append(g[1][0])
        else:
            break
    prep_ok = sorted(lead) == [q for q in range(n) if (ref_int >> q) & 1]

    qc = to_qiskit(gates, n)
    cnt = recount(qc)

    # input state and target
    if seed is None:
        target = coarse_states(groups, basis_vector(dim, ref), dt, k)[k]
        init = None
        inp = {"kind": "own reference (|0...0> + prepare gates)"}
    else:
        rng = np.random.default_rng(seed)
        c = rng.normal(size=len(sector)) + 1j * rng.normal(size=len(sector))
        c /= np.linalg.norm(c)
        phi = np.zeros(dim, dtype=complex)
        phi[sector] = c
        target = apply_groups(groups, phi.copy(), theta)
        init = np.zeros(2 ** n, dtype=complex)
        init[ints ^ ref_int] = phi          # Prep^{-1} = Prep (X gates) maps |cw> -> |cw ^ ref>
        inp = {"kind": "random sector superposition, fed through Prep^-1", "seed": seed,
               "rng": "numpy.random.default_rng(seed); complex Gaussian on sector codewords; normalised",
               "n_components": int(len(sector))}
    t_target = time.time() - t0

    from qiskit_aer import AerSimulator
    import qiskit, qiskit_aer
    qc2 = qc.copy()
    if init is not None:
        from qiskit import QuantumCircuit
        pre = QuantumCircuit(n)
        pre.set_statevector(init)
        qc2 = pre.compose(qc2)
        del init
    qc2.save_statevector()
    sim = AerSimulator(method="statevector", precision="double", fusion_enable=True,
                       max_parallel_threads=threads)
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
    leak_direct = float(np.vdot(psi, psi).real)       # weight on non-codeword strings, summed directly
    del psi
    nonsector = np.setdiff1d(np.arange(dim), sector)
    leak_sector = float(np.sum(np.abs(got[nonsector]) ** 2))   # weight on codewords of other sectors
    ov = np.vdot(target, got)
    ph = float(np.angle(ov))
    dev_raw = float(np.abs(got - target).max())
    dev_pa = float(np.abs(got * np.exp(-1j * ph) - target).max())
    l2_pa = float(np.sqrt(np.sum(np.abs(got * np.exp(-1j * ph) - target) ** 2) + leak_direct))
    out = {"class": cls, "twoB": twoB, "reference": ref, "k": k, "theta": theta, "dt": dt,
           "input": inp, "prepare_prefix_ok": prep_ok,
           "counts_recount_from_qiskit_circuit": cnt,
           "norm_total": norm_total,
           "max_abs_dpsi_phase_aligned": dev_pa, "max_abs_dpsi_raw": dev_raw,
           "l2_dpsi_phase_aligned_incl_leak": l2_pa,
           "global_phase_rad": ph, "abs_overlap": float(abs(ov)),
           "leakage_noncodeword": leak_direct, "leakage_other_sector_codewords": leak_sector,
           "leakage_outside_sector": leak_direct + leak_sector,
           "pass_bar": bool(dev_pa < 1e-10 and leak_direct + leak_sector < 1e-9),
           "timing_s": {"target": t_target, "aer": t_sim, "total": time.time() - t0},
           "peak_rss_GiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20,
           "engine": {"qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__,
                      "method": "statevector", "precision": "double", "fusion": True, "threads": threads,
                      "seed_simulator": 1},
           }
    if cls == "B" and seed is None:
        Hd = groups_d["diag"].tocsr() if hasattr(groups_d["diag"], "tocsr") else groups_d["diag"]
        offd = Hd.copy().tolil(); offd.setdiag(0); offd = offd.tocsr(); offd.eliminate_zeros()
        dref = float(np.real(Hd[ref, ref]))
        pred = float(np.angle(np.exp(1j * theta * dref)))
        out["dropped_diag"] = {"diag_group_offdiag_nnz": int(offd.nnz), "H_diag_ref_ref": dref,
                               "predicted_global_phase_rad": pred,
                               "measured_minus_predicted_rad": float(np.angle(np.exp(1j * (ph - pred))))}
    tag = f"{cls}_B{twoB//2}_ref{ref}_k{k}" + ("" if seed is None else f"_seed{seed}")
    os.makedirs(os.path.join(HERE, "001_runs"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "001_runs", tag + ".json"), "w"), indent=1)
    print(tag, json.dumps({k_: out[k_] for k_ in ("max_abs_dpsi_phase_aligned", "leakage_outside_sector",
                                                 "global_phase_rad", "pass_bar")}),
          cnt["n_2q"], cnt["depth_2q"], f"aer {t_sim:.0f}s", flush=True)


if __name__ == "__main__":
    main()
