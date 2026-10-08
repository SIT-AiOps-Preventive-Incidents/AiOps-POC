"""/api/v1/service-map, /api/v1/test-requests, /api/v1/traces."""
from fastapi import APIRouter, Response

from .. import servicemap, testreq
from .. import telemetry as tm
from .errors import ApiError, not_found
from .schemas import TestRequestIn

router = APIRouter(prefix="/api/v1", tags=["service map"])


@router.get("/service-map", summary="Nodes and edges: traced calls + connections seen by host agents")
async def get_map(refresh: bool = False):
    return await servicemap.build(force=refresh)


@router.post("/test-requests", status_code=202, summary="Send one real request through the entry point")
async def create_test(body: TestRequestIn, response: Response):
    try:
        run = await testreq.start(body.entry)
    except LookupError as e:
        raise ApiError(409, str(e))
    response.headers["Location"] = f"/api/v1/test-requests/{run['id']}"
    return run


@router.get("/test-requests/{test_id}", summary="Poll a test request until its trace is complete")
async def get_test(test_id: str):
    run = await testreq.get(test_id)
    if not run:
        raise not_found("test request", test_id)
    return run


@router.get("/traces/{trace_id}", summary="A trace flattened into spans")
async def get_trace(trace_id: str):
    spans = await tm.tempo_trace(trace_id)
    if not spans:
        raise not_found("trace", trace_id)
    return spans
