# Review 002 — cold read of `MANUAL_lgt_circuit_compression.md` (as an agent from another LGT project)

- **Date:** 2026-10-26
- **Git commit reviewed:** `ac886b2` (HEAD; the manual is unmodified at this commit)
- **Reviewer:** reviewer-opus (Opus 5.5)
- **Task in force:** coordinator's brief of 2026-10-26: cold-read the manual, run its quick start on the smallest case
  without changing any file, judge whether §4 is enough to transfer the method
- **Related:** `reviews/001-independent-verification.md` (review of the v1 families), `reports/003-full-compression-report.md`,
  `reports/004-c4-c3-second-round-and-2x3.md`, `noise/reports/003-noise-results.md`
- **Scratch work (not in the repository):** `/home/digimonk/.claude/jobs/9a585e99/tmp/manual_test/`
  (`t1_problem_structure.py`, `t2_loop_2x2.py`, `t3_aer_2x2.py`, `t4_2x3_terms.py`, their `*_out.json` and logs,
  and `lean/build.log`).  No repository file was edited.  The only writes inside the repository were gitignored
  `__pycache__` folders that Python creates on import.

## Verdict: **USABLE AFTER FIXES**

Inside this repository the manual works.  I followed it on 2x2 and built and verified complete class-A and class-B
families in 23 s, with no code changes.  Every code reference and every Lean lemma name it cites exists, and the
numbers I checked match their source files.

For a project on another theory it is not yet enough, for two reasons:
- It never writes down the model it compresses: the Hamiltonian, the truncation, or what each qubit of a vertex
  means.
- Section 4 gives research directions, not procedures, for U(1) beyond spin-1/2, for SU(2) at higher truncation, for
  SU(3) and for 2D lattices.

There is one blocking finding and thirteen important ones.

---

## 1. Ranked findings

### Blocking

**B1. The model being compressed is never stated (§1.1, §2.1, Glossary).**
A reader from another project cannot find out what the Hamiltonian is, or what the qubits encode.
- The manual never writes the Hamiltonian or the content of each term group.  In the code
  (`src/skqd/hamiltonian.py:72-76`), $H_{\rm diag}=m\,H_{\rm mass}+\tfrac{g^2}{2}H_E$ and
  $H_{\rm plaq,p}=-W_p/(2g^2)$, with $g^2=4.0$ fixed in `src/c2x4/problem.py:33`.
- It never states the truncation, $j_{\max}=\tfrac12$.  A reader can only infer it from the title of §4.2.
- It never gives the vertex register.  I measured it: 3 qubits at corner vertices and 4 at interior vertices
  (`CodewordEmbedding(Model(Lx)).codec.widths` = `[3,3,3,3]` at 2x2 and `[3,3,4,4,4,4,3,3]` at 2x4).
- It never says what the "vertex bit" is (an intertwiner label at 3-link vertices).  The same goes for $n_x$, $N$,
  the "third link", and what a "dark" intertwiner is physically.
- It never explains $B$ / `twoB` (baryon number, the sector label) or how references are chosen
  (`skqd.krylov.references`: Dirac sea, one-meson and diquark states).

Without these, the reader cannot map their own Hamiltonian onto `diag/hop/plaq`.  They also cannot predict whether
the corner and vertex factorisations should hold for them, and those factorisations are the core of the method.

*Fix:* add a one-page "§1.0 The model".  It should contain:
- the Kogut–Susskind Hamiltonian, with its signs and couplings;
- the truncation;
- the term-group contents;
- a table of the vertex encoding: qubit → meaning, for corner and interior vertices;
- the $\eta$ phases (consistent with CLAUDE.md rule 2: $\eta=i$ on x-links, $(-1)^{x_1+x_2}$ on y-links);
- the definition of the sectors and references.

Point to `src/skqd/su2.py`, `lattice.py`, `codec.py` and `hamiltonian.py` for the full detail.

### Important

