"""Coherence requirement of a compiled circuit: what T2 a device must have to run it.

`skqd.idle` answers "given a calibration record, what does the idle time of this schedule
cost in log-error units".  This module inverts that question -- given a schedule and a
target clean-shot fraction, what coherence time does the device need -- and puts the answer
next to the closed-form estimate the owner uses for a nearly serial circuit,

    T2 / t_2q  >=  n_qubits x n_2q / (2 ln(1/f_target))                       (`serial_bound`)

which assumes (a) a perfectly serial circuit, T = n_2q t_2q, (b) every qubit idle for the
whole of T, and (c) the linearised T2 term only (no T1 channel, no saturation of
1 - e^{-w/T2}).  On the frozen 2x2 canary (a) holds to 3 % and (b) does not: the qubit-time
utilisation is 0.233 (`data/S2_duration_compare.json` rescheduling_headroom), so the qubits
are idle 77 % of T rather than 100 %.  `t2_requirement` therefore solves the real budget of
`skqd.idle` (a per-qubit sum over the ACTUAL idle windows of an ASAP schedule) by bisection,
and the ratio of the two numbers is a measurement rather than an assumption.

Nothing here is fitted and nothing here is a criterion.  Two conventions are always
arguments of the call, never choices of this module:

* **which T2**.  The bound is quoted as the dimensionless ratio T2 / t_2q; whether the
  vendor's number is a Hahn-echo T2 or an in-circuit T2* is the vendor's to declare
  (amendment 01 item 2, `skqd.idle`'s "Which T2" note).
* **the T1 channel**.  `t1_mode="inf"` charges dephasing only (the serial formula's premise);
  `t1_mode="equal"` sets T1 = T2, which is the pessimistic end for a device that quotes one
  coherence number.

`uniform_record` builds a calibration record in exactly the format
`scripts/h0_backends.calibration_record` writes, so `skqd.idle` reads a synthetic uniform
device and a real snapshot through the same code path.
"""
from __future__ import annotations

import math

import numpy as np

from . import idle as _idle

# `t1_mode="inf"` is realised as a very long but finite T1, so that the fast budget below and
# `idle.idle_budget` (which always evaluates both channels) agree bit for bit.
T1_INFINITE_S = 1e9

# Heron r2 durations of the record the 2x2 canary ran on
# (data/hardware/H0_diag_prep/calibration_20260922T1400Z.json): cz 68 ns, sx and x 24 ns,
# measure 1.66 us, dt 4 ns.  Named here only as the default of `uniform_record`; every
# gate script passes the numbers it read from a record.
HERON_T_2Q = 68e-9
HERON_T_1Q = 24e-9
HERON_T_RO = 1.66e-6
HERON_DT = 4e-9

# `t_1q = 0` is the serial formula's premise (the duration comes from the two-qubit gates
# alone).  `skqd.idle.idle_budget` divides a window by 4 x sx_duration_s to decide DD
# eligibility, so the record cannot carry a one-qubit duration of exactly zero.  This value
# is 7e10 times shorter than a 68 ns CZ -- numerically zero in the schedule at double
# precision -- and it changes nothing else: with sx_error = 0 the DD cost S_DD is zero, and
# `idle_log_budget(rho=None)`, the DD-off budget every requirement here is read on, does not
# use the eligible/ineligible split at all.
ZERO_1Q_DURATION_S = 1e-18


