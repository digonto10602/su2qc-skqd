#!/usr/bin/env python3
"""
Gate S2_2x4 -- the 2x4 coarse step compiled to exact basic-gate circuits, verified, and
measured: two-qubit counts (all-to-all and routed), depth, the ASAP-scheduled duration, the
per-qubit idle budget and the coherence requirement T2 / t_2q, on the same footing as the
2x2 and 2x3 rows the owner already has.

**PASS means compiled, verified, measured -- never affordable.**  The manual's Step 4.3
budget has no 2x4 line and none is invented here: this gate carries no criterion on any
count, duration or requirement value.  What it produces is the number that did not exist,
because the 2x4 circuits had never been compiled (prompts/22).

Staged for the 30-minute laptop rule.  Every stage writes a fragment to
`data/S2_2x4/<stage>_<tag>.json` and caches its synthesised IR and transpiled circuits in
`data/S2_2x4/cache/` (gitignored, regenerable); `--stage assemble` reads the fragments and
writes `validation/S2_2x4.json` and the report.  `python scripts/run_gate.py S2_2x4` runs
`--stage assemble`, so the runner and the CI see one command.

    python scripts/gate_S2_2x4.py --stage refs
    python scripts/gate_S2_2x4.py --stage structure --lattice 3
    python scripts/gate_S2_2x4.py --stage structure --lattice 4
    python scripts/gate_S2_2x4.py --stage synth --only hop0,...,plaq2 --thetas dt,2dt,4dt,dtB1
    python scripts/gate_S2_2x4.py --stage synth --only plaq1 --thetas dt        # one command
    python scripts/gate_S2_2x4.py --stage compile  [--lattice 2|3|4] [--maps ...]
    python scripts/gate_S2_2x4.py --stage schedule [--lattice 2|3|4] [--maps ...]
    python scripts/gate_S2_2x4.py --stage circuits [--lattice 2|3|4]
    python scripts/gate_S2_2x4.py --stage dense                 # the 2^28 hop1 cross-check
    python scripts/gate_S2_2x4.py --stage repro                 # criterion C9
    python scripts/gate_S2_2x4.py --stage qpy13 --lattice 4      # QPY v13 copy for qiskit 1.x
    python scripts/gate_S2_2x4.py --stage gpu --lattice 2 --device CPU   # laptop test of part F
    python scripts/gate_S2_2x4.py --stage assemble

Under the Perlmutter CI (`skqd.hpc.ci_context()` non-empty) the defaults become
`--stage gpu --device GPU --lattice 4 --gpu-jobs transpiled --then-assemble
--tests-from-record`: the GPU job of criterion C6, then the assemble that leaves a coherent
validation/S2_2x4.json for run_gate.py (C10 carried over from the committed laptop record).

No QPU time.  Nothing here edits an existing validation JSON, a criterion constant, a
convention or a decoder.
"""
import argparse
import gzip
import json
import math
import os
import pickle
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd import coherence as coh                                       # noqa: E402
from skqd import device_req as dr                                       # noqa: E402
from skqd import hpc                                                    # noqa: E402
from skqd import idle as sk_idle                                        # noqa: E402
from skqd.circuits_ir import (CircuitFactory, gate_counts, run_ir,      # noqa: E402
                              structured_term_gates, term_structure)
from skqd.exact import Model, mass_default                              # noqa: E402
from skqd.krylov import (basis_vector, coarse_states, references,       # noqa: E402
                         term_groups)
from skqd.reference_sim import CodewordEmbedding, localize, term_support  # noqa: E402
from skqd.report import (GateResult, _jsonable, env_block, environment,  # noqa: E402
                         md_table, write_report)
from skqd.sparse_sim import run_sparse, run_sparse_qiskit               # noqa: E402

G2 = 4.0
LEVEL = 3
SEED = 7
BASIS = ("rz", "sx", "x", "cz")
FRAG = os.path.join(ROOT, "data", "S2_2x4")
CACHE = os.path.join(FRAG, "cache")

# heavy-hex distance used for the "routed" column of each lattice: 3 at 2x2 and 5 at 2x3 are
# gate S2's maps (validation/S2.json heavy_hex_distance), so those rows are like-for-like.
HH = {2: 3, 3: 5, 4: 5}
MAP_NAMES = {2: ("all_to_all", "heavy_hex_3"),
             3: ("all_to_all", "heavy_hex_5", "fakefez"),
             4: ("all_to_all", "heavy_hex_5", "heavy_hex_7", "fakefez")}
# the four coarse-step circuits of the 2x4 measurement: (sector 2B, reference slot, k)
CIRCUITS_2x4 = ((0, 0, 1), (0, 0, 4), (0, 1, 1), (2, 0, 1))
F_TARGETS = (0.1, 0.05)
DECLARED = {"eps2": 1e-3, "eps1": 1e-4, "eps_ro": 2e-3}   # data/S2D_2x3_device_requirements.json

_MODELS = {}


# ==================================================================== small helpers
def model(lat: int) -> Model:
    if lat not in _MODELS:
        t = time.time()
        _MODELS[lat] = Model(lat)
        print(f"  Model({lat}) built in {time.time() - t:.1f} s "
              f"(dim {_MODELS[lat].basis.dim})", flush=True)
    return _MODELS[lat]


def e3_reference(lat: int, twoB: int) -> dict:
    with open(os.path.join(ROOT, "validation", "E3.json")) as fh:
        d = json.load(fh)["data"]["references"]
    return d[f"2x{lat}|g2={G2}|2B={twoB}"]


def dt_of(lat: int, twoB: int = 0) -> float:
    """The Krylov step of the sector, read from the COMMITTED gate-E3 record.

    Not recomputed from `Model(lat).reference(...)`: the sparse eigensolver is not bit-for-bit
    reproducible between processes (the 2x4 B = 0 dt came out 0.11469820342078253 in one run
    and ...293 in another, a drift of 4e-16), which would give the staged commands of this
    gate different angles and different IR cache keys.  `validation/E3.json` is the record,
    the model is checked against it to 1e-12 by criterion C1, and every theta this gate
    synthesises, transpiles, schedules and compares against `krylov.coarse_states` is this
    one number.
    """
    return float(e3_reference(lat, twoB)["dt"])


def theta_table(lat: int) -> dict:
    dt0 = dt_of(lat, 0)
    out = {"dt": dt0, "2dt": 2 * dt0, "4dt": 4 * dt0}
    try:
        out["dtB1"] = dt_of(lat, 2)
    except KeyError as exc:                                      # pragma: no cover
        print(f"  no B=1 reference at 2x{lat} in validation/E3.json: {exc}")
    return out


def term_names(lat: int) -> list:
    M = model(lat)
    return ([f"hop{l}" for l in range(M.lat.n_links)]
            + [f"plaq{P}" for P in range(len(M.lat.plaquettes))])


def term_operator(lat: int, name: str):
    """(O, support) of a hop/plaq term -- exactly what gate_S2.py verifies against."""
    M = model(lat)
    if name.startswith("hop"):
        l = int(name[3:])
        return M.terms.hop[l], term_support(M, "hop", l)
    P = int(name[4:])
    return -M.terms.plaq[P] / (2 * G2), term_support(M, "plaq", P)


def nvec_for(k: int) -> int:
    """Gate S2's random-vector counts, extended to the 16-qubit support of 2x4 plaq1
    (where one vector costs about 57 s per theta)."""
    if k <= 10:
        return 20
    if k <= 14:
        return 5
    return 3


def frag_path(name: str) -> str:
    os.makedirs(FRAG, exist_ok=True)
    return os.path.join(FRAG, f"{name}.json")


def write_frag(name: str, payload: dict):
    payload = dict(payload)
    payload.setdefault("created", time.strftime("%Y-%m-%d %H:%M:%S %Z"))
    payload.setdefault("environment", environment())
    p = frag_path(name)
    with open(p, "w") as fh:
        json.dump(_jsonable(payload), fh, indent=1)
    print(f"wrote {os.path.relpath(p, ROOT)}", flush=True)
    return p


def read_frags(prefix: str) -> dict:
    import glob as _glob
    out = {}
    for p in sorted(_glob.glob(os.path.join(FRAG, f"{prefix}*.json"))):
        with open(p) as fh:
            out[os.path.basename(p)[:-5]] = json.load(fh)
    return out


def mem_available_gb() -> float:
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return float(line.split()[1]) / (1024.0 * 1024.0)
    except Exception:                                            # pragma: no cover
        pass
    return float("nan")


# ==================================================================== IR cache
def _ir_cache(lat, name, mode, theta):
    os.makedirs(CACHE, exist_ok=True)
    tag = f"{theta:.17g}".replace("-", "m").replace(".", "p")
    return os.path.join(CACHE, f"ir_{lat}_{name}_{mode}_{tag}.pkl.gz")


def term_ir(lat: int, name: str, mode: str, theta: float, force: bool = False):
    """(gates, stats, synthesis seconds, from_cache) of one structured term gate.

    The IR is cached on disk so that the staged commands of this gate never resynthesise the
    16-qubit `plaq1` (152 s) more than once per (term, mode, theta)."""
    p = _ir_cache(lat, name, mode, theta)
    if os.path.exists(p) and not force:
        with gzip.open(p, "rb") as fh:
            d = pickle.load(fh)
        return d["gates"], d["stats"], d["synth_s"], True
    M = model(lat)
    O, sup = term_operator(lat, name)
    st = []
    t0 = time.time()
    gates = structured_term_gates(M, O, sup, theta, stats=st, angle_mode=mode)
    dt = time.time() - t0
    with gzip.open(p, "wb", compresslevel=1) as fh:
        pickle.dump({"gates": gates, "stats": st, "synth_s": dt, "lattice": lat,
                     "term": name, "mode": mode, "theta": theta}, fh)
    return gates, st, dt, False


def diag_ir(lat: int, theta: float) -> list:
    M = model(lat)
    return CircuitFactory(M, G2).diag_gates(theta)


def preload_factory(lat: int, mode: str, thetas) -> CircuitFactory:
    """A CircuitFactory whose structured-term cache is filled from the disk cache.

    `CircuitFactory._structured` memoises on (term name, round(theta, 12), angle_mode); the
    gate fills that memo from `term_ir` so that assembling a coarse step costs no synthesis.
    Nothing about the gate lists changes: they are the same objects `structured_term_gates`
    returned and cached."""
    M = model(lat)
    F = CircuitFactory(M, G2, angle_mode=mode)
    for name in term_names(lat):
        for th in thetas:
            if not os.path.exists(_ir_cache(lat, name, mode, th)):
                print(f"  (IR cache miss: synthesising 2x{lat} {name} {mode} at "
                      f"theta = {th:.17g} -- this is 152 s for the 16-qubit plaq1)",
                      flush=True)
            gates, st, _s, _c = term_ir(lat, name, mode, th)
            F._struct_cache[(name, round(th, 12), mode)] = gates
            F.fixed_stats[(name, round(th, 12))] = st
    return F


# ==================================================================== verification
def verify_term(lat: int, name: str, gates: list, theta: float, nvec: int, rng) -> dict:
    """max |circuit - exp(-i theta h)| and the leakage, on random vectors of the LOCAL
    codeword space -- exactly `gate_S2.term_deviation` / `term_leakage_and_deviation`.

    The dense local unitary is never built: the exact exponential comes from the small block
    `h` of `reference_sim.localize` (1831 x 1831 for the 16-qubit 2x4 plaq1) and the circuit
    runs on the 2^k local statevector (1 MB at k = 16)."""
    import scipy.linalg as sla

    M = model(lat)
    O, sup = term_operator(lat, name)
    k = len(sup)
    states, h, _pos = localize(M, O, sup)
    idx = np.array(states)
    pos = {q: i for i, q in enumerate(sup)}
    loc = [(nm, [pos[q] for q in qs], par) for nm, qs, par in gates]
    U = sla.expm(-1j * theta * h)
    dev, leak = 0.0, 0.0
    t0 = time.time()
    for _ in range(nvec):
        c = rng.normal(size=len(states)) + 1j * rng.normal(size=len(states))
        c = c / np.linalg.norm(c)
        psi = np.zeros(2 ** k, dtype=complex)
        psi[idx] = c
        out = run_ir(loc, k, psi)
        leak = max(leak, abs(1.0 - float(np.sum(np.abs(out[idx]) ** 2))))
        ex = np.zeros(2 ** k, dtype=complex)
        ex[idx] = U @ c
        dev = max(dev, float(np.abs(out - ex).max()))
    return {"max_deviation": dev, "leakage": leak, "n_vectors": int(nvec),
            "verify_s": time.time() - t0, "support": k, "local_states": int(len(states))}


# ==================================================================== transpilation
def coupling_map(name: str):
    from qiskit.transpiler import CouplingMap
    if name in ("all_to_all", "fakefez_backend"):
        return None
    if name.startswith("heavy_hex_"):
        return CouplingMap.from_heavy_hex(int(name.split("_")[-1]))
    if name == "fakefez":
        from qiskit_ibm_runtime.fake_provider import FakeFez
        return FakeFez().coupling_map
    raise SystemExit(f"unknown coupling map '{name}'")


def cz_depth(tq) -> int:
    """Number of CZ LAYERS in the circuit DAG -- `s2_duration_compare.cz_depth`."""
    return int(tq.depth(filter_function=lambda i: i.operation.name == "cz"))


def _tq_cache(lat, mode, tag, mapname, measure):
    """The transpiled-circuit cache key.  `mode` (the angle mode) is part of it: the exact and
    the fixed-angle families are different circuits on the same (lattice, circuit, map)."""
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, f"tq_{lat}_{mode}_{tag}_{mapname}_"
                               f"{'m' if measure else 'nm'}.qpy.gz")


def transpile_ir(gates: list, n: int, mapname: str, measure: bool):
    """The transpilation of `skqd.circuits_qiskit.transpile_counts` (basis {rz, sx, x, cz},
    optimization level 3, seed 7), returning the circuit so that depth, CZ depth and the
    schedule can all be read off the same object."""
    from qiskit import transpile

    from skqd import circuits_qiskit as cq
    qc = cq.ir_to_qiskit(gates, n, measure=measure)
    t0 = time.time()
    if mapname == "fakefez_backend":
        # the calibration-AWARE layout: the transpiler is given the backend, so it avoids the
        # edges whose snapshot cz error is 1.0 (the coupling-map-only route does not know
        # about them).  This is the circuit `scripts/h0_build_circuits.py` would submit.
        from qiskit_ibm_runtime.fake_provider import FakeFez
        tq = transpile(qc, backend=FakeFez(), optimization_level=LEVEL, seed_transpiler=SEED)
    else:
        tq = transpile(qc, basis_gates=list(BASIS), coupling_map=coupling_map(mapname),
                       optimization_level=LEVEL, seed_transpiler=SEED)
    return tq, time.time() - t0


def load_tq(lat, mode, tag, mapname, measure):
    p = _tq_cache(lat, mode, tag, mapname, measure)
    if not os.path.exists(p):
        return None
    from qiskit import qpy
    with gzip.open(p, "rb") as fh:
        return qpy.load(fh)[0]


def save_tq(tq, lat, mode, tag, mapname, measure):
    from qiskit import qpy
    with gzip.open(_tq_cache(lat, mode, tag, mapname, measure), "wb", compresslevel=6) as fh:
        qpy.dump(tq, fh)


def circuit_counts(tq, transpile_s=None) -> dict:
    ops = {k: int(v) for k, v in tq.count_ops().items()}
    return {"ops": ops, "n_2q": int(ops.get("cz", 0)),
            "n_1q": int(sum(v for k, v in ops.items() if k in ("sx", "x", "rz"))),
            "n_rz": int(ops.get("rz", 0)), "n_sx": int(ops.get("sx", 0)),
            "n_x": int(ops.get("x", 0)), "n_measure": int(ops.get("measure", 0)),
            "depth": int(tq.depth()), "cz_depth": cz_depth(tq),
            "n_qubits_mapped": int(tq.num_qubits),
            "n_active_qubits": len({tq.find_bit(q).index for inst in tq.data
                                    for q in inst.qubits if inst.operation.name != "barrier"}),
            "transpile_s": transpile_s}


# ==================================================================== stages
def stage_refs(args) -> dict:
    """B1 -- the E3 link: dt and the sector dimensions of the model equal the gate-E3 record."""
    lat = args.lattice
    M = model(lat)
    out = {"stage": "refs", "lattice": lat, "sectors": {}}
    for twoB in (0, 2):
        ref = M.reference(G2, twoB)
        e3 = e3_reference(lat, twoB)
        nref = len(references(M.basis, twoB))
        out["sectors"][str(twoB)] = {
            "dt_model": float(ref.dt), "dt_E3": float(e3["dt"]),
            "dt_abs_difference": abs(float(ref.dt) - float(e3["dt"])),
            "dim_model": int(ref.dim),
            "dim_E3": int(e3["dim"]), "n_references": int(nref),
            "W_model": float(ref.W), "W_E3": float(e3["W"]),
            "E0_model": float(ref.energies[0]), "E0_E3": float(e3["energies"][0]),
        }
    out["basis_dim_total"] = int(M.basis.dim)
    out["n_qubits"] = int(CodewordEmbedding(M).n)
    out["codec_widths"] = [int(w) for w in CodewordEmbedding(M).codec.widths]
    out["n_codewords"] = int(CodewordEmbedding(M).ints.size)
    out["links"] = [[int(a), int(b), c] for a, b, c in M.lat.links]
    out["n_plaquettes"] = int(len(M.lat.plaquettes))
    return out


