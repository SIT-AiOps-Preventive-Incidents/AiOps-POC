"""Which of the many discovered-but-unmonitored machines are worth connecting first."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import fleet  # noqa: E402

SEGS = [{"cidr": "10.4.82.0/24", "gateway": "10.4.82.254", "host": "cp26pt1", "iface": "eth0"}]
HOSTS = [{"name": "cp26pt1", "ip_addresses": ["10.4.82.20"], "owner": "team-platform", "services": ["postgres", "aiops-api"]}]
NEIGH = [
    {"cidr": "10.4.82.0/24", "ip": "10.4.82.254", "mac": "c4:12:ec:d1:e6:9e", "name": None, "talks_with": [], "last_seen": 1},
    {"cidr": "10.4.82.0/24", "ip": "10.4.82.40", "mac": "bc:24:11:00:00:01", "name": "db2.sit.kmutt.ac.th",
     "talks_with": ["postgres"], "last_seen": 1},
    {"cidr": "10.4.82.0/24", "ip": "10.4.82.41", "mac": "bc:24:11:00:00:02", "name": "app9.sit.kmutt.ac.th",
     "talks_with": [], "last_seen": 1},
    {"cidr": "10.4.82.0/24", "ip": "10.4.82.42", "mac": "bc:24:11:00:00:03", "name": None, "talks_with": [], "last_seen": 1},
]


def test_a_machine_that_talks_to_a_monitored_service_is_the_top_pick():
    recs = fleet.recommend(SEGS, NEIGH, HOSTS, problem_hosts=set())
    assert [r["ip"] for r in recs][0] == "10.4.82.40"                 # it talks to postgres, which we monitor
    assert "postgres" in recs[0]["reasons"][0]
    assert recs[0]["score"] > recs[1]["score"]


def test_the_gateway_and_our_own_hosts_are_never_recommended():
    ips = {r["ip"] for r in fleet.recommend(SEGS, NEIGH, HOSTS, problem_hosts=set())}
    assert "10.4.82.254" not in ips and "10.4.82.20" not in ips       # gateway and the monitored host


def test_being_on_a_network_with_an_active_problem_raises_a_machine():
    calm = {r["ip"]: r["score"] for r in fleet.recommend(SEGS, NEIGH, HOSTS, problem_hosts=set())}
    hot = {r["ip"]: r["score"] for r in fleet.recommend(SEGS, NEIGH, HOSTS, problem_hosts={"cp26pt1"})}
    assert hot["10.4.82.41"] > calm["10.4.82.41"]
    assert any("active problem" in " ".join(r["reasons"]) for r in fleet.recommend(SEGS, NEIGH, HOSTS, problem_hosts={"cp26pt1"}))


def test_every_recommendation_has_a_plain_reason_and_the_list_is_ranked():
    recs = fleet.recommend(SEGS, NEIGH, HOSTS, problem_hosts=set())
    assert all(r["reasons"] and r["score"] > 0 for r in recs)
    assert recs == sorted(recs, key=lambda r: -r["score"])
    assert "10.4.82.42" in {r["ip"] for r in recs}                    # even an unnamed VM on our network is a candidate


def test_nothing_to_recommend_when_every_machine_is_already_ours():
    assert fleet.recommend(SEGS, [NEIGH[0]], HOSTS, problem_hosts=set()) == []   # only the gateway is left


def test_neighbours_are_the_monitored_hosts_on_the_same_network():
    segs = [{"cidr": "10.4.82.0/24", "host": "cp26pt1"}, {"cidr": "10.4.82.0/24", "host": "db-01"},
            {"cidr": "10.9.0.0/24", "host": "esg360-prod"}]
    hosts = [{"name": "cp26pt1", "owner": "team-platform"}, {"name": "db-01", "owner": "team-data"},
             {"name": "esg360-prod", "owner": "team-esg"}]
    n = fleet.neighbours("cp26pt1", segs, hosts)
    assert n == [{"host": "db-01", "owner": "team-data", "networks": ["10.4.82.0/24"]}]   # not esg360 (other network)
    assert fleet.neighbours("esg360-prod", segs, hosts) == []
