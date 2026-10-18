#!/usr/bin/env python3
"""
prompts/33f R5: assemble the qiskit-aer GPU Kraus report bundle in data/campaign33/aer_gpu_kraus_report/ (the owner files
it on Qiskit/qiskit-aer).  Every number in the bundle's README.md and summary.json is read from a committed JSON here;
nothing is typed by hand.

Run it in the qiskit 1.4.3 / aer 0.15.1 twin (the CI's versions), so that the exported noise-model dictionaries are the
ones the CI built:

    ~/.local/share/su2qc-qiskit143/venv/bin/python scripts/campaign33_aer_report.py

Writes: README.md, summary.json, circuit_IBM-T0_B0_ref117_k1.qpy.gz (+ circuit.qasm3 when qasm3.dumps accepts the
delays), noise_model_kraus.json.gz, noise_model_rm.json.gz (gzip: 13-17 MB each as plain JSON), relaxation_pass.json, counts/*.json + *.npz, logs/ (the two CI job
logs, the C2_KCHK JSONs, the laptop segment JSONs), environment/ (pip freeze of this interpreter; the CI's env is not in
the job logs).  reproduce.py is a static, self-contained file in the bundle (no skqd import) and is not written here.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")]

OUT = os.path.join(ROOT, "data", "campaign33", "aer_gpu_kraus_report")
FAMILY, CID = "IBM-T0", "B0_ref117_k1"
CIRCUIT_SRC = f"data/campaign33/circuits/{FAMILY}/{CID}.qpy.gz"
KCHK1 = "validation/archive/C2_KCHK_job59780907.json"
KCHK2 = "validation/C2_KCHK.json"
C2CAL = "validation/C2_CAL.json"
LAPTOP = "data/campaign33/c33c_diag/summary.json"
DECISION = "data/campaign33/c2_representation_decision.json"
RELEASE_NOTES = "data/campaign33/aer_release_notes_check.json"
ONEQ = ("data/campaign33/c33c_diag/oneq_q53_qiskit1.4.3.json", "data/campaign33/c33c_diag/oneq_q53_qiskit2.5.2.json")
DELAYS = ("data/campaign33/c33c_diag/delays_q53_qiskit1.4.3.json", "data/campaign33/c33c_diag/delays_q53_qiskit2.5.2.json")
CI_LOGS = ("reports/ci-59780907.out", "reports/ci-59828887.out")
SIGMA = 3.0


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def load(p):
    with open(_abs(p)) as fh:
        return json.load(fh)


def sha256(p):
    with open(_abs(p), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def git_commit():
    try:
        c = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
        dirty = subprocess.call(["git", "-C", ROOT, "diff", "--quiet", "--", "src", "scripts"]) != 0
        return c + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1)


def qpy_version(path) -> int:
    """The QPY format version: byte 6 of the uncompressed file (after the 6-byte magic b'QISKIT')."""
    with gzip.open(_abs(path), "rb") as fh:
        head = fh.read(7)
    if head[:6] != b"QISKIT":
        raise ValueError(f"{path}: not a QPY file")
    return int(head[6])


# --------------------------------------------------------------------------- the arms
def _chunks_of(arm: dict) -> list:
    return [{"index": c.get("index"), "seed": int(c["seed"]), "shots": int(c["shots"]),
             "counts": {str(k): int(v) for k, v in c["counts"].items()}} for c in arm["raw_counts"]["chunks"]]


def arms_table() -> dict:
    """Every arm of the case, with its source JSON, job, engine, shots, mean weight +- se, s/shot and (where stored) the
    raw counts by chunk with seeds."""
    from skqd.campaign33 import stats as ST
    r1, r2, cal, lap = load(KCHK1)["data"], load(KCHK2)["data"], load(C2CAL)["data"], load(LAPTOP)
    phys = r1["arms"]["rm_gpu_cusv"]["structure"]["physical_by_clbit"]
    out = {}

    def add(name, src, job, engine, opts, rep, structure, sps, chunks=None, note=None):
        tot = {}
        for c in chunks or []:
            for k, v in c["counts"].items():
                tot[int(k)] = tot.get(int(k), 0) + int(v)
        if chunks:
            s = ST.garbage_structure(tot, len(phys), phys)
            d = max([abs(s["mean_hamming_weight"] - structure["mean_hamming_weight"])]
                    + [abs(a - b) for a, b in zip(s["marginals_by_clbit"], structure["marginals_by_clbit"])])
            if d > 1e-12:
                raise SystemExit(f"{name}: raw counts do not reproduce the stored structure ({d})")
        out[name] = {"source": src, "job": job, "engine": engine, "simulator_options": opts, "representation": rep,
                     "shots": int(structure["shots"]), "mean_hamming_weight": structure["mean_hamming_weight"],
                     "se_mean_hamming_weight": structure["se_mean_hamming_weight"],
                     "sd_hamming_weight": structure["sd_hamming_weight"],
                     "marginals_by_clbit": structure["marginals_by_clbit"], "seconds_per_shot": sps,
                     "raw_counts": bool(chunks), "chunks": chunks, "note": note}

    for arm in ("kraus_gpu_cusv", "kraus_gpu_native", "kraus_gpu_cusv_nofusion", "rm_gpu_cusv"):
        a = r1["arms"][arm]
        add(f"C2_KCHK_run1:{arm}", KCHK1, "59780907", "GPU " + a["gpu_mode"], a["simulator_options"], a["representation"],
            a["structure"], a["seconds_per_shot"], _chunks_of(a))
    a = r2["arms"]["rm_gpu_cusv_anchor"]
    add("C2_KCHK_run2:rm_gpu_cusv_anchor", KCHK2, "59828887", "GPU " + a["gpu_mode"], a["simulator_options"], "rm",
        a["structure"], a["seconds_per_shot"], _chunks_of(a))
    for arm in ("kraus_cpu", "rm_cpu"):
        a = r2["arms"][arm]
        add(f"C2_KCHK_run2:{arm}", KCHK2, "59828887", a["engine"] + " (qiskit-aer-gpu wheel, CPU path)",
            a["simulator_options"], a["representation"], a["structure"], a["seconds_per_shot"], _chunks_of(a))
    cal_job = str(((cal.get("run") or {}).get("ci") or {}).get("SLURM_JOB_ID") or "59736871")
    for arm in ("kraus", "rm", "pta"):
        a = cal["arms"][arm]
        add(f"C2_CAL_run3:{arm}", C2CAL, cal_job, "GPU " + str(a.get("mode")), a["simulator_options"], arm,
            a["structure"], a.get("seconds_per_shot_mean"), None,
            "the C2_CAL JSON stores the structure (weight, marginals) and the chunk seeds, not the raw counts")
    for arm in ("cpu_kraus", "cpu_rm"):
        a = lap["arms"][arm]
        chunks = []
        for sp in [x.strip() for x in a["source"].split(",") if x.strip()]:
            seg = load(sp)
            # a segment stores its calls' seeds and its pooled counts; the counts are kept per segment
            chunks.append({"index": len(chunks), "segment": sp, "seed": int(seg["calls"][0]["seed"]),
                           "calls": [{"seed": int(c["seed"]), "shots": int(c["shots"])} for c in seg["calls"]],
                           "shots": int(sum(int(c["shots"]) for c in seg["calls"])),
                           "counts": {str(k): int(v) for k, v in seg["counts"].items()}})
        add(f"laptop:{arm}", LAPTOP, None, "CPU statevector, laptop (qiskit-aer CPU wheel)",
            load(chunks[0]["segment"]).get("simulator_options"), a["structure"].get("representation") or arm[4:],
            a["structure"], a["seconds_per_shot"], chunks,
            "seeds per call: seed0 + 1000 x call index within a segment; counts pooled per segment")
    return out


def weight_z(a, b):
    return (a["mean_hamming_weight"] - b["mean_hamming_weight"]) / math.hypot(a["se_mean_hamming_weight"],
                                                                              b["se_mean_hamming_weight"])


def fisher(a, b):
    from skqd.campaign33 import stats as ST
    na, nb = a["shots"], b["shots"]
    xa = [round(p * na) for p in a["marginals_by_clbit"]]
    xb = [round(p * nb) for p in b["marginals_by_clbit"]]
    f = ST.fisher_marginals(xa, na, xb, nb)
    return {"min_p": f["min_p"], "argmin_clbit": f["argmin_clbit"], "flagged_clbits": f["flagged_clbits"],
            "p_by_clbit": f["p_by_clbit"]}


EXHIBITS = {
    "1_gpu_vs_gpu (same channel, fusion on/off and kernel choice)": [
        ("C2_KCHK_run1:kraus_gpu_cusv_nofusion", "C2_KCHK_run1:kraus_gpu_cusv"),
        ("C2_KCHK_run1:kraus_gpu_native", "C2_KCHK_run1:kraus_gpu_cusv"),
        ("C2_KCHK_run1:kraus_gpu_native", "C2_KCHK_run1:kraus_gpu_cusv_nofusion")],
    "2_gpu_kraus_vs_cpu_kraus (identical software versions)": [
        ("C2_KCHK_run1:kraus_gpu_cusv", "C2_KCHK_run2:kraus_cpu"),
        ("C2_KCHK_run1:kraus_gpu_cusv", "laptop:cpu_kraus"),
        ("C2_CAL_run3:kraus", "laptop:cpu_kraus"),
        ("C2_KCHK_run2:kraus_cpu", "laptop:cpu_kraus")],
    "3_same_channel_without_kraus_instructions (RM) vs CPU Kraus": [
        ("C2_KCHK_run1:rm_gpu_cusv", "C2_KCHK_run2:kraus_cpu"),
        ("C2_KCHK_run1:rm_gpu_cusv", "laptop:cpu_kraus"),
        ("C2_KCHK_run1:rm_gpu_cusv", "C2_KCHK_run2:rm_cpu"),
        ("C2_KCHK_run1:rm_gpu_cusv", "laptop:cpu_rm"),
        ("C2_KCHK_run2:rm_gpu_cusv_anchor", "C2_KCHK_run1:rm_gpu_cusv")],
}


# --------------------------------------------------------------------------- noise models and the circuit
def export_models(out_dir) -> dict:
    import qiskit
    import qiskit_aer
    from qiskit_aer.noise import NoiseModel

    from skqd.campaign33 import circuits as C
    from skqd.campaign33 import noise as N
    from skqd.campaign33 import tokens_run as TR
    rec = TR.load_record()
    circ = C.load_circuit(FAMILY, CID)
    info = {"record": {"path": os.path.relpath(TR.RECORD, ROOT), "fingerprint": rec.get("fingerprint"),
                       "stamp": rec.get("stamp"), "dt_s": rec.get("dt_s")},
            "model": "I-ECHO (echo T2): NoiseModel.from_backend on a Target carrying the ibm_kingston record "
                     "(depolarizing + thermal relaxation on gates, readout, RelaxationNoisePass on delays)",
            "builder": "skqd.campaign33.noise.ibm_spec(record, 'I-ECHO', representation, 'echo')"}
    passes, specs = {}, {}
    for rep in ("kraus", "rm"):
        spec = N.ibm_spec(rec, "I-ECHO", rep, "echo")
        specs[rep] = spec
        nm = spec.noise_model
        d = nm.to_dict(serializable=True)
        # gzip: the plain JSON is 13-17 MB per model (repository limit); the content is the to_dict export unchanged
        path = os.path.join(out_dir, f"noise_model_{rep}.json.gz")
        with gzip.open(path, "wt") as fh:
            json.dump(d, fh)
        stale = os.path.join(out_dir, f"noise_model_{rep}.json")
        if os.path.exists(stale):
            os.remove(stale)          # an earlier uncompressed export of this script
        try:                          # aer 0.15.1: from_dict does not invert the serializable form (complex as [re, im])
            with gzip.open(path, "rt") as fh:
                NoiseModel.from_dict(json.load(fh))
            direct = "ok"
        except Exception as exc:
            direct = f"{type(exc).__name__}: {exc}"
        cls = N.instruction_classes(spec, circ)
        info[rep] = {"file": os.path.basename(path), "sha256": sha256(path), "n_errors": len(d.get("errors", [])),
                     "kraus_in_to_dict": cls["kraus_to_dict"], "kraus_inserted_by_the_delay_pass": cls["kraus_inserted"],
                     "inserted_error_sites": cls["n_inserted_errors"],
                     "from_dict_on_the_serializable_export": direct,
                     "basis_gates": sorted(nm.basis_gates)}
        ps = nm._custom_noise_passes
        if len(ps) != 1:
            raise SystemExit(f"{rep}: expected one custom pass, found {len(ps)}")
        p = ps[0]
        ops = p._op_types if hasattr(p, "_op_types") else None
        passes[rep] = {"class": f"{type(p).__module__}.{type(p).__name__}", "method": "append",
                       "noise_model_basis_gates": sorted(nm.basis_gates),
                       "op_types": [getattr(o, "__name__", str(o)) for o in (ops if isinstance(ops, (list, tuple)) else [ops])]
                       if ops is not None else None,
                       "dt_s": float(p._dt), "t1_s": [float(x) for x in p._t1s], "t2_s": [float(x) for x in p._t2s],
                       "excited_state_populations": [float(x) for x in p._p1s],
                       "note": ("Aer keeps custom noise passes out of NoiseModel.to_dict(); reproduce.py rebuilds this "
                                "pass and appends it to NoiseModel._custom_noise_passes, as NoiseModel.from_backend does "
                                "in aer 0.15.1 (noise_model.py, the delay_pass block)")}
    changed = N.rm_changed_qubits(rec, range(int(rec["num_qubits"])))
    passes["rm_differs_from_kraus_on"] = {str(q): {"T2_kraus_s": v[0], "T2_rm_s": v[1], "T1_s": v[2]}
                                         for q, v in changed.items()}
    passes["rm_rule"] = "RM = the same construction with T2 := min(T2, T1) per qubit (no Kraus channel anywhere)"
    jdump(os.path.join(out_dir, "relaxation_pass.json"), passes)
    info["relaxation_pass"] = {"file": "relaxation_pass.json", "sha256": sha256(os.path.join(out_dir, "relaxation_pass.json"))}
    # the bundle's own loader (reproduce.load_model) against the models the CI built: every gate / readout error and
    # the delay pass must come back identical (super-operators to 1e-12)
    import importlib.util

    import numpy as np
    from qiskit.quantum_info import SuperOp
    sp = importlib.util.spec_from_file_location("aer_report_reproduce", os.path.join(out_dir, "reproduce.py"))
    REP = importlib.util.module_from_spec(sp)
    sys.dont_write_bytecode = True    # no __pycache__ inside the bundle
    sp.loader.exec_module(REP)
    for rep, spec in specs.items():
        nm0 = spec.noise_model
        nm1 = REP.load_model(rep)
        e0, e1 = N._local_errors(nm0), N._local_errors(nm1)
        worst = max(float(np.max(np.abs(SuperOp(e0[k].to_quantumchannel()).data - SuperOp(e1[k].to_quantumchannel()).data)))
                    for k in e0) if set(e0) == set(e1) else None
        r0, r1 = nm0._local_readout_errors, nm1._local_readout_errors
        ro = max(float(np.max(np.abs(np.asarray(r0[q].probabilities) - np.asarray(r1[q].probabilities)))) for q in r0) \
            if set(r0) == set(r1) else None
        p0, p1 = nm0._custom_noise_passes[0], nm1._custom_noise_passes[0]
        same_pass = bool(np.array_equal(p0._t1s, p1._t1s) and np.array_equal(p0._t2s, p1._t2s)
                         and np.array_equal(p0._p1s, p1._p1s) and p0._dt == p1._dt and len(nm1._custom_noise_passes) == 1)
        info[rep]["reproduce_load_model_check"] = {
            "error_keys_equal": set(e0) == set(e1), "n_errors": len(e0), "max_superop_diff": worst,
            "readout_keys_equal": set(r0) == set(r1), "max_readout_diff": ro, "delay_pass_identical": same_pass,
            "basis_gates_original": sorted(nm0.basis_gates), "basis_gates_rebuilt": sorted(nm1.basis_gates),
            "ok": bool(worst is not None and worst <= 1e-12 and ro is not None and ro == 0.0 and same_pass
                       and set(nm0.basis_gates) <= set(nm1.basis_gates)),
            "rule": "SuperOp max |diff| <= 1e-12 on every gate error, readout identical, delay pass identical, basis "
                    "gates a superset (from_dict adds its defaults)"}
    active = sorted({circ.find_bit(q).index for inst in circ.data for q in inst.qubits
                     if inst.operation.name not in ("barrier", "delay")})
    info["rm_changed_active_qubits"] = sorted(int(q) for q in changed if int(q) in active)
    info["versions"] = {"qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__}
    return info


def export_circuit(out_dir) -> dict:
    import qiskit
    from qiskit import qpy

    dst = os.path.join(out_dir, f"circuit_{FAMILY}_{CID}.qpy.gz")
    shutil.copyfile(_abs(CIRCUIT_SRC), dst)
    with gzip.open(dst, "rb") as fh:
        circ = qpy.load(fh)[0]
    ops, active = {}, set()
    for inst in circ.data:
        ops[inst.operation.name] = ops.get(inst.operation.name, 0) + 1
        if inst.operation.name not in ("barrier", "delay"):
            active.update(circ.find_bit(q).index for q in inst.qubits)
    out = {"file": os.path.basename(dst), "source": CIRCUIT_SRC, "sha256": sha256(dst), "qpy_version": qpy_version(dst),
           "num_qubits": circ.num_qubits, "active_qubits": sorted(active), "num_active_qubits": len(active),
           "num_clbits": circ.num_clbits, "ops": dict(sorted(ops.items())),
           "loaded_with_qiskit": qiskit.__version__}
    try:
        from qiskit import qasm3
        txt = qasm3.dumps(circ)
        p = os.path.join(out_dir, "circuit.qasm3")
        with open(p, "w") as fh:
            fh.write(txt)
        out["qasm3"] = {"file": "circuit.qasm3", "sha256": sha256(p), "ok": True}
    except Exception as exc:          # recorded: the bundle says why there is no QASM file
        out["qasm3"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return out


def export_counts(arms, out_dir) -> dict:
    import numpy as np
    cdir = os.path.join(out_dir, "counts")
    os.makedirs(cdir, exist_ok=True)
    files = {}
    for name, a in arms.items():
        if not a["raw_counts"]:
            continue
        base = name.replace(":", "__")
        doc = {"arm": name, "source": a["source"], "job": a["job"], "engine": a["engine"],
               "simulator_options": a["simulator_options"], "representation": a["representation"], "shots": a["shots"],
               "mean_hamming_weight": a["mean_hamming_weight"], "se_mean_hamming_weight": a["se_mean_hamming_weight"],
               "convention": "keys: int with bit k = clbit k (qiskit counts-key string position j = clbit 19 - j)",
               "seed_rule": "Aer seeds shot j of a call with seed + j; one chunk = one run() call with its seed",
               "chunks": a["chunks"]}
        jdump(os.path.join(cdir, base + ".json"), doc)
        rows = [(int(k), int(v), j, int(c["seed"])) for j, c in enumerate(a["chunks"]) for k, v in c["counts"].items()]
        np.savez_compressed(os.path.join(cdir, base + ".npz"), keys=np.array([r[0] for r in rows], dtype=np.int64),
                            counts=np.array([r[1] for r in rows], dtype=np.int64),
                            chunk_index=np.array([r[2] for r in rows], dtype=np.int64),
                            chunk_seed=np.array([r[3] for r in rows], dtype=np.int64),
                            chunk_shots=np.array([int(c["shots"]) for c in a["chunks"]], dtype=np.int64))
        files[name] = {"json": f"counts/{base}.json", "npz": f"counts/{base}.npz"}
    return files


def export_logs(out_dir) -> list:
    ldir = os.path.join(out_dir, "logs")
    os.makedirs(ldir, exist_ok=True)
    out = []
    lap = load(LAPTOP)
    segs = sorted({s.strip() for arm in ("cpu_kraus", "cpu_rm") for s in lap["arms"][arm]["source"].split(",") if s.strip()})
    for p in list(CI_LOGS) + [KCHK1, KCHK2, LAPTOP] + segs + list(ONEQ) + list(DELAYS) + [RELEASE_NOTES]:
        if not os.path.exists(_abs(p)):
            out.append({"path": p, "present": False})
            continue
        dst = os.path.join(ldir, os.path.basename(p))
        shutil.copyfile(_abs(p), dst)
        out.append({"path": p, "copied_to": os.path.relpath(dst, out_dir), "sha256": sha256(p)})
    return out


def export_environment(out_dir) -> dict:
    edir = os.path.join(out_dir, "environment")
    os.makedirs(edir, exist_ok=True)
    fr = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
    p = os.path.join(edir, "laptop_twin_pip_freeze.txt")
    with open(p, "w") as fh:
        fh.write(fr.stdout)
    r1, r2 = load(KCHK1)["data"], load(KCHK2)["data"]
    ci = {"job_59780907_versions": r1["run"].get("versions"), "job_59828887_versions": r2["run"].get("versions"),
          "job_59828887_cpu_process_aer_wheel": (r2.get("cpu_process") or {}).get("aer"),
          "job_59780907_nodelist": (r1["run"].get("slurm") or {}).get("nodelist"),
          "job_59828887_nodelist": (r2["run"].get("slurm") or {}).get("nodelist"),
          "gpu_telemetry_59780907": r1["run"].get("gpu_telemetry"),
          "pip_freeze_skqd_env": None,
          "cuda_custatevec_driver_gpu_model": None,
          "missing": ("the CI job logs and JSONs carry no pip freeze of the `skqd` env and no CUDA / cuStateVec / driver "
                      "version or GPU model; jobs/gate.sbatch writes gpu_device.csv (name, memory, driver) in the job's "
                      "working directory on $SCRATCH, which the CI does not harvest -- the owner adds these from "
                      "Perlmutter (`conda activate skqd; pip freeze`, `nvidia-smi`, the cuStateVec version of the "
                      "qiskit-aer-gpu wheel)")}
    jdump(os.path.join(edir, "ci_environment.json"), ci)
    return {"laptop_twin_pip_freeze": "environment/laptop_twin_pip_freeze.txt",
            "laptop_python": platform.python_version(), "laptop_host": platform.node(),
            "ci": "environment/ci_environment.json"}


# --------------------------------------------------------------------------- README
def fmt(x, d=3):
    return "-" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def readme(S) -> str:
    A = S["arms"]
    rows = []
    for name, a in A.items():
        rows.append(f"| `{name}` | {a['job'] or 'laptop'} | `{a['source']}` | {a['engine']} | {a['representation']} | "
                    f"{a['shots']} | {fmt(a['mean_hamming_weight'])} $\\pm$ {fmt(a['se_mean_hamming_weight'])} | "
                    f"{fmt(a['seconds_per_shot'], 2)} | {'yes' if a['raw_counts'] else 'no'} |")
    ex = []
    for title, pairs in S["exhibits"].items():
        ex.append(f"\n**Exhibit {title}**\n")
        ex.append("| arm A | arm B | $\\bar w_A$ | $\\bar w_B$ | $z_w$ | Fisher min $p$ (clbit) | clbits with $p<0.0027$ |")
        ex.append("|---|---|---|---|---|---|---|")
        for c in pairs:
            ex.append(f"| `{c['a']}` | `{c['b']}` | {fmt(c['w'][0])} | {fmt(c['w'][1])} | {c['z_w']:+.2f} | "
                      f"{c['fisher']['min_p']:.3g} ({c['fisher']['argmin_clbit']}) | {c['fisher']['flagged_clbits']} |")
    M = S["models"]
    rn = S["release_notes"]
    oneq = "\n".join(f"- `{o['path']}`: {o['summary']}" for o in S["small_scale"]["one_qubit"])
    dl = "\n".join(f"- `{o['path']}`: {o['summary']}" for o in S["small_scale"]["delay_sites"])
    v = S["environment"]["ci_versions"]
    return f"""# qiskit-aer 0.15.1: GPU statevector with Kraus noise instructions samples a different distribution than the CPU statevector

