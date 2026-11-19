"""Apps that send telemetry are added on their own; stale names never come back."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import autoreg  # noqa: E402


def test_stopped_app_with_only_stale_counters_is_not_added():
    assert autoreg.pick_new({"checkout": 0.0, "payment": 0}, {}, set()) == []


def test_traced_or_logging_app_is_added_with_the_host_its_logs_came_from():
    got = autoreg.pick_new({"api": 0.42}, {"api": "web-1", "worker": None}, set())
    assert got == [{"service_name": "api", "rps": 0.42, "host": "web-1"},
                   {"service_name": "worker", "rps": None, "host": None}]


def test_known_and_ignored_names_are_skipped():
    got = autoreg.pick_new({"metabase": 1.0, "unknown_service": 2.0}, {"aiops-agent": "cp26pt1"}, {"metabase"})
    assert got == []
