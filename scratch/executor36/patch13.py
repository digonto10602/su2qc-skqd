import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
blk = open(os.path.join(os.path.dirname(__file__), "block36a_assemble.py.txt")).read()
anchor = "\n\ndef assemble_2x4(seeds=SEEDS, quick=False):"
assert anchor in s and "def replan_36a" not in s
s = s.replace(anchor, blk.rstrip("\n") + "\n" + anchor, 1)

rep = [
    # a6_slots generalised
    ('''def a6_slots(final_gpu, k5, mans):
    """A6: the part files QV_2x4_02..07 against the plan, the bundles, the seed rule and the 2700 s budget."""''',
     '''def a6_slots(final_gpu, k5, mans, slots=None, parts_dir=None, r14=False):
    """A6: the part files QV_2x4_02..07 against the plan, the bundles, the seed rule and the 2700 s budget.  r14 (prompts/36a
    R14): slots 02..05, `fits` = predicted_s <= 2700 and the 1e-3 s/shot sum <= 3300 (the three-model prediction)."""'''),
    ('''    want = dict(final_gpu)
    want.update(k5)
    out, ok_all = {}, True
    for slot in SLOTS_2X4:
        p = os.path.join(QL.PARTS_DIR, slot + ".json")''',
     '''    want = dict(final_gpu)
    want.update(k5)
    out, ok_all = {}, True
    slots = SLOTS_2X4 if slots is None else slots
    parts_dir = QL.PARTS_DIR if parts_dir is None else parts_dir
    for slot in slots:
        p = os.path.join(parts_dir, slot + ".json")'''),
    ('''        if withheld:
            rec["ok"] = not bad and n_sample == 0
        else:''',
     '''        if withheld:
            rec["ok"] = not bad and n_sample == 0
        elif r14:
            for r in part.get("runs", []):
                if r.get("kind") == "native":
                    path = os.path.join(ROOT, r["qpy"])
                    if not os.path.exists(path) or sha256_file(path) != r["gz_sha256"]:
                        bad.append(f"{r['label']}: gz sha256")
            rec["mismatches"] = bad[:20]
            rec["ok"] = bool(not bad and pred and pred.get("fits") and float(pred["predicted_s"]) <= SLOT_BUDGET_S
                             and float(pred["predicted_s_slow_sampling"]) <= SLOW_BUDGET_S)
        else:'''),
    ('''    covered = sorted(r["base_id"] for slot in SLOTS_2X4
                     for r in (load_json(os.path.join(QL.PARTS_DIR, slot + ".json")).get("runs", [])
                               if os.path.exists(os.path.join(QL.PARTS_DIR, slot + ".json")) else [])
                     if r.get("kind") == "sample")''',
     '''    covered = sorted(r["base_id"] for slot in slots
                     for r in (load_json(os.path.join(parts_dir, slot + ".json")).get("runs", [])
                               if os.path.exists(os.path.join(parts_dir, slot + ".json")) else [])
                     if r.get("kind") == "sample")'''),
    ('''    return {"slots": out, "every_sampled_circuit_in_exactly_one_slot": cover_ok, "n_sampled_circuits": len(covered),''',
     '''    return {"slots": out, "parts_dir": rel(parts_dir), "every_sampled_circuit_in_exactly_one_slot": cover_ok,
            "n_sampled_circuits": len(covered),'''),
    # assemble: owner decision
    ('''    M, codec, _acc, sectors = sectors_L(4)
    mans = circuits_L(4)
    stops = []
    # ---- A1''',
     '''    M, codec, _acc, sectors = sectors_L(4)
    mans = circuits_L(4)
    stops = []
    od = owner_decision()                          # prompts/36a 3.6
    # ---- A1'''),
    ('''    cv3_ok = bool(chunks) and all(c["ok"] for d in cv3_by_seed.values() for c in d.values())
    if chunks and not cv3_ok:
        stops.append("CV3 (k = 4 -> 5 at equal shots) > E_tol in the emulation (prompts/36 A4: STOP, family question)")''',
     '''    cv3_ok = bool(chunks) and all(c["ok"] for d in cv3_by_seed.values() for c in d.values())'''),
    ('''    n_eq = {}
    for sec, tb in SECTORS:
        ids = sorted(c for c in final if int(mans[c]["twoB"]) == tb)
        if ids:
            n_eq[tb] = int(math.ceil(sum(final[c] for c in ids) / len(ids) / 100.0) * 100)
    gpu, U = gpu_plan(final, mans, n_eq) if final else ({}, {})
    k5 = k5_plan(sectors, n_eq) if final else {}
    final_ok = bool(s_final is not None and all(all(c[k]["ok"] for k in ("CV1", "CV2", "CV4", "CV5"))
                                                 for d in crit_final.values() for c in d.values()))''',
     '''    # ---- prompts/36a: the re-plan (information unless the owner signed OD1-OD4)
    rp = replan_36a(chunks, ladder, seeds, quick, mans, sectors, nl, crit1, E_tol)
    prop = rp["proposed"]
    od1, od2, od3, od4 = (od[k] == "SIGNED" for k in OD_ITEMS)
    if od1 and prop["complete"]:
        s_final = dict(prop["s_by_sector"])
        final = dict(prop["shots_by_circuit"])
        crit_final, cert = rp["criteria_by_seed_proposed"], rp["certificates_proposed"]
    elif complete and s_final is None and not od1:
        stops.append("re-sizing to s = 8 still fails CV1/CV2/CV4/CV5 (prompts/31 fix (g))")
    if od1 and not prop["complete"]:
        stops.append("re-sizing to s = 32 still fails at B=1 (prompts/36a R10)")
    cv3_read = "final" if od2 else "1x"
    cv3_ok_read = rp["cv3_final_ok"] if od2 else cv3_ok
    if chunks and not cv3_ok_read:
        stops.append(f"CV3 (k = 4 -> 5 at equal shots) > E_tol in the emulation at the {cv3_read} reading (prompts/36 A4 / "
                     f"36a R11: STOP, family question)")
    if not rp["e1"]["E1"]:
        stops.append("E1: the extended sequences do not reproduce the 8 N cache / the ladder (prompts/36a 3.1)")
    if not rp["E3"]:
        stops.append("E3: CV3 outside [-1e-9, its variational bound] (prompts/36a 3.3: a bug)")
    if not rp["gpu_cost_model"]["fit"]["rms_ok"]:
        stops.append("GPU cost fit rms > 10 s (prompts/36a section 4: the slots are re-cut by hand)")
    n_eq = {}
    for sec, tb in SECTORS:
        ids = sorted(c for c in final if int(mans[c]["twoB"]) == tb)
        if ids:
            n_eq[tb] = int(math.ceil(sum(final[c] for c in ids) / len(ids) / 100.0) * 100)
    if od4 and od1 and prop["complete"]:
        gpu, k5, U = prop["gpu"], prop["k5"], {0 if k == "B=0" else 2: v for k, v in prop["uniform_shots_by_sector"].items()}
    else:
        gpu, U = gpu_plan(final, mans, n_eq) if final else ({}, {})
        k5 = k5_plan(sectors, n_eq) if final else {}
    final_ok = bool(s_final is not None and all(all(c[k]["ok"] for k in ("CV1", "CV2", "CV4", "CV5"))
                                                 for d in crit_final.values() for c in d.values()))'''),
    ('''          "s in grid; CV3 ok", bool(complete and final_ok and cv3_ok))''',
     '''          "s in grid; CV3 ok", bool(complete and final_ok and cv3_ok_read))'''),
    ('''    a6 = a6_slots(gpu, k5, mans) if gpu else {"ok": False, "reason": "no final plan"}''',
     '''    if od4 and gpu:
        a6 = a6_slots(gpu, k5, mans, slots=SLOTS_R14, r14=True)
    else:
        a6 = a6_slots(gpu, k5, mans) if gpu else {"ok": False, "reason": "no final plan"}
    prov_dir = os.path.join(CV4_DIR, f"provisional_parts_s{rp['s_star_information']:g}") if rp["s_star_information"] else None
    a6p = (a6_slots(prop["gpu"], prop["k5"], mans, slots=SLOTS_R14, parts_dir=prov_dir, r14=True)
           if (prov_dir and prop["complete"] and os.path.isdir(prov_dir)) else {"ok": False, "slots": {},
                                                                                  "reason": "no provisional parts"})'''),
    ('''    a7 = a7_bundles(mans, {c: None for c in k5_ids_L(sectors)})''',
     '''    a7 = a7_bundles(mans, {c: None for c in k5_ids_L(sectors)})
    a7.update(bundles_corrected(a7))
    a7["rule_as_written_holds"] = a7["n_instructions_rule_holds"]
    a7["reading"] = "corrected (OD3 signed)" if od3 else "as written (OD3 unsigned)"
    a7_ok = a7["ok_corrected"] if od3 else a7["ok"]'''),
    ('''          "all hold", a7["ok"])''',
     '''          "all hold", a7_ok)'''),
    ('''    for s_ in SLOTS_2X4:
        p = os.path.join(ROOT, "validation", "dryrun", s_ + ".json")
        dry[s_] = load_json(p)["status"] if os.path.exists(p) else None''',
     '''    for s_ in SLOTS_R14:                          # the slot contents of prompts/36a R14
        p = os.path.join(ROOT, "validation", "dryrun", s_ + ".json")
        dj = load_json(p) if os.path.exists(p) else None
        dry[s_] = None if dj is None else (dj["status"] if dj["data"].get("segments_cumulative_check") is True
                                            else f"{dj['status']} (segments_cumulative_check missing)")'''),
    ('''          "criterion by criterion (in memory), the 2x3 / 2x2 records unchanged, dry runs QV_2x4_02..07 PASS",''',
     '''          "criterion by criterion (in memory), the 2x3 / 2x2 records unchanged, dry runs QV_2x4_02..05 (R14) PASS with "
          "segments_cumulative_check",'''),
    # data additions
    ('''        "cv3": {"ok": cv3_ok, "by_seed": cv3_by_seed},''',
     '''        "cv3": {"ok": cv3_ok_read, "ok_1x": cv3_ok, "ok_final": rp["cv3_final_ok"], "reading_point": cv3_read,
                "by_seed": cv3_by_seed, "readings": rp["cv3_readings"], "E3": rp["E3"],
                "final_file": rp["cv3_final_file"],
                "bound_rule": "0 <= CV3 <= E_R(k <= 4; N_eq) - E0 (variational; prompts/36a 1.2)"},
        "owner_decision": od, "replan_prompt": PROMPT_36A,
        "replan_36a": {k: v for k, v in rp.items() if k not in ("ext_ladder", "cv3_readings", "cluster_diag",
                                                                "gpu_cost_model")},
        "resize_ladder_reproduced": rp["e1"]["resize_ladder_reproduced"], "E1": rp["e1"]["E1"],
        "nested_prefix_identity_ok": rp["nested_prefix_identity_ok"], "E2": rp["e2"],
        "s_star_information": rp["s_star_information"], "s_star_detail": rp["s_star_detail"],
        "cluster_diag": rp["cluster_diag"], "gpu_cost_model": rp["gpu_cost_model"],
        "slots_provisional": a6p.get("slots", {}), "slots_provisional_check": {k: v for k, v in a6p.items() if k != "slots"},'''),
    ('''        "slots": (a6 or {}).get("slots", {}), "slots_check": {k: v for k, v in a6.items() if k != "slots"},''',
     '''        "slots": (a6p.get("slots") if not od4 else (a6 or {}).get("slots", {})),
        "slots_ci_parts_as_written": (a6 or {}).get("slots", {}),
        "slots_check": {k: v for k, v in a6.items() if k != "slots"},'''),
    ('''        "stop": {"fired": bool(stops), "conditions": stops,
                 "rule": "prompts/36 section 9: D3'-R infeasible, CV3 failure in the emulation, or re-sizing to 8 failing"},''',
     '''        "stop": {"fired": bool(stops), "conditions": stops,
                 "conditions_under_proposed_rules": proposed_conditions(rp),
                 "signed_set": {k: od[k] for k in OD_ITEMS},
                 "rule": ("prompts/36 section 9 under the signed set (prompts/36a 3.6): D3'-R infeasible, CV3 failure at "
                          "the signed reading point, re-sizing failing at the end of the signed grid (8, or 32 under OD1), "
                          "E1 / E3 failure, cost fit rms > 10 s")},'''),
]
for a, b in rep:
    assert a in s, a[:90]
    s = s.replace(a, b)