Bundle assembled by `scripts/campaign33_aer_report.py` (prompts/33f R5) at commit {S['git_commit']}, {S['created']}.
Every number below is read from a committed JSON of the su2qc-skqd repository (listed per row) and stored in
`summary.json`; nothing is typed by hand.  Not filed yet: the owner reads it first.

## Claim

On qiskit-aer-gpu 0.15.1 (qiskit {v.get('qiskit')}, numpy {v.get('numpy')}, python {v.get('python')}), `AerSimulator(method="statevector",
precision="double", device="GPU")` running a scheduled circuit on the {S['circuit']['num_qubits']}-qubit device layout
({S['circuit']['num_active_qubits']} active qubits, {S['circuit']['num_clbits']} measured; {S['circuit']['ops'].get('cz', 0)} cz,
{S['circuit']['ops'].get('delay', 0)} delays) with a `NoiseModel.from_backend`-style thermal-relaxation model that contains Kraus
instructions returns a measured distribution that (1) changes with `fusion_enable` and with `cuStateVec_enable` (it
should not: these are execution options), (2) differs from the CPU statevector of the same aer version and the same
model, on two independent CPU installations that agree with each other, and (3) is the only outlier: the same channel
written without Kraus instructions (`T2 := min(T2, T1)` on the qubits with $T_2 > T_1$: {len(M['rm_changed_active_qubits'])} of the
{S['circuit']['num_active_qubits']} active qubits, {M['rm_changed_active_qubits']}, so that Aer's
`thermal_relaxation_error` takes its reset-mixture branch; identical super-operators everywhere else) agrees with CPU
Kraus on both CPU installations.  The GPU Kraus arms all show a lower mean Hamming weight than the CPU, i.e. more
population in $|0\\rangle$ (the direction of excess relaxation).  Observable: the mean Hamming weight $\\bar w$ of the 20
measured bits (with its standard error from the per-shot spread) and the 20 per-clbit marginals.

