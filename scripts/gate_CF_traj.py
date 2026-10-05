#!/usr/bin/env python3
"""
Gate CF_traj (prompts/28 Part A, A3): the decisive trajectory test of the A6 reference-hit excess.

Reads the raw trajectory chunks written by scripts/cf_trajectories.py (data/cf_trajectories/<id>[__xx]/),
the A4 counting-control counts (data/cf_trajectories/control_xx/), the A0 timing record, the A6 dry-run
counts (data/hardware/Q0P_2x3_dryrun/) and the phase-only check (data/quantinuum/a6_phase_error_check.json),
audits the A6 Aer path, runs the package checks, and writes validation/CF_traj.json + reports/CF_traj.md
through skqd.report.GateResult (no typed numbers).

Definitions (prompts/28; planner's labels, not manual terms):
  g0   = (1 - 15/16 p2)^n_zz (1 - 3/4 p1)^n_1q        probability of no gate-error event
  f0'  = g0 x readout survival of the reference string  (predict.json aer_channel_no_error_probability)
  h_ref = <p_tau(ref)> over FAULTY trajectories (post-readout)
  f_hit^traj = f0' + (1 - f0') h_ref / p_ref,  rho_ref = f_hit^traj / f0'
  f_T^traj   = f0' + (1 - f0') <sum_{T_c} p_tau> / sum_{T_c} p_c,  rho_T = f_T^traj / f0'
  f_eff(s)   = f0' + (1 - f0') <p_tau(s)> / p_c(s)
  T_c = {s : p_c(s) >= 1e-3, s != ref};  benign = TV(sector-normalised p_tau, p_c) < 1e-3 (pre-readout)
Intervals: 95 % bootstrap percentile over trajectories (B = 2000, seed 2028); means also with s.e.

Run in the isolated venv (the A6-path audit reads the frozen pytket circuits):
  ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/gate_CF_traj.py [--skip-checks]
"""
from __future__ import annotations

import argparse
import glob
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

from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402

import cf_trajectories as cf  # noqa: E402

GATE = "CF_traj"
TITLE = "Pauli-trajectory decomposition of the A6 reference-hit excess (prompts/28 Part A)"
WHAT_PASS_MEANS = (
    "the excess of reference-string hits over the fault-free expectation in the A6 Aer run is reproduced by "
    "an independent Pauli-trajectory decomposition of the same channel on the same circuit, and a bit-flip-only "
    "control gives the fault-free count; the reference-string estimator therefore measures the "
    "clean-plus-near-clean fraction, not the fault-free fraction.  PASS says nothing about any device.")
CIRC = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
DRYRUN = os.path.join(ROOT, "data", "hardware", "Q0P_2x3_dryrun")
PREDICT = os.path.join(ROOT, "data", "quantinuum", "q0p_stages", "predict.json")
PHASE = os.path.join(ROOT, "data", "quantinuum", "a6_phase_error_check.json")
CODING_PY = "/home/digimonk/anaconda3/envs/coding/bin/python"
VENV_PY = os.path.join(os.path.expanduser("~"), ".local", "share", "su2qc-quantinuum", "venv", "bin", "python")
PINS_EXPECTED = {"python": "3.12.14", "qiskit": "2.5.2", "qiskit-aer": "0.17.2",
                 "qiskit-ibm-runtime": "0.49.0", "numpy": "2.5.2", "scipy": "1.18.0"}
# prompts/28 A2: arms, planned K and seeds (the xx arm's seed is the executor's choice: A4 gives none)
ARMS = {"B0_ref25_k1": {"channel": "depol", "K": 720, "seeds": [101, 102, 103]},
        "B1_ref57_k1": {"channel": "depol", "K": 240, "seeds": [201]},
        "B0_ref25_k4": {"channel": "depol", "K": 240, "seeds": [301]}}
XX_ARM = {"id": "B0_ref25_k1", "channel": "xx", "K": 120, "seeds": [401]}
A6_SHOTS_PER_K1 = 140                 # the A6 dry run (predict.json dryrun.jobs)
PHASE_SHOTS = 40
CONTROL_SHOTS = 280
MARGIN = 0.7                          # rule D3'-R margin
RHO_T_STOP = 1.5                      # prompts/28: STOP (planner) if rho_T > 1.5 on any arm
LOW_SIDE_SIGMAS = 3.0                 # prompts/28 C2: low-side failure by > 3 standard errors -> STOP
P_MIN = 0.05                          # C2: two-sided Poisson P >= 0.05
N_BOOT, BOOT_SEED = 2000, 2028
PROMPT_C5_LITERAL_1Q = 3053           # prompts/28 C5 as typed; compared, see c5 notes


def load_json(p):
    with open(p) as fh:
        return json.load(fh)


def two_sided_poisson_p(k: int, mu: float) -> float:
    from scipy.stats import poisson

    return float(min(1.0, 2.0 * min(poisson.cdf(k, mu), poisson.sf(k - 1, mu))))


def poisson_band(mu: float, conf: float = 0.95) -> list:
    from scipy.stats import poisson

    a = (1.0 - conf) / 2.0
    return [int(poisson.ppf(a, mu)), int(poisson.ppf(1.0 - a, mu))]


def clopper_pearson(k: int, n: int, conf: float = 0.95) -> list:
    from scipy.stats import beta

    a = (1.0 - conf) / 2.0
    lo = 0.0 if k == 0 else float(beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a, k + 1, n - k))
    return [lo, hi]


