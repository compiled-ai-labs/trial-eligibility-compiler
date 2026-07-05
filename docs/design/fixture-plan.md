# fixture-plan.md — trial-eligibility-compiler runtime + fixtures

Companion to `corpus-plan.md`. Confirms the execution path is standard OHDSI,
offline, and CI-runnable, then specifies the synthetic patient fixtures **as
implemented**. **No real patient data anywhere — every row below is hand-authored.**

> **Seed pinned to T3 (NCT03667300).** An earlier draft of this file was written
> around T1 (NCT03985293); the implemented PoC uses **NCT03667300**, matching
> PLAN.md. All fixtures below reference the 16 criteria I1–I8 / E1–E8 of that trial.
>
> **Curated-vocab decision (resolution A).** Concept sets live under
> `compiled/NCT03667300/vocab/*.json` and are curated *input* the compile prompt
> may read. The answer key the prompt must never see is: the fixtures below, their
> expected labels, the manifest dispositions, and Chia/n2c2.

---

## TASK 3a — Runtime path (confirmed concrete)

**Artifact format:** OHDSI **Circe cohort-definition JSON** (`circe-be`
`CohortExpression` — the object ATLAS exports and the PhenotypeLibrary stores).
Committed as `compiled/NCT03667300/cohort.json`.

**Execution chain, no model in the path:**

```
Circe cohort JSON (artifact)
   │  CirceR::cohortExpressionFromJson()  →  CirceR::buildCohortQuery(generateStats=TRUE)
   ▼
OHDSI SQL (SqlRender @-parameterised; temp tables + concept_ancestor)
   │  SqlRender::translate(targetDialect = "duckdb")   +   DatabaseConnector
   ▼
duckdb OMOP CDM (synthetic)  →  cohort + cohort_inclusion_result (per-rule attrition)
```

Every stage is unmodified standard OHDSI (`CirceR`, `SqlRender`,
`DatabaseConnector`), driven by `tec/runtime/ohdsi_bridge.R`. `trcheck` only
orchestrates — it authors no cohort logic and hand-writes no SQL. Per-criterion
`INCLUDED`/`EXCLUDED` comes from the inclusion-rule bitmask; `AMBIGUOUS` comes from
`manifest.json` and is never executed.

**duckdb over SQLite:** Circe cohort SQL is date-heavy (drug within 56 days, labs
within 180 days, ARB/ACE ≥29 days), and duckdb has better date-type support.

**Concept-set expansion offline:** the synthetic CDM carries `concept`,
`concept_ancestor`, `concept_relationship`, `vocabulary` (the pinned subset), so
descendant expansion resolves locally with no Athena call.

---

## TASK 3b — Synthetic OMOP CDM instance

- **Engine:** duckdb file, built per fixture by `tec/runtime/cdm.py` from the
  fixture YAML + the committed vocab CSV seeds in `fixtures/cdm/`. Minimal OMOP
  v5.4 layout.
- **Vocabulary tables (committed, shared):** `concept`, `concept_ancestor`,
  `concept_relationship`, `vocabulary` — the pinned subset (Eunomia-precedent
  route from `corpus-plan.md` TASK 2). Generated from one authoritative concept
  table so `vocab/*.json`, `concept.csv`, and the fixtures cannot drift.
- **Clinical tables (per-patient):** `person`, `observation_period`,
  `visit_occurrence`, `condition_occurrence`, `measurement`, `drug_exposure`,
  `procedure_occurrence` — populated from the fixture YAML.
- **Index date:** every fixture carries one `visit_occurrence` (the screening
  visit) on **2023-06-01**; that visit is the cohort's index event, so every
  temporal window is evaluated relative to it deterministically.

Pinned `concept_id`s (illustrative-but-consistent; the same integers appear in
`vocab/`, `concept.csv`, and the fixtures): T2DM 201826, T1DM 201254, secondary
195771, gestational 4024659; HbA1c 3004410, UACR 3034485, eGFR 3049187, BMI
3038553, AST 3013721, ALT 3006923; ARB/ACE-I ingredients (losartan 1367500,
valsartan 1308842, lisinopril 1308216, enalapril 1341927); DPP-4i/GLP-1
(sitagliptin 1580747, linagliptin 43526465, liraglutide 45774435, exenatide
1583722). Two standalone concepts belong to **no** set and exist only for the
AMBIGUOUS probes: itraconazole 1358907, gastrectomy 4001636.

---

## TASK 3c — Fixtures (implemented: 29 synthetic patients)

Every fixture asserts expected labels for all 16 criteria plus overall
`expected_membership`. Determinate criteria (I1–I7, E1, E3, E4) are checked against
CirceR attrition in Gate 3; AMBIGUOUS criteria (I8, E2, E5, E6, E7, E8) are always
`AMBIGUOUS` and must never change membership.

**Base match — `p_match`.** T2DM dx; HbA1c 8.0, UACR 300, eGFR 45, BMI 28, AST 30;
losartan 151-day exposure. All determinate rules satisfied → **IN**.

**No-match, one determinate criterion failing each** (derived from `p_match`):

