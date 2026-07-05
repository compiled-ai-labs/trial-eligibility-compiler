# /compile — trial-eligibility-compiler (Cursor agent-driven path)

You (Cursor) are the compile-time LLM. Follow AGENTS.md exactly.

**Answer-key demotion (non-negotiable):** read ONLY `source/NCT03667300.md` and
`compiled/NCT03667300/vocab/*.json`. Do NOT read `manifest.json`, `cohort.json`,
`conventions.json`, anything under `fixtures/`, `corpus-plan.md`, or
`fixture-plan.md`.

Produce `cohort.json` (standard OHDSI Circe; determinate criteria only, each a
named inclusion rule; concept ids from vocab/ only), `manifest.json` (16 ids with
dispositions + provenance; AMBIGUOUS ⇒ concepts=[] & cohort_rule=null), and
`conventions.json`. Apply the compile/refuse rule — refuse (AMBIGUOUS) rather than
invent membership or encode a human judgment. Serialise canonically.

Run `python -m pytest -q`. On a Gate 1/2 failure, fix that exact error and re-emit.
Never weaken a gate. Do not commit; show the gate summary and the diff.

Programmatic equivalent: `trcompile build --backend cursor`.
