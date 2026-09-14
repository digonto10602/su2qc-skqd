# proposal/ — the project document

`SU2QC_Project2_rev2_SKQD_Implementation_Manual.md` is the text extraction of the reference document
**"Neural-enhanced sample-based Krylov diagonalization for SU(2) with dynamical quarks in 2+1D — SU2QC Project 2,
revision 2: corrected specification and step-by-step implementation manual"** (prepared for D. Digonto, SU2QC,
10 September 2026; all reviewer corrections of 10 September 2026 incorporated).  Equations lost their layout in
the extraction; the PDF is the authoritative version — copy
`SU2QC_Project2_rev2_SKQD_Implementation_Manual.pdf` from the Claude project into this folder (it is not
included here because the cloud session could read the document's text but not its bytes).

## What this package does with it

| manual section | package | status |
|---|---|---|
| Step 1 Hamiltonian, sectors, exact references (Table 1) | `skqd.hamiltonian`, `skqd.exact`, `scripts/gate_E1.py`, `gate_E3.py` | E1, E3 PASS (all Table-1 rows reproduced) |
| Step 2 intertwiner-labelled basis, Table 2, codewords, decoder | `skqd.vertex`, `skqd.basis`, `skqd.codec`, `scripts/gate_E2.py` | E2 PASS |
| Step 3 dressed-site builder and its validation | `skqd.hamiltonian`, `skqd.fullspace` (redundant-basis route) | E1 PASS (two builders agree to 2e-14; element-wise) |
| Step 4 support generation (references, Krylov / Trotter / coarse circuits, shot rule) | `skqd.krylov`, `skqd.circuits_ir` | S1 PASS (emulation); circuits exact at 2x2 |
| Step 5 projected diagonalization, certification, support metrics | `skqd.skqd` | S1 PASS (worked examples in the report) |
| Step 6 classical controls and primary endpoint | `skqd.controls` | S1 PASS (Table 3 reproduced) |
| Step 7 gauge-invariant importance model | `skqd.ml` (ridge on 16 features; the graph network is week-2 work) | ridge demonstration done (Spearman 0.86 / 0.89) |
| Step 8 noise simulation | `skqd.noise` (proxy), `skqd.circuits_qiskit.generic_noise_model` (Aer) | proxy done (Table 4 reproduced); Aer on the laptop (L4) |
| Step 9 hardware | prompts/07 | pending |
| Step 10 gates and error budget | `validation/gates.md` | E1–E3, S1 PASS; S2, S3, H0–H2, P1, M1 open |
| Sec. 11 timeline and Plan B | prompts/08 | one-month plan |

Numbers quoted from the manual in reports are always labelled "manual"; numbers computed here are stored in
`validation/*.json` / `data/*.json` and quoted from there.
