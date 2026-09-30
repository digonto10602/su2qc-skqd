#!/usr/bin/env python3
"""
Gate H0_model (prompts/20 part C) — the post-diction of the existing H0 hardware counts.

Gate H0_diag settled the CAUSE of the canary shortfall (idle-time relaxation; the SamplerV2
options were rejected at ~20 sigma) but not the SIZE, and the re-plan then found that the
accepted shots of the diagnostic are mostly NOT clean shots: pooled over the five hardware
pubs of the canary circuit the reference string was seen 6 times against a garbage
expectation of 2.02, so the clean-shot fraction on patch 1 is f_clean = 6.7e-4 where
inverting the accepted yield gives 0.0101 -- a 15x bias
(`reports/H0_replan_planner_analysis_20260922.md` section 2).

This gate is the post-diction the project owes itself before it spends another QPU second.
It takes the counts that already exist -- 15.0 s of diagnostic and 2.0 s of canary, nothing
new -- and asks whether the corrected model reproduces them:

  C1  the clean-yield ESTIMATOR is unbiased where the truth is known.  On two seeded Aer
      samples of the canary circuit (FakeFez, 2000 shots, scheduled and unscheduled) the
      maximum-likelihood mixture estimate of the clean accepted count is compared with the
      reference-count estimate n_ref / p_ref on the SAME sample.  Within 25 % on both.
  C2  the device counts carry a clean component at all: P(>= 6 reference hits | garbage) of
      the pooled five-pub test is below 0.05.
  C3  the bracket post-diction.  Aer on the SCHEDULED canary circuit, against the live
      calibration record the device actually ran under (fingerprint 7fd6d65e...), at both
      ends of the dephasing bracket: the record's Hahn-echo T2, and the free-induction T2*
      measured by the diagnostic's windowed Ramsey pub (rule M-T2,
      `scripts/h0_t2_override.py`).  The criterion is on the T2* end: its predicted clean
      reference hits, scaled to the 8267 hardware shots, must lie within a factor 3 of the
      measured 4.0.  The echo end is computed by the same code and recorded with its ratio.
  C4  the acceptance structure: the T2* end's predicted accepted count for 2000 shots within
      a factor 2 of J1's 35.  The Hamming-distance histogram is chi-squared against J1's and
      reported as information.

Status PASS iff C1, C2, C3 and C4.  If C3 fails at BOTH ends the bracket does not contain the
device and the planner returns (prompts/20 escalation); nothing here is tuned to make it pass.

No QPU time.  The hardware counts are read-only and never modified; the Aer samples this gate
draws are written once to `data/hardware/H0_model/` with their settings and are refused rather
than overwritten.

Usage (the sampling is split so that no invocation approaches the 30-minute rule):
  python scripts/gate_H0_model.py --sample echo   --chunk 0     # ~2 min each
  python scripts/gate_H0_model.py --sample t2star --chunk 0
  ...
  python scripts/gate_H0_model.py                               # the analysis and the gate
"""
import argparse
import glob
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import ideal_sector_distribution  # noqa: E402
from skqd.reference_sim import qiskit_key_to_bits  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import (READOUT_FACTOR, clean_fraction_mixture,  # noqa: E402
                       pooled_reference_string_test, reference_string_test)

from gate_H0P import (SCHEDULE_SEED, apply_t2_override, clean_statistics,  # noqa: E402
                      load_circuit, load_index, load_manifests, load_t2_override,
                      random_acceptance, schedule_circuit)
from h0_backends import backend_from_record  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PREP = os.path.join("data", "hardware", "H0_prep")
DEFAULT_CIRCUIT = "B0_ref06_k1_rep1"
DEFAULT_RECORD = os.path.join("data", "hardware", "H0_ibm_fez",
                              "calibration_20260922T1400Z.json")
DEFAULT_OVERRIDE = os.path.join("data", "hardware", "H0_model", "t2_override_J1_ramw.json")
DEFAULT_OUTDIR = os.path.join("data", "hardware", "H0_model")
# the five hardware pubs of the canary circuit: 2.0 s of canary + 15.0 s of diagnostic
HARDWARE_JOBS = ("H0_ibm_fez_canary", "H0_diag_J1", "H0_diag_J2", "H0_diag_J3", "H0_diag_J4")
ENDS = ("echo", "t2star")

# ---- criteria constants, fixed by prompts/20 part C before any of the numbers were computed
C1_TOLERANCE = 0.25        # mixture vs reference-count estimate of the clean accepted shots
C2_P_MAX = 0.05            # the pooled reference test must reject the pure-garbage null
C3_FACTOR = 3.0            # the T2* end's clean reference hits within this factor of measured
C4_FACTOR = 2.0            # the T2* end's accepted count within this factor of J1's 35
J1_ACCEPTED = 35           # validation/H0_diag.json:data.decision (2000 shots, DD off, tw off)
J1_DISTANCE_HISTOGRAM = [2, 0, 13, 5, 1, 6, 0, 5, 0]


