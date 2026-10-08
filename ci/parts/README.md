# ci/parts — the content of the generic class-4 part slots (prompts/33a step D)

The 20 tokens `C4_PART_01` … `C4_PART_20` (`scripts/gate_tokens.json`, 1 GPU, 01:00:00 each, env `skqd`,
allowlist lines in `ci/allowed_jobs.campaign33a`) run whatever `ci/parts/C4_PART_NN.json` says **in the requested
commit**.  A slot without a file fails honestly (`P0 slot content present`: FAIL); it never guesses.

## Who writes the files

Only `scripts/campaign33_resize.py`, from the measured ladder of `validation/C4_FCELLS_A.json`
(`data.ladder.points`).  Never edit a slot file or its shot numbers by hand: re-run the script.  It writes
`data/campaign33/sizing_33a.json` (every input named with its JSON path) and one file per assigned slot, and it
removes the slot files it wrote earlier that it no longer assigns.

## Rules

- Never two pending requests on the same slot.
- Part 1 of a split run is run by the F token itself (`C4_F1_B1`, `C4_F4_B0a`, …): it reads `n` and its own
  per-circuit ranges from `data/campaign33/sizing_33a.json`.  Without that file an F token runs as prompts/33 sized
  it (n = 1) and says so in its notes.
- Seeds are disjoint by the slot's own token index (`seed_token_index` must equal it; the job checks).
- A part JSON with `full: false`: re-size that run's remaining parts with the script, at most 2 re-requests per
  run, then `prompts/BLOCKED_C33.md` (prompts/33a section 8).

## Schema

```json
{"content": "frun" | "fcells" | "cv3",
 "slot": "C4_PART_NN", "seed_token_index": 33..52,
 "run": "F1_B1", "token": "C4_F1_B1", "scenario": "E1", "sector": "B1", "family": "NAT-O0", "kind": "plan",
 "tier": 0.15, "part": 2, "parts": 2, "chunk": 476,
 "plan_shots_by_circuit": {"B1_ref..._k1": 1537, ...},
 "ranges_by_circuit": {"B1_ref..._k1": [768, 1537], ...},
 "shots_by_circuit": {"B1_ref..._k1": 769, ...},
 "cells": [["E4", "NAT-O3"], ...],
 "written_by": "scripts/campaign33_resize.py", "from": "validation/C4_FCELLS_A.json job <id>"}
```

`ranges_by_circuit` are pieces of the **unsplit** chunk plan (`skqd.campaign33.sampling.split_ranges`): the
concatenated parts are exactly the unsplit run, so every gate_CV prefix point is a chunk boundary.

## Outputs of a slot job

- `validation/C4_PART_NN.json` and the content-named copy `validation/C33_<run>_part<i>of<n>.json`
  (`C33_<run>_cv3.json`, `C33_fcells_part<i>of<n>.json`); `results/campaign33/C33_<run>_part<i>/`.
- `<run>` is the F run name (`F1_B1`, `F4_B0a`): the scenario alone is ambiguous (F1 and F7 both run E1; the
  a / b halves share a scenario and a sector).
- `python scripts/campaign33.py --stage assemble` merges the parts of every run whose parts are all present into
  `validation/C33_<run>.json` (CV0-CV5, the certificate, recall, bootstrap, P13 / P14 / P15, `parts` listed).