def stage_structure(args) -> dict:
    """B2 -- the P1 table and the P2 disjointness/colouring, from supports alone."""
    lat = args.lattice
    M = model(lat)
    names = term_names(lat)
    rows, sup = {}, {}
    for name in names:
        t0 = time.time()
        O, s = term_operator(lat, name)
        r = term_structure(M, O, s)
        r["localize_s"] = time.time() - t0
        rows[name] = r
        sup[name] = set(s)
        print(f"  {name}: support {r['support']}, {r['local_states']} local states, "
              f"{r['blocks']} blocks, largest {r['largest_block']}, "
              f"{r['localize_s']:.1f} s", flush=True)
    sup_diag = set(term_support(M, "diag", 0))

    def disjoint_pairs(keys, extra=None):
        s = dict(sup)
        if extra:
            s.update(extra)
        ks = sorted(keys)
        pairs = [[a, b] for i, a in enumerate(ks) for b in ks[i + 1:] if not s[a] & s[b]]
        return pairs, len(ks) * (len(ks) - 1) // 2

    dj, npairs = disjoint_pairs(names)
    dj_all, npairs_all = disjoint_pairs(names + ["diag"], {"diag": sup_diag})
    # exact chromatic number of the term-overlap graph by backtracking (13 nodes at 2x4)
    adj = {a: {b for b in names if b != a and (sup[a] & sup[b])} for a in names}
    order = sorted(names, key=lambda a: -len(adj[a]))

    def colourable(kmax):
        col = {}

        def bt(i):
            if i == len(order):
                return True
            a = order[i]
            used = {col[b] for b in adj[a] if b in col}
            for c in range(min(kmax, i + 1)):
                if c in used:
                    continue
                col[a] = c
                if bt(i + 1):
                    return True
                del col[a]
            return False
        return (col if bt(0) else None)

    chrom, colouring = None, None
    for kmax in range(1, len(names) + 1):
        c = colourable(kmax)
        if c is not None:
            chrom, colouring = kmax, c
            break
    return {"stage": "structure", "lattice": lat, "terms": rows,
            "support_sizes": {k: int(len(v)) for k, v in sup.items()},
            "diag_support": int(len(sup_diag)),
            "n_terms_hop_plaq": len(names), "n_pairs": npairs,
            "n_disjoint_pairs": len(dj), "disjoint_pairs": dj,
            "disjoint_fraction": len(dj) / npairs if npairs else None,
            "n_pairs_including_diag": npairs_all,
            "n_disjoint_pairs_including_diag": len(dj_all),
            "chromatic_number_overlap_graph": chrom,
            "colouring": colouring, "serial_rounds": len(names),
            "diag_nonzero_any": any(r["diag_nonzero"] for r in rows.values())}


def stage_synth(args) -> dict:
    """B3 -- synthesise and verify the term gates, cache the IR, record cost and stats."""
    lat, mode = args.lattice, args.angle_mode
    ths = theta_table(lat)
    labels = [t for t in args.thetas.split(",") if t]
    for t in labels:
        if t not in ths:
            raise SystemExit(f"unknown theta label '{t}' (have {sorted(ths)})")
    only = [t for t in (args.only.split(",") if args.only else term_names(lat)) if t]
    rng = np.random.default_rng(args.seed)
    out = {"stage": "synth", "lattice": lat, "angle_mode": mode,
           "thetas": {t: ths[t] for t in labels}, "terms": {}}
    for name in only:
        rec = {"per_theta": {}}
        for tl in labels:
            th = ths[tl]
            gates, st, synth_s, cached = term_ir(lat, name, mode, th, force=args.force)
            k = len(term_operator(lat, name)[1])
            nv = args.nvec if args.nvec else nvec_for(k)
            v = verify_term(lat, name, gates, th, nv, rng) if not args.no_verify else {}
            ctrl = sorted(int(x["n_controls"]) for x in st)
            hist = {}
            for c in ctrl:
                hist[str(c)] = hist.get(str(c), 0) + 1
            rec["per_theta"][tl] = {
                "theta": th, "ir_gates": len(gates), "counts": gate_counts(gates),
                "n_multiplexed_rotations": len(st),
                "controls_min": min(ctrl) if ctrl else None,
                "controls_median": int(np.median(ctrl)) if ctrl else None,
                "controls_max": max(ctrl) if ctrl else None,
                "controls_histogram": hist,
                "frame_cnots": int(sum(int(x["frame_cnots"]) for x in st)),
                "real_gauge_found": bool(all(x.get("real_gauge_found", False) for x in st)) if st
                else None,
                "block_rounds_fallback": bool(any(x.get("block_rounds_fallback", False)
                                                  for x in st)),
                "synthesis_s": synth_s, "from_cache": cached, **v}
            g = rec["per_theta"][tl]
            print(f"  {name} {mode} theta={tl}: {len(gates)} IR gates "
                  f"({g['counts'].get('cx', 0)} cx), {len(st)} rotations, "
                  f"dev {g.get('max_deviation', float('nan')):.2e}, "
                  f"leak {g.get('leakage', float('nan')):.2e}, "
                  f"synth {synth_s:.0f} s, verify {g.get('verify_s', 0.0):.0f} s", flush=True)
        rec["cx"] = rec["per_theta"][labels[0]]["counts"].get("cx", 0)
        rec["support"] = len(term_operator(lat, name)[1])
        for tl in labels:
            rec["per_theta"][tl].setdefault("support", rec["support"])
        out["terms"][name] = rec
    return out


def coarse_step_ir(lat: int, mode: str, twoB: int, slot: int, k: int):
    """(gates, dt, reference index) of one coarse-step circuit, from the IR cache."""
    M = model(lat)
    dt = dt_of(lat, twoB)
    F = preload_factory(lat, mode, [k * dt])
    ref = references(M.basis, twoB)[slot]
    return F.coarse_step(ref, k, dt), dt, int(ref)


def circuit_tag(twoB, slot, k):
    return f"B{twoB // 2}_ref{slot}_k{k}"


def select_circuits(lat: int, args) -> list:
    """The coarse-step circuits a stage acts on: the four of the 2x4 measurement (or the one
    k = 1 B = 0 circuit at 2x2/2x3), filtered by `--circuits`."""
    grid = list(CIRCUITS_2x4) if lat == 4 else [(0, 0, 1)]
    want = getattr(args, "circuits", None)
    if want:
        keep = {w for w in want.split(",") if w}
        grid = [c for c in grid if circuit_tag(*c) in keep]
        if not grid:
            raise SystemExit(f"--circuits {want} selects none of "
                             f"{[circuit_tag(*c) for c in grid or CIRCUITS_2x4]}")
    return grid


def stage_compile(args) -> dict:
    """B4 -- transpile the coarse steps and the term gates on every map; record the counts."""
    lat, mode = args.lattice, args.angle_mode
    maps = [m for m in (args.maps.split(",") if args.maps else MAP_NAMES[lat]) if m]
    M = model(lat)
    n = CodewordEmbedding(M).n
    ths = theta_table(lat)
    out = {"stage": "compile", "lattice": lat, "angle_mode": mode, "maps": maps,
           "n_qubits": int(n), "optimization_level": LEVEL, "seed_transpiler": SEED,
           "basis_gates": list(BASIS), "circuits": {}, "per_term": {}}
    grid = select_circuits(lat, args)
    meas = tuple(bool(int(x)) for x in args.measure.split(",") if x != "")
    for (twoB, slot, k) in grid:
        tag = circuit_tag(twoB, slot, k)
        gates, dt, ref = coarse_step_ir(lat, mode, twoB, slot, k)
        entry = {"reference_index": ref, "reference_slot": slot, "twoB": twoB, "k": k,
                 "dt": dt, "theta": k * dt, "ir_gates": len(gates),
                 "ir_gate_counts": gate_counts(gates), "maps": {}}
        for mp in maps:
            for measure in meas:
                tq = load_tq(lat, mode, tag, mp, measure)
                ts = None
                if tq is None:
                    tq, ts = transpile_ir(gates, n, mp, measure)
                    save_tq(tq, lat, mode, tag, mp, measure)
                key = mp if not measure else f"{mp}|measured"
                entry["maps"][key] = circuit_counts(tq, ts)
                print(f"  2x{lat} {mode} {tag} {key}: {entry['maps'][key]['n_2q']} CZ, "
                      f"depth {entry['maps'][key]['depth']}, "
                      f"cz_depth {entry['maps'][key]['cz_depth']}"
                      + (f", {ts:.1f} s" if ts else " (cached)"), flush=True)
        out["circuits"][tag] = entry
    if not args.no_per_term:
        only = [t for t in (args.only.split(",") if args.only else
                            ["diag"] + term_names(lat)) if t]
        for name in only:
            g = diag_ir(lat, ths["dt"]) if name == "diag" else term_ir(lat, name, mode,
                                                                       ths["dt"])[0]
            rec = {"ir_gates": len(g), "maps": {}}
            for mp in maps:
                tq, ts = transpile_ir(g, n, mp, False)
                rec["maps"][mp] = {"n_2q": int(tq.count_ops().get("cz", 0)),
                                   "depth": int(tq.depth()), "cz_depth": cz_depth(tq),
                                   "transpile_s": ts}
            out["per_term"][name] = rec
            print(f"  term {name}: " + ", ".join(
                f"{mp} {rec['maps'][mp]['n_2q']} CZ" for mp in maps), flush=True)
        out["per_term_cz_sum"] = {mp: int(sum(r["maps"][mp]["n_2q"]
                                              for r in out["per_term"].values()))
                                  for mp in maps}
    # structure identity: are the term-gate IR counts and the transpiled n_2q the same
    # across the k and the references of a sector?  (At 2x3 they were: 2158 RZZ on all 44.)
    ident = {}
    for mp in maps:
        vals = {t: c["maps"][mp]["n_2q"] for t, c in out["circuits"].items() if mp in c["maps"]}
        same_k1 = {t: v for t, v in vals.items() if t.endswith("k1")}
        ident[mp] = {"per_circuit_n_2q": vals,
                     "identical_across_references_at_k1": len(set(same_k1.values())) <= 1,
                     "identical_across_all": len(set(vals.values())) <= 1}
    out["structure_identity"] = ident
    # like-for-like with gate S2: at 2x2 and 2x3 the same circuit, transpiler settings and map
    # must give back the committed counts (not a criterion of this gate -- C9 is the criterion
    # -- but the check that these rows are comparable)
    if lat in (2, 3) and mode in ("exact", "fixed"):
        name = "S2" if mode == "exact" else "S2_fixed"
        p = os.path.join(ROOT, "validation", f"{name}.json")
        if os.path.exists(p) and "B0_ref0_k1" in out["circuits"]:
            with open(p) as fh:
                ref = json.load(fh)["data"][f"2x{lat}"]["coarse_step"]
            got = out["circuits"]["B0_ref0_k1"]["maps"]
            cmp_ = {}
            for mp, key in (("all_to_all", "all_to_all"), (f"heavy_hex_{HH[lat]}", "routed")):
                if mp in got and key in ref:
                    cmp_[mp] = {"committed": ref[key]["cz"], "recomputed": got[mp]["n_2q"],
                                "match": ref[key]["cz"] == got[mp]["n_2q"],
                                "source": f"validation/{name}.json data.2x{lat}."
                                          f"coarse_step.{key}.cz"}
            out["like_for_like_vs_gate_S2"] = cmp_
            print(f"  like-for-like vs validation/{name}.json: "
                  f"{ {k: v['match'] for k, v in cmp_.items()} }", flush=True)
    return out


def _record_for(tq, mapname, t_1q, T1, T2, args):
    """A uniform calibration record covering the qubits and edges the circuit can use."""
    if mapname == "all_to_all":
        nq = tq.num_qubits
        edges = coh.complete_edges(nq)
    else:
        cm = coupling_map(mapname)
        nq = cm.size()
        edges = sorted({tuple(sorted(e)) for e in cm.get_edges()})
    return coh.uniform_record(nq, edges, t_2q=args.t_2q, t_1q=t_1q, t_ro=args.t_ro,
                              T1=T1, T2=T2, dt=coh.HERON_DT)


def stage_schedule(args) -> dict:
    """B5 -- ASAP schedule, idle budget, coherence requirement and the gate-only requirement."""
    lat, mode = args.lattice, args.angle_mode
    maps = [m for m in (args.maps.split(",") if args.maps else MAP_NAMES[lat]) if m]
    n_logical = CodewordEmbedding(model(lat)).n
    out = {"stage": "schedule", "lattice": lat, "angle_mode": mode, "maps": maps,
           "n_logical_qubits": int(n_logical),
           "durations": {"t_2q_s": args.t_2q, "t_1q_s": args.t_1q, "t_ro_s": args.t_ro,
                         "dt_s": coh.HERON_DT,
                         "source": "data/hardware/H0_diag_prep/calibration_20260922T1400Z.json "
                                   "(Heron r2: cz 68 ns, sx and x 24 ns, measure 1.66 us, "
                                   "dt 4 ns)"},
           "f_targets": list(F_TARGETS), "declared_error_triple": DECLARED, "rows": {}}
    grid = select_circuits(lat, args)
    for (twoB, slot, k) in grid:
        tag = circuit_tag(twoB, slot, k)
        for mp in maps:
            tq = load_tq(lat, mode, tag, mp, True)
            if tq is None:
                raise SystemExit(f"no cached transpiled circuit for 2x{lat} {tag} {mp}: run "
                                 f"`--stage compile --lattice {lat} --maps {mp}` first")
            row = {"lattice": f"2x{lat}", "angle_mode": mode, "circuit": tag, "map": mp,
                   **circuit_counts(tq)}
            for t1q_label, t1q in (("heron", args.t_1q), ("zero", 0.0)):
                rec = _record_for(tq, mp, t1q, args.T1, args.T2, args)
                t0 = time.time()
                sch = sk_idle.schedule_asap(tq, rec)
                sch_s = time.time() - t0
                rq = coh.requirement_row(sch, rec, row["n_2q"], f_targets=F_TARGETS,
                                         t_2q=args.t_2q, n_logical=n_logical)
                pq, tot = sk_idle.idle_budget(sch, rec)
                pb = coh.packing_bound(sch)
                _pq2, tot2 = sk_idle.idle_budget(pb["schedule"], rec)
                row[f"t_1q={t1q_label}"] = {
                    "t_1q_s": t1q, "schedule_s": sch_s, **rq,
                    # the budget at the record's own nominal coherence (T1, T2 of the uniform
                    # record), for the packing-bound comparison; the REQUIREMENT above solves
                    # for T2 instead of reading it
                    "record_T1_s": args.T1, "record_T2_s": args.T2,
                    "S_T1_at_record": tot["S_T1"], "S_T2_at_record": tot["S_T2"],
                    "idle_total_s": tot["idle_s"], "busy_total_s": tot["busy_s"],
                    "idle_max_s": max((sch["per_qubit"][q]["idle_s"]
                                       for q in sch["active"]), default=0.0),
                    "n_windows": tot["n_windows"],
                    "longest_window_s": max((v["longest_window_s"] for v in pq.values()),
                                            default=0.0),
                    "packing_bound": {
                        "T_min_s": pb["T_min_s"], "T_min_over_T": (
                            pb["T_min_s"] / float(sch["T_s"]) if sch["T_s"] else None),
                        "speedup_available": pb["speedup_available"],
                        "S_T1_packed": tot2["S_T1"], "S_T2_packed": tot2["S_T2"],
                        "idle_total_packed_s": tot2["idle_s"]},
                }
                req = rq["requirements"]["f=0.1|T1=inf"]["T2_req_over_t_2q"]
                print(f"  2x{lat} {tag} {mp} t_1q={t1q_label}: T {sch['T_s'] * 1e6:.1f} us, "
                      f"seriality {rq['seriality']:.3f}, "
                      f"util {rq['qubit_time_utilisation']:.3f}, "
                      f"T2/t_2q(f=0.1, T1=inf) "
                      f"{'unconstrained' if req is None else f'{req:.0f}'} "
                      f"vs serial {rq['serial_bound']['0.1']:.0f} "
                      f"({sch_s:.0f} s to schedule)", flush=True)
            # ---- gate-only requirement (part C), at zero idle
            cc = dr.CircuitCounts(row["n_2q"], row["n_1q"], row["n_rz"], row["n_measure"], tag)
            gate_only = {}
            for f in F_TARGETS:
                gate_only[str(f)] = {
                    "eps2_alone": dr.required_error(row["n_2q"], f, 1.0),
                    "eps2_at_declared_eps1_eps_ro": dr.required_error_for_set(
                        [cc], "2q", DECLARED["eps2"], DECLARED["eps1"], DECLARED["eps_ro"],
                        f, stat="mean"),
                    "eps2_at_declared_virtual_rz": dr.required_error_for_set(
                        [cc], "2q", DECLARED["eps2"], DECLARED["eps1"], DECLARED["eps_ro"],
                        f, virtual_rz=True, stat="mean"),
                    "budget_shares_at_declared": dr.budget_shares(
                        cc, DECLARED["eps2"], DECLARED["eps1"], DECLARED["eps_ro"], f),
                    "half_space": dr.log_error_budget(cc, f),
                }
            row["gate_only_requirement"] = gate_only
            out["rows"][f"2x{lat}|{mode}|{tag}|{mp}"] = row
    return out


