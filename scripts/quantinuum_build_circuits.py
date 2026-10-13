#!/usr/bin/env python3
"""
prompts/26 A3: the signed 2x3 circuit family compiled to the Quantinuum native gate set
{Rz, PhasedX, ZZPhase} and frozen as byte-identical QASM (hqslib1) + pytket JSON + a manifest.

Runs in the isolated venv (pytket is not installed in `coding`):

    ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/quantinuum_build_circuits.py [--workers 6]

Per circuit of `gate_S2D.circuit_set(3)` (44 = 2 sectors x 11 references x k = 1..4):
  1. transpile exactly as gate S2D / the planner prototype (basis rz, rx, ry, rzz; coupling_map None;
     optimization_level 3; seed_transpiler 7) -> RZZ count (must be 2158);
  2. `quantinuum_native.ir_to_pytket` (direct writer, measure q[k] -> c[k]);
  3. `compile_native(..., "H2-2", level)` for levels 0 and 2 on the OFFLINE API handler (no login);
  4. dense statevector of each compiled circuit (`pytket_to_ir` + `circuits_qiskit.statevector_aer`)
     against the statevector of the ORIGINAL exact IR circuit (before transpilation): max |dpsi|
     after global-phase removal, leakage out of the codeword space, the measurement map;
  5. the frozen level = the level with the fewest ZZ gates among those that pass Q1 (ties: fewer
     PhasedX, then the lower level); QASM, JSON, manifest written; JSON and QASM round trips;
  6. the same circuit compiled at the frozen level for H1-1 and Helios-1 (byte identity of the QASM
     recorded; the offline handler of pytket-quantinuum 0.59.3 has no Helios-1 entry).
Two calibration circuits (all zeros; X on qubit 0) are frozen alongside.

Every circuit is written as soon as it is done (resumable; --force rebuilds).  Run one sector per
invocation (--sector B0, then --sector B1) to stay inside the 30-minute rule: with 6 workers x 2 Aer
threads on the i7-8750H a circuit takes ~3 min (level-2 compilation ~60 s, six 20-qubit statevectors).
"""
import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd import circuits_qiskit as cq  # noqa: E402
from skqd import quantinuum_native as qn  # noqa: E402

OUT = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
OUT_BY_LATTICE = {2: os.path.join(ROOT, "data", "quantinuum", "circuits_2x2"), 3: OUT,
                  4: os.path.join(ROOT, "data", "quantinuum", "circuits_2x4")}    # prompts/35 3.1(a)
G2 = 4.0
TRANSPILE = {"basis_gates": ["rz", "rx", "ry", "rzz"], "coupling_map": None,
             "optimization_level": 3, "seed_transpiler": 7}
LEVELS = (0, 2)
Q1_DPSI_MAX = 1e-10        # prompts/26 Q1 (the bound of gate S2_2x4 C2)
Q1_LEAK_MAX = 1e-9
RT_MAX = 1e-12             # prompts/26 Q3
RZZ_EXPECTED = 2158        # data/S2D_2x3_device_requirements.json counts.coarse_step.rzz
OTHER_DEVICES = ("H1-1", "Helios-1")
SELECTION_RULE = ("fewest ZZ gates among the levels that pass Q1 (max |dpsi| < 1e-10 after "
                  "global-phase removal, leakage < 1e-9, q[k] -> c[k], identity permutation); "
                  "ties: fewer PhasedX, then the lower level")

_G = {}                    # filled before the fork: model, embedding, circuit set, dt by sector


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def git_commit():
    import subprocess

    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


def circuit_id(twoB, r, k):
    return f"B{twoB // 2}_ref{int(r):02d}_k{int(k)}"


def state_check(ir, n, ref, emb):
    sv = cq.statevector_aer(ir, n, threads=_G["threads"])
    res = qn.global_phase_residual(sv, ref)
    res["leakage"] = float(emb.leakage(sv))
    res["max_abs_dprob"] = float(np.max(np.abs(np.abs(sv) ** 2 - np.abs(ref) ** 2)))
    return sv, res


def write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(text)
    os.replace(tmp, path)


