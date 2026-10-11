# 33b — Campaign 33, addendum 2: scenario-aware class-4 sizing, slot re-use, what runs before the 2026-10-21 maintenance

executor: executor-opus   effort: high
time budget: laptop code + tests about 1 executor day (0 QPU s, 0 HQC); Perlmutter: the request waves of section 5
(every job 1 GPU, <= 60 min, 4 at a time)
machine: laptop (code, dry runs, commit) + Perlmutter CI (every sampling job)
date: 2026-10-11   planner: Fable 5.1 (high)   prompt number: 33b (addendum to `prompts/33` and `prompts/33a`,
which stay in force for everything not re-ruled here)

Trigger: the executor's issue of commit ce154b4 (LOG row 2026-10-11): `prompts/33a` step D3 sizes every class-4
job at the one ladder rate C4_FCELLS_A measured on scenario E1, while the f-cells of the same job show E3/E4 at
about 2.8x and E5a/b/c at about 5.5x that cost per shot.  Planner arithmetic for every derived number below:
`scratch/planner/campaign33b_sizing_20261011.{py,json}` (inputs: `validation/C4_FCELLS_A.json` job 59570315
`data.cells.*.chunks` and `data.ladder.points`; `data/campaign33/sizing_33a.json` `runs`, `cv3`, `fit`, `budget`).
The resize script recomputes everything it uses (rule 1); the numbers here are for orientation and for the
pass criteria.

**Rule 1 is binding.  Rule 2:** no convention changes; nothing under `src/skqd/{su2,lattice,codec*,reference_sim,
circuits_ir}.py` is touched.  **No criterion constant, tolerance, shot plan, tier rule or scenario definition changes**
(the plan of record stays the plan of record: option (b), fewer shots for E3/E4/E5, is rejected in section 1).
**0 QPU s, 0 HQC.**  The executor's sampler fix (7d0af48) stays as it is.  Local commits; the coordinator pushes the
request commits (`prompts/33` 7e step 4).

**Code orientation (mandatory):** `graphify-out/graph.json` exists.  Use `graphify query "<question>"`,
`graphify explain "<symbol>"`, `graphify path "A" "B"`, `graphify affected "<symbol>"` BEFORE grepping or reading
files; grep only to edit specific lines; `graphify update .` after every code change.  Start with
`graphify explain "campaign33_resize.py"`, `graphify explain "split_run"`, `graphify explain "run_part"`,
`graphify explain "run_frun"`, `graphify explain "cv3_sample"`, `graphify explain "chunk_seed"`,
`graphify affected "Sampler.run"`, `graphify explain "assemble.py"`.

---

## 0. The rulings

**R1 — the executor's scenario factors are confirmed.**  Least-squares $t = c + b\,n$ over the recorded chunks of
every f-cell (`data.cells.<cell>.chunks[*].{shots,seconds}`, chunks of 12-400 shots) gives, relative to the
`E1|NAT-O0` slope $b = 0.02494$ s/shot: E2 1.008, E3 2.804, E4 2.839, E5a 5.506, E5b 5.511, E5c 5.486; on NAT-O1:
E1 0.888, E2 0.896, E3 2.750.  The executor's statistic ($r_{\rm eff}$ of the cell fit at chunk 1428 over the
ladder's 0.02572) gives 0.98 / 0.99 / 2.73 / 2.77 / 5.38 / 5.38 / 5.36 / 0.87 / 0.88 / 2.68 — the same picture.
The cell slope of E1 (0.02494) agrees with the ladder slope (0.02450) to 1.8 %, so the ladder and the cells
measure the same thing and the cells' intercepts (0.33-1.43 s per call) are smaller than the ladder's 1.74 s
only because the ladder points are single large calls.  The cost is structural: E3/E4 carry their angle-dependent
two-qubit error and the initialisation flip as per-instruction channels, E5 carries $20\times1925$ explicit
Pauli-$Z$ sites per circuit; none of it can be made cheaper without changing the scenario definition.

