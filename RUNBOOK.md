# RUNBOOK — what to type, in order, to start running tests and move the project forward

Machine: the Dell G7 laptop (i7-8750H, GTX 1060 Max-Q, Omarchy), conda env `coding`.
Everything below is copy-pasteable.  Shell commands are in `bash` blocks; text to type into
Claude Code is in `text` blocks.  The rule everywhere: **a gate passes only when its script writes
`"status": "PASS"` into `validation/<GATE>.json`** — never because a model says so.

---

## Step 0 — unpack and check (5 min, no Claude needed)

```bash
cd ~/projects                      # or wherever you keep repos
unzip ~/Downloads/su2qc-skqd-v0.1.0.zip -d su2qc-skqd
cd su2qc-skqd
git log --oneline                  # 7 commits — the history is inside the zip

conda activate coding
pip install -r requirements.txt            # numpy, scipy: the physics core needs nothing else
python scripts/check_package.py            # must end with: PACKAGE OK
python scripts/run_tests_no_pytest.py      # 14 passed, 0 failed   (or: pytest -q tests)
```

If `check_package.py` does not print `PACKAGE OK`, stop and paste its output into Claude — something
did not survive the transfer.

---

## Step 1 — reproduce the four cloud gates on your laptop (gate L1, ~5 min)

```bash
mkdir -p validation/cloud && cp validation/*.json validation/cloud/   # keep the cloud numbers
python scripts/run_gate.py E1        # ~2-3 min: [G_a(x),H]=0 in the 160 000-dim space
python scripts/run_gate.py E2        # ~1 min: counts, codewords, decoder
python scripts/run_gate.py E3        # ~1 min: Table 1, static sectors, dt = pi/W
python scripts/run_gate.py S1        # ~2 min: emulation, certification, controls
```

Each prints a criteria table and `STATUS PASS`.  E1–E3 are deterministic: the values must match
`validation/cloud/*.json` to machine precision.  A difference there is a real finding (numpy/scipy
version behaviour) — do not adjust tolerances, escalate it (Step 6).

---

## Step 2 — GitHub: create the public repo and push (10 min)

```bash
gh auth status                      # must show you logged in as digonto10602
gh repo create digonto10602/su2qc-skqd --public --source=. --remote=origin --push
```

Without `gh`: create an empty public repo `su2qc-skqd` on github.com, then

```bash
git remote add origin https://github.com/digonto10602/su2qc-skqd.git
git push -u origin main             # or master — check: git branch --show-current
```

From now on every passed gate is pushed with `python scripts/run_gate.py <GATE> --push`.
Check that the GitHub Actions run (`.github/workflows/ci.yml`: tests + E1 + E2 + E3 + S1-quick) is green.

---

## Step 3 — install the quantum stack (10 min)

```bash
pip install -r requirements-laptop.txt     # qiskit, qiskit-aer, pytest, matplotlib
python -c "import qiskit, qiskit_aer; print(qiskit.__version__, qiskit_aer.__version__)"

# optional GPU (GTX 1060 Max-Q is sm_61, supported by Aer's GPU statevector):
pip install qiskit-aer-gpu
python -c "from qiskit_aer import AerSimulator; print(AerSimulator().available_devices())"

# optional CUDA-Q — either the wheel or the container you already have working:
pip install cudaq
# docker run --gpus all -it -v $PWD:/workspace nvcr.io/nvidia/quantum/cuda-quantum:cu13-0.15.1
```

Qiskit and CUDA-Q were **never executed** in the cloud (PyPI was blocked there), so gates L2 and L5
are the first real test of `src/skqd/circuits_qiskit.py` and `circuits_cudaq.py`.  The numpy reference
(`src/skqd/reference_sim.py`, `circuits_ir.py`) is the oracle they are checked against, and it is verified.

---

## Step 4 — run the laptop gates with Claude Code

Start Claude Code in the repo (it reads `CLAUDE.md`, `.claude/agents/*`, `.claude/skills/gate/`):

```bash
cd ~/projects/su2qc-skqd
claude
```

The repo ships a `/gate` skill that runs a gate, reads the JSON, pushes on PASS and routes a failure to
the right agent.  Type these **one at a time**, waiting for each to finish:

```text
/gate L2
```

```text
/gate L3 --level 3 --heavy-hex 3
```

```text
/gate L4 --p2 3e-3 --budget-minutes 25
```

```text
/gate L5 --target nvidia
```

If you prefer plain commands instead of the skill:

```bash
python scripts/run_gate.py L2 --push
python scripts/run_gate.py L3 --level 3 --heavy-hex 3      # expected FAIL of the CZ budget, see below
python scripts/run_gate.py L4 --p2 3e-3 --budget-minutes 25
python scripts/run_gate.py L5 --target nvidia
```

What each one is:

