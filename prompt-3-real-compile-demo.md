# Prompt 3 — real compile + demo assets

Paste into Claude Code after Stage 2 is green. This is the only stage that uses a
real API key, and only for `trcompile` (never `trcheck`).

---

```
Read CLAUDE.md and PLAN.md. Obey every hard invariant. Stages 1 and 2 are
complete: gates green, and trcompile reproduces the committed artifact from a
mock client.

This is STAGE 3 of 3. Goal: wire the real Anthropic client for compile time,
regenerate the committed artifact for real, and write the demo/README/limitations
so a professional who clones the repo gets the paradigm in 30 seconds. Keep the
runtime (trcheck) fully offline and key-free.

TASK 1 — real client.
- Add a RealClient implementing CompilerClient, using the Anthropic SDK with a
  PINNED model id and temperature=0 (record both in conventions.json for
  determinism). Select MockClient vs RealClient by an explicit flag/env var;
  default trcompile to RealClient, but CI must keep using MockClient (no secrets
  in CI).
- The RealClient reads the API key from the environment only. Never hardcode or
  log it. trcheck must not import the client at all.

TASK 2 — real compile.
- Run `trcompile build --trial NCT03667300` against the real API to regenerate
  compiled/NCT03667300/. Then run all four gates.
- If the real output differs from the Stage-1 hand-authored artifact in a
  legitimate way (e.g. a better rationale string), accept the real output as the
  new committed artifact ONLY after all gates pass, and update fixtures'
  expected labels only if a disposition genuinely changed — document any such
  change. If gates fail, iterate the compile prompt (not the gates) until green.
  Never weaken a gate to pass.
- Confirm recompile determinism: two real compiles at temperature=0 yield a
  byte-identical artifact; if not, tighten the prompt/serialisation until they do,
  and note residual nondeterminism honestly if any remains.

TASK 3 — README with the 30-second demo.
Write README.md that positions the repo per corpus-plan.md's framing:
reproducibility + auditability + calibrated refusal, NOT extraction accuracy.
Include, near the top, a single copy-paste demo that shows all four behaviours in
one run:
  * a MATCH patient (INCLUDED),
  * an EXCLUDE patient (e.g. eGFR 24 -> EXCLUDED),
  * a BOUNDARY patient (eGFR 30 -> INCLUDED; note the pinned convention),
  * the CYP3A4 REFUSAL: a patient on itraconazole where E6 prints AMBIGUOUS with
    provenance to the source sentence — explicitly note that a guess would even
    have been correct, and the tool refuses anyway.
Show the actual trcheck output blocks. Explain the compile-time-only architecture
and that no model runs in trcheck.

TASK 4 — LIMITATIONS + badges.
- Add the LIMITATIONS section verbatim-ish from PLAN.md §11 (specific, not
  boilerplate): four hand-picked criteria / not a benchmark / answer-key demotion
  / synthetic author-asserted fixtures / pinned vocab snapshot / chosen
  documented conventions / high AMBIGUOUS rate by design / not recruitment counts
  / not clinically validated.
- Add a short "Prior art & what this adds" subsection from corpus-plan.md TASK 4
  (Criteria2Query, TrialGPT, ATLAS/Circe, Chia-as-eval-only).
- CI badges for: gates passing, and determinism (recompile-equality) green.

TASK 5 — final sweep.
- Verify the answer-key-demotion lint still passes and the compile prompt reads
  only source/*.md.
- Verify trcheck runs with no network and no API key.
- Ensure conventions.json fully records: model id, temperature, vocab snapshot
  version, ULN value + source, all day-counts and boundary inclusivities.

STOP CONDITION. Deliverable: the committed artifact is the product of a real,
deterministic compile; all four gates green in CI (with MockClient); README shows
the four-behaviour demo including the CYP3A4 refusal; LIMITATIONS is specific.
Present the real trcompile run summary, the demo output, and the final gate +
determinism status.
```