**I1. The commands in §12.4 overwrite the evidence that §1.2 cites, and the disk cache can go stale silently.**
- Every script writes to fixed paths inside the study, with no `--out` option.  Examples:
  `loop_select.py:113` writes `data/archive_<label>.json` through `env.archive_path`, and
  `eval_family.py:131` writes `data/{sub}eval_*.json`.
- Re-running §12.4 "as run here" therefore overwrites `data/archive_it6*.json`, `data/eval_arch_it6_*.json`,
  `data/cert_it6_*.json` and `data/native_*_v2.json`.  These are the files behind the results table in §1.2.
- The cache `_cached` (`src/c2x4/family.py:37-50`) is keyed only by (proposal tag, reference, term, $\theta$), not by
  code version.  So does `Problem.cpath`.  A newcomer who edits a proposal will silently get the old circuits from
  `data/cache`.

*Fix:*
- Add a warning to §12.4.
- Add a "sandbox" recipe: set `c2x4.env.CACHE`, `c2x4.problem.CACHE` and `c2x4.family.CACHE`, and patch
  `c2x4.env.archive_path`, to point at a scratch directory (as in my `t2_loop_2x2.py`).  Or add `--out`/`--cache`
  options to the scripts.
- State in §8 that the cache must be cleared after any change to a proposal.

**I2. There is no smallest worked example (§11).**
- The quick start goes straight from "read the conventions" to porting eight modules.
- §12.4 lists only the full 2x4 production runs, which take 15–25 min each.
- My practical test (§2 below) shows that the complete 2x2 pipeline takes 23 s in-process: loop, both classes, all
  28 circuits per class, certified check.  It needs none of the three bookkeeping edits of §1.3.

*Fix:* add "§11.0 First 5 minutes": the 2x2 in-process recipe, with its expected output (counts, pass flags).

**I3. The commit hash in the header (line 9) is wrong.**
- Line 9 cites `bf55f30`.  That commit is on no branch (`git branch -a --contains bf55f30` is empty) and is not an
  ancestor of HEAD.
- It has the same message and date as `5984d69`, which is on master.  It is probably a pre-amend duplicate.

*Fix:* cite `5984d69` (results) and `ac886b2` (manual).

**I4. The path rule in lines 5–8 contradicts paths used throughout the manual.**
- Lines 5–8 say paths that start with `data/` are inside the study folder.
- But `data/quantinuum/...`, `data/quantinuum/devices_20261002.json` and `validation/*.json` (§1.2, §2.1, Glossary
  $f$) are at the repository root.  `2x4_compression_using_ai_v1/data/quantinuum` does not exist.

*Fix:* mark root paths explicitly, e.g. `<root>/data/quantinuum/...`.

**I5. `hop_vertex_factors` is presented as a test, but it does not test the factorisation (§3b item 3, §4.6 item 4).**
- `src/c2x4/hopframe.py:79-123` fits $\log|h|$ by least squares and raises only if the sign system is inconsistent.
- It never forms the product $\eta\,a_x\otimes b_y\otimes s_{\rm JW}$, never compares it with $h$, and never returns
  $s_{\rm JW}$.
- The "residual $\le2.7\times10^{-15}$" quoted in §3b is `magnitude_fit_residual` from
  `scripts/p2_1_structure.py:hop_fit`.  That is the residual of the log-magnitude fit, not a product residual.
- The claim "each vertex factor is an equal-step three-level chain (spin-1 raising operator)" has no field in
  `data/p2_1_structure.json`, although it is marked [num] with that file as its source.

*Fix:*
- Add a real product check, or say exactly what `hop_fit` checks.
- Give a computed source for the chain claim, or mark it [heur].

**I6. §3b item 1 (blocks bipartite with zero diagonal) cites the wrong script.**
- It points to `p2_1_structure.py`, which does not compute bipartiteness.
- In my `t1_problem_structure.py` I computed it with `scipy.sparse.csgraph.connected_components` and
  `skqd.circuits_ir._bipartition`.  At 2x2 every block of every term passed.

*Fix:* name the code that actually performs this test, or add it to the script.

