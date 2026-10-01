# Gate S2_2x4 — the 2x4 coarse step compiled, verified, and its device requirement

**Status: FAIL** — `scripts/gate_S2_2x4.py`, optimization level 3,
basis {rz, sx, x, cz}, seed 7, g2 = 4.0.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit fb58a82, 2026-09-30 18:33:37 MDT.  Assemble runtime 198 s.
**0 QPU seconds.**  Every number below comes from `validation/S2_2x4.json`, which this script wrote
from the stage fragments in `data/S2_2x4/`.

## What PASS means

compiled, verified and measured.  PASS is NOT a statement that any device can run these circuits: this gate carries no criterion on any count, duration or coherence requirement, and the manual's Step 4.3 budget has no 2x4 line.

The owner asked what a device must deliver to run 2x3 and 2x4.  At 2x3 the answer existed
(`data/S2D_2x3_device_requirements.json`); at 2x4 it did not, because the circuits had never been
compiled and the "above 1e5" figure was an extrapolation from two points.  This gate compiles them,
verifies them at the gate-S2 standard and measures the requirement.  It does not say whether any
device meets it.

## The gating question: does the structured engine reach 2x4?

Yes, with no code change to the construction.  `plaq1`, the middle plaquette, acts on
16 qubits (four interior corners,
1831 local codewords,
811 blocks, the largest with
9 configurations of degree
8), and `hop3`/`hop5` are an
interior-to-interior x-link type that does not exist at 2x3.  Every block of every term has a zero
diagonal (`diag_nonzero` false throughout), which is the premise of the bipartite singular-value
construction of `circuits_ir._block_rounds`; the diagonal gauge of `_real_gauge` made every block
generator real, so every rotation is an Ry.  Terms that needed the generic `expm` fallback of
`_block_rounds`: **none**.  Terms without a real gauge:
**none**.  The 16-qubit support decides cost and synthesis
time, not correctness: the dense local unitary of a 16-qubit support is 2^32 complex entries (68 GB)
and was never built — term verification uses the small block `h` of `reference_sim.localize` and
`circuits_ir.run_ir` on the 2^16 local statevector (1 MB).

## Per-term cost and verification at 2x4 (exact, theta = dt), with the fixed-angle column beside it

| term | support | local states | blocks | largest block | IR gates | cx | multiplexed rotations | controls min/med/max | fixed-angle cx | synthesis (s) | max deviation | leakage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hop0 | 9 | 78 | 40 | 4 | 536 | 278 | 9 | 3/5/6 | 272 | 4.3 | 2.395e-15 | 1.421e-14 |
| hop1 | 6 | 18 | 10 | 3 | 94 | 54 | 5 | 2/2/3 | 52 | 4.4 | 1.639e-15 | 5.662e-15 |
| hop2 | 10 | 156 | 80 | 4 | 484 | 258 | 9 | 3/5/5 | 280 | 3.6 | 1.591e-15 | 1.388e-14 |
| hop3 | 11 | 340 | 160 | 6 | 3000 | 1548 | 22 | 5/6/7 | 536 | 7.2 | 2.657e-15 | 3.197e-14 |
| hop4 | 8 | 85 | 47 | 4 | 746 | 390 | 9 | 3/5/6 | 272 | 5.6 | 4.066e-15 | 2.509e-14 |
| hop5 | 11 | 340 | 188 | 4 | 1040 | 542 | 9 | 4/5/7 | 536 | 5.1 | 1.268e-15 | 1.721e-14 |
| hop6 | 10 | 156 | 80 | 4 | 486 | 260 | 9 | 3/5/5 | 280 | 4.2 | 1.832e-15 | 1.354e-14 |
| hop7 | 8 | 85 | 47 | 4 | 746 | 390 | 9 | 3/5/6 | 272 | 4.5 | 3.849e-15 | 2.520e-14 |
| hop8 | 9 | 78 | 46 | 3 | 478 | 244 | 5 | 4/6/6 | 272 | 4.2 | 2.040e-15 | 1.243e-14 |
| hop9 | 6 | 18 | 10 | 3 | 90 | 54 | 5 | 2/2/3 | 52 | 4.2 | 1.737e-15 | 5.995e-15 |
| plaq0 | 14 | 383 | 194 | 3 | 430 | 228 | 4 | 5/5/6 | 286 | 3.1 | 4.605e-16 | 3.109e-15 |
| plaq1 | 16 | 1831 | 811 | 9 | 132554 | 66468 | 82 | 7/9/11 | 12952 | 1.8e+02 | 2.431e-14 | 6.517e-14 |
| plaq2 | 14 | 383 | 162 | 5 | 1546 | 806 | 17 | 4/5/7 | 484 | 8.4 | 1.783e-15 | 1.776e-15 |

Sum of the IR `cx` over the 13 hop/plaquette terms:
**71520** exact,
16546 fixed-angle (the diagonal term adds a few tens
and the transpiler then merges across term boundaries, so the coarse-step count below is not
this sum).

### The same table at 2x3, for scale

| term | support | local states | blocks | largest block | IR gates | cx | multiplexed rotations | max deviation |
|---|---|---|---|---|---|---|---|---|
| hop0 | 9 | 78 | 40 | 4 | 536 | 278 | 9 | 7.402e-16 |
| hop1 | 6 | 18 | 10 | 3 | 94 | 54 | 5 | 1.333e-15 |
| hop2 | 10 | 156 | 80 | 4 | 484 | 258 | 9 | 7.219e-16 |
| hop3 | 10 | 156 | 80 | 4 | 486 | 260 | 9 | 4.518e-16 |
| hop4 | 8 | 85 | 47 | 4 | 746 | 390 | 9 | 8.632e-16 |
| hop5 | 9 | 78 | 46 | 3 | 478 | 244 | 5 | 8.921e-16 |
| hop6 | 6 | 18 | 10 | 3 | 90 | 54 | 5 | 1.610e-15 |
| plaq0 | 14 | 383 | 194 | 3 | 430 | 228 | 4 | 3.470e-16 |
| plaq1 | 14 | 383 | 162 | 5 | 1546 | 806 | 17 | 2.803e-15 |

Sum of the IR `cx` over the 9 2x3 hop/plaquette terms:
2572.

## Coarse-step counts per coupling map

