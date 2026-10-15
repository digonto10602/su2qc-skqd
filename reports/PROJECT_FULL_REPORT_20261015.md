# su2qc-skqd: full project report for a judge (2026-10-15)

## 0. How to read this file

**What this file is.** One self-contained description of the whole `su2qc-skqd` project (a research code base and preregistered experimental programme owned by Digonto, repository `https://github.com/digonto10602/su2qc-skqd`, local path `/home/digimonk/Projects/su2qc-skqd-v0.1.0`), written on 2026-10-15 from the repository's own files so that it can be handed to another assistant that has no access to the repository. That assistant is asked to (i) judge what is going on and (ii) generate plots. The file therefore carries every number, every description, a list of what contradicts what, and machine-readable data blocks (Section 18) with a list of suggested plots (Section 19). It **refreshes** `reports/PROJECT_FULL_REPORT_20261013.md` (3 327 lines, commit `da21d6e`, which stays unchanged in the repository) and keeps its structure, its evidence labels and its glossary; Section 0.1 lists what changed. Sections 2, 3 and parts of 4, 6, 12, 13, 16-18 and 20 are carried over where nothing changed; every changed place is marked "(updated 2026-10-15)" or sits in a new subsection.

**Repository facts (from `git log`, `git worktree list`, 2026-10-15 17:43 UTC).** Branch `master` at `10f88a0` (`prompts/33e`, committed 17:41 UTC and pulled into the working tree by `scripts/ci_check.sh` while this report was being written; before that `34f73a7`), up to date with `origin/master`; **352 commits** (the first `5e3fe61`, 2026-09-14), **81 newer than the previous report's commit** `da21d6e`, most of them the CI robot's `ci: submitted` / `ci: results` commits. Both executor branches of 2026-10-13 are **merged** (`c33c` by `5f8a720`; `q35` through `4149de7` / `e66eb26` / `7c46329`). One new executor branch exists, `c33e`, with one unmerged commit (`daeb40c`, 17:46 UTC, the laptop CPU-reference runner of `prompts/33e`); as instructed I did not read the worktree directories. Untracked in the main tree: `.claude/worktrees/`, `data/hardware/H0_ddrep_dryrun_prototype/` (empty) and this report. The commit that adds this report is local and **not pushed**.

**How strongly each statement is supported (the labels used throughout).**

| label | meaning |
|---|---|
| **[GATE]** | computed by a gate script that wrote `"status": "PASS"` (or an explicit FAIL) into `validation/<GATE>.json`; cited with file and key |
| **[MEAS]** | a measurement on real hardware recorded in a `validation/*.json` measurement gate (PASS of a measurement gate means "preregistered, measured, consistent", never "the number is good") |
| **[SIM]** | the output of a simulation (Aer, pecos, Selene, exact statevector) inside a gate; true of the model, not of a device |
| **[PLAN]** | planner arithmetic: a number the project's planner agent computed in a prototype script (`scratch/planner/`) or in prose; not reproduced by a gate unless the text says so |
| **[EST]** | an ESTIMATE: an input that is a guess or a vendor-page figure (cost per credit, transport error, etc.) |
| **[EXEC]** | executor-reported, not in a gate JSON. **Retired in this report**: everything the 2026-10-13 report labelled [EXEC] is now in a committed data file or gate JSON and is cited as such |
| **[MINE]** | a trivial sum, ratio, pooling or probability I computed from sourced numbers while writing this file (the sources are named); in Section 7.10 and block (ag) this includes pooled clean fractions and rigorous bounds for the not-yet-assembled split runs |

**Rules this file follows (the owner's reporting rules).**

1. *Plain English.* Every technical word is defined the first time it appears; Section 20 is a glossary of all of them (with a new list of terms since 2026-10-13).
2. *Project labels.* Names such as "B_all", "B_sig", "rule D3'", "D3'-R", "C22", "f_hit", "f_ideal", "r_nc", "Stage E / P", "K0", "K1", "CV1-CV5", "E_tol", "class 1-4", "E1-E8", "O0-O6", "F1-F8", "RM", "PTA", "Kraus arm", "IBM-T0 / T3", "S6", "P15", "Q1L", "tiers T1-T6", "part", "half" are **the project's own labels** (invented inside this project, mostly by its planner agent), not standard physics or computer-science terms. Each is explained where first used and in the glossary.
3. *Math* is written in LaTeX: $\ldots$ inline, $$\ldots$$ displayed.
4. *Numbers.* Every number carries units, an interval where one exists, and the source file (and JSON key where useful). `validation/C4_F5_B0.json -> data.frun.at_N.certificate.width` means "open that file, go to `data`, then `frun`, ...". "95 %" intervals are the intervals the source file states; I recomputed none except where marked [MINE].
5. *Never invented.* If a number is not in a repository file I say so (Section 16 lists the ones I could not source). Planner arithmetic is [PLAN]; guesses are [EST].
6. *"PASS" does not mean "the result is good", and "FAIL" does not always mean a physics failure.* Six of the 18 FAIL files fail only on a budget, infrastructure or by-construction criterion while their physics criteria pass (Section 5.4); Sections 7 and 8 say which criterion failed each time.
7. *Rule 1 of the project (`CLAUDE.md`).* "A gate passes only when its script writes status PASS, not when the prose says so. Numbers in prose must come from `validation/*.json` or `data/*.json`." This file inherits it.

**Units used.** Energies are in the lattice units of the Hamiltonian (dimensionless numbers such as $-5.6026$). Device times are in microseconds ($\mu$s), nanoseconds (ns) or seconds (s); QPU time in seconds as billed by IBM; Quantinuum cost in HQC (hardware quantum credits; eHQC on its emulators); GPU cost in seconds or GPU-hours on one NVIDIA A100 of Perlmutter; angles in radians or, where pytket is concerned, half-turns (1 half-turn = $\pi$ rad). All UTC times derived from MDT (UTC-6) or PDT (UTC-7) stamps are my conversions.

**Date and status caveat.** "Today" is 2026-10-15, about 11:45 MDT (17:45 UTC). As instructed I ran **no gates, tests, simulations, QPU jobs or CI requests**; I read files, ran `scripts/ci_check.sh` once (it reads the queue, but its first line is `git pull --rebase --autostash`, which pulled `prompts/33e`; Section 13.8) and small python one-liners (for example to pool part files and to recompute Garwood intervals, all labelled [MINE]). Eight Perlmutter requests (`C4_F2_B0`, `C4_F2_B1`, `C4_PART_12..17`) were committed at 17:37 UTC and are pending; their results are not in this report.

**File map for the reader.** 1 executive summary; 2 physics and method from scratch; 3 the plan and its amendments; 4 the package; 5 the full gate table (87 files); 6 the chronology to 2026-10-15; **7 campaign 33 in full, with all 25 class-4 run files (7.8-7.10)**; **8 the Kraus / RM / PTA question from C2_CAL to C2_KCHK and `prompts/33e`**; **9 the Quantinuum tests as committed gates**; 10 the pipeline status matrix; 11 device readiness and submission scripts; 12 resources; 13 what was learnt (with **13.8 process issues**); 14 where we are, publishability, risks; 15 open owner decisions (renumbered); 16 contradictions and unsourced numbers; 17 progress measure; 18 DATA APPENDIX (blocks (a)-(ap)); 19 suggested plots (1-56); 20 glossary.

### 0.1 What changed since the 2026-10-13 report

- **Campaign 33: the class-4 full noisy 2x3 SKQD runs are harvested.** 25 run files from 25 Perlmutter jobs (`C4_F5_B0`, `C4_F1_B0`, `C4_F7_B0`, `C4_F5_B1` + `C4_PART_01`, `C4_F1_B1` + `C4_PART_10`, `C4_F7_B1` + `C4_PART_11`, the F4 halves `C4_F4_B0a/b`, `C4_F4_B1a/b` with `C4_PART_02..05`, the F8 halves with `C4_PART_06..09`): ten runs over scenarios E1, E7(0.07), E7(0.10) and E8, two circuit sources, both sectors. **$E_0$ is inside the certificate in 25 of 25 files**, the certified widths are far inside the signed limits, recall of the 99.9 % support is $\ge0.989$; 23 files PASS, `C4_PART_02` and `C4_PART_04` FAIL only on S6 (each took 45 696 of 49 984 shots because the conservative deadline rule stopped it; Section 7.9). The split runs are not yet assembled; Section 7.10 gives pooled values and rigorous bounds [MINE] (Sections 7.8-7.10, blocks (ae)-(ah)).
- **Class 2 (IBM noise) is blocked, and the question changed.** The `c33c` executor's CPU diagnostics showed that Kraus run on the CPU (7.47 $\pm$ 0.56) agrees with RM (7.42) and that the GPU Kraus arm (2.40) is the outlier; `prompts/33d` withdrew the planner's earlier explanation and designed `C2_KCHK`. **`C2_KCHK` (job 59780907) FAILED 7/10**: the GPU arms show Aer's GPU Kraus path giving 3.00, 3.57 and 1.14 for one channel depending on the engine and on gate fusion, but both CPU reference arms got 0 shots (a one-thread process), so the production representation is `blocked`. `prompts/33e` (2026-10-15) found the cause (`srun` without `--cpus-per-task`) and orders run 2. **Open** (Section 8).
- **`prompts/35`, `35a`, `35b`: the Quantinuum tests are committed gates.** 2x2: `Q0P_2x2` PASS 5/5, `QN_2x2` PASS 5/5 (308 f-cells over 11 scenarios, plan-of-record runs under E1, E3, E4, E5b), `QEMU_2x2` PASS 3/3, `QH_2x2` PASS 4/4; 2x3: `QH_2x3` and `QEMU_2x3_laptop_smoke` PASS (information); 2x4: `Q0P_2x4` **FAIL by construction** (79 circuits in two sources, conversion proven, the $10^{-10}$ state bar to be measured on the GPU slot `QV_2x4_01`), `QN_2x4` PASS (analytic, $f\approx0$), `QEMU_2x4` infeasible, `QH_2x4` not attempted, `QSC_prepared` (syntax checks need a Nexus login) (Section 9).
- **Perlmutter.** 25 more jobs returned (8.33 GPU-hours [MINE]); 37 campaign jobs and 12.10 GPU-hours in all; the queue turned round a wave in 1.0-5.4 h on 2026-10-13/14. Eight requests are pending (F2 and slots 12-17). The maintenance is 2026-10-21 06:00 to 2026-10-28 06:00 UTC (Sections 7.12, 12).
- **Process issues** (Section 13.8): `scripts/ci_request.sh`'s `git pull --rebase` conflicted with the merge history, so requests were committed directly; the `C2_KCHK` laptop dry run cannot meet its 8-minute budget (the CPU Kraus arm is slow by design) and fails one test in every full pytest run; every CI job's CPU phase ran on one core; the assembly has not been run.
- **Hardware: nothing new.** No QPU job since 2026-10-06; 327 s used, 273 s left of 600 s.
- **No owner decision in a file since 2026-10-06.** The open items are renumbered in Section 15; the $r_{nc}$ item (1.115 versus 1.078) is item 1.
- **Counts.** 87 gate result files with a criteria list (69 PASS, 18 FAIL; 54 / 40 / 14 on 2026-10-13); 352 commits; 43 CI job logs.

## 1. Executive summary for a judge

### 1.1 What the project is, in plain English

`su2qc-skqd` tests whether a quantum computer can help find the lowest energy levels of an SU(2) lattice gauge theory (a two-colour toy version of the strong force, with dynamical "staggered" quarks) on small two-row lattices ("ladders" of 2x2, 2x3 and 2x4 sites). The method is **neural-enhanced sample-based Krylov quantum diagonalization (SKQD)**: a quantum computer prepares states that spread a starting configuration over the configurations that matter; the measured bit strings are decoded and used to choose a small subspace; an ordinary computer then finds the exact lowest energy inside that subspace together with a rigorous error bar (the Weinstein and Kato-Temple certificates). The quantum device only *chooses the subspace*; the energy found can never lie below the true value. The "neural-enhanced" part (a learned ranking of configurations) exists only as a minimal ridge-regression baseline tested on exact amplitudes. The project's own manual expects, and says it is publishable as, a **characterised null result**: at these sizes a classical selected-configuration-interaction method of the same subspace size is at least as good as the device.

### 1.2 Where it stands (2026-10-15)

- **Classical machinery: complete and validated** [GATE]: exact references, the gauge-invariant basis, the hardware codec and decoder, exact structured circuits for 2x2/2x3/2x4, the certificates, the emulated 2x3 plan check, the noiseless GPU reference of the whole 2x3 family.
- **2x3 in simulation: the method works under every Quantinuum-type noise model tried** [SIM]. Ten full noisy SKQD runs (25 GPU files; scenarios E1 = published H2-2 rates, E7(0.07) and E7(0.10) = matched clean fraction, E8 = gate S3's model; both sectors) reproduce the exact ground-state energy with $E_R-E_0$ between $1.2\times10^{-4}$ and $1.1\times10^{-3}$, $E_0$ inside the rigorous certificate in **25 of 25** files, Kato-Temple widths $4.6\times10^{-4}$-$1.15\times10^{-3}$ at $B=0$ (limit 0.1) and Weinstein widths 0.036-0.089 at $B=1$ (limit 0.15), at simulated clean fractions $\hat f_{\rm ideal}=0.12$-$0.24$ (Section 7.8). This is about the *algorithm under assumed noise*, not about any device.
- **2x3 under IBM noise in simulation: blocked** [SIM]. The GPU Kraus path of Aer 0.15.1 gives inconsistent answers for one channel (3.00 / 3.57 / 1.14 bits by engine and fusion setting, against 7.47 on the CPU); the job built to decide the representation (`C2_KCHK`) lost its CPU reference to a one-core Slurm binding; run 2 is ruled, not run (Section 8).
- **2x3 on a real quantum computer: one measurement, a firm NO-GO on IBM** [MEAS]: 0 reference hits in $2\times10^5$ shots; $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %). Only Quantinuum trapped-ion machines meet the signed bar on published numbers; **no access has been requested** (an email draft exists).
- **2x2 on a real quantum computer: done once, not a physics result** [MEAS] (`ibm_kingston`, 53.0 s; noise saturates every sector at this size; the XY4 gain of 2026-10-02 did not replicate on 2026-10-06).
- **2x2 and 2x4 for Quantinuum: tested as far as possible without an account** [GATE]. 2x2 passes native compilation, noiseless sampling on three independent engines (Aer, the vendor's local emulator, Selene/HUGR) and 308 noise-model cells; 2x4 is compiled in two sources, its exactness bar awaits a GPU job, and every scenario at published rates gives $f_0\le10^{-23}$ (Section 9).
- **Neural step, primary endpoint P1, gates H1 / H2 / M1:** open (need 2x3 hardware data).

### 1.3 The ten most important numbers

| # | number | meaning | strength | source |
|---|---|---|---|---|
| 1 | **0 reference hits in 200 000 shots** of the two signed 2x3 circuits on `ibm_kingston` (0.191 expected from garbage); $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %), about 4 850 times below the bar 0.1 [MINE] | 2x3 on IBM Heron is a *measured* NO-GO | [MEAS], one job | `validation/K1_2x3_fpilot.json -> data.pooled` |
| 2 | **25 of 25** class-4 files certify $E_0$; $E_R-E_0$ $1.21\times10^{-4}$ to $1.05\times10^{-3}$; Kato-Temple width $4.59\times10^{-4}$-$1.15\times10^{-3}$ ($B=0$), Weinstein 0.036-0.089 ($B=1$); recall of $S_{999}$ 1.0 in 23 files and 0.989 in 2 | the noisy 2x3 SKQD pipeline works end to end at $\hat f_{\rm ideal}=0.12$-$0.24$ | [SIM], 10 runs, 4 scenarios, 2 circuit sources | `validation/C4_F*.json`, `C4_PART_01..11.json -> data.frun.at_N.certificate`; Section 7.8, block (ae) |
| 3 | **Pooled $\hat f_{\rm ideal}$ of the full runs**: E1 0.228 / 0.218 ($B=0$ / $B=1$); E7(0.07) 0.130 / 0.117; E7(0.10) 0.168 / 0.163; E8 0.120 / 0.122 [MINE pooling] | the clean fraction the method was tested at; the E7 labels understate it by a factor 1.7-1.9 [MINE: 0.168/0.10, 0.130/0.07] | [SIM] | block (ag); `data.frun.clean_fraction.pooled_k1` |
| 4 | **Class-2 mean Hamming weight on IBM-T0** (20 bits; unital limit 10): GPU Kraus 3.00 $\pm$ 0.24 (cuStateVec), 3.57 $\pm$ 0.25 (native), 1.14 $\pm$ 0.22 (fusion off); GPU RM 7.43 $\pm$ 0.10; laptop CPU Kraus 7.47 $\pm$ 0.56; device on the flown T3 9.771 $\pm$ 0.007 | the GPU Kraus simulation is internally inconsistent; the representation decision is blocked | [SIM]/[MEAS]; CPU arms of the CI job empty | `validation/C2_KCHK.json`, `data/campaign33/c33c_diag/summary.json`, `validation/C2_CAL.json` |
| 5 | Clean fraction on the same frozen 2x2 circuits: **0.0400 (2026-10-02) versus 0.0818 (2026-10-06)**; XY4 $R$ 2.819 versus 0.895 | a device's clean fraction is not a stable property; one-day A/B tests do not transfer | [MEAS], two jobs | `validation/H0_ddtest.json`, `H0_ddrep.json` |
| 6 | **$r_{nc}$ 1.115 (signed) versus 1.078** (new pooled upper end; pooled 1.055 [1.033, 1.078]); the owner-item rule now fires in code | the correction that turns $f_{\rm hit}$ into the signed-bar quantity is under review | [SIM] | `validation/CF_traj.json`, `C4_CF.json -> data.pooled`; Section 7.6 |
| 7 | **327 s of 600 s** IBM QPU time used, **273 s left**, 14 jobs | the whole hardware budget; nothing spent since 2026-10-06 | account counter | `data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json` |
| 8 | **665 605 HQC** at $f=0.10$ (1 279 660 at 0.05; 471 801 at 0.15) for the 2x3 plan of record; Stage E / P **9 949.92** eHQC / HQC | the price of a real 2x3 measurement on Quantinuum; 0 HQC spent; no access | [GATE] arithmetic, [EST] for money | `validation/CV_2x3_plan.json`, `Q0P_2x3_plan.json` |
| 9 | **Quantinuum native circuits:** 2x2 252 ZZPhase, 0.6109 HQC/shot, gate-only $f$ 0.7929 (H2-2) / 0.8046 (Helios-1), D3' plan 13 990 HQC; 2x3 2 158 ZZPhase, 4.9666 HQC/shot, $f$ 0.1502 / 0.1642; 2x4 69 676 (opt-3) or 71 548 (structured) ZZPhase, 157.5 / 185.4 HQC/shot, gate-only $f\le6\times10^{-27}$ (H2-2), rounding bound $5\times10^{-9}$ / $6\times10^{-12}$ against the $10^{-10}$ bar | 2x2 easy, 2x3 marginal, 2x4 impossible on trapped ions | [GATE] | `validation/Q0P_2x2.json`, `Q0P_2x3.json`, `Q0P_2x4.json`, `QN_2x4.json` |
| 10 | **Perlmutter**: 41 timed jobs, **12.10 GPU-hours** (3.03 node-hours charged) [MINE]; a wave of four jobs returned in 1.0-5.4 h on 2026-10-13/14; 8 requests pending; maintenance 2026-10-21 06:00 to 10-28 06:00 UTC | simulation is cheap; the calendar and owner actions bind | measured | `reports/ci-*.out`, `git log`, block (a2) |

### 1.4 The five biggest risks and open questions

1. **No device has been *measured* to reach the signed bar at 2x3.** Every Quantinuum number is a vendor figure or a simulation; the transport (memory) error is unmeasured; its full runs (F6) and those of the emulator parameter set that halves the clean fraction (F3) are deferred past the maintenance; the access request is an unsent draft. *Evidence: strong that IBM cannot; weak (model only) that Quantinuum can.*
2. **The IBM-noise simulation has no validated representation.** Aer 0.15.1's GPU Kraus path disagrees with itself (fusion on versus off: $z=5.8$) and with the CPU; the CPU reference is 19 + 24 laptop shots; the CI CPU arms are empty; run 2 is ruled but not run; no class-2 cell exists. Campaign 33 therefore has no IBM-noise prediction for 2x3.
3. **The headline statistic is unstable and its correction unsettled.** The same circuits' clean fraction doubled between two days on IBM; $r_{nc}$ is 1.115 or 1.078 (owner item) and 1.172 for $k=4$; at 2x2 the f-cells sit 7 % below the 2x3 $r_{nc}$ expectation ("tension"); the gate-only $f$ differs by 15 % between two error conventions; the E7 labels understate the simulated $\hat f_{\rm ideal}$ by a factor 1.7-1.9.
4. **The scientific payoff is modest by design.** P1 is a characterised null (CIPSI at equal subspace size matches the oracle); the 2x3 campaign costs 0.47-1.28 M HQC; "neural-enhanced" is a plan; the 2x2 hardware result and the 2x2 simulations are noise-saturated.
5. **Schedule and bookkeeping.** The maintenance window falls next week; class 2, F3, F6, the `QV_2x4` slots, `C3_LE` and the syntax checks all wait on it or on owner actions (an environment, an allowlist file, a Nexus login); the split runs are not assembled; two parts are 8.6 % short with no re-request; one test fails in every full pytest run; the status table (`validation/gates.md`) lists no campaign-33 token.

### 1.5 Verdict on publishability (my judgement, based on the files above)

- **Publishable now:** a *methods and negative-result note*: a preregistered, end-to-end SKQD pipeline for 2+1D SU(2) with dynamical staggered quarks; the saturation rule with garbage-only and random-equal-size controls; the near-clean correction of the clean-fraction estimators; the day-to-day instability of a one-job A/B test; the coherent $x$-pulse over-rotation invisible in the IBM calibration record; the measured 2x3 upper limit on IBM Heron; **and, newly, a substantial simulation section**: the full noisy 2x3 SKQD runs that certify $E_0$ in every file under four noise scenarios (E1, E7(0.07), E7(0.10), E8), with the clean fraction at which this holds, the S1 proxy shown to be conservative by an order of magnitude in both sectors, and gate S3's long-open recall criterion answered in simulation; plus the device-requirement tables for 2x2/2x3/2x4 on trapped ions. If `C2_KCHK` run 2 confirms it, the Aer GPU Kraus inconsistency is an upstream bug report and a cautionary paragraph.
- **Not publishable now:** any SKQD *physics* result, any claim of device support quality, any 2x3 or 2x4 hardware spectroscopy, any "neural-enhanced" claim, any advantage claim, and any IBM-noise prediction for 2x3 (class 2 is blocked).
- **What would change the verdict:** a Quantinuum Stage E (emulator, 9 949.92 eHQC) that reads $\hat f_{\rm ideal}\ge0.10$, then a Stage P pilot; after that the plan of record (about 0.67 M HQC) gives the first 2x3 curves.
- **Strength of this verdict:** moderate; it rests on the project's preregistered bars and one IBM device, and its simulation part is strong as simulation and silent about devices. It depends on no unsourced number.

### 1.6 What is running or next

Eight Perlmutter requests are pending (`C4_F2_B0`, `C4_F2_B1` + `C4_PART_12` = the E2 (Helios-1 rates) runs; `C4_PART_13` = 16 dropped f-cells; `C4_PART_14..17` = the CV3 equal-shots samples of F5_B1 and F1_B1). `prompts/33e` (committed 17:41 UTC) orders the sbatch fix, `C2_KCHK` run 2 and a laptop CPU reference of 64 + 64 shots; an executor branch `c33e` has begun (one unmerged commit). After the maintenance: the class-2 cells, F3, F6, the `C4_CF` re-request, `QV_2x4_01`. Not yet scheduled: the campaign assembly and the re-requests of the two short parts. Owner items are in Section 15.

## 2. The physics and the method, explained from scratch

*(Carried over from the 2026-10-13 report; nothing in the physics, the conventions or the method changed between 2026-10-13 and 2026-10-15. Section 2.12 is the place to look first if the four "clean fractions" are unfamiliar.)*

Source of this whole section unless a file is named: `proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md` ("the manual", SU2QC Project 2 rev. 2, 10 Sept 2026), `README.md`, `CLAUDE.md`, `data/references.json`, and the gate JSONs named in the text.

### 2.1 What problem is being solved

**Lattice gauge theory.** The strong force binds quarks into protons, neutrons and similar particles. Its mathematical core is a *gauge theory* with the symmetry group SU(2) in the simplified two-colour version used here (the real strong force uses SU(3)). To calculate on a computer, space is replaced by a grid (a *lattice*); quark fields live on the grid points (*sites*), and the force-carrying (gauge) field lives on the segments joining neighbouring sites (*links*). The model here is the *Kogut-Susskind Hamiltonian* with *staggered quarks* (a standard way of putting quarks on a lattice in which one quark component sits on each site and the parity of the site, $(-1)^{x_1+x_2}$, tells whether it behaves as a particle or an antiparticle slot). The **Hamiltonian** $H$ is the operator whose lowest eigenvalue $E_0$ (the *ground-state energy*, "vacuum energy") and next levels are the physics output; an *eigenvalue* of a matrix $H$ is a number $E$ with $H\psi = E\psi$ for some vector $\psi$ (the *eigenvector*, i.e. the quantum state).

**The ladder lattices.** The package works on open "$2\times L_x$ ladders": two rows and $L_x$ columns. $L_x = 2, 3, 4$ gives the **2x2**, **2x3** and **2x4** lattices (the project's own short names).

**Hamiltonian** (manual eq. (1); `README.md`):

$$
H = -\frac12\sum_{\ell=(x\to y)}\Big[\eta_\ell\,\psi^\dagger_{x,i}U_{ij}(\ell)\,\psi_{y,j}+\text{h.c.}\Big]
\;+\; m\sum_x(-1)^{x_1+x_2}\,n_x
\;+\; \frac{g^2}{2}\sum_\ell j_\ell(j_\ell+1)
\;-\; \frac{1}{2g^2}\sum_P\big(W_P+W_P^\dagger\big).
$$

Symbols: $g^2$ gauge coupling (the reference value is $g^2=4$; $g^2=2$ and $1$ are also tabulated), $m=3g^2/16$ the quark mass (so $m=0.75$ at $g^2=4$), $\eta_\ell$ the staggered phases ($i$ on links in the $x$ direction, $(-1)^{x_1+x_2}$ on links in the $y$ direction), $\psi_{x,i}$ the quark field at site $x$ with colour index $i$, $U_{ij}(\ell)$ the link operator (the gauge field's "parallel transporter" along link $\ell$), $n_x$ the quark number at site $x$, $j_\ell$ the *link spin*, $W_P$ the *plaquette* (the product of four $U$ around one square of the lattice). Four physics terms therefore exist: **hopping** (a quark moves along a link and flips its flux), **mass** (diagonal), **electric** (diagonal, costs $\tfrac{g^2}{2}\cdot\tfrac34$ for each link that carries flux), and **plaquette** (flips the flux on all four links of a square).

**Truncation.** The gauge field on each link is cut off at spin $j_{\max}=\tfrac12$, so each link carries either no flux ($j=0$) or a spin-$\tfrac12$ flux ($j=\tfrac12$). The cost of this truncation on the 2x2 lattice is computed exactly in `data/references.json -> truncation_2x2`: raising the cut-off to $j_{\max}=1$ lowers $E_0$ by $0.0019205$ at $g^2=4$ (74 instead of 38 states in the $B=0$ sector).

### 2.2 Conventions (fixed; changing one forces a re-run of gates E1-E3)

From `CLAUDE.md` rule 2 and `README.md`:

- **Link generators**: $L_a=-J_a^{\top}$ acting on the left magnetic index, $R_a=+J_a$ on the right one; commutators $[L_a,U]=-(T_aU)$, $[R_a,U]=+(UT_a)$ (file `src/skqd/su2.py`). $J_a$ are the standard spin matrices.
- **Matter charge** $Q_a=\psi^\dagger\tfrac{\sigma_a}{2}\psi$ ($\sigma_a$ the Pauli matrices).
- **Site index** $x_1L_y+x_2$; links oriented in $+x$ and $+y$; Jordan-Wigner order equals site order (`src/skqd/lattice.py`). (Jordan-Wigner is the textbook trick that turns fermions into qubit operators by attaching a sign string.)
- **Qubit order**: qubit $k$ is bit $k$ of an integer, little-endian (`src/skqd/reference_sim.py`, Qiskit's convention); the codeword layout is in `src/skqd/codec.py`.

### 2.3 Gauss's law, physical states and the sectors

**Gauss's law.** A gauge theory has redundant degrees of freedom; only states that satisfy a local constraint, *Gauss's law*, are physical. At every site $x$ the colour charge carried by the outgoing links, the incoming links and the quarks must cancel:

$$
G_a(x)=\sum_{\ell\ \mathrm{out}}L_a(\ell)+\sum_{\ell\ \mathrm{in}}R_a(\ell)+Q_a(x)\ \Big(+\tfrac{\sigma_a}{2}\Big|_{\rm static}\Big),\qquad G_a(x)|\text{phys}\rangle=0 .
$$

($a=1,2,3$ labels the three SU(2) directions; the optional last term is a *static charge*, an infinitely heavy quark used to probe the potential $V(r)$ between charges.) Gate E1 verified $[G_a(x),H]=0$ with maximum residual $0.0$ in the 160 000-dimensional redundant space of the 2x2 lattice (`validation/E1.json`, criterion "max |[G_a(x), H]|"; the manual quotes $2\times10^{-15}$).

**Dressed-site basis.** The package does not work in the redundant space. It uses the *dressed-site* (spin-network) basis of the manual's Step 2: a basis state is
$|b\rangle=|\{j_\ell\},\{n_x\},\{\iota_x\}\rangle$, i.e. the link spins, the quark occupations $n_x\in\{0,1,2\}$ and, at vertices where the Gauss singlet is not unique, an **intertwiner label** $\iota_x$ (the label of which of the two possible gauge-singlet combinations is meant; the manual fixes it by a fusion-tree convention). The number of physical states, the manual's Table 2, reproduced by gate E2 (`validation/E2.json`, 51 criteria PASS):

| lattice | qubits | physical states | distinct $(\{j\},\{n\})$ labels without $\iota$ |
|---|---|---|---|
| 2x2 | 12 | 82 | 82 |
| 2x3 | 20 | 1 727 | 1 460 |
| 2x4 | 28 | 37 165 | 26 248 |

(Earlier versions of the plan used the labels without $\iota$ and thereby miscounted; the manual's Table 2 and gate E2 fix this.)

**Sectors.** $H$ conserves *baryon number* $B=\tfrac12\sum_x(n_x-n_x^{\rm vac})$ with $n^{\rm vac}_x=1-(-1)^{x_1+x_2}$ (a count of quarks minus antiquarks, divided by the number of colours). The project also uses the integer $2B$ ("twoB") as a key. Charge conjugation maps $B\to -B$, so only $B\ge 0$ is computed. Sector sizes (the manual's Table 2, gate E2): 

| lattice | $B=0$ | $B=\pm1$ | $B=\pm2$ | $B=\pm3$ | $B=\pm4$ |
|---|---|---|---|---|---|
| 2x2 | 38 | 20 | 2 | | |
| 2x3 | 677 | 426 | 95 | 4 | |
| 2x4 | 12 843 | 8 934 | 2 869 | 350 | 8 |

With a static pair at distance $r$: 2x3 with static pair $r=1$ has 2 729 states ($B=0$: 1 089), $r=2$ has 2 418 ($B=0$: 978) (manual Table 2; `data/references.json` keys `2x3+static r=1|...`).

The project calls the three experimentally relevant sectors **$B=0$** (the vacuum sector), **$B=1$** (one baryon, here a "diquark", a pair of quarks; the lowest levels there form a near-degenerate cluster of $L_x$ states) and the **static** sectors. Project key `2B=2` means $B=1$ and `2B=4` means $B=2$.

### 2.4 The exact reference energies ("exact $E_0$")

Because the sectors are small enough (up to 12 843 states), the Hamiltonian can be diagonalized exactly on a classical computer. These exact values are the *reference* against which every later approximate method is judged. They come from the **dressed-site builder** (`src/skqd/hamiltonian.py`, `exact.py`), which was validated against an independent route (the redundant-space "projector" construction, `src/skqd/fullspace.py`): all 82 eigenvalues agree to $2.3\times10^{-14}$ (`validation/H0_2x2.json` provenance row; `validation/E1.json`, 23 criteria PASS).

Key reference numbers at $g^2=4$, $m=0.75$ (`data/references.json -> references`; `validation/E3.json`, 85 criteria PASS):

| lattice, sector | dim | $E_0$ | next levels | $\Delta t=\pi/W$ | support$_{99}$ / support$_{99.9}$ | participation ratio |
|---|---|---|---|---|---|---|
| 2x2, $B=0$ | 38 | $-3.6407665507$ | $-0.9622448$, $-0.8505667$ | 0.24501195 | 9 / 16 | 1.4744 |
| 2x2, $B=1$ | 20 | $-1.8615880345$ | $-1.8197453$, $+0.2082291$ | 0.33194311 | 8 / 13 | 2.5924 |
| 2x3, $B=0$ | 677 | $-5.6026004579$ | $-2.8886027$, $-2.8651784$ | 0.15644332 | 31 / 86 | 1.9138 |
| 2x3, $B=1$ | 426 | $-3.8260844431$ | $-3.8017280$, $-3.6686561$, $-1.6528839$ | 0.18697342 | 42 / 95 | 3.5609 |
| 2x3, $B=2$ | 95 | $-2.0118247869$ | $-1.8622427$, $-1.8438853$ | 0.23360023 | 15 / 22 | 1.5043 |
| 2x4, $B=0$ | 12 843 | $-7.5652140739$ | $-4.8435986$, $-4.8374654$ | 0.11469820 | 76 / 305 | 2.4883 |
| 2x4, $B=1$ | 8 934 | $-5.7801629009$ | $-5.7741284$, $-5.6540876$ | 0.13031277 | 127 / 470 | 4.7849 |

Here "support$_{99}$" ($S_{99}$) is the smallest set of configurations that together carry 99 % of the ground-state *weight* $|\langle b|\Omega\rangle|^2$ ($\Omega$ = exact ground state), support$_{99.9}$ ($S_{999}$) the same for 99.9 %, and the *participation ratio* is the effective number of configurations that matter. Small supports are what makes the whole sampling method viable ("sparse ground state"). Further rows (other $g^2$, static pairs, units, the derived physical quantities) are in Appendix block (k). Derived 2x3 quantities at $g^2=4$ (`data/references.json -> derived`): meson-like gap $\Delta_0=2.7139978$, baryon mass $M_B=E_0^{B=1}-E_0^{B=0}=1.7765160$, static potentials $V(1)=1.3871769$, $V(2)=2.5898457$, binding $0.0377436$; at $g^2=2$: $\Delta_0=1.4980195$, $M_B=1.1350016$, $V(1)=0.7819829$, $V(2)=1.3740250$; 2x4 at $g^2=4$: $\Delta_0=2.7216155$, $M_B=1.7850512$.

### 2.5 The qubit encoding (the "codec") and the Gauss-law decoder

**Encoding.** A quantum computer holds states as bit strings in superposition. The project assigns each physical basis state a short bit string, a **codeword** (`src/skqd/codec.py`; manual Step 2.4):

- A *corner* vertex (two link ends) uses 3 qubits: two *flux bits* (one per link end; $j=\tfrac12\Leftrightarrow 1$) and one more bit that either gives the quark occupation ($n=0$ or $2$) or is a *flag* meaning "not a valid state".
- An *interior* vertex (three link ends) uses 4 qubits: three flux bits and one more bit (occupation, intertwiner label $\iota$, or flag).
- Totals: 2x2 has four corner vertices, so 12 qubits; 2x3 has four corners and two interior vertices, so 20; 2x4 has four corners and four interior vertices, so 28. A static charge at an interior vertex needs 5 qubits, so a static pair at $r=1$ on 2x3 costs 21 qubits.

Only 82 of the $2^{12}=4096$ strings at 2x2 are valid codewords; at 2x3, 1 727 of $2^{20}$.

**Decoder.** Every measured bit string (a *shot*) is passed through a classical checker (manual Step 2.5): (i) split it into vertex codewords; (ii) reject if any vertex carries a flag; (iii) reject if the two ends of any link disagree about the flux on that link (*link consistency*, the check Gauss's law implies); (iv) read the label; (v) reject if the baryon number is not the target sector's; (vi) look the label up in the basis. A string that survives is *accepted*. Gate E2 verified that encode-then-decode returns every one of the 82 (2x2) and 1 727 (2x3) states, and the **random acceptance** $a$: the fraction of uniformly random bit strings that the decoder accepts. At 2x2 this is exactly $a_{B=0}=38/4096=0.00927734375$ and $a_{B=1}=20/4096=0.0048828125$ (exhaustive over all 4096 strings, `validation/E2.json`, `validation/H0P.json`), at 2x3 it is $0.146\,\%$ ($1727/2^{20}$, `validation/E2.json`). Because $a$ is not zero, noise that happens to land on a valid-looking string is silently accepted; this single fact drives much of Sections 6 and 13.

### 2.6 Krylov time evolution and the "coarse step"

**Krylov idea.** Starting from a simple **reference configuration** $|b_0\rangle$ (e.g. the Dirac-sea vacuum: odd sites doubly occupied, even sites empty, no flux), apply the time-evolution operator $e^{-iH\,t}$. The states $e^{-ik\Delta t\,H}|b_0\rangle$, $k=0,1,2,\ldots$ span the *Krylov space*; they spread the reference over exactly those configurations that the Hamiltonian couples it to, which are the ones the ground state needs. A quantum computer can prepare such states naturally, and then *measure* them in the configuration basis to learn which configurations appear. That list is the support.

**Time step.** To avoid aliasing the step is $\Delta t=\pi/W$ with $W=E_{\max}-E_{\min}$ the spectral width of the sector (manual Step 1.4). Values at $g^2=4$: 0.245 (2x2, $B=0$), 0.156 (2x3, $B=0$), 0.115 (2x4, $B=0$) (`data/references.json`, table above; gate E3 verified $\Delta t$ per sector).

**Coarse step.** Rather than approximating $e^{-iHt}$ by many small Trotter steps (which makes circuits deep), the project uses *one* product of exact term evolutions per circuit,
$$
|\psi_{r,k}\rangle=\prod_{\gamma}e^{-iH_\gamma\,k\Delta t}\,|r\rangle,\qquad k=1,\dots,4,
$$
where $H=\sum_\gamma H_\gamma$ splits into the term groups $\gamma$ (diagonal part, each hopping link, each plaquette) and $r$ is a reference configuration. This is the "coarse step of order $k$" (manual Step 4.3, family (b)). The state is then *not* the exact Krylov state, but it is gauge invariant by construction (each factor is an exact unitary on the Gauss-law-obeying codewords) and covers more of the support at a quarter of the depth (manual: 62 vs 41 of 86 configurations at 2x3).

**Circuit family sizes.** One circuit per (reference, $k$) pair. 2x2: 5 references in $B=0$ (the Dirac sea plus four one-meson configurations) and 2 in $B=1$ (the diquark on either even site), times $k=1..4$: 28 circuits. 2x3: 8 references in $B=0$ and 3 in $B=1$, times 4: 32 + 12 = 44 circuits (`validation/S2D.json`; `data/quantinuum/devices_20261002.json -> counts.2x3.per_circuit`: 32 circuits labelled `B0_ref...`, 12 labelled `B1_ref...`). Term groups: 2x2 has 6 (diagonal, 4 hoppings `hop0..hop3`, 1 plaquette `plaq0`), 2x3 has 10 (diagonal, 7 hoppings, 2 plaquettes `plaq0, plaq1`), 2x4 has 14 (`validation/S2_2x4.json`, prompts/22).

**Exact circuits ("structured gates").** Gate S2 compiled every term to basic gates *exactly* (no approximation of the term unitary): hopping blocks are bipartite, so $e^{-i\theta h}$ is built from Givens-rotation chains; verified to $1.87\times10^{-14}$ against the reference (`validation/S2.json`, criterion "max |structured circuit - reference|"), leakage out of the codeword space $4.5\times10^{-14}$ (<$10^{-9}$ required). Gate counts per coarse step: 2x2 256 CZ all-to-all, 618 routed on a heavy-hex device; 2x3 2 164 CZ all-to-all (2 158 RZZ gates in the RZZ basis), 5 477 routed; 2x4 69 688 CZ all-to-all (`validation/S2.json`, `validation/S2_2x4.json`; Appendix block (j)).

### 2.7 SKQD: sample, build the subspace, Ritz energy, certificates

**SKQD** = *sample-based Krylov quantum diagonalization* (Yu et al. arXiv:2501.09702; Rosanowski et al. arXiv:2510.26951; Robledo-Moreno et al. arXiv:2405.05068). The recipe in the manual (Steps 4-5):

1. **Sample.** Run each coarse-step circuit on the device many times, measuring all qubits in the configuration basis.
2. **Decode** each shot; the union of accepted configurations over all circuits of a sector (always including the references) is the **support** $B$. (The project uses $B$ both for baryon number and, in "$|B|$", for the support; context makes it clear. The project's own labels for two versions of the support are **$B_{\rm all}$** = every accepted state of the sector, and **$B_{\rm sig}$** = "signal support" = only states whose counts exceed the uniform-noise expectation $\mu_s=Na/\dim$ at the one-sided $3\sigma$ Poisson level, with $N$ the shots of that sector; both defined in `prompts/24`, decision P9.)
3. **Project.** Build $H_B=P_BHP_B$, the Hamiltonian restricted to the span of $B$, with the *exact* matrix elements from the classical builder (the quantum device only chooses $B$, it never supplies matrix elements). Diagonalize it: the lowest eigenvalue is the **Ritz energy** $E_R$ ("Ritz" is the name for a variational estimate from a subspace). **Variational bound:** $E_R\ge E_0$ for any $B$; with $\varepsilon_B=\|(1-P_B)\Omega\|^2$ the weight of the ground state outside $B$,
$$
0\le E_R-E_0\le\frac{\varepsilon_B\,(E_{\max}-E_0)}{1-\varepsilon_B}\quad\text{(manual eq. (6))}.
$$
4. **Certify.** Apply the exact $H$ to the Ritz vector $\psi_R$ and form the **Hamiltonian residual** $r_H=\|(H-E_R)\psi_R\|$ (manual eq. (7)). Two rigorous facts hold for any $B$: $E_R\ge E_0$, and (**Weinstein**) *some* exact eigenvalue lies in $[E_R-r_H,\,E_R+r_H]$. To turn this into an interval for $E_0$ one needs a *gap assumption* (that the exact level nearest to $E_R$ is the ground state, guaranteed if $r_H<E_1-E_R$ with $E_1$ the first excited exact level). Then:
$$
\textbf{Weinstein:}\ E_0\in[E_R-r_H,\,E_R];\qquad
\textbf{Kato--Temple:}\ E_0\ge E_R-\frac{r_H^2}{\alpha-E_R}\ \ \text{with } \alpha\le E_1,\ \alpha>E_R .
$$
The project uses the second Ritz value as $\alpha$ (an upper bound on $E_1$, not a lower bound), so both intervals are labelled **gap-assumed**. A near-degenerate cluster (as in $B=1$) is certified as a whole. Differences such as $M_B$ are reported by interval arithmetic.

**Which certificate reads which width at 2x3 (owner decision 2026-10-05, `data/owner_decision_20261005_kt_certificate.md`, verbatim "keep Kato-Temple for B=0, go ahead").** The manual's gate H1 asks for a certified interval of width $\le0.1$ at $B=0$, gate H2 for $\pm r_H\le0.15$ at $B=1$. At 2x3 the project reads H1 on the **Kato-Temple** interval with $\alpha=E_1$ taken as the *exactly known* first excited level (available classically at 2x3, not on lattices beyond exact diagonalisation; this is the owner's recorded caveat), width $\delta_{\rm KT}=r_H^2/(E_1-E_R)\le0.1$ (rigorous whenever $E_R<E_1$), and H2 on **Weinstein**, because the $B=1$ cluster gap ($E_1-E_0=0.0244$, `data.oracle_width.B=1.E1` minus $E_0$ in `validation/CV_2x3_plan.json`; my subtraction) makes Kato-Temple uninformative there. The reason is quantitative: even the oracle support that holds 99.9 % of the ground-state weight has Weinstein width $r_H=0.265$ at $B=0$ (Appendix block (r)), and a Weinstein width $\le0.1$ would need a captured weight $W\ge0.9999$ (planner arithmetic, `prompts/31` D1).
5. **Support quality.** *Recall* of the exact support: $R_\varepsilon=|B\cap S_\varepsilon|/|S_\varepsilon|$; the count of *false positives* (accepted states carrying exact weight $<10^{-8}$); the *yield* (accepted shots over shots); and the error $E_R-E_0$.

**What is rigorous and what is heuristic** (manual Step 4.1): the energy bound and the intervals are rigorous for any $B$. The claim that the device finds a good $B$ is heuristic on real hardware, because the SKQD convergence theorem assumes exact Krylov states and a sparse ground state, neither of which a noisy coarse-step circuit satisfies.

### 2.8 Classical controls

Because the diagonalization is variational for any $B$, the only quantum content is *which* $B$ is chosen. The manual (Step 6) therefore preregisters classical supports of equal size $|B|$: **CIPSI** (selected configuration interaction: grow $B$ by repeatedly adding the Hamiltonian-neighbour configurations with the largest score $|\langle c|H|\psi_R\rangle|^2/(H_{cc}-E_R)$), **BFS** (breadth-first neighbour growth, truncated), **random** configurations, the **oracle** (top-$|B|$ by exact weight, simulator only), **ML-alone**, and device-seeded CIPSI. The manual's emulation (Table 3) and gate S1 find that CIPSI tracks the oracle at 2x3 and beats the device proxy at equal $|B|$: at $|B|=160$ the errors are $1.2\times10^{-3}$ (CIPSI) and $1.2\times10^{-3}$ (oracle) against $8.6\times10^{-3}$ for the device proxy at $f=0.1$. The plan therefore does **not** expect a device advantage; the primary endpoint P1 is a "characterized null" (manual Step 6.3). Gate S1's controls rows, from `validation/S1.json`: CIPSI vs oracle at $|B|=160$ is $1.2\times10^{-3}$ vs $1.2\times10^{-3}$ ($B=0$) and $1.0\times10^{-3}$ vs $9.8\times10^{-4}$ ($B=1$); at $|B|=320$, $6.5\times10^{-5}$ vs $6.7\times10^{-5}$ and $6.7\times10^{-6}$ vs $6.5\times10^{-6}$.

### 2.9 The neural / ML step

The manual's Step 7 specifies a *gauge-invariant neural importance model* $f_\theta(b;\lambda)\approx\log|\langle b|\Omega_\lambda\rangle|$ (a message-passing network on the lattice graph, conditioned on $\lambda=(g^2,m,B,L_x,\text{static placement})$, trained with a pairwise ranking loss, eq. (8), and *leakage-safe* splits: test points never in training), for four uses: recovery of flagged bit strings (eq. (9)), size-constrained extension of $B$, ML-alone support proposal, and transfer from small to large lattices. The learned model is classical, so the project is "ML-assisted quantum simulation", not quantum machine learning.

**What actually exists in the package (important).** Only the manual's Step 7.4 *minimal model*: `src/skqd/ml.py` holds hand-built features (16 gauge-invariant numbers such as numbers of flux links by direction, quarks on even sites, holes on odd sites, $\sum\iota$, the diagonal energy relative to the Dirac sea), `design`, `RidgeRanker` (a ridge regression, i.e. linear regression with an $L_2$ penalty) and `spearman` (Spearman rank correlation). It is trained leakage-safely and scored **only in gate S1 on exact 2x3 and 2x4 amplitudes**: Spearman $0.862$ ($B=0$) and $0.888$ ($B=1$) at 2x3, $0.763$ on the 2x4 transfer (`validation/S1.json -> data.ml_spearman|B=0`, `data.ml_spearman|B=1`, `data.2x4_ml_spearman`; the manual's own numbers are 0.85 / 0.89). No graph network is implemented, no recovery routine (eq. (9)) exists in `src/skqd/`, and **no learned model has ever touched hardware data** (`reports/H0_2x2_full_hardware_report_20261002.md`, plan rows 7.1-7.5). "Neural-enhanced" is therefore, as of today, a plan rather than a result.

### 2.10 Noise, the clean fraction, and the statistics of the hardware runs

A real quantum computer makes errors. For this project the key concepts are (all defined in the manual Step 4.4 and Step 8 and refined by later amendments):

- **Clean fraction $f$** ("fidelity proxy"): the probability that a single shot of a circuit carries *no error at all*. The manual's model is $f\simeq(1-\epsilon)^{N_{CZ}}$ for per-CZ error $\epsilon$ and $N_{CZ}$ CZ gates, times a readout factor 0.82 for 12-20 qubits at 1 % readout error each. The **signed budget** (amendment 01 item 2): mean $f\ge0.1$ over the circuit family and worst circuit $f\ge0.05$, read on the *scheduled* circuit (the circuit as it is actually timed on the device).
- **Idle-time error.** A qubit that waits while others are gated decoheres (loses its phase, "dephasing", time constant $T_2$; loses energy, time constant $T_1$). Including it: $f=f_{\rm gates}\,e^{-S_{\rm idle}}$ with $S_{\rm idle}=S_{T_1}+S_{T_2}$ the idle-window relaxation budget in nats (`src/skqd/idle.py`). $T_2^{\rm echo}$ is the dephasing time measured with one refocusing pulse (the number in IBM's calibration records); $T_2^*$ is the dephasing time of free evolution (what an idle qubit in a circuit actually feels). The project found $T_2^*/T_2^{\rm echo}\approx0.17$ on its devices (Section 6).
- **Yield model** (manual Step 4.4, amended by rule M4.4): accepted fraction $y=0.82f+(1-f)a+(\text{near-clean term})$, where $a$ is the random acceptance of 2.5 and the *near-clean* term counts shots with a few errors that still decode as valid (the project's own concept). Consequence: the accepted-shot count overstates the clean fraction (by a factor 15 on `ibm_fez`, Section 6).
- **Clean-fraction estimators** (all the project's own labels): $f_{\rm hit}$, the *reference-string hit fraction*: (count of the circuit's most probable ideal output string minus the accidental hits expected from uniform noise) divided by (shots $\times$ the ideal probability of that string $\times$ 0.82). The **mixture estimator** fits one weight separating the ideal distribution from uniform noise over all accepted strings. $f_0$ (or $f_0'$): the *fault-free fraction* (no gate fault at all). $f_{\rm ideal}$: the *ideal-sample fraction*, shots that sample the ideal output distribution exactly (fault-free shots plus shots whose faults are *benign*, e.g. a phase error that does not change the measured string); $f_{\rm hit}$ turns out to estimate $f_{\rm ideal}$, not $f_0$; their ratio $r_{nc}=f_{\rm hit}/f_{\rm ideal}$ is the *near-clean correction* (Section 6.17: $r_{nc}=1.115$).
- **Saturation (project rule C22).** At 2x2, once $Na/\dim\gtrsim5$ (with $N$ the shots in a sector), every sector state is hit about five or more times by accidentally valid noise alone, so $B_{\rm all}$ is the whole sector whether or not the processor worked. The full 2x2 hardware run has $Na/\dim=16.97$ ($B=0$) and $15.72$ ($B=1$) (`validation/H0_2x2.json -> data.C22`). Therefore the energy from the whole accepted support is not a device result; the signal support $B_{\rm sig}$ and the controls are.
- **Shot rule** (manual eq. (5)): shots per circuit $S\ge\lambda^*/(0.82\,f\,p)$, where $p$ is the ideal probability of a configuration and $\lambda^*=6.295794$ is the Poisson mean that gives three expected observations with 95 % probability (`skqd.skqd.poisson_lambda_star(3,0.95)`). The project's rule **D3'** (2x2 sizing: every sector state must reach $\lambda^*$ expected clean counts from the $k=4$ circuits at $0.7f$) and the 2x3 replacement **D3'-R** are described in Section 6.

### 2.11 Summary table of the three lattices

| item | 2x2 | 2x3 | 2x4 |
|---|---|---|---|
| sites / links / plaquettes (lattice geometry) | 4 / 4 / 1 | 6 / 7 / 2 | 8 / 10 / 3 |
| qubits | 12 | 20 | 28 |
| physical states | 82 | 1 727 | 37 165 |
| sector dimensions $B=0$ / $B=1$ | 38 / 20 | 677 / 426 | 12 843 / 8 934 |
| exact $E_0$ at $g^2=4$, $B=0$ / $B=1$ | $-3.6407665507$ / $-1.8615880345$ | $-5.6026004579$ / $-3.8260844431$ | $-7.5652140739$ / $-5.7801629009$ |
| $\Delta t$ at $g^2=4$, $B=0$ / $B=1$ | 0.24501 / 0.33194 | 0.15644 / 0.18697 | 0.11470 / 0.13031 |
| 99.9 % support $B=0$ / $B=1$ | 16 / 13 | 86 / 95 | 305 / 470 |
| random acceptance $a$ | 0.00928 ($B=0$), 0.00488 ($B=1$) | 0.00146 (any sector, upper bound) | not tabulated in the sources read |
| exact coarse step, CZ all-to-all / routed heavy-hex | 256 / 618 | 2 164 / 5 477 | 69 688 / 148 726 |
| role in the plan | decoder / yield calibration only (manual Step 0, 9.1) | the SKQD test (H1, H2, P1) | simulator-only transfer test; hardware only if 2x3 passes |

Sources: `data/references.json`, `validation/E2.json`, `validation/S2.json`, `validation/S2_2x4.json`, `validation/K0_2x3_2x4.json -> data.2x4` (148 726 routed on the FakeFez map), manual Step 0.

### 2.12 The clean-fraction statistics in one place (added 2026-10-13)

Four numbers are all called a "clean fraction" in this project. They are different quantities, and mixing them has caused three of the project's corrections. In order from the strictest to the most generous:

| symbol | project label? | what it is | how obtained |
|---|---|---|---|
| $f_0$ (or $f_0'$) | yes | the probability that **no gate, readout or idle fault at all** happens in a shot (for a depolarizing model with parameters $p_2,p_1$ and readout survival $s_{ro}$: $f_0=(1-\tfrac{15}{16}p_2)^{n_{2q}}(1-\tfrac34p_1)^{n_{1q}}\,s_{ro}$ in the convention of Qiskit Aer's `depolarizing_error(p,n)`, $\mathcal E(\rho)=(1-p)\rho+p\,I/2^n$; $f_0'$ additionally requires the reference string to be read correctly) | analytic from the model; never measurable on hardware |
| $f_{\rm ideal}(\delta)$ | yes | the **ideal-sample fraction**: shots whose output string is drawn from the ideal distribution to within total-variation distance $\delta$ (default $10^{-3}$); equals $f_0'+(1-f_0')\,b(\delta)$ with $b$ the fraction of faulty trajectories that are *benign* (e.g. a phase error that does not change the measured string) | Pauli-trajectory decomposition (gate CF_traj, class-4 token C4_CF); a simulation quantity |
| $f_{\rm hit}$ | yes | the **reference-string hit fraction**: $\big(n_{\rm ref}-N a/\dim\big)\big/\big(N\,p_{\rm ref}\,s_{ro}\big)$ with $n_{\rm ref}$ the count of the circuit's most probable ideal string, $N a/\dim$ the accidental hits expected from uniform noise, $p_{\rm ref}$ its ideal probability and $s_{ro}$ the readout factor (0.82 in the manual's 20-qubit convention) | directly from counts; the only one a device gives |
| $\hat f_{\rm ideal}$ | yes | the device estimator of $f_{\rm ideal}$: $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ | $f_{\rm hit}$ from counts, $r_{nc}$ from the trajectory simulation |

and the **near-clean correction** $r(\delta)=f_{\rm hit}/f_{\rm ideal}(\delta)$, with $r_{nc}$ its upper 95 % bound pooled over the $k=1$ arms. The project's signed bar (mean $f\ge0.1$, worst $\ge0.05$ over the circuit family, amendment 01 item 2; owner decision 1a of 2026-10-05) is read on $\hat f_{\rm ideal}$. The relationships measured in simulation on the 2x3 $k=1$ circuits (`validation/C4_FCELLS_A.json -> data.cells['E1|NAT-O0']`, E1 = the H2-2 published rates): $f_0=0.17223$, $f_{\rm hit}=0.2312$ [0.2072, 0.2572], $\hat f_{\rm ideal}=0.2074$ [0.1858, 0.2307]; that is $f_{\rm hit}/f_0=1.34$ [MINE]: more than a third of the reference hits come from shots that had a fault but returned to the reference (benign or near-clean faults). In an idle-dephasing model the relation reverses: `validation/CF_traj.json` (A5) found $r=0.674$ and $0.902$ at the two ends of the $T_2$ bracket, i.e. $f_{\rm hit}$ *under*-estimates $f_{\rm ideal}$. **Convention caution** [MINE]: the device table of Section 7 and `data/quantinuum/devices_20261002.json` treat the published two-qubit error $\epsilon_2=8.3\times10^{-4}$ as the full fault probability per gate and give $f_{\rm gate}=0.1502$ for the 2x3 family; the campaign-33 scenarios feed the same number to Aer as $p_2$, whose fault probability is $\tfrac{15}{16}p_2$, and give $f_0=0.1722$ (same circuits, same number). The two differ by a factor $1.147$ [MINE: 0.17223/0.15016]. Which convention matches a real Quantinuum device is not established by any file.

## 3. The intended plan

Source: `proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md` (Steps 0-11, Appendix A), `validation/gates.md`, `prompts/08_month_plan_and_reporting.md`, `proposal/amendment_01_devices_and_budgets.md`.

### 3.1 What the project set out to do

**Title of the manual:** "Neural-enhanced sample-based Krylov diagonalization for SU(2) with dynamical quarks in 2+1D" (SU2QC Project 2, revision 2, corrected specification of 10 Sept 2026, prepared for D. Digonto). The first version of the plan was reviewed by two referees ("Claude" and "Codex") who both rebuilt the 2x2 Hamiltonian and reproduced every number but found the same problems beyond 2x2: non-unique labels (fixed by adding the intertwiner label), a 2x2 hardware run that cannot test SKQD because its sectors saturate (re-scoped as a calibration), a missing classical control (added: CIPSI, BFS, random, oracle), an optimistic noise model, a one-sided variational bound (replaced by two-sided certified intervals), and an under-specified ML model. The revised manual concludes that, at these small sizes, a classical selected-CI support of equal size is at least as good as the device-generated support; so the experiment is specified as a **workflow validation with certified spectra and a measured device-support quality, not as an advantage demonstration**.

**Roles of the three lattices (manual Step 0).**
- 2x2 (12 qubits, 82 states): *pipeline calibration only* (decoder validity, yield versus circuit depth, readout confusion, sector filter); not an accuracy test, because any run of about $10^3$ shots saturates its sectors (38 and 20 states).
- 2x3 (20 qubits, 1 727 states, sectors 677 and 426): *the SKQD test*, with exact references from the Step-3 builder.
- 2x4 (28 qubits, 37 165 states): simulator-only transfer and scaling test with exact Lanczos references; hardware only if the 2x3 gates pass with margin.

**Claims if all gates pass (manual Step 0):** (i) first quantum-centric spectroscopy of a non-Abelian gauge theory with dynamical matter in two spatial dimensions (vacuum energy, diquark-baryon cluster, meson-like gap, static potential $V(1),V(2)$ on 2x3, with two-sided certified intervals); (ii) a validated Gauss-law-aware pipeline; (iii) a measured curve of device-support quality (recall, false positives) versus circuit depth and shots with the classical controls at equal $|B|$. **Not claimed:** quantum advantage; the continuum limit; string breaking.

### 3.2 The ten steps of the manual

| step | content | gate(s) |
|---|---|---|
| 1 | Hamiltonian, sectors, symmetries, exact references; $\Delta t=\pi/W$ per sector | E1, E3 |
| 2 | gauge-invariant basis with intertwiner labels; codewords; decoder | E2 |
| 3 | dressed-site Hamiltonian builder, validated against the projector construction | E1 |
| 4 | support generation on the QPU: reference sets, coarse circuits (family b: exact coarse steps $k=1..4$; family a: Trotterized ablation), $\le250$ CZ per step at 2x2 and $\le500$ at 2x3, fidelity/yield model, shot rule eq. (5) | S2, S3 |
| 5 | HPC post-processing: projected diagonalization, residual $r_H$, Weinstein and Kato-Temple intervals, support metrics | S1, H1, H2 |
| 6 | classical controls (CIPSI, BFS, random, oracle, ML-alone, device-seeded CIPSI) and the primary endpoint P1 | S1, P1 |
| 7 | gauge-invariant neural importance model; leakage-safe splits; four uses; the "seven protocols" comparison | M1 |
| 8 | noise simulation before hardware (the Step 8.2 proxy; transpiled device-model simulation; gate S3 recall $\ge0.9$) | S3 |
| 9 | hardware: 9.1 the 2x2 calibration run; 9.2 the 2x3 production (4 sectors: $B=0$, $B=1$, static $r=1$, static $r=2$; 32-44 circuits per sector; $2\times10^5$ shots per sector; two calibration windows); 9.3 optional 2x4 | H0, H1, H2 |
| 10 | analysis, gates, error budget, reporting (raw bit strings, calibration snapshots, circuits and decoder released) | all |
| 11 | six-week timeline and Plan B | -- |

### 3.3 The manual's gate table (Step 10) and its endpoints

| gate | check | criterion in the manual | manual's expected timing |
|---|---|---|---|
| E1 | $[G_a(x),H]=0$; 82-dim kernel; sector split; two builders agree to $10^{-12}$ | done ($8\times10^{-15}$) | done |
| E2 | counts of Table 2; codec round trip on all 2x3 states; random-bitstring acceptance $\approx0.15\,\%$ | done | done |
| E3 | 2x3 and 2x4 references (Table 1); static sectors; $\Delta t=\pi/W$ per sector | done | done |
| S1 | emulated support recall $\ge0.9$ at $f\ge0.1$ with the production budget; controls table | done (Tables 3, 4) | done |
| S2 | routed CZ per coarse step $\le500$ on the target map; noiseless compiled circuits leak-free | -- | week 2 |
| S3 | Aer device-model recall $\ge0.9$ for the production set; shot budget fixed | -- | week 2 |
| H0 | 2x2: decoder validity, bit order, parity checks; **measured $f$ within 30 % of the model** | -- | week 3 |
| H1 | 2x3 $B=0$: certified interval $I_0$ of width $\le0.1$ containing the exact $E_0$; recall $\ge0.8$ | -- | week 4 |
| H2 | 2x3 $B=1$: cluster energy certified to $\pm r_H\le0.15$; $V(1),V(2)$ intervals containing the exact values | -- | week 4 |
| P1 | **primary endpoint**: curves $E_R-E_0$ and $R_{10^{-3}}$ versus $\lvert B\rvert $ for device and CIPSI at equal $\lvert B\rvert $, bootstrap bands; "advantage" declared only if the device curve lies below CIPSI everywhere with non-overlapping bands | -- | week 5 |
| M1 | ML uses credited only under Step 7.5 (must beat the baseline at equal $\lvert B\rvert $ on 2x3 hardware data and on held-out couplings) | -- | week 5 |

**Primary endpoint P1** (manual Step 6.3): the pair of curves $E_R-E_0$ and $R_{10^{-3}}$ versus $|B|$, device versus CIPSI at equal $|B|$, on 2x3 hardware data. The manual's own expectation is a characterized null (device between BFS and CIPSI) and says it is publishable as "the first measured support-quality curve for a non-Abelian theory".

**Manual timeline (Step 11):** week 1 E1-E3, S1; week 2 S2, S3; week 3 H0 (2x2 hardware, plus a 2x3 pilot of $10^4$ shots per circuit); week 4 H1, H2 (2x3 production, four sectors, two calibration windows); week 5 P1, M1, 2x4 transfer on the simulator; week 6 research note and release bundle. **Plan B:** if S3 fails reduce to $k=1,2$ and raise shots; if H1 fails use the union support of device + CIPSI and report the hardware as the measured support-quality curve alone.

### 3.4 Amendments and decisions that changed the plan (in order)

| date | document | what it changed |
|---|---|---|
| 2026-09-15 | `prompts/11` (planner decision), owner decision | the CZ-count budget cannot be met in this encoding (S2 FAIL on cost only); measure the cost floor first |
| 2026-09-16 | `prompts/12`; `proposal/amendment_01_devices_and_budgets.md` (draft) | combined plan: 2x2 on a Heron-class IBM device, 2x3 exact circuits on an all-to-all ion-trap device; replace the gate-count budget by the device-resolved budget "mean $f\ge0.1$, worst $\ge0.05$" (gate S2D) |
| 2026-09-23 | amendment 01 items 1-3 **signed** | item 1: the 2x2 patch is chosen by the idle-aware objective; item 2: $f$ is read on the *scheduled* circuit (thresholds 0.1 / 0.05 unchanged); item 3: the exact family is kept and judged on duration. Items 4 (the 2x3 device) and 5 (the shot quota) **remain open** |
| 2026-09-30 | `data/H0_replan_owner_decisions.md` | nine owner decisions D8', D1', D3'-f, D3''-H0, D5', C2', C3', H0P-Y', M4.4 (all approved), see Section 6.11 |
| 2026-10-02 | `data/owner_decision_20261002_run_below_signed_budget.md` | run the full 2x2 SKQD on `ibm_kingston` using the 600 s budget even if the signed budget is not met |
| 2026-10-05 | `data/owner_decision_20261005_partB.md`, `data/owner_decision_20261005_k1_2x3_fpilot.md` | decisions 1a (the signed bar refers to $f_{\rm ideal}$, read as $\hat f_{\rm ideal}=f_{\rm hit}/1.115$), 2a (rule D3'-R signed as the minimum 2x3 sizing, **condition:** any campaign also needs energy convergence and weighted coverage on the emulated plan; signing commits no HQC), 3a (the 2x2 "signed bar GO" is cited with the AMBIGUOUS qualification) on `prompts/29` Part B'; and ONE K1 pilot on `ibm_kingston` (cap 300 s) |
| 2026-10-05 | `data/owner_decision_20261005_kt_certificate.md` (`prompts/31` ruling 2) | verbatim "keep Kato-Temple for B=0, go ahead": the $B=0$ width criterion of H1 / CV2 is read on the Kato-Temple interval with the exact $E_1$; $B=1$ stays on Weinstein |
| 2026-10-05 | `data/owner_decision_20261005_b1_x2_plan.md` | verbatim "approve the 2x shot plan for sector B=1": the plan of record is D3'-R with $B=0$ at $s=1$ and $B=1$ at $s=2$ ($s=1.5$ fails CV2), 1 279 660 / 665 605 / 471 801 HQC at $f=0.05/0.10/0.15$; approves the plan only, commits no HQC, and the plan is re-sized at the measured $\hat f_{\rm ideal}$ before any campaign submission |
| 2026-10-06 | `data/owner_decision_20261006_A_then_B.md` (`prompts/32`) | verbatim "do A first, then ... do B": A = record 2x3 on IBM Heron as NO-GO on the K0 analysis (a model verdict) and spend the IBM seconds first on the 2x2 XY4 replication plus the context-aware-DD test (gate `H0_ddrep`, about 32 s planned); B = the K1 2x3 pilot as built, as a measured upper limit, when `ibm_kingston` publishes CZ calibration again, with a STOP to the owner if the seconds left do not cover K1's estimate $\times1.3$ |
| 2026-10-06 | owner request, verbatim in `reports/2x3_four_class_campaign_plan_20261006.md` section 1 (`prompts/33`) | "2x3 runs on qiskit [1] without any noise error or optimization, [2] with ibm noise, [3] with quantinuum based simulators, no error or optimization, [4] with quantinuum based simulators with varied errors and optimizations ... If any of this runs are already done, redo them and calculate the difference ... All of this runs can be done on perlmutter, give me what to add where first so that all these runs can be simultaneously parallely submitted": the 33-token four-class campaign (Section 7); 0 QPU s, 0 HQC |
| 2026-10-07 | owner request, verbatim in `reports/encodings_candidate_list_20261007.md` (`prompts/34`) | "how many encodings have you tried with? make planner a list of encoding such as spin-network encoding and others, test if that shortens the required number of qubits and gate and depth numbers": 13 candidate encodings listed, gate `ENC_compare` (Section 6.24) |
| 2026-10-07 to 2026-10-11 | planner rulings `prompts/33a`, `33b` | re-ruling after the first Perlmutter wave (missing `threadpoolctl`; C2_CAL ladder; Kraus versus Pauli-twirled thermal relaxation; scenario-aware class-4 sizing; slot re-use; which jobs can run before the 2026-10-21 maintenance); no tolerance, bar or convention changed |
| 2026-10-13 | owner question, quoted in `prompts/35`: "I need all the circuits tested for quantinuum devices. has this been done?" | answer: 2x3 yes in four of six tiers; 2x2 and 2x4 no; `prompts/35` plans the rest at 0 HQC (Section 9); the owner paused the executor mid-run for a laptop meeting |
| 2026-10-13 | planner ruling `prompts/33c` | the C2_CAL 54 sigma is the circuit variant not the channel (T0 versus T3), the RM arm is a bug until proven otherwise, C4_CF accepted as recorded, **$r_{nc}$ stays 1.115 pending an owner decision** (Section 8, Section 15 item 1) |
| 2026-10-13 | planner ruling `prompts/33d` (after the `c33c` executor's CPU diagnostics, `data/campaign33/c33c_diag/summary.json`) | **33c R1/R2 withdrawn**: the suspect is Aer 0.15.1's GPU (cuStateVec) Kraus path, not the RM arm; production for class 2 is to be RM on the GPU *conditional on* the new token `C2_KCHK`; C2_CAL run 3's "production = Kraus" decision does not stand; nothing harvested from classes 1, 3, 4 or C4_CF is affected (Kraus instructions exist only in the class-2 Kraus arms; audit `data/campaign33/kraus_audit.json`) (Section 8) |
| 2026-10-13 | planner rulings `prompts/35a` (after the `q35` executor's three findings) | R1: the Q2 criterion is "equal to the family's $k=1$ value" (the coarse step is $k$-independent); R2: pytket's angle canonicalisation, the rigorous state bound $B$ and Q1L restated; R3: the 2x2 tier-3 plan cut to f-cells on all 28 x 11 scenarios plus plan-of-record runs for E1, E3, E4, E5b only (cap 10 h); R4: 2x4 built at pytket level 0 only; R5: Selene sized on the measured rate (Section 9) |
| 2026-10-13 | planner ruling `prompts/35b` (on the binding STOP at Q0P_2x4) | the $10^{-10}$ exactness bar stays and is **measured on the GPU** (slot `QV_2x4_01`); Q1L is the conversion proof only; Q0P_2x4 is FAIL by construction until then; a second 2x4 source (the structured IR, no qiskit opt-3) is built; the frozen source is chosen by measurement (Section 9) |
| 2026-10-14/15 | coordinator requests (no planner prompt) | requests `C4_F1_B1`, `C4_PART_10`, `C4_F7_B1`, `C4_PART_11` (commit `6c3e684`), `C2_KCHK`, `C4_F8_B0b`, `C4_PART_08`, `C4_F8_B1b`, `C4_PART_09` (`f4c71e8`), `C4_F2_B0`, `C4_F2_B1`, `C4_PART_12..17` (`34f73a7`); committed directly instead of through `scripts/ci_request.sh` (Section 13.8) |
| 2026-10-15 | planner ruling `prompts/33e` (after `C2_KCHK` FAIL 7/10; committed `10f88a0` at 17:41 UTC) | R1: the CPU arm got **one** CPU because `jobs/gate.sbatch` runs `srun` without `--cpus-per-task`; one-line fix in the repo and a new `run.cpu_affinity` check; R2: `C2_KCHK` run 2 runs the CPU arms only, the GPU arms of run 1 are kept as evidence of record; R3: the laptop's CPU Kraus/RM reference is to be extended to $\ge64$ shots each (new criterion K4: the two CPU references agree); R4: class 2 after the maintenance except `C2_XY4`, which is requested as soon as run 2 reads `production_representation: rm`; R5: the three GPU Kraus executions disagree with each other (evidence of an Aer GPU Kraus defect independent of any CPU reference) (Section 8) |

### 3.5 What the manual asked for that has not been done

The manual's steps that need 2x3 hardware (Step 9.2, H1, H2, P1, M1, the seven-protocol table) and the neural step on hardware data are all **open** as of 2026-10-15 (the only 2x3 hardware data are the K1 pilot's null counts, Section 6.22; the 2x3 *simulation* picture is Section 7, now with 25 returned class-4 run files); the status of each of the 51 plan rows is in Section 17. No owner decision was recorded in a file between 2026-10-13 and 2026-10-15 (I searched `data/owner_decision_*` and `prompts/LOG.md`; the newest owner-decision file is `data/owner_decision_20261006_A_then_B.md`).

## 4. The package layout

Source: `CLAUDE.md`, `README.md`, `RUNBOOK.md`, `SKQD-CI-SETUP.md`, `prompts/ROUTING.md`, `.claude/agents/*.md`, directory listings and `wc -l` made on 2026-10-15 (updated from the 2026-10-13 report), and `graphify`. The package is a Python code base: `src/skqd/` has 28 Python files and **6 815** lines by `wc -l` (6 357 on 2026-10-13, 6 132 on 2026-10-06), plus the sub-package `src/skqd/campaign33/` (**11 modules plus `__init__.py`, 5 410 lines**; 10 modules and 4 671 lines on 2026-10-13: the new module is `kchk_cpu.py`, the separate CPU process of token `C2_KCHK`), **87** files in `scripts/` (81 on 2026-10-13, 74 on 2026-10-06) and **48** test files in `tests/` (45 on 2026-10-13). New since 2026-10-13: `scripts/quantinuum_lattice_tests.py` (1 767 lines, the driver of the Quantinuum tiers T2-T6 for every lattice), `scripts/c33c_diag_full.py`, `c33c_diag_oneq.py`, `c33c_diag_delays.py` (the class-2 CPU diagnostics of `prompts/33c`), `scripts/campaign33_kraus_audit.py` (`prompts/33d` R2), `scripts/run_venv_tests_without_pytest.py`, `src/skqd/campaign33/kchk_cpu.py`, `tests/test_campaign33_cf.py`, `tests/test_campaign33_kchk.py`, `tests/test_quantinuum_lattice.py`, and the allowlist file `ci/allowed_jobs.q35` (8 lines `QV_2x4_01..08 01:00:00 1`). Code facts below are from module docstrings.

### 4.1 `src/skqd/`: the modules

**Physics core** (exact numerics, numpy/scipy only; no quantum software needed):

| module | what it does |
|---|---|
| `su2.py` | spin matrices, Clebsch-Gordan coefficients, the truncated electric-basis link operators ($j_{\max}=\tfrac12$); fixes the generator convention $L_a=-J_a^T$, $R_a=+J_a$ |
| `fermions.py` | the two-colour staggered-fermion site (Fock space, Jordan-Wigner pieces) |
| `lattice.py` | the open $2\times L_x$ ladder: site index $x_1L_y+x_2$, links, plaquettes, staggered phases $\eta$ |
| `vertex.py` | local singlet (intertwiner) tensors of one dressed vertex (manual Algorithm 1) |
| `basis.py` | the gauge-invariant configuration basis $\lvert \{j\},\{n\},\{\iota\}\rangle$ with baryon-number sectors (Step 2) |
| `hamiltonian.py` | the dressed-site Hamiltonian builder (Step 3, Algorithm 2) and the Hamiltonian-neighbour query |
| `fullspace.py` | the second, independent route: the redundant-basis "projector" construction of the 2x2 model (gate E1) |
| `exact.py` | exact sector references (Table 1): class `Model` (central object: 86 edges in the graph), sector energies, $\Delta t$, supports |
| `codec.py` | hardware codewords and the per-shot decoder (Steps 2.4 and 2.5); class `Codec` (69 edges) |

**SKQD workflow**:

| module | what it does |
|---|---|
| `krylov.py` | support-generating states emulated exactly in the gauge-invariant basis (Step 4): exact Krylov states, coarse-step states `coarse_states`, reference sets `references` |
| `noise.py` | the device-proxy noise model on bit strings (Step 8.2): clean with probability $f$, otherwise uniform garbage or Poisson-corrupted, plus readout flips; `measure_and_decode` |
| `skqd.py` | HPC post-processing (Step 5): `ritz`, `certify` (Weinstein, Kato-Temple), `support_metrics`, `exact_support`, `shot_rule`, `poisson_lambda_star`, `yield_model`, `clean_fraction_from_yield`, `reference_string_test`, `clean_fraction_mixture`, `near_clean_yield` |
| `controls.py` | classical-support controls at prescribed size (Step 6): `cipsi`, `bfs`, `random_support`, `oracle`, `top_by_count` |
| `ml.py` | the minimal gauge-invariant ridge ranker (Step 7.4) |

**Circuit layer** (translates the exact term evolutions into gates):

| module | what it does |
|---|---|
| `reference_sim.py` | numpy reference: codeword embedding into the $2^n$ space, exact block unitaries, a plain statevector simulator; qubit $k$ = bit $k$ |
| `circuits_ir.py` | backend-independent circuit description ("IR", a list of gates); class `CircuitFactory` (48 edges); `structured_term_gates` (Givens-chain / Gray-code multiplexed-rotation synthesis) with `angle_mode` exact or fixed |
| `circuits_qiskit.py` | IR to Qiskit; statevector check; transpiled CZ counts (gate S2); Aer noise sampling (`sample_many` with memory-aware chunking `shot_chunk_for`, adaptive halving on GPU out-of-memory) |
| `circuits_cudaq.py` | IR to CUDA-Q (generated kernel source, registered custom unitaries) |
| `sparse_sim.py` | exact sparse statevector simulation of IR and transpiled circuits (used for 2x4 verification) |
| `quantinuum_native.py` | IR to the Quantinuum native gate set $\{R_z,\ \mathrm{PhasedX},\ \mathrm{ZZPhase}\}$ (gate Q0P_2x3) |

**Campaign-33 sub-package `src/skqd/campaign33/`** (new, `prompts/33`-`33c`; needs no qiskit at import):

| module (lines) | what it does |
|---|---|
| `tokens.py` (146) | the 33 job tokens, their allowlist lines, conda env per token and base seed of each |
| `tokens_run.py` (1 973) | the token jobs themselves, called by `scripts/campaign33.py`: preflight, class 1-4 runs, C2 cells, the `C2_KCHK` arms, F-runs, f-cells, CV3 parts |
| `noise.py` (788) | the noise scenarios as Aer objects: E0-E8 (Quantinuum-type depolarizing, emulator parameter sets, memory dephasing, scale, matched-$f$, S3 declared) and the IBM record models I-GATE / I-ECHO / I-STAR / I-XY4 / I-COH in three representations Kraus, PTA, RM |
| `sampling.py` (351) | order-kept, budgeted Aer sampling: chunk plans, seeds, deadline bounds (`call_bound`), out-of-memory splits |
| `analysis.py` (332) | decoding, clean-fraction cells, the SKQD/CV reading on order-kept chunks (imports `scripts/gate_CV.py`, never copies it) |
| `stats.py` (268) | clean-fraction estimators with intervals, the noiseless per-state 5-sigma test, bootstrap, the comparison statistic of every "redo" |
| `circuits.py` (252) | frozen circuit families as QPY v13 (qiskit 1.4.3 on the CI, 2.5.2 on the laptop), manifests, exactness against the exact Krylov states |
| `cf_gpu.py` (324) | C4_CF: the CF_traj Pauli-trajectory decomposition redone on the GPU |
| `engines.py` (220) | C3_LE / C3_SEL: independent Quantinuum engines (pytket-pecos `H2-1LE`, Selene) in qiskit-free environments |
| `assemble.py` (641) | assembly of `validation/C33_campaign.json` and `reports/C33_campaign_report.md` from the token JSONs only; **merges the parts of split runs** (`assemble_split_runs`) and evaluates CV0-CV5 and P15 on the merged runs; **not yet run on real data** (only `validation/dryrun/C33_campaign.json` exists) |
| `kchk_cpu.py` (113) | new: the CPU arms of `C2_KCHK` (Kraus and RM, statevector on the CPU) run as a separate process next to the GPU arms (`prompts/33d` R3) |

**Device-model and hardware bookkeeping:**

| module | what it does |
|---|---|
| `idle.py` | idle-time relaxation in $f$: ASAP schedule, per-window relaxation, `f_idle_aware`; the $T_2$ convention is an argument and a recorded field |
| `coherence.py` | the coherence ($T_2$ vs gate time) a compiled circuit requires of a device |
| `device_req.py` | device-requirement algebra: `clean_shot_fraction`, `target_with_idle`; inverts the $f$ model |
| `hardware.py` | hardware-session helpers: readout confusion matrix, inverse, transpiled layout, `logical_statevector`, link-consistency checks |
| `hpc.py` | CI / Slurm / GPU telemetry helpers shared by gate scripts that may run on Perlmutter |
| `report.py` | gate-result bookkeeping: each gate script records its criteria and the numbers it computed in `validation/<GATE>.json` and writes `reports/<GATE>_*.md` from the same numbers; nothing in a report is typed by hand |

Additions of 2026-10-05, now committed: `noise.measure_and_decode_sequence` (nested shot prefixes for the convergence check; histogram-identical to `measure_and_decode`), `skqd.corrected_clean_fraction` (the $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ statistic), `skqd.h1_energy_tolerance` (the CV constant $E_{\rm tol}$), and the `h0_support_plan.py` rule D3'-R (`d3r_plan`).

`graphify god-nodes` (the code knowledge graph, `graphify-out/graph.json`, 5 519 nodes and 10 590 edges; the file is dated 2026-10-08 and has not been rebuilt since, so it does not index the code added on 2026-10-13/14; 4 266 / 8 490 on 2026-10-06; navigation aid, never evidence) lists as the most connected nodes: `Model` (105 edges), `Codec` (87), `md_table()` (59), `load_manifests()` (58), `resolve_backend()` (57), `CircuitFactory` (55), `references()` (54), `CodewordEmbedding` (48), `write_report()` (48), `stage_assemble()` (45). (On 2026-10-06 the list read `Model` 96, `Codec` 77, `load_manifests()` 58, ...).

### 4.2 `scripts/`

- **Gate scripts**, one per gate: `gate_E1.py`, `gate_E2.py`, `gate_E3.py`, `gate_S1.py`, `gate_S2.py`, `gate_S2D.py`, `gate_S2D_idle.py`, `gate_S2D_levers.py`, `gate_S2_2x4.py`, `gate_S3.py`, `gate_H0.py` (analyses any counts directory), `gate_H0P.py`, `gate_H0_diag.py`, `gate_H0_model.py`, `gate_H0_kpilot.py`, `gate_H0_ddtest.py`, `gate_H0_2x2.py`, `gate_Q0P_2x3.py` (stage A, and since 2026-10-05 the `plan28` stage = gate `Q0P_2x3_plan`), `gate_CF_traj.py`, `gate_K0_2x3_2x4.py` (K0, `--live` option), `gate_CV.py` (gates `CV_2x3_plan` and `CV_2x2_info`), `gate_H0_ddrep.py` (stages reserve / predict / prereg-md / assemble), `gate_K1_2x3_fpilot.py` (stages record / build / patchcal / predict / prereg-md / assemble / submit). The laptop gates are `laptop_L2_qiskit_check.py` ... `laptop_L5_cudaq_check.py`.
- **Runner and status:** `run_gate.py` (runs a gate script, prints the status, on FAIL writes `validation/BLOCKED.md` listing the failing criteria, with `--push` commits and pushes on PASS), `check_package.py` (prints PACKAGE OK when everything is present), `update_status.py` (regenerates `validation/gates.md` and `reports/PROJECT_STATUS.md` from the JSON), `run_tests_no_pytest.py`, `make_amendment.py` (generates amendment 01 from the JSON; `--check-only` re-verifies every cited value).
- **IBM hardware tooling:** `ibm_account.py` (checks the stored key, never prints it), `h0_backends.py` (`resolve_backend`, `calibration_record`, `calibration_fingerprint` = rule D9), `h0_submit.py` (submit / retrieve split, dry run on `AerSimulator.from_backend(FakeFez)`, preflight, per-job `session.json`), `h0_qpu_time.py` (execution-time estimate from the target's durations), `h0_support_plan.py` (rule D3'), `h0_patch_select.py` (exhaustive embedding search scored by the idle-aware $f$), `h0_calwatch.py`, `h0_idle_model.py`, `h0_t2_override.py`, `h0_build_circuits.py`, `h0_compare_prep.py`, `h0_device_survey.py`, plus circuit builders `h0_diag_circuits.py`, `h0_kpilot_circuits.py`, `h0_ddtest_circuits.py`, `h0_2x2_circuits.py`.
- **Quantinuum tooling:** `quantinuum_account.py` (login via the Nexus token store; tokens never on a command line), `quantinuum_build_circuits.py`, `quantinuum_device_table.py` (device and cost table), `quantinuum_submit.py` (dry run, job bodies with `max_cost`), `quantinuum_stack_check.py`, `q0p_a6_phase_error_check.py`. Isolated virtual environment `~/.local/share/su2qc-quantinuum/venv` so the pinned qiskit stack in the `coding` conda environment is never touched (`data/quantinuum/stack_check_20261002.json` and `_after.json` show identical pins).
- **IonQ tooling:** only `ionq_2x3_feasibility.py` (published-specification arithmetic -> `data/ionq_2x3_feasibility_20261001.json`). The submission scripts and gates `I0P_2x3`, `I0P_2x4` named in `prompts/25` Part B have no script and no validation JSON in the repository today (not built; the Quantinuum route of `prompts/26` came first).
- **New on 2026-10-05/06:** `h0_ddrep_circuits.py` (builds the seven DD cells and four pulse-train pubs of H0_ddrep from the committed H0_ddtest circuits), `h0_devicewatch.py` (free metadata poll: a device counts as ready only when its status is `active` AND it publishes CZ errors; `operational` alone is not enough), `k0_nogo_note.py` (generates `reports/K0_2x3_ibm_heron_nogo.md`), `k1_ddrep_note.py` (generates the honest-limits paragraph of the K1 report from the H0_ddrep JSON), `cf_estimator_information.py` (gate `CF_estimator_2x2_info`).
- **New on 2026-10-06 to 2026-10-13:** `campaign33.py` (the job driver run by the CI for every campaign token: preflight imports, device selection, budgeted sampling, JSON writer), `campaign33_freeze.py` (freezes the 12 circuit families as QPY v13), `campaign33_engines.py` (pre-check of the Quantinuum-side engines), `campaign33_resize.py` (sizes class-4 runs and splits them into parts from the measured f-cell rates; never by hand), `gate_ENC_compare.py` and `enc_assignment_search.py` (`prompts/34`), `ci_request.sh` / `ci_check.sh` (multi-token, per-request) and `ci/poll_concurrent.sh` (the concurrent poller; installed on Perlmutter by the owner, `ci/poll.sh` is edit-denied for agents). **Merged on `master` since 2026-10-13** (merge `7c46329`, then `e66eb26`): `--lattice {2,3,4}` and `--source {opt3,structured}` for `quantinuum_build_circuits.py` and `gate_Q0P_2x3.py`, the lattice test driver `quantinuum_lattice_tests.py` for tiers T2-T6, the GPU slots `QV_2x4_01..08` (token indices 54-61) with the decision-job part `ci/parts/QV_2x4_01.json` (Section 9).
- **Other:** `cf_traj_2x2_arm.py`, `cf_trajectories.py` (Pauli-trajectory decomposition, gate CF_traj), `s2d_2x3_device_requirements.py`, `s2d_recall_at_predicted_f.py`, `s2_duration_compare.py`, `s2_duration_report.py`, `s2_escalation_experiments.py`, `s2_fixed_recall.py`, `s3_device_model.py`, `report_circuit_structure.py`, `ionq_2x3_feasibility.py`, `ci_request.sh`, `ci_check.sh`, `ci_smoke.py`.

### 4.3 The gate system

A **gate** is a script whose result is written to `validation/<GATE>.json` with `"status": "PASS"|"FAIL"` and a list of criteria (`name`, `value`, `threshold`, `passed`), plus a generated report `reports/<GATE>_*.md`. Rule 1 of `CLAUDE.md`: "a gate passes only when its script writes status PASS, not when the prose says so"; every number in prose must come from `validation/*.json` or `data/*.json`. The 51 JSON files in `validation/` were enumerated with a short python snippet; 46 of them are gate results with a criteria list (38 on 2026-10-05), 4 are CI result files (`ci_gate_L4`, `ci_gate_S3`, `ci_gate_S2_2x4`, `ci_smoke`) and 1 is the GPU stage record `S2_2x4_gpu.json` (Section 5).

Two kinds of gate (the project's wording):
- **Validation gates** (E1-E3, S1, CS, L2, L5, ...): PASS means the code reproduces an independently known answer.
- **Measurement gates** (S2_2x4, S2D_levers, H0_kpilot, H0_ddtest, H0_2x2, Q0P_2x3, CF_traj, ...): PASS means "preregistered, measured, verified, consistent", never "the number is good". The measured number is reported as the result.

**Preregistration**: the circuits, shot counts, decision rule and prediction are written to a committed file *before* the device data exist. **Calibration fingerprint (rule D9)**: a sha256 over the calibration-record content the prediction actually reads (30 qubit and 54 edge blocks on the IBM patch); submission is allowed only when the live fingerprint equals the preregistered one, and it is recorded again at retrieval. **Dry runs** on a simulator precede every hardware submission (`H0_dryrun`, `H0_kpilot_dryrun`, `H0_ddtest_dryrun`, `H0_2x2_dryrun`, `H0_diag_dryrun`, `H0_ddrep_dryrun`, `K1_2x3_fpilot_dryrun`). **Device-readiness rule (2026-10-06):** a hardware submission waits for `scripts/h0_devicewatch.py` to report the device `active` with every CZ error published; the live `ibm_kingston` record of 2026-10-05/06 carried none (352 of 352 CZ keys without an error, status `maintenance` from about 01:12Z, `prompts/LOG.md` row 2026-10-05/06) and the first K1 attempt stopped there at 0 QPU s. **Rules that make the record honest**: preregistered records are never rewritten (a correction is a new gate); no tolerance is changed after the fact; the 30-minute rule (below); QPU spend only with the owner's explicit go.

**The 30-minute rule** (`CLAUDE.md` rule 4): on the laptop (Intel i7-8750H, 6 cores / 12 threads, 62 GiB RAM since 2026-09-30, GTX 1060 Max-Q 6 GB with no usable local GPU because CUDA-Q's `nvidia` target needs compute capability $\ge7.0$ and the GPU has 6.1, and `qiskit-aer-gpu` 0.15.1 is incompatible with qiskit 2.5.2), any run that exceeds 30 minutes must be re-parametrized (fewer shots, `--quick`, smaller sector) with the report stating what the laptop can do and what needs the RTX 3070 desktop, the Slurm GPU cluster or the QPU.

### 4.4 Agents and model routing

From `prompts/ROUTING.md` and `.claude/agents/*.md` (Claude models; names are the project's):

| agent | model / effort | job |
|---|---|---|
| `planner-fable` | Fable 5.1, `high` (raised to `max` only for a blocked gate or a hard physics decision; owner decision 2026-10-01) | writes `prompts/NN_*.md`, decides, diagnoses blocked gates, owns the numerical plans and preregistrations |
| `executor-opus` | Opus 5.5, `high` | implements the current prompt, runs the gate, appends the outcome to `prompts/LOG.md` |
| `reviewer-opus` | Opus, `medium` | independent audit of JSON vs report vs code (never re-derives the physics) |
| `runner-sonnet` | Sonnet, `low` | runs gates, tests, transpilations; never edits source |
| `scribe-haiku` | Haiku, `low` | formats reports, updates `reports/PROJECT_STATUS.md` and `validation/gates.md`; never changes numbers |

The loop: planner writes a prompt, runner executes the gate, reviewer audits, `run_gate.py --push` on PASS; on FAIL the planner is invoked with `prompts/ESCALATION_TEMPLATE.md`. `prompts/LOG.md` is the execution log (136 lines; all outcomes with commit hashes). The numbered prompts 00-32 are listed in Section 6 with their titles. The coordinator session (the main Claude session) briefs agents, never writes production code, and is the only one that commits; there is also an auto-memory and a `gate` skill (`/gate <GATE> [--push]`).

### 4.5 The Perlmutter GPU CI loop

Source: `CLAUDE.md` ("skqd-ci" section), `SKQD-CI-SETUP.md`, `ci/README.md`, `RUNBOOK.md` ("Engine and HPC policy", owner 2026-09-21).

Perlmutter (the NERSC supercomputer, account `m4135_g`) **has no login from this project** (no ssh). It pulls the repository every hour at 07 minutes UTC, reads `ci/request.txt`, and runs *at most one allowlisted job*, then pushes the result back (`ci/status.json`, `validation/ci_gate_<TOKEN>.json`, `reports/ci-<jobid>.out`). Loop: commit and push, `scripts/ci_request.sh <TOKEN>`, poll `scripts/ci_check.sh` (not more than every 15 minutes; exit 0 done, 2 pending, 3 refused), read the JSON. Tokens: `smoke E1 E2 E3 S1 L1 L2 L3 L4 L5` originally, with `S3 04:00:00 1`, `H0P 01:00:00 1` and `S2_2x4` added by the owner on the Perlmutter side. Limits (enforced there, not changeable from the repository): one job at a time, at most 6 jobs per UTC day, 15-60 minutes walltime per token (S3 up to 4 hours), 1 GPU (an A100-SXM4-80GB, 81 920 MiB), at most 3 requests in a row without a pass before a `BLOCKED_<gate>` note. **Never** edit `ci/status.json`, `ci/poll.sh`, `reports/ci-*.out`, `validation/ci_*.json`.

**What changed for campaign 33 (updated 2026-10-13).** The 33 campaign tokens are submitted through a **concurrent poller** (`ci/poll_concurrent.sh`, installed on the Perlmutter side by the owner; `prompts/33` section 7c): every request is its own file `ci/requests/NNN-<TOKEN>.txt` written by `scripts/ci_request.sh T1 T2 ...` (one commit per call; the identity of a request is `<path>@<commit that last touched it>`, run once), up to `MAX_CONCURRENT=4` jobs at a time and `MAX_JOBS_PER_DAY=24` (`prompts/33b` R7 assumes these values; the file `ci/status/<TOKEN>.json` carries each request's state). The earlier one-job poller that reads only `ci/request.txt` still exists (`--legacy`; `scripts/ci_check.sh` still lists a pending legacy `S2_2x4` request). Twenty generic slots `C4_PART_01..20` (`ci/allowed_jobs.campaign33a`, `ci/parts/*.json`) are re-used for the parts of split runs under the seed rule of `prompts/33b` R4. One measured round trip of four jobs took 24.7 h on 2026-10-08/09 (request commit `3a768f9` at 2026-10-08T20:25:33Z, last harvest 2026-10-09T21:07:28Z; `prompts/33b` R7), so the planner counted at most 32 jobs before the Perlmutter maintenance 2026-10-21 06:00 UTC to 2026-10-28 06:00 UTC. **On 2026-10-13/14 the queue was much faster**: request commit to last harvest took 1.0 h to 5.4 h per wave of four or five jobs (Section 12.3, block (a2); my reading of the robot's commit times). Jobs run on one A100 (shared QOS, charged $G/4$ of a node per hour). The CI robot's commits (`ci: submitted job ...`, `ci: results job ...`) are what put the new `validation/` files on `origin/master`.

**Engine policy** (`RUNBOOK.md`): exact numpy/scipy for E1-E3 and S1; Qiskit + Aer-GPU for the hardware-matching gates (L2, L3, L4, S2/S2D, S3, H0/H0P), with the code required to run on qiskit 1.4.3 and qiskit-aer-gpu 0.15.1 (the laptop has qiskit 2.5.2, aer 0.17.2, so gate modules are kept free of qiskit imports at load time); CUDA-Q 0.16 (target `nvidia`) for gate-level validation. Parallelise only along $k$, sector, $g^2$, lattice, shot batch, seed or resample; every GPU job records wall time, per-phase timings, GPUs, s/shot, peak GPU memory and mean GPU utilization in its JSON; more GPUs are proposed only with measured parallel efficiency $E(p)=T_1/(pT_p)\ge0.7$.

**CI jobs actually run** (from `validation/ci_*.json` and `prompts/LOG.md`): smoke job 58717267 (pass; A100 and `qiskit_aer_gpu` True); L4 job 58737320 (FAIL, GPU out-of-memory crash, 608 s; fixed by `shot_chunk_for` plus adaptive halving), L4 job 58741899 (PASS, 686 s, code sha `79f4dae`), S3 calibration job 58771538 (PASS, 255 s, code sha `ea600be`), S2_2x4 job 59162991 (PASS, 99 s, code sha `870d0c4`). Details in Section 6.

### 4.6 Repository bookkeeping directories

`validation/` (gate JSONs, `gates.md`, ignored `BLOCKED.md`), `reports/` (generated gate reports and the planner's analyses), `data/` (reference numbers, hardware raw counts under `data/hardware/`, calibration records, frozen circuits as QPY files, owner decisions), `prompts/` (every plan, numbered; `LOG.md`), `proposal/` (the manual, amendment 01, the Quantinuum access draft), `tests/` (pytest; last recorded totals: `coding` environment 270 passed / 19 skipped and the Quantinuum venv 287 passed / 2 skipped, `validation/Q0P_2x3.json` criterion Q7, with 287 passed / 19 skipped recorded in `prompts/LOG.md` row 2026-10-05 for commit 749fe3c; the newest recorded runs are **585 passed / 40 skipped** in 46 min under load (gate `ENC_compare` criterion C1) and **608 passed / 39 skipped** in 19.6 min (`prompts/LOG.md` row 2026-10-11 step A of `prompts/33b`; 11 `tests/test_campaign33_*.py` files 239 passed / 21 skipped on the qiskit 1.4.3 / aer 0.15.1 twin environment), each with `scripts/check_package.py` returning PACKAGE OK; **newest records (2026-10-13/14):** `validation/Q0P_2x2.json -> Q7`: `coding` environment 625 passed / 47 skipped in 21 min 58 s and the Quantinuum venv 655 passed / 25 skipped (run before the merge with `master`); `validation/Q0P_2x4.json -> Q7`: `coding` **1 failed** / 644 passed / 50 skipped and venv **1 failed** / 673 passed / 21 skipped, the one failure being `tests/test_campaign33_driver.py::test_dry_run_json_exists_and_passes_its_structural_criteria[C2_KCHK]` (the C2_KCHK laptop dry run took 1 152 s against the test's 600 s limit; Section 13.8); I ran no tests), `scratch/planner/` (the planner's prototypes whose numbers are "planner arithmetic" until a gate reproduces them), `slurm/`, `jobs/`, `ci/`.


**Process note added 2026-10-15 (`prompts/33e` R1).** Every CI job so far ran its CPU phases (decoding, Ritz, bootstrap) on **one** CPU core: `jobs/gate.sbatch` line 52 calls `srun python scripts/run_gate.py "$CI_GATE"` without `--cpus-per-task`, and since Slurm 22.05 a job step no longer inherits the allocation's `--cpus-per-task` (the allocation had 32). The exported `OMP_NUM_THREADS=32` therefore over-subscribed one core. The planner rules that this affects speed, not any number; the fix (`srun --cpus-per-task="${SLURM_CPUS_PER_TASK:-1}"` plus a recorded `run.cpu_affinity`) is ordered in `prompts/33e` step 1 and **not yet committed** as of 2026-10-15 17:43 UTC (`git log`).

## 5. The full gate table

Source (updated 2026-10-15): every `validation/*.json` (enumerated with a python snippet that reads `status`, `criteria[*].passed`, `environment.timestamp`, `environment.git_commit`, `runtime_s`), `validation/gates.md` (regenerated on 2026-10-14 by `scripts/update_status.py` with the Quantinuum tier table, commit `e66eb26`; earlier regenerated 2026-10-06 08:34 UTC; it now holds the rows `CF_traj`, `CF_estimator_2x2_info`, `CV_2x2_info`, `Q0P_2x3_plan`, `CV_2x3_plan`, `H0_ddrep` and `K1_2x3_fpilot`, but still not `K0_2x3_2x4`, `H0P_repro`, `H0_*_dryrun`, `K1_2x3_fpilot_dryrun`, `L4_p2_*`, `S2_fixed`, `S2D_idle`; those are added here from their JSON files). Column "kind": *validation* = PASS means a known answer is reproduced; *measurement* = PASS means "preregistered, measured, verified, consistent" and the measured number is the result (Section 4.3). The date/time is the string recorded in the JSON `environment.timestamp` in whatever time zone the run used (MDT, PDT or UTC). "Criteria" is passed/total. The commit is the repository commit at the time the gate ran (`n/a` where the run was on the Perlmutter CI snapshot).

### 5.1 Gate results (87 gate JSON files with criteria lists; 54 on 2026-10-13, 46 on 2026-10-06; the 33 new rows are at the end of the table, in the order the jobs ran)

| gate | file | date, time as recorded | status | criteria | kind | runtime | commit | one-line meaning | key numbers (source in the file named) |
|---|---|---|---|---|---|---|---|---|---|
| `E1` | `validation/E1.json` | 2026-09-14 16:43:44 MDT | PASS | 23/23 | validation | 427 s | 57b3bff | Gauss law and the two independent Hamiltonian builders (2x2) | $\max\lvert [G_a(x),H]\rvert =0.0$ in the 160 000-dim redundant space; kernel dimension 82; sector split $\{2B:\dim\}=\{-4{:}2,-2{:}20,0{:}38,2{:}20,4{:}2\}$; $\max\lvert {\rm eig}(P^\dagger HP)-{\rm eig}(H_{\rm dressed})\rvert =2.309\times10^{-14}$ over 82 levels (threshold $10^{-12}$); element-wise $3.55\times10^{-15}$; link covariance $1.1\times10^{-16}$ |
| `E2` | `validation/E2.json` | 2026-09-14 16:44:00 MDT | PASS | 51/51 | validation | 15 s | 57b3bff | State counts (Table 2), vertex tables, codewords, decoder | 82 / 1 727 / 37 165 states at 2x2 / 2x3 / 2x4; 82/82 round trip at 2x2 (113/113 with a static pair); 2x3 sector dims $\{0{:}677,\pm2{:}426,\pm4{:}95,\pm6{:}4\}$ in the $2B$ key; random-string acceptance 0.15 % at 2x3 (0.242 % for static $[0,4]$) |
| `E3` | `validation/E3.json` | 2026-09-14 16:44:36 MDT | PASS | 85/85 | validation | 36 s | 57b3bff | Exact references (Table 1), static sectors, derived quantities, $\Delta t$ per sector | all Table 1 rows to 4 decimals (e.g. 2x2 $B{=}0$ $E_0=-3.6408$, $\pi/W=0.245$); 2x3 $V(2)=2.5898$; 2x4 $M_B=1.7851$; 2x2 $j_{\max}=1$ gives 152 states |
| `S1` | `validation/S1.json` | 2026-09-14 16:48:20 MDT | PASS | 12/12 | validation | 223 s | 57b3bff | Emulated support recall, certification and size-matched controls (2x3, 2x4) | 2x3 $B{=}0$ recall of the 99.9 % support $=1.0$ and $B{=}1$ $0.989$ at $f=0.1$, $2\times10^5$ shots (threshold 0.9); $E_0$ inside the Weinstein interval; $M_B$ interval $[1.6935,1.8314]\ni1.7765$; ridge Spearman 0.862 / 0.888; CIPSI within 3x of the oracle at $\lvert B\rvert =160,320$; 2x4 proxy recall $0.934$ (threshold 0.85) |
| `CS` | `validation/CS.json` | 2026-09-14 21:37:07 UTC | PASS | 4/4 | validation | 4 s | 3c32216 | Structure of the Hamiltonian terms in codeword space (input to S2) | 2x2 plaquette: one partner per state; 4 distinct pair amplitudes; structured plaquette gate vs dense exponential $3.97\times10^{-16}$; 30 CNOT (8 parity + 6 ladder + 16 UCRz) |
| `S2` | `validation/S2.json` | 2026-09-15 15:12:59 MDT | FAIL | 3/5 | measurement | 436 s | 5d60461 | Structured basic-gate circuits (hopping chains, interior-corner plaquettes) and their CZ cost | FAIL on the cost criteria only: 2x2 routed 618 CZ (budget $\le250$), 2x3 routed 5 477 (budget $\le500$); exactness $1.87\times10^{-14}$ and leakage $4.5\times10^{-14}$ pass |
| `S2_fixed` | `validation/S2_fixed.json` | 2026-09-15 20:18:31 MDT | FAIL | 5/9 | measurement | 301 s | 2fbcf29 | Fixed-angle generator (same codeword pairs, one angle per flip pattern): cost floor, leakage, recall | FAIL: 2x2 671 routed (heavy-hex) / 474 (square grid), 2x3 3 736 / 2 803, all above budget; recall kept (B=0 1.000, B=1 0.937 at $f=0.1$, `data/S2_fixed_recall.json`); not adopted |
| `S2D` | `validation/S2D.json` | 2026-09-16 07:02:12 MDT | FAIL | 6/8 | measurement | 213 s | 89102d2 | Device-resolved budget: 2x2 on Heron (FakeFez snapshot) and 2x3 on an all-to-all RZZ device at declared $\epsilon_2=10^{-3}$ | FAIL 6/8: 2x2 mean $f=0.1248$, worst $0.1166$ (pass); 2x3 mean $f=0.0534$ (needs $\ge0.1$: fail), worst $0.0532$; 2x3 shots per sector 4 605 472 vs quota $2\times10^5$ (fail); reproduces 618 routed and 2 164 all-to-all CZ |
| `S2D_idle` | `validation/S2D_idle.json` | 2026-09-22 16:36:34 MDT | FAIL | 6/15 | measurement | 406 s | 2c6edb6 | S2D re-evaluated on the idle-aware $f$ (scheduled circuit) at both ends of the $T_2$ bracket | FAIL 6/15: live ibm_fez, echo $T_2$: mean $f=6.708\times10^{-3}$, worst $1.542\times10^{-3}$; measured $T_2^*$: mean $1.298\times10^{-5}$; most favourable point of the bracket (DD perfect) mean $0.0623<0.1$. **Withdraws the 2x2/Heron S2D PASS as a hardware statement.** Hardware anchor V5: predicted 30.8 vs measured 35 accepted of 2 000 (ratio 1.135) |
| `S2D_levers` | `validation/S2D_levers.json` | 2026-10-02 11:13:55 MDT | PASS | 9/9 | measurement | 489 s | 782580c | 2x2 duration levers on ibm_kingston: compile/schedule levers, $f$ predicted at both $T_2$ ends, $r_{\rm crit}$ | PASS 9/9: best row duration 0.710x the as-is canary; Aer $f_{\rm clean}$ 0.2170 (echo end) and 0.0312 (ratio 0.174) for the signed family with ALAP; $r_{\rm crit}(0.1)\approx0.329$ (C6 scoped to $p_{\rm ref}\ge0.5$ by planner ruling) |
| `S2_2x4` | `validation/S2_2x4.json` | 2026-10-01 09:15:29 PDT | PASS | 12/12 | measurement | 0 s | n/a | 2x4 coarse step compiled to exact circuits, verified, measured (counts, duration, idle budget, $T_2/t_{2q}$) | PASS 12/12: exactness $3.4\times10^{-14}$; leakage of the transpiled 28-qubit circuit $1.10\times10^{-12}$ (GPU job 59162991); 69 688 CZ all-to-all, 148 726 routed; $T_2/t_{2q}=638\,742$ required vs Heron harmonic mean 1 038 (`reports/S2_2x4_compilation_and_device_requirement.md`) |
| `S3_smoke` | `validation/S3_smoke.json` | 2026-09-16 11:46:01 MDT | FAIL | 1/2 | measurement | 295 s | 1223e92 | S3 pipeline smoke test at 2x3 $B{=}1$ (2 shots per circuit) | FAIL by construction: recall 0.0737 at 24 shots (criterion $\ge0.9$); 295 s on laptop CPU; shows 10.42 s per shot at 2 shots per call |
| `S3` | `validation/S3.json` | 2026-09-22 18:01:22 PDT | PASS | 4/4 | measurement | 248 s | n/a | GPU throughput calibration of the 2x3 $B{=}0$ set (reduced size; recall criterion NOT evaluated) | PASS 4/4 as a calibration: 0.01987 s/shot at 20 qubits on one A100 (job 58771538) vs 3.198 s/shot on the laptop (161x); projected 1.10 h per $2\times10^5$-shot sector (4.41 h for four sectors) |
| `L2` | `validation/L2.json` | 2026-09-15 20:20:11 MDT | PASS | 4/4 | validation | 8 s | 0420211 | Qiskit circuits reproduce the numpy reference at 2x2 | max $\lvert \text{Qiskit}-\text{reference}\rvert =2.69\times10^{-14}$ over 35 circuits; 10 000/10 000 noiseless shots decode; TVD 0.0103 |
| `L3` | `validation/L3.json` | 2026-09-15 15:04:26 MDT | FAIL | 0/2 | measurement | 14 s | 5d60461 | Transpiled CZ counts of the dense 2x2 circuits (S2 baseline) | FAIL as expected: 35 606 CZ all-to-all, 55 459 routed (budget 250); led to the structured-gate work of S2 |
| `L4` | `validation/L4.json` | 2026-09-22 01:22:38 PDT | PASS | 4/4 | validation | 677 s | n/a | Aer noise-model sampling at 2x2 (S3 preparation); the current record is the GPU run | PASS 4/4 on the GPU at full production shots (job 58741899): yields 0.458 / 0.441 vs model 0.378 / 0.376 (ratios 1.21 / 1.17); $\lvert B\rvert =38/38$ and $20/20$; recall 1.000; 19.8x faster than the laptop. The two earlier laptop records are in `L4_p2_*.json` |
| `L4_p2_1e-3` | `validation/L4_p2_1e-3.json` | 2026-09-14 18:24:06 MDT | FAIL | 2/4 | validation | 1012 s | 30684f2 | L4 laptop record at $p_2=10^{-3}$ (reduced shots, 2026-09-14) | FAIL 2/4: yield criterion only ($f=(1-p_2)^{35670}\approx0$); Weinstein criteria pass; 1 012 s |
| `L4_p2_3e-3` | `validation/L4_p2_3e-3.json` | 2026-09-14 18:00:36 MDT | FAIL | 2/4 | validation | 1376 s | 30684f2 | L4 laptop record at $p_2=3\times10^{-3}$ (reduced shots, 2026-09-14) | FAIL 2/4: same cause; 1 376 s |
| `L4_fez` | `validation/L4_fez.json` | 2026-09-16 12:28:26 MDT | PASS | 4/4 | validation | 450 s | 3722018 | L4 with `NoiseModel.from_backend(FakeFez)` (H0 rehearsal) | PASS 4/4: measured yield 0.147 / 0.136 vs model 0.112 / 0.104 (ratios 1.32 / 1.31); recall 1.000; $E_0$ inside both Weinstein intervals |
| `L5` | `validation/L5.json` | 2026-09-15 20:19:58 MDT | PASS | 6/6 | validation | 3 s | 0420211 | CUDA-Q circuits vs the numpy reference at 2x2 (CPU target `qpp-cpu`) | PASS 6/6: TVD 0.0091; endianness test; IR gate coverage TVD 0.019; the `nvidia` target needs compute capability $\ge7.0$ |
| `H0P` | `validation/H0P.json` | 2026-09-16 13:15:46 MDT | PASS | 16/16 | validation | 1179 s | 2392fb3 | H0 preparation on the FakeFez snapshot: 84 frozen circuits, yield by repetition, confusion, Ritz consistency | PASS 16/16 after the yield model gained the term $(1-f)a$: leakage $1.49\times10^{-14}$ over 84 circuits; simulated/model yield ratios 1.34 / 1.75 / 1.53 ($B{=}0$, $r{=}1,2,3$) and 1.30 / 1.54 / 1.59 ($B{=}1$); confusion min diagonal 0.9768 |
| `H0P_rehearsal` | `validation/H0P_rehearsal.json` | 2026-09-21 17:57:49 MDT | PASS | 18/18 | validation | 175 s | 1e5c03b | H0P on FakeFez with the D3' shot plan through the sampling cache | PASS 18/18: supports 38/38 and 20/20, `missing_states==[]`, r=1 yields 0.1489 / 0.1371 |
| `H0P_repro` | `validation/H0P_repro.json` | 2026-09-30 15:28:44 MDT | PASS | 15/15 | validation | 1741 s | 6180c6a | H0P reproducibility run (15 criteria, identical to H0P) | PASS 15/15; "H0P_repro identical" |
| `H0P_ibm_fez` | `validation/H0P_ibm_fez.json` | 2026-09-22 11:46:55 MDT | PASS | 18/18 | validation | 319 s | 1e6d7d3 | H0P re-predicted on the live ibm_fez calibration (D3' plan; last PASS at stamp 20260922T1400Z) | PASS 18/18 (calibration run, throughput only): supports 38/38 and 20/20; $N_4=6900$ ($B{=}0$) / 16 800 ($B{=}1$); first attempt on 2026-09-21 FAILED 15/16 (criterion 3 premise was a coin flip, `reports/H0P_ibm_fez_escalation_20260921.md`) |
| `H0_dryrun` | `validation/H0_dryrun.json` | 2026-09-30 15:41:37 MDT | PASS | 9/9 | validation | 10 s | 6180c6a | Gate H0 run on SamplerV2 dry-run counts (FakeFez) | PASS 9/9: 58/58 accepted strings re-encode; measured $f$ 0.1710 vs predicted 0.1727 ($B{=}0$) |
| `H0_canary` | `validation/H0_canary.json` | 2026-09-30 15:41:49 MDT | FAIL | 3/6 | measurement | 11 s | 6180c6a | The 3-pub canary on ibm_fez (go rule before the main submission) | FAIL 3/6 = canary NO-GO: 8 accepted of 267 vs the preregistered $\ge10$ and simulated 71; yield-inverted $f=0.0255$ vs predicted 0.2195; $B{=}0$ energy not reproduced (support 8 of 38); readout drift ratio 3.516 (limit 3) |
| `H0_diag_dryrun` | `validation/H0_diag_dryrun.json` | 2026-09-22 14:16:46 MDT | FAIL | 6/7 | measurement | 1 s | 9cfe3ec | H0_diag on the simulator (path check) | FAIL 6/7: C5 only (post-diction vs simulator sample); path check |
| `H0_diag` | `validation/H0_diag.json` | 2026-09-22 14:46:44 MDT | FAIL | 6/8 | measurement | 1 s | 4d1e8f6 | Diagnostic session on ibm_fez: DD x twirling factorial and windowed $T_1$ / Ramsey | FAIL 6/8 but decisive on its question: J1 (both options off) 35 accepted of 2 000 vs preregistered 30.8 $\pm$ 5.5 (idle relaxation) and 374.5 $\pm$ 17.4 (options hypothesis): options exonerated; C5 post-diction misses by 88.6x / 12.0x (the bound over-charges); 15.0 s of QPU time |
| `H0_model` | `validation/H0_model.json` | 2026-09-30 15:31:18 MDT | PASS | 5/5 | measurement | 2 s | 6180c6a | Post-diction of the fez counts by scheduled Aer at both ends of the $T_2$ bracket; clean-yield statistic | PASS 5/5: 6 reference hits vs 2.018 from garbage ($P=0.0172$); at the measured $T_2^*$ predicted/measured clean count 1.0503, at the echo $T_2$ 49.58; acceptance structure ratio 0.8643 |
| `H0_kpilot_dryrun` | `validation/H0_kpilot_dryrun.json` | 2026-10-02 12:04:30 MDT | PASS | 9/9 | measurement | 49 s | 761369f | Kingston pilot dry run on FakeKingston | PASS 9/9 after the K3 ruling (`prompts/21a`) |
| `H0_kpilot` | `validation/H0_kpilot.json` | 2026-10-02 12:31:53 MDT | FAIL | 8/9 | measurement | 450 s | fc3a5a2 | ibm_kingston pilot: windowed Ramsey, $T_1$, direct $f_{\rm clean}$ of the signed $k{=}1$ circuits; GO/NO-GO | FAIL 8/9 (K5: $T_2^*$ resolved on 9/12 qubits, 10 required), **decision NO-GO**: pooled $f=0.0413$, 95 % [0.0361, 0.0470]; $r_{\rm eff}=0.0974$ vs $r_{\rm crit}=0.3285$; 12.0 s QPU |
| `H0_ddtest_dryrun` | `validation/H0_ddtest_dryrun.json` | 2026-10-02 14:10:22 MDT | PASS | 8/8 | measurement | 15 s | aa4da1e | DD A/B test dry run | PASS 8/8 (path check; simulator cannot predict DD gains) |
| `H0_ddtest` | `validation/H0_ddtest.json` | 2026-10-02 14:37:48 MDT | PASS | 8/8 | measurement | 601 s | d4b3855 | One-job A/B test of client-side DD vs no DD on the pilot's two $k{=}1$ circuits; adoption by preregistered ratio rule | PASS 8/8: T0 (no DD) $f=0.0400$ [0.0358, 0.0446]; T1 context-aware 0.0005 ($R=0.012$); T2 XY4 everywhere 0.1118 ($R=2.793$); **T3 XY4 in windows $\ge1\,\mu$s adopted: $f=0.1129$ [0.1058, 0.1203], $R=2.819$ [2.495, 3.185]**; 20.0 s QPU |
| `H0_2x2_dryrun` | `validation/H0_2x2_dryrun.json` | 2026-10-02 15:04:52 MDT | PASS | 8/8 | measurement | 17 s | 4e979a0 | Full 2x2 run dry run | PASS 8/8 |
| `H0_2x2` | `validation/H0_2x2.json` | 2026-10-02 16:04:51 MDT | PASS | 8/8 | measurement | 444 s | da715fc | The full 2x2 SKQD run on ibm_kingston below the signed budget (owner decision 2026-10-02) | PASS 8/8: pooled $f$ (7 $k{=}1$ circuits) 0.1271 [0.1084, 0.1479]; 133 907 coarse shots; $B_{\rm sig}$ 35/38 and 19/20; $E_R-E_0=5.48\times10^{-4}$ ($B{=}0$) and $5.75\times10^{-6}$ ($B{=}1$); garbage-only reproduces $E_0$ in 100/100 seeds; 53.0 s QPU |
| `Q0P_2x3` | `validation/Q0P_2x3.json` | 2026-10-02 21:36:57 MDT | PASS | 7/7 | measurement | 926 s | 8072b8d | Signed 2x3 circuits compiled to the Quantinuum native gate set, verified, costed, packaged (Stage A; Stage E/P not run) | PASS 7/7: 44 frozen circuits, max $\lvert \Delta\psi\rvert =2.09\times10^{-13}$, 2 158 ZZPhase on all 44, mean 4.9666 HQC/shot; H2-2 gate-only $f=0.1502$, Helios-1 0.1642; Stage E 11 936 eHQC, pilot 9 938 HQC (later re-planned); 0 HQC spent |
| `CF_traj` | `validation/CF_traj.json` | 2026-10-05 13:47:33 MDT | PASS | 7/7 | measurement | 1201 s | a8ebbaa | Pauli-trajectory decomposition of the reference-hit excess and the near-clean correction $r_{nc}$ | PASS 7/7: trajectory prediction 63.46 $\pm$ 2.254 vs 64 observed hits ($P=0.9794$); $r_{nc}=1.115$; floor theorem holds on all four arms; $k{=}4$ mixture bias 1.274 [1.170, 1.402] |
| `K0_2x3_2x4` | `validation/K0_2x3_2x4.json` | 2026-10-06 01:38:10 MDT | PASS | 6/6 | measurement | 943 s | 880961d | ibm_kingston readiness of 2x3 and 2x4 (prompts/25 Part A); **rewritten on 2026-10-06 by the `--live` run (the 2026-10-05 FAIL 5/6 row, written with `--skip-tests`, is superseded)**; its verdict fields are a model result, not a criterion | PASS 6/6: all-to-all 2 164 CZ reproduced; the 2x3 circuit `B0_ref25_k1` routed on the target of each record with the exactness-gated seed rule (plain level-3 seed 6, 5 527 CZ, is NOT exact: max $\lvert\Delta\psi\rvert=4.9\times10^{-5}$) to **5 659 CZ**, 21 active qubits, ALAP 410.3 / 411.2 $\mu$s. Committed record 2026-10-02 (verdict record): $f_{\rm ceiling,2q}=9.833\times10^{-3}$, layout gate-only $6.069\times10^{-6}$, idle-aware $1.06\times10^{-16}$ (echo $T_2$) / $3.73\times10^{-38}$ ($T_2^*$ ratio 0.174), $\epsilon_2$ needed for $f=0.05$ $5.29\times10^{-4}$ vs best edge $8.16\times10^{-4}$ (misses by 1.54x). Live record 2026-10-06: $6.717\times10^{-3}$, $1.671\times10^{-5}$, $1.66\times10^{-15}$ / $5.20\times10^{-35}$, misses by 1.67x. 2x4 $\log_{10}f_{\rm ceiling}=-52.8$ (routed). No record meets 0.1 / 0.05; 0 QPU s; pytest 342 passed / 19 skipped |
| `CV_2x2_info` | `validation/CV_2x2_info.json` | 2026-10-05 17:41:27 MDT | PASS | 2/2 | measurement | 14 s | 3d5f05a | Convergence and coverage curves on the recorded H0_2x2 counts, **labelled "not a device test (saturation)"**; CV0 (structural) only | PASS 2/2: the curves are flat because the sectors saturate from garbage ($Na/\dim\ge5$, $\lvert B_{\rm all}\rvert=\dim$, garbage-only reaches $E_0$): CV4 margin at $N$ is $-1.37\times10^{-4}$ ($B=0$) and $-2.2\times10^{-15}$ ($B=1$; `data.information.<sector>.information.CV4_margin_at_N`) against $E_{\rm tol}=0.02317$ / 0.01214; no verdict on any recorded 2x2 result; this is why the 2x3 criteria exist |
| `CF_estimator_2x2_info` | `validation/CF_estimator_2x2_info.json` | 2026-10-05 17:28:05 MDT | PASS | 2/2 | measurement | 4 s | 3d5f05a | Every recorded 2x2 clean fraction labelled by statistic ($f_{\rm hit}$ or mixture), with the corrected $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$, the 2x2 signed-bar qualification, the A5 model bracket and (added by `prompts/31` ruling 6) the `qualification_ruling` text | PASS 2/2: adopted cell T3 $f_{\rm hit}=0.1129$ [0.1058, 0.1203] $\to$ $\hat f_{\rm ideal}=0.1012$ [0.0938, 0.1091]; the preregistered rule (lower 95 % end $\ge0.1$) reads **AMBIGUOUS**, the v3 rule of the 2x3 stages (lower $\ge0.05$ and point $\ge0.10$) reads GO but is not applied retroactively; A5 bracket $r=0.674$ [0.539, 0.835] ($T_2^*$ end) and 0.902 [0.884, 0.918] (echo end); no recorded verdict edited (Block (b3)) |
| `Q0P_2x3_plan` | `validation/Q0P_2x3_plan.json` | 2026-10-05 17:56:24 MDT | PASS | 7/7 | measurement | 781 s | 3d5f05a | Rule D3'-R implemented and reproduced (P1), $\lambda^*$ and recall guarantees (P2), emulated check of the plan on $B_{\rm all}$ with the owner's certificate reading (P3), HQC by the billing formula job by job (P4), preregistration v3 rendered from the JSON only (P5), tests (P6), plan identical to `CV_2x3_plan`'s final plan (P7) | PASS 7/7: D3'-R base plan (no re-sizing) 63 875 + 96 503 = 160 378 shots, 797 157 HQC at $f=0.05$; 84 112 shots, 418 166 HQC at 0.10; 60 812 shots, 302 382 HQC at 0.15; **re-sized plan 1 279 660 / 665 605 / 471 801 HQC** (Block (g)); Stage E v3 and Stage P v3 each 2 000 shots (800/800/200/200), 9 949.92 eHQC / HQC (USD 124 374 ESTIMATE for Stage P); GO rule v3 on $\hat f_{\rm ideal}$; calibration pubs 45.0 and 45.2 HQC; at $f=0.10$ recall of $S_{999}$ on $B_{\rm all}$ 0.953 / 0.977 / 0.953 ($B=0$) and 0.947 / 0.958 / 0.958 ($B=1$) in the three seeds (`prompts/LOG.md` row 2026-10-05); pytest 321 passed / 19 skipped; commits no HQC |
| `CV_2x3_plan` | `validation/CV_2x3_plan.json` | 2026-10-05 17:40:48 MDT | PASS | 37/37 | measurement | 679 s | 3d5f05a | Emulated check (S1 proxy at clean fraction $0.7f$, 3 seeds, $f=0.05/0.10/0.15$, both sectors) that the D3'-R plan converges in shots and in Krylov $k$, carries $\ge0.99$ of the ground-state weight, beats random bases, and meets the certificate widths; **an emulation of the plan, not a device statement** | PASS 37/37 on `B_all` $\cup$ references: $E_{\rm tol}=1.4225\times10^{-2}$ ($B=0$, 69 states) and $1.1040\times10^{-2}$ ($B=1$, 76 states); $B=0$ passes at $s=1$ at every $f$, $B=1$ needs $s=2$ ($s=1.5$ fails CV2); oracle-width table reproduced (196 fields, max scaled difference $3.2\times10^{-14}$); no STOP (Section 6.19, Blocks (q), (q2), (r)) |
| `H0_ddrep_dryrun` | `validation/H0_ddrep_dryrun.json` | 2026-10-06 00:59:27 MDT | PASS | 8/8 | measurement | 14 s | cd9ce12 | H0_ddrep dry run on Aer / FakeKingston (20 pubs x 6 000; the sampling itself took 1 738 s per `prompts/LOG.md`, the JSON re-assembly 14 s) | PASS 8/8: path check only; ratios sit at the null values (T3 0.830, T1 0.735 on Aer) because Aer cannot show a DD gain (its relaxation on a delay is Markovian) and the trains sit at the readout floor |
| `H0_ddrep` | `validation/H0_ddrep.json` | 2026-10-06 01:11:17 MDT | PASS | 8/8 | measurement | 422 s | 36c48a2 | One-job replication on `ibm_kingston`: the XY4 gain (T0 vs T3), the T1 collapse, four mechanism cells (M1-M4) and four pulse-train pubs; **no criterion on R1, R2, C1, the classes or the mechanism reading** | PASS 8/8, results: **R1 False, R2 False, C1 False**; $f_{T0}=0.0818$ [0.0758, 0.0881] (0.0400 on 2026-10-02), $R_{T3}=0.895$ [0.804, 0.996] (2.819 on 10-02), $R_{T1}=0.647$ [0.575, 0.727], $R_{M4}=1.150$ [1.040, 1.271] (the only INTACT cell); reading "no single hypothesis"; $x$ over-rotation $\epsilon_q=0.0148$-$0.0204$ rad on 12/12 qubits; job `db29p6nr11fs7396e4ig`, 37.0 s (Section 6.21, Blocks (o), (p)) |
| `K1_2x3_fpilot_dryrun` | `validation/K1_2x3_fpilot_dryrun.json` | 2026-10-06 02:20:48 MDT | PASS | 9/9 | measurement | 430 s | f8df126 | K1 dry run: readout pubs through the real `h0_submit --dry-run` path on FakeKingston, coarse pubs sampled noiselessly (400 shots each; one noisy 21-qubit shot cost 140.6 s) | PASS 9/9: path check; noiseless reference hits 754 of 800, $f_{\rm hit}=1.238$ [1.151, 1.330] ($0.82\,f_{\rm hit}$ 95 % [0.944, 1.090], containing 1), decision class GO-B by construction |
| `K1_2x3_fpilot` | `validation/K1_2x3_fpilot.json` | 2026-10-06 02:33:45 MDT | PASS | 8/8 | measurement | 422 s | 504d452 | The 2x3 clean-fraction pilot on `ibm_kingston`: the two signed $k=1$ circuits (`B0_ref117_k1`, `B1_ref29_k1`, 5 659 CZ, XY4 cell T3) + 2 readout pubs, one job of 4 pubs x $10^5$ shots; GO-B / GO-A / NO-GO on $\hat f_{\rm ideal}$; **no criterion on $f$ or on the decision** | PASS 8/8, decision **NO-GO (firm)**: 0 reference hits in $2\times10^5$ shots vs 0.191 from garbage; pooled $\hat f_{\rm ideal}=-1.12\times10^{-6}$, 95 % upper bound $2.06\times10^{-5}$ (GO-A needs $3\times10^{-4}$); accepted 58 / 45 of $10^5$ (garbage level); readout min diagonal 0.9358; job `db2avbe8v0ts73c2i8b0`, 188.0 s (Section 6.22, Block (s)) |
| `ENC_compare` | `validation/ENC_compare.json` | 2026-10-08 00:11:16 MDT | PASS | 8/8 | measurement | 2 787 s | fa24ec4 | Does a de-duplicated codeword layout (E2) or a codeword-assignment search (E5') shorten the circuits? (`prompts/34`); the dedup files are UNSIGNED | PASS 8/8; qubits 20 to 13 at 2x3 (0.650); CZ all-to-all 2 164 to 2 004 (0.926), routed heavy-hex 5 477 to 4 941 (0.902), native ZZ 2 158 to 1 996 (0.925); kingston `B0_ref117_k1` 5 659 to 5 091 CZ, 21 to 13 active qubits, ALAP 411.152 to 387.844 $\mu$s; H2-2 gate-only mean $f$ 0.1503 to 0.1739; single-flip detection 98.17 / 98.31 % to 83.05 / 90.75 %; random acceptance $\times$128 (6.46e-4 to 0.0826); verdict `shortens` true, **`shortens_meaningfully` false** (threshold 0.5; 2x2 ratios 0.883 a2a, 0.723 routed); E5' best step ratio 1.066 (worse) |
| `C1_IDEAL` | `validation/C1_IDEAL.json` | 2026-10-09 12:04:10 PDT | PASS | 10/10 | validation | 89 s | n/a (CI) | Class 1: the whole signed 2x3 family with no noise on the GPU; exactness of five circuit families; per-state 5-sigma sampling test; $f=1$ SKQD reference | PASS 10/10 (job 59570217): max $\lvert\Delta\psi\rvert$ IR-L0 $3.5\times10^{-14}$, NAT-O0 $2.1\times10^{-13}$, IBM-U/T0/T3 $2.3\times10^{-12}$; 1 441 states in 50 circuits, max $z=4.84$, 0 failures; noiseless SKQD at the $f=0.10$ plan: recall of $S_{999}$ 1.0 in both sectors, $E_R-E_0$ $1.80\times10^{-4}$ ($B=0$, 34 909 shots, $\lvert B_{\rm all}\rvert=333$) and $1.16\times10^{-4}$ ($B=1$, 99 000 shots, 345) |
| `C3_AER` | `validation/C3_AER.json` | 2026-10-09 12:03:39 PDT | PASS | 10/10 | validation | 59 s | n/a (CI) | Class 3: the frozen Quantinuum-native family (NAT-O0, 44 circuits) noiseless on Aer GPU | PASS 10/10 (job 59570221): max $\lvert\Delta\psi\rvert=2.08\times10^{-13}$; 1 393 states in 44 circuits, max $z=4.08$, 0 failures; recall 1.0; $E_R-E_0$ $1.83\times10^{-4}$ ($B=0$), $1.83\times10^{-4}$ ($B=1$) at the plan |
| `C4_FCELLS_A` | `validation/C4_FCELLS_A.json` | 2026-10-09 13:14:53 PDT | FAIL | 7/8 | measurement | 2 320 s | n/a (CI) | Class 4: 10-minute GPU timing ladder, then f-cells (clean fraction of the four Stage-E circuits, 2 000 shots) for scenarios E1-E5c $\times$ optimisation variants O0-O4 | **FAIL on S6 only**: 10 of 42 cells completed in the 2 345 s job (32 dropped by the budget rule); P10, P11 PASS (E1 x O0 hits 338 inside the CF_traj band [302, 427], prediction 362.6 $\pm$ 12.9); job 59570315; data in Section 7.4 |
| `C4_FCELLS_B` | `validation/C4_FCELLS_B.json` | 2026-10-13 08:08:10 PDT | PASS | 8/8 | measurement | 1 866 s | n/a (CI) | Class 4: f-cells for E6a/b/c (error scale), E7 (matched-$f$ 0.05-0.15), 35 cells; faithful redo of gate S3 (IR-L3-RZZ, E8, 32 circuits $\times$ 100 shots) | PASS 8/8 (job 59736863): no cell dropped; P12: accepted 656 of 3 200 (yield 0.205) inside the binomial band (650, 741) around S3's 695 / 3 200 (0.2172); job 1 884 s |
| `C2_CAL` | `validation/C2_CAL.json` | 2026-10-13 08:19:40 PDT | PASS | 12/12 | measurement | 1 816 s | n/a (CI) | Class 2 calibration (run 3 of the token): IBM-T0 `B0_ref117_k1` sampled with three representations of thermal relaxation (PTA, RM, Kraus) and compared with each other and with the K1 hardware strings | PASS 12/12 (job 59736871) with a **decision that production = Kraus** (P4a FAIL is a decision, not a gate failure); PTA / RM / Kraus s/shot 0.287 / 0.354 / 1.840; $z$ against K1: +1.82 / $-30.6$ / $-54.2$ (Section 8) |
| `C4_CF` | `validation/C4_CF.json` | 2026-10-13 08:17:05 PDT | FAIL | 7/8 | measurement | 2 401 s | n/a (CI) | CF_traj redone on the GPU, $K=2000$ target trajectories per arm; $r$ per arm; new $r_{nc}$ | **FAIL on S6 only** (1 232 / 1 262 / 1 244 / 1 239 trajectories in 2 400 s, 0.475 s per trajectory against 0.3 sized); P16, P17 PASS; pooled $r(10^{-3})=1.055$ [1.033, 1.078]; `r_nc_new` 1.078 against 1.115; $k=4$ arm 1.172 [1.128, 1.217]; job 59736866 |
| `C4_F5_B0` | `validation/C4_F5_B0.json` | 2026-10-13 08:28:39 PDT | PASS | 8/8 | measurement | 2 223 s | n/a (CI) | The first full noisy 2x3 SKQD run: scenario E7(0.07) $\times$ O0 at the $f=0.10$ plan of record, sector $B=0$, CV1-CV5 in-job | PASS 8/8 (job 59736879): 34 909 shots; CV1-CV5 all true; $E_R-E_0=2.43\times10^{-4}$, Kato-Temple width $8.32\times10^{-4}$, recall 1.0, $W=0.999972$; pooled $f_{\rm hit}=0.1445$, $\hat f_{\rm ideal}=0.1296$ [0.1149, 0.1455] (Section 7.7) |
| `C4_F1_B0` | `validation/C4_F1_B0.json` | 2026-10-13 10:08:00 PDT | PASS | 8/8 | measurement | 1788 s | n/a (CI) | Class 4 run F1_B0 (E1 x NAT-O0, sector B=0, plan tier 0.15), whole run | PASS 8/8 (job 59739276): 27309 shots; $E_R-E_0=3.29\times10^{-4}$; Kato-Temple width $1.15\times10^{-3}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999962$; pooled $k=1$ $f_{\rm hit}=0.2544$ [0.2326, 0.2777], $\hat f_{\rm ideal}=0.2281$ |
| `C4_F7_B0` | `validation/C4_F7_B0.json` | 2026-10-13 09:49:03 PDT | PASS | 8/8 | measurement | 650 s | n/a (CI) | Class 4 run F7_B0 (E1 x NAT-O2, sector B=0, plan tier 0.15), whole run | PASS 8/8 (job 59739278): 27309 shots; $E_R-E_0=3.35\times10^{-4}$; Kato-Temple width $1.08\times10^{-3}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999959$; pooled $k=1$ $f_{\rm hit}=0.2483$ [0.2267, 0.2713], $\hat f_{\rm ideal}=0.2226$ |
| `C4_F5_B1` | `validation/C4_F5_B1.json` | 2026-10-13 10:10:44 PDT | PASS | 7/7 | measurement | 1373 s | n/a (CI) | Class 4 run F5_B1 (E7(0.07) x NAT-O0, sector B=1, plan tier 0.1), part 1 of 2 | PASS 7/7 (job 59739280): 49500 shots; $E_R-E_0=1.76\times10^{-4}$; Weinstein width $3.64\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999975$; pooled $k=1$ $f_{\rm hit}=0.1271$ [0.1040, 0.1539], $\hat f_{\rm ideal}=0.1140$ |
| `C4_PART_01` | `validation/C4_PART_01.json` | 2026-10-13 10:10:31 PDT | PASS | 8/8 | measurement | 1360 s | n/a (CI) | Class 4 run F5_B1 (E7(0.07) x NAT-O0, sector B=1, plan tier 0.1), part 2 of 2 | PASS 8/8 (job 59739282): 49500 shots; $E_R-E_0=3.40\times10^{-4}$; Weinstein width $4.81\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999948$; pooled $k=1$ $f_{\rm hit}=0.1332$ [0.1095, 0.1605], $\hat f_{\rm ideal}=0.1194$ |
| `C4_F4_B0a` | `validation/C4_F4_B0a.json` | 2026-10-13 11:21:08 PDT | PASS | 7/7 | measurement | 1395 s | n/a (CI) | Class 4 run F4_B0a (E7(0.10) x NAT-O0, sector B=0, S3 quota half a), part 1 of 2 | PASS 7/7 (job 59742843): 50016 shots; $E_R-E_0=1.21\times10^{-4}$; Kato-Temple width $4.59\times10^{-4}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999987$; pooled $k=1$ $f_{\rm hit}=0.1943$ [0.1863, 0.2025], $\hat f_{\rm ideal}=0.1743$ |
| `C4_PART_02` | `validation/C4_PART_02.json` | 2026-10-13 11:43:28 PDT | FAIL | 7/8 | measurement | 1257 s | n/a (CI) | Class 4 run F4_B0a (E7(0.10) x NAT-O0, sector B=0, S3 quota half a), part 2 of 2 | FAIL 7/8 (job 59745007): 45696 shots of 49984 requested; $E_R-E_0=2.69\times10^{-4}$; Kato-Temple width $9.16\times10^{-4}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999969$; pooled $k=1$ $f_{\rm hit}=0.1909$ [0.1826, 0.1994], $\hat f_{\rm ideal}=0.1712$; **FAIL on S6 only** (deadline stop, Section 7.9) |
| `C4_F4_B1a` | `validation/C4_F4_B1a.json` | 2026-10-13 11:45:02 PDT | PASS | 7/7 | measurement | 1351 s | n/a (CI) | Class 4 run F4_B1a (E7(0.10) x NAT-O0, sector B=1, S3 quota half a), part 1 of 2 | PASS 7/7 (job 59745015): 50004 shots; $E_R-E_0=3.13\times10^{-4}$; Weinstein width $5.07\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999959$; pooled $k=1$ $f_{\rm hit}=0.1858$ [0.1780, 0.1938], $\hat f_{\rm ideal}=0.1666$ |
| `C4_PART_03` | `validation/C4_PART_03.json` | 2026-10-13 11:55:48 PDT | PASS | 8/8 | measurement | 1345 s | n/a (CI) | Class 4 run F4_B1a (E7(0.10) x NAT-O0, sector B=1, S3 quota half a), part 2 of 2 | PASS 8/8 (job 59745024): 49992 shots; $E_R-E_0=3.82\times10^{-4}$; Weinstein width $5.65\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999951$; pooled $k=1$ $f_{\rm hit}=0.1834$ [0.1756, 0.1914], $\hat f_{\rm ideal}=0.1644$ |
| `C4_F4_B0b` | `validation/C4_F4_B0b.json` | 2026-10-13 12:51:28 PDT | PASS | 7/7 | measurement | 1388 s | n/a (CI) | Class 4 run F4_B0b (E7(0.10) x NAT-O0, sector B=0, S3 quota half b), part 1 of 2 | PASS 7/7 (job 59747539): 50016 shots; $E_R-E_0=3.04\times10^{-4}$; Kato-Temple width $1.04\times10^{-3}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999965$; pooled $k=1$ $f_{\rm hit}=0.1860$ [0.1782, 0.1940], $\hat f_{\rm ideal}=0.1668$ |
| `C4_PART_04` | `validation/C4_PART_04.json` | 2026-10-13 12:49:20 PDT | FAIL | 7/8 | measurement | 1261 s | n/a (CI) | Class 4 run F4_B0b (E7(0.10) x NAT-O0, sector B=0, S3 quota half b), part 2 of 2 | FAIL 7/8 (job 59747548): 45696 shots of 49984 requested; $E_R-E_0=1.82\times10^{-4}$; Kato-Temple width $6.15\times10^{-4}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999979$; pooled $k=1$ $f_{\rm hit}=0.1786$ [0.1706, 0.1869], $\hat f_{\rm ideal}=0.1602$; **FAIL on S6 only** (deadline stop, Section 7.9) |
| `C4_F4_B1b` | `validation/C4_F4_B1b.json` | 2026-10-13 13:46:50 PDT | PASS | 7/7 | measurement | 1360 s | n/a (CI) | Class 4 run F4_B1b (E7(0.10) x NAT-O0, sector B=1, S3 quota half b), part 1 of 2 | PASS 7/7 (job 59747551): 50004 shots; $E_R-E_0=1.05\times10^{-3}$; Weinstein width $8.92\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 0.989; $W=0.999851$; pooled $k=1$ $f_{\rm hit}=0.1771$ [0.1695, 0.1850], $\hat f_{\rm ideal}=0.1589$ |
| `C4_PART_05` | `validation/C4_PART_05.json` | 2026-10-13 13:58:39 PDT | PASS | 8/8 | measurement | 1346 s | n/a (CI) | Class 4 run F4_B1b (E7(0.10) x NAT-O0, sector B=1, S3 quota half b), part 2 of 2 | PASS 8/8 (job 59747553): 49992 shots; $E_R-E_0=4.91\times10^{-4}$; Weinstein width $6.27\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999935$; pooled $k=1$ $f_{\rm hit}=0.1795$ [0.1719, 0.1875], $\hat f_{\rm ideal}=0.1610$ |
| `C4_F8_B0a` | `validation/C4_F8_B0a.json` | 2026-10-13 16:04:50 PDT | PASS | 7/7 | measurement | 1074 s | n/a (CI) | Class 4 run F8_B0a (E8 x IR-L3-RZZ, sector B=0, S3 quota half a), part 1 of 2 | PASS 7/7 (job 59749780): 50016 shots; $E_R-E_0=2.55\times10^{-4}$; Kato-Temple width $9.58\times10^{-4}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999974$; pooled $k=1$ $f_{\rm hit}=0.1291$ [0.1227, 0.1359], $\hat f_{\rm ideal}=0.1158$ |
| `C4_PART_06` | `validation/C4_PART_06.json` | 2026-10-13 16:10:48 PDT | PASS | 8/8 | measurement | 1103 s | n/a (CI) | Class 4 run F8_B0a (E8 x IR-L3-RZZ, sector B=0, S3 quota half a), part 2 of 2 | PASS 8/8 (job 59749784): 49984 shots; $E_R-E_0=2.54\times10^{-4}$; Kato-Temple width $9.26\times10^{-4}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999972$; pooled $k=1$ $f_{\rm hit}=0.1329$ [0.1263, 0.1397], $\hat f_{\rm ideal}=0.1192$ |
| `C4_F8_B1a` | `validation/C4_F8_B1a.json` | 2026-10-13 16:36:53 PDT | PASS | 7/7 | measurement | 978 s | n/a (CI) | Class 4 run F8_B1a (E8 x IR-L3-RZZ, sector B=1, S3 quota half a), part 1 of 2 | PASS 7/7 (job 59752618): 50004 shots; $E_R-E_0=4.86\times10^{-4}$; Weinstein width $6.25\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999934$; pooled $k=1$ $f_{\rm hit}=0.1346$ [0.1280, 0.1415], $\hat f_{\rm ideal}=0.1207$ |
| `C4_PART_07` | `validation/C4_PART_07.json` | 2026-10-13 16:37:05 PDT | PASS | 8/8 | measurement | 990 s | n/a (CI) | Class 4 run F8_B1a (E8 x IR-L3-RZZ, sector B=1, S3 quota half a), part 2 of 2 | PASS 8/8 (job 59752623): 49992 shots; $E_R-E_0=7.72\times10^{-4}$; Weinstein width $7.90\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999899$; pooled $k=1$ $f_{\rm hit}=0.1370$ [0.1303, 0.1439], $\hat f_{\rm ideal}=0.1228$ |
| `C4_F1_B1` | `validation/C4_F1_B1.json` | 2026-10-14 08:30:18 PDT | PASS | 7/7 | measurement | 857 s | n/a (CI) | Class 4 run F1_B1 (E1 x NAT-O0, sector B=1, plan tier 0.15), part 1 of 2 | PASS 7/7 (job 59779331): 33800 shots; $E_R-E_0=2.92\times10^{-4}$; Weinstein width $4.65\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999959$; pooled $k=1$ $f_{\rm hit}=0.2373$ [0.2053, 0.2730], $\hat f_{\rm ideal}=0.2128$ |
| `C4_PART_10` | `validation/C4_PART_10.json` | 2026-10-14 08:51:40 PDT | PASS | 8/8 | measurement | 844 s | n/a (CI) | Class 4 run F1_B1 (E1 x NAT-O0, sector B=1, plan tier 0.15), part 2 of 2 | PASS 8/8 (job 59779334): 33800 shots; $E_R-E_0=2.38\times10^{-4}$; Weinstein width $4.37\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999968$; pooled $k=1$ $f_{\rm hit}=0.2482$ [0.2154, 0.2846], $\hat f_{\rm ideal}=0.2226$ |
| `C4_F7_B1` | `validation/C4_F7_B1.json` | 2026-10-14 08:54:54 PDT | PASS | 7/7 | measurement | 692 s | n/a (CI) | Class 4 run F7_B1 (E1 x NAT-O2, sector B=1, plan tier 0.15), part 1 of 2 | PASS 7/7 (job 59779337): 33800 shots; $E_R-E_0=4.23\times10^{-4}$; Weinstein width $5.37\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999936$; pooled $k=1$ $f_{\rm hit}=0.2676$ [0.2335, 0.3053], $\hat f_{\rm ideal}=0.2400$ |
| `C4_PART_11` | `validation/C4_PART_11.json` | 2026-10-14 09:06:28 PDT | PASS | 8/8 | measurement | 676 s | n/a (CI) | Class 4 run F7_B1 (E1 x NAT-O2, sector B=1, plan tier 0.15), part 2 of 2 | PASS 8/8 (job 59779338): 33800 shots; $E_R-E_0=3.06\times10^{-4}$; Weinstein width $4.80\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999958$; pooled $k=1$ $f_{\rm hit}=0.2567$ [0.2233, 0.2937], $\hat f_{\rm ideal}=0.2302$ |
| `C2_KCHK` | `validation/C2_KCHK.json` | 2026-10-14 10:03:30 PDT | FAIL | 7/10 | measurement | 2312 s | n/a (CI) | Class 2: the GPU Kraus check (`prompts/33d` R3): IBM-T0 `B0_ref117_k1` under I-ECHO with Kraus on three GPU engines, RM on the GPU, and Kraus and RM on the CPU in a separate process; decides the class-2 representation | FAIL 7/10 (job 59780907): mean Hamming weight $\bar w$ `kraus_gpu_cusv` 3.00 $\pm$ 0.24 (256 shots), `kraus_gpu_native` 3.57 $\pm$ 0.25 (256), `kraus_gpu_cusv_nofusion` 1.14 $\pm$ 0.22 (128), `rm_gpu_cusv` 7.43 $\pm$ 0.10 (512); **both CPU arms 0 shots** (1-thread process killed, `returncode -9`), so K1 and K2 undecided (`production_representation: blocked`), K3 `validated_kraus_gpu_path: none`, S6 short; P0 raw counts stored (Section 8) |
| `C4_F8_B0b` | `validation/C4_F8_B0b.json` | 2026-10-14 10:12:20 PDT | PASS | 7/7 | measurement | 1029 s | n/a (CI) | Class 4 run F8_B0b (E8 x IR-L3-RZZ, sector B=0, S3 quota half b), part 1 of 2 | PASS 7/7 (job 59780912): 50016 shots; $E_R-E_0=1.26\times10^{-4}$; Kato-Temple width $4.82\times10^{-4}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999987$; pooled $k=1$ $f_{\rm hit}=0.1370$ [0.1303, 0.1439], $\hat f_{\rm ideal}=0.1228$ |
| `C4_PART_08` | `validation/C4_PART_08.json` | 2026-10-14 10:24:07 PDT | PASS | 8/8 | measurement | 1050 s | n/a (CI) | Class 4 run F8_B0b (E8 x IR-L3-RZZ, sector B=0, S3 quota half b), part 2 of 2 | PASS 8/8 (job 59780915): 49984 shots; $E_R-E_0=2.14\times10^{-4}$; Kato-Temple width $6.94\times10^{-4}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999974$; pooled $k=1$ $f_{\rm hit}=0.1357$ [0.1291, 0.1427], $\hat f_{\rm ideal}=0.1217$ |
| `C4_F8_B1b` | `validation/C4_F8_B1b.json` | 2026-10-14 10:41:24 PDT | PASS | 7/7 | measurement | 1004 s | n/a (CI) | Class 4 run F8_B1b (E8 x IR-L3-RZZ, sector B=1, S3 quota half b), part 1 of 2 | PASS 7/7 (job 59780919): 50004 shots; $E_R-E_0=3.99\times10^{-4}$; Weinstein width $5.53\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 1.000; $W=0.999945$; pooled $k=1$ $f_{\rm hit}=0.1359$ [0.1292, 0.1428], $\hat f_{\rm ideal}=0.1219$ |
| `C4_PART_09` | `validation/C4_PART_09.json` | 2026-10-14 10:41:12 PDT | PASS | 8/8 | measurement | 1008 s | n/a (CI) | Class 4 run F8_B1b (E8 x IR-L3-RZZ, sector B=1, S3 quota half b), part 2 of 2 | PASS 8/8 (job 59782656): 49992 shots; $E_R-E_0=7.72\times10^{-4}$; Weinstein width $7.51\times10^{-2}$; $E_0$ inside yes; recall $S_{999}$ 0.989; $W=0.999890$; pooled $k=1$ $f_{\rm hit}=0.1353$ [0.1287, 0.1422], $\hat f_{\rm ideal}=0.1214$ |
| `Q0P_2x2` | `validation/Q0P_2x2.json` | 2026-10-13 15:01:52 MDT | PASS | 5/5 | measurement | 68 s | 0d7f4c5 | `prompts/35` tier T1 at 2x2: the 28 + 2 signed circuits compiled to the Quantinuum native gate set, verified exact, costed | PASS 5/5: max $\lvert\Delta\psi\rvert=7.21\times10^{-14}$, leakage $2.43\times10^{-14}$; 252 ZZPhase on all 28 (k-independent), PhasedX 405-425; 0.6109 HQC/shot; gate-only $f$ H2-2 0.7929, Helios-1 0.8046, H1-1 0.7560, H2-1 0.7429; D3' plan 13 990 / 13 563 / 14 233 / 14 660 HQC; Q7 pytest 625 / 655 passed (Section 9) |
| `QN_2x2` | `validation/QN_2x2.json` | 2026-10-13 19:42:46 MDT | PASS | 5/5 | measurement | 18 924 s | 1691220 | Tiers T2 + T3 at 2x2: noiseless 5-sigma test; 308 f-cells (28 circuits x 11 Quantinuum scenarios x 2 000 shots); plan-of-record SKQD under E1, E3, E4, E5b | PASS 5/5: 514 states, max $z=3.59$, 0 failures; noiseless recall 1.0, $E_R-E_0=0$; mean $k=1$ $f_{\rm hit}$ E1 0.838 (E3 0.767, E6c 0.500, E7(0.10, lattice-matched) 0.176); E1 all-circuit reference hits 22 751 against 24 433 expected at the 2x3 $r_{nc}$, band [24 127, 24 740]: "tension" (information); plan-of-record runs recall 1.0, $E_R=E_0$, accepted 0.79-0.87 (saturated, $Na/\dim$ 16.97 / 15.72) |
| `QEMU_2x2` | `validation/QEMU_2x2.json` | 2026-10-13 13:13:49 MDT | PASS | 3/3 | measurement | 0 s (assembled) | e3997bc | Tier T4 at 2x2: Quantinuum's offline local emulator H2-1LE (pytket-pecos, noiseless) | PASS 3/3: 28 circuits x 785 shots, 0 per-state failures, max $z=2.90$, 0 outside the support; per-circuit 0.027-0.084 s/shot |
| `QH_2x2` | `validation/QH_2x2.json` | 2026-10-13 15:10:37 MDT | PASS | 4/4 | measurement | 0 s (assembled) | c272e2a | Tier T6 at 2x2: the circuits as Guppy/HUGR programs on the Selene emulator (Helios software route) | PASS 4/4: 28/28 HUGR packages; 1 599 shots per circuit, 0 failures, max $z=3.67$; `CAL_x0` gives key 1 in 10 of 10; HUGR-to-pytket round trip "not available in tket 0.13.2" (recorded) |
| `QH_2x3` | `validation/QH_2x3.json` | 2026-10-13 16:20:04 MDT | PASS | 4/4 | measurement | 0 s (assembled) | 0265bf8 | Tier T6 at 2x3 (information): two circuits on Selene | PASS 4/4: `B0_ref25_k1` and `B1_ref57_k1`, 10 shots each at 158.0 and 145.6 s/shot, 9 reference hits each, 0 failures, max $z=2.66$ |
| `QEMU_2x3_laptop_smoke` | `validation/QEMU_2x3_laptop_smoke.json` | 2026-10-13 16:31:09 MDT | PASS | 2/2 | measurement | 0 s | 37ce8ad | Smoke test of the `C3_LE` engine path (H2-1LE) on the laptop at 2x3, one shot per circuit | PASS 2/2: 98.3 s per shot at 20 qubits; 0 strings outside the sector; not the `C3_LE` token |
| `Q0P_2x4` | `validation/Q0P_2x4.json` | 2026-10-13 23:59:18 MDT | FAIL | 4/6 | measurement | 6 228 s | faf8a10 | Tier T1 at 2x4: two native sources (qiskit opt-3, 19 circuits; structured IR, 60 circuits) converted, proven equal to their IR by local equivalence (Q1L), costed | **FAIL by construction** (`status_reason`: Q1 not measured on the laptop, deferred to GPU slot `QV_2x4_01`); Q1L PASS 79/79 ($4.4\times10^{-15}$ half-turns, segment residual $8.04\times10^{-13}$); $B$ max $4.98\times10^{-9}$ (opt-3) and $6.71\times10^{-12}$ (structured); ZZPhase 69 676 / 71 548; 157.5 / 185.4 HQC/shot; Q7 FAIL on one test (`C2_KCHK` dry run) |
| `QN_2x4` | `validation/QN_2x4.json` | 2026-10-14 00:30:46 MDT | PASS | 2/2 | measurement | 0 s | faf8a10 | Tier T3 at 2x4, analytic only (0 shots) | PASS 2/2: 79 circuits x 11 scenarios x 4 devices; E1 $\log_{10}f_0$ -26.1 (structured) to -24.4 (opt-3); gate-only $f$ H2-2 $5.8\times10^{-27}$ (opt-3) / $4.2\times10^{-29}$ (structured) |

**Reading the failures.** The FAIL rows are of six kinds and none is a hidden defect: (1) *cost gates that were deliberately re-defined* (S2, S2_fixed, S2D, L3): the manual's gate-count budget was replaced by the amended device-resolved budget; (2) *calibration/measurement gates whose FAIL records an honest negative physics result* (H0_canary, H0_kpilot, S2D_idle); (3) *diagnostic gates failing one prediction-comparison criterion while answering their own question* (H0_diag, H0_diag_dryrun); (4) *by-construction* failures (S3_smoke at 2 shots per circuit, the two early laptop L4 records, and **`Q0P_2x4`**, which the planner ruled FAIL until the GPU measures the $10^{-10}$ bar, `prompts/35b` R3); (5) *budget failures of the Perlmutter campaign*, where the physics criteria PASS and only "all requested shots were taken" (S6) fails: `C4_FCELLS_A` (10 of 42 f-cells), `C4_CF` (1 232-1 262 of 2 000 trajectories), and **`C4_PART_02` and `C4_PART_04`** (45 696 of 49 984 shots each, Section 7.9); (6) **an infrastructure failure that left a decision undecided**: `C2_KCHK` (the CPU reference arms drew 0 shots because the CPU process was bound to one core, Section 8.7). Records are never rewritten; a corrected analysis is a new gate or a new run of the token (`C2_KCHK` run 2 per `prompts/33e` R2 will archive run 1 byte-identically, as was done for `C2_CAL` run 1).

### 5.2 Gates that are still open (no JSON; from `validation/gates.md`)

| gate | check (manual Step 10) | runs on | status on 2026-10-15 |
|---|---|---|---|
| H0 | 2x2 hardware: decoder validity, bit order, parity checks; measured $f$ within 30 % of the model | QPU | open as a gate; its role was realised by the measurement gates `H0_canary`, `H0_diag`, `H0_kpilot`, `H0_ddtest`, `H0_2x2` and `H0_ddrep` (the replication that did not confirm the XY4 gain) |
| H1 | 2x3 $B{=}0$: certified interval of width $\le0.1$ containing the exact $E_0$; recall $\ge0.8$ | QPU | open (no usable 2x3 hardware data; in simulation every class-4 $B=0$ run meets it, Section 7.8) |
| H2 | 2x3 $B{=}1$: cluster energy certified to $\pm r_H\le0.15$; $V(1)$, $V(2)$ intervals containing exact values | QPU | open (in simulation every class-4 $B=1$ part has Weinstein $r_H$ 0.036-0.089, Section 7.8; $V(1)$, $V(2)$ need the static sectors, which have no plan) |
| P1 | primary-endpoint curves with bootstrap bands | laptop | open (needs 2x3 hardware data) |
| M1 | ML uses credited only under Step 7.5 | desktop GPU | open |
| `C2_XY4`, `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH` | class-2 cells of campaign 33 | Perlmutter | not requested; blocked on the class-2 representation decision (`C2_KCHK` run 2, `prompts/33e` R4) |
| `C3_LE` | the vendor's local emulator on Perlmutter | Perlmutter | not requested (needs the owner's `skqd-pecos` environment) |
| `QV_2x4_01..08` | GPU statevector check of the 2x4 native circuits (the $10^{-10}$ bar) | Perlmutter | not requested (planned after the campaign-33 must-run set or after the maintenance; needs the owner's allowlist file `ci/allowed_jobs.q35` installed on Perlmutter) |
| `C33_campaign` | assembly of campaign 33 (merged split runs, CV0-CV5 on merged runs, P15) | laptop | not run on real data (only the dry assembly `validation/dryrun/C33_campaign.json`) |

### 5.3 Other result files in `validation/`

| file | content | key numbers |
|---|---|---|
| `validation/S2_2x4_gpu.json` | the GPU stage of gate S2_2x4 on Perlmutter (no `status` field) | job 59162991, leakage $1.10\times10^{-12}$; peak GPU memory 4 557 MiB, mean utilisation 60 % (`prompts/LOG.md`) |
| `validation/QEMU_2x4.json` | status `infeasible` (no criteria) | the local emulator needs 51.9 s/shot at 20 qubits for 2 158 ZZ; 2x4 has 32.3x the ZZ gates on 256x the amplitudes, and H2-1LE models a 20-qubit machine (`data.numbers`) |
| `validation/QH_2x4.json` | status `not attempted` (no criteria) | a 28-qubit Quest statevector is $2^{28}$ complex128 = 4.3 GB per state on the laptop (`data.reason`) |
| `validation/QSC_prepared.json` | status `prepared` (no criteria): five syntax-check job sets for Quantinuum's free syntax checkers, records only | H2-2SC x 2x2 (30 jobs), 2x3 (46), 2x4 opt-3 $k=1$ (17), 2x4 structured $k=1$ (17); Helios-1SC x 2x2 HUGR (29); 0 HQC; needs the owner's Nexus login |
| `validation/C33_<run>_part2of2.json` (11 files) | **byte copies of the part-slot results under their content name** (`C33_F4_B0a_part2of2.json` = `C4_PART_02.json`, etc.); the assembly reads these copies, never `C4_PART_NN.json` (`ci/parts/README.md`) | not counted separately in the gate table |
| `validation/ci_gate_<TOKEN>.json` (25 new: every new C4 token and `C2_KCHK`) | CI wrappers: `exit_code`, `pass`, `seconds`, `jobid`, `code_sha`, `request_sha` | e.g. `ci_gate_C2_KCHK.json`: exit 1, pass False, 2 355 s, job 59780907, code sha `f4c71e8d`; block (a2) lists all |
| older CI wrappers, `ci_smoke.json`, `archive/C2_CAL_job59491475.json` | unchanged since 2026-10-13 | see the 2026-10-13 report's Section 5.3 (carried in block (a2)) |
| `validation/dryrun/*.json` (43 files; 41 on 2026-10-13) | laptop dry runs (reduced shots; **path checks only, not evidence about any model**); new: `dryrun/C2_KCHK.json` (FAIL on S2 only: 1 152 s against the dry budget), `dryrun/QV_2x4_01.json` (PASS 4/4 at 2x2, the same JSON structure as the GPU job) | -- |
| `validation/BLOCKED.md` | local (gitignored) list of the open STOP questions | not read as evidence |

### 5.4 Totals

Counting the gate JSON files with a criteria list (a python snippet over `validation/*.json`, excluding `ci_*` and the `C33_*` content copies): **87 files, PASS 69, FAIL 18** (sum of sourced statuses). On 2026-10-13 the same count gave 54 files, 40 PASS / 14 FAIL. The 33 new files: 25 campaign-33 GPU results (`C2_KCHK` FAIL; 24 class-4 run files, of which `C4_PART_02` and `C4_PART_04` FAIL on S6 only; note that `C4_F1_B0`, `C4_F7_B0`, `C4_F5_B1` and `C4_PART_01` were harvested at 17:07-18:07 UTC on 2026-10-13, after the previous report's text was written, and are counted as new here) and 8 Quantinuum-tier gates (`Q0P_2x4` FAIL by construction; `Q0P_2x2`, `QN_2x2`, `QEMU_2x2`, `QH_2x2`, `QH_2x3`, `QEMU_2x3_laptop_smoke`, `QN_2x4` PASS). So $40+29=69$ PASS and $14+4=18$ FAIL (sum of sourced numbers). The 18 FAILs: `C2_KCHK`, `C4_CF`, `C4_FCELLS_A`, `C4_PART_02`, `C4_PART_04`, `H0_canary`, `H0_diag`, `H0_diag_dryrun`, `H0_kpilot`, `L3`, `L4_p2_1e-3`, `L4_p2_3e-3`, `Q0P_2x4`, `S2`, `S2D`, `S2D_idle`, `S2_fixed`, `S3_smoke`. Not counted (no criteria): `QEMU_2x4` (infeasible), `QH_2x4` (not attempted), `QSC_prepared` (prepared), `S2_2x4_gpu`. **Of the 18 FAILs, 6 are budget/infrastructure/by-construction failures of 2026-10-07 to 10-14 whose physics criteria pass** (`C4_FCELLS_A`, `C4_CF`, `C4_PART_02`, `C4_PART_04`, `Q0P_2x4`, `C2_KCHK` [MINE classification]). Appendix block (a) is the machine-readable version.

Three further campaign results are not in the table because they were not produced as gate files (carried over): the **C2_CAL run 2** record (job 59570318, FAIL 8/12, overwritten by run 3; only `reports/ci-59570318.out` survives) and the three jobs of 2026-10-07/08 that died after 15-21 s on a missing `threadpoolctl` (`C1_IDEAL` 59491455, `C3_AER` 59491462, `C4_FCELLS_A` 59491480).

## 6. The chronological history to 2026-10-15

Sources (updated 2026-10-15): `prompts/LOG.md` (the execution log, every row cited with its commit), `reports/SESSION_HANDOVER_20260921_24.md`, `reports/SESSION_HANDOVER_20260925_1002.md`, `CLAUDE.md` ("Current status"), `reports/H0_2x2_full_hardware_report_20261002.md`, the gate JSONs named in each item. Each item gives: date, what was done, numbers, verdict, QPU seconds. "QPU s = 0" means no quantum computer was used.

### 6.0 The prompts (the plans in force), by number and title

The project's own scheme: the planner agent writes numbered prompt files `prompts/NN_slug.md`; the executor follows the newest prompt for its step. Titles (first line of each file):

| no. | title |
|---|---|
| 00 | Bootstrap: check the package, create the public GitHub repository, push |
| 01 | L1: reproduce the cloud-verified gates on the laptop |
| 02 | L2: Qiskit circuits reproduce the numpy reference (2x2, 12 qubits) |
| 03 | L3: transpiled CZ counts of the exact circuits (measurement for gate S2) |
| 04 | L4: Aer noise-model sampling at 2x2 (gate S3 preparation) |
| 05 | L5: CUDA-Q version of the 2x2 circuits on the GTX 1060 Max-Q |
| 06 | S2-b: structured hopping gates and interior-corner plaquette gates within the CZ budget |
| 07 | H0: first QPU session, 2x2 calibration run (12 qubits) |
| 08 | One-month plan to H1/H2 (2x3 hardware spectroscopy) with the gate table |
| 09 | L4 fix (2026-09-14): honour the 30-minute rule when the circuits carry about 35 000 CZ |
| 10 | L5 fix (2026-09-14): CUDA-Q 0.15.1 `SampleResult` API in the convention tests |
| 11 | S2 planner decision (2026-09-15): the exact coarse step cannot meet the CZ budget in this encoding; measure the floor, then the owner decides |
| 12 | Combined plan: 2x2 on Heron, 2x3 exact circuits on an all-to-all device; device-resolved budgets, shot rule, S3 preparation |
| 13 | H0 preparation on Heron (gate H0P) and the S3 desktop job |
| 14 | H0P fix (2026-09-16): the yield model must include the manual's garbage-acceptance term |
| 15 | H0: first QPU session on ibm_fez (2x2 calibration run, manual Step 9.1, gate H0) |
| 16 | H0P_ibm_fez fix (2026-09-21): the shot plan must guarantee the saturation that criterion 3 presupposes |
| 17 | H0 submission window (2026-09-22): the preflight must test the calibration CONTENT of the frozen patch, not its timestamp |
| 18 | Proposed GPU allowlist lines for S3 and H0P (owner action on Perlmutter) |
| 19 | H0 canary NO-GO: diagnostic session on ibm_fez (idle-time model, DD/twirling factorial) |
| 20 | H0 re-plan: the clean-yield statistic, the scheduled-Aer prediction at both ends of the $T_2$ bracket, the post-diction gate H0_model, and the free device survey |
| 21a | Ruling on the Part-D STOP of prompts/21: the dry-run K3 on the FakeKingston snapshot |
| 21 | The ibm_kingston pilot: in-circuit $T_2^*/T_2^{\rm echo}$ on the selected patch and the direct $f_{\rm clean}$ of the best schedulable signed circuit (gate H0_kpilot); part 0 applies the C6 ruling to S2D_levers |
| 22 | 2x4: compile the coarse step to exact circuits, measure its duration and idle budget, derive the device requirement |
| 23 | 2x2 on IBM: measure the duration levers and decide what the signed $f\ge0.1$ criterion needs |
| 24 | IBM 2x2 inside the 571 s: Stage T (dynamical-decoupling A/B test, gate H0_ddtest) and Stage R (the full 2x2 SKQD run, gate H0_2x2) |
| 25 | 2x3 and 2x4: the ibm_kingston readiness check (gate K0_2x3_2x4) and the IonQ preparation (gates I0P_2x3, I0P_2x4) |
| 26 | The signed 2x3 circuits for Quantinuum H2-2 / Helios-1 (gate Q0P_2x3): native compilation, exact verification, emulator and submission path, cost sheet |
| 27 | A substantial 2x3 result: the staged plan (simulator stages first, then the device question) |
| 28 | The 2x3 shot rule (D3'-R) and the clean-fraction estimator: decisive trajectory test, tail-class statistic, Stage E / P GO rule, 2x2 information block |
| 29 | Re-ruling after the CF_traj STOP ($\rho_T>1.5$): the ideal-sample fraction $f_{\rm ideal}$, the corrected reference-hit statistic, completion of CF_traj, and the amended Part B of prompts/28 |
| 30 | Energy-convergence and weighted-coverage criteria for the 2x3 plan check (owner decision 2a, 2026-10-05): definitions, constants, re-sizing rule; ruling in force until `prompts/31` amended it (the width criterion on $B_{\rm sig}$ and CV3 on the $3\to4$ step were planner errors) |
| 31 | CV_2x3_plan fix (2026-10-05): certificate basis $B_{\rm all}$ at 2x3, H1 width on Kato-Temple with the exact $E_1$, CV3 = the $k=4\to5$ step, the $B=1$ re-sizing, the 2x2 qualification reading (seven rulings; Section 6.19) |
| 32 | Owner decision 2026-10-06, option A then B: the 2x3 IBM NO-GO recorded on K0; one preregistered job on `ibm_kingston` replicating the XY4 gain and testing the mechanism of the context-aware DD collapse (gate H0_ddrep); then the K1 2x3 pilot as built (Sections 6.21, 6.22) |
| 33 | The 2x3 four-class simulation campaign on Perlmutter (ideal / IBM noise / Quantinuum-based ideal / Quantinuum-based with errors and optimisations): 33 one-GPU tokens (Section 7) |
| 33a | Campaign 33, addendum after the first CI wave: `threadpoolctl`, the C2_CAL ladder, Kraus versus Pauli-twirled thermal relaxation, re-sizing |
| 33b | Campaign 33, addendum 2: scenario-aware class-4 sizing, slot re-use, what runs before the 2026-10-21 maintenance |
| 33c | Campaign 33, addendum 3 (after wave 1 of 33b): the class-2 representation, the RM arm as a bug, C4_CF accepted as recorded, the next requests |
| 33d | Campaign 33, addendum 4: the Aer GPU Kraus path is the suspect, not the RM channel; `C2_KCHK` decides the class-2 representation (2026-10-13) |
| 33e | Campaign 33, addendum 5: `C2_KCHK` run 2 (the CPU arm on the node's CPUs), the laptop CPU reference now, class 2 after the maintenance (2026-10-15) |
| 34 | Encoding comparison: does a different qubit encoding shorten the 2x3 circuits? (gate `ENC_compare`) |
| 35 | Every SKQD circuit of 2x2, 2x3 and 2x4 tested for Quantinuum devices, tier by tier (gates `Q0P_2x2`, `QN_2x2`, `QEMU_2x2`, `QH_2x2`, `Q0P_2x4`, `QN_2x4`, `QV_2x4`; `C3_LE` and `QSC_*` prepared) |
| 35a | Rulings on the `q35` executor's three findings: Q2 ($k$-independent coarse step), pytket angle canonicalisation and the state bound $B$ (Q1L restated), the 2x2 tier-3 cap, level 0 only at 2x4 (2026-10-13) |
| 35b | Ruling on the 2x4 exactness STOP: the $10^{-10}$ bar is measured on the GPU (`QV_2x4_01`), Q1L is the conversion proof only, a structured-IR 2x4 source without qiskit opt-3 (2026-10-13) |

Also in `prompts/`: `README.md` (format), `ROUTING.md` (model routing), `ESCALATION_TEMPLATE.md`, `LOG.md`, and `low_clean_fraction_techniques.md` (the owner's literature catalogue of techniques that raise the clean fraction).

### 6.1 2026-09-14: the exact references (E1, E2, E3), S1 and CS; package bootstrap

*What.* The package was assembled in a cloud sandbox (Fable 5.1 session); Qiskit and CUDA-Q could not be installed there so only the numpy gates ran. Gates E1, E2, E3, S1 and CS all PASS (criteria 23, 51, 85, 12 and 4; Section 5). An independent audit (Opus reviewer, rebuilding the 2x2 in the 160 000-dimensional space) confirmed the physics and found fixes (CUDA-Q kernel via a real source file plus an endianness test, saturation marking in Table 3, a Kato-Temple denominator guard, CIPSI denominator magnitude, a locality check). `prompts/00`: package check, the public GitHub repository created and pushed (`https://github.com/digonto10602/su2qc-skqd`), CI run green, 14 tests passed. `prompts/01` (L1): the four gates were reproduced on the laptop (runtimes E1 427 s, E2 15 s, E3 36 s, S1 223 s; cloud 104 / 8 / 13 / 75 s); E1-E3 criteria identical to the cloud copies, S1 differs in one value only (ridge Spearman $B{=}0$: 0.862 laptop vs 0.861 cloud, threshold >0.7).
*Numbers.* The manual's Tables 1-4 are reproduced from scratch (README: "it reproduces every number of the manual's Tables 1-4"); $E_0^{2\times2,B=0}=-3.6407665507$; two builders agree to $2.3\times10^{-14}$.
*Verdict.* PASS (E1, E2, E3, S1, CS). *QPU s = 0.*

### 6.2 2026-09-14/15: the circuit layer and the laptop gates L2-L5

*L2* (`prompts/02`): Qiskit circuits reproduce the numpy reference, max deviation $3.7\times10^{-15}$ over 35 circuits in the first run (the current JSON records $2.69\times10^{-14}$), 10 000/10 000 noiseless shots decode, TVD 0.0103 (limit 0.272); CPU only (qiskit 2.5.2, aer 0.17.2; the aer-gpu wheel 0.15.1 is incompatible and was rolled back). *L3* (`prompts/03`): the dense circuits cost 35 606 CZ all-to-all and 55 459 routed on heavy-hex distance 3 against the budget of 250: FAIL as expected, the baseline for the S2 work. *L5* (`prompts/10`): CUDA-Q 0.15.1 on target `qpp-cpu`, PASS (runtime 3.6 s); the `nvidia` target aborts on the GTX 1060 Max-Q (compute capability 6.1 < 7.0). *L4* (`prompts/09`): two reduced laptop runs at $p_2=3\times10^{-3}$ (1 376 s) and $10^{-3}$ (1 012 s) FAIL the yield criterion only, because $f=(1-p_2)^{35670}$ is numerically zero for the dense circuits; both Weinstein criteria pass; noisy Aer costs 2-3.3 s per shot on this laptop so a full run would take about 7-14 h here. *QPU s = 0.*

### 6.3 2026-09-15: S2, the structured exact circuits; S2_fixed; the planner's decision (`prompts/06`, `prompts/11`)

*What.* `prompts/06` stage 1-3: the executor wrote a synthesis engine (`circuits_ir.structured_term_gates`: two-level Givens rotations per block, merged per flip pattern into Gray-code uniformly controlled rotations, control sets minimised by a search over non-codeword strings; for 2x3 the SVD of the off-diagonal part, giving real Ry rotations). 2x2 coarse step: 264 CZ at first, then 256 CZ all-to-all and 618 routed; 2x3: 2 164 all-to-all and 5 477 routed. Exactness $1.9\times10^{-14}$ (<$10^{-10}$), leakage $4.5\times10^{-14}$.
*Verdict.* Gate **S2 FAIL on the CZ budget only** (2x2 routed 618 vs $\le250$; 2x3 routed 5 477 vs $\le500$); the budget was not relaxed. The planner then (`prompts/11`, Fable at `max`) ran diagnostics (`data/S2_escalation_experiments.json`: no coupling map or term ablation reaches the budget) and asked for the floor of the *fixed-angle* alternative (same codeword pairs and validity controls, one angle per flip pattern). Result (`validation/S2_fixed.json`, `data/S2_fixed_recall*.json`): 240 / 671 / 474 CZ (all-to-all / heavy-hex / square) at 2x2 and 1 626 / 3 736 / 2 803 at 2x3; recall at $f=0.1$ kept (B=0 1.000, B=1 0.937) but the cost floor is far above budget: STOPPED as the prompt required. *Owner decision (2026-09-16):* a combined plan (2x2 on a Heron superconducting device, 2x3 exact circuits on an all-to-all ion-trap device; `prompts/12`).
*QPU s = 0.*

### 6.4 2026-09-16: S2D, L4_fez, H0P, H0_dryrun, S3_smoke (`prompts/12`, `13`, `14`)

*S2D (new gate; FAIL 6/8).* Device-resolved budgets for the exact circuits: 2x2 on the FakeFez snapshot: mean $f=0.1248$, worst $0.1166$ (663 CZ; passes $\ge0.1$ / $\ge0.05$); FakeTorino 0.0735 / 0.0569. 2x3 on an all-to-all RZZ device at *declared* inputs $\epsilon_2=10^{-3}$, $\epsilon_1=10^{-4}$, $\epsilon_{ro}=2\times10^{-3}$: 2 158 RZZ + 7 310 one-qubit gates give $f=0.1154\,(2q)\times0.4797\,(1q)\times0.9608\,(\text{ro})=0.0534$, worst 0.0532; the $\epsilon_2$ needed for $f=0.1$ at these counts is $7.1\times10^{-4}$ (with virtual $R_z$, $f=0.0817$, still <0.1). Shot rule (eq. (5), $p=10^{-3}$, $y=0.82f$): 2x3 $B{=}0$ 143 921 per circuit $\times32$ = 4.61e6, $B{=}1$ 1.72e6 per sector, against the manual's quota $2\times10^5$ per sector (FAIL); the manual itself is inconsistent: at its own design point $f=0.2$ eq. (5) already asks 1.69e6 per sector. A planner follow-up (`data/S2D_recall_at_f.json`) re-evaluated the S1 criterion at the S2D $f$: min recall 0.988 ($B{=}0$) / 0.958 ($B{=}1$) at $f=0.0534$ with $2\times10^5$ shots per sector.
*L4_fez (PASS 4/4).* Aer with `NoiseModel.from_backend(FakeFez)`: measured yield 0.1467 / 0.1356 vs model 0.1115 / 0.1038 (1.32 / 1.31), $|B|$ 38 / 20, recall 1.000.
*H0P* (preparation for the first hardware session): 84 frozen circuits (references $\times k=1..4\times r=1,2,3$ repetitions of the coarse step; plus 42 readout-calibration circuits), transpiled onto FakeFez; CZ per repetition 663 / 1 305 / 1 920; leakage $1.49\times10^{-14}$. First result (`prompts/13`) FAIL 3/16: the simulated yield was 3.0x / 8.3x / 5.6x the manual's $0.82f$ for $r=2$ ($B{=}0$) and $r=3$. Diagnosis: the decoder's false-acceptance floor, since a non-clean shot is still accepted whenever its string is a codeword of the target sector, with probability $a=0.00928$ ($B=0$) / $0.00488$ ($B=1$); the manual itself names the term ("plus the 0.15 % of garbage") but the gate scripts had omitted it. `prompts/14`: the model became $y=0.82f+(1-f)a$ (`skqd.yield_model`), after which all six simulated yields lie within 1.30-1.75x of the model; **H0P PASS 16/16**. Nothing was relaxed.
*H0_dryrun PASS 9/9* (the real analysis script run on simulator counts); *S3_smoke* (the S3 job script at 2x3, 2 shots per circuit, 295 s: FAIL by construction, 10.42 s per shot at 2 shots per call). *Amendment 01 draft* generated (91 cited values).
*QPU s = 0.*

### 6.5 2026-09-21: H0P_ibm_fez FAIL 15/16, the D3' shot plan (`prompts/15`, `16`)

*What.* `prompts/15` prepared the first real QPU session on `ibm_fez` (IBM Heron r2, 156 qubits, open plan with 600 s/month): part A built the live-backend resolution, the calibration record (`calibration_record`), the submit/retrieve split (every job id written before the next submit) and the QPU-time estimator (reproduces the planner's 46.7 s for 181 692 shots); the frozen circuits were rebuilt byte-identically (126/126). Part B recomputed the prediction on the day's live calibration (stamp 20260921T2053Z): gate **H0P_ibm_fez FAIL 15/16**; the one failing criterion: the $B{=}1$ decoded support was 19 of 20 (|E_R - E_0| = $5.749\times10^{-6}$), the missing state carrying $9.3\times10^{-7}$ of the ground-state weight. The executor held at the owner's stop point.
*Planner ruling (`prompts/16`, `reports/H0P_ibm_fez_escalation_20260921.md`).* The frozen shot plan (267/130/92 shots for $r=1/2/3$) saturates $B=0$ from clean shots with probability 0.0043 and $B=1$ with 0.0762, so the preregistered criterion 3 ($E_0$ reproduced to $10^{-6}$) was "a coin flip, not a measurement". Fix, **rule D3'** (new `scripts/h0_support_plan.py`): the $k=4$ circuits of each sector get $N_4$ = the smallest multiple of 100 such that every sector state has expected clean count $\ge\lambda^*=6.2958$ from the $r=1$ circuits at $0.7f_{\rm cal}$ (0.7 = the lower edge of the 30 % tolerance of criterion 2): $N_4=8200/19700$ on that day's calibration and 11 700/28 100 on FakeFez; two shot-plan criteria added to H0P (18 in all); session = 6 jobs of 21/5/2/28/28/42 pubs, 69.9 s of QPU execution (cap 120 s). Part A' rehearsal: **H0P_rehearsal PASS 18/18** on FakeFez with the new sampling cache (supports 38/38 and 20/20, `missing_states == []`). No criterion constant, tolerance or convention changed.
*QPU s = 0.* (Only read-only live metadata calls.)

### 6.6 2026-09-22: H0P_ibm_fez PASS 18/18, rule D9, and the first Perlmutter GPU runs (`prompts/16` part B', `17`, `18`)

*H0P_ibm_fez.* Re-run with the D3' plan: PASS 18/18 at calibration stamp 20260922T0711Z ($N_4=8100/19600$, supports 38/38 and 20/20, r=1 simulated yields 0.1707 / 0.1564, 69.69 s estimate). But `ibm_fez` recalibrated twice under the session and the preflight's exact-match guard on the `last_update_date` string refused a stale stamp each time; measured windows between recalibrations: 30 min 17 s, 36 min 8 s, 51 min 4 s, then more than 52 min. *Rule D9* (`prompts/17`): the preflight now tests the calibration **content** the prediction reads (sha256 of the 30 qubit x 9 and 54 edge x 4 values; the 84 live clean fractions equal to $10^{-9}$) instead of the timestamp; three stamp-only updates changed 0 of those numbers; the fingerprint fired on the one real recalibration (a readout recalibration of all 30 qubits, ratios 0.3735 to 2.6571, which moved $f$ of the $r=1$ circuits by only -0.68 % to +0.48 %).
*GPU runs (Perlmutter A100).* L4 job 58737320 crashed (GPU out-of-memory, 608 s: 20 circuits x 20 000 shots in one `run()` call); a memory-aware chunker (`shot_chunk_for`) and adaptive halving were added. L4 job 58741899 **PASS 4/4** (686 s; full production shots, 20 000 per circuit vs 8 / 22 on the laptop; yields 0.458 / 0.441 vs model 0.378 / 0.376; $|B|$ 38/38 and 20/20; recall 1.000): timing 0.00103 s/shot against the laptop's 0.02037 s/shot, a **19.8x speed-up**; peak GPU memory 27 915 MiB; mean GPU utilisation 15.3 % (max 27 %): not GPU-bound, so no second GPU is proposed; the allocation model underestimates memory by 3.5x (8.0 GB predicted, 27.9 GB measured). S3 calibration job 58771538 **PASS 4/4** (255 s job per `ci_gate_S3.json`; gate runtime 248 s, sampling wall 245 s): 0.01987 s/shot at 20 qubits vs 3.198 s/shot on the laptop (**161x**): a $2\times10^5$-shot sector is 1.10 h instead of 177.7 h; recall criterion not evaluated. `prompts/18` proposed the allowlist lines `S3 04:00:00 1` and `H0P 01:00:00 1` with the measured justification.
*QPU s = 0.*

### 6.7 2026-09-22: the ibm_fez canary (first QPU job) and its NO-GO

*What.* Job `dapbusac505c73chv0og` on `ibm_fez`, 2026-09-22 17:48:32 UTC: 3 pubs x 267 shots (one frozen $r=1$ circuit `B0_ref06_k1_rep1` of 663 CZ + the two readout pubs), runtime options XY4 dynamical decoupling on and Pauli twirling on. Calibration fingerprint equal at prediction and retrieval.
*Numbers.* 8 accepted of 267 shots against the preregistered go rule $\ge10$ (`validation/H0_canary.json -> data.f_comparison`: measured yield 0.02996, predicted yield 0.18725); yield-inverted $f=0.0255$ against the gate-only prediction $0.2195$ (relative deviation 0.884 against a tolerance 0.30). Bit-order test: 2 reference-string hits vs 0.07 from garbage ($z=7.6$). Readout error drift ratio 3.516 against a limit of 3.
*Verdict.* **Canary NO-GO**: gate H0_canary FAIL 3/6; the main 6-job submission was never run (`prompts/07` clause (b), `prompts/15` escalation B5). *QPU s = 2.0* (billed, `data/hardware/H0_ibm_fez_canary/session.json -> total_usage_s`).

### 6.8 2026-09-22: H0_diag, the idle-relaxation finding (`prompts/19`)

*What.* The planner's analysis (`reports/H0_canary_planner_analysis_20260922.md`) identified the cause by computation before spending hardware: neither prediction path knew how long the circuit takes. The canary circuit runs **43.71 $\mu$s at depth 1 328 for only 663 CZ** (nearly serial), each of the 12 qubits idling 19-42 $\mu$s; thermal relaxation over those windows is **3.323 error units** (S_T1 0.755, S_T2 2.568; qubit 146 with $T_2=16.0\ \mu$s alone 0.93) against the 2.15-2.36 missing from the prediction. Four jobs on `ibm_fez`, a $2\times2$ factorial of the frozen canary circuit: J1 (DD off, twirling off) `dapegkcak42c73cierv0` 5.0 s, J2 (XY4) `dapeh3318flc739m51e0` 4.0 s, J3 (twirl) `dapeh7ac505c73ci2o60` 3.0 s, J4 (both = the canary's own options) `dapehb4ak42c73cietig` 3.0 s (2026-09-22 20:42-20:44 UTC), 2 000 shots each, plus windowed $T_1$ and Ramsey pubs.
*Numbers.* The decisive count: J1 gave 35 accepted of 2 000, against the preregistered 30.8 $\pm$ 5.5 under hypothesis A (idle relaxation) and 374.5 $\pm$ 17.4 under hypothesis B (the sampler options caused the shortfall): B rejected at about 20 sigma. Factorial accepted counts 35 / 27 / 25 / 17 (J1 / J2 / J3 / J4; garbage floor 18.6); neither option helps. Windowed Ramsey: in-circuit $T_2^*$ far below the record's echo $T_2$ (median ratio 0.174 over nine measured qubits, `validation/S2D_idle.json -> data.t2_bracket.fallback_ratio`).
*Verdict.* Gate **H0_diag FAIL 6/8** (C5, the analytic post-diction, misses by 88.6x and 12.0x because the bound over-charges) but decisive on its question (C3). *QPU s = 15.0* (5+4+3+3).

### 6.9 2026-09-22/23: the clean-yield correction and S2D_idle (`prompts/20`)

*The correction to the correction.* The re-plan found the *accepted* shots were mostly **near-clean** strings (a few errors, still decoding as valid), not clean shots. The canary circuit should give one specific reference string about 88 % of the time (ideal probability 0.8833), and J1's 16.4 accepted shots above the garbage floor should have contained 15.0 of it; they contained 2 ($P=3.9\times10^{-5}$). 13 of the 35 accepted strings were distance-2 codewords of ideal probability 0. Pooled over the five hardware pubs of that circuit: **6 reference-string hits in 8 267 shots against 2.02 expected from garbage ($z=2.80$, $P=0.0172$): $f_{\rm clean}=6.65\times10^{-4}$** (1 sigma 2.6e-4 to 1.1e-3), which is **15 times below** the yield-inverted 0.0101; the measured in-circuit error budget $S_{\rm eff}=5.76$ (5.28-6.71) lies between the echo-$T_2$ prediction 3.32 and the $T_2^*$ prediction 7.52, so "31 predicted vs 35 measured" had *not* validated the echo-$T_2$ model. Criterion 3 ($E_0$ to $10^{-6}$) is void as a device test: garbage saturation reaches it at every planned budget (it measures the decoder, gate E2). The programme statement: **r=1 only at 2x2** on this device class (r=2 and r=3 predict clean fractions about $5\times10^{-6}$ and $2\times10^{-8}$); the manual's Step 9.1 yield-versus-CZ ladder cannot be delivered; Step 9.2's premise ($f\approx0.2$ at $\le500$ CZ) never held for these circuits on any quoted device; **2x3 on any superconducting device is dead**.
*S2D_idle (new gate).* Gate S2D's 2x2 criterion re-evaluated on the idle-aware $f$ at both ends of the $T_2$ bracket, FAIL 6/15: live `ibm_fez`, echo $T_2$: mean $f=6.708\times10^{-3}$, worst $1.542\times10^{-3}$; measured $T_2^*$: mean $1.298\times10^{-5}$, worst $3.40\times10^{-7}$; the most favourable point of the whole bracket (live record, echo $T_2$, DD refocusing perfectly) gives mean $0.0623<0.1$. **The 2x2 PASS of S2D is withdrawn as a hardware statement** (`validation/S2D.json` itself is not rewritten).
*QPU s = 0.*

### 6.10 2026-09-23: amendment 01, items 1-3 signed (`proposal/amendment_01_devices_and_budgets.md`)

*What was signed (owner, commit `336a60b`).* **Item 1:** the 2x2 patch is chosen by the idle-aware objective (`scripts/h0_patch_select.py`: exhaustive embedding search scored by $f_{\rm gates}e^{-S_{T1}-S_{T2}}$), not by the transpiler's calibration-aware layout; the transpiler's patch was the exact maximiser of the *gate+readout* $f$ on every record tested (optimal for the wrong objective); the winner swaps qubit 146 ($T_2=16.0\ \mu$s) for 140 ($T_2=36.0\ \mu$s), worth **1.41x** on the day's record and **3.31x** device-wide on `ibm_fez`, "a factor, not a rescue". **Item 2:** $f$ is read on the *scheduled* circuit (thresholds 0.1 / 0.05 unchanged); a device is assessable only if it declares gate durations and $T_1/T_2$ with the error rates; the 2x2/Heron leg **fails** the signed bar (mean idle-aware $f=6.71\times10^{-3}$). **Item 3:** the exact family is kept, judged on duration rather than gate count: the fixed-angle generator is 2.2 % shallower in DAG depth but 3.7 % *longer* in time and loses 1.34x in $f$; re-scheduling headroom is bounded at 7.03x and is unattainable (1 of 15 term pairs disjoint; changing it needs a new codeword layout, re-opening E1-E3). **Items 4 (the 2x3 device) and 5 (the shot quota) remain open** (item 5's shot figures scale as $1/f$). `scripts/make_amendment.py --check-only` verified 221 distinct cited values at that time.
*QPU s = 0.*

### 6.11 2026-09-30: the nine owner decisions and gate H0_model (`prompts/20`)

*The owner's rulings* (`data/H0_replan_owner_decisions.md`; nine approved, none amended, none rejected): **D8'** runtime DD off, twirling off by default; **D1'** patch by the idle-aware objective, circuits re-frozen on one patch; **D3'-f** rule D3' unchanged but fed with the idle-aware/measured clean fraction; **D3''-H0** for gate H0 only, size the shortest-depth circuits for the clean-fraction statistic (about $140/f_{\rm clean}$ shots); **D5'** the canary becomes a measuring pilot (Ramsey at two waits, $T_1$, two Krylov depths, options off); **C2'** the criterion-2 statistic becomes the maximum-likelihood clean-shot (mixture) estimator; **C3'** every shortest-depth circuit must show its reference string at least 3 sigma above accidental acceptance (the bit-order test), criterion 3 kept but labelled "not a device test"; **H0P-Y'** the factor-3 band becomes a bracket (analytic bound $\le$ scheduled simulation $\le$ unscheduled simulation); **M4.4** the manual's Step 4.4 yield model gains the near-miss acceptance term and eq. (5) takes the clean fraction ("the second contradiction found in that document", after the shot-budget sentence that asks for 32 circuits at $2\times10^5$ shots while its own formula demands 1 228 448).
*Gate H0_model PASS 5/5.* Scheduled Aer at the *measured* free-induction $T_2^*$ post-dicts the clean count already measured on hardware: predicted 4.18 clean reference hits vs 3.98 observed (**ratio 1.0503**); at the record's echo $T_2$ it predicts 197.4 (**49.58**); distance-histogram $\chi^2$ 16.9 vs 940.0. The prediction of record for 2x2 on a Heron is therefore Aer on the *scheduled* circuit at the *measured free-induction* $T_2^*$ read with the *clean-yield* statistic; dropping any of the three gives an error of 15-50x. `h0_submit.py` defaults now off (owner instruction: "change it so that it does not default to on everytime", commit `bb5a8fd`). *Free device survey* (`reports/H0_device_survey_live_20260930.md`, 0 QPU s): $T_2$ geography on 2026-09-30: median $T_2$ 92.2 / 78.1 / 141.2 $\mu$s (fez / marrakesh / kingston); winning 12-qubit patches by echo-end PTA clean $f$: fez 0.01995, marrakesh 0.004627, **kingston 0.05622** (kingston patch `[82, 83, 96, 102, 103, 104, 105, 106, 107, 117, 125, 126]`; D3' execution 96 s at that $f$). *QPU s = 0.*

### 6.12 2026-09-30 to 2026-10-01: S2_2x4, the 2x4 compilation (`prompts/22`), Perlmutter job 59162991

*What.* The 2x4 lattice (28 qubits, 14 term groups; `plaq1` acts on 16 qubits, 1 831 local codewords) was compiled with the *unchanged* structured engine: all terms synthesised and verified, max deviation $3.40\times10^{-14}$; no non-bipartite block; no generic fallback; 71 520 IR CX gates for the coarse step of which 66 468 (93 %) are in `plaq1` alone (5.1x the whole 2x3 step in one term); 69 688 CZ all-to-all, 145 958 / 148 850 routed on heavy-hex d=5 / d=7, 148 726 routed on the FakeFez map; fixed-angle 14 048 all-to-all. Duration of the all-to-all circuit 7 920.6 $\mu$s (qubit-time utilisation 0.058) and the requirement **$T_2/t_{2q}=638\,742$** at $f=0.1$ ($T_1\to\infty$; serial-formula 423 712; FakeFez-routed 858 529) against Heron's harmonic mean of 1 038. A 28-qubit dense run is priced and rejected (hours per circuit even at 62 GiB), so verification used an exact sparse simulator regressed to $1.49\times10^{-15}$ (2x2) / $9.71\times10^{-15}$ (2x3) vs the IR path and $1.11\times10^{-16}$ vs a dense $2^{28}$ cross-check. The gate failed 11/12 on the laptop (criterion C6, the leakage of the level-3 transpiled 28-qubit circuit of 279 083 instructions, not computable there). A QPY version-13 file was written for Perlmutter's qiskit 1.4.3; CI job **59162991** (A100, 99 s job, 88 s stage; Aer statevector 64.9 s, peak 4 557 MiB, mean utilisation 60 %, about 300x the laptop; the laptop estimate was 5.4 h): C6 leakage **$1.10\times10^{-12}$** (<$10^{-9}$) and the gate became **PASS 12/12**. The planner's measured numbers corrected one of its own earlier extrapolations. *QPU s = 0.*

### 6.13 2026-10-01/02: S2D_levers and the ibm_kingston pilot H0_kpilot (`prompts/23`, `21`, `21a`)

*S2D_levers (`prompts/23`).* The question was re-framed from "halve the duration" to "what does the kingston patch's $T_2^*$ have to be". Measured offline: ALAP scheduling with explicit delays is a parameter-free 1.3-4.9x lever; the best row `L4_all` (reordered terms, fractional $r_x/r_{zz}$) has duration **0.710x** the as-is canary; Aer $f_{\rm clean}$ 0.2426 (echo end) and 0.0278 (ratio 0.174), whereas the signed default-order family scheduled ALAP (`L1_seed_alap`) gives **0.2170 / 0.0312**, so ALAP + re-seed + patch, not the family change, carries almost all of it. $r_{\rm crit}(0.1)\approx0.329$ (Aer) / 0.726 (analytic bound). First run FAIL 8/9 on criterion C6 (one information cell, a 1.65 sigma estimator deviation); the planner's ruling (`reports/S2D_levers_C6_ruling_20261002.md`) scoped C6 to cells with $p_{\rm ref}\ge0.5$ (tolerance 0.25 and the 20-hit floor unchanged); re-assembly on the same counts gives **PASS 9/9** (worst in-scope deviation 0.0987).
*Pilot (`prompts/21`; dry run K3 ruling `21a`; gate H0_kpilot).* One job, `davv8504oijs73e88fvg`, `ibm_kingston`, 2026-10-02 18:12:35 UTC, 8 pubs x 4 000 shots on the patch `[59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]` (selected by the exhaustive embedding search on the day's record), runtime DD and twirling off (D8'), fingerprint `ec74eb8bf15dde41` at preregistration, submission and retrieval; billed **12.0 s** against an estimate of 9.04 s and a 30 s cap. *Numbers:* pooled direct clean fraction of the two $k=1$ circuits **$f=0.0413$, 95 % [0.0361, 0.0470]** (242 reference hits vs 1.95 from garbage); `B0_ref06_k1` 0.0404 [0.0332, 0.0486], `B1_ref07_k1` 0.0422 [0.0349, 0.0505]; $r_{\rm eff}=0.0974$ (68 % [0.0879, 0.1022]) against $r_{\rm crit}=0.3285$ (the day's grid 0.2788); the circuit's own $f$ corresponds to an equivalent dephasing ratio of about 0.17, the same as `ibm_fez`'s 0.174. *Verdict:* **NO-GO** on the preregistered rule (upper end below 0.1; the planner had predicted NO-GO in writing); gate **FAIL 8/9 on K5 only** (the windowed Ramsey gave readout-corrected $P_0<\tfrac12$ on 9 of 12 qubits, a coherent-phase (detuning or static-ZZ) signature that this design cannot separate from decay; $T_2^*$ "measured" on 9/12 < 10 required). *QPU s = 12.0.*

### 6.14 2026-10-02: H0_ddtest, the XY4 gain (`prompts/24` Stage T)

*What.* After a literature search (`reports/ibm_decoherence_literature_20261002.md`, 25 arXiv sources: client XY4 / context-aware DD ranked first; Pauli twirling cannot raise a clean fraction because it preserves fidelity (arXiv:1512.01098); the runtime XY4 is identical on all idle qubits and cannot refocus ZZ), one preregistered job tested client-side DD against no DD on the pilot's two $k=1$ circuits: job `db01005j371s73dnmbd0`, 2026-10-02 20:11:42 UTC, 10 pubs x 6 000 shots, fingerprint `84d59cbf9b5973d1` throughout, billed **20.0 s** (estimate 17.26 s).
*Numbers (95 % intervals).* T0 (no DD) $f=0.0400$ [0.0358, 0.0446]; T1 (context-aware staggered $X$, 862 pulses) $f=0.0005$ [-0.0000, 0.0013], ratio $R=0.012$ [0.004, 0.031] against a pulse-cost null of 0.816; T2 (XY4 in every window $\ge256$ ns, 776/780 pulses) $f=0.1118$ [0.1048, 0.1192], $R=2.793$ [2.472, 3.157] (null 0.841); **T3 (XY4 only in windows $\ge1\ \mu$s, 244 pulses) $f=0.1129$ [0.1058, 0.1203], $R=2.819$ [2.495, 3.185]** (null 0.944). Readout min diagonal 0.9457.
*Verdict.* T3 adopted by the preregistered rule (largest point ratio among cells with lower interval $>1$ and $R\ge1.25$); the signed bar read **GO** on the adopted cell (on the reference-hit statistic; see the 3a qualification in Section 14); gate **PASS 8/8**. The context-aware cell **collapsed** (about 65x below its null, planner arithmetic 0.012/0.816), unexplained: its statevector and duration were verified equal to the base circuit, so the *logical* circuit is right; the planner's three untested hypotheses are in `reports/H0_2x2_full_hardware_report_20261002.md` section 3. **Both the gain and the collapse failed to replicate four days later (gate `H0_ddrep`, Section 6.21).** *QPU s = 20.0.*

### 6.15 2026-10-02: H0_2x2, the full 2x2 SKQD run on ibm_kingston (`prompts/24` Stage R)

*What.* Under the owner's decision of 2026-10-02 (`data/owner_decision_20261002_run_below_signed_budget.md`: "... start preparing to send the 2x2 circuit anyway to qpus to finish run and see result all the way through to the end, meaning the skqd run for 2x2 plaquettes using 121 s of qpu time"), the 28 coarse circuits (7 references x $k=1..4$) + 2 readout pubs ran in 5 jobs on the pilot's patch with DD cell T3, DD/twirling options off, ALAP; fingerprint `84d59cbf9b5973d1` at preregistration (commit `a5e2c09` 2026-10-02T14:38:28-06:00), submission (21:05:55 UTC) and retrieval. Jobs `db01pddj371s73dnnqm0` (3.0 s), `db01pdtj371s73dnnqmg` (3.0), `db01pe04oijs73e8cl30` (4.0), `db01pelj371s73dnnqo0` (22.0), `db01peql7guc73cfndc0` (21.0).
*Numbers* (all `validation/H0_2x2.json`, detail in Appendix blocks (c)-(e)). Shot plan by rule D3' at the adopted $f$: $N_4=13\,100$ ($B{=}0$) / 31 400 ($B{=}1$), 133 907 coarse shots in all. Pooled $f$ over the seven $k=1$ circuits (267 shots each): **0.1271, 68 % [0.1174, 0.1375], 95 % [0.1084, 0.1479]** (173 reference hits vs 0.46 expected from garbage; per circuit 0.1024-0.1390). Readout min diagonal 0.9417, survival product 0.8338. Sector support: $B=0$: 69 505 shots, 9 454 accepted, $|B_{\rm all}|=38/38$, $|B_{\rm sig}|=35/38$ (exact 99.9 % support 16); $B=1$: 64 402 shots, 7 885 accepted, $20/20$, $19/20$ (13). Energies on $B_{\rm sig}$: $B=0$ $E_R=-3.6402188765$ vs exact $-3.6407665507$ ($E_R-E_0=5.48\times10^{-4}$), $r_H=0.0603$, Weinstein $[-3.700489,-3.640219]$, Kato-Temple $[-3.641574,-3.640219]$; $B=1$ $E_R=-1.8615822852$ vs $-1.8615880345$ ($5.75\times10^{-6}$), $r_H=5.95\times10^{-3}$ (below the exact gap $E_1-E_R=0.0418$, so the gap assumption holds and the lowest cluster level is certified), Weinstein $[-1.867536,-1.861582]$, Kato-Temple $[-1.862424,-1.861582]$; every interval contains the exact $E_0$. Saturation: $Na/\dim=16.97$ / 15.72. **Controls:** garbage-only (100 seeds): uniformly random strings give $|B|=38$ and 20 and $E_R=E_0$ to $4\times10^{-16}$ in every seed: **the processor could have output white noise and the $B_{\rm all}$ energies would be identical**; random-at-equal-size (200 seeds): the hardware's $B_{\rm sig}$ energy sits at the **5.0th percentile** for $B=0$ (size 35: random mean $-3.63266\pm0.00639$) and the **28.5th percentile** for $B=1$ (size 19; only 18 distinct random bases exist, so the percentile is coarse).
*Verdict.* Gate **PASS 8/8** (a measurement gate). Publishability (planner, `reports/H0_2x2_full_hardware_report_20261002.md`): **not** publishable as an SKQD physics result; publishable as a methods note (honest sampling at a noise-saturated size) and, after replication, a short note on the XY4 finding (**the replication of 2026-10-06 did not confirm the gain, Section 6.21; the XY4 note is withdrawn, Section 14.4**). *QPU s = 53.0* (3+3+4+22+21). Account after: **102 s consumed, 498 s remaining** of 600.

### 6.16 2026-10-02: the 2x3/2x4 device question (`prompts/25`, `26`, `27`); Q0P_2x3

*K0 verdict (planner, `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md`; the 5 477-CZ circuit and the $1.14\times10^{-2}$ ceiling below are the planner's 2026-10-02 survey values, superseded on 2026-10-05/06 by gate `K0_2x3_2x4`'s exact 5 659-CZ circuit and ceilings $9.83\times10^{-3}$ / $6.72\times10^{-3}$ on the two records, Section 6.20, and by the K1 measurement, Section 6.22).* On the committed kingston record (20261002T1906Z: CZ error min $8.164\times10^{-4}$, 10th percentile $1.146\times10^{-3}$, median $1.804\times10^{-3}$; $T_2$ median 147 $\mu$s, CZ 68 ns): 2x3 routed 5 477 CZ gives a ceiling $f\le(1-\epsilon_{2,\min})^{n_{CZ}}=1.14\times10^{-2}$, below the worst-case bar 0.05 by 4.4x before one-qubit, readout and idle errors, which lower it to about $10^{-4}$: **NO-GO**; 2x4 routed 148 726 CZ needs $\epsilon_2\le2.0\times10^{-5}$ for $f=0.05$ (the best edge is 41x worse): ceiling $\sim10^{-53}$: **NO-GO**; "no 2x2 technique can change it". **IonQ** (vendor pages read 2026-10-02; `data/ionq_2x3_feasibility_20261001.json`): Forte / Forte Enterprise (36 qubits; spec 2q 0.4 %, 1q 0.02 %, SPAM 0.5 %; day-measured DRB 99.3 % / 99.5 %; T2 about 1 s; ZZ 950 $\mu$s) give 2x3 gate-only $f=8.61\times10^{-5}$ (virtual $R_z$; Aria $3.52\times10^{-5}$) with a serial-idle estimate of $e^{-22}$; Aria is retired; Tempo is a late-2026 projection whose 99.9 % target gives $f\approx0.077$, still below 0.1; 2x4 is far out of reach (and its 208 399 native gates exceed IonQ's 150 000-gate job limit). 2x2 on Forte is feasible (gate-only $f=0.303$).
*Survey and the Quantinuum route (`prompts/26`, `reports/qpu_survey_2x3_20261002.md`).* The owner asked "search internet to find which quantum device can run 2x3". Result: **only Quantinuum's QCCD trapped-ion machines** meet the signed bar on published numbers: gate-only $f$ **0.1502 (H2-2), 0.1642 (Helios-1)**, 0.1113 (H1-1), 0.0860 (H2-1); every other surveyed platform fails by 2-13 orders of magnitude (Appendix block (f)). The decisive unknown is the *memory (transport) term* of a circuit with a two-qubit critical path 1 925 gates deep; three ESTIMATE scenarios (round time 0.5 / 1.1 / 4.4 ms) give $f_{\rm mem}$ for H2-2 of 0.1454 / 0.1398 / 0.1130 and for Helios-1 0.1378 / 0.1117 / 0.0352. Cost: HQC per shot $=\;5+C(N_{1q}+10N_{2q}+5N_m)/5000$ per job; mean 4.9666 HQC per shot for the 2x3 family; an Azure Standard plan equivalent of 12.5 USD per HQC (ESTIMATE; pay-as-you-go not public).
*`prompts/27` (planner analysis `reports/2x3_qec_amplification_strategy_20261002.md`).* The owner asked whether error correction, an "amplifier" or many qubits could give a substantial 2x3 result. Answer: fault-tolerant 2x3 needs about $1.1\times10^5$ $T$ gates per shot on $10^4$-$10^5$ physical qubits (ESTIMATE): a 2029-class option (IBM Starling, Quantinuum Apollo, STAR-class), not 2026-2028; error detection by an Iceberg code is a net loss because the Gauss-law codewords are already a distance-2 detection code; there is no quantum amplifier, but *shots* are one: with the decoder and $B_{\rm sig}$ the usable clean fraction at 2x3 can drop from 0.1 to about $10^{-3}$ (cost $\propto1/f$ up to $2\times10^6$ shots per sector, $\propto1/f^2$ beyond). It defined claim tiers A/B/C (Section 14) and stages T0 (tier arithmetic), T0c (levers), 0b (a 2x3 pilot on `ibm_kingston`: the K1 pilot), S3H (Helios-class device-model GPU stage), then access and a pilot.
*Q0P_2x3 (`prompts/26` Stage A) PASS 7/7* (2026-10-02 21:36 MDT): 44 circuits compiled to $\{R_z,\mathrm{PhasedX},\mathrm{ZZPhase}\}$ with pytket and frozen with checksums, max $|\Delta\psi|=2.09\times10^{-13}$ (build $4.06\times10^{-14}$), leakage $1.29\times10^{-13}$, 2 158 ZZPhase on all 44, 2 989-3 091 PhasedX; HQC per shot 4.9538-4.9742 (mean 4.9666); **level-2 compilation is not state-exact with measurements** (max $|\Delta\psi|=0.585$ because TKET removes the $R_z$ in front of each Measure; probabilities agree to $1.6\times10^{-13}$). Stage E plan (vendor emulator): 11 936 eHQC (k=1 x1000, k=4 x200, both sectors); Stage P pilot 9 938 HQC; campaign (D3-type union reading at $0.7f$): 2.02e6 / 1.01e6 / 6.75e5 HQC at $f=0.05/0.10/0.15$. **Rule D3' is not a finite plan at 2x3**: 32 of 677 $B=0$ states and 11 of 426 $B=1$ states have total $k=4$ probability <$10^{-6}$ (min $1.2\times10^{-34}$). A local dry run of the emulator path: pooled reference-string $f=0.2502$, 95 % [0.1927, 0.3195] at 280 shots vs gate-only model 0.1502 / Aer channel 0.1722: 64 hits against 44.1 expected from error-free shots ($P=0.0028$), read as *near-clean* shots. The isolated Quantinuum venv left the `coding` pins untouched. *QPU s = 0, HQC = 0, no Nexus account.*

### 6.17 2026-10-03/05: the D3'-R ruling, CF_traj, the f_ideal re-ruling (`prompts/28`, `29`)

*`prompts/28` (planner ruling, `reports/2x3_shot_rule_estimator_ruling_20261003.md`).* Problem 1: rule D3' cannot size 2x3 ($N_4\approx8.8\times10^{35}$ at $f=0.1$); the shots exist only to put the states carrying the ground-state weight into $B$ (the manual's S1, H1, H2, P1 criteria never ask for all 677 states). **Rule D3'-R** (the project's label, "R" for recall): (a) every state of $S_{99}$ (31 of 677 in $B=0$, 42 of 426 in $B=1$) gets expected clean count $\ge\lambda^*=6.2958$ from the sector's circuits via a minimum-shot linear programme with every circuit $\ge267$ shots; (b) the $k=4$ circuits are topped up in multiples of 100 until $P(\text{clean-only recall of }S_{999}\ge0.9)\ge0.95$; yield $y=0.82\times0.7\times f$ as in D3'. Plan (planner arithmetic, prototype `scratch/planner/d3s_2x3_shot_rule_20261003.py`): $f=0.05/0.10/0.15$: 160 378 / 84 112 / 60 812 total shots, 797 157 / 418 166 / 302 382 HQC (Appendix block (g)); the D3-type union reading costs 1.01e6 HQC at $f=0.10$ with 23 / 38 $S_{999}$ states below $\lambda^*$ and $P(R\ge0.9)=0.895$ in $B=1$; D3'-S (all of $S_{999}$) 2.78e6 HQC. 2x2 is consistent and stays as recorded (min expected clean count over $S_{999}$ 30.15 / 32.76 vs $\lambda^*=6.30$; every $S_{999}$ state observed $\ge59$ / 80 times). Problem 2 (the reference-string estimator overstated $f$ in a pure gate-noise model): read as the Z-type near-clean term of M4.4, to be proved by a Pauli-trajectory decomposition (gate CF_traj) plus a bit-flip-only control to exclude a merged-gate bug.
*CF_traj, first execution (2026-10-05 Part A): FAIL (C1, C4 fail only because the STOP "$\rho_T>1.5$" truncated the run).* Physics confirmed (trajectory prediction of the A6 hits $62.58\pm2.64$ vs 64 observed, fault-free only 44.06; bit-flip control 40 hits vs predicted 45.95), but the tail-class statistic $f_T$ was inflated: $\rho_T$ up to 3.86.
*`prompts/29` (re-ruling, `Physics confirmed, f_T withdrawn`).* The returns to the reference are single Pauli events acting as a *phase* in the computational frame; most returning trajectories are at total-variation distance exactly 0 from the ideal, i.e. they are *ideal samples*. New referent: $f_{\rm ideal}(\delta)=f_0'+(1-f_0')\,b(\delta)$ (shots that sample the ideal output distribution to within TV distance $\delta$; $b$ the benign-fault fraction); $f_{\rm hit}$ is an estimator of $f_{\rm ideal}$, not of $f_0'$; $f_T$ withdrawn (noise *scattering* into low-probability states inflates it 21-39x). Budget bar refers to $f_{\rm ideal}$; the GO/sizing statistic is $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$; GO rule v3; Stage E/P v3 = 800/800/200/200 shots (about 9 950 (e)HQC). 2x2 under v3 at $r_{nc}=1.10$: the H0_2x2 "signed bar GO" reads **AMBIGUOUS** (0.103, lower 95 % 0.096).
*CF_traj completed (Part A', 2026-10-05): PASS 7/7* (`validation/CF_traj.json`, `reports/CF_traj.md`; wall 1 201 s; no STOP). Trajectories K per arm: `B0_ref25_k1` 720, `B1_ref57_k1` 240, `B0_ref25_k4` 240, `xx` arm 120; A5 (the 2x2 circuit under a twirled idle model) K=2 000 at each $T_2$ end. **$r(10^{-3})=f_{\rm hit}/f_{\rm ideal}$:** `B0_ref25_k1` 1.089 [1.050, 1.136] ($f_0'=0.17209$, $b=0.0569$ [0.0417, 0.075], $f_{\rm ideal}=0.2192$ [0.2066, 0.2342], $f_{\rm hit}=0.2387$ [0.2241, 0.2549]); `B1_ref57_k1` 1.052 [0.987, 1.126] ($f_{\rm ideal}=0.2448$ [0.2172, 0.2758]); `B0_ref25_k4` 1.115 [1.036, 1.220] ($f_0'=0.17219$, $f_{\rm ideal}=0.2205$ [0.1963, 0.2481]); `xx` 1.042 [1.001, 1.122]. **Pooled $k=1$: $r=1.069$ [1.029, 1.115] $\Rightarrow$ $r_{nc}=1.115$** (`data/cf_trajectories/r_nc.json`; commit `a8ebbaa`; the STOP $r_{nc}>1.3$ did not fire). **Floor theorem** ($f_{\rm eff}(s)\ge f_{\rm ideal}(1-2\delta/p_c)$ per state): min over $S_{99}$ of $f_{\rm eff}/f_{\rm ideal}(10^{-3})$ is 1.089 / 1.040 / 1.100 / 1.041, all $\ge0.95$. **Mixture-estimator bias at $k=4$:** 1.274 [1.170, 1.402] (inside [0.67, 1.5]). **A5 2x2:** $T_2^*$ end: $f_0'=1.64\times10^{-6}$, $f_{\rm hit}=0.0189$ [0.0139, 0.0241], $f_{\rm ideal}=0.028$ [0.021, 0.035], $r=0.674$ [0.539, 0.835]; echo end: $f_0'=0.0915$, $f_{\rm hit}=0.288$ [0.273, 0.302], $f_{\rm ideal}=0.320$ [0.301, 0.336], $r=0.902$ [0.884, 0.918] — under idle dephasing the reference-hit fraction *under*-estimates $f_{\rm ideal}$ in this model. C2: 63.46 $\pm$ 2.25 predicted vs 64 observed ($P=0.979$). *QPU s = 0, HQC = 0.*

### 6.18 2026-10-05: the owner's decisions and the Quantinuum access draft

*Decisions (`data/owner_decision_20261005_partB.md`, verbatim "1a, 2a with the convergence condition, 3a").* **1a:** the signed bar (mean $f\ge0.1$, worst $\ge0.05$) refers to $f_{\rm ideal}$, measured on a device as $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ with $r_{nc}=1.115$. **2a:** rule D3'-R is signed as the **minimum** 2x3 shot sizing (input $y=0.82\times0.7\times\hat f_{\rm ideal}$) together with the Stage E / Stage P v3 plans (800/800/200/200); condition: approval of any full 2x3 campaign additionally requires that the emulated check of the plan shows **energy convergence** (E_R and certificate width against shots and against Krylov $k$) and **weighted coverage**, under criteria the planner adds; if not met the planner re-sizes and the new cost returns to the owner; signing commits no HQC. **3a:** the 2x2 "signed bar GO" (H0_ddtest / H0_2x2) was read on $f_{\rm hit}$; under the conservative correction it may read AMBIGUOUS; external citations carry this qualification; no recorded verdict is edited. *K1 decision (`data/owner_decision_20261005_k1_2x3_fpilot.md`):* verbatim "go with step 1,2 and 3, send the 2x3 job to ibm qpu first if its ready to submit": authorises ONE preregistered K1 pilot submission on `ibm_kingston`, cap 300 s billed, under the preconditions of `prompts/27` stage 0b (gate K0 on the day's record, dry run PASS, D9 fingerprint match, QPU estimate $\le300$ s); the GO-B / GO-A / NO-GO thresholds are read on $\hat f_{\rm ideal}=f_{\rm hit}/1.115$ with $f_{\rm hit}$ reported beside it.
*`prompts/30` (planner, `CV_2x3_plan`).* Finding: coverage is checked as recall but the energy only at the final point; convergence against shots, against $k$, and weighted coverage are checked nowhere as a criterion. Defines the weighted coverage $W(B)=\sum_{s\in B}|c_s|^2$ (exact ground state of each sector; the captured weight of `support_metrics`), nested subsamples (prefixes of each circuit's shot sequence at $\phi\in\{1/16,1/8,1/4,1/2,1\}$), a Krylov curve cumulative over $k=1..4$, 200 random equal-size bases at every point, **one computed constant** $E_{\rm tol}=E_R(R\cup\text{top 80 \% of }S_{999})-E_0$ (the Ritz error H1's own recall target tolerates; planner expectation of order $10^{-2}$ from Table 3, `oracle|80` = 1.010e-2 / 1.024e-2), and **criteria CV0-CV5** (structural; shot convergence $E_R(N/2)-E_R(N)\le E_{\rm tol}$; certificate $r_H(N/2)\le0.1$ ($B=0$) / 0.15 ($B=1$) with $E_0\in[E_R-r_H,E_R]$; Krylov convergence $E_R(B^{(3)})-E_R(B^{(4)})\le E_{\rm tol}$, failure = STOP because a $k=5$ circuit is a family change; below the random 2.5th percentile with $E_{\rm rand,2.5\%}-E_R\ge E_{\rm tol}$ and weight above the random 97.5th percentile; $W(B_{\rm sig}(N))\ge0.99$) and a **re-sizing rule** (uniform multiplier $s\in\{2,4,8\}$ on D3'-R, smallest passing on prefixes of the same samples; $s=8$ failing = STOP; planner arithmetic: 418 167 HQC at $f=0.10$ becomes about 8.4e5 / 1.7e6 / 3.3e6). Stage E / P test $f$ only (two references cannot generate a support). A 2x2 information block applies the same curves to the H0_2x2 counts, labelled "not a device test (saturation)". Laptop about 1 executor day, 0 QPU s, 0 HQC. **Executed the same day; its first run failed and `prompts/31` corrected the criteria; the passing result is in Section 6.19.**
*`proposal/quantinuum_access_request_draft_20261005.md`* (a draft by the coordinator for the owner to edit; nothing sent): two routes, (A) the OLCF Quantum Computing User Program (QCUP; default emulator quota "6000 seconds"; hardware credits "must be justified using results from an emulator"; eligibility to be confirmed by the owner) and (B) Sales@Quantinuum.com for a research agreement with Nexus access; ask for the emulator first (about 10 000 eHQC: two $k=1$ circuits at 800 shots and two $k=4$ circuits at 200), then, if the preregistered rule passes ($\hat f_{\rm ideal}\ge0.10$ with 95 % lower bound $\ge0.05$), a hardware pilot of the same four circuits (about 10 000 HQC); five questions to the vendor (measured 2q error; memory error per layer for a 20-qubit mostly serial 1 900-layer program; parallel gates; how $R_z$ and PhasedX enter HQC; the HQC rate and research allocations). The full-campaign scale for the owner's planning is 3.0-4.2e5 HQC at H2-2 (prompts/28/29), a minimum under the convergence condition. *QPU s = 0, HQC = 0.*

### 6.19 2026-10-05: the 2x3 plan check (`prompts/30`, `prompts/31`; gates `CV_2x3_plan`, `Q0P_2x3_plan`)

*The question (owner decision 2a).* A campaign on the minimum D3'-R sizing may be approved only if an emulation of the plan shows **energy convergence** (the Ritz energy $E_R$ and the certificate width against shots and against the Krylov order $k$) and **weighted coverage**. Gate `CV_2x3_plan` is that emulation: the S1 proxy at clean fraction $0.7f$, 3 seeds (20260914, 1, 2), $f=0.05/0.10/0.15$, both sectors, nested subsamples at 1/16 ... 1 of the plan's shots, 200 random equal-size bases at every point. Criteria (the project's labels): **CV0** structural (nested, monotone, variational, the manual's Table 3 oracle rows reproduced); **CV1** $E_R(N/2)-E_R(N)\le E_{\rm tol}$; **CV2** certificate width at $N/2$ and $N$ meets H1 ($\le0.1$, $B=0$) / H2 ($r_H\le0.15$, $B=1$) and brackets $E_0$; **CV3** convergence in $k$; **CV4** better than random bases of the same size by at least $E_{\rm tol}$; **CV5** captured ground-state weight $W\ge0.99$. The one computed constant is $E_{\rm tol}=E_R(R\cup\text{top 80 \% of }S_{999})-E_0$, the Ritz error that H1's own recall target ($\ge0.8$) tolerates: $1.4225\times10^{-2}$ at $B=0$ (69 states of $S_{999}=86$) and $1.1040\times10^{-2}$ at $B=1$ (76 of 95) (`validation/CV_2x3_plan.json -> data.E_tol`).

*First execution: FAIL 27/36, STOP (2026-10-05, `prompts/LOG.md`).* CV2 and CV3 failed on the **width** over $B_{\rm sig}$ (the signal support) in every $B=0$ cell and CV3 at both sectors; re-sizing to $s=8$ could not rescue $B=0$. The planner's diagnosis (`prompts/31`, max effort; none of it a code bug): **D1** the Weinstein width is $r_H\approx10\sqrt{1-W}$ at 2x3, so a width $\le0.1$ needs $W\ge0.9999$ (173 states, hardest state with weight $1.8\times10^{-5}$, about $6\times10^{6}$ shots per sector by the $k=4$-scaled bound; planner arithmetic) and is unreachable even by the oracle $S_{999}$ ($r_H=0.265$, Block (r)); the manual's certified interval is Weinstein *or* Kato-Temple (Step 5.3) and the criterion had applied the Weinstein width to H1 by planner error. **D2** the $B_{\rm sig}$ cut is a saturation-regime device (2x2, $Na/\dim=17$); at 2x3, $Na/\dim=0.03$-$0.5$, it drops exactly the low-weight states the residual needs and breaks nestedness, while the manual defines $B$ as the union of accepted configurations (Step 5.1). **D3** CV3 tested the $3\to4$ step, which only shows that the $k=4$ circuits are needed; convergence is the $4\to5$ step, which can be emulated without a device (a coarse circuit has the same gate count at every $k$).

*The rulings (`prompts/31`, "Ruling", seven items) and the owner decisions.* (1) Certificates, CV1-CV5 and the D3'-R check are evaluated on $B_{\rm all}\cup$ references at 2x3; the $B_{\rm sig}$ rule (decision P9) stays for 2x2 and for the neural step's training labels. (2) CV2 at $B=0$ reads **Kato-Temple with the exact $E_1$**, at $B=1$ Weinstein $r_H\le0.15$; both thresholds unchanged. **Owner confirmation, verbatim "keep Kato-Temple for B=0, go ahead"** (`data/owner_decision_20261005_kt_certificate.md`), with the recorded caveat that this reading needs an exactly known $E_1$ (classical at 2x3, not beyond exact diagonalisation). (3) CV3 becomes $E_R(B^{(4)})-E_R(B^{(5)})\le E_{\rm tol}$ at equal shots, a failure being an owner item and not a STOP. (4) Re-sizing: the smallest $s\in\{1.5,2,3,4,6,8\}$ per sector. (5) `Q0P_2x3_plan` P3 reads recall on $B_{\rm all}$ and the ruling-2 certificate; preregistration v3. (6) The 2x2 qualification is read under the rule the verdict was preregistered with: GO on $f_{\rm hit}$, **AMBIGUOUS on $\hat f_{\rm ideal}=0.1012$ [0.0938, 0.1091]**; the v3 rule is not applied retroactively (a post-hoc rule change). (7) Decision 2a is checkable.

*Result: `CV_2x3_plan` PASS 37/37 (no STOP) and `Q0P_2x3_plan` PASS 7/7.* Table (maximum over the three seeds unless "min"; every figure from `validation/CV_2x3_plan.json -> data.criteria_by_seed, data.plan`; Blocks (q), (q2)):

| $f$ | sector | $s$ | shots | HQC | CV2 width at $N/2$ (limit) | CV3 $\Delta E_{4\to5}/E_{\rm tol}$ | CV4 margin / $E_{\rm tol}$ (min) | CV5 $W$ (min) |
|---|---|---|---|---|---|---|---|---|
| 0.05 | $B=0$ | 1 | 63 875 | 317 546 | 0.0195 (0.1, KT) | 0.218 | 7.93 | 0.99952 |
| 0.05 | $B=1$ | **2** | 193 600 | 962 114 | 0.1181 (0.15, Weinstein) | 0.264 | 4.74 | 0.99986 |
| 0.10 | $B=0$ | 1 | 34 909 | 173 614 | 0.0252 (0.1, KT) | 0.675 | 8.41 | 0.99951 |
| 0.10 | $B=1$ | **2** | 99 000 | 491 991 | 0.1433 (0.15, Weinstein) | 0.307 | 5.20 | 0.99985 |
| 0.15 | $B=0$ | 1 | 27 309 | 135 860 | 0.0267 (0.1, KT) | 0.206 | 8.36 | 0.99928 |
| 0.15 | $B=1$ | **2** | 67 600 | 335 941 | 0.1343 (0.15, Weinstein) | 0.335 | 5.83 | 0.99976 |

At $B=1$ the factor $s=1.5$ fails CV2 at every $f$ (Weinstein $r_H(N/2)=0.1568$ / 0.1669 / 0.1553 against 0.15; the $s=2$ values are 0.1181 / 0.1433 / 0.1343), so the owner decision of the same evening (`data/owner_decision_20261005_b1_x2_plan.md`, verbatim "approve the 2x shot plan for sector B=1") fixes the plan of record at $B=0$ at $s=1$ and $B=1$ at $s=2$. **Campaign HQC:** 797 157 $\to$ **1 279 660** ($f=0.05$), 418 166 $\to$ **665 605** (0.10), 302 382 $\to$ **471 801** (0.15) (`data.campaign_hqc`; the planner had expected about 663 000 at 0.10, planner arithmetic). In shots: 257 475 / 133 909 / 94 909 and 64 / 53 / 49 jobs (sum of sourced numbers, Block (g)). The $k=4\to5$ step moves $E_R$ by at most 0.68 $E_{\rm tol}$ at the plan's shots (0.0096 absolute at $B=0$, $f=0.10$), so a $k=5$ circuit (a family change) is **not** needed and that owner item disappears. The oracle-width table (Block (r)) is the report's statement of why the Weinstein width $\le0.1$ is out of reach at this family: at $B=0$ the oracle $S_{999}$ (86 states) has $W=0.99904$, $r_H=0.2647$, $\delta_{\rm KT}=0.0259$.

*What this does and does not say.* It is an emulation at a *presumed* clean fraction with the S1 proxy noise model, which Section 13 shows to be an optimistic proxy for real devices; the device number is unknown (Section 6.22). The plan is re-sized again at the measured $\hat f_{\rm ideal}$ before any campaign submission, and no HQC are committed. Stage E / Stage P (the two-reference pilots) test $f$ only: 2 000 shots, 9 949.92 eHQC (emulator) / HQC (hardware), USD 124 374 ESTIMATE at 12.5 USD per HQC (`validation/Q0P_2x3_plan.json -> data.stage_E_v3, stage_P_v3`).

### 6.20 2026-10-05/06: gate K0 and the first K1 attempt, stopped at 0 QPU s (`prompts/25` Part A, `prompts/27` stage 0b)

*K0 (model verdict).* `scripts/gate_K0_2x3_2x4.py` routes the signed 2x3 circuit `B0_ref25_k1` onto the target of a calibration record with an **exactness-gated seed rule**: the plain level-3 transpile with the fewest CZ (seed 6, 5 527 CZ) turned out *not exact* on this circuit (max $\lvert\Delta\psi\rvert=4.9\times10^{-5}$, leakage $2.7\times10^{-9}$; measured cause on qiskit 2.5.2: the level-3 loop's two-qubit peephole pass is not exact at approximation degree 1), so the chosen circuit is seed 7 with **5 659 CZ**, exact to $1.5\times10^{-12}$ (`validation/K0_2x3_2x4.json -> data.2x3.committed.routing`). (The 5 527-CZ figure in the 2026-10-05 report is the inexact circuit.) Committed record 2026-10-02: $f_{\rm ceiling,2q}=(1-\epsilon_{2,\min})^{n_{CZ}}=9.83\times10^{-3}$, gate-only on the routed layout $6.07\times10^{-6}$, idle-aware $1.06\times10^{-16}$ (echo $T_2$) and $3.73\times10^{-38}$ ($T_2^*/T_2^{\rm echo}=0.174$), $\epsilon_2$ needed for $f=0.05$ with nothing else wrong $5.29\times10^{-4}$ against the best edge $8.16\times10^{-4}$.

*K1 attempt.* Under the owner's K1 authorisation (cap 300 s) the executor built and rehearsed the pilot (circuits `B0_ref117_k1` / `B1_ref29_k1`, the two with the largest ideal reference probability 0.92836 / 0.92831), and then **stopped before any submission**: the live `ibm_kingston` target carried no CZ calibration at all (352 of 352 CZ keys without an error value, observed continuously from 21:49Z to 01:26Z, status `maintenance` from about 01:12Z), so the preconditions "gate K0 on the day's record" and the D9 fingerprint could not be met (`prompts/LOG.md` row 2026-10-05/06, commit `4227a94`). 0 QPU s were spent.

### 6.21 2026-10-06: option A, gate `H0_ddrep`: the XY4 gain did not replicate (`prompts/32`)

*Owner decision (verbatim, `data/owner_decision_20261006_A_then_B.md`):* "I want you to do A first, then when that is finished, do B because by that time it might be online". *A0:* the 2x3 IBM NO-GO was recorded as a **model verdict** from K0 in `reports/K0_2x3_ibm_heron_nogo.md` (generated from the JSON; every number a calibration-record computation, none a measurement; `data/K0_2x3_nogo.json`).

*The design (planner, `prompts/32`; arithmetic in `scratch/planner/ddrep_budget_20261006.json`).* One job on `ibm_kingston`, the same 12-qubit patch `[59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]` (kept by rule P2: it ranked 2 of 750 on the day's record, $f_{\rm dd\,off}=0.0828$ against the winner's 0.0838), the two signed $k=1$ circuits, **seven cells**: T0 (no DD), T1 (context-aware staggered DD, the cell that had collapsed), T3 (client XY4 in windows $\ge1.024\ \mu$s, the adopted cell), and four mechanism cells built from T1/T2: **M1** = T1 with alternating pulse signs (same timing), **M2** = XX pairs in the 194 windows of T2, **M3** = M2 with alternating signs, **M4** = T1 minus all pulses on the two qubits that carry the most T1 pulses (91 and 95); plus four **pulse-train** pubs (XX-8, XX-32, XX-128, XpXm-128 on all 12 qubits) that measure the $x$ pulse's over-rotation $\epsilon_q$ and incoherent per-pulse cost $c_q$ directly. Three hypotheses were preregistered with a reading rule: $H_A$ coherent accumulation in uncompensated $X$ trains, $H_B$ the context-aware pass's output as such, $H_D$ a qubit-specific dense-drive cost on the hot qubits. Classes per cell on $R_i=X_i/X_0$ (excess reference hits over the garbage expectation): COLLAPSED iff the 95 % upper end $<0.25$, INTACT iff the lower end $>1$, else INTERMEDIATE. Replication verdicts: **R1** T3 qualifies under the H0_ddtest adoption rule ($R_{\rm lo}>1$ and $R\ge1.25$); **R2** $\lvert\ln R_{\rm new}-\ln2.819\rvert\le0.162$; **C1** T1 COLLAPSED. The planner wrote down its own expectation before the data: "T3 replicates (R about 2.8); T1 collapses again". Execution estimate 34.04 s, caps 36 s (estimator) / 45 s (billed); the reserve for part B (300 s) was checked first (498 - 45 = 453 s).

*Preconditions and the job.* Device watch 2026-10-06 06:02Z: `active`, 352/352 CZ errors published. Day's record 20261006T0501Z differs from the 2026-10-02 record in **1 110 calibration values** across the six families $T_1$, $T_2$, CZ error, measure error, $\sqrt{x}$ error, $x$ error (ratio of new to old between 0.102 and 111.3; `data/hardware/H0_ddrep_prep/live.json -> diff_against`). Preregistration committed before submission (commit `cd9ce12`), fingerprint `cb40a250fb24387d` at preregistration, submission and retrieval. Job **`db29p6nr11fs7396e4ig`**, 2026-10-06 07:00:40 UTC, 20 pubs x 6 000 shots, DD and twirling off, DONE, **billed 37.0 s** (estimate 34.04 s); account 498 s $\to$ 461 s left (`data/hardware/H0_ddrep_ibm_kingston/account_check_after_20261006T0703Z.json`). Readout minimum diagonal 0.9462.

*Results (95 % intervals; Block (o)).* No-DD baseline T0 $f=0.0818$ [0.0758, 0.0881] (716 reference hits, 2.93 from garbage) **against 0.0400 [0.0358, 0.0446] on 2026-10-02 for the very same QPY files**: a factor 2.04 (my division). T3 $f=0.0732$ [0.0675, 0.0792], $R_{T3}=0.895$ [0.804, 0.996] (2.819 [2.495, 3.185] on 10-02). T1 $0.0529$, $R=0.647$ [0.575, 0.727] (it collapsed to 0.012 on 10-02). M1 0.788 [0.706, 0.880], M2 0.806 [0.723, 0.900], M3 0.888 [0.798, 0.988] (all INTERMEDIATE), **M4 1.150 [1.040, 1.271] INTACT**, the only cell above the baseline. **R1 False, R2 False ($\ln R$: $-0.111$ against $1.036$, difference 1.148 against a tolerance 0.162), C1 False.** On T3 the signed bar reads NO-GO on $f_{\rm hit}$ and on $\hat f_{\rm ideal}=0.0656$ [0.0599, 0.0717] (information). *Mechanism:* matches per hypothesis $H_A$ 1/5, $H_B$ 0/5, $H_D$ 1/5, so the preregistered reading is **"no single hypothesis"**; M3 vs M2 gives $z=1.67$ (compensating the first-order timing effect may matter, marginal at one-sided 1.645). *Pulse trains:* the $x$ pulse over-rotates by $\epsilon_q=0.0148$ to $0.0204$ rad (68 % intervals a few $10^{-4}$ rad wide) on **all 12 qubits**; XX-128 minus XpXm-128 exceeds 0.05 on 12 of 12 qubits (the $H_A$ pattern is True); the incoherent per-pulse cost exceeds three times the record's `x_error` only on qubits 71 and 91 (the $H_D$ pattern, which wanted the hot qubits 91 and 95, is False). The calibration record cannot show this over-rotation: it aliases `x_error` to `sx_error` (the K0 record statistics give the same minimum $9.8\times10^{-5}$ for both), and the planner's RB-level estimate $\sqrt{6\,x_{\rm error}}$ (0.029-0.045 rad per qubit, Block (p)) is 1.5 to 3 times larger than the measured $\epsilon_q$. *Reading:* the 2026-10-02 gain and collapse were specific to that calibration; a coherent $x$ over-rotation is real but, with M1 INTERMEDIATE, does not by itself explain the collapse; and the device's baseline moved more between two days than any decoupling effect moved it within one.

### 6.22 2026-10-06: option B, the K1 2x3 pilot: a firm NO-GO (`prompts/32` part B, `prompts/27` stage 0b)

*Preconditions.* Device watch 07:21Z READY; account 461 s $\ge\max(300,\,1.3\times182.63)$ s; gate `K0_2x3_2x4 --live` PASS 6/6 on the day's record (fingerprint `b948ddc8`, content identical to the 05:01Z record that `H0_ddrep` used); circuits `B0_ref117_k1` / `B1_ref29_k1` rebuilt on that record (each 5 659 CZ, 21 active qubits, 411.2 / 410.8 $\mu$s, 2 408 / 2 404 XY4 pulses, exact to $1.6\times10^{-12}$ / $2.3\times10^{-12}$); preregistration (commit `f8df126`, calibration fingerprint `99035ef0`), dry run PASS 9/9, all preconditions held at submission.

*The job.* **`db2avbe8v0ts73c2i8b0`**, 2026-10-06 08:22:03 UTC, 4 pubs x $10^5$ shots (2 circuits + 2 readout pubs), DD and twirling off in the runtime options, cell T3 in the circuits, DONE, **billed 188.0 s** against an estimate of 182.63 s (1.029, my division; the preregistered expectation of billed time was 211.7-242.4 s); fingerprint equal at preregistration, submission and retrieval; account 461 s $\to$ **273 s** left. Readout minimum diagonal 0.9358 (qubit 92).

*Result (`validation/K1_2x3_fpilot.json`, Block (s)).* **Reference hits: 0 and 0**; the expectation from uniform garbage is $10^5\times2^{-20}=0.0954$ per circuit, 0.191 pooled. Accepted strings 58 (sector $B=0$) and 45 ($B=1$) of $10^5$ each, which is the garbage level (the exhaustive random acceptance gives about 64.6 and 40.6; `prompts/LOG.md`); the decoder re-encodes all 99 accepted strings with 0 mismatches. Pooled $f_{\rm hit}=-1.25\times10^{-6}$ (zero hits minus the garbage expectation; read it as zero), 95 % upper end $2.30\times10^{-5}$; $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ upper 95 % end **$2.06\times10^{-5}$** (per circuit $4.23\times10^{-5}$). The preregistered rule (GO-B $\ge10^{-3}$, GO-A $\ge3\times10^{-4}$, NO-GO below) reads **NO-GO, firm** (the point value and both interval ends agree). The upper bound is 14.6 times below the GO-A threshold and about 4 850 times below the signed bar 0.1 (my arithmetic).

*What it means.* (i) 2x3 on IBM Heron is now a **measured** NO-GO, not only a model verdict; the model's idle-aware ends predicted garbage only (0.0954 expected hits per circuit) and the data agree. (ii) The no-idle gate-only end of the preregistered bracket ($f=1.67\times10^{-5}$, 1.37 expected hits per circuit including garbage) is mildly disfavoured: a Poisson mean of 2.74 pooled gives P(0 hits) $\approx0.065$ (my arithmetic), so the data do not exclude it strongly. (iii) The correction $r_{nc}=1.115$ is a gate-noise value; under idle dephasing the A5 model gives $r<1$, so dividing by it can only lower the estimate and is conservative here. (iv) The report's honest limit: the XY4 cell this job carries did not replicate on the same morning's `H0_ddrep`, so the "XY4 transfer" ends of the bracket are not supported; the decision statistic $f_{\rm hit}$ does not use $R$. (v) Two circuits, one calibration content, one job: a pilot reading for this day, not a device constant.

### 6.23 Other items worth a line

- **Amendment 01 item 4 prerequisite work** (`data/S2D_2x3_device_requirements.json`, `reports/S2D_2x3_device_requirements.md`): requirement stated as the exact half-space $2158\,\tilde\epsilon_2+7310\,\tilde\epsilon_1+20\,\tilde\epsilon_{ro}\le\ln10$: $\epsilon_2\le7.094\times10^{-4}$ at the declared $\epsilon_1,\epsilon_{ro}$ ($9.066\times10^{-4}$ with virtual $R_z$); levers: connectivity spent, virtual $R_z$ and the fixed-angle generator (1 620 RZZ vs 2 158) unspent; the live `ibm_fez` gap: 3.31x in $\epsilon_2$ plus 2.53x routing.
- **Literature** (`reports/ibm_decoherence_literature_20261002.md`; `prompts/low_clean_fraction_techniques.md` read): client-side XY4 / context-aware DD arXiv:2403.06852, ZZ-robust DD arXiv:2506.18010 (equivalent to plain DD on tunable-coupler devices, consistent with T2 = T3 and making the T1 collapse more surprising), the random-baseline critiques arXiv:2608.11569 and arXiv:2605.23697.
- **Environment events:** the `coding` conda environment was repaired on 2026-10-02 (pinned stack qiskit 2.5.2, aer 0.17.2, runtime 0.49.0 re-verified; it reproduced every Stage T number exactly); a power failure interrupted the 2x4 work on 2026-09-30; laptop RAM rose to 62 GiB on 2026-09-30.

### 6.24 2026-10-06: campaign 33 is planned and built (`prompts/33`, milestone A; 0 QPU s, 0 HQC)

*The request.* The owner's request of 2026-10-06 (verbatim in Section 3.4) asked for four classes of 2x3 runs on qiskit, every earlier 2x3 simulation redone with the difference computed, all submittable at once to Perlmutter. The planner (Fable 5.1) wrote `prompts/33` and `reports/2x3_four_class_campaign_plan_20261006.md`: **33 one-GPU tokens**, sum of estimates 20.1 h of walltime = 5.0 GPU node-hours (cap 7.9) [PLAN, `scratch/planner/campaign33_sizing_20261006.json`], two UTC days at 4 concurrent jobs and 24 per day. The old results to be redone and compared: S1, S3, S3_smoke, the A6 dry run, CF_traj, CV_2x3_plan, Q0P_2x3_plan P3, and the K0/K1 predictions against the measured 0 hits and 58 / 45 accepted.
*The build* (executor, Opus 5.5, `prompts/LOG.md` row 2026-10-06, commits `a839278`, `7fec49b`, `a033fa6`, `cb7753f`, `1598363`): (A1) token table `scripts/gate_tokens.json` and `run_gate.py --resolve`; (A5) the concurrent poller `ci/poll_concurrent.sh` (the agents cannot edit `ci/poll.sh`; the owner installs) with a 15-test poller simulation; (A2) **12 circuit families frozen as QPY version 13, 373 files**, every family exact (max $\lvert\Delta\psi\rvert\le2.33\times10^{-12}$, leakage $\le2.14\times10^{-13}$; the qiskit-level-3 all-to-all family NAT-O4 turned out exact; the chosen exact-variant NAT-O2 has 2 158 ZZ like all others); (A3) noise scenarios E0-E8 and the IBM record models (the record model reproduces Aer's `from_backend` exactly: super-operator difference 0 on 664 gate errors); (A6) the engine pre-check: **`C3_LE` KEEP** (pytket-pecos `H2-1LE`, 51.9 s/shot at 20 qubits against a 60 s limit; installable only *without* the prompt's `numpy<2` pin because guppylang needs numpy $\ge2.2.6$), **`C3_SEL` DROP** (selene 0.3.4 and qir-qis 0.1.11 reject pytket-qir's `read_result` in every profile); (A4/A7) the job driver and assembly, with 33 laptop dry runs (32 PASS, `C3_SEL` FAIL by the drop) and a dry assembly PASS; pytest 476 passed. Open items the executor raised: seed rule widened (`s0*1e4 + 1e6 c + i*stride`) so that circuits, chunks and halves cannot share seeds; the f-cell circuits are `ref25` / `ref57`, not the `ref117` / `ref29` the prompt text names; dry runs were capped at 32 shots per circuit because noisy 20-21-qubit CPU shots cost 3-70 s; class-2 Kraus on the laptop cost 69 s per shot and PTA 24 s per shot.
*Owner's part* (`prompts/33` section 7): append 33 allowlist lines to `~/skqd-ci/allowed_jobs`, set `MAX_JOBS_PER_DAY=24` and `MAX_CONCURRENT=4`, review and install the concurrent poller. This was done (the CI has been submitting four jobs at once since the wave of 2026-10-08; inferred from the `ci/status/*.json` timestamps, no file states the installation date).

### 6.25 2026-10-07/08: the encoding comparison (`prompts/34`, gate `ENC_compare` PASS 8/8; 0 QPU s)

*Question* (owner, 2026-10-07): how many encodings have we tried, list others, test whether one shortens qubits, gates and depth. *Answer* (planner, `reports/encodings_candidate_list_20261007.md`): **one** (`src/skqd/codec.py`: one flux bit per link *end*, so each link bit is stored twice, plus one extra bit per vertex: $N_q=2N_\ell+N_s$ = 12 / 20 / 28). Thirteen candidates were listed with qubits at 2x2 / 2x3 / 2x4: E2 de-duplicated flux bits 8 / 13 / 18; E3 12 / 19 / 26; E4 dense sector encoding 6 / 10 / 14 at $B=0$; E6 local spin-network (LSH) 12 / 20-22 / 28-32; E7 bosonic 24 / 40 / 56 (Kogut-Susskind 20 / 33 / 46); E8 fermionic plus loops 11 / 18 / 25 (not equivalent at $j_{\max}=\tfrac12$); E9 magnetic basis (wrong regime); E10 qudits; E11 fermion-to-qubit maps (no gain: the quarks are absorbed in the vertex labels); E12 partial gauge fixing (declined); E13 architecture (same encoding). Twenty-six arXiv abstracts were fetched [PLAN]. The executor then ran **E2 (dedup) and E5' (a codeword-assignment search inside the current widths)**.
*Result* (`validation/ENC_compare.json`, Section 5.1): dedup shortens (2x3 qubits $20\to13$; CZ all-to-all $2164\to2004$, ratio 0.926; routed $5477\to4941$, 0.902; native ZZ $2158\to1996$, 0.925; kingston-routed `B0_ref117_k1` $5659\to5091$ CZ, active qubits $21\to13$, ALAP $411.152\to387.844\ \mu$s, gate-only layout $f$ $1.671\times10^{-5}\to1.365\times10^{-4}$, idle-aware echo $1.662\times10^{-15}\to1.900\times10^{-10}$; H2-2 gate-only mean $f$ $0.1503\to0.1739$) **but not meaningfully** (threshold: ratio $\le0.5$): the multiplexed-rotation and control counts are identical in both codecs, i.e. the cost is the physics, not the label width. The price: single-flip error detection falls from 98.17 / 98.31 % to **83.05 / 90.75 %** (2x3 $B=0$ / $B=1$), the random acceptance $a$ rises 128-fold ($6.46\times10^{-4}\to0.0826$), and saturation at the plan-of-record shots goes from 0.033 / 0.094 to **4.26 / 12.08** against the $3\sigma$ lines 10.5 / 22.5 and $\lambda^*=6.2958$ (Section 2 rule C22). E5' (best interior assignment, id 233, on the score sets {hop4, plaq1}): 1 122 to 1 090 CZ on those terms, but the nine-term step rises $2144\to2286$ (best step ratio **1.066**, worse); the corner best is the current layout. E4 at 2x2 costs 1 783 CZ in 6 qubits against 256 in 12. *Honest limits:* the E5' score sets fixed by the prompt choose an assignment worse on the full step; a full-step-scored search (about 4x the cost) was not done; the dedup circuits carry the UNSIGNED flag; static-charge sectors out of scope. *Planner's recommendation* (`prompts/34`): losing the link check is acceptable only if the gain is at least 2x, which the prototype already ruled out. Not adopted.

### 6.26 2026-10-07/08: the first Perlmutter wave and its failures (`prompts/33a`)

*What ran.* Request commit `7a8f7f1` (2026-10-07 10:05 MDT) asked for `C1_IDEAL`, `C3_AER`, `C2_CAL`, `C4_FCELLS_A`. Three jobs died after 15-21 s with `ModuleNotFoundError: No module named 'threadpoolctl'` (raised from `scripts/gate_CV.py:114` through `campaign33/analysis.py:53`): `C1_IDEAL` job 59491455 (21 s), `C3_AER` 59491462 (15 s), `C4_FCELLS_A` 59491480 (16 s); no JSON was written. `C2_CAL` job **59491475** ran 783 s and wrote a FAIL on one criterion, P5 (ladder points per mode 2 / 1 / 4 / 3 against $\ge2$), with P4 resolved to "Kraus only" because no Kraus point reached 512 shots. The ladder data (21 qubits, IBM-T0 `B0_ref117_k1`, cuStateVec versus the batched-shots mode) showed `batched_shots_gpu` slower than cuStateVec at every measured point (10.53 versus 6.88, 2.29 versus 1.84, 1.45 versus 0.794, 1.11 versus 0.374 s/shot at 8, 32, 128, 512 shots).
*Planner rulings (`prompts/33a`, 2026-10-07)*: **R1** archive the run-1 JSON unedited (`validation/archive/C2_CAL_job59491475.json`, sha256 `54b77474...`), decide the GPU mode from it (cuStateVec; batched closed) and make a second calibration run because the physics question was not answered (at the accepted rate the device showed, $58/10^5$, a 512-shot test carries 0.30 expected accepted strings and has no power). **R2** (physics): Aer's relaxation channel is a Kraus channel only where $T_2>T_1$, which is true for 4 of the 21 patch qubits (59, 69, 92, 95); the Pauli-twirled channel (PTA) is *unital* and cannot give the device's Hamming-weight deficit ($9.771\pm0.007$ of 20 on the K1 strings; readout asymmetry explains 0.063 of the 0.229-bit deficit) so a non-unital channel is required; a new fast representation "RM" ($T_2:=\min(T_2,T_1)$, no Kraus, PTA speed) was to be tested against Kraus on the mean Hamming weight and the 20 marginals. **R3** the $10^5$-shot targets withdrawn: per 60-minute job Kraus delivers 679-1 445 shots, RM / PTA about 8 000 (0.270 s/shot). **R4** class 4's rate basis plausible but per-call set-up (2.7 s inferred) and the driver's 25-40 % analysis reserve need 2 parts for $10^5$ halves and for the 67 600 / 99 000-shot $B=1$ plans, sized by `scripts/campaign33_resize.py` from the f-cell ladder, never by hand. **R5** no silent `threadpoolctl` fallback; the preflight exits in under 5 s and the smoke imports it.
*Executor (steps A-D, branch `c33a`, commits `b4a099b`, `74491e5`, `5e23b04`)*: preflight first in `main()`; `validation/archive/` record; C2_CAL run 2 design (PTA 512 / RM 1 024 / Kraus up to 1 024 shots at 0.9 of the remaining window, chunk 128); 20 generic slots `C4_PART_01..20`; `pytest` 574 passed / 40 skipped; the laptop dry runs were not delivered (the 30-minute rule under load).

### 6.27 2026-10-08/09: the second wave (jobs 59570217, 59570221, 59570315, 59570318)

Smoke job 59552188 passed first (2026-10-08). Request commit `3a768f9` (2026-10-08 14:25 MDT) asked for `C1_IDEAL`, `C3_AER`, `C4_FCELLS_A`, `C2_CAL`. Results: **`C1_IDEAL` PASS 10/10** (103 s) and **`C3_AER` PASS 10/10** (72 s) (Section 7.2); **`C4_FCELLS_A` FAIL 7/8** on S6 (2 337 s; 10 of 42 f-cells, Section 7.4); **`C2_CAL` run 2 FAIL 8/12** (250 s): the PTA arm took its 512 shots but the RM and Kraus arms drew **zero** shots because the sampler multiplied the discarded one-shot warm-up time (RM 12.27 s, Kraus 13.19 s; per-call set-up on the A100, not per-shot cost) by the round's 128 shots and predicted 1 571 / 1 688 s against 0.6 / 0.9 of the time left, so it stopped before round 0. Silent, but no exception was swallowed (`prompts/LOG.md` row 2026-10-11).

### 6.28 2026-10-11: the deadline fix, scenario-aware sizing and the request waves (`prompts/33a` fix, `33b`)

*Fix* (commit `7d0af48`): `sampling.call_bound` (a bound $t(s)\le t_p\max(1,s/s_p)$ from the measured point; a probe costs at most 0.1 of the time left, at most 3 probes); reproduced on the qiskit 1.4.3 / aer 0.15.1 twin with real Aer (noiseless 18-qubit circuit: $t(1)=1.69$ s, $t(128)=1.64$ s; before the fix 0 shots, after 1 024); regression test with 7 of 8 failing on the old code. The same rule would have zeroed most `C4_F*` runs. *Sizing* (`scripts/campaign33_resize.py` on job 59570315): custatevec fit $c=1.737$ s per call, $b=0.0245$ s/shot, chunk 1 428, $r_{\rm eff}=0.02572$ s/shot; $N_{\max}$ plan 53 758 / quota 67 197.
*Planner `prompts/33b` (2026-10-11)* found that the sizing ignored scenario cost: per-cell slope fits of `C4_FCELLS_A` give relative slopes E2 1.008, E3 2.804, E4 2.839, E5a/b/c 5.51 / 5.51 / 5.49 times the E1 slope (E1 cell slope 0.02494 against the ladder's 0.02450), so the E3 and E5 plan-of-record runs would have taken 2.8 to 5.5 times longer than sized. Rulings: **R2** scenario-aware rates $r_s=r_{\rm ladder}\rho_s$ (E1 0.02572, E2 0.02592, E3 0.07210, E4 0.07301, E5a/b/c 0.14158 / 0.14171 / 0.14107 s/shot); parts F3_B0 4, F3_B1 11, F6_B0 3, F6_B1 7. **R3** option (c): F3 (15 jobs) and F6 (10 jobs) are **deferred past the maintenance**, not shrunk (fewer shots would make a run that is not the plan of record). **R4** parts seed from the run's own F token with the global chunk index, so slots can be re-used and no more allowlist lines are needed. **R5** dropped f-cells packed by predicted cost into 4 slots; slot A first. **R6** six CV3 samples were `not_evaluated` in the 33a sizing (F1_B1, F2_B1, F3_B0, F3_B1, F5_B1, F6_B1); only F5_B1 and F1_B1 get cv3 slots before the maintenance (F2_B1 after it); because decision 2a's convergence condition is the gate `CV_2x3_plan` (PASS), campaign CV3 is information. **R7** the queue allows at most 32 jobs before 2026-10-21 06:00 UTC; 24 are must-run. The executor (step A, commit `ad44847`) reproduced the planner's rates exactly (every diff 0) and built the generation-1 part files; pytest 608 passed / 39 skipped.

### 6.29 2026-10-13: wave 3 returns, wave 4 submitted, the class-2 ruling and the Quantinuum question

Request commit `20b3887` (2026-10-13 08:25 MDT) ran `C4_FCELLS_B` (**PASS 8/8**), `C4_CF` (**FAIL 7/8**, S6), `C2_CAL` run 3 (**PASS 12/12**, production = Kraus) and `C4_F5_B0` (**PASS 8/8**), harvested at 2026-10-13T15:32Z (Sections 7.4-7.7, 8). Request `23d18e2` (08:27 MDT) submitted `C4_F1_B0`, `C4_F7_B0`, `C4_F5_B1` and `C4_PART_01` (jobs 59739276 / 78 / 80 / 82, state `submitted` at 15:32Z). Requests `ebc60de` (`C4_F4_B0a`, `C4_PART_02`, `C4_F4_B1a`, `C4_PART_03`) and `d7dd0c4` (`C4_F4_B0b`, `C4_PART_04`, `C4_F4_B1b`, `C4_PART_05`) are committed and pending. The planner then wrote **`prompts/33c`** (09:41 MDT) re-ruling class 2 (Section 8) and the owner asked the Quantinuum question that produced **`prompts/35`** (09:23 MDT; Section 9). The executors of `33c` (branch `c33c`, WIP `3ce492a`) and `35` (branch `q35`, WIP `e5503b8`) were both **paused by the owner** for a laptop meeting; neither has merged.

*(Addendum to 6.29, from the files of 2026-10-15.)* Both paused executors were resumed the same day and their branches were **merged into `master`**: `c33c` by `5f8a720` (2026-10-13 21:42 UTC) and `q35` through `4149de7` / `e66eb26` / `7c46329` (2026-10-14 00:27-06:34 UTC). Everything that the 2026-10-13 report labelled [EXEC] for Sections 8 and 9 is now either in a committed data file or a committed gate JSON (Sections 8, 9); the label [EXEC] is therefore retired in this report except where stated.

### 6.30 2026-10-13: waves 4-6 return on Perlmutter (F1_B0, F7_B0, F5_B1, the F4 and F8 halves a)

All times UTC from the CI robot's commits (block (a2)). Request `23d18e2` (14:27Z): `C4_F7_B0` harvested 17:07Z (**PASS 8/8**), `C4_F1_B0`, `C4_F5_B1` and `C4_PART_01` harvested 18:07Z (all **PASS**). Requests `ebc60de` (15:33Z) and `d7dd0c4` (15:41Z): the F4 halves (scenario E7(0.10), the S3 quota of $10^5$ shots per half and sector) ran 17:07Z-21:07Z: `C4_F4_B0a`, `C4_F4_B1a`, `C4_PART_03`, `C4_F4_B0b`, `C4_F4_B1b`, `C4_PART_05` **PASS**; **`C4_PART_02` and `C4_PART_04` FAIL 7/8 on S6 only** (each stopped by its own deadline rule after 45 696 of 49 984 shots; Section 7.9). Request `f940a18` (19:38Z): `C4_F8_B0a`, `C4_PART_06`, `C4_F8_B1a`, `C4_PART_07` (scenario E8, the gate-S3 model, on the IR-L3-RZZ family) ran 20:07Z to 2026-10-14 00:07Z, all **PASS**. Gate seconds 669-1 811 per job (block (a2)). The queue was fast: 1.0 to 5.4 h from request commit to last harvest per wave [MINE from the commit times], against 24.7 h on 2026-10-08/09.

### 6.31 2026-10-13: the class-2 diagnostics and the second re-ruling (`prompts/33c` executor, `prompts/33d`)

*Executor (`c33c`, `prompts/LOG.md` row 152).* Step 1 of `33c` (find the RM bug) stopped: the RM and Kraus delay-pass errors on qubit 53 of IBM-T0 `B0_ref117_k1` are **identical** (55 delay sites, 407.3 $\mu$s, super-operator maximum difference 0.0, on both software stacks; `data/campaign33/c33c_diag/delays_q53_*.json`); the one-qubit test ($x$, delay 400 $\mu$s, measure; 20 000 shots) gives RM 0.2614 ($z=+2.07$) and Kraus 0.2510 ($z=-1.32$) against $e^{-400/292.7}=0.2550$ (`oneq_q53_*.json`); and a **CPU run of the full circuit on the CI's software versions** (qiskit 1.4.3 / aer 0.15.1, laptop, `scripts/c33c_diag_full.py`) gave Kraus $\bar w=7.47\pm0.56$ (19 shots, 173.9 s/shot) and RM $6.92\pm0.57$ (24 shots, 84.0 s/shot) against the GPU's RM $7.42\pm0.08$ and Kraus $2.40\pm0.14$ (`data/campaign33/c33c_diag/summary.json`): CPU Kraus versus GPU Kraus $z_w=8.8$, CPU Kraus versus GPU RM $z_w=0.10$. **The outlier is the GPU Kraus arm, not RM.** Steps 2-3: `C2_XY4` became the I-XY4 cell on IBM-T3 (echo only) with an RM reference arm (dry run PASS with a stub decision); the owner-item rule of `C4_CF` now fires on section 6 OR section 8 of `prompts/33` (evaluated at assembly; the harvested JSON is not rewritten); the 2-part `C4_CF` content was prepared.
*Planner (`prompts/33d`, committed `1e9e4b2`).* R0: 33c R1/R2 withdrawn (the 2.64-bit relaxation estimate neglected the final `sx` rotation and the $T_2$ dephasing). R1: production RM on the GPU **conditional on `C2_KCHK`**. R2: Kraus audit: only the Kraus arms of `C2_CAL` runs 1-3 used Kraus instructions; nothing else harvested is affected and nothing is re-run (`data/campaign33/kraus_audit.json`). R3: token `C2_KCHK` (Kraus on cuStateVec / native / cuStateVec-without-fusion, RM on cuStateVec, Kraus and RM on the CPU; decisions K1 bug confirmed, K2 production representation, K3 validated Kraus GPU path). R4: upstream report to qiskit-aer after confirmation (release notes 0.16-0.17.2 contain no relevant fix: `data/campaign33/aer_release_notes_check.json`). R5: C2_CAL run 3's decision "production = Kraus" does not stand.
*Executor (33d section 1, `prompts/LOG.md` row 156):* token built (index 53, no other index moved); dry runs: `C2_XY4` PASS in 532 s, **`C2_KCHK` dry run FAIL on S2 only (1 152 s against the 8-minute dry budget)**, which also fails the test `test_dry_run_json_exists_and_passes_its_structural_criteria[C2_KCHK]` (Section 13.8). The executor flagged that K2's marginal test uses a binomial sigma that is 0 when a CPU marginal is 0 or 1 (probability 0.39 at 16 CPU shots under the GPU RM marginals), which would block K2 by the statistic rather than the channel.

### 6.32 2026-10-13/14: the Quantinuum tests completed as gates (`prompts/35`, `35a`, `35b`)

*`prompts/35a`* (planner, 2026-10-13 18:31 UTC): R1 Q2 corrected ($k$-independent: 2 158 ZZ on all 44 at 2x3, 252 on all 28 at 2x2); the 2x4 GPU cost is per circuit, not per $k$ (about 1.6 GPU-hours for $k\ge2$ [PLAN], not 4.9); R2 pytket canonicalises angles within $10^{-11}$ half-turns of a multiple of 1/4, and the effect on the state is bounded by $B=\tfrac{\pi}{2}\sum_g(\lvert\Delta a_g\rvert+2\lvert\Delta b_g\rvert)$; Q1L requires $B<10^{-10}$; R3 the 2x2 tier T3: f-cells on all 28 circuits x 11 scenarios, plan-of-record runs only for E1, E3, E4, E5b, cap 10 h; R4 2x4 at level 0 only; R5 Selene sized on the measured rate.
*Executor STOP* (`prompts/LOG.md` row 149): **Q1L (iii) failed on all 19 built 2x4 circuits**: $B=4.96$-$4.98\times10^{-9}$ against $10^{-10}$, the sum of about 67 000 pytket snaps of near-Clifford angles left by the qiskit opt-3 transpile (each at most $8.0\times10^{-13}$ half-turns); the conversion itself is exact ((i) $4.4\times10^{-15}$, (ii) $8.0\times10^{-15}$).
*`prompts/35b`* (planner, 20:23 UTC): the fact from the files is that the $10^{-10}$ bar was never met by any compiled 2x4 circuit even before conversion (the qiskit opt-3 all-to-all circuit is $1.528\times10^{-9}$ from `krylov.coarse_states` on the GPU, `validation/S2_2x4.json -> data.gpu_validation`; the structured IR $1.07\times10^{-13}$); R1 the bar stays and is measured on the GPU; R2 Q1L is the conversion proof and $B$ a falsifiable consistency check of the GPU job; R3 `Q0P_2x4` FAIL with a stated reason until the measurement; R4 a second, **structured** 2x4 source (exact IR through `ir_to_pytket`, pytket level 0, no qiskit opt-3); R5 cross-check on 2x3; R6 the frozen source is chosen by the GPU slot `QV_2x4_01`.
*Gates* (Section 9): `QEMU_2x2` PASS 3/3, `Q0P_2x2` PASS 5/5, `QH_2x2` PASS 4/4, `QH_2x3` PASS 4/4, `QEMU_2x3_laptop_smoke` PASS, `QN_2x2` PASS 5/5 (T3 wall 5.25 h of the 10 h cap), `Q0P_2x4` **FAIL by construction** 4/6, `QN_2x4` PASS 2/2, `QSC_prepared`, `QEMU_2x4` infeasible, `QH_2x4` not attempted; GPU slots `QV_2x4_01..08` added (indices 54-61), `ci/parts/QV_2x4_01.json` (9 runs, predicted 888 s) and its 2x2 dry run PASS. Merged into `master` (`e66eb26`, 2026-10-14 06:32 UTC). 0 QPU s, 0 HQC.

### 6.33 2026-10-14: waves 7-8 (F1_B1, F7_B1, the F8 halves b) and `C2_KCHK`

Request `6c3e684` (15:05Z): `C4_F1_B1`, `C4_PART_10`, `C4_F7_B1`, `C4_PART_11` submitted 15:07Z and harvested 16:07Z, all **PASS**. Request `f4c71e8` (15:05Z): `C2_KCHK` (job 59780907) harvested 17:07Z, **FAIL 7/10**; `C4_F8_B0b`, `C4_PART_08`, `C4_F8_B1b` harvested 18:07Z and `C4_PART_09` (submitted 17:07Z) harvested 18:07Z, all **PASS**. Both request commits were made directly on `master` after `scripts/ci_request.sh`'s `git pull --rebase` conflicted with the local merge history (merges `4b8ca48`, `34fea24`; Section 13.8). After this wave every planned must-run class-4 job of `prompts/33c` section 4 except F2 had returned.

### 6.34 2026-10-15: requests for F2 and slots 12-17; `prompts/33e`

Request commit `34f73a7` (17:37Z): `C4_F2_B0`, `C4_F2_B1`, `C4_PART_12..17` (F2_B1 part 2; f-cell slot A part 1 of 4; the cv3 equal-shots samples of F5_B1 and F1_B1, two parts each; contents from `ci/parts/C4_PART_12..17.json`). `scripts/ci_check.sh` at 17:43Z shows all eight `pending`. **`prompts/33e`** (planner, committed `10f88a0` at 17:41Z, pulled by `ci_check.sh` while this report was being written) re-rules class 2 after `C2_KCHK` (Section 8.7): the one-thread cause, the sbatch fix, `C2_KCHK` run 2 with the CPU arms only, the laptop CPU reference to $\ge64$ shots per representation, `C2_XY4` immediately on `production_representation: rm`, the other class-2 cells after the maintenance, and the GPU-versus-GPU Kraus inconsistency as the first exhibit for an upstream report. On `master` no executor work on 33e exists yet; an executor branch `c33e` carries one unmerged commit (`daeb40c`, 17:46 UTC: "background segment runner for the laptop CPU reference", `prompts/33e` R3), so the laptop CPU sampling of R3 is being set up.

### 6.35 Not changed since 2026-10-13

No QPU job (the IBM account stands at 327 s used, 273 s left as of the last check on 2026-10-06); no Quantinuum, IonQ or other vendor access; no owner decision file; no change to any convention, tolerance or frozen circuit; `validation/C33_campaign.json` not assembled.

## 7. Campaign 33 results in full (Perlmutter, 2x3 four-class campaign)

Source of the whole section unless named otherwise: the class-1 to class-4 token JSONs `validation/C1_IDEAL.json`, `C3_AER.json`, `C4_FCELLS_A.json`, `C4_FCELLS_B.json`, `C2_CAL.json`, `C2_KCHK.json`, `C4_CF.json`, the 25 class-4 run files `C4_F*.json` / `C4_PART_*.json` and their `validation/ci_gate_*.json` wrappers (all on `master`, harvested by the CI robot), `prompts/33`-`33e`, `data/campaign33/sizing_33a.json`, `ci/parts/*.json`, `ci/requests/*.txt`, `ci/status/*.json`, `reports/ci-<jobid>.out` and `scripts/ci_check.sh` (run 2026-10-15 17:43 UTC). All of it is **simulation on a classical GPU**; nothing here is a quantum-device statement. (Updated 2026-10-15: Sections 7.8-7.10 and 7.12 are new; 7.5 is rewritten; the rest is carried over with small updates.)

### 7.1 What campaign 33 is, in plain English

The owner asked (2026-10-06) for the signed 2x3 circuit family (44 circuits: references $\times$ $k=1..4$, 32 in sector $B=0$ and 12 in $B=1$, 20 logical qubits) to be run on a classical GPU simulator in **four classes** and for every earlier 2x3 simulation to be redone with the difference computed:

| class | what is simulated | engine | tokens |
|---|---|---|---|
| 1 | no noise, no circuit optimisation: the circuits as built (IR-L0), the Quantinuum-native version (NAT-O0), the three IBM-routed versions (IBM-U unscheduled, IBM-T0 ALAP-scheduled, IBM-T3 with the XY4 pulses that actually flew) | Aer statevector on the GPU | `C1_IDEAL` |
| 2 | IBM noise from the committed 2026-10-06 `ibm_kingston` calibration record (without any fake provider): gate depolarizing plus thermal relaxation (I-GATE), plus relaxation on every ALAP delay at the record's echo $T_2$ (I-ECHO) or at $T_2^*=0.174\,T_2^{\rm echo}$ (I-STAR), the flown XY4 circuit (I-XY4, information), a coherent $x$ over-rotation of 0.015-0.020 rad (I-COH) | Aer with noise, 21 qubits | `C2_CAL`, `C2_GATE`, `C2_ECHO`, `C2_STAR`, `C2_XY4`, `C2_COH` |
| 3 | Quantinuum-native circuits, no error | Aer GPU (`C3_AER`); local vendor emulator pytket-pecos `H2-1LE` (`C3_LE`); Selene via QIR (`C3_SEL`, dropped) | `C3_AER`, `C3_LE`, `C3_SEL` |
| 4 | Quantinuum-native circuits with eight error scenarios E1-E8 and exact optimisation variants O0-O6; clean-fraction cells ("f-cells") and full SKQD runs F1-F8 | Aer with noise | `C4_FCELLS_A/B`, `C4_F1..F8_B0/B1` (with halves a/b), `C4_CF`, 20 generic part slots `C4_PART_01..20` |

**Scenarios (the project's labels; `validation/C4_FCELLS_A.json -> data.noise_descriptions` and `C4_FCELLS_B.json`).** The parameters are Aer `depolarizing_error(p,n)` values, whose fault probability is $\tfrac{15}{16}p$ for $n=2$ and $\tfrac34p$ for $n=1$.

| id | channel | parameters | source |
|---|---|---|---|
| E1 | depolarizing on `rzz` and `rx`/`ry`, asymmetric readout, `rz` virtual | $p_2=8.3\times10^{-4}$, $p_1=2.8\times10^{-5}$, $p(1\vert0)=6.7\times10^{-4}$, $p(0\vert1)=1.2\times10^{-3}$ | H2-2 performance-validation page read 2026-10-02 (`data/quantinuum/devices_20261002.json`) |
| E2 | same | Helios-1: $p_2=7.9\times10^{-4}$, $p_1=3.0\times10^{-5}$, readout $4.8\times10^{-4}$ | same file |
| E3 | H2-2E emulator parameter set (2025-07-16) with angle-dependent 2q error $p_2(\theta)=(1.518\lvert\theta\rvert/\pi+0.241)\,p_2$, initialisation flip | $p_2=1.29\times10^{-3}$, $p_1=7.3\times10^{-5}$, readout $(9\times10^{-4},1.8\times10^{-3})$, $p_{\rm init}=4\times10^{-5}$ | `docs.quantinuum.com` emulator pages read 2026-10-06 |
| E4 | Helios-1E parameter set (2025-11-18), same classes (leakage not representable in Aer) | $p_2=8\times10^{-4}$, $p_1=2.5\times10^{-5}$, readout $10^{-6}$, $p_{\rm init}=5\times10^{-4}$ | same |
| E5a/b/c | E1 plus memory (transport/idle) dephasing: Pauli-$Z$ with probability $p_{\rm mem}=r\,t_{\rm round}$ after every two-qubit layer on every qubit, $r=0.0028\ {\rm s^{-1}}$ | $t_{\rm round}=0.5/1.1/4.4$ ms, $p_{\rm mem}=1.4\times10^{-6}/3.08\times10^{-6}/1.232\times10^{-5}$ ([EST]: the transport schedule is unmeasured) | the project's low/mid/high memory scenarios |
| E6a/b/c | E1 with every error probability scaled | $\times0.5/\times2/\times4$ ($p_2$ $4.15\times10^{-4}/1.66\times10^{-3}/3.32\times10^{-3}$) | emulator `scale` parameter |
| E7(f) | matched-$f$: E1 with $p_2$ inverted so that the *gate-only* clean fraction of the family equals $f$ at mean counts (2 158, 3 053, 20) | $f=0.05/0.07/0.10/0.15\to p_2=1.3390\times10^{-3}/1.1833\times10^{-3}/1.0182\times10^{-3}/8.3048\times10^{-4}$ | reproduces the device-table value for 0.10 to $7.6\times10^{-10}$ |
| E8 | the gate-S3 declared model: depolarizing also on `rz` (not virtual), symmetric readout | $\epsilon_2=10^{-3}$, $\epsilon_1=10^{-4}$, $\epsilon_{ro}=2\times10^{-3}$ | `validation/S3.json` |
| I-GATE / ECHO / STAR / XY4 / COH | IBM record models (see class 2) | `data/hardware/K0_prep/ibm_kingston_full_20261006T0652Z.json`, fingerprint `b948ddc8...` | `NoiseModel.from_backend` semantics |

**Optimisation variants (O\*)** are circuit rewrites allowed only if they pass the exactness bars $\max\lvert\Delta\psi\rvert<10^{-10}$, leakage $<10^{-9}$: O0 none; O1 pytket peephole resynthesis plus 1-qubit squashing on the measurement-free circuit; O2 qiskit level 1 (adjacent cancellation); O3 level 2 (commutation); O4 level 3 (two-qubit resynthesis); O6 approximate KAK synthesis (inexact, information only). Class-4 **runs**: F1 = E1 x O0 at the plan tier, F2 = E2, F3 = E3, F4 = E7(0.10) with the S3 quota ($2\times10^5$ shots per sector in two halves a, b), F5 = E7(0.07) at the $f=0.10$ plan of record (like-for-like with `CV_2x3_plan`, whose proxy sampled at $0.7f$), F6 = E5b, F7 = E1 on the chosen exact variant (NAT-O2), F8 = E8 with the S3 quota; each for sectors B0 and B1. The **plan tier** of a run is the largest of 0.05 / 0.10 / 0.15 not above the lower 95 % end of the scenario's $\hat f_{\rm ideal}$ in the f-cells. Tiers read from `C4_FCELLS_A`: E1 0.15 (lower end 0.1858), E2 0.15 (0.2167), E3 **0.05** (0.0869), E4 0.15 (0.2062), E5a / E5b / E5c 0.15 (0.1893 / 0.1969 / 0.1731); from `C4_FCELLS_B`: E6a 0.15, E6b and E6c 0.05 (lower ends 0.0494 and 0.0038, so the floor tier), E7(0.05) 0.05, E7(0.07) 0.10, E7(0.10) 0.10, E7(0.15) 0.15.

### 7.2 Classes 1 and 3 on the GPU (`C1_IDEAL` PASS 10/10, `C3_AER` PASS 10/10)

Both ran on 2026-10-09 (jobs 59570217 and 59570221; the first attempt of 2026-10-07 had died on a missing python package, Section 6.26). Both gates are validation gates: the simulated bit strings must match the exact distribution.

| quantity | `C1_IDEAL` (IR-L0 and four more families) | `C3_AER` (NAT-O0, the Quantinuum-native family) |
|---|---|---|
| exactness, max $\lvert\Delta\psi\rvert$ after global phase | IR-L0 $3.48\times10^{-14}$ (44 circuits); NAT-O0 $2.08\times10^{-13}$ (44); IBM-U and IBM-T0 $2.33\times10^{-12}$ (2 each); IBM-T3 $2.33\times10^{-12}$ (2) | NAT-O0 $2.08\times10^{-13}$ (44) |
| leakage out of the codeword space | $\le2.19\times10^{-13}$ | $\le1.28\times10^{-13}$ |
| per-state 5-sigma sampling test ($p_s\ge10^{-3}$) | 50 circuits, 1 441 states, max $z=4.84$, 0 failures | 44 circuits, 1 393 states, max $z=4.08$, 0 failures |
| noiseless SKQD at the $f=0.10$ plan, $B=0$ (34 909 shots) | $\lvert B_{\rm all}\rvert=333$ of 677; $E_R-E_0=1.800\times10^{-4}$; Kato-Temple width $5.69\times10^{-4}$; $r_H=0.0393$; $W=0.999977$; recall of $S_{999}$ and $S_{99}$ 1.0; 8 false positives | $\lvert B_{\rm all}\rvert=327$; $E_R-E_0=1.828\times10^{-4}$; width $6.02\times10^{-4}$; $r_H=0.0404$; $W=0.999978$; recall 1.0 |
| the same at $2\times10^5$ shots, $B=0$ | $\lvert B_{\rm all}\rvert=426$; $E_R-E_0=7.20\times10^{-5}$; width $2.07\times10^{-4}$; $W=0.999990$ | $\lvert B_{\rm all}\rvert=414$; $7.90\times10^{-5}$; $2.35\times10^{-4}$; $W=0.999989$ |
| noiseless SKQD at the plan, $B=1$ (99 000 shots) | $\lvert B_{\rm all}\rvert=345$ of 426; $E_R-E_0=1.155\times10^{-4}$; Weinstein $r_H=0.0286$; $W=0.999983$; recall 1.0 | $\lvert B_{\rm all}\rvert=344$; $1.827\times10^{-4}$; $r_H=0.0349$; $W=0.999972$; recall 1.0 |
| the same at $2\times10^5$ shots, $B=1$ | $\lvert B_{\rm all}\rvert=326$; $1.306\times10^{-4}$; $r_H=0.0299$ | $\lvert B_{\rm all}\rvert=327$; $1.935\times10^{-4}$; $r_H=0.0364$ |
| $E_0$ inside the certificate (Kato-Temple at $B=0$, Weinstein at $B=1$) | yes in all four readings | yes in all four |
| wall time; GPU | 89 s; mean utilisation 1.4 %, peak memory 473 MiB; $3.34\times10^{-5}$ s/shot | 59 s; mean utilisation 1.5 %, peak 429 MiB; $4.95\times10^{-5}$ s/shot |

*What it means.* (i) Every circuit family, including the Quantinuum-native one (the one that would be submitted) and the two IBM-routed circuits with and without the XY4 pulses, produces the exact distribution to $10^{-12}$ and samples it correctly at the 5-sigma level; (ii) at *zero noise* the plan-of-record shot counts reach recall 1.0 of the 99.9 % support in both sectors, with captured weight 0.99998 and an energy error of order $10^{-4}$, so the shot plan is **not** the bottleneck in the ideal case; (iii) $E_R-E_0>0$ because the support $B_{\rm all}$ is a finite sample; the Kato-Temple widths at $B=0$ are $2\text{-}6\times10^{-4}$, i.e. 170 to 480 times narrower than the signed limit 0.1 [MINE: 0.1/5.69e-4 and 0.1/2.07e-4]. [GATE]/[SIM].

### 7.3 The GPU timing ladder and the rates that sized everything

`C4_FCELLS_A -> data.ladder` (one A100, 20-qubit NAT-O0 circuits, double precision, one `run()` call per point): the cuStateVec path takes 0.02883 s/shot at chunk 476, 0.02564 at 952, 0.02594 at 1 428; the `batched_shots_gpu` path 0.2244, 0.2251, 0.2256 s/shot. So **cuStateVec is 7.8 to 8.7 times faster** [MINE] and the batched mode is closed. The fit used for sizing: per-call set-up $c=1.737$ s, per-shot $b=0.0245$ s, $r_{\rm eff}=0.02572$ s/shot at chunk 1 428 (executor, `prompts/LOG.md` row 2026-10-11); gate S3's earlier 0.01987 s/shot at 476-shot calls is the same family under the E8 model. Per-scenario slopes relative to E1 x O0 (planner, confirmed by the executor): E2 1.008, E3 2.804, E4 2.839, E5a/b/c 5.51 / 5.51 / 5.49 (`prompts/33b` R1): E5 carries $20\times1925$ explicit Pauli-$Z$ sites per circuit and E3/E4 the angle-dependent 2q error as per-instruction channels, so the cost is structural. GPU telemetry from the gate JSONs: `C4_FCELLS_A` mean utilisation 77.9 %, peak memory 23 553 MiB; `C4_FCELLS_B` 52.2 %, 1 783 MiB; `C2_CAL` 81.8 %, 2 295 MiB; `C4_CF` 2.2 % (one statevector at a time); `C4_F5_B0` 50.1 %, 1 783 MiB.

*Rates actually measured in the 25 class-4 run files (updated 2026-10-15; `data.seconds_per_shot` of each file, block (ae)).* E7(0.07) and E7(0.10) on NAT-O0: 0.02589-0.02734 s/shot (11 files); E1 on NAT-O0 (F1): 0.02331-0.02769; E1 on NAT-O2 (F7): 0.01827-0.02157; E8 on IR-L3-RZZ (F8): 0.01854-0.02059. Every run used cuStateVec, chunks of 476 (single-job runs) or 1 428 (split runs), 0 out-of-memory retries, peak GPU memory 1 783 MiB in all 25, mean GPU utilisation 36.8-58.9 %. The O2 variant samples about 20 % faster than O0 under the same E1 noise [MINE: 0.02157/0.02769 = 0.78 at $B=0$]; no file explains why (O2 is qiskit level-1 adjacent-gate cancellation with the same 2 158 ZZ, Section 7.1).

### 7.4 The f-cells: the simulated clean fraction of the 2x3 family under every scenario (`C4_FCELLS_A`, `C4_FCELLS_B`)

*What an f-cell is.* The four Stage-E circuits (`B0_ref25_k1`, `B1_ref57_k1`: 800 shots each; `B0_ref25_k4`, `B1_ref57_k4`: 200 shots each; 2 000 shots per cell) are sampled under one scenario and one optimisation variant; the pooled $k=1$ reference-hit count (1 600 shots) gives $f_{\rm hit}$ with a Garwood interval, then $\hat f_{\rm ideal}=f_{\rm hit}/1.115$. **Which circuits:** the prompt text said `ref117`/`ref29`, the executor used `ref25`/`ref57` as `Q0P_2x3_plan.json` does (`prompts/LOG.md` row 2026-10-06). `C4_FCELLS_A` (job 59570315): 10-minute ladder (Section 7.3) then 42 planned cells; only **10** fitted in the job (E1-E5c $\times$ O0 = 7 cells, then E1/E2/E3 $\times$ O1), so S6 failed and 32 cells were dropped (E4, E5a/b/c $\times$ O1 and every cell of O2, O3, O4, O6); `C4_FCELLS_B` (job 59736863): all 35 cells (E6a/b/c and E7 at four tiers, $\times$ O0-O4) in 1 710.9 s of sampling, no drop.

**Pooled $k=1$ clean fraction, variant O0 (95 % intervals; `data.cells[<scenario>|NAT-O0].stats.pooled_k1`; $z$ is the difference from E1 in standard errors [MINE]).**

| scenario | $f_0$ (analytic, mean of the 2 $k=1$ circuits) | reference hits / 1 600 shots | $f_{\rm hit}$ [95 %] | $\hat f_{\rm ideal}$ [95 %] | $z$ vs E1 | plan tier |
|---|---|---|---|---|---|---|
| E1 (H2-2 spec) | 0.17223 | 338 | **0.2312** [0.2072, 0.2572] | 0.2074 [0.1858, 0.2307] | 0 | 0.15 |
| E2 (Helios-1 spec) | 0.18696 | 391 | 0.2675 [0.2416, 0.2954] | 0.2399 [0.2167, 0.2649] | +1.9 | 0.15 |
| E3 (H2-2E emulator set) | 0.06113 | 166 | **0.1136** [0.0969, 0.1322] | 0.1018 [0.0869, 0.1186] | **-7.5** | **0.05** |
| E4 (Helios-1E set) | 0.18582 | 373 | 0.2552 [0.2299, 0.2824] | 0.2288 [0.2062, 0.2533] | +1.3 | 0.15 |
| E5a (E1 + memory, 0.5 ms) | 0.16319 | 344 | 0.2353 [0.2111, 0.2616] | 0.2110 [0.1893, 0.2346] | +0.2 | 0.15 |
| E5b (1.1 ms) | 0.15297 | 357 | 0.2442 [0.2195, 0.2709] | 0.2190 [0.1969, 0.2429] | +0.7 | 0.15 |
| E5c (4.4 ms) | 0.10718 | 316 | 0.2162 [0.1930, 0.2414] | 0.1939 [0.1731, 0.2165] | -0.9 | 0.15 |
| E6a (errors $\times0.5$) | 0.41507 | 771 | **0.5274** [0.4909, 0.5660] | 0.4730 [0.4402, 0.5076] | +12.9 | 0.15 |
| E6b ($\times2$) | 0.02962 | 99 | 0.0677 [0.0550, 0.0825] | 0.0607 [0.0494, 0.0739] | -11.2 | 0.05 |
| E6c ($\times4$) | 0.00087 | 12 | **0.0082** [0.0042, 0.0143] | 0.0074 [0.0038, 0.0129] | -17.1 | 0.05 |
| E7(0.05) matched-$f$ | 0.06143 | 160 | 0.1095 [0.0932, 0.1278] | 0.0982 [0.0835, 0.1146] | -7.9 | 0.05 |
| E7(0.07) | 0.08421 | 233 | 0.1594 [0.1396, 0.1812] | 0.1429 [0.1252, 0.1625] | -4.3 | 0.10 |
| E7(0.10) | 0.11765 | 256 | 0.1751 [0.1543, 0.1979] | 0.1570 [0.1384, 0.1775] | -3.3 | 0.10 |
| E7(0.15) | 0.17206 | 380 | 0.2600 [0.2345, 0.2875] | 0.2331 [0.2103, 0.2578] | +1.6 | 0.15 |

(Block (v) in Section 18 has all 45 cells with the variants. The 2 000-shot cells took 42.9-58.4 s for E1/E2/E6/E7, 146-154 s for E3/E4 and 302 s for E5.)

*What these numbers say.*
1. **At the vendor-published H2-2 and Helios-1 rates the simulated 2x3 family clears the signed bar comfortably** ($\hat f_{\rm ideal}=0.207$ and $0.240$; lower 95 % ends 0.186 and 0.217 against 0.1), as the analytic table said (0.1502 / 0.1642 gate-only; the Aer convention gives $f_0=0.172$ / 0.187, Section 2.12). **With the H2-2E emulator parameters (E3) it only just does**: $\hat f_{\rm ideal}=0.1018$ [0.0869, 0.1186]; the lower end is below 0.1, so the plan tier drops to 0.05 (in `CV_2x3_plan` the tier-0.05 plan costs 1 279 660 HQC, the tier-0.10 plan 665 605). The E3 parameter set differs from E1 by an angle-dependent two-qubit error $(1.518\lvert\theta\rvert/\pi+0.241)\,p_2$ and a larger $p_2$ (1.29 against 0.83 $\times10^{-3}$): **the scenario choice moves the plan cost by a factor 2.7 (tier 0.15 at 471 801 HQC for E1, tier 0.05 at 1 279 660 HQC for E3 [MINE: 1 279 660/471 801])**.
2. **The bar is lost at twice the E1 error** (E6b $\hat f_{\rm ideal}=0.061$) and badly at four times (E6c 0.0074). Half the error gives 0.473. $f_{\rm hit}$ falls by a factor 7.8 when the error grows from $\times0.5$ to $\times2$ (a factor 4) and by 8.3 when it doubles again to $\times4$ [MINE: 0.5274/0.0677; 0.0677/0.0082], as expected for a clean fraction that is exponential in the error.
3. **Memory (transport) dephasing, E5, is invisible in $f_{\rm hit}$** (z within $\pm1$ of E1 at all three round times) while the analytic fault-free fraction $f_0$ falls from 0.1722 to 0.1072. A Pauli-$Z$ fault in the middle of the circuit mostly leaves the *reference string* unchanged, so $f_{\rm hit}$ is nearly blind to it; whether the *other* support states are populated correctly under such faults is not what $f_{\rm hit}$ tests. [MINE, a judgement: the project's sizing statistic $\hat f_{\rm ideal}$ cannot detect a transport-dephasing problem on a real Quantinuum device, which is the one unmeasured term (Section 14.2); the full runs F6 (E5b) were designed to look at it and are deferred past the maintenance.]
4. **The matched-$f$ scenarios** E7(f) are labelled by the *gate-only* analytic $f$ but the measured $\hat f_{\rm ideal}$ is 1.55 to 2.04 times larger (0.0982 at label 0.05; 0.1429 at 0.07; 0.157 at 0.10; 0.2331 at 0.15) [MINE: ratios 1.96, 2.04, 1.57, 1.55]. So the label "0.07" of F5 corresponds to a measured $\hat f_{\rm ideal}$ of about 0.13-0.14, not 0.07 (this matters for the comparison with `CV_2x3_plan`, Section 7.7).
5. **Optimisation variants.** All 28 comparisons of an exact variant (O1-O4) with O0 in `C4_FCELLS_B`, and 3 in `C4_FCELLS_A`, are labelled "consistent" except two at $z\approx2.0$ (E7(0.07) and E7(0.15) with O3, labelled "tension", $\Delta f_{\rm hit}=-0.029$ and $-0.038$); 22 of 28 differences in B are negative, so the variants are on average slightly *lower* than O0 [MINE count] but not significantly. In `C4_FCELLS_A` the O1 cells for E2 and E3 reproduce the O0 pooled hit counts exactly (391 = 189 + 202 versus 204 + 187; 166 = 89 + 77 versus 87 + 79), with different seeds and different accepted counts: a coincidence of sums, as the executor verified (`prompts/LOG.md` row 2026-10-11 point 3). **Conclusion supported by the data: the exact circuit rewrites do not change the clean fraction by more than about 0.03 at these statistics; they do not rescue or hurt the family.**
6. **Gate-S3 redo (P12, `C4_FCELLS_B -> data.s3_redo`).** Re-running gate S3's path (IR-L3-RZZ circuits, model E8, 32 circuits $\times$ 100 shots, `seed_simulator` 11) gave **656 accepted of 3 200** (yield 0.205) against S3's 695 of 3 200 (0.2172); the preregistered binomial 95 % band is (650, 741), so the redo is inside it (just: 656 is 6 above the lower edge). The two counts are not equal (`equal_to_s3_count` false). This used 14-shot calls and cost 141 s (0.044 s/shot, set-up dominated), a second measurement of the E8 rate below E1's.
7. **P11 (physics, `C4_FCELLS_A`):** the E1 x O0 reference hits on the $k=1$ circuits (338 of 1 600) lie in [302, 427], the Poisson band widened by the standard error of the CF_traj trajectory prediction (362.6 $\pm$ 12.9, `validation/CF_traj.json data.C2`): the Aer f-cell and the independent Pauli-trajectory computation agree. [GATE]

### 7.5 Class 2 in one paragraph (the full history is Section 8)

`C2_CAL` (three runs, the third PASS 12/12 on 2026-10-13) compared three representations of IBM thermal relaxation on the circuit IBM-T0 `B0_ref117_k1` with the 100 000 device strings of K1 and found mean Hamming weights PTA 9.96, RM 7.42 and Kraus 2.40 against the device's 9.77. The executor's CPU diagnostics of 2026-10-13 then showed that **Kraus run on the CPU gives 7.47 $\pm$ 0.56**, agreeing with RM, so the GPU Kraus arm is the outlier (`data/campaign33/c33c_diag/summary.json`); `prompts/33d` withdrew the earlier explanation and designed `C2_KCHK`. **`C2_KCHK` (job 59780907, 2026-10-14) FAILED 7/10**: its four GPU arms ran (Kraus on cuStateVec 3.00 $\pm$ 0.24, Kraus on Aer's native GPU kernels 3.57 $\pm$ 0.25, Kraus on cuStateVec without fusion 1.14 $\pm$ 0.22, RM on cuStateVec 7.43 $\pm$ 0.10) but **both CPU reference arms drew 0 shots**, so the decision on the class-2 representation is `blocked`. `prompts/33e` (2026-10-15) orders a second run with the CPU arms on the node's CPUs. **No class-2 cell (`C2_XY4`, `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH`) has run, and therefore campaign 33 has no IBM-noise prediction of the 2x3 family yet.**

### 7.6 `C4_CF`: the near-clean correction redone on the GPU (FAIL 7/8 on S6 only; job 59736866)

The Pauli-trajectory decomposition of `CF_traj` was redone with $K=2000$ target trajectories per arm; the 3 600 s job ended every arm at its 600 s deadline after 1 232 / 1 262 / 1 244 / 1 239 trajectories (0.475 s per trajectory against 0.3 s sized). P16 (r per arm with bootstrap intervals) and P17 (floor theorem $\ge0.95$) PASS.

| arm | trajectories $K$ | $f_{\rm hit}$ [95 %] | benign fraction $b$ | $f_{\rm ideal}(10^{-3})$ [95 %] | $r=f_{\rm hit}/f_{\rm ideal}$ [95 %] | floor $\min f_{\rm eff}/f_{\rm ideal}$ over $S_{99}$ | old $r$ (CF_traj, 2026-10-05) |
|---|---|---|---|---|---|---|---|
| `B0_ref25_k1` | 1 232 | 0.2532 [0.2400, 0.2661] | 0.0804 | 0.2386 [0.2265, 0.2507] | **1.0610** [1.0348, 1.0896] | 1.0567 | 1.089 [1.050, 1.136] |
| `B1_ref57_k1` | 1 262 | 0.2350 [0.2238, 0.2476] | 0.0626 | 0.2242 [0.2137, 0.2360] | **1.0483** [1.0156, 1.0823] | 1.0483 | 1.052 [0.987, 1.126] |
| `B0_ref25_k4` | 1 244 | 0.2478 [0.2354, 0.2610] | 0.0474 | 0.2114 [0.2021, 0.2221] | **1.1720** [1.1276, 1.2171] | 1.1720 | 1.115 [1.036, 1.220] |
| `B0_ref25_k1__xx` (bit-flip control) | 1 239 | 0.1831 [0.1787, 0.1878] | 0.0024 | 0.1741 [0.1721, 0.1768] | **1.0517** [1.0295, 1.0754] | 1.0517 | 1.042 [1.001, 1.122] |
| **pooled** | -- | 0.2441 [0.2353, 0.2528] | -- | 0.2314 [0.2231, 0.2395] | **1.0549** [1.0325, 1.0779] | -- | pooled $k=1$ 1.069 [1.029, 1.115] |

(`validation/C4_CF.json -> data.arms, data.pooled`; old values `validation/CF_traj.json`; the old pooled value was over the three $k=1$-type arms.) **$r_{nc}$:** `data.r_nc_new` = 1.0779 (the upper end of the pooled interval) against the signed 1.1151 (`data.r_nc_old`, `data/cf_trajectories/r_nc.json`). `data.owner_item_r_nc_outside_old_interval` reads **false** because the code compares 1.0779 with the old *pooled-$k=1$ interval* [1.0286, 1.1151], which contains it; the planner (`prompts/33c` R4) reads the owner-item rule of `prompts/33` section 6 differently (the new pooled 95 % interval [1.033, 1.078] *excludes* 1.115, so "the owner item fires") and asked the executor to check the rule. **Two readings of one rule; no number is edited; the decision is the owner's (Section 15, item 1).** If $r_{nc}$ were replaced by 1.078 every $\hat f_{\rm ideal}$ would rise by 3.4 % [PLAN, `prompts/33c`] (1.1151/1.0779 = 1.0345 [MINE]) and no plan tier changes. The $k=4$ arm's $r=1.172$ [1.128, 1.217] lies above both 1.078 and 1.115: $r_{nc}$ bounds the $k=1$ excess only, which is all the pooled-$k=1$ statistic uses. The bit-flip control arm (`__xx`: only bit-flip faults) behaves like the others, as before.

*Update 2026-10-15.* The `c33c` executor (`prompts/LOG.md` row 152, step 3) changed the code's owner-item rule so that it fires on section 6 OR section 8 of `prompts/33`; evaluated on job 59736866 it **fires** (the new interval [1.0325, 1.0779] excludes 1.115). The harvested JSON is not rewritten; the assembly evaluates the rule. The two readings of 2026-10-13 are therefore reconciled in the code, and the decision itself stays with the owner (Section 15 item 1). The 2-part `C4_CF` re-request ($K=1\,170$ trajectories per part) is prepared, owner-gated and planned after the maintenance.

### 7.7 `C4_F5_B0`: the first full noisy 2x3 SKQD run (PASS 8/8; job 59736879)

*Definition.* Scenario E7(0.07) (matched-$f$ depolarizing, $p_2=1.1833\times10^{-3}$), variant NAT-O0, sector $B=0$, at the **plan of record for $f=0.10$** (`CV_2x3_plan.json -> data.plan.f=0.10.B=0.final_shots_by_circuit`: 32 circuits, 267 shots for most $k\le3$ circuits up to 17 600 shots for `B0_ref25_k4`; 34 909 shots in all). Sampling in 203 `run()` calls in 954 s wall (0.02734 s/shot), 40 rounds, 0 out-of-memory retries; seeds from the run's own F token (stride 476). The in-job CV3 sample used $N_{\rm eq}=1100$ shots per circuit ($k\le4$) plus 8 extra $k=5$ circuits. All CV criteria are *information* in campaign 33 (the plan-of-record check is `CV_2x3_plan`); P13 and P14 are the gate's criteria.

*Result (all from `data.frun`).*

| quantity | value |
|---|---|
| accepted shots / total | 6 848 / 34 909 (19.6 %) |
| $\lvert B_{\rm all}\rvert$ (distinct accepted states plus references) | **372 of 677** |
| $E_R-E_0$ (all) at $N$ | **$2.427\times10^{-4}$** (the gate's bootstrap, 2 000 multinomial resamples of the shots within each circuit, gives 95 % [$3.71\times10^{-4}$, $8.81\times10^{-4}$], mean $5.01\times10^{-4}$: this band does **not** contain the point value; a resample can lose rare states but not create new ones, so I read the band as pessimistic, an interpretation of mine) |
| certificate (owner-confirmed reading, `kato_temple_exact_E1`) | interval [-5.603190, -5.602358], **width $8.32\times10^{-4}$**, $E_0=-5.6026004579$ inside |
| Weinstein $r_H$ at $N$ | 0.04753; interval [-5.649888, -5.602358] |
| captured weight $W$ | **0.999972** (bootstrap [0.99990, 0.99996]) |
| recall of $S_{999}$ / $S_{99}$ on $B_{\rm all}$ | **1.0 / 1.0** (bootstrap recall of $S_{999}$ [0.988, 1.0]) |
| $E_{\rm tol}$ | $1.42252\times10^{-2}$ (equal to `CV_2x3_plan`'s, difference 0) |
| CV1 (shots: $E_R(N/2)-E_R(N)$) | $3.90\times10^{-4}$ = 0.027 $E_{\rm tol}$: PASS |
| CV2 (certificate width at $N/2$ and $N$, Kato-Temple, limit 0.1) | $2.10\times10^{-3}$ and $8.32\times10^{-4}$, $E_0$ inside both: PASS |
| CV3 (Krylov $k=4\to5$ at equal shots) | $\Delta E_R=3.54\times10^{-4}$ = 0.0249 $E_{\rm tol}$ ($E_R(k\!\le\!4)=-5.602084$, $\lvert B\rvert=334$; $E_R(k\!\le\!5)=-5.602438$, $\lvert B\rvert=395$; 35 200 and 44 000 shots): PASS |
| CV4 (better than random equal-size bases) | below the random 2.5th percentile at all 5 points; margin at $N$ 0.0695 = **4.89 $E_{\rm tol}$**; $W_{\rm rand,97.5}=0.9876$: PASS |
| CV5 ($W\ge0.99$) | 0.999972 ($B_{\rm sig}$: 0.999931): PASS |
| pooled $k=1$ clean fraction (8 circuits, 2 136 shots, 284 reference hits, 0.002 from garbage) | $f_{\rm hit}=0.1445$ [0.1282, 0.1623]; $\hat f_{\rm ideal}=0.1296$ [0.1149, 0.1455]; GO rule v3 reads **GO** (information) |
| $k=4$ circuits (e.g. `B0_ref25_k4`, 17 600 shots) | $f_{\rm hit}=0.1407$ [0.1295, 0.1525] |

*The shot-count curve* (nested prefixes of the same shot stream; `data.cv.shots_curve`, $B_{\rm all}$ basis):

| shots $N$ | accepted | $\lvert B_{\rm all}\rvert$ | $E_R-E_0$ | Kato-Temple width | $r_H$ | $W$ | recall $S_{999}$ |
|---|---|---|---|---|---|---|---|
| 2 188 | 446 | 125 | $1.052\times10^{-2}$ | 0.03007 | 0.2851 | 0.998553 | 0.826 |
| 4 357 | 866 | 175 | $5.708\times10^{-3}$ | 0.01678 | 0.2132 | 0.999245 | 0.919 |
| 8 734 | 1 719 | 223 | $1.628\times10^{-3}$ | 0.00536 | 0.1205 | 0.999808 | 0.988 |
| 17 468 | 3 442 | 300 | $6.33\times10^{-4}$ | 0.00210 | 0.0755 | 0.999925 | 1.000 |
| 34 909 | 6 848 | 372 | $2.43\times10^{-4}$ | 0.00083 | 0.0475 | 0.999972 | 1.000 |

*Comparison with the project's earlier emulation (`CV_2x3_plan`, S1-proxy noise at $0.7f$, $f=0.10$, three seeds).* At the same plan and the same $N$ the proxy gave $E_R-E_0=3.03/2.57/3.73\times10^{-3}$ with $\lvert B_{\rm all}\rvert=201/208/185$ and Kato-Temple width at $N$ $0.0082/0.0075/0.0110$ (`validation/CV_2x3_plan.json -> data.curves, data.criteria_by_seed`), i.e. the Aer run is **10 to 15 times better in energy error and about 10 to 13 times narrower in certified width** [MINE: ratios 3.03e-3/2.43e-4 = 12.5, 2.57e-3/2.43e-4 = 10.6, 3.73e-3/2.43e-4 = 15.4; widths 0.0082/8.3e-4 = 9.9, 0.0110/8.3e-4 = 13.2]. The reason is the clean fraction: the proxy samples at an effective $0.7f=0.07$ while F5's measured $\hat f_{\rm ideal}=0.130$ is 1.9 times larger [MINE: 0.1296/0.07] and the Aer noise also feeds more accepted garbage states into $B_{\rm all}$ (372 against about 200), which helps recall. **The S1 proxy used to size the 2x3 plan is therefore conservative relative to this Aer model**; whether it is conservative relative to a real device is exactly the open question. The comparison is not like-for-like in $f$ (the label "0.07" of E7 refers to the gate-only analytic $f$, Section 7.4 item 4).


*Strength.* One scenario, one sector, one seed set. The gate's PASS means P13 (variational, nested, $E_0$ inside the certificate) and P14 (recall $\ge0.9$) hold, plus the five S-criteria. Its $B=1$ partner (F5_B1, 99 000 shots in two parts) and two more $B=0$ runs under the published H2-2 rates (F1_B0, F7_B0) have now returned (Section 7.8).

### 7.8 All 25 class-4 run files, one row each (new, 2026-10-15)

*What a row is.* Each row is one GPU job (one JSON file) of a full noisy 2x3 SKQD run: sample the 32 ($B=0$) or 12 ($B=1$) signed circuits of one sector under one noise scenario, decode, build $B_{\rm all}$ (all accepted states plus the references), compute the Ritz energy $E_R$, the certificate and the support metrics. A run that did not fit one 60-minute job was **split into parts** (`data/campaign33/sizing_33a.json -> runs.<run>.parts`); part 1 is run by the F token itself, part 2 by a generic slot `C4_PART_NN` (Section 7.9). For a part, every number in the row is computed **on that part's shots alone**; the merged run is computed only at assembly (not yet done). The scenario labels are those of Section 7.1 (E1 = published H2-2 rates; E7(f) = matched-$f$ depolarizing; E8 = gate S3's declared model on the qiskit-transpiled IR-L3-RZZ family); "KT" = Kato-Temple with the exact $E_1$ (the $B=0$ reading, owner decision 2026-10-05), "Weinstein" = the $B=1$ reading (width $=r_H$). The $f_{\rm hit}$ and $\hat f_{\rm ideal}=f_{\rm hit}/1.1151$ columns are the pooled $k=1$ reference-hit statistics of that file (8 circuits at $B=0$, 3 at $B=1$) with 95 % Garwood intervals. "CV1-CV5" lists P (pass), F (fail) or n/e (not evaluated); for split runs they are evaluated at assembly only. Sources: each file's `data.frun.at_N.certificate`, `data.frun.clean_fraction.pooled_k1`, `data.frun.cv.criteria`, `criteria`; job ids from `ci/status/<TOKEN>.json`. The CSV version is block (ae).

| # | token (job) | run: scenario x family, sector | kind | part | shots done / requested | accepted | $\lvert B_{\rm all}\rvert$ | $E_R-E_0$ | certificate | width | $E_0$ in | recall $S_{999}$ | $W$ | $f_{\rm hit}$ [95 %] | $\hat f_{\rm ideal}$ [95 %] | CV1-CV5 | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `C4_F5_B0` (59736879) | F5_B0: E7(0.07) x NAT-O0, B=0 | plan, tier 0.1 | 1/1 | 34909 / 34909 | 6848 | 372 | $2.427\times10^{-4}$ | KT | $8.325\times10^{-4}$ | yes | 1.000 | 0.999972 | 0.1445 [0.1282, 0.1623] | 0.1296 [0.1149, 0.1455] | P P P P P | PASS 8/8 |
| 2 | `C4_F1_B0` (59739276) | F1_B0: E1 x NAT-O0, B=0 | plan, tier 0.15 | 1/1 | 27309 / 27309 | 8507 | 322 | $3.290\times10^{-4}$ | KT | $1.145\times10^{-3}$ | yes | 1.000 | 0.999962 | 0.2544 [0.2326, 0.2777] | 0.2281 [0.2085, 0.2490] | P P P P P | PASS 8/8 |
| 3 | `C4_F7_B0` (59739278) | F7_B0: E1 x NAT-O2, B=0 | plan, tier 0.15 | 1/1 | 27309 / 27309 | 8447 | 326 | $3.349\times10^{-4}$ | KT | $1.085\times10^{-3}$ | yes | 1.000 | 0.999959 | 0.2483 [0.2267, 0.2713] | 0.2226 [0.2033, 0.2433] | P P n/e P P | PASS 8/8 |
| 4 | `C4_F5_B1` (59739280) | F5_B1: E7(0.07) x NAT-O0, B=1 | plan, tier 0.1 | 1/2 | 49500 / 49500 | 9554 | 346 | $1.760\times10^{-4}$ | Weinstein | $3.635\times10^{-2}$ | yes | 1.000 | 0.999975 | 0.1271 [0.1040, 0.1539] | 0.1140 [0.0933, 0.1380] | at assembly | PASS 7/7 |
| 5 | `C4_PART_01` (59739282) | F5_B1: E7(0.07) x NAT-O0, B=1 | plan, tier 0.1 | 2/2 | 49500 / 49500 | 9432 | 336 | $3.395\times10^{-4}$ | Weinstein | $4.807\times10^{-2}$ | yes | 1.000 | 0.999948 | 0.1332 [0.1095, 0.1605] | 0.1194 [0.0982, 0.1440] | at assembly | PASS 8/8 |
| 6 | `C4_F1_B1` (59779331) | F1_B1: E1 x NAT-O0, B=1 | plan, tier 0.15 | 1/2 | 33800 / 33800 | 10273 | 313 | $2.920\times10^{-4}$ | Weinstein | $4.645\times10^{-2}$ | yes | 1.000 | 0.999959 | 0.2373 [0.2053, 0.2730] | 0.2128 [0.1841, 0.2448] | at assembly | PASS 7/7 |
| 7 | `C4_PART_10` (59779334) | F1_B1: E1 x NAT-O0, B=1 | plan, tier 0.15 | 2/2 | 33800 / 33800 | 10104 | 312 | $2.376\times10^{-4}$ | Weinstein | $4.367\times10^{-2}$ | yes | 1.000 | 0.999968 | 0.2482 [0.2154, 0.2846] | 0.2226 [0.1932, 0.2553] | at assembly | PASS 8/8 |
| 8 | `C4_F7_B1` (59779337) | F7_B1: E1 x NAT-O2, B=1 | plan, tier 0.15 | 1/2 | 33800 / 33800 | 10212 | 319 | $4.229\times10^{-4}$ | Weinstein | $5.365\times10^{-2}$ | yes | 1.000 | 0.999936 | 0.2676 [0.2335, 0.3053] | 0.2400 [0.2094, 0.2738] | at assembly | PASS 7/7 |
| 9 | `C4_PART_11` (59779338) | F7_B1: E1 x NAT-O2, B=1 | plan, tier 0.15 | 2/2 | 33800 / 33800 | 10172 | 317 | $3.055\times10^{-4}$ | Weinstein | $4.799\times10^{-2}$ | yes | 1.000 | 0.999958 | 0.2567 [0.2233, 0.2937] | 0.2302 [0.2003, 0.2634] | at assembly | PASS 8/8 |
| 10 | `C4_F4_B0a` (59742843) | F4_B0a: E7(0.10) x NAT-O0, B=0 | S3 quota, half a | 1/2 | 50016 / 50016 | 12159 | 376 | $1.212\times10^{-4}$ | KT | $4.585\times10^{-4}$ | yes | 1.000 | 0.999987 | 0.1943 [0.1863, 0.2025] | 0.1743 [0.1671, 0.1816] | at assembly | PASS 7/7 |
| 11 | `C4_PART_02` (59745007) | F4_B0a: E7(0.10) x NAT-O0, B=0 | S3 quota, half a | 2/2 | 45696 / 49984 | 11125 | 353 | $2.693\times10^{-4}$ | KT | $9.161\times10^{-4}$ | yes | 1.000 | 0.999969 | 0.1909 [0.1826, 0.1994] | 0.1712 [0.1638, 0.1789] | at assembly | FAIL 7/8 (S6) |
| 12 | `C4_F4_B0b` (59747539) | F4_B0b: E7(0.10) x NAT-O0, B=0 | S3 quota, half b | 1/2 | 50016 / 50016 | 12268 | 360 | $3.037\times10^{-4}$ | KT | $1.042\times10^{-3}$ | yes | 1.000 | 0.999965 | 0.1860 [0.1782, 0.1940] | 0.1668 [0.1598, 0.1740] | at assembly | PASS 7/7 |
| 13 | `C4_PART_04` (59747548) | F4_B0b: E7(0.10) x NAT-O0, B=0 | S3 quota, half b | 2/2 | 45696 / 49984 | 11150 | 371 | $1.817\times10^{-4}$ | KT | $6.153\times10^{-4}$ | yes | 1.000 | 0.999979 | 0.1786 [0.1706, 0.1869] | 0.1602 [0.1530, 0.1676] | at assembly | FAIL 7/8 (S6) |
| 14 | `C4_F4_B1a` (59745015) | F4_B1a: E7(0.10) x NAT-O0, B=1 | S3 quota, half a | 1/2 | 50004 / 50004 | 11919 | 298 | $3.130\times10^{-4}$ | Weinstein | $5.075\times10^{-2}$ | yes | 1.000 | 0.999959 | 0.1858 [0.1780, 0.1938] | 0.1666 [0.1596, 0.1738] | at assembly | PASS 7/7 |
| 15 | `C4_PART_03` (59745024) | F4_B1a: E7(0.10) x NAT-O0, B=1 | S3 quota, half a | 2/2 | 49992 / 49992 | 11947 | 286 | $3.825\times10^{-4}$ | Weinstein | $5.654\times10^{-2}$ | yes | 1.000 | 0.999951 | 0.1834 [0.1756, 0.1914] | 0.1644 [0.1575, 0.1716] | at assembly | PASS 8/8 |
| 16 | `C4_F4_B1b` (59747551) | F4_B1b: E7(0.10) x NAT-O0, B=1 | S3 quota, half b | 1/2 | 50004 / 50004 | 11860 | 288 | $1.053\times10^{-3}$ | Weinstein | $8.923\times10^{-2}$ | yes | 0.989 | 0.999851 | 0.1771 [0.1695, 0.1850] | 0.1589 [0.1520, 0.1659] | at assembly | PASS 7/7 |
| 17 | `C4_PART_05` (59747553) | F4_B1b: E7(0.10) x NAT-O0, B=1 | S3 quota, half b | 2/2 | 49992 / 49992 | 11927 | 280 | $4.909\times10^{-4}$ | Weinstein | $6.268\times10^{-2}$ | yes | 1.000 | 0.999935 | 0.1795 [0.1719, 0.1875] | 0.1610 [0.1541, 0.1681] | at assembly | PASS 8/8 |
| 18 | `C4_F8_B0a` (59749780) | F8_B0a: E8 x IR-L3-RZZ, B=0 | S3 quota, half a | 1/2 | 50016 / 50016 | 9686 | 395 | $2.555\times10^{-4}$ | KT | $9.577\times10^{-4}$ | yes | 1.000 | 0.999974 | 0.1291 [0.1227, 0.1359] | 0.1158 [0.1100, 0.1218] | at assembly | PASS 7/7 |
| 19 | `C4_PART_06` (59749784) | F8_B0a: E8 x IR-L3-RZZ, B=0 | S3 quota, half a | 2/2 | 49984 / 49984 | 9836 | 383 | $2.542\times10^{-4}$ | KT | $9.260\times10^{-4}$ | yes | 1.000 | 0.999972 | 0.1329 [0.1263, 0.1397] | 0.1192 [0.1133, 0.1253] | at assembly | PASS 8/8 |
| 20 | `C4_F8_B0b` (59780912) | F8_B0b: E8 x IR-L3-RZZ, B=0 | S3 quota, half b | 1/2 | 50016 / 50016 | 9798 | 389 | $1.255\times10^{-4}$ | KT | $4.817\times10^{-4}$ | yes | 1.000 | 0.999987 | 0.1370 [0.1303, 0.1439] | 0.1228 [0.1168, 0.1290] | at assembly | PASS 7/7 |
| 21 | `C4_PART_08` (59780915) | F8_B0b: E8 x IR-L3-RZZ, B=0 | S3 quota, half b | 2/2 | 49984 / 49984 | 9860 | 387 | $2.136\times10^{-4}$ | KT | $6.943\times10^{-4}$ | yes | 1.000 | 0.999974 | 0.1357 [0.1291, 0.1427] | 0.1217 [0.1158, 0.1279] | at assembly | PASS 8/8 |
| 22 | `C4_F8_B1a` (59752618) | F8_B1a: E8 x IR-L3-RZZ, B=1 | S3 quota, half a | 1/2 | 50004 / 50004 | 9658 | 272 | $4.864\times10^{-4}$ | Weinstein | $6.247\times10^{-2}$ | yes | 1.000 | 0.999934 | 0.1346 [0.1280, 0.1415] | 0.1207 [0.1148, 0.1269] | at assembly | PASS 7/7 |
| 23 | `C4_PART_07` (59752623) | F8_B1a: E8 x IR-L3-RZZ, B=1 | S3 quota, half a | 2/2 | 49992 / 49992 | 9542 | 277 | $7.717\times10^{-4}$ | Weinstein | $7.905\times10^{-2}$ | yes | 1.000 | 0.999899 | 0.1370 [0.1303, 0.1439] | 0.1228 [0.1168, 0.1291] | at assembly | PASS 8/8 |
| 24 | `C4_F8_B1b` (59780919) | F8_B1b: E8 x IR-L3-RZZ, B=1 | S3 quota, half b | 1/2 | 50004 / 50004 | 9508 | 287 | $3.992\times10^{-4}$ | Weinstein | $5.533\times10^{-2}$ | yes | 1.000 | 0.999945 | 0.1359 [0.1292, 0.1428] | 0.1219 [0.1159, 0.1281] | at assembly | PASS 7/7 |
| 25 | `C4_PART_09` (59782656) | F8_B1b: E8 x IR-L3-RZZ, B=1 | S3 quota, half b | 2/2 | 49992 / 49992 | 9551 | 286 | $7.720\times10^{-4}$ | Weinstein | $7.507\times10^{-2}$ | yes | 0.989 | 0.999890 | 0.1353 [0.1287, 0.1422] | 0.1214 [0.1154, 0.1276] | at assembly | PASS 8/8 |

*Constant across all 25 files* (read from the files): $E_0$ inside the certificate in 25 of 25; the variational check P13 passes in 25 of 25 (no $E_R<E_0-10^{-9}$); recall of the 99.9 % support $S_{999}$ is 1.000 in 23 files and 0.989 (94 of 95 states) in `C4_F4_B1b` and `C4_PART_09`; captured weight $W\ge0.99985$ everywhere; $E_R-E_0$ between $1.21\times10^{-4}$ and $1.05\times10^{-3}$; Kato-Temple widths at $B=0$ between $4.59\times10^{-4}$ and $1.15\times10^{-3}$ (the signed limit is 0.1, i.e. 87 to 218 times wider [MINE]); Weinstein widths at $B=1$ between 0.0364 and 0.0892 (the signed limit $r_H\le0.15$). **The project's 2x3 certificate criteria (H1 width $\le0.1$ at $B=0$ on Kato-Temple; H2 $r_H\le0.15$ at $B=1$) are met in every file, in simulation, under every scenario run so far.**

*The CV1-CV5 values of the three single-job runs* (`data.frun.cv.criteria`; $E_{\rm tol}=1.42252\times10^{-2}$ in all three, equal to `CV_2x3_plan`'s):

| criterion | F5_B0 (E7(0.07), NAT-O0) | F1_B0 (E1, NAT-O0) | F7_B0 (E1, NAT-O2) |
|---|---|---|---|
| CV1: $E_R(N/2)-E_R(N)$, ratio to $E_{\rm tol}$ | $3.90\times10^{-4}$, 0.027: P | $4.51\times10^{-4}$, 0.032: P | $4.38\times10^{-4}$, 0.031: P |
| CV2: KT width at $N/2$ and $N$; $E_0$ inside | $2.10\times10^{-3}$ / $8.32\times10^{-4}$; yes: P | $2.75\times10^{-3}$ / $1.15\times10^{-3}$; yes: P | $2.59\times10^{-3}$ / $1.08\times10^{-3}$; yes: P |
| Weinstein $r_H$ at $N/2$ / $N$ (information) | 0.0755 / 0.0475 | 0.0864 / 0.0557 | 0.0838 / 0.0543 |
| CV3: $\Delta E_R$ for $k\le4\to k\le5$ at equal shots, ratio; sizes; shots | $3.54\times10^{-4}$, 0.025; 334 / 395; 35 200 / 44 000: P | $1.16\times10^{-4}$, 0.008; 319 / 392; 28 800 / 36 000: P | not evaluated ("not a NAT-O0 plan-of-record run": the equal-shots samples were not taken) |
| CV4: points below the random 2.5th percentile; margin at $N$ ($E_{\rm tol}$ units); random $W_{97.5}$ | 5/5; 0.0695 (4.89); 0.9876: P | 5/5; 0.0817 (5.74); 0.9842: P | 5/5; 0.0821 (5.77); 0.9839: P |
| CV5: $W$ ($B_{\rm all}$ / $B_{\rm sig}$) | 0.999972 / 0.999931: P | 0.999962 / 0.999909: P | 0.999959 / 0.999899: P |
| accepted fraction | 6 848 / 34 909 = 0.196 | 8 507 / 27 309 = 0.312 | 8 447 / 27 309 = 0.309 |
| `B0_ref25_k4` $f_{\rm hit}$ (shots: 17 600 in F5_B0, 1 400 in F1_B0 and F7_B0) | 0.1407 [0.1295, 0.1525] | 0.2388 [0.1891, 0.2976] | 0.2509 [0.1998, 0.3110] |

(Accepted fractions are my divisions of the files' `accepted` by the shots.) The shot curves of the three runs are block (af).

*A systematic feature of the bootstrap.* In **all 25** files the point value $E_R-E_0$ lies **below** the lower end of the gate's 95 % bootstrap band (2 000 multinomial resamples of the shots within each circuit; e.g. F1_B0: point $3.29\times10^{-4}$, band [$4.77\times10^{-4}$, $8.72\times10^{-4}$]; block (ae) columns `boot_err_lo/hi`) [MINE count]. A resample can lose rare states but never adds new ones, so the bootstrap of a support-based energy is biased upwards; the band is a pessimistic spread, not a confidence interval for the point value (my interpretation, as in the 2026-10-13 report for F5_B0; no project file states it).

### 7.9 Parts, halves, and what the two S6 failures mean

*Halves.* F4 and F8 run the **S3 quota**: $2\times10^5$ shots per sector, as the manual's Step 9.2 and gate S3 asked, in two independently seeded halves `a` and `b` of $10^5$ each (`kind: s3quota`). *Parts.* Each half (and each $B=1$ plan run: 99 000 shots for F5_B1, 67 600 for F1_B1 and F7_B1) exceeds what one job can sample ($N_{\max}$ 53 758 for plan runs and 67 197 for quota runs at the sized rate, `sizing_33a.json`), so it is cut into 2 parts by the "equal-fraction" rule: every circuit's chunk plan is split at the same fraction, part 1 takes shots $[0, N_c/2)$ of each circuit and part 2 takes $[N_c/2, N_c)$ (e.g. `C4_PART_02` covers shots 1 563-3 125 of each of the 32 $B=0$ circuits). Both parts are seeded from the run's own F token with the global chunk index (`prompts/33b` R4), so concatenating them reproduces the unsplit run seed for seed. Mapping (from each file's `data.part` and `ci/parts`): F5_B1 = `C4_F5_B1` + `C4_PART_01`; F4_B0a = `C4_F4_B0a` + `C4_PART_02`; F4_B1a = `C4_F4_B1a` + `C4_PART_03`; F4_B0b = `C4_F4_B0b` + `C4_PART_04`; F4_B1b = `C4_F4_B1b` + `C4_PART_05`; F8_B0a + `C4_PART_06`; F8_B1a + `C4_PART_07`; F8_B0b + `C4_PART_08`; F8_B1b + `C4_PART_09`; F1_B1 + `C4_PART_10`; F7_B1 + `C4_PART_11`.

*What S6 is and why `C4_PART_02` and `C4_PART_04` failed it.* S6 reads "shots $\ge$ the token's minimum (C4_F*: the plan of record in full)", threshold "no reduction below the minimum". Both slots were asked for 49 984 shots (1 562 per circuit) and took **45 696** (1 428 per circuit), i.e. 91.4 % [MINE]. The sampler stopped itself by its deadline rule after the first round of 32 calls: `data.frun.sampling.stopped` = {round 1, reason "deadline", predicted_round_s 1 186.2, seconds_left 1 049.3, rule "call_bound: $t(s)\le t_p\max(1,s/s_p)$ from the measured point"}. The predicted 1 186 s is exactly 32 times the cost of one full 1 428-shot call [MINE: 1 186.22 / 32 = 37.07 s = 1 428 x 0.02596 s/shot]: the bound charges a call of only 134 remaining shots as if it were a full chunk (the factor $\max(1, s/s_p)$ never goes below 1), which is the conservative rule introduced after the zero-shot bug of C2_CAL run 2 (Section 6.28). Their sibling files `C4_F4_B0a` and `C4_F4_B0b` took 1 563 shots per circuit in full, and the four $B=1$ files of F4 (12 circuits per round, not 32) were not stopped. **What it means.** (1) The physics criteria of both files pass (P13 variational; $E_0$ inside; recall 1.0; widths $9.2\times10^{-4}$ and $6.2\times10^{-4}$); (2) no shot was lost to an error: the shots that were taken are complete chunks of the unsplit plan; (3) the F4 $B=0$ sector therefore holds 191 424 of its $2\times10^5$ quota shots (95.7 % [MINE]), so the S3-quota reading of F4 at $B=0$ is 8 576 shots short; (4) by the rule of `ci/parts/README.md` ("A part JSON with `full: false`: re-size that run's remaining parts with the script, at most 2 re-requests per run"), the 4 288 missing shots per half are to be re-sized and re-requested; **no such request exists yet** (the requests of 2026-10-15 are F2 and slots 12-17); (5) it is a budget-rule failure, not a physics failure, of the same kind as `C4_FCELLS_A` and `C4_CF`.

### 7.10 What the 25 files say together

*Per-run summary, pooled over parts and halves [MINE].* The assembly has not run, so no project file holds the merged runs. The table below is my own arithmetic from sourced numbers: the pooled $k=1$ reference-hit statistic recomputed from the files' own pooled fields (numerator $n_{\rm ref}-$ garbage, denominator recovered as $(n_{\rm ref}-g)/f_{\rm hit}$ per file, summed; 95 % Garwood interval on the summed count; this recipe reproduces the file's own interval exactly for F5_B0: [0.12817, 0.16230]); $\hat f_{\rm ideal}=f_{\rm hit}/1.1151$. The two "bound" columns are **rigorous bounds** that hold whatever the assembly finds, because the assembly sums the accepted counts of the parts (`assemble.merge_halves`, `merge_run`), so the merged support contains every part's support: by the variational principle the merged $E_R$ is at most the smallest part $E_R$, and the merged recall and $W$ are at least the largest part values. The certificate width of the merged run is not bounded this way (it depends on $r_H$) and is not computed. Block (ag) is the CSV.

| run | scenario | sector | kind | files | shots done / requested | pooled $k=1$ reference hits / shots | pooled $f_{\rm hit}$ [95 %] | pooled $\hat f_{\rm ideal}$ [95 %] | rigorous bound on the merged $E_R-E_0$ (min over files) | recall $S_{999}$ of the merged support (lower bound = max over files) | certificate widths of the files |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F5_B0 | E7(0.07) | B=0 | plan 0.10 | 1 | 34909 / 34909 | 284 / 2136 | 0.1445 [0.1282, 0.1623] | 0.1296 [0.1149, 0.1455] | $\le 2.43\times10^{-4}$ | $\ge 1.000$ | KT 0.00083-0.00083 |
| F1_B0 | E1 | B=0 | plan 0.15 | 1 | 27309 / 27309 | 500 / 2136 | 0.2544 [0.2326, 0.2777] | 0.2281 [0.2085, 0.2490] | $\le 3.29\times10^{-4}$ | $\ge 1.000$ | KT 0.0011-0.0011 |
| F7_B0 | E1 (NAT-O2) | B=0 | plan 0.15 | 1 | 27309 / 27309 | 488 / 2136 | 0.2483 [0.2267, 0.2713] | 0.2226 [0.2033, 0.2433] | $\le 3.35\times10^{-4}$ | $\ge 1.000$ | KT 0.0011-0.0011 |
| F5_B1 | E7(0.07) | B=1 | plan 0.10 | 2 | 99000 / 99000 | 215 / 1800 | 0.1302 [0.1134, 0.1488] | 0.1167 [0.1017, 0.1334] | $\le 1.76\times10^{-4}$ | $\ge 1.000$ | Weinstein 0.036-0.048 |
| F1_B1 | E1 | B=1 | plan 0.15 | 2 | 67600 / 67600 | 401 / 1800 | 0.2428 [0.2196, 0.2678] | 0.2177 [0.1969, 0.2401] | $\le 2.38\times10^{-4}$ | $\ge 1.000$ | Weinstein 0.044-0.046 |
| F7_B1 | E1 (NAT-O2) | B=1 | plan 0.15 | 2 | 67600 / 67600 | 433 / 1800 | 0.2622 [0.2381, 0.2881] | 0.2351 [0.2135, 0.2583] | $\le 3.06\times10^{-4}$ | $\ge 1.000$ | Weinstein 0.048-0.054 |
| F4_B0 (a+b) | E7(0.10) | B=0 | S3 quota | 4 | 191424 / 200000 | 8261 / 47856 | 0.1876 [0.1836, 0.1917] | 0.1682 [0.1646, 0.1719] | $\le 1.21\times10^{-4}$ | $\ge 1.000$ | KT 0.00046-0.001 |
| F4_B1 (a+b) | E7(0.10) | B=1 | S3 quota | 4 | 199992 / 199992 | 8325 / 49998 | 0.1815 [0.1776, 0.1854] | 0.1627 [0.1593, 0.1663] | $\le 3.13\times10^{-4}$ | $\ge 1.000$ | Weinstein 0.051-0.089 |
| F8_B0 (a+b) | E8 (IR-L3-RZZ) | B=0 | S3 quota | 4 | 200000 / 200000 | 6151 / 50000 | 0.1337 [0.1304, 0.1371] | 0.1199 [0.1169, 0.1229] | $\le 1.26\times10^{-4}$ | $\ge 1.000$ | KT 0.00048-0.00096 |
| F8_B1 (a+b) | E8 (IR-L3-RZZ) | B=1 | S3 quota | 4 | 199992 / 199992 | 6226 / 49998 | 0.1357 [0.1324, 0.1391] | 0.1217 [0.1187, 0.1248] | $\le 3.99\times10^{-4}$ | $\ge 1.000$ | Weinstein 0.055-0.079 |

*Readings (each labelled by its evidence).*

1. **The algorithm works end to end at 2x3 in every scenario run so far** [SIM]: ten runs, three scenario families (E1, E7, E8), two circuit families (Quantinuum-native NAT-O0/O2 and the qiskit-transpiled IR-L3-RZZ), both sectors; $E_0$ is inside the certificate in 25 of 25 files and the certificate widths meet the signed H1/H2 limits with a factor 87-218 to spare at $B=0$ and 1.7-4.1 at $B=1$ [MINE: 0.15/0.0892 and 0.15/0.0364]. This is a statement about the *algorithm under assumed noise models* whose measured $\hat f_{\rm ideal}$ is 0.12 to 0.24, not about any device.
2. **More shots buy little in $B=0$ once $\hat f_{\rm ideal}\gtrsim0.12$** [SIM]: at the plan of record (27 309-34 909 shots) $E_R-E_0$ is $2.4$-$3.4\times10^{-4}$; with the $2\times10^5$-shot quota (F4, F8) the merged run's $E_R-E_0$ is at most $1.2$-$1.3\times10^{-4}$ (the bound of the table above), i.e. at least 2.0-2.6 times smaller for 5.7-7.3 times the shots [MINE ratios; the scenarios differ, E7(0.10)/E8 against E7(0.07)/E1, so this is indicative only]; the Kato-Temple widths of the individual files go from $0.8$-$1.1\times10^{-3}$ (plan) to $0.5$-$1.0\times10^{-3}$ (one quota part of about 50 000 shots).
3. **$B=1$ is the harder sector, as `CV_2x3_plan` predicted** [SIM]: Weinstein widths 0.036-0.089 against 0.15, with recall of $S_{999}$ 0.989 in two of 14 files; the plan-of-record $B=1$ runs used the doubled ($s=2$) plan.
4. **The matched-$f$ labels understate the simulated clean fraction**: E7(0.07) gives a pooled $\hat f_{\rm ideal}$ of 0.130 ($B=0$) and 0.117 ($B=1$); E7(0.10) gives 0.168 and 0.163 [MINE pooled]; the E7 label is the gate-only analytic $f$ at the family's mean counts (Section 7.4 item 4). E8, gate S3's declared model ($\epsilon_2=10^{-3}$ also on $R_z$), gives 0.120 / 0.122 on the IR-L3-RZZ family.
5. **E1 on the exact variant NAT-O2 equals E1 on NAT-O0** within the intervals: $\hat f_{\rm ideal}$ 0.223 versus 0.228 ($B=0$), 0.235 versus 0.218 ($B=1$); $E_R-E_0$ $3.35$ versus $3.29\times10^{-4}$ ($B=0$). The exact circuit rewrite neither helps nor hurts, as the f-cells said (Section 7.4 item 5).
6. **Gate S3's open recall criterion is now answerable in simulation** [SIM, MINE bound]: gate S3 (manual Step 8.3) asked for recall $\ge0.9$ at $2\times10^5$ shots per sector under its declared model. F8 is exactly that model and family at that quota; every F8 file already has recall 1.0 ($B=0$) or $\ge0.989$ ($B=1$), so the merged recall is $\ge1.0$ and $\ge1.0$ respectively (bound of the table above). The formal criterion P15 (recall $\ge0.9$ **and** $E_0$ inside the merged Weinstein interval) is evaluated only at assembly.
7. **The comparison with the project's emulation (`CV_2x3_plan`, S1 proxy at $0.7f$) holds for both sectors**: at $B=0$ the Aer runs are 10-15 times better in $E_R-E_0$ (Section 7.7). At $B=1$, $f=0.10$, the proxy's curve ends at 49 203 shots with $E_R-E_0=2.71$ / $2.24$ / $2.67\times10^{-3}$, $r_H=0.137$ / $0.125$ / $0.143$, recall of $S_{999}$ 0.947 / 0.958 / 0.958 in its three seeds (`validation/CV_2x3_plan.json -> data.curves['f=0.10']['B=1'].<seed>.shots[-1]`); the Aer part `C4_F5_B1` with a comparable 49 500 shots gives $1.76\times10^{-4}$, $r_H=0.0364$, recall 1.0, i.e. 13-15 times smaller error and 3.4-3.9 times narrower Weinstein width [MINE ratios]. The S1 proxy is conservative relative to Aer in both sectors; whether it is conservative relative to a device is unknown.

*Strength of this section.* Moderate-to-strong as simulation (25 files, every number from a gate JSON, the per-run pooling is mine and labelled). Weak as a device prediction: the scenarios are vendor-page error rates or matched-$f$ constructions, the transport (memory) term E5 has no full run yet (F6 deferred), the emulator-parameter scenario E3 that halves the clean fraction has no full run yet (F3 deferred), and F2 (Helios-1 rates) is only requested.

### 7.11 Redo of earlier results: what changed

| earlier result | campaign-33 redo | difference |
|---|---|---|
| gate S3 accepted 695 / 3 200 (E8, IR-L3-RZZ) | `C4_FCELLS_B s3_redo` 656 / 3 200 | -39 (inside the band 650-741) |
| gate S3 recall criterion at $2\times10^5$ per sector (never evaluated) | F8 at the quota: every part recall 1.0 ($B=0$) / $\ge0.989$ ($B=1$); merged recall $\ge1.0$ [MINE bound] | the criterion would pass on recall; P15 at assembly |
| CF_traj pooled $k=1$ $r_{nc}=1.115$ | `C4_CF` pooled 1.055 [1.033, 1.078]; $r_{nc}$ new 1.078 | -0.037 (owner item, Section 15 item 1) |
| CF_traj prediction of E1 hits 362.6 $\pm$ 12.9 | `C4_FCELLS_A` 338 hits | inside the 95 % band [302, 427] |
| `CV_2x3_plan` proxy, $f=0.10$, $B=0$: $E_R-E_0$ about $3\times10^{-3}$ | `C4_F5_B0` $2.43\times10^{-4}$ | the proxy is about 12 times more pessimistic (Section 7.7) |
| `CV_2x3_plan` proxy at $B=1$, $f=0.10$, 49 203 shots: $E_R-E_0$ 2.2-2.7 $\times10^{-3}$, $r_H$ 0.125-0.143 | `C4_F5_B1` (49 500 shots): $1.76\times10^{-4}$, $r_H=0.0364$; `C4_PART_01` $3.40\times10^{-4}$, 0.0481 | the proxy is 13-15 times more pessimistic in energy (Section 7.10 item 7) |
| `A6` dry run (Q0P_2x3, H2-2 noise, 280 shots): $f_{\rm hit}=0.2502$ [0.1927, 0.3195] | E1 f-cell 0.2312 [0.2072, 0.2572]; F1_B0 pooled 0.2544 [0.2326, 0.2777]; F1_B1 0.2428 [0.2196, 0.2678] [MINE pooled] | consistent |
| K1 prediction (IBM, model) versus measured 0 hits | no class-2 cell has run; `C2_KCHK` blocked | pending (Section 8) |
| S1 (emulated recall) | `C1_IDEAL` / `C3_AER` recall 1.0 noiseless; all 25 noisy files recall $\ge0.989$ | consistent |

### 7.12 Queue state and what is next (as of 2026-10-15 17:43 UTC; `scripts/ci_check.sh`)

| state | requests (file number, token, job) |
|---|---|
| done since the 2026-10-13 report (25) | 014 `C4_F1_B0` 59739276; 015 `C4_F7_B0` 59739278; 016 `C4_F5_B1` 59739280; 017 `C4_PART_01` 59739282; 018 `C4_F4_B0a` 59742843; 019 `C4_PART_02` 59745007 (slurm FAILED = gate exit 1); 020 `C4_F4_B1a` 59745015; 021 `C4_PART_03` 59745024; 022 `C4_F4_B0b` 59747539; 023 `C4_PART_04` 59747548 (FAILED); 024 `C4_F4_B1b` 59747551; 025 `C4_PART_05` 59747553; 026 `C4_F8_B0a` 59749780; 027 `C4_PART_06` 59749784; 028 `C4_F8_B1a` 59752618; 029 `C4_PART_07` 59752623; 030 `C4_F1_B1` 59779331; 031 `C4_PART_10` 59779334; 032 `C4_F7_B1` 59779337; 033 `C4_PART_11` 59779338; 034 `C2_KCHK` 59780907 (FAILED); 035 `C4_F8_B0b` 59780912; 036 `C4_PART_08` 59780915; 037 `C4_F8_B1b` 59780919; 038 `C4_PART_09` 59782656 |
| done before (8) | 005 smoke 59552188; 006 `C1_IDEAL` 59570217; 007 `C3_AER` 59570221; 008 `C4_FCELLS_A` 59570315 (FAILED); 010 `C4_FCELLS_B` 59736863; 011 `C4_CF` 59736866 (FAILED); 012 `C2_CAL` 59736871; 013 `C4_F5_B0` 59736879 |
| **pending** (committed `34f73a7`, 2026-10-15 17:37 UTC) | 039 `C4_F2_B0` (E2 = Helios-1 published rates, $B=0$, plan tier 0.15, 27 309 shots, one job); 040 `C4_F2_B1` (E2, $B=1$, part 1 of 2 of 67 600 shots); 041 `C4_PART_12` (F2_B1 part 2 of 2); 042 `C4_PART_13` (f-cell group A, part 1 of 4: 16 dropped cells E1-E3 x O2/O3/O4/O6 and E4 x O1-O4, predicted 1 687 s); 043 `C4_PART_14` and 044 `C4_PART_15` (the CV3 equal-shots sample of F5_B1, parts 1 and 2); 045 `C4_PART_16` and 046 `C4_PART_17` (the CV3 sample of F1_B1, parts 1 and 2) |
| shown "pending" by `ci_check.sh` although their jobs ran | 001-004 and 009 (the status file holds only a token's latest request), plus the legacy `ci/request.txt` entry `S2_2x4` (carried over) |
| next by `prompts/33e` | `C2_KCHK` run 2 (CPU arms only) once 33e steps 1-2 are committed; `C2_XY4` immediately if run 2 reads `production_representation: rm`; `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH` after the maintenance |
| not yet requested | the re-sized remainders of `C4_PART_02` / `04` (Section 7.9); `C4_PART_18..20` (F3_B0 parts 2-4; F3 deferred past the maintenance, 15 jobs); F6 (10 jobs, deferred); the 2-part `C4_CF` re-request; `C3_LE` (needs the owner's `skqd-pecos` environment); `QV_2x4_01..08` (needs the owner's `ci/allowed_jobs.q35` installed); the assembly `scripts/campaign33.py --stage assemble` (laptop, no request) |

**Calendar constraint.** The Perlmutter maintenance runs **2026-10-21 06:00 UTC to 2026-10-28 06:00 UTC** (`prompts/33b` R7, `prompts/33e` R4: reservation `maintenance_20261021`). On 2026-10-13/14 the time from request commit to last harvest was 1.0-5.4 h per wave (block (a2)), so the eight pending requests should return well before it if the queue stays as fast; this is my inference from two days, not a project statement.

## 8. The class-2 representation question: Kraus versus PTA versus RM, C2_CAL to C2_KCHK

Sources: `validation/C2_CAL.json` (run 3, job 59736871), `validation/archive/C2_CAL_job59491475.json` (run 1), `reports/ci-59570318.out` (run 2), `data/campaign33/c33c_diag/summary.json` and its segment files (the `prompts/33c` executor's CPU diagnostics, committed), `data/campaign33/kraus_audit.json`, `data/campaign33/aer_release_notes_check.json`, `validation/C2_KCHK.json` (job 59780907), `validation/dryrun/C2_KCHK.json`, `prompts/33a` R2, `prompts/33c` R1-R3, `prompts/33d` R0-R5, `prompts/33e` R1-R5, `prompts/LOG.md` rows 147, 150, 152, 156. **Status on 2026-10-15: open.** The question moved: on 2026-10-13 it was "is the exact Kraus channel or the RM arm wrong?"; the CPU diagnostics answered "the GPU Kraus arm", and the one job built to decide the production representation (`C2_KCHK`) returned without its CPU reference. Everything that the 2026-10-13 report labelled [EXEC] in this section is now in committed data files and is cited as such.

### 8.1 The question

A real device (`ibm_kingston`, 2026-10-06) ran the 2x3 circuit `B0_ref117_k1` 100 000 times (K1 pilot, Section 6.22). Can a classical simulator of that circuit with IBM's published noise record reproduce the *statistics of the strings* the device returned? This matters because the class-2 simulations (and any "IBM noise" prediction of the campaign) are only as good as this answer. The test statistic is the **mean Hamming weight** $\bar w$ of the 20 measured bits (the number of 1s per string, averaged; a perfectly random string has $\bar w=10$ and standard deviation $\sqrt{20}/2=2.236$) and the 20 per-bit marginals $P(1)$. At the accepted-string rate of the device ($58$ of $10^5$) an accepted-fraction comparison has no power; the Hamming weight does.

### 8.2 What the device did

`validation/C2_CAL.json -> data.K1_device_structure` (from `data/hardware/K1_2x3_ibm_kingston/counts/B0_ref117_k1.json`, job `db2avbe8v0ts73c2i8b0`): $10^5$ strings of the circuit **IBM-T3** (XY4 decoupling pulses in the idle windows), mean Hamming weight **$\bar w=9.77099\pm0.00715$**, standard deviation 2.26026, i.e. a deficit of **0.2290 bits below the unital limit 10**. The 20 marginals lie between 0.445 and 0.507. The measurement (readout) asymmetry alone shifts a uniform string by 0.0631 bits (mean readout survival $P_{00}=0.98630$, $P_{11}=0.97998$), which explains 27.6 % of the deficit (`P4c.K1_device.readout_share`); the rest is relaxation towards $|0\rangle$ that the pulses did not fully symmetrise.

### 8.3 `C2_CAL`, runs 1 to 3 (circuit IBM-T0, not the flown T3)

*Run 1* (job 59491475, 2026-10-07, 783 s): FAIL on its timing-ladder criterion P5 only; it showed cuStateVec faster than the batched-shots mode at every point (Section 6.26) and is archived byte-identically. *Run 2* (job 59570318, 2026-10-09, 250 s): FAIL 8/12; the RM and Kraus arms drew zero shots (a sampler-deadline bug, Section 6.27; fixed in `7d0af48`). *Run 3* (job 59736871, 2026-10-13, 1 828 s): PASS 12/12 with the decision "production = Kraus" (P4a: RM and Kraus disagree). The three arms of run 3:

All three arms: 21 qubits, the 2026-10-06 `ibm_kingston` record (fingerprint `b948ddc8...`), echo $T_2$, IBM-**T0** `B0_ref117_k1` (ALAP-scheduled, the XY4 pulses replaced by delays), cuStateVec on one A100, chunk 128. The three representations of thermal relaxation on the delays (`prompts/33` 1.2, `33a` R2; the labels are the project's):

- **Kraus**: Aer's exact `NoiseModel.from_backend` channel. For the 17 qubits with $T_2\le T_1$ Aer's thermal-relaxation channel is already a mixture of identity, $Z$ and resets; only for qubits 59, 69, 92 and 95 ($T_2>T_1$) is it a genuine Kraus map (445 Kraus delay sites in the model, `rm_check.kraus_in_kraus_model`). Non-unital (it drives populations to $|0\rangle$).
- **PTA** (Pauli-twirled approximation): $p_X=p_Y=\tfrac14(1-e^{-t/T_1})$, $p_Z=\tfrac12(1-e^{-t/T_2})-\tfrac14(1-e^{-t/T_1})$ per delay (Geller and Zhou, arXiv:1305.2021) and every gate error twirled; **unital**, cannot produce a Hamming-weight deficit by construction (its only deficit is readout).
- **RM** (the project's label: "$T_2:=\min(T_2,T_1)$, no Kraus"): the record with $T_2$ clipped at $T_1$ so that every channel is a mixture of Pauli and reset, intended to be as fast as PTA and as faithful as Kraus.

| arm | shots (done) | wall (s) | s/shot at the largest point | $\bar w$ | s.e. | deficit vs 10 | accepted by the decoder | max $\lvert z\rvert$ over 20 marginals vs K1 | **$z_w$ vs the device** |
|---|---|---|---|---|---|---|---|---|---|
| PTA | 512 | 151.0 | 0.2870 | **9.9570** | 0.1021 | 0.0430 | 0 | 2.87 | **+1.82** |
| RM | 1 024 | 387.9 | 0.3539 | **7.4199** | 0.0766 | 2.5801 | 4 | 44.5 | **$-30.55$** |
| Kraus | 640 (stopped by its deadline in round 5) | 1 224.3 | 1.8402 | **2.3984** | 0.1358 | 7.6016 | 1 | 64.2 | **$-54.20$** |
| device (K1, T3) | 100 000 | -- | -- | 9.7710 | 0.0071 | 0.2290 | 58 | -- | -- |

($z_w=(\bar w_{\rm sim}-\bar w_{\rm dev})/\sqrt{{\rm se}^2_{\rm sim}+{\rm se}^2_{\rm dev}}$ is what `P4c` stores; `data.comparisons.P4c_vs_K1`.) Pairwise: **RM versus Kraus** $z_w=+32.20$, max marginal $z=18.06$ (all 20 marginals outside $\pm3$): P4a FAIL, hence `production_representation: kraus` (rule of `prompts/33a`: production = RM iff RM and Kraus agree to $3\sigma$); **PTA versus Kraus** $z_w=+44.47$, max marginal $z=21.71$ (P4b, information). The per-bit marginals $P(1)$: Kraus 0.033-0.184 (a few bits below 0.1), RM 0.091-0.519, PTA 0.451-0.562, device 0.445-0.507 (Block (w)). The reference-string hits and distinct accepted states are zero or one in every arm (the circuit is a $k=1$ circuit of probability 0.93 at the reference but the noise leaves essentially nothing clean at 21 qubits and 5 659 CZ).

**The contradiction in one sentence:** the physically most faithful channel (Kraus) is 54 standard errors from the device, the physically unfaithful unital one (PTA) agrees with it, and the intermediate one (RM) that was supposed to equal Kraus does not.

### 8.4 Explanation 1, now withdrawn: the planner's `prompts/33c` R1-R2

`prompts/33c` (2026-10-13) argued that the 54 $\sigma$ was the circuit variant, not the channel: on IBM-T0 the idle windows are long, a zeroth-order relaxation estimate $\sum_q\tfrac12e^{-t_{{\rm idle},q}/T_{1,q}}$ gave **2.64 bits** [PLAN, `scratch/planner/campaign33c_c2_relaxation_expectation_20261013.json`] and matched Kraus (2.40); the flown T3 with XY4 pulses would symmetrise amplitude damping and give $\bar w\approx10$; and "RM is a bug until proven otherwise" (on physical qubit 53, unchanged by RM, RM gave $P(1)=0.52$ against an expectation of 0.12). **`prompts/33d` R0 withdrew R1 and R2**: the 2.64-bit estimate neglected the measurement-basis rotation (`sx` after the last idle on most qubits) and the $T_2$ dephasing, so it "had no power to tell 2.4 from 7.4"; qubit 53 is dephased at the measurement ($T_2=68\ \mu$s, followed by an `sx`), so $P(1)\approx0.5$ there is expected. What remains of 33c: the device-versus-T0 comparison is still on different circuits, and `C2_XY4` (the flown T3) stays the primary class-2 cell, now with the gap measured against about 7.4 rather than 2.4.

### 8.5 Explanation 2, now evidence: the executor's CPU diagnostics (`data/campaign33/c33c_diag/`, committed 2026-10-13)

| test | result | file |
|---|---|---|
| delay-pass errors on qubit 53 of IBM-T0 `B0_ref117_k1`, RM versus Kraus | identical: 55 delay sites, 407.3 $\mu$s in all, super-operator maximum difference 0.0 on qiskit 1.4.3 / aer 0.15.1 and on 2.5.2 / 0.17.2 | `delays_q53_qiskit1.4.3.json`, `delays_q53_qiskit2.5.2.json` |
| one qubit: $x$, delay 400 $\mu$s, measure on qubit 53, 20 000 shots each | RM $P(1)=0.2614$ ($z=+2.07$), Kraus 0.2510 ($z=-1.32$) against $e^{-400/292.7}=0.2550$ | `oneq_q53_*.json` |
| full circuit on the **CPU**, same software as the CI (qiskit 1.4.3, aer 0.15.1, numpy 2.5.3; laptop, 12 threads) | **Kraus $\bar w=7.474\pm0.559$** (19 shots, 173.9 s/shot); **RM $6.917\pm0.571$** (24 shots, 84.0 s/shot) | `summary.json -> arms.cpu_kraus`, `arms.cpu_rm` |
| CPU Kraus vs CPU RM | $z_w=+0.70$, max marginal $\lvert z\rvert$ 2.59: agree | `summary.json -> comparisons` |
| CPU Kraus vs GPU Kraus (C2_CAL run 3) | $z_w=+8.83$: **disagree** | same |
| CPU Kraus vs GPU RM | $z_w=+0.10$, max marginal 2.83: agree | same |
| CPU RM vs GPU RM | $z_w=-0.87$, but max marginal $\lvert z\rvert$ 13.15 on clbits 1 and 2: flagged | same |
| CPU RM vs GPU Kraus | $z_w=+7.70$: disagree | same |

*What this established* (`prompts/33d` R0): the channels of RM and Kraus are identical where they should be, the CPU executes Kraus and RM consistently with each other and with the GPU's RM, and **the one arm that disagrees with everything else is Kraus on the GPU**. The flag on the CPU-RM-versus-GPU-RM marginals (CPU RM saw 0 ones in 24 shots on clbits 1 and 2 where the GPU gives 0.145 and 0.120) is the reason `C2_KCHK` carries a CPU RM arm. The 13.15 is partly an artefact of the per-arm binomial sigma, which is zero when an observed marginal is 0 (the executor's flag, `prompts/LOG.md` row 156).

### 8.6 `prompts/33d` (2026-10-13): the GPU Kraus path is the suspect; the audit; the design of `C2_KCHK`

- **R1:** production for class 2 is RM on the GPU **conditional on `C2_KCHK`**: RM is Kraus's exact channel on 17 of 21 qubits and differs on four (59, 69, 92, 95) only by $T_2:=\min(T_2,T_1)$ (at most a factor 1.23 in $T_2$), contains no Kraus instruction and costs 0.35 s/shot; CPU Kraus (174 s/shot on the laptop) is not a production engine.
- **R2, the audit** (`data/campaign33/kraus_audit.json`, written by `scripts/campaign33_kraus_audit.py`): every class-4 builder (E0-E8) and CF emits only Pauli/depolarizing/readout errors (0 Kraus instructions); Kraus instructions exist only in `ibm_spec(..., 'kraus')` for I-GATE (6 580 `to_dict` entries), I-ECHO and I-COH (6 580 + 445 delay-pass), I-XY4 (6 580 + 269); 0 in I-STAR (where $T_2^*\le T_1$ everywhere). **Consequence: only the Kraus arms of `C2_CAL` runs 1-3 used the suspect path; nothing harvested from classes 1, 3, 4 or `C4_CF` is affected and nothing is re-run.**
- **R3, token `C2_KCHK`** (60 min, 1 GPU): Kraus on cuStateVec (256 shots), RM on cuStateVec (512), Kraus on Aer's native GPU kernels (target 256, minimum 64), Kraus on cuStateVec without gate fusion (target 128, minimum 32), and Kraus and RM on the CPU in a separate process (minimum 16 each); decisions **K1** `bug_confirmed` iff $\lvert z_w(\text{kraus\_gpu\_cusv},\text{kraus\_cpu})\rvert>3$; **K2** `production_representation` = rm iff RM on the GPU agrees with both CPU arms ($\lvert z_w\rvert\le3$ and no marginal beyond $3\sigma$; Bonferroni false-alarm expectation 0.054), else blocked; **K3** `validated_kraus_gpu_path` = the first GPU Kraus engine that agrees with CPU Kraus, else none.
- **R4:** an upstream issue to qiskit-aer after confirmation (the owner files it); the release notes of aer 0.16.0-0.17.2 contain no relevant fix and an issue search for "kraus custatevec" gave 0 results (`data/campaign33/aer_release_notes_check.json`, read 2026-10-13).
- **R5:** C2_CAL run 3's decision "production = Kraus" does not stand; `C2_KCHK` supersedes the field; the C2_CAL JSON is not rewritten.

### 8.7 `C2_KCHK` (job 59780907, 2026-10-14): FAIL 7/10, decision blocked

All on IBM-T0 `B0_ref117_k1`, model I-ECHO (the 2026-10-06 `ibm_kingston` record at echo $T_2$), 21 qubits, one A100, qiskit 1.4.3 / aer 0.15.1. Source: `validation/C2_KCHK.json -> data.arms.<arm>.structure`, `data.decision`, `data.cpu_process`, `data.comparisons`.

| arm | engine | shots done (target / minimum) | s/shot | $\bar w$ $\pm$ s.e. | deficit vs 10 | marginals $P(1)$ (20 clbits) | accepted / reference hits |
|---|---|---|---|---|---|---|---|
| `kraus_gpu_cusv` | Kraus, cuStateVec | 256 (256 / 256) | 1.920 | **2.996 $\pm$ 0.235** | 7.004 | 0.027-0.223 | 1 / 0 |
| `kraus_gpu_native` | Kraus, Aer native GPU kernels (`cuStateVec_enable=False`) | 256 (256 / 64) | 2.223 | **3.566 $\pm$ 0.247** | 6.434 | 0.035-0.254 | 1 / 0 |
| `kraus_gpu_cusv_nofusion` | Kraus, cuStateVec, `fusion_enable=False` | 128 (128 / 32) | 5.047 | **1.141 $\pm$ 0.219** | 8.859 | 0.023-0.102 | 0 / 0 |
| `rm_gpu_cusv` | RM, cuStateVec | 512 (512 / 512) | 0.417 | **7.434 $\pm$ 0.100** | 2.566 | 0.088-0.506 | 0 / 0 |
| `kraus_cpu` | Kraus, CPU statevector, separate process | **0** (minimum 16) | -- | -- | -- | -- | -- |
| `rm_cpu` | RM, CPU statevector, separate process | **0** (minimum 16) | -- | -- | -- | -- | -- |

*Why the CPU arms are empty.* `data.cpu_process`: `threads: 1`, `chunk: 16`, `min_shots: 16`, `build_s` 53.8, `status: running`, `returncode: -9`, `killed_after_grace: true` (grace 60 s). The CPU process started with **one thread** and its first 16-shot chunk never finished inside the job (2 312 s of wall time; GPU arms 2 020 s, CPU process 2 305 s by `data.run.phases_s`). At the laptop's rate of 174 s/shot on 12 threads (Section 8.5), 16 Kraus shots on one thread could not finish in the window [MINE reading]. `prompts/33e` R1 found the cause (Section 8.8).

*Criteria.* K1 FAIL as "not decided" (`z_w: null`, `bug_confirmed: null`); K2 FAIL (`production_representation: blocked`, both comparisons `null`); K3 PASS as recorded (`validated_kraus_gpu_path: none`); P0 PASS (raw counts of every chunk stored, sums equal shots); S1-S5 PASS; S6 FAIL (CPU arms 0 of 16). The only comparison the job could evaluate is GPU Kraus versus GPU RM: $\Delta\bar w=-4.44$, $z_w=-17.38$, 18 of 20 marginals outside $3\sigma$ (power: differences below 0.115 in a marginal or 0.766 bits in $\bar w$ are invisible at 256 / 512 shots).

*What the GPU arms show anyway* [MINE z-values, the project's formula $z=(\bar w_1-\bar w_2)/\sqrt{{\rm se}_1^2+{\rm se}_2^2}$, which reproduces the JSON's $-17.38$]:

| comparison | $z_w$ | reading |
|---|---|---|
| `rm_gpu_cusv` (C2_KCHK) vs RM of C2_CAL run 3 | +0.11 | the GPU RM path is reproducible across jobs |
| `kraus_gpu_cusv` (C2_KCHK) vs Kraus of C2_CAL run 3 | +2.20 | the GPU Kraus deficit reproduces (3.00 against 2.40) |
| `kraus_gpu_cusv_nofusion` vs `kraus_gpu_cusv` | $-5.78$ | **the same channel gives different answers with fusion on and off** |
| `kraus_gpu_native` vs `kraus_gpu_cusv` | +1.67 | |
| `kraus_gpu_native` vs `kraus_gpu_cusv_nofusion` | +7.36 | |
| each GPU Kraus arm vs the laptop CPU Kraus (7.474 $\pm$ 0.559, `c33c_diag/summary.json`) | $-7.39$ (cusv), $-6.40$ (native), $-10.56$ (no fusion) | all three far below the CPU reference (not a criterion: the CPU reference is a laptop diagnostic, not the CI arm) |
| `rm_gpu_cusv` vs the laptop CPU Kraus / CPU RM | $-0.07$ / $+0.89$ | GPU RM agrees with both CPU references in weight |
| `rm_gpu_cusv` vs the device (K1, flown T3) | $-23.4$ | the T0-versus-T3 gap, now 7.43 against 9.77 |

### 8.8 `prompts/33e` (2026-10-15): the re-ruling after `C2_KCHK` (open; on `master` no executor work yet, one unmerged commit on branch `c33e`)

- **R1, cause and fix.** `kchk_cpu.cpu_threads` correctly reads the CPU affinity; the step was bound to **one CPU** because `jobs/gate.sbatch` line 52 runs `srun python scripts/run_gate.py "$CI_GATE"` without `--cpus-per-task`, and Slurm (since 22.05) no longer lets a job step inherit the allocation's `--cpus-per-task` (the allocation had 32). The exported `OMP_NUM_THREADS=32` has therefore been over-subscribing one core in every CI job's CPU phase: speed, not correctness, "no number changes". Fix: `srun --cpus-per-task="${SLURM_CPUS_PER_TASK:-1}"`, and every token JSON records `run.cpu_affinity` (S3 FAILs on the CI unless it equals `SLURM_CPUS_PER_TASK`); for the CPU arm `--chunk 1` (no shot lost to the deadline) and `--min-shots 8`.
- **R2, run 2 is CPU-only.** The GPU arms of run 1 are evidence of record (archived byte-identically as `validation/archive/C2_KCHK_job59780907.json`, sha256 recorded in run 2) and are not repeated; run 2 runs the CPU process for about 2 700 s with RM : Kraus alternated 2 : 1, plus a 128-shot `rm_gpu_cusv` anchor. Expected yield [PLAN]: about 40 Kraus and 80 RM CPU shots, $\bar w$ to $\pm0.4$ and $\pm0.3$; enough for K1 (3.0 versus 7.4 is $z\approx10$) and K2's weight test; the marginal tests are weak at that count.
- **R3, the laptop CPU reference now.** In the twin environment (qiskit 1.4.3, aer 0.15.1) the laptop extends its CPU arms to $\ge64$ Kraus and $\ge64$ RM shots in 30-minute segments (about 3.2 h + 1.5 h [PLAN]), committed segment by segment; new criterion **K4** in run 2: the laptop and CI CPU references agree per representation ($\lvert z_w\rvert\le3$), else STOP.
- **R4, timing.** Class 2 goes after the maintenance (2026-10-21 to 10-28), with one exception: `C2_XY4` is requested as soon as run 2 reads `production_representation: rm`; if run 2 reads `blocked`, class 2 goes to `prompts/BLOCKED_C33.md` and the owner chooses between the native-GPU Kraus engine (2.2 s/shot, only if K3 validates it) and dropping class 2.
- **R5, the upstream case.** "The three GPU Kraus executions of the same channel disagree with each other" (no fusion versus cuStateVec $z=5.7$; native versus no fusion $z=7.3$); a correct simulator is invariant under fusion on/off and the kernel choice, so this is evidence of a defect in aer 0.15.1's GPU Kraus path "that needs no CPU reference at all" and is not cuStateVec-specific; the direction is excess relaxation. The upstream report (owner files it) gets two parts: GPU versus GPU now, GPU versus CPU after run 2.

### 8.9 What is established, what is not, and what would decide (updated 2026-10-15)

| statement | strength |
|---|---|
| The device's mean weight on the flown T3 circuit is 9.771 $\pm$ 0.007, 0.229 below the unital limit, of which 0.063 is readout | solid ([MEAS], $10^5$ strings, one job) |
| On circuit T0 under I-ECHO, **GPU RM gives 7.42-7.43** in two independent jobs ($z=0.11$) | solid ([SIM], 1 024 + 512 shots) |
| On T0, **CPU Kraus (7.47 $\pm$ 0.56) and CPU RM (6.92 $\pm$ 0.57) agree with GPU RM** in weight | moderate (19 and 24 shots on the laptop; the CI CPU arms are empty) |
| **Aer 0.15.1's GPU Kraus execution is inconsistent**: 3.00, 3.57 and 1.14 for the same channel on three GPU engines, all far below the CPU value | strong for "inconsistent" (5.8 $\sigma$ between fusion on and off, within one job); moderate for "wrong" (needs the CI CPU arms) |
| Nothing outside the class-2 Kraus arms used Kraus on the GPU | strong (the audit file) |
| The 30-54 $\sigma$ device comparisons of C2_CAL say nothing about channel correctness by themselves (T0 versus T3) | follows from the circuit difference; unchanged |
| The planner's relaxation estimate (2.64 bits) supported Kraus-GPU | **withdrawn** by the planner (33d R0) |
| RM misapplies relaxation | **refuted** at the delay-error and one-qubit level and by the CPU comparison (Section 8.5) |
| The correct IBM-noise prediction of K1 | cannot be stated; no class-2 cell has run; the representation is `blocked` |

*What would decide it, in order of cost:* (a) the laptop's 64 + 64 CPU shots (`prompts/33e` R3, about 5 h in the background); (b) `C2_KCHK` run 2 on the node's CPUs (one 60-minute job after the sbatch fix); (c) `C2_XY4` on the flown circuit T3 with RM in production, which tests whether RM reproduces the device's 9.77 on the circuit the device actually ran. On `master` none of (a)-(c) had started at 17:43 UTC; the branch `c33e` (unmerged, commit `daeb40c` at 17:46 UTC) adds the runner for (a). **This is open.**

## 9. prompts/35, 35a, 35b: the Quantinuum tests (now committed gates)

**Status on 2026-10-15: committed gates on `master`** (merged from branch `q35` on 2026-10-14, `e66eb26`). The owner asked on 2026-10-13: "I need all the circuits tested for quantinuum devices. has this been done?" The planner answered with `prompts/35` (2x3 done in four of six tiers; 2x2 and 2x4 not), then ruled on the executor's findings in `prompts/35a` and on a binding STOP at 2x4 in `prompts/35b`. Sources: the gate JSONs `validation/Q0P_2x2.json`, `QN_2x2.json`, `QEMU_2x2.json`, `QH_2x2.json`, `QH_2x3.json`, `QEMU_2x3_laptop_smoke.json`, `Q0P_2x4.json`, `QN_2x4.json`, `QEMU_2x4.json`, `QH_2x4.json`, `QSC_prepared.json`; `validation/dryrun/QV_2x4_01.json`; `ci/parts/QV_2x4_01.json`; the manifests under `data/quantinuum/circuits_2x2/` and `circuits_2x4/`; `prompts/35`, `35a`, `35b`; `prompts/LOG.md` rows 146, 148-149, 151, 153, 155, 157-162. **0 QPU s, 0 HQC, 0 eHQC throughout** (every gate records `qpu_seconds: 0`, `hqc: 0`). The [EXEC] numbers of the 2026-10-13 report are now [GATE]; where a committed value differs from the earlier [EXEC] one, it is said.

### 9.1 The six tiers (the project's labels, `prompts/35` section 0)

| tier | meaning |
|---|---|
| T1 native and exact | the signed circuits compiled to the Quantinuum native gate set $\{R_z,\ {\rm PhasedX},\ {\rm ZZPhase}\}$ with pytket, verified exact against the pre-conversion statevector ($\max\lvert\Delta\psi\rvert<10^{-10}$, leakage $<10^{-9}$), frozen with checksums |
| T2 noiseless sampling | the frozen circuits sampled without noise on Aer; per-state 5-sigma test |
| T3 Quantinuum noise models | scenarios E1-E7 on the frozen circuits (f-cells and full plan-of-record SKQD) |
| T4 vendor local emulator | pytket-pecos `H2-1LE` (noiseless, runs locally, no credentials) |
| T5 syntax checker | Quantinuum's online syntax checkers (free, but need a Nexus login; none exists) |
| T6 Helios HUGR | the circuits as a Guppy/HUGR program run on the Selene emulator (the Helios software route) |

### 9.2 State per lattice on 2026-10-15

| lattice | T1 | T2 | T3 | T4 | T5 | T6 |
|---|---|---|---|---|---|---|
| 2x2 (28 + 2 circuits) | **PASS** `Q0P_2x2` 5/5 | **PASS** `QN_2x2` (N1, N2) | **PASS** `QN_2x2` (N3-N5): 308 f-cells, 4 of 11 plan-of-record runs (7 dropped by `35a` R3) | **PASS** `QEMU_2x2` 3/3 (28 circuits) | prepared (`QSC_prepared`: H2-2SC 30 jobs, Helios-1SC 29) | **PASS** `QH_2x2` 4/4 (28 circuits) |
| 2x3 (44 + 2 circuits) | PASS `Q0P_2x3` 7/7 (2026-10-02) | PASS `C3_AER` 10/10 | campaign 33 class 4 (Section 7) | laptop smoke PASS (`QEMU_2x3_laptop_smoke`, 98 s/shot); the `C3_LE` token not run (needs `skqd-pecos` on Perlmutter) | prepared (H2-2SC, 46 jobs) | PASS as information (`QH_2x3`: 2 circuits x 10 shots) |
| 2x4 (60 + 2 circuits; 79 built in two sources) | **FAIL by construction** `Q0P_2x4` 4/6 (the bar is measured on the GPU slot `QV_2x4_01`, not yet requested) | not done on the laptop; GPU slot `QV_2x4_01` prepared (dry run at 2x2 PASS) | **PASS** `QN_2x4` 2/2 (analytic, 0 shots; $f\approx0$) | `QEMU_2x4` **infeasible** | prepared (opt-3 $k=1$ 17 jobs, structured $k=1$ 17 jobs) | `QH_2x4` **not attempted** |

### 9.3 2x2, tier T1: `Q0P_2x2` PASS 5/5 [GATE]

*Circuits.* 5 $B=0$ references (06, 17, 21, 30, 43) and 2 $B=1$ references (07, 14), each at $k=1..4$: 28 circuits, plus `CAL_zeros` and `CAL_x0`. Frozen in `data/quantinuum/circuits_2x2/`, compiled for H2-2 with the offline pytket handler, frozen level 0 (selection rule: fewest ZZ among the levels that pass Q1).

| quantity (all 28 circuits) | value | source key (`validation/Q0P_2x2.json`) |
|---|---|---|
| ZZPhase per circuit | **252** on all 28 (min = mean = max); `rzz` before compilation 252; level 0 and level 2 both 252 | `data.frozen.index_summary.n_zz`, criterion Q2 |
| PhasedX per circuit | 405 to 425, mean 414.57 | `data.frozen.index_summary.n_phasedx` |
| two-qubit depth | 201 | `data.Q5.devices.quantinuum_h2_2.memory_ESTIMATE.depth_2q` |
| exactness $\max\lvert\Delta\psi\rvert$ (global phase removed) | **$7.21\times10^{-14}$** (worst `B0_ref06_k2`; build $6.40\times10^{-15}$) | criterion Q1 |
| leakage | $2.43\times10^{-14}$ | criterion Q1 |
| JSON / QASM round trip | $6.99\times10^{-14}$ / $6.98\times10^{-14}$ (QASM drops the global phase); sha256 ok; $X$ on qubit 0 gives key 1 | criterion Q3 |
| pytket rounding bound $B$ at 2x2 | $2.7\times10^{-13}$ (information) | `prompts/LOG.md` row 157 |
| HQC per shot | **0.6109** mean (0.6090 to 0.6130), $N_m=24$; manifest and index differences 0 | criterion Q5 |
| gate-only clean fraction $f$ (family mean; worst circuit) | **H2-2 0.7929** (0.7927, `B0_ref17_k2`); **Helios-1 0.8046**; **H1-1 0.7560**; **H2-1 0.7429**; with the memory ESTIMATE (low / mid / high) on H2-2 0.7913 / 0.7894 / 0.7789 | criterion Q5; `data.Q5.devices.*` |
| $\epsilon_2$ that would still give mean $f=0.1$ / worst $0.05$ (H2-2) | 0.009006 / 0.01173 | `data.Q5.devices.quantinuum_h2_2.eps2_for_*` |
| rule D3' plan at $0.7f$ | **H2-2 13 990 HQC; Helios-1 13 563; H1-1 14 233; H2-1 14 660** | criterion Q5 |
| test suite (criterion Q7) | `coding` 625 passed / 47 skipped (21 min 58 s); venv 655 passed / 25 skipped; `check_package` rc 0; pins and freeze unchanged; `Q0P_2x3` reproduced in memory; campaign-33 token indices unchanged | criterion Q7 |

All values equal the [EXEC] values of the 2026-10-13 report. Cross-check [MINE]: $(1-8.3\times10^{-4})^{252}=0.811$ for the two-qubit factor alone, consistent with 0.7929 after the one-qubit and readout factors.

*Finding: the coarse step is $k$-independent* (`prompts/35a` R1). `circuit_set` builds one coarse step evaluated at the angle $k\,\Delta t$, so every circuit of a family has the same gate skeleton (252 ZZ at 2x2, 2 158 at 2x3, 69 676 / 71 548 at 2x4 depending on the source). The Q2 criterion was re-ruled to "equal to the family's $k=1$ value on every circuit"; consequence: the $k=4$ circuits are not four times as costly as $k=1$; they need more shots only because their reference probability is lower.

### 9.4 2x2, tiers T2 and T3: `QN_2x2` PASS 5/5 [SIM]

*T2, noiseless* (Aer CPU statevector, 4 threads, $\max(20\,000,$ plan shots$)$ per circuit, seeds $35\,000\,000+1000c$+chunk): **514 states tested, max $z=3.585$, 0 failures, 0 shots outside the exact support** (N1). Noiseless SKQD at the `H0_2x2` plan of record (133 907 shots; `data/hardware/H0_2x2_prep/shot_plan.json`): $B=0$ and $B=1$ recall of $S_{999}$ 1.0, $E_R-E_0=0$, the certificate interval collapsed onto $E_0$ (N2).

*T3, f-cells* (N3): **308 cells = 28 circuits x 11 scenarios x 2 000 shots** (Aer CPU, 4 threads, fusion off; seeds $35\,200\,000+1000s+c$). The scenarios are those of campaign 33 (Section 7.1) with E7 re-matched to the 2x2 native counts (`E7_0.10_lat`: $p_2=9.006\times10^{-3}$, the value that gives gate-only $f=0.10$ at $n_2=252$, $n_1=414.6$, $n_m=12$). Per scenario (the file stores per-cell values; the means are my averages over the 7 $k=1$ circuits and over all 28 circuits, `data.fcells.per_scenario.<s>.cells`):

| scenario | $p_2$ | mean $k=1$ $f_{\rm hit}$ [MINE mean] | $k=1$ range | mean $k=1$ $f_0$ | mean accepted fraction (28 circuits) | wall (s) |
|---|---|---|---|---|---|---|
| E1 (H2-2 published) | $8.3\times10^{-4}$ | 0.8378 | 0.826-0.846 | 0.8070 | 0.8578 | 1 293 |
| E2 (Helios-1) | $7.9\times10^{-4}$ | 0.8418 | 0.829-0.858 | 0.8172 | 0.8652 | 951 |
| E3 (H2-2E emulator set) | $1.29\times10^{-3}$ + angle dependence | 0.7666 | 0.749-0.781 | 0.7129 | 0.7941 | 1 237 |
| E4 (Helios-1E set) | $8\times10^{-4}$ + angle dependence | 0.8524 | 0.841-0.859 | 0.8180 | 0.8738 | 1 124 |
| E5a / E5b / E5c (memory 0.5 / 1.1 / 4.4 ms) | $8.3\times10^{-4}$ + $p_{\rm mem}$ $1.4/3.08/12.3\times10^{-6}$ | 0.8342 / 0.8374 / 0.8298 | 0.804-0.853 | 0.8042 / 0.8010 / 0.7833 | 0.854 / 0.850 / 0.849 | 1 276 / 1 100 / 1 384 |
| E6a / E6b / E6c (errors x0.5 / x2 / x4) | $4.15\times10^{-4}$ / $1.66\times10^{-3}$ / $3.32\times10^{-3}$ | 0.9196 / 0.6936 / 0.4998 | 0.492-0.941 | 0.8983 / 0.6511 / 0.4236 | 0.931 / 0.732 / 0.551 | 1 018 / 847 / 903 |
| E7(0.10), lattice-matched | $9.006\times10^{-3}$ | **0.1762** | 0.154-0.201 | 0.1159 | 0.2345 | 889 |

*What it says.* At the published rates the 2x2 family keeps 77-85 % of its $k=1$ shots on the reference statistic; even at four times the H2-2 error it keeps half. The E7 row shows what a device at the signed bar ($f=0.10$ gate-only) would give: $f_{\rm hit}\approx0.18$, the same factor of about 1.7 above the label as at 2x3 (Section 7.10 item 4). **E1 band test (information):** over all 28 circuits the E1 reference hits are **22 751 against 24 433 expected** from $f_{\rm hit}=f_0\,r_{nc}$ with the 2x3 value $r_{nc}=1.1151$ (95 % band [24 127, 24 740]; $k=1$ only: 10 397 against 11 167, band [10 960, 11 375]): verdict **"tension"** (`data.fcells.E1_band`). The file's own reading: "2x2 has no measured $r_{nc}$ of its own; $r_{nc}$ is the 2x3 $k=1$ value". My reading: the 2x3 correction overstates the 2x2 excess by about 7 % [MINE: 24 433/22 751 = 1.074], i.e. at 2x2 the reference-hit fraction exceeds $f_0$ by less than at 2x3 (consistent with the mean $k=1$ $f_{\rm hit}/f_0=1.038$ [MINE: 0.8378/0.8070]).

*T3, plan-of-record runs* (N4; the `H0_2x2` plan, 133 907 shots per scenario: $B=0$ 69 505 shots on 20 circuits, $B=1$ 64 402):

| scenario | $B=0$ accepted fraction | $B=1$ accepted fraction | $\lvert B_{\rm all}\rvert$ / $\lvert B_{\rm sig}\rvert$ | recall $S_{999}$ | $E_R-E_0$ | certificate | wall (s) |
|---|---|---|---|---|---|---|---|
| E1 | 0.8589 | 0.8537 | 38/38, 20/20 | 1.0 / 1.0 | 0 / 0 | KT ($B=0$) and Weinstein ($B=1$) collapsed onto $E_0$, $r_H=6.1\times10^{-15}$ / $1.5\times10^{-15}$ | 1 764 |
| E3 | 0.7856 | 0.7776 | same | 1.0 / 1.0 | 0 / 0 | same | 1 630 |
| E4 | 0.8671 | 0.8617 | same | 1.0 / 1.0 | 0 / 0 | same | 1 638 |
| E5b | 0.8575 | 0.8539 | same | 1.0 / 1.0 | 0 / 0 | same | 1 857 |

The saturation parameter is $Na/\dim=16.97$ ($B=0$) and 15.72 ($B=1$) in every run (`mu_per_state`), so **these runs are saturated by construction and carry no information about support quality** (the 2x2 role is pipeline calibration, Section 3.1). *Dropped by `35a` R3 and recorded with their predicted cost* (`data.plan_of_record.<s>.status`): E2, E6a, E6b, E6c, E7_0.10_lat (0.87 h each at the E1 rate) and E5a, E5c (1.03 h each at the E5b rate). Rates (N5): 0.02344 s/shot (E1) and 0.02780 s/shot (E5b) on 500 shots of `B0_ref06_k4`. **T3 wall: f-cells 12 021 s + plan of record 6 888 s = 5.25 h of the 10 h cap** (`data.t3_cap`); the gate's runtime field is 18 924 s. (The 2026-10-13 report's "15.4 h [MINE]" was a sizing of the unreduced plan and is superseded.)

### 9.5 2x2 and 2x3, tiers T4 and T6

*T4, `QEMU_2x2` PASS 3/3* (environment `~/.local/share/su2qc-pecos/venv`: pytket 2.18.4, pytket-quantinuum 0.59.3, pytket-pecos 0.3.3, quantum-pecos 0.8.0.dev8): **all 28 circuits at 785 shots** (rule $\min(1000,\lfloor4\times3600/(28\,s_{\rm shot})\rfloor)$ at the 5-shot probe rate 0.655 s/shot), seed $35\,100\,000+c$; **0 per-state failures, max $z=2.898$, 0 outside the support**; per-circuit rate 0.0266-0.0842 s/shot. No noisy-mode emulator probe was run (`data.noisy_probe` null). (On 2026-10-13 only 17 of 28 had run.)

*T6, `QH_2x2` PASS 4/4*: route frozen pytket JSON, `guppy.load_pytket` inside a `@guppy` `main`, `main.compile()` to a HUGR package, `selene_sim.build`, `run_shots(Quest, IdealErrorModel)`. **28/28 HUGR packages** written with sha256; **1 599 shots per circuit** (`35a` R5: $\min(2000,\lfloor3600/(28\,s_{\rm shot})\rfloor)$ at 0.0804 s/shot measured on 100 shots just before the run; floor 500), total wall 4 352 s under load; **0 per-state failures, max $z=3.67$**; per-circuit 0.0667-0.1271 s/shot; `CAL_x0` gives key 1 in 10 of 10 (bit order fixed). Findings recorded in the file: guppylang 0.21.16's `compile()` does not list the `tket.qsystem.helios` extension that `load_pytket` uses for PhasedX and ZZPhase, so the package is written with that extension embedded (a "stack block" fix allowed in the pecos venv only by `35a` R5); the HUGR-to-pytket round trip is "not available in tket 0.13.2" (`to_tket1()` returns a 0-qubit circuit).

*2x3, information only.* `QH_2x3` PASS 4/4: `B0_ref25_k1` and `B1_ref57_k1` as HUGR on Selene, **10 shots each at 158.0 and 145.6 s/shot** (one circuit per 30-minute command), 9 reference hits each, 0 failures, max $z=2.66$. `QEMU_2x3_laptop_smoke` PASS 2/2: the `C3_LE` engine path in dry mode, **98.3 s for one shot** at 20 qubits, 0 strings outside the sector. Neither is the `C3_LE` token, which needs the owner's `skqd-pecos` environment on Perlmutter.

### 9.6 2x4, tier T1: `Q0P_2x4` FAIL by construction 4/6 [GATE]; the two sources

*Why there are two sources.* Under `prompts/35` the executor built 2x4 native circuits from the qiskit level-3 ("opt-3") transpile of the structured IR (the route that made 2x3). The local-equivalence proof Q1L (part (iii), the pytket rounding bound) then **failed on all 19 built circuits**: pytket stores every angle within $10^{-11}$ half-turns of a multiple of 1/4 as that multiple, and the opt-3 transpile leaves about 67 000 near-Clifford angles per circuit, so the rigorous state bound $B=\tfrac{\pi}{2}\sum_g(\lvert\Delta a_g\rvert+2\lvert\Delta b_g\rvert)$ reaches $4.96$-$4.98\times10^{-9}$, above the $10^{-10}$ bar (binding STOP, `prompts/LOG.md` row 149). `prompts/35b` then established from the files that **the bar was never met by any compiled 2x4 circuit before conversion**: the opt-3 all-to-all circuit is $1.528\times10^{-9}$ (phase-aligned) from `krylov.coarse_states` on the GPU (`validation/S2_2x4.json -> data.gpu_validation`), the structured IR $1.07\times10^{-13}$; and it ordered a second, **structured** source (the exact IR through `ir_to_pytket`, no qiskit opt-3).

| quantity | opt-3 source (`<id>.opt3.*`) | structured source (`<id>.structured.*`) | source |
|---|---|---|---|
| circuits built | 19 ($k=1$: all 15 references; $k=2$: 4); paused by `35b` R6 | **60** (all 15 references x $k=1..4$) | `data.index.sources.*` |
| ZZPhase per circuit | **69 676** | **71 548** (= source `cx` + `cp`) | criterion Q2 |
| PhasedX per circuit | 90 272-90 646 | 210 994-210 995 | `data.index.sources.*.summary` |
| example `B0_ref102_k1`: $R_z$; depth; two-qubit depth | 139 267; 205 139; 68 648 | 143 140; 347 827; 70 300 | `data/quantinuum/circuits_2x4/B0_ref102_k1.*.manifest.json -> counts` |
| HQC per shot | **157.46-157.54** (mean 157.51) | **185.35** | criterion Q5 |
| pytket rounding bound $B$ (rigorous) | **$4.956$-$4.979\times10^{-9}$** (up to 67 236 rounded gates) | **$5.76$-$6.71\times10^{-12}$** (up to 7 549) | `data.Q1.B_per_circuit`, `data.Q1L.by_source` |
| Q1L conversion proof (i) skeleton angles, (ii) segments | PASS 19/19 | PASS 60/60 | criterion Q1L: (i) max $4.4\times10^{-15}$ half-turns; (ii) frame residual $8.04\times10^{-13}$ |
| Q1 (state against `krylov.coarse_states`, bar $10^{-10}$) | **not measured** (deferred to the GPU) | **not measured** | criterion Q1 FAIL with `status_reason` |
| gate-only $f$, H2-2 / Helios-1 / H1-1 / H2-1 | $5.78\times10^{-27}$ / $7.95\times10^{-26}$ / $7.91\times10^{-31}$ / $8.65\times10^{-35}$ | $4.18\times10^{-29}$ / $4.87\times10^{-28}$ / $1.47\times10^{-32}$ / $1.12\times10^{-36}$ | `validation/QN_2x4.json -> data.analytic.devices_by_source` |
| reference probability `B0_ref102_k1` | 0.9340 | 0.9340 | manifests |
| build time `B0_ref102_k1` | 558 s | 880 s | manifests |

*Why `Q0P_2x4` FAILs by construction.* `prompts/35b` R1-R3: the $10^{-10}$ bar stays; it is measured on the GPU with a full $2^{28}$ statevector; no bound and no probabilistic estimate may replace it; Q1L is "the conversion proof" only, and $B$ becomes a falsifiable consistency check of the GPU job (native-versus-own-source distance $\le B+10^{-12}$). Until the GPU measures it, criterion Q1 reads FAIL and the file carries `status_reason` "Q1 (state vs coarse_states) not measured on the laptop; deferred to QV_2x4_01 (GPU); Q1L conversion proof PASS 79/79". The second failing criterion, **Q7**, is not about 2x4: the full pytest run had 1 failure in each environment (`coding` 644 passed / 50 skipped, venv 673 / 21), the test `test_campaign33_driver[C2_KCHK]` that reads `master`'s `validation/dryrun/C2_KCHK.json` (dry wall 1 152 s against the test's 600 s limit; Section 13.8); it also flips the in-memory re-run of `Q0P_2x3`'s Q6/Q7, while its Q1-Q5 are identical.

*Cross-check on 2x3* (`35b` R5, `data.structured_source_check_2x3`): the structured source of `B0_ref25_k1` has 2 590 ZZ against the frozen opt-3 family's 2 158; its state is $3.06\times10^{-14}$ from `coarse_states` and $1.93\times10^{-13}$ from the frozen opt-3 native circuit; $B=3.9\times10^{-13}$; the frozen 2x3 family is unchanged. So the structured route costs 20 % more ZZ at 2x3 [MINE: 2590/2158 = 1.200] and 2.7 % more at 2x4 [MINE: 71548/69676 = 1.027], but has a rounding bound three orders of magnitude below the bar.

*The decision job `QV_2x4_01`* (`ci/parts/QV_2x4_01.json`, written at `0265bf8`): 9 statevector runs on one A100: for `B0_ref102_k1` and `B1_ref230_k1`, the native and source circuits of both sources (8 runs; e.g. the opt-3 native QPY has 480 509 instructions, the structured native 847 670), plus a reproduction of the S2_2x4 CZ-basis circuit's recorded $1.528\times10^{-9}$ (V2); predicted **888 s** (at $2.32\times10^{-4}$ s per instruction from `S2_2x4`), budget 2 700 s. Criteria: V1 every run completes; V2 the S2_2x4 reproduction to $10^{-12}$; V3 native-versus-own-source $\le B+10^{-12}$ for both sources, else STOP; V4 the frozen source is the one whose native circuits meet $10^{-10}$ and leakage $<10^{-9}$ on both circuits (both: the smaller; neither: STOP and the planner rules). Its laptop dry run at 2x2 PASSED 4/4 (V4 chose `ir-opt3` at $1.36\times10^{-14}$; `validation/dryrun/QV_2x4_01.json`). **Pending**: not requested (the planner and LOG place it after the campaign-33 must-run set or after the maintenance; the allowlist file `ci/allowed_jobs.q35` must be installed on Perlmutter by the owner). The slots `QV_2x4_02..08` are for the $k\ge2$ checks of the chosen source.

### 9.7 2x4, tiers T3-T6

- **T3, `QN_2x4` PASS 2/2, analytic, 0 shots** (`35` R3): the analytic fault-free fraction $f_0$ of all 79 built circuits under the 11 scenarios. E1: $\log_{10}f_0=-24.39$ (opt-3) and $-26.12$ (structured); E3 $-38.8$ / $-42.6$; E6c $-97.7$ / $-104.6$; the only scenario with $f_0$ near 1 is `E7_0.10_lat` ($\log_{10}f_0=-0.73$ / $-0.46$; it re-solves $p_2$ so that the gate-only $f$ at the 2x4 counts is 0.10, which is why `max_f0_any_scenario` reads 0.351). E6a (half the H2-2 errors) gives $\log_{10}f_0=-12.2$ / $-13.1$. **Every scenario other than the constructed E7 gives $f\approx0$ at 2x4.**
- **T4, `QEMU_2x4` infeasible**: 51.9 s/shot at 20 qubits for 2 158 ZZ; 2x4 has 32.3x the ZZ on $2^8=256$x the amplitudes, and H2-1LE models a 20-qubit machine that cannot hold 28 qubits (`data.numbers`).
- **T5, prepared**: `QSC_prepared` (H2-2SC syntax checks of 17 opt-3 and 17 structured $k=1$ circuits; if they were device runs they would cost 472 605 and 556 160 HQC respectively for the job set, `data.sets[*].hqc_estimate_if_it_were_a_device_run`; the syntax checkers are free).
- **T6, `QH_2x4` not attempted**: a 28-qubit Quest statevector is 4.3 GB per state on the laptop CPU.

### 9.8 The rulings of `prompts/35a` and `prompts/35b` in one place

| ruling | content |
|---|---|
| 35a R1 | Q2 corrected: the coarse step is $k$-independent; Q2 = "equal to the family's $k=1$ value"; the 2x4 GPU cost is per circuit (about 1.6 GPU-hours for $k\ge2$ [PLAN], not 4.9) |
| 35a R2 | pytket canonicalises angles within $10^{-11}$ half-turns of a multiple of 1/4; rigorous bound $B$ ($2\lvert\sin(\delta/4)\rvert\le\delta/2$ per rotation, triangle inequality over the product); Q1L restated: skeleton angles to $10^{-11}$, segment products to $10^{-12}$ with the read-back angles, and $B<10^{-10}$; $\max\lvert\Delta\psi\rvert\le B+10^{-12}$ where a statevector exists |
| 35a R3 | 2x2 T3: f-cells on all 28 x 11 kept; plan-of-record runs E1, E3, E4, E5b only; cap 10 h |
| 35a R4 | 2x4 built at level 0 only (level 2 capped at 1 800 s, recorded) |
| 35a R5 | Selene sized on the rate measured just before the run (floor 500 shots); the E7 test skipped in the pecos venv with a reason; the helios-extension packaging fix allowed in the pecos venv only |
| 35b R1 | the $10^{-10}$ bar stays and is **measured on the GPU** (candidate (a)); no bound or probabilistic estimate is a criterion |
| 35b R2 | Q1L = the conversion proof (i)+(ii); $B$ stays as a falsifiable consistency criterion of the GPU job |
| 35b R3 | `Q0P_2x4` status FAIL with the reason until the measurement; `prompts/35` R2's "PASS on Q1L" reversed |
| 35b R4 | second 2x4 source: the structured IR through `ir_to_pytket` (+ `cx`, `p`, `cp`, one-qubit unitaries) and pytket level 0, no qiskit opt-3 |
| 35b R5 | cross-check of the new rules on 2x3 `B0_ref25_k1` (dense; expected $10^{-13}$ class; the 2x3 frozen family unchanged) |
| 35b R6 | opt-3 $k\ge2$ builds paused; structured $k=1$ built (in the event all 60 structured circuits were built in 30-minute chunks); the frozen source is chosen by `QV_2x4_01`; if neither source passes, STOP for the planner with the four measured numbers |

### 9.9 What is pending, and the strength of this section

*Pending (all 0 HQC):* `QV_2x4_01` (decides the frozen 2x4 source) and `QV_2x4_02..08`; T5 for every lattice (needs a Nexus login); `C3_LE` on Perlmutter (needs `skqd-pecos`); the noisy-mode H2-1LE probe; nothing for 2x4 beyond analytics, because no device can run it.

*Strength.* Strong for the 2x2 build and its noiseless tiers (committed gates, exact to $10^{-13}$, three independent engines agree at the 5-sigma level: Aer, the vendor's local emulator, Selene); strong that 2x4 is out of reach ($f_0\le10^{-23}$ at every published device rate, E1-E5; even at half the H2-2 error, E6a, $f_0\approx10^{-12}$; only the constructed `E7_0.10_lat` is near 1); the 2x4 exactness itself is unproven until the GPU job runs. None of it is a device measurement.

## 10. Pipeline status matrix (lattice by step)

How to read: each cell says what exists, how strong the evidence is (labels of Section 0) and where it is. "DONE" means a committed gate with PASS; "PARTIAL" means a committed gate with a restricted scope (or a FAIL by construction pending a measurement); "NOT DONE" means no file; "n/a" means not applicable by design. The hardware rows distinguish *circuits ready to submit* (Section 11) from *data taken*. (Updated 2026-10-15: the 2x2 and 2x4 Quantinuum rows are now committed gates; the 2x3 noisy-simulation rows gained ten full SKQD runs; the IBM-type row records `C2_KCHK`.)

| step | 2x2 (12 qubits, 82 states; 28 circuits) | 2x3 (20 qubits, 1 727 states; 44 circuits) | 2x4 (28 qubits, 37 165 states; 60 circuits planned) |
|---|---|---|---|
| **exact references** ($E_0$, gaps, supports, $\Delta t$) | DONE [GATE] E1-E3: $E_0^{B=0}=-3.6407665507$, $E_0^{B=1}=-1.8615880345$ | DONE [GATE]: $-5.6026004579$ / $-3.8260844431$ | DONE [GATE] (Lanczos): $-7.5652140739$ / $-5.7801629009$ |
| **exact circuits** (structured IR, verified) | DONE [GATE] S2 / L2: 256 CZ all-to-all, 618 routed; exact to $1.9\times10^{-14}$ | DONE [GATE] S2: 2 164 CZ all-to-all (2 158 RZZ), 5 477 routed (5 659 with the exactness-gated seed rule); $1.9\times10^{-14}$ | DONE [GATE] S2_2x4: one circuit, 69 688 CZ, 148 726 routed; GPU leakage $1.10\times10^{-12}$; note: the opt-3 circuit is $1.528\times10^{-9}$ from the exact state, the structured IR $1.07\times10^{-13}$ (`prompts/35b`) |
| **native Quantinuum circuits** | **DONE [GATE]** `Q0P_2x2` PASS 5/5: 28 + 2 circuits, exact $7.2\times10^{-14}$, 252 ZZPhase, 0.6109 HQC/shot | DONE [GATE] `Q0P_2x3` PASS 7/7: 44 circuits, exact $2.1\times10^{-13}$, 2 158 ZZPhase | **PARTIAL [GATE]** `Q0P_2x4` FAIL by construction 4/6: 79 circuits built in two sources (opt-3 19, structured 60), conversion proven (Q1L 79/79), the $10^{-10}$ state bar pending the GPU job `QV_2x4_01` |
| **IBM-routed circuits** | DONE [GATE] H0 family on the `ibm_kingston` patch (frozen QPY; 12 qubits, about 44 $\mu$s) | DONE [GATE] K0 / K1: 2 circuits, 5 659 CZ, 411 $\mu$s, 21 qubits; campaign 33 also froze IBM-U / T0 / T3 | model only [GATE] K0: 148 726 CZ routed; not built as a family |
| **noiseless simulation** | **DONE [GATE]** L2; `QN_2x2` (514 states, max $z$ 3.59), `QEMU_2x2` (vendor emulator, 28 circuits), `QH_2x2` (Selene, 28 circuits) | DONE [GATE] C1_IDEAL, C3_AER: exact to $10^{-12}$, 5-sigma test, recall 1.0; `QH_2x3` (2 circuits, information) | NOT DONE (28-qubit statevector: GPU slot `QV_2x4_01` prepared, not requested) |
| **noisy simulation, Quantinuum-type** | **DONE [SIM, GATE]** `QN_2x2`: 308 f-cells over 11 scenarios (E1 mean $k=1$ $f_{\rm hit}$ 0.838; E7(0.10) 0.176) | **PARTIAL, substantial [SIM]**: f-cells 45 of 77 planned cells (16 more requested in slot 13); **10 full SKQD runs** (F1, F4, F5, F7, F8 in both sectors; 25 files) | **DONE, analytic [GATE]** `QN_2x4`: $f_0\le10^{-23}$ at every published rate |
| **noisy simulation, IBM-type** | DONE [GATE] L4_fez, S2D_levers (post-diction 1.05x at $T_2^*$) | **BLOCKED [SIM]**: C2_CAL (contradicted by the device on a different circuit); C2_KCHK FAIL 7/10, representation `blocked`; the GPU Kraus path is internally inconsistent; no class-2 cell has run | NOT DONE |
| **full SKQD, simulated, with noise** | DONE [SIM, GATE]: `QN_2x2` plan of record under E1, E3, E4, E5b (saturated: $Na/\dim\approx17$, $E_R=E_0$ by construction); earlier L4 / H0P rehearsals | **PARTIAL, substantial [SIM]**: 10 runs (Section 7.8); $E_0$ certified in 25/25 files; F2 requested; F3, F6 deferred; the assembly (merged parts, CV on merged runs, P15) not run | PROXY only: S1 emulation recall 0.934 at the device proxy |
| **full SKQD on hardware, IBM** | DONE once [MEAS] H0_2x2 (53.0 s; noise-saturated, not a physics result); mitigation did not replicate (H0_ddrep) | **NO-GO** [MEAS] K1: 0 hits in $2\times10^5$ shots | infeasible by model [GATE] K0 / S2_2x4 |
| **full SKQD on hardware, Quantinuum** | circuits ready [GATE]; no access; D3' plan 13 990 HQC (H2-2) | circuits ready [GATE]; no access; Stage E 9 949.92 eHQC, Stage P 9 949.92 HQC, plan of record 665 605 HQC at $f=0.10$ | infeasible: $f\approx0$ |
| **full SKQD on hardware, IonQ** | NOT DONE; feasible on paper (Forte gate-only $f=0.303$, 5-20 kUSD at Braket rates, [PLAN]); no submission code | infeasible on paper (Forte gate-only $f=8.6\times10^{-5}$) | infeasible (208 399 native gates > 150 000 job limit) |
| **ML step** | not applied to any hardware data | ridge baseline on exact amplitudes: Spearman 0.862 ($B=0$), 0.888 ($B=1$) [GATE] S1; graph network, recovery, seven-protocol comparison NOT DONE | ridge transfer from 2x3: Spearman 0.763 [GATE] S1 |

**Count of the cells by status** (my reading of the table, 12 rows x 3 lattices = 36 cells): DONE 17, PARTIAL or BLOCKED 6 (2x4 native; 2x3 Quantinuum-noisy, IBM-noisy, noisy full SKQD; the two ridge-ranker cells), NOT DONE, not applied or infeasible 13 [MINE; the 2026-10-13 report counted 13 / 9 / 14 under a slightly different reading of the same rows, so only the direction of the change is meaningful]. The changes: 2x2 native, noiseless, Quantinuum-noisy and noisy-full-SKQD cells became DONE (committed gates); 2x4 Quantinuum-noisy became DONE (analytic); 2x4 native moved from executor-reported PARTIAL to a committed PARTIAL; 2x3 IBM-type moved from PARTIAL to BLOCKED. Calling a model-only or proxy-only cell "not done" and an infeasible hardware cell "not done" are judgements.

## 11. Device readiness matrix and submission scripts

Sources: `data/quantinuum/devices_20261002.json`, `validation/Q0P_2x3.json`, `validation/K0_2x3_2x4.json`, `validation/K1_2x3_fpilot.json`, `data/ionq_2x3_feasibility_20261001.json`, `reports/qpu_survey_2x3_20261002.md`, the scripts named, and (for 2x2 and 2x4 on Quantinuum, updated 2026-10-15) the committed gates `Q0P_2x2`, `QN_2x2`, `QEMU_2x2`, `QH_2x2`, `Q0P_2x4`, `QN_2x4`, `QSC_prepared`. "Ready" means: circuits frozen with checksums, verified exact, cost computed, submission path present and dry-run tested. **Nothing is ready to submit without an owner action** (access, budget or a go) except IBM, whose account is nearly spent.

### 11.1 Circuits by device

| circuit set | IBM Heron (`ibm_kingston`, `ibm_fez`, `ibm_marrakesh`) | Quantinuum (H2-2, Helios-1, H1-1, H2-1; emulators H2-2E, H1-1E; local H2-1LE) | IonQ (Forte, Forte Enterprise; Tempo is a projection) |
|---|---|---|---|
| **2x2, 28 coarse circuits + 2 readout** | READY, flown: frozen QPY in `data/hardware/H0_2x2_*`, 12-qubit patch `[59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]`, XY4 cell T3; measured $f_{\rm hit}$ 0.1129 / 0.1271 (2026-10-02), 0.0732 (2026-10-06) | **READY [GATE]**: `data/quantinuum/circuits_2x2/` (28 + 2, sha256), 252 ZZPhase, 0.6109 HQC/shot, exact $7.2\times10^{-14}$; HUGR packages for Helios in `circuits_2x2_helios/` (28/28); verified on Aer, H2-1LE and Selene; syntax-check job sets prepared; gate-only $f$ 0.79-0.80 on H2-2 / Helios-1; not submitted; no account | no circuits exported; feasibility only (Forte gate-only $f=0.303$, [PLAN]) |
| **2x3, 44 coarse circuits + 2 readout** | built for 2 circuits (`B0_ref117_k1`, `B1_ref29_k1`), flown once: **NO-GO** (measured); the other 42 are unneeded | **READY** [GATE]: `data/quantinuum/circuits_2x3/` (44 + 2, sha256 in `index.json`), 2 158 ZZPhase, 4.9666 HQC/shot, exact $2.1\times10^{-13}$, the pilot plan (Stage E / P: 9 949.92) and the campaign plan (665 605 HQC at 0.10) computed; A6 dry run done; no Nexus account | circuits not exported; infeasible on paper (gate-only $f=8.6\times10^{-5}$ on Forte with virtual $R_z$) |
| **2x4, 60 coarse circuits** | not built; infeasible | built, not frozen [GATE]: 79 circuits in two sources (opt-3 19: 69 676 ZZPhase, 157.5 HQC/shot; structured 60: 71 548 ZZPhase, 185.4 HQC/shot); the frozen source awaits `QV_2x4_01`; infeasible ($f_0\approx10^{-24}$ to $10^{-26}$ at the H2-2 rate) | infeasible |
| **calibration circuits** (all zeros, $X$ on qubit 0) | yes (readout pubs) | yes (`CAL_zeros`, `CAL_x0`) [GATE for 2x2 and 2x3; `CAL_x0` gives key 1 on Selene] | no |

### 11.2 Predicted clean fraction by device and lattice (the "clean-fraction landscape")

All **models or vendor figures**, never measurements, except where a "measured" label stands. Gate-only $f$ is $\prod(1-\epsilon)^{n}$ over two-qubit, one-qubit and readout operations with the vendor's published error rates; the memory (transport) term is an [EST] scenario. The bar is mean $\ge0.1$ and worst $\ge0.05$ on $\hat f_{\rm ideal}$. Source rows: `data/quantinuum/devices_20261002.json -> rows`, `validation/Q0P_2x3.json`, `validation/Q0P_2x2.json` (2x2 native), `validation/QN_2x4.json` (2x4), `data/ionq_2x3_feasibility_20261001.json`, `validation/K1_2x3_fpilot.json`, `validation/H0_*.json`. Block (x) in Section 18 is the same table in CSV.

| device | 2x2 | 2x3 | 2x4 |
|---|---|---|---|
| Quantinuum H2-2 (56 qubits, $\epsilon_2=8.3\times10^{-4}$) | 0.7929 [GATE native]; 0.7875 (pre-native); simulated mean $k=1$ $f_{\rm hit}$ 0.838 (E1) and 0.767 (E3) [SIM `QN_2x2`] | **0.1502** gate-only; with memory 0.1454 / 0.1398 / 0.1130 [EST]; Aer-convention simulated $\hat f_{\rm ideal}$ 0.207 (E1 f-cell), 0.228 / 0.218 (F1 full runs, $B=0$ / $B=1$ [MINE pooled]) and 0.102 (E3, emulator parameters) | gate-only $5.8\times10^{-27}$ (opt-3) / $4.2\times10^{-29}$ (structured) [GATE `QN_2x4`] |
| Quantinuum Helios-1 (98 qubits, $7.9\times10^{-4}$) | 0.8046 [GATE]; 0.7991; simulated mean $k=1$ $f_{\rm hit}$ 0.842 (E2) | **0.1642**; memory 0.1378 / 0.1117 / 0.0352 [EST]; simulated 0.240 (E2 f-cell; the F2 full runs are requested) | $7.9\times10^{-26}$ / $4.9\times10^{-28}$ [GATE] |
| Quantinuum H1-1 (20 qubits, $9.7\times10^{-4}$) | 0.7560 [GATE]; 0.7514 | 0.1113; memory 0.1049 / 0.0977 / 0.0661 | does not fit (20 qubits) |
| Quantinuum H2-1 (56 qubits, $1.1\times10^{-3}$) | 0.7429 [GATE]; 0.7378 | 0.0860; memory 0.0815 / 0.0764 / 0.0535 | $8.6\times10^{-35}$ / $1.1\times10^{-36}$ [GATE] |
| IBM Heron, `ibm_kingston` | **measured** $f_{\rm hit}$ (2x2 circuits): 2026-10-02 pilot 0.0413 (no DD), `H0_ddtest` 0.0400 (no DD) and 0.1129 (XY4), full run 0.1271 (XY4); 2026-10-06 `H0_ddrep` 0.0818 (no DD) and 0.0732 (XY4) | **measured upper bound $2.06\times10^{-5}$** on $\hat f_{\rm ideal}$ (95 %); model ceiling $9.8\times10^{-3}$ (two-qubit factor only, committed record) | model $\sim10^{-53}$ |
| IBM Heron, `ibm_fez` | measured $6.65\times10^{-4}$ (reference-string fraction, 2026-09-22; the yield-inverted value was 0.0255) | model: dead | dead |
| IonQ Forte (36 qubits, $\epsilon_2=4\times10^{-3}$) | 0.303 gate-only [PLAN] | $8.6\times10^{-5}$ (virtual $R_z$); $3.7\times10^{-5}$ (physical $R_z$) | does not fit the job limit |
| IonQ Tempo (projection, 99.9 % target) | -- | about 0.077, still below 0.1 [PLAN] | -- |
| other platforms surveyed (Google, Rigetti, IQM, neutral atoms, ...) | see block (f) | fail by 2 to 13 orders of magnitude [PLAN, `reports/qpu_survey_2x3_20261002.md`] | -- |

### 11.3 Submission scripts and their status

| device | script | purpose | tested how | needs |
|---|---|---|---|---|
| IBM | `scripts/h0_submit.py` (`--submit`, `--retrieve`, `--dry-run` on FakeBackend, preflight with rule D9 fingerprint) | submit/retrieve any frozen QPY group via SamplerV2; DD and twirling off by default | 14 real jobs (Section 12) | IBM account `open-instance`, 273 s left |
| IBM | `scripts/gate_H0_2x2.py`, `gate_K1_2x3_fpilot.py`, `gate_H0_ddrep.py` (stages plan / predict / prereg-md / assemble / submit) | preregistered gates for specific sessions | dry runs `*_dryrun` PASS | a go and a "ready" `h0_devicewatch.py` |
| IBM | `scripts/h0_devicewatch.py` | free poll: `active` and every CZ error published | used 2026-10-06 | -- |
| Quantinuum | `scripts/quantinuum_submit.py` (`--dry-run` on Aer with H2-2 noise; `--syntax-check`, `--emulate`, `--preflight`, `--submit`, `--retrieve`, `--status`; every job body carries `max_cost`; `--submit` refuses without `--prereg`, a preflight record and `--cap-hqc`) | submit the frozen 2x3 circuits | `--dry-run` only (A6 dry run, 280 shots) | a Nexus account, `quantinuum_account.py --login`, a preregistration, an allocation |
| Quantinuum | `scripts/quantinuum_account.py` (`--login`, `--check`, `--logout`; tokens never on a command line) | account handling | never run with a real account | an account |
| Quantinuum | `scripts/quantinuum_build_circuits.py`, `quantinuum_device_table.py`, `quantinuum_stack_check.py`, `gate_Q0P_2x3.py` | build, cost and verify the native circuits | gates Q0P_2x3, Q0P_2x3_plan PASS | -- |
| Quantinuum | `quantinuum_build_circuits.py --lattice {2,3,4} --source {opt3,structured}`, `quantinuum_lattice_tests.py` (merged 2026-10-14) | the 2x2 and 2x4 builds and tiers T2-T6 | gates of Section 9 | -- |
| Quantinuum | `quantinuum_submit.py --syntax-check` on the `QSC_prepared` job records | free syntax checks (tier T5) of 2x2, 2x3, 2x4 | records only | a Nexus login |
| Perlmutter (verification) | GPU slots `QV_2x4_01..08`, part file `ci/parts/QV_2x4_01.json` | the 2x4 $10^{-10}$ state check and the choice of the frozen source | laptop dry run at 2x2 PASS | the owner's `ci/allowed_jobs.q35` on Perlmutter; a request |
| Quantinuum | local emulator `src/skqd/campaign33/engines.py` (`Pecos`, `Selene`), token `C3_LE` | noiseless vendor-emulator check | laptop probes 51.9 s/shot at 20 qubits | `skqd-pecos` environment on Perlmutter |
| IonQ | none (only `scripts/ionq_2x3_feasibility.py`, published-specification arithmetic) | -- | -- | circuit export, account, decision (Section 15) |
| Perlmutter (simulation) | `scripts/ci_request.sh`, `ci_check.sh`, `campaign33.py`, `campaign33_resize.py` | request and read GPU jobs | 37 returned campaign jobs (Section 12.3); `ci_request.sh` conflicted with the merge history on 2026-10-14 (Section 13.8) | the owner's allowlist; queue time |

### 11.4 What each missing piece costs (all in the files)

- **Quantinuum access** (the only route to 2x3 hardware data): the draft is `proposal/quantinuum_access_request_draft_20261005.md`. Stage E 9 949.92 eHQC (4 jobs, 2 000 shots: two $k=1$ circuits at 800 shots, two $k=4$ at 200), Stage P 9 949.92 HQC (USD 124 374 at 12.5 USD/HQC [EST]), campaign 665 605 HQC at $f=0.10$ (about 78.8 machine-hours at the mid memory scenario [EST]).
- **2x2 on Quantinuum** (cross-platform check, [GATE] `Q0P_2x2` Q5): D3' plan at $0.7f$ costs 13 990 HQC on H2-2, 13 563 on Helios-1, 14 233 on H1-1, 14 660 on H2-1 (a campaign, not a pilot). The syntax checks of all sets are free but need a Nexus login.
- **IBM** remaining: 273 s; a replication-type 2x2 job costs about 37 s, the 2x3 pilot cost 188.0 s, the full 2x2 run 53.0 s.

## 12. Resources: QPU seconds, Perlmutter, HQC, calendar

Sources (QPU part unchanged since 2026-10-06; Perlmutter, HQC and calendar parts updated 2026-10-15): `data/hardware/*/session.json -> jobs[*].{job_id,usage_s,submitted,n_pubs,group_shots}` and `total_usage_s`; `data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json -> usage`; `reports/SESSION_HANDOVER_20260921_24.md`, `reports/SESSION_HANDOVER_20260925_1002.md`; `validation/H0_*.json`, `validation/H0_ddrep.json`, `validation/K1_2x3_fpilot.json`, `data/hardware/H0_ddrep_ibm_kingston/account_check_after_20261006T0703Z.json`, `data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json`. QPU seconds are the billed `usage` the IBM service reports per job. All real quantum jobs so far ran on **IBM Quantum (open plan, instance `open-instance`, 600 s of QPU time per rolling 28-day period)** on the 156-qubit Heron r2 devices `ibm_fez` and `ibm_kingston`. No job has been run on any other quantum computer.

### 12.1 Every QPU job

| # | date, UTC (submitted) | device | job id | what (pubs x shots) | purpose | billed QPU s | result |
|---|---|---|---|---|---|---|---|
| 1 | 2026-09-22 17:48:32 | ibm_fez | `dapbusac505c73chv0og` | canary: 3 pubs x 267 | first real run: one frozen 663-CZ $r=1$ circuit + 2 readout pubs; options: runtime XY4 DD on, twirling on | 2.0 | 8 accepted of 267 vs required $\ge10$; yield-inverted $f=0.0255$ vs predicted 0.2195: **NO-GO** (`validation/H0_canary.json`) |
| 2 | 2026-09-22 20:42:56 | ibm_fez | `dapegkcak42c73cierv0` (J1) | 5 pubs x 2 000 | diagnostic: both options off | 5.0 | 35 accepted of 2 000 (pre-registered 30.8 $\pm$ 5.5 idle relaxation / 374.5 $\pm$ 17.4 options hypothesis) |
| 3 | 2026-09-22 20:43:55 | ibm_fez | `dapeh3318flc739m51e0` (J2) | 3 pubs x 2 000 | diagnostic: XY4 on | 4.0 | 27 accepted |
| 4 | 2026-09-22 20:44:13 | ibm_fez | `dapeh7ac505c73ci2o60` (J3) | 1 pub x 2 000 | diagnostic: twirling on | 3.0 | 25 accepted |
| 5 | 2026-09-22 20:44:27 | ibm_fez | `dapehb4ak42c73cietig` (J4) | 1 pub x 2 000 | diagnostic: XY4 + twirling (the canary's own options) | 3.0 | 17 accepted; consistent with no clean component |
| 6 | 2026-10-02 18:12:35 | ibm_kingston | `davv8504oijs73e88fvg` | kpilot: 8 pubs x 4 000 | pilot on the selected patch: two $k=1$ circuits + one $k=4$ + Ramsey (44.03 and 22.02 $\mu$s) + $T_1$ + readout; options off | 12.0 | pooled $f=0.0413$ [0.0361, 0.0470]: **NO-GO** (`validation/H0_kpilot.json`) |
| 7 | 2026-10-02 20:11:42 | ibm_kingston | `db01005j371s73dnmbd0` | ddtest: 10 pubs x 6 000 | A/B test of client-side DD (4 cells x 2 circuits + 2 readout) | 20.0 | T0 0.0400; T2 0.1118; **T3 0.1129 [0.1058, 0.1203] adopted**; T1 0.0005 (`validation/H0_ddtest.json`) |
| 8 | 2026-10-02 21:05:55 | ibm_kingston | `db01pddj371s73dnnqm0` | H0_2x2: 14 pubs x 267 | full 2x2 run, $B=0$ $k=1..3$-type circuits at the 267 floor | 3.0 | see Section 6.15 |
| 9 | 2026-10-02 21:05:57 | ibm_kingston | `db01pdtj371s73dnnqmg` | 7 pubs x 267 | full 2x2 run: `B0_ref43_k3` and the $B=1$ circuits with $k=1,2,3$ (references 07, 14) at the floor | 3.0 | " |
| 10 | 2026-10-02 21:05:59 | ibm_kingston | `db01pe04oijs73e8cl30` | 2 pubs x 4 000 | readout calibration (all-0 / all-1) | 4.0 | min diagonal 0.9417 |
| 11 | 2026-10-02 21:06:00 | ibm_kingston | `db01pelj371s73dnnqo0` | 5 pubs x 13 100 | the five $B=0$ $k=4$ circuits (rule D3' $N_4$) | 22.0 | " |
| 12 | 2026-10-02 21:06:02 | ibm_kingston | `db01peql7guc73cfndc0` | 2 pubs x 31 400 | the two $B=1$ $k=4$ circuits (rule D3' $N_4$) | 21.0 | " |

| 13 | 2026-10-06 07:00:40 | ibm_kingston | `db29p6nr11fs7396e4ig` | H0_ddrep: 20 pubs x 6 000 | replication of the XY4 gain and the T1 collapse + four mechanism cells + four pulse-train pubs + 2 readout pubs on the 2x2 patch; options off | 37.0 | $R_{T3}=0.895$ [0.804, 0.996] (vs 2.819); T0 0.0818 (vs 0.0400); R1, R2, C1 all False; reading "no single hypothesis" (`validation/H0_ddrep.json`) |
| 14 | 2026-10-06 08:22:03 | ibm_kingston | `db2avbe8v0ts73c2i8b0` | K1: 4 pubs x 100 000 | the 2x3 pilot: two signed $k=1$ circuits (5 659 CZ, XY4 T3) + 2 readout pubs; options off | 188.0 | 0 reference hits in $2\times10^5$ shots vs 0.191 from garbage; $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %): **NO-GO, firm** (`validation/K1_2x3_fpilot.json`) |

(Circuit composition of rows 8-12 is from `data/hardware/H0_2x2_ibm_kingston/session.json -> jobs[*].circuit_ids`: 28 coarse circuits = 14 + 7 at the 267-shot floor plus 5 + 2 $k=4$ circuits at $N_4$, and 2 readout pubs at 4 000 shots.)

### 12.2 Totals and budget

| quantity | value | source |
|---|---|---|
| ibm_fez, 2026-09-22 (canary + diagnostic) | 2.0 + 15.0 = **17.0 s** | `session.json -> total_usage_s` (canary 2.0; J1-J4 5.0+4.0+3.0+3.0) |
| ibm_kingston, 2026-10-02 (pilot + DD test + full run) | 12.0 + 20.0 + 53.0 = **85.0 s** | `session.json` files (pilot 12.0; ddtest 20.0; H0_2x2 3+3+4+22+21 = 53.0) |
| ibm_kingston, 2026-10-06 (DD replication + 2x3 pilot) | 37.0 + 188.0 = **225.0 s** | `data/hardware/H0_ddrep_ibm_kingston/session.json`, `data/hardware/K1_2x3_ibm_kingston/session.json -> total_usage_s` |
| ibm_kingston, all days | 85.0 + 225.0 = **310.0 s** (sum of sourced numbers) | the three lines above |
| **total QPU time used** | 17.0 + 85.0 + 225.0 = **327.0 s** (sum of sourced numbers) | the account counter after the last retrieval: `usage_consumed_seconds` **327** (`data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json`) |
| plan allowance | 600 s per period (`usage_limit_seconds` 600); the period is a rolling window whose `start_time` / `end_time` move with the check (at the last check 2026-09-08T08:26Z to 2026-10-06T08:26Z) | same file |
| **remaining** | **273 s** (`usage_remaining_seconds` 273) | same file |
| number of real jobs | 14 (1 canary + 4 diagnostic + 1 pilot + 1 ddtest + 5 full-run + 1 ddrep + 1 K1) | `session.json` files |
| estimate-to-billed ratio | full 2x2 run 41.7 s estimated vs 53.0 s billed (1.27; planner arithmetic from the report); `H0_ddrep` 34.04 s vs 37.0 s (1.087, my division); K1 182.63 s vs 188.0 s (1.029, my division) | `reports/H0_2x2_full_hardware_report_20261002.md` section 5; `validation/H0_ddrep.json -> data.live`; `validation/K1_2x3_fpilot.json -> data.live` |
| throughput | `H0_ddrep` 120 000 shots in 37.0 s = 3 243 shots/s; K1 400 000 shots in 188.0 s = 2 128 shots/s (both my division; K1's circuits are 411 $\mu$s long, 2x2's 44 $\mu$s) | the two sessions |
| the 400 IBM minutes | requested allocation **not yet visible** to the account (only `open-instance` is) as of `reports/SESSION_HANDOVER_20260925_1002.md` section 1; nothing newer in the repository | that file |
| authorised next spend | **none**: the K1 authorisation (cap 300 s) was used (188.0 s); the owner's decision of 2026-10-06 covered A and B only; the 273 s are unallocated | `data/owner_decision_20261005_k1_2x3_fpilot.md`, `data/owner_decision_20261006_A_then_B.md` |

Note on the budget history: the owner's "600 second budget" and the plan numbers quoted at various times (583 s left after the fez work, 571 s after the kingston pilot, 551 s after the DD test, 498 s after the full run, 461 s after `H0_ddrep`, 273 s after K1) are the account counter at those moments (`data/hardware/*/account_check*.json`: consumed 17, 29, 49, 102, 139, 327 s). My inference, not verified in a file: because the period is a rolling 28-day window, the 17.0 s spent on `ibm_fez` on 2026-09-22 would leave the window on about 2026-10-20 and the 273 s would then become about 290 s.

### 12.3 Everything else that cost compute (no QPU time)

| resource | job / run | cost | source |
|---|---|---|---|
| Perlmutter A100 (CI), before campaign 33 | smoke 58717267 (pass); L4 58737320 (crashed, OOM) 607 s; L4 58741899 (PASS) 684 s; S3 calibration 58771538 (PASS) 254 s; S2_2x4 59162991 (PASS) 97 s | 1 642 s for the four timed jobs [MINE] | `reports/ci-*.out`, `validation/ci_gate_*.json` |
| Perlmutter A100 (CI), campaign 33 up to the 2026-10-13 report | 12 timed jobs (three missing-package deaths, C2_CAL runs 1-3, C1_IDEAL, C3_AER, C4_FCELLS_A/B, C4_CF, C4_F5_B0) | **11 958 s = 3.32 GPU-hours** [MINE] | the 2026-10-13 report, Section 12.3; `reports/ci-<jobid>.out` |
| Perlmutter A100 (CI), campaign 33 since then | 24 class-4 jobs (the gate seconds of `reports/ci-<jobid>.out`: 669-1 811 s each, sum 27 624 s) and `C2_KCHK` (2 352 s) | **29 976 s = 8.33 GPU-hours** [MINE]; `C2_KCHK` alone records `gpu_node_hours` 0.642 and `node_hours_charged_shared_qos` 0.161 (`validation/C2_KCHK.json -> data.run`) | block (a2) |
| Perlmutter A100 (CI), all timed jobs to date | 41 jobs (4 before campaign 33, 37 campaign jobs) | **43 576 s = 12.10 GPU-hours**; charged at $G/4$ of a node per hour on the shared QOS: **3.03 node-hours** [MINE] | the three lines above |
| Perlmutter queue | request commit to last harvest per wave on 2026-10-13/14: 1.1 h (`20b3887`), 3.7 h (`23d18e2`), 3.6 h (`ebc60de`), 5.4 h (`d7dd0c4`), 4.5 h (`f940a18`), 1.0 h (`6c3e684`), 3.0 h (`f4c71e8`) [MINE from the commit times in UTC, block (a2)]; 24.7 h on 2026-10-08/09 (`prompts/33b` R7) | -- | `git log` of the CI robot's `submitted` / `results` commits |
| Perlmutter, pending | 8 requests (`C4_F2_B0`, `C4_F2_B1`, `C4_PART_12..17`) committed 2026-10-15 17:37 UTC; 60-minute walltime each | not yet known | `ci/requests/039..046`, `scripts/ci_check.sh` |
| Perlmutter, planned (not requested) | `C2_KCHK` run 2 (60 min, `prompts/33e`); `C2_XY4` (conditional); after the maintenance `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH`, F3 (15 jobs), F6 (10 jobs), the `C4_CF` 2-part re-request, the remaining f-cell slots, the `C4_PART_02` / `04` remainders; `QV_2x4_01` (predicted 888 s) and `QV_2x4_02..08` (about 1.6 GPU-hours for $k\ge2$ [PLAN, `prompts/35a` R1]) | -- | `prompts/33b`-`33e`, `prompts/35a`, `35b` |
| Quantinuum (HQC / eHQC) | none: no Nexus account, no allocation | **0 HQC, 0 eHQC** | every Quantinuum gate's `hqc: 0` |
| IonQ (Braket / Azure) | none | **0 USD** | `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` |
| laptop, new since 2026-10-13 | `QN_2x2` 18 924 s (T3 5.25 h of the 10 h cap); `Q0P_2x4` 6 228 s (plus 2x4 builds of 558-880 s per circuit, in 30-minute chunks); `Q0P_2x2` Q7 pytest 21 min 58 s and 19 min 40 s; `QH_2x2` 4 352 s; `QN_2x4` analytic 6 798 s; the class-2 CPU diagnostics (19 Kraus shots at 173.9 s and 24 RM shots at 84.0 s, about 5 320 s = 1.5 h of sampling [MINE]); dry runs `C2_KCHK` 1 152 s and `C2_XY4` 532 s / 1 464 s | each run inside the 30-minute rule by chunking (the long ones were split into commands of at most 30 minutes) | the gate JSONs' `runtime_s`, `data.wall_s`, `prompts/LOG.md` rows 152-162 |

### 12.4 What the hardware ledger says (unchanged since 2026-10-06; no QPU job since then)

- 14 jobs used 327 s: 17 s on `ibm_fez` (two failures to reach the planned run: a NO-GO and a diagnosis) and 310 s on `ibm_kingston` (one NO-GO, one adopted mitigation that did not replicate, one full 2x2 run, one replication and one 2x3 pilot that ended in a firm NO-GO).
- 53 of the 327 s (16 %, my division) bought the only full SKQD run on hardware, at 2x2; 188 of 327 s (57 %, my division) bought a measurement of a null (no 2x3 reference hit).
- The cost structure: the per-job billing floor is about 2-2.5 s regardless of shots (`SESSION_HANDOVER_20260921_24.md` section 4), so a session of many small jobs is job-count dominated; long circuits are shot-rate dominated (2 128 shots/s for the 411 $\mu$s 2x3 circuits against 3 243 shots/s for the 44 $\mu$s 2x2 circuits).
- Next planned spend: **none on IBM**. What to do with the 273 s is an open owner question (Section 15); Quantinuum emulator / pilot (about 9 950 eHQC / 9 950 HQC) pending access.

### 12.5 The calendar (dates that bound what can be done)

| date | event | source |
|---|---|---|
| 2026-10-15 | today; 8 Perlmutter requests pending; `prompts/33e` committed (C2_KCHK run 2, laptop CPU reference) | `scripts/ci_check.sh`, `git log` |
| about 2026-10-20 | the 17.0 s of QPU time used on `ibm_fez` on 2026-09-22 would leave IBM's rolling 28-day usage window, raising the remaining allowance from 273 s to about 290 s **(inference of mine, unverified; no account check since 2026-10-06)** | `data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json` |
| **2026-10-21 06:00 UTC to 2026-10-28 06:00 UTC** | Perlmutter maintenance (reservation `maintenance_20261021`): no jobs | `prompts/33b` R7; `prompts/33e` R4 |
| after 2026-10-28 | class-2 cells (`C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH`; `C2_XY4` earlier if run 2 allows), deferred class-4 jobs (F3 15, F6 10), f-cell slots, cv3 F2_B1, the `C4_CF` re-request, the `QV_2x4` slots | `prompts/33b`-`33e`, `35b` |
| not dated | the 400 IBM minutes (requested allocation, not visible to the account as of `reports/SESSION_HANDOVER_20260925_1002.md`); Quantinuum access; Nexus login | -- |

### 12.6 HQC and money (all vendor-page or planner figures, none spent)

| item | quantity | source |
|---|---|---|
| cost formula | $\mathrm{HQC}=5+C\,(N_{1q}+10N_{2q}+5N_m)/5000$ per job, $C$ shots, $N_m$ = qubits + measurements | `data/quantinuum/devices_20261002.json -> billing` |
| per shot, 2x2 / 2x3 / 2x4 | **0.6109** / 4.9666 / **157.51 (opt-3) or 185.35 (structured)** HQC | `validation/Q0P_2x2.json` Q5, `Q0P_2x3.json`, `Q0P_2x4.json` Q5 |
| Stage E (emulator H2-2E) | 9 949.92 eHQC, 4 jobs, 2 000 shots | `validation/Q0P_2x3_plan.json -> data.stage_E_v3` |
| Stage P (hardware pilot) | 9 949.92 HQC; USD 124 374 at 12.5 USD/HQC [EST] | same, `stage_P_v3` |
| 2x3 campaign, plan of record | 1 279 660 / 665 605 / 471 801 HQC at $f=0.05/0.10/0.15$; 257 475 / 133 909 / 94 909 shots; 64 / 53 / 49 jobs | `validation/CV_2x3_plan.json -> data.campaign_hqc` |
| 2x3 campaign, base D3'-R (without $B=1$ doubling) | 797 157 / 418 166 / 302 382 HQC | `validation/Q0P_2x3_plan.json` |
| 2x2 campaign (D3' at $0.7f$) | H2-2 13 990, Helios-1 13 563, H1-1 14 233, H2-1 14 660 HQC | `validation/Q0P_2x2.json` Q5 [GATE] |
| syntax checks (T5) | free; the job sets would cost 3 580.76 (2x2, H2-2SC), 43 952.04 (2x3), 472 604.6 (2x4 opt-3 $k=1$), 556 160.4 (2x4 structured $k=1$), 3 570.96 (2x2 Helios-1SC) HQC **if** they were device runs | `validation/QSC_prepared.json -> data.sets[*]` |
| rate | Azure Standard plan 125 000 USD per month for 10 000 HQC = 12.5 USD/HQC [EST]; pay-as-you-go and research rates not public | `data/quantinuum/devices_20261002.json -> access` |
| HQC spent so far | **0** | no account |

The plan-of-record cost depends on the scenario tier (Section 7.4): an E3-like (H2-2E parameter set) device would put the plan at tier 0.05, 1 279 660 HQC; an E1-like (published rates) one at tier 0.15, 471 801 HQC [MINE reading of the two documents].

### 12.7 The laptop and the desktop

The laptop (i7-8750H, 6 cores / 12 threads, 62 GiB RAM, GTX 1060 Max-Q without a usable GPU) is bound by the 30-minute rule. The RTX 3070 desktop is mentioned in plans but no file records a desktop run. Recorded costs on the laptop: class-2 CPU Kraus **173.9 s/shot** and RM **84.0 s/shot** at 21 qubits on 12 threads with the CI's software versions (`data/campaign33/c33c_diag/summary.json`; earlier 69 s and 24 s per shot for Kraus and PTA on the newer stack, `prompts/LOG.md` 2026-10-06); pecos H2-1LE 51.9 s/shot (engine probe) and 98.3 s for one shot in the smoke test at 20 qubits; Selene 145.6-158.0 s/shot at 20 qubits and 0.067-0.127 s/shot at 12; Aer 2x2 E1 / E5b 0.0234 / 0.0278 s/shot (4 threads); versus 0.018-0.028 s/shot on one A100 at 20 qubits for the class-4 runs (Section 7.3).

## 13. What was learnt

Every item is tied to the file that carries it. "Planner" statements are the project planner agent's conclusions, labelled as such.

### 13.1 Physics

1. **The exact references and the certification machinery work as specified.** All of the manual's Tables 1-2 and the derived quantities reproduce (gates E1-E3, Section 5); two independent Hamiltonian builders agree to $2.3\times10^{-14}$. On the hardware data, every Weinstein and Kato-Temple interval contained the exact $E_0$; at $B=1$ the residual $r_H=5.95\times10^{-3}$ is below the exact gap $0.0418$, so the lowest member of the near-degenerate cluster is certified, which the manual had listed as a stretch goal (`validation/H0_2x2.json -> data.energies.B=1.B_sig`).
2. **Ground states here are sparse.** The 99.9 % supports are 16 and 13 states at 2x2 (of 38 and 20), 86 and 95 at 2x3 (of 677 and 426) and 305 and 470 at 2x4 (of 12 843 and 8 934); participation ratios 1.5-4.8 at $g^2=4$ (`data/references.json`). At smaller coupling the support grows (2x3, $g^2=1$: 396 / 549, PR 33.8), the regime where sample-based methods get harder.
3. **At 2x2 the SKQD energy from the whole accepted support is not a device measurement.** The random decoder acceptance is $a=\dim/4096$, so once $N\gtrsim5\times4096$ shots (rule C22) the sector fills from accidentally valid noise alone. The run used 69 505 and 64 402 shots, i.e. $Na/\dim=16.97$ and $15.72$ (`validation/H0_2x2.json -> data.C22`). Uniformly random bit strings through the same decoder reproduced $E_0$ exactly in 100 of 100 seeds (`data.baselines.*.garbage_only`). The manual had anticipated it qualitatively (Step 0: "any $10^3$-shot run saturates its sectors"); the project quantified it and built the controls. The same warning is in the 2026 literature on sample-based diagonalization (arXiv:2608.11569, arXiv:2605.23697).
4. **The device-dependent reading is the signal support $B_{\rm sig}$**: 35 of 38 and 19 of 20 states above the $3\sigma$ noise line, with $E_R-E_0=5.48\times10^{-4}$ and $5.75\times10^{-6}$, at the 5.0th and 28.5th percentile of 200 random equal-size bases (the 28.5 % is coarse: only 18 distinct random bases exist for a 19-of-20 subset with both references fixed, and the omitted state carries exact weight $9.3\times10^{-7}$). A modest signal in $B=0$, no evidence in $B=1$ (`reports/H0_2x2_full_hardware_report_20261002.md` section 4).
5. **The manual itself expects no device advantage at 2x3 and 2x4**: CIPSI tracks the oracle at equal $|B|$ (S1 rows: $1.2\times10^{-3}$ vs $1.2\times10^{-3}$ at $|B|=160$), and device-seeded CIPSI does not help (manual Step 6.2). The planned primary endpoint P1 is a characterized null.
6. **Truncation matters at small coupling.** At 2x2, raising $j_{\max}$ from $\tfrac12$ to 1 shifts $E_0$ by $-0.0019$ ($g^2=4$), $-0.0385$ ($g^2=2$), $-0.341$ ($g^2=1$) (`data/references.json -> truncation_2x2`).
7. **Table 4 of the manual rests on a proxy, which later hardware showed to be badly optimistic.** The proxy treats a non-clean shot as uniform garbage or a few random bit flips; real idle-time error produces *near-clean* strings (below).

### 13.2 The device

8. **Idle-time dephasing, not gate count, is the loss that matters on Heron for this circuit family.** The gate-only model predicted $f=0.2195$ on `ibm_fez`; the clean fraction measured on the same circuit was $6.65\times10^{-4}$. The 663-CZ canary circuit runs 43.71 $\mu$s at depth 1 328 (nearly serial: 0.233 qubit-time utilisation per amendment item 3), each qubit idling 19-42 $\mu$s (`reports/SESSION_HANDOVER_20260921_24.md`). Ratio of in-circuit free-induction $T_2^*$ to the calibration record's echo $T_2$: 0.174 on `ibm_fez` (median over nine measured qubits, `validation/S2D_idle.json -> data.t2_bracket.fallback_ratio`) and about 0.17 equivalent on `ibm_kingston` (from the pilot's own $f$; the Ramsey estimate $r_{\rm eff}=0.0974$ is biased low by a coherent-phase signature). Only the *scheduled* simulation at the *measured* $T_2^*$ read with the *clean-yield* statistic post-dicts the device (ratio 1.0503; the echo end is 49.58x off; `validation/H0_model.json`).
9. **Runtime XY4 plus Pauli twirling did not help on fez; client-side XY4 restricted to windows of at least 1 $\mu$s helped by about 2.8x on kingston; staggered context-aware DD collapsed.** Same-job ratios (95 %): T2 2.793 [2.472, 3.157], T3 2.819 [2.495, 3.185], T1 0.012 [0.004, 0.031] against pulse-cost nulls 0.841 / 0.944 / 0.816 (`validation/H0_ddtest.json -> data.decision.cells`). Twirling cannot raise a clean fraction (it preserves average error, arXiv:1512.01098). The context-aware collapse is unexplained; the planner notes that arXiv:2506.18010 predicts little difference between staggered and plain DD on tunable-coupler devices, which makes the collapse more surprising. One job, one patch, one calibration content: **not a replicated result**, and the replication of 2026-10-06 (gate `H0_ddrep`, lesson 29) **failed**: $R_{T3}=0.895$ [0.804, 0.996], the baseline doubled, the context-aware cell was no longer collapsed ($R_{T1}=0.647$). Read this item as the record of what one calibration showed, not as a finding about XY4 on this device.
10. **Patch selection and scheduling are first-order levers but not rescues**: the idle-aware patch rule was worth 1.41x on the record that flew and 3.31x device-wide on fez; ALAP with explicit delays cut the scheduled duration to 0.710x (`validation/S2D_levers.json -> data.verdict.duration_ratio_best`); the exact family is kept because the fixed-angle generator is 3.7 % *longer* in time though 2.2 % shallower in depth. Neither alone reaches the bar; with client XY4 on the kingston patch the $k=1$ circuits reached $f\approx0.11$-$0.13$ on the reference-hit statistic **on 2026-10-02 only**: on 2026-10-06 the same circuits gave 0.0732 [0.0675, 0.0792] with XY4 and 0.0818 [0.0758, 0.0881] without (lesson 28), below the bar either way.
11. **Superconducting devices cannot run 2x3 or 2x4 of this family.** 2x3 routes to 5 477 CZ; even at the record's best edge error $8.164\times10^{-4}$ on every gate the ceiling is $f\le1.14\times10^{-2}$ (K0 verdict); 2x4 needs $T_2/t_{2q}=638\,742$ against Heron's 1 038. Dynamical decoupling removes only idle error, so it cannot change that. **Since 2026-10-06 this is a measurement and not only a model verdict** (lesson 31): the K1 pilot saw no reference hit in $2\times10^5$ shots, upper 95 % bound $2.06\times10^{-5}$ on $\hat f_{\rm ideal}$. (The 5 477-CZ figure in this item is the planner's survey value; the exactness-gated route that K0 and K1 actually use is 5 659 CZ, Section 6.20.)
12. **IonQ Forte-class machines cannot run 2x3 either** (gate-only $f=8.6\times10^{-5}$; the circuit is 2 158 serial two-qubit gates at 950 $\mu$s each); only Quantinuum's QCCD machines meet the signed gate-error bar on published numbers (H2-2 0.150, Helios-1 0.164, H1-1 0.111), with the transport (memory) error unknown and decisive. Error correction is a 2029-class option; detection codes are a net loss (planner, `reports/2x3_qec_amplification_strategy_20261002.md`).
13. **The calibration-content fingerprint behaves.** It stayed constant through three stamp-only updates on 2026-09-22 and fired on the one real recalibration; on kingston it was `84d59cbf9b5973d1` throughout 2026-10-02. Readout on the kingston patch: min diagonal 0.9417 against the live expectation 0.9525; survival product 0.8338 against the manual's design 0.82 (`validation/H0_2x2.json -> data.readout`).

### 13.3 Statistics and the meaning of "clean"

14. **Accepted shots are not clean shots.** The decoder accepts near-clean strings at a rate comparable to pure noise; on fez 13 of 35 accepted strings were distance-2 codewords of ideal probability 0. The yield inversion of the manual's Step 4.4 overstated the clean fraction by a factor 15 (0.0101 vs $6.65\times10^{-4}$; `validation/H0_model.json -> data.C2_pooled_device_clean_count`). Simulated Aer shows the same effect (34-42 % of accepted shots on the FakeFez snapshot), so it needed no hardware to find and was derivable from the exhaustive decoder enumeration of gate E2 (owner-approved rule M4.4).
15. **The right measurement is the reference-string statistic** ($f_{\rm hit}$), cross-checked by the mixture estimator; the C6 ruling scoped their agreement to circuits whose reference probability is at least 0.5 (at low $p_{\rm ref}$ the two estimators use nearly disjoint information, combined relative sigma 0.172).
16. **$f_{\rm hit}$ estimates the ideal-sample fraction, not the fault-free fraction.** The Pauli-trajectory decomposition (CF_traj, PASS 7/7) shows the shots that return to the reference are single phase-type events that do not change the measured string, most of them sampling the ideal distribution exactly; $r_{nc}=f_{\rm hit}/f_{\rm ideal}=1.115$ (upper 95 % end; `data/cf_trajectories/r_nc.json`). The first candidate statistic ($f_T$, tail-class fraction) was withdrawn because noise *scatters* shots into low-probability states and inflates it 21-39x. Consequence for 2x2: under the conservative correction the "signed bar GO" reads **AMBIGUOUS** (0.103 with lower 95 % bound 0.096, planner arithmetic at $r_{nc}=1.10$; owner decision 3a). Under idle dephasing at 2x2 the reference-hit fraction *under*-estimates $f_{\rm ideal}$ in the A5 model ($r=0.674$ and $0.902$ at the two $T_2$ ends), so the correction is not one-directional.
17. **The floor theorem** (CF_traj): the effective clean rate of every $S_{99}$ state is at least $f_{\rm ideal}(1-2\delta/p_c)$; measured minima 1.089 / 1.040 / 1.100 / 1.041 of $f_{\rm ideal}$ on the four arms, so sizing on $f_{\rm ideal}$ is safe by construction.
18. **At $k=4$ the mixture estimator overstates $f_{\rm ideal}$ by 27 %** (bias 1.274 [1.170, 1.402]).
19. **Rule D3' is not a finite plan at 2x3** ($N_4\sim8.8\times10^{35}$ at $f=0.1$ because 32 of 677 and 11 of 426 states have total $k=4$ probability below $10^{-6}$), and was measuring the wrong set: none of those states is in the 99.9 % support. The replacement D3'-R (31 / 42 states of $S_{99}$ at $\lambda^*$, then recall of $S_{999}\ge0.9$ with probability $\ge0.95$) cost 418 166 HQC at $f=0.10$ as a base plan (reproduced by gate `Q0P_2x3_plan` P1); after the convergence check doubled sector $B=1$ the plan of record costs **665 605 HQC** at $f=0.10$ (`validation/CV_2x3_plan.json -> data.campaign_hqc`).
20. **Cost scales as $1/f$** (up to about $2\times10^6$ shots per sector, and $\propto1/f^2$ beyond; planner, `prompts/27` and `reports/2x3_qec_amplification_strategy_20261002.md`): the shot quota of the manual cannot be signed until the 2x3 $f$ is measured (amendment item 5).
21. **The depth ladder at 2x2 is uninformative as run**: 94 % of the shots sit at $k=4$ (65 500 of 69 505 in $B=0$, planner arithmetic), so the $k$-resolved growth of $B_{\rm sig}$ mostly tracks shot count; the clean fraction of $k=2..4$ circuits is not measurable with the present estimators at their low $p_{\rm ref}$.

### 13.4 The reference manual

22. Two internal contradictions were found in the manual: (a) Step 9.2 asks for $2\times10^5$ shots per sector for 32 circuits while its own eq. (5) demands 1 228 448 (and at its design point $f=0.2$ already 1.69e6 per sector); (b) Step 4.4's yield model has no near-clean term (rule M4.4; "a stronger claim than the other eight ... it amends the reference manual"). The manual's premise (Step 9.2) that circuits of $\le500$ CZ keep $f\gtrsim0.2$ "never held for these circuits on any quoted device" (handover).
23. The **0.82 readout factor** double-counts the readout survival on Quantinuum (its $f_0$ already contains it); it is kept for consistency with 2x2; removing it would lower every shot count by 18 % and is the owner's call (`reports/2x3_shot_rule_estimator_ruling_20261003.md` section 5).

### 13.5 Compute and process

24. **GPU speed-ups** (Perlmutter A100): 19.8x at 12 qubits (0.00103 vs 0.02037 s/shot, L4), 161x at 20 qubits (0.01987 vs 3.198 s/shot, S3), about 300x for one 28-qubit leakage check (2x4); but L4 mean GPU utilisation was 15.3 %, so more GPUs would not help; the allocation model underestimates real memory 3.5x.
25. **Measurement gates plus preregistration kept the record honest.** Every hardware step has a committed prediction and decision rule before the data, a fingerprint-guarded submission, a dry run, and a PASS that means "measured" rather than "good"; two NO-GO verdicts (canary, pilot) and one FAIL (diag) are in the record with their numbers. The one exception is positive: the full run proceeded under an explicit, scoped owner waiver of the signed bar, not under a quietly relaxed criterion.
26. **Dry runs cannot predict DD gains** (Aer's relaxation on a delay is Markovian): dry-run ratios 0.71-0.79 vs nulls 0.82-0.94 were path checks only, as `prompts/24` P10 said in advance.
27. **Mistakes recorded in the handover** (`reports/SESSION_HANDOVER_20260921_24.md` section 7): the assistant reported the corrected model as predicting the device "to 1.13x" (that anchored on the accepted-shot count, the wrong statistic); a batching change crashed the first GPU job (about 92 GB requested on an 80 GB card); the assistant repeated the amendment's own erratum (2 164 CZ quoted for 2x2: it is the 2x3 figure; 2x2 is 256 all-to-all / 618 routed); a first count of clean shots accepted bit strings in both orders and double-counted (9 instead of 6); an executor was told to preserve a file that the prompt says to overwrite.

### 13.6 Lessons added on 2026-10-06

28. **Day-to-day calibration variation is larger than the dynamical-decoupling effects.** On the 2026-10-02 calibration the frozen no-DD circuits gave a pooled clean fraction 0.0400 [0.0358, 0.0446]; on the 2026-10-06 calibration the *same QPY files* on the *same patch* gave 0.0818 [0.0758, 0.0881], a factor 2.04 (my division; `validation/H0_ddtest.json`, `validation/H0_ddrep.json -> data.cells.T0`). Between the two days 1 110 values of the calibration record changed (the six families $T_1$, $T_2$, CZ error, measure error, $\sqrt{x}$ error, $x$ error), by factors from 0.102 to 111.3, and the patch's calibration fingerprint changed (`84d59cbf9b5973d1` $\to$ `cb40a250fb24387d`). The largest same-day DD effects of 2026-10-06 are ratios 0.647 (T1) to 1.150 (M4); the 2026-10-02 XY4 gain (2.819) is about the size of the day-to-day change of the baseline itself. A one-day A/B test cannot separate a mitigation from the calibration it ran on; a baseline (T0) must be in every job, as it was.
29. **The XY4 non-replication.** Gate `H0_ddrep` (preregistered, same QPYs for T0/T1/T3): R1 False (T3 no longer qualifies: $R_{T3}=0.895$ [0.804, 0.996], its 95 % interval excludes 1 from *above*), R2 False, C1 False (T1 not collapsed). Consequences: the 2x2 "signed bar GO" of 2026-10-02 was a one-day result (and on 2026-10-06 T3 reads NO-GO on both $f_{\rm hit}$ and $\hat f_{\rm ideal}=0.0656$ [0.0599, 0.0717]); the XY4 technical note is not supported as written (Section 14.4); the "XY4 transfer" columns of the K0 and K1 predictions rest on an $R$ that did not hold. Honest limits: one job, one patch, one calibration content per day; the planner's preregistered expectation ("T3 replicates; T1 collapses again") was wrong on both counts, which is the reason the test was run.
30. **The calibration record cannot see the $x$ pulse.** The record aliases `x_error` to `sx_error` (both minima $9.8\times10^{-5}$ in `validation/K0_2x3_2x4.json`), and the pulse-train pubs of `H0_ddrep` show a coherent over-rotation $\epsilon_q=0.0148$-$0.0204$ rad on all 12 patch qubits (XX-128 minus XpXm-128 above 0.05 on 12 of 12), about 1.5-3 times smaller than the RB-level estimate $\sqrt{6\,x_{\rm error}}$ (0.029-0.045 rad). Any decoupling sequence that applies the same $x$ pulse many times accumulates this coherent error: XX-128 reached $P_1=0.76$-0.98. Whether it explains the collapse is open (M1 INTERMEDIATE; the reading is "no single hypothesis"); the incoherent per-pulse cost exceeds three times the record's `x_error` only on qubits 71 and 91 (the $H_D$ pattern wanted 91 and 95, so it is False), while M4, the cell that removes the pulses on 91 and 95, is the one INTACT cell.
31. **2x3 on IBM Heron is a measured NO-GO.** K0's model verdict (idle-aware $f\sim10^{-16}$ on a 5 659-CZ, 411 $\mu$s circuit) was tested by K1: 0 reference hits in $2\times10^5$ shots, accepted strings at the garbage level, $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %), firm NO-GO against a GO-A threshold of $3\times10^{-4}$. The measurement removes the last IBM-side uncertainty about 2x3; the remaining device route in the repository's survey is Quantinuum. For scale, K0 puts the two-qubit error needed for $f=0.05$ on this routed circuit at $\epsilon_2=5.3\times10^{-4}$ with nothing else wrong, against the best calibrated edge $8.2\times10^{-4}$ (and that is only the two-qubit ceiling).
32. **The plan check changed the cost, not the plan's shape.** The emulation showed that the certificate widths, not the shot counts, set the cost: Weinstein width $\le0.1$ is out of reach for any affordable support (oracle $S_{999}$ has $r_H=0.265$ at $B=0$), Kato-Temple with the exact $E_1$ is met at $s=1$, and sector $B=1$ needs twice the shots for $r_H\le0.15$. The campaign minimum rose from 418 166 to 665 605 HQC at $f=0.10$ (+59 %, my division). Two planner criteria had to be corrected after a failed first run (width read on the wrong basis and wrong certificate; CV3 on the wrong step); the corrections were rulings with the owner's confirmation, not tolerance changes.
33. **A readiness check must test what the experiment needs.** On the night of 2026-10-05/06 `ibm_kingston` reported `operational` while in maintenance and publishing no two-qubit calibration; the project's device watch therefore requires status `active` and every CZ error present. The first K1 attempt stopped at 0 QPU s for that reason, and the order of the owner's decision (A, then B) made use of the wait.

### 13.7 Lessons added on 2026-10-13 (campaign 33, ENC_compare, prompts/35)

34. **"Gate-only clean fraction" is convention-dependent by 15 %.** Feeding the published two-qubit error $8.3\times10^{-4}$ to Aer's `depolarizing_error` (fault probability $\tfrac{15}{16}p$) gives $f_0=0.1722$ for the 2x3 family; treating the same number as the full fault probability (the project's device table) gives 0.1502 (ratio 1.147 [MINE]). The vendor's "error per gate" is the probability of a non-identity Pauli, i.e. the second convention for the emulator (the noise descriptions in `validation/C4_FCELLS_A.json` say "The vendor emulator's p is the probability of a non-identity Pauli (16/15 resp. 4/3 times larger fault rate in Aer's convention): not converted"). So the E1-E4 scenarios may be up to 16/15 too optimistic in fault rate; no file quantifies the effect on $\hat f_{\rm ideal}$. Evidence: `validation/C4_FCELLS_A.json -> data.noise_descriptions.E1.aer_convention`.
35. **The scenario is as important as the physics.** At the published H2-2 rates the simulated 2x3 clean fraction clears the bar (lower 95 % end 0.186); with the vendor's emulator parameter set, which adds an angle-dependent two-qubit error and a larger $p_2$, it only just reaches it (0.102, lower end 0.087); at twice the error it fails (0.061). The campaign cost swings by a factor 2.7 between tiers 0.15 and 0.05 (Section 7.4).
36. **The reference-hit fraction is nearly blind to phase noise.** Adding memory dephasing that cuts the analytic $f_0$ from 0.172 to 0.107 changes $f_{\rm hit}$ by less than one standard error (z = 0.2, 0.7, $-0.9$). The statistic the signed bar is read on therefore cannot detect the one device term the project calls decisive (transport dephasing on a trapped-ion machine). [MINE, a judgement]
37. **The project's S1 proxy is conservative relative to Aer.** At the same plan and shot count `CV_2x3_plan` (proxy at $0.7f$) gave $E_R-E_0\approx3\times10^{-3}$, the Aer run $2.4\times10^{-4}$: 10 to 15 times better; the Aer run's measured $\hat f_{\rm ideal}$ (0.130) was 1.9 times the proxy's effective 0.07. Whether the proxy is also conservative relative to a real device is not known (on IBM the proxy was optimistic by orders of magnitude, lesson 7).
38. **A simulation that agrees with data for a wrong reason is worse than one that disagrees.** The unital PTA channel reproduces the device's Hamming weight ($z=+1.8$) because it cannot produce a deficit at all; the exact channel disagrees by 54 $\sigma$ because it was compared on a different circuit (T0 versus the flown T3). The comparison must be made on the same circuit (Section 8).
39. **Silent logic errors do not raise.** The C2_CAL sampler computed a deadline from a discarded one-shot warm-up (set-up time on the A100) times the round's 128 shots, predicted 1 571 s, and silently drew 0 shots in two arms; the run finished green on every other criterion. The same rule would have zeroed most class-4 runs. Fixed by a bound $t(s)\le t_p\max(1,s/s_p)$ and a regression test that fails on the old code (7 of 8).
40. **Preflight every dependency.** Three Perlmutter jobs died after 15-21 s on a missing python package and wrote no JSON; now the driver imports its module list first and exits in under 5 s with the pip line.
41. **Size by scenario, not by the cheapest scenario.** The E3/E4 two-qubit channels cost 2.8 times and E5 5.5 times the E1 time per shot; the 33a sizing (one rate) would have given the E3 and E5 plan-of-record runs 29-60 % of their shots. The rule `r_s = r_ladder * rho_s` (measured slopes) fixed it, and F3 (15 jobs) and F6 (10 jobs) are deferred rather than shrunk because a shrunk run is no longer the plan of record.
42. **A shorter encoding is not free.** De-duplicating the flux bits shortens the 2x3 circuit by 7 to 10 % and the active qubits from 20 to 13, but the Gauss-law redundancy *is* the error-detection code: single-flip detection falls from 98 % to 83 % ($B=0$), random acceptance rises 128-fold, and the saturation parameter at the plan shots goes above 4. The multiplexed-rotation counts do not change; the cost is the physics. Not adopted.
43. **Exactness without a statevector, and its limit.** At 28 qubits the conversion to native gates can be proved locally (segment by segment, `Q1L`: 79 of 79 circuits), but pytket's angle canonicalisation adds a rigorous state error bound $B$ of $5\times10^{-9}$ on the qiskit opt-3 source and $6\times10^{-12}$ on the structured source; and the opt-3 source itself was already $1.5\times10^{-9}$ from the exact state before any conversion. The project therefore measures the $10^{-10}$ bar on the GPU instead of bounding it (`prompts/35b`; Section 9.6). (Updated 2026-10-15; the 2026-10-13 text quoted an executor's interim residual of $8.3\times10^{-13}$ on 8 circuits.)
44. **The coarse-step family does not scale with $k$.** All circuits of a reference have the same gate skeleton (252 ZZPhase at 2x2, 2 158 at 2x3, 69 676 or 71 548 at 2x4) with the angle $k\,\Delta t$; a prompt that assumed $k$ repetitions had to be corrected (`prompts/35a` R1; `Q0P_2x2` Q2, `Q0P_2x4` Q2). Consequence: the $k=4$ circuits are not four times as costly or as noisy as $k=1$; their lower reference probability (0.24 versus 0.92) is why they need more shots.
45. **The queue, not the GPU, is the bottleneck.** One measured round trip of four jobs took 24.7 h; the 12 timed campaign jobs used 3.32 GPU-hours; the maintenance window 2026-10-21 to 2026-10-28 caps the campaign at about 32 jobs. Request ordering therefore matters more than job speed (`prompts/33b` R7).
46. **Unmerged parallel work is a bookkeeping risk.** On 2026-10-13 two executors were paused mid-task in separate worktrees with their results uncommitted. Both were resumed and merged the same day (Section 6.29 addendum), and their numbers survived unchanged into committed files; the risk did not materialise this time.

### 13.8 Process issues recorded 2026-10-13 to 2026-10-15

1. **`scripts/ci_request.sh` and the merge history.** The script commits a request and pulls with `git pull --rebase`; on 2026-10-14 the local `master` carried merge commits (`7c46329`, then `4b8ca48` and `34fea24` around the requests), and the rebase conflicted with them. The coordinator therefore wrote the request files and committed them directly (`6c3e684` 4 files, `f4c71e8` 5 files, `34f73a7` 8 files; each touches only `ci/requests/NNN-<TOKEN>.txt`, as the script's own commits do; the account of the conflict is the owner's brief to this report, the merge commits are in `git log`). The poller accepted the direct commits (`<path>@<commit>` identity), so nothing was lost; the risk is that the script and the hand path drift (numbering, format). No fix to the script is recorded.
2. **`scripts/ci_check.sh` is not purely read-only.** Its first action is `git pull -q --rebase --autostash origin master` (line 12). Run for this report at 17:43 UTC it stashed the uncommitted `.claude/settings.local.json`, pulled `10f88a0` (`prompts/33e`) and re-applied the stash. Harmless here, but a "read the queue" command that rewrites the working tree is worth knowing.
3. **The `C2_KCHK` laptop dry run cannot meet its time budget.** The dry runs of campaign tokens have an 8-minute budget (S2 allows $1.1\times480+120=648$ s) and the test `test_dry_run_json_exists_and_passes_its_structural_criteria` requires `wall_seconds <= 600` (`tests/test_campaign33_driver.py` line 165). `C2_KCHK` samples 21-qubit noisy circuits in six arms including Kraus and RM on the CPU, which cost about 174 and 84 s per shot on the laptop (Section 8.5); its dry run took **1 152 s** ("six 21-qubit calls at about 250 s each under load", `prompts/LOG.md` row 156). The CPU Kraus arm is slow by design (it is the reference the GPU is checked against), so the test fails in every full pytest run on `master` (`Q0P_2x4` Q7: 1 failed in each environment). No ruling on the test (exempting the token, a smaller dry design, or a longer dry budget) exists yet; `prompts/33e` does not address it.
4. **The CPU phases of every CI job ran on one core** (Section 4.6 note; `prompts/33e` R1): `srun` without `--cpus-per-task`. It voided `C2_KCHK`'s CPU arms and slowed every job's decoding and Ritz phases; the planner states that no number changes. Fix ordered, not yet committed.
5. **The conservative deadline bound costs shots.** `call_bound` charges a short call as a full chunk, which stopped `C4_PART_02` and `C4_PART_04` at 91.4 % of their shots although about 1 000 s were left (Section 7.9). It is the price of the fix that prevented zero-shot arms; a bound with a per-call set-up term would be tighter (my suggestion; no file proposes it).
6. **The assembly lags the harvest.** 25 class-4 files are in, 22 of them parts of split runs, but `scripts/campaign33.py --stage assemble` has not been run on real data, so CV0-CV5 of the split runs, P15 of the S3 quotas, the merged certificates, the `C4_CF` owner-item evaluation and the campaign report do not exist yet. Section 7.10 gives rigorous bounds in the meantime.
7. **Status bookkeeping is behind.** `validation/gates.md` (regenerated 2026-10-14 at `e66eb26`) lists the Quantinuum gates but none of the campaign-33 tokens and not `K0_2x3_2x4`; `graphify-out/graph.json` was built on 2026-10-08 and does not index the code of 2026-10-13/14 (navigation only, so no number is affected).

### 13.9 Lessons added on 2026-10-15

47. **A GPU simulator path can be internally inconsistent.** Aer 0.15.1 on the A100 gives mean Hamming weights 3.00, 3.57 and 1.14 for one Kraus channel on one circuit depending on the engine and on gate fusion (fusion on versus off: $z=5.8$ within one job), while the CPU gives 7.47 and the RM channel gives 7.42-7.43 on both. A correct simulator is invariant under such switches (`prompts/33e` R5). Only the class-2 Kraus arms used this path (the audit); nothing else is affected.
48. **A reference arm must be validated before it decides anything.** `C2_CAL` run 3 set "production = Kraus" by comparing RM against the GPU Kraus arm, which turned out to be the suspect path; the decision was withdrawn (`prompts/33d` R5). A decision field that is computed against an unvalidated reference should not be acted on until a second engine agrees.
49. **A zeroth-order estimate that agrees with a number is not a confirmation.** The planner's 2.64-bit relaxation estimate "matched" the GPU Kraus value 2.40 and was used to explain the 54-sigma device gap; it had neglected the final basis rotation and $T_2$ dephasing and was withdrawn the same day (`prompts/33c` at about 15:41 UTC, `prompts/33d` at 19:42 UTC; `prompts/33d` R0).
50. **In simulation, the 2x3 SKQD pipeline certifies $E_0$ in every scenario tried.** Ten full runs (25 files), four noise families, two circuit sources, both sectors: $E_0$ inside the certificate 25/25, recall of $S_{999}$ $\ge0.989$, $W\ge0.99985$, $E_R-E_0$ $1.2	imes10^{-4}$ to $1.1	imes10^{-3}$, Kato-Temple widths 87-218 times below the limit at $B=0$, Weinstein widths 1.7-4.1 times below it at $B=1$ (Section 7.8). The *model's* clean fractions were 0.12-0.24; this is the strongest evidence in the project that the method itself is sound at 2x3, and it says nothing about a device.
51. **More shots buy little once the clean fraction is about 0.12 or more.** The $2\times10^5$-shot quota improves $E_R-E_0$ by a factor of at least 2.0-2.6 over the plan of record at 5.7-7.3 times the shots (different scenarios, so indicative only; Section 7.10 item 2).
52. **Check the exactness bar at the source, not only after conversion.** The 2x4 opt-3 circuits were $1.5\times10^{-9}$ from the exact state before any Quantinuum conversion, which the conversion proof could not see; a structured source without a qiskit transpile has a bound three orders of magnitude lower (Section 9.6).
53. **Infrastructure assumptions must be measured in the job.** A job allocation of 32 CPUs gave the job step one CPU; only a CPU-heavy arm made it visible. `prompts/33e` makes the affinity a recorded, checked field (S3).
54. **When the queue is free it is fast.** On 2026-10-13/14 a wave of four or five one-GPU jobs went from request commit to last harvest in 1.0-5.4 h, against 24.7 h on 2026-10-08/09; the maintenance window, not the GPU, is the binding constraint for the rest of October.

## 14. Where we are, what can be published, risks

### 14.1 One-paragraph state of every track (updated 2026-10-15)

- **Physics core (E1-E3, S1, CS):** done and reproduced on cloud, laptop and (for the noiseless sampler) the Perlmutter GPU (all PASS).
- **Circuit layer:** exact structured circuits verified at 2x2, 2x3 and 2x4 (S2, S2_2x4 PASS); the native Quantinuum circuits are now committed gates at 2x2 (`Q0P_2x2` PASS) and 2x3 (`Q0P_2x3` PASS); at 2x4, 79 circuits in two sources with the conversion proven but the $10^{-10}$ state bar awaiting the GPU (`Q0P_2x4` FAIL by construction). The routed IBM version of the 2x3 circuit (5 659 CZ) was flown once. Rejected: a de-duplicated encoding (`ENC_compare`).
- **2x2 hardware:** the full SKQD run is done (H0_2x2 PASS, 53.0 s). Verdict "methods note, not an SKQD physics result"; the XY4 gain did not replicate. No QPU job since 2026-10-06; 273 s left.
- **2x3 hardware:** one job, a **measured NO-GO on IBM**. Only Quantinuum H2-2 / Helios-1 meet the signed gate-error bar on published numbers; access is not requested (draft only).
- **2x3 simulation, Quantinuum-type noise (substantial progress):** noiseless picture complete; f-cells 45 of 77 cells; **ten full noisy SKQD runs in 25 files** (F1, F4, F5, F7, F8, both sectors), every one certifying $E_0$ with widths far inside the signed limits (Section 7.8); F2 requested; F3 and F6 deferred past the maintenance; the campaign assembly not yet run.
- **2x3 simulation, IBM-type noise:** **blocked**. The GPU Kraus path of Aer 0.15.1 is internally inconsistent; the representation decision (`C2_KCHK`) returned without its CPU reference; run 2 is ruled (`prompts/33e`); no class-2 cell has run.
- **2x2 and 2x4 on Quantinuum (new, gates):** 2x2 passes every tier that can run without an account (T1, T2, T3, T4, T6), with gate-only $f\approx0.79$-$0.80$ on H2-2 / Helios-1 and a D3' plan of about 14 000 HQC; 2x4 is out of reach on every device ($f_0\le10^{-23}$ at published rates).
- **Neural / ML step:** only the minimal ridge ranker on exact amplitudes.
- **Statistics machinery for the 2x3 plan:** complete and signed; $r_{nc}$ remains an open owner item (1.115 versus 1.078).
- **Process:** 352 commits; 87 gate files (69 PASS, 18 FAIL); both executor branches merged; 8 Perlmutter requests pending; one ruling (`33e`) waiting for its executor; the maintenance 2026-10-21 to 10-28 ahead.

### 14.2 The Quantinuum route (the only device route that reaches the signed bar)

Facts (all `reports/qpu_survey_2x3_20261002.md`, `data/quantinuum/devices_20261002.json`; vendor numbers were read on 2026-10-02, none measured by this project):

| device | qubits | 2q error | gate-only $f$ (2x3) | $f$ with memory (low / mid / high, ESTIMATE) | HQC per full D3-type campaign (ESTIMATE) |
|---|---|---|---|---|---|
| H2-2 | 56 | $8.3\times10^{-4}$ | **0.1502** | 0.1454 / 0.1398 / 0.1130 | 507 144 (102 100 shots, 60.1 machine-hours at the mid scenario) |
| Helios-1 | 98 | $7.9\times10^{-4}$ | **0.1642** | 0.1378 / 0.1117 / 0.0352 | 634 299 |
| H1-1 | 20 | $9.7\times10^{-4}$ | 0.1113 | 0.1049 / 0.0977 / 0.0661 | 725 197 |
| H2-1 | 56 | $1.1\times10^{-3}$ | 0.0860 | 0.0815 / 0.0764 / 0.0535 | 927 358 |

The memory (transport) error of a 20-qubit, mostly serial, 1 925-two-qubit-layer program is *unknown* (three ESTIMATE scenarios); the vendor emulator (H2-2E) carries the real transport schedule and replaces it.

**The staged plan** (after `prompts/26`, `28`, `29`, `31`; decision 2a signs the minimum sizing, the decision of 2026-10-05 approves the $B=1$ doubling, no HQC committed):
- **Stage E (emulator H2-2E):** two $k=1$ circuits at 800 shots and two $k=4$ circuits at 200 shots: **9 949.92 eHQC** (gate-computed: `validation/Q0P_2x3_plan.json -> data.stage_E_v3.hqc_total`, 4 jobs, 2 000 shots; v1 was 11 936 eHQC). Read $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ with GO rule v3: GO iff lower 95 % $\ge0.05$ and point $\ge0.10$; NO-GO iff upper 95 % $<0.10$; AMBIGUOUS otherwise (one top-up).
- **Stage P (hardware pilot on H2-2):** the same four circuits and shots, **9 949.92 HQC** (USD 124 374 ESTIMATE at 12.5 USD per HQC).
- **Campaign (plan of record, gate `CV_2x3_plan` / `Q0P_2x3_plan`; Appendix block (g)):** rule D3'-R with sector $B=0$ at $s=1$ and $B=1$ at $s=2$, sized at $\hat f_{\rm ideal}$ and re-sized at the measured value before any submission. At $f=0.10$: **133 909 shots, 53 jobs, 665 605 HQC**, about 78.8 machine-hours at the mid memory scenario and an Azure-Standard-equivalent 8.32e6 USD at 12.5 USD per HQC (ESTIMATE: the pay-as-you-go and research rates are not public; the hours and USD are sums of the per-sector ESTIMATE fields in `validation/CV_2x3_plan.json -> data.plan`, my addition); at $f=0.05$: 257 475 shots, **1 279 660 HQC** (151.4 machine-hours); at $f=0.15$: 94 909 shots, **471 801 HQC** (55.8 machine-hours). For comparison the un-doubled base plan was 418 166 HQC at $f=0.10$. The convergence condition (decision 2a) is met; the factor $s=2$ at $B=1$ is the whole of the re-sizing, and no further multiple is expected unless the measured $f$ differs. Commercial purchase is not realistic (the only published rate is the Azure Standard plan: 125 000 USD per month for 10 000 HQC); the realistic routes are a QCUP allocation or a research agreement.
- **Access (not yet requested):** the drafted email to Sales@Quantinuum.com (route B; also the project summary for QCUP, route A). QCUP: default hardware quota 0 HQC, emulator quota 6 000 s, requests must be justified by emulator results; eligibility ("US national labs, universities, government, and industry") to be confirmed by the owner. Helios-1 needs a Guppy/HUGR program (Stage A9 not built).

*My reading (not a project statement):* every Quantinuum number above is a vendor-published or planner-estimated *prediction*; the project's one device-versus-model comparison on IBM missed by a factor of about 330 before idle dephasing was included and, on 2026-10-06, the same circuits' clean fraction moved by a factor of 2 between days, so the first emulator stage (Stage E, which carries the vendor's real transport schedule) is the first informative number for 2x3 on this route and should be read before any larger budget is discussed.

*What campaign 33 adds to this route (updated 2026-10-15, [SIM]).* At the published H2-2 rates the simulated $\hat f_{\rm ideal}$ is 0.207 (f-cells) and the full plan-of-record runs F1 give pooled 0.228 ($B=0$) and 0.218 ($B=1$) [MINE pooling], with $E_R-E_0\approx3\times10^{-4}$ and certificates far inside the limits in both sectors; under the matched scenarios E7(0.07) / E7(0.10) / E8 the pooled $\hat f_{\rm ideal}$ is 0.117-0.168 and the runs still certify $E_0$ (Section 7.10). With the emulator parameter set (E3) the f-cell value is 0.102 and the plan tier falls to 0.05 (1 279 660 HQC); its full runs (F3) are deferred. The decisive unknown stays the transport (memory) error, which $f_{\rm hit}$ cannot see (lesson 36) and whose full runs (F6) are deferred. **For 2x2** the same route is ready to the last step: circuits, HUGR packages, three-engine verification, syntax-check job records and a 13 990-HQC plan (H2-2); it would be a cross-platform check, not a physics result (saturation). The vendor emulator (Stage E) remains the first informative number for 2x3.

### 14.3 IonQ and 2x4

- **IonQ:** unchanged: no accessible IonQ device can run 2x3 (Forte / Forte Enterprise gate-only $f=8.6\times10^{-5}$; Tempo is a projection whose 99.9 % target gives $f\approx0.077$). 2x2 on Forte Enterprise is feasible on paper (gate-only $f=0.303$, about 5-20 kUSD at Braket rates [PLAN]); no IonQ tooling exists.
- **2x4:** compiled and verified (qiskit circuit: one; native Quantinuum circuits: 79 in two sources, conversion proven, state bar pending `QV_2x4_01`); every Quantinuum scenario at published rates gives $f_0\le10^{-23}$ (`QN_2x4`); on Heron the ceiling is $\sim10^{-53}$; IonQ's job limit is below the 208 399 native gates. No device action is planned; only the GPU verification.

### 14.4 Publishability

*Source: `reports/H0_2x2_full_hardware_report_20261002.md` section 6 (planner, written 2026-10-02, with the field survey of arXiv abstracts fetched that day), updated for the results of 2026-10-06 and, in Section 1.5, for 2026-10-13 and 2026-10-15; the campaign-33 simulations add no hardware claim (`validation/H0_ddrep.json`, `validation/K1_2x3_fpilot.json`). The planner has not rewritten its section 6 after the replication; the updates below are my reading of the new gate results and are marked as such.*

- **Today's 2x2 result can claim:** a validated, preregistered, end-to-end SKQD pipeline for a 2+1D SU(2) gauge theory with staggered quarks on a Heron processor (intertwiner-labelled basis, Gauss-law decoder with 0 mismatches over 58 hardware strings in the full run and 0 over 58 and 99 strings in the two 2026-10-06 jobs, exact structured circuits, ALAP, a calibration-content guard, certified Ritz energies with their controls); a signal support of 35/38 and 19/20 states; a quantified statement of why the all-state energies carry no device information; and measured clean fractions on 12-qubit, 588-CZ, 44 $\mu$s circuits **with their dates**: on 2026-10-02 0.0413 [0.0361, 0.0470] without decoupling and 0.1271 [0.1084, 0.1479] in the full run with client XY4; on 2026-10-06 0.0818 [0.0758, 0.0881] without decoupling and 0.0732 [0.0675, 0.0792] with XY4, on the same frozen circuits and patch. **Caveats that must travel with the 2x2 signed-bar statement:** (a) it was a GO on $f_{\rm hit}$ under the preregistered rule and reads AMBIGUOUS on $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ (adopted cell 0.1012 [0.0938, 0.1091], `validation/CF_estimator_2x2_info.json`; decision 3a; the idle-dephasing correction on `ibm_kingston` is unmeasured and the A5 model bracket has $r=0.67$-$0.90$); (b) **it is a one-day result**: four days later the same cell read NO-GO (0.0732 on $f_{\rm hit}$, 0.0656 [0.0599, 0.0717] on $\hat f_{\rm ideal}$), and the baseline itself moved by a factor 2.04 (my division), so the "day-to-day caveat" is part of the claim; (c) the wording in `prompts/31` ruling 6 is the planner's proposed external text.
- **It cannot claim:** an SKQD accuracy result (saturation), a device-support-quality result (recall 1.0 is reached by noise alone; no CIPSI control on hardware data), a claim about the circuit family's clean fraction (the bar was read on $k=1$ circuits only), **a dynamical-decoupling gain (it did not replicate)**, "neural-enhanced", or any physics number beyond reproduction of known exact values.
- **Verdict (planner, 2026-10-02, with my update):** publishable as (a) a methods / technical note on running sample-based diagonalization honestly at a size where noise saturates the subspace (clean-fraction estimators, near-clean term, saturation rule, signal-support definition, garbage/random baselines, the 2x2 run as worked example). The planner's option (b), **a short note on client-side XY4 raising the clean fraction 2.8x on a Heron r2, is no longer supported as written**: its precondition ("after replication") failed. *My reading:* what the replication adds that can be written honestly is a negative-result section for the methods note: the same-circuit baseline varied by 2.04x between two calibrations, a one-job A/B test cannot be trusted across days, a coherent $x$-pulse over-rotation of 0.015-0.020 rad exists on all 12 qubits and is invisible in the calibration record, and 2x3 on IBM Heron has a measured upper limit $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %). Not publishable as an SKQD result for SU(2) lattice gauge theory.
- **Context:** "first SU(2) with dynamical matter on hardware" is not available as a claim (arXiv:2102.08920, 2021; arXiv:2602.18080, 2026); the manual's own claim is the 2x3 result "first quantum-centric spectroscopy of a non-Abelian gauge theory with dynamical matter in two spatial dimensions".
- **What a publishable physics claim needs, in the plan's order:** (1) a lattice where noise cannot saturate the sector: at 2x3 the saturation parameter is $2\times10^5\times0.00146/677=0.43$ at most (planner arithmetic, upper bound), which needs a 2x3 device, **and IBM Heron is now measured not to be one**; (2) the primary endpoint P1, device vs CIPSI at equal $|B|$ with bootstrap bands over circuits, on that lattice; (3) the clean fraction measured on the whole circuit family ($k=2..4$); (4) repeat runs (second calibration window, patch, device; 2026-10-06 shows why: the repeat is where a one-day result fails); (5) the ML step credited or nulled under Step 7.5 on hardware data; (6) the release bundle (raw bit strings, calibration records, circuits, decoder).
- **Claim tiers for the first 2x3 hardware run** (`prompts/27`, evaluated per sector on $B_{\rm sig}$ with references always included; since `prompts/31` the 2x3 certificates and convergence criteria are read on $B_{\rm all}\cup$ references, the tier definitions below are as `prompts/27` wrote them): **Tier A** $|B_{\rm sig}|\ge40$; $E_R(B_{\rm sig})-E_0$ below the 2.5th percentile of 200 random equal-size bases (bands not overlapping); $\le1.5\times$ the BFS error at equal size; $E_0$ in the Weinstein interval. **Tier B** Tier A plus recall of the 99.9 % support $\ge0.8$ (gate H1), gap-assumed certified width $\le0.1$ containing $E_0$ (H1; now the Kato-Temple reading with the exact $E_1$), cluster energy certified to $\pm r_H\le0.15$ at $B=1$ (H2). **Tier C** Tier B plus $|B_{\rm sig}|\ge300$ and device error $\le0.5\times$ the BFS error at equal size. Thresholds are preregistered and may not be tuned to the outcome. The planner's proxy emulation (prototype, 2026-10-02, not a gate) suggests that with $f\approx0.17$ and $2\times10^5$ shots per sector $|B_{\rm sig}|=200$, $E_R(B_{\rm sig})-E_0=1.5037\times10^{-3}$, recall 0.988 (`prompts/27` T0.1).
- **What the campaign-33 class-4 runs add (2026-10-15, my reading):** a simulation section that is now complete enough to stand in a methods note: the end-to-end 2x3 SKQD pipeline under four noise scenarios (E1, E7(0.07), E7(0.10), E8) certifies $E_0$ in every one of 25 files, with the clean fraction at which it was tested stated (0.12-0.24), the S1 proxy shown to be conservative by an order of magnitude in both sectors, and gate S3's long-open recall criterion answered in simulation. It is still a statement about models; it strengthens the "device-requirement" part of a methods note, not any hardware claim.
- **What the class-2 episode adds:** a documented case of a GPU simulator path (Aer 0.15.1 GPU Kraus) giving inconsistent results for one channel, found because the project insisted on comparing against the device and a CPU reference; if confirmed by `C2_KCHK` run 2, it is an upstream bug report and a cautionary paragraph, not a physics result.

### 14.5 Risk register (my synthesis; each row names its evidence; updated 2026-10-15)

| # | risk | evidence in the files | strength | what would reduce it |
|---|---|---|---|---|
| 1 | No device is measured to reach the bar at 2x3; Quantinuum figures are vendor numbers plus unmeasured transport | Sections 7.4, 11.2; `data/quantinuum/devices_20261002.json`; K1 null on IBM | strong that IBM cannot, weak that Quantinuum can | Stage E (emulator) then Stage P; needs access (unsent) |
| 2 | The IBM-noise simulator has no validated representation: GPU Kraus inconsistent, CPU reference thin (19 + 24 laptop shots), CI CPU arms empty | Section 8; `C2_KCHK` blocked | strong that GPU Kraus is unreliable; open which path is right | `C2_KCHK` run 2, the laptop 64 + 64 shots, then `C2_XY4` |
| 3 | The clean-fraction statistic is unstable day to day and its correction unsettled | factor 2.04 between days (`H0_ddrep`); $r_{nc}$ 1.115 versus 1.078 (the rule now fires in code); the 2x2 f-cells sit 7 % below the 2x3 $r_{nc}$ expectation ("tension"); 15 % convention gap in gate-only $f$ | strong for the day-to-day change; moderate for $r_{nc}$ | a baseline in every job; owner ruling on $r_{nc}$; settle the Aer-versus-vendor convention |
| 4 | $f_{\rm hit}$ cannot see transport dephasing, the one unmeasured trapped-ion term | E5a/b/c within one standard error of E1 at 2x3 and at 2x2 (0.834 / 0.837 / 0.830 against 0.838) while $f_0$ falls | moderate (simulation) | F6 (deferred), Stage E read on support quality as well |
| 5 | Payoff: the primary endpoint is a null by design; "neural" absent; 2x2 saturates | manual Step 6.3; S1; `H0_2x2`; `QN_2x2` plan-of-record runs saturated | strong | none inside the design; the methods note is the realistic output |
| 6 | Plan cost 0.47 to 1.28 M HQC depending on the scenario; money unknown | Section 12.6 | moderate | a research allocation (QCUP or agreement) |
| 7 | Schedule: maintenance 2026-10-21 to 10-28; class 2, F3, F6, the `QV_2x4` slots and the assembly all fall after it or need owner actions | `prompts/33b`, `33e` R4 | strong | keep the queue full until 10-21 (8 requests pending) |
| 8 | Split runs are not yet assembled; two parts are short by 8.6 % of their shots and no re-request exists | Sections 7.9, 13.8 items 5-6 | moderate (bounds exist, numbers pending) | run the assembly; re-size and request the remainders |
| 9 | The full test suite has one standing failure (`C2_KCHK` dry-run time) | `Q0P_2x4` Q7 | strong | a ruling on the dry design or budget of `C2_KCHK` |
| 10 | The IBM allowance (273 s) and the day-to-day instability make any further IBM job a one-off | Section 12 | strong | decide whether to spend it |
| 11 | Every CI job ran its CPU phases on one core; fixed in a ruling but not yet in code | `prompts/33e` R1 | weak for correctness (planner: speed only), strong for the `C2_KCHK` failure | commit the sbatch fix and the affinity check |

### 14.6 Questions a judge might ask first, with the file that answers each

1. *Is the 2x3 NO-GO on IBM solid?* One job, one calibration, two circuits, 0 hits in $2\times10^5$ shots; Section 6.22; `validation/K1_2x3_fpilot.json`.
2. *Is the algorithm sound at 2x3?* In noiseless simulation yes (Section 7.2). Under four depolarizing-type noise scenarios at $\hat f_{\rm ideal}=0.12$-$0.24$, yes in both sectors: 25 of 25 files certify $E_0$ (Section 7.8). Under IBM-type noise: unknown (class 2 blocked).
3. *Does the simulated noise resemble a device?* For Quantinuum: untested (no data). For IBM: the GPU Kraus path is inconsistent and the RM path has not been compared with the device on the flown circuit (Section 8).
4. *Are the certificates trustworthy?* Rigorous inequalities given the gap assumption; at $B=0$ the width uses the exactly known $E_1$ (owner-confirmed caveat). Section 2.7.
5. *Could classical methods do the same?* The manual says CIPSI at equal subspace size is at least as good; the project claims no advantage.
6. *What does a split run's "PASS" mean before assembly?* Each part passed its own variational and recall checks; the merged energy is bounded above by the best part (Section 7.10); CV0-CV5 and P15 of merged runs are not yet computed.
7. *What is the contradiction list?* Section 16.

## 15. Open owner decisions (numbered)

Sources: `prompts/33` sections 6 and 7, `33a` section 8, `33b` section 6, `33c` section 5, `33d` (owner items), `33e` section 4, `prompts/34`, `prompts/35` section 6, `35a`, `35b`, `prompts/27` decisions D1-D7, `prompts/LOG.md`. **No file records an owner answer to any item below** (the newest owner-decision file is `data/owner_decision_20261006_A_then_B.md`). Renumbered on 2026-10-15; the item "resume the two paused executors" of the 2026-10-13 list is closed (both merged). Where a file states the planner's or executor's recommendation I give it as such.

1. **$r_{nc}$: keep 1.115 or move to 1.078? (the `C4_CF` owner item).** The new `C4_CF` pooled $r$ is 1.055 [1.033, 1.078] (upper end `r_nc_new` 1.0779); the signed value is 1.1151 (`data/cf_trajectories/r_nc.json`). The rule of `prompts/33` (sections 6 and 8) fires: the code now evaluates it as section 6 OR section 8 and it **fires** on job 59736866 (Section 7.6; the harvested JSON's own field still reads false and is not rewritten). Options: keep 1.115 (conservative; every $\hat f_{\rm ideal}$ in this report uses it) or replace by 1.078 (every $\hat f_{\rm ideal}$ rises by 3.4 %, $1.1151/1.0779=1.0345$ [MINE]; no plan tier changes). The $k=4$ arm (1.172 [1.128, 1.217]) is above both, so decide also whether $r_{nc}$ stays a $k=1$ quantity. New context: the 2x2 f-cells (`QN_2x2` E1 band) sit 7 % below what 1.115 predicts ("tension", information). *Cost:* none. *Default if no answer:* 1.115.
2. **Send the Quantinuum access request** (`proposal/quantinuum_access_request_draft_20261005.md`; route A the OLCF QCUP, route B Sales@Quantinuum.com). Still the only path to 2x3 hardware data; still unsent. The Section 7 results (now ten full noisy runs) can be cited as the emulator-justification QCUP asks for.
3. **The Stage E and Stage P budgets** (9 949.92 eHQC, 9 949.92 HQC; separate written decisions; none signed).
4. **Approval of a full 2x3 campaign** once Stage P has measured $\hat f_{\rm ideal}$: 665 605 HQC at 0.10 (1 279 660 at 0.05; 471 801 at 0.15), re-sized at the measured $f$; the static-charge sectors of the manual's Step 9.2 still have no plan.
5. **A Nexus login** (`scripts/quantinuum_account.py --login`): unlocks the free syntax checks already prepared for every lattice (`QSC_prepared`: 2x2 H2-2SC and Helios-1SC, 2x3, 2x4 both sources) and Stage E.
6. **The `skqd-pecos` conda environment on Perlmutter** so that token `C3_LE` (the vendor's local emulator at 2x3) can run; the laptop smoke test passed at 98 s per shot.
7. **The 2x4 GPU verification:** install `ci/allowed_jobs.q35` (8 lines `QV_2x4_01..08 01:00:00 1`) on Perlmutter; `QV_2x4_01` is predicted at 888 s and decides the frozen 2x4 source; the $k\ge2$ checks are about 1.6 GPU-hours [PLAN, `prompts/35a` R1]. Only verification: no device can run 2x4.
8. **Class 2 if `C2_KCHK` run 2 reads `blocked`** (`prompts/33e` R4, section 4 item 3): run class 2 on the native-GPU Kraus engine (2.2 s per shot, about 1 000 shots per cell) only if K3 validates it, else drop class 2. Before that, nothing is needed from the owner (the sbatch fix is in the repository and the `C2_KCHK` allowlist line exists).
9. **File the qiskit-aer issue** (`prompts/33d` R4, `33e` R5 and section 4 item 2): the GPU-versus-GPU Kraus inconsistency is available now (raw counts in `validation/C2_KCHK.json`), the GPU-versus-CPU part after run 2. The owner files it with QPY, model dictionary, seeds, counts and versions.
10. **The deferred campaign-33 jobs after the maintenance:** F3 (15 jobs; E3, the scenario that halves the clean fraction and sets tier 0.05), F6 (10 jobs; E5b, memory dephasing), the class-2 cells on the decided representation, the 2-part `C4_CF` re-request, the remaining f-cell slots and the cv3 slots of F2_B1. `prompts/33b` recommends F3 first if only one is run.
11. **Which noise parameter set defines the planning scenario** (E1: tier 0.15, 471 801 HQC; E3: tier 0.05, 1 279 660 HQC; or the matched-$f$ E7 series), **and which error convention** (Aer's $\tfrac{15}{16}p$ fault probability versus the device table's full-probability reading) is the vendor's.
12. **D4 (`prompts/27`): an unsigned cheaper 2x3 circuit family?** (no-plaq1, fixed-angle; needs stage T0c and a signature). `ENC_compare` already ruled out a cheaper encoding.
13. **D5 (`prompts/27`): re-order the signed term order for parallelism?** Only if the Helios-class device-model stage `S3H` (not built) shows the pessimistic idle end dominates.
14. **IonQ 2x2** as a cross-platform check (5-20 kUSD at Braket rates [PLAN]); no exporter or submission code exists.
15. **The 273 s left on the IBM open plan** (about 290 s from about 2026-10-20 if the rolling window behaves as inferred). No file proposes a spend.
16. **The 400 IBM minutes** (allocation awaiting approval; not visible to the account as of the last handover).
17. **Publication route** (Sections 1.5, 14.4): write the methods / negative-result note now? Its simulation section is now substantial (Section 7); the XY4 note is not supported as written; the external wording of the 2x2 signed-bar qualification (`prompts/31` ruling 6) is not owner-confirmed in any file.
18. **The 0.82 readout factor** double-counts readout survival on Quantinuum; removing it lowers every shot count by 18 % (`reports/2x3_shot_rule_estimator_ruling_20261003.md` section 5).
19. **Amendment 01 item 4** (the 2x3 device; IBM excluded by measurement, Quantinuum remains) and **item 5** (the shot quota of Step 9.2; the plan of record answers it for two of four sectors, and F4/F8 show what the manual's $2\times10^5$ quota buys in simulation).
20. **The ML step:** build the graph network of manual Step 7 and the seven-protocol comparison once 2x3 data exist; until then "neural" is a plan.
21. **Encoding question** (`prompts/34`): is losing the link check ever acceptable; reopen unsigned approximate generators; a q-deformed SU(2)$_k$ target?
22. **Housekeeping (no physics):** delete the untracked empty directory `data/hardware/H0_ddrep_dryrun_prototype/`; register the campaign-33 tokens and `K0_2x3_2x4` in `scripts/update_status.py` (`validation/gates.md` of 2026-10-14 lists none of them); `graphify update .` (graph from 2026-10-08); push (the coordinator's call, `CLAUDE.md` rule 5; this report's commit is local).

*Items for the planner or coordinator, not the owner (listed so that they are not lost):* (a) re-size and request the remainders of `C4_PART_02` and `C4_PART_04` (4 288 shots each; `ci/parts/README.md` rule); (b) a ruling on the `C2_KCHK` dry-run test (Section 13.8 item 3); (c) execute `prompts/33e` steps 1-4 (sbatch fix, run 2, laptop CPU reference); (d) run the campaign assembly on the harvested files; (e) decide whether `scripts/ci_request.sh` should be fixed or retired for direct commits.

## 16. Gaps, discrepancies and numbers I could not source

### 16.1 Contradictions and tensions between files (updated 2026-10-15)

1. **Class 2 (Section 8).** Three GPU executions of one Kraus channel give $\bar w$ = 3.00, 3.57 and 1.14 (`validation/C2_KCHK.json`), the laptop CPU gives 7.47 (`data/campaign33/c33c_diag/summary.json`), RM gives 7.42-7.43 on the GPU; the device gives 9.77 on a different circuit. `validation/C2_CAL.json -> data.decision.production_representation` still reads `kraus`; `prompts/33d` R5 says that decision "does not stand" and `C2_KCHK` supersedes it (the JSON is not rewritten by design). Unresolved until `C2_KCHK` run 2.
2. **$r_{nc}$ owner-item rule.** `validation/C4_CF.json` stores `owner_item_r_nc_outside_old_interval: false`; the code (after the `c33c` executor's step 3) evaluates the rule as firing; `prompts/33c` said it fires. Reconciled in code, not in the harvested JSON; the decision is the owner's.
3. **The 2x2 E1 band.** `validation/QN_2x2.json -> data.fcells.E1_band`: 22 751 reference hits against 24 433 expected from $f_{
m hit}=f_0\,r_{nc}$ with the 2x3 $r_{nc}$ (band [24 127, 24 740]): verdict "tension" (information). Either the near-clean excess is smaller at 2x2 (likely: different circuits) or the 2x3 $r_{nc}$ is not transferable; the file itself says 2x2 has no $r_{nc}$ of its own.
4. **Queue round trip.** `prompts/33e` R4 plans with "the measured 25-h round trip" (from 2026-10-08/09); the CI robot's commit times give 1.0-5.4 h per wave on 2026-10-13/14 (block (a2)). Both are measurements of different days; the planner's figure is the conservative one.
5. **The bootstrap bands of the class-4 runs** exclude their own point value in 25 of 25 files (Section 7.8); the gate stores them as "95 %" intervals. My reading is that they are biased (a resample cannot add states); no project file discusses it.
6. **The matched-$f$ label** (carried): E7(0.07) measures pooled $\hat f_{
m ideal}=0.130$ / 0.117, E7(0.10) 0.168 / 0.163 [MINE pooled] (Section 7.10 item 4).
7. **Gate-only $f$ for the same circuits and rates** (carried): 0.1502 (device table) versus 0.1722 (Aer convention) at 2x3; at 2x2 the native 0.7929 versus the pre-native 0.7875 (252 versus 256 two-qubit gates).
8. **S2_2x4's exactness versus the 2x4 bar.** `validation/S2_2x4.json` PASS 12/12 states exactness $3.4	imes10^{-14}$ (the structured circuit) while its GPU stage found the qiskit opt-3 circuit $1.528	imes10^{-9}$ from the exact state (`data.gpu_validation`); S2_2x4's C6 checked leakage only. `prompts/35b` drew the consequence (the $10^{-10}$ bar was never met by an opt-3 2x4 circuit).
9. **Prompt versus part file:** `prompts/35b` section 4 says "six statevector runs" for `QV_2x4_01`; `ci/parts/QV_2x4_01.json` carries nine (eight listed native/source runs plus the S2_2x4 reproduction) and records the reason in `run_count_note`.
10. **Gate-FAIL semantics:** 6 of the 18 FAIL files (`C4_FCELLS_A`, `C4_CF`, `C4_PART_02`, `C4_PART_04`, `Q0P_2x4`, `C2_KCHK`) fail on budget, infrastructure or by construction, with their physics criteria passing (Section 5.4). Counting them as failures overstates a physics problem; counting them as passes would break Rule 1.
11. **Status files behind the data:** `validation/gates.md` (2026-10-14) lists no campaign-33 token; `scripts/ci_check.sh` prints requests 001-004 and 009 as pending although their jobs ran (carried).
12. **The previous report's queue section** listed `C4_F1_B0`, `C4_F7_B0`, `C4_F5_B1`, `C4_PART_01` as running, but their results were committed by the CI robot (17:07-18:07 UTC) before that report's commit `da21d6e` reached `master` (author time 16:52 UTC; the commit sits on top of the robot's result commits in the history); the report text was written before the harvest. Harmless; corrected here.
13. **Prompt versus code (campaign 33, carried):** `prompts/33` names `B0_ref117_k1` / `B1_ref29_k1` as the f-cell circuits; the code uses `B0_ref25_k1` / `B1_ref57_k1`.
14. **Time stamps (carried):** the gate JSONs of Perlmutter jobs carry PDT `environment.timestamp` (end time), request commits MDT, robot commits PDT; all UTC conversions in this report are mine.

### 16.2 Numbers I could not source or reconcile (new items)

A. **The `ci_request.sh` conflict.** The account that `git pull --rebase` conflicted with the merge history comes from the owner's brief for this report; `git log` shows the merge commits and the direct request commits, but no file records the conflict itself.
B. **Merged class-4 runs.** No project file holds the merged split runs, CV0-CV5 of split runs, P15 of the S3 quotas, or the merged certificate widths; Section 7.10 gives my pooled clean fractions and rigorous bounds only.
C. **`C2_KCHK` run 2 expectations** (about 40 Kraus + 80 RM CPU shots; $\pm0.4$ / $\pm0.3$; the node taken as 3 times the laptop) are planner arithmetic [PLAN] in `prompts/33e` R2.
D. **Why NAT-O2 samples about 20 % faster than NAT-O0** under the same E1 noise: no file explains it.
E. **The per-shot CPU cost of `C2_KCHK`'s CPU arms on the Perlmutter node:** not measured (0 shots).
F. **IBM account state today:** no account check after 2026-10-06 (327 s used / 273 s left is the last recorded value).
G. **Results of the 8 pending requests** (`C4_F2_B0`, `C4_F2_B1`, `C4_PART_12..17`): unknown at the time of writing.
H. **The static-charge sectors** have no shot plan; **the random acceptance of the 2x4 decoder** is still not computed (carried).
I. **Whether the `skqd-pecos` environment, `ci/allowed_jobs.q35` and a Nexus login exist on the owner's side:** no file says they do; every gate treats them as absent.

### 16.3 Items carried over from the earlier reports (still valid unless Section 16.1 says otherwise)

1. **The canary's predicted accepted count.** `CLAUDE.md` quotes "8 accepted of 267 against the preregistered $\ge10$ and the simulated 71"; `prompts/15` D5 quotes a predicted 39.9; `validation/H0_canary.json -> data.f_comparison` gives a predicted yield 0.18725, which corresponds to 50.0 expected accepted shots of 267 **(my multiplication of sourced numbers)**. I could not reconcile the three; Section 6.7 uses the JSON values and the go-rule threshold of 10.
2. **Time zones.** The `environment.timestamp` strings in the gate JSON are in the time zone of the run (MDT, PDT or UTC) and are shown as recorded; ordering across zones in block (a) is approximate (within hours). The 2026-10-06 hardware times in Sections 6.21, 6.22 and block (i) are UTC from the `session.json` files; the gate JSON of the same jobs say MDT (UTC minus 6 h).
3. **Numbers taken from documents rather than JSON.** The following have no JSON key I could cite and come from prose reports or `prompts/LOG.md` (named where used): the CI jobs' timings and utilisations, the GPU speed-ups (19.8x, 161x, about 300x), the planner's 2x2 `AMBIGUOUS` arithmetic at $r_{nc}=1.10$, the 94 % of shots at $k=4$, the `S2D` shot-quota numbers 556 000 / 808 104, the memory scenarios' cost ESTIMATEs, the K1 expected-billed range 211.7-242.4 s, the K1 circuit build times (1 223 s / 1 250 s), the H0_ddrep dry-run sampling time (1 738 s), the garbage acceptance counts 64.6 / 40.6 of $10^5$ for K1, the "ranked 2 of 750" patch statement, and the statement that the live `ibm_kingston` record of 2026-10-05/06 had 352 of 352 CZ keys without an error (the JSON of that unusable record is under `data/hardware/K0_prep/`; I read the statement in `prompts/LOG.md`).
4. **Planner arithmetic still not reproduced by a gate:** the first-run diagnosis numbers of `prompts/31` D1 (173 states for $W\ge0.9999$, hardest state weight $1.8\times10^{-5}$, about $6\times10^6$ shots per sector), the USD figures and machine-hours (ESTIMATE inputs), the memory/transport scenarios, and the Tier-claim proxy emulation of `prompts/27` T0.1. **Now reproduced by gates:** the D3'-R plan (`Q0P_2x3_plan` P1), the re-sized plan and its HQC (`CV_2x3_plan`, P4/P7 of `Q0P_2x3_plan`), the Stage E / P plans (`Q0P_2x3_plan -> data.stage_E_v3 / stage_P_v3`), the oracle-width table (`CV_2x3_plan -> data.oracle_width_reproduction`, 196 fields, maximum scaled difference $3.2\times10^{-14}$).
5. **Values not computed in the repository.** The random acceptance of the 2x4 decoder; any measurement of Quantinuum, IonQ, Google or other non-IBM devices (all vendor numbers were read from web pages by the planner on 2026-10-01/02 and are not measurements by this project); the memory/transport error of any ion-trap device for this circuit; the mechanism of the 2026-10-02 context-aware DD collapse (not replicated, so open in a different sense); the static-sector shot plan; any 2x3 clean fraction above the K1 upper limit.
6. **Unclear count.** Test counts in Section 4.6 are the last values recorded in the cited JSON/LOG rows (the newest 342 passed / 19 skipped), not a fresh run (I ran no tests, as instructed).
7. **Derived statements that no file makes in these words (my comparisons, labelled where used):** that the day-to-day change of the no-DD baseline (factor 2.04) exceeds the same-day DD effects of 2026-10-06 (ratios 0.647-1.150) and is comparable to the 2026-10-02 XY4 gain (2.819); that the K1 upper bound is 14.6x below GO-A and about 4 850x below the bar; that P(0 hits) for the no-idle bracket is about 0.065; that the 273 s may grow to about 290 s on 2026-10-20 (inference about a rolling window, unverified); the machine-hour and USD sums for the re-sized campaign.
8. **"Five most important numbers"** in Section 1 are my selection; the project itself does not rank numbers. Every figure that the refresh task named was found in the named files; the one place where a source now disagrees with the previous report is the K0 gate, whose old FAIL 5/6 numbers (5 527 CZ, $f_{\rm ceiling}=1.095\times10^{-2}$) were superseded by the exact 5 659-CZ circuit (Section 6.20).

*Items of the 2026-10-13 report's Section 16.1-16.2 that are now resolved:* the executor numbers of Sections 8.5 and 9 that had no gate file (now in `data/campaign33/c33c_diag/` and the `Q*` gate JSONs); the CPU RM 16-shot twin and the empty CPU Kraus twin (superseded by the 19- and 24-shot committed CPU arms); the "T3 needs about 15 h" figure (superseded: T3 ran in 5.25 h under `35a` R3); the results of the four running jobs and eight pending requests of 2026-10-13 (all harvested, Section 7.8).

## 17. Progress measure

Source: `reports/H0_2x2_full_hardware_report_20261002.md` section 2 (planner, 2026-10-02): the SKQD plan was broken into 51 rows (33 rows of the manual's Steps 0-11 and 18 rows of amendment 01, the owner decisions and the preregistration discipline) and each row was scored against the *2x2 hardware campaign* with its evidence. Status key: **F** = fulfilled; **FD** = fulfilled with a deviation (named); **ND** = not done (reason named). The tally printed by the report is: **fulfilled 31, fulfilled with deviation 12, not done 8** (I recounted the table: F 31, FD 12, ND 8). The first count in the report text reads "33 manual rows + 18 amendment/decision rows". Note on scope: this scores the plan against the 2x2 hardware run only; all 2x3/2x4 hardware rows are, by that scope, "not done".

Share of the 51 rows: F 31/51 = 60.8 %, FD 12/51 = 23.5 %, ND 8/51 = 15.7 % **(sum of sourced counts)**.

**Not re-scored on 2026-10-15 either** (the class-4 runs, `C2_KCHK` and the Quantinuum gates are simulations and verifications, outside the table's 2x2-hardware scope). **Not re-scored on 2026-10-13 either.** The campaign-33 simulations, the encoding comparison and the Quantinuum tests do not change any F / FD / ND count of this 2x2-hardware-scoped table; the two new milestone rows below record them. The marker below is from 2026-10-06: **Not re-scored on 2026-10-06.** The planner's table was written on 2026-10-02 and no file re-scores it; the new results (the replication, the 2x3 pilot) change no F / FD / ND count by the table's own scope (the 2x2 campaign), but two row notes are now incomplete and I have appended a marker to them: row A2 ("met on $k=1$ only") must also say that the $k=1$ result was one calibration's and did not repeat, and row 9.2 stays ND with one more fact (the only 2x3 job, K1, measured a null on IBM).

### 17.1 The 51 rows

| row | plan item | status | note on deviation or reason (planner report) |
|---|---|---|---|
| 0 | Role of $2\times2$: pipeline calibration only (decoder validity, yield vs depth, readout confusion, sector filter); not an accuracy test because any $10^3$-shot run satur | F |  |
| 1.1 | Hamiltonian eq. (1), Gauss's law eq. (2) verified: $[G_a(x), H] = 0$; two independent builders agree | F |  |
| 1.2 | Conserved quantities, sector split | F |  |
| 1.3 | Exact references (Table 1) | F |  |
| 1.4 | $\Delta t = \pi/W_B$ per sector | F |  |
| 1.5 | $B=1$ near-degenerate cluster (splitting 0.042 at 2x2); certification treats the cluster as a whole; gate tolerances tied to the splitting | F |  |
| 2.1-2.3 | Local singlet spaces, intertwiner label, basis orthonormality; Table 2 counts | F |  |
| 2.4 | Codewords: 12 qubits at 2x2 | F |  |
| 2.5 | Decoder: flag / link-consistency / sector checks; round trip; random acceptance $\approx 0.15\%$ at 2x3 | F |  |
| 3 | Dressed-site Hamiltonian builder, validated against the projector construction | F |  |
| 4.1 | State what is rigorous (variational bound) and what is heuristic (device support) | F |  |
| 4.2 | Multi-reference generation: Dirac sea + one-meson configurations ($B=0$), diquark on each even site ($B=1$) | F |  |
| 4.3 | Coarse single-step circuits $k=1..4$ (family b), gauge-invariant by construction; $\le 250$ CZ per step at 2x2 after routing | FD | the gate-count budget was not met; the criterion was amended to the one it stood for |
| 4.4 | Yield model $y = 0.82 f + (1-f)a$; shot rule eq. (5) ($S \ge 6.3/(0.82 f p)$, $2\times10^5$ shots per sector) | FD | model and shot rule both amended before the run (owner-approved 2026-09-30) |
| 5.1 | Decode every shot; $B$ = union of accepted configurations plus references; record yield and rejection reasons; build $H_B$ and diagonalize | F |  |
| 5.2 | $E_R \ge E_0$ for any $B$ | F |  |
| 5.3 | Residual $r_H$, Weinstein and Kato-Temple intervals, gap assumption stated | F |  |
| 5.4 | Support metrics: recall of the 99.9 % support, false positives, yield, $E_R - E_0$ | F | (but see row 6: at 2x2 recall 1.0 is reached by noise alone) |
| 6.1-6.2 | Size-matched classical controls at equal $\lvert B\rvert$: CIPSI, BFS, random, oracle, ML-alone, device-seeded CIPSI | FD | two of the six controls, chosen because at 2x2 the saturated sector makes CIPSI at  $\lvert B\rvert = 35$ of 38 trivially near-exact; the manual itself puts the control comparison on 2x3 |
| 6.3 | Primary endpoint P1: $E_R - E_0$ and recall vs $\lvert B\rvert$ for device vs CIPSI, with bootstrap bands, on **2x3** hardware data | ND | requires 2x3 hardware |
| 6.4 | Production mode: union of device support and CIPSI growth | ND | (moot at 2x2) |
| 7.1-7.2 | Gauge-invariant neural importance model $f_\theta(b;\lambda)$ (message-passing network), leakage-safe splits | FD | on the simulator (minimal model only); **not used on the 2x2 hardware data at all** |
| 7.3 | ML uses: (i) recovery of flagged strings by eq. (9), (ii) size-constrained extension, (iii) ML-alone proposal, (iv) transfer | ND | ML is not part of the 2x2 hardware result |
| 7.5 | Seven-protocol comparison table at equal $\lvert B\rvert$; ML credited only if it beats the baseline on 2x3 hardware data | ND |  |
| 8.1-8.2 | Noise proxy: clean with probability $f$, otherwise uniform or locally corrupted, readout flips; Table 4 | F | (simulator) |
| 8.3 | Transpiled-circuit Aer simulation with device noise models (CZ errors, $T_1$, $T_2$, readout) before hardware; gate S3 recall $\ge 0.9$ for the production set | FD | the manual's gate-only noise model was wrong by 15-50x on hardware until the idle term and $T_2^*$ were added; S3 for 2x3 is still open |
| 9.1 | 2x2 calibration run, one session: validate codewords, decoder, sector filter on real strings; yield vs CZ by repetition $r = 1,2,3$ ($N_{CZ} \approx 250, 500, 750$); per- | FD | no $r = 2,3$ depth ladder; the model comparison became a measurement-to-measurement comparison because the model (Aer at the echo $T_2$) was 5.1x off in the pilot (`validation/H0_kpilot.json` -> `data.aer_at.B0_ref06_k1.r=1` 0.2114 vs `data.decision.f_pool` 0.0413, **planner arithmetic** for the ratio) |
| 9.2 | 2x3 production, four sectors, $\le 500$ CZ, $2\times10^5$ shots per sector, two calibration windows | ND | **[2026-10-06 marker, not the planner's:** the only 2x3 hardware job, K1 (188.0 s on `ibm_kingston`), saw 0 reference hits in $2\times10^5$ shots; $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %)] |
| 9.3 | Optional 2x4 hardware only if H1-H2 pass | ND | (by design) |
| 10 | Gates E1-E3, S1 (done), S2, S3, H0, H1, H2, P1, M1 | FD |  |
| 10 (error budget) | Truncation ($j_{\max}$), subspace (certified interval), device (recall, false positives, yield, CIPSI comparison), shot (bootstrap over circuits), classical | FD |  |
| 10 (reporting) | Raw bitstrings, calibration snapshots, circuits and decoder released | FD | in the repository, not yet a public release bundle |
| 11 | Six-week timeline: 2x2 in week 3, 2x3 in week 4 | FD |  |
| A1 | Patch selected on the day by the exhaustive idle-aware rule R1' on the full device; re-frozen onto that patch | F |  |
| A2 | Budget criterion: $f = f_{\rm gates}\,e^{-S_{\rm idle}}$ on the scheduled circuit, mean $\ge 0.1$, worst $\ge 0.05$; $T_2$ convention named | FD | met on $k=1$ only; family-level unknown; owner waiver in force. **[2026-10-06 marker, not the planner's:** the $k=1$ result was one day's; on 2026-10-06 the same cell T3 gave $f_{\rm hit}=0.0732$ and $\hat f_{\rm ideal}=0.0656$, below the bar] |
| A3 | Circuit family: exact structured circuits, judged by ASAP-scheduled duration and idle budget | F |  |
| A4 | 2x3 device: must declare gate durations and $T_1/T_2$ | ND |  |
| A5 | Shot quota of Step 9.2 | ND |  |
| M4.4 | Yield model gains the near-clean term; eq. (5) takes the clean yield | F |  |
| D8' | Runtime DD off, twirling off | F |  |
| D1' | Patch by the idle-aware objective | F |  |
| D3'-f | Rule D3' fed with the measured clean fraction | F |  |
| D3''-H0 | For gate H0 only, size the $k=1$ circuits for the clean-fraction statistic | FD | struck |
| D5' | Canary becomes a measuring pilot (Ramsey at two waits, $T_1$, two depths, options off); go rule on the measured $f$ | F |  |
| C2' | Mixture clean-shot estimator reported beside the yield inversion | F |  |
| C3' | Reference string $\ge 3\sigma$ above garbage on every shortest-depth circuit; criterion 3 kept but labelled "not a device test" | F |  |
| H0P-Y' | Prediction bracket: analytic bound $\le$ scheduled simulation $\le$ unscheduled simulation | F |  |
| D9 | Submission keyed on calibration *content*; fingerprint recorded at prereg, submission, retrieval | F |  |
| prereg | Preregistration committed before submission | F |  |
| dry runs | Path check on the simulator before every submission | F |  |
| owner 2026-10-02 | Run the full 2x2 SKQD whether or not the signed bar is met; use the 600 s budget | F |  |

### 17.2 Status of the manual's gate table (Step 10) today

| manual gate | state today | evidence |
|---|---|---|
| E1 | **done** | `validation/E1.json` PASS 23/23 |
| E2 | **done** | `validation/E2.json` PASS 51/51 |
| E3 | **done** | `validation/E3.json` PASS 85/85 |
| S1 | **done** | `validation/S1.json` PASS 12/12 |
| S2 | **amended; the original budget FAILS** (2x2 618 routed vs 250; 2x3 5 477 vs 500); the amended criterion (amendment 01, signed 2026-09-23) reads $f$ on the scheduled circuit and the 2x2 leg FAILS it (idle-aware mean $6.71\times10^{-3}$) | `validation/S2.json`, `S2D.json`, `S2D_idle.json` |
| S3 | **partial, nearly answered in simulation**: throughput calibration PASS on the GPU (161x); campaign 33 redid the S3 path (`C4_FCELLS_B` s3_redo inside the band) and ran **F8, gate S3's model and family at $2\times10^5$ shots per sector**: every one of its 8 files has recall of $S_{999}$ 1.0 ($B=0$) or $\ge0.989$ ($B=1$), so the merged recall is $\ge1.0$ in both sectors [MINE bound]; the formal P15 is read at assembly | `validation/S3.json`, `C4_FCELLS_B.json`, `C4_F8_*.json`, `C4_PART_06..09.json` |
| H0 | **realised by measurement gates**: H0_canary (NO-GO), H0_diag, H0_kpilot (NO-GO), H0_ddtest (PASS), **H0_2x2 (PASS)**, H0_ddrep (PASS; replication did not confirm the H0_ddtest gain); "measured $f$ within 30 % of the model" was read measurement-to-measurement | Section 5 |
| H1 | **open** (no 2x3 hardware data); in simulation every $B=0$ class-4 file meets the width criterion with Kato-Temple widths $4.6\times10^{-4}$-$1.15\times10^{-3}$ and recall 1.0 | Section 7.8 |
| H2 | **open**; in simulation every $B=1$ file has Weinstein $r_H$ 0.036-0.089 $\le0.15$; $V(1)$, $V(2)$ need the static sectors (no plan) | Section 7.8 |
| P1 | **open** | -- |
| M1 | **open** (no ML on hardware data) | -- |

Of the manual's 11 Step-10 gates: 4 done (E1, E2, E3, S1), 3 partial or amended (S2, S3, H0), 4 open (H1, H2, P1, M1) **(sum of the table above)**.

### 17.3 Status per milestone

The project does not keep a separate milestone list; it tracks progress through the gate table. The twelve milestone names below are **my own grouping** of the project's work (descriptive names, not project labels), each tied to the project's own gates.

| milestone | what it means | status | evidence / remaining |
|---|---|---|---|
| physics core | Hamiltonian, basis, builder, references (Steps 1-3) | **done** | E1-E3 PASS |
| exact circuits | structured exact coarse-step circuits at 2x2, 2x3, 2x4 | **done** (verified; cost over the original budget) | S2 (cost FAIL), S2_2x4 PASS, L2, L5, Q0P_2x3 PASS |
| emulation and controls | support recall, controls, Table 3/4 reproduced | **done** | S1 PASS |
| noise model and device model | proxy replaced by scheduled Aer at measured $T_2^*$ | **done for 2x2**; 2x3 S3 recall answered in simulation by F8 (assembly pending); the IBM-type 2x3 model **blocked** (class 2) | H0_model PASS, S3 calibration PASS, F8 files, `C2_KCHK` |
| 2x2 hardware | calibration and full run | **done** (measurement gates); the DD mitigation did not replicate | H0_2x2 PASS; H0_ddrep PASS (negative); 14 jobs on IBM in all, 327 s of 600 s |
| clean-fraction statistics | estimator, near-clean term, $r_{nc}$, floor theorem | **done** | CF_traj PASS 7/7 |
| 2x3 plan check | D3'-R, convergence and coverage criteria CV0-CV5, Stage E/P plans | **done** (emulation; no device statement) | `CV_2x3_plan` PASS 37/37, `Q0P_2x3_plan` PASS 7/7; plan of record 665 605 HQC at $f=0.10$ |
| 2x3 hardware access | a device that can run 2x3 (Quantinuum) and an allocation | **not started** (draft email only); IBM Heron **measured NO-GO** (K1) | Section 14.2, 6.22 |
| 2x3 hardware results | H1, H2, P1 | **open** (the one 2x3 job is a null) | needs the 2x3 hardware access row above |
| neural step | graph network, recovery, seven-protocol comparison, M1 | **open** | only the ridge baseline exists |
| 2x4 | transfer and optional hardware | **simulator verified (structured circuit), native circuits built in two sources, state bar pending the GPU; hardware infeasible** | S2_2x4 PASS; `Q0P_2x4` FAIL by construction; `QN_2x4` PASS |
| release | raw bit strings, calibration records, circuits, decoder, methods note | **not started** (data are in the repository) | Section 14.4 |
| campaign 33 (2x3 simulation, four classes) | the owner's request of 2026-10-06 | **mostly done for classes 1, 3, 4; blocked for class 2**: classes 1 and 3 PASS; class 4: f-cells 45 of 77 cells (16 more requested), **10 full runs in 25 files** (F1, F4, F5, F7, F8 x both sectors), F2 requested, F3 and F6 deferred, assembly not run; class 2: `C2_CAL` withdrawn as a decision, `C2_KCHK` blocked, no cell run | Sections 7, 8 |
| encoding comparison | `prompts/34` | **done** (ENC_compare PASS 8/8): not meaningful | Section 6.25 |
| Quantinuum tests of all circuits | `prompts/35`, `35a`, `35b` | **done where possible without an account**: 2x2 T1, T2, T3, T4, T6 PASS; 2x3 T1, T2 PASS, T4/T6 information, T3 = campaign 33; 2x4 T1 FAIL by construction (GPU bar pending), T3 analytic PASS, T4/T6 infeasible; T5 prepared for all | Section 9 |

## 18. DATA APPENDIX for plotting

**How to use.** Every block below is a fenced ```csv block that can be copied into pandas (`pd.read_csv(io.StringIO(text))`), R or a spreadsheet; fields that contain commas are double-quoted. Each block has a title, its source file(s) and key(s), and the units of its columns. Empty cells mean "not available in the source". **Provenance (updated 2026-10-15):** blocks (a), (a2), (ab), (ad) are regenerated, and blocks (ae)-(ap) are new; all of them were written by short scripts that read `validation/*.json`, `data/campaign33/*`, `data/quantinuum/circuits_2x4/*.manifest.json`, `reports/ci-*.out`, `ci/status/*.json`, `ci/parts/*.json` and `git log` directly, so no number in them was typed by hand (the exceptions are labelled `MINE` or `PLAN` in a `kind` column or in the block's note). Block (x) is carried with its executor-reported rows replaced by the committed gate values and with new rows appended. Blocks (b)-(w2), (y)-(aa3) and (ac) are carried unchanged from the 2026-10-13 report (they describe results that did not change).

**The block list:** (a) gate timeline (87 rows); (a2) Perlmutter CI jobs (43 jobs, with submit and harvest times); (b) clean-fraction history per hardware run; (b2) corrected by $r_{nc}$; (b3) $\hat f_{\rm ideal}$ as computed by the gates; (c) H0_ddtest cells; (d) H0_2x2 energies (d2 baselines, d3 per-state counts); (e) $B_{\rm all}$ / $B_{\rm sig}$ growth; (f) device survey (f2 2x2); (g) 2x3 shots and HQC versus $f$; (h) CF_traj arms; (i) cumulative QPU seconds (unchanged: 327 s after 14 jobs); (j) gate counts and device requirements; (k) exact references (k2 derived); (l) the 51 plan rows; (m) the 2x2 shot plan; (n) S2D_levers (n2 kingston pilot); (o) H0_ddrep cells; (p) pulse trains; (q) CV_2x3_plan cells (q2 the $B=1$ ladder); (r) oracle widths; (s) K1 pilot; (t) K0; (u) calibration statistics; (v) f-cells (45); (v2) scenario parameters; (w) C2_CAL arms (w2 marginals); (x) **clean-fraction landscape**; (y) C4_CF arms; (z) F5_B0 shot curve (z2 CV values, z3 per circuit); (aa) ENC_compare (aa2, aa3); (ab) Quantinuum native numbers per lattice (regenerated from gates); (ac) class-4 run plan and sizing; (ad) the campaign tokens and their state (regenerated); **new:** (ae) **all 25 class-4 run files**; (af) shot curves of the three single-job runs; (ag) **per-run pooled clean fraction and merged-run bounds [MINE]**; (ah) per-circuit reference-hit fractions of all 25 files; (ai) class-2 per-bit marginals ($C2\_CAL$, $C2\_KCHK$, device); (aj) **class-2 mean Hamming weight, every arm**; (ak) `QN_2x2` f-cells (308); (al) `QN_2x2` plan-of-record runs; (am) the 79 native 2x4 circuits; (an) `QN_2x4` analytic summary; (ao) the 28 native 2x2 circuits; (ap) Perlmutter request waves.

**Caution for the plotting assistant.** (1) The clean-fraction statistics are *different estimators* (yield-inverted, reference-string `f_hit`, mixture, `f_hat_ideal`, analytic `f0`); do not draw them as one series without saying so. (2) All device-prediction numbers (blocks (f), (g), (x) `kind` = model / ESTIMATE / vendor-published) are **models**; the only measured clean fractions are in blocks (b), (b3), (c), (o), (s) and the `measured` rows of (x). (3) Intervals are 95 % unless a column says otherwise. (4) Block (g) carries the re-sized plan of record beside older rules; the older rows are alternatives. (5) Simulation blocks (v), (w), (y), (z), (ae)-(al) are properties of the *model*; do not mix them with hardware on one axis without a marker. (6) In (ae) and (ah) a row of a **split run** describes that part's shots only; use (ag) for per-run values, and remember that (ag)'s clean fractions are my pooling and its energy/recall columns are bounds, not the assembly's values. (7) In (ae) the bootstrap columns lie above the point value in every row (Section 7.8); plot them as a pessimistic spread, not as a confidence interval.

#### (a) Gate timeline (regenerated 2026-10-15)

**Source:** every `validation/*.json` with a criteria list (`environment.timestamp`, `status`, `criteria[*].passed`, `runtime_s`, `environment.git_commit`), excluding the `ci_*` wrappers and the `C33_*` content copies; 87 rows (54 on 2026-10-13), sorted by the UTC conversion of the recorded time (MDT = UTC-6, PDT = UTC-7; my conversion).

**Columns and units:** `date`, `time`, `tz` as recorded; `file` JSON file stem; `gate`; `status` PASS or FAIL; `criteria_passed`, `criteria_total` counts; `runtime_s` seconds (0 = assembled from fragments, see the gate); `commit` short git hash (`n/a` on the CI); `utc` the same instant in UTC.

```csv
date,time,tz,file,gate,status,criteria_passed,criteria_total,runtime_s,commit,utc
2026-09-14,21:37:07,UTC,CS,CS,PASS,4,4,4,3c32216,2026-09-14T21:37:07Z
2026-09-14,16:43:44,MDT,E1,E1,PASS,23,23,427,57b3bff,2026-09-14T22:43:44Z
2026-09-14,16:44:00,MDT,E2,E2,PASS,51,51,15,57b3bff,2026-09-14T22:44:00Z
2026-09-14,16:44:36,MDT,E3,E3,PASS,85,85,36,57b3bff,2026-09-14T22:44:36Z
2026-09-14,16:48:20,MDT,S1,S1,PASS,12,12,223,57b3bff,2026-09-14T22:48:20Z
2026-09-14,18:00:36,MDT,L4_p2_3e-3,L4,FAIL,2,4,1376,30684f2,2026-09-15T00:00:36Z
2026-09-14,18:24:06,MDT,L4_p2_1e-3,L4,FAIL,2,4,1012,30684f2,2026-09-15T00:24:06Z
2026-09-15,15:04:26,MDT,L3,L3,FAIL,0,2,14,5d60461,2026-09-15T21:04:26Z
2026-09-15,15:12:59,MDT,S2,S2,FAIL,3,5,436,5d60461,2026-09-15T21:12:59Z
2026-09-15,20:18:31,MDT,S2_fixed,S2_fixed,FAIL,5,9,301,2fbcf29,2026-09-16T02:18:31Z
2026-09-15,20:19:58,MDT,L5,L5,PASS,6,6,3,0420211,2026-09-16T02:19:58Z
2026-09-15,20:20:11,MDT,L2,L2,PASS,4,4,8,0420211,2026-09-16T02:20:11Z
2026-09-16,07:02:12,MDT,S2D,S2D,FAIL,6,8,213,89102d2,2026-09-16T13:02:12Z
2026-09-16,11:46:01,MDT,S3_smoke,S3_smoke,FAIL,1,2,295,1223e92,2026-09-16T17:46:01Z
2026-09-16,12:28:26,MDT,L4_fez,L4_fez,PASS,4,4,450,3722018,2026-09-16T18:28:26Z
2026-09-16,13:15:46,MDT,H0P,H0P,PASS,16,16,1179,2392fb3,2026-09-16T19:15:46Z
2026-09-21,17:57:49,MDT,H0P_rehearsal,H0P_rehearsal,PASS,18,18,175,1e5c03b,2026-09-21T23:57:49Z
2026-09-22,01:22:38,PDT,L4,L4,PASS,4,4,677,n/a,2026-09-22T08:22:38Z
2026-09-22,11:46:55,MDT,H0P_ibm_fez,H0P_ibm_fez,PASS,18,18,319,1e6d7d3,2026-09-22T17:46:55Z
2026-09-22,14:16:46,MDT,H0_diag_dryrun,H0_diag_dryrun,FAIL,6,7,1,9cfe3ec,2026-09-22T20:16:46Z
2026-09-22,14:46:44,MDT,H0_diag,H0_diag,FAIL,6,8,1,4d1e8f6,2026-09-22T20:46:44Z
2026-09-22,16:36:34,MDT,S2D_idle,S2D_idle,FAIL,6,15,406,2c6edb6,2026-09-22T22:36:34Z
2026-09-22,18:01:22,PDT,S3,S3,PASS,4,4,248,n/a,2026-09-23T01:01:22Z
2026-09-30,15:28:44,MDT,H0P_repro,H0P_repro,PASS,15,15,1741,6180c6a,2026-09-30T21:28:44Z
2026-09-30,15:31:18,MDT,H0_model,H0_model,PASS,5,5,2,6180c6a,2026-09-30T21:31:18Z
2026-09-30,15:41:37,MDT,H0_dryrun,H0_dryrun,PASS,9,9,10,6180c6a,2026-09-30T21:41:37Z
2026-09-30,15:41:49,MDT,H0_canary,H0_canary,FAIL,3,6,11,6180c6a,2026-09-30T21:41:49Z
2026-10-01,09:15:29,PDT,S2_2x4,S2_2x4,PASS,12,12,0,n/a,2026-10-01T16:15:29Z
2026-10-02,11:13:55,MDT,S2D_levers,S2D_levers,PASS,9,9,489,782580c,2026-10-02T17:13:55Z
2026-10-02,12:04:30,MDT,H0_kpilot_dryrun,H0_kpilot_dryrun,PASS,9,9,49,761369f,2026-10-02T18:04:30Z
2026-10-02,12:31:53,MDT,H0_kpilot,H0_kpilot,FAIL,8,9,450,fc3a5a2,2026-10-02T18:31:53Z
2026-10-02,14:10:22,MDT,H0_ddtest_dryrun,H0_ddtest_dryrun,PASS,8,8,15,aa4da1e,2026-10-02T20:10:22Z
2026-10-02,14:37:48,MDT,H0_ddtest,H0_ddtest,PASS,8,8,601,d4b3855,2026-10-02T20:37:48Z
2026-10-02,15:04:52,MDT,H0_2x2_dryrun,H0_2x2_dryrun,PASS,8,8,17,4e979a0,2026-10-02T21:04:52Z
2026-10-02,16:04:51,MDT,H0_2x2,H0_2x2,PASS,8,8,444,da715fc,2026-10-02T22:04:51Z
2026-10-02,21:36:57,MDT,Q0P_2x3,Q0P_2x3,PASS,7,7,926,8072b8d,2026-10-03T03:36:57Z
2026-10-05,13:47:33,MDT,CF_traj,CF_traj,PASS,7,7,1201,a8ebbaa,2026-10-05T19:47:33Z
2026-10-05,17:28:05,MDT,CF_estimator_2x2_info,CF_estimator_2x2_info,PASS,2,2,4,3d5f05a,2026-10-05T23:28:05Z
2026-10-05,17:40:48,MDT,CV_2x3_plan,CV_2x3_plan,PASS,37,37,679,3d5f05a,2026-10-05T23:40:48Z
2026-10-05,17:41:27,MDT,CV_2x2_info,CV_2x2_info,PASS,2,2,14,3d5f05a,2026-10-05T23:41:27Z
2026-10-05,17:56:24,MDT,Q0P_2x3_plan,Q0P_2x3_plan,PASS,7,7,781,3d5f05a,2026-10-05T23:56:24Z
2026-10-06,00:59:27,MDT,H0_ddrep_dryrun,H0_ddrep_dryrun,PASS,8,8,14,cd9ce12,2026-10-06T06:59:27Z
2026-10-06,01:11:17,MDT,H0_ddrep,H0_ddrep,PASS,8,8,422,36c48a2,2026-10-06T07:11:17Z
2026-10-06,01:38:10,MDT,K0_2x3_2x4,K0_2x3_2x4,PASS,6,6,943,880961d,2026-10-06T07:38:10Z
2026-10-06,02:20:48,MDT,K1_2x3_fpilot_dryrun,K1_2x3_fpilot_dryrun,PASS,9,9,430,f8df126,2026-10-06T08:20:48Z
2026-10-06,02:33:45,MDT,K1_2x3_fpilot,K1_2x3_fpilot,PASS,8,8,422,504d452,2026-10-06T08:33:45Z
2026-10-08,00:11:16,MDT,ENC_compare,ENC_compare,PASS,8,8,2787,fa24ec4,2026-10-08T06:11:16Z
2026-10-09,12:03:39,PDT,C3_AER,C3_AER,PASS,10,10,59,n/a,2026-10-09T19:03:39Z
2026-10-09,12:04:10,PDT,C1_IDEAL,C1_IDEAL,PASS,10,10,89,n/a,2026-10-09T19:04:10Z
2026-10-09,13:14:53,PDT,C4_FCELLS_A,C4_FCELLS_A,FAIL,7,8,2320,n/a,2026-10-09T20:14:53Z
2026-10-13,08:08:10,PDT,C4_FCELLS_B,C4_FCELLS_B,PASS,8,8,1866,n/a,2026-10-13T15:08:10Z
2026-10-13,08:17:05,PDT,C4_CF,C4_CF,FAIL,7,8,2401,n/a,2026-10-13T15:17:05Z
2026-10-13,08:19:40,PDT,C2_CAL,C2_CAL,PASS,12,12,1816,n/a,2026-10-13T15:19:40Z
2026-10-13,08:28:39,PDT,C4_F5_B0,C4_F5_B0,PASS,8,8,2223,n/a,2026-10-13T15:28:39Z
2026-10-13,09:49:03,PDT,C4_F7_B0,C4_F7_B0,PASS,8,8,650,n/a,2026-10-13T16:49:03Z
2026-10-13,10:08:00,PDT,C4_F1_B0,C4_F1_B0,PASS,8,8,1788,n/a,2026-10-13T17:08:00Z
2026-10-13,10:10:31,PDT,C4_PART_01,C4_PART_01,PASS,8,8,1360,n/a,2026-10-13T17:10:31Z
2026-10-13,10:10:44,PDT,C4_F5_B1,C4_F5_B1,PASS,7,7,1373,n/a,2026-10-13T17:10:44Z
2026-10-13,11:21:08,PDT,C4_F4_B0a,C4_F4_B0a,PASS,7,7,1395,n/a,2026-10-13T18:21:08Z
2026-10-13,11:43:28,PDT,C4_PART_02,C4_PART_02,FAIL,7,8,1257,n/a,2026-10-13T18:43:28Z
2026-10-13,11:45:02,PDT,C4_F4_B1a,C4_F4_B1a,PASS,7,7,1351,n/a,2026-10-13T18:45:02Z
2026-10-13,11:55:48,PDT,C4_PART_03,C4_PART_03,PASS,8,8,1345,n/a,2026-10-13T18:55:48Z
2026-10-13,13:13:49,MDT,QEMU_2x2,QEMU_2x2,PASS,3,3,0,e3997bc,2026-10-13T19:13:49Z
2026-10-13,12:49:20,PDT,C4_PART_04,C4_PART_04,FAIL,7,8,1261,n/a,2026-10-13T19:49:20Z
2026-10-13,12:51:28,PDT,C4_F4_B0b,C4_F4_B0b,PASS,7,7,1388,n/a,2026-10-13T19:51:28Z
2026-10-13,13:46:50,PDT,C4_F4_B1b,C4_F4_B1b,PASS,7,7,1360,n/a,2026-10-13T20:46:50Z
2026-10-13,13:58:39,PDT,C4_PART_05,C4_PART_05,PASS,8,8,1346,n/a,2026-10-13T20:58:39Z
2026-10-13,15:01:52,MDT,Q0P_2x2,Q0P_2x2,PASS,5,5,68,0d7f4c5,2026-10-13T21:01:52Z
2026-10-13,15:10:37,MDT,QH_2x2,QH_2x2,PASS,4,4,0,c272e2a,2026-10-13T21:10:37Z
2026-10-13,16:20:04,MDT,QH_2x3,QH_2x3,PASS,4,4,0,0265bf8,2026-10-13T22:20:04Z
2026-10-13,16:31:09,MDT,QEMU_2x3_laptop_smoke,QEMU_2x3_laptop_smoke,PASS,2,2,0,37ce8ad,2026-10-13T22:31:09Z
2026-10-13,16:04:50,PDT,C4_F8_B0a,C4_F8_B0a,PASS,7,7,1074,n/a,2026-10-13T23:04:50Z
2026-10-13,16:10:48,PDT,C4_PART_06,C4_PART_06,PASS,8,8,1103,n/a,2026-10-13T23:10:48Z
2026-10-13,16:36:53,PDT,C4_F8_B1a,C4_F8_B1a,PASS,7,7,978,n/a,2026-10-13T23:36:53Z
2026-10-13,16:37:05,PDT,C4_PART_07,C4_PART_07,PASS,8,8,990,n/a,2026-10-13T23:37:05Z
2026-10-13,19:42:46,MDT,QN_2x2,QN_2x2,PASS,5,5,18924,1691220,2026-10-14T01:42:46Z
2026-10-13,23:59:18,MDT,Q0P_2x4,Q0P_2x4,FAIL,4,6,6228,faf8a10,2026-10-14T05:59:18Z
2026-10-14,00:30:46,MDT,QN_2x4,QN_2x4,PASS,2,2,0,faf8a10,2026-10-14T06:30:46Z
2026-10-14,08:30:18,PDT,C4_F1_B1,C4_F1_B1,PASS,7,7,857,n/a,2026-10-14T15:30:18Z
2026-10-14,08:51:40,PDT,C4_PART_10,C4_PART_10,PASS,8,8,844,n/a,2026-10-14T15:51:40Z
2026-10-14,08:54:54,PDT,C4_F7_B1,C4_F7_B1,PASS,7,7,692,n/a,2026-10-14T15:54:54Z
2026-10-14,09:06:28,PDT,C4_PART_11,C4_PART_11,PASS,8,8,676,n/a,2026-10-14T16:06:28Z
2026-10-14,10:03:30,PDT,C2_KCHK,C2_KCHK,FAIL,7,10,2312,n/a,2026-10-14T17:03:30Z
2026-10-14,10:12:20,PDT,C4_F8_B0b,C4_F8_B0b,PASS,7,7,1029,n/a,2026-10-14T17:12:20Z
2026-10-14,10:24:07,PDT,C4_PART_08,C4_PART_08,PASS,8,8,1050,n/a,2026-10-14T17:24:07Z
2026-10-14,10:41:12,PDT,C4_PART_09,C4_PART_09,PASS,8,8,1008,n/a,2026-10-14T17:41:12Z
2026-10-14,10:41:24,PDT,C4_F8_B1b,C4_F8_B1b,PASS,7,7,1004,n/a,2026-10-14T17:41:24Z
```

#### (a2) Perlmutter CI jobs (A100, 1 GPU each), with gate seconds and queue times (regenerated 2026-10-15)

**Source:** `reports/ci-<jobid>.out` (line `gate X: status S, exit code N, T s`); the CI robot's `ci: submitted job ...` and `ci: results job ...` commits (`git log`, author time converted to UTC by me); `ci/status/<TOKEN>.json -> request`. The first 18 rows are carried from the 2026-10-13 report (their notes column as there).

**Columns and units:** `job_id` Slurm job id; `gate` token; `gate_status` as printed by the driver (UNKNOWN = died before writing a JSON); `gate_seconds` s; `submitted_utc`, `harvested_utc` the robot's commit times (minute resolution; empty before the concurrent poller); `request` the request identity `<path>@<commit>`; `note`.

```csv
job_id,gate,gate_status,gate_seconds,submitted_utc,harvested_utc,request,note
58717267,smoke,PASS,,2026-09-21T23:38Z,2026-09-22T00:07Z,,
58737320,L4,FAIL,607,2026-09-22T06:07Z,2026-09-22T07:07Z,,
58741899,L4,PASS,684,2026-09-22T08:07Z,2026-09-22T09:07Z,,
58771538,S3,PASS,254,2026-09-22T23:07Z,2026-09-23T01:07Z,,
59162991,S2_2x4,PASS,97,2026-10-01T15:51Z,2026-10-01T16:41Z,,
59491455,C1_IDEAL,UNKNOWN,21,2026-10-07T16:06Z,2026-10-07T17:07Z,,missing threadpoolctl
59491462,C3_AER,UNKNOWN,15,2026-10-07T16:06Z,2026-10-07T17:07Z,,missing threadpoolctl
59491475,C2_CAL,FAIL,783,2026-10-07T16:06Z,2026-10-07T18:07Z,,run 1
59491480,C4_FCELLS_A,UNKNOWN,16,2026-10-07T16:06Z,2026-10-07T18:07Z,,missing threadpoolctl
59552188,smoke,PASS,,2026-10-08T16:07Z,2026-10-08T17:07Z,ci/requests/005-smoke.txt@388ed1c3ad67921ce15771e9d6dad7c3117c8e46,
59570217,C1_IDEAL,PASS,103,2026-10-08T21:07Z,2026-10-09T19:28Z,ci/requests/006-C1_IDEAL.txt@3a768f9eca4cf1afa4d86b1297634864f37b0074,
59570221,C3_AER,PASS,72,2026-10-08T21:07Z,2026-10-09T19:28Z,ci/requests/007-C3_AER.txt@3a768f9eca4cf1afa4d86b1297634864f37b0074,
59570315,C4_FCELLS_A,FAIL,2337,2026-10-08T21:07Z,2026-10-09T21:07Z,ci/requests/008-C4_FCELLS_A.txt@3a768f9eca4cf1afa4d86b1297634864f37b0074,S6 only
59570318,C2_CAL,FAIL,250,2026-10-08T21:07Z,2026-10-09T20:07Z,,run 2; zero-shot arms
59736863,C4_FCELLS_B,PASS,1883,2026-10-13T14:26Z,2026-10-13T15:32Z,ci/requests/010-C4_FCELLS_B.txt@20b38879ea5de994f6e4f05d773c112aca1234fd,
59736866,C4_CF,FAIL,2417,2026-10-13T14:26Z,2026-10-13T15:32Z,ci/requests/011-C4_CF.txt@20b38879ea5de994f6e4f05d773c112aca1234fd,S6 only
59736871,C2_CAL,PASS,1827,2026-10-13T14:26Z,2026-10-13T15:32Z,ci/requests/012-C2_CAL.txt@20b38879ea5de994f6e4f05d773c112aca1234fd,run 3
59736879,C4_F5_B0,PASS,2234,2026-10-13T14:26Z,2026-10-13T15:32Z,ci/requests/013-C4_F5_B0.txt@20b38879ea5de994f6e4f05d773c112aca1234fd,
59739276,C4_F1_B0,PASS,1811,2026-10-13T15:32Z,2026-10-13T18:07Z,ci/requests/014-C4_F1_B0.txt@23d18e2422e388afa377b2865a0920cba6f89ea5,
59739278,C4_F7_B0,PASS,669,2026-10-13T15:32Z,2026-10-13T17:07Z,ci/requests/015-C4_F7_B0.txt@23d18e2422e388afa377b2865a0920cba6f89ea5,
59739280,C4_F5_B1,PASS,1392,2026-10-13T15:32Z,2026-10-13T18:07Z,ci/requests/016-C4_F5_B1.txt@23d18e2422e388afa377b2865a0920cba6f89ea5,
59739282,C4_PART_01,PASS,1381,2026-10-13T15:32Z,2026-10-13T18:07Z,ci/requests/017-C4_PART_01.txt@23d18e2422e388afa377b2865a0920cba6f89ea5,
59742843,C4_F4_B0a,PASS,1412,2026-10-13T17:07Z,2026-10-13T19:07Z,ci/requests/018-C4_F4_B0a.txt@ebc60debc75a61804661b013d701df49f4442a2a,
59745007,C4_PART_02,FAIL,1270,2026-10-13T18:07Z,2026-10-13T19:07Z,ci/requests/019-C4_PART_02.txt@ebc60debc75a61804661b013d701df49f4442a2a,S6 only
59745015,C4_F4_B1a,PASS,1363,2026-10-13T18:07Z,2026-10-13T19:07Z,ci/requests/020-C4_F4_B1a.txt@ebc60debc75a61804661b013d701df49f4442a2a,
59745024,C4_PART_03,PASS,1354,2026-10-13T18:07Z,2026-10-13T19:07Z,ci/requests/021-C4_PART_03.txt@ebc60debc75a61804661b013d701df49f4442a2a,
59747539,C4_F4_B0b,PASS,1408,2026-10-13T19:07Z,2026-10-13T20:07Z,ci/requests/022-C4_F4_B0b.txt@d7dd0c462542c4ca0bce883535ffc82c29d46a44,
59747548,C4_PART_04,FAIL,1276,2026-10-13T19:07Z,2026-10-13T20:07Z,ci/requests/023-C4_PART_04.txt@d7dd0c462542c4ca0bce883535ffc82c29d46a44,S6 only
59747551,C4_F4_B1b,PASS,1378,2026-10-13T19:08Z,2026-10-13T21:07Z,ci/requests/024-C4_F4_B1b.txt@d7dd0c462542c4ca0bce883535ffc82c29d46a44,
59747553,C4_PART_05,PASS,1358,2026-10-13T19:08Z,2026-10-13T21:07Z,ci/requests/025-C4_PART_05.txt@d7dd0c462542c4ca0bce883535ffc82c29d46a44,
59749780,C4_F8_B0a,PASS,1089,2026-10-13T20:07Z,2026-10-13T23:07Z,ci/requests/026-C4_F8_B0a.txt@f940a180aa4c61ff4ecea409367bb0441dbb88f3,
59749784,C4_PART_06,PASS,1113,2026-10-13T20:07Z,2026-10-14T00:07Z,ci/requests/027-C4_PART_06.txt@f940a180aa4c61ff4ecea409367bb0441dbb88f3,
59752618,C4_F8_B1a,PASS,987,2026-10-13T21:07Z,2026-10-14T00:07Z,ci/requests/028-C4_F8_B1a.txt@f940a180aa4c61ff4ecea409367bb0441dbb88f3,
59752623,C4_PART_07,PASS,999,2026-10-13T21:07Z,2026-10-14T00:07Z,ci/requests/029-C4_PART_07.txt@f940a180aa4c61ff4ecea409367bb0441dbb88f3,
59779331,C4_F1_B1,PASS,878,2026-10-14T15:07Z,2026-10-14T16:07Z,ci/requests/030-C4_F1_B1.txt@6c3e684e76b6f15ecb15eef185d10f2f3148de2b,
59779334,C4_PART_10,PASS,856,2026-10-14T15:07Z,2026-10-14T16:07Z,ci/requests/031-C4_PART_10.txt@6c3e684e76b6f15ecb15eef185d10f2f3148de2b,
59779337,C4_F7_B1,PASS,707,2026-10-14T15:07Z,2026-10-14T16:07Z,ci/requests/032-C4_F7_B1.txt@6c3e684e76b6f15ecb15eef185d10f2f3148de2b,
59779338,C4_PART_11,PASS,689,2026-10-14T15:07Z,2026-10-14T16:07Z,ci/requests/033-C4_PART_11.txt@6c3e684e76b6f15ecb15eef185d10f2f3148de2b,
59780907,C2_KCHK,FAIL,2352,2026-10-14T16:07Z,2026-10-14T17:07Z,ci/requests/034-C2_KCHK.txt@f4c71e8d4870d76a16c0135098b7dfad75af6567,CPU arms 0 shots; decision blocked
59780912,C4_F8_B0b,PASS,1073,2026-10-14T16:07Z,2026-10-14T18:07Z,ci/requests/035-C4_F8_B0b.txt@f4c71e8d4870d76a16c0135098b7dfad75af6567,
59780915,C4_PART_08,PASS,1089,2026-10-14T16:08Z,2026-10-14T18:07Z,ci/requests/036-C4_PART_08.txt@f4c71e8d4870d76a16c0135098b7dfad75af6567,
59780919,C4_F8_B1b,PASS,1029,2026-10-14T16:08Z,2026-10-14T18:07Z,ci/requests/037-C4_F8_B1b.txt@f4c71e8d4870d76a16c0135098b7dfad75af6567,
59782656,C4_PART_09,PASS,1043,2026-10-14T17:07Z,2026-10-14T18:07Z,ci/requests/038-C4_PART_09.txt@f4c71e8d4870d76a16c0135098b7dfad75af6567,
```

#### (b) Clean-fraction history per hardware run

**Source:** `validation/H0_canary.json`, `H0_model.json`, `H0_kpilot.json`, `H0_ddtest.json`, `H0_2x2.json`, **`H0_ddrep.json` and `K1_2x3_fpilot.json` (new rows at the end, 2026-10-06)** (keys in the last column). The H0_diag runs J1-J4 and the canary enter only through the pooled fez row (6 reference hits in 8 267 shots).

**Columns and units:** `f` clean-fraction statistic (dimensionless probability per shot); `lo`,`hi` interval ends at the stated `level`; `shots` shots the statistic uses (for pooled rows the sum over circuits; for H0_2x2 pooled the 7 k=1 circuits x 267); `stat` names the estimator. Different statistics are NOT interchangeable: the yield-inverted value overstates the clean fraction (15x on fez); the reference-string value `f_hit` estimates the ideal-sample fraction (ratio r_nc = 1.115). The K1 rows (2x3, `ibm_kingston`) have a *negative* `f` because the statistic subtracts the garbage expectation (0.0954 per circuit) from zero observed hits; read the interval's upper end. The H0_ddrep T0 / T1 / T3 rows are the same circuits as the H0_ddtest rows of 2026-10-02 above (compare T0: 0.0400 vs 0.0818).

```csv
run,date,device,circuit,statistic,f,lo,hi,interval_level,shots,note,source_key
H0_canary,2026-09-22,ibm_fez,B0_ref06_k1_rep1 (663 CZ),yield-inverted (y=0.82f+(1-f)a),0.0255145,,,,267,"DD on, twirling on; 8 accepted; NOT a clean-shot measurement",validation/H0_canary.json data.f_comparison
H0_canary,2026-09-22,ibm_fez,B0_ref06_k1_rep1 (663 CZ),prediction: gate-only model,0.219522,,,,267,prediction,validation/H0_canary.json data.f_comparison
H0_model (5 fez pubs),2026-09-22,ibm_fez,B0_ref06_k1 pooled over canary + J1-J4,reference-string f_clean (readout factor 0.82),0.000664981,0.000267503,0.0012635,68% Garwood,8267,"6 hits vs 2.018 from garbage; interval is 68%, not 95%",validation/H0_model.json data.C2_pooled_device_clean_count.pooled_reference_test
H0_kpilot,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.041293,0.0361148,0.0469982,95%,8000,"DD off, twirling off; NO-GO",validation/H0_kpilot.json data.decision
H0_kpilot,2026-10-02,ibm_kingston,B0_ref06_k1,reference-string f_hit,0.0403927,0.0332439,0.0486082,95%,4000,,validation/H0_kpilot.json data.decision.f_by_circuit
H0_kpilot,2026-10-02,ibm_kingston,B1_ref07_k1,reference-string f_hit,0.0421874,0.034898,0.0505359,95%,4000,,validation/H0_kpilot.json data.decision.f_by_circuit
H0_kpilot,2026-10-02,ibm_kingston,B0_ref06_k4,reference-string f_hit,0.0384758,0.0211611,0.0635501,95%,4000,,validation/H0_kpilot.json data.decision.f_by_circuit
H0_ddtest T0,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.0400315,0.035844,0.0445691,95%,12000,cell T0,validation/H0_ddtest.json data.decision.cells.T0
H0_ddtest T1,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.000466785,-1.96655e-05,0.00133721,95%,12000,cell T1,validation/H0_ddtest.json data.decision.cells.T1
H0_ddtest T2,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.111821,0.104764,0.119227,95%,12000,cell T2,validation/H0_ddtest.json data.decision.cells.T2
H0_ddtest T3,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.112853,0.105763,0.120292,95%,12000,cell T3,validation/H0_ddtest.json data.decision.cells.T3
H0_2x2,2026-10-02,ibm_kingston,pooled 7 k=1 circuits,reference-string f_hit,0.127053,0.108428,0.147942,95%,1869,DD cell T3; 173 hits vs 0.456 from garbage,validation/H0_2x2.json data.clean_fraction.pooled
H0_2x2,2026-10-02,ibm_kingston,B0_ref06_k1,reference-string f_hit,0.13411,0.0866992,0.198013,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref06_k1,mixture estimator,0.127551,,,,267,"68 percent interval in source: [0.11235706313885048, 0.1414890748184295]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref17_k1,reference-string f_hit,0.128636,0.0823605,0.191382,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref17_k1,mixture estimator,0.138705,,,,267,"68 percent interval in source: [0.12550506985006343, 0.14913202094957254]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref21_k1,reference-string f_hit,0.138953,0.0906493,0.203693,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref21_k1,mixture estimator,0.148416,,,,267,"68 percent interval in source: [0.13767737943758027, 0.1561715400780899]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref30_k1,reference-string f_hit,0.138953,0.0906493,0.203693,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref30_k1,mixture estimator,0.128372,,,,267,"68 percent interval in source: [0.1178297362522436, 0.13645570114493744]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref43_k1,reference-string f_hit,0.108,0.0660441,0.166513,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref43_k1,mixture estimator,0.127889,,,,267,"68 percent interval in source: [0.12391147402301594, 0.1278889193386316]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B1_ref07_k1,reference-string f_hit,0.138375,0.090272,0.202845,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B1_ref07_k1,mixture estimator,0.132496,,,,267,"68 percent interval in source: [0.12253408105946641, 0.13970340414288612]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B1_ref14_k1,reference-string f_hit,0.102413,0.0617701,0.15957,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B1_ref14_k1,mixture estimator,0.101259,,,,267,"68 percent interval in source: [0.09038906250384834, 0.10963820058819713]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_ddrep T0,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0817751,0.0757532,0.0881453,95%,12000,cell T0; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.T0
H0_ddrep T1,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0528757,0.0480506,0.05805,95%,12000,cell T1; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.T1
H0_ddrep T3,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0731741,0.0674826,0.0792142,95%,12000,cell T3; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.T3
H0_ddrep M1,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0644584,0.059122,0.0701436,95%,12000,cell M1; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.M1
H0_ddrep M2,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0659492,0.0605505,0.0716968,95%,12000,cell M2; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.M2
H0_ddrep M3,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0726007,0.0669319,0.0786181,95%,12000,cell M3; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.M3
H0_ddrep M4,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0940459,0.0875813,0.100858,95%,12000,cell M4; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.M4
H0_ddrep T0,2026-10-06,ibm_kingston,B0_ref06_k1,reference-string f_hit,0.0871053,0.0783659,0.0965467,95%,6000,,validation/H0_ddrep.json data.cells.T0.f_by_circuit
H0_ddrep T0,2026-10-06,ibm_kingston,B1_ref07_k1,reference-string f_hit,0.0764796,0.0683291,0.0853283,95%,6000,,validation/H0_ddrep.json data.cells.T0.f_by_circuit
K1_2x3_fpilot,2026-10-06,ibm_kingston,"B0_ref117_k1 (2x3, 5659 CZ)",reference-string f_hit,-1.25277e-06,-1.25277e-06,4.72052e-05,95%,100000,0 reference hits vs 0.0954 from garbage; negative = zero hits minus the garbage expectation; read the upper end,validation/K1_2x3_fpilot.json data.circuits.B0_ref117_k1
K1_2x3_fpilot,2026-10-06,ibm_kingston,"B1_ref29_k1 (2x3, 5659 CZ)",reference-string f_hit,-1.25284e-06,-1.25284e-06,4.72077e-05,95%,100000,0 reference hits vs 0.0954 from garbage; negative = zero hits minus the garbage expectation; read the upper end,validation/K1_2x3_fpilot.json data.circuits.B1_ref29_k1
K1_2x3_fpilot,2026-10-06,ibm_kingston,pooled 2 circuits (2x3),reference-string f_hit,-1.2528e-06,-1.2528e-06,2.29768e-05,95%,200000,0 reference hits vs 0.190735 from garbage; NO-GO firm,validation/K1_2x3_fpilot.json data.pooled
K1_2x3_fpilot,2026-10-06,ibm_kingston,B0_ref117_k1,prediction: gate-only on the routed layout (no idle),1.67113e-05,,,,100000,prediction (preregistered),validation/K1_2x3_fpilot.json data.prediction_prereg.B0_ref117_k1.f_bracket
```

#### (b2) The same three pooled values divided by r_nc (MY ARITHMETIC from sourced numbers)

**Source:** `f` and 95 % ends from the files above; `r_nc` = 1.1151352098 from `validation/CF_traj.json -> data.pooled_k1.r_nc` (`data/cf_trajectories/r_nc.json`). The combined interval that includes the uncertainty of r_nc is wider than shown (the planner combines Garwood and bootstrap variances on the log scale; I did not).

**Columns and units:** `f_hit` etc. dimensionless; `f_over_rnc` = f_hit / r_nc; `verdict_vs_0.1` compares the 95 % interval of f_hit/r_nc (without the r_nc uncertainty) with the mean bar 0.1

```csv
run,f_hit,lo95,hi95,r_nc,f_over_rnc,lo95_over_rnc,hi95_over_rnc,interval_vs_bar,bar
H0_kpilot pooled,0.041293,0.0361148,0.0469982,1.11514,0.0370296,0.032386,0.0421457,below,0.1 (mean bar)
H0_ddtest T3 (adopted),0.112853,0.105763,0.120292,1.11514,0.101202,0.0948432,0.107872,straddles,0.1 (mean bar)
H0_2x2 pooled,0.127053,0.108428,0.147942,1.11514,0.113935,0.0972327,0.132667,straddles,0.1 (mean bar)
```

#### (b3) \hat f_ideal = f_hit / r_nc as computed by the gates (sourced, not my division)

**Source:** `validation/CF_estimator_2x2_info.json -> data.rows` (the 2x2 records of 2026-10-02), `validation/H0_ddrep.json -> data.replication.f_hat_ideal_T3` (its interval is at confidence 0.9545, z = 2.0000, not 0.95), `validation/K1_2x3_fpilot.json -> data.pooled`. $r_{nc}=1.1151352098$ and its 95 % interval [1.0286, 1.1151] (`data/cf_trajectories/r_nc.json`); the intervals combine the Garwood (hit count) and bootstrap ($r_{nc}$) uncertainties on the log scale.

**Columns and units:** `f_hit` and `f_hat_ideal` dimensionless; `recorded_rule_on_f_hat_ideal` the preregistered 2x2 rule (lower 95 % end $\ge0.1$ is GO, upper end $<0.1$ is NO-GO, else AMBIGUOUS) applied to $\hat f_{\rm ideal}$; `v3_rule_on_f_hat_ideal` the rule of the 2x3 stages (GO iff lower $\ge0.05$ and point $\ge0.10$), not applied retroactively (`prompts/31` ruling 6); `recorded_verdict` the verdict written in the original gate. For K1 the decision rule is GO-B $\ge10^{-3}$, GO-A $\ge3\times10^{-4}$.

```csv
record,field,f_hit,f_hit_lo95,f_hit_hi95,f_hat_ideal,f_hat_ideal_lo95,f_hat_ideal_hi95,recorded_rule_on_f_hat_ideal,v3_rule_on_f_hat_ideal,recorded_verdict
H0_kpilot,data.decision.f_pool,0.041293,0.0361148,0.0469982,0.0370296,0.0321937,0.042406,NO-GO,NO-GO,NO-GO (kpilot)
H0_ddtest,data.decision.cells.T0.f_pool,0.0400315,0.035844,0.0445691,0.0358983,0.0319141,0.0402621,NO-GO,NO-GO,
H0_ddtest,data.decision.cells.T1.f_pool,0.000466785,-1.96655e-05,0.00133721,0.00041859,0,0.00120008,NO-GO,NO-GO,
H0_ddtest,data.decision.cells.T2.f_pool,0.111821,0.104764,0.119227,0.100276,0.0928731,0.108171,AMBIGUOUS,GO,
H0_ddtest,data.decision.cells.T3.f_pool,0.112853,0.105763,0.120292,0.101202,0.0937546,0.109142,AMBIGUOUS,GO,signed bar GO (adopted)
H0_2x2,data.clean_fraction.pooled.f,0.127053,0.108428,0.147942,0.113935,0.0967415,0.133368,AMBIGUOUS,GO,
H0_2x2,data.adopted_configuration.f_pool,0.112853,0.105763,0.120292,0.101202,0.0937546,0.109142,AMBIGUOUS,GO,signed bar GO
H0_ddrep,"data.replication.f_hat_ideal_T3 (2026-10-06, 95.45 % interval)",0.0731741,0.0674826,0.0792142,0.065619,0.059942,0.0717274,NO-GO (upper end 0.0717 < 0.1),NO-GO,signed bar NO-GO (information)
K1_2x3_fpilot,data.pooled (2x3),-1.2528e-06,-1.2528e-06,2.29768e-05,-1.12345e-06,-1.12345e-06,2.06045e-05,NO-GO,"NO-GO (K1 rule: GO-B >= 1e-3, GO-A >= 3e-4)",NO-GO firm
```

#### (c) H0_ddtest cells (ibm_kingston, job db01005j371s73dnmbd0, 2 circuits x 6 000 shots per cell)

**Note (2026-10-06):** these are the 2026-10-02 values; the same cells T0, T1, T3 on 2026-10-06 and four new mechanism cells are in block (o).

**Source:** `validation/H0_ddtest.json -> data.decision.cells.<cell>` (`f_pool`, `f_pool_95`, `R`, `R_95`, `null_ratio`, `accepted`, `reference_hits`, `qualifies`) and `data.decision.adopted`.

**Columns and units:** `n_pulses_total` sum over the two circuits of inserted DD pulses (per circuit in the source; T1 862 each); `f` reference-string clean fraction of the pooled two circuits; `f_lo95`,`f_hi95` 95 % interval; `R` = f(cell)/f(T0) with its 95 % interval; `null_ratio` the ratio the pulse error alone would give (pulse cost exp(-nats)); `accepted`, `reference_hits` summed over the two circuits

```csv
cell,description,n_pulses_total,f,f_lo95,f_hi95,R,R_lo95,R_hi95,null_ratio,accepted,reference_hits,qualifies,adopted
T0,no DD (baseline),0,0.0400315,0.035844,0.0445691,1,,,1,526,352,,False
T1,"context-aware staggered X (qiskit ContextAwareDynamicalDecoupling, min window 512 ns)",1724,0.000466785,-1.96655e-05,0.00133721,0.0116604,0.00438888,0.0309796,0.816228,102,7,False,False
T2,client XY4 in every idle window >= 256 ns,1556,0.111821,0.104764,0.119227,2.79333,2.4719,3.15656,0.841058,1429,978,True,False
T3,client XY4 in idle windows >= 1.024 us only,488,0.112853,0.105763,0.120292,2.81912,2.49509,3.18523,0.944388,1456,987,True,True
```

#### (d) H0_2x2 Ritz energies versus exact E0, certificate intervals (per sector)

**Source:** `validation/H0_2x2.json -> data.energies.<sector>.{B_all,B_sig}` (`E_R`, `abs_error`, `rH`, `weinstein_gap_assumed`, `kato_temple`, `gap_assumption_holds`, `E0_inside_gap_assumed_weinstein`) and `data.support.<sector>` (`dim`, `shots`, `accepted`, `Na_over_dim`).

**Columns and units:** energies in lattice units (dimensionless); `abs_error` = |E_R - E0|; `rH` Hamiltonian residual; Weinstein/Kato-Temple intervals as [lo, hi] (the gap-assumed interval is [E_R - delta, E_R]); `Na_over_dim` = N a / dim, the saturation parameter (rule C22)

```csv
sector,basis,basis_size,E_R,E0_exact,abs_error,rH,weinstein_lo,weinstein_hi,kato_temple_lo,kato_temple_hi,gap_assumption_holds,E0_in_weinstein,sector_dim,shots,accepted,Na_over_dim
B=0,B_all,38,-3.64077,-3.64077,0,6.14037e-15,-3.64077,-3.64077,-3.64077,-3.64077,True,True,38,69505,9454,16.969
B=0,B_sig,35,-3.64022,-3.64077,0.000547674,0.0602701,-3.70049,-3.64022,-3.64157,-3.64022,True,True,38,69505,9454,16.969
B=1,B_all,20,-1.86159,-1.86159,0,1.50912e-15,-1.86159,-1.86159,-1.86159,-1.86159,True,True,20,64402,7885,15.7231
B=1,B_sig,19,-1.86158,-1.86159,5.74934e-06,0.00595351,-1.86754,-1.86158,-1.86242,-1.86158,True,True,20,64402,7885,15.7231
```

#### (d2) H0_2x2 baselines: random equal-size bases and garbage-only (per sector)

**Source:** `validation/H0_2x2.json -> data.baselines.<sector>.{random_equal_size,garbage_only}`.

**Columns and units:** `n_seeds` number of random draws (200 seeds 23-222 for random subsets of the sector codewords including the references; 100 seeds 11-110 for uniformly random 12-bit strings run through the decoder at the hardware shot counts); `basis_size` size of each random basis (for garbage-only the mean decoded support size); E columns are the Ritz energy distribution of the baseline in lattice units; `hardware_E_R` the hardware value compared (B_sig for the random baseline, B_all for garbage-only); `hardware_percentile` the percentile of the hardware value within the baseline (5.0 means only 5 % of random bases are at least as good as the hardware for B=0; for garbage-only 100 means the hardware value equals the garbage-only value)

```csv
sector,baseline,n_seeds,basis_size,E_R_mean,E_R_std,E_R_p2.5,E_R_p97.5,E_R_min,E_R_max,hardware_E_R,hardware_percentile
B=0,random_equal_size,200,35,-3.63266,0.00638631,-3.64036,-3.61855,-3.64069,-3.61337,-3.64022,5
B=0,garbage_only,100,38,-3.64077,4.46326e-16,-3.64077,-3.64077,-3.64077,-3.64077,-3.64077,100
B=1,random_equal_size,200,19,-1.85411,0.00794102,-1.86158,-1.84104,-1.86158,-1.84104,-1.86158,28.5
B=1,garbage_only,100,20,-1.86159,6.6949e-16,-1.86159,-1.86159,-1.86159,-1.86159,-1.86159,100
```

#### (d3) H0_2x2 per-state counts and exact ground-state weights (one row per sector state)

**Source:** `validation/H0_2x2.json -> data.support.<sector>.per_state`.

**Columns and units:** `n_s` accepted count of the state over all shots of the sector; `mu_s` expected count from uniform noise N a/dim; `z` one-sided Poisson significance above mu_s; `ground_state_weight` exact |<b|Omega>|^2 (dimensionless, sums to 1 over the sector); `label` is the project's (j2 flux labels); (n labels)

```csv
sector,basis_index,label,n_s,mu_s,z,in_B_all,in_B_sig,ground_state_weight,is_reference
B=0,3,"(0,0,0,0); (0,0,2,2)",374,16.969,86.6718,True,True,0.00171136,False
B=0,5,"(0,0,0,0); (0,2,0,2)",304,16.969,69.6788,True,True,0.00171136,False
B=0,6,"(0,0,0,0); (0,2,2,0)",764,16.969,181.347,True,True,0.819498,True
B=0,9,"(0,0,0,0); (2,0,0,2)",169,16.969,36.9066,True,True,2.03589e-05,False
B=0,10,"(0,0,0,0); (2,0,2,0)",391,16.969,90.7987,True,True,0.00171136,False
B=0,12,"(0,0,0,0); (2,2,0,0)",443,16.969,103.422,True,True,0.00171136,False
B=0,17,"(0,0,0,1); (0,2,1,1)",634,16.969,149.789,True,True,0.0407652,True
B=0,18,"(0,0,0,1); (2,0,1,1)",335,16.969,77.2043,True,True,0.000110977,False
B=0,21,"(0,0,1,0); (0,1,2,1)",704,16.969,166.782,True,True,0.0407652,True
B=0,22,"(0,0,1,0); (2,1,0,1)",289,16.969,66.0375,True,True,0.000110977,False
B=0,25,"(0,0,1,1); (0,1,1,2)",283,16.969,64.5809,True,True,0.00097665,False
B=0,26,"(0,0,1,1); (2,1,1,0)",137,16.969,29.1384,True,True,1.22896e-05,False
B=0,29,"(0,1,0,0); (1,1,0,2)",218,16.969,48.8017,True,True,0.000110977,False
B=0,30,"(0,1,0,0); (1,1,2,0)",639,16.969,151.002,True,True,0.0407652,True
B=0,32,"(0,1,0,1); (1,1,1,1)",368,16.969,85.2153,True,True,0.00222583,False
B=0,34,"(0,1,1,0); (1,0,2,1)",308,16.969,70.6498,True,True,0.00097665,False
B=0,35,"(0,1,1,0); (1,2,0,1)",67,16.969,12.1454,True,True,1.22896e-05,False
B=0,38,"(0,1,1,1); (1,0,1,2)",139,16.969,29.6239,True,True,2.69479e-05,False
B=0,39,"(0,1,1,1); (1,2,1,0)",76,16.969,14.3302,True,True,7.81328e-05,False
B=0,42,"(1,0,0,0); (1,0,1,2)",186,16.969,41.0335,True,True,0.000110977,False
B=0,43,"(1,0,0,0); (1,2,1,0)",563,16.969,132.553,True,True,0.0407652,True
B=0,46,"(1,0,0,1); (1,0,2,1)",91,16.969,17.9716,True,True,1.22896e-05,False
B=0,47,"(1,0,0,1); (1,2,0,1)",395,16.969,91.7697,True,True,0.00097665,False
B=0,49,"(1,0,1,0); (1,1,1,1)",403,16.969,93.7118,True,True,0.00222583,False
B=0,51,"(1,0,1,1); (1,1,0,2)",112,16.969,23.0695,True,True,2.69479e-05,False
B=0,52,"(1,0,1,1); (1,1,2,0)",97,16.969,19.4281,True,True,7.81328e-05,False
B=0,55,"(1,1,0,0); (0,1,1,2)",44,16.969,6.56197,True,True,1.22896e-05,False
B=0,56,"(1,1,0,0); (2,1,1,0)",272,16.969,61.9106,True,True,0.00097665,False
B=0,59,"(1,1,0,1); (0,1,2,1)",30,16.969,3.16337,True,False,7.81328e-05,False
B=0,60,"(1,1,0,1); (2,1,0,1)",171,16.969,37.3921,True,True,2.69479e-05,False
B=0,63,"(1,1,1,0); (0,2,1,1)",55,16.969,9.2323,True,True,7.81328e-05,False
B=0,64,"(1,1,1,0); (2,0,1,1)",161,16.969,34.9646,True,True,2.69479e-05,False
B=0,69,"(1,1,1,1); (0,0,2,2)",28,16.969,2.67786,True,False,2.51948e-06,False
B=0,71,"(1,1,1,1); (0,2,0,2)",26,16.969,2.19234,True,False,2.51948e-06,False
B=0,72,"(1,1,1,1); (0,2,2,0)",59,16.969,10.2033,True,True,0.00129327,False
B=0,75,"(1,1,1,1); (2,0,0,2)",37,16.969,4.86267,True,True,4.48908e-07,False
B=0,76,"(1,1,1,1); (2,0,2,0)",50,16.969,8.01851,True,True,2.51948e-06,False
B=0,78,"(1,1,1,1); (2,2,0,0)",32,16.969,3.64888,True,True,2.51948e-06,False
B=1,7,"(0,0,0,0); (0,2,2,2)",555,15.7231,136.001,True,True,0.437467,True
B=1,11,"(0,0,0,0); (2,0,2,2)",719,15.7231,177.36,True,True,0.00480969,False
B=1,13,"(0,0,0,0); (2,2,0,2)",492,15.7231,120.113,True,True,0.00480969,False
B=1,14,"(0,0,0,0); (2,2,2,0)",669,15.7231,164.751,True,True,0.437467,True
B=1,19,"(0,0,0,1); (2,2,1,1)",826,15.7231,204.345,True,True,0.0270718,False
B=1,23,"(0,0,1,0); (2,1,2,1)",1171,15.7231,291.351,True,True,0.0270718,False
B=1,27,"(0,0,1,1); (2,1,1,2)",698,15.7231,172.064,True,True,0.00065098,False
B=1,31,"(0,1,0,0); (1,1,2,2)",455,15.7231,110.782,True,True,0.0270718,False
B=1,36,"(0,1,1,0); (1,2,2,1)",212,15.7231,49.4993,True,True,0.0022532,False
B=1,40,"(0,1,1,1); (1,2,1,2)",135,15.7231,30.0806,True,True,9.32586e-07,False
B=1,44,"(1,0,0,0); (1,2,1,2)",540,15.7231,132.218,True,True,0.0270718,False
B=1,48,"(1,0,0,1); (1,2,2,1)",351,15.7231,84.5539,True,True,0.0022532,False
B=1,53,"(1,0,1,1); (1,1,2,2)",27,15.7231,2.84393,True,False,9.32586e-07,False
B=1,57,"(1,1,0,0); (2,1,1,2)",218,15.7231,51.0125,True,True,0.00065098,False
B=1,61,"(1,1,0,1); (2,1,2,1)",176,15.7231,40.4204,True,True,9.32586e-07,False
B=1,65,"(1,1,1,0); (2,2,1,1)",191,15.7231,44.2033,True,True,9.32586e-07,False
B=1,73,"(1,1,1,1); (0,2,2,2)",80,15.7231,16.2101,True,True,0.000670039,False
B=1,77,"(1,1,1,1); (2,0,2,2)",115,15.7231,25.0368,True,True,3.16517e-06,False
B=1,79,"(1,1,1,1); (2,2,0,2)",131,15.7231,29.0718,True,True,3.16517e-06,False
B=1,80,"(1,1,1,1); (2,2,2,0)",124,15.7231,27.3065,True,True,0.000670039,False
```

#### (e) B_all and B_sig support growth versus k (cumulative over circuits with k <= k_max)

**Source:** `validation/H0_2x2.json -> data.support.<sector>.k_growth`.

**Columns and units:** `k_max` largest Krylov order included; `shots` cumulative shots of the sector over circuits with k <= k_max (94 % of the shots are at k = 4); `B_all` and `B_sig` support sizes (number of sector states); `sector_dim` 38 or 20

Reading note: at k_max = 4 the shot count jumps by a factor of about 17 (B=0: 4 005 -> 69 505), so the k-resolved curve mostly tracks shots rather than depth (planner report, lesson 9).

```csv
sector,sector_dim,k_max,shots,B_all,B_sig
B=0,38,1,1335,21,8
B=0,38,2,2670,26,13
B=0,38,3,4005,34,19
B=0,38,4,69505,38,35
B=1,20,1,534,9,3
B=1,20,2,1068,13,6
B=1,20,3,1602,16,10
B=1,20,4,64402,20,19
```

#### (f) Device survey for the signed 2x3 circuit family: gate-only f, f under the memory scenarios, and cost

**Source:** `data/quantinuum/devices_20261002.json -> rows.2x3|*` (Quantinuum rows), `data/ionq_2x3_feasibility_20261001.json -> results` (IonQ rows), `reports/qpu_survey_2x3_20261002.md` section 3 and `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` section 2.3 (the other devices; planner arithmetic with an ESTIMATE routing overhead where marked).

**Columns and units:** `n_2q` two-qubit gates per circuit; `eps2`, `eps1`, `eps_ro` error rates per gate / per qubit (dimensionless); `f_gate_only_mean`, `f_gate_only_worst` clean fraction from gate and readout errors only; `f_mem_low/mid/high` clean fraction including the transport/memory term of the ESTIMATE scenarios (round time 0.5 / 1.1 / 4.4 ms); `shots_total` D3-type union shot rule scaled as 1/f; `hqc_est` HQC = 5 + C(N_1q+10N_2q+5N_m)/5000 per job summed (ESTIMATE); `usd_est` at 12.5 USD per HQC (Azure Standard-plan equivalent, ESTIMATE; pay-as-you-go not public); `machine_h_mid_est` hours at the mid scenario (ESTIMATE). Blank = not available in the sources. For non-Quantinuum rows `f_gate_only_mean` holds the survey's gate-only value.

Signed bar: mean f >= 0.1 over the family and worst >= 0.05 (amendment 01 item 2). Only H2-2, Helios-1 and (marginally) H1-1 reach it on gate errors alone.

```csv
device,platform,lattice,n_2q,eps2,eps1,eps_ro,f_gate_only_mean,f_gate_only_worst,f_mem_low,f_mem_mid,f_mem_high,shots_total,hqc_est,usd_est,machine_h_mid_est,source,note
H2-2,trapped ion (QCCD),2x3,2158,0.00083,2.8e-05,0.000935,0.150157,0.149997,0.145378,0.139845,0.112966,102100,507144,6339299,60.1,data/quantinuum/devices_20261002.json rows.2x3|quantinuum_h2_2,vendor numbers read 2026-10-02; memory and cost are ESTIMATE
Helios-1,trapped ion (QCCD),2x3,2158,0.00079,3e-05,0.00048,0.164197,0.16401,0.137837,0.111728,0.0352008,127700,634299,7928733,75.1,data/quantinuum/devices_20261002.json rows.2x3|quantinuum_helios_1,vendor numbers read 2026-10-02; memory and cost are ESTIMATE
H1-1,trapped ion (QCCD),2x3,2158,0.00097,1.8e-05,0.0023,0.111327,0.111251,0.104918,0.097713,0.0660704,146000,725197,9064966,85.9,data/quantinuum/devices_20261002.json rows.2x3|quantinuum_h1_1,vendor numbers read 2026-10-02; memory and cost are ESTIMATE
H2-1,trapped ion (QCCD),2x3,2158,0.0011,1.9e-05,0.001,0.0860245,0.0859623,0.0815105,0.0764053,0.0535337,186700,927358,11591969,109.8,data/quantinuum/devices_20261002.json rows.2x3|quantinuum_h2_1,vendor numbers read 2026-10-02; memory and cost are ESTIMATE
IonQ Aria (retired 2026),trapped ion,2x3,2158,0.004,0.0005,0.0039,3.52042e-05,,,,,,,,,data/ionq_2x3_feasibility_20261001.json results.2x3|ionq_aria|virtual_rz,virtual Rz; f incl. serial idle estimate 6.09826e-12
IonQ Forte,trapped ion,2x3,2158,0.004,0.0002,0.005,8.6081e-05,,,,,,,,,data/ionq_2x3_feasibility_20261001.json results.2x3|ionq_forte|virtual_rz,virtual Rz; f incl. serial idle estimate 
"IonQ Tempo (targets, late 2026)",trapped ion,2x3,2158,,,,0.077,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic: reports/qpu_survey_2x3_20261002.md table row 5 (99.9 % target; no gate time or T2 published)
Google Willow chip 2 (iswap-like 1.4e-3),superconducting,2x3,3884,,,,0.0013,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,"planner arithmetic, routing 1.8 ESTIMATE (qpu_survey rank 6); proposal-only access"
"IBM Heron / ibm_kingston best edge, ceiling",superconducting,2x3,5477,0.0008164,,,0.0001,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,gate-only ceiling f<=1.14e-2 at 5477 routed CZ (ionq_devices_2x3_2x4_planner_analysis_20261002.md 2.3); about 1e-4 with 1q+readout; K0 gate: 1.095e-2
Infleqtion Sqale (raw 98.8 %),neutral atom,2x3,3884,,,,1.4e-05,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic (qpu_survey rank 9); private beta
QuEra Gemini (99.2 % global),neutral atom,2x3,3884,,,,1.3e-08,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic (qpu_survey rank 10); consultation
IBM Nighthawk / Heron-class median 2.15e-3,superconducting,2x3,5477,0.00215,,,3e-06,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic (qpu_survey rank 11)
Rigetti Cepheus / IQM Emerald (99.5 %),superconducting,2x3,3884,0.005,,,1e-09,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic: f < 1e-9 (qpu_survey rank 12)
AQT IBEX Q1,trapped ion,2x3,2158,0.013,,,5e-13,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,12 qubits < 20 and a 2000-gate cap (qpu_survey rank 13); f_2q only; eps2 = 1 - 0.987 from the product page
```

#### (f2) The 2x2 circuit on the other devices (information; not a plan item)

**Source:** `data/quantinuum/devices_20261002.json -> rows.2x2|*`, `data/ionq_2x3_feasibility_20261001.json -> results.2x2|*`, `validation/H0_2x2.json`.

**Columns and units:** as block (f); 2x2 circuit of 256 two-qubit gates (all-to-all). The IBM row is the measured pooled reference-hit fraction with DD, 588 routed CZ.

```csv
device,lattice,n_2q,eps2,f_gate_only_mean,f_mem_low,f_mem_mid,f_mem_high,source
H2-2,2x2,256,0.00083,0.787461,0.786953,0.786344,0.783003,data/quantinuum/devices_20261002.json rows.2x2|quantinuum_h2_2
Helios-1,2x2,256,0.00079,0.799066,0.796282,0.792953,0.774892,data/quantinuum/devices_20261002.json rows.2x2|quantinuum_helios_1
H1-1,2x2,256,0.00097,0.751405,0.750683,0.749818,0.745078,data/quantinuum/devices_20261002.json rows.2x2|quantinuum_h1_1
H2-1,2x2,256,0.0011,0.737831,0.737038,0.736088,0.730883,data/quantinuum/devices_20261002.json rows.2x2|quantinuum_h2_1
ionq_aria,2x2,256,0.004,0.260928,,,,data/ionq_2x3_feasibility_20261001.json results.2x2|ionq_aria|virtual_rz
ionq_forte,2x2,256,0.004,0.302881,,,,data/ionq_2x3_feasibility_20261001.json results.2x2|ionq_forte|virtual_rz
"IBM ibm_kingston, T3 measured (reference-hit statistic)",2x2,588,,0.127053,,,,"validation/H0_2x2.json (588 routed CZ on the patch; measured, not a model)"
```

#### (g) 2x3 shots and HQC versus clean fraction f, for each shot rule (planner prototype rows; the D3'-R base rows and the re-sized rows are now reproduced by gates)

**Source:** `scratch/planner/d3s_2x3_shot_rule_20261003.json -> plans["<sector>|f=<f>"].<rule>` (shots_total, jobs, hqc_total, recall floors, probabilities); the rows labelled D3'-R reproduce the table of `reports/2x3_shot_rule_estimator_ruling_20261003.md` section 2.4 (e.g. f=0.10: 34 909 + 49 203 shots, 418 166 HQC). This JSON is a planner prototype; gate `Q0P_2x3_plan` (P1) has since reproduced the D3'-R rows to the shot (criterion P1, whose text names $f=0.10$ while the log row of 2026-10-05 says all three $f$; `validation/Q0P_2x3_plan.json -> data.plan_table`), and gate `CV_2x3_plan` produced the **re-sized plan of record** (the last nine rows, three per $f$: `rule` = "D3'-R x s ...", from `validation/CV_2x3_plan.json -> data.plan.<f>.<sector>.{final_shots_total, final_jobs, final_hqc, resized_by}`; the `s` column is the multiplier, $B=0$ at 1 and $B=1$ at 2). The other rules (D3'-S, S99-only, D3-type union) remain planner prototype arithmetic and are alternatives, not the plan. The "both" rows are sums over the two sectors **(sum of sourced numbers)**.

**Columns and units:** `f` the clean (ideal-sample) fraction fed to the rule, dimensionless; `shots` total shots of the sector (or both); `jobs` Quantinuum jobs of <= 10 000 shots; `hqc` HQC = sum over jobs of [5 + C(N_1q + 10 N_2q + 5 N_m)/5000], 4.9666 HQC per shot at the mean counts (ESTIMATE of cost; USD at 12.5 USD per HQC would be hqc x 12.5); `recall_floor_S999` expected recall of the 99.9 % support from clean shots alone; `P_recall_ge_0.9` probability that clean shots alone recall >= 0.9 of S999; `n_S999_below_lambda_star` S999 states with expected clean count < 6.2958; `lambda_min` minimum expected clean count (over S99 for D3'-R and the S99 rule, over S999 otherwise) at y = 0.82 x 0.7 x f

```csv
rule,f,sector,shots,jobs,hqc,recall_floor_S999,P_recall_ge_0.9,n_S999_below_lambda_star,lambda_min
D3'-R (ruling),0.05,B=0,63875,35,317546,0.940225,0.953118,45,7.24961
D3'-R (ruling),0.05,B=1,96503,20,479612,0.950075,0.993485,34,6.30634
D3'-R (ruling),0.05,both,160378,55,797157,,,,
D3'-R (ruling),0.10,B=0,34909,33,173614,0.941808,0.960341,45,7.3424
D3'-R (ruling),0.10,B=1,49203,16,244553,0.949956,0.993329,34,6.29926
D3'-R (ruling),0.10,both,84112,49,418166,,,,
D3'-R (ruling),0.15,B=0,27309,33,135860,0.94272,0.965226,47,7.7371
D3'-R (ruling),0.15,B=1,33503,13,166522,0.950151,0.993515,34,6.31865
D3'-R (ruling),0.15,both,60812,46,302382,,,,
"D3'-S (lambda* on every S999 state, LP allocation)",0.05,B=0,375000,66,1.8636e+06,0.999863,,,6.30077
"D3'-S (lambda* on every S999 state, LP allocation)",0.05,B=1,735000,84,3.65269e+06,0.999895,,,6.29653
"D3'-S (lambda* on every S999 state, LP allocation)",0.05,both,1110000,150,5.51628e+06,,,,
"D3'-S (lambda* on every S999 state, LP allocation)",0.10,B=0,190300,49,945788,0.999869,,,6.30801
"D3'-S (lambda* on every S999 state, LP allocation)",0.10,B=1,368700,47,1.83232e+06,0.999896,,,6.2979
"D3'-S (lambda* on every S999 state, LP allocation)",0.10,both,559000,96,2.77811e+06,,,,
"D3'-S (lambda* on every S999 state, LP allocation)",0.15,B=0,128600,42,639183,0.99987,,,6.31405
"D3'-S (lambda* on every S999 state, LP allocation)",0.15,B=1,246500,35,1.22503e+06,0.999895,,,6.29765
"D3'-S (lambda* on every S999 state, LP allocation)",0.15,both,375100,77,1.86422e+06,,,,
D3'-S k=4-scaled allocation (as D3'),0.05,B=0,732008,104,3.6377e+06,0.99996,,,6.30201
D3'-S k=4-scaled allocation (as D3'),0.05,B=1,1062903,117,5.28227e+06,0.999959,,,6.29606
D3'-S k=4-scaled allocation (as D3'),0.05,both,1794911,221,8.91997e+06,,,,
D3'-S k=4-scaled allocation (as D3'),0.10,B=0,368008,64,1.82886e+06,0.99996,,,6.30792
D3'-S k=4-scaled allocation (as D3'),0.10,B=1,532503,63,2.64637e+06,0.999959,,,6.29794
D3'-S k=4-scaled allocation (as D3'),0.10,both,900511,127,4.47524e+06,,,,
D3'-S k=4-scaled allocation (as D3'),0.15,B=0,246408,48,1.22458e+06,0.99996,,,6.30692
D3'-S k=4-scaled allocation (as D3'),0.15,B=1,355503,45,1.76674e+06,0.999959,,,6.29626
D3'-S k=4-scaled allocation (as D3'),0.15,both,601911,93,2.99133e+06,,,,
lambda* on S99 only (LP),0.05,B=0,48700,35,242144,0.873018,0.185866,48,6.34723
lambda* on S99 only (LP),0.05,B=1,96800,20,481085,0.950111,0.993525,34,6.31066
lambda* on S99 only (LP),0.05,both,145500,55,723228,,,,
lambda* on S99 only (LP),0.10,B=0,27000,33,134315,0.869123,0.156051,48,6.36359
lambda* on S99 only (LP),0.10,B=1,49500,16,246026,0.950029,0.993411,34,6.30791
lambda* on S99 only (LP),0.10,both,76500,49,380341,,,,
lambda* on S99 only (LP),0.15,B=0,20200,33,100536,0.822438,0.0107314,48,6.40712
lambda* on S99 only (LP),0.15,B=1,33800,13,167995,0.95026,0.993634,34,6.33564
lambda* on S99 only (LP),0.15,both,54000,46,268532,,,,
D3-type union reading (Stage A record),0.05,B=0,204320,32,1.01528e+06,0.98489,,,1.0796
D3-type union reading (Stage A record),0.05,B=1,203100,24,1.00791e+06,0.928152,,,0.533317
D3-type union reading (Stage A record),0.05,both,407420,56,2.02319e+06,,,,
D3-type union reading (Stage A record),0.10,B=0,102208,32,507960,0.984904,,,1.08011
D3-type union reading (Stage A record),0.10,B=1,101604,12,504222,0.928202,,,0.5336
D3-type union reading (Stage A record),0.10,both,203812,44,1.01218e+06,,,,
D3-type union reading (Stage A record),0.15,B=0,68128,32,338640,0.9849,,,1.07994
D3-type union reading (Stage A record),0.15,B=1,67704,12,336010,0.928157,,,0.533348
D3-type union reading (Stage A record),0.15,both,135832,44,674650,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=1",0.05,B=0,63875,35,317546,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=2",0.05,B=1,193600,29,962114,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1)",0.05,both,257475,64,1279660,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=1",0.10,B=0,34909,33,173614,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=2",0.10,B=1,99000,20,491991,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1)",0.10,both,133909,53,665605,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=1",0.15,B=0,27309,33,135860,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=2",0.15,B=1,67600,16,335941,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1)",0.15,both,94909,49,471801,,,,
```

#### (h) CF_traj: per-arm f0', f_hit, benign fraction, f_ideal and r (with 95 % bootstrap intervals)

**Source:** `validation/CF_traj.json -> data.arms.<arm>.stats`, `data.pooled_k1.stats`, `data.A5_2x2_arm.ends.<end>` (the A5 rows use the 2x2 circuit `B0_ref06_k1` with DD cell T3 under a twirled idle model at the two T2 ends; `star` = free-induction T2*, `echo` = Hahn-echo T2). The pooled row's `r` upper end is **r_nc = 1.1151352098** (`data/cf_trajectories/r_nc.json`). Arm `B0_ref25_k1__xx` is the bit-flip-only control. C7: the k=4 mixture-estimator bias is 1.27436 [1.16999, 1.40205] (`data.C7_k4_mixture.bias_ratio`).

**Columns and units:** `K` number of Pauli trajectories; `n_zz`,`n_phasedx` gate counts of the circuit (2158 two-qubit gates at 2x3; 588 sites at 2x2); `p_ref` ideal probability of the reference string; `f0_prime` fault-free fraction (no gate error and the reference read out correctly), dimensionless; `f_hit` reference-hit fraction; `b` benign fraction of faulty trajectories within total-variation distance 1e-3 of the ideal; `f_ideal` = f0' + (1 - f0') b; `r` = f_hit / f_ideal; `min_feff_over_fideal_S99` the floor-theorem quantity (>= 0.95 required); `rho_T` information only (withdrawn statistic). Each estimate is followed by `_lo`,`_hi` = 95 % interval

```csv
arm,K,n_two_qubit,n_phasedx,p_ref,f0_prime,f_hit,f_hit_lo,f_hit_hi,b,b_lo,b_hi,f_ideal,f_ideal_lo,f_ideal_hi,r,r_lo,r_hi,min_feff_over_fideal_S99,min_lo,min_hi,rho_T
B0_ref25_k1,720,2158,3091,0.915021,0.172087,0.238733,0.224073,0.254904,0.0569444,0.0416667,0.075,0.219232,0.206583,0.23418,1.08895,1.04969,1.13613,1.08895,1.04829,1.13314,3.07375
B1_ref57_k1,240,2158,2989,0.912199,0.172365,0.257455,0.228477,0.290026,0.0875,0.0541667,0.125,0.244783,0.217195,0.275819,1.05177,0.987028,1.126,1.04031,0.980229,1.10469,3.85601
B0_ref25_k4,240,2158,3063,0.236292,0.172188,0.245912,0.218692,0.276283,0.0583333,0.0291667,0.0916667,0.220477,0.196333,0.248071,1.11536,1.03564,1.21968,1.09967,1.01952,1.18691,1.6194
B0_ref25_k1__xx,120,2158,3091,0.915021,0.172087,0.179345,0.172291,0.193086,0,0,0,0.172087,0.172087,0.172087,1.04218,1.00119,1.12202,1.04101,1.00077,1.11958,2.77239
"pooled k=1 (B0_ref25_k1 + B1_ref57_k1, 800+800 shots)",,,,,,0.24808,0.23082,0.266234,,,,0.232007,0.216487,0.249826,1.06927,1.02859,1.11514,,,,
"A5 2x2 star (T3 circuit, K=2000)",2000,588,,0.883276,1.64125e-06,0.0188678,0.0139073,0.0240857,0.028,0.021,0.0350125,0.0280016,0.0210016,0.0350141,0.673813,0.538634,0.834637,,,,
"A5 2x2 echo (T3 circuit, K=2000)",2000,588,,0.883276,0.0915231,0.288124,0.272764,0.301992,0.251,0.2305,0.269,0.319551,0.300927,0.335903,0.901652,0.884234,0.918329,,,,
```

#### (i) Cumulative QPU seconds over time (IBM open plan, 600 s allowance)

**Source:** `data/hardware/*/session.json -> jobs[*].{submitted,job_id,usage_s,n_pubs,group_shots}`, `backend`; the final cumulative 327 s equals the account counter `usage_consumed_seconds` 327 (`data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json`; 139 s after job 13 in `data/hardware/H0_ddrep_ibm_kingston/account_check_after_20261006T0703Z.json`; 102 s after job 12 in `data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json`). `remaining_of_600_s` is my subtraction 600 - cumulative **(sum of sourced numbers)**; the account's own remaining value after the last job is 273.

**Columns and units:** `submitted_utc` job submission time (UTC); `usage_s` billed QPU seconds of the job; `cumulative_s` running total; `remaining_of_600_s` allowance left; `n_pubs` circuits (pubs) in the job; `shots_per_pub`

The two newest rows (2026-10-06) are the `H0_ddrep` job and the K1 pilot; no QPU job has run after 2026-10-06 08:22 UTC as far as the repository records show.

```csv
submitted_utc,device,job_id,what,usage_s,cumulative_s,remaining_of_600_s,n_pubs,shots_per_pub
2026-09-22 17:48:32,ibm_fez,dapbusac505c73chv0og,canary,2,2,598,3,267
2026-09-22 20:42:56,ibm_fez,dapegkcak42c73cierv0,diag J1 (both options off),5,7,593,5,2000
2026-09-22 20:43:55,ibm_fez,dapeh3318flc739m51e0,diag J2 (XY4),4,11,589,3,2000
2026-09-22 20:44:13,ibm_fez,dapeh7ac505c73ci2o60,diag J3 (twirling),3,14,586,1,2000
2026-09-22 20:44:27,ibm_fez,dapehb4ak42c73cietig,diag J4 (XY4 + twirling),3,17,583,1,2000
2026-10-02 18:12:35,ibm_kingston,davv8504oijs73e88fvg,H0_kpilot,12,29,571,8,4000
2026-10-02 20:11:42,ibm_kingston,db01005j371s73dnmbd0,H0_ddtest,20,49,551,10,6000
2026-10-02 21:05:55,ibm_kingston,db01pddj371s73dnnqm0,H0_2x2,3,52,548,14,267
2026-10-02 21:05:57,ibm_kingston,db01pdtj371s73dnnqmg,H0_2x2,3,55,545,7,267
2026-10-02 21:05:59,ibm_kingston,db01pe04oijs73e8cl30,H0_2x2,4,59,541,2,4000
2026-10-02 21:06:00,ibm_kingston,db01pelj371s73dnnqo0,H0_2x2,22,81,519,5,13100
2026-10-02 21:06:02,ibm_kingston,db01peql7guc73cfndc0,H0_2x2,21,102,498,2,31400
2026-10-06 07:00:40,ibm_kingston,db29p6nr11fs7396e4ig,H0_ddrep,37,139,461,20,6000
2026-10-06 08:22:03,ibm_kingston,db2avbe8v0ts73c2i8b0,K1_2x3_fpilot,188,327,273,4,100000
```

#### (j) 2x2 / 2x3 / 2x4 gate counts and device requirements

**Source:** `validation/S2.json -> data.{2x2,2x3}.{per_term_cz,per_term_cz_routed,coarse_step}`, `validation/S2_2x4.json -> data.term_cost` and `data.schedule.schedule_*.rows` (the `B0_ref0_k1` rows; Heron durations from `data/hardware/H0_diag_prep/calibration_20260922T1400Z.json`).

**Columns and units:** `value` is a count of two-qubit gates (CZ, or IR CX where stated), a transpiled depth, a duration in microseconds, a dimensionless utilisation, or a ratio T2 / t_2q (the coherence time over the two-qubit gate time the device must have for f = 0.1 with T1 -> infinity). `quantity` names which. 

Note: the `per_term_ir_cx_before_transpile_*` rows are IR CX counts of each term circuit before the transpiler merges gates (so they differ from the transpiled per-term CZ rows of the 2x2 and 2x3 lattices); the same per-term table with all columns is in `reports/S2_2x4_compilation_and_device_requirement.md` (hop0 278 CX ... plaq1 66 468 CX; sum of the 13 hop/plaquette terms 71 520 exact and 16 546 fixed-angle).

```csv
lattice,kind,item,value,source
2x2,per_term_cz_all_to_all,diag,8,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,hop0,60,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,hop1,48,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,hop2,66,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,hop3,44,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,plaq0,30,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_routed,diag,8,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,hop0,122,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,hop1,92,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,hop2,149,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,hop3,72,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,plaq0,73,validation/S2.json data.2x2.per_term_cz_routed
2x2,coarse_step_all_to_all_cz,total,256,validation/S2.json data.2x2.coarse_step.all_to_all.cz
2x2,coarse_step_all_to_all_depth,total,736,"validation/S2.json (transpiled depth, basis rz/sx/x/cz)"
2x2,coarse_step_routed_cz,total,618,validation/S2.json data.2x2.coarse_step.routed.cz
2x2,coarse_step_routed_depth,total,1294,"validation/S2.json (transpiled depth, basis rz/sx/x/cz)"
2x3,per_term_cz_all_to_all,diag,20,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop0,194,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop1,48,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop2,182,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop3,184,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop4,358,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop5,156,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop6,44,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,plaq0,214,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,plaq1,764,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_routed,diag,20,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop0,433,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop1,82,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop2,415,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop3,396,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop4,846,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop5,275,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop6,72,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,plaq0,497,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,plaq1,1698,validation/S2.json data.2x3.per_term_cz_routed
2x3,coarse_step_all_to_all_cz,total,2164,validation/S2.json data.2x3.coarse_step.all_to_all.cz
2x3,coarse_step_all_to_all_depth,total,7325,"validation/S2.json (transpiled depth, basis rz/sx/x/cz)"
2x3,coarse_step_routed_cz,total,5477,validation/S2.json data.2x3.coarse_step.routed.cz
2x3,coarse_step_routed_depth,total,11540,"validation/S2.json (transpiled depth, basis rz/sx/x/cz)"
2x3,per_term_ir_cx_before_transpile_exact,hop0,278,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop1,54,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop2,258,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop3,260,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop4,390,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop5,244,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop6,54,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,plaq0,228,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,plaq1,806,validation/S2_2x4.json data.term_cost.2x3|exact
2x4,per_term_ir_cx_before_transpile_exact,hop0,278,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop1,54,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop2,258,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop3,1548,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop4,390,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop5,542,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop6,260,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop7,390,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop8,244,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop9,54,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,plaq0,228,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,plaq2,806,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,plaq1,66468,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_fixed,hop0,272,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop1,52,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop2,280,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop3,536,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop4,272,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop5,536,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop6,280,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop7,272,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop8,272,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop9,52,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,plaq0,286,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,plaq1,12952,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,plaq2,484,validation/S2_2x4.json data.term_cost.2x4|fixed
2x2,"schedule[exact,all_to_all]",n_2q,256,validation/S2_2x4.json data.schedule.schedule_2_exact
2x2,"schedule[exact,all_to_all]",cz_depth,202,same
2x2,"schedule[exact,all_to_all]",duration_us,21.22,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x2,"schedule[exact,all_to_all]",qubit_time_utilisation,0.1877,same
2x2,"schedule[exact,all_to_all]",T2_req_over_t_2q_f0.1_T1inf,625.1,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x2,"schedule[exact,all_to_all]",serial_bound_T2_over_t_2q,667.1,closed-form serial bound
2x2,"schedule[exact,heavy_hex_3]",n_2q,618,validation/S2_2x4.json data.schedule.schedule_2_exact
2x2,"schedule[exact,heavy_hex_3]",cz_depth,426,same
2x2,"schedule[exact,heavy_hex_3]",duration_us,41.24,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x2,"schedule[exact,heavy_hex_3]",qubit_time_utilisation,0.216,same
2x2,"schedule[exact,heavy_hex_3]",T2_req_over_t_2q_f0.1_T1inf,1276.8,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x2,"schedule[exact,heavy_hex_3]",serial_bound_T2_over_t_2q,1744.6,closed-form serial bound
2x3,"schedule[exact,all_to_all]",n_2q,2164,validation/S2_2x4.json data.schedule.schedule_3_exact
2x3,"schedule[exact,all_to_all]",cz_depth,1926,same
2x3,"schedule[exact,all_to_all]",duration_us,213.84,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x3,"schedule[exact,all_to_all]",qubit_time_utilisation,0.0929,same
2x3,"schedule[exact,all_to_all]",T2_req_over_t_2q_f0.1_T1inf,11999.7,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x3,"schedule[exact,all_to_all]",serial_bound_T2_over_t_2q,9398.1,closed-form serial bound
2x3,"schedule[exact,heavy_hex_5]",n_2q,5477,validation/S2_2x4.json data.schedule.schedule_3_exact
2x3,"schedule[exact,heavy_hex_5]",cz_depth,3692,same
2x3,"schedule[exact,heavy_hex_5]",duration_us,363.78,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x3,"schedule[exact,heavy_hex_5]",qubit_time_utilisation,0.1091,same
2x3,"schedule[exact,heavy_hex_5]",T2_req_over_t_2q_f0.1_T1inf,21526.7,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x3,"schedule[exact,heavy_hex_5]",serial_bound_T2_over_t_2q,30922.2,closed-form serial bound
2x3,"schedule[exact,fakefez]",n_2q,5737,validation/S2_2x4.json data.schedule.schedule_3_exact
2x3,"schedule[exact,fakefez]",cz_depth,3749,same
2x3,"schedule[exact,fakefez]",duration_us,364.39,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x3,"schedule[exact,fakefez]",qubit_time_utilisation,0.1177,same
2x3,"schedule[exact,fakefez]",T2_req_over_t_2q_f0.1_T1inf,22500,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x3,"schedule[exact,fakefez]",serial_bound_T2_over_t_2q,31144.3,closed-form serial bound
2x4,"schedule[exact,all_to_all]",n_2q,69688,validation/S2_2x4.json data.schedule.schedule_4_exact
2x4,"schedule[exact,all_to_all]",cz_depth,68653,same
2x4,"schedule[exact,all_to_all]",duration_us,7920.58,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[exact,all_to_all]",qubit_time_utilisation,0.0577,same
2x4,"schedule[exact,all_to_all]",T2_req_over_t_2q_f0.1_T1inf,638742,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[exact,all_to_all]",serial_bound_T2_over_t_2q,423712,closed-form serial bound
2x4,"schedule[exact,heavy_hex_5]",n_2q,145958,validation/S2_2x4.json data.schedule.schedule_4_exact
2x4,"schedule[exact,heavy_hex_5]",cz_depth,108091,same
2x4,"schedule[exact,heavy_hex_5]",duration_us,11033.6,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[exact,heavy_hex_5]",qubit_time_utilisation,0.0865,same
2x4,"schedule[exact,heavy_hex_5]",T2_req_over_t_2q_f0.1_T1inf,873536,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[exact,heavy_hex_5]",serial_bound_T2_over_t_2q,919137,closed-form serial bound
2x4,"schedule[exact,heavy_hex_7]",n_2q,148850,validation/S2_2x4.json data.schedule.schedule_4_exact
2x4,"schedule[exact,heavy_hex_7]",cz_depth,108634,same
2x4,"schedule[exact,heavy_hex_7]",duration_us,11013,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[exact,heavy_hex_7]",qubit_time_utilisation,0.0912,same
2x4,"schedule[exact,heavy_hex_7]",T2_req_over_t_2q_f0.1_T1inf,861392,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[exact,heavy_hex_7]",serial_bound_T2_over_t_2q,905026,closed-form serial bound
2x4,"schedule[exact,fakefez]",n_2q,148726,validation/S2_2x4.json data.schedule.schedule_4_exact
2x4,"schedule[exact,fakefez]",cz_depth,108053,same
2x4,"schedule[exact,fakefez]",duration_us,10998.2,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[exact,fakefez]",qubit_time_utilisation,0.0916,same
2x4,"schedule[exact,fakefez]",T2_req_over_t_2q_f0.1_T1inf,858529,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[exact,fakefez]",serial_bound_T2_over_t_2q,904272,closed-form serial bound
2x4,"schedule[fixed,all_to_all]",n_2q,14048,validation/S2_2x4.json data.schedule.schedule_4_fixed
2x4,"schedule[fixed,all_to_all]",cz_depth,13656,same
2x4,"schedule[fixed,all_to_all]",duration_us,1564.64,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[fixed,all_to_all]",qubit_time_utilisation,0.0587,same
2x4,"schedule[fixed,all_to_all]",T2_req_over_t_2q_f0.1_T1inf,126067,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[fixed,all_to_all]",serial_bound_T2_over_t_2q,85413.6,closed-form serial bound
2x4,"schedule[fixed,heavy_hex_5]",n_2q,30208,validation/S2_2x4.json data.schedule.schedule_4_fixed
2x4,"schedule[fixed,heavy_hex_5]",cz_depth,21216,same
2x4,"schedule[fixed,heavy_hex_5]",duration_us,2109.22,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[fixed,heavy_hex_5]",qubit_time_utilisation,0.0894,same
2x4,"schedule[fixed,heavy_hex_5]",T2_req_over_t_2q_f0.1_T1inf,163723,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[fixed,heavy_hex_5]",serial_bound_T2_over_t_2q,196788,closed-form serial bound
2x4,"schedule[fixed,heavy_hex_7]",n_2q,28925,validation/S2_2x4.json data.schedule.schedule_4_fixed
2x4,"schedule[fixed,heavy_hex_7]",cz_depth,19649,same
2x4,"schedule[fixed,heavy_hex_7]",duration_us,2032.7,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[fixed,heavy_hex_7]",qubit_time_utilisation,0.0891,same
2x4,"schedule[fixed,heavy_hex_7]",T2_req_over_t_2q_f0.1_T1inf,169701,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[fixed,heavy_hex_7]",serial_bound_T2_over_t_2q,188430,closed-form serial bound
2x4,"schedule[fixed,fakefez]",n_2q,28765,validation/S2_2x4.json data.schedule.schedule_4_fixed
2x4,"schedule[fixed,fakefez]",cz_depth,19484,same
2x4,"schedule[fixed,fakefez]",duration_us,1998.49,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[fixed,fakefez]",qubit_time_utilisation,0.0871,same
2x4,"schedule[fixed,fakefez]",T2_req_over_t_2q_f0.1_T1inf,172796,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[fixed,fakefez]",serial_bound_T2_over_t_2q,193634,closed-form serial bound
```

#### (k) Exact reference energies per lattice and sector

**Source:** `data/references.json -> references` (the output of gate E3; `validation/E3.json` PASS 85/85).

**Columns and units:** energies in lattice units (m = 3 g^2/16); `B` baryon number = twoB/2; `W` spectral width E_max - E_min of the sector block; `emax` largest eigenvalue; `dt` = pi/W the Krylov time step; `support99`, `support999` numbers of configurations carrying 99 % / 99.9 % of the ground-state weight; `PR` participation ratio. For the 2x4 sectors only the lowest levels from Lanczos are tabulated; for static-charge sectors only 3 levels are stored

```csv
lattice,g2,m,twoB,B,dim,E0,E1,E2,W,Emax,dt,support99,support999,PR
2x2,4,0.75,0,0,38,-3.64077,-0.962245,-0.850567,12.8222,9.18144,0.245012,9,16,1.47438
2x2,4,0.75,2,1,20,-1.86159,-1.81975,0.208229,9.46425,7.60266,0.331943,8,13,2.59238
2x3,4,0.75,0,0,677,-5.6026,-2.8886,-2.86518,20.0813,14.4787,0.156443,31,86,1.91384
2x3,4,0.75,2,1,426,-3.82608,-3.80173,-3.66866,16.8023,12.9763,0.186973,42,95,3.56092
2x3,4,0.75,4,2,95,-2.01182,-1.86224,-1.84389,13.4486,11.4368,0.2336,15,22,1.50427
2x3,2,0.375,0,0,677,-4.22161,-2.72359,-2.70321,12.2336,8.01204,0.256799,137,326,5.93582
2x3,2,0.375,2,1,426,-3.08661,-2.97297,-2.79396,10.2927,7.20607,0.305226,135,240,11.9219
2x3,1,0.1875,0,0,677,-4.39179,-3.42014,-3.25049,10.3818,5.98998,0.302607,396,549,33.8312
2x4,4,0.75,0,0,12843,-7.56521,-4.8436,-4.83747,27.3901,19.8249,0.114698,76,305,2.4883
2x4,4,0.75,2,1,8934,-5.78016,-5.77413,-5.65409,24.1081,18.3279,0.130313,127,470,4.78485
2x3+static r=1,4,0.75,0,0,1089,-4.21542,-3.51247,-1.87712,17.7109,13.4954,0.177382,48,133,3.19288
2x3+static r=2,4,0.75,0,0,978,-3.01275,-2.65282,-2.65198,15.7007,12.6879,0.200093,69,174,6.1483
2x3+static r=1,2,0.375,0,0,1089,-3.43963,-2.74384,-2.26699,11.2319,7.79226,0.279703,226,512,8.37376
2x3+static r=2,2,0.375,0,0,978,-2.84759,-2.50289,-2.49183,10.5054,7.65779,0.299046,268,530,14.8782
```

#### (k2) Derived quantities and the j_max = 1 truncation shift

**Source:** `data/references.json -> derived`, `-> truncation_2x2`.

**Columns and units:** `quantity` D0 meson-like gap, MB baryon mass, binding = E0(B=2) - E0(B=0) - 2 MB, V1, V2 static potentials at separations 1 and 2 (lattice units); for the truncation rows: E0_half (jmax 1/2), E0_one (jmax 1), shift = E0_one - E0_half, dim_half, dim_one (state counts in the B=0 sector)

```csv
key,quantity,value
2x3|g2=4.0,D0,2.714
2x3|g2=4.0,MB,1.77652
2x3|g2=4.0,binding,0.0377436
2x3|g2=4.0,V1,1.38718
2x3|g2=4.0,V2,2.58985
2x3|g2=2.0,D0,1.49802
2x3|g2=2.0,MB,1.135
2x3|g2=2.0,binding,0.174795
2x3|g2=2.0,V1,0.781983
2x3|g2=2.0,V2,1.37403
2x4|g2=4.0,D0,2.72162
2x4|g2=4.0,MB,1.78505
2x4|g2=2.0,D0,1.50282
2x4|g2=2.0,MB,1.15598
2x2 truncation|g2=4.0,E0_half,-3.64077
2x2 truncation|g2=4.0,E0_one,-3.64269
2x2 truncation|g2=4.0,shift,-0.00192045
2x2 truncation|g2=4.0,dim_half,38
2x2 truncation|g2=4.0,dim_one,74
2x2 truncation|g2=2.0,E0_half,-2.67121
2x2 truncation|g2=2.0,E0_one,-2.70967
2x2 truncation|g2=2.0,shift,-0.0384592
2x2 truncation|g2=2.0,dim_half,38
2x2 truncation|g2=2.0,dim_one,74
2x2 truncation|g2=1.0,E0_half,-2.71752
2x2 truncation|g2=1.0,E0_one,-3.05857
2x2 truncation|g2=1.0,shift,-0.341051
2x2 truncation|g2=1.0,dim_half,38
2x2 truncation|g2=1.0,dim_one,74
```

#### (l) The 51 plan rows and their status (2x2 hardware campaign)

**Source:** `reports/H0_2x2_full_hardware_report_20261002.md` section 2 (planner scoring); full text in Section 17.1 of this file.

**Columns and units:** `row` the plan-row id used by the report; `group` manual (33 rows) or amendment/decision (18 rows); `status` F fulfilled, FD fulfilled with deviation, ND not done. Tally F 31, FD 12, ND 8

```csv
row,group,status
0,manual,F
1.1,manual,F
1.2,manual,F
1.3,manual,F
1.4,manual,F
1.5,manual,F
2.1-2.3,manual,F
2.4,manual,F
2.5,manual,F
3,manual,F
4.1,manual,F
4.2,manual,F
4.3,manual,FD
4.4,manual,FD
5.1,manual,F
5.2,manual,F
5.3,manual,F
5.4,manual,F
6.1-6.2,manual,FD
6.3,manual,ND
6.4,manual,ND
7.1-7.2,manual,FD
7.3,manual,ND
7.5,manual,ND
8.1-8.2,manual,F
8.3,manual,FD
9.1,manual,FD
9.2,manual,ND
9.3,manual,ND
10,manual,FD
10 (error budget),manual,FD
10 (reporting),manual,FD
11,manual,FD
A1,amendment/decision,F
A2,amendment/decision,FD
A3,amendment/decision,F
A4,amendment/decision,ND
A5,amendment/decision,ND
M4.4,amendment/decision,F
D8',amendment/decision,F
D1',amendment/decision,F
D3'-f,amendment/decision,F
D3''-H0,amendment/decision,FD
D5',amendment/decision,F
C2',amendment/decision,F
C3',amendment/decision,F
H0P-Y',amendment/decision,F
D9,amendment/decision,F
prereg,amendment/decision,F
dry runs,amendment/decision,F
owner 2026-10-02,amendment/decision,F
```

#### (m) The 2x2 shot plan actually flown (rule D3' at the adopted f)

**Source:** `validation/H0_2x2.json -> data.shot_plan`.

**Columns and units:** `N4` shots per k=4 circuit; the k=1,2,3 circuits ran at the 267-shot floor; `total_coarse_shots` over all 28 coarse circuits

```csv
quantity,value
N4_B=0,13100
N4_B=1,31400
total_coarse_shots,133907
```

#### (n) S2D_levers: Aer clean fraction versus the dephasing ratio r = T2*/T2echo, per lever row (2x2 circuit on the ibm_kingston patch)

**Source:** `validation/S2D_levers.json -> data.rows.<row>.{manifest,compile}` and `data.aer.<row>.<r>` (scheduled Aer at the record of 2026-10-01 with each qubit's dephasing time replaced by r x its echo T2; 4 000 shots, reference-string and mixture estimators). `data.verdict` gives r_crit(0.1) = 0.3302 (Aer interpolated; 0.7261 analytic bound) over all rows and 0.3285 for the signed family; the pilot measured an equivalent r of about 0.172 (`validation/H0_kpilot.json`).

**Columns and units:** `row` lever row (L0_asis = the canary as is, ASAP or ALAP scheduled; L1_seed = re-seeded transpile; L2_order = reordered terms; L3_rx = fractional rx; L4_all = all levers; L1_seed_alap = the signed term family with ALAP, the row the pilot and the full run used); `n_cz`,`n_rzz` two-qubit gates; `duration_us` ASAP/ALAP critical path T_s in microseconds; `twoq_layers` two-qubit layers; `r` dephasing ratio; `f_ref`, `f_ref_lo68`, `f_ref_hi68` reference-string clean fraction with its 68 % interval; `f_mix` mixture estimator; `shots` Aer shots

```csv
row,schedule,fractional,n_cz,n_rzz,duration_us,twoq_layers,r,f_ref,f_ref_lo68,f_ref_hi68,f_mix,shots
L0_asis_asap,asap,False,663,0,47.964,455,1.0,0.11771,0.11133,0.124445,0.121716,4000
L0_asis_asap,asap,False,663,0,47.964,455,0.5,0.0538542,0.0495338,0.0585336,0.0563266,4000
L0_asis_asap,asap,False,663,0,47.964,455,0.25,0.0117438,0.00971151,0.0141505,0.0125648,4000
L0_asis_asap,asap,False,663,0,47.964,455,0.174,0.00345976,0.00265646,0.0044541,0.00357271,8000
L0_asis_alap,alap,False,663,0,47.964,455,1.0,0.165688,0.158121,0.173609,0.164426,4000
L0_asis_alap,alap,False,663,0,47.964,455,0.5,0.114258,0.107972,0.120899,0.110984,4000
L0_asis_alap,alap,False,663,0,47.964,455,0.25,0.0345248,0.0310616,0.0383504,0.0323474,4000
L0_asis_alap,alap,False,663,0,47.964,455,0.174,0.0151955,0.0128886,0.0178733,0.0136954,4000
L1_seed,asap,False,588,0,44.24,412,1.0,0.146014,0.138909,0.153472,0.14989,4000
L1_seed,asap,False,588,0,44.24,412,0.5,0.0776707,0.0724855,0.0832127,0.0814008,4000
L1_seed,asap,False,588,0,44.24,412,0.25,0.0176116,0.0151306,0.0204619,0.0178837,4000
L1_seed,asap,False,588,0,44.24,412,0.174,0.00829211,0.00657786,0.0103861,0.00814562,4000
L2_order,asap,False,584,0,37.272,350,1.0,0.18985,0.18175,0.198303,0.190489,4000
L2_order,asap,False,584,0,37.272,350,0.5,0.124268,0.117713,0.131178,0.127404,4000
L2_order,asap,False,584,0,37.272,350,0.25,0.0462605,0.0422549,0.0506262,0.0463095,4000
L2_order,asap,False,584,0,37.272,350,0.174,0.0113986,0.00939587,0.0137762,0.0112632,4000
L3_rx,asap,True,356,226,34.068,349,1.0,0.216428,0.20778,0.225428,0.213106,4000
L3_rx,asap,True,356,226,34.068,349,0.5,0.158095,0.150702,0.16584,0.155492,4000
L3_rx,asap,True,356,226,34.068,349,0.25,0.0586865,0.0541772,0.0635543,0.0579117,4000
L3_rx,asap,True,356,226,34.068,349,0.174,0.0238246,0.0209436,0.0270715,0.0243143,4000
L4_all,alap,True,356,226,34.068,349,1.0,0.243696,0.23452,0.253224,0.242642,4000
L4_all,alap,True,356,226,34.068,349,0.5,0.180531,0.172632,0.188782,0.178805,4000
L4_all,alap,True,356,226,34.068,349,0.25,0.0683512,0.063486,0.0735739,0.0677443,4000
L4_all,alap,True,356,226,34.068,349,0.174,0.0290021,0.0258261,0.0325422,0.0278078,4000
L1_seed_alap,alap,False,588,0,44.24,412,1.0,0.216083,0.207442,0.225076,0.216958,4000
L1_seed_alap,alap,False,588,0,44.24,412,0.5,0.166034,0.158458,0.173962,0.163942,4000
L1_seed_alap,alap,False,588,0,44.24,412,0.25,0.0735287,0.0684832,0.0789313,0.0725077,4000
L1_seed_alap,alap,False,588,0,44.24,412,0.174,0.0334893,0.0300781,0.0372632,0.0311589,4000
```

#### (n2) Kingston pilot: the day's Aer prediction at r = 1 (echo T2) and r = 0.174 against the measurement

**Source:** `validation/H0_kpilot.json -> data.aer_at.<circuit>` (`r=1`, `r=0.174`) and `data.decision.f_pool`.

**Columns and units:** dimensionless clean fractions per shot; the measured pooled value 0.0413 matches the r = 0.174 end (about 0.041-0.046), not the echo end (about 0.21-0.24)

```csv
circuit,aer_f_at_r_1,aer_f_at_r_0.174
B0_ref06_k1,0.211397,0.0413219
B1_ref07_k1,0.226755,0.0457617
B0_ref06_k4,0.237881,0.0554602
"MEASURED pooled (kingston, 2026-10-02)",0.041293,
```


#### (o) H0_ddrep cells: the seven DD cells of 2026-10-06 against the 2026-10-02 values (ibm_kingston, job db29p6nr11fs7396e4ig, 2 circuits x 6 000 shots per cell)

**Source:** `validation/H0_ddrep.json -> data.cells.<cell>` (`f_pool`, `f_pool_95`, `excess_hits`, `reference_hits`, `accepted`, `n_pulses_per_circuit`, `R`, `R_95`, `class`, `null_ratio`) and, for the last two columns, `validation/H0_ddtest.json -> data.decision.cells.<cell>` (cells T0, T1, T3 only; M1-M4 did not exist on 2026-10-02).

**Columns and units:** `n_pulses_total` pulses inserted over the two circuits; `accepted` accepted shots and `reference_hits` reference-string hits summed over the two circuits (12 000 shots); `excess_hits` = reference hits minus the garbage expectation 2.93; `f` pooled reference-string clean fraction with its 95 % interval; `R` = excess hits of the cell over those of T0 (T0 = 1) with its 95 % interval; `class` COLLAPSED (upper end < 0.25), INTACT (lower end > 1) or INTERMEDIATE; `null_ratio` the ratio the pulse cost alone would give; `f_20261002`, `R_20261002` the same cell on 2026-10-02. Reading: R1 False, R2 False, C1 False; the mechanism reading is "no single hypothesis".

```csv
cell,description,n_pulses_total,accepted,reference_hits,excess_hits,f,f_lo95,f_hi95,R,R_lo95,R_hi95,class,null_ratio,f_20261002,R_20261002
T0,no DD (baseline),0,1134,716,713.07,0.0817751,0.0757532,0.0881453,1,,,,1,0.0400315,1
T1,context-aware staggered X (committed H0_ddtest QPY),1724,785,464,461.07,0.0528757,0.0480506,0.05805,0.646599,0.575131,0.726947,INTERMEDIATE,0.840694,0.000466785,0.0116604
T3,client XY4 in idle windows >= 1.024 us (committed H0_ddtest QPY),488,981,641,638.07,0.0731741,0.0674826,0.0792142,0.894821,0.804175,0.995684,INTERMEDIATE,0.953771,0.112853,2.81912
M1,T1 with alternating pulse signs (same timing),1724,859,565,562.07,0.0644584,0.059122,0.0701436,0.78824,0.705743,0.88038,INTERMEDIATE,0.840694,,
M2,XX pairs in T2's 194 windows (ratio 4.0),778,974,578,575.07,0.0659492,0.0605505,0.0716968,0.806471,0.722572,0.900111,INTERMEDIATE,0.922343,,
M3,M2 with alternating signs,778,997,636,633.07,0.0726007,0.0669319,0.0786181,0.887809,0.797696,0.988102,INTERMEDIATE,0.922343,,
M4,T1 minus all pulses on hot qubits 91 and 95,1228,1322,823,820.07,0.0940459,0.0875813,0.100858,1.15006,1.04024,1.27146,INTACT,0.879885,,
```

#### (p) Pulse trains: x-pulse over-rotation epsilon_q and per-pulse cost c_q per qubit (H0_ddrep)

**Source:** `validation/H0_ddrep.json -> data.trains.per_qubit.<qubit>` (`P1` readout-corrected, `epsilon`, `epsilon_68`, `c_per_pulse`, `c_68`, `x_error_record`, `c_over_x_error`, `epsilon_RB_level_sqrt_6_x_error`) and `data.hot_qubits`. Fit rule (fixed before the data): $c_q=(P_1(\mathrm{XpXm\text{-}128})-P_1(\mathrm{XX\text{-}8}))/120$, floor$_n=P_1(\mathrm{XX\text{-}8})+(n-8)c_q$, $\epsilon_q=\arg\min_{[0,\pi/8]}\sum_{n=8,32,128}(P_1(\mathrm{XX\text{-}}n)-\mathrm{floor}_n-\sin^2(n\epsilon/2))^2$ on a 0.0001 rad grid, 68 % intervals by a parametric bootstrap (2 000 draws, seed 32).

**Columns and units:** `P1_*` readout-corrected probability of measuring 1 after a train of 8, 32 or 128 pulses (XX = repeated $X$, XpXm = alternating $+X,-X$), dimensionless; `epsilon_rad` coherent over-rotation per $x$ pulse in radians with its 68 % interval; `eps_RB_level_sqrt6xerr_rad` the planner's reference $\sqrt{6\,x_{\rm error}}$ in radians; `c_per_pulse` incoherent cost per pulse (dimensionless probability) with its 68 % interval; `x_error_record` the calibration record's `x_error` (aliased to `sx_error`); `c_over_x_error` the ratio; `hot_qubit_M4` 1 for the two qubits whose pulses cell M4 removes. Summary: $\epsilon_q\ge0.01$ rad and XX-128 minus XpXm-128 $>0.05$ on 12 of 12 qubits; $c_q>3\,x_{\rm error}$ on qubits 71 and 91.

```csv
qubit,P1_XX8,P1_XX32,P1_XX128,P1_XpXm128,epsilon_rad,eps_lo68,eps_hi68,eps_RB_level_sqrt6xerr_rad,c_per_pulse,c_lo68,c_hi68,x_error_record,c_over_x_error,hot_qubit_M4
59,0.00644395,0.0663049,0.873495,0.0301848,0.0181,0.018,0.0182,0.0336174,0.000197841,0.000172546,0.000223164,0.000188355,1.05036,0
71,0.00675333,0.0482863,0.75688,0.0916765,0.0148,0.0147,0.015,0.0297698,0.000707693,0.000673183,0.000739775,0.000147707,4.79119,0
72,0.0125912,0.0759124,0.930657,0.0248175,0.0195,0.0193,0.0196,0.0287484,0.000101886,6.55568e-05,0.00013751,0.000137745,0.739667,0
73,0.0136387,0.0830565,0.921839,0.0556041,0.0186,0.0185,0.0187,0.0356369,0.000349711,0.000320728,0.000377923,0.000211665,1.6522,0
74,0.00929054,0.0923986,0.976182,0.035473,0.0204,0.0203,0.0206,0.0376763,0.000218187,0.000196906,0.000242609,0.000236584,0.922239,0
75,0.00632695,0.0536936,0.835328,0.0280438,0.0173,0.0172,0.0174,0.0296218,0.000180974,0.000155688,0.000205661,0.000146242,1.23749,0
79,0.00340948,0.0422775,0.766962,0.0368224,0.0159,0.0158,0.016,0.0377649,0.000278441,0.000252568,0.000303574,0.000237699,1.1714,0
91,0.00768425,0.0625218,0.936605,0.137269,0.0171,0.017,0.0173,0.0362902,0.00107987,0.00104258,0.00112035,0.000219497,4.91975,1
92,0.00194346,0.0284452,0.763604,0.0913428,0.0149,0.0148,0.015,0.0447153,0.000744994,0.000705252,0.000785669,0.000333243,2.23559,0
93,0.0131801,0.0755323,0.960122,0.0474823,0.0196,0.0195,0.0197,0.0340982,0.000285851,0.000259184,0.000313863,0.000193781,1.47512,0
94,0.000350816,0.0691107,0.92475,0.0443782,0.0189,0.0187,0.019,0.0320854,0.000366895,0.000331089,0.000403159,0.000171579,2.13834,0
95,0.0144416,0.0827876,0.951134,0.0654912,0.019,0.0189,0.0191,0.0301252,0.000425413,0.000392347,0.000454426,0.000151255,2.81255,1
```

#### (q) CV_2x3_plan cells: certificate widths, convergence steps, weight and the re-sizing multiplier (S1-proxy emulation, three seeds, maximum or minimum over seeds as the column says)

**Source:** `validation/CV_2x3_plan.json -> data.criteria_by_seed.<f>.<sector>.<seed>.{CV1,CV2,CV3,CV4,CV5}`, `data.cv3_at_2Nc_information`, `data.plan.<f>.<sector>.{resized_by, final_shots_total, final_jobs, final_hqc}`, `data.E_tol` ($E_{\rm tol}=1.4225\times10^{-2}$ at $B=0$, $1.1040\times10^{-2}$ at $B=1$; `data.constants` for the thresholds). Basis `B_all | refs` (`prompts/31` ruling 1). An emulation of the plan at clean fraction $0.7f$, not a device statement.

**Columns and units:** `s_final` re-sizing multiplier; `hqc_final` HQC (rounded to an integer) of the sector at that multiplier; `cv2_certificate` the certificate read (Kato-Temple with the exact $E_1$ at $B=0$, Weinstein at $B=1$) and `cv2_threshold` its width limit; `cv2_width_N_half_max_over_seeds` and `cv2_width_N_max` the worst width over seeds at $N/2$ and at $N$ (lattice energy units); `rH_*` the Weinstein half-width $r_H$ at the same points (information at $B=0$); `KT_width_*` the Kato-Temple width (information at $B=1$, where the cluster gap makes it uninformative); `cv1_ratio_max` $[E_R(N/2)-E_R(N)]/E_{\rm tol}$ (limit 1); `cv3_dE_k4_k5_max` $E_R(B^{(4)})-E_R(B^{(5)})$ at equal shots, `cv3_ratio_to_Etol_max` its ratio to $E_{\rm tol}$ (limit 1), `cv3_dE_at_2Nc_info_max` the same at $2N_c$ shots (information); `cv4_margin_over_Etol_min` (random 2.5th percentile minus $E_R$)/$E_{\rm tol}$ at $N$ (limit 1); `cv5_W_min` captured ground-state weight (limit 0.99).

```csv
f,sector,s_final,shots_final,jobs_final,hqc_final,cv2_certificate,cv2_threshold,cv2_width_N_half_max_over_seeds,cv2_width_N_max,rH_N_half_max,rH_N_max,KT_width_N_half_max,KT_width_N_max,cv1_ratio_max,cv3_dE_k4_k5_max,cv3_ratio_to_Etol_max,cv3_dE_at_2Nc_info_max,cv4_margin_over_Etol_min,cv5_W_min,all_cv1_to_cv5_ok
0.05,B=0,1,63875,35,317546,kato_temple_exact_E1,0.1,0.0194892,0.00973772,0.229696,0.162464,0.0194892,0.00973772,0.279115,0.00309976,0.217906,0.00145608,7.93132,0.999524,True
0.05,B=1,2,193600,29,962114,weinstein,0.15,0.118073,0.0853809,0.118073,0.0853809,0.616841,0.31201,0.132269,0.00291957,0.26445,0.00231958,4.73738,0.999859,True
0.10,B=0,1,34909,33,173614,kato_temple_exact_E1,0.1,0.0251712,0.011034,0.260939,0.172931,0.0251712,0.011034,0.449226,0.00960404,0.675141,0.00206,8.41479,0.999509,True
0.10,B=1,2,99000,20,491991,weinstein,0.15,0.143297,0.0837356,0.143297,0.0837356,0.946879,0.300009,0.166833,0.0033855,0.306653,0.00196274,5.19717,0.999854,True
0.15,B=0,1,27309,33,135860,kato_temple_exact_E1,0.1,0.0267184,0.0139266,0.268819,0.194232,0.0267184,0.0139266,0.364973,0.0029331,0.20619,0.00176459,8.36328,0.999281,True
0.15,B=1,2,67600,16,335941,weinstein,0.15,0.134337,0.107993,0.134337,0.107993,0.826125,0.513501,0.138849,0.00370291,0.335404,0.00287604,5.83481,0.999758,True
```

#### (q2) The B=1 re-sizing ladder: why s = 2 (s = 1.5 fails CV2 at every f)

**Source:** `validation/CV_2x3_plan.json -> data.resize_summary.<f>.B=1.<s>` (the grid was {1.5, 2, 3, 4, 6, 8}; $B=0$ passes at $s=1$ so its ladder is empty). Columns: `shots_total` the sector's shots at that multiplier; `cv2_width_half_max` the worst Weinstein $r_H(N/2)$ over seeds on `B_all` (limit 0.15), `cv2_width_full_max` at $N$; `rH_half_B_sig_max` the same on the signal support (information: the $B_{\rm sig}$ cut keeps the width above the limit, the reason for `prompts/31` ruling 1); `ok_all_seeds` and the four criteria flags.

```csv
f,sector,s_tried,shots_total,cv2_width_half_max,cv2_width_full_max,rH_half_B_all_max,rH_half_B_sig_max,ok_all_seeds,CV1,CV2,CV4,CV5
0.05,B=1,1.5,145650,0.156787,0.09236,0.156787,0.273303,False,True,False,True,True
0.05,B=1,2,193600,0.118073,0.0853809,0.118073,0.229369,True,True,True,True,True
0.10,B=1,1.5,74700,0.166921,0.104398,0.166921,0.225461,False,True,False,True,True
0.10,B=1,2,99000,0.143297,0.0837356,0.143297,0.210536,True,True,True,True,True
0.15,B=1,1.5,51150,0.155289,0.111444,0.155289,0.222578,False,True,False,True,True
0.15,B=1,2,67600,0.134337,0.107993,0.134337,0.202807,True,True,True,True,True
```

#### (r) The oracle-width table: what the exact ground-state support of weight 1 - eps can certify (2x3, g^2 = 4)

**Source:** `validation/CV_2x3_plan.json -> data.oracle_width.<sector>.rows.<eps>` (reproduces the planner prototype `scratch/planner/oracle_width_20261005.json` to $3.2\times10^{-14}$, 196 fields; `data.oracle_width_reproduction`). `E1` is the exact first excited level (the $B=0$ gap $E_1-E_0=2.714$; at $B=1$ the cluster gap is 0.0244). For each cut $S_\varepsilon$ (the smallest set carrying $1-\varepsilon$ of the ground-state weight, plus the references) the table gives the Ritz error and the certificates of the *oracle* basis, i.e. the best any support of that size can do.

**Columns and units:** `eps` the weight cut; `size_S_eps_union_refs` number of states; `ER_minus_E0` Ritz error (lattice units); `rH` Hamiltonian residual = Weinstein half-width; `rH_estimate` the planner's estimate $\sqrt{\sum_{n\notin B}(E_0-H_{nn})^2|\Omega_n|^2}$; `W` captured weight and `one_minus_W`; `kt_width_exact_E1` Kato-Temple width $r_H^2/(E_1-E_R)$ (blank where the Ritz value is not below $E_1$, so the bound does not apply); `gap_holds` whether $r_H<E_1-E_R$. At $B=0$ even the oracle $S_{999}$ has $r_H=0.265$ and the Weinstein width reaches 0.1 only at $\varepsilon=10^{-4}$ (173 states); the Kato-Temple width is $0.0259$ already at $S_{999}$.

```csv
sector,eps,size_S_eps_union_refs,ER_minus_E0,rH,rH_estimate,W,one_minus_W,kt_width_exact_E1,gap_holds
B=0,0.01,31,0.0579401,0.608693,0.753279,0.990595,0.00940546,0.139495,True
B=0,0.001,86,0.00805673,0.264705,0.304772,0.999037,0.000962875,0.0258945,True
B=0,0.0003,116,0.00240824,0.144916,0.168288,0.999703,0.000297298,0.00774474,True
B=0,0.0001,173,0.000977034,0.100163,0.110841,0.9999,9.97644e-05,0.00369792,True
B=0,3e-05,231,0.000293686,0.0557288,0.0612972,0.999971,2.94854e-05,0.00114445,True
B=0,1e-05,288,0.000102949,0.0334254,0.0364659,0.99999,9.97844e-06,0.00041168,True
B=0,1e-06,429,1.21832e-05,0.0124195,0.0129707,0.999999,9.96221e-07,5.68332e-05,True
B=1,0.01,42,0.0526099,0.553735,0.682156,0.990385,0.00961541,,False
B=1,0.001,95,0.00716494,0.235486,0.269152,0.999027,0.000972936,3.22564,False
B=1,0.0003,130,0.0022323,0.132281,0.147202,0.9997,0.000299678,0.790908,False
B=1,0.0001,165,0.000878776,0.0901342,0.0982597,0.999903,9.74948e-05,0.346038,False
B=1,3e-05,211,0.000293714,0.0547243,0.0580958,0.999971,2.94745e-05,0.124456,False
B=1,1e-05,242,0.000103058,0.0331099,0.0345999,0.99999,9.87792e-06,0.0452007,False
B=1,1e-06,306,1.12374e-05,0.011571,0.0119051,0.999999,9.66837e-07,0.00549961,True
```

#### (s) The K1 pilot: 2x3 on ibm_kingston (job db2avbe8v0ts73c2i8b0), the two signed k = 1 circuits, 10^5 shots each

**Source:** `validation/K1_2x3_fpilot.json -> data.circuits.<circuit>`, `data.pooled`, `data.decision`, `data.prediction_prereg`. Pooled result: 0 reference hits in $2\times10^5$ shots against 0.190735 expected from garbage; $f_{\rm hit}=-1.2528\times10^{-6}$ with 95 % interval [$-1.2528\times10^{-6}$, $2.2977\times10^{-5}$]; $\hat f_{\rm ideal}=-1.1235\times10^{-6}$, 95 % upper end $2.0605\times10^{-5}$; decision NO-GO, firm (GO-B $\ge10^{-3}$, GO-A $\ge3\times10^{-4}$); readout minimum diagonal 0.9358; 188.0 s billed; account 273 s left.

**Columns and units:** `reference_int_index` the circuit's reference configuration; `p_reference` its ideal output probability (dimensionless); `garbage_acceptance_a` the decoder's random acceptance of 20-qubit strings; `routed_cz` CZ count after routing; `scheduled_duration_us` ALAP duration in $\mu$s; `n_xy4_pulses` inserted pulses; `accepted` accepted shots of $10^5$ (garbage level is $10^5a$ = 64.6 and 40.6); `distinct_accepted` distinct accepted strings; `garbage_expected_ref_hits` $=10^5\times2^{-20}$; `f_hit_hi95`, `f_hat_ideal_hi95` 95 % upper ends; `pred_f_gates_layout_no_idle` the preregistered gate-only prediction on the routed layout and `pred_expected_ref_hits_no_idle` the hits it implies (including garbage); the idle-aware ends of the bracket predict garbage only (0.0954 hits per circuit).

```csv
circuit,sector,reference_int_index,p_reference,sector_dim,garbage_acceptance_a,routed_cz,scheduled_duration_us,n_xy4_pulses,shots,accepted,distinct_accepted,garbage_expected_ref_hits,reference_hits,f_hit_hi95,f_hat_ideal_hi95,pred_f_gates_layout_no_idle,pred_expected_ref_hits_no_idle
B0_ref117_k1,B=0,117,0.928357,677,0.000645638,5659,411.152,2408,100000,58,57,0.0953674,0,4.72052e-05,4.23314e-05,1.67113e-05,1.36752
B1_ref29_k1,B=1,29,0.928308,426,0.000406265,5659,410.768,2404,100000,45,42,0.0953674,0,4.72077e-05,4.23336e-05,1.67429e-05,1.36986
```

#### (t) K0: the 2x3 circuit B0_ref25_k1 routed onto ibm_kingston, on two calibration records (a model, not a measurement)

**Source:** `validation/K0_2x3_2x4.json -> data.2x3.committed` and `data.2x3.live` (the verdict record is `committed`, the 2026-10-02 record; `live` is the 2026-10-06 06:52Z record). `S_idle` in nats; `f_idle_aware_*` $=f_{\rm gates}e^{-S_{\rm idle}}$ on the ALAP schedule at the echo $T_2$ and at $T_2^*=0.174\,T_2^{\rm echo}$ (without the 2x2-transferred XY4 gain, which did not replicate). `f_ceiling_2q` $=(1-\epsilon_{2,\min})^{n_{CZ}}$ with the record's best CZ error; `f_best_patch_bound` best CZ, one-qubit and readout error everywhere; `f_gates_layout` the gate-and-readout product on the chosen layout. This block supersedes the IBM row of block (f) (5 477 CZ, ceiling $1.14\times10^{-2}$), which used the plain level-3 circuit that is not exact.

```csv
record,stamp,fingerprint8,last_update_date,routed_cz,active_qubits,alap_duration_us,eps2_min,f_ceiling_2q,f_best_patch_bound,f_gates_layout,S_idle_echo_nats,f_idle_aware_echo,S_idle_T2star_nats,f_idle_aware_T2star,eps2_needed_for_f_0.05,best_edge_misses_by_factor,garbage_ref_hits_per_circuit_1e5_shots,exactness_max_abs_delta,leakage
committed,20261002T1906Z,e4ecac38,2026-10-02T13:06:57-06:00,5659,21,410.256,0.000816415,0.00983329,0.0029669,6.06884e-06,24.774,1.05654e-16,74.169,3.73174e-38,0.000529375,1.54223,0.0954,1.47019e-12,2.04281e-13
live,20261006T0652Z,b948ddc8,2026-10-06T00:52:19-06:00,5659,21,411.152,0.000883702,0.00671723,0.00204042,1.67078e-05,23.0309,1.66237e-15,67.9413,5.20442e-35,0.000529375,1.66933,0.0954,1.61297e-12,2.01505e-13
```

#### (u) Calibration-record statistics of ibm_kingston on the two K0 records (day-to-day variation)

**Source:** `validation/K0_2x3_2x4.json -> data.records.<record>.stats`. Between the 2026-10-02 and 2026-10-05/06 full records 1 110 leaves changed in the six families (`data/hardware/H0_ddrep_prep/live.json -> diff_against`: ratios 0.102 to 111.3). Columns: CZ error statistics over the 342 calibrated CZ keys (dimensionless), median $\sqrt{x}$ and readout errors, median $T_1$ and $T_2$ in $\mu$s, and the minima of `x_error` and `sx_error` (equal: the record aliases the two). The medians move by about 1.5 to 7 percent (my reading of the table); the single-circuit clean fraction moved by 2.04x (block (o)), so the record's summary statistics do not carry the variation that matters.

```csv
record,stamp,cz_error_min,cz_error_p10,cz_error_median,cz_error_mean,sx_error_median,measure_error_median,T1_median_us,T2_median_us,x_error_min,sx_error_min,n_cz_calibrated,n_cz_uncalibrated
committed,20261002T1906Z,0.000816415,0.00114591,0.00180416,0.00549304,0.00024671,0.00897217,228.897,147.265,9.99091e-05,9.99091e-05,342,10
live,20261006T0652Z,0.000883702,0.00125281,0.00188416,0.00576294,0.000242951,0.00836182,220.859,137.054,9.80754e-05,9.80754e-05,342,10
```


#### (v) f-cells: pooled k=1 clean fraction of the 2x3 Stage-E circuits for every scenario and optimisation variant (45 cells, simulation)

**Source:** `validation/C4_FCELLS_A.json -> data.cells`, `validation/C4_FCELLS_B.json -> data.cells` (`stats.pooled_k1`, `f0`, `seconds`)

**Columns and units:** `token` source gate; `scenario` E1-E5c, E6a-c, E7_0.05..0.15; `family` NAT-O0 (no optimisation) or the exact variant O1-O4 as NAT-O1.. (dimensionless probabilities per shot); `f0_k1` analytic fault-free fraction (mean of the two k=1 circuits, Aer convention); `n_ref_hits` reference-string hits in `shots_k1` = 1 600 k=1 shots; `f_hit`, `f_hit_lo`, `f_hit_hi` the reference-hit fraction with its 95 % Garwood interval; `f_hat_ideal*` = f_hit / 1.1151 (r_nc) with interval; `seconds` GPU seconds for the cell (2 000 shots)

The 32 cells dropped from `C4_FCELLS_A` by the budget rule (E4/E5 x O1, every O2/O3/O4/O6 cell) are absent. In `C4_FCELLS_A` the E2 and E3 cells of O1 reproduce the O0 pooled hit counts exactly (a coincidence of sums, different seeds).

```csv
token,scenario,family,f0_k1,n_ref_hits,shots_k1,f_hit,f_hit_lo,f_hit_hi,f_hat_ideal,f_hat_ideal_lo,f_hat_ideal_hi,seconds
C4_FCELLS_A,E1,NAT-O0,0.172226,338,1600,0.231225,0.207228,0.257237,0.207351,0.185832,0.230678,58.4
C4_FCELLS_A,E2,NAT-O0,0.186959,391,1600,0.267482,0.241623,0.295354,0.239865,0.216676,0.26486,57.9
C4_FCELLS_A,E3,NAT-O0,0.0611298,166,1600,0.113559,0.0969411,0.132209,0.101835,0.0869321,0.118559,151.8
C4_FCELLS_A,E4,NAT-O0,0.185817,373,1600,0.255168,0.229927,0.282424,0.228822,0.206187,0.253264,153.5
C4_FCELLS_A,E5a,NAT-O0,0.163189,344,1600,0.235329,0.211115,0.261559,0.211032,0.189318,0.234554,302.5
C4_FCELLS_A,E5b,NAT-O0,0.152968,357,1600,0.244222,0.219543,0.270917,0.219007,0.196875,0.242946,302.4
C4_FCELLS_A,E5c,NAT-O0,0.107177,316,1600,0.216174,0.192994,0.241372,0.193855,0.173068,0.216451,302.2
C4_FCELLS_A,E1,NAT-O1,0.172164,373,1600,0.255168,0.229927,0.282424,0.228822,0.206187,0.253264,51.3
C4_FCELLS_A,E2,NAT-O1,0.186888,391,1600,0.267482,0.241623,0.295354,0.239865,0.216676,0.26486,51.2
C4_FCELLS_A,E3,NAT-O1,0.061073,166,1600,0.113559,0.0969411,0.132209,0.101835,0.0869321,0.118559,146.3
C4_FCELLS_B,E6a,NAT-O0,0.415069,771,1600,0.527439,0.490861,0.566021,0.472983,0.440181,0.507581,57.8
C4_FCELLS_B,E6b,NAT-O0,0.0296225,99,1600,0.0677248,0.0550432,0.0824527,0.0607324,0.0493601,0.0739397,58.1
C4_FCELLS_B,E6c,NAT-O0,0.00087286,12,1600,0.00820815,0.00424076,0.0143388,0.00736067,0.00380292,0.0128583,57.5
C4_FCELLS_B,E7_0.05,NAT-O0,0.0614332,160,1600,0.109455,0.0931517,0.12779,0.0981539,0.083534,0.114596,57.8
C4_FCELLS_B,E7_0.07,NAT-O0,0.0842146,233,1600,0.159394,0.139583,0.181229,0.142937,0.125171,0.162517,58.2
C4_FCELLS_B,E7_0.10,NAT-O0,0.117652,256,1600,0.175128,0.154331,0.197948,0.157047,0.138396,0.17751,57.2
C4_FCELLS_B,E7_0.15,NAT-O0,0.172058,380,1600,0.259957,0.234473,0.287454,0.233117,0.210264,0.257775,57.3
C4_FCELLS_B,E6a,NAT-O1,0.414995,735,1600,0.502812,0.467114,0.540515,0.450898,0.418885,0.484708,50.6
C4_FCELLS_B,E6b,NAT-O1,0.0296014,96,1600,0.0656725,0.0531947,0.0801976,0.0588919,0.0477025,0.0719174,50.6
C4_FCELLS_B,E6c,NAT-O1,0.000871614,9,1600,0.00615585,0.00281428,0.0116867,0.00552027,0.00252371,0.01048,50.6
C4_FCELLS_B,E7_0.05,NAT-O1,0.0614112,162,1600,0.110823,0.0944142,0.129264,0.0993808,0.0846661,0.115918,49.9
C4_FCELLS_B,E7_0.07,NAT-O1,0.0841845,205,1600,0.140239,0.121698,0.160807,0.12576,0.109133,0.144204,50.5
C4_FCELLS_B,E7_0.10,NAT-O1,0.11761,276,1600,0.18881,0.16719,0.212451,0.169316,0.149928,0.190516,50.6
C4_FCELLS_B,E7_0.15,NAT-O1,0.171996,349,1600,0.23875,0.214355,0.265159,0.214099,0.192224,0.237782,50.6
C4_FCELLS_B,E6a,NAT-O2,0.415242,741,1600,0.506917,0.47107,0.544767,0.454579,0.422433,0.488521,44.8
C4_FCELLS_B,E6b,NAT-O2,0.0296717,81,1600,0.055411,0.0440041,0.0688711,0.0496899,0.0394608,0.0617603,43.9
C4_FCELLS_B,E6c,NAT-O2,0.000875762,14,1600,0.00957635,0.005235,0.0160682,0.00858761,0.0046945,0.0144092,43.9
C4_FCELLS_B,E7_0.05,NAT-O2,0.0614842,149,1600,0.10193,0.0862203,0.119673,0.0914057,0.0773183,0.107317,44
C4_FCELLS_B,E7_0.07,NAT-O2,0.0842845,207,1600,0.141608,0.122972,0.162269,0.126987,0.110276,0.145515,44.3
C4_FCELLS_B,E7_0.10,NAT-O2,0.117749,252,1600,0.172392,0.151762,0.195043,0.154593,0.136093,0.174906,42.9
C4_FCELLS_B,E7_0.15,NAT-O2,0.1722,357,1600,0.244222,0.219543,0.270917,0.219007,0.196875,0.242946,44.8
C4_FCELLS_B,E6a,NAT-O3,0.415146,694,1600,0.474764,0.440094,0.511439,0.425746,0.394655,0.458634,44.6
C4_FCELLS_B,E6b,NAT-O3,0.0296443,95,1600,0.0649884,0.0525793,0.0794452,0.0582785,0.0471506,0.0712426,44.7
C4_FCELLS_B,E6c,NAT-O3,0.000874144,5,1600,0.00341945,0.00110958,0.00798125,0.0030664,0.00099502,0.00715721,44.2
C4_FCELLS_B,E7_0.05,NAT-O3,0.0614558,177,1600,0.121085,0.103903,0.140296,0.108583,0.093175,0.125811,44.8
C4_FCELLS_B,E7_0.07,NAT-O3,0.0842455,191,1600,0.130662,0.112788,0.150564,0.117171,0.101143,0.135019,44.6
C4_FCELLS_B,E7_0.10,NAT-O3,0.117695,269,1600,0.184022,0.162686,0.207378,0.165022,0.145889,0.185967,45.1
C4_FCELLS_B,E7_0.15,NAT-O3,0.172121,324,1600,0.221647,0.198167,0.247144,0.198763,0.177707,0.221627,44.9
C4_FCELLS_B,E6a,NAT-O4,0.415146,734,1600,0.502128,0.466454,0.539806,0.450284,0.418294,0.484072,45.2
C4_FCELLS_B,E6b,NAT-O4,0.0296443,88,1600,0.0601997,0.0482817,0.0741679,0.0539842,0.0432967,0.0665103,44.5
C4_FCELLS_B,E6c,NAT-O4,0.000874144,14,1600,0.00957635,0.005235,0.0160682,0.00858761,0.0046945,0.0144092,44.5
C4_FCELLS_B,E7_0.05,NAT-O4,0.0614558,151,1600,0.103298,0.087479,0.121151,0.0926327,0.078447,0.108642,44.9
C4_FCELLS_B,E7_0.07,NAT-O4,0.0842455,192,1600,0.131346,0.113423,0.151296,0.117785,0.101713,0.135675,45
C4_FCELLS_B,E7_0.10,NAT-O4,0.117695,250,1600,0.171024,0.150479,0.193591,0.153366,0.134942,0.173603,43.9
C4_FCELLS_B,E7_0.15,NAT-O4,0.172121,357,1600,0.244222,0.219543,0.270917,0.219007,0.196875,0.242946,45.3
```

#### (v2) Noise-scenario parameters of the class-4 f-cells

**Source:** `validation/C4_FCELLS_A.json`, `C4_FCELLS_B.json -> data.noise_descriptions`

**Columns and units:** `scenario` id; `class` channel class; `p2`,`p1` Aer depolarizing parameters for two- and one-qubit gates; `p10`,`p01` readout flip probabilities P(1|0), P(0|1); `p_init` initialisation flip; `p_mem` memory Z probability per two-qubit layer; `t_round_s` assumed round time (s); `scale` error scale; `f_target` gate-only matched f; `angle_a`,`angle_b` coefficients of p2(theta) = (a|theta|/pi + b) p2

```csv
scenario,class,p2,p1,p10,p01,p_init,p_mem,t_round_s,scale,f_target,angle_a,angle_b
E1,depolarizing + readout,0.00083,2.8e-05,0.00067,0.0012,,,,,,,
E2,depolarizing + readout,0.00079,3e-05,0.00048,0.00048,,,,,,,
E3,emulator parameter set (H2-2E 2025-07-16),0.00129,7.3e-05,0.0009,0.0018,4e-05,,,,,1.518,0.241
E4,emulator parameter set (Helios-1E 2025-11-18),0.0008,2.5e-05,1e-06,1e-06,0.0005,,,,,1.518,0.241
E5a,E1 + memory (transport/idle) dephasing,0.00083,2.8e-05,0.00067,0.0012,,1.4e-06,0.0005,,,,
E5b,E1 + memory (transport/idle) dephasing,0.00083,2.8e-05,0.00067,0.0012,,3.08e-06,0.0011,,,,
E5c,E1 + memory (transport/idle) dephasing,0.00083,2.8e-05,0.00067,0.0012,,1.232e-05,0.0044,,,,
E6a,depolarizing + readout,0.000415,1.4e-05,0.000335,0.0006,,,,0.5,,,
E6b,depolarizing + readout,0.00166,5.6e-05,0.00134,0.0024,,,,2,,,
E6c,depolarizing + readout,0.00332,0.000112,0.00268,0.0048,,,,4,,,
E7_0.05,depolarizing + readout,0.00133902,2.8e-05,0.00067,0.0012,,,,,0.05,,
E7_0.07,depolarizing + readout,0.0011833,2.8e-05,0.00067,0.0012,,,,,0.07,,
E7_0.10,depolarizing + readout,0.0010182,2.8e-05,0.00067,0.0012,,,,,0.1,,
E7_0.15,depolarizing + readout,0.000830483,2.8e-05,0.00067,0.0012,,,,,0.15,,
```

#### (w) C2_CAL arms: PTA / RM / Kraus against the K1 device strings (run 3, job 59736871)

**Source:** `validation/C2_CAL.json -> data.arms.<arm>.structure`, `data.comparisons.P4c_vs_K1`, `data.K1_device_structure`

**Columns and units:** `arm`; `shots` done; `wall_s` seconds; `s_per_shot` at the largest chunk (s); `mean_weight` mean Hamming weight of the 20 measured bits (unital limit 10); `se` its standard error; `deficit_vs_10` = 10 - mean_weight; `accepted`,`ref_hits` decoder-accepted strings and reference hits; `z_weight` = (mean_sim - mean_device)/sqrt(se^2 + se_dev^2); `max_abs_z_marginal` largest |z| over the 20 per-bit marginals. The simulated arms sample circuit IBM-T0, the device row circuit IBM-T3 (the XY4 pulses in the delays). For the device row `accepted` is the K1 `B0_ref117_k1` value 58 (`validation/K1_2x3_fpilot.json`)

```csv
arm,shots,wall_s,s_per_shot,mean_weight,se,deficit_vs_10,accepted,ref_hits,z_weight_vs_device,max_abs_z_marginal
pta,512,151,0.287007,9.95703,0.102132,0.0429688,0,0,1.81714,2.8744
rm,1024,387.9,0.353922,7.41992,0.0766178,2.58008,4,0,-30.553,44.475
kraus,640,1224.3,1.84019,2.39844,0.13585,7.60156,1,0,-54.195,64.2259
device_K1_T3,100000,,,9.77099,0.00714757,0.22901,58,0,,
```

#### (w2) C2_CAL per-bit marginals P(1)

**Source:** `validation/C2_CAL.json -> data.arms.<arm>.structure.marginals_by_clbit`, `data.K1_device_structure`

**Columns and units:** `clbit` bit index; `physical_qubit` the ibm_kingston qubit read into that bit; `pta`,`rm`,`kraus` simulated P(1) (probabilities); `device_T3` device P(1) from 10^5 shots

```csv
clbit,physical_qubit,pta,rm,kraus,device_T3
0,92,0.507812,0.238281,0.0890625,0.50707
1,69,0.527344,0.144531,0.0421875,0.49856
2,54,0.503906,0.120117,0.0578125,0.47731
3,52,0.464844,0.245117,0.0859375,0.48498
4,53,0.511719,0.518555,0.142187,0.49821
5,68,0.535156,0.0908203,0.0328125,0.49634
6,73,0.486328,0.429688,0.151562,0.44523
7,94,0.453125,0.392578,0.1,0.49545
8,50,0.492188,0.410156,0.128125,0.49939
9,72,0.515625,0.504883,0.184375,0.4922
10,71,0.523438,0.4375,0.1375,0.45983
11,79,0.484375,0.399414,0.134375,0.47248
12,51,0.517578,0.498047,0.171875,0.49226
13,74,0.451172,0.459961,0.140625,0.48605
14,70,0.511719,0.40918,0.121875,0.47336
15,93,0.474609,0.398438,0.117188,0.50373
16,75,0.5,0.439453,0.176563,0.50188
17,58,0.480469,0.393555,0.13125,0.4789
18,95,0.453125,0.451172,0.114062,0.50544
19,59,0.5625,0.438477,0.139063,0.50232
```

#### (x) The clean-fraction landscape: device x lattice (models, vendor figures, simulations and measurements kept apart by `kind`)

**Source:** `data/quantinuum/devices_20261002.json -> rows` (gate-only and memory scenarios), `validation/C4_FCELLS_A.json`, `C4_FCELLS_B.json` (simulation), the measurement gates named in `source`, `data/ionq_2x3_feasibility_20261001.json`, and (updated 2026-10-15) the committed native 2x2 values `validation/Q0P_2x2.json`, the 2x2 simulation `validation/QN_2x2.json`, the 2x4 analytics `validation/QN_2x4.json` and my pooling of the class-4 runs (block (ag)) (worktree `q35`, now merged,)

**Columns and units:** `device`; `lattice`; `statistic` what the number is; `value`; `lo`,`hi` the 95 % interval where one exists (dimensionless probabilities per shot); `kind` model / ESTIMATE / simulation / measured / executor-reported; `source`. **Do not draw the `measured`, `simulation` and `model` kinds as one series**; the signed bar is 0.1 (mean) and 0.05 (worst). The device-table gate-only values use the vendor error as the full fault probability; the Aer simulations use Aer's convention (Section 2.12)

```csv
device,lattice,statistic,value,lo,hi,kind,source
Quantinuum H2-2,2x3,"gate-only analytic (device table, pre-native counts)",0.150157,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x3,gate-only with memory scenario low (ESTIMATE),0.145378,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x3,gate-only with memory scenario mid (ESTIMATE),0.139845,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x3,gate-only with memory scenario high (ESTIMATE),0.112966,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x3,"gate-only analytic (device table, pre-native counts)",0.164197,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x3,gate-only with memory scenario low (ESTIMATE),0.137837,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x3,gate-only with memory scenario mid (ESTIMATE),0.111728,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x3,gate-only with memory scenario high (ESTIMATE),0.0352008,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x3,"gate-only analytic (device table, pre-native counts)",0.111327,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x3,gate-only with memory scenario low (ESTIMATE),0.104918,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x3,gate-only with memory scenario mid (ESTIMATE),0.097713,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x3,gate-only with memory scenario high (ESTIMATE),0.0660704,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x3,"gate-only analytic (device table, pre-native counts)",0.0860245,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x3,gate-only with memory scenario low (ESTIMATE),0.0815105,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x3,gate-only with memory scenario mid (ESTIMATE),0.0764053,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x3,gate-only with memory scenario high (ESTIMATE),0.0535337,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x2,"gate-only analytic (device table, pre-native counts)",0.787461,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x2,gate-only with memory scenario low (ESTIMATE),0.786953,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x2,gate-only with memory scenario mid (ESTIMATE),0.786344,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x2,gate-only with memory scenario high (ESTIMATE),0.783003,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x2,"gate-only analytic (device table, pre-native counts)",0.799066,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x2,gate-only with memory scenario low (ESTIMATE),0.796282,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x2,gate-only with memory scenario mid (ESTIMATE),0.792953,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x2,gate-only with memory scenario high (ESTIMATE),0.774892,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x2,"gate-only analytic (device table, pre-native counts)",0.751405,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x2,gate-only with memory scenario low (ESTIMATE),0.750683,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x2,gate-only with memory scenario mid (ESTIMATE),0.749818,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x2,gate-only with memory scenario high (ESTIMATE),0.745078,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x2,"gate-only analytic (device table, pre-native counts)",0.737831,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x2,gate-only with memory scenario low (ESTIMATE),0.737038,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x2,gate-only with memory scenario mid (ESTIMATE),0.736088,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x2,gate-only with memory scenario high (ESTIMATE),0.730883,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x4,"gate-only analytic (device table, pre-native counts)",1.48377e-27,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x4,gate-only with memory scenario low (ESTIMATE),2.95191e-28,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x4,gate-only with memory scenario mid (ESTIMATE),4.25194e-29,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x4,gate-only with memory scenario high (ESTIMATE),1.00057e-33,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x4,"gate-only analytic (device table, pre-native counts)",1.85354e-26,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x4,gate-only with memory scenario low (ESTIMATE),2.97363e-30,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x4,gate-only with memory scenario mid (ESTIMATE),8.31054e-35,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum Helios-1,2x4,gate-only with memory scenario high (ESTIMATE),7.49048e-60,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x4,"gate-only analytic (device table, pre-native counts)",3.28274e-31,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x4,gate-only with memory scenario low (ESTIMATE),1.70054e-32,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x4,gate-only with memory scenario mid (ESTIMATE),4.87312e-34,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H1-1,2x4,gate-only with memory scenario high (ESTIMATE),1.59412e-42,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x4,"gate-only analytic (device table, pre-native counts)",3.41418e-35,,,vendor-published rates; model,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x4,gate-only with memory scenario low (ESTIMATE),2.31481e-36,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x4,gate-only with memory scenario mid (ESTIMATE),9.16195e-38,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-1,2x4,gate-only with memory scenario high (ESTIMATE),1.77048e-45,,,ESTIMATE,data/quantinuum/devices_20261002.json rows
Quantinuum H2-2,2x2,gate-only analytic (native 252 ZZPhase),0.7929,,,model (gate),validation/Q0P_2x2.json Q5
Quantinuum Helios-1,2x2,gate-only analytic (native 252 ZZPhase),0.8046,,,model (gate),validation/Q0P_2x2.json Q5
Quantinuum H1-1,2x2,gate-only analytic (native 252 ZZPhase),0.756,,,model (gate),validation/Q0P_2x2.json Q5
Quantinuum H2-1,2x2,gate-only analytic (native 252 ZZPhase),0.7429,,,model (gate),validation/Q0P_2x2.json Q5
Aer E1 (H2-2 published),2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.2074,0.1858,0.2307,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E2 (Helios-1 published),2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.2399,0.2167,0.2649,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E3 (H2-2E emulator set),2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.1018,0.0869,0.1186,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E4 (Helios-1E set),2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.2288,0.2062,0.2533,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E5a E1+memory 0.5 ms,2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.211,0.1893,0.2346,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E5b E1+memory 1.1 ms,2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.219,0.1969,0.2429,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E5c E1+memory 4.4 ms,2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.1939,0.1731,0.2165,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E6a errors x0.5,2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.473,0.4402,0.5076,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E6b errors x2,2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.0607,0.0494,0.0739,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
Aer E6c errors x4,2x3,"f_hat_ideal = f_hit/1.1151 (k=1 circuits, simulation)",0.0074,0.0038,0.0129,simulation,"validation/C4_FCELLS_A.json, C4_FCELLS_B.json"
IBM ibm_kingston 2026-10-02,2x2,"f_hit, no DD (H0_ddtest T0)",0.04,0.0358,0.0446,measured,validation/H0_ddtest.json
IBM ibm_kingston 2026-10-02,2x2,"f_hit, client XY4 (H0_ddtest T3)",0.1129,0.1058,0.1203,measured,validation/H0_ddtest.json
IBM ibm_kingston 2026-10-02,2x2,"f_hit pooled 7 k=1 circuits, full run (XY4)",0.1271,0.1084,0.1479,measured,validation/H0_2x2.json
IBM ibm_kingston 2026-10-06,2x2,"f_hit, no DD (H0_ddrep T0)",0.0818,0.0758,0.0881,measured,validation/H0_ddrep.json
IBM ibm_kingston 2026-10-06,2x2,"f_hit, client XY4 (H0_ddrep T3)",0.0732,0.0675,0.0792,measured,validation/H0_ddrep.json
IBM ibm_fez 2026-09-22,2x2,reference-string clean fraction (6 hits in 8 267 shots),0.000665,0.00026,0.0011,measured (1-sigma-ish range),validation/H0_model.json
IBM ibm_kingston 2026-10-06,2x3,"f_hat_ideal, 0 hits in 2e5 shots (upper 95 % bound)",,,2.06e-05,measured,validation/K1_2x3_fpilot.json
IBM ibm_kingston committed record,2x3,two-qubit factor ceiling on the routed circuit (committed 2026-10-02 record),0.009833,,,model,validation/K0_2x3_2x4.json
IonQ Forte,2x2,gate-only analytic,0.303,,,vendor-published rates; model,data/ionq_2x3_feasibility_20261001.json / reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md
IonQ Forte,2x3,"gate-only analytic, virtual Rz",8.608e-05,,,vendor-published rates; model,data/ionq_2x3_feasibility_20261001.json
IonQ Tempo (projection),2x3,99.9 % target,0.077,,,projection,reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md
Quantinuum H2-2,2x4,gate-only analytic (opt-3 source 69676 ZZ),5.78e-27,,,model (gate),validation/QN_2x4.json data.analytic.devices_by_source.opt3
Quantinuum H2-2,2x4,gate-only analytic (structured source 71548 ZZ),4.18e-29,,,model (gate),validation/QN_2x4.json data.analytic.devices_by_source.structured
Quantinuum Helios-1,2x4,gate-only analytic (opt-3 source),7.95e-26,,,model (gate),same
Quantinuum Helios-1,2x4,gate-only analytic (structured source),4.87e-28,,,model (gate),same
Quantinuum H2-2 (E1 model),2x2,mean k=1 f_hit over 7 circuits (2 000 shots each),0.8378,0.826,0.846,simulation (range of the 7 cells; MY mean),validation/QN_2x2.json data.fcells.per_scenario.E1
Quantinuum Helios-1 (E2 model),2x2,mean k=1 f_hit,0.8418,0.829,0.858,simulation (range; MY mean),validation/QN_2x2.json E2
Quantinuum H2-2E parameters (E3 model),2x2,mean k=1 f_hit,0.7666,0.749,0.781,simulation (range; MY mean),validation/QN_2x2.json E3
matched f = 0.10 at 2x2 counts (E7 lattice),2x2,mean k=1 f_hit,0.1762,0.154,0.201,simulation (range; MY mean),validation/QN_2x2.json E7_0.10_lat
Quantinuum H2-2 (E1 model),2x3,pooled f_hat_ideal of full run F1_B0 (27 309 shots),0.2281,0.2085,0.2490,simulation,validation/C4_F1_B0.json data.frun.clean_fraction.pooled_k1
Quantinuum H2-2 (E1 model),2x3,pooled f_hat_ideal of full run F1_B1 (2 parts),0.2177,0.1969,0.2401,simulation (MY pooling),block (ag)
matched E7(0.07),2x3,pooled f_hat_ideal F5_B0,0.1296,0.1149,0.1455,simulation,validation/C4_F5_B0.json
matched E7(0.07),2x3,pooled f_hat_ideal F5_B1 (2 parts),0.1167,0.1017,0.1334,simulation (MY pooling),block (ag)
matched E7(0.10),2x3,pooled f_hat_ideal F4 B=0 (4 files),0.1682,0.1646,0.1719,simulation (MY pooling),block (ag)
matched E7(0.10),2x3,pooled f_hat_ideal F4 B=1 (4 files),0.1627,0.1593,0.1663,simulation (MY pooling),block (ag)
gate-S3 model E8 (IR-L3-RZZ),2x3,pooled f_hat_ideal F8 B=0 (4 files),0.1199,0.1169,0.1229,simulation (MY pooling),block (ag)
gate-S3 model E8 (IR-L3-RZZ),2x3,pooled f_hat_ideal F8 B=1 (4 files),0.1217,0.1187,0.1248,simulation (MY pooling),block (ag)
```

#### (y) C4_CF: near-clean correction r per arm with 95 % bootstrap intervals (GPU redo, 2026-10-13)

**Source:** `validation/C4_CF.json -> data.arms, data.pooled` (job 59736866; K = 1 232 / 1 262 / 1 244 / 1 239 trajectories of 2 000 planned)

**Columns and units:** `arm`; `K` Pauli trajectories run; `f_hit`,`f_ideal` (delta = 1e-3) with 95 % intervals; `benign_b` fraction of faulty trajectories that are benign; `r` = f_hit/f_ideal with 95 % interval; `floor_min` = min over S99 of f_eff/f_ideal. `r_nc_new` = 1.07794 (upper end of the pooled interval); signed `r_nc` = 1.11514 (CF_traj); CF_traj per-arm r (old): 1.089 [1.050, 1.136], 1.052 [0.987, 1.126], 1.115 [1.036, 1.220], 1.042 [1.001, 1.122]; pooled k=1 1.069 [1.029, 1.115]

```csv
arm,K,f_hit,f_hit_lo,f_hit_hi,benign_b,f_ideal,f_ideal_lo,f_ideal_hi,r,r_lo,r_hi,floor_min
B0_ref25_k1,1232,0.253168,0.239973,0.266121,0.0803571,0.238616,0.22652,0.250712,1.06098,1.03485,1.08958,1.05665
B1_ref57_k1,1262,0.235004,0.223834,0.247624,0.062599,0.224174,0.213681,0.235978,1.04831,1.0156,1.08232,1.04831
B0_ref25_k4,1244,0.247823,0.23539,0.261004,0.0474277,0.211449,0.202133,0.222096,1.17202,1.12759,1.21712,1.17202
B0_ref25_k1__xx,1239,0.183091,0.178685,0.187796,0.00242131,0.174092,0.172087,0.176764,1.05169,1.02949,1.07542,1.05169
pooled,,0.2441,0.235295,0.252764,,0.231395,0.223148,0.239451,1.05491,1.03253,1.07794,
```

#### (z) C4_F5_B0: SKQD shot-count curve (nested prefixes), sector B=0, scenario E7(0.07), plan of record f = 0.10

**Source:** `validation/C4_F5_B0.json -> data.frun.cv.shots_curve` (basis B_all for the `all` columns, B_sig for the `sig` columns)

**Columns and units:** `shots` N; `accepted` decoder-accepted shots; `B_all_size`; `err_all` = E_R - E_0 (lattice units); `kt_width` Kato-Temple width with exact E_1; `rH` residual (Weinstein half-width); `W` captured ground-state weight; `recall_S999`,`recall_S99`; `false_pos` accepted states with exact weight < 1e-8; `B_sig_size`,`err_sig`,`W_sig` for the signal support

```csv
shots,accepted,B_all_size,err_all,kt_width,rH,W,recall_S999,recall_S99,false_pos,B_sig_size,err_sig,W_sig
2188,446,125,0.0105164,0.0300731,0.285135,0.998553,0.825581,1,1,57,0.0249619,0.996264
4357,866,175,0.00570793,0.0167815,0.213188,0.999245,0.918605,1,4,88,0.0129319,0.998243
8734,1719,223,0.00162795,0.00535718,0.120543,0.999808,0.988372,1,6,135,0.00543572,0.99931
17468,3442,300,0.000632878,0.00210137,0.0755102,0.999925,1,1,14,187,0.00181641,0.999782
34909,6848,372,0.000242659,0.000832453,0.0475297,0.999972,1,1,29,256,0.000598769,0.999931
```

#### (z2) C4_F5_B0: the CV1-CV5 values

**Source:** `validation/C4_F5_B0.json -> data.frun.cv.criteria`

**Columns and units:** `quantity`; `value` in lattice energy units (or a probability for W); `ratio` = value / E_tol for CV1, CV3, CV4 and value / 0.1 (the H1 width limit) for CV2; `ok` the criterion verdict

```csv
quantity,value,ratio_or_margin_over_Etol,ok
E_tol,0.0142252,,
CV1_dE_N2_to_N,0.00039022,0.0274315,True
CV2_kt_width_half,0.00210137,0.0210137,True
CV2_kt_width_full,0.000832453,0.00832453,True
CV2_rH_half_weinstein,0.0755102,,
CV2_rH_full_weinstein,0.0475297,,
CV3_dE_k4_to_k5,0.000354233,0.0249017,True
CV4_margin_at_N,0.069544,4.88878,True
CV5_W_at_N,0.999972,,True
```

#### (z3) C4_F5_B0: reference-hit fraction per circuit

**Source:** `validation/C4_F5_B0.json -> data.frun.clean_fraction.per_circuit`

**Columns and units:** `circuit`; `shots`; `accepted`; `ref_hits`; `p_ref` ideal probability of the reference string; `f_hit` with 95 % interval. Pooled over the 8 k=1 circuits (2 136 shots, 284 hits): f_hit 0.14448 [0.12817, 0.16230], f_hat_ideal 0.12956 [0.11493, 0.14554]

```csv
circuit,shots,accepted,ref_hits,p_ref,f_hit,f_hit_lo,f_hit_hi
B0_ref117_k1,267,45,34,0.928357,0.137167,0.0949918,0.191677
B0_ref117_k2,267,48,19,0.741412,0.0959791,0.0577852,0.149884
B0_ref117_k3,267,52,20,0.506415,0.147913,0.0903484,0.228441
B0_ref117_k4,1367,302,72,0.292662,0.179966,0.140812,0.226638
B0_ref169_k1,267,59,45,0.92163,0.18287,0.133386,0.244695
B0_ref169_k2,267,47,29,0.720098,0.150831,0.101014,0.216619
B0_ref169_k3,267,50,18,0.474101,0.142195,0.0842729,0.22473
B0_ref169_k4,1367,249,37,0.26009,0.104062,0.0732685,0.143438
B0_ref25_k1,267,47,29,0.915021,0.1187,0.0794951,0.170474
B0_ref25_k2,267,44,17,0.700263,0.0909223,0.052965,0.145576
B0_ref25_k3,1000,198,57,0.446764,0.127582,0.0966289,0.165298
B0_ref25_k4,17600,3526,585,0.236292,0.140664,0.129494,0.152539
B0_ref333_k1,267,54,30,0.92163,0.121913,0.0822538,0.174039
B0_ref333_k2,267,53,30,0.720098,0.156032,0.105274,0.222747
B0_ref333_k3,267,51,24,0.474101,0.189594,0.121476,0.282102
B0_ref333_k4,1367,251,39,0.260091,0.109687,0.0779975,0.149948
B0_ref525_k1,267,52,39,0.916002,0.159461,0.113392,0.217989
B0_ref525_k2,267,46,16,0.702617,0.0852871,0.0487483,0.138502
B0_ref525_k3,267,39,11,0.448469,0.0918625,0.0458564,0.164369
B0_ref525_k4,1500,287,47,0.235448,0.133075,0.0977778,0.176964
B0_ref70_k1,267,52,26,0.916002,0.106307,0.0694428,0.155765
B0_ref70_k2,267,53,28,0.702617,0.149253,0.0991773,0.215713
B0_ref70_k3,267,56,21,0.448469,0.175376,0.10856,0.268082
B0_ref70_k4,1700,337,46,0.235448,0.114921,0.0841354,0.15329
B0_ref795_k1,267,56,43,0.92163,0.174742,0.126462,0.235377
B0_ref795_k2,267,59,31,0.720098,0.161234,0.10955,0.228859
B0_ref795_k3,267,51,14,0.474101,0.110596,0.0604627,0.185562
B0_ref795_k4,1367,239,42,0.26009,0.118125,0.0851334,0.159673
B0_ref86_k1,267,52,38,0.92163,0.154423,0.109279,0.211958
B0_ref86_k2,267,52,24,0.720098,0.124826,0.0799777,0.185731
B0_ref86_k3,267,50,20,0.474101,0.157995,0.0965064,0.244011
B0_ref86_k4,1500,291,63,0.26009,0.161479,0.124084,0.206602
```

#### (aa) ENC_compare: de-duplicated (dedup, E2) over current codec, ratios

**Source:** `validation/ENC_compare.json -> data.verdict.<lattice>.ratios`

**Columns and units:** `lattice`; `quantity` (qubits, cz_a2a_mean = CZ all-to-all mean over seeds 7/8/9, cz_routed = heavy-hex d=5 seed 7, zz_native = H2-2 native ZZ, depth_*, two_qubit_depth_*); `ratio` = dedup / current (dimensionless; 1 = no gain; `shortens_meaningfully` requires <= 0.5). Empty ratios (null) are not applicable

```csv
lattice,quantity,ratio_dedup_over_current
2x2,qubits,0.666667
2x2,cz_a2a_mean,0.882812
2x2,cz_routed,0.723301
2x2,depth_a2a,0.923913
2x2,depth_routed,0.832303
2x2,two_qubit_depth,0.950495
2x2,two_qubit_depth_routed,0.809859
2x3,qubits,0.65
2x3,cz_a2a_mean,0.926063
2x3,cz_routed,0.902136
2x3,zz_native,0.92493
2x3,depth_a2a,0.95413
2x3,depth_routed,0.906066
2x3,two_qubit_depth,0.946002
2x3,two_qubit_depth_routed,1.00081
2x3,two_qubit_depth_native,0.943896
```

#### (aa2) ENC_compare: error detection of single bit flips and random acceptance, current versus dedup

**Source:** `validation/ENC_compare.json -> data.verdict.<lattice>.detection_single_flip, random_acceptance`; 2x3 values from `data.detect` (single-flip detection 0.9817 / 0.9831 current, 0.8305 / 0.9075 dedup)

**Columns and units:** `lattice`; `det_current_B0`,`det_current_B1`,`det_dedup_B0`,`det_dedup_B1` fraction of single bit flips that the decoder rejects; `a_current_B0`,`a_dedup_B0` random acceptance of sector B=0

```csv
lattice,det_current_B0,det_current_B1,det_dedup_B0,det_dedup_B1,a_current_B0,a_dedup_B0
2x2,1,1,0.894737,1,0.00927734,0.148438
2x3,0.981684,0.983099,0.830474,0.907548,0.000645638,0.0826416
```

#### (aa3) ENC_compare in absolute numbers: current codec versus de-duplicated (dedup) codec

**Source:** `validation/ENC_compare.json -> data.counts, data.native.summary, data.f.codecs, data.kingston.circuits, data.detect`

**Columns and units:** `lattice`; `codec` current or dedup (the dedup files are UNSIGNED); `quantity`; `value`; `unit`. 'Kingston' rows use the 2026-10-06 `ibm_kingston` record (fingerprint `b948ddc8...`) and the exactness-gated routing; the f values are gate-only and idle-aware model values, not measurements

```csv
lattice,codec,quantity,value,unit
2x2,current,coarse step with diagonal: qubits,12,qubits
2x2,current,CZ all-to-all (mean of seeds 7/8/9),256,gates
2x2,current,two-qubit depth all-to-all,202,layers
2x2,current,CZ routed heavy-hex d=5 seed 7,618,gates
2x2,current,two-qubit depth routed,426,layers
2x2,dedup,coarse step with diagonal: qubits,8,qubits
2x2,dedup,CZ all-to-all (mean of seeds 7/8/9),226,gates
2x2,dedup,two-qubit depth all-to-all,192,layers
2x2,dedup,CZ routed heavy-hex d=5 seed 7,447,gates
2x2,dedup,two-qubit depth routed,345,layers
2x3,current,coarse step with diagonal: qubits,20,qubits
2x3,current,CZ all-to-all (mean of seeds 7/8/9),2164,gates
2x3,current,two-qubit depth all-to-all,1926,layers
2x3,current,CZ routed heavy-hex d=5 seed 7,5477,gates
2x3,current,two-qubit depth routed,3692,layers
2x3,dedup,coarse step with diagonal: qubits,13,qubits
2x3,dedup,CZ all-to-all (mean of seeds 7/8/9),2004,gates
2x3,dedup,two-qubit depth all-to-all,1822,layers
2x3,dedup,CZ routed heavy-hex d=5 seed 7,4941,gates
2x3,dedup,two-qubit depth routed,3695,layers
2x3,current,native ZZPhase per circuit (mean of 44),2158,gates
2x3,current,native PhasedX per circuit (mean),3009.61,gates
2x3,current,native two-qubit depth (mean),1925,layers
2x3,current,HQC per shot (mean),4.95792,HQC
2x3,current,native max |dpsi| / leakage,9.07e-14 / 1.2e-13,dimensionless
2x3,dedup,native ZZPhase per circuit (mean of 44),1996,gates
2x3,dedup,native PhasedX per circuit (mean),2840.89,gates
2x3,dedup,native two-qubit depth (mean),1817,layers
2x3,dedup,HQC per shot (mean),4.58618,HQC
2x3,dedup,native max |dpsi| / leakage,1.79e-13 / 9.47e-14,dimensionless
2x3,current,H2-2 gate-only f mean,0.150339,probability
2x3,dedup,H2-2 gate-only f mean,0.173935,probability
2x3,current,kingston B0_ref117_k1: CZ after routing,5659,gates
2x3,current,kingston B0_ref117_k1: active qubits,21,qubits
2x3,current,kingston B0_ref117_k1: f_gates_layout,1.67113e-05,probability
2x3,current,kingston B0_ref117_k1: f_ceiling_2q,0.00671723,probability
2x3,current,kingston B0_ref117_k1: ALAP scheduled duration,411.152,us
2x3,current,kingston B0_ref117_k1: idle-aware f at echo T2,1.6625e-15,probability
2x3,current,kingston B0_ref117_k1: idle-aware f at T2* = 0.174 T2echo,5.20227e-35,probability
2x3,current,kingston B1_ref29_k1: CZ after routing,5659,gates
2x3,current,kingston B1_ref29_k1: active qubits,21,qubits
2x3,current,kingston B1_ref29_k1: f_gates_layout,1.67429e-05,probability
2x3,current,kingston B1_ref29_k1: f_ceiling_2q,0.00671723,probability
2x3,current,kingston B1_ref29_k1: ALAP scheduled duration,410.768,us
2x3,current,kingston B1_ref29_k1: idle-aware f at echo T2,1.69324e-15,probability
2x3,current,kingston B1_ref29_k1: idle-aware f at T2* = 0.174 T2echo,5.50557e-35,probability
2x3,dedup,kingston B0_ref117_k1: CZ after routing,5091,gates
2x3,dedup,kingston B0_ref117_k1: active qubits,13,qubits
2x3,dedup,kingston B0_ref117_k1: f_gates_layout,0.000136515,probability
2x3,dedup,kingston B0_ref117_k1: f_ceiling_2q,0.0110988,probability
2x3,dedup,kingston B0_ref117_k1: ALAP scheduled duration,387.844,us
2x3,dedup,kingston B0_ref117_k1: idle-aware f at echo T2,1.90018e-10,probability
2x3,dedup,kingston B0_ref117_k1: idle-aware f at T2* = 0.174 T2echo,2.4719e-24,probability
2x3,dedup,kingston B1_ref29_k1: CZ after routing,4930,gates
2x3,dedup,kingston B1_ref29_k1: active qubits,13,qubits
2x3,dedup,kingston B1_ref29_k1: f_gates_layout,0.000179391,probability
2x3,dedup,kingston B1_ref29_k1: f_ceiling_2q,0.0127966,probability
2x3,dedup,kingston B1_ref29_k1: ALAP scheduled duration,379.68,us
2x3,dedup,kingston B1_ref29_k1: idle-aware f at echo T2,2.80203e-10,probability
2x3,dedup,kingston B1_ref29_k1: idle-aware f at T2* = 0.174 T2echo,2.45308e-23,probability
2x2,current,B=0: single-flip detected fraction,1,fraction
2x2,current,B=0: random acceptance a,0.00927734,fraction
2x2,current,B=1: single-flip detected fraction,1,fraction
2x2,current,B=1: random acceptance a,0.00488281,fraction
2x2,dedup,B=0: single-flip detected fraction,0.894737,fraction
2x2,dedup,B=0: random acceptance a,0.148438,fraction
2x2,dedup,B=1: single-flip detected fraction,1,fraction
2x2,dedup,B=1: random acceptance a,0.078125,fraction
2x3,current,B=0: single-flip detected fraction,0.981684,fraction
2x3,current,B=0: random acceptance a,0.000645638,fraction
2x3,current,B=1: single-flip detected fraction,0.983099,fraction
2x3,current,B=1: random acceptance a,0.000406265,fraction
2x3,dedup,B=0: single-flip detected fraction,0.830474,fraction
2x3,dedup,B=0: random acceptance a,0.0826416,fraction
2x3,dedup,B=1: single-flip detected fraction,0.907548,fraction
2x3,dedup,B=1: random acceptance a,0.052002,fraction
```

#### (ab) Quantinuum native circuits: numbers per lattice (regenerated 2026-10-15 from committed gates)

**Source:** `validation/Q0P_2x2.json`, `QN_2x2.json`, `QEMU_2x2.json`, `QH_2x2.json`, `QH_2x3.json`, `QEMU_2x3_laptop_smoke.json`, `Q0P_2x3.json`, `Q0P_2x4.json`, `QN_2x4.json`, `ci/parts/QV_2x4_01.json` (keys in `source`).

**Columns and units:** `lattice`; `quantity`; `value` (numbers, or slash-separated lists as text); `unit`; `kind` gate / simulation / PLAN; `source`.

```csv
lattice,quantity,value,unit,kind,source
2x2,circuits (signed family) + calibration,28 + 2,count,gate,validation/Q0P_2x2.json data.frozen
2x2,ZZPhase per circuit (min=mean=max),252,gates,gate,Q0P_2x2 data.frozen.index_summary.n_zz
2x2,PhasedX per circuit (min / mean / max),405 / 414.57 / 425,gates,gate,Q0P_2x2 data.frozen.index_summary.n_phasedx
2x2,two-qubit depth,201,layers,gate,Q0P_2x2 data.Q5.devices.quantinuum_h2_2.memory_ESTIMATE.depth_2q
2x2,max |dpsi| after global phase,7.21e-14,dimensionless,gate,Q0P_2x2 Q1 (worst B0_ref06_k2)
2x2,leakage,2.43e-14,dimensionless,gate,Q0P_2x2 Q1
2x2,HQC per shot (mean; min; max),0.6109; 0.609; 0.613,HQC,gate,Q0P_2x2 Q5
2x2,gate-only f mean H2-2,0.7929,probability,gate,Q0P_2x2 Q5
2x2,gate-only f mean Helios-1,0.8046,probability,gate,Q0P_2x2 Q5
2x2,gate-only f mean H1-1,0.756,probability,gate,Q0P_2x2 Q5
2x2,gate-only f mean H2-1,0.7429,probability,gate,Q0P_2x2 Q5
2x2,"D3 prime plan cost at 0.7 f, H2-2",13990,HQC,gate,Q0P_2x2 Q5
2x2,"D3 prime plan cost at 0.7 f, Helios-1",13563,HQC,gate,Q0P_2x2 Q5
2x2,"D3 prime plan cost at 0.7 f, H1-1",14233,HQC,gate,Q0P_2x2 Q5
2x2,"D3 prime plan cost at 0.7 f, H2-1",14660,HQC,gate,Q0P_2x2 Q5
2x2,T2 noiseless: states tested / max z / failures,514 / 3.585 / 0,5-sigma test,gate,QN_2x2 N1
2x2,T2 noiseless SKQD at 133 907 shots: E_R - E0 both sectors,0,energy,gate,QN_2x2 N2
2x2,T3 f-cells: cells / scenarios / shots per cell,308 / 11 / 2000,count,gate,QN_2x2 N3
2x2,T3 E1 mean k=1 f_hit (my mean of 7 cells),0.8378,probability,simulation (MY mean),QN_2x2 data.fcells.per_scenario.E1.cells
2x2,T3 E1 band: hits / expected / band95,22751 / 24433 / [24127 24740],counts,gate (information: tension),QN_2x2 data.fcells.E1_band
2x2,T3 plan-of-record runs (E1 E3 E4 E5b): recall S999 / E_R-E0,1.0 / 0,--,gate,QN_2x2 N4
2x2,T3 wall: f-cells + plan of record,12021 + 6888 = 18909 (5.25 h),s,gate,QN_2x2 data.t3_cap
2x2,T3 rates E1 / E5b, 0.02344 / 0.02780,s/shot,gate,QN_2x2 N5
2x2,T4 H2-1LE: circuits / shots each / max z / failures,28 / 785 / 2.898 / 0,5-sigma test,gate,QEMU_2x2 M1
2x2,T4 rate range (per circuit),0.0266 to 0.0842,s/shot,gate,QEMU_2x2 data.per_circuit
2x2,T6 Selene: packages / circuits / shots each / max z / failures,28 / 28 / 1599 / 3.67 / 0,5-sigma test,gate,QH_2x2 H1 H2
2x2,T6 rate range (per circuit),0.0667 to 0.1271,s/shot,gate,QH_2x2 data.per_circuit
2x3,ZZPhase per circuit (all 44),2158,gates,gate,validation/Q0P_2x3.json
2x3,PhasedX per circuit (range),2989 - 3091,gates,gate,same
2x3,max |dpsi|,2.09e-13,dimensionless,gate,same
2x3,HQC per shot mean,4.9666,HQC,gate,same
2x3,gate-only f mean H2-2 / Helios-1 / H1-1 / H2-1,0.1502 / 0.1642 / 0.1113 / 0.0860,probability,gate,validation/Q0P_2x3.json; data/quantinuum/devices_20261002.json
2x3,T6 Selene: 2 circuits x 10 shots; s/shot,158.0 / 145.6,s/shot,gate (information),QH_2x3
2x3,T4 H2-1LE smoke: one shot,98.27,s,gate (smoke),QEMU_2x3_laptop_smoke
2x3,structured source cross-check B0_ref25_k1: ZZ structured / opt-3,2590 / 2158,gates,gate,Q0P_2x4 data.structured_source_check_2x3
2x3,structured cross-check: |dpsi| vs coarse_states / vs frozen opt-3 native,3.06e-14 / 1.93e-13,dimensionless,gate,same
2x4,circuits built: opt-3 / structured / planned,19 / 60 / 60,circuits,gate,Q0P_2x4 data.index
2x4,ZZPhase per circuit opt-3 / structured,69676 / 71548,gates,gate,Q0P_2x4 Q2
2x4,PhasedX per circuit opt-3 (range) / structured,90272-90646 / 210994-210995,gates,gate,Q0P_2x4 data.index.sources
2x4,HQC per shot opt-3 (mean) / structured,157.51 / 185.35,HQC,gate,Q0P_2x4 Q5
2x4,rounding bound B opt-3 (range),4.956e-09 to 4.979e-09,dimensionless,gate,Q0P_2x4 data.Q1.B_per_circuit
2x4,rounding bound B structured (range),5.756e-12 to 6.706e-12,dimensionless,gate,same
2x4,Q1L (i) max 2q angle delta / (ii) frame residual,4.4e-15 half-turns / 8.04e-13,dimensionless,gate,Q0P_2x4 Q1L
2x4,Q1 state bar 1e-10,not measured (GPU slot QV_2x4_01),--,gate (FAIL by construction),Q0P_2x4 Q1
2x4,gate-only f mean H2-2 opt-3 / structured,5.78e-27 / 4.18e-29,probability,gate,QN_2x4 data.analytic.devices_by_source
2x4,E1 log10 f0 opt-3 / structured,-24.39 / -26.12,log10,gate,QN_2x4 data.analytic.f0
2x4,QV_2x4_01 predicted GPU time / budget,887.5 / 2700,s,PLAN (part file),ci/parts/QV_2x4_01.json prediction
```

#### (ac) Campaign 33 class-4 full runs: plan, parts and sizing (written by `scripts/campaign33_resize.py`; carried unchanged, states in (ad))

**Source:** `data/campaign33/sizing_33a.json -> runs` (33b scenario-aware rates)

**Columns and units:** `run`; `token` first-part token; `scenario`; `family` NAT-O0 / NAT-O2 / IR-L3-RZZ; `sector`; `kind` plan (plan of record) or s3quota (2e5 shots per sector); `tier` plan tier f (dimensionless; blank for s3quota); `total_shots` over all parts; `parts` number of 1-GPU-hour jobs; `rate_s_per_shot` sizing rate (s); `N_max` shots per part allowed

```csv
run,token,scenario,family,sector,kind,plan_tier,total_shots,parts,rate_s_per_shot,N_max_per_part
F1_B0,C4_F1_B0,E1,NAT-O0,B=0,plan,0.15,27309,1,0.0257151,53758
F1_B1,C4_F1_B1,E1,NAT-O0,B=1,plan,0.15,67600,2,0.0257151,53758
F2_B0,C4_F2_B0,E2,NAT-O0,B=0,plan,0.15,27309,1,0.0259195,53334
F2_B1,C4_F2_B1,E2,NAT-O0,B=1,plan,0.15,67600,2,0.0259195,53334
F3_B0,C4_F3_B0,E3,NAT-O0,B=0,plan,0.05,63875,4,0.072096,19174
F3_B1,C4_F3_B1,E3,NAT-O0,B=1,plan,0.05,193600,11,0.072096,19174
F4_B0a,C4_F4_B0a,E7_0.10,NAT-O0,B=0,s3quota,,100000,2,0.0257151,67197
F4_B0b,C4_F4_B0b,E7_0.10,NAT-O0,B=0,s3quota,,100000,2,0.0257151,67197
F4_B1a,C4_F4_B1a,E7_0.10,NAT-O0,B=1,s3quota,,99996,2,0.0257151,67197
F4_B1b,C4_F4_B1b,E7_0.10,NAT-O0,B=1,s3quota,,99996,2,0.0257151,67197
F5_B0,C4_F5_B0,E7_0.07,NAT-O0,B=0,plan,0.1,34909,1,0.0257151,53758
F5_B1,C4_F5_B1,E7_0.07,NAT-O0,B=1,plan,0.1,99000,2,0.0257151,53758
F6_B0,C4_F6_B0,E5b,NAT-O0,B=0,plan,0.15,27309,3,0.141714,9754
F6_B1,C4_F6_B1,E5b,NAT-O0,B=1,plan,0.15,67600,7,0.141714,9754
F7_B0,C4_F7_B0,E1,NAT-O2,B=0,plan,0.15,27309,1,0.0257151,53758
F7_B1,C4_F7_B1,E1,NAT-O2,B=1,plan,0.15,67600,2,0.0257151,53758
F8_B0a,C4_F8_B0a,E8,IR-L3-RZZ,B=0,s3quota,,100000,2,0.0257151,67197
F8_B0b,C4_F8_B0b,E8,IR-L3-RZZ,B=0,s3quota,,100000,2,0.0257151,67197
F8_B1a,C4_F8_B1a,E8,IR-L3-RZZ,B=1,s3quota,,99996,2,0.0257151,67197
F8_B1b,C4_F8_B1b,E8,IR-L3-RZZ,B=1,s3quota,,99996,2,0.0257151,67197
```


#### (ad) Campaign 33 and the Quantinuum GPU slots: every token, its state and result (as of 2026-10-15 17:43 UTC)

**Source:** `scripts/gate_tokens.json` (62 tokens), `ci/status/*.json`, `scripts/ci_check.sh`, `validation/<TOKEN>.json`, `reports/ci-<jobid>.out`, `data/campaign33/sizing_33a.json`, `ci/parts/*.json`, `prompts/33b`-`33e`, `35b`.

**Columns and units:** `token`; `state` done / pending (request number) / not requested (reason) / deferred / DROPPED; `job_id` of the latest done request; `gate_status` with failing criteria; `criteria` passed/total; `gate_seconds` s; `key_result` (for class-4 files: run, scenario, sector, part, $E_R-E_0$, certificate type (KT or W = Weinstein) and width, recall of $S_{999}$, $\hat f_{\rm ideal}$); `source`.

```csv
token,state,job_id,gate_status,criteria,gate_seconds,key_result,source
C1_IDEAL,done,59570217,PASS,10/10,103,max dpsi 2.3e-12; recall S999 1.0; E_R-E0 1.8e-4 (B0 plan),validation/C1_IDEAL.json
C2_CAL,done,59736871,PASS,12/12,1827,run 3: z_w vs device PTA +1.82 RM -30.55 Kraus -54.20; decision withdrawn by 33d R5,validation/C2_CAL.json
C2_GATE,not requested (after maintenance; representation blocked),,,,,,
C2_ECHO,"not requested (after maintenance, prompts/33e R4)",,,,,,
C2_STAR,not requested (after maintenance),,,,,,
C2_XY4,"not requested (only after C2_KCHK run 2 reads rm, prompts/33e R4)",,,,,,
C2_COH,not requested (after maintenance),,,,,,
C3_AER,done,59570221,PASS,10/10,72,max dpsi 2.1e-13; 1393 states max z 4.08; recall 1.0,validation/C3_AER.json
C3_LE,not requested (needs skqd-pecos env on Perlmutter),,,,,,
C3_SEL,DROPPED (selene/qir-qis incompatibility),,,,,,
C4_FCELLS_A,done,59570315,FAIL (S6),7/8,2337,10 of 42 cells; E1 f_hit 0.2312,validation/C4_FCELLS_A.json
C4_FCELLS_B,done,59736863,PASS,8/8,1883,35 cells; S3 redo 656/3200 inside (650 741),validation/C4_FCELLS_B.json
C4_F1_B0,done,59739276,PASS,8/8,1811,F1_B0 E1 B=0 part 1/1: E_R-E0 0.000329; KT width 0.00115; recall 1.000; f_hat_ideal 0.2281,validation/C4_F1_B0.json
C4_F1_B1,done,59779331,PASS,7/7,878,F1_B1 E1 B=1 part 1/2: E_R-E0 0.000292; W width 0.0465; recall 1.000; f_hat_ideal 0.2128,validation/C4_F1_B1.json
C4_F2_B0,pending (request 039),,,,,,
C4_F2_B1,pending (request 040),,,,,,
C4_F3_B0,deferred past maintenance (4 parts; parts 2-4 = slots 18-20),,,,,,
C4_F3_B1,deferred past maintenance (11 parts),,,,,,
C4_F4_B0a,done,59742843,PASS,7/7,1412,F4_B0a E7_0.10 B=0 part 1/2: E_R-E0 0.000121; KT width 0.000459; recall 1.000; f_hat_ideal 0.1743,validation/C4_F4_B0a.json
C4_F4_B0b,done,59747539,PASS,7/7,1408,F4_B0b E7_0.10 B=0 part 1/2: E_R-E0 0.000304; KT width 0.00104; recall 1.000; f_hat_ideal 0.1668,validation/C4_F4_B0b.json
C4_F4_B1a,done,59745015,PASS,7/7,1363,F4_B1a E7_0.10 B=1 part 1/2: E_R-E0 0.000313; W width 0.0507; recall 1.000; f_hat_ideal 0.1666,validation/C4_F4_B1a.json
C4_F4_B1b,done,59747551,PASS,7/7,1378,F4_B1b E7_0.10 B=1 part 1/2: E_R-E0 0.00105; W width 0.0892; recall 0.989; f_hat_ideal 0.1589,validation/C4_F4_B1b.json
C4_F5_B0,done,59736879,PASS,8/8,2234,F5_B0 E7_0.07 B=0 part 1/1: E_R-E0 0.000243; KT width 0.000832; recall 1.000; f_hat_ideal 0.1296,validation/C4_F5_B0.json
C4_F5_B1,done,59739280,PASS,7/7,1392,F5_B1 E7_0.07 B=1 part 1/2: E_R-E0 0.000176; W width 0.0364; recall 1.000; f_hat_ideal 0.1140,validation/C4_F5_B1.json
C4_F6_B0,deferred past maintenance (3 parts),,,,,,
C4_F6_B1,deferred past maintenance (7 parts),,,,,,
C4_F7_B0,done,59739278,PASS,8/8,669,F7_B0 E1 B=0 part 1/1: E_R-E0 0.000335; KT width 0.00108; recall 1.000; f_hat_ideal 0.2226,validation/C4_F7_B0.json
C4_F7_B1,done,59779337,PASS,7/7,707,F7_B1 E1 B=1 part 1/2: E_R-E0 0.000423; W width 0.0537; recall 1.000; f_hat_ideal 0.2400,validation/C4_F7_B1.json
C4_F8_B0a,done,59749780,PASS,7/7,1089,F8_B0a E8 B=0 part 1/2: E_R-E0 0.000255; KT width 0.000958; recall 1.000; f_hat_ideal 0.1158,validation/C4_F8_B0a.json
C4_F8_B0b,done,59780912,PASS,7/7,1073,F8_B0b E8 B=0 part 1/2: E_R-E0 0.000126; KT width 0.000482; recall 1.000; f_hat_ideal 0.1228,validation/C4_F8_B0b.json
C4_F8_B1a,done,59752618,PASS,7/7,987,F8_B1a E8 B=1 part 1/2: E_R-E0 0.000486; W width 0.0625; recall 1.000; f_hat_ideal 0.1207,validation/C4_F8_B1a.json
C4_F8_B1b,done,59780919,PASS,7/7,1029,F8_B1b E8 B=1 part 1/2: E_R-E0 0.000399; W width 0.0553; recall 1.000; f_hat_ideal 0.1219,validation/C4_F8_B1b.json
C4_CF,done,59736866,FAIL (S6),7/8,2417,pooled r 1.0549 [1.0325 1.0779]; r_nc_new 1.0779; k4 arm 1.172,validation/C4_CF.json
C4_PART_01,done,59739282,PASS,8/8,1381,F5_B1 E7_0.07 B=1 part 2/2: E_R-E0 0.00034; W width 0.0481; recall 1.000; f_hat_ideal 0.1194,validation/C4_PART_01.json
C4_PART_02,done,59745007,FAIL (S6),7/8,1270,F4_B0a E7_0.10 B=0 part 2/2: E_R-E0 0.000269; KT width 0.000916; recall 1.000; f_hat_ideal 0.1712,validation/C4_PART_02.json
C4_PART_03,done,59745024,PASS,8/8,1354,F4_B1a E7_0.10 B=1 part 2/2: E_R-E0 0.000382; W width 0.0565; recall 1.000; f_hat_ideal 0.1644,validation/C4_PART_03.json
C4_PART_04,done,59747548,FAIL (S6),7/8,1276,F4_B0b E7_0.10 B=0 part 2/2: E_R-E0 0.000182; KT width 0.000615; recall 1.000; f_hat_ideal 0.1602,validation/C4_PART_04.json
C4_PART_05,done,59747553,PASS,8/8,1358,F4_B1b E7_0.10 B=1 part 2/2: E_R-E0 0.000491; W width 0.0627; recall 1.000; f_hat_ideal 0.1610,validation/C4_PART_05.json
C4_PART_06,done,59749784,PASS,8/8,1113,F8_B0a E8 B=0 part 2/2: E_R-E0 0.000254; KT width 0.000926; recall 1.000; f_hat_ideal 0.1192,validation/C4_PART_06.json
C4_PART_07,done,59752623,PASS,8/8,999,F8_B1a E8 B=1 part 2/2: E_R-E0 0.000772; W width 0.079; recall 1.000; f_hat_ideal 0.1228,validation/C4_PART_07.json
C4_PART_08,done,59780915,PASS,8/8,1089,F8_B0b E8 B=0 part 2/2: E_R-E0 0.000214; KT width 0.000694; recall 1.000; f_hat_ideal 0.1217,validation/C4_PART_08.json
C4_PART_09,done,59782656,PASS,8/8,1043,F8_B1b E8 B=1 part 2/2: E_R-E0 0.000772; W width 0.0751; recall 0.989; f_hat_ideal 0.1214,validation/C4_PART_09.json
C4_PART_10,done,59779334,PASS,8/8,856,F1_B1 E1 B=1 part 2/2: E_R-E0 0.000238; W width 0.0437; recall 1.000; f_hat_ideal 0.2226,validation/C4_PART_10.json
C4_PART_11,done,59779338,PASS,8/8,689,F7_B1 E1 B=1 part 2/2: E_R-E0 0.000306; W width 0.048; recall 1.000; f_hat_ideal 0.2302,validation/C4_PART_11.json
C4_PART_12,pending (request 041),,,,,,
C4_PART_13,pending (request 042),,,,,,
C4_PART_14,pending (request 043),,,,,,
C4_PART_15,pending (request 044),,,,,,
C4_PART_16,pending (request 045),,,,,,
C4_PART_17,pending (request 046),,,,,,
C4_PART_18,assigned F3_B0 part 2 of 4 (deferred),,,,,,
C4_PART_19,assigned F3_B0 part 3 of 4 (deferred),,,,,,
C4_PART_20,assigned F3_B0 part 4 of 4 (deferred),,,,,,
C2_KCHK,done,59780907,"FAIL (K1,K2,S6)",7/10,2352,w: kraus cusv 3.00 native 3.57 nofusion 1.14 rm 7.43; CPU arms 0 shots; blocked,validation/C2_KCHK.json
QV_2x4_01,not requested (decision job prepared; dry run PASS at 2x2),,,,,,
QV_2x4_02,not requested (needs ci/allowed_jobs.q35 on Perlmutter),,,,,,
QV_2x4_03,not requested (needs ci/allowed_jobs.q35 on Perlmutter),,,,,,
QV_2x4_04,not requested (needs ci/allowed_jobs.q35 on Perlmutter),,,,,,
QV_2x4_05,not requested (needs ci/allowed_jobs.q35 on Perlmutter),,,,,,
QV_2x4_06,not requested (needs ci/allowed_jobs.q35 on Perlmutter),,,,,,
QV_2x4_07,not requested (needs ci/allowed_jobs.q35 on Perlmutter),,,,,,
QV_2x4_08,not requested (needs ci/allowed_jobs.q35 on Perlmutter),,,,,,
```

#### (ae) All 25 class-4 run files (new)

**Source:** `validation/<token>.json -> data.frun.{at_N.certificate, at_N.accepted, at_N.B_all_size, clean_fraction.pooled_k1, bootstrap_at_N, cv.criteria, sampling.wall_s}`, `data.seconds_per_shot`, `data.run.gpu_telemetry`, `criteria`; `gate_s` from `reports/ci-<job>.out`.

**Columns and units:** `token`, `job`; `run`, `scenario`, `family`, `sector`; `kind` plan / s3quota; `tier` plan tier (blank for quota); `half` a / b; `part`, `parts`; `shots_done`, `shots_requested`, `accepted` counts; `B_all` states; `E_R` Ritz energy (lattice units); `E_R_minus_E0`; `cert_type` kato_temple_exact_E1 ($B=0$) or weinstein ($B=1$); `cert_lo`, `cert_hi` interval (lattice units); `cert_width`; `E0_inside`; `recall_S999`, `recall_S99`, `W` fractions; `n_ref_k1`, `shots_k1`: pooled $k=1$ reference hits and shots; `f_hit` (+ `_lo`, `_hi` 95 % Garwood); `f_hat_ideal` (+ interval) $=f_{\rm hit}/r_{nc}$; `r_nc` 1.1151; `boot_err_lo/hi` the gate's 95 % bootstrap band of $E_R-E_0$; `CV1`-`CV5` True / False / None (None = not evaluated; blank = evaluated at assembly); `status`, `failed` criteria; `sampling_wall_s`, `gate_s` seconds; `s_per_shot`; `gpu_mean_util_pct`; `gpu_peak_mib`.

```csv
token,job,run,scenario,family,sector,kind,tier,half,part,parts,shots_done,shots_requested,accepted,B_all,E_R,E_R_minus_E0,cert_type,cert_lo,cert_hi,cert_width,E0_inside,recall_S999,recall_S99,W,n_ref_k1,shots_k1,f_hit,f_hit_lo,f_hit_hi,f_hat_ideal,f_hat_ideal_lo,f_hat_ideal_hi,r_nc,boot_err_lo,boot_err_hi,CV1,CV2,CV3,CV4,CV5,status,failed,sampling_wall_s,s_per_shot,gate_s,gpu_mean_util_pct,gpu_peak_mib
C4_F5_B0,59736879,F5_B0,E7_0.07,NAT-O0,B0,plan,0.1,,1,1,34909,34909,6848,372,-5.6023577993,2.426586e-04,kato_temple_exact_E1,-5.6031902519,-5.6023577993,8.324527e-04,True,1.000000,1.000000,0.99997189,284,2136,0.144482,0.128165,0.162301,0.129565,0.114932,0.145543,1.115135,3.714186e-04,8.809922e-04,True,True,True,True,True,PASS,,954.4,0.027341,2234,50.1,1783.0
C4_F1_B0,59739276,F1_B0,E1,NAT-O0,B0,plan,0.15,,1,1,27309,27309,8507,322,-5.6022714434,3.290145e-04,kato_temple_exact_E1,-5.6034167657,-5.6022714434,1.145322e-03,True,1.000000,1.000000,0.99996197,500,2136,0.254371,0.232560,0.277676,0.228107,0.208549,0.249006,1.115135,4.772781e-04,8.724568e-04,True,True,True,True,True,PASS,,756.1,0.027686,1811,54.2,1783.0
C4_F7_B0,59739278,F7_B0,E1,NAT-O2,B0,plan,0.15,,1,1,27309,27309,8447,326,-5.6022655431,3.349148e-04,kato_temple_exact_E1,-5.6033502758,-5.6022655431,1.084733e-03,True,1.000000,1.000000,0.99995860,488,2136,0.248266,0.226724,0.271302,0.222633,0.203316,0.243291,1.115135,5.013149e-04,8.761375e-04,True,True,,True,True,PASS,,589.1,0.021573,669,47.7,1783.0
C4_F5_B1,59739280,F5_B1,E7_0.07,NAT-O0,B1,plan,0.1,,1,2,49500,49500,9554,346,-3.8259084229,1.760202e-04,weinstein,-3.8622589777,-3.8259084229,3.635055e-02,True,1.000000,1.000000,0.99997518,105,900,0.127147,0.103993,0.153919,0.114019,0.093256,0.138027,1.115135,2.331103e-04,4.939432e-04,,,,,,PASS,,1305.5,0.026373,1392,58.7,1783.0
C4_PART_01,59739282,F5_B1,E7_0.07,NAT-O0,B1,plan,0.1,,2,2,49500,49500,9432,336,-3.8257449341,3.395091e-04,weinstein,-3.8738103464,-3.8257449341,4.806541e-02,True,1.000000,1.000000,0.99994794,110,900,0.133201,0.109475,0.160544,0.119448,0.098172,0.143968,1.115135,3.873928e-04,7.414067e-04,,,,,,PASS,,1297.2,0.026205,1381,54.6,1783.0
C4_F1_B1,59779331,F1_B1,E1,NAT-O0,B1,plan,0.15,,1,2,33800,33800,10273,313,-3.8257924244,2.920187e-04,weinstein,-3.8722431006,-3.8257924244,4.645068e-02,True,1.000000,1.000000,0.99995859,196,900,0.237341,0.205275,0.272996,0.212836,0.184081,0.244809,1.115135,3.673563e-04,6.325848e-04,,,,,,PASS,,798.4,0.023621,878,36.8,1783.0
C4_PART_10,59779334,F1_B1,E1,NAT-O0,B1,plan,0.15,,2,2,33800,33800,10104,312,-3.8258468063,2.376368e-04,weinstein,-3.8695204571,-3.8258468063,4.367365e-02,True,1.000000,1.000000,0.99996848,205,900,0.248239,0.215419,0.284647,0.222609,0.193177,0.255258,1.115135,3.160657e-04,7.895673e-04,,,,,,PASS,,787.9,0.023312,856,45.9,1783.0
C4_F7_B1,59779337,F7_B1,E1,NAT-O2,B1,plan,0.15,,1,2,33800,33800,10212,319,-3.8256615263,4.229168e-04,weinstein,-3.8793132955,-3.8256615263,5.365177e-02,True,1.000000,1.000000,0.99993593,221,900,0.267614,0.233492,0.305320,0.239984,0.209385,0.273797,1.115135,4.912220e-04,1.177412e-03,,,,,,PASS,,634.0,0.018757,707,41.9,1783.0
C4_PART_11,59779338,F7_B1,E1,NAT-O2,B1,plan,0.15,,2,2,33800,33800,10172,317,-3.8257789063,3.055368e-04,weinstein,-3.8737689352,-3.8257789063,4.799003e-02,True,1.000000,1.000000,0.99995756,212,900,0.256716,0.223320,0.293698,0.230211,0.200263,0.263374,1.115135,3.889856e-04,7.919586e-04,,,,,,PASS,,617.4,0.018266,689,45.9,1783.0
C4_F4_B0a,59742843,F4_B0a,E7_0.10,NAT-O0,B0,s3quota,,a,1,2,50016,50016,12159,376,-5.6024792688,1.211891e-04,kato_temple_exact_E1,-5.6029378009,-5.6024792688,4.585320e-04,True,1.000000,1.000000,0.99998735,2236,12504,0.194321,0.186349,0.202546,0.174258,0.167109,0.181634,1.115135,2.345485e-04,4.728733e-04,,,,,,PASS,,1317.5,0.026343,1412,52.8,1783.0
C4_PART_02,59745007,F4_B0a,E7_0.10,NAT-O0,B0,s3quota,,a,2,2,45696,49984,11125,353,-5.6023311679,2.692899e-04,kato_temple_exact_E1,-5.6032472794,-5.6023311679,9.161115e-04,True,1.000000,1.000000,0.99996891,2007,11424,0.190909,0.182647,0.199448,0.171198,0.163789,0.178856,1.115135,3.585403e-04,5.392813e-04,,,,,,FAIL,S6,1186.2,0.025959,1270,54.7,1783.0
C4_F4_B0b,59747539,F4_B0b,E7_0.10,NAT-O0,B0,s3quota,,b,1,2,50016,50016,12268,360,-5.6022967795,3.036784e-04,kato_temple_exact_E1,-5.6033390769,-5.6022967795,1.042297e-03,True,1.000000,1.000000,0.99996457,2140,12504,0.185978,0.178181,0.194029,0.166776,0.159784,0.173996,1.115135,3.930628e-04,5.725271e-04,,,,,,PASS,,1316.4,0.026319,1408,56.8,1783.0
C4_PART_04,59747548,F4_B0b,E7_0.10,NAT-O0,B0,s3quota,,b,2,2,45696,49984,11150,371,-5.6024187536,1.817042e-04,kato_temple_exact_E1,-5.6030340860,-5.6024187536,6.153323e-04,True,1.000000,1.000000,0.99997885,1878,11424,0.178638,0.170649,0.186905,0.160194,0.153030,0.167607,1.115135,2.732002e-04,4.579187e-04,,,,,,FAIL,S6,1184.0,0.025910,1276,55.3,1783.0
C4_F4_B1a,59745015,F4_B1a,E7_0.10,NAT-O0,B1,s3quota,,a,1,2,50004,50004,11919,298,-3.8257714130,3.130302e-04,weinstein,-3.8765171113,-3.8257714130,5.074570e-02,True,1.000000,1.000000,0.99995925,2131,12501,0.185779,0.177974,0.193838,0.166598,0.159599,0.173825,1.115135,5.661816e-04,2.123969e-03,,,,,,PASS,,1301.1,0.026021,1363,58.9,1783.0
C4_PART_03,59745024,F4_B1a,E7_0.10,NAT-O0,B1,s3quota,,a,2,2,49992,49992,11947,286,-3.8257019711,3.824720e-04,weinstein,-3.8822411092,-3.8257019711,5.653914e-02,True,1.000000,1.000000,0.99995136,2103,12498,0.183382,0.175628,0.191391,0.164449,0.157494,0.171631,1.115135,5.536434e-04,1.808976e-03,,,,,,PASS,,1294.1,0.025885,1354,56.9,1783.0
C4_F4_B1b,59747551,F4_B1b,E7_0.10,NAT-O0,B1,s3quota,,b,1,2,50004,50004,11860,288,-3.8250310923,1.053351e-03,weinstein,-3.9142639712,-3.8250310923,8.923288e-02,True,0.989474,1.000000,0.99985149,2032,12501,0.177149,0.169529,0.185022,0.158858,0.152026,0.165919,1.115135,1.176847e-03,2.169564e-03,,,,,,PASS,,1306.8,0.026134,1378,58.2,1783.0
C4_PART_05,59747553,F4_B1b,E7_0.10,NAT-O0,B1,s3quota,,b,2,2,49992,49992,11927,280,-3.8255935591,4.908841e-04,weinstein,-3.8882725942,-3.8255935591,6.267904e-02,True,1.000000,1.000000,0.99993461,2059,12498,0.179546,0.171873,0.187472,0.161008,0.154128,0.168116,1.115135,6.459541e-04,1.788420e-03,,,,,,PASS,,1298.6,0.025976,1358,53.7,1783.0
C4_F8_B0a,59749780,F8_B0a,E8,IR-L3-RZZ,B0,s3quota,,a,1,2,50016,50016,9686,395,-5.6023450056,2.554523e-04,kato_temple_exact_E1,-5.6033026713,-5.6023450056,9.576657e-04,True,1.000000,1.000000,0.99997365,1486,12504,0.129142,0.122658,0.135879,0.115808,0.109994,0.121850,1.115135,3.501598e-04,5.859860e-04,,,,,,PASS,,994.0,0.019875,1089,45.5,1783.0
C4_PART_06,59749784,F8_B0a,E8,IR-L3-RZZ,B0,s3quota,,a,2,2,49984,49984,9836,383,-5.6023462583,2.541995e-04,kato_temple_exact_E1,-5.6032722394,-5.6023462583,9.259811e-04,True,1.000000,1.000000,0.99997199,1528,12496,0.132877,0.126297,0.139710,0.119157,0.113257,0.125286,1.115135,3.575653e-04,6.131698e-04,,,,,,PASS,,1029.3,0.020594,1113,43.5,1783.0
C4_F8_B0b,59780912,F8_B0b,E8,IR-L3-RZZ,B0,s3quota,,b,1,2,50016,50016,9798,389,-5.6024749506,1.255073e-04,kato_temple_exact_E1,-5.6029566553,-5.6024749506,4.817047e-04,True,1.000000,1.000000,0.99998722,1576,12504,0.136963,0.130284,0.143896,0.122822,0.116832,0.129039,1.115135,2.642299e-04,5.847042e-04,,,,,,PASS,,927.2,0.018537,1073,39.7,1783.0
C4_PART_08,59780915,F8_B0b,E8,IR-L3-RZZ,B0,s3quota,,b,2,2,49984,49984,9860,387,-5.6023868752,2.135827e-04,kato_temple_exact_E1,-5.6030811500,-5.6023868752,6.942748e-04,True,1.000000,1.000000,0.99997361,1561,12496,0.135746,0.129095,0.142652,0.121731,0.115766,0.127923,1.115135,3.112824e-04,5.043067e-04,,,,,,PASS,,940.9,0.018824,1089,39.1,1783.0
C4_F8_B1a,59752618,F8_B1a,E8,IR-L3-RZZ,B1,s3quota,,a,1,2,50004,50004,9658,272,-3.8255980375,4.864056e-04,weinstein,-3.8880635845,-3.8255980375,6.246555e-02,True,1.000000,1.000000,0.99993427,1544,12501,0.134605,0.127974,0.141490,0.120707,0.114761,0.126882,1.115135,6.873290e-04,1.825491e-03,,,,,,PASS,,936.6,0.018730,987,46.9,1783.0
C4_PART_07,59752623,F8_B1a,E8,IR-L3-RZZ,B1,s3quota,,a,2,2,49992,49992,9542,277,-3.8253127816,7.716615e-04,weinstein,-3.9043583889,-3.8253127816,7.904561e-02,True,1.000000,1.000000,0.99989911,1571,12498,0.136992,0.130300,0.143937,0.122847,0.116847,0.129076,1.115135,9.460840e-04,2.096220e-03,,,,,,PASS,,947.2,0.018948,999,37.2,1783.0
C4_F8_B1b,59780919,F8_B1b,E8,IR-L3-RZZ,B1,s3quota,,b,1,2,50004,50004,9508,287,-3.8256852212,3.992220e-04,weinstein,-3.8810115618,-3.8256852212,5.532634e-02,True,1.000000,1.000000,0.99994451,1559,12501,0.135912,0.129249,0.142831,0.121880,0.115904,0.128084,1.115135,6.077799e-04,1.733161e-03,,,,,,PASS,,947.6,0.018951,1029,46.1,1783.0
C4_PART_09,59782656,F8_B1b,E8,IR-L3-RZZ,B1,s3quota,,b,2,2,49992,49992,9551,286,-3.8253124729,7.719702e-04,weinstein,-3.9003798422,-3.8253124729,7.506737e-02,True,0.989474,1.000000,0.99988961,1552,12498,0.135335,0.128685,0.142239,0.121362,0.115398,0.127553,1.115135,9.640948e-04,2.458200e-03,,,,,,PASS,,947.7,0.018957,1043,39.6,1783.0
```

#### (af) Shot-count curves of the three single-job class-4 runs (nested prefixes, $B_{\rm all}$ basis)

**Source:** `validation/C4_F5_B0.json`, `C4_F1_B0.json`, `C4_F7_B0.json -> data.frun.cv.shots_curve[*]` (fields `shots`, `accepted`, `B_all_size`, `all.{err, kt_width, rH, W, recall_S999, false_positives}`, `sig.{size, err}`, `random.E_R.p2_5`). The F5_B0 rows repeat block (z).

**Columns and units:** `shots` prefix size; `E_R_minus_E0` and `E_R_minus_E0_sig` lattice energy units; `kt_width` Kato-Temple width; `rH` Weinstein residual; `W` captured weight; `recall_S999`; `false_positives` states of exact weight below $10^{-8}$; `B_sig` signal-support size; `random_E_R_p2_5` the 2.5th percentile of the Ritz energy of 200 random equal-size bases (absolute energy, lattice units).

```csv
token,scenario,family,shots,accepted,B_all,E_R_minus_E0,kt_width,rH,W,recall_S999,false_positives,B_sig,E_R_minus_E0_sig,random_E_R_p2_5
C4_F5_B0,E7_0.07,NAT-O0,2188,446,125,0.0105164,0.0300731,0.285135,0.99855319,0.825581,1,57,0.0249619,-5.45446
C4_F5_B0,E7_0.07,NAT-O0,4357,866,175,0.00570793,0.0167815,0.213188,0.99924531,0.918605,4,88,0.0129319,-5.47175
C4_F5_B0,E7_0.07,NAT-O0,8734,1719,223,0.00162795,0.00535718,0.120543,0.99980761,0.988372,6,135,0.00543572,-5.49348
C4_F5_B0,E7_0.07,NAT-O0,17468,3442,300,0.000632878,0.00210137,0.0755102,0.99992463,1,14,187,0.00181641,-5.51405
C4_F5_B0,E7_0.07,NAT-O0,34909,6848,372,0.000242659,0.000832453,0.0475297,0.99997189,1,29,256,0.000598769,-5.53281
C4_F1_B0,E1,NAT-O0,1715,540,113,0.0142521,0.0395313,0.326687,0.99796427,0.77907,3,53,0.0226087,-5.45363
C4_F1_B0,E1,NAT-O0,3404,1068,156,0.00559925,0.0172673,0.216256,0.99929023,0.953488,4,78,0.0155702,-5.46483
C4_F1_B0,E1,NAT-O0,6834,2144,201,0.00202341,0.00685639,0.136361,0.99977132,1,7,126,0.00489208,-5.47539
C4_F1_B0,E1,NAT-O0,13668,4289,262,0.000779688,0.00274844,0.0863547,0.99991405,1,11,169,0.00196752,-5.50234
C4_F1_B0,E1,NAT-O0,27309,8507,322,0.000329014,0.00114532,0.0557497,0.99996197,1,17,223,0.000785934,-5.52058
C4_F7_B0,E1,NAT-O2,1715,521,109,0.0104546,0.0282669,0.276443,0.99846154,0.837209,0,57,0.0319434,-5.45341
C4_F7_B0,E1,NAT-O2,3404,1057,157,0.00470287,0.0131859,0.189009,0.99933778,0.94186,2,81,0.0129247,-5.46192
C4_F7_B0,E1,NAT-O2,6834,2118,205,0.00160048,0.00514035,0.118079,0.99980479,1,6,118,0.00620048,-5.47296
C4_F7_B0,E1,NAT-O2,13668,4219,263,0.000772968,0.00258995,0.083828,0.99990889,1,14,172,0.00170225,-5.50053
C4_F7_B0,E1,NAT-O2,27309,8447,326,0.000334915,0.00108473,0.0542549,0.9999586,1,18,224,0.000828651,-5.52016
```

#### (ag) Per-run pooled clean fraction and rigorous bounds on the merged runs (MY ARITHMETIC from sourced numbers)

**Source:** the pooled $k=1$ fields of each file (`data.frun.clean_fraction.pooled_k1.{n_reference, shots, expected_from_garbage, f_hit}`) and `data.frun.at_N.certificate`; pooling recipe: numerator $\sum(n_{\rm ref}-g)$, denominator $\sum(n_{\rm ref}-g)/f_{\rm hit}$ per file, 95 % Garwood interval on $\sum n_{\rm ref}$ (reproduces the file's own interval for single files exactly); $\hat f_{\rm ideal}=f_{\rm hit}/1.1151352$. The bounds follow from the variational principle because the assembly sums the parts' accepted counts (`src/skqd/campaign33/assemble.py`): merged $E_R-E_0\le$ the smallest file value; merged recall and $W\ge$ the largest file value. **Not the assembly's numbers.**

**Columns and units:** `run`; `scenario`; `family`; `sector`; `kind`; `files` the JSON files pooled; `shots_done`, `shots_requested`, `accepted`, `n_ref_k1`, `shots_k1` counts; `f_hit`, `f_hat_ideal` with 95 % intervals; `merged_E_R_minus_E0_upper_bound`; `merged_recall_S999_lower_bound`; `merged_W_lower_bound`; `part_width_min/max` the certificate widths of the files; `part_B_all_max`.

```csv
run,scenario,family,sector,kind,files,shots_done,shots_requested,accepted,n_ref_k1,shots_k1,f_hit,f_hit_lo,f_hit_hi,f_hat_ideal,f_hat_ideal_lo,f_hat_ideal_hi,merged_E_R_minus_E0_upper_bound,merged_recall_S999_lower_bound,merged_W_lower_bound,part_width_min,part_width_max,part_B_all_max
F5_B0,E7_0.07,NAT-O0,B0,plan 0.10,C4_F5_B0,34909,34909,6848,284,2136,0.144482,0.128165,0.162301,0.129565,0.114932,0.145543,2.426586e-04,1.000000,0.99997189,8.324527e-04,8.324527e-04,372
F1_B0,E1,NAT-O0,B0,plan 0.15,C4_F1_B0,27309,27309,8507,500,2136,0.254371,0.232560,0.277676,0.228107,0.208549,0.249006,3.290145e-04,1.000000,0.99996197,1.145322e-03,1.145322e-03,322
F7_B0,E1,NAT-O2,B0,plan 0.15,C4_F7_B0,27309,27309,8447,488,2136,0.248266,0.226724,0.271302,0.222633,0.203316,0.243291,3.349148e-04,1.000000,0.99995860,1.084733e-03,1.084733e-03,326
F5_B1,E7_0.07,NAT-O0,B1,plan 0.10,C4_F5_B1+C4_PART_01,99000,99000,18986,215,1800,0.130174,0.113354,0.148786,0.116734,0.101650,0.133424,1.760202e-04,1.000000,0.99997518,3.635055e-02,4.806541e-02,346
F1_B1,E1,NAT-O0,B1,plan 0.15,C4_F1_B1+C4_PART_10,67600,67600,20377,401,1800,0.242790,0.219605,0.267757,0.217723,0.196932,0.240112,2.376368e-04,1.000000,0.99996848,4.367365e-02,4.645068e-02,313
F7_B1,E1,NAT-O2,B1,plan 0.15,C4_F7_B1+C4_PART_11,67600,67600,20384,433,1800,0.262165,0.238050,0.288061,0.235097,0.213472,0.258319,3.055368e-04,1.000000,0.99995756,4.799003e-02,5.365177e-02,319
F4_B0a,E7_0.10,NAT-O0,B0,s3quota half a,C4_F4_B0a+C4_PART_02,95712,100000,23284,4243,23928,0.192692,0.186937,0.198579,0.172797,0.167636,0.178076,1.211891e-04,1.000000,0.99998735,4.585320e-04,9.161115e-04,376
F4_B0b,E7_0.10,NAT-O0,B0,s3quota half b,C4_F4_B0b+C4_PART_04,95712,100000,23418,4018,23928,0.182474,0.176875,0.188205,0.163634,0.158613,0.168773,1.817042e-04,1.000000,0.99997885,6.153323e-04,1.042297e-03,371
F4_B1a,E7_0.10,NAT-O0,B1,s3quota half a,C4_F4_B1a+C4_PART_03,99996,99996,23866,4234,24999,0.184581,0.179063,0.190226,0.165523,0.160575,0.170586,3.130302e-04,1.000000,0.99995925,5.074570e-02,5.653914e-02,298
F4_B1b,E7_0.10,NAT-O0,B1,s3quota half b,C4_F4_B1b+C4_PART_05,99996,99996,23787,4091,24999,0.178347,0.172923,0.183898,0.159933,0.155069,0.164910,4.908841e-04,1.000000,0.99993461,6.267904e-02,8.923288e-02,288
F8_B0a,E8,IR-L3-RZZ,B0,s3quota half a,C4_F8_B0a+C4_PART_06,100000,100000,19522,3014,25000,0.131009,0.126373,0.135771,0.117482,0.113325,0.121753,2.541995e-04,1.000000,0.99997365,9.259811e-04,9.576657e-04,395
F8_B0b,E8,IR-L3-RZZ,B0,s3quota half b,C4_F8_B0b+C4_PART_08,100000,100000,19658,3137,25000,0.136355,0.131625,0.141212,0.122277,0.118035,0.126632,1.255073e-04,1.000000,0.99998722,4.817047e-04,6.942748e-04,389
F8_B1a,E8,IR-L3-RZZ,B1,s3quota half a,C4_F8_B1a+C4_PART_07,99996,99996,19200,3115,24999,0.135798,0.131071,0.140652,0.121777,0.117538,0.126130,4.864056e-04,1.000000,0.99993427,6.246555e-02,7.904561e-02,277
F8_B1b,E8,IR-L3-RZZ,B1,s3quota half b,C4_F8_B1b+C4_PART_09,99996,99996,19059,3111,24999,0.135624,0.130899,0.140475,0.121621,0.117384,0.125971,3.992220e-04,1.000000,0.99994451,5.532634e-02,7.506737e-02,287
F4_B0 (a+b),E7_0.10,NAT-O0,B0,s3quota merged,C4_F4_B0a+C4_PART_02+C4_F4_B0b+C4_PART_04,191424,200000,46702,8261,47856,0.187583,0.183560,0.191673,0.168216,0.164607,0.171883,1.211891e-04,1.000000,0.99998735,4.585320e-04,1.042297e-03,376
F4_B1 (a+b),E7_0.10,NAT-O0,B1,s3quota merged,C4_F4_B1a+C4_PART_03+C4_F4_B1b+C4_PART_05,199992,199992,47653,8325,49998,0.181464,0.177587,0.185405,0.162728,0.159251,0.166262,3.130302e-04,1.000000,0.99995925,5.074570e-02,8.923288e-02,298
F8_B0 (a+b),E8,IR-L3-RZZ,B0,s3quota merged,C4_F8_B0a+C4_PART_06+C4_F8_B0b+C4_PART_08,200000,200000,39180,6151,50000,0.133682,0.130362,0.137065,0.119879,0.116902,0.122913,1.255073e-04,1.000000,0.99998722,4.817047e-04,9.576657e-04,395
F8_B1 (a+b),E8,IR-L3-RZZ,B1,s3quota merged,C4_F8_B1a+C4_PART_07+C4_F8_B1b+C4_PART_09,199992,199992,38259,6226,49998,0.135711,0.132360,0.139125,0.121699,0.118695,0.124760,3.992220e-04,1.000000,0.99994451,5.532634e-02,7.904561e-02,287
```

#### (ah) Reference-hit fraction per circuit, all 25 class-4 files (520 rows)

**Source:** `validation/<token>.json -> data.frun.clean_fraction.per_circuit.<circuit>` (`shots`, `accepted`, `reference_hits`, `p_reference`, `f_hit`, `f_hit_ci95`, `distinct_accepted`).

**Columns and units:** `token`; `run`; `scenario`; `sector`; `circuit` (`B<s>_ref<r>_k<k>`); `k` coarse-step order; `shots`, `accepted`, `reference_hits`, `distinct_accepted` counts (this file's shots only); `p_ref` ideal probability of the reference string; `f_hit` (+ 95 % interval; blank where the file stores none).

```csv
token,run,scenario,sector,circuit,k,shots,accepted,reference_hits,p_ref,f_hit,f_hit_lo,f_hit_hi,distinct_accepted
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref117_k1,1,267,45,34,0.928357,0.137167,0.094992,0.191677,9
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref117_k2,2,267,48,19,0.741412,0.095979,0.057785,0.149884,19
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref117_k3,3,267,52,20,0.506415,0.147913,0.090348,0.228441,22
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref117_k4,4,1367,302,72,0.292662,0.179966,0.140812,0.226638,69
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref169_k1,1,267,59,45,0.921630,0.182870,0.133386,0.244695,11
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref169_k2,2,267,47,29,0.720098,0.150831,0.101014,0.216619,13
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref169_k3,3,267,50,18,0.474101,0.142195,0.084273,0.224730,22
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref169_k4,4,1367,249,37,0.260090,0.104062,0.073268,0.143438,86
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref25_k1,1,267,47,29,0.915021,0.118700,0.079495,0.170474,15
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref25_k2,2,267,44,17,0.700263,0.090922,0.052965,0.145576,14
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref25_k3,3,1000,198,57,0.446764,0.127582,0.096629,0.165298,54
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref25_k4,4,17600,3526,585,0.236292,0.140664,0.129494,0.152539,273
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref333_k1,1,267,54,30,0.921630,0.121913,0.082254,0.174039,11
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref333_k2,2,267,53,30,0.720098,0.156032,0.105274,0.222747,14
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref333_k3,3,267,51,24,0.474101,0.189594,0.121476,0.282102,19
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref333_k4,4,1367,251,39,0.260091,0.109687,0.077997,0.149948,82
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref525_k1,1,267,52,39,0.916002,0.159461,0.113392,0.217989,10
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref525_k2,2,267,46,16,0.702617,0.085287,0.048748,0.138502,22
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref525_k3,3,267,39,11,0.448469,0.091863,0.045856,0.164369,21
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref525_k4,4,1500,287,47,0.235448,0.133075,0.097778,0.176964,87
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref70_k1,1,267,52,26,0.916002,0.106307,0.069443,0.155765,14
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref70_k2,2,267,53,28,0.702617,0.149253,0.099177,0.215713,18
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref70_k3,3,267,56,21,0.448469,0.175376,0.108560,0.268082,22
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref70_k4,4,1700,337,46,0.235448,0.114921,0.084135,0.153290,110
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref795_k1,1,267,56,43,0.921630,0.174742,0.126462,0.235377,10
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref795_k2,2,267,59,31,0.720098,0.161234,0.109550,0.228859,17
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref795_k3,3,267,51,14,0.474101,0.110596,0.060463,0.185562,23
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref795_k4,4,1367,239,42,0.260090,0.118125,0.085133,0.159673,64
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref86_k1,1,267,52,38,0.921630,0.154423,0.109279,0.211958,10
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref86_k2,2,267,52,24,0.720098,0.124826,0.079978,0.185731,17
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref86_k3,3,267,50,20,0.474101,0.157995,0.096506,0.244011,16
C4_F5_B0,F5_B0,E7_0.07,B0,B0_ref86_k4,4,1500,291,63,0.260090,0.161479,0.124084,0.206602,84
C4_F1_B0,F1_B0,E1,B0,B0_ref117_k1,1,267,78,58,0.928357,0.233991,0.177679,0.302488,10
C4_F1_B0,F1_B0,E1,B0,B0_ref117_k2,2,267,80,54,0.741412,0.272785,0.204924,0.355926,13
C4_F1_B0,F1_B0,E1,B0,B0_ref117_k3,3,267,79,36,0.506415,0.266245,0.186474,0.368596,21
C4_F1_B0,F1_B0,E1,B0,B0_ref117_k4,4,1267,374,99,0.292662,0.266985,0.216992,0.325046,67
C4_F1_B0,F1_B0,E1,B0,B0_ref169_k1,1,267,91,68,0.921630,0.276337,0.214586,0.350324,12
C4_F1_B0,F1_B0,E1,B0,B0_ref169_k2,2,267,82,55,0.720098,0.286061,0.215500,0.372348,18
C4_F1_B0,F1_B0,E1,B0,B0_ref169_k3,3,267,81,26,0.474101,0.205393,0.134169,0.300950,24
C4_F1_B0,F1_B0,E1,B0,B0_ref169_k4,4,1267,387,82,0.260090,0.248832,0.197903,0.308868,86
C4_F1_B0,F1_B0,E1,B0,B0_ref25_k1,1,267,83,57,0.915021,0.233309,0.176705,0.302279,18
C4_F1_B0,F1_B0,E1,B0,B0_ref25_k2,2,267,77,37,0.700263,0.197891,0.139333,0.272767,22
C4_F1_B0,F1_B0,E1,B0,B0_ref25_k3,3,10400,3273,1166,0.446764,0.250948,0.236749,0.265776,171
C4_F1_B0,F1_B0,E1,B0,B0_ref25_k4,4,1400,431,79,0.236292,0.238805,0.189063,0.297623,97
C4_F1_B0,F1_B0,E1,B0,B0_ref333_k1,1,267,80,62,0.921630,0.251954,0.193172,0.322995,14
C4_F1_B0,F1_B0,E1,B0,B0_ref333_k2,2,267,100,54,0.720098,0.280859,0.210990,0.366461,18
C4_F1_B0,F1_B0,E1,B0,B0_ref333_k3,3,267,68,32,0.474101,0.252792,0.172909,0.356868,22
C4_F1_B0,F1_B0,E1,B0,B0_ref333_k4,4,1267,391,87,0.260091,0.264005,0.211456,0.325650,92
C4_F1_B0,F1_B0,E1,B0,B0_ref525_k1,1,267,79,57,0.916002,0.233059,0.176516,0.301955,14
C4_F1_B0,F1_B0,E1,B0,B0_ref525_k2,2,267,91,47,0.702617,0.250533,0.184082,0.333157,24
C4_F1_B0,F1_B0,E1,B0,B0_ref525_k3,3,267,88,34,0.448469,0.283943,0.196638,0.396783,20
C4_F1_B0,F1_B0,E1,B0,B0_ref525_k4,4,1400,446,71,0.235448,0.215391,0.168221,0.271687,90
C4_F1_B0,F1_B0,E1,B0,B0_ref70_k1,1,267,94,71,0.916002,0.290301,0.226727,0.366176,15
C4_F1_B0,F1_B0,E1,B0,B0_ref70_k2,2,267,92,48,0.702617,0.255864,0.188653,0.339239,21
C4_F1_B0,F1_B0,E1,B0,B0_ref70_k3,3,267,96,32,0.448469,0.267241,0.182792,0.377265,32
C4_F1_B0,F1_B0,E1,B0,B0_ref70_k4,4,1500,507,95,0.235448,0.268987,0.217626,0.328823,112
C4_F1_B0,F1_B0,E1,B0,B0_ref795_k1,1,267,87,65,0.921630,0.264146,0.203862,0.336676,17
C4_F1_B0,F1_B0,E1,B0,B0_ref795_k2,2,267,77,44,0.720098,0.228848,0.166281,0.307218,20
C4_F1_B0,F1_B0,E1,B0,B0_ref795_k3,3,267,82,37,0.474101,0.292292,0.205800,0.402886,23
C4_F1_B0,F1_B0,E1,B0,B0_ref795_k4,4,1267,361,77,0.260090,0.233660,0.184400,0.292035,89
C4_F1_B0,F1_B0,E1,B0,B0_ref86_k1,1,267,78,62,0.921630,0.251954,0.193172,0.322995,12
C4_F1_B0,F1_B0,E1,B0,B0_ref86_k2,2,267,79,54,0.720098,0.280859,0.210990,0.366461,14
C4_F1_B0,F1_B0,E1,B0,B0_ref86_k3,3,267,85,36,0.474101,0.284392,0.199184,0.393719,20
C4_F1_B0,F1_B0,E1,B0,B0_ref86_k4,4,1400,410,90,0.260090,0.247163,0.198748,0.303806,87
C4_F7_B0,F7_B0,E1,B0,B0_ref117_k1,1,267,83,73,0.928357,0.294507,0.230846,0.370298,8
C4_F7_B0,F7_B0,E1,B0,B0_ref117_k2,2,267,83,41,0.741412,0.207114,0.148628,0.280974,19
C4_F7_B0,F7_B0,E1,B0,B0_ref117_k3,3,267,74,33,0.506415,0.244058,0.167998,0.342749,20
C4_F7_B0,F7_B0,E1,B0,B0_ref117_k4,4,1267,376,99,0.292662,0.266985,0.216992,0.325046,67
C4_F7_B0,F7_B0,E1,B0,B0_ref169_k1,1,267,78,57,0.921630,0.231635,0.175438,0.300111,12
C4_F7_B0,F7_B0,E1,B0,B0_ref169_k2,2,267,73,49,0.720098,0.254854,0.188542,0.336931,12
C4_F7_B0,F7_B0,E1,B0,B0_ref169_k3,3,267,80,29,0.474101,0.229093,0.153426,0.329017,27
C4_F7_B0,F7_B0,E1,B0,B0_ref169_k4,4,1267,382,81,0.260090,0.245798,0.195198,0.305505,91
C4_F7_B0,F7_B0,E1,B0,B0_ref25_k1,1,267,86,58,0.915021,0.237402,0.180269,0.306897,16
C4_F7_B0,F7_B0,E1,B0,B0_ref25_k2,2,267,88,54,0.700263,0.288815,0.216966,0.376841,22
C4_F7_B0,F7_B0,E1,B0,B0_ref25_k3,3,10400,3288,1123,0.446764,0.241693,0.227762,0.256254,161
C4_F7_B0,F7_B0,E1,B0,B0_ref25_k4,4,1400,428,83,0.236292,0.250896,0.199837,0.311025,97
C4_F7_B0,F7_B0,E1,B0,B0_ref333_k1,1,267,88,68,0.921630,0.276337,0.214586,0.350324,16
C4_F7_B0,F7_B0,E1,B0,B0_ref333_k2,2,267,80,51,0.720098,0.265256,0.197500,0.348763,18
C4_F7_B0,F7_B0,E1,B0,B0_ref333_k3,3,267,80,28,0.474101,0.221193,0.146981,0.319687,27
C4_F7_B0,F7_B0,E1,B0,B0_ref333_k4,4,1267,406,82,0.260091,0.248832,0.197903,0.308867,92
C4_F7_B0,F7_B0,E1,B0,B0_ref525_k1,1,267,78,55,0.916002,0.224881,0.169411,0.292714,15
C4_F7_B0,F7_B0,E1,B0,B0_ref525_k2,2,267,78,33,0.702617,0.175906,0.121085,0.247038,19
C4_F7_B0,F7_B0,E1,B0,B0_ref525_k3,3,267,82,32,0.448469,0.267241,0.182792,0.377265,29
C4_F7_B0,F7_B0,E1,B0,B0_ref525_k4,4,1400,459,74,0.235448,0.224492,0.176274,0.281830,95
C4_F7_B0,F7_B0,E1,B0,B0_ref70_k1,1,267,76,57,0.916002,0.233059,0.176516,0.301955,13
C4_F7_B0,F7_B0,E1,B0,B0_ref70_k2,2,267,81,43,0.702617,0.229211,0.165881,0.308747,21
C4_F7_B0,F7_B0,E1,B0,B0_ref70_k3,3,267,83,32,0.448469,0.267241,0.182792,0.377265,25
C4_F7_B0,F7_B0,E1,B0,B0_ref70_k4,4,1500,443,78,0.235448,0.220852,0.174573,0.275634,96
C4_F7_B0,F7_B0,E1,B0,B0_ref795_k1,1,267,91,63,0.921630,0.256018,0.196731,0.327559,12
C4_F7_B0,F7_B0,E1,B0,B0_ref795_k2,2,267,69,37,0.720098,0.192440,0.135495,0.265254,18
C4_F7_B0,F7_B0,E1,B0,B0_ref795_k3,3,267,94,34,0.474101,0.268592,0.186007,0.375331,25
C4_F7_B0,F7_B0,E1,B0,B0_ref795_k4,4,1267,387,90,0.260090,0.273109,0.219611,0.335698,84
C4_F7_B0,F7_B0,E1,B0,B0_ref86_k1,1,267,83,57,0.921630,0.231635,0.175438,0.300111,14
C4_F7_B0,F7_B0,E1,B0,B0_ref86_k2,2,267,86,50,0.720098,0.260055,0.193017,0.342850,16
C4_F7_B0,F7_B0,E1,B0,B0_ref86_k3,3,267,81,29,0.474101,0.229093,0.153426,0.329017,21
C4_F7_B0,F7_B0,E1,B0,B0_ref86_k4,4,1400,403,77,0.260090,0.211461,0.166881,0.264291,90
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref27_k1,1,300,65,37,0.912199,0.135203,0.095195,0.186360,14
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref27_k2,2,300,65,26,0.691321,0.125363,0.081891,0.183686,18
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref27_k3,3,300,55,18,0.433194,0.138504,0.082085,0.218897,23
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref27_k4,4,14800,2911,471,0.222562,0.142987,0.130363,0.156503,200
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref29_k1,1,300,54,38,0.928308,0.136448,0.096558,0.187286,11
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref29_k2,2,300,60,37,0.741693,0.166285,0.117080,0.229202,13
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref29_k3,3,300,52,19,0.508105,0.124644,0.075043,0.194648,20
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref29_k4,4,11400,2050,469,0.296637,0.138686,0.126416,0.151824,147
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref57_k1,1,300,56,30,0.912199,0.109624,0.073963,0.156496,12
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref57_k2,2,300,61,25,0.691321,0.120541,0.078007,0.177943,17
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref57_k3,3,300,61,21,0.433194,0.161588,0.100025,0.247006,23
C4_F5_B1,F5_B1,E7_0.07,B1,B1_ref57_k4,4,20600,4064,675,0.222562,0.147222,0.136324,0.158760,168
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref27_k1,1,300,55,32,0.912199,0.116932,0.079981,0.165074,14
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref27_k2,2,300,62,32,0.691321,0.154293,0.105536,0.217816,15
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref27_k3,3,300,49,11,0.433194,0.084640,0.042251,0.151447,24
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref27_k4,4,14800,2828,481,0.222562,0.146023,0.133263,0.159675,191
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref29_k1,1,300,52,42,0.928308,0.150811,0.108691,0.203853,8
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref29_k2,2,300,58,35,0.741693,0.157296,0.109562,0.218762,15
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref29_k3,3,300,50,16,0.508105,0.104963,0.059995,0.170455,21
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref29_k4,4,11400,2084,521,0.296637,0.154063,0.141116,0.167878,151
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref57_k1,1,300,55,36,0.912199,0.131549,0.092135,0.182120,12
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref57_k2,2,300,62,33,0.691321,0.159114,0.109527,0.223456,14
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref57_k3,3,300,54,18,0.433194,0.138504,0.082085,0.218897,18
C4_PART_01,F5_B1,E7_0.07,B1,B1_ref57_k4,4,20600,4023,666,0.222562,0.145259,0.134435,0.156723,164
C4_F1_B1,F1_B1,E1,B1,B1_ref27_k1,1,300,102,67,0.912199,0.244828,0.189738,0.310924,14
C4_F1_B1,F1_B1,E1,B1,B1_ref27_k2,2,300,103,63,0.691321,0.303765,0.233421,0.388648,17
C4_F1_B1,F1_B1,E1,B1,B1_ref27_k3,3,300,97,41,0.433194,0.315484,0.226396,0.427991,27
C4_F1_B1,F1_B1,E1,B1,B1_ref27_k4,4,9900,3010,561,0.222562,0.254607,0.233971,0.276575,180
C4_F1_B1,F1_B1,E1,B1,B1_ref29_k1,1,300,81,67,0.928308,0.240580,0.186446,0.305528,10
C4_F1_B1,F1_B1,E1,B1,B1_ref29_k2,2,300,95,54,0.741693,0.242687,0.182313,0.316654,18
C4_F1_B1,F1_B1,E1,B1,B1_ref29_k3,3,300,98,45,0.508105,0.295213,0.215330,0.395018,22
C4_F1_B1,F1_B1,E1,B1,B1_ref29_k4,4,7500,2154,520,0.296637,0.233728,0.214068,0.254708,129
C4_F1_B1,F1_B1,E1,B1,B1_ref57_k1,1,300,93,62,0.912199,0.226558,0.173700,0.290437,13
C4_F1_B1,F1_B1,E1,B1,B1_ref57_k2,2,300,91,52,0.691321,0.250727,0.187254,0.328795,15
C4_F1_B1,F1_B1,E1,B1,B1_ref57_k3,3,300,90,34,0.433194,0.261621,0.181179,0.365590,28
C4_F1_B1,F1_B1,E1,B1,B1_ref57_k4,4,13700,4259,800,0.222562,0.262369,0.244500,0.281198,150
C4_PART_10,F1_B1,E1,B1,B1_ref27_k1,1,300,90,67,0.912199,0.244828,0.189738,0.310924,12
C4_PART_10,F1_B1,E1,B1,B1_ref27_k2,2,300,98,54,0.691321,0.260370,0.195598,0.339727,21
C4_PART_10,F1_B1,E1,B1,B1_ref27_k3,3,300,93,32,0.433194,0.246231,0.168421,0.347606,27
C4_PART_10,F1_B1,E1,B1,B1_ref27_k4,4,9900,2910,520,0.222562,0.235999,0.216148,0.257183,172
C4_PART_10,F1_B1,E1,B1,B1_ref29_k1,1,300,90,68,0.928308,0.244171,0.189608,0.309545,12
C4_PART_10,F1_B1,E1,B1,B1_ref29_k2,2,300,88,52,0.741693,0.233698,0.174537,0.306464,15
C4_PART_10,F1_B1,E1,B1,B1_ref29_k3,3,300,84,40,0.508105,0.262411,0.187470,0.357330,24
C4_PART_10,F1_B1,E1,B1,B1_ref29_k4,4,7500,2218,572,0.296637,0.257101,0.236460,0.279061,138
C4_PART_10,F1_B1,E1,B1,B1_ref57_k1,1,300,98,70,0.912199,0.255791,0.199401,0.323177,15
C4_PART_10,F1_B1,E1,B1,B1_ref57_k2,2,300,93,52,0.691321,0.250727,0.187254,0.328795,20
C4_PART_10,F1_B1,E1,B1,B1_ref57_k3,3,300,89,32,0.433194,0.246231,0.168421,0.347606,28
C4_PART_10,F1_B1,E1,B1,B1_ref57_k4,4,13700,4153,769,0.222562,0.252202,0.234689,0.270675,145
C4_F7_B1,F7_B1,E1,B1,B1_ref27_k1,1,300,107,82,0.912199,0.299641,0.238313,0.371934,14
C4_F7_B1,F7_B1,E1,B1,B1_ref27_k2,2,300,87,40,0.691321,0.192866,0.137786,0.262630,18
C4_F7_B1,F7_B1,E1,B1,B1_ref27_k3,3,300,104,34,0.433194,0.261621,0.181179,0.365590,28
C4_F7_B1,F7_B1,E1,B1,B1_ref27_k4,4,9900,3049,588,0.222562,0.266861,0.245724,0.289330,179
C4_F7_B1,F7_B1,E1,B1,B1_ref29_k1,1,300,100,81,0.928308,0.290851,0.230977,0.361501,14
C4_F7_B1,F7_B1,E1,B1,B1_ref29_k2,2,300,92,61,0.741693,0.274146,0.209700,0.352153,16
C4_F7_B1,F7_B1,E1,B1,B1_ref29_k3,3,300,84,22,0.508105,0.144325,0.090447,0.218511,21
C4_F7_B1,F7_B1,E1,B1,B1_ref29_k4,4,7500,2205,557,0.296637,0.250359,0.229996,0.272041,137
C4_F7_B1,F7_B1,E1,B1,B1_ref57_k1,1,300,86,58,0.912199,0.211941,0.160935,0.273983,16
C4_F7_B1,F7_B1,E1,B1,B1_ref57_k2,2,300,97,48,0.691321,0.231440,0.170645,0.306856,17
C4_F7_B1,F7_B1,E1,B1,B1_ref57_k3,3,300,111,35,0.433194,0.269315,0.187587,0.374553,29
C4_F7_B1,F7_B1,E1,B1,B1_ref57_k4,4,13700,4090,740,0.222562,0.242691,0.225517,0.260825,134
C4_PART_11,F7_B1,E1,B1,B1_ref27_k1,1,300,99,74,0.912199,0.270408,0.212328,0.339472,12
C4_PART_11,F7_B1,E1,B1,B1_ref27_k2,2,300,100,61,0.691321,0.294122,0.224979,0.377812,19
C4_PART_11,F7_B1,E1,B1,B1_ref27_k3,3,300,100,33,0.433194,0.253926,0.174790,0.356607,25
C4_PART_11,F7_B1,E1,B1,B1_ref27_k4,4,9900,2981,620,0.222562,0.281384,0.259668,0.304432,161
C4_PART_11,F7_B1,E1,B1,B1_ref29_k1,1,300,88,65,0.928308,0.233399,0.180132,0.297486,11
C4_PART_11,F7_B1,E1,B1,B1_ref29_k2,2,300,94,66,0.741693,0.296617,0.229403,0.377370,12
C4_PART_11,F7_B1,E1,B1,B1_ref29_k3,3,300,96,45,0.508105,0.295213,0.215330,0.395018,24
C4_PART_11,F7_B1,E1,B1,B1_ref29_k4,4,7500,2183,517,0.296637,0.232379,0.212777,0.253302,132
C4_PART_11,F7_B1,E1,B1,B1_ref57_k1,1,300,96,73,0.912199,0.266754,0.209092,0.335403,17
C4_PART_11,F7_B1,E1,B1,B1_ref57_k2,2,300,96,51,0.691321,0.245905,0.183092,0.323320,21
C4_PART_11,F7_B1,E1,B1,B1_ref57_k3,3,300,87,37,0.433194,0.284705,0.200458,0.392429,22
C4_PART_11,F7_B1,E1,B1,B1_ref57_k4,4,13700,4152,755,0.222562,0.247610,0.230260,0.265921,143
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref117_k1,1,1563,386,286,0.928357,0.197101,0.174918,0.221319,27
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref117_k2,2,1563,375,220,0.741412,0.189846,0.165586,0.216659,34
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref117_k3,3,1563,350,141,0.506415,0.178135,0.149946,0.210083,45
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref117_k4,4,1563,386,98,0.292662,0.214237,0.173927,0.261087,76
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref169_k1,1,1563,359,283,0.921630,0.196457,0.174233,0.220731,25
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref169_k2,2,1563,377,214,0.720098,0.190134,0.165511,0.217387,44
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref169_k3,3,1563,364,136,0.474101,0.183529,0.153981,0.217094,69
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref169_k4,4,1563,340,90,0.260090,0.221387,0.178021,0.272123,88
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref25_k1,1,1563,414,259,0.915021,0.181095,0.159710,0.204547,36
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref25_k2,2,1563,375,185,0.700263,0.169024,0.145544,0.195213,63
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref25_k3,3,1563,403,126,0.446764,0.180438,0.150310,0.214835,72
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref25_k4,4,1563,368,56,0.236292,0.151624,0.114534,0.196898,94
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref333_k1,1,1563,374,261,0.921630,0.181185,0.159869,0.204553,27
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref333_k2,2,1563,361,201,0.720098,0.178584,0.154747,0.205053,43
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref333_k3,3,1563,366,145,0.474101,0.195674,0.165121,0.230241,64
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref333_k4,4,1563,354,72,0.260091,0.177109,0.138576,0.223040,88
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref525_k1,1,1563,426,294,0.916002,0.205348,0.182543,0.230213,38
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref525_k2,2,1563,391,200,0.702617,0.182116,0.157750,0.209181,43
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref525_k3,3,1563,393,127,0.448469,0.181179,0.151040,0.215568,75
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref525_k4,4,1563,393,72,0.235448,0.195645,0.153079,0.246384,99
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref70_k1,1,1563,438,267,0.916002,0.186489,0.164789,0.210252,29
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref70_k2,2,1563,386,201,0.702617,0.183027,0.158597,0.210154,61
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref70_k3,3,1563,360,120,0.448469,0.171192,0.141935,0.204704,78
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref70_k4,4,1563,384,68,0.235448,0.184776,0.143485,0.234249,99
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref795_k1,1,1563,422,322,0.921630,0.223531,0.199780,0.249329,28
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref795_k2,2,1563,360,180,0.720098,0.159926,0.137415,0.185072,52
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref795_k3,3,1563,382,128,0.474101,0.172733,0.144106,0.205380,76
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref795_k4,4,1563,412,80,0.260090,0.196788,0.156040,0.244921,100
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref86_k1,1,1563,353,264,0.921630,0.183268,0.161825,0.206761,29
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref86_k2,2,1563,373,196,0.720098,0.174142,0.150614,0.200302,43
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref86_k3,3,1563,377,138,0.474101,0.186228,0.156454,0.220019,75
C4_F4_B0a,F4_B0a,E7_0.10,B0,B0_ref86_k4,4,1563,357,78,0.260090,0.191868,0.151663,0.239461,86
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref117_k1,1,1428,356,271,0.928357,0.204420,0.180804,0.230264,18
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref117_k2,2,1428,329,205,0.741412,0.193626,0.168026,0.222023,39
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref117_k3,3,1428,334,135,0.506415,0.186679,0.156518,0.220957,46
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref117_k4,4,1428,342,84,0.292662,0.200992,0.160318,0.248842,62
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref169_k1,1,1428,304,227,0.921630,0.172480,0.150770,0.196437,24
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref169_k2,2,1428,331,190,0.720098,0.184770,0.159430,0.212993,40
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref169_k3,3,1428,339,133,0.474101,0.196448,0.164482,0.232814,57
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref169_k4,4,1428,323,60,0.260090,0.161543,0.123274,0.207940,95
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref25_k1,1,1428,364,229,0.915021,0.175256,0.153291,0.199486,34
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref25_k2,2,1428,342,176,0.700263,0.176003,0.150960,0.204013,47
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref25_k3,3,1428,321,113,0.446764,0.177120,0.145971,0.212947,54
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref25_k4,4,1428,352,60,0.236292,0.177813,0.135689,0.228882,88
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref333_k1,1,1428,360,262,0.921630,0.199074,0.175696,0.224696,29
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref333_k2,2,1428,374,216,0.720098,0.210054,0.182974,0.240014,41
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref333_k3,3,1428,351,126,0.474101,0.186109,0.155033,0.221586,71
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref333_k4,4,1428,348,94,0.260091,0.253086,0.204519,0.309714,80
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref525_k1,1,1428,383,264,0.916002,0.201826,0.178212,0.227698,29
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref525_k2,2,1428,391,209,0.702617,0.208304,0.181018,0.238540,54
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref525_k3,3,1428,345,124,0.448469,0.193623,0.161045,0.230855,66
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref525_k4,4,1428,369,56,0.235448,0.166554,0.125812,0.216285,103
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref70_k1,1,1428,360,248,0.916002,0.189594,0.166730,0.214718,28
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref70_k2,2,1428,362,178,0.702617,0.177407,0.152301,0.205469,51
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref70_k3,3,1428,358,134,0.448469,0.209237,0.175311,0.247813,66
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref70_k4,4,1428,367,55,0.235448,0.163580,0.123229,0.212922,98
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref795_k1,1,1428,335,254,0.921630,0.192995,0.169988,0.218248,30
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref795_k2,2,1428,343,194,0.720098,0.188660,0.163045,0.217157,44
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref795_k3,3,1428,352,128,0.474101,0.189063,0.157730,0.224797,65
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref795_k4,4,1428,328,63,0.260090,0.169621,0.130340,0.217020,93
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref86_k1,1,1428,357,252,0.921630,0.191476,0.168562,0.216634,29
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref86_k2,2,1428,330,197,0.720098,0.191577,0.165757,0.220279,40
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref86_k3,3,1428,350,141,0.474101,0.208265,0.175308,0.245617,62
C4_PART_02,F4_B0a,E7_0.10,B0,B0_ref86_k4,4,1428,325,86,0.260090,0.231547,0.185207,0.285960,80
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref117_k1,1,1563,374,275,0.928357,0.189521,0.167781,0.213295,21
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref117_k2,2,1563,378,244,0.741412,0.210556,0.184964,0.238701,31
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref117_k3,3,1563,367,145,0.506415,0.183188,0.154585,0.215550,55
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref117_k4,4,1563,384,95,0.292662,0.207679,0.168024,0.253877,73
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref169_k1,1,1563,357,268,0.921630,0.186044,0.164435,0.209704,30
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref169_k2,2,1563,374,210,0.720098,0.186580,0.162197,0.213595,41
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref169_k3,3,1563,378,131,0.474101,0.176781,0.147806,0.209776,61
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref169_k4,4,1563,367,64,0.260090,0.157430,0.121239,0.201035,91
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref25_k1,1,1563,413,264,0.915021,0.184591,0.162994,0.208254,35
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref25_k2,2,1563,409,184,0.700263,0.168110,0.144696,0.194234,55
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref25_k3,3,1563,395,122,0.446764,0.174710,0.145086,0.208604,74
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref25_k4,4,1563,381,59,0.236292,0.159747,0.121606,0.206063,93
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref333_k1,1,1563,380,273,0.921630,0.189515,0.167699,0.213382,27
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref333_k2,2,1563,401,230,0.720098,0.204350,0.178792,0.232537,47
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref333_k3,3,1563,370,144,0.474101,0.194325,0.163882,0.228782,67
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref333_k4,4,1563,374,64,0.260091,0.157430,0.121239,0.201035,98
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref525_k1,1,1563,405,274,0.916002,0.191378,0.169386,0.215433,32
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref525_k2,2,1563,376,194,0.702617,0.176653,0.152668,0.203337,47
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref525_k3,3,1563,395,133,0.448469,0.189738,0.158864,0.224862,64
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref525_k4,4,1563,361,66,0.235448,0.179341,0.138701,0.228167,91
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref70_k1,1,1563,398,255,0.916002,0.178107,0.156916,0.201363,41
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref70_k2,2,1563,395,199,0.702617,0.181206,0.156902,0.208207,51
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref70_k3,3,1563,376,127,0.448469,0.181179,0.151040,0.215569,67
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref70_k4,4,1563,384,69,0.235448,0.187493,0.145880,0.237286,105
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref795_k1,1,1563,400,269,0.921630,0.186739,0.165088,0.210440,39
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref795_k2,2,1563,380,210,0.720098,0.186580,0.162197,0.213595,46
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref795_k3,3,1563,414,157,0.474101,0.211868,0.180023,0.247723,70
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref795_k4,4,1563,371,73,0.260090,0.179569,0.140753,0.225782,88
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref86_k1,1,1563,369,262,0.921630,0.181879,0.160521,0.205289,23
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref86_k2,2,1563,386,216,0.720098,0.191911,0.167170,0.219283,44
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref86_k3,3,1563,377,144,0.474101,0.194325,0.163882,0.228782,68
C4_F4_B0b,F4_B0b,E7_0.10,B0,B0_ref86_k4,4,1563,379,80,0.260090,0.196788,0.156040,0.244921,84
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref117_k1,1,1428,330,243,0.928357,0.183299,0.160975,0.207854,25
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref117_k2,2,1428,356,196,0.741412,0.185125,0.160114,0.212935,33
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref117_k3,3,1428,350,139,0.506415,0.192210,0.161585,0.226950,51
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref117_k4,4,1428,363,73,0.292662,0.174671,0.136913,0.219623,75
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref169_k1,1,1428,327,227,0.921630,0.172480,0.150770,0.196437,31
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref169_k2,2,1428,323,193,0.720098,0.187687,0.162141,0.216116,35
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref169_k3,3,1428,338,119,0.474101,0.175769,0.145610,0.210334,59
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref169_k4,4,1428,342,77,0.260090,0.207315,0.163609,0.259109,81
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref25_k1,1,1428,368,227,0.915021,0.173726,0.151859,0.197856,29
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref25_k2,2,1428,369,189,0.700263,0.189003,0.163017,0.217955,50
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref25_k3,3,1428,364,108,0.446764,0.169283,0.138865,0.204382,72
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref25_k4,4,1428,349,73,0.236292,0.216340,0.169575,0.272017,89
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref333_k1,1,1428,327,236,0.921630,0.179318,0.157168,0.203716,25
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref333_k2,2,1428,343,203,0.720098,0.197412,0.171188,0.226517,47
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref333_k3,3,1428,353,127,0.474101,0.187586,0.156381,0.223192,71
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref333_k4,4,1428,356,75,0.260091,0.201930,0.158830,0.253122,94
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref525_k1,1,1428,340,226,0.916002,0.172775,0.150982,0.196830,33
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref525_k2,2,1428,357,169,0.702617,0.168437,0.143999,0.195834,51
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref525_k3,3,1428,356,106,0.448469,0.165516,0.135510,0.200187,64
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref525_k4,4,1428,344,65,0.235448,0.193322,0.149201,0.246406,99
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref70_k1,1,1428,339,227,0.916002,0.173540,0.151697,0.197644,30
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref70_k2,2,1428,366,193,0.702617,0.192357,0.166175,0.221493,45
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref70_k3,3,1428,345,113,0.448469,0.176446,0.145416,0.212137,74
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref70_k4,4,1428,354,53,0.235448,0.157631,0.118075,0.206187,100
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref795_k1,1,1428,356,236,0.921630,0.179318,0.157168,0.203716,26
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref795_k2,2,1428,341,183,0.720098,0.177962,0.153111,0.205698,46
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref795_k3,3,1428,355,138,0.474101,0.203833,0.171245,0.240819,68
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref795_k4,4,1428,370,65,0.260090,0.175006,0.135065,0.223060,98
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref86_k1,1,1428,344,256,0.921630,0.194515,0.171415,0.219860,27
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref86_k2,2,1428,334,174,0.720098,0.169210,0.145001,0.196305,46
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref86_k3,3,1428,350,136,0.474101,0.200879,0.168538,0.237618,69
C4_PART_04,F4_B0b,E7_0.10,B0,B0_ref86_k4,4,1428,341,72,0.260090,0.193853,0.151677,0.244126,83
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref27_k1,1,4167,1104,746,0.912199,0.196256,0.182424,0.210859,45
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref27_k2,2,4167,976,500,0.691321,0.173566,0.158683,0.189468,75
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref27_k3,3,4167,1047,338,0.433194,0.187243,0.167811,0.208308,93
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref27_k4,4,4167,1036,162,0.222562,0.174675,0.148812,0.203741,130
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref29_k1,1,4167,914,718,0.928308,0.185612,0.172282,0.199700,39
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref29_k2,2,4167,937,562,0.741693,0.181838,0.167113,0.197513,47
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref29_k3,3,4167,907,352,0.508105,0.166250,0.149333,0.184557,73
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref29_k4,4,4167,954,226,0.296637,0.182832,0.159770,0.208287,104
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref57_k1,1,4167,1015,667,0.912199,0.175473,0.162407,0.189310,42
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref57_k2,2,4167,1028,528,0.691321,0.183285,0.167983,0.199607,55
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref57_k3,3,4167,1034,337,0.433194,0.186689,0.167287,0.207725,84
C4_F4_B1a,F4_B1a,E7_0.10,B1,B1_ref57_k4,4,4167,967,160,0.222562,0.172518,0.146822,0.201419,102
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref27_k1,1,4166,1044,689,0.912199,0.181304,0.168017,0.195362,43
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref27_k2,2,4166,977,512,0.691321,0.177774,0.162707,0.193861,67
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref27_k3,3,4166,1038,348,0.433194,0.192829,0.173099,0.214192,91
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref27_k4,4,4166,1008,169,0.222562,0.182267,0.155822,0.211913,127
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref29_k1,1,4166,994,744,0.928308,0.192380,0.178803,0.206714,34
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref29_k2,2,4166,962,616,0.741693,0.199358,0.183924,0.215742,59
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref29_k3,3,4166,908,393,0.508105,0.185659,0.167754,0.204953,69
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref29_k4,4,4166,963,258,0.296637,0.208770,0.184070,0.235861,109
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref57_k1,1,4166,1009,670,0.912199,0.176304,0.163206,0.190175,37
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref57_k2,2,4166,1039,541,0.691321,0.187843,0.172346,0.204360,63
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref57_k3,3,4166,1027,333,0.433194,0.184518,0.165229,0.205439,74
C4_PART_03,F4_B1a,E7_0.10,B1,B1_ref57_k4,4,4166,978,159,0.222562,0.171481,0.145862,0.200305,95
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref27_k1,1,4167,1004,654,0.912199,0.172053,0.159117,0.185760,47
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref27_k2,2,4167,1026,527,0.691321,0.182938,0.167651,0.199245,67
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref27_k3,3,4167,1035,336,0.433194,0.186135,0.166762,0.207141,107
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref27_k4,4,4167,1018,220,0.222562,0.237214,0.206902,0.270719,115
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref29_k1,1,4167,953,730,0.928308,0.188714,0.175271,0.202915,33
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref29_k2,2,4167,918,544,0.741693,0.176014,0.161532,0.191446,52
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref29_k3,3,4167,936,377,0.508105,0.178057,0.160535,0.196970,76
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref29_k4,4,4167,1012,227,0.296637,0.183641,0.160526,0.209149,113
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref57_k1,1,4167,1014,648,0.912199,0.170474,0.157600,0.184121,43
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref57_k2,2,4167,1004,540,0.691321,0.187451,0.171972,0.203949,54
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref57_k3,3,4167,992,323,0.433194,0.178934,0.159950,0.199551,73
C4_F4_B1b,F4_B1b,E7_0.10,B1,B1_ref57_k4,4,4167,948,179,0.222562,0.193005,0.165765,0.223445,93
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref27_k1,1,4166,1044,667,0.912199,0.175515,0.162446,0.189356,43
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref27_k2,2,4166,1040,504,0.691321,0.174996,0.160050,0.190963,69
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref27_k3,3,4166,1019,329,0.433194,0.182301,0.163132,0.203104,96
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref27_k4,4,4166,969,165,0.222562,0.177952,0.151835,0.207273,116
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref29_k1,1,4166,928,711,0.928308,0.183847,0.170580,0.197872,35
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref29_k2,2,4166,930,569,0.741693,0.184147,0.169325,0.199919,52
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref29_k3,3,4166,924,371,0.508105,0.175265,0.157882,0.194040,75
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref29_k4,4,4166,981,223,0.296637,0.180448,0.157539,0.205751,118
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref57_k1,1,4166,1038,681,0.912199,0.179199,0.165991,0.193178,45
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref57_k2,2,4166,1043,526,0.691321,0.182635,0.167359,0.198931,73
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref57_k3,3,4166,1039,331,0.433194,0.183409,0.164181,0.204272,68
C4_PART_05,F4_B1b,E7_0.10,B1,B1_ref57_k4,4,4166,972,158,0.222562,0.170403,0.144868,0.199143,96
C4_F8_B0a,F8_B0a,E8,B0,B0_ref117_k1,1,1563,280,191,0.928357,0.131630,0.113624,0.151680,26
C4_F8_B0a,F8_B0a,E8,B0,B0_ref117_k2,2,1563,300,164,0.741412,0.141521,0.120690,0.164915,30
C4_F8_B0a,F8_B0a,E8,B0,B0_ref117_k3,3,1563,311,119,0.506415,0.150340,0.124544,0.179905,60
C4_F8_B0a,F8_B0a,E8,B0,B0_ref117_k4,4,1563,315,71,0.292662,0.155212,0.121221,0.195779,79
C4_F8_B0a,F8_B0a,E8,B0,B0_ref169_k1,1,1563,299,209,0.921630,0.145087,0.126082,0.166147,29
C4_F8_B0a,F8_B0a,E8,B0,B0_ref169_k2,2,1563,296,162,0.720098,0.143933,0.122622,0.167883,46
C4_F8_B0a,F8_B0a,E8,B0,B0_ref169_k3,3,1563,302,110,0.474101,0.148442,0.122001,0.178913,67
C4_F8_B0a,F8_B0a,E8,B0,B0_ref169_k4,4,1563,314,69,0.260090,0.169729,0.132059,0.214804,94
C4_F8_B0a,F8_B0a,E8,B0,B0_ref25_k1,1,1563,290,159,0.915021,0.111174,0.094565,0.129860,30
C4_F8_B0a,F8_B0a,E8,B0,B0_ref25_k2,2,1563,307,142,0.700263,0.129737,0.109276,0.152916,55
C4_F8_B0a,F8_B0a,E8,B0,B0_ref25_k3,3,1563,316,94,0.446764,0.134612,0.108780,0.164732,75
C4_F8_B0a,F8_B0a,E8,B0,B0_ref25_k4,4,1563,292,46,0.236292,0.124548,0.091184,0.166131,101
C4_F8_B0a,F8_B0a,E8,B0,B0_ref333_k1,1,1563,292,176,0.921630,0.122178,0.104794,0.141622,39
C4_F8_B0a,F8_B0a,E8,B0,B0_ref333_k2,2,1563,277,148,0.720098,0.131494,0.111163,0.154468,42
C4_F8_B0a,F8_B0a,E8,B0,B0_ref333_k3,3,1563,322,108,0.474101,0.145743,0.119555,0.175962,75
C4_F8_B0a,F8_B0a,E8,B0,B0_ref333_k4,4,1563,285,55,0.260091,0.135291,0.101918,0.176100,96
C4_F8_B0a,F8_B0a,E8,B0,B0_ref525_k1,1,1563,294,166,0.916002,0.115944,0.098977,0.134985,33
C4_F8_B0a,F8_B0a,E8,B0,B0_ref525_k2,2,1563,309,132,0.702617,0.120196,0.100567,0.142538,54
C4_F8_B0a,F8_B0a,E8,B0,B0_ref525_k3,3,1563,329,89,0.448469,0.126967,0.101965,0.156244,83
C4_F8_B0a,F8_B0a,E8,B0,B0_ref525_k4,4,1563,303,46,0.235448,0.124994,0.091510,0.166726,115
C4_F8_B0a,F8_B0a,E8,B0,B0_ref70_k1,1,1563,300,170,0.916002,0.118738,0.101559,0.137990,31
C4_F8_B0a,F8_B0a,E8,B0,B0_ref70_k2,2,1563,325,154,0.702617,0.140229,0.118956,0.164209,53
C4_F8_B0a,F8_B0a,E8,B0,B0_ref70_k3,3,1563,304,89,0.448469,0.126967,0.101965,0.156244,69
C4_F8_B0a,F8_B0a,E8,B0,B0_ref70_k4,4,1563,306,39,0.235448,0.105973,0.075356,0.144870,109
C4_F8_B0a,F8_B0a,E8,B0,B0_ref795_k1,1,1563,289,191,0.921630,0.132591,0.114453,0.152787,30
C4_F8_B0a,F8_B0a,E8,B0,B0_ref795_k2,2,1563,280,139,0.720098,0.123498,0.103821,0.145819,46
C4_F8_B0a,F8_B0a,E8,B0,B0_ref795_k3,3,1563,294,90,0.474101,0.121452,0.097661,0.149286,65
C4_F8_B0a,F8_B0a,E8,B0,B0_ref795_k4,4,1563,305,57,0.260090,0.140211,0.106193,0.181660,88
C4_F8_B0a,F8_B0a,E8,B0,B0_ref86_k1,1,1563,325,224,0.921630,0.155500,0.135801,0.177252,31
C4_F8_B0a,F8_B0a,E8,B0,B0_ref86_k2,2,1563,289,160,0.720098,0.142156,0.120982,0.165970,41
C4_F8_B0a,F8_B0a,E8,B0,B0_ref86_k3,3,1563,309,107,0.474101,0.144393,0.118334,0.174485,63
C4_F8_B0a,F8_B0a,E8,B0,B0_ref86_k4,4,1563,327,65,0.260090,0.159890,0.123399,0.203793,89
C4_PART_06,F8_B0a,E8,B0,B0_ref117_k1,1,1562,282,186,0.928357,0.128267,0.110495,0.148083,25
C4_PART_06,F8_B0a,E8,B0,B0_ref117_k2,2,1562,269,143,0.741412,0.123478,0.104070,0.145456,35
C4_PART_06,F8_B0a,E8,B0,B0_ref117_k3,3,1562,323,130,0.506415,0.164343,0.137308,0.195144,48
C4_PART_06,F8_B0a,E8,B0,B0_ref117_k4,4,1562,287,73,0.292662,0.159686,0.125168,0.200782,62
C4_PART_06,F8_B0a,E8,B0,B0_ref169_k1,1,1562,285,198,0.921630,0.137538,0.119047,0.158088,31
C4_PART_06,F8_B0a,E8,B0,B0_ref169_k2,2,1562,317,181,0.720098,0.160917,0.138327,0.186144,44
C4_PART_06,F8_B0a,E8,B0,B0_ref169_k3,3,1562,288,108,0.474101,0.145836,0.119632,0.176074,56
C4_PART_06,F8_B0a,E8,B0,B0_ref169_k4,4,1562,310,59,0.260090,0.145223,0.110550,0.187329,104
C4_PART_06,F8_B0a,E8,B0,B0_ref25_k1,1,1562,336,194,0.915021,0.135733,0.117304,0.156236,35
C4_PART_06,F8_B0a,E8,B0,B0_ref25_k2,2,1562,359,181,0.700263,0.165475,0.142245,0.191417,53
C4_PART_06,F8_B0a,E8,B0,B0_ref25_k3,3,1562,339,98,0.446764,0.140430,0.114008,0.171140,81
C4_PART_06,F8_B0a,E8,B0,B0_ref25_k4,4,1562,306,50,0.236292,0.135465,0.100544,0.178595,84
C4_PART_06,F8_B0a,E8,B0,B0_ref333_k1,1,1562,305,190,0.921630,0.131981,0.113881,0.152141,36
C4_PART_06,F8_B0a,E8,B0,B0_ref333_k2,2,1562,298,159,0.720098,0.141358,0.120240,0.165118,45
C4_PART_06,F8_B0a,E8,B0,B0_ref333_k3,3,1562,289,120,0.474101,0.162041,0.134347,0.193761,66
C4_PART_06,F8_B0a,E8,B0,B0_ref333_k4,4,1562,315,69,0.260091,0.169838,0.132143,0.214941,86
C4_PART_06,F8_B0a,E8,B0,B0_ref525_k1,1,1562,303,178,0.916002,0.124405,0.106800,0.144084,32
C4_PART_06,F8_B0a,E8,B0,B0_ref525_k2,2,1562,316,137,0.702617,0.124829,0.104802,0.147569,47
C4_PART_06,F8_B0a,E8,B0,B0_ref525_k3,3,1562,309,99,0.448469,0.141324,0.114860,0.172057,86
C4_PART_06,F8_B0a,E8,B0,B0_ref525_k4,4,1562,311,58,0.235448,0.157703,0.119750,0.203869,104
C4_PART_06,F8_B0a,E8,B0,B0_ref70_k1,1,1562,314,179,0.916002,0.125104,0.107448,0.144834,32
C4_PART_06,F8_B0a,E8,B0,B0_ref70_k2,2,1562,326,156,0.702617,0.142141,0.120711,0.166280,46
C4_PART_06,F8_B0a,E8,B0,B0_ref70_k3,3,1562,310,88,0.448469,0.125621,0.100751,0.154769,72
C4_PART_06,F8_B0a,E8,B0,B0_ref70_k4,4,1562,280,54,0.235448,0.146827,0.110300,0.191579,93
C4_PART_06,F8_B0a,E8,B0,B0_ref795_k1,1,1562,302,202,0.921630,0.140317,0.121633,0.161059,26
C4_PART_06,F8_B0a,E8,B0,B0_ref795_k2,2,1562,312,160,0.720098,0.142247,0.121060,0.166076,40
C4_PART_06,F8_B0a,E8,B0,B0_ref795_k3,3,1562,298,98,0.474101,0.132333,0.107434,0.161272,67
C4_PART_06,F8_B0a,E8,B0,B0_ref795_k4,4,1562,298,64,0.260090,0.157531,0.121317,0.201164,75
C4_PART_06,F8_B0a,E8,B0,B0_ref86_k1,1,1562,300,201,0.921630,0.139622,0.120986,0.160317,38
C4_PART_06,F8_B0a,E8,B0,B0_ref86_k2,2,1562,327,170,0.720098,0.151138,0.129271,0.175643,49
C4_PART_06,F8_B0a,E8,B0,B0_ref86_k3,3,1562,302,108,0.474101,0.145836,0.119632,0.176074,68
C4_PART_06,F8_B0a,E8,B0,B0_ref86_k4,4,1562,320,70,0.260090,0.172299,0.134315,0.217691,78
C4_F8_B0b,F8_B0b,E8,B0,B0_ref117_k1,1,1563,282,195,0.928357,0.134387,0.116186,0.154631,27
C4_F8_B0b,F8_B0b,E8,B0,B0_ref117_k2,2,1563,297,160,0.741412,0.138069,0.117504,0.161198,37
C4_F8_B0b,F8_B0b,E8,B0,B0_ref117_k3,3,1563,301,116,0.506415,0.146550,0.121097,0.175774,50
C4_F8_B0b,F8_B0b,E8,B0,B0_ref117_k4,4,1563,290,69,0.292662,0.150839,0.117361,0.190898,65
C4_F8_B0b,F8_B0b,E8,B0,B0_ref169_k1,1,1563,301,193,0.921630,0.133979,0.115743,0.154273,32
C4_F8_B0b,F8_B0b,E8,B0,B0_ref169_k2,2,1563,290,157,0.720098,0.139491,0.118524,0.163097,42
C4_F8_B0b,F8_B0b,E8,B0,B0_ref169_k3,3,1563,301,97,0.474101,0.130899,0.106150,0.159686,63
C4_F8_B0b,F8_B0b,E8,B0,B0_ref169_k4,4,1563,288,67,0.260090,0.164810,0.127724,0.209303,85
C4_F8_B0b,F8_B0b,E8,B0,B0_ref25_k1,1,1563,335,200,0.915021,0.139842,0.121131,0.160624,40
C4_F8_B0b,F8_B0b,E8,B0,B0_ref25_k2,2,1563,313,150,0.700263,0.137046,0.115992,0.160817,46
C4_F8_B0b,F8_B0b,E8,B0,B0_ref25_k3,3,1563,328,92,0.446764,0.131748,0.106207,0.161578,75
C4_F8_B0b,F8_B0b,E8,B0,B0_ref25_k4,4,1563,290,42,0.236292,0.113717,0.081956,0.153714,88
C4_F8_B0b,F8_B0b,E8,B0,B0_ref333_k1,1,1563,287,195,0.921630,0.135368,0.117034,0.155759,32
C4_F8_B0b,F8_B0b,E8,B0,B0_ref333_k2,2,1563,296,163,0.720098,0.144822,0.123442,0.168840,41
C4_F8_B0b,F8_B0b,E8,B0,B0_ref333_k3,3,1563,313,109,0.474101,0.147092,0.120778,0.177438,71
C4_F8_B0b,F8_B0b,E8,B0,B0_ref333_k4,4,1563,306,67,0.260091,0.164809,0.127724,0.209303,94
C4_F8_B0b,F8_B0b,E8,B0,B0_ref525_k1,1,1563,316,195,0.916002,0.136200,0.117753,0.156716,32
C4_F8_B0b,F8_B0b,E8,B0,B0_ref525_k2,2,1563,323,158,0.702617,0.143872,0.122313,0.168136,47
C4_F8_B0b,F8_B0b,E8,B0,B0_ref525_k3,3,1563,327,90,0.448469,0.128394,0.103243,0.157818,76
C4_F8_B0b,F8_B0b,E8,B0,B0_ref525_k4,4,1563,311,49,0.235448,0.133146,0.098501,0.176028,98
C4_F8_B0b,F8_B0b,E8,B0,B0_ref70_k1,1,1563,333,203,0.916002,0.141787,0.122952,0.162691,37
C4_F8_B0b,F8_B0b,E8,B0,B0_ref70_k2,2,1563,321,142,0.702617,0.129302,0.108910,0.152404,57
C4_F8_B0b,F8_B0b,E8,B0,B0_ref70_k3,3,1563,324,102,0.448469,0.145513,0.118648,0.176643,76
C4_F8_B0b,F8_B0b,E8,B0,B0_ref70_k4,4,1563,317,50,0.235448,0.135864,0.100840,0.179121,102
C4_F8_B0b,F8_B0b,E8,B0,B0_ref795_k1,1,1563,305,187,0.921630,0.129814,0.111874,0.149813,28
C4_F8_B0b,F8_B0b,E8,B0,B0_ref795_k2,2,1563,303,157,0.720098,0.139491,0.118524,0.163097,41
C4_F8_B0b,F8_B0b,E8,B0,B0_ref795_k3,3,1563,314,100,0.474101,0.134947,0.109798,0.164132,71
C4_F8_B0b,F8_B0b,E8,B0,B0_ref795_k4,4,1563,280,47,0.260090,0.115612,0.084946,0.153740,73
C4_F8_B0b,F8_B0b,E8,B0,B0_ref86_k1,1,1563,313,208,0.921630,0.144392,0.125435,0.165406,32
C4_F8_B0b,F8_B0b,E8,B0,B0_ref86_k2,2,1563,284,157,0.720098,0.139491,0.118524,0.163097,44
C4_F8_B0b,F8_B0b,E8,B0,B0_ref86_k3,3,1563,314,115,0.474101,0.155189,0.128124,0.186282,70
C4_F8_B0b,F8_B0b,E8,B0,B0_ref86_k4,4,1563,295,58,0.260090,0.142670,0.108335,0.184436,91
C4_PART_08,F8_B0b,E8,B0,B0_ref117_k1,1,1562,280,196,0.928357,0.135163,0.116901,0.155468,26
C4_PART_08,F8_B0b,E8,B0,B0_ref117_k2,2,1562,282,142,0.741412,0.122615,0.103277,0.144522,40
C4_PART_08,F8_B0b,E8,B0,B0_ref117_k3,3,1562,303,115,0.506415,0.145380,0.120026,0.174507,60
C4_PART_08,F8_B0b,E8,B0,B0_ref117_k4,4,1562,317,65,0.292662,0.142186,0.109735,0.181228,67
C4_PART_08,F8_B0b,E8,B0,B0_ref169_k1,1,1562,280,190,0.921630,0.131981,0.113881,0.152141,29
C4_PART_08,F8_B0b,E8,B0,B0_ref169_k2,2,1562,290,144,0.720098,0.128022,0.107967,0.150723,43
C4_PART_08,F8_B0b,E8,B0,B0_ref169_k3,3,1562,306,94,0.474101,0.126931,0.102573,0.155332,64
C4_PART_08,F8_B0b,E8,B0,B0_ref169_k4,4,1562,314,56,0.260090,0.137839,0.104121,0.178996,86
C4_PART_08,F8_B0b,E8,B0,B0_ref25_k1,1,1562,325,176,0.915021,0.123139,0.105618,0.142737,32
C4_PART_08,F8_B0b,E8,B0,B0_ref25_k2,2,1562,321,151,0.700263,0.138048,0.116908,0.161907,55
C4_PART_08,F8_B0b,E8,B0,B0_ref25_k3,3,1562,308,88,0.446764,0.126100,0.101136,0.155360,69
C4_PART_08,F8_B0b,E8,B0,B0_ref25_k4,4,1562,317,50,0.236292,0.135465,0.100544,0.178595,98
C4_PART_08,F8_B0b,E8,B0,B0_ref333_k1,1,1562,277,187,0.921630,0.129897,0.111946,0.149909,30
C4_PART_08,F8_B0b,E8,B0,B0_ref333_k2,2,1562,285,150,0.720098,0.133357,0.112869,0.156487,46
C4_PART_08,F8_B0b,E8,B0,B0_ref333_k3,3,1562,310,109,0.474101,0.147187,0.120855,0.177551,62
C4_PART_08,F8_B0b,E8,B0,B0_ref333_k4,4,1562,297,57,0.260091,0.140300,0.106261,0.181776,81
C4_PART_08,F8_B0b,E8,B0,B0_ref525_k1,1,1562,348,208,0.916002,0.145373,0.126287,0.166529,35
C4_PART_08,F8_B0b,E8,B0,B0_ref525_k2,2,1562,304,137,0.702617,0.124829,0.104802,0.147569,52
C4_PART_08,F8_B0b,E8,B0,B0_ref525_k3,3,1562,314,103,0.448469,0.147034,0.120013,0.178322,68
C4_PART_08,F8_B0b,E8,B0,B0_ref525_k4,4,1562,323,65,0.235448,0.176737,0.136401,0.225267,85
C4_PART_08,F8_B0b,E8,B0,B0_ref70_k1,1,1562,338,192,0.916002,0.134190,0.115879,0.154572,41
C4_PART_08,F8_B0b,E8,B0,B0_ref70_k2,2,1562,293,135,0.702617,0.123007,0.103133,0.145594,49
C4_PART_08,F8_B0b,E8,B0,B0_ref70_k3,3,1562,315,91,0.448469,0.129903,0.104590,0.159493,81
C4_PART_08,F8_B0b,E8,B0,B0_ref70_k4,4,1562,336,49,0.235448,0.133232,0.098564,0.176140,97
C4_PART_08,F8_B0b,E8,B0,B0_ref795_k1,1,1562,311,198,0.921630,0.137538,0.119047,0.158088,28
C4_PART_08,F8_B0b,E8,B0,B0_ref795_k2,2,1562,296,141,0.720098,0.125355,0.105518,0.147837,38
C4_PART_08,F8_B0b,E8,B0,B0_ref795_k3,3,1562,295,103,0.474101,0.139084,0.113525,0.168681,63
C4_PART_08,F8_B0b,E8,B0,B0_ref795_k4,4,1562,317,69,0.260090,0.169838,0.132143,0.214942,93
C4_PART_08,F8_B0b,E8,B0,B0_ref86_k1,1,1562,318,214,0.921630,0.148653,0.129402,0.169960,31
C4_PART_08,F8_B0b,E8,B0,B0_ref86_k2,2,1562,310,161,0.720098,0.143136,0.121880,0.167033,51
C4_PART_08,F8_B0b,E8,B0,B0_ref86_k3,3,1562,307,106,0.474101,0.143136,0.117187,0.173119,66
C4_PART_08,F8_B0b,E8,B0,B0_ref86_k4,4,1562,323,52,0.260090,0.127993,0.095590,0.167847,101
C4_F8_B1a,F8_B1a,E8,B1,B1_ref27_k1,1,4167,821,495,0.912199,0.130223,0.119002,0.142217,48
C4_F8_B1a,F8_B1a,E8,B1,B1_ref27_k2,2,4167,827,390,0.691321,0.135381,0.122276,0.149507,70
C4_F8_B1a,F8_B1a,E8,B1,B1_ref27_k3,3,4167,855,244,0.433194,0.135169,0.118739,0.153237,93
C4_F8_B1a,F8_B1a,E8,B1,B1_ref27_k4,4,4167,814,136,0.222562,0.146640,0.123031,0.173460,123
C4_F8_B1a,F8_B1a,E8,B1,B1_ref29_k1,1,4167,763,538,0.928308,0.139080,0.127574,0.151344,41
C4_F8_B1a,F8_B1a,E8,B1,B1_ref29_k2,2,4167,755,437,0.741693,0.141394,0.128446,0.155293,48
C4_F8_B1a,F8_B1a,E8,B1,B1_ref29_k3,3,4167,749,287,0.508105,0.135550,0.120319,0.152174,70
C4_F8_B1a,F8_B1a,E8,B1,B1_ref29_k4,4,4167,761,172,0.296637,0.139145,0.119127,0.161565,97
C4_F8_B1a,F8_B1a,E8,B1,B1_ref57_k1,1,4167,839,511,0.912199,0.134432,0.123028,0.146610,45
C4_F8_B1a,F8_B1a,E8,B1,B1_ref57_k2,2,4167,826,415,0.691321,0.144059,0.130531,0.158609,63
C4_F8_B1a,F8_B1a,E8,B1,B1_ref57_k3,3,4167,820,247,0.433194,0.136831,0.120297,0.155002,72
C4_F8_B1a,F8_B1a,E8,B1,B1_ref57_k4,4,4167,828,136,0.222562,0.146640,0.123031,0.173460,94
C4_PART_07,F8_B1a,E8,B1,B1_ref27_k1,1,4166,872,525,0.912199,0.138149,0.126583,0.150488,42
C4_PART_07,F8_B1a,E8,B1,B1_ref27_k2,2,4166,827,372,0.691321,0.129163,0.116370,0.142980,68
C4_PART_07,F8_B1a,E8,B1,B1_ref27_k3,3,4166,827,246,0.433194,0.136310,0.119807,0.154451,91
C4_PART_07,F8_B1a,E8,B1,B1_ref27_k4,4,4166,792,139,0.222562,0.149911,0.126025,0.177006,120
C4_PART_07,F8_B1a,E8,B1,B1_ref29_k1,1,4166,733,530,0.928308,0.137044,0.125624,0.149224,37
C4_PART_07,F8_B1a,E8,B1,B1_ref29_k2,2,4166,713,399,0.741693,0.129129,0.116768,0.142443,51
C4_PART_07,F8_B1a,E8,B1,B1_ref29_k3,3,4166,732,290,0.508105,0.137000,0.121684,0.153710,81
C4_PART_07,F8_B1a,E8,B1,B1_ref29_k4,4,4166,744,173,0.296637,0.139988,0.119904,0.162474,106
C4_PART_07,F8_B1a,E8,B1,B1_ref57_k1,1,4166,847,516,0.912199,0.135780,0.124316,0.148018,47
C4_PART_07,F8_B1a,E8,B1,B1_ref57_k2,2,4166,814,370,0.691321,0.128469,0.115711,0.142250,50
C4_PART_07,F8_B1a,E8,B1,B1_ref57_k3,3,4166,813,263,0.433194,0.145730,0.128648,0.164449,81
C4_PART_07,F8_B1a,E8,B1,B1_ref57_k4,4,4166,828,131,0.222562,0.141283,0.118125,0.167652,100
C4_F8_B1b,F8_B1b,E8,B1,B1_ref27_k1,1,4167,847,534,0.912199,0.140483,0.128819,0.152920,47
C4_F8_B1b,F8_B1b,E8,B1,B1_ref27_k2,2,4167,841,420,0.691321,0.145795,0.132183,0.160428,67
C4_F8_B1b,F8_B1b,E8,B1,B1_ref27_k3,3,4167,780,260,0.433194,0.144033,0.127056,0.162647,90
C4_F8_B1b,F8_B1b,E8,B1,B1_ref27_k4,4,4167,797,117,0.222562,0.126153,0.104331,0.151192,122
C4_F8_B1b,F8_B1b,E8,B1,B1_ref29_k1,1,4167,752,534,0.928308,0.138046,0.126584,0.150266,39
C4_F8_B1b,F8_B1b,E8,B1,B1_ref29_k2,2,4167,740,407,0.741693,0.131687,0.119202,0.145123,50
C4_F8_B1b,F8_B1b,E8,B1,B1_ref29_k3,3,4167,766,297,0.508105,0.140273,0.124771,0.157168,75
C4_F8_B1b,F8_B1b,E8,B1,B1_ref29_k4,4,4167,752,181,0.296637,0.146426,0.125870,0.169382,102
C4_F8_B1b,F8_B1b,E8,B1,B1_ref57_k1,1,4167,778,491,0.912199,0.129171,0.117997,0.141118,43
C4_F8_B1b,F8_B1b,E8,B1,B1_ref57_k2,2,4167,816,389,0.691321,0.135034,0.121946,0.149143,64
C4_F8_B1b,F8_B1b,E8,B1,B1_ref57_k3,3,4167,854,253,0.433194,0.140155,0.123415,0.158532,81
C4_F8_B1b,F8_B1b,E8,B1,B1_ref57_k4,4,4167,785,131,0.222562,0.141249,0.118097,0.167612,97
C4_PART_09,F8_B1b,E8,B1,B1_ref27_k1,1,4166,860,508,0.912199,0.133675,0.122302,0.145822,46
C4_PART_09,F8_B1b,E8,B1,B1_ref27_k2,2,4166,790,390,0.691321,0.135413,0.122306,0.149543,67
C4_PART_09,F8_B1b,E8,B1,B1_ref27_k3,3,4166,837,239,0.433194,0.132431,0.116172,0.150328,95
C4_PART_09,F8_B1b,E8,B1,B1_ref27_k4,4,4166,796,147,0.222562,0.158539,0.133946,0.186340,119
C4_PART_09,F8_B1b,E8,B1,B1_ref29_k1,1,4166,756,529,0.928308,0.136786,0.125376,0.148955,38
C4_PART_09,F8_B1b,E8,B1,B1_ref29_k2,2,4166,739,434,0.741693,0.140457,0.127551,0.154314,52
C4_PART_09,F8_B1b,E8,B1,B1_ref29_k3,3,4166,780,284,0.508105,0.134165,0.119013,0.150711,77
C4_PART_09,F8_B1b,E8,B1,B1_ref29_k4,4,4166,735,178,0.296637,0.144034,0.123651,0.166818,99
C4_PART_09,F8_B1b,E8,B1,B1_ref57_k1,1,4166,834,515,0.912199,0.135517,0.124064,0.147743,49
C4_PART_09,F8_B1b,E8,B1,B1_ref57_k2,2,4166,803,375,0.691321,0.130205,0.117359,0.144074,63
C4_PART_09,F8_B1b,E8,B1,B1_ref57_k3,3,4166,781,244,0.433194,0.135202,0.118768,0.153273,70
C4_PART_09,F8_B1b,E8,B1,B1_ref57_k4,4,4166,840,120,0.222562,0.129419,0.107300,0.154754,105
```

#### (ai) Class-2 per-bit marginals $P(1)$ on IBM-T0 `B0_ref117_k1` (20 clbits), every arm, and the device on the flown circuit

**Source:** `validation/C2_KCHK.json -> data.arms.<arm>.structure.{marginals_by_clbit, se_marginals_by_clbit, physical_by_clbit}`; `validation/C2_CAL.json -> data.arms.<arm>.structure` and `data.K1_device_structure`. The CPU arms of `C2_KCHK` have no shots and no rows.

**Columns and units:** `source`; `job`; `arm`; `circuit`; `clbit` 0-19; `physical_qubit` on `ibm_kingston`; `p1` fraction of shots with that bit 1; `se` its standard error (blank where the file stores none); `shots`.

```csv
source,job,arm,circuit,clbit,physical_qubit,p1,se,shots
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,0,92,0.105469,0.0191973,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,1,69,0.0742188,0.0163829,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,2,54,0.0820312,0.0171508,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,3,52,0.121094,0.0203898,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,4,53,0.21875,0.0258374,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,5,68,0.0273438,0.0101927,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,6,73,0.140625,0.0217271,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,7,94,0.148438,0.0222208,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,8,50,0.132812,0.0212107,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,9,72,0.21875,0.0258374,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,10,71,0.191406,0.024588,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,11,79,0.15625,0.0226933,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,12,51,0.191406,0.024588,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,13,74,0.222656,0.0260018,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,14,70,0.148438,0.0222208,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,15,93,0.136719,0.0214719,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,16,75,0.183594,0.024197,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,17,58,0.167969,0.0233649,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,18,95,0.167969,0.0233649,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv,IBM-T0,19,59,0.160156,0.0229219,256
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,0,92,0.261719,0.0194264,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,1,69,0.136719,0.0151829,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,2,54,0.146484,0.0156267,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,3,52,0.212891,0.0180909,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,4,53,0.505859,0.0220956,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,5,68,0.0878906,0.012513,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,6,73,0.480469,0.0220802,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,7,94,0.380859,0.0214606,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,8,50,0.414062,0.0217683,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,9,72,0.486328,0.0220888,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,10,71,0.427734,0.0218651,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,11,79,0.398438,0.0216364,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,12,51,0.484375,0.0220863,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,13,74,0.460938,0.0220295,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,14,70,0.400391,0.0216542,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,15,93,0.378906,0.0214392,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,16,75,0.455078,0.0220077,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,17,58,0.421875,0.0218257,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,18,95,0.4375,0.0219238,512
validation/C2_KCHK.json,59780907,rm_gpu_cusv,IBM-T0,19,59,0.455078,0.0220077,512
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,0,92,0.136719,0.0214719,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,1,69,0.0664062,0.0155619,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,2,54,0.0859375,0.017517,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,3,52,0.117188,0.0201027,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,4,53,0.242188,0.0267754,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,5,68,0.0351562,0.0115109,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,6,73,0.214844,0.0256696,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,7,94,0.179688,0.0239954,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,8,50,0.183594,0.024197,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,9,72,0.253906,0.0272028,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,10,71,0.21875,0.0258374,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,11,79,0.222656,0.0260018,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,12,51,0.214844,0.0256696,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,13,74,0.210938,0.0254984,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,14,70,0.238281,0.026627,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,15,93,0.160156,0.0229219,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,16,75,0.191406,0.024588,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,17,58,0.203125,0.0251453,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,18,95,0.191406,0.024588,256
validation/C2_KCHK.json,59780907,kraus_gpu_native,IBM-T0,19,59,0.199219,0.0249633,256
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,0,92,0.03125,0.0153789,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,1,69,0.0234375,0.0133721,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,2,54,0.0390625,0.0171247,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,3,52,0.0625,0.0213954,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,4,53,0.0546875,0.0200968,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,5,68,0.0234375,0.0133721,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,6,73,0.0546875,0.0200968,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,7,94,0.0625,0.0213954,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,8,50,0.0546875,0.0200968,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,9,72,0.0859375,0.0247728,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,10,71,0.0390625,0.0171247,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,11,79,0.0546875,0.0200968,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,12,51,0.0625,0.0213954,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,13,74,0.0703125,0.0225985,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,14,70,0.0859375,0.0247728,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,15,93,0.0390625,0.0171247,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,16,75,0.078125,0.0237206,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,17,58,0.101562,0.0266997,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,18,95,0.0546875,0.0200968,128
validation/C2_KCHK.json,59780907,kraus_gpu_cusv_nofusion,IBM-T0,19,59,0.0625,0.0213954,128
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,0,92,0.507812,0.0220944,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,1,69,0.527344,0.022064,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,2,54,0.503906,0.0220964,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,3,52,0.464844,0.0220424,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,4,53,0.511719,0.022091,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,5,68,0.535156,0.0220424,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,6,73,0.486328,0.0220888,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,7,94,0.453125,0.0219998,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,8,50,0.492188,0.0220944,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,9,72,0.515625,0.0220863,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,10,71,0.523438,0.0220728,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,11,79,0.484375,0.0220863,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,12,51,0.517578,0.0220834,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,13,74,0.451172,0.0219915,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,14,70,0.511719,0.022091,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,15,93,0.474609,0.0220686,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,16,75,0.5,0.0220971,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,17,58,0.480469,0.0220802,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,18,95,0.453125,0.0219998,512
validation/C2_CAL.json,59736871,pta_gpu_cusv,IBM-T0,19,59,0.5625,0.0219238,512
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,0,92,0.238281,0.0133135,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,1,69,0.144531,0.0109884,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,2,54,0.120117,0.0101593,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,3,52,0.245117,0.0134424,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,4,53,0.518555,0.0156142,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,5,68,0.0908203,0.00897979,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,6,73,0.429688,0.0154697,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,7,94,0.392578,0.0152601,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,8,50,0.410156,0.0153707,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,9,72,0.504883,0.0156243,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,10,71,0.4375,0.0155024,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,11,79,0.399414,0.0153056,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,12,51,0.498047,0.0156249,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,13,74,0.459961,0.0155748,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,14,70,0.40918,0.0153651,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,15,93,0.398438,0.0152993,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,16,75,0.439453,0.01551,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,17,58,0.393555,0.0152668,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,18,95,0.451172,0.0155503,1024
validation/C2_CAL.json,59736871,rm_gpu_cusv,IBM-T0,19,59,0.438477,0.0155063,1024
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,0,92,0.0890625,0.011259,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,1,69,0.0421875,0.00794588,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,2,54,0.0578125,0.00922549,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,3,52,0.0859375,0.0110787,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,4,53,0.142187,0.013805,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,5,68,0.0328125,0.00704182,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,6,73,0.151562,0.0141748,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,7,94,0.1,0.0118585,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,8,50,0.128125,0.0132116,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,9,72,0.184375,0.0153287,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,10,71,0.1375,0.0136126,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,11,79,0.134375,0.0134814,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,12,51,0.171875,0.014913,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,13,74,0.140625,0.0137415,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,14,70,0.121875,0.0129314,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,15,93,0.117188,0.0127141,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,16,75,0.176563,0.0150721,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,17,58,0.13125,0.0133477,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,18,95,0.114062,0.0125656,640
validation/C2_CAL.json,59736871,kraus_gpu_cusv,IBM-T0,19,59,0.139063,0.0136773,640
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),0,92,0.50707,0.00158098,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),1,69,0.49856,0.00158113,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),2,54,0.47731,0.00157951,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),3,52,0.48498,0.00158043,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),4,53,0.49821,0.00158113,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),5,68,0.49634,0.0015811,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),6,73,0.44523,0.00157162,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),7,94,0.49545,0.00158107,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),8,50,0.49939,0.00158114,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),9,72,0.4922,0.00158095,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),10,71,0.45983,0.00157603,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),11,79,0.47248,0.00157874,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),12,51,0.49226,0.00158095,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),13,74,0.48605,0.00158052,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),14,70,0.47336,0.00157889,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),15,93,0.50373,0.00158109,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),16,75,0.50188,0.00158113,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),17,58,0.4789,0.00157973,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),18,95,0.50544,0.00158105,100000
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device_ibm_kingston,IBM-T3 (flown),19,59,0.50232,0.00158112,100000
```

#### (aj) Class-2 mean Hamming weight of the 20 measured bits, every arm of every run (the plot of Section 8)

**Source:** as named in the `source` column. A uniformly random string has mean weight 10 (unital limit). $z$ between any two rows: $(\bar w_1-\bar w_2)/\sqrt{{\rm se}_1^2+{\rm se}_2^2}$ (the project's formula).

**Columns and units:** `source`; `job`; `engine`; `representation` pta / rm / kraus / hardware; `circuit` IBM-T0 (simulated) or IBM-T3 (flown); `shots`; `mean_w` bits; `se` bits.

```csv
source,job,engine,representation,circuit,shots,mean_w,se
validation/C2_CAL.json (run 3),59736871,GPU cuStateVec,pta,IBM-T0,512,9.957031,0.102132
validation/C2_CAL.json (run 3),59736871,GPU cuStateVec,rm,IBM-T0,1024,7.419922,0.076618
validation/C2_CAL.json (run 3),59736871,GPU cuStateVec,kraus,IBM-T0,640,2.398438,0.135850
data/campaign33/c33c_diag/summary.json,laptop,"CPU (qiskit 1.4.3, aer 0.15.1, 12 threads)",kraus,IBM-T0,19,7.473684,0.558656
data/campaign33/c33c_diag/summary.json,laptop,"CPU (qiskit 1.4.3, aer 0.15.1, 12 threads)",rm,IBM-T0,24,6.916667,0.570776
validation/C2_KCHK.json,59780907,GPU cuStateVec,kraus,IBM-T0,256,2.996094,0.235127
validation/C2_KCHK.json,59780907,GPU native kernels,kraus,IBM-T0,256,3.566406,0.246572
validation/C2_KCHK.json,59780907,"GPU cuStateVec, fusion off",kraus,IBM-T0,128,1.140625,0.218693
validation/C2_KCHK.json,59780907,GPU cuStateVec,rm,IBM-T0,512,7.433594,0.099644
validation/C2_KCHK.json,59780907,CPU separate process (1 thread),kraus,IBM-T0,0,,
validation/C2_KCHK.json,59780907,CPU separate process (1 thread),rm,IBM-T0,0,,
validation/C2_CAL.json K1_device_structure,db2avbe8v0ts73c2i8b0,device ibm_kingston,hardware,IBM-T3 (flown),100000,9.770990,0.007148
```

#### (ak) `QN_2x2` f-cells: 28 native 2x2 circuits x 11 Quantinuum scenarios (308 cells, 2 000 shots each)

**Source:** `validation/QN_2x2.json -> data.fcells.per_scenario.<scenario>.cells.<circuit>`; scenario parameters as in Section 9.4 (E7_0.10_lat: $p_2=9.006\times10^{-3}$).

**Columns and units:** `scenario`; `circuit`; `sector`; `k`; `shots`, `reference_hits` counts; `p_ref` ideal reference probability; `f_hit` with 95 % interval; `f0` analytic fault-free fraction (Aer convention); `accepted_fraction`; `seed`.

```csv
scenario,circuit,sector,k,shots,reference_hits,p_ref,f_hit,f_hit_lo,f_hit_hi,f0,accepted_fraction,seed
E1,B0_ref06_k1,B0,1,2000,1459,0.883276,0.825626,0.783786,0.869119,0.807312,0.856,35200000
E1,B0_ref06_k2,B0,2,2000,1030,0.606424,0.848838,0.79776,0.902327,0.807278,0.853,35200001
E1,B0_ref06_k3,B0,3,2000,518,0.319898,0.80887,0.74064,0.881691,0.807362,0.8605,35200002
E1,B0_ref06_k4,B0,4,2000,233,0.126968,0.915631,0.801588,1.04132,0.807498,0.863,35200003
E1,B0_ref17_k1,B0,1,2000,1499,0.88536,0.846273,0.803955,0.890239,0.806799,0.8535,35200004
E1,B0_ref17_k2,B0,2,2000,991,0.608525,0.813862,0.763949,0.866179,0.806765,0.8555,35200005
E1,B0_ref17_k3,B0,3,2000,493,0.313899,0.784507,0.716709,0.856985,0.806951,0.86,35200006
E1,B0_ref17_k4,B0,4,2000,198,0.112244,0.879828,0.761247,1.01161,0.807036,0.854,35200007
E1,B0_ref21_k1,B0,1,2000,1479,0.88536,0.834978,0.792947,0.878657,0.80685,0.8635,35200008
E1,B0_ref21_k2,B0,2,2000,1049,0.608525,0.861518,0.810142,0.915297,0.806782,0.8625,35200009
E1,B0_ref21_k3,B0,3,2000,532,0.313901,0.846623,0.776135,0.921788,0.806951,0.863,35200010
E1,B0_ref21_k4,B0,4,2000,168,0.112272,0.746006,0.637145,0.868088,0.807002,0.8575,35200011
E1,B0_ref30_k1,B0,1,2000,1483,0.88536,0.837237,0.795149,0.880974,0.806866,0.8625,35200012
E1,B0_ref30_k2,B0,2,2000,1025,0.608525,0.841799,0.791023,0.894978,0.806799,0.849,35200013
E1,B0_ref30_k3,B0,3,2000,523,0.313901,0.832287,0.762411,0.906841,0.8069,0.8525,35200014
E1,B0_ref30_k4,B0,4,2000,204,0.112272,0.90633,0.785931,1.03992,0.807002,0.852,35200015
E1,B0_ref43_k1,B0,1,2000,1480,0.88536,0.835543,0.793498,0.879236,0.80685,0.859,35200016
E1,B0_ref43_k2,B0,2,2000,1029,0.608525,0.845085,0.794209,0.898365,0.806833,0.865,35200017
E1,B0_ref43_k3,B0,3,2000,527,0.313899,0.838664,0.768515,0.913491,0.806917,0.8615,35200018
E1,B0_ref43_k4,B0,4,2000,187,0.112244,0.830828,0.71571,0.959155,0.807053,0.855,35200019
E1,B1_ref07_k1,B1,1,2000,1500,0.88906,0.843313,0.801157,0.88711,0.80707,0.8575,35200020
E1,B1_ref07_k2,B1,2,2000,1024,0.620792,0.824359,0.774611,0.876463,0.807053,0.848,35200021
E1,B1_ref07_k3,B1,3,2000,562,0.333466,0.841932,0.773694,0.91457,0.806968,0.859,35200022
E1,B1_ref07_k4,B1,4,2000,205,0.132343,0.772655,0.670256,0.886244,0.807087,0.8455,35200023
E1,B1_ref14_k1,B1,1,2000,1497,0.88906,0.841626,0.799513,0.88538,0.807002,0.867,35200024
E1,B1_ref14_k2,B1,2,2000,1013,0.620792,0.8155,0.766024,0.867332,0.807036,0.859,35200025
E1,B1_ref14_k3,B1,3,2000,583,0.333466,0.873419,0.803892,0.947347,0.806951,0.858,35200026
E1,B1_ref14_k4,B1,4,2000,260,0.132343,0.980448,0.864666,1.10739,0.807104,0.865,35200027
E2,B0_ref06_k1,B0,1,2000,1516,0.883276,0.857892,0.815232,0.902205,0.817199,0.8745,35201000
E2,B0_ref06_k2,B0,2,2000,1046,0.606424,0.86203,0.810551,0.915921,0.817162,0.875,35201001
E2,B0_ref06_k3,B0,3,2000,504,0.319898,0.786988,0.719707,0.858861,0.817254,0.859,35201002
E2,B0_ref06_k4,B0,4,2000,235,0.126968,0.923507,0.80896,1.0497,0.817401,0.8645,35201003
E2,B0_ref17_k1,B0,1,2000,1499,0.88536,0.846273,0.803955,0.890239,0.817107,0.8655,35201004
E2,B0_ref17_k2,B0,2,2000,1029,0.608525,0.845085,0.794209,0.898365,0.81707,0.8685,35201005
E2,B0_ref17_k3,B0,3,2000,525,0.313899,0.835478,0.765466,0.910169,0.817272,0.8705,35201006
E2,B0_ref17_k4,B0,4,2000,201,0.112244,0.893192,0.773684,1.0259,0.817364,0.862,35201007
E2,B0_ref21_k1,B0,1,2000,1484,0.88536,0.837801,0.795699,0.881553,0.817162,0.8685,35201008
E2,B0_ref21_k2,B0,2,2000,1040,0.608525,0.854123,0.802972,0.907678,0.817088,0.8645,35201009
E2,B0_ref21_k3,B0,3,2000,546,0.313901,0.868923,0.797494,0.945029,0.817272,0.868,35201010
E2,B0_ref21_k4,B0,4,2000,176,0.112272,0.781633,0.670109,0.906372,0.817327,0.866,35201011
E2,B0_ref30_k1,B0,1,2000,1469,0.88536,0.82933,0.787444,0.872866,0.81718,0.8545,35201012
E2,B0_ref30_k2,B0,2,2000,1026,0.608525,0.84262,0.791819,0.895825,0.817107,0.852,35201013
E2,B0_ref30_k3,B0,3,2000,541,0.313901,0.860959,0.789864,0.93673,0.817217,0.863,35201014
E2,B0_ref30_k4,B0,4,2000,185,0.112272,0.821714,0.707265,0.94937,0.817327,0.8625,35201015
E2,B0_ref43_k1,B0,1,2000,1484,0.88536,0.837801,0.795699,0.881553,0.817162,0.8695,35201016
E2,B0_ref43_k2,B0,2,2000,1061,0.608525,0.871378,0.819705,0.925455,0.817143,0.8755,35201017
E2,B0_ref43_k3,B0,3,2000,544,0.313899,0.865743,0.794447,0.941716,0.817235,0.875,35201018
E2,B0_ref43_k4,B0,4,2000,181,0.112244,0.804101,0.690915,0.930501,0.817382,0.8645,35201019
E2,B1_ref07_k1,B1,1,2000,1507,0.88906,0.84725,0.804995,0.891146,0.817401,0.8605,35201020
E2,B1_ref07_k2,B1,2,2000,1041,0.620792,0.838052,0.787886,0.890573,0.817382,0.8625,35201021
E2,B1_ref07_k3,B1,3,2000,548,0.333466,0.82094,0.753576,0.892706,0.817291,0.8765,35201022
E2,B1_ref07_k4,B1,4,2000,214,0.132343,0.806657,0.701956,0.922545,0.817419,0.853,35201023
E2,B1_ref14_k1,B1,1,2000,1488,0.88906,0.836564,0.79458,0.880191,0.817327,0.8595,35201024
E2,B1_ref14_k2,B1,2,2000,1021,0.620792,0.821943,0.772269,0.873973,0.817364,0.86,35201025
E2,B1_ref14_k3,B1,3,2000,564,0.333466,0.844931,0.776569,0.917693,0.817272,0.857,35201026
E2,B1_ref14_k4,B1,4,2000,247,0.132343,0.931333,0.818575,1.05526,0.817438,0.874,35201027
E3,B0_ref06_k1,B0,1,2000,1323,0.883276,0.74864,0.708824,0.79011,0.713427,0.801,35202000
E3,B0_ref06_k2,B0,2,2000,962,0.606424,0.792772,0.743435,0.84452,0.713042,0.8,35202001
E3,B0_ref06_k3,B0,3,2000,485,0.319898,0.757291,0.691319,0.827856,0.712931,0.7955,35202002
E3,B0_ref06_k4,B0,4,2000,193,0.126968,0.758111,0.654661,0.873233,0.712937,0.8055,35202003
E3,B0_ref17_k1,B0,1,2000,1384,0.88536,0.781327,0.740687,0.823617,0.712589,0.8,35202004
E3,B0_ref17_k2,B0,2,2000,940,0.608525,0.771958,0.723366,0.822954,0.712205,0.793,35202005
E3,B0_ref17_k3,B0,3,2000,479,0.313899,0.762206,0.6954,0.833694,0.712328,0.7945,35202006
E3,B0_ref17_k4,B0,4,2000,165,0.112244,0.732828,0.624956,0.853929,0.712216,0.802,35202007
E3,B0_ref21_k1,B0,1,2000,1366,0.88536,0.771162,0.73079,0.813183,0.712706,0.8065,35202008
E3,B0_ref21_k2,B0,2,2000,942,0.608525,0.773601,0.724957,0.824649,0.712244,0.791,35202009
E3,B0_ref21_k3,B0,3,2000,470,0.313901,0.747866,0.681705,0.818709,0.712328,0.802,35202010
E3,B0_ref21_k4,B0,4,2000,189,0.112272,0.839528,0.723802,0.968458,0.712138,0.797,35202011
E3,B0_ref30_k1,B0,1,2000,1354,0.88536,0.764385,0.724193,0.806226,0.712745,0.793,35202012
E3,B0_ref30_k2,B0,2,2000,917,0.608525,0.753059,0.705076,0.803448,0.712283,0.7895,35202013
E3,B0_ref30_k3,B0,3,2000,493,0.313901,0.784502,0.716704,0.856979,0.712211,0.794,35202014
E3,B0_ref30_k4,B0,4,2000,172,0.112272,0.763819,0.653619,0.887238,0.712138,0.7805,35202015
E3,B0_ref43_k1,B0,1,2000,1354,0.88536,0.764385,0.724193,0.806226,0.712706,0.799,35202016
E3,B0_ref43_k2,B0,2,2000,899,0.608525,0.73827,0.690767,0.788177,0.712361,0.7925,35202017
E3,B0_ref43_k3,B0,3,2000,477,0.313899,0.759021,0.692357,0.830366,0.71225,0.7975,35202018
E3,B0_ref43_k4,B0,4,2000,153,0.112244,0.679373,0.575658,0.796329,0.712255,0.793,35202019
E3,B1_ref07_k1,B1,1,2000,1350,0.88906,0.758954,0.71899,0.800561,0.713105,0.7955,35202020
E3,B1_ref07_k2,B1,2,2000,890,0.620792,0.716433,0.670106,0.765117,0.712651,0.7715,35202021
E3,B1_ref07_k3,B1,3,2000,524,0.333466,0.784954,0.719114,0.855198,0.712041,0.7945,35202022
E3,B1_ref07_k4,B1,4,2000,193,0.132343,0.727318,0.628071,0.837764,0.711899,0.7835,35202023
E3,B1_ref14_k1,B1,1,2000,1383,0.88906,0.777513,0.737056,0.819612,0.712949,0.792,35202024
E3,B1_ref14_k2,B1,2,2000,983,0.620792,0.791337,0.742611,0.84242,0.712612,0.7865,35202025
E3,B1_ref14_k3,B1,3,2000,543,0.333466,0.813443,0.746394,0.884895,0.712002,0.7905,35202026
E3,B1_ref14_k4,B1,4,2000,218,0.132343,0.82177,0.71606,0.938663,0.711938,0.794,35202027
E4,B0_ref06_k1,B0,1,2000,1486,0.883276,0.84091,0.79868,0.884793,0.817986,0.8785,35203000
E4,B0_ref06_k2,B0,2,2000,1036,0.606424,0.853785,0.802556,0.907425,0.817737,0.884,35203001
E4,B0_ref06_k3,B0,3,2000,533,0.319898,0.832315,0.763082,0.906137,0.817596,0.8745,35203002
E4,B0_ref06_k4,B0,4,2000,230,0.126968,0.903817,0.790536,1.02875,0.817501,0.8875,35203003
E4,B0_ref17_k1,B0,1,2000,1511,0.88536,0.85305,0.810561,0.897187,0.817909,0.874,35203004
E4,B0_ref17_k2,B0,2,2000,1016,0.608525,0.834404,0.783855,0.887356,0.817661,0.8705,35203005
E4,B0_ref17_k3,B0,3,2000,533,0.313899,0.848221,0.777666,0.923455,0.817611,0.8645,35203006
E4,B0_ref17_k4,B0,4,2000,186,0.112244,0.826374,0.711575,0.954382,0.81747,0.871,35203007
E4,B0_ref21_k1,B0,1,2000,1520,0.88536,0.858132,0.815516,0.902397,0.817955,0.872,35203008
E4,B0_ref21_k2,B0,2,2000,1029,0.608525,0.845085,0.794209,0.898365,0.817676,0.881,35203009
E4,B0_ref21_k3,B0,3,2000,541,0.313901,0.860959,0.789864,0.93673,0.817611,0.867,35203010
E4,B0_ref21_k4,B0,4,2000,213,0.112272,0.946411,0.82329,1.08272,0.817439,0.8865,35203011
E4,B0_ref30_k1,B0,1,2000,1518,0.88536,0.857003,0.814415,0.90124,0.81797,0.8765,35203012
E4,B0_ref30_k2,B0,2,2000,992,0.608525,0.814684,0.764745,0.867027,0.817691,0.8675,35203013
E4,B0_ref30_k3,B0,3,2000,535,0.313901,0.851402,0.780711,0.926769,0.817565,0.872,35203014
E4,B0_ref30_k4,B0,4,2000,192,0.112272,0.852888,0.736213,0.982765,0.817439,0.8835,35203015
E4,B0_ref43_k1,B0,1,2000,1519,0.88536,0.857567,0.814965,0.901818,0.817955,0.872,35203016
E4,B0_ref43_k2,B0,2,2000,1001,0.608525,0.822079,0.77191,0.874651,0.817722,0.8635,35203017
E4,B0_ref43_k3,B0,3,2000,536,0.313899,0.853,0.782242,0.928436,0.817581,0.8695,35203018
E4,B0_ref43_k4,B0,4,2000,188,0.112244,0.835283,0.719846,0.963928,0.817485,0.8835,35203019
E4,B1_ref07_k1,B1,1,2000,1496,0.88906,0.841063,0.798965,0.884804,0.818077,0.8685,35203020
E4,B1_ref07_k2,B1,2,2000,1072,0.620792,0.86302,0.812101,0.916293,0.817767,0.874,35203021
E4,B1_ref07_k3,B1,3,2000,620,0.333466,0.928897,0.857153,1.00504,0.817395,0.8765,35203022
E4,B1_ref07_k4,B1,4,2000,252,0.132343,0.950223,0.836293,1.07532,0.817207,0.8755,35203023
E4,B1_ref14_k1,B1,1,2000,1528,0.88906,0.85906,0.816508,0.903254,0.818016,0.8635,35203024
E4,B1_ref14_k2,B1,2,2000,1054,0.620792,0.848522,0.798039,0.90136,0.817751,0.8605,35203025
E4,B1_ref14_k3,B1,3,2000,573,0.333466,0.858425,0.789509,0.931742,0.817379,0.8705,35203026
E4,B1_ref14_k4,B1,4,2000,260,0.132343,0.980448,0.864666,1.10739,0.817222,0.8775,35203027
E5a,B0_ref06_k1,B0,1,2000,1443,0.883276,0.816569,0.774962,0.859829,0.80459,0.868,35204000
E5a,B0_ref06_k2,B0,2,2000,1021,0.606424,0.841417,0.790566,0.89468,0.804556,0.8595,35204001
E5a,B0_ref06_k3,B0,3,2000,521,0.319898,0.813559,0.745127,0.886581,0.804641,0.8525,35204002
E5a,B0_ref06_k4,B0,4,2000,216,0.126968,0.848685,0.739024,0.970004,0.804776,0.8645,35204003
E5a,B0_ref17_k1,B0,1,2000,1485,0.88536,0.838366,0.796249,0.882132,0.804079,0.8595,35204004
E5a,B0_ref17_k2,B0,2,2000,1003,0.608525,0.823722,0.773503,0.876345,0.804045,0.8455,35204005
E5a,B0_ref17_k3,B0,3,2000,519,0.313899,0.825921,0.756318,0.900202,0.804231,0.8395,35204006
E5a,B0_ref17_k4,B0,4,2000,197,0.112244,0.875374,0.757104,1.00684,0.804315,0.861,35204007
E5a,B0_ref21_k1,B0,1,2000,1473,0.88536,0.831589,0.789645,0.875182,0.80413,0.855,35204008
E5a,B0_ref21_k2,B0,2,2000,999,0.608525,0.820435,0.770318,0.872957,0.804062,0.8515,35204009
E5a,B0_ref21_k3,B0,3,2000,529,0.313901,0.841844,0.77156,0.916806,0.804231,0.844,35204010
E5a,B0_ref21_k4,B0,4,2000,162,0.112272,0.719285,0.612464,0.839334,0.804282,0.8515,35204011
E5a,B0_ref30_k1,B0,1,2000,1461,0.88536,0.824812,0.783042,0.868232,0.804146,0.8585,35204012
E5a,B0_ref30_k2,B0,2,2000,995,0.608525,0.817149,0.767133,0.869568,0.804079,0.8475,35204013
E5a,B0_ref30_k3,B0,3,2000,491,0.313901,0.781316,0.713659,0.853653,0.80418,0.85,35204014
E5a,B0_ref30_k4,B0,4,2000,209,0.112272,0.928597,0.806679,1.0637,0.804282,0.8505,35204015
E5a,B0_ref43_k1,B0,1,2000,1489,0.88536,0.840625,0.798451,0.884448,0.80413,0.8605,35204016
E5a,B0_ref43_k2,B0,2,2000,994,0.608525,0.816327,0.766337,0.868721,0.804113,0.8575,35204017
E5a,B0_ref43_k3,B0,3,2000,527,0.313899,0.838664,0.768515,0.913491,0.804197,0.865,35204018
E5a,B0_ref43_k4,B0,4,2000,206,0.112244,0.915465,0.794426,1.0497,0.804332,0.866,35204019
E5a,B1_ref07_k1,B1,1,2000,1506,0.88906,0.846687,0.804446,0.89057,0.804349,0.8575,35204020
E5a,B1_ref07_k2,B1,2,2000,1037,0.620792,0.83483,0.784762,0.887253,0.804332,0.841,35204021
E5a,B1_ref07_k3,B1,3,2000,549,0.333466,0.82244,0.755013,0.894268,0.804248,0.849,35204022
E5a,B1_ref07_k4,B1,4,2000,215,0.132343,0.810435,0.705481,0.926575,0.804366,0.8595,35204023
E5a,B1_ref14_k1,B1,1,2000,1496,0.88906,0.841063,0.798965,0.884804,0.804282,0.8555,35204024
E5a,B1_ref14_k2,B1,2,2000,1031,0.620792,0.829997,0.780077,0.882273,0.804315,0.852,35204025
E5a,B1_ref14_k3,B1,3,2000,562,0.333466,0.841932,0.773694,0.91457,0.804231,0.8395,35204026
E5a,B1_ref14_k4,B1,4,2000,214,0.132343,0.806657,0.701956,0.922545,0.804383,0.858,35204027
E5b,B0_ref06_k1,B0,1,2000,1448,0.883276,0.819399,0.777719,0.862732,0.801336,0.854,35205000
E5b,B0_ref06_k2,B0,2,2000,1010,0.606424,0.832348,0.781776,0.885331,0.801303,0.855,35205001
E5b,B0_ref06_k3,B0,3,2000,555,0.319898,0.866701,0.796023,0.941967,0.801387,0.8685,35205002
E5b,B0_ref06_k4,B0,4,2000,193,0.126968,0.758111,0.654661,0.873233,0.801521,0.8665,35205003
E5b,B0_ref17_k1,B0,1,2000,1499,0.88536,0.846273,0.803955,0.890239,0.800827,0.858,35205004
E5b,B0_ref17_k2,B0,2,2000,972,0.608525,0.798251,0.748826,0.85008,0.800794,0.8315,35205005
E5b,B0_ref17_k3,B0,3,2000,522,0.313899,0.8307,0.760892,0.905186,0.800979,0.8395,35205006
E5b,B0_ref17_k4,B0,4,2000,186,0.112244,0.826374,0.711575,0.954382,0.801063,0.8505,35205007
E5b,B0_ref21_k1,B0,1,2000,1476,0.88536,0.833284,0.791296,0.87692,0.800878,0.8415,35205008
E5b,B0_ref21_k2,B0,2,2000,1012,0.608525,0.831117,0.780669,0.883968,0.80081,0.8575,35205009
E5b,B0_ref21_k3,B0,3,2000,528,0.313901,0.840252,0.770035,0.915146,0.800979,0.8445,35205010
E5b,B0_ref21_k4,B0,4,2000,170,0.112272,0.754912,0.64538,0.877665,0.801029,0.8575,35205011
E5b,B0_ref30_k1,B0,1,2000,1499,0.88536,0.846273,0.803955,0.890239,0.800894,0.8515,35205012
E5b,B0_ref30_k2,B0,2,2000,1044,0.608525,0.85741,0.806158,0.911065,0.800827,0.8525,35205013
E5b,B0_ref30_k3,B0,3,2000,487,0.313901,0.774944,0.70757,0.846999,0.800928,0.8525,35205014
E5b,B0_ref30_k4,B0,4,2000,214,0.112272,0.950864,0.827445,1.08747,0.801029,0.856,35205015
E5b,B0_ref43_k1,B0,1,2000,1471,0.88536,0.83046,0.788545,0.874024,0.800878,0.8475,35205016
E5b,B0_ref43_k2,B0,2,2000,1043,0.608525,0.856589,0.805362,0.910218,0.800861,0.8525,35205017
E5b,B0_ref43_k3,B0,3,2000,526,0.313899,0.837071,0.76699,0.91183,0.800945,0.85,35205018
E5b,B0_ref43_k4,B0,4,2000,180,0.112244,0.799646,0.686785,0.925722,0.80108,0.8515,35205019
E5b,B1_ref07_k1,B1,1,2000,1492,0.88906,0.838814,0.796772,0.882497,0.801096,0.852,35205020
E5b,B1_ref07_k2,B1,2,2000,1035,0.620792,0.833219,0.7832,0.885593,0.80108,0.831,35205021
E5b,B1_ref07_k3,B1,3,2000,547,0.333466,0.819441,0.75214,0.891144,0.800995,0.8455,35205022
E5b,B1_ref07_k4,B1,4,2000,218,0.132343,0.82177,0.71606,0.938663,0.801113,0.855,35205023
E5b,B1_ref14_k1,B1,1,2000,1507,0.88906,0.84725,0.804995,0.891146,0.801029,0.8505,35205024
E5b,B1_ref14_k2,B1,2,2000,1034,0.620792,0.832414,0.78242,0.884763,0.801063,0.8385,35205025
E5b,B1_ref14_k3,B1,3,2000,536,0.333466,0.802947,0.736341,0.873957,0.800979,0.836,35205026
E5b,B1_ref14_k4,B1,4,2000,223,0.132343,0.84066,0.733703,0.958797,0.80113,0.865,35205027
E5c,B0_ref06_k1,B0,1,2000,1420,0.883276,0.803549,0.762279,0.846472,0.783674,0.8405,35206000
E5c,B0_ref06_k2,B0,2,2000,971,0.606424,0.800192,0.750622,0.852175,0.783642,0.842,35206001
E5c,B0_ref06_k3,B0,3,2000,532,0.319898,0.830752,0.761586,0.904508,0.783724,0.8655,35206002
E5c,B0_ref06_k4,B0,4,2000,216,0.126968,0.848685,0.739024,0.970004,0.783855,0.8605,35206003
E5c,B0_ref17_k1,B0,1,2000,1465,0.88536,0.827071,0.785243,0.870549,0.783177,0.8585,35206004
E5c,B0_ref17_k2,B0,2,2000,1000,0.608525,0.821257,0.771114,0.873804,0.783144,0.844,35206005
E5c,B0_ref17_k3,B0,3,2000,539,0.313899,0.857779,0.786818,0.933416,0.783325,0.8415,35206006
E5c,B0_ref17_k4,B0,4,2000,197,0.112244,0.875374,0.757104,1.00684,0.783407,0.845,35206007
E5c,B0_ref21_k1,B0,1,2000,1474,0.88536,0.832154,0.790196,0.875761,0.783226,0.845,35206008
E5c,B0_ref21_k2,B0,2,2000,1006,0.608525,0.826187,0.775891,0.878886,0.78316,0.859,35206009
E5c,B0_ref21_k3,B0,3,2000,518,0.313901,0.824323,0.754789,0.898535,0.783325,0.8495,35206010
E5c,B0_ref21_k4,B0,4,2000,195,0.112272,0.866249,0.748632,0.997065,0.783374,0.8585,35206011
E5c,B0_ref30_k1,B0,1,2000,1511,0.88536,0.85305,0.810561,0.897187,0.783242,0.8555,35206012
E5c,B0_ref30_k2,B0,2,2000,986,0.608525,0.809754,0.759968,0.861943,0.783177,0.8545,35206013
E5c,B0_ref30_k3,B0,3,2000,495,0.313901,0.787687,0.719749,0.860305,0.783275,0.8515,35206014
E5c,B0_ref30_k4,B0,4,2000,209,0.112272,0.928597,0.806679,1.0637,0.783374,0.8595,35206015
E5c,B0_ref43_k1,B0,1,2000,1468,0.88536,0.828766,0.786894,0.872286,0.783226,0.8445,35206016
E5c,B0_ref43_k2,B0,2,2000,1022,0.608525,0.839334,0.788633,0.892437,0.783209,0.847,35206017
E5c,B0_ref43_k3,B0,3,2000,525,0.313899,0.835478,0.765466,0.910169,0.783292,0.847,35206018
E5c,B0_ref43_k4,B0,4,2000,194,0.112244,0.86201,0.744677,0.992546,0.783423,0.8425,35206019
E5c,B1_ref07_k1,B1,1,2000,1485,0.88906,0.834877,0.792936,0.87846,0.78344,0.8515,35206020
E5c,B1_ref07_k2,B1,2,2000,1039,0.620792,0.836441,0.786324,0.888913,0.783423,0.8465,35206021
E5c,B1_ref07_k3,B1,3,2000,548,0.333466,0.82094,0.753576,0.892706,0.783341,0.8435,35206022
E5c,B1_ref07_k4,B1,4,2000,251,0.132343,0.946445,0.832749,1.07131,0.783456,0.843,35206023
E5c,B1_ref14_k1,B1,1,2000,1475,0.88906,0.829253,0.787455,0.872693,0.783374,0.8405,35206024
E5c,B1_ref14_k2,B1,2,2000,1013,0.620792,0.8155,0.766024,0.867332,0.783407,0.841,35206025
E5c,B1_ref14_k3,B1,3,2000,545,0.333466,0.816442,0.749267,0.88802,0.783325,0.8335,35206026
E5c,B1_ref14_k4,B1,4,2000,222,0.132343,0.836882,0.730173,0.954771,0.783473,0.8475,35206027
E6a,B0_ref06_k1,B0,1,2000,1621,0.883276,0.91733,0.873199,0.963114,0.898523,0.932,35207000
E6a,B0_ref06_k2,B0,2,2000,1109,0.606424,0.913974,0.860943,0.969415,0.898504,0.931,35207001
E6a,B0_ref06_k3,B0,3,2000,595,0.319898,0.929221,0.855987,1.00704,0.898551,0.9385,35207002
E6a,B0_ref06_k4,B0,4,2000,253,0.126968,0.994391,0.875394,1.12503,0.898627,0.935,35207003
E6a,B0_ref17_k1,B0,1,2000,1625,0.88536,0.91743,0.873348,0.963161,0.898238,0.93,35207004
E6a,B0_ref17_k2,B0,2,2000,1104,0.608525,0.90671,0.853983,0.961838,0.898219,0.932,35207005
E6a,B0_ref17_k3,B0,3,2000,599,0.313899,0.953351,0.878462,1.03291,0.898323,0.9355,35207006
E6a,B0_ref17_k4,B0,4,2000,195,0.112244,0.866465,0.748818,0.997313,0.89837,0.935,35207007
E6a,B0_ref21_k1,B0,1,2000,1666,0.88536,0.940585,0.895943,0.986874,0.898266,0.9315,35207008
E6a,B0_ref21_k2,B0,2,2000,1127,0.608525,0.925608,0.872327,0.981291,0.898228,0.932,35207009
E6a,B0_ref21_k3,B0,3,2000,585,0.313901,0.931044,0.857055,1.00971,0.898323,0.9305,35207010
E6a,B0_ref21_k4,B0,4,2000,202,0.112272,0.897423,0.777637,1.0304,0.898351,0.9265,35207011
E6a,B0_ref30_k1,B0,1,2000,1618,0.88536,0.913477,0.869491,0.959111,0.898276,0.928,35207012
E6a,B0_ref30_k2,B0,2,2000,1117,0.608525,0.917391,0.864351,0.972834,0.898238,0.9335,35207013
E6a,B0_ref30_k3,B0,3,2000,601,0.313901,0.95653,0.881514,1.03622,0.898294,0.926,35207014
E6a,B0_ref30_k4,B0,4,2000,216,0.112272,0.959771,0.835756,1.09697,0.898351,0.929,35207015
E6a,B0_ref43_k1,B0,1,2000,1637,0.88536,0.924207,0.87996,0.970102,0.898266,0.9335,35207016
E6a,B0_ref43_k2,B0,2,2000,1129,0.608525,0.927251,0.873922,0.982982,0.898257,0.9285,35207017
E6a,B0_ref43_k3,B0,3,2000,577,0.313899,0.918308,0.844835,0.996455,0.898304,0.931,35207018
E6a,B0_ref43_k4,B0,4,2000,231,0.112244,1.02683,0.898401,1.16843,0.898379,0.933,35207019
E6a,B1_ref07_k1,B1,1,2000,1618,0.88906,0.909675,0.865872,0.955119,0.898389,0.9295,35207020
E6a,B1_ref07_k2,B1,2,2000,1154,0.620792,0.929064,0.876205,0.984278,0.898379,0.9335,35207021
E6a,B1_ref07_k3,B1,3,2000,628,0.333466,0.940892,0.868677,1.01751,0.898332,0.9305,35207022
E6a,B1_ref07_k4,B1,4,2000,236,0.132343,0.889774,0.779639,1.01108,0.898398,0.9285,35207023
E6a,B1_ref14_k1,B1,1,2000,1627,0.88906,0.914737,0.870811,0.960304,0.898351,0.9255,35207024
E6a,B1_ref14_k2,B1,2,2000,1182,0.620792,0.951616,0.89811,1.00748,0.89837,0.932,35207025
E6a,B1_ref14_k3,B1,3,2000,603,0.333466,0.903407,0.832673,0.978541,0.898323,0.9295,35207026
E6a,B1_ref14_k4,B1,4,2000,237,0.132343,0.893552,0.783176,1.0151,0.898408,0.9325,35207027
E6b,B0_ref06_k1,B0,1,2000,1248,0.883276,0.706185,0.667529,0.746494,0.651647,0.7645,35208000
E6b,B0_ref06_k2,B0,2,2000,806,0.606424,0.664149,0.619056,0.711656,0.651593,0.7395,35208001
E6b,B0_ref06_k3,B0,3,2000,419,0.319898,0.654133,0.59292,0.719945,0.65173,0.743,35208002
E6b,B0_ref06_k4,B0,4,2000,169,0.126968,0.663599,0.567041,0.771848,0.651949,0.7385,35208003
E6b,B0_ref17_k1,B0,1,2000,1220,0.88536,0.68871,0.650586,0.728484,0.650819,0.7165,35208004
E6b,B0_ref17_k2,B0,2,2000,861,0.608525,0.707047,0.660575,0.755923,0.650764,0.7385,35208005
E6b,B0_ref17_k3,B0,3,2000,462,0.313899,0.735128,0.669545,0.805393,0.651065,0.7395,35208006
E6b,B0_ref17_k4,B0,4,2000,176,0.112244,0.781828,0.670276,0.906598,0.651202,0.727,35208007
E6b,B0_ref21_k1,B0,1,2000,1250,0.88536,0.705652,0.667056,0.745898,0.650901,0.7335,35208008
E6b,B0_ref21_k2,B0,2,2000,842,0.608525,0.691435,0.645488,0.739788,0.650792,0.7335,35208009
E6b,B0_ref21_k3,B0,3,2000,437,0.313901,0.695301,0.63156,0.763727,0.651065,0.7395,35208010
E6b,B0_ref21_k4,B0,4,2000,138,0.112272,0.612402,0.514145,0.723915,0.651147,0.7405,35208011
E6b,B0_ref30_k1,B0,1,2000,1189,0.88536,0.671203,0.633573,0.710483,0.650928,0.7085,35208012
E6b,B0_ref30_k2,B0,2,2000,814,0.608525,0.668429,0.623265,0.715998,0.650819,0.7155,35208013
E6b,B0_ref30_k3,B0,3,2000,455,0.313901,0.723973,0.658901,0.793728,0.650983,0.734,35208014
E6b,B0_ref30_k4,B0,4,2000,157,0.112272,0.697018,0.591926,0.815343,0.651147,0.7295,35208015
E6b,B0_ref43_k1,B0,1,2000,1240,0.88536,0.700004,0.661565,0.740094,0.650901,0.7405,35208016
E6b,B0_ref43_k2,B0,2,2000,877,0.608525,0.720193,0.673285,0.769507,0.650874,0.7495,35208017
E6b,B0_ref43_k3,B0,3,2000,440,0.313899,0.700085,0.636119,0.768734,0.65101,0.731,35208018
E6b,B0_ref43_k4,B0,4,2000,163,0.112244,0.723919,0.616729,0.844339,0.651229,0.723,35208019
E6b,B1_ref07_k1,B1,1,2000,1255,0.88906,0.705527,0.667013,0.745684,0.651257,0.737,35208020
E6b,B1_ref07_k2,B1,2,2000,882,0.620792,0.709989,0.663875,0.758462,0.651229,0.7275,35208021
E6b,B1_ref07_k3,B1,3,2000,475,0.333466,0.711484,0.648866,0.778508,0.651092,0.7205,35208022
E6b,B1_ref07_k4,B1,4,2000,185,0.132343,0.697094,0.600002,0.80539,0.651284,0.721,35208023
E6b,B1_ref14_k1,B1,1,2000,1206,0.88906,0.67797,0.640226,0.717357,0.651147,0.712,35208024
E6b,B1_ref14_k2,B1,2,2000,893,0.620792,0.718849,0.672443,0.767613,0.651202,0.734,35208025
E6b,B1_ref14_k3,B1,3,2000,483,0.333466,0.723479,0.660324,0.79104,0.651065,0.7225,35208026
E6b,B1_ref14_k4,B1,4,2000,196,0.132343,0.738653,0.638608,0.849893,0.651311,0.737,35208027
E6c,B0_ref06_k1,B0,1,2000,880,0.883276,0.497869,0.465496,0.531899,0.424372,0.575,35209000
E6c,B0_ref06_k2,B0,2,2000,579,0.606424,0.476986,0.438888,0.517504,0.4243,0.56,35209001
E6c,B0_ref06_k3,B0,3,2000,309,0.319898,0.482203,0.429849,0.539168,0.424479,0.555,35209002
E6c,B0_ref06_k4,B0,4,2000,118,0.126968,0.462761,0.382708,0.554562,0.424764,0.574,35209003
E6c,B0_ref17_k1,B0,1,2000,913,0.88536,0.515334,0.482427,0.549894,0.423292,0.555,35209004
E6c,B0_ref17_k2,B0,2,2000,627,0.608525,0.514779,0.475238,0.55673,0.423221,0.543,35209005
E6c,B0_ref17_k3,B0,3,2000,319,0.313899,0.507347,0.453111,0.566281,0.423612,0.5455,35209006
E6c,B0_ref17_k4,B0,4,2000,115,0.112244,0.5101,0.42076,0.612733,0.42379,0.538,35209007
E6c,B0_ref21_k1,B0,1,2000,874,0.88536,0.493309,0.461124,0.527147,0.423398,0.5525,35209008
E6c,B0_ref21_k2,B0,2,2000,622,0.608525,0.51067,0.47129,0.55246,0.423256,0.551,35209009
E6c,B0_ref21_k3,B0,3,2000,329,0.313901,0.523273,0.468169,0.583072,0.423612,0.5535,35209010
E6c,B0_ref21_k4,B0,4,2000,123,0.112272,0.5456,0.45308,0.651398,0.423719,0.5655,35209011
E6c,B0_ref30_k1,B0,1,2000,886,0.88536,0.500086,0.467677,0.534148,0.423434,0.5445,35209012
E6c,B0_ref30_k2,B0,2,2000,617,0.608525,0.506562,0.467344,0.548191,0.423292,0.5695,35209013
E6c,B0_ref30_k3,B0,3,2000,329,0.313901,0.523273,0.468169,0.583072,0.423505,0.551,35209014
E6c,B0_ref30_k4,B0,4,2000,122,0.112272,0.541147,0.449021,0.646552,0.423719,0.5545,35209015
E6c,B0_ref43_k1,B0,1,2000,872,0.88536,0.492179,0.460032,0.52598,0.423398,0.5505,35209016
E6c,B0_ref43_k2,B0,2,2000,620,0.608525,0.509027,0.469712,0.550753,0.423363,0.5675,35209017
E6c,B0_ref43_k3,B0,3,2000,292,0.313899,0.46434,0.412516,0.520865,0.423541,0.5525,35209018
E6c,B0_ref43_k4,B0,4,2000,135,0.112244,0.599191,0.502031,0.709614,0.423825,0.552,35209019
E6c,B1_ref07_k1,B1,1,2000,899,0.88906,0.505315,0.472802,0.539475,0.423861,0.5495,35209020
E6c,B1_ref07_k2,B1,2,2000,631,0.620792,0.507828,0.468943,0.549076,0.423825,0.549,35209021
E6c,B1_ref07_k3,B1,3,2000,336,0.333466,0.503067,0.450632,0.559921,0.423647,0.552,35209022
E6c,B1_ref07_k4,B1,4,2000,129,0.132343,0.485523,0.405054,0.577249,0.423897,0.5255,35209023
E6c,B1_ref14_k1,B1,1,2000,880,0.88906,0.49463,0.462467,0.528439,0.423719,0.537,35209024
E6c,B1_ref14_k2,B1,2,2000,632,0.620792,0.508634,0.469717,0.549913,0.42379,0.5505,35209025
E6c,B1_ref14_k3,B1,3,2000,356,0.333466,0.533055,0.47904,0.591487,0.423612,0.5265,35209026
E6c,B1_ref14_k4,B1,4,2000,127,0.132343,0.477967,0.398153,0.569041,0.423932,0.527,35209027
E7_0.10_lat,B0_ref06_k1,B0,1,2000,272,0.883276,0.153696,0.13594,0.173124,0.115956,0.252,35210000
E7_0.10_lat,B0_ref06_k2,B0,2,2000,214,0.606424,0.176042,0.153192,0.201332,0.115951,0.2625,35210001
E7_0.10_lat,B0_ref06_k3,B0,3,2000,121,0.319898,0.18836,0.156166,0.225214,0.115963,0.2365,35210002
E7_0.10_lat,B0_ref06_k4,B0,4,2000,40,0.126968,0.155597,0.110612,0.212575,0.115983,0.2385,35210003
E7_0.10_lat,B0_ref17_k1,B0,1,2000,356,0.88536,0.200772,0.180428,0.222781,0.115882,0.249,35210004
E7_0.10_lat,B0_ref17_k2,B0,2,2000,225,0.608525,0.184472,0.161103,0.210272,0.115878,0.2345,35210005
E7_0.10_lat,B0_ref17_k3,B0,3,2000,118,0.313899,0.187181,0.1548,0.224313,0.115904,0.2325,35210006
E7_0.10_lat,B0_ref17_k4,B0,4,2000,31,0.112244,0.135916,0.0916514,0.193835,0.115917,0.23,35210007
E7_0.10_lat,B0_ref21_k1,B0,1,2000,324,0.88536,0.182701,0.163317,0.203749,0.11589,0.2395,35210008
E7_0.10_lat,B0_ref21_k2,B0,2,2000,219,0.608525,0.179542,0.156497,0.205018,0.11588,0.2295,35210009
E7_0.10_lat,B0_ref21_k3,B0,3,2000,108,0.313901,0.171251,0.140341,0.206919,0.115904,0.2335,35210010
E7_0.10_lat,B0_ref21_k4,B0,4,2000,59,0.112272,0.260579,0.197846,0.336759,0.115912,0.2425,35210011
E7_0.10_lat,B0_ref30_k1,B0,1,2000,314,0.88536,0.177053,0.15798,0.197792,0.115892,0.2295,35210012
E7_0.10_lat,B0_ref30_k2,B0,2,2000,234,0.608525,0.191867,0.168019,0.218145,0.115882,0.247,35210013
E7_0.10_lat,B0_ref30_k3,B0,3,2000,101,0.313901,0.160101,0.130261,0.194704,0.115897,0.224,35210014
E7_0.10_lat,B0_ref30_k4,B0,4,2000,47,0.112272,0.207138,0.15162,0.276166,0.115912,0.2335,35210015
E7_0.10_lat,B0_ref43_k1,B0,1,2000,308,0.88536,0.173665,0.15478,0.194216,0.11589,0.2395,35210016
E7_0.10_lat,B0_ref43_k2,B0,2,2000,214,0.608525,0.175434,0.152663,0.200637,0.115887,0.2255,35210017
E7_0.10_lat,B0_ref43_k3,B0,3,2000,122,0.313899,0.193552,0.160602,0.231253,0.1159,0.2565,35210018
E7_0.10_lat,B0_ref43_k4,B0,4,2000,61,0.112244,0.269553,0.205676,0.346871,0.115919,0.2495,35210019
E7_0.10_lat,B1_ref07_k1,B1,1,2000,311,0.88906,0.174629,0.155729,0.195189,0.115921,0.227,35210020
E7_0.10_lat,B1_ref07_k2,B1,2,2000,220,0.620792,0.1768,0.154157,0.201826,0.115919,0.2345,35210021
E7_0.10_lat,B1_ref07_k3,B1,3,2000,136,0.333466,0.203187,0.170356,0.240481,0.115907,0.234,35210022
E7_0.10_lat,B1_ref07_k4,B1,4,2000,48,0.132343,0.179502,0.131866,0.238594,0.115924,0.2245,35210023
E7_0.10_lat,B1_ref14_k1,B1,1,2000,304,0.88906,0.170692,0.152012,0.191032,0.115912,0.2135,35210024
E7_0.10_lat,B1_ref14_k2,B1,2,2000,222,0.620792,0.178411,0.155662,0.203543,0.115917,0.219,35210025
E7_0.10_lat,B1_ref14_k3,B1,3,2000,112,0.333466,0.167201,0.137543,0.201335,0.115904,0.2175,35210026
E7_0.10_lat,B1_ref14_k4,B1,4,2000,46,0.132343,0.171945,0.125392,0.229967,0.115926,0.2105,35210027
```

#### (al) `QN_2x2` plan-of-record SKQD runs (the `H0_2x2` plan, 133 907 shots per scenario)

**Source:** `validation/QN_2x2.json -> data.plan_of_record.<scenario>.reading.<sector>` and `.wall_s`; dropped runs from `.status`, `.predicted_h`.

**Columns and units:** `scenario`; `sector`; `shots`; `accepted`; `accepted_fraction`; `mu_per_state` = $Na/\dim$ (saturation parameter); `B_all`, `B_sig` states; `recall_S999`; `E_R_minus_E0`; `rH`; `wall_s` per scenario (both sectors); `status`.

```csv
scenario,sector,shots,accepted,accepted_fraction,mu_per_state,B_all,B_sig,recall_S999,E_R_minus_E0,rH,wall_s,status
E1,B0,69505,59699,0.858917,16.969,38,38,1.0,0,6.14e-15,1764.1,run
E1,B1,64402,54977,0.853654,15.723,20,20,1.0,0,1.51e-15,1764.1,run
E3,B0,69505,54606,0.785641,16.969,38,38,1.0,0,6.14e-15,1630.0,run
E3,B1,64402,50080,0.777616,15.723,20,20,1.0,0,1.51e-15,1630.0,run
E4,B0,69505,60268,0.867103,16.969,38,38,1.0,0,6.14e-15,1637.8,run
E4,B1,64402,55497,0.861728,15.723,20,20,1.0,0,1.51e-15,1637.8,run
E5b,B0,69505,59601,0.857507,16.969,38,38,1.0,0,6.14e-15,1856.5,run
E5b,B1,64402,54990,0.853856,15.723,20,20,1.0,0,1.51e-15,1856.5,run
E2,both,133907,,,,,,,,,,dropped by prompts/35a (0.87 h predicted)
E6a,both,133907,,,,,,,,,,dropped by prompts/35a (0.87 h predicted)
E6b,both,133907,,,,,,,,,,dropped by prompts/35a (0.87 h predicted)
E6c,both,133907,,,,,,,,,,dropped by prompts/35a (0.87 h predicted)
E7_0.10_lat,both,133907,,,,,,,,,,dropped by prompts/35a (0.87 h predicted)
E5a,both,133907,,,,,,,,,,dropped by prompts/35a (1.03 h predicted)
E5c,both,133907,,,,,,,,,,dropped by prompts/35a (1.03 h predicted)
```

#### (am) The 79 native 2x4 circuits of the two sources

**Source:** `data/quantinuum/circuits_2x4/<id>.manifest.json -> counts, hqc_per_shot, p_reference, k, twoB, reference`; `B_bound` from `validation/Q0P_2x4.json -> data.Q1.B_per_circuit`.

**Columns and units:** `id`; `source` opt3 / structured; `twoB` ($2B$: 0 or 2); `reference`; `k`; `n_zz`, `n_phasedx`, `n_rz` gate counts; `depth`, `depth_2q` layers; `hqc_per_shot` HQC; `p_reference`; `B_bound` the rigorous pytket-rounding state bound (dimensionless; the bar is $10^{-10}$).

```csv
id,source,twoB,reference,k,n_zz,n_phasedx,n_rz,depth,depth_2q,hqc_per_shot,p_reference,B_bound
B0_ref102_k1.opt3,opt3,0,102,1,69676,90522,139267,205139,68648,157.5124,0.933998,4.956e-09
B0_ref102_k1.structured,structured,0,102,1,71548,210994,143140,347827,70300,185.3508,0.933998,6.538e-12
B0_ref102_k2.opt3,opt3,0,102,2,69676,90645,139272,205158,68648,157.537,0.760663,4.979e-09
B0_ref102_k2.structured,structured,0,102,2,71548,210994,143140,347827,70300,185.3508,0.760663,6.706e-12
B0_ref102_k3.structured,structured,0,102,3,71548,210994,143140,347827,70300,185.3508,0.539465,6.139e-12
B0_ref102_k4.structured,structured,0,102,4,71548,210994,143140,347827,70300,185.3508,0.332415,6.146e-12
B0_ref11026_k1.opt3,opt3,0,11026,1,69676,90520,139268,205138,68648,157.512,0.934553,4.956e-09
B0_ref11026_k1.structured,structured,0,11026,1,71548,210995,143140,347827,70300,185.351,0.934553,6.538e-12
B0_ref11026_k2.opt3,opt3,0,11026,2,69676,90646,139273,205158,68648,157.5372,0.762274,4.979e-09
B0_ref11026_k2.structured,structured,0,11026,2,71548,210995,143140,347827,70300,185.351,0.762274,6.706e-12
B0_ref11026_k3.structured,structured,0,11026,3,71548,210995,143140,347827,70300,185.351,0.541484,6.139e-12
B0_ref11026_k4.structured,structured,0,11026,4,71548,210995,143140,347827,70300,185.351,0.333727,6.146e-12
B0_ref1338_k1.opt3,opt3,0,1338,1,69676,90522,139268,205139,68648,157.5124,0.940724,4.956e-09
B0_ref1338_k1.structured,structured,0,1338,1,71548,210995,143140,347827,70300,185.351,0.940724,6.538e-12
B0_ref1338_k2.structured,structured,0,1338,2,71548,210995,143140,347827,70300,185.351,0.782642,6.706e-12
B0_ref1338_k3.structured,structured,0,1338,3,71548,210995,143140,347827,70300,185.351,0.574677,6.139e-12
B0_ref1338_k4.structured,structured,0,1338,4,71548,210995,143140,347827,70300,185.351,0.371113,6.146e-12
B0_ref16833_k1.opt3,opt3,0,16833,1,69676,90524,139268,205138,68648,157.5128,0.937634,4.956e-09
B0_ref16833_k1.structured,structured,0,16833,1,71548,210995,143140,347827,70300,185.351,0.937634,6.538e-12
B0_ref16833_k2.opt3,opt3,0,16833,2,69676,90645,139272,205159,68648,157.537,0.772391,4.979e-09
B0_ref16833_k2.structured,structured,0,16833,2,71548,210995,143140,347827,70300,185.351,0.772391,6.706e-12
B0_ref16833_k3.structured,structured,0,16833,3,71548,210995,143140,347827,70300,185.351,0.557833,6.139e-12
B0_ref16833_k4.structured,structured,0,16833,4,71548,210995,143140,347827,70300,185.351,0.351924,6.146e-12
B0_ref2086_k1.opt3,opt3,0,2086,1,69676,90522,139268,205138,68648,157.5124,0.941305,4.956e-09
B0_ref2086_k1.structured,structured,0,2086,1,71548,210995,143140,347828,70300,185.351,0.941305,6.538e-12
B0_ref2086_k2.structured,structured,0,2086,2,71548,210995,143140,347828,70300,185.351,0.784577,6.706e-12
B0_ref2086_k3.structured,structured,0,2086,3,71548,210995,143140,347828,70300,185.351,0.57788,6.139e-12
B0_ref2086_k4.structured,structured,0,2086,4,71548,210995,143140,347828,70300,185.351,0.374803,6.146e-12
B0_ref281_k1.opt3,opt3,0,281,1,69676,90521,139266,205139,68648,157.5122,0.934553,4.956e-09
B0_ref281_k1.structured,structured,0,281,1,71548,210995,143140,347827,70300,185.351,0.934553,6.538e-12
B0_ref281_k2.structured,structured,0,281,2,71548,210995,143140,347827,70300,185.351,0.762274,6.706e-12
B0_ref281_k3.structured,structured,0,281,3,71548,210995,143140,347827,70300,185.351,0.541484,6.139e-12
B0_ref281_k4.structured,structured,0,281,4,71548,210995,143140,347827,70300,185.351,0.333727,6.146e-12
B0_ref3166_k1.opt3,opt3,0,3166,1,69676,90521,139268,205138,68648,157.5122,0.940724,4.956e-09
B0_ref3166_k1.structured,structured,0,3166,1,71548,210995,143140,347827,70300,185.351,0.940724,6.538e-12
B0_ref3166_k2.structured,structured,0,3166,2,71548,210995,143140,347827,70300,185.351,0.782642,6.706e-12
B0_ref3166_k3.structured,structured,0,3166,3,71548,210995,143140,347827,70300,185.351,0.574677,6.139e-12
B0_ref3166_k4.structured,structured,0,3166,4,71548,210995,143140,347827,70300,185.351,0.371113,6.146e-12
B0_ref345_k1.opt3,opt3,0,345,1,69676,90524,139267,205139,68648,157.5128,0.937634,4.956e-09
B0_ref345_k1.structured,structured,0,345,1,71548,210995,143140,347827,70300,185.351,0.937634,6.538e-12
B0_ref345_k2.structured,structured,0,345,2,71548,210995,143140,347827,70300,185.351,0.772391,6.706e-12
B0_ref345_k3.structured,structured,0,345,3,71548,210995,143140,347827,70300,185.351,0.557833,6.139e-12
B0_ref345_k4.structured,structured,0,345,4,71548,210995,143140,347827,70300,185.351,0.351924,6.146e-12
B0_ref474_k1.opt3,opt3,0,474,1,69676,90522,139268,205139,68648,157.5124,0.941305,4.956e-09
B0_ref474_k1.structured,structured,0,474,1,71548,210995,143140,347827,70300,185.351,0.941305,6.538e-12
B0_ref474_k2.structured,structured,0,474,2,71548,210995,143140,347827,70300,185.351,0.784577,6.706e-12
B0_ref474_k3.structured,structured,0,474,3,71548,210995,143140,347827,70300,185.351,0.57788,6.139e-12
B0_ref474_k4.structured,structured,0,474,4,71548,210995,143140,347827,70300,185.351,0.374803,6.146e-12
B0_ref682_k1.opt3,opt3,0,682,1,69676,90521,139267,205139,68648,157.5122,0.937634,4.956e-09
B0_ref682_k1.structured,structured,0,682,1,71548,210995,143140,347827,70300,185.351,0.937634,6.538e-12
B0_ref682_k2.structured,structured,0,682,2,71548,210995,143140,347827,70300,185.351,0.772391,6.706e-12
B0_ref682_k3.structured,structured,0,682,3,71548,210995,143140,347827,70300,185.351,0.557833,6.139e-12
B0_ref682_k4.structured,structured,0,682,4,71548,210995,143140,347827,70300,185.351,0.351924,6.146e-12
B0_ref6930_k1.opt3,opt3,0,6930,1,69676,90519,139268,205138,68648,157.5118,0.937634,4.956e-09
B0_ref6930_k1.structured,structured,0,6930,1,71548,210995,143140,347827,70300,185.351,0.937634,6.538e-12
B0_ref6930_k2.opt3,opt3,0,6930,2,69676,90643,139273,205158,68648,157.5366,0.772391,4.979e-09
B0_ref6930_k2.structured,structured,0,6930,2,71548,210995,143140,347827,70300,185.351,0.772391,6.706e-12
B0_ref6930_k3.structured,structured,0,6930,3,71548,210995,143140,347827,70300,185.351,0.557833,6.139e-12
B0_ref6930_k4.structured,structured,0,6930,4,71548,210995,143140,347827,70300,185.351,0.351924,6.146e-12
B1_ref103_k1.opt3,opt3,2,103,1,69676,90273,139266,205128,68648,157.4626,0.931314,4.966e-09
B1_ref103_k1.structured,structured,2,103,1,71548,210995,143140,347827,70300,185.351,0.931314,6.265e-12
B1_ref103_k2.structured,structured,2,103,2,71548,210995,143140,347827,70300,185.351,0.751849,5.891e-12
B1_ref103_k3.structured,structured,2,103,3,71548,210995,143140,347827,70300,185.351,0.525205,6.075e-12
B1_ref103_k4.structured,structured,2,103,4,71548,210995,143140,347827,70300,185.351,0.3165,5.756e-12
B1_ref110_k1.opt3,opt3,2,110,1,69676,90273,139266,205128,68648,157.4626,0.939261,4.966e-09
B1_ref110_k1.structured,structured,2,110,1,71548,210995,143140,347827,70300,185.351,0.939261,6.265e-12
B1_ref110_k2.structured,structured,2,110,2,71548,210995,143140,347827,70300,185.351,0.777897,5.891e-12
B1_ref110_k3.structured,structured,2,110,3,71548,210995,143140,347827,70300,185.351,0.567192,6.075e-12
B1_ref110_k4.structured,structured,2,110,4,71548,210995,143140,347827,70300,185.351,0.363123,5.756e-12
B1_ref118_k1.opt3,opt3,2,118,1,69676,90273,139266,205128,68648,157.4626,0.939261,4.966e-09
B1_ref118_k1.structured,structured,2,118,1,71548,210995,143140,347827,70300,185.351,0.939261,6.265e-12
B1_ref118_k2.structured,structured,2,118,2,71548,210995,143140,347827,70300,185.351,0.777897,5.891e-12
B1_ref118_k3.structured,structured,2,118,3,71548,210995,143140,347827,70300,185.351,0.567194,6.075e-12
B1_ref118_k4.structured,structured,2,118,4,71548,210995,143140,347827,70300,185.351,0.363141,5.756e-12
B1_ref230_k1.opt3,opt3,2,230,1,69676,90272,139266,205128,68648,157.4624,0.931314,4.966e-09
B1_ref230_k1.structured,structured,2,230,1,71548,210995,143140,347827,70300,185.351,0.931314,6.265e-12
B1_ref230_k2.structured,structured,2,230,2,71548,210995,143140,347827,70300,185.351,0.751849,5.891e-12
B1_ref230_k3.structured,structured,2,230,3,71548,210995,143140,347827,70300,185.351,0.525205,6.075e-12
B1_ref230_k4.structured,structured,2,230,4,71548,210995,143140,347827,70300,185.351,0.3165,5.756e-12
```

#### (an) `QN_2x4`: analytic $\log_{10}$ of the fault-free fraction per scenario and source, and the gate-only $f$ per device

**Source:** `validation/QN_2x4.json -> data.analytic.f0.<circuit>.<scenario>.log10_f0` (min and max over the circuits of a source) and `data.analytic.devices_by_source.<source>.<device>.{f_gate_only_worst, f_gate_only_mean}` (log10 taken by me).

**Columns and units:** `quantity`; `source`; `circuits` count; `log10_min`, `log10_max` (for the device rows: log10 of the worst and of the mean).

```csv
quantity,source,circuits,log10_min,log10_max
log10 f0 E1,opt3,19,-24.391,-24.388
log10 f0 E1,structured,60,-26.122,-26.121
log10 f0 E2,opt3,19,-23.311,-23.307
log10 f0 E2,structured,60,-25.09,-25.09
log10 f0 E3,opt3,19,-38.782,-38.773
log10 f0 E3,structured,60,-42.631,-42.63
log10 f0 E4,opt3,19,-23.445,-23.442
log10 f0 E4,structured,60,-25.037,-25.037
log10 f0 E5a,opt3,19,-25.56,-25.556
log10 f0 E5a,structured,60,-27.318,-27.318
log10 f0 E5b,opt3,19,-26.962,-26.959
log10 f0 E5b,structured,60,-28.755,-28.754
log10 f0 E5c,opt3,19,-34.676,-34.672
log10 f0 E5c,structured,60,-36.654,-36.653
log10 f0 E6a,opt3,19,-12.193,-12.192
log10 f0 E6a,structured,60,-13.058,-13.058
log10 f0 E6b,opt3,19,-48.801,-48.794
log10 f0 E6b,structured,60,-52.262,-52.262
log10 f0 E6c,opt3,19,-97.675,-97.661
log10 f0 E6c,structured,60,-104.6,-104.6
log10 f0 E7_0.10_lat,opt3,19,-0.73117,-0.72776
log10 f0 E7_0.10_lat,structured,60,-0.45504,-0.4548
log10 gate-only f H2-2,opt3,19,-26.24,-26.238
log10 gate-only f Helios-1,opt3,19,-25.102,-25.1
log10 gate-only f H1-1,opt3,19,-30.103,-30.102
log10 gate-only f H2-1,opt3,19,-34.064,-34.063
log10 gate-only f H2-2,structured,60,-28.378,-28.378
log10 gate-only f Helios-1,structured,60,-27.312,-27.312
log10 gate-only f H1-1,structured,60,-31.833,-31.833
log10 gate-only f H2-1,structured,60,-35.952,-35.952
```

#### (ao) The 28 native 2x2 circuits: HQC per shot and gate-only $f$ per device

**Source:** `validation/Q0P_2x2.json -> data.Q5.hqc.per_circuit`, `data.Q5.devices.<device>.f_gate_only_per_circuit`.

**Columns and units:** `circuit`; `hqc_per_shot` HQC; `f_gate_only_<device>` probability per shot.

```csv
circuit,hqc_per_shot,f_gate_only_H22,f_gate_only_Helios1,f_gate_only_H11,f_gate_only_H21
B0_ref06_k1,0.6116,0.792806,0.80456,0.756,0.742821
B0_ref06_k2,0.612,0.792762,0.804511,0.755972,0.742792
B0_ref06_k3,0.611,0.792873,0.804632,0.75604,0.742863
B0_ref06_k4,0.6094,0.793051,0.804825,0.756149,0.742976
B0_ref43_k1,0.612,0.792762,0.804511,0.755972,0.742792
B0_ref43_k2,0.6122,0.79274,0.804487,0.755959,0.742778
B0_ref43_k3,0.6112,0.792851,0.804608,0.756027,0.742849
B0_ref43_k4,0.6096,0.793028,0.804801,0.756136,0.742962
B0_ref30_k1,0.6118,0.792784,0.804535,0.755986,0.742807
B0_ref30_k2,0.6126,0.792695,0.804439,0.755932,0.74275
B0_ref30_k3,0.6114,0.792829,0.804584,0.756013,0.742835
B0_ref30_k4,0.6102,0.792962,0.804729,0.756095,0.742919
B0_ref21_k1,0.612,0.792762,0.804511,0.755972,0.742792
B0_ref21_k2,0.6128,0.792673,0.804415,0.755918,0.742736
B0_ref21_k3,0.6108,0.792895,0.804656,0.756054,0.742877
B0_ref21_k4,0.6102,0.792962,0.804729,0.756095,0.742919
B0_ref17_k1,0.6126,0.792695,0.804439,0.755932,0.74275
B0_ref17_k2,0.613,0.792651,0.804391,0.755904,0.742722
B0_ref17_k3,0.6108,0.792895,0.804656,0.756054,0.742877
B0_ref17_k4,0.6098,0.793006,0.804777,0.756122,0.742948
B1_ref14_k1,0.6102,0.792962,0.804729,0.756095,0.742919
B1_ref14_k2,0.6098,0.793006,0.804777,0.756122,0.742948
B1_ref14_k3,0.6108,0.792895,0.804656,0.756054,0.742877
B1_ref14_k4,0.609,0.793095,0.804873,0.756176,0.743004
B1_ref07_k1,0.6094,0.793051,0.804825,0.756149,0.742976
B1_ref07_k2,0.6096,0.793028,0.804801,0.756136,0.742962
B1_ref07_k3,0.6106,0.792917,0.80468,0.756068,0.742891
B1_ref07_k4,0.6092,0.793073,0.804849,0.756163,0.74299
```

#### (ap) Perlmutter request waves since 2026-10-13 (request commit, submissions, harvests)

**Source:** `git log` author times converted to UTC by me (request commits by the coordinator; `ci: submitted` / `ci: results` commits by the CI robot); the durations are MY ARITHMETIC.

**Columns and units:** `request_commit`; `tokens`; `request_utc`; `first_submit_utc`; `last_harvest_utc`; `hours_request_to_last_harvest`; `outcome`.

```csv
request_commit,tokens,request_utc,first_submit_utc,last_harvest_utc,hours_request_to_last_harvest,outcome
20b3887,C4_FCELLS_B C4_CF C2_CAL C4_F5_B0,2026-10-13T14:25Z,2026-10-13T14:26Z,2026-10-13T15:32Z,1.1,"3 PASS, C4_CF FAIL (S6)"
23d18e2,C4_F1_B0 C4_F7_B0 C4_F5_B1 C4_PART_01,2026-10-13T14:27Z,2026-10-13T15:32Z,2026-10-13T18:07Z,3.7,4 PASS
ebc60de,C4_F4_B0a C4_PART_02 C4_F4_B1a C4_PART_03,2026-10-13T15:33Z,2026-10-13T17:07Z,2026-10-13T19:07Z,3.6,"3 PASS, C4_PART_02 FAIL (S6)"
d7dd0c4,C4_F4_B0b C4_PART_04 C4_F4_B1b C4_PART_05,2026-10-13T15:41Z,2026-10-13T19:07Z,2026-10-13T21:07Z,5.4,"3 PASS, C4_PART_04 FAIL (S6)"
f940a18,C4_F8_B0a C4_PART_06 C4_F8_B1a C4_PART_07,2026-10-13T19:38Z,2026-10-13T20:07Z,2026-10-14T00:07Z,4.5,4 PASS
6c3e684,C4_F1_B1 C4_PART_10 C4_F7_B1 C4_PART_11,2026-10-14T15:05Z,2026-10-14T15:07Z,2026-10-14T16:07Z,1.0,4 PASS
f4c71e8,C2_KCHK C4_F8_B0b C4_PART_08 C4_F8_B1b C4_PART_09,2026-10-14T15:05Z,2026-10-14T16:07Z,2026-10-14T18:07Z,3.0,"4 PASS, C2_KCHK FAIL (K1, K2, S6)"
34f73a7,C4_F2_B0 C4_F2_B1 C4_PART_12..17,2026-10-15T17:37Z,,,,pending at 17:43Z
```

## 19. Suggested plots

Plots 1-40 are carried over from the 2026-10-13 report (their blocks are unchanged or regenerated; plot 40 now has 87 rows and plot 36 has 43 jobs); plots 41-56 are new (2026-10-15). For every plot state in the caption which `kind` the data are (measured / simulation / model / executor-reported) and the source file.


| # | plot | block and columns | how |
|---|---|---|---|
| 1 | **Timeline of gate verdicts** | (a): `date`, `gate`, `status` | scatter or strip chart, x = date, y = gate name (sorted by first date), colour = PASS / FAIL, marker size = `criteria_total`; annotate FAILs with `criteria_passed/criteria_total` |
| 2 | **Clean fraction of every hardware measurement (log y)** | (b): `run`, `f`, `lo`, `hi`, `statistic` | error bars on a log axis, x = run in time order, symbol by `statistic`; put the gate-only prediction 0.2195 (canary) and the signed bar 0.1 (and 0.05) as horizontal lines; shows the fall from 0.22 (model) to 6.65e-4 (fez measured), the rise to 0.127 (kingston with XY4, 2026-10-02) and, from block (b)'s new rows, the 2026-10-06 return to 0.073-0.082 and the 2x3 upper limit below 1e-4 |
| 3 | **DD A/B test** | (c): `cell`, `f`, `f_lo95`, `f_hi95`, `R`, `null_ratio` | bar chart of `f` with error bars; second panel `R` with its interval against the pulse-cost null (`null_ratio`) and the adoption threshold R >= 1.25; T1 is the collapsed cell |
| 4 | **Energy error and certificate for the 2x2 run** | (d): `E_R`, `E0_exact`, `weinstein_lo/hi`, `kato_temple_lo/hi`; (d2) random-basis `E_R_p2.5/p97.5/mean` | for each sector draw the exact E0 as a line, the B_sig E_R as a point with the Weinstein and Kato-Temple intervals as nested bars, and the random-equal-size 2.5-97.5 % band; also plot `abs_error` (log y) for B_sig vs B_all to show that B_all is exact by construction |
| 5 | **Garbage-only vs hardware** | (d2) `garbage_only` rows | single panel: histogram placeholder (all 100 seeds equal E0), shows that white noise reproduces the B_all energy |
| 6 | **Per-state counts vs exact weight** | (d3): `n_s`, `mu_s`, `ground_state_weight`, `in_B_sig` | scatter, x = exact weight (log), y = count (log), horizontal line at `mu_s`; colour by `in_B_sig`; shows which states carry signal above the noise expectation |
| 7 | **Support growth with Krylov order** | (e): `k_max`, `B_all`, `B_sig`, `shots`, `sector_dim` | two panels (one per sector), x = k_max, lines for B_all and B_sig as a fraction of `sector_dim`, secondary axis `shots` (log) to show that growth tracks shots |
| 8 | **Device landscape for 2x3** | (f): `device`, `f_gate_only_mean`, `f_mem_low/mid/high` | horizontal bar chart on a log x-axis of `f_gate_only_mean`, with a range bar from `f_mem_high` to `f_mem_low` for the Quantinuum rows; vertical lines at 0.1 and 0.05 |
| 9 | **Cost of a 2x3 campaign vs clean fraction** | (g): rows with `sector` = both: `f`, `hqc`, `shots`, `rule` | log-log lines, x = f, y = hqc, one line per rule; mark D3'-R; secondary y for shots; add the 1/f guide |
| 10 | **Near-clean correction** | (h): `arm`, `f_hit`, `f_ideal`, `r` with intervals | dot plot of r with error bars per arm and the pooled row, horizontal lines at 1 and r_nc = 1.115; second panel f_hit vs f_ideal vs f0_prime per arm; A5 rows show the opposite sign under idle dephasing |
| 11 | **QPU budget burn-down** | (i): `submitted_utc`, `cumulative_s`, `remaining_of_600_s` | step plot of cumulative seconds vs time with the 600 s line; label jobs by `what` |
| 12 | **Idle dephasing prediction vs measurement** | (n): `r`, `f_ref` for `L1_seed_alap`, `L4_all`; (n2) | line plot of Aer f vs r (log y) for each row with 68 % bands; overlay the measured kingston pilot f = 0.0413 and the H0_2x2 f = 0.127 (with XY4) as horizontal lines; mark r_crit = 0.33 |
| 13 | **Circuit cost by lattice** | (j): rows `coarse_step_*_cz`, `schedule[...]` `duration_us`, `T2_req_over_t_2q_f0.1_T1inf` | grouped bar chart on log y: CZ count (all-to-all vs routed) for 2x2, 2x3, 2x4; second panel the T2/t_2q requirement vs Heron's harmonic mean 1038 (a horizontal line) |
| 14 | **Per-term gate cost** | (j) rows `per_term_cz_all_to_all`, `per_term_ir_cx_before_transpile_*` | stacked or grouped bars per term for each lattice; shows plaq1 dominating at 2x3 and 2x4 (93 % of the 2x4 IR CX) |
| 15 | **Exact spectrum** | (k): `lattice`, `twoB`, `E0`, `E1`, `E2`, `support999`, `dt` | bar or table plot of E0 and gaps by sector; scatter of `support999` vs `dim` (log-log) to show sparsity; `PR` vs g2 for the 2x3 B=0 sector |
| 16 | **Plan fulfilment** | (l): `group`, `status` | stacked bar of F / FD / ND per group (manual 33 rows, amendments 18 rows) and overall (31 / 12 / 8) |
| 17 | **Day-to-day variation of the same circuits** | (o): `cell`, `f`, `f_lo95`, `f_hi95`, `f_20261002` for T0, T1, T3; (u) | paired bars (2026-10-02 vs 2026-10-06) with 95 % error bars for T0 / T1 / T3; annotate the ratio 2.04 for T0 and R_T3 2.819 vs 0.895; second panel the record statistics of (u) as a percent change to show that the summary statistics barely move while the clean fraction doubles |
| 18 | **H0_ddrep ratios and classes** | (o): `cell`, `R`, `R_lo95`, `R_hi95`, `null_ratio`, `class` | forest plot of R per cell on a log x-axis with the lines R = 1, R = 0.25 (collapse threshold) and R = 1.25 (adoption threshold); colour by class (M4 INTACT, the rest INTERMEDIATE); mark the 2026-10-02 R_T3 = 2.819 and R_T1 = 0.012 as hollow points |
| 19 | **x-pulse over-rotation per qubit** | (p): `qubit`, `epsilon_rad`, `eps_lo68`, `eps_hi68`, `eps_RB_level_sqrt6xerr_rad`, `c_over_x_error`, `hot_qubit_M4` | dot plot of epsilon_q with 68 % bars per qubit and the RB-level estimate as a second marker; second panel c_q / x_error_record with the line at 3; highlight qubits 91 and 95 |
| 20 | **Pulse-train signal** | (p): `P1_XX8`, `P1_XX32`, `P1_XX128`, `P1_XpXm128` | per-qubit lines of P1 against train length (8, 32, 128) for XX and the XpXm-128 end point; shows the coherent growth ($\sin^2$) of the uncompensated train |
| 21 | **2x3 plan: convergence margins** | (q): `f`, `sector`, `cv2_width_N_half_max_over_seeds`, `cv2_threshold`, `cv3_ratio_to_Etol_max`, `cv1_ratio_max`, `cv4_margin_over_Etol_min`, `cv5_W_min` | small-multiples grid, one panel per criterion, bars per (f, sector) against the limit line; shows that B=1 at s = 2 sits 4-21 % below the 0.15 limit while B=0 has more than a factor 3.7 of room on Kato-Temple |
| 22 | **Why B=1 needs s = 2** | (q2): `s_tried`, `cv2_width_half_max`, `rH_half_B_sig_max`, per `f` | width at N/2 versus s (1.5, 2) with the 0.15 limit; B_all and B_sig side by side |
| 23 | **Oracle width table** | (r): `sector`, `eps`, `size_S_eps_union_refs`, `rH`, `kt_width_exact_E1`, `W` | log-log of r_H against 1 - W (or against size) for B=0 and B=1 with horizontal lines at 0.1 and 0.15; the B=0 Kato-Temple curve on the same axes shows that H1 is met two orders of magnitude earlier |
| 24 | **Campaign cost: base vs re-sized** | (g): rows `D3'-R (ruling)` and `D3'-R x s` with sector = both | grouped bars of HQC at f = 0.05, 0.10, 0.15 (797 157 / 418 166 / 302 382 base; 1 279 660 / 665 605 / 471 801 re-sized); optional shots on a secondary axis |
| 25 | **K1: what the null excludes** | (s) and (b) K1 rows | log-x plot of the clean-fraction scale: the K1 95 % upper bound 2.06e-5 (arrow), the preregistered no-idle gate-only prediction 1.67e-5, the GO-A / GO-B thresholds 3e-4 / 1e-3, the signed bar 0.1 and the 2x2 values 0.04-0.13; shows the 2x3 pilot below every threshold |
| 26 | **Budget burn-down (extended)** | (i): 14 rows | the plot-11 step chart now ends at 327 s used, 273 s left; label the two 2026-10-06 jobs |
| 27 | **Simulated clean fraction by scenario (2x3, k=1)** | (v): rows with `family` = NAT-O0: `scenario`, `f_hat_ideal`, `f_hat_ideal_lo`, `f_hat_ideal_hi`, `f_hit` | horizontal dot plot with 95 % error bars, log x, one dot per scenario (E1-E4, E5a-c, E6a-c, E7 at four tiers); vertical lines at 0.1 and 0.05; colour the E3 row and the E6b/E6c rows (they fall below the bar); this is the "what noise level the bar tolerates" figure |
| 28 | **Response to the error scale** | (v) rows E6a, E1 (= scale 1), E6b, E6c: `f_hit`, `f0_k1`; scales 0.5, 1, 2, 4 | log-log of `f_hit` and of the analytic `f0_k1` against the error scale; the slope shows the exponential dependence; add E7 rows as a second series versus their `p2` from (v2) |
| 29 | **Memory dephasing is invisible in f_hit** | (v) rows E1, E5a, E5b, E5c: `f0_k1`, `f_hit`, `f_hat_ideal` against `t_round_s` (0.0005, 0.0011, 0.0044 from (v2); E1 at 0) | two series on one axis: `f0_k1` falls from 0.172 to 0.107 while `f_hit` stays 0.22-0.24; the visual statement of lesson 36 |
| 30 | **Optimisation variants against O0** | (v): for each scenario with O0..O4 cells, `f_hit - f_hit(O0)` with the combined interval | forest plot grouped by scenario; vertical line at 0; shows all variants consistent with O0 (two at about 2 sigma) |
| 31 | **C2_CAL: the three representations against the device** | (w): `mean_weight`, `se`; (w2): `pta`, `rm`, `kraus`, `device_T3` by `clbit` | left panel bars of `mean_weight` with se and a horizontal line at the device 9.771 and the unital limit 10; right panel the 20 marginals as lines per arm with the device as a band; shows PTA on top of the device, Kraus at 0.03-0.18, RM in between; add the planner's T0-versus-T3 caption |
| 32 | **Near-clean correction r, old and new** | (y): `arm`, `r`, `r_lo`, `r_hi` and the CF_traj values in the note | forest plot of r per arm (new) with the old values as hollow markers; horizontal lines at 1.078 (r_nc new), 1.115 (signed), 1.0; mark the k=4 arm as outside both |
| 33 | **F5_B0 convergence** | (z): `shots`, `err_all`, `kt_width`, `rH`, `W`, `recall_S999`, `B_all_size`; (z2) `E_tol` | log-log of `err_all` and `kt_width` against `shots` with the line `E_tol` = 0.01423 and the H1 width limit 0.1; second panel `B_all_size` and `recall_S999` against `shots`; annotate the proxy values 2.6-3.7e-3 at 34 909 shots from the text of Section 7.7 (the proxy curves are not in a block; use (q) for its widths) |
| 34 | **The clean-fraction landscape** | (x): `device`, `lattice`, `value`, `lo`, `hi`, `kind` | dot plot, y = device, x = value on a log axis, facet by lattice, marker shape by `kind`; vertical lines at 0.1 and 0.05; the 2x3 facet shows Quantinuum at 0.09-0.16 (models), the Aer simulations 0.007-0.47, IBM below 1e-4 (measured bound); the 2x4 facet is off the chart (values below 1e-24: annotate, do not plot) |
| 35 | **Encoding comparison** | (aa): `quantity`, `ratio_dedup_over_current`; (aa2) | bars of the ratios (all between 0.65 and 1.0) against the "meaningful" threshold 0.5; second panel detection fractions current versus dedup (1.0 -> 0.83 at 2x3 $B=0$) |
| 36 | **Perlmutter job ledger** | (a2): `job_id`, `gate`, `gate_status`, `gate_seconds` | Gantt-like horizontal bars of seconds per job in job-id order, colour by status (PASS / FAIL / UNKNOWN), annotate the three 15-21 s package failures and the 2 300-2 400 s budget failures; cumulative GPU-hours as a step line |
| 37 | **Campaign-33 status board** | (ad): `token`, `class`, `state`, `gate_status` | token x state heat map (one colour per state: done PASS, done FAIL, running, pending, planned, deferred, not requested, dropped); counts per class as a side bar |
| 38 | **Native circuit cost by lattice** | (ab): `ZZPhase per circuit`, `HQC per shot`, `two-qubit depth` for 2x2, 2x3, 2x4 (both 2x4 sources) | log-y bar chart: 252 / 2 158 / 69 676 (opt-3) and 71 548 (structured) ZZPhase; 0.61 / 4.97 / 157.5 and 185.4 HQC per shot; the 2x4 step is 32 times the 2x3 one (69 676/2 158 [MINE]) |
| 39 | **The campaign cost depends on the scenario** | (g) re-sized rows `D3'-R x s` and the tier of (v)/(ad) | bars of HQC at the tier each scenario selects: E1/E2/E4/E5/E6a/E7(0.15) tier 0.15 (471 801), E7(0.07/0.10) tier 0.10 (665 605), E3/E6b/E6c/E7(0.05) tier 0.05 (1 279 660); shows the factor 2.7 |
| 40 | **Gate verdict timeline, regenerated** | (a): `utc`, `gate`, `status`, `criteria_total` | as plot 1 but with the 54 rows; use the `utc` column for the x axis (the zones differ); add vertical markers at 2026-10-06 (reversal), 2026-10-09 (first Perlmutter results) and 2026-10-13 |
| 41 | **Every class-4 run: energy error and certificate width** | (ae): `token`, `run`, `sector`, `scenario`, `E_R_minus_E0`, `cert_width`, `cert_type`, `part`; (ag) bounds | two panels ($B=0$, $B=1$), x = file (grouped by run, parts side by side), log y: dots for `E_R_minus_E0`, open squares for `cert_width`; horizontal lines at the signed limits (0.1 Kato-Temple at $B=0$, 0.15 Weinstein at $B=1$) and at $E_{\rm tol}=0.0142$; colour by scenario. Caption: simulation, per part, not merged |
| 42 | **Error versus shots across scenarios** | (ae) and (ag): `shots_done` (per file) against `E_R_minus_E0`; (af) curves | log-log scatter; overlay the three nested shot curves of (af); shows the flattening near $10^{-4}$ |
| 43 | **Clean fraction of the full runs by scenario** | (ag): `run`, `scenario`, `sector`, `f_hat_ideal` with interval; (v) f-cell values for the same scenarios | dot plot with error bars, x = $\hat f_{\rm ideal}$, y = scenario, $B=0$ / $B=1$ markers; vertical lines at 0.10 and 0.05; f-cell values as hollow markers; mark the E7 labels (0.07, 0.10) on the axis to show the label/measured gap |
| 44 | **Per-circuit reference-hit fraction versus k** | (ah): `k`, `f_hit` with interval, `scenario` | box or strip plot of `f_hit` by `k` for each scenario; shows that $f_{\rm hit}$ is roughly $k$-independent (one coarse step) while the shot counts are not |
| 45 | **Bootstrap band versus point value** | (ae): `E_R_minus_E0`, `boot_err_lo`, `boot_err_hi` | for each file a vertical bar (bootstrap band) and a dot (point); all 25 dots lie below their bars |
| 46 | **The S3 quota in simulation** | (ag) rows `F4_B* (a+b)`, `F8_B* (a+b)`: `merged_recall_S999_lower_bound`, `merged_E_R_minus_E0_upper_bound`, `shots_done` | small table-plot against gate S3's criterion recall $\ge0.9$ at $2\times10^5$ shots; mark the F4 $B=0$ shortfall (191 424) |
| 47 | **Class-2: every arm's mean Hamming weight** | (aj): `engine`, `representation`, `mean_w`, `se` | horizontal dot plot with $\pm1.96$ se bars, grouped by job (C2_CAL run 3, laptop CPU, C2_KCHK, device); vertical lines at 10 (unital limit) and 9.77 (device); colour by representation; caption: device on IBM-T3, all simulations on IBM-T0 |
| 48 | **GPU Kraus inconsistency** | (aj) rows `kraus` of C2_KCHK: cuStateVec, native, fusion off; plus CPU Kraus | four points with error bars; annotate the pairwise $z$ (5.78, 1.67, 7.36) |
| 49 | **Class-2 marginals per bit** | (ai): `arm`, `clbit`, `p1`, `se` | lines (or a heat map) of $P(1)$ against clbit for every arm and the device; the Kraus GPU arms sit at 0.02-0.25, RM and the device near 0.1-0.5 |
| 50 | **2x2 f-cells by scenario** | (ak): `scenario`, `k`, `f_hit` with interval, `f0` | dot plot per scenario of the 7 $k=1$ cells (or all 28 with colour by $k$), with $f_0$ as a second marker; shows the near-constant ratio $f_{\rm hit}/f_0\approx1.04$ at 2x2 versus 1.34 at 2x3 |
| 51 | **2x2 versus 2x3 under the same scenarios** | (ak) mean $k=1$ $f_{\rm hit}$ per scenario against (v) $k=1$ $f_{\rm hit}$ per scenario | scatter, x = 2x3, y = 2x2, one point per scenario E1-E6c; shows how lattice size compresses the clean fraction |
| 52 | **Native 2x4 sources** | (am): `source`, `n_zz`, `n_phasedx`, `depth`, `hqc_per_shot`, `B_bound` | paired bars opt-3 versus structured; log-y panel of `B_bound` against the $10^{-10}$ bar |
| 53 | **2x4 is out of reach** | (an): `quantity`, `log10_min`, `log10_max` | horizontal bars of $\log_{10}f_0$ per scenario and source with the bar $\log_{10}0.1=-1$; only E7 (constructed) is near it |
| 54 | **2x2 native: f per device and per circuit** | (ao) | strip plot of `f_gate_only_<device>` across the 28 circuits (nearly constant across circuits: the H2-2 values span 0.79265-0.79310) per device |
| 55 | **Perlmutter waves** | (ap) and (a2): `request_utc`, `first_submit_utc`, `last_harvest_utc` | Gantt chart per wave with the maintenance window 2026-10-21 06:00 to 2026-10-28 06:00 UTC shaded |
| 56 | **Cumulative GPU-hours** | (a2): `gate_seconds` cumulated by `harvested_utc` | step plot to 43 576 s (12.10 GPU-hours) with campaign-33 jobs coloured by class |

**What a good chart script can add (updated 2026-10-15):** (i) a "simulation versus device" figure: plots 43 (simulated $\hat f_{\rm ideal}$ by scenario), 34 (landscape with the measured IBM points) and 47 (class 2) side by side, captioned with the evidence kind of every point; (ii) a "does the method work at 2x3?" figure: plot 41 with the signed limits, plot 42 with $E_{\rm tol}$, and plot 46 for the S3 quota; (iii) keep every simulated point visually distinct (hollow, or a separate facet) from the three measured families (fez, kingston 2x2, kingston 2x3 upper bound).

## 20. Glossary

Terms in alphabetical order. **(project label)** marks names invented inside this project (mostly by its planner agent), which are not standard terms.

- **$a$ (random acceptance)** *(project symbol)*: the fraction of uniformly random bit strings that the decoder accepts into a sector; $a=\dim/4096$ at 2x2 ($0.00927734375$ for $B=0$, $0.0048828125$ for $B=1$), $0.146\,\%$ at 2x3.
- **Accepted shot / yield**: a shot whose bit string passes all decoder checks; yield = accepted shots divided by shots. Not the same as a clean shot.
- **Aer**: Qiskit's classical simulator (`qiskit-aer`); `AerSimulator.from_backend(...)` builds a noise model from a device calibration.
- **ALAP / ASAP**: "as late as possible" / "as soon as possible" scheduling of gates in a circuit; ALAP writes the idle waits as explicit `delay` instructions and moves qubits' first gates later, so qubits idle in $|0\rangle$ (which does not dephase) rather than in superposition.
- **Amendment 01**: the project's signed modification of the manual (`proposal/amendment_01_devices_and_budgets.md`): items 1-3 signed 2026-09-23, items 4-5 open.
- **B (baryon number)**: conserved quark number divided by the number of colours; $B=0$ vacuum sector, $B=1$ one-baryon sector. Project key `twoB` = $2B$. Also, loosely, $B$ or $|B|$ = the support (see **support**).
- **$B_{\rm all}$, $B_{\rm sig}$** *(project labels, `prompts/24` decision P9)*: $B_{\rm all}$ = every accepted state of the sector; $B_{\rm sig}$ ("signal support") = states whose count exceeds the uniform-noise expectation $\mu_s=Na/\dim$ at the one-sided $3\sigma$ Poisson level.
- **BFS**: breadth-first neighbour growth; a classical control that adds Hamiltonian neighbours of the current support.
- **Braket / Azure**: Amazon Braket and Microsoft Azure Quantum, cloud routes to IonQ and Quantinuum devices.
- **Calibration fingerprint (rule D9)** *(project label)*: a sha256 hash of the calibration-record numbers the prediction reads; submission requires the live hash to equal the preregistered one.
- **Calibration drift (day-to-day variation)** *(descriptive term)*: the change of a device's calibration record between days (on `ibm_kingston`, 1 110 values changed between 2026-10-02 and 2026-10-06, by factors 0.102 to 111.3); the clean fraction of the same frozen circuits moved by a factor 2.04 between those days, more than any decoupling effect seen on 2026-10-06.
- **Canary** *(project term)*: the first small QPU job (3 pubs x 267 shots on `ibm_fez`, 2.0 s) whose result decided whether the main run would go ahead.
- **CF_traj** *(project gate)*: Pauli-trajectory decomposition proving that the reference-hit excess is a near-clean term; also yields $r_{nc}$.
- **CIPSI**: configuration interaction by perturbation with selection; classical selected-CI method that grows a subspace by scoring Hamiltonian neighbours $|\langle c|H|\psi_R\rangle|^2/(H_{cc}-E_R)$.
- **Circuit family**: the 28 (2x2) or 44 (2x3) coarse-step circuits = references $\times\ k=1..4$.
- **Clean fraction $f$**: probability that a shot carries no error at all (manual Step 4.4); see also $f_0$, $f_{\rm hit}$, $f_{\rm ideal}$.
- **Clifford / T gate / non-Clifford**: gate classes in fault-tolerant quantum computing; non-Clifford gates (such as arbitrary rotations) are expensive to protect by error correction.
- **Codeword / codec / decoder**: the bit string assigned to a physical basis state; the module that maps states to bit strings; the per-shot checker that rejects non-physical strings.
- **Coarse step** *(manual term)*: one circuit $\prod_\gamma e^{-iH_\gamma k\Delta t}$ for a reference configuration, order $k=1..4$.
- **Coarse-step order $k$**: the multiple of $\Delta t$ used in the circuit.
- **Context-aware DD**: dynamical decoupling in which neighbouring qubits receive mutually orthogonal pulse patterns so that $ZZ$ crosstalk is also cancelled (arXiv:2403.06852).
- **Corner / interior vertex**: lattice sites with two / three link ends; they use 3 / 4 qubits.
- **CV0-CV5** *(project criteria, `prompts/30`, amended by `prompts/31`)*: convergence and weighted-coverage criteria for the 2x3 plan check (gate `CV_2x3_plan`): CV0 structural checks; CV1 $E_R(N/2)-E_R(N)\le E_{\rm tol}$ (convergence in shots); CV2 the certificate width at $N/2$ and $N$ meets H1 / H2 (Kato-Temple with the exact $E_1$ at $B=0$, width $\le0.1$; Weinstein $r_H\le0.15$ at $B=1$); CV3 $E_R(B^{(4)})-E_R(B^{(5)})\le E_{\rm tol}$ (convergence in the Krylov order, the $k=4\to5$ step); CV4 better than random bases of equal size by at least $E_{\rm tol}$; CV5 captured weight $W\ge0.99$. Evaluated on $B_{\rm all}\cup$ references.
- **CZ / RZZ / ZZPhase**: two-qubit gates: controlled-Z (IBM native), $e^{-i\varphi Z\otimes Z/2}$ (ion-trap native), and Quantinuum's name for the latter (angle in half-turns).
- **D3', D3'-R, D3'-S, D3-type union** *(project labels)*: shot-sizing rules. D3': every sector state must get $\lambda^*$ expected clean counts from the $k=4$ circuits at $0.7f$ (used at 2x2, infinite at 2x3); D3'-R ("recall"): $\lambda^*$ on every state of $S_{99}$ plus recall of $S_{999}\ge0.9$ with probability $\ge0.95$ (signed as the minimum 2x3 sizing); D3'-S: $\lambda^*$ on every state of $S_{999}$; D3-type union: the manual's eq. (5) rule scaled by $1/(0.7f)$.
- **DD (dynamical decoupling)**: sequences of $\pi$-pulses in idle windows that cancel slowly varying phase errors; each pulse costs its own gate error. **XY4**: the four-pulse sequence $X\,Y\,X\,Y$.
- **Devicewatch** *(project script `h0_devicewatch.py`)*: a free metadata poll that declares a device ready only when its status is `active` and every CZ error is published; `operational` alone is not enough (the 2026-10-06 record of `ibm_kingston` read operational while in maintenance).
- **Dirac sea**: the vacuum reference configuration (odd sites doubly occupied, even sites empty, no flux).
- **Dressed-site basis**: the gauge-invariant basis built from local singlets at each vertex (spin-network basis).
- **Dry run**: running the real submission/analysis path on a simulator before any hardware spend.
- **$E_0$, $E_R$**: exact ground-state energy; Ritz energy (lowest eigenvalue in the chosen subspace).
- **echo $T_2$ / free-induction $T_2^*$**: dephasing time measured with one refocusing pulse (the number in IBM calibration records) / of free evolution (what an idle qubit in a circuit feels).
- **Electric term**: the part of $H$ proportional to $g^2 j(j+1)$.
- **eHQC**: the Quantinuum credit unit on its emulators.
- **$\epsilon_q$ (over-rotation) and $c_q$ (per-pulse cost)** *(project labels, gate `H0_ddrep`)*: the coherent angle in radians by which one $x$ pulse of qubit $q$ over-rotates, and its incoherent error per pulse, fitted from pulse trains of 8, 32 and 128 pulses (XX-$n$: $n$ repeated $X$; XpXm-$n$: alternating $+X,-X$, which cancels a coherent over-rotation). Measured $\epsilon_q=0.0148$-$0.0204$ rad on all 12 patch qubits.
- **$E_{\rm tol}$** *(project constant, `prompts/30`)*: $E_R(R\cup\text{top 80 \% of }S_{999})-E_0$, the Ritz error the manual's own recall target tolerates; $1.4225\times10^{-2}$ ($B=0$) and $1.1040\times10^{-2}$ ($B=1$) at 2x3.
- **Executor / planner / reviewer / runner / scribe**: the project's agent roles (Section 4.4).
- **$f_0, f_0'$**: fault-free fraction (no gate error); $f_0'$ includes correct readout of the reference string.
- **$f_{\rm hit}$** *(project label)*: reference-string clean fraction: (count of the circuit's most probable ideal string minus accidental hits) / (shots $\times$ ideal probability $\times$ readout factor).
- **$f_{\rm ideal}$, $\hat f_{\rm ideal}$** *(project labels)*: ideal-sample fraction (shots that sample the ideal output distribution to within TV distance $10^{-3}$: fault-free plus benign-fault shots) and its device estimator $f_{\rm hit}/r_{nc}$.
- **$f_T$** *(project label, withdrawn)*: tail-class clean fraction; inflated by noise scattering.
- **Floor theorem** *(project term)*: the effective clean rate of each state is at least $f_{\rm ideal}(1-2\delta/p_c)$.
- **Firm (NO-GO)** *(project term, gate `K1_2x3_fpilot`)*: a decision is called firm when the point value and both ends of the 95 % interval fall in the same class.
- **Gate (project sense)**: a script whose result is recorded in `validation/<GATE>.json`; **validation gate** vs **measurement gate** (Section 4.3).
- **Garbage-only / random-equal-size baselines** *(project terms)*: control analyses of the 2x2 run: uniformly random bit strings at the same shot counts through the decoder; random subsets of the sector codewords of the same size as $B_{\rm sig}$.
- **Gauss's law**: the local constraint that colour charge cancels at every site; physical states satisfy $G_a(x)|\psi\rangle=0$.
- **Gauge theory / SU(2) / staggered quarks / link / plaquette / Kogut-Susskind**: see Section 2.1.
- **Givens rotation / Gray code / multiplexed rotation**: building blocks of the exact structured circuits (two-level rotations, ordering of control patterns, rotations controlled on many qubits).
- **Hamiltonian $H$, residual $r_H$**: the energy operator; $r_H=\|(H-E_R)\psi_R\|$.
- **H0_ddrep, K0, K1** *(project gate names)*: H0_ddrep = the one-job replication on `ibm_kingston` of the XY4 gain and the context-aware collapse, with four mechanism cells and four pulse-train pubs (2026-10-06); K0 = the model analysis of how the 2x3 circuit routes and what clean fraction a calibration record allows on `ibm_kingston` (`K0_2x3_2x4`); K1 = the 2x3 clean-fraction pilot on `ibm_kingston` (`K1_2x3_fpilot`, 2026-10-06).
- **Hot qubits** *(project term)*: the two patch qubits (91 and 95) that carry the most pulses in cell T1 and whose pulses cell M4 removes (qubit 91 is also the patch's worst $T_1$/$T_2$ qubit in the record, 99 / 68 $\mu$s, `prompts/32`).
- **Heavy-hex, Heron (r2)**: IBM's qubit connectivity pattern and processor generation (156 qubits). **Nighthawk**: IBM's newer square-lattice processor.
- **HQC**: Hardware Quantum Credit, Quantinuum's billing unit, $\mathrm{HQC}=5+C(N_{1q}+10N_{2q}+5N_m)/5000$ per job ($C$ shots).
- **Idle window / idle budget $S_{\rm idle}$**: time a qubit waits while others are gated / the resulting relaxation error in nats, $S_{\rm idle}=S_{T_1}+S_{T_2}$.
- **Intertwiner label $\iota$**: label distinguishing two gauge-singlet combinations at a vertex.
- **IR (intermediate representation)**: the project's backend-independent circuit gate list.
- **Iceberg code**: a distance-2 error-detecting code $[[k+2,k,2]]$ for trapped ions.
- **Kato-Temple / Weinstein**: error-bound formulas for an eigenvalue from a residual (Section 2.7); "gap-assumed" means they assume the nearest exact level to $E_R$ is the ground state; at 2x3 the project reads Kato-Temple with the *exactly known* $E_1$ for the $B=0$ width (owner decision 2026-10-05).
- **Krylov space**: the span of $e^{-ik\Delta t H}|b_0\rangle$.
- **$\lambda^*=6.2958$**: the Poisson mean at which a count of at least 3 has probability 0.95.
- **Leakage**: weight of a circuit's output outside the valid codeword space (required below $10^{-9}$).
- **Link consistency**: the decoder check that the two ends of a link agree on its flux bit.
- **M1-M4, T0-T3 (cells)** *(project labels, `H0_ddtest`, `H0_ddrep`)*: dynamical-decoupling variants run on the same two circuits: T0 none, T1 context-aware staggered $X$, T2 client XY4 in every window $\ge256$ ns, T3 client XY4 in windows $\ge1.024\ \mu$s, M1 T1 with alternating pulse signs, M2 XX pairs in T2's windows, M3 M2 with alternating signs, M4 T1 minus the pulses on qubits 91 and 95.
- **Measurement gate**: see Gate.
- **Mixture estimator** *(project term)*: fits one weight separating the ideal distribution from uniform noise over all accepted strings.
- **Near-clean string / near-clean term (rule M4.4)** *(project terms)*: a string with a few errors that still passes all decoder checks; the additional term in the yield model.
- **NO-GO / GO-A / GO-B / AMBIGUOUS** *(project decision words)*: outcomes of preregistered go rules.
- **COLLAPSED / INTACT / INTERMEDIATE** *(project classes, `H0_ddrep`)*: a cell's ratio $R=X_i/X_0$ of excess reference hits to those of the no-DD cell is COLLAPSED if its 95 % upper end is below 0.25, INTACT if its lower end is above 1, else INTERMEDIATE.
- **Oracle-width table** *(project term, `prompts/31`)*: for each cut $\varepsilon$ the Ritz error and certificate widths of the exact (oracle) support of weight $1-\varepsilon$; the statement of what the best possible support of that size certifies (block (r)).
- **Participation ratio (PR)**: effective number of configurations in a state, $1/\sum_b|c_b|^4$.
- **Patch**: the set of physical qubits used; **rule R1'** *(project)*: exhaustive embedding search scored by the idle-aware clean fraction.
- **Pauli twirling**: random Pauli gates around each two-qubit gate, undone afterwards; reshapes errors but does not reduce the average error.
- **PhasedX**: Quantinuum native one-qubit rotation $R_z(b)R_x(a)R_z(-b)$.
- **Preregistration**: writing circuits, shots, decision rule and prediction to a committed file before the device data exist.
- **Pub**: one circuit with its parameters submitted in a Qiskit SamplerV2 job.
- **Pulse train** *(project term)*: a circuit of $n$ repeated single-qubit pulses on every qubit used to measure the pulse's own error (block (p)).
- **QCCD**: quantum charge-coupled device architecture (trapped ions physically moved between zones; all-to-all connectivity). **QCUP**: the DOE/ORNL Quantum Computing User Program. **QPY**: Qiskit's circuit serialization format. **QPU**: quantum processing unit.
- **QEC**: quantum error correction.
- **$r_{nc}$** *(project label)*: near-clean correction = upper 95 % bound of the pooled $f_{\rm hit}/f_{\rm ideal}(10^{-3})$ from CF_traj; $1.115$.
- **$r_{\rm crit}$, $r_{\rm eff}$** *(project labels)*: the break-even ratio $T_2^*/T_2^{\rm echo}$ above which $f\ge0.1$ (0.3285 preregistered) and the ratio the pilot measured (0.0974).
- **Recall $R_\varepsilon$**: $|B\cap S_\varepsilon|/|S_\varepsilon|$.
- **Reference configuration**: starting configuration $|b_0\rangle$ of a circuit (Dirac sea, one-meson states, diquark states).
- **Re-sizing multiplier $s$** *(project label, `prompts/30`/`31`)*: the uniform factor applied to a sector's D3'-R shots (grid 1.5, 2, 3, 4, 6, 8; smallest passing wins); plan of record $s=1$ at $B=0$, $s=2$ at $B=1$.
- **Ritz value / Ritz vector**: eigenvalue / eigenvector of $H$ restricted to a subspace.
- **Rule C22 (noise saturation)** *(project label)*: once $Na/\dim\gtrsim5$ the sector is filled by noise alone.
- **S99, S999** *(project notation)*: smallest sets carrying 99 % / 99.9 % of the ground-state weight (the 99.9 % support).
- **Saturation parameter $Na/\dim$**: expected accidental hits per sector state.
- **SKQD / SQD**: sample-based Krylov / sample-based quantum diagonalization.
- **Stage E / Stage P / Stage T / Stage R / Stage A** *(project labels)*: E = emulator run, P = hardware pilot (Quantinuum plan), T = the DD test, R = the full 2x2 run (`prompts/24`), A = the native-gate compilation (`prompts/26`).
- **Static charge**: an infinitely heavy quark used to probe the potential $V(r)$.
- **Structured gates**: the exact circuit construction of gate S2.
- **Support**: the set $B$ of decoded configurations used for the projected diagonalization.
- **$T_1$, $T_2$**: energy-relaxation and dephasing times. **PTA** *(project usage, two meanings)*: (i) in the idle-aware $f$ model, "the Pauli-twirled approximation bound" that charges every idle error as fatal ($f=f_{\rm gates}e^{-S_{\rm idle}}$); (ii) since campaign 33, the **Pauli-twirled representation of thermal relaxation** in the Aer class-2 simulations (see the new-terms list below).
- **Tier A / B / C** *(project, `prompts/27`)*: preregistered levels of a 2x3 hardware claim (Section 14.4).
- **TV distance**: total-variation distance between two probability distributions.
- **VQE**: variational quantum eigensolver (the older approach in the literature).
- **Weight $W(B)$**: $\sum_{s\in B}|c_s|^2$ (captured ground-state weight).
- **Yield model**: $y=0.82f+(1-f)a+$ near-clean term.
- **0.82 readout factor**: the manual's survival of 20-qubit readout at 1 % error each.
- **30-minute rule**: the laptop rule of Section 4.3.


### New terms since 2026-10-06 (alphabetical)

- **Aer convention (for depolarizing noise)**: Qiskit Aer's `depolarizing_error(p, n)` is $\mathcal E(\rho)=(1-p)\rho+p\,I/2^n$, whose probability of a non-identity Pauli ("fault") is $\tfrac{15}{16}p$ for two qubits and $\tfrac34p$ for one. The project's device table instead treats the published error as the full fault probability; the two conventions differ by 15 % in the 2x3 clean fraction (Section 2.12).
- **Bootstrap (multinomial)**: resampling the shots of each circuit with replacement to get an interval; for support-based quantities such as $E_R$ it is biased pessimistic because a resample can drop rare states but cannot add new ones.
- **Campaign 33** *(project label)*: the 33-token simulation campaign on Perlmutter (`prompts/33`-`33c`, Section 7).
- **Class 1 / 2 / 3 / 4** *(project labels, `prompts/33`)*: 1 = no noise, no optimisation; 2 = IBM noise from the `ibm_kingston` record; 3 = Quantinuum-native circuits, noiseless; 4 = Quantinuum-native circuits with error scenarios E1-E8 and optimisation variants O0-O6.
- **Concurrent poller**: the Perlmutter-side script (`ci/poll_concurrent.sh`) that runs up to 4 allowlisted jobs at once from the request files in `ci/requests/`.
- **cuStateVec**: NVIDIA's GPU statevector library used by Aer's GPU backend; 7.8-8.7 times faster than Aer's `batched_shots_gpu` mode on these circuits.
- **Dedup (E2) codec** *(project label)*: the unsigned alternative codeword layout that stores each link bit once instead of at both ends (8 / 13 / 18 qubits at 2x2 / 2x3 / 2x4); shorter by 7-10 % in gates but with weaker error detection (`ENC_compare`).
- **E1-E8, E5a/b/c, E6a/b/c, E7(f)** *(project labels)*: the class-4 noise scenarios of Section 7.1.
- **E5' (E-five-prime)** *(project label)*: a search over the meaning of the extra codeword bit inside the current codec widths (`ENC_compare`).
- **Executor-reported [EXEC]**: a number quoted from an executor's paused, uncommitted work, not in a committed gate JSON.
- **F1-F8, B0 / B1, a / b halves** *(project labels)*: the class-4 full SKQD runs (scenario x variant) and their sectors; a / b are the two $10^5$-shot halves of an S3-quota run.
- **f-cell** *(project label)*: a 2 000-shot clean-fraction measurement of the four Stage-E circuits under one scenario and one optimisation variant.
- **Guppy / HUGR / Selene**: Quantinuum's software route for Helios: a Python-embedded language (Guppy) compiled to a graph IR (HUGR) and run on the Selene simulator; tier T6 of `prompts/35`.
- **Hamming weight**: the number of 1s in a bit string; its mean over many shots ($\bar w$) is the test statistic of C2_CAL (10 for a uniformly random 20-bit string).
- **IBM-U / IBM-T0 / IBM-T3** *(project labels)*: the routed 2x3 circuits on the `ibm_kingston` patch: U unscheduled (no delays), T0 ALAP-scheduled with explicit delays and no pulses, T3 the flown circuit with client-side XY4 pulses in the windows of at least 1.024 $\mu$s.
- **I-GATE / I-ECHO / I-STAR / I-XY4 / I-COH** *(project labels)*: the IBM-record noise models of class 2 (gate errors only; plus relaxation on delays at the echo $T_2$; at $0.174\,T_2^{\rm echo}$; on the XY4 circuit; plus coherent $x$ over-rotation).
- **K1 strings**: the $10^5$ bit strings the real device returned for `B0_ref117_k1` on 2026-10-06 (`data/hardware/K1_2x3_ibm_kingston/counts/`), the only 2x3 device data.
- **Kraus arm / Kraus channel**: Aer's exact thermal-relaxation channel in Kraus form (here the "production" class-2 representation after C2_CAL); non-unital.
- **Matched-$f$ (E7)** *(project label)*: a depolarizing scenario whose $p_2$ is inverted so that the gate-only analytic clean fraction of the family equals a target $f$.
- **Memory (transport) dephasing**: phase error of idle trapped ions during the moves between zones in a QCCD machine; modelled as a Pauli-$Z$ with probability (rate $\times$ round time) per two-qubit layer; the project's one unmeasured trapped-ion term.
- **Nexus**: Quantinuum's cloud platform and Python client (`qnexus`); needed for the syntax checkers and emulators.
- **O0-O6 (optimisation variants)** *(project labels)*: O0 none; O1 pytket peephole resynthesis; O2 qiskit level 1; O3 level 2; O4 level 3; O6 approximate KAK synthesis (information only).
- **Part / slot (`C4_PART_NN`)** *(project labels)*: a run that does not fit one 60-minute job is split into parts; extra parts run in re-usable generic slots whose seeds come from the run's own token.
- **pecos / `H2-1LE`**: the open-source Quantinuum local emulator (pytket-pecos, quantum-pecos) in its noiseless mode.
- **Perlmutter / shared QOS**: the NERSC supercomputer and its shared GPU queue (charged $G/4$ of a node per hour).
- **Plan tier** *(project label)*: the largest of 0.05 / 0.10 / 0.15 not above the lower 95 % end of a scenario's $\hat f_{\rm ideal}$; chooses which plan-of-record shot counts a run uses.
- **Preflight (campaign driver)**: the first step of every campaign job, importing its module list and exiting in under 5 s with an install line if one is missing.
- **PTA arm / Pauli-twirled representation** *(project label)*: relaxation replaced by a stochastic Pauli channel with $p_X=p_Y=\tfrac14(1-e^{-t/T_1})$, $p_Z=\tfrac12(1-e^{-t/T_2})-\tfrac14(1-e^{-t/T_1})$; unital, fast, cannot produce a Hamming-weight deficit.
- **Q1L / Q1S** *(project labels, `prompts/35`)*: Q1L the local-equivalence proof of a 28-qubit native circuit (every single-qubit segment between the two-qubit skeleton equal to $10^{-12}$); Q1S the statevector check on the sparse path or the GPU.
- **QPY version 13**: the Qiskit circuit file format version that Perlmutter's qiskit 1.4.3 can read.
- **RM** *(project label)*: the "$T_2:=\min(T_2,T_1)$, no Kraus" representation of relaxation, meant to be as fast as PTA and as faithful as Kraus; not validated and suspected of a bug (Section 8).
- **S6** *(project criterion of the campaign gates)*: "shots at least the token's minimum; no reduction below the minimum"; the criterion that `C4_FCELLS_A` and `C4_CF` fail.
- **Scenario-aware rate** *(project label)*: seconds per shot of a scenario = ladder rate $\times$ measured slope ratio $\rho_s$.
- **Stage-E circuits**: the four circuits (`B0_ref25_k1`, `B1_ref57_k1`, `B0_ref25_k4`, `B1_ref57_k4`) used for the clean-fraction cells and for the Quantinuum emulator pilot.
- **Tiers T1-T6** *(project labels, `prompts/35`)*: native-and-exact, noiseless sampling, vendor noise models, vendor local emulator, syntax checker, Helios HUGR.
- **Token** *(project term)*: one allow-listed Perlmutter job name.
- **Unital / non-unital channel**: a channel that maps the maximally mixed state to itself (Pauli noise) / one that does not (amplitude damping, which drives populations to $\lvert0\rangle$).
- **Unmerged work / worktree**: a git working copy on its own branch (`c33c`, `q35`); results there are not on `master`.
- **WIP commit**: a work-in-progress commit made when an executor is paused (`3ce492a`, `e5503b8`).



### New terms since 2026-10-13 (alphabetical)

- **Assembly** *(project term)*: the laptop stage `scripts/campaign33.py --stage assemble` (`src/skqd/campaign33/assemble.py`) that merges the parts of split runs (sums their accepted counts), evaluates CV0-CV5 and P15 on merged runs and writes `validation/C33_campaign.json`; not yet run on real data.
- **`C2_KCHK`** *(project token, `prompts/33d`)*: the class-2 GPU Kraus check: one circuit, Kraus on three GPU engines, RM on the GPU, Kraus and RM on the CPU; decisions K1 (bug confirmed), K2 (production representation rm / blocked), K3 (validated Kraus GPU path).
- **CPU affinity / `--cpus-per-task`**: the set of CPU cores a process may run on; Slurm's option that sets it per job step. Without it on `srun`, a step gets one core (`prompts/33e` R1).
- **cuStateVec / native kernels / gate fusion**: three ways Aer executes a statevector on an NVIDIA GPU: NVIDIA's cuStateVec library, Aer's own GPU kernels, and the optimisation that merges adjacent gates into one matrix before applying it ("fusion"); a correct simulator gives the same distribution with any of them.
- **Deadline stop / `call_bound`** *(project term)*: the sampler's rule that skips the next round of calls when a conservative bound $t(s)\le t_p\max(1,s/s_p)$ predicts it would overrun the job's time budget; it caused the S6 failures of `C4_PART_02` and `C4_PART_04`.
- **Equal-fraction split** *(project term)*: cutting a run into parts so that every circuit's shots are split at the same fraction; part 1 takes the first half of each circuit's chunk plan, part 2 the second.
- **F-run, F1-F8** *(project labels, `prompts/33`)*: the class-4 full SKQD runs: F1 = E1 x NAT-O0, F2 = E2, F3 = E3, F4 = E7(0.10) at the S3 quota, F5 = E7(0.07) at the $f=0.10$ plan, F6 = E5b, F7 = E1 x NAT-O2, F8 = E8 on IR-L3-RZZ at the S3 quota; suffix `_B0` / `_B1` the sector, `a` / `b` the quota half.
- **Garwood interval**: the exact (conservative) 95 % confidence interval for a Poisson count $n$: $[\tfrac12\chi^2_{0.025}(2n),\ \tfrac12\chi^2_{0.975}(2n+2)]$.
- **Half (a / b)** *(project label)*: one of the two independently seeded $10^5$-shot halves of an S3-quota run.
- **HUGR / Guppy / Selene**: Quantinuum's program representation for its Helios software stack (HUGR), the Python-embedded language that produces it (Guppy), and the emulator that runs it (Selene).
- **H2-1LE / pytket-pecos**: Quantinuum's local (offline) emulator target and the package that provides it; noiseless statevector in the runs here.
- **K4** *(project label, `prompts/33e`)*: the new `C2_KCHK` run-2 criterion that the laptop and the CI CPU references agree per representation.
- **Kraus channel / Kraus instruction**: the general form of a quantum noise channel, $\rho\to\sum_iK_i\rho K_i^\dagger$; Aer stores a channel as a "Kraus instruction" when it cannot write it as a mixture of unitaries and resets (here for thermal relaxation with $T_2>T_1$).
- **NAT-O0 / NAT-O2 / IR-L3-RZZ** *(project labels)*: circuit families: the Quantinuum-native circuits without optimisation, the native circuits after the exact qiskit level-1 rewrite, and the qiskit level-3 transpile of the IR in the RZZ basis (gate S3's family).
- **opt-3 source / structured source** *(project labels, `prompts/35b`)*: the two ways of producing 2x4 native circuits: via a qiskit optimisation-level-3 transpile of the IR, or directly from the exact structured IR through `ir_to_pytket`.
- **Part / slot `C4_PART_NN`** *(project labels)*: one GPU job of a split run; parts 2 and higher run on generic slots whose content is given by `ci/parts/C4_PART_NN.json` in the requested commit.
- **P15** *(project label)*: the S3-quota criterion evaluated at assembly: recall of $S_{999}\ge0.9$ and $E_0$ inside the Weinstein interval on the merged a + b halves ($2\times10^5$ shots per sector).
- **Q1 / Q1L / rounding bound $B$** *(project labels, `prompts/35a`, `35b`)*: Q1 = the native circuit's state equals the exact coarse state to $10^{-10}$; Q1L = the local proof that the conversion to native gates is exact (skeleton angles and single-qubit segments); $B$ = a rigorous bound on the state error caused by pytket's rounding of angles near multiples of 1/4 half-turn.
- **QSC / QN / QEMU / QH / QV** *(project gate prefixes, `prompts/35`)*: syntax-check sets (T5), noise-model tests (T2-T3), local emulator (T4), HUGR/Selene (T6), GPU statevector verification of 2x4.
- **S3 quota** *(project term)*: $2\times10^5$ shots per sector, the manual's Step 9.2 production budget and gate S3's recall condition.
- **S6** *(project criterion)*: "shots $\ge$ the token's minimum"; fails when a job took fewer shots than planned even if every physics criterion passed.
- **Saturation parameter $Na/\dim$** *(project quantity, rule C22)*: the expected number of accidental noise hits per sector state; above about 5 the sector fills from noise alone.
- **`status_reason`**: a field a gate writes when it fails by construction, stating why (e.g. `Q0P_2x4`).
- **Syntax checker**: a free Quantinuum service that compiles a job without running it (tier T5); needs an account.
