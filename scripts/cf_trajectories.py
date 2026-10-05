#!/usr/bin/env python3
"""
prompts/28 Part A (gate CF_traj): Pauli-error trajectory decomposition of the A6 gate-only H2-2 channel on a
frozen 2x3 Quantinuum-native circuit.

The A6 channel (`quantinuum_submit.A6_NOISE`, frozen) as qiskit-aer defines it:
  depolarizing_error(p2, 2) on every rzz  = identity with probability 1 - 15/16 p2, each of the 15 non-identity
                                           two-qubit Paulis with p2/16
  depolarizing_error(p1, 1) on every rx/ry = identity with 1 - 3/4 p1, each of X, Y, Z with p1/4
  rz noiseless (virtual); ReadoutError [[1-p10, p10], [p01, 1-p01]] on every measurement.
(qiskit_aer/noise/errors/standard_errors.py depolarizing_error: prob_iden = 1 - param / max_param with
max_param = 4^n / (4^n - 1), prob_pauli = param / 4^n.)  The error is applied AFTER the gate it is attached
to; `aer_error_placement_check` establishes this on the installed Aer and its result is written into every
chunk file.

A trajectory = one draw of the error events: Bernoulli(15/16 p2) per rzz site, Bernoulli(3/4 p1) per rx/ry
site (one physical PhasedX each: pytket_to_ir writes PhasedX as rz, rx, rz and the error attaches to the
rx), the Pauli uniform over the channel's non-identity set.  The all-identity draw (probability
g0 = (1 - 15/16 p2)^n_zz (1 - 3/4 p1)^n_1q) is rejected without simulation: only FAULTY trajectories are
simulated.  For each, the drawn Paulis are inserted as x / y / z IR gates directly after their gate, the
exact statevector is computed (Aer statevector, double precision) and the readout flips are applied exactly
to the 2^n probability vector (per-qubit convolution, n passes).  Every sector probability of every
trajectory is recorded, so the averages carry no shot noise.

Speed: the ideal state is stored at `--checkpoints` evenly spaced gate positions; a trajectory starts from
the last checkpoint at or before its first error (Aer `set_statevector`), which is exact (the first
trajectory of each chunk is cross-checked against a from-scratch evaluation).

Runs in the isolated venv (pytket is needed to read the frozen circuit JSON):
  V=~/.local/share/su2qc-quantinuum/venv/bin/python
  $V scripts/cf_trajectories.py --timing-pilot --id B0_ref25_k1
  $V scripts/cf_trajectories.py --id B0_ref25_k1 --K 240 --seed 101 --chunk 0 --workers 6
  $V scripts/cf_trajectories.py --id B0_ref25_k1 --K 120 --seed 401 --chunk 0 --channel xx
  $V scripts/cf_trajectories.py --combine --id B0_ref25_k1 [--channel xx]
  $V scripts/cf_trajectories.py --control-xx --id B0_ref25_k1 --shots 280 --seed 23 --threads 6
Outputs: data/cf_trajectories/<id>[__xx]/chunk<n>.json (raw data, never overwritten), combined.json,
data/cf_trajectories/control_xx/ (A4 counts, the format of the A6 dry-run counts), timing_A0.json.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import multiprocessing as mp
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

OUT = os.path.join(ROOT, "data", "cf_trajectories")
CIRC = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
G2 = 4.0
TAIL_P_MIN = 1e-3                 # prompts/28: T_c = {s : p_c(s) >= 1e-3, s != ref}
BENIGN_TV = 1e-3                  # prompts/28 A3: benign = TV distance < 1e-3 from the ideal
PAULIS_2Q = [a + b for a in "IXYZ" for b in "IXYZ" if a + b != "II"]   # label[0] acts on qs[0]
PAULIS_1Q = ["X", "Y", "Z"]
CHANNELS = {
    # name: (2q labels, 1q labels); event probabilities are those of the A6 depolarizing channels
    "depol": (PAULIS_2Q, PAULIS_1Q),
    "xx": (["XX"], ["X"]),        # A4 counting control: bit flips only, same event probabilities
}
SCRATCH_ENV = "CF_TRAJ_SCRATCH"   # where the checkpoint memmap goes (default: data/cf_trajectories/.ckpt)


# =========================================================================== pure helpers (tested)
def event_probabilities(p2: float, p1: float) -> tuple:
    """(e2, e1): the probability that Aer's depolarizing_error(p, n) applies a NON-identity Pauli."""
    return 15.0 / 16.0 * float(p2), 0.75 * float(p1)


