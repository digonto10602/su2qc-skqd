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
A relative --out is resolved against the family's LATTICE folder (notes/012): the command above writes
2x2_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_classA/.  --frozen-dir is relative to
the repository root.
No login, no network, no submission.

Options added for the 2x3 / 2x4 exports (owner 2026-10-28, H2-2SC syntax check of the compressed families; the 2x2
behaviour is the default and unchanged):
  --frozen-suffix .structured   frozen id = <id> + suffix (the frozen 2x4 set names its structured circuits
                                B0_ref102_k1.structured); the exported ids carry no suffix
  --extra-k                     export family circuits that have no frozen counterpart (2x4: the 15 k = 5 circuits;
                                the frozen 2x4 set stops at k = 4).  Their dt is the frozen index's dt[str(twoB)], their
                                reference_int is checked against the frozen manifest of the same (twoB, reference)
  --state-check sparse          28 qubits: no dense statevector.  The native circuit (read back with qn.pytket_to_ir)
                                runs on the study's certified pruned sparse simulator (c2x4.evaluate.
                                certified_state_check, notes/006: certified max|dpsi| and leakage include the pruning
                                bound) against the same exact target; the JSON/QASM round trips are checked by the
                                package's Q1L proof applied to the re-read circuits plus equal counts.  --state-check
                                q1l-only skips the state simulation (then Q1 is not claimed: passes_Q1 = null)
  --gzip                        write <id>.json.gz / <id>.qasm.gz (gzip level 9, mtime 0; sha256 of the UNcompressed
                                text, manifest key sha256_of) -- the on-disk convention of the frozen 2x4 set, which
                                scripts/quantinuum_submit.py reads (load_frozen handles .gz)
  --ids a,b / --max-wall S      chunking: circuits whose manifest already exists are skipped (resume); index.json is
                                written only once every circuit of the family has its manifest
