"""Noisy SKQD campaign: one chunk of Pauli trajectories (one shot = one trajectory) of one circuit under one device
model, with the full shot sequence kept for the SKQD analysis (scripts/skqd_analyse.py).

Usage: python skqd_sample.py LATTICE FAMILY DEVICE CID --chunk I --start S --shots N
Writes <lattice results>/<FAMILY>/<DEVICE>/skqd_samples/<CID>/c<III>.npz and .json (skips if present).

Engine: noise/src/traj_sparse.py (the package's exact sparse simulator skqd.sparse_sim on the IR gate list, faults
sampled from the device model of noise/src/noise_models.py and inserted as Pauli gates; validated against Aer to
2.7e-12, reports/003), identical to scripts/noisy_run.py; only the bookkeeping differs: noisy_run keeps the
accepted histogram, this script keeps every shot in order (prefix analysis) and the per-shot pre-readout numbers.

Per shot (arrays in the .npz, shot order):
  post      post-readout string (qubit k = bit k), uint32 at n <= 32
  nf        number of sampled faults (uint16)
  tv_pre    1/2 sum_s |p_tau(s)/w_tau - p_c(s)| over the sector codewords (TV_pre of noisy_run.py), float32
  w         sector weight w_tau of the pre-readout state, float32
  p_ref     pre-readout probability of the reference string, float32
Seeds: simulator crc32("lattice|family|device|cid|skqd|chunk") % 2^31 (campaign.chunk_seed), readout seed + 1.
"""
import os as _os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")   # one BLAS thread per job: the queue runs several jobs in parallel

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import campaign as C  # noqa: E402
import circuits  # noqa: E402
import noise_models as nm  # noqa: E402
import targets  # noqa: E402
import traj_sparse as ts  # noqa: E402
from provenance import provenance, dump  # noqa: E402


def gates_of(lattice, family, cid):
    src = C.circuits(lattice, family)[cid]
    if src == "frozen":
        return circuits.ir_gates(lattice, "frozen", cid), src
    g, md = circuits.genie_ir(src)[cid]
    assert md["lattice"] == lattice, (md["lattice"], lattice)
    return (g, int(md["n_qubits"])), src


