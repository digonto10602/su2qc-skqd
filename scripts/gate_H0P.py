#!/usr/bin/env python3
"""
Gate H0P — H0 preparation on a Heron calibration snapshot (prompts/13 steps 2 and 5).

The frozen circuit set of `scripts/h0_build_circuits.py` (data/hardware/H0_prep) is
sampled with `AerSimulator.from_backend(FakeFez())` inside a wall-clock budget, decoded
with `skqd.codec.Codec.decode_counts`, and turned into the numbers the first QPU session
needs before it is booked:

  * the predicted yield curve versus CZ count, by repetition r = 1, 2, 3 of the coarse
    step: CZ, the clean-shot fraction f of the calibration snapshot (as gate S2D computes
    it), the manual's model yield 0.82 f, the simulated yield and their ratio;
  * the rejection reasons of the decoder (flag / link / sector / unknown) and the
    exhaustive acceptance of random bit strings into each sector (the decoder-validity
    control of prompts/07);
  * the per-qubit readout confusion matrix from the simulated calibration circuits
    (`skqd.hardware.confusion_matrix`);
  * the Ritz consistency check: the decoded supports of the saturated 2x2 sectors must
    reproduce E0 = -3.6408 (B = 0) and -1.8616 (B = 1) to 1e-6;
  * the shot plan from `skqd.skqd.shot_rule` (manual eq. 5) at the simulated yield.

It also writes `reports/H0_prereg_draft.md`, the preregistration paragraph that prompts/07
requires BEFORE any circuit is submitted.  Nothing here touches a QPU.

Usage: python scripts/gate_H0P.py [--prep data/hardware/H0_prep] [--budget-minutes 22]
                                  [--pilot-shots 20] [--min-shots 8] [--cal-shots 4000]
                                  [--p 1e-3] [--k 3] [--conf 0.95] [--seed 11]
                                  [--no-tests] [--out H0P]
Expected runtime: the sampling budget plus about 3 minutes (inside the 30-minute rule).
"""
import argparse
import glob
import gzip
import itertools
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.codec import Codec, Reject  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.hardware import confusion_matrix  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.reference_sim import qiskit_key_to_bits  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import (READOUT_FACTOR, certify, clean_fraction_from_yield,  # noqa: E402
                       ritz, shot_rule, support_metrics, yield_model)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
YIELD_FACTOR = READOUT_FACTOR   # 0.82, manual Step 4.4: readout survival of the clean shots
# manual Step 4.4: "the accepted-shot yield is ~ 0.82 f plus the garbage that decodes as valid"
YIELD_MODEL_NAME = "0.82 f + (1-f) a"
RATIO_LO, RATIO_HI = 1 / 3, 3.0   # the L4 criterion: the model is a rough proxy
LEAK_TOL = 1e-9
E0_TOL = 1e-6
RANDOM_ACCEPT_MAX = 0.01     # prompts/07: acceptance of random-looking strings < 1 %
DIAG_MIN = 0.9               # prompts/13: every readout-confusion diagonal element >= 0.9
EPS_SUPPORT = 1e-3


# ------------------------------------------------------------------ frozen circuit set
def load_index(prep_dir):
    with open(os.path.join(prep_dir, "index.json")) as fh:
        return json.load(fh)


def load_manifests(prep_dir):
    """(coarse-step manifests, calibration manifests), both sorted by id."""
    cdir = os.path.join(prep_dir, "circuits")
    mans = []
    for p in sorted(glob.glob(os.path.join(cdir, "*.json"))):
        with open(p) as fh:
            mans.append(json.load(fh))
    return ([m for m in mans if m["kind"] == "coarse_step"],
            [m for m in mans if m["kind"] == "readout_calibration"])


def load_circuit(prep_dir, manifest):
    from qiskit import qpy
    with gzip.open(os.path.join(prep_dir, "circuits", manifest["qpy"]), "rb") as fh:
        return qpy.load(fh)[0]


# ------------------------------------------------------------------ shared analysis
def random_acceptance(codec, twoB):
    """Exhaustive acceptance of uniformly random bit strings into the sector (2^n strings)."""
    acc, reasons = 0, {}
    for bits in itertools.product((0, 1), repeat=codec.n_qubits):
        try:
            codec.decode(bits, twoB)
            acc += 1
        except Reject as r:
            reasons[str(r)] = reasons.get(str(r), 0) + 1
    n = 2 ** codec.n_qubits
    return {"accepted": acc, "strings": n, "fraction": acc / n, "reasons": reasons}