Calibration circuits are copied byte for byte also when gzipped (sha256 of the uncompressed text checked).
"""
from __future__ import annotations

import argparse
import gzip
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

from c2x4.env import git_commit, lattice_study, write_json                      # noqa: E402
from c2x4.evaluate import certified_state_check                                # noqa: E402
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


def write_circuit_file(out, name, text, gz):
    """<name> (plain) or <name>.gz (gzip level 9, mtime 0, as the frozen 2x4 set); returns the file name written."""
    if not gz:
        write_text(os.path.join(out, name), text)
        return name
    path = os.path.join(out, name + ".gz")
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(gzip.compress(text.encode(), compresslevel=9, mtime=0))
    os.replace(tmp, path)
    return name + ".gz"


def read_circuit_text(path):
    if path.endswith(".gz"):
        with gzip.open(path, "rb") as fh:
            return fh.read().decode()
    with open(path) as fh:
        return fh.read()


def summarise(mans, cals, args, hdr, fdir, f_index, out, t0):
    zz = [m["counts"]["n_zz"] for m in mans]
    px = [m["counts"]["n_phasedx"] for m in mans]
    d2 = [m["counts"]["depth_2q"] for m in mans]
    hq = [m["hqc_per_shot"] for m in mans]
    devs = sorted({d for m in mans for d in m["clean_shot_fraction_gate_only"]})
    q1 = [m["levels"]["0"]["passes_Q1"] for m in mans]
    se = [m["levels"]["0"]["state_vs_exact_target"] for m in mans if m["levels"]["0"]["state_vs_exact_target"]]
    index = {
        "produced_by": "2x4_compression_using_ai_v1/scripts/export_quantinuum_family.py",
        "prompt": args.prompt,
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
                    "state_check": sorted({m["state_check"] for m in mans}),
                    "max_abs_dpsi_vs_exact": max((x["max_abs_dpsi"] for x in se), default=None),
                    "max_leakage": max((x["leakage"] for x in se), default=None),
                    "n_Q1_pass": sum(1 for x in q1 if x is True),
                    "all_Q1": (all(q1) if all(x is not None for x in q1) else None),
                    "n_Q1L_pass": sum(1 for m in mans if m["Q1L"]["ok"]),
                    "all_Q1L": all(m["Q1L"]["ok"] for m in mans),
                    "max_Q1L_rounding_state_bound_B": max(m["Q1L"]["rounding_state_bound_B"] for m in mans),
                    "n_without_frozen_counterpart": sum(1 for m in mans if m["frozen_counterpart"]["id"] is None),
                    "clean_shot_fraction_gate_only": {
                        d: {"min": min(m["clean_shot_fraction_gate_only"][d] for m in mans),
                            "mean": float(np.mean([m["clean_shot_fraction_gate_only"][d] for m in mans])),
                            "max": max(m["clean_shot_fraction_gate_only"][d] for m in mans)} for d in devs}},
        "frozen_counterpart": {"dir": os.path.relpath(fdir, ROOT), "id_suffix": args.frozen_suffix,
                               "summary": f_index["summary"]},
        "device_name_compiled_for": args.device, "transpile": None, "levels": [0],
        "selection_rule": SELECTION_RULE, "versions": qn.versions(), "python": sys.executable,
        "git_commit": git_commit(), "runtime_s_this_invocation": time.time() - t0,
        "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "lattice": hdr["lattice"],
    }
    if args.gzip:
        index["sha256_of"] = "the uncompressed text of every .qasm.gz / .json.gz (gzip mtime 0, level 9)"
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--frozen-dir", required=True, help="the package's frozen directory of the same lattice (read only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="H2-2")
    ap.add_argument("--frozen-suffix", default="")
    ap.add_argument("--extra-k", action="store_true")
    ap.add_argument("--state-check", choices=("aer", "sparse", "q1l-only"), default="aer")
    ap.add_argument("--gzip", action="store_true")
    ap.add_argument("--ids", default="all")
    ap.add_argument("--max-wall", type=float, default=1e9)
    ap.add_argument("--prompt", default="owner 2026-10-28 'make the 2x2 compressed family' "
                                        "(2x4_compression_using_ai_v1/notes/011)")
    args = ap.parse_args()
    t0 = time.time()
    fdir = args.frozen_dir if os.path.isabs(args.frozen_dir) else os.path.join(ROOT, args.frozen_dir)
    hdr = family_header(args.family)
    out = args.out if os.path.isabs(args.out) else os.path.join(lattice_study(hdr["lattice"]), args.out)
    if os.path.exists(os.path.join(out, "index.json")):
        raise SystemExit(f"{out} already holds an index.json: an export is written once (choose another --out)")
    os.makedirs(out, exist_ok=True)
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
    sfx = args.frozen_suffix
    frozen_ids = [c[:len(c) - len(sfx)] for c in f_index["circuits"] if c.endswith(sfx)] if sfx else \
        list(f_index["circuits"])
    ids = [cid for cid, _g, _md in fam]
    with_frozen = [cid for cid in ids if cid in set(frozen_ids)]
    if with_frozen != frozen_ids:
        raise SystemExit(f"circuit ids/order differ from the frozen index: {with_frozen} vs {frozen_ids}")
    extra = [cid for cid in ids if cid not in set(frozen_ids)]
    if extra and not args.extra_k:
        raise SystemExit(f"{len(extra)} family circuits have no frozen counterpart ({extra[:3]}...): pass --extra-k")
    want = None if args.ids == "all" else set(args.ids.split(","))
    done_before = 0
    for cid, g, md in fam:
        if os.path.exists(os.path.join(out, cid + ".manifest.json")):
            done_before += 1
            continue
        if want is not None and cid not in want:
            continue
        if time.time() - t0 > args.max_wall:
            print(f"wall limit {args.max_wall} s reached: stopping before {cid}", flush=True)
            break
        t1 = time.time()
        if cid in set(frozen_ids):
            f_man = json.load(open(os.path.join(fdir, cid + sfx + ".manifest.json")))
            for key in ("twoB", "reference", "k", "dt", "n_qubits"):
                if f_man[key] != md[key]:
                    raise SystemExit(f"{cid}: {key} {md[key]!r} differs from the frozen manifest {f_man[key]!r}")
            dt, f_ref_int = float(f_man["dt"]), int(f_man["reference_int"])
            counterpart = {"dir": os.path.relpath(fdir, ROOT), "id": cid + sfx,
                           "n_zz": f_man["counts"]["n_zz"], "n_phasedx": f_man["counts"]["n_phasedx"],
                           "depth_2q": f_man["counts"]["depth_2q"]}
        else:
            dt = float(f_index["dt"][str(md["twoB"])])
            if dt != md["dt"]:
                raise SystemExit(f"{cid}: dt {md['dt']!r} differs from the frozen index dt {dt!r}")
            sib = next(c for c in frozen_ids if c.startswith(f"B{md['twoB'] // 2}_ref") and
                       json.load(open(os.path.join(fdir, c + sfx + ".manifest.json")))["reference"] == md["reference"])
            f_ref_int = int(json.load(open(os.path.join(fdir, sib + sfx + ".manifest.json")))["reference_int"])
            counterpart = {"dir": os.path.relpath(fdir, ROOT), "id": None,
                           "note": f"no frozen counterpart (the frozen set stops at k = {max(f_index.get('built_k', [0]))}); "
                                   f"dt = frozen index dt[{md['twoB']}], reference_int checked against {sib + sfx}"}
        g = [("cp", qs, math.pi) if nm == "cz" else (nm, qs, par) for nm, qs, par in g]
        pc = qn.ir_to_pytket(g, n, measure=True)
        cc = qn.compile_native(pc, args.device, 0)
        cnt = qn.native_counts(cc)
        q1l = qn.local_equivalence_35a(g, cc, n, structured=True)
        ir_c, nn, qmap = qn.pytket_to_ir(cc)
        mm_id = qmap == {q: q for q in range(n)}
        perm_id = all(a == b for a, b in cc.implicit_qubit_permutation().items())
        ref_int = int(ints[md["reference"]])
        if ref_int != f_ref_int:
            raise SystemExit(f"{cid}: reference_int {ref_int} != frozen {f_ref_int}")
        qasm = qn.to_qasm(cc)
        js_text = json.dumps(qn.to_json(cc), sort_keys=True)
        c_json = qn.from_json(json.loads(js_text))
        c_qasm = qn.from_qasm(qasm)
        tgt = coarse_states(groups, basis_vector(M.basis.dim, md["reference"]), dt, md["k"])[md["k"]]
        vs_ir, extra_state = None, {}
        if args.state_check == "aer":
            sv_nat = cq.statevector_aer(ir_c, nn, fusion=False)
            sv_ir = cq.statevector_aer(g, n, fusion=False)
            full = np.zeros(2 ** n, dtype=complex)
            full[ints] = tgt
            vs_exact = qn.global_phase_residual(sv_nat, full)
            vs_exact["leakage"] = float(emb.leakage(sv_nat))
            vs_ir = qn.global_phase_residual(sv_nat, sv_ir)
            vs_ir["leakage"] = float(emb.leakage(sv_nat))
            sv_json = cq.statevector_aer(qn.pytket_to_ir(c_json)[0], n, fusion=False)
            sv_qasm = cq.statevector_aer(qn.pytket_to_ir(c_qasm)[0], n, fusion=False)
            rt = {"json_max_abs_dpsi_raw": float(np.max(np.abs(sv_json - sv_nat))),
                  "json": qn.global_phase_residual(sv_json, sv_nat),
                  "qasm": qn.global_phase_residual(sv_qasm, sv_nat), "qasm_drops_global_phase": True,
                  "qasm_counts_equal": qn.native_counts(c_qasm)["ops"] == cnt["ops"],
                  "json_counts_equal": qn.native_counts(c_json)["ops"] == cnt["ops"]}
            rt_ok = (rt["qasm_counts_equal"] and rt["json_counts_equal"] and rt["json"]["max_abs_dpsi"] < Q1_DPSI_MAX
                     and rt["qasm"]["max_abs_dpsi"] < Q1_DPSI_MAX)
            p = np.abs(sv_nat) ** 2
            top = int(np.argmax(p))
            extra_state = {"p_reference": float(p[ref_int]), "most_probable_int": top, "p_most_probable": float(p[top]),
                           "frozen_state_leakage": float(emb.leakage(sv_nat)),
                           "statevector_engine": "circuits_qiskit.statevector_aer (Aer statevector, double precision, "
                                                 "fusion off)"}
            passes_q1 = bool(vs_exact["max_abs_dpsi"] < Q1_DPSI_MAX and vs_exact["leakage"] < Q1_LEAK_MAX
                             and mm_id and perm_id)
        else:
            vs_exact, passes_q1 = None, None
            pt = np.abs(tgt) ** 2
            extra_state = {"p_reference": float(pt[md["reference"]]),
                           "p_reference_source": "exact coarse state (krylov.coarse_states), basis index r (as the "
                                                 "frozen 2x4 manifests)",
                           "most_probable_basis_index": int(np.argmax(pt)), "p_most_probable": float(pt.max())}
            if args.state_check == "sparse":
                chk = certified_state_check([x for x in ir_c if x[0] != "measure"], n, ints, tgt)
                vs_exact = {"max_abs_dpsi": chk["certified_max_dev"], "leakage": chk["certified_leakage"],
                            "max_abs_dpsi_measured": chk["max_dev_phase_aligned"],
                            "leakage_measured": chk["leakage_direct"], "prune_bound": chk["prune_bound"],
                            "certified": True}
                passes_q1 = bool(vs_exact["max_abs_dpsi"] < Q1_DPSI_MAX and vs_exact["leakage"] < Q1_LEAK_MAX
                                 and mm_id and perm_id)
                extra_state["statevector_engine"] = ("c2x4.evaluate.certified_state_check (skqd.sparse_sim, pruning "
                                                     "tau 1e-15 with its certified bound, notes/006)")
            q1l_json = qn.local_equivalence_35a(g, c_json, n, structured=True)
            q1l_qasm = qn.local_equivalence_35a(g, c_qasm, n, structured=True)
            rt = {"method": "Q1L (local_equivalence_35a, structured) of the IR against each re-read circuit, counts equal",
                  "json_Q1L_ok": bool(q1l_json["ok"]),
                  "json_rounding_state_bound_B": q1l_json["iii_rounding"]["state_bound_B"],
                  "qasm_Q1L_ok": bool(q1l_qasm["ok"]),
                  "qasm_rounding_state_bound_B": q1l_qasm["iii_rounding"]["state_bound_B"],
                  "qasm_drops_global_phase": True,
                  "qasm_counts_equal": qn.native_counts(c_qasm)["ops"] == cnt["ops"],
                  "json_counts_equal": qn.native_counts(c_json)["ops"] == cnt["ops"]}
            rt_ok = rt["json_Q1L_ok"] and rt["qasm_Q1L_ok"] and rt["qasm_counts_equal"] and rt["json_counts_equal"]
        if not (q1l["ok"] and passes_q1 is not False and mm_id and perm_id):
            raise SystemExit(f"{cid}: Q1 {passes_q1} / Q1L {q1l['ok']} / maps {mm_id} {perm_id} -- STOP, nothing "
                             f"exported for this circuit: {json.dumps(vs_exact)} "
                             f"{json.dumps({k: str(v)[:300] for k, v in q1l.items()})}")
        if not rt_ok:
            raise SystemExit(f"{cid}: round trip fails: {json.dumps(rt, default=str)}")
        f_gate = {}
        for key, s_ in dev.items():
            if "eps2" not in s_:
                continue
            ero = 0.5 * (s_["eps_ro_0"] + s_["eps_ro_1"])
            f_gate[s_.get("device_name", key)] = clean_shot_fraction(cnt["n_zz"], cnt["n_phasedx"], n,
                                                                     s_["eps2"], s_["eps1"], ero)
        f_qasm = write_circuit_file(out, cid + ".qasm", qasm, args.gzip)
        f_json = write_circuit_file(out, cid + ".json", js_text, args.gzip)
        man = {
            "id": cid, "kind": f"compressed_2x{lx}_coarse_step_class{md['class']}", "lattice": hdr["lattice"],
            "sector": f"B={md['twoB'] // 2}", "twoB": int(md["twoB"]), "reference": int(md["reference"]),
            "k": int(md["k"]), "repetitions": 1, "dt": dt, "g2": 4.0, "n_qubits": n,
            "family": args.family, "class": md["class"], "family_version": md["version"],
            "family_file": os.path.relpath(family_path(args.family), ROOT),
            "family_file_sha256": sha256_file(family_path(args.family)),
            "content_sha256_ir": md["content_sha256"], "contract": md["contract"], "valid_use": md["valid_use"],
            "global_phase_vs_target_ir": md["global_phase_vs_target"],
            "frozen_counterpart": counterpart,
            "original_ir_counts": qn.ir_counts(g), "ir_n_2q": md["n_2q"], "ir_depth_2q": md["depth_2q"],
            "ir_rewrite": "cz -> cp(pi) (identical matrix diag(1,1,1,-1)) before ir_to_pytket",
            "transpile": None,
            "state_check": args.state_check,
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
            "files": {"qasm": f_qasm, "json": f_json},
            "qasm_sha256": sha256(qasm), "json_sha256": sha256(js_text), "round_trips": rt,
            "reference_bits": [int((ref_int >> q) & 1) for q in range(n)], "reference_int": ref_int,
            **extra_state,
            "versions": qn.versions(), "git_commit": git_commit(),
            "built": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "build_s": time.time() - t1,
        }
        if args.gzip:
            man["sha256_of"] = "the uncompressed text"
        write_text(os.path.join(out, cid + ".manifest.json"), json.dumps(man, indent=1))
        ve = "" if vs_exact is None else f"vs exact {vs_exact['max_abs_dpsi']:.1e} leak {vs_exact['leakage']:.1e} "
        print(f"{cid}: ZZ {cnt['n_zz']} PhasedX {cnt['n_phasedx']} depth2q {cnt['depth_2q']} | {ve}Q1 {passes_q1} "
              f"Q1L {q1l['ok']} B {q1l['iii_rounding']['state_bound_B']:.1e} f(H2-2) "
              f"{f_gate.get('H2-2', float('nan')):.4f} ({time.time() - t1:.1f} s)", flush=True)
    missing = [cid for cid in ids if not os.path.exists(os.path.join(out, cid + ".manifest.json"))]
    if missing:
        print(f"{len(ids) - len(missing)}/{len(ids)} circuits exported ({done_before} before this run); "
              f"index.json not written yet; next: {missing[:3]}", flush=True)
        return
    mans = [json.load(open(os.path.join(out, cid + ".manifest.json"))) for cid in ids]
    # calibration circuits: byte-identical copies of the frozen ones (sha256 of the (uncompressed) text checked)
    cals = []
    for cal in f_index.get("calibration", []):
        cm = json.load(open(os.path.join(fdir, cal + ".manifest.json")))
        for kind in ("json", "qasm"):
            src = os.path.join(fdir, cm["files"][kind])
            if sha256(read_circuit_text(src)) != cm[f"{kind}_sha256"]:
                raise SystemExit(f"{src}: sha256 differs from its frozen manifest")
            shutil.copyfile(src, os.path.join(out, cm["files"][kind]))
            if sha256_file(src) != sha256_file(os.path.join(out, cm["files"][kind])):
                raise SystemExit(f"{src}: copy is not byte-identical")
        cm = dict(cm, copied_from=os.path.relpath(fdir, ROOT), copied_by="2x4_compression_using_ai_v1/scripts/"
                  "export_quantinuum_family.py (byte-identical .json/.qasm; this manifest = the frozen one + this key)")
        write_text(os.path.join(out, cal + ".manifest.json"), json.dumps(cm, indent=1))
        cals.append(cm)
    index = summarise(mans, cals, args, hdr, fdir, f_index, out, t0)
    write_text(os.path.join(out, "index.json"), json.dumps(index, indent=1))
    print(json.dumps(index["summary"], indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