def stage_anchor(args) -> dict:
    """B5's 2x2 anchor (criterion C7) and the FakeFez full-device reading of 2x4.

    (a) the frozen canary QPY on the real ibm_fez record must reproduce T_s, S_T1 and S_T2 of
    `data/S2_duration_compare.json` to 1e-9 relative -- the same code path
    (`skqd.idle.schedule_asap` + `idle_budget`) on the same inputs;
    (b) the FakeFez-routed 2x4 circuits on the FakeFez full-device snapshot: the gate-only f,
    the idle budget, the coherence scale for mean f >= 0.1 with the record's gate errors and
    the coherence-ONLY scale (all gate and readout errors set to zero), which always exists.
    """
    from h0_backends import calibration_record, resolve_backend

    out = {"stage": "anchor"}
    # ---- (a) the frozen canary
    with open(os.path.join(ROOT, "data", "hardware", "H0_diag_prep",
                           "calibration_20260922T1400Z.json")) as fh:
        real = json.load(fh)
    with open(os.path.join(ROOT, "data", "S2_duration_compare.json")) as fh:
        comp = json.load(fh)
    frozen = comp["circuits"]["exact|frozen|B0_ref06_k1_rep1"]
    from qiskit import qpy
    cdir = os.path.join(ROOT, "data", "hardware", "H0_prep", "circuits")
    with open(os.path.join(cdir, "B0_ref06_k1_rep1.json")) as fh:
        man = json.load(fh)
    with gzip.open(os.path.join(cdir, man["qpy"]), "rb") as fh:
        qc = qpy.load(fh)[0]
    sch = sk_idle.schedule_asap(qc, real)
    _pq, tot = sk_idle.idle_budget(sch, real)
    got = {"T_s": float(sch["T_s"]), "S_T1": tot["S_T1"], "S_T2": tot["S_T2"]}
    ref = {"T_s": frozen["T_s"], "S_T1": frozen["S_T1"], "S_T2": frozen["S_T2"]}
    out["canary_2x2"] = {
        "record": os.path.join("data", "hardware", "H0_diag_prep",
                               "calibration_20260922T1400Z.json"),
        "reference": ref, "recomputed": got,
        "relative_difference": {k: abs(got[k] - ref[k]) / abs(ref[k]) for k in ref},
        "max_relative_difference": max(abs(got[k] - ref[k]) / abs(ref[k]) for k in ref),
        "n_cz": int(frozen["n_cz"]), "depth": int(frozen["depth"]),
        "cz_depth": int(frozen["cz_depth"]),
        "qubit_time_utilisation": comp["rescheduling_headroom"]["qubit_time_utilisation"],
        "T_min_s": comp["rescheduling_headroom"]["T_min_s"],
    }
    # ---- Heron T2 statistics of the same record (the device-side comparison numbers)
    T2 = np.array([v["T2_s"] for v in real["qubits"].values()], dtype=float)
    T1 = np.array([v["T1_s"] for v in real["qubits"].values()], dtype=float)
    t2q = coh.record_t_2q(real)
    out["heron_r2_record"] = {
        "source": "data/hardware/H0_diag_prep/calibration_20260922T1400Z.json "
                  "(the 12 qubits the canary ran on)",
        "n_qubits": int(T2.size), "t_2q_s": t2q,
        "T2_mean_s": float(T2.mean()), "T2_median_s": float(np.median(T2)),
        "T2_harmonic_mean_s": float(T2.size / np.sum(1.0 / T2)),
        "T2_min_s": float(T2.min()), "T2_max_s": float(T2.max()),
        "T1_mean_s": float(T1.mean()),
        "T1_harmonic_mean_s": float(T1.size / np.sum(1.0 / T1)),
        "T2_over_t_2q": {
            "arithmetic_mean": float(T2.mean() / t2q),
            "harmonic_mean": float((T2.size / np.sum(1.0 / T2)) / t2q),
            "best_qubit": float(T2.max() / t2q), "worst_qubit": float(T2.min() / t2q)},
        "which_statistic": ("the harmonic mean is the physically right one: the idle budget is "
                            "a sum over qubits of (idle time)/T2_q, so it is the sum of 1/T2 "
                            "that matters, not the mean of T2"),
    }
    # ---- (b) the FakeFez full-device record
    if not args.no_fakefez:
        backend = resolve_backend("FakeFez")
        edges = sorted({tuple(sorted(e)) for e in backend.coupling_map.get_edges()})
        t0 = time.time()
        fez = calibration_record(backend, list(range(backend.num_qubits)), edges)
        out["fakefez_record"] = {
            "backend": fez["backend"], "num_qubits": fez["num_qubits"],
            "last_update_date": fez["last_update_date"], "fingerprint": fez["fingerprint"],
            "n_missing_errors": len(fez["missing_errors"]), "build_s": time.time() - t0}
        cz_err = {}
        for e in fez["edges"].values():
            key = tuple(e["target_key"])
            for kk in (key, key[::-1]):
                cz_err[kk] = e["cz_error"]
        meas_err = {int(q): v["measure_error"] for q, v in fez["qubits"].items()}
        rows = {}
        for lat in (args.fez_lattices and [int(x) for x in args.fez_lattices.split(",")]
                    or [4]):
            grid = CIRCUITS_2x4 if lat == 4 else ((0, 0, 1),)
            for (twoB, slot, k) in grid:
              for mp in ("fakefez", "fakefez_backend"):
                tag = circuit_tag(twoB, slot, k)
                tq = load_tq(lat, "exact", tag, mp, True)
                if tq is None:
                    continue
                logf, n_cz, n_meas = 0.0, 0, 0
                dead, missing = {}, []
                for inst in tq.data:
                    nm = inst.operation.name
                    qs = tuple(tq.find_bit(q).index for q in inst.qubits)
                    if nm == "cz":
                        n_cz += 1
                        e = cz_err.get(qs, cz_err.get(qs[::-1]))
                        if e is None:
                            missing.append(list(qs))
                            continue
                        if float(e) >= 1.0:
                            # the snapshot calls this edge dead; f is then exactly zero and
                            # the edge is RECORDED, never defaulted (prompts/15 A1)
                            dead[f"{min(qs)}-{max(qs)}"] = dead.get(
                                f"{min(qs)}-{max(qs)}", 0) + 1
                            continue
                        logf += math.log1p(-float(e))
                    elif nm == "measure":
                        n_meas += 1
                        e = meas_err.get(qs[0])
                        if e is None or float(e) >= 1.0:
                            missing.append([int(qs[0])])
                            continue
                        logf += math.log1p(-float(e))
                f_gates = 0.0 if (dead or missing) else math.exp(logf)
                f_gates_excluding = math.exp(logf)
                sch = sk_idle.schedule_asap(tq, fez)
                _p, tot = sk_idle.idle_budget(sch, fez)
                s_idle = sk_idle.idle_log_budget(tot)
                lam, limit = coh.coherence_scale_one(sch, fez,
                                                     f_gates if f_gates > 0 else
                                                     f_gates_excluding, 0.1)
                zrec = coh.zero_error_record(fez)
                lam0, _l0 = coh.coherence_scale_one(sch, zrec, 1.0, 0.1)
                lam0w, _ = coh.coherence_scale_one(sch, zrec, 1.0, 0.05)
                rows[f"2x{lat}|{tag}|{mp}"] = {
                    "n_cz": n_cz, "n_measure": n_meas, "T_s": float(sch["T_s"]),
                    "T_total_s": float(sch["T_total_s"]),
                    "f_gates": f_gates,
                    "f_gates_excluding_dead_edges": f_gates_excluding,
                    "dead_edges_used": dead, "n_dead_cz_instructions": int(sum(dead.values())),
                    "entries_without_an_error": missing,
                    "f_gates_note": ("f_gates is exactly 0 when the routing used an edge whose "
                                     "FakeFez snapshot cz error is 1.0; the "
                                     "f_gates_excluding_dead_edges column is the same product "
                                     "with those instructions left out, which is what the "
                                     "coherence-scale column is read on"),
                    "S_T1": tot["S_T1"], "S_T2": tot["S_T2"],
                    "S_idle": s_idle, "f_idle_aware": sk_idle.f_idle_aware(f_gates, tot),
                    "n_windows": tot["n_windows"], "idle_total_s": tot["idle_s"],
                    "coherence_scale_for_f_0.1": lam, "coherence_scale_limit_f_gates": limit,
                    "coherence_only_scale_for_f_0.1": lam0,
                    "coherence_only_scale_for_f_0.05": lam0w,
                    "log_budget_accounting": {
                        "f_target": 0.1, "budget_log": math.log(10.0),
                        "spent_by_gates_and_readout": -math.log(f_gates_excluding),
                        "spent_by_idle": s_idle,
                        "total": -math.log(f_gates_excluding) + s_idle,
                        "over_budget_by": (-math.log(f_gates_excluding) + s_idle
                                           - math.log(10.0)),
                        "note": "read on f_gates_excluding_dead_edges"},
                }
                print(f"  FakeFez 2x{lat} {tag} [{mp}]: f_gates {f_gates:.3e} "
                      f"({f_gates_excluding:.3e} excluding {sum(dead.values())} dead-edge CZ), "
                      f"S_idle {s_idle:.1f}, lam {lam}, coherence-only lam {lam0:.1f}",
                      flush=True)
        out["fakefez_rows"] = rows
    return out


def stage_serial(args) -> dict:
    """C8 -- the owner's serial formula reproduced from the committed counts."""
    with open(os.path.join(ROOT, "validation", "S2.json")) as fh:
        s2 = json.load(fh)["data"]
    with open(os.path.join(ROOT, "data", "S2_duration_compare.json")) as fh:
        sdc = json.load(fh)
    with open(os.path.join(ROOT, "data", "S2D_2x3_device_requirements.json")) as fh:
        sheet = json.load(fh)
    rows = [
        ("2x2 all-to-all (CZ)", 12, s2["2x2"]["coarse_step"]["all_to_all"]["cz"],
         "validation/S2.json data.2x2.coarse_step.all_to_all.cz", 667.1),
        ("2x2 routed, the frozen canary", 12,
         sdc["circuits"]["exact|frozen|B0_ref06_k1_rep1"]["n_cz"],
         "data/S2_duration_compare.json circuits.exact|frozen|B0_ref06_k1_rep1.n_cz", 1727.6),
        ("2x3 all-to-all (RZZ)", 20, sheet["counts"]["per_term_rzz_sum"],
         "data/S2D_2x3_device_requirements.json counts.per_term_rzz_sum", 9372.1),
        ("2x3 routed heavy-hex d=5", 20, s2["2x3"]["coarse_step"]["routed"]["cz"],
         "validation/S2.json data.2x3.coarse_step.routed.cz", 23786.3),
        ("2x3 fixed-angle all-to-all (RZZ)", 20,
         sheet["levers"]["fixed_angle_generator"]["counts_rzz_recomputed"]["rzz"],
         "data/S2D_2x3_device_requirements.json levers.fixed_angle_generator."
         "counts_rzz_recomputed.rzz", 7035.6),
    ]
    out = {"stage": "serial", "f_target": 0.1, "rows": []}
    worst = 0.0
    for label, n, n2q, src, owner in rows:
        v = coh.serial_bound(n, int(n2q), 0.1)
        worst = max(worst, abs(v - owner))
        out["rows"].append({"circuit": label, "n_qubits": n, "n_2q": int(n2q), "source": src,
                            "serial_bound": v, "owner_value": owner,
                            "abs_difference": abs(v - owner)})
        print(f"  {label}: n={n}, n_2q={n2q} -> T2/t_2q {v:.1f} (owner {owner})", flush=True)
    out["max_abs_difference"] = worst
    # extra rows for the report (no owner value to compare against)
    extra = [("2x2 routed heavy-hex d=3", 12, s2["2x2"]["coarse_step"]["routed"]["cz"],
              "validation/S2.json data.2x2.coarse_step.routed.cz"),
             ("2x3 all-to-all (CZ)", 20, s2["2x3"]["coarse_step"]["all_to_all"]["cz"],
              "validation/S2.json data.2x3.coarse_step.all_to_all.cz")]
    out["extra_rows"] = [{"circuit": l, "n_qubits": n, "n_2q": int(c), "source": s,
                          "serial_bound": coh.serial_bound(n, int(c), 0.1)}
                         for l, n, c, s in extra]
    return out


def stage_circuits(args) -> dict:
    """B6 -- the sparse simulator: the coarse-step circuits against `krylov.coarse_states`,
    the regressions at 2x2/2x3 against `run_ir`, and the compiled-circuit leakage."""
    lat, mode = args.lattice, args.angle_mode
    M = model(lat)
    E = CodewordEmbedding(M)
    out = {"stage": "circuits", "lattice": lat, "angle_mode": mode,
           "n_qubits": int(E.n), "n_codewords": int(E.ints.size),
           "regressions": {}, "coarse_steps": {}, "compiled": {}}
    groups = term_groups(M.terms, G2, mass_default(G2))

    # ---- C4: the simulator against run_ir on the dense statevector (2x2 and 2x3 only)
    if lat in (2, 3) and not args.no_regression:
        worst, cnt = 0.0, 0
        t0 = time.time()
        if lat == 2:
            F = CircuitFactory(M, G2, angle_mode=mode)
            for twoB in (0, 2):
                dt = dt_of(lat, twoB)
                for r in references(M.basis, twoB)[:2]:
                    for k in (1, 2, 3, 4):
                        g = F.coarse_step(r, k, dt)
                        worst = max(worst, float(np.abs(run_ir(g, E.n)
                                                        - run_sparse(g, E.n).dense()).max()))
                        cnt += 1
                    g = F.trotter(r, 2, dt)
                    worst = max(worst, float(np.abs(run_ir(g, E.n)
                                                    - run_sparse(g, E.n).dense()).max()))
                    cnt += 1
        else:
            F = CircuitFactory(M, G2, angle_mode=mode)
            dt = dt_of(lat, 0)
            r = references(M.basis, 0)[0]
            for k in (1, 2):
                g = F.coarse_step(r, k, dt)
                worst = max(worst, float(np.abs(run_ir(g, E.n)
                                                - run_sparse(g, E.n).dense()).max()))
                cnt += 1
        out["regressions"][f"2x{lat}_vs_run_ir"] = {
            "n_circuits": cnt, "max_abs_difference": worst, "wall_s": time.time() - t0}
        print(f"  2x{lat}: {cnt} circuits vs run_ir, max |delta| {worst:.2e} "
              f"({time.time() - t0:.0f} s)", flush=True)

    # ---- C5: the coarse-step circuits against the dressed-basis emulation
    grid = select_circuits(lat, args)
    for (twoB, slot, k) in (() if args.no_coarse else grid):
        tag = circuit_tag(twoB, slot, k)
        gates, dt, ref = coarse_step_ir(lat, mode, twoB, slot, k)
        t0 = time.time()
        st = run_sparse(gates, E.n)
        wall = time.time() - t0
        t1 = time.time()
        exact = coarse_states(groups, basis_vector(M.basis.dim, ref), dt, k)[k]
        emu = time.time() - t1
        got = st.dense_on(E.ints)
        dev = float(np.abs(got - exact).max()) if mode == "exact" else None
        leak = float(1.0 - np.sum(np.abs(got) ** 2))
        out["coarse_steps"][tag] = {
            "reference_index": ref, "twoB": twoB, "k": k, "dt": dt,
            "ir_gates": len(gates), "max_deviation_vs_coarse_states": dev,
            "leakage": leak, "sparse_wall_s": wall, "emulation_wall_s": emu,
            "sparse_max_support": int(st.max_support),
            "sparse_final_support": int(st.support_size),
            "n_pairings": int(st.n_pairings), "n_sorts": int(st.n_sorts),
            "norm": st.norm()}
        print(f"  2x{lat} {tag}: {len(gates)} IR gates, dev "
              f"{'n/a' if dev is None else f'{dev:.2e}'}, leak {leak:.2e}, "
              f"support max {st.max_support}, {wall:.0f} s sparse + {emu:.0f} s emulation",
              flush=True)

    # ---- C6: leakage of the level-3 all-to-all transpiled circuit
    if not args.no_compiled:
        for (twoB, slot, k) in grid:
            tag = circuit_tag(twoB, slot, k)
            if k != 1 or twoB != 0 or slot != 0:
                continue
            tq = load_tq(lat, mode, tag, "all_to_all", False)
            if tq is None:
                print("  (no cached all-to-all transpiled circuit: run --stage compile)")
                continue
            t0 = time.time()
            stq = run_sparse_qiskit(tq)
            wall = time.time() - t0
            v = stq.dense_on(E.ints)
            out["compiled"][f"{tag}|all_to_all"] = {
                "n_instructions": int(len(tq.data)), "n_2q": int(tq.count_ops().get("cz", 0)),
                "leakage": float(1.0 - np.sum(np.abs(v) ** 2)),
                "sparse_wall_s": wall, "sparse_max_support": int(stq.max_support),
                "norm": stq.norm()}
            print(f"  2x{lat} {tag} transpiled all-to-all: leakage "
                  f"{out['compiled'][f'{tag}|all_to_all']['leakage']:.2e}, "
                  f"support max {stq.max_support}, {wall:.0f} s", flush=True)
    return out


def stage_compiled(args) -> dict:
    """C6, staged -- the leakage of the level-3 transpiled 2x4 circuit, in segments.

    The 2x4 all-to-all transpiled circuit has of order 6e5 instructions and the sparse state
    carries 2.6e5 amplitudes, so one pass is about 30 minutes on this CPU: past the 20-minute
    guidance of prompts/22 B6 and at the 30-minute laptop rule.  The check is therefore SPLIT,
    not reduced: `--nseg n --seg i` executes the i-th contiguous block of instructions starting
    from the checkpointed state of the previous block, and the last block writes the fragment
    with the summed wall time.  Nothing about the check changes -- the same instructions in the
    same order on the same exact simulator.
    """
    import numpy as _np
    lat, mode = args.lattice, args.angle_mode
    M = model(lat)
    E = CodewordEmbedding(M)
    grid = select_circuits(lat, args)
    mp = (args.maps or "all_to_all").split(",")[0]
    out = {"stage": "compiled", "lattice": lat, "angle_mode": mode, "map": mp,
           "n_segments": int(args.nseg), "compiled": {}}
    from skqd.sparse_sim import SparseState, apply_ir, qiskit_to_ir
    for (twoB, slot, k) in grid:
        tag = circuit_tag(twoB, slot, k)
        tq = load_tq(lat, mode, tag, mp, False)
        if tq is None:
            raise SystemExit(f"no cached transpiled circuit for 2x{lat} {mode} {tag} {mp}")
        gates = qiskit_to_ir(tq)
        n_inst = len(gates)
        bounds = [round(i * n_inst / args.nseg) for i in range(args.nseg + 1)]
        ck = os.path.join(CACHE, f"leak_{lat}_{mode}_{tag}_{mp}_{args.nseg}.npz")
        if args.seg == 0:
            st = SparseState(tq.num_qubits)
            prev = {"wall_s": 0.0, "max_support": 1}
        else:
            z = _np.load(ck)
            st = SparseState(tq.num_qubits, idx=z["idx"], amp=z["amp"])
            st.max_support = int(z["max_support"])
            prev = {"wall_s": float(z["wall_s"]), "max_support": int(z["max_support"])}
        t0 = time.time()
        apply_ir(st, gates[bounds[args.seg]:bounds[args.seg + 1]])
        st.to_sparse()
        wall = prev["wall_s"] + (time.time() - t0)
        maxsup = max(prev["max_support"], st.max_support)
        _np.savez_compressed(ck, idx=st.idx, amp=st.amp, wall_s=wall, max_support=maxsup)
        rec = {"segment": args.seg, "n_segments": int(args.nseg),
               "instructions": [bounds[args.seg], bounds[args.seg + 1]],
               "n_instructions_total": n_inst,
               "support_after_segment": int(st.support_size),
               "sparse_max_support": int(maxsup), "sparse_wall_s": wall,
               "n_2q": int(tq.count_ops().get("cz", 0))}
        if args.seg == args.nseg - 1:
            v = st.dense_on(E.ints)
            rec["leakage"] = float(1.0 - _np.sum(_np.abs(v) ** 2))
            rec["norm"] = st.norm()
            rec["complete"] = True
        else:
            rec["complete"] = False
        out["compiled"][f"{tag}|{mp}"] = rec
        print(f"  2x{lat} {mode} {tag} {mp} segment {args.seg + 1}/{args.nseg} "
              f"[{bounds[args.seg]}:{bounds[args.seg + 1]}] of {n_inst}: support "
              f"{st.support_size}, max {maxsup}, {wall:.0f} s cumulative"
              + (f", leakage {rec['leakage']:.2e}" if rec.get("complete") else ""), flush=True)
    return out


