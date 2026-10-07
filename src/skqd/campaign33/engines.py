"""
C3_LE and C3_SEL (prompts/33 1.5, P8/P9): the four Stage-E circuits on an independent Quantinuum
engine, noiselessly, in an env that has NO qiskit (skqd-pecos / skqd-selene on Perlmutter, the
~/.local/share/su2qc-pecos / su2qc-selene venvs on the laptop).

  C3_LE   pytket-quantinuum QuantinuumBackend("H2-1LE", api_handler=QuantinuumAPIOffline()) -- the local
          emulator (pytket-pecos / quantum-pecos), simulator="state-vector", noisy_simulation=False, on the
          frozen pytket JSON of gate Q0P_2x3 (sha256 checked against its index).
  C3_SEL  Selene (selene-sim, Quest statevector, IdealErrorModel) on the QIR export of the same circuits
          (data/campaign33/qir/<id>.ll, written on the laptop by scripts/campaign33_engines.py).

Exact probabilities and the sector codeword tables come from data/campaign33/exact/stage_e.json (written
on the laptop: `scripts/campaign33.py --stage exact-data`), so nothing here needs scipy or the model.
P8: |n_s/N - p_s| <= 3 sqrt(p_s (1-p_s)/N) for every state with p_s >= 1e-3 (prompts/33 2.4; small N);
P9: every observed string is a codeword of the circuit's sector (noiseless: nothing may be rejected).
The two-sample TV distance against C3_AER is computed at assembly (both JSONs carry the counts).
"""
from __future__ import annotations

import hashlib
import json
import os
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FCELL_SHOTS = {"B0_ref25_k1": 800, "B1_ref57_k1": 800, "B0_ref25_k4": 200, "B1_ref57_k4": 200}
EXACT = os.path.join(ROOT, "data", "campaign33", "exact", "stage_e.json")
Q0P_DIR = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
QIR_DIR = os.path.join(ROOT, "data", "campaign33", "qir")
LADDER = (2, 8, 32)
MAX_PER_CIRCUIT = 100000


def _load(p):
    with open(p) as fh:
        return json.load(fh)


def bits_to_int(bits):
    return int(sum(int(b) << k for k, b in enumerate(bits)))


# --------------------------------------------------------------------------- the engines
class Pecos:
    name = "pytket-quantinuum H2-1LE local emulator (pytket-pecos / quantum-pecos), state-vector, noiseless"

    def __init__(self):
        from pytket import Circuit
        from pytket.extensions.quantinuum import QuantinuumBackend
        from pytket.extensions.quantinuum.backends.api_wrappers import QuantinuumAPIOffline
        self.be = QuantinuumBackend(device_name="H2-1LE", api_handler=QuantinuumAPIOffline())
        idx = _load(os.path.join(Q0P_DIR, "index.json"))
        self.circ, self.sha = {}, {}
        for cid in FCELL_SHOTS:
            text = open(os.path.join(Q0P_DIR, cid + ".json")).read()
            sha = hashlib.sha256(text.encode()).hexdigest()
            if sha != idx["files"][cid]["json_sha256"]:
                raise SystemExit(f"{cid}: frozen JSON sha256 mismatch")
            self.circ[cid] = Circuit.from_dict(json.loads(text))
            self.sha[cid] = sha

    def versions(self):
        from importlib import metadata
        out = {}
        for p in ("pytket", "pytket-quantinuum", "pytket-pecos", "quantum-pecos", "numpy"):
            try:
                out[p] = metadata.version(p)
            except Exception:
                out[p] = None
        return out

    def run(self, cid, n, seed):
        c = self.circ[cid]
        h = self.be.process_circuit(c, n_shots=int(n), simulator="state-vector", noisy_simulation=False,
                                    seed=int(seed))
        r = self.be.get_result(h)
        bits = r.get_bitlist() if hasattr(r, "get_bitlist") else None
        names = [(b.reg_name, b.index[0]) for b in (bits or c.bits)]
        out = {}
        for key, v in r.get_counts().items():
            d = {names[j]: int(key[j]) for j in range(len(key))}
            x = sum(d[("c", k)] << k for k in range(len(key)))
            out[x] = out.get(x, 0) + int(v)
        return out


class Selene:
    name = "Selene (selene-sim, Quest statevector simulator, IdealErrorModel) on the QIR export"

    def __init__(self):
        import pathlib

        from selene_sim import build
        self.inst, self.sha = {}, {}
        for cid in FCELL_SHOTS:
            p = os.path.join(QIR_DIR, cid + ".ll")
            self.sha[cid] = hashlib.sha256(open(p, "rb").read()).hexdigest()
            self.inst[cid] = build(pathlib.Path(p), name=f"c33_{cid.lower()}")

    def versions(self):
        from importlib import metadata
        out = {}
        for p in ("selene-sim", "selene-core", "qir-qis", "numpy"):
            try:
                out[p] = metadata.version(p)
            except Exception:
                out[p] = None
        return out

    def run(self, cid, n, seed):
        from selene_sim import IdealErrorModel, Quest
        out = {}
        for shot in self.inst[cid].run_shots(Quest(random_seed=int(seed)), n_qubits=20, n_shots=int(n),
                                             error_model=IdealErrorModel(random_seed=int(seed)),
                                             random_seed=int(seed)):
            x = decode_selene_shot(list(shot))
            out[x] = out.get(x, 0) + 1
        return out