def noise_sites(ir: list) -> list:
    """[(gate position, '2q' | '1q', qubits)] for every gate that carries an A6 error (rzz; rx / ry)."""
    out = []
    for pos, (name, qs, _par) in enumerate(ir):
        if name == "rzz":
            out.append((pos, "2q", list(qs)))
        elif name in ("rx", "ry"):
            out.append((pos, "1q", list(qs)))
    return out


def no_error_probability(n_2q: int, n_1q: int, p2: float, p1: float) -> float:
    e2, e1 = event_probabilities(p2, p1)
    return (1.0 - e2) ** int(n_2q) * (1.0 - e1) ** int(n_1q)


def readout_survival(ref_bits, p10: float, p01: float) -> float:
    ones = int(sum(int(b) for b in ref_bits))
    return (1.0 - p10) ** (len(ref_bits) - ones) * (1.0 - p01) ** ones


def draw_trajectories(rng, sites: list, K: int, p2: float, p1: float, channel: str = "depol"):
    """K faulty trajectories (all-identity draws rejected).  Returns (list of event lists, n_draws).
    An event is [site index, gate position, '2q'|'1q', qubits, Pauli label]."""
    lab2, lab1 = CHANNELS[channel]
    e2, e1 = event_probabilities(p2, p1)
    probs = np.array([e2 if kind == "2q" else e1 for _pos, kind, _qs in sites], float)
    out, draws = [], 0
    while len(out) < K:
        draws += 1
        hit = np.nonzero(rng.random(len(probs)) < probs)[0]
        if len(hit) == 0:
            continue
        ev = []
        for i in hit:
            pos, kind, qs = sites[int(i)]
            labs = lab2 if kind == "2q" else lab1
            ev.append([int(i), int(pos), kind, list(qs), labs[int(rng.integers(len(labs)))]])
        out.append(ev)
    return out, draws


def is_z_type(events: list) -> bool:
    """All Paulis Z-type: Z on 1q sites; ZI, IZ, ZZ on 2q sites."""
    return all(set(ev[4]) <= {"I", "Z"} for ev in events)


def insert_paulis(ir: list, events: list, start: int = 0) -> list:
    """The IR from gate `start` on, with the drawn Paulis inserted directly after their gates."""
    by_pos = {}
    for ev in events:
        by_pos.setdefault(int(ev[1]), []).append(ev)
    out = []
    for pos in range(start, len(ir)):
        out.append(ir[pos])
        for ev in by_pos.get(pos, ()):
            for q, c in zip(ev[3], ev[4]):
                if c != "I":
                    out.append((c.lower(), [int(q)], None))
    if any(int(ev[1]) < start for ev in events):
        raise ValueError("an event lies before the start position")
    return out


def readout_convolve(p: np.ndarray, n: int, p10: float, p01: float) -> np.ndarray:
    """Exact readout channel on a 2^n probability vector (qubit k = bit k of the index): per qubit,
    P(read 1 | 0) = p10, P(read 0 | 1) = p01 (Aer ReadoutError [[1-p10, p10], [p01, 1-p01]])."""
    q = np.asarray(p, float).copy()
    for k in range(n):
        v = q.reshape(2 ** (n - 1 - k), 2, 2 ** k)
        a0, a1 = v[:, 0, :].copy(), v[:, 1, :].copy()
        v[:, 0, :] = (1.0 - p10) * a0 + p01 * a1
        v[:, 1, :] = p10 * a0 + (1.0 - p01) * a1
    return q


def hamming_distance_table(n: int, ref_int: int) -> np.ndarray:
    idx = np.arange(2 ** n, dtype=np.int64) ^ int(ref_int)
    d = np.zeros(2 ** n, dtype=np.uint8)
    for k in range(n):
        d += ((idx >> k) & 1).astype(np.uint8)
    return d


def tv_distance(p_sector: np.ndarray, p_ideal: np.ndarray) -> float:
    """Total-variation distance of the sector-normalised p from the (sector-normalised) ideal."""
    m = float(np.sum(p_sector))
    if m <= 0.0:
        return 1.0
    return 0.5 * float(np.sum(np.abs(np.asarray(p_sector) / m - np.asarray(p_ideal))))