**I7. The structure script is tied to 2x4 (§3b, §11 step 4).**
- `scripts/p2_1_structure.py:main` uses `get_problem()` (2x4 by default) and hard-codes `range(3)` plaquettes and
  references 102 / 345 / 230.
- It also writes `data/p2_1_structure.json` unconditionally.

*Fix:* add an `--lx` option and an output path, or say in §3b that the script must be adapted.

**I8. Several equations use symbols that are never defined.**
- §3b.2: $C$ in $h_P\vert_C$.
- §3b.3: $a_x$, $b_y$, $s_{\rm JW}$ (here $x$, $y$ are vertices, which clashes with x-link/y-link).
- §3b.4: $\theta_0$, $A$, $x_c$ (it is defined later, in §3c).
- §3c: which corner is "1".  The math writes $\prod_{c\neq1}$ while the pseudo-code writes `c != c00`.  Also
  $p_1$, $s_{p_1}$, $F(s)$, $\ell$.
- §3d: $a,b,c,\bar x$ in the CCZ identity ($c$ is also the corner index); $F_{\rm free}$ and $F_{\rm cost}$ (these
  clash with the angle table $F$); $u,w,b$.
- §3e: $M(x)$.
- §3f: $W$, $m$, $Z_S$, $Y_t$, ${\rm CX}_S$.
- §3g.5: $H_2$, $h_0$, $P(\theta)$.
- §5.2: $V_i$, $U_i$, $v_i$, $G$, $G'$, $\gamma_2$.
- The letter $B$ means four different things: baryon number, vertex $B$ (§3g.4), the rounding bound of Q1L, and the
  basis change $B$ (§3g.5, §3h).

*Fix:* add a symbol table, and rename the overloaded symbols.

**I9. Several terms used in the text are neither in the glossary nor defined at first use.**
- Package gate names: Q0P, Q1, Q2, Q5.
- Project labels: CF_traj, C1–C6, C3/C4/C5, "owner answer O5", "prompts/35b R1", "genie-opus".
- Physics: dressed basis, intertwiner, sector / $2B$.
- Noise quantities: $f_{\rm hit}$, $f_{\rm ideal}$, $r_{\rm nc}$, acceptance, TV.
- Gate and algorithm terms: PhasedX, Margolus, RC3X, Gray code, 2-opt.
- Devices: H1-1, Helios-1.

*Fix:* extend the glossary.  For project-internal labels (C*, O5, 35b), give one line each, or drop them.

**I10. Two different quantities are both called $f$ without saying so (§1.2 against §9).**
- §1.2 gives class B v2 $f=0.5293$, class A v2 $f=0.2512$, and frozen 2x4 $f=4.18\times10^{-29}$.
- §9 gives 0.401, 0.136, and $\le4.71\times10^{-41}$.
- The first set is the package's gate-only $f$.  The second is the noise report's full-model $f$ (its §3.3 defines
  $f$, $f_{\rm gate}$ and $f_{\rm pkg}$).

*Fix:* name them, e.g. $f_{\rm pkg}$ and $f_{\rm full}$, and define both.

**I11. Independent verification of the v2 and 2x3 families is narrower than §5.4 and §10 imply.**
- The random-superposition operator test (§5.4) was run only on v1, in `reviews/001`.
- `compressed_circuit_llm_2x4_classA_v2` and `compressed_circuit_llm_2x3_classA` have had own-reference Aer runs
  only: the noise agent ran 40/75 and 44/44, with one proposer sample.
- No document reports an independent operator test for them.

*Fix:* state this in §1.2, or have the §5.4 test run on v2 and 2x3 class A.

**I12. The porting effort is understated (§11 step 5).**
- §11 step 5 says to port eight modules "adapting only the layout helpers".
- But §12.5 lists 17 private `skqd.circuits_ir` helpers plus `sparse_sim` and `quantinuum_native`.
- Other parts are lattice-specific beyond `corners_of`:
  - `Problem` fixes $g^2=4.0$, sectors `twoB ∈ {0,2}` and the ladder.
  - `proposals.py:69-90` hard-codes 2x4 term tuples for `pkg`, `rpkg`, `cf2` and `*_sw`.
  - `eval_family.py:130`, `certify_family.py`, `native_family.py` and `verify_aer_family.py` only know $L_x\in\{3,4\}$.
  - `corner_frame` raises for blocks other than size 2 and 3.

