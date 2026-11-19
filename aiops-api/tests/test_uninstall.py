"""Remove agent: the platform asks the agent to remove itself on its next report - no password needed again."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import inventory  # noqa: E402


def test_agent_is_told_to_remove_itself_only_after_someone_asked():
    out = {"host": "esg360-prod", "instrument": [], "collector": "{}"}
    assert "uninstall" not in inventory.with_uninstall(dict(out), {"uninstall_requested_at": None})
    told = inventory.with_uninstall(dict(out), {"uninstall_requested_at": 1792070000.0})
    assert told["uninstall"] is True
    assert told["instrument"] == [] and "collector" not in told     # start nothing new on a machine being cleaned
