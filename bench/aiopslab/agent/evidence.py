"""Evidence: what the agent reads from the cluster, and how it reads it.

Two halves, both free of AIOpsLab and of any LLM:
  * PLAYBOOK - the shell commands the agent runs, in order (deterministic, like AIOps One's skill playbooks)
  * parsers  - turn kubectl output into Findings: which component, what kind of trouble, and the line that shows it
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

DB_HINT = re.compile(r"mongo|mysql|postgres|redis|memcache|cassandra|etcd|consul", re.I)

# kind of trouble -> words that show it in a log line or event. General SRE knowledge, not tied to any benchmark.
SIGNS = {
    "auth": re.compile(r"unauthori[sz]ed|not authori[sz]ed|authentication fail|auth(entication)? error|permission denied|"
                       r"access denied|requires authentication|invalid credentials|user .* not found|userNotFound|"
                       r"command \w+ requires", re.I),
    "network": re.compile(r"connection refused|connection reset|i/o timeout|no such host|dial tcp|context deadline exceeded|"
                          r"network is unreachable|no route to host|EOF", re.I),
    "storage": re.compile(r"no space left|read-only file system|volume|mount|persistentvolume|disk", re.I),
    "config": re.compile(r"invalid (argument|config|value)|parse error|unknown (flag|field)|missing required|cannot unmarshal|"
                         r"configuration|bad config|env var", re.I),
    "crash": re.compile(r"panic:|fatal|segmentation fault|exit code [1-9]|crashloopbackoff|back-off restarting|oomkilled", re.I),
}
ORDER = ["auth", "storage", "config", "network", "crash"]  # most specific first


@dataclass
class Pod:
    name: str
    ready: str
    status: str
    restarts: int

    @property
    def component(self) -> str:
        return component_of(self.name)

    @property
    def healthy(self) -> bool:
        have, want = (self.ready.split("/") + ["0"])[:2]
        return self.status in ("Running", "Completed") and have == want and self.restarts == 0


@dataclass
class Finding:
    component: str
    kind: str          # auth | storage | config | network | crash | unhealthy
    line: str          # the evidence, as seen
    source: str = ""   # "logs" | "events" | "pods"


@dataclass
class Evidence:
    namespace: str = ""
    pods: list[Pod] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def components(self) -> set[str]:
        return {p.component for p in self.pods}

    def by_kind(self, kind: str) -> list[Finding]:
        return [f for f in self.findings if f.kind == kind]


def component_of(pod_name: str) -> str:
    """'geo-6b9d8c7f5-x2k4p' -> 'geo';  'mongodb-geo-5d4c9-abcde' -> 'mongodb-geo';  'consul-0' -> 'consul'."""
    parts = pod_name.split("-")
    if len(parts) >= 3 and re.fullmatch(r"[a-z0-9]{8,10}", parts[-2]) and re.fullmatch(r"[a-z0-9]{5}", parts[-1]):
        return "-".join(parts[:-2])
    if len(parts) >= 2 and re.fullmatch(r"[a-z0-9]{5}|\d+", parts[-1]):
        return "-".join(parts[:-1])
    return pod_name


def namespace_from(problem_desc: str) -> str:
    m = re.search(r"[Nn]amespace\W+([a-z0-9][a-z0-9-]*)", problem_desc)
    return m.group(1) if m else "default"


def parse_pods(text: str) -> list[Pod]:
    pods = []
    for line in text.splitlines():
        cols = line.split()
        if len(cols) < 4 or cols[0] == "NAME" or "/" not in cols[1]:
            continue
        restarts = re.match(r"\d+", cols[3])
        pods.append(Pod(cols[0], cols[1], cols[2], int(restarts.group()) if restarts else 0))
    return pods


def classify(line: str) -> str | None:
    for kind in ORDER:
        if SIGNS[kind].search(line):
            return kind
    return None


def parse_events(text: str, components: set[str]) -> list[Finding]:
    """Warning events -> findings, attributed to the component named in the event's object."""
    out = []
    for line in text.splitlines():
        if "Warning" not in line:
            continue
        kind = classify(line) or "unhealthy"
        comp = next((c for c in sorted(components, key=len, reverse=True) if re.search(rf"\b{re.escape(c)}\b", line)), None)
        if comp:
            out.append(Finding(comp, kind, line.strip()[-240:], "events"))
    return out


def parse_log_scan(text: str) -> list[Finding]:
    """Output of the log-scan command: '== pod/<name>' headers, then that pod's suspicious lines."""
    out, comp = [], None
    for line in text.splitlines():
        if line.startswith("== "):
            comp = component_of(line[3:].strip().split("/")[-1])
            continue
        kind = classify(line) if comp else None
        if kind:
            out.append(Finding(comp, kind, line.strip()[-240:], "logs"))
    return out


# ---------------- the playbook ----------------
def playbook(ns: str) -> list[tuple[str, str]]:
    """(key, shell command) in the order the agent runs them. Read-only: nothing here changes the cluster."""
    grep = "error|fail|refused|denied|unauthori|not authori|panic|fatal|timeout|no such host|invalid|cannot"
    return [
        ("pods", f"kubectl get pods -n {ns} -o wide"),
        ("events", f"kubectl get events -n {ns} --sort-by=.lastTimestamp | tail -n 40"),
        ("logs", f"for p in $(kubectl get pods -n {ns} -o name); do echo '== '$p; "
                 f"kubectl logs $p -n {ns} --all-containers --tail=200 2>&1 | grep -iE '{grep}' | tail -n 4; done"),
    ]


def collect(ns: str, outputs: dict[str, str]) -> Evidence:
    ev = Evidence(namespace=ns, raw=outputs)
    ev.pods = parse_pods(outputs.get("pods", ""))
    ev.findings += [Finding(p.component, "unhealthy", f"{p.name} {p.ready} {p.status} restarts={p.restarts}", "pods")
                    for p in ev.pods if not p.healthy]
    ev.findings += parse_events(outputs.get("events", ""), ev.components)
    ev.findings += parse_log_scan(outputs.get("logs", ""))
    return ev


def data_store_of(component: str, components: set[str]) -> str | None:
    """The database that belongs to an application component, by naming convention: geo -> mongodb-geo."""
    for c in components:
        if c != component and DB_HINT.search(c) and re.search(rf"(^|-){re.escape(component)}($|-)", c):
            return c
    return None
