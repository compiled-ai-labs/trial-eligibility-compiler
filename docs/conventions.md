# Pinned conventions

`compiled/NCT03667300/conventions.json` records every choice the compiler had to
make that the source prose did not fully specify. The rule (see
[AMBIGUOUS.md](AMBIGUOUS.md)): a criterion may compile **only if** the sole thing
added is a convention a reviewer can change in one place. This file is that place.
Everything here is *chosen and documented*, not authoritative.

## Upper normal limit (E3)

`uln`: AST/ALT ULN pinned at **40 U/L**, so ">3× the upper normal limit" = **120
U/L** (threshold_multiple 3). Implemented as "exclude if any AST or ALT measurement
> 120". ULN is lab-specific and is not a value in the CDM, so a reference value must
be chosen; 40 U/L is a common clinical reference range. This is the criterion's one
load-bearing assumption — the boundary fixtures `b_ast_120` (INCLUDED, `120` is not
`> 120`) and `b_ast_121` (EXCLUDED) pin the edge.

## Day-counts (I6, E4)

`day_counts`:

- **I6 — "for more than 4 weeks"** → pinned ">4 weeks == ≥ 29 days continuous
  exposure", implemented as `DrugExposure days_supply >= 29`. In the synthetic CDM,
  `days_supply` is `(end − start).days` (`cdm.py`). Fixtures `b_arbace_28d`
  (EXCLUDED) and `b_arbace_29d` (INCLUDED) pin the edge.
- **E4 — "within 8 weeks prior to screening"** → pinned "within 8 weeks == drug
  start within 56 days before index", implemented as a Circe `StartWindow` of
  `[index − 56d, index]`.

Prose windows ("more than 4 weeks", "within 8 weeks") do not state a day count or
inclusivity; the convention supplies both, auditably.

## Numeric bounds and inclusivity (I3, I4, I5, I7)

`numeric_bounds` records the low/high and which edges are inclusive:

| criterion | bound | inclusive | unit |
|-----------|-------|-----------|------|
| I3 HbA1c | 7.0 – 10.0 | both | % (NGSP) |
| I4 UACR | 30 – 3000 | both | µg/mg |
| I5 eGFR | ≥ 30 | low | mL/min/1.73m² |
| I7 BMI | 20 – 40 | both | kg/m² |

Where the source gives the operator ("7.0% or more, and 10% or less", "30 or more")
the edge is determinate and the convention just makes the inclusivity explicit. The
boundary fixtures (`b_hba1c_70`/`b_hba1c_69`, `b_egfr_30`/`b_egfr_29_9`, etc.) pin
each side. The HbA1c unit is pinned to % (NGSP); a mmol/mol source value would need
a documented unit conversion before it could be compared.

## Index and window

`index_date` **2023-06-01**, `index_event` = the first `VisitOccurrence` (the
synthetic screening visit). Every temporal window is evaluated relative to that visit,
so results are deterministic. `measurement_window_days` **180**: labs are considered
if measured within 180 days before index.

## Vocabulary snapshot

`vocab_snapshot` = `athena-v5-2023q3 (pinned synthetic subset)`. Concept mappings are
pinned to this snapshot; a different version can shift descendant sets. See
[vocab-and-licensing.md](vocab-and-licensing.md).

## Compile provenance and a determinism caveat

`compile` records the model and settings for the run that produced the artifact. In
the committed hand-authored artifact, `model_id` is `null` and `temperature` is `0`
(the pinned *intent* from the staged plan). Note that the pinned real backend model,
`claude-opus-4-8`, does **not** accept a `temperature` parameter — so byte-stability
is enforced by Gate 4 (recompile-equality), not by a sampling knob. A real compile
records the actual backend/model. See [determinism.md](determinism.md).

## Changing a convention

Edit the single value in `conventions.json`, then recompile and re-run the gates. The
boundary fixtures that pin the affected edge will need their expected labels updated
in the same change — Gate 4 (edges) and Gate 3 (behaviour) will fail until they
agree, which is the point: a convention change is visible and reviewable, never
silent.
