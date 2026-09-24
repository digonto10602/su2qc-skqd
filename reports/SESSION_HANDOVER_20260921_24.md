# Session handover — 21 to 24 September 2026

Written at the end of the session so that the next one (human or agent) can pick up without
re-reading 55 commits.  Everything described here is committed and pushed to
`origin/master`; nothing is left in a working tree.

**The one-sentence summary:** the project's performance predictions were missing idle-time
decoherence, the first real hardware run exposed it, a preregistered experiment confirmed it,
and amendment 01 items 1-3 are now signed with the corrected physics.

**Quantum machine time spent: 17.0 s of the 600 s monthly open-plan allowance (583 s left).**
Two jobs: the canary (2.0 s) and the H0_diag factorial (15.0 s).  Two GPU jobs on Perlmutter
(L4 and the S3 calibration) cost nothing from that allowance.

---

## 1. What was established, in order

### 1.1 The gate table moved

| gate | before | after | where |
|---|---|---|---|
| L4 | FAIL since 2026-09-14 | **PASS** on the GPU at full production shots | job 58741899 |
| S3 | open | **calibration PASS** (throughput only; the recall criterion is NOT evaluated) | job 58771538 |
| H0P | PASS on a snapshot | **PASS 18/18** twice on live calibration | `validation/H0P_ibm_fez.json` |
| H0 | open | **canary NO-GO**, main run held | `validation/H0_canary.json` |
| H0_diag | — | **FAIL 6/8**, but decisive on the question it was built for | `validation/H0_diag.json` |
| S2D (2x2 leg) | PASS | **withdrawn as a hardware statement** | `validation/S2D_idle.json` |

`validation/S2D.json`, `S2.json`, `H0_canary.json` and `H0_diag.json` are preregistered records
and were never rewritten.  Corrected analyses are new gates, never edits of old ones.

### 1.2 The physics finding

Neither prediction path knew how long a circuit takes.  `gate_S2D.analyse_on_backend` multiplies
gate and readout errors; `AerSimulator.from_backend` ran *unscheduled* circuits.  The frozen 2x2
canary circuit runs **43.71 us at depth 1328 for only 663 CZ** — nearly serial — so each of the 12
qubits idles 19-42 us.  Thermal relaxation over those windows is **3.323 error units** against the
**2.153** that were missing from the prediction.  Parameter-free, right size, absent from both paths.

The library form is `src/skqd/idle.py`; `scripts/h0_idle_model.py` is the CLI over it.

### 1.3 The correction to the correction

The re-plan then showed the *accepted* shots were mostly **near-clean** strings — a few errors, but
still decoding as valid codewords — not clean shots.  The canary circuit should give one specific
reference string ~88 % of the time; of J1's ~16 accepted shots above the garbage floor, ~15 should
have been that string.  **Two were.**  Pooled over all five hardware runs of that circuit: **6
reference hits in 8267 shots against 2.02 expected from garbage (P = 0.017)**, giving
**f_clean = 6.7e-4**.

Consequences, all recorded in `prompts/20`:
- the accepted-yield inversion **overstates the clean fraction 15x** on the device;
- "31 predicted vs 35 measured" was **not** a validation of the echo-T2 model.  The measured
  S_eff = 5.76 sits between the echo PTA's 3.32 and the T2* PTA's 7.52 — neither end is right;
- **criterion 3 (E0 to 1e-6) is void as a device test**: garbage saturation reaches it at every
  budget the project has ever planned.  It measures the decoder (gate E2), not the hardware.

### 1.4 The programme, stated without hedging

- **r = 1 only** at 2x2 on this device class.  r = 2 and r = 3 predict clean fractions ~5e-6 and
  ~2e-8: out of reach at any shot budget.
- Manual Step 9.1's yield-versus-CZ ladder **cannot be delivered**.
- Step 9.2's premise (f ~ 0.2 at <= 500 CZ) **never held** for these circuits on any quoted device.
- **2x3 on any superconducting device is dead.**  H1/H2 survive only conditional on an ion-trap
  specification that carries gate durations and in-circuit T2* under the vendor's own DD.

---

## 2. What is signed, and what is not

