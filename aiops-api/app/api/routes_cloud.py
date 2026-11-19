"""/api/v1/cloud: connect a cloud account (read-only), see every instance it holds, and what changed."""
from fastapi import APIRouter, Response

from .. import cloud, cloudinv
from .errors import ApiError, not_found

router = APIRouter(prefix="/api/v1/cloud", tags=["cloud"])


@router.get("/providers", summary="Clouds we can read, the fields each needs, and the least privilege to grant")
async def providers():
    return [{"id": k, **v} for k, v in cloud.PROVIDERS.items()]


@router.get("/accounts", summary="Connected cloud accounts (secrets are never returned)")
async def list_accounts():
    return [cloud.public(a) for a in cloudinv.accounts()]


@router.post("/accounts", status_code=201, summary="Connect a cloud account: the credential is tested before it is stored")
async def add_account(body: dict):
    provider, name = (body.get("provider") or "").strip(), (body.get("name") or "").strip()
    config, secret = body.get("config") or {}, body.get("secret") or {}
    errs = cloud.validate(provider, config, secret) + ([] if name else ["name is required"])
    if errs:
        raise ApiError(422, "; ".join(errs), details={"problems": errs})
    try:
        found = await cloud.fetch(provider, config, secret)
    except cloud.CloudError as e:
        raise ApiError(422, str(e), code="credential_failed")
    try:
        acc = cloudinv.create(provider, name, config, secret)
    except Exception as e:
        if "unique" in str(e).lower():
            raise ApiError(409, f"a cloud account named '{name}' already exists")
        raise
    d = cloudinv.save_sync(acc["id"], found)
    return {"account": cloud.public(cloudinv.get(acc["id"])),
            "sync": {"instances": len(found), "added": len(d["added"]), "removed": len(d["removed"]), "changed": len(d["changed"])}}


@router.post("/accounts/{account_id}/sync", summary="Read the account now")
async def sync_account(account_id: int):
    if not cloudinv.get(account_id):
        raise not_found("cloud account", account_id)
    try:
        return await cloudinv.sync(account_id)
    except cloud.CloudError as e:
        raise ApiError(502, str(e), code="provider_failed")


@router.delete("/accounts/{account_id}", status_code=204, summary="Disconnect: the credential and its instances are deleted")
async def delete_account(account_id: int):
    if not cloudinv.get(account_id):
        raise not_found("cloud account", account_id)
    cloudinv.delete(account_id)
    return Response(status_code=204)


@router.get("/instances", summary="Every instance, matched to our agents, with what the cloud and the agent say together")
async def list_instances(account_id: int | None = None):
    return [{**i, "verdict": cloud.verdict(i["state"], i.get("host_status"))} for i in await cloudinv.instances(account_id)]


@router.get("/events", summary="Cloud changes: instances added, removed, started or stopped")
async def list_events(limit: int = 50):
    return cloudinv.events(min(limit, 500))