# --------------------------------------------------------------------------- shared pieces
def canary_manifest(prep, circuit_id):
    mans, _cals = load_manifests(prep)
    man = next((m for m in mans if m["id"] == circuit_id), None)
    if man is None:
        raise SystemExit(f"no circuit '{circuit_id}' in {prep}")
    return man, load_index(prep)


def decode_histogram(counts, codec, dist, pos, twoB, n_bins):
    """(per-sector-position counts, Hamming-distance histogram, shots) of one counts dict."""
    from skqd.codec import Reject
    shots = int(sum(counts.values()))
    n = np.zeros(len(pos))
    hist = np.zeros(n_bins)
    for key, c in counts.items():
        bits = qiskit_key_to_bits(key) if isinstance(key, str) else key
        try:
            b, _ = codec.decode(bits, twoB)
        except Reject:
            continue
        n[pos[int(b)]] += int(c)
        hist[dist[int(b)]] += int(c)
    return n, hist, shots


def geometry(model, man, g2):
    """The ideal distribution, the position map and the Hamming distances to the reference."""
    codec = Codec(model.basis)
    d = ideal_sector_distribution(model, g2, int(man["twoB"]), int(man["reference"]),
                                  int(man["k"]), float(man["dt"]), int(man["repetitions"]))
    pos = {int(b): i for i, b in enumerate(d["sector_indices"])}
    refbits = tuple(int(x) for x in codec.encode(model.basis.labels[int(man["reference"])]))
    dist = {int(b): int(sum(x != y for x, y in
                            zip(codec.encode(model.basis.labels[int(b)]), refbits)))
            for b in d["sector_indices"]}
    return codec, d, pos, dist


# --------------------------------------------------------------------------- sampling phase
def chunk_seed(seed_base, chunk, shots_per_chunk):
    """The seed of chunk `i`, so that the chunks together ARE one seeded run.

    Measured on this stack (qiskit-aer 0.17.2, statevector method with a noise model):
    AerSimulator seeds the noise trajectory of shot j with `seed_simulator + j`, so two runs
    whose seeds differ by 1 share all but one of their shots -- `200 shots at seed 12` is
    `200 shots at seed 11` with the first shot dropped and one new shot added (2 differing
    keys of 200).  Offsetting by the chunk's own shot count instead makes the shot streams
    contiguous and disjoint, and it was verified bit for bit that

        200 shots at seed 11  +  200 shots at seed 211  ==  400 shots at seed 11

    (0 differing keys).  So `--chunks 4 --shots-per-chunk 2000 --seed 11` is exactly one
    8000-shot run at seed_simulator = 11, split only to respect the 30-minute rule."""
    return int(seed_base) + int(chunk) * int(shots_per_chunk)


def chunk_path(outdir, end, chunk, seed, shots):
    return os.path.join(outdir, f"aer_{end}_chunk{chunk}_seed{seed}_{shots}shots.json")


def sample_chunk(args, end, chunk, prep, man, record, override):
    """One seeded Aer invocation: the scheduled canary circuit at one end of the bracket."""
    from qiskit_aer import AerSimulator
    outdir = os.path.join(ROOT, args.outdir)
    os.makedirs(outdir, exist_ok=True)
    seed = chunk_seed(args.seed, chunk, args.shots_per_chunk)
    path = chunk_path(outdir, end, chunk, seed, int(args.shots_per_chunk))
    if os.path.exists(path):
        print(f"{os.path.relpath(path, ROOT)} exists: counts files are write-once, not re-drawn")
        return path
    t0 = time.time()
    backend, binfo = backend_from_record(record)
    t2_table = None
    if end == "t2star":
        t2_table = apply_t2_override(backend, override)
        t2_table["file"] = args.t2_override
    sim = AerSimulator.from_backend(backend, seed_simulator=seed)
    qc = load_circuit(prep, man)
    sched, sinfo = (schedule_circuit(qc, backend) if args.schedule == "asap" else (qc, None))
    ts = time.time()
    counts = sim.run(sched, shots=int(args.shots_per_chunk)).result().get_counts()
    seconds = time.time() - ts
    rec = {
        "gate": "H0_model", "end": end, "chunk": int(chunk),
        "circuit": man["id"], "shots": int(args.shots_per_chunk),
        "schedule": args.schedule, "seed_simulator": seed, "seed_base": int(args.seed),
        "seed_transpiler": SCHEDULE_SEED if args.schedule == "asap" else None,
        "simulator": f"AerSimulator.from_backend(backend_from_record({args.record}), "
                     f"seed_simulator={seed})",
        "backend_from_record": binfo,
        "record": args.record,
        "record_fingerprint": record.get("fingerprint"),
        "t2_override": t2_table,
        "schedule_info": sinfo,
        "seconds": seconds, "total_seconds": time.time() - t0,
        "when": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "counts": {str(k): int(v) for k, v in counts.items()},
    }
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(tmp, path)
    print(f"{end} chunk {chunk} (seed {seed}): {int(args.shots_per_chunk)} shots in "
          f"{seconds:.0f} s -> {os.path.relpath(path, ROOT)}")
    return path