| gate | what it proves | expected |
|---|---|---|
| L2 | Qiskit statevectors of all 28 2x2 circuits equal the numpy reference; noiseless Aer shots all decode | PASS |
| L3 | transpiled CZ count per coarse step (all-to-all and heavy-hex) | **FAIL is the expected result** — it measures the generic-synthesis baseline that gate S2 must beat; push the numbers anyway |
| L4 | Aer noise model → yield, support recall, certified interval; applies the 30-minute rule by scaling shots | PASS |
| L5 | CUDA-Q on the GPU, after two convention tests (result-string order, `register_operation` endianness) | PASS |

Before starting each one you can have Claude read the matching prompt file, which states the pass
criteria and the escalation rule:

```text
Read prompts/02_laptop_L2_qiskit_check.md and execute it exactly, then report the JSON status.
```

---

## Step 5 — the real open problem (gate S2): structured circuits within the CZ budget

This is the one piece of genuine work left before hardware.  The exact hopping terms are currently
generic 6–11-qubit block unitaries; the budget is $\le 250$ CZ per coarse step at 2×2 and $\le 500$ at 2×3.
The structure that makes it possible is already computed (`reports/circuit_structure.md`,
`validation/CS.json`): each hopping term flips at most four qubits, connects chains of at most three (2×2)
or four (2×3) configurations, and has only 3–6 distinct matrix-element magnitudes — a handful of
controlled Givens rotations, not a dense unitary.  The 2×2 plaquette is already solved this way
(a 30-CNOT pair rotation $W+W^\dagger = D\,X^{\otimes 8}$).

In Claude Code:

```text
Read prompts/06_S2b_plaquette_interior_and_hopping_decomposition.md, reports/circuit_structure.md
and src/skqd/circuits_ir.py. Use the executor-opus agent at high effort to implement the structured
hopping gates first (2x2 only), verify them against skqd.reference_sim.local_unitary on 20 random
physical states for theta in {dt, 2dt, 4dt} to 1e-10, add the test to tests/test_circuits_ir.py,
and re-measure the CZ count with scripts/laptop_L3_cz_counts.py before touching the 2x3 plaquettes.
```

Do 2×2 hopping first and only then the 2×3 interior-corner plaquettes — the prompt says the same, and
it keeps each verification cheap.

---

## Step 6 — when a gate fails

`scripts/run_gate.py` writes `validation/BLOCKED.md` with the failing criteria.  Then, in Claude Code:

```text
A gate failed. Read validation/BLOCKED.md and validation/<GATE>.json, then use the planner-fable
agent at max effort to diagnose it and write the fix prompt as prompts/NN_<gate>_fix_<date>.md
following prompts/ESCALATION_TEMPLATE.md. Do not change any physics convention without saying so
explicitly, and do not relax a tolerance to make a gate pass.
```

Then hand the fix prompt to the executor:

```text
Execute prompts/NN_<gate>_fix_<date>.md with the executor-opus agent at high effort. Re-run the gate
and, if src/skqd physics changed, re-run E1, E2 and E3 as well.
```

Model routing (why it is set up this way: Fable is the expensive one, so it only plans and unblocks):

| task | agent | model | effort |
|---|---|---|---|
| plan a step, diagnose a blocked gate, physics decision | `planner-fable` | Fable 5.1 | max |
| implement code, decompositions, analysis | `executor-opus` | Opus | high |
| review a passed gate before the push | `reviewer-opus` | Opus | medium |
| run gates, tests, transpilations | `runner-sonnet` | Sonnet | low |
| update status tables and logs | `scribe-haiku` | Haiku | low |

Escalate effort inside a model once (`high` → `xhigh`) before escalating the model.

---

## Step 7 — keeping the bookkeeping straight

```bash
python scripts/update_status.py     # regenerates validation/gates.md and reports/PROJECT_STATUS.md
make check                          # package check
make test                           # tests
make gates                          # E1 + E2 + E3 + S1
```

After every gate, append one line to `prompts/LOG.md` (prompt file, gate, result, commit, notes).
In Claude Code the scribe does it:

```text
Use the scribe-haiku agent to update reports/PROJECT_STATUS.md, validation/gates.md and
prompts/LOG.md from the validation JSONs. It must not change any number.
```

---

## Suggested first session, end to end

```bash
cd ~/projects/su2qc-skqd && conda activate coding
pip install -r requirements.txt && python scripts/check_package.py && python scripts/run_tests_no_pytest.py
python scripts/run_gate.py E1 && python scripts/run_gate.py E2 && python scripts/run_gate.py E3 && python scripts/run_gate.py S1
gh repo create digonto10602/su2qc-skqd --public --source=. --remote=origin --push
pip install -r requirements-laptop.txt
claude
```

then, inside Claude Code:

```text
/gate L2
```

That is the whole first day: the physics core reproduced on your machine, the repo public, and the
first circuit-level gate run.  The four-week plan from there is `prompts/08_month_plan_and_reporting.md`.