def git_commit():
    try:
        c = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                    stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "scripts", "src"], cwd=ROOT).returncode != 0
        return c, bool(dirty)
    except Exception:
        return "n/a", None


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


# =========================================================================== Aer evolution
def aer_sim(threads: int = 1):
    from qiskit_aer import AerSimulator

    return AerSimulator(method="statevector", precision="double", fusion_enable=True,
                        max_parallel_threads=int(threads))


def evolve(sv0, gates: list, n: int, sim) -> np.ndarray:
    """|psi> = gates |sv0> (sv0 None = |0...0>), Aer statevector, double precision."""
    from qiskit import QuantumCircuit
    import qiskit_aer  # noqa: F401  (registers QuantumCircuit.set_statevector)

    from skqd import circuits_qiskit as cq

    qc = QuantumCircuit(n)
    if sv0 is not None:
        qc.set_statevector(np.ascontiguousarray(sv0))
    qc.compose(cq.ir_to_qiskit(gates, n, measure=False), inplace=True)
    qc.save_statevector()
    res = sim.run(qc, shots=1).result()
    return np.asarray(res.data(0)["statevector"].data)


def aer_error_placement_check() -> dict:
    """Does Aer apply a gate's QuantumError after the gate?  rx(pi/2) with a probability-1 Z error:
    after -> Z Rx|0> = (|0> + i|1>)/sqrt2; before -> Rx Z|0> = (|0> - i|1>)/sqrt2."""
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, pauli_error

    nm = NoiseModel(basis_gates=["rz", "rx", "ry", "rzz"])
    nm.add_all_qubit_quantum_error(pauli_error([("Z", 1.0)]), ["rx"])
    qc = QuantumCircuit(1)
    qc.rx(math.pi / 2, 0)
    qc.save_statevector()
    sv = np.asarray(AerSimulator(method="statevector", noise_model=nm, seed_simulator=1)
                    .run(qc, shots=1).result().data(0)["statevector"].data)
    after = np.array([1.0, 1j]) / math.sqrt(2)
    before = np.array([1.0, -1j]) / math.sqrt(2)
    ov_a, ov_b = abs(np.vdot(after, sv)) ** 2, abs(np.vdot(before, sv)) ** 2
    return {"test": "1 qubit: rx(pi/2) with pauli_error([('Z', 1.0)]) attached to rx; save_statevector",
            "overlap_with_error_after_gate": float(ov_a), "overlap_with_error_before_gate": float(ov_b),
            "error_applied_after_gate": bool(ov_a > 1 - 1e-12 and ov_b < 1e-12),
            "source_text": ("no sentence on the placement found in the installed qiskit-aer 0.17.2 Python "
                            "sources (noise/noise_model.py, noise/errors/*.py); the only related sentence is "
                            "qiskit_aer/noise/passes/local_noise_pass.py: '\"append\": add the return of the "
                            "callable after the instruction.' (a different mechanism).  The convention is "
                            "therefore established by this measurement on the installed Aer.")}


# =========================================================================== circuit context
def load_circuit_ir(cid: str):
    from skqd import quantinuum_native as qn
    from quantinuum_submit import load_frozen, load_manifest

    man = load_manifest(CIRC, cid)
    ir, n, qmap = qn.pytket_to_ir(load_frozen(CIRC, man))
    if qmap != {q: q for q in range(n)}:
        raise SystemExit(f"{cid}: measurement map is not q[k] -> c[k]")
    return man, ir, n


def sector_context(man: dict) -> dict:
    """Sector integers (Model(3).reference order), the reference position, S99 / S999 positions."""
    from skqd.exact import Model
    from skqd.reference_sim import CodewordEmbedding

    M = Model(3)
    emb = CodewordEmbedding(M)
    R = M.reference(G2, int(man["twoB"]), k=4)
    idx = np.asarray(R.indices, dtype=int)
    ints = np.asarray(emb.ints[idx], dtype=np.int64)
    prob = np.abs(np.asarray(R.ground)) ** 2
    order = np.argsort(-prob, kind="stable")
    ref_int = int(man["reference_int"])
    pos = np.nonzero(ints == ref_int)[0]
    if len(pos) != 1:
        raise SystemExit(f"{man['id']}: the reference string is not a sector state")
    return {"ints": ints, "ref_pos": int(pos[0]), "ref_int": ref_int,
            "S99": [int(i) for i in order[:int(R.support99)]],
            "S999": [int(i) for i in order[:int(R.support999)]],
            "ground_prob": prob, "dim": int(R.dim), "E0": float(R.energies[0])}


