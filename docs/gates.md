# The four gates

The gates are the reason the paradigm works: the LLM's output is not committed
unless external, automated checks agree it does what it claims. Without them this is
"ask a model for a config file" — which is everywhere and worth nothing.

Gates 1 and 2 are pure Python and run inside the compiler retry loop (`tec/compile/
compiler.py`) and in CI. Gates 3 and 4 execute the artifact and run in the
devcontainer / CI; the R-dependent parts skip locally when `Rscript` is absent. Each
gate has a CLI: `python -m tec.gates.g1_structure` (through `g4_determinism`).

## Gate 1 — Structure (`g1_structure.py`)

**Proves:** the artifact is a well-formed, self-consistent Circe cohort + manifest.

- `manifest.json` validates against `tec/schema/manifest.schema.json`.
- `cohort.json` has the required Circe keys (`ConceptSets`, `PrimaryCriteria`,
  `InclusionRules`); every concept set has `id`/`name`/`expression`; inclusion-rule
  names are unique and non-empty (per-criterion attrition needs names).
- Every `CONCEPT_ID` referenced by `cohort.json` exists in the pinned `vocab/`.
- Manifest §4 invariants: `disposition ∈ {INCLUDE, EXCLUDE, AMBIGUOUS}`; `AMBIGUOUS`
  ⇒ `concepts == []` and `cohort_rule == null`; `INCLUDE`/`EXCLUDE` ⇒ `cohort_rule`
  names a rule present in `cohort.json` and every listed `concept_id` is in `vocab/`.
- No orphan executable rule: every inclusion rule in `cohort.json` is claimed by
  exactly one determinate manifest entry.

**Does not prove:** that the concepts are the *right* concepts, or that the rule
logic matches the clinical intent. That is Gate 3's job (behaviour) and human review.

## Gate 2 — Coverage / anti-hallucination (`g2_coverage.py`)

**Proves:** the compiler neither dropped nor invented a criterion, and did not
rewrite the source text.

- A bijection between the source sentence ids in `source/NCT03667300.md` and the
  manifest entries: no duplicate, no dropped (in source, absent from manifest), no
  invented (in manifest, absent from source).
- Every manifest `source_span` is byte-identical to the verbatim source sentence for
  its id.

**Does not prove:** that each disposition is correct — only that every criterion is
accounted for and quoted faithfully. This is the machine-checkable form of "the
compiler didn't quietly ignore a line."

## Gate 3 — Fixtures / behaviour (`g3_fixtures.py`) · R-gated

**Proves:** the committed `cohort.json`, executed by real OHDSI tooling, classifies
synthetic patients exactly as the fixtures assert.

For each `fixtures/patients/*.yaml`: build the duckdb OMOP CDM (`cdm.py`), execute
`cohort.json` through `ohdsi_bridge.R` (`CirceR` → `SqlRender` "duckdb" →
`DatabaseConnector`, `generateStats=TRUE`), and compare per-inclusion-rule attrition
+ overall membership to the expected labels. Also asserts no `AMBIGUOUS` criterion
maps to an executed rule.

Requires the OHDSI R stack; raises `BridgeUnavailable` and skips when `Rscript` is
missing. This is the only gate that runs the *actual* runtime, and so the only one
that can catch a Circe-semantics error.

## Gate 4 — Determinism + boundaries (`g4_determinism.py`)

**Proves:** the artifact is byte-stable and the pinned edges are what the
conventions say.

- Each committed file, re-serialised through `tec/canonical.py`, is byte-identical
  to what is on disk (already canonical → recompiling can be byte-stable). Emits the
  sha256 of each file.
- Recompile-equality (the compiler-dependent half) lives in
  `tec/compile/recompile.py`: recompiling with the same client must reproduce the
  committed bytes exactly. Tested in `tests/test_compiler.py` and diffed in CI.
- Boundary edges: for every fixture in `BOUNDARY_PROBES`, the probed criterion's
  label is cross-checked against the pinned `conventions.json` thresholds.

**Does not prove** determinism of the LLM itself — a model can be nondeterministic;
Gate 4 is what makes that observable (a drifting recompile fails the diff). See
[determinism.md](determinism.md).

## The gate-only oracle (`tec/gates/oracle.py`)

Gate 4's local boundary check uses a small pure-Python differential oracle that
recomputes each determinate disposition from a fixture and the pinned conventions.
It exists so the boundary/consistency assertions can run without a JVM, as an
**independent** check against the authoritative CirceR execution in Gate 3.

It is quarantined from the runtime: `trcheck` must never import it (CLAUDE.md
invariant 5). It is a test cross-check, not a second cohort engine in the request
path. Two independent computations (oracle in Gate 4, CirceR in Gate 3) agreeing on
the same labels is the differential-testing signal; one reimplementing the other
would defeat the point.

## Discipline

If a contributor proposes weakening a gate, push back — the gates are the value
proposition. Maximum 3 compile retries with the concrete gate errors fed back into
the prompt; after that the compiler surfaces to a human and writes nothing. Never
commit an artifact that failed gates.
