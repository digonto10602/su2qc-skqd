"""Candidate circuit families: a family maps (twoB, ref, k) to a full 28-qubit IR gate list.

A builder is (P, name, theta, ctx) -> gate list for exp(-i theta H_name); ctx = {"twoB", "ref", "k"}.
The circuit is prepare(ref) + diag + hop0..hop9 + plaq0..plaq2 in the package order
(krylov.term_groups), never reordered.

Contracts (A3):
  operator-exact builders (baseline, cf1, cf2) are exact on every local codeword of the term;
  input-specific builders (rh = restricted hop, rp = restricted plaquette) are exact on the blocks reachable
  from the circuit's own reference (reach.py) and arbitrary elsewhere;
  drop_diag: the diagonal group acts first on the reference basis state, i.e. as a global phase
  (Lean: Compress2x4.Sanity.diagonal_mulVec_single); the bar is judged after removing the global phase.
"""
from __future__ import annotations

import gzip
import os
import pickle

from .env import CACHE
from . import plaqfactor
from .reach import Reach, restricted_term_gates

_REACH = {}


def get_reach(P) -> Reach:
    if id(P) not in _REACH:
        _REACH[id(P)] = Reach(P)
    return _REACH[id(P)]


def _key(theta):
    return f"{theta:.17g}".replace("-", "m").replace(".", "p")


def _cached(tag, fn, per_ref=False):
    def b(P, name, theta, ctx):
        r = f"_r{ctx['ref']}" if per_ref else ""
        p = P.cpath(f"{tag}{r}_{name}_{_key(theta)}.pkl.gz")
        if os.path.exists(p):
            with gzip.open(p, "rb") as fh:
                return pickle.load(fh)
        g = fn(P, name, theta, ctx)
        os.makedirs(CACHE, exist_ok=True)
        with gzip.open(p, "wb", compresslevel=1) as fh:
            pickle.dump(g, fh)
        return g
    b.tag = tag
    b.contract = "input-specific" if per_ref else "operator-exact"
    return b


def baseline_builder(P, name, theta, ctx=None):
    return P.baseline_term_ir(name, theta)


baseline_builder.tag = "baseline"
baseline_builder.contract = "operator-exact"

cf1_builder = _cached("cf1", lambda P, nm, th, ctx: plaqfactor.cf1_gates(P, nm, th, int(nm[4:])))
cf2_builder = _cached("cf2", lambda P, nm, th, ctx: plaqfactor.cf2_gates(P, nm, th, int(nm[4:])))
rh_builder = _cached("rh", lambda P, nm, th, ctx: restricted_term_gates(
    P, nm, th, get_reach(P).local_reachable(ctx["ref"], nm)), per_ref=True)

_PLAQ = {"plaq0": cf1_builder, "plaq1": cf2_builder, "plaq2": cf1_builder}
_HOPS_R = {f"hop{l}": rh_builder for l in range(10)}

FAMILIES = {
    "baseline": {"builders": {}, "drop_diag": False},
    "F2a": {"builders": dict(_PLAQ), "drop_diag": False},
    "F12a": {"builders": {**_PLAQ, **_HOPS_R}, "drop_diag": True},
}


def term_builder(family: dict, name: str):
    return family["builders"].get(name, baseline_builder)


def circuit(P, family: dict, twoB: int, ref: int, k: int) -> list:
    th = P.theta(twoB, k)
    ctx = {"twoB": twoB, "ref": ref, "k": k}
    gates = list(P.factory.prepare(ref))
    if not family.get("drop_diag", False):
        gates += P.factory.diag_gates(th)
    for nm in P.names[1:]:
        gates += term_builder(family, nm)(P, nm, th, ctx)
    return finish(family, gates)


# ------------------------------------------------------------------ archive-driven families
import json as _json
from .env import STUDY as _STUDY
from .proposals import PROPOSALS as _PROPOSALS
from .reach import contract_states as _contract_states


def proposal_builder(plabel: str, cls: str):
    """Builder running proposal `plabel` on the input contract (cls 'input') or on all codewords."""
    def fn(P, name, theta, ctx):
        if cls == "input":
            loc = get_reach(P).local_reachable(ctx["ref"], name)
            con = _contract_states(P, name, loc)
        else:
            loc, con = None, None
        return _PROPOSALS[plabel]["fn"](P, name, theta, con, loc)
    return _cached(f"prop_{plabel}_{cls}", fn, per_ref=(cls == "input"))


def archive_builder(label: str, cls: str):
    """Builder that uses, per (reference, term) [input class] or per term [operator class], the best
    verified proposal of data/archive_<label>.json (cache keyed by the proposal, never by the archive)."""
    from .env import archive_path
    path = archive_path(label)
    with open(path) as fh:
        arch = _json.load(fh)

    def b(P, name, theta, ctx):
        if cls == "input":
            best = arch["input"][str(ctx["ref"])][name]["best"]
        else:
            best = arch["operator"][name]["best"]
        return proposal_builder(best["label"], cls)(P, name, theta, ctx)
    b.tag = f"arch_{label}_{cls}"
    b.contract = "input-specific" if cls == "input" else "operator-exact"
    return b


def archive_family(label: str, cls: str, peephole: bool = False, lx: int = 4) -> dict:
    from .problem import get_problem
    b = archive_builder(label, cls)
    P_names = get_problem(lx).term_names()
    return {"builders": {nm: b for nm in P_names}, "drop_diag": cls == "input", "peephole": peephole,
            "archive": label, "class": cls, "lx": lx}


def family_from_spec(spec: str, lx: int = 4) -> dict:
    """arch:<label>:<input|operator>[:pp|:pp2]"""
    parts = spec.split(":")
    pp = parts[3] if len(parts) > 3 else False
    return archive_family(parts[1], parts[2], peephole=pp, lx=lx)


def finish(family: dict, gates: list) -> list:
    if family.get("peephole"):
        from .peephole import optimise
        gates, _ = optimise(gates)
        if family.get("peephole") == "pp2":           # C4 step 4: CNOT-run resynthesis, then the peephole again
            from .peephole import resynth_cx_runs
            gates, _ = resynth_cx_runs(gates)
            gates, _ = optimise(gates)
    return gates
