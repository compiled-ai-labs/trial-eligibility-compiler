# AGENTS.md — driving the compiler from Claude Code or Cursor

This repo is a **Compiled AI** reference implementation. An LLM runs at compile
time to turn verbatim ClinicalTrials.gov eligibility prose into a deterministic
OHDSI Circe cohort, committed only after four machine-checkable gates pass. The
runtime (`trcheck`) is unmodified OHDSI — no model in the path.

There are three ways to invoke the LLM at compile time. **The trust anchor is the
gates, not which frontend drives the LLM** — every path faces the identical
`pytest` gate suite and the recompile-equality check.

## 1. Claude Code (preferred) and 2. Cursor — agent-driven

You (Claude Code or Cursor) are the LLM. Run the `/compile` command, or follow the
protocol directly:

1. Read **only** `source/NCT03667300.md` and the curated concept sets under
   `compiled/NCT03667300/vocab/*.json`. Do **not** read `manifest.json`,
   `cohort.json`, `conventions.json`, anything under `fixtures/`, `corpus-plan.md`,
   or `fixture-plan.md` — those encode the target dispositions/labels (the answer
   key). This is *answer-key demotion* and it is non-negotiable (CLAUDE.md
   invariant 2).
2. Emit `cohort.json` (standard OHDSI Circe, determinate criteria only, each a
   named inclusion rule), `manifest.json` (all 16 source ids with dispositions +
   provenance), and `conventions.json`, applying the compile/refuse rule: compile
   only if you add a writable convention; otherwise **AMBIGUOUS**. Never invent
   concept-set membership; use only the provided concept sets.
3. Write the three files canonically and run `python -m pytest -q`. If Gate 1 or 2
   fails, fix the exact error and re-emit. Do not weaken a gate.

Cost: $0 marginal under a subscription. Quarantine (answer-key demotion) is
enforced by this protocol + review + CI — this is the agent-driven analog of the
in-code guard the API path uses.

Programmatic equivalents also exist: `trcompile build --backend claude-code` and
`--backend cursor` shell out to `claude -p` / `cursor-agent -p`.

## 3. Anthropic API — batch, in code

```
uv pip install -e '.[llm]'
export ANTHROPIC_API_KEY=...          # or ANTHROPIC_BASE_URL for an alt provider
trcompile build --trial NCT03667300 --backend api
```

Pinned model `claude-opus-4-8` (override with `TRCOMPILE_MODEL`). Quarantine is
enforced **in code**: `tec/compile/prompt.py` reads only `source/*.md` + `vocab/`,
covered by `tests/test_answer_key_demotion.py`. Determinism is enforced by Gate 4
(recompile-equality), not by a sampling temperature (Opus 4.8 removed
`temperature`).

## Default selection

`trcompile build` (no `--backend`) resolves `auto`: **Claude Code first**, then
API, then Cursor. CI always uses `--backend mock` (no secrets, no network).
`trcompile backends` prints what is available in the current environment.
