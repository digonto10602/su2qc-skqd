# 006 — Full-circuit verification by certified pruned simulation (change of method for A2; the bar is unchanged)

- Date: 2026-10-21.  Author: genie-opus.  Amends `notes/001-phase2-plan.md` §2.2 item 2 / A2 (method only).

**What happened.**  On the compressed circuits the package's exact sparse simulator (`skqd.sparse_sim`, every nonzero
amplitude kept) became slow: one class-B circuit (`B1_ref230_k1`) reached a support of 4 184 564 strings and took
33.4 s, and a class-A circuit grew to $2^{16}$ strings within 2 000 gates and did not finish in 10 minutes.  The cause
is round-off: frames and basis changes that cancel exactly in exact arithmetic leave residues of order $10^{-17}$ on
non-codeword strings; later multiplexors act arbitrarily on those don't-care strings and scatter them.  The residues
carry no weight (the measured leakage onto non-codeword strings is $\le1.6\times10^{-30}$) but every one costs memory.

**The method now used** (`src/c2x4/evaluate.verify_circuit_pruned`, option `--prune-tau` of `scripts/eval_family.py`):
after every 32 gates, amplitudes with $|a|<\tau=10^{-15}$ are removed and the removed $\ell_2$ norm is added up as
$B_{\rm prune}$.  With $v$ the computed state and $u$ the exact output of the same gate list,
$\lVert v-u\rVert_2\le B_{\rm prune}$ (Lean `Compress2x4.telescoping_bound_mirror`: every gate step is unitary, pruning
is the only non-unitary step).  Hence the **certified** quantities

$$\max_s|u_se^{-i\varphi}-t_s|\le\max_s|v_se^{-i\varphi}-t_s|+B_{\rm prune},\qquad
\text{leak}(u)\le\bigl(\sqrt{\text{leak}(v)}+B_{\rm prune}\bigr)^2,$$

and a circuit passes only if the certified deviation is $<10^{-10}$ and the certified leakage $<10^{-9}$ — the package bar,
now with a rigorous allowance for everything not simulated.  On `B1_ref230_k1` (class B) the exact and the pruned runs
give $2.33\times10^{-14}$ and $2.36\times10^{-14}$; the certified value is $3.48\times10^{-14}$ (0.10 s instead of 33.4 s).
The exact unpruned runs that finished are kept as cross-checks (`data/eval_it5_input_all75_part0.log`).

**Why this is not a weaker bar.**  The package bar is a measured maximum amplitude deviation; here the measured value
plus a proved upper bound on what pruning can have changed is below the same number.  $\tau$ is fixed before the runs and
the bound is reported per circuit.
