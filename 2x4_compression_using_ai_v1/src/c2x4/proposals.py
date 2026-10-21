"""Proposals (candidate constructions) for each term, and the archive of the best verified one.

This is the study's version of the loop of arXiv:2610.22367 (Methods, "Evolutionary search"): the proposer
(genie-opus, turn by turn) writes construction programs; the independent evaluator (`evaluate.py`) checks
each candidate on its contract; the archive keeps, per (reference, term), the verified candidate with the
fewest two-qubit gates, then the smallest two-qubit depth (owner O6).  Each proposal is a function
(P, name, theta, contract_states | None, reach_local | None) -> gate list.
"""
from __future__ import annotations

from . import plaqfactor
from .reach import restricted_term_gates


def _cf1(P, nm, th, con, loc):
    return plaqfactor.cf1_gates(P, nm, th, int(nm[4:]), contract=con)


def _cf2(P, nm, th, con, loc):
    return plaqfactor.cf2_gates(P, nm, th, int(nm[4:]), contract=con)


def _rpkg(P, nm, th, con, loc):
    return restricted_term_gates(P, nm, th, loc)


def _pkg(P, nm, th, con, loc):
    return P.baseline_term_ir(nm, th)


PROPOSALS = {
    "pkg": {"fn": _pkg, "terms": tuple([f"hop{l}" for l in range(10)] + ["plaq0", "plaq2"]),
            "contract": "operator"},
    # rpkg is not run on plaq1: its unrestricted form is 66 468 CX (data/p2_0_harness_baseline.json) and
    # the restricted synthesis of the 16-qubit term costs minutes per reference for no prospect of beating cf2
    "rpkg": {"fn": _rpkg, "terms": tuple([f"hop{l}" for l in range(10)] + ["plaq0", "plaq2"]),
             "contract": "input"},
    "cf1": {"fn": _cf1, "terms": "plaq", "contract": "both"},
    "cf2": {"fn": _cf2, "terms": ("plaq1",), "contract": "both"},
}


def applicable(label: str, name: str) -> bool:
    t = PROPOSALS[label]["terms"]
    if t == "all":
        return True
    if t == "plaq":
        return name.startswith("plaq")
    return name in t


def register(label: str, fn, terms, contract: str):
    PROPOSALS[label] = {"fn": fn, "terms": terms, "contract": contract}
