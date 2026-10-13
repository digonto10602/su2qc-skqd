#!/usr/bin/env python3
"""
prompts/35 tiers T2-T6 of the Quantinuum test of every SKQD circuit (2x2, 2x3, 2x4), and the deferred GPU
token QV_2x4.  One driver, one tier per invocation; every invocation writes its fragment under
data/quantinuum/lattice_tests/ and re-assembles the gate JSON (validation/<GATE>.json, `skqd.report.GateResult`)
and the generated report (reports/<GATE>.md).  0 QPU s, 0 HQC, no network.

  --tier export      (su2qc-quantinuum venv: pytket)  the frozen native circuits -> QPY v13 bundles
                     (pytket_to_ir -> ir_to_qiskit, measure q[k] -> c[k]) data/quantinuum/circuits_2x<L>_qpy/
  --tier noiseless   (coding: Aer CPU)  T2 at 2x2: 20000 shots per circuit, per-state 5 sigma test, the f = 1 SKQD
                     reference at the H0_2x2 plan of record                                   -> QN_2x2 (N1, N2)
  --tier noise       (coding)  T3 at 2x2: --part rate | fcells | por (Quantinuum scenarios E1-E7)  -> QN_2x2 (N3-N5)
                     (venv)    T3 at 2x4: analytic f0 and gate-only f per circuit / scenario       -> QN_2x4 (A1, A2)
  --tier pecos       (su2qc-pecos venv)  T4: pytket-quantinuum H2-1LE local emulator, noiseless state vector
                     2x2 (--part rate | circuit --only <id> | probe | assemble)              -> QEMU_2x2 (M1-M3)
                     2x3 (--part smoke: engines.run of token C3_LE with a dry CI context)    -> QEMU_2x3_laptop_smoke
                     2x4 (infeasible, the numbers)                                           -> QEMU_2x4
  --tier hugr        (su2qc-pecos venv)  T6: Guppy load_pytket -> HUGR package -> Selene Quest (IdealErrorModel)
                     2x2 all 28 -> QH_2x2 (H1-H4); 2x3 the two k = 1 f-cell circuits -> QH_2x3; 2x4 -> QH_2x4
  --tier gpu-verify  (CI env skqd: qiskit 1.4.3 / Aer 0.15.1, GPU)  token QV_2x4: Aer GPU statevector of the 15
                     native k = 1 2x4 circuits vs the exact coarse states; noiseless per-state test at 6250 shots.
                     `--lattice 2 --dry-run` is the laptop CPU path check (validation/dryrun/QV_2x4.json).

Seeds: T2 35 000 000 + 1000 c + chunk (prompts/35 3.4); T4 35 100 000 + c (3.6); T3 f-cells 35 200 000 +
1000 s + c, plan-of-record 35 300 000 + 1000 s + c; QV_2x4 35 400 000 + c; T6 Selene 35 500 000 + c
(executor's rules, recorded in every JSON).
"""
import argparse
import glob
import gzip
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

PROMPT = "prompts/35_quantinuum_all_circuits_test.md"
G2 = 4.0
FRAG = os.path.join(ROOT, "data", "quantinuum", "lattice_tests")
H0_PLAN = os.path.join(ROOT, "data", "hardware", "H0_2x2_prep", "shot_plan.json")
SEED_T2, SEED_T4, SEED_FC, SEED_POR, SEED_QV, SEED_T6 = (35_000_000, 35_100_000, 35_200_000, 35_300_000,
                                                         35_400_000, 35_500_000)
SEED_RULES = {"T2": "35 000 000 + 1000 c + chunk (c = index in the sorted id list)",
              "T3_fcells": "35 200 000 + 1000 s + c (s = scenario index in SCENARIOS, c = index in the sorted ids)",
              "T3_plan_of_record": "35 300 000 + 1000 s + c", "T3_rate": "44 200 000 (one call per scenario)",
              "T4": "35 100 000 + c", "T6": "35 500 000 + c", "QV_2x4": "35 400 000 + c"}
N_T2 = 20000
N_FCELL = 2000
N_SIGMA, P_MIN = 5.0, 1e-3
SCENARIOS = ("E1", "E2", "E3", "E4", "E5a", "E5b", "E5c", "E6a", "E6b", "E6c", "E7_0.10_lat")
POR_ORDER = ("E1", "E3", "E4", "E5b", "E7_0.10_lat", "E2", "E6a", "E6b", "E6c", "E5a", "E5c")
RATE_CIRCUIT = "B0_ref06_k4"
RATE_SHOTS = 500
CAP_T3_S = 8 * 3600.0
CAP_T4_S = 4 * 3600.0
QV_SHOTS = 6250
VAR_TOL = 1e-9
RECALL_MIN = 0.9
CODING_PY = "/home/digimonk/anaconda3/envs/coding/bin/python"


# --------------------------------------------------------------------------- small helpers
def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def load_json(p):
    with open(p) as fh:
        return json.load(fh)


def rel(p):
    return os.path.relpath(p, ROOT)


def sha256_text(t):
    return hashlib.sha256(t.encode() if isinstance(t, str) else t).hexdigest()


def save_frag(gate, name, d):
    os.makedirs(os.path.join(FRAG, gate), exist_ok=True)
    p = os.path.join(FRAG, gate, name + ".json")
    d = dict(d, fragment=name, created=now())
    from skqd.report import _jsonable
    with open(p + ".tmp", "w") as fh:
        json.dump(_jsonable(d), fh, indent=1)
    os.replace(p + ".tmp", p)
    return p


def frag(gate, name):
    p = os.path.join(FRAG, gate, name + ".json")
    return load_json(p) if os.path.exists(p) else None


def frags(gate, prefix):
    out = {}
    for p in sorted(glob.glob(os.path.join(FRAG, gate, prefix + "*.json"))):
        out[os.path.basename(p)[:-5]] = load_json(p)
    return out


def circ_dir(lat):
    return os.path.join(ROOT, "data", "quantinuum", f"circuits_2x{lat}")


def qpy_dir(lat):
    return os.path.join(ROOT, "data", "quantinuum", f"circuits_2x{lat}_qpy")


def family(lat):
    d = circ_dir(lat)
    idx = load_json(os.path.join(d, "index.json"))
    mans = {c: load_json(os.path.join(d, c + ".manifest.json")) for c in idx["circuits"]}
    cals = {c: load_json(os.path.join(d, c + ".manifest.json")) for c in idx.get("calibration", [])}
    return idx, mans, cals


def read_frozen(lat, name):
    p = os.path.join(circ_dir(lat), name)
    if p.endswith(".gz"):
        with gzip.open(p, "rb") as fh:
            return fh.read().decode()
    with open(p) as fh:
        return fh.read()


def versions(pkgs=("numpy", "scipy", "qiskit", "qiskit-aer", "pytket", "pytket-quantinuum", "pytket-pecos",
                   "quantum-pecos", "guppylang", "guppylang-internals", "hugr", "tket", "tket-exts", "selene-sim",
                   "selene-core", "selene-hugr-qis-compiler")):
    from importlib import metadata
    out = {"python": sys.version.split()[0]}
    for p in pkgs:
        try:
            out[p] = metadata.version(p)
        except Exception:
            out[p] = None
    return out


def env_record():
    return {"sys_prefix": sys.prefix, "python": sys.executable, "versions": versions()}


def write_gate(R, text):
    from skqd.report import write_report
    path = R.save()
    write_report(f"{R.gate}.md", text)
    print(f"{R.gate}: {'PASS' if R.passed else 'FAIL'} -> {rel(path)}")
    for c in R.criteria:
        print(f"  [{'PASS' if c.passed else 'FAIL'}] {c.name[:100]}: {str(c.value)[:300]}")
    return 0 if R.passed else 1


def fmt(x, nd=4):
    if x is None:
        return "n/a"
    if isinstance(x, (bool, np.bool_)):
        return str(bool(x))
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    x = float(x)
    return f"{x:.{nd}g}" if (abs(x) >= 1e-3 or x == 0) else f"{x:.3e}"


# --------------------------------------------------------------------------- the physics of one lattice
class Phys:
    """Model(L), the codeword table, the per-sector data and the exact distribution of every frozen circuit."""

    def __init__(self, lat):
        from skqd.exact import Model
        from skqd.reference_sim import CodewordEmbedding
        self.lat = lat
        self.M = Model(lat)
        self.emb = CodewordEmbedding(self.M)
        self.n = int(self.emb.n)
        self.int_to_idx = {int(x): i for i, x in enumerate(self.emb.ints)}
        self.sector = {}
        for tb in (0, 2):
            ref = self.M.reference(G2, tb)
            idx = np.asarray(ref.indices, dtype=int)
            self.sector[tb] = {"indices": idx, "dim": int(len(idx)), "ints": set(int(self.emb.ints[i]) for i in idx),
                               "a": float(len(idx)) / float(2 ** self.n)}

    def exact(self, man):
        """{string int: p} over the sector codewords (krylov.ideal_sector_distribution, repetitions 1)."""
        from skqd.krylov import ideal_sector_distribution
        d = ideal_sector_distribution(self.M, G2, int(man["twoB"]), int(man["reference"]), int(man["k"]),
                                      float(man["dt"]), 1)
        p = np.asarray(d["p"], float)
        return {int(self.emb.ints[int(i)]): float(x) for i, x in zip(d["sector_indices"], p)}

    def decode(self, counts, twoB):
        """{string int: n} -> ({full-basis index: n} of the sector, rejected count)."""
        acc, rej = {}, 0
        S = self.sector[twoB]["ints"]
        for x, v in counts.items():
            if int(x) in S:
                i = self.int_to_idx[int(x)]
                acc[i] = acc.get(i, 0) + int(v)
            else:
                rej += int(v)
        return acc, rej


def per_state(counts, probs, n):
    from skqd.campaign33 import stats as ST
    return ST.per_state_test(counts, probs, n, N_SIGMA, P_MIN)


def plan_of_record():
    """{circuit id: shots} of the H0_2x2 plan of record (the coarse-step circuits only)."""
    d = load_json(H0_PLAN)
    out = {}
    for g in d.get("groups", []) or load_json(os.path.join(ROOT, "validation", "H0_2x2.json"))["data"]["shot_plan"]["groups"]:
        for c in g["ids"]:
            if not c.startswith("cal_"):
                out[c] = out.get(c, 0) + int(g["shots"])
    return out


