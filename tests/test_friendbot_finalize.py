"""friendbot-finalize enforcement plugin probe (runs the node self-check)."""

import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN_DIR = (
    Path(__file__).resolve().parents[1] / "agents" / "agent-3" / "extensions" / "friendbot-finalize"
)
TEST_MJS = PLUGIN_DIR / "test.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not TEST_MJS.exists(),
    reason="node or plugin probe not available in this environment",
)


def test_friendbot_finalize_probe() -> None:
    """node test.mjs must exit 0 with every probe passing."""
    result = subprocess.run(
        ["node", str(TEST_MJS)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"probe failed:\n{result.stdout}\n{result.stderr}"
    assert "probes passed" in result.stdout
