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
                       clean_fraction_mixture, pooled_reference_string_test,
                       reference_string_test, ritz, shot_rule, support_metrics,
                       yield_model)

from h0_backends import (calibration_diff, calibration_record,  # noqa: E402
                         fresh_calibration, frozen_qubits_and_edges,
                         is_fake, last_update_date, resolve_backend)

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


CIRCUIT_KINDS = ("coarse_step", "idle_test")   # prompts/19 C2: what --shots applies to


def load_manifests(prep_dir):
    """(circuit manifests, readout-calibration manifests), both sorted by id.

    The first list holds the kinds a session submits at `--shots`: `coarse_step` (the
    frozen set) and, since prompts/19 C2, `idle_test` (the diagnostic T1/Ramsey circuits
    of `scripts/h0_diag_circuits.py`).  `data/hardware/H0_prep` contains no `idle_test`
    manifest, so gate_H0P and the production path see exactly what they saw before."""
    cdir = os.path.join(prep_dir, "circuits")
    mans = []
    for p in sorted(glob.glob(os.path.join(cdir, "*.json"))):
        with open(p) as fh:
            mans.append(json.load(fh))
    return ([m for m in mans if m["kind"] in CIRCUIT_KINDS],
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


def label_of(model, basis_index):
    """'(j2 tuple); (n tuple)' of a basis state -- the label the memo's tables use."""
    j2, n, _iota = model.basis.labels[int(basis_index)]
    return (f"({','.join(str(int(x)) for x in j2)}); "
            f"({','.join(str(int(x)) for x in n)})")


def analyse_records(records, cal_records, model, g2, plan=None):
    """records: [(manifest, {bit tuple: count})] for the coarse-step circuits;
    cal_records: the same for the readout-calibration circuits.  Returns the full
    analysis dictionary shared by gate_H0P (simulated) and gate_H0 (device counts).

    `plan` is a shot plan of `scripts/h0_support_plan.py` (or the `shot_plan` block of
    an H0P JSON): when it is given, the per-sector support table gains the predicted
    clean count of every sector state next to the observed one.  It is an OUTPUT only —
    no criterion of this function depends on it (prompts/16 change 3)."""
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
        if man.get("f_calibration_manifest") is not None:
            # live path (prompts/15 A1): f above is recomputed on the day's calibration,
            # this is the value frozen into the manifest by h0_build_circuits.py
            out["per_circuit"][-1]["f_calibration_manifest"] = float(man["f_calibration_manifest"])
        key = (man["sector"], man["repetitions"])
        g = groups.setdefault(key, {"shots": 0, "accepted": 0, "circuits": 0, "cz": [], "f": [],
                                    "support": set(), "rejections": {}, "twoB": twoB})
        g["shots"] += shots
        g["accepted"] += n_acc
        g["circuits"] += 1
        g["cz"].append(man["cz"])
        if man.get("f_calibration_snapshot") is not None:
            g["f"].append(man["f_calibration_snapshot"])
        if man.get("f_calibration_manifest") is not None:
            g.setdefault("f_man", []).append(float(man["f_calibration_manifest"]))
        g["support"] |= set(acc)
        for kk, v in rej.items():
            g["rejections"][kk] = g["rejections"].get(kk, 0) + int(v)
        s = sectors.setdefault(man["sector"], {"twoB": twoB, "support": set(), "shots": 0,
                                               "accepted": 0, "state_counts": {}})
        s["support"] |= set(acc)
        s["shots"] += shots
        s["accepted"] += n_acc
        for st, v in acc.items():
            s["state_counts"][int(st)] = s["state_counts"].get(int(st), 0) + int(v)

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
        if g.get("f_man"):
            out["by_sector_repetition"][f"{sec} r={r}"]["f_calibration_manifest_mean"] = \
                float(np.mean(g["f_man"]))

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
        # prompts/16 change 3 (OUTPUT only, no criterion): which states the support holds,
        # which it misses, and -- when a shot plan is at hand -- what was predicted for each.
        sector_idx = [int(x) for x in ref.indices]
        pos = {ix: i for i, ix in enumerate(sector_idx)}
        pstates = ((plan or {}).get("sectors", {}).get(sec, {}) or {}).get("per_state")
        per_state = []
        for ix in sector_idx:
            row = {"basis_index": ix, "sector_position": pos[ix],
                   "label": label_of(model, ix),
                   "observed_accepted_count": int(s["state_counts"].get(ix, 0)),
                   "in_support": ix in s["support"]}
            if pstates:
                pr = pstates[pos[ix]]
                row["predicted_clean_count_all_circuits_at_f"] = pr.get("lambda_all_at_f")
                row["predicted_clean_count_r1_at_margin"] = pr.get("lambda_r1_at_margin")
                row["ground_state_weight"] = pr.get("ground_state_weight")
            per_state.append(row)
        out["by_sector"][sec]["support_states_decoded"] = sorted(int(x) for x in s["support"])
        out["by_sector"][sec]["missing_states"] = [
            {"basis_index": r["basis_index"], "sector_position": r["sector_position"],
             "label": r["label"],
             **({"predicted_clean_count_all_circuits_at_f":
                 r["predicted_clean_count_all_circuits_at_f"],
                 "predicted_clean_count_r1_at_margin": r["predicted_clean_count_r1_at_margin"]}
                if pstates else {})}
            for r in per_state if not r["in_support"]]
        out["by_sector"][sec]["per_state"] = per_state
        out["by_sector"][sec]["per_state_prediction_source"] = (
            "the shot plan of scripts/h0_support_plan.py" if pstates else None)

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


# ------------------------------------------------------------------ prompts/20: the clean statistic
# Decisions C2' / C3' / M4.4 (data/H0_replan_owner_decisions.md, signed 2026-09-30).  The
# accepted-shot yield of `analyse_records` above counts three things at once -- clean shots,
# uniformly random garbage that decodes, and strings with a few structured errors that decode --
# and gate H0_diag measured the third to be comparable with the second (0.65 % against 0.93 %),
# so the yield inversion overstated the clean fraction 15x on the device.  The functions below
# estimate the CLEAN component from the shape of the accepted histogram.  They are OUTPUTS of
# `analyse_records`' callers, never inputs to it: gate H0's criteria block is untouched unless
# it is run with `--clean-statistic mixture` (D1 of prompts/20).
def sector_distributions(records, model, g2):
    """{circuit id: ideal sector distribution} plus the codeword Hamming-distance map.

    Cached by (twoB, reference, k, dt, repetitions) -- the frozen set has 84 circuits over 24
    distinct such keys.  `skqd.krylov.ideal_sector_distribution` is the group-evolution route;
    `scripts/h0_support_plan.ideal_probabilities` takes the same object off the frozen QPY and
    the two agree to 1.8e-14 (tests/test_clean_yield.py)."""
    from skqd.krylov import ideal_sector_distribution
    codec = Codec(model.basis)
    dcache, distcache, out = {}, {}, {}
    for man, _ in records:
        key = (int(man["twoB"]), int(man["reference"]), int(man["k"]),
               round(float(man["dt"]), 15), int(man["repetitions"]))
        if key not in dcache:
            dcache[key] = ideal_sector_distribution(model, g2, int(man["twoB"]),
                                                    int(man["reference"]), int(man["k"]),
                                                    float(man["dt"]), int(man["repetitions"]))
        d = dcache[key]
        dk = (int(man["twoB"]), int(man["reference"]))
        if dk not in distcache:
            refbits = tuple(int(x) for x in codec.encode(model.basis.labels[int(man["reference"])]))
            distcache[dk] = {int(b): int(sum(x != y for x, y in
                                             zip(codec.encode(model.basis.labels[int(b)]), refbits)))
                             for b in d["sector_indices"]}
        out[man["id"]] = (d, distcache[dk])
    return out


def clean_statistics(records, model, g2, acceptance_by_sector):
    """The clean-yield statistic of decision C2' and the reference-string test of C3'.

    Returns `per_circuit`, `by_sector_repetition` (one w fitted jointly over the class's
    circuits: their ideal distributions differ, so the histograms cannot be added but the
    log-likelihoods can), `by_sector`, `reference_string_tests` (the k = 1 circuits, where the
    output is concentrated at p 0.883 / 0.889 and the count is an independent check on the
    fit) and the pooled reference test per sector.

    `near_clean_accepted` is the residual of the amended Step-4.4 model (M4.4):
    accepted - clean - N a (1 - f_clean).  It is a measurement, not a model."""
    codec = Codec(model.basis)
    dists = sector_distributions(records, model, g2)
    per_circuit, groups, sectors = {}, {}, {}
    for man, counts in records:
        d, dmap = dists[man["id"]]
        pos = {int(b): i for i, b in enumerate(d["sector_indices"])}
        acc, _rej = codec.decode_counts(counts, target_twoB=int(man["twoB"]))
        shots = int(sum(counts.values()))
        n = np.zeros(d["dim"])
        hist = np.zeros(model.basis.lat.n_links + model.basis.lat.n_sites * 2 + 1)
        for st, v in acc.items():
            n[pos[int(st)]] += int(v)
            hist[dmap[int(st)]] += int(v)
        a = float(acceptance_by_sector[man["sector"]])
        mix = clean_fraction_mixture(n, d["p"], d["dim"], shots)
        n_ref = int(round(float(n[d["reference_position"]])))
        rst = reference_string_test(n_ref, shots, float(d["p_reference"]), a, d["dim"])
        garbage = shots * a * (1.0 - mix["f_clean"])
        per_circuit[man["id"]] = {
            "id": man["id"], "sector": man["sector"], "twoB": int(man["twoB"]),
            "reference": int(man["reference"]), "k": int(man["k"]),
            "repetitions": int(man["repetitions"]), "cz": man.get("cz"),
            "shots": shots, "accepted": int(n.sum()), "dim": d["dim"],
            "p_reference": float(d["p_reference"]), "reference_hits": n_ref,
            "garbage_acceptance": a,
            "mixture": mix, "reference_string_test": rst,
            "expected_garbage_accepted": float(garbage),
            "near_clean_accepted": float(n.sum() - mix["clean_accepted"] - garbage),
            "distance_histogram": [int(x) for x in hist],
        }
        gkey = f"{man['sector']} r={int(man['repetitions'])}"
        g = groups.setdefault(gkey, {"sector": man["sector"], "repetitions": int(man["repetitions"]),
                                     "rows": [], "p": [], "shots": 0, "accepted": 0,
                                     "dim": d["dim"], "ids": [], "ref_rows": [],
                                     "distance_histogram": np.zeros_like(hist)})
        g["rows"].append(n)
        g["p"].append(d["p"])
        g["shots"] += shots
        g["accepted"] += int(n.sum())
        g["ids"].append(man["id"])
        g["ref_rows"].append((n_ref, shots, float(d["p_reference"]), a, d["dim"]))
        g["distance_histogram"] = g["distance_histogram"] + hist
        s = sectors.setdefault(man["sector"], {"ref_rows": [], "k1_ref_rows": [], "shots": 0})
        s["ref_rows"].append((n_ref, shots, float(d["p_reference"]), a, d["dim"]))
        s["shots"] += shots
        if int(man["k"]) == 1:
            s["k1_ref_rows"].append((n_ref, shots, float(d["p_reference"]), a, d["dim"]))

    bsr = {}
    for key, g in sorted(groups.items()):
        mix = clean_fraction_mixture(np.array(g["rows"]), np.array(g["p"]), g["dim"], g["shots"])
        a = float(g["ref_rows"][0][3])
        garbage = g["shots"] * a * (1.0 - mix["f_clean"])
        bsr[key] = {
            "sector": g["sector"], "repetitions": g["repetitions"], "circuits": len(g["ids"]),
            "shots": g["shots"], "accepted": g["accepted"], "dim": g["dim"],
            "mixture": mix, "reference_pooled": pooled_reference_string_test(g["ref_rows"]),
            "expected_garbage_accepted": float(garbage),
            "near_clean_accepted": float(g["accepted"] - mix["clean_accepted"] - garbage),
            "distance_histogram": [int(x) for x in g["distance_histogram"]],
        }
    bysec = {}
    for sec, s in sorted(sectors.items()):
        bysec[sec] = {"reference_pooled": pooled_reference_string_test(s["ref_rows"]),
                      "reference_pooled_k1": (pooled_reference_string_test(s["k1_ref_rows"])
                                              if s["k1_ref_rows"] else None),
                      "shots": s["shots"]}
    k1 = {cid: v["reference_string_test"] for cid, v in sorted(per_circuit.items())
          if v["k"] == 1}
    return {"per_circuit": per_circuit, "by_sector_repetition": bsr, "by_sector": bysec,
            "reference_string_tests": k1,
            "statistic": ("clean_fraction_mixture (decision C2') and reference_string_test "
                          "(decision C3'); the near-clean term is the residual of the amended "
                          "Step-4.4 model (decision M4.4)")}


# ------------------------------------------------------------------ prompts/20 B1: scheduling
SCHEDULE_SEED = 7          # seed_transpiler of the scheduling pass (P9 of the planner analysis)


def schedule_circuit(circ, backend, seed_transpiler=SCHEDULE_SEED):
    """`transpile(..., optimization_level=0, scheduling_method='asap')`: the idle windows of
    the circuit become explicit `Delay` instructions on the target's own durations, which is
    what `AerSimulator.from_backend` charges with thermal relaxation.

    The unscheduled path of the dry run had no delays at all, which is why it reported the
    wrong hypothesis as confirmed (decision H0P-Y').  Asserts that no NON-delay operation
    count moved: scheduling must add time, never gates."""
    from qiskit import transpile
    before = {k: v for k, v in circ.count_ops().items() if k != "delay"}
    sched = transpile(circ, backend=backend, optimization_level=0, scheduling_method="asap",
                      seed_transpiler=seed_transpiler)
    after = {k: v for k, v in sched.count_ops().items() if k != "delay"}
    if before != after:
        raise SystemExit(f"scheduling changed the operations of the circuit: before {before}, "
                         f"after {after} (prompts/20 escalation B1)")
    dt = float(backend.dt) if getattr(backend, "dt", None) else None
    dur_dt = sum(int(inst.operation.duration) for inst in sched.data
                 if inst.operation.name == "delay")
    info = {"n_delays": int(sched.count_ops().get("delay", 0)),
            "n_cz": int(after.get("cz", 0)),
            "delay_dt_total": int(dur_dt),
            "ops_non_delay": {k: int(v) for k, v in sorted(after.items())},
            "dt_s": dt, "seed_transpiler": int(seed_transpiler)}
    try:
        from h0_qpu_time import circuit_duration_s
        t = backend.target
        info["scheduled_duration_s"] = float(circuit_duration_s(sched, t.durations(), t))
        info["unscheduled_duration_s"] = float(circuit_duration_s(circ, t.durations(), t))
        info["duration_agreement_dt"] = (
            None if dt is None else
            abs(info["scheduled_duration_s"] - info["unscheduled_duration_s"]) / dt)
    except Exception as exc:                        # pragma: no cover - reported, never silent
        info["duration_check_error"] = str(exc)
    return sched, info


# ------------------------------------------------------------------ prompts/20 B2: the T2 override
def load_t2_override(path):
    """A `{source, per_qubit: {physical: {T2_s, provenance}}}` file, or None."""
    if not path:
        return None, None
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(p) as fh:
        blob = fh.read()
    ov = json.loads(blob)
    if "per_qubit" not in ov:
        raise SystemExit(f"{path} is not a T2 override file of scripts/h0_t2_override.py "
                         f"(no 'per_qubit' block)")
    import hashlib
    return ov, hashlib.sha256(blob.encode()).hexdigest()


def apply_t2_override(backend, override):
    """Replace `target.qubit_properties` by a NEW list carrying the override T2 per qubit.

    prompts/17 PC 3: `Target.qubit_properties` must be ASSIGNED as a list -- mutating the
    objects in place does not reach the target, and therefore does not reach
    `AerSimulator.from_backend`'s relaxation pass.  T1 is left as the record has it; a T2
    above 2 T1 is unphysical for the relaxation channel and is clipped, with the clip
    recorded rather than silently applied."""
    from qiskit.providers.backend import QubitProperties
    target = backend.target
    qp = list(target.qubit_properties)
    table, clipped = [], []
    for q, v in sorted(override["per_qubit"].items(), key=lambda kv: int(kv[0])):
        qi = int(q)
        if qi >= len(qp):
            raise SystemExit(f"the T2 override names qubit {qi} but the target has {len(qp)}")
        old = qp[qi]
        t1 = None if old is None else old.t1
        t2_new = float(v["T2_s"])
        clip = False
        if t1 is not None and t2_new > 2.0 * t1:
            clipped.append({"qubit": qi, "T2_requested_s": t2_new, "T2_used_s": 2.0 * t1,
                            "T1_s": t1, "reason": "T2 <= 2 T1"})
            t2_new, clip = 2.0 * t1, True
        qp[qi] = QubitProperties(t1=t1, t2=t2_new,
                                 frequency=None if old is None else old.frequency)
        table.append({"qubit": qi, "T1_s": t1,
                      "T2_original_s": None if old is None else old.t2,
                      "T2_override_s": t2_new,
                      "provenance": v.get("provenance"), "clipped_to_2T1": clip})
    target.qubit_properties = qp                # ASSIGNED, never mutated in place
    check = {int(r["qubit"]): target.qubit_properties[int(r["qubit"])].t2 for r in table}
    for r in table:
        if abs(check[int(r["qubit"])] - r["T2_override_s"]) > 1e-18:
            raise SystemExit(f"the T2 override did not reach the target for qubit {r['qubit']} "
                             f"(prompts/20 escalation B2)")
    return {"source": override.get("source"), "n_qubits": len(table), "per_qubit": table,
            "clipped": clipped,
            "note": ("target.qubit_properties assigned as a new list (prompts/17 PC 3); T1 "
                     "unchanged; AerSimulator.from_backend reads these values for the thermal "
                     "relaxation of every delay")}


# ------------------------------------------------------------------ prompts/20 B3: the PTA bound
def pta_bounds(circuits, mans, record, t2_s=None):
    """`skqd.idle`'s analytic clean-f bound per circuit on `record` at the T2 actually used.

    The bound is parameter-free and charges every relaxation error as fatal, so it sits BELOW
    the scheduled simulation by an understood factor (11.8x on the FakeFez snapshot, of which
    22.4 % of the phase budget provably cannot matter).  Decision H0P-Y' requires the ordering
    PTA <= Aer-scheduled <= Aer-unscheduled to be tested rather than a number asserted."""
    import h0_idle_model as im
    out = {}
    for m in mans:
        qc = circuits[m["id"]]
        sch = im.schedule(qc, record)
        _per_q, tot = im.budgets(sch, record, t2_s)
        with np.errstate(divide="ignore", invalid="ignore"):
            f_gates, f_gates_only, ro, n_cz, n_meas = im.f_on_record(qc, record)
        from skqd import idle
        out[m["id"]] = {
            "f_gates": float(f_gates), "f_pta": float(idle.f_idle_aware(f_gates, tot)),
            "S_T1": tot["S_T1"], "S_T2": tot["S_T2"], "idle_s": tot["idle_s"],
            "T_total_s": sch["T_total_s"], "n_cz": int(n_cz), "n_measure": int(n_meas),
        }
    return out


class LazySchedule(dict):
    """`circuits[id]` returns the ASAP-scheduled circuit, transpiled on first access.

    Lazy so that a run restricted with `--only-ids` does not pay for scheduling the other
    83 circuits of the frozen set; the schedule info of every circuit that was actually
    scheduled lands in `self.info` and from there in the JSON."""

    def __init__(self, base, backend):
        super().__init__()
        self.base = base
        self.backend = backend
        self.info = {}
        self.seconds = 0.0

    def __getitem__(self, key):
        if key not in self:
            t = time.time()
            sched, info = schedule_circuit(self.base[key], self.backend)
            self.seconds += time.time() - t
            self.info[key] = info
            super().__setitem__(key, sched)
            print(f"    scheduled {key}: {info['n_delays']} delays, "
                  f"{info['n_cz']} cz, {info.get('scheduled_duration_s', float('nan')) * 1e6:.2f} us "
                  f"({time.time() - t:.1f} s)", flush=True)
        return super().__getitem__(key)


def yield_bracket(pta_by_circuit, clean_stats, mans):
    """The H0P-Y' sandwich per (sector, repetition): PTA bound <= scheduled Aer clean f.

    The unscheduled end is not recomputed here -- it is the clean f of a `--schedule none`
    run of the same command, which the report names -- so what this function checks is the
    lower edge of the ordering, the one a single invocation can see."""
    out = {}
    by_class = {}
    for m in mans:
        by_class.setdefault(f"{m['sector']} r={int(m['repetitions'])}", []).append(m["id"])
    for key, ids in sorted(by_class.items()):
        ids = [i for i in ids if i in pta_by_circuit]
        if not ids or key not in clean_stats["by_sector_repetition"]:
            continue
        mix = clean_stats["by_sector_repetition"][key]["mixture"]
        f_pta = float(np.mean([pta_by_circuit[i]["f_pta"] for i in ids]))
        f_sim = float(mix["f_clean"])
        out[key] = {
            "f_pta_bound_mean": f_pta,
            "f_pta_bound_min": float(np.min([pta_by_circuit[i]["f_pta"] for i in ids])),
            "f_pta_bound_max": float(np.max([pta_by_circuit[i]["f_pta"] for i in ids])),
            "f_gates_mean": float(np.mean([pta_by_circuit[i]["f_gates"] for i in ids])),
            "f_clean_scheduled_simulation": f_sim,
            "f_clean_scheduled_simulation_68": mix["f_clean_68"],
            "ratio_simulation_over_bound": (f_sim / f_pta) if f_pta > 0 else None,
            "bound_below_simulation": bool(f_pta <= f_sim),
            "ordering": "PTA bound <= Aer-scheduled clean f (<= Aer-unscheduled clean f)",
        }
    return out


def plan_calibration_diff(support_plan, live_record, caldir, bname):
    """' -- 30 leaves changed (measure_error), ratios 0.37..2.66' if the record the plan was
    built from is still on disk, '' otherwise (prompts/17 F3(i): a refusal says WHAT moved).

    The plan stores the live target, not a file, so the record is looked up by the stamp in
    the calibration directory gate_H0P itself writes to."""
    cb = support_plan.get("calibration") or {}
    cands = [cb.get("fingerprint_source"), cb.get("path")]
    if cb.get("stamp"):
        cands.append(os.path.join(caldir or "", f"calibration_{cb['stamp']}.json"))
    for c in cands:
        if not c or not isinstance(c, str):
            continue
        p = c if os.path.isabs(c) else os.path.join(ROOT, c)
        if not os.path.isfile(p):
            continue
        try:
            with open(p) as fh:
                old = json.load(fh)
            d = calibration_diff(old, live_record)
        except Exception:
            continue
        if d["n_leaves"] == 0:
            continue
        return (f" -- {d['n_leaves']} leaf/leaves changed against {os.path.relpath(p, ROOT)} "
                f"({', '.join(d['families'])}; ratios "
                f"{d['min_ratio'] if d['min_ratio'] is None else round(d['min_ratio'], 4)} .. "
                f"{d['max_ratio'] if d['max_ratio'] is None else round(d['max_ratio'], 4)})")
    return ""


# ------------------------------------------------------------------ sampling cache (prompts/16 F2)
# prompts/20 B1/B2: the two keys the cache gained.  A cache file written before prompts/20
# carries neither key and is, by construction, the unscheduled run with the target's own T2.
CACHE_KEY_DEFAULTS = {"schedule": "none", "t2_override_sha": None}


def cache_path(cdir, sector, r):
    return os.path.join(cdir, f"{sector}_r{r}.json")


def cache_stamp(rec_expect, rec_found, path):
    """Every field that would make a cached class a different experiment is compared;
    a mismatch is a SystemExit naming it -- a stale cache is never silently reused.

    prompts/17 D11: the key is the calibration FINGERPRINT of the frozen patch, not its
    timestamp.  `calibration_last_update_date`, `shot_plan_stamp` and `shots_plan_file`
    stay in the files as information (a cached class is a seeded Aer run of fixed
    circuits at fixed shots against a fixed noise model, and the noise model is the
    fingerprinted content); a file written before the migration of prompts/17 A''6 has no
    fingerprint and is refused rather than trusted."""
    if "calibration_fingerprint" not in rec_found:
        raise SystemExit(
            f"{os.path.basename(path)} carries no `calibration_fingerprint`: it predates "
            f"prompts/17 D11.  Add it with the A''6 migration (snippet 5 of prompts/17) if it "
            f"belongs to the calibration content you are running on, or re-sample the class "
            f"with --refresh-cache.")
    for key in ("backend", "seed", "calibration_fingerprint", "sector", "repetition",
                "schedule", "t2_override_sha"):
        # prompts/20 B1: `schedule` and `t2_override_sha` join the key because a scheduled run
        # and a run at an overridden T2 are different experiments on the same circuits.  A file
        # written before prompts/20 carries neither and is the unscheduled, un-overridden
        # experiment -- the default below, so the 14 committed cache files stay valid.
        # the default is applied to BOTH sides: absent on both sides means "the unscheduled
        # run with the target's own T2", which is what a pre-prompts/20 file and a
        # pre-prompts/20 expectation both describe
        got = rec_found.get(key, CACHE_KEY_DEFAULTS.get(key))
        want = rec_expect.get(key, CACHE_KEY_DEFAULTS.get(key))
        if str(got) != str(want):
            raise SystemExit(
                f"{os.path.basename(path)}: cached {key} is {got!r}, this run needs "
                f"{want!r}.  The cache is not reused silently: delete the file or "
                f"re-sample the class with --refresh-cache.")
    for cid, sh in rec_expect["shots_by_circuit"].items():
        got = rec_found.get("shots_by_circuit", {}).get(cid)
        if got is not None and int(got) != int(sh):
            raise SystemExit(
                f"{os.path.basename(path)}: circuit {cid} was sampled with {got} shots, this run "
                f"needs {sh}.  Re-sample the class with --refresh-cache.")


def load_cache(path, expect):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        rec = json.load(fh)
    cache_stamp(expect, rec, path)
    return rec


def save_cache(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(tmp, path)


def run_by_shots(sim, circuits, mans, shots_of):
    """One sim.run per distinct shot count; returns {circuit id: qiskit counts dict}."""
    by_shots = {}
    for m in mans:
        by_shots.setdefault(int(shots_of[m["id"]]), []).append(m)
    out = {}
    for sh in sorted(by_shots):
        batch = by_shots[sh]
        cts = sim.run([circuits[m["id"]] for m in batch], shots=sh).result().get_counts()
        if isinstance(cts, dict):
            cts = [cts]
        for m, cc in zip(batch, cts):
            out[m["id"]] = {str(k): int(v) for k, v in cc.items()}
        print(f"    {len(batch)} circuit(s) x {sh} shots", flush=True)
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
    ap.add_argument("--shots-plan", default=None, metavar="JSON",
                    help="a per-circuit shot plan written by scripts/h0_support_plan.py (rule D3' "
                         "of prompts/16); mutually exclusive with --shots-by-rep")
    ap.add_argument("--sample-cache", default=None, metavar="DIR",
                    help="directory of per-class sampling caches (<sector>_r<r>.json and "
                         "calibration_circuits.json): a class that is already on disk with the same "
                         "backend, seed, calibration date and shots is loaded instead of re-sampled")
    ap.add_argument("--sectors", nargs="*", default=None, help="restrict the sampling to these sectors")
    ap.add_argument("--reps", nargs="*", type=int, default=None,
                    help="restrict the sampling to these repetitions")
    ap.add_argument("--only-ids", nargs="*", default=None,
                    help="restrict the sampling to these circuit ids (splits a class over several "
                         "invocations; the 30-minute rule)")
    ap.add_argument("--sample-only", action="store_true",
                    help="exit 0 once the selected classes are in the cache (no analysis)")
    ap.add_argument("--refresh-cache", action="store_true",
                    help="re-sample the selected classes even if they are cached")
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
    ap.add_argument("--no-prereg", action="store_true",
                    help="do not write the preregistration report (reproducibility re-runs)")
    ap.add_argument("--backend", default=None,
                    help="FakeFez / FakeTorino (default: the snapshot named in index.json) or a LIVE "
                         "IBM backend: the day's calibration is then the reference of the prediction "
                         "(prompts/15 D1) and is recorded in --calibration-dir")
    ap.add_argument("--schedule", default="none", choices=("none", "asap"),
                    help="prompts/20 B1: with 'asap' every circuit is passed through "
                         "transpile(optimization_level=0, scheduling_method='asap') before "
                         "sim.run, so its idle windows become explicit Delay instructions and "
                         "Aer charges them with thermal relaxation.  The default 'none' is the "
                         "path every committed H0P output was produced with; a scheduled run "
                         "is a different experiment and gets its own sampling cache.")
    ap.add_argument("--t2-override", default=None, metavar="JSON",
                    help="prompts/20 B2: a {source, per_qubit: {physical: {T2_s, provenance}}} "
                         "file (scripts/h0_t2_override.py) whose T2 values replace the "
                         "target's before the Aer noise model is built.  T1 is untouched.")
    ap.add_argument("--yield-criterion", default="auto", choices=("auto", "ratio", "bracket"),
                    help="decision H0P-Y': 'bracket' judges the yield by the ordering "
                         "PTA bound <= scheduled-Aer clean f instead of the [1/3, 3] band of "
                         "the simulated-over-model ratio.  'auto' (the default) uses the "
                         "bracket when --schedule asap makes it computable and the ratio "
                         "otherwise, so every unscheduled output keeps the criteria it had.")
    ap.add_argument("--calibration-dir", default=None,
                    help="where calibration_<stamp>.json goes (default data/hardware/H0_<backend>)")
    ap.add_argument("--out", default="H0P")
    args = ap.parse_args()
    t0 = time.time()
    prep = os.path.join(ROOT, args.prep)
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    if not mans:
        raise SystemExit(f"no frozen circuits in {prep}: run scripts/h0_build_circuits.py first")

    from qiskit_aer import AerSimulator

    snapshot_name = index["common"]["backend"]
    bname = args.backend or snapshot_name
    live = not is_fake(bname)
    backend = resolve_backend(bname)
    # the simulator is built AFTER the live calibration record below: `fresh_calibration`
    # refreshes the backend object, and the noise model of the prediction must come from
    # the same target content the record fingerprints (prompts/17 D9).
    sim = None
    g2 = index["common"]["g2"]
    M = Model(int(index["common"]["lattice"].split("x")[1]))
    n = index["common"]["n_logical_qubits"]

    R = GateResult(args.out, f"H0 preparation on the {bname} calibration "
                             f"{'of the session day' if live else 'snapshot'}: frozen circuit set, "
                             f"predicted yield curve by repetition, readout confusion, Ritz consistency")

    # ------------------------------------------------------- pilot timing -> shots
    circuits = {m["id"]: load_circuit(prep, m) for m in mans}
    reps = sorted({m["repetitions"] for m in mans})

    # ------------------------------------------------------- the day's calibration (live only)
    # prompts/15 D1: the circuits stay frozen, the PREDICTION is recomputed on the calibration of
    # the session day -- f per circuit from the live target, the Aer device model from the live
    # backend, and the per-qubit readout errors that gate_H0.py --calibration will reference.
    calibration, cal_path, f_live = None, None, {}
    if live:
        # imported here, not at module level: gate_S2D imports random_acceptance from this module
        from gate_S2D import analyse_on_backend      # the f of gate S2D, same definition
        qubits, edges = frozen_qubits_and_edges(prep)
        # prompts/17 F1: the record comes from a target refreshed in THIS invocation
        # (IBMBackend.properties() is cached per object, so a long-lived object can report
        # an hour-old calibration) and the Aer noise model below is built from that target.
        calibration = fresh_calibration(backend, qubits, edges)
        caldir = os.path.join(ROOT, args.calibration_dir or
                              os.path.join("data", "hardware", f"H0_{bname}"))
        os.makedirs(caldir, exist_ok=True)
        cal_path = os.path.join(caldir, f"calibration_{calibration['stamp']}.json")
        with open(cal_path, "w") as fh:
            json.dump(calibration, fh, indent=1)
        print(f"live calibration of {bname} ({calibration['last_update_date']}): "
              f"{calibration['n_qubits_frozen_set']} qubits, {calibration['n_edges_frozen_set']} edges "
              f"-> {os.path.relpath(cal_path, ROOT)}", flush=True)
        if calibration["missing_errors"]:
            raise SystemExit(
                f"{len(calibration['missing_errors'])} target entries of the frozen set have no error "
                f"on {bname}: {calibration['missing_errors'][:5]} (full list in "
                f"{os.path.relpath(cal_path, ROOT)}).  prompts/15 A1/B3: a None error is a hard stop, "
                f"not a value to default -- the clean-shot fraction f cannot be predicted today.")
        new_mans = []
        for m in mans:
            a = analyse_on_backend(circuits[m["id"]], backend)
            mm = dict(m)
            mm["f_calibration_manifest"] = m.get("f_calibration_snapshot")
            mm["f_calibration_snapshot"] = a["f"]
            new_mans.append(mm)
            f_live[m["id"]] = {"cz": a["cz"], "cz_manifest": m["cz"],
                               "f_live": a["f"], "f_manifest": m.get("f_calibration_snapshot"),
                               "mean_edge_error": a["mean_edge_error"],
                               "mean_readout_error": a["mean_readout_error"]}
        mans = new_mans
        bad_cz = [i for i, v in f_live.items() if v["cz"] != v["cz_manifest"]]
        if bad_cz:
            raise SystemExit(f"the loaded QPY of {len(bad_cz)} circuits does not carry the CZ count of "
                             f"its manifest (e.g. {bad_cz[:3]}): the frozen set is not intact")
        print(f"recomputed f on the live target for {len(f_live)} circuits: mean live "
              f"{np.mean([v['f_live'] for v in f_live.values()]):.4f} vs manifest "
              f"{np.mean([v['f_manifest'] for v in f_live.values()]):.4f}", flush=True)

    # ------------------------------------------------------- prompts/20 D11 + B2
    # The calibration RECORD and its fingerprint are read from the target as the device
    # reported it, BEFORE any T2 override: the record on disk keeps the device's own T2 and
    # the override is recorded next to it as a separate, named table.  The cache key then
    # carries both the fingerprint and the sha256 of the override file, so a run at the
    # measured T2* is never confused with a run at the record's Hahn-echo T2.
    cal_date = calibration["last_update_date"] if live else "snapshot"
    if live:
        cal_fingerprint = calibration["fingerprint"]
        cal_fingerprint_source = os.path.relpath(cal_path, ROOT)
    else:
        snap_qubits, snap_edges = frozen_qubits_and_edges(prep)
        snapshot_rec = calibration_record(backend, snap_qubits, snap_edges)
        cal_fingerprint = snapshot_rec["fingerprint"]
        cal_fingerprint_source = f"{bname} snapshot record"
    t2_override, t2_override_sha = load_t2_override(args.t2_override)
    t2_table = None
    if t2_override is not None:
        t2_table = apply_t2_override(backend, t2_override)
        t2_table["file"] = args.t2_override
        t2_table["sha256"] = t2_override_sha
        print(f"T2 override {args.t2_override} ({t2_override_sha[:16]}): "
              f"{t2_table['n_qubits']} qubits, {len(t2_table['clipped'])} clipped to 2 T1",
              flush=True)
        if live:
            calibration["t2_override"] = t2_table
            with open(cal_path, "w") as fh:
                json.dump(calibration, fh, indent=1)
    # the simulator is built from the target as it stands now: the override above is inside
    # the noise model, the fingerprint recorded above is not a function of it
    sim = AerSimulator.from_backend(backend, seed_simulator=args.seed)
    if args.schedule == "asap":
        circuits = LazySchedule(circuits, backend)
        print(f"--schedule asap: circuits are transpiled with optimization_level=0, "
              f"scheduling_method='asap', seed_transpiler={SCHEDULE_SEED} on first use",
              flush=True)

    # ------------------------------------------------------- pinned shots (prompts/16 F2)
    # Either the per-circuit shot plan of rule D3' (scripts/h0_support_plan.py) or the
    # --shots-by-rep of prompts/15.  Both pin the shots BEFORE the pilot, which is what makes
    # a sampling cache meaningful: the cached counts belong to a known shot count.
    support_plan, plan_stamp, shots_of, shots_by_rep_pinned = None, None, None, None
    plan_fingerprint = None
    if args.shots_plan and args.shots_by_rep:
        raise SystemExit("--shots-plan and --shots-by-rep are mutually exclusive")
    if args.shots_by_rep:
        shots_by_rep_pinned = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.shots_by_rep}
        # prompts/20 B4: a PARTIAL map is allowed so that a restricted invocation
        # (--only-ids / --reps) does not have to invent shot counts for the repetitions it
        # never samples.  A class with an unpinned repetition is simply not cacheable, and the
        # analysis (which needs every class) refuses as it always did.
        shots_of = {m["id"]: int(shots_by_rep_pinned[m["repetitions"]]) for m in mans
                    if m["repetitions"] in shots_by_rep_pinned}
        unpinned_reps = sorted({m["repetitions"] for m in mans} - set(shots_by_rep_pinned))
        if unpinned_reps:
            print(f"--shots-by-rep pins {sorted(shots_by_rep_pinned)}; repetition(s) "
                  f"{unpinned_reps} are unpinned and cannot be sampled or cached in this "
                  f"invocation", flush=True)
    if args.shots_plan:
        pp = (args.shots_plan if os.path.isabs(args.shots_plan)
              else os.path.join(ROOT, args.shots_plan))
        with open(pp) as fh:
            support_plan = json.load(fh)
        if "shots_by_circuit" not in support_plan:
            raise SystemExit(f"{args.shots_plan} is not a shot plan of scripts/h0_support_plan.py")
        shots_of = {k: int(v) for k, v in support_plan["shots_by_circuit"].items()}
        missing = [m["id"] for m in mans if m["id"] not in shots_of]
        if missing:
            raise SystemExit(f"the shot plan {args.shots_plan} carries no shots for {len(missing)} "
                             f"frozen circuit(s) (e.g. {missing[:3]})")
        plan_stamp = (support_plan.get("calibration") or {}).get("stamp")
        plan_fingerprint = (support_plan.get("calibration") or {}).get("fingerprint")
        if live:
            # prompts/17 F3(i): the plan must have been sized on the calibration CONTENT of
            # the record just written, not merely on a record carrying the same timestamp.
            if plan_fingerprint is None:
                raise SystemExit(
                    f"{args.shots_plan} carries no `calibration.fingerprint`: it was written "
                    f"before prompts/17 F2.  Re-run h0_support_plan.py --backend {bname}.")
            if plan_fingerprint != calibration["fingerprint"]:
                diff = plan_calibration_diff(support_plan, calibration, caldir, bname)
                raise SystemExit(
                    f"the shot plan was built on the calibration fingerprint "
                    f"{plan_fingerprint[:16]} (stamp {plan_stamp}, {(support_plan['calibration'] or {}).get('last_update_date')}) "
                    f"and the live {bname} target reports {calibration['fingerprint'][:16]} "
                    f"({calibration['last_update_date']}){diff}: re-run h0_support_plan.py "
                    f"--backend {bname} (prompts/17 D9/D10).")
        print(f"shot plan {args.shots_plan} (calibration stamp {plan_stamp}, fingerprint "
              f"{(plan_fingerprint or 'n/a')[:16]}): "
              + ", ".join(f"{sec} N4 {v['N4']}" for sec, v in support_plan["sectors"].items()),
              flush=True)
    # prompts/17 D11: the cache is keyed by the calibration CONTENT (computed above, before
    # the T2 override).  On a fake backend that content is the snapshot's own record, which
    # is constant per qiskit-ibm-runtime version.

    # ------------------------------------------------------- which classes this invocation samples
    classes = sorted({(m["sector"], m["repetitions"]) for m in mans})
    use_cache = args.sample_cache is not None
    restricted = bool(args.sectors or args.reps or args.only_ids)
    if (restricted or args.sample_only or args.refresh_cache) and not use_cache:
        raise SystemExit("--sectors / --reps / --only-ids / --sample-only / --refresh-cache need "
                         "--sample-cache <dir>")
    if use_cache and shots_of is None:
        raise SystemExit("--sample-cache needs pinned shots: give --shots-plan or --shots-by-rep")
    known_sectors = {sec for sec, _ in classes}
    if args.sectors and set(args.sectors) - known_sectors:
        raise SystemExit(f"--sectors: no such sector(s) {sorted(set(args.sectors) - known_sectors)} "
                         f"(known: {sorted(known_sectors)})")
    sel_sectors = set(args.sectors) if args.sectors else known_sectors
    sel_reps = set(args.reps) if args.reps else {r for _, r in classes}
    selected = [c for c in classes if c[0] in sel_sectors and c[1] in sel_reps]
    cal_selected = not restricted
    only_ids = set(args.only_ids) if args.only_ids else None
    if only_ids and only_ids - {m["id"] for m in mans}:
        raise SystemExit(f"--only-ids: no such circuit(s) {sorted(only_ids - {m['id'] for m in mans})}")
    cdir = None
    if use_cache:
        cdir = args.sample_cache if os.path.isabs(args.sample_cache) else \
            os.path.join(ROOT, args.sample_cache)
        os.makedirs(cdir, exist_ok=True)

    def expect(sector, repetition, ids):
        return {"backend": bname, "seed": int(args.seed), "sector": sector,
                "repetition": int(repetition),
                "calibration_fingerprint": cal_fingerprint,
                "calibration_fingerprint_source": cal_fingerprint_source,
                "calibration_last_update_date": cal_date,
                "schedule": args.schedule, "t2_override_sha": t2_override_sha,
                "t2_override_file": args.t2_override,
                "shot_plan_stamp": plan_stamp, "shots_plan_file": args.shots_plan,
                "shots_by_circuit": {i: int(shots_of[i]) for i in ids}}

    by_class = {c: [m for m in mans if (m["sector"], m["repetitions"]) == c] for c in classes}
    cached, cal_cached = {}, None
    if use_cache:
        for c in classes:
            path = cache_path(cdir, c[0], c[1])
            ids = [m["id"] for m in by_class[c]]
            if any(i not in shots_of for i in ids):
                if c in selected:
                    raise SystemExit(
                        f"class {c[0]} r={c[1]} is selected but its shots are not pinned: give "
                        f"--shots-by-rep {c[1]}:<shots> (or a --shots-plan covering it)")
                cached[c] = None                # unpinned and unselected: not this invocation's
                continue
            if args.refresh_cache and c in selected:
                cached[c] = None
                continue
            cached[c] = load_cache(path, expect(c[0], c[1], ids))
        calpath = os.path.join(cdir, "calibration_circuits.json")
        cal_exp = {"backend": bname, "seed": int(args.seed), "sector": "calibration",
                   "repetition": 0, "calibration_fingerprint": cal_fingerprint,
                   "calibration_fingerprint_source": cal_fingerprint_source,
                   "calibration_last_update_date": cal_date,
                   "schedule": args.schedule, "t2_override_sha": t2_override_sha,
                   "t2_override_file": args.t2_override,
                   "shot_plan_stamp": plan_stamp, "shots_plan_file": args.shots_plan,
                   "shots_by_circuit": {m["id"]: int(args.cal_shots) for m in cals}}
        cal_cached = None if (args.refresh_cache and cal_selected) else load_cache(calpath, cal_exp)

    def class_complete(c):
        rec = cached.get(c)
        return rec is not None and all(m["id"] in rec["counts"] for m in by_class[c])

    to_sample = [c for c in selected if not class_complete(c)] if use_cache else classes
    cal_to_sample = (cal_selected and
                     (cal_cached is None or
                      not all(m["id"] in cal_cached["counts"] for m in cals))) if use_cache else True

    # ------------------------------------------------------- two-point pilot
    # one simulator call has a fixed setup cost (circuit load, noise binding) plus a cost per
    # circuit-shot; both are measured so that the budget is not spent on setup
    t_shot, setup = {}, {}
    pilot_reps = reps if shots_of is None else sorted({r for _, r in to_sample})
    for r in pilot_reps:
        # prompts/20 B1: with --only-ids the pilot times the circuits this invocation will
        # actually run, so a scheduled run does not transpile three circuits it never samples
        ms = [m for m in mans if m["repetitions"] == r
              and (only_ids is None or m["id"] in only_ids)][:args.pilot_circuits]
        if not ms:
            continue
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
    setup_total = sum(setup.get(r, 0.0) * n_by_rep[r] / max(args.pilot_circuits, 1) for r in reps)
    available = max(budget_s - setup_total, 60.0)
    if shots_by_rep_pinned:
        shots_by_rep = shots_by_rep_pinned
    elif shots_of is not None:                  # the plan pins the shots circuit by circuit
        shots_by_rep = {}
        for r in reps:
            vals = sorted({shots_of[m["id"]] for m in mans if m["repetitions"] == r})
            shots_by_rep[r] = vals[0] if len(vals) == 1 else vals
    elif args.shot_allocation == "equal-shots":
        tot = sum(n_by_rep[r] * t_shot[r] for r in reps)
        shots_by_rep = {r: int(min(args.max_shots, max(args.min_shots, available / tot))) for r in reps}
    else:                       # equal wall clock per repetition class
        per_class = available / len(reps)
        shots_by_rep = {r: int(min(args.max_shots, max(args.min_shots, per_class / (n_by_rep[r] * t_shot[r]))))
                        for r in reps}
    if shots_of is None:
        shots_of = {m["id"]: int(shots_by_rep[m["repetitions"]]) for m in mans}
    predicted_s = sum(shots_of.get(m["id"], 0) * t_shot.get(m["repetitions"], 0.0)
                      for m in mans) + setup_total
    per_shot_total = sum(t_shot.get(m["repetitions"], 0.0) for m in mans)
    print(f"{len(mans)} circuits, {per_shot_total:.2f} s per shot over the whole set -> shots per circuit "
          f"{shots_by_rep} ({args.shot_allocation}, predicted {predicted_s / 60:.1f} min of a "
          f"{args.budget_minutes} min budget)", flush=True)

    # ------------------------------------------------------- sampling
    ts = time.time()
    records, class_log = [], {}
    if not use_cache:
        for r in reps:                  # one simulator call per repetition class (amortised overhead)
            ms = [m for m in mans if m["repetitions"] == r]
            cts = sim.run([circuits[m["id"]] for m in ms], shots=shots_by_rep[r]).result().get_counts()
            if isinstance(cts, dict):
                cts = [cts]
            for m, cc in zip(ms, cts):
                records.append((m, {qiskit_key_to_bits(kk): v for kk, v in cc.items()}))
            print(f"  r={r}: {len(ms)} circuits x {shots_by_rep[r]} shots "
                  f"({time.time() - t0:.0f} s)", flush=True)
        t_sample = time.time() - ts
        tc = time.time()
        cal_records = []
        cal_base = {m["id"]: load_circuit(prep, m) for m in cals}
        cal_view = LazySchedule(cal_base, backend) if args.schedule == "asap" else cal_base
        cal_counts = sim.run([cal_view[m["id"]] for m in cals],
                             shots=args.cal_shots).result().get_counts()
        if isinstance(cal_counts, dict):
            cal_counts = [cal_counts]
        for m, cc in zip(cals, cal_counts):
            cal_records.append((m, {qiskit_key_to_bits(kk): v for kk, v in cc.items()}))
        t_cal = time.time() - tc
    else:
        for c in classes:
            sec, r = c
            path = cache_path(cdir, sec, r)
            rec = cached.get(c)
            if c in to_sample:
                ms = [m for m in by_class[c] if (only_ids is None or m["id"] in only_ids)]
                if rec is not None:
                    ms = [m for m in ms if m["id"] not in rec["counts"]]
                if ms:
                    tstart = time.time()
                    print(f"  sampling {sec} r={r}: {len(ms)} circuit(s) "
                          f"({time.time() - t0:.0f} s elapsed)", flush=True)
                    got = run_by_shots(sim, circuits, ms, shots_of)
                    if rec is None:
                        rec = expect(sec, r, [m["id"] for m in by_class[c]])
                        rec.update({"counts": {}, "sampled": [], "seconds": 0.0,
                                    "simulator": f"AerSimulator.from_backend({bname}, "
                                                 f"seed_simulator={args.seed})"})
                        rec["shots_by_circuit"] = {}
                    rec["counts"].update(got)
                    rec["shots_by_circuit"].update({m["id"]: int(shots_of[m["id"]]) for m in ms})
                    rec["seconds"] = float(rec.get("seconds", 0.0) + time.time() - tstart)
                    rec["sampled"] = list(rec.get("sampled", [])) + [
                        {"when": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "circuits": [m["id"] for m in ms],
                         "seconds": time.time() - tstart,
                         "seconds_per_circuit_shot": t_shot.get(r)}]
                    save_cache(path, rec)
                    cached[c] = rec
            if rec is None or not all(m["id"] in rec["counts"] for m in by_class[c]):
                have = 0 if rec is None else len([m for m in by_class[c] if m["id"] in rec["counts"]])
                class_log[f"{sec} r={r}"] = {"complete": False, "circuits_cached": have,
                                             "circuits": len(by_class[c])}
                continue
            class_log[f"{sec} r={r}"] = {"complete": True, "circuits": len(by_class[c]),
                                         "seconds": rec.get("seconds"), "file": os.path.basename(path),
                                         "sampled_now": c in to_sample}
            for m in by_class[c]:
                cc = rec["counts"][m["id"]]
                records.append((m, {qiskit_key_to_bits(kk): int(v) for kk, v in cc.items()}))
        t_sample = time.time() - ts
        tc = time.time()
        cal_records = []
        if cal_to_sample:
            print(f"  sampling the {len(cals)} readout-calibration circuits x {args.cal_shots} shots "
                  f"({time.time() - t0:.0f} s elapsed)", flush=True)
            cal_circuits = {m["id"]: load_circuit(prep, m) for m in cals}
            if args.schedule == "asap":
                cal_circuits = LazySchedule(cal_circuits, backend)
            got = run_by_shots(sim, cal_circuits, cals, {m["id"]: args.cal_shots for m in cals})
            cal_cached = {"backend": bname, "seed": int(args.seed), "sector": "calibration",
                          "repetition": 0, "calibration_fingerprint": cal_fingerprint,
                          "calibration_fingerprint_source": cal_fingerprint_source,
                          "calibration_last_update_date": cal_date,
                          "schedule": args.schedule, "t2_override_sha": t2_override_sha,
                          "t2_override_file": args.t2_override,
                          "shot_plan_stamp": plan_stamp, "shots_plan_file": args.shots_plan,
                          "shots_by_circuit": {m["id"]: int(args.cal_shots) for m in cals},
                          "counts": got, "seconds": time.time() - tc,
                          "sampled": [{"when": time.strftime("%Y-%m-%d %H:%M:%S %Z")}]}
            save_cache(calpath, cal_cached)
        if cal_cached is not None and all(m["id"] in cal_cached["counts"] for m in cals):
            for m in cals:
                cc = cal_cached["counts"][m["id"]]
                cal_records.append((m, {qiskit_key_to_bits(kk): int(v) for kk, v in cc.items()}))
            class_log["calibration"] = {"complete": True, "circuits": len(cals),
                                        "seconds": cal_cached.get("seconds"),
                                        "sampled_now": bool(cal_to_sample)}
        else:
            class_log["calibration"] = {"complete": False,
                                        "circuits_cached": 0 if cal_cached is None else
                                        len(cal_cached["counts"]), "circuits": len(cals)}
        t_cal = time.time() - tc
        if args.sample_only:
            print(f"--sample-only: the selected classes are in {os.path.relpath(cdir, ROOT)} "
                  f"({time.time() - t0:.0f} s)")
            for k, v in sorted(class_log.items()):
                print(f"  {k}: {v}")
            # prompts/20 B4: the clean statistic of exactly the circuits this invocation has in
            # the cache, so that a restricted run (--only-ids) can be checked without the full
            # 84-circuit analysis.  Written next to the cache as sample_check.json.
            sampled = []
            for c in selected:
                rec = cached.get(c)
                if rec is None:
                    continue
                for m in by_class[c]:
                    if only_ids is not None and m["id"] not in only_ids:
                        continue
                    if m["id"] in rec["counts"]:
                        sampled.append((m, {qiskit_key_to_bits(kk): int(v)
                                            for kk, v in rec["counts"][m["id"]].items()}))
            if sampled:
                codec0 = Codec(M.basis)
                acc_by_sec = {m["sector"]: random_acceptance(codec0, m["twoB"])["fraction"]
                              for m, _ in sampled}
                cs = clean_statistics(sampled, M, g2, acc_by_sec)
                print(f"  clean statistic of the {len(sampled)} circuit(s) sampled here "
                      f"(schedule {args.schedule}, seed {args.seed}, "
                      f"T2 override {args.t2_override or 'none'}):")
                for cid, v in sorted(cs["per_circuit"].items()):
                    print(f"    {cid}: {v['shots']} shots, accepted {v['accepted']}, "
                          f"reference hits {v['reference_hits']}, w {v['mixture']['w']:.4f}, "
                          f"clean accepted {v['mixture']['clean_accepted']:.1f}, "
                          f"near-clean {v['near_clean_accepted']:.1f}, "
                          f"f_clean(mixture) {v['mixture']['f_clean']:.4e}, "
                          f"f_clean(reference) {v['reference_string_test']['f_clean']:.4e}")
                chk = {"gate": args.out, "backend": bname, "seed": int(args.seed),
                       "schedule": args.schedule, "seed_transpiler": SCHEDULE_SEED,
                       "t2_override_file": args.t2_override, "t2_override_sha": t2_override_sha,
                       "t2_override": t2_table,
                       "calibration_fingerprint": cal_fingerprint,
                       "calibration_fingerprint_source": cal_fingerprint_source,
                       "circuits": sorted(cs["per_circuit"]),
                       "schedule_info": (dict(circuits.info) if isinstance(circuits, LazySchedule)
                                         else None),
                       "clean_statistics": cs,
                       "when": time.strftime("%Y-%m-%d %H:%M:%S %Z")}
                with open(os.path.join(cdir, "sample_check.json"), "w") as fh:
                    json.dump(chk, fh, indent=1)
                print(f"  wrote {os.path.relpath(os.path.join(cdir, 'sample_check.json'), ROOT)}")
            return 0
        incomplete = [k for k, v in class_log.items() if not v["complete"]]
        if incomplete:
            raise SystemExit(
                f"the analysis needs all {len(classes)} sampling classes and the calibration set; "
                f"{incomplete} are incomplete in {os.path.relpath(cdir, ROOT)}.  Run the missing "
                f"classes with --sample-only first (prompts/16 A'3).")
    print(f"sampling {t_sample:.0f} s, calibration {t_cal:.0f} s", flush=True)

    # ------------------------------------------------------- analysis
    A = analyse_records(records, cal_records, M, g2, plan=support_plan)
    plan = shot_plan(A, args.p, args.k, args.conf)
    # prompts/20 B3: the clean statistic of the SIMULATED counts (decisions C2'/C3'/M4.4) and,
    # when the circuits were scheduled, the analytic PTA bound at the T2 actually used, so that
    # the H0P-Y' ordering "bound <= scheduled simulation" is computed and not asserted.
    tcs = time.time()
    clean = clean_statistics(records, M, g2,
                             {sec: A["random_acceptance"][sec]["fraction"]
                              for sec in A["random_acceptance"]})
    A["clean_statistics"] = clean
    print(f"clean statistic of {len(clean['per_circuit'])} circuits "
          f"({time.time() - tcs:.0f} s)", flush=True)
    pta, bracket, pta_record = None, None, None
    if args.schedule == "asap":
        pta_record = calibration if live else snapshot_rec
        t2_s = (None if t2_table is None else
                {int(r["qubit"]): float(r["T2_override_s"]) for r in t2_table["per_qubit"]})
        try:
            pta = pta_bounds(circuits, mans, pta_record, t2_s)
            bracket = yield_bracket(pta, clean, mans)
        except SystemExit as exc:                  # a record that cannot carry the model
            print(f"the PTA bound could not be computed on this record: {exc}", flush=True)
            pta, bracket = None, {"error": str(exc)}
        if bracket:
            for key, v in sorted(bracket.items()):
                if "f_pta_bound_mean" not in v:
                    continue
                print(f"  {key}: PTA bound {v['f_pta_bound_mean']:.4e} <= scheduled-Aer clean f "
                      f"{v['f_clean_scheduled_simulation']:.4e} "
                      f"({v['ratio_simulation_over_bound']:.1f}x) -> "
                      f"{'ordered' if v['bound_below_simulation'] else 'VIOLATED'}", flush=True)
    data = {
        "frozen_set": {kk: index[kk] for kk in ("created", "n_circuits", "n_calibration_circuits",
                                                "repetitions", "kmax", "sectors", "references",
                                                "per_repetition", "distinct_readout_patches", "leakage")},
        "backend": bname, "backend_is_live": live, "snapshot_of_the_frozen_set": snapshot_name,
        "simulator": (f"AerSimulator.from_backend({bname}, seed_simulator={args.seed})" if live else
                      f"AerSimulator.from_backend({bname}(), seed_simulator={args.seed})"),
        "sampling": {"shots_per_circuit_by_repetition": {str(r): shots_by_rep[r] for r in reps},
                     "shot_allocation": ("pinned with --shots-plan" if args.shots_plan else
                                         "pinned with --shots-by-rep" if args.shots_by_rep
                                         else args.shot_allocation),
                     "circuits": len(mans),
                     "total_shots": sum(shots_of[m["id"]] for m in mans),
                     "seconds_per_shot_by_repetition": {str(r): t_shot[r] for r in sorted(t_shot)},
                     "setup_seconds_per_call_by_repetition": {str(r): setup[r] for r in sorted(setup)},
                     "predicted_sampling_seconds": predicted_s,
                     "seconds_per_shot_whole_set": per_shot_total,
                     "budget_minutes": args.budget_minutes, "sampling_seconds": t_sample,
                     "calibration_shots_per_circuit": args.cal_shots, "calibration_seconds": t_cal,
                     "pilot_shots": args.pilot_shots,
                     "shots_by_circuit": {c: int(v) for c, v in sorted(shots_of.items())},
                     "sample_cache": (None if not use_cache else os.path.relpath(cdir, ROOT)),
                     "sampling_classes": class_log or None},
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
        "shot_plan_file": args.shots_plan,
        "shot_plan_stamp": plan_stamp,
        "shot_plan_calibration_fingerprint": plan_fingerprint,
        "support_shot_plan": (None if support_plan is None else {
            kk: support_plan[kk] for kk in
            ("rule", "lambda_star", "margin", "readout_factor", "floor", "round_to", "backend",
             "calibration", "f_source", "amplitude_crosscheck_max_dp", "sectors",
             "shots_by_circuit", "calibration_shots", "totals") if kk in support_plan}),
        "analysis": A,
        # ---------------------------------------------------- prompts/20 B1/B2/B3
        "schedule": {
            "mode": args.schedule,
            "seed_transpiler": SCHEDULE_SEED,
            "method": ("transpile(circ, backend, optimization_level=0, "
                       "scheduling_method='asap', seed_transpiler=7): the idle windows become "
                       "explicit Delay instructions, which AerSimulator.from_backend charges "
                       "with thermal relaxation from target.qubit_properties"),
            "seconds": (float(circuits.seconds) if isinstance(circuits, LazySchedule) else 0.0),
            "per_circuit": (dict(circuits.info) if isinstance(circuits, LazySchedule) else None),
        },
        "t2_override": t2_table,
        "pta_bound": pta,
        "yield_bracket": bracket,
        "yield_criterion": None,          # filled in with the criteria below
        "clean_statistic": {
            "statistic": clean["statistic"],
            "decisions": ("C2' (mixture estimator), C3' (reference-string / bit-order test), "
                          "M4.4 (near-clean acceptance term) -- data/H0_replan_owner_decisions.md"),
            "readout_factor": READOUT_FACTOR,
        },
    }
    if live:
        data["calibration"] = {
            "path": os.path.relpath(cal_path, ROOT),
            "backend": calibration["backend"],
            "last_update_date": calibration["last_update_date"],
            "stamp": calibration["stamp"],
            # prompts/17 D9: the identity the submission preflight compares.  The stamp is
            # kept as information -- IBM moves it when it calibrates other parts of the device.
            "fingerprint": calibration["fingerprint"],
            "fingerprint_fields": calibration["fingerprint_fields"],
            "fingerprint_note": calibration["fingerprint_note"],
            "dt_s": calibration["dt_s"], "default_rep_delay_s": calibration["default_rep_delay_s"],
            "max_circuits": calibration["max_circuits"], "status": calibration["status"],
            "n_qubits_frozen_set": calibration["n_qubits_frozen_set"],
            "n_edges_frozen_set": calibration["n_edges_frozen_set"],
            "missing_errors": calibration["missing_errors"],
        }
        data["f_recomputed_on_the_day"] = {
            "source": f"gate_S2D.analyse_on_backend(frozen circuit, {bname}.target)",
            "per_circuit": f_live,
            "mean_f_live": float(np.mean([v["f_live"] for v in f_live.values()])),
            "mean_f_manifest": float(np.mean([v["f_manifest"] for v in f_live.values()])),
            "note": ("the frozen circuits are unchanged (prompts/15 D1); only the calibration they are "
                     "evaluated against is the session day's"),
        }

    # ------------------------------------------------------- criteria
    lk = index["leakage"]
    R.add(f"every frozen circuit leak-free after transpilation onto {snapshot_name} "
          f"({lk['n_checked']} circuits, noiseless statevector permuted back with the final layout)",
          lk["max"], f"< {LEAK_TOL:g}", lk["max"] < LEAK_TOL)
    for sec in sorted(A["by_sector"]):
        s = A["by_sector"][sec]
        R.add(f"{sec}: decoded support reproduces the exact E0 = {s['exact_E0']:.4f}",
              s["abs_error"], f"|E_R - E_0| < {E0_TOL:g}", s["abs_error"] < E0_TOL)
    if support_plan is not None:
        # prompts/16 change 2: the premise of criterion 3 of the preregistration ("the Ritz
        # energies of the SATURATED sectors reproduce E_0") becomes a checked prediction.  No
        # criterion of the preregistration and no constant is touched; these are two criteria of
        # the PREPARATION gate about the shot plan itself.
        for sec in sorted(support_plan["sectors"]):
            v = support_plan["sectors"][sec]
            R.add(f"{sec} shot plan: every one of the {v['dimension']} sector states has expected "
                  f"clean count >= lambda* in the r = 1 circuits at "
                  f"{support_plan['margin']} x f_cal (N4 = {v['N4']}, "
                  f"{v['r1_shots_total']} r = 1 shots; min lambda_s)",
                  round(v["min_lambda_r1_at_margin"], 4),
                  f">= lambda* = {support_plan['lambda_star']:.4f}",
                  v["min_lambda_r1_at_margin"] >= support_plan["lambda_star"])
    for sec in sorted(A["random_acceptance"]):
        ra = A["random_acceptance"][sec]
        R.add(f"{sec}: acceptance of random bit strings (exhaustive over all {ra['strings']} strings)",
              f"{100 * ra['fraction']:.3f}%", f"< {100 * RANDOM_ACCEPT_MAX:.0f}%",
              ra["fraction"] < RANDOM_ACCEPT_MAX)
    # decision H0P-Y' (signed 2026-09-30): the factor-of-three band around the manual's yield
    # model compared a BOUND against a simulation as though it were a prediction, which is the
    # failure mode that produced the misreported "1.13x agreement".  With a scheduled run the
    # criterion becomes the ordering PTA bound <= scheduled-Aer clean f, which tests mutual
    # consistency instead of asserting a number none of the three quantities claims.  Without a
    # scheduled run there is no bound to order against, so the old ratio band is what is
    # evaluated -- which is why every unscheduled output keeps exactly the criteria it had.
    use_bracket = (args.yield_criterion == "bracket" or
                   (args.yield_criterion == "auto" and args.schedule == "asap"))
    if use_bracket and not (bracket and any("f_pta_bound_mean" in v for v in bracket.values())):
        raise SystemExit(
            f"--yield-criterion {args.yield_criterion} needs the analytic PTA bound, which needs "
            f"--schedule asap and a calibration record covering the frozen set "
            f"({(bracket or {}).get('error', 'no bound computed')}).  Use --yield-criterion ratio "
            f"for the unscheduled band of prompts/13.")
    data["yield_criterion"] = ("bracket: PTA bound <= scheduled-Aer clean f (decision H0P-Y')"
                               if use_bracket else
                               f"ratio: simulated / model yield in [{RATIO_LO:.2f}, {RATIO_HI:.0f}] "
                               f"(prompts/13)")
    for key in sorted(A["by_sector_repetition"]):
        v = A["by_sector_repetition"][key]
        if use_bracket:
            b = bracket[key]
            R.add(f"{key} ({v['cz_mean']:.0f} CZ): the analytic PTA bound "
                  f"{b['f_pta_bound_mean']:.3e} does not exceed the clean f of the scheduled "
                  f"simulation {b['f_clean_scheduled_simulation']:.3e} (decision H0P-Y'; the "
                  f"bound charges every relaxation error as fatal, so the ordering is the "
                  f"statement, not the ratio)",
                  round(b["ratio_simulation_over_bound"], 3)
                  if b["ratio_simulation_over_bound"] is not None else None,
                  "scheduled clean f / PTA bound >= 1", b["bound_below_simulation"])
            continue
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
    if not args.no_prereg:
        write_report(f"H0_prereg_{bname}.md" if live else "H0_prereg_draft.md",
                     prereg_report(args, R, data, index))
    print(R.criteria_table())
    return 0 if R.passed else 1


# ------------------------------------------------------------------ reports
def fmt(v, spec=".4f"):
    return "n/a" if v is None else format(v, spec)


def has_manifest_f(A):
    """True on the live path: f was recomputed on the day's calibration (prompts/15 A1)."""
    return any("f_calibration_manifest_mean" in v for v in A["by_sector_repetition"].values())


def yield_head(A):
    head = list(YIELD_HEAD)
    if has_manifest_f(A):
        head.insert(head.index("f (calibration)") + 1, "f (frozen snapshot)")
    return head


def yield_rows(A):
    rows = []
    extra = has_manifest_f(A)
    for key in sorted(A["by_sector_repetition"]):
        v = A["by_sector_repetition"][key]
        rows.append([v["sector"], v["repetitions"], v["circuits"], f"{v['cz_mean']:.0f}",
                     fmt(v["f_calibration_mean"])]
                    + ([fmt(v.get("f_calibration_manifest_mean"))] if extra else [])
                    + [fmt(v["garbage_acceptance"], ".5f"),
                     fmt(v["model_yield_0.82f"]), fmt(v["model_yield_full"]),
                     v["shots"], fmt(v["yield"]), fmt(v["ratio_simulated_over_model"], ".2f"),
                     fmt(v["ratio_simulated_over_full_model"], ".2f"),
                     v["support_size"], str(v["rejections"])])
    return rows


YIELD_HEAD = ["sector", "r", "circuits", "CZ", "f (calibration)", "a (garbage)",
              "model 0.82 f (old)", "model 0.82 f + (1−f) a", "shots", "simulated yield",
              "simulated / 0.82 f", "simulated / full model", "distinct states", "rejections"]


def support_block(D):
    """Section 4 of the report: which sector states the support holds and which it misses
    (prompts/16 change 3 -- an OUTPUT, no criterion depends on it)."""
    A = D["analysis"]
    sp = D.get("support_shot_plan")
    out = []
    for sec in sorted(A["by_sector"]):
        v = A["by_sector"][sec]
        miss = v.get("missing_states") or []
        head = ["basis index", "label (j2; n)", "observed accepted count"]
        if sp:
            head += ["predicted clean count (all circuits, at f)",
                     "predicted clean count (r = 1, at margin)"]
        rows = []
        for r in sorted(v.get("per_state", []), key=lambda x: x["observed_accepted_count"])[:8]:
            row = [r["basis_index"], r["label"], r["observed_accepted_count"]]
            if sp:
                row += [fmt(r.get("predicted_clean_count_all_circuits_at_f"), ".2f"),
                        fmt(r.get("predicted_clean_count_r1_at_margin"), ".2f")]
            rows.append(row)
        planline = ""
        if sp:
            sv = sp["sectors"][sec]
            planline = (f"  Shot plan: N4 = {sv['N4']}, {sv['r1_shots_total']} r = 1 shots, "
                        f"min lambda_s at {sp['margin']} f = {sv['min_lambda_r1_at_margin']:.4f} "
                        f"(lambda* = {sp['lambda_star']:.4f}), P(all {sv['dimension']} states seen "
                        f"from clean shots) = {sv['P_saturation_clean_at_margin']:.5f}.")
        out.append(f"""**{sec}**: {len(v['support_states_decoded'])} of {v['sector_dimension']} sector states decoded,
{len(miss)} missing{' (' + ', '.join(str(m['basis_index']) + ' ' + m['label'] for m in miss) + ')' if miss else ''}.{planline}
The eight least observed states:

{md_table(head, rows)}
""")
    return "\n".join(out)


def gate_report(args, R, D, index):
    A = D["analysis"]
    S = D["sampling"]
    lk = D["frozen_set"]["leakage"]
    calblock = ""
    if D.get("calibration"):
        c, fr = D["calibration"], D["f_recomputed_on_the_day"]
        st = c["status"]
        calblock = (
            f"\n**The calibration of the session day** (prompts/15 D1: the circuits stay frozen, the "
            f"prediction is recomputed).  `{c['path']}` -- {c['backend']}, `last_update_date` "
            f"{c['last_update_date']}, fingerprint `{(c.get('fingerprint') or 'n/a')[:16]}` "
            f"(prompts/17 D9: the sha256 of the {c['n_qubits_frozen_set']} qubit and "
            f"{c['n_edges_frozen_set']} edge blocks this prediction reads), dt {c['dt_s']}, "
            f"default rep delay "
            f"{c['default_rep_delay_s']} s, max_circuits {c['max_circuits']}, "
            f"{'operational' if st.get('operational') else 'NOT operational'}, "
            f"{st.get('pending_jobs')} pending jobs.  It covers the {c['n_qubits_frozen_set']} qubits and "
            f"{c['n_edges_frozen_set']} two-qubit edges the frozen set uses; "
            f"{len(c['missing_errors'])} of those target entries carry no error value (a non-empty list "
            f"is a hard stop, not a defaulted value).  The clean-shot fraction f was recomputed circuit "
            f"by circuit on that target with `gate_S2D.analyse_on_backend`: mean {fr['mean_f_live']:.4f} "
            f"against {fr['mean_f_manifest']:.4f} frozen into the manifests.\n")

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
{calblock}
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

{md_table(yield_head(A), yield_rows(A))}

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
(manual Step 9.1), not an accuracy test: a permuted codeword would give a different energy.  Whether
they saturate is a property of the SHOT PLAN, not an assumption: see the support table below.

{support_block(D)}

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
    calblock = ""
    if D.get("calibration"):
        c, fr = D["calibration"], D["f_recomputed_on_the_day"]
        st = c["status"]
        calblock = (
            f"\n**The calibration of the session day** (prompts/15 D1: the circuits stay frozen, the "
            f"prediction is recomputed).  `{c['path']}` -- {c['backend']}, `last_update_date` "
            f"{c['last_update_date']}, dt {c['dt_s']}, default rep delay "
            f"{c['default_rep_delay_s']} s, max_circuits {c['max_circuits']}, "
            f"{'operational' if st.get('operational') else 'NOT operational'}, "
            f"{st.get('pending_jobs')} pending jobs.  It covers the {c['n_qubits_frozen_set']} qubits and "
            f"{c['n_edges_frozen_set']} two-qubit edges the frozen set uses; "
            f"{len(c['missing_errors'])} of those target entries carry no error value (a non-empty list "
            f"is a hard stop, not a defaulted value).  The clean-shot fraction f was recomputed circuit "
            f"by circuit on that target with `gate_S2D.analyse_on_backend`: mean {fr['mean_f_live']:.4f} "
            f"against {fr['mean_f_manifest']:.4f} frozen into the manifests.\n"
            f"\n**Submission rule (prompts/17 D9)**: the jobs are submitted only while the live "
            f"calibration of these {c['n_qubits_frozen_set']} qubits and {c['n_edges_frozen_set']} edges "
            f"is identical to this record (fingerprint `{c.get('fingerprint')}`) and the live "
            f"clean-shot fraction of all {len(fr['per_circuit'])} circuits equals the plan's to 1e-9; "
            f"the calibration timestamp at submission is recorded and may differ from the one above "
            f"when IBM's update touched other parts of the device.\n")

    prows = [[v["sector"], v["repetitions"], v["circuits"], fmt(v["model_yield_0.82f"]),
              v["N_circuit_model"], fmt(v["N_sector_model"], ".3e"),
              fmt(v["simulated_yield"]), v["N_circuit_simulated"],
              fmt(v["N_sector_simulated"], ".3e")] for v in D["shot_plan"].values()]
    r1 = [v for v in A["by_sector_repetition"].values() if v["repetitions"] == 1]
    return f"""# H0 preregistration (draft) — 2x2 calibration session on a Heron-class device

**Generated by `scripts/gate_H0P.py` from `validation/{R.gate}.json`; no number below is typed by hand.**
{env_block()}
{calblock}
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

{md_table(yield_head(A), rows)}

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

On the session day the predicted yields are recomputed from **that day's** calibration by
`scripts/gate_H0P.py --backend <device>`, before submission.  The circuits themselves are **not**
rebuilt: `{args.prep}` is submitted byte-for-byte as validated here and by `scripts/ibm_account.py
--check` on the live coupling map (prompts/15 D1 — re-transpiling on the live target would let
level-3 layout selection pick a patch from the day's error rates, producing a set that neither this
gate nor the dry run ever saw).  What is recomputed is the per-circuit clean-shot fraction f from
the live `backend.target`, the Aer device model built from the live backend, and the per-qubit
readout errors that `scripts/gate_H0.py --calibration` uses as its drift reference.

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
