"""Backend selection logic (no live LLM calls — availability is monkeypatched)."""

import pytest

from tec.compile import backends
from tec.compile.backends import (
    AnthropicApiClient,
    BackendUnavailable,
    ClaudeCodeClient,
    CursorClient,
    available_backends,
    resolve_backend,
)
from tec.compile.client import MockClient


def _set_availability(monkeypatch, claude=False, api=False, cursor=False):
    monkeypatch.setattr(ClaudeCodeClient, "available", staticmethod(lambda: claude))
    monkeypatch.setattr(AnthropicApiClient, "available", staticmethod(lambda: api))
    monkeypatch.setattr(CursorClient, "available", staticmethod(lambda: cursor))


def test_mock_always_resolvable():
    assert isinstance(resolve_backend("mock"), MockClient)


def test_auto_prefers_claude_code(monkeypatch):
    _set_availability(monkeypatch, claude=True, api=True, cursor=True)
    assert isinstance(resolve_backend("auto"), ClaudeCodeClient)


def test_auto_falls_back_to_api_then_cursor(monkeypatch):
    _set_availability(monkeypatch, claude=False, api=True, cursor=True)
    assert isinstance(resolve_backend("auto"), AnthropicApiClient)
    _set_availability(monkeypatch, claude=False, api=False, cursor=True)
    assert isinstance(resolve_backend("auto"), CursorClient)


def test_auto_raises_when_nothing_available(monkeypatch):
    _set_availability(monkeypatch, claude=False, api=False, cursor=False)
    with pytest.raises(BackendUnavailable):
        resolve_backend("auto")


def test_explicit_backend_unavailable_raises(monkeypatch):
    _set_availability(monkeypatch, claude=False)
    with pytest.raises(BackendUnavailable):
        resolve_backend("claude-code")


def test_unknown_backend_raises():
    with pytest.raises(ValueError):
        resolve_backend("gpt")


def test_available_backends_includes_mock(monkeypatch):
    _set_availability(monkeypatch, claude=True, api=False, cursor=False)
    avail = available_backends()
    assert avail["mock"] is True
    assert avail["claude-code"] is True
    assert avail["api"] is False


def test_api_client_pins_default_model(monkeypatch):
    monkeypatch.delenv("TRCOMPILE_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    c = AnthropicApiClient()
    assert c.model == backends.DEFAULT_MODEL == "claude-opus-4-8"
    assert c.descriptor()["backend"] == "api"
