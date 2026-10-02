#!/usr/bin/env python3
"""
Stage R of prompts/24 -- the full 2x2 SKQD circuit set on ibm_kingston
(`data/hardware/H0_2x2_prep/`): the signed family's 28 coarse-step circuits on the patch, with
the DD configuration Stage T adopted (or none), plus the patch's two readout pubs.  Zero QPU
seconds.  Runs below the signed f >= 0.1 budget by the owner's decision of 2026-10-02
(`data/owner_decision_20261002_run_below_signed_budget.md`).

The circuits are built by the SAME functions as Stage T (`h0_ddtest_circuits.build_coarse`,
`dd_variant`, `dd_checks`), so the adopted cell's pulses are inserted by the same code path
with the same checks (i)-(v).

Stages (default `--prep data/hardware/H0_2x2_prep`):
  account   as Stage T's (`--after` for the post-submission read)
  record    the day's full-device record, `calibration_diff` against Stage T's (information)
  select    R.A1: if the content of Stage T's patch is unchanged on the day's record, Stage T's
            patch is kept (P3); otherwise rule R1'-pilot is re-run and the report says so (D10)
  build     R.B1: the 28 circuits (+ adopted DD) and the two readout pubs
  patchcal  R.B2: the patch-scoped D9 record
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import h0_ddtest_circuits as DC  # noqa: E402
import h0_kpilot_circuits as KP  # noqa: E402

PREP = os.path.join("data", "hardware", "H0_2x2_prep")
T_PREP = DC.PREP
OWNER_DECISION = os.path.join("data", "owner_decision_20261002_run_below_signed_budget.md")
p, rel, load_json, dump_json, now = DC.p, DC.rel, DC.load_json, DC.dump_json, DC.now


def stage_t_record_path():
    info = load_json(p(T_PREP, "live.json"))
    return info["record"]["path"]


def family_ids():
    fam = load_json(p("data", "S2D_levers", "family.json"))["families"][KP.FAMILY_TAG]
    return [c["id"] for c in fam["circuits"]]


def adopted_cell(path=os.path.join("validation", "H0_ddtest.json")):
    d = load_json(p(path))
    if d.get("status") is None or "decision" not in d.get("data", {}):
        raise SystemExit(f"{path} carries no decision: Stage T is not assembled")
    return d["data"]["decision"]["adopted"], d


def stage_select(args):
    """R.A1 / P3: keep Stage T's patch when its calibration content is unchanged, else D10."""
    rec, info = DC.day_record(args.prep)
    tinfo = load_json(p(T_PREP, "live.json"))
    tpatch = load_json(tinfo["patch_record"]["path"])
    diffs = KP.leaves_equal(tpatch, rec)
    tsel = load_json(p(T_PREP, "select.json"))
    if not diffs:
        out = dict(tsel)
        out.update({"stage": "select", "created": now(),
                    "rule": ("P3 (prompts/24): Stage R uses Stage T's patch; the content of that patch on the day's "
                             "record is identical to Stage T's patch record, so the R1'-pilot search is not re-run"),
                    "inherited_from": rel(p(T_PREP, "select.json")),
                    "stage_T_patch_record": tinfo["patch_record"]["path"],
                    "stage_T_patch_fingerprint": tinfo["patch_record"]["fingerprint"],
                    "patch_content_unchanged": True, "patch_changed": False,
                    "record_path": info["record"]["path"], "record_fingerprint": rec["fingerprint"],
                    "stage_T_select_record_fingerprint": tsel["record_fingerprint"]})
        dump_json(out, p(args.prep, "select.json"))
        print(f"Stage T's patch content unchanged on {info['record']['path']}: patch {out['winner_patch']} kept "
              f"(mapping reproduced {out['mapping_reproduced']})")
        return 0
    print(f"the content of Stage T's patch moved ({len(diffs)} leaves, e.g. {diffs[:3]}): D10 -- R1'-pilot re-run")
    rc = DC.stage_select(args)
    sel = load_json(p(args.prep, "select.json"))
    sel.update({"patch_content_unchanged": False, "stage_T_patch": tsel["winner_patch"],
                "patch_changed": sel["winner_patch"] != tsel["winner_patch"],
                "stage_T_patch_leaf_differences": diffs[:50]})
    dump_json(sel, p(args.prep, "select.json"))
    print(f"patch changed vs Stage T: {sel['patch_changed']}")
    return rc


def stage_build(args):
    t0 = time.time()
    adopted, _d = adopted_cell(args.ddtest)
    rec, info, sel, base, binfo, mp, patch, cdir, n = DC.prepare_build(args.prep, args.force)
    common = DC.common_block(rec)
    common["circuit_family"] += f"; Stage T adopted cell {adopted} ({DC.CELL_DESCRIPTION[adopted]})"
    common["owner_decision"] = OWNER_DECISION
    ids = family_ids()
    reuse = None
    if adopted == "T0" and sel.get("pilot_mapping_reproduced"):
        reuse = {cid: os.path.join(DC.PILOT_PREP, "circuits", cid + ".qpy.gz")
                 for cid in ("B0_ref06_k1", "B1_ref07_k1", "B0_ref06_k4")}
    mans = DC.build_coarse(args.prep, rec, base, ids, (adopted,), cdir, common, sel, mp, patch,
                           force_reuse=reuse, id_suffix=False)
    mans += DC.build_calibration_pubs(base, rec, patch, n, cdir, common)
    extra = {"created": now(), "script": "scripts/h0_2x2_circuits.py", "stage": "build",
             "purpose": ("prompts/24 Stage R: the signed family's 28 coarse-step circuits on the patch with Stage T's "
                         "adopted DD configuration, plus the patch's readout pubs; the full 2x2 SKQD run below the "
                         "signed budget by the owner's decision"),
             "owner_decision": OWNER_DECISION, "adopted_cell": adopted,
             "adopted_cell_description": DC.CELL_DESCRIPTION[adopted],
             "common": common, "record": info["record"],
             "base_backend": {k: v for k, v in binfo.items() if k not in ("qubits", "edges")},
             "patch": patch, "winner_mapping": sel["winner_mapping"],
             "mapping_reproduced": sel["mapping_reproduced"],
             "pilot_mapping_reproduced": sel.get("pilot_mapping_reproduced"),
             "patch_inherited_from_stage_T": bool(sel.get("patch_content_unchanged")),
             "runtime_s": time.time() - t0}
    index, qubits, edges = DC.write_index(args.prep, mans, extra)
    print(f"wrote {len(mans)} circuits to {rel(cdir)} ({len(qubits)} qubits, {len(edges)} directed edges), adopted "
          f"cell {adopted}, in {time.time() - t0:.0f} s")
    return 0


def main():
    ap = DC.build_parser(default_prep=PREP, default_diff=None)
    ap.add_argument("--ddtest", default=os.path.join("validation", "H0_ddtest.json"))
    args = ap.parse_args()
    if args.stage == "record" and args.diff_against is None:
        args.diff_against = stage_t_record_path()
    if args.stage == "account" and args.min_remaining == DC.MIN_REMAINING_S:
        args.min_remaining = 0.0          # Stage R's STOP is the reserve check of gate_H0_2x2 --stage plan
    stages = {"account": DC.stage_account, "record": DC.stage_record, "select": stage_select,
              "build": stage_build, "patchcal": DC.stage_patchcal}
    return stages[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
