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
              "T4": "35 100 000 + c", "T6": "35 500 000 + c", "QV_2x4": "no random numbers in slot runs (statevectors only); the dry run's sampling is not used"}
N_T2 = 20000
N_FCELL = 2000
N_SIGMA, P_MIN = 5.0, 1e-3
SCENARIOS = ("E1", "E2", "E3", "E4", "E5a", "E5b", "E5c", "E6a", "E6b", "E6c", "E7_0.10_lat")
POR_ORDER = ("E1", "E3", "E4", "E5b", "E7_0.10_lat", "E2", "E6a", "E6b", "E6c", "E5a", "E5c")
POR_RUN = ("E1", "E3", "E4", "E5b")          # prompts/35a R3: the plan-of-record runs, in this order
POR_DROPPED = tuple(x for x in POR_ORDER if x not in POR_RUN)
CAP_T3_S_35A = 10 * 3600.0                   # prompts/35a R3
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
                  "por_estimate_s_per_scenario": worst * por, "cap_s": CAP_T3_S_35A, "por_runs": list(POR_RUN),
                  "predicted_total_s": worst * (N_FCELL * len(ids) * len(SCENARIOS) + len(POR_RUN) * por),
                  "rule": "estimates at the dearer of the two measured rates (E5b, the memory transform)"}
        save_frag("QN_2x2", "noise_rate", {"rates": out, "sizing": sizing, "threads": args.threads,
                                          "aer_settings": NOISY_SIM_KW(args.threads),
                                          "environment": env_record()})
        return assemble_QN_2x2()
    if part == "fcells":
        sids = args.scenarios or list(SCENARIOS)
        for sid in sids:
            if frag("QN_2x2", f"fcells_{sid}"):
                continue
            if args.budget_s and time.time() - t0 > float(args.budget_s):
                print(f"  budget reached before f-cells {sid}", flush=True)
                break
            s_i = SCENARIOS.index(sid)
            spec = spec_of(sid, P.n, mans, lat)
            # resumable across <= 30-min commands: finished cells are kept in fcpartial_<sid> until all 28 exist
            part_ = frag("QN_2x2", f"fcpartial_{sid}") or {"cells": {}, "wall_s": 0.0}
            cells, wall = dict(part_["cells"]), time.time()
            for c_i, cid in enumerate(ids):
                if cid in cells:
                    continue
                if args.budget_s and time.time() - t0 > float(args.budget_s):
                    break
                m = mans[cid]
                qc, _ = load_native_qiskit(lat, cid)
                seed = SEED_FC + 1000 * s_i + c_i
                cnt, dt = run_noisy(spec, qc, N_FCELL, seed, args.threads)
                cells[cid] = fcell(P, m, cnt, N_FCELL, spec, qc, seed, dt)
                save_frag("QN_2x2", f"fcpartial_{sid}", {"cells": cells, "wall_s": float(part_["wall_s"]) + time.time() - wall})
            if len(cells) < len(ids):
                print(f"  f-cells {sid}: {len(cells)} of {len(ids)} circuits (budget), resumable", flush=True)
                break
            wall_total = float(part_["wall_s"]) + time.time() - wall
            save_frag("QN_2x2", f"fcells_{sid}", {"scenario": sid, "description": N.describe(spec) if hasattr(N, "describe") else spec.description,
                                                 "cells": cells, "wall_s": wall_total, "shots_per_cell": N_FCELL,
                                                 "seed_rule": SEED_RULES["T3_fcells"], "threads": args.threads,
                                                 "aer_settings": NOISY_SIM_KW(args.threads),
                                                 "environment": env_record()})
            pp = os.path.join(FRAG, "QN_2x2", f"fcpartial_{sid}.json")
            if os.path.exists(pp):
                os.remove(pp)
            print(f"  f-cells {sid}: {len(cells)} circuits in {wall_total:.0f} s", flush=True)
        return assemble_QN_2x2()
    if part == "por":
        sids = args.scenarios or list(POR_RUN)
        bad = [x for x in sids if x not in POR_RUN]
        if bad:
            raise SystemExit(f"prompts/35a R3: the plan-of-record runs are {POR_RUN}; {bad} are dropped")
        plan = plan_of_record()
        for sid in sids:
            if frag("QN_2x2", f"por_{sid}"):
                continue
            s_i = SCENARIOS.index(sid)
            spec = spec_of(sid, P.n, mans, lat)
            # resumable across <= 30-min chunks: per-circuit counts are kept in porpartial_<sid> until all 28 exist
            part_ = frag("QN_2x2", f"porpartial_{sid}") or {"counts": {}, "seeds": {}, "wall_s": 0.0}
            wall = time.time()
            stopped = False
            for c_i, cid in enumerate(ids):
                if cid in part_["counts"]:
                    continue
                if args.budget_s and time.time() - t0 > float(args.budget_s):
                    stopped = True
                    break
                qc, _ = load_native_qiskit(lat, cid)
                seed = SEED_POR + 1000 * s_i + c_i
                cnt, _dt = run_noisy(spec, qc, plan[cid], seed, args.threads)
                part_["counts"][cid] = {str(k): int(v) for k, v in cnt.items()}
                part_["seeds"][cid] = seed
                part_["wall_s"] = float(part_["wall_s"]) + _dt
                save_frag("QN_2x2", f"porpartial_{sid}", part_)
            if stopped or len(part_["counts"]) < len(ids):
                print(f"  plan of record {sid}: {len(part_['counts'])} of {len(ids)} circuits (budget), resumable", flush=True)
                break
            counts = {c: {int(k): v for k, v in part_["counts"][c].items()} for c in ids}
            rd = skqd_reading(P, counts, mans)
            save_frag("QN_2x2", f"por_{sid}", {"scenario": sid, "reading": rd, "seeds": part_["seeds"],
                                              "seed_rule": SEED_RULES["T3_plan_of_record"],
                                              "shots_total": int(sum(plan.values())), "wall_s": float(part_["wall_s"]),
                                              "seconds_per_shot": float(part_["wall_s"]) / sum(plan.values()),
                                              "threads": args.threads, "aer_settings": NOISY_SIM_KW(args.threads),
                                              "environment": env_record()})
            os.remove(os.path.join(FRAG, "QN_2x2", f"porpartial_{sid}.json"))
            print(f"  plan of record {sid}: " + "; ".join(f"{s} recall {v['recall_S999_B_all']:.3f} E_R-E0 "
                                                           f"{v['E_R_minus_E0_B_all']:.2e} acc {v['accepted_fraction']:.3f}"
                                                           for s, v in rd.items()), flush=True)
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
    the circuit read back from the frozen JSON) and the gate-only f per device, per source (prompts/35b R4: opt3,
    structured; E7 matched at each source's own mean counts); 0 shots.  Resumable: rows already computed are kept
    (a bare id of the pre-35b record is the opt-3 source)."""
    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    from skqd.campaign33 import noise as N
    lat = 4
    t0 = time.time()
    idx, mans, _ = family(lat)
    ids = sorted(idx["circuits"])
    prev = frag("QN_2x4", "analytic") or {}
    table = {}
    for c, row in (prev.get("f0") or {}).items():
        table[c + ".opt3" if (c not in mans and c + ".opt3" in mans) else c] = row
    by_src = {}
    for c, m in mans.items():
        by_src.setdefault(m.get("source", "opt3"), {})[c] = m
    for cid in ids:
        if cid in table:
            continue
        if args.budget_s and time.time() - t0 > float(args.budget_s):
            break
        m = mans[cid]
        c = qn.from_json(json.loads(read_frozen(lat, m["files"]["json"])))
        ir, n, _ = qn.pytket_to_ir(c)
        qc = cq.ir_to_qiskit(ir, n, measure=True)
        row = {}
        for sid in SCENARIOS:
            spec = spec_of(sid, n, by_src[m.get("source", "opt3")], lat)
            f0 = N.f0_quantinuum(qc, spec, ref_bits=m["reference_bits"])
            row[sid] = {"f0": f0["f0"], "g0": f0["g0"], "log10_f0": (math.log10(f0["f0"]) if f0["f0"] > 0 else None),
                        "n_2q": f0.get("n_2q"), "n_1q_noisy": f0.get("n_1q_noisy")}
        table[cid] = row
        save_frag("QN_2x4", "analytic_partial", {"f0": table})
        print(f"  {cid}: E1 f0 {row['E1']['f0']:.3e} [{time.time() - t0:.0f} s]", flush=True)
    import gate_Q0P_2x3 as GQ                 # the device rows of Q0P_2x4's predict stage, computed here from the same
    devices = {s_: GQ.device_rows_L(4, ms)[0] for s_, ms in by_src.items()}   # frozen counts, per source
    save_frag("QN_2x4", "analytic", {"f0": table, "scenarios": list(SCENARIOS), "devices_by_source": devices,
                                     "devices": devices.get("structured") or devices.get("opt3"),
                                     "devices_source": ("gate_Q0P_2x3.device_rows_L(4, manifests of one source) (the device "
                                                        "table's formula); `devices` = the structured source's rows when built"),
                                     "circuits_built": sorted(mans), "built_k": idx.get("built_k"),
                                     "sampled_shots": 0, "wall_s": float(prev.get("wall_s", 0.0)) + time.time() - t0,
                                     "environment": env_record(),
                                     "e7_counts": {s_: mean_counts(ms) for s_, ms in by_src.items()}})
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
        data["plan_of_record"] = dict(PR)
        data["scenarios_run"] = [s for s in POR_ORDER if s in PR]
        data["stop_variational"] = [s for s, ok in var.items() if not ok]
    else:
        R.add("N4 plan-of-record runs", "not run (--tier noise --part por)", "fields; variational", False)
    # prompts/35a R3: the dropped plan-of-record runs with their predicted cost (measured rates of noise_rate)
    rates_ = (RT or {}).get("rates") or {}
    por_shots = int(sum(plan_of_record().values()))
    pod = data.setdefault("plan_of_record", {})
    for sid in POR_DROPPED + tuple(x for x in POR_RUN if x not in PR):
        r_ = rates_.get("E5b" if sid.startswith("E5") else "E1", {}).get("s_per_shot")
        h = (por_shots * r_ / 3600.0) if r_ else None
        why = "dropped by prompts/35a" if sid in POR_DROPPED else "not run (yet): no completed plan-of-record fragment"
        pod[sid] = {"status": f"{why}: {h:.2f} h predicted" if h is not None else f"{why}: rate not measured",
                    "predicted_h": h, "shots": por_shots,
                    "rate_used": ("E5b" if sid.startswith("E5") else "E1") + " of data.rates"}
    walls = {"fcells_s": sum(float(v.get("wall_s", 0.0)) for v in FC.values()),
             "plan_of_record_s": sum(float(v.get("wall_s", 0.0)) for v in PR.values())}
    data["t3_cap"] = dict(walls, total_h=(walls["fcells_s"] + walls["plan_of_record_s"]) / 3600.0, cap_h=CAP_T3_S_35A / 3600.0,
                          rule="prompts/35a R3: f-cells 28 x 11, plan of record E1, E3, E4, E5b, 10 h")
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
            L += ["## Gate-only f per device (data.analytic.devices: the device table formula on the frozen counts)", "",
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
        la = os.getloadavg()
        rec = hugr_one(lat, ids[0], out_dir, 100 if lat == 2 else 3, SEED_T6 + 999)
        rec["load_average_before"] = list(la)
        save_frag(G, "rate", rec)
        print(f"  rate: {rec.get('seconds_per_shot')} s/shot, compile {rec.get('compile_s')} s", flush=True)
        return assemble_QH(lat)
    todo = list(args.only or (["CAL_x0"] + ids))
    plan = frag(G, "run_plan")
    if plan is None or args.force:
        # prompts/35a R5: size on the rate measured IMMEDIATELY before the run (2x2), the planned rule at 2x3
        la = os.getloadavg()
        rt = hugr_one(lat, ids[0], out_dir, 100 if lat == 2 else 3, SEED_T6 + 999)
        rt["load_average_before"] = list(la)
        save_frag(G, "rate", rt)
        n = hugr_shots(rt, lat)
        plan = {"shots_per_circuit": n, "rate_s_per_shot": rt["seconds_per_shot"], "load_average_before": list(la),
                "rule": (HUGR_RULE_R5 if lat == 2 else hugr_shots.__doc__.strip()), "measured_on": ids[0]}
        save_frag(G, "run_plan", plan)
        print(f"  run plan: {n} shots per circuit at {rt['seconds_per_shot']:.4f} s/shot (load {la})", flush=True)
    for cid in todo:
        if frag(G, f"circuit_{cid}") and not args.force:
            continue
        c_i = ids.index(cid) if cid in ids else 900
        n = 10 if cid == "CAL_x0" else int(plan["shots_per_circuit"])
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
HUGR_RULE_R5 = ("prompts/35a R5: shots per circuit = min(2000, floor(3600 / (28 s_shot))), floor 500, s_shot measured on 100 "
                "shots immediately before the run")
HUGR_PLAN = {2: {"circuits": 28, "cap_s": 3600.0, "planned_shots": 2000},     # prompts/35 3.7 and the caps of section 2
             3: {"circuits": 2, "cap_s": 1700.0, "planned_shots": 100}}   # 2x3: per circuit, one command each


def hugr_shots(rt, lat):
    """2x2: prompts/35a R5, min(2000, floor(3600 / (28 s_shot))), floor 500.  2x3 (information, prompts/35 3.7 '100 shots
    each or what 30 min allows'): one circuit per command, floor((1700 s - overhead) / s_shot), at most 100, floor 1."""
    if not rt or not rt.get("seconds_per_shot"):
        raise SystemExit("measure the rate first (prompts/35 3.7)")
    s = float(rt["seconds_per_shot"])
    if lat == 2:
        return max(500, min(2000, int(math.floor(3600.0 / (28.0 * s)))))
    p = HUGR_PLAN[lat]
    over = float(rt.get("compile_s", 0.0)) + float(rt.get("selene_build_s", 0.0))
    n = int(math.floor((p["cap_s"] - over) / s))      # ONE circuit per <= 30-min command (2x3: Selene ~1e2 s/shot)
    return max(1, min(p["planned_shots"], n))


def hugr_stack_block():
    """prompts/35a R5: the HUGR packaging fix as a stack-check block -- the pecos venv's pip freeze (nothing is installed
    by prompts/35 / 35a: the fix embeds an extension definition that the installed tket-exts already ships), the
    extension added to every package and the error it fixed.  Only in the pecos venv; nothing in `coding` or the
    quantinuum venv."""
    r = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
    fr = sorted(line for line in r.stdout.splitlines() if line.strip())
    out = {"venv": sys.prefix, "pip_freeze_sha256": sha256_text("\n".join(fr)), "pip_freeze_n": len(fr),
           "pip_freeze": fr, "packages_installed_by_prompts_35_35a": [],
           "pip_freeze_before_equals_after": "yes by construction: no pip command was run in this venv under prompts/35/35a",
           "fix": HUGR_EXT_NOTE,
           "error_fixed": ("selene_hugr_qis_compiler.HugrReadError: Error loading HUGR package. OpaqueOp:"
                           "tket.qsystem.helios.ZZPhase requires extension tket.qsystem.helios, but it could not be found "
                           "in the extension list used during resolution (selene_sim.build of the raw main.compile())"),
           "scope": "the pecos venv (~/.local/share/su2qc-pecos/venv) only"}
    try:
        import tket_exts
        e = tket_exts.qsystem_helios()
        out["extension_added"] = {"name": e.name, "version": str(e.version), "from": f"tket-exts {versions(('tket-exts',))['tket-exts']}"}
    except Exception as exc:
        out["extension_added"] = f"not importable here ({type(exc).__name__})"
    return out


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
            "run_plan": frag(G, "run_plan"),
            "shot_plan": dict(HUGR_PLAN[lat], rule=(HUGR_RULE_R5 if lat == 2 else hugr_shots.__doc__.strip()),
                              shots_used=sorted({r.get("shots") for r in per.values()}),
                              wall_s_total=sum(float(r.get("wall_s") or 0.0) for r in per.values())),
            "stack": hugr_stack_block(),
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
def native_qiskit_any(lat, cid, man):
    """The native circuit as a qiskit circuit: the QPY v13 bundle when it exists, else the frozen pytket JSON through
    the pytket-free reader (prompts/35a R1)."""
    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    ip = os.path.join(qpy_dir(lat), "index.json")
    if os.path.exists(ip) and cid in load_json(ip)["circuits"]:
        qc, e = load_native_qiskit(lat, cid)
        return qc, {"route": "QPY v13 bundle", "gz_sha256": e["gz_sha256"]}
    text = read_frozen(lat, man["files"]["json"])
    if sha256_text(text) != man["json_sha256"]:
        raise SystemExit(f"{cid}: frozen JSON sha256 mismatch")
    ir, n, qmap = qn.pytket_json_to_ir(json.loads(text))
    if qmap != {q: q for q in range(n)}:
        raise SystemExit(f"{cid}: measurement map is not q[k] -> c[k]")
    return cq.ir_to_qiskit(ir, n, measure=True), {"route": "frozen pytket JSON -> quantinuum_native.pytket_json_to_ir",
                                                   "json_sha256": man["json_sha256"]}


S_PER_INSTRUCTION_SRC = "validation/S2_2x4.json data.gpu_validation.telemetry_summary.s_per_instruction"
SLOT_SHARE, SLOT_WALL_S = 0.75, 3600.0
N_SLOTS = 8
PARTS_DIR = os.path.join(ROOT, "ci", "parts")


def s_per_instruction():
    return float(load_json(os.path.join(ROOT, "validation", "S2_2x4.json"))["data"]["gpu_validation"]
                 ["telemetry_summary"]["s_per_instruction"])


def slot01_ids():
    """B0_ref0_k1 and B1_ref0_k1 of prompts/35b (the first reference of each sector, k = 1) as base ids."""
    from skqd.exact import Model
    from skqd.krylov import references
    from quantinuum_build_circuits import circuit_id
    M = Model(4)
    return [circuit_id(tb, int(references(M.basis, tb)[0]), 1) for tb in (0, 2)], M


def tier_slots(args):
    """prompts/35b section 4 (venv: pytket + qiskit 2.5.2): the QPY v13 bundles of slot QV_2x4_01 -- per circuit
    (B0_ref0_k1, B1_ref0_k1) the opt-3-source native circuit, its opt-3 source (the prototype transpile), the
    structured-source native circuit and the structured IR itself -- plus the S2_2x4 reproduction circuit as committed;
    writes ci/parts/QV_2x4_01.json (the runs, the native/source pairs with their bound B, the prediction) and the
    placeholders QV_2x4_02..08 (filled after slot 01 chooses the source)."""
    from qiskit import transpile

    import gate_S2_2x4 as S4
    from quantinuum_build_circuits import TRANSPILE

    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    from skqd.campaign33.circuits import dump_qpy13, sha256_file
    t0 = time.time()
    base_ids, M = slot01_ids()
    S4._MODELS[4] = M
    idx, mans, _ = family(4)
    dts = {tb: float(S4.dt_of(4, tb)) for tb in (0, 2)}
    F = S4.preload_factory(4, "exact", sorted(set(dts.values())))
    out_dir = qpy_dir(4)
    os.makedirs(out_dir, exist_ok=True)
    spi = s_per_instruction()
    runs, pairs = [], []
    for base in base_ids:
        mo, ms = mans[base + ".opt3"], mans[base + ".structured"]
        gates = F.coarse_step(int(mo["reference"]), 1, dts[int(mo["twoB"])])
        src_struct = cq.ir_to_qiskit(gates, 28, measure=False)
        src_opt3 = transpile(src_struct, **TRANSPILE)
        if int(src_opt3.count_ops().get("rzz", 0)) != int(mo["counts"]["rzz_before"]):
            raise SystemExit(f"{base}: the re-transpiled opt-3 source differs from the build (rzz count)")
        items = []
        for src, m in (("opt3", mo), ("structured", ms)):
            c = qn.from_json(json.loads(read_frozen(4, m["files"]["json"])))
            if sha256_text(read_frozen(4, m["files"]["json"])) != m["json_sha256"]:
                raise SystemExit(f"{m['id']}: frozen JSON sha256 mismatch")
            ir, n, _ = qn.pytket_to_ir(c)
            items.append((f"{m['id']}:native", "native", src, cq.ir_to_qiskit(ir, n, measure=False), m))
        items.append((f"{base}.opt3:source", "source", "opt3", src_opt3, mo))
        items.append((f"{base}.structured:source", "source", "structured", src_struct, ms))
        for label, kind, src, qc, m in items:
            path = os.path.join(out_dir, label.replace(":", ".") + ".qpy.gz")
            rec = dump_qpy13(qc, path)
            runs.append({"label": label, "base_id": base, "kind": kind, "source": src, "qpy": rel(path),
                         "gz_sha256": rec["gz_sha256"], "qpy_header": rec["header"], "n_instructions": int(len(qc.data)),
                         "twoB": int(m["twoB"]), "reference": int(m["reference"]), "k": 1, "dt": float(m["dt"]),
                         "method": "save_statevector (full 2^28 vector)"})
            print(f"  {label}: {len(qc.data)} instructions [{time.time() - t0:.0f} s]", flush=True)
        ver = (load_json(os.path.join(ROOT, "data", "quantinuum", "q0p_stages_2x4", "verify.json"))
               if os.path.exists(os.path.join(ROOT, "data", "quantinuum", "q0p_stages_2x4", "verify.json")) else {})
        for src, m in (("opt3", mo), ("structured", ms)):
            if "rounding" in m.get("Q1L", {}):
                B, B_from = m["Q1L"]["rounding"]["state_bound_B"], f"data/quantinuum/circuits_2x4/{m['id']}.manifest.json Q1L.rounding"
            else:                              # opt-3 circuits built before 35a: B from the Q0P_2x4 verify record
                vr = (ver.get("per_circuit") or {})
                rec_ = vr.get(m["id"]) or vr.get(m.get("base_id", ""))
                if not rec_:
                    raise SystemExit(f"{m['id']}: no rounding bound (run gate_Q0P_2x3.py --lattice 4 --stage verify)")
                B, B_from = rec_["Q1L"]["rounding"]["state_bound_B"], "data/quantinuum/q0p_stages_2x4/verify.json per_circuit Q1L.rounding"
            pairs.append({"native": f"{m['id']}:native", "source": f"{m['id']}:source", "B": B, "B_from": B_from})
    s2 = load_json(os.path.join(ROOT, "validation", "S2_2x4.json"))["data"]["gpu_validation"]["compiled"]["B0_ref0_k1|all_to_all"]
    runs.append({"label": "S2_2x4:B0_ref0_k1|all_to_all", "base_id": base_ids[0], "kind": "reproduction", "source": "S2_2x4-cz",
                 "qpy": s2["file"], "gz_sha256": sha256_file(os.path.join(ROOT, s2["file"])),
                 "sha256_expected": s2["sha256"], "n_instructions": int(s2["n_instructions"]),
                 "twoB": 0, "reference": int(mans[base_ids[0] + ".opt3"]["reference"]), "k": 1, "dt": dts[0],
                 "expected_phase_aligned": float(s2["max_abs_difference_vs_coarse_states_phase_aligned"]),
                 "expected_from": "validation/S2_2x4.json data.gpu_validation.compiled['B0_ref0_k1|all_to_all']",
                 "method": "save_amplitudes on the codewords (the S2_2x4 method, gate_S2_2x4.py L1615-1648)"})
    pred = spi * sum(r["n_instructions"] for r in runs)
    part = {"slot": "QV_2x4_01", "prompt": "prompts/35b_2x4_exactness_ruling.md section 4", "lattice": "2x4",
            "content": "the decision job: which 2x4 source is frozen", "runs": runs, "pairs": pairs,
            "prediction": {"s_per_instruction": spi, "source": S_PER_INSTRUCTION_SRC, "predicted_s": pred,
                           "budget_s": SLOT_SHARE * SLOT_WALL_S, "fits": pred <= SLOT_SHARE * SLOT_WALL_S},
            "criteria": {
                "V1": "every run completed on the GPU with the policy telemetry",
                "V2": ("S2_2x4 reproduction: the committed CZ-basis circuit of S2_2x4 (data/S2_2x4/..._v13.qpy.gz) gives "
                       "max abs(dpsi) phase-aligned = the recorded 1.528e-9 to 1e-12 (same qiskit 1.4.3 / Aer 0.15.1). "
                       "Executor's note: prompts/35b section 4 names 'its opt-3 source' for this check, but the S2_2x4 "
                       "number belongs to the CZ-basis transpile, not to the rz/rx/ry/rzz opt-3 source of the Quantinuum "
                       "family; the S2_2x4 circuit is therefore run as its own reproduction run (the opt-3 source is run "
                       "and recorded as well)"),
                "V3": "native-vs-own-source max abs(dpsi) (full vector, phase removed) <= B + 1e-12 for both sources, else STOP",
                "V4": ("the frozen source is the one whose native circuits meet max abs(dpsi) < 1e-10 and leakage < 1e-9 "
                       "against krylov.coarse_states on both circuits; both -> the smaller maximum; neither -> STOP, the "
                       "planner rules in writing with the measured numbers")},
            "run_count_note": ("prompts/35b says 'six statevector runs' and lists four kinds per circuit for two circuits; "
                               "this part carries the eight listed runs plus the S2_2x4 reproduction run (nine)"),
            "created": now(), "git_commit": git_commit_short()}
    os.makedirs(PARTS_DIR, exist_ok=True)
    with open(os.path.join(PARTS_DIR, "QV_2x4_01.json"), "w") as fh:
        json.dump(part, fh, indent=1)
    for k in range(2, N_SLOTS + 1):
        p = os.path.join(PARTS_DIR, f"QV_2x4_{k:02d}.json")
        if not os.path.exists(p):
            with open(p, "w") as fh:
                json.dump({"slot": f"QV_2x4_{k:02d}", "prompt": "prompts/35b section 4", "runs": [], "pairs": [],
                           "status": ("placeholder: filled after QV_2x4_01 has chosen the source (the chosen source's "
                                      "remaining k = 1 circuits and, if built, k >= 2, with the per-state noiseless test)")},
                          fh, indent=1)
    print(f"ci/parts/QV_2x4_01.json: {len(runs)} runs, predicted {pred:.0f} s of {SLOT_SHARE * SLOT_WALL_S:.0f} s")
    return 0


def git_commit_short():
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() or "n/a"


def _statevector_gpu(qc, device, threads, ints=None):
    """Aer statevector (double; cuStateVec on the GPU) of the unitary part; with `ints` only those amplitudes."""
    from qiskit_aer import AerSimulator

    from skqd.campaign33 import circuits as C
    cc = C.unitary_part(qc)
    kw = dict(method="statevector", precision="double")
    if device == "GPU":
        kw.update(device="GPU", cuStateVec_enable=True)
    else:
        kw["max_parallel_threads"] = int(threads)
    sim = AerSimulator(**kw)
    if ints is None:
        cc.save_statevector()
        res = sim.run(cc, shots=1).result()
        return np.asarray(res.data(0)["statevector"].data), res
    cc.save_amplitudes([int(x) for x in ints])
    res = sim.run(cc, shots=1).result()
    return np.asarray(res.data(0)["amplitudes"], dtype=complex), res


def dry_part_2x2():
    """The same structure at 2x2 (laptop CPU path check): native QPY bundles and their IR sources for two k = 1
    circuits."""
    from gate_S2D import circuit_set
    from quantinuum_build_circuits import circuit_id
    _M, _F, cset = circuit_set(2)
    idx, mans, _ = family(2)
    ids = [c for c in sorted(idx["circuits"]) if c.endswith("_k1")][:2]
    runs, pairs = [], []
    for cid in ids:
        m = mans[cid]
        runs.append({"label": f"{cid}:native", "base_id": cid, "kind": "native", "source": "ir-opt3", "qpy": None,
                     "twoB": m["twoB"], "reference": m["reference"], "k": 1, "dt": m["dt"]})
        runs.append({"label": f"{cid}:source", "base_id": cid, "kind": "source", "source": "ir", "qpy": None,
                     "twoB": m["twoB"], "reference": m["reference"], "k": 1, "dt": m["dt"]})
        pairs.append({"native": f"{cid}:native", "source": f"{cid}:source", "B": None})
    gates = {circuit_id(*c[:3]): c[3] for c in cset}
    return {"slot": "dryrun-2x2", "runs": runs, "pairs": pairs}, gates, mans


def tier_gpu_verify(args):
    """Token QV_2x4_NN (prompts/35b section 4): the runs of ci/parts/QV_2x4_NN.json on the Aer GPU statevector --
    each against krylov.coarse_states (max abs(dpsi) up to phase on the codewords, leakage), the native-vs-own-source
    distances against B, the S2_2x4 reproduction -- and the frozen-source decision of slot 01 (V4).  --dry-run:
    --lattice 2 on the CPU, the same JSON structure."""
    from qiskit_aer import AerSimulator

    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    from skqd.campaign33 import circuits as C
    from skqd.campaign33.circuits import load_qpy, sha256_file
    from skqd.hpc import ci_context, gpu_count, gpu_telemetry, slurm_layout
    from skqd.report import GateResult
    lat = args.lattice
    dry = bool(args.dry_run)
    t0 = time.time()
    ci = ci_context()
    avail = list(AerSimulator().available_devices())
    device = "GPU" if ("GPU" in avail and not dry) else "CPU"
    slot = f"QV_2x4_{int(args.slot or 1):02d}"
    if dry:
        part, ir_by_id, mans = dry_part_2x2()
    else:
        part = load_json(os.path.join(PARTS_DIR, slot + ".json"))
        if not part.get("runs"):
            raise SystemExit(f"{slot}: no runs in ci/parts/{slot}.json ({part.get('status')})")
    P = Phys(lat)
    from skqd.exact import mass_default
    from skqd.krylov import apply_groups, basis_vector, term_groups
    groups = term_groups(P.M.terms, G2, mass_default(G2))
    exact_cache, per, vecs, phases = {}, {}, {}, {"load_s": 0.0, "statevector_s": 0.0, "compare_s": 0.0}
    keep = {p_[k] for p_ in part["pairs"] for k in ("native", "source")}
    for r in part["runs"]:
        t = time.time()
        if dry:
            base = r["base_id"]
            if r["kind"] == "native":
                qc, _e = load_native_qiskit(2, base)
            else:
                qc = cq.ir_to_qiskit(ir_by_id[base], P.n, measure=False)
            sha = None
        else:
            path = os.path.join(ROOT, r["qpy"])
            sha = sha256_file(path)
            if sha != r["gz_sha256"]:
                raise SystemExit(f"{r['label']}: QPY sha256 mismatch")
            qc = load_qpy(path)[0]
        phases["load_s"] += time.time() - t
        key = (int(r["twoB"]), int(r["reference"]), int(r["k"]))
        if key not in exact_cache:
            exact_cache[key] = apply_groups(groups, basis_vector(P.M.basis.dim, key[1]), key[2] * float(r["dt"]))
        psi_ex = exact_cache[key]
        t = time.time()
        if r["kind"] == "reproduction":
            amps, res = _statevector_gpu(qc, device, args.threads, ints=P.emb.ints)
            ov = complex(np.vdot(psi_ex, amps))
            rec = {"max_abs_dpsi_raw": float(np.abs(amps - psi_ex).max()),
                   "max_abs_dpsi_phase_aligned": float(np.abs(amps * np.exp(-1j * np.angle(ov)) - psi_ex).max()),
                   "leakage": float(1.0 - np.sum(np.abs(amps) ** 2))}
            rec["reproduces"] = abs(rec["max_abs_dpsi_phase_aligned"] - float(r["expected_phase_aligned"])) <= 1e-12
            rec["expected_phase_aligned"] = r["expected_phase_aligned"]
        else:
            sv, res = _statevector_gpu(qc, device, args.threads)
            ex = C.exactness(sv, psi_ex, P.emb, True)
            rec = {"max_abs_dpsi": ex["max_abs_dpsi_up_to_phase"], "leakage": ex["leakage"],
                   "meets_bar": bool(ex["max_abs_dpsi_up_to_phase"] < 1e-10 and ex["leakage"] < 1e-9)}
            if r["label"] in keep:
                vecs[r["label"]] = sv
            else:
                del sv
        phases["statevector_s"] += time.time() - t
        rec.update({"label": r["label"], "kind": r["kind"], "source": r["source"], "n_instructions": int(len(qc.data)),
                    "seconds": time.time() - t, "qpy_gz_sha256": sha,
                    "aer_success": bool(getattr(res, "success", True))})
        per[r["label"]] = rec
        print(f"  {r['label']}: {json.dumps({k: rec[k] for k in rec if k.startswith('max') or k == 'leakage'})} "
              f"[{time.time() - t0:.0f} s]", flush=True)
    t = time.time()
    pair_rec = []
    for p_ in part["pairs"]:
        a, b = vecs.get(p_["native"]), vecs.get(p_["source"])
        d = qn.global_phase_residual(a, b)["max_abs_dpsi"] if (a is not None and b is not None) else None
        B = p_.get("B")
        pair_rec.append({"native": p_["native"], "source": p_["source"], "max_abs_dpsi_native_vs_source": d, "B": B,
                         "consistent": (d is not None and (B is None or d <= B + 1e-12))})
    vecs.clear()
    phases["compare_s"] = time.time() - t
    wall = time.time() - t0
    tel = gpu_telemetry() if device == "GPU" else None
    gate = slot if not dry else f"dryrun/{slot}"
    R = GateResult(gate, ("DRY RUN (laptop CPU path check at 2x2): " if dry else "")
                   + f"{slot}: 2x4 native and source statevectors on the Aer GPU vs the exact coarse states (prompts/35b section 4)")
    run = {"engine": f"AerSimulator statevector double, device {device}" + (", cuStateVec" if device == "GPU" else ""),
           "device": device, "available_devices": avail, "gpus": (gpu_count(slurm_layout()) if device == "GPU" else 0),
           "wall_s": wall, "phases": phases, "seconds_per_shot": None,
           "s_per_instruction": phases["statevector_s"] / max(1, sum(v["n_instructions"] for v in per.values())),
           "peak_gpu_memory_mib": (tel or {}).get("peak_memory_mib"), "mean_gpu_utilization": (tel or {}).get("mean_utilization_pct"),
           "gpu_telemetry": tel, "E_p": None, "prediction": part.get("prediction"), "ci": ci,
           "versions": versions(("qiskit", "qiskit-aer", "numpy", "scipy"))}
    v1 = all(v["aer_success"] for v in per.values()) and len(per) == len(part["runs"]) and (
        dry or (device == "GPU" and run["gpus"] == 1 and run["peak_gpu_memory_mib"] is not None))
    R.add("V1 every run completed" + ("" if dry else " on the GPU with the policy telemetry"),
          {"runs": len(per), "of": len(part["runs"]), "device": device, "peak_gpu_memory_mib": run["peak_gpu_memory_mib"]},
          "all; GPU; telemetry", v1)
    repro = [v for v in per.values() if v["kind"] == "reproduction"]
    R.add("V2 S2_2x4 reproduction: max abs(dpsi) phase-aligned of the committed CZ-basis circuit = the recorded value to 1e-12",
          {v["label"]: [v["max_abs_dpsi_phase_aligned"], v["expected_phase_aligned"]] for v in repro} or "no reproduction run (dry)",
          "|measured - recorded| <= 1e-12", all(v["reproduces"] for v in repro) if repro else dry)
    v3 = all(p_["consistent"] for p_ in pair_rec)
    R.add("V3 native-vs-own-source max abs(dpsi) <= B + 1e-12 for both sources (else STOP: conversion or bound wrong)",
          [{k: p_[k] for k in ("native", "max_abs_dpsi_native_vs_source", "B")} for p_ in pair_rec], "<= B + 1e-12", v3)
    by_src = {}
    for v in per.values():
        if v["kind"] == "native":
            by_src.setdefault(v["source"], []).append(v)
    ok_src = {s_: all(v["meets_bar"] for v in vs) for s_, vs in by_src.items()}
    worst = {s_: max(v["max_abs_dpsi"] for v in vs) for s_, vs in by_src.items()}
    passing = [s_ for s_ in ok_src if ok_src[s_]]
    chosen = min(passing, key=lambda s_: worst[s_]) if passing else None
    R.add("V4 the frozen source: its native circuits meet max abs(dpsi) < 1e-10 and leakage < 1e-9 on both circuits "
          "(both -> the smaller maximum; neither -> STOP, the planner rules)",
          {"max_abs_dpsi_by_source": worst, "meets_bar": ok_src, "chosen": chosen}, "a source meets the bar", chosen is not None)
    R.data = {"prompt": "prompts/35b_2x4_exactness_ruling.md section 4", "token": slot, "dry_run": dry,
              "lattice": f"2x{lat}", "qpu_seconds": 0, "hqc": 0, "per_run": per, "pairs": pair_rec,
              "frozen_source": chosen, "run": run, "part": {k: v for k, v in part.items() if k != "runs"},
              "stop": (not v3) or chosen is None}
    if dry:
        os.makedirs(os.path.join(ROOT, "validation", "dryrun"), exist_ok=True)
        os.makedirs(os.path.join(ROOT, "reports", "dryrun"), exist_ok=True)
    return write_gate(R, f"# {gate}\n\nStatus: **{'PASS' if R.passed else 'FAIL'}**.\n\n" + R.criteria_table() + "\n")


def tier_qv_tokens(args):
    """prompts/35b section 4: the eight generic slots QV_2x4_01..08 in scripts/gate_tokens.json (the QV_2x4_K1..K4 of
    35a R1 removed), appended after the campaign-33 tokens; estimate_minutes of slot 01 from its part's prediction,
    the others the 45-min budget (their content is written after slot 01); ci/allowed_jobs.q35 with eight lines."""
    p = os.path.join(ROOT, "scripts", "gate_tokens.json")
    d = json.loads(open(p).read())
    head = [k for k in d if not k.startswith("QV_2x4")]
    out = {k: d[k] for k in head}
    p01 = os.path.join(PARTS_DIR, "QV_2x4_01.json")
    pred = load_json(p01)["prediction"]["predicted_s"] if os.path.exists(p01) else None
    for k in range(1, N_SLOTS + 1):
        t = f"QV_2x4_{k:02d}"
        est = int(math.ceil(pred / 60.0)) if (k == 1 and pred) else int(SLOT_SHARE * SLOT_WALL_S / 60.0)
        out[t] = {"script": "scripts/quantinuum_lattice_tests.py", "args": ["--lattice", "4", "--tier", "gpu-verify", "--slot", f"{k:02d}"],
                  "class": 3, "walltime": "01:00:00", "gpus": 1, "env": "skqd", "estimate_minutes": est,
                  "content": (f"prompts/35b section 4: generic 2x4 GPU slot {k:02d}; its runs are ci/parts/{t}.json in the "
                              f"requested commit" + (" (slot 01: the decision job, the frozen 2x4 source)" if k == 1 else "")
                              + "; appended after the campaign-33 tokens (indices and seeds unchanged); allowlist "
                              "ci/allowed_jobs.q35")}
    with open(p, "w") as fh:
        fh.write(json.dumps(out, indent=1))
    with open(os.path.join(ROOT, "ci", "allowed_jobs.q35"), "w") as fh:
        fh.write("".join(f"QV_2x4_{k:02d}   01:00:00 1\n" for k in range(1, N_SLOTS + 1)))
    print({k: v["estimate_minutes"] for k, v in out.items() if k.startswith("QV")})
    return 0


# --------------------------------------------------------------------------- tier: qsc (T5 prepared, venv)
QSC_SETS = (
    {"name": "QSC_2x2_H2-2SC", "device": "H2-2SC", "lattice": 2, "circuits": "data/quantinuum/circuits_2x2",
     "select": "all", "program": "pytket"},
    {"name": "QSC_2x3_H2-2SC", "device": "H2-2SC", "lattice": 3, "circuits": "data/quantinuum/circuits_2x3",
     "select": "all", "program": "pytket"},
    {"name": "QSC_2x4_opt3_H2-2SC", "device": "H2-2SC", "lattice": 4, "circuits": "data/quantinuum/circuits_2x4",
     "select": "k1:opt3", "program": "pytket"},
    {"name": "QSC_2x4_structured_H2-2SC", "device": "H2-2SC", "lattice": 4, "circuits": "data/quantinuum/circuits_2x4",
     "select": "k1:structured", "program": "pytket"},
    {"name": "QSC_2x2_Helios-1SC", "device": "Helios-1SC", "lattice": 2, "circuits": "data/quantinuum/circuits_2x2_helios",
     "select": "all", "program": "hugr"},
)
QSC_CRITERION = ("every circuit compiles on the syntax checker; the checker's ZZ count equals the frozen count (else the "
                 "no_opt=True resubmission rule of prompts/26 E1); 0 HQC (syntax checkers are free)")


def tier_qsc(args):
    """prompts/35 3.8: the four syntax-check job sets as LOCAL job records (quantinuum_submit.py --dry-run
    --records-only; no login, no network) -> validation/QSC_prepared.json (prepared: no status PASS is claimed)."""
    from skqd.report import environment, write_report
    py = sys.executable
    sets = []
    for s in QSC_SETS:
        out = os.path.join("data", "hardware", s["name"])
        cmd = [py, os.path.join(ROOT, "scripts", "quantinuum_submit.py"), "--dry-run", "--records-only",
               "--device", s["device"], "--circuits", s["circuits"], "--out", out, "--program", s["program"]]
        idx = load_json(os.path.join(ROOT, s["circuits"], "index.json"))
        if s["select"].startswith("k1"):         # prompts/35b: the 15 k = 1 circuits of one 2x4 source + calibration
            src = s["select"].split(":")[1]
            _i, mans_, _c = family(s["lattice"])
            cmd += (["--only"] + [c for c in idx["circuits"] if int(mans_[c]["k"]) == 1 and mans_[c].get("source") == src]
                    + list(idx.get("calibration", [])))
        else:
            cmd += ["--all"]
        sess_p = os.path.join(ROOT, out, "session.json")
        if not os.path.exists(sess_p):
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit(f"{s['name']}: {r.stderr[-800:]}")
        sess = load_json(sess_p)
        src_dir = s["circuits"] if s["program"] == "pytket" else f"data/quantinuum/circuits_2x{s['lattice']}"
        zz = {}
        for j in sess["jobs"]:
            m = load_json(os.path.join(ROOT, src_dir, j["circuit_id"] + ".manifest.json"))
            zz[j["circuit_id"]] = int(m["counts"]["n_zz"])
        owner_cmd = " ".join(["$V scripts/quantinuum_submit.py --syntax-check", "--device", s["device"], "--circuits",
                              s["circuits"]] + (["--program", "hugr"] if s["program"] == "hugr" else [])
                             + (["--all"] if s["select"] == "all" else ["--only", f"<the 15 k=1 {s['select'].split(':')[1]} ids + CAL_zeros CAL_x0>"])
                             + ["--out", f"data/hardware/{s['name']}"])
        sets.append({"name": s["name"], "device": s["device"], "program": s["program"], "circuits_dir": s["circuits"],
                     "session": rel(sess_p), "n_jobs": len(sess["jobs"]), "n_circuits": len({j["circuit_id"] for j in sess["jobs"]}),
                     "expected_zz_count_ours": zz, "hqc_estimate_if_it_were_a_device_run": sess["hqc_estimate_total"],
                     "records_only": sess.get("records_only"), "owner_command": owner_cmd})
    out = {"gate": "QSC_prepared", "title": "T5 syntax checks prepared (job records only; needs the owner's Nexus login)",
           "status": "prepared", "criteria": [],
           "data": {"prompt": PROMPT, "qpu_seconds": 0, "hqc": 0, "sets": sets, "criterion_for_the_owner_run": QSC_CRITERION,
                    "login_first": "~/.local/share/su2qc-quantinuum/venv/bin/python scripts/quantinuum_account.py --login",
                    "why_not_run": "no Nexus account (Q0P_2x3 data.stage_E.status 'not run'); syntax checkers are free but the "
                                   "account is the owner's to create (prompts/35 section 6 item 3)"},
           "runtime_s": 0.0, "environment": environment()}
    with open(os.path.join(ROOT, "validation", "QSC_prepared.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    from skqd.report import md_table
    write_report("QSC_prepared.md", "\n".join([
        "# QSC_prepared — T5 syntax checks prepared, not run", "",
        "Status: **prepared** (no PASS claimed).  Generated from `validation/QSC_prepared.json`.", "",
        f"Criterion for the owner's run: {QSC_CRITERION}.", "",
        md_table(["set", "device", "program", "circuits", "jobs", "owner command"],
                 [[x["name"], x["device"], x["program"], x["n_circuits"], x["n_jobs"], f"`{x['owner_command']}`"] for x in sets]), ""]))
    print("QSC_prepared:", [(x["name"], x["n_circuits"]) for x in sets])
    return 0


# --------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lattice", type=int, choices=(2, 3, 4), required=True)
    ap.add_argument("--tier", required=True, choices=("export", "noiseless", "noise", "pecos", "hugr", "gpu-verify", "qsc", "qv-tokens", "slots", "assemble"))
    ap.add_argument("--part", default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--shots", type=int, default=None)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--budget-s", type=float, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--slot", type=int, default=None, help="--tier gpu-verify: the slot NN of token QV_2x4_NN (prompts/35b)")
    ap.add_argument("--note", default=None, help="the reason recorded with an explicit --shots (hugr tier)")
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
    if args.tier == "qsc":
        return tier_qsc(args)
    if args.tier == "qv-tokens":
        return tier_qv_tokens(args)
    if args.tier == "slots":
        return tier_slots(args)
    if args.tier == "gpu-verify":
        return tier_gpu_verify(args)
    if args.lattice == 2:
        return assemble_QN_2x2()
    return assemble_QN_2x4()


if __name__ == "__main__":
    sys.exit(main())