def load_chunks(outdir, end, seed_base, shots, chunks):
    """Every chunk of one end, refusing a partial set (the gate needs all 4 x shots)."""
    out = []
    for c in range(int(chunks)):
        p = chunk_path(outdir, end, c, chunk_seed(seed_base, c, shots), int(shots))
        if not os.path.exists(p):
            return None, os.path.relpath(p, ROOT)
        with open(p) as fh:
            out.append(json.load(fh))
    return out, None


# --------------------------------------------------------------------------- C1
def c1_from_cache(cache_dir, prep, model, g2, label):
    """The two estimators on one seeded Aer sample, read from a gate_H0P sampling cache.

    The cache is written by `gate_H0P.py --sample-only --sample-cache <dir>` (prompts/20 B4):
    `<sector>_r<r>.json` carries the seeded counts and the settings they were drawn under."""
    d = cache_dir if os.path.isabs(cache_dir) else os.path.join(ROOT, cache_dir)
    files = sorted(glob.glob(os.path.join(d, "B=*_r*.json")))
    if not files:
        raise SystemExit(f"no sampling cache in {cache_dir}: run prompts/20 B4 first "
                         f"(gate_H0P.py --sample-only --sample-cache {cache_dir})")
    mans, _ = load_manifests(prep)
    by_id = {m["id"]: m for m in mans}
    records, settings = [], None
    for f in files:
        with open(f) as fh:
            rec = json.load(fh)
        settings = settings or {k: rec.get(k) for k in
                                ("backend", "seed", "schedule", "t2_override_sha",
                                 "t2_override_file", "calibration_fingerprint",
                                 "calibration_fingerprint_source")}
        for cid, counts in rec["counts"].items():
            records.append((by_id[cid], {qiskit_key_to_bits(k): int(v)
                                         for k, v in counts.items()}))
    codec = Codec(model.basis)
    acc = {m["sector"]: random_acceptance(codec, m["twoB"])["fraction"] for m, _ in records}
    cs = clean_statistics(records, model, g2, acc)
    rows = []
    for cid, v in sorted(cs["per_circuit"].items()):
        n_over_p = v["reference_hits"] / v["p_reference"]
        mix = v["mixture"]["clean_accepted"]
        rows.append({
            "circuit": cid, "shots": v["shots"], "accepted": v["accepted"],
            "reference_hits": v["reference_hits"], "p_reference": v["p_reference"],
            "clean_accepted_mixture": mix,
            "clean_accepted_reference_count": n_over_p,
            "clean_accepted_reference_count_garbage_corrected":
                v["reference_string_test"]["excess"] / v["p_reference"],
            "ratio_mixture_over_reference": (mix / n_over_p) if n_over_p else None,
            "relative_deviation": (abs(mix - n_over_p) / n_over_p) if n_over_p else None,
            "near_clean_accepted": v["near_clean_accepted"],
            "expected_garbage_accepted": v["expected_garbage_accepted"],
            "f_clean_mixture": v["mixture"]["f_clean"],
            "f_clean_reference": v["reference_string_test"]["f_clean"],
            "distance_histogram": v["distance_histogram"],
            "w": v["mixture"]["w"], "w_68": v["mixture"]["w_68"],
        })
    return {"label": label, "cache": cache_dir, "settings": settings,
            "n_circuits": len(rows), "per_circuit": rows,
            "worst_relative_deviation": max((r["relative_deviation"] for r in rows
                                             if r["relative_deviation"] is not None),
                                            default=None)}