*Fix:* give an honest port list: (i) the package interface, (ii) the private synthesis helpers, (iii) the
lattice-specific code.

**I13. The generalisation guide (§4) has several gaps.**  Details are in §3 below.  In short:
- There are no literature references for the factorisations.
- Several statements are judgements but are not marked [heur].
- It never says that for U(1) and SU(3) the plaquette is $T+T^\dagger$ with non-Hermitian $T$, so the
  factorisation applies to $T$.
- It never discusses rectangular SVD blocks (kernel = dark states).
- It never discusses the length of the Jordan–Wigner string in 2D.

### Minor

- **m1 (§6.1).** "63 `#print axioms` lines" is inaccurate.
  - The sources contain 66 `#print axioms` commands.
  - The log has 63 lines "depends on axioms", all within {propext, Classical.choice, Quot.sound}, plus 3 lines
    "does not depend on any axioms".
  - My scratch rebuild reproduced this exactly.
- **m2 (§5.6).** "4 184 564 strings (33 s)": the cited `data/eval_arch_it5_input_pp_exact_crosscheck.json` gives
  `sparse_wall_s` = 27.7 s for that circuit (B1_ref230_k1).  The 33 s comes from report 003 prose.
- **m3 (§3h).** The counts "`B0_ref1338` 760/762" are not in the cited key `k_dependent_references_by_count`, which
  lists names only.  They are in `data/eval_arch_it5_input_pp_all75_pruned.json` (760, 760, 762, 760, 762).
- **m4 (§3c pseudo-code).** It calls `multiplexed_two_level`.  The real function is the private
  `skqd.circuits_ir._multiplexed_two_level`.
- **m5 (§3i, §5.3).** The sign convention of "the measured global phase" is not given.  My 2x2 test found
  $\arg\langle t|\psi\rangle=+\theta\,(H_{\rm diag})_{rr}$ to $6.0\times10^{-15}$ rad.
- **m6.** Several numbers are sourced only to report prose, not to a JSON:
  - report 003 §2.3.4: 2 110 and $3.4\times10^{-14}$;
  - §2.4.3: 6 + 6 CX;
  - §2.4.5: 5 against 22 multiplexors;
  - §2.4.8: 4–5 %;
  - §2.3.7: 900 s and 4.3 GB.

  Lines 9–10 promise a file next to every number.  Either point to the JSON, or state that these come from prose.
- **m7 (§1.3).** "Whether it beats 252 ZZ is unknown".  This is cheap to settle; see §2 test T2.  The manual
  should not quote my scratch numbers, but it can say that the run takes under a minute.
- **m8 (§7.1).** I could not check arXiv:2610.22367 offline.  The authors and title are given, which is enough to
  look it up.

### Checked and correct (no action)

- **Code references.** Every `src/c2x4` function, class and constant named in §2–§12.1 exists with the stated name
  (checked one by one with grep), apart from m4.  All 36 skqd names in §12.5 exist too, including `Ladder.ends`, `CircuitFactory.hop_gates/plaq_gates/diag_gates/prepare`
  and `Model.reference`.
- **Lean.** Every lemma marked [Lean] in §3, §5 and §6.2 exists in the stated file (62 names checked with grep).
  The per-file counts match: Bits 14, Peephole 8, Ucr 7, Pair 13.  The toolchain and Mathlib tag are `v4.35.0`.
  There is no `sorry` or `admit`.
