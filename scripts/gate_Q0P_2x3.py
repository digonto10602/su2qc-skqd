#!/usr/bin/env python3
"""
Gate Q0P_2x3 (prompts/26 Stage A): the signed 2x3 circuits compiled to the Quantinuum native gate set
{Rz, PhasedX, ZZPhase}, verified exactly, costed and packaged.  0 HQC; no account; no network.

Stages (each writes a fragment under data/quantinuum/q0p_stages/ and re-assembles
validation/Q0P_2x3.json + reports/Q0P_2x3.md from ALL fragments present):

  --stage verify     (isolated venv: needs pytket)  Q1-Q3 recomputed from the FROZEN files, independent
                     of the build's own numbers; Q7 (pytest in both envs, check_package, the pins).
  --stage predict    (any env; after verify)  Q4-Q6: device table, HQC formula against the manifests,
                     the pilot / Stage-E / campaign plans (rule D3' at 0.7 f on the verify stage's
                     frozen-circuit distributions), the dry-run statistics (A6).
  --stage prereg-md  renders reports/Q0P_2x3_prereg.md from the predict fragment.
  --stage assemble-emulator   Stage E (vendor emulator) -- records "not run" until an emulator
                     session exists (prompts/26: needs a Nexus login and the owner's budget).

Status PASS iff Q1-Q7 (prompts/26).  `what_pass_means` is quoted verbatim from the prompt.

Usage:
  ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/gate_Q0P_2x3.py --stage verify
  python scripts/gate_Q0P_2x3.py --stage predict
  python scripts/gate_Q0P_2x3.py --stage prereg-md
"""
import argparse
import glob
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

from skqd import quantinuum_native as qn  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402

GATE = "Q0P_2x3"
TITLE = ("signed 2x3 circuits compiled to the Quantinuum native gate set, verified exactly, costed and "
         "packaged (Stage A; Stage E/P not run)")
WHAT_PASS_MEANS = ("compiled to the Quantinuum native gate set, verified exactly, costed and packaged; "
                   "PASS is NOT a statement that H2-2 or Helios-1 delivers the signed clean-shot fraction "
                   "— that is Stage E's emulator measurement, and after it Stage P's device pilot")
CIRC = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
STAGES = os.path.join(ROOT, "data", "quantinuum", "q0p_stages")
DEVICES = os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")
STACK = os.path.join(ROOT, "data", "quantinuum", "stack_check_20261002.json")
DRYRUN = os.path.join(ROOT, "data", "hardware", "Q0P_2x3_dryrun")
PILOTS = os.path.join(ROOT, "data", "hardware", "Q0P_2x3_dryrun_pilots")   # timing pilots (scratch runs, copied)
A6_PLANNED_SHOTS, A6_BUDGET_S = 200, 25 * 60.0                            # prompts/26 A6
EMU_DIR = os.path.join(ROOT, "data", "hardware", "Q0P_2x3_H2-2E")
CODING_PY = "/home/digimonk/anaconda3/envs/coding/bin/python"
VENV_PY = os.path.join(os.path.expanduser("~"), ".local", "share", "su2qc-quantinuum", "venv", "bin", "python")
G2 = 4.0
Q1_DPSI, Q1_LEAK, Q3_RT, Q45_TOL = 1e-10, 1e-9, 1e-12, 1e-12
RZZ_EXPECTED = 2158                 # data/S2D_2x3_device_requirements.json counts.coarse_step.rzz
N_CIRCUITS = 44
PILOT_SHOTS = 1000                  # Stage P: B0 and B1 k = 1 at 1000 shots each
E_K1_SHOTS, E_K4_SHOTS = 1000, 200  # Stage E2
CAMPAIGN_F = (0.05, 0.10, 0.15)
D3_MARGIN, D3_FLOOR, D3_ROUND = 0.7, 267, 100     # rule D3' constants (scripts/h0_support_plan.py)
D3_SANE_SHOTS = 10 ** 9            # display flag only: a plan above 1e9 shots is reported as not a finite campaign
MAX_COST_MARGIN = 1.10
GO_RULE = ("GO to Stage P iff the 95 % lower bound of pooled f_E >= 0.05 and the point estimate >= 0.10 "
           "(the signed bars applied to the emulator)")
PINS_EXPECTED = {"python": "3.12.14", "qiskit": "2.5.2", "qiskit-aer": "0.17.2",
                 "qiskit-ibm-runtime": "0.49.0", "numpy": "2.5.2", "scipy": "1.18.0"}

_G = {}


def sha256_text(t):
    return hashlib.sha256(t.encode()).hexdigest()


def load_json(p):
    with open(p) as fh:
        return json.load(fh)


