# su2qc-skqd

**Neural-enhanced sample-based Krylov quantum diagonalization (SKQD) for SU(2) lattice gauge theory with
staggered quarks on 2×Lx ladders** — the code package for SU2QC Project 2 (rev. 2 implementation manual,
`proposal/`).  Independent implementation, built and validated on 14 September 2026; it reproduces every number
of the manual's Tables 1–4 from scratch (gates E1, E2, E3, S1 — reports in `reports/`, machine-readable results
in `validation/`).

## The physics in one screen

Kogut–Susskind Hamiltonian on an open $2\times L_x$ patch, links truncated at $j_{\max}=\tfrac12$, two-colour
staggered quarks, $m = 3g^2/16$:

$$
H = -\frac12\sum_{\ell=(x\to y)}\Big[\eta_\ell\,\psi^\dagger_{x,i}U_{ij}(\ell)\psi_{y,j}+\text{h.c.}\Big]
+ m\sum_x(-1)^{x_1+x_2}\,n_x + \frac{g^2}{2}\sum_\ell j_\ell(j_\ell+1)
- \frac{1}{2g^2}\sum_P\big(W_P+W_P^\dagger\big)
$$

with $g^2$ the gauge coupling, $m$ the quark mass, $\eta_\ell$ the staggered phases ($i$ on $x$-links,
$(-1)^{x_1+x_2}$ on $y$-links), $U_{ij}(\ell)$ the truncated link operator, $j_\ell$ the link spin,
$n_x$ the quark occupation and $W_P$ the plaquette Wilson loop.  Gauss's law
$G_a(x)=\sum_{\rm out}L_a+\sum_{\rm in}R_a+\psi_x^\dagger\tfrac{\sigma_a}{2}\psi_x\,(+\tfrac{\sigma_a}{2}|_{\rm static})$
selects the physical (dressed-site) basis $|b\rangle=|\{j_\ell\},\{n_x\},\{\iota_x\}\rangle$ with the intertwiner label
$\iota_x$ (82 states at 2×2, 1 727 at 2×3, 37 165 at 2×4).  SKQD: a device prepares
$\prod_\gamma e^{-iH_\gamma k\Delta t}|b_0\rangle$ (one coarse step per circuit, $\Delta t=\pi/W_B$), is measured in
the configuration basis, the accepted configurations form the support $B$, and the exact $H_B$ is diagonalized
classically: $E_R\ge E_0$ for any $B$, with the certified interval $E_0\in[E_R-r_H,E_R]$ (Weinstein, gap-assumed),
$r_H=\|(H-E_R)\psi_R\|$.

## Status

| gate | content | status |
|---|---|---|
| E1 | $[G_a(x),H]=0$ in the 160 000-dim redundant basis; 82-dim kernel; sector split 38/20/20/2/2; dressed-site builder = projector route element by element (3.6e-15) | PASS |
| E2 | Table 2 counts (82 / 1 727 / 37 165; 113, 112; 2 729, 2 418), codewords, decoder round trip on every state, random acceptance 0.15 % | PASS |
| E3 | Table 1 (all rows, 4 decimals), $V(1)=1.3872$, $V(2)=2.5898$, $M_B$, $\Delta_0$, $B=1$ clusters, $\Delta t=\pi/W$, $j_{\max}=1$ truncation shift | PASS |
| S1 | device-proxy emulation (Table 4), production-budget recall 1.00 / 0.99 at $f=0.1$ (`validation/S1.json`), Table 3 controls (CIPSI tracks the oracle), ridge ranker Spearman 0.86 / 0.89, 2×4 transfer | PASS |
| circuits | exact gauge-invariant coarse-step circuits at 2×2 verified against the emulation (all 28 circuits agree to < 1e-10, `tests/test_circuits_ir.py`; the run that built the package saw ≤ 5e-15); the plaquette term is a 30-CNOT pair rotation (`validation/CS.json`) | verified (numpy) |
| L2–L5 | Qiskit / CUDA-Q on the laptop | next (prompts 02–05) |
| S2, S3, H0–H2, P1, M1 | structured gates within the CZ budget, device-model simulation, hardware | open |

Full table: `validation/gates.md`; plan: `prompts/08_month_plan_and_reporting.md`.

## Quick start

```bash
pip install -r requirements.txt            # numpy, scipy — the physics core
python scripts/check_package.py            # everything present? gates PASS?
pytest -q tests                            # 14 tests, < 1 min
python scripts/run_gate.py E3              # exact references, ~1 min
python scripts/run_gate.py S1 --quick      # emulation, ~1 min
pip install -r requirements-laptop.txt     # qiskit, qiskit-aer, ... (laptop gates)
python scripts/run_gate.py L2 --push       # Qiskit vs numpy reference, then push on PASS
```

```python
from skqd.exact import Model
M = Model(3)                                   # 2x3 ladder: basis (1727 states) + Hamiltonian terms in 0.8 s
r = M.reference(g2=4.0, twoB=0)                # B = 0 sector: dense diagonalization of the 677-dim block
print(r.E0, r.dt, r.support999)                # -5.6026, 0.156 (= pi/W), 86
```

A coarse-step circuit in Qiskit (exact block unitaries, 12 qubits at 2×2):

```python
from skqd.exact import Model
from skqd.circuits_ir import CircuitFactory
from skqd.circuits_qiskit import ir_to_qiskit, sample
from skqd.krylov import references
from skqd.codec import Codec

M = Model(2); F = CircuitFactory(M, g2=4.0); dt = M.reference(4.0, 0).dt
gates = F.coarse_step(references(M.basis, 0)[0], k=2, dt=dt)   # X prep + diag + 4 hops + plaquette (30 CNOT)
qc = ir_to_qiskit(gates, n=12)                                  # QuantumCircuit with measurements
counts = sample(gates, 12, shots=10_000)                         # AerSimulator -> {bit tuple: count}
accepted, rejected = Codec(M.basis).decode_counts(counts, target_twoB=0)   # support B (all shots decode noiselessly)
```

The same IR runs on CUDA-Q (`skqd.circuits_cudaq.sample(gates, 12, shots, target="nvidia")`, generated
`@cudaq.kernel` source with registered custom unitaries).

## Layout

`src/skqd/` package · `scripts/` gate scripts and the runner · `tests/` · `validation/` gate JSON + gate table ·
`reports/` gate reports · `data/` reference numbers · `prompts/` the prompt chain (planner-written, executor-run) ·
`proposal/` the manual · `.claude/` agents (model/effort routing), gate skill, settings.  `CLAUDE.md` is the
operating manual for the agents.

## Conventions (do not change without re-running E1–E3)

Link generators $L_a=-J_a^{\top}$ on $m_L$, $R_a=+J_a$ on $m_R$; $[L_a,U_{ij}]=-(T_aU)_{ij}$, $[R_a,U_{ij}]=+(UT_a)_{ij}$;
matter charge $Q_a=\psi^\dagger\tfrac{\sigma_a}{2}\psi$; site index $x_1L_y+x_2$; JW order = site order;
codeword layout of `codec.py`; qubit $k$ = bit $k$ (little-endian, Qiskit's convention).

## License

MIT (see `LICENSE`).  Reference documents: the SU2QC Project 2 manual (`proposal/`), Yu et al. arXiv:2501.09702,
Rosanowski et al. arXiv:2510.26951, Robledo-Moreno et al. arXiv:2405.05068.