def ival(point, boot):
    boot = np.asarray(boot, float)
    return {"value": float(point), "se_boot": float(np.std(boot, ddof=1)),
            "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]}


def ref_hits(counts_rec: dict, ref_int: int) -> int:
    from skqd.reference_sim import bits_to_int, qiskit_key_to_bits

    return int(sum(v for k, v in counts_rec["counts"].items() if bits_to_int(qiskit_key_to_bits(k)) == int(ref_int)))


# =========================================================================== arm statistics
def load_arm(cid, channel):
    chunks = cf.load_chunks(cid, channel)
    if not chunks:
        return None
    base = chunks[0][1]
    trajs = [t for _f, c in chunks for t in c["trajectories"]]
    return {"chunks": chunks, "base": base, "trajs": trajs}


def arm_statistics(cid: str, arm: dict, man: dict, A6: dict, predict: dict | None) -> dict:
    base, trajs = arm["base"], arm["trajs"]
    K = len(trajs)
    p2, p1 = A6["depolarizing_2q_rzz"], A6["depolarizing_1q_rx_ry"]
    p10, p01 = A6["readout_p1_given_0"], A6["readout_p0_given_1"]
    c = man["counts"]
    g0 = cf.no_error_probability(c["n_zz"], c["n_phasedx"], p2, p1)
    r_ref = cf.readout_survival(man["reference_bits"], p10, p01)
    f0 = g0 * r_ref
    checks = {"g0_vs_chunk_abs": abs(g0 - base["no_error_probability_g0"]),
              "readout_survival_vs_chunk_abs": abs(r_ref - base["readout_survival_reference"])}
    pred = (predict or {}).get("dryrun", {}).get("predictions", {}).get(cid)
    if pred:
        checks["f0_vs_predict_json_abs"] = abs(f0 - float(pred["aer_channel_no_error_probability"]))
    checks["f0_check_ok"] = all(v < 1e-12 for k, v in checks.items() if k.endswith("_abs"))
    sec = base["sector"]
    pc = np.asarray(base["ideal"]["p_c"], float)
    p_ref = float(man["p_reference"])
    tail = np.asarray(sec["tail_pos"], int)
    pT = float(pc[tail].sum())
    S99, S999 = np.asarray(sec["S99"], int), np.asarray(sec["S999"], int)
    h = np.array([t["p_ref_post"] for t in trajs])
    h_pre = np.array([t["p_ref_pre"] for t in trajs])
    tl = np.array([t["tail_post"] for t in trajs])
    tv = np.array([t["tv_pre"] for t in trajs])
    zo = np.array([t["z_only"] for t in trajs], bool)
    n2 = np.array([t["n_2q"] for t in trajs])
    n1 = np.array([t["n_1q"] for t in trajs])
    P = np.array([t["p_sector_post"] for t in trajs])
    benign = tv < cf.BENIGN_TV

    def derived(w):
        """All statistics for trajectory weights w (sum 1): the point (w = 1/K) and each bootstrap draw."""
        hm = float(w @ h)
        tm = float(w @ tl)
        Pm = w @ P
        f_hit = f0 + (1 - f0) * hm / p_ref
        f_T = f0 + (1 - f0) * tm / pT
        with np.errstate(divide="ignore", invalid="ignore"):
            feff = np.where(pc > 0, f0 + (1 - f0) * Pm / np.where(pc > 0, pc, 1.0), np.nan)
        r99, r999 = feff[S99] / f0, feff[S999] / f0
        tail99 = [s for s in S99 if pc[s] >= cf.TAIL_P_MIN]
        tail999 = [s for s in S999 if pc[s] >= cf.TAIL_P_MIN]
        return {"h_ref": hm, "f_hit": f_hit, "rho_ref": f_hit / f0, "tail_mean": tm, "f_T": f_T,
                "rho_T": f_T / f0, "benign_fraction": float(w @ benign),
                "min_feff_over_f0_S99": float(np.nanmin(r99)), "min_feff_over_f0_S999": float(np.nanmin(r999)),
                "median_feff_over_f0_S99": float(np.nanmedian(r99)),
                "median_feff_over_f0_S999": float(np.nanmedian(r999)),
                "max_feff_over_f0_S99": float(np.nanmax(r99)), "max_feff_over_f0_S999": float(np.nanmax(r999)),
                "min_feff_over_f0_S99_tail": float(np.min(feff[tail99] / f0)) if tail99 else None,
                "max_feff_over_f0_S99_tail": float(np.max(feff[tail99] / f0)) if tail99 else None,
                "min_feff_over_f0_S999_tail": float(np.min(feff[tail999] / f0)) if tail999 else None,
                "max_feff_over_f0_S999_tail": float(np.max(feff[tail999] / f0)) if tail999 else None,
                "min_feff_over_fT_S99": float(np.nanmin(feff[S99]) / f_T),
                "n_S99_p_c_zero": int(np.sum(pc[S99] <= 0)), "n_S999_p_c_zero": int(np.sum(pc[S999] <= 0)),
                "n_S99_feff_below_margin_fT": int(np.sum(feff[S99] < MARGIN * f_T)),
                "_feff": feff}

    point = derived(np.full(K, 1.0 / K))
    rng = np.random.default_rng(BOOT_SEED)
    W = rng.multinomial(K, np.full(K, 1.0 / K), size=N_BOOT) / K
    boots = [derived(w) for w in W]
    stats = {}
    for key, v in point.items():
        if key.startswith("_") or v is None:
            continue
        stats[key] = ival(v, [b[key] for b in boots])
    stats["h_ref"]["se_analytic"] = float(np.std(h, ddof=1) / math.sqrt(K))
    stats["tail_mean"]["se_analytic"] = float(np.std(tl, ddof=1) / math.sqrt(K))
    nb = int(benign.sum())
    stats["benign_fraction"]["ci95_clopper_pearson"] = clopper_pearson(nb, K)
    feff = point["_feff"]
    per_state = []
    for rank, s in enumerate(S999):
        per_state.append({"pos": int(s), "int": int(sec["ints"][s]), "rank": rank, "in_S99": bool(rank < len(S99)),
                          "p_c": float(pc[s]), "mean_p_tau_post": float(P[:, s].mean()),
                          "feff_over_f0": float(feff[s] / f0), "in_tail_class": bool(int(s) in set(tail.tolist())),
                          "is_reference": bool(int(s) == int(sec["ref_pos"]))})
    # exact decomposition (information): E[hit]/N = g0 * ideal post-readout p(ref) + (1 - g0) h_ref
    p_ref_post0 = float(base["ideal"]["p_ref_post_readout"])
    hit_exact = g0 * p_ref_post0 + (1 - g0) * point["h_ref"]
    hit_prompt = f0 * p_ref + (1 - f0) * point["h_ref"]
    # Z-only stratum (pre-readout: the phase-only check had no readout error)
    zs = {"n_z_only": int(zo.sum()), "fraction_z_only": float(zo.mean())}
    if zo.any():
        zs["h_Z"] = float(h_pre[zo].mean())
        zs["h_Z_se"] = float(np.std(h_pre[zo], ddof=1) / math.sqrt(zo.sum())) if zo.sum() > 1 else None
        # importance reweighting to the phase channel (Z events at the full event rate):
        # P_phase(tau) / P_depol(tau) = 5^n2 3^n1 for Z-type tau (2q: (e2/3)/(e2/15); 1q: e1/(e1/3))
        w = np.where(zo, 5.0 ** n2 * 3.0 ** n1, 0.0)
        zs["phase_channel_reweighted"] = {
            "mean_weight": float(w.mean()), "mean_weight_expected": 1.0,
            "h_faulty_unnormalised": float(np.mean(w * h_pre)),
            "h_faulty_self_normalised": float(np.sum(w * h_pre) / np.sum(w)),
            "note": ("information: the Z-only stratum of the depolarizing draws is weighted towards ONE event "
                     "(each extra Z event costs a factor 1/5 or 1/3), whereas the phase-only check draws Z events "
                     "at the full event rate; this importance-reweighted mean is the phase channel's faulty-shot "
                     "average estimated from the same trajectories (unbiased, high variance)")}
    events_hist = {"n_events": {str(k): int(np.sum(n2 + n1 == k)) for k in sorted(set((n2 + n1).tolist()))}}
    by_z = {"h_ref_z_only": float(h[zo].mean()) if zo.any() else None,
            "h_ref_not_z_only": float(h[~zo].mean()) if (~zo).any() else None,
            "tail_z_only": float(tl[zo].mean()) if zo.any() else None,
            "tail_not_z_only": float(tl[~zo].mean()) if (~zo).any() else None}
    chunks = [{"file": os.path.relpath(f, ROOT), "chunk": c["chunk"], "seed": c["seed"], "K": c["K"],
               "git_commit": c["git_commit"], "git_dirty_scripts_src": c["git_dirty_scripts_src"],
               "wall_s": c["wall_s"], "workers": c["workers"], "n_draws": c["n_draws"],
               "n_rejected_all_identity": c["n_rejected_all_identity"],
               "crosscheck_from_scratch_max_abs_dprob": next(
                   (t["crosscheck_from_scratch_max_abs_dprob"] for t in c["trajectories"]
                    if "crosscheck_from_scratch_max_abs_dprob" in t), None),
               "verify_json_p_sector_max_abs": c["ideal"]["p_sector_vs_verify_json_max_abs"],
               "aer_error_placement_after_gate": c["aer_error_placement_check"]["error_applied_after_gate"]}
              for f, c in arm["chunks"]]
    draws = sum(ch["n_draws"] for ch in chunks)
    rej = sum(ch["n_rejected_all_identity"] for ch in chunks)
    return {
        "id": cid, "channel": base["channel"], "K": K, "chunks": chunks,
        "n_zz": int(c["n_zz"]), "n_phasedx": int(c["n_phasedx"]), "p_ref": p_ref,
        "g0": g0, "readout_survival_reference": r_ref, "f0_prime": f0, "f0_checks": checks,
        "rejection": {"n_draws": draws, "n_rejected": rej, "fraction": rej / draws if draws else None,
                      "expected_g0": g0,
                      "z": (rej - draws * g0) / math.sqrt(draws * g0 * (1 - g0)) if draws else None},
        "tail_class": {"size": int(len(tail)), "p_Tc": pT, "p_min": cf.TAIL_P_MIN},
        "S99_size": int(len(S99)), "S999_size": int(len(S999)),
        "stats": stats,
        "hit_fraction_per_shot": {"prompt_formula_f0p_pref_plus_1mf0_h": hit_prompt,
                                  "exact_g0_pideal_post_plus_1mg0_h": hit_exact,
                                  "difference": hit_exact - hit_prompt,
                                  "f_hit_exact_decomposition": hit_exact / p_ref},
        "z_stratum": zs, "by_error_type": by_z, "event_counts": events_hist,
        "per_state_S999": per_state,
        "_h_se": float(np.std(h, ddof=1) / math.sqrt(K)), "_h_pre_mean": float(h_pre.mean()),
    }


def hamming_block(arm):
    trajs = arm["trajs"]
    m = np.mean([t["hamming_post"] for t in trajs], axis=0)
    ms = np.mean([t["hamming_post_sector"] for t in trajs], axis=0)
    return {"faulty_mean_weight_by_distance": [float(x) for x in m],
            "faulty_mean_in_sector_weight_by_distance": [float(x) for x in ms],
            "ideal_post_readout_weight_by_distance": arm["base"]["ideal"]["hamming_post_readout"]}


# =========================================================================== A6-path audit
def a6_path_audit(mans):
    """The circuit objects run_aer hands to AerSimulator.run for the two A6 circuits, the noise model and the
    simulator options of the dry run; a 1-shot noisy run's metadata (what Aer did with the circuit)."""
    from qiskit_aer import AerSimulator

    import quantinuum_submit as qs
    from skqd import circuits_qiskit as cq
    from skqd import quantinuum_native as qn

    sess = load_json(os.path.join(DRYRUN, "session.json"))
    nm = qs.a6_noise_model()
    out = {"session": os.path.relpath(os.path.join(DRYRUN, "session.json"), ROOT),
           "session_git_commit": sess["git_commit"],
           "sampler": ("quantinuum_submit.run_aer: qcs = [skqd.circuits_qiskit.ir_to_qiskit(ir, n, measure=True)] "
                       "with ir from skqd.quantinuum_native.pytket_to_ir(frozen circuit); "
                       "AerSimulator(noise_model=a6_noise_model(), method='statevector', seed_simulator=aer_seed, "
                       "max_parallel_threads=threads).run(qcs, shots=shots) -- no transpile call on this path"),
           "aer_options": {"method": "statevector", "seed_simulator": [j["aer_seed"] for j in sess["jobs"]],
                           "max_parallel_threads": sess["arguments"]["threads"], "shots": sess["arguments"]["shots"]},
           "noise_model": {"basis_gates": list(nm.basis_gates), "noise_instructions": sorted(nm.noise_instructions),
                           "noise_qubits": sorted(int(q) for q in nm.noise_qubits),
                           "str": str(nm)},
           "circuits": {}}
    ok = True
    for cid in ("B0_ref25_k1", "B1_ref57_k1"):
        man = mans[cid]
        ir, n, qmap = qn.pytket_to_ir(qs.load_frozen(CIRC, man))
        qc = cq.ir_to_qiskit(ir, n, measure=True)
        ops = {k: int(v) for k, v in qc.count_ops().items()}
        n1 = ops.get("rx", 0) + ops.get("ry", 0)
        # consecutive rzz on the same pair with no gate on either qubit in between (what a merge would remove)
        last = {}
        mergeable = 0
        for inst in qc.data:
            qs_ = tuple(sorted(qc.find_bit(q).index for q in inst.qubits))
            name = inst.operation.name
            if name == "rzz":
                if all(last.get(q) == ("rzz", qs_) for q in qs_):
                    mergeable += 1
                for q in qs_:
                    last[q] = ("rzz", qs_)
            elif name not in ("barrier",):
                for q in qs_:
                    last[q] = (name, None)
        rec = {"ops": ops, "n_rzz": ops.get("rzz", 0), "n_noisy_1q_rx_ry": n1,
               "manifest_n_zz": int(man["counts"]["n_zz"]), "manifest_n_phasedx": int(man["counts"]["n_phasedx"]),
               "adjacent_same_pair_rzz_in_executed_circuit": mergeable,
               "one_noisy_1q_rotation_per_phasedx": n1 == int(man["counts"]["n_phasedx"]),
               "rzz_equals_2158": ops.get("rzz", 0) == 2158,
               "measure_map_identity": qmap == {q: q for q in range(n)}}
        ok = ok and rec["one_noisy_1q_rotation_per_phasedx"] and rec["rzz_equals_2158"]
        out["circuits"][cid] = rec
    # what Aer reports for a 1-shot run of the executed B0 circuit under the A6 model
    man = mans["B0_ref25_k1"]
    ir, n, _ = qn.pytket_to_ir(qs.load_frozen(CIRC, man))
    qc = cq.ir_to_qiskit(ir, n, measure=True)
    t0 = time.time()
    res = AerSimulator(noise_model=nm, method="statevector", seed_simulator=11).run(qc, shots=1).result()
    md = res.results[0].metadata
    out["one_shot_metadata"] = {k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(v))
                                for k, v in dict(md).items()}
    out["one_shot_wall_s"] = time.time() - t0
    want = {"rzz", "rx", "ry", "measure"}
    out["noise_instructions_ok"] = set(nm.noise_instructions) == want
    out["ok"] = bool(ok and out["noise_instructions_ok"])
    lo_hi = sorted(int(m["counts"]["n_phasedx"]) for m in mans.values() if m.get("kind") != "calibration")
    out["prompt_c5_literal"] = {
        "typed_value": PROMPT_C5_LITERAL_1Q,
        "phasedx_counts_of_the_44_frozen_circuits": {"min": lo_hi[0], "max": lo_hi[-1]},
        "matches_any_frozen_circuit": PROMPT_C5_LITERAL_1Q in lo_hi,
        "note": ("prompts/28 C5 types 3053 noisy 1q rotations; A3 defines the requirement as 'one noisy 1q rotation "
                 "per PhasedX'.  The A6 circuits carry 3091 (B0_ref25_k1) and 2989 (B1_ref57_k1) PhasedX in their "
                 "manifests; C5 is evaluated against the per-circuit PhasedX count (A3's definition)")}
    return out


