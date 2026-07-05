"""Compiler client interface + deterministic mocks (Stage 2).

The compiler depends only on the ``CompilerClient`` protocol: prompt in, raw model
text out. Stage 2 injects mocks so the whole pipeline + gates run with no API key
and no network. The real Anthropic-backed client is added in Stage 3.

Clients are test doubles, NOT the prompt: they may read the committed artifact to
build a canned response. Only tec/compile/prompt.py is bound by answer-key
demotion.
"""

from __future__ import annotations

import copy
import json
from typing import Protocol, runtime_checkable

from tec import canonical
from tec.paths import artifact_paths


@runtime_checkable
class CompilerClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return raw model output (a JSON envelope string) for a compile prompt."""
        ...


def _committed(trial_id: str) -> tuple[dict, dict, dict]:
    p = artifact_paths(trial_id)
    return (canonical.read(p["cohort"]),
            canonical.read(p["manifest"]),
            canonical.read(p["conventions"]))


def envelope(cohort: dict, manifest: dict, conventions: dict) -> str:
    return json.dumps({
        "cohort_json": cohort,
        "manifest_json": manifest,
        "conventions_json": conventions,
    })


def good_envelope(trial_id: str = "NCT03667300") -> str:
    """Canned response that reproduces the committed artifact byte-for-byte."""
    return envelope(*_committed(trial_id))


def faulty_envelope_drop(trial_id: str = "NCT03667300", drop_id: str = "E6") -> str:
    """A response that silently drops a criterion -> Gate 2 (coverage) fails."""
    cohort, manifest, conventions = _committed(trial_id)
    manifest = copy.deepcopy(manifest)
    manifest["entries"] = [e for e in manifest["entries"] if e["criterion_id"] != drop_id]
    return envelope(cohort, manifest, conventions)


def faulty_envelope_invent(trial_id: str = "NCT03667300") -> str:
    """A response that marks E6 INCLUDE with invented membership -> Gate 1 fails."""
    cohort, manifest, conventions = _committed(trial_id)
    manifest = copy.deepcopy(manifest)
    for e in manifest["entries"]:
        if e["criterion_id"] == "E6":
            e["disposition"] = "INCLUDE"
            e["cohort_rule"] = "E6_cyp3a4_strong"
            e["concepts"] = [{"concept_id": 999999, "concept_set": "cyp3a4_strong"}]
    return envelope(cohort, manifest, conventions)


class MockClient:
    """Returns a fixed canned response for every prompt (records prompts seen)."""

    def __init__(self, response: str | None = None, trial_id: str = "NCT03667300"):
        self.response = response if response is not None else good_envelope(trial_id)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class ScriptedMockClient:
    """Returns a scripted sequence of responses (one per attempt).

    Exercises the retry loop: e.g. [faulty, good] recovers on attempt 2, while
    [faulty, faulty, faulty] hard-fails. Records every prompt it received so tests
    can assert the gate errors were fed back.
    """

    def __init__(self, responses: list[str]):
        if not responses:
            raise ValueError("ScriptedMockClient needs at least one response")
        self.responses = list(responses)
        self.prompts: list[str] = []
        self._i = 0

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        resp = self.responses[min(self._i, len(self.responses) - 1)]
        self._i += 1
        return resp
