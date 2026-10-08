"""
Order-kept, budgeted Aer sampling for the 2x3 campaign (prompts/33 sections 1.3 and 2.3).

* Chunks.  Every circuit's N_c shots are cut at the gate_CV prefix points round(phi N_c), phi in
  {1/16, 1/8, 1/4, 1/2, 1} (gate_CV.PHI and gate_CV.rnd), and every segment is further cut into chunks
  of at most `max_chunk` shots (476 = the 20-qubit one-call memory bound of gate S3; 16 in the laptop
  dry run).  Each chunk's counts are kept separately, so every prefix the CV criteria read is an exact
  sum of chunks (nested by construction).  This keeps the prompt's purpose for the chunk rule
  "chunk <= min(476, ceil(N_c/16))" with fewer run() calls: the boundaries are placed at the prefix
  points instead of every N_c/16 shots (recorded as `chunk_rule` in every JSON).
* Seeds.  Chunk i of circuit c uses tokens.chunk_seed(s0, c, i, stride) with stride = the largest chunk;
  Aer seeds shot j of a call with seed + j, so chunks never share a shot stream.  An out-of-memory chunk
  is split in two calls with seeds (seed, seed + a): the SAME shot stream as the unsplit chunk.
* Rounds and budget.  Calls are issued chunk-index-major (round j = chunk j of every circuit that has one),
  so a deadline stops at a round boundary with every circuit holding a complete prefix; the shots
  reached are recorded (`shots_reduced_to`), never extrapolated.
* One circuit per run() call, so every chunk has its own recorded seed (Aer derives undocumented seeds
  for the second and later experiments of a multi-circuit call).  Under the memory model a
  multi-circuit call holds proportionally fewer shots, so the number of calls is the same.

Works on qiskit 1.4.3 / aer 0.15.1 (the CI) and 2.5.2 / 0.17.2 (the laptop).
"""
from __future__ import annotations

import time

import numpy as np

from . import tokens as T

PHI = (1 / 16, 1 / 8, 1 / 4, 1 / 2, 1.0)
GPU_MODES = ("policy", "custatevec", "batched")
CHUNK_RULE = ("boundaries at round(phi N_c) for phi in (1/16, 1/8, 1/4, 1/2, 1) (gate_CV prefixes) and every "
              "chunk <= max_chunk shots; the prefix curves are exact sums of chunks")


def rnd(x):
    """gate_CV.rnd: floor(x + 0.5)."""
    return int(np.floor(float(x) + 0.5))


def chunk_plan(n_shots: int, max_chunk: int, phis=PHI) -> list:
    """[(start, size)] covering [0, n_shots) with boundaries at the prefix points and sizes <= max_chunk."""
    n = int(n_shots)
    if n <= 0:
        return []
    cuts = sorted({rnd(p * n) for p in phis if rnd(p * n) > 0} | {n})
    out, a = [], 0
    for b in cuts:
        while a < b:
            s = min(int(max_chunk), b - a)
            out.append((a, s))
            a += s
    return out


def split_ranges(n_shots: int, max_chunk: int, parts: int, phis=PHI) -> list:
    """prompts/33a step D: [(start, end)] of `parts` consecutive pieces of the unsplit chunk plan of n_shots,
    each boundary the first chunk start >= i n_shots / parts (rounded UP to a chunk boundary), so that the
    concatenated parts are exactly the unsplit chunk plan and every gate_CV prefix point stays a boundary."""
    plan = chunk_plan(n_shots, max_chunk, phis)
    starts = [a for a, _s in plan] + [int(n_shots)]
    cuts = [0]
    for i in range(1, int(parts)):
        x = i * float(n_shots) / int(parts)
        cuts.append(min(s for s in starts if s >= x))
    cuts.append(int(n_shots))
    return [(cuts[i], cuts[i + 1]) for i in range(int(parts))]


def part_plan(n_shots: int, max_chunk: int, start: int, end: int, phis=PHI) -> list:
    """The chunks [(start, size)] of the unsplit plan of n_shots that lie in [start, end) (exact cover)."""
    p = [(a, s) for a, s in chunk_plan(n_shots, max_chunk, phis) if start <= a < end]
    if sum(s for _a, s in p) != int(end) - int(start) or (p and p[0][0] != int(start)):
        raise ValueError(f"[{start}, {end}) is not a union of chunks of the plan of {n_shots} at {max_chunk}")
    return p


