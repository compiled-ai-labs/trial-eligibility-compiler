Scaffold a new immutable source spec for a trial. Does NOT invoke the compiler.

Given a trial id (e.g. NCT01234567):
1. Create `source/<NCTID>.md` with the VERBATIM eligibility criteria as registered
   on ClinicalTrials.gov, each sentence tagged with a stable id (`I1..`, `E1..`).
   Do not paraphrase, reorder, or clean up wording — only the ids are ours.
2. Create the empty artifact folder `compiled/<NCTID>/` with a `vocab/` subdir.
3. Leave `cohort.json` / `manifest.json` / `conventions.json` unwritten — those are
   produced by `/compile` (or `trcompile build`) and committed only after the gates
   pass.

Stop after scaffolding. Remind the user to curate `compiled/<NCTID>/vocab/` concept
sets before compiling (the compiler may use only curated membership).
