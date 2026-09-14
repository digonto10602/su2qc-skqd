# Model and effort routing

Goal: spend Fable 5.1 only where reasoning depth changes the outcome (physics decisions, blocked gates,
the next prompt), spend Opus on implementation, and push every repetitive execution to Sonnet/Haiku (or, in
Hermes runs, to the NVIDIA NIM open models).  Effort levels are the Claude Code levels `low, medium, high,
xhigh, max` (set per agent in `.claude/agents/*.md` via the `effort:` frontmatter field, or per session
with `/effort` / `CLAUDE_CODE_EFFORT_LEVEL`).

## The loop

```
planner-fable (max)  --writes-->  prompts/NN_step.md
        ^                                |
        |                                v
   BLOCKED.md  <--FAIL--  runner-sonnet (low) runs scripts/run_gate.py GATE
        |                                |
        |                              PASS
        |                                v
        |                 reviewer-opus (medium) audits JSON <-> report <-> code
        |                                |
        |                             APPROVE
        |                                v
        |                 run_gate.py GATE --push ; scribe-haiku (low) updates status tables
        |
   executor-opus (high) implements the fix prompt; planner is NOT re-invoked unless the fix fails twice
```

## Rules

1. **Fable is invoked at `max` only** (a) to write the next step's prompt when the step involves a physics or
   method decision, (b) when `validation/BLOCKED.md` exists and the executor failed twice, (c) for the weekly
   plan revision.  Everything else runs without Fable.
2. **Opus at `high`** implements; **Opus at `medium`** reviews.  A review never re-derives the physics from
   scratch; it checks computed-versus-quoted numbers and conventions.
3. **Sonnet at `low`** runs.  It never edits source.  It reports tracebacks verbatim.
4. **Haiku at `low`** formats.  It never changes numbers.
5. Effort escalation inside one model is allowed once before escalating the model: executor-opus `high` →
   `xhigh` on the second attempt, then planner-fable `max`.
6. Every invocation names the prompt file it executes; every outcome goes to `prompts/LOG.md`.
7. Hermes / open-model equivalents (when Claude quotas are exhausted): runner-sonnet → any NIM model
   (DeepSeek/Qwen/Nemotron) with the same prompt; executor-opus → Codex; planner-fable has no substitute —
   wait for quota rather than downgrade a physics decision.

## Cost sketch per gate

| gate type | Fable calls | Opus calls | Sonnet/Haiku calls |
|---|---|---|---|
| routine gate that passes | 0 | 1 (review) | 2 (run, scribe) |
| gate that fails once | 0 | 2 (fix at high, review) | 3 |
| gate blocked twice | 1 (max) | 2 | 3 |
| new step needing a method decision | 1 (max, prompt) | 1–2 | 2 |
