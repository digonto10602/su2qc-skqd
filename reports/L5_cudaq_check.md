# Laptop gate L5 — CUDA-Q circuits versus the numpy reference (2x2)

**Status: PASS** — `scripts/laptop_L5_cudaq_check.py`, target qpp-cpu.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 0420211, 2026-09-15 20:19:58 MDT.
Runtime 3 s; sampling 10000 shots took 1.65 s.  Conventions found: result strings list
qubit 0 first; register_operation BIG_ENDIAN = True (make this the default in
`src/skqd/circuits_cudaq.py` if it differs).

| check | value | criterion | result |
|---|---|---|---|
| cudaq importable | CUDA-Q Version 0.15.1 (https://github.com/NVIDIA/cuda-quantum aca5853a76d499ecc3d5f97c2e06163ae99d9c75) | installed | PASS |
| result-string order test (X on qubit 0 of 3) | 100 | '100' (qubit 0 first) or '001' (qubit 0 last) | PASS |
| register_operation convention determined (custom CNOT = x.ctrl) | BIG_ENDIAN=True, 11 vs 11 | custom CNOT acts like x.ctrl under the chosen flag | PASS |
| IR gate coverage (h, x, ry, rx, rz, p, cp, cx, gphase, unitary, mcu) vs numpy | 0.019 | total-variation distance < 0.120 | PASS |
| noiseless sampling: accepted shots | 10000/10000 | = all shots | PASS |
| total-variation distance to the exact distribution | 0.0091 | < 0.272 | PASS |