- **Numbers.** About 40 numbers were checked against the cited JSON files, and all match:
  - frozen 2x2: 252 ZZ, depth 201, $f$ 0.7929;
  - frozen 2x3: 2158 ZZ, depth 1925, $f$ 0.1502;
  - frozen 2x4: 71548 ZZ, depth 70300, $f=4.184\times10^{-29}$;
  - v2 class A: 1492 / 948, and v2 class B: 580–763 / 675.0;
  - certified bounds $1.75\times10^{-12}$ and $7.70\times10^{-13}$, rounding $1.59\times10^{-12}$, prune $1.05\times10^{-13}$;
  - v1 with rounding: $1.716\times10^{-12}$ and $7.715\times10^{-13}$;
  - 2x3: 871 / 611 and 309–465 / 387.6, Aer $3.05\times10^{-14}$ and $2.10\times10^{-14}$;
  - $f$ H2-2: 0.25115, 0.52932 (0.4881–0.5763), 0.44504, 0.69169;
  - per-term hop sum 1370 → 1144, and the term sum 1530;
  - certificates 64/65 (643 against 632, walk 750 against 697), 813/852, 43/43, 388/396; plaq1 85 against 78 after 1 500 s;
  - plaq1 multiplexor: 7 controls, support 85, walk 92;
  - reachable blocks: plaq1 344–578 of 648, hops 0–12;
  - pair ratio $1/\sqrt2$ to $9.4\times10^{-11}$;
  - plaquette product residual $2.55\times10^{-15}$;
  - A1 checks: $1.03\times10^{-14}$ over 130 and $8.77\times10^{-15}$ over 975;
  - wall times 916, 1307–1432, 513–561, 528, 1298, 433 / 370, 847 and 518 s;
  - Aer sample times 750 / 1310 s;
  - CX-resynthesis gains 13–14 and 2–11;
  - approximate-class counts 660 / 582 / 660;
  - reviewer 001: random-superposition $\ell_2$ error $\le5.03\times10^{-14}$ over 8 runs, and the class-B contrast $2.30\times10^{-2}$;
  - noise numbers in §9, found in `noise/reports/003-noise-results.md` §4.
- **Conventions (CLAUDE.md rule 2).** No drift.  The manual's $\eta=i$ on x-links and real on y-links, its
  little-endian order (qubit $k$ = bit $k$), and its doubly stored links all agree with `lattice.py`, `codec.py` and
  `reference_sim.py`.

---

## 2. Practical-test log

**Setup.**
- Python: the `coding` env (`/home/digimonk/anaconda3/envs/coding/bin/python`; qiskit 2.5.2, qiskit-aer 0.17.2,
  scipy 1.18.0).
- Everything ran in the scratch folder.
- In every script I redirected the cache and the archive path before any import of builders.  This is the recipe
  that I1 asks the manual to add:
  ```python
  import c2x4.env as env; env.CACHE = SCR+"/cache"; env.archive_path = lambda l: f"{SCR}/data/archive_{l}.json"
  import c2x4.problem as problem; problem.CACHE = env.CACHE
  import c2x4.family as family;  family.CACHE = env.CACHE
  ```
- A check with `find -newer` afterwards showed no new or changed file in the repository except gitignored `__pycache__`.

| # | manual step | command | result | wall |
|---|---|---|---|---|
| T1 | §1.3 inputs and §3b structure tests, 2x2 | `python t1_problem_structure.py` | **worked** (details below) | 0.25 s |
| T2 | §7.1 / §11 steps 7–8, both classes, 2x2 | `python t2_loop_2x2.py` | **worked** (details below) | 23.3 s (loop 17.3 s) |
| T3 | §5.3 / §5.4 independent Aer check, 2x2 | `python t3_aer_2x2.py` | **worked** (details below) | 3.1 s |
| T4 | reproduce §3e/§3g per-term class-A counts, 2x3 | `python t4_2x3_terms.py` | **worked** (details below) | 4.5 s |
| T5 | §12.4 unit tests | `python -m pytest -q -p no:cacheprovider tests/` (study dir) | **17 passed**; no cache file written | 34.2 s |
| T6 | §6.1 Lean build | copy of `lean/` in scratch, `.lake/packages` symlinked, `lake build` | **Build completed successfully (9059 jobs)**; 63 + 3 axiom lines (see m1); 0 `sorry` | 47.9 s |

