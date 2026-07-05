# PLAN.md — trial-eligibility-compiler

Fourth reference implementation in `github.com/compiled-ai-labs`. Same five-part
shape as `tax-rules-compiler`. PoC scope: **one trial, one runtime command,
refusal as a first-class output.**

> An LLM runs at **compile time only**. It reads verbatim ClinicalTrials.gov
> eligibility prose and emits a deterministic **OHDSI Circe cohort definition**,
> committed only after passing four machine-checkable gates. The runtime that
> consumes the artifact is **unmodified standard OHDSI tooling** — no model in
> the path. Indeterminate criteria compile to **AMBIGUOUS**, never to a guess.

Read `corpus-plan.md` and `fixture-plan.md` first — this file is scoped from them.

---

## 1. Scope

- **Seed trial:** `NCT03667300` (evogliptin on albuminuria in T2D + renal
  insufficiency). Chosen because it carries the three demo anchors in one trial:
  a first-class **CYP3A4 refusal**, an **AST >3× ULN compile-with-documented-
  assumption**, and an **eGFR = 30 boundary**.
- **One runtime command:** `trcheck evaluate --patient <fixture.yaml>` → prints,
  per criterion, `INCLUDED` / `EXCLUDED` / `AMBIGUOUS` with a pointer to the
  source sentence.
- **One compile command:** `trcompile build --trial NCT03667300` → produces the
  committed artifact (compile-time only; the API key is never needed to run
  `trcheck`).
- **Non-goals (state in README):** not an extraction benchmark; not
  recruitment-ready patient counts; not clinically validated; four hand-picked
  criteria sets from one therapeutic area, synthetic fixtures only.

## 2. The five-part shape (mapped to this repo)

1. **Prose input spec** — `source/NCT03667300.md`: verbatim criteria, immutable,
   every sentence carries a stable id (`I1..I8`, `E1..E8`). This is the *only*
   thing the compile prompt is allowed to read.
2. **LLM compiler with retry loop** — `tec/compile/`: prose → candidate artifact
   → fast gates (1,2) → on failure, feed gate errors back, retry ≤ N → hard-fail
   if still red. Never commits an unvalidated artifact.
3. **Four validation gates** — `tec/gates/` (see §5).
4. **Committed artifact folder** — `compiled/NCT03667300/` (see §4).
5. **Deterministic runtime tool** — `trcheck`, delegating cohort execution to
   standard OHDSI (`CirceR` → `SqlRender` → `DatabaseConnector` → duckdb).

## 3. Repo layout

```
trial-eligibility-compiler/
├── CLAUDE.md
├── PLAN.md
├── corpus-plan.md
├── fixture-plan.md
├── README.md                      # written in Stage 3
├── pyproject.toml                 # console_scripts: trcompile, trcheck
├── .devcontainer/                 # pinned image: Python 3.11 + R + JDK + duckdb
├── .github/workflows/ci.yml       # runs all four gates offline
├── source/
│   └── NCT03667300.md             # verbatim criteria, stable sentence ids
├── tec/
│   ├── compile/                   # LLM compiler + retry loop  (Part 2)
│   │   ├── client.py              # Anthropic client, mockable
│   │   ├── prompt.py              # compile prompt (reads ONLY source/*.md)
│   │   └── compiler.py
│   ├── gates/                     # Part 3
│   │   ├── g1_structure.py
│   │   ├── g2_coverage.py
│   │   ├── g3_fixtures.py
│   │   └── g4_determinism.py
│   ├── runtime/                   # Part 5
│   │   ├── trcheck.py             # CLI entry
│   │   ├── cdm.py                 # build single-patient duckdb CDM from fixture
│   │   └── ohdsi_bridge.R         # CirceR/SqlRender/DatabaseConnector executor
│   └── schema/
│       ├── manifest.schema.json   # our envelope (dispositions + provenance)
│       └── fixture.schema.json
├── compiled/
│   └── NCT03667300/               # Part 4 — the committed artifact
│       ├── cohort.json            # canonical OHDSI Circe CohortExpression
│       ├── manifest.json          # per-criterion disposition + provenance
│       ├── conventions.json       # pinned boundaries / ULN / day-counts
│       └── vocab/                 # pinned concept sets referenced by cohort.json
└── fixtures/
    ├── cdm/                       # committed synthetic OMOP CDM seeds (CSV)
    └── patients/                  # *.yaml, each with expected labels
```

## 4. The committed artifact (envelope)

Two files, deliberately separated so the AMBIGUOUS surface can **never** enter
the executable:

