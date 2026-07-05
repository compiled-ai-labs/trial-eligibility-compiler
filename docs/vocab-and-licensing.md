# Vocabulary and licensing

The compiler wires determinate criteria to standard OMOP concepts. Those concept
sets are **curated, committed input** — not compiler output, and not something the
model may invent. This doc covers what is committed, why it is redistributable, and
how it is pinned.

## What is committed

Under `compiled/NCT03667300/vocab/` there is one JSON per concept set (nine sets):
`t2dm`, `hba1c`, `uacr`, `egfr`, `arb_acei`, `bmi`, `dm_other`, `ast_alt`,
`dpp4_glp1`. Each file holds integer `concept_id`s, our own labels, provenance, and
an `include_descendants` flag. Domains follow the OMOP standard: conditions → SNOMED,
labs → LOINC, drugs/classes → RxNorm.

The synthetic CDM's vocabulary tables are committed as CSV seeds under
`fixtures/cdm/`: `concept`, `concept_ancestor`, `concept_relationship`, `vocabulary`.
These are generated from a single authoritative concept table so that `vocab/*.json`,
`concept.csv`, and the fixtures cannot drift.

Two concepts — itraconazole (1358907) and gastrectomy (4001636) — exist in
`concept.csv` but belong to **no** concept set. They exist only so the AMBIGUOUS
probes (E6, E2) can carry data that the executed cohort deliberately does not test.

## Membership is curated, never invented

The compiler may read `vocab/` (resolution A — see
[answer-key-demotion.md](answer-key-demotion.md)) and must use only those concepts.
Inventing a `concept_id` — emitting one not present in `vocab/` — fails Gate 1. A
criterion with no vocabulary-native set (a DDI-strength category, an investigator
catch-all) is `AMBIGUOUS`, not a guessed set. This is the line between "compile" and
"hallucinate."

## Is the committed subset redistributable?

- **The criteria prose is US public record.** Registered ClinicalTrials.gov criteria
  are committable without question.
- **The vocabulary subset is the real question, and the answer is precedent.**
  OHDSI's own **Eunomia** package publicly redistributes a small OMOP CDM — including
  a subset of the Standardized Vocabularies — as file-based test data. A minimal
  vocabulary subset for testing/demonstration is established, accepted practice.
- **Per-vocabulary terms.** LOINC (open) and RxNorm (NLM, freely available) cover the
  labs and drugs cleanly. **SNOMED CT** (conditions) carries an affiliate/UMLS regime
  where blanket redistribution is restricted in non-member territories.
- **The conservative route adopted here.** The repo commits **concept-set
  definitions** (integer ids + our own labels + provenance), not a bulk vocabulary
  export. Nothing beyond a test-scale, purpose-restricted subset — matching what
  OHDSI itself already ships. The `concept_id`s in this PoC are synthetic-but-plausible
  pinned values for a self-contained demo, not a curated production mapping.

Net: the vocabulary subset is committable; the one nuance (SNOMED) is handled by the
Eunomia-precedent / pinned-subset route, documented rather than left as a blocker.

## Pinning and versioning

`conventions.json` records the `vocab_snapshot` (`athena-v5-2023q3 (pinned synthetic
subset)`). Concept mappings are pinned to that snapshot — a different Athena version
can shift descendant sets, so the snapshot id is part of the artifact's provenance.
To move snapshots: update the snapshot id, regenerate the concept sets, recompile,
and re-run the gates; the boundary/behaviour gates will flag any resulting change.

For a production build, replace the synthetic pinned ids with a real Athena subset
built the Eunomia way (in CI, restricted to the pinned concept list) — the shape of
the committed artifact does not change.
