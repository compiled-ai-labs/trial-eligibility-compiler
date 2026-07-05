"""The duckdb CDM builder works offline (no R/JVM needed)."""

import duckdb
import yaml

from tec.paths import PATIENTS_DIR
from tec.runtime.cdm import build_cdm


def _load(stem):
    return yaml.safe_load((PATIENTS_DIR / f"{stem}.yaml").read_text(encoding="utf-8"))


def test_build_cdm_populates_tables(tmp_path):
    fx = _load("p_match")
    db = build_cdm(fx, tmp_path / "cdm.duckdb")
    con = duckdb.connect(str(db))
    try:
        assert con.execute("SELECT COUNT(*) FROM person").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM visit_occurrence").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM condition_occurrence").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM measurement").fetchone()[0] == 5
        assert con.execute("SELECT COUNT(*) FROM drug_exposure").fetchone()[0] == 1
        # pinned vocab loaded
        t2d = con.execute("SELECT COUNT(*) FROM concept WHERE concept_id = 201826").fetchone()[0]
        assert t2d == 1
        # days_supply derived from exposure span
        ds = con.execute("SELECT days_supply FROM drug_exposure").fetchone()[0]
        assert ds == 151
    finally:
        con.close()


def test_build_cdm_ambiguous_probe_has_procedure(tmp_path):
    fx = _load("p_bariatric_e2")
    db = build_cdm(fx, tmp_path / "cdm.duckdb")
    con = duckdb.connect(str(db))
    try:
        assert con.execute("SELECT COUNT(*) FROM procedure_occurrence").fetchone()[0] == 1
    finally:
        con.close()