- **`cohort.json`** — a *pure, standard* OHDSI Circe `CohortExpression`. Contains
  only the determinate criteria. Each determinate criterion is a **named Circe
  inclusion rule** (this is what lets `trcheck` report per-criterion pass/fail
  via inclusion-rule attrition stats). Stock ATLAS/CirceR can load this file
  unchanged.
- **`manifest.json`** — our provenance/audit layer. One entry per source
  sentence:

```json
{
  "criterion_id": "E6",
  "source_span": "subjects taking strong CYP3A4 inhibitors or strong CYP3A4 inducers",
  "disposition": "AMBIGUOUS",
  "rationale": "DDI-strength category has no vocabulary-native standard concept set; membership requires an external curated list (FDA DDI guidance).",
  "cohort_rule": null,
  "concepts": []
}
```

Invariants (enforced by gates, not convention):
- `disposition ∈ {INCLUDE, EXCLUDE, AMBIGUOUS}`.
- `AMBIGUOUS` ⇒ `concepts == []` **and** `cohort_rule == null` (cannot touch the
  executable).
- `INCLUDE|EXCLUDE` ⇒ `cohort_rule` names a rule present in `cohort.json`, and
  every referenced `concept_id` exists in `compiled/**/vocab/`.
- Exactly one manifest entry per source sentence id, and vice-versa (bijection).

## 5. The four gates

Gates 1–2 are pure Python (fast, JVM-free) and run inside the compiler retry
loop. Gates 3–4 execute the artifact and run in CI.

- **Gate 1 — Structure.** `cohort.json` validates against the Circe JSON schema;
  `manifest.json` validates against `manifest.schema.json`; all §4 invariants
  hold; every concept referenced exists in the pinned `vocab/`.
- **Gate 2 — Coverage / anti-hallucination.** Bijection between source sentence
  ids (`source/NCT03667300.md`) and manifest entries. **No dropped criterion**
  (silent omission) and **no invented criterion** (entry with no matching source
  span). This is the gate that makes "the compiler didn't quietly ignore a line"
  machine-checkable.
