"""Request bodies. Pydantic validates them, so handlers only see well-formed input (bad input -> 422)."""
from typing import Literal

from pydantic import BaseModel, Field


class ServiceIn(BaseModel):
    service_name: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = ""
    owner: str = ""
    language: str | None = None
    repo: str = ""
    environment: str = "production"
    entry_url: str | None = None
    entry_method: Literal["GET", "POST"] = "GET"


class ServicePatch(BaseModel):
    display_name: str | None = None
    owner: str | None = None
    language: str | None = None
    repo: str | None = None
    environment: str | None = None
    entry_url: str | None = None
    entry_method: Literal["GET", "POST"] | None = None


class HostIn(BaseModel):
    """A server AIOps pulls from (node_exporter)."""
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9._-]+$")
    address: str = Field(min_length=3)
    os: str = "Linux"
    environment: str = "production"
    owner: str = "team-platform"


class HostRegistration(BaseModel):
    """Sent by the host agent installer; idempotent."""
    os: str = ""
    arch: str = ""
    kind: Literal["server", "workstation"] = "server"


class Inventory(BaseModel):
    ips: list[str] = []
    listeners: list[dict] = []
    connections: list[dict] = []
    containers: list[dict] = []


class DeploymentIn(BaseModel):
    service: str
    version: str
    commit: str
    author: str = "ci-pipeline"
    message: str = ""
    profile: Literal["healthy", "bad"] | None = None


class ApprovalIn(BaseModel):
    decision: Literal["approve", "reject"]
    candidate_id: int | None = None
    approver: str = Field(min_length=1, max_length=80)
    owner_confirmed: bool = False
    comment: str = ""


class IncidentPatch(BaseModel):
    status: Literal["closed"]


class FeedbackIn(BaseModel):
    score: int = Field(ge=1, le=5)
    rca_correct: bool = True
    comment: str = ""


class RunbookPatch(BaseModel):
    enabled: bool


class TestRequestIn(BaseModel):
    entry: str | None = None
