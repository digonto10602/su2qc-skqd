"""Export a FROZEN compressed family as Quantinuum native circuits in exactly the on-disk format that the package's
`scripts/quantinuum_submit.py` reads for the frozen circuits (`load_index`, `load_manifest`, `load_frozen`):

    <out>/index.json                 circuits, calibration, files {id: sha256s}, summary, provenance
    <out>/<id>.json                  pytket JSON  (json.dumps(qn.to_json(c), sort_keys=True); sha256 in the manifest)
    <out>/<id>.qasm                  OpenQASM 2   (qn.to_qasm(c); drops the global phase, as for the frozen circuits)
    <out>/<id>.manifest.json         id, kind, files, qasm_sha256, json_sha256, counts, hqc_per_shot, ...

Conversion = the package path used for every compressed family (scripts/native_family.py): IR from the loader
(`c2x4.families.get_family_ir`), `cz` -> `cp(pi)` (identical matrix; the package's `ir_to_pytket` has no `cz`),
`qn.ir_to_pytket(measure=True)`, `qn.compile_native(., "H2-2", optimisation_level=0)` (offline backend, no network),
the conversion proof Q1L `qn.local_equivalence_35a(ir, native, n, structured=True)` with its rounding bound.

Checks per circuit (written into the manifest, bar = the package's Q1 bar: max|dpsi| < 1e-10 after global-phase
removal, leakage < 1e-9, q[k] -> c[k], identity implicit permutation):
  * native statevector (Aer, double, fusion off) against the package's EXACT coarse state
    skqd.krylov.coarse_states(term_groups(Model(2).terms, 4, mass_default(4)), e_ref, dt, k)[k] (dt of the manifest
    of the frozen family's circuit with the same id), embedded with skqd.reference_sim.CodewordEmbedding;
  * native statevector against the family's IR statevector (state_vs_original_ir, as in the frozen manifests);
  * JSON and QASM round trips (re-read, re-simulated, counts equal).
The calibration circuits CAL_zeros / CAL_x0 are copied byte for byte from the frozen directory (their sha256 checked
against the frozen manifests): they contain no lattice circuit (measure only / X on qubit 0, then measure).

Run with the isolated venv (never the coding env):
  ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/export_quantinuum_family.py \
      --family compressed_circuit_llm_2x2_classA --frozen-dir data/quantinuum/circuits_2x2 \
      --out data/families/native_2x2/compressed_circuit_llm_2x2_classA
No login, no network, no submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(STUDY, "src"))
sys.path.insert(0, os.path.join(ROOT, "src"))

from c2x4.env import git_commit, write_json                                     # noqa: E402
from c2x4.families import family_header, family_path, get_family_ir            # noqa: E402
from skqd import circuits_qiskit as cq                                          # noqa: E402
from skqd import quantinuum_native as qn                                        # noqa: E402
from skqd.device_req import clean_shot_fraction                                 # noqa: E402
from skqd.exact import Model, mass_default                                      # noqa: E402
from skqd.krylov import basis_vector, coarse_states, term_groups                # noqa: E402
from skqd.reference_sim import CodewordEmbedding                                # noqa: E402

Q1_DPSI_MAX, Q1_LEAK_MAX = 1e-10, 1e-9
SELECTION_RULE = ("single level: pytket optimisation level 0 on the structured compressed IR (cz -> cp(pi)); the "
                  "circuit is kept only if it passes Q1 against the package's exact coarse state and Q1L")


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(text)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--frozen-dir", required=True, help="the package's frozen directory of the same lattice (read only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="H2-2")
    args = ap.parse_args()
    t0 = time.time()
    fdir = args.frozen_dir if os.path.isabs(args.frozen_dir) else os.path.join(ROOT, args.frozen_dir)
    out = args.out if os.path.isabs(args.out) else os.path.join(STUDY, args.out)
    if os.path.exists(os.path.join(out, "index.json")):
        raise SystemExit(f"{out} already holds an index.json: an export is written once (choose another --out)")
    os.makedirs(out, exist_ok=True)
    hdr = family_header(args.family)
    lx = int(hdr["lattice"].split("x")[1])
    with open(os.path.join(fdir, "index.json")) as fh:
        f_index = json.load(fh)
    dev = json.load(open(os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")))["specs"]
    M = Model(lx)
    groups = term_groups(M.terms, 4.0, mass_default(4.0))
    emb = CodewordEmbedding(M)
    ints = np.asarray(emb.ints, dtype=np.int64)
    n = int(emb.n)
    fam = get_family_ir(args.family)
    ids = [cid for cid, _g, _md in fam]
    if ids != list(f_index["circuits"]):
        raise SystemExit(f"circuit ids/order differ from the frozen index: {ids} vs {f_index['circuits']}")
    mans = []
    for cid, g, md in fam:
        t1 = time.time()
        f_man = json.load(open(os.path.join(fdir, cid + ".manifest.json")))
        for key in ("twoB", "reference", "k", "dt", "n_qubits"):
            if f_man[key] != md[key]:
                raise SystemExit(f"{cid}: {key} {md[key]!r} differs from the frozen manifest {f_man[key]!r}")
        g = [("cp", qs, math.pi) if nm == "cz" else (nm, qs, par) for nm, qs, par in g]
        pc = qn.ir_to_pytket(g, n, measure=True)
        cc = qn.compile_native(pc, args.device, 0)
        cnt = qn.native_counts(cc)
        q1l = qn.local_equivalence_35a(g, cc, n, structured=True)
        ir_c, nn, qmap = qn.pytket_to_ir(cc)
        sv_nat = cq.statevector_aer(ir_c, nn, fusion=False)
        sv_ir = cq.statevector_aer(g, n, fusion=False)
        tgt = coarse_states(groups, basis_vector(M.basis.dim, md["reference"]), f_man["dt"], md["k"])[md["k"]]
        full = np.zeros(2 ** n, dtype=complex)
        full[ints] = tgt
        vs_exact = qn.global_phase_residual(sv_nat, full)
        vs_exact["leakage"] = float(emb.leakage(sv_nat))
        vs_ir = qn.global_phase_residual(sv_nat, sv_ir)
        vs_ir["leakage"] = float(emb.leakage(sv_nat))
        mm_id = qmap == {q: q for q in range(n)}
        perm_id = all(a == b for a, b in cc.implicit_qubit_permutation().items())
        passes_q1 = bool(vs_exact["max_abs_dpsi"] < Q1_DPSI_MAX and vs_exact["leakage"] < Q1_LEAK_MAX
                         and mm_id and perm_id)
        if not (passes_q1 and q1l["ok"]):
            raise SystemExit(f"{cid}: Q1 {passes_q1} / Q1L {q1l['ok']} -- STOP, nothing exported for this circuit: "
                             f"{json.dumps(vs_exact)} {json.dumps({k: str(v)[:300] for k, v in q1l.items()})}")
        qasm = qn.to_qasm(cc)
        js_text = json.dumps(qn.to_json(cc), sort_keys=True)
        c_json = qn.from_json(json.loads(js_text))
        sv_json = cq.statevector_aer(qn.pytket_to_ir(c_json)[0], n, fusion=False)
        c_qasm = qn.from_qasm(qasm)
        sv_qasm = cq.statevector_aer(qn.pytket_to_ir(c_qasm)[0], n, fusion=False)
        rt = {"json_max_abs_dpsi_raw": float(np.max(np.abs(sv_json - sv_nat))),
              "json": qn.global_phase_residual(sv_json, sv_nat),
              "qasm": qn.global_phase_residual(sv_qasm, sv_nat), "qasm_drops_global_phase": True,
              "qasm_counts_equal": qn.native_counts(c_qasm)["ops"] == cnt["ops"],
              "json_counts_equal": qn.native_counts(c_json)["ops"] == cnt["ops"]}
        if not (rt["qasm_counts_equal"] and rt["json_counts_equal"] and rt["json"]["max_abs_dpsi"] < Q1_DPSI_MAX
                and rt["qasm"]["max_abs_dpsi"] < Q1_DPSI_MAX):
            raise SystemExit(f"{cid}: round trip fails: {json.dumps(rt)}")
        p = np.abs(sv_nat) ** 2
        top = int(np.argmax(p))
        ref_int = int(ints[md["reference"]])
        if ref_int != int(f_man["reference_int"]):
            raise SystemExit(f"{cid}: reference_int {ref_int} != frozen {f_man['reference_int']}")
        f_gate = {}
        for key, s_ in dev.items():
            if "eps2" not in s_:
                continue
            ero = 0.5 * (s_["eps_ro_0"] + s_["eps_ro_1"])
            f_gate[s_.get("device_name", key)] = clean_shot_fraction(cnt["n_zz"], cnt["n_phasedx"], n,
                                                                     s_["eps2"], s_["eps1"], ero)
        man = {
            "id": cid, "kind": f"compressed_2x{lx}_coarse_step_class{md['class']}", "lattice": hdr["lattice"],
            "sector": f"B={md['twoB'] // 2}", "twoB": int(md["twoB"]), "reference": int(md["reference"]),
            "k": int(md["k"]), "repetitions": 1, "dt": float(f_man["dt"]), "g2": 4.0, "n_qubits": n,
            "family": args.family, "class": md["class"], "family_version": md["version"],
            "family_file": os.path.relpath(family_path(args.family), ROOT),
            "family_file_sha256": sha256_file(family_path(args.family)),
            "content_sha256_ir": md["content_sha256"], "contract": md["contract"], "valid_use": md["valid_use"],
            "global_phase_vs_target_ir": md["global_phase_vs_target"],
            "frozen_counterpart": {"dir": os.path.relpath(fdir, ROOT), "id": cid,
                                   "n_zz": f_man["counts"]["n_zz"], "n_phasedx": f_man["counts"]["n_phasedx"],
                                   "depth_2q": f_man["counts"]["depth_2q"]},
            "original_ir_counts": qn.ir_counts(g), "ir_n_2q": md["n_2q"], "ir_depth_2q": md["depth_2q"],
            "ir_rewrite": "cz -> cp(pi) (identical matrix diag(1,1,1,-1)) before ir_to_pytket",
            "transpile": None,
            "levels": {"0": {"level": 0, "counts": cnt, "state_vs_exact_target": vs_exact,
                             "state_vs_original_ir": vs_ir, "measure_map_identity": mm_id,
                             "implicit_permutation_identity": perm_id, "passes_Q1": passes_q1}},
            "frozen_level": 0, "selection_rule": SELECTION_RULE,
            "Q1L": {"ok": bool(q1l["ok"]), "rounding_state_bound_B": q1l["iii_rounding"]["state_bound_B"],
                    "detail": json.loads(json.dumps(q1l, default=str))},
            "device_name_compiled_for": args.device,
            "compile_route": ("QuantinuumBackend(device, api_handler=QuantinuumAPIOffline(), compilation_config="
                              "QuantinuumBackendCompilationConfig(allow_implicit_swaps=False, target_2qb_gate=ZZPhase, "
                              "preserve_qubit_names=True)).get_compiled_circuit(circ, 0)  [skqd.quantinuum_native."
                              "compile_native]"),
            "counts": cnt, "hqc_per_shot": qn.hqc_per_shot(cnt),
            "clean_shot_fraction_gate_only": f_gate,
            "clean_shot_fraction_formula": ("skqd.device_req.clean_shot_fraction(n_zz, n_phasedx, n_qubits, eps2, eps1, "
                                            "(eps_ro_0 + eps_ro_1)/2), data/quantinuum/devices_20261002.json"),
            "files": {"qasm": cid + ".qasm", "json": cid + ".json"},
            "qasm_sha256": sha256(qasm), "json_sha256": sha256(js_text), "round_trips": rt,
            "reference_bits": [int((ref_int >> q) & 1) for q in range(n)], "reference_int": ref_int,
            "p_reference": float(p[ref_int]), "most_probable_int": top, "p_most_probable": float(p[top]),
            "frozen_state_leakage": float(emb.leakage(sv_nat)),
            "statevector_engine": "circuits_qiskit.statevector_aer (Aer statevector, double precision, fusion off)",
            "versions": qn.versions(), "git_commit": git_commit(),
            "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "build_s": time.time() - t1,
        }
        write_text(os.path.join(out, cid + ".qasm"), qasm)
        write_text(os.path.join(out, cid + ".json"), js_text)
        write_text(os.path.join(out, cid + ".manifest.json"), json.dumps(man, indent=1))
        mans.append(man)
        print(f"{cid}: ZZ {cnt['n_zz']} PhasedX {cnt['n_phasedx']} depth2q {cnt['depth_2q']} | vs exact "
              f"{vs_exact['max_abs_dpsi']:.1e} leak {vs_exact['leakage']:.1e} Q1L {q1l['ok']} "
              f"f(H2-2) {f_gate.get('H2-2', float('nan')):.4f} ({time.time() - t1:.1f} s)", flush=True)
    # calibration circuits: byte-identical copies of the frozen ones (sha256 checked)
    cals = []
    for cal in f_index.get("calibration", []):
        cm = json.load(open(os.path.join(fdir, cal + ".manifest.json")))
        for kind in ("json", "qasm"):
            src = os.path.join(fdir, cm["files"][kind])
            with open(src) as fh:
                text = fh.read()
            if sha256(text) != cm[f"{kind}_sha256"]:
                raise SystemExit(f"{src}: sha256 differs from its frozen manifest")
            shutil.copyfile(src, os.path.join(out, cm["files"][kind]))
        cm = dict(cm, copied_from=os.path.relpath(fdir, ROOT), copied_by="2x4_compression_using_ai_v1/scripts/"
                  "export_quantinuum_family.py (byte-identical .json/.qasm; this manifest = the frozen one + this key)")
        write_text(os.path.join(out, cal + ".manifest.json"), json.dumps(cm, indent=1))
        cals.append(cm)
    zz = [m["counts"]["n_zz"] for m in mans]
    px = [m["counts"]["n_phasedx"] for m in mans]
    d2 = [m["counts"]["depth_2q"] for m in mans]
    hq = [m["hqc_per_shot"] for m in mans]
    devs = sorted({d for m in mans for d in m["clean_shot_fraction_gate_only"]})
    index = {
        "produced_by": "2x4_compression_using_ai_v1/scripts/export_quantinuum_family.py",
        "prompt": "owner 2026-10-28 'make the 2x2 compressed family' (2x4_compression_using_ai_v1/notes/011)",
        "family": args.family, "class": hdr["class"], "family_version": hdr["version"],
        "family_file": os.path.relpath(family_path(args.family), ROOT),
        "family_file_sha256": sha256_file(family_path(args.family)),
        "contract": hdr["contract"], "valid_use": hdr["valid_use"],
        "circuits": [m["id"] for m in mans], "calibration": [c["id"] for c in cals],
        "files": {**{m["id"]: {"qasm_sha256": m["qasm_sha256"], "json_sha256": m["json_sha256"],
                               "frozen_level": 0} for m in mans},
                  **{c["id"]: {"qasm_sha256": c["qasm_sha256"], "json_sha256": c["json_sha256"],
                               "frozen_level": 0, "source": "calibration (copied from the frozen directory)"}
                     for c in cals}},
        "summary": {"n_circuits": len(mans),
                    "n_zz": {"min": min(zz), "max": max(zz), "mean": float(np.mean(zz))},
                    "n_phasedx": {"min": min(px), "max": max(px), "mean": float(np.mean(px))},
                    "depth_2q": {"min": min(d2), "max": max(d2), "mean": float(np.mean(d2))},
                    "hqc_per_shot": {"min": min(hq), "max": max(hq), "mean": float(np.mean(hq))},
                    "frozen_levels": [0],
                    "max_abs_dpsi_vs_exact": max(m["levels"]["0"]["state_vs_exact_target"]["max_abs_dpsi"]
                                                 for m in mans),
                    "max_leakage": max(m["levels"]["0"]["state_vs_exact_target"]["leakage"] for m in mans),
                    "all_Q1": all(m["levels"]["0"]["passes_Q1"] for m in mans),
                    "all_Q1L": all(m["Q1L"]["ok"] for m in mans),
                    "max_Q1L_rounding_state_bound_B": max(m["Q1L"]["rounding_state_bound_B"] for m in mans),
                    "clean_shot_fraction_gate_only": {
                        d: {"min": min(m["clean_shot_fraction_gate_only"][d] for m in mans),
                            "mean": float(np.mean([m["clean_shot_fraction_gate_only"][d] for m in mans])),
                            "max": max(m["clean_shot_fraction_gate_only"][d] for m in mans)} for d in devs}},
        "frozen_counterpart": {"dir": os.path.relpath(fdir, ROOT), "summary": f_index["summary"]},
        "device_name_compiled_for": args.device, "transpile": None, "levels": [0],
        "selection_rule": SELECTION_RULE, "versions": qn.versions(), "python": sys.executable,
        "git_commit": git_commit(), "runtime_s_this_invocation": time.time() - t0,
        "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "lattice": hdr["lattice"],
    }
    write_text(os.path.join(out, "index.json"), json.dumps(index, indent=1))
    print(json.dumps(index["summary"], indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
