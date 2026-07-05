"""Fixture integrity: schema validity + differential-oracle consistency.

The oracle cross-check (independent of CirceR) asserts every fixture's
hand-written expected labels agree with the pinned conventions. Gate 3 then
confirms the committed cohort.json reproduces the same labels via real OHDSI
execution.
"""

import jsonschema
import pytest
import yaml

from tec import canonical
from tec.gates import oracle
from tec.gates.common import load_artifact
from tec.paths import PATIENTS_DIR, SCHEMA_DIR

TRIAL = "NCT03667300"
FIXTURES = sorted(PATIENTS_DIR.glob("*.yaml"))
DETERMINATE = ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "E1", "E3", "E4"]


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_fixtures_exist():
    assert len(FIXTURES) >= 29


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_matches_schema(path):
    schema = canonical.read(SCHEMA_DIR / "fixture.schema.json")
    jsonschema.validate(_load(path), schema)


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_labels_consistent_with_conventions(path):
    conventions = load_artifact(TRIAL)["conventions"]
    fx = _load(path)
    got = oracle.evaluate(fx, conventions)
    for cid in DETERMINATE:
        if cid in fx["expected"]:
            assert got[cid] == fx["expected"][cid], f"{path.stem}: {cid}"
    if "expected_membership" in fx:
        assert got["membership"] == fx["expected_membership"], f"{path.stem}: membership"


def test_ambiguous_probes_do_not_change_membership():
    conventions = load_artifact(TRIAL)["conventions"]
    for stem in ("p_cyp3a4_itraconazole", "p_bariatric_e2"):
        fx = _load(PATIENTS_DIR / f"{stem}.yaml")
        got = oracle.evaluate(fx, conventions)
        assert got["membership"] is True
        assert fx["expected"]["E6"] == "AMBIGUOUS" or fx["expected"]["E2"] == "AMBIGUOUS"
