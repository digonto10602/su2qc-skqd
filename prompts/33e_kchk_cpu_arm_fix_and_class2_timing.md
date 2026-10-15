# 33e — Campaign 33, addendum 5: C2_KCHK run 2 (the CPU arm on the node's CPUs), the laptop CPU reference now, class 2 after the maintenance

executor: executor-opus   effort: high
time budget: laptop code about 2 h + background laptop sampling about 5 h (30-min chunks; 0 QPU s, 0 HQC);
Perlmutter: one 60-min job (`C2_KCHK` run 2)
machine: laptop (code, background CPU sampling in the 1.4.3 twin, commit) + Perlmutter CI
date: 2026-10-15   planner: Fable 5.1 (high)   prompt number: 33e (addendum to `prompts/33d`; 33d's rulings stand
except where re-ruled here)

Trigger: `validation/C2_KCHK.json` (job 59780907) FAIL 7/10: the GPU arms completed (IBM-T0 `B0_ref117_k1`, I-ECHO,
$\bar w$: `kraus_gpu_cusv` 3.00 $\pm$ 0.24 at 256 shots / 1.92 s per shot, `kraus_gpu_native` 3.57 $\pm$ 0.25 at
256 / 2.22, `kraus_gpu_cusv_nofusion` 1.14 $\pm$ 0.22 at 128 / 5.05, `rm_gpu_cusv` 7.43 $\pm$ 0.10 at 512 / 0.417;
raw counts stored, P0 PASS), the CPU arms drew 0 shots: the CPU process was started with **1 thread** (`cpu_process.
threads: 1`) and its first 16-shot chunk never finished (killed after the grace period, `returncode -9`), so K1, K2
are undecided and `production_representation = blocked`.  C2_KCHK's first failure.

**Rule 1 binding; no criterion, tolerance or convention changes; 0 QPU s.**

---

## 0. The rulings

**R1 — the cause of the 1 thread, and the fix.**  `kchk_cpu.cpu_threads` reads `os.sched_getaffinity(0)` (right:
a Slurm binding must be respected); the step was bound to **one CPU** because `jobs/gate.sbatch` line 52 runs
`srun python scripts/run_gate.py "$CI_GATE"` without `--cpus-per-task`, and Slurm (since 22.05) no longer lets a
job step inherit the batch allocation's `--cpus-per-task` (the allocation had `cpus_per_task: 32`; the step got 1).
The exported `OMP_NUM_THREADS=32` has therefore been oversubscribing one core in every CI job's CPU phase (speed,
not correctness: the decoding / Ritz / bootstrap phases of the F runs were slower than they needed to be; no number
changes).  Fix (one line, in the repo's `jobs/gate.sbatch`, which every job takes from the requested commit — no
owner action): `srun --cpus-per-task="${SLURM_CPUS_PER_TASK:-1}" python scripts/run_gate.py "$CI_GATE"`, and the
driver records `run.cpu_affinity = len(os.sched_getaffinity(0))` in every token JSON from now on (S3 gains the field;
on the CI it must equal `SLURM_CPUS_PER_TASK`, else S3 FAILs — a stronger check, not a loosening).  Stacking fix
for the CPU arm itself: `--chunk 1` (every completed shot is recorded; a chunk is never lost to the deadline),
`--min-shots 8`, threads = affinity minus 4 as now (28 on the node).