def skqd_reading(P, counts_by_circuit, mans, label=""):
    """The SKQD assembly of gate_H0_2x2.stage_assemble per sector (decode, B_all, B_sig, recall of S999, the
    Ritz energy and the certificates) on {circuit id: {string int: n}}."""
    import gate_H0_2x2 as H
    from skqd.skqd import support_metrics
    out = {}
    for sec, tb in (("B=0", 0), ("B=1", 2)):
        Hm, idx, ev, refobj, refs = H.sector_tables(P.M, G2, tb)
        E0, E1 = float(refobj.E0), float(refobj.energies[1])
        ids = sorted(c for c in counts_by_circuit if int(mans[c]["twoB"]) == tb)
        N = int(sum(sum(counts_by_circuit[c].values()) for c in ids))
        dim = len(idx)
        a = P.sector[tb]["a"]
        mu = N * a / dim
        nstate = {int(s): 0 for s in idx}
        rejected = 0
        for c in ids:
            acc, rej = P.decode(counts_by_circuit[c], tb)
            rejected += rej
            for s, v in acc.items():
                nstate[int(s)] += int(v)
        B_all = sorted(s for s, v in nstate.items() if v > 0)
        B_sig, _pv = H.sig_support(nstate, {s: mu for s in nstate})
        prob = np.zeros(P.M.basis.dim)
        prob[refobj.indices] = np.abs(refobj.ground) ** 2
        dt = float(mans[ids[0]]["dt"])
        e_all = H.energy_block(Hm, B_all, refs, E0, E1, ev, dt)
        e_sig = H.energy_block(Hm, B_sig, refs, E0, E1, ev, dt)
        rec_all = support_metrics(sorted(set(B_all) | set(refs)), prob, 1e-3)
        rec_sig = support_metrics(sorted(set(B_sig) | set(refs)), prob, 1e-3)
        if tb == 0:
            ctype, iv = "kato_temple_exact_E1", e_all["kato_temple_rigorous_exact_E1"]
        else:
            ctype, iv = "weinstein", e_all["weinstein_rigorous"]
        inside = bool(iv is not None and iv[0] - 1e-12 <= E0 <= iv[1] + 1e-12)
        out[sec] = {"circuits": len(ids), "shots": N, "accepted": int(sum(nstate.values())), "rejected": int(rejected),
                    "accepted_fraction": (sum(nstate.values()) / N) if N else None, "dim": dim, "garbage_acceptance": a,
                    "mu_per_state": mu, "B_all_size": len(B_all), "B_sig_size": len(B_sig),
                    "recall_S999_B_all": rec_all["recall"], "recall_S999_B_sig": rec_sig["recall"],
                    "support_B_all": rec_all, "support_B_sig": rec_sig,
                    "E0": E0, "E1": E1, "E_R_B_all": e_all["E_R"], "E_R_B_sig": e_sig["E_R"],
                    "E_R_minus_E0_B_all": e_all["E_R"] - E0, "E_R_minus_E0_B_sig": e_sig["E_R"] - E0,
                    "certificate": {"type": ctype, "interval": iv, "E0_inside": inside, "basis": "B_all u refs"},
                    "variational_ok": bool(e_all["E_R"] >= E0 - VAR_TOL and e_sig["E_R"] >= E0 - VAR_TOL),
                    "energy_B_all": e_all, "energy_B_sig": e_sig}
    return out


# --------------------------------------------------------------------------- tier: export (venv)
def tier_export(args):
    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    from skqd.campaign33.circuits import dump_qpy13
    lat = args.lattice
    t0 = time.time()
    idx, mans, cals = family(lat)
    ids = list(idx["circuits"]) + list(idx.get("calibration", []))
    if lat == 4:
        ids = [c for c in idx["circuits"] if int(mans[c]["k"]) == 1]
    if args.only:
        ids = [c for c in ids if c in set(args.only)]
    out_dir = qpy_dir(lat)
    os.makedirs(out_dir, exist_ok=True)
    ip = os.path.join(out_dir, "index.json")
    index = load_json(ip) if os.path.exists(ip) else {"circuits": {}}
    for cid in ids:
        m = mans.get(cid) or cals[cid]
        text = read_frozen(lat, m["files"]["json"])
        if sha256_text(text) != m["json_sha256"]:
            raise SystemExit(f"{cid}: frozen JSON sha256 mismatch")
        c = qn.from_json(json.loads(text))
        ir, n, qmap = qn.pytket_to_ir(c)
        if qmap != {q: q for q in range(n)}:
            raise SystemExit(f"{cid}: measurement map is not q[k] -> c[k]")
        qc = cq.ir_to_qiskit(ir, n, measure=True)
        rec = dump_qpy13(qc, os.path.join(out_dir, cid + ".qpy.gz"))
        index["circuits"][cid] = {"file": cid + ".qpy.gz", "gz_sha256": rec["gz_sha256"], "qpy": rec["header"],
                                  "bytes_uncompressed": rec["bytes_uncompressed"], "source_json_sha256": m["json_sha256"],
                                  "ops": {k: int(v) for k, v in qc.count_ops().items()}}
        print(f"  {cid}: {rec['header']} {rec['bytes_uncompressed']} B [{time.time() - t0:.0f} s]", flush=True)
    index.update({"produced_by": "scripts/quantinuum_lattice_tests.py --tier export", "prompt": PROMPT,
                  "lattice": f"2x{lat}", "route": ("frozen pytket JSON -> quantinuum_native.pytket_to_ir -> "
                                                   "circuits_qiskit.ir_to_qiskit(measure=True: barrier, measure q[k] -> c[k]) "
                                                   "-> campaign33.circuits.dump_qpy13 (QPY v13, gzip mtime 0)"),
                  "versions": versions(("qiskit", "pytket", "pytket-quantinuum")), "created": now()})
    with open(ip, "w") as fh:
        json.dump(index, fh, indent=1)
    return 0


def load_native_qiskit(lat, cid):
    from skqd.campaign33.circuits import load_qpy, sha256_file
    d = qpy_dir(lat)
    idx = load_json(os.path.join(d, "index.json"))
    e = idx["circuits"][cid]
    p = os.path.join(d, e["file"])
    if sha256_file(p) != e["gz_sha256"]:
        raise SystemExit(f"{cid}: QPY bundle sha256 mismatch")
    return load_qpy(p)[0], e


# --------------------------------------------------------------------------- tier: noiseless (coding)
def tier_noiseless(args):
    from qiskit_aer import AerSimulator
    lat = 2
    t0 = time.time()
    idx, mans, _ = family(lat)
    P = Phys(lat)
    plan = plan_of_record()
    ids = sorted(idx["circuits"])
    sim = AerSimulator(method="statevector", precision="double", max_parallel_threads=int(args.threads))
    per, seeds, seqs = {}, {}, {}
    t_s = time.time()
    for c_i, cid in enumerate(ids):
        qc, _e = load_native_qiskit(lat, cid)
        n = max(N_T2, int(plan[cid]))
        seed = SEED_T2 + 1000 * c_i + 0
        mem = sim.run(qc, shots=n, seed_simulator=seed, memory=True).result().get_memory(0)
        x = [int(s.replace(" ", ""), 2) for s in mem]
        counts = {}
        for v in x:
            counts[v] = counts.get(v, 0) + 1
        probs = P.exact(mans[cid])
        ps = per_state(counts, probs, n)
        ps.update({"seed": seed, "shots": n, "reference_hits": int(counts.get(int(mans[cid]["reference_int"]), 0))})
        per[cid] = ps
        seeds[cid] = seed
        seqs[cid] = x
        print(f"  {cid}: {n} shots, max z {ps['max_z']:.2f}, failures {len(ps['failures'])}, outside "
              f"{ps['fraction_outside_exact_support']} [{time.time() - t0:.0f} s]", flush=True)
    t_samp = time.time() - t_s
    # the f = 1 SKQD reference at the plan of record: the first plan[c] shots of each circuit's sequence
    cnt_por = {}
    for cid in ids:
        cc = {}
        for v in seqs[cid][:int(plan[cid])]:
            cc[v] = cc.get(v, 0) + 1
        cnt_por[cid] = cc
    ref = skqd_reading(P, cnt_por, mans)
    save_frag("QN_2x2", "noiseless", {
        "engine": "AerSimulator(method=statevector, precision=double), CPU", "threads": args.threads,
        "per_circuit": per, "seeds": seeds, "seed_rule": SEED_RULES["T2"],
        "shots_rule": f"max({N_T2}, plan-of-record shots of the circuit) (the f = 1 reference reads the first plan shots)",
        "plan_of_record": {"path": rel(H0_PLAN), "shots_by_circuit": plan, "total": int(sum(plan.values()))},
        "skqd_f1_reference": ref, "sampling_s": t_samp, "seconds_per_shot": t_samp / sum(p["shots"] for p in per.values()),
        "wall_s": time.time() - t0, "environment": env_record()})
    return assemble_QN_2x2()


# --------------------------------------------------------------------------- tier: noise (coding / venv)
def mean_counts(mans):
    return {"n2": float(np.mean([m["counts"]["n_zz"] for m in mans.values()])),
            "n1": float(np.mean([m["counts"]["n_phasedx"] for m in mans.values()])),
            "nm": float(np.mean([m["counts"]["n_meas"] for m in mans.values()]))}


def spec_of(sid, n_qubits, mans, lat):
    """The prompts/33 scenario; E7 at this lattice's mean native counts (labelled E7(0.10; 2x<L> counts))."""
    from skqd.campaign33 import noise as N
    if sid != "E7_0.10_lat":
        return N.quantinuum_spec(sid, n_qubits=n_qubits)
    mc = mean_counts(mans)
    p2 = N.matched_f_eps2(0.10, n2=mc["n2"], n1=mc["n1"], nm=mc["nm"])
    E = dict(N.E1, p2=p2)
    nm = N._model(E["p2"], E["p1"], E["p10"], E["p01"])
    desc = {"id": f"E7(0.10; 2x{lat} counts)", "class": "depolarizing + readout",
            "channel_classes": ["2q depolarizing on rzz", "1q depolarizing on rx/ry (= native PhasedX)",
                                "asymmetric readout", "rz virtual (noiseless)"],
            "parameters": dict(E, f_target=0.10, matched_counts=mc,
                               matched_f_rule=("f_gate = (1-eps2)^n2 (1-eps1)^n1 (1-eps_ro)^nm at the 2x%d mean native "
                                               "counts (noise.matched_f_eps2 with n2, n1, nm passed explicitly)") % lat),
            "source": N.SOURCES["E7"] + f"; counts of the frozen 2x{lat} family",
            "not_modelled": ["memory / transport dephasing", "leakage", "crosstalk", "initialisation error"]}
    return N.NoiseSpec("E7_0.10_lat", nm, None, desc, readout=(E["p10"], E["p01"]))


