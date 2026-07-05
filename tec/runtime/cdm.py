"""Build a one-person synthetic OMOP v5.4 duckdb CDM from a fixture YAML.

Loads the pinned vocabulary CSVs (fixtures/cdm/*.csv) and inserts the fixture's
clinical rows. The resulting .duckdb file is what the OHDSI bridge executes
cohort.json against. All data is synthetic (CLAUDE.md invariant 4).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import yaml

from tec.paths import CDM_SEED_DIR

GENDER_CONCEPT = {"MALE": 8507, "FEMALE": 8532}
VISIT_CONCEPT = 9202          # Outpatient Visit
TYPE_CONCEPT = 32020          # EHR encounter record

# Minimal OMOP v5.4 DDL: only the tables/columns the Circe-generated SQL touches.
DDL = """
CREATE TABLE person (
  person_id BIGINT, gender_concept_id INTEGER, year_of_birth INTEGER,
  month_of_birth INTEGER, day_of_birth INTEGER, birth_datetime TIMESTAMP,
  race_concept_id INTEGER, ethnicity_concept_id INTEGER,
  location_id BIGINT, provider_id BIGINT, care_site_id BIGINT
);
CREATE TABLE observation_period (
  observation_period_id BIGINT, person_id BIGINT,
  observation_period_start_date DATE, observation_period_end_date DATE,
  period_type_concept_id INTEGER
);
CREATE TABLE visit_occurrence (
  visit_occurrence_id BIGINT, person_id BIGINT, visit_concept_id INTEGER,
  visit_start_date DATE, visit_start_datetime TIMESTAMP,
  visit_end_date DATE, visit_end_datetime TIMESTAMP,
  visit_type_concept_id INTEGER, provider_id BIGINT, care_site_id BIGINT
);
CREATE TABLE condition_occurrence (
  condition_occurrence_id BIGINT, person_id BIGINT, condition_concept_id INTEGER,
  condition_start_date DATE, condition_start_datetime TIMESTAMP,
  condition_end_date DATE, condition_end_datetime TIMESTAMP,
  condition_type_concept_id INTEGER, condition_status_concept_id INTEGER,
  stop_reason VARCHAR, provider_id BIGINT, visit_occurrence_id BIGINT,
  condition_source_concept_id INTEGER
);
CREATE TABLE drug_exposure (
  drug_exposure_id BIGINT, person_id BIGINT, drug_concept_id INTEGER,
  drug_exposure_start_date DATE, drug_exposure_start_datetime TIMESTAMP,
  drug_exposure_end_date DATE, drug_exposure_end_datetime TIMESTAMP,
  verbatim_end_date DATE, drug_type_concept_id INTEGER, stop_reason VARCHAR,
  refills INTEGER, quantity DOUBLE, days_supply INTEGER, route_concept_id INTEGER,
  provider_id BIGINT, visit_occurrence_id BIGINT, drug_source_concept_id INTEGER
);
CREATE TABLE measurement (
  measurement_id BIGINT, person_id BIGINT, measurement_concept_id INTEGER,
  measurement_date DATE, measurement_datetime TIMESTAMP,
  measurement_type_concept_id INTEGER, operator_concept_id INTEGER,
  value_as_number DOUBLE, value_as_concept_id INTEGER, unit_concept_id INTEGER,
  range_low DOUBLE, range_high DOUBLE, provider_id BIGINT,
  visit_occurrence_id BIGINT, measurement_source_concept_id INTEGER
);
CREATE TABLE procedure_occurrence (
  procedure_occurrence_id BIGINT, person_id BIGINT, procedure_concept_id INTEGER,
  procedure_date DATE, procedure_datetime TIMESTAMP,
  procedure_type_concept_id INTEGER, modifier_concept_id INTEGER,
  quantity INTEGER, provider_id BIGINT, visit_occurrence_id BIGINT,
  procedure_source_concept_id INTEGER
);
CREATE TABLE concept (
  concept_id INTEGER, concept_name VARCHAR, domain_id VARCHAR, vocabulary_id VARCHAR,
  concept_class_id VARCHAR, standard_concept VARCHAR, concept_code VARCHAR,
  valid_start_date DATE, valid_end_date DATE, invalid_reason VARCHAR
);
CREATE TABLE concept_ancestor (
  ancestor_concept_id INTEGER, descendant_concept_id INTEGER,
  min_levels_of_separation INTEGER, max_levels_of_separation INTEGER
);
CREATE TABLE concept_relationship (
  concept_id_1 INTEGER, concept_id_2 INTEGER, relationship_id VARCHAR,
  valid_start_date DATE, valid_end_date DATE, invalid_reason VARCHAR
);
CREATE TABLE vocabulary (
  vocabulary_id VARCHAR, vocabulary_name VARCHAR, vocabulary_reference VARCHAR,
  vocabulary_version VARCHAR, vocabulary_concept_id INTEGER
);
"""


def load_fixture(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _load_vocab(con: duckdb.DuckDBPyConnection, seed_dir: Path) -> None:
    for table, fname in (("concept", "concept.csv"),
                         ("concept_ancestor", "concept_ancestor.csv"),
                         ("concept_relationship", "concept_relationship.csv"),
                         ("vocabulary", "vocabulary.csv")):
        csv = (seed_dir / fname).as_posix()
        con.execute(f"INSERT INTO {table} SELECT * FROM read_csv_auto('{csv}', header=true)")


def build_cdm(fixture: dict, db_path: str | Path, seed_dir: Path = CDM_SEED_DIR) -> Path:
    """Materialise a duckdb CDM for one patient. Returns the db path."""
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        con.execute(DDL)
        _load_vocab(con, Path(seed_dir))

        pid = 1
        index = date.fromisoformat(fixture["index_date"])
        bd = date.fromisoformat(fixture["person"]["birth_date"])
        gender = GENDER_CONCEPT[fixture["person"]["gender"]]
        con.execute(
            "INSERT INTO person VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [pid, gender, bd.year, bd.month, bd.day, f"{bd} 00:00:00", 0, 0, None, None, None],
        )
        # generous observation period so all labs/drugs fall inside it
        con.execute(
            "INSERT INTO observation_period VALUES (?,?,?,?,?)",
            [1, pid, date(index.year - 1, 1, 1), date(index.year + 1, 12, 31), TYPE_CONCEPT],
        )
        # single screening visit == index event
        con.execute(
            "INSERT INTO visit_occurrence VALUES (?,?,?,?,?,?,?,?,?,?)",
            [1, pid, VISIT_CONCEPT, index, f"{index} 00:00:00", index, f"{index} 00:00:00",
             TYPE_CONCEPT, None, None],
        )

        for i, c in enumerate(fixture.get("conditions", []), start=1):
            s = date.fromisoformat(c["start_date"])
            con.execute(
                "INSERT INTO condition_occurrence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [i, pid, c["concept_id"], s, f"{s} 00:00:00", s, f"{s} 00:00:00",
                 TYPE_CONCEPT, 0, None, None, 1, 0],
            )
        for i, m in enumerate(fixture.get("measurements", []), start=1):
            d = date.fromisoformat(m["date"])
            con.execute(
                "INSERT INTO measurement VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [i, pid, m["concept_id"], d, f"{d} 00:00:00", TYPE_CONCEPT, 0,
                 float(m["value"]), 0, 0, None, None, None, 1, 0],
            )
        for i, dexp in enumerate(fixture.get("drugs", []), start=1):
            s = date.fromisoformat(dexp["start_date"])
            e = date.fromisoformat(dexp["end_date"])
            con.execute(
                "INSERT INTO drug_exposure VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [i, pid, dexp["concept_id"], s, f"{s} 00:00:00", e, f"{e} 00:00:00",
                 e, TYPE_CONCEPT, None, 0, 0.0, (e - s).days, 0, None, 1, 0],
            )
        for i, p in enumerate(fixture.get("procedures", []), start=1):
            d = date.fromisoformat(p["date"])
            con.execute(
                "INSERT INTO procedure_occurrence VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [i, pid, p["concept_id"], d, f"{d} 00:00:00", TYPE_CONCEPT, 0, 1, None, 1, 0],
            )
        con.commit()
    finally:
        con.close()
    return db_path


if __name__ == "__main__":
    import sys

    fx = load_fixture(sys.argv[1])
    out = build_cdm(fx, sys.argv[2] if len(sys.argv) > 2 else "cdm.duckdb")
    print(f"built CDM: {out}")