**R2 — run 2 is CPU-only on the GPU node; no CPU token.**  The CI submits GPU jobs only (one GPU, shared QOS; a
CPU-QOS token would need a poller and sbatch change on the owner's side, not before the maintenance).  The GPU
arms of run 1 are evidence of record (raw counts, seeds, P0 PASS) and are **not repeated**: run 1's JSON is archived
byte-identically as `validation/archive/C2_KCHK_job59780907.json` (sha256 in run 2, as C2_CAL run 1 was), and run 2
(`--content cpu_only`, `calibration_run: 2`, `supersedes` pointing at the archive) runs the CPU process alone for the
whole window (0.9 of the remaining budget, about 2 700 s) with `rm_gpu_cusv` repeated at **128 shots first** (53 s;
a same-job anchor that the GPU side is unchanged — information).  K1-K3 are evaluated on run 1's GPU arms and run
2's CPU arms.  Expected CPU yield (planner arithmetic from the laptop's 174 / 84 s per shot on 12 threads of 6
cores; the node's 28 threads of an EPYC 7763 are taken as 3x): about 40 Kraus + 80 RM shots when alternated 1 : 2
(two RM shots per Kraus shot, since RM is the production candidate and the clbit 1/2 flag of 33d R1 is on RM),
i.e. $\bar w$ to $\pm0.4$ (Kraus) and $\pm0.3$ (RM).  Enough for K1 (3.0 vs 7.4 is $z\approx10$) and for K2's weight
test; the marginal tests are weak at that count and the JSON states the power, as 33d R3 requires.  If the node
rate turns out below 1 Kraus shot per 100 s, the minimum of 8 still decides K1.

**R3 — the laptop runs the CPU reference now, as evidence of record.**  The twin venv
(`~/.local/share/su2qc-qiskit143`: qiskit 1.4.3, aer 0.15.1, numpy 2.5.3 — the CI's versions) and
`scripts/c33c_diag_full.py` exist; the 19 + 24 shots of 33c are too few for K2.  Background chunks under the
30-minute rule: Kraus first, `--rep kraus --shots-per-call 2 --max-seconds 1700` repeated until the pooled Kraus
arm has $\ge64$ shots (about 3.2 h at 174 s per shot; $\bar w\pm0.30$), then RM to $\ge64$ (about 1.5 h at 84 s per
shot).  Every segment is a committed JSON under `data/campaign33/c33c_diag/` (as the existing segments), merged by
`--summarize` into `summary.json` with the GPU arms of **both** C2_CAL run 3 and C2_KCHK run 1 (the script gains
`--gpu-source validation/archive/C2_KCHK_job59780907.json`).  Use of the laptop numbers: (a) the preregistered
expectation of run 2's CPU arms (same software versions; the CPU statevector code is the same source, the wheel is
not: `qiskit-aer-gpu` on the CI, `qiskit-aer` on the laptop — said in the JSON); (b) a **cross-check criterion** in
run 2, **K4**: the two CPU references agree, $|z_w|\le3$ per representation — if they disagree, STOP (planner): the
reference itself would be in question; (c) K1 and K2 are read on the CI CPU arms (33d, unchanged) — the laptop
alone decides nothing of record, but it tells us by tonight which way run 2 will go.

**R4 — class 2 goes after the maintenance, with one exception.**  Timeline: fix + laptop launch today (2026-10-15);
run 2 requested today, harvested about 2026-10-16/17 at the measured 25-h round trip; `C2_XY4` could be requested
on 10-17 and would be queued when the reservation `maintenance_20261021` starts.  Rule: **`C2_XY4` is requested as
soon as run 2 says `production_representation: rm`** (it runs whenever the queue runs it; nothing is lost if that is
after 10-28), and `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH` are after the maintenance as 33d said.  If run 2 says
`blocked` (RM disagrees with its own CPU reference), class 2 is `prompts/BLOCKED_C33.md` and the owner decides
between the native-GPU Kraus engine at 2.2 s per shot (only if K3 validates it — it did not against run 1's other
GPU arms, see R5) and dropping class 2.  The F batches keep the queue full meanwhile (the coordinator's requests of
`C4_F2_B0`, `C4_F2_B1`, `C4_PART_12..17` stand).

**R5 — the native result sharpens the upstream case; it does not weaken it.**  The three GPU Kraus executions of
the same channel disagree **with each other**: `kraus_gpu_cusv_nofusion` 1.14 $\pm$ 0.22 against `kraus_gpu_cusv`
3.00 $\pm$ 0.24 is $z = 5.7$, and the native kernels give 3.57 $\pm$ 0.25 ($z = 1.6$ from cuStateVec, $z = 7.3$ from
no-fusion).  A correct simulator's output distribution is invariant under fusion on/off and under the choice of
kernel; three mutually inconsistent results from one channel are evidence of a defect in the GPU Kraus path of
aer 0.15.1 **that needs no CPU reference at all**, and it is not cuStateVec-specific.  All three are far below RM's
7.43 and the laptop's CPU Kraus 7.47 $\pm$ 0.56, in the direction of excess relaxation (as if the damping operator
were drawn with too high a probability — a normalisation of the Kraus sampling is the natural suspect; the
executor does not speculate in the report, it attaches the numbers).  The upstream report (33d R4, owner files
it) therefore carries two parts: the GPU-vs-GPU inconsistency (available now, raw counts in run 1) and GPU vs CPU
(after run 2).  Only the "laptop 19-shot outlier" alternative of the coordinator's note is still formally open,
and it is closed by R3 tonight and R2 formally.

