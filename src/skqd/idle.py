"""Idle-time relaxation in the clean-shot fraction f.

`gate_S2D.analyse_on_backend` (and `device_req.clean_shot_fraction`, its inverse algebra)
computes f as a product over the *instructions* of a compiled circuit,

    f_gates = prod_{2q gates} (1 - eps_gate) x prod_{measured qubits} (1 - eps_ro) ,

and therefore contains no term for the time a qubit spends WAITING for other qubits'
gates.  On a heavy-hex device the routed 2x2 coarse step is nearly serial (663 CZ in
depth 1328, 43.71 us before readout) and each of its 12 qubits idles 19-42 us of that;
the omission is not small.  Gate H0_diag (2026-09-22, `validation/H0_diag.json`) measured
the canary circuit under {DD on/off} x {twirling on/off} and found f = 0.0255 where
`analyse_on_backend` predicted 0.2195, with the idle term accounting for the whole
discrepancy (3.323 error units available against 2.153 missing).

This module adds that term, with no fitted parameter.  It schedules a compiled circuit
ASAP on a calibration RECORD (`scripts/h0_backends.calibration_record`: the record's own
durations, T1, T2 and errors), collects the idle windows of every active qubit, and
converts them into a log-error budget in the Pauli-twirling approximation of thermal
relaxation -- the channel Aer's `RelaxationNoisePass` would attach to an explicit `delay`:

    per idle window w on qubit q:   p = (1 - e^{-w/T1_q})/4 + (1 - e^{-w/T2_q})/2
    S_T1 = sum_q sum_w (1 - e^{-w/T1_q})/4     S_T2 = sum_q sum_w (1 - e^{-w/T2_q})/2
    f    = f_gates x exp(-S_T1 - S_T2)                                   (DD off)

The runtime's `PadDynamicalDecoupling` pads a window only when it is longer than
`sequence_min_length_ratios` (default 2.0) times the sequence length, so with XY4 =
4 x sx_duration a window is DD-eligible when w / (4 sx_duration) > 2.0, and one sequence
per eligible window costs S_DD = sum_eligible 4 x sx_error.  The refocusing efficiency
rho (the fraction of the eligible-window T2 budget that survives DD) is not computable
from a calibration, so DD-on predictions are a bracket over rho:

    f(rho) = f_gates x exp(-S_T1 - rho S_T2_eligible - S_T2_ineligible - S_DD) .

**Which T2.**  The calibration record's `T2_s` is the vendor's Hahn-echo T2; the windowed
Ramsey test of gate H0_diag measured the free-induction T2* on the same patch on the same
day and found it 2-7x shorter (median ratio 0.174 over the 9 qubits with a usable time).
Neither is the effective dephasing time inside a circuit, and H0_diag does not determine
where between them it lies: on the echo T2 the idle-aware model predicted 31 accepted
shots against the measured 35 (a factor 1.13), on the measured T2* it is 89x too
pessimistic.  This module therefore never chooses: `idle_budget` takes an explicit
per-qubit `t2_s` override and `effective_t2` builds one from a recorded ratio, so the
convention is always an argument of the call and a recorded field of the output.

Nothing here is a criterion and nothing here is fitted.  The bars of amendment 01
section 1(c) (mean f >= 0.1, worst f >= 0.05) are unchanged; what changes is the f they
are read on.
"""
from __future__ import annotations

import math

# qiskit_ibm_runtime.transpiler.passes.scheduling.PadDynamicalDecoupling defaults
DD_MIN_LENGTH_RATIO = 2.0
XY4_PULSES = 4                      # X, Y, X, Y -- 4 x the single-qubit pulse duration

ZERO_DURATION = ("barrier", "rz")   # frame changes and synchronisation cost no time


# --------------------------------------------------------------------- durations
def instruction_duration_s(record: dict, name: str, qubits) -> float:
    """Duration of `name` on `qubits` in seconds, read from a calibration RECORD.

    The record is the one `scripts/h0_backends.calibration_record` writes: per qubit
    `sx_duration_s`, `x_duration_s`, `measure_duration_s`, per edge `cz_duration_s`.
    """
    if name in ZERO_DURATION:
        return 0.0
    Q, E = record["qubits"], record["edges"]
    if name in ("sx", "id"):        # `id` is one single-qubit pulse slot
        return float(Q[str(qubits[0])]["sx_duration_s"])
    if name == "x":
        return float(Q[str(qubits[0])]["x_duration_s"])
    if name == "measure":
        return float(Q[str(qubits[0])]["measure_duration_s"])
    if name == "cz":
        a, b = qubits
        e = E.get(f"{a}-{b}") or E.get(f"{b}-{a}")
        if e is None:
            raise KeyError(f"the calibration record has no cz entry for the edge ({a}, {b})")
        return float(e["cz_duration_s"])
    raise KeyError(f"no duration for instruction '{name}' in the calibration record")


