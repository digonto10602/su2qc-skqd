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


def _cfg(P, nm, th, con, loc):
    return plaqfactor.cfg_gates(P, nm, th, int(nm[4:]), contract=con, flag_rule="dark")


def _cfg_t(P, nm, th, con, loc):
    return plaqfactor.cfg_gates(P, nm, th, int(nm[4:]), contract=con, flag_rule="triple")


def _sw(fn):
    """The same proposal with every multiplexed rotation synthesised by the sparse-Walsh walk."""
    from .sparsemux import use_sparse_mux

    def g(P, nm, th, con, loc):
        with use_sparse_mux():
            return fn(P, nm, th, con, loc)
    return g


def _fullsynth(P, nm, th, con, loc):
    """The package's exact block synthesis on all local codewords (operator class), via reach.synth_on."""
    from .reach import synth_on
    sup, states, h, pos = P.local(nm)
    g = synth_on(states, h, len(sup), th)
    return [(n, [sup[q] for q in qs], par) for n, qs, par in g]


def _framed(P, nm, th, con, loc):
    """Vertex parity frame, then the package block synthesis on the framed generator (hopframe.py)."""
    from .hopframe import framed_gates, vertex_parity_frame
    return framed_gates(P, nm, th, vertex_parity_frame(P, nm), contract=con)


def _bframed(P, nm, th, con, loc):
    """Vertex parity fold + bright/dark intertwiner rotations, then block synthesis (hopframe.py)."""
    from .hopframe import framed_gates, vertex_bright_frame
    return framed_gates(P, nm, th, vertex_bright_frame(P, nm), contract=con)


PROPOSALS = {
    "pkg": {"fn": _pkg, "terms": tuple([f"hop{l}" for l in range(10)] + ["plaq0", "plaq2"]),
            "contract": "operator"},
    # rpkg is not run on plaq1: its unrestricted form is 66 468 CX (data/p2_0_harness_baseline.json) and
    # the restricted synthesis of the 16-qubit term costs minutes per reference for no prospect of beating cf2
    "rpkg": {"fn": _rpkg, "terms": tuple([f"hop{l}" for l in range(10)] + ["plaq0", "plaq2"]),
             "contract": "input"},
    "cf1": {"fn": _cf1, "terms": "plaq", "contract": "both"},
    "cf2": {"fn": _cf2, "terms": ("plaq1",), "contract": "both"},
    "cfg": {"fn": _cfg, "terms": "plaq", "contract": "both"},
    "cfg_t": {"fn": _cfg_t, "terms": "plaq", "contract": "both"},
    "rpkg_sw": {"fn": _sw(_rpkg), "terms": tuple([f"hop{l}" for l in range(10)] + ["plaq0", "plaq2"]),
                "contract": "input"},
    "full_sw": {"fn": _sw(_fullsynth), "terms": tuple([f"hop{l}" for l in range(10)]), "contract": "operator"},
    "cfg_sw": {"fn": _sw(_cfg), "terms": "plaq", "contract": "both"},
    "cfg_t_sw": {"fn": _sw(_cfg_t), "terms": "plaq", "contract": "both"},
    "cf2_sw": {"fn": _sw(_cf2), "terms": ("plaq1",), "contract": "both"},
    "framed_sw": {"fn": _sw(_framed), "terms": tuple(f"hop{l}" for l in range(10)), "contract": "both"},
    "bframed": {"fn": _bframed, "terms": tuple(f"hop{l}" for l in range(10)), "contract": "both"},
    "bframed_sw": {"fn": _sw(_bframed), "terms": tuple(f"hop{l}" for l in range(10)), "contract": "both"},
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
