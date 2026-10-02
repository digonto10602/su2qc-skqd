#!/usr/bin/env python3
"""
Gate H0_kpilot (prompts/21) -- the ibm_kingston pilot: the in-circuit T2*/T2_echo ratio on the
patch the day's calibration selects, and the direct f_clean of the best schedulable SIGNED
circuit, read against the preregistered GO / NO-GO rule.

A measurement gate: PASS = preregistered, measured, verified, consistent.  There is no
criterion on f, r_eff or the decision itself -- a NO-GO pilot is a PASS gate.

Stages (all 0 QPU s; the one submission is `scripts/h0_submit.py`, unchanged):

  aer        C3: one or more seeded Aer chunks of a pilot circuit at a uniform T2 ratio r
             (`--circuit <id> --ratio <r> [--ratio ...] --chunk <i> [--chunk ...]`), on
             `backend_from_record(patch record, FakeKingston(), strict=True)` with
             `apply_t2_override` at r on the 12 patch qubits, seeds `chunk_seed(11, i, 2000)`.
             Counts are written once and refused rather than re-drawn.
  predict    C1/C2: the preregistration `data/hardware/H0_kpilot_prep/prereg_<fp16>.json`
             (format of `h0_submit.preflight` / `gate_H0_diag.load_prereg`): PTA on the
             explicit delay windows, ramw / t1w predictions per qubit, windows, pubs, the
             execution estimate on the live durations (STOP if > 30 s), the Aer grid with the
             day's r_crit, the decision thresholds verbatim.
  prereg-md  C4: `reports/H0_kpilot_prereg_<stamp>.md` generated from the prereg JSON.
  assemble   D2 / F1: the analysis S1-S5 on a counts directory, the decision block, criteria
             K1-K9 -> `validation/<out>.json` and the report.  `--dry-run` for the dry-run
             counts (the reference record is then the FakeKingston snapshot of the patch).
"""
import argparse
import glob
import gzip
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PREP = os.path.join("data", "hardware", "H0_kpilot_prep")
DEVICE = "ibm_kingston"
G2 = 4.0

# ---- preregistered constants (prompts/21 "Preregistration"; none of them new)
SHOTS = 4000
SHOTS_PER_CHUNK = 2000
CHUNKS = 2
SEED_BASE = 11
AER_GRID = {"B0_ref06_k1": (1.0, 0.5, 0.3285, 0.25, 0.174),
            "B1_ref07_k1": (1.0, 0.174),
            "B0_ref06_k4": (1.0, 0.174)}
K1_IDS = ("B0_ref06_k1", "B1_ref07_k1")
INFO_IDS = ("B0_ref06_k4",)
DECIDING = "B0_ref06_k1"
BAR_MEAN, BAR_WORST = 0.1, 0.05             # amendment 01 section 1(c): read, never changed
R_CRIT_PREREG = 0.3285                      # validation/S2D_levers.json data.verdict ... L1_seed_alap
FEZ_RATIO = 0.174                           # validation/S2D_idle.json data.t2_bracket fallback
CONF68, CONF95 = 0.6827, 0.9545
BOOT_DRAWS, BOOT_SEED = 10000, 11
LOGR_TOL = 1e-6
MAX_ESTIMATE_S = 30.0
MAX_USAGE_S = 60.0
K7_TOL = 0.25
PLANNER_EXPECTATION = ("Planner expectation (from the fez ratio and the Aer grid: f_Aer(0.153-0.174) = "
                       "0.031): NO-GO is the likely outcome; it is a result, not a failure of the gate.")


def p(*parts):
    return os.path.join(ROOT, *parts)


def rel(path):
    return os.path.relpath(path, ROOT)


def load_json(path):
    with open(path if os.path.isabs(path) else p(path)) as fh:
        return json.load(fh)


def dump_json(obj, path):
    from skqd.report import _jsonable
    path = path if os.path.isabs(path) else p(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(_jsonable(obj), fh, indent=1)
    os.replace(tmp, path)
    return path


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "n/a"


def versions():
    import qiskit
    import qiskit_aer
    import qiskit_ibm_runtime
    return {"qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__,
            "qiskit_ibm_runtime": qiskit_ibm_runtime.__version__}


def rkey(r):
    return f"{float(r):g}"


# --------------------------------------------------------------------------- prep access
def prep_manifests(prep=PREP):
    from gate_H0P import load_manifests
    mans, cals = load_manifests(p(prep))
    return {m["id"]: m for m in mans + cals}


def patch_record(prep=PREP):
    info = load_json(p(prep, "live.json"))
    pr = info.get("patch_record")
    if not pr:
        raise SystemExit("live.json carries no patch_record: run h0_kpilot_circuits.py --stage patchcal")
    return load_json(pr["path"]), pr, info


def patch_qubits(prep=PREP):
    return list(load_json(p(prep, "index.json"))["patch"])


def chunk_seed(chunk):
    from gate_H0_model import chunk_seed as cs
    return cs(SEED_BASE, chunk, SHOTS_PER_CHUNK)


def aer_path(cid, r, chunk, prep=PREP):
    return p(prep, "aer", f"{cid}_r{rkey(r)}_chunk{int(chunk)}.json")


# --------------------------------------------------------------------------- C3 Aer cells
def run_aer_chunk(cid, r, chunk, prep=PREP):
    from gate_H0P import apply_t2_override, load_circuit
    from h0_backends import backend_from_record
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    path = aer_path(cid, r, chunk, prep)
    if os.path.exists(path):
        print(f"{rel(path)} exists: counts are written once, not re-drawn")
        return load_json(path)
    mans = prep_manifests(prep)
    man = mans[cid]
    rec, prinfo, _ = patch_record(prep)
    t0 = time.time()
    base, binfo = backend_from_record(rec, base=FakeKingston(), strict=True)
    ov_rec = None
    if abs(float(r) - 1.0) > 1e-15:
        ov = {"source": f"uniform ratio {r} x the patch record's echo T2 (prompts/21 C3)",
              "per_qubit": {str(q): {"T2_s": float(rec["qubits"][str(q)]["T2_s"]) * float(r),
                                     "provenance": f"{r} x record T2"} for q in patch_qubits(prep)}}
        ov_rec = apply_t2_override(base, ov)
    qc = load_circuit(p(prep), man)
    seed = chunk_seed(chunk)
    sim = AerSimulator.from_backend(base, seed_simulator=int(seed))
    ts = time.time()
    counts = sim.run(qc, shots=SHOTS_PER_CHUNK).result().get_counts()
    secs = time.time() - ts
    out = {"gate": "H0_kpilot", "circuit": cid, "ratio": float(r), "chunk": int(chunk),
           "seed_simulator": int(seed), "shots": SHOTS_PER_CHUNK,
           "circuit_qpy_gz_sha256": man["qpy_gz_sha256"],
           "record_fingerprint": rec["fingerprint"], "record_path": prinfo["path"],
           "t2_override": ov_rec, "versions": versions(), "seconds": secs,
           "total_seconds": time.time() - t0, "when": now(),
           "counts": {str(k): int(v) for k, v in counts.items()}}
    dump_json(out, path)
    print(f"  {rel(path)}: {SHOTS_PER_CHUNK} shots in {secs:.0f} s", flush=True)
    return out


def stage_aer(args):
    ids = args.circuit or list(AER_GRID)
    for cid in ids:
        ratios = args.ratio if args.ratio else AER_GRID[cid]
        for r in ratios:
            if float(r) not in [float(x) for x in AER_GRID[cid]]:
                raise SystemExit(f"r = {r} is not a preregistered cell of {cid}: {AER_GRID[cid]}")
            for ch in (args.chunk if args.chunk is not None else range(CHUNKS)):
                run_aer_chunk(cid, r, ch, args.prep)
    return 0




# --------------------------------------------------------------------------- pure analysis (tested)
def decide(f_pool_95, f_c_95):
    """The preregistered decision rule on f (prompts/21).

    `f_pool_95` = [lo, hi] of the pooled f at 95 %; `f_c_95` = {circuit: [lo, hi]}.
    GO iff f_pool,lo95 >= 0.1 and min_c f_c,lo95 >= 0.05; NO-GO iff f_pool,hi95 < 0.1 or
    min_c f_c,hi95 < 0.05; AMBIGUOUS otherwise."""
    lo, hi = float(f_pool_95[0]), float(f_pool_95[1])
    min_lo = min(float(v[0]) for v in f_c_95.values())
    min_hi = min(float(v[1]) for v in f_c_95.values())
    if lo >= BAR_MEAN and min_lo >= BAR_WORST:
        return "GO"
    if hi < BAR_MEAN or min_hi < BAR_WORST:
        return "NO-GO"
    return "AMBIGUOUS"


def r_verdict(r68, r_crit=R_CRIT_PREREG):
    if r68 is None or r68[0] is None or r68[1] is None:
        return None
    if r68[0] >= r_crit:
        return "above"
    if r68[1] < r_crit:
        return "below"
    return "straddles"


def model_consistent(f_meas, f_aer, factor=None):
    from gate_H0_diag import POSTDICTION_FACTOR
    fac = POSTDICTION_FACTOR if factor is None else factor
    if f_meas is None or f_aer is None or f_aer <= 0:
        return None, None
    ratio = float(f_meas) / float(f_aer)
    return ratio, bool(1.0 / fac <= ratio <= fac)


def t2star_window(P0, sigma, T):
    """(T2*, relative sigma) from one window, or (None, None) when 2 P0 - 1 is not in (0, 1)."""
    if P0 is None or sigma is None:
        return None, None
    x = 2.0 * float(P0) - 1.0
    if not (0.0 < x < 1.0):
        return None, None
    lx = math.log(x)
    return -float(T) / lx, 2.0 * float(sigma) / (abs(x) * abs(lx))


def t2star_rule(windows, sigma_k=None):
    """Rule S3 (prompts/21, M-T2 extended to two windows) for ONE qubit.

    `windows` = {"long": {"P0", "sigma", "T"}, "half": {...}}.  Returns (T2*, provenance,
    window, relative sigma) -- provenance "measured" (the window with the smaller relative
    sigma among those with 0 < 2 P0 - 1 < 1), "upper_bound_3sigma_half" (the 3 sigma upper
    bound at the half window), or None (the caller applies the patch minimum)."""
    from gate_H0_diag import SIGMA
    k = SIGMA if sigma_k is None else sigma_k
    best = None
    for w in ("long", "half"):
        d = windows.get(w)
        if not d:
            continue
        t, rs = t2star_window(d.get("P0"), d.get("sigma"), d.get("T"))
        if t is not None and (best is None or rs < best[3]):
            best = (t, "measured", w, rs)
    if best is not None:
        return best
    d = windows.get("half")
    if d and d.get("P0") is not None and d.get("sigma") is not None:
        hi = 2.0 * (float(d["P0"]) + k * float(d["sigma"])) - 1.0
        if 0.0 < hi < 1.0:
            return -float(d["T"]) / math.log(hi), "upper_bound_3sigma_half", "half", None
    return None, None, None, None


def t2star_patch(per_q_windows, sigma_k=None):
    """{qubit: (T2*, provenance, window, rel sigma)} with the patch-minimum fallback."""
    out = {q: t2star_rule(w, sigma_k) for q, w in per_q_windows.items()}
    resolved = [v[0] for v in out.values() if v[0] is not None]
    pmin = min(resolved) if resolved else None
    for q, v in list(out.items()):
        if v[0] is None:
            out[q] = (pmin, "patch_minimum" if pmin is not None else None, None, None)
    return out


def s_t2(windows_by_q, t2_by_q):
    """S_T2 = sum_q sum_w (1 - e^{-w/T2_q}) / 2 (the PTA dephasing sum of skqd.idle.idle_budget)."""
    s = 0.0
    for q, ws in windows_by_q.items():
        T = float(t2_by_q[q])
        s += float(np.sum((1.0 - np.exp(-np.asarray(ws, dtype=float) / T)) / 2.0))
    return s


def r_eff_solve(windows_by_q, t2echo_by_q, t2star_by_q, lo=1e-4, hi=1e3, tol=LOGR_TOL):
    """The uniform ratio r with S_T2(r x T2_echo) = S_T2(T2*), bisection on log r to `tol`."""
    target = s_t2(windows_by_q, t2star_by_q)
    qs = list(windows_by_q)
    ws = [np.asarray(windows_by_q[q], dtype=float) for q in qs]
    te = [float(t2echo_by_q[q]) for q in qs]

    def S(r):
        return sum(float(np.sum((1.0 - np.exp(-w / (r * t))) / 2.0)) for w, t in zip(ws, te))

    a, b = math.log(lo), math.log(hi)
    if S(math.exp(a)) < target:
        return lo
    if S(math.exp(b)) > target:
        return hi
    while b - a > tol:
        m = 0.5 * (a + b)
        if S(math.exp(m)) > target:      # S decreases with r: too much dephasing -> r larger
            a = m
        else:
            b = m
    return math.exp(0.5 * (a + b))


def loglog_interp(grid, r):
    """f(r) by log-log interpolation on {r: f}; extrapolated from the nearest two points
    outside the grid (flagged).  Returns (f, status)."""
    pts = sorted((float(k), float(v)) for k, v in grid.items() if v is not None and v > 0)
    if len(pts) < 2 or r is None or r <= 0:
        return None, "no data"
    x = math.log(r)
    xs = [math.log(a) for a, _ in pts]
    ys = [math.log(b) for _, b in pts]
    if x <= xs[0]:
        i, status = 0, "extrapolated below the grid"
    elif x >= xs[-1]:
        i, status = len(xs) - 2, "extrapolated above the grid"
    else:
        i = max(j for j in range(len(xs) - 1) if xs[j] <= x)
        status = "interpolated"
    y = ys[i] + (x - xs[i]) * (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i])
    return math.exp(y), status


