# trial-eligibility-compiler

[![gates](https://github.com/compiled-ai-labs/trial-eligibility-compiler/actions/workflows/ci.yml/badge.svg)](https://github.com/compiled-ai-labs/trial-eligibility-compiler/actions/workflows/ci.yml)
![determinism](https://img.shields.io/badge/determinism-byte--identical%20recompile-informational)
![refusal](https://img.shields.io/badge/AMBIGUOUS-first--class%20output-blueviolet)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

**ClinicalTrials.gov eligibility prose as a deterministic, gate-verified OHDSI
Circe cohort — with refusal as a first-class output.**

An LLM runs at **compile time only**. It reads the verbatim eligibility criteria of
a registered trial and emits a standard OHDSI Circe cohort definition, committed
only after passing four machine-checkable gates. The runtime that consumes the
artifact is **unmodified OHDSI tooling** (`CirceR` → `SqlRender` →
`DatabaseConnector`) — no model in the path. Where prose admits no single
determinate encoding, the criterion compiles to **AMBIGUOUS**, never to a guess.

Built on the Compiled AI methodology described in
["Compiled AI: Engineering Deterministic LLM Systems"](https://itnext.io/compiled-ai-engineering-deterministic-llm-systems-f911558764d4)
(Boris Teplitsky, ITNEXT, 2026) — see also the related academic treatment
[Trooskens et al., "Compiled AI: Deterministic Code Generation for LLM-Based Workflow Automation"](https://arxiv.org/abs/2604.05150)
(arXiv:2604.05150). Sibling to
[`tax-rules-compiler`](https://github.com/compiled-ai-labs/tax-rules-compiler). It
is the reference implementation where the compile target is a **clinical
phenotype** and calibrated **refusal** is the headline behaviour, not extraction
accuracy.

---

## 1. What is Compiled AI, and why it fits trial eligibility

Compiled AI moves the LLM out of the request path. The model runs once, offline, to
produce a reviewable artifact; a separate deterministic tool runs that artifact
forever after, identically, with no inference.

| Part | In this repo |
|------|--------------|
| **Spec** — human-maintained input | `source/NCT03667300.md` — verbatim registered criteria, stable sentence ids, immutable |
| **Compiler** — LLM + retry loop | `tec/compile/` — reads only `source/*.md` + curated `vocab/`; validates candidates against Gates 1 & 2 before writing |
| **Validation gates** — automated checks | `tec/gates/g1..g4` — structure, coverage, fixture behaviour, determinism |
| **Artifact** — the committed file | `compiled/NCT03667300/` — `cohort.json` (standard Circe), `manifest.json`, `conventions.json`, `vocab/` |
| **Runtime** — deterministic, well-known | `trcheck` → `tec/runtime/ohdsi_bridge.R` (CirceR/SqlRender/DatabaseConnector), no LLM |

Eligibility computation is an unusually good fit:

- **Determinism and auditability are the whole point.** A phenotype that classifies
  patients differently between runs, or that can't say *why* a patient was included,
  is unusable for research. The artifact reruns identically and points every verdict
  at a source sentence.
- **The spec already exists and is authoritative.** Registered ClinicalTrials.gov
  criteria are US public record — a fixed, citable input the compiler reads verbatim.
- **The runtime already exists.** OHDSI Circe executes cohort definitions today —
  but the JSON is **hand-authored by an analyst**. The compiler closes that
  manual-authoring bottleneck while reusing ATLAS/Circe unchanged.
- **Genuine indeterminacy is common, so refusal is exercised, not decorative.**
  DDI-strength categories ("strong CYP3A4 inhibitor"), investigator-discretion
  catch-alls, and non-clinical consent items cannot be encoded over any CDM. Those
  are the tested `AMBIGUOUS` surface.

---

## 2. This build: the NCT03667300 slice

**Scope:** one trial (NCT03667300 — evogliptin on albuminuria in type-2 diabetes
with renal insufficiency), 16 criteria (I1–I8, E1–E8), one therapeutic area,
synthetic fixtures only. Chosen because it carries all three demo anchors in one
trial: a first-class **CYP3A4 refusal**, an **AST >3× ULN** compile-with-documented-
assumption, and an **eGFR = 30 boundary**.

**The four gates:**

1. **Structure** — `cohort.json` is valid Circe with named inclusion rules;
   `manifest.json` validates against its schema; every §4 invariant holds; every
   referenced `concept_id` exists in the pinned `vocab/`.
2. **Coverage / anti-hallucination** — a bijection between the 16 source sentence
   ids and the 16 manifest entries: no dropped criterion, no invented criterion,
   every `source_span` verbatim. This is what makes "the compiler didn't quietly
   ignore a line" machine-checkable.
3. **Fixtures / behaviour** — build the synthetic duckdb OMOP CDM, execute
   `cohort.json` via the OHDSI bridge with `generateStats=TRUE`, and assert
   membership + per-rule attrition == each fixture's expected labels; assert
   AMBIGUOUS criteria never touch the executed logic.
4. **Determinism + boundaries** — the committed artifact is canonical and
   byte-stable; recompiling reproduces it byte-for-byte; the pinned edge fixtures
   (eGFR 30/29.9, HbA1c 7.0/6.9 & 10.0/10.1, UACR 30/29 & 3000/3001, BMI 20/40, AST
   120/121, ARB/ACE 28/29 days) produce the pinned results.

**Status:** all four gates pass. **10 of 16** criteria are determinate (62.5% —
clears the 60% feasibility bar); **6 are AMBIGUOUS** by design (I8, E2, E5, E6, E7,
E8), the tested refusal suite. Gates 1, 2, and the pure half of 4 run with only
Python; Gate 3 and the CirceR half of 4 run in the devcontainer/CI (they skip
locally when `Rscript` is absent). See [`AMBIGUOUS`](#the-refusal-ledger) below.

---

## 3. Workflow and the three LLM backends

Staged build (three Claude Code prompts): skeleton + gates + synthetic CDM →
compiler with a deterministic mock → real compile + demo. The compile prompt reads
**only** `source/*.md` and the curated concept sets — never the fixtures, expected
labels, or manifest dispositions (*answer-key demotion*).

**Three ways to run the compile — the trust anchor is the gates, not which frontend
drives the LLM.** Every path faces the identical `pytest` gate suite and the
recompile-equality check.

| Backend | Command | Auth |
|---|---|---|
| **claude-code** (default, tried first) | `trcompile build --backend claude-code`, or `/compile` in Claude Code | Claude Code subscription — no API key |
| **api** | `trcompile build --backend api` | `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL`; pinned `claude-opus-4-8` |
| **cursor** | `trcompile build --backend cursor`, or `/compile` in Cursor | Cursor login |
| mock | `trcompile build --backend mock` | none — CI/tests; reproduces the committed artifact |

`trcompile build` with no `--backend` resolves `auto`: **Claude Code → API →
Cursor**. `trcompile backends` prints what is available locally. CI always uses
`--backend mock` (no secrets, no network). Only the **claude-code** path is verified
in this build; **api** and **cursor** are provided but not yet verified. Determinism
is enforced by **Gate 4 (byte-identical recompile)**, not by a sampling temperature —
Opus 4.8 removes `temperature`.

---

## 4. Repository layout

```
trial-eligibility-compiler/
├── source/
│   └── NCT03667300.md          # verbatim criteria, stable sentence ids — IMMUTABLE
├── tec/
│   ├── compile/                # Part 2 — LLM compiler + retry loop + backends
│   │   ├── prompt.py           #   reads ONLY source/*.md + vocab/  (answer-key demotion)
│   │   ├── backends.py         #   claude-code / api / cursor / mock
│   │   ├── compiler.py         #   parse -> Gate 1 + Gate 2 -> write; retry <=3
│   │   └── recompile.py        #   recompile-equality (Gate 4 half)
│   ├── gates/                  # Part 3 — g1_structure .. g4_determinism (+ gate-only oracle)
│   ├── runtime/                # Part 5 — trcheck, cdm.py (duckdb), ohdsi_bridge.R
│   └── schema/                 # manifest.schema.json, fixture.schema.json
├── compiled/
│   └── NCT03667300/            # Part 4 — the committed artifact (canonical JSON)
│       ├── cohort.json         #   standard OHDSI Circe CohortExpression
│       ├── manifest.json       #   per-criterion disposition + provenance (16 entries)
│       ├── conventions.json    #   pinned ULN / day-counts / bound inclusivity / vocab snapshot
│       └── vocab/              #   curated concept-set definitions
├── fixtures/
│   ├── cdm/                    # committed vocab CSV seeds (synthetic)
│   └── patients/               # 29 synthetic patients, each with expected labels
├── tests/                      # pytest = all four gates + demotion + backends
├── .claude/commands/           # /compile /verify /new-spec /check-pattern
├── .cursor/commands/           # /compile (Cursor)
├── AGENTS.md                   # agent-driven compile protocol
└── .devcontainer/, scripts/    # Python 3.11 + R + JDK + duckdb + pinned OHDSI stack
```

Discipline per artifact class: **source** is verbatim and never edited by the
compiler; **vocab** is curated *input* the prompt may read (membership, not an
answer); **fixtures + expected labels** are the answer key the prompt must never
see; the **committed artifact** is canonical and byte-reviewable; the **compiler**
reads only source + vocab, enforced in code and tested.

---

## 5. Compiled AI vs vibe coding

The same criteria pasted into any chat session yield similar-looking cohort JSON.
The difference is everything that happens after generation:

| | Vibe coding | trial-eligibility-compiler |
|---|---|---|
| Trust anchor | "looks right" | four gates, incl. execution against synthetic patients |
| Provenance | none | every verdict points at a verbatim source sentence id |
| Ambiguity | silently guessed | first-class `AMBIGUOUS` with a rationale; can never change a patient's disposition |
| Concept membership | invented from model memory | only curated, pinned concept sets; inventing a `concept_id` fails Gate 1 |
| Criteria change | undetected | recompile-equality flags an edited spec that wasn't recompiled |
| Regeneration | a new, different file | byte-identical recompile |
| Runtime | the model, again | unmodified OHDSI — no model, no network, no key |
| Failure | ships silently | gates block the commit; refusals are surfaced, not hidden |

A build system, not a workflow. **The gates are the product; the LLM is replaceable
labour.**

---

## Try it (no API key needed)

The gates run with only Python (Gates 1, 2, and the pure half of 4):

```
uv venv && uv pip install -e '.[dev]'
python -m pytest -q            # 90 passed, 3 skipped (the R-gated OHDSI-execution tests)
```

The full behaviour check and `trcheck` execution run inside the devcontainer (which
pins Python 3.11 + R + JDK + duckdb + the OHDSI stack):

```
trcheck evaluate --patient fixtures/patients/p_match.yaml
```

`trcheck` prints a per-criterion `INCLUDED` / `EXCLUDED` / `AMBIGUOUS` table, each
row pointing at its source sentence. The 30-second demo shows all four behaviours:

```
# MATCH — every determinate rule satisfied
p_match                → COHORT MEMBERSHIP: IN

# EXCLUSION — eGFR 24 fails I5
nm_i5_egfr    I5  EXCLUDED  "...estimated glomerular filtration rate (eGFR) 30 or more."
                       → COHORT MEMBERSHIP: OUT

# BOUNDARY — eGFR exactly 30 is INCLUDED (pinned "≥30" edge, conventions.json)
b_egfr_30     I5  INCLUDED  "...estimated glomerular filtration rate (eGFR) 30 or more."
                       → COHORT MEMBERSHIP: IN

# REFUSAL — patient on itraconazole (a strong CYP3A4 inhibitor)
p_cyp3a4_itraconazole  E6  AMBIGUOUS  "Subjects taking strong CYP3A4 inhibitors or strong CYP3A4 inducers."
                       → COHORT MEMBERSHIP: IN
```

The CYP3A4 row is the point: a "helpful" guess would be **correct** (itraconazole
*is* a strong CYP3A4 inhibitor), and the tool **refuses anyway** — there is no
vocabulary-native standard concept set for the DDI-strength category, so encoding it
would be inventing membership. It reports `AMBIGUOUS` with provenance and leaves the
patient's disposition unchanged.

Adding another trial is a `source/*.md` + curated `vocab/` + `/compile` loop — see
[docs/new-trial.md](docs/new-trial.md).

---

## The refusal ledger

Six criteria compile to `AMBIGUOUS`, each with a machine-readable rationale in
`manifest.json` and a human-readable entry in [`docs/AMBIGUOUS.md`](docs/AMBIGUOUS.md):

| id | criterion | why refused | what would make it determinate |
|----|-----------|-------------|-------------------------------|
| I8 | consent / willingness | non-clinical; not evaluable over any CDM | nothing — out of scope by nature |
| E2 | resection of >½ stomach/intestine | the extent qualifier isn't in the data | a coded "extent" attribute |
| E5 | oral triple hypoglycemic agents | undefined count/combination | a protocol-supplied enumerated regimen |
| E6 | strong CYP3A4 inhibitors/inducers | no vocabulary-native strength set | a protocol-supplied enumerated drug list (FDA DDI guidance) |
| E7 | pregnant or breastfeeding | compound; weakest disjunct (breastfeeding) is poorly coded | better breastfeeding coding |
| E8 | unsuitable per labs / other reasons | investigator-discretion catch-all | not machine-evaluable |

---

## Limitations

- Four hand-picked criteria sets, one therapeutic area — **not a benchmark**;
  answer-key demotion forbids training/evaluating on Chia or n2c2 as compile input.
- Fixtures are hand-authored synthetic; expected labels are author-asserted, **not
  clinically adjudicated**.
- Concept mappings are pinned to one Athena vocabulary snapshot; a different version
  can shift descendant sets.
- Boundary / ULN / day-count conventions are **chosen and documented**, not
  authoritative — see `conventions.json`.
- The `AMBIGUOUS` rate is high **by design**: this produces auditable phenotypes,
  not recruitment-ready patient counts.
- **Not clinically validated.** This is a methodology demonstration, not a medical
  device or a recruitment tool.

## Prior art & what this adds

- **Criteria2Query (Yuan et al., JAMIA 2019)** — hybrid NLP that parses eligibility
  text into OMOP-conformant SQL. Closest analog. *This adds:* a committed,
  fixture-verified artifact with a first-class `AMBIGUOUS` class — not an
  interactive best-effort extraction whose failure modes ship silently.
- **TrialGPT (Jin et al., Nat. Commun. 2024)** — end-to-end LLM patient-to-trial
  matching. *This adds:* the model is at **compile time**, not the runtime hot path;
  the "why included/excluded" answer comes from a deterministic committed artifact.
- **OHDSI ATLAS / Circe + PhenotypeLibrary** — the deterministic cohort runtime,
  but the JSON is **hand-authored**. *This adds:* the compile step from prose,
  gated, reusing ATLAS/Circe unchanged.
- **Chia corpus (Kury et al.)** — human-annotated criteria→concept dataset. Under
  answer-key demotion it is **evaluation-only**, never a compile input.

---

## Docs

| Doc | For |
|-----|-----|
| [docs/AMBIGUOUS.md](docs/AMBIGUOUS.md) | The refusal ledger — each AMBIGUOUS criterion and what would make it determinate |
| [docs/gates.md](docs/gates.md) | The four gates: what each proves, and what it does not |
| [docs/answer-key-demotion.md](docs/answer-key-demotion.md) | What the compile prompt may read (resolution A), and how it's enforced |
| [docs/conventions.md](docs/conventions.md) | Every pinned choice (ULN, day-counts, bound inclusivity, snapshot) and how to change one |
| [docs/runtime-ohdsi.md](docs/runtime-ohdsi.md) | The Circe → SqlRender → duckdb execution path; why the runtime is not ours |
| [docs/vocab-and-licensing.md](docs/vocab-and-licensing.md) | Curated concept sets, the Eunomia-precedent redistribution stance, pinning |
| [docs/determinism.md](docs/determinism.md) | Canonical JSON, recompile-equality, and the honest temperature caveat |
| [docs/new-trial.md](docs/new-trial.md) | Runbook for compiling a second trial |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setup, commands, backends, and the rules that block a PR |
| [AGENTS.md](AGENTS.md) | The agent-driven compile protocol (Claude Code / Cursor) |

---

Compiler and gate code: **Apache 2.0**. The runtime delegates to standard OHDSI
packages (`CirceR`, `SqlRender`, `DatabaseConnector` — Apache 2.0) on R. The
committed vocabulary is a **synthetic, purpose-restricted subset** (Eunomia
precedent), not a redistribution of SNOMED/LOINC/RxNorm — see `conventions.json`
for the pinned snapshot id.