def NOISY_SIM_KW(threads):
    """Shot-parallel trajectories without gate fusion: the fastest exact-equivalent CPU setting measured on this
    laptop for the 12-qubit noisy circuits (0.021 s/shot vs 0.031 with fusion, 4 threads, under load)."""
    return {"max_parallel_threads": int(threads), "max_parallel_shots": int(threads), "fusion_enable": False}


def run_noisy(spec, qc, shots, seed, threads):
    from qiskit_aer import AerSimulator
    sim = AerSimulator(method="statevector", precision="double", noise_model=spec.noise_model, **NOISY_SIM_KW(threads))
    t = time.time()
    res = sim.run(spec.apply(qc), shots=int(shots), seed_simulator=int(seed)).result()
    from skqd.campaign33.sampling import counts_to_int
    return counts_to_int(res.get_counts(0)), time.time() - t


def tier_noise(args):
    if args.lattice == 4:
        return tier_noise_4(args)
    lat = 2
    t0 = time.time()
    idx, mans, _ = family(lat)
    ids = sorted(idx["circuits"])
    P = Phys(lat)
    part = args.part or "rate"
    from skqd.campaign33 import noise as N
    if part == "rate":
        qc, _ = load_native_qiskit(lat, RATE_CIRCUIT)
        out = {}
        for sid in ("E1", "E5b"):
            spec = spec_of(sid, P.n, mans, lat)
            cnt, dt = run_noisy(spec, qc, RATE_SHOTS, SEED_FC + 9_000_000, args.threads)
            out[sid] = {"shots": RATE_SHOTS, "seconds": dt, "s_per_shot": dt / RATE_SHOTS, "circuit": RATE_CIRCUIT}
            print(f"  rate {sid}: {dt / RATE_SHOTS:.2e} s/shot", flush=True)
        por = sum(plan_of_record().values())
        worst = max(v["s_per_shot"] for v in out.values())
        sizing = {"fcells_shots": N_FCELL * len(ids) * len(SCENARIOS), "por_shots_per_scenario": por,
                  "fcells_estimate_s": worst * N_FCELL * len(ids) * len(SCENARIOS),
                  "por_estimate_s_per_scenario": worst * por, "cap_s": CAP_T3_S,
                  "rule": "estimates at the dearer of the two measured rates (E5b, the memory transform)"}
        save_frag("QN_2x2", "noise_rate", {"rates": out, "sizing": sizing, "threads": args.threads,
                                          "aer_settings": NOISY_SIM_KW(args.threads),
                                          "environment": env_record()})
        return assemble_QN_2x2()
    if part == "fcells":
        sids = args.scenarios or list(SCENARIOS)
        for sid in sids:
            s_i = SCENARIOS.index(sid)
            spec = spec_of(sid, P.n, mans, lat)
            cells, wall = {}, time.time()
            for c_i, cid in enumerate(ids):
                m = mans[cid]
                qc, _ = load_native_qiskit(lat, cid)
                seed = SEED_FC + 1000 * s_i + c_i
                cnt, dt = run_noisy(spec, qc, N_FCELL, seed, args.threads)
                cells[cid] = fcell(P, m, cnt, N_FCELL, spec, qc, seed, dt)
            save_frag("QN_2x2", f"fcells_{sid}", {"scenario": sid, "description": N.describe(spec) if hasattr(N, "describe") else spec.description,
                                                 "cells": cells, "wall_s": time.time() - wall, "shots_per_cell": N_FCELL,
                                                 "seed_rule": SEED_RULES["T3_fcells"], "threads": args.threads,
                                                 "environment": env_record()})
            print(f"  f-cells {sid}: {len(cells)} circuits in {time.time() - wall:.0f} s", flush=True)
        return assemble_QN_2x2()
    if part == "por":
        sids = args.scenarios or list(POR_ORDER)
        plan = plan_of_record()
        for sid in sids:
            if args.budget_s and time.time() - t0 > float(args.budget_s):
                print(f"  budget reached before {sid}", flush=True)
                break
            s_i = SCENARIOS.index(sid)
            spec = spec_of(sid, P.n, mans, lat)
            counts, wall, seeds = {}, time.time(), {}
            for c_i, cid in enumerate(ids):
                qc, _ = load_native_qiskit(lat, cid)
                seed = SEED_POR + 1000 * s_i + c_i
                cnt, _dt = run_noisy(spec, qc, plan[cid], seed, args.threads)
                counts[cid] = cnt
                seeds[cid] = seed
            rd = skqd_reading(P, counts, mans)
            save_frag("QN_2x2", f"por_{sid}", {"scenario": sid, "reading": rd, "seeds": seeds,
                                              "seed_rule": SEED_RULES["T3_plan_of_record"],
                                              "shots_total": int(sum(plan.values())), "wall_s": time.time() - wall,
                                              "seconds_per_shot": (time.time() - wall) / sum(plan.values()),
                                              "threads": args.threads, "environment": env_record()})
            print(f"  plan of record {sid}: " + "; ".join(f"{s} recall {v['recall_S999_B_all']:.3f} E_R-E0 "
                                                           f"{v['E_R_minus_E0_B_all']:.2e} acc {v['accepted_fraction']:.3f}"
                                                           for s, v in rd.items()) + f" [{time.time() - wall:.0f} s]",
                  flush=True)
        return assemble_QN_2x2()
    raise SystemExit(f"--part {part}?")


def fcell(P, m, cnt, N, spec, qc, seed, dt):
    from skqd.campaign33 import noise as N_
    from skqd.campaign33 import stats as ST
    tb = int(m["twoB"])
    probs = P.exact(m)
    pref = float(probs[int(m["reference_int"])])
    S = P.sector[tb]
    acc, rej = P.decode(cnt, tb)
    hits = int(cnt.get(int(m["reference_int"]), 0))
    a_cnt = int(sum(acc.values()))
    cell = ST.f_hit_cell([(hits, N, pref, S["a"], S["dim"])], kappa=1.0)
    f0 = N_.f0_quantinuum(qc, spec, ref_bits=m["reference_bits"])
    lo, hi = ST.wilson(a_cnt, N)
    return {"shots": N, "seed": int(seed), "seconds": dt, "reference_hits": hits, "p_reference_exact": pref,
            "garbage_acceptance": S["a"], "dim": S["dim"], "f_hit": cell["f_hit"], "f_hit_ci95": cell["f_hit_ci"],
            "f0": f0["f0"], "g0": f0["g0"], "readout_survival": f0["readout_survival"],
            "r_nc": (cell["f_hit"] / f0["f0"]) if (cell["f_hit"] is not None and f0["f0"] > 0) else None,
            "accepted": a_cnt, "accepted_fraction": a_cnt / N, "accepted_fraction_wilson95": [lo, hi],
            "k": int(m["k"]), "sector": m["sector"]}


def tier_noise_4(args):
    """QN_2x4 (R3): analytic only -- f0 per circuit and scenario from the native counts (noise.f0_quantinuum on
    the circuit read back from the frozen JSON) and the gate-only f per device (Q0P_2x4 predict); 0 shots."""
    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    from skqd.campaign33 import noise as N
    lat = 4
    t0 = time.time()
    idx, mans, _ = family(lat)
    ids = sorted(idx["circuits"])
    table = {}
    for cid in ids:
        m = mans[cid]
        c = qn.from_json(json.loads(read_frozen(lat, m["files"]["json"])))
        ir, n, _ = qn.pytket_to_ir(c)
        qc = cq.ir_to_qiskit(ir, n, measure=True)
        row = {}
        for sid in SCENARIOS:
            spec = spec_of(sid, n, mans, lat)
            f0 = N.f0_quantinuum(qc, spec, ref_bits=m["reference_bits"])
            row[sid] = {"f0": f0["f0"], "g0": f0["g0"], "log10_f0": (math.log10(f0["f0"]) if f0["f0"] > 0 else None),
                        "n_2q": f0.get("n_2q"), "n_1q_noisy": f0.get("n_1q_noisy")}
        table[cid] = row
        print(f"  {cid}: E1 f0 {row['E1']['f0']:.3e} [{time.time() - t0:.0f} s]", flush=True)
    q0p = load_json(os.path.join(ROOT, "validation", "Q0P_2x4.json"))["data"].get("Q5") or {}
    save_frag("QN_2x4", "analytic", {"f0": table, "scenarios": list(SCENARIOS), "devices": q0p.get("devices"),
                                     "sampled_shots": 0, "wall_s": time.time() - t0, "environment": env_record(),
                                     "e7_counts": mean_counts(mans)})
    return assemble_QN_2x4()


# --------------------------------------------------------------------------- assembly: QN_2x2, QN_2x4
def cross_reference_2x3():
    out = {}
    for p in [os.path.join(ROOT, "validation", "C4_FCELLS_A.json")] + sorted(glob.glob(os.path.join(ROOT, "validation", "C33_*.json"))):
        if os.path.exists(p):
            d = load_json(p)
            out[rel(p)] = {"status": d.get("status"), "title": d.get("title", "")[:200]}
    out["C3_AER"] = {"file": "validation/C3_AER.json",
                     "status": load_json(os.path.join(ROOT, "validation", "C3_AER.json")).get("status")}
    return out


