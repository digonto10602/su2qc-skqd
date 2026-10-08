#!/usr/bin/env python3
"""
Gate ENC_compare (prompts/34): does a different qubit encoding shorten the signed 2x2 / 2x3 coarse-step
circuits at FIXED physics?  The current vertex-local codec (`skqd.codec.Codec`, link bits stored at both
ends) is compared with the de-duplicated codec E2 (`skqd.codec_dedup.DedupCodec`, one bit per link plus one
per vertex), and the codeword-assignment search E5' inside the current widths
(`scripts/enc_assignment_search.py`).  0 QPU s, 0 HQC.  PASS means *measured*, not *good* (as K0).

Same Hamiltonian, basis, truncation, dt (data/references.json), term order (krylov.term_groups), circuit
family (gate_S2D.circuit_set: references x k = 1..4; 28 at 2x2, 44 at 2x3) and the transpiler settings of
gate S2 (basis rz/sx/x/cz, level 3, seeds 7/8/9 all-to-all, seed 7 routed on heavy-hex d = 3 / 5).  The
dedup circuits are UNSIGNED candidates everywhere they are written.

Stages (each one invocation, each under the 30-minute rule; fragments in data/enc_compare/):
  equiv     round trips, exhaustive random acceptance, per-term and per-circuit exactness of the dedup codec
  compile   IR counts, all-to-all (seeds 7/8/9) and routed (seed 7) counts of every term and circuit
            (--lattice 2|3, --codec current|dedup: one (lattice, codec) per invocation if needed)
  native    [isolated pytket venv] 2x3 family -> ir_to_pytket -> compile_native(H2-2, level 2) -> check_native,
            counts, exactness of pytket_to_ir -> run_ir (--codec, --sector B0|B1)
  kingston  K0 path (exactness-gated routing, ALAP, idle terms) on the 2026-10-06 ibm_kingston record,
            --kingston-circuit B0_ref117_k1 | B1_ref29_k1, both codecs in one invocation
  f         H2-2 gate-only f per circuit (quantinuum_device_table.row), memory ESTIMATE scenarios,
            the kingston f values, the 2x4 projection by formula
  detect    exhaustive single-flip (and 2x2 double-flip) detection, random acceptance, saturation at the
            plan-of-record shots, the B_sig 3 sigma line against lambda*
  assign    E5' (calls scripts/enc_assignment_search.py; --quick subsamples)
  e4        documentation numbers for the dense encoding E4 (2x2 sector unitaries synthesised; formula bounds)
  assemble  criteria C1-C8, verdict, validation/ENC_compare.json, reports/ENC_compare.md, gates.md

Usage: python scripts/gate_ENC_compare.py --stage <stage> [--quick] [--lattice L] [--codec C] [--sector S]
       ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/gate_ENC_compare.py --stage native --codec dedup
       python scripts/gate_ENC_compare.py --stage kingston --kingston-circuit B0_ref117_k1
`python scripts/run_gate.py ENC_compare` runs the default stage `assemble`.
"""
import argparse
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

OUT = os.path.join(ROOT, "data", "enc_compare")
G2 = 4.0
CODECS = ("current", "dedup")
SEEDS_A2A = (7, 8, 9)
SEED_ROUTED = 7
HEAVY_HEX = {2: 3, 3: 5}
EXACT_TOL, LEAK_TOL = 1e-10, 1e-9          # gate S2 bars (= gate Q0P_2x3 Q1 bars)
TERM_TOL = 1e-10
NATIVE_LEVEL = 2
NATIVE_DEVICE = "H2-2"
NATIVE_PRE = {"basis_gates": ["rz", "rx", "ry", "rzz"], "coupling_map": None, "optimization_level": 3,
              "seed_transpiler": 7}        # the Q0P_2x3 / S3 transpile in front of ir_to_pytket
KINGSTON_RECORD = os.path.join("data", "hardware", "K0_prep", "ibm_kingston_full_20261006T0652Z.json")
KINGSTON_CIRCUITS = ("B0_ref117_k1", "B1_ref29_k1")
PLAN_PATH = ("validation/CV_2x3_plan.json", "data.plan.f=0.10.{B=0,B=1}.final_shots_total")
UNSIGNED = "UNSIGNED candidate circuit (prompts/34, encoding E2 dedup): not part of any signed family"
RANDOM_STRINGS_2X3_CURRENT = 1_000_000
RANDOM_SEED = 7
LOG = []


def log(*a, **_kw):
    s = " ".join(str(x) for x in a)
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)
    LOG.append(s)


def p(*parts):
    return os.path.join(ROOT, *parts)


def load(path):
    with open(path) as fh:
        return json.load(fh)


def dump(obj, path):
    from skqd.report import _jsonable
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(_jsonable(obj), fh, indent=1)
    os.replace(tmp, path)


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


def frag_path(name):
    return os.path.join(OUT, f"{name}.json")


def stamp(stage, t0, extra=None):
    d = {"stage": stage, "git_commit": git_commit(), "python": sys.executable,
         "finished": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "wall_s": time.time() - t0}
    if extra:
        d.update(extra)
    return d


# ------------------------------------------------------------------------------------------- model layer
_M = {}


def model(Lx):
    if Lx not in _M:
        from skqd.exact import Model
        _M[Lx] = Model(Lx)
    return _M[Lx]


def codec_arg(name, M):
    """The `codec=` argument of the factory: None for the current codec (the default path)."""
    if name == "current":
        return None
    from skqd.codec_dedup import DedupCodec
    return DedupCodec(M.basis)


def codec_obj(name, M):
    from skqd.codec import Codec
    from skqd.codec_dedup import DedupCodec
    return Codec(M.basis) if name == "current" else DedupCodec(M.basis)


_F = {}


def factory(Lx, name):
    key = (Lx, name)
    if key not in _F:
        from skqd.circuits_ir import CircuitFactory
        M = model(Lx)
        _F[key] = CircuitFactory(M, G2, codec=codec_arg(name, M))
    return _F[key]


def cid_of(twoB, r, k):
    return f"B{twoB // 2}_ref{int(r):02d}_k{int(k)}"


def family(Lx):
    """[(cid, twoB, ref, k, dt)]: gate_S2D.circuit_set's order (sectors 0, 2; references; k = 1..4)."""
    from skqd.krylov import references
    M = model(Lx)
    out = []
    for twoB in (0, 2):
        dt = float(M.reference(G2, twoB).dt)
        for r in references(M.basis, twoB):
            for k in (1, 2, 3, 4):
                out.append((cid_of(twoB, r, k), twoB, int(r), k, dt))
    return out


def circuit_gates(Lx, name, twoB, r, k, dt):
    return factory(Lx, name).coarse_step(int(r), int(k), dt)


def term_list(Lx):
    M = model(Lx)
    names = ["diag"] + [f"hop{l}" for l in range(M.lat.n_links)] + [f"plaq{P}" for P in range(len(M.lat.plaquettes))]
    return names


def term_gates(Lx, name, term, theta):
    F = factory(Lx, name)
    if term == "diag":
        return F.diag_gates(theta)
    if term.startswith("hop"):
        return F.hop_gates(int(term[3:]), theta)
    return F.plaq_gates(int(term[4:]), theta, True)


def term_operator(Lx, term):
    from skqd.exact import mass_default
    M = model(Lx)
    if term == "diag":
        return mass_default(G2) * M.terms.mass + 0.5 * G2 * M.terms.electric
    if term.startswith("hop"):
        return M.terms.hop[int(term[3:])]
    return -M.terms.plaq[int(term[4:])] / (2 * G2)


_EX = {}


def exact_state(Lx, twoB, r, k):
    """krylov.coarse_states in the signed group order (the state gate S2 checks circuits against)."""
    key = (Lx, twoB, r, k)
    if key not in _EX:
        from skqd.exact import mass_default
        from skqd.krylov import basis_vector, coarse_states, term_groups
        M = model(Lx)
        if ("groups", Lx) not in _EX:
            _EX[("groups", Lx)] = term_groups(M.terms, G2, mass_default(G2))
        dt = float(M.reference(G2, twoB).dt)
        _EX[key] = coarse_states(_EX[("groups", Lx)], basis_vector(M.basis.dim, int(r)), dt, int(k))[int(k)]
    return _EX[key]


# ------------------------------------------------------------------------------------------- counts layer
def tcounts(gates, n, cmap=None, seed=7):
    """transpile exactly as skqd.circuits_qiskit.transpile_counts (basis rz/sx/x/cz, level 3) plus the
    two-qubit depth (depth with the one-qubit gates removed)."""
    from qiskit import transpile

    from skqd import circuits_qiskit as cq
    qc = cq.ir_to_qiskit(gates, n, measure=False)
    t0 = time.time()
    tq = transpile(qc, basis_gates=["rz", "sx", "x", "cz"], coupling_map=cmap, optimization_level=3,
                   seed_transpiler=seed)
    ops = {k: int(v) for k, v in tq.count_ops().items()}
    return {"cz": ops.get("cz", 0), "n_1q": ops.get("sx", 0) + ops.get("x", 0), "rz": ops.get("rz", 0),
            "depth": int(tq.depth()), "depth_2q": int(tq.depth(lambda inst: inst.operation.num_qubits == 2)),
            "n_qubits": int(tq.num_qubits), "ops": ops, "transpile_s": time.time() - t0}


def unit_counts(job):
    """One work unit: (key, Lx, codec, kind, spec).  kind 'term' (spec = term name), 'circuit' (spec =
    (cid, twoB, r, k, dt)), 'step' (spec = 'with_diag' | 'without_diag')."""
    from qiskit.transpiler import CouplingMap

    from skqd.circuits_ir import gate_counts
    key, Lx, name, kind, spec, routed_seeds = job
    t0 = time.time()
    M = model(Lx)
    F = factory(Lx, name)
    n = F.n
    dt0 = float(M.reference(G2, 0).dt)
    if kind == "term":
        gates = term_gates(Lx, name, spec, dt0)
    elif kind == "circuit":
        _cid, twoB, r, k, dt = spec
        gates = circuit_gates(Lx, name, twoB, r, k, dt)
    elif spec == "with_diag":
        from skqd.krylov import references
        gates = F.coarse_step(references(M.basis, 0)[0], 1, dt0)       # the S2 coarse step
    else:
        gates = []
        for t in term_list(Lx)[1:]:
            gates += term_gates(Lx, name, t, dt0)
    row = {"ir": {k: int(v) for k, v in gate_counts(gates).items()}, "n_qubits": n, "a2a": {}, "routed": {}}
    for s in SEEDS_A2A:
        row["a2a"][str(s)] = tcounts(gates, n, None, s)
    cmap = CouplingMap.from_heavy_hex(HEAVY_HEX[Lx])
    for s in routed_seeds:
        row["routed"][str(s)] = tcounts(gates, n, cmap, s)
    row["unit_s"] = time.time() - t0
    return key, row


def _prebuild(Lx, names):
    """Build the factories and the cached term gates before forking (children inherit them)."""
    M = model(Lx)
    dts = sorted({float(M.reference(G2, t).dt) for t in (0, 2)})
    for name in names:
        F = factory(Lx, name)
        for dt in dts:
            for k in (1, 2, 3, 4):
                for l in range(M.lat.n_links):
                    F.hop_gates(l, k * dt)
                for P in range(len(M.lat.plaquettes)):
                    F.plaq_gates(P, k * dt, True)


def pool_map(fn, jobs, workers):
    import multiprocessing as mp
    if workers <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    ctx = mp.get_context("fork")
    out = []
    with ctx.Pool(workers) as pool:
        for i, r in enumerate(pool.imap_unordered(fn, jobs)):
            out.append(r)
            if (i + 1) % 10 == 0 or i + 1 == len(jobs):
                log(f"  {i + 1}/{len(jobs)} units done")
    return out