# --------------------------------------------------------------------------- C2
def c2_hardware(prep, model, g2, man, jobs):
    """P8 of the planner analysis, recomputed: the five pubs and the pooled reference test."""
    codec, d, pos, dist = geometry(model, man, g2)
    a = random_acceptance(codec, int(man["twoB"]))["fraction"]
    n_bins = len(dist) and max(dist.values()) + 1
    n_bins = max(n_bins, 9)
    rows, ref_rows, mix_rows = [], [], []
    for job in jobs:
        p = os.path.join(ROOT, "data", "hardware", job, "counts", f"{man['id']}.json")
        if not os.path.exists(p):
            raise SystemExit(f"no hardware counts for {man['id']} in {job}: {p}")
        with open(p) as fh:
            blob = json.load(fh)
        n, hist, shots = decode_histogram(blob["counts"], codec, dist, pos,
                                          int(man["twoB"]), n_bins)
        accepted = float(n.sum())
        n_ref = int(round(float(n[d["reference_position"]])))
        excess = accepted - shots * a
        expected_if_clean = excess * d["p_reference"] + shots * a / d["dim"]
        from scipy.stats import poisson
        mix = clean_fraction_mixture(n, d["p"], d["dim"], shots)
        rows.append({
            "job": job, "options": blob.get("sampler_options"),
            "shots": shots, "accepted": int(accepted),
            "garbage_floor": float(shots * a), "excess_accepted": float(excess),
            "reference_hits": n_ref,
            "expected_reference_hits_if_the_excess_were_clean": float(expected_if_clean),
            "P_le_seen": (float(poisson.cdf(n_ref, expected_if_clean))
                          if expected_if_clean > 0 else None),
            "reference_string_test": reference_string_test(n_ref, shots, d["p_reference"],
                                                           a, d["dim"]),
            "mixture": mix,
            "distance_histogram": [int(x) for x in hist[:9]],
        })
        ref_rows.append((n_ref, shots, float(d["p_reference"]), a, d["dim"]))
        mix_rows.append((n, d["p"]))
    pooled = pooled_reference_string_test(ref_rows)
    pooled_mix = clean_fraction_mixture(np.array([m[0] for m in mix_rows]),
                                        np.array([m[1] for m in mix_rows]),
                                        d["dim"], sum(r[1] for r in ref_rows))
    return {"jobs": list(jobs), "garbage_acceptance": a, "dim": d["dim"],
            "p_reference": float(d["p_reference"]),
            "ideal_by_distance": [float(x) for x in
                                  np.bincount([dist[b] for b in d["sector_indices"]],
                                              weights=d["p"], minlength=n_bins)[:9]],
            "per_pub": rows, "pooled_reference_test": pooled,
            "pooled_mixture": pooled_mix}


