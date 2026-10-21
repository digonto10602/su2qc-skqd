# 004 — The approximate class: what is dropped, the tolerance, and why it is enough for SKQD

- Date: 2026-10-21.  Author: genie-opus.  Plan in force: `notes/003` (this note adds the approximate class the
  owner asked for in `notes/002`, answer O2).  Written BEFORE any approximate circuit was built.

## 1. What the approximate class drops

The exact input-specific class synthesises term $\gamma$ exactly on every block of its local generator that the
circuit can reach structurally from the reference (`src/c2x4/reach.py`).  The approximate class additionally
treats as don't-care the blocks that the exact trajectory reaches only with a tiny amplitude: for circuit
$(r,k)$ and term $\gamma$ let $\varphi_\gamma$ be the exact state before term $\gamma$ (computed in complex128 with
`krylov.apply_groups` on the 37 165-dimensional dressed basis), and $\Pi_{D_\gamma}$ the projector onto the
dropped blocks.  The circuit is then exact on the kept blocks and arbitrary (but unitary) on the dropped ones.
Nothing else changes: same term order, same exact rotations on the kept blocks, no state loaded from the
classical result.

## 2. The error bound (proved in Lean)

With $U_\gamma$ the exact term, $V_\gamma$ the circuit's term, both unitary, and $V_\gamma=U_\gamma$ on the range
of $1-\Pi_{D_\gamma}$ (which both leave invariant):

$$\lVert\psi_{\rm approx}-\psi_{\rm exact}\rVert_2\;\le\;\sum_\gamma\lVert(V_\gamma-U_\gamma)\varphi_\gamma\rVert_2
\;\le\;\sum_\gamma 2\,\lVert\Pi_{D_\gamma}\varphi_\gamma\rVert_2 .$$

The first inequality is `Compress2x4.telescoping_bound` (L6, proved); the second is
`Compress2x4.dropped_part_bound` (L6c, proved 2026-10-21 in `lean/Compress2x4/Budget.lean`, before any approximate circuit was built).

## 3. The tolerance and its justification

SKQD uses the circuit only through the distribution of measured bit strings (the classical step then
diagonalises the exact $H$ on the sampled support).  For two normalised states the total-variation distance of
their computational-basis distributions obeys

$$\mathrm{TV}(|\psi|^2,|\phi|^2)=\tfrac12\sum_s\bigl||\psi_s|^2-|\phi_s|^2\bigr|\;\le\;\tfrac12\lVert\psi-\phi\rVert_2\,
\lVert\psi+\phi\rVert_2\;\le\;\min_\alpha\lVert\psi-e^{i\alpha}\phi\rVert_2$$

(Cauchy–Schwarz; global phase free; lemma L6b `Compress2x4.tv_le_norm_sub`, proved 2026-10-21 in `lean/Compress2x4/Budget.lean`).  By the coupling
inequality, $N$ independent shots of the two circuits can be coupled so that the two shot records differ with
probability at most $N\cdot\mathrm{TV}$.  The 2x4 plan of the package samples about $2\times10^{5}$ shots per sector
at its plan point and, on the GPU, "generously" more (prompts/36 R5, K6); I take $N_{\rm sector}\le10^{6}$ as the
design value.  I state the tolerance as

$$\varepsilon:=\min_\alpha\lVert\psi_{\rm approx}-e^{i\alpha}\psi_{\rm exact}\rVert_2\;\le\;10^{-8}\quad\text{per circuit,}$$

so that, summed over all circuits of a sector, the probability that the approximate family's sampled records
differ from the exact family's at all is at most $10^{6}\times10^{-8}=10^{-2}$.  Every downstream quantity of SKQD
(sampled support, recall, Ritz energy $E_R$ and therefore the comparison with $E_{\rm tol}$) is a function of the
records, so with probability $\ge0.99$ the approximate family gives bit-identical SKQD output to the exact one.
For scale: the package's $E_{\rm tol}$ at 2x3 is 0.0142 / 0.0110 (B = 0 / 1, `validation/CV_2x3_plan.json`); no
2x4 value exists yet, and none is needed for this argument, which is stronger (identical samples).

The tolerance is $10^2$ times looser than the exact bar in amplitude terms ($10^{-10}$ max amplitude), and it is
checked as a measured number, not only as the bound: every approximate circuit is run on the exact sparse
simulator and $\varepsilon$, $\max_s|\Delta\psi_s|$ and the leakage are reported.

## 4. Budget split used by the builder

$\varepsilon_{\rm budget}=10^{-8}$ split evenly over the 13 non-diagonal terms: drop blocks of term $\gamma$ in
increasing order of their weight while $2\lVert\Pi_{D_\gamma}\varphi_\gamma\rVert_2\le\varepsilon_{\rm budget}/13$.
The approximate circuits depend on $(r,k)$ (amplitudes depend on $\theta=k\,dt$), so the family has one circuit
per (reference, $k$), as the input-specific class already does per reference.

## 5. Addendum (2026-10-21, later the same day; the tolerance is unchanged)

The package's 2x4 plan was signed and merged while this study ran (`validation/CV_2x4_plan.json`, PASS):
`data.plan.final.shots_total` = 308 547 shots at the plan point and `gpu_shots_total` = 1 411 324 on the GPU,
both sectors together; `data.E_tol` = 0.014495 (B = 0) and 0.012534 (B = 1).  With
$\varepsilon\le10^{-8}$ per circuit the coupling bound for the whole GPU run is
$1\,411\,324\times10^{-8}\approx0.014$ (both sectors), i.e. the design value $N_{\rm sector}\le10^{6}$ of section 3
is met per sector to within the stated rounding.