def assemble_QN_2x2():
    from skqd.report import GateResult, md_table
    t0 = time.time()
    G = "QN_2x2"
    R = GateResult(G, "2x2 native circuits under noiseless sampling and the Quantinuum noise models (prompts/35 T2 + T3)")
    NL = frag(G, "noiseless")
    RT = frag(G, "noise_rate")
    FC = {k[len("fcells_"):]: v for k, v in frags(G, "fcells_").items()}
    PR = {k[len("por_"):]: v for k, v in frags(G, "por_").items()}
    data = {"prompt": PROMPT, "qpu_seconds": 0, "hqc": 0, "ehqc": 0, "seed_rules": SEED_RULES,
            "what_pass_means": ("the 28 frozen 2x2 native circuits sample their exact distributions noiselessly and run "
                                "through the Quantinuum-class noise scenarios E1-E7 with every number recorded; a model "
                                "statement, not a device statement")}
    # N1
    if NL:
        per = NL["per_circuit"]
        nf = sum(len(v["failures"]) for v in per.values())
        out = max(v["fraction_outside_exact_support"] for v in per.values())
        tested = sum(v["tested_states"] for v in per.values())
        R.add("N1 per-state 5 sigma test |n_s/N - p_s| <= 5 sqrt(p_s(1-p_s)/N), p_s >= 1e-3, on all 28 noiseless circuits; "
              "fraction outside the exact support",
              {"circuits": len(per), "states_tested": tested, "max_z": max(v["max_z"] for v in per.values()),
               "failures": nf, "max_fraction_outside_exact_support": out},
              "28 circuits; 0 failures (Bonferroni: P(any |z| > 5 | no bug) < 6e-7 x states tested); outside 0",
              len(per) == 28 and nf == 0 and out == 0.0)
        ref = NL["skqd_f1_reference"]
        rec_ok = all(ref[s]["recall_S999_B_all"] >= RECALL_MIN for s in ref)
        in_ok = all(ref[s]["certificate"]["E0_inside"] for s in ref)
        var_ok = all(ref[s]["variational_ok"] for s in ref)
        R.add("N2 noiseless SKQD at the H0_2x2 plan of record (133907 shots): recall of S999 >= 0.9 in both sectors, E0 "
              "inside the Kato-Temple (B=0) / Weinstein (B=1) interval, E_R >= E0 - 1e-9",
              {s: {"recall_S999": ref[s]["recall_S999_B_all"], "E_R_minus_E0": ref[s]["E_R_minus_E0_B_all"],
                   "interval": ref[s]["certificate"]["interval"], "E0_inside": ref[s]["certificate"]["E0_inside"]}
               for s in ref}, ">= 0.9; inside; variational", rec_ok and in_ok and var_ok)
        data["noiseless"] = NL
    else:
        R.add("N1 noiseless per-state test", "not run (--tier noiseless)", "0 failures", False)
        R.add("N2 noiseless SKQD reference", "not run (--tier noiseless)", "recall >= 0.9; inside; variational", False)
    # N3
    cf = load_json(os.path.join(ROOT, "validation", "CF_traj.json"))["data"]["pooled_k1"]
    r_nc_23 = float(cf["r_nc"])
    if FC:
        complete = all(all(all(k in c and c[k] is not None for k in ("f_hit", "f_hit_ci95", "f0", "seed"))
                           and "r_nc" in c for c in v["cells"].values()) and len(v["cells"]) == 28 for v in FC.values())
        band = None
        if "E1" in FC:
            from skqd.campaign33 import stats as ST
            cells = FC["E1"]["cells"]
            hits = int(sum(c["reference_hits"] for c in cells.values()))
            mu = float(sum(c["shots"] * (c["p_reference_exact"] * c["f0"] * r_nc_23 + c["garbage_acceptance"] / c["dim"])
                           for c in cells.values()))
            mu_k1 = float(sum(c["shots"] * (c["p_reference_exact"] * c["f0"] * r_nc_23 + c["garbage_acceptance"] / c["dim"])
                              for c in cells.values() if c["k"] == 1))
            hits_k1 = int(sum(c["reference_hits"] for c in cells.values() if c["k"] == 1))
            lo, hi = ST.poisson_band(mu)
            lo1, hi1 = ST.poisson_band(mu_k1)
            band = {"hits": hits, "expected": mu, "band95": [lo, hi], "inside": lo <= hits <= hi,
                    "k1_only": {"hits": hits_k1, "expected": mu_k1, "band95": [lo1, hi1], "inside": lo1 <= hits_k1 <= hi1},
                    "r_nc_2x3": r_nc_23, "r_nc_source": "validation/CF_traj.json data.pooled_k1.r_nc (2x3, k = 1 arms)",
                    "expectation_rule": ("sum_c N_c (p_ref,c f0(c) r_nc + a/dim): the reference-hit count implied by "
                                         "f_hit = f0 r_nc (prompts/35 N3 writes sum_c N_c f0(c) r_nc on the f_hit scale; "
                                         "the count adds p_ref and the garbage term of pooled_reference_string_test)"),
                    "reading": "information: 2x2 has no measured r_nc of its own; r_nc is the 2x3 k = 1 value",
                    "verdict": "consistent" if lo <= hits <= hi else "tension"}
        R.add("N3 every f-cell (28 circuits x the scenarios run) has f_hit, its 95 % Garwood interval, f0, r_nc and its "
              "seed; E1 all-circuit reference hits against the Poisson 95 % band at the 2x3 r_nc (information)",
              {"scenarios": sorted(FC), "cells": sum(len(v["cells"]) for v in FC.values()),
               "E1_band": None if band is None else {k: band[k] for k in ("hits", "expected", "band95", "verdict")}},
              "complete; band = information ('tension' does not fail)", complete and len(FC) == len(SCENARIOS))
        data["fcells"] = {"per_scenario": FC, "E1_band": band}
    else:
        R.add("N3 f-cells", "not run (--tier noise --part fcells)", "complete", False)
    # N4
    if PR:
        fields_ok = all(all(k in v for k in ("recall_S999_B_all", "E_R_B_all", "certificate", "accepted_fraction"))
                        for p in PR.values() for v in p["reading"].values())
        var = {sid: all(v["variational_ok"] for v in p["reading"].values()) for sid, p in PR.items()}
        R.add("N4 every plan-of-record run reports recall, E_R, the certificate, the accepted fraction, and E_R >= E0 - 1e-9 "
              "(a violation is a STOP)",
              {sid: {s: {"recall": round(v["recall_S999_B_all"], 4), "E_R_minus_E0": v["E_R_minus_E0_B_all"],
                         "accepted": round(v["accepted_fraction"], 4), "E0_inside": v["certificate"]["E0_inside"]}
                     for s, v in p["reading"].items()} for sid, p in PR.items()},
              "fields present; variational", fields_ok and all(var.values()))
        data["plan_of_record"] = PR
        data["scenarios_run"] = [s for s in POR_ORDER if s in PR]
        data["stop_variational"] = [s for s, ok in var.items() if not ok]
    else:
        R.add("N4 plan-of-record runs", "not run (--tier noise --part por)", "fields; variational", False)
    # N5
    seeds_ok = bool(NL) and all("seed" in v for v in (NL or {}).get("per_circuit", {}).values()) and \
        all(all("seed" in c for c in v["cells"].values()) for v in FC.values()) and all("seeds" in p for p in PR.values())
    rates = (RT or {}).get("rates")
    R.add("N5 qpu_seconds == 0, hqc == 0; seeds and s/shot recorded; scenarios_run listed",
          {"qpu_seconds": 0, "hqc": 0, "seeds": seeds_ok, "s_per_shot": None if not rates else
           {k: v["s_per_shot"] for k, v in rates.items()}, "scenarios_run": data.get("scenarios_run")},
          "0; 0; recorded; listed", seeds_ok and bool(rates) and bool(data.get("scenarios_run")))
    data["rates"] = RT
    data["cross_reference_2x3"] = cross_reference_2x3()
    data["environment_runner"] = env_record()
    R.data = data
    R.runtime_s = time.time() - t0 + sum(float(x.get("wall_s", 0.0)) for x in [NL or {}] + list(FC.values()) + list(PR.values()))
    L = [f"# Gate {G} — {R.title}", "", f"Status: **{'PASS' if R.passed else 'FAIL'}**.  Generated by "
         f"`scripts/quantinuum_lattice_tests.py` from `validation/{G}.json`; no number is typed.  QPU s 0, HQC 0.", "",
         f"What PASS means: \"{data['what_pass_means']}\".", "", "## Criteria", "", R.criteria_table(), ""]
    if FC:
        L += ["## f-cells (2000 shots per circuit and scenario; pooled over the 28 circuits)", "",
              md_table(["scenario", "k = 1 f_hit (mean of circuits)", "mean f0", "mean r_nc (k = 1)", "accepted fraction (mean)"],
                       [[s, fmt(np.mean([c["f_hit"] for c in v["cells"].values() if c["k"] == 1])),
                         fmt(np.mean([c["f0"] for c in v["cells"].values()])),
                         fmt(np.mean([c["r_nc"] for c in v["cells"].values() if c["k"] == 1 and c["r_nc"] is not None])),
                         fmt(np.mean([c["accepted_fraction"] for c in v["cells"].values()]))]
                        for s, v in sorted(FC.items())]), ""]
    if PR:
        L += ["## Plan-of-record SKQD per scenario (133907 shots; B_all u refs)", "",
              md_table(["scenario", "sector", "recall S999", "E_R - E0", "certificate", "E0 inside", "accepted fraction"],
                       [[sid, s, fmt(v["recall_S999_B_all"]), fmt(v["E_R_minus_E0_B_all"]), v["certificate"]["type"],
                         v["certificate"]["E0_inside"], fmt(v["accepted_fraction"])]
                        for sid in POR_ORDER if sid in PR for s, v in PR[sid]["reading"].items()]), "",
              "Measured on ibm_kingston (validation/H0_2x2.json data.clean_fraction): see that gate; not recomputed here.", ""]
    L += ["## 2x3 cross reference", "", md_table(["file", "status"], [[k, v.get("status")] for k, v in data["cross_reference_2x3"].items()]), ""]
    from skqd.report import write_report  # noqa
    return write_gate(R, "\n".join(L))


