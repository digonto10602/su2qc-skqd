#!/usr/bin/env python3
"""
prompts/32 A.0.1 -- the 2x3 IBM Heron NO-GO, recorded as a model verdict on gate K0_2x3_2x4.

Reads `validation/K0_2x3_2x4.json` (every physics number) and, for the one pub-size parameter
of the garbage line, the K1 rehearsal preregistration (`shots_per_coarse_pub`).  Writes:

  data/K0_2x3_nogo.json              the block `k0_2x3_nogo` (copied verbatim into
                                     validation/H0_ddrep.json at assembly, prompts/32 A.F)
  reports/K0_2x3_ibm_heron_nogo.md   the generated note

No number is typed by hand; 0 QPU seconds.
"""
import glob
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

K0_JSON = os.path.join("validation", "K0_2x3_2x4.json")
K1_REHEARSAL_PREREG_GLOB = os.path.join("data", "K1_2x3_fpilot", "rehearsal_committed_record", "prep", "prereg_*.json")
OUT_JSON = os.path.join("data", "K0_2x3_nogo.json")
REPORT = "K0_2x3_ibm_heron_nogo.md"
CLOSING = ("Every number above is computed from the calibration record named; none is a measurement on the device.  "
           "Option B (prompts/32) is the one measurement this verdict allows: the K1 pilot as an upper limit.")
# fields copied verbatim from validation/K0_2x3_2x4.json (path inside data.2x3.<record>) -> block key
COPIED = {
    "record_label": ("record_label",),
    "record_fingerprint": ("record_fingerprint",),
    "record_last_update_date": ("record_last_update_date",),
    "circuit": ("circuit",),
    "routed_cz": ("n_cz",),
    "active_qubits": ("n_active_qubits",),
    "alap_duration_s": ("schedule", "scheduled_duration_s"),
    "f_ceiling_2q": ("f_ceiling_2q",),
    "eps2_min": ("eps2_min",),
    "f_gates_best_patch_bound": ("f_gates_best_patch_bound",),
    "f_gates_layout": ("f_gates_layout",),
    "S_idle_echo": ("idle", "echo", "S_idle"),
    "f_idle_aware_echo": ("idle", "echo", "f_idle_aware"),
    "t2_ratio_transferred": ("idle", "transferred_0.174", "t2_ratio"),
    "S_idle_transferred": ("idle", "transferred_0.174", "S_idle"),
    "f_idle_aware_transferred": ("idle", "transferred_0.174", "f_idle_aware"),
    "f_idle_aware_xy4_echo": ("idle", "echo", "f_idle_aware_xy4"),
    "f_idle_aware_xy4_echo_95": ("idle", "echo", "f_idle_aware_xy4_95"),
    "f_idle_aware_xy4_transferred": ("idle", "transferred_0.174", "f_idle_aware_xy4"),
    "f_idle_aware_xy4_transferred_95": ("idle", "transferred_0.174", "f_idle_aware_xy4_95"),
    "xy4_transfer": ("xy4_gain",),
    "eps2_needed_for_f_0.05": ("eps2_needed_for_f_0.05_nothing_else_wrong",),
    "best_edge_misses_by_factor": ("best_edge_misses_by_factor",),
    "verdict_flags": ("verdict",),
}


def load(path):
    with open(os.path.join(ROOT, path) if not os.path.isabs(path) else path) as fh:
        return json.load(fh)


def dig(d, path):
    for k in path:
        d = d[k]
    return d


def nogo_block(k0, shots):
    """The `k0_2x3_nogo` block from a K0 validation JSON (pure; tested)."""
    rec = k0["data"]["verdict_record"]
    x = k0["data"]["2x3"][rec]
    blk = {"source": K0_JSON, "k0_status": k0["status"], "verdict_record": rec,
           "record_path": k0["data"]["records"][rec]["path"]}
    for key, path in COPIED.items():
        blk[key] = dig(x, path)
    n = int(x["circuit"]["n_logical_qubits"])
    blk["garbage_reference_hits_per_circuit"] = {
        "shots": int(shots), "n_logical_qubits": n, "value": float(shots) * 2.0 ** (-n),
        "formula": "shots x 2^-n: the expected number of uniform-garbage strings equal to the circuit's reference string",
        "shots_source": "data/K1_2x3_fpilot/rehearsal_committed_record/prep/prereg_*.json shots_per_coarse_pub"}
    blk["verdict"] = ("NO-GO for 2x3 on IBM Heron (ibm_kingston) on the K0 analysis: a model verdict, not a measurement")
    blk["any_estimate_meets_worst_0.05"] = any(v.get("meets_worst_0.05") for v in x["verdict"].values())
    blk["closing"] = CLOSING
    return blk


def check_block(blk, k0):
    """D7 of prompts/32: every copied field equals K0's; the computed line recomputes."""
    rec = k0["data"]["verdict_record"]
    x = k0["data"]["2x3"][rec]
    bad = [key for key, path in COPIED.items() if blk.get(key) != dig(x, path)]
    g = blk.get("garbage_reference_hits_per_circuit") or {}
    if g.get("value") != float(g.get("shots", -1)) * 2.0 ** (-int(x["circuit"]["n_logical_qubits"])):
        bad.append("garbage_reference_hits_per_circuit")
    return bad