**R2 — scenario-aware rate (the sizing rule; replaces the single rate of 33a step D3).**  For scenario $s$,
$r_s = r_{\rm ladder}\times\rho_s$ with $r_{\rm ladder} = b + c/{\rm chunk}$ from the E1 ladder (as now) and
$\rho_s = \max_{\rm measured\ families}\,b_{s,{\rm fam}}/b_{E1,{\rm NAT\text{-}O0}}$ from the per-cell slope fits
of every f-cell JSON present (C4_FCELLS_A now; C4_FCELLS_B once harvested), $\rho_{E1}\ge1$.  Scenarios without a
cell: E6a/b/c and E7(f) use $\rho_{E1}$ and are labelled `assumed: E1 (same channel classes, other parameters)`
until C4_FCELLS_B's cells replace the label; E8 uses $\rho_{E1}$ labelled `upper bound: gate S3 measured
0.0199 s/shot at 476-shot calls on this family and model (validation/S3.json data.cost.seconds_per_shot_best_ladder)
against the E1 ladder's 0.0288 at 476` until C4_FCELLS_B's `s3_redo` timing (E8 on IR-L3-RZZ in this driver)
replaces it.  $N_{\max}(\text{kind}, s) = \text{share}\times(3000-120)/(1.25\,r_s)$, shares unchanged (0.6 plan,
0.75 quota / f-cells / cv3).  Resulting rates (s/shot): E1 0.02572, E2 0.02592, E3 0.07210, E4 0.07301, E5a 0.14158,
E5b 0.14171, E5c 0.14107.  Parts: **F3_B0 4, F3_B1 11, F6_B0 3, F6_B1 7**; every other run as in 33a (F1/F2/F7 B1,
F5_B1, F4 and F8 halves 2; F1/F2/F5/F7 B0 1).  Under the 33a sizing the first part of F3_B0 / F3_B1 / F6_B0 /
F6_B1 would have reached about 60 / 36 / 36 / 29 % of its shots ((N_max x r_ladder)/(part shots x r_s)) and
FAILed S6 — the runs are not requested on the 33a files.

**R3 — option (c) with (a) for the slots; option (b) is rejected.**  Fewer shots for E3/E4/E5 would turn
plan-of-record runs into runs that are not the plan of record: S6 ("the plan of record in full") fails by
definition, P14 (recall $\ge0.9$ where the plan was sized for the tier) cannot be read, and the CV1-CV5 readings
would be at an $N$ the plan was never sized for — the run's purpose is gone, not reduced.  The physics does not
allow it; the statistics does not help (the tier of F3 is 0.05 because the E3 f-cell's lower end is 0.0869 and
0.10 is above it: `plan_tiers.E3`).  So: **F3 and F6 keep their plans and are deferred** (section 2), and the slot
shortage is solved by **re-using slots** (R4) instead of asking the owner for 25 more allowlist lines — the 20
lines of `ci/allowed_jobs.campaign33a` are the only ones needed.

**R4 — slots are re-usable once the seed rule stops depending on the slot.**  Today a part on slot NN draws its
seeds from the slot's own token index (`seed_token_index`, criterion P0) with chunk index $j$ = the round index
*within the part* (`Sampler.run`: `T.chunk_seed(self.s0, circuit_offset + c, j, stride)`).  Two parts of one run on
the same slot would therefore sample identical shot streams — slot re-use is unsafe under the current rule, and
under the current rule the deferred work (33 F parts, 4 f-cell slots, the cv3 parts) needs more than 20 slots.
**New rule (33b):** every part of a run (part 1 on the F token included) uses $s_0$ of the run's **own F token**
(`tokens.base_seed(part["token"])`), the chunk index of the chunk in the **unsplit** chunk plan (global index), and
stride := the sizing's `chunk` — so the concatenation of the parts is seed-identical to the unsplit run, parts of
one run never share a stream whichever slot runs them, and different runs are disjoint by their F-token index as
before.  The cv3 content of a run uses the same $s_0$ with `circuit_offset` 100 / 200 (as the in-job path does), so
it is disjoint from the run's plan circuits.  P0 becomes "`seed_token_index` = the index of the run's own F token
and `slot` = this token".  A slot is **free** for a new content when `ci/status/<slot>.json` says `done` for its
current request **and** the content-named copy (`validation/C33_<run>_part<i>of<n>.json`, `..._cv3_part<i>of<n>`,
`C33_fcells_part<i>of<n>.json`) of its current content exists; the harvest overwrites `validation/C4_PART_NN.json`,
which assembly never reads (it reads the content-named copies: `assemble.py` L65).  "Never two pending requests on
the same slot" stays.