def assemble_QN_2x4():
    from skqd.report import GateResult, md_table
    G = "QN_2x4"
    A = frag(G, "analytic")
    R = GateResult(G, "2x4 native circuits under the Quantinuum noise models: analytic fault-free fraction and gate-only f "
                      "(prompts/35 T3, R3; nothing sampled)")
    idx, mans, _ = family(4)
    data = {"prompt": PROMPT, "qpu_seconds": 0, "hqc": 0, "ehqc": 0, "sampled_shots": 0,
            "what_pass_means": ("the analytic fault-free fraction f0 of every built 2x4 native circuit under the 11 "
                                "Quantinuum scenarios and the gate-only f per device are tabulated; nothing is sampled "
                                "because at 2x4 every scenario gives f ~ 0 (R3: (1 - eps2)^n_zz with n_zz ~ 7e4)")}
    if A:
        t = A["f0"]
        devs = A.get("devices") or {}
        complete = (len(t) == len(mans) and all(len(r) == len(SCENARIOS) for r in t.values()) and len(devs) == 4)
        R.add("A1 the table is complete over the built circuits x 11 scenarios x 4 devices",
              {"circuits": len(t), "scenarios": len(SCENARIOS), "devices": len(devs),
               "max_f0_any_scenario": max(v["f0"] for r in t.values() for v in r.values()),
               "E1_log10_f0_range": [min(r["E1"]["log10_f0"] for r in t.values()), max(r["E1"]["log10_f0"] for r in t.values())]},
              "complete", complete)
        R.add("A2 sampled_shots == 0 and the reason (R3) in what_pass_means", {"sampled_shots": A["sampled_shots"]},
              "0", A["sampled_shots"] == 0)
        data["analytic"] = A
    else:
        R.add("A1 table", "not run", "complete", False)
        R.add("A2 sampled_shots", "not run", "0", False)
    R.data = data
    L = [f"# Gate {G} — {R.title}", "", f"Status: **{'PASS' if R.passed else 'FAIL'}**.  Generated from `validation/{G}.json`.", "",
         f"What PASS means: \"{data['what_pass_means']}\".", "", "## Criteria", "", R.criteria_table(), ""]
    if A:
        L += ["## log10 f0 per scenario (min / max over the built circuits)", "",
              md_table(["scenario", "min", "max"],
                       [[s, fmt(min(r[s]["log10_f0"] for r in A["f0"].values() if r[s]["log10_f0"] is not None)),
                         fmt(max(r[s]["log10_f0"] for r in A["f0"].values() if r[s]["log10_f0"] is not None))]
                        for s in SCENARIOS]), ""]
        if A.get("devices"):
            L += ["## Gate-only f per device (validation/Q0P_2x4.json data.Q5)", "",
                  md_table(["device", "f mean", "eps2 for mean f 0.1", "eps2 for worst f 0.05"],
                           [[v["device"], fmt(v["f_gate_only_mean"]), fmt(v["eps2_for_mean_f_0.1"]),
                             fmt(v["eps2_for_worst_f_0.05"])] for v in A["devices"].values()]), ""]
    return write_gate(R, "\n".join(L))


# --------------------------------------------------------------------------- tier: pecos (pecos venv)
def tier_pecos(args):
    lat = args.lattice
    if lat == 4:
        return pecos_2x4()
    if lat == 3:
        return pecos_2x3_smoke(args)
    from skqd.campaign33 import engines as EN
    G = "QEMU_2x2"
    idx, mans, _ = family(2)
    ids = sorted(idx["circuits"])
    part = args.part or "rate"
    P = Phys(2)
    if part == "rate":
        eng = EN.Pecos(circuit_dir=circ_dir(2), ids=["B0_ref06_k1"])
        t = time.time()
        cnt = eng.run("B0_ref06_k1", 5, SEED_T4 + ids.index("B0_ref06_k1"))
        dt = time.time() - t
        sps = dt / 5.0
        shots = max(20, min(1000, int(math.floor(CAP_T4_S / (28.0 * sps)))))
        save_frag(G, "rate", {"circuit": "B0_ref06_k1", "shots": 5, "seconds": dt, "seconds_per_shot": sps,
                              "shots_per_circuit": shots, "rule": "min(1000, floor(4 x 3600 / (28 s_shot))), floor 20",
                              "counts": {str(k): v for k, v in cnt.items()}, "versions": eng.versions(),
                              "environment": env_record()})
        print(f"  pecos rate {sps:.3f} s/shot -> {shots} shots per circuit", flush=True)
        return assemble_QEMU_2x2()
    if part == "circuit":
        rt = frag(G, "rate")
        if not rt:
            raise SystemExit("run --part rate first")
        for cid in (args.only or ids):
            eng = EN.Pecos(circuit_dir=circ_dir(2), ids=[cid])
            c_i = ids.index(cid)
            n = int(args.shots or rt["shots_per_circuit"])
            seed = SEED_T4 + c_i
            t = time.time()
            cnt = eng.run(cid, n, seed)
            dt = time.time() - t
            m = mans[cid]
            ps = per_state(cnt, P.exact(m), n)
            save_frag(G, f"circuit_{cid}", {"id": cid, "shots": n, "seed": seed, "seconds": dt, "seconds_per_shot": dt / n,
                                            "per_state": ps, "reference_hits": int(cnt.get(int(m["reference_int"]), 0)),
                                            "counts": {str(k): v for k, v in sorted(cnt.items())},
                                            "input_sha256": eng.sha[cid], "versions": eng.versions(),
                                            "decode_rule": "bit k = c[k] (engines.Pecos.run)", "environment": env_record()})
            print(f"  {cid}: {n} shots in {dt:.0f} s, max z {ps['max_z']:.2f}, failures {len(ps['failures'])}, outside "
                  f"{ps['fraction_outside_exact_support']}", flush=True)
        return assemble_QEMU_2x2()
    if part == "probe":
        eng = EN.Pecos(circuit_dir=circ_dir(2), ids=["B0_ref06_k1"])
        m = mans["B0_ref06_k1"]
        rec = {"circuit": "B0_ref06_k1", "shots": 20, "seed": SEED_T4 + 900, "noisy_simulation": True}
        t = time.time()
        try:
            c = eng.circ["B0_ref06_k1"]
            h = eng.be.process_circuit(c, n_shots=20, simulator="state-vector", noisy_simulation=True, seed=SEED_T4 + 900)
            r = eng.be.get_result(h)
            names = [(b.reg_name, b.index[0]) for b in (r.get_bitlist() if hasattr(r, "get_bitlist") else c.bits)]
            cnt = {}
            for key, v in r.get_counts().items():
                d = {names[j]: int(key[j]) for j in range(len(key))}
                x = sum(d[("c", k)] << k for k in range(len(key)))
                cnt[x] = cnt.get(x, 0) + int(v)
            rec.update({"accepted_by_emulator": True, "reference_hits": int(cnt.get(int(m["reference_int"]), 0)),
                        "counts": {str(k): v for k, v in sorted(cnt.items())}})
        except Exception as exc:
            rec.update({"accepted_by_emulator": False, "error": f"{type(exc).__name__}: {str(exc)[:500]}"})
        rec["seconds"] = time.time() - t
        rec["note"] = ("information: the offline H2-1LE ships pecos's generic error model, not the H2-2 calibration "
                       "(prompts/35 3.6)")
        save_frag(G, "noisy_probe", rec)
        print(f"  noisy probe: {rec.get('accepted_by_emulator')} hits {rec.get('reference_hits')}", flush=True)
        return assemble_QEMU_2x2()
    if part == "assemble":
        return assemble_QEMU_2x2()
    raise SystemExit(f"--part {part}?")


def assemble_QEMU_2x2():
    from skqd.report import GateResult, md_table
    G = "QEMU_2x2"
    R = GateResult(G, "2x2 native circuits on Quantinuum's local emulator (pytket-quantinuum H2-1LE, pytket-pecos, "
                      "noiseless state vector; prompts/35 T4)")
    idx, mans, _ = family(2)
    rt = frag(G, "rate")
    per = {k[len("circuit_"):]: v for k, v in frags(G, "circuit_").items()}
    probe = frag(G, "noisy_probe")
    nf = sum(len(v["per_state"]["failures"]) for v in per.values())
    out = max([v["per_state"]["fraction_outside_exact_support"] for v in per.values()] or [None] or [0]) if per else None
    minshots = min([v["shots"] for v in per.values()] or [0])
    R.add("M1 all 28 circuits ran with >= 20 shots; 0 per-state failures (5 sigma, p_s >= 1e-3); fraction outside the "
          "exact support 0 on every circuit",
          {"circuits": len(per), "min_shots": minshots, "failures": nf, "max_fraction_outside": out,
           "max_z": max([v["per_state"]["max_z"] for v in per.values()] or [0.0])},
          "28; >= 20; 0; 0", len(per) == 28 and minshots >= 20 and nf == 0 and out == 0.0)
    vers = (rt or {}).get("versions") or {}
    R.add("M2 versions (pytket, pytket-quantinuum, pytket-pecos, quantum-pecos) and the rate recorded",
          {"versions": {k: vers.get(k) for k in ("pytket", "pytket-quantinuum", "pytket-pecos", "quantum-pecos")},
           "seconds_per_shot": (rt or {}).get("seconds_per_shot")},
          "recorded", bool(rt) and all(vers.get(k) for k in ("pytket", "pytket-quantinuum", "pytket-pecos", "quantum-pecos")))
    R.add("M3 hqc == 0", 0, "0", True)
    data = {"prompt": PROMPT, "qpu_seconds": 0, "hqc": 0, "ehqc": 0, "rate": rt, "per_circuit": per, "noisy_probe": probe,
            "seed_rule": SEED_RULES["T4"],
            "what_pass_means": ("the 28 frozen 2x2 native circuits run on Quantinuum's own local emulator (offline, "
                                "noiseless state vector) and reproduce their exact distributions; not a device statement")}
    R.data = data
    L = [f"# Gate {G} — {R.title}", "", f"Status: **{'PASS' if R.passed else 'FAIL'}**.  Generated from `validation/{G}.json`.", "",
         f"What PASS means: \"{data['what_pass_means']}\".", "", "## Criteria", "", R.criteria_table(), "",
         md_table(["circuit", "shots", "s/shot", "states tested", "max z", "outside support", "reference hits"],
                  [[c, v["shots"], fmt(v["seconds_per_shot"]), v["per_state"]["tested_states"], fmt(v["per_state"]["max_z"]),
                    v["per_state"]["fraction_outside_exact_support"], v["reference_hits"]] for c, v in sorted(per.items())]), ""]
    if probe:
        L += [f"Noisy probe (information): accepted {probe.get('accepted_by_emulator')}, reference hits "
              f"{probe.get('reference_hits')} of {probe.get('shots')}, {fmt(probe.get('seconds'))} s.  {probe['note']}.", ""]
    return write_gate(R, "\n".join(L))