def k1_shots():
    fs = sorted(glob.glob(os.path.join(ROOT, K1_REHEARSAL_PREREG_GLOB)))
    if not fs:
        raise SystemExit("no K1 rehearsal preregistration found")
    return int(load(fs[-1])["shots_per_coarse_pub"]), os.path.relpath(fs[-1], ROOT)


def e(x, spec="{:.3e}"):
    return spec.format(x)


def main():
    from skqd.report import md_table, write_report
    k0 = load(K0_JSON)
    shots, spath = k1_shots()
    blk = nogo_block(k0, shots)
    blk["garbage_reference_hits_per_circuit"]["shots_source"] = spath + " shots_per_coarse_pub"
    blk["created"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    blk["script"] = "scripts/k0_nogo_note.py"
    blk["qpu_seconds"] = 0
    bad = check_block(blk, k0)
    if bad:
        raise SystemExit(f"block fields disagree with {K0_JSON}: {bad}")
    with open(os.path.join(ROOT, OUT_JSON), "w") as fh:
        json.dump(blk, fh, indent=1)
    xy = blk["xy4_transfer"]
    g = blk["garbage_reference_hits_per_circuit"]
    rows = [
        ["routed CZ (signed 2x3 k = 1 circuit, routed on ibm_kingston)", blk["routed_cz"]],
        ["active qubits", blk["active_qubits"]],
        ["ALAP duration", f"{blk['alap_duration_s'] * 1e6:.1f} us"],
        ["two-qubit-only ceiling f_ceiling_2q = (1 - eps2_min)^n_CZ", f"{e(blk['f_ceiling_2q'])} (eps2_min {e(blk['eps2_min'])})"],
        ["best-patch bound (best cz, best 1q, best readout everywhere)", e(blk["f_gates_best_patch_bound"])],
        ["f_gates on the routed layout", e(blk["f_gates_layout"])],
        ["S_idle / f_idle_aware, echo T2 (ratio 1)", f"{blk['S_idle_echo']:.2f} nats / {e(blk['f_idle_aware_echo'])}"],
        [f"S_idle / f_idle_aware, T2* (ratio {blk['t2_ratio_transferred']})",
         f"{blk['S_idle_transferred']:.2f} nats / {e(blk['f_idle_aware_transferred'])}"],
        [f"XY4 transfer (R = {xy['R']:.3f}, 95 % [{xy['R_95'][0]:.3f}, {xy['R_95'][1]:.3f}], {xy['source']}), echo end",
         f"{e(blk['f_idle_aware_xy4_echo'])} (95 % [{e(blk['f_idle_aware_xy4_echo_95'][0])}, {e(blk['f_idle_aware_xy4_echo_95'][1])}])"],
        ["XY4 transfer, T2* end",
         f"{e(blk['f_idle_aware_xy4_transferred'])} (95 % [{e(blk['f_idle_aware_xy4_transferred_95'][0])}, {e(blk['f_idle_aware_xy4_transferred_95'][1])}])"],
        ["eps2 needed for f = 0.05 with nothing else wrong", e(blk["eps2_needed_for_f_0.05"])],
        ["factor by which the best edge misses it", f"{blk['best_edge_misses_by_factor']:.3f}"],
        [f"garbage reference hits per circuit at {g['shots']} shots ({g['formula']})", f"{g['value']:.4f}"],
    ]
    vrows = [[k, v.get("meets_mean_0.1"), v.get("meets_worst_0.05")] for k, v in blk["verdict_flags"].items()]
    txt = f"""# 2x3 on IBM Heron: NO-GO on the K0 analysis (a model verdict, not a measurement)

Generated by `scripts/k0_nogo_note.py` from `{K0_JSON}` (gate K0_2x3_2x4, status **{blk['k0_status']}**) on {blk['created']};
the block is also in `{OUT_JSON}` and is copied verbatim into `validation/H0_ddrep.json` (prompts/32 A.0.1 / A.F).
Owner decision 2026-10-06 (`data/owner_decision_20261006_A_then_B.md`), option A.

Record: **{blk['verdict_record']}** = `{blk['record_path']}`, fingerprint `{blk['record_fingerprint']}`, last update
{blk['record_last_update_date']}.  Circuit: {blk['circuit']['id']} ({blk['circuit']['lattice']}, {blk['circuit']['n_logical_qubits']} logical qubits).

{md_table(["quantity", "value"], rows)}

Signed-bar flags of every estimate (mean f >= 0.1 / worst f >= 0.05):

{md_table(["estimate", "meets mean 0.1", "meets worst 0.05"], vrows)}

Verdict: {blk['verdict']}.

{CLOSING}
"""
    path = write_report(REPORT, txt)
    print(f"wrote {OUT_JSON} and {os.path.relpath(path, ROOT)}: f_gates_layout {e(blk['f_gates_layout'])}, "
          f"f_idle_aware echo {e(blk['f_idle_aware_echo'])}, garbage hits {g['value']:.4f} per circuit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
