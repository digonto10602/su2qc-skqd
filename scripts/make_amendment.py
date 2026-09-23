#!/usr/bin/env python3
"""
Generate proposal/amendment_01_devices_and_budgets.md (prompts/12 step 6, prompts/21) from
validation/S2D.json, validation/S2.json, validation/S2D_idle.json, validation/L4_fez.json,
data/H0_patch_select.json and data/S2_duration_compare.json.

Rule of the project: no number is typed by hand.  Every numeric value in the amendment is
pulled from a JSON file through `cite(path, fmt)`, which records the JSON path it came
from; the document ends with the provenance table of those paths, and the script verifies
after writing that every cited string really occurs in the file (and only then exits 0).
Where a cited value is rendered in another unit or as a percentage change, the conversion is
a `xf` callable of this script and is spelled out in the provenance table next to the path.

Usage: python scripts/make_amendment.py [--check-only]
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "proposal", "amendment_01_devices_and_budgets.md")


class Cites:
    """cite("S2D:data.2x3.f.mean", "{:.4f}") -> the formatted value, remembered for the
    provenance table and for the post-write verification."""

    def __init__(self):
        self.src, self.paths, self.items = {}, {}, []

    def load(self, tag, path):
        with open(path) as fh:
            self.src[tag] = json.load(fh)
        self.paths[tag] = os.path.relpath(path, ROOT)
        return self.src[tag]

    def raw(self, path):
        """Longest-key lookup, so that JSON keys containing '.' or '/' (e.g.
        'eps2_required_for_f_0.1', '2x3 / all-to-all') can be addressed with a dotted path."""
        tag, rest = path.split(":", 1)
        node = self.src[tag]
        while rest:
            if isinstance(node, list):
                part, _, rest = rest.partition(".")
                node = node[int(part)]
                continue
            cands = [k for k in node if rest == k or rest.startswith(k + ".")]
            if not cands:
                raise KeyError(f"{path}: cannot resolve '{rest}'")
            k = max(cands, key=len)
            node, rest = node[k], rest[len(k) + 1:]
        return node

    def __call__(self, path, fmt="{}", xf=None, note=None):
        """`xf` is an optional conversion (unit change, percentage change) applied to the JSON
        value before formatting; `note` names it in the provenance table."""
        val = self.raw(path)
        txt = fmt.format(val if xf is None else xf(val))
        self.items.append((path, val, txt, note))
        return txt

    def table(self):
        lines = ["| value in this document | source (JSON path) | value in the JSON |", "|---|---|---|"]
        seen = set()
        for path, val, txt, note in self.items:
            if (path, txt) in seen:
                continue
            seen.add((path, txt))
            tag, rest = path.split(":")
            conv = f", {note}" if note else ""
            lines.append(f"| `{txt}` | `{self.paths[tag]}` -> `{rest}`{conv} | `{val}` |")
        return "\n".join(lines)

    def verify(self, text):
        missing = [(p, t) for p, v, t, n in self.items if t not in text]
        return missing


SIGNED = "2026-09-23"          # the date the owner signed items 1, 2 and 3 (not a measurement)
PCT = lambda v: (v - 1.0) * 100.0        # ratio -> percentage change
US = lambda v: v * 1e6                   # seconds -> microseconds
PCT_NOTE = "rendered as the percentage change (v - 1) x 100"
US_NOTE = "rendered in us (x 1e6)"


def build(C):
    S = C.load("S2D", os.path.join(ROOT, "validation", "S2D.json"))
    C.load("S2", os.path.join(ROOT, "validation", "S2.json"))
    SI = C.load("S2D_idle", os.path.join(ROOT, "validation", "S2D_idle.json"))
    C.load("H0_patch_select", os.path.join(ROOT, "data", "H0_patch_select.json"))
    C.load("S2_duration_compare", os.path.join(ROOT, "data", "S2_duration_compare.json"))
    l4p = os.path.join(ROOT, "validation", "L4_fez.json")
    has_l4 = os.path.exists(l4p)
    if has_l4:
        C.load("L4_fez", l4p)
    best = S["data"]["2x2"]["best_snapshot"]
    other = [b for b in S["data"]["2x2"]["snapshots"] if b != best][0]
    status = S["status"]
    stamp = time.strftime("%Y-%m-%d")
    # the live-record leg of gate S2D_idle, and the two ends of its T2 bracket
    live = "data.records.live ibm_fez at the canary submission"
    echo = f"S2D_idle:{live}.by_convention.echo"
    star = f"S2D_idle:{live}.by_convention.star"
    # the record the canary actually flew, and the full-device search, in data/H0_patch_select.json
    canary_rec, full_dev = "H0_patch_select:sources.0.result", "H0_patch_select:sources.7.result"
    early_recs = ["H0_patch_select:sources.3.result", "H0_patch_select:sources.4.result"]
    assert SI["data"]["records"]["live ibm_fez at the canary submission"]  # fail loudly if renamed

    # ---- tables built entirely from cited values
    dev_rows = [
        [f"2x2 ({C('S2D:data.2x2.n_qubits')} qubits)", "Heron-class superconducting, heavy-hex, native CZ",
         f"{C(f'S2D:data.2x2.snapshots.{best}.cz.mean', '{:.0f}')} CZ",
         C(f"S2D:data.2x2.snapshots.{best}.f.mean", "{:.4f}"),
         C(f"S2D:data.2x2.snapshots.{best}.f.min", "{:.4f}"),
         "calibration snapshot " + best, "yes"],
        [f"2x3 ({C('S2D:data.2x3.n_qubits')} qubits)", "all-to-all trapped ion, native RZZ",
         f"{C('S2D:data.2x3.rzz.mean', '{:.0f}')} RZZ",
         C("S2D:data.2x3.f.mean", "{:.4f}"), C("S2D:data.2x3.f.min", "{:.4f}"),
         f"declared eps2 = {C('S2D:data.assumed_inputs.eps2_two_qubit_all_to_all', '{:g}')}", "**no**"],
    ]
    budget = S["data"]["shot_budget"]
    b_rows = []
    for tag in budget:
        for sec in budget[tag]:
            p = f"S2D:data.shot_budget.{tag}.{sec}"
            b_rows.append([tag, sec, C(f"{p}.n_circuits"), C(f"{p}.mean_f", "{:.4f}"),
                           C(f"{p}.yield", "{:.4f}"), C(f"{p}.N_circuit"), C(f"{p}.N_sector", "{:.3e}"),
                           "yes" if C.raw(f"{p}.within_manual_budget") else "no"])
    l4_rows = []
    if has_l4:
        for sec in ("B=0", "B=1"):
            p = f"L4_fez:data.{sec}"
            l4_rows.append([sec, C(f"{p}.circuits"), C(f"{p}.shots"), C(f"{p}.cz", "{:.0f}"),
                            C(f"{p}.f_model", "{:.4f}"), C(f"{p}.predicted_yield", "{:.4f}"),
                            C(f"{p}.yield_", "{:.4f}"), C(f"{p}.ratio_measured_over_predicted", "{:.2f}"),
                            C(f"{p}.size"), C(f"{p}.recall", "{:.3f}")])
    l4_block = ("*(not available: `validation/L4_fez.json` does not exist yet)*" if not has_l4 else f"""
