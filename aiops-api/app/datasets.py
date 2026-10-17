"""Which application the demo monitors. Set with DEMO_DATASET:

  shop    (default) the instrumented shop in docker-compose.yml: frontend, checkout, payment, inventory, edge-fw/lb
  anomod  SocialNetwork from AnoMod (Ping et al., MSR'26, CC BY 4.0): logs and traces recorded from a real running
          system, replayed live by replay/anomod. The 12 services are registered here; their telemetry arrives
          over OTLP like any traced app, so the detector, service map and agent work on it unchanged.

Switching back and forth only changes which services are registered; incidents and history are kept.
"""
from __future__ import annotations

import os

import httpx

from . import repo, seed

DATASET = os.environ.get("DEMO_DATASET", "shop").strip().lower()
REPLAY_URL = os.environ.get("ANOMOD_REPLAY_URL", "http://anomod-replay:8000")

# service, display name, owner team, tier. The tier decides which lab switch the service's host sits behind.
SOCIALNETWORK = [
    ("nginx-web-server", "Web Gateway (nginx)", "team-web", "app"),
    ("compose-post-service", "Compose Post", "team-posts", "app"),
    ("home-timeline-service", "Home Timeline", "team-timeline", "app"),
    ("user-timeline-service", "User Timeline", "team-timeline", "app"),
    ("text-service", "Text", "team-posts", "app"),
    ("media-service", "Media", "team-posts", "app"),
    ("url-shorten-service", "URL Shorten", "team-posts", "app"),
    ("user-mention-service", "User Mention", "team-posts", "app"),
    ("unique-id-service", "Unique ID", "team-posts", "app"),
    ("user-service", "User", "team-identity", "data"),
    ("social-graph-service", "Social Graph", "team-identity", "data"),
    ("post-storage-service", "Post Storage", "team-posts", "data"),
]


REPLAY_AGENT = "anomod-replay"   # hosts.agent of the stand-in machines: no host metrics, health follows the service


def host_of(service: str) -> str:
    """The lab host (container) that stands for a replayed service on the network."""
    return f"sn-{service}"


def ensure():
    if DATASET == "anomod":
        ensure_anomod()
    else:
        seed.ensure_demo()


def ensure_anomod():
    if not repo.host(seed.PLATFORM_HOST):
        repo.upsert_host(seed.PLATFORM_HOST, address="node-exporter:9100", os="Ubuntu 26.04", agent="node_exporter",
                         kind="server", environment="poc", owner="team-platform")
    for svc, *_ in seed.DEMO:          # the shop is not running in this mode
        if repo.service(svc):
            repo.delete_service(svc)
    for svc, disp, owner, _tier in SOCIALNETWORK:
        if not repo.service(svc):
            repo.create_service(svc, display_name=disp, kind="service", source="traced", language="cpp", owner=owner,
                                repo="github.com/delimitrou/DeathStarBench/socialNetwork", environment="anomod")
        repo.update_service(svc, instrumentation="sdk", entry_url=None)
        # Each replayed service gets its own stand-in machine, so the map reads like the real spread-out deployment.
        repo.upsert_host(host_of(svc), os="AnoMod replay", agent=REPLAY_AGENT, kind="server", environment="anomod",
                         owner=owner)
        repo.ensure_instance(svc, host_of(svc), host=host_of(svc), container=host_of(svc))


# ---------------- scenarios: replay a recorded fault ----------------
PREFIX = "anomod:"


async def replay_cases() -> list[str]:
    if DATASET != "anomod":
        return []
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{REPLAY_URL}/cases")
            r.raise_for_status()
            return [PREFIX + n for n in r.json().get("faults", [])]
    except httpx.HTTPError:
        return []


async def play(scenario: str):
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.post(f"{REPLAY_URL}/play", json={"case": scenario[len(PREFIX):]})
        r.raise_for_status()
        return r.json()


async def reset():
    if DATASET != "anomod":
        return
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{REPLAY_URL}/stop")
    except httpx.HTTPError:
        pass