def run(lattice, family, device, cid, chunk, start, shots, time_limit=None):
    out = C.chunk_path(lattice, family, device, cid, chunk)
    if os.path.exists(out):
        print("exists", out)
        return None
    t0 = time.time()
    Lx = int(lattice.split("x")[1])
    twoB, ref, k = C.parse(cid)
    seed = C.chunk_seed(lattice, family, device, cid, chunk)
    (gates, n), src = gates_of(lattice, family, cid)
    d = targets.model(Lx)
    assert n == d["n"], (n, d["n"])
    ints = d["ints"]
    sector = targets.sector(Lx, twoB)
    sec_ints = ints[sector]
    tgt = targets.target(Lx, twoB, ref, k)
    pc = np.abs(tgt[sector]) ** 2
    pc = pc / pc.sum()
    ref_int = int(ints[ref])
    order = np.argsort(sec_ints)
    sorted_sec = sec_ints[order]
    pc_sorted = pc[order]
    E = ts.Engine(gates, n, device)
    clean = E.clean.dense_on(ints)
    ov = np.vdot(tgt, clean)
    clean_dev = float(np.abs(clean * np.exp(-1j * np.angle(ov)) - tgt).max())
    leak = float(1.0 - np.sum(np.abs(clean) ** 2))
    t_init = time.time() - t0
    rng = np.random.default_rng(seed)
    raw = np.zeros(shots, dtype=np.int64)
    nf = np.zeros(shots, dtype=np.uint16)
    tvp = np.zeros(shots, dtype=np.float32)
    w = np.zeros(shots, dtype=np.float32)
    pref = np.zeros(shots, dtype=np.float32)
    prune = 0.0
    t1 = time.time()
    done = shots
    for s in range(shots):
        faults = E.sample_faults(rng)
        idx, amp, b, kf = E.trajectory(faults)
        pr = np.abs(amp) ** 2
        tot = pr.sum()
        raw[s] = idx[rng.choice(len(idx), p=pr / tot)]
        pos = np.searchsorted(idx, sorted_sec)
        pos[pos >= len(idx)] = len(idx) - 1
        hit = idx[pos] == sorted_sec
        ps = np.where(hit, pr[pos], 0.0)
        ws = ps.sum()
        w[s] = ws
        tvp[s] = 0.5 * np.abs(ps / ws - pc_sorted).sum() if ws > 0 else 1.0
        j = np.searchsorted(idx, ref_int)
        pref[s] = pr[j] if (j < len(idx) and idx[j] == ref_int) else 0.0
        nf[s] = min(kf, 65535)
        prune = max(prune, b)
        if time_limit and time.time() - t0 > time_limit:
            done = s + 1
            break
    t_sim = time.time() - t1
    raw, nf, tvp, w, pref = raw[:done], nf[:done], tvp[:done], w[:done], pref[:done]
    p10, p01 = nm.readout_probs(device)
    rrng = np.random.default_rng(seed + 1)
    bits = ((raw[:, None] >> np.arange(n)) & 1).astype(np.int8)
    u = rrng.random(bits.shape)
    flip = np.where(bits == 0, u < p10, u < p01)
    post = ((bits ^ flip).astype(np.int64) << np.arange(n)).sum(axis=1)
    meta = {"lattice": lattice, "family": family, "source_family": src, "device": device, "circuit": cid,
            "twoB": twoB, "reference": ref, "k": k, "chunk": int(chunk), "start": int(start), "shots": int(done),
            "shots_requested": int(shots), "truncated_by_time_limit": bool(done < shots),
            "seed_simulator": seed, "seed_readout": seed + 1, "n_qubits": n, "sector_size": int(len(sector)),
            "reference_int": ref_int, "p_ref": float(pc[int(np.nonzero(sector == ref)[0][0])]),
            "readout_p10_p01": [p10, p01], "budget": E.budget, "f_gate": E.budget["f_gate"],
            "clean_state_max_abs_dpsi": clean_dev, "clean_state_leakage": leak, "clean_prune_bound": E.clean_prune,
            "prune_bound_max": prune, "fault_free_fraction": float(np.mean(nf == 0)),
            "engine": "skqd.sparse_sim (package) via noise/src/traj_sparse.py, prune |a|<1e-12 every 32 gates",
            "noise_placement": "IR level (traj_sparse.ir_events)",
            "noise_spec_file": os.path.relpath(nm.spec_path(device), circuits.NOISE),
            "noise_spec_sha256": nm.spec_sha256(device), "noise_model_params": nm.params(device),
            "timing_s": {"init": t_init, "simulate": t_sim, "per_shot": t_sim / max(done, 1),
                         "total": time.time() - t0},
            "threads": {"OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
                        "affinity": sorted(os.sched_getaffinity(0))},
            "provenance": provenance()}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    dt = np.uint32 if n <= 32 else np.uint64
    tmp = out[:-4] + ".tmp.npz"
    np.savez_compressed(tmp, post=post.astype(dt), nf=nf, tv_pre=tvp, w=w, p_ref=pref)
    dump(meta, out[:-4] + ".json")
    os.replace(tmp, out)
    acc = float(np.isin(post, sorted_sec).mean())
    print(lattice, C.short(family), device, cid, f"chunk {chunk} shots {done} f_gate {E.budget['f_gate']:.3f}",
          f"ff {meta['fault_free_fraction']:.3f} member {acc:.3f} init {t_init:.1f}s sim {t_sim:.1f}s",
          f"({t_sim / max(done, 1):.4f} s/shot) dpsi {clean_dev:.1e}", flush=True)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lattice"); ap.add_argument("family"); ap.add_argument("device"); ap.add_argument("cid")
    ap.add_argument("--chunk", type=int, required=True)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--shots", type=int, required=True)
    ap.add_argument("--time-limit", type=float, default=None,
                    help="timing probes only: stop after this many seconds (the chunk is then marked truncated)")
    a = ap.parse_args()
    run(a.lattice, a.family, a.device, a.cid, a.chunk, a.start, a.shots, a.time_limit)


if __name__ == "__main__":
    main()
