"""Gate-only differential oracle. NOT the runtime.

This module recomputes each determinate criterion's disposition directly from a
fixture and the pinned conventions, in pure Python. It exists solely so Gate 4's
boundary/consistency assertions can run without a JVM, as an INDEPENDENT check
against the authoritative CirceR execution in Gate 3.

Hard boundary (CLAUDE.md invariant 5): the runtime (``trcheck``) must never import
this. Cohort execution is done only by standard OHDSI packages. This oracle is a
test cross-check, not a second cohort engine in the request path.
"""

from __future__ import annotations

from datetime import date, timedelta

INDEX_WINDOW_DAYS = 180


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _measurements(fixture, concept_ids, index, window_days=INDEX_WINDOW_DAYS):
    lo = index - timedelta(days=window_days)
    vals = []
    for m in fixture.get("measurements", []):
        if m["concept_id"] in concept_ids and lo <= _d(m["date"]) <= index:
            vals.append(m["value"])
    return vals


def _conditions(fixture, concept_ids, index):
    return [c for c in fixture.get("conditions", [])
            if c["concept_id"] in concept_ids and _d(c["start_date"]) <= index]


def _drugs(fixture, concept_ids, index, within_days=None, min_days_supply=None):
    out = []
    for dexp in fixture.get("drugs", []):
        if dexp["concept_id"] not in concept_ids:
            continue
        start, end = _d(dexp["start_date"]), _d(dexp["end_date"])
        if start > index:
            continue
        if within_days is not None and start < index - timedelta(days=within_days):
            continue
        if min_days_supply is not None and (end - start).days < min_days_supply:
            continue
        out.append(dexp)
    return out


# concept-set ids (mirror gen_vocab SETS); kept local so the oracle is self-contained
T2DM = {201826}
HBA1C = {3004410}
UACR = {3034485}
EGFR = {3049187}
ARB_ACEI = {1367500, 1308842, 1308216, 1341927}
BMI = {3038553}
DM_OTHER = {201254, 195771, 4024659}
AST_ALT = {3013721, 3006923}
DPP4_GLP1 = {1580747, 43526465, 45774435, 1583722}

AMBIGUOUS_IDS = ["I8", "E2", "E5", "E6", "E7", "E8"]
DETERMINATE_ORDER = ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "E1", "E3", "E4"]


def evaluate(fixture: dict, conventions: dict) -> dict:
    """Return {criterion_id: INCLUDED|EXCLUDED|AMBIGUOUS} plus 'membership' bool."""
    index = _d(fixture["index_date"])
    bd = _d(fixture["person"]["birth_date"])
    age = index.year - bd.year - ((index.month, index.day) < (bd.month, bd.day))

    nb = conventions["numeric_bounds"]
    uln = conventions["uln"]["threshold_value_U_per_L"]

    def inc(cond):
        return "INCLUDED" if cond else "EXCLUDED"

    out = {}
    out["I1"] = inc(age >= 20)
    out["I2"] = inc(bool(_conditions(fixture, T2DM, index)))
    out["I3"] = inc(any(nb["hba1c_percent"]["low"] <= v <= nb["hba1c_percent"]["high"]
                        for v in _measurements(fixture, HBA1C, index)))
    out["I4"] = inc(any(nb["uacr_ug_per_mg"]["low"] <= v <= nb["uacr_ug_per_mg"]["high"]
                        for v in _measurements(fixture, UACR, index)))
    out["I5"] = inc(any(v >= nb["egfr_ml_min_1_73m2"]["low"]
                        for v in _measurements(fixture, EGFR, index)))
    out["I6"] = inc(bool(_drugs(fixture, ARB_ACEI, index, min_days_supply=29)))
    out["I7"] = inc(any(nb["bmi_kg_m2"]["low"] <= v <= nb["bmi_kg_m2"]["high"]
                        for v in _measurements(fixture, BMI, index)))
    # exclusions: rule is SATISFIED (INCLUDED) when the disqualifier is absent
    out["E1"] = inc(not _conditions(fixture, DM_OTHER, index))
    out["E3"] = inc(not any(v > uln for v in _measurements(fixture, AST_ALT, index)))
    out["E4"] = inc(not _drugs(fixture, DPP4_GLP1, index, within_days=56))

    for a in AMBIGUOUS_IDS:
        out[a] = "AMBIGUOUS"

    out["membership"] = all(out[c] == "INCLUDED" for c in DETERMINATE_ORDER)
    return out