def decode_selene_shot(entries):
    """The c register of one Selene shot as an int with bit k = c[k] (pytket-qir records the register as
    one integer, `__quantum__rt__int_record_output`, whose bit k is c[k])."""
    vals = [v for tag, v in entries if str(tag).split(":")[-1] in ("c", "USER:INT:c")]
    if len(vals) != 1:
        raise ValueError(f"cannot find the c register in {entries[:5]}")
    v = vals[0]
    if isinstance(v, (list, tuple)):
        return bits_to_int(v)
    return int(v)


# --------------------------------------------------------------------------- the token
def run(ctx):
    from campaign33 import add_table

    from . import stats as ST
    from . import tokens as TK
    ex = _load(EXACT)
    eng_cls = Pecos if ctx.token == "C3_LE" else Selene
    ej = os.path.join(ROOT, "data", "campaign33", "engines.json")
    dec = _load(ej).get(ctx.token, {}) if os.path.exists(ej) else {}
    ctx.data["engines_json_decision"] = {"decision": dec.get("decision"), "reason": dec.get("reason"),
                                         "source": "data/campaign33/engines.json"}
    if dec.get("decision") == "drop":
        ctx.notes.append(f"{ctx.token} is DROPPED by data/campaign33/engines.json ({dec.get('reason')}); its job is "
                         "not requested on Perlmutter")
    t_b = time.time()
    try:
        eng = eng_cls()
    except Exception as exc:
        ctx.phases["engine_setup_s"] = time.time() - t_b
        ctx.data["engine"] = f"{eng_cls.name}: UNAVAILABLE ({type(exc).__name__}: {str(exc)[:300]})"
        ctx.device = "engine unavailable"
        ctx.data["dropped"] = True
        ctx.notes.append(f"the engine could not be set up: {type(exc).__name__}: {str(exc)[:300]}")
        return
    ctx.phases["engine_setup_s"] = time.time() - t_b
    ctx.data["engine"] = eng.name + " (CPU)"
    ctx.data["engine_versions"] = eng.versions()
    ctx.data["inputs_sha256"] = eng.sha
    ids = list(FCELL_SHOTS)
    if ctx.dry:                                        # a path check: one circuit per sector
        ids = [c for c in ids if c.endswith("_k1")]
    lad = [n for n in LADDER if n <= max(2, ctx.scaled(32))] or [2]
    if ctx.dry:
        lad = [1]
    pts, rate = [], None
    t_l = time.time()
    for j, n in enumerate(lad):
        if ctx.deadline is not None and rate is not None and time.time() + rate * n > ctx.sampling_deadline(0.3):
            pts.append({"shots": n, "skipped": "budget"})
            continue
        t0 = time.time()
        cnt = eng.run(ids[0], n, TK.chunk_seed(ctx.s0, 90, j, n))
        el = time.time() - t0
        rate = el / n
        pts.append({"shots": n, "seconds": el, "seconds_per_shot": rate, "distinct": len(cnt)})
        ctx.log(f"ladder {n} shots: {el:.1f} s ({rate:.3f} s/shot)")
    ctx.phases["ladder_s"] = time.time() - t_l
    left = 0.75 * (ctx.remaining() or 3600.0)
    fit = int(left / (rate * len(ids))) if rate else ctx.scaled(200)
    shots = max(2, min(MAX_PER_CIRCUIT, fit))
    if ctx.dry:
        shots = 1
    counts, p8, p9, seeds = {}, {}, {}, {}
    t_s = time.time()
    for i, cid in enumerate(ids):
        seed = TK.chunk_seed(ctx.s0, i, 0, shots)
        cnt = eng.run(cid, shots, seed)
        seeds[cid] = seed
        counts[cid] = cnt
        c = ex["circuits"][cid]
        probs = {int(k): float(v) for k, v in c["probabilities"].items()}
        sec = "B=0" if c["twoB"] == 0 else "B=1"
        cw = set(int(x) for x in ex["sectors"][sec]["codeword_ints"])
        p8[cid] = ST.per_state_test(cnt, probs, shots, 3.0, 1e-3)
        bad = int(sum(v for k, v in cnt.items() if int(k) not in cw))
        p9[cid] = {"shots": shots, "not_a_sector_codeword": bad, "ok": bad == 0,
                   "reference_hits": int(cnt.get(int(c["reference_int"]), 0))}
        ctx.log(f"{cid}: {shots} shots, max z {p8[cid]['max_z']:.2f}, outside sector {bad}")
    ctx.phases["sampling_s"] = time.time() - t_s
    ctx.data["seconds_per_shot"] = ctx.phases["sampling_s"] / max(1, shots * len(ids))
    nfail = sum(len(v["failures"]) for v in p8.values())
    ctx.physics("P8 per-state agreement with the exact distribution at 3 sigma (p_s >= 1e-3); the TV distance to "
                "C3_AER is computed at assembly", {"failures": nfail, "max_z": max(v["max_z"] for v in p8.values())},
                "0 failures", nfail == 0)
    ctx.physics("P9 every observed string decodes into the circuit's sector", {c: v["not_a_sector_codeword"] for c, v in p9.items()},
                "0 outside", all(v["ok"] for v in p9.values()))
    ctx.data.update({"ladder": pts, "shots_per_circuit": shots, "seeds": dict(ctx.data["seeds"], per_circuit=seeds),
                     "per_state": p8, "decode": p9,
                     "counts": {c: {str(k): v for k, v in sorted(counts[c].items())} for c in ids},
                     "gpu_mode_used": None})
    add_table(ctx, f"{ctx.token}: {eng.name}", ["circuit", "shots", "states tested", "max z", "outside sector",
                                                 "reference hits"],
              [[c, shots, p8[c]["tested_states"], p8[c]["max_z"], p9[c]["not_a_sector_codeword"],
                p9[c]["reference_hits"]] for c in ids])
