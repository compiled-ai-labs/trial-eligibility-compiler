"""Stage 2 compiler: mock reproduction, recompile-equality, retry loop."""

import pytest

from tec.compile import cli
from tec.compile.client import (
    MockClient,
    ScriptedMockClient,
    faulty_envelope_drop,
    faulty_envelope_invent,
    good_envelope,
)
from tec.compile.compiler import CompileError, ParseError, compile_trial, parse_envelope
from tec.compile.recompile import recompile_diff, recompile_equals_committed
from tec.paths import artifact_paths

TRIAL = "NCT03667300"
OUTPUT_FILES = ("cohort.json", "manifest.json", "conventions.json")


def _committed_bytes():
    d = artifact_paths(TRIAL)["cohort"].parent
    return {f: (d / f).read_bytes() for f in OUTPUT_FILES}


# ---- parse ---------------------------------------------------------------
def test_parse_envelope_roundtrip():
    cohort, manifest, conventions = parse_envelope(good_envelope(TRIAL))
    assert manifest["trial_id"] == TRIAL
    assert len(manifest["entries"]) == 16


def test_parse_envelope_rejects_non_json():
    with pytest.raises(ParseError):
        parse_envelope("this is not json")


def test_parse_envelope_rejects_missing_key():
    with pytest.raises(ParseError):
        parse_envelope('{"cohort_json": {}, "manifest_json": {}}')


# ---- mock reproduces the committed artifact byte-for-byte -----------------
def test_mock_reproduces_committed(tmp_path):
    result = compile_trial(TRIAL, MockClient(trial_id=TRIAL), out_dir=tmp_path)
    assert result.attempts == 1
    committed = _committed_bytes()
    for f in OUTPUT_FILES:
        assert (tmp_path / f).read_bytes() == committed[f], f"{f} not byte-identical"


def test_recompile_equals_committed():
    assert recompile_equals_committed(TRIAL, MockClient(trial_id=TRIAL))
    assert recompile_diff(TRIAL, MockClient(trial_id=TRIAL)) == {}


# ---- retry loop ----------------------------------------------------------
def test_retry_recovers_and_feeds_back_gate_errors(tmp_path):
    client = ScriptedMockClient([faulty_envelope_drop(TRIAL, "E6"), good_envelope(TRIAL)])
    result = compile_trial(TRIAL, client, out_dir=tmp_path)
    assert result.attempts == 2
    # the 2nd prompt must carry the concrete Gate 2 failure from attempt 1
    assert "Gate 2" in client.prompts[1]
    assert "E6" in client.prompts[1]
    committed = _committed_bytes()
    for f in OUTPUT_FILES:
        assert (tmp_path / f).read_bytes() == committed[f]


def test_retry_recovers_from_parse_error(tmp_path):
    client = ScriptedMockClient(["<<not json>>", good_envelope(TRIAL)])
    result = compile_trial(TRIAL, client, out_dir=tmp_path)
    assert result.attempts == 2
    assert "[PARSE]" in client.prompts[1]


def test_gate1_catches_invented_membership(tmp_path):
    client = ScriptedMockClient([faulty_envelope_invent(TRIAL)] * 3)
    with pytest.raises(CompileError) as exc:
        compile_trial(TRIAL, client, out_dir=tmp_path)
    assert "999999" in str(exc.value) or "E6_cyp3a4_strong" in str(exc.value)
    assert list(tmp_path.iterdir()) == []  # wrote nothing


def test_hard_fail_writes_nothing(tmp_path):
    client = MockClient(response=faulty_envelope_drop(TRIAL, "E6"), trial_id=TRIAL)
    before = _committed_bytes()
    with pytest.raises(CompileError):
        compile_trial(TRIAL, client, out_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert _committed_bytes() == before  # committed artifact untouched


# ---- CLI -----------------------------------------------------------------
def test_cli_build_mock(tmp_path, capsys):
    rc = cli.main(["build", "--trial", TRIAL, "--backend", "mock", "--out", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "compiled" in out and "attempt" in out
    committed = _committed_bytes()
    for f in OUTPUT_FILES:
        assert (tmp_path / f).read_bytes() == committed[f]
