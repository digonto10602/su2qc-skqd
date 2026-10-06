#!/usr/bin/env python3
"""
prompts/33 A2: freeze every circuit family of the 2x3 campaign as QPY version 13 with manifests
(data/campaign33/circuits/<family>/<id>.{qpy.gz,json}) and the index (data/campaign33/circuits/index.json).

    python scripts/campaign33_freeze.py --family IR-L0 [--workers 6 --threads 2] [--only B0_ref25_k1 ...]
    ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/campaign33_freeze.py --family NAT-O0   (pytket)
    python scripts/campaign33_freeze.py --stage index
    ~/.local/share/su2qc-qiskit143/venv/bin/python scripts/campaign33_freeze.py --stage check143

Families (prompts/33 1.1 / 1.4): IR-L0 (the IR as built, no transpilation), NAT-O0 (the frozen pytket
level-0 Quantinuum circuits of gate Q0P_2x3, converted by skqd.quantinuum_native.pytket_to_ir),
NAT-O0-k5 (the k = 5 coarse step of every reference, same level-0 route, for CV3), NAT-O1 (pytket
FullPeepholeOptimise -> rebase -> RemoveRedundancies -> SquashRzPhasedX on the measurement-free
circuit), NAT-O2 / O3 / O4 (qiskit preset levels 1 / 2 / 3 on the measurement-free NAT-O0), NAT-O6
(pytket KAKDecomposition at cx_fidelity 0.999, information), IR-L3-RZZ (the gate-S3 transpilation),
IBM-T3 / IBM-T0 / IBM-U (the two K1 circuits as flown, without the XY4 pulses, unscheduled).

Every circuit is checked against the exact Krylov state (skqd.krylov.coarse_states, embedded by the
codeword map): max |dpsi| < 1e-10 after global-phase removal and leakage < 1e-9 (the project bars);
the first circuit of each family is cross-checked with qiskit.quantum_info.Statevector.  A base family
(IR-L0, NAT-O0, IBM-T3) failing the bar is a STOP (prompts/33 section 8): the script exits non-zero and
writes validation/BLOCKED.md.  Every circuit is written as soon as it is done (resumable; --force).
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.campaign33 import circuits as C  # noqa: E402

G2 = 4.0
S3_TRANSPILE = {"basis_gates": ["rz", "rx", "ry", "rzz"], "coupling_map": None, "optimization_level": 3,
                "seed_transpiler": 7}
Q0P_DIR = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
K1_DIR = os.path.join(ROOT, "data", "hardware", "K1_2x3_prep")
QISKIT_LEVEL = {"NAT-O2": 1, "NAT-O3": 2, "NAT-O4": 3}
FAMILY_TEXT = {
    "IR-L0": "the signed IR exactly as built (gate_S2D.circuit_set(3) / CircuitFactory(Model(3), 4.0).coarse_step), "
             "ir_to_qiskit with measure; no transpilation (unitary, cx, ry, p, cp, x executed natively by Aer)",
    "NAT-O0": "data/quantinuum/circuits_2x3/<id>.json (gate Q0P_2x3, pytket level 0 = pure rebase) -> "
              "skqd.quantinuum_native.pytket_to_ir (PhasedX -> rz, rx, rz; ZZPhase -> rzz) -> ir_to_qiskit",
    "NAT-O0-k5": "F.coarse_step(ref, 5, dt) -> transpile(basis rz/rx/ry/rzz, level 3, seed 7) -> ir_to_pytket -> "
                 "compile_native(H2-2, level 0, offline) -> pytket_to_ir -> ir_to_qiskit (the Q0P_2x3 route at k = 5)",
    "NAT-O1": "peephole resynthesis + 1q squashing: pytket FullPeepholeOptimise(allow_swaps=False, target_2qb_gate=TK2) "
              "-> AutoRebase({Rz, PhasedX, ZZPhase}) -> RemoveRedundancies -> SquashRzPhasedX on the measurement-free "
              "NAT-O0 circuit; measurements re-appended",
    "NAT-O2": "adjacent-gate collapsing: qiskit preset level 1, basis [rz, rx, ry, rzz], no coupling map, seed 7, on the "
              "measurement-free NAT-O0 circuit; measurements re-appended",
    "NAT-O3": "commutation-based cancellation: qiskit preset level 2 (same basis, seed 7), measurement-free; re-appended",
    "NAT-O4": "two-qubit peephole / unitary resynthesis: qiskit preset level 3, approximation_degree 1.0 (same basis, "
              "seed 7), measurement-free; re-appended",
    "NAT-O6": "approximate synthesis: pytket KAKDecomposition(target_2qb_gate=CX, cx_fidelity=0.999, allow_swaps=False) "
              "-> AutoRebase({Rz, PhasedX, ZZPhase}) -> RemoveRedundancies -> SquashRzPhasedX, measurement-free; "
              "information only by construction",
    "IR-L3-RZZ": "the circuits gate S3 sampled: transpile(ir_to_qiskit(ir, measure=True), basis [rz, rx, ry, rzz], "
                 "coupling_map None, optimization_level 3, seed_transpiler 7) (scripts/s3_device_model.py)",
    "IBM-T3": "the two K1 circuits as flown (routed on the 2026-10-06 ibm_kingston record, ALAP delays, client XY4 "
              "cell T3): data/hardware/K1_2x3_prep/circuits/<id>.qpy.gz re-written at QPY 13",
    "IBM-T0": "IBM-T3 with every inserted XY4 operation replaced by a delay of its duration "
              "(h0_ddrep_circuits.strip_pulses_on on all qubits; base = the ALAP schedule rebuilt from the record, "
              "verified to reproduce IBM-T3 instruction by instruction through dd_variant)",
    "IBM-U": "the same routed circuit unscheduled (the level-3 seed-7 routing of K0.route on the record, no delays)",
}
_G = {}


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def git_commit():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


def versions():
    out = {}
    for m in ("qiskit", "qiskit_aer", "numpy", "scipy"):
        try:
            out[m] = __import__(m).__version__
        except Exception:
            out[m] = None
    try:
        from importlib import metadata
        out["pytket"] = metadata.version("pytket")
    except Exception:
        out["pytket"] = None
    return out


def cid_of(twoB, ref, k):
    return f"B{twoB // 2}_ref{int(ref):02d}_k{int(k)}"


def parse_cid(cid):
    b, r, k = cid.split("_")
    return 2 * int(b[1]), int(r[3:]), int(k[1:])


# --------------------------------------------------------------------------- physics (built before the fork)
def physics():
    if "P" not in _G:
        import gate_K0_2x3_2x4 as K0
        P = K0.physics()
        _G["P"] = P
        _G["K0"] = K0
    return _G["P"]


def exact_psi(twoB, ref, k):
    return _G["K0"].exact_coarse(twoB, ref, k)


def signed_set():
    """{cid: (twoB, ref, k, gates)} of gate_S2D.circuit_set(3) (44 circuits)."""
    if "set" not in _G:
        from gate_S2D import circuit_set
        _M, F, cset = circuit_set(3)
        _G["F"] = F
        _G["set"] = {cid_of(t, r, k): (t, r, k, g) for t, r, k, g in cset}
    return _G["set"]


def q0p_index():
    with open(os.path.join(Q0P_DIR, "index.json")) as fh:
        return json.load(fh)


def q0p_manifest(cid):
    with open(os.path.join(Q0P_DIR, cid + ".manifest.json")) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- one circuit -> files
def finalize(family, cid, circ, ex, extra, qi_check=False):
    from skqd.campaign33.noise import rzz_layers  # noqa: F401  (counts_summary uses it)
    t0 = time.time()
    P = physics()
    psi = C.statevector(circ, threads=_G["threads"])
    mm = C.measure_map(circ)
    mm_ok = mm == {i: i for i in range(P["n"])}
    exa = C.exactness(psi, ex["psi"], P["emb"], mm_ok)
    exa["seconds"] = time.time() - t0
    p_ref = float(np.abs(psi[int(ex["reference_int"])]) ** 2)
    if qi_check:
        tq = time.time()
        psi_qi = C.statevector(circ, method="quantum_info")
        ov = complex(np.vdot(psi_qi, psi))
        exa["quantum_info_cross_check"] = {
            "max_abs_diff_aer_vs_quantum_info": float(np.max(np.abs(psi * np.exp(-1j * np.angle(ov)) - psi_qi))),
            "raw_max_abs_diff": float(np.max(np.abs(psi - psi_qi))),
            "exactness_quantum_info": C.exactness(psi_qi, ex["psi"], P["emb"], mm_ok), "seconds": time.time() - tq}
    path = C.qpy_path(family, cid)
    q = C.dump_qpy13(circ, path)
    rt = C.roundtrip(circ, path)
    man = {"id": cid, "family": family, "family_text": FAMILY_TEXT[family.split("@")[0]],
           "lattice": "2x3", "g2": G2, "twoB": ex.get("twoB"), "sector": ex.get("sector"),
           "reference": ex.get("reference"), "k": ex.get("k"), "dt": ex["dt"],
           "n_logical_qubits": int(P["n"]), "reference_bits": ex["reference_bits"],
           "reference_int": int(ex["reference_int"]), "p_reference_exact": float(ex["p_reference_unnormalised"]),
           "p_reference_circuit": p_ref, "sector_dim": int(ex["dim"]),
           "counts": C.counts_summary(circ), "measure_map_identity": bool(mm_ok),
           "exactness": exa, "exact": bool(exa["ok"]),
           "qpy": {"file": os.path.basename(path), "version_written": C.QPY_VERSION, **q},
           "roundtrip": rt, "ops_digest": C.ops_digest(circ),
           "written_by": versions(), "git_commit": _G.get("commit"), "built": now()}
    man.update(extra or {})
    with open(C.manifest_path(family, cid), "w") as fh:
        json.dump(man, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return man


def ex_block(twoB, ref, k):
    ex = exact_psi(twoB, ref, k)
    ex = dict(ex)
    ex.update({"twoB": twoB, "sector": f"B={twoB // 2}", "reference": int(ref), "k": int(k)})
    return ex


# --------------------------------------------------------------------------- family builders (one task = one cid)
def build_ir_l0(cid, qi):
    from skqd import circuits_qiskit as cq
    t, r, k, gates = signed_set()[cid]
    qc = cq.ir_to_qiskit(gates, physics()["n"], measure=True)
    from skqd.quantinuum_native import ir_counts
    ir_c = ir_counts(gates)
    q0p = q0p_manifest(cid)["original_ir_counts"]
    return finalize("IR-L0", cid, qc, ex_block(t, r, k),
                    {"source": "gate_S2D.circuit_set(3)", "ir_counts": ir_c,
                     "ir_counts_equal_Q0P_manifest": ir_c == q0p}, qi_check=qi)


def build_ir_l3_rzz(cid, qi):
    from qiskit import transpile

    from skqd import circuits_qiskit as cq
    t, r, k, gates = signed_set()[cid]
    t0 = time.time()
    tq = transpile(cq.ir_to_qiskit(gates, physics()["n"], measure=True), **S3_TRANSPILE)
    lay = getattr(tq, "layout", None)
    perm = None
    if lay is not None:
        perm = [int(x) for x in lay.final_index_layout()]
    return finalize("IR-L3-RZZ", cid, tq, ex_block(t, r, k),
                    {"source": "scripts/s3_device_model.py transpilation", "transpile": dict(S3_TRANSPILE),
                     "transpile_s": time.time() - t0, "final_index_layout": perm,
                     "rzz": int(tq.count_ops().get("rzz", 0))}, qi_check=qi)


def _nat_from_pytket(cc, n):
    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    ir, nn, qmap = qn.pytket_to_ir(cc)
    if nn != n or qmap != {q: q for q in range(n)}:
        raise SystemExit(f"measurement map is not q[k] -> c[k]: {qmap}")
    return cq.ir_to_qiskit(ir, nn, measure=True)


def build_nat_o0(cid, qi):
    import hashlib

    from skqd import quantinuum_native as qn
    idx = q0p_index()
    man = q0p_manifest(cid)
    jpath = os.path.join(Q0P_DIR, man["files"]["json"])
    text = open(jpath).read()
    sha = hashlib.sha256(text.encode()).hexdigest()
    if sha != idx["files"][cid]["json_sha256"] or sha != man["json_sha256"]:
        raise SystemExit(f"{cid}: the frozen Q0P JSON does not match its index sha256")
    c = qn.from_json(json.loads(text))
    qn.check_native(c)
    counts = qn.native_counts(c)
    qc = _nat_from_pytket(c, physics()["n"])
    t, r, k = parse_cid(cid)
    return finalize("NAT-O0", cid, qc, ex_block(t, r, k),
                    {"source": os.path.relpath(jpath, ROOT), "source_sha256": sha, "native_counts": counts,
                     "n_zz": counts["n_zz"], "n_phasedx": counts["n_phasedx"],
                     "q0p_level0_state_vs_original_ir": man["levels"]["0"]["state_vs_original_ir"]}, qi_check=qi)


def build_nat_o0_k5(cid, qi):
    from qiskit import transpile

    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    t, r, k = parse_cid(cid)
    signed_set()
    F = _G["F"]
    P = physics()
    M = P["M"]
    dt = float(M.reference(G2, t).dt)
    gates = F.coarse_step(int(r), 5, dt)
    tq = transpile(cq.ir_to_qiskit(gates, P["n"], measure=False), **S3_TRANSPILE)
    ir_t = qn.qiskit_to_ir(tq)
    pc = qn.ir_to_pytket(ir_t, P["n"], measure=True)
    cc = qn.compile_native(pc, "H2-2", 0)
    counts = qn.native_counts(cc)
    qc = _nat_from_pytket(cc, P["n"])
    os.makedirs(C.family_dir("NAT-O0-k5"), exist_ok=True)
    with open(os.path.join(C.family_dir("NAT-O0-k5"), cid + ".pytket.json"), "w") as fh:
        json.dump(qn.to_json(cc), fh)
    return finalize("NAT-O0-k5", cid, qc, ex_block(t, r, 5),
                    {"source": "in-process Q0P_2x3 route at k = 5", "native_counts": counts,
                     "n_zz": counts["n_zz"], "n_phasedx": counts["n_phasedx"], "rzz_before_compilation":
                     int(tq.count_ops().get("rzz", 0)), "dt_used": dt}, qi_check=qi)


def _measurement_free(c):
    from pytket import Circuit, OpType
    out = Circuit(c.n_qubits)
    out.add_phase(c.phase)
    for cmd in c.get_commands():
        if cmd.op.type in (OpType.Measure, OpType.Barrier):
            continue
        out.add_gate(cmd.op, cmd.args)
    return out


def build_nat_pytket(family, cid, qi):
    from pytket import OpType
    from pytket.passes import (AutoRebase, FullPeepholeOptimise, KAKDecomposition, RemoveRedundancies,
                               SequencePass, SquashRzPhasedX)

    from skqd import quantinuum_native as qn
    man = q0p_manifest(cid)
    c0 = qn.from_json(json.load(open(os.path.join(Q0P_DIR, man["files"]["json"]))))
    c = _measurement_free(c0)
    rebase = AutoRebase({OpType.Rz, OpType.PhasedX, OpType.ZZPhase})
    if family == "NAT-O1":
        seq = SequencePass([FullPeepholeOptimise(allow_swaps=False, target_2qb_gate=OpType.TK2), rebase,
                            RemoveRedundancies(), SquashRzPhasedX()])
    else:
        seq = SequencePass([KAKDecomposition(target_2qb_gate=OpType.CX, cx_fidelity=0.999, allow_swaps=False),
                            rebase, RemoveRedundancies(), SquashRzPhasedX()])
    t0 = time.time()
    seq.apply(c)
    tcomp = time.time() - t0
    c.add_c_register("c", c.n_qubits)
    for q in range(c.n_qubits):
        c.Measure(q, q)
    qn.check_native(c)
    counts = qn.native_counts(c)
    qc = _nat_from_pytket(c, physics()["n"])
    t, r, k = parse_cid(cid)
    return finalize(family, cid, qc, ex_block(t, r, k),
                    {"source": f"NAT-O0 ({os.path.relpath(os.path.join(Q0P_DIR, man['files']['json']), ROOT)}) "
                               "without measurements", "compile_s": tcomp, "native_counts": counts,
                     "n_zz": counts["n_zz"], "n_phasedx": counts["n_phasedx"]}, qi_check=qi)


def build_nat_qiskit(family, cid, qi):
    from qiskit import transpile
    base = C.load_circuit("NAT-O0", cid)
    nm = C.unitary_part(base)
    lvl = QISKIT_LEVEL[family]
    kw = dict(basis_gates=["rz", "rx", "ry", "rzz"], coupling_map=None, optimization_level=lvl, seed_transpiler=7)
    if lvl == 3:
        kw["approximation_degree"] = 1.0
    t0 = time.time()
    tq = transpile(nm, **kw)
    tcomp = time.time() - t0
    lay = getattr(tq, "layout", None)
    perm = None if lay is None else [int(x) for x in lay.final_index_layout()]
    if perm is not None and perm != list(range(len(perm))):
        raise SystemExit(f"{family} {cid}: the transpiler permuted the qubits {perm}")
    from qiskit import QuantumCircuit
    out = QuantumCircuit(nm.num_qubits, nm.num_qubits)
    out.global_phase = tq.global_phase
    for inst in tq.data:
        out.append(inst.operation, [tq.find_bit(q).index for q in inst.qubits])
    out.barrier()
    out.measure(range(nm.num_qubits), range(nm.num_qubits))
    t, r, k = parse_cid(cid)
    kw.pop("coupling_map")
    return finalize(family, cid, out, ex_block(t, r, k),
                    {"source": "NAT-O0 QPY without measurements", "transpile": dict(kw, coupling_map=None),
                     "compile_s": tcomp, "final_index_layout": perm,
                     "n_zz": int(out.count_ops().get("rzz", 0)),
                     "n_1q_native": int(out.count_ops().get("rx", 0) + out.count_ops().get("ry", 0))}, qi_check=qi)


BUILDERS = {"IR-L0": build_ir_l0, "IR-L3-RZZ": build_ir_l3_rzz, "NAT-O0": build_nat_o0, "NAT-O0-k5": build_nat_o0_k5,
            "NAT-O1": lambda c, q: build_nat_pytket("NAT-O1", c, q),
            "NAT-O6": lambda c, q: build_nat_pytket("NAT-O6", c, q),
            "NAT-O2": lambda c, q: build_nat_qiskit("NAT-O2", c, q),
            "NAT-O3": lambda c, q: build_nat_qiskit("NAT-O3", c, q),
            "NAT-O4": lambda c, q: build_nat_qiskit("NAT-O4", c, q)}


def family_cids(family):
    if family == "NAT-O0-k5":
        from skqd.krylov import references
        M = physics()["M"]
        return [f"B{t // 2}_ref{int(r):02d}_k5" for t in (0, 2) for r in references(M.basis, t)]
    return list(q0p_index()["circuits"])


def _task(args):
    family, cid, qi = args
    path = C.manifest_path(family, cid)
    if os.path.exists(path) and not _G["force"]:
        return cid, "kept", None
    t0 = time.time()
    try:
        man = BUILDERS[family](cid, qi)
    except SystemExit as exc:
        return cid, "error", str(exc)
    return cid, "built", {"exact": man["exact"], "dpsi": man["exactness"]["max_abs_dpsi_up_to_phase"],
                          "leak": man["exactness"]["leakage"], "s": time.time() - t0,
                          "ops": man["counts"]["ops"]}


def run_family(args):
    family = args.family
    physics()
    if family not in ("IBM",):
        signed_set()
    cids = family_cids(family)
    if args.only:
        cids = [c for c in cids if c in args.only]
    if args.sector:
        cids = [c for c in cids if c.startswith(args.sector + "_")]
    tasks = [(family, c, (i == 0 and not args.no_qi and c == family_cids(family)[0])) for i, c in enumerate(cids)]
    t0 = time.time()
    print(f"{family}: {len(tasks)} circuits, {args.workers} workers x {args.threads} threads", flush=True)
    results = []
    if args.workers > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(args.workers) as pool:
            for cid, st, info in pool.imap_unordered(_task, tasks):
                results.append((cid, st, info))
                print(f"  [{len(results)}/{len(tasks)}] {cid}: {st} {info}  ({time.time() - t0:.0f} s)", flush=True)
    else:
        for t in tasks:
            cid, st, info = _task(t)
            results.append((cid, st, info))
            print(f"  [{len(results)}/{len(tasks)}] {cid}: {st} {info}  ({time.time() - t0:.0f} s)", flush=True)
    errs = [r for r in results if r[1] == "error"]
    inexact = [r for r in results if r[1] == "built" and not r[2]["exact"]]
    print(f"{family}: {len(results)} done in {time.time() - t0:.0f} s; errors {len(errs)}; inexact {len(inexact)}")
    if errs:
        for e in errs:
            print("  ERROR", e)
        return 1
    return 0


# --------------------------------------------------------------------------- IBM families (coding env)
def run_ibm(args):
    """IBM-T3 (re-written at QPY 13), IBM-T0 (pulses -> delays), IBM-U (unscheduled), both K1 circuits."""
    import gate_K0_2x3_2x4 as K0
    import gate_K1_2x3_fpilot as K1
    import h0_ddrep_circuits as DR
    import h0_ddtest_circuits as DC
    from h0_build_circuits import load_qpy_gz

    physics()
    t0 = time.time()
    rec, _info = K1.day_record(K1.PREP)
    base, _binfo = K0.kingston_backend(rec)
    bad = K0.uncalibrated_pairs(rec)
    tgt, _removed = K0.routing_target(base.target, bad)
    rc = 0
    for cid in ("B0_ref117_k1", "B1_ref29_k1"):
        done = all(os.path.exists(C.manifest_path(f, cid)) for f in ("IBM-T3", "IBM-T0", "IBM-U"))
        if done and not args.force:
            print(f"  {cid}: kept")
            continue
        if args.only and cid not in args.only:
            continue
        tc = time.time()
        with open(os.path.join(K1_DIR, "circuits", cid + ".json")) as fh:
            kman = json.load(fh)
        src = os.path.join(K1_DIR, "circuits", cid + ".qpy.gz")
        src_sha = C.sha256_file(src)
        if src_sha != kman["qpy_gz_sha256"]:
            raise SystemExit(f"{cid}: K1 QPY sha256 mismatch")
        t3 = load_qpy_gz(src)
        src_header = C.qpy_header(src)
        twoB, ref, k = parse_cid(cid)
        ex = ex_block(twoB, ref, k)
        final = [int(x) for x in kman["logical_to_physical"]]
        # the base: K0's level-3 routing at the chosen seed on the same record, then ALAP
        if kman["routing"]["chosen"] != "L3|7":
            print(f"  NOTE {cid}: K1 chose {kman['routing']['chosen']}")
        variant, seed = kman["routing"]["variant"], int(kman["routing"]["seed"])
        # resumable stages (each costs minutes at 21 active qubits on a 156-qubit target): the routed and the
        # scheduled circuits are cached as QPY under data/campaign33/circuits/.cache/ (gitignored)
        cache = os.path.join(C.CIRC_DIR, ".cache")
        os.makedirs(cache, exist_ok=True)
        p_tq, p_sched = os.path.join(cache, f"{cid}_routed.qpy.gz"), os.path.join(cache, f"{cid}_alap.qpy.gz")
        if os.path.exists(p_tq) and not args.force:
            tq = C.load_qpy(p_tq)[0]
            print(f"  {cid}: routed circuit from the cache", flush=True)
        else:
            # the routing input is built at the K1 manifest's dt (Model.reference's dt drifts ~4e-16 between
            # processes, which changes the last digits of every angle)
            from skqd import circuits_qiskit as cq
            _M, F, n = K0.model_2x3()
            qc = cq.ir_to_qiskit(F.coarse_step(int(ref), int(k), float(kman["dt"])), n, measure=True)
            tq = K0.pass_manager(tgt, seed, variant).run(qc)
            C.dump_qpy13(tq, p_tq)
            print(f"  {cid}: routed {variant}|{seed} ({time.time() - tc:.0f} s)", flush=True)
        if os.path.exists(p_sched) and not args.force:
            sched = C.load_qpy(p_sched)[0]
            print(f"  {cid}: ALAP circuit from the cache", flush=True)
        else:
            sched, sch = K0.alap(tq, base, rec)
            if not sch["k0_4_ok"]:
                raise SystemExit(f"{cid}: ALAP check failed {sch}")
            C.dump_qpy13(sched, p_sched)
            print(f"  {cid}: ALAP scheduled ({time.time() - tc:.0f} s)", flush=True)
        p_chk = os.path.join(cache, f"{cid}_t3check.json")
        key = {"t3_sha256": src_sha, "alap_sha256": C.sha256_file(p_sched)}
        sd = None
        if os.path.exists(p_chk) and not args.force:
            with open(p_chk) as fh:
                ck = json.load(fh)
            if ck.get("key") == key:
                sd = ck["structure_diff"]
                print(f"  {cid}: dd_variant check from the cache", flush=True)
        if sd is None:
            out_re, _par = DC.dd_variant(K1.CELL, sched, rec, base.target)
            print(f"  {cid}: dd_variant rebuilt ({time.time() - tc:.0f} s)", flush=True)
            sd = C.structure_diff(out_re, t3, tol=1e-9)
            with open(p_chk, "w") as fh:
                json.dump({"key": key, "structure_diff": sd}, fh, indent=1)
        same_t3 = bool(sd["structure_equal"] and sd.get("equal_within_tol"))
        print(f"  {cid}: rebuilt routing {variant}|{seed} -> T3 structure equal {sd['structure_equal']}, max |dparam| "
              f"{sd['max_param_diff']:.1e} ({time.time() - tc:.0f} s)", flush=True)
        if not same_t3:
            raise SystemExit(f"STOP {cid}: the rebuilt ALAP base does not reproduce the flown T3 circuit {sd}")
        # T0 and U are cut out of the FLOWN T3 (its own parameters); the rebuilt schedule only locates the pulses
        t0c, n_rm = DR.strip_pulses_on(t3, sched, rec, hot=list(range(t3.num_qubits)))
        flags = DR.inserted_flags(sched, t3, rec)
        uc = t3.copy_empty_like()
        for inst, f in zip(t3.data, flags):
            if not f and inst.operation.name != "delay":
                uc.append(inst)
        t3_base_only = t3.copy_empty_like()
        for inst, f in zip(t3.data, flags):
            if not f:
                t3_base_only.append(inst)
        order_u = K0.per_qubit_order(uc)
        su = C.structure_diff(uc, tq, tol=1e-9)        # global order (information: ALAP permutes it across qubits)
        order_checks = {"T0_equals_U": K0.per_qubit_order(t0c) == order_u,
                        "T3_without_inserted_equals_U": K0.per_qubit_order(t3_base_only) == order_u,
                        "U_equals_rebuilt_routing_per_qubit": K0.per_qubit_order(tq) == order_u,
                        "ALAP_base_equals_U_per_qubit": K0.per_qubit_order(sched) == order_u}
        tq = uc
        print(f"  {cid}: pulses stripped {n_rm}; per-qubit non-delay order {order_checks}", flush=True)
        if not all(order_checks.values()):
            raise SystemExit(f"STOP {cid}: per-qubit operation order differs {order_checks}")
        from h0_qpu_time import circuit_duration_s
        dur = {nm: circuit_duration_s(c, base.target.durations(), base.target) for nm, c in
               (("T3", t3), ("T0", t0c), ("ALAP_base", sched))}
        common = {"source": os.path.relpath(src, ROOT), "source_sha256": src_sha, "source_qpy_header": src_header,
                  "record_fingerprint": rec["fingerprint"], "record_stamp": rec["stamp"],
                  "logical_to_physical": final, "physical_qubits": kman["physical_qubits"],
                  "readout_patch": kman["readout_patch"], "garbage_acceptance": kman["garbage_acceptance"],
                  "dim": kman["dim"], "p_reference_K1": kman["p_reference"], "routing": {
                      "chosen": kman["routing"]["chosen"], "cz": kman["routed"]["cz"]},
                  "per_qubit_order_checks": order_checks, "durations_s": dur,
                  "rebuild": {"pass_manager": f"K0.pass_manager(target minus uncalibrated cz, {seed}, {variant})",
                              "input_dt": float(kman["dt"]), "alap": "K0.alap", "dd_variant_reproduces_T3": same_t3,
                              "T3_structure_diff": sd, "U_vs_rebuilt_routing": su,
                              "rule": ("structure (names, qubits, clbits, delay durations) exact, parameters to 1e-9; "
                                       "T0 and U are cut from the flown T3, the rebuilt schedule only locates the "
                                       "inserted pulses")}}
        for fam, circ, extra in (("IBM-T3", t3, {"n_pulses_inserted": int(sum(flags))}),
                                 ("IBM-T0", t0c, {"pulses_replaced_by_delays": int(n_rm)}),
                                 ("IBM-U", tq, {})):
            te = time.time()
            r, _psi = K0.circuit_exactness(circ, final, ex, phase_align=True)
            exa = {"max_abs_dpsi_up_to_phase": r["max_abs_delta_up_to_phase"],
                   "max_abs_dpsi_raw_phase": r["max_abs_delta_raw_phase"], "leakage": r["leakage"],
                   "overlap_abs": r["overlap_abs"], "measurement_consistent": r["measurement_consistent"],
                   "n_active": r["n_active"], "ok": r["ok"], "seconds": time.time() - te,
                   "method": "gate_K0_2x3_2x4.circuit_exactness (Aer statevector on the active qubits, logical order)"}
            path = C.qpy_path(fam, cid)
            q = C.dump_qpy13(circ, path)
            rt = C.roundtrip(circ, path)
            man = {"id": cid, "family": fam, "family_text": FAMILY_TEXT[fam], "lattice": "2x3", "g2": G2,
                   "twoB": twoB, "sector": f"B={twoB // 2}", "reference": ref, "k": k, "dt": ex["dt"],
                   "n_logical_qubits": int(physics()["n"]), "reference_bits": ex["reference_bits"],
                   "reference_int": int(ex["reference_int"]),
                   "p_reference_exact": float(ex["p_reference_unnormalised"]), "sector_dim": int(ex["dim"]),
                   "counts": C.counts_summary(circ), "exactness": exa, "exact": bool(exa["ok"]),
                   "qpy": {"file": os.path.basename(path), "version_written": C.QPY_VERSION, **q},
                   "roundtrip": rt, "ops_digest": C.ops_digest(circ), "written_by": versions(),
                   "git_commit": _G.get("commit"), "built": now()}
            man.update(common)
            man.update(extra)
            with open(C.manifest_path(fam, cid), "w") as fh:
                json.dump(man, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
            print(f"  {fam} {cid}: exact {exa['ok']} |dpsi| {exa['max_abs_dpsi_up_to_phase']:.2e} leak "
                  f"{exa['leakage']:.2e}; qpy v{q['header']['qpy_version']} roundtrip {rt['identical']} "
                  f"({time.time() - te:.0f} s)", flush=True)
            if fam == "IBM-T3" and not exa["ok"]:
                rc = 2
    print(f"IBM families done in {time.time() - t0:.0f} s")
    return rc


# --------------------------------------------------------------------------- index
def stage_index(args):
    from skqd.campaign33 import circuits as CC
    fams = {}
    for fam in C.FAMILIES:
        d = C.family_dir(fam)
        if not os.path.isdir(d):
            continue
        mans = []
        for f in sorted(os.listdir(d)):
            if f.endswith(".json") and not f.endswith(".pytket.json"):
                with open(os.path.join(d, f)) as fh:
                    mans.append(json.load(fh))
        if not mans:
            continue
        ok_files = all(C.sha256_file(C.qpy_path(fam, m["id"])) == m["qpy"]["gz_sha256"] for m in mans)
        ex = [m["exact"] for m in mans]
        dps = [m["exactness"]["max_abs_dpsi_up_to_phase"] for m in mans]
        lk = [m["exactness"]["leakage"] for m in mans]
        n2 = [m.get("n_zz", m["counts"]["n_2q"]) for m in mans]
        n1 = [m.get("n_phasedx", m.get("n_1q_native", m["counts"]["n_1q_nonvirtual"])) for m in mans]
        expected = 2 if fam.startswith("IBM") else (11 if fam == "NAT-O0-k5" else 44)
        fams[fam] = {"text": FAMILY_TEXT[fam], "circuits": [m["id"] for m in mans], "n_circuits": len(mans),
                     "complete": len(mans) == expected, "all_exact": all(ex), "n_exact": int(sum(ex)),
                     "max_abs_dpsi_max": float(max(dps)), "leakage_max": float(max(lk)),
                     "n_2q": {"min": int(min(n2)), "max": int(max(n2)), "mean": float(np.mean(n2))},
                     "n_1q": {"min": int(min(n1)), "max": int(max(n1)), "mean": float(np.mean(n1))},
                     "qpy_versions": sorted({m["qpy"]["header"]["qpy_version"] for m in mans}),
                     "all_roundtrips_identical": all(m["roundtrip"]["identical"] for m in mans),
                     "sha256_match": bool(ok_files),
                     "quantum_info_cross_check": next((m["exactness"]["quantum_info_cross_check"] for m in mans
                                                       if "quantum_info_cross_check" in m["exactness"]), None)}
    variants = {}
    for v in C.VARIANTS:
        if v not in fams:
            continue
        f = fams[v]
        info_only = v == "NAT-O6"
        allowed = bool(f["complete"] and f["all_exact"] and not info_only)
        variants[v] = {"allowed": allowed, "status": "allowed" if allowed else "information only",
                       "reason": ("approximate synthesis: information only by construction" if info_only else
                                  ("passes the bar on all 44 circuits" if allowed else
                                   f"{44 - f['n_exact']} of 44 circuits fail the bar (max |dpsi| "
                                   f"{f['max_abs_dpsi_max']:.2e}, max leakage {f['leakage_max']:.2e})")),
                       "n_2q": f["n_2q"], "n_1q": f["n_1q"]}
    allowed = [v for v, x in variants.items() if x["allowed"]]
    chosen = (sorted(allowed, key=lambda v: (variants[v]["n_2q"]["mean"], variants[v]["n_1q"]["mean"], v))[0]
              if allowed else None)
    idx = {"produced_by": "scripts/campaign33_freeze.py --stage index", "prompt": "prompts/33 A2 / 1.1 / 1.4",
           "created": now(), "git_commit": git_commit(), "qpy_version": C.QPY_VERSION,
           "bars": {"max_abs_dpsi": C.AMP_TOL, "leakage": C.LEAK_TOL}, "families": fams, "variants": variants,
           "chosen_variant": chosen,
           "chosen_rule": ("the allowed variant with the fewest two-qubit gates, ties fewer one-qubit gates, then the "
                           "lower id (Q0P's selection rule)"),
           "base_families_exact": {b: (fams.get(b, {}).get("all_exact") and fams.get(b, {}).get("complete"))
                                   for b in C.BASE_FAMILIES}}
    with open(C.INDEX, "w") as fh:
        json.dump(idx, fh, indent=1)
    print(json.dumps({k: {kk: v[kk] for kk in ("n_circuits", "all_exact", "max_abs_dpsi_max", "leakage_max", "n_2q")}
                      for k, v in fams.items()}, indent=1))
    print("variants:", {v: x["status"] for v, x in variants.items()}, "chosen:", chosen)
    bad = [b for b, ok in idx["base_families_exact"].items() if b in fams and not ok]
    if bad:
        with open(os.path.join(ROOT, "validation", "BLOCKED.md"), "w") as fh:
            fh.write(f"# prompts/33 STOP: base family {bad} fails the exactness bar ({now()})\n\n"
                     "A signed circuit would be wrong (rule 3).  See data/campaign33/circuits/index.json.\n")
        return 2
    return 0


# --------------------------------------------------------------------------- the qiskit 1.4.3 check
def stage_check143(args):
    """Run under qiskit 1.4.3 + aer 0.15.1: load every frozen QPY, recompute the instruction digest, and
    recompute the exactness of the first circuit of every family on aer 0.15.1 (CPU)."""
    import qiskit
    import qiskit_aer
    physics()
    idx = C.load_index()
    out = {"qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__, "created": now(), "families": {}}
    t0 = time.time()
    for fam, f in idx["families"].items():
        rows = {}
        for cid in f["circuits"]:
            man = C.load_manifest(fam, cid)
            circ = C.load_circuit(fam, cid)
            rows[cid] = {"loaded": True, "digest_equal": C.ops_digest(circ) == man["ops_digest"]}
        cid0 = f["circuits"][0]
        man = C.load_manifest(fam, cid0)
        circ = C.load_circuit(fam, cid0)
        twoB, ref, k = man["twoB"], man["reference"], man["k"]
        ex = ex_block(twoB, ref, k)
        if fam.startswith("IBM"):
            r, _ = _G["K0"].circuit_exactness(circ, man["logical_to_physical"], ex, phase_align=True)
            exa = {"max_abs_dpsi_up_to_phase": r["max_abs_delta_up_to_phase"], "leakage": r["leakage"], "ok": r["ok"]}
        else:
            psi = C.statevector(circ, threads=args.threads)
            exa = C.exactness(psi, ex["psi"], physics()["emb"], C.measure_map(circ) == {i: i for i in range(20)})
        out["families"][fam] = {"n_loaded": len(rows), "all_digests_equal": all(r["digest_equal"] for r in rows.values()),
                                "exactness_first_circuit": {"id": cid0, **exa}}
        print(f"  {fam}: {len(rows)} loaded, digests equal {out['families'][fam]['all_digests_equal']}, "
              f"{cid0} exact {exa['ok']} ({time.time() - t0:.0f} s)", flush=True)
    out["runtime_s"] = time.time() - t0
    out["all_ok"] = all(v["all_digests_equal"] and v["exactness_first_circuit"]["ok"] for v in out["families"].values())
    with open(os.path.join(C.CIRC_DIR, "check_qiskit143.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("all ok:", out["all_ok"])
    return 0 if out["all_ok"] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--stage", default="build", choices=("build", "index", "check143"))
    ap.add_argument("--family", default=None, help="IR-L0, IR-L3-RZZ, NAT-O0, NAT-O0-k5, NAT-O1..O4, NAT-O6, IBM")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--sector", default=None, choices=("B0", "B1"))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-qi", action="store_true", help="skip the quantum_info cross-check of the first circuit")
    args = ap.parse_args()
    _G.update({"threads": args.threads, "force": args.force, "commit": git_commit()})
    if args.stage == "index":
        return stage_index(args)
    if args.stage == "check143":
        return stage_check143(args)
    if args.family == "IBM":
        return run_ibm(args)
    if args.family not in BUILDERS:
        raise SystemExit(f"unknown family {args.family}")
    return run_family(args)


if __name__ == "__main__":
    sys.exit(main())