# --------------------------------------------------------------------- scheduling
def schedule_asap(qc, record: dict) -> dict:
    """ASAP schedule of a compiled circuit `qc` on the record's durations.

    Returns {"active", "per_qubit" -> {busy_s, delay_s, idle_s, windows_s}, "T_s",
    "T_total_s", "measured_qubits", "measure_duration_s"}.  `T_s` is the critical path
    before the measure layer; `T_total_s` adds the (single) measure layer, which is what
    `scripts/h0_qpu_time.circuit_duration_s` reports for the same circuit.

    A `delay` counts as BUSY time, not as an idle window: it is an instruction the
    scheduler placed and its relaxation is modelled explicitly wherever a delay is used.
    A barrier synchronises its qubits, which opens an idle window on every qubit that
    reaches it early.
    """
    dt = float(record["dt_s"])
    active = sorted({qc.find_bit(q).index for inst in qc.data for q in inst.qubits
                     if inst.operation.name != "barrier"})
    t = {q: 0.0 for q in active}
    busy = {q: 0.0 for q in active}
    delayed = {q: 0.0 for q in active}
    windows = {q: [] for q in active}
    measured, meas_dur = [], {}
    for inst in qc.data:
        name = inst.operation.name
        qs = [qc.find_bit(q).index for q in inst.qubits]
        if name == "barrier":
            qs = [q for q in qs if q in active]
            if not qs:
                continue
            tm = max(t[q] for q in qs)
            for q in qs:
                if tm > t[q] + 1e-15:
                    windows[q].append(tm - t[q])
                    t[q] = tm
            continue
        if name == "measure":
            measured.append(qs[0])
            meas_dur[qs[0]] = instruction_duration_s(record, "measure", qs)
            continue
        if name == "delay":
            d = float(inst.operation.duration) * dt
            delayed[qs[0]] += d
        else:
            d = instruction_duration_s(record, name, qs)
        start = max(t[q] for q in qs)
        for q in qs:
            if start > t[q] + 1e-15:
                windows[q].append(start - t[q])
            t[q] = start + d
            busy[q] += d
    T = max(t.values()) if t else 0.0
    T_total = T + (max(meas_dur.values()) if meas_dur else 0.0)
    per_q = {q: {"busy_s": busy[q], "delay_s": delayed[q], "idle_s": T - busy[q],
                 "windows_s": windows[q]} for q in active}
    return {"active": active, "per_qubit": per_q, "T_s": T, "T_total_s": T_total,
            "measured_qubits": sorted(measured),
            "measure_duration_s": (max(meas_dur.values()) if meas_dur else 0.0)}


# --------------------------------------------------------------------- T2 convention
def _effective_time(record: dict, key: str, qubits=None, ratio: float = 1.0,
                    per_qubit_ratio: dict | None = None) -> dict:
    pr = {int(k): float(v) for k, v in (per_qubit_ratio or {}).items()}
    qs = sorted(int(q) for q in record["qubits"]) if qubits is None else sorted(set(map(int, qubits)))
    out = {}
    for q in qs:
        T = record["qubits"][str(q)][key]
        if T is None:
            raise KeyError(f"the calibration record carries no {key} for qubit {q}")
        out[q] = float(T) * pr.get(q, float(ratio))
    return out


def effective_t2(record: dict, qubits=None, ratio: float = 1.0,
                 per_qubit_ratio: dict | None = None) -> dict:
    """{qubit: effective dephasing time} = ratio_q x the record's Hahn-echo T2.

    `ratio = 1.0` with no per-qubit map is the echo end of the bracket (the record as it
    stands).  `per_qubit_ratio` carries measured ratios T2_measured / T2_record where a
    measurement exists (gate H0_diag's windowed Ramsey test), and `ratio` is the fallback
    for every other qubit.  The ratio form, rather than a table of times, is what lets a
    measurement made on one patch be transferred to another qubit explicitly and visibly.
    """
    return _effective_time(record, "T2_s", qubits, ratio, per_qubit_ratio)


def effective_t1(record: dict, qubits=None, ratio: float = 1.0,
                 per_qubit_ratio: dict | None = None) -> dict:
    """{qubit: effective relaxation time} = ratio_q x the record's T1 (see `effective_t2`)."""
    return _effective_time(record, "T1_s", qubits, ratio, per_qubit_ratio)


