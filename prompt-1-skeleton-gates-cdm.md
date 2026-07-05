# Prompt 1 — skeleton + gates + synthetic CDM

Paste into Claude Code in a fresh `trial-eligibility-compiler` repo that already
contains `PLAN.md`, `CLAUDE.md`, `corpus-plan.md`, `fixture-plan.md`.

---

```
Read CLAUDE.md and PLAN.md fully first. Obey every hard invariant in CLAUDE.md.

This is STAGE 1 of 3. Goal: stand up the repo skeleton, the four gates, the
synthetic OMOP CDM, and the deterministic runtime — WITHOUT the LLM compiler.
A hand-authored, correct artifact will make the whole gate suite go green, so
that Stages 2 and 3 have a fixed target to reproduce. Do NOT write any part of
tec/compile/ in this stage. Do NOT wire any Anthropic client.

Seed trial: NCT03667300. Build exactly the layout in PLAN.md §3.

TASK 1 — scaffold.
- pyproject.toml with console_scripts trcompile and trcheck (trcompile may be a
  stub that exits with "not implemented until Stage 2").
- .devcontainer with Python 3.11 + R + JDK + duckdb, pinning R packages CirceR,
  SqlRender, DatabaseConnector via renv. .github/workflows/ci.yml that runs
  pytest offline inside that image.
- tec/schema/manifest.schema.json and fixture.schema.json per PLAN.md §4.

TASK 2 — the immutable source spec.
- source/NCT03667300.md: the verbatim eligibility criteria below, each sentence
  tagged with a stable id. Do not paraphrase.
    Inclusion:
      [I1] Men and women aged 20 years or older diagnosed with type 2 diabetes.
      [I2] Subjects diagnosed with type 2 diabetes.               # (diagnosis anchor)
      [I3] Subjects having HbA1c 7.0% or more, and 10% or less.
      [I4] Subjects having urine albumin to creatinine ratio (UACR) 30 ug/mg or more, and 3000 ug/mg or less.
      [I5] Subjects having estimated glomerular filtration rate (eGFR) 30 or more.
      [I6] Subjects who had taken an ARB or ACE inhibitor for more than 4 weeks.
      [I7] Subjects having body mass index (BMI) 20 kg/m2 or more, 40 kg/m2 or less.
      [I8] Subjects who entirely understood the study and voluntarily consented.
    Exclusion:
      [E1] Subjects having type 1 diabetes, secondary diabetes, or gestational diabetes.
      [E2] Subjects who had a history of resection of more than a half length of stomach or intestine.
      [E3] Subjects having more than three-fold higher levels of AST or ALT than upper normal limit.
      [E4] Subjects who had taken a DPP4-inhibitor or GLP-1 analogue within 8 weeks prior to screening.
      [E5] Subjects who had taken oral triple hypoglycemic agents within 8 weeks prior to screening.
      [E6] Subjects taking strong CYP3A4 inhibitors or strong CYP3A4 inducers.
      [E7] Subjects who are pregnant or breastfeeding.
      [E8] Subjects unsuitable for participation based on clinical laboratory results or other reasons.
  (Note: I1 folds age+diagnosis in the registered text; keep I1 verbatim and use
  I2 as the diagnosis anchor id. Preserve the wording; only the ids are ours.)

TASK 3 — hand-authored committed artifact (the fixed target).
Build compiled/NCT03667300/ by hand, following PLAN.md §4 and §8 exactly:
- cohort.json: a valid, standard OHDSI Circe CohortExpression. Determinate
  criteria only (I1–I7, E1, E3, E4), each as a NAMED Circe inclusion rule so
  per-criterion attrition is reportable. Pin concept sets by concept_id.
- manifest.json: 16 entries (I1–I8, E1–E8), each with source_span, disposition,
  rationale, cohort_rule, concepts — matching the disposition table in PLAN.md
  §8 (10 determinate, 6 AMBIGUOUS: I8, E2, E5, E6, E7, E8).
- conventions.json: pinned ULN (state the value + a cited source),
  ">4 weeks = >=29 days", inclusivity of each numeric bound, HbA1c unit handling.
- vocab/: concept-set definitions (integer concept_id + our label + provenance)
  for every concept referenced by cohort.json. Keep it minimal.
Serialise all JSON canonically (sorted keys, fixed float format) so it is
byte-stable.

TASK 4 — synthetic OMOP CDM + fixtures.
- fixtures/cdm/: committed CSV seeds for a minimal OMOP v5.4 CDM (person,
  observation_period, condition_occurrence, measurement, drug_exposure,
  visit_occurrence) plus the pinned vocab tables (concept, concept_ancestor,
  concept_relationship, vocabulary). All synthetic. Screening/index date
  2023-06-01.
- tec/runtime/cdm.py: build a duckdb CDM from a fixture YAML + the committed vocab.
- fixtures/patients/*.yaml per fixture.schema.json, each declaring expected
  per-criterion labels. Author, at minimum:
    * one MATCH and one NO-MATCH per determinate criterion (I1–I7, E1, E3, E4),
    * the boundary set from PLAN.md §5 Gate 4 (eGFR 30/29.9; HbA1c 7.0/6.9,
      10.0/10.1; UACR 30/29, 3000/3001; BMI 20/40 edges; AST 120/121 at pinned
      ULN; ARB/ACE 28/29 days),
    * two AMBIGUOUS probes: a patient on itraconazole (E6) and a patient with a
      bariatric-surgery procedure (E2), each asserting the criterion is reported
      AMBIGUOUS and does NOT change membership.

TASK 5 — the four gates (tec/gates/) exactly per PLAN.md §5.
- g1_structure.py, g2_coverage.py: pure Python.
- g3_fixtures.py: build the duckdb CDM, run cohort.json through
  tec/runtime/ohdsi_bridge.R (CirceR -> SqlRender "duckdb" -> DatabaseConnector,
  generateStats=TRUE), compare membership + inclusion-rule attrition to expected
  labels; assert AMBIGUOUS criteria are absent from the executed logic.
- g4_determinism.py: hash the committed artifact; assert the boundary fixtures
  produce the pinned edges. (The recompile-equality half of Gate 4 is a no-op
  placeholder in Stage 1 — there is no compiler yet — leave a clearly marked TODO
  that Stage 2 fills in.)
- Wire all four into pytest.

TASK 6 — trcheck runtime.
Implement trcheck evaluate --patient <fixture.yaml> per PLAN.md §7: build the
one-person CDM, execute via the bridge, print the per-criterion table
(INCLUDED/EXCLUDED from attrition; AMBIGUOUS from manifest, never executed) with
each source_span. No API key, no network.

STOP CONDITION. Deliverable: `pytest` and CI are fully green against the
hand-authored artifact and fixtures, and a sample
`trcheck evaluate --patient fixtures/patients/<a match>.yaml` prints a correct
per-criterion table including at least one AMBIGUOUS row. Present the gate
results and one sample trcheck run. Do not start the compiler.
```
