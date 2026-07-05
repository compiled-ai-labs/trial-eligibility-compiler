Audit this repo for drift from the Compiled AI five-part shape. Read-only.

Verify each part is present and intact:
1. **Prose input spec** — `source/*.md` verbatim, stable sentence ids, immutable.
2. **Compiler** — `tec/compile/` reads ONLY `source/*.md` + `vocab/`; the retry loop
   validates candidates against Gates 1 & 2 before writing; never commits unvalidated
   output. Confirm `tests/test_answer_key_demotion.py` still passes.
3. **Validation gates** — `tec/gates/g1..g4`; parse + lint + functional verdict on
   known-failing and known-passing fixtures; AMBIGUOUS never touches the executable.
4. **Committed artifact** — `compiled/<trial>/` reviewable, versioned, canonical.
5. **Runtime** — `trcheck` delegates to standard OHDSI (CirceR/SqlRender/
   DatabaseConnector); no LLM, no hand-written cohort SQL.

Also check: answer-key demotion holds; determinism (recompile-equality) is wired;
CI runs all four gates with `--backend mock`. Report any part that is missing,
weakened, or drifting — do not fix, just report.
