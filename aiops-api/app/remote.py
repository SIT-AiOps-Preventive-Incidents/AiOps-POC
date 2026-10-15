"""Connect a server from the platform.

The user gives an address, a user name and a password or key, once. AIOps then:
  1. signs in with it over SSH (AIOps connects out, so the server never has to reach AIOps),
  2. opens a data channel on that connection: the server's 127.0.0.1:18080 / :14318 lead to AIOps' API / OTLP,
  3. adds the platform key to the server, limited to opening exactly those two loopback ports (no shell),
     and runs the normal agent installer through the channel,
  4. forgets the password or key and keeps the channel open with the platform key, reconnecting by itself.

The server's host key is remembered on first contact and checked on every reconnect.
"""
import asyncio
import os
import shlex
import time
import traceback
import uuid

from . import db, repo

PORT_API, PORT_OTLP = 18080, 14318
API_TARGET = ("127.0.0.1", 8080)
OTLP_TARGET = (os.environ.get("OTLP_HOST", "otel-collector"), 4318)
KEY_PATH = os.environ.get("SSH_KEY_PATH", "/data/ssh/platform_ed25519")
RETRY_S = 10
STEPS = [("connect", "Sign in over SSH"), ("channel", "Open the data channel"), ("install", "Install the agent"),
         ("link", "Keep the channel open with the platform key"), ("data", "First data from the server")]
_jobs: dict[str, dict] = {}
_links: dict[str, dict] = {}


# ---------------- pure helpers ----------------
def tunnel_line(pub: str) -> str:
    kind, b64 = pub.split()[:2]
    return (f'restrict,port-forwarding,permitlisten="127.0.0.1:{PORT_API}",permitlisten="127.0.0.1:{PORT_OTLP}",'
            f'command="/bin/false" {kind} {b64} aiops-platform')


def setup_script(name: str, pub: str, ebpf: bool = True) -> str:
    q = shlex.quote
    b64 = pub.split()[1]
    api, otlp = f"http://127.0.0.1:{PORT_API}", f"http://127.0.0.1:{PORT_OTLP}"
    return "\n".join([
        "set -e",
        "umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys",
        f"grep -qF {b64} ~/.ssh/authorized_keys || echo {q(tunnel_line(pub))} >> ~/.ssh/authorized_keys",
        "echo 'platform key added (it can only open the AIOps data channel)'",
        f"curl -fsSL {api}/install/agent.sh | AIOPS_HOST_NAME={q(name)} AIOPS_API={api} AIOPS_OTLP={otlp}"
        f"{' AIOPS_EBPF=0' if not ebpf else ''} sh", ""])


def new_job(name: str) -> dict:
    return {"id": uuid.uuid4().hex[:12], "name": name, "state": "running", "error": None, "started_at": time.time(),
            "steps": [{"key": k, "label": label, "state": "pending"} for k, label in STEPS], "log": []}


def step(job: dict, key: str):
    """Finish the running step and start `key`."""
    for s in job["steps"]:
        if s["state"] == "running":
            s["state"] = "done"
        if s["key"] == key:
            s["state"] = "running"
            return


def fail(job: dict, why: str):
    for s in job["steps"]:
        if s["state"] == "running":
            s["state"] = "failed"
    job.update(state="failed", error=why)


def finish(job: dict):
    for s in job["steps"]:
        if s["state"] == "running":
            s["state"] = "done"
    job["state"] = "done"


def reason(e: BaseException) -> str:
    text = f"{type(e).__name__}: {e}"
    if "Permission denied" in text or "PermissionDenied" in text:
        return "The server did not accept that password or key for this user."
    if isinstance(e, (TimeoutError, asyncio.TimeoutError, ConnectionRefusedError, OSError)) and "forward" not in text:
        return f"Could not reach the server over SSH ({type(e).__name__}). Check the address and port."
    if "forward" in text or "listen" in text:
        return (f"The server would not open the data channel (ports {PORT_API}/{PORT_OTLP} on its loopback): {e}. "
                "Another program may be using them, or SSH port forwarding is turned off (AllowTcpForwarding).")
    return text


# ---------------- platform key ----------------
def platform_key():
    import asyncssh
    if not os.path.exists(KEY_PATH):
        os.makedirs(os.path.dirname(KEY_PATH), mode=0o700, exist_ok=True)
        k = asyncssh.generate_private_key("ssh-ed25519", comment="aiops-platform")
        k.write_private_key(KEY_PATH)
        os.chmod(KEY_PATH, 0o600)
    return asyncssh.read_private_key(KEY_PATH)


