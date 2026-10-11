"""
Regression test for the C2_CAL run-2 zero-shot arms (CI job 59570318, validation/C2_CAL.json run 2).

The Sampler's discarded 1-shot warmup took 12.27 s (RM) and 13.19 s (Kraus) on the A100 -- almost all of it
per-call set-up -- and the old deadline rule read that as 12-13 s PER SHOT: round 0 (one 128-shot call) was
predicted at 1571 s / 1688 s against 0.6 / 0.9 of the time left, so both arms stopped before their first call
with 0 shots and no log line.  The call model is t(s) = c + b s; job 59491475's fit for Kraus is c = 10.8 s,
b = 1.49 s/shot, the PTA fit c = 3.46 s, b = 0.236 s/shot (prompts/33a section 0).  These tests run the
Sampler on a virtual clock with a stub simulator obeying that model, so they are fast, deterministic and need
no Aer.  The old code fails test 1 and test 2 (0 shots); test 3 pins that the protection the warmup existed
for (a per-shot-dominated channel, Kraus at 21 qubits on a CPU) is kept: no round is started that cannot
finish before the deadline.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from skqd.campaign33 import sampling as SM  # noqa: E402


class Clock:
    def __init__(self, t0=1.0e6):
        self.t = float(t0)

    def time(self):
        return self.t


class ModelSim:
    """run() of `shots` shots advances the virtual clock by c + b * shots (the measured call model); the first
    call (the Sampler's 1-shot warmup) costs `first` seconds when given (the measured warmup, which also carries
    the one-time initialisation)."""

    def __init__(self, clock, c, b, first=None):
        self.clock, self.c, self.b, self.first, self.calls = clock, float(c), float(b), first, []

    def run(self, circ, shots, seed_simulator):
        self.calls.append((int(shots), int(seed_simulator), self.clock.t))
        if self.first is not None and len(self.calls) == 1:
            self.clock.t += float(self.first)
        else:
            self.clock.t += self.c + self.b * int(shots)
        n = int(shots)
        res = type("R", (), {"success": True, "get_counts": lambda s, i: {"0" * 20: n}})()
        return type("J", (), {"result": lambda s: res})()


@pytest.fixture
def clock(monkeypatch):
    ck = Clock()
    monkeypatch.setattr(SM, "time", ck)
    return ck


def _arm(clock, c, b, shots, window, chunk=128, first=None):
    """One C2_CAL arm as run_c2_cal calls it: plain chunks (phis = (1.0,)), deadline = now + window."""
    sim = ModelSim(clock, c, b, first)
    logs = []
    s = SM.Sampler(sim, s0=33_100_000, max_chunk=chunk, deadline=clock.time() + window, log=logs.append,
                   phis=(1.0,))
    t0 = clock.time()
    res, info = s.run(["B0_ref117_k1"], [shots], ["B0_ref117_k1"], circuit_offset=501)
    return res[0], info, sim, logs, clock.time() - t0


def test_rm_arm_with_a_set_up_dominated_call_draws_all_its_shots(clock):
    # RM in job 59570318: warmup 12.27 s; PTA-like per-shot cost; guard 0.6 x ~1880 s left = 1130 s
    r, info, sim, logs, used = _arm(clock, c=12.0, b=0.27, shots=1024, window=1130.0, first=12.27)
    assert r["shots_done"] == 1024, (info["stopped"], logs)
    assert info["stopped"] is None
    assert used <= 1130.0
    assert info["seconds_per_shot"] is not None


def test_kraus_arm_reaches_its_minimum(clock):
    # Kraus in job 59570318: warmup 13.19 s, 0.9 x ~1876 s left = 1688 s, target 1024, minimum 384
    r, info, sim, logs, used = _arm(clock, c=10.8, b=1.49, shots=1024, window=1688.0, first=13.19)
    assert r["shots_done"] >= 384, (info["stopped"], logs)
    assert used <= 1688.0, "never past the deadline"
    # deadline-stopped at a chunk boundary, and the stop is logged with its numbers
    assert r["shots_done"] % 128 == 0
    if info["stopped"] is not None:
        assert any("deadline stop" in m for m in logs)
        assert info["stopped"]["predicted_round_s"] > info["stopped"]["seconds_left"]


def test_kraus_at_the_flat_rate_still_reaches_the_minimum(clock):
    # job 59491475's flat Kraus rate 3.18 s/shot (c ~ 0): one 128-shot round ~ 407 s
    r, info, sim, logs, used = _arm(clock, c=0.5, b=3.18, shots=1024, window=1688.0, first=13.19)
    assert r["shots_done"] >= 384 and used <= 1688.0


def test_a_per_shot_dominated_channel_is_still_stopped_before_overrunning(clock):
    # Kraus at 21 qubits on the laptop CPU: ~140 s per shot (K1 dry run); a 128-shot round needs ~5 h
    r, info, sim, logs, used = _arm(clock, c=1.0, b=140.0, shots=1024, window=1000.0)
    assert r["shots_done"] == 0
    assert info["stopped"] is not None and info["stopped"]["round"] == 0
    assert used <= 1000.0, "the probes themselves stay inside the window"
    assert info["seconds_per_shot"] is None, "no shot drawn: no measured rate (the warmup is not a rate)"
    assert any("deadline stop" in m for m in logs)


def test_probes_are_recorded_discarded_and_seed_disjoint(clock):
    r, info, sim, logs, used = _arm(clock, c=12.0, b=0.27, shots=1024, window=1130.0, first=12.27)
    w = info["warmup"]
    assert w["shots"] == 1 and w["discarded"] and w["probes"], "the 1-shot bound did not fit: a probe ran"
    assert all(p["discarded"] for p in w["probes"])
    real = [(ch["seed"], ch["seed"] + ch["shots"]) for ch in r["chunks"]]
    probe = [(w["seed"], w["seed"] + 1)] + [(p["seed"], p["seed"] + p["shots"]) for p in w["probes"]]
    ranges = sorted(real + probe)
    assert all(ranges[i][1] <= ranges[i + 1][0] for i in range(len(ranges) - 1)), "no shot stream shared"
    # real chunks are untouched by the fix: same seeds as an unbudgeted run
    assert [ch["seed"] for ch in r["chunks"]] == [SM.T.chunk_seed(33_100_000, 501, j, 128) for j in range(8)]


def test_a_fitting_warmup_takes_no_probe(clock):
    # PTA in job 59570318 (warmup 4.0 s, 512 shots, guard 0.6 x ~1890 s): the 1-shot bound 4 x 128 = 512 s fits
    r, info, sim, logs, used = _arm(clock, c=3.46, b=0.236, shots=512, window=1134.0, first=4.05)
    assert r["shots_done"] == 512 and info["warmup"]["probes"] == []
    assert len(sim.calls) == 1 + 4


def test_call_bound_is_an_upper_bound_of_the_linear_model():
    for c, b in ((12.0, 0.27), (0.0, 3.0), (5.0, 0.0)):
        for sp in (1, 9, 128):
            for s in (1, 7, 128, 476):
                assert SM.call_bound((sp, c + b * sp), s) >= c + b * s - 1e-12
        assert SM.call_bound((128, c + b * 128), 128) == pytest.approx(c + b * 128)


def test_c2_cal_run_rate_is_non_null_when_any_arm_sampled():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    from skqd.campaign33.tokens_run import c2_cal_run_rate
    arms = {"pta": {"representation": "pta", "shots_done": 512, "sampling_wall_s": 146.4,
                    "seconds_per_shot_at_largest_point": 0.286},
            "rm": {"representation": "rm", "shots_done": 0, "sampling_wall_s": 0.0,
                   "seconds_per_shot_at_largest_point": None},
            "kraus": {"representation": "kraus", "shots_done": 0, "sampling_wall_s": 0.0,
                      "seconds_per_shot_at_largest_point": None}}
    out = c2_cal_run_rate(arms, "kraus", "custatevec")
    assert out["seconds_per_shot"] == pytest.approx(146.4 / 512) and "pooled" in out["seconds_per_shot_source"]
    arms["kraus"].update(shots_done=384, sampling_wall_s=800.0, seconds_per_shot_at_largest_point=2.0)
    assert c2_cal_run_rate(arms, "kraus", "custatevec")["seconds_per_shot"] == 2.0
    for a in arms.values():
        a.update(shots_done=0, seconds_per_shot_at_largest_point=None)
    assert c2_cal_run_rate(arms, "kraus", "custatevec")["seconds_per_shot"] is None