# =========================================================================== worker
_W = {}


def _init_worker(ctx):
    _W.clear()
    _W.update(ctx)
    _W["ckpt"] = np.load(ctx["ckpt_path"], mmap_mode="r")
    _W["dist"] = hamming_distance_table(ctx["n"], ctx["ref_int"])
    _W["sim"] = aer_sim(1)


def trajectory_record(sv, events, ctx, dist) -> dict:
    n = ctx["n"]
    ints = ctx["ints"]
    p_pre = np.abs(sv) ** 2
    p_post = readout_convolve(p_pre, n, ctx["p10"], ctx["p01"])
    sec_pre, sec_post = p_pre[ints], p_post[ints]
    pc = ctx["p_c"]
    tail = ctx["tail_pos"]
    ref = ctx["ref_int"]
    in_sector = np.zeros(2 ** n, bool)
    in_sector[ints] = True
    return {
        "events": events, "n_2q": int(sum(e[2] == "2q" for e in events)),
        "n_1q": int(sum(e[2] == "1q" for e in events)), "z_only": bool(is_z_type(events)),
        "sector_mass_pre": float(sec_pre.sum()), "sector_mass_post": float(sec_post.sum()),
        "p_ref_pre": float(p_pre[ref]), "p_ref_post": float(p_post[ref]),
        "tv_pre": tv_distance(sec_pre, pc), "tv_post": tv_distance(sec_post, pc),
        "tail_pre": float(sec_pre[tail].sum()), "tail_post": float(sec_post[tail].sum()),
        "p_S999_post": [float(x) for x in sec_post[ctx["S999"]]],
        "p_sector_post": [float(x) for x in sec_post],
        "hamming_post": [float(x) for x in np.bincount(dist, weights=p_post, minlength=n + 1)],
        "hamming_post_sector": [float(x) for x in np.bincount(dist[in_sector], weights=p_post[in_sector],
                                                              minlength=n + 1)],
    }


def run_one(task):
    i, events = task
    t0 = time.time()
    ir, n, bounds = _W["ir"], _W["n"], _W["bounds"]
    first = min(int(e[1]) for e in events)
    c = int(np.searchsorted(bounds, first + 1, side="right") - 1)     # largest bound <= first + 1
    start = int(bounds[c])
    gates = insert_paulis(ir, events, start)
    sv0 = None if start == 0 else np.array(_W["ckpt"][c])
    sv = evolve(sv0, gates, n, _W["sim"])
    rec = trajectory_record(sv, events, _W, _W["dist"])
    rec.update({"index": int(i), "first_event_gate_pos": first, "checkpoint": c, "start_gate": start,
                "wall_s": time.time() - t0})
    if _W.get("crosscheck_index") == i:
        full = evolve(None, insert_paulis(ir, events, 0), n, _W["sim"])
        rec["crosscheck_from_scratch_max_abs_dprob"] = float(np.max(np.abs(np.abs(full) ** 2 - np.abs(sv) ** 2)))
    return rec


# =========================================================================== commands
def arm_dir(cid, channel, root=None):
    return os.path.join(root or OUT, cid if channel == "depol" else f"{cid}__{channel}")


def build_checkpoints(ir, n, n_ckpt, threads, path):
    """States after gates[0:b] for b in bounds (b_0 = 0 -> |0...0>), as a memmapped .npy."""
    bounds = np.unique(np.linspace(0, len(ir), n_ckpt + 1).astype(int)[:-1])
    sim = aer_sim(threads)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    arr = np.lib.format.open_memmap(path, mode="w+", dtype=np.complex128, shape=(len(bounds), 2 ** n))
    sv = np.zeros(2 ** n, complex)
    sv[0] = 1.0
    arr[0] = sv
    for j in range(1, len(bounds)):
        sv = evolve(sv, ir[bounds[j - 1]:bounds[j]], n, sim)
        arr[j] = sv
    final = evolve(sv, ir[bounds[-1]:], n, sim)
    arr.flush()
    del arr
    return bounds, final


