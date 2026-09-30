# Superseded Aer draws — seeds 11, 12, 13, 14

These eight files are the first attempt at the C3 chunks of gate `H0_model` (prompts/20).
They were drawn at `seed_simulator` 11, 12, 13 and 14 on the assumption that consecutive
seeds give independent samples.  They do not: qiskit-aer 0.17.2 seeds the noise trajectory
of shot *j* with `seed_simulator + j`, so two 2000-shot runs whose seeds differ by 1 share
1999 of their 2000 shots.  All four chunks of each end therefore decoded to exactly the same
accepted count (115 and 33 of 2000) and the same reference-hit count (53 and 4), and the
"8000 shots per end" were in truth 2000 shots counted four times.

The mechanism was verified bit for bit: `200 shots at seed 11` + `200 shots at seed 211`
reproduces `400 shots at seed 11` with 0 differing keys, while `200 at seed 11` and
`200 at seed 12` differ in 2 keys.

The gate now uses `seed_simulator = seed + chunk * shots_per_chunk` (11, 2011, 4011, 6011),
which makes the four invocations exactly one 8000-shot run at seed 11.  These files are kept
only as the record of the error; nothing reads them.

## The counts themselves, decoded, before they were deleted

| end | chunk | seed_simulator | shots | accepted | reference hits |
|---|---|---|---|---|---|
| echo | 0 | 11 | 2000 | 115 | 53 |
| echo | 1 | 12 | 2000 | 115 | 53 |
| echo | 2 | 13 | 2000 | 115 | 53 |
| echo | 3 | 14 | 2000 | 115 | 53 |
| t2star | 0 | 11 | 2000 | 33 | 4 |
| t2star | 1 | 12 | 2000 | 33 | 4 |
| t2star | 2 | 13 | 2000 | 33 | 4 |
| t2star | 3 | 14 | 2000 | 33 | 4 |

The identical rows within each end are the whole point: four different `seed_simulator`
values, four essentially identical samples.  The count files were deleted after this table
was taken -- they are not measurements and nothing should read them -- while this note stays
as the record of the error and of how it was found.  The correct chunks are
`../aer_<end>_chunk<i>_seed<11 + 2000 i>_2000shots.json`.
