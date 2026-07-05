"""Gates 1, 2 and the pure-Python half of Gate 4 — run everywhere (no JVM)."""

from tec.gates import g1_structure, g2_coverage, g4_determinism

TRIAL = "NCT03667300"


def test_gate1_structure():
    res = g1_structure.run(TRIAL)
    assert res.ok, res.summary()


def test_gate2_coverage_bijection():
    res = g2_coverage.run(TRIAL)
    assert res.ok, res.summary()


def test_gate4_determinism_and_boundaries():
    res = g4_determinism.run(TRIAL)
    assert res.ok, res.summary()


def test_manifest_has_16_entries_10_determinate_6_ambiguous():
    from tec.gates.common import load_artifact

    entries = load_artifact(TRIAL)["manifest"]["entries"]
    assert len(entries) == 16
    determinate = [e for e in entries if e["disposition"] in ("INCLUDE", "EXCLUDE")]
    ambiguous = [e for e in entries if e["disposition"] == "AMBIGUOUS"]
    assert len(determinate) == 10
    assert {e["criterion_id"] for e in ambiguous} == {"I8", "E2", "E5", "E6", "E7", "E8"}


def test_ambiguous_never_touches_executable():
    from tec.gates.common import cohort_rule_names, load_artifact

    art = load_artifact(TRIAL)
    exec_rules = set(cohort_rule_names(art["cohort"]))
    for e in art["manifest"]["entries"]:
        if e["disposition"] == "AMBIGUOUS":
            assert e["cohort_rule"] is None and e["concepts"] == []
            assert e["cohort_rule"] not in exec_rules