def make_simulator(device: str = "CPU", mode: str = "policy", noise_model=None, threads: int = 0,
                   batched_max_qubits: int = 24):
    """AerSimulator per the owner's HPC policy.  GPU modes:
      policy     cuStateVec_enable=True + batched_shots_gpu=True (the RUNBOOK line; at > 16 active qubits
                 Aer ignores the batching and runs the cuStateVec per-shot path -- what gate S3 measured)
      custatevec cuStateVec_enable=True, batched_shots_gpu=False
      batched    batched_shots_gpu=True with batched_shots_gpu_max_qubits raised (default 16 in Aer)
    CPU: statevector, double precision, `threads` (0 = Aer's default)."""
    from qiskit_aer import AerSimulator
    kw = dict(method="statevector", precision="double")
    if noise_model is not None:
        kw["noise_model"] = noise_model
    if device == "GPU":
        kw["device"] = "GPU"
        if mode == "policy":
            kw.update(cuStateVec_enable=True, batched_shots_gpu=True)
        elif mode == "custatevec":
            kw.update(cuStateVec_enable=True, batched_shots_gpu=False)
        elif mode == "batched":
            kw.update(cuStateVec_enable=False, batched_shots_gpu=True,
                      batched_shots_gpu_max_qubits=int(batched_max_qubits))
        else:
            raise ValueError(mode)
    else:
        kw["max_parallel_threads"] = int(threads)
    return AerSimulator(**kw), {k: (v if k != "noise_model" else "attached") for k, v in kw.items()}


def is_oom(exc) -> bool:
    t = str(exc).lower()
    return ("out of memory" in t or "bad_alloc" in t or "cudaerrormemoryallocation" in t
            or "insufficient memory" in t)


def counts_to_int(counts: dict) -> dict:
    """Aer counts keys ('0101...', clbit 0 rightmost, or hex) -> {int with bit k = clbit k: count}."""
    out = {}
    for k, v in counts.items():
        s = str(k).replace(" ", "")
        x = int(s, 16) if s.startswith("0x") else int(s, 2)
        out[x] = out.get(x, 0) + int(v)
    return out