def pooled_interval_scaled(rows, m, conf):
    """The pooled reference-string interval if every count and shot number were m times larger
    (Poisson scaling at the measured rates; non-integer counts allowed in the Garwood formula)."""
    from scipy.stats import chi2
    from skqd.skqd import READOUT_FACTOR
    n = sum(float(r[0]) for r in rows) * m
    exp_ = sum(float(r[1]) * float(r[3]) / float(r[4]) for r in rows) * m
    den = sum(float(r[1]) * float(r[2]) for r in rows) * m
    alpha = 1.0 - conf
    lo_n = 0.0 if n <= 0 else float(chi2.ppf(alpha / 2.0, 2 * n) / 2.0)
    hi_n = float(chi2.ppf(1.0 - alpha / 2.0, 2 * n + 2) / 2.0)
    f = lambda x: (x - exp_) / den / READOUT_FACTOR
    return f(n), [f(lo_n), f(hi_n)]


def topup_factor(rows, bar, conf=CONF95, m_max=1e4):
    """Smallest m >= 1 with the scaled pooled interval excluding `bar` (None if not by m_max)."""
    f0, _ = pooled_interval_scaled(rows, 1.0, conf)

    def excl(m):
        _f, iv = pooled_interval_scaled(rows, m, conf)
        return iv[0] >= bar if f0 >= bar else iv[1] < bar
    if excl(1.0):
        return 1.0
    lo, hi = 1.0, 2.0
    while not excl(hi):
        lo, hi = hi, hi * 2.0
        if hi > m_max:
            return None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if excl(mid):
            hi = mid
        else:
            lo = mid
    return hi


def ambiguous_topup(rows_pool, rows_by_circuit):
    """Additional shots (total over the k = 1 circuits, Poisson scaling at the measured f) that
    make the pooled 95 % interval exclude 0.1 and every circuit's exclude 0.05."""
    shots = sum(int(r[1]) for r in rows_pool)
    need = {"pooled_vs_0.1": topup_factor(rows_pool, BAR_MEAN)}
    for c, row in rows_by_circuit.items():
        need[f"{c}_vs_0.05"] = topup_factor([row], BAR_WORST)
    ms = [v for v in need.values() if v is not None]
    m = max(ms) if ms and len(ms) == len(need) else None
    return {"factors": need, "factor": m,
            "additional_shots_total": (None if m is None else int(math.ceil((m - 1.0) * shots))),
            "additional_shots_per_circuit": (None if m is None else
                                             int(math.ceil((m - 1.0) * shots / len(rows_pool)))),
            "method": "Poisson scaling of the measured counts; Garwood 95 % interval on the pooled count"}


DECISION_FIELDS = ("f_pool", "f_pool_68", "f_pool_95", "f_by_circuit", "worst_circuit_f_95", "decision",
                   "ambiguous_topup_shots", "r_eff", "r_eff_68", "r_eff_95", "r_crit_preregistered",
                   "r_crit_day", "r_verdict", "f_aer_at_r_eff", "model_consistent", "shape_ratio_median",
                   "n_qubits_resolved_long", "n_qubits_resolved_half", "usage_s", "dry_run")


def decision_complete(dec):
    """K8 (i): every field of F2 present and non-null (ambiguous_topup_shots only when AMBIGUOUS;
    usage_s may be null in a dry run, whose local jobs carry no billed usage)."""
    missing = []
    for k in DECISION_FIELDS:
        if k not in dec:
            missing.append(k)
            continue
        if dec[k] is None:
            if k == "ambiguous_topup_shots" and dec.get("decision") != "AMBIGUOUS":
                continue
            if k == "usage_s" and dec.get("dry_run"):
                continue
            missing.append(k)
    return missing


def prereg_keys_ok(pre):
    """The keys `h0_submit.preflight` and `gate_H0_diag.load_prereg` read."""
    cal = pre.get("calibration") or {}
    need = [("calibration.fingerprint", cal.get("fingerprint")), ("calibration.path", cal.get("path")),
            ("calibration.last_update_date", cal.get("last_update_date")),
            ("calibration.stamp", cal.get("stamp")), ("created", pre.get("created")),
            ("commit", pre.get("commit")), ("script", pre.get("script")), ("prep", pre.get("prep"))]
    return [k for k, v in need if not v]


def check_mixing(dry_run_flag, session, records):
    """The assemble stage never mixes dry-run and device counts."""
    sd = (session or {}).get("dry_run")
    if sd is None:
        raise SystemExit("the counts directory has no session.json with a dry_run field: refusing")
    if bool(sd) != bool(dry_run_flag):
        raise SystemExit(f"session.dry_run is {sd} but --dry-run is {bool(dry_run_flag)}: dry-run and "
                         f"device counts are never mixed")
    bad = [m.get("id") for m, _c in records if bool(m.get("dry_run")) != bool(dry_run_flag)]
    if bad:
        raise SystemExit(f"counts files {bad[:3]} disagree with the session's dry_run flag: refusing")



# --------------------------------------------------------------------------- K3 (prompts/21a)
def readout_expected_live(rec, patch):
    """The preregistered device-K3 expectation: per qubit 1 - measure_error of the patch record."""
    per = {str(q): 1.0 - float(rec["qubits"][str(q)]["measure_error"]) for q in patch}
    qmin = min(per, key=lambda q: per[q])
    return {"per_qubit": per, "min": per[qmin], "min_qubit": int(qmin),
            "source": "1 - measure_error of the preregistered patch record (prompts/21a item 2)"}


def device_k3(min_diagonal):
    """Device-mode K3, unchanged: the smallest confusion diagonal >= DIAG_MIN."""
    from gate_H0P import DIAG_MIN
    return min_diagonal is not None and float(min_diagonal) >= DIAG_MIN


def dry_k3(measured, expected, shots, k=3.0):
    """Dry-run K3 (prompts/21a item 1): every measured diagonal within k binomial sigma of the
    simulator's own readout model.  `measured` / `expected` = {qubit: (d00, d11)}."""
    rows, ok = {}, True
    for q, (m00, m11) in measured.items():
        e00, e11 = expected[q]
        r = {}
        for lab, m, e in (("d00", m00, e00), ("d11", m11, e11)):
            sig = math.sqrt(max(e * (1.0 - e), 0.0) / float(shots))
            z = (m - e) / sig if sig > 0 else (0.0 if m == e else float("inf"))
            r[lab] = {"expected": e, "measured": m, "sigma": sig, "z": z}
            ok = ok and abs(z) <= k
        rows[str(q)] = r
    return ok, rows


def snapshot_readout_model(backend_name, patch):
    """{qubit: (P[0][0], P[1][1])} of the readout errors NoiseModel.from_backend attaches."""
    from h0_backends import resolve_backend
    from qiskit_aer.noise import NoiseModel
    nm = NoiseModel.from_backend(resolve_backend(backend_name))
    out = {}
    for q in patch:
        P = nm._local_readout_errors[(int(q),)].probabilities
        out[int(q)] = (float(P[0][0]), float(P[1][1]))
    return out


