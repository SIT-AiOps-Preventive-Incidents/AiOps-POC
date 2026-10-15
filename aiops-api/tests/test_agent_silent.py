"""A service that stops answering leaves no failing span of its own: the agent finds it by its silence."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import agent  # noqa: E402


def test_silent_service_found_and_alerting_service_excluded():
    before = {"nginx-web-server": 0.07, "text-service": 0.036, "media-service": 0.036, "user-service": 0.036}
    now = {"nginx-web-server": 0.06, "media-service": 0.035, "user-service": 0.004}
    got = agent.silent_services(before, now, {"nginx-web-server"})
    assert [g["service"] for g in got] == ["text-service", "user-service"]     # fully silent first
    assert got[0] == {"service": "text-service", "per_min_before": 2.16, "per_min_now": 0.0}


def test_quiet_services_and_normal_dips_are_not_silent():
    assert agent.silent_services({"cron": 0.001}, {}, set()) == []             # never really busy
    assert agent.silent_services({"a": 0.05}, {"a": 0.03}, set()) == []        # slower, still answering


def test_finding_and_fallback_name_the_silent_service():
    facts = {"alerting_service": "nginx-web-server", "error_origin_service": "text-service", "trace_origin_votes": {},
             "silent_services": [{"service": "text-service", "per_min_before": 2.16, "per_min_now": 0.0}],
             "error_rate_by_version": [], "suspect_deploy": None}
    text = " ".join(agent.findings("error_rate", facts))
    assert "text-service stopped answering" in text and "originates" not in text
    rc = agent.fallback_text("error_rate", facts, {"type": "restart_service", "params": {"service": "text-service"}})
    assert rc["root_cause"].startswith("text-service stopped answering")
