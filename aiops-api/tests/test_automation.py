"""User-built automation: skills, skill sets, runbooks and playbooks (pure rules, no database, no LLM)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import automation as a  # noqa: E402

BUILTIN = [{"id": "service-error-analysis", "kinds": ["error_rate"], "enabled": True, "builtin": True},
           {"id": "infra-resource-analysis", "kinds": ["host_cpu", "host_disk"], "enabled": True, "builtin": True}]
CUSTOM = {"id": "payments-errors", "kinds": ["error_rate"], "enabled": True, "builtin": False}


# ------------------------------------------------------------------ tools a custom skill may use
def test_every_tool_gets_its_arguments_from_the_incident_entity():
    assert a.tool_args("searchLogs", "checkout", "service") == {"service": "checkout"}
    assert a.tool_args("getHostMetrics", "db-01", "host") == {"host": "db-01"}
    assert a.tool_args("searchFirewallLogs", "checkout", "service") == {}
    assert a.tool_args("getHostMetrics", "checkout", "service") is None      # needs a host, incident is about a service
    assert a.tool_args("nope", "x", "service") is None


def test_catalog_lists_only_read_only_tools_with_plain_labels():
    assert "searchLogs" in a.TOOL_CATALOG and a.TOOL_CATALOG["searchLogs"]["label"]
    assert all(t["reads"] for t in a.TOOL_CATALOG.values())


# ------------------------------------------------------------------ a skill someone writes
def test_a_custom_skill_needs_a_name_triggers_known_tools_and_gets_a_safe_id():
    body = {"name": "Payments errors", "kinds": ["error_rate"], "tools": ["searchLogs", "getMetric"], "instructions": "Check the card gateway first."}
    assert a.validate_skill(body) == []
    assert a.skill_id("Payments errors / v2!") == "custom-payments-errors-v2"
    errs = a.validate_skill({"name": "", "kinds": ["teleport"], "tools": ["rm -rf"]})
    assert any("name" in e for e in errs) and any("teleport" in e for e in errs) and any("rm -rf" in e for e in errs)


def test_eligible_skills_follow_the_incident_kind_and_drop_disabled_ones():
    assert a.eligible_skills("error_rate", "checkout", BUILTIN + [CUSTOM], []) == ["service-error-analysis", "payments-errors"]
    off = {**CUSTOM, "enabled": False}
    assert a.eligible_skills("error_rate", "checkout", BUILTIN + [off], []) == ["service-error-analysis"]


def test_a_skill_set_scoped_to_a_service_narrows_the_choice_for_that_service_only():
    sets = [{"name": "Payments", "scope": "pay-*, checkout", "skills": ["payments-errors"], "enabled": True}]
    assert a.eligible_skills("error_rate", "checkout", BUILTIN + [CUSTOM], sets) == ["payments-errors"]
    assert a.eligible_skills("error_rate", "search", BUILTIN + [CUSTOM], sets) == ["service-error-analysis", "payments-errors"]
    # a set whose skills do not cover this kind does not leave the incident with nothing
    assert a.eligible_skills("host_cpu", "checkout", BUILTIN + [CUSTOM], sets) == ["infra-resource-analysis"]


def test_base_skill_is_the_builtin_investigation_a_custom_skill_rides_on():
    assert a.base_skill("host_disk", BUILTIN) == "infra-resource-analysis"


# ------------------------------------------------------------------ a runbook someone writes
def test_a_written_runbook_matches_by_kind_service_and_fix_like_a_learned_one():
    body = {"title": "Checkout 5xx after deploy", "kind": "error_rate", "service": "checkout", "action_type": "rollback_deployment",
            "root_cause": "A bad release", "steps": ["Check the deploy", "Roll back"]}
    assert a.validate_runbook(body) == []
    assert a.runbook_signature(body) == "error_rate|checkout|rollback_deployment"
    errs = a.validate_runbook({"title": "", "kind": "error_rate", "service": "", "action_type": "format_disk", "steps": []})
    assert any("title" in e for e in errs) and any("format_disk" in e for e in errs) and any("step" in e for e in errs)


# ------------------------------------------------------------------ playbooks: when X happens, do Y
PB = {"id": 1, "name": "Payments on-call", "enabled": True,
      "trigger": {"kinds": ["error_rate", "latency"], "min_severity": "major", "entity": "checkout*"},
      "actions": {"owner_team": "team-payments", "escalate_after_min": 30}}


def test_a_playbook_fires_on_its_kinds_severity_and_entity_only():
    inc = {"id": 9, "kind": "error_rate", "severity": "critical", "entity": "checkout"}
    assert [p["id"] for p in a.match_playbooks(inc, [PB])] == [1]
    assert a.match_playbooks({**inc, "severity": "minor"}, [PB]) == []
    assert a.match_playbooks({**inc, "entity": "search"}, [PB]) == []
    assert a.match_playbooks({**inc, "kind": "host_cpu"}, [PB]) == []
    assert a.match_playbooks(inc, [{**PB, "enabled": False}]) == []
    assert [p["id"] for p in a.match_playbooks(inc, [{**PB, "trigger": {}}])] == [1]     # no trigger = every incident


def test_escalation_is_due_once_after_the_wait_and_never_twice():
    waiting = [{"id": 9, "kind": "error_rate", "severity": "major", "entity": "checkout", "analyzed_at": 1000.0, "status": "awaiting_approval"}]
    assert a.due_escalations(waiting, [PB], escalated=set(), now=1000 + 29 * 60) == []
    assert a.due_escalations(waiting, [PB], escalated=set(), now=1000 + 31 * 60) == [(9, 1)]
    assert a.due_escalations(waiting, [PB], escalated={(9, 1)}, now=1000 + 90 * 60) == []


def test_playbooks_are_validated_and_never_apply_a_fix_on_their_own():
    assert a.validate_playbook({"name": "x", "trigger": {"kinds": ["error_rate"]}, "actions": {"escalate_after_min": 15}}) == []
    errs = a.validate_playbook({"name": "", "trigger": {"kinds": ["nope"], "min_severity": "huge"}, "actions": {"auto_apply": True}})
    assert any("name" in e for e in errs) and any("nope" in e for e in errs) and any("huge" in e for e in errs)
    assert any("approval" in e for e in errs)


# ------------------------------------------------------------------ the agent's choice among what the team allows
def test_the_llm_may_only_pick_a_skill_the_team_allows_for_this_incident():
    assert a.choose_skill(["service-error-analysis", "payments-errors"], "payments-errors", "service-error-analysis")[0] == "payments-errors"
    skill, why = a.choose_skill(["payments-errors"], "service-error-analysis", "service-error-analysis")
    assert skill == "payments-errors" and "skill set" in why
    skill, why = a.choose_skill([], None, "service-error-analysis")     # every skill for the kind switched off
    assert skill == "service-error-analysis" and "switched off" in why


def test_a_custom_skill_adds_only_the_tools_its_built_in_base_does_not_run():
    assert a.extra_tools(["searchLogs", "searchFirewallLogs", "getHostMetrics"], ["searchLogs", "getMetric"]) == ["searchFirewallLogs", "getHostMetrics"]


def test_a_new_playbook_does_not_escalate_the_backlog_that_was_waiting_before_it_existed():
    old = [{"id": 3, "kind": "error_rate", "severity": "major", "entity": "checkout", "analyzed_at": 1000.0, "status": "awaiting_approval"}]
    assert a.due_escalations(old, [{**PB, "since": 5000.0}], escalated=set(), now=9000.0) == []
    assert a.due_escalations(old, [{**PB, "since": 500.0}], escalated=set(), now=9000.0) == [(3, 1)]
