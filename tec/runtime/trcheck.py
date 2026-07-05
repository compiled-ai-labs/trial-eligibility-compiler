"""`trcheck evaluate --patient <fixture.yaml>` — deterministic, offline, key-free.

Builds a one-person duckdb CDM, executes cohort.json via the OHDSI R bridge, and
prints a per-criterion table:
  - INCLUDED / EXCLUDED   for determinate criteria (from inclusion-rule attrition),
  - AMBIGUOUS             for refused criteria (from manifest.json, never executed).

No model, no network, no API key. This module must not import tec.compile or the
gate oracle (CLAUDE.md invariants 2 & 5).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tec import canonical
from tec.gates.common import bridge_script, rscript_available
from tec.paths import artifact_paths
from tec.runtime.cdm import build_cdm, load_fixture

JSON_START = "<<<TRCHECK_JSON>>>"
JSON_END = "<<<END_TRCHECK_JSON>>>"


class BridgeUnavailable(RuntimeError):
    pass


def run_bridge(cohort_path: Path, db_path: Path) -> dict:
    """Execute cohort.json against a duckdb CDM via standard OHDSI packages."""
    if not rscript_available():
        raise BridgeUnavailable(
            "Rscript not found. trcheck needs the OHDSI R stack (CirceR, SqlRender, "
            "DatabaseConnector); run inside .devcontainer or CI."
        )
    proc = subprocess.run(
        ["Rscript", str(bridge_script()), str(cohort_path), str(db_path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"OHDSI bridge failed:\n{proc.stderr}")
    out = proc.stdout
    if JSON_START not in out or JSON_END not in out:
        raise RuntimeError(f"OHDSI bridge produced no result payload:\n{out}")
    payload = out.split(JSON_START, 1)[1].split(JSON_END, 1)[0].strip()
    return json.loads(payload)


def labels_from_bridge(manifest: dict, bridge_result: dict) -> list[dict]:
    """Join manifest entries with the bridge's satisfied-rule flags.

    Pure function (no execution) — shared by the CLI and the offline preview.
    """
    satisfied = {r["name"]: r["satisfied"] for r in bridge_result.get("rules", [])}
    rows = []
    for e in manifest["entries"]:
        if e["disposition"] == "AMBIGUOUS":
            label = "AMBIGUOUS"
        else:
            rule = e["cohort_rule"]
            if rule not in satisfied:
                raise RuntimeError(f"{e['criterion_id']}: rule {rule!r} missing from bridge output")
            label = "INCLUDED" if satisfied[rule] else "EXCLUDED"
        rows.append({
            "criterion_id": e["criterion_id"],
            "disposition": e["disposition"],
            "label": label,
            "source_span": e["source_span"],
        })
    return rows


def render_table(rows: list[dict], membership: bool | None) -> str:
    lines = [
        f"{'CRITERION':<10} {'LABEL':<10} SOURCE",
        f"{'-'*10} {'-'*10} {'-'*6}",
    ]
    for r in rows:
        lines.append(f"{r['criterion_id']:<10} {r['label']:<10} {r['source_span']}")
    if membership is not None:
        lines.append("")
        if membership:
            lines.append("COHORT MEMBERSHIP: IN (all determinate inclusion rules satisfied)")
        else:
            lines.append("COHORT MEMBERSHIP: OUT (>=1 determinate rule failed)")
    return "\n".join(lines)


def evaluate(fixture_path: str | Path, trial_id: str = "NCT03667300") -> dict:
    p = artifact_paths(trial_id)
    manifest = canonical.read(p["manifest"])
    fixture = load_fixture(fixture_path)
    with tempfile.TemporaryDirectory() as td:
        db = build_cdm(fixture, Path(td) / "cdm.duckdb")
        bridge = run_bridge(p["cohort"], db)
    rows = labels_from_bridge(manifest, bridge)
    return {"rows": rows, "membership": bridge["membership"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="trcheck",
        description="Evaluate one synthetic patient against a committed cohort (offline).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("evaluate", help="evaluate a patient fixture")
    ev.add_argument("--patient", required=True, help="path to a fixture YAML")
    ev.add_argument("--trial", default="NCT03667300")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.cmd == "evaluate":
        try:
            result = evaluate(args.patient, args.trial)
        except BridgeUnavailable as e:
            sys.stderr.write(f"trcheck: {e}\n")
            return 3
        print(render_table(result["rows"], result["membership"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
