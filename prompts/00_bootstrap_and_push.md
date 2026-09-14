# 00 — Bootstrap: check the package, create the public GitHub repository, push
executor: runner-sonnet   effort: low   (planner-fable only if check_package.py reports something missing)
time budget: 15 min   machine: laptop (Dell G7, i7-8750H, GTX 1060 Max-Q, Omarchy)

## Goal
Make sure the delivered package is complete and every cloud-verified gate really says PASS, then put it on
GitHub as the public repository `digonto10602/su2qc-skqd` and push.  From now on every passed gate is pushed
from this machine (`scripts/run_gate.py <GATE> --push`).

## Inputs
- the unpacked package directory (`su2qc-skqd/`), `CLAUDE.md`, `reports/PROJECT_STATUS.md`
- GitHub CLI `gh` authenticated as digonto10602 (`gh auth status`), or a personal access token with `repo` scope

## Steps
1. `cd su2qc-skqd && python scripts/check_package.py` — must end with `PACKAGE OK` and list E1, E2, E3, S1 as PASS.
   If anything is missing, stop and hand the output to planner-fable.
2. Create the Python environment (the `coding` conda/mamba env is fine):
   `pip install -r requirements.txt` (numpy, scipy — the physics core needs nothing else) then
   `pip install -r requirements-laptop.txt` (qiskit, qiskit-aer, pytest; qiskit-aer-gpu and cudaq are optional
   and handled in prompts 02 and 05).
3. `pytest -q tests` — 14 tests, < 1 minute.  (Fallback without pytest: `python scripts/run_tests_no_pytest.py`.)
4. Create the repository and push (the repo is initialised with commits already):
   ```
   gh repo create digonto10602/su2qc-skqd --public --source=. --remote=origin --push
   ```
   or, without gh: create an empty public repo `su2qc-skqd` on github.com, then
   `git remote add origin https://github.com/digonto10602/su2qc-skqd.git && git push -u origin main`.
5. Check that GitHub Actions ran `.github/workflows/ci.yml` (tests + gates E2/E3 quick) and is green.
6. Append to `prompts/LOG.md`: date, machine, commit hash, "00 done".

## Pass criteria
- `python scripts/check_package.py` exit code 0
- `pytest` reports 14 passed
- `git remote -v` shows origin = https://github.com/digonto10602/su2qc-skqd.git and `git status` is clean after the push
- the CI run is green (or, if the runner has no GPU/Qiskit, at least the tests job is green)

## Outputs
public repository online; prompts/LOG.md entry.  Push: yes.

## Escalation
Environment problems (pip, conda) → retry with the `coding` env; if `pytest` fails on the laptop although
the package check passed, copy the traceback into validation/BLOCKED.md and call planner-fable (this would
mean a numpy/scipy version difference — the gates were computed with numpy 2.4.4 / scipy 1.17.1).