## 1. Executor steps (laptop, about 2 h of code; then the background sampling of R3)

1. `jobs/gate.sbatch`: the `--cpus-per-task` line of R1; `tokens_run` / `campaign33.py`: `run.cpu_affinity` in every
   JSON and the S3 clause (`== SLURM_CPUS_PER_TASK` on the CI).  Test: `tests/test_ci_gpu_mode.py` gains a check that
   the sbatch's `srun` line carries `--cpus-per-task`.
2. `C2_KCHK` run 2 per R2: `--content cpu_only`, archive of run 1 (byte-identical; sha256 recorded), the 128-shot RM
   anchor, CPU process `--chunk 1 --min-shots 8`, RM : Kraus = 2 : 1 alternation, K1-K3 on the archived GPU arms,
   **K4** per R3 (laptop JSON path recorded; the laptop arms are read from `data/campaign33/c33c_diag/summary.json`
   at run time if present in the commit, else K4 is `not_evaluated` and says so).  Dry run on the laptop.
3. Launch R3's laptop sampling in the background in the twin venv (Kraus segments first), each segment $\le$ 1 700 s,
   committing each finished segment; `--summarize` after each; stop at 64 + 64 shots or at the planner's STOP if a
   segment shows a $\bar w$ outside 7.47 $\pm$ 3 $\times$ 0.56 at $\ge$ 32 shots (then say so, do not pool silently).
4. `pytest -q tests` (laptop) and the campaign33 tests on the twin; `graphify update .`; LOG row (with the laptop
   segment table: shots, $\bar w\pm$ se per representation, s per shot); commit; the coordinator pushes and requests.

## 2. Pass criteria

- `validation/C2_KCHK.json` run 2 (CI): `calibration_run: 2`, `supersedes.sha256` equal to the archive's;
  `run.cpu_affinity == 32`; `kraus_cpu.shots_done >= 8`, `rm_cpu.shots_done >= 8`, raw counts stored (P0); K1 decided
  (`bug_confirmed` true or false); K2 decided (`rm` or `blocked`); K4 evaluated when the laptop summary is in the
  commit; `status: PASS` iff S1-S6 and P0 hold (K1/K2 are decisions, both outcomes PASS the token).
- `data/campaign33/c33c_diag/summary.json`: Kraus $\ge64$ and RM $\ge64$ laptop shots, per-segment provenance (git
  commit, versions, seeds, s per shot), the comparisons against both GPU sources.
- `git diff --stat` shows nothing under `src/skqd/{su2,lattice,codec*,reference_sim,circuits_ir}.py`.

## 3. Requests (coordinator)

| when | tokens |
|---|---|
| step 1-2 merged and pushed (today) | `C2_KCHK` (run 2; the allowlist line already exists) |
| run 2 harvested with `production_representation: rm` | `C2_XY4` — immediately, whatever the date |
| `blocked` | none; `prompts/BLOCKED_C33.md`; owner decision (R4) |
| after the maintenance | `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH` on the decided representation |

## 4. What needs the owner

1. Nothing before run 2 (the sbatch fix is in the repo snapshot; the `C2_KCHK` line is installed).
2. After run 2: the qiskit-aer issue of 33d R4, now with the GPU-vs-GPU inconsistency of R5 as its first exhibit.
3. If run 2 says `blocked`: class 2 on the native-GPU Kraus engine (2.2 s per shot, about 1 000 shots per cell)
   only if K3 validates it, else drop class 2 — owner's call.