**Amendment 01 items 1, 2, 3 — SIGNED 2026-09-23** (commit `336a60b`).  The document is generated
by `scripts/make_amendment.py`; **edit the generator, never the .md**, and
`python scripts/make_amendment.py --check-only` must exit 0 (currently: 221 distinct cited values,
all verified).

- **Item 1** — the 2x2 patch is chosen by the idle-aware objective, not by the transpiler's
  calibration-aware layout.  The transpiler's patch is the *exact maximiser of gate+readout f* on
  every record tested: it was optimal for the wrong objective.  The winner swaps qubit 146
  (T2 16.0 us, 0.857 of 2.568 S_T2 units) for 140 (T2 36.0 us), worth 1.41x on the day's record and
  3.31x device-wide, one single winner across all seven records.  Stated in the document as
  **"a factor, not a rescue."**
- **Item 2** — f is read on the *scheduled* circuit; the 0.1 / 0.05 thresholds are **unchanged**.
  The T2 convention must be named wherever an f is quoted.  A device is assessable only if it
  declares **gate durations and T1/T2 alongside error rates**.  The document says plainly that
  signing fixes the bar and that the 2x2/Heron leg **fails** it (idle-aware mean f 6.71e-03).
- **Item 3** — the exact family is kept, judged on duration rather than gate count.  The
  fixed-angle generator is 2.2 % shallower in DAG depth yet **3.7 % longer in time** and loses
  1.34x in f.  Re-scheduling headroom is bounded at 7.03x and is **unattainable** (1 of 15 term
  pairs disjoint; changing it needs a new codeword layout, which re-opens E1-E3).

**Items 4 and 5 remain open.**  Item 4 now additionally needs the vendor's gate durations and
T1/T2.  Item 5's 556000 / 808104 shot figures exist only in a report, not in any JSON, so under
rule 1 they could not be cited into the amendment — they need a script and a JSON first.

**Nine named changes await a decision** — `prompts/20` section 8, listed as a sign/amend/reject
checklist: D8' (options off), D1' (re-freeze on the selected patch), D3'-f, D3''-H0, D5', C2',
C3', H0P-Y', M4.4.  None is applied; all are prepared behind default-preserving flags.
**D3''-H0 and C2' are the two that decide whether gate H0 is affordable at all** (~1900 s under the
current rule against 583 s left, versus ~143 s if H0 is sized for the clean-f statistic).

---

## 3. Infrastructure built this session

- `src/skqd/idle.py` — the idle-time model (ASAP schedule, per-window relaxation, `f_idle_aware`).
  The T2 convention is an argument of every call and a recorded field of every output.
- `src/skqd/hpc.py` — CI detection, Slurm layout, GPU telemetry; shared by L4 and S3.
- `scripts/h0_patch_select.py` — exhaustive embedding search scored by the idle-aware f.
- `scripts/h0_backends.py` — `calibration_fingerprint` and friends (rule D9, below).
- `scripts/h0_calwatch.py` — calibration watcher.  **Builds a fresh backend object per poll**:
  `IBMBackend.properties()` is cached per instance and will otherwise report a stale timestamp
  forever (this cost 71 minutes once).
- `scripts/gate_S2D_idle.py`, `scripts/gate_H0_diag.py`, `scripts/gate_S3.py`,
  `scripts/s2_duration_compare.py`, `scripts/h0_idle_model.py`.
- `circuits_qiskit.sample_many` — one `run([...])` call per batch with **memory-aware chunking**
  (`shot_chunk_for`) and adaptive halving on out-of-memory.

**Rule D9** (in `prompts/17`): submission requires identity of the calibration *content* of the
frozen patch — a fingerprint over the 30x9 qubit and 54x4 edge values the prediction reads — not
of the `last_update_date` string.  Three stamp changes overnight on 2026-09-22 changed **zero** of
those numbers; the timestamp guard was refusing work for nothing.  The fingerprint stayed quiet
through all three and fired on the one real recalibration.

---

## 4. Numbers worth not re-deriving