**T1: inputs and structure tests (2x2).**
- `Problem(lx=2)` matches every claim in §1.3:
  - 12 qubits and 82 basis states;
  - terms `diag, hop0..hop3, plaq0`;
  - `dt` = 0.24501194722475933 and 0.33194310785049674, exactly equal to the two frozen manifests;
  - references `[6, 43, 30, 21, 17]` and `[14, 7]`.
- Every block of every term is bipartite with zero diagonal.
- plaq0 factorises over its corners: product residual $2.2\times10^{-16}$, magnitude residual $1.3\times10^{-15}$.
  All four corners have no third link (`third` = None), as §1.3 says.
- Hops: the magnitude-fit residual is $\le8.9\times10^{-16}$ and the signs factorise.  $\eta=i$ on hop0 and hop2
  (x-links) and is real on hop1 and hop3 (y-links).

**T2: the loop, both classes (2x2).** It used the proposal sets of the §12.4 it6 commands, run in-process.
- Class A, best per term:

  | term | best proposal | ZZ |
  |---|---|---|
  | hop0 | `full_lin` | 64 |
  | hop1 | `full_lin` | 52 |
  | hop2 | `full_lin` | 64 |
  | hop3 | `full_lin` | 52 |
  | plaq0 | `cfg_lin` | 34 |

- The `jwc_*` proposals raise `NotImplementedError('no JW qubits')` on the y-hops.  The loop records this
  correctly; it is not a failure.
- I assembled each class with `family_from_spec("arch:L2_mtest:<cls>:pp2", lx=2)` and built all 28 circuits.
- Class A: **245 ZZ on all 28 circuits** (the frozen family has 252), depth 188.  Certified pruned check
  (`verify_circuit_pruned`, $\tau=10^{-15}$): **28/28 pass**, maximum certified deviation $2.0\times10^{-13}$,
  direct leakage 0.
- Class B: **55–162 ZZ (mean 119.4)**, depth 45–137.  **28/28 pass**, maximum certified deviation
  $1.4\times10^{-13}$.
- Output: `t2_out.json`.

**T3: independent check with my own converter (2x2).**
- My converter refuses multi-qubit `unitary` gates.  The simulator was Aer statevector, double precision, fusion off.
  The target came from the package call `coarse_states(term_groups(Model(2).terms, 4.0, mass_default(4.0)), …)[k]`,
  with $dt$ from `Model(2).reference`.
- Own-reference runs:
  - class A: 28/28, maximum $|\Delta\psi|$ $1.10\times10^{-14}$;
  - class B: 28/28, maximum $6.93\times10^{-15}$;
  - non-codeword leakage $\le8.0\times10^{-32}$;
  - the X-gate prefix equals `prepare(ref)` in all 56 circuits;
  - class-B phase $=+\theta(H_{\rm diag})_{rr}$ to $6.0\times10^{-15}$ rad.
- Random-superposition test (B = 0 sector, 38 states, reference 6, $k=2$):
  - class A: $\ell_2$ error $8.5\times10^{-15}$ with seed 11 and $8.2\times10^{-15}$ with seed 12;
  - class B: $\ell_2$ error 1.11 (maximum 0.53).  This is the expected failure that defines class B.

**T4: per-term counts at 2x3.**
- plaq0 `cfg_lin` 88, plaq1 `cfg_lin` 96, hop0 `cb1` 130, hop3 `jwc_bframed_milp` 124.
- All four are identical to `data/report004_tables.json` `per_term_2x3`.  All pass A1 at $\le6.6\times10^{-15}$.

**Not run.**
- `native_family.py` (pytket venv): it writes `data/native_*.json` and has no 2x2 branch (see §1.3).
- The production commands of §12.4: they would overwrite cited files (see I1).
- No command failed.  The only obstacle was having to monkey-patch the output and cache paths, which the manual
  does not mention.

---

## 3. Transferability of §4 (generalisation)

