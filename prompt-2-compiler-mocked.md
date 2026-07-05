# Prompt 2 — compiler with mocked client

Paste into Claude Code after Stage 1 is green.

---

```
Read CLAUDE.md and PLAN.md. Obey every hard invariant. Stage 1 is complete: the
gates, synthetic CDM, runtime, and a hand-authored committed artifact are green.

This is STAGE 2 of 3. Goal: implement the LLM compiler and its retry loop, driven
by a DETERMINISTIC MOCK client — no real Anthropic API, no network, no API key.
By the end, `trcompile` reproduces the committed artifact and every gate stays
green in CI. Do NOT wire the real Anthropic client in this stage.

TASK 1 — compile prompt (tec/compile/prompt.py).
- Build the compile prompt from source/NCT03667300.md ONLY. Enforce answer-key
  demotion in code: the module must read nothing under fixtures/, compiled/,
  corpus-plan.md, or fixture-plan.md. Add a unit test that fails if this module
  imports or opens any of those paths.
- The prompt instructs the model to emit BOTH cohort.json (standard Circe, named
  inclusion rules, determinate criteria only) and manifest.json (all 16 source
  ids, dispositions, provenance), applying the compile/refuse rule from CLAUDE.md
  and pinning conventions into conventions.json. It must be told: refusal is a
  valid output; never invent concept-set membership; a compound criterion is only
  as determinable as its weakest part.

TASK 2 — client interface (tec/compile/client.py).
- Define a small CompilerClient interface with one method (prose -> raw model
  output). Provide a MockClient that returns a canned, valid response reproducing
  the Stage-1 committed artifact byte-for-byte after canonical serialisation.
- Also provide a "faulty" mock variant used only in tests that returns an
  artifact failing Gate 1 or Gate 2 (e.g. drops E6, or marks E6 INCLUDE with an
  invented concept set), to exercise the retry loop.

TASK 3 — compiler + retry loop (tec/compile/compiler.py).
Implement exactly PLAN.md §6:
  read source -> client -> parse candidate cohort.json + manifest.json
    -> Gate 1 (structure) + Gate 2 (coverage)
       pass -> canonical-serialise, write to compiled/NCT03667300/
       fail -> append the concrete gate errors to the prompt, retry (<=3)
               exhausted -> raise, exit non-zero, write nothing.
Wire it to `trcompile build --trial NCT03667300`, defaulting to MockClient in
this stage.

TASK 4 — close Gate 4's recompile half.
Now that a compiler exists, implement the recompile-equality check flagged TODO
in Stage 1: `trcompile` output must be byte-identical to the committed artifact.
Add a CI step that runs trcompile with the MockClient and diffs against
compiled/NCT03667300/ (must be empty diff).

TASK 5 — retry-loop tests.
- With the faulty mock: assert the loop feeds gate errors back, and either
  recovers within 3 tries (if the mock is scripted to fix itself) or hard-fails
  and writes nothing. Assert compiled/** is untouched on hard failure.
- With the good mock: assert a clean single-pass compile reproducing the artifact.

STOP CONDITION. Deliverable, all offline with no API key:
  * `trcompile build --trial NCT03667300` (MockClient) reproduces the committed
    artifact byte-for-byte,
  * all four gates green in CI, including the new recompile-equality and
    answer-key-demotion checks,
  * retry-loop tests pass.
Present: the trcompile run, the empty recompile diff, and the gate summary. Do
not wire the real API.
```
