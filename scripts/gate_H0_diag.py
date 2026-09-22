#!/usr/bin/env python3
"""
Gate H0_diag (prompts/19 step D) — the PREREGISTERED analysis of the diagnostic session.

Four SamplerV2 jobs on ibm_fez decide between two hypotheses for the canary NO-GO
(`reports/H0_canary_planner_analysis_20260922.md`):

  H_A  the prediction omits idle-time relaxation of a nearly serial 43.7 us circuit
       (3.323 Pauli-error units on the calibration's own T1/T2) -> with the SamplerV2
       options OFF the yield gets WORSE, 31 +- 6 accepted of 2000;
  H_B  the options (DD XY4, twirling `active-accum`), live for the first time in the
       canary, are harmful -> with them off the gate-only prediction is restored,
       374 +- 17 accepted of 2000.

  J1  DD off, twirling off: canary circuit, `t1w`, `ramw`, all-0, all-1
  J2  DD XY4, twirling off: canary circuit, `t1w`, `ramw`
  J3  DD off, twirling on:  canary circuit
  J4  DD XY4, twirling on:  canary circuit (the canary's own options, 7.5x its statistics)

The decision rule and every prediction are fixed BEFORE the data exist, in the
preregistration file written by `scripts/h0_idle_model.py --backend ibm_fez` and committed
with this script: N1 <= 100 rejects H_B, N1 >= 250 confirms it, and 100 < N1 < 250 is
reported as inconclusive (C3 fails) rather than argued either way.

Criteria (D5): C1 job bookkeeping and the QPU-time caps; C2 decoder round trip; C3 the
decisive J1 count; C4a/C4b the idle tests against the calibration record's T1 and T2;
C5 the idle-aware post-diction with the MEASURED T1/T2* of J1 and T1/T2 under DD of J2,
within a factor 3 of the measured clean yield; C6 the readout confusion at 2000 shots.

The script reads the raw counts only and never modifies them; no QPU time is used.

Usage: python scripts/gate_H0_diag.py --prereg data/hardware/H0_diag_prep/idle_model_<fp>.json \\
           --counts-J1 data/hardware/H0_diag_J1/counts [--counts-J2 ... --counts-J3 ... --counts-J4 ...] \\
           --out H0_diag
"""
import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.hardware import confusion_matrix  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import READOUT_FACTOR, yield_model  # noqa: E402

import h0_idle_model as im  # noqa: E402
from gate_H0 import codeword_roundtrip, read_counts_dir  # noqa: E402
from gate_H0P import DIAG_MIN, load_circuit, load_manifests, random_acceptance  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CANARY_ID = "B0_ref06_k1_rep1"
MAX_USAGE_PER_JOB_S = 30.0       # prompts/19 D6 / prompts/15 D6
MAX_USAGE_SESSION_S = 40.0
N1_REJECT_H_B = 100              # C3: at or below this, H_B is rejected
N1_CONFIRM_H_B = 250             # C3: at or above this, H_B is confirmed
RATE_LO, RATE_HI = 0.5, 2.0      # C4a: 1/T1_meas within [0.5, 2] x 1/T1_record
IDLE_QUBITS_MIN = 10             # C4a / C4b: at least this many of 12 qubits
POSTDICTION_FACTOR = 3.0         # C5
SIGMA = 3.0                      # C4b: 3 binomial sigma of slack on the Hahn-echo bound
RO_REFERENCE_QUBIT = 123         # the readout-drift item of the canary (information only)


