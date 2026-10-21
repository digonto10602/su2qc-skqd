import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()

# ---- R12 corrected (addendum A1)
a = s.index("def bundles_corrected(a7):")
b = s.index("def write_owner_draft(D):")
new = '''RULE_R12_A1 = ("n_unitary_instructions = C + n_x(bundle) for every bundle and every k = 1..5, with C one constant common to "
               "all 75 bundles (the coarse-step body) and n_x the reference's preparation x gates, equal to the 1-bits of its "
               "codeword (prompts/36a addendum A1)")


def bundles_corrected(a7, M=None):
    """R12 as corrected by the prompts/36a addendum A1 (OD3): n_unitary = C + n_x(bundle), C one constant for all 75
    bundles; n_x(bundle) = the bundle's x instructions = n_x of the k = 1 bundle of the same reference = the popcount of
    the reference's codeword (Codec.encode).  If the popcount identity fails, `popcount_identity_holds` is false and the
    caller STOPs (no silent re-definition)."""
    from skqd.codec import Codec
    from skqd.reference_sim import bits_to_int
    if M is None:
        from skqd.exact import Model
        M = Model(4)
    codec = Codec(M.basis)
    idx = load_json(BUNDLE_INDEX_2X4)["irl0"]
    nx = {c: int(e["ops"].get("x", 0)) for c, e in idx.items()}
    nx_ir = {c: int(e["ir_counts"].get("x", 0)) for c, e in idx.items()}
    body = {c: int(e["n_unitary_instructions"]) - nx[c] for c, e in idx.items()}
    Cs = sorted(set(body.values()))
    by_ref, k1 = {}, {}
    for c, e in idx.items():
        key = f"2B={e['twoB']} ref {e['reference']}"
        by_ref.setdefault(key, set()).add(nx[c])
        if int(e["k"]) == 1:
            k1[key] = nx[c]
    popc = {}
    for c, e in idx.items():
        key = f"2B={e['twoB']} ref {e['reference']}"
        popc[key] = int(bin(bits_to_int(codec.encode(M.basis.labels[int(e["reference"])]))).count("1"))
    n_x_by_ref = {k: sorted(v) for k, v in sorted(by_ref.items())}
    pop_by_ref = dict(sorted(popc.items()))
    same_as_k1 = all(nx[c] == k1[f"2B={e['twoB']} ref {e['reference']}"] for c, e in idx.items())
    pop_ok = all(n_x_by_ref[k] == [pop_by_ref[k]] for k in n_x_by_ref)
    ok = bool(len(idx) == 75 and len(Cs) == 1 and same_as_k1 and pop_ok and nx == nx_ir)
    n_unit_by_ref = {}
    for e in idx.values():
        n_unit_by_ref.setdefault(f"2B={e['twoB']} ref {e['reference']}", set()).add(int(e["n_unitary_instructions"]))
    return {"rule_corrected": RULE_R12_A1, "C": Cs[0] if len(Cs) == 1 else Cs, "C_constant": len(Cs) == 1,
            "n_x_by_reference": n_x_by_ref, "popcount_by_reference": pop_by_ref, "popcount_identity_holds": bool(pop_ok),
            "n_x_equals_k1_bundle_of_reference": bool(same_as_k1), "n_x_bundle_ops_equals_ir_counts": nx == nx_ir,
            "rule_corrected_holds": ok,
            "rule_corrected_failures": sorted(c for c in idx if len(Cs) != 1 or not pop_ok) if not ok else [],
            "information_body_minus_prep_x": Cs, "information_body_constant": len(Cs) == 1,
            "information_n_unitary_by_reference": {k: sorted(v) for k, v in sorted(n_unit_by_ref.items())},
            "withdrawn": "R12 per sector (n_unit[twoB] from slot 01) -- withdrawn by the prompts/36a addendum A1",
            "ok_corrected": bool(ok and a7.get("within_cap") and a7.get("slot01_sources_ok") and a7.get("roundtrip_ok")
                                 and not a7.get("missing_or_bad_sha"))}


def d2_scratch_flags(cd):
    """prompts/36a addendum A2: the D2 comparison with the executor's scratch oracle_b1.json is information at 1e-5
    (`scratch_rH_reproduced_1e-5`, `rH_O_vs_scratch_abs_diff` per seed); the 1e-9 flag is removed.  Pure re-labelling
    of the recorded numbers (no recomputation)."""
    if not cd:
        return cd
    for r in cd["D2"].values():
        r.pop("oracle_rH_reproduced_1e-9", None)
        if "rH_O_oracle_b1_json" in r:
            r["rH_O_vs_scratch_abs_diff"] = abs(r["rH_O"] - r["rH_O_oracle_b1_json"])
            r["scratch_rH_reproduced_1e-5"] = bool(r["rH_O_vs_scratch_abs_diff"] <= 1e-5)
    cd.pop("oracle_rH_reproduced_1e-9", None)
    rows = [r for r in cd["D2"].values() if "scratch_rH_reproduced_1e-5" in r]
    cd["scratch_rH_reproduced_1e-5"] = (all(r["scratch_rH_reproduced_1e-5"] for r in rows) if rows else None)
    cd["scratch_check_rule"] = ("prompts/36a addendum A2: |r_H(O) - scratch| <= 1e-5 per seed, information only (never a "
                                "pass criterion); the gate-internal one-thread reproducibility (O_equals_one_thread_O) "
                                "is the real check")
    return cd


'''
s = s[:a] + new + s[b:]

