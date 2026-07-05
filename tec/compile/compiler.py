"""The compile loop (PLAN.md §6).

  read source -> client -> parse candidate cohort/manifest/conventions
    -> Gate 1 (structure) + Gate 2 (coverage)
       pass -> canonical-serialise, write to compiled/<trial>/
       fail -> append the concrete gate errors to the prompt, retry (<= max_attempts)
               exhausted -> raise, write nothing.

Vocab is a pinned INPUT (resolution A); the compiler writes only cohort.json,
manifest.json and conventions.json. Gates 3 & 4 run in CI on the written artifact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tec import canonical
from tec.compile.client import CompilerClient
from tec.compile.prompt import build_prompt
from tec.gates import g1_structure, g2_coverage
from tec.gates.common import candidate_bundle
from tec.paths import artifact_paths

MAX_ATTEMPTS = 3
OUTPUT_FILES = ("cohort", "manifest", "conventions")


class ParseError(ValueError):
    pass


class CompileError(RuntimeError):
    """Gates still failing after the retry budget is exhausted. Nothing written."""


@dataclass
class CompileResult:
    trial_id: str
    attempts: int
    out_dir: Path
    written: list[str]


def parse_envelope(raw: str) -> tuple[dict, dict, dict]:
    text = raw.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        i, j = text.find("{"), text.rfind("}")
        if i == -1 or j == -1 or j < i:
            raise ParseError("no JSON object found in model output") from None
        try:
            obj = json.loads(text[i:j + 1])
        except json.JSONDecodeError as e:
            raise ParseError(f"model output is not valid JSON: {e}") from None
    if not isinstance(obj, dict):
        raise ParseError("model output is not a JSON object")
    for k in ("cohort_json", "manifest_json", "conventions_json"):
        if k not in obj:
            raise ParseError(f"model output missing required key {k!r}")
    return obj["cohort_json"], obj["manifest_json"], obj["conventions_json"]


def _feedback(*gate_results) -> str:
    lines = []
    for g in gate_results:
        if not g.ok:
            lines.append(g.summary())
    return "\n".join(lines)


def _write(out_dir: Path, cohort: dict, manifest: dict, conventions: dict) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"cohort": cohort, "manifest": manifest, "conventions": conventions}
    for name in OUTPUT_FILES:
        canonical.write(out_dir / f"{name}.json", payload[name])
    return [f"{n}.json" for n in OUTPUT_FILES]


def compile_trial(
    trial_id: str,
    client: CompilerClient,
    out_dir: str | Path | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> CompileResult:
    out = Path(out_dir) if out_dir is not None else artifact_paths(trial_id)["cohort"].parent
    prior_failure: str | None = None

    for attempt in range(1, max_attempts + 1):
        prompt = build_prompt(trial_id, prior_failure)
        raw = client.complete(prompt)

        try:
            cohort, manifest, conventions = parse_envelope(raw)
        except ParseError as e:
            prior_failure = f"[PARSE] {e}"
            continue

        art = candidate_bundle(trial_id, cohort, manifest, conventions)
        g1 = g1_structure.run(trial_id, art=art)
        g2 = g2_coverage.run(trial_id, art=art)

        if g1.ok and g2.ok:
            written = _write(out, cohort, manifest, conventions)
            return CompileResult(trial_id, attempt, out, written)

        prior_failure = _feedback(g1, g2)

    raise CompileError(
        f"{trial_id}: gates still failing after {max_attempts} attempts; wrote nothing.\n"
        f"Last failure:\n{prior_failure}"
    )