# ------------------------------------------------------------------ records
def uniform_record(n_qubits: int, edges, t_2q: float = HERON_T_2Q, t_1q: float = HERON_T_1Q,
                   t_ro: float = HERON_T_RO, T1: float = 1e-3, T2: float = 1e-4,
                   dt: float = HERON_DT, sx_error: float = 0.0, cz_error: float = 0.0,
                   measure_error: float = 0.0, name: str = "uniform") -> dict:
    """A calibration record with the same duration, error and coherence time on every qubit.

    The format is `scripts/h0_backends.calibration_record`'s: `qubits[str q]` carries
    `sx_duration_s`, `x_duration_s`, `measure_duration_s`, `T1_s`, `T2_s`, `sx_error`,
    `measure_error`; `edges["a-b"]` carries `cz_duration_s` and `cz_error`; `dt_s` is the
    device time quantum.  `edges` is any iterable of qubit pairs (undirected; each pair is
    recorded once under the sorted key, which is what `idle.instruction_duration_s` looks up).

    `t_1q = 0` (the serial formula's premise) is stored as `ZERO_1Q_DURATION_S`; see its note.
    """
    t_1q_asked = float(t_1q)
    t_1q = t_1q_asked if t_1q_asked > 0.0 else ZERO_1Q_DURATION_S
    q = {str(int(i)): {"sx_duration_s": float(t_1q), "x_duration_s": float(t_1q),
                       "rz_duration_s": 0.0, "measure_duration_s": float(t_ro),
                       "T1_s": float(T1), "T2_s": float(T2),
                       "sx_error": float(sx_error), "x_error": float(sx_error),
                       "measure_error": float(measure_error)}
         for i in range(int(n_qubits))}
    e = {}
    for a, b in edges:
        a, b = int(a), int(b)
        key = f"{min(a, b)}-{max(a, b)}"
        e[key] = {"target_key": [min(a, b), max(a, b)],
                  "cz_duration_s": float(t_2q), "cz_error": float(cz_error)}
    return {"backend": name, "num_qubits": int(n_qubits), "dt_s": float(dt),
            "last_update_date": None, "qubits": q, "edges": e, "missing_errors": [],
            "uniform": {"t_2q_s": float(t_2q), "t_1q_s": float(t_1q),
                        "t_1q_requested_s": t_1q_asked, "t_ro_s": float(t_ro),
                        "T1_s": float(T1), "T2_s": float(T2), "sx_error": float(sx_error),
                        "cz_error": float(cz_error), "measure_error": float(measure_error)}}


def complete_edges(n_qubits: int) -> list:
    """Every pair of an all-to-all device (the coupling map the logical counts are taken on)."""
    return [(a, b) for a in range(int(n_qubits)) for b in range(a + 1, int(n_qubits))]


def record_t_2q(record: dict) -> float:
    """The two-qubit gate duration of a record whose edges all share one (a uniform record)."""
    vals = sorted({float(e["cz_duration_s"]) for e in record["edges"].values()})
    if len(vals) != 1:
        raise ValueError(f"the record's cz durations are not uniform: {len(vals)} distinct values")
    return vals[0]


# ------------------------------------------------------------------ the serial estimate
def serial_bound(n_qubits: int, n_2q: int, f_target: float) -> float:
    """T2 / t_2q >= n_qubits x n_2q / (2 ln(1/f_target)): the owner's closed form.

    Derivation: a perfectly serial circuit runs T = n_2q t_2q; if every one of the n_qubits
    qubits idles for all of it, the linearised PTA dephasing budget is
    S_T2 = n_qubits x (T / T2) / 2, and S_T2 <= ln(1/f_target) is the statement above."""
    if not 0.0 < float(f_target) < 1.0:
        raise ValueError("f_target must be in (0, 1)")
    return int(n_qubits) * int(n_2q) / (2.0 * math.log(1.0 / float(f_target)))


# ------------------------------------------------------------------ schedule statistics
def seriality(sch: dict, n_2q: int, t_2q: float) -> float:
    """T / (n_2q t_2q): 1.0 for a perfectly serial circuit, less when gates run in parallel."""
    den = int(n_2q) * float(t_2q)
    return float(sch["T_s"]) / den if den > 0 else float("nan")


def utilisation(sch: dict) -> float:
    """Qubit-time utilisation sum_q busy_q / (n_active T) -- premise (b) of the serial form."""
    T = float(sch["T_s"])
    act = sch["active"]
    if not act or T <= 0.0:
        return float("nan")
    busy = sum(sch["per_qubit"][q]["busy_s"] for q in act)
    return busy / (len(act) * T)