| lattice | family | circuit | map | IR gates | 2q gates | 1q gates | depth | CZ depth | mapped qubits | active qubits | transpile (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2x2 | exact | B0_ref0_k1 | all_to_all | 524 | 256 | 920 | 736 | 202 | 12 | 12 | 1.4 |
| 2x2 | exact | B0_ref0_k1 | all_to_all + measure layer | 524 | 256 | 920 | 737 | 202 | 12 | 12 | 0.031 |
| 2x2 | exact | B0_ref0_k1 | heavy_hex_3 | 524 | 618 | 2023 | 1294 | 426 | 19 | 13 | 0.067 |
| 2x2 | exact | B0_ref0_k1 | heavy_hex_3 + measure layer | 524 | 618 | 2023 | 1295 | 426 | 19 | 13 | 0.054 |
| 2x3 | exact | B0_ref0_k1 | all_to_all | 4930 | 2164 | 6754 | 7325 | 1926 | 20 | 20 | 1.5 |
| 2x3 | exact | B0_ref0_k1 | all_to_all + measure layer | 4930 | 2164 | 6754 | 7326 | 1926 | 20 | 20 | 0.13 |
| 2x3 | exact | B0_ref0_k1 | fakefez | 4930 | 5737 | 17218 | 11084 | 3749 | 156 | 25 | 0.87 |
| 2x3 | exact | B0_ref0_k1 | fakefez + measure layer | 4930 | 5737 | 17218 | 11085 | 3749 | 156 | 25 | 0.94 |
| 2x3 | exact | B0_ref0_k1 | heavy_hex_5 | 4930 | 5477 | 17465 | 11540 | 3692 | 57 | 26 | 0.4 |
| 2x3 | exact | B0_ref0_k1 | heavy_hex_5 + measure layer | 4930 | 5477 | 17465 | 11541 | 3692 | 57 | 26 | 0.39 |
| 2x4 | exact | B0_ref0_k1 | all_to_all | 142288 | 69688 | 209395 | 272923 | 68653 | 28 | 28 | 72 |
| 2x4 | exact | B0_ref0_k1 | all_to_all + measure layer | 142288 | 69688 | 209395 | 272924 | 68653 | 28 | 28 | 72 |
| 2x4 | exact | B0_ref0_k1 | fakefez | 142288 | 148726 | 501985 | 375535 | 108053 | 156 | 28 | 22 |
| 2x4 | exact | B0_ref0_k1 | fakefez + measure layer | 142288 | 148726 | 501985 | 375536 | 108053 | 156 | 28 | 21 |
| 2x4 | exact | B0_ref0_k1 | fakefez_backend + measure layer | 142288 | 148726 | 497456 | 377173 | 108053 | 156 | 28 | 25 |
| 2x4 | exact | B0_ref0_k1 | heavy_hex_5 | 142288 | 144902 | 501689 | 383183 | 107798 | 57 | 43 | 27 |
| 2x4 | exact | B0_ref0_k1 | heavy_hex_5 + measure layer | 142288 | 145958 | 498289 | 377509 | 108091 | 57 | 29 | 24 |
| 2x4 | exact | B0_ref0_k1 | heavy_hex_7 | 142288 | 151164 | 498001 | 369518 | 111751 | 115 | 30 | 25 |
| 2x4 | exact | B0_ref0_k1 | heavy_hex_7 + measure layer | 142288 | 148850 | 493084 | 368548 | 108634 | 115 | 28 | 21 |
| 2x4 | exact | B0_ref0_k4 | all_to_all | 142288 | 69688 | 209437 | 272911 | 68653 | 28 | 28 | 89 |
| 2x4 | exact | B0_ref0_k4 | all_to_all + measure layer | 142288 | 69688 | 209437 | 272912 | 68653 | 28 | 28 | 93 |
| 2x4 | exact | B0_ref0_k4 | fakefez | 142288 | 148726 | 501987 | 375529 | 108053 | 156 | 28 | 27 |
| 2x4 | exact | B0_ref0_k4 | fakefez + measure layer | 142288 | 148726 | 501987 | 375530 | 108053 | 156 | 28 | 34 |
| 2x4 | exact | B0_ref0_k4 | fakefez_backend + measure layer | 142288 | 148726 | 497372 | 377075 | 108053 | 156 | 28 | 28 |
| 2x4 | exact | B0_ref0_k4 | heavy_hex_5 | 142288 | 144902 | 501559 | 383090 | 107798 | 57 | 43 | 19 |
| 2x4 | exact | B0_ref0_k4 | heavy_hex_5 + measure layer | 142288 | 145958 | 498140 | 377471 | 108091 | 57 | 29 | 19 |
| 2x4 | exact | B0_ref0_k4 | heavy_hex_7 | 142288 | 151164 | 497704 | 369301 | 111751 | 115 | 30 | 21 |
| 2x4 | exact | B0_ref0_k4 | heavy_hex_7 + measure layer | 142288 | 148850 | 492604 | 368325 | 108634 | 115 | 28 | 25 |
| 2x4 | exact | B0_ref1_k1 | all_to_all | 142289 | 69688 | 209397 | 272922 | 68653 | 28 | 28 | 88 |
| 2x4 | exact | B0_ref1_k1 | all_to_all + measure layer | 142289 | 69688 | 209397 | 272923 | 68653 | 28 | 28 | 1.1e+02 |
| 2x4 | exact | B0_ref1_k1 | fakefez | 142289 | 148726 | 501984 | 375535 | 108053 | 156 | 28 | 30 |
| 2x4 | exact | B0_ref1_k1 | fakefez + measure layer | 142289 | 148726 | 501984 | 375536 | 108053 | 156 | 28 | 29 |
| 2x4 | exact | B0_ref1_k1 | fakefez_backend + measure layer | 142289 | 148726 | 497459 | 377173 | 108053 | 156 | 28 | 25 |
| 2x4 | exact | B0_ref1_k1 | heavy_hex_5 | 142289 | 144902 | 501687 | 383180 | 107798 | 57 | 43 | 26 |
| 2x4 | exact | B0_ref1_k1 | heavy_hex_5 + measure layer | 142289 | 145958 | 498293 | 377510 | 108091 | 57 | 29 | 27 |
| 2x4 | exact | B0_ref1_k1 | heavy_hex_7 | 142289 | 151164 | 498002 | 369518 | 111751 | 115 | 30 | 23 |
| 2x4 | exact | B0_ref1_k1 | heavy_hex_7 + measure layer | 142289 | 148850 | 493089 | 368549 | 108634 | 115 | 28 | 27 |
| 2x4 | exact | B1_ref0_k1 | all_to_all | 142289 | 69688 | 209374 | 272931 | 68653 | 28 | 28 | 74 |
| 2x4 | exact | B1_ref0_k1 | all_to_all + measure layer | 142289 | 69688 | 209374 | 272932 | 68653 | 28 | 28 | 84 |
| 2x4 | exact | B1_ref0_k1 | fakefez | 142289 | 148726 | 502113 | 375615 | 108053 | 156 | 28 | 28 |
| 2x4 | exact | B1_ref0_k1 | fakefez + measure layer | 142289 | 148726 | 502113 | 375616 | 108053 | 156 | 28 | 30 |
| 2x4 | exact | B1_ref0_k1 | fakefez_backend + measure layer | 142289 | 148726 | 497603 | 377170 | 108053 | 156 | 28 | 25 |
| 2x4 | exact | B1_ref0_k1 | heavy_hex_5 | 142289 | 144902 | 501852 | 383314 | 107798 | 57 | 43 | 24 |
| 2x4 | exact | B1_ref0_k1 | heavy_hex_5 + measure layer | 142289 | 145958 | 498428 | 377600 | 108091 | 57 | 29 | 23 |
| 2x4 | exact | B1_ref0_k1 | heavy_hex_7 | 142289 | 151164 | 498272 | 369639 | 111751 | 115 | 30 | 26 |
| 2x4 | exact | B1_ref0_k1 | heavy_hex_7 + measure layer | 142289 | 148850 | 493375 | 368703 | 108634 | 115 | 28 | 26 |
| 2x4 | fixed | B0_ref0_k1 | all_to_all | 32802 | 14048 | 41888 | 53800 | 13656 | 28 | 28 | 27 |
| 2x4 | fixed | B0_ref0_k1 | all_to_all + measure layer | 32802 | 14048 | 41888 | 53801 | 13656 | 28 | 28 | 25 |
| 2x4 | fixed | B0_ref0_k1 | fakefez | 32802 | 28765 | 89637 | 67126 | 19484 | 156 | 31 | 6.5 |
| 2x4 | fixed | B0_ref0_k1 | fakefez + measure layer | 32802 | 28765 | 89637 | 67127 | 19484 | 156 | 31 | 6.7 |
| 2x4 | fixed | B0_ref0_k1 | heavy_hex_5 | 32802 | 30208 | 91134 | 65715 | 21216 | 57 | 30 | 5.3 |
| 2x4 | fixed | B0_ref0_k1 | heavy_hex_5 + measure layer | 32802 | 30208 | 91134 | 65716 | 21216 | 57 | 30 | 6.1 |
| 2x4 | fixed | B0_ref0_k1 | heavy_hex_7 | 32802 | 28925 | 91077 | 68372 | 19649 | 115 | 30 | 5.9 |
| 2x4 | fixed | B0_ref0_k1 | heavy_hex_7 + measure layer | 32802 | 28925 | 91077 | 68373 | 19649 | 115 | 30 | 5.8 |
| 2x4 | fixed | B0_ref0_k4 | all_to_all | 32802 | 14048 | 41903 | 53801 | 13656 | 28 | 28 | 31 |
| 2x4 | fixed | B0_ref0_k4 | all_to_all + measure layer | 32802 | 14048 | 41903 | 53802 | 13656 | 28 | 28 | 31 |
| 2x4 | fixed | B0_ref0_k4 | fakefez | 32802 | 28765 | 88814 | 66226 | 19484 | 156 | 31 | 8.4 |
| 2x4 | fixed | B0_ref0_k4 | fakefez + measure layer | 32802 | 28765 | 88814 | 66227 | 19484 | 156 | 31 | 6 |
| 2x4 | fixed | B0_ref0_k4 | heavy_hex_5 | 32802 | 30208 | 89859 | 65147 | 21216 | 57 | 30 | 5.8 |
| 2x4 | fixed | B0_ref0_k4 | heavy_hex_5 + measure layer | 32802 | 30208 | 89859 | 65148 | 21216 | 57 | 30 | 5.7 |
| 2x4 | fixed | B0_ref0_k4 | heavy_hex_7 | 32802 | 28925 | 90625 | 67618 | 19649 | 115 | 30 | 5.7 |
| 2x4 | fixed | B0_ref0_k4 | heavy_hex_7 + measure layer | 32802 | 28925 | 90625 | 67619 | 19649 | 115 | 30 | 5.8 |
| 2x4 | fixed | B0_ref1_k1 | all_to_all | 32803 | 14048 | 41887 | 53799 | 13656 | 28 | 28 | 35 |
| 2x4 | fixed | B0_ref1_k1 | all_to_all + measure layer | 32803 | 14048 | 41887 | 53800 | 13656 | 28 | 28 | 26 |
| 2x4 | fixed | B0_ref1_k1 | fakefez | 32803 | 28765 | 89641 | 67125 | 19484 | 156 | 31 | 6.8 |
| 2x4 | fixed | B0_ref1_k1 | fakefez + measure layer | 32803 | 28765 | 89641 | 67126 | 19484 | 156 | 31 | 6.4 |
| 2x4 | fixed | B0_ref1_k1 | heavy_hex_5 | 32803 | 30208 | 91134 | 65715 | 21216 | 57 | 30 | 5.5 |
| 2x4 | fixed | B0_ref1_k1 | heavy_hex_5 + measure layer | 32803 | 30208 | 91134 | 65716 | 21216 | 57 | 30 | 5.3 |
| 2x4 | fixed | B0_ref1_k1 | heavy_hex_7 | 32803 | 28925 | 91079 | 68373 | 19649 | 115 | 30 | 5.5 |
| 2x4 | fixed | B0_ref1_k1 | heavy_hex_7 + measure layer | 32803 | 28925 | 91079 | 68374 | 19649 | 115 | 30 | 6.1 |
| 2x4 | fixed | B1_ref0_k1 | all_to_all | 32803 | 14048 | 41873 | 53815 | 13656 | 28 | 28 | 28 |
| 2x4 | fixed | B1_ref0_k1 | all_to_all + measure layer | 32803 | 14048 | 41873 | 53816 | 13656 | 28 | 28 | 25 |
| 2x4 | fixed | B1_ref0_k1 | fakefez | 32803 | 28765 | 90188 | 67280 | 19484 | 156 | 31 | 6.2 |
| 2x4 | fixed | B1_ref0_k1 | fakefez + measure layer | 32803 | 28765 | 90188 | 67281 | 19484 | 156 | 31 | 5.6 |
| 2x4 | fixed | B1_ref0_k1 | heavy_hex_5 | 32803 | 30208 | 91632 | 65872 | 21216 | 57 | 30 | 5.7 |
| 2x4 | fixed | B1_ref0_k1 | heavy_hex_5 + measure layer | 32803 | 30208 | 91632 | 65873 | 21216 | 57 | 30 | 6.2 |
| 2x4 | fixed | B1_ref0_k1 | heavy_hex_7 | 32803 | 28925 | 91770 | 68492 | 19649 | 115 | 30 | 5.7 |
| 2x4 | fixed | B1_ref0_k1 | heavy_hex_7 + measure layer | 32803 | 28925 | 91770 | 68493 | 19649 | 115 | 30 | 5.9 |

Structure identity (does the transpiled count depend on the reference or on k?):
`{"compile_2_exact|all_to_all": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_2_exact|heavy_hex_3": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_3_exact|all_to_all": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_3_exact|heavy_hex_5": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_3_exact|fakefez": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_a2a_k1|all_to_all": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_fezbackend|fakefez_backend": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_perterm|all_to_all": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_perterm|heavy_hex_5": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_perterm|heavy_hex_7": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_perterm|fakefez": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_rest|all_to_all": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_rest|heavy_hex_5": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_rest|heavy_hex_7": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_rest|fakefez": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_routed_k1|heavy_hex_5": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_routed_k1|heavy_hex_7": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_exact_routed_k1|fakefez": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_fixed|all_to_all": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_fixed|heavy_hex_5": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_fixed|heavy_hex_7": {"identical_across_references_at_k1": true, "identical_across_all": true}, "compile_4_fixed|fakefez": {"identical_across_references_at_k1": true, "identical_across_all": true}}`

Like-for-like with gate S2 (the same circuit, transpiler settings and map must give back the
committed counts at 2x2 and 2x3):
`{"compile_2_exact": {"all_to_all": {"committed": 256, "recomputed": 256, "match": true, "source": "validation/S2.json data.2x2.coarse_step.all_to_all.cz"}, "heavy_hex_3": {"committed": 618, "recomputed": 618, "match": true, "source": "validation/S2.json data.2x2.coarse_step.routed.cz"}}, "compile_3_exact": {"all_to_all": {"committed": 2164, "recomputed": 2164, "match": true, "source": "validation/S2.json data.2x3.coarse_step.all_to_all.cz"}, "heavy_hex_5": {"committed": 5477, "recomputed": 5477, "match": true, "source": "validation/S2.json data.2x3.coarse_step.routed.cz"}}}`

## Duration, idle budget and the coherence requirement

Schedules are ASAP (`skqd.idle.schedule_asap`) on a **uniform** record
(`skqd.coherence.uniform_record`) at the Heron r2 durations of
`data/hardware/H0_diag_prep/calibration_20260922T1400Z.json` (cz 68 ns, sx and x 24 ns, measure
1.66 us, dt 4 ns), and again with t_1q = 0, which is the serial formula's premise.  `T2_req` is
solved by bisection so that the idle budget of `skqd.idle` equals ln(1/f_target) exactly.

| circuit | t_1q | f_target | T1 convention | 2q gates | T (s) | seriality | qubit-time utilisation | total idle (s) | idle windows | T2/t_2q measured | T2/t_2q serial (active qubits) | T2/t_2q serial (logical qubits) | measured / formula |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2x2 / exact / B0_ref0_k1 / all_to_all | heron | 0.1 | inf | 256 | 2.122e-05 | 1.22 | 0.188 | 2.069e-04 | 249 | 625.1 | 667.1 | 667.1 | 0.937 |
| 2x2 / exact / B0_ref0_k1 / all_to_all | heron | 0.1 | equal | 256 | 2.122e-05 | 1.22 | 0.188 | 2.069e-04 | 249 | 955.3 | 667.1 | 667.1 | 1.43 |
| 2x2 / exact / B0_ref0_k1 / all_to_all | heron | 0.05 | inf | 256 | 2.122e-05 | 1.22 | 0.188 | 2.069e-04 | 249 | 472.4 | 512.7 | 512.7 | 0.921 |
| 2x2 / exact / B0_ref0_k1 / all_to_all | heron | 0.05 | equal | 256 | 2.122e-05 | 1.22 | 0.188 | 2.069e-04 | 249 | 726.1 | 512.7 | 512.7 | 1.42 |
| 2x2 / exact / B0_ref0_k1 / all_to_all | zero | 0.1 | inf | 256 | 1.374e-05 | 0.789 | 0.211 | 1.300e-04 | 237 | 391.5 | 667.1 | 667.1 | 0.587 |
| 2x2 / exact / B0_ref0_k1 / all_to_all | zero | 0.1 | equal | 256 | 1.374e-05 | 0.789 | 0.211 | 1.300e-04 | 237 | 599 | 667.1 | 667.1 | 0.898 |
| 2x2 / exact / B0_ref0_k1 / all_to_all | zero | 0.05 | inf | 256 | 1.374e-05 | 0.789 | 0.211 | 1.300e-04 | 237 | 295.5 | 512.7 | 512.7 | 0.576 |
| 2x2 / exact / B0_ref0_k1 / all_to_all | zero | 0.05 | equal | 256 | 1.374e-05 | 0.789 | 0.211 | 1.300e-04 | 237 | 455 | 512.7 | 512.7 | 0.887 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | heron | 0.1 | inf | 618 | 4.124e-05 | 0.981 | 0.216 | 4.203e-04 | 356 | 1277 | 1745 | 1610 | 0.732 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | heron | 0.1 | equal | 618 | 4.124e-05 | 0.981 | 0.216 | 4.203e-04 | 356 | 1946 | 1745 | 1610 | 1.12 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | heron | 0.05 | inf | 618 | 4.124e-05 | 0.981 | 0.216 | 4.203e-04 | 356 | 967.2 | 1341 | 1238 | 0.721 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | heron | 0.05 | equal | 618 | 4.124e-05 | 0.981 | 0.216 | 4.203e-04 | 356 | 1481 | 1341 | 1238 | 1.1 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | zero | 0.1 | inf | 618 | 2.897e-05 | 0.689 | 0.223 | 2.925e-04 | 344 | 887.9 | 1745 | 1610 | 0.509 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | zero | 0.1 | equal | 618 | 2.897e-05 | 0.689 | 0.223 | 2.925e-04 | 344 | 1354 | 1745 | 1610 | 0.776 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | zero | 0.05 | inf | 618 | 2.897e-05 | 0.689 | 0.223 | 2.925e-04 | 344 | 672.5 | 1341 | 1238 | 0.501 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | zero | 0.05 | equal | 618 | 2.897e-05 | 0.689 | 0.223 | 2.925e-04 | 344 | 1030 | 1341 | 1238 | 0.768 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | heron | 0.1 | inf | 2164 | 2.138e-04 | 1.45 | 0.0929 | 0.00388 | 2153 | 1.2e+04 | 9398 | 9398 | 1.28 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | heron | 0.1 | equal | 2164 | 2.138e-04 | 1.45 | 0.0929 | 0.00388 | 2153 | 1.819e+04 | 9398 | 9398 | 1.94 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | heron | 0.05 | inf | 2164 | 2.138e-04 | 1.45 | 0.0929 | 0.00388 | 2153 | 9135 | 7224 | 7224 | 1.26 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | heron | 0.05 | equal | 2164 | 2.138e-04 | 1.45 | 0.0929 | 0.00388 | 2153 | 1.389e+04 | 7224 | 7224 | 1.92 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | zero | 0.1 | inf | 2164 | 1.310e-04 | 0.89 | 0.112 | 0.00233 | 2118 | 7182 | 9398 | 9398 | 0.764 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | zero | 0.1 | equal | 2164 | 1.310e-04 | 0.89 | 0.112 | 0.00233 | 2118 | 1.089e+04 | 9398 | 9398 | 1.16 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | zero | 0.05 | inf | 2164 | 1.310e-04 | 0.89 | 0.112 | 0.00233 | 2118 | 5465 | 7224 | 7224 | 0.757 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | zero | 0.05 | equal | 2164 | 1.310e-04 | 0.89 | 0.112 | 0.00233 | 2118 | 8317 | 7224 | 7224 | 1.15 |
| 2x3 / exact / B0_ref0_k1 / fakefez | heron | 0.1 | inf | 5737 | 3.644e-04 | 0.934 | 0.118 | 0.00804 | 3203 | 2.25e+04 | 3.114e+04 | 2.492e+04 | 0.722 |
| 2x3 / exact / B0_ref0_k1 / fakefez | heron | 0.1 | equal | 5737 | 3.644e-04 | 0.934 | 0.118 | 0.00804 | 3203 | 3.403e+04 | 3.114e+04 | 2.492e+04 | 1.09 |
| 2x3 / exact / B0_ref0_k1 / fakefez | heron | 0.05 | inf | 5737 | 3.644e-04 | 0.934 | 0.118 | 0.00804 | 3203 | 1.716e+04 | 2.394e+04 | 1.915e+04 | 0.717 |
| 2x3 / exact / B0_ref0_k1 / fakefez | heron | 0.05 | equal | 5737 | 3.644e-04 | 0.934 | 0.118 | 0.00804 | 3203 | 2.603e+04 | 2.394e+04 | 1.915e+04 | 1.09 |
| 2x3 / exact / B0_ref0_k1 / fakefez | zero | 0.1 | inf | 5737 | 2.549e-04 | 0.653 | 0.122 | 0.00559 | 3128 | 1.565e+04 | 3.114e+04 | 2.492e+04 | 0.502 |
| 2x3 / exact / B0_ref0_k1 / fakefez | zero | 0.1 | equal | 5737 | 2.549e-04 | 0.653 | 0.122 | 0.00559 | 3128 | 2.367e+04 | 3.114e+04 | 2.492e+04 | 0.76 |
| 2x3 / exact / B0_ref0_k1 / fakefez | zero | 0.05 | inf | 5737 | 2.549e-04 | 0.653 | 0.122 | 0.00559 | 3128 | 1.193e+04 | 2.394e+04 | 1.915e+04 | 0.499 |
| 2x3 / exact / B0_ref0_k1 / fakefez | zero | 0.05 | equal | 5737 | 2.549e-04 | 0.653 | 0.122 | 0.00559 | 3128 | 1.81e+04 | 2.394e+04 | 1.915e+04 | 0.756 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | heron | 0.1 | inf | 5477 | 3.638e-04 | 0.977 | 0.109 | 0.00843 | 3088 | 2.153e+04 | 3.092e+04 | 2.379e+04 | 0.696 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | heron | 0.1 | equal | 5477 | 3.638e-04 | 0.977 | 0.109 | 0.00843 | 3088 | 3.259e+04 | 3.092e+04 | 2.379e+04 | 1.05 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | heron | 0.05 | inf | 5477 | 3.638e-04 | 0.977 | 0.109 | 0.00843 | 3088 | 1.641e+04 | 2.377e+04 | 1.828e+04 | 0.69 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | heron | 0.05 | equal | 5477 | 3.638e-04 | 0.977 | 0.109 | 0.00843 | 3088 | 2.491e+04 | 2.377e+04 | 1.828e+04 | 1.05 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | zero | 0.1 | inf | 5477 | 2.511e-04 | 0.674 | 0.114 | 0.00578 | 3012 | 1.477e+04 | 3.092e+04 | 2.379e+04 | 0.478 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | zero | 0.1 | equal | 5477 | 2.511e-04 | 0.674 | 0.114 | 0.00578 | 3012 | 2.237e+04 | 3.092e+04 | 2.379e+04 | 0.723 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | zero | 0.05 | inf | 5477 | 2.511e-04 | 0.674 | 0.114 | 0.00578 | 3012 | 1.126e+04 | 2.377e+04 | 1.828e+04 | 0.474 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | zero | 0.05 | equal | 5477 | 2.511e-04 | 0.674 | 0.114 | 0.00578 | 3012 | 1.71e+04 | 2.377e+04 | 1.828e+04 | 0.719 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | heron | 0.1 | inf | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69670 | 6.3874e+05 | 4.2371e+05 | 4.2371e+05 | 1.51 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | heron | 0.1 | equal | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69670 | 9.7229e+05 | 4.2371e+05 | 4.2371e+05 | 2.29 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | heron | 0.05 | inf | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69670 | 4.8445e+05 | 3.2567e+05 | 3.2567e+05 | 1.49 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | heron | 0.05 | equal | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69670 | 7.4075e+05 | 3.2567e+05 | 3.2567e+05 | 2.27 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | zero | 0.1 | inf | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 3.7008e+05 | 4.2371e+05 | 4.2371e+05 | 0.873 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | zero | 0.1 | equal | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 5.6360e+05 | 4.2371e+05 | 4.2371e+05 | 1.33 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | zero | 0.05 | inf | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 2.8057e+05 | 3.2567e+05 | 3.2567e+05 | 0.861 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | zero | 0.05 | equal | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 4.2927e+05 | 3.2567e+05 | 3.2567e+05 | 1.32 |
| 2x4 / exact / B0_ref0_k1 / fakefez | heron | 0.1 | inf | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 8.5853e+05 | 9.0427e+05 | 9.0427e+05 | 0.949 |
| 2x4 / exact / B0_ref0_k1 / fakefez | heron | 0.1 | equal | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 1.3050e+06 | 9.0427e+05 | 9.0427e+05 | 1.44 |
| 2x4 / exact / B0_ref0_k1 / fakefez | heron | 0.05 | inf | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 6.5201e+05 | 6.9504e+05 | 6.9504e+05 | 0.938 |
| 2x4 / exact / B0_ref0_k1 / fakefez | heron | 0.05 | equal | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 9.9507e+05 | 6.9504e+05 | 6.9504e+05 | 1.43 |
| 2x4 / exact / B0_ref0_k1 / fakefez | zero | 0.1 | inf | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 5.6915e+05 | 9.0427e+05 | 9.0427e+05 | 0.629 |
| 2x4 / exact / B0_ref0_k1 / fakefez | zero | 0.1 | equal | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 8.6522e+05 | 9.0427e+05 | 9.0427e+05 | 0.957 |
| 2x4 / exact / B0_ref0_k1 / fakefez | zero | 0.05 | inf | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 4.3219e+05 | 6.9504e+05 | 6.9504e+05 | 0.622 |
| 2x4 / exact / B0_ref0_k1 / fakefez | zero | 0.05 | equal | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 6.5969e+05 | 6.9504e+05 | 6.9504e+05 | 0.949 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | heron | 0.1 | inf | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89855 | 8.7354e+05 | 9.1914e+05 | 8.8744e+05 | 0.95 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | heron | 0.1 | equal | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89855 | 1.3232e+06 | 9.1914e+05 | 8.8744e+05 | 1.44 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | heron | 0.05 | inf | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89855 | 6.6552e+05 | 7.0647e+05 | 6.8211e+05 | 0.942 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | heron | 0.05 | equal | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89855 | 1.0111e+06 | 7.0647e+05 | 6.8211e+05 | 1.43 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | zero | 0.1 | inf | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 5.7741e+05 | 9.1914e+05 | 8.8744e+05 | 0.628 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | zero | 0.1 | equal | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 8.7471e+05 | 9.1914e+05 | 8.8744e+05 | 0.952 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | zero | 0.05 | inf | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 4.3987e+05 | 7.0647e+05 | 6.8211e+05 | 0.623 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | zero | 0.05 | equal | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 6.6833e+05 | 7.0647e+05 | 6.8211e+05 | 0.946 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | heron | 0.1 | inf | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91505 | 8.6139e+05 | 9.0503e+05 | 9.0503e+05 | 0.952 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | heron | 0.1 | equal | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91505 | 1.3087e+06 | 9.0503e+05 | 9.0503e+05 | 1.45 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | heron | 0.05 | inf | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91505 | 6.5447e+05 | 6.9562e+05 | 6.9562e+05 | 0.941 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | heron | 0.05 | equal | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91505 | 9.9819e+05 | 6.9562e+05 | 6.9562e+05 | 1.43 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | zero | 0.1 | inf | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 5.7340e+05 | 9.0503e+05 | 9.0503e+05 | 0.634 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | zero | 0.1 | equal | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 8.7124e+05 | 9.0503e+05 | 9.0503e+05 | 0.963 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | zero | 0.05 | inf | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 4.3562e+05 | 6.9562e+05 | 6.9562e+05 | 0.626 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | zero | 0.05 | equal | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 6.6449e+05 | 6.9562e+05 | 6.9562e+05 | 0.955 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | heron | 0.1 | inf | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69668 | 6.3874e+05 | 4.2371e+05 | 4.2371e+05 | 1.51 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | heron | 0.1 | equal | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69668 | 9.7229e+05 | 4.2371e+05 | 4.2371e+05 | 2.29 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | heron | 0.05 | inf | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69668 | 4.8444e+05 | 3.2567e+05 | 3.2567e+05 | 1.49 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | heron | 0.05 | equal | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69668 | 7.4075e+05 | 3.2567e+05 | 3.2567e+05 | 2.27 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | zero | 0.1 | inf | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 3.7008e+05 | 4.2371e+05 | 4.2371e+05 | 0.873 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | zero | 0.1 | equal | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 5.6360e+05 | 4.2371e+05 | 4.2371e+05 | 1.33 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | zero | 0.05 | inf | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 2.8057e+05 | 3.2567e+05 | 3.2567e+05 | 0.861 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | zero | 0.05 | equal | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 4.2927e+05 | 3.2567e+05 | 3.2567e+05 | 1.32 |
| 2x4 / exact / B0_ref0_k4 / fakefez | heron | 0.1 | inf | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 8.5862e+05 | 9.0427e+05 | 9.0427e+05 | 0.95 |
| 2x4 / exact / B0_ref0_k4 / fakefez | heron | 0.1 | equal | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 1.3051e+06 | 9.0427e+05 | 9.0427e+05 | 1.44 |
| 2x4 / exact / B0_ref0_k4 / fakefez | heron | 0.05 | inf | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 6.5208e+05 | 6.9504e+05 | 6.9504e+05 | 0.938 |
| 2x4 / exact / B0_ref0_k4 / fakefez | heron | 0.05 | equal | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 9.9518e+05 | 6.9504e+05 | 6.9504e+05 | 1.43 |
| 2x4 / exact / B0_ref0_k4 / fakefez | zero | 0.1 | inf | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 5.6915e+05 | 9.0427e+05 | 9.0427e+05 | 0.629 |
| 2x4 / exact / B0_ref0_k4 / fakefez | zero | 0.1 | equal | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 8.6522e+05 | 9.0427e+05 | 9.0427e+05 | 0.957 |
| 2x4 / exact / B0_ref0_k4 / fakefez | zero | 0.05 | inf | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 4.3219e+05 | 6.9504e+05 | 6.9504e+05 | 0.622 |
| 2x4 / exact / B0_ref0_k4 / fakefez | zero | 0.05 | equal | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 6.5969e+05 | 6.9504e+05 | 6.9504e+05 | 0.949 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | heron | 0.1 | inf | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89859 | 8.7376e+05 | 9.1914e+05 | 8.8744e+05 | 0.951 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | heron | 0.1 | equal | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89859 | 1.3235e+06 | 9.1914e+05 | 8.8744e+05 | 1.44 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | heron | 0.05 | inf | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89859 | 6.6570e+05 | 7.0647e+05 | 6.8211e+05 | 0.942 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | heron | 0.05 | equal | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89859 | 1.0113e+06 | 7.0647e+05 | 6.8211e+05 | 1.43 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | zero | 0.1 | inf | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 5.7741e+05 | 9.1914e+05 | 8.8744e+05 | 0.628 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | zero | 0.1 | equal | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 8.7471e+05 | 9.1914e+05 | 8.8744e+05 | 0.952 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | zero | 0.05 | inf | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 4.3987e+05 | 7.0647e+05 | 6.8211e+05 | 0.623 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | zero | 0.05 | equal | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 6.6833e+05 | 7.0647e+05 | 6.8211e+05 | 0.946 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | heron | 0.1 | inf | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91504 | 8.6145e+05 | 9.0503e+05 | 9.0503e+05 | 0.952 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | heron | 0.1 | equal | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91504 | 1.3088e+06 | 9.0503e+05 | 9.0503e+05 | 1.45 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | heron | 0.05 | inf | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91504 | 6.5452e+05 | 6.9562e+05 | 6.9562e+05 | 0.941 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | heron | 0.05 | equal | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91504 | 9.9826e+05 | 6.9562e+05 | 6.9562e+05 | 1.44 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | zero | 0.1 | inf | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 5.7340e+05 | 9.0503e+05 | 9.0503e+05 | 0.634 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | zero | 0.1 | equal | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 8.7124e+05 | 9.0503e+05 | 9.0503e+05 | 0.963 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | zero | 0.05 | inf | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 4.3562e+05 | 6.9562e+05 | 6.9562e+05 | 0.626 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | zero | 0.05 | equal | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 6.6449e+05 | 6.9562e+05 | 6.9562e+05 | 0.955 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | heron | 0.1 | inf | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69669 | 6.3874e+05 | 4.2371e+05 | 4.2371e+05 | 1.51 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | heron | 0.1 | equal | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69669 | 9.7229e+05 | 4.2371e+05 | 4.2371e+05 | 2.29 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | heron | 0.05 | inf | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69669 | 4.8445e+05 | 3.2567e+05 | 3.2567e+05 | 1.49 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | heron | 0.05 | equal | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69669 | 7.4075e+05 | 3.2567e+05 | 3.2567e+05 | 2.27 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | zero | 0.1 | inf | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 3.7008e+05 | 4.2371e+05 | 4.2371e+05 | 0.873 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | zero | 0.1 | equal | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 5.6360e+05 | 4.2371e+05 | 4.2371e+05 | 1.33 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | zero | 0.05 | inf | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 2.8057e+05 | 3.2567e+05 | 3.2567e+05 | 0.861 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | zero | 0.05 | equal | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 4.2927e+05 | 3.2567e+05 | 3.2567e+05 | 1.32 |
| 2x4 / exact / B0_ref1_k1 / fakefez | heron | 0.1 | inf | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 8.5853e+05 | 9.0427e+05 | 9.0427e+05 | 0.949 |
| 2x4 / exact / B0_ref1_k1 / fakefez | heron | 0.1 | equal | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 1.3050e+06 | 9.0427e+05 | 9.0427e+05 | 1.44 |
| 2x4 / exact / B0_ref1_k1 / fakefez | heron | 0.05 | inf | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 6.5201e+05 | 6.9504e+05 | 6.9504e+05 | 0.938 |
| 2x4 / exact / B0_ref1_k1 / fakefez | heron | 0.05 | equal | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91043 | 9.9507e+05 | 6.9504e+05 | 6.9504e+05 | 1.43 |
| 2x4 / exact / B0_ref1_k1 / fakefez | zero | 0.1 | inf | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 5.6915e+05 | 9.0427e+05 | 9.0427e+05 | 0.629 |
| 2x4 / exact / B0_ref1_k1 / fakefez | zero | 0.1 | equal | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 8.6522e+05 | 9.0427e+05 | 9.0427e+05 | 0.957 |
| 2x4 / exact / B0_ref1_k1 / fakefez | zero | 0.05 | inf | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 4.3219e+05 | 6.9504e+05 | 6.9504e+05 | 0.622 |
| 2x4 / exact / B0_ref1_k1 / fakefez | zero | 0.05 | equal | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 6.5969e+05 | 6.9504e+05 | 6.9504e+05 | 0.949 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | heron | 0.1 | inf | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89854 | 8.7354e+05 | 9.1914e+05 | 8.8744e+05 | 0.95 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | heron | 0.1 | equal | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89854 | 1.3232e+06 | 9.1914e+05 | 8.8744e+05 | 1.44 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | heron | 0.05 | inf | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89854 | 6.6552e+05 | 7.0647e+05 | 6.8211e+05 | 0.942 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | heron | 0.05 | equal | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89854 | 1.0111e+06 | 7.0647e+05 | 6.8211e+05 | 1.43 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | zero | 0.1 | inf | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 5.7741e+05 | 9.1914e+05 | 8.8744e+05 | 0.628 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | zero | 0.1 | equal | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 8.7471e+05 | 9.1914e+05 | 8.8744e+05 | 0.952 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | zero | 0.05 | inf | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 4.3987e+05 | 7.0647e+05 | 6.8211e+05 | 0.623 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | zero | 0.05 | equal | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 6.6833e+05 | 7.0647e+05 | 6.8211e+05 | 0.946 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | heron | 0.1 | inf | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91505 | 8.6139e+05 | 9.0503e+05 | 9.0503e+05 | 0.952 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | heron | 0.1 | equal | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91505 | 1.3087e+06 | 9.0503e+05 | 9.0503e+05 | 1.45 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | heron | 0.05 | inf | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91505 | 6.5447e+05 | 6.9562e+05 | 6.9562e+05 | 0.941 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | heron | 0.05 | equal | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91505 | 9.9819e+05 | 6.9562e+05 | 6.9562e+05 | 1.43 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | zero | 0.1 | inf | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 5.7340e+05 | 9.0503e+05 | 9.0503e+05 | 0.634 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | zero | 0.1 | equal | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 8.7124e+05 | 9.0503e+05 | 9.0503e+05 | 0.963 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | zero | 0.05 | inf | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 4.3562e+05 | 6.9562e+05 | 6.9562e+05 | 0.626 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | zero | 0.05 | equal | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 6.6449e+05 | 6.9562e+05 | 6.9562e+05 | 0.955 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | heron | 0.1 | inf | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69670 | 6.3874e+05 | 4.2371e+05 | 4.2371e+05 | 1.51 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | heron | 0.1 | equal | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69670 | 9.7229e+05 | 4.2371e+05 | 4.2371e+05 | 2.29 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | heron | 0.05 | inf | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69670 | 4.8444e+05 | 3.2567e+05 | 3.2567e+05 | 1.49 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | heron | 0.05 | equal | 69688 | 0.00792 | 1.67 | 0.0577 | 0.209 | 69670 | 7.4075e+05 | 3.2567e+05 | 3.2567e+05 | 2.27 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | zero | 0.1 | inf | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 3.7008e+05 | 4.2371e+05 | 4.2371e+05 | 0.873 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | zero | 0.1 | equal | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 5.6360e+05 | 4.2371e+05 | 4.2371e+05 | 1.33 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | zero | 0.05 | inf | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 2.8057e+05 | 3.2567e+05 | 3.2567e+05 | 0.861 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | zero | 0.05 | equal | 69688 | 0.00467 | 0.985 | 0.0725 | 0.121 | 69565 | 4.2927e+05 | 3.2567e+05 | 3.2567e+05 | 1.32 |
| 2x4 / exact / B1_ref0_k1 / fakefez | heron | 0.1 | inf | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91045 | 8.5859e+05 | 9.0427e+05 | 9.0427e+05 | 0.949 |
| 2x4 / exact / B1_ref0_k1 / fakefez | heron | 0.1 | equal | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91045 | 1.3051e+06 | 9.0427e+05 | 9.0427e+05 | 1.44 |
| 2x4 / exact / B1_ref0_k1 / fakefez | heron | 0.05 | inf | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91045 | 6.5205e+05 | 6.9504e+05 | 6.9504e+05 | 0.938 |
| 2x4 / exact / B1_ref0_k1 / fakefez | heron | 0.05 | equal | 148726 | 0.011 | 1.09 | 0.0916 | 0.28 | 91045 | 9.9514e+05 | 6.9504e+05 | 6.9504e+05 | 1.43 |
| 2x4 / exact / B1_ref0_k1 / fakefez | zero | 0.1 | inf | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 5.6915e+05 | 9.0427e+05 | 9.0427e+05 | 0.629 |
| 2x4 / exact / B1_ref0_k1 / fakefez | zero | 0.1 | equal | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 8.6522e+05 | 9.0427e+05 | 9.0427e+05 | 0.957 |
| 2x4 / exact / B1_ref0_k1 / fakefez | zero | 0.05 | inf | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 4.3219e+05 | 6.9504e+05 | 6.9504e+05 | 0.622 |
| 2x4 / exact / B1_ref0_k1 / fakefez | zero | 0.05 | equal | 148726 | 0.00735 | 0.727 | 0.0983 | 0.186 | 89395 | 6.5969e+05 | 6.9504e+05 | 6.9504e+05 | 0.949 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | heron | 0.1 | inf | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89854 | 8.7358e+05 | 9.1914e+05 | 8.8744e+05 | 0.95 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | heron | 0.1 | equal | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89854 | 1.3233e+06 | 9.1914e+05 | 8.8744e+05 | 1.44 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | heron | 0.05 | inf | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89854 | 6.6555e+05 | 7.0647e+05 | 6.8211e+05 | 0.942 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | heron | 0.05 | equal | 145958 | 0.011 | 1.11 | 0.0865 | 0.292 | 89854 | 1.0111e+06 | 7.0647e+05 | 6.8211e+05 | 1.43 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | zero | 0.1 | inf | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 5.7741e+05 | 9.1914e+05 | 8.8744e+05 | 0.628 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | zero | 0.1 | equal | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 8.7471e+05 | 9.1914e+05 | 8.8744e+05 | 0.952 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | zero | 0.05 | inf | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 4.3987e+05 | 7.0647e+05 | 6.8211e+05 | 0.623 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | zero | 0.05 | equal | 145958 | 0.00735 | 0.741 | 0.0931 | 0.193 | 88175 | 6.6833e+05 | 7.0647e+05 | 6.8211e+05 | 0.946 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | heron | 0.1 | inf | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91504 | 8.6148e+05 | 9.0503e+05 | 9.0503e+05 | 0.952 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | heron | 0.1 | equal | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91504 | 1.3088e+06 | 9.0503e+05 | 9.0503e+05 | 1.45 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | heron | 0.05 | inf | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91504 | 6.5453e+05 | 6.9562e+05 | 6.9562e+05 | 0.941 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | heron | 0.05 | equal | 148850 | 0.011 | 1.09 | 0.0912 | 0.28 | 91504 | 9.9829e+05 | 6.9562e+05 | 6.9562e+05 | 1.44 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | zero | 0.1 | inf | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 5.7340e+05 | 9.0503e+05 | 9.0503e+05 | 0.634 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | zero | 0.1 | equal | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 8.7124e+05 | 9.0503e+05 | 9.0503e+05 | 0.963 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | zero | 0.05 | inf | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 4.3562e+05 | 6.9562e+05 | 6.9562e+05 | 0.626 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | zero | 0.05 | equal | 148850 | 0.00739 | 0.73 | 0.0979 | 0.187 | 89479 | 6.6449e+05 | 6.9562e+05 | 6.9562e+05 | 0.955 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | heron | 0.1 | inf | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14062 | 1.2607e+05 | 8.541e+04 | 8.541e+04 | 1.48 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | heron | 0.1 | equal | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14062 | 1.9189e+05 | 8.541e+04 | 8.541e+04 | 2.25 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | heron | 0.05 | inf | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14062 | 9.562e+04 | 6.565e+04 | 6.565e+04 | 1.46 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | heron | 0.05 | equal | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14062 | 1.4620e+05 | 6.565e+04 | 6.565e+04 | 2.23 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | zero | 0.1 | inf | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 7.357e+04 | 8.541e+04 | 8.541e+04 | 0.861 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | zero | 0.1 | equal | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 1.1202e+05 | 8.541e+04 | 8.541e+04 | 1.31 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | zero | 0.05 | inf | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 5.578e+04 | 6.565e+04 | 6.565e+04 | 0.85 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | zero | 0.05 | equal | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 8.533e+04 | 6.565e+04 | 6.565e+04 | 1.3 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | heron | 0.1 | inf | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18498 | 1.7280e+05 | 1.9363e+05 | 1.7489e+05 | 0.892 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | heron | 0.1 | equal | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18498 | 2.6266e+05 | 1.9363e+05 | 1.7489e+05 | 1.36 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | heron | 0.05 | inf | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18498 | 1.3122e+05 | 1.4883e+05 | 1.3443e+05 | 0.882 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | heron | 0.05 | equal | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18498 | 2.0028e+05 | 1.4883e+05 | 1.3443e+05 | 1.35 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | zero | 0.1 | inf | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.1351e+05 | 1.9363e+05 | 1.7489e+05 | 0.586 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | zero | 0.1 | equal | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.7252e+05 | 1.9363e+05 | 1.7489e+05 | 0.891 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | zero | 0.05 | inf | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 8.621e+04 | 1.4883e+05 | 1.3443e+05 | 0.579 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | zero | 0.05 | equal | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.3156e+05 | 1.4883e+05 | 1.3443e+05 | 0.884 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | heron | 0.1 | inf | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19108 | 1.6372e+05 | 1.9679e+05 | 1.8367e+05 | 0.832 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | heron | 0.1 | equal | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19108 | 2.4896e+05 | 1.9679e+05 | 1.8367e+05 | 1.27 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | heron | 0.05 | inf | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19108 | 1.2429e+05 | 1.5126e+05 | 1.4117e+05 | 0.822 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | heron | 0.05 | equal | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19108 | 1.8979e+05 | 1.5126e+05 | 1.4117e+05 | 1.25 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | zero | 0.1 | inf | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.1125e+05 | 1.9679e+05 | 1.8367e+05 | 0.565 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | zero | 0.1 | equal | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.6918e+05 | 1.9679e+05 | 1.8367e+05 | 0.86 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | zero | 0.05 | inf | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 8.446e+04 | 1.5126e+05 | 1.4117e+05 | 0.558 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | zero | 0.05 | equal | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.2897e+05 | 1.5126e+05 | 1.4117e+05 | 0.853 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | heron | 0.1 | inf | 28925 | 0.00203 | 1.03 | 0.0891 | 0.0555 | 18466 | 1.6970e+05 | 1.8843e+05 | 1.7587e+05 | 0.901 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | heron | 0.1 | equal | 28925 | 0.00203 | 1.03 | 0.0891 | 0.0555 | 18466 | 2.5817e+05 | 1.8843e+05 | 1.7587e+05 | 1.37 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | heron | 0.05 | inf | 28925 | 0.00203 | 1.03 | 0.0891 | 0.0555 | 18466 | 1.2877e+05 | 1.4483e+05 | 1.3518e+05 | 0.889 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | heron | 0.05 | equal | 28925 | 0.00203 | 1.03 | 0.0891 | 0.0555 | 18466 | 1.9676e+05 | 1.4483e+05 | 1.3518e+05 | 1.36 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | zero | 0.1 | inf | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.1044e+05 | 1.8843e+05 | 1.7587e+05 | 0.586 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | zero | 0.1 | equal | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.6801e+05 | 1.8843e+05 | 1.7587e+05 | 0.892 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | zero | 0.05 | inf | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 8.38e+04 | 1.4483e+05 | 1.3518e+05 | 0.579 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | zero | 0.05 | equal | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.2804e+05 | 1.4483e+05 | 1.3518e+05 | 0.884 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | heron | 0.1 | inf | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14060 | 1.2607e+05 | 8.541e+04 | 8.541e+04 | 1.48 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | heron | 0.1 | equal | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14060 | 1.9189e+05 | 8.541e+04 | 8.541e+04 | 2.25 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | heron | 0.05 | inf | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14060 | 9.561e+04 | 6.565e+04 | 6.565e+04 | 1.46 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | heron | 0.05 | equal | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14060 | 1.4620e+05 | 6.565e+04 | 6.565e+04 | 2.23 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | zero | 0.1 | inf | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 7.357e+04 | 8.541e+04 | 8.541e+04 | 0.861 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | zero | 0.1 | equal | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 1.1202e+05 | 8.541e+04 | 8.541e+04 | 1.31 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | zero | 0.05 | inf | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 5.578e+04 | 6.565e+04 | 6.565e+04 | 0.85 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | zero | 0.05 | equal | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 8.533e+04 | 6.565e+04 | 6.565e+04 | 1.3 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | heron | 0.1 | inf | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18489 | 1.7303e+05 | 1.9363e+05 | 1.7489e+05 | 0.894 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | heron | 0.1 | equal | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18489 | 2.6301e+05 | 1.9363e+05 | 1.7489e+05 | 1.36 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | heron | 0.05 | inf | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18489 | 1.3139e+05 | 1.4883e+05 | 1.3443e+05 | 0.883 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | heron | 0.05 | equal | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18489 | 2.0055e+05 | 1.4883e+05 | 1.3443e+05 | 1.35 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | zero | 0.1 | inf | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.1351e+05 | 1.9363e+05 | 1.7489e+05 | 0.586 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | zero | 0.1 | equal | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.7252e+05 | 1.9363e+05 | 1.7489e+05 | 0.891 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | zero | 0.05 | inf | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 8.621e+04 | 1.4883e+05 | 1.3443e+05 | 0.579 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | zero | 0.05 | equal | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.3156e+05 | 1.4883e+05 | 1.3443e+05 | 0.884 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | heron | 0.1 | inf | 30208 | 0.00211 | 1.03 | 0.0892 | 0.0578 | 19098 | 1.6412e+05 | 1.9679e+05 | 1.8367e+05 | 0.834 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | heron | 0.1 | equal | 30208 | 0.00211 | 1.03 | 0.0892 | 0.0578 | 19098 | 2.4957e+05 | 1.9679e+05 | 1.8367e+05 | 1.27 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | heron | 0.05 | inf | 30208 | 0.00211 | 1.03 | 0.0892 | 0.0578 | 19098 | 1.2459e+05 | 1.5126e+05 | 1.4117e+05 | 0.824 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | heron | 0.05 | equal | 30208 | 0.00211 | 1.03 | 0.0892 | 0.0578 | 19098 | 1.9025e+05 | 1.5126e+05 | 1.4117e+05 | 1.26 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | zero | 0.1 | inf | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.1125e+05 | 1.9679e+05 | 1.8367e+05 | 0.565 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | zero | 0.1 | equal | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.6918e+05 | 1.9679e+05 | 1.8367e+05 | 0.86 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | zero | 0.05 | inf | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 8.446e+04 | 1.5126e+05 | 1.4117e+05 | 0.558 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | zero | 0.05 | equal | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.2897e+05 | 1.5126e+05 | 1.4117e+05 | 0.853 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | heron | 0.1 | inf | 28925 | 0.00203 | 1.03 | 0.0892 | 0.0555 | 18471 | 1.6964e+05 | 1.8843e+05 | 1.7587e+05 | 0.9 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | heron | 0.1 | equal | 28925 | 0.00203 | 1.03 | 0.0892 | 0.0555 | 18471 | 2.5807e+05 | 1.8843e+05 | 1.7587e+05 | 1.37 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | heron | 0.05 | inf | 28925 | 0.00203 | 1.03 | 0.0892 | 0.0555 | 18471 | 1.2872e+05 | 1.4483e+05 | 1.3518e+05 | 0.889 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | heron | 0.05 | equal | 28925 | 0.00203 | 1.03 | 0.0892 | 0.0555 | 18471 | 1.9668e+05 | 1.4483e+05 | 1.3518e+05 | 1.36 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | zero | 0.1 | inf | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.1044e+05 | 1.8843e+05 | 1.7587e+05 | 0.586 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | zero | 0.1 | equal | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.6801e+05 | 1.8843e+05 | 1.7587e+05 | 0.892 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | zero | 0.05 | inf | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 8.38e+04 | 1.4483e+05 | 1.3518e+05 | 0.579 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | zero | 0.05 | equal | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.2804e+05 | 1.4483e+05 | 1.3518e+05 | 0.884 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | heron | 0.1 | inf | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14061 | 1.2607e+05 | 8.541e+04 | 8.541e+04 | 1.48 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | heron | 0.1 | equal | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14061 | 1.9189e+05 | 8.541e+04 | 8.541e+04 | 2.25 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | heron | 0.05 | inf | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14061 | 9.562e+04 | 6.565e+04 | 6.565e+04 | 1.46 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | heron | 0.05 | equal | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14061 | 1.4620e+05 | 6.565e+04 | 6.565e+04 | 2.23 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | zero | 0.1 | inf | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 7.357e+04 | 8.541e+04 | 8.541e+04 | 0.861 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | zero | 0.1 | equal | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 1.1202e+05 | 8.541e+04 | 8.541e+04 | 1.31 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | zero | 0.05 | inf | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 5.578e+04 | 6.565e+04 | 6.565e+04 | 0.85 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | zero | 0.05 | equal | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 8.533e+04 | 6.565e+04 | 6.565e+04 | 1.3 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | heron | 0.1 | inf | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18497 | 1.7280e+05 | 1.9363e+05 | 1.7489e+05 | 0.892 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | heron | 0.1 | equal | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18497 | 2.6266e+05 | 1.9363e+05 | 1.7489e+05 | 1.36 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | heron | 0.05 | inf | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18497 | 1.3122e+05 | 1.4883e+05 | 1.3443e+05 | 0.882 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | heron | 0.05 | equal | 28765 | 0.002 | 1.02 | 0.0871 | 0.0566 | 18497 | 2.0028e+05 | 1.4883e+05 | 1.3443e+05 | 1.35 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | zero | 0.1 | inf | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.1351e+05 | 1.9363e+05 | 1.7489e+05 | 0.586 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | zero | 0.1 | equal | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.7252e+05 | 1.9363e+05 | 1.7489e+05 | 0.891 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | zero | 0.05 | inf | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 8.621e+04 | 1.4883e+05 | 1.3443e+05 | 0.579 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | zero | 0.05 | equal | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.3156e+05 | 1.4883e+05 | 1.3443e+05 | 0.884 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | heron | 0.1 | inf | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19108 | 1.6372e+05 | 1.9679e+05 | 1.8367e+05 | 0.832 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | heron | 0.1 | equal | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19108 | 2.4896e+05 | 1.9679e+05 | 1.8367e+05 | 1.27 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | heron | 0.05 | inf | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19108 | 1.2429e+05 | 1.5126e+05 | 1.4117e+05 | 0.822 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | heron | 0.05 | equal | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19108 | 1.8979e+05 | 1.5126e+05 | 1.4117e+05 | 1.25 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | zero | 0.1 | inf | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.1125e+05 | 1.9679e+05 | 1.8367e+05 | 0.565 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | zero | 0.1 | equal | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.6918e+05 | 1.9679e+05 | 1.8367e+05 | 0.86 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | zero | 0.05 | inf | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 8.446e+04 | 1.5126e+05 | 1.4117e+05 | 0.558 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | zero | 0.05 | equal | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.2897e+05 | 1.5126e+05 | 1.4117e+05 | 0.853 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | heron | 0.1 | inf | 28925 | 0.00203 | 1.03 | 0.0891 | 0.0555 | 18466 | 1.6970e+05 | 1.8843e+05 | 1.7587e+05 | 0.901 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | heron | 0.1 | equal | 28925 | 0.00203 | 1.03 | 0.0891 | 0.0555 | 18466 | 2.5817e+05 | 1.8843e+05 | 1.7587e+05 | 1.37 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | heron | 0.05 | inf | 28925 | 0.00203 | 1.03 | 0.0891 | 0.0555 | 18466 | 1.2877e+05 | 1.4483e+05 | 1.3518e+05 | 0.889 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | heron | 0.05 | equal | 28925 | 0.00203 | 1.03 | 0.0891 | 0.0555 | 18466 | 1.9676e+05 | 1.4483e+05 | 1.3518e+05 | 1.36 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | zero | 0.1 | inf | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.1044e+05 | 1.8843e+05 | 1.7587e+05 | 0.586 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | zero | 0.1 | equal | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.6801e+05 | 1.8843e+05 | 1.7587e+05 | 0.892 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | zero | 0.05 | inf | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 8.38e+04 | 1.4483e+05 | 1.3518e+05 | 0.579 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | zero | 0.05 | equal | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.2804e+05 | 1.4483e+05 | 1.3518e+05 | 0.884 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | heron | 0.1 | inf | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14063 | 1.2607e+05 | 8.541e+04 | 8.541e+04 | 1.48 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | heron | 0.1 | equal | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14063 | 1.9190e+05 | 8.541e+04 | 8.541e+04 | 2.25 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | heron | 0.05 | inf | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14063 | 9.562e+04 | 6.565e+04 | 6.565e+04 | 1.46 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | heron | 0.05 | equal | 14048 | 0.00156 | 1.64 | 0.0587 | 0.0412 | 14063 | 1.4621e+05 | 6.565e+04 | 6.565e+04 | 2.23 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | zero | 0.1 | inf | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 7.357e+04 | 8.541e+04 | 8.541e+04 | 0.861 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | zero | 0.1 | equal | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 1.1202e+05 | 8.541e+04 | 8.541e+04 | 1.31 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | zero | 0.05 | inf | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 5.578e+04 | 6.565e+04 | 6.565e+04 | 0.85 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | zero | 0.05 | equal | 14048 | 9.286e-04 | 0.972 | 0.0735 | 0.0241 | 14032 | 8.533e+04 | 6.565e+04 | 6.565e+04 | 1.3 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | heron | 0.1 | inf | 28765 | 0.002 | 1.02 | 0.0872 | 0.0566 | 18493 | 1.7280e+05 | 1.9363e+05 | 1.7489e+05 | 0.892 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | heron | 0.1 | equal | 28765 | 0.002 | 1.02 | 0.0872 | 0.0566 | 18493 | 2.6266e+05 | 1.9363e+05 | 1.7489e+05 | 1.36 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | heron | 0.05 | inf | 28765 | 0.002 | 1.02 | 0.0872 | 0.0566 | 18493 | 1.3122e+05 | 1.4883e+05 | 1.3443e+05 | 0.882 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | heron | 0.05 | equal | 28765 | 0.002 | 1.02 | 0.0872 | 0.0566 | 18493 | 2.0028e+05 | 1.4883e+05 | 1.3443e+05 | 1.35 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | zero | 0.1 | inf | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.1351e+05 | 1.9363e+05 | 1.7489e+05 | 0.586 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | zero | 0.1 | equal | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.7252e+05 | 1.9363e+05 | 1.7489e+05 | 0.891 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | zero | 0.05 | inf | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 8.621e+04 | 1.4883e+05 | 1.3443e+05 | 0.579 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | zero | 0.05 | equal | 28765 | 0.00132 | 0.677 | 0.0952 | 0.0372 | 17265 | 1.3156e+05 | 1.4883e+05 | 1.3443e+05 | 0.884 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | heron | 0.1 | inf | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19109 | 1.6381e+05 | 1.9679e+05 | 1.8367e+05 | 0.832 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | heron | 0.1 | equal | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19109 | 2.4909e+05 | 1.9679e+05 | 1.8367e+05 | 1.27 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | heron | 0.05 | inf | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19109 | 1.2436e+05 | 1.5126e+05 | 1.4117e+05 | 0.822 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | heron | 0.05 | equal | 30208 | 0.00211 | 1.03 | 0.0894 | 0.0576 | 19109 | 1.8989e+05 | 1.5126e+05 | 1.4117e+05 | 1.26 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | zero | 0.1 | inf | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.1125e+05 | 1.9679e+05 | 1.8367e+05 | 0.565 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | zero | 0.1 | equal | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.6918e+05 | 1.9679e+05 | 1.8367e+05 | 0.86 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | zero | 0.05 | inf | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 8.446e+04 | 1.5126e+05 | 1.4117e+05 | 0.558 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | zero | 0.05 | equal | 30208 | 0.00144 | 0.702 | 0.0949 | 0.0392 | 18350 | 1.2897e+05 | 1.5126e+05 | 1.4117e+05 | 0.853 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | heron | 0.1 | inf | 28925 | 0.00203 | 1.03 | 0.0892 | 0.0555 | 18473 | 1.6960e+05 | 1.8843e+05 | 1.7587e+05 | 0.9 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | heron | 0.1 | equal | 28925 | 0.00203 | 1.03 | 0.0892 | 0.0555 | 18473 | 2.5801e+05 | 1.8843e+05 | 1.7587e+05 | 1.37 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | heron | 0.05 | inf | 28925 | 0.00203 | 1.03 | 0.0892 | 0.0555 | 18473 | 1.2870e+05 | 1.4483e+05 | 1.3518e+05 | 0.889 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | heron | 0.05 | equal | 28925 | 0.00203 | 1.03 | 0.0892 | 0.0555 | 18473 | 1.9664e+05 | 1.4483e+05 | 1.3518e+05 | 1.36 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | zero | 0.1 | inf | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.1044e+05 | 1.8843e+05 | 1.7587e+05 | 0.586 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | zero | 0.1 | equal | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.6801e+05 | 1.8843e+05 | 1.7587e+05 | 0.892 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | zero | 0.05 | inf | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 8.38e+04 | 1.4483e+05 | 1.3518e+05 | 0.579 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | zero | 0.05 | equal | 28925 | 0.00134 | 0.679 | 0.0981 | 0.0362 | 17358 | 1.2804e+05 | 1.4483e+05 | 1.3518e+05 | 0.884 |

### The serial formula on the committed counts (criterion C8)

| circuit | n | n_2q | T2/t_2q | owner's value | source |
|---|---|---|---|---|---|
| 2x2 all-to-all (CZ) | 12 | 256 | 667.08 | 667.1 | validation/S2.json data.2x2.coarse_step.all_to_all.cz |
| 2x2 routed, the frozen canary | 12 | 663 | 1727.6 | 1727.6 | data/S2_duration_compare.json circuits.exact|frozen|B0_ref06_k1_rep1.n_cz |
| 2x3 all-to-all (RZZ) | 20 | 2158 | 9372.1 | 9372.1 | data/S2D_2x3_device_requirements.json counts.per_term_rzz_sum |
| 2x3 routed heavy-hex d=5 | 20 | 5477 | 23786 | 23786.3 | validation/S2.json data.2x3.coarse_step.routed.cz |
| 2x3 fixed-angle all-to-all (RZZ) | 20 | 1620 | 7035.6 | 7035.6 | data/S2D_2x3_device_requirements.json levers.fixed_angle_generator.counts_rzz_recomputed.rzz |
| 2x2 routed heavy-hex d=3 | 12 | 618 | 1610.4 | - | validation/S2.json data.2x2.coarse_step.routed.cz |
| 2x3 all-to-all (CZ) | 20 | 2164 | 9398.1 | - | validation/S2.json data.2x3.coarse_step.all_to_all.cz |

### What a real device has, for comparison

| record | T2 mean (s) | T2 harmonic mean (s) | T2 best (s) | T2 worst (s) | T2/t_cz mean | T2/t_cz harmonic | T2/t_cz best | T2/t_cz worst |
|---|---|---|---|---|---|---|---|---|
| Heron r2, the 12 canary qubits | 1.191e-04 | 7.056e-05 | 2.651e-04 | 1.602e-05 | 1751 | **1038** | 3898 | 235.5 |

Which statistic: the harmonic mean is the physically right one: the idle budget is a sum over qubits of (idle time)/T2_q, so it is the sum of 1/T2 that matters, not the mean of T2.  The harmonic mean is therefore the headline
comparison statistic here and the other three are reported beside it; the owner's "1912 on the
patch that flew" is not any statistic of this record and is not used.

### The FakeFez full-device reading (a real per-qubit record, not a uniform one)

| circuit | CZ | f_gates | T (s) | S_T1 | S_T2 | S_idle | f idle-aware | coherence scale for mean f >= 0.1 | coherence-only scale (f = 0.1) | coherence-only scale (f = 0.05) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2x4 / B0_ref0_k1 / fakefez | 148726 | 0 | 0.0127 | 201 | 508 | 709 | 0 | - | 1059 | 791.1 |
| 2x4 / B0_ref0_k1 / fakefez_backend | 148726 | 1.749e-223 | 0.0126 | 237 | 845 | 1.08e+03 | 0 | - | 2134 | 1589 |
| 2x4 / B0_ref0_k4 / fakefez | 148726 | 0 | 0.0127 | 201 | 508 | 709 | 0 | - | 1059 | 791.2 |
| 2x4 / B0_ref0_k4 / fakefez_backend | 148726 | 1.749e-223 | 0.0126 | 237 | 845 | 1.08e+03 | 0 | - | 2134 | 1589 |
| 2x4 / B0_ref1_k1 / fakefez | 148726 | 0 | 0.0127 | 201 | 508 | 709 | 0 | - | 1059 | 791.1 |
| 2x4 / B0_ref1_k1 / fakefez_backend | 148726 | 1.749e-223 | 0.0126 | 237 | 845 | 1.08e+03 | 0 | - | 2134 | 1589 |
| 2x4 / B1_ref0_k1 / fakefez | 148726 | 0 | 0.0127 | 201 | 508 | 709 | 0 | - | 1059 | 791.2 |
| 2x4 / B1_ref0_k1 / fakefez_backend | 148726 | 1.749e-223 | 0.0126 | 237 | 845 | 1.08e+03 | 0 | - | 2134 | 1589 |

A `None` in the coherence-scale column means the gate and readout errors of the record alone
already put f below the target, so no amount of coherence reaches it; the coherence-ONLY column
(every gate and readout error set to zero, durations and coherence times kept) always exists and is
the like-for-like reading against the 5.51x that `validation/S2D_idle.json` records at 2x2.

## The gate-only requirement (part C: the same criterion with zero idle time)

The criterion is one half-space, n_2q eps2~ + n_1q eps1~ + n_meas eps_ro~ + S_idle <= ln(1/f_target)
(`skqd.device_req.target_with_idle`); the T2/t_2q number above is its coherence-only face and the
table below is its gate face at S_idle = 0.

| circuit | f_target | n_2q | n_1q | n_meas | eps2 alone | eps2 at declared eps1/eps_ro | eps2 with virtual rz | log budget spent | log budget available | over budget by |
|---|---|---|---|---|---|---|---|---|---|---|
| 2x2 / exact / B0_ref0_k1 / all_to_all | 0.1 | 256 | 920 | 12 | 0.00895 | 0.0085 | 0.00865 | 0.372 | 2.3 | -1.93 |
| 2x2 / exact / B0_ref0_k1 / all_to_all | 0.05 | 256 | 920 | 12 | 0.0116 | 0.0112 | 0.0113 | 0.372 | 3 | -2.62 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | 0.1 | 618 | 2023 | 12 | 0.00372 | 0.00335 | 0.00347 | 0.845 | 2.3 | -1.46 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | 0.05 | 618 | 2023 | 12 | 0.00484 | 0.00447 | 0.00458 | 0.845 | 3 | -2.15 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | 0.1 | 2164 | 6754 | 20 | 0.00106 | 7.331e-04 | 8.471e-04 | 2.88 | 2.3 | 0.578 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | 0.05 | 2164 | 6754 | 20 | 0.00138 | 0.00105 | 0.00117 | 2.88 | 3 | -0.115 |
| 2x3 / exact / B0_ref0_k1 / fakefez | 0.1 | 5737 | 17218 | 20 | 4.013e-04 | 9.424e-05 | 1.824e-04 | 7.5 | 2.3 | 5.2 |
| 2x3 / exact / B0_ref0_k1 / fakefez | 0.05 | 5737 | 17218 | 20 | 5.220e-04 | 2.150e-04 | 3.032e-04 | 7.5 | 3 | 4.51 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | 0.1 | 5477 | 17465 | 20 | 4.203e-04 | 9.420e-05 | 1.948e-04 | 7.27 | 2.3 | 4.96 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | 0.05 | 5477 | 17465 | 20 | 5.468e-04 | 2.207e-04 | 3.214e-04 | 7.27 | 3 | 4.27 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | 0.1 | 69688 | 209395 | 28 | 3.304e-05 | - | - | 90.7 | 2.3 | 88.4 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | 0.05 | 69688 | 209395 | 28 | 4.299e-05 | - | - | 90.7 | 3 | 87.7 |
| 2x4 / exact / B0_ref0_k1 / fakefez | 0.1 | 148726 | 501985 | 28 | 1.548e-05 | - | - | 199 | 2.3 | 197 |
| 2x4 / exact / B0_ref0_k1 / fakefez | 0.05 | 148726 | 501985 | 28 | 2.014e-05 | - | - | 199 | 3 | 196 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | 0.1 | 145958 | 498289 | 28 | 1.578e-05 | - | - | 196 | 2.3 | 194 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | 0.05 | 145958 | 498289 | 28 | 2.052e-05 | - | - | 196 | 3 | 193 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | 0.1 | 148850 | 493084 | 28 | 1.547e-05 | - | - | 198 | 2.3 | 196 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | 0.05 | 148850 | 493084 | 28 | 2.013e-05 | - | - | 198 | 3 | 195 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | 0.1 | 69688 | 209437 | 28 | 3.304e-05 | - | - | 90.7 | 2.3 | 88.4 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | 0.05 | 69688 | 209437 | 28 | 4.299e-05 | - | - | 90.7 | 3 | 87.7 |
| 2x4 / exact / B0_ref0_k4 / fakefez | 0.1 | 148726 | 501987 | 28 | 1.548e-05 | - | - | 199 | 2.3 | 197 |
| 2x4 / exact / B0_ref0_k4 / fakefez | 0.05 | 148726 | 501987 | 28 | 2.014e-05 | - | - | 199 | 3 | 196 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | 0.1 | 145958 | 498140 | 28 | 1.578e-05 | - | - | 196 | 2.3 | 194 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | 0.05 | 145958 | 498140 | 28 | 2.052e-05 | - | - | 196 | 3 | 193 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | 0.1 | 148850 | 492604 | 28 | 1.547e-05 | - | - | 198 | 2.3 | 196 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | 0.05 | 148850 | 492604 | 28 | 2.013e-05 | - | - | 198 | 3 | 195 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | 0.1 | 69688 | 209397 | 28 | 3.304e-05 | - | - | 90.7 | 2.3 | 88.4 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | 0.05 | 69688 | 209397 | 28 | 4.299e-05 | - | - | 90.7 | 3 | 87.7 |
| 2x4 / exact / B0_ref1_k1 / fakefez | 0.1 | 148726 | 501984 | 28 | 1.548e-05 | - | - | 199 | 2.3 | 197 |
| 2x4 / exact / B0_ref1_k1 / fakefez | 0.05 | 148726 | 501984 | 28 | 2.014e-05 | - | - | 199 | 3 | 196 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | 0.1 | 145958 | 498293 | 28 | 1.578e-05 | - | - | 196 | 2.3 | 194 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | 0.05 | 145958 | 498293 | 28 | 2.052e-05 | - | - | 196 | 3 | 193 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | 0.1 | 148850 | 493089 | 28 | 1.547e-05 | - | - | 198 | 2.3 | 196 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | 0.05 | 148850 | 493089 | 28 | 2.013e-05 | - | - | 198 | 3 | 195 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | 0.1 | 69688 | 209374 | 28 | 3.304e-05 | - | - | 90.7 | 2.3 | 88.4 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | 0.05 | 69688 | 209374 | 28 | 4.299e-05 | - | - | 90.7 | 3 | 87.7 |
| 2x4 / exact / B1_ref0_k1 / fakefez | 0.1 | 148726 | 502113 | 28 | 1.548e-05 | - | - | 199 | 2.3 | 197 |
| 2x4 / exact / B1_ref0_k1 / fakefez | 0.05 | 148726 | 502113 | 28 | 2.014e-05 | - | - | 199 | 3 | 196 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | 0.1 | 145958 | 498428 | 28 | 1.578e-05 | - | - | 196 | 2.3 | 194 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | 0.05 | 145958 | 498428 | 28 | 2.052e-05 | - | - | 196 | 3 | 193 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | 0.1 | 148850 | 493375 | 28 | 1.547e-05 | - | - | 198 | 2.3 | 196 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | 0.05 | 148850 | 493375 | 28 | 2.013e-05 | - | - | 198 | 3 | 195 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | 0.1 | 14048 | 41888 | 28 | 1.639e-04 | - | - | 18.3 | 2.3 | 16 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | 0.05 | 14048 | 41888 | 28 | 2.132e-04 | - | 1.288e-05 | 18.3 | 3 | 15.3 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | 0.1 | 28765 | 89637 | 28 | 8.004e-05 | - | - | 37.8 | 2.3 | 35.5 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | 0.05 | 28765 | 89637 | 28 | 1.041e-04 | - | - | 37.8 | 3 | 34.8 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | 0.1 | 30208 | 91134 | 28 | 7.622e-05 | - | - | 39.4 | 2.3 | 37.1 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | 0.05 | 30208 | 91134 | 28 | 9.917e-05 | - | - | 39.4 | 3 | 36.4 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | 0.1 | 28925 | 91077 | 28 | 7.960e-05 | - | - | 38.1 | 2.3 | 35.8 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | 0.05 | 28925 | 91077 | 28 | 1.036e-04 | - | - | 38.1 | 3 | 35.1 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | 0.1 | 14048 | 41903 | 28 | 1.639e-04 | - | - | 18.3 | 2.3 | 16 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | 0.05 | 14048 | 41903 | 28 | 2.132e-04 | - | 1.280e-05 | 18.3 | 3 | 15.3 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | 0.1 | 28765 | 88814 | 28 | 8.004e-05 | - | - | 37.7 | 2.3 | 35.4 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | 0.05 | 28765 | 88814 | 28 | 1.041e-04 | - | - | 37.7 | 3 | 34.7 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | 0.1 | 30208 | 89859 | 28 | 7.622e-05 | - | - | 39.3 | 2.3 | 37 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | 0.05 | 30208 | 89859 | 28 | 9.917e-05 | - | - | 39.3 | 3 | 36.3 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | 0.1 | 28925 | 90625 | 28 | 7.960e-05 | - | - | 38.1 | 2.3 | 35.8 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | 0.05 | 28925 | 90625 | 28 | 1.036e-04 | - | - | 38.1 | 3 | 35.1 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | 0.1 | 14048 | 41887 | 28 | 1.639e-04 | - | - | 18.3 | 2.3 | 16 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | 0.05 | 14048 | 41887 | 28 | 2.132e-04 | - | 1.287e-05 | 18.3 | 3 | 15.3 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | 0.1 | 28765 | 89641 | 28 | 8.004e-05 | - | - | 37.8 | 2.3 | 35.5 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | 0.05 | 28765 | 89641 | 28 | 1.041e-04 | - | - | 37.8 | 3 | 34.8 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | 0.1 | 30208 | 91134 | 28 | 7.622e-05 | - | - | 39.4 | 2.3 | 37.1 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | 0.05 | 30208 | 91134 | 28 | 9.917e-05 | - | - | 39.4 | 3 | 36.4 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | 0.1 | 28925 | 91079 | 28 | 7.960e-05 | - | - | 38.1 | 2.3 | 35.8 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | 0.05 | 28925 | 91079 | 28 | 1.036e-04 | - | - | 38.1 | 3 | 35.1 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | 0.1 | 14048 | 41873 | 28 | 1.639e-04 | - | - | 18.3 | 2.3 | 16 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | 0.05 | 14048 | 41873 | 28 | 2.132e-04 | - | 1.294e-05 | 18.3 | 3 | 15.3 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | 0.1 | 28765 | 90188 | 28 | 8.004e-05 | - | - | 37.9 | 2.3 | 35.6 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | 0.05 | 28765 | 90188 | 28 | 1.041e-04 | - | - | 37.9 | 3 | 34.9 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | 0.1 | 30208 | 91632 | 28 | 7.622e-05 | - | - | 39.4 | 2.3 | 37.1 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | 0.05 | 30208 | 91632 | 28 | 9.917e-05 | - | - | 39.4 | 3 | 36.4 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | 0.1 | 28925 | 91770 | 28 | 7.960e-05 | - | - | 38.2 | 2.3 | 35.9 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | 0.05 | 28925 | 91770 | 28 | 1.036e-04 | - | - | 38.2 | 3 | 35.2 |

Declared inputs: eps1 = 0.0001, eps_ro = 0.002
(`data/S2D_2x3_device_requirements.json` feasible_region.declared_inputs).  A `-` in the
"eps2 at declared" column is the honest answer that the one-qubit and readout channels alone already
exhaust the budget, so no two-qubit error rate satisfies the criterion.

## Disjointness, colouring and the packing bound

| lattice | terms (hop+plaq) | pairs | disjoint pairs | fraction | disjoint incl. diag | chromatic number of the overlap graph | serial rounds |
|---|---|---|---|---|---|---|---|
| 2x3 | 9 | 36 | 10 | 0.278 | 10 of 45 | 6 | 9 |
| 2x4 | 13 | 78 | 35 | 0.449 | 35 of 91 | 6 | 13 |

Nearly half the term pairs at 2x4 commute trivially and the overlap graph is 6-colourable, so a
coarse step could in principle run in 6 rounds of mutually disjoint term gates instead of
13 serial ones.  **Term reordering is not evaluated here**: the order of
the groups in `krylov.term_groups` / `CircuitFactory.coarse_step` is a convention of this package
that the emulated recall of gates S1 and S2_fixed was established on, so changing it is a method
decision with a recall re-emulation, not a compilation option.  What is measured is the schedule's
own packing bound — no reordering of the same gates on the same layout can finish before
T_min = max_q busy_q, and the perfectly packed schedule (one idle window per qubit) is a rigorous
lower bound on the PTA budget at equal charged idle time because 1 - e^{-w/T} is concave.  The
S_T2 columns are read at the uniform record's own T2 (1e-4 s).  One caveat the numbers make
visible: `skqd.idle.schedule_asap` opens a window only BETWEEN instructions, so the time a qubit
sits idle after its own last gate is in `idle_s` but is not a window and costs nothing in the PTA
budget, while the packed schedule charges the full T_min - busy_q -- so the packed S_T2 can come
out ABOVE the ASAP one where T_min is close to T.  The duration bound T_min <= T is unconditional.

| circuit | T (s) | T_min (s) | speedup available | total idle now (s) | total idle packed (s) | S_T2 now | S_T2 packed |
|---|---|---|---|---|---|---|---|
| 2x2 / exact / B0_ref0_k1 / all_to_all | 2.122e-05 | 6.568e-06 | 3.23 | 2.069e-04 | 3.102e-05 | 1.01 | 0.152 |
| 2x2 / exact / B0_ref0_k1 / heavy_hex_3 | 4.124e-05 | 2.680e-05 | 1.54 | 4.203e-04 | 2.327e-04 | 2.01 | 1.05 |
| 2x3 / exact / B0_ref0_k1 / all_to_all | 2.138e-04 | 7.707e-05 | 2.77 | 0.00388 | 0.00114 | 15.6 | 4.24 |
| 2x3 / exact / B0_ref0_k1 / fakefez | 3.644e-04 | 2.740e-04 | 1.33 | 0.00804 | 0.00578 | 26.7 | 10.7 |
| 2x3 / exact / B0_ref0_k1 / heavy_hex_5 | 3.638e-04 | 2.032e-04 | 1.79 | 0.00843 | 0.00425 | 25.4 | 9.9 |
| 2x4 / exact / B0_ref0_k1 / all_to_all | 0.00792 | 0.00429 | 1.85 | 0.209 | 0.107 | 391 | 13.5 |
| 2x4 / exact / B0_ref0_k1 / fakefez | 0.011 | 0.00783 | 1.4 | 0.28 | 0.191 | 505 | 13.5 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_5 | 0.011 | 0.00665 | 1.66 | 0.292 | 0.165 | 514 | 14 |
| 2x4 / exact / B0_ref0_k1 / heavy_hex_7 | 0.011 | 0.00814 | 1.35 | 0.28 | 0.2 | 500 | 13.5 |
| 2x4 / exact / B0_ref0_k4 / all_to_all | 0.00792 | 0.00429 | 1.85 | 0.209 | 0.107 | 391 | 13.5 |
| 2x4 / exact / B0_ref0_k4 / fakefez | 0.011 | 0.00783 | 1.4 | 0.28 | 0.191 | 505 | 13.5 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_5 | 0.011 | 0.00665 | 1.66 | 0.292 | 0.165 | 514 | 14 |
| 2x4 / exact / B0_ref0_k4 / heavy_hex_7 | 0.011 | 0.00814 | 1.35 | 0.28 | 0.2 | 500 | 13.5 |
| 2x4 / exact / B0_ref1_k1 / all_to_all | 0.00792 | 0.00429 | 1.85 | 0.209 | 0.107 | 391 | 13.5 |
| 2x4 / exact / B0_ref1_k1 / fakefez | 0.011 | 0.00783 | 1.4 | 0.28 | 0.191 | 505 | 13.5 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_5 | 0.011 | 0.00665 | 1.66 | 0.292 | 0.165 | 514 | 14 |
| 2x4 / exact / B0_ref1_k1 / heavy_hex_7 | 0.011 | 0.00814 | 1.35 | 0.28 | 0.2 | 500 | 13.5 |
| 2x4 / exact / B1_ref0_k1 / all_to_all | 0.00792 | 0.00429 | 1.85 | 0.209 | 0.107 | 391 | 13.5 |
| 2x4 / exact / B1_ref0_k1 / fakefez | 0.011 | 0.00783 | 1.4 | 0.28 | 0.191 | 505 | 13.5 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_5 | 0.011 | 0.00665 | 1.66 | 0.292 | 0.165 | 514 | 14 |
| 2x4 / exact / B1_ref0_k1 / heavy_hex_7 | 0.011 | 0.00814 | 1.35 | 0.28 | 0.2 | 500 | 13.5 |
| 2x4 / fixed / B0_ref0_k1 / all_to_all | 0.00156 | 0.00138 | 1.14 | 0.0412 | 0.036 | 89.7 | 13.5 |
| 2x4 / fixed / B0_ref0_k1 / fakefez | 0.002 | 0.00148 | 1.35 | 0.0566 | 0.0406 | 112 | 15 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_5 | 0.00211 | 0.00155 | 1.36 | 0.0576 | 0.0407 | 116 | 14.5 |
| 2x4 / fixed / B0_ref0_k1 / heavy_hex_7 | 0.00203 | 0.00149 | 1.36 | 0.0555 | 0.0394 | 111 | 14.5 |
| 2x4 / fixed / B0_ref0_k4 / all_to_all | 0.00156 | 0.00138 | 1.14 | 0.0412 | 0.036 | 89.7 | 13.5 |
| 2x4 / fixed / B0_ref0_k4 / fakefez | 0.002 | 0.00148 | 1.35 | 0.0566 | 0.0406 | 112 | 15 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_5 | 0.00211 | 0.00155 | 1.37 | 0.0578 | 0.0407 | 116 | 14.5 |
| 2x4 / fixed / B0_ref0_k4 / heavy_hex_7 | 0.00203 | 0.00149 | 1.36 | 0.0555 | 0.0393 | 111 | 14.5 |
| 2x4 / fixed / B0_ref1_k1 / all_to_all | 0.00156 | 0.00138 | 1.14 | 0.0412 | 0.036 | 89.7 | 13.5 |
| 2x4 / fixed / B0_ref1_k1 / fakefez | 0.002 | 0.00148 | 1.35 | 0.0566 | 0.0406 | 112 | 15 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_5 | 0.00211 | 0.00155 | 1.36 | 0.0576 | 0.0407 | 116 | 14.5 |
| 2x4 / fixed / B0_ref1_k1 / heavy_hex_7 | 0.00203 | 0.00149 | 1.36 | 0.0555 | 0.0394 | 111 | 14.5 |
| 2x4 / fixed / B1_ref0_k1 / all_to_all | 0.00156 | 0.00138 | 1.14 | 0.0412 | 0.036 | 89.7 | 13.5 |
| 2x4 / fixed / B1_ref0_k1 / fakefez | 0.002 | 0.00148 | 1.35 | 0.0566 | 0.0406 | 112 | 15 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_5 | 0.00211 | 0.00155 | 1.36 | 0.0576 | 0.0407 | 116 | 14.5 |
| 2x4 / fixed / B1_ref0_k1 / heavy_hex_7 | 0.00203 | 0.00149 | 1.36 | 0.0555 | 0.0394 | 111 | 14.5 |

## Verification detail

| family | term | support | max deviation | leakage | real gauge found | block-rounds fallback |
|---|---|---|---|---|---|---|
| 2x3|exact | hop0 | 9 | 7.402e-16 | 8.882e-16 | yes | no |
| 2x3|exact | hop1 | 6 | 1.333e-15 | 5.551e-15 | yes | no |
| 2x3|exact | hop2 | 10 | 7.219e-16 | 1.443e-15 | yes | no |
| 2x3|exact | hop3 | 10 | 4.518e-16 | 1.776e-15 | yes | no |
| 2x3|exact | hop4 | 8 | 8.632e-16 | 2.554e-15 | yes | no |
| 2x3|exact | hop5 | 9 | 8.921e-16 | 3.109e-15 | yes | no |
| 2x3|exact | hop6 | 6 | 1.610e-15 | 5.329e-15 | yes | no |
| 2x3|exact | plaq0 | 14 | 3.470e-16 | 3.331e-16 | yes | no |
| 2x3|exact | plaq1 | 14 | 2.803e-15 | 1.243e-14 | yes | no |
| 2x4|exact | hop0 | 9 | 2.395e-15 | 1.421e-14 | yes | no |
| 2x4|exact | hop1 | 6 | 1.639e-15 | 5.662e-15 | yes | no |
| 2x4|exact | hop2 | 10 | 1.591e-15 | 1.388e-14 | yes | no |
| 2x4|exact | hop3 | 11 | 2.657e-15 | 3.197e-14 | yes | no |
| 2x4|exact | hop4 | 8 | 4.066e-15 | 2.509e-14 | yes | no |
| 2x4|exact | hop5 | 11 | 1.268e-15 | 1.721e-14 | yes | no |
| 2x4|exact | hop6 | 10 | 1.832e-15 | 1.354e-14 | yes | no |
| 2x4|exact | hop7 | 8 | 3.849e-15 | 2.520e-14 | yes | no |
| 2x4|exact | hop8 | 9 | 2.040e-15 | 1.243e-14 | yes | no |
| 2x4|exact | hop9 | 6 | 1.737e-15 | 5.995e-15 | yes | no |
| 2x4|exact | plaq0 | 14 | 4.605e-16 | 3.109e-15 | yes | no |
| 2x4|exact | plaq1 | 16 | 2.431e-14 | 6.517e-14 | yes | no |
| 2x4|exact | plaq2 | 14 | 1.783e-15 | 1.776e-15 | yes | no |
| 2x4|fixed | hop0 | 9 | 0.00975 | 2.665e-15 | yes | no |
| 2x4|fixed | hop1 | 6 | 0.0157 | 4.219e-15 | yes | no |
| 2x4|fixed | hop2 | 10 | 0.00555 | 2.665e-15 | yes | no |
| 2x4|fixed | hop3 | 11 | 0.00465 | 7.772e-15 | yes | no |
| 2x4|fixed | hop4 | 8 | 0.00813 | 4.885e-15 | yes | no |
| 2x4|fixed | hop5 | 11 | 0.0034 | 4.441e-15 | yes | no |
| 2x4|fixed | hop6 | 10 | 0.00658 | 2.887e-15 | yes | no |
| 2x4|fixed | hop7 | 8 | 0.00907 | 4.663e-15 | yes | no |
| 2x4|fixed | hop8 | 9 | 0.00694 | 9.548e-15 | yes | no |
| 2x4|fixed | hop9 | 6 | 0.0134 | 4.330e-15 | yes | no |
| 2x4|fixed | plaq0 | 14 | 0.00172 | 1.110e-15 | yes | no |
| 2x4|fixed | plaq1 | 16 | 8.433e-04 | 3.182e-13 | yes | no |
| 2x4|fixed | plaq2 | 14 | 0.002 | 1.976e-14 | yes | no |

Full coarse-step circuits against the dressed-basis emulation `krylov.coarse_states`, through the
exact sparse statevector simulator `skqd.sparse_sim`:

| circuit | IR gates | max |delta| on the codewords | leakage | sparse max support | sparse (s) | emulation (s) |
|---|---|---|---|---|---|---|
| B0_ref0_k1 | 142288 | 1.069e-13 | -4.219e-15 | 262144 | 191 | 0.381 |
| B0_ref0_k4 | 142288 | 1.615e-13 | 3.618e-13 | 262144 | 222 | 0.895 |
| B0_ref1_k1 | 142289 | 3.238e-13 | -5.922e-13 | 262144 | 220 | 0.248 |
| B1_ref0_k1 | 142289 | 1.816e-13 | 3.606e-13 | 262144 | 191 | 0.341 |

### The compiled circuit at 28 qubits (criterion C6)

Gate S2 checks the leakage of the level-3 transpiled coarse step on the full statevector at
2x2 and 2x3.  **At 2x4 that check does not fit on this machine, and the reason is measured
rather than argued.**  Level 3 collects and re-synthesises two-qubit blocks, which destroys the
property that makes the IR circuit sparse -- inside a multiplexed rotation the IR touches ONE
target qubit, while a KAK block rotates both of its qubits -- so the exact sparse support of
the transpiled circuit grows past the 2^18 of the IR circuit:

| fraction of the circuit | instructions | sparse support | amplitudes (MB) | wall (s) |
|---|---|---|---|---|
| 0.2 % | 558 | 384 | 0.00586 | 0.011 |
| 0.5 % | 1395 | 16382 | 0.25 | 0.0801 |
| 1.0 % | 2790 | 131072 | 2 | 0.738 |
| 2.0 % | 5581 | 262143 | 4 | 8.28 |
| 4.0 % | 11163 | 33547458 | 512 | 711 |

A first attempt ran the whole circuit and was stopped at the 30-minute laptop rule; the staged
re-run above shows why: at 4 % of the instructions the support is already 33.5 million
amplitudes and one gate costs of order a second.  The same measurement at **2x3** settles what
is happening: there the transpiled coarse step runs to the end in 101 s and is leak-free, and
its sparse support saturates at 1048576 = 2^20, i.e. the **whole** 20-qubit Hilbert space.  A
level-3 transpiled coarse step is therefore not a sparse object at all: checking it is a DENSE
statevector simulation, which is 2^20 amplitudes (16 MB) at 2x3 and 2^28 (4.3 GB) at 2x4.  With
`circuits_ir.run_ir` at 0.7-3.8 s per gate on 2^28 (planner P4) and 2.8e5 instructions, that is
of order 100 hours on this CPU whichever representation is used.
**This is what part F (the Perlmutter Aer-GPU cross-check) exists for**: on one A100 the same
28-qubit statevector is 4.3 GB and Aer's fused kernels run it in minutes.  The branch is
written and tested on the laptop at 2x2 (`--stage gpu --lattice 2 --device CPU`:
`{"gpu_2_CPU": {}, "gpu_3_CPU": {"leakage": 3.8413716652030416e-14, "max_abs_difference_vs_sparse": 1.0551208236468243e-14, "max_abs_difference_vs_coarse_states": 1.854371588885293e-14}, "gpu_estimate": {}}`);
the proposed allowlist line is `S2_2x4 01:00:00 1`.  Walltime estimate (`--stage gpu_estimate`):
`{"n_instructions": 279083, "laptop_aer_cpu_s_per_instruction": 0.0699444590806961, "laptop_full_circuit_s_projected": 19520.309473617912, "gpu_speedup_bracket": {"conservative_assumed": 20.0, "optimistic_measured_S3": 160.99588652418254, "source_optimistic": "validation/S3.json data.cost: reference_S2D.seconds_per_shot / seconds_per_shot_used_for_projection (noisy sampling at 20 qubits, a different workload)"}, "gpu_job_s_projected": {"conservative": 1109.036986189288, "optimistic": 187.75801228695104}, "gpu_memory_statevector_gb": 4.294967296}`.

**Perlmutter result** (`validation/S2_2x4_gpu.json`, written by `--stage gpu` from the QPY
version-13 copy of the transpiled circuit, never re-transpiled):
not yet run (the CI token `S2_2x4` is not on the allowlist).

What IS measured here instead -- a reported number, not criterion C6 -- is the leakage of the
level-3 transpiled **term gates**, each on its own support (k <= 16 qubits), through the same
exact simulator from a random superposition of that term's local codewords:

| term | support | transpiled CZ | instructions | depth | leakage | deviation from exp(-i theta h) | vectors |
|---|---|---|---|---|---|---|---|
| hop0 | 9 | 194 | 817 | 675 | 1.077e-14 | 1.788e-12 | 5 |
| hop1 | 6 | 48 | 218 | 139 | 6.661e-16 | 8.775e-14 | 5 |
| hop2 | 10 | 182 | 776 | 617 | 8.771e-15 | 1.119e-12 | 5 |
| hop3 | 11 | 1282 | 5239 | 4768 | 1.088e-14 | 3.929e-12 | 5 |
| hop4 | 8 | 358 | 1399 | 1227 | 1.599e-14 | 3.674e-12 | 5 |
| hop5 | 11 | 334 | 1364 | 1185 | 1.288e-14 | 2.146e-12 | 5 |
| hop6 | 10 | 184 | 776 | 603 | 8.882e-15 | 1.088e-12 | 5 |
| hop7 | 8 | 358 | 1400 | 1229 | 1.543e-14 | 3.329e-12 | 5 |
| hop8 | 9 | 156 | 652 | 576 | 1.010e-14 | 1.846e-12 | 5 |
| hop9 | 6 | 44 | 207 | 135 | 1.554e-15 | 5.451e-14 | 5 |
| plaq0 | 14 | 214 | 895 | 787 | 1.776e-15 | 3.685e-12 | 3 |
| plaq2 | 14 | 764 | 3192 | 2757 | 1.155e-14 | 6.259e-12 | 3 |
| plaq1 | 16 | 65540 | 262141 | 259750 | 2.864e-14 | 5.006e-10 | 1 |

Leakage of the level-3 all-to-all transpiled coarse step where it WAS computable
(2x2 and 2x3 in this gate's own run, and the 2x4 entry if a completed segment exists):
`{"2x2|B0_ref0_k1|all_to_all": {"n_instructions": 1176, "n_2q": 256, "leakage": -4.440892098500626e-16, "sparse_wall_s": 0.08961868286132812, "sparse_max_support": 4096, "norm": 1.0000000000000004}, "2x3|B0_ref0_k1|all_to_all": {"n_instructions": 8918, "n_2q": 2164, "leakage": -5.484501741648273e-14, "sparse_wall_s": 100.7036805152893, "sparse_max_support": 1048576, "norm": 1.0000000000000548}}`

The simulator itself is regressed against `circuits_ir.run_ir`:
`{"circuits_2_exact": {"2x2_vs_run_ir": {"n_circuits": 20, "max_abs_difference": 1.4895204919483639e-15, "wall_s": 2.7770307064056396}}, "circuits_3_exact": {"2x3_vs_run_ir": {"n_circuits": 2, "max_abs_difference": 9.705406867517015e-15, "wall_s": 107.20640468597412}}}`
and against one dense 2^28 `run_ir` of the smallest 2x4 term
(`hop1`, 94 gates, MemAvailable
48 GB): max |delta|
1.110e-16.

`validation/S2.json` and `validation/S2_fixed.json` were re-run after the additive
`circuits_ir` change (the Walsh-Hadamard angle transform above 10 controls, which no 2x2 or 2x3 gate
list reaches) and reproduce their committed counts:
`{"S2": {"n_differences": 0, "identical": true}, "S2_fixed": {"n_differences": 1, "identical": false}}`
and the one key that differs is attributed by running HEAD's own `circuits_ir` beside the
modified one:
`[{"lattice": "2x3", "key": "coarse_step.all_to_all.depth", "committed": 5840, "reproduced": 5841, "pristine_head_value": 5840, "pristine_head_reproduces_the_fresh_value": true, "attribution": "the environment, not this change: HEAD's circuits_ir gives the same gate list and the same transpiled counts as the modified one (gate_list_sha256 identical)"}]`
`{"2x2|exact": true, "2x2|fixed": true, "2x3|exact": true, "2x3|fixed": true}`

## Test suite

`pytest -q tests`: 211 passed, 2 skipped, 11 warnings in 197.22s (0:03:17).
All tests pass.

## Honest limits

- The gate says what the 2x4 circuits cost and what coherence they need; it does not say whether
  any device meets it.
- The requirement is a PTA bound on a uniform record (`skqd.idle` is a bound, prompts/20 M-A),
  quoted as a ratio T2/t_2q; the T2 convention (Hahn-echo vs in-circuit T2*) is the vendor's to
  declare (amendment 01 item 2), and a real device is a per-qubit sum, for which the coherence-scale
  number on the FakeFez record is the like-for-like reading.
- The fixed-angle rows are a cost floor: that generator's recall is established at 2x3 only.
- The 6-round packing and the two compilation levers named in
  `reports/S2_2x4_planner_analysis_20260930.md` (control minimisation above m = 10 control bits;
  star-block diagonalisation) are measured or named, not spent.
- The 2x4 hardware run is "optional" in the manual (Step 10 row 5); nothing here changes the
  hardware programme.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| C1 2x4 dt equals validation/E3.json (2B = 0 and 2) | 2.498e-16 | <= 1e-12 | PASS |
| C1 2x4 sector dimensions and reference counts | dims 12843 / 8934, refs 11 + 4 | 12843 / 8934, 11 + 4 | PASS |
| C2 max |exact term circuit - exp(-i theta h)| on the local codeword space (13 terms, theta = dt, 2dt, 4dt) | 3.404e-14 | < 1e-10 | PASS |
| C3 leakage of every 2x4 term circuit (exact and fixed, every theta) | 3.317e-13 | < 1e-12 | PASS |
| C4 sparse simulator vs run_ir (2x2, 2x3) and vs the dense 2^28 cross-check | 2x2_vs_run_ir 1.49e-15 (20 circuits), 2x3_vs_run_ir 9.71e-15 (2 circuits); dense 2^28 hop1 1.11e-16 | < 1e-13 each | PASS |
| C5 the 4 2x4 coarse-step circuits vs krylov.coarse_states (max |delta| on the codewords) | 3.238e-13 | < 1e-10 | PASS |
| C5 leakage of the 2x4 coarse-step circuits | 5.922e-13 | < 1e-12 | PASS |
| C6 leakage of the level-3 all-to-all transpiled 2x4 k = 1 B = 0 circuit (sparse statevector) | not computable on this machine: the sparse support of the level-3 transpiled circuit reaches 33554432 (512 MB of amplitudes) after 11163 of 279084 instructions in 711 s | < 1e-9 | FAIL |
| C7 the frozen 2x2 canary on the real ibm_fez record reproduces T_s, S_T1, S_T2 of data/S2_duration_compare.json | 0 | <= 1e-9 relative | PASS |
| C8 serial_bound on the committed counts reproduces 667.1, 1727.6, 9372.1, 23786.3, 7035.6 | 0.0293932 | <= 0.1 | PASS |
| C9 validation/S2.json and S2_fixed.json counts reproduced identically after the circuits_ir change | CZ/per-term counts identical: True; HEAD circuits_ir identical to the modified one: True; 1 difference(s) against the committed JSON over all A3 keys (coarse_step.all_to_all.depth 5840 -> 5841) | every CZ / per-term count identical and HEAD's circuits_ir bit-for-bit identical to the modified one | PASS |
| C10 pytest -q tests | 211 passed, 2 skipped, 11 warnings in 197.22s (0:03:17) | all pass | PASS |