def save_fragment(name, d):
    os.makedirs(STAGES, exist_ok=True)
    d = dict(d)
    d["stage"] = name
    d["created"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    with open(os.path.join(STAGES, name + ".json"), "w") as fh:
        json.dump(d, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def fragment(name):
    p = os.path.join(STAGES, name + ".json")
    return load_json(p) if os.path.exists(p) else None


def manifests():
    idx = load_json(os.path.join(CIRC, "index.json"))
    mans = {c: load_json(os.path.join(CIRC, c + ".manifest.json")) for c in idx["circuits"]}
    cals = {c: load_json(os.path.join(CIRC, c + ".manifest.json")) for c in idx.get("calibration", [])}
    return idx, mans, cals


def pilot_ids(idx):
    return [next(c for c in idx["circuits"] if c.startswith(s + "_") and c.endswith("_k1")) for s in ("B0", "B1")]


# =========================================================================== verify (venv)
def verify_one(cid):
    """Q1-Q3 for one frozen circuit, recomputed from the files on disk."""
    from qiskit import transpile

    from skqd import circuits_qiskit as cq

    man = _G["mans"][cid]
    twoB, r, k, gates = _G["by_id"][cid]
    n = _G["n"]
    emb = _G["emb"]
    th = _G["threads"]
    out = {"id": cid}
    qasm = open(os.path.join(CIRC, man["files"]["qasm"])).read()
    js_text = open(os.path.join(CIRC, man["files"]["json"])).read()
    out["qasm_sha256_ok"] = sha256_text(qasm) == man["qasm_sha256"]
    out["json_sha256_ok"] = sha256_text(js_text) == man["json_sha256"]
    tq = transpile(cq.ir_to_qiskit(gates, n, measure=False), basis_gates=["rz", "rx", "ry", "rzz"],
                   coupling_map=None, optimization_level=3, seed_transpiler=7)
    out["rzz_before_compilation"] = int(tq.count_ops().get("rzz", 0))
    ref = cq.statevector_aer(gates, n, threads=th)
    c = qn.from_json(json.loads(js_text))
    try:
        qn.check_native(c)
        out["native"] = True
    except qn.NativeCompileError as exc:
        out["native"] = False
        out["native_error"] = str(exc)
    out["counts"] = qn.native_counts(c)
    out["counts_match_manifest"] = out["counts"] == man["counts"]
    ir, nn, qmap = qn.pytket_to_ir(c)
    out["measure_map_identity"] = qmap == {q: q for q in range(n)}
    out["implicit_permutation_identity"] = all(a == b for a, b in c.implicit_qubit_permutation().items())
    sv = cq.statevector_aer(ir, nn, threads=th)
    out["state_vs_original_ir"] = qn.global_phase_residual(sv, ref)
    out["leakage"] = float(emb.leakage(sv))
    out["original_ir_leakage"] = float(emb.leakage(ref))
    # JSON round trip: file -> circuit -> to_json -> from_json, and the QASM file
    c2 = qn.from_json(json.loads(json.dumps(qn.to_json(c))))
    sv2 = cq.statevector_aer(qn.pytket_to_ir(c2)[0], n, threads=th)
    out["json_round_trip_max_abs_dpsi_raw"] = float(np.max(np.abs(sv2 - sv)))
    cq_ = qn.from_qasm(qasm)
    svq = cq.statevector_aer(qn.pytket_to_ir(cq_)[0], n, threads=th)
    out["qasm_vs_json"] = qn.global_phase_residual(svq, sv)
    out["qasm_counts_equal"] = qn.native_counts(cq_)["ops"] == out["counts"]["ops"]
    p = np.abs(sv) ** 2
    out["p_reference"] = float(p[int(man["reference_int"])])
    # the ideal sector distribution from the frozen circuit's statevector (the primary route of
    # scripts/h0_support_plan.ideal_probabilities); input of rule D3' in --stage predict
    sec_idx = _G["sector_indices"][int(twoB)]
    out["p_sector"] = [float(x) for x in p[emb.ints[sec_idx]]]
    out["sector_mass"] = float(np.sum(out["p_sector"]))
    out["p_reference_matches_manifest"] = abs(out["p_reference"] - man["p_reference"]) < 1e-12
    return out


def endianness_test():
    """3-qubit circuit with X on qubit 0 -> our key 1, through pytket_to_ir and a BackendResult."""
    from pytket import Bit, Circuit
    from pytket.backends.backendresult import BackendResult
    from pytket.utils.outcomearray import OutcomeArray

    from skqd import circuits_qiskit as cq
    from skqd.reference_sim import bits_to_int, int_to_bits, qiskit_key_to_bits

    c = Circuit(3, 3)
    c.X(0)
    for q in range(3):
        c.Measure(q, q)
    cc = qn.compile_native(c, "H2-2", 0)
    ir, n, qmap = qn.pytket_to_ir(cc)
    key_sv = bits_to_int(int_to_bits(int(np.argmax(np.abs(cq.statevector(ir, n)))), 3))
    res = BackendResult(shots=OutcomeArray.from_readouts([[0, 1, 0]] * 3),
                        c_bits=[Bit("c", 2), Bit("c", 0), Bit("c", 1)])
    cnt = qn.counts_from_pytket_readouts(dict(res.get_counts()), [("c", 0), ("c", 1), ("c", 2)])
    key_br = bits_to_int(next(iter(cnt)))
    key_qiskit = bits_to_int(qiskit_key_to_bits("001"))
    return {"key_statevector": key_sv, "key_backendresult": key_br, "key_qiskit_reader": key_qiskit,
            "measure_map": {str(k): v for k, v in qmap.items()},
            "convention": ("pytket BackendResult.get_counts(): 'Toggle between ILO (increasing lexicographic "
                           "order of bit ids) and DLO (decreasing lexicographic order) for column ordering "
                           "if cbits is None. Defaults to BasisOrder.ilo.' (pytket 2.18.4 docstring); tuple "
                           "index k = c[k] = qubit k"),
            "ok": key_sv == key_br == key_qiskit == 1}


def run_tests():
    t0 = time.time()
    out = {}
    for tag, py in (("coding", CODING_PY), ("venv", VENV_PY)):
        r = subprocess.run([py, "-m", "pytest", "-q", "tests"], cwd=ROOT, capture_output=True, text=True)
        out[f"pytest_{tag}"] = {"python": py, "returncode": r.returncode,
                                "summary": (r.stdout.strip().splitlines() or [""])[-1]}
    c = subprocess.run([CODING_PY, os.path.join("scripts", "check_package.py")], cwd=ROOT,
                       capture_output=True, text=True)
    out["check_package"] = {"python": CODING_PY, "returncode": c.returncode,
                            "tail": "\n".join(c.stdout.strip().splitlines()[-3:])}
    code = ("import sys,json,qiskit,qiskit_aer,qiskit_ibm_runtime,numpy,scipy;print(json.dumps({'python':"
            "sys.version.split()[0],'qiskit':qiskit.__version__,'qiskit-aer':qiskit_aer.__version__,"
            "'qiskit-ibm-runtime':qiskit_ibm_runtime.__version__,'numpy':numpy.__version__,'scipy':scipy.__version__}))")
    pr = subprocess.run([CODING_PY, "-c", code], capture_output=True, text=True)
    out["pins_now"] = json.loads(pr.stdout.strip().splitlines()[-1])
    out["seconds"] = time.time() - t0
    return out


def stage_verify(args):
    import multiprocessing as mp

    from gate_S2D import circuit_set
    from quantinuum_build_circuits import circuit_id
    from skqd.reference_sim import CodewordEmbedding

    t0 = time.time()
    if args.checks_only:
        frag = fragment("verify")
        if not frag:
            raise SystemExit("--checks-only needs an existing verify fragment")
        frag["endianness"] = endianness_test()
        frag["checks"] = run_tests()
        frag["checks"]["rerun_note"] = "Q7 checks re-run with --checks-only on the final code; Q1-Q3 from the verify run"
        save_fragment("verify", frag)
        return assemble()
    idx, mans, cals = manifests()
    M, _F, cset = circuit_set(3)
    emb = CodewordEmbedding(M)
    _G.update({"mans": mans, "by_id": {circuit_id(*c[:3]): c for c in cset}, "n": int(emb.n),
               "emb": emb, "threads": args.threads,
               "sector_indices": {tb: np.asarray(M.reference(G2, tb).indices, dtype=int) for tb in (0, 2)}})
    if sorted(_G["by_id"]) != sorted(idx["circuits"]):
        raise SystemExit("the frozen index does not list the 44 circuits of gate_S2D.circuit_set(3)")
    print(f"verify: {len(idx['circuits'])} circuits ({time.time() - t0:.0f} s)", flush=True)
    per = {}
    with mp.get_context("fork").Pool(args.workers) as pool:
        for rec in pool.imap_unordered(verify_one, idx["circuits"]):
            per[rec["id"]] = rec
            print(f"  {rec['id']}: dpsi {rec['state_vs_original_ir']['max_abs_dpsi']:.1e}, leak "
                  f"{rec['leakage']:.1e}, qasm {rec['qasm_vs_json']['max_abs_dpsi']:.1e} "
                  f"[{time.time() - t0:.0f} s]", flush=True)
    cal = {}
    for cid, m in cals.items():
        txt = open(os.path.join(CIRC, m["files"]["qasm"])).read()
        cal[cid] = {"qasm_sha256_ok": sha256_text(txt) == m["qasm_sha256"],
                    "expected_int": m["expected_int"], "statevector_argmax_int": m["statevector_argmax_int"],
                    "ok": m["expected_int"] == m["statevector_argmax_int"] and m["measure_map_identity"]}
    frag = {"per_circuit": per, "calibration": cal, "endianness": endianness_test(),
            "index_sha256": sha256_text(open(os.path.join(CIRC, "index.json")).read()),
            "versions": qn.versions(), "python": sys.executable, "runtime_s": time.time() - t0,
            "statevector_engine": "circuits_qiskit.statevector_aer (Aer statevector, double, fusion on)"}
    frag["checks"] = {"skipped": True} if args.skip_tests else run_tests()
    save_fragment("verify", frag)
    return assemble()


# =========================================================================== predict
def sector_p(model, mans, V, crosscheck_ids):
    """{id: {"p", "sector_indices"}} from the verify stage's frozen-circuit statevectors, and the
    cross-check of the full vectors against skqd.krylov.ideal_sector_distribution (the group-evolution
    route) on `crosscheck_ids` (~20 s per circuit at 2x3, so not on all 44)."""
    from skqd.krylov import ideal_sector_distribution

    out = {}
    for cid, m in mans.items():
        idx = [int(b) for b in model.reference(G2, int(m["twoB"])).indices]
        p = np.asarray(V["per_circuit"][cid]["p_sector"], float)
        out[cid] = {"p": p / p.sum(), "sector_indices": idx, "mass": float(p.sum())}
    xc = {}
    for cid in crosscheck_ids:
        m = mans[cid]
        d = ideal_sector_distribution(model, G2, int(m["twoB"]), int(m["reference"]), int(m["k"]), float(m["dt"]), 1)
        if d["sector_indices"] != out[cid]["sector_indices"]:
            raise SystemExit(f"{cid}: sector orderings differ")
        xc[cid] = float(np.max(np.abs(np.asarray(d["p"]) - out[cid]["p"])))
    return out, xc


def d3_plan(mans, dists, f, hqc_by_id):
    """Rule D3' (scripts/h0_support_plan.n4_of_sector) at a uniform f, per sector."""
    from h0_support_plan import n4_of_sector

    from skqd.skqd import READOUT_FACTOR, poisson_lambda_star

    lam = poisson_lambda_star()
    shots, n4s, unreach = {}, {}, {}
    for sec in ("B=0", "B=1"):
        ids = sorted(c for c, m in mans.items() if m["sector"] == sec)
        k4 = [c for c in ids if int(mans[c]["k"]) == 4]
        P = {c: dists[c]["p"] for c in ids}
        F = {c: float(f) for c in ids}
        n4 = n4_of_sector(P, F, ids, k4, D3_FLOOR, lam, margin=D3_MARGIN, readout_factor=READOUT_FACTOR,
                          round_to=D3_ROUND)
        n4s[sec] = n4
        tot = sum(P[c] for c in k4)
        unreach[sec] = {"states": int(len(tot)), "states_with_sum_k4_p_below_1e-6": int((tot < 1e-6).sum()),
                        "min_sum_k4_p": float(tot.min())}
        for c in ids:
            shots[c] = n4 if c in k4 else D3_FLOOR
    plan = cost_of_plan(shots, mans, hqc_by_id)
    plan.update({"N4": n4s, "f": f, "margin": D3_MARGIN, "floor": D3_FLOOR, "round_to": D3_ROUND,
                 "lambda_star": lam, "readout_factor": READOUT_FACTOR, "k4_reachability": unreach,
                 "rule": "D3' (scripts/h0_support_plan.n4_of_sector): every sector state >= lambda* expected clean "
                         "counts from the circuits at 0.82 x 0.7 x f",
                 "finite_campaign": bool(plan["shots_total"] <= D3_SANE_SHOTS)})
    return plan


def d3type_plan(mans, f, hqc_by_id):
    """The D3-type union-reading rule of gate S1 (data/S2D_recall_at_f.json, the planner prototype's
    shot rule) at the margin-reduced f: N_sector = ceil100(N_sector(f = 0.1) x 0.1 / (0.7 f)), spread
    evenly over the sector's circuits."""
    r = load_json(os.path.join(ROOT, "data", "S2D_recall_at_f.json"))["results"]
    shots, nsec = {}, {}
    for sec in ("B=0", "B=1"):
        base = int(r[f"{sec}|f=0.1"]["shot_rule_union_reading_N_sector"])
        n = int(math.ceil(base * 0.1 / (D3_MARGIN * f) / 100.0) * 100)
        ids = sorted(c for c, m in mans.items() if m["sector"] == sec)
        per = int(math.ceil(n / len(ids)))
        nsec[sec] = {"N_sector_rule": n, "N_sector_at_f_0.1": base, "per_circuit": per}
        for c in ids:
            shots[c] = per
    plan = cost_of_plan(shots, mans, hqc_by_id)
    plan.update({"f": f, "margin": D3_MARGIN, "sectors": nsec,
                 "rule": ("D3-type union reading (data/S2D_recall_at_f.json results.<sector>|f=0.1."
                          "shot_rule_union_reading_N_sector, gate S1's recall criterion) x 0.1 / (0.7 f), rounded "
                          "up to 100, spread evenly over the sector's circuits")})
    return plan


def cost_of_plan(shots, mans, hqc_by_id):
    """HQC of a per-circuit shot plan: every circuit in jobs of at most 10,000 shots, each job
    5 + C (N_1q + 10 N_2q + 5 N_m) / 5000."""
    jobs, hqc = 0, 0.0
    per = {}
    for c, s in shots.items():
        nj = -(-int(s) // qn.MAX_SHOTS_PER_JOB)          # ceil, exact for any integer size
        h = qn.HQC_JOB_BASE * nj + float(s) * qn.hqc_per_shot(mans[c]["counts"])   # = sum of hqc_job over the jobs
        per[c] = {"shots": int(s), "jobs": nj, "hqc": h}
        jobs += nj
        hqc += h
    by_sec = {}
    for c, v in per.items():
        b = by_sec.setdefault(mans[c]["sector"], {"shots": 0, "jobs": 0, "hqc": 0.0})
        b["shots"] += v["shots"]
        b["jobs"] += v["jobs"]
        b["hqc"] += v["hqc"]
    return {"shots_by_circuit": {c: v["shots"] for c, v in per.items()}, "per_circuit": per,
            "by_sector": by_sec, "shots_total": int(sum(shots.values())), "jobs": jobs, "hqc_total": hqc}


def analyse_dryrun(model, mans, cals):
    """A6: the dry-run counts through the project's clean statistics and the reference-string test."""
    from gate_H0P import clean_statistics
    from gate_S2D import garbage_acceptance_from_E2

    from skqd.device_req import clean_shot_fraction
    from skqd.reference_sim import bits_to_int, qiskit_key_to_bits
    from skqd.skqd import pooled_reference_string_test, reference_string_test
    from quantinuum_submit import A6_NOISE

    sess_p = os.path.join(DRYRUN, "session.json")
    if not os.path.exists(sess_p):
        return {"present": False}
    sess = load_json(sess_p)
    files = sorted(glob.glob(os.path.join(DRYRUN, "counts", "*.json")))
    recs = {os.path.basename(f)[:-5]: load_json(f) for f in files}
    a, a_src = garbage_acceptance_from_E2("2x3")
    records = []
    for cid, rec in recs.items():
        if rec.get("kind") == "calibration":
            continue
        counts = {qiskit_key_to_bits(k): int(v) for k, v in rec["counts"].items()}
        records.append((rec, counts))
    cs = clean_statistics(records, model, G2, {"B=0": a, "B=1": a}) if records else None
    e = A6_NOISE
    p10, p01 = e["readout_p1_given_0"], e["readout_p0_given_1"]
    rows68, rows_ids, direct, preds = [], [], {}, {}
    dims = {}
    for rec, counts in records:
        cid = rec["id"]
        m = mans[cid]
        dim = cs["per_circuit"][cid]["dim"]
        dims[cid] = dim
        n_ref = int(sum(v for b, v in counts.items() if bits_to_int(b) == int(m["reference_int"])))
        shots = int(sum(counts.values()))
        row = (n_ref, shots, float(m["p_reference"]), a, dim)
        rows68.append(row)
        rows_ids.append(cid)
        direct[cid] = {"f_estimate_readout_factor_1": reference_string_test(*row, readout_factor=1.0, conf=0.95),
                       "n_reference": n_ref, "shots": shots, "p_reference_statevector": m["p_reference"],
                       "p_reference_ideal_distribution": cs["per_circuit"][cid]["p_reference"]}
        c = m["counts"]
        ones = sum(m["reference_bits"])
        ro = (1 - p10) ** (c["n_qubits"] - ones) * (1 - p01) ** ones
        preds[cid] = {
            "f_gate_only_model": clean_shot_fraction(c["n_zz"], c["n_phasedx"], c["n_meas"], e["depolarizing_2q_rzz"],
                                                     e["depolarizing_1q_rx_ry"], 0.5 * (p10 + p01)),
            "aer_channel_no_error_probability": ((1 - 15 / 16 * e["depolarizing_2q_rzz"]) ** c["n_zz"]
                                                 * (1 - 3 / 4 * e["depolarizing_1q_rx_ry"]) ** c["n_phasedx"] * ro),
            "expected_clean_shots_model": shots * clean_shot_fraction(
                c["n_zz"], c["n_phasedx"], c["n_meas"], e["depolarizing_2q_rzz"], e["depolarizing_1q_rx_ry"],
                0.5 * (p10 + p01))}
    pooled95 = pooled_reference_string_test(rows68, readout_factor=1.0, conf=0.95) if rows68 else None
    pooled68 = pooled_reference_string_test(rows68, readout_factor=1.0, conf=0.6827) if rows68 else None
    shots_tot = sum(r[1] for r in rows68)
    w_model = sum(preds[c]["f_gate_only_model"] * r[1] for c, r in zip(rows_ids, rows68)) / shots_tot if rows68 else None
    w_aer = sum(preds[c]["aer_channel_no_error_probability"] * r[1] for c, r in zip(rows_ids, rows68)) / shots_tot if rows68 else None
    lo, hi = (pooled95["f_clean_68"] if pooled95 else (None, None))     # key name is the module's; conf = 0.95
    cal = {}
    for cid, rec in recs.items():
        if rec.get("kind") != "calibration":
            continue
        counts = {bits_to_int(qiskit_key_to_bits(k)): int(v) for k, v in rec["counts"].items()}
        exp = int(cals[cid]["expected_int"])
        cal[cid] = {"shots": int(sum(counts.values())), "expected_int": exp,
                    "fraction_expected": counts.get(exp, 0) / max(1, sum(counts.values()))}
    # the 30-minute rule: the two-point timing pilot (prompts/26 A6 asked for 200 shots per circuit)
    pilots = {}
    for tag in ("shots12", "shots40"):
        pp = os.path.join(PILOTS, tag, "session.json")
        if os.path.exists(pp):
            ps = load_json(pp)
            pilots[tag] = {"shots_per_circuit": int(ps["jobs"][0]["n_shots"]), "n_jobs": len(ps["jobs"]),
                           "sampling_wall_s": float(ps["sampling_wall_s"]),
                           "session": os.path.relpath(pp, ROOT)}
    timing = {"pilots": pilots, "planned_shots_per_circuit": A6_PLANNED_SHOTS,
              "budget_s": A6_BUDGET_S, "shots_used_per_k1_circuit": sorted({r[1] for r in rows68})}
    if len(pilots) == 2:
        a, b = pilots["shots12"], pilots["shots40"]
        slope = (b["sampling_wall_s"] - a["sampling_wall_s"]) / (b["shots_per_circuit"] - a["shots_per_circuit"])
        icpt = a["sampling_wall_s"] - slope * a["shots_per_circuit"]
        timing.update({"s_per_shot_of_the_4_circuit_call": slope, "intercept_s": icpt,
                       "estimate_at_planned_shots_s": icpt + slope * A6_PLANNED_SHOTS,
                       "max_shots_in_budget": int((A6_BUDGET_S - icpt) / slope),
                       })
        s3 = load_json(os.path.join(ROOT, "validation", "S3.json"))["data"]["cost"]
        gpu = float(s3["seconds_per_shot_best_ladder"])
        timing["gpu_s_per_shot_S3_A100"] = gpu
        timing["gpu_estimate_full_run_s_ESTIMATE"] = gpu * 2 * A6_PLANNED_SHOTS
        timing["full_run_needs"] = (
            "200 shots per circuit is ~{:.0f} min on this laptop; on the Perlmutter A100 the S3 calibration "
            "measured {:.4f} s per noisy 20-qubit 2x3 shot (validation/S3.json data.cost.seconds_per_shot_best_ladder), "
            "i.e. ~{:.0f} s for the 2 x 200 shots (ESTIMATE: S3's device model, not this noise model); not needed "
            "for Stage A, and Stage E's vendor emulator replaces it").format(
                (icpt + slope * A6_PLANNED_SHOTS) / 60.0, gpu, gpu * 2 * A6_PLANNED_SHOTS)
    phase_p = os.path.join(ROOT, "data", "quantinuum", "a6_phase_error_check.json")
    phase = load_json(phase_p) if os.path.exists(phase_p) else None
    from scipy.stats import poisson
    exp_hits_aer = sum(preds[c]["aer_channel_no_error_probability"] * r[1] * r[2] + r[1] * r[3] / r[4]
                       for c, r in zip(rows_ids, rows68))
    n_hits = sum(r[0] for r in rows68)
    return {
        "present": True, "session": os.path.relpath(sess_p, ROOT), "noise_model": sess.get("noise_model"),
        "laptop_rule": timing,
        "reference_hits_total": n_hits,
        "expected_hits_if_only_error_free_shots_hit_aer_channel": exp_hits_aer,
        "P_hits_ge_observed_if_only_error_free_shots_hit": float(poisson.sf(n_hits - 1, exp_hits_aer)),
        "near_clean_interpretation": (
            "the reference-string estimator counts every shot that ends on the reference string; on a k = 1 "
            "circuit (~91 % of the ideal output on that string) a shot whose errors do not flip any measured "
            "bit also ends there, so the estimator measures 'clean + near-clean', which is >= the error-free "
            "fraction f.  The same mechanism was found on hardware (prompts/20: accepted shots mostly "
            "near-clean)"),
        "phase_error_check": phase,
        "jobs": [{k: j[k] for k in ("circuit_id", "n_shots", "max_cost", "backend_config", "job_id")}
                 for j in sess["jobs"]],
        "sampling_wall_s": sess.get("sampling_wall_s"),
        "garbage_acceptance": a, "garbage_acceptance_source": a_src,
        "clean_statistics_project_path": cs, "reference_string_direct": direct, "predictions": preds,
        "pooled_95": pooled95, "pooled_68": pooled68,
        "pooled_f_estimate": (pooled95 or {}).get("f_clean"), "pooled_f_95": [lo, hi],
        "shots_used": shots_tot, "pooled_prediction_gate_only_model": w_model,
        "pooled_prediction_aer_channel": w_aer,
        "consistent_with_gate_only_model_95": (lo is not None and lo <= w_model <= hi),
        "consistent_with_aer_channel_95": (lo is not None and lo <= w_aer <= hi),
        "readout_factor_note": ("f here = clean_yield (readout_factor 1.0): the prediction f = (1-e2)^n2 "
                                "(1-e1)^n1 (1-ero)^nm already contains the readout survival, so the project's "
                                "0.82 factor would count it twice; the 0.82-convention value is in "
                                "clean_statistics_project_path"),
        "calibration": cal,
    }


def stage_predict(args):
    import quantinuum_device_table as qt

    from skqd.exact import Model

    t0 = time.time()
    rc = qt.main()
    table = load_json(DEVICES)
    idx, mans, cals = manifests()
    hqc_by_id = {c: m["hqc_per_shot"] for c, m in mans.items()}
    # Q5: hqc_per_shot from the manifests' counts vs the manifests and the table
    recomputed = {c: qn.hqc_per_shot(m["counts"]) for c, m in mans.items()}
    q5_manifest = max(abs(recomputed[c] - m["hqc_per_shot"]) for c, m in mans.items())
    q5_table = abs(float(np.mean(list(recomputed.values()))) - table["rows"]["2x3|quantinuum_h2_2"]["hqc_per_shot_mean"])
    V = fragment("verify")
    if not V:
        raise SystemExit("run --stage verify first (the D3' plan reads its frozen-circuit distributions)")
    model = Model(3)
    pilot = pilot_ids(idx)
    print(f"  predict: device table done ({time.time() - t0:.0f} s)", flush=True)
    dists, xcheck = sector_p(model, mans, V, pilot)
    print(f"  predict: sector distributions + cross-check ({time.time() - t0:.0f} s)", flush=True)
    pref_diff = max(abs(float(dists[c]["p"][dists[c]["sector_indices"].index(int(m["reference"]))]) - m["p_reference"])
                    for c, m in mans.items())
    k4_of_pilot = [c.replace("_k1", "_k4") for c in pilot]
    pilot_plan = cost_of_plan({c: PILOT_SHOTS for c in pilot}, mans, hqc_by_id)
    pilot_plan.update({"device": "H2-2", "ids": pilot, "rule": "Stage P: B0 and B1 k = 1 at 1000 shots each",
                       "go_rule_full_campaign": "pooled device f 95 % lower bound >= 0.05 and point estimate >= 0.10"})
    e_shots = {c: E_K1_SHOTS for c in pilot} | {c: E_K4_SHOTS for c in k4_of_pilot}
    stage_e = cost_of_plan(e_shots, mans, hqc_by_id)
    stage_e.update({"device": "H2-2E", "unit": "eHQC", "rule": "E2: k = 1 at 1000 shots, k = 4 at 200 shots, B0 and B1",
                    "max_cost_per_job": {c: round(stage_e["per_circuit"][c]["hqc"] * MAX_COST_MARGIN, 2) for c in e_shots},
                    "go_rule": GO_RULE})
    campaign = {f"f={f:.2f}": d3_plan(mans, dists, f, hqc_by_id) for f in CAMPAIGN_F}
    campaign_d3type = {f"f={f:.2f}": d3type_plan(mans, f, hqc_by_id) for f in CAMPAIGN_F}
    print(f"  predict: D3' campaign plans ({time.time() - t0:.0f} s)", flush=True)
    usd = table["billing"]["usd_per_hqc_ESTIMATE"]["value"]
    h22 = table["rows"]["2x3|quantinuum_h2_2"]
    shot_s_mid = h22["memory_ESTIMATE"]["scenarios"]["mid"]["shot_time_s"]
    for v in list(campaign.values()) + list(campaign_d3type.values()):
        v["usd_ESTIMATE_azure_standard_equivalent"] = v["hqc_total"] * usd
        v["machine_hours_mid_ESTIMATE_H2-2"] = v["shots_total"] * shot_s_mid / 3600.0
    pilot_plan["usd_ESTIMATE_azure_standard_equivalent"] = pilot_plan["hqc_total"] * usd
    # Q5 check of the totals: the formula applied to the plan's shots
    def formula_total(plan):
        """Independent recomputation: every job of at most 10,000 shots through qn.hqc_job."""
        tot = 0.0
        for c, s in plan["shots_by_circuit"].items():
            full, rest = divmod(int(s), qn.MAX_SHOTS_PER_JOB)
            tot += full * qn.hqc_job(mans[c]["counts"], qn.MAX_SHOTS_PER_JOB)
            if rest:
                tot += qn.hqc_job(mans[c]["counts"], rest)
        return tot
    finite = [pilot_plan, stage_e] + list(campaign_d3type.values()) + [v for v in campaign.values() if v["finite_campaign"]]
    q5_totals = max(abs(formula_total(v) - v["hqc_total"]) / max(1.0, v["hqc_total"]) for v in finite)
    devices = {}
    for key, row in table["rows"].items():
        lat, dev = key.split("|")
        if lat != "2x3":
            continue
        pil = {}
        for c in pilot:
            from skqd.device_req import clean_shot_fraction
            cc = mans[c]["counts"]
            pil[c] = clean_shot_fraction(cc["n_zz"], cc["n_phasedx"], cc["n_meas"], row["eps2"], row["eps1"], row["eps_ro"])
        devices[dev] = {"device": row["device"], "f_gate_only_mean": row["f_gate_only_mean"],
                        "f_gate_only_worst": row["f_gate_only_worst"],
                        "f_gate_only_pilot_circuits": pil,
                        "memory_scenarios_ESTIMATE": {k: v["f_with_memory"] for k, v in
                                                      row["memory_ESTIMATE"]["scenarios"].items()},
                        "meets_mean_0.1_gate_only": row["meets_mean_0.1_gate_only"],
                        "meets_worst_0.05_gate_only": row["meets_worst_0.05_gate_only"],
                        "eps2_for_mean_f_0.1": row["eps2_for_mean_f_0.1"]}
    dry = analyse_dryrun(model, mans, cals)
    print(f"  predict: dry-run statistics ({time.time() - t0:.0f} s)", flush=True)
    frag = {"device_table": os.path.relpath(DEVICES, ROOT), "device_table_returncode": rc,
            "reproduction_ok": table["reproduction_ok"],
            "prototype_reproduction": table["prototype_reproduction"],
            "ionq_reproduction_max_abs_diff": max(v["abs_diff"] for v in table["ionq_reproduction"].values()),
            "spec_fields_ok": all(s.get("source") and s.get("read_on") and s.get("verbatim") for s in table["specs"].values()),
            "estimates_flagged": (table["memory_model"]["flag"] == "ESTIMATE"
                                  and table["billing"]["usd_per_hqc_ESTIMATE"]["flag"] == "ESTIMATE"
                                  and all("memory_ESTIMATE" in r for r in table["rows"].values())),
            "hqc": {"recomputed_vs_manifest_max_abs": q5_manifest, "mean_vs_table_abs": q5_table,
                    "plan_totals_vs_formula_max_abs": q5_totals,
                    "per_shot": {"mean": float(np.mean(list(recomputed.values()))),
                                 "min": min(recomputed.values()), "max": max(recomputed.values())},
                    "planner_value_at_prototype_counts": qn.hqc_per_shot({"n_phasedx": 3053, "n_zz": 2158,
                                                                          "n_qubits": 20, "n_meas": 20})},
            "p_reference_sector_vector_vs_manifest_max_abs": pref_diff,
            "p_sector_statevector_vs_group_evolution_max_abs": xcheck,
            "sector_mass_min": min(d_["mass"] for d_ in dists.values()),
            "devices": devices, "pilot_plan": pilot_plan, "stage_E_plan": stage_e, "campaign": campaign,
            "campaign_d3type": campaign_d3type,
            "d3prime_reachable_at_2x3": all(v["finite_campaign"] for v in campaign.values()),
            "dryrun": dry, "go_rule": GO_RULE, "runtime_s": time.time() - t0}
    save_fragment("predict", frag)
    return assemble()


# =========================================================================== emulator (not run)
def stage_assemble_emulator(args):
    sess = os.path.join(EMU_DIR, "session.json")
    if not os.path.exists(sess):
        save_fragment("emulator", {"status": "not run", "reason": (
            "prompts/26 Stage E needs a Quantinuum Nexus login and the owner's eHQC budget; neither exists "
            "(coordinator ruling 2026-10-02).  No emulator session in " + os.path.relpath(EMU_DIR, ROOT))})
        return assemble()
    raise SystemExit("an emulator session exists: its analysis is a later prompt's work (prompts/26 E4); "
                     "this executor did not run Stage E")


# =========================================================================== assembly
def assemble():
    t0 = time.time()
    V, P, E = fragment("verify"), fragment("predict"), fragment("emulator")
    R = GateResult(GATE, TITLE)
    data = {"what_pass_means": WHAT_PASS_MEANS, "prompt": "prompts/26_2x3_circuits_for_quantinuum_h2_helios.md",
            "stage_A": {}, "stage_E": (E or {"status": "not run"}), "stage_P": {"status": "not run (not under prompts/26)"}}
    idx, mans, cals = manifests()
    stack = load_json(STACK) if os.path.exists(STACK) else None
    # ---- Q1
    if V:
        per = V["per_circuit"]
        dpsi = max(v["state_vs_original_ir"]["max_abs_dpsi"] for v in per.values())
        leak = max(abs(v["leakage"]) for v in per.values())
        okmap = all(v["measure_map_identity"] and v["implicit_permutation_identity"] and v["native"] for v in per.values())
        worst = max(per, key=lambda c: per[c]["state_vs_original_ir"]["max_abs_dpsi"])
        build_dpsi = max(m["levels"][str(m["frozen_level"])]["state_vs_original_ir"]["max_abs_dpsi"] for m in mans.values())
        q1 = len(per) == N_CIRCUITS and dpsi < Q1_DPSI and leak < Q1_LEAK and okmap and build_dpsi < Q1_DPSI
        R.add("Q1 44 frozen native circuits exact: max abs(dpsi) (global phase removed), leakage, q[k]->c[k], "
              "identity permutation, native op set",
              f"{len(per)} circuits; max abs(dpsi) {dpsi:.2e} ({worst}; build {build_dpsi:.2e}); leakage {leak:.2e}; "
              f"maps/permutations/op set {'all ok' if okmap else 'NOT ok'}",
              f"44; < {Q1_DPSI:g}; < {Q1_LEAK:g}; identity", q1)
        data["stage_A"]["Q1"] = {"max_abs_dpsi": dpsi, "worst_id": worst, "max_leakage": leak,
                                 "build_max_abs_dpsi": build_dpsi, "maps_ok": okmap}
    else:
        R.add("Q1 frozen circuits exact", "verify stage not run", "run --stage verify", False)
    # ---- Q2
    rzz_build = {c: m["transpile"]["rzz"] for c, m in mans.items()}
    lv = {c: {L: m["levels"][L]["counts"]["n_zz"] for L in m["levels"] if "counts" in m["levels"][L]} for c, m in mans.items()}
    frozen_zz = {c: m["counts"]["n_zz"] for c, m in mans.items()}
    rzz_ver = {c: v["rzz_before_compilation"] for c, v in V["per_circuit"].items()} if V else {}
    q2 = (len(mans) == N_CIRCUITS and all(v == RZZ_EXPECTED for v in rzz_build.values())
          and (not V or all(v == RZZ_EXPECTED for v in rzz_ver.values()))
          and all(z <= RZZ_EXPECTED for z in frozen_zz.values()) and all(len(v) == 2 for v in lv.values())
          and bool(V))
    zz_by_level = {L: sorted({v[L] for v in lv.values() if L in v}) for L in ("0", "2")}
    R.add("Q2 RZZ count before compilation = 2158 on all 44 (build and re-transpiled); ZZ per level recorded; "
          "frozen ZZ <= 2158",
          f"build {sorted(set(rzz_build.values()))}, verify {sorted(set(rzz_ver.values())) or 'n/a'}; ZZ level 0 "
          f"{zz_by_level['0']}, level 2 {zz_by_level['2']}; frozen {sorted(set(frozen_zz.values()))}; frozen levels "
          f"{sorted({m['frozen_level'] for m in mans.values()})}",
          "= 2158; recorded; <= 2158", q2)
    data["stage_A"]["Q2"] = {"rzz_build": rzz_build, "rzz_verify": rzz_ver, "zz_by_level": lv, "frozen_zz": frozen_zz}
    # ---- Q3
    if V:
        rt_json = max(max(v["json_round_trip_max_abs_dpsi_raw"] for v in V["per_circuit"].values()),
                      max(m["round_trips"]["json_max_abs_dpsi_raw"] for m in mans.values()))
        rt_qasm = max(max(v["qasm_vs_json"]["max_abs_dpsi"] for v in V["per_circuit"].values()),
                      max(m["round_trips"]["qasm"]["max_abs_dpsi"] for m in mans.values()))
        sha_ok = all(v["qasm_sha256_ok"] and v["json_sha256_ok"] for v in V["per_circuit"].values())
        cnt_ok = all(v["qasm_counts_equal"] and v["counts_match_manifest"] for v in V["per_circuit"].values())
        en = V["endianness"]
        q3 = rt_json < Q3_RT and rt_qasm < Q3_RT and sha_ok and cnt_ok and en["ok"]
        R.add("Q3 JSON and QASM round trips identical; files match their sha256; endianness X on q0 -> key 1",
              f"JSON {rt_json:.2e}, QASM {rt_qasm:.2e} (QASM drops the global phase); sha256 "
              f"{'ok' if sha_ok else 'MISMATCH'}; counts {'equal' if cnt_ok else 'DIFFER'}; keys "
              f"{en['key_statevector']}/{en['key_backendresult']}/{en['key_qiskit_reader']}",
              f"< {Q3_RT:g}; ok; key 1", q3)
        data["stage_A"]["Q3"] = {"json_round_trip": rt_json, "qasm_round_trip": rt_qasm, "sha_ok": sha_ok,
                                 "endianness": en}
    else:
        R.add("Q3 round trips and endianness", "verify stage not run", "run --stage verify", False)
    # ---- Q4-Q6
    if P:
        pr = P["prototype_reproduction"]
        q4 = (P["reproduction_ok"] and P["spec_fields_ok"] and P["estimates_flagged"]
              and P["ionq_reproduction_max_abs_diff"] <= Q45_TOL)
        R.add("Q4 device table reproduces the prototype's Quantinuum gate-only f and the IonQ rows; specs carry "
              "source/read_on/verbatim; estimates flagged",
              f"prototype max abs diff {max(v['abs_diff'] for v in pr.values()):.1e} (H2-2 "
              f"{pr['quantinuum_h2_2']['f_table']:.5f}, Helios-1 {pr['quantinuum_helios_1']['f_table']:.5f}, H1-1 "
              f"{pr['quantinuum_h1_1']['f_table']:.5f}, H2-1 {pr['quantinuum_h2_1']['f_table']:.5f}); IonQ max abs diff "
              f"{P['ionq_reproduction_max_abs_diff']:.1e}; fields {P['spec_fields_ok']}; ESTIMATE flags {P['estimates_flagged']}",
              f"<= {Q45_TOL:g}; all present", q4)
        h = P["hqc"]
        q5 = (h["recomputed_vs_manifest_max_abs"] <= Q45_TOL and h["mean_vs_table_abs"] <= Q45_TOL
              and h["plan_totals_vs_formula_max_abs"] <= Q45_TOL)
        R.add("Q5 hqc_per_shot from the manifests = table value; pilot / Stage-E / campaign HQC = formula on the plan's shots",
              f"per shot {h['per_shot']['mean']:.4f} mean ({h['per_shot']['min']:.4f}-{h['per_shot']['max']:.4f}); "
              f"manifest abs diff {h['recomputed_vs_manifest_max_abs']:.1e}, table abs diff {h['mean_vs_table_abs']:.1e}; "
              f"plan totals relative diff {h['plan_totals_vs_formula_max_abs']:.1e}; pilot {P['pilot_plan']['hqc_total']:.0f} HQC",
              f"<= {Q45_TOL:g} (per shot), <= 1e-12 relative (totals)", q5)
        d = P["dryrun"]
        if d.get("present"):
            jobs = d["jobs"]
            k1 = [j for j in jobs if j["circuit_id"].endswith("_k1")]
            calj = [j for j in jobs if j["circuit_id"].startswith("CAL_")]
            body_ok = all(j["backend_config"]["no_opt"] is True and j["backend_config"]["allow_implicit_swaps"] is False
                          and j["max_cost"] is not None and j["job_id"] is None for j in jobs)
            cred = None
            if V and not V["checks"].get("skipped"):
                cred = V["checks"]["pytest_venv"]["returncode"] == 0
            q6 = len(k1) == 2 and len(calj) == 2 and body_ok and d["pooled_f_95"][0] is not None and cred is True
            R.add("Q6 dry run: session + counts for the 2 k = 1 and 2 calibration circuits; job bodies no_opt, "
                  "allow_implicit_swaps false, max_cost; credential test (venv pytest); A6 f interval with shots",
                  f"{len(k1)} k=1 + {len(calj)} cal jobs; bodies {'ok' if body_ok else 'NOT ok'}; credential test "
                  f"{'pass' if cred else ('not run' if cred is None else 'FAIL')}; f {d['pooled_f_estimate']:.4f} "
                  f"95% [{d['pooled_f_95'][0]:.4f}, {d['pooled_f_95'][1]:.4f}] at {d['shots_used']} shots "
                  f"(gate-only model {d['pooled_prediction_gate_only_model']:.4f}, Aer channel "
                  f"{d['pooled_prediction_aer_channel']:.4f})",
                  "present; ok; reported", q6)
        else:
            R.add("Q6 dry run", "no dry-run session", "run scripts/quantinuum_submit.py --dry-run", False)
        data["stage_A"]["predict"] = P
    else:
        for q in ("Q4 device table", "Q5 HQC", "Q6 dry run"):
            R.add(q, "predict stage not run", "run --stage predict", False)
    # ---- Q7
    if V and not V["checks"].get("skipped"):
        ch = V["checks"]
        pins_ok = (ch["pins_now"] == PINS_EXPECTED and stack is not None and stack["pins_unchanged"]
                   and stack["coding_freeze_identical"])
        q7 = (ch["pytest_coding"]["returncode"] == 0 and ch["pytest_venv"]["returncode"] == 0
              and ch["check_package"]["returncode"] == 0 and pins_ok)
        R.add("Q7 pytest -q tests (coding and venv) and check_package.py pass; the pinned versions unchanged",
              f"coding: {ch['pytest_coding']['summary']}; venv: {ch['pytest_venv']['summary']}; check_package rc "
              f"{ch['check_package']['returncode']}; pins {ch['pins_now']} (unchanged {pins_ok})",
              "all pass; pins = qiskit 2.5.2 / aer 0.17.2 / runtime 0.49.0 / numpy 2.5.2 / scipy 1.18.0", q7)
        data["stage_A"]["Q7"] = {"checks": ch, "stack_check": os.path.relpath(STACK, ROOT)}
    else:
        R.add("Q7 tests and pins", "not run (--skip-tests or verify missing)", "all pass", False)
    data["stack"] = stack
    data["frozen"] = {"dir": os.path.relpath(CIRC, ROOT), "index_summary": idx["summary"],
                      "versions": idx["versions"], "selection_rule": idx["selection_rule"],
                      "other_devices": {d_: sorted({str(m["other_devices"][d_].get("byte_identical_to_H2-2",
                                                                                   m["other_devices"][d_].get("error")))
                                                   for m in mans.values()}) for d_ in ("H1-1", "Helios-1")},
                      "level2_diagnostics": next((m["diagnostics"] for m in mans.values() if "diagnostics" in m), None),
                      "level2_state_residual_max": max(m["levels"]["2"]["state_vs_original_ir"]["max_abs_dpsi"]
                                                       for m in mans.values() if "counts" in m["levels"]["2"]),
                      "level2_prob_residual_max": max(m["levels"]["2"]["state_vs_original_ir"]["max_abs_dprob"]
                                                      for m in mans.values() if "counts" in m["levels"]["2"])}
    data["verify"] = V
    R.data = data
    R.runtime_s = (V or {}).get("runtime_s", 0.0) + (P or {}).get("runtime_s", 0.0) + time.time() - t0
    path = R.save()
    write_report(f"{GATE}.md", report_text(R, data))
    print(f"{GATE}: {'PASS' if R.passed else 'FAIL'} -> {os.path.relpath(path, ROOT)}")
    for c in R.criteria:
        print(f"  [{'PASS' if c.passed else 'FAIL'}] {c.name}: {c.value}")
    return 0 if R.passed else 1


def fmt(x, nd=4):
    if x is None:
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    return f"{x:.{nd}g}" if (abs(x) >= 1e-3 or x == 0) else f"{x:.3e}"


def report_text(R, D):
    P = (D["stage_A"] or {}).get("predict")
    F = D["frozen"]
    s = F["index_summary"]
    lines = [f"# Gate {GATE} — {TITLE}", "",
             f"Status: **{'PASS' if R.passed else 'FAIL'}** ({len(R.criteria)} criteria).  Generated by "
             f"`scripts/gate_Q0P_2x3.py` from `validation/{GATE}.json`; no number here is typed by hand.  {env_block()}",
             "", f"What PASS means (prompts/26, verbatim): \"{WHAT_PASS_MEANS}\".", "",
             "Stage E (vendor emulator): **" + str(D["stage_E"].get("status")) + "** — " + str(D["stage_E"].get("reason", "")),
             "", "Stage P (device pilot): **not run** (not under prompts/26).", "",
             "## Criteria", "", R.criteria_table(), "",
             "## The frozen circuits", "",
             f"`{F['dir']}/`: 44 circuits `B<sector>_ref<r>_k<k>` + `CAL_zeros`, `CAL_x0`, each as QASM (`hqslib1`), "
             f"pytket JSON and a manifest; `index.json` lists the sha256 of every file.  Compiled with pytket "
             f"{F['versions'].get('pytket')} / pytket-quantinuum {F['versions'].get('pytket-quantinuum')} on the offline "
             f"API handler for H2-2.  Selection rule: {F['selection_rule']}.", "",
             md_table(["quantity", "min", "mean", "max"],
                      [["ZZPhase per circuit", s["n_zz"]["min"], fmt(s["n_zz"]["mean"]), s["n_zz"]["max"]],
                       ["PhasedX per circuit", s["n_phasedx"]["min"], fmt(s["n_phasedx"]["mean"]), s["n_phasedx"]["max"]],
                       ["HQC per shot", fmt(s["hqc_per_shot"]["min"]), fmt(s["hqc_per_shot"]["mean"]),
                        fmt(s["hqc_per_shot"]["max"])]]), "",
             f"Frozen level(s): {s['frozen_levels']}.  Level 2 with measurements changes the STATE (max abs(dpsi) "
             f"{fmt(F['level2_state_residual_max'])}) but not the measured distribution (max abs(dp) "
             f"{fmt(F['level2_prob_residual_max'])}): TKET removes the Rz gates in front of a Measure.  Q1 is a state "
             f"criterion, so level 2 is not eligible; on the unitary part alone level 2 is exact (diagnostic circuit: "
             f"{fmt(((F['level2_diagnostics'] or {}).get('level2_without_measurement') or {}).get('state_vs_original_ir', {}).get('max_abs_dpsi'))}).  "
             f"Other devices at the frozen level: H1-1 byte-identical {F['other_devices']['H1-1']}; Helios-1 "
             f"{F['other_devices']['Helios-1']} (the offline machine list of pytket-quantinuum has no Helios-1 entry; "
             f"the H2-2 circuits are kept — same native gate set).", ""]
    if P:
        lines += ["## Devices (gate-only f of the frozen family; memory term = ESTIMATE)", "",
                  md_table(["device", "f mean", "f worst", "low", "mid", "high", "mean >= 0.1", "worst >= 0.05",
                            "eps2 for mean 0.1"],
                           [[v["device"], fmt(v["f_gate_only_mean"]), fmt(v["f_gate_only_worst"]),
                             fmt(v["memory_scenarios_ESTIMATE"]["low"]), fmt(v["memory_scenarios_ESTIMATE"]["mid"]),
                             fmt(v["memory_scenarios_ESTIMATE"]["high"]), v["meets_mean_0.1_gate_only"],
                             v["meets_worst_0.05_gate_only"], fmt(v["eps2_for_mean_f_0.1"])]
                            for v in P["devices"].values()]), "",
                  "## Plans and cost (HQC = 5 + C (N_1q + 10 N_2q + 5 N_m)/5000 per job; USD at the Azure-Standard-equivalent ESTIMATE)", "",
                  md_table(["plan", "shots", "jobs", "HQC", "USD (ESTIMATE)"],
                           [["Stage E (H2-2E, eHQC)", fmt(P["stage_E_plan"]["shots_total"]), P["stage_E_plan"]["jobs"],
                             fmt(P["stage_E_plan"]["hqc_total"]), "-"],
                            ["Stage P pilot (H2-2)", fmt(P["pilot_plan"]["shots_total"]), P["pilot_plan"]["jobs"],
                             fmt(P["pilot_plan"]["hqc_total"]), fmt(P["pilot_plan"]["usd_ESTIMATE_azure_standard_equivalent"])]]
                           + [[f"campaign, D3-type union reading at 0.7 f, {k} (N_sector "
                               f"{ {s_: v['sectors'][s_]['N_sector_rule'] for s_ in v['sectors']} })",
                               fmt(v["shots_total"]), v["jobs"], fmt(v["hqc_total"]),
                               fmt(v["usd_ESTIMATE_azure_standard_equivalent"])]
                              for k, v in P["campaign_d3type"].items()]
                           + [[f"campaign, rule D3' at 0.7 f, {k}: N4 B=0 {float(v['N4']['B=0']):.2e}, B=1 "
                               f"{float(v['N4']['B=1']):.2e} (NOT a finite campaign)" if not v["finite_campaign"] else
                               f"campaign, rule D3' at 0.7 f, {k}", f"{float(v['shots_total']):.2e}", f"{float(v['jobs']):.2e}",
                               f"{float(v['hqc_total']):.2e}", f"{float(v['usd_ESTIMATE_azure_standard_equivalent']):.2e}"]
                              for k, v in P["campaign"].items()]), "",
                  ("Rule D3' (every sector state >= lambda* expected clean counts) is NOT reachable at 2x3: "
                   + "; ".join(f"{s_}: {r_['states_with_sum_k4_p_below_1e-6']} of {r_['states']} states have total "
                               f"k = 4 probability < 1e-6 (min {r_['min_sum_k4_p']:.1e})"
                               for s_, r_ in next(iter(P["campaign"].values()))["k4_reachability"].items())
                   + ".  The D3-type union reading (gate S1's recall rule, the planner's prototype rule) is the "
                     "finite plan; D3' needs a planner ruling (a reachable-support restriction) before it can size a "
                     "2x3 campaign." if not P.get("d3prime_reachable_at_2x3", True) else ""), ""]
        d = P["dryrun"]
        if d.get("present"):
            lines += ["## A6 local dry run (gate-only H2-2 noise, no memory term; path check)", "",
                      f"{d['shots_used']} shots over the two k = 1 circuits; pooled reference-string estimate f = "
                      f"{fmt(d['pooled_f_estimate'])}, 95 % Garwood [{fmt(d['pooled_f_95'][0])}, {fmt(d['pooled_f_95'][1])}]; "
                      f"predictions: gate-only model {fmt(d['pooled_prediction_gate_only_model'])} (consistent: "
                      f"{d['consistent_with_gate_only_model_95']}), Aer channel {fmt(d['pooled_prediction_aer_channel'])} "
                      f"(consistent: {d['consistent_with_aer_channel_95']}).  {d['readout_factor_note']}.  Sampling "
                      f"{fmt(d['sampling_wall_s'])} s.", "",
                      f"Reference-string hits {d['reference_hits_total']} against {fmt(d['expected_hits_if_only_error_free_shots_hit_aer_channel'])} "
                      f"expected if only error-free shots (and garbage) hit it (Poisson P(>= observed) "
                      f"{fmt(d['P_hits_ge_observed_if_only_error_free_shots_hit'])}).  Interpretation: "
                      f"{d['near_clean_interpretation']}." + (
                          f"  Direct check with a Z-type-only channel of the same error-event rate on "
                          f"{d['phase_error_check']['circuit']} ({d['phase_error_check']['shots']} shots, "
                          f"`data/quantinuum/a6_phase_error_check.json`): {d['phase_error_check']['reference_hits']} hits, "
                          f"{fmt(d['phase_error_check']['expected_hits_if_only_error_free_shots_hit'])} expected from error-free "
                          f"shots alone, {fmt(d['phase_error_check']['expected_hits_if_phase_errors_leave_the_reference'])} if every "
                          f"phase error left the shot on the reference." if d.get('phase_error_check') else ""), "",
                      f"30-minute rule: A6 asked for {d['laptop_rule']['planned_shots_per_circuit']} shots per circuit; the "
                      f"two-point pilot (12 / 40 shots) measured {fmt(d['laptop_rule'].get('s_per_shot_of_the_4_circuit_call'))} s "
                      f"per shot of the 4-circuit call, i.e. {fmt(d['laptop_rule'].get('estimate_at_planned_shots_s'))} s at "
                      f"{d['laptop_rule']['planned_shots_per_circuit']} shots against a {fmt(d['laptop_rule']['budget_s'])} s budget, "
                      f"so the run used {d['laptop_rule']['shots_used_per_k1_circuit']} shots per circuit.  "
                      f"{d['laptop_rule'].get('full_run_needs', '')}.", ""]
    lines += ["## What the owner must do before Stage E", "",
              "A Quantinuum Nexus login (QCUP allocation, a research agreement, or an Azure Quantum workspace) and a "
              "written eHQC budget with `--max-cost` per job and `--cap-hqc` for the stage (prompts/26, 'What the owner "
              "must do').  Then: `quantinuum_account.py --login`, `quantinuum_submit.py --syntax-check` (free), "
              "`--emulate --max-cost ...`, `gate_Q0P_2x3.py --stage assemble-emulator`.", ""]
    return "\n".join(lines)


def stage_prereg_md(args):
    P = fragment("predict")
    if not P:
        raise SystemExit("run --stage predict first")
    L = ["# Q0P_2x3 preregistration block (prompts/26 A8) — generated from data/quantinuum/q0p_stages/predict.json", "",
         f"Created {P['created']}.  Every number below is copied by `scripts/gate_Q0P_2x3.py --stage prereg-md` from "
         "the JSON; none is typed.  These are PREDICTIONS from vendor-published error rates (gate-only) and an "
         "ESTIMATE of the memory term; the vendor emulator (Stage E) replaces the memory estimate.", "",
         "## Per device: gate-only f of the 44 frozen circuits and the three memory scenarios (ESTIMATE)", "",
         md_table(["device", "f mean", "f worst", "pilot k=1 circuits", "low", "mid", "high"],
                  [[v["device"], fmt(v["f_gate_only_mean"]), fmt(v["f_gate_only_worst"]),
                    ", ".join(f"{c}: {fmt(x)}" for c, x in v["f_gate_only_pilot_circuits"].items()),
                    fmt(v["memory_scenarios_ESTIMATE"]["low"]), fmt(v["memory_scenarios_ESTIMATE"]["mid"]),
                    fmt(v["memory_scenarios_ESTIMATE"]["high"])] for v in P["devices"].values()]), "",
         "## Stage E plan (H2-2E, noise model on; eHQC)", "",
         md_table(["circuit", "shots", "jobs", "eHQC", "max_cost (formula + 10 %)"],
                  [[c, v["shots"], v["jobs"], fmt(v["hqc"]), P["stage_E_plan"]["max_cost_per_job"][c]]
                   for c, v in P["stage_E_plan"]["per_circuit"].items()]), "",
         f"Total {fmt(P['stage_E_plan']['hqc_total'])} eHQC.  GO rule: {P['go_rule']}.", "",
         "## Stage P pilot (H2-2; not under prompts/26)", "",
         md_table(["circuit", "shots", "jobs", "HQC"],
                  [[c, v["shots"], v["jobs"], fmt(v["hqc"])] for c, v in P["pilot_plan"]["per_circuit"].items()]), "",
         f"Total {fmt(P['pilot_plan']['hqc_total'])} HQC (USD {fmt(P['pilot_plan']['usd_ESTIMATE_azure_standard_equivalent'])}, "
         f"Azure-Standard-equivalent ESTIMATE).  Full-campaign GO rule: {P['pilot_plan']['go_rule_full_campaign']}.", "",
         "## Full campaign, finite plan: the D3-type union reading at 0.7 f (data/S2D_recall_at_f.json, gate S1's "
         "recall rule, scaled as 1/(0.7 f), spread evenly over the sector's circuits)", "",
         md_table(["f", "N_sector", "shots", "jobs (<= 10,000 shots each)", "HQC", "USD ESTIMATE", "machine hours (H2-2 mid ESTIMATE)"],
                  [[fmt(v["f"]), {s_: v["sectors"][s_]["N_sector_rule"] for s_ in v["sectors"]}, fmt(v["shots_total"]),
                    v["jobs"], fmt(v["hqc_total"]), fmt(v["usd_ESTIMATE_azure_standard_equivalent"]),
                    fmt(v["machine_hours_mid_ESTIMATE_H2-2"])] for v in P["campaign_d3type"].values()]), "",
         "## Rule D3' at 0.7 f (scripts/h0_support_plan.n4_of_sector; floor 267, round 100, lambda* from "
         "skqd.skqd.poisson_lambda_star, readout factor 0.82 as the rule defines it)", "",
         md_table(["f", "N4 B=0", "N4 B=1", "finite campaign", "k = 4 reachability"],
                  [[fmt(v["f"]), f"{float(v['N4']['B=0']):.3e}", f"{float(v['N4']['B=1']):.3e}", v["finite_campaign"],
                    "; ".join(f"{s_}: {r_['states_with_sum_k4_p_below_1e-6']}/{r_['states']} states below 1e-6 "
                              f"(min {r_['min_sum_k4_p']:.1e})" for s_, r_ in v["k4_reachability"].items())]
                   for v in P["campaign"].values()]), ""]
    write_report(f"{GATE}_prereg.md", "\n".join(L))
    print(f"wrote reports/{GATE}_prereg.md")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("verify", "predict", "prereg-md", "assemble-emulator", "assemble"))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--checks-only", action="store_true",
                    help="verify: keep the per-circuit results, re-run only the tests / pins (Q7)")
    args = ap.parse_args()
    if args.stage == "verify":
        return stage_verify(args)
    if args.stage == "predict":
        return stage_predict(args)
    if args.stage == "prereg-md":
        return stage_prereg_md(args)
    if args.stage == "assemble-emulator":
        return stage_assemble_emulator(args)
    return assemble()


if __name__ == "__main__":
    sys.exit(main())