# the resize ladder: extended points (B=1 only) with beyond_signed_grid
old = '''                          for s_, v in ladder.items()},
        "curves":'''
new = '''                          for s_, v in ladder.items()} | {
            s_: {"B=1": dict(_ladder_summary(v["sectors"]["B=1"]), beyond_signed_grid=True,
                             extension_seed=v.get("extension_seed"))} for s_, v in rp["ext_ladder"].items()},
        "curves":'''
assert old in s
s = s.replace(old, new)

old = '''def assemble_2x4(seeds=SEEDS, quick=False):'''
new = '''def proposed_conditions(rp):
    """The STOP conditions that would hold if OD1-OD4 were signed (information; [] = none)."""
    c = []
    if rp["s_star_information"] is None:
        c.append("s = 32 still fails at B=1")
    if not rp["cv3_final_ok"]:
        c.append("CV3 > E_tol at the final N_eq")
    if not rp["E3"]:
        c.append("E3")
    if not rp["e1"]["E1"]:
        c.append("E1")
    if not rp["gpu_cost_model"]["fit"]["rms_ok"]:
        c.append("cost fit rms > 10 s")
    return c


def assemble_2x4(seeds=SEEDS, quick=False):'''
assert old in s
s = s.replace(old, new, 1)

# E_tol source and the owner draft
old = '''    R.data = data
    R.runtime_s = sum(ch["runtime_s"] for ch in chunks.values()) + time.time() - t0
    path = R.save()
    write_report(f"{gate}.md", report_2x4(R, data))'''
new = '''    for sec in data["E_tol"]:
        data["E_tol"][sec]["source"] = "stage etol"
    data["owner_decision"]["draft_written"] = write_owner_draft(data)
    R.data = data
    R.runtime_s = sum(ch["runtime_s"] for ch in chunks.values()) + time.time() - t0
    path = R.save()
    write_report(f"{gate}.md", report_2x4(R, data))'''
assert old in s
s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
