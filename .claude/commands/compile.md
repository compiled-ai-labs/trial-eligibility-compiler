Compile the trial eligibility cohort (agent-driven path — you are the LLM).

Obey CLAUDE.md. This is answer-key demotion: read ONLY `source/NCT03667300.md`
and `compiled/NCT03667300/vocab/*.json`. Do NOT open `manifest.json`,
`cohort.json`, `conventions.json`, anything under `fixtures/`, `corpus-plan.md`,
or `fixture-plan.md`.

Then:
1. Produce `cohort.json` (standard OHDSI Circe; determinate criteria only —
   I1–I7, E1, E3, E4 — each a NAMED inclusion rule; concept sets by concept_id
   from vocab/ only), `manifest.json` (all 16 ids I1–I8, E1–E8 with disposition +
   rationale + provenance; AMBIGUOUS ⇒ concepts=[] and cohort_rule=null), and
   `conventions.json` (pinned ULN, day-counts, numeric-bound inclusivity).
2. Apply the compile/refuse rule: compile only if you add a writable convention;
   refuse (AMBIGUOUS) if you would invent membership or encode a human judgment.
   A compound criterion is only as determinable as its weakest part.
3. Serialise canonically (sorted keys, 2-space indent, LF, trailing newline).
4. Run `python -m pytest -q`. If Gate 1 (structure) or Gate 2 (coverage) fails,
   fix exactly that error and re-emit. Never weaken a gate.

Do not commit. Show the gate summary and the diff against the current artifact.