def packing_bound(sch: dict) -> dict:
    """T_min = max_q busy_q and the perfectly packed schedule (one window per qubit).

    A qubit executes its own instructions serially, so `T_min` is a rigorous lower bound on
    the duration of ANY reordering of the same gates on the same layout, and because
    1 - e^{-w/T} is concave, putting each qubit's idle time into ONE window minimises the PTA
    budget **at fixed total idle time** -- the same construction
    `scripts/s2_duration_compare.packing_bound` uses at 2x2.

    One caveat that the budget comparison has to carry: `idle.schedule_asap` opens a window
    only BETWEEN instructions, so the time a qubit sits idle after its own last gate while
    others finish is counted in `idle_s` but is not a window and costs nothing in the PTA
    budget.  The packed schedule charges the full T_min - busy_q, so when T_min is close to T
    (a schedule whose critical path is one qubit's own busy time) its budget can come out
    ABOVE the ASAP one.  The duration bound is unconditional; the budget bound holds at equal
    total charged idle time.
    """
    act = sch["active"]
    T_min = max((sch["per_qubit"][q]["busy_s"] for q in act), default=0.0)
    per_qubit = {}
    for q in act:
        b = sch["per_qubit"][q]["busy_s"]
        w = max(T_min - b, 0.0)
        per_qubit[q] = {"busy_s": b, "delay_s": 0.0, "idle_s": w,
                        "windows_s": [w] if w > 1e-15 else []}
    ideal = {"active": act, "per_qubit": per_qubit, "T_s": T_min,
             "T_total_s": T_min + sch.get("measure_duration_s", 0.0),
             "measured_qubits": sch.get("measured_qubits", []),
             "measure_duration_s": sch.get("measure_duration_s", 0.0)}
    return {"T_min_s": T_min, "T_s": float(sch["T_s"]),
            "speedup_available": (float(sch["T_s"]) / T_min) if T_min > 0 else None,
            "schedule": ideal}


# ------------------------------------------------------------------ the requirement
def window_arrays(sch: dict, record: dict | None = None):
    """(all idle windows, T1 of each window's qubit, T2 of each window's qubit) as arrays.

    The PTA budget of `skqd.idle` is a sum over idle windows of
    (1 - e^{-w/T1})/4 + (1 - e^{-w/T2})/2, so it is a pure function of these three arrays.
    Flattening them once turns each evaluation of the budget into one numpy pass, which is
    what makes the 200-step bisections below affordable on a 2x4 schedule with of order 10^5
    windows; the value at the solution is always re-checked against `idle.idle_budget`
    itself, which stays the definition.
    """
    w, t1, t2 = [], [], []
    Q = (record or {}).get("qubits", {})
    for q in sch["active"]:
        ws = sch["per_qubit"][q]["windows_s"]
        if not ws:
            continue
        w.extend(float(x) for x in ws)
        rec = Q.get(str(q), {})
        t1.extend([float(rec.get("T1_s") or 0.0)] * len(ws))
        t2.extend([float(rec.get("T2_s") or 0.0)] * len(ws))
    return (np.asarray(w, dtype=float), np.asarray(t1, dtype=float),
            np.asarray(t2, dtype=float))


def _S_uniform(w, t2: float, t1: float) -> float:
    """The budget of `idle.idle_log_budget(idle_budget(...))` for one T1 and one T2."""
    if w.size == 0:
        return 0.0
    return float(0.25 * np.sum(-np.expm1(-w / t1)) + 0.5 * np.sum(-np.expm1(-w / t2)))


def _budget(sch, record, t2, t1_mode):
    qs = sch["active"]
    t2_s = {int(q): float(t2) for q in qs}
    t1_s = {int(q): (float(t2) if t1_mode == "equal" else T1_INFINITE_S) for q in qs}
    _pq, tot = _idle.idle_budget(sch, record, t2_s=t2_s, t1_s=t1_s)
    return tot