def analyse_records(records, cal_records, model, g2):
    """records: [(manifest, {bit tuple: count})] for the coarse-step circuits;
    cal_records: the same for the readout-calibration circuits.  Returns the full
    analysis dictionary shared by gate_H0P (simulated) and gate_H0 (device counts)."""
    codec = Codec(model.basis)
    out = {"per_circuit": [], "by_sector_repetition": {}, "by_sector": {},
           "random_acceptance": {}, "confusion": {}}
    for man, _ in records:                      # the decoder's false-acceptance floor per sector
        if man["sector"] not in out["random_acceptance"]:
            out["random_acceptance"][man["sector"]] = random_acceptance(codec, man["twoB"])
    groups, sectors = {}, {}
    for man, counts in records:
        twoB = man["twoB"]
        acc, rej = codec.decode_counts(counts, target_twoB=twoB)
        shots = int(sum(counts.values()))
        n_acc = int(sum(acc.values()))
        out["per_circuit"].append({
            "id": man["id"], "sector": man["sector"], "reference": man["reference"], "k": man["k"],
            "repetitions": man["repetitions"], "cz": man["cz"], "shots": shots, "accepted": n_acc,
            "yield": n_acc / shots if shots else 0.0, "distinct_states": len(acc),
            "f_calibration_snapshot": man.get("f_calibration_snapshot"),
            "rejections": {kk: int(v) for kk, v in rej.items()},
        })
        key = (man["sector"], man["repetitions"])
        g = groups.setdefault(key, {"shots": 0, "accepted": 0, "circuits": 0, "cz": [], "f": [],
                                    "support": set(), "rejections": {}, "twoB": twoB})
        g["shots"] += shots
        g["accepted"] += n_acc
        g["circuits"] += 1
        g["cz"].append(man["cz"])
        if man.get("f_calibration_snapshot") is not None:
            g["f"].append(man["f_calibration_snapshot"])
        g["support"] |= set(acc)
        for kk, v in rej.items():
            g["rejections"][kk] = g["rejections"].get(kk, 0) + int(v)
        s = sectors.setdefault(man["sector"], {"twoB": twoB, "support": set(), "shots": 0, "accepted": 0})
        s["support"] |= set(acc)
        s["shots"] += shots
        s["accepted"] += n_acc

    for (sec, r), g in sorted(groups.items()):
        fmean = float(np.mean(g["f"])) if g["f"] else None
        y = g["accepted"] / g["shots"] if g["shots"] else 0.0
        # manual Step 4.4, both terms: y = 0.82 f + (1 - f) a.  A shot that is not clean is
        # accepted whenever its (essentially random) string is a codeword of the target
        # sector, which happens with the decoder's random-string acceptance a of that sector,
        # so 0.82 f alone describes the yield only while f >> a / 0.82.
        a = out["random_acceptance"][sec]["fraction"]
        clean_y = YIELD_FACTOR * fmean if fmean is not None else None    # the old, first-term-only model
        full_y = yield_model(fmean, a) if fmean is not None else None
        out["by_sector_repetition"][f"{sec} r={r}"] = {
            "sector": sec, "repetitions": r, "circuits": g["circuits"], "shots": g["shots"],
            "accepted": g["accepted"], "yield": float(y),
            "cz_mean": float(np.mean(g["cz"])), "cz_min": int(min(g["cz"])), "cz_max": int(max(g["cz"])),
            "f_calibration_mean": fmean,
            "garbage_acceptance": float(a),
            "yield_model": YIELD_MODEL_NAME,
            "model_yield_0.82f": clean_y,
            "ratio_simulated_over_model": float(y / clean_y) if clean_y else None,
            "model_yield_full": full_y,
            "ratio_simulated_over_full_model": float(y / full_y) if full_y else None,
            "f_from_yield": (clean_fraction_from_yield(y, a) if fmean is not None else None),
            "support_size": len(g["support"]), "rejections": g["rejections"],
        }

    for sec, s in sorted(sectors.items()):
        twoB = s["twoB"]
        ref = model.reference(g2, twoB)
        refs = references(model.basis, twoB)
        B = np.array(sorted(set(s["support"]) | set(refs)))
        res = ritz(model.H(g2), B)
        cert = certify(res, ref.E0, float(ref.energies[1]))
        prob = np.zeros(model.basis.dim)
        prob[ref.indices] = np.abs(ref.ground) ** 2
        met = support_metrics(B, prob, EPS_SUPPORT)
        out["by_sector"][sec] = {
            "twoB": twoB, "shots": s["shots"], "accepted": s["accepted"],
            "yield": s["accepted"] / s["shots"] if s["shots"] else 0.0,
            "support_size_decoded": len(s["support"]), "support_size_with_references": int(len(B)),
            "sector_dimension": int(len(ref.indices)), "references": [int(x) for x in refs],
            "ER": float(res.ER), "exact_E0": float(ref.E0), "abs_error": float(abs(res.ER - ref.E0)),
            "rH": float(res.rH), "weinstein": [float(cert.weinstein[0]), float(cert.weinstein[1])],
            "exact_E0_inside_weinstein": bool(cert.weinstein[0] - 1e-9 <= ref.E0 <= cert.weinstein[1] + 1e-9),
            "recall_99.9pct_support": float(met["recall"]), "false_positives": met["false_positives"],
            "captured_weight": met["captured_weight"],
        }

    # ---------------------------------------------------- readout confusion, per patch
    by_patch = {}
    for man, counts in cal_records:
        by_patch.setdefault(man["patch_index"], {})[tuple(man["prep_bits"])] = counts
    for pi, cbp in sorted(by_patch.items()):
        C = confusion_matrix(cbp, n_qubits=codec.n_qubits)
        man = next(m for m, _ in cal_records if m["patch_index"] == pi)
        phys = man["logical_to_physical"]
        diag = [float(min(C[q, 0, 0], C[q, 1, 1])) for q in range(codec.n_qubits)]
        out["confusion"][f"patch{pi}"] = {
            "physical_qubits_logical_order": phys,
            "matrix": C.tolist(),
            "P_measure_0_given_0": [float(C[q, 0, 0]) for q in range(codec.n_qubits)],
            "P_measure_1_given_1": [float(C[q, 1, 1]) for q in range(codec.n_qubits)],
            "diagonal_min_per_qubit": diag,
            "min_diagonal": float(min(diag)), "mean_diagonal": float(np.mean(diag)),
            "shots_per_prep": {str(list(k)): int(sum(v.values())) for k, v in sorted(cbp.items())},
        }
    if out["confusion"]:
        allmin = [v["min_diagonal"] for v in out["confusion"].values()]
        allmean = [v["mean_diagonal"] for v in out["confusion"].values()]
        out["confusion_summary"] = {"min_diagonal": float(min(allmin)),
                                    "mean_diagonal": float(np.mean(allmean)),
                                    "n_patches": len(out["confusion"])}
    return out