# =========================================================================== checks (C6)
def run_checks():
    t0 = time.time()
    out = {}
    for tag, py in (("coding", CODING_PY), ("venv", VENV_PY)):
        r = subprocess.run([py, "-m", "pytest", "-q", "tests"], cwd=ROOT, capture_output=True, text=True)
        out[f"pytest_{tag}"] = {"python": py, "returncode": r.returncode,
                                "summary": (r.stdout.strip().splitlines() or [""])[-1]}
    c = subprocess.run([CODING_PY, os.path.join("scripts", "check_package.py")], cwd=ROOT, capture_output=True, text=True)
    out["check_package"] = {"returncode": c.returncode, "tail": "\n".join(c.stdout.strip().splitlines()[-3:])}
    code = ("import sys,json,qiskit,qiskit_aer,qiskit_ibm_runtime,numpy,scipy;print(json.dumps({'python':"
            "sys.version.split()[0],'qiskit':qiskit.__version__,'qiskit-aer':qiskit_aer.__version__,"
            "'qiskit-ibm-runtime':qiskit_ibm_runtime.__version__,'numpy':numpy.__version__,'scipy':scipy.__version__}))")
    pr = subprocess.run([CODING_PY, "-c", code], capture_output=True, text=True)
    out["pins_now"] = json.loads(pr.stdout.strip().splitlines()[-1])
    out["pins_ok"] = out["pins_now"] == PINS_EXPECTED
    out["seconds"] = time.time() - t0
    out["ok"] = (out["pytest_coding"]["returncode"] == 0 and out["pytest_venv"]["returncode"] == 0
                 and c.returncode == 0 and out["pins_ok"])
    return out


