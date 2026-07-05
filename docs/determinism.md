# Determinism

The runtime must produce the same verdict forever. That property is manufactured in
two places: canonical serialisation of the artifact, and a recompile-equality gate
that fails on any drift.

## Canonical JSON

Every committed artifact file is written through `tec/canonical.py`:

- keys sorted;
- UTF-8, no ASCII escaping;
- 2-space indent, standard separators;
- floats via Python's shortest round-trip repr;
- a single trailing newline, `\n` line endings only (never CRLF, even on Windows —
  `canonical.write` writes bytes).

`canonical.sha256(obj)` hashes the canonical serialisation, so two artifacts are
equal iff their bytes are. Gate 4 re-serialises each committed file and asserts it
already equals the on-disk bytes — i.e. the file is canonical, so a correct recompile
can be byte-identical.

## Recompile-equality

`tec/compile/recompile.py` compiles the trial to a temp directory with a given client
and diffs the three output files against the committed artifact. `recompile_diff`
returns the differing files (empty ⇒ byte-identical); `recompile_equals_committed`
returns the boolean.

This is what catches the regression the paradigm most cares about: **someone edited a
spec but did not recompile.** It runs in `tests/test_compiler.py` and as an explicit
CI step (`trcompile build --backend mock --out /tmp/recompiled`, then `cmp` each file
against `compiled/NCT03667300/`). CI uses the mock so the check is credential-free and
network-free.

## Pinned inputs

Determinism of a *real* compile depends on pinning its inputs, recorded in
`conventions.json` and the environment:

- **Model / backend.** The API backend pins `claude-opus-4-8` (override with
  `TRCOMPILE_MODEL`); a real compile records the actual backend + model.
- **Python deps** via `uv` / `pyproject.toml`; **R package versions** pinned in
  `scripts/install_ohdsi.R`; **vocabulary snapshot** via `conventions.vocab_snapshot`.

## The temperature caveat (be honest)

The staged plan says "temperature = 0". The pinned model **`claude-opus-4-8` removed
`temperature`/`top_p`/`top_k`** — sending them returns a 400. So the API backend does
**not** set a sampling temperature; it uses `effort: "low"` for the most consolidated
output. The committed hand-authored `conventions.json` still carries `temperature: 0`
as the recorded intent, but it is not what enforces determinism.

This is honest and, per the model migration guidance, more correct anyway:
`temperature = 0` never guaranteed identical outputs. **Determinism is enforced by
Gate 4 (byte-identical recompile), not by a sampling knob.** If a real backend
produces a non-byte-stable artifact across two compiles, that is a fact the gate
surfaces — tighten the prompt/serialisation, or accept and document residual
nondeterminism; do not weaken the gate.

## What determinism does and does not guarantee

- **Guarantees:** the committed artifact is byte-stable, hashable, and reviewable;
  the runtime reruns it identically; an un-recompiled spec edit is caught.
- **Does not guarantee:** that any given LLM is deterministic. The paradigm does not
  require the model to be deterministic — it requires the *committed output* to be,
  and makes model drift observable through the recompile diff. The gates are the
  guarantee; the LLM is replaceable labour.
