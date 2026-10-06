#!/usr/bin/env python3
"""
prompts/33 A6: the laptop pre-check of the two class-3 engines that run without a Quantinuum account,
written to data/campaign33/engines.json (versions, s/shot, keep/drop and the reason).

    V1=~/.local/share/su2qc-pecos/venv/bin/python     # pytket-quantinuum[pecos] 0.59.3 (H2-1LE)
    V2=~/.local/share/su2qc-selene/venv/bin/python    # selene-sim 0.3.4 (+ qir-qis)
    V3=~/.local/share/su2qc-quantinuum/venv/bin/python  # pytket-qir 2.0.2 (the QIR export)
    $V1 scripts/campaign33_engines.py --probe pecos  [--circuit B0_ref117_k1 --shots 2]
    $V3 scripts/campaign33_engines.py --export-qir   [--variant native|rx]
    $V2 scripts/campaign33_engines.py --probe selene [--variant native|rx]
    python scripts/campaign33_engines.py --write --pip-log-dir <dir>

Each probe writes data/campaign33/engine_probes/<engine>[_<tag>].json; --write combines them with the pip
attempts (the commands and the decisive lines of their logs, quoted) into engines.json.  Rule (prompts/33
A6): drop C3_LE if the install fails or the measured s/shot > 60 s (fewer than 50 shots in a 50-minute
job); drop C3_SEL unless Selene's Quest simulator runs the QIR with IdealErrorModel at 2 shots and the
counts decode.  A dropped token stays in the table; its job is simply not requested.
"""
import argparse
import glob
import json
import os
import platform
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "campaign33")
PROBES = os.path.join(OUT, "engine_probes")
Q0P = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
QIR = os.path.join(OUT, "qir")
S_PER_SHOT_MAX = 60.0
STAGE_E = ("B0_ref25_k1", "B1_ref57_k1", "B0_ref25_k4", "B1_ref57_k4")


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def versions(pkgs):
    from importlib import metadata
    out = {"python": sys.version.split()[0]}
    for p in pkgs:
        try:
            out[p] = metadata.version(p)
        except Exception:
            out[p] = None
    return out


def load_avg():
    try:
        return list(os.getloadavg())
    except OSError:
        return None


def bits_to_int(bits):
    return int(sum(int(b) << k for k, b in enumerate(bits)))


def probe_pecos(args):
    from pytket import Circuit
    from pytket.extensions.quantinuum import QuantinuumBackend
    from pytket.extensions.quantinuum.backends.api_wrappers import QuantinuumAPIOffline
    man = json.load(open(os.path.join(Q0P, args.circuit + ".manifest.json")))
    c = Circuit.from_dict(json.load(open(os.path.join(Q0P, args.circuit + ".json"))))
    be = QuantinuumBackend(device_name="H2-1LE", api_handler=QuantinuumAPIOffline())
    la0 = load_avg()
    t0 = time.time()
    h = be.process_circuit(c, n_shots=args.shots, simulator="state-vector", noisy_simulation=False, seed=7)
    r = be.get_result(h)
    dt = time.time() - t0
    counts = {str(bits_to_int(k)): int(v) for k, v in r.get_counts().items()}
    rec = {"engine": "pecos", "backend": "QuantinuumBackend('H2-1LE', api_handler=QuantinuumAPIOffline())",
           "options": {"simulator": "state-vector", "noisy_simulation": False, "seed": 7},
           "circuit": args.circuit, "shots": args.shots, "seconds": dt, "seconds_per_shot": dt / args.shots,
           "counts": counts, "reference_int": man["reference_int"],
           "reference_hits": counts.get(str(man["reference_int"]), 0),
           "load_average_before": la0, "load_average_after": load_avg(), "tag": args.tag,
           "versions": versions(["pytket", "pytket-quantinuum", "pytket-pecos", "quantum-pecos", "numpy"]),
           "platform": platform.platform(), "cpu_count": os.cpu_count(), "created": now()}
    os.makedirs(PROBES, exist_ok=True)
    path = os.path.join(PROBES, "pecos" + (f"_{args.tag}" if args.tag else "") + ".json")
    json.dump(rec, open(path, "w"), indent=1)
    print(json.dumps({k: rec[k] for k in ("seconds", "seconds_per_shot", "counts", "load_average_before")}))


