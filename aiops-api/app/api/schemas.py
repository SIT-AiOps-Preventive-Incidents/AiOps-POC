"""Request bodies. Pydantic validates them, so handlers only see well-formed input (bad input -> 422)."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ServiceIn(BaseModel):
    service_name: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = ""
    owner: str = ""
    language: str | None = None
    repo: str = ""
    environment: str = "production"
    entry_url: str | None = None
    entry_method: Literal["GET", "POST"] = "GET"


class CheckIn(BaseModel):
    """A system watched from the outside: AIOps calls this address every few seconds."""
    service_name: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    url: str = Field(min_length=8, max_length=500)
    display_name: str = ""
    owner: str = ""
    environment: str = "production"


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
    ebpf: dict | None = None  # {state: running|starting|unavailable|disabled|error, services, error, version}
    interfaces: list[dict] = []  # [{name, cidr, mac, gateway}] - the segments this server sits on
    neighbors: list[dict] = []  # [{ip, mac, name, last_seen}] heard over ARP by the passive watcher
    netwatch: dict | None = None  # passive watcher status {state, error}
    collector: dict | None = None  # OpenTelemetry Collector for logs + container metrics: {state, logs, error, version}


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


class SshConnectIn(BaseModel):
    """Connect a server from the platform. The password or key is used once and never stored."""
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9._-]+$")
    address: str = Field(min_length=1, max_length=253, pattern=r"^[A-Za-z0-9.:-]+$")
    port: int = Field(default=22, ge=1, le=65535)
    user: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    password: str | None = None
    private_key: str | None = None
    passphrase: str | None = None
    ebpf: bool = True

    @model_validator(mode="after")
    def _one_way_in(self):
        if bool(self.password) == bool(self.private_key):
            raise ValueError("give either a password or a private key")
        return self
