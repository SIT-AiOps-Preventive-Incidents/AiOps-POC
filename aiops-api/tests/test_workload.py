"""Apps without traces still get detected and explained: error logs and their container."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import agent, baseline, telemetry as tm  # noqa: E402


def test_error_logs_need_volume_and_double_the_usual():
    band = {"low": 0.0, "high": 2.0, "median": 1.0}
    assert baseline.judge("log_errors", 4, band)["state"] == "ok"        # under 5/min is noise
    assert baseline.judge("log_errors", 9, band)["state"] == "high"


def test_container_memory_safety_limit_applies_while_learning():
    assert baseline.judge("cmem", 98, None)["state"] == "high"
    assert baseline.judge("ccpu", 60, None, fallback_limit=90)["state"] == "learning"


def test_container_query_targets_one_container_on_one_server():
    e = tm.container_expr("esg360-prod", "metabase", "mem")
    assert 'host_name="esg360-prod"' in e and 'container_name="metabase"' in e


def test_findings_explain_a_stopped_container_and_its_logs():
    facts = {"service": "lo-calc", "host": "esg360-prod", "container": "lo-calc", "error_log_count": 3,
             "top_error_log": "soffice crashed", "top_error_log_count": 3, "remote_host": True}
    text = " ".join(agent.findings("container_down", facts))
    assert "not running" in text and "soffice crashed" in text and "observe-only" in text
    fb = agent.fallback_text("container_down", facts, {"type": "manual", "params": {}})
    assert "lo-calc" in fb["root_cause"] and "docker logs lo-calc" in fb["runbook"][0]


def test_every_new_signal_has_a_skill_and_a_label():
    for k in ("log_errors", "container_cpu", "container_mem", "container_down"):
        assert agent.rule_skill(k) == "workload-analysis" and k in agent.KIND_LABEL
