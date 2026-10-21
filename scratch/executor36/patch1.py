import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
p = os.path.join(ROOT, "scripts", "gate_CV.py")
s = open(p).read()
old1 = '''def sample_sequences(S, states, plan, mult, f_proxy, seed, codec, cw, tag):
    """{cid: int16 decoded index per shot (-1 rejected)} of mult x plan[c] shots, circuits in sorted
    order on one generator; cached in data/cv/<tag>.npz."""
    from skqd.noise import measure_and_decode_sequence

    ids = sorted(states)
    path = os.path.join(CV_DIR, tag + ".npz")
    want = {c: int(mult * plan[c]) for c in ids}
    if os.path.exists(path):
        z = np.load(path, allow_pickle=False)
        meta = json.loads(str(z["__meta__"]))
        if meta.get("want") == want and abs(meta.get("f_proxy", -1) - f_proxy) < 1e-15 and meta.get("seed") == seed:
            return {c: z[c] for c in ids}, {"cache": rel(path), "hit": True, "sampling_s": meta.get("sampling_s")}
    rng = np.random.default_rng(int(seed))
    t0 = time.time()
    seqs = {}
    for c in ids:
        dec, _why = measure_and_decode_sequence(codec, cw, states[c], want[c], f_proxy, P_RO, rng, S.twoB)
        seqs[c] = dec.astype(np.int16)
    dt = time.time() - t0
    os.makedirs(CV_DIR, exist_ok=True)
    meta = {"want": want, "f_proxy": f_proxy, "seed": int(seed), "p_ro": P_RO, "sampling_s": dt,
            "sector": S.sec, "rng": "numpy default_rng(seed), circuits in sorted id order"}'''
new1 = '''def sample_sequences(S, states, plan, mult, f_proxy, seed, codec, cw, tag, p_ro=P_RO, dtype=np.int16, cache_dir=CV_DIR):
    """{cid: decoded index per shot (-1 rejected)} of mult x plan[c] shots, circuits in sorted
    order on one generator; cached in <cache_dir>/<tag>.npz.  int16 at 2x3 (dim 1727); the 2x4 path passes
    int32 (dim 37165), p_ro = 0 and its own cache directory (prompts/36)."""
    from skqd.noise import measure_and_decode_sequence

    ids = sorted(states)
    path = os.path.join(cache_dir, tag + ".npz")
    want = {c: int(mult * plan[c]) for c in ids}
    if os.path.exists(path):
        z = np.load(path, allow_pickle=False)
        meta = json.loads(str(z["__meta__"]))
        if (meta.get("want") == want and abs(meta.get("f_proxy", -1) - f_proxy) < 1e-15 and meta.get("seed") == seed
                and meta.get("p_ro", P_RO) == p_ro):
            return {c: z[c] for c in ids}, {"cache": rel(path), "hit": True, "sampling_s": meta.get("sampling_s")}
    rng = np.random.default_rng(int(seed))
    t0 = time.time()
    seqs = {}
    for c in ids:
        dec, _why = measure_and_decode_sequence(codec, cw, states[c], want[c], f_proxy, p_ro, rng, S.twoB)
        seqs[c] = dec.astype(dtype)
    dt = time.time() - t0
    os.makedirs(cache_dir, exist_ok=True)
    meta = {"want": want, "f_proxy": f_proxy, "seed": int(seed), "p_ro": p_ro, "sampling_s": dt,
            "sector": S.sec, "rng": "numpy default_rng(seed), circuits in sorted id order"}'''
assert old1 in s
s = s.replace(old1, new1)
old2 = '''def sample_k_next(S, states_eq, eq_want, states_k5, k5_want, f_proxy, seed, codec, cw, cached_eq, tag):'''
new2 = '''def sample_k_next(S, states_eq, eq_want, states_k5, k5_want, f_proxy, seed, codec, cw, cached_eq, tag, p_ro=P_RO,
                  dtype=np.int16, cache_dir=CV_DIR):'''
assert old2 in s
s = s.replace(old2, new2)
seg_start = s.index(new2)
seg_end = s.index("def counts_of(")
seg = s[seg_start:seg_end]
seg2 = seg.replace('path = os.path.join(CV_DIR, tag + ".npz")', 'path = os.path.join(cache_dir, tag + ".npz")')
seg2 = seg2.replace('''        if meta.get("want") == want and abs(meta.get("f_proxy", -1) - f_proxy) < 1e-15 and meta.get("seed") == seed:''',
                    '''        if (meta.get("want") == want and abs(meta.get("f_proxy", -1) - f_proxy) < 1e-15 and meta.get("seed") == seed
                and meta.get("p_ro", P_RO) == p_ro):''')
