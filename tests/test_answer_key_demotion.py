"""Answer-key demotion (CLAUDE.md invariant 2, resolution A).

tec/compile/prompt.py may read ONLY source/*.md and compiled/**/vocab/*.json.
Reading manifest.json / cohort.json / conventions.json / anything under fixtures/
/ corpus-plan.md / fixture-plan.md would leak the target dispositions or labels.
"""

import pathlib

from tec.compile import prompt as prompt_mod
from tec.paths import SOURCE_DIR, artifact_paths

TRIAL = "NCT03667300"
FORBIDDEN_NAMES = {"manifest.json", "cohort.json", "conventions.json",
                   "corpus-plan.md", "fixture-plan.md"}


def test_build_prompt_reads_only_source_and_vocab(monkeypatch):
    opened: list[pathlib.Path] = []
    orig_rt = pathlib.Path.read_text
    orig_rb = pathlib.Path.read_bytes

    def rec_rt(self, *a, **k):
        opened.append(pathlib.Path(self).resolve())
        return orig_rt(self, *a, **k)

    def rec_rb(self, *a, **k):
        opened.append(pathlib.Path(self).resolve())
        return orig_rb(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "read_text", rec_rt)
    monkeypatch.setattr(pathlib.Path, "read_bytes", rec_rb)

    text = prompt_mod.build_prompt(TRIAL, prior_failure="some gate error")
    assert "cohort_json" in text and "manifest_json" in text

    source_dir = SOURCE_DIR.resolve()
    vocab_dir = artifact_paths(TRIAL)["vocab_dir"].resolve()
    assert opened, "build_prompt read nothing?"
    for p in opened:
        assert p.name not in FORBIDDEN_NAMES, f"read forbidden file: {p}"
        assert "fixtures" not in p.parts, f"read fixtures path: {p}"
        under_allowed = source_dir in p.parents or vocab_dir in p.parents or p == source_dir
        assert under_allowed, f"read path outside source/ and vocab/: {p}"


def test_prompt_module_does_not_reference_answer_key_paths():
    src = pathlib.Path(prompt_mod.__file__).read_text(encoding="utf-8")
    # Split off the leading docstring (which legitimately names the forbidden paths
    # to document the rule) and the SYSTEM_RULES prompt text; scan only the code.
    body = src.split('SYSTEM_RULES = """', 1)[0]
    body = body.split('"""', 2)[-1]  # drop the module docstring
    for forbidden in ("PATIENTS_DIR", "FIXTURES_DIR", "CDM_SEED_DIR",
                      "corpus-plan", "fixture-plan", '"manifest"', '["manifest"]'):
        assert forbidden not in body, f"prompt.py code references answer-key path: {forbidden}"