def export_qir(args):
    from pytket import Circuit, OpType
    from pytket.passes import AutoRebase
    from pytket.qir import QIRFormat, QIRProfile, pytket_to_qir
    os.makedirs(os.path.join(PROBES, "qir"), exist_ok=True)
    out = {}
    for cid in [args.circuit]:
        c = Circuit.from_dict(json.load(open(os.path.join(Q0P, cid + ".json"))))
        if args.variant == "rx":
            AutoRebase({OpType.Rx, OpType.Rz, OpType.ZZPhase}).apply(c)
        for prof in (QIRProfile.ADAPTIVE, QIRProfile.BASE, QIRProfile.PYTKET):
            s = pytket_to_qir(c, name=cid, qir_format=QIRFormat.STRING, profile=prof)
            p = os.path.join(PROBES, "qir", f"{cid}_{args.variant}_{prof.name}.ll")
            with open(p, "w") as fh:
                fh.write(s)
            out[prof.name] = os.path.relpath(p, ROOT)
    json.dump({"exports": out, "variant": args.variant, "versions": versions(["pytket", "pytket-qir"]),
               "created": now()}, open(os.path.join(PROBES, f"qir_export_{args.variant}.json"), "w"), indent=1)
    print(out)


def probe_selene(args):
    import pathlib

    from selene_sim import IdealErrorModel, Quest, build
    res = {}
    for f in sorted(glob.glob(os.path.join(PROBES, "qir", f"{args.circuit}_{args.variant}_*.ll"))):
        prof = os.path.basename(f).rsplit("_", 1)[1][:-3]
        t0 = time.time()
        try:
            inst = build(pathlib.Path(f), name=f"probe_{args.variant}_{prof.lower()}")
            t1 = time.time()
            shots = [list(s) for s in inst.run_shots(Quest(random_seed=7), n_qubits=20, n_shots=2,
                                                      error_model=IdealErrorModel(), random_seed=7)]
            res[prof] = {"ok": True, "build_s": t1 - t0, "run_s": time.time() - t1, "shots": str(shots)}
        except Exception as exc:
            res[prof] = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:400]}"}
    rec = {"engine": "selene", "circuit": args.circuit, "variant": args.variant, "per_profile": res,
           "versions": versions(["selene-sim", "selene-core", "qir-qis", "numpy"]), "created": now()}
    os.makedirs(PROBES, exist_ok=True)
    json.dump(rec, open(os.path.join(PROBES, f"selene_{args.variant}.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


def pip_lines(path, keys):
    if not path or not os.path.exists(path):
        return None
    out = []
    for line in open(path, errors="replace"):
        if any(k in line for k in keys):
            out.append(line.rstrip()[:300])
    return out[-40:]


def write(args):
    d = args.pip_log_dir
    lp = lambda n: os.path.join(d, n) if d else None  # noqa: E731
    P = lambda n: json.load(open(os.path.join(PROBES, n))) if os.path.exists(os.path.join(PROBES, n)) else None  # noqa: E731
    pecos_probes = {os.path.basename(f)[:-5]: json.load(open(f)) for f in sorted(glob.glob(os.path.join(PROBES, "pecos*.json")))}
    idle = pecos_probes.get("pecos_idle") or pecos_probes.get("pecos")
    sps = idle["seconds_per_shot"] if idle else None
    keep_le = bool(idle and sps is not None and sps <= S_PER_SHOT_MAX)
    sel = {v: P(f"selene_{v}.json") for v in ("native", "rx")}
    sel_ok = any(r and any(x.get("ok") for x in r["per_profile"].values()) for r in sel.values())
    rec = {
        "produced_by": "scripts/campaign33_engines.py --write", "prompt": "prompts/33 A6", "created": now(),
        "qpu_seconds": 0, "hqc": 0,
        "rule": ("drop C3_LE if the install fails or s/shot > 60 s (fewer than 50 shots in a 50-minute job); drop "
                 "C3_SEL unless Selene's Quest simulator runs the QIR with IdealErrorModel at 2 shots and the counts "
                 "decode (prompts/33 A6).  A dropped token stays in scripts/gate_tokens.json; its job is not requested."),
        "C3_LE": {
            "engine": "pytket-quantinuum[pecos] 0.59.3 local emulator H2-1LE (quantum-pecos 0.8.0.dev8), noiseless",
            "venv": "~/.local/share/su2qc-pecos/venv (python 3.12.14 from the coding env, no system site packages)",
            "attempts": [
                {"command": 'pip install "numpy<2" "pytket~=2.17" "pytket-quantinuum[pecos]==0.59.3"',
                 "source": "prompts/33 A6 / 7d verbatim", "result": "FAILED: ResolutionImpossible",
                 "log": pip_lines(lp("pecos_pip_attempt1.log"), ("ERROR", "depends on", "conflict", "requested"))},
                {"command": 'pip install "pytket~=2.17" "pytket-quantinuum[pecos]==0.59.3"',
                 "reason": ("quantum-pecos 0.8.0.dev8 does NOT require numpy<2 (its METADATA: guppylang>=0.21.6, "
                            "hugr>=0.13.0, networkx, pecos-rslib==0.8.0.dev8, phir>=0.3.3, selene-sim~=0.2.0); every "
                            "guppylang release requires numpy>=2.2.6 (or ~=2.0/~=2.5), so the prompt's numpy<2 pin "
                            "makes the set unsatisfiable; dropping the pin resolves it"),
                 "result": "installed",
                 "log": pip_lines(lp("pecos_pip_attempt2.log"), ("Successfully installed", "ERROR"))}],
            "probes": pecos_probes,
            "seconds_per_shot_used_for_the_decision": sps,
            "decision": "keep" if keep_le else "drop",
            "reason": (f"measured {sps:.1f} s per shot at 20 qubits on the H2-1LE state-vector emulator "
                       f"({idle['shots']} shots of {idle['circuit']}, load average {idle['load_average_before']}); "
                       f"{'<=' if keep_le else '>'} 60 s/shot: {int(3000 / sps) if sps else 0} shots fit a 50-minute job"
                       if idle else "no probe"),
            "perlmutter_env_if_kept": ("conda create -n skqd-pecos python=3.12 -y && conda activate skqd-pecos && pip "
                                       "install \"pytket~=2.17\" \"pytket-quantinuum[pecos]==0.59.3\"  (WITHOUT the "
                                       "prompt's numpy<2 pin, which is unsatisfiable)")},
        "C3_SEL": {
            "engine": "selene-sim 0.3.4 (QuEST statevector, IdealErrorModel) on a pytket-qir 2.0.2 QIR export",
            "venv": "~/.local/share/su2qc-selene/venv (python 3.12.14, no system site packages)",
            "attempts": [
                {"command": 'pip install "selene-sim==0.3.4"', "result": "installed (numpy 2.5.3)",
                 "log": pip_lines(lp("selene_pip_attempt2.log"), ("Successfully installed", "ERROR"))},
                {"step": "build(<pytket-qir QIR>) with Quest + IdealErrorModel, 2 shots",
                 "result": "FAILED: ModuleNotFoundError: QIR support requires the optional `qir-qis` dependency."},
                {"command": 'pip install "qir-qis"', "result": "installed (qir-qis 0.1.11)",
                 "log": pip_lines(lp("selene_qirqis_pip.log"), ("Successfully installed", "ERROR"))},
                {"step": "build(<pytket-qir QIR, profiles ADAPTIVE / BASE / PYTKET>)",
                 "result": "FAILED", "probe": sel.get("native")},
                {"step": "the same circuit rebased to {Rx, Rz, ZZPhase} before the export (removes PhasedX)",
                 "result": "FAILED", "probe": sel.get("rx")}],
            "decision": "keep" if sel_ok else "drop",
            "reason": ("Selene's QIR front end (qir-qis 0.1.11) rejects `__quantum__qis__read_result__body`, which "
                       "pytket-qir 2.0.2 emits for every measurement in every profile (and "
                       "`__quantum__qis__phasedx__body` unless rebased): the QIR route of prompts/33 A6 does not run; a "
                       "HUGR/Guppy route would be a new conversion, not built here" if not sel_ok else
                       "Selene ran the QIR at 2 shots")},
        "laptop": {"platform": platform.platform(), "cpu_count": os.cpu_count()},
    }
    path = os.path.join(OUT, "engines.json")
    json.dump(rec, open(path, "w"), indent=1)
    print(f"wrote {os.path.relpath(path, ROOT)}: C3_LE {rec['C3_LE']['decision']}, C3_SEL {rec['C3_SEL']['decision']}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", choices=("pecos", "selene"))
    ap.add_argument("--export-qir", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--circuit", default="B0_ref117_k1")
    ap.add_argument("--shots", type=int, default=2)
    ap.add_argument("--variant", default="native", choices=("native", "rx"))
    ap.add_argument("--tag", default="")
    ap.add_argument("--pip-log-dir", default=None)
    a = ap.parse_args()
    if a.probe == "pecos":
        return probe_pecos(a)
    if a.probe == "selene":
        return probe_selene(a)
    if a.export_qir:
        return export_qir(a)
    if a.write:
        return write(a)
    ap.error("nothing to do")


if __name__ == "__main__":
    sys.exit(main())
