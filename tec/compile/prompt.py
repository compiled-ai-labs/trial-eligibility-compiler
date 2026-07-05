"""Compile-prompt construction.

Answer-key demotion (CLAUDE.md invariant 2, resolution A): this module may read
ONLY the verbatim source spec (source/*.md) and the curated concept sets
(compiled/**/vocab/*.json). It must never open manifest.json, cohort.json,
conventions.json, anything under fixtures/, corpus-plan.md, or fixture-plan.md —
those encode the target dispositions/labels (the answer key). The concept sets are
curated reference membership, not an answer key, so the model can wire determinate
criteria to real concept_ids instead of inventing them.

A unit test (tests/test_answer_key_demotion.py) fails if this module reads any
forbidden path.
"""

from __future__ import annotations

from tec import canonical
from tec.paths import artifact_paths, source_file

# Paths this module is permitted to read. Anything else is an answer-key leak.
# (Enforced by test; kept here as executable documentation.)
ALLOWED_READ_ROOTS = ("source/", "compiled/NCT03667300/vocab/")


def _load_source(trial_id: str) -> str:
    return source_file(trial_id).read_text(encoding="utf-8")


def _load_vocab_sets(trial_id: str) -> list[dict]:
    vocab_dir = artifact_paths(trial_id)["vocab_dir"]
    return [canonical.read(vf) for vf in sorted(vocab_dir.glob("*.json"))]


def _render_vocab(vocab_sets: list[dict]) -> str:
    lines = []
    for vs in vocab_sets:
        concepts = ", ".join(
            f"{c['concept_id']} ({c['concept_name']}, {c['vocabulary_id']})"
            for c in vs["concepts"]
        )
        desc = f" include_descendants={str(vs['include_descendants']).lower()}"
        lines.append(f"- concept_set id={vs['concept_set_id']} name={vs['name']}{desc}: {concepts}")
    return "\n".join(lines)


SYSTEM_RULES = """\
You are a compile-time cohort compiler. You convert verbatim ClinicalTrials.gov
eligibility prose into a deterministic OHDSI Circe cohort definition plus an audit
manifest. You run at compile time only; a separate, unmodified OHDSI runtime
executes your output. Correctness and calibrated refusal matter far more than
coverage.

Hard rules:
1. Emit BOTH a standard OHDSI Circe CohortExpression (cohort_json) and an audit
   manifest (manifest_json) with exactly one entry per source sentence id, plus a
   conventions_json recording every pinned choice.
2. Compile a criterion (INCLUDE/EXCLUDE) ONLY if the sole thing you add is a
   convention a reviewer can change in one place (a unit, a numeric edge, a date
   window, a reference value). REFUSE (disposition AMBIGUOUS) if you would have to
   invent concept-set membership or encode a human judgment.
3. A compound criterion is only as determinable as its weakest conjunct/disjunct.
   When in genuine doubt, REFUSE — a false AMBIGUOUS is safe; a false
   INCLUDE/EXCLUDE is not.
4. NEVER invent concept-set membership. Use ONLY the curated concept sets provided
   below, by their concept_set id and the concept_ids listed. If no provided set
   fits a criterion, that criterion is AMBIGUOUS.
5. AMBIGUOUS entries MUST have concepts == [] and cohort_rule == null and MUST NOT
   appear as an inclusion rule in cohort_json.
6. Every determinate (INCLUDE/EXCLUDE) manifest entry MUST name a cohort_rule that
   is a named inclusion rule in cohort_json (so per-criterion attrition is
   reportable), and every concept it lists MUST come from a provided concept set.
7. Each manifest entry's source_span MUST be the verbatim source sentence, copied
   exactly.

Output contract: return a SINGLE JSON object and nothing else, with exactly these
keys: "cohort_json", "manifest_json", "conventions_json". No prose, no code fences.
"""


def build_prompt(trial_id: str = "NCT03667300", prior_failure: str | None = None) -> str:
    """Construct the compile prompt from source + curated vocab only."""
    source = _load_source(trial_id)
    vocab = _render_vocab(_load_vocab_sets(trial_id))

    parts = [
        SYSTEM_RULES,
        "\n## Verbatim source spec (the ONLY criteria; copy source_span exactly)\n",
        source,
        "\n## Curated concept sets (the ONLY allowed membership)\n",
        vocab,
        "\n## manifest_json shape\n",
        '{"trial_id": "<NCT...>", "entries": [{"criterion_id","source_span",'
        '"disposition","rationale","cohort_rule","concepts":[{"concept_id","concept_set"}]}]}',
    ]
    if prior_failure:
        parts.append(
            "\n## Your previous attempt FAILED these validation gates. Fix exactly "
            "these problems and re-emit the full JSON object:\n" + prior_failure
        )
    return "\n".join(parts)
