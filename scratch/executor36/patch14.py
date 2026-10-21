import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "quantinuum_lattice_tests.py")
s = open(p).read()
a = s.index("SLOT_LAYOUT_2X4 = {      # prompts/36 R6")
b = s.index("def sample_aer(")
new = open(os.path.join(os.path.dirname(__file__), "slots_r14.py.txt")).read()
s = s[:a] + new + s[b:]
rep = [
    ('''    ap.add_argument("--provisional-s", type=float, default=None,
                    help="--tier slots-2x4: write the parts of the plan D3'-R x S to data/cv/2x4/provisional_parts_s<S>/ "
                         "(information when CV_2x4_plan has no final plan)")
''', ""),
    ('''SKQD_SLOTS = ("QV_2x4_02", "QV_2x4_03", "QV_2x4_04", "QV_2x4_05", "QV_2x4_06")''',
     '''SKQD_SLOTS = ("QV_2x4_02", "QV_2x4_03", "QV_2x4_04")      # prompts/36a R14: the k = 5 runs ride with their sector'''),
    # the segments cumulative check (36a R15 (iii)) and the dropped prefixes
    ('''        rec["segments"] = segments_of(seq, r)''',
     '''        rec["segments"] = segments_of(seq, r)
        rec["prefix_lengths_dropped"] = r.get("prefix_lengths_dropped", [])
        rec["segments_cumulative_check"] = segments_cumulative_check(rec["segments"], seq, r)'''),
    ('''    R.add("M measure_sampling true on every sampled run''',
     '''    seg_ok = all(v["segments_cumulative_check"] for v in samples)
    R.add("K0 the prefix segments rebuild the counts of the first L outcomes at every prefix L (prompts/36a R15 (iii))",
          {v["label"]: v["segments_cumulative_check"] for v in samples}, "all true", seg_ok)
    R.add("M measure_sampling true on every sampled run'''),
    ('''              "stop": {"K1": not k1, "measure_sampling": not all(v["measure_sampling"] for v in samples)},''',
     '''              "stop": {"K1": not k1, "measure_sampling": not all(v["measure_sampling"] for v in samples)},
              "segments_cumulative_check": bool(seg_ok),
              "prefix_lengths_dropped": {v["label"]: v["prefix_lengths_dropped"] for v in samples},'''),
    ('''def gpu_verify_36(args, slot, dry, device, avail, ci, t0):''',
     '''def segments_cumulative_check(segments, seq, run):
    """True iff, for every prefix length L of the run, the counts rebuilt from the segments ending at or before L equal
    np.unique of the first L outcomes."""
    for L in run.get("prefix_lengths", []):
        tot = {}
        for sg in segments:
            if sg["start"] + sg["shots"] <= int(L):
                for k, v in sg["counts"].items():
                    tot[int(k)] = tot.get(int(k), 0) + int(v)
        u, c = np.unique(seq[: int(L)], return_counts=True)
        if tot != {int(a): int(b) for a, b in zip(u, c)}:
            return False
    return True


def gpu_verify_36(args, slot, dry, device, avail, ci, t0):'''),
]
for a_, b_ in rep:
    assert a_ in s, a_[:80]
    s = s.replace(a_, b_)
open(p, "w").write(s)
print("ok")