def cmd_chunk(args):
    from quantinuum_submit import A6_NOISE

    t_start = time.time()
    outdir = arm_dir(args.id, args.channel, args.out_root)
    path = os.path.join(outdir, f"chunk{args.chunk}.json")
    if os.path.exists(path):
        raise SystemExit(f"{path} exists: chunk files are raw data and are never overwritten")
    commit, dirty = git_commit()
    man, ir, n = load_circuit_ir(args.id)
    sites = noise_sites(ir)
    n2 = sum(s[1] == "2q" for s in sites)
    n1 = sum(s[1] == "1q" for s in sites)
    c = man["counts"]
    if n2 != int(c["n_zz"]) or n1 != int(c["n_phasedx"]):
        raise SystemExit(f"{args.id}: noise sites {n2} rzz / {n1} rx,ry differ from the manifest "
                         f"{c['n_zz']} ZZ / {c['n_phasedx']} PhasedX")
    p2, p1 = A6_NOISE["depolarizing_2q_rzz"], A6_NOISE["depolarizing_1q_rx_ry"]
    p10, p01 = A6_NOISE["readout_p1_given_0"], A6_NOISE["readout_p0_given_1"]
    sec = sector_context(man)
    placement = aer_error_placement_check()
    if not placement["error_applied_after_gate"]:
        raise SystemExit(f"Aer error placement is not 'after the gate': {placement}")
    scratch = os.environ.get(SCRATCH_ENV, os.path.join(OUT, ".ckpt"))
    ckpt_path = os.path.join(scratch, f"{args.id}_ckpt.npy")
    t0 = time.time()
    bounds, final = build_checkpoints(ir, n, args.checkpoints, args.workers, ckpt_path)
    t_ckpt = time.time() - t0
    p_ideal = np.abs(final) ** 2
    p_ideal_sector = p_ideal[sec["ints"]]
    p_c = p_ideal_sector / p_ideal_sector.sum()
    # cross-check against the verify stage's frozen-circuit distribution
    vpath = os.path.join(ROOT, "data", "quantinuum", "q0p_stages", "verify.json")
    with open(vpath) as fh:
        v_ps = np.asarray(json.load(fh)["per_circuit"][args.id]["p_sector"], float)
    verify_diff = float(np.max(np.abs(v_ps - p_ideal_sector)))
    tail_pos = [int(i) for i in np.nonzero(p_c >= TAIL_P_MIN)[0] if int(i) != sec["ref_pos"]]
    rng = np.random.default_rng(int(args.seed))
    trajs, draws = draw_trajectories(rng, sites, int(args.K), p2, p1, args.channel)
    ctx = {"ir": ir, "n": n, "bounds": bounds, "ckpt_path": ckpt_path, "ints": sec["ints"],
           "ref_int": sec["ref_int"], "p10": p10, "p01": p01, "p_c": p_c, "tail_pos": tail_pos,
           "S999": sec["S999"], "crosscheck_index": 0}
    dist = hamming_distance_table(n, sec["ref_int"])
    p_ideal_post = readout_convolve(p_ideal, n, p10, p01)
    ideal = {"p_c": [float(x) for x in p_c], "sector_mass": float(p_ideal_sector.sum()),
             "p_ref": float(p_ideal[sec["ref_int"]]),
             "p_ref_post_readout": float(p_ideal_post[sec["ref_int"]]),
             "p_sector_post_readout": [float(x) for x in p_ideal_post[sec["ints"]]],
             "hamming_post_readout": [float(x) for x in np.bincount(dist, weights=p_ideal_post, minlength=n + 1)],
             "p_reference_manifest": float(man["p_reference"]),
             "p_ref_vs_manifest_abs": abs(float(p_ideal[sec["ref_int"]]) - float(man["p_reference"])),
             "p_sector_vs_verify_json_max_abs": verify_diff}
    print(f"{args.id} [{args.channel}] chunk {args.chunk}: checkpoints {len(bounds)} in {t_ckpt:.0f} s, "
          f"{len(trajs)} trajectories from {draws} draws, verify diff {verify_diff:.1e}", flush=True)
    recs = []
    t1 = time.time()
    with mp.get_context("spawn").Pool(int(args.workers), initializer=_init_worker, initargs=(ctx,)) as pool:
        for rec in pool.imap_unordered(run_one, list(enumerate(trajs)), chunksize=1):
            recs.append(rec)
            if len(recs) % 20 == 0 or len(recs) == len(trajs):
                el = time.time() - t1
                print(f"  {len(recs)}/{len(trajs)}  {el:.0f} s  ({el / len(recs):.2f} s per trajectory)", flush=True)
    recs.sort(key=lambda r: r["index"])
    wall = time.time() - t_start
    e2, e1 = event_probabilities(p2, p1)
    out = {
        "produced_by": "scripts/cf_trajectories.py", "prompt": "prompts/28 Part A (A1/A2)",
        "id": args.id, "channel": args.channel, "channel_labels": {"2q": CHANNELS[args.channel][0],
                                                                    "1q": CHANNELS[args.channel][1]},
        "pauli_label_convention": "2q label[0] acts on the rzz's first IR qubit, label[1] on the second",
        "chunk": int(args.chunk), "seed": int(args.seed), "K": int(args.K), "git_commit": commit,
        "git_dirty_scripts_src": dirty, "created": now(), "workers": int(args.workers),
        "threads_per_worker": 1, "checkpoints": {"n": int(len(bounds)), "bounds": [int(b) for b in bounds],
                                                 "build_s": t_ckpt},
        "noise": A6_NOISE, "event_probability_2q": e2, "event_probability_1q": e1,
        "n_sites_2q": int(n2), "n_sites_1q": int(n1), "n_gates_ir": len(ir), "n_qubits": int(n),
        "no_error_probability_g0": no_error_probability(n2, n1, p2, p1),
        "readout_survival_reference": readout_survival(man["reference_bits"], p10, p01),
        "n_draws": int(draws), "n_rejected_all_identity": int(draws - len(trajs)),
        "aer_error_placement_check": placement,
        "sector": {"twoB": int(man["twoB"]), "dim": sec["dim"], "ints": [int(x) for x in sec["ints"]],
                   "ref_pos": sec["ref_pos"], "ref_int": sec["ref_int"], "S99": sec["S99"],
                   "S999": sec["S999"], "tail_pos": tail_pos, "tail_p_min": TAIL_P_MIN,
                   "positions": "Model(3).reference(4.0, twoB).indices order (skqd.exact)"},
        "ideal": ideal, "wall_s": wall, "trajectory_wall_s": time.time() - t1,
        "trajectories": recs,
    }
    os.makedirs(outdir, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(out, fh)
    os.replace(tmp, path)
    try:
        os.remove(ckpt_path)
    except OSError:
        pass
    print(f"wrote {os.path.relpath(path, ROOT)} ({wall:.0f} s)")
    return 0


SCALARS = ("n_2q", "n_1q", "z_only", "sector_mass_pre", "sector_mass_post", "p_ref_pre", "p_ref_post",
           "tv_pre", "tv_post", "tail_pre", "tail_post", "first_event_gate_pos", "wall_s")


def load_chunks(cid, channel="depol"):
    files = sorted(glob.glob(os.path.join(arm_dir(cid, channel), "chunk*.json")),
                   key=lambda p: int(os.path.basename(p)[5:-5]))
    out = []
    for f in files:
        with open(f) as fh:
            out.append((f, json.load(fh)))
    return out


def cmd_combine(args):
    chunks = load_chunks(args.id, args.channel)
    if not chunks:
        raise SystemExit("no chunk files")
    base = chunks[0][1]
    seeds = [c["seed"] for _f, c in chunks]
    if len(set(seeds)) != len(seeds):
        raise SystemExit(f"duplicate seeds {seeds}")
    for f, c in chunks[1:]:
        for key in ("id", "channel", "n_sites_2q", "n_sites_1q", "no_error_probability_g0"):
            if c[key] != base[key]:
                raise SystemExit(f"{f}: {key} differs from chunk 0")
        if max(abs(a - b) for a, b in zip(c["ideal"]["p_c"], base["ideal"]["p_c"])) > 1e-12:
            raise SystemExit(f"{f}: the ideal distribution differs from chunk 0 by > 1e-12")
    trajs = [t for _f, c in chunks for t in c["trajectories"]]
    P = np.array([t["p_sector_post"] for t in trajs])
    comb = {k: base[k] for k in ("produced_by", "prompt", "id", "channel", "channel_labels", "noise",
                                 "event_probability_2q", "event_probability_1q", "n_sites_2q", "n_sites_1q",
                                 "n_qubits", "no_error_probability_g0", "readout_survival_reference",
                                 "sector", "ideal", "aer_error_placement_check")}
    comb.update({
        "combined": now(), "K_total": len(trajs),
        "chunks": [{"file": os.path.relpath(f, ROOT), "chunk": c["chunk"], "seed": c["seed"], "K": c["K"],
                    "git_commit": c["git_commit"], "git_dirty_scripts_src": c["git_dirty_scripts_src"],
                    "created": c["created"], "wall_s": c["wall_s"], "workers": c["workers"],
                    "n_draws": c["n_draws"], "n_rejected_all_identity": c["n_rejected_all_identity"],
                    "crosscheck_from_scratch_max_abs_dprob": next(
                        (t["crosscheck_from_scratch_max_abs_dprob"] for t in c["trajectories"]
                         if "crosscheck_from_scratch_max_abs_dprob" in t), None)}
                   for f, c in chunks],
        "scalars": {k: [t[k] for t in trajs] for k in SCALARS},
        "mean_p_sector_post": [float(x) for x in P.mean(axis=0)],
        "std_p_sector_post": [float(x) for x in P.std(axis=0, ddof=1)] if len(trajs) > 1 else None,
        "mean_hamming_post": [float(x) for x in np.mean([t["hamming_post"] for t in trajs], axis=0)],
        "mean_hamming_post_sector": [float(x) for x in np.mean([t["hamming_post_sector"] for t in trajs], axis=0)],
    })
    path = os.path.join(arm_dir(args.id, args.channel), "combined.json")
    with open(path, "w") as fh:
        json.dump(comb, fh)
    print(f"wrote {os.path.relpath(path, ROOT)}: K = {len(trajs)} from {len(chunks)} chunk(s), seeds {seeds}")
    return 0


def _timed_sv(task):
    import pickle

    path, threads = task
    with open(path, "rb") as fh:
        ir, n = pickle.load(fh)
    from skqd import circuits_qiskit as cq

    t0 = time.time()
    cq.statevector_aer(ir, n, threads=threads)
    return time.time() - t0


def cmd_timing(args):
    """A0: one statevector_aer of the circuit on 1 thread, then `workers` of them in parallel."""
    import pickle

    man, ir, n = load_circuit_ir(args.id)
    scratch = os.environ.get(SCRATCH_ENV, os.path.join(OUT, ".ckpt"))
    os.makedirs(scratch, exist_ok=True)
    pk = os.path.join(scratch, f"{args.id}_ir.pkl")
    with open(pk, "wb") as fh:
        pickle.dump((ir, n), fh)
    single = _timed_sv((pk, 1))
    t0 = time.time()
    with mp.get_context("spawn").Pool(int(args.workers)) as pool:
        par = pool.map(_timed_sv, [(pk, 1)] * int(args.workers))
    par_wall = time.time() - t0
    os.remove(pk)
    rec = {"produced_by": "scripts/cf_trajectories.py --timing-pilot", "id": args.id, "created": now(),
           "git_commit": git_commit()[0], "engine": "circuits_qiskit.statevector_aer (double, fusion on)",
           "n_gates_ir": len(ir), "single_thread_s": single, "workers": int(args.workers),
           "parallel_per_statevector_s": par, "parallel_wall_s": par_wall,
           "throughput_s_per_statevector": par_wall / int(args.workers),
           "planner_reading_s_per_statevector_per_core": 903.5106384754181 * 6 / 176,
           "planner_reading_source": "verify.json runtime_s 903.5 s for 176 statevectors on 6 workers"}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "timing_A0.json")
    if os.path.exists(path):
        raise SystemExit(f"{path} exists (raw record)")
    with open(path, "w") as fh:
        json.dump(rec, fh, indent=1)
    print(json.dumps(rec, indent=1))
    return 0