| fixture | change | fails | membership |
|---|---|---|---|
| `nm_i1_age` | born 2010 (age 13) | I1 | OUT |
| `nm_i2_t2dm` | no T2DM condition | I2 | OUT |
| `nm_i3_hba1c` | HbA1c 6.5 | I3 | OUT |
| `nm_i4_uacr` | UACR 10 | I4 | OUT |
| `nm_i5_egfr` | eGFR 24 (README EXCLUDE example) | I5 | OUT |
| `nm_i6_arbace` | no ARB/ACE exposure | I6 | OUT |
| `nm_i7_bmi` | BMI 45 | I7 | OUT |
| `nm_e1_otherdm` | + type 1 diabetes | E1 | OUT |
| `nm_e3_ast` | AST 200 (>3× ULN) | E3 | OUT |
| `nm_e4_dpp4` | + sitagliptin within 8 wk | E4 | OUT |

---

## TASK 3d — Boundary cases (the pinned-edge set) + inclusivity findings

Boundaries are where determinism is won or lost. Where the text gives the operator
(`≥`, `≤`) the edge is determinate; the fixtures pin it. The AST edge is a *chosen,
documented* convention (`conventions.json` ULN = 40 U/L, 3× = 120 U/L), and the
ARB/ACE edge pins the prose ">4 weeks" as ≥29 days.

| fixture | value | criterion | expected |
|---|---|---|---|
| `b_egfr_30` / `b_egfr_29_9` | eGFR 30 / 29.9 | I5 (≥30) | INCLUDED / EXCLUDED |
| `b_hba1c_70` / `b_hba1c_69` | HbA1c 7.0 / 6.9 | I3 (≥7.0) | INCLUDED / EXCLUDED |
| `b_hba1c_100` / `b_hba1c_101` | HbA1c 10.0 / 10.1 | I3 (≤10) | INCLUDED / EXCLUDED |
| `b_uacr_30` / `b_uacr_29` | UACR 30 / 29 | I4 (≥30) | INCLUDED / EXCLUDED |
| `b_uacr_3000` / `b_uacr_3001` | UACR 3000 / 3001 | I4 (≤3000) | INCLUDED / EXCLUDED |
| `b_bmi_20` / `b_bmi_40` | BMI 20 / 40 | I7 (both edges incl.) | INCLUDED / INCLUDED |
| `b_ast_120` / `b_ast_121` | AST 120 / 121 | E3 (>3× ULN = >120) | INCLUDED / EXCLUDED |
| `b_arbace_29d` / `b_arbace_28d` | days_supply 29 / 28 | I6 (>4 wk ≡ ≥29 d) | INCLUDED / EXCLUDED |

**Boundary-inclusivity as an output class:** where the text gives only prose (">4
weeks") the compiler pins a convention **and records it as an explicit, reviewable
assumption** in `conventions.json` — never a silent guess. A local, JVM-free
differential oracle cross-checks every fixture's asserted labels against those
pinned conventions (Gate 4); CirceR execution (Gate 3) confirms the artifact
reproduces them.

---

## TASK 3e — First-class AMBIGUOUS fixtures (the differentiator)

- **`p_cyp3a4_itraconazole`** — `drug_exposure(itraconazole 1358907, start
  2023-05-15)`. The trial's "strong CYP3A4 inhibitors" exclusion (E6) compiled to
  **AMBIGUOUS** — no vocabulary-native strength set (`corpus-plan.md` TASK 2). Gate
  assertion: E6 reports **AMBIGUOUS with provenance to the source sentence** and
  **never** silently excludes person 950 — even though a "helpful" guess
  (itraconazole *is* a strong CYP3A4 inhibitor) would be correct. Refusing to guess
  is the tested behaviour; membership stays **IN**.
- **`p_bariatric_e2`** — `procedure_occurrence(gastrectomy 4001636, 2019-05-01)`.
  E2 ("resection of more than a half length of stomach/intestine") compiled to
  **AMBIGUOUS** because the extent qualifier isn't in the data. Emits AMBIGUOUS, not
  EXCLUDED; membership stays **IN**.

---

## TASK 3f — Offline CI confirmation

The full loop runs with **no external services**:

1. CI installs R + `CirceR`/`SqlRender`/`DatabaseConnector` (+ JDK) and duckdb via
   the pinned `scripts/install_ohdsi.R`; Python deps via pip.
2. `tec/runtime/cdm.py` builds each synthetic duckdb CDM from the committed CSV
   seeds + fixture YAML.
3. `tec/runtime/ohdsi_bridge.R` loads `cohort.json` → CirceR builds SQL → SqlRender
   translates to duckdb → DatabaseConnector executes with `generateStats=TRUE`.
4. Gate 3 compares cohort membership + per-rule attrition per fixture against the
   authored expected labels; asserts AMBIGUOUS criteria never silently decide.
   Gate 4 asserts the boundary edges and recompile-equality.

No network, no Athena call, no patient data, deterministic across reruns.

**Loop status: confirmed runnable offline end-to-end** (Gates 1, 2, and the pure
half of 4 also run with no JVM, so local `pytest` is green without R; the CirceR
gates run in the devcontainer/CI).
