"""Fleet onboarding help: of the machines AIOps found but does not monitor, which to connect first.

A team with a hundred VMs cannot wire them all at once. This ranks the unmonitored ones by how much AIOps
would learn from them: a machine already talking to a service we monitor, or sitting on a network where
something is going wrong, is worth far more than an idle box nobody calls. Each pick carries a plain reason,
so the person (or the agent) can act on it.
"""
from . import netseg


def recommend(segments: list[dict], neighbors: list[dict], hosts: list[dict], problem_hosts: set[str]) -> list[dict]:
    items = netseg._items(segments, neighbors, hosts)
    monitored_cidrs = {i["cidr"] for i in items if i["aiops_host"]}
    problem_cidrs = {i["cidr"] for i in items if i["aiops_host"] in problem_hosts}
    out = []
    for i in items:
        if i["aiops_host"] or i["kind"] in ("gateway", "random MAC"):   # ours, the router, or an anonymous address
            continue
        score, reasons = 0, []
        if i["talks_with"]:
            score += 3
            reasons.append(f"talks to {', '.join(i['talks_with'][:2])}, which you monitor")
        if i["cidr"] in problem_cidrs:
            score += 2
            reasons.append("on a network with an active problem")
        elif i["cidr"] in monitored_cidrs:
            score += 1
            reasons.append("on a network you already monitor")
        if i["name"]:
            score += 1
            reasons.append("has a hostname")
        if score <= 0:
            continue
        out.append({"ip": i["ip"], "name": i["name"] or i["ip"], "cidr": i["cidr"], "vendor": i["vendor"],
                    "score": score, "reasons": reasons})
    out.sort(key=lambda r: (-r["score"], r["name"]))
    return out


def neighbours(host: str, segments: list[dict], hosts: list[dict]) -> list[dict]:
    """The other machines AIOps monitors on the same network(s) as `host` - the first ring of blast radius when
    something goes wrong, and the set the agent should check for a shared cause (e.g. a busy hypervisor node)."""
    mine = {s["cidr"] for s in segments if s["host"] == host}
    out = []
    for h in hosts:
        if h["name"] == host:
            continue
        shared = sorted(mine & {s["cidr"] for s in segments if s["host"] == h["name"]})
        if shared:
            out.append({"host": h["name"], "owner": h.get("owner"), "networks": shared})
    return out
