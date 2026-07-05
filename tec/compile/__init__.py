"""Compile-time package (LLM compiler + retry loop).

STAGE 2: prompt (source + curated vocab only), CompilerClient interface + mocks,
the retry loop, and recompile-equality — all driven by a deterministic mock (no
API key, no network). The real Anthropic client is wired in Stage 3.
"""
