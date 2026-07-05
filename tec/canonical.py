"""Canonical JSON serialisation.

Every committed artifact is serialised through :func:`dumps` so that recompiling
the same source yields a byte-identical file (PLAN.md invariant 6 / Gate 4).

Rules:
- keys sorted,
- UTF-8, no ASCII escaping,
- compact but human-diffable (2-space indent, ``", "``/``": "`` separators),
- floats rendered by Python's shortest round-trip repr (``json`` default),
- trailing newline, ``\\n`` line endings only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def dumps(obj: Any) -> str:
    """Serialise ``obj`` to canonical JSON text (with trailing newline)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def loads(text: str) -> Any:
    return json.loads(text)


def write(path: str | Path, obj: Any) -> None:
    """Write ``obj`` as canonical JSON with ``\\n`` endings (no CRLF on Windows)."""
    Path(path).write_bytes(dumps(obj).encode("utf-8"))


def read(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(obj: Any) -> str:
    """Stable content hash of an object via its canonical serialisation."""
    return hashlib.sha256(dumps(obj).encode("utf-8")).hexdigest()
