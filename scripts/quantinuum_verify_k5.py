#!/usr/bin/env python3
"""
Verification of the k = 5 extension of a frozen 2x2 / 2x3 Quantinuum set (owner request 2026-10-28), with the checks
the frozen sets passed (builder Q1 / gate_Q0P_2x3 --stage verify), recomputed from the files on disk:

  * file integrity: sha256 of the QASM / JSON text against the manifest; native gate set; counts = manifest;
    q[k] -> c[k] and the identity permutation;
  * Q1 (physics bar): the native circuit's state against the EXACT coarse state krylov.coarse_states(...)[k]
    (theta = k dt, dt the frozen one), max |dpsi| up to a global phase on the codewords < 1e-10 and leakage < 1e-9
    (campaign33.circuits.exactness); also against the original structured IR (the builder's Q1 reference);
  * Q1L: quantinuum_native.local_equivalence_35a against the prototype transpile (35b reading: skeleton, segments,
    maps), with the recorded rounding bound B (35a bar B < 1e-10);
  * Q3: the QASM read back -> same counts, same state up to a global phase (< 1e-12);
  * counts: ZZ equal to the k = 1..4 circuits of the same reference in the frozen set; PhasedX against their range;
  * dt bit-identical to the frozen manifests; calibration files byte-identical to the frozen folder.

Runs in the isolated venv (pytket):
    ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/quantinuum_verify_k5.py --lattice 2 \
        --circuits data/quantinuum/circuits_2x2_k5 --frozen data/quantinuum/circuits_2x2 --workers 5 --threads 1
Writes <circuits>/verify.json.
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

Q1_DPSI_MAX, Q1_LEAK_MAX, Q3_RT = 1e-10, 1e-9, 1e-12
_G = {}


def sha_text(s):
    return hashlib.sha256(s.encode()).hexdigest()


def sha_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load(p):
    with open(p) as fh:
        return json.load(fh)


def statevector(ir, n):
    """2x2: qiskit.quantum_info (exact, as gate_Q0P_2x3 --stage verify); 2x3: Aer (as the 2x3 builder)."""
    return cq.statevector(ir, n) if n <= 12 else cq.statevector_aer(ir, n, threads=_G["threads"])


def verify_one(cid):
    from qiskit import transpile

    from skqd.campaign33.circuits import exactness
    from skqd.krylov import basis_vector, coarse_states
    from quantinuum_build_circuits import TRANSPILE

    t0 = time.time()
    d, n, emb, M = _G["dir"], _G["n"], _G["emb"], _G["model"]
    man = load(os.path.join(d, cid + ".manifest.json"))
    twoB, r, k, dt = int(man["twoB"]), int(man["reference"]), int(man["k"]), float(man["dt"])
    out = {"id": cid, "twoB": twoB, "reference": r, "k": k, "dt": dt,
           "dt_equals_frozen": dt == _G["frozen_dt"][twoB]}
    with open(os.path.join(d, man["files"]["qasm"])) as fh:
        qasm = fh.read()
    with open(os.path.join(d, man["files"]["json"])) as fh:
        js_text = fh.read()
    out["qasm_sha256_ok"] = sha_text(qasm) == man["qasm_sha256"]
    out["json_sha256_ok"] = sha_text(js_text) == man["json_sha256"]
    c = qn.from_json(json.loads(js_text))
    try:
        qn.check_native(c)
        out["native"] = True
    except qn.NativeCompileError as exc:
        out["native"], out["native_error"] = False, str(exc)
    out["counts"] = qn.native_counts(c)
    out["counts_match_manifest"] = out["counts"] == {kk: v for kk, v in man["counts"].items() if kk != "rzz_before"}
    ir, nn, qmap = qn.pytket_to_ir(c)
    out["measure_map_identity"] = qmap == {q: q for q in range(n)}
    out["implicit_permutation_identity"] = all(a == b for a, b in c.implicit_qubit_permutation().items())
    # the gate list of the structured IR at the frozen dt
    gates = _G["factory"].coarse_step(r, k, dt)
    sv = statevector(ir, nn)
    # Q1 against the exact coarse state (krylov.coarse_states at theta = k dt)
    psi_ex = coarse_states(_G["groups"], basis_vector(M.basis.dim, r), dt, k)[k]
    ex = exactness(sv, psi_ex, emb, out["measure_map_identity"] and out["implicit_permutation_identity"])
    out["Q1_vs_coarse_states"] = ex
    out["Q1_pass"] = bool(ex["max_abs_dpsi_up_to_phase"] < Q1_DPSI_MAX and ex["leakage"] < Q1_LEAK_MAX
                          and ex["measurement_consistent"])
    ref = statevector(gates, n)
    out["state_vs_original_ir"] = qn.global_phase_residual(sv, ref)
    out["original_ir_vs_coarse_states"] = exactness(ref, psi_ex, emb)
    # Q1L against the prototype transpile (the source the native circuit was compiled from)
    tq = transpile(cq.ir_to_qiskit(gates, n, measure=False), **TRANSPILE)
    ir_t = qn.qiskit_to_ir(tq)
    out["rzz_before_compilation"] = int(tq.count_ops().get("rzz", 0))
    q1l = qn.local_equivalence_35a(ir_t, c, n)
    out["Q1L"] = q1l
    out["Q1L_pass_35b"] = bool(q1l["i_skeleton"]["ok"] and q1l["ii_segments_vs_readback"]["ok"]
                               and q1l["measure_map_identity"] and q1l["implicit_permutation_identity"])
    out["Q1L_rounding_B"] = q1l["rounding"]["state_bound_B"]
    out["Q1L_B_below_1e-10"] = bool(q1l["rounding"]["state_bound_B"] is not None
                                    and q1l["rounding"]["state_bound_B"] < Q1_DPSI_MAX)
    # Q3: the QASM read back
    c_q = qn.from_qasm(qasm)
    out["qasm_counts_equal"] = qn.native_counts(c_q)["ops"] == out["counts"]["ops"]
    out["qasm_vs_json"] = qn.global_phase_residual(statevector(qn.pytket_to_ir(c_q)[0], n), sv)
    out["Q3_pass"] = bool(out["qasm_counts_equal"] and out["qasm_vs_json"]["max_abs_dpsi"] < Q3_RT)
    # counts against the frozen k = 1..4 circuits of the same reference
    base = cid.rsplit("_k", 1)[0]
    fr = {kk: _G["frozen_counts"][f"{base}_k{kk}"] for kk in (1, 2, 3, 4)}
    zz = {kk: v["n_zz"] for kk, v in fr.items()}
    px = {kk: v["n_phasedx"] for kk, v in fr.items()}
    out["frozen_k1_4"] = {"n_zz": zz, "n_phasedx": px}
    out["zz_equal_to_frozen_k1_4"] = all(v == out["counts"]["n_zz"] for v in zz.values())
    out["phasedx_equal_to_frozen_k1_4"] = all(v == out["counts"]["n_phasedx"] for v in px.values())
    out["phasedx_within_frozen_k1_4_range"] = min(px.values()) <= out["counts"]["n_phasedx"] <= max(px.values())
    out["p_reference"] = float(np.abs(sv[int(man["reference_int"])]) ** 2)
    out["p_reference_matches_manifest"] = abs(out["p_reference"] - man["p_reference"]) < 1e-12
    out["pass"] = bool(out["dt_equals_frozen"] and out["qasm_sha256_ok"] and out["json_sha256_ok"] and out["native"]
                       and out["counts_match_manifest"] and out["Q1_pass"] and out["Q1L_pass_35b"]
                       and out["Q3_pass"] and out["zz_equal_to_frozen_k1_4"])
    out["seconds"] = time.time() - t0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lattice", type=int, choices=(2, 3), required=True)
    ap.add_argument("--circuits", required=True, help="the k = 5 folder")
    ap.add_argument("--frozen", required=True, help="the frozen k = 1..4 folder (read only)")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--threads", type=int, default=1)
    args = ap.parse_args()
    t0 = time.time()
    from gate_S2D import G2
    from quantinuum_build_circuits import frozen_dts
    from skqd.circuits_ir import CircuitFactory
    from skqd.exact import Model, mass_default
    from skqd.krylov import term_groups
    from skqd.reference_sim import CodewordEmbedding

    d, fz = os.path.abspath(args.circuits), os.path.abspath(args.frozen)
    M = Model(args.lattice)
    emb = CodewordEmbedding(M)
    fidx, idx = load(os.path.join(fz, "index.json")), load(os.path.join(d, "index.json"))
    _G.update({"dir": d, "n": int(emb.n), "emb": emb, "model": M, "threads": args.threads,
               "factory": CircuitFactory(M, G2), "groups": term_groups(M.terms, G2, mass_default(G2)),
               "frozen_dt": frozen_dts(fz),
               "frozen_counts": {c: load(os.path.join(fz, c + ".manifest.json"))["counts"] for c in fidx["circuits"]}})
    import multiprocessing as mp

    per = {}
    with mp.get_context("fork").Pool(args.workers) as pool:
        for rec in pool.imap_unordered(verify_one, idx["circuits"]):
            per[rec["id"]] = rec
            print(f"  {rec['id']}: ZZ {rec['counts']['n_zz']} PhasedX {rec['counts']['n_phasedx']} "
                  f"dpsi {rec['Q1_vs_coarse_states']['max_abs_dpsi_up_to_phase']:.2e} "
                  f"leak {rec['Q1_vs_coarse_states']['leakage']:.2e} Q1L {rec['Q1L_pass_35b']} "
                  f"(B {rec['Q1L_rounding_B']:.2e}) pass {rec['pass']} [{time.time() - t0:.0f} s]", flush=True)
    per = {c: per[c] for c in idx["circuits"]}
    cal = {}
    for cid in idx["calibration"]:
        m = load(os.path.join(fz, cid + ".manifest.json"))
        names = [cid + ".manifest.json", m["files"]["qasm"], m["files"]["json"]]
        cal[cid] = {nm: sha_file(os.path.join(d, nm)) == sha_file(os.path.join(fz, nm)) for nm in names}
        cal[cid]["byte_identical"] = all(cal[cid].values())
    expected_ids = sorted(c.rsplit("_k", 1)[0] + "_k5" for c in fidx["circuits"] if c.endswith("_k1"))
    rec = {
        "produced_by": "scripts/quantinuum_verify_k5.py", "lattice": f"2x{args.lattice}",
        "circuits_dir": os.path.relpath(d, ROOT), "frozen_dir": os.path.relpath(fz, ROOT),
        "index_sha256": sha_file(os.path.join(d, "index.json")),
        "frozen_index_sha256": sha_file(os.path.join(fz, "index.json")),
        "ids_match_frozen_references": sorted(idx["circuits"]) == expected_ids,
        "per_circuit": per, "calibration": cal,
        "bars": {"Q1_max_abs_dpsi": Q1_DPSI_MAX, "Q1_leakage": Q1_LEAK_MAX, "Q3": Q3_RT,
                 "Q1L": "prompts/35b R2 reading (skeleton, segments, maps); B < 1e-10 recorded (35a)"},
        "summary": {"n": len(per), "all_pass": all(v["pass"] for v in per.values()),
                    "max_Q1_dpsi": max(v["Q1_vs_coarse_states"]["max_abs_dpsi_up_to_phase"] for v in per.values()),
                    "max_Q1_leakage": max(v["Q1_vs_coarse_states"]["leakage"] for v in per.values()),
                    "max_Q1L_B": max(v["Q1L_rounding_B"] for v in per.values()),
                    "all_Q1L_B_below_1e-10": all(v["Q1L_B_below_1e-10"] for v in per.values()),
                    "all_zz_equal_frozen": all(v["zz_equal_to_frozen_k1_4"] for v in per.values()),
                    "n_phasedx_equal_frozen_all_k": sum(v["phasedx_equal_to_frozen_k1_4"] for v in per.values()),
                    "n_phasedx_within_frozen_range": sum(v["phasedx_within_frozen_k1_4_range"] for v in per.values()),
                    "calibration_byte_identical": all(v["byte_identical"] for v in cal.values())},
        "statevector_engine": ("circuits_qiskit.statevector (qiskit.quantum_info, exact)" if args.lattice == 2 else
                               f"circuits_qiskit.statevector_aer ({args.threads} thread(s), fusion on)"),
        "versions": qn.versions(), "python": sys.executable, "runtime_s": time.time() - t0,
        "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    rec["status"] = "PASS" if (rec["summary"]["all_pass"] and rec["summary"]["calibration_byte_identical"]
                               and rec["ids_match_frozen_references"]) else "FAIL"
    with open(os.path.join(d, "verify.json"), "w") as fh:
        json.dump(rec, fh, indent=1)
    print(f"{rec['status']}: {json.dumps(rec['summary'])} -> {os.path.join(d, 'verify.json')}", flush=True)
    return 0 if rec["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
