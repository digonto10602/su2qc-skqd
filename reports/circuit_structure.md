# Structure of the Hamiltonian terms in codeword space (input to gate S2)

Produced by `scripts/report_circuit_structure.py`; numbers stored in `validation/CS.json`.  Environment: Python 3.11.15, numpy 2.4.4, scipy 1.17.1, Linux-6.18.44-fc-v24-x86_64-with-glibc2.39, 2 CPUs, commit 3c32216, 2026-09-14 21:37:07 UTC.

Every term of $H$ is exactly gauge invariant on the codeword subspace and acts on a small set of qubits:
the *support* (touched vertices plus, for hopping, the flux bits of the Jordan–Wigner sites in between, whose
parity is the XOR of their flux bits).  Off-diagonal elements flip a fixed small set of qubits (the *flip
patterns*), the rest of the support only controls the angle.  The largest connected block of a term is the
longest chain of configurations it connects (e.g. $|0,2\rangle \to |1,1\rangle \to |2,0\rangle$ for a hopping link
between an empty and a doubly occupied site).

| lattice | term | support qubits | flipped qubits | flip patterns | largest block | max degree | distinct |element| |
|---|---|---|---|---|---|---|---|
| 2x2 | hop 0 (0, 2) | 8 | [0, 2, 6, 8] | 4 | 3 | 2 | 3 |
| 2x2 | hop 1 (0, 1) | 6 | [1, 2, 3, 5] | 4 | 3 | 2 | 3 |
| 2x2 | hop 2 (1, 3) | 8 | [4, 5, 9, 11] | 4 | 3 | 2 | 3 |
| 2x2 | hop 3 (2, 3) | 6 | [7, 8, 10, 11] | 4 | 3 | 2 | 3 |
| 2x2 | plaquette 0 | 12 | [0, 1, 3, 4, 6, 7, 9, 10] | 1 | 2 | 1 | 3 |
| 2x3 | hop 0 (0, 2) | 9 | [0, 2, 6, 9] | 4 | 4 | 2 | 6 |
| 2x3 | hop 1 (0, 1) | 6 | [1, 2, 3, 5] | 4 | 3 | 2 | 3 |
| 2x3 | hop 2 (1, 3) | 10 | [4, 5, 10, 13] | 4 | 4 | 2 | 6 |
| 2x3 | hop 3 (2, 4) | 10 | [7, 9, 14, 16] | 4 | 4 | 2 | 6 |
| 2x3 | hop 4 (2, 3) | 8 | [8, 9, 11, 13] | 4 | 4 | 2 | 6 |
| 2x3 | hop 5 (3, 5) | 9 | [12, 13, 17, 19] | 4 | 3 | 2 | 3 |
| 2x3 | hop 6 (4, 5) | 6 | [15, 16, 18, 19] | 4 | 3 | 2 | 3 |
| 2x3 | plaquette 0 | 14 | [0, 1, 3, 4, 6, 8, 9, 10, 11] | 2 | 3 | 2 | 5 |
| 2x3 | plaquette 1 | 14 | [7, 8, 9, 11, 12, 13, 14, 15, 17, 18] | 4 | 5 | 4 | 9 |

## The 2x2 plaquette is a pair rotation

At 2x2 every physical state has exactly one plaquette partner (all four link spins flipped = all eight flux
bits flipped); the pair amplitude $w$ is real and depends only on which corners carry one quark
(parities $p_c = q_1 \oplus q_2$; key order $(p_{00}, p_{10}, p_{11}, p_{01})$):

| corner parities | w |
|---|---|
| (0, 0, 0, 0) | -2.0 |
| (0, 0, 1, 1) | -1.0 |
| (0, 1, 0, 1) | -1.0 |
| (0, 1, 1, 0) | 1.0 |
| (1, 0, 0, 1) | -1.0 |
| (1, 0, 1, 0) | 1.0 |
| (1, 1, 0, 0) | 1.0 |
| (1, 1, 1, 1) | 0.5 |

so $W + W^\dagger = D\,X^{\otimes 8}$ and $e^{-i\theta H_{\rm plaq}} = \exp(+i\tfrac{\theta}{2g^2} D X^{\otimes 8})$ is
implemented exactly by: CNOT($q_1\to q_2$) per corner (so $q_2$ holds $p_c$), $H$ on the four $q_1$, a CNOT ladder,
one uniformly controlled $R_z(-\theta w(p)/g^2)$ with the four parity qubits as controls (Gray-code
decomposition: 16 $R_z$ + 16 CNOT), and the inverse.  Verified in this run against the dense exponential on random
physical states at three angles: max deviation 3.97e-16; CNOT count of the plaquette gate: 30.

## IR gate counts of one exact coarse step at 2x2

{'x': 2, 'cx': 38, 'p': 12, 'unitary8q': 2, 'unitary6q': 2, 'h': 8, 'rz': 16}

The four hopping terms are dense local unitaries (6 or 8 qubits) in this first version; generic synthesis of an
8-qubit unitary costs $\mathcal O(10^4)$ CX, which is why gate S2 (routed CZ $\le 250$ per step at 2x2, $\le 500$ at
2x3) is open.  The table above says what a structured hopping gate must do: flip at most four qubits (the flux
bit of the link at both ends and the occupation bits of both vertices), with blocks of at most three (2x2) or
four (2x3) configurations and only four flip patterns per link, i.e. a handful of controlled Givens rotations.
At 2x3 the plaquettes with interior corners have degree up to 4 (intertwiner multiplicity) and 2–4 flip
patterns — the pair trick generalizes to a uniformly controlled small unitary (S2-b).

| check | value | criterion | result |
|---|---|---|---|
| 2x2 plaquette: one partner per state (pair structure) | 1 | = 1 | PASS |
| 2x2 plaquette: distinct pair amplitudes | 4 | = 4 (-2, -1, +1, 1/2) | PASS |
| 2x2 structured plaquette gate vs dense exponential (random physical states, 3 angles) | 3.974e-16 | < 1e-12 | PASS |
| 2x2 structured plaquette gate: CNOT count | 30 | = 30 (8 parity + 6 ladder + 16 UCRz) | PASS |