def stage_probe(args) -> dict:
    """The C6 attempt, recorded: how the sparse support of the level-3 TRANSPILED 2x4 circuit
    grows, and how far the exact simulation gets inside a wall-clock cap.

    This is the measurement the prompts/22 B6 instruction asks for when a circuit does not
    finish ("stop that circuit, record the wall time and the sparse support size, and report --
    do not reduce the check silently").  Nothing is truncated or thresholded: the run is simply
    stopped, and where it stopped is the number.
    """
    lat, mode = args.lattice, args.angle_mode
    mp = (args.maps or "all_to_all").split(",")[0]
    out = {"stage": "probe", "lattice": lat, "angle_mode": mode, "map": mp,
           "wall_cap_s": float(args.cap_s), "circuits": {}}
    from skqd.sparse_sim import SparseState, apply_ir, qiskit_to_ir
    for (twoB, slot, k) in select_circuits(lat, args):
        tag = circuit_tag(twoB, slot, k)
        tq = load_tq(lat, mode, tag, mp, False)
        if tq is None:
            raise SystemExit(f"no cached transpiled circuit for 2x{lat} {mode} {tag} {mp}")
        gates = qiskit_to_ir(tq)
        st = SparseState(tq.num_qubits)
        rows, t0, last = [], time.time(), 0
        for frac in (0.002, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.0):
            hi = int(frac * len(gates))
            apply_ir(st, gates[last:hi])
            last = hi
            st.to_sparse()
            rows.append({"fraction": frac, "instructions": hi,
                         "support": int(st.support_size),
                         "max_support": int(st.max_support),
                         "n_pairings": int(st.n_pairings), "wall_s": time.time() - t0,
                         "amplitude_array_mb": st.support_size * 16 / 2 ** 20})
            print(f"  {tag} {mp}: {100 * frac:5.1f} % ({hi} of {len(gates)} instructions) "
                  f"support {st.support_size}, {time.time() - t0:.0f} s", flush=True)
            if time.time() - t0 > float(args.cap_s):
                break
        out["circuits"][f"{tag}|{mp}"] = {
            "n_instructions": len(gates), "ops": {kk: int(v) for kk, v in tq.count_ops().items()},
            "n_2q": int(tq.count_ops().get("cz", 0)), "n_qubits": int(tq.num_qubits),
            "completed": last == len(gates), "growth": rows,
            "final_support": int(st.support_size), "wall_s": time.time() - t0,
            "leakage": (float(1.0 - np.sum(np.abs(
                st.dense_on(CodewordEmbedding(model(lat)).ints)) ** 2))
                if last == len(gates) else None)}
    return out


def stage_term_compiled(args) -> dict:
    """Leakage and deviation of the level-3 TRANSPILED term gates, on their own supports.

    Affordable where the transpiled full step is not: each term gate is transpiled as a
    k-qubit all-to-all circuit (k <= 16) with exactly the settings of `cq.transpile_counts`,
    and executed on the 2^k local statevector by the exact sparse simulator from a random
    superposition of the local codewords.  A REPORTED measurement, not a criterion: gate
    S2_2x4's criterion C6 is on the transpiled coarse step, not on its terms.
    """
    lat, mode = args.lattice, args.angle_mode
    M = model(lat)
    ths = theta_table(lat)
    th = ths["dt"]
    rng = np.random.default_rng(args.seed)
    only = [t for t in (args.only.split(",") if args.only else term_names(lat)) if t]
    out = {"stage": "term_compiled", "lattice": lat, "angle_mode": mode, "theta": th,
           "optimization_level": LEVEL, "seed_transpiler": SEED, "terms": {}}
    import scipy.linalg as sla
    from qiskit import transpile

    from skqd import circuits_qiskit as cq
    from skqd.sparse_sim import SparseState, apply_ir, qiskit_to_ir
    for name in only:
        O, sup = term_operator(lat, name)
        k = len(sup)
        states, h, _pos = localize(M, O, sup)
        pos = {q: i for i, q in enumerate(sup)}
        gates, _st, _s, _c = term_ir(lat, name, mode, th)
        loc = [(nm, [pos[q] for q in qs], par) for nm, qs, par in gates]
        t0 = time.time()
        tq = transpile(cq.ir_to_qiskit(loc, k, measure=False), basis_gates=list(BASIS),
                       optimization_level=LEVEL, seed_transpiler=SEED)
        t_tr = time.time() - t0
        tir = qiskit_to_ir(tq)
        idx = np.array(states, dtype=np.int64)
        U = sla.expm(-1j * th * h)
        leak, dev, t0 = 0.0, 0.0, time.time()
        nv = args.nvec if args.nvec else (3 if k >= 14 else 5)
        for _ in range(nv):
            c = rng.normal(size=len(states)) + 1j * rng.normal(size=len(states))
            c = c / np.linalg.norm(c)
            st = SparseState(k, idx=idx, amp=c)
            apply_ir(st, tir)
            got = st.dense_on(idx)
            leak = max(leak, abs(1.0 - float(np.sum(np.abs(got) ** 2))))
            dev = max(dev, float(np.abs(got - U @ c).max()))
        out["terms"][name] = {
            "support": k, "n_2q": int(tq.count_ops().get("cz", 0)),
            "n_instructions": int(len(tq.data)), "depth": int(tq.depth()),
            "leakage": leak, "max_deviation": dev, "n_vectors": nv,
            "transpile_s": t_tr, "simulate_s": time.time() - t0,
            "sparse_max_support": int(st.max_support)}
        print(f"  {name} transpiled ({tq.count_ops().get('cz', 0)} CZ, {len(tq.data)} "
              f"instructions): leakage {leak:.2e}, deviation {dev:.2e} "
              f"({t_tr:.0f} s transpile, {time.time() - t0:.0f} s simulate)", flush=True)
    out["worst_leakage"] = max((v["leakage"] for v in out["terms"].values()), default=None)
    out["worst_deviation"] = max((v["max_deviation"] for v in out["terms"].values()),
                                 default=None)
    return out


def stage_dense(args) -> dict:
    """D3 -- the one dense 2^28 cross-check: the 2x4 `hop1` term gate on the Dirac sea.

    `run_ir` on a 2^28 statevector needs about 17 GB with its work copies (planner P4), so
    MemAvailable is checked first and the shortfall is RECORDED, never silently skipped."""
    lat, mode = 4, args.angle_mode
    M = model(lat)
    E = CodewordEmbedding(M)
    dt = dt_of(lat, 0)
    gates, _st, _s, _c = term_ir(lat, args.dense_term, mode, dt)
    from skqd.krylov import dirac_sea
    init = int(E.ints[dirac_sea(M.basis)])
    avail = mem_available_gb()
    out = {"stage": "dense", "term": args.dense_term, "theta": dt, "n_qubits": int(E.n),
           "ir_gates": len(gates), "ir_gate_counts": gate_counts(gates),
           "init_int": init, "mem_available_gb": avail,
           "mem_required_gb": 17.0,
           "requirement": "MemAvailable >= 24 GB (a 2^28 complex128 statevector is 4.3 GB and "
                          "run_ir's apply_local work copies bring the peak to about 17 GB)"}
    t0 = time.time()
    sp = run_sparse(gates, E.n, init_int=init)
    out["sparse_wall_s"] = time.time() - t0
    out["sparse_support"] = int(sp.support_size)
    out["sparse_max_support"] = int(sp.max_support)
    if avail < 24.0:
        out["ran_dense"] = False
        out["max_abs_difference"] = None
        out["reason"] = (f"MemAvailable {avail:.1f} GB < 24 GB: the dense 2^28 run_ir "
                         f"cross-check was not run")
        print(f"  MemAvailable {avail:.1f} GB < 24 GB: dense 2^28 check NOT run", flush=True)
        return out
    psi = np.zeros(2 ** E.n, dtype=complex)
    psi[init] = 1.0
    t0 = time.time()
    dense = run_ir(gates, E.n, psi)
    out["dense_wall_s"] = time.time() - t0
    out["ran_dense"] = True
    nz = np.nonzero(dense)[0]
    sidx, samp = sp.sorted_state()
    got = np.zeros(nz.size, dtype=complex)
    pos = np.searchsorted(sidx, nz)
    pos = np.clip(pos, 0, max(sidx.size - 1, 0))
    found = sidx[pos] == nz
    got[found] = samp[pos[found]]
    d1 = float(np.abs(dense[nz] - got).max()) if nz.size else 0.0
    d2 = float(np.abs(samp).max()) if sidx.size else 0.0
    # the reverse direction: every sparse entry must equal the dense amplitude
    d3 = float(np.abs(dense[sidx] - samp).max()) if sidx.size else 0.0
    out["dense_nonzero_entries"] = int(nz.size)
    out["max_abs_difference"] = max(d1, d3)
    out["max_abs_difference_dense_to_sparse"] = d1
    out["max_abs_difference_sparse_to_dense"] = d3
    out["max_abs_amplitude"] = d2
    del dense, psi
    print(f"  dense 2^28 {args.dense_term}: max |delta| {out['max_abs_difference']:.2e} "
          f"({out['dense_wall_s']:.0f} s dense, {out['sparse_wall_s']:.1f} s sparse)",
          flush=True)
    return out


def pristine_module():
    """`src/skqd/circuits_ir.py` as it stands at HEAD, imported beside the modified one.

    This is what makes criterion C9 decisive rather than circumstantial: the two modules are
    asked for the SAME coarse-step gate lists and the same transpiled counts, so a difference
    between the committed JSON and a fresh run can be attributed to this change or to the
    environment by measurement instead of argument.
    """
    import importlib.util
    import tempfile
    src = subprocess.check_output(["git", "show", "HEAD:src/skqd/circuits_ir.py"],
                                  cwd=ROOT).decode()
    d = tempfile.mkdtemp()
    path = os.path.join(d, "pristine_circuits_ir.py")
    with open(path, "w") as fh:
        fh.write(src.replace("from .codec import", "from skqd.codec import")
                    .replace("from .exact import", "from skqd.exact import")
                    .replace("from .krylov import", "from skqd.krylov import")
                    .replace("from .reference_sim import", "from skqd.reference_sim import"))
    spec = importlib.util.spec_from_file_location("pristine_circuits_ir", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pristine_circuits_ir"] = mod
    spec.loader.exec_module(mod)
    return mod


def pristine_comparison() -> dict:
    """HEAD's `circuits_ir` against the modified one: gate-list digest and transpiled counts."""
    import hashlib

    import skqd.circuits_ir as newmod
    from skqd import circuits_qiskit as cq
    old = pristine_module()
    out = {"source": "git show HEAD:src/skqd/circuits_ir.py", "rows": {}}
    same = True
    for lat in (2, 3):
        M = model(lat)
        n = CodewordEmbedding(M).n
        dt = dt_of(lat, 0)
        r = references(M.basis, 0)[0]
        for am in ("exact", "fixed"):
            rec = {}
            for label, mod in (("pristine", old), ("modified", newmod)):
                g = mod.CircuitFactory(M, G2, angle_mode=am).coarse_step(r, 1, dt)
                blob = repr([(nm, list(qs),
                              None if par is None else
                              (par.tolist() if hasattr(par, "tolist") else par))
                             for nm, qs, par in g])
                res = cq.transpile_counts(g, n, optimization_level=LEVEL, seed=SEED)
                rec[label] = {"ir_gates": len(g),
                              "gate_list_sha256": hashlib.sha256(blob.encode()).hexdigest(),
                              "cz": res["cz"], "depth": res["depth"]}
            rec["identical"] = rec["pristine"] == rec["modified"]
            same = same and rec["identical"]
            out["rows"][f"2x{lat}|{am}"] = rec
    out["identical"] = same
    return out


def stage_repro(args) -> dict:
    """A3 / C9 -- gate S2 and S2_fixed reproduce their committed counts after the A1 change."""
    out = {"stage": "repro", "runs": {}}
    ok = True
    # `gate_S2.py` writes its report under a FIXED name whatever `--out` is, so the two
    # committed gate-S2 reports are saved and restored around the reproduction runs: this
    # gate must not rewrite another gate's report.
    reports = [os.path.join(ROOT, "reports", n) for n in
               ("S2_structured_circuits.md", "S2_fixed_angle_circuits.md")]
    saved = {p: (open(p, "rb").read() if os.path.exists(p) else None) for p in reports}
    for mode, ref_name in (("exact", "S2"), ("fixed", "S2_fixed")):
        tmp = f"{ref_name}_repro"
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "gate_S2.py"), "--quick",
               "--no-tests", "--out", tmp]
        if mode == "fixed":
            cmd += ["--angle-mode", "fixed"]
        t0 = time.time()
        pr = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        wall = time.time() - t0
        rp = os.path.join(ROOT, "validation", f"{tmp}.json")
        if not os.path.exists(rp):
            out["runs"][ref_name] = {"ran": False, "returncode": pr.returncode,
                                     "stderr": pr.stderr[-2000:], "wall_s": wall}
            ok = False
            continue
        with open(rp) as fh:
            new = json.load(fh)["data"]
        with open(os.path.join(ROOT, "validation", f"{ref_name}.json")) as fh:
            old = json.load(fh)["data"]
        diffs = []
        keys = ["per_term_cz", "per_term_cz_routed"]
        if mode == "fixed":
            keys += ["per_term_cz_grid"]
        for lat in ("2x2", "2x3"):
            for key in keys:
                if old[lat].get(key) != new[lat].get(key):
                    for t in sorted(set(old[lat].get(key, {})) | set(new[lat].get(key, {}))):
                        a, b = old[lat].get(key, {}).get(t), new[lat].get(key, {}).get(t)
                        if a != b:
                            diffs.append({"lattice": lat, "key": key, "term": t,
                                          "committed": a, "reproduced": b})
            for sub in sorted(set(old[lat]["coarse_step"]) & set(new[lat]["coarse_step"])):
                for f in ("cz", "depth"):
                    a = old[lat]["coarse_step"][sub][f]
                    b = new[lat]["coarse_step"][sub][f]
                    if a != b:
                        diffs.append({"lattice": lat, "key": f"coarse_step.{sub}.{f}",
                                      "committed": a, "reproduced": b})
            if mode == "fixed":
                for t, a in old[lat].get("per_term_leakage", {}).items():
                    b = new[lat].get("per_term_leakage", {}).get(t)
                    if b is None or abs(float(a) - float(b)) > 1e-15:
                        diffs.append({"lattice": lat, "key": "per_term_leakage", "term": t,
                                      "committed": a, "reproduced": b})
        out["runs"][ref_name] = {
            "ran": True, "returncode": pr.returncode, "wall_s": wall,
            "compared_keys": keys + ["coarse_step.*.cz", "coarse_step.*.depth"]
            + (["per_term_leakage (to 1e-15)"] if mode == "fixed" else []),
            "n_differences": len(diffs), "differences": diffs,
            "identical": len(diffs) == 0,
            "coarse_step_cz": {lat: {s: new[lat]["coarse_step"][s]["cz"]
                                     for s in new[lat]["coarse_step"]}
                               for lat in ("2x2", "2x3")}}
        ok = ok and not diffs
        print(f"  gate_S2 --angle-mode {mode}: {len(diffs)} differences from "
              f"validation/{ref_name}.json ({wall:.0f} s)", flush=True)
        # the reproduction run is a test output, not a gate output
        os.remove(rp)
    restored = []
    for p, blob in saved.items():
        if blob is None:
            if os.path.exists(p):
                os.remove(p)
                restored.append(os.path.relpath(p, ROOT) + " (removed)")
        else:
            with open(p, "rb") as fh:
                now = fh.read()
            if now != blob:
                with open(p, "wb") as fh:
                    fh.write(blob)
                restored.append(os.path.relpath(p, ROOT))
    out["restored_reports"] = restored
    out["identical_all_keys"] = ok
    t0 = time.time()
    out["pristine_vs_modified"] = pristine_comparison()
    out["pristine_vs_modified"]["wall_s"] = time.time() - t0
    # a difference against the COMMITTED json that the pristine HEAD module reproduces is not
    # caused by this change; it is recorded with the evidence, never dropped
    attributed = []
    for name, run in out["runs"].items():
        for diff in run.get("differences", []):
            key = f"2x{diff['lattice'].split('x')[1]}|{'exact' if name == 'S2' else 'fixed'}"
            row = out["pristine_vs_modified"]["rows"].get(key)
            pr = row["pristine"] if row else None
            attributed.append({
                **diff, "pristine_head_value":
                    (pr.get(diff["key"].split(".")[-1]) if pr else None),
                "pristine_head_reproduces_the_fresh_value": bool(
                    row and row["identical"]),
                "attribution": ("the environment, not this change: HEAD's circuits_ir gives "
                                "the same gate list and the same transpiled counts as the "
                                "modified one (gate_list_sha256 identical)")
                if (row and row["identical"]) else "UNATTRIBUTED"})
    out["differences_not_caused_by_this_change"] = attributed
    cz_ok = all(not [d for d in run.get("differences", [])
                     if "cz" in d["key"] or d["key"] in ("per_term_cz", "per_term_cz_routed",
                                                         "per_term_cz_grid",
                                                         "per_term_leakage")]
                for run in out["runs"].values())
    out["cz_counts_identical"] = bool(cz_ok)
    out["identical"] = bool(cz_ok and out["pristine_vs_modified"]["identical"])
    out["criterion_note"] = (
        "C9 is read as: every CZ / per-term count identical to the committed JSON, AND HEAD's "
        "circuits_ir bit-for-bit identical to the modified one (gate lists and transpiled "
        "counts).  `identical_all_keys` is the stricter reading over every key of A3 and is "
        "recorded beside it; any key where the two disagree is listed in "
        "differences_not_caused_by_this_change with the pristine-HEAD evidence.")
    print(f"  pristine HEAD vs modified circuits_ir: "
          f"identical {out['pristine_vs_modified']['identical']}; "
          f"CZ counts identical {cz_ok}; all A3 keys identical {ok}", flush=True)
    return out