# =========================================================================== main
def fmt(x, nd=4):
    if x is None:
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    x = float(x)
    if x != 0 and (abs(x) < 1e-3 or abs(x) >= 1e5):
        return f"{x:.3e}"
    return f"{x:.{nd}g}"


def fi(d, nd=4):
    return f"{fmt(d['value'], nd)} [{fmt(d['ci95'][0], nd)}, {fmt(d['ci95'][1], nd)}]"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-checks", action="store_true", help="development only: C6 recorded as not run")
    args = ap.parse_args(argv)
    t_start = time.time()
    import quantinuum_submit as qs

    A6 = qs.A6_NOISE
    idx = load_json(os.path.join(CIRC, "index.json"))
    mans = {c: load_json(os.path.join(CIRC, c + ".manifest.json")) for c in idx["circuits"]}
    predict = load_json(PREDICT)
    phase = load_json(PHASE)
    G = GateResult(GATE, TITLE)
    data = {"prompt": "prompts/28_2x3_shot_rule_and_clean_fraction_estimator.md Part A",
            "what_pass_means": WHAT_PASS_MEANS, "A6_NOISE": A6,
            "definitions": __doc__.split("Definitions")[1].split("Run in")[0].strip()}

    # ---------------------------------------------------------------- C1: timing, K, chunk files
    tpath = os.path.join(cf.OUT, "timing_A0.json")
    timing = load_json(tpath) if os.path.exists(tpath) else None
    data["A0_timing"] = timing
    arms, raw = {}, {}
    c1_notes = []
    c1_ok = timing is not None
    for cid, plan in list(ARMS.items()) + [(XX_ARM["id"] + "__xx", XX_ARM)]:
        real = cid.split("__")[0]
        a = load_arm(real, plan["channel"])
        if a is None:
            c1_ok = False
            c1_notes.append(f"{cid}: no chunk files")
            continue
        raw[cid] = a
        arms[cid] = arm_statistics(real, a, mans[real], A6, predict)
        seeds = sorted(ch["seed"] for ch in arms[cid]["chunks"])
        okK = arms[cid]["K"] >= plan["K"]
        okS = seeds == sorted(plan["seeds"])
        okC = all(ch["git_commit"] not in (None, "n/a") for ch in arms[cid]["chunks"])
        c1_ok = c1_ok and okK and okS and okC
        c1_notes.append(f"{cid}: K {arms[cid]['K']}/{plan['K']}, seeds {seeds}")
        arms[cid]["hamming"] = hamming_block(a)
    data["arms"] = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in arms.items()}
    G.add("C1 A0 timing recorded; planned K per arm reached; every chunk file with seed and git commit",
          "; ".join(c1_notes), "B0_ref25_k1 720 (seeds 101-103), B1_ref57_k1 240 (201), B0_ref25_k4 240 (301), "
          "xx control arm 120 (401)", c1_ok)

    # ---------------------------------------------------------------- C2: the A6 hit prediction + A4
    observed = {}
    for cid in ("B0_ref25_k1", "B1_ref57_k1"):
        rec = load_json(os.path.join(DRYRUN, "counts", cid + ".json"))
        observed[cid] = {"hits": ref_hits(rec, mans[cid]["reference_int"]), "shots": int(rec["shots"])}
    n_obs = sum(v["hits"] for v in observed.values())
    c2 = {"observed_per_circuit": observed, "observed_total": n_obs,
          "observed_total_predict_json": predict["dryrun"]["reference_hits_total"]}
    if all(c in arms for c in ("B0_ref25_k1", "B1_ref57_k1")):
        mu, var = 0.0, 0.0
        per = {}
        for cid in ("B0_ref25_k1", "B1_ref57_k1"):
            s = arms[cid]
            N = observed[cid]["shots"]
            m = N * s["hit_fraction_per_shot"]["prompt_formula_f0p_pref_plus_1mf0_h"]
            se = N * (1 - s["f0_prime"]) * s["_h_se"]
            per[cid] = {"shots": N, "predicted": m, "se": se, "observed": observed[cid]["hits"],
                        "fault_free_only": N * s["f0_prime"] * s["p_ref"],
                        "predicted_exact_decomposition": N * s["hit_fraction_per_shot"]["exact_g0_pideal_post_plus_1mg0_h"]}
            mu += m
            var += se ** 2
        se_mu = math.sqrt(var)
        P = two_sided_poisson_p(n_obs, mu)
        # information: Poisson P with mu's trajectory uncertainty integrated (normal prior on mu, truncated > 0)
        grid = np.linspace(max(1e-6, mu - 5 * se_mu), mu + 5 * se_mu, 401)
        wts = np.exp(-0.5 * ((grid - mu) / se_mu) ** 2)
        wts /= wts.sum()
        from scipy.stats import poisson
        cdf = float(np.sum(wts * poisson.cdf(n_obs, grid)))
        sf = float(np.sum(wts * poisson.sf(n_obs - 1, grid)))
        sd_tot = math.sqrt(mu + se_mu ** 2)
        low_side = (mu < n_obs) and ((n_obs - mu) / sd_tot > LOW_SIDE_SIGMAS)
        c2.update({"per_circuit": per, "predicted_total": mu, "predicted_total_se": se_mu,
                   "fault_free_only_total": sum(v["fault_free_only"] for v in per.values()),
                   "two_sided_poisson_P": P, "two_sided_P_with_mu_uncertainty": float(min(1.0, 2 * min(cdf, sf))),
                   "sd_total_poisson_plus_trajectory": sd_tot, "z_observed_minus_predicted": (n_obs - mu) / sd_tot,
                   "prediction_below_observed_by_more_than_3_sd": bool(low_side),
                   "pooled_f_hit_traj": (sum(per[c]["shots"] * arms[c]["stats"]["f_hit"]["value"] for c in per)
                                         / sum(per[c]["shots"] for c in per)),
                   "A6_pooled_reference_string_f": predict["dryrun"]["pooled_f_estimate"],
                   "A6_pooled_reference_string_f_95": predict["dryrun"]["pooled_f_95"]})
    # A4 control
    a4 = {"present": False}
    cpath = os.path.join(cf.OUT, "control_xx", "counts", "B0_ref25_k1.json")
    xx = arms.get("B0_ref25_k1__xx")
    if os.path.exists(cpath) and xx is not None:
        rec = load_json(cpath)
        hits = ref_hits(rec, mans["B0_ref25_k1"]["reference_int"])
        N = int(rec["shots"])
        mu_xx = N * xx["hit_fraction_per_shot"]["prompt_formula_f0p_pref_plus_1mf0_h"]
        band = poisson_band(mu_xx)
        sess = load_json(os.path.join(cf.OUT, "control_xx", "session.json"))
        a4 = {"present": True, "shots": N, "seed": int(sess["jobs"][0]["aer_seed"]), "hits": hits,
              "h_ref_xx": xx["stats"]["h_ref"], "predicted": mu_xx,
              "predicted_se": N * (1 - xx["f0_prime"]) * xx["_h_se"],
              "fault_free_only": N * xx["f0_prime"] * xx["p_ref"], "poisson_95_band": band,
              "two_sided_poisson_P": two_sided_poisson_p(hits, mu_xx),
              "pass": band[0] <= hits <= band[1], "above_band": hits > band[1],
              "A6_like_count_for_280_shots": n_obs, "session": os.path.relpath(cpath, ROOT),
              "sampling_wall_s": sess.get("sampling_wall_s"), "noise_model": sess["noise_model"]}
    c2["A4_control"] = a4
    data["C2"] = c2
    c2_ok = bool(c2.get("two_sided_poisson_P", 0.0) >= P_MIN and a4.get("pass", False))
    G.add("C2 trajectory prediction of the A6 reference hits vs observed (two-sided Poisson) and the A4 control",
          (f"predicted {fmt(c2.get('predicted_total'))} +- {fmt(c2.get('predicted_total_se'))} vs observed {n_obs}, "
           f"P = {fmt(c2.get('two_sided_poisson_P'))}; A4: {a4.get('hits')} hits vs predicted "
           f"{fmt(a4.get('predicted'))}, band {a4.get('poisson_95_band')}") if "predicted_total" in c2 else "not computed",
          "P >= 0.05 and the A4 hits inside the Poisson 95 % band of the xx-arm prediction", c2_ok)

    # ---------------------------------------------------------------- C3: Z-only stratum vs phase-only check
    c3 = {"phase_check": {k: phase[k] for k in ("circuit", "shots", "seed", "reference_hits", "no_error_probability",
                                                "p_reference", "channel")}}
    c3_ok = False
    s = arms.get("B0_ref25_k1")
    if s is not None and s["z_stratum"].get("h_Z") is not None:
        g0p, pr = float(phase["no_error_probability"]), float(phase["p_reference"])
        hz = s["z_stratum"]["h_Z"]
        mu_z = PHASE_SHOTS * (g0p * pr + (1 - g0p) * hz)
        band = poisson_band(mu_z)
        k = int(phase["reference_hits"])
        c3.update({"h_Z": hz, "h_Z_se": s["z_stratum"].get("h_Z_se"), "n_z_only": s["z_stratum"]["n_z_only"],
                   "predicted": mu_z, "poisson_95_band": band, "observed": k,
                   "two_sided_poisson_P": two_sided_poisson_p(k, mu_z)})
        rw = s["z_stratum"].get("phase_channel_reweighted")
        if rw:
            mu_rw = PHASE_SHOTS * (g0p * pr + (1 - g0p) * rw["h_faulty_self_normalised"])
            c3["information_reweighted_to_phase_channel"] = {
                "h_faulty": rw["h_faulty_self_normalised"], "predicted": mu_rw, "poisson_95_band": poisson_band(mu_rw),
                "two_sided_poisson_P": two_sided_poisson_p(k, mu_rw), "mean_weight": rw["mean_weight"], "note": rw["note"]}
        c3_ok = band[0] <= k <= band[1]
    data["C3"] = c3
    G.add("C3 Z-only stratum reproduces the phase-only check (11 hits in 40)",
          (f"predicted {fmt(c3.get('predicted'))}, band {c3.get('poisson_95_band')}, observed {c3.get('observed')}"
           if "predicted" in c3 else "not computed"),
          "observed inside the Poisson 95 % band of 40 [g0 p_ref + (1 - g0) h_Z]", c3_ok)

    # ---------------------------------------------------------------- C4: reported with intervals
    keys = ["rho_ref", "rho_T", "benign_fraction", "min_feff_over_f0_S99", "min_feff_over_f0_S999",
            "n_S99_feff_below_margin_fT"]
    c4_ok = all(cid in arms and all(k in arms[cid]["stats"] for k in keys) for cid in ARMS)
    G.add("C4 rho_ref, rho_T, b, min f_eff/f0' (S99, S999), #S99 below 0.7 f_T reported with intervals, 3 arms",
          "; ".join(f"{cid}: rho_ref {fi(arms[cid]['stats']['rho_ref'])}, rho_T {fi(arms[cid]['stats']['rho_T'])}"
                    for cid in ARMS if cid in arms), "all six quantities with 95 % intervals for all three arms", c4_ok)

    # ---------------------------------------------------------------- C5: A6-path audit
    audit = a6_path_audit(mans)
    data["C5_A6_path_audit"] = audit
    G.add("C5 A6-path audit: 2158 rzz, one noisy 1q rotation per PhasedX, noise on rzz, rx, ry, measure",
          "; ".join(f"{c}: rzz {r['n_rzz']}, rx+ry {r['n_noisy_1q_rx_ry']} (PhasedX {r['manifest_n_phasedx']})"
                    for c, r in audit["circuits"].items()) + f"; noise_instructions {audit['noise_model']['noise_instructions']}",
          "rzz = 2158 and rx+ry = the manifest PhasedX count (prompt's typed 3053 matches no frozen circuit: see "
          "data.C5_A6_path_audit.prompt_c5_literal)", audit["ok"])

    # ---------------------------------------------------------------- STOP flags + verdict
    rho_T_max = max((arms[c]["stats"]["rho_T"]["value"] for c in ARMS if c in arms), default=None)
    stops = {"C2_low_side": bool(c2.get("prediction_below_observed_by_more_than_3_sd", False)),
             "A4_reproduces_A6_like_count": bool(a4.get("above_band", False)),
             "rho_T_above_1p5": bool(rho_T_max is not None and rho_T_max > RHO_T_STOP),
             "rho_T_max_over_arms": rho_T_max}
    data["stop_flags"] = stops
    if stops["C2_low_side"] or stops["A4_reproduces_A6_like_count"]:
        verdict = "bug candidate (Aer path applies fewer error events than modelled, or trajectory model too low)"
    elif c2_ok:
        verdict = ("physics: near-clean term -- the reference-hit excess is reproduced by the trajectory "
                   "decomposition and the bit-flip-only control gives the fault-free count")
    elif c2.get("predicted_total", 0) > n_obs:
        verdict = "model question: the trajectory prediction lies above the observed hits (not a bug candidate)"
    else:
        verdict = "undecided"
    data["physics_verdict"] = verdict

    # ---------------------------------------------------------------- C6
    checks = {"skipped": True, "ok": False} if args.skip_checks else run_checks()
    data["C6_checks"] = checks
    G.add("C6 pytest (coding + venv), check_package, pins unchanged",
          ("skipped" if checks.get("skipped") else
           f"coding: {checks['pytest_coding']['summary']}; venv: {checks['pytest_venv']['summary']}; "
           f"check_package rc {checks['check_package']['returncode']}; pins_ok {checks['pins_ok']}"),
          "all pass, pins = " + json.dumps(PINS_EXPECTED), checks.get("ok", False))

    data["A5_2x2_arm"] = load_json(os.path.join(cf.OUT, "A5_2x2", "result.json")) if os.path.exists(
        os.path.join(cf.OUT, "A5_2x2", "result.json")) else {"status": "not run"}
    G.data = data
    G.runtime_s = time.time() - t_start
    path = G.save()
    write_report("CF_traj.md", render(G, data, arms))
    print(f"{GATE}: {'PASS' if G.passed else 'FAIL'} -> {os.path.relpath(path, ROOT)}")
    for c in G.criteria:
        print(f"  {'PASS' if c.passed else 'FAIL'}  {c.name}: {c.value}")
    print("stop flags:", stops)
    print("verdict:", verdict)
    return 0 if G.passed else 1


