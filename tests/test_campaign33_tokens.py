"""
prompts/33 A1: the campaign token table, the runner hook, the allowlist file and the env hook.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from skqd.campaign33 import tokens as T  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

EXPECTED = ["C1_IDEAL", "C2_CAL", "C2_GATE", "C2_ECHO", "C2_STAR", "C2_XY4", "C2_COH", "C3_AER", "C3_LE",
            "C3_SEL", "C4_FCELLS_A", "C4_FCELLS_B", "C4_F1_B0", "C4_F1_B1", "C4_F2_B0", "C4_F2_B1", "C4_F3_B0",
            "C4_F3_B1", "C4_F4_B0a", "C4_F4_B0b", "C4_F4_B1a", "C4_F4_B1b", "C4_F5_B0", "C4_F5_B1", "C4_F6_B0",
            "C4_F6_B1", "C4_F7_B0", "C4_F7_B1", "C4_F8_B0a", "C4_F8_B0b", "C4_F8_B1a", "C4_F8_B1b", "C4_CF"]


SLOTS = [f"C4_PART_{i:02d}" for i in range(1, 21)]      # prompts/33a step D1: appended after the 33


def test_table_is_complete_and_in_the_order_of_section_1_5():
    tok = T.load_tokens()
    assert list(tok)[:33] == EXPECTED and list(T.campaign_tokens()) == EXPECTED
    assert list(tok)[33:] == SLOTS and list(T.slot_tokens()) == SLOTS and len(tok) == 53


def test_every_entry_is_valid():
    for t, v in T.load_tokens().items():
        assert v["script"] == "scripts/campaign33.py" and v["args"] == ["--token", t]
        assert v["class"] == int(t[1]) and v["class"] in (1, 2, 3, 4)
        assert 0 < T.walltime_seconds(v["walltime"]) <= T.MAX_WALLTIME_S, t
        assert v["gpus"] == 1, "no 2-GPU line: no E(p) measurement exists (RUNBOOK)"
        assert v["env"] in T.VALID_ENVS
        assert v["estimate_minutes"] * 60 < T.walltime_seconds(v["walltime"])
    assert {t for t, v in T.load_tokens().items() if v["env"] != "skqd"} == {"C3_LE", "C3_SEL"}


def test_allowlist_file_is_generated_from_the_table():
    assert open(T.ALLOWLIST_FILE).read() == T.allowlist_text()


def test_allowlist_matches_prompt_section_7a():
    lines = open(os.path.join(ROOT, "prompts", "33_2x3_four_class_perlmutter_campaign.md")).read().splitlines()
    i = lines.index("C1_IDEAL     00:30:00 1")
    assert "\n".join(lines[i:i + 33]) + "\n" == T.allowlist_text()


def test_env_files():
    for t, e in T.env_files().items():
        assert open(os.path.join(ROOT, "jobs", "env", t)).read().strip() == e
    s = open(os.path.join(ROOT, "jobs", "gate.sbatch")).read()
    assert 'jobs/env/${CI_GATE' in s and 'conda activate "$CI_ENV"' in s and "CI_ENV=skqd" in s
    assert "srun python scripts/run_gate.py \"$CI_GATE\"" in s, "the job line is unchanged"


def test_run_gate_resolves_every_token():
    import run_gate
    for t in EXPECTED:
        script, args = run_gate.resolve(t)
        assert script == os.path.join(ROOT, "scripts", "campaign33.py") and args == ["--token", t]
    # existing gates still resolve to their own scripts, with no args
    assert run_gate.resolve("S3") == (os.path.join(ROOT, "scripts", "gate_S3.py"), [])
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "run_gate.py"), "C4_F8_B1b", "--resolve"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and r.stdout.strip() == "scripts/campaign33.py --token C4_F8_B1b"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "run_gate.py"), "_comment", "--resolve"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode != 0, "the table's comment key is not a token"


def test_driver_help_runs_for_the_resolved_command():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "campaign33.py"), "--help"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and "--token" in r.stdout


def test_seed_rule_is_disjoint():
    tok = T.load_tokens()
    a, b = T.base_seed("C4_F4_B0a", tok), T.base_seed("C4_F4_B0b", tok)
    assert b - a == T.SEED_PER_TOKEN and a == T.BASE_SEED + T.SEED_PER_TOKEN * EXPECTED.index("C4_F4_B0a")
    # the a half's last seed of its last circuit is below the b half's first seed
    last_a = T.chunk_seed(a, 43, 99, 10000)
    assert last_a + 10000 <= T.chunk_seed(b, 0, 0, 476)
    # circuits never overlap inside a token while a circuit takes <= 1e6 shots
    assert T.chunk_seed(a, 0, 2000, 476) + 476 <= T.chunk_seed(a, 1, 0, 476)
    import pytest
    with pytest.raises(ValueError):
        T.chunk_seed(a, 0, 3000, 476)
