# Contributing

This is a Compiled AI reference implementation. Read `CLAUDE.md` and `PLAN.md`
before making changes — the hard invariants there override convenience, and
violating one is a defect even if tests pass.

## Setup

Python 3.11, managed with `uv`:

```
uv venv --python 3.11
uv pip install -e '.[dev]'      # duckdb, pyyaml, jsonschema, pytest, ruff
uv pip install -e '.[llm]'      # optional: anthropic SDK, only for --backend api
```

The full runtime (OHDSI R stack + JDK + duckdb) lives in `.devcontainer/`. Gates 1,
2, and the pure half of 4 run with only Python; Gate 3 and the CirceR half of 4 need
R and run in the devcontainer (CI is Python-only).

## Everyday commands

```
python -m pytest -q                 # all four gates + demotion + backends
ruff check tec tests conftest.py    # lint
python -m tec.gates.g1_structure    # a single gate CLI (g1..g4)
trcompile backends                  # which LLM backends are available here
trcompile build --backend mock      # compile with the canned client (offline)
trcheck evaluate --patient fixtures/patients/p_match.yaml   # devcontainer
```

Slash commands (Claude Code / Cursor): `/compile`, `/verify`, `/new-spec`,
`/check-pattern`. See `AGENTS.md` for the agent-driven compile protocol.

## LLM backends

`trcompile build --backend {auto,claude-code,api,cursor,mock}` (env
`TRCOMPILE_BACKEND`). `auto` tries Claude Code, then API, then Cursor. Only
**claude-code** (agent-driven) is verified in this build; **api** and **cursor** are
provided but not yet verified. CI always uses `--backend mock`. The trust anchor is
the gates, not the frontend — any backend must produce output that passes the same
gates.

## The rules that block a PR

1. **Never weaken a gate.** The gates are the value. If a change makes a gate fail,
   fix the artifact or the code — do not loosen the check. If you believe a gate is
   wrong, open an issue explaining why before changing it.
2. **Answer-key demotion.** `tec/compile/prompt.py` reads only `source/*.md` and
   `compiled/**/vocab/`. It must never read `manifest.json`, `cohort.json`,
   `conventions.json`, `fixtures/`, `corpus-plan.md`, `fixture-plan.md`, or any
   external structured-criteria dataset (Chia, n2c2). `tests/test_answer_key_demotion.py`
   enforces this. See [docs/answer-key-demotion.md](docs/answer-key-demotion.md).
3. **AMBIGUOUS never touches the executable.** `disposition == "AMBIGUOUS"` ⇒
   `concepts == []` and `cohort_rule == null`; it never appears in `cohort.json`.
4. **Runtime is not ours.** Cohort SQL is built and executed only by standard OHDSI
   packages. Do not hand-write cohort SQL or reimplement Circe. `trcheck` must not
   import `tec.compile` or `tec.gates.oracle`.
5. **Determinism.** Serialise all artifacts as canonical JSON (`tec/canonical.py`);
   recompiling must be byte-identical (Gate 4). See
   [docs/determinism.md](docs/determinism.md).
6. **No real patient data, ever.** Every CDM row and fixture is hand-authored
   synthetic.

## Pull requests

- CI (`.github/workflows/ci.yml`) must be green: lint, the Python gates (1, 2, and
  the byte-stability/boundary half of 4) + demotion + backends, and the
  recompile-equality diff (MockClient output == committed). CI is Python-only; the
  OHDSI-execution gates (3, and the CirceR half of 4) run in the devcontainer.
- If you edit a `source/*.md` spec, recompile and commit the regenerated artifact —
  Gate 4's recompile-equality catches an edited spec that wasn't recompiled.
- Keep the voice terse and technical; sentence case in docs; no emoji.

Adding a trial: [docs/new-trial.md](docs/new-trial.md).