def render(G, data, arms):
    L = [f"# Gate {GATE}: {TITLE}", "",
         f"Status: **{'PASS' if G.passed else 'FAIL'}**.  Prompt: `prompts/28_2x3_shot_rule_and_clean_fraction_estimator.md` "
         "Part A.  Generated by `scripts/gate_CF_traj.py` from `validation/CF_traj.json`; every number below is read "
         "from that file.  0 QPU s, 0 HQC.", "",
         f"What PASS means: {WHAT_PASS_MEANS}", "",
         f"Physics verdict: **{data['physics_verdict']}**.", "",
         "## Criteria", "", G.criteria_table(), "",
         "## Definitions (the planner's labels, prompts/28; not manual terms)", "", "```", data["definitions"], "```", "",
         "## Per-arm results (95 % bootstrap intervals over trajectories)", ""]
    rows = []
    for cid, s in arms.items():
        st = s["stats"]
        rows.append([cid, s["channel"], s["K"], fmt(s["f0_prime"], 6), fi(st["h_ref"]), fi(st["f_hit"]), fi(st["f_T"]),
                     fi(st["rho_ref"]), fi(st["rho_T"]), fi(st["benign_fraction"])])
    L += [md_table(["arm", "channel", "K", "f0'", "h_ref", "f_hit^traj", "f_T^traj", "rho_ref", "rho_T", "b"], rows), ""]
    rows = []
    for cid, s in arms.items():
        st = s["stats"]
        rows.append([cid, s["tail_class"]["size"], fmt(s["tail_class"]["p_Tc"]), fi(st["min_feff_over_f0_S99"]),
                     fi(st["median_feff_over_f0_S99"]), fi(st["min_feff_over_f0_S999"]), fi(st["median_feff_over_f0_S999"]),
                     fi(st["min_feff_over_fT_S99"]), fi(st["n_S99_feff_below_margin_fT"])])
    L += ["Per-state effective rates ($f_{\\rm eff}(s)/f_0'$; states with tiny $p_c(s)$ inflate the median/max, the "
          "per-state table is in the JSON, `data.arms.<arm>.per_state_S999`):", "",
          md_table(["arm", "|T_c|", "p_Tc", "min S99", "median S99", "min S999", "median S999",
                    "min f_eff/f_T on S99", "#S99 with f_eff < 0.7 f_T"], rows), ""]
    c2 = data["C2"]
    if "predicted_total" in c2:
        L += ["## C2: the A6 reference hits", "",
              md_table(["circuit", "shots", "observed", "fault-free only", "trajectory prediction", "s.e."],
                       [[c, v["shots"], v["observed"], fmt(v["fault_free_only"]), fmt(v["predicted"]), fmt(v["se"])]
                        for c, v in c2["per_circuit"].items()]
                       + [["total", sum(v["shots"] for v in c2["per_circuit"].values()), c2["observed_total"],
                           fmt(c2["fault_free_only_total"]), fmt(c2["predicted_total"]), fmt(c2["predicted_total_se"])]]),
              "", f"Two-sided Poisson P = {fmt(c2['two_sided_poisson_P'])} (with the trajectory uncertainty of the "
              f"mean integrated: {fmt(c2['two_sided_P_with_mu_uncertainty'])}); (observed - predicted)/sd = "
              f"{fmt(c2['z_observed_minus_predicted'])}.  Pooled trajectory $f_{{\\rm hit}}$ = {fmt(c2['pooled_f_hit_traj'])} "
              f"against the A6 reference-string estimate {fmt(c2['A6_pooled_reference_string_f'])} "
              f"(95 % {[fmt(x) for x in c2['A6_pooled_reference_string_f_95']]}).", ""]
    a4 = c2["A4_control"]
    if a4.get("present"):
        L += ["## A4: bit-flip-only counting control (Aer sampler path)", "",
              f"{a4['shots']} shots, seed {a4['seed']}: **{a4['hits']}** reference hits; prediction from the xx "
              f"trajectory arm {fmt(a4['predicted'])} +- {fmt(a4['predicted_se'])} (fault-free only "
              f"{fmt(a4['fault_free_only'])}), Poisson 95 % band {a4['poisson_95_band']}, two-sided P "
              f"{fmt(a4['two_sided_poisson_P'])}; the A6 depolarizing run gave {a4['A6_like_count_for_280_shots']} "
              f"in the same number of shots.", ""]
    c3 = data["C3"]
    if "predicted" in c3:
        L += ["## C3: Z-only stratum vs the phase-only check", "",
              f"{c3['n_z_only']} Z-only faulty trajectories of B0_ref25_k1, mean pre-readout $p_\\tau$(ref) = "
              f"{fmt(c3['h_Z'])} (s.e. {fmt(c3['h_Z_se'])}); prediction 40 [g0 p_ref + (1 - g0) h_Z] = "
              f"{fmt(c3['predicted'])}, band {c3['poisson_95_band']}, observed {c3['observed']}."]
        rw = c3.get("information_reweighted_to_phase_channel")
        if rw:
            L += ["", f"Information: reweighted to the phase channel's event-count distribution, h = {fmt(rw['h_faulty'])}, "
                  f"prediction {fmt(rw['predicted'])}, band {rw['poisson_95_band']} (mean weight {fmt(rw['mean_weight'])}, "
                  "expected 1).  " + rw["note"]]
        L += [""]
    au = data["C5_A6_path_audit"]
    L += ["## C5: A6-path audit", "", au["sampler"], "",
          md_table(["circuit", "rzz", "rx+ry", "manifest ZZ", "manifest PhasedX", "adjacent same-pair rzz"],
                   [[c, r["n_rzz"], r["n_noisy_1q_rx_ry"], r["manifest_n_zz"], r["manifest_n_phasedx"],
                     r["adjacent_same_pair_rzz_in_executed_circuit"]] for c, r in au["circuits"].items()]),
          "", f"Noise instructions {au['noise_model']['noise_instructions']}, basis {au['noise_model']['basis_gates']}.  "
          f"Prompt literal: {au['prompt_c5_literal']['note']}.", ""]
    L += ["## Where the faulty weight goes (Hamming distance from the reference, 20-bit strings)", ""]
    hdr = ["arm"] + [f"d={d}" for d in range(0, 7)] + ["d>=7"]
    rows = []
    for cid, s in arms.items():
        w = s["hamming"]["faulty_mean_weight_by_distance"]
        rows.append([cid] + [fmt(x, 3) for x in w[:7]] + [fmt(sum(w[7:]), 3)])
    L += [md_table(hdr, rows), ""]
    L += ["## STOP flags", "", "```", json.dumps(data["stop_flags"], indent=1), "```", "",
          "## A5 (optional 2x2 arm)", "", "```", json.dumps(data["A5_2x2_arm"], indent=1)[:3000], "```", "",
          "## Timing (A0)", "", "```", json.dumps(data["A0_timing"], indent=1), "```", "", env_block(), ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
