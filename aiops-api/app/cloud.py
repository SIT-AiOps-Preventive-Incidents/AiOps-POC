"""Cloud inventory: read a customer's cloud account (read-only) and put every VM on the Fleet.

Most customers run on a cloud, not on a LAN we can hear. Inside a cloud tenant ARP shows only your own subnet and
the provider's switches are not yours to poll, so the source of truth for "which machines exist" is the provider's
own control-plane API. We read it with the narrowest read-only credential each provider offers, turn every
provider's answer into one instance shape, and then:

  diff     - what was added, removed or changed state since the last read (the change log on the Fleet)
  match    - which instances already run our agent (by private/public IP, then by name)
  verdict  - what the cloud's state and the agent's heartbeat mean together: a VM that is running in the console
             while its agent is silent is a different problem from a VM someone stopped.

Connectors
  proxmox    API token (PVEAuditor, pool-scoped) -> /cluster/resources + guest agent IPs   (GIST Starships Cloud)
  openstack  Keystone v3 application credential -> Nova /servers/detail     (also what most Thai IaaS run on)
  vcd        VMware Cloud Director API token -> /api/query?type=vm           (the other common Thai IaaS stack)
  cloudstack Apache CloudStack API key + secret, signed -> listVirtualMachines
  aws        access key with ec2:DescribeInstances, SigV4 signed
  azure      service principal with the Reader role -> ARM VMs, NICs, public IPs
  gcp        service account with roles/compute.viewer -> instances aggregatedList

Nothing here changes the cloud. Secrets are sealed (Fernet) before they reach the database and never come back out
through the API.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import xml.etree.ElementTree as ET

import httpx

TIMEOUT_S = 20


class CloudError(Exception):
    """A provider said no, or answered something we cannot read. The message is shown to the person."""


# ===================================================================== providers: what each needs
PROVIDERS = {
    "proxmox": {"label": "Proxmox VE (e.g. GIST Starships Cloud)", "config": ["url"], "optional": ["pool", "verify_tls"],
                "secret": ["token_id", "token_secret"],
                "role": "a Proxmox API token with the PVEAuditor role, limited to your resource pool"},
    "openstack": {"label": "OpenStack", "config": ["auth_url"], "optional": ["region", "interface", "verify_tls"],
                  "secret": ["application_credential_id", "application_credential_secret"],
                  "role": "a Keystone application credential with the reader role on the project"},
    "vcd": {"label": "VMware Cloud Director", "config": ["url", "org"], "optional": ["verify_tls"],
            "secret": ["api_token"], "role": "an API token of a user with a read-only organization role"},
    "cloudstack": {"label": "Apache CloudStack", "config": ["url"], "optional": ["verify_tls"],
                   "secret": ["api_key", "secret_key"], "role": "API keys of a read-only domain user"},
    "aws": {"label": "Amazon Web Services", "config": ["region"], "optional": [],
            "secret": ["access_key_id", "secret_access_key"], "role": "an IAM user or role allowed only ec2:DescribeInstances"},
    "azure": {"label": "Microsoft Azure", "config": ["tenant_id", "subscription_id"], "optional": [],
              "secret": ["client_id", "client_secret"], "role": "a service principal with the Reader role on the subscription"},
    "gcp": {"label": "Google Cloud", "config": ["project"], "optional": [],
            "secret": ["service_account_json"], "role": "a service account with roles/compute.viewer"},
}
URL_KEYS = ("auth_url", "url")


def validate(provider: str, config: dict, secret: dict) -> list[str]:
    spec = PROVIDERS.get(provider)
    if not spec:
        return [f"unknown provider '{provider}'"]
    errs = []
    for k in spec["config"]:
        if not str(config.get(k) or "").strip():
            errs.append(f"{k} is required")
    for k in URL_KEYS:
        if k in config and config[k] and not str(config[k]).startswith("https://"):
            errs.append(f"{k} must be an https:// address (credentials are sent to it)")
    if any(not str(secret.get(k) or "").strip() for k in spec["secret"]):
        errs.append(f"credential needs {', '.join(spec['secret'])} ({spec['role']})")
    return errs


# ===================================================================== normalising: one instance shape
STATE = {
    # openstack
    "ACTIVE": "running", "SHUTOFF": "stopped", "STOPPED": "stopped", "SUSPENDED": "stopped", "PAUSED": "stopped",
    "SHELVED": "stopped", "SHELVED_OFFLOADED": "stopped", "BUILD": "starting", "REBOOT": "starting",
    "HARD_REBOOT": "starting", "ERROR": "error", "DELETED": "deleted", "SOFT_DELETED": "deleted",
    # vcd
    "POWERED_ON": "running", "POWERED_OFF": "stopped", "PARTIALLY_POWERED_OFF": "stopped", "UNRESOLVED": "starting",
    "FAILED_CREATION": "error",
    # cloudstack / aws / gcp
    "Running": "running", "Stopped": "stopped", "Starting": "starting", "Stopping": "stopping", "Error": "error",
    "Destroyed": "deleted", "Expunging": "deleted",
    "running": "running", "stopped": "stopped", "pending": "starting", "stopping": "stopping",
    "shutting-down": "stopping", "terminated": "deleted",
    "RUNNING": "running", "TERMINATED": "stopped", "STAGING": "starting", "PROVISIONING": "starting",
    "STOPPING": "stopping", "SUSPENDING": "stopping", "REPAIRING": "error",
}


def _state(raw) -> str:
    return STATE.get(str(raw or ""), "unknown")


def _inst(iid, name, state, private, public, networks, zone, size, created, tags) -> dict:
    return {"instance_id": str(iid), "name": name or str(iid), "state": state,
            "private_ips": [ip for ip in private if ip], "public_ips": [ip for ip in public if ip],
            "networks": sorted({n for n in networks if n}), "zone": zone, "size": size, "created_at": created,
            "tags": tags or {}}


def _split_ips(ips) -> tuple[list, list]:
    import ipaddress
    private, public = [], []
    for ip in ips:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if a.is_loopback or a.is_link_local:
            continue
        (private if a.is_private else public).append(ip)
    return private, public


def _pve_bridges(cfg: dict) -> list[str]:
    import re
    out = []
    for k in sorted(cfg):
        if re.fullmatch(r"net\d+", k):
            parts = dict(p.split("=", 1) for p in str(cfg[k]).split(",") if "=" in p)
            if parts.get("bridge"):
                out.append(parts["bridge"] + (f".{parts['tag']}" if parts.get("tag") else ""))
    return out


def parse_proxmox(resources: dict, nets: dict, configs: dict, pool: str | None = None) -> list[dict]:
    """VMs (and containers) from /cluster/resources. IPs come from the QEMU guest agent when it answers, else from
    the cloud-init ipconfigN in the VM config. Public or private is decided by the address range."""
    import re
    out = []
    for r in resources.get("data", []):
        if r.get("type") not in ("qemu", "lxc") or (pool and r.get("pool") != pool):
            continue
        vmid, cfg = r["vmid"], configs.get(r["vmid"]) or {}
        ips = [a["ip-address"] for itf in (nets.get(vmid) or {}).get("result", [])
               for a in itf.get("ip-addresses") or [] if a.get("ip-address-type") == "ipv4"]
        if not ips:
            ips = [m.group(1) for k, v in sorted(cfg.items()) if re.fullmatch(r"ipconfig\d+", k)
                   for m in [re.search(r"ip=([0-9.]+)", str(v))] if m]
        private, public = _split_ips(ips)
        gb = round((r.get("maxmem") or 0) / 2**30)
        size = f"{r['maxcpu']} vCPU / {gb} GB" if r.get("maxcpu") else None
        tags = {k: v for k, v in (("pool", r.get("pool")), ("tags", r.get("tags"))) if v}
        out.append(_inst(vmid, r.get("name"), {"running": "running", "stopped": "stopped", "paused": "stopped"}
                         .get(r.get("status"), "unknown"), private, public, _pve_bridges(cfg), r.get("node"), size, None, tags))
    return out


def parse_openstack(body: dict) -> list[dict]:
    out = []
    for s in body.get("servers", []):
        private, public = [], []
        for net, addrs in (s.get("addresses") or {}).items():
            for a in addrs:
                (public if a.get("OS-EXT-IPS:type") == "floating" else private).append(a.get("addr"))
        fl = s.get("flavor") or {}
        out.append(_inst(s["id"], s.get("name"), _state(s.get("status")), private, public,
                         list((s.get("addresses") or {}).keys()), s.get("OS-EXT-AZ:availability_zone"),
                         fl.get("original_name") or fl.get("id"), s.get("created"), s.get("metadata")))
    return out


def parse_vcd(body: dict) -> list[dict]:
    out = []
    for r in body.get("record", []):
        if r.get("isVAppTemplate"):
            continue
        iid = (r.get("href") or "").rstrip("/").rsplit("/", 1)[-1]
        tags = {k: v for k, v in (("vapp", r.get("containerName")), ("os", r.get("guestOs"))) if v}
        out.append(_inst(iid, r.get("name"), _state(r.get("status")), [r.get("ipAddress")], [],
                         [r.get("networkName")], r.get("vdcName"), None, r.get("dateCreated"), tags))
    return out


def parse_cloudstack(body: dict) -> list[dict]:
    out = []
    for v in (body.get("listvirtualmachinesresponse") or {}).get("virtualmachine", []):
        nics = v.get("nic") or []
        out.append(_inst(v["id"], v.get("displayname") or v.get("name"), _state(v.get("state")),
                         [n.get("ipaddress") for n in nics], [v.get("publicip")], [n.get("networkname") for n in nics],
                         v.get("zonename"), v.get("serviceofferingname"), v.get("created"),
                         {t["key"]: t.get("value") for t in v.get("tags") or []}))
    return out


def _x(el, path, ns):
    found = el.find(path, ns)
    return found.text if found is not None else None


def parse_ec2(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    ns = {"e": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {"e": ""}
    p = (lambda s: "/".join(f"e:{x}" for x in s.split("/"))) if ns["e"] else (lambda s: s)
    out = []
    for it in root.iterfind(p("reservationSet/item/instancesSet/item"), ns):
        tags = {_x(t, p("key"), ns): _x(t, p("value"), ns) for t in it.iterfind(p("tagSet/item"), ns)}
        vpc, subnet = _x(it, p("vpcId"), ns), _x(it, p("subnetId"), ns)
        iid = _x(it, p("instanceId"), ns)
        out.append(_inst(iid, tags.get("Name") or iid, _state(_x(it, p("instanceState/name"), ns)),
                         [_x(it, p("privateIpAddress"), ns)], [_x(it, p("ipAddress"), ns)],
                         [f"{vpc}/{subnet}" if vpc and subnet else vpc], _x(it, p("placement/availabilityZone"), ns),
                         _x(it, p("instanceType"), ns), _x(it, p("launchTime"), ns), tags))
    return out


def _last(path: str | None) -> str | None:
    return path.rstrip("/").rsplit("/", 1)[-1] if path else None


def parse_azure(vms: dict, nics: dict, pips: dict) -> list[dict]:
    nic_by_id = {n["id"].lower(): n for n in nics.get("value", [])}
    pip_by_id = {p["id"].lower(): p for p in pips.get("value", [])}
    out = []
    for v in vms.get("value", []):
        props = v.get("properties") or {}
        power = next((s["code"].split("/", 1)[1] for s in (props.get("instanceView") or {}).get("statuses", [])
                      if s.get("code", "").startswith("PowerState/")), None)
        state = {"running": "running", "deallocated": "stopped", "stopped": "stopped", "starting": "starting",
                 "stopping": "stopping", "deallocating": "stopping"}.get(power, "unknown")
        private, public, nets = [], [], []
        for ref in (props.get("networkProfile") or {}).get("networkInterfaces", []):
            nic = nic_by_id.get(ref["id"].lower()) or {}
            for cfg in (nic.get("properties") or {}).get("ipConfigurations", []):
                cp = cfg.get("properties") or {}
                private.append(cp.get("privateIPAddress"))
                sub = (cp.get("subnet") or {}).get("id", "")
                if "/virtualNetworks/" in sub:
                    vnet, _, sn = sub.split("/virtualNetworks/", 1)[1].partition("/subnets/")
                    nets.append(f"{vnet}/{sn}" if sn else vnet)
                pip = pip_by_id.get(((cp.get("publicIPAddress") or {}).get("id") or "").lower())
                if pip:
                    public.append((pip.get("properties") or {}).get("ipAddress"))
        zone = v.get("location") + (f"-{v['zones'][0]}" if v.get("zones") else "")
        out.append(_inst(v["id"], v.get("name"), state, private, public, nets, zone,
                         (props.get("hardwareProfile") or {}).get("vmSize"), props.get("timeCreated"), v.get("tags")))
    return out


def parse_gcp(body: dict) -> list[dict]:
    out = []
    for scope in (body.get("items") or {}).values():
        for i in scope.get("instances", []):
            nis = i.get("networkInterfaces") or []
            out.append(_inst(i["id"], i.get("name"), _state(i.get("status")), [n.get("networkIP") for n in nis],
                             [a.get("natIP") for n in nis for a in n.get("accessConfigs") or []],
                             [_last(n.get("network")) for n in nis], _last(i.get("zone")), _last(i.get("machineType")),
                             i.get("creationTimestamp"), i.get("labels")))
    return out


# ===================================================================== what changed, who runs our agent, what it means
def diff(before: dict[str, dict], now: list[dict]) -> dict:
    cur = {i["instance_id"]: i for i in now}
    added = [i for k, i in cur.items() if k not in before]
    removed = [i for k, i in before.items() if k not in cur]
    changed = [{"instance_id": k, "name": i["name"], "from": before[k]["state"], "to": i["state"]}
               for k, i in cur.items() if k in before and before[k]["state"] != i["state"]]
    return {"added": added, "removed": removed, "changed": changed}


def match(instances: list[dict], hosts: list[dict]) -> list[dict]:
    by_ip = {ip: h for h in hosts for ip in h.get("ip_addresses") or []}
    by_name = {h["name"].lower(): h for h in hosts}
    out = []
    for i in instances:
        h = next((by_ip[ip] for ip in i.get("private_ips", []) + i.get("public_ips", []) if ip in by_ip), None)
        h = h or by_name.get((i.get("name") or "").lower())
        out.append({**i, "aiops_host": h["name"] if h else None, "host_status": h.get("status") if h else None})
    return out


VERDICTS = {
    "ok": "Running, and our agent is reporting.",
    "agent_silent": "Running in the cloud, but our agent stopped reporting: look inside the machine.",
    "stopped_in_cloud": "Stopped in the cloud console: start it there, nothing is wrong inside.",
    "not_monitored": "Found in the cloud account, not monitored yet.",
    "gone": "Deleted from the cloud account.",
    "transition": "Starting or stopping in the cloud.",
    "error": "The cloud reports an error state for this machine.",
}


def verdict(cloud_state: str, host_status: str | None) -> dict:
    if cloud_state == "deleted":
        code = "gone"
    elif cloud_state == "error":
        code = "error"
    elif cloud_state in ("starting", "stopping"):
        code = "transition"
    elif host_status is None:
        code = "not_monitored"
    elif cloud_state == "stopped":
        code = "stopped_in_cloud"
    elif host_status in ("down", "offline", "silent"):
        code = "agent_silent"
    else:
        code = "ok"
    return {"code": code, "text": VERDICTS[code]}


def graph(accounts: list[dict], instances: list[dict]) -> dict:
    """Fleet-map nodes for the cloud side: account -> its networks (hubs) -> instances. An instance that already
    runs our agent is not drawn twice: its agent host node is linked to the cloud network instead."""
    names = {a["id"]: a["name"] for a in accounts}
    provider = {a["id"]: a["provider"] for a in accounts}
    nodes, links, matched = [], [], {}
    for a in accounts:
        nodes.append({"id": f"cloud:{a['id']}", "kind": "cloud", "label": a["name"], "provider": a["provider"],
                      "status": "ok" if a.get("status") == "ok" else a.get("status") or "new"})
        links.append({"source": f"cloud:{a['id']}", "target": "internet", "kind": "cable"})
    hubs = set()
    for i in instances:
        acc = names.get(i["account_id"])
        if acc is None or i.get("state") == "deleted":
            continue
        hub = f"hub:{acc} / {(i.get('networks') or ['(no network)'])[0]}"
        if hub not in hubs:
            hubs.add(hub)
            nodes.append({"id": hub, "kind": "hub", "label": hub[4:], "status": "ok", "cloud": True})
            links.append({"source": hub, "target": f"cloud:{i['account_id']}", "kind": "cable"})
        v = verdict(i["state"], i.get("host_status"))
        if i.get("aiops_host"):
            links.append({"source": f"host:{i['aiops_host']}", "target": hub, "kind": "cable"})
            matched[i["aiops_host"]] = {"account": acc, "state": i["state"], "verdict": v["code"]}
            continue
        ip = (i.get("private_ips") or i.get("public_ips") or [None])[0]
        nodes.append({"id": f"cloud:{i['account_id']}:{i['instance_id']}", "kind": "cloud instance",
                      "label": i["name"], "status": i["state"], "ip": ip, "public_ip": (i.get("public_ips") or [None])[0],
                      "zone": i.get("zone"), "size": i.get("size"), "provider": provider[i["account_id"]],
                      "account": acc, "verdict": v})
        links.append({"source": f"cloud:{i['account_id']}:{i['instance_id']}", "target": hub, "kind": "cable"})
    return {"nodes": nodes, "links": links, "matched": matched}


def merge(base: dict, cg: dict) -> dict:
    """Add the cloud side to the Fleet graph: no node or link twice, agent hosts tagged with what their cloud says."""
    seen = {n["id"] for n in base["nodes"]}
    nodes = [({**n, "cloud": cg["matched"][n["id"][5:]]} if n["id"].startswith("host:") and n["id"][5:] in cg["matched"] else n)
             for n in base["nodes"]]
    nodes += [n for n in cg["nodes"] if n["id"] not in seen]
    keys = {(l["source"], l["target"], l["kind"]) for l in base["links"]}
    links = base["links"] + [l for l in cg["links"] if (l["source"], l["target"], l["kind"]) not in keys]
    return {**base, "nodes": nodes, "links": links}


# ===================================================================== secrets: sealed at rest, never returned
def _fernet():
    from cryptography.fernet import Fernet
    key = os.environ.get("AIOPS_SECRET_KEY")
    if not key:
        path = os.environ.get("AIOPS_SECRET_KEY_FILE", "/data/secret.key")
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(Fernet.generate_key())
        with open(path, "rb") as f:
            key = f.read().strip()
    return Fernet(key)


def seal(secret: dict) -> str:
    return _fernet().encrypt(json.dumps(secret).encode()).decode()


def unseal(blob: str) -> dict:
    return json.loads(_fernet().decrypt(blob.encode()))


def public(account: dict) -> dict:
    out = {k: v for k, v in account.items() if k != "secret"}
    out["has_secret"] = bool(account.get("secret"))
    out["provider_label"] = PROVIDERS.get(account.get("provider"), {}).get("label", account.get("provider"))
    return out


# ===================================================================== signing helpers
def sigv4_headers(method: str, url: str, *, region: str, service: str, access_key: str, secret_key: str,
                  amz_date: str | None = None, extra: dict | None = None, body: bytes = b"") -> dict:
    """AWS Signature Version 4 for a request with the parameters in the query string."""
    u = urllib.parse.urlsplit(url)
    amz_date = amz_date or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    day = amz_date[:8]
    headers = {**{k.lower(): v for k, v in (extra or {}).items()}, "host": u.netloc, "x-amz-date": amz_date}
    q = sorted(urllib.parse.parse_qsl(u.query, keep_blank_values=True))
    cq = "&".join(f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(v, safe='-_.~')}" for k, v in q)
    signed = ";".join(sorted(headers))
    ch = "".join(f"{k}:{headers[k].strip()}\n" for k in sorted(headers))
    creq = "\n".join([method, u.path or "/", cq, ch, signed, hashlib.sha256(body).hexdigest()])
    scope = f"{day}/{region}/{service}/aws4_request"
    sts = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(creq.encode()).hexdigest()])
    k = ("AWS4" + secret_key).encode()
    for part in (day, region, service, "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    out = {kk: v for kk, v in headers.items() if kk != "host"}
    out["Authorization"] = f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={signed}, Signature={sig}"
    return out


def _cloudstack_url(base: str, params: dict, api_key: str, secret_key: str) -> str:
    p = {**params, "apiKey": api_key, "response": "json"}
    query = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted(p.items(), key=lambda kv: kv[0].lower()))
    sig = base64.b64encode(hmac.new(secret_key.encode(), query.lower().encode(), hashlib.sha1).digest()).decode()
    return f"{base.rstrip('/')}/client/api?{query}&signature={urllib.parse.quote(sig, safe='')}"


def _gcp_assertion(sa: dict) -> str:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    now = int(time.time())
    b64 = lambda d: base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=")  # noqa: E731
    head = b64({"alg": "RS256", "typ": "JWT"}) + b"." + b64({
        "iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/compute.readonly",
        "aud": sa.get("token_uri", "https://oauth2.googleapis.com/token"), "iat": now, "exp": now + 600})
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = key.sign(head, padding.PKCS1v15(), hashes.SHA256())
    return (head + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()


# ===================================================================== fetch: one read-only pass per provider
def _check(r: httpx.Response, what: str):
    if r.status_code in (401, 403):
        raise CloudError(f"{what}: the provider rejected the credential (HTTP {r.status_code}). "
                         "Check it is valid and has read access.")
    if r.status_code >= 400:
        raise CloudError(f"{what}: HTTP {r.status_code} {r.text[:200]}")


async def fetch(provider: str, config: dict, secret: dict, transport: httpx.AsyncBaseTransport | None = None) -> list[dict]:
    """Read every instance the credential can see. Raises CloudError with a message a person can act on."""
    verify = config.get("verify_tls", True) not in (False, "false", "0", 0)
    async with httpx.AsyncClient(timeout=TIMEOUT_S, verify=verify, transport=transport, follow_redirects=True) as c:
        try:
            return await FETCHERS[provider](c, config, secret)
        except CloudError:
            raise
        except httpx.HTTPError as e:
            raise CloudError(f"could not reach the {PROVIDERS[provider]['label']} API: {type(e).__name__}: {e}") from e
        except (KeyError, ValueError, ET.ParseError) as e:
            raise CloudError(f"unexpected answer from the {PROVIDERS[provider]['label']} API: {type(e).__name__}: {e}") from e


async def _proxmox(c, cfg, sec):
    base = cfg["url"].rstrip("/") + "/api2/json"
    h = {"Authorization": f"PVEAPIToken={sec['token_id']}={sec['token_secret']}"}
    r = await c.get(base + "/cluster/resources", headers=h, params={"type": "vm"})
    _check(r, "Proxmox cluster resources")
    res = r.json()
    pool = cfg.get("pool") or None
    nets, configs = {}, {}
    for v in res.get("data", []):
        if v.get("type") != "qemu" or (pool and v.get("pool") != pool):
            continue
        node, vmid = v["node"], v["vmid"]
        cr = await c.get(f"{base}/nodes/{node}/qemu/{vmid}/config", headers=h)
        if cr.status_code == 200:
            configs[vmid] = cr.json().get("data") or {}
        if v.get("status") == "running":   # the guest agent only answers in a running VM that has it installed
            nr = await c.get(f"{base}/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces", headers=h)
            if nr.status_code == 200:
                nets[vmid] = nr.json().get("data") or {}
    return parse_proxmox(res, nets, configs, pool)


async def _openstack(c, cfg, sec):
    auth = {"auth": {"identity": {"methods": ["application_credential"], "application_credential": {
        "id": sec["application_credential_id"], "secret": sec["application_credential_secret"]}}}}
    r = await c.post(cfg["auth_url"].rstrip("/") + "/auth/tokens", json=auth)
    _check(r, "Keystone login")
    token = r.headers["X-Subject-Token"]
    iface, region = cfg.get("interface") or "public", cfg.get("region")
    compute = next((s for s in r.json()["token"]["catalog"] if s["type"] == "compute"), None)
    if not compute:
        raise CloudError("the credential's project has no compute (Nova) service in its catalog")
    eps = [e for e in compute["endpoints"] if e["interface"] == iface and (not region or e.get("region") == region)]
    if not eps:
        raise CloudError(f"no {iface} compute endpoint" + (f" in region {region}" if region else ""))
    servers, url = [], eps[0]["url"].rstrip("/") + "/servers/detail"
    params = {"limit": 500}
    while url:
        r = await c.get(url, headers={"X-Auth-Token": token}, params=params)
        _check(r, "Nova servers")
        body = r.json()
        servers += body.get("servers", [])
        nxt = next((l["href"] for l in body.get("servers_links", []) if l.get("rel") == "next"), None)
        url, params = nxt, None
    return parse_openstack({"servers": servers})


async def _vcd(c, cfg, sec):
    base, org = cfg["url"].rstrip("/"), cfg["org"]
    path = "/oauth/provider/token" if org.lower() == "system" else f"/oauth/tenant/{org}/token"
    r = await c.post(base + path, data={"grant_type": "refresh_token", "refresh_token": sec["api_token"]},
                     headers={"Accept": "application/json"})
    _check(r, "Cloud Director login")
    bearer = r.json()["access_token"]
    records, page = [], 1
    while True:
        r = await c.get(base + "/api/query", headers={"Authorization": f"Bearer {bearer}",
                                                      "Accept": "application/*+json;version=36.0"},
                        params={"type": "vm", "format": "records", "pageSize": 128, "page": page})
        _check(r, "Cloud Director VM query")
        body = r.json()
        records += body.get("record", [])
        if len(records) >= int(body.get("total") or len(records)) or not body.get("record"):
            break
        page += 1
    return parse_vcd({"record": records})


async def _cloudstack(c, cfg, sec):
    r = await c.get(_cloudstack_url(cfg["url"], {"command": "listVirtualMachines", "listall": "true"},
                                    sec["api_key"], sec["secret_key"]))
    _check(r, "CloudStack listVirtualMachines")
    return parse_cloudstack(r.json())


async def _aws(c, cfg, sec):
    region = cfg["region"]
    out, token = [], None
    while True:
        q = {"Action": "DescribeInstances", "Version": "2016-11-15", "MaxResults": "500"}
        if token:
            q["NextToken"] = token
        url = f"https://ec2.{region}.amazonaws.com/?" + urllib.parse.urlencode(q)
        h = sigv4_headers("GET", url, region=region, service="ec2", access_key=sec["access_key_id"],
                          secret_key=sec["secret_access_key"])
        if sec.get("session_token"):
            h["X-Amz-Security-Token"] = sec["session_token"]
        r = await c.get(url, headers=h)
        _check(r, "EC2 DescribeInstances")
        out += parse_ec2(r.text)
        root = ET.fromstring(r.text)
        nt = next((e.text for e in root.iter() if e.tag.endswith("nextToken")), None)
        if not nt:
            return out
        token = nt


async def _azure(c, cfg, sec):
    r = await c.post(f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token",
                     data={"grant_type": "client_credentials", "client_id": sec["client_id"],
                           "client_secret": sec["client_secret"], "scope": "https://management.azure.com/.default"})
    _check(r, "Azure login")
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    sub = f"https://management.azure.com/subscriptions/{cfg['subscription_id']}/providers"

    async def all_pages(url):
        items = []
        while url:
            rr = await c.get(url, headers=h)
            _check(rr, "Azure Resource Manager")
            body = rr.json()
            items += body.get("value", [])
            url = body.get("nextLink")
        return {"value": items}
    vms = await all_pages(f"{sub}/Microsoft.Compute/virtualMachines?api-version=2024-07-01&statusOnly=true")
    nics = await all_pages(f"{sub}/Microsoft.Network/networkInterfaces?api-version=2024-05-01")
    pips = await all_pages(f"{sub}/Microsoft.Network/publicIPAddresses?api-version=2024-05-01")
    return parse_azure(vms, nics, pips)


async def _gcp(c, cfg, sec):
    sa = sec["service_account_json"]
    sa = json.loads(sa) if isinstance(sa, str) else sa
    r = await c.post(sa.get("token_uri", "https://oauth2.googleapis.com/token"),
                     data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": _gcp_assertion(sa)})
    _check(r, "Google login")
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    items, token = {}, None
    while True:
        params = {"maxResults": 500, **({"pageToken": token} if token else {})}
        rr = await c.get(f"https://compute.googleapis.com/compute/v1/projects/{cfg['project']}/aggregated/instances",
                         headers=h, params=params)
        _check(rr, "Compute Engine instances")
        body = rr.json()
        for k, v in (body.get("items") or {}).items():
            items.setdefault(k, {"instances": []})["instances"] += v.get("instances", [])
        token = body.get("nextPageToken")
        if not token:
            return parse_gcp({"items": items})


FETCHERS = {"proxmox": _proxmox, "openstack": _openstack, "vcd": _vcd, "cloudstack": _cloudstack, "aws": _aws, "azure": _azure, "gcp": _gcp}


def iso_to_epoch(s: str | None) -> float | None:
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        if len(s) > 5 and s[-5] in "+-" and s[-3] != ":":   # +0700 -> +07:00
            s = s[:-2] + ":" + s[-2:]
        return dt.datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None