class Sampler:
    """Chunk-major, budgeted sampling of a list of circuits with per-chunk counts."""

    WARMUP_CIRCUIT_INDEX = 999       # seed slot of the discarded 1-shot rate probe (no token has 999 circuits)

    def __init__(self, sim, s0: int, max_chunk: int, deadline: float = None, log=print, rate_hint: float = None,
                 min_rounds: int = 0, phis=PHI):
        self.sim, self.s0, self.max_chunk = sim, int(s0), int(max_chunk)
        self.deadline, self.log = deadline, log
        self.rate_hint = rate_hint
        self.min_rounds = int(min_rounds)      # rounds run regardless of the deadline (a dry run samples every unit)
        self.phis = tuple(phis)                # (1.0,) = plain chunks of max_chunk (class 2 reads no prefix curve)
        self.calls, self.oom_retries, self.call_seconds = 0, [], []
        self.warmup = None

    def _sim(self, c):
        """The simulator of circuit c: `sim` may be one AerSimulator or a list with one per circuit (class 2:
        each T2 convention has its own noise model)."""
        return self.sim[c] if isinstance(self.sim, (list, tuple)) else self.sim

    def _run(self, circ, shots, seed, c=0):
        """One chunk; on OOM split into halves with seeds (seed, seed + a) -- the same shot stream."""
        try:
            t0 = time.time()
            res = self._sim(c).run(circ, shots=int(shots), seed_simulator=int(seed)).result()
            if not res.success:
                raise RuntimeError(str(getattr(res, "status", "")))
            c = counts_to_int(res.get_counts(0))
            self.calls += 1
            self.call_seconds.append(time.time() - t0)
            return c
        except Exception as exc:
            if not is_oom(exc) or shots <= 1:
                raise
            a = shots // 2
            self.oom_retries.append({"shots": int(shots), "seed": int(seed), "split": [a, shots - a],
                                     "error": str(exc)[:200]})
            c1 = self._run(circ, a, seed, c)
            c2 = self._run(circ, shots - a, seed + a, c)
            for k, v in c2.items():
                c1[k] = c1.get(k, 0) + v
            return c1

    def run(self, circuits: list, shots: list, labels: list, circuit_offset: int = 0, plans: list = None):
        """Sample circuits[c] for shots[c] shots.  Returns per circuit {label, plan, chunks: [{start, shots,
        seed, counts}], shots_done} and the info block.  Circuit c's seeds use index circuit_offset + c.
        plans: an explicit [(start, size)] list per circuit (prompts/33a step D: part i of a split run samples
        the chunks of the unsplit chunk plan that lie in its range; `shots` is then their sum)."""
        if plans is None:
            plans = [chunk_plan(n, self.max_chunk, self.phis) for n in shots]
        plans = [list(p) for p in plans]
        stride = max([s for p in plans for _a, s in p] or [1])
        out = [{"label": lab, "requested": int(n), "chunks": [], "shots_done": 0} for lab, n in zip(labels, shots)]
        n_rounds = max([len(p) for p in plans] or [0])
        rate0 = self.rate_hint
        if self.deadline is not None and rate0 is None and circuits and n_rounds > self.min_rounds:
            # a discarded 1-shot call measures the rate before round 0 (otherwise the first round of a
            # slow channel -- Kraus relaxation at 21 qubits on a CPU -- could run far past the deadline)
            tw = time.time()
            self._sim(0).run(circuits[0], shots=1,
                         seed_simulator=T.chunk_seed(self.s0, self.WARMUP_CIRCUIT_INDEX, 0, 1)).result()
            rate0 = time.time() - tw
            self.warmup = {"shots": 1, "seconds": rate0, "discarded": True,
                           "seed": T.chunk_seed(self.s0, self.WARMUP_CIRCUIT_INDEX, 0, 1)}
        t_start = time.time()
        done_shots, stopped = 0, None
        for j in range(n_rounds):
            todo = [c for c, p in enumerate(plans) if j < len(p)]
            if self.deadline is not None and j >= self.min_rounds:
                rate = (time.time() - t_start) / done_shots if done_shots > 0 else rate0
                need = (rate or 0.0) * sum(plans[c][j][1] for c in todo)
                if time.time() + need > self.deadline:
                    stopped = {"round": j, "reason": "deadline", "predicted_round_s": need,
                               "rate_s_per_shot": rate}
                    break
            for c in todo:
                a, s = plans[c][j]
                seed = T.chunk_seed(self.s0, circuit_offset + c, j, stride)
                t_c = time.time()
                counts = self._run(circuits[c], s, seed, c)
                out[c]["chunks"].append({"start": int(a), "shots": int(s), "seed": int(seed), "counts": counts,
                                         "seconds": time.time() - t_c})
                out[c]["shots_done"] += int(s)
                done_shots += int(s)
        wall = time.time() - t_start
        info = {"calls": self.calls, "oom_retries": list(self.oom_retries), "stride": int(stride),
                "max_chunk": self.max_chunk,
                "chunk_rule": CHUNK_RULE if self.phis == PHI else
                f"plain chunks of <= max_chunk shots with boundaries at phi in {list(self.phis)} of N_c",
                "rounds": n_rounds,
                "stopped": stopped, "wall_s": wall, "shots_done": int(done_shots),
                "seconds_per_shot": wall / done_shots if done_shots else rate0,
                "warmup": self.warmup, "seed_rule": T.SEED_RULE}
        return out, info


def sample_noiseless_memory(sim, circ, shots: int, seed: int):
    """One noiseless call with memory=True: the per-shot outcomes in order (ints, bit k = clbit k)."""
    res = sim.run(circ, shots=int(shots), seed_simulator=int(seed), memory=True).result()
    mem = res.get_memory(0)
    return np.fromiter((int(m.replace(" ", ""), 2) for m in mem), dtype=np.int64, count=len(mem))
