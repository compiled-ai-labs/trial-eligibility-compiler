"""Recompile-equality — the half of Gate 4 that needs a compiler (PLAN.md §6/§10).

Recompiling the same source with the same client must reproduce the committed
artifact byte-for-byte. This is what catches "someone edited a spec but did not
recompile" and any serialisation drift.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from tec.compile.client import CompilerClient
from tec.compile.compiler import OUTPUT_FILES, compile_trial
from tec.paths import artifact_paths


def recompile_diff(trial_id: str, client: CompilerClient) -> dict[str, tuple[bytes, bytes]]:
    """Return {filename: (committed_bytes, recompiled_bytes)} for any file that differs.

    Empty dict == byte-identical recompile.
    """
    committed_dir = artifact_paths(trial_id)["cohort"].parent
    diffs: dict[str, tuple[bytes, bytes]] = {}
    with tempfile.TemporaryDirectory() as td:
        compile_trial(trial_id, client, out_dir=td)
        for name in OUTPUT_FILES:
            fname = f"{name}.json"
            committed = (committed_dir / fname).read_bytes()
            recompiled = (Path(td) / fname).read_bytes()
            if committed != recompiled:
                diffs[fname] = (committed, recompiled)
    return diffs


def recompile_equals_committed(trial_id: str, client: CompilerClient) -> bool:
    return not recompile_diff(trial_id, client)
