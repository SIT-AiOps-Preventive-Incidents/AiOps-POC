"""/api/v1/checks - watch a system from the outside by calling its web address (nothing installed on it)."""
from fastapi import APIRouter, Response

from .. import repo, synthetic
from .errors import ApiError, not_found
from .schemas import CheckIn

router = APIRouter(prefix="/api/v1/checks", tags=["checks"])


@router.post("", status_code=201, summary="Start checking a web address every 10 s")
async def create_check(body: CheckIn, response: Response):
    url = body.url.strip()
    if not synthetic.valid_url(url):
        raise ApiError(422, "url must be an http:// or https:// address")
    if repo.service(body.service_name):
        raise ApiError(409, f"service '{body.service_name}' already exists")
    repo.create_service(body.service_name, display_name=body.display_name or body.service_name.replace("-", " ").title(),
                        kind="service", source="manual", owner=body.owner or "unassigned", environment=body.environment,
                        entry_url=url, entry_method="GET")
    s = repo.update_service(body.service_name, instrumentation=synthetic.KIND)
    first = await synthetic.check(body.service_name, url)   # answer the wizard straight away
    response.headers["Location"] = f"/api/v1/services/{body.service_name}"
    return {"service": s, "first_check": first, "every_s": synthetic.CHECK_S}


@router.get("/{name}", summary="The latest checks of one system, newest first")
async def recent_checks(name: str):
    s = repo.service(name)
    if not s or s.get("instrumentation") != synthetic.KIND:
        raise not_found("check", name)
    return {"service": name, "url": s.get("entry_url"), "every_s": synthetic.CHECK_S, "checks": synthetic.recent(name)}