# =========================================================================================== stage equiv
def stage_equiv(args):
    import scipy.sparse.linalg as spl

    from skqd.circuits_ir import run_ir
    from skqd.codec import Reject
    from skqd.reference_sim import CodewordEmbedding, int_to_bits
    t0 = time.time()
    refs = load(p("data", "references.json"))["references"]
    out = {"what": "round trips, exhaustive random acceptance, dedup term and circuit exactness (S2 bars)",
           "bars": {"term": TERM_TOL, "circuit_deviation": EXACT_TOL, "leakage": LEAK_TOL}, "lattices": {}}
    for Lx in (2, 3):
        M = model(Lx)
        lat = f"2x{Lx}"
        L = {"codecs": {}}
        # -- dt and E0 from data/references.json (no recomputation of E0)
        L["dt"] = {}
        L["E0_references_json"] = {}
        for twoB in (0, 2):
            key = f"{lat}|g2=4.0|2B={twoB}"
            dt_model = float(M.reference(G2, twoB).dt)
            L["dt"][f"B={twoB // 2}"] = {"references_json": refs[key]["dt"], "model": dt_model,
                                         "abs_diff": abs(dt_model - refs[key]["dt"])}
            L["E0_references_json"][f"B={twoB // 2}"] = refs[key]["energies"][0]
        # -- the Hamiltonian is not touched by the codec: sha256 of the term matrices
        h = hashlib.sha256()
        for mat in [M.terms.mass, M.terms.electric] + list(M.terms.hop) + list(M.terms.plaq):
            c = mat.tocsr().sorted_indices()
            for arr in (c.data, c.indices, c.indptr):
                h.update(np.ascontiguousarray(arr).tobytes())
        L["hamiltonian_sha256"] = h.hexdigest()
        for name in CODECS:
            C = codec_obj(name, M)
            nq = C.n_qubits
            cw = C.all_codewords()
            rt = sum(1 for k, lab in enumerate(M.basis.labels) if C.decode(C.encode(lab))[0] == k)
            distinct = len({tuple(r) for r in cw.tolist()})
            row = {"n_qubits": nq, "dim": M.basis.dim, "round_trip_ok": rt, "distinct_codewords": distinct}
            # -- random acceptance per sector
            dims = {0: len(M.basis.sector(0)), 2: len(M.basis.sector(2))}
            acc = {}
            if nq <= 13:
                cnt = {0: 0, 2: 0}
                for x in range(2 ** nq):
                    try:
                        _k, lab = C.decode(int_to_bits(x, nq))
                    except Reject:
                        continue
                    twoB = sum(lab[1][s] - M.lat.n_vac(s) for s in range(M.lat.n_sites))
                    if twoB in cnt:
                        cnt[twoB] += 1
                for twoB in (0, 2):
                    acc[f"B={twoB // 2}"] = {"method": "exhaustive", "strings": 2 ** nq, "accepted": cnt[twoB],
                                             "a": cnt[twoB] / 2 ** nq, "dim_over_2^n": dims[twoB] / 2 ** nq,
                                             "equal": cnt[twoB] == dims[twoB]}
            else:
                rng = np.random.default_rng(RANDOM_SEED)
                N = RANDOM_STRINGS_2X3_CURRENT
                cnt = {0: 0, 2: 0}
                X = rng.integers(0, 2, size=(N, nq), dtype=np.int8)
                for i in range(N):
                    try:
                        _k, lab = C.decode(tuple(int(b) for b in X[i]))
                    except Reject:
                        continue
                    twoB = sum(lab[1][s] - M.lat.n_vac(s) for s in range(M.lat.n_sites))
                    if twoB in cnt:
                        cnt[twoB] += 1
                for twoB in (0, 2):
                    a = dims[twoB] / 2 ** nq
                    acc[f"B={twoB // 2}"] = {
                        "method": ("exact: the decoder accepts only valid labels and the codewords are distinct, "
                                   "so a = dim / 2^n; verified on uniformly random strings"),
                        "a": a, "dim_over_2^n": a, "equal": True,
                        "random_check": {"strings": N, "seed": RANDOM_SEED, "accepted": cnt[twoB],
                                         "expected": N * a, "z": (cnt[twoB] - N * a) / math.sqrt(N * a * (1 - a))}}
            row["random_acceptance"] = acc
            L["codecs"][name] = row
            log(f"equiv {lat} {name}: n {nq}, round trip {rt}/{M.basis.dim}, distinct {distinct}, "
                f"a {[acc[s]['a'] for s in acc]}")
        # -- dedup: per-term exactness on 20 random superpositions of all codewords (seed 7)
        C = codec_obj("dedup", M)
        E = CodewordEmbedding(M, codec=C)
        n = C.n_qubits
        rng = np.random.default_rng(RANDOM_SEED)
        vecs = []
        for _ in range(20):
            v = rng.normal(size=M.basis.dim) + 1j * rng.normal(size=M.basis.dim)
            vecs.append(v / np.linalg.norm(v))
        dt0 = float(M.reference(G2, 0).dt)
        terms = {}
        for t in term_list(Lx):
            O = term_operator(Lx, t)
            worst, worst_leak = 0.0, 0.0
            locality_ok = True
            try:
                for theta in (dt0, 4 * dt0):
                    g = term_gates(Lx, "dedup", t, theta)
                    for v in vecs:
                        got = run_ir(g, n, E.embed(v))
                        ref = spl.expm_multiply(-1j * theta * O, v)
                        worst = max(worst, float(np.abs(got - E.embed(ref)).max()))
                        worst_leak = max(worst_leak, abs(E.leakage(got)))
            except AssertionError as exc:
                locality_ok = False
                terms[t] = {"locality_ok": False, "error": str(exc)}
                log(f"equiv {lat} dedup {t}: LOCALITY FAIL {exc}")
                continue
            sup = len(C.support("diag" if t == "diag" else ("hop" if t.startswith("hop") else "plaq"),
                                0 if t == "diag" else int(t[3:] if t.startswith("hop") else t[4:])))
            terms[t] = {"locality_ok": locality_ok, "max_deviation": worst, "max_leakage": worst_leak,
                        "support": sup, "thetas": [dt0, 4 * dt0], "n_vectors": len(vecs)}
            log(f"equiv {lat} dedup {t}: dev {worst:.1e}, leak {worst_leak:.1e}, support {sup}")
        L["dedup_terms"] = terms
        # -- dedup coarse circuits against krylov.coarse_states
        circ = {}
        for cid, twoB, r, k, dt in family(Lx):
            psi = run_ir(circuit_gates(Lx, "dedup", twoB, r, k, dt), n)
            ex = E.embed(exact_state(Lx, twoB, r, k))
            ov = complex(np.vdot(ex, psi))
            circ[cid] = {"max_deviation": float(np.abs(psi - ex).max()),
                         "max_deviation_up_to_phase": float(np.abs(psi * np.exp(-1j * np.angle(ov)) - ex).max()),
                         "leakage": float(abs(E.leakage(psi)))}
        L["dedup_circuits"] = circ
        L["dedup_circuits_summary"] = {
            "n": len(circ), "max_deviation": max(v["max_deviation"] for v in circ.values()),
            "max_leakage": max(v["leakage"] for v in circ.values())}
        log(f"equiv {lat} dedup circuits: {L['dedup_circuits_summary']}")
        out["lattices"][lat] = L
    out["hamiltonian_unchanged"] = True
    out["hamiltonian_unchanged_reason"] = ("the codec is a relabelling of the same basis states: the term matrices "
                                           "(sha256 per lattice above) are built from skqd.exact.Model and never "
                                           "read the codec")
    out["timing"] = stamp("equiv", t0)
    dump(out, frag_path("equiv"))
    log(f"equiv written ({time.time() - t0:.0f} s)")


# =========================================================================================== stage compile
def stage_compile(args):
    t0 = time.time()
    lats = [int(args.lattice)] if args.lattice else [2, 3]
    names = [args.codec] if args.codec else list(CODECS)
    path = frag_path("compile")
    out = load(path) if os.path.exists(path) else {"what": "IR, all-to-all (seeds 7/8/9) and routed counts",
                                                   "transpile": {"basis": ["rz", "sx", "x", "cz"],
                                                                 "optimization_level": 3,
                                                                 "a2a_seeds": list(SEEDS_A2A),
                                                                 "routed_seed_circuits": SEED_ROUTED,
                                                                 "routed_seeds_step": list(SEEDS_A2A),
                                                                 "heavy_hex_distance": HEAVY_HEX},
                                                   "results": {}, "timing": {}}
    for Lx in lats:
        _prebuild(Lx, names)
        jobs = []
        for name in names:
            for t in term_list(Lx):
                jobs.append((f"2x{Lx}|{name}|term|{t}", Lx, name, "term", t, (SEED_ROUTED,)))
            for spec in ("with_diag", "without_diag"):
                jobs.append((f"2x{Lx}|{name}|step|{spec}", Lx, name, "step", spec, SEEDS_A2A))
            if not args.quick:
                for f in family(Lx):
                    jobs.append((f"2x{Lx}|{name}|circuit|{f[0]}", Lx, name, "circuit", f, (SEED_ROUTED,)))
        jobs.sort(key=lambda j: {"circuit": 0, "step": 1, "term": 2}[j[3]])
        tl = time.time()
        log(f"compile 2x{Lx} {names}: {len(jobs)} units on {args.workers} workers")
        for key, row in pool_map(unit_counts, jobs, args.workers):
            out["results"][key] = row
        out["timing"][f"2x{Lx}|{'+'.join(names)}"] = time.time() - tl
        dump(out, path)
        log(f"compile 2x{Lx} done ({time.time() - tl:.0f} s)")
    out["quick"] = bool(args.quick)
    out["stamp"] = stamp("compile", t0)
    dump(out, path)
    # dedup IR counts per circuit (data/enc_compare/dedup_ir_counts.json), flagged unsigned
    ir = {k: v["ir"] for k, v in out["results"].items() if "|dedup|" in k}
    dump({"flag": UNSIGNED, "produced_by": "scripts/gate_ENC_compare.py --stage compile", "ir_gate_counts": ir},
         os.path.join(OUT, "dedup_ir_counts.json"))


# =========================================================================================== stage native
def rzz_expanded(ir):
    """rzz(p) on (a, b) = cx(a, b) rz(p) on b cx(a, b) (exact, no phase): run_ir has no rzz."""
    out = []
    for nm, qs, par in ir:
        if nm == "rzz":
            out += [("cx", [qs[0], qs[1]], None), ("rz", [qs[1]], par), ("cx", [qs[0], qs[1]], None)]
        else:
            out.append((nm, qs, par))
    return out


