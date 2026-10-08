"""AIOps One - API server.

REST API under /api/v1 (OpenAPI docs at /docs), the agent installer under /install, and the Vue single-page
app served from the same origin.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import agent, db, detector, repo, seed
from .api import errors, routes_hosts, routes_incidents, routes_map, routes_platform, routes_services
from .api.schemas import HostRegistration

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
APP_DIR = os.path.dirname(__file__)
WEB_DIST = os.environ.get("WEB_DIST", os.path.join(APP_DIR, "web"))
AGENT_DIST = os.path.join(APP_DIR, "agent_dist")
PUBLIC_URL = routes_platform.PUBLIC_URL
OTLP_PUBLIC = routes_platform.OTLP_PUBLIC


async def rotate_edge_logs():
    """Network device logs are shipped to Loki; keep the local files from filling the disk."""
    while True:
        for f in ("/var/log/edge/firewall.log", "/var/log/edge/lb.log"):
            try:
                if os.path.getsize(f) > 50 * 2**20:
                    open(f, "w").close()
            except OSError:
                pass
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(_):
    db.init()
    repo.seed_skills(agent.SKILLS)
    if seed.migrate_sqlite():
        logging.info("imported legacy SQLite data")
    seed.ensure_demo()
    routes_hosts.write_targets()
    tasks = [asyncio.create_task(detector.loop()), asyncio.create_task(rotate_edge_logs())]
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="AIOps One API", version="1.0.0", lifespan=lifespan,
              description="Agentic root cause analysis: services, hosts, service map, incidents, approvals.")
errors.install(app)
for r in (routes_platform, routes_services, routes_hosts, routes_map, routes_incidents):
    app.include_router(r.router)


# ---------------- agent installer (plain text, piped into sh) ----------------
def _dist(name: str) -> str:
    with open(os.path.join(AGENT_DIST, name)) as f:
        return f.read().replace("__API__", PUBLIC_URL).replace("__OTLP__", OTLP_PUBLIC)


@app.get("/install/agent.sh", response_class=PlainTextResponse, include_in_schema=False)
async def install_script():
    return _dist("install.sh")


@app.get("/install/uninstall.sh", response_class=PlainTextResponse, include_in_schema=False)
async def uninstall_script():
    return _dist("uninstall.sh")


@app.get("/install/aiops-agent.py", response_class=PlainTextResponse, include_in_schema=False)
async def agent_py():
    return _dist("aiops-agent.py")


# ---------------- compatibility for agents installed before /api/v1 ----------------
@app.get("/api/ping", include_in_schema=False)
async def ping():
    return {"ok": True}


@app.post("/api/hosts/register", include_in_schema=False)
async def legacy_register(body: dict):
    return await routes_hosts.register_host(body["name"], HostRegistration(**{k: v for k, v in body.items() if k != "name"}))


# ---------------- web app ----------------
if os.path.isdir(WEB_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(WEB_DIST, "assets")), name="assets")
    if os.path.isdir(os.path.join(WEB_DIST, "icons")):
        app.mount("/icons", StaticFiles(directory=os.path.join(WEB_DIST, "icons")), name="icons")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(os.path.join(WEB_DIST, "index.html"))
