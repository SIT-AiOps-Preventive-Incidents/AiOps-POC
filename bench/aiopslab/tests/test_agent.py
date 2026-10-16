"""Unit tests for the bench agent: parsers, rules, guard and the step loop, on recorded-style kubectl output.
No cluster, no AIOpsLab, no LLM needed.  Run: python -m pytest bench/aiopslab/tests"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent import AIOpsOneAgent  # noqa: E402
from agent import evidence as evi  # noqa: E402
from agent import guard, skills  # noqa: E402

PODS_HEALTHY = """NAME                                      READY   STATUS    RESTARTS   AGE   IP
frontend-6b9d8c7f5-x2k4p                  1/1     Running   0          5m    10.244.0.12
geo-7c8d9e6f4-ab12c                       1/1     Running   0          5m    10.244.0.13
mongodb-geo-5d4c9b8a7-zz9yx               1/1     Running   0          5m    10.244.0.14
consul-0                                  1/1     Running   0          5m    10.244.0.15
"""
PODS_GEO_CRASH = PODS_HEALTHY.replace("geo-7c8d9e6f4-ab12c                       1/1     Running   0",
                                      "geo-7c8d9e6f4-ab12c                       0/1     CrashLoopBackOff   4")
LOGS_AUTH = """== pod/frontend-6b9d8c7f5-x2k4p
== pod/geo-7c8d9e6f4-ab12c
{"level":"error","message":"not authorized on geo-db to execute command { find: \\"geo\\" }"}
== pod/mongodb-geo-5d4c9b8a7-zz9yx
== pod/consul-0
"""
LOGS_CONFIG = """== pod/geo-7c8d9e6f4-ab12c
panic: invalid argument: unknown flag --dbaddr
== pod/mongodb-geo-5d4c9b8a7-zz9yx
"""
EVENTS_NONE = "No resources found in test-hotel-reservation namespace."


def ev(pods, logs="", events=EVENTS_NONE):
    return evi.collect("test-hotel-reservation", {"pods": pods, "events": events, "logs": logs})


def test_component_names_drop_kubernetes_suffixes():
    assert evi.component_of("geo-7c8d9e6f4-ab12c") == "geo"
    assert evi.component_of("mongodb-geo-5d4c9b8a7-zz9yx") == "mongodb-geo"
    assert evi.component_of("consul-0") == "consul"
    assert evi.component_of("jaeger") == "jaeger"


def test_namespace_is_read_from_the_problem_text():
    assert evi.namespace_from("Service Name: Hotel Reservation\nNamespace: test-hotel-reservation\n") == "test-hotel-reservation"


def test_healthy_cluster_is_not_an_anomaly():
    v = skills.judge(ev(PODS_HEALTHY))
    assert not v.anomaly and v.culprits == []


def test_auth_errors_point_at_the_data_store_the_app_uses():
    v = skills.judge(ev(PODS_HEALTHY, LOGS_AUTH))
    assert v.anomaly and v.fault_kind == "auth" and v.culprits == ["mongodb-geo"]
    assert skills.analysis_answer(v) == {"system_level": "Application", "fault_type": "Authentication Issue"}


def test_a_crashing_misconfigured_app_is_the_culprit_and_gets_rolled_back():
    e = ev(PODS_GEO_CRASH, LOGS_CONFIG)
    v = skills.judge(e)
    assert v.fault_kind == "config" and v.culprits == ["geo"]
    assert skills.mitigation_plan(e, v) == [("kubectl rollout history deployment/geo -n test-hotel-reservation",
                                             "kubectl rollout undo deployment/geo -n test-hotel-reservation")]


def test_data_store_problems_are_left_to_a_person():
    e = ev(PODS_HEALTHY, LOGS_AUTH)
    assert skills.mitigation_plan(e, skills.judge(e)) == []


LOGS_STARTUP_NOISE = """== pod/frontend-6b9d8c7f5-x2k4p
2026/10/14 06:44:52 grpc/lb/consul: error retrieving instances from Consul: dial tcp 10.96.229.58:8500: connect: connection refused
== pod/jaeger-67445b6dd6-qxk2r
last error: connection error: desc = "transport: Error while dialing: dial tcp [::1]:14250: socket: address family not supported"
"""


def test_retry_noise_from_healthy_pods_is_not_an_incident():
    # seen on AIOpsLab's no-fault problem: startup and IPv6 retries in pods that are Running, Ready, 0 restarts
    assert not skills.judge(ev(PODS_HEALTHY, LOGS_STARTUP_NOISE)).anomaly


def test_the_same_errors_count_when_the_pod_is_in_trouble():
    crash_frontend = PODS_HEALTHY.replace("frontend-6b9d8c7f5-x2k4p                  1/1     Running   0",
                                          "frontend-6b9d8c7f5-x2k4p                  0/1     CrashLoopBackOff   3")
    v = skills.judge(ev(crash_frontend, LOGS_STARTUP_NOISE))
    assert v.anomaly and v.fault_kind == "network" and v.culprits == ["frontend"]


def test_unhealthy_without_a_cause_is_flagged_but_not_confident():
    v = skills.judge(ev(PODS_GEO_CRASH))
    assert v.anomaly and not v.confident and v.culprits == ["geo"]


def test_guard_rejects_components_that_do_not_exist_or_have_no_evidence():
    e = ev(PODS_GEO_CRASH, LOGS_CONFIG)
    v = skills.judge(e)
    assert guard.check_culprits(["payments-db"], e, v)[0] == ["geo"]
    assert guard.check_culprits(["consul"], e, v)[0] == ["geo"]
    assert guard.check_culprits(["geo"], e, v) == (["geo"], "accepted")


def test_guard_rejects_a_fault_type_the_evidence_contradicts():
    v = skills.judge(ev(PODS_HEALTHY, LOGS_AUTH))
    out, why = guard.check_analysis({"system_level": "Hardware", "fault_type": "Code Defect"}, v)
    assert out["fault_type"] == "Authentication Issue" and why.startswith("rejected")


def _run(agent, observations):
    async def go():
        actions = [await agent.get_action("Please take the next action")]
        for obs in observations:
            actions.append(await agent.get_action(obs + "\nPlease take the next action"))
        return actions
    return asyncio.run(go())


def test_agent_reads_evidence_then_submits_one_answer():
    a = AIOpsOneAgent()
    a.init_context("Namespace: test-hotel-reservation", "", {"submit(faulty_components)": "faulty_components (list[str])"})
    actions = _run(a, [PODS_HEALTHY, EVENTS_NONE, LOGS_AUTH])
    assert [x.split("(")[0].strip("`\n") for x in actions] == ["exec_shell", "exec_shell", "exec_shell", "submit"]
    assert actions[-1] == '```\nsubmit(["mongodb-geo"])\n```'
    assert a.trace[0]["task"] == "localization"
    assert next(t for t in a.trace if t["kind"] == "analysis")["evidence_ok"] is True


def test_agent_records_when_it_could_not_see_the_cluster():
    a = AIOpsOneAgent()
    a.init_context("Namespace: test-hotel-reservation", "", {"submit(has_anomaly)": "has_anomaly"})
    _run(a, ["Error response from daemon: No such container", "", ""])
    assert next(t for t in a.trace if t["kind"] == "analysis")["evidence_ok"] is False


def test_mitigation_runs_dry_run_then_apply_then_verify():
    a = AIOpsOneAgent()
    a.init_context("Namespace: test-hotel-reservation", "submit()", {"submit()": "Submit once your mitigation is done"})
    actions = _run(a, [PODS_GEO_CRASH, EVENTS_NONE, LOGS_CONFIG, "rev 1, rev 2", "rolled back", "successfully rolled out"])
    shells = [x for x in actions if "exec_shell" in x]
    assert "rollout history" in shells[3] and "rollout undo" in shells[4] and "rollout status" in shells[5]
    assert actions[-1] == "```\nsubmit()\n```"