# the cluster stage writes the new keys from now on
old = '''            row["oracle_rH_reproduced_1e-9"] = bool(abs(row["rH_O"] - row["rH_O_oracle_b1_json"]) <= 1e-9)'''
assert old in s
s = s.replace(old, '''            row["rH_O_vs_scratch_abs_diff"] = abs(row["rH_O"] - row["rH_O_oracle_b1_json"])
            row["scratch_rH_reproduced_1e-5"] = bool(row["rH_O_vs_scratch_abs_diff"] <= 1e-5)''')
old = '''                "oracle_rH_reproduced_1e-9": (all(r.get("oracle_rH_reproduced_1e-9", False) for r in rows.values())
                                              if oref else None)})'''
assert old in s
s = s.replace(old, '''                "scratch_rH_reproduced_1e-5": (all(r.get("scratch_rH_reproduced_1e-5", False) for r in rows.values())
                                               if oref else None)})''')

# assemble: the corrected rule with the model, the STOP on the popcount identity, the D2 relabelling
old = '''    a7.update(bundles_corrected(a7))'''
assert old in s
s = s.replace(old, '''    a7.update(bundles_corrected(a7, M))
    if not a7["popcount_identity_holds"]:
        stops.append("R12 (addendum A1): n_x(bundle) differs from the popcount of the reference codeword (STOP)")''')
old = '''    cp = os.path.join(CV4_DIR, "cluster_diag_B1.json")
    out["cluster_diag"] = load_json(cp) if os.path.exists(cp) else None'''
assert old in s
s = s.replace(old, '''    cp = os.path.join(CV4_DIR, "cluster_diag_B1.json")
    out["cluster_diag"] = d2_scratch_flags(load_json(cp)) if os.path.exists(cp) else None''')

# the draft: OD3 in the addendum's wording, numbers from the record
a = s.index('''             "OD3: UNSIGNED", "",''')
b = s.index('''             "OD4: UNSIGNED", "",''')
bd = "D['bundles']"
new_od3 = '''             "OD3: UNSIGNED", "",
             "  A7 corrected (prompts/36a addendum A1): n_unitary_instructions = C + n_x(bundle) for every bundle and every "
             f"k = 1..5, with C one constant common to all 75 bundles (the coarse-step body, {D['bundles']['C']} as computed: "
             "information_body_minus_prep_x) and n_x the reference's preparation x gates, equal to the 1-bits of its "
             f"codeword ({od3_nx_text(D['bundles'])}: information_n_unitary_by_reference "
             f"{' / '.join(str(x) for x in sorted({v for vs in D['bundles']['information_n_unitary_by_reference'].values() for v in vs}))}"
             "); replaces \\"k x 142288\\".  The per-sector wording of the first draft (\\"2B=0: 142288, 2B=2: 142289\\") was "
             "wrong and is withdrawn; rule_corrected_holds is re-evaluated by the gate under this wording (prompts/36a A3) "
             f"before the owner signs: rule_corrected_holds = {D['bundles']['rule_corrected_holds']}, n_x_by_reference == "
             f"popcount_by_reference: {D['bundles']['popcount_identity_holds']}.", "",
'''
s = s[:a] + new_od3 + s[b:]
old = '''def write_owner_draft(D):'''
new = '''def od3_nx_text(bd):
    """'4 for the Dirac-sea reference 102, 5 for the other fourteen references' rendered from n_x_by_reference."""
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 10: "ten", 13: "thirteen", 14: "fourteen"}
    by_n = {}
    for k, v in bd["n_x_by_reference"].items():
        by_n.setdefault(v[0], []).append(k.split(" ref ")[1])
    parts = []
    for n, refs in sorted(by_n.items(), key=lambda kv: len(kv[1])):
        if len(refs) == 1:
            parts.append(f"{n} for the Dirac-sea reference {refs[0]}" if refs[0] == "102" else f"{n} for reference {refs[0]}")
        else:
            parts.append(f"{n} for the other {words.get(len(refs), len(refs))} references")
    return ", ".join(parts)


def write_owner_draft(D):'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w").write(s)
print("ok")