def shot_plan(analysis, p, k, conf):
    """shot_rule (manual eq. 5) at the model yield and at the simulated yield, per sector/r."""
    plan = {}
    for key, v in analysis["by_sector_repetition"].items():
        row = {"sector": v["sector"], "repetitions": v["repetitions"], "circuits": v["circuits"],
               "simulated_yield": v["yield"], "model_yield_0.82f": v["model_yield_0.82f"]}
        for tag, y in (("simulated", v["yield"]), ("model", v["model_yield_0.82f"])):
            if y and y > 0:
                nc = shot_rule(p, y, k, conf)
                row[f"N_circuit_{tag}"] = int(nc)
                row[f"N_sector_{tag}"] = int(nc * v["circuits"])
            else:
                row[f"N_circuit_{tag}"] = None
                row[f"N_sector_{tag}"] = None
        plan[key] = row
    return plan


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--budget-minutes", type=float, default=22.0, help="wall-clock budget for the sampling")
    ap.add_argument("--pilot-shots", type=int, default=60, help="upper point of the two-point pilot")
    ap.add_argument("--pilot-shots-low", type=int, default=10, help="lower point of the two-point pilot")
    ap.add_argument("--pilot-circuits", type=int, default=4, help="circuits per repetition in the pilot")
    ap.add_argument("--min-shots", type=int, default=8)
    ap.add_argument("--shots-by-rep", nargs="*", default=None, metavar="R:SHOTS",
                    help="pin the shots per repetition (e.g. 1:267 2:130 3:92) instead of deriving them "
                         "from the pilot; the pilot still runs and its timings are recorded")
    ap.add_argument("--shot-allocation", default="equal-time", choices=("equal-time", "equal-shots"),
                    help="equal-time: each repetition class gets the same wall clock, so the cheap "
                         "r = 1 circuits get more shots; equal-shots: the same shots everywhere")
    ap.add_argument("--max-shots", type=int, default=20000)
    ap.add_argument("--cal-shots", type=int, default=4000, help="shots per readout-calibration circuit")
    ap.add_argument("--p", type=float, default=1e-3, help="ideal probability in the shot rule")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--conf", type=float, default=0.95)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--out", default="H0P")
    args = ap.parse_args()
    t0 = time.time()
    prep = os.path.join(ROOT, args.prep)
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    if not mans:
        raise SystemExit(f"no frozen circuits in {prep}: run scripts/h0_build_circuits.py first")

    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeFez, FakeTorino

    bname = index["common"]["backend"]
    backend = {"FakeFez": FakeFez, "FakeTorino": FakeTorino}[bname]()
    sim = AerSimulator.from_backend(backend, seed_simulator=args.seed)
    g2 = index["common"]["g2"]
    M = Model(int(index["common"]["lattice"].split("x")[1]))
    n = index["common"]["n_logical_qubits"]

    R = GateResult(args.out, f"H0 preparation on the {bname} calibration snapshot: frozen circuit set, "
                             f"predicted yield curve by repetition, readout confusion, Ritz consistency")

    # ------------------------------------------------------- pilot timing -> shots
    circuits = {m["id"]: load_circuit(prep, m) for m in mans}
    reps = sorted({m["repetitions"] for m in mans})
    # two-point pilot: one simulator call has a fixed setup cost (circuit load, noise binding)
    # plus a cost per circuit-shot; both are measured so that the budget is not spent on setup
    t_shot, setup = {}, {}
    for r in reps:
        ms = [m for m in mans if m["repetitions"] == r][:args.pilot_circuits]
        qs = [circuits[m["id"]] for m in ms]
        tt = []
        for sh in (args.pilot_shots_low, args.pilot_shots):
            tp = time.time()
            sim.run(qs, shots=sh).result()
            tt.append(time.time() - tp)
        dn = (args.pilot_shots - args.pilot_shots_low) * len(ms)
        t_shot[r] = max((tt[1] - tt[0]) / dn, 1e-6)
        setup[r] = max(tt[0] - args.pilot_shots_low * len(ms) * t_shot[r], 0.0)
        print(f"pilot r={r}: {len(ms)} circuits, {args.pilot_shots_low}/{args.pilot_shots} shots -> "
              f"{t_shot[r]:.4f} s per circuit-shot, {setup[r]:.1f} s setup per call", flush=True)
    n_by_rep = {r: len([m for m in mans if m["repetitions"] == r]) for r in reps}
    budget_s = args.budget_minutes * 60
    setup_total = sum(setup[r] * n_by_rep[r] / max(args.pilot_circuits, 1) for r in reps)
    available = max(budget_s - setup_total, 60.0)
    if args.shots_by_rep:
        shots_by_rep = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.shots_by_rep}
    elif args.shot_allocation == "equal-shots":
        tot = sum(n_by_rep[r] * t_shot[r] for r in reps)
        shots_by_rep = {r: int(min(args.max_shots, max(args.min_shots, available / tot))) for r in reps}
    else:                       # equal wall clock per repetition class
        per_class = available / len(reps)
        shots_by_rep = {r: int(min(args.max_shots, max(args.min_shots, per_class / (n_by_rep[r] * t_shot[r]))))
                        for r in reps}
    predicted_s = sum(shots_by_rep[r] * n_by_rep[r] * t_shot[r] for r in reps) + setup_total
    per_shot_total = sum(t_shot[m["repetitions"]] for m in mans)
    print(f"{len(mans)} circuits, {per_shot_total:.2f} s per shot over the whole set -> shots per circuit "
          f"{shots_by_rep} ({args.shot_allocation}, predicted {predicted_s / 60:.1f} min of a "
          f"{args.budget_minutes} min budget)", flush=True)

    # ------------------------------------------------------- sampling
    ts = time.time()
    records = []
    for r in reps:                      # one simulator call per repetition class (amortised overhead)
        ms = [m for m in mans if m["repetitions"] == r]
        cts = sim.run([circuits[m["id"]] for m in ms], shots=shots_by_rep[r]).result().get_counts()
        if isinstance(cts, dict):
            cts = [cts]
        for m, cc in zip(ms, cts):
            records.append((m, {qiskit_key_to_bits(kk): v for kk, v in cc.items()}))
        print(f"  r={r}: {len(ms)} circuits x {shots_by_rep[r]} shots ({time.time() - t0:.0f} s)", flush=True)
    t_sample = time.time() - ts
    tc = time.time()
    cal_records = []
    cal_counts = sim.run([load_circuit(prep, m) for m in cals], shots=args.cal_shots).result().get_counts()
    if isinstance(cal_counts, dict):
        cal_counts = [cal_counts]
    for m, cc in zip(cals, cal_counts):
        cal_records.append((m, {qiskit_key_to_bits(kk): v for kk, v in cc.items()}))
    t_cal = time.time() - tc
    print(f"sampling {t_sample:.0f} s, calibration {t_cal:.0f} s", flush=True)

    # ------------------------------------------------------- analysis
    A = analyse_records(records, cal_records, M, g2)
    plan = shot_plan(A, args.p, args.k, args.conf)
    data = {
        "frozen_set": {kk: index[kk] for kk in ("created", "n_circuits", "n_calibration_circuits",
                                                "repetitions", "kmax", "sectors", "references",
                                                "per_repetition", "distinct_readout_patches", "leakage")},
        "backend": bname, "simulator": f"AerSimulator.from_backend({bname}(), seed_simulator={args.seed})",
        "sampling": {"shots_per_circuit_by_repetition": {str(r): shots_by_rep[r] for r in reps},
                     "shot_allocation": ("pinned with --shots-by-rep" if args.shots_by_rep
                                         else args.shot_allocation),
                     "circuits": len(mans),
                     "total_shots": sum(shots_by_rep[m["repetitions"]] for m in mans),
                     "seconds_per_shot_by_repetition": {str(r): t_shot[r] for r in reps},
                     "setup_seconds_per_call_by_repetition": {str(r): setup[r] for r in reps},
                     "predicted_sampling_seconds": predicted_s,
                     "seconds_per_shot_whole_set": per_shot_total,
                     "budget_minutes": args.budget_minutes, "sampling_seconds": t_sample,
                     "calibration_shots_per_circuit": args.cal_shots, "calibration_seconds": t_cal,
                     "pilot_shots": args.pilot_shots},
        "yield_model": YIELD_MODEL_NAME,
        "garbage_acceptance": {sec: A["random_acceptance"][sec]["fraction"]
                               for sec in sorted(A["random_acceptance"])},
        "yield_model_inputs": {
            "formula": f"y = {YIELD_MODEL_NAME}  (manual Step 4.4, both terms)",
            "readout_factor": YIELD_FACTOR,
            "garbage_acceptance_source": (
                f"exhaustive: all {2 ** n} bit strings through skqd.codec.Codec.decode for the "
                f"target sector (section 3 of this report)"),
            "note": ("the shot rule below keeps using the CLEAN yield 0.82 f: a shot accepted "
                     "because its garbage string happens to be a codeword adds no support"),
        },
        "shot_rule_inputs": {"p": args.p, "k": args.k, "confidence": args.conf,
                             "yield_model": f"y = {YIELD_FACTOR} f (clean shots only, manual eq. 5)"},
        "shot_plan": plan,
        "analysis": A,
    }

    # ------------------------------------------------------- criteria
    lk = index["leakage"]
    R.add(f"every frozen circuit leak-free after transpilation onto {bname} "
          f"({lk['n_checked']} circuits, noiseless statevector permuted back with the final layout)",
          lk["max"], f"< {LEAK_TOL:g}", lk["max"] < LEAK_TOL)
    for sec in sorted(A["by_sector"]):
        s = A["by_sector"][sec]
        R.add(f"{sec}: decoded support reproduces the exact E0 = {s['exact_E0']:.4f}",
              s["abs_error"], f"|E_R - E_0| < {E0_TOL:g}", s["abs_error"] < E0_TOL)
    for sec in sorted(A["random_acceptance"]):
        ra = A["random_acceptance"][sec]
        R.add(f"{sec}: acceptance of random bit strings (exhaustive over all {ra['strings']} strings)",
              f"{100 * ra['fraction']:.3f}%", f"< {100 * RANDOM_ACCEPT_MAX:.0f}%",
              ra["fraction"] < RANDOM_ACCEPT_MAX)
    for key in sorted(A["by_sector_repetition"]):
        v = A["by_sector_repetition"][key]
        ratio = v["ratio_simulated_over_full_model"]
        R.add(f"{key} ({v['cz_mean']:.0f} CZ): simulated yield {v['yield']:.3f} vs the model "
              f"{YIELD_MODEL_NAME} = {v['model_yield_full']:.3f} (a = {v['garbage_acceptance']:.5f}; "
              f"the first term alone, {YIELD_FACTOR} f = {v['model_yield_0.82f']:.3f}, gives "
              f"{v['ratio_simulated_over_model']:.2f})", round(ratio, 3),
              f"ratio in [{RATIO_LO:.2f}, {RATIO_HI:.0f}]", RATIO_LO <= ratio <= RATIO_HI)
    cs = A["confusion_summary"]
    R.add(f"readout confusion matrix on {cs['n_patches']} patch(es): smallest diagonal element",
          round(cs["min_diagonal"], 4), f">= {DIAG_MIN}", cs["min_diagonal"] >= DIAG_MIN)

    # artefacts required by prompts/13
    for name, path in (("dry-run counts of scripts/h0_submit.py --dry-run",
                        os.path.join(ROOT, "data", "hardware", "H0_dryrun", "counts")),):
        cnt = len(glob.glob(os.path.join(path, "*.json"))) if os.path.isdir(path) else 0
        R.add(name, f"{cnt} counts files", "> 0", cnt > 0)
        data.setdefault("artefacts", {})[name] = cnt
    for gate in ("H0_dryrun", "S3_smoke"):
        p = os.path.join(ROOT, "validation", f"{gate}.json")
        ok = os.path.exists(p)
        st = json.load(open(p))["status"] if ok else "missing"
        R.add(f"validation/{gate}.json exists (produced by this step; its own status is reported there)",
              f"present, status {st}" if ok else "missing", "exists", ok)
        data.setdefault("artefacts", {})[f"validation/{gate}.json"] = st
    if not args.no_tests:
        tp = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT,
                            capture_output=True, text=True)
        line = tp.stdout.strip().splitlines()[-1] if tp.stdout.strip() else "no output"
        R.add("pytest -q tests", line, "all pass", tp.returncode == 0)
        data["pytest"] = line

    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report(f"{args.out}_heron_preparation.md", gate_report(args, R, data, index))
    write_report("H0_prereg_draft.md", prereg_report(args, R, data, index))
    print(R.criteria_table())
    return 0 if R.passed else 1


