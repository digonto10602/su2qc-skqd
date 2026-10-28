"""Independent statevector check of a FROZEN family through the loader API (c2x4.families.get_family, i.e. exactly
the qiskit circuits the noise agent receives), with qiskit-aer, against the package's exact coarse states.

Independence from my evaluator: no study simulator, no study target or Problem object.  The target is
skqd.krylov.coarse_states(term_groups(Model(Lx).terms, 4, mass_default(4)), basis_vector(ref), dt, k)[k] with dt
from the package (2x4: validation/E3.json; 2x3: Model(3).reference(4, 2B).dt, the frozen 2x3 family's rule), embedded
with skqd.reference_sim.CodewordEmbedding (qubit k = bit k).  Engine: AerSimulator(method=statevector,
precision=double), fusion off by default (so no fusion error enters).  Reported per circuit: max |dpsi| after removing
the global phase, l2 norm, leakage on non-codeword strings and on codewords of the other sector (summed directly),
the measured global phase against the metadata's global_phase_vs_target, and the bar
(max |dpsi| < 1e-10, total leakage < 1e-9).

Usage: python scripts/verify_aer_family.py --family compressed_circuit_llm_2x3_classA [--ids B0_ref25_k1,...]
       [--threads 6] [--fusion]
Writes data/c2x3/aer_<family>.json (2x3) or data/aer_<family>[_<label>].json (2x4).
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(STUDY, "src"))

from skqd.exact import Model, mass_default                                       # noqa: E402
from skqd.krylov import basis_vector, coarse_states, term_groups                 # noqa: E402
from skqd.reference_sim import CodewordEmbedding                                 # noqa: E402
from c2x4.env import write_json                                                  # noqa: E402
from c2x4.families import family_header, get_family                             # noqa: E402


def package_dt(M, lx: int, twoB: int) -> float:
    if lx == 4:
        with open(os.path.join(ROOT, "validation", "E3.json")) as fh:
            E3 = json.load(fh)["data"]["references"]
        return float(E3[f"2x4|g2=4.0|2B={twoB}"]["dt"])
    return float(M.reference(4.0, twoB).dt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--ids", default="all")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--fusion", action="store_true")
    ap.add_argument("--label", default="")
    ap.add_argument("--max-wall", type=float, default=1700.0)
    ap.add_argument("--superposition-seeds", default="",
                    help="comma list of seeds: also run the operator test on a random superposition of the circuit's "
                         "sector codewords (manual 5.4; class A must pass, class B is expected to fail).  The "
                         "X-gate prefix is undone on the input (|cw> -> |cw ^ ref>), so the circuit body acts on phi.")
    args = ap.parse_args()
    t0 = time.time()
    from qiskit_aer import AerSimulator
    import qiskit
    import qiskit_aer
    hdr = family_header(args.family)
    lx = int(hdr["lattice"].split("x")[1])
    M = Model(lx)
    g2 = 4.0
    m = mass_default(g2)
    groups = term_groups(M.terms, g2, m)
    groups_d = M.terms.groups(g2, m)
    E = CodewordEmbedding(M)
    ints = np.asarray(E.ints, dtype=np.int64)
    n = int(E.n)
    dim = M.basis.dim
    dts = {tb: package_dt(M, lx, tb) for tb in (0, 2)}
    fam = get_family(args.family)
    want = None if args.ids == "all" else set(args.ids.split(","))
    sim = AerSimulator(method="statevector", precision="double", fusion_enable=bool(args.fusion),
                       max_parallel_threads=args.threads)
    Hd = groups_d["diag"]
    Hd = Hd.tocsr() if hasattr(Hd, "tocsr") else Hd
    rows = {}
    truncated = False
    for cid, qc, md in fam:
        if want is not None and cid not in want:
            continue
        if time.time() - t0 > args.max_wall:
            truncated = True
            break
        twoB, ref, k = md["twoB"], md["reference"], md["k"]
        dt = dts[twoB]
        target = coarse_states(groups, basis_vector(dim, ref), dt, k)[k]
        qc2 = qc.copy()
        qc2.save_statevector()
        t1 = time.time()
        res = sim.run(qc2, shots=1, seed_simulator=1).result()
        t_sim = time.time() - t1
        if not res.success:
            raise RuntimeError(res.status)
        psi = np.asarray(res.data(0)["statevector"].data)
        got = psi[ints].copy()
        psi[ints] = 0
        leak_nc = float(np.vdot(psi, psi).real)
        del psi
        sector = np.asarray(M.basis.sector(twoB))
        nonsector = np.setdiff1d(np.arange(dim), sector)
        leak_sec = float(np.sum(np.abs(got[nonsector]) ** 2))
        ov = np.vdot(target, got)
        ph = float(np.angle(ov))
        d = got * np.exp(-1j * ph) - target
        dev = float(np.abs(d).max())
        l2 = float(np.sqrt(np.sum(np.abs(d) ** 2) + leak_nc))
        pred = float(np.angle(np.exp(1j * md["global_phase_vs_target"])))
        n2 = sum(1 for ins in qc.data if ins.operation.num_qubits == 2)
        rows[cid] = {"twoB": twoB, "reference": ref, "k": k, "dt_package": dt, "dt_metadata": md["dt"],
                     "n_2q_qiskit": n2, "n_2q_metadata": md["n_2q"],
                     "max_abs_dpsi_phase_aligned": dev, "l2_dpsi_phase_aligned_incl_leak": l2,
                     "leakage_noncodeword": leak_nc, "leakage_other_sector_codewords": leak_sec,
                     "leakage_total": leak_nc + leak_sec, "global_phase_rad": ph,
                     "global_phase_predicted_rad": pred,
                     "global_phase_minus_predicted_rad": float(np.angle(np.exp(1j * (ph - pred)))),
                     "pass_bar": bool(dev < 1e-10 and leak_nc + leak_sec < 1e-9), "aer_s": t_sim}
        print(cid, f"dev {dev:.2e} leak {leak_nc + leak_sec:.1e} phase-pred {rows[cid]['global_phase_minus_predicted_rad']:.1e}"
              f" 2q {n2} pass {rows[cid]['pass_bar']} ({t_sim:.1f} s)", flush=True)
    sup_rows = {}
    seeds = [int(v) for v in args.superposition_seeds.split(",") if v.strip()]
    if seeds:
        from qiskit import QuantumCircuit
        from skqd.krylov import apply_groups
        for cid, qc, md in fam:
            if want is not None and cid not in want:
                continue
            twoB, ref, k = md["twoB"], md["reference"], md["k"]
            ref_int = int(ints[ref])
            if ref_int != int(md["reference_bits"]):
                raise ValueError(f"{cid}: metadata reference_bits {md['reference_bits']} != codeword {ref_int}")
            sector = np.asarray(M.basis.sector(twoB))
            for seed in seeds:
                rng = np.random.default_rng(seed)
                c = rng.normal(size=len(sector)) + 1j * rng.normal(size=len(sector))
                c /= np.linalg.norm(c)
                phi = np.zeros(dim, dtype=complex)
                phi[sector] = c
                target = apply_groups(groups, phi.copy(), k * dts[twoB])
                init = np.zeros(2 ** n, dtype=complex)
                init[ints ^ ref_int] = phi
                pre = QuantumCircuit(n)
                pre.set_statevector(init)
                qc2 = pre.compose(qc)
                qc2.save_statevector()
                res = sim.run(qc2, shots=1, seed_simulator=1).result()
                if not res.success:
                    raise RuntimeError(res.status)
                psi = np.asarray(res.data(0)["statevector"].data)
                got = psi[ints].copy()
                psi[ints] = 0
                leak_nc = float(np.vdot(psi, psi).real)
                ov = np.vdot(target, got)
                ph = float(np.angle(ov))
                d = got * np.exp(-1j * ph) - target
                dev = float(np.abs(d).max())
                sup_rows[f"{cid}:seed{seed}"] = {
                    "circuit_id": cid, "seed": seed, "n_components": int(len(sector)),
                    "max_abs_dpsi_phase_aligned": dev, "l2_dpsi_phase_aligned": float(np.linalg.norm(d)),
                    "leakage_noncodeword": leak_nc, "global_phase_rad": ph,
                    "global_phase_minus_predicted_rad": float(np.angle(np.exp(1j * (ph - md["global_phase_vs_target"])))),
                    "pass_bar": bool(dev < 1e-10 and leak_nc < 1e-9)}
            print(cid, "superposition", [f"{sup_rows[f'{cid}:seed{s_}']['l2_dpsi_phase_aligned']:.2e}" for s_ in seeds],
                  flush=True)
    vals = list(rows.values())
    summary = {"n": len(vals), "n_pass": sum(r["pass_bar"] for r in vals),
               "max_abs_dpsi": max((r["max_abs_dpsi_phase_aligned"] for r in vals), default=None),
               "max_leakage_total": max((r["leakage_total"] for r in vals), default=None),
               "max_abs_phase_minus_predicted": max((abs(r["global_phase_minus_predicted_rad"]) for r in vals),
                                                    default=None),
               "n_2q_consistent": all(r["n_2q_qiskit"] == r["n_2q_metadata"] for r in vals),
               "dt_consistent": all(abs(r["dt_package"] - r["dt_metadata"]) < 1e-15 for r in vals),
               "truncated": truncated}
    if sup_rows:
        sv = list(sup_rows.values())
        summary["random_superposition"] = {
            "seeds": seeds, "n": len(sv), "n_pass": sum(r["pass_bar"] for r in sv),
            "max_abs_dpsi": max(r["max_abs_dpsi_phase_aligned"] for r in sv),
            "max_l2_dpsi": max(r["l2_dpsi_phase_aligned"] for r in sv),
            "min_l2_dpsi": min(r["l2_dpsi_phase_aligned"] for r in sv),
            "max_leakage_noncodeword": max(r["leakage_noncodeword"] for r in sv),
            "max_abs_phase_minus_predicted": max(abs(r["global_phase_minus_predicted_rad"]) for r in sv)}
    print(summary)
    sub = "" if lx == 4 else f"c2x{lx}/"
    lab = f"_{args.label}" if args.label else ""
    p = write_json(f"data/{sub}aer_{args.family}{lab}.json",
                   {"family": args.family, "circuits": rows, "summary": summary, "random_superposition": sup_rows,
                    "engine": {"qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__,
                               "method": "statevector", "precision": "double", "fusion": bool(args.fusion),
                               "threads": args.threads},
                    "peak_rss_GiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 20},
                   produced_by="2x4_compression_using_ai_v1/scripts/verify_aer_family.py",
                   parameters=vars(args), seed={"aer_seed_simulator": 1, "superposition_rng": seeds}, t_start=t0)
    print("wrote", p)


if __name__ == "__main__":
    main()
