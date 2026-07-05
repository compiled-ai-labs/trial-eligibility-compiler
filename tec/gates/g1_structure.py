"""Gate 1 — Structure.

cohort.json is a structurally valid Circe CohortExpression with named inclusion
rules; manifest.json validates against manifest.schema.json; all PLAN.md §4
invariants hold; every concept referenced by cohort.json exists in the pinned
vocab/.
"""

from __future__ import annotations

import jsonschema

from tec import canonical
from tec.gates.common import (
    GateResult,
    cohort_concept_ids,
    cohort_rule_names,
    load_artifact,
)
from tec.paths import SCHEMA_DIR

VALID_DISPOSITIONS = {"INCLUDE", "EXCLUDE", "AMBIGUOUS"}
REQUIRED_COHORT_KEYS = {"ConceptSets", "PrimaryCriteria", "InclusionRules"}


def run(trial_id: str = "NCT03667300", art: dict | None = None) -> GateResult:
    r = GateResult("Gate 1 — Structure")
    if art is None:
        art = load_artifact(trial_id)
    cohort, manifest = art["cohort"], art["manifest"]
    vocab_ids = set(art["vocab_concepts"])

    # 1. manifest validates against its schema
    schema = canonical.read(SCHEMA_DIR / "manifest.schema.json")
    try:
        jsonschema.validate(manifest, schema)
    except jsonschema.ValidationError as e:
        r.fail(f"manifest.json fails schema: {e.message} at {list(e.path)}")

    # 2. cohort.json structural sanity (standard Circe shape)
    missing = REQUIRED_COHORT_KEYS - set(cohort)
    if missing:
        r.fail(f"cohort.json missing required Circe keys: {sorted(missing)}")
    for cs in cohort.get("ConceptSets", []):
        if "id" not in cs or "name" not in cs or "expression" not in cs:
            r.fail(f"ConceptSet malformed: {cs!r}")
    rule_names = cohort_rule_names(cohort)
    if len(rule_names) != len(set(rule_names)):
        r.fail("cohort.json InclusionRules have duplicate names")
    for rule in cohort.get("InclusionRules", []):
        if not rule.get("name"):
            r.fail("cohort.json has an unnamed inclusion rule "
                   "(per-criterion attrition requires names)")
        expr = rule.get("expression", {})
        if "Type" not in expr or "CriteriaList" not in expr:
            r.fail(f"inclusion rule {rule.get('name')!r} has a malformed expression")

    # 3. every concept referenced by cohort exists in pinned vocab
    for cid in sorted(cohort_concept_ids(cohort)):
        if cid not in vocab_ids:
            r.fail(f"cohort.json references concept_id {cid} absent from compiled/**/vocab/")

    # 4. §4 invariants on the manifest envelope
    rule_name_set = set(rule_names)
    referenced_rules: set[str] = set()
    for e in manifest.get("entries", []):
        cid = e["criterion_id"]
        disp = e["disposition"]
        rule = e["cohort_rule"]
        concepts = e["concepts"]
        if disp not in VALID_DISPOSITIONS:
            r.fail(f"{cid}: invalid disposition {disp!r}")
        if disp == "AMBIGUOUS":
            if concepts != [] or rule is not None:
                r.fail(f"{cid}: AMBIGUOUS must have concepts==[] and cohort_rule==null "
                       f"(got concepts={concepts!r}, cohort_rule={rule!r})")
        else:  # INCLUDE | EXCLUDE
            if rule is None:
                r.fail(f"{cid}: {disp} must name a cohort_rule")
            elif rule not in rule_name_set:
                r.fail(f"{cid}: cohort_rule {rule!r} not present in cohort.json InclusionRules")
            else:
                referenced_rules.add(rule)
            for c in concepts:
                if c["concept_id"] not in vocab_ids:
                    r.fail(f"{cid}: concept_id {c['concept_id']} not in pinned vocab/")

    # 5. no orphan executable rule (every cohort rule is claimed by exactly one manifest entry)
    orphans = rule_name_set - referenced_rules
    if orphans:
        r.fail(f"cohort.json inclusion rules with no determinate manifest entry: {sorted(orphans)}")

    return r


if __name__ == "__main__":
    res = run()
    print(res.summary())
    raise SystemExit(0 if res.ok else 1)