def t2_requirement(sch: dict, record: dict, f_target: float = 0.1, t1_mode: str = "inf",
                   t_2q: float | None = None, iters: int = 200) -> dict:
    """The smallest UNIFORM T2 at which the idle budget of `sch` stays inside ln(1/f_target).

    Solves `idle_log_budget(idle_budget(sch, record, T2)) = ln(1/f_target)` by bisection on
    log T2 (the left side is monotone decreasing in T2), with the record supplying the
    durations and the sx errors.  `t1_mode`: "inf" charges the T2 channel only (the premise of
    `serial_bound`), "equal" sets T1 = T2.

    Returns the requirement, its ratio to the two-qubit gate duration, the budget actually
    spent at that T2 (which must equal ln(1/f_target) to 1e-9 -- recorded, not asserted), and
    the share of it that the T1 channel carries.  `unconstrained` is True when even T2 -> 0
    leaves the budget inside the target: the schedule has too few or too short idle windows
    for coherence to matter, and no requirement exists.
    """
    if t1_mode not in ("inf", "equal"):
        raise ValueError("t1_mode must be 'inf' or 'equal'")
    budget = -math.log(float(f_target))
    tq = record_t_2q(record) if t_2q is None else float(t_2q)
    w, _t1a, _t2a = window_arrays(sch, record)

    def S(t2):
        return _S_uniform(w, t2, t2 if t1_mode == "equal" else T1_INFINITE_S)

    lo = tq * 1e-6                      # a T2 far below any window: S is at its maximum
    hi = tq * 1e12
    s_lo = S(lo)
    if s_lo <= budget:
        return {"f_target": float(f_target), "t1_mode": t1_mode, "budget_log": budget,
                "T2_req_s": None, "T2_req_over_t_2q": None, "unconstrained": True,
                "S_at_T2_req": s_lo, "S_T1_share": None, "t_2q_s": tq,
                "max_possible_S": s_lo,
                "note": "even T2 -> 0 keeps the idle budget inside ln(1/f_target)"}
    while S(hi) > budget:
        hi *= 2.0
        if hi > tq * 1e24:
            raise RuntimeError("the idle budget does not fall below the target at any T2")
    llo, lhi = math.log(lo), math.log(hi)
    for _ in range(int(iters)):
        mid = 0.5 * (llo + lhi)
        if S(math.exp(mid)) > budget:
            llo = mid
        else:
            lhi = mid
    T2 = math.exp(lhi)                  # the end that MEETS the budget
    tot = _budget(sch, record, T2, t1_mode)     # the definition, re-evaluated at the solution
    S_ref = _idle.idle_log_budget(tot)
    return {"f_target": float(f_target), "t1_mode": t1_mode, "budget_log": budget,
            "T2_req_s": T2, "T2_req_over_t_2q": T2 / tq, "unconstrained": False,
            "S_at_T2_req": S_ref, "S_budget_residual": S_ref - budget,
            "S_fast_minus_S_idle_module": S(T2) - S_ref,
            "S_T1": tot["S_T1"], "S_T2": tot["S_T2"],
            "S_T1_share": (tot["S_T1"] / S_ref) if S_ref > 0 else None,
            "n_windows": tot["n_windows"], "idle_total_s": tot["idle_s"], "t_2q_s": tq,
            "max_possible_S": s_lo}