def platform_public() -> str:
    return platform_key().export_public_key().decode().strip()


async def _forwards(conn):
    await conn.forward_remote_port("127.0.0.1", PORT_API, *API_TARGET)
    await conn.forward_remote_port("127.0.0.1", PORT_OTLP, *OTLP_TARGET)


# ---------------- connect job ----------------
def start(body) -> dict:
    job = new_job(body.name)
    _jobs[job["id"]] = job
    if len(_jobs) > 30:
        for k in list(_jobs)[:-30]:
            _jobs.pop(k, None)
    asyncio.create_task(_run(job, body))
    return job


def get_job(jid: str) -> dict | None:
    return _jobs.get(jid)


async def _run(job: dict, body):
    import asyncssh
    log = job["log"]
    secret = {"password": body.password} if body.password else {}
    try:
        if body.private_key:
            secret["client_keys"] = [asyncssh.import_private_key(body.private_key, body.passphrase or None)]
        step(job, "connect")
        await stop_link(body.name)                       # an older channel would hold the ports
        conn = await asyncio.wait_for(asyncssh.connect(body.address, port=body.port, username=body.user,
                                                       known_hosts=None, agent_path=None, **secret), 20)
        async with conn:
            host_key = conn.get_server_host_key().export_public_key().decode().strip()
            log.append(f"signed in to {body.user}@{body.address} - server key {host_key.split()[0]} "
                       f"{conn.get_server_host_key().get_fingerprint()}")
            step(job, "channel")
            await _forwards(conn)
            log.append(f"server 127.0.0.1:{PORT_API} -> AIOps API, 127.0.0.1:{PORT_OTLP} -> AIOps OTLP")
            step(job, "install")
            proc = await conn.create_process("sh -s", stderr=asyncssh.STDOUT)
            proc.stdin.write(setup_script(body.name, platform_public(), body.ebpf))
            proc.stdin.write_eof()
            async for line in proc.stdout:
                log.append(line.rstrip())
            res = await proc.wait()
            if res.exit_status != 0:
                raise RuntimeError(f"the installer stopped with exit code {res.exit_status} (see the log)")
        secret.clear()                                   # the user's password / key is not kept
        step(job, "link")
        repo.save_ssh_link(body.name, body.address, body.port, body.user, host_key)
        ensure_link(body.name)
        for _ in range(30):
            if _links.get(body.name, {}).get("state") == "connected":
                break
            await asyncio.sleep(1)
        else:
            raise RuntimeError(_links.get(body.name, {}).get("error") or "the platform key could not open the channel")
        log.append("channel kept open with the platform key")
        step(job, "data")
        for _ in range(45):
            h = repo.host(body.name)
            if h and h.get("last_inventory_at"):
                break
            await asyncio.sleep(2)
        finish(job)
    except Exception as e:
        traceback.print_exc()
        fail(job, reason(e))
    finally:
        secret.clear()


# ---------------- persistent channel ----------------
def link_state(name: str) -> dict:
    s = _links.get(name) or {}
    return {"name": name, "state": s.get("state", "stopped"), "since": s.get("since"), "error": s.get("error")}


def ensure_link(name: str):
    cur = _links.get(name)
    if cur and not cur["task"].done():
        return
    _links[name] = {"state": "connecting", "since": time.time(), "error": None, "task": None}
    _links[name]["task"] = asyncio.create_task(_keep(name))


async def stop_link(name: str):
    cur = _links.pop(name, None)
    if cur and cur.get("task"):
        cur["task"].cancel()
        await asyncio.sleep(0.5)


async def _keep(name: str):
    import asyncssh
    while True:
        row = repo.ssh_link(name)
        st = _links.get(name)
        if not row or st is None:
            return
        try:
            trusted = asyncssh.import_public_key(row["host_key"])
            async with asyncssh.connect(row["address"], port=row["port"], username=row["username"],
                                        client_keys=[platform_key()], known_hosts=([trusted], [], []),
                                        agent_path=None, keepalive_interval=30, keepalive_count_max=3) as conn:
                await _forwards(conn)
                st.update(state="connected", since=time.time(), error=None)
                db.ex("UPDATE ssh_links SET last_connected_at=now() WHERE host_name=%s", (name,))
                await conn.wait_closed()
            st.update(state="reconnecting", since=time.time(), error="connection closed")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            st.update(state="reconnecting", since=time.time(), error=reason(e))
        await asyncio.sleep(RETRY_S)


def start_all():
    for r in repo.ssh_links():
        ensure_link(r["host_name"])