# --------------------------------------------------------------------------- decoding
def decode_counts(counts_list, man):
    """Both clean-yield statistics (68 % and 95 %), the distance histogram and the garbage
    expectation of one coarse circuit, from raw qiskit-key counts."""
    import gate_S2D_levers as G
    from gate_H0_model import decode_histogram
    from skqd.codec import Codec
    from skqd.skqd import clean_fraction_mixture, reference_string_test
    fx = G.factory()
    codec = Codec(fx["M"].basis)
    order, twoB, ref, theta = man["order"], int(man["twoB"]), int(man["reference"]), float(man["theta"])
    d = G.ideal_distribution(order, twoB, ref, theta)
    pos = {int(b): i for i, b in enumerate(d["sector_indices"])}
    refbits = tuple(int(x) for x in codec.encode(fx["M"].basis.labels[ref]))
    dist = {int(b): int(sum(x != y for x, y in zip(codec.encode(fx["M"].basis.labels[int(b)]), refbits)))
            for b in d["sector_indices"]}
    a = G.garbage_acceptance(twoB)
    n_bins = max(max(dist.values()) + 1, 9)
    tot = np.zeros(d["dim"])
    hist = np.zeros(n_bins)
    shots = 0
    for c in counts_list:
        n, h, sh = decode_histogram(c, codec, dist, pos, twoB, n_bins)
        tot += n
        hist += h
        shots += sh
    n_ref = int(round(float(tot[d["reference_position"]])))
    r68 = reference_string_test(n_ref, shots, d["p_reference"], a, d["dim"], conf=CONF68)
    r95 = reference_string_test(n_ref, shots, d["p_reference"], a, d["dim"], conf=CONF95)
    mix = clean_fraction_mixture(tot, d["p"], d["dim"], shots)
    fr, fm = r68["f_clean"], mix["f_clean"]
    return {"shots": shots, "accepted": int(tot.sum()), "reference_hits": n_ref,
            "p_reference": d["p_reference"], "garbage_acceptance": a, "dim": d["dim"],
            "expected_reference_hits_from_garbage": r68["expected_from_garbage"],
            "z": r68["z"], "P_ge": r68["P_ge"],
            "f_clean_reference": fr, "f_clean_reference_68": r68["f_clean_68"],
            "f_clean_reference_95": r95["f_clean_68"],
            "f_clean_mixture": fm, "f_clean_mixture_68": mix["f_clean_68"], "w": mix["w"],
            "c6_relative_deviation": (abs(fm - fr) / fr) if fr else None,
            "c6_flag_information": (bool(abs(fm - fr) / fr > 0.25) if fr else None),
            "distance_histogram": [int(x) for x in hist],
            "row": [n_ref, shots, d["p_reference"], a, d["dim"]]}


def aer_cells(prep=PREP):
    """{circuit: {r: decoded cell}} of every preregistered Aer cell present on disk."""
    mans = prep_manifests(prep)
    out = {}
    for cid, ratios in AER_GRID.items():
        out[cid] = {}
        for r in ratios:
            chunks = []
            for ch in range(CHUNKS):
                path = aer_path(cid, r, ch, prep)
                if os.path.exists(path):
                    chunks.append(load_json(path))
            if len(chunks) < CHUNKS:
                out[cid][rkey(r)] = None
                continue
            d = decode_counts([c["counts"] for c in chunks], mans[cid])
            d["seeds"] = [c["seed_simulator"] for c in chunks]
            d["strided_seeds"] = d["seeds"] == [chunk_seed(i) for i in range(CHUNKS)]
            d["files"] = [rel(aer_path(cid, r, i, prep)) for i in range(CHUNKS)]
            d["record_fingerprint"] = chunks[0]["record_fingerprint"]
            d["t2_override_clipped"] = [x for c in chunks for x in ((c.get("t2_override") or {}).get("clipped") or [])]
            d["expected_reference_hits_at_4000"] = d["reference_hits"] * SHOTS / d["shots"]
            out[cid][rkey(r)] = d
    return out


# --------------------------------------------------------------------------- C1/C2 predictions
def coarse_schedules(rec, prep=PREP):
    """{circuit: (sched circuit, delay schedule leading-excluded, leading-included)}."""
    import gate_S2D_levers as G
    from gate_H0P import load_circuit
    mans = prep_manifests(prep)
    out = {}
    for cid in AER_GRID:
        qc = load_circuit(p(prep), mans[cid])
        out[cid] = (qc, G.delay_schedule(qc, rec, include_leading=False),
                    G.delay_schedule(qc, rec, include_leading=True))
    return out


def stage_predict(args):
    import gate_S2D_levers as G
    import h0_qpu_time as qt
    from h0_backends import fresh_calibration, frozen_qubits_and_edges, resolve_backend
    t0 = time.time()
    prep = args.prep
    rec, prinfo, info = patch_record(prep)
    index = load_json(p(prep, "index.json"))
    sel = load_json(p(prep, "select.json"))
    mans = prep_manifests(prep)
    patch = index["patch"]
    # D9 at prediction time: the live patch content must still be the record's
    b = resolve_backend(DEVICE)
    qubits, edges = frozen_qubits_and_edges(p(prep))
    live = fresh_calibration(b, qubits, edges)
    if live["fingerprint"] != rec["fingerprint"]:
        print(f"STOP (D10): the live patch fingerprint {live['fingerprint'][:16]} is not the patch record's "
              f"{rec['fingerprint'][:16]} -- re-run A2-C4 on the new content")
        return 3
    est = qt.estimate(p(prep), b, {}, SHOTS, shots_default=SHOTS)
    # PTA on the explicit delay windows, both leading conventions
    sch = coarse_schedules(rec, prep)
    pta = {}
    for cid, (qc, dex, din) in sch.items():
        fg, n2, f1 = G.f_gates_on_record(qc, rec)
        pta[cid] = {"f_gates": fg, "n_2q": n2, "f_including_1q_errors": f1,
                    "T_s": mans[cid]["T_s"], "T_total_s": mans[cid]["T_total_s"],
                    "leading_excluded": {rkey(r): G.pta_at(dex, rec, fg, r) for r in AER_GRID[DECIDING]},
                    "leading_included": {rkey(r): G.pta_at(din, rec, fg, r) for r in AER_GRID[DECIDING]},
                    "leading_delay_s": {str(k): v for k, v in dex["leading_s"].items()}}
    # ramw / t1w predictions per qubit
    W = index["windows"]
    Tl, Th = W["total_delay_long_s"], W["total_delay_half_s"]
    idle_pred = {}
    for q in patch:
        v = rec["qubits"][str(q)]
        T1, T2 = float(v["T1_s"]), float(v["T2_s"])
        idle_pred[str(q)] = {
            "T1_record_s": T1, "T2_echo_record_s": T2,
            "ramw_P0_echo_bound_long": (1 + math.exp(-Tl / T2)) / 2,
            "ramw_P0_echo_bound_half": (1 + math.exp(-Th / T2)) / 2,
            "ramw_P0_at_r_0.174_long": (1 + math.exp(-Tl / (FEZ_RATIO * T2))) / 2,
            "ramw_P0_at_r_0.174_half": (1 + math.exp(-Th / (FEZ_RATIO * T2))) / 2,
            "t1w_survival_long": math.exp(-Tl / T1)}
    # Aer grid
    cells = aer_cells(prep)
    missing = [f"{c} r={r}" for c, d in cells.items() for r, v in d.items() if v is None]
    if missing:
        raise SystemExit(f"Aer cells missing: {missing} -- run --stage aer first")
    grid_mix = {r: (None if d is None else d["f_clean_mixture"]) for r, d in cells[DECIDING].items()}
    grid_ref = {r: (None if d is None else d["f_clean_reference"]) for r, d in cells[DECIDING].items()}
    rc_day = G.aer_r_crit(grid_mix, BAR_MEAN)
    rc_day_ref = G.aer_r_crit(grid_ref, BAR_MEAN)
    s2d = load_json(p("validation", "S2D_levers.json"))["data"]
    ref_cell = s2d["aer"]["L1_seed_alap"]["1.0"]
    mine = cells[DECIDING].get("1")
    k7 = {"reference": "validation/S2D_levers.json data.aer.L1_seed_alap['1.0'].f_clean_mixture",
          "reference_value": ref_cell["f_clean_mixture"], "reference_68": ref_cell["f_clean_mixture_68"],
          "day_value": None if mine is None else mine["f_clean_mixture"],
          "mapping_reproduced": sel["mapping_reproduced"]}
    if mine is not None:
        k7["relative_deviation"] = abs(mine["f_clean_mixture"] - ref_cell["f_clean_mixture"]) / ref_cell["f_clean_mixture"]
        k7["within_tolerance"] = k7["relative_deviation"] <= K7_TOL
    pubs = [{"id": m["id"], "kind": m["kind"], "test": m.get("test"), "window": m.get("window"),
             "shots": SHOTS} for m in sorted(mans.values(), key=lambda m: m["id"])]
    fp16 = rec["fingerprint"][:16]
    pre = {
        "gate": "H0_kpilot", "script": "scripts/gate_H0_kpilot.py --stage predict",
        "created": now(), "commit": git_commit(), "versions": versions(), "qpu_seconds": 0,
        "prep": prep, "prep_created": index["created"],
        "calibration": {"backend": DEVICE, "fingerprint": rec["fingerprint"], "path": prinfo["path"],
                        "last_update_date": rec["last_update_date"], "stamp": rec["stamp"],
                        "full_record_path": info["record"]["path"],
                        "full_record_fingerprint": info["record"]["fingerprint"],
                        "live_fingerprint_at_predict": live["fingerprint"],
                        "live_match_at_predict": live["fingerprint"] == rec["fingerprint"]},
        "patch": patch, "selection": {"rule": sel["rule"], "winner_mapping": sel["winner_mapping"],
                                      "mapping_reproduced": sel["mapping_reproduced"],
                                      "n_embeddings": sel["n_embeddings"], "n_scored": sel["n_scored"],
                                      "winner_f_dd_off": sel["winner"]["f_dd_off"],
                                      "top5": [{k: e[k] for k in ("rank", "physical_qubits", "f_dd_off", "f_gates", "T_s")}
                                               for e in sel["top5"]]},
        "windows": W,
        "pubs": pubs, "shots_per_pub": SHOTS, "total_shots": SHOTS * len(pubs),
        "sampler_options": "D8': --dd off --twirling off; no resilience, raw bit strings",
        "execution_estimate": {"total_execution_s": est["total_execution_s"], "total_shots": est["total_shots"],
                               "rep_delay_s": est["rep_delay_s"], "groups": est["groups"],
                               "per_circuit": est["per_circuit"], "last_update_date": est["last_update_date"],
                               "cap_s": MAX_ESTIMATE_S, "within_cap": est["total_execution_s"] <= MAX_ESTIMATE_S},
        "coarse_circuits": {cid: {k: mans[cid][k] for k in ("sector", "reference", "k", "theta", "cz", "n_delays",
                                                            "T_s", "T_total_s", "p_reference", "exactness",
                                                            "placement", "qpy_gz_sha256", "source_qpy_sha256")}
                            for cid in AER_GRID},
        "pta": pta, "idle_predictions": idle_pred,
        "aer": cells, "aer_grid_B0_ref06_k1_mixture": grid_mix, "aer_grid_B0_ref06_k1_reference": grid_ref,
        "r_crit_day": rc_day, "r_crit_day_reference_statistic": rc_day_ref,
        "r_crit_preregistered": R_CRIT_PREREG, "k7_reproduction": k7,
        "decision_rule": {
            "GO": "f_pool,lo95 >= 0.1 and min_c f_c,lo95 >= 0.05",
            "NO-GO": "f_pool,hi95 < 0.1 or min_c f_c,hi95 < 0.05",
            "AMBIGUOUS": "otherwise -> STOP; the report states the additional shots (Poisson scaling)",
            "bars": [BAR_MEAN, BAR_WORST], "statistic": "reference-string f_clean (S1/S2), Garwood intervals at 0.6827 / 0.9545",
            "r_verdict": f"above iff r_eff,lo68 >= {R_CRIT_PREREG}; below iff r_eff,hi68 < {R_CRIT_PREREG}; else straddles",
            "model_consistent": "f_B0,meas / f_Aer(r_eff) in [1/3, 3] (POSTDICTION_FACTOR of H0_diag / H0_model C3)",
            "disagreement": "the direct measurement decides f; a disagreement with the r-verdict is a model finding"},
        "statistics": {
            "S1": "reference_string_test per k = 1 circuit (68 % and 95 %), clean_fraction_mixture alongside (C6 deviation information)",
            "S2": "pooled_reference_string_test over the two k = 1 circuits -> f_pool",
            "S3": "readout-corrected P0 per qubit and window (gate_H0_diag.idle_tests, SIGMA 3); T2* from the window with the smaller relative sigma among 0 < 2P0-1 < 1, else the 3 sigma upper bound at the half window, else the patch minimum",
            "S4": "r_eff: uniform r with S_T2(r T2_echo) = S_T2(T2*) on the ALAP B0_ref06_k1 delay windows, leading excluded; bisection on log r to 1e-6; bootstrap 10000 draws seed 11",
            "S5": "f_Aer(r_eff) by log-log interpolation of the day's B0_ref06_k1 grid (mixture statistic); the day's r_crit by gate_S2D_levers.aer_r_crit"},
        "planner_expectation": PLANNER_EXPECTATION,
        "runtime_s": time.time() - t0,
    }
    path = p(prep, f"prereg_{fp16}.json")
    if os.path.exists(path):
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel(path)], cwd=ROOT,
                                 capture_output=True).returncode == 0
        if tracked:
            raise SystemExit(f"{rel(path)} is committed as the preregistration: refusing to overwrite")
    from gate_H0P import DIAG_MIN
    pre["readout_expected_live"] = readout_expected_live(rec, patch)
    if pre["readout_expected_live"]["min"] < DIAG_MIN:
        print(f"STOP (prompts/21a): the live readout expectation {pre['readout_expected_live']['min']:.4f} "
              f"(qubit {pre['readout_expected_live']['min_qubit']}) < DIAG_MIN {DIAG_MIN}: nothing is submitted")
        return 3
    dump_json(pre, path)
    print(f"wrote {rel(path)}: estimate {est['total_execution_s']:.2f} s over {est['total_shots']} shots "
          f"(cap {MAX_ESTIMATE_S:.0f}); Aer B0_ref06_k1 grid {json.dumps({k: (None if v is None else round(v, 4)) for k, v in grid_mix.items()})}; "
          f"r_crit day {rc_day}; K7 {k7.get('relative_deviation')}")
    if est["total_execution_s"] > MAX_ESTIMATE_S:
        print(f"STOP: the execution estimate {est['total_execution_s']:.1f} s exceeds {MAX_ESTIMATE_S:.0f} s")
        return 3
    return 0