def requirement_row(sch: dict, record: dict, n_2q: int, f_targets=(0.1, 0.05),
                    t_2q: float | None = None, n_logical: int | None = None) -> dict:
    """One row of the vendor table: schedule statistics, the T2 requirement at each target
    and each T1 convention, and the serial closed form beside it.

    Two counts of "n" appear in the serial formula and they are both recorded, because they
    differ once a circuit is routed: `n_active_qubits` is how many qubits the compiled circuit
    actually occupies (28 plus routing ancillas at 2x4), while `n_logical` is the lattice's own
    qubit count, which is the n the owner's 667 / 1728 / 9372 / 23786 / 7036 were computed
    with.  `measured_over_serial` is quoted against the ACTIVE count, the one the schedule was
    read on; `serial_bound_logical` carries the owner's convention beside it.
    """
    tq = record_t_2q(record) if t_2q is None else float(t_2q)
    n_active = len(sch["active"])
    n_log = int(n_logical) if n_logical else n_active
    out = {
        "n_active_qubits": n_active, "n_logical_qubits": n_log, "n_2q": int(n_2q),
        "t_2q_s": tq, "T_s": float(sch["T_s"]), "T_total_s": float(sch["T_total_s"]),
        "seriality": seriality(sch, n_2q, tq), "qubit_time_utilisation": utilisation(sch),
        "requirements": {}, "serial_bound": {}, "serial_bound_logical": {},
    }
    pb = packing_bound(sch)
    out["T_min_s"] = pb["T_min_s"]
    out["speedup_available"] = pb["speedup_available"]
    for f in f_targets:
        out["serial_bound"][str(f)] = serial_bound(n_active, n_2q, f)
        out["serial_bound_logical"][str(f)] = serial_bound(n_log, n_2q, f)
        for mode in ("inf", "equal"):
            r = t2_requirement(sch, record, f_target=f, t1_mode=mode, t_2q=tq)
            r["serial_bound_T2_over_t_2q"] = out["serial_bound"][str(f)]
            r["serial_bound_logical_T2_over_t_2q"] = out["serial_bound_logical"][str(f)]
            r["measured_over_serial"] = (
                (r["T2_req_over_t_2q"] / out["serial_bound"][str(f)])
                if r["T2_req_over_t_2q"] is not None else None)
            out["requirements"][f"f={f}|T1={mode}"] = r
    return out


# ------------------------------------------------------------------ real-record scale
def coherence_scale_one(sch: dict, record: dict, f_gates: float, f_target: float = 0.1,
                        t2_s: dict | None = None, lam_max: float = 1e6,
                        iters: int = 200):
    """Factor lam on every T1 and T2 of the record at which the idle-aware f of ONE circuit
    reaches `f_target` (DD off) -- the single-circuit form of
    `scripts/gate_S2D_idle.coherence_scale`, with `f_gates` given explicitly so that a
    coherence-ONLY reading (f_gates = 1.0, all gate and readout errors set to zero) can be
    taken on the same record as the full one.

    Because (1 - e^{-w/(lam T)}) is the same function of the window w divided by lam, lam is
    equally the factor by which the SCHEDULE would have to shrink.  Returns (lam, limit) with
    `limit` = f_gates, the lam -> infinity limit; lam is None when even a perfectly coherent
    device leaves f below the target (the gate errors alone exhaust the budget).
    """
    w, t1a, t2a = window_arrays(sch, record)
    if t2_s is not None:                       # an explicit per-qubit T2 convention
        ov = {int(k): float(v) for k, v in t2_s.items()}
        t2l = []
        for q in sch["active"]:
            ws = sch["per_qubit"][q]["windows_s"]
            t2l.extend([ov.get(int(q), float(record["qubits"][str(q)]["T2_s"]))] * len(ws))
        t2a = np.asarray(t2l, dtype=float)

    def value(lam):
        if w.size == 0:
            return float(f_gates)
        s = float(0.25 * np.sum(-np.expm1(-w / (lam * t1a)))
                  + 0.5 * np.sum(-np.expm1(-w / (lam * t2a))))
        return float(f_gates) * math.exp(-s)

    limit = float(f_gates)
    if limit < f_target:
        return None, limit
    if value(1.0) >= f_target:
        return 1.0, limit
    lo, hi = 1.0, 1.0
    while value(hi) < f_target:
        hi *= 2.0
        if hi > lam_max:
            return None, limit
    for _ in range(int(iters)):
        mid = 0.5 * (lo + hi)
        if value(mid) >= f_target:
            hi = mid
        else:
            lo = mid
    return float(hi), limit


def zero_error_record(record: dict) -> dict:
    """A copy of `record` with every gate and readout ERROR set to zero and every duration,
    T1 and T2 kept -- the record on which `coherence_scale_one` reads the coherence-only
    scale, which always exists (the gate channel can no longer exhaust the budget)."""
    out = dict(record)
    out["qubits"] = {q: {**v, "sx_error": 0.0, "x_error": 0.0, "measure_error": 0.0}
                     for q, v in record["qubits"].items()}
    out["edges"] = {k: {**v, "cz_error": 0.0} for k, v in record["edges"].items()}
    return out