**R5 — the dropped f-cells by priority, packed by predicted cost.**  Cost of a cell = the measured seconds of the
scenario's most expensive measured cell (E1 58.4, E2 57.9, E3 151.8, E4 153.5, E5a 302.5, E5b 302.4, E5c 302.2 s per
2 000 shots); slot capacity $0.75\times2880/1.25 = 1728$ s of predicted sampling.  Priority: scenario E1, E2, E3,
E4, E5a, E5b, E5c, within a scenario O1, O2, O3, O4, O6; first fit in that order.  Result (planner arithmetic):
4 slots at 1687 / 1666 / 1512 / 1511 s; **slot A** = E1/E2/E3 x {O2, O3, O4, O6} + E4 x {O1, O2, O3, O4} (16 cells,
the P10 comparison at every scenario that has a different $f$) runs before the maintenance if the queue allows;
slots B-D (E4|O6 and E5a/b/c x all variants) after it, last — the E5 scenarios are statistically
indistinguishable from E1 at the f-cell level ($z$ of pooled $f_{\rm hit}$ against E1|O0: E5a 0.23, E5b 0.71,
E5c $-0.85$; E3 $-7.54$, E2 1.94, E4 1.29), so their variant cells carry the least information per GPU-second.
The 33a slot C4_PART_18 (all 32 cells in one job, about 6 400 s of predicted sampling against 1 728) is replaced.

**R6 — the six `not_evaluated` CV3 samples.**  Decision 2a's convergence condition is the gate `CV_2x3_plan`
(`validation/CV_2x3_plan.json`: PASS, CV3 PASS in all six (sector, $f$) cells); in campaign 33 CV1-CV5 are
information ("the plan-of-record check is CV_2x3_plan", `prompts/33` section 5, P13/P14).  `not_evaluated` therefore
changes no decision; it leaves the circuit-level CV3 reading absent for those runs.  Two of the six are worth a
slot: **F5_B1** (the like-for-like redo of CV_2x3_plan, whose comparison row in section 6 of `prompts/33` lists
CV3's $\Delta E_{4\to5}$: 124 500 shots at the E7 rate = 2 parts) and **F1_B1** (the reference scenario of class 4:
85 500 shots = 2 parts).  F3_B0 / F3_B1 / F6_B1 stay `not_evaluated` with the cost recorded (4 / 11 / 8 parts at
$r_{E3}$, $r_{E5b}$ — more GPU time than the runs themselves, for an information field); F2_B1 (2 parts) after
the maintenance if the owner wants it.  The `cv3` slot content therefore gains `part`/`parts` like `frun`
(same `split_ranges` on the equal-shots plan at the sizing's chunk; assembly merges the parts before reading
CV3).  F5_B0's CV3 is expected in-job (planner arithmetic: 44 000 extra shots at 0.02572 = 1 131 s against about
1 400 s left at the 0.75 share); if its JSON says `not_evaluated` for the budget, it gets one cv3 slot (44 000
shots fit one).

**R7 — what the queue allows before 2026-10-21 06:00 UTC.**  The one measured round trip (request commit
3a768f9 at 2026-10-08T20:25:33Z, harvest of the last of its four jobs 2026-10-09T21:07:28Z) is 24.7 h for 4
jobs at `MAX_CONCURRENT=4`; from 2026-10-12T00Z there are 222 h = 8.99 round trips = **32 jobs if the request
pipeline is never empty**.  The daily cap (24) does not bind.  Requests are therefore committed in **batches of 8**
(two poller rounds; the poller submits in file-name order while fewer than 4 are running), and the next batch is
committed as soon as one job of the previous batch has passed (`CLAUDE.md`: never more than 3 requests in a row
without a passing result).  The ranking of section 2 puts 24 jobs in the **must-run** set and 8 in **should-run**;
the rest **may slip** past the maintenance.  F3 (15 jobs), F6 (10), f-cell slots B-D (3), cv3 F2_B1 (2) and the
remaining cv3 are after the maintenance by this ruling, not by accident.

---

## 1. Scenario-aware sizing (the numbers the script must reproduce)

