# What runs where: laptop (i7-8750H, GTX 1060 Max-Q 6 GB) versus desktop / cluster / QPU

Rule: every run on the laptop must finish within 30 minutes; if it does not, re-parametrize (fewer shots,
`--quick`, one sector) and record here what the reduced run showed and what the full run needs.

Measured in the cloud sandbox where this package was built (2 CPUs, 7 GB RAM, numpy 2.4.4 / scipy 1.17.1).
Gate times are the `runtime_s` fields of `validation/*.json`; the S1-quick and test times were read from the
session log (they are not stored in a JSON):

| step | script | cloud time | laptop estimate | comment |
|---|---|---|---|---|
| E1 (2x2 Gauss law, kernel of the 160 000-dim redundant space, two builders) | `gate_E1.py` | 104 s | 1–3 min | dominated by dense `eigh` of 4096-dim blocks; runs on CPU |
| E2 (counts, codewords, decoder, 2x4 round trip, 2e5 random strings ×4) | `gate_E2.py` | 8 s | 1 min | pure Python loops |
| E3 (2x2/2x3/2x4 builds, Lanczos, static sectors, j_max = 1) | `gate_E3.py` | 14 s | < 1 min | 2x4 build 5 s, 37 165 states, 521 017 non-zeros |
| S1 quick (1 repetition, no 2x4) | `gate_S1.py --quick` | 35 s | < 1 min | |
| S1 full (3 repetitions + 2x4 device proxy, CIPSI to 640, ML transfer) | `gate_S1.py` | 86 s | 2 min | |
| circuit-structure report | `report_circuit_structure.py` | 1 s (+ model builds) | < 1 min | |
| tests (14) | `pytest -q tests` | 8 s | < 1 min | |

Laptop estimates assume the i7-8750H is at least as fast per core as the sandbox CPU (verify in gate L1).

## Laptop gates (Qiskit / CUDA-Q — never executed in the sandbox, PyPI was blocked)

| gate | what | size | expected time | risk |
|---|---|---|---|---|
| L2 | Qiskit statevector of the 2x2 circuits vs numpy reference; noiseless Aer sampling | 12 qubits, 4096 amplitudes; unitaries up to 8 qubits (256×256) | < 5 min | bit-order conventions (tested first) |
| L3 | transpiled CZ counts (all-to-all, heavy-hex) | 12 qubits; 8-qubit `UnitaryGate` synthesis at level 3 can take minutes each | 5–30 min | if > 30 min use `--level 2` |
| L4 | Aer noise-model sampling (depolarizing + readout), decode, yield | 12 qubits × 28 circuits (B=0: 5 refs × 4 steps; B=1: 2 × 4); shots scaled to 25 min | ≤ 30 min by construction | none |
| L5 | CUDA-Q on the GPU (`nvidia` target) | 12 qubits | < 5 min | register_operation conventions (tested first) |

## What needs the desktop (RTX 3070 8 GB, 32 GB RAM) or the Slurm GPU cluster

| task | why not the laptop | where |
|---|---|---|
| S3: noisy Aer simulation of the full 2x3 production set (32–44 circuits per sector, 2e5 shots per sector, 20–21 qubits) | per-shot cost of noisy simulation × 2e5 shots × 4 sectors; a 2x3 pilot (1e4 shots, one sector) fits the laptop | desktop GPU (Aer GPU statevector, 2^20 amplitudes = 16 MB) or cluster |
| 2x4 circuits (28 qubits) | statevector 2^28 × 16 B = 4 GB (double); the GTX 1060 has 6 GB but the laptop RAM and the noisy per-shot cost make it impractical | desktop (single precision on the 3070, or CPU with 32 GB) / cluster |
| ML model v2 (message-passing network) training on 2x2–2x3 data, transfer to 2x4 | GPU training time; the ridge baseline runs anywhere | desktop GPU |
| bootstrap analyses over circuits (P1) at 2x3 | cheap; laptop is fine | laptop |
| exact references beyond 2x4 (2x5: ~8e5 states) | memory for the builder and Lanczos | cluster |
| hardware runs H0–H2 | QPU | IBM Heron-class / Nighthawk |

## Memory

The 2x4 dressed-site Hamiltonian (37 165 × 37 165, 521 017 non-zeros) needs ~10 MB; the 2x2 redundant-basis
construction (160 000-dim sparse, 736 922 non-zeros in H) ~50 MB; no laptop constraint for the physics core.
