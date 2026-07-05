"""Gate 3 — Fixtures / behaviour.

Build the synthetic duckdb CDM for each patient fixture, execute cohort.json via
the OHDSI bridge (CirceR -> SqlRender "duckdb" -> DatabaseConnector,
generateStats=TRUE), and assert actual membership + per-inclusion-rule attrition
== the fixture's expected labels. Also assert every AMBIGUOUS criterion is absent
from the executed logic (it cannot change any patient's disposition).

Requires the OHDSI R stack. When Rscript is unavailable (e.g. local dev without
the devcontainer) this raises BridgeUnavailable and the pytest wrapper skips it;
CI always runs it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from tec.gates.common import GateResult, load_artifact, rscript_available
from tec.paths import PATIENTS_DIR
from tec.runtime.cdm import build_cdm
from tec.runtime.trcheck import BridgeUnavailable, labels_from_bridge, run_bridge


def _ambiguous_ids(manifest: dict) -> set[str]:
    return {e["criterion_id"] for e in manifest["entries"] if e["disposition"] == "AMBIGUOUS"}


def _executed_rule_names(cohort: dict) -> set[str]:
    return {r["name"] for r in cohort.get("InclusionRules", [])}


def run(trial_id: str = "NCT03667300") -> GateResult:
    r = GateResult("Gate 3 — Fixtures / behaviour")
    if not rscript_available():
        raise BridgeUnavailable("Rscript not found; Gate 3 runs in the .devcontainer only.")

    art = load_artifact(trial_id)
    cohort, manifest = art["cohort"], art["manifest"]

    # AMBIGUOUS criteria must never correspond to an executed inclusion rule.
    amb = _ambiguous_ids(manifest)
    exec_rules = _executed_rule_names(cohort)
    for e in manifest["entries"]:
        if e["criterion_id"] in amb and e["cohort_rule"] in exec_rules:
            r.fail(f"AMBIGUOUS {e['criterion_id']} maps to executed rule {e['cohort_rule']!r}")

    fixtures = sorted(PATIENTS_DIR.glob("*.yaml"))
    if not fixtures:
        r.fail("no patient fixtures found")
        return r

    for fpath in fixtures:
        fx = yaml.safe_load(fpath.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            db = build_cdm(fx, Path(td) / "cdm.duckdb")
            bridge = run_bridge(art["paths"]["cohort"], db)
        rows = {row["criterion_id"]: row["label"] for row in labels_from_bridge(manifest, bridge)}

        for cid, expected in fx["expected"].items():
            got = rows.get(cid)
            if got != expected:
                r.fail(f"{fpath.name}: {cid} executed={got} != expected {expected}")
        if "expected_membership" in fx and bridge["membership"] != fx["expected_membership"]:
            r.fail(f"{fpath.name}: membership={bridge['membership']} != expected "
                   f"{fx['expected_membership']}")

    if r.ok:
        r.note(f"executed {len(fixtures)} fixtures; membership + attrition match expected labels")
    return r


if __name__ == "__main__":
    try:
        res = run()
    except BridgeUnavailable as e:
        print(f"[SKIP] Gate 3 — {e}")
        raise SystemExit(0) from None
    print(res.summary())
    raise SystemExit(0 if res.ok else 1)