# --------------------------------------------------------------------------- C3 / C4
def postdiction(chunks, model, g2, man, hardware_shots, measured_clean_hits):
    """One end of the bracket: the pooled Aer prediction and the two ratios."""
    codec, d, pos, dist = geometry(model, man, g2)
    a = random_acceptance(codec, int(man["twoB"]))["fraction"]
    n_bins = max(max(dist.values()) + 1, 9)
    tot_n = np.zeros(d["dim"])
    tot_hist = np.zeros(n_bins)
    shots = 0
    per_chunk, mix_rows = [], []
    for ch in chunks:
        n, hist, sh = decode_histogram(ch["counts"], codec, dist, pos, int(man["twoB"]), n_bins)
        tot_n = tot_n + n
        tot_hist = tot_hist + hist
        shots += sh
        per_chunk.append({"chunk": ch["chunk"], "seed_simulator": ch["seed_simulator"],
                          "shots": sh, "accepted": int(n.sum()),
                          "reference_hits": int(round(float(n[d["reference_position"]]))),
                          "seconds": ch.get("seconds")})
        mix_rows.append((n, d["p"]))
    accepted = float(tot_n.sum())
    n_ref = int(round(float(tot_n[d["reference_position"]])))
    rst = reference_string_test(n_ref, shots, d["p_reference"], a, d["dim"])
    mix = clean_fraction_mixture(np.array([m[0] for m in mix_rows]),
                                 np.array([m[1] for m in mix_rows]), d["dim"], shots)
    scale = float(hardware_shots) / shots
    clean_hits = rst["excess"] * scale
    obs = tot_hist[:9]
    exp = np.array(J1_DISTANCE_HISTOGRAM, dtype=float) * (accepted / max(sum(J1_DISTANCE_HISTOGRAM), 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        chi = float(np.nansum(np.where(exp > 0, (obs - exp) ** 2 / exp, 0.0)))
    return {
        "shots": shots, "chunks": per_chunk, "accepted": int(accepted),
        "reference_hits": n_ref,
        "expected_reference_hits_from_garbage": rst["expected_from_garbage"],
        "clean_reference_hits": float(rst["excess"]),
        "clean_reference_hits_scaled_to_hardware": float(clean_hits),
        "hardware_shots": int(hardware_shots),
        "measured_clean_reference_hits": float(measured_clean_hits),
        "ratio_predicted_over_measured": (float(clean_hits / measured_clean_hits)
                                          if measured_clean_hits else None),
        "reference_string_test": rst, "mixture": mix,
        "f_clean_reference": rst["f_clean"], "f_clean_mixture": mix["f_clean"],
        "accepted_per_2000_shots": float(accepted * 2000.0 / shots),
        "ratio_accepted_over_J1": float(accepted * 2000.0 / shots / J1_ACCEPTED),
        "distance_histogram": [int(x) for x in obs],
        "distance_histogram_J1": list(J1_DISTANCE_HISTOGRAM),
        "distance_chi_square_vs_J1": chi,
        "distance_chi_square_note": ("J1's histogram normalised to this sample's accepted "
                                     "count; information only, no criterion"),
    }


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=DEFAULT_PREP)
    ap.add_argument("--circuit", default=DEFAULT_CIRCUIT)
    ap.add_argument("--record", default=DEFAULT_RECORD,
                    help="the live calibration record the device ran under (prompts/20 C3)")
    ap.add_argument("--t2-override", default=DEFAULT_OVERRIDE,
                    help="the per-qubit T2* table of scripts/h0_t2_override.py")
    ap.add_argument("--outdir", default=DEFAULT_OUTDIR,
                    help="where the Aer sample counts of C3 are written (write-once)")
    ap.add_argument("--schedule", default="asap", choices=("none", "asap"))
    ap.add_argument("--seed", type=int, default=11, help="base seed; chunk i uses seed + i")
    ap.add_argument("--shots-per-chunk", type=int, default=2000)
    ap.add_argument("--chunks", type=int, default=4)
    ap.add_argument("--sample", default=None, choices=("echo", "t2star", "all"),
                    help="sampling phase: draw the missing chunks of this end and exit")
    ap.add_argument("--chunk", type=int, default=None,
                    help="with --sample: draw only this chunk (the 30-minute rule)")
    ap.add_argument("--c1-cache-scheduled",
                    default=os.path.join("data", "hardware", "H0_model", "cache_asap_echo"),
                    help="gate_H0P sampling cache of the SCHEDULED FakeFez sample (B4)")
    ap.add_argument("--c1-cache-unscheduled",
                    default=os.path.join("data", "hardware", "H0_model",
                                         "cache_none_snapshot"),
                    help="gate_H0P sampling cache of the UNSCHEDULED FakeFez sample (B4)")
    ap.add_argument("--jobs", nargs="*", default=list(HARDWARE_JOBS))
    ap.add_argument("--out", default="H0_model")
    args = ap.parse_args()
    t0 = time.time()

    prep = os.path.join(ROOT, args.prep) if not os.path.isabs(args.prep) else args.prep
    man, index = canary_manifest(prep, args.circuit)
    g2 = index["common"]["g2"]
    M = Model(int(index["common"]["lattice"].split("x")[1]))
    rp = args.record if os.path.isabs(args.record) else os.path.join(ROOT, args.record)
    with open(rp) as fh:
        record = json.load(fh)
    override, override_sha = load_t2_override(args.t2_override)

    if args.sample:
        ends = ENDS if args.sample == "all" else (args.sample,)
        chunks = ([int(args.chunk)] if args.chunk is not None
                  else list(range(int(args.chunks))))
        for end in ends:
            for c in chunks:
                sample_chunk(args, end, c, prep, man, json.loads(json.dumps(record)), override)
        print(f"{time.time() - t0:.0f} s")
        return 0

    R = GateResult(args.out,
                   "post-diction of the H0 hardware counts by the scheduled-Aer model at both "
                   "ends of the T2 bracket; the clean-yield statistic")

    # -------------------------------------------------------------- C1
    c1 = {lab: c1_from_cache(d, prep, M, g2, lab) for lab, d in
          (("scheduled", args.c1_cache_scheduled),
           ("unscheduled", args.c1_cache_unscheduled))}
    # -------------------------------------------------------------- C2
    c2 = c2_hardware(prep, M, g2, man, args.jobs)
    measured = c2["pooled_reference_test"]["excess"]
    # -------------------------------------------------------------- C3 / C4
    outdir = os.path.join(ROOT, args.outdir)
    post, missing = {}, {}
    for end in ENDS:
        ch, miss = load_chunks(outdir, end, args.seed, args.shots_per_chunk, args.chunks)
        if ch is None:
            missing[end] = miss
            continue
        post[end] = postdiction(ch, M, g2, man, c2["pooled_reference_test"]["shots"], measured)
    if missing:
        raise SystemExit(
            "the post-diction needs every Aer chunk of both ends; missing e.g. "
            + ", ".join(f"{k}: {v}" for k, v in missing.items())
            + f".  Draw them with: python scripts/gate_H0_model.py --sample <end> --chunk <i> "
              f"({args.chunks} chunks x {args.shots_per_chunk} shots per end).")

    lo, hi = 1.0 / C3_FACTOR, C3_FACTOR
    t2 = post["t2star"]
    echo = post["echo"]

    data = {
        "question": ("does the corrected model -- Aer on the SCHEDULED circuit, at a measured "
                     "dephasing time, read with the clean-yield statistic -- reproduce the "
                     "hardware counts that already exist?"),
        "circuit": man["id"], "cz": man["cz"], "sector": man["sector"],
        "prep": args.prep, "record": args.record,
        "record_fingerprint": record.get("fingerprint"),
        "record_stamp": record.get("stamp"),
        "record_last_update_date": record.get("last_update_date"),
        "t2_override_file": args.t2_override, "t2_override_sha256": override_sha,
        "t2_override_rule": override.get("rule"),
        "t2_override_source": override.get("source"),
        "t2_override_table": override.get("table"),
        "t2_override_provenance_counts": override.get("provenance_counts"),
        "aer_settings": {
            "schedule": args.schedule, "seed_transpiler": SCHEDULE_SEED,
            "seed_base": int(args.seed),
            "seeds": [chunk_seed(args.seed, c, args.shots_per_chunk)
                      for c in range(int(args.chunks))],
            "shots_per_chunk": int(args.shots_per_chunk), "chunks": int(args.chunks),
            "shots_per_end": int(args.shots_per_chunk) * int(args.chunks),
            "backend": ("AerSimulator.from_backend(h0_backends.backend_from_record(record, "
                        "base=FakeFez())) -- the record's 30 x 9 qubit and 54 x 4 edge leaves "
                        "written into a FakeFez target, fingerprint asserted equal to the "
                        "record's"),
            "seed_note": ("chunk i runs at seed_simulator = seed + i * shots_per_chunk, so "
                          "the four invocations ARE one 8000-shot run at seed_simulator = 11: "
                          "qiskit-aer seeds the noise trajectory of shot j with "
                          "seed_simulator + j, verified bit for bit by 200@11 + 200@211 == "
                          "400@11 (0 differing keys).  Consecutive seeds would have shared all "
                          "but one shot -- 11 and 12 differ in 2 of 200 keys -- which is why "
                          "the offset is the chunk's shot count and not 1."),
            "counts_files": sorted(os.path.relpath(p, ROOT) for p in
                                   glob.glob(os.path.join(outdir, "aer_*.json"))),
        },
        "C1_estimator_validation": c1,
        "C2_pooled_device_clean_count": c2,
        "C3_bracket_postdiction": post,
        "criteria_inputs": {
            "C1_tolerance": C1_TOLERANCE, "C2_P_max": C2_P_MAX,
            "C3_factor": C3_FACTOR, "C3_window": [lo * measured, hi * measured],
            "C4_factor": C4_FACTOR, "J1_accepted": J1_ACCEPTED,
            "readout_factor": READOUT_FACTOR,
            "measured_clean_reference_hits": float(measured),
        },
        "runtimes": {"analysis_s": None},
    }

    # -------------------------------------------------------------- criteria
    for lab in ("unscheduled", "scheduled"):
        v = c1[lab]
        row = v["per_circuit"][0]
        R.add(f"C1 {lab} Aer sample ({row['shots']} shots, seed {v['settings'].get('seed')}): "
              f"the mixture estimate of the clean accepted shots "
              f"{row['clean_accepted_mixture']:.1f} against the reference-count estimate "
              f"n_ref / p_ref = {row['clean_accepted_reference_count']:.1f} "
              f"(near-clean {row['near_clean_accepted']:.1f}, garbage "
              f"{row['expected_garbage_accepted']:.1f})",
              round(row["relative_deviation"], 4),
              f"relative deviation <= {C1_TOLERANCE:.2f}",
              row["relative_deviation"] <= C1_TOLERANCE)
    p = c2["pooled_reference_test"]
    R.add(f"C2 the device counts carry a clean component: {p['n_reference']} reference-string "
          f"hits over {p['shots']} shots of {p['circuits']} pubs against a garbage expectation "
          f"of {p['expected_from_garbage']:.3f} ({p['z']:.2f} sigma; clean "
          f"{p['excess']:.1f} shots, f_clean {p['f_clean']:.3e})",
          round(p["P_ge"], 4), f"P(>= n | garbage) < {C2_P_MAX:.2f}", p["P_ge"] < C2_P_MAX)
    R.add(f"C3 the T2* end of the bracket post-dicts the measured clean count: predicted "
          f"{t2['clean_reference_hits_scaled_to_hardware']:.2f} clean reference hits over "
          f"{t2['hardware_shots']} shots against the measured {measured:.2f} "
          f"(echo end {echo['clean_reference_hits_scaled_to_hardware']:.2f}, ratio "
          f"{echo['ratio_predicted_over_measured']:.2f})",
          round(t2["ratio_predicted_over_measured"], 4),
          f"predicted / measured in [{lo:.2f}, {hi:.2f}]",
          lo <= t2["ratio_predicted_over_measured"] <= hi)
    R.add(f"C4 the T2* end reproduces the acceptance structure: predicted "
          f"{t2['accepted_per_2000_shots']:.1f} accepted shots per 2000 against J1's "
          f"{J1_ACCEPTED} (echo end {echo['accepted_per_2000_shots']:.1f}; distance "
          f"chi-square vs J1 {t2['distance_chi_square_vs_J1']:.1f}, information)",
          round(t2["ratio_accepted_over_J1"], 4),
          f"predicted / measured in [{1 / C4_FACTOR:.2f}, {C4_FACTOR:.0f}]",
          1 / C4_FACTOR <= t2["ratio_accepted_over_J1"] <= C4_FACTOR)

    data["runtimes"]["analysis_s"] = time.time() - t0
    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report("H0_model_postdiction_2x2.md", report_text(args, R, data))
    print(R.criteria_table())
    if not R.passed and not (lo <= t2["ratio_predicted_over_measured"] <= hi) and \
            not (lo <= echo["ratio_predicted_over_measured"] <= hi):
        print("\nBOTH ends of the bracket miss the measured clean count by more than a factor "
              f"{C3_FACTOR:.0f} (T2* {t2['ratio_predicted_over_measured']:.2f}, echo "
              f"{echo['ratio_predicted_over_measured']:.2f}): prompts/20 escalation -- neither "
              "end describes the device, write validation/BLOCKED.md and stop.  Nothing here "
              "is tuned to make it pass.")
    return 0 if R.passed else 1


# --------------------------------------------------------------------------- report
def report_text(args, R, D):
    c1rows = []
    for lab in ("unscheduled", "scheduled"):
        v = D["C1_estimator_validation"][lab]
        for r in v["per_circuit"]:
            c1rows.append([lab, r["circuit"], r["shots"], r["accepted"], r["reference_hits"],
                           f"{r['clean_accepted_mixture']:.1f}",
                           f"{r['clean_accepted_reference_count']:.1f}",
                           f"{r['clean_accepted_reference_count_garbage_corrected']:.1f}",
                           f"{r['relative_deviation']:.3f}",
                           f"{r['near_clean_accepted']:.1f}",
                           f"{r['expected_garbage_accepted']:.1f}",
                           f"{r['f_clean_mixture']:.3e}", f"{r['f_clean_reference']:.3e}"])
    nc_frac = " and ".join(
        f"{100 * D['C1_estimator_validation'][lab]['per_circuit'][0]['near_clean_accepted'] / max(D['C1_estimator_validation'][lab]['per_circuit'][0]['accepted'], 1):.0f} %"
        for lab in ("unscheduled", "scheduled"))
    c2 = D["C2_pooled_device_clean_count"]
    c2rows = []
    for r in c2["per_pub"]:
        c2rows.append([r["job"], r["shots"], r["accepted"], f"{r['garbage_floor']:.1f}",
                       f"{r['excess_accepted']:.1f}", r["reference_hits"],
                       f"{r['expected_reference_hits_if_the_excess_were_clean']:.1f}",
                       ("-" if r["P_le_seen"] is None else f"{r['P_le_seen']:.2e}"),
                       str(r["distance_histogram"]),
                       f"{r['mixture']['w']:.3f}",
                       f"{r['mixture']['f_clean']:.2e}"])
    p = c2["pooled_reference_test"]
    c2rows.append(["**pooled**", p["shots"], "-", f"{p['expected_from_garbage']:.2f}", "-",
                   p["n_reference"], f"{p['expected_from_garbage']:.2f}",
                   f"P(>=) {p['P_ge']:.4f}", "-",
                   f"{c2['pooled_mixture']['w']:.3f}", f"{p['f_clean']:.2e}"])
    prows = []
    for end in ("echo", "t2star"):
        v = D["C3_bracket_postdiction"][end]
        prows.append([("record Hahn-echo T2" if end == "echo" else "measured free-induction T2*"),
                      v["shots"], v["accepted"], v["reference_hits"],
                      f"{v['expected_reference_hits_from_garbage']:.2f}",
                      f"{v['clean_reference_hits']:.2f}",
                      f"{v['clean_reference_hits_scaled_to_hardware']:.2f}",
                      f"{v['ratio_predicted_over_measured']:.2f}",
                      f"{v['f_clean_reference']:.3e}", f"{v['f_clean_mixture']:.3e}",
                      f"{v['accepted_per_2000_shots']:.1f}",
                      f"{v['ratio_accepted_over_J1']:.2f}",
                      str(v["distance_histogram"])])
    trows = [[r["qubit"], r["logical"],
              ("-" if not r["T2star_measured_s"] else f"{r['T2star_measured_s'] * 1e6:.1f}"),
              ("-" if not r["T2star_upper_bound_s"] else f"{r['T2star_upper_bound_s'] * 1e6:.1f}"),
              f"{r['T2_record_echo_s'] * 1e6:.1f}", f"{r['T2_used_s'] * 1e6:.1f}",
              r["provenance"],
              ("-" if not r["echo_over_used"] else f"{r['echo_over_used']:.1f}")]
             for r in D["t2_override_table"]]
    ci = D["criteria_inputs"]
    return f"""# Gate {R.gate} — post-diction of the H0 hardware counts at both ends of the T2 bracket

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/gate_H0_model.py`, circuit
`{D['circuit']}` ({D['cz']} CZ, {D['sector']}), calibration record `{D['record']}`
(fingerprint `{(D['record_fingerprint'] or '')[:16]}`, {D['record_last_update_date']}).
{env_block()}  Runtime {R.runtime_s:.0f} s.  **No QPU time**: the hardware counts are the
2.0 s canary and the 15.0 s diagnostic already on disk, read-only.

The question is not whether the device performed: gate H0_diag settled that.  It is whether
the corrected model — Aer on the **scheduled** circuit, at a **measured** dephasing time, read
with the **clean-yield** statistic — reproduces the counts that already exist.  All three
corrections are needed: the unscheduled simulation has no idle windows at all, the record has
no free-induction T2, and the accepted-shot yield counts near-clean strings as clean.

## 1. C1 — is the estimator unbiased where the truth is known?

Two seeded Aer samples of the same circuit on the FakeFez snapshot, 2000 shots each, one
scheduled and one not.  The mixture estimator uses the whole accepted histogram; the
reference-count estimator uses one number.  They must agree, because on this circuit the
reference string carries {c2['p_reference']:.4f} of the ideal output.

{md_table(["sample", "circuit", "shots", "accepted", "reference hits", "clean (mixture)",
           "clean (n_ref / p_ref)", "clean (garbage-corrected)", "relative deviation",
           "near-clean", "garbage", "f_clean (mixture)", "f_clean (reference)"], c1rows)}

The near-clean column is the residual of the amended Step-4.4 model (decision M4.4):
accepted − clean − N a (1 − f).  It is {nc_frac} of the accepted shots of the unscheduled and of
the scheduled sample respectively — which is why the accepted count is not a clean-shot
measurement on the simulator either, not only on the device.

## 2. C2 — do the device counts carry a clean component at all?

The five hardware pubs of this circuit (canary + the four diagnostic option cells), decoded
here from the raw counts.  "expected if clean" is what the reference-string count would be if
the accepted shots above the garbage floor were clean shots; `P(<= seen)` is the Poisson
probability of seeing no more than the observed number under that hypothesis.

{md_table(["job", "shots", "accepted", "garbage floor N a", "excess", "reference hits",
           "expected if the excess were clean", "P(<= seen)", "distance histogram d = 0..8",
           "w (mixture)", "f_clean (mixture)"], c2rows)}

Ideal mass by Hamming distance to the reference codeword: {[round(x, 3) for x in c2['ideal_by_distance']]};
the decoder's exhaustive random-string acceptance of this sector is {c2['garbage_acceptance']:.5f}
over {c2['dim']} codewords.  Pooled: **{p['n_reference']} reference hits over {p['shots']} shots
against {p['expected_from_garbage']:.3f} expected from garbage**, P = {p['P_ge']:.4f}, i.e. a clean
component of **{p['excess']:.1f} shots** and f_clean = **{p['f_clean']:.3e}**
(1 sigma {p['f_clean_68_sqrt_n'][0]:.2e} – {p['f_clean_68_sqrt_n'][1]:.2e}).

## 3. C3 / C4 — the bracket post-diction

Aer on the scheduled circuit against the record the device ran under, once with the record's
Hahn-echo T2 and once with the free-induction T2* of the diagnostic's windowed Ramsey pub.
{D['aer_settings']['shots_per_end']} shots per end in {D['aer_settings']['chunks']} invocations of
{D['aer_settings']['shots_per_chunk']} (seeds {D['aer_settings']['seeds']}).

{md_table(["dephasing time", "shots", "accepted", "reference hits", "garbage expectation",
           "clean reference hits", "scaled to the 8267 hardware shots",
           "predicted / measured", "f_clean (reference)", "f_clean (mixture)",
           "accepted per 2000 shots", "accepted / J1's 35", "distance histogram"], prows)}

Criterion C3 is on the T2* end: its predicted clean reference hits, scaled to the hardware's
{p['shots']} shots, must lie in [{ci['C3_window'][0]:.2f}, {ci['C3_window'][1]:.2f}] — a factor
{ci['C3_factor']:.0f} of the measured {ci['measured_clean_reference_hits']:.2f}.  The echo end is
computed by the same code and reported with its ratio; it is not a criterion, because the
record's echo T2 is not the time the circuit's unrefocused idle windows see.

## 4. The T2 table and its provenance

Rule M-T2: the measured T2* where the readout-corrected inversion resolves it, else the
3 sigma upper bound, else the smallest resolved value on the patch.  Source:
`{D['t2_override_source']}`.

{md_table(["physical qubit", "logical", "T2* measured (us)", "3 sigma bound (us)",
           "T2 echo, record (us)", "T2 used (us)", "provenance", "echo / used"], trows)}

{D['t2_override_provenance_counts']['measured']} measured,
{D['t2_override_provenance_counts']['upper_bound']} upper bounds,
{D['t2_override_provenance_counts']['patch_minimum']} at the patch minimum.

## Criteria

{R.criteria_table()}

Every number above is computed by `scripts/gate_H0_model.py` and stored in
`validation/{R.gate}.json`.  The hardware counts in `data/hardware/H0_*/counts/` are never
modified; the Aer counts of section 3 are written once to `{args.outdir}` with the settings
they were drawn under and are refused rather than re-drawn.
"""


if __name__ == "__main__":
    sys.exit(main())
