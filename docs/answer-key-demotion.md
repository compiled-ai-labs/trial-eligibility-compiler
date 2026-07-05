# Answer-key demotion

The compiler must be judged on whether it can produce a gate-passing artifact from
the *criteria alone* — not from having seen the answer. Answer-key demotion is the
rule that keeps the compile prompt away from anything that encodes the target
dispositions or the expected patient labels.

## What the compile prompt may and may not read

`tec/compile/prompt.py` builds the prompt. It may read **only**:

- `source/*.md` — the verbatim registered criteria (the input), and
- `compiled/<trial>/vocab/*.json` — the curated concept sets.

It must never read:

- `manifest.json` — it contains the target **dispositions** (the answer),
- `cohort.json`, `conventions.json` — compiler output,
- anything under `fixtures/` — the synthetic patients and their **expected labels**,
- `corpus-plan.md`, `fixture-plan.md` — planning docs that discuss the answer,
- any external structured-criteria dataset (Chia, n2c2) — see below.

## Resolution A: vocab is curated input, not answer key

An earlier framing said the prompt reads "raw prose only." That collides with the
rule "never invent concept-set membership": if the compiler can't see the curated
concept sets, it must conjure `concept_id`s from model memory — which is exactly the
invention the paradigm forbids.

**Resolution A** draws the line at *what encodes the target*, not at a directory:

- **Membership is curated reference data, not an answer.** `vocab/*.json` says which
  standard concepts constitute "type 2 diabetes" — a human-curated, citable fact, not
  the compiler's verdict. The prompt reads it; the model wires determinate criteria
  to those concepts and refuses when no set fits.
- **The answer key is the dispositions and labels.** `manifest.json` (INCLUDE /
  EXCLUDE / AMBIGUOUS per criterion), the fixtures, and their expected labels reveal
  the intended output. The prompt never sees them.

So the demotion carve-out is: everything under `compiled/<trial>/` is off-limits to
the prompt **except** `vocab/`.

## Why Chia and n2c2 are evaluation-only

Chia (Kury et al.) and n2c2 are human-annotated criteria→concept datasets. They can
*score* the compiler, but a compile prompt that reads them is reading a curated
answer key. Under demotion they are evaluation-only and never a compile input.

## How it is enforced

- **In code.** `prompt.py` reads only the two allowed roots; the module documents
  `ALLOWED_READ_ROOTS` as executable intent.
- **In test.** `tests/test_answer_key_demotion.py` monkeypatches `Path.read_text` /
  `Path.read_bytes`, runs `build_prompt`, and asserts every file actually read is
  under `source/` or `vocab/` — and that no forbidden filename or `fixtures/` path is
  opened. A second test scans the module source for answer-key path references.
- **In review + CI.** For the agent-driven backends (Claude Code, Cursor) the guard
  is protocol + review + CI rather than a code path — the `/compile` command and
  `AGENTS.md` state the same read allow-list, and the same gates run either way.

## Clients are not the prompt

The demotion rule binds `prompt.py` only. The backend clients in
`tec/compile/client.py` and `backends.py` are test doubles / real API callers, not
the prompt — `MockClient` may read the committed artifact to build a canned response,
because it is standing in for the model's *output*, not assembling the model's
*input*. The line is: nothing that *builds the prompt* may see the answer key.

## Why this matters

Without demotion, a compiler that "passes the gates" might only be echoing an answer
it was shown. The gates prove the artifact is correct; demotion proves the compiler
earned it from the criteria. Together they are the difference between a build system
and a lookup.