def pecos_2x3_smoke(args):
    """QEMU_2x3_laptop_smoke: engines.run (token C3_LE) with the campaign driver's own Ctx in dry mode, nothing of
    campaign 33 written (the result goes only into validation/QEMU_2x3_laptop_smoke.json)."""
    import campaign33 as C33
    from skqd.campaign33 import engines as EN
    from skqd.report import GateResult
    t0 = time.time()
    ap = C33.build_parser({})
    a = ap.parse_args(["--token", "C3_LE", "--dry-run"])
    C33.apply_dry_defaults(a)
    ctx = C33.Ctx(a, {})
    err = None
    try:
        EN.run(ctx)
    except Exception as exc:
        err = f"{type(exc).__name__}: {str(exc)[:500]}"
    R = GateResult("QEMU_2x3_laptop_smoke", "2x3 C3_LE engine path on the laptop pecos venv (prompts/35 3.6; a smoke "
                                            "test, not the C3_LE token)")
    phys = ctx.physics_criteria
    R.add("engine set up and ran in dry mode (1 shot per k = 1 f-cell circuit + the 1-shot ladder)",
          {"engine": ctx.data.get("engine"), "shots_per_circuit": ctx.data.get("shots_per_circuit"),
           "ladder": ctx.data.get("ladder"), "error": err},
          "ran", err is None and not ctx.data.get("dropped"))
    R.add("decode check (P9 of the token, information in dry mode): every observed string in the circuit's sector",
          [p for p in phys if p["name"].startswith("P9")], "information", True)
    R.data = {"prompt": PROMPT, "qpu_seconds": 0, "hqc": 0, "ctx_data": ctx.data, "phases": ctx.phases,
              "physics_information": phys, "notes": ctx.notes, "wall_s": time.time() - t0, "environment": env_record(),
              "expected_token_content": "4 circuits, 57 shots in all at 51.9 s/shot (data/campaign33/engines.json C3_LE.reason)",
              "campaign33_files_written": "none (Ctx creates only the gitignored results/campaign33/dryrun/C3_LE dir)"}
    return write_gate(R, f"# QEMU_2x3_laptop_smoke\n\nStatus: **{'PASS' if R.passed else 'FAIL'}**.\n\n" + R.criteria_table() + "\n")


