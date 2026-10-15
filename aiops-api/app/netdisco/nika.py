"""NIKA research lab control (bench/nika/bridge.py on the host): its fault cases as demo scenarios, and the ground
truth of whatever is injected, so the Network page can show what NIKA broke next to what AIOps One sees."""
from __future__ import annotations

import os

import httpx

URL = os.environ.get("NIKA_BRIDGE_URL", "http://host.docker.internal:18900").rstrip("/")
PREFIX = "nika:"


async def _get(path: str):
    async with httpx.AsyncClient(timeout=3) as c:
        r = await c.get(URL + path)
        r.raise_for_status()
        return r.json()


async def cases() -> list[str]:
    try:
        return [PREFIX + c["id"] for c in await _get("/cases")]
    except (httpx.HTTPError, ValueError, KeyError):
        return []


async def status() -> dict | None:
    try:
        return await _get("/status")
    except (httpx.HTTPError, ValueError):
        return None


async def play(scenario: str):
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.post(URL + "/play", json={"id": scenario[len(PREFIX):]})
        r.raise_for_status()


async def reset():
    """Redeploy clean, but only when a NIKA fault is active: a redeploy takes ~20 s."""
    s = await status()
    if s and s.get("case"):
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(URL + "/reset")