# ==================================================================== part F (Perlmutter)
# The transpiled 2x4 circuit of criterion C6 is shipped to the CI as a QPY file.  The laptop's
# qiskit 2.5.2 writes QPY version 17 by default, which the CI's qiskit 1.4.3 cannot read, so the
# circuit is re-written at version 13 (qiskit 2.5.2's QPY_COMPATIBILITY_VERSION, the newest
# version the 1.x line reads) and checked to round-trip.  The GPU job loads ONLY that file: if it
# cannot be read, the job fails loudly -- it never re-transpiles the IR, because qiskit 1.4.3's
# transpiler would produce a different circuit from the one whose 69688 CZ were reported.
QPY_CI_VERSION = 13
TRANSPILED_V17 = {4: os.path.join(FRAG, "circuit_2x4_B0_ref0_k1_all_to_all.qpy.gz")}


def transpiled_v13_path(lat: int) -> str:
    return os.path.join(FRAG, f"circuit_2x{lat}_B0_ref0_k1_all_to_all_v13.qpy.gz")


def transpiled_manifest_path(lat: int) -> str:
    return os.path.join(FRAG, f"circuit_2x{lat}_B0_ref0_k1_all_to_all_v13.json")


def _sha256_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _qpy_header(path: str) -> dict:
    """The QPY magic and format version, read from the (gzipped) file header."""
    with gzip.open(path, "rb") as fh:
        head = fh.read(7)
    return {"magic": head[:6].decode("ascii", "replace"), "qpy_version": int(head[6])}


def _listing(qc) -> list:
    """(name, qubit indices, params) of every instruction -- gate-by-gate identity."""
    return [(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits),
             tuple(float(x) for x in inst.operation.params))
            for inst in qc.data]


def map_to_physical(ints, perm) -> np.ndarray:
    """Basis integers of the virtual (IR) qubits -> the physical qubits of the transpiled
    circuit, with perm[v] = the physical qubit that carries virtual qubit v at the end
    (`TranspileLayout.final_index_layout`, recorded in the manifest on the laptop so the CI
    needs no layout API).  The identity permutation returns the integers unchanged."""
    ints = np.asarray(ints, dtype=np.int64)
    if perm is None or list(perm) == list(range(len(perm))):
        return ints
    out = np.zeros_like(ints)
    for v, ph in enumerate(perm):
        out |= ((ints >> np.int64(v)) & 1) << np.int64(ph)
    return out


def stage_qpy13(args) -> dict:
    """Re-write the transpiled k = 1 B = 0 all-to-all circuit at QPY version 13 (laptop only).

    Source: the committed v17 file at 2x4, the transpile cache at 2x2/2x3 (the laptop tests of
    the GPU branch).  The v13 file is reloaded and compared with the source: qubit count, global
    phase, op counts, instruction count, gate-by-gate (name, qubits, params) and
    `QuantumCircuit.__eq__`.  The manifest written beside it carries the sha256 the GPU job
    checks, the expected counts, and the final index layout, so the CI uses no layout API."""
    import qiskit
    from qiskit import qpy
    lat = args.lattice
    src = TRANSPILED_V17.get(lat) or _tq_cache(lat, "exact", "B0_ref0_k1", "all_to_all", False)
    if not os.path.exists(src):
        raise SystemExit(f"no transpiled source circuit {os.path.relpath(src, ROOT)}: run "
                         f"`--stage compile --lattice {lat} --maps all_to_all` first")
    with gzip.open(src, "rb") as fh:
        qc = qpy.load(fh)[0]
    dst = transpiled_v13_path(lat)
    t0 = time.time()
    with gzip.open(dst, "wb", compresslevel=6) as fh:
        qpy.dump(qc, fh, version=QPY_CI_VERSION)
    dump_s = time.time() - t0
    with gzip.open(dst, "rb") as fh:
        back = qpy.load(fh)[0]
    perm = None
    if qc.layout is not None:
        try:
            perm = [int(x) for x in qc.layout.final_index_layout()]
        except Exception:                                        # pragma: no cover
            perm = None
    checks = {
        "num_qubits": qc.num_qubits == back.num_qubits,
        "global_phase": float(qc.global_phase) == float(back.global_phase),
        "count_ops": dict(qc.count_ops()) == dict(back.count_ops()),
        "n_instructions": len(qc.data) == len(back.data),
        "gate_by_gate": _listing(qc) == _listing(back),
        "circuit_equality": bool(qc == back),
    }
    # the expected two-qubit count is the one the compile stage reported for this circuit
    want_cz = None
    for frag in read_frags(f"compile_{lat}_exact").values():
        m = frag.get("circuits", {}).get("B0_ref0_k1", {}).get("maps", {}).get("all_to_all")
        if m:
            want_cz = int(m["n_2q"])
    manifest = {
        "file": os.path.relpath(dst, ROOT), "sha256": _sha256_file(dst),
        "header": _qpy_header(dst), "qpy_version_written": QPY_CI_VERSION,
        "source": os.path.relpath(src, ROOT), "source_sha256": _sha256_file(src),
        "source_header": _qpy_header(src),
        "written_by": {"qiskit": qiskit.__version__},
        "lattice": lat, "circuit": "B0_ref0_k1", "map": "all_to_all", "angle_mode": "exact",
        "transpiler": {"optimization_level": LEVEL, "seed_transpiler": SEED,
                       "basis_gates": list(BASIS)},
        "num_qubits": int(qc.num_qubits), "n_instructions": int(len(qc.data)),
        "ops": {k: int(v) for k, v in qc.count_ops().items()},
        "n_2q": int(qc.count_ops().get("cz", 0)), "n_2q_reported_by_compile": want_cz,
        "global_phase": float(qc.global_phase),
        "final_index_layout": perm,
        "final_layout_is_identity": perm is None or perm == list(range(len(perm))),
        "roundtrip_checks": checks, "roundtrip_identical": all(checks.values()),
        "dump_s": dump_s, "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }
    if want_cz is not None and want_cz != manifest["n_2q"]:
        manifest["roundtrip_identical"] = False
        manifest["count_mismatch"] = f"file has {manifest['n_2q']} CZ, compile reported {want_cz}"
    with open(transpiled_manifest_path(lat), "w") as fh:
        json.dump(_jsonable(manifest), fh, indent=1)
    print(f"  2x{lat}: {os.path.relpath(src, ROOT)} (QPY v{manifest['source_header']['qpy_version']}) "
          f"-> {os.path.relpath(dst, ROOT)} (QPY v{manifest['header']['qpy_version']}), "
          f"{manifest['n_instructions']} instructions, {manifest['n_2q']} CZ, round trip "
          f"{checks}", flush=True)
    if not manifest["roundtrip_identical"]:
        raise SystemExit("the QPY v13 file does not round-trip to the same circuit: not shipped")
    return {"stage": "qpy13", "lattice": lat, "manifest": manifest}


def _aer_metadata(res) -> dict:
    """The scalar leaves of Aer's result metadata (time taken, GPU memory, fusion, device)."""
    def scal(d):
        return {k: v for k, v in (d or {}).items()
                if isinstance(v, (int, float, str, bool)) or v is None}
    out = {}
    try:
        out["result"] = scal(getattr(res, "metadata", {}) or {})
    except Exception:                                            # pragma: no cover
        pass
    try:
        md = res.results[0].metadata
        md = md if isinstance(md, dict) else md.to_dict()
        out["experiment"] = scal(md)
        if isinstance(md.get("fusion"), dict):
            out["fusion"] = scal(md["fusion"])
    except Exception:                                            # pragma: no cover
        pass
    return out


def transpiled_job(args, lat: int, M, E) -> dict:
    """C6 on any statevector backend: the level-3 transpiled k = 1 B = 0 all-to-all circuit,
    loaded from the QPY v13 file (never re-transpiled), run by Aer with `save_amplitudes` on
    the codeword integers only (the 2^n vector never leaves the simulator), leakage
    1 - sum |amplitude|^2.  Failure to load or a count mismatch is recorded and makes the entry
    incomplete -- there is no fallback."""
    from skqd import circuits_qiskit as cq
    path, mpath = transpiled_v13_path(lat), transpiled_manifest_path(lat)
    entry = {"complete": False, "file": os.path.relpath(path, ROOT),
             "manifest": os.path.relpath(mpath, ROOT), "device": args.device,
             "no_fallback": ("if the file cannot be loaded the job fails; it does NOT "
                             "re-transpile the IR (a different qiskit gives a different "
                             "circuit from the one whose counts were reported)"),
             "phases": {}}
    try:
        with open(mpath) as fh:
            man = json.load(fh)
        entry["expected"] = {k: man[k] for k in ("sha256", "num_qubits", "n_instructions",
                                                  "n_2q", "final_index_layout")}
        sha = _sha256_file(path)
        entry["sha256"] = sha
        if sha != man["sha256"]:
            raise RuntimeError(f"sha256 {sha} != manifest {man['sha256']}")
        entry["header"] = _qpy_header(path)
        from qiskit import qpy
        t0 = time.time()
        with gzip.open(path, "rb") as fh:
            tq = qpy.load(fh)[0]
        entry["phases"]["qpy_load_s"] = time.time() - t0
        got = {"num_qubits": int(tq.num_qubits), "n_instructions": int(len(tq.data)),
               "n_2q": int(tq.count_ops().get("cz", 0))}
        entry["loaded"] = {**got, "ops": {k: int(v) for k, v in tq.count_ops().items()}}
        bad = {k: (v, man[k]) for k, v in got.items() if v != man[k]}
        if bad:
            raise RuntimeError(f"the loaded circuit differs from the manifest: {bad}")
    except Exception as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"
        print(f"  TRANSPILED JOB FAILED: {entry['error']}", flush=True)
        return entry
    ints = map_to_physical(E.ints, man["final_index_layout"])
    t0 = time.time()
    sim = cq._aer_simulator(method="statevector", device=args.device, precision="double")
    qc = tq.copy()
    qc.save_amplitudes([int(x) for x in ints])      # registered by importing qiskit_aer
    entry["phases"]["build_s"] = time.time() - t0
    t0 = time.time()
    try:
        res = sim.run(qc, shots=1).result()
        entry["phases"]["aer_run_s"] = time.time() - t0
        if not res.success:
            raise RuntimeError(f"Aer status: {getattr(res, 'status', '?')}")
        amps = np.asarray(res.data(0)["amplitudes"], dtype=complex)
    except Exception as exc:
        entry["phases"].setdefault("aer_run_s", time.time() - t0)
        entry["error"] = f"{type(exc).__name__}: {exc}"
        print(f"  TRANSPILED JOB FAILED in Aer: {entry['error']}", flush=True)
        return entry
    entry["aer_metadata"] = _aer_metadata(res)
    entry["leakage"] = float(1.0 - np.sum(np.abs(amps) ** 2))
    entry["n_2q"] = got["n_2q"]
    entry["n_instructions"] = got["n_instructions"]
    entry["s_per_instruction"] = entry["phases"]["aer_run_s"] / max(got["n_instructions"], 1)
    entry["complete"] = True
    # reported cross-checks (not criteria): the dressed-basis emulation, and at <= 20 qubits
    # the exact sparse simulation of the SAME transpiled circuit
    t0 = time.time()
    dt = dt_of(lat, 0)
    groups = term_groups(M.terms, G2, mass_default(G2))
    ref = references(M.basis, 0)[0]
    ex = coarse_states(groups, basis_vector(M.basis.dim, ref), dt, 1)[1]
    entry["max_abs_difference_vs_coarse_states"] = float(np.abs(amps - ex).max())
    ov = complex(np.vdot(ex, amps))
    entry["max_abs_difference_vs_coarse_states_phase_aligned"] = float(
        np.abs(amps * np.exp(-1j * np.angle(ov)) - ex).max()) if abs(ov) > 0 else None
    entry["phases"]["coarse_states_s"] = time.time() - t0
    if E.n <= 20:
        t0 = time.time()
        sp = run_sparse_qiskit(tq)
        sv = sp.dense_on(ints)
        entry["sparse_leakage"] = float(1.0 - np.sum(np.abs(sv) ** 2))
        entry["max_abs_difference_vs_sparse"] = float(np.abs(sv - amps).max())
        entry["phases"]["sparse_s"] = time.time() - t0
    entry["_amplitudes"] = amps
    print(f"  transpiled 2x{lat} k=1 B=0 on {args.device}: {got['n_instructions']} instructions, "
          f"{got['n_2q']} CZ, leakage {entry['leakage']:.2e}, vs coarse_states "
          f"{entry['max_abs_difference_vs_coarse_states']:.2e}, "
          f"Aer {entry['phases']['aer_run_s']:.1f} s", flush=True)
    return entry


def stage_gpu_estimate(args) -> dict:
    """The walltime estimate of the part-F job, from a MEASURED laptop rate.

    Aer (CPU, double, fusion on, all threads) runs the first `--nvec` (default 2000)
    instructions of the 2x4 v13 circuit on the full 2^28 statevector; the measured seconds per
    instruction times the full instruction count is the laptop time.  The GPU time is that
    divided by a GPU/laptop throughput factor, given as a bracket: the measured S3 GPU
    calibration speed-up (validation/S3.json, noisy sampling at 20 qubits -- a different
    workload, hence only the optimistic end) and an ASSUMED conservative floor of 20.  The
    fixed overheads (model build, QPY load) are measured here too."""
    from qiskit import QuantumCircuit, qpy

    from skqd import circuits_qiskit as cq
    n_pre = int(args.nvec) if args.nvec else 2000
    t0 = time.time()
    M = model(4)
    E = CodewordEmbedding(M)
    model_s = time.time() - t0
    t0 = time.time()
    with gzip.open(transpiled_v13_path(4), "rb") as fh:
        tq = qpy.load(fh)[0]
    load_s = time.time() - t0
    qc = QuantumCircuit(tq.num_qubits)
    for inst in tq.data[:n_pre]:
        qc.append(inst)
    sim = cq._aer_simulator(method="statevector", device="CPU", precision="double")
    qc.save_amplitudes([int(x) for x in E.ints[:16]])     # registered by importing qiskit_aer
    t0 = time.time()
    res = sim.run(qc, shots=1).result()
    run_s = time.time() - t0
    rate = run_s / n_pre
    n_all = len(tq.data)
    with open(os.path.join(ROOT, "validation", "S3.json")) as fh:
        s3 = json.load(fh)["data"]["cost"]
    s3_speedup = float(s3["reference_S2D"]["seconds_per_shot"]) / float(
        s3["seconds_per_shot_used_for_projection"])
    laptop_s = rate * n_all
    over = model_s + load_s
    out = {"stage": "gpu_estimate", "prefix_instructions": n_pre, "n_instructions": n_all,
           "laptop_aer_cpu_s_per_instruction": rate, "laptop_prefix_s": run_s,
           "laptop_full_circuit_s_projected": laptop_s,
           "aer_metadata": _aer_metadata(res),
           "overheads_measured_on_laptop_s": {"model_build": model_s, "qpy_load_v13": load_s},
           "gpu_speedup_bracket": {
               "conservative_assumed": 20.0,
               "optimistic_measured_S3": s3_speedup,
               "source_optimistic": "validation/S3.json data.cost: reference_S2D.seconds_per_"
                                    "shot / seconds_per_shot_used_for_projection (noisy "
                                    "sampling at 20 qubits, a different workload)"},
           "gpu_aer_s_projected": {"conservative": laptop_s / 20.0,
                                   "optimistic": laptop_s / s3_speedup},
           "gpu_job_s_projected": {"conservative": laptop_s / 20.0 + 2 * over + 120.0,
                                   "optimistic": laptop_s / s3_speedup + over + 60.0},
           "fixed_allowance_note": ("2 x the measured overheads + 120 s (Aer circuit "
                                    "conversion, coarse_states, the in-job assemble) on the "
                                    "conservative side; 1 x + 60 s on the optimistic side"),
           "gpu_memory_statevector_gb": (2 ** tq.num_qubits) * 16 / 1e9}
    print(f"  laptop Aer CPU: {rate:.4f} s/instruction at 2^{tq.num_qubits} "
          f"({n_pre} instructions in {run_s:.0f} s) -> {laptop_s / 3600:.1f} h for {n_all}; "
          f"GPU job projected {out['gpu_job_s_projected']['optimistic'] / 60:.0f}-"
          f"{out['gpu_job_s_projected']['conservative'] / 60:.0f} min", flush=True)
    return out


def stage_gpu(args) -> dict:
    """F -- the Perlmutter job.  `transpiled` is criterion C6 (the level-3 transpiled circuit,
    see `transpiled_job`); `coarse_step_k1` and `plaq1_on_dirac_sea` are the optional Aer
    cross-checks of the UN-transpiled IR, which criterion C5 already verified on the laptop.

    The CI runs `transpiled` only (it is the criterion, and the IR jobs would have to
    re-synthesise all 13 terms on the CI node, whose IR cache is not in the repository).  Every
    run records wall time, per-phase timings, s per instruction, the GPUs, peak GPU memory and
    mean GPU utilisation (RUNBOOK, engine and HPC policy).  At 2x4 the result is written to
    `validation/S2_2x4_gpu.json` -- the CI copies back only validation/ and reports/ -- and
    that file is what `--stage assemble` reads for C6.  At 2x2/2x3 (the laptop tests of this
    branch) the result stays in the data/S2_2x4/ fragment.
    """
    import resource
    t_all = time.time()
    lat, mode = args.lattice, args.angle_mode
    jobs = [j for j in args.gpu_jobs.split(",") if j]
    ctx = hpc.ci_context()
    out = {"stage": "gpu", "lattice": lat, "angle_mode": mode, "device": args.device,
           "jobs": jobs, "ci_context": ctx, "qiskit_versions": hpc.qiskit_versions(),
           "slurm_layout": hpc.slurm_layout(), "gpus": hpc.gpu_count(),
           "results": {}, "compiled": {}, "phases": {}}
    t0 = time.time()
    M = model(lat)
    E = CodewordEmbedding(M)
    out["phases"]["model_s"] = time.time() - t0
    amps_out = {}
    if "transpiled" in jobs:
        t0 = time.time()
        e = transpiled_job(args, lat, M, E)
        out["phases"]["transpiled_s"] = time.time() - t0
        a = e.pop("_amplitudes", None)
        if a is not None:
            amps_out["transpiled"] = a
        out["compiled"]["B0_ref0_k1|all_to_all"] = e
    ir_jobs = [j for j in jobs if j in ("coarse_step_k1", "plaq1_on_dirac_sea")]
    if ir_jobs:
        from skqd import circuits_qiskit as cq
        dt = dt_of(lat, 0)
        F = preload_factory(lat, mode, [dt]) if lat == 4 else CircuitFactory(M, G2,
                                                                             angle_mode=mode)
        ref = references(M.basis, 0)[0]
        gl = {}
        if "coarse_step_k1" in ir_jobs:
            gl["coarse_step_k1"] = F.coarse_step(ref, 1, dt)
        if "plaq1_on_dirac_sea" in ir_jobs and lat == 4:
            from skqd.krylov import dirac_sea
            init = int(E.ints[dirac_sea(M.basis)])
            gl["plaq1_on_dirac_sea"] = ([("x", [q], None) for q in range(E.n) if (init >> q) & 1]
                                        + term_ir(lat, "plaq1", mode, dt)[0])
        groups = term_groups(M.terms, G2, mass_default(G2))
        exact_ref = coarse_states(groups, basis_vector(M.basis.dim, ref), dt, 1)[1]
        for label, gates in gl.items():
            t0 = time.time()
            sparse_v = run_sparse(gates, E.n).dense_on(E.ints)
            t_sparse = time.time() - t0
            sim = cq._aer_simulator(method="statevector", device=args.device, precision="double")
            qc = cq.ir_to_qiskit(gates, E.n, measure=False)
            qc.save_amplitudes([int(x) for x in E.ints])
            t0 = time.time()
            res = sim.run(qc, shots=1).result()
            t_aer = time.time() - t0
            v = np.asarray(res.data(0)["amplitudes"], dtype=complex)
            entry = {"n_gates": len(gates), "aer_wall_s": t_aer, "sparse_wall_s": t_sparse,
                     "leakage": float(1.0 - np.sum(np.abs(v) ** 2)),
                     "max_abs_difference_vs_sparse": float(np.abs(v - sparse_v).max()),
                     "n_codewords": int(E.ints.size), "aer_metadata": _aer_metadata(res)}
            if label == "coarse_step_k1":
                entry["max_abs_difference_vs_coarse_states"] = float(np.abs(v - exact_ref).max())
            out["results"][label] = entry
            out["phases"][label] = {"aer_s": t_aer, "sparse_s": t_sparse}
            amps_out[label] = v
            print(f"  {label} on {args.device}: leakage {entry['leakage']:.2e}, vs sparse "
                  f"{entry['max_abs_difference_vs_sparse']:.2e} ({t_aer:.1f} s Aer)", flush=True)
    out["wall_s"] = time.time() - t_all
    out["peak_host_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    tel = hpc.gpu_telemetry()
    out["gpu_telemetry"] = tel
    out["telemetry_summary"] = {"wall_s": out["wall_s"], "gpus": out["gpus"],
                                "peak_gpu_memory_mib": tel.get("peak_memory_mib"),
                                "mean_gpu_utilization_pct": tel.get("mean_utilization_pct"),
                                "s_per_instruction": (out["compiled"].get(
                                    "B0_ref0_k1|all_to_all", {}).get("s_per_instruction"))}
    if lat == 4:
        full = dict(out)
        full["codeword_integers"] = [int(x) for x in E.ints]
        full["amplitudes_on_codewords"] = {
            k: {"real": [float(x) for x in np.real(v)], "imag": [float(x) for x in np.imag(v)]}
            for k, v in amps_out.items()}
        full["note"] = ("only the amplitudes projected on the codeword integers are recorded; "
                        "the 2^n statevector (4.3 GB at 28 qubits) never leaves the simulator")
        p = os.path.join(ROOT, "validation", "S2_2x4_gpu.json")
        with open(p, "w") as fh:
            json.dump(_jsonable(full), fh, indent=1)
        print(f"wrote {os.path.relpath(p, ROOT)}", flush=True)
    return out


def gpu_c6_entries(path: str):
    """(completed C6 entries, failures, summary) from the part-F result file.

    Only a 2x4 exact-mode file counts; an entry counts only if the job completed and produced a
    leakage.  An incomplete entry is returned as a failure with its recorded error, so that
    criterion C6 states WHY it has no value instead of silently ignoring the GPU run."""
    if not os.path.exists(path):
        return {}, [], None
    with open(path) as fh:
        gv = json.load(fh)
    if gv.get("lattice") != 4 or gv.get("angle_mode") != "exact":
        return {}, [], None
    ok, fail = {}, []
    for kk, vv in (gv.get("compiled") or {}).items():
        if vv.get("complete") and vv.get("leakage") is not None:
            ok[f"{kk}|aer_{gv.get('device')}"] = vv
        else:
            fail.append(f"{kk} on {gv.get('device')}: {vv.get('error')}")
    summary = {k: v for k, v in gv.items()
               if k not in ("amplitudes_on_codewords", "codeword_integers")}
    return ok, fail, summary


def pytest_attribution(node_ids: list) -> dict:
    """Do the failing tests also fail at HEAD, without this gate's changes?

    A second working tree is checked out at HEAD with `git worktree` and the same node ids are
    run there.  A test that fails in both places is not this gate's -- it belongs to whatever
    is in flight on master (this prompt ran in parallel with prompts/20) -- and saying so is a
    measurement, not an opinion.  Nothing is skipped or excused: criterion C10 still requires
    every test to pass.
    """
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="skqd_pristine_")
    wt = os.path.join(d, "tree")
    out = {"worktree": wt, "node_ids": list(node_ids)}
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
        subprocess.run(["git", "worktree", "add", "--detach", wt, head], cwd=ROOT,
                       capture_output=True, text=True, check=True)
        pr = subprocess.run([sys.executable, "-m", "pytest", "-q", *node_ids], cwd=wt,
                            capture_output=True, text=True)
        fail_here = sorted({ln.split(" ")[1] for ln in pr.stdout.splitlines()
                            if ln.startswith("FAILED ")})
        out.update({
            "head_commit": head, "returncode": pr.returncode,
            "summary": pr.stdout.strip().splitlines()[-1] if pr.stdout.strip() else "",
            "also_failing_at_head": fail_here,
            "introduced_by_this_gate": sorted(set(node_ids) - set(fail_here)),
        })
    except Exception as exc:                                     # pragma: no cover
        out["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", wt], cwd=ROOT,
                       capture_output=True, text=True)
        shutil.rmtree(d, ignore_errors=True)
    return out