def native_one(job):
    from qiskit import transpile

    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn
    from skqd.circuits_ir import run_ir
    from skqd.reference_sim import CodewordEmbedding
    name, cid, twoB, r, k, dt = job
    t0 = time.time()
    M = model(3)
    gates = circuit_gates(3, name, twoB, r, k, dt)
    n = factory(3, name).n
    tq = transpile(cq.ir_to_qiskit(gates, n, measure=False), **NATIVE_PRE)
    ir_t = qn.qiskit_to_ir(tq)
    pc = qn.ir_to_pytket(ir_t, n, measure=False)
    tc = time.time()
    cc = qn.compile_native(pc, NATIVE_DEVICE, NATIVE_LEVEL)          # raises NativeCompileError if not native
    t_comp = time.time() - tc
    qn.check_native(cc)
    cnt = qn.native_counts(cc)
    cnt["n_meas"] = n                                                 # one measurement per qubit appended
    hps = qn.hqc_per_shot(cnt)
    ir_c, nn, _qmap = qn.pytket_to_ir(cc)
    perm_ok = all(a == b for a, b in cc.implicit_qubit_permutation().items())
    E = CodewordEmbedding(M, codec=codec_obj(name, M))
    psi = run_ir(rzz_expanded(ir_c), nn)
    ex = E.embed(exact_state(3, twoB, r, k))
    res = qn.global_phase_residual(psi, ex)
    leak = float(abs(E.leakage(psi)))
    # campaign33's NAT-O2 definition (pytket level 0 rebase, then qiskit preset level 1 on rz/rx/ry/rzz,
    # measurement-free) -- counts only, for the comparison with data/campaign33/circuits/index.json
    c0 = qn.compile_native(pc, NATIVE_DEVICE, 0)
    ir0, _n0, _ = qn.pytket_to_ir(c0)
    t1 = transpile(cq.ir_to_qiskit(ir0, n, measure=False), basis_gates=["rz", "rx", "ry", "rzz"], coupling_map=None,
                   optimization_level=1, seed_transpiler=7)
    o1 = {kk: int(v) for kk, v in t1.count_ops().items()}
    row = {"id": cid, "codec": name, "twoB": twoB, "reference": r, "k": k, "counts": cnt, "hqc_per_shot": hps,
           "pre_transpile_rzz": int(tq.count_ops().get("rzz", 0)), "compile_s": t_comp,
           "exactness": {"max_abs_dpsi": res["max_abs_dpsi"], "one_minus_overlap": res["one_minus_overlap"],
                         "leakage": leak, "implicit_permutation_identity": bool(perm_ok),
                         "ok": bool(res["max_abs_dpsi"] < EXACT_TOL and leak < LEAK_TOL and perm_ok),
                         "engine": "pytket_to_ir -> run_ir (rzz expanded as cx rz cx), against the embedded "
                                   "krylov.coarse_states state, global phase removed"},
           "nat_o2_campaign33_definition": {"n_zz": o1.get("rzz", 0), "n_1q": o1.get("rx", 0) + o1.get("ry", 0),
                                            "n_rz": o1.get("rz", 0)},
           "flag": UNSIGNED if name == "dedup" else "signed family, current codec", "unit_s": time.time() - t0}
    return cid, row


def stage_native(args):
    t0 = time.time()
    try:
        import pytket  # noqa: F401
    except ImportError as exc:
        path = frag_path("native")
        out = load(path) if os.path.exists(path) else {}
        out["skipped"] = {"reason": f"pytket not importable in {sys.executable}: {exc}; run this stage with "
                                    "~/.local/share/su2qc-quantinuum/venv/bin/python"}
        dump(out, path)
        log("native skipped:", out["skipped"]["reason"])
        return
    from skqd import quantinuum_native as qn
    names = [args.codec] if args.codec else list(CODECS)
    sectors = {"B0": (0,), "B1": (2,)}.get(args.sector, (0, 2))
    path = frag_path("native")
    out = load(path) if os.path.exists(path) else {"circuits": {}, "timing": {}}
    out.update({"what": "2x3 family -> transpile(rz/rx/ry/rzz, level 3, seed 7) -> ir_to_pytket(measure=False) -> "
                        f"compile_native({NATIVE_DEVICE}, optimisation_level={NATIVE_LEVEL}) -> check_native; "
                        "exactness of pytket_to_ir -> run_ir under the Q1 bars",
                "pre_transpile": NATIVE_PRE, "device": NATIVE_DEVICE, "level": NATIVE_LEVEL,
                "versions": qn.versions(),
                "measurement_note": ("compiled measurement-free (TKET level >= 1 deletes the Rz in front of a "
                                     "Measure, which changes the state but not the distribution); n_meas = n "
                                     "is added to the counts for HQC and f"),
                "nat_o2_note": ("prompts/34 names compile_native(level 2) as campaign33's NAT-O2; campaign33 "
                                "(scripts/campaign33_freeze.py) defines NAT-O2 as pytket level 0 followed by "
                                "qiskit preset level 1: both are recorded, the verdict uses compile_native "
                                "level 2 as the prompt specifies")})
    out.pop("skipped", None)
    _prebuild(3, names)
    jobs = []
    for name in names:
        for cid, twoB, r, k, dt in family(3):
            if twoB in sectors and (f"{name}|{cid}" not in out["circuits"] or args.force):
                jobs.append((name, cid, twoB, r, k, dt))
    if args.part:
        i, m = (int(x) for x in args.part.split("/"))
        jobs = jobs[i - 1::m]                       # one of m interleaved parts (30-minute rule)
    log(f"native: {len(jobs)} circuits on {args.workers} workers")
    tl = time.time()
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for i, (cid, row) in enumerate(pool.imap_unordered(native_one, jobs)):
            out["circuits"][f"{row['codec']}|{cid}"] = row
            dump(out, path)
            log(f"  native {row['codec']} {cid}: ZZ {row['counts']['n_zz']}, PhasedX {row['counts']['n_phasedx']}, "
                f"dpsi {row['exactness']['max_abs_dpsi']:.1e}, leak {row['exactness']['leakage']:.1e} "
                f"({row['unit_s']:.0f} s) [{i + 1}/{len(jobs)}]")
    out["timing"][f"{'+'.join(names)}|{args.sector or 'all'}|{args.part or '1/1'}"] = time.time() - tl
    out["stamp"] = stamp("native", t0)
    dump(out, path)


# =========================================================================================== stage kingston
def stage_kingston(args):
    """K0's evaluate_2x3 on one circuit in both codecs.  The dedup run pre-fills K0's model and physics
    caches with the dedup factory / embedding (K0's code itself is not modified)."""
    import gate_K0_2x3_2x4 as K
    from qiskit import qpy

    from skqd.circuits_ir import CircuitFactory
    from skqd.exact import mass_default
    from skqd.krylov import term_groups
    from skqd.reference_sim import CodewordEmbedding
    t0 = time.time()
    cid = args.kingston_circuit
    twoB = 2 * int(cid[1])
    ref = int(cid.split("_ref")[1].split("_")[0])
    k = int(cid.split("_k")[1])
    rec = K.load_json(p(KINGSTON_RECORD))
    path = frag_path("kingston")
    out = load(path) if os.path.exists(path) else {"circuits": {}}
    out.update({"record": KINGSTON_RECORD, "record_fingerprint": rec["fingerprint"],
                "what": "gate_K0_2x3_2x4.evaluate_2x3 (exactness-gated routing seeds 0..7, ALAP, idle terms) "
                        "with the dedup factory/embedding pre-filled into K0's caches for the dedup codec"})
    M = model(3)
    for name in CODECS:
        if f"{name}|{cid}" in out["circuits"] and not args.force:
            log(f"kingston {name} {cid}: kept")
            continue
        K._MODEL.clear()
        K._PHYS.clear()
        if name == "dedup":
            C = codec_obj("dedup", M)
            F = CircuitFactory(M, G2, codec=C)
            K._MODEL.update(M=M, F=F, n=C.n_qubits)
            K._PHYS.update(M=M, F=F, n=C.n_qubits, codec=C, emb=CodewordEmbedding(M, codec=C),
                           groups=term_groups(M.terms, G2, mass_default(G2)))
        tl = time.time()
        block, tq, sched, _base = K.evaluate_2x3(rec, f"enc_{name}", twoB=twoB, ref=ref, k=k, log=log)
        block["codec"] = name
        block["wall_s"] = time.time() - tl
        if name == "dedup":
            block["flag"] = UNSIGNED
            d = os.path.join(OUT, "kingston")
            os.makedirs(d, exist_ok=True)
            files = {}
            for tag, circ in (("routed", tq), ("scheduled", sched)):
                fn = os.path.join(d, f"dedup_{cid}_{tag}.qpy.gz")
                with gzip.open(fn, "wb", mtime=0) as fh:
                    qpy.dump(circ, fh, version=13)
                with open(fn, "rb") as fh:
                    files[tag] = {"path": os.path.relpath(fn, ROOT),
                                  "sha256": hashlib.sha256(fh.read()).hexdigest(), "qpy_version": 13}
            man = {"id": cid, "codec": "dedup", "flag": UNSIGNED, "record": KINGSTON_RECORD,
                   "record_fingerprint": rec["fingerprint"], "files": files, "n_cz": block["n_cz"],
                   "n_active_qubits": block["n_active_qubits"],
                   "scheduled_duration_s": block["schedule"]["scheduled_duration_s"],
                   "routing_chosen": block["routing"]["chosen"], "exactness": block["exactness"],
                   "logical_to_physical": block["routing"]["per_seed"][block["routing"]["chosen"]]["logical_to_physical"],
                   "produced_by": "scripts/gate_ENC_compare.py --stage kingston", "git_commit": git_commit()}
            dump(man, os.path.join(d, f"dedup_{cid}.manifest.json"))
            block["files"] = files
        # keep the JSON small: drop the per-seed physical layouts of the unchosen seeds
        for key, v in block["routing"]["per_seed"].items():
            if key != block["routing"]["chosen"]:
                v.pop("logical_to_physical", None)
                v.pop("physical_qubits", None)
        out["circuits"][f"{name}|{cid}"] = block
        out.setdefault("timing", {})[f"{name}|{cid}"] = time.time() - tl
        dump(out, path)
    K._MODEL.clear()
    K._PHYS.clear()
    out["stamp"] = stamp("kingston", t0)
    dump(out, path)


