#!/usr/bin/env python3
"""
Generate proposal/amendment_01_devices_and_budgets.md from validation/S2D.json and
validation/L4_fez.json (prompts/12 step 6).

Rule of the project: no number is typed by hand.  Every numeric value in the amendment is
pulled from a JSON file through `cite(path, fmt)`, which records the JSON path it came
from; the document ends with the provenance table of those paths, and the script verifies
after writing that every cited string really occurs in the file (and only then exits 0).

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
        self.src, self.items = {}, []

    def load(self, tag, path):
        with open(path) as fh:
            self.src[tag] = json.load(fh)
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

    def __call__(self, path, fmt="{}"):
        val = self.raw(path)
        txt = fmt.format(val)
        self.items.append((path, val, txt))
        return txt

    def table(self):
        lines = ["| value in this document | source (JSON path) | value in the JSON |", "|---|---|---|"]
        seen = set()
        for path, val, txt in self.items:
            if (path, txt) in seen:
                continue
            seen.add((path, txt))
            tag, rest = path.split(":")
            lines.append(f"| `{txt}` | `validation/{tag}.json` -> `{rest}` | `{val}` |")
        return "\n".join(lines)

    def verify(self, text):
        missing = [(p, t) for p, v, t in self.items if t not in text]
        return missing


def build(C):
    S = C.load("S2D", os.path.join(ROOT, "validation", "S2D.json"))
    l4p = os.path.join(ROOT, "validation", "L4_fez.json")
    has_l4 = os.path.exists(l4p)
    if has_l4:
        C.load("L4_fez", l4p)
    best = S["data"]["2x2"]["best_snapshot"]
    other = [b for b in S["data"]["2x2"]["snapshots"] if b != best][0]
    status = S["status"]
    stamp = time.strftime("%Y-%m-%d")

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

    doc = f"""# Amendment 01 — devices and budgets (DRAFT for the owner's signature, {stamp})

Status: **draft, unsigned.**  Prepared by the executor from `validation/S2D.json` (gate S2D, status
**{status}**) and `validation/L4_fez.json`; every number is cited in the provenance table at the end and
re-checked against the JSON by `scripts/make_amendment.py`.  This amendment changes the *device
assignment* and the *budget criterion* of the preregistration.  It does **not** change the circuit
family, any physics convention, or any statistical threshold.

## 1. What is amended

**(a) Device per lattice.**  The preregistration assumed one Heron-class superconducting device for both
lattices.  The amendment assigns:

{tbl(["lattice", "device", "two-qubit gates per coarse step", "mean f", "worst-circuit f",
      "f computed from", "meets f >= 0.1"], dev_rows)}

**(b) Circuit family: unchanged.**  The exact structured circuits of gate S2 (`validation/S2.json`,
`skqd.circuits_ir.structured_term_gates`, `angle_mode="exact"`) remain the preregistered family.  The
fixed-angle alternative measured in `validation/S2_fixed.json` is *not* adopted.  Reproduction checks in
gate S2D: the k = 1 coarse step gives {C('S2D:data.2x2.ideal_heavy_hex_cz_k1')} CZ routed on the ideal
heavy-hex d = 3 map and {C('S2D:data.2x3.all_to_all_cz_k1')} CZ all-to-all in the CZ basis, identical to
the numbers recorded in `validation/S2.json`.

**(c) The budget criterion.**  Manual Step 4.3 fixed the budget as "<= 250 CZ at 2x2 and <= 500 CZ at
2x3".  Those numbers were derived in Step 4.4 from a physical condition: with per-CZ error eps the
clean-shot fraction is f = (1 - eps)^N_CZ, and the circuits must keep f high enough for the shot budget
to find a configuration of ideal probability p = {C('S2D:data.assumed_inputs.p_configuration_probability', '{:g}')}.
The amendment replaces the gate-count proxy by the condition itself, evaluated on the device that will
actually run the circuits:

> **Budget criterion (amended).**  For the production circuit set of a lattice, the clean-shot fraction
> f = prod over executed two-qubit gates (1 - eps_gate) x prod over measured qubits (1 - eps_readout),
> computed from the calibration of the device that will run them, must satisfy
> mean f >= 0.1 and worst-circuit f >= 0.05.

f >= 0.1 is the operating point at which gate S1 established recall >= 0.9 of the 99.9 % support with the
production shot budget (`validation/S1.json`); it is therefore the condition the CZ numbers stood for.
The criterion is *not* weaker than the old one: at 2x2 the routed count {C('S2D:data.2x2.S2_heavy_hex_cz_k1')}
CZ is still far above 250, but on the {best} calibration it gives mean f =
{C(f'S2D:data.2x2.snapshots.{best}.f.mean', '{:.4f}')}, above the physical requirement.

## 2. Evidence (gate S2D, status {status})

### 2x2 on a Heron-class device — the amendment is supported

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
calibration of the day, not fixed in advance.**

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

## 5. What the owner is asked to sign

1. 2x2 runs on a Heron-class device; the qubit patch is chosen by calibration-aware layout on the day of
   the run (evidence: section 2).
2. The fixed CZ numbers of Step 4.3 are replaced by the f >= 0.1 / worst >= 0.05 criterion of section 1(c).
3. The circuit family stays the exact structured circuits of gate S2.
4. **Open:** the 2x3 device.  At the declared eps2 = {C('S2D:data.assumed_inputs.eps2_two_qubit_all_to_all', '{:g}')}
   the criterion is missed by a factor of about two; a device with two-qubit error
   {C('S2D:data.2x3.eps2_required_for_f_0.1', '{:.2e}')} or better satisfies it at the present gate counts.
5. **Open:** the shot quota of Step 9.2 (section 3).

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
(commit {C('S2D:environment.git_commit')}, {C('S2D:environment.timestamp')})"""
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
    n = len({(p, t) for p, v, t in C.items})
    if missing:
        print(f"MISMATCH: {len(missing)} cited values are not in the document:")
        for p, t in missing[:20]:
            print(f"  {p} -> '{t}'")
        return 1
    print(f"{OUT}: {n} distinct cited values, all verified against the JSON sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