def _f(x, spec="{:.4f}"):
    return "n/a" if x is None else spec.format(x)


def _iv(iv, spec="{:.4f}"):
    if not iv or iv[0] is None:
        return "n/a"
    return "[" + spec.format(iv[0]) + ", " + spec.format(iv[1]) + "]"


def stage_prereg_md(args):
    from skqd.report import md_table, write_report
    path = args.prereg or sorted(glob.glob(p(args.prep, "prereg_*.json")))[-1]
    pre = load_json(path)
    W = pre["windows"]
    est = pre["execution_estimate"]
    pubs = [[x["id"], x["kind"], x.get("test") or "", x.get("window") or "", x["shots"]] for x in pre["pubs"]]
    aer_rows = []
    for cid, cells in pre["aer"].items():
        for r, d in cells.items():
            pt = pre["pta"][cid]["leading_excluded"].get(r, {}).get("f")
            aer_rows.append([cid, r, "n/a" if d is None else d["accepted"],
                             "n/a" if d is None else d["reference_hits"],
                             "n/a" if d is None else _f(d["f_clean_reference"]) + " " + _iv(d["f_clean_reference_95"]),
                             "n/a" if d is None else _f(d["f_clean_mixture"]) + " " + _iv(d["f_clean_mixture_68"]),
                             "n/a" if d is None else f"{d['expected_reference_hits_at_4000']:.0f}",
                             _f(pt, "{:.3e}")])
    q_rows = [[q, f"{v['T1_record_s'] * 1e6:.1f}", f"{v['T2_echo_record_s'] * 1e6:.1f}",
               f"{v['ramw_P0_echo_bound_long']:.4f}", f"{v['ramw_P0_echo_bound_half']:.4f}",
               f"{v['ramw_P0_at_r_0.174_long']:.4f}", f"{v['ramw_P0_at_r_0.174_half']:.4f}",
               f"{v['t1w_survival_long']:.4f}"] for q, v in pre["idle_predictions"].items()]
    pta_rows = [[cid, f"{v['f_gates']:.4f}", f"{v['T_s'] * 1e6:.2f}"] +
                [_f(v["leading_excluded"][r]["f"], "{:.3e}") for r in v["leading_excluded"]] +
                [_f(v["leading_included"]["1"]["f"], "{:.3e}")] for cid, v in pre["pta"].items()]
    rlab = list(next(iter(pre["pta"].values()))["leading_excluded"])
    k7 = pre["k7_reproduction"]
    cal = pre["calibration"]
    txt = f"""# H0_kpilot preregistration -- ibm_kingston, calibration `{cal['fingerprint'][:16]}`

Generated by `scripts/gate_H0_kpilot.py --stage prereg-md` from `{rel(path) if os.path.isabs(path) else path}`
(written {pre['created']} at commit `{pre['commit']}`).  Every number below is read from that JSON.  Nothing
was submitted when this was written; the commit that adds this file is what criterion K1 checks against the
submission time.

## Calibration and patch

- Patch record `{cal['path']}`: fingerprint `{cal['fingerprint']}`, last update {cal['last_update_date']}
  (full-device record `{cal['full_record_path']}`, `{cal['full_record_fingerprint'][:16]}`); live content at the
  prediction identical: {cal['live_match_at_predict']}.
- Patch (rule R1'-pilot, run once): {pre['patch']}; the S2D_levers `L1_seed_alap` mapping reproduced:
  {pre['selection']['mapping_reproduced']} ({pre['selection']['n_scored']} of {pre['selection']['n_embeddings']} embeddings
  scored; winner PTA f (DD off, echo T2) {pre['selection']['winner_f_dd_off']:.4f}).

## Windows

dt {W['dt_s']:.3e} s, granularity {W['granularity']}, pulse_alignment {W['pulse_alignment']}: window {W['window_dt']} dt =
{W['window_s'] * 1e9:.1f} ns ({W['window_rule']}); T_s of `{W['T_s_matched_circuit']}` (ALAP) {W['T_s_matched'] * 1e6:.2f} us ->
N_long = {W['N_long']} ({W['total_delay_long_s'] * 1e6:.2f} us), N_half = {W['N_half']} ({W['total_delay_half_s'] * 1e6:.2f} us).

## Pubs, shots, execution estimate

{md_table(["pub", "kind", "test", "window", "shots"], pubs)}

{pre['total_shots']} shots in one job; execution estimate **{est['total_execution_s']:.2f} s** (cap {est['cap_s']:.0f} s,
within: {est['within_cap']}; rep delay {est['rep_delay_s'] * 1e6:.0f} us; live durations of {est['last_update_date']}).
Options: {pre['sampler_options']}.

## PTA on the explicit delay windows (leading |0> delays excluded; last column included, r = 1)

{md_table(["circuit", "f_gates", "T_s (us)"] + [f"PTA f r={r}" for r in rlab] + ["PTA f r=1 (leading incl.)"], pta_rows)}

## Aer predictions (scheduled circuits as submitted, patch record, uniform T2 ratio r; 2 x 2000 shots, seeds 11 / 2011)

{md_table(["circuit", "r", "accepted", "ref hits", "f_clean (reference) [95 %]", "f_clean (mixture) [68 %]",
           "expected ref hits at 4000", "PTA f"], aer_rows)}

Day's r_crit(0.1) on the `B0_ref06_k1` grid (mixture): {pre['r_crit_day']}; reference statistic: {pre['r_crit_day_reference_statistic']};
preregistered r_crit {pre['r_crit_preregistered']}.  K7 reproduction of S2D_levers' r = 1 cell
({k7['reference_value']:.4f}): day value {_f(k7['day_value'])}, relative deviation {_f(k7.get('relative_deviation'), '{:.3f}')}
(mapping reproduced: {k7['mapping_reproduced']}; tolerance 0.25).

## Per-qubit idle predictions (patch record)

{md_table(["qubit", "T1 (us)", "T2 echo (us)", "ramw P0 bound long", "ramw P0 bound half", "P0 r=0.174 long",
           "P0 r=0.174 half", "t1w survival long"], q_rows)}

## Decision rule (verbatim)

- GO: {pre['decision_rule']['GO']}; NO-GO: {pre['decision_rule']['NO-GO']}; AMBIGUOUS: {pre['decision_rule']['AMBIGUOUS']}.
- Statistic: {pre['decision_rule']['statistic']}.
- r-verdict: {pre['decision_rule']['r_verdict']}; model consistency: {pre['decision_rule']['model_consistent']}.
- {pre['decision_rule']['disagreement']}.
- {pre['planner_expectation']}
"""
    stamp = pre["calibration"]["stamp"]
    out = write_report(f"H0_kpilot_prereg_{stamp}.md", txt)
    print(f"wrote {rel(out)}")
    return 0


# --------------------------------------------------------------------------- D2 / F1 assemble
def find_prereg(prep, path=None):
    if path:
        return path
    info = load_json(p(prep, "live.json"))
    fp = (info.get("patch_record") or {}).get("fingerprint")
    cands = sorted(glob.glob(p(prep, f"prereg_{fp[:16]}.json"))) if fp else []
    if not cands:
        raise SystemExit("no preregistration for the current patch record: run --stage predict")
    return rel(cands[0])


def snapshot_record(prep):
    """The FakeKingston snapshot over the pilot's qubits and edges (the dry run's 'device')."""
    from h0_backends import calibration_record, frozen_qubits_and_edges
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    q, e = frozen_qubits_and_edges(p(prep))
    return calibration_record(FakeKingston(), q, e)


