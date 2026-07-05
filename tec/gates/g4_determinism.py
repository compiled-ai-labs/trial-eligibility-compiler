"""Gate 4 — Determinism + boundaries.

Two halves:
  (a) Determinism. Every committed artifact file is already canonical (re-serialising
      its parsed content is byte-identical to what is on disk) and hashes stably.
      The recompile-equality half (recompile from source == committed) is a
      Stage-2 TODO: there is no compiler yet.
  (b) Boundaries. The pinned edge fixtures (eGFR 30/29.9, HbA1c 7.0/6.9, ...)
      produce the pinned results. Authoritative confirmation runs the artifact via
      CirceR in Gate 3; here (and locally, JVM-free) we cross-check each boundary
      fixture against the pinned conventions with the differential oracle.
"""

from __future__ import annotations

import yaml

from tec import canonical
from tec.gates import oracle
from tec.gates.common import GateResult, load_artifact
from tec.paths import PATIENTS_DIR

ARTIFACT_FILES = ("cohort.json", "manifest.json", "conventions.json")

# The boundary set from PLAN.md §5 (fixture patient_id -> the criterion it probes).
BOUNDARY_PROBES = {
    "b_egfr_30": "I5", "b_egfr_29_9": "I5",
    "b_hba1c_70": "I3", "b_hba1c_69": "I3", "b_hba1c_100": "I3", "b_hba1c_101": "I3",
    "b_uacr_30": "I4", "b_uacr_29": "I4", "b_uacr_3000": "I4", "b_uacr_3001": "I4",
    "b_bmi_20": "I7", "b_bmi_40": "I7",
    "b_ast_120": "E3", "b_ast_121": "E3",
    "b_arbace_28d": "I6", "b_arbace_29d": "I6",
}


def _hashes(trial_id: str) -> dict:
    p = load_artifact(trial_id)["paths"]
    return {name: canonical.sha256(canonical.read(p[key]))
            for name, key in (("cohort.json", "cohort"),
                              ("manifest.json", "manifest"),
                              ("conventions.json", "conventions"))}


def run(trial_id: str = "NCT03667300") -> GateResult:
    r = GateResult("Gate 4 — Determinism + boundaries")
    art = load_artifact(trial_id)
    conventions = art["conventions"]
    tdir = art["paths"]["cohort"].parent

    # (a) canonical / byte-stability
    for fname in ARTIFACT_FILES:
        raw = (tdir / fname).read_bytes()
        recanon = canonical.dumps(canonical.loads(raw.decode("utf-8"))).encode("utf-8")
        if raw != recanon:
            r.fail(f"{fname} is not canonical on disk (recompile would not be byte-identical)")
    for name, h in _hashes(trial_id).items():
        r.note(f"sha256 {name} = {h}")

    # recompile-equality is implemented in tec.compile.recompile (Stage 2) and
    # exercised by tests/test_compiler.py + the CI diff step. It lives with the
    # compiler so the gates stay independent of the compile path.
    r.note("recompile-equality: tec.compile.recompile.recompile_equals_committed "
           "(tested + diffed in CI).")

    # (b) boundary edges — differential cross-check against pinned conventions
    checked = 0
    for pid, crit in BOUNDARY_PROBES.items():
        fpath = PATIENTS_DIR / f"{pid}.yaml"
        if not fpath.exists():
            r.fail(f"boundary fixture missing: {fpath.name}")
            continue
        fx = yaml.safe_load(fpath.read_text(encoding="utf-8"))
        got = oracle.evaluate(fx, conventions)
        exp = fx["expected"].get(crit)
        if exp is None:
            r.fail(f"{pid}: fixture does not assert expected[{crit}]")
        elif got[crit] != exp:
            r.fail(f"{pid}: boundary probe {crit} oracle={got[crit]} != asserted {exp}")
        else:
            checked += 1
    r.note(f"boundary edges cross-checked against conventions: {checked}/{len(BOUNDARY_PROBES)}")
    return r


if __name__ == "__main__":
    res = run()
    print(res.summary())
    for n in res.notes:
        print("   ", n)
    raise SystemExit(0 if res.ok else 1)
