# Getting good estimates when the clean fraction is below 0.1

**A catalogue of computational techniques from physics, chemistry, optimization, biology and statistics, with notes on what each one means for SU2QC SKQD**

*Compiled 1 October 2026 for the SU2QC SKQD project (Project 2). Sources: about 300 arXiv and web look-ups across four parallel literature sweeps.*

---

## 0. How to read this file

**Symbols used throughout.** Every symbol is defined here once and is used with this meaning everywhere below.

| Symbol | Meaning |
|---|---|
| $f$ | **Clean fraction**: the probability that one shot (one run of the circuit followed by one measurement) has no error at all. |
| $\varepsilon$ | Error probability per two-qubit gate, as quoted by the hardware vendor. |
| $N_{2q}$ | Number of two-qubit gates in the circuit (CZ, ECR or CNOT gates). |
| $\lambda$ | Expected number of errors in one shot, $\lambda=\sum_i \varepsilon_i\approx \varepsilon N_{2q}$. |
| $p$ | Ideal (noise-free) probability of one particular configuration (bitstring) in the state being sampled. |
| $S$ | Number of shots per circuit. |
| $F$ | Damping factor: noise shrinks a measured average as $\langle O\rangle_{\rm noisy}\approx F\langle O\rangle_{\rm ideal}$. For noise that has been made random-looking by twirling (Section B), $F\approx f$, and $F$ is close to $f$ in many other cases too. |
| $O$ | An observable (a measurable quantity, for example an energy term or a link electric-field value). |
| $B$ | The SKQD subspace: the set of accepted configurations in which $H$ is diagonalized. |
| $H$ | The Hamiltonian (the energy operator) of the model. |

**The basic relation** (the one the SKQD manual uses in its Section 4.4):

$$
f=\prod_{i=1}^{N_{2q}}(1-\varepsilon_i)\;\approx\;(1-\varepsilon)^{N_{2q}}\;\approx\;e^{-\varepsilon N_{2q}}=e^{-\lambda}.
$$

So $f<0.1$ means $\lambda>\ln 10\approx 2.3$: on average more than 2.3 errors happen in every shot.

*Worked example.* With $\varepsilon=3\times10^{-3}$ and $N_{2q}=1000$:

$$
f=(1-0.003)^{1000}=e^{1000\ln(0.997)}=e^{-3.0045}\approx 0.050 .
$$

This matches the manual's table value of 0.050.