The method is general in principle.  Its core needs:
- exact per-term locality;
- bipartite blocks with real matrix elements in some gauge;
- factorisation of terms over vertices or corners;
- redundancy in the encoding (for the clean ancillas);
- for class B, a small reachable set.

The method itself is clear on this ("test first, construct second", the fallback order of §4.6).  What another
project needs and does not get:

**All theories.**
- First the B1 material: a newcomer cannot judge "is my encoding like yours?" without it.
- §4 has no literature references.  The corner and $6j$ factorisation of plaquettes in the singlet / local-multiplet
  basis has published sources that would anchor §4.2 and §4.3.  Candidates are the loop-string-hadron papers of
  Raychowdhury and Stryker, and Ciavarella, Klco and Savage on SU(3) in the local multiplet basis.  I give names
  only; the planner should add verified arXiv IDs.
- Several §4 statements are judgements but are not marked [heur]:
  - "steps (c)+(f) apply directly" (U(1));
  - the incrementer recipe;
  - "The frame costs a multiplexed basis change per corner";
  - "Expect plaq1 costs everywhere";
  - "Clean ancillas are more plentiful";
  - "Reachable sets … grow faster".

**U(1).**
- Spin-1/2 quantum links: adequate.
- Missing:
  - that $U_P$ is not Hermitian, so $h_P=T+T^\dagger$ and the factorisation is applied to $T$, not to $h_P$;
  - that with links stored once (the usual U(1) encoding) the clean-ancilla trick has no source, and §2.3 says so;
  - a worked count for the smallest U(1) plaquette, so the reader knows what "good" looks like.
- Higher truncations: one sentence, untested.  It needs the explicit form of the link raising operator in binary and
  Gray encodings, and a statement that it is a cyclic shift, which is not a single flip.  It also needs a fallback
  rule: treat each link as a bipartite chain and use the SVD frame.

**SU(2) at $j_{\max}>\tfrac12$.**
- The SVD frame recipe is the right idea.  Any bipartite block $\begin{pmatrix}0&K\\K^T&0\end{pmatrix}$ splits into
  $2\times2$ pairs through the SVD of $K$.
- Missing:
  - the rectangular case, where $K$ is not square or is rank-deficient.  Its kernel is the set of dark states and
    must get flags, as at the interior corners here.
  - the cost of the frame.  A dense basis change on a corner with $d$ multiplicity states costs $O(d^2)$ Givens
    rotations, each one a multiplexor.  The reader needs that to decide whether to try the frame at all.
  - a statement that `corner_frame` and `_bright_rotations` must be rewritten, not only adapted.  They raise
    `NotImplementedError` for blocks larger than 3.

**SU(3).**
- Three bullets only.  Missing:
  - the plaquette is $T+T^\dagger$ (as for U(1));
  - matrix elements may be complex with no real gauge.  The angle-linear synthesis of §3h then fails (§2.3 says
    "fails loudly"), and the manual does not give a replacement.
  - multiplicity labels need more than one qubit, so the "vertex bit" flag logic does not carry over;
  - no estimate of local codeword counts, and no sign of which steps stay tractable (for example the MILP grows
    with the number of controls $m$).

**2D lattices.**
- Missing:
  - vertices with 4 links: the corner frame meets blocks larger than 3, so it needs the SVD frame;
  - Jordan–Wigner strings in 2D cross a whole row.  The parity fold of §3g.5 costs about $|J|-1$ CX each way, so
    JW handling dominates the hops on long rows.  The manual should say so and point to alternatives (§4.5 lists
    them without costs);
  - no guidance on scheduling disjoint commuting terms in parallel to reduce depth (§2.2 q1 allows reordering
    disjoint terms);
  - the code is a ladder throughout (`Ladder`, `corners_of` with `c00..c01` and a single "third" link).

**Bottom line for §4.**
- A U(1) spin-1/2 project could start today.  An SU(2) $j_{\max}=1$ project could start with significant design work.
- SU(3) and 2D projects get the strategy (test, then construct) but not a procedure.
- Calling §4 a "guide" is fair.  Calling it enough to "reproduce the same level of compression" is not yet supported.
