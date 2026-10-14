"""
Order-kept, budgeted Aer sampling for the 2x3 campaign (prompts/33 sections 1.3 and 2.3).

* Chunks.  Every circuit's N_c shots are cut at the gate_CV prefix points round(phi N_c), phi in
  {1/16, 1/8, 1/4, 1/2, 1} (gate_CV.PHI and gate_CV.rnd), and every segment is further cut into chunks
  of at most `max_chunk` shots (476 = the 20-qubit one-call memory bound of gate S3; 16 in the laptop
  dry run).  Each chunk's counts are kept separately, so every prefix the CV criteria read is an exact
  sum of chunks (nested by construction).  This keeps the prompt's purpose for the chunk rule
  "chunk <= min(476, ceil(N_c/16))" with fewer run() calls: the boundaries are placed at the prefix
  points instead of every N_c/16 shots (recorded as `chunk_rule` in every JSON).
* Seeds.  Chunk i of circuit c uses tokens.chunk_seed(s0, c, i, stride) with i the chunk's index in the
  UNSPLIT chunk plan (chunk_plan numbers its chunks, part_plan keeps the numbers: prompts/33b R4) and stride =
  the largest chunk (an unsplit run) or the sizing's chunk (a part of a split run, given explicitly), so the
  parts of a split run concatenate to the unsplit run seed for seed.  Aer seeds shot j of a call with seed + j,
  so chunks never share a shot stream.  An out-of-memory chunk is split in two calls with seeds
  (seed, seed + a): the SAME shot stream as the unsplit chunk.
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
    """[(start, size, index)] covering [0, n_shots) with boundaries at the prefix points and sizes <= max_chunk;
    `index` numbers the chunks of this (unsplit) plan 0, 1, ... -- the chunk index of the seed rule (prompts/33b
    R4), kept by part_plan for the pieces of a split run."""
    n = int(n_shots)
    if n <= 0:
        return []
    cuts = sorted({rnd(p * n) for p in phis if rnd(p * n) > 0} | {n})
    out, a = [], 0
    for b in cuts:
        while a < b:
            s = min(int(max_chunk), b - a)
            out.append((a, s, len(out)))
            a += s
    return out


def split_ranges(n_shots: int, max_chunk: int, parts: int, phis=PHI) -> list:
    """prompts/33a step D: [(start, end)] of `parts` consecutive pieces of the unsplit chunk plan of n_shots,
    each boundary the first chunk start >= i n_shots / parts (rounded UP to a chunk boundary), so that the
    concatenated parts are exactly the unsplit chunk plan and every gate_CV prefix point stays a boundary."""
    plan = chunk_plan(n_shots, max_chunk, phis)
    starts = [a for a, _s, _i in plan] + [int(n_shots)]
    cuts = [0]
    for i in range(1, int(parts)):
        x = i * float(n_shots) / int(parts)
        cuts.append(min(s for s in starts if s >= x))
    cuts.append(int(n_shots))
    return [(cuts[i], cuts[i + 1]) for i in range(int(parts))]


def part_plan(n_shots: int, max_chunk: int, start: int, end: int, phis=PHI) -> list:
    """The chunks [(start, size, index)] of the unsplit plan of n_shots that lie in [start, end) (exact cover);
    `index` is the chunk's number in the UNSPLIT plan (the seed rule's chunk index, prompts/33b R4)."""
    p = [(a, s, i) for a, s, i in chunk_plan(n_shots, max_chunk, phis) if start <= a < end]
    if sum(s for _a, s, _i in p) != int(end) - int(start) or (p and p[0][0] != int(start)):
        raise ValueError(f"[{start}, {end}) is not a union of chunks of the plan of {n_shots} at {max_chunk}")
    return p


def ranges_list(r) -> list:
    """A part's piece of one circuit as [[a, b], ...]: the 33a form [a, b] (one contiguous range), or (prompts/33b,
    a chunk-packed part) a list of ranges [[a1, b1], [a2, b2], ...], possibly empty."""
    r = list(r)
    if not r:
        return []
    if isinstance(r[0], (list, tuple)):
        return [[int(a), int(b)] for a, b in r]
    return [[int(r[0]), int(r[1])]]


def range_shots(r) -> int:
    return sum(b - a for a, b in ranges_list(r))


def part_plan_ranges(n_shots: int, max_chunk: int, r, phis=PHI) -> list:
    """The chunks [(start, size, index)] of the unsplit plan covered by a part's range(s) of one circuit (each
    range an exact union of chunks; part_plan), in start order."""
    out = [t for a, b in ranges_list(r) for t in part_plan(n_shots, max_chunk, a, b, phis)]
    return sorted(out)


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
        elif mode == "native":            # prompts/33d R3: Aer's own GPU statevector kernels, no cuStateVec
            kw.update(cuStateVec_enable=False, batched_shots_gpu=False)
        elif mode == "custatevec_nofusion":   # prompts/33d R3: C2_CAL's path with gate fusion off
            kw.update(cuStateVec_enable=True, batched_shots_gpu=False, fusion_enable=False)
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


def call_bound(point, shots: int) -> float:
    """Upper bound on the wall time of one run() call of `shots` shots from one measured call `point` =
    (s_p, t_p) of the same circuit, under the call model t(s) = c + b s with c, b >= 0 (per-call set-up c,
    per-shot cost b):  t(s) <= t_p max(1, s / s_p).  For s >= s_p it is the line through the origin and the
    point (>= c + b s because c s / s_p >= c); for s <= s_p, t(s) <= t(s_p).  The bound is tight when the
    point was measured at the call size itself, and overstates a set-up-dominated call by up to s / s_p --
    a 1-shot point (the warmup) overstates a 128-shot call by up to 128x (the C2_CAL run-2 bug, job 59570318:
    RM 12.27 s, Kraus 13.19 s for one shot on the A100, read as 12-13 s PER SHOT)."""
    s_p, t_p = point
    return float(t_p) * max(1.0, float(shots) / float(s_p))


class Sampler:
    """Chunk-major, budgeted sampling of a list of circuits with per-chunk counts.

    Deadline rule (the fix of the C2_CAL run-2 zero-shot arms, job 59570318).  The time of the next round is
    the sum over its calls of `call_bound` from the best measured point of each circuit: its own largest
    completed chunk, else (round 0) the largest discarded probe of circuit 0, else the per-shot `rate_hint`.
    Before round 0, without a hint, a discarded 1-shot warmup is the first point; when its bound does not fit
    the deadline, discarded probes of increasing size (each pessimistically costing <= PROBE_SHARE of the
    time left, at most the largest round-0 call) replace it until the bound fits or no larger probe is
    affordable.  A round is never started whose bound exceeds the deadline, so the protection against a
    per-shot-dominated channel (Kraus relaxation on a CPU: t(s) ~ b s) is kept, and a set-up-dominated one
    (the A100: c >> b) is no longer stopped on a 1-shot extrapolation.  Every probe and every stop is logged
    and recorded."""

    WARMUP_CIRCUIT_INDEX = 999       # seed slot of the discarded 1-shot rate probe (no token has 999 circuits)
    PROBE_SHARE = 0.1                # a probe's pessimistic cost is at most this share of the time left
    MAX_PROBES = 3

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

    def _timed(self, circ, shots, seed):
        """One discarded probe call (circuit 0's simulator); returns its wall time."""
        t0 = time.time()
        res = self._sim(0).run(circ, shots=int(shots), seed_simulator=int(seed)).result()
        if not res.success:
            raise RuntimeError(f"probe call failed: {getattr(res, 'status', '')}")
        return time.time() - t0

    def _probe(self, circuits, plans, stride):
        """Before round 0 without a rate hint: the discarded 1-shot warmup (as before, same seed), then, only
        if its call_bound for round 0 does not fit the deadline, discarded probes of increasing size (seeds in
        the WARMUP_CIRCUIT_INDEX slot, chunk index i >= 1, stride = the largest chunk: disjoint from the
        warmup and from every real chunk).  Returns the bounding point (shots, seconds)."""
        seed0 = T.chunk_seed(self.s0, self.WARMUP_CIRCUIT_INDEX, 0, 1)
        tw = self._timed(circuits[0], 1, seed0)
        self.warmup = {"shots": 1, "seconds": tw, "discarded": True, "seed": seed0, "probes": [],
                       "probe_rule": f"call_bound from the largest probe; a probe costs <= {self.PROBE_SHARE} of the "
                                     f"time left at its pessimistic bound, at most {self.MAX_PROBES} probes, size <= "
                                     "the largest round-0 call"}
        point = (1, tw)
        round0 = [p[0][1] for p in plans if p]
        s_max = max(round0)
        for i in range(1, self.MAX_PROBES + 1):
            need = sum(call_bound(point, s) for s in round0)
            left = self.deadline - time.time()
            if need <= left or point[0] >= s_max:
                break
            s_p = min(s_max, int(self.PROBE_SHARE * left * point[0] / point[1]))
            if s_p <= point[0]:
                break
            seed = T.chunk_seed(self.s0, self.WARMUP_CIRCUIT_INDEX, i, max(s_max, stride))
            try:
                tp = self._timed(circuits[0], s_p, seed)
            except Exception as exc:
                if not is_oom(exc):
                    raise
                self.warmup["probes"].append({"shots": int(s_p), "seed": int(seed), "oom": str(exc)[:200]})
                self.log(f"rate probe of {s_p} shots ran out of memory; the bound keeps the {point[0]}-shot point")
                break
            self.warmup["probes"].append({"shots": int(s_p), "seconds": tp, "seed": int(seed), "discarded": True,
                                          "round0_bound_before_s": need, "seconds_left_before": left})
            self.log(f"rate probe {i}: {s_p} shots in {tp:.2f} s (the {point[0]}-shot bound {need:.1f} s for round 0 "
                     f"exceeded the {left:.1f} s left)")
            point = (s_p, tp)
        self.warmup["bounding_point"] = {"shots": int(point[0]), "seconds": float(point[1])}
        return point

    def _round_bound(self, out, plans, todo, j, probe_point):
        """call_bound summed over the calls of round j: each circuit from its own largest completed chunk
        (slowest of that size), else circuit 0's probe point, else the per-shot rate hint."""
        need, basis = 0.0, set()
        for c in todo:
            s = plans[c][j][1]
            chs = out[c]["chunks"]
            if chs:
                big = max(ch["shots"] for ch in chs)
                tk = max(ch["seconds"] for ch in chs if ch["shots"] == big)
                need += call_bound((big, tk), s)
                basis.add("own chunks")
            elif probe_point is not None:
                need += call_bound(probe_point, s)
                basis.add(f"probe {probe_point[0]} shots")
            elif self.rate_hint is not None:
                need += float(self.rate_hint) * s
                basis.add("rate hint")
        return need, ", ".join(sorted(basis)) or "none"

    def run(self, circuits: list, shots: list, labels: list, circuit_offset: int = 0, plans: list = None,
            stride: int = None):
        """Sample circuits[c] for shots[c] shots.  Returns per circuit {label, plan, chunks: [{start, shots,
        index, seed, counts}], shots_done} and the info block.  Circuit c's seeds use index circuit_offset + c.
        plans: an explicit [(start, size, index)] list per circuit (prompts/33a step D: part i of a split run
        samples the chunks of the unsplit chunk plan that lie in its range; `shots` is then their sum; `index` is
        the chunk's number in the unsplit plan, prompts/33b R4).  stride: the seed stride -- the sizing's chunk
        for a part of a split run (prompts/33b R4); default the largest chunk of `plans` (an unsplit run, as
        before).  The seed of a chunk is tokens.chunk_seed(s0, circuit_offset + c, index, stride)."""
        if plans is None:
            plans = [chunk_plan(n, self.max_chunk, self.phis) for n in shots]
        plans = [[(int(t[0]), int(t[1]), int(t[2]) if len(t) > 2 else j) for j, t in enumerate(p)] for p in plans]
        stride = int(stride) if stride is not None else max([t[1] for p in plans for t in p] or [1])
        big = max([t[1] for p in plans for t in p] or [0])
        if big > stride:
            raise ValueError(f"seed stride {stride} below the largest chunk {big}: chunks would share shot streams")
        out = [{"label": lab, "requested": int(n), "chunks": [], "shots_done": 0} for lab, n in zip(labels, shots)]
        n_rounds = max([len(p) for p in plans] or [0])
        probe_point = None                      # (shots, seconds) of the largest discarded probe of circuit 0
        if self.deadline is not None and self.rate_hint is None and circuits and n_rounds > self.min_rounds:
            probe_point = self._probe(circuits, plans, stride)
        t_start = time.time()
        done_shots, stopped = 0, None
        for j in range(n_rounds):
            todo = [c for c, p in enumerate(plans) if j < len(p)]
            if self.deadline is not None and j >= self.min_rounds:
                need, basis = self._round_bound(out, plans, todo, j, probe_point)
                left = self.deadline - time.time()
                if need > left:
                    stopped = {"round": j, "reason": "deadline", "predicted_round_s": need,
                               "seconds_left": left, "bound_basis": basis,
                               "rate_s_per_shot": need / max(1, sum(plans[c][j][1] for c in todo)),
                               "rule": "call_bound: t(s) <= t_p max(1, s / s_p) from the measured point"}
                    self.log(f"deadline stop before round {j}: predicted {need:.1f} s > {left:.1f} s left "
                             f"(basis {basis}); {done_shots} shots done")
                    break
            for c in todo:
                a, s, gi = plans[c][j]
                seed = T.chunk_seed(self.s0, circuit_offset + c, gi, stride)
                t_c = time.time()
                counts = self._run(circuits[c], s, seed, c)
                out[c]["chunks"].append({"start": int(a), "shots": int(s), "index": int(gi), "seed": int(seed),
                                         "counts": counts, "seconds": time.time() - t_c})
                out[c]["shots_done"] += int(s)
                done_shots += int(s)
        wall = time.time() - t_start
        info = {"calls": self.calls, "oom_retries": list(self.oom_retries), "stride": int(stride), "s0": self.s0,
                "circuit_offset": int(circuit_offset), "max_chunk": self.max_chunk,
                "chunk_rule": CHUNK_RULE if self.phis == PHI else
                f"plain chunks of <= max_chunk shots with boundaries at phi in {list(self.phis)} of N_c",
                "rounds": n_rounds,
                "stopped": stopped, "wall_s": wall, "shots_done": int(done_shots),
                "seconds_per_shot": wall / done_shots if done_shots else None,
                "warmup": self.warmup, "seed_rule": T.SEED_RULE}
        return out, info


def sample_noiseless_memory(sim, circ, shots: int, seed: int):
    """One noiseless call with memory=True: the per-shot outcomes in order (ints, bit k = clbit k)."""
    res = sim.run(circ, shots=int(shots), seed_simulator=int(seed), memory=True).result()
    mem = res.get_memory(0)
    return np.fromiter((int(m.replace(" ", ""), 2) for m in mem), dtype=np.int64, count=len(mem))