def pecos_2x4():
    from skqd.report import GateResult
    eng = load_json(os.path.join(ROOT, "data", "campaign33", "engines.json"))
    sps20 = eng["C3_LE"]["probes"]["pecos_idle"]["seconds_per_shot"]
    q = load_json(os.path.join(ROOT, "validation", "Q0P_2x4.json"))["data"]["frozen"]["index_summary"]
    dev = load_json(os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json"))["specs"]["quantinuum_h1_1"]
    R = GateResult("QEMU_2x4", "2x4 on the local emulator H2-1LE: infeasible (prompts/35 3.6)")
    R.data = {"status_note": "infeasible", "prompt": PROMPT, "qpu_seconds": 0, "hqc": 0,
              "numbers": {"seconds_per_shot_20_qubits_2158_zz": sps20, "source": "data/campaign33/engines.json C3_LE.probes.pecos_idle",
                          "zz_2x4_frozen": q["n_zz"], "zz_2x3": 2158,
                          "zz_ratio": q["n_zz"]["mean"] / 2158.0, "amplitude_ratio": 2 ** 8,
                          "emulator_model_qubits": dev["qubits"], "needed_qubits": 28},
              "sentence": (f"at 20 qubits the emulator needs {sps20:.1f} s per shot for 2158 ZZ; the 2x4 k = 1 circuit has "
                           f"{q['n_zz']['mean'] / 2158.0:.1f}x the two-qubit gates on 2^8 = 256x the amplitudes, i.e. hours "
                           f"per shot, and the H2-1LE models a {dev['qubits']}-qubit machine (devices_20261002.json "
                           f"specs.quantinuum_h1_1), which cannot hold 28")}
    out = {"gate": "QEMU_2x4", "title": R.title, "status": "infeasible", "criteria": [], "data": R.data,
           "runtime_s": 0.0}
    from skqd.report import environment, write_report
    out["environment"] = environment()
    with open(os.path.join(ROOT, "validation", "QEMU_2x4.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    write_report("QEMU_2x4.md", f"# QEMU_2x4 — {R.title}\n\nStatus: **infeasible** (no criteria).  {R.data['sentence']}.\n")
    print("QEMU_2x4: infeasible ->", R.data["sentence"])
    return 0


# --------------------------------------------------------------------------- tier: hugr (pecos venv)
HUGR_TEMPLATE = '''# generated by scripts/quantinuum_lattice_tests.py --tier hugr (prompts/35 3.7); one circuit per module
import json
from pytket import Circuit
from guppylang import guppy
from guppylang.std.builtins import array, result
from guppylang.std.quantum import qubit, discard_array

circ_fn = guppy.load_pytket("circ_fn", Circuit.from_dict(json.loads(open(%(path)r).read())))


@guppy
def main() -> None:
    q = array(qubit() for _ in range(%(n)d))
    bits = circ_fn(q)
    result("c", bits)
    discard_array(q)
'''
HUGR_EXT_NOTE = ("guppylang 0.21.16 `main.compile()` lists only the extensions it resolves itself; load_pytket "
                 "(tket 0.13.2 CompilationState.from_tket1) emits PhasedX and ZZPhase as ops of `tket.qsystem.helios`, "
                 "which neither selene-hugr-qis-compiler 0.2.11 nor tket's own registry carry, so the package is written "
                 "with that extension embedded (tket_exts 0.12.4 `qsystem_helios()`), the way tket's "
                 "CircBuild.finish_package packages it; the raw compile() output is recorded by its sha256")


def hugr_one(lat, cid, out_dir, n_shots, seed):
    """One circuit: Guppy program -> HUGR package (+ the helios extension) -> Selene Quest -> counts."""
    import importlib.util
    import tempfile

    import selene_sim
    import tket_exts
    from hugr.package import Package
    rec = {"id": cid}
    t0 = time.time()
    _idx, mans, cals = family(lat)
    m = mans.get(cid) or cals[cid]
    jpath = os.path.join(circ_dir(lat), m["files"]["json"])
    text = read_frozen(lat, m["files"]["json"])
    rec["json_sha256_ok"] = sha256_text(text) == m["json_sha256"]
    src = HUGR_TEMPLATE % {"path": jpath, "n": int(m["n_qubits"])}
    with tempfile.TemporaryDirectory() as td:
        mp_ = os.path.join(td, f"guppy_{cid.lower()}.py")
        with open(mp_, "w") as fh:
            fh.write(src)
        spec = importlib.util.spec_from_file_location(f"guppy_{cid.lower()}", mp_)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            pkg = mod.main.compile()
        except Exception as exc:
            rec.update({"load_or_compile_error": f"{type(exc).__name__}: {str(exc)[:800]}", "ok": False})
            return rec
    rec["program_template_sha256"] = sha256_text(HUGR_TEMPLATE)
    rec["compile_s"] = time.time() - t0
    raw_json = pkg.to_json()
    rec["raw_compile_package_sha256"] = sha256_text(raw_json)
    helios = tket_exts.qsystem_helios()
    pkg2 = Package(modules=pkg.modules, extensions=list(pkg.extensions) + [helios])
    js = pkg2.to_json()
    os.makedirs(out_dir, exist_ok=True)
    hp = os.path.join(out_dir, cid + ".hugr.json.gz")
    with open(hp + ".tmp", "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as fh:
            fh.write(js.encode())
    os.replace(hp + ".tmp", hp)
    rec.update({"hugr_file": rel(hp), "hugr_sha256": sha256_text(js), "hugr_sha256_of": "the uncompressed JSON",
                "package_extensions": [e.name for e in pkg2.extensions], "extension_note": HUGR_EXT_NOTE})
    # the round trip: tket (tket2) HUGR -> pytket
    rec["hugr_to_pytket"] = hugr_roundtrip(pkg2, text, int(m["n_qubits"]))
    # Selene
    t1 = time.time()
    try:
        inst = selene_sim.build(pkg2)
        rec["selene_build_s"] = time.time() - t1
        cnt, order = {}, None
        t2 = time.time()
        for shot in inst.run_shots(selene_sim.Quest(random_seed=int(seed)), n_qubits=int(m["n_qubits"]), n_shots=int(n_shots),
                                   error_model=selene_sim.IdealErrorModel(random_seed=int(seed)), random_seed=int(seed)):
            ent = list(shot)
            vals = [v for tag, v in ent if str(tag).split(":")[-1] == "c"]
            if len(vals) != 1:
                raise ValueError(f"cannot find the c register in {ent[:3]}")
            bits = [int(b) for b in vals[0]]
            x = int(sum(b << k for k, b in enumerate(bits)))         # list index k = c[k] (checked on CAL_x0)
            cnt[x] = cnt.get(x, 0) + 1
        rec.update({"selene_run_s": time.time() - t2, "shots": int(n_shots), "seed": int(seed),
                    "seconds_per_shot": (time.time() - t2) / max(1, n_shots),
                    "counts": {str(k): v for k, v in sorted(cnt.items())},
                    "decode_rule": "result('c', array[bool, n]): list index k = c[k] = qubit k (bit k of the key)"})
        rec["ok"] = True
    except Exception as exc:
        rec.update({"selene_error": f"{type(exc).__name__}: {str(exc)[:800]}", "ok": False})
    rec["wall_s"] = time.time() - t0
    return rec


def hugr_roundtrip(pkg2, json_text, n):
    """HUGR -> pytket through tket 0.13.2, compared with the frozen circuit by pytket_to_ir and the sparse statevector
    (numpy only; this env has no qiskit).  Two routes: the whole package (CompilationState.from_python(...).to_tket1())
    and the circuit's own HUGR (from_tket1 -> bytes -> from_bytes -> to_tket1).  A route whose result is not the
    n-qubit circuit is recorded as not available, with the reason."""
    from pytket import Circuit

    from skqd import quantinuum_native as qn
    from skqd.sparse_sim import run_sparse
    c0 = Circuit.from_dict(json.loads(json_text))
    out, got = {}, None
    try:
        from tket._state import CompilationState
        c_rt = CompilationState.from_python(pkg2).to_tket1()
        if c_rt.n_qubits == n:
            got = ("package", c_rt)
        else:
            out["package_route"] = (f"to_tket1() of the package returns a {c_rt.n_qubits}-qubit circuit with "
                                    f"{len(c_rt.get_commands())} commands (the entry point allocates its qubits; the loaded "
                                    f"pytket function is not extracted)")
    except Exception as exc:
        out["package_route"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    if got is None:
        try:
            from tket._state import CompilationState
            c_rt = CompilationState.from_bytes(CompilationState.from_tket1(c0).to_bytes()).to_tket1()
            got = ("circuit", c_rt)
        except Exception as exc:
            lines = str(exc).splitlines()
            out["circuit_route"] = f"{type(exc).__name__}: {(lines[-1] if lines else '')[:300]}"
    if got is None:
        out["status"] = ("not available in tket 0.13.2 (package route: " + out.get("package_route", "") + "; circuit route: "
                         + out.get("circuit_route", "") + ")")
        return out
    try:
        ir0, n0, _ = qn.pytket_to_ir(c0)
        ir1, n1, q1 = qn.pytket_to_ir(got[1])
        out["route"] = got[0]
        if n0 <= 20 and n1 == n0:
            out["statevector_vs_frozen"] = qn.global_phase_residual(run_sparse(ir1, n1).dense(), run_sparse(ir0, n0).dense())
        out["ops"] = {k: int(v) for k, v in qn.native_counts(got[1])["ops"].items()}
        out["measure_map"] = {str(k): v for k, v in q1.items()}
        out["status"] = "ok"
    except Exception as exc:
        out["status"] = f"read back but not comparable ({type(exc).__name__}: {str(exc)[:300]})"
    return out


def tier_hugr(args):
    lat = args.lattice
    if lat == 4:
        from skqd.report import environment, write_report
        out = {"gate": "QH_2x4", "title": "2x4 Helios Guppy/HUGR + Selene: not attempted (prompts/35 3.7)",
               "status": "not attempted", "criteria": [],
               "data": {"prompt": PROMPT, "qpu_seconds": 0, "hqc": 0,
                        "reason": ("a 28-qubit Quest statevector is 2^28 complex128 = 4.3 GB per state on this laptop's CPU, "
                                   "the cost R2 rules out (validation/S2_2x4.json data.dense.requirement)")},
               "runtime_s": 0.0, "environment": environment()}
        with open(os.path.join(ROOT, "validation", "QH_2x4.json"), "w") as fh:
            json.dump(out, fh, indent=1)
        write_report("QH_2x4.md", f"# QH_2x4 — not attempted\n\n{out['data']['reason']}.\n")
        print("QH_2x4: not attempted")
        return 0
    G = "QH_2x2" if lat == 2 else "QH_2x3"
    idx, mans, cals = family(lat)
    ids = sorted(idx["circuits"]) if lat == 2 else ["B0_ref25_k1", "B1_ref57_k1"]
    out_dir = os.path.join(ROOT, "data", "quantinuum", f"circuits_2x{lat}_helios")
    part = args.part or "all"
    if part == "rate":
        rec = hugr_one(lat, ids[0], out_dir, 100 if lat == 2 else 3, SEED_T6 + 999)
        save_frag(G, "rate", rec)
        print(f"  rate: {rec.get('seconds_per_shot')} s/shot, compile {rec.get('compile_s')} s", flush=True)
        return assemble_QH(lat)
    todo = list(args.only or (["CAL_x0"] + ids))
    for cid in todo:
        if frag(G, f"circuit_{cid}") and not args.force:
            continue
        c_i = ids.index(cid) if cid in ids else 900
        n = int(args.shots or hugr_shots(frag(G, "rate"), lat))
        if cid == "CAL_x0":
            n = 10
        rec = hugr_one(lat, cid, out_dir, n, SEED_T6 + c_i)
        if rec.get("ok") and cid in mans:
            P = _PHYS.setdefault(lat, Phys(lat))
            cnt = {int(k): v for k, v in rec["counts"].items()}
            rec["per_state"] = per_state(cnt, P.exact(mans[cid]), n)
            rec["reference_hits"] = int(cnt.get(int(mans[cid]["reference_int"]), 0))
        save_frag(G, f"circuit_{cid}", rec)
        print(f"  {cid}: ok {rec.get('ok')} {rec.get('seconds_per_shot')} s/shot "
              f"{(rec.get('per_state') or {}).get('max_z')} {rec.get('selene_error') or rec.get('load_or_compile_error') or ''}",
              flush=True)
    write_helios_index(lat, out_dir, G)
    return assemble_QH(lat)


_PHYS = {}
HUGR_PLAN = {2: {"circuits": 28, "cap_s": 3600.0, "planned_shots": 2000},     # prompts/35 3.7 and the caps of section 2
             3: {"circuits": 2, "cap_s": 1800.0, "planned_shots": 100}}


def hugr_shots(rt, lat):
    """Shots per circuit inside the tier's cap from the measured rate: floor((cap - (circuits + 1) x per-circuit
    overhead) / (circuits x s_shot)), at most the planned shots, rounded down to 100 when >= 100, floor 20."""
    if not rt or not rt.get("seconds_per_shot"):
        raise SystemExit("run --part rate first (prompts/35 3.7: measure the rate first)")
    p = HUGR_PLAN[lat]
    over = float(rt.get("compile_s", 0.0)) + float(rt.get("selene_build_s", 0.0))
    n = int(math.floor((p["cap_s"] - (p["circuits"] + 1) * over) / (p["circuits"] * float(rt["seconds_per_shot"]))))
    n = min(p["planned_shots"], n)
    if n >= 100:
        n = (n // 100) * 100
    return max(20, n)


def write_helios_index(lat, out_dir, G):
    """index.json + one manifest per circuit in circuits_2x<L>_helios (read by quantinuum_submit.py --program hugr)."""
    _idx, mans, cals = family(lat)
    recs = {k[len("circuit_"):]: v for k, v in frags(G, "circuit_").items()}
    ok = {c: r for c, r in recs.items() if r.get("hugr_file")}
    if not ok:
        return
    os.makedirs(out_dir, exist_ok=True)
    for c, r in ok.items():
        m = mans.get(c) or cals[c]
        man = {k: m.get(k) for k in ("id", "kind", "sector", "twoB", "reference", "k", "n_qubits", "counts", "hqc_per_shot",
                                     "reference_int", "p_reference", "dt", "qasm_sha256", "json_sha256")}
        man.update({"files": {"hugr": os.path.basename(r["hugr_file"])}, "hugr_sha256": r["hugr_sha256"],
                    "source": f"data/quantinuum/circuits_2x{lat}/{m['files']['json']}", "program": "hugr"})
        with open(os.path.join(out_dir, c + ".manifest.json"), "w") as fh:
            json.dump(man, fh, indent=1)
    index = {"produced_by": "scripts/quantinuum_lattice_tests.py --tier hugr", "prompt": PROMPT, "lattice": f"2x{lat}",
             "program": "hugr", "circuits": sorted(c for c in ok if c in mans), "calibration": sorted(c for c in ok if c in cals),
             "files": {c: {"hugr": os.path.basename(r["hugr_file"]), "hugr_sha256": r["hugr_sha256"]} for c, r in ok.items()},
             "versions": versions(("guppylang", "hugr", "tket", "tket-exts", "selene-sim", "pytket")), "created": now()}
    with open(os.path.join(out_dir, "index.json"), "w") as fh:
        json.dump(index, fh, indent=1)


def assemble_QH(lat):
    from skqd.report import GateResult, md_table
    G = "QH_2x2" if lat == 2 else "QH_2x3"
    idx, mans, _ = family(lat)
    ids = sorted(idx["circuits"]) if lat == 2 else ["B0_ref25_k1", "B1_ref57_k1"]
    recs = {k[len("circuit_"):]: v for k, v in frags(G, "circuit_").items()}
    cal = recs.get("CAL_x0")
    per = {c: recs[c] for c in ids if c in recs}
    R = GateResult(G, f"2x{lat} native circuits as Helios Guppy/HUGR programs on Selene (Quest, IdealErrorModel), offline "
                      f"(prompts/35 T6{'' if lat == 2 else '; information'})")
    h1 = [c for c, r in per.items() if r.get("hugr_file") and r.get("hugr_sha256")]
    R.add(f"H1 {len(ids)}/{len(ids)} HUGR packages written with sha256", {"written": len(h1), "of": len(ids)},
          f"{len(ids)}", len(h1) == len(ids))
    nf = sum(len(r["per_state"]["failures"]) for r in per.values() if r.get("per_state"))
    outs = [r["per_state"]["fraction_outside_exact_support"] for r in per.values() if r.get("per_state")]
    ran = [c for c, r in per.items() if r.get("per_state")]
    cal_ok = bool(cal and cal.get("ok") and cal.get("counts") == {"1": cal.get("shots")})
    R.add("H2 Selene counts: per-state 5 sigma test 0 failures and fraction outside the exact support 0 on every circuit; "
          "bit order fixed by CAL_x0 (X on qubit 0 -> key 1)",
          {"ran": len(ran), "of": len(ids), "failures": nf, "max_outside": max(outs) if outs else None,
           "max_z": max([per[c]["per_state"]["max_z"] for c in ran] or [None] if ran else [None]),
           "CAL_x0_counts": (cal or {}).get("counts"), "errors": {c: r.get("selene_error") or r.get("load_or_compile_error")
                                                                  for c, r in per.items() if not r.get("ok")}},
          "0; 0; key 1", len(ran) == len(ids) and nf == 0 and outs and max(outs) == 0.0 and cal_ok)
    R.add("H3 the HUGR -> pytket round-trip field present (either form)",
          {c: (r.get("hugr_to_pytket") or {}).get("status") for c, r in list(per.items())[:4]},
          "present", all("hugr_to_pytket" in r for r in per.values()) and len(per) == len(ids))
    R.add("H4 hqc == 0", 0, "0", True)
    data = {"prompt": PROMPT, "qpu_seconds": 0, "hqc": 0, "ehqc": 0, "per_circuit": per, "CAL_x0": cal,
            "rate": frag(G, "rate"), "seed_rule": SEED_RULES["T6"], "extension_note": HUGR_EXT_NOTE,
            "shot_plan": dict(HUGR_PLAN[lat], shots_per_circuit=(hugr_shots(frag(G, "rate"), lat) if frag(G, "rate") else None),
                              rule=hugr_shots.__doc__.strip(), shots_used=sorted({r.get("shots") for r in per.values()})),
            "route": ("frozen pytket JSON -> guppy.load_pytket inside a @guppy main that allocates the qubits, calls it, "
                      "records result('c', bits) and discards the qubits -> main.compile() (HUGR package) -> "
                      "selene_sim.build -> run_shots(Quest, IdealErrorModel)"),
            "what_pass_means": ("the frozen native circuits survive the Helios Guppy/HUGR route offline and reproduce "
                                "their exact distributions on Selene; not a Helios device or Helios-1E statement")}
    if lat == 3:
        data["status_note"] = "information (prompts/35 3.7: H1-H4 on 2 circuits)"
    R.data = data
    L = [f"# Gate {G} — {R.title}", "", f"Status: **{'PASS' if R.passed else 'FAIL'}**.  Generated from `validation/{G}.json`.", "",
         f"What PASS means: \"{data['what_pass_means']}\".", "", f"Route: {data['route']}.  {HUGR_EXT_NOTE}.", "",
         "## Criteria", "", R.criteria_table(), "",
         md_table(["circuit", "shots", "s/shot", "max z", "outside", "reference hits", "round trip"],
                  [[c, r.get("shots"), fmt(r.get("seconds_per_shot")), fmt((r.get("per_state") or {}).get("max_z")),
                    (r.get("per_state") or {}).get("fraction_outside_exact_support"), r.get("reference_hits"),
                    (r.get("hugr_to_pytket") or {}).get("status", "")[:60]] for c, r in sorted(per.items())]), ""]
    return write_gate(R, "\n".join(L))


# --------------------------------------------------------------------------- tier: gpu-verify (token QV_2x4)
def tier_gpu_verify(args):
    """QV_2x4: per k = 1 2x4 native circuit (QPY v13 bundle) the Aer statevector on the GPU (cuStateVec) projected on the
    codewords against the exact coarse state (max abs(dpsi) up to phase, leakage), then noiseless measure sampling at 6250
    shots and the per-state 5 sigma test (p_s >= 1e-3).  --dry-run: --lattice 2 on the CPU, same JSON structure."""
    from qiskit_aer import AerSimulator

    from skqd.campaign33 import circuits as C
    from skqd.hpc import ci_context, gpu_count, gpu_telemetry, slurm_layout
    from skqd.report import GateResult
    lat = args.lattice
    dry = bool(args.dry_run)
    t0 = time.time()
    phases = {}
    ci = ci_context()
    avail = list(AerSimulator().available_devices())
    device = "GPU" if ("GPU" in avail and not dry) else "CPU"
    idx, mans, _ = family(lat)
    ids = sorted(c for c in idx["circuits"] if int(mans[c]["k"]) == 1)
    if dry:
        ids = ids[:2] if lat == 2 else ids[:1]
    t = time.time()
    P = Phys(lat)
    phases["model_s"] = time.time() - t
    if lat == 4:
        import gate_S2_2x4 as S4   # noqa: F401  (the 2x4 dt is the manifest's, from validation/E3.json)
    from skqd.exact import mass_default
    from skqd.krylov import apply_groups, basis_vector, term_groups
    groups = term_groups(P.M.terms, G2, mass_default(G2))
    per, seeds = {}, {}
    t_ex, t_sa = 0.0, 0.0
    shots = QV_SHOTS if not dry else 200
    sim = AerSimulator(method="statevector", precision="double", device=device,
                       **({"cuStateVec_enable": True} if device == "GPU" else {"max_parallel_threads": int(args.threads)}))
    for c_i, cid in enumerate(ids):
        m = mans[cid]
        qc, e = load_native_qiskit(lat, cid)
        t = time.time()
        psi_q = C.statevector(qc, device=device, threads=int(args.threads))
        psi_ex = apply_groups(groups, basis_vector(P.M.basis.dim, int(m["reference"])), int(m["k"]) * float(m["dt"]))
        ex = C.exactness(psi_q, psi_ex, P.emb, C.measure_map(qc) == {i: i for i in range(P.n)})
        del psi_q
        t_ex += time.time() - t
        t = time.time()
        seed = SEED_QV + c_i
        res = sim.run(qc, shots=int(shots), seed_simulator=seed).result()
        from skqd.campaign33.sampling import counts_to_int
        cnt = counts_to_int(res.get_counts(0))
        probs = {int(P.emb.ints[i]): float(abs(psi_ex[i]) ** 2) for i in P.sector[int(m["twoB"])]["indices"]}
        ps = per_state(cnt, probs, int(shots))
        t_sa += time.time() - t
        per[cid] = {"exactness": ex, "per_state": ps, "seed": seed, "shots": int(shots), "qpy_gz_sha256": e["gz_sha256"]}
        seeds[cid] = seed
        print(f"  {cid}: dpsi {ex['max_abs_dpsi_up_to_phase']:.2e} leak {ex['leakage']:.2e} max z {ps['max_z']:.2f} "
              f"[{time.time() - t0:.0f} s]", flush=True)
    phases.update({"exactness_s": t_ex, "sampling_s": t_sa})
    wall = time.time() - t0
    tel = gpu_telemetry() if device == "GPU" else None
    gate = "QV_2x4" if not dry else "dryrun/QV_2x4"
    R = GateResult(gate, ("DRY RUN (laptop CPU path check at 2x2): " if dry else "")
                   + "the 15 native k = 1 2x4 circuits: Aer GPU statevector vs the exact coarse states and noiseless "
                     "per-state sampling (prompts/35 token QV_2x4)")
    dmax = max(v["exactness"]["max_abs_dpsi_up_to_phase"] for v in per.values())
    lmax = max(v["exactness"]["leakage"] for v in per.values())
    nf = sum(len(v["per_state"]["failures"]) for v in per.values())
    R.add("V1 max abs(dpsi) (up to phase) < 1e-10 and leakage < 1e-9 on every circuit (projected on the codewords)",
          {"circuits": len(per), "max_abs_dpsi": dmax, "max_leakage": lmax}, "< 1e-10; < 1e-9",
          dmax < 1e-10 and lmax < 1e-9 and all(v["exactness"]["ok"] for v in per.values()))
    R.add("V2 noiseless per-state 5 sigma test (p_s >= 1e-3) at %d shots, 0 failures; 0 outside the exact support" % shots,
          {"failures": nf, "max_z": max(v["per_state"]["max_z"] for v in per.values()),
           "max_outside": max(v["per_state"]["fraction_outside_exact_support"] for v in per.values())},
          "0; 0", nf == 0 and max(v["per_state"]["fraction_outside_exact_support"] for v in per.values()) == 0.0)
    run = {"engine": f"AerSimulator statevector double, device {device}" + (", cuStateVec" if device == "GPU" else ""),
           "device": device, "available_devices": avail, "gpus": (gpu_count(slurm_layout()) if device == "GPU" else 0),
           "wall_s": wall, "phases": phases, "seconds_per_shot": t_sa / max(1, shots * len(per)),
           "peak_gpu_memory_mib": (tel or {}).get("peak_memory_mib"), "mean_gpu_utilization": (tel or {}).get("mean_utilization_pct"),
           "gpu_telemetry": tel, "required_gpu_memory_mb": 4096 if lat == 4 else None, "E_p": None,
           "ci": ci, "versions": versions(("qiskit", "qiskit-aer", "numpy", "scipy"))}
    R.add("V3 telemetry: wall, phases, s/shot, GPUs" + ("" if dry else ", peak GPU memory, utilisation (policy fields)"),
          {k: run[k] for k in ("wall_s", "seconds_per_shot", "gpus", "peak_gpu_memory_mib", "mean_gpu_utilization")},
          "present" + (" (GPU fields null on the CPU dry run)" if dry else ""),
          all(run[k] is not None for k in ("wall_s", "seconds_per_shot"))
          and (dry or (run["gpus"] == 1 and run["peak_gpu_memory_mib"] is not None and run["mean_gpu_utilization"] is not None)))
    R.data = {"prompt": PROMPT, "token": "QV_2x4", "dry_run": dry, "lattice": f"2x{lat}", "qpu_seconds": 0, "hqc": 0,
              "per_circuit": per, "seeds": seeds, "seed_rule": SEED_RULES["QV_2x4"], "run": run,
              "inputs": rel(qpy_dir(lat)) + "/index.json"}
    if dry:
        os.makedirs(os.path.join(ROOT, "validation", "dryrun"), exist_ok=True)
        os.makedirs(os.path.join(ROOT, "reports", "dryrun"), exist_ok=True)
    return write_gate(R, f"# {gate}\n\nStatus: **{'PASS' if R.passed else 'FAIL'}**.\n\n" + R.criteria_table() + "\n")


# --------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lattice", type=int, choices=(2, 3, 4), required=True)
    ap.add_argument("--tier", required=True, choices=("export", "noiseless", "noise", "pecos", "hugr", "gpu-verify", "assemble"))
    ap.add_argument("--part", default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--shots", type=int, default=None)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--budget-s", type=float, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.tier == "export":
        return tier_export(args)
    if args.tier == "noiseless":
        return tier_noiseless(args)
    if args.tier == "noise":
        return tier_noise(args)
    if args.tier == "pecos":
        return tier_pecos(args)
    if args.tier == "hugr":
        return tier_hugr(args)
    if args.tier == "gpu-verify":
        return tier_gpu_verify(args)
    if args.lattice == 2:
        return assemble_QN_2x2()
    return assemble_QN_2x4()


if __name__ == "__main__":
    sys.exit(main())
