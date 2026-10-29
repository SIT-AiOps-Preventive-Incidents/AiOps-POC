"""Playbook escalation: a fix waiting past the playbook's limit is escalated once, and recorded before it is sent."""
from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import escalation  # noqa: E402

PB = {"id": 1, "name": "Payments on-call", "enabled": True, "trigger": {"kinds": ["error_rate"]},
      "actions": {"owner_team": "team-payments", "escalate_after_min": 30}}


def test_a_fix_waiting_past_the_limit_is_escalated_once(monkeypatch):
    done, sent, order = set(), [], []
    st = escalation.st
    monkeypatch.setattr(st, "playbooks", lambda: [PB])
    monkeypatch.setattr(st, "waiting_for_approval", lambda: [
        {"id": 9, "kind": "error_rate", "severity": "major", "entity": "checkout", "status": "awaiting_approval",
         "analyzed_at": time.time() - 45 * 60},
        {"id": 10, "kind": "error_rate", "severity": "major", "entity": "checkout", "status": "awaiting_approval",
         "analyzed_at": time.time() - 5 * 60}])
    monkeypatch.setattr(st, "escalated", lambda: set(done))
    monkeypatch.setattr(st, "mark_escalated", lambda i, p: (done.add((i, p)), order.append("mark")))

    async def send(iid, event):
        order.append("send"); sent.append((iid, event))
    monkeypatch.setattr(escalation.notify, "send", send)
    asyncio.run(escalation.tick())
    asyncio.run(escalation.tick())
    assert sent == [(9, "escalation")] and order == ["mark", "send"]
