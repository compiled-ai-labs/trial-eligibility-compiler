"""Gate 3 — behaviour. R-gated: executes cohort.json via the OHDSI bridge.

Skips locally when Rscript is absent; runs for real in .devcontainer/CI where the
CirceR/SqlRender/DatabaseConnector stack is installed.
"""

import pytest

from tec.gates import g3_fixtures
from tec.gates.common import rscript_available
from tec.runtime.trcheck import BridgeUnavailable

pytestmark = pytest.mark.skipif(
    not rscript_available(),
    reason="Rscript / OHDSI stack unavailable; Gate 3 runs in .devcontainer/CI only.",
)


def test_gate3_behaviour():
    try:
        res = g3_fixtures.run("NCT03667300")
    except BridgeUnavailable as e:
        pytest.skip(str(e))
    assert res.ok, res.summary()
