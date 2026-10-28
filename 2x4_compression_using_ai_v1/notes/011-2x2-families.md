# 011 — 2x2 compressed families (owner request 2026-10-28)

- Date: 2026-10-28.  Author: genie-opus.  Plan in force: this note (the owner's words relayed by the coordinator:
  "make the 2x2 compressed family"); naming/separation rule `notes/008`; loader contract `notes/009`.
- Scope: build `compressed_circuit_llm_2x2_classA` and `compressed_circuit_llm_2x2_classB` the same way as the 2x3
  families, verify them at the package bar, convert them to Quantinuum native gates and export them in the on-disk
  format of `data/quantinuum/circuits_2x2` so that a separate agent can run the syntax checker.  No Nexus submission,
  no CI, no push.  The families are NOT substituted for the package's frozen 2x2 circuits anywhere (`notes/008`).

## Steps (all run; numbers in `data/c2x2/summary_2x2.json`)

1. Code (study folder only): `Problem(lx=2)` reads $dt$ from all 28 frozen 2x2 manifests and checks it bit for bit
   against `Model(2).reference(4, 2B).dt`; `Problem.tag` zero-pads the reference to two digits like the package's
   `circuit_id` (`B0_ref06_k1`; 2x3/2x4 ids unchanged, all their references are $\ge 10$); `archive_path("L2_*")` ->
   `data/c2x2/`; eval/Aer/native/certify scripts write 2x2 outputs to `data/c2x2/`; `families.py` registers the two
   names (no existing family changed).
2. Loop (`scripts/loop_select.py --lx 2 --label L2_it1`), the it6 proposal set of the sandbox (`examples/2x2_sandbox`):
   class A `full_lin, framed_lin, bframed_lin, bframed_lin_milp, jwc_bframed, jwc_framed, cb0, cb1, cb0_jwc, cb1_jwc,
   cfg_lin, cfg_t_lin, cfg_lin_milp`; class B `rpkg_lin, cfg_lin, cfg_t_lin, cfg_lin_milp, bframed_lin, framed_lin,
   jwc_bframed, jwc_framed, cb0, cb1, cb0_jwc, cb1_jwc, cb0p, cb1p`.  Archive `data/c2x2/archive_L2_it1.json`.
3. Verification: `eval_family.py --lx 2 --family arch:L2_it1:<operator|input>:pp2 --kmax 4 --prune-tau 1e-15`
   (certified pruned, rounding term included); `certify_family.py --lx 2` (MILP minimum Walsh support);
   `freeze_family.py --lx 2 --kmax 4 --version v1`; `verify_aer_family.py --superposition-seeds 11,12` (independent
   Aer statevector on all 28 + random-superposition operator test on all 28 circuits x 2 seeds; class B is the
   expected-failure control).
4. Native: `native_family.py` (pytket venv, level 0, `cz -> cp(pi)`, Q1L) and the new
   `scripts/export_quantinuum_family.py` (pytket venv): exports `data/families/native_2x2/<family>/` with `index.json`,
   `<id>.json` (pytket JSON, `json.dumps(to_json, sort_keys=True)`), `<id>.qasm`, `<id>.manifest.json`, and the frozen
   `CAL_zeros` / `CAL_x0` copied byte for byte; refuses to write a circuit that fails Q1 against the exact target or Q1L.
5. Local dry run of the package's `scripts/quantinuum_submit.py --dry-run --all --circuits <export dir>` (pytket venv,
   no login, no network) into the job tmp dir; session records copied to `data/c2x2/dryrun/`.
6. `scripts/summarise_2x2.py` -> `data/c2x2/summary_2x2.json` (all numbers of the report, incl. the frozen 2x2
   family's gate-only $f$ by the same formula).

## Result in one paragraph (numbers from `data/c2x2/summary_2x2.json`)

Class A: 245 ZZ on all 28 circuits, two-qubit depth 188 (frozen 2x2: 252 ZZ, depth 201).  Class B: 55–162 ZZ (mean
119.4), depth 45–137.  Both pass every check at the package bar.  **Class A does not raise the gate-only clean-shot
fraction on H2-2**: $f=0.79287$ against the frozen family's $0.79288$, because pytket level 0 leaves 623 PhasedX gates
against the frozen family's 405–425 (the frozen route squashed one-qubit gates with Qiskit opt-3 first); the 7 ZZ saved
are paid back by the extra one-qubit gates.  Class B reaches $f$ 0.854–0.941 (mean 0.888) on H2-2.