# =========================================================================================== stage f
def stage_f(args):
    import quantinuum_device_table as QT

    from skqd.device_req import clean_shot_fraction
    t0 = time.time()
    nat = load(frag_path("native"))
    dev = load(p("data", "quantinuum", "devices_20261002.json"))
    spec = dict(QT.SPECS["quantinuum_h2_2"])
    js = dev["specs"]["quantinuum_h2_2"]
    triple_ok = all(abs(float(js[k]) - float(spec[k])) <= 1e-15 for k in ("eps2", "eps1", "eps_ro_0", "eps_ro_1"))
    out = {"what": "H2-2 gate-only f per circuit as quantinuum_device_table.row (eps_ro = mean of the two SPAM "
                   "values), memory ESTIMATE scenarios, kingston f values, 2x4 projection by formula",
           "h2_2": {"eps2": spec["eps2"], "eps1": spec["eps1"], "eps_ro": QT.eps_ro_of(spec),
                    "eps_ro_rule": QT.EPS_RO_RULE, "triple_equals_devices_json": triple_ok,
                    "source": "data/quantinuum/devices_20261002.json specs.quantinuum_h2_2 (= quantinuum_device_table.SPECS)"},
           "codecs": {}}
    for name in CODECS:
        rows = [v for k, v in nat.get("circuits", {}).items() if k.startswith(name + "|")]
        if not rows:
            out["codecs"][name] = {"missing": "native stage not run for this codec"}
            continue
        per = [{"id": v["id"], "sector": f"B={v['twoB'] // 2}", "n_2q": v["counts"]["n_zz"],
                "n_1q": v["counts"]["n_phasedx"], "n_meas": v["counts"]["n_meas"],
                "n_qubits": v["counts"]["n_qubits"], "depth_2q": v["counts"]["depth_2q"],
                "hqc_per_shot": v["hqc_per_shot"]} for v in sorted(rows, key=lambda x: x["id"])]
        cnt = {"per_circuit": per, "n_qubits": per[0]["n_qubits"], "n_meas": per[0]["n_meas"],
               "n_2q_mean": float(np.mean([x["n_2q"] for x in per])),
               "n_1q_mean": float(np.mean([x["n_1q"] for x in per])),
               "depth_2q_max": int(max(x["depth_2q"] for x in per)),
               "hqc_per_shot_mean": float(np.mean([x["hqc_per_shot"] for x in per]))}
        r = QT.row("quantinuum_h2_2", spec, "2x3", cnt)
        fs = {x["id"]: clean_shot_fraction(x["n_2q"], x["n_1q"], x["n_meas"], spec["eps2"], spec["eps1"],
                                           QT.eps_ro_of(spec)) for x in per}
        out["codecs"][name] = {"n_circuits": len(per), "f_per_circuit": fs,
                               "f_gate_only_mean": r["f_gate_only_mean"], "f_gate_only_worst": r["f_gate_only_worst"],
                               "f_gate_only_worst_id": r["f_gate_only_worst_id"], "f_2q_only": r["f_2q_only"],
                               "meets_mean_0.1_gate_only": r["meets_mean_0.1_gate_only"],
                               "meets_worst_0.05_gate_only": r["meets_worst_0.05_gate_only"],
                               "bars_note": "amendment-01 bars 0.1 / 0.05 REPORTED, not applied",
                               "memory_ESTIMATE": r["memory_ESTIMATE"],
                               "f_with_memory_mid_ESTIMATE": r["f_with_memory_mid_ESTIMATE"],
                               "hqc_per_shot_mean": cnt["hqc_per_shot_mean"], "n_2q_mean": cnt["n_2q_mean"],
                               "n_1q_mean": cnt["n_1q_mean"], "depth_2q_max": cnt["depth_2q_max"]}
        log(f"f {name}: H2-2 mean {r['f_gate_only_mean']:.4f}, worst {r['f_gate_only_worst']:.4f}, "
            f"mid memory {r['f_with_memory_mid_ESTIMATE']:.4f}")
    # kingston values from the kingston stage
    if os.path.exists(frag_path("kingston")):
        kg = load(frag_path("kingston"))
        out["kingston"] = {key: {"n_cz": b["n_cz"], "n_active_qubits": b["n_active_qubits"],
                                 "scheduled_duration_s": b["schedule"]["scheduled_duration_s"],
                                 "f_gates_layout": b["f_gates_layout"],
                                 "f_gates_best_patch_bound": b["f_gates_best_patch_bound"],
                                 "f_ceiling_2q": b["f_ceiling_2q"],
                                 "f_idle_aware_echo": b["idle"]["echo"]["f_idle_aware"],
                                 "f_idle_aware_0.174": b["idle"]["transferred_0.174"]["f_idle_aware"],
                                 "S_idle_echo": b["idle"]["echo"]["S_idle"],
                                 "S_idle_0.174": b["idle"]["transferred_0.174"]["S_idle"]}
                           for key, b in kg["circuits"].items()}
    # 2x4 projection by formula (qubits), the current 2x4 counts read from validation/S2_2x4.json
    from skqd.basis import enumerate_basis
    from skqd.codec import Codec
    from skqd.lattice import Ladder
    lat4 = Ladder(4)
    s24 = load(p("validation", "S2_2x4.json"))["data"]
    a2a24 = s24["compile"]["compile_4_exact_a2a_k1"]["circuits"]["B0_ref0_k1"]["maps"]["all_to_all"]
    out["projection_2x4"] = {
        "n_qubits_current": int(Codec(enumerate_basis(lat4)).n_qubits),
        "n_qubits_dedup_formula": lat4.n_links + lat4.n_sites,
        "formula": "current 2 N_links + N_sites, dedup N_links + N_sites",
        "current_a2a_n_2q": int(a2a24["n_2q"]),
        "current_a2a_source": "validation/S2_2x4.json data.compile.compile_4_exact_a2a_k1.circuits.B0_ref0_k1.maps.all_to_all.n_2q",
        "dedup_compiled": False, "note": "--2x4 not given: no dedup 2x4 compile (optional per prompts/34 step 6)"}
    out["timing"] = stamp("f", t0)
    dump(out, frag_path("f"))


# =========================================================================================== stage detect
def detection(C, basis, twoB, doubles):
    from skqd.codec import Reject
    idx = basis.sector(twoB)
    n = C.n_qubits
    det = {}
    silent_other = 0
    total = 0
    for k in idx:
        c = C.encode(basis.labels[k])
        for q in range(n):
            cc = list(c)
            cc[q] ^= 1
            total += 1
            try:
                kk, _ = C.decode(tuple(cc), twoB)
                if kk != k:
                    silent_other += 1
            except Reject as r:
                det[str(r)] = det.get(str(r), 0) + 1
    row = {"n_qubits": n, "dim": len(idx), "single_flips": total, "detected": sum(det.values()),
           "detected_by": det, "silently_accepted_as_other_state": silent_other,
           "detected_fraction": sum(det.values()) / total, "random_acceptance": len(idx) / 2 ** n}
    if doubles:
        d2 = t2 = 0
        for k in idx:
            c = C.encode(basis.labels[k])
            for q1 in range(n):
                for q2 in range(q1 + 1, n):
                    cc = list(c)
                    cc[q1] ^= 1
                    cc[q2] ^= 1
                    t2 += 1
                    try:
                        C.decode(tuple(cc), twoB)
                    except Reject:
                        d2 += 1
        row.update(double_flips=t2, double_detected=d2, double_detected_fraction=d2 / t2)
    return row


def stage_detect(args):
    from skqd.skqd import poisson_lambda_star
    t0 = time.time()
    plan = load(p("validation", "CV_2x3_plan.json"))["data"]["plan"]["f=0.10"]
    shots = {"B=0": int(plan["B=0"]["final_shots_total"]), "B=1": int(plan["B=1"]["final_shots_total"])}
    lam = float(poisson_lambda_star(3, 0.95))
    out = {"plan_shots": shots, "plan_source": PLAN_PATH, "lambda_star": lam, "lattices": {}}
    for Lx in (2, 3):
        M = model(Lx)
        L = {}
        for name in CODECS:
            C = codec_obj(name, M)
            L[name] = {}
            for twoB in (0, 2):
                row = detection(C, M.basis, twoB, doubles=(Lx == 2))
                s = f"B={twoB // 2}"
                if Lx == 3:
                    N = shots[s]
                    a = row["random_acceptance"]
                    mu = N * a / row["dim"]
                    row["saturation_at_plan"] = {"N": N, "N_a_over_dim": mu, "mu_s": mu,
                                                 "three_sigma_line": mu + 3 * math.sqrt(mu),
                                                 "three_sigma_line_above_lambda_star": bool(mu + 3 * math.sqrt(mu) > lam),
                                                 "saturated_rule_C22_gt_5": bool(mu > 5)}
                L[name][s] = row
                log(f"detect 2x{Lx} {name} {s}: single {row['detected_fraction']:.4f}, a {row['random_acceptance']:.3e}"
                    + (f", sat {row['saturation_at_plan']['N_a_over_dim']:.3f}" if Lx == 3 else ""))
        out["lattices"][f"2x{Lx}"] = L
    out["timing"] = stamp("detect", t0)
    dump(out, frag_path("detect"))


# =========================================================================================== stage assign
def stage_assign(args):
    import enc_assignment_search as A
    t0 = time.time()
    res = A.run(quick=args.quick, workers=args.workers, log=log)
    res["timing"] = stamp("assign", t0)
    dump(res, frag_path("assign"))


# =========================================================================================== stage e4
def stage_e4(args):
    """Documentation numbers for the dense sector encoding E4 (prompts/34 / the planner list section 5 item 3):
    the 2x2 sector step exp(-i dt H_sector) synthesised as one unitary (qiskit level 3, seed 7) and the
    quantum-Shannon-decomposition bound 23/48 4^n.  Not a criterion: E4 is documented, not built."""
    import scipy.linalg as sla
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import UnitaryGate
    t0 = time.time()
    out = {"what": "E4 dense sector encoding: 2x2 synthesis and formula bounds (documentation only)", "2x2": {}}
    M = model(2)
    for twoB in (0, 2):
        ref = M.reference(G2, twoB)
        H = M.H(G2)[ref.indices][:, ref.indices].toarray()
        d = H.shape[0]
        nq = math.ceil(math.log2(d))
        U = np.eye(2 ** nq, dtype=complex)
        U[:d, :d] = sla.expm(-1j * ref.dt * H)
        qc = QuantumCircuit(nq)
        qc.append(UnitaryGate(U), list(range(nq)))
        tq = transpile(qc, basis_gates=["rz", "sx", "x", "cz"], optimization_level=3, seed_transpiler=7)
        ops = {k: int(v) for k, v in tq.count_ops().items()}
        out["2x2"][f"B={twoB // 2}"] = {"dim": d, "n_qubits": nq, "cz": ops.get("cz", 0), "depth": int(tq.depth()),
                                        "qsd_bound_23_48_4n": 23 / 48 * 4 ** nq}
        log(f"e4 2x2 B={twoB // 2}: {out['2x2'][f'B={twoB // 2}']}")
    from skqd.basis import enumerate_basis
    from skqd.lattice import Ladder
    for Lx in (3, 4):
        b = enumerate_basis(Ladder(Lx))
        row = {}
        for twoB in (0, 2):
            d = len(b.sector(twoB))
            nq = math.ceil(math.log2(d))
            row[f"B={twoB // 2}"] = {"dim": d, "n_qubits": nq, "qsd_bound_23_48_4n": 23 / 48 * 4 ** nq,
                                     "random_acceptance": d / 2 ** nq}
        out[f"2x{Lx}"] = row
    out["timing"] = stamp("e4", t0)
    dump(out, frag_path("e4"))


# =========================================================================================== assemble
def _mean(xs):
    return float(np.mean(xs))


def step_summary(cmp_, lat, name, spec):
    r = cmp_["results"][f"{lat}|{name}|step|{spec}"]
    a = [r["a2a"][str(s)] for s in SEEDS_A2A]
    rr = [r["routed"][str(s)] for s in SEEDS_A2A if str(s) in r["routed"]]
    return {"n_qubits": r["n_qubits"], "ir": r["ir"],
            "cz_a2a": {str(s): x["cz"] for s, x in zip(SEEDS_A2A, a)}, "cz_a2a_mean": _mean([x["cz"] for x in a]),
            "cz_a2a_spread": max(x["cz"] for x in a) - min(x["cz"] for x in a),
            "depth_a2a_mean": _mean([x["depth"] for x in a]), "depth_2q_a2a_mean": _mean([x["depth_2q"] for x in a]),
            "n_1q_a2a_mean": _mean([x["n_1q"] for x in a]),
            "cz_routed_seed7": r["routed"][str(SEED_ROUTED)]["cz"],
            "cz_routed": {str(s): r["routed"][str(s)]["cz"] for s in SEEDS_A2A if str(s) in r["routed"]},
            "cz_routed_spread": (max(x["cz"] for x in rr) - min(x["cz"] for x in rr)) if rr else None,
            "depth_routed_seed7": r["routed"][str(SEED_ROUTED)]["depth"],
            "depth_2q_routed_seed7": r["routed"][str(SEED_ROUTED)]["depth_2q"],
            "n_qubits_routed": r["routed"][str(SEED_ROUTED)]["n_qubits"]}