# ==================================================================== assemble
def stage_assemble(args) -> int:
    t0 = time.time()
    R = GateResult("S2_2x4", "2x4 coarse step compiled to exact circuits, verified and "
                            "measured: counts, duration, idle budget and the T2/t_2q "
                            "requirement (a measurement gate: no budget criterion)")
    F = {
        "refs": read_frags("refs_"), "structure": read_frags("structure_"),
        "synth": read_frags("synth_"), "compile": read_frags("compile_"),
        "schedule": read_frags("schedule_"), "anchor": read_frags("anchor"),
        "serial": read_frags("serial"), "circuits": read_frags("circuits_"),
        "compiled": read_frags("compiled_"), "probe": read_frags("probe_"),
        "gpu_estimate": read_frags("gpu_estimate"),
        "term_compiled": read_frags("term_compiled_"),
        "dense": read_frags("dense"), "repro": read_frags("repro"),
        "gpu": read_frags("gpu_"),
    }
    missing = [k for k, v in F.items() if not v and k not in ("gpu", "compiled")]
    data = {"fragments": {k: sorted(v) for k, v in F.items()},
            "missing_fragments": missing,
            "what_pass_means": (
                "compiled, verified and measured.  PASS is NOT a statement that any device "
                "can run these circuits: this gate carries no criterion on any count, "
                "duration or coherence requirement, and the manual's Step 4.3 budget has no "
                "2x4 line."),
            "qpu_time_used_s": 0.0}

    # ---------------- C1 the E3 link
    refs = F["refs"].get("refs_4")
    if refs:
        s0, s2_ = refs["sectors"]["0"], refs["sectors"]["2"]
        worst = max(s0["dt_abs_difference"], s2_["dt_abs_difference"])
        dims_ok = (s0["dim_E3"] == 12843 and s2_["dim_E3"] == 8934)
        nref_ok = (s0["n_references"] == 11 and s2_["n_references"] == 4)
        R.add("C1 2x4 dt equals validation/E3.json (2B = 0 and 2)", worst, "<= 1e-12",
              worst <= 1e-12)
        R.add("C1 2x4 sector dimensions and reference counts",
              f"dims {s0['dim_E3']} / {s2_['dim_E3']}, refs {s0['n_references']} + "
              f"{s2_['n_references']}", "12843 / 8934, 11 + 4", dims_ok and nref_ok)
        data["refs"] = refs
    else:
        R.add("C1 2x4 E3 link", "fragment missing", "refs_4.json present", False)

    # ---------------- C2 / C3 the term circuits
    data["structure"] = {k: v for k, v in F["structure"].items()}
    syn = {}
    for frag in F["synth"].values():
        key = f"2x{frag['lattice']}|{frag['angle_mode']}"
        dst = syn.setdefault(key, {})
        for term, rec in frag["terms"].items():
            # the thetas of one term can come from several commands (plaq1 was synthesised one
            # theta at a time to stay inside the 30-minute rule), so per_theta is MERGED
            cur = dst.setdefault(term, {"per_theta": {}})
            cur["per_theta"].update(rec["per_theta"])
            for kk, vv in rec.items():
                if kk != "per_theta":
                    cur[kk] = vv
    data["synth"] = syn
    ex = syn.get("2x4|exact", {})
    fx = syn.get("2x4|fixed", {})
    # the term list comes from the structure fragment (which enumerated the 2x4 lattice), so
    # `--stage assemble` never has to rebuild Model(4)
    st4_terms = list((F["structure"].get("structure_4") or {}).get("terms", {}))
    want = set(st4_terms) or set(ex)
    data["terms_2x4"] = sorted(want)
    dev_thetas = ("dt", "2dt", "4dt")
    devs = [(t, tl, e["max_deviation"]) for t, r in ex.items()
            for tl, e in r["per_theta"].items() if tl in dev_thetas and "max_deviation" in e]
    leaks = [(m, t, tl, e["leakage"]) for m, s in (("exact", ex), ("fixed", fx))
             for t, r in s.items() for tl, e in r["per_theta"].items() if "leakage" in e]
    have_ex = set(ex) >= want
    have_fx = set(fx) >= want
    if devs and have_ex:
        wd = max(d for _t, _tl, d in devs)
        R.add("C2 max |exact term circuit - exp(-i theta h)| on the local codeword space "
              f"({len(want)} terms, theta = dt, 2dt, 4dt)", wd, "< 1e-10", wd < 1e-10)
    else:
        R.add("C2 exact term circuits", f"{len(set(ex))} of {len(want)} terms synthesised",
              f"all {len(want)} terms at theta = dt, 2dt, 4dt", False)
    if leaks and have_ex and have_fx:
        wl = max(v for _m, _t, _tl, v in leaks)
        R.add("C3 leakage of every 2x4 term circuit (exact and fixed, every theta)", wl,
              "< 1e-12", wl < 1e-12)
    else:
        R.add("C3 leakage of every 2x4 term circuit",
              f"exact {len(set(ex))}/{len(want)}, fixed {len(set(fx))}/{len(want)}",
              "every term in both modes", False)
    data["term_cost"] = {
        m: {t: {"support": r["per_theta"]["dt"]["support"],
                "ir_gates": r["per_theta"]["dt"]["ir_gates"],
                "cx": r["per_theta"]["dt"]["counts"].get("cx", 0),
                "ry": r["per_theta"]["dt"]["counts"].get("ry", 0),
                "unitary1q": r["per_theta"]["dt"]["counts"].get("unitary1q", 0),
                "n_multiplexed_rotations": r["per_theta"]["dt"]["n_multiplexed_rotations"],
                "controls": [r["per_theta"]["dt"]["controls_min"],
                             r["per_theta"]["dt"]["controls_median"],
                             r["per_theta"]["dt"]["controls_max"]],
                "controls_histogram": r["per_theta"]["dt"]["controls_histogram"],
                "real_gauge_found": r["per_theta"]["dt"]["real_gauge_found"],
                "block_rounds_fallback": r["per_theta"]["dt"]["block_rounds_fallback"],
                "synthesis_s": r["per_theta"]["dt"]["synthesis_s"],
                "max_deviation": r["per_theta"]["dt"].get("max_deviation"),
                "leakage": r["per_theta"]["dt"].get("leakage")}
            for t, r in s.items() if "dt" in r["per_theta"]}
        for m, s in syn.items()}
    for m, s in data["term_cost"].items():
        data.setdefault("ir_cx_total", {})[m] = int(sum(v["cx"] for v in s.values()))
    data["block_rounds_fallback_terms"] = sorted(
        f"{m}|{t}" for m, s in data["term_cost"].items() for t, v in s.items()
        if v["block_rounds_fallback"])
    data["real_gauge_missing_terms"] = sorted(
        f"{m}|{t}" for m, s in data["term_cost"].items() for t, v in s.items()
        if v["real_gauge_found"] is False)

    # ---------------- C4 the simulator
    data["compile"] = F["compile"]
    data["schedule"] = F["schedule"]
    data["anchor"] = F["anchor"].get("anchor")
    data["serial"] = F["serial"].get("serial")
    data["circuits"] = F["circuits"]
    data["compiled"] = F["compiled"]
    data["compiled_probe"] = F["probe"]
    data["gpu_estimate"] = F["gpu_estimate"].get("gpu_estimate")
    data["term_compiled"] = F["term_compiled"]
    data["dense"] = F["dense"].get("dense")
    data["repro"] = F["repro"].get("repro")
    data["gpu"] = F["gpu"]
    reg = []
    for frag in F["circuits"].values():
        for kk, v in frag.get("regressions", {}).items():
            reg.append((kk, v["max_abs_difference"], v["n_circuits"]))
    dense = data["dense"]
    parts = []
    ok4 = bool(reg) and all(d < 1e-13 for _k, d, _n in reg)
    if reg:
        parts.append(", ".join(f"{k} {d:.2e} ({n} circuits)" for k, d, n in reg))
    else:
        parts.append("no 2x2/2x3 regression fragment")
    if dense and dense.get("ran_dense"):
        parts.append(f"dense 2^28 {dense['term']} {dense['max_abs_difference']:.2e}")
        ok4 = ok4 and dense["max_abs_difference"] < 1e-13
    else:
        parts.append(f"dense 2^28 NOT run ({dense.get('reason') if dense else 'no fragment'})")
        ok4 = False
    R.add("C4 sparse simulator vs run_ir (2x2, 2x3) and vs the dense 2^28 cross-check",
          "; ".join(parts), "< 1e-13 each", ok4)

    # ---------------- C5 the coarse-step circuits
    cs = {}
    for frag in F["circuits"].values():
        if frag["lattice"] == 4 and frag["angle_mode"] == "exact":
            cs.update(frag.get("coarse_steps", {}))
    if len(cs) >= len(CIRCUITS_2x4):
        wd = max(v["max_deviation_vs_coarse_states"] for v in cs.values())
        wl = max(abs(v["leakage"]) for v in cs.values())
        R.add(f"C5 the {len(cs)} 2x4 coarse-step circuits vs krylov.coarse_states "
              "(max |delta| on the codewords)", wd, "< 1e-10", wd < 1e-10)
        R.add("C5 leakage of the 2x4 coarse-step circuits", wl, "< 1e-12", wl < 1e-12)
    else:
        R.add("C5 the 2x4 coarse-step circuits vs krylov.coarse_states",
              f"{len(cs)} of {len(CIRCUITS_2x4)} simulated",
              f"all {len(CIRCUITS_2x4)}", False)
        R.add("C5 leakage of the 2x4 coarse-step circuits", "not computed", "< 1e-12", False)

    # ---------------- C6 the compiled circuit
    comp = {}
    for frag in list(F["circuits"].values()) + list(F["compiled"].values()):
        if frag["lattice"] == 4 and frag["angle_mode"] == "exact":
            comp.update({kk: vv for kk, vv in frag.get("compiled", {}).items()
                         if vv.get("complete", True)})
    # the Perlmutter result (part F): validation/S2_2x4_gpu.json, which the CI copies back
    g_ok, gpu_fail, g_summary = gpu_c6_entries(os.path.join(ROOT, "validation",
                                                           "S2_2x4_gpu.json"))
    comp.update(g_ok)
    if g_summary is not None:
        data["gpu_validation"] = g_summary
    if comp:
        wl = max(abs(v["leakage"]) for v in comp.values())
        R.add("C6 leakage of the level-3 all-to-all transpiled 2x4 k = 1 B = 0 circuit "
              "(sparse statevector)", wl, "< 1e-9", wl < 1e-9)
    else:
        pr = {}
        for frag in F["probe"].values():
            pr.update(frag.get("circuits", {}))
        note = "not computed"
        if pr:
            v = list(pr.values())[0]
            g = v["growth"][-1]
            note = (f"not computable on this machine: the sparse support of the level-3 "
                    f"transpiled circuit reaches {g['max_support']} "
                    f"({g['amplitude_array_mb']:.0f} MB of amplitudes) after "
                    f"{g['instructions']} of {v['n_instructions']} instructions in "
                    f"{g['wall_s']:.0f} s")
        if gpu_fail:
            note += "; the GPU job did not complete: " + "; ".join(gpu_fail)
        R.add("C6 leakage of the level-3 all-to-all transpiled 2x4 k = 1 B = 0 circuit "
              "(sparse statevector)", note, "< 1e-9", False)

    # ---------------- C7 the 2x2 anchor
    a = data["anchor"]
    if a:
        m = a["canary_2x2"]["max_relative_difference"]
        R.add("C7 the frozen 2x2 canary on the real ibm_fez record reproduces T_s, S_T1, S_T2 "
              "of data/S2_duration_compare.json", m, "<= 1e-9 relative", m <= 1e-9)
    else:
        R.add("C7 the frozen 2x2 canary anchor", "fragment missing", "<= 1e-9 relative", False)

    # ---------------- C8 the serial formula
    s = data["serial"]
    if s:
        R.add("C8 serial_bound on the committed counts reproduces 667.1, 1727.6, 9372.1, "
              "23786.3, 7035.6", s["max_abs_difference"], "<= 0.1",
              s["max_abs_difference"] <= 0.1)
    else:
        R.add("C8 the serial formula", "fragment missing", "<= 0.1", False)

    # ---------------- C9 the S2 reproduction
    rp = data["repro"]
    if rp:
        nd = sum(v.get("n_differences", 1) for v in rp["runs"].values())
        att = rp.get("differences_not_caused_by_this_change", [])
        val = (f"CZ/per-term counts identical: {rp.get('cz_counts_identical')}; "
               f"HEAD circuits_ir identical to the modified one: "
               f"{rp.get('pristine_vs_modified', {}).get('identical')}; "
               f"{nd} difference(s) against the committed JSON over all A3 keys"
               + (f" ({'; '.join(d['key'] + ' ' + str(d['committed']) + ' -> ' + str(d['reproduced']) for d in att)})" if att else ""))
        R.add("C9 validation/S2.json and S2_fixed.json counts reproduced identically after "
              "the circuits_ir change", val,
              "every CZ / per-term count identical and HEAD's circuits_ir bit-for-bit "
              "identical to the modified one", bool(rp["identical"]))
    else:
        R.add("C9 the S2 / S2_fixed reproduction", "fragment missing", "0 differences", False)

    # ---------------- C10 pytest
    if getattr(args, "tests_from_record", False):
        prev = None
        vpath = os.path.join(ROOT, "validation", "S2_2x4.json")
        if os.path.exists(vpath):
            with open(vpath) as fh:
                old_rec = json.load(fh)
            prev = next((c for c in old_rec["criteria"] if c["name"].startswith("C10")), None)
        if prev is None:
            R.add("C10 pytest -q tests", "no committed record to carry over", "all pass", False)
        else:
            env = old_rec.get("environment", {})
            R.add("C10 pytest -q tests",
                  f"{prev['value']} (carried over from the committed laptop record of "
                  f"{env.get('timestamp')} at commit {env.get('git_commit')}; pytest is not "
                  f"re-run on the CI GPU node)", "all pass", bool(prev["passed"]))
            data["pytest"] = prev["value"]
            data["pytest_source"] = "carried over from the committed validation/S2_2x4.json"
    elif args.no_tests:
        R.add("C10 pytest -q tests", "not run (--no-tests)", "all pass", False)
    else:
        tp = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT,
                            capture_output=True, text=True)
        line = tp.stdout.strip().splitlines()[-1] if tp.stdout.strip() else "no output"
        failing = sorted({ln.split(" ")[1] for ln in tp.stdout.splitlines()
                          if ln.startswith("FAILED ")})
        data["pytest"] = line
        data["pytest_failing"] = failing
        if failing:
            data["pytest_attribution"] = pytest_attribution(failing)
        R.add("C10 pytest -q tests", line, "all pass", tp.returncode == 0)

    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report("S2_2x4_compilation_and_device_requirement.md", report_text(R, data))
    print(R.criteria_table())
    return 0 if R.passed else 1


