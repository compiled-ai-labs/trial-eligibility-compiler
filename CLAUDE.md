# CLAUDE.md — trial-eligibility-compiler

Guardrails for every Claude Code session in this repo. Read `docs/design/PLAN.md`
before any task. These invariants override convenience; violating one is a defect
even if tests pass.

## What this repo is

A **Compiled AI** reference implementation: an LLM compiles verbatim
ClinicalTrials.gov eligibility prose into a deterministic OHDSI Circe cohort
definition at **compile time only**. The runtime is unmodified standard OHDSI —
no model in the path. Refusal (`AMBIGUOUS`) is a first-class, tested output.

## Hard invariants (never violate)

1. **Never commit an unvalidated artifact.** `compiled/**` is written only after
   Gates 1 & 2 pass; Gates 3 & 4 must be green in CI. If gates fail and retries
   are exhausted, exit non-zero and write nothing.
2. **Answer-key demotion.** `tec/compile/prompt.py` reads **only** `source/*.md`.
   It must never read fixtures, expected labels, `manifest.json`,
   `corpus-plan.md`, `fixture-plan.md`, or any external structured-criteria
   dataset (Chia, n2c2). If you catch yourself importing those into the compile
   path, stop.
3. **AMBIGUOUS never touches the executable.** A manifest entry with
   `disposition == "AMBIGUOUS"` must have `concepts == []` and
   `cohort_rule == null`. It never appears in `cohort.json`.
4. **No real patient data, ever.** Every CDM row and fixture is hand-authored
   synthetic. Reject any task that would introduce MIMIC/real data.
5. **Runtime is not ours.** Cohort SQL is built and executed only by standard
   OHDSI packages (`CirceR`, `SqlRender`, `DatabaseConnector`). Do not
   hand-write cohort SQL or reimplement Circe. `cohort.json` must load unchanged
   in stock ATLAS/CirceR.
6. **Determinism.** Compile with `temperature=0` and a pinned model id. Serialise
   all artifacts as canonical JSON (sorted keys, fixed float format). Recompiling
   the same source must produce a byte-identical artifact (Gate 4).
7. **Source is immutable.** `source/*.md` is verbatim as registered on
   ClinicalTrials.gov, with stable sentence ids. Do not paraphrase, reorder, or
   "clean up" criteria text.
8. **Provenance is mandatory.** Every source sentence id maps to exactly one
   manifest entry and vice-versa (Gate 2). No dropped or invented criteria.

## Compile/refuse rule (when unsure of a disposition)

Compile a criterion **only if** the sole thing you add is a *convention you can
write to `conventions.json` and a reviewer can change in one place* (a unit, a
date-window edge, a standard reference value). **Refuse (AMBIGUOUS)** if you would
have to invent set *membership* or encode a *human judgment*. A compound
criterion is only as determinable as its weakest conjunct/disjunct. When in
genuine doubt, refuse — a false AMBIGUOUS is safe; a false INCLUDE/EXCLUDE is not.

## Stack & commands

- Python 3.11 CLI (`trcompile`, `trcheck`); R only for the OHDSI execution bridge.
- Everything runs offline inside `.devcontainer` (Python + R + JDK + duckdb).
- `trcompile build --trial NCT03667300` — compile. Selects a backend (default
  `auto`: claude-code, then api, then cursor); `--backend mock` needs no key/network.
- `trcheck evaluate --patient <fixture.yaml>` — evaluate one synthetic patient
  (never needs API key or network).
- `pytest` runs Gates 1–4; CI (`.github/workflows/ci.yml`) runs them offline with
  `--backend mock`.

## Working discipline

The staged build is complete (its history is `docs/design/PLAN.md` §12). For any
change: obey the invariants above, never weaken a gate, and present the gate
results. When unsure of a disposition, refuse (AMBIGUOUS) — see
`docs/AMBIGUOUS.md`. Adding a trial: `docs/new-trial.md`.
