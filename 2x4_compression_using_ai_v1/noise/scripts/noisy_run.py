"""C5 test 2: behaviour of one circuit under one device noise model (Pauli trajectories).

Usage: python noisy_run.py LATTICE FAMILY DEVICE TAG [--shots N] [--seed S] [--engine sparse|aer] [--outdir D]
Writes <lattice folder>/noise/data/results/<LATTICE>/<FAMILY>/<DEVICE>/<outdir default noisy_runs>/<TAG>.json (skips if present).

Engine 'sparse' (default): src/traj_sparse.py -- the package's exact sparse simulator (skqd.sparse_sim) on the IR
gate list, faults sampled from the device model and inserted as Pauli gates, |a| < 1e-12 pruned every 32 gates
(the pruned norm is recorded).  Engine 'aer': the same IR circuit with the same channels inserted as Aer
QuantumError instructions, Aer statevector sampling (independent cross-check; slow).
One shot = one trajectory: the final pre-readout state gives p_tau on the sector codewords; one string is sampled
from |amp|^2 and passed through the readout flips.

Quantities (CF_traj sense, reports/CF_traj.md; the labels are the planner's, not manual terms):
  acceptance     fraction of post-readout shots the package codec decodes into the circuit's sector
                 (skqd.codec.Codec.decode_counts(counts, target_twoB))
  f_model        clean-shot fraction of the model = P(no gate / idle / memory fault) * (1 - mean readout error)^n
  f0_prime       P(no gate / idle / memory fault) * readout survival of the reference string (CF_traj f0')
  f_hit          (reference-string hits / shots) / p_ref, p_ref = ideal probability of the reference string
  TV_pre(tau)    1/2 sum_s |p_tau(s)/w_tau - p_c(s)| over the sector codewords, w_tau = sector weight of tau
  b_all(delta)   fraction of ALL trajectories with TV_pre < delta (fault-free ones have TV_pre ~ 1e-12)
  f_ideal(delta) = readout survival of the reference string * b_all(delta)  (= CF_traj f0' + (1 - f0') b(delta))
  r_nc           = f_hit / f_ideal(1e-3)
  TV_acc         TV of the empirical accepted distribution from p_c; TV_acc_floor = same statistic for the same
                 number of ideal samples (finite-shot floor; mean of 20 seeded draws)
  TV_pop_pre     TV of the trajectory-averaged, sector-normalised pre-readout distribution from p_c
"""
import os as _os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")   # one BLAS thread per job: the queue runs several jobs in parallel

import argparse
import os
import sys
import time
import zlib

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits  # noqa: E402
import targets  # noqa: E402
import noise_models as nm  # noqa: E402
import traj_sparse as ts  # noqa: E402
from provenance import provenance, dump  # noqa: E402

from results import lattice_results  # noqa: E402  (one folder per lattice, notes/012)
DELTAS = (1e-3, 1e-2, 0.03)


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]


def tv(p, q):
    return 0.5 * float(np.abs(p - q).sum())


def run_sparse(E, shots, seed, sec_ints, n):
    rng = np.random.default_rng(seed)
    P = np.zeros((shots, len(sec_ints)))
    raw = np.zeros(shots, dtype=np.int64)
    nf = np.zeros(shots, dtype=np.int64)
    prune = np.zeros(shots)
    supp = np.zeros(shots, dtype=np.int64)
    order = np.argsort(sec_ints)
    sorted_sec = sec_ints[order]
    for s in range(shots):
        faults = E.sample_faults(rng)
        idx, amp, b, k = E.trajectory(faults)
        pr = np.abs(amp) ** 2
        tot = pr.sum()
        raw[s] = idx[rng.choice(len(idx), p=pr / tot)]
        pos = np.searchsorted(idx, sorted_sec)
        pos[pos >= len(idx)] = len(idx) - 1
        hit = idx[pos] == sorted_sec
        row = np.zeros(len(sec_ints))
        row[order[hit]] = pr[pos[hit]]
        P[s] = row
        nf[s], prune[s], supp[s] = k, b, len(idx)
    return P, raw, {"n_faults_mean": float(nf.mean()), "n_faults_hist": np.bincount(nf).tolist(),
                    "fault_free_fraction_sampled": float(np.mean(nf == 0)), "prune_bound_max": float(prune.max()),
                    "support_max": int(supp.max()), "support_mean": float(supp.mean())}