# ==================================================================== report
def _fmt(v, nd=3):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        if v == 0:
            return "0"
        if abs(v) < 1e-3 or abs(v) >= 1e5:
            return f"{v:.{nd}e}"
        return f"{v:.{nd}g}"
    return str(v)


def report_text(R, d) -> str:
    tc = d.get("term_cost", {})
    ex4 = tc.get("2x4|exact", {})
    fx4 = tc.get("2x4|fixed", {})
    ex3 = tc.get("2x3|exact", {})
    st4 = d.get("structure", {}).get("structure_4", {})
    st3 = d.get("structure", {}).get("structure_3", {})
    names4 = list(st4.get("terms", {})) or sorted(ex4)
    names3 = list(st3.get("terms", {})) or sorted(ex3)
    rows = []
    for t in (names4 if ex4 else []):
        e = ex4.get(t, {})
        f = fx4.get(t, {})
        s = st4.get("terms", {}).get(t, {})
        rows.append([t, s.get("support"), s.get("local_states"), s.get("blocks"),
                     s.get("largest_block"), e.get("ir_gates"), e.get("cx"),
                     e.get("n_multiplexed_rotations"),
                     "/".join(_fmt(x) for x in e.get("controls", [])),
                     f.get("cx"), _fmt(e.get("synthesis_s"), 2),
                     _fmt(e.get("max_deviation")), _fmt(e.get("leakage"))])
    rows3 = []
    for t in (names3 if ex3 else []):
        e = ex3.get(t, {})
        s = st3.get("terms", {}).get(t, {})
        rows3.append([t, s.get("support"), s.get("local_states"), s.get("blocks"),
                      s.get("largest_block"), e.get("ir_gates"), e.get("cx"),
                      e.get("n_multiplexed_rotations"), _fmt(e.get("max_deviation"))])
    # coarse-step counts per map
    seen = {}
    for name, frag in sorted(d.get("compile", {}).items()):
        lat, mode = frag["lattice"], frag["angle_mode"]
        for tag, c in sorted(frag.get("circuits", {}).items()):
            for mp, cc in sorted(c["maps"].items()):
                # "|" would break the markdown table: the map key carries the measure variant
                label = mp.replace("|measured", " + measure layer")
                key = (lat, mode, tag, label)
                row = [f"2x{lat}", mode, tag, label, c["ir_gates"], cc["n_2q"],
                       cc["n_1q"], cc["depth"], cc["cz_depth"],
                       cc["n_qubits_mapped"], cc["n_active_qubits"],
                       _fmt(cc.get("transpile_s"), 2)]
                if key not in seen or cc.get("transpile_s") is not None:
                    seen[key] = row
    crows = [seen[k] for k in sorted(seen)]
    # requirement table
    rrows = []
    for key, row in sorted(d.get("schedule", {}).items()):
        for k2, r in sorted(row.get("rows", {}).items()):
            for t1q in ("t_1q=heron", "t_1q=zero"):
                q = r.get(t1q)
                if not q:
                    continue
                for f in F_TARGETS:
                    for mode in ("inf", "equal"):
                        e = q["requirements"][f"f={f}|T1={mode}"]
                        rrows.append([k2.replace("|", " / "), t1q.split("=")[1], f, mode,
                                      r["n_2q"],
                                      _fmt(q["T_s"]), _fmt(q["seriality"]),
                                      _fmt(q["qubit_time_utilisation"]),
                                      _fmt(q["idle_total_s"]), q["n_windows"],
                                      _fmt(e["T2_req_over_t_2q"], 4),
                                      _fmt(e["serial_bound_T2_over_t_2q"], 4),
                                      _fmt(e.get("serial_bound_logical_T2_over_t_2q"), 4),
                                      _fmt(e["measured_over_serial"])])
    srows = []
    for r in (d.get("serial") or {}).get("rows", []):
        srows.append([r["circuit"], r["n_qubits"], r["n_2q"], _fmt(r["serial_bound"], 5),
                      r["owner_value"], r["source"]])
    for r in (d.get("serial") or {}).get("extra_rows", []):
        srows.append([r["circuit"], r["n_qubits"], r["n_2q"], _fmt(r["serial_bound"], 5),
                      "-", r["source"]])
    a = d.get("anchor") or {}
    her = a.get("heron_r2_record", {})
    hrow = []
    if her:
        o = her["T2_over_t_2q"]
        hrow = [["Heron r2, the 12 canary qubits", _fmt(her["T2_mean_s"]),
                 _fmt(her["T2_harmonic_mean_s"]), _fmt(her["T2_max_s"]),
                 _fmt(her["T2_min_s"]), _fmt(o["arithmetic_mean"], 4),
                 f"**{_fmt(o['harmonic_mean'], 4)}**", _fmt(o["best_qubit"], 4),
                 _fmt(o["worst_qubit"], 4)]]
    djrows = []
    for nm, frag in sorted(d.get("structure", {}).items()):
        djrows.append([f"2x{frag['lattice']}", frag["n_terms_hop_plaq"], frag["n_pairs"],
                       frag["n_disjoint_pairs"], _fmt(frag["disjoint_fraction"]),
                       f"{frag['n_disjoint_pairs_including_diag']} of "
                       f"{frag['n_pairs_including_diag']}",
                       frag["chromatic_number_overlap_graph"], frag["serial_rounds"]])
    prows = []
    for key, row in sorted(d.get("schedule", {}).items()):
        for k2, r in sorted(row.get("rows", {}).items()):
            q = r.get("t_1q=heron")
            if not q:
                continue
            pb = q["packing_bound"]
            prows.append([k2.replace("|", " / "), _fmt(q["T_s"]), _fmt(pb["T_min_s"]),
                          _fmt(pb["speedup_available"]), _fmt(q["idle_total_s"]),
                          _fmt(pb["idle_total_packed_s"]), _fmt(q.get("S_T2_at_record")),
                          _fmt(pb["S_T2_packed"])])
    grows = []
    for key, row in sorted(d.get("schedule", {}).items()):
        for k2, r in sorted(row.get("rows", {}).items()):
            go = r.get("gate_only_requirement", {})
            for f in F_TARGETS:
                g = go.get(str(f))
                if not g:
                    continue
                bs = g["budget_shares_at_declared"]
                grows.append([k2.replace("|", " / "), f, r["n_2q"], r["n_1q"],
                              r["n_measure"],
                              _fmt(g["eps2_alone"]), _fmt(g["eps2_at_declared_eps1_eps_ro"]),
                              _fmt(g["eps2_at_declared_virtual_rz"]),
                              _fmt(bs["total"]), _fmt(bs["budget_log"]),
                              _fmt(bs["over_budget_by"])])
    fez = (a.get("fakefez_rows") or {})
    frows = [[k.replace("|", " / "), v["n_cz"], _fmt(v["f_gates"]), _fmt(v["T_s"]),
              _fmt(v["S_T1"]),
              _fmt(v["S_T2"]), _fmt(v["S_idle"]), _fmt(v["f_idle_aware"]),
              _fmt(v["coherence_scale_for_f_0.1"]),
              _fmt(v["coherence_only_scale_for_f_0.1"], 4),
              _fmt(v["coherence_only_scale_for_f_0.05"], 4)]
             for k, v in sorted(fez.items())]
    dense = d.get("dense") or {}
    vrows = []
    for m, s in sorted(tc.items()):
        for t, v in sorted(s.items()):
            vrows.append([m, t, v["support"], _fmt(v.get("max_deviation")),
                          _fmt(v.get("leakage")), _fmt(v["real_gauge_found"]),
                          _fmt(v["block_rounds_fallback"])])
    cs4 = {}
    for frag in d.get("circuits", {}).values():
        if frag.get("lattice") == 4 and frag.get("angle_mode") == "exact":
            cs4.update(frag.get("coarse_steps", {}))
    csrows = [[k.replace("|", " / "), v["ir_gates"],
               _fmt(v["max_deviation_vs_coarse_states"]),
               _fmt(v["leakage"]), v["sparse_max_support"], _fmt(v["sparse_wall_s"], 3),
               _fmt(v["emulation_wall_s"], 3)] for k, v in sorted(cs4.items())]
    comp4 = {}
    for frag in list(d.get("circuits", {}).values()) + list(d.get("compiled", {}).values()):
        if frag.get("angle_mode") == "exact":
            comp4.update({f"2x{frag.get('lattice')}|{kk}": vv
                          for kk, vv in frag.get("compiled", {}).items()})

    return f"""# Gate S2_2x4 — the 2x4 coarse step compiled, verified, and its device requirement

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/gate_S2_2x4.py`, optimization level {LEVEL},
basis {{rz, sx, x, cz}}, seed {SEED}, g2 = {G2}.  {env_block()}  Assemble runtime {R.runtime_s:.0f} s.
**0 QPU seconds.**  Every number below comes from `validation/S2_2x4.json`, which this script wrote
from the stage fragments in `data/S2_2x4/`.

## What PASS means

{d['what_pass_means']}

The owner asked what a device must deliver to run 2x3 and 2x4.  At 2x3 the answer existed
(`data/S2D_2x3_device_requirements.json`); at 2x4 it did not, because the circuits had never been
compiled and the "above 1e5" figure was an extrapolation from two points.  This gate compiles them,
verifies them at the gate-S2 standard and measures the requirement.  It does not say whether any
device meets it.

## The gating question: does the structured engine reach 2x4?

Yes, with no code change to the construction.  `plaq1`, the middle plaquette, acts on
{st4.get('terms', {}).get('plaq1', {}).get('support', '-')} qubits (four interior corners,
{st4.get('terms', {}).get('plaq1', {}).get('local_states', '-')} local codewords,
{st4.get('terms', {}).get('plaq1', {}).get('blocks', '-')} blocks, the largest with
{st4.get('terms', {}).get('plaq1', {}).get('largest_block', '-')} configurations of degree
{st4.get('terms', {}).get('plaq1', {}).get('max_degree', '-')}), and `hop3`/`hop5` are an
interior-to-interior x-link type that does not exist at 2x3.  Every block of every term has a zero
diagonal (`diag_nonzero` false throughout), which is the premise of the bipartite singular-value
construction of `circuits_ir._block_rounds`; the diagonal gauge of `_real_gauge` made every block
generator real, so every rotation is an Ry.  Terms that needed the generic `expm` fallback of
`_block_rounds`: **{d.get('block_rounds_fallback_terms') or 'none'}**.  Terms without a real gauge:
**{d.get('real_gauge_missing_terms') or 'none'}**.  The 16-qubit support decides cost and synthesis
time, not correctness: the dense local unitary of a 16-qubit support is 2^32 complex entries (68 GB)
and was never built — term verification uses the small block `h` of `reference_sim.localize` and
`circuits_ir.run_ir` on the 2^16 local statevector (1 MB).

## Per-term cost and verification at 2x4 (exact, theta = dt), with the fixed-angle column beside it

{md_table(["term", "support", "local states", "blocks", "largest block", "IR gates", "cx",
           "multiplexed rotations", "controls min/med/max", "fixed-angle cx", "synthesis (s)",
           "max deviation", "leakage"], rows)}

Sum of the IR `cx` over the {len(names4)} hop/plaquette terms:
**{d.get('ir_cx_total', {}).get('2x4|exact', '-')}** exact,
{d.get('ir_cx_total', {}).get('2x4|fixed', '-')} fixed-angle (the diagonal term adds a few tens
and the transpiler then merges across term boundaries, so the coarse-step count below is not
this sum).

### The same table at 2x3, for scale

{md_table(["term", "support", "local states", "blocks", "largest block", "IR gates", "cx",
           "multiplexed rotations", "max deviation"], rows3)}

Sum of the IR `cx` over the {len(names3)} 2x3 hop/plaquette terms:
{d.get('ir_cx_total', {}).get('2x3|exact', '-')}.

## Coarse-step counts per coupling map

{md_table(["lattice", "family", "circuit", "map", "IR gates", "2q gates", "1q gates", "depth",
           "CZ depth", "mapped qubits", "active qubits", "transpile (s)"], crows)}

Structure identity (does the transpiled count depend on the reference or on k?):
`{json.dumps({f"{k}|{kk}": {x: y for x, y in vv.items() if x != 'per_circuit_n_2q'}
              for k, v in d.get('compile', {}).items()
              for kk, vv in (v.get('structure_identity') or {}).items()})}`

Like-for-like with gate S2 (the same circuit, transpiler settings and map must give back the
committed counts at 2x2 and 2x3):
`{json.dumps({k: v.get('like_for_like_vs_gate_S2') for k, v in d.get('compile', {}).items()
              if v.get('like_for_like_vs_gate_S2')})}`

## Duration, idle budget and the coherence requirement

Schedules are ASAP (`skqd.idle.schedule_asap`) on a **uniform** record
(`skqd.coherence.uniform_record`) at the Heron r2 durations of
`data/hardware/H0_diag_prep/calibration_20260922T1400Z.json` (cz 68 ns, sx and x 24 ns, measure
1.66 us, dt 4 ns), and again with t_1q = 0, which is the serial formula's premise.  `T2_req` is
solved by bisection so that the idle budget of `skqd.idle` equals ln(1/f_target) exactly.

{md_table(["circuit", "t_1q", "f_target", "T1 convention", "2q gates", "T (s)", "seriality",
           "qubit-time utilisation", "total idle (s)", "idle windows", "T2/t_2q measured",
           "T2/t_2q serial (active qubits)", "T2/t_2q serial (logical qubits)",
           "measured / formula"], rrows)}

### The serial formula on the committed counts (criterion C8)

{md_table(["circuit", "n", "n_2q", "T2/t_2q", "owner's value", "source"], srows)}

### What a real device has, for comparison

{md_table(["record", "T2 mean (s)", "T2 harmonic mean (s)", "T2 best (s)", "T2 worst (s)",
           "T2/t_cz mean", "T2/t_cz harmonic", "T2/t_cz best", "T2/t_cz worst"], hrow)}

Which statistic: {her.get('which_statistic', '')}.  The harmonic mean is therefore the headline
comparison statistic here and the other three are reported beside it; the owner's "1912 on the
patch that flew" is not any statistic of this record and is not used.

### The FakeFez full-device reading (a real per-qubit record, not a uniform one)

{md_table(["circuit", "CZ", "f_gates", "T (s)", "S_T1", "S_T2", "S_idle", "f idle-aware",
           "coherence scale for mean f >= 0.1", "coherence-only scale (f = 0.1)",
           "coherence-only scale (f = 0.05)"], frows) if frows else '(not computed)'}

A `None` in the coherence-scale column means the gate and readout errors of the record alone
already put f below the target, so no amount of coherence reaches it; the coherence-ONLY column
(every gate and readout error set to zero, durations and coherence times kept) always exists and is
the like-for-like reading against the 5.51x that `validation/S2D_idle.json` records at 2x2.

## The gate-only requirement (part C: the same criterion with zero idle time)

The criterion is one half-space, n_2q eps2~ + n_1q eps1~ + n_meas eps_ro~ + S_idle <= ln(1/f_target)
(`skqd.device_req.target_with_idle`); the T2/t_2q number above is its coherence-only face and the
table below is its gate face at S_idle = 0.

{md_table(["circuit", "f_target", "n_2q", "n_1q", "n_meas", "eps2 alone",
           "eps2 at declared eps1/eps_ro", "eps2 with virtual rz", "log budget spent",
           "log budget available", "over budget by"], grows)}

Declared inputs: eps1 = {DECLARED['eps1']}, eps_ro = {DECLARED['eps_ro']}
(`data/S2D_2x3_device_requirements.json` feasible_region.declared_inputs).  A `-` in the
"eps2 at declared" column is the honest answer that the one-qubit and readout channels alone already
exhaust the budget, so no two-qubit error rate satisfies the criterion.

## Disjointness, colouring and the packing bound

{md_table(["lattice", "terms (hop+plaq)", "pairs", "disjoint pairs", "fraction",
           "disjoint incl. diag", "chromatic number of the overlap graph", "serial rounds"],
          djrows)}

Nearly half the term pairs at 2x4 commute trivially and the overlap graph is 6-colourable, so a
coarse step could in principle run in 6 rounds of mutually disjoint term gates instead of
{st4.get('serial_rounds', '-')} serial ones.  **Term reordering is not evaluated here**: the order of
the groups in `krylov.term_groups` / `CircuitFactory.coarse_step` is a convention of this package
that the emulated recall of gates S1 and S2_fixed was established on, so changing it is a method
decision with a recall re-emulation, not a compilation option.  What is measured is the schedule's
own packing bound — no reordering of the same gates on the same layout can finish before
T_min = max_q busy_q, and the perfectly packed schedule (one idle window per qubit) is a rigorous
lower bound on the PTA budget at equal charged idle time because 1 - e^{{-w/T}} is concave.  The
S_T2 columns are read at the uniform record's own T2 (1e-4 s).  One caveat the numbers make
visible: `skqd.idle.schedule_asap` opens a window only BETWEEN instructions, so the time a qubit
sits idle after its own last gate is in `idle_s` but is not a window and costs nothing in the PTA
budget, while the packed schedule charges the full T_min - busy_q -- so the packed S_T2 can come
out ABOVE the ASAP one where T_min is close to T.  The duration bound T_min <= T is unconditional.

{md_table(["circuit", "T (s)", "T_min (s)", "speedup available", "total idle now (s)",
           "total idle packed (s)", "S_T2 now", "S_T2 packed"], prows)}

## Verification detail

{md_table(["family", "term", "support", "max deviation", "leakage", "real gauge found",
           "block-rounds fallback"], vrows)}

Full coarse-step circuits against the dressed-basis emulation `krylov.coarse_states`, through the
exact sparse statevector simulator `skqd.sparse_sim`:

{md_table(["circuit", "IR gates", "max |delta| on the codewords", "leakage",
           "sparse max support", "sparse (s)", "emulation (s)"], csrows)}

### The compiled circuit at 28 qubits (criterion C6)

Gate S2 checks the leakage of the level-3 transpiled coarse step on the full statevector at
2x2 and 2x3.  **At 2x4 that check does not fit on this machine, and the reason is measured
rather than argued.**  Level 3 collects and re-synthesises two-qubit blocks, which destroys the
property that makes the IR circuit sparse -- inside a multiplexed rotation the IR touches ONE
target qubit, while a KAK block rotates both of its qubits -- so the exact sparse support of
the transpiled circuit grows past the 2^18 of the IR circuit:

{md_table(["fraction of the circuit", "instructions", "sparse support", "amplitudes (MB)",
           "wall (s)"],
          [[f"{r['fraction'] * 100:.1f} %", r["instructions"], r["support"],
            _fmt(r["amplitude_array_mb"], 3), _fmt(r["wall_s"], 3)]
           for v in (d.get("compiled_probe") or {}).values()
           for c in v.get("circuits", {}).values() for r in c["growth"]])
 if d.get("compiled_probe") else "(not measured)"}

A first attempt ran the whole circuit and was stopped at the 30-minute laptop rule; the staged
re-run above shows why: at 4 % of the instructions the support is already 33.5 million
amplitudes and one gate costs of order a second.  The same measurement at **2x3** settles what
is happening: there the transpiled coarse step runs to the end in 101 s and is leak-free, and
its sparse support saturates at 1048576 = 2^20, i.e. the **whole** 20-qubit Hilbert space.  A
level-3 transpiled coarse step is therefore not a sparse object at all: checking it is a DENSE
statevector simulation, which is 2^20 amplitudes (16 MB) at 2x3 and 2^28 (4.3 GB) at 2x4.  With
`circuits_ir.run_ir` at 0.7-3.8 s per gate on 2^28 (planner P4) and 2.8e5 instructions, that is
of order 100 hours on this CPU whichever representation is used.
**This is what part F (the Perlmutter Aer-GPU cross-check) exists for**: on one A100 the same
28-qubit statevector is 4.3 GB and Aer's fused kernels run it in minutes.  The branch is
written and tested on the laptop at 2x2 (`--stage gpu --lattice 2 --device CPU`:
`{json.dumps({k: {kk: vv for kk, vv in (v.get('results') or {}).get('coarse_step_k1', {}).items() if kk.startswith(('leak', 'max_abs'))} for k, v in (d.get('gpu') or {}).items()})}`);
the proposed allowlist line is `S2_2x4 01:00:00 1`.  Walltime estimate (`--stage gpu_estimate`):
`{json.dumps({k: v for k, v in (d.get("gpu_estimate") or {}).items() if k in ("laptop_aer_cpu_s_per_instruction", "n_instructions", "laptop_full_circuit_s_projected", "gpu_speedup_bracket", "gpu_job_s_projected", "gpu_memory_statevector_gb")})}`.

**Perlmutter result** (`validation/S2_2x4_gpu.json`, written by `--stage gpu` from the QPY
version-13 copy of the transpiled circuit, never re-transpiled):
{(lambda g: ("`" + json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("complete", "leakage", "error", "n_2q", "n_instructions", "s_per_instruction", "max_abs_difference_vs_coarse_states", "phases")} for k, v in (g.get("compiled") or {}).items()}) + "` on " + str(g.get("device")) + ", telemetry `" + json.dumps(g.get("telemetry_summary")) + "`") if g else "not yet run (the CI token `S2_2x4` is not on the allowlist).")(d.get("gpu_validation"))}

What IS measured here instead -- a reported number, not criterion C6 -- is the leakage of the
level-3 transpiled **term gates**, each on its own support (k <= 16 qubits), through the same
exact simulator from a random superposition of that term's local codewords:

{md_table(["term", "support", "transpiled CZ", "instructions", "depth", "leakage",
           "deviation from exp(-i theta h)", "vectors"],
          [[t, v["support"], v["n_2q"], v["n_instructions"], v["depth"], _fmt(v["leakage"]),
            _fmt(v["max_deviation"]), v["n_vectors"]]
           for frag in (d.get("term_compiled") or {}).values()
           for t, v in sorted(frag.get("terms", {}).items())])
 if d.get("term_compiled") else "(not measured)"}

Leakage of the level-3 all-to-all transpiled coarse step where it WAS computable
(2x2 and 2x3 in this gate's own run, and the 2x4 entry if a completed segment exists):
`{json.dumps(comp4)}`

The simulator itself is regressed against `circuits_ir.run_ir`:
`{json.dumps({k: v.get('regressions') for k, v in d.get('circuits', {}).items() if v.get('regressions')})}`
and against one dense 2^28 `run_ir` of the smallest 2x4 term
(`{dense.get('term', '-')}`, {dense.get('ir_gates', '-')} gates, MemAvailable
{_fmt(dense.get('mem_available_gb'))} GB): max |delta|
{_fmt(dense.get('max_abs_difference'))}{'' if dense.get('ran_dense') else ' — ' + str(dense.get('reason'))}.

`validation/S2.json` and `validation/S2_fixed.json` were re-run after the additive
`circuits_ir` change (the Walsh-Hadamard angle transform above 10 controls, which no 2x2 or 2x3 gate
list reaches) and reproduce their committed counts:
`{json.dumps({k: {'n_differences': v.get('n_differences'), 'identical': v.get('identical')} for k, v in (d.get('repro') or {}).get('runs', {}).items()})}`
and the one key that differs is attributed by running HEAD's own `circuits_ir` beside the
modified one:
`{json.dumps((d.get('repro') or {}).get('differences_not_caused_by_this_change'))}`
`{json.dumps({k: v['identical'] for k, v in ((d.get('repro') or {}).get('pristine_vs_modified') or {}).get('rows', {}).items()})}`

## Test suite

`pytest -q tests`: {d.get('pytest', '(not run)')}.
{("Failing: `" + "`, `".join(d.get("pytest_failing", [])) + "`.  Re-run at HEAD in a second "
  "`git worktree` without any of this gate's changes: also failing there `"
  + "`, `".join((d.get("pytest_attribution") or {}).get("also_failing_at_head", []))
  + "`; introduced by this gate `"
  + "`, `".join((d.get("pytest_attribution") or {}).get("introduced_by_this_gate", []) or ["(none)"])
  + "`.") if d.get("pytest_failing") else "All tests pass."}

## Honest limits

- The gate says what the 2x4 circuits cost and what coherence they need; it does not say whether
  any device meets it.
- The requirement is a PTA bound on a uniform record (`skqd.idle` is a bound, prompts/20 M-A),
  quoted as a ratio T2/t_2q; the T2 convention (Hahn-echo vs in-circuit T2*) is the vendor's to
  declare (amendment 01 item 2), and a real device is a per-qubit sum, for which the coherence-scale
  number on the FakeFez record is the like-for-like reading.
- The fixed-angle rows are a cost floor: that generator's recall is established at 2x3 only.
- The 6-round packing and the two compilation levers named in
  `reports/S2_2x4_planner_analysis_20260930.md` (control minimisation above m = 10 control bits;
  star-block diagonalisation) are measured or named, not spent.
- The 2x4 hardware run is "optional" in the manual (Step 10 row 5); nothing here changes the
  hardware programme.

## Criteria

{R.criteria_table()}
"""