## Every arm

| arm | job | source JSON | engine | representation | shots | $\\bar w \\pm$ se | s/shot | raw counts |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Statistics

$z_w = (\\bar w_A - \\bar w_B)/\\sqrt{{\\mathrm{{se}}_A^2 + \\mathrm{{se}}_B^2}}$; per clbit, Fisher's exact test on the $2\\times2$ table
(two-sided, `scipy.stats.fisher_exact`), flagged at $P(|Z|>3) = 0.0027$ per test (Bonferroni over 20 clbits: 0.054).
Marginal counts are recovered exactly as $p_k N$ from the stored structures.
{chr(10).join(ex)}

## Files

- `circuit_{FAMILY}_{CID}.qpy.gz` (QPY version {S['circuit']['qpy_version']}, sha256 `{S['circuit']['sha256']}`); `circuit.qasm3`:
  {('present, sha256 `' + S['circuit']['qasm3']['sha256'] + '`') if S['circuit']['qasm3']['ok'] else ('not written: ' + S['circuit']['qasm3']['error'])}.
- `noise_model_kraus.json.gz`, `noise_model_rm.json.gz`: `NoiseModel.to_dict(serializable=True)`, gzipped (13-17 MB each as plain JSON) (aer {M['versions']['qiskit_aer']});
  Kraus instructions in `to_dict`: {M['kraus']['kraus_in_to_dict']} (Kraus model), {M['rm']['kraus_in_to_dict']} (RM model);
  inserted by the delay pass into this circuit: {M['kraus']['kraus_inserted_by_the_delay_pass']} / {M['rm']['kraus_inserted_by_the_delay_pass']} of
  {M['kraus']['inserted_error_sites']} sites.  `NoiseModel.from_dict` applied directly to this serializable export fails in
  aer {M['versions']['qiskit_aer']} (`{M['kraus']['from_dict_on_the_serializable_export'][:120]}`: complex entries are
  written as `[re, im]` and not read back); `reproduce.py` decodes them first.  Its loader rebuilds the models the CI
  built: {M['kraus']['reproduce_load_model_check']['n_errors']} gate errors, super-operator max difference
  {fmt(M['kraus']['reproduce_load_model_check']['max_superop_diff'], 3) if M['kraus']['reproduce_load_model_check']['max_superop_diff'] is None else f"{M['kraus']['reproduce_load_model_check']['max_superop_diff']:.1e}"} (Kraus) /
  {f"{M['rm']['reproduce_load_model_check']['max_superop_diff']:.1e}" if M['rm']['reproduce_load_model_check']['max_superop_diff'] is not None else '-'} (RM), readout and delay pass identical: check
  {M['kraus']['reproduce_load_model_check']['ok']} / {M['rm']['reproduce_load_model_check']['ok']}.
