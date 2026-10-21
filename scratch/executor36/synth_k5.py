"""Fill the gate_S2_2x4 term-IR cache at the two k = 5 angles (5 dt, both sectors) -- prompts/36 3.3."""
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import gate_S2_2x4 as S4  # noqa: E402

t0 = time.time()
th = [5 * S4.dt_of(4, 0), 5 * S4.dt_of(4, 2)]
print("thetas", [repr(x) for x in th], flush=True)
S4.preload_factory(4, "exact", th)
print(f"done {time.time() - t0:.0f} s", flush=True)
