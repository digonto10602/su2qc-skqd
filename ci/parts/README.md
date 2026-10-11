# ci/parts — the content of the generic class-4 part slots (prompts/33a step D, prompts/33b step A)

The 20 tokens `C4_PART_01` … `C4_PART_20` (`scripts/gate_tokens.json`, 1 GPU, 01:00:00 each, env `skqd`,
allowlist lines in `ci/allowed_jobs.campaign33a`) run whatever `ci/parts/C4_PART_NN.json` says **in the requested
commit**.  A slot without a file fails honestly (`P0 slot content present`: FAIL); it never guesses.

## Who writes the files

Only `scripts/campaign33_resize.py`, from the measured ladder of `validation/C4_FCELLS_A.json`
(`data.ladder.points`) and the per-cell chunk timings of every f-cell JSON present (prompts/33b R2: a scenario's
rate is the ladder rate times the ratio of its cells' per-shot slope to E1|NAT-O0's).  Never edit a slot file or its
shot numbers by hand: re-run the script.  It writes `data/campaign33/sizing_33a.json` (every input named with its
JSON path) and one file per assigned slot, and it removes the slot files it wrote earlier that it no longer assigns.

- `python scripts/campaign33_resize.py` -- generation 1: the first 20 items of the slot queue on `C4_PART_01..20`;
  the rest is listed in `deferred` (generation 2, no file).  Refused once `slot_history` records a re-used slot.
- `python scripts/campaign33_resize.py --reassign` -- later generations: every **free** slot gets the next deferred
  item in queue order (its file is overwritten); busy slots keep their file; `slot_history` records every content
  a slot has held.

## Rules

- Never two pending requests on the same slot.
- Part 1 of a split run is run by the F token itself (`C4_F1_B1`, `C4_F4_B0a`, …): it reads `n` and its own
  per-circuit ranges from `data/campaign33/sizing_33a.json`.  Without that file an F token runs as prompts/33 sized
  it (n = 1) and says so in its notes.
- Seeds (prompts/33b R4): every part of a split run -- part 1 on its F token, parts >= 2 on any slot -- seeds
  from the run's **own F token** (`seed_token_index` = the F token's index; `slot` = the token that runs it; the job
  checks both, criterion P0), with the chunk index of the **unsplit** chunk plan and stride = the sizing's `chunk`.
  The parts therefore concatenate to the unsplit run seed for seed, two parts of one run never share a stream
  whichever slot runs them, and different runs stay disjoint by their F-token index.  A cv3 content uses the same
  s0 with circuit offsets 100 (k <= 4) / 200 (k = 5); an f-cell content (no run) the slot's own index with circuit
  offset 4 x the cell's global index (`cell_index_offset`).
- A slot is **free** for a new content when `ci/status/<slot>.json` says `done` for its current request **and** the
  content-named copy of its current content exists in `validation/`.  The harvest overwrites
  `validation/C4_PART_NN.json`, which the assembly never reads (it reads the content-named copies).
- A part JSON with `full: false`: re-size that run's remaining parts with the script, at most 2 re-requests per
  run, then `prompts/BLOCKED_C33.md` (prompts/33a section 8).

## Schema

```json
{"content": "frun" | "fcells" | "cv3",
 "slot": "C4_PART_NN", "seed_token_index": <index of the run's F token (frun, cv3) | the slot's own (fcells)>,
 "run": "F1_B1", "token": "C4_F1_B1", "scenario": "E1", "sector": "B1", "family": "NAT-O0", "kind": "plan",
 "tier": 0.15, "part": 2, "parts": 2, "chunk": 476,
 "plan_shots_by_circuit": {"B1_ref..._k1": 1537, ...},
 "ranges_by_circuit": {"B1_ref..._k1": [768, 1537], ...},
 "shots_by_circuit": {"B1_ref..._k1": 769, ...},
 "N_eq": 8300, "eq_ranges_by_circuit": {...}, "k5_ranges_by_circuit": {...}   (cv3, part i of n),
 "cells": [["E4", "NAT-O3"], ...], "group": "A", "label": "A", "cell_index_offset": 0, "predicted_s": 1686.7 (fcells),
 "written_by": "scripts/campaign33_resize.py", "from": "validation/C4_FCELLS_A.json job <id>"}
```

`ranges_by_circuit` are pieces of the **unsplit** chunk plan: the concatenated parts are exactly the unsplit run, so
every gate_CV prefix point is a chunk boundary.  The cut is the 33a rule (equal per-circuit fractions,
`skqd.campaign33.sampling.split_ranges`) when it fits every part's N_max, else the run's own call order cut into
windows of <= N_max shots (`round_major`; a circuit may then have an empty range in a part).  `split_method` in the
sizing JSON says which.

## Outputs of a slot job

- `validation/C4_PART_NN.json` and the content-named copy `validation/C33_<run>_part<i>of<n>.json`
  (`C33_<run>_cv3_part<i>of<n>.json`, or `C33_<run>_cv3.json` for a single-part cv3; `C33_fcells_part<i>of<n>.json`
  for C4_FCELLS_A's dropped cells, `C33_fcellsB_part<i>of<n>.json` for C4_FCELLS_B's);
  `results/campaign33/C33_<run>_part<i>/`.
- `<run>` is the F run name (`F1_B1`, `F4_B0a`): the scenario alone is ambiguous (F1 and F7 both run E1; the
  a / b halves share a scenario and a sector).
- `python scripts/campaign33.py --stage assemble` merges the parts of every run whose parts are all present into
  `validation/C33_<run>.json` (CV0-CV5, the certificate, recall, bootstrap, P13 / P14 / P15, `parts` listed); the cv3
  parts of a run are merged (equal-shots totals summed, ranges checked to tile N_eq) before CV3 is read.