- **Gate 3 — Fixtures / behaviour.** Build the synthetic duckdb CDM, execute
  `cohort.json` via the OHDSI bridge with `generateStats=TRUE`, and for every
  patient fixture assert actual membership + per-rule attrition == the fixture's
  expected labels. Assert every `AMBIGUOUS` criterion is absent from the executed
  logic (it cannot change any patient's disposition).
- **Gate 4 — Determinism + boundaries.** Recompile from source → artifact is
  **byte-identical** (stable JSON serialisation, sorted keys); committed artifact
  == recompiled (no drift). Boundary fixtures (eGFR 30/29.9; HbA1c 7.0/6.9,
  10.0/10.1; UACR 30/29, 3000/3001; BMI 20/40 edges; AST 120/121 at pinned ULN;
  ARB/ACE 28/29 days) produce the pinned edge results.

## 6. Compiler + retry loop (Part 2)

```
read source/NCT03667300.md            # ONLY input to the prompt
  → LLM → candidate cohort.json + manifest.json
  → Gate 1 (structure) + Gate 2 (coverage)
      ├─ pass → write to compiled/NCT03667300/  (Gates 3,4 run in CI)
      └─ fail → append gate errors to prompt, retry (≤ 3)
                 exhausted → hard error, exit non-zero, commit nothing
```

- The Anthropic client (`tec/compile/client.py`) is behind an interface so
  Stage 2 injects a deterministic **mock** (canned valid artifact) → the whole
  pipeline and all gates run in CI with no API key and no network.
- **Answer-key demotion (hard rule):** fixtures, expected labels,
  `corpus-plan.md`, `fixture-plan.md`, and any external structured-criteria
  dataset (Chia, n2c2) are **never** read by `tec/compile/prompt.py`. The prompt
  reads `source/*.md` and nothing else. Enforced by review + a lint check on the
  prompt module's imports/reads.

## 7. Runtime (Part 5)

`trcheck evaluate --patient fixtures/patients/p_match.yaml`:
1. `tec/runtime/cdm.py` builds a one-person duckdb OMOP CDM from the fixture YAML
   + the pinned `vocab/`.
2. `ohdsi_bridge.R`: `CirceR::buildCohortQuery` → `SqlRender::translate("duckdb")`
   → `DatabaseConnector` executes with `generateStats=TRUE`.
3. Print a per-criterion table: for each `manifest` entry → `INCLUDED` /
   `EXCLUDED` (from inclusion-rule attrition) or `AMBIGUOUS` (from manifest,
   never executed), each with its `source_span`.

Runtime needs **no API key and no network.** `trcompile` needs the API key;
`trcheck` never does.

## 8. Pinned per-criterion decisions (seed NCT03667300)

Applying the compile/refuse rule ("compile if you only add a writable convention;
refuse if you'd invent membership or encode a human judgment"):

| id | criterion | disposition |
|----|-----------|-------------|
| I1 | age ≥ 20 | INCLUDE |
| I2 | T2D diagnosis | INCLUDE |
| I3 | HbA1c 7.0–10% | INCLUDE |
| I4 | UACR 30–3000 µg/mg | INCLUDE |
| I5 | eGFR ≥ 30 | INCLUDE |
| I6 | ARB or ACE-I > 4 weeks | INCLUDE (pin ">4 wk = ≥29 days continuous") |
| I7 | BMI 20–40 | INCLUDE |
| I8 | consent / willingness | **AMBIGUOUS** (non-clinical; not evaluable over any CDM) |
| E1 | T1 / secondary / gestational diabetes | EXCLUDE |
| E2 | resection of >½ stomach/intestine | **AMBIGUOUS** (extent ">½" not in data) |
| E3 | AST or ALT > 3× ULN | EXCLUDE (pin ULN; documented assumption, cited) |
| E4 | DPP4i or GLP-1 within 8 weeks | EXCLUDE |
| E5 | oral triple hypoglycemic agents within 8 weeks | **AMBIGUOUS** (undefined count/combination) |
| E6 | strong CYP3A4 inhibitors/inducers | **AMBIGUOUS** (no vocabulary-native strength set) |
| E7 | pregnant or breastfeeding | **AMBIGUOUS** (compound criterion is only as determinable as its weakest disjunct — breastfeeding is poorly coded) |
| E8 | unsuitable per labs / other reasons | **AMBIGUOUS** (investigator-discretion catch-all) |

Determinate (in `cohort.json`): 10/16 = **62.5%** → clears the 60% bar. AMBIGUOUS
suite: 6 criteria (I8, E2, E5, E6, E7, E8) — the tested refusal surface.

`conventions.json` records every pinned choice (ULN value + source, "6 months"
and "4 weeks" day-counts and inclusivity, HbA1c unit handling) as auditable,
one-line-editable metadata.

## 9. Vocabulary / CDM

Per `corpus-plan.md` §TASK 2: conditions → SNOMED, drugs/classes → RxNorm/ATC,
labs → LOINC. Commit **concept-set definitions** (integer ids + our labels +
provenance) under `compiled/**/vocab/`; build the CI test CDM the Eunomia way
(pinned subset), never a bulk SNOMED export. duckdb backend (date handling).

## 10. Determinism requirements

Canonical JSON serialisation (sorted keys, fixed float formatting, `\n` endings)
so recompilation is byte-stable. Gate 4 hashes the artifact and fails on any
drift. Pin: Python deps, R package versions (renv), vocabulary snapshot version,
model id + temperature=0 for compile.

## 11. Limitations (specific — goes in README, verbatim-ish)

- Four hand-picked criteria sets, one therapeutic area — **not a benchmark**;
  answer-key demotion forbids training/evaluating on Chia or n2c2 as input.
- Fixtures are hand-authored synthetic; expected labels are author-asserted, not
  clinically adjudicated.
- Concept mappings are pinned to one Athena vocabulary snapshot; a different
  version can shift descendant sets.
- Boundary/ULN/day-count conventions are **chosen and documented**, not
  authoritative — see `conventions.json`.
- AMBIGUOUS rate is high **by design**: this produces auditable phenotypes, not
  recruitment-ready patient counts.

## 12. Staging (the three Claude Code prompts)

- **Prompt 1 — skeleton + gates + synthetic CDM.** Repo scaffold, `source/*.md`,
  schemas, Gates 1–4, `trcheck` runtime + OHDSI bridge, synthetic duckdb CDM +
  fixtures. Compiler absent; a **hand-committed** correct artifact makes the gate
  suite go green. Deliverable: `pytest` + CI all green against the committed
  artifact and fixtures.
- **Prompt 2 — compiler with mocked client.** Implement `tec/compile/` + retry
  loop; inject a deterministic mock client returning a valid artifact; wire the
  answer-key-demotion lint. Deliverable: `trcompile build --trial NCT03667300`
  reproduces the committed artifact from the mock, all gates green, no network.
- **Prompt 3 — real compile + demo assets.** Wire the real Anthropic client
  (temperature 0, pinned model); run a real compile to regenerate the committed
  artifact; write README (30-second demo: one `trcheck` run showing a match, an
  exclusion, a boundary, and the CYP3A4 AMBIGUOUS-with-provenance), LIMITATIONS,
  and the determinism/CI badges.
