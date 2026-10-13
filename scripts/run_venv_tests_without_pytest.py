#!/usr/bin/env python3
"""Runs the test functions of one test module in an interpreter that has no pytest (prompts/35: the
~/.local/share/su2qc-pecos/venv carries pytket-pecos, guppylang and selene-sim but no pytest, and nothing is
installed into it).  A minimal stand-in for `pytest` provides `mark.skipif`, `raises` and `tmp_path`; a test
skipped by its own skipif is reported as SKIP with the reason.

  ~/.local/share/su2qc-pecos/venv/bin/python scripts/run_venv_tests_without_pytest.py tests/test_quantinuum_lattice.py
"""
import contextlib
import importlib.util
import inspect
import os
import sys
import tempfile
import time
import traceback
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class _Mark:
    @staticmethod
    def skipif(cond, reason=""):
        def deco(f):
            f.__skip__ = (bool(cond), reason)
            return f
        return deco

    @staticmethod
    def parametrize(name, values):
        def deco(f):
            f.__params__ = (name, list(values))
            return f
        return deco


@contextlib.contextmanager
def _raises(exc):
    try:
        yield
    except exc:
        return
    raise AssertionError(f"did not raise {exc}")


def main():
    stub = types.ModuleType("pytest")
    stub.mark = _Mark()
    stub.raises = _raises
    sys.modules.setdefault("pytest", stub)
    path = os.path.abspath(sys.argv[1])
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ok = fail = skip = 0
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        f = getattr(mod, name)
        sk = getattr(f, "__skip__", (False, ""))
        if sk[0]:
            skip += 1
            print(f"SKIP {name}: {sk[1]}")
            continue
        params = getattr(f, "__params__", None)
        calls = [{params[0]: v} for v in params[1]] if params else [{}]
        for kw in calls:
            t = time.time()
            try:
                if "tmp_path" in inspect.signature(f).parameters:
                    with tempfile.TemporaryDirectory() as td:
                        f(tmp_path=td, **kw)
                else:
                    f(**kw)
                ok += 1
                print(f"PASS {name}{kw or ''} ({time.time() - t:.1f} s)")
            except Exception:
                fail += 1
                print(f"FAIL {name}{kw or ''}")
                traceback.print_exc()
    print(f"{ok} passed, {fail} failed, {skip} skipped ({sys.executable})")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
