import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "quantinuum_lattice_tests.py")
s = open(p).read()
old = '''    from skqd.campaign33 import tokens as T
    t0 = time.time()
    fin = load_json(CV_PLAN_2X4)["data"]["plan"]["final"]
    gpu, k5 = fin["gpu"], fin["cv3_at_equal_shots"]
    irl0 = load_json(os.path.join(qpy_dir(4), "index.json"))["irl0"]'''
new = '''    from skqd.campaign33 import tokens as T
    t0 = time.time()
    out_dir, prov = PARTS_DIR, None
    if args.provisional_s is not None:            # information only: the parts a plan at s would give (never requested)
        import gate_CV as CV
        prov = float(args.provisional_s)
        prov = int(prov) if prov == int(prov) else prov
        gpu, k5 = provisional_plan_2x4(CV, prov)
        out_dir = os.path.join(CV.CV4_DIR, f"provisional_parts_s{prov:g}")
        os.makedirs(out_dir, exist_ok=True)
    else:
        fin = load_json(CV_PLAN_2X4)["data"]["plan"]["final"]
        if fin.get("resized_by") is None or not fin.get("gpu"):
            raise SystemExit("STOP: validation/CV_2x4_plan.json has no final plan (data.plan.final.resized_by is None: "
                             "prompts/36 section 9); ci/parts/QV_2x4_02..07.json are not written.  --provisional-s S writes "
                             "the parts of a plan at S to data/cv/2x4/provisional_parts_s<S>/ for information")
        gpu, k5 = fin["gpu"], fin["cv3_at_equal_shots"]
    irl0 = load_json(os.path.join(qpy_dir(4), "index.json"))["irl0"]'''
assert old in s
s = s.replace(old, new)
old = '''        with open(os.path.join(PARTS_DIR, slot + ".json"), "w") as fh:
            json.dump(part, fh, indent=1)'''
new = '''        if prov is not None:
            part["status"] = (f"PROVISIONAL (s = {prov:g}): validation/CV_2x4_plan.json STOPPED (no final plan); "
                              f"information only, never requested; was: {part['status']}")
            part["plan_source"] = f"data/cv/2x4/plan.json x s = {prov:g} (gate_CV.resized_shots), provisional"
        with open(os.path.join(out_dir, slot + ".json"), "w") as fh:
            json.dump(part, fh, indent=1)'''
assert old in s
s = s.replace(old, new)
old = '''def tier_slots_2x4(args):'''
new = '''def provisional_plan_2x4(CV, s):
    """(gpu, k5) of the plan D3'-R x s (s = 1: the plan itself), the R5 rule -- information when CV_2x4_plan STOPs."""
    nl = CV._stage_file("plan.json")["noiseless"]
    mans = CV.circuits_L(4)
    final = {}
    for sec in ("B=0", "B=1"):
        for c, v in nl[sec]["shots"].items():
            final[c] = int(v) if s == 1 else CV.resized_shots(int(v), s)
    n_eq = {}
    for tb in (0, 2):
        ids = [c for c in final if int(mans[c]["twoB"]) == tb]
        n_eq[tb] = int(math.ceil(sum(final[c] for c in ids) / len(ids) / 100.0) * 100)
    gpu, _U = CV.gpu_plan(final, mans, n_eq)
    _M, _codec, _acc, sectors = CV.sectors_L(4)
    return gpu, CV.k5_plan(sectors, n_eq)


def tier_slots_2x4(args):'''
assert old in s
s = s.replace(old, new)
old = '''    ap.add_argument("--note", default=None,'''
new = '''    ap.add_argument("--provisional-s", type=float, default=None,
                    help="--tier slots-2x4: write the parts of the plan D3'-R x S to data/cv/2x4/provisional_parts_s<S>/ "
                         "(information when CV_2x4_plan has no final plan)")
    ap.add_argument("--note", default=None,'''
assert old in s
s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
