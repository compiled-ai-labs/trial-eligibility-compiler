# The runtime (OHDSI, not ours)

`trcheck` evaluates one synthetic patient against the committed cohort. It is
deterministic, offline, and key-free — no model, no network. Critically, **it
authors no cohort logic**: the cohort SQL is built and executed only by standard
OHDSI packages (CLAUDE.md invariant 5). `trcheck` orchestrates; OHDSI decides.

## The execution chain

```
compiled/NCT03667300/cohort.json            (committed artifact)
   │  CirceR::cohortExpressionFromJson()
   │  CirceR::buildCohortQuery(generateStats = TRUE)
   ▼
OHDSI SQL (SqlRender @-parameterised; temp tables + concept_ancestor)
   │  SqlRender::translate(targetDialect = "duckdb")
   │  DatabaseConnector::executeSql(...)
   ▼
duckdb OMOP CDM (synthetic, one patient)  →  cohort + cohort_inclusion_result
```

Every stage is unmodified HADES. Reproducing a path OHDSI's own CI already exercises
(Circe → CirceR → SqlRender → a file-based CDM, the Eunomia way), on a smaller
hand-built CDM. duckdb is chosen over SQLite for its date-type support — the cohort
SQL is date-heavy (drug within 56 days, labs within 180 days, exposure ≥ 29 days).

## The pieces

- **`tec/runtime/cdm.py`** builds a one-person duckdb CDM from a fixture YAML plus
  the committed vocab CSV seeds. Minimal OMOP v5.4 DDL for the tables the generated
  SQL touches; `days_supply` is derived as `(end − start).days`; the single
  `VisitOccurrence` on the fixture's `index_date` is the index event.
- **`tec/runtime/ohdsi_bridge.R`** is the bridge. It reads `cohort.json`, has CirceR
  build the stats-enabled query, renders/translates it to duckdb, creates the
  standard OHDSI result tables (`cohort`, `cohort_inclusion`,
  `cohort_inclusion_result`, …), executes, and emits a JSON payload between
  `<<<TRCHECK_JSON>>>` markers: `{membership, rules:[{rule_sequence, name,
  satisfied}]}`. The satisfied flag per rule comes from the inclusion-rule bitmask.
- **`tec/runtime/trcheck.py`** builds the CDM, runs the bridge, and joins the result
  with `manifest.json`: a determinate criterion's label is `INCLUDED`/`EXCLUDED` from
  whether its named rule was satisfied; an `AMBIGUOUS` criterion's label comes from
  the manifest and is **never executed**. It renders the per-criterion table.

## Per-criterion labels from attrition

Because each determinate criterion is a **named** Circe inclusion rule, `generateStats
= TRUE` yields per-rule pass/fail for the patient. `INCLUDED` on an inclusion rule
means the rule was satisfied — for an exclusion criterion (E1, E3, E4) that means the
disqualifier was *absent*. Overall membership is `IN` iff all determinate rules were
satisfied. `AMBIGUOUS` rows sit alongside the executed ones for provenance but cannot
change membership — Gate 3 asserts this.

## Local vs CI

`trcheck` and Gate 3 need the R stack (`CirceR`, `SqlRender`, `DatabaseConnector`) +
a JDK + duckdb — pinned in `.devcontainer/` via `scripts/install_ohdsi.R`. When
`Rscript` is absent, `trcheck` exits with a clear message and Gate 3 raises
`BridgeUnavailable` and skips. The `.devcontainer` installs the stack and runs them
for real; CI is Python-only, so those cases skip there too.

This split is deliberate: the pure-Python gates (structure, coverage, determinism)
give fast local signal, while the one gate that runs the *actual* runtime — and can
catch a Circe-semantics error the pure checks cannot — runs where OHDSI is installed.

## What "not ours" buys

Anyone who trusts OHDSI/ATLAS can load `cohort.json` unchanged in stock ATLAS or
CirceR and get the same result. The artifact is not tied to this repo's code; the
repo's contribution is the gated *compile step* that produced it, not a bespoke
execution engine.
