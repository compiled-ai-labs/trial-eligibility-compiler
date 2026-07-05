"""The four validation gates (PLAN.md §5).

Gates 1-2 are pure Python and run inside the compiler retry loop (Stage 2) and in
CI. Gates 3-4 execute the artifact against the synthetic CDM via the OHDSI R
bridge and run in CI (they skip locally when R is unavailable).

An artifact is committed only after Gates 1 & 2 pass; Gates 3 & 4 must be green in
CI. Never weaken a gate to make it pass (CLAUDE.md invariant 1).
"""

from tec.gates.common import GateResult

__all__ = ["GateResult"]
