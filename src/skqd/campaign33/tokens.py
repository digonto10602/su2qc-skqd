"""
The 33 job tokens of the 2x3 four-class campaign (prompts/33 section 1.5) and what is derived from
them: the allowlist lines the owner appends on Perlmutter (section 7a), the conda env per token
(`jobs/env/<TOKEN>`), and the base seed of every token (section 2.3).

`scripts/gate_tokens.json` is the single source.  Nothing here imports qiskit.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TOKENS_FILE = os.path.join(ROOT, "scripts", "gate_tokens.json")
ALLOWLIST_FILE = os.path.join(ROOT, "ci", "allowed_jobs.campaign33")
ENV_DIR = os.path.join(ROOT, "jobs", "env")
VALID_ENVS = ("skqd", "skqd-pecos", "skqd-selene")
MAX_WALLTIME_S = 3600
BASE_SEED = 33_000_000           # prompts/33 2.3: s0 = 33 000 000 + 1e5 x token index
SEED_PER_TOKEN = 100_000
SEED_PER_CIRCUIT = 1_000
# The Aer seed of chunk i of circuit c is  s0 * 10^4 + c * 10^6 + i * stride  (see chunk_seed): the
# literal rule of prompts/33 2.3 (s0 + 1e3 c + i stride) is NOT disjoint once a circuit takes more
# than 1000 shots (circuit c's chunks run into circuit c+1's) or a token spans more than 1e5 seeds
# (the a/b halves of an S3-quota run: 32 circuits x 3125 shots = 1.0e5 seeds per half), and Aer
# seeds shot j with seed + j, so overlapping ranges are correlated samples.  Scaling s0 by 10^4
# keeps s0 as the token's label and makes every range disjoint by construction:
# tokens 10^9 apart, circuits 10^6 apart (< 1000 circuits), chunks `stride` apart (<= 10^6 shots).
SEED_SCALE = 10_000
CIRCUIT_SEED_SPAN = 1_000_000
MAX_SHOTS_PER_CIRCUIT_SEEDED = CIRCUIT_SEED_SPAN
SEED_RULE = ("aer seed of chunk i of circuit c = s0 * 1e4 + c * 1e6 + i * stride, stride = chunk size, "
             "s0 = 33 000 000 + 1e5 x token index (prompts/33 2.3 s0; the circuit/chunk offsets are widened "
             "from 1e3 c so that circuits, chunks, tokens and the a/b halves are disjoint for <= 1e6 shots per "
             "circuit: the literal s0 + 1e3 c + i stride overlaps above 1000 shots per circuit)")


def load_tokens(path: str = TOKENS_FILE) -> dict:
    """{token: entry} in file order (the `_comment` key dropped)."""
    with open(path) as fh:
        d = json.load(fh)
    return {k: v for k, v in d.items() if not k.startswith("_")}


def walltime_seconds(w: str) -> int:
    h, m, s = (int(x) for x in w.split(":"))
    return 3600 * h + 60 * m + s


def allowlist_text(tokens: dict = None) -> str:
    """`TOKEN  MAX_WALLTIME  GPUS` lines, aligned as in prompts/33 section 7a."""
    tokens = load_tokens() if tokens is None else tokens
    width = max(len(t) for t in tokens) + 2
    lines = [f"{t:<{width}}{v['walltime']} {int(v['gpus'])}" for t, v in tokens.items()]
    return "\n".join(lines) + "\n"


def env_files(tokens: dict = None) -> dict:
    """{token: env} for every token whose env is not the default `skqd` (the jobs/env/ files)."""
    tokens = load_tokens() if tokens is None else tokens
    return {t: v["env"] for t, v in tokens.items() if v["env"] != "skqd"}


def token_index(token: str, tokens: dict = None) -> int:
    tokens = load_tokens() if tokens is None else tokens
    return list(tokens).index(token)


def base_seed(token: str, tokens: dict = None) -> int:
    """s0 = 33 000 000 + 1e5 x (token index in scripts/gate_tokens.json)."""
    return BASE_SEED + SEED_PER_TOKEN * token_index(token, tokens)


def circuit_seed(s0: int, circuit_index: int) -> int:
    """First Aer seed of circuit c in a token with base seed s0 (SEED_RULE)."""
    if not 0 <= int(circuit_index) < SEED_SCALE * SEED_PER_TOKEN // CIRCUIT_SEED_SPAN:
        raise ValueError(f"circuit index {circuit_index} outside the disjoint seed range")
    return int(s0) * SEED_SCALE + CIRCUIT_SEED_SPAN * int(circuit_index)


def chunk_seed(s0: int, circuit_index: int, chunk_index: int, stride: int) -> int:
    """Aer seed of chunk i of circuit c (SEED_RULE).  Aer seeds shot j of a call with seed + j, so
    chunks `stride` >= chunk size apart never share a shot stream; circuits are 1e6 apart and tokens
    1e9 apart, so nothing overlaps while a circuit takes <= 1e6 shots in one token."""
    if stride < 1:
        raise ValueError("stride must be >= 1")
    if (int(chunk_index) + 1) * int(stride) > CIRCUIT_SEED_SPAN:
        raise ValueError("more than 1e6 seeded shots for one circuit in one token: the seed ranges "
                         "would overlap the next circuit's")
    return circuit_seed(s0, circuit_index) + int(chunk_index) * int(stride)


def write_derived(tokens: dict = None) -> dict:
    """Write ci/allowed_jobs.campaign33 and jobs/env/<TOKEN> from the token table."""
    tokens = load_tokens() if tokens is None else tokens
    with open(ALLOWLIST_FILE, "w") as fh:
        fh.write(allowlist_text(tokens))
    os.makedirs(ENV_DIR, exist_ok=True)
    envs = env_files(tokens)
    for t, e in envs.items():
        with open(os.path.join(ENV_DIR, t), "w") as fh:
            fh.write(e + "\n")
    return {"allowlist": ALLOWLIST_FILE, "env_files": envs}


if __name__ == "__main__":
    print(json.dumps(write_derived(), indent=1))