- `relaxation_pass.json`: the `RelaxationNoisePass` on `Delay` (per-qubit $T_1$, $T_2$, excited-state populations, `dt`),
  which `to_dict` does not carry; RM differs from Kraus on qubits {sorted(int(q) for q in M['rm_differs_from_kraus_on'])} of the
  record (active in this circuit: {M['rm_changed_active_qubits']}).
- `reproduce.py`: self-contained (qiskit + qiskit-aer only): loads the QPY, rebuilds both models from the dictionaries,
  appends the relaxation pass, runs the CPU arm and the GPU arms (cuStateVec on/off, fusion on/off) with the recorded
  seeds and prints $\\bar w$ per arm.  `python reproduce.py --help`.
- `counts/`: the raw counts of every arm that stored them (`.json` with chunk seeds and shots, `.npz` with the same rows).
- `logs/`: the CI job logs, the C2_KCHK JSONs (run 1 archive, run 2), the laptop CPU segments and summary, the 1-qubit
  and delay-site checks, the release-note reading.
- `environment/`: `pip freeze` of the laptop twin; `ci_environment.json` with the versions the CI jobs recorded and what
  is missing (below).

## Versions

CI (both jobs, from the JSONs): {json.dumps(v)}; CPU arm wheel on the CI: {S['environment']['ci_cpu_wheel']}.
Laptop twin: {json.dumps(S['environment']['laptop_versions'])} (CPU wheel `qiskit-aer`).
**Not recorded by the jobs (the owner adds them before filing):** the CUDA, cuStateVec and driver versions and the GPU
model; a `pip freeze` of the CI env.