| sector | circuits | shots/circuit | CZ | f ({best}) | predicted yield 0.82 f | measured yield | measured / predicted | \\|B\\| | recall of the 99.9 % support |
|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in l4_rows) + f"""

Status of that run: **{C('L4_fez:status')}** ({C('L4_fez:runtime_s', '{:.0f}')} s on the laptop CPU, criterion: measured
yield within a factor 3 of the manual's 0.82 f).  Both sectors keep the exact E_0 inside the Weinstein
interval, so bit order, decoder and sector filter survive a full calibration-snapshot noise model --
which is exactly what gate H0 has to confirm on hardware.

Two things the owner should note before H0.  (i) The manual's yield model is **conservative**: the measured
yield is a factor {C('L4_fez:data.B=0.ratio_measured_over_predicted', '{:.2f}')} (B = 0) and
{C('L4_fez:data.B=1.ratio_measured_over_predicted', '{:.2f}')} (B = 1) above 0.82 f, in the same direction in both
sectors.  The manual's uniform-garbage term (0.15 % of random bitstrings decode) is far too small to explain
that; the excess is corrupted shots that still decode as a valid configuration of the right sector, because
the errors are local and leave most of the string intact.  (ii) Gate H0's preregistered criterion is
"measured f within 30 % of the model"; a systematic factor
{C('L4_fez:data.B=0.ratio_measured_over_predicted', '{:.2f}')} sits just outside that window, so either the yield
model gains a calibrated acceptance term before H0 or H0's tolerance is revisited.  This amendment flags the
question and does not decide it.""")

    tbl = lambda head, rows: ("| " + " | ".join(head) + " |\n|" + "---|" * len(head) + "\n"
                              + "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows))

    doc = f"""# Amendment 01 — devices and budgets (items 1-3 signed {SIGNED}; items 4 and 5 open)

Status: **items 1, 2 and 3 signed by the owner on {SIGNED}** on the evidence named in section 5;
**items 4 and 5 remain open.**  Prepared by the executor from `validation/S2D.json` (gate S2D, status
**{status}**), `validation/S2.json`, `validation/S2D_idle.json` (gate S2D_idle, status
**{C('S2D_idle:status')}**), `validation/L4_fez.json`, `data/H0_patch_select.json` and
`data/S2_duration_compare.json`; every number is cited in the provenance table at the end and
re-checked against the JSON by `scripts/make_amendment.py`.  This amendment changes the *device
assignment*, the *budget criterion* and the *figure of merit* of the preregistration.  It does **not**
change the circuit family, any physics convention, any decoder, any frozen circuit, or any statistical
threshold.

What signing did and did not settle, in one line: item 2 fixes the **bar** (the clean-shot fraction is
read on the scheduled circuit, thresholds unchanged), and on that bar the present 2x2/Heron leg
**fails** — signing a criterion is not a claim that the device meets it.

## 1. What is amended

**(a) Device per lattice.**  The preregistration assumed one Heron-class superconducting device for both
lattices.  The amendment assigns:

{tbl(["lattice", "device", "two-qubit gates per coarse step", "mean f (gate-only)",
      "worst-circuit f (gate-only)", "f computed from", "meets f >= 0.1 (gate-only)"], dev_rows)}

The two f columns of that table are the **gate-and-readout** f of the original draft, i.e. the
S_idle = 0 limit of the criterion the owner signed as item 2.  Read on the scheduled circuit, the 2x2
row does not meet the criterion either (section 2, item 2 of section 5); the row is kept because it is
what gate S2D computed and because the device assignment itself is unchanged.

**(b) Circuit family: unchanged.**  The exact structured circuits of gate S2 (`validation/S2.json`,
`skqd.circuits_ir.structured_term_gates`, `angle_mode="exact"`) remain the preregistered family.  The
fixed-angle alternative measured in `validation/S2_fixed.json` is *not* adopted (re-measured under the
corrected figure of merit: item 3 of section 5).  Reproduction checks in gate S2D: the **2x2** k = 1
coarse step gives {C('S2D:data.2x2.ideal_heavy_hex_cz_k1')} CZ routed on the ideal heavy-hex d = 3 map,
identical to the {C('S2:data.2x2.coarse_step.routed.cz')} routed CZ of `validation/S2.json`, whose
all-to-all count for that same 2x2 step is {C('S2:data.2x2.coarse_step.all_to_all.cz')} CZ; the **2x3**
k = 1 coarse step gives {C('S2D:data.2x3.all_to_all_cz_k1')} CZ all-to-all in the CZ basis, identical to
the {C('S2D:data.2x3.S2_all_to_all_cz_k1')} recorded in `validation/S2.json`.  (Errata, {SIGNED}: until
this revision the 2x2 sentence quoted the 2x3 all-to-all count for the 2x2 step.  No criterion, gate
count or JSON record changed; the sentence now cites `validation/S2.json` -> `data.2x2.coarse_step`.)

**(c) The budget criterion.**  Manual Step 4.3 fixed the budget as "<= 250 CZ at 2x2 and <= 500 CZ at
2x3".  Those numbers were derived in Step 4.4 from a physical condition: with per-CZ error eps the
clean-shot fraction is f = (1 - eps)^N_CZ, and the circuits must keep f high enough for the shot budget
to find a configuration of ideal probability p = {C('S2D:data.assumed_inputs.p_configuration_probability', '{:g}')}.
The amendment replaces the gate-count proxy by the condition itself, evaluated on the device that will
actually run the circuits:

> **Budget criterion (amended, as drafted).**  For the production circuit set of a lattice, the
> clean-shot fraction
> f = prod over executed two-qubit gates (1 - eps_gate) x prod over measured qubits (1 - eps_readout),
> computed from the calibration of the device that will run them, must satisfy
> mean f >= 0.1 and worst-circuit f >= 0.05.

**As signed on {SIGNED} (item 2 of section 5), f is read on the *scheduled* circuit:**

> **Budget criterion (as signed).**  f = f_gates x exp(-S_idle), with f_gates the gate-and-readout
> product above and S_idle = S_T1 + S_T2 the relaxation budget of the idle windows of the circuit's own
> ASAP schedule on that device (`skqd.idle`),
> S_T1 = sum_q sum_w (1 - e^(-w/T1_q))/4, S_T2 = sum_q sum_w (1 - e^(-w/T2_q))/2.
> The thresholds are unchanged: **mean f >= 0.1 and worst-circuit f >= 0.05**.  The T2 convention
> (Hahn-echo T2 of the record, or measured free-induction T2*) must be named wherever an f is quoted,
> and a device is assessable only if it declares **gate durations and T1/T2 alongside its error rates**.

f >= 0.1 is the operating point at which gate S1 established recall >= 0.9 of the 99.9 % support with the
production shot budget (`validation/S1.json`); it is therefore the condition the CZ numbers stood for.
The criterion is *not* weaker than the old one: at 2x2 the routed count {C('S2D:data.2x2.S2_heavy_hex_cz_k1')}
CZ is still far above 250, and on the {best} calibration its *gate-only* f is
{C(f'S2D:data.2x2.snapshots.{best}.f.mean', '{:.4f}')} — which is what the draft reported as clearing the
requirement, and what the signed form of the criterion no longer accepts: on the scheduled circuit the
same set gives mean f = {C(f'{echo}.f_dd_off.mean', '{:.2e}')} on the live ibm_fez record with the
Hahn-echo T2 and DD off (section 2, gate S2D_idle).

## 2. Evidence (gate S2D, status {status}; gate S2D_idle, status {C('S2D_idle:status')})

### 2x2 on a Heron-class device — the gate-only computation

{tbl(["snapshot", "device qubits", "circuits", "CZ per circuit", "mean f", "worst f",
      "mean error of the edges used", "snapshot median CZ error", "mean readout error of the patch"],
     [[b, C(f"S2D:data.2x2.snapshots.{b}.backend_qubits"), C(f"S2D:data.2x2.snapshots.{b}.n_circuits"),
       C(f"S2D:data.2x2.snapshots.{b}.cz.mean", "{:.0f}"), C(f"S2D:data.2x2.snapshots.{b}.f.mean", "{:.4f}"),
       C(f"S2D:data.2x2.snapshots.{b}.f.min", "{:.4f}"),
       C(f"S2D:data.2x2.snapshots.{b}.patch_mean_edge_error", "{:.2e}"),
       C(f"S2D:data.2x2.snapshots.{b}.snapshot_median_cz_error", "{:.2e}"),
       C(f"S2D:data.2x2.snapshots.{b}.patch_mean_readout_error", "{:.2e}")]
      for b in (best, other)])}

The transpiler's calibration-aware layout is what makes the difference: on {best} it places the
{C('S2D:data.2x2.n_qubits')} qubits on a patch whose edges average {C(f'S2D:data.2x2.snapshots.{best}.patch_mean_edge_error', '{:.2e}')} against a
snapshot median of {C(f'S2D:data.2x2.snapshots.{best}.snapshot_median_cz_error', '{:.2e}')}.  On {other} the
same construction only reaches mean f = {C(f'S2D:data.2x2.snapshots.{other}.f.mean', '{:.4f}')}, mostly through a
readout error of {C(f'S2D:data.2x2.snapshots.{other}.patch_mean_readout_error', '{:.2e}')} per qubit.  **The 2x2 run
must therefore be scheduled on a device of the {best} class, and the patch must be chosen from the
calibration of the day, not fixed in advance.**  How it is chosen is item 1 of section 5: a
calibration-aware layout is not enough, because the transpiler's layout maximises exactly the
gate-and-readout f of this table and is blind to the idle term that dominates.

### 2x2 — withdrawn as a hardware statement ({SIGNED})

Read on the scheduled circuit, as the signed criterion requires, the same
{C(f'S2D_idle:{live}.n_circuits')} circuits fail at **every** point of the T2 x DD bracket (gate
S2D_idle, `validation/S2D_idle.json`, status {C('S2D_idle:status')}):

{tbl(["record / T2 convention", "f_gates mean", "S_T1 mean", "S_T2 mean", "idle-aware f mean (DD off)",
      "worst", "mean f at the most favourable corner (perfect DD refocusing)", "criterion"],
     [["live ibm_fez at the canary submission / Hahn-echo T2",
       C(f"S2D_idle:{live}.f_gates.mean", "{:.4f}"), C(f"{echo}.S_T1.mean", "{:.3f}"),
       C(f"{echo}.S_T2.mean", "{:.3f}"), C(f"{echo}.f_dd_off.mean", "{:.2e}"),
       C(f"{echo}.f_dd_off.min", "{:.2e}"),
       C(f"{echo}.criterion_best_of_bracket.mean_f", "{:.4f}"), "**FAIL**"],
      ["live ibm_fez at the canary submission / measured T2*",
       C(f"S2D_idle:{live}.f_gates.mean", "{:.4f}"), C(f"{star}.S_T1.mean", "{:.3f}"),
       C(f"{star}.S_T2.mean", "{:.3f}"), C(f"{star}.f_dd_off.mean", "{:.2e}"),
       C(f"{star}.f_dd_off.min", "{:.2e}"),
       C(f"{star}.criterion_best_of_bracket.mean_f", "{:.4f}"), "**FAIL**"]])}

The bars are {C(f'{echo}.criterion_dd_off.mean_f_min')} (mean) and
{C(f'{echo}.criterion_dd_off.worst_f_min')} (worst).  **Gate S2D's 2x2 PASS is therefore withdrawn as a
statement about the hardware**; it stands as the gate-only computation it was, i.e. the S_idle = 0 limit
of the signed criterion, which gate S2D_idle reproduces to a maximum absolute difference of
{C('S2D_idle:criteria.0.value', '{:.1e}')} (criterion V1; `validation/S2D.json` is not rewritten).  Nothing here is a
model artefact: those {C(f'S2D_idle:{live}.n_circuits')} circuits are the r = 1 subset of the frozen H0
set — the circuits that flew — and their measured f is
{C('S2D_idle:data.hardware_anchor.measured_f_by_cell.J1', '{:.4f}')} (J1),
{C('S2D_idle:data.hardware_anchor.measured_f_by_cell.J2', '{:.4f}')} (J2),
{C('S2D_idle:data.hardware_anchor.measured_f_by_cell.J3', '{:.4f}')} (J3),
{C('S2D_idle:data.hardware_anchor.measured_f_by_cell.J4', '{:.4f}')} (J4) and
{C('S2D_idle:data.hardware_anchor.measured_f_H0_canary', '{:.4f}')} in the canary job itself, every one
below the worst-circuit bar with no model at all.

### 2x3 on an all-to-all trapped-ion device — the amendment is NOT yet supported

Declared inputs (vendor-class specifications, **not** measurements):
eps2 = {C('S2D:data.assumed_inputs.eps2_two_qubit_all_to_all', '{:g}')} (two-qubit),
eps1 = {C('S2D:data.assumed_inputs.eps1_one_qubit_all_to_all', '{:g}')} (one-qubit),
eps_ro = {C('S2D:data.assumed_inputs.eps_ro_readout_all_to_all', '{:g}')} (readout).

{tbl(["circuit set", "circuits", "RZZ", "one-qubit gates", "f (2q factor)", "f (1q factor)",
      "f (readout factor)", "mean f", "required"],
     [["2x3 coarse step, RZZ basis, all-to-all", C("S2D:data.2x3.n_circuits"),
       C("S2D:data.2x3.rzz.mean", "{:.0f}"), C("S2D:data.2x3.n_1q.mean", "{:.0f}"),
       C("S2D:data.2x3.f_factors_k1.f_2q", "{:.4f}"), C("S2D:data.2x3.f_factors_k1.f_1q", "{:.4f}"),
       C("S2D:data.2x3.f_factors_k1.f_ro", "{:.4f}"), C("S2D:data.2x3.f.mean", "{:.4f}"), ">= 0.1"]])}

Even with all-to-all connectivity (no routing overhead at all: {C('S2D:data.2x3.rzz.mean', '{:.0f}')} RZZ against
{C('S2D:data.2x3.S2_all_to_all_cz_k1')} CZ for the same circuit) the exact coarse step reaches only
f = {C('S2D:data.2x3.f.mean', '{:.4f}')}, about half of what the criterion requires.  Two-qubit error that would be
needed at these gate counts, holding eps1 and eps_ro: **{C('S2D:data.2x3.eps2_required_for_f_0.1', '{:.2e}')}**.
Note that a quarter of the loss (in log terms) is not the two-qubit error at all: the one-qubit factor alone is
{C('S2D:data.2x3.f_factors_k1.f_1q', '{:.4f}')}.  If the platform implements rz as a virtual frame change (no
physical error), f rises to {C('S2D:data.2x3.f_virtual_rz.mean', '{:.4f}')} -- still below 0.1.  **This is a
decision the owner has to make; the amendment cannot be signed for 2x3 as it stands.**

**Necessary but no longer sufficient ({SIGNED}).**  Everything above is the gate-and-readout f.  Under
the criterion as signed, the two-qubit requirement is the S_idle = 0 row of a table, not a number: the
sheet's requirement is recomputed at the shifted target `f_target e^(S_idle)`
(`skqd.device_req.target_with_idle`) over the same
{C('S2D_idle:data.implication_2x3.n_circuits')} circuits and the same declared inputs
(`reports/S2D_2x3_device_requirements.md`, `reports/S2D_idle_device_budgets.md` section 5):

{tbl(["S_idle of the 2x3 schedule", "shifted mean target", "eps2 for mean f >= 0.1",
      "eps2 for worst f >= 0.05", "mean f at the declared eps2"],
     [[C(f"S2D_idle:data.implication_2x3.rows.{i}.S_idle", "{:.3f}"),
       C(f"S2D_idle:data.implication_2x3.rows.{i}.f_target_mean_shifted", "{:.4f}"),
       C(f"S2D_idle:data.implication_2x3.rows.{i}.eps2_for_mean", "{:.3e}"),
       C(f"S2D_idle:data.implication_2x3.rows.{i}.eps2_for_worst", "{:.3e}"),
       C(f"S2D_idle:data.implication_2x3.rows.{i}.mean_f_at_declared", "{:.4f}")] for i in range(4)]
     + [[C("S2D_idle:data.implication_2x3.rows.4.S_idle", "{:.3f}"), "unreachable", "-", "-", "-"]])}

S_idle for the 2x3 device is **not computed anywhere in this repository and no number is asserted for
it**: the all-to-all device has no declared gate durations and no declared T1/T2, so its schedule cannot
be built.  The last row is the 2x2/Heron idle budget measured on the live record, shown only for scale:
at that S_idle the criterion is unreachable at any gate error.

## 3. Shot budget (manual Step 4.4, eq. 5)

N_circuit = ceil(lambda*/(p y)), lambda* = {C('S2D:data.assumed_inputs.lambda_star', '{:.6f}')} for
k = {C('S2D:data.assumed_inputs.k_min_counts')} counts at confidence
{C('S2D:data.assumed_inputs.confidence')}, y = 0.82 f, p = {C('S2D:data.assumed_inputs.p_configuration_probability', '{:g}')};
N_sector = N_circuit x (number of circuits).  Implementation: `skqd.skqd.shot_rule`.

{tbl(["circuit set / device", "sector", "circuits", "mean f", "yield y", "N_circuit", "N_sector",
      "within the 2e5 of Step 9.2"], b_rows)}

Two findings, neither of which is repaired by lowering p or the confidence (they are preregistered and
were left untouched):

1. At the measured f the 2x3 production run needs
   {C('S2D:data.shot_budget.2x3 / all-to-all.B=0.N_sector', '{:.3e}')} shots in B = 0 and
   {C('S2D:data.shot_budget.2x3 / all-to-all.B=1.N_sector', '{:.3e}')} in B = 1.
2. The 2x10^5-per-sector quota of Step 9.2 is inconsistent with eq. (5) *in the manual itself*: at the
   manual's own design point f = 0.2 eq. (5) asks
   {C('S2D:data.shot_budget.manual design point f = 0.2 (manual eq. 5).any sector.N_circuit')} shots per circuit,
   i.e. {C('S2D:data.shot_budget.manual design point f = 0.2 (manual eq. 5).any sector.N_sector', '{:.3e}')} per sector
   over {C('S2D:data.shot_budget.manual design point f = 0.2 (manual eq. 5).any sector.n_circuits')} circuits.
   The owner must either raise the quota, reduce the circuit set, or accept a larger p (a weaker support
   claim).  **Nothing in this amendment chooses for him.**

Both findings are computed on the gate-only f, and every N_circuit and N_sector in the table above scales
as 1/f: when f is re-read on the scheduled circuit (the criterion as signed), these shot numbers move by
the same factor as f.  That is why item 5 stays open — see section 5 and
`reports/S2D_shot_quota_decision_20260922.md`.

Device time is N_sector / throughput; the throughput of the chosen device is not known here, so the
amendment states the formula and leaves the number to the owner
(`validation/S2D.json` -> `data.device_time_illustrative` holds an illustrative table for 100, 300 and
1000 shots per minute; those are round numbers, not device specifications).

## 4. The H0 role split

The 2x2 lattice cannot test SKQD accuracy (its sectors saturate at 38 and 20 states, manual Step 9.1), so
the amendment fixes what each lattice is *for*:

| lattice / device | what it establishes | gate |
|---|---|---|
| 2x2 on {best}-class Heron | decoder validity, bit order, link-parity checks, sector filter, readout confusion, measured f versus the model | H0 |
| 2x3 on the all-to-all device | yield versus two-qubit-gate count, support recall, certified energies | H1, H2 |

Rehearsal of H0 on the calibration snapshot (`validation/L4_fez.json`, `scripts/laptop_L4_aer_noise.py
--backend {best}`: full `NoiseModel.from_backend`, circuits transpiled onto the snapshot's qubits):
{l4_block}

**Note added {SIGNED}.**  The rehearsal above compares a gate-only model with a gate-only noise
simulation, and in that setting the model is conservative.  On hardware the ordering is the other way
round: the gate-only f predicts
{C('S2D_idle:data.hardware_anchor.gate_only_for_comparison.expected_accepted', '{:.1f}')} accepted shots of
{C('S2D_idle:data.hardware_anchor.echo.shots')} against the
{C('S2D_idle:data.hardware_anchor.echo.measured_accepted')} that gate H0_diag measured (a factor
{C('S2D_idle:data.hardware_anchor.gate_only_for_comparison.factor_measured_over_predicted', '{:.3f}')}),
while the same prediction with the idle term and the Hahn-echo T2 is
{C('S2D_idle:data.hardware_anchor.echo.expected_accepted', '{:.1f}')} against
{C('S2D_idle:data.hardware_anchor.echo.measured_accepted')} (factor
{C('S2D_idle:data.hardware_anchor.echo.factor_measured_over_predicted', '{:.2f}')}).  What was missing was
idle-time relaxation, not the acceptance term; that is what item 2 of section 5 fixes.

## 5. What the owner has signed, and what stays open

Items 1, 2 and 3 are **signed, {SIGNED}**, in the wording below, on the evidence named under each.
Items 4 and 5 remain open.

### 1. The 2x2 qubit patch, and the rule that selects it — SIGNED {SIGNED}

> The 2x2 circuits run on a Heron-class device, and the physical qubit patch is **not** fixed in
> advance: it is selected on the day of the run by the following rule.
>
>   * **Candidates.**  A candidate patch is an embedding of the routed circuit's CZ interaction graph
>     ({C(f'{canary_rec}.pattern.n_nodes')} nodes,
>     {C(f'{canary_rec}.pattern.n_edges')} edges for the 2x2 r = 1 circuit) into the device
>     coupling graph.  Relabelling the frozen circuit along an embedding changes no gate, no angle, no
>     CZ count and no classical-bit mapping — only which physical qubit plays which role.  The
>     enumeration is exhaustive and deterministic.
>   * **Objective.**  `{C.raw('H0_patch_select:objective')}` on the calibration record — the
>     idle-aware clean-shot fraction of item 2, not the gate-and-readout product alone.
>   * **Tie-breaks.**  {C.raw('H0_patch_select:tie_break')}.
>   * **When it runs.**  On the calibration read of the day, on the **full device** (a target query:
>     free, no QPU time).  The H0 calibration records cover only the
>     {C(f'{canary_rec}.host.n_qubits')} qubits the frozen set already uses, so a search
>     restricted to them is a lower bound on what the rule finds.
>   * **Recording and freezing.**  The selected patch, the calibration record it was selected from with
>     its fingerprint, and the relabelled circuits are written to the run's prep directory and frozen
>     before submission, exactly as the present frozen set is.  Implementation and evidence:
>     `scripts/h0_patch_select.py`, `data/H0_patch_select.json`, `reports/H0_patch_select.md`.
>
> Why the rule is needed: the level-3 transpiler's calibration-aware layout is the **exact maximiser of
> gate-plus-readout f on every record tested** — a T2-blind objective returns the transpiler's own patch,
> a gain of {C(f'{canary_rec}.gain.f_dd_off_gate_only_over_incumbent', '{:.2f}')}x, on all
> {C('H0_patch_select:stability.n_committed_records')} committed records and on the full device.  The
> layout pass was not mis-solving its problem; it was solving the wrong one.  Scored with the idle term
> the winner is the same patch with qubit {C(f'{canary_rec}.incumbent.worst_qubit')}
> (T2 {C(f'{canary_rec}.incumbent.worst_qubit_T2_s', '{:.1f}', US, US_NOTE)} us, carrying
> {C(f'{canary_rec}.incumbent.worst_qubit_S_T2', '{:.3f}')} of the patch's
> {C(f'{canary_rec}.incumbent.S_T2', '{:.3f}')} S_T2 units) replaced by qubit
> {C(f'{canary_rec}.best.worst_qubit')}
> (T2 {C(f'{canary_rec}.best.worst_qubit_T2_s', '{:.1f}', US, US_NOTE)} us):
> **{C('H0_patch_select:stability.winners.0')}**.  It is worth
> **{C(f'{canary_rec}.gain.f_dd_off_best_over_incumbent', '{:.2f}')}x** in f on the record the canary
> actually flew ({C(f'{canary_rec}.incumbent.f_dd_off', '{:.3e}')} ->
> {C(f'{canary_rec}.best.f_dd_off', '{:.3e}')}, the transpiler's patch ranking
> {C(f'{canary_rec}.incumbent.rank')} of {C(f'{canary_rec}.n_candidates')} candidates),
> {C(f'{early_recs[0]}.gain.f_dd_off_best_over_incumbent', '{:.2f}')}x to
> {C(f'{early_recs[1]}.gain.f_dd_off_best_over_incumbent', '{:.2f}')}x on the four earlier ibm_fez
> records, and **{C(f'{full_dev}.gain.f_dd_off_best_over_incumbent', '{:.2f}')}x** on the full
> {C(f'{full_dev}.host.n_qubits')}-qubit device, where the transpiler's patch ranks
> {C(f'{full_dev}.incumbent.rank')} of {C(f'{full_dev}.n_candidates')}.  Over the
> {C('H0_patch_select:stability.n_committed_records')} committed records the rule returns
> **{C('H0_patch_select:stability.n_distinct_winners')}** distinct winner.
>
> **This is a factor, not a rescue.**  At {C(f'{canary_rec}.best.f_dd_off', '{:.3e}')} the 2x2
> r = 1 circuit remains far below the f >= 0.1 of item 2: of
> {C(f'{canary_rec}.gain.shots_reference')} shots the predicted accepted count moves from
> {C(f'{canary_rec}.gain.accepted_of_reference_incumbent', '{:.1f}')} to
> {C(f'{canary_rec}.gain.accepted_of_reference_best', '{:.1f}')} over a garbage floor of
> {C(f'{canary_rec}.gain.garbage_floor_of_reference', '{:.1f}')}.  Signing item 1 fixes how the patch is
> chosen; it does not make the 2x2 leg meet the criterion.

Evidence: `reports/H0_patch_select.md`, `data/H0_patch_select.json`
(commit {C('H0_patch_select:commit')}, {C('H0_patch_select:created')}, no QPU time).

### 2. The budget criterion: the idle-aware clean-shot fraction of the scheduled circuit — SIGNED {SIGNED}

> The fixed CZ numbers of manual Step 4.3 are replaced by the criterion of section 1(c), with the
> clean-shot fraction read on the **scheduled** circuit:
> f = f_gates x exp(-S_idle), f_gates the gate-and-readout product and S_idle = S_T1 + S_T2 the
> relaxation budget of the idle windows of the circuit's own ASAP schedule (`skqd.idle`).
>
>   * the thresholds are **unchanged**: mean f >= {C(f'{echo}.criterion_dd_off.mean_f_min')},
>     worst-circuit f >= {C(f'{echo}.criterion_dd_off.worst_f_min')};
>   * the **T2 convention must be named wherever an f is quoted**.  The two ends in use here are the
>     record's Hahn-echo T2 and the measured free-induction T2* (gate H0_diag's windowed Ramsey; median
>     ratio T2*/T2_echo {C('S2D_idle:data.t2_bracket.fallback_ratio', '{:.4f}')}), and on the same 2x2
>     circuits they give mean f {C(f'{echo}.f_dd_off.mean', '{:.2e}')} and
>     {C(f'{star}.f_dd_off.mean', '{:.2e}')} respectively;
>   * a device is **assessable only if it declares gate durations and T1/T2 alongside its error rates**.
>     Without a schedule there is no S_idle and therefore no f: error rates alone are not an answer to
>     this criterion (item 4).
>
> **Signing this fixes the bar; the present 2x2/Heron leg fails it.**  On the idle-aware f that leg does
> not meet the criterion **at any point of the T2 x DD bracket** (gate S2D_idle,
> `validation/S2D_idle.json`, status {C('S2D_idle:status')}): on the live ibm_fez record at the canary
> submission, echo T2, DD off, mean f = {C(f'{echo}.f_dd_off.mean', '{:.2e}')} and worst
> {C(f'{echo}.f_dd_off.min', '{:.2e}')}; and at the most favourable corner of the whole bracket (live
> record, echo T2, perfect DD refocusing — which the hardware contradicts, the canary having run XY4 DD
> on and measured a lower yield than with it off) mean f =
> {C(f'{echo}.criterion_best_of_bracket.mean_f', '{:.4f}')} and worst
> {C(f'{echo}.criterion_best_of_bracket.worst_f', '{:.4f}')}.  Every T1 and T2 of the patch would have to
> be a factor
> {C(f'S2D_idle:data.device_requirement.live ibm_fez at the canary submission.echo.coherence_scale_for_mean_0.1', '{:.1f}')}
> longer to reach the mean bar.  The verdict does not depend on the model: the
> {C(f'S2D_idle:{live}.n_circuits')} circuits of the 2x2 set are the r = 1 subset of the frozen H0 set —
> the circuits that flew — and their measured f is
> {C('S2D_idle:data.hardware_anchor.measured_f_by_cell.J1', '{:.4f}')} (J1),
> {C('S2D_idle:data.hardware_anchor.measured_f_by_cell.J2', '{:.4f}')} (J2),
> {C('S2D_idle:data.hardware_anchor.measured_f_by_cell.J3', '{:.4f}')} (J3),
> {C('S2D_idle:data.hardware_anchor.measured_f_by_cell.J4', '{:.4f}')} (J4) and
> {C('S2D_idle:data.hardware_anchor.measured_f_H0_canary', '{:.4f}')} in the canary job, every one below
> the worst-circuit bar with no model at all.
>
> **Gate S2D's 2x2 PASS is therefore withdrawn as a hardware statement.**  It stands as the gate-only
> computation it was — the S_idle = 0 limit of the criterion above, reproduced by gate S2D_idle to
> {C('S2D_idle:criteria.0.value', '{:.1e}')} — and `validation/S2D.json` is not rewritten.

Evidence: `reports/S2D_idle_device_budgets.md`, `validation/S2D_idle.json`
(commit {C('S2D_idle:environment.git_commit')}, {C('S2D_idle:environment.timestamp')}, no QPU time).

### 3. The circuit family, and the figure of merit by which a family is chosen — SIGNED {SIGNED}

> The circuit family stays the exact structured circuits of gate S2 (`validation/S2.json`,
> `skqd.circuits_ir.structured_term_gates`, `angle_mode="exact"`).  The criterion on which that choice
> rests is amended: a circuit family is judged not by its two-qubit gate count but by the
> **ASAP-scheduled duration and per-qubit idle budget** of its circuits on the calibration of the device
> that will run them —
>
>   * `T` = the ASAP critical path before the measure layer, and the idle window list of every active
>     qubit (`skqd.idle` / `scripts/h0_idle_model.py`);
>   * `S_T1 = sum_q sum_w (1 - e^(-w/T1_q))/4`, `S_T2 = sum_q sum_w (1 - e^(-w/T2_q))/2`;
>   * the idle-aware clean-shot fraction `f = f_gates x exp(-S_T1 - S_T2)` of item 2.
>
> Gate H0_diag (`validation/H0_diag.json`,
> {C('S2_duration_compare:context.H0_diag.total_usage_s', '{:.1f}')} s of QPU time on ibm_fez; J1 gave
> N1 = {C('S2_duration_compare:context.H0_diag.N1')} accepted of
> {C(f'{canary_rec}.gain.shots_reference')}) established the reason: at 2x2 the dominant loss is
> idle-time decoherence over the circuit's wall-clock duration, not the gate count.  The frozen canary
> runs {C('S2_duration_compare:circuits.exact|frozen|B0_ref06_k1_rep1.T_s', '{:.2f}', US, US_NOTE)} us at
> depth {C('S2_duration_compare:circuits.exact|frozen|B0_ref06_k1_rep1.depth')} for only
> {C('S2_duration_compare:circuits.exact|frozen|B0_ref06_k1_rep1.n_cz')} CZ
> ({C('S2_duration_compare:circuits.exact|frozen|B0_ref06_k1_rep1.cz_per_cz_layer', '{:.2f}')} CZ per CZ
> layer, qubit-time utilisation
> {C('S2_duration_compare:rescheduling_headroom.qubit_time_utilisation', '{:.3f}')}), and its idle budget
> is S_T1 = {C('S2_duration_compare:rescheduling_headroom.S_T1_now', '{:.3f}')} plus S_T2 =
> {C('S2_duration_compare:rescheduling_headroom.S_T2_now', '{:.3f}')} error units, which is what
> separates the gate-only prediction from the device.  A family with fewer gates at the same or greater
> duration therefore buys nothing, and a shallower-in-time family wins even at equal gate count.
>
> Re-evaluated on that criterion (`data/S2_duration_compare.json`,
> `reports/S2_duration_and_idle_2x2.md`, {C('S2_duration_compare:n_circuits')} circuits, no QPU time),
> the fixed-angle generator of `validation/S2_fixed.json` is **not adopted** — and now for the right
> reason.  With both families on the canary's own 12 physical qubits and the same ibm_fez calibration
> record ({C('S2_duration_compare:verdict.pinned / ibm_fez.n_pairs')} paired circuits), the fixed-angle
> circuits are
> {C('S2_duration_compare:verdict.pinned / ibm_fez.depth_ratio.mean', '{:+.1f}', PCT, PCT_NOTE)} % in DAG
> depth but
> **{C('S2_duration_compare:verdict.pinned / ibm_fez.T_ratio_fixed_over_exact.mean', '{:+.1f}', PCT, PCT_NOTE)} %
> in duration**,
> {C('S2_duration_compare:verdict.pinned / ibm_fez.idle_ratio.mean', '{:+.1f}', PCT, PCT_NOTE)} % in
> summed idle time and
> {C('S2_duration_compare:verdict.pinned / ibm_fez.cz_ratio.mean', '{:+.1f}', PCT, PCT_NOTE)} % in CZ,
> reaching {C('S2_duration_compare:verdict.pinned / ibm_fez.f_idle_ratio_fixed_over_exact.mean', '{:.3f}')}x
> the exact family's idle-aware f: the exact family wins by
> **{C('S2_duration_compare:verdict.pinned / ibm_fez.win_margin_f', '{:.2f}')}x**.  They are not shallower
> in time, so the earlier rejection on routed CZ count is confirmed rather than reversed, and their known
> cost (a different generator: worst per-term deviation
> {C('S2_duration_compare:context.S2_fixed.max_per_term_deviation_2x2', '{:.3f}')} at 2x2 against
> {C('S2_duration_compare:context.S2.max_deviation', '{:.1e}')} for the exact family, with gate-S1 recall
> {C('S2_duration_compare:context.S2_fixed.recall_2x3_B0', '{:.3f}')} /
> {C('S2_duration_compare:context.S2_fixed.recall_2x3_B1', '{:.3f}')}) is not incurred.  For the record,
> the gate counts on which item 3 was originally decided are
> {C('S2_duration_compare:context.S2.cz_all_to_all_2x2')} all-to-all /
> {C('S2_duration_compare:context.S2.cz_routed_2x2')} routed CZ per 2x2 coarse step for the exact family
> and {C('S2_duration_compare:context.S2_fixed.cz_all_to_all_2x2')} /
> {C('S2_duration_compare:context.S2_fixed.cz_routed_2x2')} for the fixed-angle one.
>
> This item does **not** claim that the exact family is adequate at 2x2 on the present device: at the
> production point it reaches an idle-aware f of
> {C('S2_duration_compare:summary.exact|pinned|ibm_fez.f_idle_dd_off.mean', '{:.2e}')} (mean over
> {C('S2_duration_compare:summary.exact|pinned|ibm_fez.n_circuits')} circuits) against the f >= 0.1 of
> item 2.  What moves that number is duration and patch quality, not the family — see 3(b) and item 1.
>
> **3(b).  Re-scheduling headroom (measured, no new decomposition).**  On the same gates and the same
> layout no qubit can finish before its own busy time, so the duration cannot fall below
> `T_min = max_q busy_q` =
> {C('S2_duration_compare:rescheduling_headroom.T_min_s', '{:.2f}', US, US_NOTE)} us against the
> {C('S2_duration_compare:rescheduling_headroom.T_s', '{:.2f}', US, US_NOTE)} us the ASAP schedule takes:
> a perfect re-schedule is worth at most
> **{C('S2_duration_compare:rescheduling_headroom.speedup_available', '{:.2f}')}x** in duration (S_T1
> {C('S2_duration_compare:rescheduling_headroom.S_T1_now', '{:.3f}')} ->
> {C('S2_duration_compare:rescheduling_headroom.S_T1', '{:.3f}')}, S_T2
> {C('S2_duration_compare:rescheduling_headroom.S_T2_now', '{:.3f}')} ->
> {C('S2_duration_compare:rescheduling_headroom.S_T2', '{:.3f}')}) and
> **{C('S2_duration_compare:rescheduling_headroom.f_gain', '{:.2f}')}x** in f — which reaches
> {C('S2_duration_compare:rescheduling_headroom.f_idle_dd_off', '{:.4f}')}, still short of f >= 0.1.  That
> bound is not attainable: only
> **{C('S2_duration_compare:rescheduling_headroom.terms.n_disjoint_pairs')} of the
> {C('S2_duration_compare:rescheduling_headroom.terms.n_pairs')}** pairs of Hamiltonian terms have
> disjoint support, and the diagonal and plaquette terms touch
> {C('S2_duration_compare:rescheduling_headroom.terms.support_sizes.diag')} and
> {C('S2_duration_compare:rescheduling_headroom.terms.support_sizes.plaq0')} of the
> {C('S2_duration_compare:circuits.exact|frozen|B0_ref06_k1_rep1.n_active')} logical qubits, so no
> term-level re-ordering can put either in parallel with anything else.  Reaching the bound would require
> a different codeword layout (`skqd.codec`), which re-opens E1-E3 — not a re-ordering of the present
> one.  Qubit {C(f'{canary_rec}.incumbent.worst_qubit')} alone
> (T2 {C('S2_duration_compare:rescheduling_headroom.per_qubit.146.T2_s', '{:.1f}', US, US_NOTE)} us)
> carries {C('S2_duration_compare:rescheduling_headroom.per_qubit.146.S_T2', '{:.3f}')} of the
> {C('S2_duration_compare:rescheduling_headroom.S_T2_now', '{:.3f}')} S_T2 units, so patch selection on
> T2 is the larger lever and is covered by item 1.

Evidence: `reports/S2_duration_and_idle_2x2.md`, `data/S2_duration_compare.json`
(commit {C('S2_duration_compare:environment.git_commit')},
{C('S2_duration_compare:environment.timestamp')}, no QPU time).

### 4. OPEN — the 2x3 device

At the declared eps2 = {C('S2D:data.assumed_inputs.eps2_two_qubit_all_to_all', '{:g}')} the criterion is
missed by a factor of about two; a device with two-qubit error
{C('S2D:data.2x3.eps2_required_for_f_0.1', '{:.2e}')} or better satisfies it at the present gate counts
**on the gate-and-readout f alone**.  What today's measurement adds: that requirement
(`eps2 <= {C('S2D_idle:data.implication_2x3.eps2_of_the_sheet_at_S_idle_0', '{:.3e}')}`, which is the
row `S_idle = {C('S2D_idle:data.implication_2x3.rows.0.S_idle', '{:.3f}')}` of the table in section 2)
is **necessary but no longer sufficient**.  Under item 2 the requirement is
`n_2q eps2~ + n_1q eps1~ + n_meas eps_ro~ <= ln(1/f_target) - S_idle`
(`skqd.device_req.target_with_idle`), so a vendor must additionally declare

  * two-qubit and one-qubit **gate durations**,
  * **T1 and T2** per qubit (and which T2 convention),
  * whether the device **idles qubits serially** (a trapped-ion device that executes one gate at a time
    idles every other qubit for the whole circuit),

because without them S_idle, and hence f, cannot be computed at all.  **No S_idle is asserted here for a
device that has no schedule in this repository**; section 2 gives the requirement as a function of it.
Sources: `reports/S2D_2x3_device_requirements.md`, `src/skqd/device_req.py`
(`target_with_idle`), `validation/S2D_idle.json` -> `data.implication_2x3`.

### 5. OPEN — the shot quota of Step 9.2

The analysis and the recommendation are in `reports/S2D_shot_quota_decision_20260922.md` (section 3 of
this document is the arithmetic).  Its per-sector shot figures are computed at the gate-only 2x3 f and
scale as 1/f; they are not to be signed until the corrected, idle-aware f of item 2 is available for the
2x3 device (which requires item 4 first).

Until 4 and 5 are settled, gate S2D stays **{status}** and the 2x3 hardware claim of the plan is not
supported by measurement.  The 2x3 numbers can still be delivered from the certified emulation
(`validation/S1.json`) and from the S3 device-model simulation, whose cost is now measured:
{C('S2D:data.per_shot_cost_2x3.seconds_per_shot', '{:.2f}')} s per shot on this laptop CPU for one 20-qubit
coarse-step circuit in the RZZ basis
({C('S2D:data.per_shot_cost_2x3.shots_timed')} shots timed), i.e.
{C('S2D:data.per_shot_cost_2x3.desktop_job_hours_per_sector_this_cpu.B=0', '{:.3e}')} CPU-hours for one B = 0 sector
at the budget of section 3 -- a GPU job with batched shots (RTX 3070 desktop or the Slurm cluster), not a
laptop job.

## Provenance of every number above

{C.table()}

Generated by `scripts/make_amendment.py` from `validation/S2D.json`
(commit {C('S2D:environment.git_commit')}, {C('S2D:environment.timestamp')}), `validation/S2.json`,
`validation/S2D_idle.json` (commit {C('S2D_idle:environment.git_commit')}), `data/H0_patch_select.json`
and `data/S2_duration_compare.json` (commit {C('S2_duration_compare:environment.git_commit')})"""
    if has_l4:
        doc += f""" and `validation/L4_fez.json`
(commit {C('L4_fez:environment.git_commit')}, {C('L4_fez:environment.timestamp')})"""
    doc += ".\n"
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true", help="verify the existing file, write nothing")
    args = ap.parse_args()
    C = Cites()
    doc = build(C)
    if args.check_only:
        doc = open(OUT).read()
    else:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w") as fh:
            fh.write(doc)
    missing = C.verify(doc)
    n = len({(p, t) for p, v, t, note in C.items})
    if missing:
        print(f"MISMATCH: {len(missing)} cited values are not in the document:")
        for p, t in missing[:20]:
            print(f"  {p} -> '{t}'")
        return 1
    print(f"{OUT}: {n} distinct cited values, all verified against the JSON sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