*A small correction.* Vendors usually quote $\varepsilon$ as an average gate infidelity from randomized benchmarking (a standard test that measures average gate error). The error-mitigation literature uses the process infidelity, which for two-qubit gates is $\tfrac{5}{4}\varepsilon$. That makes the true $f$ slightly smaller: $f\approx(1-\tfrac54\varepsilon)^{N_{2q}}$ (Cai et al. review, [arXiv:2210.00921](https://arxiv.org/abs/2210.00921)).

**Labels in each entry.**

- **Cost vs $f$**: how the number of shots, or the error, grows as $f$ shrinks.
- **Low-$f$ evidence**: the largest or noisiest hardware run found.
- **Refs**: arXiv IDs, each checked against its arxiv.org abstract page unless marked *(unverified)*.
- Where a scaling or number is my own back-of-envelope estimate rather than a paper's, it says *(my estimate)*.
- Where a name is my own descriptive label rather than a standard term, it says *(my label)*.

---

## 1. The three ideas that make $f<0.1$ survivable

Every technique below works for one or more of these three reasons. Knowing which one applies tells you what the technique costs.

### Idea 1: You need clean *information*, not clean *shots*

- **Sample-based methods (SKQD, SQD, QSCI).** QSCI is quantum-selected configuration interaction, defined in entry C1. These methods only need each important configuration to **appear** often enough among the accepted samples. The SKQD manual's shot rule says a configuration of probability $p$ is seen at least three times with 95% probability if
  $$S\;\ge\;\frac{6.3}{0.82\,f\,p}\;\approx\;\frac{7.7}{f\,p}.$$
  Here 6.3 is the Poisson mean (the average count) that gives at least 3 hits with 95% probability, and 0.82 is the fraction of clean shots that survive 1% readout error on 20 qubits. **Cost grows only as $1/f$.**
- **Post-selection keeps more than $f$.** Post-selection means discarding shots that fail a check, such as the Gauss law (the local constraint every physical gauge-theory state obeys). It only removes the errors it can **detect**, so the kept fraction $f_{\rm keep}$ (my notation) is at least $f$. Undetected errors become false positives in $B$. The variational bound $E_R\ge E_0$ still holds for any $B$, where $E_R$ is the lowest eigenvalue found in $B$ and $E_0$ is the exact ground-state energy.

### Idea 2: Local observables only "see" their lightcone

- The **backward lightcone** of a measured qubit is the set of gates that can influence it.
- A local observable is damped only by the errors inside its lightcone. Its effective clean fraction is $f_{\rm LC}=e^{-\lambda_{\rm LC}}$ (my notation), where $\lambda_{\rm LC}$ is the expected number of errors inside the lightcone. This is much larger than the global $f$.
- **Every record low-$f$ demonstration relies on this:**

| Run | Global $f$ | Lightcone $f_{\rm LC}$ |
|---|---|---|
| IBM 127-qubit utility run | $\sim e^{-29}$ | — |
| Algorithmiq 91-qubit TEM run | $\sim e^{-20}$ | — |
| Farrell et al. 112-qubit Schwinger run | $\sim e^{-30}$ | — |
| Qedma 103-qubit run | $\approx 0.007$ | $\approx 0.16$ |

  (Global $f$ values are my estimates from the papers' gate counts and error rates.)

### Idea 3: Structured noise can be divided out

- **Pauli twirling** (inserting random Pauli gates that cancel in the ideal circuit) turns coherent errors into random Pauli errors. The noise then mostly shrinks signals by a factor $F$ without shifting them.
- Measuring $F$ on a twin circuit whose answer is known, and dividing by it, costs $\sim F^{-2}\approx f^{-2}$ shots.
- For global depolarizing noise (noise that mixes the state toward the fully random state), this simple rescaling is provably optimal (Tsubouchi et al., [arXiv:2208.09385](https://arxiv.org/abs/2208.09385)).

### The hard wall

Any **unbiased** error-mitigation method costs shots that grow exponentially in $\lambda$, i.e. polynomially in $1/f$ with a power of at least about 1–2, and up to 4 for PEC (probabilistic error cancellation, entry D4). See Section I.

The only ways around this wall are:

- **raise $f$** with fewer or better gates, error detection, or error correction (Section B);
- **accept a controlled bias**, for example with extrapolation or machine-learning fits;
- **use a variational quantity** that stays an upper bound however noisy the data are. SKQD's projected energy is one.

---

## 2. Cost tiers at a glance

| Shot cost vs $f$ | Techniques (entry numbers below) | Bias? |
|---|---|---|
| **About constant** | EMRE (D19), PIE (D18), ML-QEM at inference (D23), CDR after training (D21), classical recovery and local search on samples (C3, C14) | Biased; the size of the bias must be checked |
| **$\sim f^{-1}$** | Symmetry or Gauss-law post-selection done in the circuit (C2, F4), sample-based support discovery (C1), CVaR bounds (C17), error-detection codes (B13) | None for kept shots; undetected errors remain |
| **$\sim f^{-2}$** | Global and observable rescaling: noise-estimation circuits, ODR, self-mitigation, echo normalization (D11–D14); TEM (D7); PNA (D6); QESEM (D8); symmetry verification in post-processing (D25); robust shadows (D30); Hadamard-test or QCELS phase estimation (E5–E8) | Small if the noise is twirled |
| **$\sim f^{-4}$** | PEC (D4), 2-copy virtual distillation (D27) | Unbiased, but unaffordable at $f<0.1$ unless restricted to the lightcone |
| **Raises $f$ itself** | Fewer or native gates, compression, layout choice, error-detection or correction codes, erasure (Section B) | — |

Abbreviations in this table (each is defined fully in its entry):

- **EMRE**: error mitigation by restricted evolution
- **PIE**: physics-inspired extrapolation
- **ML-QEM**: machine-learning quantum error mitigation
- **CDR**: Clifford data regression
- **CVaR**: conditional value-at-risk
- **ODR**: operator decoherence renormalization
- **TEM**: tensor-network error mitigation
- **PNA**: propagated noise absorption
- **QESEM**: Qedma's error-mitigation product
- **QCELS**: quantum complex exponential least squares
- **PEC**: probabilistic error cancellation

---
## A. First measure $f$ (benchmarking that estimates the clean fraction)

You cannot pick a strategy without knowing $f$. These methods measure it directly.

**A1. Layer fidelity and EPLG (error per layered gate)**
- **What it is.** Measures the fidelity of an entire layer of simultaneous two-qubit gates across many qubits, including crosstalk (unwanted interaction between neighbouring qubits). The product of the layer fidelities over the circuit is a direct, predictive estimate of $f$.
- **Low-$f$ evidence.** At 100 qubits, Eagle had a layer fidelity of 0.19 and Heron 0.26. At 80 qubits, Heron reached 0.61.
- **Refs.** [arXiv:2311.05933](https://arxiv.org/abs/2311.05933).

**A2. Mirror circuits**
- **What it is.** Run the circuit followed by its inverse. The ideal outcome is known, so the measured polarization (how far the output stays from fully random) gives the circuit fidelity.
- **Refs.** [arXiv:2112.09853](https://arxiv.org/abs/2112.09853).

**A3. Cycle benchmarking**
- **What it is.** Measures the error per repeated "cycle" of gates across many qubits at once.
- **Refs.** [arXiv:1902.08543](https://arxiv.org/abs/1902.08543).

**A4. Cross-entropy benchmarking (XEB)**
- **What it is.** The estimator is
  $$F_{\rm XEB}=2^n\,\overline{p_{\rm ideal}(x)}-1,$$
  where:
  - $n$ is the number of qubits;
  - $p_{\rm ideal}(x)$ is the classically computed ideal probability of a measured bitstring $x$;
  - the bar means the average over the measured samples.
- **Cost vs $f$.** The statistical error is about $1/\sqrt{S}$, so shots grow as $f^{-2}$.
- **Low-$f$ evidence.** A signal was extracted at $F\sim 2\times10^{-3}$ (Google's 53- and 67-qubit runs).
- **Refs.** [arXiv:1910.11333](https://arxiv.org/abs/1910.11333), [arXiv:2304.11119](https://arxiv.org/abs/2304.11119).

**A5. Gauss-law and symmetry yield (already built into SKQD)**
- **What it is.** The fraction of shots that pass the decoder gives an upper bound on $f$, because undetected errors also pass.
- **Calibration from the manual's emulator.**
  - Accepted yield $\approx 0.82f+0.0015$. The 0.0015 is the 0.15% of fully random 20-bit strings that happen to decode as valid.
  - So if the measured yield is $Y$, then $f\approx (Y-0.0015)/0.82$ (my rearrangement).

**A6. Cycle error reconstruction (CER)**
- **What it is.** Learns the full Pauli-error distribution of each scheduled cycle under randomized compiling (a standard technique that averages random gate variants so that coherent errors behave like random ones; see B2). The result feeds into rescaling or PEC.
- **Refs.** [arXiv:2303.17714](https://arxiv.org/abs/2303.17714).

---

## B. Raise $f$: fewer gates, better gates, detected errors

Every factor-$k$ reduction of $N_{2q}$ turns $f$ into $f^{1/k}$. For example, halving the gate count takes $0.05\to\sqrt{0.05}=0.22$. This is usually the cheapest lever.

**B1. Dynamical decoupling (DD)**
- **What it is.** Pulse sequences on idle qubits (qubits waiting while others run gates) cancel slow dephasing (random phase drift) and crosstalk.
- **Cost.** No extra shots. Used in essentially every large lattice-gauge-theory (LGT) run. Survey of 60 sequences on IBM hardware: UR and QDD sequences performed best; tuned XY4 and CPMG were almost as good.
- **Refs.** [arXiv:2207.03670](https://arxiv.org/abs/2207.03670).

**B2. Pauli twirling / randomized compiling**
- **What it is.** Random Pauli gates are placed around each two-qubit gate and then undone. Averaged over the random variants, coherent errors become stochastic Pauli errors. Coherent errors add up linearly with circuit depth; stochastic errors add up much more slowly.
- **Why it matters.** It does not change $N_{2q}$, but it is the prerequisite that makes rescaling, ZNE (zero-noise extrapolation), PEA and PEC valid.
- **Refs.** [arXiv:1512.01098](https://arxiv.org/abs/1512.01098), [arXiv:2010.00215](https://arxiv.org/abs/2010.00215).

**B3. IBM fractional gates (native $R_{ZZ}(\theta)$ on Heron)**
- **What it is.** One calibrated pulse implements $e^{-i\theta Z\otimes Z/2}$, replacing 2 CZ gates plus single-qubit gates.
  - $\theta$ is the rotation angle.
  - $Z$ is the Pauli-Z operator.
- **Effect on $f$.** For circuits made mostly of $ZZ$ terms, $N_{2q}$ is roughly halved, so $f\to\sqrt f$.
- **Limits** (IBM documentation; there is no arXiv paper):
  - only $0<\theta\le\pi/2$ is allowed;
  - the feature is experimental;
  - it is **not compatible with built-in gate twirling, PEC or PEA**;
  - it is compatible with DD and TREX (twirled readout error extinction, entry C16).

**B4. Layout chosen by layer fidelity, best-of-N transpilation**
- **What it is.** Choose the qubit chain with the best measured layer fidelity (A1). Transpile (compile the circuit onto the chip) with several random seeds and keep the circuit with the fewest two-qubit gates.
- **Low-$f$ evidence.** A 101-qubit LGT run took the best of 10 seeds ([arXiv:2608.02756](https://arxiv.org/abs/2608.02756)).

**B5. Coarse single-step circuits (the SKQD manual's own choice)**
- **What it is.** Use one coarse step $\prod_\gamma e^{-iH_\gamma k\Delta t}$ per circuit instead of $k$ Trotter steps. A Trotter step is one time slice that applies each Hamiltonian piece $H_\gamma$ in turn; $\Delta t$ is the time step and $k$ the number of steps.
- **Effect.** About 1/4 of the depth. In SKQD, any discovered configuration is useful, because the projected diagonalization is exact inside $B$.
- **Evidence.** At 2×3, it covered 62 of the 86 support configurations from one reference, against 41 for full Trotter.

**B6. AQC-Tensor (approximate quantum compiling with tensor networks)**
- **What it is.** Compute the time-evolved state classically as an MPS (matrix product state, a compressed representation of a many-qubit state). Then fit a much shallower parameterized circuit to it, also classically.
- **Effect.** At least a 10× depth reduction at 100 qubits.
- **Refs.** [arXiv:2301.08609](https://arxiv.org/abs/2301.08609).

**B7. Classically optimized or compressed Trotter circuits**
- **What it is.** Optimize the Trotter gate parameters, either with tensor networks or with Riemannian optimization (gradient methods on the curved space of unitary matrices). Fewer, coarser steps then reach the target accuracy.
- **Refs.** [arXiv:2205.11427](https://arxiv.org/abs/2205.11427), [arXiv:2212.07556](https://arxiv.org/abs/2212.07556).

**B8. Variational time evolution with fixed depth (p-VQD)**
- **What it is.** p-VQD (projected variational quantum dynamics) keeps the circuit depth constant in time. The price is many more circuit runs.
- **Refs.** [arXiv:2101.04579](https://arxiv.org/abs/2101.04579).

**B9. ZX-calculus simplification**
- **What it is.** ZX-calculus is a graph rewriting language for circuits. Simplifying the graph and re-extracting a circuit removes redundant two-qubit gates.
- **Effect.** Modest for Trotter circuits.
- **Refs.** [arXiv:1902.03178](https://arxiv.org/abs/1902.03178).

**B10. Trotter order choice and Trotter-step extrapolation**
- **What it is.**
  - Higher-order Trotter formulas multiply $N_{2q}$, so first- or second-order steps plus extrapolation in the step size are often better on noisy hardware.
  - Extrapolating in $\Delta t$ removes the *algorithmic* (Trotter) error, not the hardware error.
- **Refs.** [arXiv:1912.08854](https://arxiv.org/abs/1912.08854) (theory of Trotter error), [arXiv:2212.14144](https://arxiv.org/abs/2212.14144) (step-size extrapolation).

**B11. Circuit cutting / knitting**
- **What it is.** Split a big circuit into smaller pieces, run them separately, and recombine the results with signed weights. Each piece has a higher $f$.
- **Cost.** A shot overhead of $\gamma^2$ per cut, where $\gamma$ is the quasi-probability norm (the sum of absolute values of the recombination weights):

  | What is cut | No classical communication | With classical communication |
  |---|---|---|
  | CZ gate | $9^k$ ($\gamma=3$) | $\to 4^k$ ($\gamma\to2$) |
  | Wire | $16^n$ | $4^n$ |

  Here $k$ is the number of gate cuts and $n$ the number of wire cuts. For a small-angle $R_{ZZ}(\theta)$ gate, $\gamma=1+2|\sin\theta|$ *(textbook result, not re-checked)*, which is cheap.
- **Low-$f$ evidence.** 142 qubits across two linked Eagle processors.
- **Refs.** [arXiv:1909.07534](https://arxiv.org/abs/1909.07534), [arXiv:2205.00016](https://arxiv.org/abs/2205.00016), [arXiv:2302.03366](https://arxiv.org/abs/2302.03366), [arXiv:2303.07340](https://arxiv.org/abs/2303.07340), [arXiv:2402.17833](https://arxiv.org/abs/2402.17833).

**B12. Dynamic circuits (mid-circuit measurement + feed-forward)**
- **What it is.** Measure some qubits partway through the circuit and use the results to choose later gates. Long-range CNOTs, GHZ states (maximally entangled "cat" states) and toric-code states (a $\mathbb Z_2$ gauge-theory ground state) can then be prepared in constant depth instead of depth that grows with distance.
- **Low-$f$ evidence.**
  - A CNOT teleported across 101 qubits ([arXiv:2308.13065](https://arxiv.org/abs/2308.13065)).
  - Toric code on Quantinuum ([arXiv:2302.01917](https://arxiv.org/abs/2302.01917)).
  - DD plus ZNE applied to dynamic circuits removed up to 99% of the error ([arXiv:2605.05256](https://arxiv.org/abs/2605.05256)).

**B13. Error-detection codes: Iceberg $[[k{+}2,k,2]]$ and $[[4,2,2]]$**
- **What it is.** Encode $k$ logical qubits in $k+2$ physical qubits. Any single error is detected, and the shot is discarded.
- **Cost.** About $1/f_{\rm keep}$.
- **Low-$f$ evidence.**
  - 8 logical qubits ([arXiv:2211.06703](https://arxiv.org/abs/2211.06703)).
  - QAOA (a quantum optimization algorithm) on 20 logical qubits ([arXiv:2409.12104](https://arxiv.org/abs/2409.12104)).
  - Compiling the code together with the algorithm raised the post-selection rate from 4% to 33% at 22 qubits ([arXiv:2504.21172](https://arxiv.org/abs/2504.21172)).
  - 48–94 logical qubits beyond break-even on Quantinuum Helios ([arXiv:2602.22211](https://arxiv.org/abs/2602.22211)).
  - $[[4,2,2]]$ for chemistry ([arXiv:1910.00129](https://arxiv.org/abs/1910.00129)).
- **Fit.** Best on all-to-all-connected trapped ions, which you can reach through Azure.

**B14. Erasure conversion and leakage detection**
- **What it is.** The hardware is engineered so that most errors are *heralded*: the device signals where they happened. You then discard or correct those shots.
  - **Erasure** = a heralded error.
  - **Leakage** = a qubit leaving its two computational levels.
- **Low-$f$ evidence.**
  - In Rydberg atoms, about 98% of errors become erasures ([arXiv:2201.03540](https://arxiv.org/abs/2201.03540)).
  - Superconducting erasure qubits ([arXiv:2208.05461](https://arxiv.org/abs/2208.05461)).
  - Leakage-detection gadgets were used in a 56-qubit $\mathbb Z_2$ LGT run on Quantinuum H2 ([arXiv:2604.07435](https://arxiv.org/abs/2604.07435)).

**B15. Qudit encodings**
- **What it is.** Store a truncated gauge link in one $d$-level system (a qudit, a quantum unit with $d$ levels instead of 2) instead of several qubits.
- **Low-$f$ evidence.** For an SU(2) ladder of 3 plaquettes on Innsbruck ions, this needed **67 two-qudit gates against about 1,088 qubit gates (16×)**.
- **Fit.** Not available on IBM hardware.
- **Refs.** [arXiv:2605.05841](https://arxiv.org/abs/2605.05841), [arXiv:2203.15541](https://arxiv.org/abs/2203.15541), [arXiv:2310.12110](https://arxiv.org/abs/2310.12110).

**B16. Dynamic gauge induction**
- **What it is.** Start from a simpler three-body XXX model (a spin model with equal couplings along $x$, $y$ and $z$). Strong Gauss-law penalty terms then make it follow the U(1) quantum-link Schwinger model, through the quantum Zeno effect (frequent or strong "checks" freeze transitions out of a subspace).
- **Effect.** About 5× fewer two-qubit layers per step, so $f\to f^{1/5}$; for example $0.01\to0.40$.
- **Low-$f$ evidence.** 101 qubits on ibm_basquecountry.
- **Refs.** [arXiv:2608.02756](https://arxiv.org/abs/2608.02756).

**B17. Early fault tolerance / logical qubits**
- **Quantinuum and Microsoft.** Logical error rates 9.8–800× below physical ([arXiv:2404.02280](https://arxiv.org/abs/2404.02280)).
- **Quantinuum Helios.** Two-qubit error $\varepsilon=7.9\times10^{-4}$ ([arXiv:2511.05465](https://arxiv.org/abs/2511.05465)).
  - With $f=(1-\varepsilon)^{N_{2q}}$, the largest circuit that keeps $f\ge0.1$ is
    $$N_{2q}=\ln(0.1)/\ln(1-7.9\times10^{-4})\approx 2{,}900$$
    two-qubit gates.
  - At $\varepsilon=2.3\times10^{-3}$, the same formula gives about 1,000.
- **IBM gross qLDPC code.** qLDPC = quantum low-density parity-check code. It holds 12 logical qubits in 288 physical qubits ([arXiv:2308.07915](https://arxiv.org/abs/2308.07915)).
- **STAR architecture.** Error-corrected Clifford gates plus non-corrected analog rotations ([arXiv:2303.13181](https://arxiv.org/abs/2303.13181)).

---
## C. Sample-based methods (SKQD, SQD, QSCI and relatives): the family SKQD belongs to

These methods output **configurations** (bitstrings), not averages. The energy comes from diagonalizing $H$ classically inside the sampled set $B$. Hardware noise therefore changes *which* configurations are found. It cannot push the energy below the true ground-state energy $E_0$: the result stays variational.

### C-i. Core methods

**C1. QSCI / SQD / SKQD (the base methods)**
- **QSCI** (quantum-selected configuration interaction): sample from a prepared state, keep the frequent bitstrings, and diagonalize $H$ in their span.
- **SQD** (sample-based quantum diagonalization): IBM's large-scale version, with configuration recovery (entry C3).
- **SKQD** (sample-based Krylov quantum diagonalization): samples from time-evolved states $e^{-iHk\Delta t}|\psi_0\rangle$. Here $|\psi_0\rangle$ is the starting state and $k=0,1,2,\dots$ indexes the time steps. SKQD has a polynomial-time convergence proof when the ground state is concentrated on few configurations.
- **Cost vs $f$.** Shots $\propto 1/(fp)$ (the shot rule in Section 1).
- **Low-$f$ evidence.** SKQD on 85 qubits with up to 6,153 two-qubit gates at $\varepsilon\approx2.8\times10^{-3}$. That gives $f\sim e^{-17}$ *(my estimate)*, yet the results agree with DMRG (density-matrix renormalization group, the standard classical reference method for 1D and quasi-1D systems).
- **Refs.** [arXiv:2302.11320](https://arxiv.org/abs/2302.11320) (QSCI), [arXiv:2405.05068](https://arxiv.org/abs/2405.05068) (SQD), [arXiv:2501.09702](https://arxiv.org/abs/2501.09702) (SKQD).

**C2. Symmetry / Gauss-law post-selection of samples**
- **What it is.** Discard bitstrings in the wrong sector: wrong total charge, wrong particle number, or a broken Gauss law.
- **Low-$f$ evidence.** Closest precedent to your project: SKQD for the Schwinger model (1+1-dimensional quantum electrodynamics) with a θ-term (a topological term in the action), post-selecting on zero total charge.
  - Relative energy error $1.4\times10^{-3}$ at 20 qubits on IBM Heron r2.
  - Extended to 30 qubits.
  - 4 qubits on a Mainz trapped-ion device.
- **Refs.** [arXiv:2510.26951](https://arxiv.org/abs/2510.26951).

**C3. Self-consistent configuration recovery (S-CORE)**
- **What it is.** Do not throw away invalid bitstrings; **repair** them.
  - Bits are flipped at random, weighted by how far each bit's value is from its average occupation. Each orbital's occupation (how often it is filled) is averaged over the current best eigenvector.
  - The average is then recomputed and the loop repeated, typically 3–5 times.
- **Cost vs $f$.** It reached the same accuracy with about **2% usable signal** as without recovery at about 20%.
- **Low-$f$ evidence.**
  - N₂ molecule: 58 qubits, up to 3,500 two-qubit gates at 99.77% gate fidelity, so $f\sim3\times10^{-4}$ *(my estimate)*.
  - [4Fe-4S] iron–sulfur cluster: 77 qubits.
- **Software.** The `qiskit-addon-sqd` package implements it for particle-number constraints. A Gauss-law version needs custom code (see Section K).
- **Refs.** [arXiv:2405.05068](https://arxiv.org/abs/2405.05068).

**C4. Code-space recovery (dual-rail constraint + stochastic repair)**
- **What it is.** Each logical bit is stored in two physical qubits, $|0\rangle\to|01\rangle$ and $|1\rangle\to|10\rangle$ (dual-rail encoding). Pairs reading 00 or 11 are invalid and are repaired with occupancies taken from the current best eigenvector. The loop runs 7–22 iterations.
- **Low-$f$ evidence.**
  - Only **0.024%–4.8%** of bitstrings were fully valid, so $f\sim10^{-4}$–$10^{-2}$ and plain post-selection is useless.
  - Recovery still roughly halved the error relative to DMRG for the 36-site 2D transverse-field Ising model (from 0.320 to 0.167).
  - Hardware: 72 qubits, up to 1,132 two-qubit gates, IBM Heron r2.
- **Why it matters here.** Your Gauss-law decoder plays the same role as the dual-rail check. This is the most directly transferable recovery scheme.
- **Refs.** [arXiv:2607.10227](https://arxiv.org/abs/2607.10227).

**C5. Cluster-adaptive SQD (CSQD)**
- **What it is.** Cluster the sampled strings and give each cluster its own reference occupancy for recovery.
- **Result.** Energies up to 16 mHa lower for stretched N₂ and up to 58 mHa lower for [2Fe-2S], compared with SQD. (mHa = milli-hartree; 1 Ha ≈ 27.2 eV.)
- **Refs.** [arXiv:2603.09346](https://arxiv.org/abs/2603.09346).

**C6. Deterministic-field SQD (DF-SQD)**
- **What it is.** Shallow circuits that preserve particle number propose configurations. Recovery is followed by strict post-selection, then by selected-CI diagonalization (CI = configuration interaction, a wavefunction written as a sum over configurations; "selected" means only chosen ones are kept).
- **Low-$f$ evidence.** Run on IBM hardware.
- **Refs.** [arXiv:2609.01264](https://arxiv.org/abs/2609.01264).

### C-ii. Better ways to generate samples (raise the hit rate per clean shot)

**C7. Multi-reference starting states**
- **What it is.** Start from several reference configurations instead of one.
- **Evidence.** In the SKQD manual at 2×3, recall (the fraction of the important support configurations that were found) rose from 41 of 86 to 86 of 86.
- **Emulated result.** At $f=0.10$, 8 references × 5 coarse circuits with $5\times10^4$ shots in total gave a Ritz error of $2.9\times10^{-3}$ and recall 0.97. (The Ritz value is the eigenvalue found inside $B$; the Ritz error is its distance from the exact value.)

**C8. Hamiltonian-simulation-based QSCI (HSB-QSCI) and QSCI from a time-evolved state (TE-QSCI)**
- **What it is.** Sample from real-time evolution of an approximate state.
- **Result.** More than 99.18% of the correlation energy using about 1% of the configurations (Slater determinants), on up to 36 IBM qubits. The correlation energy is the part of the energy beyond the mean-field approximation.
- **Refs.** [arXiv:2412.07218](https://arxiv.org/abs/2412.07218), [arXiv:2510.23154](https://arxiv.org/abs/2510.23154), [arXiv:2412.13839](https://arxiv.org/abs/2412.13839).

**C9. SqDRIFT**
- **What it is.** SKQD with time evolution built by qDRIFT, a randomized method that samples Hamiltonian terms in proportion to their size. Circuit depth then depends on the sum of the Hamiltonian's coefficients, not on the number of terms.
- **Low-$f$ evidence.** Coronene, at least 48 qubits. Sources disagree on the largest size (48 vs 72/100 qubits).
- **Refs.** [arXiv:2508.02578](https://arxiv.org/abs/2508.02578).

**C10. ADAPT-QSCI**
- **What it is.** Grows the input circuit step by step, using QSCI results to choose each step.
- **Evidence.** Robust at 1% two-qubit and 1% readout error on 8 qubits.
- **Refs.** [arXiv:2311.01105](https://arxiv.org/abs/2311.01105).

**C11. Bias-field counterdiabatic optimization (BF-DCQO)**
- **What it is.**
  - A short counterdiabatic circuit: a circuit with added terms that suppress unwanted transitions during an adiabatic sweep.
  - The lowest-energy samples set a "bias field" that seeds the next round.
  - Raw samples are polished by greedy bit flips.
- **Why it tolerates noise.** Noise only makes the prior worse; it does not bias the final classical search.
- **Low-$f$ evidence.** 156 qubits on IBM, and protein folding on 36–61 trapped-ion qubits.
- **Refs.** [arXiv:2405.13898](https://arxiv.org/abs/2405.13898), [arXiv:2409.04477](https://arxiv.org/abs/2409.04477), [arXiv:2505.08663](https://arxiv.org/abs/2505.08663), [arXiv:2506.07866](https://arxiv.org/abs/2506.07866), [arXiv:2604.26861](https://arxiv.org/abs/2604.26861).

### C-iii. Machine-learning recovery and extension

**C12. Generative models trained on noisy samples**

| Method | What it uses | Hardware / scale | Ref |
|---|---|---|---|
| PIGen-SQD | Physics-informed generative model | IBM Heron r2 | [arXiv:2512.06858](https://arxiv.org/abs/2512.06858) |
| QiankunNet-QSCI | Transformer neural network rebuilds the wavefunction from sparse samples | 40-qubit [2Fe-2S] on Zuchongzhi 3.1 at chemical accuracy; nitrogenase P-cluster within 12 mHa of DMRG | [arXiv:2605.24617](https://arxiv.org/abs/2605.24617) |
| Q-WAVE | Variational autoencoder | — | [arXiv:2609.07972](https://arxiv.org/abs/2609.07972) |
| GenKSR | Transformer and Mamba sequence models trained on Krylov samples | 20-qubit IBM chains | [arXiv:2512.19420](https://arxiv.org/abs/2512.19420) |

- **For your project.** Your manual's "device + ML recovery/extension" protocol (Section 7.5) is in this class.
- **Gap.** No diffusion-model or normalizing-flow configuration recovery was found. GFlowNets (generative flow networks) are listed as an open gap in the review [arXiv:2608.05314](https://arxiv.org/abs/2608.05314).

**C13. Hamming-distance clustering with Bayesian reweighting (Q-Cluster)**
- **What it is.**
  - Cluster noisy bitstrings by Hamming distance (the number of differing bits).
  - Take each cluster centre by majority vote per qubit.
  - Reweight using a bit-flip noise model.
- **Evidence.** Handles bit-flip rates up to 40% per qubit.
- **Refs.** [arXiv:2504.10801](https://arxiv.org/abs/2504.10801).

### C-iv. Classical hand-off: the device only seeds a classical method

**C14. Greedy / local-search repair of samples**
- **What it is.** An $O(n)$ classical pass of single bit flips that undoes bit-flip damage ($n$ is the number of bits).
- **Evidence.** Max-Cut and spin glasses on 127–156 IBM qubits.
- **Refs.** [arXiv:2406.01743](https://arxiv.org/abs/2406.01743).

**C15. Selected-CI / perturbative extension of the sampled subspace**
- **Active-sampling SQD (AS-SQD).** Adds configurations chosen by an Epstein–Nesbet second-order perturbation estimate (PT2: second-order perturbation theory). Refs: [arXiv:2603.13536](https://arxiv.org/abs/2603.13536).
- **QSCI plus multireference perturbation theory.** Configuration space more than 200× smaller (SiH₄ on 42 IQM qubits). Refs: [arXiv:2509.02525](https://arxiv.org/abs/2509.02525).
- **Extended SQD (ext-SQD).** Refs: [arXiv:2411.00468](https://arxiv.org/abs/2411.00468).
- **SQD as the trial state for ph-AFQMC.** ph-AFQMC is phaseless auxiliary-field quantum Monte Carlo, a classical stochastic method; it recovers about 100 mHa of correlation energy. Refs: [arXiv:2503.05967](https://arxiv.org/abs/2503.05967).
- **For your project.** This is the "CIPSI" row of your manual's comparison table. CIPSI is a classical selected-CI method that adds configurations iteratively, using perturbation theory to choose them.

**C16. Readout mitigation for samples**
- **M3** (matrix-free measurement mitigation): corrects readout errors only within the subspace of bitstrings actually observed. Refs: [arXiv:2108.12518](https://arxiv.org/abs/2108.12518).
- **TREX** (twirled readout error extinction): randomizes the readout and rescales. Refs: [arXiv:2012.09738](https://arxiv.org/abs/2012.09738).
- **Bit-flip averaging.** Refs: [arXiv:2106.05800](https://arxiv.org/abs/2106.05800).
- **Iterative Bayesian unfolding (IBU),** borrowed from high-energy physics: repeatedly reweights a prior through the readout response matrix and never produces negative probabilities. Refs: [arXiv:1910.01969](https://arxiv.org/abs/1910.01969), [arXiv:2204.05757](https://arxiv.org/abs/2204.05757).
- **Bayesian analog-signal methods** (work on the raw readout signal). Refs: [arXiv:2408.00869](https://arxiv.org/abs/2408.00869).
- **Scope.** These fix readout errors only, not gate errors. With 1% readout error on 20 qubits they recover the factor 0.82.

### C-v. Certified and provable estimators built from noisy samples

**C17. CVaR bounds from noisy samples**
- **What it is.** CVaR (conditional value-at-risk) is the mean of the best (lowest) fraction $\alpha$ of sampled values.
- **The result.** Suppose the noisy distribution $\tilde p_x$ satisfies $\tilde p_x\ge p_x/C$ for every bitstring $x$, where:
  - $\tilde p_x$ is the noisy probability of bitstring $x$;
  - $p_x$ is its ideal probability;
  - $C$ is a constant.

  If $\alpha\le1/C$, then the CVaR of the lowest $\alpha$-tail and the mean of the highest $\alpha$-tail of the noisy samples **bound the noise-free expectation value from below and above**.
- **Choosing $\alpha$.** Measured layer fidelities give $C$, so $\alpha\approx f$.
- **Cost vs $f$.** About $1/f$ shots, compared with $f^{-4}$ for PEC.
- **Low-$f$ evidence.** 127 qubits.
- **Refs.** [arXiv:2312.00733](https://arxiv.org/abs/2312.00733); original CVaR: [arXiv:1907.04769](https://arxiv.org/abs/1907.04769).

**C18. Quantum-enhanced Markov chain Monte Carlo (QMCMC)**
- **What it is.** The quantum circuit only *proposes* moves. A classical Metropolis–Hastings step accepts or rejects them; it accepts a move with probability $\min(1,\pi(s')/\pi(s))$, where:
  - $\pi$ is the target distribution;
  - $s$ is the current configuration;
  - $s'$ is the proposed configuration.

  The proposal is symmetric, and twirling keeps it symmetric on average under noise.
- **Effect of noise.** **The answer stays exact at any $f$.** Noise only slows mixing (how fast the chain forgets its starting point). As $f\to0$ it becomes ordinary MCMC with uniform proposals.
- **Refs.** [arXiv:2203.12497](https://arxiv.org/abs/2203.12497), [arXiv:2305.08789](https://arxiv.org/abs/2305.08789), [arXiv:2405.04247](https://arxiv.org/abs/2405.04247).

**C19. Variational bound + Weinstein / Kato–Temple intervals (already in your manual, Step 5.3)**
- **What it is.** For any $B$, the lowest eigenvalue in $B$, $E_R$, satisfies $E_R\ge E_0$.
- **Residual.** $r_H=\|(H-E_R)\psi_R\|$, where $\psi_R$ is the Ritz vector (the eigenvector found in $B$) and $\|\cdot\|$ is the vector norm.
- **Weinstein bound.** Some exact eigenvalue lies in $[E_R-r_H,\,E_R+r_H]$.
- **Kato–Temple bound.** $E_0\ge E_R-r_H^2/(\alpha_{\rm gap}-E_R)$, where $\alpha_{\rm gap}$ is a lower bound on the first excited energy $E_1$.
- **Why it matters at low $f$.** These **do not depend on $f$ at all**. They are the rigorous safety net when samples are very noisy.

**C20. Good–Turing estimate of missing probability**
- **What it is.** $\hat M_0=N_1/S$, where:
  - $\hat M_0$ is the estimated total probability of configurations never seen;
  - $N_1$ is the number of configurations seen exactly once among the accepted shots;
  - $S$ is the number of accepted shots.

  This estimates how much ground-state weight your sampled support might be missing, i.e. a practical monitor for $\varepsilon_B$ in the manual's bound (6).
- **Status.** No quantum-computing paper was found that uses it. Applying it here is **my suggestion**.
- **Refs.** Statistics background: [arXiv:2503.14313](https://arxiv.org/abs/2503.14313).

**C21. Syndrome-count extrapolation** *(my label; the paper does not name it this way)*
- **What it is.**
  - Sort shots by $w$, the number of failed checks (stabilizer or Gauss-law violations per shot).
  - Fit the observable as $m(w)=a+bw$, where $a$ and $b$ are fit constants.
  - Extrapolate to $w=0$.

  This uses **all** shots, unlike post-selection.
- **Low-$f$ evidence (the strongest $f\ll0.1$ example found).** Quantinuum Helios, 90 qubits, 3,439 two-qubit gates. Only about 0.4% of shots were free of leakage. Fermi–Hubbard pairing correlations were still extracted.
- **Refs.** [arXiv:2511.02125](https://arxiv.org/abs/2511.02125).

### C-vi. Warnings that are specific to sample-based methods at low $f$

**C22. Random configurations can reproduce the benchmark numbers**
- **The finding.** Two 2026 studies show that once noise is high, **uniformly random configurations plus configuration recovery reproduce the published SQD benchmark energies**. In one case only 0.17% of samples had the right electron number, and adding *more* bit-flip noise and then recovering *improved* the energy.
- **What this means.** At that $f$, the recovery algorithm, not the device, is producing the answer.
- **Fix.** Always report a random-configuration baseline with the same $|B|$, the number of configurations in the subspace. Your manual's 7-protocol table already does this.
- **Refs.** [arXiv:2605.23697](https://arxiv.org/abs/2605.23697), [arXiv:2608.11569](https://arxiv.org/abs/2608.11569).

**C23. Fundamental limitations of QSCI**
- **The finding.** Sampling keeps returning configurations it has already seen. Low $f$ makes this worse by a factor $1/f$.
- **Refs.** [arXiv:2501.07231](https://arxiv.org/abs/2501.07231).

**C24. Purely classical replacements**
- **The finding.** TrimCI starts from random determinants and repeatedly expands and trims the set. It matched the 77-qubit [4Fe-4S] quantum result with $10^6$ times fewer determinants.
- **What this means.** Classical baselines must be strong.
- **Refs.** [arXiv:2511.14734](https://arxiv.org/abs/2511.14734).

**C25. Hardware robustness of SQD**
- **The finding.** Layout and mitigation choices matter in the first recovery iteration, but the differences shrink within a few iterations. Accuracy stops improving beyond moderate shot budgets.
- **Refs.** [arXiv:2607.18196](https://arxiv.org/abs/2607.18196).

---
## D. Error mitigation for expectation values (averages of observables)

Use these when the quantity you want is an average, $\langle O\rangle$ — for example the electric energy, a plaquette value or a correlator — rather than a set of configurations. In SKQD these methods matter for any observable you measure directly on hardware, and for cross-checks.

### D-i. Extrapolation family

**D1. Zero-noise extrapolation (ZNE)**
- **What it is.** Run the circuit at amplified noise levels $G=1,2,3,\dots$ and fit $\langle O\rangle(G)$. Then extrapolate the fit to $G=0$.
  - $G$ is the noise-amplification factor; $G=1$ is the hardware's own noise.
  - **Ways to amplify the noise:** stretch the control pulses, or "fold" gates (replace $U$ by $UU^\dagger U$).
  - **Fit models:** Richardson (polynomial), exponential, or multi-exponential.
- **Cost.** Richardson extrapolation with $M$ points multiplies the shots by $(2^M-1)^2$. The signal itself decays as about $f_{\rm LC}^{\,G}$, so the variance grows at least as $f_{\rm LC}^{-2}$ *(my estimate)*. The output is biased.
- **Low-$f$ evidence.** 26 qubits with 1,080 CNOTs ([arXiv:2108.09197](https://arxiv.org/abs/2108.09197)).
- **Refs.** [arXiv:1612.02058](https://arxiv.org/abs/1612.02058), [arXiv:1611.09301](https://arxiv.org/abs/1611.09301), [arXiv:1805.04492](https://arxiv.org/abs/1805.04492), [arXiv:1712.09271](https://arxiv.org/abs/1712.09271), [arXiv:2005.10921](https://arxiv.org/abs/2005.10921), [arXiv:2007.01265](https://arxiv.org/abs/2007.01265).

**D2. Probabilistic error amplification (PEA)**
- **What it is.** ZNE in which the noise is first *learned* as a sparse Pauli–Lindblad model (D3). It is then amplified exactly, by inserting extra random Paulis.
- **Low-$f$ evidence.** IBM's "utility" experiment (Kim et al., *Nature* 618, 500, 2023): 127 qubits, 2,880 CNOTs, kicked Ising model, global $f\sim e^{-29}$ *(my estimate)*.
- **Refs.** The Nature paper has no arXiv version.

**D3. Sparse Pauli–Lindblad (SPL) noise learning**
- **What it is.** Each twirled layer's noise is modelled as
  $$\Lambda(\rho)=\exp\!\Big[\sum_k\lambda_k\big(P_k\rho P_k-\rho\big)\Big],$$
  where:
  - $\Lambda$ is the noise channel (the map that the noise applies to the state);
  - $\rho$ is the state (density matrix);
  - $P_k$ are nearest-neighbour Pauli operators;
  - $\lambda_k$ are their error rates, learned from circuits of different depths.
- **Role.** It is the shared noise model behind PEC, PEA, TEM and PNA.
- **Caveat.** Drift caused by two-level-system (TLS) defects can break it. Noise stabilization addresses this ([arXiv:2407.02467](https://arxiv.org/abs/2407.02467)).
- **Refs.** [arXiv:2201.09866](https://arxiv.org/abs/2201.09866), [arXiv:2311.11639](https://arxiv.org/abs/2311.11639).

### D-ii. Inverting the noise

**D4. Probabilistic error cancellation (PEC)**
- **What it is.** Write the inverse of the noise as a mixture of runnable operations with some negative weights (a "quasi-probability" decomposition). Sample from that mixture and reweight by sign.
- **Output.** Unbiased.
- **Cost.** The quasi-probability norm is $\gamma\approx e^{2\lambda}=f^{-2}$, so the shot cost is $\gamma^2\approx e^{4\lambda}=f^{-4}$:
  - $10^4\times$ more shots at $f=0.1$;
  - $10^8\times$ more at $f=0.01$.
- **When usable.** Only if restricted to a lightcone with $f_{\rm LC}\gtrsim0.1$–$0.3$.
- **Refs.** [arXiv:1612.02058](https://arxiv.org/abs/1612.02058), [arXiv:2201.09866](https://arxiv.org/abs/2201.09866), [arXiv:2210.00921](https://arxiv.org/abs/2210.00921).

**D5. Lightcone and shaded-lightcone PEC; Pauli-error-propagation PEC**
- **What it is.** Cancel only the errors that can actually reach the measured observable. The cost becomes $e^{4\lambda_{\rm eff}}$ with $\lambda_{\rm eff}\ll\lambda$, where $\lambda_{\rm eff}$ is the expected number of errors that matter for that observable.
- **Evidence.** About a 100× runtime saving for a 127-qubit Trotter circuit (a runtime estimate, not a hardware run).
- **Refs.** [arXiv:2409.04401](https://arxiv.org/abs/2409.04401), [arXiv:2412.01311](https://arxiv.org/abs/2412.01311).

**D6. Propagated noise absorption (PNA)**
- **What it is.**
  1. Learn the SPL noise model.
  2. Classically propagate the *inverse* noise through the circuit using Pauli propagation (tracking how Pauli operators transform gate by gate).
  3. Fold the result into a modified observable $\tilde O$.
  4. Measure $\tilde O$ on the ordinary noisy circuit.

  No extra random circuits are needed.
- **Evidence.** 56 qubits.
- **Software.** `qiskit-addon-pna`.
- **Refs.** [arXiv:2606.20441](https://arxiv.org/abs/2606.20441).

**D7. Tensor-network error mitigation (TEM)**
- **What it is.**
  1. Measure with informationally complete measurements: randomized local measurements that capture everything about the state.
  2. Build the inverse noise map classically as a tensor network.
  3. Apply it to the data in post-processing.
- **Cost.** The quasi-probability norm is $\gamma_{\rm TEM}\approx\sqrt{\gamma_{\rm PEC}}$, so the shot cost is $\gamma_{\rm TEM}^2\approx\gamma_{\rm PEC}\approx f^{-2}$. That is quadratically better than PEC.
- **Low-$f$ evidence.** 91 qubits, 4,095 two-qubit gates, global $f\sim e^{-20}$ to $e^{-40}$ *(my estimate)*.
- **Refs.** [arXiv:2307.11740](https://arxiv.org/abs/2307.11740), [arXiv:2411.00765](https://arxiv.org/abs/2411.00765).

**D8. QESEM (Qedma)**
- **What it is.** Characterization-based, unbiased mitigation combined with error suppression. The quasi-probability norm is $W\approx e^{2\,\mathrm{IF}\cdot V_A}\sim f_{\rm LC}^{-2}$, where:
  - $W$ is the quasi-probability norm;
  - IF is the infidelity per gate;
  - $V_A$ is the "active volume", the number of gates inside the lightcone.
- **Low-$f$ evidence.** 103 qubits, 832 RZZ gates at 99.4% fidelity, with active volume 301.
  - Global: $f=0.994^{832}\approx0.007$.
  - Lightcone: $f_{\rm LC}=0.994^{301}\approx0.16$.
- **Refs.** [arXiv:2508.10997](https://arxiv.org/abs/2508.10997), [arXiv:2607.24937](https://arxiv.org/abs/2607.24937).

**D9. Randomized compiling / Pauli twirling** — see B2. It is a prerequisite for D1–D8 and D11–D14.

**D10. Noise stabilization**
- **What it is.** Tune the qubits away from defect (TLS) resonances so that the learned noise model stays valid over time.
- **Refs.** [arXiv:2407.02467](https://arxiv.org/abs/2407.02467).

### D-iii. Rescaling: the workhorse at very low $f$

**D11. Global depolarizing rescaling and noise-estimation circuits**
- **What it is.** Assume $\langle O\rangle_{\rm noisy}=F\langle O\rangle_{\rm ideal}$. Measure $F$ on a twin circuit, then divide by it. The twin has the same gate structure, but its answer is known: for example, non-Clifford rotations set to identity, or the couplings switched off.
- **Cost.** About $F^{-2}$. For global depolarizing noise this is provably optimal.
- **Refs.** [arXiv:2103.08591](https://arxiv.org/abs/2103.08591), [arXiv:2101.01690](https://arxiv.org/abs/2101.01690), [arXiv:2111.14907](https://arxiv.org/abs/2111.14907) (random circuits turn local noise into global white noise).

**D12. Operator decoherence renormalization (ODR)**
- **What it is.** D11 done separately for each observable. Each operator $O$ gets its own factor:
  $$1-\eta_O=\frac{\langle O\rangle_{\rm mit}^{\rm meas}}{\langle O\rangle_{\rm mit}^{\rm pred}},$$
  where:
  - $\eta_O$ is the fractional loss of signal for operator $O$;
  - "mit" means the mitigation circuit;
  - "meas" means measured on hardware;
  - "pred" means computed classically.
- **Low-$f$ evidence.**
  - Schwinger-model vacuum on 100 qubits.
  - Hadron dynamics on **112 qubits with 13,858 two-qubit gates** (global $f\sim e^{-30}$ or less).
  - SU(2) thermalization on chains of up to 151 plaquettes.
- **Refs.** [arXiv:2308.04481](https://arxiv.org/abs/2308.04481), [arXiv:2401.08044](https://arxiv.org/abs/2401.08044), [arXiv:2603.23948](https://arxiv.org/abs/2603.23948), [arXiv:2209.10781](https://arxiv.org/abs/2209.10781).

**D13. Self-mitigation (forward–backward Trotter)**
- **What it is.** The calibration circuit runs $N/2$ Trotter steps forward and $N/2$ steps backward, so its ideal output is the initial state. It has *exactly* the same CNOT count as the physics circuit.
- **Evidence.** Demonstrated for **SU(2)** lattice gauge theory on IBM hardware.
- **Refs.** [arXiv:2205.09247](https://arxiv.org/abs/2205.09247).

**D14. Echo normalization**
- **What it is.** Normalize measured signals by a global rescaling factor obtained from echo circuits (forward-then-backward evolution).
- **Evidence.**
  - Google's 2025 "Quantum Echoes" OTOC experiment (OTOC = out-of-time-order correlator, a measure of how information spreads), 103-qubit chip.
  - IBM 2026: $S_\delta\approx\tilde S_\delta/\tilde S_0$, where $\tilde S_\delta$ is the measured signal for perturbation strength $\delta$ and $\tilde S_0$ is the same circuit at $\delta=0$.
- **Refs.** [arXiv:2506.10191](https://arxiv.org/abs/2506.10191), [arXiv:2607.25998](https://arxiv.org/abs/2607.25998).

**D15. Clifford perturbation theory (CPT) mitigation**
- **What it is.** Learn a zeroth-order model of the noise and invert it.
- **Evidence.** (2+1)D U(1) quantum link model, 112 qubits on ibm_pittsburgh.
- **Refs.** [arXiv:2606.19601](https://arxiv.org/abs/2606.19601).

### D-iv. Extrapolation guided by physics

**D16. GUESS (Guiding Extrapolations from Symmetry decayS)**
- **What it is.** Watch how a *conserved* quantity decays as noise is amplified (ideally it would not change at all). Learn the extrapolation from that decay and apply it to the target observables.
- **Low-$f$ evidence.** 100 qubits, **up to 8,000 CZ gates**, about 10% relative error, about 2× the shots of ZNE.
- **Relevance.** Gauss-law operators are natural conserved quantities to use here.
- **Refs.** [arXiv:2603.13060](https://arxiv.org/abs/2603.13060).

**D17. Global randomized error cancellation (GREC)**
- **What it is.** Noise-cancelling coefficients are learned in one regime and transferred to another.
- **Evidence.** Schwinger model, simulation only.
- **Refs.** [arXiv:2507.06601](https://arxiv.org/abs/2507.06601).

**D18. Physics-inspired extrapolation (PIE)**
- **What it is.** ZNE with a fit form derived from physics. Shot overhead is constant. The fitted slope also certifies the hardware.
- **Evidence.** 84 qubits on IBM.
- **Refs.** [arXiv:2505.07977](https://arxiv.org/abs/2505.07977).

**D19. Error mitigation by restricted evolution (EMRE / HEMRE)**
- **What it is.** Trade a known, computable bias for a **constant** shot overhead.
- **Evidence.** Simulation only.
- **Refs.** [arXiv:2409.06636](https://arxiv.org/abs/2409.06636).

### D-v. Learning-based

**D20. Learning-based QEM**
- **What it is.** Learn the mitigation coefficients from training circuits that are classically simulable.
- **Refs.** [arXiv:2005.07601](https://arxiv.org/abs/2005.07601).

**D21. Clifford data regression (CDR) and variable-noise CDR (vnCDR)**
- **What it is.**
  1. Replace most non-Clifford gates with Clifford gates; Clifford circuits are cheap to simulate classically.
  2. Fit $\langle O\rangle_{\rm ideal}=a\langle O\rangle_{\rm noisy}+b$ on these training circuits, where $a$ and $b$ are fit constants.
  3. Apply the fit to the real circuit.

  vnCDR adds noise-scaled data, as in ZNE.
- **Refs.** [arXiv:2005.10189](https://arxiv.org/abs/2005.10189), [arXiv:2011.01157](https://arxiv.org/abs/2011.01157), [arXiv:2511.03556](https://arxiv.org/abs/2511.03556), [arXiv:2412.09518](https://arxiv.org/abs/2412.09518).

**D22. Neural error mitigation**
- **What it is.** A neural quantum state (a neural network that represents a wavefunction) is trained on noisy data and then refined variationally.
- **Refs.** [arXiv:2105.08086](https://arxiv.org/abs/2105.08086).

**D23. ML-QEM (random forests, multilayer perceptrons, graph neural networks)**
- **What it is.** A regression model from noisy values plus circuit features to ideal values.
- **Evidence.** Up to 100 qubits, with accuracy comparable to ZNE at lower cost. One study works in the *high-noise* regime where signals are strongly suppressed.
- **Refs.** [arXiv:2309.17368](https://arxiv.org/abs/2309.17368), [arXiv:2310.13382](https://arxiv.org/abs/2310.13382), [arXiv:2604.16815](https://arxiv.org/abs/2604.16815), [arXiv:2512.12578](https://arxiv.org/abs/2512.12578), [arXiv:2511.07092](https://arxiv.org/abs/2511.07092).
- **Caution.** Extrapolating far from the training circuits is the main risk.

### D-vi. Purification, verification and subspace methods

**D24. Symmetry verification**
- **What it is.** Measure conserved quantities (particle number, Gauss law). Either discard violating shots, or project the violation out in post-processing.
- **Cost.** $\mathrm{Tr}[\Pi\rho]^{-1}$ if done in the circuit, $\mathrm{Tr}[\Pi\rho]^{-2}$ if done in post-processing. Here $\Pi$ is the projector onto the symmetric subspace, and $\mathrm{Tr}[\Pi\rho]$ is the fraction of shots that pass.
- **Refs.** [arXiv:1807.10050](https://arxiv.org/abs/1807.10050), [arXiv:1807.02467](https://arxiv.org/abs/1807.02467).

**D25. Symmetry expansion**
- **What it is.** A weighted combination of symmetry operators that tunes the trade-off between bias and variance.
- **Evidence.** 6–9× lower bias than plain verification.
- **Refs.** [arXiv:2101.03151](https://arxiv.org/abs/2101.03151).

**D26. Echo verification, verified phase estimation, dual-state purification**
- **What it is.** Single-copy methods that use an echo of the circuit to reject or reweight errors.
- **Cost.** About $\mathrm{Tr}[\rho^2]^{-1}$, where $\mathrm{Tr}[\rho^2]$ is the purity of the noisy state.
- **Refs.** [arXiv:2010.02538](https://arxiv.org/abs/2010.02538), [arXiv:2105.01239](https://arxiv.org/abs/2105.01239).

**D27. Virtual distillation / exponential error suppression (VD / ESD)**
- **What it is.** Prepare $M$ copies of the state and estimate $\mathrm{Tr}[\rho^MO]/\mathrm{Tr}[\rho^M]$.
- **Cost.** For 2 copies, $\mathrm{Tr}[\rho^2]^{-2}\lesssim f^{-4}$, plus twice the qubits.
- **Verdict.** Poor at $f<0.1$.
- **Refs.** [arXiv:2011.07064](https://arxiv.org/abs/2011.07064), [arXiv:2011.05942](https://arxiv.org/abs/2011.05942).

**D28. Quantum subspace expansion (QSE) and generalized QSE**
- **What it is.** Measure $H$ and the overlap matrix in a basis expanded by Pauli operators or by powers of $\rho$, then solve the small generalized eigenproblem classically.
- **Caution.** At low $f$ this needs a regularization threshold.
- **Refs.** [arXiv:1603.05681](https://arxiv.org/abs/1603.05681), [arXiv:2107.02611](https://arxiv.org/abs/2107.02611), [arXiv:2403.08868](https://arxiv.org/abs/2403.08868), [arXiv:2406.11533](https://arxiv.org/abs/2406.11533).

**D29. RDM purification and N-representability (chemistry)**
- **What it is.** Project the measured 1- or 2-particle reduced density matrix (RDM) onto matrices that a real $N$-particle state could produce. These are the N-representability constraints.
  - **McWeeny purification** makes the 1-RDM satisfy $\gamma^2=\gamma$, where $\gamma$ here denotes the 1-RDM. This idempotency holds exactly for a single Slater determinant.
- **Refs.** [arXiv:1801.03524](https://arxiv.org/abs/1801.03524), [arXiv:2004.04174](https://arxiv.org/abs/2004.04174), [arXiv:2304.13401](https://arxiv.org/abs/2304.13401), [arXiv:2511.10789](https://arxiv.org/abs/2511.10789), [arXiv:2511.09717](https://arxiv.org/abs/2511.09717).
- **Caution.** At $f\ll1$ the projection may simply pull the answer onto the classical prior.

**D30. Robust / fermionic / symmetry-aware classical shadows**
- **What it is.** Classical shadows estimate many observables at once from randomized measurements. "Robust" versions calibrate the measurement noise out; symmetry-aware versions use the Hamiltonian's symmetries.
- **Cost.** Variance about $f^{-2}$.
- **Refs.** [arXiv:2011.09636](https://arxiv.org/abs/2011.09636), [arXiv:2010.16094](https://arxiv.org/abs/2010.16094), [arXiv:2310.03071](https://arxiv.org/abs/2310.03071), [arXiv:2305.04956](https://arxiv.org/abs/2305.04956), [arXiv:2402.17911](https://arxiv.org/abs/2402.17911), [arXiv:2207.13723](https://arxiv.org/abs/2207.13723) *(unverified)*.

**D31. Reference-state and multireference error mitigation (REM / MREM)**
- **What it is.** Subtract the error measured on a classically solvable reference state, such as Hartree–Fock (the mean-field state), run through the same circuit.
- **Caution.** Fragile at $f<0.1$, because the correction becomes a difference of two tiny signals *(my estimate)*.
- **Refs.** [arXiv:2203.14756](https://arxiv.org/abs/2203.14756), [arXiv:2505.08291](https://arxiv.org/abs/2505.08291).

**D32. Bayesian inference of error rates**
- **What it is.** Infer the gate and readout error rates by Bayesian methods, with uncertainty quantification, and mitigate with them.
- **Refs.** [arXiv:2010.09188](https://arxiv.org/abs/2010.09188), [arXiv:2307.05302](https://arxiv.org/abs/2307.05302).

---

## E. Eigenvalue algorithms that tolerate noise

These target energies directly and either cancel the damping factor or are insensitive to it.

**E1. Quantum computed moments (QCM) with a Lanczos cumulant correction**
- **What it is.** Measure $\langle H^k\rangle$ for $k=1,\dots,4$ and combine them into cumulants (the connected parts of the moments). A closed-form Lanczos expansion then gives a corrected ground-state energy. Incoherent noise largely cancels in the cumulant ratios.
- **Low-$f$ evidence.** 20 qubits with about 500 CNOTs, where VQE (the variational quantum eigensolver) "completely fails".
- **Refs.** [arXiv:2009.13140](https://arxiv.org/abs/2009.13140), [arXiv:2211.08780](https://arxiv.org/abs/2211.08780), [arXiv:2312.06975](https://arxiv.org/abs/2312.06975), [arXiv:2509.10758](https://arxiv.org/abs/2509.10758).

**E2. Connected-moments expansions**
- **Refs.** [arXiv:2009.05709](https://arxiv.org/abs/2009.05709), [arXiv:2103.09124](https://arxiv.org/abs/2103.09124), [arXiv:2008.10914](https://arxiv.org/abs/2008.10914).

**E3. Fourier moments with echo verification and noise renormalization**
- **What it is.** Measure $\langle e^{-iHt}\rangle$ and divide out a decay factor measured separately.
- **Evidence.** About 100× noise reduction (5 qubits, 266 CNOTs; nuclear physics).
- **Refs.** [arXiv:2401.13048](https://arxiv.org/abs/2401.13048).

**E4. Krylov subspace diagonalization with thresholding and regularization**
- **What it is.** Discard eigenvalues of the overlap matrix $\mathbf S$ below a threshold. Here $\mathbf S_{kl}=\langle\psi_k|\psi_l\rangle$ is the matrix of overlaps between the Krylov states $|\psi_k\rangle$. This keeps the lowest eigenvalue stable when the noise is large.
- **Refs.**
  - Theory: [arXiv:2110.07492](https://arxiv.org/abs/2110.07492), [arXiv:2208.00567](https://arxiv.org/abs/2208.00567), [arXiv:2401.01246](https://arxiv.org/abs/2401.01246) (error analysis), [arXiv:2307.16279](https://arxiv.org/abs/2307.16279) (shot noise).
  - Hardware: KQD (Krylov quantum diagonalization) on 56 qubits, [arXiv:2407.14431](https://arxiv.org/abs/2407.14431).
  - VQPE (variational quantum phase estimation), [arXiv:2103.08563](https://arxiv.org/abs/2103.08563).
  - A variant that avoids the Hadamard test, [arXiv:2109.06868](https://arxiv.org/abs/2109.06868) *(authors unverified)*.

**E5. Observable dynamic mode decomposition (ODMD)**
- **What it is.** Fit time-series measurements with dynamic mode decomposition to extract eigenenergies.
- **Evidence.** Proven to converge under large perturbative noise.
- **Refs.** [arXiv:2306.01858](https://arxiv.org/abs/2306.01858).

**E6. Early-fault-tolerant phase estimation: Lin–Tong CDF method, QCELS, multi-modal QCELS (MM-QCELS)**
- **What it is.** Short circuits with one ancilla qubit. Classical signal processing then fits the phases.
  - CDF method: fits the cumulative distribution function of the energy spectrum.
  - QCELS: quantum complex exponential least squares.
  - MM-QCELS: the multi-eigenvalue version of QCELS.
- **Cost.** About $1/(\eta^2\epsilon_E)$, where $\eta$ is the overlap of the starting state with the ground state and $\epsilon_E$ is the target energy precision. Noise effectively replaces $\eta$ by $F\eta$, so the cost rises by about $F^{-2}$ *(my estimate)*.
- **Refs.** [arXiv:2102.11340](https://arxiv.org/abs/2102.11340), [arXiv:2211.11973](https://arxiv.org/abs/2211.11973), [arXiv:2303.05714](https://arxiv.org/abs/2303.05714), [arXiv:2209.06811](https://arxiv.org/abs/2209.06811), [arXiv:2302.02454](https://arxiv.org/abs/2302.02454).

**E7. Ground-state energy estimation robust to depolarizing noise**
- **What it is.** The depolarizing factor is built directly into the fit model. The bias is exponentially small in circuit depth at fixed $f$.
- **Refs.** [arXiv:2307.11257](https://arxiv.org/abs/2307.11257), [arXiv:2410.05369](https://arxiv.org/abs/2410.05369), [arXiv:2603.21873](https://arxiv.org/abs/2603.21873).

**E8. Statistical phase estimation**
- **What it is.** Global depolarizing noise shrinks the signal but does not move the eigenvalue.
- **Evidence.** Reached chemical precision on Rigetti hardware, beating the authors' own noise expectations by 1–2 orders of magnitude.
- **Refs.** [arXiv:2304.05126](https://arxiv.org/abs/2304.05126).

**E9. Bayesian QPE with error detection**
- **What it is.** Bayesian quantum phase estimation (QPE) run inside the Iceberg code (entry B13).
- **Evidence.** 920 two-qubit gates on Quantinuum; H₂ energy within $6\times10^{-3}$ Ha.
- **Refs.** [arXiv:2306.16608](https://arxiv.org/abs/2306.16608).

**E10. Robust amplitude estimation**
- **What it is.** Deliberately deeper, noisier circuits, analysed with a likelihood model that includes exponential decay.
- **Refs.** [arXiv:2110.10664](https://arxiv.org/abs/2110.10664).

---
## F. Techniques from lattice gauge theory (LGT) and nuclear/particle physics

**F1. Energy-penalty and linear gauge protection**
- **What it is.** Add a protection term to the Hamiltonian:
  $$H\to H+V\sum_j c_jG_j,$$
  where:
  - $V$ is the protection strength;
  - $G_j$ is the Gauss-law operator at site $j$;
  - $c_j$ are fixed coefficients, chosen so that gauge-violating processes become energetically forbidden (off-resonant).
- **Effect.** Violations stay at about $\lambda_{\rm gb}/V$, where $\lambda_{\rm gb}$ is the strength of the gauge-breaking error terms. For Abelian groups this costs only single-qubit rotations per step. It does not raise $f$, but it raises the Gauss-law yield.
- **Refs.** [arXiv:2001.00024](https://arxiv.org/abs/2001.00024), [arXiv:2007.00668](https://arxiv.org/abs/2007.00668), [arXiv:2204.13709](https://arxiv.org/abs/2204.13709), [arXiv:2203.01338](https://arxiv.org/abs/2203.01338), [arXiv:2203.08905](https://arxiv.org/abs/2203.08905).

**F2. Protection for non-Abelian groups (SU(2), SU(3))**
- **The problem.** The non-Abelian Gauss-law generators do not commute with each other, so simple penalties fail.
- **Workarounds.**
  - Protect Abelian symmetries in the loop–string–hadron (LSH) formulation, which rewrites SU(2) LGT in gauge-invariant variables.
  - Use local "pseudogenerators" instead.
- **Status.** Numerical studies only.
- **Refs.** [arXiv:2206.07444](https://arxiv.org/abs/2206.07444), [arXiv:2404.12158](https://arxiv.org/abs/2404.12158).

**F3. Dynamical decoupling with gauge transformations; random gauge transformations against "gauge drift"**
- **What it is.**
  - Apply gauge transformations as fast decoupling pulses, which averages out gauge-violating terms (non-Abelian invariance from DD).
  - Or insert pseudorandom gauge transformations between steps. Coherent violations then grow like $\sqrt{N_{\rm steps}}$ instead of like $N_{\rm steps}$, where $N_{\rm steps}$ is the number of Trotter steps.
- **Refs.** [arXiv:2012.08620](https://arxiv.org/abs/2012.08620), [arXiv:2005.12688](https://arxiv.org/abs/2005.12688), [arXiv:2409.04395](https://arxiv.org/abs/2409.04395).

**F4. Gauss-law oracles, dynamical post-selection (DPS) and post-processed symmetry verification (PSV)**
- **What it is.** Check the Gauss law with ancilla qubits or from the final measurements.
  - **DPS:** mid-circuit checks.
  - **PSV:** correlate observables with gauge transformations afterwards, with no extra circuit.
- **Cost.** About $1/f_{\rm keep}$.
- **Refs.** [arXiv:1812.01617](https://arxiv.org/abs/1812.01617), [arXiv:2412.07844](https://arxiv.org/abs/2412.07844) (non-Abelian, D₃ group), [arXiv:1803.03326](https://arxiv.org/abs/1803.03326).

**F5. Sparse error detection for LGT**
- **What it is.** Iceberg and hypercube codes plus Gauss-law sector post-selection, applied to the Schwinger model.
- **Evidence.** About 55% less systematic error.
- **Refs.** [arXiv:2608.02944](https://arxiv.org/abs/2608.02944).

**F6. Gauge redundancy used as an error-correcting code**
- **What it is.** The Gauss law is itself a set of parity checks (stabilizers), so it can detect and correct errors.
  - **For SU(2) at $j_{\max}=1/2$** ($j_{\max}$ is the largest electric-flux spin kept on a link — your truncation): codes that correct single-qubit errors ([arXiv:2511.13721](https://arxiv.org/abs/2511.13721)).
  - **Approximate correction:** a mid-circuit vertex syndrome followed by "gauge cooling" recovery ([arXiv:2603.26819](https://arxiv.org/abs/2603.26819)).
- **Other refs.** [arXiv:2112.05186](https://arxiv.org/abs/2112.05186), [arXiv:2402.16780](https://arxiv.org/abs/2402.16780) (error thresholds), [arXiv:2604.06087](https://arxiv.org/abs/2604.06087), [arXiv:2608.00165](https://arxiv.org/abs/2608.00165).

**F7. Measurement-based time evolution with free "one-form-symmetry" syndromes**
- **What it is.** The circuit runs on a recycled cluster state (a highly entangled resource state used for measurement-based computation) on Quantinuum H2. The measurement record gives error syndromes at no extra cost, and these are used for post-selection.
- **Refs.** [arXiv:2608.04290](https://arxiv.org/abs/2608.04290).

**F8. Detected errors turned into intended resets (no post-selection)**
- **What it is.** For dissipative (open-system) simulations only: a detected error is turned into a reset that the simulated dynamics already includes, so no shot is discarded.
- **Refs.** [arXiv:2509.25326](https://arxiv.org/abs/2509.25326).

**F9. Floquet-engineered "hierarchical emergent symmetries"**
- **What it is.** Periodic driving creates approximate selection rules that slow the spread of gauge defects.
- **Status.** Numerical only.
- **Refs.** [arXiv:2604.11085](https://arxiv.org/abs/2604.11085).

**F10. Full mitigation stacks used in record LGT runs**
These are worth copying, because they all work at $f\ll0.1$.

| Run | Hardware and size | Mitigation stack | Ref |
|---|---|---|---|
| SU(2) adjoint string breaking | 156 qubits, 7,634 CZ gates | DD + twirling + TREX + ODR + ZNE + reflection averaging + ancilla post-selection; matches tensor networks | [arXiv:2608.28752](https://arxiv.org/abs/2608.28752) |
| Gauge induction | 101 qubits | Gauss-law post-selection tolerating 2 violated sites (yield fell below 1% and results were still usable) + 500 twirls + XpXm DD + best of 10 layouts | [arXiv:2608.02756](https://arxiv.org/abs/2608.02756) |
| (2+1)D $\mathbb Z_2$ strings | Google, 45 qubits | Ancilla post-selection + echo DD + randomized compiling + readout correction + global rescaling | [arXiv:2409.17142](https://arxiv.org/abs/2409.17142) |
| (2+1)D $\mathbb Z_2$-Higgs strings | IBM, up to 144 qubits | Gauge dynamical decoupling + Gauss-sector correction + calibrated ODR + DMRG check | [arXiv:2507.08088](https://arxiv.org/abs/2507.08088) |
| SU(2) string breaking | 104 qubits | Mitigation details not confirmed | [arXiv:2411.05915](https://arxiv.org/abs/2411.05915) |
| SU(3) lattice Yang–Mills at large N | ibm_torino | — | [arXiv:2402.10265](https://arxiv.org/abs/2402.10265) |
| SU(2) hadrons with VQE | — | — | [arXiv:2102.08920](https://arxiv.org/abs/2102.08920) |

---

## G. Hybrid schemes in which noise enters only a "guide"

In each of these, the quantum device supplies a guide, a prior or a starting point. An exact classical method does the rest, so noise degrades efficiency rather than correctness.

**G1. QC-AFQMC**
- **What it is.** The device provides trial-state overlaps through classical shadows. AFQMC (auxiliary-field quantum Monte Carlo, a classical stochastic method) uses them as a guide. Noise only affects that guide.
- **Evidence.** IonQ, 24 qubits.
- **Refs.** [arXiv:2106.16235](https://arxiv.org/abs/2106.16235), [arXiv:2506.22408](https://arxiv.org/abs/2506.22408), [arXiv:2502.20066](https://arxiv.org/abs/2502.20066).

**G2. Embedding (DMET, DMFT)**
- **What it is.** Only a small fragment or impurity is solved on the device, so $N_{2q}$ stays small and $f$ stays high.
  - DMET: density-matrix embedding theory.
  - DMFT: dynamical mean-field theory.
- **Refs.** [arXiv:2102.07045](https://arxiv.org/abs/2102.07045), [arXiv:1910.04735](https://arxiv.org/abs/1910.04735).

**G3. Orbital-optimized post-processing**
- **What it is.** Orbital rotations are optimized classically from the measured RDMs (reduced density matrices).
- **Refs.** [arXiv:2212.02482](https://arxiv.org/abs/2212.02482).

**G4. Quantum-enhanced greedy solver; warm-start QAOA**
- **What it is.** The method provably falls back to the classical greedy algorithm (or to the classical starting point) as $f\to0$.
- **Refs.** [arXiv:2303.05509](https://arxiv.org/abs/2303.05509), [arXiv:2009.10095](https://arxiv.org/abs/2009.10095).

**G5. Quantum generative priors for drug discovery and biology**
- **What it is.** A QCBM (quantum-circuit Born machine, a circuit used as a probability model) acts as a prior. Classical filters and wet-lab tests decide what is kept.
- **Evidence.**
  - KRAS inhibitors: [arXiv:2402.08210](https://arxiv.org/abs/2402.08210).
  - mRNA secondary structure with CVaR on 10–80 IBM qubits: [arXiv:2405.20328](https://arxiv.org/abs/2405.20328), [arXiv:2505.05782](https://arxiv.org/abs/2505.05782).

**G6. Noise used as a feature, not something to remove**
- **Examples.**
  - Quantum reservoir learning, 108 neutral atoms ([arXiv:2407.02553](https://arxiv.org/abs/2407.02553)).
  - HSBC/IBM bond-trading features ([arXiv:2509.17715](https://arxiv.org/abs/2509.17715)).
- **Caution.** Not an estimation method. It is listed only for completeness.

---

## H. Statistics for very noisy data

**H1. Median-of-means**
- **What it is.** Split the shots into batches, average each batch, and take the median of the batch averages. This is robust to outlier batches.
- **Refs.** [arXiv:2002.08953](https://arxiv.org/abs/2002.08953).

**H2. Bootstrap / jackknife error bars**
- **What it is.** Resampling methods for error bars, needed for every ratio estimator (ODR, echo normalization) and every fit (ZNE, CDR).
- **Refs.** Standard textbook methods.

**H3. Maximum-likelihood projection onto physical states or distributions**
- **What it is.** Replace a noisy estimate by the closest physically allowed one.
- **Refs.** [arXiv:1106.5458](https://arxiv.org/abs/1106.5458).

**H4. Iterative Bayesian unfolding** — see C16.

**H5. Good–Turing missing mass** — see C20.

**H6. Optimal shot allocation**
- **What it is.** Allocate shots to Hamiltonian term $i$ in proportion to $|c_i|\sigma_i$, where:
  - $c_i$ is the term's coefficient;
  - $\sigma_i$ is its standard deviation.
- **Refs.** [arXiv:2004.06252](https://arxiv.org/abs/2004.06252), [arXiv:1910.01155](https://arxiv.org/abs/1910.01155).

**H7. Heavy-output hypothesis test**
- **What it is.** Check whether the samples land on outputs of above-median ideal probability more often than chance. This tests whether any signal survives at all.
- **Refs.** [arXiv:1612.05903](https://arxiv.org/abs/1612.05903).

---

## I. The theoretical limits (what no technique can beat)

**I1. Exponential cost for any mitigation in a broad class (Takagi, Endo, Minagawa, Gu)**
- **Statement.** Shot cost grows exponentially in depth for local depolarizing noise. PEC is optimal for local dephasing noise.
- **Refs.** [arXiv:2109.04457](https://arxiv.org/abs/2109.04457).

**I2. Universal lower bound on shots (Takagi, Tajima, Gu)**
- **Statement.** The number of shots satisfies
  $$N_{\rm shots}\gtrsim (1-\gamma_{\rm L})^{-2L},$$
  where:
  - $\gamma_{\rm L}$ is the noise strength per layer;
  - $L$ is the number of layers.

  This is roughly $f^{-2}$ per qubit wire.
- **Refs.** [arXiv:2208.09178](https://arxiv.org/abs/2208.09178).

**I3. Quantum estimation theory bound (Tsubouchi, Sagawa, Yoshioka)**
- **Statement.** Unbiased mitigation costs exponentially in depth. For global depolarizing noise the bound is reached by simple rescaling, with cost about $F^{-2}$.
- **Refs.** [arXiv:2208.09385](https://arxiv.org/abs/2208.09385).

**I4. Exponentially tighter bounds (Quek et al.)**
- **Statement.** In the worst case, $f^{-\Omega(1)}$ samples are needed. ($\Omega(1)$ means "some positive constant power".)
- **Refs.** [arXiv:2210.11505](https://arxiv.org/abs/2210.11505).

**I5. Mitigation thresholds with imperfect noise models**
- **Statement.** In 1D, methods that invert the noise fail at constant time. In 2D and higher there is a threshold on how accurately the noise must be characterized.
- **Refs.** [arXiv:2302.04278](https://arxiv.org/abs/2302.04278).

**I6. Perspectives**
- **Review.** Cai et al., [arXiv:2210.00921](https://arxiv.org/abs/2210.00921). Post-selection costs $e^{\lambda}$; PEC costs $e^{4\lambda}$.
- **"Myths around quantum computation before full fault tolerance".** Explains the lightcone and local-observable loopholes. Refs: [arXiv:2501.05694](https://arxiv.org/abs/2501.05694).

**Bottom line.** If you want an *unbiased* number, you pay at least about $f^{-1}$ to $f^{-2}$, and $f^{-4}$ for PEC. You escape this only by raising $f$ (Section B) or by using quantities whose correctness does not depend on $f$:

- the variational energy and its certified intervals (C19);
- CVaR bounds (C17);
- Metropolis-corrected sampling (C18);
- hand-off to an exact classical method (Sections C-iv and G).

---

## J. What this means for SU2QC SKQD at $f<0.1$ (a recommended stack)

This is my synthesis, ordered by cost-effectiveness. Every step is an existing technique listed above.

1. **Measure $f$ first.**
   - Use layer fidelity (A1) on the chosen qubit chain, and the Gauss-law yield (A5): $f\approx(Y-0.0015)/0.82$, where $Y$ is the accepted-shot yield.
2. **Raise $f$ before mitigating anything.**
   - Coarse single-step circuits (B5).
   - Fractional $R_{ZZ}$ gates (B3); halving $N_{2q}$ gives $f\to\sqrt f$.
   - Best-of-N layout (B4).
   - DD (B1).
   - If you go through Azure to trapped ions: an Iceberg code plus leakage detection (B13, B14).
   - Choose either fractional gates or built-in twirling per circuit; IBM's runtime does not combine them.
3. **Sample generation.**
   - Multi-reference starting states (C7). In your manual's emulator at $f=0.10$ this already gave recall 0.97 and a Ritz error of $2.9\times10^{-3}$ with $5\times10^4$ total shots.
   - Shots set by $S\ge 7.7/(fp)$. For $f=0.1$ and $p=10^{-3}$ that is $S\approx7.7\times10^4$ per circuit.
4. **Decode, then recover rather than only reject.**
   - Gauss-law post-selection (C2, F4).
   - Plus S-CORE-style or code-space-style repair of near-miss shots (C3, C4). Your decoder plays the role of the dual-rail check.
   - Recovery can raise the usable fraction. If shots with at most $k^*$ errors can be repaired, the usable fraction becomes *(my estimate, Poisson model)*
     $$f_{\rm eff}\approx\sum_{k\le k^*}\frac{e^{-\lambda}\lambda^k}{k!}.$$
     Here $k$ is the number of errors in a shot and $k^*$ the most that can be repaired. For $\lambda=3$ (so $f=0.050$): $f_{\rm eff}\approx0.050\times(1+3)=0.20$ for $k^*=1$, and $0.050\times(1+3+4.5)=0.42$ for $k^*=2$. This is optimistic, because one gate error in a time-evolution circuit can flip several bits.
5. **Extend classically.**
   - PT2 / selected-CI growth of $B$ (C15) and the ML proposer (C12), as in your manual's protocol table.
6. **Certify.**
   - Variational bound + Weinstein / Kato–Temple intervals (C19).
   - Good–Turing missing mass (C20) as a support-completeness monitor.
   - **Always** the random-configuration baseline at equal $|B|$ (C22).
7. **Any directly measured observable** (e.g. electric energy, string tension proxy).
   - Twirling + TREX + ODR or self-mitigation (D12, D13). Self-mitigation was demonstrated for SU(2).
   - Then GUESS with Gauss-law decay (D16) or PEA (D2) if more accuracy is needed.

---

## K. Code: small helpers (tested in the sandbox with NumPy/SciPy)

The pure-NumPy helpers below were run on toy data, and their outputs are shown after the code. The Qiskit block at the end was **not** run, because it needs an IBM account.

```python
import itertools, numpy as np
from scipy.stats import poisson

def clean_fraction(eps, n2q):                    # f = (1-eps)^N2q
    return (1.0 - eps) ** n2q

def f_from_yield(Y, readout_keep=0.82, garbage_pass=0.0015):   # invert Y ≈ 0.82 f + 0.0015
    return max(Y - garbage_pass, 0.0) / readout_keep

def shots_needed(f, p, hits=3, conf=0.95, readout_keep=0.82):  # manual eq. (5)
    mu = 0.0
    while poisson.sf(hits - 1, mu) < conf:       # P(N >= hits) for Poisson mean mu
        mu += 0.01
    return int(np.ceil(mu / (readout_keep * f * p)))

def recover(bits, is_valid, occ, max_flips=2, rng=None):
    """S-CORE-style repair: among flip sets of size 1..max_flips that make the string
    valid, pick one with weight prod |bit - occ| (occ = occupations from current Ritz vector)."""
    rng = rng or np.random.default_rng()
    w = np.abs(np.asarray(bits) - occ) + 1e-9
    for k in range(1, max_flips + 1):
        cands, wts = [], []
        for idx in itertools.combinations(range(len(bits)), k):
            b = list(bits)
            for i in idx: b[i] ^= 1
            if is_valid(b): cands.append(tuple(b)); wts.append(np.prod(w[list(idx)]))
        if cands:
            return cands[rng.choice(len(cands), p=np.array(wts) / sum(wts))]
    return None                                   # not repairable -> discard

def odr_rescale(phys_meas, mit_meas, mit_pred):   # divide out (1-eta_O)
    return phys_meas * mit_pred / mit_meas

def cvar_bounds(values, alpha):                   # alpha <= f  (arXiv:2312.00733)
    v = np.sort(np.asarray(values)); k = max(1, int(alpha * len(v)))
    return v[:k].mean(), v[-k:].mean()

def good_turing_missing(counts):                  # N1 / S
    c = np.asarray(list(counts.values())); return np.sum(c == 1) / np.sum(c)

def kato_temple_interval(E_R, r_H, alpha_gap):    # gap-assumed [E_R - r^2/(alpha-E_R), E_R]
    return E_R - r_H**2 / (alpha_gap - E_R), E_R
```

Output of the test run:

```
f(eps=3e-3, N=1000) = 0.050
f from yield 0.05: 0.0591
shots for f=0.1, p=1e-3: 76830              # matches 7.7/(f p) = 77,000
recover (1,0,0,0): (1, 1, 0, 0)             # toy pair-parity "Gauss law", occ=(.9,.9,.1,.1)
ODR: 0.24                                    # 0.012 * 0.80 / 0.04
Good-Turing missing mass: 0.2               # 2 singletons / 10 shots
Kato-Temple (2x3 B=0, illustrative alpha): (-5.6219, -5.5929)   # reproduces manual's [-5.622, -5.593]
```

How the numbers in the test run were obtained:

- **Shots.** The loop finds the smallest Poisson mean $\mu$ with $P(N\ge3)\ge0.95$; it gives $\mu\approx6.30$. Then $S=6.30/(0.82\times0.1\times10^{-3})\approx76{,}830$.
- **Kato–Temple.** It uses the manual's $E_R=-5.5929$ and $r_H=0.281$ with an illustrative $\alpha_{\rm gap}=-2.87$. Then $r_H^2/(\alpha_{\rm gap}-E_R)=0.0790/2.7229=0.0290$, so the lower end is $-5.5929-0.0290=-5.6219$.

**Qiskit runtime options for steps 1–2 of Section J** (not run; option names are those of qiskit-ibm-runtime 0.3x, so check them against your installed version):

```python
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
svc = QiskitRuntimeService()
be  = svc.least_busy(operational=True, simulator=False)
# Route A: CZ circuits + dynamical decoupling + Pauli twirling
s = Sampler(mode=be)
s.options.dynamical_decoupling.enable = True
s.options.dynamical_decoupling.sequence_type = "XpXm"
s.options.twirling.enable_gates = True
s.options.twirling.num_randomizations = 64
# Route B: native fractional RZZ (fewer 2q gates; built-in twirling not allowed)
be_frac = svc.backend(be.name, use_fractional_gates=True)
# ... transpile, run, then: Y = accepted/total ; f = f_from_yield(Y) ; recover() near-misses
```

---

## L. Notes on sources and confidence

- **How references were checked.** Each arXiv ID was checked on its arxiv.org abstract page, or through a search result that showed the ID and title together.
  - Marked *(unverified)*: [arXiv:2207.13723](https://arxiv.org/abs/2207.13723) (fetched only via search), and the authors of [arXiv:2109.06868](https://arxiv.org/abs/2109.06868).
  - [arXiv:1705.02329](https://arxiv.org/abs/1705.02329) (flag qubits) and [arXiv:1904.10910](https://arxiv.org/abs/1904.10910) (particle-number-preserving circuits) were cited from memory, so they are not used above.
- **Very recent papers.** Many 2026 papers (IDs starting 26xx) are past my training data. Their claims come from the fetched abstracts or HTML pages only.
- **IBM utility experiment** (PEA, D2): it has no arXiv version (*Nature* 618, 500, 2023).
- **Fractional gates** (B3): the only source is IBM's documentation.
- **Back-of-envelope global $f$ values** (e.g. $e^{-29}$, $e^{-30}$): my estimates from the papers' gate counts and typical error rates of $(2$–$10)\times10^{-3}$. The papers do not state them.
- **My own derivations, not taken from papers:**
  - the $f$-scalings of ZNE, CDR and ODR;
  - the $f_{\rm eff}$ recovery formula;
  - the Good–Turing suggestion.
- **Unresolved.** Sources disagree on two figures: the SqDRIFT qubit count (48 vs 72/100) and whether the [4Fe-4S] "10,570 gates" counts only two-qubit gates.
- **Not found in the literature:**
  - diffusion-model or normalizing-flow recovery for SQD;
  - a dedicated majority-vote or importance-reweighting paper for SQD;
  - **any SQD/SKQD study of SU(2) lattice gauge theory with dynamical quarks.**

  The last of these appears to be an open niche, which is good news for this project.
