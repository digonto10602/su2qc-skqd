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
ADDED = ["C2_KCHK"]                                     # prompts/33d R3: appended after the slots
LATER = [f"QV_2x4_{k:02d}" for k in range(1, 9)]          # prompts/35 3.1(g) + 35b section 4: appended after C2_KCHK


def test_table_is_complete_and_in_the_order_of_section_1_5():
    tok = T.load_tokens()
    assert list(tok)[:33] == EXPECTED and list(T.campaign_tokens()) == EXPECTED + ADDED
    assert list(tok)[33:53] == SLOTS and list(T.slot_tokens()) == SLOTS
    assert list(tok)[53:54] == ADDED, "prompts/33d: C2_KCHK appended (no index moves)"
    assert list(tok)[54:] == LATER, "tokens appended for prompts/35 come after C2_KCHK, in order"


def test_every_entry_is_valid():
    for t, v in T.load_tokens().items():
        if t in LATER:
            continue
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
    # the 33 lines of prompts/33 7a, then the line prompts/33d section 4 adds (C2_KCHK)
    assert T.allowlist_text().splitlines()[:33] == lines[i:i + 33]
    assert T.allowlist_text().splitlines()[33:] == ["C2_KCHK      01:00:00 1"]


def test_env_files():
    for t, e in T.env_files().items():
        assert open(os.path.join(ROOT, "jobs", "env", t)).read().strip() == e
    s = open(os.path.join(ROOT, "jobs", "gate.sbatch")).read()
    assert 'jobs/env/${CI_GATE' in s and 'conda activate "$CI_ENV"' in s and "CI_ENV=skqd" in s
    # the job line (prompts/33e R1 adds --cpus-per-task to it; tests/test_ci_gpu_mode.py pins that part)
    assert 'python scripts/run_gate.py "$CI_GATE"' in s and s.count("srun ") == 1


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


def test_qv_2x4_appended_without_moving_any_campaign_token():
    """prompts/35 3.9 + 35b section 4: the QV_2x4_01..08 append keeps every campaign-33 token index (hence base seed)."""
    tok = T.load_tokens()
    for i, t in enumerate(EXPECTED + SLOTS + ADDED):
        assert T.token_index(t, tok) == i and T.base_seed(t, tok) == T.BASE_SEED + T.SEED_PER_TOKEN * i
    assert T.token_index("C4_PART_20", tok) == 52 and T.token_index("C2_KCHK", tok) == 53
    for j, t in enumerate(LATER):
        assert T.token_index(t, tok) == 54 + j
        v = tok[t]
        assert v["script"] == "scripts/quantinuum_lattice_tests.py"
        assert v["args"] == ["--lattice", "4", "--tier", "gpu-verify", "--slot", f"{j + 1:02d}"]
        assert os.path.exists(os.path.join(ROOT, "ci", "parts", t + ".json")), "every slot has its part file"
        assert (v["class"], v["walltime"], v["gpus"], v["env"]) == (3, "01:00:00", 1, "skqd")
        assert 0 < v["estimate_minutes"] * 60 < T.walltime_seconds(v["walltime"])
        assert t not in T.campaign_tokens() and t not in T.slot_tokens()
    assert open(os.path.join(ROOT, "ci", "allowed_jobs.q35")).read() == "".join(f"{t}   01:00:00 1\n" for t in LATER)
    import run_gate
    assert run_gate.resolve("QV_2x4_03") == (os.path.join(ROOT, "scripts", "quantinuum_lattice_tests.py"),
                                             ["--lattice", "4", "--tier", "gpu-verify", "--slot", "03"])
