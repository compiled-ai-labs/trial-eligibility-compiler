# Adding a new trial

The PoC ships one trial (NCT03667300). This is the runbook for compiling a second.
It is a `source/*.md` + curated `vocab/` + `/compile` loop; the gates do the rest.

> **Honest scope note.** The gate wiring is currently single-trial: `tec/gates/*`
> default `trial_id="NCT03667300"`, the boundary-probe map in `g4_determinism.py`
> names NCT03667300 fixtures, and the tests pin `TRIAL="NCT03667300"`. Adding a
> trial therefore also means extending that wiring (below, step 5). Generalising
> the gates to iterate over all trials in `compiled/` is a good first contribution.

## 1. Scaffold the immutable spec

Use `/new-spec <NCTID>` (Claude Code / Cursor), or by hand:

- Create `source/<NCTID>.md` with the **verbatim** eligibility criteria as
  registered on ClinicalTrials.gov, each sentence tagged with a stable id
  (`I1..`, `E1..`). Do not paraphrase, reorder, or clean up wording — only the ids
  are ours. `source/*.md` is immutable after this step (CLAUDE.md invariant 7).
- Create the artifact folder `compiled/<NCTID>/vocab/`.

## 2. Curate the concept sets

The compiler may use only curated membership (resolution A — see
[answer-key-demotion.md](answer-key-demotion.md)). For each determinate criterion,
add a `compiled/<NCTID>/vocab/<name>.json` concept set: integer `concept_id`s +
your labels + provenance + `include_descendants`. Follow the licensing rule in
[vocab-and-licensing.md](vocab-and-licensing.md) — pin a snapshot, commit
concept-set *definitions*, never a bulk vocabulary export.

Refuse early: if a criterion has no vocabulary-native set (a DDI-strength category,
an investigator catch-all), do not create a set for it — it is `AMBIGUOUS`.

## 3. Compile

```
trcompile build --trial <NCTID>            # auto: claude-code, then api, then cursor
```

or `/compile` in a fresh Claude Code / Cursor session (agent-driven). The loop reads
only `source/<NCTID>.md` + `vocab/`, emits `cohort.json` / `manifest.json` /
`conventions.json`, runs Gate 1 + Gate 2 on the candidate, and writes only on pass.
On a gate failure it feeds the exact error back and retries (≤ 3), then hard-fails
writing nothing.

## 4. Author fixtures

Add `fixtures/patients/*.yaml` (see `tec/schema/fixture.schema.json`). At minimum,
per the PoC pattern:

- one MATCH and one NO-MATCH per determinate criterion;
- the boundary pairs for every numeric / day-count edge (value on each side of the
  pinned threshold);
- an AMBIGUOUS probe per refused criterion that carries the relevant data and
  asserts the criterion is `AMBIGUOUS` and does not change membership.

Expected labels are **author-asserted** and are the answer key — never readable by
the compile prompt.

## 5. Wire the gates for the new trial

- Extend `BOUNDARY_PROBES` in `tec/gates/g4_determinism.py` (or the generalised
  iteration, if you built it) with the new boundary fixtures.
- Add a test module (or parametrize the existing ones) that runs Gates 1–4 for
  `<NCTID>`.

## 6. Verify

```
python -m pytest -q          # Gates 1, 2, pure half of 4 + fixtures + demotion
```

Gate 3 and the CirceR half of Gate 4 run in the devcontainer / CI (they skip
locally when `Rscript` is absent). CI runs all four with `--backend mock`.

## Rough effort

For a threshold-dense trial in a familiar therapeutic area: about **1–1.5 days** —
most of it curating concept sets and authoring fixtures, not compiling. Trials heavy
in class-(c) prose (judgment/DDI/consent) compile faster but yield a higher
`AMBIGUOUS` rate, which is the correct outcome, not a failure.