| quantity | value |
|---|---|
| canary circuit duration / depth / CZ | 43.71 us / 1328 / 663 |
| its idle budget | S_T1 0.755, S_T2 2.568, S_DD 0.317 |
| measured f_clean on patch 1 | 6.7e-4 (1 sigma 2.6e-4 – 1.1e-3) |
| coherence needed to meet f >= 0.1 | every T1 and T2 **5.5x longer** |
| GPU speed-up, 12 qubits (L4) | **19.8x** (0.00103 vs 0.02037 s/shot) |
| GPU speed-up, 20 qubits (S3) | **161x** (0.0199 vs 3.198 s/shot) |
| S3 sector cost | 178 h on the laptop -> **1.1 h** on one A100 |
| GPU utilisation (L4) | **15.3 %** — not GPU-bound; more GPUs would not help |
| `shot_chunk_for` model factor | underestimates real memory by **3.5x** (8.0 GB predicted, 27.9 measured) |
| shots per `run()` call | 122070 (12q, 1 circuit) → **476** (20q, 1 circuit) → **14** (20q, 32 circuits) |
| per-job billing floor | ~2-2.5 s regardless of shots — a session of many small jobs is job-count-dominated |

---

## 5. Environment facts that bite

- **Perlmutter runs qiskit 1.4.3 + qiskit-aer-gpu 0.15.1 + CUDA-Q 0.16; the laptop runs qiskit
  2.5.2 + aer 0.17.2.**  Anything the CI may execute must run on 1.4.3.  Keep gate modules free of
  qiskit imports at load time.
- **There is no usable local GPU**: aer-gpu 0.15.1 is incompatible with qiskit 2.5.2, and CUDA-Q's
  `nvidia` target refuses the GTX 1060 Max-Q (compute capability 6.1 < 7.0).
- The CI allowlist lives at `$CI/allowed_jobs` **on Perlmutter** and cannot be changed from this
  repository.  It now contains `S3 04:00:00 1` and `H0P 01:00:00 1` in addition to the originals.
- A CI request passes only a gate token: the job runs `python scripts/run_gate.py <GATE>` with no
  arguments, so a gate needing GPU behaviour must detect the CI itself (`CI_GATE` or
  `SLURM_JOB_ID`).
- Slurm does **not** reliably export `SLURM_GPUS_PER_TASK` to the step; fall back through
  `SLURM_GPUS_ON_NODE` and `CUDA_VISIBLE_DEVICES`.

---

## 6. Where to pick up

1. **Read** `CLAUDE.md`'s "Current status" paragraph (updated `c900462`) — it is the short version
   of everything above.
2. **Decide** the nine named changes in `prompts/20` section 8.  Start with **D3''-H0** and
   **C2'**: they determine whether H0 fits the remaining budget.
3. **Then** `prompts/21` (not yet written) is the pilot: ~10 s of QPU on the selected patch,
   measuring T2* and f_clean before the main run is sized.
4. **Open in parallel, needs nothing from the QPU:** amendment item 4 needs a vendor conversation
   (durations and T1/T2, not just error rates); item 5 needs a script and a JSON for its shot
   figures.
5. **S3 production** is now affordable on the GPU (4.4 h for four sectors) — but its recall
   criterion is not a hardware criterion until the idle term is in the model, so it should wait
   for the corrected model rather than be run for its own sake.

**Do not** run the main 6-job H0 submission.  It is held by the canary NO-GO under prompts/07
clause (b), and at the measured clean fraction it would spend ~70 s of QPU producing noise.

---

## 7. Honest record of mistakes made this session

Kept because they are cheaper to read than to rediscover.

- The assistant reported the corrected model as predicting the device "to 1.13x — remarkably good".
  That anchored on the accepted-shot count, which section 1.3 shows is the wrong statistic.  The
  honest answer is the bracket, and neither end of it.
- A batching change introduced by the assistant crashed the first GPU job (58737320) by requesting
  ~92 GB on an 80 GB card.  Fixed by `shot_chunk_for` plus adaptive halving; the next run needed
  no retries.
- The assistant repeated the amendment's own errata (2164 CZ quoted for 2x2; it is the 2x3 figure,
  2x2 is 256 all-to-all / 618 routed) when briefing an agent.  The agent caught it and checked the
  source.  Fixed in the generator, with a dated errata note in the document.
- A first count of clean shots accepted bit-strings in both orders and double-counted (9 instead of
  6).  Corrected against the declared convention.
- The assistant told an executor to preserve `validation/H0P_ibm_fez.json` when `prompts/16` B'4
  says that step overwrites it.  The executor followed the prompt file over the instruction and
  said so, which was right; the FAIL record survives at `51ac0e6`.
