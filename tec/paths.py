"""Repo-relative path resolution shared by gates and runtime."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIR = REPO_ROOT / "source"
COMPILED_DIR = REPO_ROOT / "compiled"
SCHEMA_DIR = REPO_ROOT / "tec" / "schema"
FIXTURES_DIR = REPO_ROOT / "fixtures"
CDM_SEED_DIR = FIXTURES_DIR / "cdm"
PATIENTS_DIR = FIXTURES_DIR / "patients"


def trial_dir(trial_id: str) -> Path:
    return COMPILED_DIR / trial_id


def source_file(trial_id: str) -> Path:
    return SOURCE_DIR / f"{trial_id}.md"


def artifact_paths(trial_id: str) -> dict[str, Path]:
    d = trial_dir(trial_id)
    return {
        "cohort": d / "cohort.json",
        "manifest": d / "manifest.json",
        "conventions": d / "conventions.json",
        "vocab_dir": d / "vocab",
    }