def run_aer(gates, n, device, shots, seed, sec_ints, threads):
    """Same channels as the sparse engine, as Aer QuantumError instructions at the same IR positions."""
    from qiskit import QuantumCircuit, ClassicalRegister
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import pauli_error
    ev, _ = ts.ir_events(gates, n, device)
    by = {}
    for e in ev:
        by.setdefault(e[0], []).append(e)
    qc = QuantumCircuit(n)

    def emit(e):
        _, qs, _, plist = e
        tot = sum(p for _, p in plist)
        qc.append(pauli_error(list(plist) + [("I" * len(qs), 1 - tot)]), list(qs))
    for i, g in enumerate(gates):
        for e in by.get(i - 0.5, []):
            emit(e)
        one = circuits.to_qiskit([g], n)                 # IR index i -> exactly this gate (gphase: global phase)
        qc.global_phase += one.global_phase
        for ins in one.data:
            qc.append(ins.operation, [one.find_bit(x).index for x in ins.qubits])
        for e in by.get(i, []) + by.get(i + 0.25, []):
            emit(e)
    for e in by.get(len(gates) + 0.5, []):
        emit(e)
    qc.save_amplitudes_squared([int(x) for x in sec_ints], label="psec", pershot=True)
    cr = ClassicalRegister(n, "c")
    qc.add_register(cr)
    qc.measure(range(n), cr)
    sim = AerSimulator(method="statevector", precision="double", max_parallel_threads=threads,
                       max_parallel_shots=threads)
    res = sim.run(qc, shots=shots, seed_simulator=seed, memory=True).result()
    if not res.success:
        raise RuntimeError(res.status)
    P = np.asarray(res.data(0)["psec"], dtype=float)
    raw = np.array([int(s.replace(" ", ""), 2) for s in res.get_memory(0)], dtype=np.int64)
    return P, raw, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lattice"); ap.add_argument("family"); ap.add_argument("device"); ap.add_argument("tag")
    ap.add_argument("--shots", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--engine", default="sparse", choices=["sparse", "aer"])
    ap.add_argument("--threads", type=int, default=int(os.environ.get("AER_THREADS", "4")))
    ap.add_argument("--outdir", default="noisy_runs")
    a = ap.parse_args()
    out = os.path.join(lattice_results(a.lattice), a.family, a.device, a.outdir, a.tag + ".json")
    if os.path.exists(out):
        print("exists", out)
        return
    t0 = time.time()
    Lx = int(a.lattice.split("x")[1])
    twoB, ref, k = circuits.parse_tag(a.tag)
    seed = a.seed if a.seed is not None else zlib.crc32(f"{a.lattice}|{a.family}|{a.device}|{a.tag}".encode()) % 2 ** 31
    gates, n = circuits.ir_gates(a.lattice, a.family, a.tag)
    d = targets.model(Lx)
    assert n == d["n"]
    ints = d["ints"]
    sector = targets.sector(Lx, twoB)
    sec_ints = ints[sector]
    tgt = targets.target(Lx, twoB, ref, k)
    pc = np.abs(tgt[sector]) ** 2
    pc_total = float(pc.sum())
    pc = pc / pc_total
    ref_pos = int(np.nonzero(sector == ref)[0][0])
    p_ref = float(pc[ref_pos])
    ref_int = int(ints[ref])
    t1 = time.time()
    if a.engine == "sparse":
        E = ts.Engine(gates, n, a.device)
        bud = E.budget
        clean = E.clean.dense_on(ints)
        ov = np.vdot(tgt, clean)
        clean_dev = float(np.abs(clean * np.exp(-1j * np.angle(ov)) - tgt).max())
        P, raw, diag = run_sparse(E, a.shots, seed, sec_ints, n)
        diag["clean_state_max_abs_dpsi"] = clean_dev
        diag["clean_prune_bound"] = E.clean_prune
    else:
        _, bud = ts.ir_events(gates, n, a.device)
        P, raw, diag = run_aer(gates, n, a.device, a.shots, seed, sec_ints, a.threads)
    t_sim = time.time() - t1
    # readout flips (classical, seeded)
    p10, p01 = nm.readout_probs(a.device)
    rng = np.random.default_rng(seed + 1)
    bits = ((raw[:, None] >> np.arange(n)) & 1).astype(np.int8)
    u = rng.random(bits.shape)
    flip = np.where(bits == 0, u < p10, u < p01)
    post = ((bits ^ flip).astype(np.int64) << np.arange(n)).sum(axis=1)
    # package decoding
    uniq, cnt = np.unique(post, return_counts=True)
    counts = {tuple(int((x >> q) & 1) for q in range(n)): int(c) for x, c in zip(uniq, cnt)}
    acc, rej = d["codec"].decode_counts(counts, target_twoB=twoB)
    n_acc = int(sum(acc.values()))
    sec_index = {int(x): i for i, x in enumerate(sec_ints)}
    member = np.array([int(x) in sec_index for x in post])
    hits = int((post == ref_int).sum())
    rb = [(ref_int >> q) & 1 for q in range(n)]
    rho_ref = float(np.prod([(1 - p01) if b else (1 - p10) for b in rb]))
    w = P.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        Pn = P / w[:, None]
    tv_pre = 0.5 * np.abs(Pn - pc[None, :]).sum(axis=1)
    tv_pre[~(w > 0)] = 1.0
    b_all = {str(dl): float(np.mean(tv_pre < dl)) for dl in DELTAS}
    f_ideal = {str(dl): rho_ref * b_all[str(dl)] for dl in DELTAS}
    f_hit = (hits / a.shots) / p_ref
    brng = np.random.default_rng(2028)
    idx = brng.integers(0, a.shots, size=(2000, a.shots))
    hv = (post == ref_int).astype(float)
    fh_b = hv[idx].mean(axis=1) / p_ref
    fi_b = rho_ref * (tv_pre[idx] < 1e-3).mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        r_b = fh_b / fi_b
    r_nc = f_hit / f_ideal["0.001"] if f_ideal["0.001"] > 0 else None
    q = np.zeros(len(sector))
    for kk, c in acc.items():
        q[np.nonzero(sector == kk)[0][0]] += c
    tv_acc = tv(q / n_acc, pc) if n_acc else None
    frng = np.random.default_rng(seed + 2)
    floors = [tv(frng.multinomial(max(n_acc, 1), pc) / max(n_acc, 1), pc) for _ in range(20)]
    good = w > 0
    mix = Pn[good].mean(axis=0) if good.any() else np.zeros_like(pc)
    p_fault_free = bud["f_gate"]
    rec = {"lattice": a.lattice, "family": a.family, "device": a.device, "circuit": a.tag, "engine_name": a.engine,
           "twoB": twoB, "reference": ref, "k": k, "shots": a.shots, "seed_simulator": seed,
           "seed_readout": seed + 1, "seed_floor": seed + 2, "seed_bootstrap": 2028,
           "n_qubits": n, "sector_size": int(len(sector)), "p_ref": p_ref, "ideal_weight_in_sector": pc_total,
           "budget": bud, "f_model": p_fault_free * (1 - 0.5 * (p10 + p01)) ** n, "f_gate": p_fault_free,
           "f0_prime": p_fault_free * rho_ref, "readout_survival_ref": rho_ref,
           "acceptance": n_acc / a.shots, "acceptance_ci95": wilson(n_acc, a.shots),
           "acceptance_codeword_membership": float(member.mean()), "rejections": rej,
           "acceptance_random_level": len(sector) / 2 ** n,
           "ref_hits": hits, "f_hit": f_hit, "f_hit_ci95": [x / p_ref for x in wilson(hits, a.shots)],
           "f_hit_traj": float(np.mean(P[:, ref_pos])) * rho_ref / p_ref,
           "b_all": b_all, "f_ideal": f_ideal,
           "f_ideal_1e-3_ci95": [float(np.percentile(fi_b, 2.5)), float(np.percentile(fi_b, 97.5))],
           "r_nc": r_nc, "r_nc_ci95": [float(np.nanpercentile(r_b[np.isfinite(r_b)], 2.5)),
                                       float(np.nanpercentile(r_b[np.isfinite(r_b)], 97.5))] if np.isfinite(r_b).any() else None,
           "mean_sector_weight_pre_readout": float(w.mean()),
           "tv_accepted": tv_acc, "tv_accepted_floor_mean": float(np.mean(floors)),
           "tv_accepted_floor_sd": float(np.std(floors)), "tv_population_pre_readout": tv(mix, pc),
           "accepted_counts": {int(kk): int(c) for kk, c in acc.items()},
           "engine_diagnostics": diag,
           "engine": {"sparse": "skqd.sparse_sim (package) via noise/src/traj_sparse.py, prune |a|<1e-12 every 32 gates",
                      "aer": "qiskit_aer AerSimulator statevector double, QuantumError instructions"}[a.engine],
           "noise_placement": "IR level (traj_sparse.ir_events)",
           "noise_spec_file": os.path.relpath(nm.spec_path(a.device), circuits.NOISE),
           "noise_spec_sha256": nm.spec_sha256(a.device), "noise_model_params": nm.params(a.device),
           "timing_s": {"simulate": t_sim, "total": time.time() - t0}, "provenance": provenance()}
    dump(rec, out)
    print(a.lattice, a.family, a.device, a.tag, a.engine, f"acc {rec['acceptance']:.3f} f {rec['f_model']:.3f}",
          f"f_hit {f_hit:.3f} f_ideal {f_ideal['0.001']:.3f} r_nc {r_nc if r_nc is None else round(r_nc, 3)}",
          f"tv_acc {tv_acc if tv_acc is None else round(tv_acc, 3)}/{np.mean(floors):.3f} sim {t_sim:.0f}s", flush=True)


if __name__ == "__main__":
    main()
