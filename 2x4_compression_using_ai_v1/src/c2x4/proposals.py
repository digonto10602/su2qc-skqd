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


def applicable(label: str, name: str, P=None) -> bool:
    """Lattice-generic term classes: 'hop', 'plaq', 'hop+plaq_small' (hops and the plaquettes that are not all-interior),
    'plaq_interior' (plaquettes whose four corners are interior vertices); explicit tuples are the 2x4 names of it1-it5."""
    t = PROPOSALS[label]["terms"]
    if t == "all":
        return True
    if t == "plaq":
        return name.startswith("plaq")
    if t == "hop":
        return name.startswith("hop")
    if t in ("hop+plaq_small", "plaq_interior"):
        if name.startswith("hop"):
            return t == "hop+plaq_small"
        interior = _all_interior(P, name) if P is not None else name == "plaq1"
        return interior if t == "plaq_interior" else not interior
    return name in t


def _all_interior(P, name: str) -> bool:
    from .plaqfactor import corners_of
    return all(c["third"] is not None for c in corners_of(P, int(name[4:])))


def register(label: str, fn, terms, contract: str):
    PROPOSALS[label] = {"fn": fn, "terms": terms, "contract": contract}


# ------------------------------------------------------------------ C4 round (notes/010): angle-linear synthesis
def _lin(fn, mode="lp"):
    """The same proposal through linsynth.use_linear: theta-free structural decisions (strictly k-independent
    skeleton), LP (mode 'lp') or exact-minimum MILP (mode 'milp') Walsh supports."""
    from .linsynth import use_linear

    def g(P, nm, th, con, loc):
        with use_linear(mode):
            return fn(P, nm, th, con, loc)
    return g


_HOPS = "hop"
for _base, _fn, _terms, _con in [("rpkg", _rpkg, "hop+plaq_small", "input"), ("full", _fullsynth, _HOPS, "operator"),
                                 ("framed", _framed, _HOPS, "both"), ("bframed", _bframed, _HOPS, "both"),
                                 ("cfg", _cfg, "plaq", "both"), ("cfg_t", _cfg_t, "plaq", "both"),
                                 ("cf2", _cf2, "plaq_interior", "both")]:
    for _mode in ("lp", "milp"):
        PROPOSALS[f"{_base}_lin{'' if _mode == 'lp' else '_milp'}"] = {"fn": _lin(_fn, _mode), "terms": _terms,
                                                                       "contract": _con}


def _jwc(frame_fn, milp=False):
    def g(P, nm, th, con, loc):
        from . import hopframe
        old = hopframe.SOLVER_MODE["milp"]
        hopframe.SOLVER_MODE["milp"] = milp
        try:
            return hopframe.jwc_framed_gates(P, nm, th, frame_fn(P, nm), contract=con)
        finally:
            hopframe.SOLVER_MODE["milp"] = old
    return g


def _frame_none(P, nm):
    return []


def _frame_parity(P, nm):
    from .hopframe import vertex_parity_frame
    return vertex_parity_frame(P, nm)


def _frame_bright(P, nm):
    from .hopframe import vertex_bright_frame
    return vertex_bright_frame(P, nm)


for _fl, _ff in [("plain", _frame_none), ("framed", _frame_parity), ("bframed", _frame_bright)]:
    PROPOSALS[f"jwc_{_fl}"] = {"fn": _jwc(_ff), "terms": "hop", "contract": "both"}
    PROPOSALS[f"jwc_{_fl}_milp"] = {"fn": _jwc(_ff, True), "terms": "hop", "contract": "both"}


def _cb(anc_vertex, bright=True, jwc=False, mode="lp"):
    """Hop with the clean-ancilla frame (hopframe.vertex_bright_frame_clean) and flagged angle-linear multiplexors
    (constant multiplexors included, linsynth.CONST_LIN); optional JW conjugation."""
    def g(P, nm, th, con, loc):
        from . import hopframe
        from .linsynth import CONST_LIN, use_linear
        frame, anc = hopframe.vertex_bright_frame_clean(P, nm, anc_vertex, bright)
        old = CONST_LIN["on"]
        CONST_LIN["on"] = True
        try:
            if jwc:
                oldm = hopframe.SOLVER_MODE["milp"]
                hopframe.SOLVER_MODE["milp"] = (mode == "milp")
                try:
                    return hopframe.jwc_framed_gates(P, nm, th, frame, contract=con, anc=anc)
                finally:
                    hopframe.SOLVER_MODE["milp"] = oldm
            with use_linear(mode):
                return hopframe.framed_gates(P, nm, th, frame, contract=con, anc=anc)
        finally:
            CONST_LIN["on"] = old
    return g


for _av in (0, 1):
    for _br in (True, False):
        for _j in (False, True):
            for _mode in ("lp", "milp"):
                _lab = f"cb{_av}{'' if _br else 'p'}{'_jwc' if _j else ''}{'' if _mode == 'lp' else '_milp'}"
                PROPOSALS[_lab] = {"fn": _cb(_av, _br, _j, _mode), "terms": "hop", "contract": "both"}