# ------------------------------------------------------------------ reports
def fmt(v, spec=".4f"):
    return "n/a" if v is None else format(v, spec)


def yield_rows(A):
    rows = []
    for key in sorted(A["by_sector_repetition"]):
        v = A["by_sector_repetition"][key]
        rows.append([v["sector"], v["repetitions"], v["circuits"], f"{v['cz_mean']:.0f}",
                     fmt(v["f_calibration_mean"]), fmt(v["garbage_acceptance"], ".5f"),
                     fmt(v["model_yield_0.82f"]), fmt(v["model_yield_full"]),
                     v["shots"], fmt(v["yield"]), fmt(v["ratio_simulated_over_model"], ".2f"),
                     fmt(v["ratio_simulated_over_full_model"], ".2f"),
                     v["support_size"], str(v["rejections"])])
    return rows


YIELD_HEAD = ["sector", "r", "circuits", "CZ", "f (calibration)", "a (garbage)",
              "model 0.82 f (old)", "model 0.82 f + (1−f) a", "shots", "simulated yield",
              "simulated / 0.82 f", "simulated / full model", "distinct states", "rejections"]


def gate_report(args, R, D, index):
    A = D["analysis"]
    S = D["sampling"]
    lk = D["frozen_set"]["leakage"]
    frows = [[r, v["n_circuits"], f"{v['cz']['mean']:.0f}", f"{v['depth']['mean']:.0f}",
              f"{v['f']['mean']:.4f}", f"{v['f']['min']:.4f}", f"{v['f']['max']:.4f}"]
             for r, v in sorted(D["frozen_set"]["per_repetition"].items())]
    srows = [[sec, v["sector_dimension"], v["support_size_decoded"], v["support_size_with_references"],
              f"{v['ER']:.10f}", f"{v['exact_E0']:.10f}", f"{v['abs_error']:.2e}", f"{v['rH']:.2e}",
              f"{v['recall_99.9pct_support']:.3f}", v["false_positives"]]
             for sec, v in sorted(A["by_sector"].items())]
    crows = []
    for pk, v in sorted(A["confusion"].items()):
        for i, q in enumerate(v["physical_qubits_logical_order"]):
            crows.append([pk, i, q, f"{v['P_measure_0_given_0'][i]:.4f}",
                          f"{v['P_measure_1_given_1'][i]:.4f}", f"{v['diagonal_min_per_qubit'][i]:.4f}"])
    rarows = [[sec, f"{v['accepted']} / {v['strings']}", f"{100 * v['fraction']:.3f}%", str(v["reasons"])]
              for sec, v in sorted(A["random_acceptance"].items())]
    prows = [[v["sector"], v["repetitions"], v["circuits"], fmt(v["simulated_yield"]),
              fmt(v["model_yield_0.82f"]), v["N_circuit_simulated"], fmt(v["N_sector_simulated"], ".3e"),
              v["N_circuit_model"], fmt(v["N_sector_model"], ".3e")]
             for v in D["shot_plan"].values()]
    return f"""# Gate {R.gate} — H0 preparation on the {D['backend']} calibration snapshot

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/gate_H0P.py` on the frozen circuit set of
`scripts/h0_build_circuits.py` ({args.prep}, created {D['frozen_set']['created']}).
{env_block()}  Runtime {R.runtime_s:.0f} s.  Nothing in this gate touches a QPU.

## 1. The frozen circuit set

{D['frozen_set']['n_circuits']} coarse-step circuits (both sectors, every reference, k = 1..{D['frozen_set']['kmax']},
r = {D['frozen_set']['repetitions']} repetitions of the step) plus {D['frozen_set']['n_calibration_circuits']} readout-calibration circuits
(all-0, all-1 and the {index['common']['n_logical_qubits']} single-qubit flips on each of the
{len(D['frozen_set']["distinct_readout_patches"])} physical patches the transpiler chose), transpiled onto {D['backend']} at optimization
level {index['common']['transpiler']['optimization_level']}, seed {index['common']['transpiler']['seed_transpiler']}, and stored as QPY with one manifest JSON each.

{md_table(["repetitions r", "circuits", "CZ mean", "depth mean", "f mean", "f min", "f max"], frows)}

Leakage of the **transpiled** circuits (noiseless statevector, measurements removed, permuted back to
logical order with each circuit's own final layout, weight outside the codeword subspace):
max {lk['max']:.2e} over {lk['n_checked']} circuits, tolerance {lk['tolerance']:g}.  The measurement map of every circuit
was checked against its final layout, so classical bit i of every counts key is logical qubit i.

## 2. Predicted yield curve by repetition

Sampling: `{D['simulator']}`, {', '.join(f"{v} shots per r = {k} circuit" for k, v in sorted(S['shots_per_circuit_by_repetition'].items()))}
({S['shot_allocation']} allocation, {S['total_shots']} shots in total, {S['sampling_seconds']:.0f} s; the pilot measured
{', '.join(f"{v:.3f} s/shot at r={k}" for k, v in sorted(S['seconds_per_shot_by_repetition'].items()))},
i.e. {S['seconds_per_shot_whole_set']:.1f} s per shot over the whole set, and the budget was {S['budget_minutes']:.0f} min).

{md_table(YIELD_HEAD, yield_rows(A))}

**The yield model.**  Manual Step 4.4: "the accepted-shot yield is ≈ 0.82 f plus the 0.15 % of garbage that
decodes as valid", i.e. y = {YIELD_MODEL_NAME} (`skqd.skqd.yield_model`).  The first term is the clean shots
that survive readout, with the f of gate S2D (per-edge CZ errors and per-qubit readout errors of the patch
the transpiler chose on this snapshot).  The second term is the non-clean fraction (1 − f) whose bit strings,
after ~1000 CZ, are close to uniformly random and are accepted whenever they happen to be a codeword of the
target sector: that happens with the decoder's random-string acceptance
a = {', '.join(f"{sec} {v['fraction']:.5f}" for sec, v in sorted(A['random_acceptance'].items()))}, measured
exhaustively over all {2 ** index['common']['n_logical_qubits']} bit strings in section 3.  The simulated column is the full Aer device model of the
same snapshot.  The criterion is the ratio "simulated / full model"; the column "simulated / 0.82 f" is the
first term alone, which is the model the gate used before prompts/14 — it describes the yield only while
f >> a / {YIELD_FACTOR} = {max(v['fraction'] for v in A['random_acceptance'].values()) / YIELD_FACTOR:.3f}, i.e. at r = 1 here, and is kept in the table for comparison.
The prediction the H0 session will be judged against is the simulated yield itself (see
`reports/H0_prereg_draft.md`).  The shot plan of section 6 keeps using the CLEAN yield 0.82 f: a shot
accepted because its garbage string is a codeword adds no support.

## 3. Decoder validity

Exhaustive acceptance of random bit strings into each sector ({2 ** index['common']['n_logical_qubits']} strings, the control of prompts/07):

{md_table(["sector", "accepted", "fraction", "rejection reasons"], rarows)}

## 4. Ritz consistency (bit order and conventions)

{md_table(["sector", "sector dimension", "decoded states", "with references", "E_R", "exact E_0",
            "\\|E_R − E_0\\|", "r_H", "recall of the 99.9 % support", "false positives"], srows)}

At 2x2 both sectors saturate, so this is a consistency check of the bit order and the conventions
(manual Step 9.1), not an accuracy test: a permuted codeword would give a different energy.

## 5. Readout confusion (simulated calibration circuits, {S['calibration_shots_per_circuit']} shots each)

{md_table(["patch", "logical qubit", "physical qubit", "P(0\\|0)", "P(1\\|1)", "min diagonal"], crows)}

`skqd.hardware.confusion_matrix` builds the tensored (independent-qubit) model from all
{D['frozen_set']['n_calibration_circuits']} preparations; `skqd.hardware.apply_inverse` unfolds a counts dictionary with its exact tensor
inverse.  Smallest diagonal element over all patches: {A['confusion_summary']['min_diagonal']:.4f}.

## 6. Shot plan (manual eq. 5, `skqd.skqd.shot_rule`, p = {args.p:.0e}, k = {args.k}, confidence {args.conf})

{md_table(["sector", "r", "circuits", "simulated yield", "clean yield 0.82 f", "N/circuit (simulated)",
            "N/sector (simulated)", "N/circuit (clean 0.82 f)", "N/sector (clean 0.82 f)"], prows)}

The budget preregistered for the session is the one computed from the **clean** yield 0.82 f (last two
columns): a shot that is accepted only because its garbage string happens to be a codeword adds no support,
so the garbage term of the yield model must not enter the shot rule.

## Criteria

{R.criteria_table()}

## Scope

Every number above is computed by `scripts/gate_H0P.py` and stored in `validation/{R.gate}.json`.
{D['backend']} is a calibration **snapshot** of a Heron r2 device, not a reservation on one: the real session
replaces the backend argument of `scripts/h0_submit.py` and re-runs `scripts/gate_H0.py` on the returned counts.
"""