def family_summary(cmp_, lat, name):
    rows = {k.split("|")[3]: v for k, v in cmp_["results"].items() if k.startswith(f"{lat}|{name}|circuit|")}
    if not rows:
        return None
    per_seed = {str(s): _mean([v["a2a"][str(s)]["cz"] for v in rows.values()]) for s in SEEDS_A2A}
    return {"n_circuits": len(rows), "cz_a2a_mean_per_seed": per_seed,
            "cz_a2a_mean": _mean(list(per_seed.values())),
            "cz_a2a_min": min(v["a2a"][str(s)]["cz"] for v in rows.values() for s in SEEDS_A2A),
            "cz_a2a_max": max(v["a2a"][str(s)]["cz"] for v in rows.values() for s in SEEDS_A2A),
            "depth_a2a_mean": _mean([v["a2a"][str(s)]["depth"] for v in rows.values() for s in SEEDS_A2A]),
            "depth_2q_a2a_mean": _mean([v["a2a"][str(s)]["depth_2q"] for v in rows.values() for s in SEEDS_A2A]),
            "cz_routed_mean": _mean([v["routed"][str(SEED_ROUTED)]["cz"] for v in rows.values()]),
            "depth_routed_mean": _mean([v["routed"][str(SEED_ROUTED)]["depth"] for v in rows.values()]),
            "depth_2q_routed_mean": _mean([v["routed"][str(SEED_ROUTED)]["depth_2q"] for v in rows.values()]),
            "per_circuit": {cid: {"ir_cx": v["ir"].get("cx", 0), "cz_a2a": {s: v["a2a"][s]["cz"] for s in v["a2a"]},
                                  "depth_2q_a2a_seed7": v["a2a"][str(SEED_ROUTED)]["depth_2q"],
                                  "cz_routed": v["routed"][str(SEED_ROUTED)]["cz"]} for cid, v in sorted(rows.items())}}


def native_summary(nat, name):
    rows = [v for k, v in nat.get("circuits", {}).items() if k.startswith(name + "|")]
    if not rows:
        return None
    zz = [v["counts"]["n_zz"] for v in rows]
    return {"n_circuits": len(rows), "zz_mean": _mean(zz), "zz_min": min(zz), "zz_max": max(zz),
            "phasedx_mean": _mean([v["counts"]["n_phasedx"] for v in rows]),
            "depth_2q_mean": _mean([v["counts"]["depth_2q"] for v in rows]),
            "depth_2q_max": max(v["counts"]["depth_2q"] for v in rows),
            "depth_mean": _mean([v["counts"]["depth"] for v in rows]),
            "hqc_per_shot_mean": _mean([v["hqc_per_shot"] for v in rows]),
            "max_abs_dpsi": max(v["exactness"]["max_abs_dpsi"] for v in rows),
            "max_leakage": max(v["exactness"]["leakage"] for v in rows),
            "all_exact": all(v["exactness"]["ok"] for v in rows),
            "nat_o2_campaign33_zz_mean": _mean([v["nat_o2_campaign33_definition"]["n_zz"] for v in rows]),
            "nat_o2_campaign33_1q_mean": _mean([v["nat_o2_campaign33_definition"]["n_1q"] for v in rows])}


def ratio(a, b):
    return None if (a is None or b in (None, 0)) else float(a) / float(b)


def verdict_for(lat, cur, ded, ncur, nded, det):
    """prompts/34 Goal: shortens iff (i) fewer qubits, (ii) mean a2a CZ of the coarse step smaller by more
    than the current three-seed spread, (iii) routed CZ and native ZZ both smaller.  Meaningfully: the
    two-qubit ratios <= 0.5."""
    sq = ded["n_qubits"] < cur["n_qubits"]
    sa = (cur["cz_a2a_mean"] - ded["cz_a2a_mean"]) > cur["cz_a2a_spread"]
    sr = ded["cz_routed_seed7"] < cur["cz_routed_seed7"]
    native_applicable = ncur is not None and nded is not None
    sn = (nded["zz_mean"] < ncur["zz_mean"]) if native_applicable else None
    r = {"qubits": ratio(ded["n_qubits"], cur["n_qubits"]),
         "cz_a2a_mean": ratio(ded["cz_a2a_mean"], cur["cz_a2a_mean"]),
         "cz_routed": ratio(ded["cz_routed_seed7"], cur["cz_routed_seed7"]),
         "zz_native": ratio(nded["zz_mean"], ncur["zz_mean"]) if native_applicable else None,
         "depth_a2a": ratio(ded["depth_a2a_mean"], cur["depth_a2a_mean"]),
         "depth_routed": ratio(ded["depth_routed_seed7"], cur["depth_routed_seed7"]),
         "two_qubit_depth": ratio(ded["depth_2q_a2a_mean"], cur["depth_2q_a2a_mean"]),
         "two_qubit_depth_routed": ratio(ded["depth_2q_routed_seed7"], cur["depth_2q_routed_seed7"]),
         "two_qubit_depth_native": ratio(nded["depth_2q_mean"], ncur["depth_2q_mean"]) if native_applicable else None}
    shortens = bool(sq and sa and sr and (sn if native_applicable else True))
    twoq = [r["cz_a2a_mean"], r["cz_routed"]] + ([r["zz_native"]] if native_applicable else [])
    v = {"lattice": lat, "shortens_qubits": bool(sq), "shortens_2q_a2a": bool(sa), "shortens_2q_routed": bool(sr),
         "shortens_2q_native": sn, "native_applicable": native_applicable, "shortens": shortens,
         "shortens_meaningfully": bool(shortens and all(x <= 0.5 for x in twoq)),
         "ratios": r, "a2a_margin": cur["cz_a2a_mean"] - ded["cz_a2a_mean"],
         "a2a_spread_current": cur["cz_a2a_spread"], "meaningful_threshold": 0.5,
         "coarse_step": "the S2 coarse step (B=0 first reference, k = 1, with diag and preparation)"}
    if det is not None:
        v["detection_single_flip"] = {nm: {s: det[nm][s]["detected_fraction"] for s in det[nm]} for nm in CODECS}
        v["random_acceptance"] = {nm: {s: det[nm][s]["random_acceptance"] for s in det[nm]} for nm in CODECS}
        if "saturation_at_plan" in det["current"]["B=0"]:
            v["saturation_at_plan"] = {nm: {s: det[nm][s]["saturation_at_plan"]["N_a_over_dim"] for s in det[nm]}
                                       for nm in CODECS}
    return v