| run | scenario | shots | $r_s$ (s/shot) | $N_{\max}$ | parts 33a | **parts 33b** | 33a part 1 would reach |
|---|---|---|---|---|---|---|---|
| F1_B0 / F1_B1 | E1 | 27 309 / 67 600 | 0.02572 | 53 758 | 1 / 2 | 1 / 2 | full |
| F2_B0 / F2_B1 | E2 | 27 309 / 67 600 | 0.02592 | 53 334 | 1 / 2 | 1 / 2 | full |
| F3_B0 / F3_B1 | E3 | 63 875 / 193 600 | 0.07210 | 19 174 | 2 / 4 | **4 / 11** | 60 % / 36 % |
| F4 a/b, both sectors | E7(0.10) | 4 x 10^5 | 0.02572 | 67 197 | 2 each | 2 each | full |
| F5_B0 / F5_B1 | E7(0.07) | 34 909 / 99 000 | 0.02572 | 53 758 | 1 / 2 | 1 / 2 | full |
| F6_B0 / F6_B1 | E5b | 27 309 / 67 600 | 0.14171 | 9 754 | 1 / 2 | **3 / 7** | 36 % / 29 % |
| F7_B0 / F7_B1 | E1 x NAT-O2 | 27 309 / 67 600 | 0.02572 (NAT-O0's, the most expensive measured family) | 53 758 | 1 / 2 | 1 / 2 | full |
| F8 a/b, both sectors | E8 x IR-L3-RZZ | 4 x 10^5 | 0.02572 (upper bound, R2) | 67 197 | 2 each | 2 each | full |

Slots for parts $\ge2$: 33 in all (12 before the maintenance: F1_B1, F2_B1, F5_B1, F7_B1, F4 x 4, F8 x 4; 21 for
F3/F6 after it).  cv3: F5_B1 2 parts, F1_B1 2 parts (F2_B1 2, F3_B0 4, F3_B1 11, F6_B1 8 recorded, not scheduled).
f-cells: 4 slots (R5).  Generation 1 (the 20 slots as they exist) holds everything needed before the maintenance
plus F3_B0's three parts; generation 2 (re-used slots, R4) holds the rest.

## 2. Ranking of the remaining tokens (scientific value to the owner's request: four classes + every earlier 2x3 simulation redone)

Done: C1_IDEAL PASS, C3_AER PASS (classes 1 and 3), C4_FCELLS_A (10 of 42 cells; P11 PASS, tiers fixed).

| rank | token(s) | jobs | what it settles | set |
|---|---|---|---|---|
| 1 | `C4_FCELLS_B` | 1 | the faithful S3 redo (P12), the E6/E7 f-cells, the S2D declared-model comparison, the E8 and E7 rates for R2 | must |
| 2 | `C4_CF` | 1 | CF_traj redo, $r_{nc}$ (every $\hat f_{\rm ideal}$ of the campaign depends on it) | must |
| 3 | `C2_CAL` run 3 (sampler fix 7d0af48) | 1 | class 2 opens or is BLOCKED (third request: a failure is `prompts/BLOCKED_C33.md`, class 2 stops) | must |
| 4 | `C4_F5_B0`, `C4_F5_B1` + part 2 | 3 | the CV_2x3_plan / Q0P_2x3_plan P3 like-for-like redo (E7(0.07) at the 0.10 plan) | must |
| 5 | `C4_F1_B0`, `C4_F7_B0` | 2 | the class-4 reference scenario (H2-2 spec) and the chosen exact optimisation at $B=0$ (with in-job CV3) | must |
| 6 | `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH` | 4 | class 2: the model behind the K1 NO-GO (garbage structure vs the device) | must (if C2_CAL passes) |
| 7 | `C4_F4_B0a/b`, `C4_F4_B1a/b` + 4 parts | 8 | the S1 redo at the S3 quota with circuit-level noise (Table 4's $f=0.1$ row) | must |
| 8 | `C4_F8_B0a/b`, `C4_F8_B1a/b` + 4 parts | 8 | the gate-S3 criterion evaluated for the first time (P15) | should (first 4 must) |
| 9 | `C4_F1_B1` + part 2, `C4_F7_B1` + part 2 | 4 | the $B=1$ halves of rank 5 | should |
| 10 | `C2_XY4` | 1 | information cell (Markovian DD null) | may slip |
| 11 | `C4_F2_B0`, `C4_F2_B1` + part 2 | 3 | Helios spec ($z=1.94$ from E1 at the f-cell level) | may slip |
| 12 | f-cells slot A (16 cells, R5) | 1 | P10 at E1-E4 x exact variants | may slip |
| 13 | cv3 F5_B1 (2 parts), cv3 F1_B1 (2 parts) | 4 | CV3 under circuit noise for the redo row and the reference | may slip |
| 14 | `C4_F3_B0` + 3 parts, `C4_F3_B1` + 10 parts | 15 | the H2-2E emulator parameter set at the 0.05 plan | after maintenance |
| 15 | `C4_F6_B0` + 2 parts, `C4_F6_B1` + 6 parts | 10 | memory dephasing mid ($z=0.71$ from E1 at the f-cell level) | after maintenance, last |
| 16 | f-cell slots B-D, cv3 F2_B1 | 5 | E5 x variants, O6 information cells, CV3 of F2_B1 | after maintenance, last |
| — | `C3_LE`, `C3_SEL` | 0 | dropped / not requested per `data/campaign33/engines.json` | — |

Must = 24 jobs (ranks 1-7 and the first four of rank 8), should = 8, i.e. the 32 the queue allows at best.

## 3. Step A — the resize script and the seed rule (laptop, about 1 executor day)

1. `scripts/campaign33_resize.py`:
   (a) `scenario_rates(fcells_jsons, ladder_fit, chunk)` per R2: per-cell least-squares slopes over
   `data.cells.<cell>.chunks[*]` of every f-cell JSON that exists (`validation/C4_FCELLS_A.json`,
   `validation/C4_FCELLS_B.json`), the ratio rule, the `assumed` / `upper bound` labels, and — when C4_FCELLS_B is
   present — E8 from its `s3_redo` block (its recorded seconds and shots; name the JSON path in the output) and
   E6/E7 from its cells.  Written to `sizing_33a.json` as `scenario_rates: {s: {s_per_shot, rho, source, fit: {b, c,
   n_chunks, rms}, label}}` and `rate_rule`.
   (b) $N_{\max}$ per (kind, scenario); `split_run` per run at its own $N_{\max}$ (unchanged otherwise).
   (c) f-cells: `cell_cost_s` per scenario (R5), capacity $0.75\times(3000-120)/1.25$, first fit in the priority
   order of R5, every slot content listing `predicted_s`; the dropped cells of C4_FCELLS_B appended in the same
   order once that JSON exists.
   (d) cv3 with parts: `CV3_SLOTS = ("F5_B1", "F1_B1")` (R6; a module constant with the prompt reference), the
   equal-shots plan ($N_{\rm eq}$ per $k\le4$ circuit + the $k=5$ circuits, as `cv3_sample` builds it) split with
   `split_ranges` at the sizing's chunk into $\lceil{\rm shots}/N_{\max}({\rm fcells}, s)\rceil$ parts; the other
   runs recorded with `status: "not_evaluated: deferred by prompts/33b (n parts at r_s)"`, `shots`, `parts`.
   (e) the slot queue in this order: F5_B1 p2; F4_B0a p2, F4_B1a p2, F4_B0b p2, F4_B1b p2; F8_B0a p2, F8_B1a p2,
   F8_B0b p2, F8_B1b p2; F1_B1 p2, F7_B1 p2; F2_B1 p2; f-cells slot A; cv3 F5_B1 p1-2; cv3 F1_B1 p1-2; F3_B0 p2-4;
   then F3_B1 p2-11, F6_B0 p2-3, F6_B1 p2-7, f-cells B-D, cv3 F2_B1 p1-2.  Generation 1 = the first 20 on
   `C4_PART_01..20` in that order (`ci/parts/` files written); the rest `deferred` with `generation: 2` and no file.
   `--reassign`: a slot is free per R4 (read `ci/status/<slot>.json` and the content-named copy in `validation/`);
   free slots receive the next deferred items in queue order; the files of the previous content are overwritten;
   `sizing_33a.json` records `slot_history: {slot: [contents...]}`.  Exit 0 when nothing is unassigned *or*
   everything unassigned is `deferred`; exit 2 only on an item that is neither assigned nor deferred.
   (f) `sizing_33a.json` keeps its name and every 33a field (the driver's `load_sizing` reads it), adds `prompt:
   "prompts/33b"`, `scenario_rates`, `rate_rule`, `fcells.slots[*].predicted_s`, `cv3.*.parts`, `slot_queue`,
   `deferred`, `slot_history`, and `from` listing both f-cell JSONs with their job ids.
2. Seeds (R4): `Sampler.run` takes the global chunk index — `plans` entries become `(start, size, global_index)`
   (`chunk_plan` numbers its chunks; `part_plan` keeps the numbers) and `chunk_seed(s0, circuit_offset + c,
   global_index, stride)`; `stride` := the explicit `chunk` of the part descriptor when one is given (part 1 on the
   F token reads it from the sizing, as it already reads its ranges).  `run_frun` / `run_cv3_slot` build the
   sampler with `s0 = TK.base_seed(part["token"])`; the resize script writes `seed_token_index =
   TK.token_index(part["token"])`; `run_part`'s P0 compares against that and against `slot == ctx.token`.  The
   unsplit path (n = 1) is unchanged in effect: stride = the plan's largest chunk as now, indices global by
   construction.  `tokens.SEED_RULE` text and `ci/parts/README.md` updated (the README's "Seeds are disjoint by the
   slot's own token index" line is replaced by the R4 rule and the free-slot rule).
3. Assembly: `assemble.py` reads `C33_<run>_cv3_part<i>of<n>.json` (all parts present) for CV3, merging the
   equal-shots totals before `cv_reading`; a single-part cv3 keeps the name `C33_<run>_cv3.json`.
4. Done-checks (`tests/test_campaign33_parts.py`, extended; `tests/test_campaign33_seeds.py`, new):
   - a synthetic FCELLS_A with two scenarios whose chunk slopes are $b$ and $3b$ gives $\rho = 1, 3$, $N_{\max}$
     in the ratio 3 : 1 and parts 1 / 3 for the same shot count;
   - the real `validation/C4_FCELLS_A.json` reproduces section 1 (`runs.F3_B1.parts == 11`, `runs.F6_B1.parts == 7`,
     `runs.F3_B0.parts == 4`, `runs.F6_B0.parts == 3`, every other run's `parts` equal to 33a's);
   - f-cell packing: the real dropped list gives 4 slots whose first is the 16 cells of R5 and whose
     `predicted_s` are all $\le1728$;
   - seeds: for a run split into $n$ parts, the sorted list of (circuit, seed) over all parts equals the unsplit
     run's; two parts of one run never share a seed; two different runs never share a seed; the cv3 parts are
     disjoint from the plan circuits of the same run (`circuit_offset` 100 / 200);
   - `--reassign` refuses a slot whose `ci/status` is not `done` or whose content-named copy is missing (temp dir
     with stub files), and assigns the next deferred item to a free one, recording `slot_history`;
   - `test_dry_part_slot_and_assembly_if_run` extended to a cv3 content of 2 parts (dry sizes) merged by assembly.
5. Run the script on the real JSONs (`python scripts/campaign33_resize.py`), check the printed table against
   section 1, commit `data/campaign33/sizing_33a.json` + `ci/parts/C4_PART_01..20.json` + the code + tests; append
   the LOG row; `graphify update .`.  Also record in the LOG row (information, no code): the pooled $k=1$ hit totals
   of E2|O1 and E2|O0 (391 and 391), E3|O1 and E3|O0 (166 and 166) and E1|O1 and E4|O0 (373 and 373) coincide while
   their per-circuit hits, seeds and accepted counts differ (`data.cells.*.stats.per_circuit`); state the per-chunk
   hit counts of one such pair so the coincidence is on record as a coincidence.

## 4. Pass criteria (machine-checkable)

- `python scripts/check_package.py` PASS; `pytest -q tests` PASS on the laptop (pins unchanged) and
  `tests/test_campaign33_*.py` on the qiskit 1.4.3 twin.
- `data/campaign33/sizing_33a.json`: `prompt == "prompts/33b"`; `scenario_rates.E3.s_per_shot` within $10^{-6}$ of
  $0.02572\times2.804 = 0.07210$ and `scenario_rates.E5b.s_per_shot` of $0.14171$ (the script's own fit; the
  tolerance covers rounding of the orientation numbers only); `runs.{F3_B0,F3_B1,F6_B0,F6_B1}.parts == {4, 11, 3, 7}`;
  for every part of every run `shots x r_s x 1.25 <= share x 2880`; `fcells.slots` has 4 entries, the first with
  the 16 cells of R5; `cv3.F5_B1.parts == 2`, `cv3.F1_B1.parts == 2`, `cv3.F3_B1.status` starts with
  `not_evaluated: deferred`; `slots` has $\le20$ entries and `deferred` lists the rest with `generation: 2`.
- Every `ci/parts/C4_PART_NN.json` has `seed_token_index == token_index(token)` of the run it belongs to (f-cell
  slots: the slot's own index, as they have no run), `written_by`, `from` naming both f-cell JSONs.
- The seed tests of step A4 pass; `validation/dryrun/C4_PART_01.json` (dry part) and the dry assembly PASS their
  structural criteria.
- `git diff --stat` shows nothing under `src/skqd/{su2,lattice,codec*,reference_sim,circuits_ir}.py`.

## 5. The request waves (coordinator; `scripts/ci_request.sh` with all tokens of a batch in one commit)

| batch | wave | tokens (file-name order = submission order) | gate to open |
|---|---|---|---|
| 1 | 1 | `C4_FCELLS_B`, `C4_CF`, `C2_CAL`, `C4_F5_B0` | c33a merged and pushed (7d0af48 + this prompt's step A is not needed for these four) |
| 1 | 2 | `C4_F1_B0`, `C4_F7_B0`, `C4_F5_B1`, `C4_PART_01` (F5_B1 p2) | step A committed and pushed; the owner's 20 slot lines installed |
| 2 | 3 | `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH` — if `validation/C2_CAL.json` run 3 PASS with P4a decided; else this wave is wave 5's content and class 2 is BLOCKED | C2_CAL harvested |
| 2 | 4 | `C4_F4_B0a`, `C4_PART_02`, `C4_F4_B1a`, `C4_PART_03` | one PASS in batch 1 |
| 3 | 5 | `C4_F4_B0b`, `C4_PART_04`, `C4_F4_B1b`, `C4_PART_05` | one PASS in batch 2 |
| 3 | 6 | `C4_F8_B0a`, `C4_PART_06`, `C4_F8_B1a`, `C4_PART_07` | `C4_FCELLS_B` harvested and the resize re-run (E8 rate measured, dropped cells appended) — else swap with wave 8 |
| 4 | 7 | `C4_F8_B0b`, `C4_PART_08`, `C4_F8_B1b`, `C4_PART_09` | one PASS in batch 3 |
| 4 | 8 | `C4_F1_B1`, `C4_PART_10`, `C4_F7_B1`, `C4_PART_11` | same |
| 5 | 9 | `C2_XY4`, `C4_F2_B0`, `C4_F2_B1`, `C4_PART_12` | may slip |
| 5 | 10 | `C4_PART_13` (f-cells A), `C4_PART_14`, `C4_PART_15` (cv3 F5_B1), `C4_PART_16` (cv3 F1_B1 p1) | may slip |
| after 2026-10-28 | 11+ | `C4_PART_17` (cv3 F1_B1 p2), `C4_F3_B0` + `C4_PART_18..20`, then `--reassign` for F3_B1, F6, f-cells B-D, cv3 F2_B1 | owner's go for the deferred 30 jobs |

Rules: a part JSON with `full: false` → re-size that run's remaining parts with the script (never by hand), at most
2 re-requests per run, then `prompts/BLOCKED_C33.md`; `E_R < E_0 - 10^{-9}` or P11-type physics FAIL → STOP as in
`prompts/33` section 8; three CI failures in a row on one token → BLOCKED.  Check `scripts/ci_check.sh` at most
hourly; commit the next batch within the hour of the first PASS of the running one so the pipeline never idles.

## 6. What needs the owner

1. `cat $SCRATCH/su2qc-skqd/ci/allowed_jobs.campaign33a >> ~/skqd-ci/allowed_jobs` (the 20 `C4_PART_NN  01:00:00 1`
   lines already in the repo) — before wave 2.  **No further allowlist lines** (slots are re-used, R4).
2. Note for the record: F3 (15 jobs) and F6 (10 jobs) run after the maintenance (R3, R7); whether to spend them at
   all is the owner's call — the E5b f-cell is indistinguishable from E1's at 2 000 shots ($z=0.71$), the E3 one
   is not ($z=-7.54$), so F3 first if only one is run.
3. Note: the class-2 token `C2_CAL` is on its third request; a third failure blocks class 2 (`prompts/33a` 8).

## 7. Outputs

`scripts/campaign33_resize.py`, `src/skqd/campaign33/{sampling,tokens,tokens_run,assemble}.py`, `ci/parts/README.md`,
`ci/parts/C4_PART_01..20.json` (generation 1), `data/campaign33/sizing_33a.json` (33b fields), `tests/test_campaign33_
{parts,seeds}.py`, dry-run JSONs, LOG row, `graphify update .`.  Local commits; pushes only with the request commits.
