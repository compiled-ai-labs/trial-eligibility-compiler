"""Shared types and loaders for the gates."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from tec import canonical
from tec.paths import artifact_paths, source_file

SENTENCE_RE = re.compile(r"^\-\s*\[([IE]\d+)\]\s*(.*?)\s*$")


@dataclass
class GateResult:
    """Outcome of one gate. ``ok`` iff no errors."""

    gate: str
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def summary(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        head = f"[{status}] {self.gate}"
        if self.errors:
            head += "\n  - " + "\n  - ".join(self.errors)
        return head

    def raise_if_failed(self) -> None:
        if not self.ok:
            raise AssertionError(self.summary())


def load_vocab(trial_id: str) -> tuple[dict[int, dict], dict[str, dict]]:
    """Load the pinned (curated) concept sets from compiled/**/vocab/."""
    p = artifact_paths(trial_id)
    vocab_concepts: dict[int, dict] = {}
    vocab_sets: dict[str, dict] = {}
    for vf in sorted(p["vocab_dir"].glob("*.json")):
        doc = canonical.read(vf)
        vocab_sets[doc["name"]] = doc
        for c in doc["concepts"]:
            vocab_concepts[c["concept_id"]] = c
    return vocab_concepts, vocab_sets


def load_artifact(trial_id: str) -> dict:
    """Load the committed cohort/manifest/conventions and the merged vocab."""
    p = artifact_paths(trial_id)
    vocab_concepts, vocab_sets = load_vocab(trial_id)
    return {
        "cohort": canonical.read(p["cohort"]),
        "manifest": canonical.read(p["manifest"]),
        "conventions": canonical.read(p["conventions"]),
        "vocab_concepts": vocab_concepts,
        "vocab_sets": vocab_sets,
        "paths": p,
    }


def candidate_bundle(trial_id: str, cohort: dict, manifest: dict, conventions: dict) -> dict:
    """Assemble a gate-ready bundle from an in-memory candidate + the pinned vocab.

    Used by the compiler retry loop to run Gates 1 & 2 BEFORE the candidate is
    written. Vocab is curated input read from disk; cohort/manifest/conventions
    are the candidate under test.
    """
    vocab_concepts, vocab_sets = load_vocab(trial_id)
    return {
        "cohort": cohort,
        "manifest": manifest,
        "conventions": conventions,
        "vocab_concepts": vocab_concepts,
        "vocab_sets": vocab_sets,
        "paths": artifact_paths(trial_id),
    }


def parse_source(trial_id: str) -> dict[str, str]:
    """Map source sentence id -> verbatim sentence text."""
    out: dict[str, str] = {}
    for line in source_file(trial_id).read_text(encoding="utf-8").splitlines():
        m = SENTENCE_RE.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def cohort_concept_ids(cohort: dict) -> set[int]:
    ids: set[int] = set()
    for cs in cohort.get("ConceptSets", []):
        for item in cs.get("expression", {}).get("items", []):
            cid = item.get("concept", {}).get("CONCEPT_ID")
            if cid is not None:
                ids.add(cid)
    return ids


def cohort_rule_names(cohort: dict) -> list[str]:
    return [r["name"] for r in cohort.get("InclusionRules", [])]


def rscript_available() -> bool:
    return shutil.which("Rscript") is not None


def bridge_script() -> Path:
    from tec.paths import REPO_ROOT

    return REPO_ROOT / "tec" / "runtime" / "ohdsi_bridge.R"