def stage_assemble(args):
    from skqd.report import GateResult, write_report
    t0 = time.time()
    R = GateResult("ENC_compare", "encoding comparison at fixed physics: current vertex-local codec vs the dedup "
                                  "codec E2 (one bit per link) and the E5' assignment search (prompts/34)")
    frags = {}
    for nm in ("equiv", "compile", "native", "kingston", "f", "detect", "assign", "e4"):
        frags[nm] = load(frag_path(nm)) if os.path.exists(frag_path(nm)) else None
    data = {"what_pass_means": ("PASS means measured, not good (as K0): every comparison number is computed and the "
                                "current codec reproduces the signed numbers; the physics reading is in `verdict`"),
            "prompt": "prompts/34_encoding_comparison.md", "planner_list": "reports/encodings_candidate_list_20261007.md",
            "flag_dedup": UNSIGNED, "qpu_seconds": 0, "hqc": 0,
            "fragments": {k: (os.path.relpath(frag_path(k), ROOT) if v is not None else None) for k, v in frags.items()},
            "timing": {k: (v.get("timing") or v.get("stamp")) for k, v in frags.items() if v is not None}}
    for nm, v in frags.items():
        if v is not None and nm in ("compile", "native", "kingston"):
            data["timing"][nm] = {"stamp": v.get("stamp"), "per_invocation_s": v.get("timing")}
    s2 = load(p("validation", "S2.json"))["data"]
    # ---------------- C1 regression
    cmp_ = frags["compile"]
    exp = {lat: s2[lat]["per_term_cz"] for lat in ("2x2", "2x3")}
    exp_r = {lat: s2[lat]["per_term_cz_routed"] for lat in ("2x2", "2x3")}
    got, got_r, mism = {}, {}, []
    if cmp_:
        for lat in ("2x2", "2x3"):
            got[lat] = {t: cmp_["results"][f"{lat}|current|term|{t}"]["a2a"]["7"]["cz"] for t in exp[lat]
                        if f"{lat}|current|term|{t}" in cmp_["results"]}
            got_r[lat] = {t: cmp_["results"][f"{lat}|current|term|{t}"]["routed"]["7"]["cz"] for t in exp[lat]
                          if f"{lat}|current|term|{t}" in cmp_["results"]}
            for t in exp[lat]:
                if got[lat].get(t) != exp[lat][t]:
                    mism.append(f"{lat} {t} a2a {got[lat].get(t)} != {exp[lat][t]}")
                if got_r[lat].get(t) != exp_r[lat][t]:
                    mism.append(f"{lat} {t} routed {got_r[lat].get(t)} != {exp_r[lat][t]}")
    match = bool(cmp_) and not mism
    step_exp = {lat: (s2[lat]["coarse_step"]["all_to_all"]["cz"], s2[lat]["coarse_step"]["routed"]["cz"])
                for lat in ("2x2", "2x3")}
    step_got = {}
    if cmp_:
        for lat in ("2x2", "2x3"):
            r_ = cmp_["results"].get(f"{lat}|current|step|with_diag")
            if r_:
                step_got[lat] = (r_["a2a"]["7"]["cz"], r_["routed"]["7"]["cz"])
    step_match = all(step_got.get(lat) == tuple(step_exp[lat]) for lat in step_exp)
    checks = run_checks(args)
    data["regression"] = {"s2_per_term_cz_expected": exp, "s2_per_term_cz_routed_expected": exp_r,
                          "per_term_cz_current": got, "per_term_cz_routed_current": got_r,
                          "s2_per_term_cz_match": match, "mismatches": mism,
                          "coarse_step_expected_a2a_routed": step_exp, "coarse_step_current_a2a_routed": step_got,
                          "coarse_step_match": step_match, "checks": checks,
                          "baseline_pytest_before_changes": "476 passed, 19 skipped (step 0, 2026-10-07)"}
    R.add("C1 regression: current-codec per-term CZ (a2a seed 7 and routed) at 2x2 and 2x3 = validation/S2.json; "
          "coarse step = S2; pytest; check_package",
          f"per-term match {match} ({len(mism)} mismatches), step {step_got}; pytest: {checks.get('pytest_summary')}; "
          f"check_package rc {checks.get('check_package_rc')}",
          "all equal; pytest all pass; rc 0",
          match and step_match and checks.get("pytest_ok") and checks.get("check_package_rc") == 0)
    # ---------------- C2 / C3 equivalence
    eq = frags["equiv"]
    data["equiv"] = eq
    c2 = c3 = False
    if eq:
        rt = []
        aeq = []
        for lat, L in eq["lattices"].items():
            for nm, row in L["codecs"].items():
                rt.append(row["round_trip_ok"] == row["dim"] and row["distinct_codewords"] == row["dim"])
                aeq.append(all(v["equal"] for v in row["random_acceptance"].values()))
        d3 = eq["lattices"]["2x3"]["codecs"]["dedup"]
        d2 = eq["lattices"]["2x2"]["codecs"]["dedup"]
        c2 = all(rt) and all(aeq)
        R.add("C2 round trip: dedup 82/82 and 1727/1727 (and current), codewords distinct, a = dim/2^n per sector "
              "(exhaustive for n <= 13)",
              f"dedup {d2['round_trip_ok']}/{d2['dim']}, {d3['round_trip_ok']}/{d3['dim']}; all round trips "
              f"{sum(rt)}/{len(rt)}; a equal {sum(aeq)}/{len(aeq)}", "all", c2)
        tdev = max(v.get("max_deviation", float("inf")) for L in eq["lattices"].values() for v in L["dedup_terms"].values())
        tloc = all(v.get("locality_ok") for L in eq["lattices"].values() for v in L["dedup_terms"].values())
        cdev = max(L["dedup_circuits_summary"]["max_deviation"] for L in eq["lattices"].values())
        clk = max(L["dedup_circuits_summary"]["max_leakage"] for L in eq["lattices"].values())
        ncirc = sum(L["dedup_circuits_summary"]["n"] for L in eq["lattices"].values())
        c3 = tloc and tdev <= TERM_TOL and cdev <= EXACT_TOL and clk <= LEAK_TOL and ncirc == 72
        R.add("C3 exactness: every dedup term (localize locality, deviation) and every dedup coarse circuit "
              "(28 + 44) against krylov.coarse_states",
              f"terms local {tloc}, max term dev {tdev:.1e}; circuits {ncirc}, max dev {cdev:.1e}, max leak {clk:.1e}",
              f"local; <= {TERM_TOL:g}; 72; <= {EXACT_TOL:g}; <= {LEAK_TOL:g}", c3)
    else:
        R.add("C2 round trip", "equiv stage not run", "run --stage equiv", False)
        R.add("C3 exactness", "equiv stage not run", "run --stage equiv", False)
    # ---------------- C4 counts
    nat = frags["native"] or {}
    comp = {}
    c4_parts = []
    if cmp_:
        for lat, nfam in (("2x2", 28), ("2x3", 44)):
            comp[lat] = {}
            for nm in CODECS:
                terms = {t: {"ir": cmp_["results"][f"{lat}|{nm}|term|{t}"]["ir"],
                             "cz_a2a": {s: cmp_["results"][f"{lat}|{nm}|term|{t}"]["a2a"][s]["cz"] for s in ("7", "8", "9")},
                             "depth_2q_a2a_seed7": cmp_["results"][f"{lat}|{nm}|term|{t}"]["a2a"]["7"]["depth_2q"],
                             "cz_routed": cmp_["results"][f"{lat}|{nm}|term|{t}"]["routed"]["7"]["cz"]}
                         for t in term_list(int(lat[-1])) if f"{lat}|{nm}|term|{t}" in cmp_["results"]}
                fam = family_summary(cmp_, lat, nm)
                comp[lat][nm] = {"terms": terms, "step_with_diag": step_summary(cmp_, lat, nm, "with_diag"),
                                 "step_without_diag": step_summary(cmp_, lat, nm, "without_diag"), "family": fam}
                c4_parts.append(len(terms) == len(term_list(int(lat[-1]))) and fam is not None
                                and fam["n_circuits"] == nfam)
    nsum = {nm: native_summary(nat, nm) for nm in CODECS}
    native_ok = (nat.get("skipped") is not None) or all(nsum[nm] is not None and nsum[nm]["n_circuits"] == 44
                                                          for nm in CODECS)
    data["counts"] = comp
    data["native"] = {"summary": nsum, "skipped": nat.get("skipped"), "what": nat.get("what"),
                      "nat_o2_note": nat.get("nat_o2_note"), "measurement_note": nat.get("measurement_note"),
                      "versions": nat.get("versions"),
                      "per_circuit": {k: {"zz": v["counts"]["n_zz"], "phasedx": v["counts"]["n_phasedx"],
                                          "depth_2q": v["counts"]["depth_2q"], "hqc_per_shot": v["hqc_per_shot"],
                                          "max_abs_dpsi": v["exactness"]["max_abs_dpsi"],
                                          "leakage": v["exactness"]["leakage"], "ok": v["exactness"]["ok"],
                                          "nat_o2_campaign33_zz": v["nat_o2_campaign33_definition"]["n_zz"]}
                                      for k, v in sorted(nat.get("circuits", {}).items())}}
    c4 = bool(c4_parts) and all(c4_parts) and len(c4_parts) == 4 and native_ok
    native_exact = nat.get("skipped") is not None or all(nsum[nm] and nsum[nm]["all_exact"] for nm in CODECS)
    R.add("C4 counts complete: per-term and per-circuit rows for both codecs (IR, a2a seeds 7/8/9, routed, native "
          "or native.skipped), coarse-step totals with and without diag; native circuits exact (Q1 bars)",
          f"{sum(c4_parts)}/4 (lattice, codec) blocks; native "
          + ("skipped" if nat.get("skipped") else f"{[nsum[nm]['n_circuits'] if nsum[nm] else 0 for nm in CODECS]} "
                                                  f"circuits, exact {native_exact}"),
          "4/4; 44 + 44 exact", c4 and native_exact)
    # ---------------- C5 f
    ff = frags["f"]
    kg = frags["kingston"]
    data["f"] = ff
    data["kingston"] = kg
    c5 = False
    kcmp = {}
    if ff and kg:
        h2ok = all("f_gate_only_mean" in ff["codecs"][nm] for nm in CODECS)
        kb = {nm: kg["circuits"].get(f"{nm}|B0_ref117_k1") for nm in CODECS}
        k_ok = all(kb[nm] is not None for nm in CODECS)
        repro = {}
        if kb.get("current"):
            k1 = load(p("validation", "K1_2x3_fpilot.json"))["data"]["prediction_prereg"]["B0_ref117_k1"]
            k0 = load(p("validation", "K0_2x3_2x4.json"))["data"]["2x3"]["live"]
            b = kb["current"]
            repro = {"k1_prereg_B0_ref117_k1": {"cz": k1["cz"], "scheduled_duration_s": k1["scheduled_duration_s"],
                                                 "f_gates_layout": k1["f_bracket"]["f_gates_layout (no idle)"],
                                                 "f_idle_aware_echo": k1["f_bracket"]["f_idle_aware echo"]},
                     "k0_live_record_block": {"id": k0["circuit"]["id"], "cz": k0["n_cz"],
                                              "scheduled_duration_s": k0["schedule"]["scheduled_duration_s"]},
                     "this_run": {"cz": b["n_cz"], "scheduled_duration_s": b["schedule"]["scheduled_duration_s"],
                                  "f_gates_layout": b["f_gates_layout"],
                                  "f_idle_aware_echo": b["idle"]["echo"]["f_idle_aware"]},
                     "tolerance_duration_s": 1e-12, "tolerance_note": "K0.4's 1e-12 s; CZ exact"}
            repro["cz_equal"] = b["n_cz"] == k1["cz"] == k0["n_cz"]
            repro["duration_abs_diff_k1_s"] = abs(b["schedule"]["scheduled_duration_s"] - k1["scheduled_duration_s"])
            repro["duration_abs_diff_k0_s"] = abs(b["schedule"]["scheduled_duration_s"] - k0["schedule"]["scheduled_duration_s"])
            repro["f_gates_layout_rel_diff_k1"] = abs(b["f_gates_layout"] - repro["k1_prereg_B0_ref117_k1"]["f_gates_layout"]) \
                / repro["k1_prereg_B0_ref117_k1"]["f_gates_layout"]
            repro["ok"] = bool(repro["cz_equal"] and repro["duration_abs_diff_k1_s"] <= 1e-12
                               and repro["duration_abs_diff_k0_s"] <= 1e-12)
        kcmp["reproduction_current"] = repro
        k4 = all(kb[nm]["schedule"]["k0_4_ok"] for nm in CODECS) if k_ok else False
        dedup_exact = bool(k_ok and kb["dedup"]["exactness"]["ok"])
        c5 = h2ok and k_ok and bool(repro.get("ok")) and k4 and dedup_exact
        R.add("C5 f complete: H2-2 gate-only per circuit + mean/worst (both codecs); kingston gate-only, idle-aware "
              "(echo, 0.174) and ALAP duration for B0_ref117_k1 (both codecs, exactness-gated routing, K0.4 schedule "
              "check), current codec reproducing K0/K1",
              f"H2-2 {h2ok}; kingston {k_ok}, K0.4 {k4}, dedup routing exact {dedup_exact}; repro CZ "
              f"{repro.get('cz_equal')}, |dT| {repro.get('duration_abs_diff_k1_s', float('nan')):.1e} s",
              "all; CZ equal; |dT| <= 1e-12 s", c5)
    else:
        R.add("C5 f complete", "f or kingston stage not run", "run --stage kingston, --stage f", False)
    data["kingston_reproduction"] = kcmp
    # ---------------- C6 detection
    dd = frags["detect"]
    data["detect"] = dd
    c6 = False
    if dd:
        L3 = dd["lattices"]["2x3"]
        L2 = dd["lattices"]["2x2"]
        c6 = (all("saturation_at_plan" in L3[nm][s] for nm in CODECS for s in L3[nm])
              and all("double_detected_fraction" in L2[nm][s] for nm in CODECS for s in L2[nm]))
        R.add("C6 detection complete: single flips (2x2, 2x3), double flips (2x2), a, saturation at the plan-of-record "
              "shots and the 3 sigma line",
              "; ".join(f"2x3 {nm} single {L3[nm]['B=0']['detected_fraction']:.4f}/{L3[nm]['B=1']['detected_fraction']:.4f}"
                        for nm in CODECS), "all fields present", c6)
    else:
        R.add("C6 detection complete", "detect stage not run", "run --stage detect", False)
    # ---------------- verdict
    verdict = {}
    if cmp_:
        for lat in ("2x2", "2x3"):
            cur = comp[lat]["current"]["step_with_diag"]
            ded = comp[lat]["dedup"]["step_with_diag"]
            v = verdict_for(lat, cur, ded, nsum["current"] if lat == "2x3" else None,
                            nsum["dedup"] if lat == "2x3" else None, dd["lattices"][lat] if dd else None)
            fc, fd = comp[lat]["current"]["family"], comp[lat]["dedup"]["family"]
            v["family_cross_check"] = {"cz_a2a_mean_ratio": ratio(fd["cz_a2a_mean"], fc["cz_a2a_mean"]),
                                       "cz_routed_mean_ratio": ratio(fd["cz_routed_mean"], fc["cz_routed_mean"]),
                                       "depth_2q_a2a_mean_ratio": ratio(fd["depth_2q_a2a_mean"], fc["depth_2q_a2a_mean"])}
            v["step_without_diag"] = {
                "cz_a2a_mean_ratio": ratio(comp[lat]["dedup"]["step_without_diag"]["cz_a2a_mean"],
                                           comp[lat]["current"]["step_without_diag"]["cz_a2a_mean"]),
                "cz_routed_ratio": ratio(comp[lat]["dedup"]["step_without_diag"]["cz_routed_seed7"],
                                         comp[lat]["current"]["step_without_diag"]["cz_routed_seed7"])}
            verdict[lat] = v
        verdict["dedup"] = dict(verdict["2x3"])
        verdict["dedup"]["per_lattice"] = {"2x2": verdict["2x2"]}
        if ff:
            verdict["dedup"]["h2_2_f_gate_only_mean"] = {nm: ff["codecs"][nm].get("f_gate_only_mean") for nm in CODECS}
        if kg:
            verdict["dedup"]["kingston_B0_ref117_k1"] = {
                nm: {"cz": kg["circuits"][f"{nm}|B0_ref117_k1"]["n_cz"],
                     "scheduled_duration_s": kg["circuits"][f"{nm}|B0_ref117_k1"]["schedule"]["scheduled_duration_s"],
                     "f_gates_layout": kg["circuits"][f"{nm}|B0_ref117_k1"]["f_gates_layout"],
                     "f_idle_aware_echo": kg["circuits"][f"{nm}|B0_ref117_k1"]["idle"]["echo"]["f_idle_aware"]}
                for nm in CODECS if f"{nm}|B0_ref117_k1" in kg["circuits"]}
        proto = load(p("scratch", "planner", "encodings_prototype_20261007.json"))["sections"]
        pc = proto["D_compile"]["2x3"]["terms"]
        mine = {nm: comp["2x3"][nm]["step_without_diag"] for nm in CODECS}
        verdict["prototype_comparison"] = {
            "prototype_step_without_diag_a2a_seed7": {nm: pc[nm]["_step_without_diag"]["cz_all_to_all"] for nm in CODECS},
            "prototype_step_without_diag_routed": {nm: pc[nm]["_step_without_diag"].get("cz_routed") for nm in CODECS},
            "measured_step_without_diag_a2a_seed7": {nm: mine[nm]["cz_a2a"]["7"] for nm in CODECS},
            "measured_step_without_diag_routed_seed7": {nm: mine[nm]["cz_routed_seed7"] for nm in CODECS},
            "prototype_detection_2x3": {nm: {s: proto["C_detection"]["2x3"][nm][s]["detected_fraction"]
                                             for s in ("B=0", "B=1")} for nm in CODECS}}
        pcmp = verdict["prototype_comparison"]
        pcmp["a2a_identical"] = pcmp["prototype_step_without_diag_a2a_seed7"] == pcmp["measured_step_without_diag_a2a_seed7"]
        pcmp["routed_identical"] = pcmp["prototype_step_without_diag_routed"] == pcmp["measured_step_without_diag_routed_seed7"]
        pcmp["disagrees_beyond_seed_spread"] = any(
            abs(pcmp["prototype_step_without_diag_a2a_seed7"][nm] - mine[nm]["cz_a2a_mean"]) > max(mine[nm]["cz_a2a_spread"], 0)
            for nm in CODECS)
    aa = frags["assign"]
    if aa:
        verdict["assign"] = {"best_step_cz_ratio": aa.get("best_step_cz_ratio"),
                             "detection_unchanged": aa.get("detection_unchanged"),
                             "best_interior": aa.get("best_interior"), "best_corner": aa.get("best_corner"),
                             "quick": aa.get("quick")}
    data["assign"] = aa
    data["e4"] = frags["e4"]
    data["verdict"] = verdict
    req = ["shortens_qubits", "shortens_2q_a2a", "shortens_2q_routed", "shortens_2q_native", "shortens",
           "shortens_meaningfully", "ratios", "detection_single_flip", "random_acceptance", "saturation_at_plan"]
    rkeys = ["qubits", "cz_a2a_mean", "cz_routed", "zz_native", "depth_a2a", "depth_routed", "two_qubit_depth"]
    vd = verdict.get("dedup", {})
    c7 = (all(k in vd for k in req) and all(vd["ratios"].get(k) is not None for k in rkeys)
          and "assign" in verdict and verdict["assign"]["best_step_cz_ratio"] is not None
          and verdict["assign"]["detection_unchanged"] is not None)
    R.add("C7 verdict fields present (verdict.dedup.* and verdict.assign.*), computed by the prompts/34 definition",
          f"dedup fields {sum(k in vd for k in req)}/{len(req)}, ratios {sum(vd.get('ratios', {}).get(k) is not None for k in rkeys)}"
          f"/{len(rkeys)}, assign {'assign' in verdict}", "all", c7)
    # ---------------- C8 bookkeeping (report generated below; registration; scope)
    scope = scope_check()
    data["scope"] = scope
    R.data = data
    R.runtime_s = time.time() - t0
    reg = registration_check()
    data["registration"] = reg
    c8_pre = scope["ok"] and reg["ok"]
    R.add("C8 bookkeeping: report generated from the JSON, gate registered (run_gate resolves it, update_status lists "
          "it), nothing under the campaign33 / CI paths changed, dedup flagged unsigned, no push",
          f"scope ok {scope['ok']} ({len(scope['forbidden_changes'])} forbidden changes); registration {reg}",
          "all", c8_pre)
    path = R.save()
    saved = load(path)
    write_report("ENC_compare.md", report_text(saved))
    subprocess.run([sys.executable, p("scripts", "update_status.py")], cwd=ROOT, check=False)
    print(R.criteria_table())
    print(f"status {saved['status']}")
    return 0 if saved["status"] == "PASS" else 1