def prereg_report(args, R, D, index):
    A = D["analysis"]
    S = D["sampling"]
    fs = D["frozen_set"]
    rows = yield_rows(A)
    prows = [[v["sector"], v["repetitions"], v["circuits"], fmt(v["model_yield_0.82f"]),
              v["N_circuit_model"], fmt(v["N_sector_model"], ".3e"),
              fmt(v["simulated_yield"]), v["N_circuit_simulated"],
              fmt(v["N_sector_simulated"], ".3e")] for v in D["shot_plan"].values()]
    r1 = [v for v in A["by_sector_repetition"].values() if v["repetitions"] == 1]
    return f"""# H0 preregistration (draft) — 2x2 calibration session on a Heron-class device

**Generated by `scripts/gate_H0P.py` from `validation/{R.gate}.json`; no number below is typed by hand.**
{env_block()}

This is the paragraph prompts/07 step 1 requires *before* any circuit is submitted.  It fixes the circuit
set, the expected yields and the criteria; the session then only replaces the backend.

## 1. Frozen circuit set

`{args.prep}` (created {fs['created']}, `scripts/h0_build_circuits.py`):
{fs['n_circuits']} coarse-step circuits = both sectors x every reference x k = 1..{fs['kmax']} x r = {fs['repetitions']}
repetitions of the coarse step, plus {fs['n_calibration_circuits']} readout-calibration circuits.  Each circuit is stored as QPY with a
manifest (sector, reference, k, r, CZ, depth, physical qubits, logical -> physical map, codeword bit order,
link-consistency checks).  Transpiled onto {D['backend']} at optimization level
{index['common']['transpiler']['optimization_level']}, seed {index['common']['transpiler']['seed_transpiler']};
all {fs['leakage']['n_checked']} circuits are leak-free (max {fs['leakage']['max']:.2e} < {fs['leakage']['tolerance']:g}).

CZ per repetition: {', '.join(f"r = {r}: {v['cz']['mean']:.0f}" for r, v in sorted(fs['per_repetition'].items()))}.

## 2. Predicted yields

{md_table(YIELD_HEAD, rows)}

**The yield model (manual Step 4.4, both terms).**  y = {YIELD_MODEL_NAME} = `skqd.skqd.yield_model(f, a)`,
with a = the decoder's random-string acceptance of the target sector
({', '.join(f"{sec} {v['fraction']:.5f}" for sec, v in sorted(A['random_acceptance'].items()))}, exhaustive over all
{2 ** index['common']['n_logical_qubits']} strings) — the "garbage that decodes as valid" of the manual's sentence.  The measured clean-shot
fraction is the inverse, f = (y − a) / ({YIELD_FACTOR} − a) = `skqd.skqd.clean_fraction_from_yield(y, a)`.
The first term alone, {YIELD_FACTOR} f, is kept as a column for comparison: it describes the yield only while
f >> a / {YIELD_FACTOR} = {max(v['fraction'] for v in A['random_acceptance'].values()) / YIELD_FACTOR:.3f}, and on this snapshot it is off by up to
{max(v['ratio_simulated_over_model'] for v in A['by_sector_repetition'].values()):.1f}x at r = 3 while the full model describes every point within
{max(v['ratio_simulated_over_full_model'] for v in A['by_sector_repetition'].values()):.2f}x.  The shot plan in section 3 nevertheless uses the CLEAN yield only: a garbage
string that happens to be a codeword adds no support.

**Which prediction the 30 % criterion of prompts/07 step 4 is judged against: the simulated yield**
with the calibration snapshot of the session day, not the model.  Reason (planner's decision,
prompts/13): the model is conservative by a factor {np.mean([v['ratio_simulated_over_full_model'] for v in A['by_sector_repetition'].values() if v['repetitions'] == 1]):.2f} on the r = 1 circuits of this snapshot
(gate L4_fez measured the same factor on the same snapshot with the same circuits), so judging the device
against the model would reject a device that behaves exactly as simulated.  Both numbers are recorded.

**The criterion applies to the r = 1 circuits only.**  At r = 2 and r = 3 the clean-shot fraction
({', '.join(f"r = {v['repetitions']}: f = {v['f_calibration_mean']:.4f}" for v in A['by_sector_repetition'].values() if v['sector'] == 'B=0')})
falls to the level of a itself, so inverting the yield for f is ill-conditioned there however good the model
is.  On the session day, r = 2 and r = 3 measure the SHAPE of the yield-versus-CZ curve (manual Step 9.1),
not f.

On the session day the predicted yields are recomputed from **that day's** calibration by re-running
`scripts/h0_build_circuits.py --backend <device>` and `scripts/gate_H0P.py`, before submission.

## 3. Shot plan (manual Step 4.4, eq. 5; `skqd.skqd.shot_rule`)

N_circuit = ceil(lambda*/(p y)) with p = {args.p:.0e}, k = {args.k}, confidence {args.conf}.  **The budget uses the
CLEAN yield y = {YIELD_FACTOR} f**, not the accepted yield: a shot that is accepted only because its garbage
string happens to be a codeword carries no configuration and adds no support.  The columns computed from the
simulated accepted yield are shown next to it for reference only.

{md_table(["sector", "r", "circuits", "clean yield 0.82 f", "N per circuit", "N per sector",
            "(ref.) simulated yield", "(ref.) N per circuit", "(ref.) N per sector"], prows)}

This is the budget for the *support* requirement.  The calibration session itself (this gate's purpose)
does not need it: yields at the percent level are already resolved by a few hundred shots per circuit,
and the r = 1 circuits alone ({sum(v['circuits'] for v in r1)} circuits) carry the 30 % comparison.

## 4. Pass criteria (prompts/07, unchanged)

1. Decoder validity: every accepted string is a valid codeword of the target sector (by construction), and
   the acceptance of random-looking strings is
   {', '.join(f"{sec} {100 * v['fraction']:.3f}%" for sec, v in sorted(A['random_acceptance'].items()))}
   (exhaustive over all {2 ** index['common']['n_logical_qubits']} strings) — criterion < 1 %.
2. Measured f within 30 % of the prediction for the r = 1 circuits ({r1[0]['cz_mean']:.0f} CZ), with
   f_measured = (measured yield − a) / ({YIELD_FACTOR} − a) = `skqd.skqd.clean_fraction_from_yield(y, a)`,
   the inverse of the full model y = {YIELD_MODEL_NAME}; the predicted f is obtained from the predicted
   (simulated) yield the same way, so the comparison is between two clean-shot fractions.
3. Ritz energies of the saturated sectors reproduce
   {', '.join(f"E_0({sec}) = {v['exact_E0']:.4f}" for sec, v in sorted(A['by_sector'].items()))} to 1e-6.
4. Every diagonal element of the per-qubit readout confusion matrix >= {DIAG_MIN}
   (simulated: {A['confusion_summary']['min_diagonal']:.4f}).

## 5. Submission

`python scripts/h0_submit.py --backend <ibm backend> --shots <N>` builds the SamplerV2 jobs from the frozen
QPY circuits with dynamical decoupling and Pauli twirling enabled and **no** error mitigation of
expectation values (SKQD needs raw bit strings), and writes one counts JSON per circuit; `--dry-run`
does the same on `AerSimulator.from_backend({D['backend']}())`.  The analysis is
`python scripts/gate_H0.py --counts <dir> --out H0`.

Escalation (prompts/07): if the measured yield at {r1[0]['cz_mean']:.0f} CZ is far below the prediction, the 2x3 budget is
not spent; the planner re-plans with k = 1, 2 only (Plan B of manual Sec. 11).
"""


if __name__ == "__main__":
    sys.exit(main())
