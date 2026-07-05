"""LLM invocation backends (three options + mock).

The trust anchor is the gates, not which frontend drives the LLM: every backend
returns raw model text that goes through the same parse -> Gate 1 + Gate 2 -> write
loop (PLAN.md §6). Modelled on compiled-ai-labs/tax-rules-compiler.

Backends, in the `auto` selection order (Claude Code first):
  1. claude-code : the `claude` CLI in headless print mode (`claude -p`). Uses the
     user's Claude Code subscription — no API key, $0 marginal.
  2. api         : the Anthropic Python SDK (ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL,
     model via TRCOMPILE_MODEL). The deterministic, pinned path used for the
     committed artifact.
  3. cursor      : the `cursor-agent` CLI in headless print mode.
  4. mock        : deterministic canned client (tec/compile/client.py) — CI/tests.

Determinism note: Opus 4.8 removed `temperature`/`top_p`/`top_k` (they 400), so the
API backend does NOT set them; byte-identical output is enforced by Gate 4
(recompile-equality), not by a sampling knob.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess

from tec.compile.client import CompilerClient, MockClient

DEFAULT_MODEL = "claude-opus-4-8"
BACKENDS = ("claude-code", "api", "cursor", "mock")
AUTO_ORDER = ("claude-code", "api", "cursor")


class BackendUnavailable(RuntimeError):
    """The requested backend has no credentials / CLI available."""


# --------------------------------------------------------------------------
class ClaudeCodeClient:
    """Drive compilation through the Claude Code CLI (`claude -p`, headless).

    Uses the user's existing Claude Code auth (subscription); no API key. The
    prompt (system rules + source + curated vocab) is passed on stdin.
    """

    name = "claude-code"

    def __init__(self, model: str | None = None):
        self.model = model  # optional; Claude Code uses its own configured model if None

    @staticmethod
    def available() -> bool:
        return shutil.which("claude") is not None

    def descriptor(self) -> dict:
        return {"backend": self.name, "model": self.model or "claude-code-default"}

    def complete(self, prompt: str) -> str:
        if not self.available():
            raise BackendUnavailable("`claude` CLI not found (install Claude Code).")
        cmd = ["claude", "-p", "--output-format", "text"]
        if self.model:
            cmd += ["--model", self.model]
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed:\n{proc.stderr}")
        return proc.stdout


# --------------------------------------------------------------------------
class CursorClient:
    """Drive compilation through the Cursor agent CLI (`cursor-agent -p`)."""

    name = "cursor"

    def __init__(self, model: str | None = None):
        self.model = model

    @staticmethod
    def available() -> bool:
        return shutil.which("cursor-agent") is not None

    def descriptor(self) -> dict:
        return {"backend": self.name, "model": self.model or "cursor-default"}

    def complete(self, prompt: str) -> str:
        if not self.available():
            raise BackendUnavailable("`cursor-agent` CLI not found (install Cursor).")
        cmd = ["cursor-agent", "-p", "--output-format", "text"]
        if self.model:
            cmd += ["--model", self.model]
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"cursor-agent CLI failed:\n{proc.stderr}")
        return proc.stdout


# --------------------------------------------------------------------------
class AnthropicApiClient:
    """Drive compilation through the Anthropic Python SDK.

    Model pinned via TRCOMPILE_MODEL (default claude-opus-4-8). ANTHROPIC_BASE_URL
    (alternative provider endpoint) is honoured by the SDK from the environment;
    it is also passed explicitly here when set. No sampling params (removed on
    Opus 4.8); low effort for the most consolidated output.
    """

    name = "api"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("TRCOMPILE_MODEL", DEFAULT_MODEL)
        self.base_url = os.environ.get("ANTHROPIC_BASE_URL")  # None => SDK default
        self.effort = os.environ.get("TRCOMPILE_EFFORT", "low")

    @staticmethod
    def available() -> bool:
        # Needs both the SDK installed and a credential signal (a set API key, or an
        # ANTHROPIC_BASE_URL alt-provider endpoint). Without the SDK we cannot run,
        # so report unavailable rather than being auto-selected and failing mid-loop.
        if importlib.util.find_spec("anthropic") is None:
            return False
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_BASE_URL"))

    def descriptor(self) -> dict:
        return {"backend": self.name, "model": self.model, "effort": self.effort,
                "base_url": self.base_url}

    def complete(self, prompt: str) -> str:
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover - env-dependent
            raise BackendUnavailable(
                "anthropic SDK not installed; `uv pip install 'trial-eligibility-compiler[llm]'`"
            ) from e

        kwargs = {}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = anthropic.Anthropic(**kwargs)  # key from env / ant profile

        # Stream (large max_tokens) to avoid the SDK's non-streaming timeout guard.
        with client.messages.stream(
            model=self.model,
            max_tokens=32000,
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()

        if message.stop_reason == "refusal":  # pragma: no cover - runtime path
            raise RuntimeError("model refused the compile request (stop_reason=refusal)")
        return "".join(b.text for b in message.content if b.type == "text")


_REGISTRY = {
    "claude-code": ClaudeCodeClient,
    "api": AnthropicApiClient,
    "cursor": CursorClient,
}


def available_backends() -> dict[str, bool]:
    return {name: cls.available() for name, cls in _REGISTRY.items()} | {"mock": True}


def resolve_backend(name: str = "auto", model: str | None = None) -> CompilerClient:
    """Return a CompilerClient for `name`, trying Claude Code first when 'auto'."""
    name = name or "auto"
    if name == "mock":
        return MockClient()
    if name == "auto":
        for candidate in AUTO_ORDER:
            cls = _REGISTRY[candidate]
            if cls.available():
                return cls(model=model)
        raise BackendUnavailable(
            "no LLM backend available. Install Claude Code (`claude`), set "
            "ANTHROPIC_API_KEY, or install Cursor (`cursor-agent`) — or use "
            "`--backend mock` for the offline canned client."
        )
    if name not in _REGISTRY:
        raise ValueError(f"unknown backend {name!r}; choose from {BACKENDS}")
    cls = _REGISTRY[name]
    if not cls.available():
        raise BackendUnavailable(f"backend {name!r} is not available in this environment.")
    return cls(model=model)