def git_commit_time(ref):
    try:
        out = subprocess.check_output(["git", "log", "-1", "--format=%H %cI", ref], cwd=ROOT,
                                      stderr=subprocess.DEVNULL).decode().strip()
        h, t = out.split()
        return h, t
    except Exception:
        return None, None


def git_added(path):
    try:
        out = subprocess.check_output(["git", "log", "--diff-filter=A", "--format=%H %cI", "--", path],
                                      cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip().splitlines()
        if not out:
            return None, None
        h, t = out[-1].split()
        return h, t
    except Exception:
        return None, None


def _utc(s):
    from datetime import datetime, timezone
    if s is None:
        return None
    if s.endswith(" UTC"):
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def bootstrap_r_eff(per_q_windows, windows_by_q, t2echo, draws=BOOT_DRAWS, seed=BOOT_SEED):
    """Parametric bootstrap of r_eff: every P0 ~ N(P0, sigma_P0) clipped to [0, 1], rule S3 re-applied."""
    rng = np.random.default_rng(seed)
    qs = list(per_q_windows)
    vals, failed = [], 0
    for _ in range(draws):
        pw = {}
        for q in qs:
            pw[q] = {}
            for w, d in per_q_windows[q].items():
                if d.get("P0") is None or d.get("sigma") is None:
                    pw[q][w] = dict(d)
                    continue
                x = float(np.clip(rng.normal(d["P0"], d["sigma"]), 0.0, 1.0))
                pw[q][w] = {"P0": x, "sigma": d["sigma"], "T": d["T"]}
        t = t2star_patch(pw)
        if any(v[0] is None for v in t.values()):
            failed += 1
            continue
        vals.append(r_eff_solve(windows_by_q, t2echo, {q: t[q][0] for q in qs}))
    v = np.asarray(vals)
    if v.size == 0:
        return {"draws": draws, "failed": failed, "r_eff_68": None, "r_eff_95": None}
    return {"draws": draws, "failed": failed, "seed": seed,
            "r_eff_68": [float(np.percentile(v, 16)), float(np.percentile(v, 84))],
            "r_eff_95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))],
            "median": float(np.median(v))}


def budgets_at(f, prep, full_rec, mp):
    """D3' and D3''-H0 budgets of the signed family (28 r = 1 circuits) at a measured f (information)."""
    import gate_S2D_levers as G
    import h0_device_survey as ds
    from gate_H0P import load_circuit, load_manifests
    from qiskit import qpy
    from skqd import idle
    if f is None or f <= 0:
        return {"status": "no positive f", "f": f}
    fam = load_json(p("data", "S2D_levers", "family.json"))["families"]["diag-hop0-hop1-hop2-hop3-plaq0_s2"]
    T, mans, P = {}, [], {}
    for c in fam["circuits"]:
        with gzip.open(p(fam["qpy_dir"], c["id"] + ".qpy.gz"), "rb") as fh:
            tq = qpy.load(fh)[0]
        rc = G.relabelled(tq, mp)
        T[c["id"]] = float(idle.schedule_asap(rc, full_rec)["T_total_s"])
        mans.append({"id": c["id"], "sector": c["sector"], "repetitions": 1, "k": c["k"]})
        P[c["id"]] = G.ideal_distribution(list(G.DEFAULT_ORDER), c["twoB"], c["reference"], c["theta"])["p_unnormalised"]
    _m, cals = load_manifests(G.PREP)
    ce = []
    for c in cals:
        qc = load_circuit(G.PREP, c)
        T[c["id"]] = float(idle.schedule_asap(qc, full_rec)["T_total_s"])
        ce.append({"id": c["id"]})
    rep = float(full_rec.get("default_rep_delay_s") or ds.REP_DELAY_DEFAULT)
    d3 = ds.d3_budget(P, T, mans, ce, f, rep)
    dpp = ds.d3pp_budget(T, mans, ce, f, rep)
    return {"f": f, "note": ("information: the signed family's 28 r = 1 circuits relabelled onto the pilot's "
                             "patch at their own durations; r = 2, 3 excluded (not rebuilt in this family)"),
            "D3prime_N4": d3["N4"], "D3prime_execution_s": d3["execution_s"],
            "D3prime_total_coarse_shots": d3["total_coarse_shots"],
            "D3pp_H0_shots_per_k1": dpp["shots_per_k1_circuit"], "D3pp_H0_execution_s": dpp["execution_s"]}


def stage_assemble(args):
    import gate_S2D_levers as G
    from gate_H0 import codeword_roundtrip, read_counts_dir
    from gate_H0_diag import (IDLE_QUBITS_MIN, RATE_HI, RATE_LO, SIGMA, idle_tests,
                              readout_reference)
    from gate_H0P import DIAG_MIN, load_circuit
    from h0_backends import calibration_diff
    from skqd.codec import Codec
    from skqd.report import GateResult, write_report
    from skqd.skqd import pooled_reference_string_test
    t0 = time.time()
    dry = bool(args.dry_run)
    out = args.out or ("H0_kpilot_dryrun" if dry else "H0_kpilot")
    prep = args.prep
    pre_path = find_prereg(prep, args.prereg)
    pre = load_json(pre_path)
    missing_keys = prereg_keys_ok(pre)
    mans = prep_manifests(prep)
    index = load_json(p(prep, "index.json"))
    patch = index["patch"]
    if not args.counts:
        raise SystemExit("--counts <dir> is required")
    cdir = p(args.counts) if not os.path.isabs(args.counts) else args.counts
    records = read_counts_dir(cdir)
    spath = os.path.join(os.path.dirname(os.path.normpath(cdir)), "session.json")
    session = load_json(spath) if os.path.exists(spath) else None
    check_mixing(dry, session, records)
    by_id = {m["id"]: (m, c) for m, c in records}
    prereg_rec = load_json(pre["calibration"]["path"])
    refrec = snapshot_record(prep) if dry else prereg_rec
    full_rec = load_json(pre["calibration"]["full_record_path"])
    fx = G.factory()
    codec = Codec(fx["M"].basis)
    n = codec.n_qubits

    # ---- readout (K3)
    ro = readout_reference({"records": records}, n)
    ro_survival = float(np.prod([1.0 - e for e in ro["measured_error"]])) if ro else None
    ro_live = readout_expected_live(prereg_rec, patch)
    cal_phys = mans["cal_patch_all0"]["logical_to_physical"]
    dry_k3_block = None
    if dry and ro:
        exp_model = snapshot_readout_model(index["common"]["backend"], cal_phys)
        meas = {int(q): (ro["P_measure_0_given_0"][i], ro["P_measure_1_given_1"][i]) for i, q in enumerate(cal_phys)}
        shots_cal = int(sum(by_id["cal_patch_all0"][1].values()))
        k3_ok, k3_rows = dry_k3(meas, exp_model, shots_cal)
        qmin = cal_phys[min(range(len(cal_phys)), key=lambda i: min(ro["P_measure_0_given_0"][i],
                                                                      ro["P_measure_1_given_1"][i]))]
        dry_k3_block = {"ok": k3_ok, "per_qubit": k3_rows, "shots": shots_cal, "sigma_k": 3.0,
                        "model": f"NoiseModel.from_backend({index['common']['backend']}) local readout errors",
                        "min_diagonal_qubit": int(qmin),
                        "min_diagonal_qubit_snapshot_error": 1.0 - 0.5 * sum(exp_model[int(qmin)]),
                        "min_diagonal_qubit_live_error": float(prereg_rec["qubits"][str(qmin)]["measure_error"]),
                        "ruling": "prompts/21a_H0_kpilot_dryrun_K3_ruling_20261002.md option (a)"}

    # ---- S3: the idle pubs
    idle = {}
    for cid in ("kpilot_ramw_long", "kpilot_ramw_half", "kpilot_t1w_long"):
        man, cts = by_id[cid]
        t = idle_tests({"records": [(man, cts)]}, ro, refrec, n, "own job all-0/all-1")
        idle[cid] = t[man["test"]]
    Tl = mans["kpilot_ramw_long"]["total_delay_s"]
    Th = mans["kpilot_ramw_half"]["total_delay_s"]
    per_q_windows = {}
    for q in patch:
        lq = idle["kpilot_ramw_long"]["per_qubit"][str(q)]
        hq = idle["kpilot_ramw_half"]["per_qubit"][str(q)]
        per_q_windows[q] = {"long": {"P0": lq["P_zero"], "sigma": lq["sigma"], "T": Tl},
                            "half": {"P0": hq["P_zero"], "sigma": hq["sigma"], "T": Th}}
    t2s = t2star_patch(per_q_windows)
    t2echo = {q: float(refrec["qubits"][str(q)]["T2_s"]) for q in patch}
    ramsey = {}
    shape = []
    n_res = {"long": 0, "half": 0}
    for q in patch:
        row = {"T2_echo_s": t2echo[q]}
        for w, cid, T in (("long", "kpilot_ramw_long", Tl), ("half", "kpilot_ramw_half", Th)):
            v = idle[cid]["per_qubit"][str(q)]
            tw, rs = t2star_window(v["P_zero"], v["sigma"], T)
            if tw is not None:
                n_res[w] += 1
            row[w] = {"raw_P0": v["raw_P_zero"], "P0": v["P_zero"], "sigma": v["sigma"],
                      "T2star_s": tw, "rel_sigma": rs, "upper_bound_3sigma_s": v["T2star_upper_bound_s"],
                      "echo_bound": v["P_zero_bound_from_record"], "within_echo_bound_3sigma": v["within_bound"],
                      "P0_at_r_0.174": (1 + math.exp(-T / (FEZ_RATIO * t2echo[q]))) / 2}
        T2q, prov, win, rs = t2s[q]
        row.update({"T2star_s": T2q, "provenance": prov, "window_used": win, "rel_sigma": rs,
                    "ratio_T2star_over_echo": None if T2q is None else T2q / t2echo[q]})
        xl, xh = 2 * (row["long"]["P0"] or 0) - 1, 2 * (row["half"]["P0"] or 0) - 1
        if 0 < xl < 1 and 0 < xh < 1:
            row["shape_ratio"] = math.log(xl) / math.log(xh)
            shape.append(row["shape_ratio"])
        else:
            row["shape_ratio"] = None
        if dry and T2q is not None and rs is not None:
            row["dry_run_T2star_within_3sigma_of_snapshot_echo"] = abs(T2q - t2echo[q]) <= 3 * rs * T2q
        ramsey[str(q)] = row
    t1rows = {q: idle["kpilot_t1w_long"]["per_qubit"][str(q)] for q in patch}

    # ---- S4: r_eff
    qc_b0 = load_circuit(p(prep), mans[DECIDING])
    dsch = G.delay_schedule(qc_b0, refrec, include_leading=False)
    windows_by_q = {int(q): dsch["per_qubit"][q]["windows_s"] for q in dsch["active"]}
    ok_t2 = all(t2s[q][0] is not None for q in windows_by_q)
    r_eff = r_eff_solve(windows_by_q, t2echo, {q: t2s[q][0] for q in windows_by_q}) if ok_t2 else None
    boot = bootstrap_r_eff({q: per_q_windows[q] for q in windows_by_q}, windows_by_q, t2echo) if ok_t2 else {}
    idle_q = {q: float(sum(windows_by_q[q])) for q in windows_by_q}
    harm = (sum(idle_q.values()) / sum(idle_q[q] / ramsey[str(q)]["ratio_T2star_over_echo"] for q in idle_q)
            if ok_t2 else None)
    s_star = s_t2(windows_by_q, {q: t2s[q][0] for q in windows_by_q}) if ok_t2 else None
    s_echo = s_t2(windows_by_q, t2echo)

    # ---- S1 / S2: the coarse circuits
    circ = {}
    for cid in AER_GRID:
        man, cts = by_id[cid]
        circ[cid] = decode_counts([cts], mans[cid])
    rt = codeword_roundtrip([(dict(mans[cid], **{"twoB": mans[cid]["twoB"]}), by_id[cid][1]) for cid in AER_GRID], codec)
    rows_pool = [circ[c]["row"] for c in K1_IDS]
    pool68 = pooled_reference_string_test(rows_pool, conf=CONF68)
    pool95 = pooled_reference_string_test(rows_pool, conf=CONF95)
    f_c95 = {c: circ[c]["f_clean_reference_95"] for c in K1_IDS}
    decision = decide(pool95["f_clean_68"], f_c95)
    worst = min(K1_IDS, key=lambda c: f_c95[c][0])
    topup = ambiguous_topup(rows_pool, {c: circ[c]["row"] for c in K1_IDS})

    # ---- S5
    grid_mix = pre["aer_grid_B0_ref06_k1_mixture"]
    f_aer_r, f_aer_status = loglog_interp(grid_mix, r_eff)
    rc_day = pre["r_crit_day"].get("value")
    ratio_mc, mc = model_consistent(circ[DECIDING]["f_clean_reference"], f_aer_r)
    f_aer_ref, _ = loglog_interp(pre["aer_grid_B0_ref06_k1_reference"], r_eff)
    ratio_mc_ref, mc_ref = model_consistent(circ[DECIDING]["f_clean_reference"], f_aer_ref)
    aer_at = {}
    for cid in AER_GRID:
        g = {r: (None if d is None else d["f_clean_mixture"]) for r, d in pre["aer"][cid].items()}
        aer_at[cid] = {"r=1": g.get("1"), "r=0.174": g.get("0.174"),
                       "r_eff": loglog_interp(g, r_eff)[0], "r_eff_status": loglog_interp(g, r_eff)[1]}

    # ---- session / live block
    usage_s = None
    job_ids, statuses = [], []
    if session:
        jobs = [j for j in session.get("jobs", []) if j.get("job_id")]
        job_ids = [j["job_id"] for j in jobs]
        statuses = [j.get("status") for j in jobs]
        us = [j.get("usage_s") for j in jobs if j.get("usage_s") is not None]
        usage_s = float(sum(us)) if us else None
    ret_fp = (session or {}).get("retrieval_calibration_fingerprint")
    ret_diff = None
    if ret_fp and ret_fp != pre["calibration"]["fingerprint"] and (session or {}).get("retrieval_calibration_file"):
        d = calibration_diff(prereg_rec, load_json(session["retrieval_calibration_file"]))
        ret_diff = {k: d[k] for k in ("n_leaves", "families", "max_ratio", "min_ratio")}
    acct = {}
    for lab, pat in (("before", p(prep, "account_check_*.json")),
                     ("after", p(os.path.dirname(os.path.normpath(cdir)), "account_check_after_*.json"))):
        fs = sorted(glob.glob(pat))
        if fs:
            a = load_json(fs[-1])
            acct[lab] = {"file": rel(fs[-1]), "usage": a.get("usage"), "backend": a.get("backend")}

    dec = {"dry_run": dry,
           "f_pool": pool68["f_clean"], "f_pool_68": pool68["f_clean_68"], "f_pool_95": pool95["f_clean_68"],
           "f_pool_n_reference": pool68["n_reference"], "f_pool_expected_from_garbage": pool68["expected_from_garbage"],
           "f_by_circuit": {c: {"reference": circ[c]["f_clean_reference"], "reference_68": circ[c]["f_clean_reference_68"],
                                "reference_95": circ[c]["f_clean_reference_95"], "mixture": circ[c]["f_clean_mixture"],
                                "mixture_68": circ[c]["f_clean_mixture_68"]} for c in AER_GRID},
           "worst_circuit": worst, "worst_circuit_f_95": f_c95[worst],
           "decision": decision,
           "ambiguous_topup_shots": topup["additional_shots_total"] if decision == "AMBIGUOUS" else None,
           "topup_computation": topup,
           "r_eff": r_eff, "r_eff_68": boot.get("r_eff_68"), "r_eff_95": boot.get("r_eff_95"),
           "r_crit_preregistered": R_CRIT_PREREG, "r_crit_day": rc_day,
           "r_verdict": r_verdict(boot.get("r_eff_68")),
           "f_aer_at_r_eff": f_aer_r, "f_aer_at_r_eff_status": f_aer_status,
           "model_ratio_measured_over_aer": ratio_mc, "model_consistent": mc,
           "model_ratio_reference_statistic_both_sides": ratio_mc_ref, "model_consistent_reference_statistic": mc_ref,
           "f_and_r_verdicts_agree": None,
           "shape_ratio_median": float(np.median(shape)) if shape else None,
           "n_qubits_resolved_long": n_res["long"], "n_qubits_resolved_half": n_res["half"],
           "usage_s": usage_s}
    rv = dec["r_verdict"]
    if rv in ("above", "below"):
        dec["f_and_r_verdicts_agree"] = ((decision == "GO") == (rv == "above")) if decision != "AMBIGUOUS" else None

    # ---- criteria
    R = GateResult(out, ("ibm_kingston pilot on the selected patch: windowed Ramsey at two lengths (T2*/T2_echo "
                         "ratio r_eff vs r_crit), T1, the signed k = 1 circuits' direct f_clean; GO/NO-GO on "
                         "f >= 0.1 (measurement gate)") + (" -- DRY RUN" if dry else ""))
    k1_info = {}
    if dry:
        R.add("K1 preregistration before data", "n/a (dry run)", "device run only", True)
        R.add("K2 one job DONE, usage <= 60 s, estimate <= 30 s, 8 x 4000 counts, DD/twirling off",
              "n/a (dry run)", "device run only", True)
    else:
        sub = (session.get("jobs") or [{}])[0].get("submitted")
        h, tc = git_commit_time(pre["commit"])
        ha, ta = git_added(pre_path)
        fp_ok = (session.get("prereg_calibration_fingerprint") == pre["calibration"]["fingerprint"]
                 == session.get("calibration_fingerprint"))
        before = (tc is not None and sub is not None and _utc(tc) < _utc(sub)
                  and ta is not None and _utc(ta) < _utc(sub))
        k1_info = {"prereg_commit": pre["commit"], "prereg_commit_full": h, "prereg_commit_time": tc,
                   "prereg_added_in": ha, "prereg_added_time": ta, "submitted": sub,
                   "fingerprints_equal": fp_ok, "retrieval_fingerprint": ret_fp,
                   "retrieval_match": (None if ret_fp is None else ret_fp == pre["calibration"]["fingerprint"]),
                   "retrieval_diff": ret_diff}
        R.add("K1 preregistration committed before the submission; prereg = session = submission fingerprint; "
              "retrieval fingerprint recorded (a move is information)",
              f"prereg commit {tc}, added {ha and ha[:7]} {ta}, submitted {sub}; fingerprints equal {fp_ok}; "
              f"retrieval match {k1_info['retrieval_match']}",
              "commit < submission, equal fingerprints, retrieval recorded",
              before and fp_ok and ret_fp is not None and not missing_keys)
        est = ((session.get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s")
        so = session.get("sampler_options") or {}
        opts_ok = (so.get("dynamical_decoupling") == {"enable": False}
                   and so.get("twirling") == {"enable_gates": False, "enable_measure": False})
        shots_ok = len(records) == 8 and all(int(sum(c.values())) == SHOTS for _m, c in records)
        k2 = (len(job_ids) == 1 and statuses == ["DONE"] and usage_s is not None and usage_s <= MAX_USAGE_S
              and est is not None and est <= MAX_ESTIMATE_S and shots_ok and opts_ok)
        R.add("K2 one job DONE, usage_s recorded <= 60, preflight estimate <= 30 s, 8 counts files x 4000 shots, "
              "DD off and twirling off", f"jobs {job_ids} {statuses}, usage {usage_s} s, estimate "
              f"{_f(est, '{:.2f}')} s, counts ok {shots_ok}, options off {opts_ok}", "all hold", k2)
    if dry:
        nz = sum(1 for v in (dry_k3_block or {}).get("per_qubit", {}).values()
                 if abs(v["d00"]["z"]) <= 3 and abs(v["d11"]["z"]) <= 3)
        maxz = max((max(abs(v["d00"]["z"]), abs(v["d11"]["z"])) for v in (dry_k3_block or {}).get("per_qubit", {}).values()),
                   default=None)
        R.add("K3 readout confusion of the patch (all-0 / all-1 pubs) (dry run: agreement with the snapshot's "
              "readout model; the device criterion >= 0.9 is evaluated only on device counts)",
              f"{nz}/12 qubits with |z| <= 3 on both diagonals (max |z| {_f(maxz, '{:.2f}')}); min diagonal "
              f"{_f(None if not ro else ro['min_diagonal'])} (information); live expectation min "
              f"{ro_live['min']:.4f} (qubit {ro_live['min_qubit']})",
              f"all 12 within 3 binomial sigma; live expectation >= {DIAG_MIN}",
              bool(dry_k3_block and dry_k3_block["ok"]) and nz == len(patch) and ro_live["min"] >= DIAG_MIN)
    else:
        R.add("K3 readout confusion of the patch (all-0 / all-1 pubs): smallest diagonal",
              None if not ro else round(ro["min_diagonal"], 4), f">= {DIAG_MIN}",
              bool(ro) and device_k3(ro["min_diagonal"]))
    R.add("K4 decoder round trip over every accepted string of the three coarse pubs",
          f"{rt['mismatches']} mismatches over {rt['distinct_accepted_strings']} strings", "0", rt["mismatches"] == 0)
    n_meas = sum(1 for q in patch if ramsey[str(q)]["provenance"] == "measured")
    n_bound = sum(1 for q in patch if ramsey[str(q)]["long"]["within_echo_bound_3sigma"]
                  and ramsey[str(q)]["half"]["within_echo_bound_3sigma"])
    n_rate = sum(1 for q in patch if t1rows[q]["rate_within_band"])
    r_ok = (r_eff is not None and math.isfinite(r_eff) and boot.get("r_eff_68") is not None
            and boot.get("r_eff_95") is not None)
    k5 = n_meas >= IDLE_QUBITS_MIN and n_bound >= IDLE_QUBITS_MIN and n_rate >= IDLE_QUBITS_MIN and r_ok
    k5_val = (f"T2* measured {n_meas}/12; P0 <= echo bound + {SIGMA:.0f} sigma at both windows {n_bound}/12; "
              f"1/T1 in [{RATE_LO}, {RATE_HI}] x record {n_rate}/12; r_eff {_f(r_eff)} 68 % "
              f"{_iv(boot.get('r_eff_68'))} 95 % {_iv(boot.get('r_eff_95'))}")
    if dry:
        n_dry = sum(1 for q in patch if ramsey[str(q)].get("dry_run_T2star_within_3sigma_of_snapshot_echo"))
        k5 = k5 and n_dry >= IDLE_QUBITS_MIN
        k5_val += f"; dry run: T2* within 3 sigma of the snapshot's echo T2 {n_dry}/12"
    R.add("K5 idle tests (reference record: " + ("the FakeKingston snapshot" if dry else "the prereg's patch record") + ")",
          k5_val, f">= {IDLE_QUBITS_MIN} of 12 each; r_eff finite with both intervals", k5)
    ex_ok = all(mans[c]["exactness"]["ok"] and mans[c]["exactness"]["max_abs_delta"] < 1e-10
                and mans[c]["exactness"]["leakage"] < 1e-9 for c in AER_GRID)
    sched_ok = all((mans[c].get("schedule_info") or {}).get("method") == "alap" for c in AER_GRID)
    ops_ok = all(mans[c].get("ops_as_intended") for c in ("kpilot_ramw_long", "kpilot_ramw_half", "kpilot_t1w_long"))
    dry_gate = None
    if not dry:
        dp = p("validation", "H0_kpilot_dryrun.json")
        dry_gate = load_json(dp)["status"] if os.path.exists(dp) else None
    k6 = ex_ok and sched_ok and ops_ok and (dry or dry_gate == "PASS")
    R.add("K6 circuits: exactness of the three coarse circuits at build, ALAP scheduling asserted, idle-pub op "
          "multisets as intended" + ("" if dry else ", dry-run gate PASS"),
          f"exact {ex_ok} (max |d| {max(mans[c]['exactness']['max_abs_delta'] for c in AER_GRID):.1e}), alap {sched_ok}, "
          f"ops {ops_ok}" + ("" if dry else f", dry run {dry_gate}"), "all hold", k6)
    cells_ok = all(d is not None and d["strided_seeds"] for cs in pre["aer"].values() for d in cs.values())
    k7r = pre["k7_reproduction"]
    k7_repro = (k7r.get("within_tolerance") is True) if k7r.get("mapping_reproduced") else True
    R.add("K7 every preregistered Aer cell present with strided seeds; r = 1 B0_ref06_k1 within 25 % of "
          "S2D_levers' L1_seed_alap cell (mapping reproduced)",
          f"cells {cells_ok}; day {_f(k7r.get('day_value'))} vs {k7r['reference_value']:.4f} (dev "
          f"{_f(k7r.get('relative_deviation'), '{:.3f}')})", "present, strided, <= 0.25", cells_ok and k7_repro)
    miss = decision_complete(dec)
    recomputed = decide(dec["f_pool_95"], {c: dec["f_by_circuit"][c]["reference_95"] for c in K1_IDS})
    R.add("K8 data.decision complete and reproduces the preregistered rule from the recorded intervals",
          f"missing {miss}; decision {decision}, recomputed {recomputed}", "complete and equal",
          not miss and recomputed == decision)
    if args.skip_tests:
        checks = {"skipped": True, "ok": None}
        R.add("K9 pytest -q tests and scripts/check_package.py", "n/a (--skip-tests" + (", dry run)" if dry else ")"),
              "all pass", dry)
    else:
        checks = G.run_checks(False)
        R.add("K9 pytest -q tests and scripts/check_package.py",
              f"pytest: {checks.get('pytest_summary')}; check_package rc {checks.get('check_package_returncode')}",
              "all pass", checks["ok"])

    R.data = {
        "what_pass_means": ("preregistered, measured, verified, consistent; there is no criterion on f, r_eff or "
                            "the decision: a NO-GO pilot is a PASS gate"),
        "dry_run": dry, "versions": versions(),
        "prereg": pre_path, "prereg_created": pre["created"], "prereg_commit": pre["commit"],
        "prereg_keys_missing": missing_keys,
        "calibration_prereg": pre["calibration"],
        "reference_record": ("FakeKingston snapshot over the pilot's qubits" if dry else pre["calibration"]["path"]),
        "reference_record_fingerprint": refrec["fingerprint"],
        "patch": patch, "windows": pre["windows"], "pubs": pre["pubs"],
        "execution_estimate_prereg_s": pre["execution_estimate"]["total_execution_s"],
        "counts_dir": rel(cdir), "session_file": rel(spath) if session else None,
        "live": {"job_ids": job_ids, "statuses": statuses, "usage_s": usage_s,
                 "submission_fingerprint": (session or {}).get("calibration_fingerprint"),
                 "prereg_fingerprint_match": (session or {}).get("prereg_fingerprint_match"),
                 "retrieval_fingerprint": ret_fp, "retrieval_diff": ret_diff,
                 "preflight_estimate_s": (((session or {}).get("preflight") or {}).get("qpu_time_estimate") or {}).get("total_execution_s"),
                 "sampler_options": (session or {}).get("sampler_options"), "account": acct, "K1": k1_info},
        "readout": ro, "readout_survival_product": ro_survival,
        "readout_expected_live": ro_live, "dry_run_K3": dry_k3_block,
        "analysis_change_21a": {"commit": _commit_with_subject("H0_kpilot: dry-run K3 reads the snapshot"),
                                 "text": ("dry-run K3 form changed (prompts/21a option (a)); device K3 >= 0.9 "
                                          "unchanged; no prereg number edited")},
        "ramsey": ramsey, "t1": {str(q): v for q, v in t1rows.items()},
        "r_eff_block": {"r_eff": r_eff, "bootstrap": boot, "S_T2_measured_T2star": s_star, "S_T2_echo": s_echo,
                        "idle_weighted_harmonic_ratio": harm, "windows": "ALAP B0_ref06_k1 explicit delays, leading excluded",
                        "n_windows": sum(len(v) for v in windows_by_q.values()),
                        "idle_s_per_qubit": {str(q): v for q, v in idle_q.items()}},
        "circuits": circ, "aer_at": aer_at, "pool_68": pool68, "pool_95": pool95,
        "roundtrip": rt, "decision": dec, "checks": checks,
        "budgets_at_f_pool": None,
    }
    try:
        R.data["budgets_at_f_pool"] = budgets_at(pool68["f_clean"], prep, full_rec,
                                                 {int(k): int(v) for k, v in pre["selection"]["winner_mapping"].items()})
    except Exception as exc:                       # information only, never silent
        R.data["budgets_at_f_pool"] = {"status": f"not computed: {type(exc).__name__}: {exc}"}
    R.runtime_s = time.time() - t0
    path = R.save()
    saved = load_json(path)
    name = "H0_kpilot_dryrun.md" if dry else "H0_kpilot_ibm_kingston.md"
    write_report(name, report_text(saved, R))
    print(R.criteria_table())
    print(f"status {saved['status']}; decision {decision}: f_pool {pool68['f_clean']:.4f} 95 % {_iv(pool95['f_clean_68'])}; "
          f"r_eff {_f(r_eff)} 68 % {_iv(boot.get('r_eff_68'))} vs r_crit {R_CRIT_PREREG}; model_consistent {mc}")
    return 0 if saved["status"] == "PASS" else 1


def _commit_with_subject(prefix):
    try:
        out = subprocess.check_output(["git", "log", "--format=%h %s"], cwd=ROOT,
                                      stderr=subprocess.DEVNULL).decode().splitlines()
    except Exception:
        return None
    return next((l.split()[0] for l in out if l.split(" ", 1)[1].startswith(prefix)), None)


def dry_k3_sentence(D):
    b = D.get("dry_run_K3")
    if not b:
        return ""
    return (f"Dry-run K3 (prompts/21a, option (a)): the measured diagonals are compared with the readout model of "
            f"the simulator ({b['model']}) within {b['sigma_k']:.0f} binomial sigma at {b['shots']} shots.  The first "
            f"assembly of this dry run failed the device form (>= 0.9) because qubit {b['min_diagonal_qubit']} carries "
            f"a snapshot readout error of {b['min_diagonal_qubit_snapshot_error']:.4f} against the live record's "
            f"{b['min_diagonal_qubit_live_error']:.4f}; the device criterion is unchanged and is evaluated only on "
            f"device counts.")


def report_text(saved, R):
    from skqd.report import md_table
    D = saved["data"]
    dec = D["decision"]
    live = D["live"]
    dry = D["dry_run"]
    rq = []
    for q, v in D["ramsey"].items():
        rq.append([q, f"{v['long']['raw_P0']:.4f}", _f(v['long']['P0']), _f(v['long']['sigma']),
                   f"{v['half']['raw_P0']:.4f}", _f(v['half']['P0']), _f(v['half']['sigma']),
                   _f(None if v['long']['T2star_s'] is None else v['long']['T2star_s'] * 1e6, "{:.1f}"),
                   _f(None if v['half']['T2star_s'] is None else v['half']['T2star_s'] * 1e6, "{:.1f}"),
                   _f(None if v['T2star_s'] is None else v['T2star_s'] * 1e6, "{:.1f}") + f" ({v['provenance']}, {v['window_used']})",
                   f"{v['T2_echo_s'] * 1e6:.1f}", _f(v['ratio_T2star_over_echo'], "{:.3f}"),
                   _f(v['shape_ratio'], "{:.2f}"), f"{v['long']['echo_bound']:.4f} / {v['half']['echo_bound']:.4f}",
                   f"{v['long']['P0_at_r_0.174']:.4f} / {v['half']['P0_at_r_0.174']:.4f}"])
    t1 = [[q, f"{v['raw_P_one']:.4f}", _f(v['P_survive']), f"{v['P_survive_predicted']:.4f}",
           _f(None if v['T1_measured_s'] is None else v['T1_measured_s'] * 1e6, "{:.1f}"), f"{v['T1_record_s'] * 1e6:.1f}",
           _f(v['rate_ratio'], "{:.2f}"), "yes" if v['rate_within_band'] else "no"] for q, v in D["t1"].items()]
    cr = []
    for cid, c in D["circuits"].items():
        a = D["aer_at"][cid]
        cr.append([cid, c["shots"], c["accepted"], c["reference_hits"], f"{c['expected_reference_hits_from_garbage']:.2f}",
                   _f(c["P_ge"], "{:.2e}"), f"{c['p_reference']:.4f}",
                   f"{_f(c['f_clean_reference'])} {_iv(c['f_clean_reference_68'])} {_iv(c['f_clean_reference_95'])}",
                   f"{_f(c['f_clean_mixture'])} {_iv(c['f_clean_mixture_68'])}", _f(c["c6_relative_deviation"], "{:.3f}"),
                   f"{_f(a['r=1'])} / {_f(a['r_eff'])} / {_f(a['r=0.174'])}", str(c["distance_histogram"])])
    rb = D["r_eff_block"]
    ro = D["readout"] or {}
    bud = D.get("budgets_at_f_pool") or {}
    k1 = live.get("K1") or {}
    acct = live.get("account") or {}
    ub = (acct.get("before") or {}).get("usage") or {}
    ua = (acct.get("after") or {}).get("usage") or {}
    title = "dry run (local Aer on the FakeKingston snapshot; a path check, not a prediction)" if dry else "ibm_kingston"
    return f"""# Gate {saved['gate']} -- the kingston T2* pilot, {title}

**Status: {saved['status']}** -- `scripts/gate_H0_kpilot.py --stage assemble --counts {D['counts_dir']}{' --dry-run' if dry else ''} --out {saved['gate']}`.
Runtime {saved['runtime_s']:.0f} s.  Every number below is computed by the script from the raw counts and from
`{D['prereg']}` and is stored in `validation/{saved['gate']}.json`.

## 0. What PASS means

{D['what_pass_means']}.

## 1. The decision{' (dry_run: true)' if dry else ''}

| quantity | value |
|---|---|
| f_pool (reference-string statistic, two k = 1 circuits) | **{_f(dec['f_pool'])}** 68 % {_iv(dec['f_pool_68'])}, 95 % {_iv(dec['f_pool_95'])} |
| pooled reference hits / garbage expectation | {dec['f_pool_n_reference']} / {dec['f_pool_expected_from_garbage']:.2f} |
| worst circuit ({dec['worst_circuit']}) f 95 % | {_iv(dec['worst_circuit_f_95'])} against 0.05 |
| **decision** | **{dec['decision']}** |
| top-up shots (only if AMBIGUOUS) | {dec['ambiguous_topup_shots']} |
| r_eff | **{_f(dec['r_eff'])}** 68 % {_iv(dec['r_eff_68'])}, 95 % {_iv(dec['r_eff_95'])} |
| r_crit preregistered / day | {dec['r_crit_preregistered']} / {_f(dec['r_crit_day'])} |
| r verdict | {dec['r_verdict']} |
| f_Aer(r_eff) (B0_ref06_k1, mixture grid) | {_f(dec['f_aer_at_r_eff'])} ({dec['f_aer_at_r_eff_status']}) |
| measured / Aer, model_consistent (factor 3) | {_f(dec['model_ratio_measured_over_aer'], '{:.3f}')}, {dec['model_consistent']} |
| same with the reference statistic on both sides | {_f(dec['model_ratio_reference_statistic_both_sides'], '{:.3f}')}, {dec['model_consistent_reference_statistic']} |
| f and r verdicts agree | {dec['f_and_r_verdicts_agree']} |
| shape ratio median (2 = exponential, 4 = Gaussian) | {_f(dec['shape_ratio_median'], '{:.2f}')} |
| qubits resolved long / half | {dec['n_qubits_resolved_long']} / {dec['n_qubits_resolved_half']} |
| usage (s) | {dec['usage_s']} |

Preregistered rule: GO iff f_pool,lo95 >= 0.1 and min_c f_c,lo95 >= 0.05; NO-GO iff f_pool,hi95 < 0.1 or
min_c f_c,hi95 < 0.05; AMBIGUOUS otherwise.  The direct measurement decides f; a disagreement with the r-verdict is a
model finding.

## 2. Preregistration

`{D['prereg']}`, written {D['prereg_created']} at commit `{D['prereg_commit']}` on the patch record
`{D['calibration_prereg']['path']}` (fingerprint `{D['calibration_prereg']['fingerprint']}`).  Patch {D['patch']}; windows
{D['windows']['window_dt']} dt = {D['windows']['window_s'] * 1e9:.0f} ns, N_long {D['windows']['N_long']}
({D['windows']['total_delay_long_s'] * 1e6:.2f} us), N_half {D['windows']['N_half']} ({D['windows']['total_delay_half_s'] * 1e6:.2f} us)
matched to T_s {D['windows']['T_s_matched'] * 1e6:.2f} us; 8 pubs x 4000 shots; execution estimate
{D['execution_estimate_prereg_s']:.2f} s.  Analysis change after the preregistration:
{D['analysis_change_21a']['text']} (commit `{D['analysis_change_21a']['commit']}`).

## 3. Live block

| item | value |
|---|---|
| job id(s) / status | {live['job_ids']} / {live['statuses']} |
| usage (s) | {live['usage_s']} |
| preflight estimate (s) | {live['preflight_estimate_s']} |
| fingerprint at prereg / submission / retrieval | `{D['calibration_prereg']['fingerprint'][:16]}` / `{(live['submission_fingerprint'] or 'n/a')[:16]}` / `{(live['retrieval_fingerprint'] or 'n/a')[:16]}` |
| prereg match at submission | {live['prereg_fingerprint_match']} |
| retrieval diff | {live['retrieval_diff']} |
| prereg commit time / submitted | {k1.get('prereg_commit_time')} (added in {k1.get('prereg_added_in')}, {k1.get('prereg_added_time')}) / {k1.get('submitted')} |
| account usage before / after | {ub.get('usage_consumed_seconds')} s ({ub.get('usage_remaining_seconds')} left) / {ua.get('usage_consumed_seconds')} s ({ua.get('usage_remaining_seconds')} left) |
| sampler options | {live['sampler_options']} |

## 4. Readout

Smallest confusion diagonal {_f(ro.get('min_diagonal'))}; measured readout survival of the patch prod_q (1 - e_q)
= {_f(D['readout_survival_product'])} (the analysis applies the manual's factor 0.82).  Preregistered live expectation
(1 - measure_error of the patch record): min {D['readout_expected_live']['min']:.4f} on qubit {D['readout_expected_live']['min_qubit']}.
{dry_k3_sentence(D)}

## 5. Windowed Ramsey (readout-corrected; T2* by rule S3)

{md_table(["qubit", "raw P0 long", "P0 long", "sigma", "raw P0 half", "P0 half", "sigma", "T2* long (us)", "T2* half (us)",
           "T2* used (us)", "T2 echo (us)", "T2*/T2 echo", "shape ratio", "echo bound long / half", "P0 at r=0.174 long / half"], rq)}

## 6. Windowed T1

{md_table(["qubit", "raw P1", "P1 corrected", "P1 predicted", "T1 measured (us)", "T1 record (us)", "rate ratio", "in band"], t1)}

## 7. r_eff against r_crit

r_eff = **{_f(rb['r_eff'])}** (68 % {_iv((rb['bootstrap'] or {}).get('r_eff_68'))}, 95 % {_iv((rb['bootstrap'] or {}).get('r_eff_95'))};
{(rb['bootstrap'] or {}).get('draws')} bootstrap draws, {(rb['bootstrap'] or {}).get('failed')} failed) on {rb['n_windows']} delay windows
({rb['windows']}); S_T2 at the measured T2* {_f(rb['S_T2_measured_T2star'], '{:.3f}')} against {_f(rb['S_T2_echo'], '{:.3f}')} at the echo T2;
idle-weighted harmonic mean of T2*/T2_echo {_f(rb['idle_weighted_harmonic_ratio'], '{:.3f}')}.  Preregistered r_crit {dec['r_crit_preregistered']};
the day's {_f(dec['r_crit_day'])}.

## 8. The circuits

{md_table(["circuit", "shots", "accepted", "ref hits", "garbage expectation", "P_ge", "p_ref",
           "f_clean reference [68 %] [95 %]", "f_clean mixture [68 %]", "C6 dev (info)", "Aer f r=1 / r_eff / 0.174",
           "distance histogram"], cr)}

B0_ref06_k4 is information only (C6 ruling: the estimators are not tolerance-calibrated at p_ref 0.13).

## 9. Budgets at the measured f_pool (information)

{json.dumps({k: v for k, v in bud.items() if k != 'note'})}
{bud.get('note', '')}

## 10. Honest limits

- r_eff is one number for a patch whose per-qubit ratios may spread an order of magnitude (this patch: T2*/T2_echo
  {_f(min((v['ratio_T2star_over_echo'] for v in D['ramsey'].values() if v['ratio_T2star_over_echo'] is not None), default=None), '{:.3f}')}-{_f(max((v['ratio_T2star_over_echo'] for v in D['ramsey'].values() if v['ratio_T2star_over_echo'] is not None), default=None), '{:.3f}')}; fez: 0.070-1.209); the uniform-r axis is the one r_crit is defined on, and the per-qubit table is beside it.
- Aer's dephasing on a delay is exponential; the shape ratio (median {_f(dec['shape_ratio_median'], '{:.2f}')}; 2 exponential, 4 Gaussian) tests
  that with two lengths only.  A Gaussian decay makes the many short windows of the circuit less harmful than the long Ramsey
  windows suggest -- the direction in which the r-verdict could be pessimistic while the f-verdict is not; that is why f is primary.
- Two k = 1 circuits are not the 28-circuit family; the S2D bar is read on them as a pilot.  The k = 4 cell's f is information.
- The readout factor 0.82 of manual Step 4.4 is applied to both statistics and to the Aer predictions; the patch's measured
  readout survival is {_f(D['readout_survival_product'])}.
- One job on one calibration content; a drift between submission and retrieval is reported (retrieval diff above), not corrected.

## 11. Criteria

{R.criteria_table()}
"""


# --------------------------------------------------------------------------- driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--circuit", nargs="*", default=None)
    ap.add_argument("--ratio", nargs="*", type=float, default=None)
    ap.add_argument("--chunk", nargs="*", type=int, default=None)
    ap.add_argument("--prep", default=PREP)
    ap.add_argument("--prereg", default=None)
    ap.add_argument("--counts", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    stages = {"aer": stage_aer}
    for name, fn in (("predict", "stage_predict"), ("prereg-md", "stage_prereg_md"),
                     ("assemble", "stage_assemble")):
        if fn in globals():
            stages[name] = globals()[fn]
    if args.stage not in stages:
        raise SystemExit(f"unknown stage {args.stage}; one of {sorted(stages)}")
    return stages[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