## Small-scale checks (negative results)

{oneq}
{dl}
- The 2- and 8-qubit statevector-vs-density-matrix checks mentioned in prompts/33d R4 have no committed record in
  this repository; they are not quoted here.  No small-scale **GPU** check was run (the CI runs one job at a time).

## Upstream status

Release notes read {rn['read']} ({', '.join(s['url'] for s in rn['sources'])}): {rn['finding']}
Re-checked {S['release_notes_recheck']['date']}: latest release {S['release_notes_recheck']['latest']} -- **no fix found**.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="prompts/33f R5: the qiskit-aer GPU Kraus report bundle")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--latest-release", default=None, help="latest qiskit-aer tag read today (recorded as given)")
    ap.add_argument("--latest-release-date", default=None)
    a = ap.parse_args(argv)
    import qiskit_aer
    if qiskit_aer.__version__ != "0.15.1":
        raise SystemExit(f"run this in the qiskit 1.4.3 / aer 0.15.1 twin (found aer {qiskit_aer.__version__})")
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    arms = arms_table()
    ex = {}
    for title, pairs in EXHIBITS.items():
        ex[title] = [{"a": x, "b": y, "w": [arms[x]["mean_hamming_weight"], arms[y]["mean_hamming_weight"]],
                      "shots": [arms[x]["shots"], arms[y]["shots"]], "z_w": weight_z(arms[x], arms[y]),
                      "fisher": fisher(arms[x], arms[y])} for x, y in pairs]
    circuit = export_circuit(a.out)
    models = export_models(a.out)
    rel = load(os.path.join(a.out, "relaxation_pass.json"))
    models["rm_differs_from_kraus_on"] = rel["rm_differs_from_kraus_on"]
    counts = export_counts(arms, a.out)
    logs = export_logs(a.out)
    env = export_environment(a.out)
    r1 = load(KCHK1)["data"]
    lapv = load(LAPTOP)["arms"]["cpu_kraus"].get("versions")
    oneq = []
    for p in ONEQ:
        d = load(p)
        br = d["by_representation"]
        oneq.append({"path": p, "versions": d["versions"], "shots": d["shots"], "expected_P1": d["expected_P1"],
                     "by_representation": br,
                     "summary": (f"CPU, qiskit {d['versions']['qiskit']} / aer {d['versions']['qiskit_aer']}: x, delay("
                                 f"{d['delay_s'] * 1e6:.0f} us), measure on physical qubit {d['qubit']} (T1 "
                                 f"{d['T1_s'] * 1e6:.1f} us), {d['shots']} shots: P(1) Kraus {br['kraus']['P1']:.4f} "
                                 f"(z {br['kraus']['z_vs_exp']:+.2f}), RM {br['rm']['P1']:.4f} (z {br['rm']['z_vs_exp']:+.2f}) "
                                 f"vs e^(-t/T1) = {d['expected_P1']:.4f}")})
    dsl = []
    for p in DELAYS:
        d = load(p)
        dsl.append({"path": p, "versions": d["versions"], "n_delay_errors": d["n_delay_errors"],
                    "max_superop_diff": d["max_superop_diff"],
                    "summary": (f"qiskit {d['versions']['qiskit']} / aer {d['versions']['qiskit_aer']}: the Kraus and RM "
                                f"models attach {d['n_delay_errors']['kraus']} / {d['n_delay_errors']['rm']} delay errors "
                                f"to physical qubit {d['qubit']} of this circuit ({d['total_delay_s']['kraus'] * 1e6:.1f} us "
                                f"in total); super-operator max |difference| {d['max_superop_diff']}")})
    S = {"title": "qiskit-aer 0.15.1 GPU Kraus report bundle (prompts/33f R5)", "git_commit": git_commit(),
         "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
         "command": "python scripts/campaign33_aer_report.py" + (" " + " ".join(argv) if argv else ""),
         "arms": {k: {kk: vv for kk, vv in v.items() if kk != "chunks"} for k, v in arms.items()},
         "exhibits": ex, "circuit": circuit, "models": models, "counts_files": counts, "logs": logs,
         "environment": {**env, "ci_versions": r1["run"].get("versions"),
                         "ci_cpu_wheel": (load(KCHK2)["data"].get("cpu_process") or {}).get("aer"),
                         "laptop_versions": lapv},
         "small_scale": {"one_qubit": oneq, "delay_sites": dsl},
         "release_notes": load(RELEASE_NOTES),
         "release_notes_recheck": {"date": a.latest_release_date, "latest": a.latest_release,
                                   "source": "https://api.github.com/repos/Qiskit/qiskit-aer/releases"},
         "decision_file": {"path": DECISION, "sha256": sha256(DECISION)} if os.path.exists(_abs(DECISION)) else None,
         "seconds": time.time() - t0}
    jdump(os.path.join(a.out, "summary.json"), S)
    with open(os.path.join(a.out, "README.md"), "w") as fh:
        fh.write(readme(S))
    print(f"wrote {os.path.relpath(a.out, ROOT)}: {len(arms)} arms, {len(counts)} with raw counts, {len(logs)} log files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
