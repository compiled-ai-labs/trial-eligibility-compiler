"""trcheck table assembly (pure) + real OHDSI execution (R-gated)."""

import pytest

from tec import canonical
from tec.gates.common import cohort_rule_names, rscript_available
from tec.paths import PATIENTS_DIR, artifact_paths
from tec.runtime import trcheck

TRIAL = "NCT03667300"


def _manifest():
    return canonical.read(artifact_paths(TRIAL)["manifest"])


def _all_satisfied_bridge():
    cohort = canonical.read(artifact_paths(TRIAL)["cohort"])
    rules = [{"rule_sequence": i, "name": n, "satisfied": True}
             for i, n in enumerate(cohort_rule_names(cohort))]
    return {"membership": True, "rules": rules}


def test_labels_from_bridge_maps_determinate_and_ambiguous():
    rows = trcheck.labels_from_bridge(_manifest(), _all_satisfied_bridge())
    by_id = {r["criterion_id"]: r for r in rows}
    assert len(rows) == 16
    assert by_id["I2"]["label"] == "INCLUDED"
    assert by_id["E1"]["label"] == "INCLUDED"      # exclusion rule satisfied == disqualifier absent
    assert by_id["E6"]["label"] == "AMBIGUOUS"     # refused, never executed
    assert by_id["E6"]["source_span"].startswith("Subjects taking strong CYP3A4")


def test_render_table_contains_ambiguous_row():
    rows = trcheck.labels_from_bridge(_manifest(), _all_satisfied_bridge())
    table = trcheck.render_table(rows, membership=True)
    assert "AMBIGUOUS" in table
    assert "COHORT MEMBERSHIP: IN" in table
    assert "E6" in table


def test_failed_rule_becomes_excluded():
    manifest = _manifest()
    bridge = _all_satisfied_bridge()
    for r in bridge["rules"]:
        if r["name"] == "I5_egfr":
            r["satisfied"] = False
    bridge["membership"] = False
    rows = {r["criterion_id"]: r["label"] for r in trcheck.labels_from_bridge(manifest, bridge)}
    assert rows["I5"] == "EXCLUDED"


# ---- R-gated: real OHDSI execution ---------------------------------------
requires_r = pytest.mark.skipif(
    not rscript_available(),
    reason="Rscript / OHDSI stack unavailable; runs in the .devcontainer only.",
)


@requires_r
def test_evaluate_match_patient_real_execution():
    result = trcheck.evaluate(PATIENTS_DIR / "p_match.yaml", TRIAL)
    assert result["membership"] is True
    by_id = {r["criterion_id"]: r["label"] for r in result["rows"]}
    assert by_id["I5"] == "INCLUDED"
    assert by_id["E6"] == "AMBIGUOUS"


@requires_r
def test_evaluate_exclude_patient_real_execution():
    result = trcheck.evaluate(PATIENTS_DIR / "nm_i5_egfr.yaml", TRIAL)
    assert result["membership"] is False
    by_id = {r["criterion_id"]: r["label"] for r in result["rows"]}
    assert by_id["I5"] == "EXCLUDED"