def xx_noise_model(p2, p1, p10, p01):
    """A4: the A6 event probabilities with bit-flip Paulis only; readout unchanged."""
    from qiskit_aer.noise import NoiseModel, ReadoutError, pauli_error

    e2, e1 = event_probabilities(p2, p1)
    nm = NoiseModel(basis_gates=["rz", "rx", "ry", "rzz"])
    nm.add_all_qubit_quantum_error(pauli_error([("XX", e2), ("II", 1 - e2)]), ["rzz"])
    nm.add_all_qubit_quantum_error(pauli_error([("X", e1), ("I", 1 - e1)]), ["rx", "ry"])
    nm.add_all_qubit_readout_error(ReadoutError([[1 - p10, p10], [p01, 1 - p01]]))
    return nm


def cmd_control_xx(args):
    """A4: the A6 sampler path (quantinuum_submit.run_aer) with the bit-flip-only channel."""
    import quantinuum_submit as qs
    from skqd import quantinuum_native as qn

    outdir = os.path.join(OUT, "control_xx")
    if os.path.exists(os.path.join(outdir, "session.json")):
        raise SystemExit(f"{outdir} holds a session: raw data are never overwritten")
    A = qs.A6_NOISE
    p2, p1 = A["depolarizing_2q_rzz"], A["depolarizing_1q_rx_ry"]
    p10, p01 = A["readout_p1_given_0"], A["readout_p0_given_1"]
    e2, e1 = event_probabilities(p2, p1)
    man = qs.load_manifest(CIRC, args.id)
    job = {"circuit_id": args.id, "chunk": 0, "n_shots": int(args.shots), "device_name": "local Aer (A4 control)",
           "aer_seed": int(args.seed), "job_id": None, "submitted": None, "backend_config": None}
    session = {"created": now(), "script": "scripts/cf_trajectories.py --control-xx", "phase": "A4 counting control",
               "dry_run": True, "executed_on": "local AerSimulator (statevector, CPU) via quantinuum_submit.run_aer",
               "noise_model": {"source": "quantinuum_submit.A6_NOISE event probabilities, bit flips only",
                               "rzz": f"pauli_error([('XX', {e2!r}), ('II', 1 - e2)])",
                               "rx_ry": f"pauli_error([('X', {e1!r}), ('I', 1 - e1)])",
                               "readout": f"ReadoutError([[1 - {p10}, {p10}], [{p01}, 1 - {p01}]])",
                               "A6_NOISE": A},
               "git_commit": git_commit()[0], "jobs": [job], "versions": qn.versions()}
    os.makedirs(outdir, exist_ok=True)
    qs.save_session(outdir, session)
    circ = qs.load_frozen(CIRC, man)
    t0 = time.time()
    res = qs.run_aer({args.id: circ}, [job], args.threads, noise_model=xx_noise_model(p2, p1, p10, p01))
    counts, sec = res[(args.id, 0)]
    job["status"] = "COMPLETED (local Aer)"
    job["aer_seconds_share"] = sec
    qs.write_counts(outdir, session, job, man, counts, "qiskit_aer get_counts() keys (qubit 0 rightmost) -> bit tuples")
    session["sampling_wall_s"] = time.time() - t0
    session["completed"] = now()
    qs.save_session(outdir, session)
    hits = sum(v for b, v in counts.items() if int(sum(int(x) << k for k, x in enumerate(b))) == int(man["reference_int"]))
    print(f"A4 control: {hits} reference hits in {args.shots} shots ({session['sampling_wall_s']:.0f} s)")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(description="prompts/28 A0/A1/A4: Pauli-trajectory decomposition of the A6 channel")
    ap.add_argument("--id", default="B0_ref25_k1")
    ap.add_argument("--K", type=int, default=240)
    ap.add_argument("--seed", type=int, default=101)
    ap.add_argument("--chunk", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--channel", choices=sorted(CHANNELS), default="depol")
    ap.add_argument("--checkpoints", type=int, default=48)
    ap.add_argument("--combine", action="store_true")
    ap.add_argument("--timing-pilot", action="store_true")
    ap.add_argument("--control-xx", action="store_true")
    ap.add_argument("--shots", type=int, default=280)
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--out-root", default=None, help="smoke runs only: write the chunk under this root instead")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.timing_pilot:
        return cmd_timing(args)
    if args.combine:
        return cmd_combine(args)
    if args.control_xx:
        return cmd_control_xx(args)
    return cmd_chunk(args)


if __name__ == "__main__":
    sys.exit(main())
