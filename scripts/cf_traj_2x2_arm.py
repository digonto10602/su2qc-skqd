#!/usr/bin/env python3
"""
prompts/28 A5 (optional, information only): the Pauli-trajectory decomposition at 2x2 on the H0_2x2 adopted
k = 1 circuit `B0_ref06_k1` (cell T3: ALAP schedule with explicit delays, client-side XY4 DD in windows >= 8 x
the sequence), under a Pauli model built from the H0_2x2 calibration record and the pilot's Ramsey T2*:

  cz      depolarizing_error(eps_cz(edge), 2)   -> a non-identity 2q Pauli with probability 15/16 eps_cz
  sx, x   depolarizing_error(eps_sx(q), 1)       -> X, Y or Z with probability 3/4 eps_sx (x uses x_error)
  rz      noiseless (virtual)
  delay   (every explicit delay of the scheduled circuit = one idle window of duration t on qubit q)
          Z with probability 1/2 (1 - exp(-t / T2*_q))   (Pauli-twirled pure dephasing, prompts/28 A5)
  measure symmetric readout flip at the record's measure_error(q)

T2*_q = validation/H0_kpilot.json data.ramsey.<q>.T2star_s (with its provenance: several entries are 3-sigma
upper bounds or the patch minimum, not measurements).  This Markovian model cannot represent DD's refocusing
of quasi-static dephasing, so f0' here is a model number for the composition question (how much of the
faulty weight returns to the reference / the tail class), not a prediction of the device's f.

Simulation: 12 logical qubits, numpy statevector (qubit k = bit k), exact readout convolution.
Output: data/cf_trajectories/A5_2x2/result.json (summary read by gate_CF_traj) and trajectories.json;
--t2 echo writes result_echo.json / trajectories_echo.json (the record's echo T2 instead of T2*: a bracket).
Usage: python scripts/cf_traj_2x2_arm.py [--K 2000 --seed 501]
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import cf_trajectories as cf  # noqa: E402

PREP = os.path.join(ROOT, "data", "hardware", "H0_2x2_prep")
CID = "B0_ref06_k1"
OUTDIR = os.environ.get("CF_A5_OUT", os.path.join(cf.OUT, "A5_2x2"))   # env: smoke runs elsewhere
N_BOOT, BOOT_SEED = 2000, 2028

_SX = 0.5 * np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]])
_X = np.array([[0, 1], [1, 0]], complex)
_Y = np.array([[0, -1j], [1j, 0]], complex)
_Z = np.array([[1, 0], [0, -1]], complex)


def apply_1q(psi, n, q, U):
    v = psi.reshape(2 ** (n - 1 - q), 2, 2 ** q)
    a0, a1 = v[:, 0, :].copy(), v[:, 1, :].copy()
    v[:, 0, :] = U[0, 0] * a0 + U[0, 1] * a1
    v[:, 1, :] = U[1, 0] * a0 + U[1, 1] * a1


def simulate(ops, n, diag_cache):
    psi = np.zeros(2 ** n, complex)
    psi[0] = 1.0
    for op in ops:
        name, qs, par = op
        if name == "rz":
            apply_1q(psi, n, qs[0], np.diag([np.exp(-0.5j * par), np.exp(0.5j * par)]))
        elif name == "sx":
            apply_1q(psi, n, qs[0], _SX)
        elif name == "x":
            apply_1q(psi, n, qs[0], _X)
        elif name == "y":
            apply_1q(psi, n, qs[0], _Y)
        elif name == "z":
            apply_1q(psi, n, qs[0], _Z)
        elif name == "cz":
            key = tuple(sorted(qs))
            if key not in diag_cache:
                idx = np.arange(2 ** n)
                diag_cache[key] = np.where(((idx >> key[0]) & 1) & ((idx >> key[1]) & 1), -1.0, 1.0)
            psi *= diag_cache[key]
        elif name == "delay":
            continue
        else:
            raise ValueError(name)
    return psi


def load_logical_ops(man, rec):
    from qiskit import qpy

    with gzip.open(os.path.join(PREP, "circuits", man["qpy"]), "rb") as fh:
        qc = qpy.load(fh)[0]
    l2p = [int(p) for p in man["logical_to_physical"]]
    p2l = {p: i for i, p in enumerate(l2p)}
    dt = float(rec["dt_s"])
    ops, windows, cmap = [], [], {}
    for inst in qc.data:
        name = inst.operation.name
        phys = [qc.find_bit(q).index for q in inst.qubits]
        if name == "barrier":
            continue
        if not all(p in p2l for p in phys):
            if name == "delay":
                continue            # ALAP padding of qubits outside the patch
            raise SystemExit(f"{name} on {phys} leaves the patch")
        qs = [p2l[p] for p in phys]
        if name == "measure":
            cmap[qs[0]] = qc.find_bit(inst.clbits[0]).index
            continue
        if name == "delay":
            d = float(inst.operation.duration)
            unit = inst.operation.unit
            t = d * dt if unit == "dt" else d * {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}[unit]
            ops.append(("delay", qs, t))
            continue
        par = float(inst.operation.params[0]) if inst.operation.params else None
        ops.append((name, qs, par))
    if cmap != {i: i for i in range(len(l2p))}:
        raise SystemExit(f"measurement map is not logical i -> clbit i: {cmap}")
    return ops, l2p, qc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--K", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=501)
    ap.add_argument("--t2", choices=("star", "echo"), default="star",
                    help="star = the pilot's Ramsey T2* (prompts/28 A5); echo = the record's T2 (bracket, information)")
    args = ap.parse_args(argv)
    t0 = time.time()
    from skqd.exact import Model
    from skqd.reference_sim import CodewordEmbedding

    man = json.load(open(os.path.join(PREP, "circuits", CID + ".json")))
    idx = json.load(open(os.path.join(PREP, "index.json")))
    rec = json.load(open(os.path.join(ROOT, idx["record"]["path"])))
    ramsey = json.load(open(os.path.join(ROOT, "validation", "H0_kpilot.json")))["data"]["ramsey"]
    ops, l2p, _qc = load_logical_ops(man, rec)
    n = len(l2p)
    edges = {}
    for e in rec["edges"].values():
        a, b = (int(x) for x in e["target_key"])
        edges[(min(a, b), max(a, b))] = float(e["cz_error"])
    # noise sites
    sites, windows = [], []
    for pos, (name, qs, par) in enumerate(ops):
        phys = [l2p[q] for q in qs]
        if name == "cz":
            eps = edges[(min(phys), max(phys))]
            sites.append({"pos": pos, "kind": "2q", "qs": qs, "p": 15 / 16 * eps, "labels": cf.PAULIS_2Q})
        elif name in ("sx", "x"):
            eps = float(rec["qubits"][str(phys[0])][name + "_error"])
            sites.append({"pos": pos, "kind": "1q", "qs": qs, "p": 0.75 * eps, "labels": cf.PAULIS_1Q})
        elif name == "delay":
            T2s = (float(ramsey[str(phys[0])]["T2star_s"]) if args.t2 == "star"
                   else float(rec["qubits"][str(phys[0])]["T2_s"]))
            pz = 0.5 * (1.0 - math.exp(-par / T2s))
            sites.append({"pos": pos, "kind": "idle", "qs": qs, "p": pz, "labels": ["Z"]})
            windows.append({"logical": qs[0], "physical": phys[0], "t_s": par, "T2star_s": T2s, "p_z": pz})
    probs = np.array([s["p"] for s in sites])
    g0 = float(np.prod(1.0 - probs))
    # ideal and sector
    cache = {}
    psi0 = simulate(ops, n, cache)
    p_ideal = np.abs(psi0) ** 2
    ref_int = int(np.argmax(p_ideal))
    if abs(p_ideal[ref_int] - float(man["p_reference"])) > 1e-9:
        raise SystemExit(f"ideal p(ref) {p_ideal[ref_int]} != manifest {man['p_reference']}")
    M = Model(2)
    emb = CodewordEmbedding(M)
    R = M.reference(4.0, int(man["twoB"]), k=4)
    ints = np.asarray(emb.ints[np.asarray(R.indices, int)], np.int64)
    pc = p_ideal[ints] / p_ideal[ints].sum()
    ref_pos = int(np.nonzero(ints == ref_int)[0][0])
    tail = [int(i) for i in np.nonzero(pc >= cf.TAIL_P_MIN)[0] if int(i) != ref_pos]
    pT = float(pc[tail].sum())
    meas = np.array([float(rec["qubits"][str(l2p[q])]["measure_error"]) for q in range(n)])

    def readout(p):
        q = p.copy()
        for k in range(n):
            v = q.reshape(2 ** (n - 1 - k), 2, 2 ** k)
            a0, a1 = v[:, 0, :].copy(), v[:, 1, :].copy()
            e = meas[k]
            v[:, 0, :] = (1 - e) * a0 + e * a1
            v[:, 1, :] = e * a0 + (1 - e) * a1
        return q

    ref_bits = [(ref_int >> k) & 1 for k in range(n)]
    r_ref = float(np.prod([1 - meas[k] for k in range(n)]))
    f0 = g0 * r_ref
    rng = np.random.default_rng(args.seed)
    trajs, draws = [], 0
    H, T, TV, ZO = [], [], [], []
    while len(trajs) < args.K:
        draws += 1
        hit = np.nonzero(rng.random(len(probs)) < probs)[0]
        if len(hit) == 0:
            continue
        ev = []
        for i in hit:
            s = sites[int(i)]
            ev.append((s["pos"], s["qs"], s["labels"][int(rng.integers(len(s["labels"])))], s["kind"]))
        by = {}
        for e in ev:
            by.setdefault(e[0], []).append(e)
        nops = []
        for pos, op in enumerate(ops):
            nops.append(op)
            for e in by.get(pos, ()):
                for q, c in zip(e[1], e[2]):
                    if c != "I":
                        nops.append((c.lower(), [q], None))
        p = np.abs(simulate(nops, n, cache)) ** 2
        pp = readout(p)
        H.append(float(pp[ref_int]))
        T.append(float(pp[ints][tail].sum()))
        TV.append(cf.tv_distance(p[ints], pc))
        ZO.append(all(set(e[2]) <= {"I", "Z"} for e in ev))
        trajs.append({"n_events": len(ev), "n_idle": sum(e[3] == "idle" for e in ev),
                      "p_ref_post": H[-1], "tail_post": T[-1], "tv_pre": TV[-1], "z_only": ZO[-1]})
    H, T, TV, ZO = map(np.asarray, (H, T, TV, ZO))
    p_ref = float(man["p_reference"])
    K = len(H)

    def stats(w):
        hm, tm = float(w @ H), float(w @ T)
        fh = f0 + (1 - f0) * hm / p_ref
        fT = f0 + (1 - f0) * tm / pT
        return {"h_ref": hm, "f_hit": fh, "rho_ref": fh / f0, "tail_mean": tm, "f_T": fT, "rho_T": fT / f0,
                "benign_fraction": float(w @ (TV < cf.BENIGN_TV))}

    pt = stats(np.full(K, 1.0 / K))
    W = np.random.default_rng(BOOT_SEED).multinomial(K, np.full(K, 1.0 / K), size=N_BOOT) / K
    bs = [stats(w) for w in W]
    out = {"produced_by": "scripts/cf_traj_2x2_arm.py", "prompt": "prompts/28 A5 (optional, information)",
           "status": "run", "t2_variant": args.t2, "circuit": CID, "dd_cell": man["dd"]["cell"], "K": K, "seed": args.seed,
           "git_commit": cf.git_commit()[0], "created": cf.now(),
           "model": __doc__.split("Simulation:")[0].strip(),
           "record": idx["record"]["path"], "ramsey_source": "validation/H0_kpilot.json data.ramsey",
           "T2_used": {str(l2p[q]): ({"T2star_s": float(ramsey[str(l2p[q])]["T2star_s"]),
                                      "provenance": ramsey[str(l2p[q])]["provenance"]} if args.t2 == "star" else
                                     {"T2_echo_record_s": float(rec["qubits"][str(l2p[q])]["T2_s"])})
                       for q in range(n)},
           "n_sites": {"2q": sum(s["kind"] == "2q" for s in sites), "1q": sum(s["kind"] == "1q" for s in sites),
                       "idle_windows": len(windows)},
           "window_list": windows,
           "g0": g0, "readout_survival_reference": r_ref, "f0_prime": f0, "p_ref": p_ref,
           "ref_int": ref_int, "ref_bits": ref_bits, "tail_class": {"size": len(tail), "p_Tc": pT},
           "n_draws": draws, "n_rejected": draws - K,
           "z_only_fraction": float(ZO.mean()), "h_ref_z_only": float(H[ZO].mean()) if ZO.any() else None,
           "h_ref_not_z_only": float(H[~ZO].mean()) if (~ZO).any() else None,
           "stats": {k: {"value": v, "ci95": [float(np.percentile([b[k] for b in bs], 2.5)),
                                              float(np.percentile([b[k] for b in bs], 97.5))]}
                     for k, v in pt.items()},
           "wall_s": time.time() - t0}
    os.makedirs(OUTDIR, exist_ok=True)
    tag = "" if args.t2 == "star" else "_echo"
    with open(os.path.join(OUTDIR, f"trajectories{tag}.json"), "w") as fh:
        json.dump(trajs, fh)
    with open(os.path.join(OUTDIR, f"result{tag}.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: out[k] for k in ("K", "g0", "f0_prime", "n_sites", "z_only_fraction", "wall_s")}, indent=1))
    print(json.dumps(out["stats"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