# --------------------------------------------------------------------------- inputs
def load_prereg(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(p) as fh:
        pre = json.load(fh)
    if not (pre.get("calibration") or {}).get("fingerprint"):
        raise SystemExit(f"{path} is not a preregistration of scripts/h0_idle_model.py")
    cal_rel = pre["calibration"].get("path")
    if not cal_rel:
        raise SystemExit(f"{path} carries no calibration.path: the record it was written on "
                         f"is needed for the post-diction of C5")
    cp = cal_rel if os.path.isabs(cal_rel) else os.path.join(ROOT, cal_rel)
    with open(cp) as fh:
        rec = json.load(fh)
    return pre, rec


def load_job(counts_dir):
    """(records, session) of one diagnostic job; the session sits next to the counts."""
    if counts_dir is None:
        return None
    p = counts_dir if os.path.isabs(counts_dir) else os.path.join(ROOT, counts_dir)
    if not os.path.isdir(p):
        raise SystemExit(f"{counts_dir} is not a directory")
    recs = read_counts_dir(p)
    if not recs:
        raise SystemExit(f"no counts files in {counts_dir}")
    spath = os.path.join(os.path.dirname(os.path.normpath(p)), "session.json")
    session = None
    if os.path.isfile(spath):
        with open(spath) as fh:
            session = json.load(fh)
    return {"counts_dir": counts_dir, "records": recs, "session": session,
            "session_file": (os.path.relpath(spath, ROOT) if session else None)}


# --------------------------------------------------------------------------- D2 canary pubs
def mixture_fit(shots, accepted, rejections, uniform_reasons, a):
    """planner P3: fit 'c x clean + (1 - c) x uniform' on the acceptance, then test the
    rejection split against it (chi-square with 2 degrees of freedom)."""
    y = accepted / shots if shots else 0.0
    c = (y - a) / (1.0 - a)
    total_uniform = sum(uniform_reasons.values()) + round(a * 2 ** 12)
    exp, obs, chi2 = {}, {}, 0.0
    for r, n_uniform in sorted(uniform_reasons.items()):
        e = (1.0 - c) * shots * n_uniform / total_uniform
        o = float(rejections.get(r, 0))
        exp[r], obs[r] = e, o
        if e > 0:
            chi2 += (o - e) ** 2 / e
    return {"c": float(c), "expected_rejections": exp, "observed_rejections": obs,
            "chi_square": float(chi2), "dof": max(len(uniform_reasons) - 1, 1),
            "uniform_reasons": {k: int(v) for k, v in uniform_reasons.items()}}


def canary_pub(job, codec, a, uniform_reasons, reference_key):
    man, counts = next((m, c) for m, c in job["records"] if m["id"] == CANARY_ID)
    acc, rej = codec.decode_counts(counts, target_twoB=man["twoB"])
    shots = int(sum(counts.values()))
    n_acc = int(sum(acc.values()))
    rt = codeword_roundtrip([(man, counts)], codec)
    from skqd.reference_sim import qiskit_key_to_bits
    ref_bits = qiskit_key_to_bits(reference_key)
    return {
        "id": CANARY_ID, "shots": shots, "accepted": n_acc,
        "yield": n_acc / shots if shots else 0.0,
        "clean_fraction_from_yield": ((n_acc / shots - a) / (READOUT_FACTOR - a)
                                      if shots else None),
        "distinct_states": len(acc), "distinct_strings": len(counts),
        "rejections": {k: int(v) for k, v in rej.items()},
        "reference_string": reference_key,
        "reference_string_count": int(counts.get(ref_bits, 0)),
        "roundtrip": rt,
        "mixture": mixture_fit(shots, n_acc, rej, uniform_reasons, a),
        "sampler_options": man.get("sampler_options"),
        "job_id": man.get("job_id"),
    }


# --------------------------------------------------------------------------- D3 idle tests
def readout_reference(job, n):
    """(P(0|0), P(1|1)) per logical qubit from the all-0 / all-1 pubs of this job."""
    preps = {}
    for man, counts in job["records"]:
        if man["kind"] == "readout_calibration":
            preps[tuple(man["prep_bits"])] = counts
    if not preps:
        return None
    C = confusion_matrix(preps, n)
    return {"P_measure_0_given_0": [float(C[q, 0, 0]) for q in range(n)],
            "P_measure_1_given_1": [float(C[q, 1, 1]) for q in range(n)],
            "min_diagonal": float(min(min(C[q, 0, 0], C[q, 1, 1]) for q in range(n))),
            "measured_error": [1.0 - 0.5 * (float(C[q, 0, 0]) + float(C[q, 1, 1]))
                               for q in range(n)]}


def marginal_ones(counts, n):
    """(per-logical-qubit P(bit = 1), shots) of a counts dictionary of bit tuples."""
    shots = sum(counts.values())
    ones = [0] * n
    for bits, c in counts.items():
        for q in range(n):
            ones[q] += c * int(bits[q])
    return [o / shots for o in ones], int(shots)


def idle_tests(job, ro, rec, n, label):
    """Per-qubit T1 and T2* from the `t1w` / `ramw` pubs, readout-corrected (D3)."""
    out = {}
    for man, counts in job["records"]:
        if man["kind"] != "idle_test":
            continue
        Td = float(man["total_delay_s"])
        phys = man["logical_to_physical"]
        p1, shots = marginal_ones(counts, n)
        per_q = {}
        for q in range(n):
            e00 = ro["P_measure_0_given_0"][q] if ro else 1.0
            e11 = ro["P_measure_1_given_1"][q] if ro else 1.0
            qq = rec["qubits"][str(phys[q])]
            T1r, T2r = float(qq["T1_s"]), float(qq["T2_s"])
            if man["test"] == "t1w":
                raw = p1[q]
                denom = e11 - (1.0 - e00)
                p = (raw - (1.0 - e00)) / denom if denom else None
                sig = math.sqrt(max(raw * (1 - raw), 0.0) / shots) / abs(denom) if denom else None
                T1m = -Td / math.log(p) if (p is not None and 0.0 < p < 1.0) else None
                per_q[str(phys[q])] = {
                    "logical": q, "raw_P_one": raw, "P_survive": p, "sigma": sig,
                    "T1_measured_s": T1m, "T1_record_s": T1r,
                    "rate_ratio": (T1r / T1m) if T1m else None,
                    "P_survive_predicted": math.exp(-Td / T1r),
                    "rate_within_band": (T1m is not None
                                         and RATE_LO <= (T1r / T1m) <= RATE_HI),
                }
            else:
                raw0 = 1.0 - p1[q]
                denom = e00 - (1.0 - e11)
                p0 = (raw0 - (1.0 - e11)) / denom if denom else None
                sig = math.sqrt(max(raw0 * (1 - raw0), 0.0) / shots) / abs(denom) if denom else None
                bound = (1.0 + math.exp(-Td / T2r)) / 2.0
                T2m = (-Td / math.log(2 * p0 - 1.0)
                       if (p0 is not None and 2 * p0 - 1.0 > 0.0) else None)
                hi = None if (p0 is None or sig is None) else p0 + SIGMA * sig
                ub = (-Td / math.log(2 * hi - 1.0)
                      if (hi is not None and 0.0 < 2 * hi - 1.0 < 1.0) else None)
                per_q[str(phys[q])] = {
                    "logical": q, "raw_P_zero": raw0, "P_zero": p0, "sigma": sig,
                    "T2star_measured_s": T2m,
                    "T2star_upper_bound_s": ub,
                    "fully_dephased": bool(p0 is not None and 2 * p0 - 1.0 <= 0.0),
                    "T2_record_s": T2r,
                    "P_zero_bound_from_record": bound,
                    "within_bound": (p0 is not None and sig is not None
                                     and p0 <= bound + SIGMA * sig),
                }
        out[man["test"]] = {
            "id": man["id"], "shots": shots, "total_delay_s": Td,
            "readout_reference": label, "per_qubit": per_q,
            "n_within": sum(1 for v in per_q.values()
                            if v.get("rate_within_band") or v.get("within_bound")),
        }
    return out


# --------------------------------------------------------------------------- D4 post-diction
def substituted_record(rec, phys_to_T1, phys_to_T2):
    """A copy of the calibration record with the MEASURED coherence times substituted."""
    out = json.loads(json.dumps(rec))
    for q, v in out["qubits"].items():
        if int(q) in phys_to_T1 and phys_to_T1[int(q)]:
            v["T1_s"] = float(phys_to_T1[int(q)])
        if int(q) in phys_to_T2 and phys_to_T2[int(q)]:
            v["T2_s"] = float(phys_to_T2[int(q)])
    return out


def postdiction(prep, rec, tests, a, measured_yield, with_dd):
    """The A3 budget re-run on the measured T1 / T2 for the canary circuit (D4).

    For J2 the DD pulse cost is INSIDE the measured T2 under DD, so no S_DD is added
    and the whole T2 budget is taken as it stands."""
    t1 = {int(q): v["T1_measured_s"] for q, v in (tests.get("t1w") or {}).get("per_qubit", {}).items()}
    t2 = {int(q): (v["T2star_measured_s"] or v["T2star_upper_bound_s"])
          for q, v in (tests.get("ramw") or {}).get("per_qubit", {}).items()}
    missing = [q for q, v in t1.items() if not v] + [q for q, v in t2.items() if not v]
    rec2 = substituted_record(rec, t1, t2)
    mans, _ = load_manifests(prep)
    man = next(m for m in mans if m["id"] == CANARY_ID)
    qc = load_circuit(prep, man)
    sch = im.schedule(qc, rec2)
    per_q, tot = im.budgets(sch, rec2)
    f_gates, f_only, ro, _n, _nm = im.f_on_record(qc, rec2)
    f = f_gates * math.exp(-tot["S_T1"] - tot["S_T2"])
    y = yield_model(f, a)
    clean_meas = measured_yield - a
    clean_pred = y - a
    ratio = (clean_meas / clean_pred) if clean_pred > 0 else None
    return {
        "with_dd": with_dd,
        "T1_measured_s": {str(k): v for k, v in sorted(t1.items())},
        "T2_measured_s": {str(k): v for k, v in sorted(t2.items())},
        "qubits_without_a_usable_time": sorted(set(missing)),
        "S_T1": tot["S_T1"], "S_T2": tot["S_T2"],
        "S_DD_not_applied": ("the measured T2 under DD already contains the pulse cost"
                             if with_dd else "DD was off"),
        "f_gates": f_gates, "f_predicted": f,
        "yield_predicted": y, "yield_measured": measured_yield,
        "garbage_acceptance": a,
        "clean_yield_measured": clean_meas, "clean_yield_predicted": clean_pred,
        "ratio_measured_over_predicted": ratio,
        "within_factor": (ratio is not None and 1.0 / POSTDICTION_FACTOR <= ratio <= POSTDICTION_FACTOR),
        "factor": POSTDICTION_FACTOR,
        "per_qubit": per_q,
    }


# --------------------------------------------------------------------------- main
def usage_block(job):
    s = job["session"] or {}
    jobs = s.get("jobs") or []
    us = [j.get("usage_s") for j in jobs]
    return {
        "session_file": job["session_file"],
        "job_ids": [j.get("job_id") for j in jobs],
        "statuses": [j.get("status") for j in jobs],
        "usage_s_per_job": us,
        "usage_s": (float(sum(u for u in us if u is not None)) if any(u is not None for u in us)
                    else None),
        "all_done": bool(jobs) and all(j.get("status") == "DONE" for j in jobs),
        "usage_recorded": bool(jobs) and all(j.get("usage_s") is not None for j in jobs),
        "sampler_options": s.get("sampler_options"),
        "calibration_fingerprint": s.get("calibration_fingerprint"),
        "retrieval_calibration_fingerprint": s.get("retrieval_calibration_fingerprint"),
        "prereg_fingerprint_match": s.get("prereg_fingerprint_match"),
        "dry_run": s.get("dry_run"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", required=True, help="the idle-model preregistration JSON")
    ap.add_argument("--counts-J1", required=True)
    ap.add_argument("--counts-J2", default=None)
    ap.add_argument("--counts-J3", default=None)
    ap.add_argument("--counts-J4", default=None)
    ap.add_argument("--out", default="H0_diag")
    args = ap.parse_args()
    t0 = time.time()

    pre, rec = load_prereg(args.prereg)
    prep = os.path.join(ROOT, pre["prep"])
    jobs = {}
    for name, d in (("J1", args.counts_J1), ("J2", args.counts_J2),
                    ("J3", args.counts_J3), ("J4", args.counts_J4)):
        j = load_job(d)
        if j is not None:
            jobs[name] = j

    index_common = None
    with open(os.path.join(prep, "index.json")) as fh:
        index_common = json.load(fh)["common"]
    M = Model(int(index_common["lattice"].split("x")[1]))
    codec = Codec(M.basis)
    n = codec.n_qubits
    ra = random_acceptance(codec, 0)
    a = ra["fraction"]
    ref_key = pre.get("session_prediction", {}).get("reference_string") or "000100100000"

    R = GateResult(args.out, "H0 diagnostic session on ibm_fez: the DD x twirling factorial "
                             "of the frozen canary circuit and the windowed idle tests that "
                             "decide between the idle-relaxation and the sampler-options "
                             "hypotheses")

    # ---------------------------------------------------------------- D2 canary pubs
    pubs, usage = {}, {}
    for name, job in jobs.items():
        pubs[name] = canary_pub(job, codec, a, ra["reasons"], ref_key)
        usage[name] = usage_block(job)

    # ---------------------------------------------------------------- D3 idle tests
    ro_j1 = readout_reference(jobs["J1"], n)
    tests = {}
    for name, job in jobs.items():
        if not any(m["kind"] == "idle_test" for m, _ in job["records"]):
            continue
        own = readout_reference(job, n)
        label = (f"{name} own all-0/all-1" if own else
                 "J1 all-0/all-1 (this job carries no readout-calibration pub)")
        tests[name] = idle_tests(job, own or ro_j1, rec, n, label)

    # ---------------------------------------------------------------- D4 post-diction
    post = {}
    if "J1" in tests:
        post["J1"] = postdiction(prep, rec, tests["J1"], a, pubs["J1"]["yield"], with_dd=False)
    if "J2" in tests:
        post["J2"] = postdiction(prep, rec, tests["J2"], a, pubs["J2"]["yield"], with_dd=True)

    # ---------------------------------------------------------------- the decision
    N1 = pubs["J1"]["accepted"]
    sp = pre.get("session_prediction") or {}
    decision = ("H_B rejected (the options are not the cause; the idle term is)" if N1 <= N1_REJECT_H_B
                else "H_B confirmed (the sampler options were the cause)" if N1 >= N1_CONFIRM_H_B
                else "inconclusive")
    comparison = {
        "N1": N1, "shots_J1": pubs["J1"]["shots"],
        "prediction_H_A": sp.get("H_A"), "prediction_H_B": sp.get("H_B"),
        "garbage_floor_expected": sp.get("garbage_floor_expected"),
        "rule": sp.get("decision_rule"),
        "decision": decision,
        "decisive": decision != "inconclusive",
    }
    ratios = {}
    if "J2" in pubs:
        ratios["J2_over_J1"] = (pubs["J2"]["accepted"] / pubs["J1"]["accepted"]
                                if pubs["J1"]["accepted"] else None)
    if "J3" in pubs:
        ratios["J3_over_J1"] = (pubs["J3"]["accepted"] / pubs["J1"]["accepted"]
                                if pubs["J1"]["accepted"] else None)
    if "J4" in pubs and "J2" in pubs:
        ratios["J4_over_J2"] = (pubs["J4"]["accepted"] / pubs["J2"]["accepted"]
                                if pubs["J2"]["accepted"] else None)

    # ---------------------------------------------------------------- C6 readout
    ro_block = {"J1": ro_j1}
    ro_q123 = None
    if ro_j1:
        phys = next(m["logical_to_physical"] for m, _ in jobs["J1"]["records"]
                    if m["kind"] == "readout_calibration")
        if RO_REFERENCE_QUBIT in phys:
            i = phys.index(RO_REFERENCE_QUBIT)
            rref = float(rec["qubits"][str(RO_REFERENCE_QUBIT)]["measure_error"])
            ro_q123 = {"physical_qubit": RO_REFERENCE_QUBIT,
                       "measured_error": ro_j1["measured_error"][i],
                       "record_error": rref,
                       "ratio": ro_j1["measured_error"][i] / rref if rref else None,
                       "note": ("information (prompts/19 D5 C6): RO_FACTOR 3 is sized for the "
                                "4000-shot calibration circuits of the main run and is not a "
                                "criterion here")}
        ro_block["physical_qubits_logical_order"] = phys

    data = {
        "backend": next((m.get("backend") for m, _ in jobs["J1"]["records"]), "unknown"),
        "prereg": args.prereg,
        "prereg_calibration": pre["calibration"],
        "prereg_commit": pre.get("commit"),
        "prereg_created": pre.get("created"),
        "prep": pre["prep"],
        "hypotheses": {
            "H_A": ("idle-time relaxation over the scheduled idle windows, omitted by "
                    "gate_S2D.analyse_on_backend and by AerSimulator.from_backend on an "
                    "unscheduled circuit (prompts/19, planner P1)"),
            "H_B": ("the SamplerV2 options (DD XY4 + twirling active-accum), live for the "
                    "first time in the canary job, are harmful"),
        },
        "garbage_acceptance": a, "random_acceptance": ra,
        "yield_model": f"y = {READOUT_FACTOR} f + (1 - f) a (manual Step 4.4)",
        "jobs": usage, "canary_pubs": pubs, "decision": comparison, "ratios": ratios,
        "idle_tests": tests, "postdiction": post,
        "readout": ro_block, "readout_qubit_123": ro_q123,
        "criteria_inputs": {
            "max_usage_per_job_s": MAX_USAGE_PER_JOB_S,
            "max_usage_session_s": MAX_USAGE_SESSION_S,
            "N1_reject_H_B": N1_REJECT_H_B, "N1_confirm_H_B": N1_CONFIRM_H_B,
            "rate_band": [RATE_LO, RATE_HI], "idle_qubits_min": IDLE_QUBITS_MIN,
            "postdiction_factor": POSTDICTION_FACTOR, "sigma": SIGMA,
            "confusion_diagonal_min": DIAG_MIN,
        },
    }

    # ---------------------------------------------------------------- criteria (D5)
    per_job_ok = all(u["all_done"] and u["usage_recorded"]
                     and (u["usage_s"] or 0.0) <= MAX_USAGE_PER_JOB_S for u in usage.values())
    total_usage = sum((u["usage_s"] or 0.0) for u in usage.values())
    data["total_usage_s"] = total_usage
    usage_text = ", ".join(f"{k} {u['usage_s']} s" for k, u in sorted(usage.items()))
    R.add(f"C1 every job DONE with usage recorded, each <= {MAX_USAGE_PER_JOB_S:.0f} s, total "
          f"<= {MAX_USAGE_SESSION_S:.0f} s ({len(usage)} job directory/ies: {usage_text})",
          round(total_usage, 3), f"per job <= {MAX_USAGE_PER_JOB_S:.0f}, total <= "
          f"{MAX_USAGE_SESSION_S:.0f}", per_job_ok and total_usage <= MAX_USAGE_SESSION_S)
    mism = sum(p["roundtrip"]["mismatches"] for p in pubs.values())
    checked = sum(p["roundtrip"]["distinct_accepted_strings"] for p in pubs.values())
    R.add(f"C2 decoder round trip over the accepted strings of {len(pubs)} canary pub(s) "
          f"({checked} distinct strings)", f"{mism} mismatch(es)", "0", mism == 0)
    R.add(f"C3 decisive J1 count: N1 = {N1} of {pubs['J1']['shots']} against the "
          f"preregistered {sp.get('H_A', {}).get('expected', float('nan')):.0f} (H_A) and "
          f"{sp.get('H_B', {}).get('expected', float('nan')):.0f} (H_B) -- {decision}",
          N1, f"<= {N1_REJECT_H_B} or >= {N1_CONFIRM_H_B}", comparison["decisive"])
    t1w = (tests.get("J1") or {}).get("t1w")
    n_rate = (sum(1 for v in t1w["per_qubit"].values() if v["rate_within_band"]) if t1w else 0)
    R.add(f"C4a t1w (J1): per-qubit decay rate 1/T1_measured within [{RATE_LO}, {RATE_HI}] x "
          f"1/T1_record", f"{n_rate} of {n}", f">= {IDLE_QUBITS_MIN} of {n}",
          n_rate >= IDLE_QUBITS_MIN)
    ramw = (tests.get("J1") or {}).get("ramw")
    n_bound = (sum(1 for v in ramw["per_qubit"].values() if v["within_bound"]) if ramw else 0)
    R.add(f"C4b ramw (J1): P(0) <= (1 + e^-T/T2_record)/2 + {SIGMA:.0f} sigma_binomial",
          f"{n_bound} of {n}", f">= {IDLE_QUBITS_MIN} of {n}", n_bound >= IDLE_QUBITS_MIN)
    for name in sorted(post):
        v = post[name]
        R.add(f"C5 {name}: the idle-aware post-diction with the measured T1/T2 predicts a clean "
              f"yield {v['clean_yield_predicted']:.5f} against the measured "
              f"{v['clean_yield_measured']:.5f}",
              None if v["ratio_measured_over_predicted"] is None
              else round(v["ratio_measured_over_predicted"], 3),
              f"within a factor {POSTDICTION_FACTOR:.0f}", v["within_factor"])
    if not post:
        R.add("C5 idle-aware post-diction", "no idle-test pub retrieved", "a J1 post-diction",
              False)
    R.add(f"C6 readout confusion of patch 1 at {pubs['J1']['shots']} shots (J1): smallest "
          f"diagonal element",
          None if not ro_j1 else round(ro_j1["min_diagonal"], 4), f">= {DIAG_MIN}",
          bool(ro_j1) and ro_j1["min_diagonal"] >= DIAG_MIN)

    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report(f"{args.out}_hardware_2x2.md", report_text(args, R, data))
    print(R.criteria_table())
    print(f"\nJ1 N1 = {N1} of {pubs['J1']['shots']}: {decision}")
    return 0 if R.passed else 1


def report_text(args, R, D):
    prows = []
    for name in ("J1", "J2", "J3", "J4"):
        p = D["canary_pubs"].get(name)
        if not p:
            continue
        o = p.get("sampler_options") or {}
        dd = (o.get("dynamical_decoupling") or {})
        tw = (o.get("twirling") or {})
        prows.append([name,
                      (dd.get("sequence_type") or "on") if dd.get("enable") else "off",
                      ("on (" + str(tw.get("strategy")) + ")") if tw.get("enable_gates") else "off",
                      p["shots"], p["accepted"], f"{p['yield']:.4f}",
                      f"{p['clean_fraction_from_yield']:.4f}",
                      p["distinct_strings"], p["distinct_states"],
                      p["reference_string_count"],
                      str(p["rejections"]), f"{p['mixture']['c']:.4f}",
                      f"{p['mixture']['chi_square']:.2f}"])
    urows = [[k, ", ".join(str(i) for i in u["job_ids"]), ", ".join(str(s) for s in u["statuses"]),
              u["usage_s"], u["calibration_fingerprint"] and u["calibration_fingerprint"][:16],
              u["prereg_fingerprint_match"]]
             for k, u in sorted(D["jobs"].items())]
    t1rows, t2rows = [], []
    for name in sorted(D["idle_tests"]):
        t = D["idle_tests"][name]
        for q, v in sorted((t.get("t1w") or {}).get("per_qubit", {}).items(), key=lambda kv: int(kv[0])):
            t1rows.append([name, q, f"{v['raw_P_one']:.4f}",
                           "-" if v["P_survive"] is None else f"{v['P_survive']:.4f}",
                           f"{v['P_survive_predicted']:.4f}",
                           "-" if v["T1_measured_s"] is None else f"{v['T1_measured_s'] * 1e6:.1f}",
                           f"{v['T1_record_s'] * 1e6:.1f}",
                           "-" if v["rate_ratio"] is None else f"{v['rate_ratio']:.2f}",
                           "yes" if v["rate_within_band"] else "no"])
        for q, v in sorted((t.get("ramw") or {}).get("per_qubit", {}).items(), key=lambda kv: int(kv[0])):
            t2rows.append([name, q, f"{v['raw_P_zero']:.4f}",
                           "-" if v["P_zero"] is None else f"{v['P_zero']:.4f}",
                           f"{v['P_zero_bound_from_record']:.4f}",
                           "-" if v["T2star_measured_s"] is None
                           else f"{v['T2star_measured_s'] * 1e6:.1f}",
                           "-" if v["T2star_upper_bound_s"] is None
                           else f"{v['T2star_upper_bound_s'] * 1e6:.1f}",
                           f"{v['T2_record_s'] * 1e6:.1f}",
                           "yes" if v["within_bound"] else "no"])
    crows = [[k, f"{v['S_T1']:.3f}", f"{v['S_T2']:.3f}", f"{v['f_predicted']:.3e}",
              f"{v['yield_predicted']:.5f}", f"{v['yield_measured']:.5f}",
              "-" if v["ratio_measured_over_predicted"] is None
              else f"{v['ratio_measured_over_predicted']:.3f}",
              "yes" if v["within_factor"] else "no"]
             for k, v in sorted(D["postdiction"].items())]
    dec = D["decision"]
    hA, hB = dec.get("prediction_H_A") or {}, dec.get("prediction_H_B") or {}
    return f"""# Gate {R.gate} — the H0 diagnostic session on {D['backend']}

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/gate_H0_diag.py --prereg {args.prereg} --out {args.out}`.
{env_block()}  Runtime {R.runtime_s:.0f} s.  Total QPU usage of the session
**{D['total_usage_s']:.1f} s** (cap {D['criteria_inputs']['max_usage_session_s']:.0f} s).

Preregistration `{args.prereg}` (written {D['prereg_created']} at commit `{D['prereg_commit']}`) on the
calibration fingerprint **`{D['prereg_calibration']['fingerprint']}`**
({D['prereg_calibration']['backend']}, {D['prereg_calibration']['last_update_date']}).  The decision rule and
both predictions were fixed before any of these counts existed.

## 1. The decision

| | value |
|---|---|
| J1 accepted N1 of {dec['shots_J1']} | **{dec['N1']}** |
| preregistered H_A (idle relaxation, options off) | {hA.get('expected', float('nan')):.1f} +- {hA.get('sigma', float('nan')):.1f} |
| preregistered H_B (the options were the cause) | {hB.get('expected', float('nan')):.1f} +- {hB.get('sigma', float('nan')):.1f} |
| garbage floor (a = {D['garbage_acceptance']:.5f}) | {dec['garbage_floor_expected']:.1f} |
| rule | {dec['rule']} |
| **outcome** | **{dec['decision']}** |

Ratios between the cells of the factorial: {', '.join(f'{k} = {v:.3f}' if v is not None else f'{k} = n/a' for k, v in sorted(D['ratios'].items())) or 'only J1 was run'}.

## 2. The four canary pubs

{md_table(["job", "DD", "twirling", "shots", "accepted", "yield", "f from yield",
           "distinct strings", "distinct states", "reference string seen", "rejections",
           "mixture c", "chi-square (2 dof)"], prows)}

## 3. Jobs

{md_table(["job", "job id(s)", "status", "usage (s)", "calibration fingerprint",
           "prereg match"], urows)}

## 4. Windowed T1 test (`diag_patch1_t1w`)

{md_table(["job", "physical qubit", "raw P(1)", "P(1) readout-corrected", "P(1) predicted",
           "T1 measured (us)", "T1 record (us)", "rate ratio", "in band"], t1rows)}

## 5. Windowed Ramsey test (`diag_patch1_ramw`)

{md_table(["job", "physical qubit", "raw P(0)", "P(0) readout-corrected",
           "P(0) bound from the record", "T2* measured (us)", "T2* upper bound (us)",
           "T2 record (us)", "under the bound"], t2rows)}

## 6. Idle-aware post-diction with the measured coherence times

{md_table(["job", "S_T1", "S_T2", "f predicted", "yield predicted", "yield measured",
           "measured/predicted clean yield", "within a factor 3"], crows)}

## 7. Readout

Smallest confusion diagonal of patch 1 in J1: {('%.4f' % D['readout']['J1']['min_diagonal']) if D['readout'].get('J1') else 'n/a'}
(criterion >= {D['criteria_inputs']['confusion_diagonal_min']}).
{('Qubit 123: measured error %.5f against the record'
  ' %.5f, ratio %.2f (information, not a criterion).'
  % (D['readout_qubit_123']['measured_error'], D['readout_qubit_123']['record_error'],
     D['readout_qubit_123']['ratio'])) if D.get('readout_qubit_123') else ''}

## Criteria

{R.criteria_table()}

Every number above is computed by `scripts/gate_H0_diag.py` from the raw counts of the job directories
and from `{args.prereg}`, and is stored in `validation/{R.gate}.json`.  The counts files are never modified.
"""


if __name__ == "__main__":
    sys.exit(main())