seg2 = seg2.replace('''measure_and_decode_sequence(codec, cw, states_eq[c], int(eq_want[c]), f_proxy, P_RO, rng, S.twoB)
        replay_ok &= bool(np.array_equal(dec.astype(np.int16), cached_eq[c]))''',
                    '''measure_and_decode_sequence(codec, cw, states_eq[c], int(eq_want[c]), f_proxy, p_ro, rng, S.twoB)
        replay_ok &= bool(np.array_equal(dec.astype(dtype), cached_eq[c]))''')
seg2 = seg2.replace('''measure_and_decode_sequence(codec, cw, states_k5[c], want[c], f_proxy, P_RO, rng, S.twoB)
        seqs[c] = dec.astype(np.int16)''', '''measure_and_decode_sequence(codec, cw, states_k5[c], want[c], f_proxy, p_ro, rng, S.twoB)
        seqs[c] = dec.astype(dtype)''')
seg2 = seg2.replace('''    os.makedirs(CV_DIR, exist_ok=True)
    meta = {"want": want, "f_proxy": f_proxy, "seed": int(seed), "p_ro": P_RO, "sampling_s": dt, "sector": S.sec,''',
                    '''    os.makedirs(cache_dir, exist_ok=True)
    meta = {"want": want, "f_proxy": f_proxy, "seed": int(seed), "p_ro": p_ro, "sampling_s": dt, "sector": S.sec,''')
print(seg2.count("cache_dir"), "P_RO, rng" in seg2)
s = s.replace(seg, seg2)
old3 = '''def run_seed(S, states, plan_sec, f, seed, codec, cw, mans, E_tol, ckeep, states_k5=None, basis=BASIS_2X3):
    ids = sorted(states)
    kof = {c: int(mans[c]["k"]) for c in ids}
    f_proxy = MARGIN * f
    t0 = time.time()
    seqs, sinfo = sample_sequences(S, states, plan_sec, SAMPLE_MULT, f_proxy, seed, codec, cw,
                                   f"{S.sec.replace('=', '')}_{f:.2f}_{seed}")
    N_sec = int(sum(plan_sec.values()))
    N_eq = int(math.ceil(N_sec / len(ids) / 100.0) * 100)
    eq_plan = {c: N_eq for c in ids}
    seqs_eq, sinfo_eq = sample_sequences(S, states, eq_plan, 2, f_proxy, seed, codec, cw,
                                         f"{S.sec.replace('=', '')}_{f:.2f}_{seed}_eq")
    seqs_k5, sinfo_k5 = {}, None
    if states_k5:
        seqs_k5, sinfo_k5 = sample_k_next(S, states, {c: 2 * N_eq for c in ids}, states_k5,
                                          {c: 2 * N_eq for c in states_k5}, f_proxy, seed, codec, cw, seqs_eq,
                                          f"{S.sec.replace('=', '')}_{f:.2f}_{seed}_eq_k{K_NEXT}")'''
new3 = '''def run_seed(S, states, plan_sec, f, seed, codec, cw, mans, E_tol, ckeep, states_k5=None, basis=BASIS_2X3,
             f_proxy=None, p_ro=P_RO, dtype=np.int16, cache_dir=CV_DIR):
    """One (sector, f, seed) of the emulation.  The 2x3 call uses the defaults (f_proxy = MARGIN f, the S1 proxy
    readout P_RO, int16 sequences in data/cv); the 2x4 noiseless path (prompts/36 A4) passes f_proxy = 1, p_ro = 0,
    int32 and data/cv/2x4."""
    ids = sorted(states)
    kof = {c: int(mans[c]["k"]) for c in ids}
    f_proxy = MARGIN * f if f_proxy is None else float(f_proxy)
    skw = {"p_ro": p_ro, "dtype": dtype, "cache_dir": cache_dir}
    t0 = time.time()
    seqs, sinfo = sample_sequences(S, states, plan_sec, SAMPLE_MULT, f_proxy, seed, codec, cw,
                                   f"{S.sec.replace('=', '')}_{f:.2f}_{seed}", **skw)
    N_sec = int(sum(plan_sec.values()))
    N_eq = int(math.ceil(N_sec / len(ids) / 100.0) * 100)
    eq_plan = {c: N_eq for c in ids}
    seqs_eq, sinfo_eq = sample_sequences(S, states, eq_plan, 2, f_proxy, seed, codec, cw,
                                         f"{S.sec.replace('=', '')}_{f:.2f}_{seed}_eq", **skw)
    seqs_k5, sinfo_k5 = {}, None
    if states_k5:
        seqs_k5, sinfo_k5 = sample_k_next(S, states, {c: 2 * N_eq for c in ids}, states_k5,
                                          {c: 2 * N_eq for c in states_k5}, f_proxy, seed, codec, cw, seqs_eq,
                                          f"{S.sec.replace('=', '')}_{f:.2f}_{seed}_eq_k{K_NEXT}", **skw)'''
assert old3 in s
s = s.replace(old3, new3)
open(p, "w").write(s)
print("ok")