def run_checks(args):
    if args.skip_tests:
        return {"skipped": True, "pytest_ok": False, "pytest_summary": "n/a (--skip-tests)", "check_package_rc": None}
    t0 = time.time()
    tp = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests", "-p", "no:cacheprovider"], cwd=ROOT,
                        capture_output=True, text=True)
    lines = [ln for ln in tp.stdout.strip().splitlines() if ln.strip()]
    summ = lines[-1] if lines else "no output"
    cp = subprocess.run([sys.executable, p("scripts", "check_package.py")], cwd=ROOT, capture_output=True, text=True)
    return {"pytest_ok": tp.returncode == 0, "pytest_summary": summ, "pytest_s": time.time() - t0,
            "check_package_rc": cp.returncode,
            "check_package_tail": cp.stdout.strip().splitlines()[-3:] if cp.stdout.strip() else []}


FORBIDDEN = ("ci/requests/", "ci/status", "data/campaign33/", "src/skqd/campaign33/", "scripts/campaign33",
             "validation/ci_", "reports/ci-")


def scope_check():
    st = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    changed = [ln[3:] for ln in st.splitlines() if ln.strip()]
    bad = [c for c in changed if c.startswith(FORBIDDEN)]
    return {"forbidden_prefixes": list(FORBIDDEN), "forbidden_changes": bad, "ok": not bad,
            "note": "git status --porcelain at assemble time; the dedup files carry the UNSIGNED flag"}


def registration_check():
    import run_gate
    script, _a = run_gate.resolve("ENC_compare")
    with open(p("scripts", "update_status.py")) as fh:
        us = fh.read()
    return {"run_gate_resolves": os.path.basename(script) == "gate_ENC_compare.py",
            "update_status_lists": '("ENC_compare"' in us,
            "ok": os.path.basename(script) == "gate_ENC_compare.py" and '("ENC_compare"' in us}


# =========================================================================================== report
def _f(x, spec="{:.4g}"):
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}".replace(",", " ")
    try:
        return spec.format(x)
    except (TypeError, ValueError):
        return str(x)


