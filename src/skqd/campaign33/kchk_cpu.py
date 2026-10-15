"""
C2_KCHK's CPU arms (prompts/33d R3): Kraus and RM on Aer's CPU statevector in a SEPARATE process, started first by
`tokens_run.run_c2_kchk` and run beside the GPU arms.  The two arms alternate in chunks of `--chunk` shots in the
pattern `--ratio K,R` (K Kraus chunks, then R RM chunks, repeated; run 1 of 33d: 1,1 = kraus, rm, kraus, ...; run 2 of
prompts/33e R2: 1,2 = kraus, rm, rm, kraus, ... with --chunk 1, so every completed shot is recorded).  Each arm runs
its chunks regardless of the deadline until it has `--min-shots`, then only while the predicted end of its next
chunk (its slowest chunk so far) is before `--deadline` (epoch seconds).  The JSON is rewritten after every chunk,
so a process stopped by the driver keeps every completed chunk.

Seeds (the token rule, tokens.chunk_seed): s0 of C2_KCHK, circuit offset per arm (`--offsets`), chunk index j,
stride = the chunk.  Raw counts of every chunk are kept ({int with bit k = clbit k: count}).

    python -m skqd.campaign33.kchk_cpu --out <json> --deadline <epoch> --s0 <s0> --threads <n>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time


def cpu_threads(requested: int = 0, reserve: int = 4) -> int:
    """prompts/33d R3: the node's CPUs minus `reserve` (the CPUs this process may run on, so a Slurm binding is
    respected); `requested` > 0 caps it (the laptop: the other executor's share)."""
    try:
        n = len(os.sched_getaffinity(0))
    except AttributeError:
        n = os.cpu_count() or 1
    t = max(1, n - int(reserve))
    return min(t, int(requested)) if requested and requested > 0 else t


def cpu_affinity():
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return None


def aer_distribution() -> dict:
    """Which wheel provides qiskit_aer here (prompts/33e R3 (a): `qiskit-aer-gpu` on the CI, `qiskit-aer` on the
    laptop -- the CPU statevector code is the same source, the wheel is not) and its version."""
    try:
        from importlib import metadata
        names = sorted(set(metadata.packages_distributions().get("qiskit_aer", [])))
        return {"distributions": names, "versions": {n: metadata.version(n) for n in names}}
    except Exception as exc:          # recorded, never fatal: the arms' numbers do not depend on it
        return {"distributions": None, "error": f"{type(exc).__name__}: {exc}"}


def pattern(arms, ratio) -> list:
    """The alternation of one cycle: ratio[i] consecutive chunks of arm i, in the order of `arms`."""
    out = []
    for name, r in zip(arms, ratio):
        if int(r) < 0:
            raise ValueError("ratio entries must be >= 0")
        out += [name] * int(r)
    if not out:
        raise ValueError("an empty alternation pattern")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--deadline", type=float, required=True)
    ap.add_argument("--s0", type=int, required=True)
    ap.add_argument("--offsets", default="610,611", help="circuit seed offsets of kraus_cpu, rm_cpu")
    ap.add_argument("--chunk", type=int, default=4)
    ap.add_argument("--min-shots", type=int, default=16)
    ap.add_argument("--max-shots", type=int, default=0, help="per arm (0 = until the deadline)")
    ap.add_argument("--threads", type=int, default=0, help="cap on the thread count (0 = CPUs minus 4)")
    ap.add_argument("--stand-in", default=None, help="dry run: one representation for both arms (pta)")
    ap.add_argument("--ratio", default="1,1", help="chunks of kraus_cpu, rm_cpu per cycle (prompts/33e R2: 1,2)")
    a = ap.parse_args(argv)

    from . import circuits as C
    from . import noise as N
    from . import sampling as SM
    from . import tokens as T
    from . import tokens_run as TR
    t0 = time.time()
    rec = TR.load_record()
    circ = C.load_circuit("IBM-T0", TR.KCHK_CIRCUIT)
    threads = cpu_threads(a.threads)
    offs = [int(x) for x in a.offsets.split(",")]
    arms = {}
    for (name, rep), off in zip((("kraus_cpu", "kraus"), ("rm_cpu", "rm")), offs):
        spec = N.ibm_spec(rec, "I-ECHO", a.stand_in or rep, "echo")
        sim, kw = SM.make_simulator("CPU", "policy", spec.noise_model, threads=threads)
        arms[name] = {"rep": rep, "spec": spec, "sim": sim, "circuit": spec.apply(circ), "offset": off,
                      "out": {"representation": spec.description["representation"], "planned_representation": rep,
                              "engine": "CPU statevector (separate process)", "simulator_options": kw,
                              "seed_circuit_offset": off, "chunk": a.chunk, "chunks": [], "shots_done": 0,
                              "stopped": None}}
    ratio = [int(x) for x in a.ratio.split(",")]
    cycle = pattern(list(arms), ratio)
    doc = {"pid": os.getpid(), "threads": threads, "cpu_affinity": cpu_affinity(), "deadline": a.deadline,
           "min_shots": a.min_shots, "chunk": a.chunk, "ratio": dict(zip(arms, ratio)), "cycle": cycle,
           "stand_in": a.stand_in, "build_s": time.time() - t0, "status": "running", "aer": aer_distribution(),
           "sequence": [],
           "rule": ("alternating chunks in the cycle order; an arm runs regardless of the deadline until min_shots, "
                    "then only while its slowest chunk so far would end before the deadline")}

    def dump():
        doc["arms"] = {k: v["out"] for k, v in arms.items()}
        doc["wall_s"] = time.time() - t0
        tmp = a.out + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(doc, fh)
        os.replace(tmp, a.out)

    dump()
    active = list(arms)
    j = {k: 0 for k in arms}
    while active:
        for name in cycle:
            if name not in active:
                continue
            arm = arms[name]
            o = arm["out"]
            if a.max_shots and o["shots_done"] >= a.max_shots:
                o["stopped"] = "max_shots"
                active.remove(name)
                continue
            if o["shots_done"] >= a.min_shots:
                slow = max([c["seconds"] for c in o["chunks"]] or [0.0])
                if time.time() + slow > a.deadline:
                    o["stopped"] = f"deadline: next chunk predicted {slow:.0f} s"
                    active.remove(name)
                    continue
            k = a.chunk if not a.max_shots else min(a.chunk, a.max_shots - o["shots_done"])
            seed = T.chunk_seed(a.s0, arm["offset"], j[name], a.chunk)
            t_c = time.time()
            res = arm["sim"].run(arm["circuit"], shots=k, seed_simulator=seed).result()
            if not res.success:
                raise RuntimeError(str(getattr(res, "status", "")))
            cnt = SM.counts_to_int(res.get_counts(0))
            o["chunks"].append({"index": j[name], "seed": seed, "shots": k, "start": o["shots_done"],
                                "seconds": time.time() - t_c, "counts": {str(x): int(v) for x, v in cnt.items()}})
            o["shots_done"] += k
            j[name] += 1
            doc["sequence"].append(name)
            dump()
    doc["status"] = "done"
    dump()
    return 0


if __name__ == "__main__":
    sys.exit(main())
