#!/usr/bin/env python3
"""
prompts/33: the 2x3 four-class campaign driver -- one Perlmutter job per token, plus the laptop stages.

    python scripts/run_gate.py C4_F1_B0                       # what the CI runs (scripts/gate_tokens.json)
    python scripts/campaign33.py --token C4_F1_B0             # the same
    python scripts/campaign33.py --token C4_F1_B0 --dry-run   # laptop path check: CPU, shots x 0.01,
                                                              #   <= 16 shots per run() call, few circuits,
                                                              #   validation/dryrun/<TOKEN>.json
    python scripts/campaign33.py --stage freeze ...           # = scripts/campaign33_freeze.py (laptop)
    python scripts/campaign33.py --stage assemble [--dry-run] # validation/C33_campaign.json + report
    python scripts/campaign33.py --stage exact-data           # data/campaign33/exact/*.json (laptop, once)

Classes (prompts/33 section 1): 1 ideal (C1_IDEAL), 2 IBM noise (C2_*), 3 Quantinuum-based ideal (C3_*),
4 Quantinuum-based errors and optimisations (C4_*).  The CI passes only the token, so the driver
recognises the CI itself (skqd.hpc.ci_context) and then defaults to the GPU, the token's walltime budget
(<= 50 min: run_gate.py kills a gate at 3600 s), the 476-shot chunk bound and 2000 bootstrap resamples;
explicit arguments win.  Every run writes validation/<TOKEN>.json (status PASS/FAIL on the token's
criteria of section 5: structural S1-S6 for every token, physics P1-P17 by class) and
reports/<TOKEN>.md generated from the same numbers.  In a --dry-run the physics criteria are recorded
as information and the status is the structural criteria only (a path check at tiny sizes).

Engine and HPC policy (RUNBOOK.md): Aer statevector, double precision, on the GPU
AerSimulator(method="statevector", device="GPU", cuStateVec_enable=True, batched_shots_gpu=True) unless
the token's calibration (C2_CAL, C4_FCELLS_A) measured a faster exact-equivalent mode; the `run` block
records engine, device, GPUs, tasks, wall, phases, s/shot, peak GPU memory and mean utilisation (the
nvidia-smi sampler of jobs/gate.sbatch), versions and every seed; E(p) is null (one task).
Runs on qiskit 1.4.3 + aer 0.15.1 (the CI) and 2.5.2 + 0.17.2 (the laptop); pytket is never imported
except by C3_LE in its own env.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.campaign33 import tokens as TK  # noqa: E402
from skqd.hpc import ci_context, gpu_count, gpu_telemetry, slurm_layout  # noqa: E402

PROMPT = "prompts/33_2x3_four_class_perlmutter_campaign.md"
DATA = os.path.join(ROOT, "data", "campaign33")
EXACT_DIR = os.path.join(DATA, "exact")
ENGINES_JSON = os.path.join(DATA, "engines.json")
FCELL_SHOTS = {"B0_ref25_k1": 800, "B1_ref57_k1": 800, "B0_ref25_k4": 200, "B1_ref57_k4": 200}
FCELL_SOURCE = "validation/Q0P_2x3_plan.json data.stage_E_v3.shots_by_circuit"
K1_IDS = ("B0_ref117_k1", "B1_ref29_k1")
CI_CHUNK = 476                       # shot_chunk_for(20, 1, 8e9): gate S3's one-call memory bound
DRY = {"shots_scale": 0.01, "max_shots_per_run": 16, "budget_minutes": 8.0, "bootstrap": 20,
       "max_circuits": 4, "threads": 6, "max_shots": 32}
DRY_REASON = ("a laptop path check, not a result: shots x 0.01 (prompts/33 A4), <= 16 shots per run() call, at most 4 "
              "circuits per sector, and at most 32 shots per circuit / unit -- noisy 20-21-qubit Aer runs at several "
              "seconds per shot on this CPU (the 1-shot warm-up of C4_F8_B0a took 52 s under load), so a 0.01-scaled "
              "plan of record (up to 676 shots for C4_F1_B1) would not fit the 10-minute dry-run bound")
TIERS = (0.05, 0.10, 0.15)
DEFAULT_TIER = 0.15


# =========================================================================== small helpers
def now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def load_json(p):
    with open(p if os.path.isabs(p) else os.path.join(ROOT, p)) as fh:
        return json.load(fh)


def rel(p):
    return os.path.relpath(p, ROOT)


def versions() -> dict:
    out = {}
    for m in ("qiskit", "qiskit_aer", "numpy", "scipy"):
        try:
            out[m] = __import__(m).__version__
        except Exception as exc:
            out[m] = f"unavailable: {type(exc).__name__}"
    out["python"] = sys.version.split()[0]
    return out


def token_class(token):
    return int(token[1])


# =========================================================================== the token context
class Ctx:
    """Everything one token run shares: arguments, device, budget, seeds, output paths, the result."""

    def __init__(self, args, ci):
        from skqd.report import GateResult
        self.args, self.ci = args, ci
        self.token = args.token
        self.tokens = TK.load_tokens()
        self.entry = self.tokens[self.token]
        self.dry = bool(args.dry_run)
        self.t0 = time.time()
        self.deadline = self.t0 + 60.0 * args.budget_minutes if args.budget_minutes > 0 else None
        self.s0 = TK.base_seed(self.token, self.tokens)
        self.gate = f"dryrun/{self.token}" if self.dry else self.token
        os.makedirs(os.path.join(ROOT, "validation", "dryrun"), exist_ok=True)
        os.makedirs(os.path.join(ROOT, "reports", "dryrun"), exist_ok=True)
        self.results_dir = os.path.join(ROOT, "results", "campaign33", "dryrun" if self.dry else "", self.token)
        os.makedirs(self.results_dir, exist_ok=True)
        self.R = GateResult(self.gate, self.title())
        self.data = {"token": self.token, "class": token_class(self.token), "prompt": PROMPT,
                     "content": self.entry["content"], "dry_run": self.dry, "created": now(),
                     "seeds": {"s0": self.s0, "rule": TK.SEED_RULE}}
        self.phases = {}
        self.physics_criteria = []
        self.notes = []
        self.device, self.available = self._device()
        self.gpu_mode = args.gpu_mode
        self.min_shots_ok = True
        self.no_shots = False            # a dry run that sampled nothing at all on some unit
        self.shots_reduced_to = None
        if self.dry:
            self.data["dry_run_reductions"] = {"shots_scale": args.shots_scale, "max_shots_per_run": args.max_shots_per_run,
                                               "max_circuits_per_sector": args.max_circuits,
                                               "max_shots_per_circuit": DRY["max_shots"],
                                               "budget_minutes": args.budget_minutes, "reason": DRY_REASON}
        self.oom = []
        self.seeds_recorded = True

    def title(self):
        base = f"Campaign 33 token {self.token} (class {token_class(self.token)}): {self.entry['content']}"
        return ("DRY RUN (laptop path check, reduced size): " + base) if self.dry else base

    def _device(self):
        if self.entry["env"] != "skqd":
            return "CPU", ["CPU"]
        try:
            from qiskit_aer import AerSimulator
            avail = list(AerSimulator().available_devices())
        except Exception as exc:
            return "CPU", [f"unavailable: {exc}"]
        req = self.args.device
        if req == "CPU":
            return "CPU", avail
        if "GPU" in avail:
            return "GPU", avail
        if req == "GPU":
            raise SystemExit(f"GPU requested but Aer reports {avail}")
        return "CPU", avail

    def remaining(self):
        return None if self.deadline is None else self.deadline - time.time()

    def sampling_deadline(self, share=0.75):
        """25 % of what is left is reserved for decoding / Ritz / the report (prompts/33 A4)."""
        if self.deadline is None:
            return None
        return time.time() + share * max(0.0, self.deadline - time.time())

    def scaled(self, n):
        v = max(1, int(math.ceil(float(n) * self.args.shots_scale)))
        return min(v, DRY["max_shots"]) if self.dry else v

    def physics(self, name, value, threshold, passed):
        """A physics criterion: gating on a real run, information in a dry run."""
        if self.dry:
            self.physics_criteria.append({"name": name, "value": value, "threshold": threshold,
                                          "passed": bool(passed), "gating": False})
        else:
            self.R.add(name, value, threshold, passed)

    def log(self, *a):
        print(f"[{time.time() - self.t0:7.1f} s] {self.token}:", *a, flush=True)


def build_parser(ci: dict = None):
    """The command line, with the CI defaults applied when `ci` is non-empty (tests pin them)."""
    ci = ci_context() if ci is None else ci
    ap = argparse.ArgumentParser(description="prompts/33 campaign driver")
    ap.add_argument("--token", default=None, help="one of scripts/gate_tokens.json")
    ap.add_argument("--stage", default="run", choices=("run", "freeze", "assemble", "exact-data"))
    ap.add_argument("--dry-run", action="store_true", help="laptop path check (validation/dryrun/<TOKEN>.json)")
    ap.add_argument("--shots-scale", type=float, default=1.0)
    ap.add_argument("--max-shots-per-run", type=int, default=0, help="chunk bound (0 = 476 on the GPU, 476 on CPU)")
    ap.add_argument("--budget-minutes", type=float, default=0.0, help="whole-job budget (0 = none)")
    ap.add_argument("--device", default="auto", choices=("auto", "GPU", "CPU"))
    ap.add_argument("--gpu-mode", default="auto", choices=("auto", "policy", "custatevec", "batched"))
    ap.add_argument("--threads", type=int, default=0, help="Aer CPU threads (0 = Aer's default)")
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--max-circuits", type=int, default=0, help="per family/sector (0 = all; dry run 4)")
    ap.add_argument("--min-shots", type=int, default=1)
    if ci:
        tok = None
        for i, a in enumerate(sys.argv):
            if a == "--token" and i + 1 < len(sys.argv):
                tok = sys.argv[i + 1]
        tok = tok or ci.get("CI_GATE")
        wall = TK.walltime_seconds(TK.load_tokens()[tok]["walltime"]) if tok in TK.load_tokens() else 3600
        # run_gate.py's default --timeout is 3600 s: 50 minutes at most, and 10 minutes below the walltime
        budget = min(50.0, wall / 60.0 - 10.0)
        ap.set_defaults(device="GPU", budget_minutes=budget, max_shots_per_run=CI_CHUNK, bootstrap=2000)
    return ap


def apply_dry_defaults(args):
    """--dry-run: explicit values win over the DRY table."""
    if not args.dry_run:
        return args
    if args.shots_scale == 1.0:
        args.shots_scale = DRY["shots_scale"]
    if args.max_shots_per_run == 0:
        args.max_shots_per_run = DRY["max_shots_per_run"]
    if args.budget_minutes == 0.0:
        args.budget_minutes = DRY["budget_minutes"]
    if args.bootstrap == 2000:
        args.bootstrap = DRY["bootstrap"]
    if args.max_circuits == 0:
        args.max_circuits = DRY["max_circuits"]
    if args.threads == 0:
        args.threads = DRY["threads"]
    if args.device == "auto":
        args.device = "CPU"
    return args


def chunk_bound(ctx):
    return int(ctx.args.max_shots_per_run) if ctx.args.max_shots_per_run > 0 else CI_CHUNK


# =========================================================================== structural criteria and output
def finish(ctx, extra_run=None):
    """S1-S6 (prompts/33 section 5), the run block, the JSON and the generated report."""
    wall = time.time() - ctx.t0
    layout = slurm_layout()
    tele = gpu_telemetry()
    gpus = gpu_count(layout)
    want_gpu = bool(ctx.ci) and ctx.entry["env"] == "skqd"
    if ctx.entry["env"] != "skqd":
        ok = not ctx.data.get("dropped")
        ctx.R.add("S1 the run happened on the requested engine (CPU, its own env)", ctx.data.get("engine"),
                  "the engine ran", ok)
    else:
        ctx.R.add("S1 the run happened on the requested device" + (" (GPU under the CI)" if want_gpu else ""),
                  f"{ctx.device} (available {ctx.available})", "GPU" if want_gpu else "as requested",
                  (ctx.device == "GPU") if want_gpu else True)
    budget_s = 60.0 * ctx.args.budget_minutes if ctx.args.budget_minutes > 0 else None
    wall_limit = TK.walltime_seconds(ctx.entry["walltime"])
    ok_wall = wall <= min(wall_limit, 3600.0) and (budget_s is None or wall <= budget_s * 1.10 + 120.0)
    ctx.R.add("S2 wall time inside the walltime budget", f"{wall:.0f} s",
              f"<= min(walltime {wall_limit} s, 3600 s) and <= 1.1 x budget + 120 s" if budget_s else
              f"<= min(walltime {wall_limit} s, 3600 s)", ok_wall)
    run = {"engine": ctx.data.get("engine", "Qiskit Aer statevector (double precision)"),
           "device": ctx.device, "device_requested": ctx.args.device, "available_devices": ctx.available,
           "gpu_mode": ctx.data.get("gpu_mode_used"), "ci": ctx.ci or None, "slurm": layout, "gpus": gpus,
           "tasks": layout["tasks"], "rank": layout["rank"], "wall_seconds": wall,
           "gpu_node_hours": None if not gpus else gpus * wall / 3600.0,
           "node_hours_charged_shared_qos": None if not gpus else (gpus / 4.0) * wall / 3600.0,
           "parallel_efficiency_Ep": None,
           "parallel_efficiency_note": "one task: E(p) needs T_1 and T_p from two task counts (not measured)",
           "phases_s": ctx.phases, "gpu_telemetry": tele, "versions": versions(),
           "seconds_per_shot": ctx.data.get("seconds_per_shot"), "budget_minutes": ctx.args.budget_minutes,
           "shots_scale": ctx.args.shots_scale, "max_shots_per_run": chunk_bound(ctx),
           "oom_retries": ctx.oom}
    if extra_run:
        run.update(extra_run)
    ctx.data["run"] = run
    policy_ok = all(run.get(k) is not None for k in ("engine", "device", "wall_seconds", "phases_s", "versions"))
    if ctx.ci:
        policy_ok = policy_ok and gpus is not None and tele.get("peak_memory_mib") is not None \
            and tele.get("mean_utilization_pct") is not None and run["seconds_per_shot"] is not None
    ctx.R.add("S3 telemetry and run block present" + (" (policy fields non-null on the CI)" if ctx.ci else ""),
              {k: run.get(k) is not None for k in ("engine", "device", "wall_seconds", "seconds_per_shot", "gpus")},
              "every policy field non-null on the CI; present on the laptop", policy_ok)
    ctx.R.add("S4 every seed and every chunk recorded", ctx.seeds_recorded, "true", ctx.seeds_recorded)
    oom_ok = all("split" in o for o in ctx.oom)
    ctx.R.add("S5 no out-of-memory retry left unrecorded", f"{len(ctx.oom)} recorded", "each OOM split recorded",
              oom_ok)
    if ctx.dry:
        ctx.R.add("S6 (dry run) every unit sampled; any budget reduction recorded (the full-plan check is the CI's)",
                  ctx.shots_reduced_to or "full", "shots > 0 on every unit", not ctx.no_shots)
    else:
        ctx.R.add("S6 shots >= the token's minimum" + (" (C4_F*: the plan of record in full)"
                                                       if ctx.token.startswith("C4_F") and "CELLS" not in ctx.token else ""),
                  ctx.shots_reduced_to or "full", "no reduction below the minimum", ctx.min_shots_ok)
    ctx.data["physics_criteria_information_dry_run"] = ctx.physics_criteria if ctx.dry else None
    ctx.data["notes"] = ctx.notes
    ctx.tables = ctx.data.pop("_tables", [])          # report-only: the JSON carries the numbers themselves
    ctx.R.data = ctx.data
    ctx.R.runtime_s = wall
    ctx.R.save()
    from skqd.report import write_report
    name = (f"dryrun/{ctx.token}.md" if ctx.dry else f"{ctx.token}.md")
    write_report(name, report_text(ctx))
    print(ctx.R.criteria_table())
    status = "PASS" if ctx.R.passed else "FAIL"
    print(f"{ctx.token}: {status} ({wall:.0f} s){' [dry run]' if ctx.dry else ''}")
    return 0 if ctx.R.passed else 1


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, (list, tuple)) and v and all(isinstance(x, (int, float)) or x is None for x in v):
        return "[" + ", ".join("None" if x is None else (f"{x:.4g}" if isinstance(x, float) else str(x)) for x in v) + "]"
    return str(v)


def report_text(ctx):
    from skqd.report import env_block, md_table
    d = ctx.data
    run = d["run"]
    tele = run["gpu_telemetry"]
    banner = ("\n> **DRY RUN** — a laptop path check at reduced size (shots x {}, <= {} shots per run() call, "
              "at most {} circuits per family/sector, CPU).  Physics criteria are listed as information; the "
              "status is the structural criteria only.  No number here is a campaign result.\n".format(
                  ctx.args.shots_scale, chunk_bound(ctx), ctx.args.max_circuits or "all")) if ctx.dry else ""
    lines = [f"# {ctx.R.title}", "",
             f"**Status: {'PASS' if ctx.R.passed else 'FAIL'}** — `python scripts/campaign33.py --token {ctx.token}"
             f"{' --dry-run' if ctx.dry else ''}`.  {env_block()}  Runtime {ctx.R.runtime_s:.0f} s.  Prompt {PROMPT}.",
             banner,
             "## Engine and resources", "",
             f"Engine {run['engine']}; device {run['device']} (requested {run['device_requested']}, available "
             f"{run['available_devices']}); GPU mode {run['gpu_mode']}; GPUs {run['gpus']}; tasks {run['tasks']}; "
             f"wall {run['wall_seconds']:.0f} s; GPU node-hours (shared QOS, G/4 x t) "
             f"{_fmt(run['node_hours_charged_shared_qos'])}; E(p) {run['parallel_efficiency_Ep']} "
             f"({run['parallel_efficiency_note']}); seconds per shot {_fmt(run['seconds_per_shot'])}; peak GPU memory "
             f"{_fmt(tele['peak_memory_mib'])} MiB; mean GPU utilisation {_fmt(tele['mean_utilization_pct'])} %; "
             f"versions {run['versions']}.  Phases (s): "
             + ", ".join(f"{k} {v:.1f}" for k, v in run["phases_s"].items()) + ".", ""]
    for title, rows, header in getattr(ctx, "tables", []):
        lines += [f"## {title}", "", md_table(header, [[_fmt(x) for x in r] for r in rows]), ""]
    if ctx.dry and ctx.physics_criteria:
        lines += ["## Physics criteria (information in a dry run)", "",
                  md_table(["check", "value", "criterion", "would pass"],
                           [[c["name"], _fmt(c["value"]), c["threshold"], c["passed"]] for c in ctx.physics_criteria]), ""]
    if ctx.notes:
        lines += ["## Notes", ""] + [f"- {n}" for n in ctx.notes] + [""]
    lines += ["## Criteria", "", ctx.R.criteria_table(), "",
              f"Every number above is computed by `scripts/campaign33.py` and stored in `validation/{ctx.gate}.json`."]
    return "\n".join(lines) + "\n"


def add_table(ctx, title, header, rows):
    ctx.data.setdefault("_tables", []).append((title, rows, header))


# =========================================================================== token dispatch
def run_token(args, ci):
    from skqd.campaign33 import tokens_run as TR
    ctx = Ctx(args, ci)
    ctx.log(f"device {ctx.device} (available {ctx.available}), budget {args.budget_minutes} min, "
            f"shots x {args.shots_scale}, chunk <= {chunk_bound(ctx)}, s0 {ctx.s0}"
            + (" [DRY RUN]" if ctx.dry else ""))
    t = ctx.token
    if t in ("C1_IDEAL", "C3_AER"):
        TR.run_ideal(ctx)
    elif t == "C2_CAL":
        TR.run_c2_cal(ctx)
    elif t.startswith("C2_"):
        TR.run_c2_cell(ctx)
    elif t in ("C3_LE", "C3_SEL"):
        TR.run_c3_engine(ctx)
    elif t.startswith("C4_FCELLS"):
        TR.run_fcells(ctx)
    elif t == "C4_CF":
        TR.run_cf(ctx)
    elif t.startswith("C4_F"):
        TR.run_frun(ctx)
    else:
        raise SystemExit(f"unknown token {t}")
    return finish(ctx)


def main(argv=None):
    ci = ci_context()
    ap = build_parser(ci)
    args = ap.parse_args(argv)
    if args.stage == "freeze":
        import campaign33_freeze
        sys.argv = [sys.argv[0]] + [a for a in (argv or sys.argv[1:]) if a not in ("--stage", "freeze")]
        return campaign33_freeze.main()
    if args.stage == "assemble":
        from skqd.campaign33 import assemble
        return assemble.main(dry=args.dry_run)
    if args.stage == "exact-data":
        from skqd.campaign33 import tokens_run as TR
        return TR.write_exact_data()
    if not args.token:
        ap.error("--token is required for --stage run")
    if args.token not in TK.load_tokens():
        raise SystemExit(f"unknown token {args.token}")
    args = apply_dry_defaults(args)
    return run_token(args, ci)


if __name__ == "__main__":
    sys.exit(main())
