"""Request bodies. Pydantic validates them, so handlers only see well-formed input (bad input -> 422)."""
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class PageSummaryIn(BaseModel):
    page: Literal[
        "dashboard", "technical_overview", "incident_list", "incident_detail", "service_list", "service_detail",
        "host_list", "host_detail", "service_map", "fleet_map", "fleet_list", "fleet_3d", "cloud_accounts", "insights",
        "connect", "connect_computer", "connect_service", "connect_website", "ai_skills", "playbooks", "runbooks",
        "notifications", "deployments", "demo_scenarios", "pricing", "design_system", "settings", "access", "page_not_found",
    ]
    locale: Literal["en", "th"]
    facts: dict[Literal[
        "open_incidents", "awaiting_approval", "ai_investigations", "fixes_in_progress", "failed_fixes",
        "recent_closed_incidents", "monitored_services", "services_with_issues", "monitored_hosts", "hosts_with_issues",
        "resources_without_data", "affected_services", "proposed_fixes", "applications", "network_devices",
        "discovered_services", "map_connections", "known_machines", "networks", "cloud_accounts", "findings",
        "available_skills", "enabled_runbooks", "enabled_playbooks", "recent_notifications", "recent_deployments",
        "available_scenarios", "detector_active", "detector_unconfirmed", "stale_data", "incident_open",
        "incident_analyzing", "incident_awaiting_approval", "incident_remediating", "incident_verifying",
        "incident_resolved", "incident_rejected", "incident_closed", "incident_remediation_failed", "health_healthy",
        "health_problem", "health_down", "health_offline", "health_no_data", "test_sending", "test_tracing",
        "test_playing", "test_error", "connecting", "connection_failed", "waiting_for_data", "sending_data",
        "check_successful", "check_failed", "discovery_requested", "demo_starting", "auto_investigation_on",
        "auto_investigation_off", "issue_error_rate", "issue_latency", "issue_host_cpu", "issue_host_mem",
        "issue_host_disk", "issue_host_down", "issue_auth_bruteforce", "issue_log_errors", "issue_container_cpu",
        "issue_container_mem", "issue_container_down",
    ], Annotated[int, Field(strict=True, ge=0, le=2**53 - 1)]] = Field(max_length=16)


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
    approver: str = Field(default="", max_length=80)   # ignored when someone is signed in: the session names them
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


class BulkTarget(BaseModel):
    """One machine to connect in a bulk run. name defaults to the address when the discovery had no hostname.
    A machine may bring its own sign-in (user, password or key); anything it leaves out comes from the shared one."""
    address: str = Field(min_length=1, max_length=253, pattern=r"^[A-Za-z0-9.:-]+$")
    name: str | None = Field(default=None, max_length=60, pattern=r"^[A-Za-z0-9._-]+$")
    user: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    password: str | None = None
    private_key: str | None = None
    passphrase: str | None = None


class SshBulkConnectIn(BaseModel):
    """Connect several machines in one go with one shared credential - the fleet case: many VMs from one template
    reachable with the same key or password. Each becomes its own connect job; the credential is used once per host
    and never stored."""
    targets: list[BulkTarget] = Field(min_length=1, max_length=50)
    port: int = Field(default=22, ge=1, le=65535)
    user: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    password: str | None = None
    private_key: str | None = None
    passphrase: str | None = None
    ebpf: bool = True

    @model_validator(mode="after")
    def _one_way_in(self):
        if self.password and self.private_key:
            raise ValueError("give either a password or a private key, not both")
        for t in self.targets:
            own = bool(t.password or t.private_key)
            if t.password and t.private_key:
                raise ValueError(f"{t.address}: give either a password or a private key, not both")
            if not own and not (self.password or self.private_key):
                raise ValueError(f"{t.address}: no password or key, and no shared one")
            if not (t.user or self.user):
                raise ValueError(f"{t.address}: no user to sign in as")
        return self

    def each(self) -> list[SshConnectIn]:
        """One SshConnectIn per target, carrying the shared credential. A target without a hostname is named after
        its address (dots and colons swapped for dashes so it is a valid host name)."""
        out = []
        for t in self.targets:
            name = t.name or t.address.replace(".", "-").replace(":", "-")
            own = bool(t.password or t.private_key)   # a machine's own credential replaces the shared one entirely
            out.append(SshConnectIn(name=name, address=t.address, port=self.port, user=t.user or self.user,
                                    password=t.password if own else self.password,
                                    private_key=t.private_key if own else self.private_key,
                                    passphrase=t.passphrase if own else self.passphrase, ebpf=self.ebpf))
        return out
