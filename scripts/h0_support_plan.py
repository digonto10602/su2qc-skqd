#!/usr/bin/env python3
"""
The H0 shot plan (rule D3' of prompts/16) — sized so that the SUPPORT SATURATES.

`reports/H0P_ibm_fez_escalation_20260921.md` showed that the frozen plan (267 / 130 / 92
shots per r = 1 / 2 / 3 circuit) saturates neither 2x2 sector from clean shots: the
probability that every sector state is observed at least once is 0.004 (B=0) and 0.076
(B=1) on the live calibration of 2026-09-21.  The premise of criterion 3 of the
preregistration ("the Ritz energies of the *saturated* sectors reproduce E_0 to 1e-6")
was therefore a coin flip, and the criterion measured the coin, not the device.

**Rule D3'.**  r = 2 and r = 3 keep 130 / 92 shots.  Every r = 1 circuit keeps the floor
267.  The k = 4 circuits of each sector — the coarse step at the largest angle 4*dt,
which spreads the reference furthest — get N4(sector) shots, the smallest multiple of
`--round-to` such that every sector state s satisfies

    lambda_s = sum_{c in r=1} N_c * y_c * p_c(s) >= lambda*,
    y_c = READOUT_FACTOR * margin * f_c,   lambda* = poisson_lambda_star(k, conf),

with f_c the clean-shot fraction of the session day's calibration for circuit c (the
`gate_S2D.analyse_on_backend` value the prediction itself uses), p_c(s) the IDEAL
probability of sector state s in the frozen circuit c, and margin = 0.7 = the lower edge
of criterion 2 of the preregistration (measured f within 30 % of the prediction).  A
device that passes criterion 2 therefore saturates both sectors with the manual's
three-hit / 95 % guarantee per state.  Garbage acceptances — the manual's (1 - f) a term
— are computed and reported but never counted towards the guarantee (conservative).

Nothing here changes a criterion, a tolerance, a convention or a frozen circuit: the
QPY files of `data/hardware/H0_prep` are read only, and the constants READOUT_FACTOR
(0.82), the floor 267, the r = 2 / 3 shots and the 4000 calibration shots are inputs.

The ideal probabilities p_c(s) are taken from the FROZEN QPY (`skqd.hardware.
logical_statevector` -> `skqd.reference_sim.CodewordEmbedding.project`), i.e. from the
circuit that will actually be submitted, and cross-checked against the exact group
evolution `skqd.krylov.apply_groups` at the manifest's angle k*dt applied r times;
`amplitude_crosscheck_max_dp` records the largest disagreement.

Usage:
  python scripts/h0_support_plan.py --backend FakeFez \\
      --out data/H0_shot_plan_FakeFez.json --report reports/H0_support_plan_FakeFez.md
  python scripts/h0_support_plan.py \\
      --calibration data/hardware/H0_ibm_fez/calibration_20260921T2053Z.json \\
      --out /tmp/plan_live.json --report /tmp/plan_live.md
Runtime: about 1 minute (84 QPY statevectors).  No QPU time is used; `--backend <live>`
only reads `backend.target`, which is a free metadata query.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.hardware import logical_statevector  # noqa: E402
from skqd.krylov import apply_groups, basis_vector, references, term_groups  # noqa: E402
from skqd.reference_sim import CodewordEmbedding  # noqa: E402
from skqd.report import env_block, md_table  # noqa: E402
from skqd.skqd import READOUT_FACTOR, poisson_lambda_star  # noqa: E402

from gate_H0P import load_circuit, load_index, load_manifests, random_acceptance  # noqa: E402
from h0_backends import is_fake, last_update_date, resolve_backend  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RULE = ("D3' (prompts/16): r=2 and r=3 keep their shots, every r=1 circuit keeps the floor, "
        "and the k=4 circuits of each sector get N4 = the smallest multiple of `round_to` such "
        "that every sector state has expected clean count >= lambda* from the r=1 circuits alone "
        "at the clean yield readout_factor * margin * f_c")
AMPLITUDE_TOL = 1e-9
F_CROSSCHECK_TOL = 1e-9


# --------------------------------------------------------------- the D3' arithmetic
def clean_rate(p_by_circuit, f_by_circuit, readout_factor=READOUT_FACTOR, margin=1.0):
    """{circuit id: expected clean counts per shot, per sector state} = y_c * p_c(s)."""
    return {c: readout_factor * margin * float(f_by_circuit[c]) * np.asarray(p_by_circuit[c], float)
            for c in p_by_circuit}


def lambda_of_plan(p_by_circuit, f_by_circuit, shots_by_circuit,
                   readout_factor=READOUT_FACTOR, margin=1.0, only=None):
    """Expected clean count of every sector state under a per-circuit shot plan."""
    ids = list(only) if only is not None else list(p_by_circuit)
    if not ids:
        raise ValueError("no circuits selected")
    rate = clean_rate({c: p_by_circuit[c] for c in ids}, f_by_circuit, readout_factor, margin)
    lam = np.zeros_like(rate[ids[0]])
    for c in ids:
        lam = lam + float(shots_by_circuit[c]) * rate[c]
    return lam


def garbage_of_plan(f_by_circuit, shots_by_circuit, acceptance, dimension, only=None):
    """Expected garbage acceptances per sector state: sum_c N_c (1 - f_c) a / dim."""
    ids = list(only) if only is not None else list(f_by_circuit)
    return float(sum(float(shots_by_circuit[c]) * (1.0 - float(f_by_circuit[c]))
                     for c in ids) * acceptance / dimension)


def n4_of_sector(p_by_circuit, f_by_circuit, r1_ids, k4_ids, floor, lambda_star,
                 margin=0.7, readout_factor=READOUT_FACTOR, round_to=100):
    """N4 of rule D3': the smallest multiple of `round_to` (>= floor) such that the r=1
    circuits alone give every sector state an expected clean count >= lambda*."""
    k4 = [c for c in r1_ids if c in set(k4_ids)]
    base_ids = [c for c in r1_ids if c not in set(k4_ids)]
    if not k4:
        raise ValueError("no k=4 circuit in the r=1 set: rule D3' has nothing to scale")
    rate = clean_rate({c: p_by_circuit[c] for c in r1_ids}, f_by_circuit, readout_factor, margin)
    base = sum((float(floor) * rate[c] for c in base_ids),
               np.zeros_like(rate[k4[0]]))
    denom = sum((rate[c] for c in k4), np.zeros_like(rate[k4[0]]))
    short = lambda_star - base
    if np.any((denom <= 0) & (short > 0)):
        bad = np.where((denom <= 0) & (short > 0))[0].tolist()
        raise ValueError(f"sector states {bad} have zero ideal probability in every k=4 circuit: "
                         f"rule D3' cannot reach them (this is an escalation, not a default)")
    need = np.where(denom > 0, short / np.where(denom > 0, denom, 1.0), 0.0)
    n4 = int(np.ceil(max(float(np.max(need)), 0.0) / round_to) * round_to)
    return max(n4, int(floor))


def p_seen(lam):
    """P(a state with expected count lambda is observed at least once), Poisson."""
    return 1.0 - np.exp(-np.asarray(lam, float))


def p_all_seen(lam):
    return float(np.prod(p_seen(lam)))


# --------------------------------------------------------------- f from a calibration file
def load_calibration(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(p) as fh:
        cal = json.load(fh)
    cz, meas = {}, {}
    for rec in cal["edges"].values():
        e = rec["cz_error"]
        key = tuple(int(x) for x in rec["target_key"])
        pairs = [tuple(int(x) for x in q) for q in rec.get("directed_pairs_of_the_frozen_set", [])]
        for k in {key, key[::-1], *pairs, *[q[::-1] for q in pairs]}:
            cz[k] = e
    for q, rec in cal["qubits"].items():
        meas[int(q)] = rec["measure_error"]
    return cal, cz, meas


def f_from_calibration(tq, cz_error, measure_error):
    """The f of `gate_S2D.analyse_on_backend`, evaluated on a calibration RECORD.

    Identical formula: f = prod over the circuit's cz instructions of (1 - eps_edge)
    times prod over its measure instructions of (1 - eps_readout).  A missing or None
    error is a hard stop, never a default (prompts/15 A1)."""
    log_f, n_cz, n_meas = 0.0, 0, 0
    for inst in tq.data:
        nm = inst.operation.name
        qs = tuple(tq.find_bit(q).index for q in inst.qubits)
        if nm == "cz":
            e = cz_error.get(qs, cz_error.get(qs[::-1]))
            if e is None:
                raise SystemExit(f"the calibration record has no cz error for the edge {qs}: "
                                 f"the clean-shot fraction f cannot be computed offline")
            log_f += np.log1p(-float(e))
            n_cz += 1
        elif nm == "measure":
            e = measure_error.get(qs[0])
            if e is None:
                raise SystemExit(f"the calibration record has no measure error for qubit {qs[0]}")
            log_f += np.log1p(-float(e))
            n_meas += 1
    return float(np.exp(log_f)), n_cz, n_meas


# --------------------------------------------------------------- ideal probabilities
def ideal_probabilities(prep, mans, model, g2, crosscheck=True):
    """({circuit id: p over its sector's states}, max |Delta p| of the cross-check).

    The primary source is the FROZEN QPY: the noiseless statevector of the transpiled
    circuit, permuted back to logical order with its own final layout, projected onto the
    codeword subspace.  The cross-check is the exact group evolution of `skqd.krylov`
    at the manifest's angle k*dt, applied `repetitions` times."""
    emb = CodewordEmbedding(model)
    idx = {sec: model.reference(g2, twoB).indices for sec, twoB in (("B=0", 0), ("B=1", 2))}
    P = {}
    for m in mans:
        qc = load_circuit(prep, m)
        psi = logical_statevector(qc, emb.n)
        P[m["id"]] = (np.abs(emb.project(psi)) ** 2)[idx[m["sector"]]]
    max_dp = None
    if crosscheck:
        G = term_groups(model.terms, g2, 3 * g2 / 16)
        max_dp = 0.0
        cache = {}
        for m in mans:
            key = (m["reference"], m["k"], m["repetitions"], round(float(m["dt"]), 15))
            if key not in cache:
                psi = basis_vector(model.basis.dim, int(m["reference"]))
                for _ in range(int(m["repetitions"])):
                    psi = apply_groups(G, psi, int(m["k"]) * float(m["dt"]))
                cache[key] = (np.abs(psi) ** 2)[idx[m["sector"]]]
            max_dp = max(max_dp, float(np.max(np.abs(cache[key] - P[m["id"]]))))
    return P, max_dp


# --------------------------------------------------------------- the plan
def build_plan(args, prep, mans, model, g2, f_by_circuit, f_source, calibration_block,
               backend=None, backend_name=None):
    lambda_star = poisson_lambda_star(args.k, args.conf)
    reps_shots = {int(x.split(":")[0]): int(x.split(":")[1]) for x in args.reps_shots}
    P, max_dp = ideal_probabilities(prep, mans, model, g2, crosscheck=not args.no_crosscheck)
    if max_dp is not None and max_dp >= AMPLITUDE_TOL:
        raise SystemExit(
            f"the ideal probabilities of the frozen QPY and of skqd.krylov.apply_groups differ by "
            f"{max_dp:.3e} >= {AMPLITUDE_TOL:g}: the frozen set is not the circuit set gate H0P "
            f"validated (prompts/16 escalation A'1/A'2).  Nothing was written.")

    sectors, shots_by_circuit = {}, {}
    frozen_shots = {m["id"]: int(args.floor if m["repetitions"] == 1
                                 else reps_shots[m["repetitions"]]) for m in mans}
    for sec, twoB in (("B=0", 0), ("B=1", 2)):
        sm = [m for m in mans if m["sector"] == sec]
        ids = [m["id"] for m in sm]
        r1 = [m["id"] for m in sm if m["repetitions"] == 1]
        k4 = [m["id"] for m in sm if m["repetitions"] == 1 and m["k"] == args.kmax]
        ref = model.reference(g2, twoB)
        dim = int(len(ref.indices))
        a = random_acceptance(Codec(model.basis), twoB)["fraction"]
        n4 = n4_of_sector({c: P[c] for c in r1}, f_by_circuit, r1, k4, args.floor, lambda_star,
                          margin=args.margin, readout_factor=READOUT_FACTOR, round_to=args.round_to)
        plan_shots = {}
        for m in sm:
            if m["repetitions"] == 1:
                plan_shots[m["id"]] = n4 if m["id"] in k4 else int(args.floor)
            else:
                plan_shots[m["id"]] = int(reps_shots[m["repetitions"]])
        shots_by_circuit.update(plan_shots)

        lam_margin = lambda_of_plan(P, f_by_circuit, plan_shots, margin=args.margin, only=r1)
        lam_f_r1 = lambda_of_plan(P, f_by_circuit, plan_shots, margin=1.0, only=r1)
        lam_all_margin = lambda_of_plan(P, f_by_circuit, plan_shots, margin=args.margin, only=ids)
        lam_all_f = lambda_of_plan(P, f_by_circuit, plan_shots, margin=1.0, only=ids)
        lam_frozen = lambda_of_plan(P, f_by_circuit, frozen_shots, margin=1.0, only=ids)
        gar_frozen = garbage_of_plan(f_by_circuit, frozen_shots, a, dim, only=ids)
        gar_plan = garbage_of_plan(f_by_circuit, plan_shots, a, dim, only=ids)

        weight = np.abs(ref.ground) ** 2
        per_state = []
        for i in range(dim):
            best = max(ids, key=lambda c: P[c][i])
            best_r1 = max(r1, key=lambda c: P[c][i])
            j2, n, iota = model.basis.labels[int(ref.indices[i])]
            per_state.append({
                "sector_position": i, "basis_index": int(ref.indices[i]),
                "j2": list(map(int, j2)), "n": list(map(int, n)), "iota": list(map(int, iota)),
                "label": f"({','.join(str(int(x)) for x in j2)}); ({','.join(str(int(x)) for x in n)})",
                "ground_state_weight": float(weight[i]),
                "best_circuit": best, "best_p": float(P[best][i]),
                "best_r1_circuit": best_r1, "best_r1_p": float(P[best_r1][i]),
                "lambda_frozen_plan_clean": float(lam_frozen[i]),
                "lambda_r1_at_margin": float(lam_margin[i]),
                "lambda_r1_at_f": float(lam_f_r1[i]),
                "lambda_all_at_margin": float(lam_all_margin[i]),
                "lambda_all_at_f": float(lam_all_f[i]),
                "P_seen_r1_at_margin": float(p_seen(lam_margin[i])),
                "P_seen_frozen_plan_clean": float(p_seen(lam_frozen[i])),
                "P_seen_frozen_plan_with_garbage": float(p_seen(lam_frozen[i] + gar_frozen)),
            })
        sectors[sec] = {
            "twoB": twoB, "dimension": dim, "N4": int(n4),
            "k4_circuits": sorted(k4), "r1_circuits": sorted(r1), "circuits": len(sm),
            "floor": int(args.floor),
            "r1_shots_total": int(sum(plan_shots[c] for c in r1)),
            "coarse_shots_total": int(sum(plan_shots[c] for c in ids)),
            "garbage_acceptance": float(a),
            "garbage_hits_per_state_frozen_plan": gar_frozen,
            "garbage_hits_per_state_plan": gar_plan,
            "min_lambda_r1_at_margin": float(np.min(lam_margin)),
            "min_lambda_r1_at_f": float(np.min(lam_f_r1)),
            "min_lambda_frozen_plan_clean": float(np.min(lam_frozen)),
            "P_saturation_clean_at_margin": p_all_seen(lam_margin),
            "P_saturation_clean_at_f": p_all_seen(lam_f_r1),
            "P_saturation_all_circuits_at_margin": p_all_seen(lam_all_margin),
            "P_saturation_frozen_plan_clean": p_all_seen(lam_frozen),
            "P_saturation_frozen_plan_with_garbage": p_all_seen(lam_frozen + gar_frozen),
            "f_min": float(min(f_by_circuit[c] for c in ids)),
            "f_max": float(max(f_by_circuit[c] for c in ids)),
            "f_mean_r1": float(np.mean([f_by_circuit[c] for c in r1])),
            "per_state": per_state,
        }

    totals = {
        "coarse_shots": int(sum(shots_by_circuit.values())),
        "r1_shots": int(sum(v["r1_shots_total"] for v in sectors.values())),
        "frozen_plan_coarse_shots": int(sum(frozen_shots.values())),
        "calibration_shots_total": int(args.cal_shots * len(load_manifests(prep)[1])),
        "qpu_execution_s": None,
    }
    totals["total_shots"] = totals["coarse_shots"] + totals["calibration_shots_total"]
    qpu = None
    if backend is not None:
        from h0_qpu_time import estimate
        qpu = estimate(prep, backend, {}, args.cal_shots, shots_by_circuit=shots_by_circuit)
        totals["qpu_execution_s"] = float(qpu["total_execution_s"])

    plan = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "script": "scripts/h0_support_plan.py",
        "arguments": vars(args),
        "rule": RULE,
        "lambda_star": float(lambda_star),
        "lambda_star_source": f"skqd.skqd.poisson_lambda_star({args.k}, {args.conf})",
        "margin": float(args.margin),
        "margin_source": ("0.7 = the lower edge of criterion 2 of the preregistration "
                          "(measured f within 30 % of the prediction)"),
        "readout_factor": float(READOUT_FACTOR),
        "floor": int(args.floor),
        "round_to": int(args.round_to),
        "reps_shots": {str(r): int(v) for r, v in sorted(reps_shots.items())},
        "kmax": int(args.kmax),
        "prep": os.path.relpath(prep, ROOT),
        "prep_created": load_index(prep)["created"],
        "backend": backend_name,
        "calibration": calibration_block,
        "f_source": f_source,
        "f_by_circuit": {c: float(v) for c, v in sorted(f_by_circuit.items())},
        "amplitude_crosscheck_max_dp": max_dp,
        "amplitude_crosscheck": ("frozen QPY (skqd.hardware.logical_statevector -> "
                                 "CodewordEmbedding.project) versus skqd.krylov.apply_groups at the "
                                 "manifest's k*dt applied `repetitions` times"),
        "sectors": sectors,
        "shots_by_circuit": {c: int(v) for c, v in sorted(shots_by_circuit.items())},
        "frozen_plan_shots_by_circuit": {c: int(v) for c, v in sorted(frozen_shots.items())},
        "calibration_shots": int(args.cal_shots),
        "totals": totals,
    }
    if qpu is not None:
        plan["qpu_time_estimate"] = {"groups": qpu["groups"], "rep_delay_s": qpu["rep_delay_s"],
                                     "total_shots": qpu["total_shots"],
                                     "total_execution_s": qpu["total_execution_s"],
                                     "last_update_date": qpu["last_update_date"]}
    return plan


# --------------------------------------------------------------- report
def report_text(plan):
    c = plan["calibration"]
    lines = []
    for sec in ("B=0", "B=1"):
        v = plan["sectors"][sec]
        weak = sorted(v["per_state"], key=lambda s: s["lambda_frozen_plan_clean"])[:10]
        rows = [[s["basis_index"], s["label"], f"{s['ground_state_weight']:.3e}",
                 s["best_circuit"], f"{s['best_p']:.3e}", s["best_r1_circuit"],
                 f"{s['best_r1_p']:.3e}", f"{s['lambda_frozen_plan_clean']:.2f}",
                 f"{s['lambda_r1_at_margin']:.2f}", f"{s['lambda_r1_at_f']:.2f}",
                 f"{s['P_seen_r1_at_margin']:.5f}"] for s in weak]
        lines.append(f"""### {sec} ({v['dimension']} states, N4 = {v['N4']})

The ten states with the smallest expected clean count under the FROZEN plan
(267 / {plan['reps_shots'].get('2')} / {plan['reps_shots'].get('3')} shots, all circuits, at f):

{md_table(["basis index", "label (j2; n)", "ground-state weight", "best circuit", "p",
           "best r=1 circuit", "p", "lambda frozen", f"lambda D3' at {plan['margin']} f",
           "lambda D3' at f", "P(seen) at margin"], rows)}

`lambda D3'` is the r = 1 circuits alone with the plan of this file.  N4 = {v['N4']} shots on the
{len(v['k4_circuits'])} k = 4 circuit(s) {', '.join(f'`{x}`' for x in v['k4_circuits'])}; the other
{len(v['r1_circuits']) - len(v['k4_circuits'])} r = 1 circuits keep the floor {v['floor']}, so the sector costs
{v['r1_shots_total']} r = 1 shots ({v['coarse_shots_total']} coarse shots in all).
min lambda_s at {plan['margin']} f = **{v['min_lambda_r1_at_margin']:.4f}** (>= lambda* = {plan['lambda_star']:.4f}),
at f = {v['min_lambda_r1_at_f']:.4f}.  P(all {v['dimension']} states seen from clean shots):
**{v['P_saturation_clean_at_margin']:.5f}** at {plan['margin']} f, {v['P_saturation_clean_at_f']:.5f} at f —
against {v['P_saturation_frozen_plan_clean']:.4f} under the frozen plan (clean) and
{v['P_saturation_frozen_plan_with_garbage']:.4f} with its garbage term
({v['garbage_hits_per_state_frozen_plan']:.2f} garbage hits per state, a = {v['garbage_acceptance']:.5f}).
""")
    qpu = plan.get("qpu_time_estimate")
    qrows = ([[g["group"], g["circuits"], g["shots_per_circuit"], g["total_shots"],
               f"{g['execution_s']:.1f} s"] for g in qpu["groups"]] if qpu else [])
    qblock = (f"""## 3. QPU execution estimate ({plan['backend']})

{md_table(["group", "circuits", "shots/circuit", "total shots", "execution"], qrows)}

Total **{qpu['total_execution_s']:.1f} s** over {qpu['total_shots']} shots (rep delay
{qpu['rep_delay_s'] * 1e6:.0f} us; `scripts/h0_qpu_time.py`).  The D6 cap is 120 s.
""" if qpu else """## 3. QPU execution estimate

Not computed: this plan was built from a calibration FILE (`--calibration`), so no target's
instruction durations were available.  Run `scripts/h0_qpu_time.py --backend <name> --shots-plan
<this file>` on the session day.
""")
    return f"""# H0 shot plan (rule D3') — {plan['backend'] or plan['calibration']['path']}

**Generated by `scripts/h0_support_plan.py`; no number below is typed by hand.**
{env_block()}

## 1. The rule

{plan['rule']}

lambda* = `{plan['lambda_star_source']}` = {plan['lambda_star']:.6f} (the manual's "seen at least
{plan['arguments']['k']} times with {100 * plan['arguments']['conf']:.0f} %", eq. 5).  margin = {plan['margin']}
({plan['margin_source']}).  readout factor {plan['readout_factor']}, floor {plan['floor']} shots,
N4 rounded up to a multiple of {plan['round_to']}, r = 2 / 3 unchanged at
{plan['reps_shots'].get('2')} / {plan['reps_shots'].get('3')} shots, {plan['calibration_shots']} calibration shots.

Clean-shot fraction f: {plan['f_source']}.  Calibration `{c['path']}`
({c.get('backend')}, `last_update_date` {c.get('last_update_date')}, stamp {c.get('stamp')}).
Ideal probabilities: {plan['amplitude_crosscheck']}; largest disagreement
**{plan['amplitude_crosscheck_max_dp']:.2e}** (tolerance {AMPLITUDE_TOL:g}).

## 2. The two sectors

{chr(10).join(lines)}
{qblock}
## 4. Totals

{plan['totals']['r1_shots']} r = 1 shots, {plan['totals']['coarse_shots']} coarse shots
(the frozen plan was {plan['totals']['frozen_plan_coarse_shots']}, a factor
{plan['totals']['coarse_shots'] / plan['totals']['frozen_plan_coarse_shots']:.2f}), plus
{plan['totals']['calibration_shots_total']} readout-calibration shots =
{plan['totals']['total_shots']} shots in all.

## Scope

This file sizes the shots so that the SATURATION criterion 3 presupposes is a prediction.  It changes
no criterion, no tolerance, no convention and no frozen circuit; `data/hardware/H0_prep` is read only.
"""


# --------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--backend", default=None, help="FakeFez / FakeTorino or a live IBM backend: "
                                                    "f per circuit from gate_S2D.analyse_on_backend")
    ap.add_argument("--calibration", default=None,
                    help="calibration_<stamp>.json: f recomputed offline with the same formula")
    ap.add_argument("--margin", type=float, default=0.7)
    ap.add_argument("--floor", type=int, default=267)
    ap.add_argument("--reps-shots", nargs="*", default=["2:130", "3:92"], metavar="R:SHOTS")
    ap.add_argument("--cal-shots", type=int, default=4000)
    ap.add_argument("--kmax", type=int, default=4, help="the k of the circuits rule D3' scales")
    ap.add_argument("--round-to", type=int, default=100)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--conf", type=float, default=0.95)
    ap.add_argument("--no-crosscheck", action="store_true",
                    help="skip the apply_groups cross-check of the ideal probabilities (tests only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    t0 = time.time()
    if not args.backend and not args.calibration:
        raise SystemExit("give --backend <name> or --calibration <calibration_<stamp>.json>")

    prep = os.path.join(ROOT, args.prep)
    index = load_index(prep)
    mans, cals = load_manifests(prep)
    g2 = index["common"]["g2"]
    model = Model(int(index["common"]["lattice"].split("x")[1]))

    backend, backend_name, calibration_block, f_source = None, None, None, None
    f_live, f_file = {}, {}
    if args.backend:
        from gate_S2D import analyse_on_backend
        backend_name = args.backend
        backend = resolve_backend(args.backend)
        for m in mans:
            f_live[m["id"]] = float(analyse_on_backend(load_circuit(prep, m), backend)["f"])
        iso = last_update_date(backend)
        from h0_backends import calibration_stamp
        calibration_block = {
            "path": (args.calibration or
                     (f"{args.backend} snapshot" if is_fake(args.backend) else f"live {args.backend} target")),
            "backend": args.backend, "last_update_date": iso,
            "stamp": ("FakeFez snapshot" if is_fake(args.backend) else calibration_stamp(iso)),
        }
        f_source = f"gate_S2D.analyse_on_backend(frozen circuit, {args.backend}.target)"
    if args.calibration:
        cal, cz, meas = load_calibration(args.calibration)
        for m in mans:
            f_file[m["id"]] = f_from_calibration(load_circuit(prep, m), cz, meas)[0]
        calibration_block = {
            "path": args.calibration, "backend": cal.get("backend"),
            "last_update_date": cal.get("last_update_date"), "stamp": cal.get("stamp"),
        }
        if not args.backend:
            f_source = (f"offline recomputation from {args.calibration} with the formula of "
                        f"gate_S2D.analyse_on_backend (per-edge cz and per-qubit measure errors)")

    f_by_circuit = f_live or f_file
    crosschecks = {}
    if f_live and f_file:
        d = max(abs(f_live[c] - f_file[c]) for c in f_live)
        crosschecks["backend_vs_calibration_file_max_df"] = float(d)
        if d >= F_CROSSCHECK_TOL:
            raise SystemExit(f"the f of {args.backend}.target and of {args.calibration} differ by "
                             f"{d:.3e} >= {F_CROSSCHECK_TOL:g}: they are not the same calibration")
    snap = index["common"]["backend"]
    if (backend_name == snap) or (calibration_block and calibration_block.get("backend") == snap):
        d = max(abs(f_by_circuit[m["id"]] - float(m["f_calibration_snapshot"])) for m in mans)
        crosschecks["manifest_snapshot_max_df"] = float(d)

    plan = build_plan(args, prep, mans, model, g2, f_by_circuit, f_source, calibration_block,
                      backend=backend, backend_name=backend_name)
    plan["f_crosschecks"] = crosschecks
    plan["runtime_s"] = time.time() - t0

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(plan, fh, indent=1)
    print(f"rule D3' on {backend_name or calibration_block['path']} "
          f"(calibration {calibration_block.get('last_update_date')})")
    for sec, v in plan["sectors"].items():
        print(f"  {sec}: N4 {v['N4']}, r=1 shots {v['r1_shots_total']}, "
              f"min lambda at {args.margin} f {v['min_lambda_r1_at_margin']:.4f} "
              f"(lambda* {plan['lambda_star']:.4f}), P(sat) clean {v['P_saturation_clean_at_margin']:.5f} "
              f"| frozen plan: clean {v['P_saturation_frozen_plan_clean']:.4f}, "
              f"with garbage {v['P_saturation_frozen_plan_with_garbage']:.4f}")
    print(f"  amplitude cross-check max |dp| {plan['amplitude_crosscheck_max_dp']:.2e}; "
          f"f cross-checks {crosschecks}")
    print(f"  totals: {plan['totals']['r1_shots']} r=1 shots, {plan['totals']['coarse_shots']} coarse "
          f"shots, QPU execution {plan['totals']['qpu_execution_s']}")
    print(f"wrote {out} ({plan['runtime_s']:.0f} s)")
    if args.report:
        rp = args.report if os.path.isabs(args.report) else os.path.join(ROOT, args.report)
        os.makedirs(os.path.dirname(rp), exist_ok=True)
        with open(rp, "w") as fh:
            fh.write(report_text(plan))
        print(f"wrote {rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