def write_gz(path, text):
    """gzip with mtime 0 and no file name (deterministic bytes); the sha256 recorded elsewhere is the
    one of the UNCOMPRESSED text (prompts/35 3.1(a))."""
    import gzip

    tmp = path + ".tmp"
    with open(tmp, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as fh:
            fh.write(text.encode())
    os.replace(tmp, path)


def read_text(path):
    """A frozen circuit file, plain or gzipped (2x4)."""
    import gzip

    if path.endswith(".gz"):
        with gzip.open(path, "rb") as fh:
            return fh.read().decode()
    with open(path) as fh:
        return fh.read()


def build_one(i):
    from qiskit import transpile

    if _G.get("lattice", 3) == 4:
        return build_one_4(i)
    t0 = time.time()
    twoB, r, k, gates = _G["set"][i]
    cid = circuit_id(twoB, r, k)
    man_path = os.path.join(OUT, cid + ".manifest.json")
    if os.path.exists(man_path) and not _G["force"]:
        return cid, "kept"
    n = _G["n"]
    emb, M = _G["emb"], _G["model"]
    ref = cq.statevector_aer(gates, n, threads=_G["threads"])
    ref_leak = float(emb.leakage(ref))
    qc = cq.ir_to_qiskit(gates, n, measure=False)
    tt = time.time()
    tq = transpile(qc, **TRANSPILE)
    t_tr = time.time() - tt
    ir_t = qn.qiskit_to_ir(tq)
    _sv_t, res_t = state_check(ir_t, n, ref, emb)
    pc = qn.ir_to_pytket(ir_t, n, measure=True)

    levels, compiled = {}, {}
    for lvl in LEVELS:
        rec = {"level": lvl}
        tc = time.time()
        try:
            cc = qn.compile_native(pc, "H2-2", lvl)
        except qn.NativeCompileError as exc:      # recorded, the level is then not eligible
            rec.update({"error": f"{type(exc).__name__}: {exc}", "passes_Q1": False})
            levels[str(lvl)] = rec
            continue
        rec["compile_s"] = time.time() - tc
        rec["counts"] = qn.native_counts(cc)
        ir_c, nn, qmap = qn.pytket_to_ir(cc)
        _sv, res = state_check(ir_c, nn, ref, emb)
        rec["state_vs_original_ir"] = res
        rec["measure_map_identity"] = qmap == {q: q for q in range(n)}
        rec["implicit_permutation_identity"] = all(a == b for a, b in
                                                   cc.implicit_qubit_permutation().items())
        rec["passes_Q1"] = bool(res["max_abs_dpsi"] < Q1_DPSI_MAX and res["leakage"] < Q1_LEAK_MAX
                                and rec["measure_map_identity"] and rec["implicit_permutation_identity"])
        levels[str(lvl)] = rec
        compiled[lvl] = (cc, ir_c, _sv)
    ok = [lvl for lvl in compiled if levels[str(lvl)]["passes_Q1"]]
    if not ok:
        raise SystemExit(f"{cid}: no compiled level passes Q1 -- STOP (prompts/26): "
                         f"{json.dumps(levels)[:2000]}")
    frozen = min(ok, key=lambda L: (levels[str(L)]["counts"]["n_zz"],
                                    levels[str(L)]["counts"]["n_phasedx"], L))
    cc, ir_c, sv_c = compiled[frozen]
    qasm = qn.to_qasm(cc)
    js = qn.to_json(cc)
    js_text = json.dumps(js, sort_keys=True)
    # round trips (prompts/26 A4 / Q3)
    c_json = qn.from_json(json.loads(js_text))
    sv_json = cq.statevector_aer(qn.pytket_to_ir(c_json)[0], n, threads=_G["threads"])
    c_qasm = qn.from_qasm(qasm)
    sv_qasm = cq.statevector_aer(qn.pytket_to_ir(c_qasm)[0], n, threads=_G["threads"])
    rt = {"json_max_abs_dpsi_raw": float(np.max(np.abs(sv_json - sv_c))),
          "json": qn.global_phase_residual(sv_json, sv_c),
          "qasm": qn.global_phase_residual(sv_qasm, sv_c),
          "qasm_drops_global_phase": True,
          "qasm_counts_equal": qn.native_counts(c_qasm)["ops"] == qn.native_counts(cc)["ops"],
          "json_counts_equal": qn.native_counts(c_json)["ops"] == qn.native_counts(cc)["ops"]}
    # other devices at the frozen level
    other = {}
    for dev in OTHER_DEVICES:
        try:
            cd = qn.compile_native(pc, dev, frozen)
            qd = qn.to_qasm(cd)
            other[dev] = {"compiled": True, "qasm_sha256": sha256(qd),
                          "byte_identical_to_H2-2": qd == qasm, "counts": qn.native_counts(cd)}
        except Exception as exc:                  # recorded per device (DeviceNotAvailable)
            other[dev] = {"compiled": False, "error": f"{type(exc).__name__}: {exc}",
                          "kept": "the H2-2 circuit (same native gate set)"}
    # the reference string and its ideal probability (prompts/26 A6: exact p_ref per circuit)
    codec = emb.codec
    ref_bits = tuple(int(x) for x in codec.encode(M.basis.labels[int(r)]))
    ref_int = int(sum(b << q for q, b in enumerate(ref_bits)))
    p = np.abs(sv_c) ** 2
    top = int(np.argmax(p))
    counts = levels[str(frozen)]["counts"]
    lat = int(_G.get("lattice", 3))
    if lat != 3:                     # prompts/35 3.1(a): the rzz count of the prototype transpile
        counts = dict(counts, rzz_before=int(tq.count_ops().get("rzz", 0)))
    man = {
        "id": cid, "kind": f"signed_2x{lat}_coarse_step", "lattice": f"2x{lat}", "sector": f"B={twoB // 2}",
        "twoB": int(twoB), "reference": int(r), "k": int(k), "repetitions": 1,
        "dt": float(_G["dt"][twoB]), "g2": G2, "n_qubits": n,
        "family": (f"gate_S2D.circuit_set({lat}): CircuitFactory(Model({lat}), 4.0) default "
                   "(angle_mode exact, structured hopping), coarse_step(r, k, dt)"),
        "original_ir_counts": qn.ir_counts(gates), "original_ir_leakage": ref_leak,
        "transpile": {**TRANSPILE, "seconds": t_tr, "ops": {kk: int(v) for kk, v in tq.count_ops().items()},
                      "rzz": int(tq.count_ops().get("rzz", 0)), "global_phase": float(tq.global_phase),
                      "state_vs_original_ir": res_t},
        "levels": levels, "frozen_level": int(frozen), "selection_rule": SELECTION_RULE,
        "device_name_compiled_for": "H2-2", "compile_route": (
            "QuantinuumBackend(device, api_handler=QuantinuumAPIOffline(), compilation_config="
            "QuantinuumBackendCompilationConfig(allow_implicit_swaps=False, target_2qb_gate=ZZPhase, "
            "preserve_qubit_names=True)).get_compiled_circuit(circ, optimisation_level)"),
        "counts": counts, "hqc_per_shot": qn.hqc_per_shot(counts),
        "files": {"qasm": cid + ".qasm", "json": cid + ".json"},
        "qasm_sha256": sha256(qasm), "json_sha256": sha256(js_text),
        "round_trips": rt, "other_devices": other,
        "reference_bits": list(ref_bits), "reference_int": ref_int,
        "p_reference": float(p[ref_int]), "most_probable_int": top, "p_most_probable": float(p[top]),
        "frozen_state_leakage": float(emb.leakage(sv_c)),
        "statevector_engine": "circuits_qiskit.statevector_aer (Aer statevector, double precision, gate fusion on)",
        "versions": qn.versions(), "git_commit": _G["commit"],
        "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "build_s": time.time() - t0,
    }
    if i == _G.get("diagnose_index"):
        man["diagnostics"] = diagnose(pc, ir_t, ref, sv_c, emb, n)
    write_text(os.path.join(OUT, cid + ".qasm"), qasm)
    write_text(os.path.join(OUT, cid + ".json"), js_text)
    write_text(man_path, json.dumps(man, indent=1))
    return cid, f"built in {time.time() - t0:.0f} s (frozen level {frozen}, ZZ {counts['n_zz']}, " \
                f"PhasedX {counts['n_phasedx']}, dpsi {levels[str(frozen)]['state_vs_original_ir']['max_abs_dpsi']:.1e})"


def diagnose(pc, ir_t, ref, sv_c, emb, n):
    """One-circuit diagnostics: (a) level 2 on the UNITARY part (no measurement) -- the state is
    then exact, which locates the level-2 deviation in the removal of the Rz gates in front of
    the measurements; (b) the frozen circuit's state from qiskit.quantum_info (`statevector`)
    against Aer (`statevector_aer`), the engine cross-check (~3 min)."""
    out = {}
    pu = qn.ir_to_pytket(ir_t, n, measure=False)
    tc = time.time()
    cu = qn.compile_native(pu, "H2-2", 2)
    ir_u, nn, _ = qn.pytket_to_ir(cu)
    sv_u = cq.statevector_aer(ir_u, nn, threads=_G["threads"])
    out["level2_without_measurement"] = {
        "compile_s": time.time() - tc, "counts": qn.native_counts(cu),
        "state_vs_original_ir": qn.global_phase_residual(sv_u, ref),
        "leakage": float(emb.leakage(sv_u))}
    tq = time.time()
    sv_qi = cq.statevector(qn.pytket_to_ir(qn.compile_native(qn.ir_to_pytket(ir_t, n, True), "H2-2", 0))[0], n)
    out["engine_crosscheck_frozen_level0"] = {
        "max_abs_quantum_info_minus_aer": float(np.max(np.abs(sv_qi - sv_c))),
        "seconds": time.time() - tq,
        "note": "frozen circuit (level 0) state by qiskit.quantum_info.Statevector vs Aer, no phase removal"}
    return out


# =========================================================================== 2x4 (prompts/35 3.3)
LEVELS_4 = (0,)            # level 2 is not compiled per circuit at 2x4 (cost; at 2x2/2x3 it never passes the state bar)
SELECTION_RULE_4 = ("fewest ZZ gates among the levels that pass Q1L (local equivalence to the transpiled IR, "
                    "quantinuum_native.local_equivalence_35a: prompts/35a R2 (i)-(iii), q[k] -> c[k], identity permutation); ties: "
                    "fewer PhasedX, then the lower level; if no level passes, the pure rebase "
                    "AutoRebase({Rz, PhasedX, ZZPhase}) (compile_mode 'pure_rebase'); level 2 not attempted at 2x4 "
                    "(prompts/35a R4)")
DT_SOURCE_4 = ("gate_S2_2x4.dt_of(4, twoB): validation/E3.json, equal to Model(4).reference(4.0, twoB).dt to "
               "<= 4e-16 and fixed so that the build is bit-reproducible (the sparse eigensolver is not)")


def exact_coarse_4(M, r, k, dt):
    """The exact coarse state exp(-i k dt H) |r> over the 2x4 basis (krylov.apply_groups, the
    ideal_sector_distribution route at repetitions 1)."""
    from skqd.exact import mass_default
    from skqd.krylov import apply_groups, basis_vector, term_groups

    if "groups" not in _G:
        _G["groups"] = term_groups(M.terms, G2, mass_default(G2))
    return apply_groups(_G["groups"], basis_vector(M.basis.dim, int(r)), int(k) * float(dt))


def build_one_4(i):
    """One 2x4 circuit: prototype transpile, levels, Q1L, frozen gzipped files, manifest.  No dense
    statevector (R2): Q1S is the gate's sparse stage and the deferred GPU token QV_2x4."""
    from qiskit import transpile

    t0 = time.time()
    twoB, r, k, _none = _G["set"][i]
    cid = circuit_id(twoB, r, k)
    man_path = os.path.join(OUT, cid + ".manifest.json")
    if os.path.exists(man_path) and not _G["force"]:
        return cid, "kept"
    n, M = _G["n"], _G["model"]
    dt = float(_G["dt"][twoB])
    gates = _G["factory"].coarse_step(int(r), int(k), dt)
    qc = cq.ir_to_qiskit(gates, n, measure=False)
    tt = time.time()
    tq = transpile(qc, **TRANSPILE)
    t_tr = time.time() - tt
    ir_t = qn.qiskit_to_ir(tq)
    pc = qn.ir_to_pytket(ir_t, n, measure=True)
    levels, compiled = {}, {}
    for lvl in _G["levels"]:
        rec = {"level": lvl}
        tc = time.time()
        try:
            cc = qn.compile_native(pc, "H2-2", lvl)
        except qn.NativeCompileError as exc:
            rec.update({"error": f"{type(exc).__name__}: {exc}", "passes_Q1L": False})
            levels[str(lvl)] = rec
            continue
        rec["compile_s"] = time.time() - tc
        rec["counts"] = qn.native_counts(cc)
        tl = time.time()
        rec["Q1L"] = qn.local_equivalence_35a(ir_t, cc, n)
        rec["Q1L_s"] = time.time() - tl
        rec["passes_Q1L"] = bool(rec["Q1L"]["ok"])
        levels[str(lvl)] = rec
        compiled[lvl] = cc
    ok = [L for L in compiled if levels[str(L)]["passes_Q1L"]]
    if ok:
        frozen = min(ok, key=lambda L: (levels[str(L)]["counts"]["n_zz"], levels[str(L)]["counts"]["n_phasedx"], L))
        cc, mode = compiled[frozen], f"level{frozen}"
        q1l = levels[str(frozen)]["Q1L"]
    else:
        tc = time.time()
        cc = qn.compile_native(pc, pure_rebase=True)
        rec = {"compile_s": time.time() - tc, "counts": qn.native_counts(cc)}
        rec["Q1L"] = qn.local_equivalence_35a(ir_t, cc, n)
        rec["passes_Q1L"] = bool(rec["Q1L"]["ok"])
        levels["pure_rebase"] = rec
        frozen, mode, q1l = "pure_rebase", "pure_rebase", rec["Q1L"]
    # information (prompts/35 3.3 diagnosis): where a Q1L residual comes from -- the IR -> pytket writer
    # (pytket stores a parameter within < 1e-11 half-turns of a multiple of 1/4 as that multiple) or the compiler
    stop_q1l = not q1l["ok"]
    counts = dict(qn.native_counts(cc), rzz_before=int(tq.count_ops().get("rzz", 0)))
    qasm = qn.to_qasm(cc)
    js_text = json.dumps(qn.to_json(cc), sort_keys=True)
    other = {}
    for dev in OTHER_DEVICES:
        try:
            be = qn.offline_backend(dev)          # raises DeviceNotAvailable for a device the offline list lacks
            nq_dev = len(be.backend_info.architecture.nodes)
            if nq_dev < n:                        # H1-1 (20 qubits): not compiled, recorded
                other[dev] = {"compiled": False, "device_qubits": nq_dev,
                              "error": f"the offline machine list gives {dev} {nq_dev} qubits < {n}",
                              "kept": "the H2-2 circuit (same native gate set)"}
                continue
            cd = (qn.compile_native(pc, pure_rebase=True) if mode == "pure_rebase"
                  else qn.compile_native(pc, dev, int(frozen)))
            qd = qn.to_qasm(cd)
            other[dev] = {"compiled": True, "qasm_sha256": sha256(qd), "byte_identical_to_H2-2": qd == qasm,
                          "counts": qn.native_counts(cd)}
        except Exception as exc:                  # recorded per device (DeviceNotAvailable, qubit count)
            other[dev] = {"compiled": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                          "kept": "the H2-2 circuit (same native gate set)"}
    codec = _G["emb"].codec
    ref_bits = tuple(int(x) for x in codec.encode(M.basis.labels[int(r)]))
    ref_int = int(sum(b << q for q, b in enumerate(ref_bits)))
    psi = exact_coarse_4(M, r, k, dt)
    p = np.abs(psi) ** 2
    top = int(np.argmax(p))
    man = {
        "id": cid, "kind": "signed_2x4_coarse_step", "lattice": "2x4", "sector": f"B={twoB // 2}",
        "twoB": int(twoB), "reference": int(r), "k": int(k), "repetitions": 1, "dt": dt, "dt_source": DT_SOURCE_4,
        "g2": G2, "n_qubits": n,
        "family": ("gate_S2D.circuit_set(4): CircuitFactory(Model(4), 4.0) default (angle_mode exact, structured "
                   "hopping), coarse_step(r, k, dt); the term IR from gate_S2_2x4.preload_factory (data/S2_2x4/cache, "
                   "the same gate lists structured_term_gates returns)"),
        "original_ir_counts": qn.ir_counts(gates),
        "transpile": {**TRANSPILE, "seconds": t_tr, "ops": {kk: int(v) for kk, v in tq.count_ops().items()},
                      "rzz": int(tq.count_ops().get("rzz", 0)), "global_phase": float(tq.global_phase),
                      "state_vs_original_ir": "not computed at 2x4 (R2: no dense statevector); Q1S / QV_2x4"},
        "levels": levels, "frozen_level": frozen, "compile_mode": mode, "selection_rule": SELECTION_RULE_4,
        "Q1L": q1l, "Q1L_rule": "prompts/35a R2 (quantinuum_native.local_equivalence_35a)", "STOP_Q1L": bool(stop_q1l), "device_name_compiled_for": "H2-2",
        "compile_route": ("QuantinuumBackend(device, api_handler=QuantinuumAPIOffline(), compilation_config="
                          "QuantinuumBackendCompilationConfig(allow_implicit_swaps=False, target_2qb_gate=ZZPhase, "
                          "preserve_qubit_names=True)).get_compiled_circuit(circ, optimisation_level)"),
        "counts": counts, "hqc_per_shot": qn.hqc_per_shot(counts),
        "files": {"qasm": cid + ".qasm.gz", "json": cid + ".json.gz"}, "sha256_of": "the uncompressed text",
        "qasm_sha256": sha256(qasm), "json_sha256": sha256(js_text),
        "other_devices": other,
        "reference_bits": list(ref_bits), "reference_int": ref_int,
        "p_reference": float(p[int(r)]), "p_reference_source": "exact coarse state (krylov.apply_groups), basis index r",
        "most_probable_basis_index": top, "p_most_probable": float(p[top]),
        "versions": qn.versions(), "git_commit": _G["commit"],
        "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "build_s": time.time() - t0,
    }
    write_gz(os.path.join(OUT, cid + ".qasm.gz"), qasm)
    write_gz(os.path.join(OUT, cid + ".json.gz"), js_text)
    write_text(man_path, json.dumps(man, indent=1))
    if stop_q1l:
        return cid, (f"Q1L FAILS ({mode}): {json.dumps({k: q1l[k] for k in ('i_skeleton', 'ii_segments_vs_readback', 'rounding')}, default=str)[:600]}, first difference "
                     f"{q1l['i_skeleton']['first_difference']} -- STOP (prompts/35 section 7)")
    return cid, (f"built in {time.time() - t0:.0f} s ({mode}, ZZ {counts['n_zz']} = rzz_before "
                 f"{counts['rzz_before']}: {counts['n_zz'] == counts['rzz_before']}, PhasedX {counts['n_phasedx']}, "
                 f"Q1L ok, B {q1l['rounding']['state_bound_B']:.1e}, raw segments {q1l['segment_residual_raw']:.1e})")


def set_4():
    """circuit_set(4)'s (twoB, r, k) grid without the gate lists (they are built per worker)."""
    from skqd.exact import Model
    from skqd.krylov import references

    M = Model(4)
    out = [(twoB, int(r), k, None) for twoB in (0, 2) for r in references(M.basis, twoB) for k in (1, 2, 3, 4)]
    return M, out


def main_4(args, t0):
    import gate_S2_2x4 as S4

    from skqd.reference_sim import CodewordEmbedding

    M, cset = set_4()
    S4._MODELS[4] = M
    emb = CodewordEmbedding(M)
    dts = {tb: float(S4.dt_of(4, tb)) for tb in (0, 2)}
    ks = sorted(set(args.k or (1, 2, 3, 4)))
    idx = [i for i, c in enumerate(cset) if c[2] in ks]
    if args.sector:
        idx = [i for i in idx if circuit_id(*cset[i][:3]).startswith(args.sector + "_")]
    if args.only:
        keep = set(args.only)
        idx = [i for i in idx if circuit_id(*cset[i][:3]) in keep]
    thetas = sorted({k * dts[tb] for tb in (0, 2) for k in ks})
    _G.update({"set": cset, "model": M, "emb": emb, "n": int(emb.n), "force": args.force or bool(args.only),
               "threads": args.threads, "commit": git_commit(), "dt": dts, "lattice": 4,
               "levels": tuple(args.levels) if args.levels else LEVELS_4})
    if not args.index_only:
        _G["factory"] = S4.preload_factory(4, "exact", thetas)
        from skqd.exact import mass_default
        from skqd.krylov import term_groups

        _G["groups"] = term_groups(M.terms, G2, mass_default(G2))
        if args.level2_probe:
            return level2_probe_4(args.level2_probe, 1800.0)
        print(f"2x4 set: {len(cset)} circuits, {len(idx)} selected (k {ks}), {emb.n} qubits, levels "
              f"{_G['levels']} ({time.time() - t0:.0f} s)", flush=True)
        import multiprocessing as mp

        with mp.get_context("fork").Pool(args.workers) as pool:
            for cid, msg in pool.imap_unordered(build_one_4, idx):
                print(f"  {cid}: {msg} [{time.time() - t0:.0f} s]", flush=True)
        if not all(os.path.exists(os.path.join(OUT, c + ".manifest.json")) for c in ("CAL_zeros", "CAL_x0")):
            calibration_circuits(int(emb.n))
    write_index_4(cset, t0)
    return 0


def _level2_child(pc, conn):
    t = time.time()
    try:
        cc = qn.compile_native(pc, "H2-2", 2)
        conn.send({"finished": True, "compile_s": time.time() - t, "counts": qn.native_counts(cc)})
    except Exception as exc:                      # recorded
        conn.send({"finished": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}", "compile_s": time.time() - t})


def level2_probe_4(cid, cap_s):
    """prompts/35 3.3 cost record: pytket level 2 on ONE 2x4 circuit in a child process with a cap; the result
    decides whether level 2 is compiled per circuit (LEVELS_4) -> data/quantinuum/circuits_2x4/level2_probe.json."""
    import multiprocessing as mp

    from qiskit import transpile
    i = next(j for j, c in enumerate(_G["set"]) if circuit_id(*c[:3]) == cid)
    twoB, r, k, _ = _G["set"][i]
    gates = _G["factory"].coarse_step(int(r), int(k), float(_G["dt"][twoB]))
    tq = transpile(cq.ir_to_qiskit(gates, _G["n"], measure=False), **TRANSPILE)
    pc = qn.ir_to_pytket(qn.qiskit_to_ir(tq), _G["n"], measure=True)
    a, b = mp.get_context("fork").Pipe(duplex=False)
    p = mp.get_context("fork").Process(target=_level2_child, args=(pc, b))
    t0 = time.time()
    p.start()
    rec = a.recv() if a.poll(cap_s) else None
    if rec is None:
        p.kill()
        rec = {"finished": False, "capped_at_s": cap_s}
    p.join()
    rec.update({"id": cid, "cap_s": cap_s, "wall_s": time.time() - t0, "device": "H2-2", "level": 2,
                "rzz_before": int(tq.count_ops().get("rzz", 0)), "versions": qn.versions(), "git_commit": git_commit(),
                "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "decision": ("level 2 is not compiled per 2x4 circuit (LEVELS_4 = (0,)): one compile exceeds the 30-min "
                             "per-circuit cap of prompts/35 section 2" if not rec.get("finished") else
                             "level 2 finishes inside the cap on this circuit")})
    write_text(os.path.join(OUT, "level2_probe.json"), json.dumps(rec, indent=1))
    print(f"level-2 probe {cid}: {rec}", flush=True)
    return 0


def write_index_4(cset, t0):
    """index.json over the BUILT circuits (prompts/35 3.3: `built_k`), sha256 of the uncompressed texts."""
    ids_all = [circuit_id(*c[:3]) for c in cset]
    ids = [c for c in ids_all if os.path.exists(os.path.join(OUT, c + ".manifest.json"))]
    if not ids:
        return
    mans = [json.load(open(os.path.join(OUT, i + ".manifest.json"))) for i in ids]
    cals = [json.load(open(os.path.join(OUT, c + ".manifest.json"))) for c in ("CAL_zeros", "CAL_x0")
            if os.path.exists(os.path.join(OUT, c + ".manifest.json"))]
    # prompts/35a R4: every manifest records the level-2 attempt (scripted from level2_probe.json, never typed)
    pp = os.path.join(OUT, "level2_probe.json")
    probe = json.load(open(pp)) if os.path.exists(pp) else None
    for m in mans:
        if probe is None:
            break
        l2 = (f"capped at {probe['cap_s']:.0f} s on {probe['id']} (prompts/35a R4; attempt wall {probe['wall_s']:.0f} s)"
              if not probe.get("finished") else f"finished in {probe['compile_s']:.0f} s on {probe['id']}")
        la = {"0": m["levels"].get("0", {}).get("counts"), "2": l2}
        changed = m.get("levels_attempted") != la or m.get("selection_rule") != SELECTION_RULE_4
        m["levels_attempted"] = la
        m["selection_rule"] = SELECTION_RULE_4
        if "i_skeleton" not in m.get("Q1L", {}):
            m["Q1L_rule"] = ("prompts/35 raw form at build (before prompts/35a); the restated Q1L (35a R2) is recomputed "
                             "from the frozen files by gate_Q0P_2x3.py --lattice 4 --stage verify")
            changed = True
        if changed:
            write_text(os.path.join(OUT, m["id"] + ".manifest.json"), json.dumps(m, indent=1))
    zz = [m["counts"]["n_zz"] for m in mans]
    px = [m["counts"]["n_phasedx"] for m in mans]
    hq = [m["hqc_per_shot"] for m in mans]
    built_k = sorted({int(m["k"]) for m in mans})
    complete_k = [k for k in built_k if all(os.path.exists(os.path.join(OUT, circuit_id(c[0], c[1], k) + ".manifest.json"))
                                            for c in cset if c[2] == k)]
    index = {
        "produced_by": "scripts/quantinuum_build_circuits.py --lattice 4", "prompt": "prompts/35 3.3",
        "lattice": "2x4", "circuits": ids, "circuits_planned": ids_all, "calibration": [c["id"] for c in cals],
        "built_k": built_k, "complete_k": complete_k,
        "files": {m["id"]: {"qasm": m["files"]["qasm"], "json": m["files"]["json"],
                            "qasm_sha256": m["qasm_sha256"], "json_sha256": m["json_sha256"],
                            "frozen_level": m.get("frozen_level"), "compile_mode": m.get("compile_mode", "level0")}
                  for m in mans + cals},
        "sha256_of": "the uncompressed text of every .qasm.gz / .json.gz (gzip mtime 0, level 9)",
        "summary": {"n_circuits": len(mans),
                    "n_zz": {"min": min(zz), "max": max(zz), "mean": float(np.mean(zz))},
                    "n_phasedx": {"min": min(px), "max": max(px), "mean": float(np.mean(px))},
                    "hqc_per_shot": {"min": min(hq), "max": max(hq), "mean": float(np.mean(hq))},
                    "rzz_before": sorted({m["counts"]["rzz_before"] for m in mans}),
                    "frozen_levels": sorted({m["frozen_level"] for m in mans}, key=str),
                    "compile_modes": sorted({m.get("compile_mode", "level0") for m in mans})},
        "level2_probe": probe,
        "rebuild_command": ("~/.local/share/su2qc-quantinuum/venv/bin/python scripts/quantinuum_build_circuits.py "
                            "--lattice 4 --only <id> [--out <dir>]  (deterministic at pytket 2.18.4 / qiskit 2.5.2: "
                            "the sha256 above is the check)"),
        "device_name_compiled_for": "H2-2", "transpile": TRANSPILE, "levels": list(_G["levels"]),
        "selection_rule": SELECTION_RULE_4, "dt": _G["dt"], "dt_source": DT_SOURCE_4,
        "versions": qn.versions(), "python": sys.executable,
        "git_commit": git_commit(), "runtime_s_this_invocation": time.time() - t0,
        "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    write_text(os.path.join(OUT, "index.json"), json.dumps(index, indent=1))
    print(f"wrote {OUT}/index.json: {len(ids)} circuits, built_k {built_k}, ZZ {index['summary']['n_zz']} "
          f"({time.time() - t0:.0f} s)", flush=True)



def calibration_circuits(n):
    """CAL_zeros (measure only) and CAL_x0 (X on qubit 0, then measure), compiled at level 0."""
    from pytket import Circuit

    out = []
    for cid, xq in (("CAL_zeros", None), ("CAL_x0", 0)):
        c = Circuit(n, n)
        if xq is not None:
            c.X(xq)
        for q in range(n):
            c.Measure(q, q)
        cc = qn.compile_native(c, "H2-2", 0)
        ir, nn, qmap = qn.pytket_to_ir(cc)
        if nn > 20:                  # 2x4: the 28-qubit basis state from the exact sparse path
            from skqd.sparse_sim import run_sparse

            st = run_sparse(ir, nn)
            key = int(st.idx[int(np.argmax(np.abs(st.amp)))])
        else:
            sv = cq.statevector(ir, nn) if nn <= 12 else cq.statevector_aer(ir, nn)
            key = int(np.argmax(np.abs(sv)))
        qasm, js = qn.to_qasm(cc), json.dumps(qn.to_json(cc), sort_keys=True)
        counts = qn.native_counts(cc)
        gz = ".gz" if _G.get("lattice", 3) == 4 else ""
        man = {"id": cid, "kind": "calibration", "n_qubits": n, "x_on": xq,
               "expected_int": 0 if xq is None else (1 << xq), "statevector_argmax_int": key,
               "measure_map_identity": qmap == {q: q for q in range(n)},
               "counts": counts, "hqc_per_shot": qn.hqc_per_shot(counts), "frozen_level": 0,
               "files": {"qasm": cid + ".qasm" + gz, "json": cid + ".json" + gz},
               "qasm_sha256": sha256(qasm), "json_sha256": sha256(js),
               "versions": qn.versions(), "git_commit": git_commit(),
               "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
        if gz:
            man["sha256_of"] = "the uncompressed text"
            write_gz(os.path.join(OUT, cid + ".qasm.gz"), qasm)
            write_gz(os.path.join(OUT, cid + ".json.gz"), js)
        else:
            write_text(os.path.join(OUT, cid + ".qasm"), qasm)
            write_text(os.path.join(OUT, cid + ".json"), js)
        write_text(os.path.join(OUT, cid + ".manifest.json"), json.dumps(man, indent=1))
        out.append(man)
    return out


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--lattice", type=int, choices=(2, 3, 4), default=3,
                    help="2x<L> ladder (prompts/35 R5; default 3 = the frozen prompts/26 family, unchanged)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--threads", type=int, default=2, help="Aer threads per worker")
    ap.add_argument("--only", nargs="*", default=None, help="circuit ids to (re)build")
    ap.add_argument("--force", action="store_true", help="rebuild existing manifests")
    ap.add_argument("--sector", choices=("B0", "B1"), default=None,
                    help="build one sector only (each half fits the 30-minute rule)")
    ap.add_argument("--k", type=int, nargs="*", default=None,
                    help="--lattice 4: the k values to build (prompts/35 3.3 build order k = 1, then 2, 3, 4)")
    ap.add_argument("--levels", type=int, nargs="*", default=None,
                    help="--lattice 4: the pytket optimisation levels to try (default LEVELS_4)")
    ap.add_argument("--out", default=None, help="output directory (default data/quantinuum/circuits_2x<L>); "
                                                "the rebuild check of an ignored 2x4 circuit writes elsewhere")
    ap.add_argument("--index-only", action="store_true", help="--lattice 4: (re)write index.json from the manifests")
    ap.add_argument("--level2-probe", default=None, metavar="ID",
                    help="--lattice 4: time pytket level 2 on one circuit with a 30-min cap (level2_probe.json)")
    args = ap.parse_args()
    t0 = time.time()
    lat = int(args.lattice)
    OUT = os.path.abspath(args.out) if args.out else OUT_BY_LATTICE[lat]
    os.makedirs(OUT, exist_ok=True)
    from gate_S2D import circuit_set
    from skqd.reference_sim import CodewordEmbedding

    if lat == 4:
        return main_4(args, t0)
    M, _F, cset = circuit_set(lat)
    emb = CodewordEmbedding(M)
    _G.update({"set": cset, "model": M, "emb": emb, "n": int(emb.n), "force": args.force,
               "threads": args.threads, "commit": git_commit(), "diagnose_index": 0,  # the first circuit carries the one-off diagnostics
               "dt": {tb: float(M.reference(G2, tb).dt) for tb in (0, 2)}, "lattice": lat})
    print(f"circuit set: {len(cset)} circuits, {emb.n} qubits ({time.time() - t0:.0f} s)", flush=True)
    idx = list(range(len(cset)))
    if args.sector:
        idx = [i for i in idx if circuit_id(*cset[i][:3]).startswith(args.sector + "_")]
    if args.only:
        keep = set(args.only)
        idx = [i for i in idx if circuit_id(*cset[i][:3]) in keep]
        if args.force is False:
            _G["force"] = True
    import multiprocessing as mp

    with mp.get_context("fork").Pool(args.workers) as pool:
        for cid, msg in pool.imap_unordered(build_one, idx):
            print(f"  {cid}: {msg} [{time.time() - t0:.0f} s]", flush=True)
    cals = calibration_circuits(int(emb.n))
    if lat == 3:
        # the offline machine list the compiler used (a second, dated source for the device table)
        from pytket.extensions.quantinuum import QuantinuumAPIOffline

        write_text(os.path.join(ROOT, "data", "quantinuum", "offline_machine_list.json"), json.dumps({
            "source": "pytket.extensions.quantinuum.QuantinuumAPIOffline().get_machine_list()",
            "pytket-quantinuum": qn.versions()["pytket-quantinuum"],
            "note": "embedded in the package, no network; the noise_specs dates are the package's",
            "machines": QuantinuumAPIOffline().get_machine_list()}, indent=1))
    # index (only once all circuits are on disk)
    ids = [circuit_id(*c[:3]) for c in cset]
    missing = [i for i in ids if not os.path.exists(os.path.join(OUT, i + ".manifest.json"))]
    if missing:
        print(f"{len(missing)} circuit(s) not built yet ({missing[:3]} ...): index.json not written "
              f"({time.time() - t0:.0f} s)", flush=True)
        return 0
    mans = [json.load(open(os.path.join(OUT, i + ".manifest.json"))) for i in ids]
    zz = [m["counts"]["n_zz"] for m in mans]
    px = [m["counts"]["n_phasedx"] for m in mans]
    hq = [m["hqc_per_shot"] for m in mans]
    index = {
        "produced_by": "scripts/quantinuum_build_circuits.py",
        "prompt": "prompts/26 A3" if lat == 3 else "prompts/35 3.1(a) / 3.2",
        "circuits": ids, "calibration": [c["id"] for c in cals],
        "files": {m["id"]: {"qasm_sha256": m["qasm_sha256"], "json_sha256": m["json_sha256"],
                            "frozen_level": m.get("frozen_level")} for m in mans + cals},
        "summary": {"n_circuits": len(mans),
                    "n_zz": {"min": min(zz), "max": max(zz), "mean": float(np.mean(zz))},
                    "n_phasedx": {"min": min(px), "max": max(px), "mean": float(np.mean(px))},
                    "hqc_per_shot": {"min": min(hq), "max": max(hq), "mean": float(np.mean(hq))},
                    "frozen_levels": sorted({m["frozen_level"] for m in mans})},
        "device_name_compiled_for": "H2-2", "transpile": TRANSPILE, "levels": list(LEVELS),
        "selection_rule": SELECTION_RULE, "versions": qn.versions(), "python": sys.executable,
        "git_commit": git_commit(), "runtime_s_this_invocation": time.time() - t0,
        "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    if lat != 3:
        index["lattice"] = f"2x{lat}"
        index["summary"]["rzz_before"] = sorted({m["counts"]["rzz_before"] for m in mans})
    write_text(os.path.join(OUT, "index.json"), json.dumps(index, indent=1))
    print(f"wrote {OUT}/index.json: ZZ {index['summary']['n_zz']}, PhasedX "
          f"{index['summary']['n_phasedx']}, HQC/shot {index['summary']['hqc_per_shot']} "
          f"({time.time() - t0:.0f} s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
