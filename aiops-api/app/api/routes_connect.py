"""/api/v1/connect/ssh - connect a server from the platform (the user never runs a command)."""
from fastapi import APIRouter, Response

from .. import remote, repo
from .errors import not_found
from .schemas import SshBulkConnectIn, SshConnectIn

router = APIRouter(prefix="/api/v1/connect/ssh", tags=["connect"])


@router.post("", status_code=202, summary="Sign in once, install the agent, keep a data channel open")
async def connect(body: SshConnectIn, response: Response):
    job = remote.start(body)
    response.headers["Location"] = f"/api/v1/connect/ssh/jobs/{job['id']}"
    return {"job_id": job["id"]}


@router.post("/bulk", status_code=202, summary="Connect several machines at once with one shared credential")
async def connect_bulk(body: SshBulkConnectIn):
    jobs = [{"name": c.name, "address": c.address, "job_id": remote.start(c)["id"]} for c in body.each()]
    return {"count": len(jobs), "jobs": jobs}


@router.get("/jobs/{job_id}", summary="Progress of a connect: steps, installer output, error")
async def job(job_id: str):
    j = remote.get_job(job_id)
    if not j:
        raise not_found("connect job", job_id)
    return j


@router.get("/key", summary="The platform's public key and the exact line it adds to a server")
async def key():
    pub = remote.platform_public()
    return {"public_key": pub, "authorized_keys_line": remote.tunnel_line(pub)}


@router.get("/links", summary="Servers connected from the platform and the state of their data channel")
async def links():
    return [{**remote.link_state(r["host_name"]), "address": r["address"], "port": r["port"], "user": r["username"],
             "last_connected_at": r["last_connected_at"]} for r in repo.ssh_links()]


@router.delete("/links/{name}", status_code=204, summary="Close the data channel and forget the server")
async def disconnect(name: str):
    if not repo.ssh_link(name):
        raise not_found("connected server", name)
    await remote.stop_link(name)
    repo.delete_ssh_link(name)
    return Response(status_code=204)