# --------------------------------------------------------------------- budgets
def idle_budget(sch: dict, record: dict, t2_s: dict | None = None, t1_s: dict | None = None):
    """(per_qubit, totals) log-error budget of the idle windows of a scheduled circuit.

    `t2_s` / `t1_s` override the record's coherence times per qubit (see `effective_t2`,
    `effective_t1`); the durations and the sx errors always come from the record.
    """
    Q = record["qubits"]
    over = {int(k): float(v) for k, v in (t2_s or {}).items()}
    over1 = {int(k): float(v) for k, v in (t1_s or {}).items()}
    per_q = {}
    tot = {"S_T1": 0.0, "S_T2": 0.0, "S_T2_eligible": 0.0, "S_T2_ineligible": 0.0,
           "S_DD": 0.0, "dd_eligible": 0, "n_windows": 0, "idle_s": 0.0, "busy_s": 0.0}
    for q in sch["active"]:
        qq = Q[str(q)]
        T1 = over1.get(int(q), None)
        if T1 is None:
            T1 = float(qq["T1_s"])
        T2 = over.get(int(q), None)
        if T2 is None:
            T2 = float(qq["T2_s"])
        sx_d, sx_e = float(qq["sx_duration_s"]), float(qq["sx_error"])
        w = sch["per_qubit"][q]["windows_s"]
        s1 = sum((1.0 - math.exp(-x / T1)) / 4.0 for x in w)
        s2 = sum((1.0 - math.exp(-x / T2)) / 2.0 for x in w)
        elig = [x for x in w if x / (XY4_PULSES * sx_d) > DD_MIN_LENGTH_RATIO]
        s2e = sum((1.0 - math.exp(-x / T2)) / 2.0 for x in elig)
        sdd = XY4_PULSES * sx_e * len(elig)
        per_q[str(q)] = {
            "T1_s": T1, "T2_s": T2, "sx_duration_s": sx_d, "sx_error": sx_e,
            "busy_s": sch["per_qubit"][q]["busy_s"], "delay_s": sch["per_qubit"][q]["delay_s"],
            "idle_s": sch["per_qubit"][q]["idle_s"], "n_windows": len(w),
            "n_dd_eligible": len(elig),
            "longest_window_s": max(w) if w else 0.0,
            "S_T1": s1, "S_T2": s2, "S_T2_eligible": s2e, "S_T2_ineligible": s2 - s2e,
            "S_DD": sdd,
        }
        tot["S_T1"] += s1
        tot["S_T2"] += s2
        tot["S_T2_eligible"] += s2e
        tot["S_T2_ineligible"] += s2 - s2e
        tot["S_DD"] += sdd
        tot["dd_eligible"] += len(elig)
        tot["n_windows"] += len(w)
        tot["idle_s"] += sch["per_qubit"][q]["idle_s"]
        tot["busy_s"] += sch["per_qubit"][q]["busy_s"]
    tot["exp_minus_S_T1_S_T2"] = math.exp(-tot["S_T1"] - tot["S_T2"])
    return per_q, tot


# --------------------------------------------------------------------- f
def idle_log_budget(totals: dict, rho: float | None = None) -> float:
    """S_idle: the log-error units the idle time costs, `-log(f / f_gates)`.

    `rho = None` is DD off (the whole T2 budget is paid); a float is the DD-on bracket at
    refocusing efficiency rho, which also pays the XY4 pulse cost S_DD.
    """
    if rho is None:
        return totals["S_T1"] + totals["S_T2"]
    return (totals["S_T1"] + float(rho) * totals["S_T2_eligible"]
            + totals["S_T2_ineligible"] + totals["S_DD"])


def relaxation_factor(totals: dict, rho: float | None = None) -> float:
    """exp(-S_idle): the factor by which idle time multiplies the gate-only f."""
    return math.exp(-idle_log_budget(totals, rho))


def f_idle_aware(f_gates: float, totals: dict, rho: float | None = None) -> float:
    """The clean-shot fraction with idle-time relaxation: f_gates x exp(-S_idle).

    `f_gates` is exactly `gate_S2D.analyse_on_backend(tq, backend)["f"]` (equivalently
    `h0_support_plan.f_from_calibration` on the same calibration as a record), so the
    gate-only model is the rho-independent limit S_idle = 0 of this one and the earlier
    numbers remain reproducible.
    """
    return float(f_gates) * relaxation_factor(totals, rho)