# ==================================================================== driver
def build_parser(ci: dict = None) -> argparse.ArgumentParser:
    """The command line, with the CI defaults applied when `ci` is non-empty.

    The Perlmutter CI runs `python scripts/run_gate.py S2_2x4` with NO arguments, so under the
    CI (`skqd.hpc.ci_context()` non-empty, the pattern of gates L4 and S3) the defaults become
    the GPU job of criterion C6 -- `--stage gpu --device GPU --lattice 4 --gpu-jobs transpiled`
    -- followed by `--stage assemble` with C10 carried over from the committed laptop record
    (`--tests-from-record`), so that the run leaves a coherent validation/S2_2x4.json for
    run_gate.py's status line.  Any explicit flag still wins; on the laptop nothing changes.
    Split out of `main` so the CI defaults are testable without a GPU
    (tests/test_s2_2x4_ci_mode.py)."""
    ci = hpc.ci_context() if ci is None else ci
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="gpu" if ci else "assemble",
                    choices=("refs", "structure", "synth", "compile", "schedule", "anchor",
                             "serial", "circuits", "compiled", "probe", "term_compiled",
                             "dense", "repro", "qpy13", "gpu", "gpu_estimate",
                             "assemble"))
    ap.add_argument("--lattice", type=int, default=4, choices=(2, 3, 4))
    ap.add_argument("--angle-mode", default="exact", choices=("exact", "fixed"))
    ap.add_argument("--only", default=None, help="comma-separated terms (or circuit tags)")
    ap.add_argument("--maps", default=None, help="comma-separated coupling-map names")
    ap.add_argument("--circuits", default=None,
                    help="comma-separated circuit tags (B0_ref0_k1, B0_ref0_k4, B0_ref1_k1, "
                         "B1_ref0_k1); default all four")
    ap.add_argument("--measure", default="0,1",
                    help="which measure variants to transpile: 0 (counts, S2-comparable), "
                         "1 (with the measure layer, used by --stage schedule)")
    ap.add_argument("--thetas", default="dt,2dt,4dt",
                    help="comma-separated theta labels: dt, 2dt, 4dt, dtB1")
    ap.add_argument("--tag", default=None, help="fragment name suffix")
    ap.add_argument("--nvec", type=int, default=0, help="override the random-vector count")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--force", action="store_true", help="resynthesise, ignoring the IR cache")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--no-per-term", action="store_true")
    ap.add_argument("--no-regression", action="store_true")
    ap.add_argument("--no-compiled", action="store_true")
    ap.add_argument("--cap-s", dest="cap_s", type=float, default=600.0,
                    help="wall-clock cap of --stage probe")
    ap.add_argument("--nseg", type=int, default=1, help="segments of --stage compiled")
    ap.add_argument("--seg", type=int, default=0, help="which segment (0-based)")
    ap.add_argument("--no-coarse", action="store_true",
                    help="skip the coarse-step sparse simulation (C5), keep the compiled one")
    ap.add_argument("--no-fakefez", action="store_true")
    ap.add_argument("--no-plaq1", action="store_true")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--tests-from-record", action="store_true", default=bool(ci),
                    help="assemble: carry C10 over from the committed validation/S2_2x4.json "
                         "instead of running pytest (the CI default; clearly labelled)")
    ap.add_argument("--then-assemble", action="store_true", default=bool(ci),
                    help="after --stage gpu, run --stage assemble (the CI default)")
    ap.add_argument("--gpu-jobs", default="transpiled" if ci else "transpiled,coarse_step_k1",
                    help="comma-separated jobs of --stage gpu: transpiled (criterion C6), "
                         "coarse_step_k1, plaq1_on_dirac_sea (IR cross-checks)")
    ap.add_argument("--no-model", action="store_true",
                    help="assemble without building Model(4) (term names are hard-coded)")
    ap.add_argument("--fez-lattices", default="4")
    ap.add_argument("--dense-term", default="hop1")
    ap.add_argument("--device", default="GPU" if ci else "CPU", choices=("CPU", "GPU"))
    ap.add_argument("--t-2q", dest="t_2q", type=float, default=coh.HERON_T_2Q)
    ap.add_argument("--t-1q", dest="t_1q", type=float, default=coh.HERON_T_1Q)
    ap.add_argument("--t-ro", dest="t_ro", type=float, default=coh.HERON_T_RO)
    ap.add_argument("--T1", type=float, default=1e-3)
    ap.add_argument("--T2", type=float, default=1e-4)
    return ap


def main(argv=None):
    ci = hpc.ci_context()
    args = build_parser(ci).parse_args(argv)
    if ci:
        print(f"CI run ({', '.join(f'{k}={v}' for k, v in ci.items())}): stage {args.stage}, "
              f"device {args.device}, jobs {args.gpu_jobs}, then assemble {args.then_assemble}",
              flush=True)

    if args.stage == "assemble":
        return stage_assemble(args)
    fn = {"refs": stage_refs, "structure": stage_structure, "synth": stage_synth,
          "compile": stage_compile, "schedule": stage_schedule, "anchor": stage_anchor,
          "serial": stage_serial, "circuits": stage_circuits, "dense": stage_dense,
          "compiled": stage_compiled, "probe": stage_probe,
          "term_compiled": stage_term_compiled, "qpy13": stage_qpy13,
          "gpu_estimate": stage_gpu_estimate,
          "repro": stage_repro, "gpu": stage_gpu}[args.stage]
    t0 = time.time()
    payload = fn(args)
    payload["wall_s"] = time.time() - t0
    payload["args"] = {k: v for k, v in vars(args).items()}
    suffix = args.tag if args.tag else {
        "refs": str(args.lattice), "structure": str(args.lattice),
        "synth": f"{args.lattice}_{args.angle_mode}",
        "compile": f"{args.lattice}_{args.angle_mode}",
        "schedule": f"{args.lattice}_{args.angle_mode}",
        "circuits": f"{args.lattice}_{args.angle_mode}",
        "compiled": f"{args.lattice}_{args.angle_mode}_seg{args.seg}",
        "probe": f"{args.lattice}_{args.angle_mode}",
        "term_compiled": f"{args.lattice}_{args.angle_mode}",
        "qpy13": str(args.lattice),
        "gpu": f"{args.lattice}_{args.device}",
    }.get(args.stage, "")
    name = f"{args.stage}_{suffix}" if suffix else args.stage
    write_frag(name, payload)
    print(f"stage {args.stage} done in {payload['wall_s']:.0f} s", flush=True)
    rc = 0
    if args.stage == "gpu" and "transpiled" in args.gpu_jobs.split(","):
        e = payload["compiled"].get("B0_ref0_k1|all_to_all", {})
        if not e.get("complete"):
            print(f"criterion C6 job did not complete: {e.get('error')}", flush=True)
            rc = 1
    if args.stage == "gpu" and args.then_assemble:
        rc = max(rc, stage_assemble(args))
    return rc


if __name__ == "__main__":
    sys.exit(main())
