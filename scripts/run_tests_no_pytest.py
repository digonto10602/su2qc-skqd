#!/usr/bin/env python3
"""Fallback test runner when pytest is not installed: runs every test_* function in tests/."""
import importlib
import os
import sys
import time
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
ok = fail = 0
for fn in sorted(os.listdir(os.path.join(ROOT, "tests"))):
    if not (fn.startswith("test_") and fn.endswith(".py")):
        continue
    m = importlib.import_module(fn[:-3])
    for name in sorted(dir(m)):
        if name.startswith("test_"):
            t = time.time()
            try:
                getattr(m, name)()
                ok += 1
                print(f"PASS {fn}::{name} ({time.time() - t:.1f}s)")
            except Exception:
                fail += 1
                print(f"FAIL {fn}::{name}")
                traceback.print_exc()
print(f"{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
