"""Convenience shim: `import families` from the study folder (or with it on sys.path) gives the stable loader API
of src/c2x4/families.py (notes/009).  Signature: get_family(name, measure=False) -> list of
(circuit_id, qiskit.QuantumCircuit, metadata)."""
import os as _os
import sys as _sys

_src = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "src")
if _src not in _sys.path:
    _sys.path.insert(0, _src)

from c2x4.families import *            # noqa: E402,F401,F403
from c2x4.families import __all__       # noqa: E402,F401