def report_text(saved):
    from skqd.report import md_table
    d = saved["data"]
    v = d.get("verdict", {})
    vd = v.get("dedup", {})
    c = d.get("counts", {})
    ns = d.get("native", {}).get("summary", {})
    ff = d.get("f") or {}
    kg = (d.get("kingston") or {}).get("circuits", {})
    det = (d.get("detect") or {}).get("lattices", {})
    lines = [f"# Gate ENC_compare -- encoding comparison at fixed physics (prompts/34)", "",
             f"Status: **{saved['status']}** ({len(saved['criteria'])} criteria).  Generated by "
             f"`scripts/gate_ENC_compare.py --stage assemble` from `validation/ENC_compare.json`; every number "
             f"below is read from that file.  Commit {saved['environment'].get('git_commit')}, "
             f"{saved['environment'].get('timestamp')}.  0 QPU s, 0 HQC.", "",
             f"**What PASS means.** {d.get('what_pass_means')}", "",
             f"**Flag.** {d.get('flag_dedup')}", "",
             "Jargon: *codec* = the map from basis states to qubit bit strings; *dedup* = encoding E2, one flux bit "
             "per link instead of one per link end; *a2a* = all-to-all connectivity; *routed* = transpiled onto a "
             "heavy-hex coupling map; *native ZZ* = ZZPhase gates after the Quantinuum compiler; *two-qubit depth* = "
             "depth of the circuit with the one-qubit gates removed; *random acceptance a* = probability that a "
             "uniformly random string decodes into the sector; *saturation* $Na/\\dim$ (rule C22).", "",
             "## Criteria", "", criteria_md(saved), ""]
    # ---- comparison table
    rows = []
    for lat in ("2x2", "2x3"):
        if lat not in c:
            continue
        cu, de = c[lat]["current"]["step_with_diag"], c[lat]["dedup"]["step_with_diag"]
        rows.append([lat, "qubits", _f(cu["n_qubits"]), _f(de["n_qubits"]), _f(de["n_qubits"] / cu["n_qubits"], "{:.3f}")])
        rows.append([lat, "CZ a2a, coarse step (mean of seeds 7/8/9; spread)",
                     f"{_f(cu['cz_a2a_mean'], '{:.1f}')} ({cu['cz_a2a_spread']})",
                     f"{_f(de['cz_a2a_mean'], '{:.1f}')} ({de['cz_a2a_spread']})",
                     _f(de["cz_a2a_mean"] / cu["cz_a2a_mean"], "{:.3f}")])
        rows.append([lat, f"CZ routed heavy-hex, coarse step (seed 7; seeds 7/8/9 spread)",
                     f"{_f(cu['cz_routed_seed7'])} ({cu['cz_routed_spread']})",
                     f"{_f(de['cz_routed_seed7'])} ({de['cz_routed_spread']})",
                     _f(de["cz_routed_seed7"] / cu["cz_routed_seed7"], "{:.3f}")])
        cw, dw = c[lat]["current"]["step_without_diag"], c[lat]["dedup"]["step_without_diag"]
        rows.append([lat, "CZ a2a / routed, step without diag (seed 7)", f"{cw['cz_a2a']['7']} / {cw['cz_routed_seed7']}",
                     f"{dw['cz_a2a']['7']} / {dw['cz_routed_seed7']}",
                     _f(dw["cz_a2a"]["7"] / cw["cz_a2a"]["7"], "{:.3f}") + " / " +
                     _f(dw["cz_routed_seed7"] / cw["cz_routed_seed7"], "{:.3f}")])
        rows.append([lat, "two-qubit depth a2a (mean of seeds)", _f(cu["depth_2q_a2a_mean"], "{:.1f}"),
                     _f(de["depth_2q_a2a_mean"], "{:.1f}"), _f(de["depth_2q_a2a_mean"] / cu["depth_2q_a2a_mean"], "{:.3f}")])
        rows.append([lat, "depth a2a (mean of seeds)", _f(cu["depth_a2a_mean"], "{:.1f}"), _f(de["depth_a2a_mean"], "{:.1f}"),
                     _f(de["depth_a2a_mean"] / cu["depth_a2a_mean"], "{:.3f}")])
        rows.append([lat, "depth / two-qubit depth routed (seed 7)",
                     f"{cu['depth_routed_seed7']} / {cu['depth_2q_routed_seed7']}",
                     f"{de['depth_routed_seed7']} / {de['depth_2q_routed_seed7']}",
                     _f(de["depth_routed_seed7"] / cu["depth_routed_seed7"], "{:.3f}") + " / " +
                     _f(de["depth_2q_routed_seed7"] / cu["depth_2q_routed_seed7"], "{:.3f}")])
        fc, fd = c[lat]["current"]["family"], c[lat]["dedup"]["family"]
        if fc and fd:
            rows.append([lat, f"family ({fc['n_circuits']} circuits): CZ a2a mean / routed mean",
                         f"{_f(fc['cz_a2a_mean'], '{:.1f}')} / {_f(fc['cz_routed_mean'], '{:.1f}')}",
                         f"{_f(fd['cz_a2a_mean'], '{:.1f}')} / {_f(fd['cz_routed_mean'], '{:.1f}')}",
                         _f(fd["cz_a2a_mean"] / fc["cz_a2a_mean"], "{:.3f}") + " / " +
                         _f(fd["cz_routed_mean"] / fc["cz_routed_mean"], "{:.3f}")])
        if lat == "2x3" and ns.get("current") and ns.get("dedup"):
            a, b = ns["current"], ns["dedup"]
            rows.append([lat, "native ZZ (H2-2, compile_native level 2; mean, min-max of 44)",
                         f"{_f(a['zz_mean'], '{:.1f}')} ({a['zz_min']}-{a['zz_max']})",
                         f"{_f(b['zz_mean'], '{:.1f}')} ({b['zz_min']}-{b['zz_max']})", _f(b["zz_mean"] / a["zz_mean"], "{:.3f}")])
            rows.append([lat, "native PhasedX mean / two-qubit depth mean", f"{_f(a['phasedx_mean'], '{:.1f}')} / "
                         f"{_f(a['depth_2q_mean'], '{:.1f}')}", f"{_f(b['phasedx_mean'], '{:.1f}')} / {_f(b['depth_2q_mean'], '{:.1f}')}",
                         _f(b["depth_2q_mean"] / a["depth_2q_mean"], "{:.3f}") + " (2q depth)"])
            rows.append([lat, "native ZZ, campaign33 NAT-O2 definition (pytket L0 + qiskit L1; mean)",
                         _f(a["nat_o2_campaign33_zz_mean"], "{:.1f}"), _f(b["nat_o2_campaign33_zz_mean"], "{:.1f}"),
                         _f(b["nat_o2_campaign33_zz_mean"] / a["nat_o2_campaign33_zz_mean"], "{:.3f}")])
            rows.append([lat, "HQC per shot (mean)", _f(a["hqc_per_shot_mean"], "{:.3f}"), _f(b["hqc_per_shot_mean"], "{:.3f}"),
                         _f(b["hqc_per_shot_mean"] / a["hqc_per_shot_mean"], "{:.3f}")])
        if lat == "2x3" and ff.get("codecs", {}).get("current", {}).get("f_gate_only_mean") is not None:
            a, b = ff["codecs"]["current"], ff["codecs"]["dedup"]
            rows.append([lat, "H2-2 gate-only f mean / worst", f"{_f(a['f_gate_only_mean'])} / {_f(a['f_gate_only_worst'])}",
                         f"{_f(b['f_gate_only_mean'])} / {_f(b['f_gate_only_worst'])}",
                         _f(b["f_gate_only_mean"] / a["f_gate_only_mean"], "{:.3f}")])
            rows.append([lat, "H2-2 f with memory, mid ESTIMATE", _f(a["f_with_memory_mid_ESTIMATE"]),
                         _f(b["f_with_memory_mid_ESTIMATE"]), _f(b["f_with_memory_mid_ESTIMATE"] / a["f_with_memory_mid_ESTIMATE"], "{:.3f}")])
        if lat == "2x3" and "current|B0_ref117_k1" in kg and "dedup|B0_ref117_k1" in kg:
            a, b = kg["current|B0_ref117_k1"], kg["dedup|B0_ref117_k1"]
            rows.append([lat, "kingston B0_ref117_k1: routed CZ / active qubits", f"{a['n_cz']} / {a['n_active_qubits']}",
                         f"{b['n_cz']} / {b['n_active_qubits']}", _f(b["n_cz"] / a["n_cz"], "{:.3f}")])
            rows.append([lat, "kingston ALAP duration (us)", _f(a["schedule"]["scheduled_duration_s"] * 1e6, "{:.3f}"),
                         _f(b["schedule"]["scheduled_duration_s"] * 1e6, "{:.3f}"),
                         _f(b["schedule"]["scheduled_duration_s"] / a["schedule"]["scheduled_duration_s"], "{:.3f}")])
            rows.append([lat, "kingston f gate-only (layout) / idle-aware echo / idle-aware 0.174",
                         f"{_f(a['f_gates_layout'], '{:.3e}')} / {_f(a['idle']['echo']['f_idle_aware'], '{:.3e}')} / "
                         f"{_f(a['idle']['transferred_0.174']['f_idle_aware'], '{:.3e}')}",
                         f"{_f(b['f_gates_layout'], '{:.3e}')} / {_f(b['idle']['echo']['f_idle_aware'], '{:.3e}')} / "
                         f"{_f(b['idle']['transferred_0.174']['f_idle_aware'], '{:.3e}')}",
                         _f(b["f_gates_layout"] / a["f_gates_layout"], "{:.3f}") + " (gate-only)"])
        if lat in det:
            for s in ("B=0", "B=1"):
                a, b = det[lat]["current"][s], det[lat]["dedup"][s]
                rows.append([lat, f"{s}: single flips detected", _f(a["detected_fraction"], "{:.4f}"),
                             _f(b["detected_fraction"], "{:.4f}"), "-"])
                rows.append([lat, f"{s}: random acceptance a", _f(a["random_acceptance"], "{:.3e}"),
                             _f(b["random_acceptance"], "{:.3e}"), _f(b["random_acceptance"] / a["random_acceptance"], "{:.1f}")])
                if "saturation_at_plan" in a:
                    rows.append([lat, f"{s}: saturation $Na/\\dim$ at N = {a['saturation_at_plan']['N']} (3 sigma line)",
                                 f"{_f(a['saturation_at_plan']['N_a_over_dim'], '{:.4g}')} ({_f(a['saturation_at_plan']['three_sigma_line'], '{:.3g}')})",
                                 f"{_f(b['saturation_at_plan']['N_a_over_dim'], '{:.4g}')} ({_f(b['saturation_at_plan']['three_sigma_line'], '{:.3g}')})",
                                 f"lambda* {_f(d['detect']['lambda_star'], '{:.4f}')}"])
    lines += ["## Comparison table (current vs dedup)", "",
              "The *coarse step* is gate S2's: the first $B=0$ reference, $k=1$, with the diagonal term and the "
              "state preparation.", "", md_table(["lattice", "quantity", "current", "dedup", "ratio dedup/current"], rows), ""]
    # ---- verdict
    if vd:
        r = vd["ratios"]
        lines += ["## Verdict (prompts/34 definition, judged at 2x3; 2x2 below)", "",
                  md_table(["field", "value"], [
                      ["shortens_qubits", _f(vd["shortens_qubits"])],
                      ["shortens_2q_a2a (mean a2a margin vs the current three-seed spread)",
                       f"{_f(vd['shortens_2q_a2a'])} (margin {_f(vd['a2a_margin'], '{:.1f}')} CZ, spread {vd['a2a_spread_current']})"],
                      ["shortens_2q_routed", _f(vd["shortens_2q_routed"])],
                      ["shortens_2q_native", _f(vd["shortens_2q_native"])],
                      ["**shortens**", f"**{_f(vd['shortens'])}**"],
                      ["**shortens_meaningfully** (all two-qubit ratios <= 0.5)", f"**{_f(vd['shortens_meaningfully'])}**"],
                      ["ratios qubits / CZ a2a / CZ routed / ZZ native",
                       f"{_f(r['qubits'], '{:.3f}')} / {_f(r['cz_a2a_mean'], '{:.3f}')} / {_f(r['cz_routed'], '{:.3f}')} / {_f(r['zz_native'], '{:.3f}')}"],
                      ["ratios depth a2a / depth routed / two-qubit depth a2a",
                       f"{_f(r['depth_a2a'], '{:.3f}')} / {_f(r['depth_routed'], '{:.3f}')} / {_f(r['two_qubit_depth'], '{:.3f}')}"],
                      ["2x2: shortens / meaningfully (no native leg at 2x2)",
                       f"{_f(vd['per_lattice']['2x2']['shortens'])} / {_f(vd['per_lattice']['2x2']['shortens_meaningfully'])}"
                       f" (ratios CZ a2a {_f(vd['per_lattice']['2x2']['ratios']['cz_a2a_mean'], '{:.3f}')}, routed "
                       f"{_f(vd['per_lattice']['2x2']['ratios']['cz_routed'], '{:.3f}')})"],
                  ]), ""]
        pc = v.get("prototype_comparison")
        if pc:
            lines += [f"**Planner prototype vs this gate.** Step without diag, a2a seed 7: prototype "
                      f"{pc['prototype_step_without_diag_a2a_seed7']}, measured {pc['measured_step_without_diag_a2a_seed7']} "
                      f"(identical: {_f(pc['a2a_identical'])}); routed: prototype {pc['prototype_step_without_diag_routed']}, "
                      f"measured {pc['measured_step_without_diag_routed_seed7']} (identical: {_f(pc['routed_identical'])}); "
                      f"disagreement beyond the seed spread: {_f(pc['disagrees_beyond_seed_spread'])}.", ""]
    aa = d.get("assign")
    if aa:
        lines += ["## E5' codeword-assignment search (current widths, flux bits fixed)", "",
                  md_table(["quantity", "value"], [
                      ["interior assignments scored (of 256) on hop4 + plaq1", _f(aa.get("n_interior_scored"))],
                      ["corner assignments scored (of 8) on hop0 + hop1 + plaq0", _f(aa.get("n_corner_scored"))],
                      ["current score interior / corner (CZ a2a seed 7)", f"{aa.get('current_interior_score')} / {aa.get('current_corner_score')}"],
                      ["best interior (id, score)", f"{aa.get('best_interior')} ({aa.get('best_interior_score')})"],
                      ["best corner (id, score)", f"{aa.get('best_corner')} ({aa.get('best_corner_score')})"],
                      ["coarse step without diag, current -> best (CZ a2a seed 7)",
                       f"{aa.get('current_step_cz')} -> {aa.get('best_step_cz')}"],
                      ["best_step_cz_ratio", _f(aa.get("best_step_cz_ratio"), "{:.4f}")],
                      ["detection unchanged (single-flip fractions identical at 2x3)", _f(aa.get("detection_unchanged"))],
                      ["quick (subsampled)", _f(aa.get("quick"))]]), "",
                  "The diagonal term is excluded on both sides of the ratio: its gate is written for the current bit "
                  "polarities (prompts/34 step 8 changes no production code).", ""]
    e4 = d.get("e4")
    if e4:
        er = []
        for s, x in e4["2x2"].items():
            er.append(["2x2", s, x["dim"], x["n_qubits"], _f(x["cz"]), _f(x["qsd_bound_23_48_4n"], "{:.3g}")])
        for lat in ("2x3", "2x4"):
            for s, x in e4[lat].items():
                er.append([lat, s, x["dim"], x["n_qubits"], "not built", _f(x["qsd_bound_23_48_4n"], "{:.3g}")])
        lines += ["## E4 dense sector encoding (documentation only, not a criterion)", "",
                  "One coarse step $e^{-i\\Delta t H_{\\rm sector}}$ synthesised as a single unitary (qiskit level 3, "
                  "seed 7); the quantum-Shannon-decomposition bound is $\\tfrac{23}{48}4^n$ CZ.", "",
                  md_table(["lattice", "sector", "dim", "qubits", "CZ (synthesised)", "QSD bound"], er), ""]
    ns_ = d.get("native", {})
    lines += ["## Notes", "",
              f"- Native path: {ns_.get('what')}.  {ns_.get('measurement_note')}  {ns_.get('nat_o2_note')}",
              "- Static-charge sectors are out of scope for the dedup codec (it raises NotImplementedError).",
              "- The kingston numbers use `gate_K0_2x3_2x4.evaluate_2x3` unchanged; for the dedup codec the K0 model "
              "and physics caches are filled with the dedup factory and embedding.",
              f"- 2x4 projection by formula: {json.dumps((ff.get('projection_2x4') or {}))}",
              f"- Stage wall times: see `data.timing` in the JSON.", ""]
    return "\n".join(lines)


def criteria_md(saved):
    out = ["| criterion | value | bar | result |", "|---|---|---|---|"]
    for c in saved["criteria"]:
        out.append(f"| {c['name']} | {c['value']} | {c['threshold']} | {'PASS' if c['passed'] else 'FAIL'} |")
    return "\n".join(out)


# =========================================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="assemble",
                    choices=["equiv", "compile", "native", "kingston", "f", "detect", "assign", "e4", "assemble", "all"])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--lattice", choices=["2", "3"], default=None)
    ap.add_argument("--codec", choices=list(CODECS), default=None)
    ap.add_argument("--sector", choices=["B0", "B1"], default=None)
    ap.add_argument("--kingston-circuit", choices=list(KINGSTON_CIRCUITS), default="B0_ref117_k1")
    ap.add_argument("--part", default=None, help="native stage: 'i/m' runs every m-th remaining circuit from i")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    stages = {"equiv": stage_equiv, "compile": stage_compile, "native": stage_native, "kingston": stage_kingston,
              "f": stage_f, "detect": stage_detect, "assign": stage_assign, "e4": stage_e4, "assemble": stage_assemble}
    if args.stage == "all":
        for s in ("equiv", "compile", "native", "kingston", "f", "detect", "assign", "e4"):
            stages[s](args)
        return stage_assemble(args)
    r = stages[args.stage](args)
    return r if isinstance(r, int) else 0


if __name__ == "__main__":
    sys.exit(main())
