# Laptop gate L2 — Qiskit circuits versus the numpy reference (2x2)

**Status: PASS** — `scripts/laptop_L2_qiskit_check.py`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 54c131f, 2026-09-14 16:57:37 MDT.  Runtime 26 s.

| check | value | criterion | result |
|---|---|---|---|
| qiskit importable | 2.5.2 | installed | PASS |
| max |Qiskit statevector - reference| over 35 circuits | 3.725e-15 | < 1e-9 | PASS |
| noiseless sampling: accepted shots | 10000/10000 | = all shots | PASS |
| total-variation distance to the exact distribution | 0.0103 | < 0.272 (shot noise) | PASS |

Gate counts of the k = 2 coarse-step circuit (IR): {'x': 2, 'cx': 38, 'p': 12, 'unitary8q': 2, 'unitary6q': 2, 'h': 8, 'rz': 16}

| timing | value |
|---|---|
| statevector, all circuits | 4.2 s |
| Aer CPU sampling, 10000 shots | 20.87 s |
