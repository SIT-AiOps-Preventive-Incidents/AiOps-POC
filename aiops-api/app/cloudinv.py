"""Cloud inventory storage and the sync loop. The provider logic (parsing, diffing, matching) lives in cloud.py."""
import asyncio
import logging

from . import cloud, db, health

log = logging.getLogger("aiops.cloud")
_COLS = "id, provider, name, config, secret, status, last_sync_at, last_error, created_at"


def accounts() -> list[dict]:
    return db.q(f"""SELECT {_COLS}, (SELECT count(*) FROM cloud_instances i WHERE i.account_id=a.id AND gone_at IS NULL)
                    AS instance_count FROM cloud_accounts a ORDER BY name""")


def get(account_id: int) -> dict | None:
    return db.one(f"""SELECT {_COLS}, (SELECT count(*) FROM cloud_instances i WHERE i.account_id=a.id AND gone_at IS NULL)
                      AS instance_count FROM cloud_accounts a WHERE id=%s""", (account_id,))


def create(provider: str, name: str, config: dict, secret: dict) -> dict:
    return db.one(f"""INSERT INTO cloud_accounts(provider, name, config, secret) VALUES (%s,%s,%s,%s)
                      RETURNING {_COLS}""", (provider, name, db.J(config), cloud.seal(secret)))


def delete(account_id: int) -> None:
    db.ex("DELETE FROM cloud_accounts WHERE id=%s", (account_id,))


def _current(account_id: int) -> dict[str, dict]:
    rows = db.q("SELECT instance_id, name, state FROM cloud_instances WHERE account_id=%s AND gone_at IS NULL", (account_id,))
    return {r["instance_id"]: r for r in rows}


def save_sync(account_id: int, instances: list[dict]) -> dict:
    """Store one read of the account: upsert what is listed, mark the rest gone, log the changes."""
    d = cloud.diff(_current(account_id), instances)
    with db.tx() as c:
        for i in instances:
            c.execute("""INSERT INTO cloud_instances(account_id, instance_id, name, state, private_ips, public_ips, networks,
                         zone, size, created_at, tags) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                         ON CONFLICT (account_id, instance_id) DO UPDATE SET name=EXCLUDED.name, state=EXCLUDED.state,
                         private_ips=EXCLUDED.private_ips, public_ips=EXCLUDED.public_ips, networks=EXCLUDED.networks,
                         zone=EXCLUDED.zone, size=EXCLUDED.size, tags=EXCLUDED.tags, last_seen=now(), gone_at=NULL""",
                      (account_id, i["instance_id"], i["name"], i["state"], i["private_ips"], i["public_ips"],
                       i["networks"], i.get("zone"), i.get("size"), db.T(cloud.iso_to_epoch(i.get("created_at"))),
                       db.J(i.get("tags") or {})))
        for i in d["removed"]:
            c.execute("UPDATE cloud_instances SET gone_at=now() WHERE account_id=%s AND instance_id=%s",
                      (account_id, i["instance_id"]))
        events = ([("added", i["instance_id"], i["name"], i["state"]) for i in d["added"]] +
                  [("removed", i["instance_id"], i["name"], "no longer listed") for i in d["removed"]] +
                  [("state", x["instance_id"], x["name"], f"{x['from']} -> {x['to']}") for x in d["changed"]])
        for kind, iid, name, detail in events:
            c.execute("INSERT INTO cloud_events(account_id, kind, instance_id, name, detail) VALUES (%s,%s,%s,%s,%s)",
                      (account_id, kind, iid, name, detail))
        c.execute("UPDATE cloud_accounts SET status='ok', last_sync_at=now(), last_error=NULL WHERE id=%s", (account_id,))
    return d


async def sync(account_id: int) -> dict:
    acc = get(account_id)
    try:
        instances = await cloud.fetch(acc["provider"], acc["config"], cloud.unseal(acc["secret"]))
    except cloud.CloudError as e:
        db.ex("UPDATE cloud_accounts SET status='error', last_error=%s WHERE id=%s", (str(e)[:500], account_id))
        raise
    d = save_sync(account_id, instances)
    return {"instances": len(instances), "added": len(d["added"]), "removed": len(d["removed"]), "changed": len(d["changed"])}


async def instances(account_id: int | None = None) -> list[dict]:
    rows = db.q("""SELECT i.*, a.name AS account, a.provider FROM cloud_instances i JOIN cloud_accounts a ON a.id=i.account_id
                   WHERE i.gone_at IS NULL AND (%s::int IS NULL OR i.account_id=%s) ORDER BY a.name, i.name""",
                (account_id, account_id))
    hosts = [{"name": h["name"], "ip_addresses": h.get("ip_addresses") or [], "status": h["status"]}
             for h in await health.hosts_health()]
    return cloud.match(rows, hosts)


def events(limit: int = 50) -> list[dict]:
    return db.q("""SELECT e.*, a.name AS account FROM cloud_events e JOIN cloud_accounts a ON a.id=e.account_id
                   ORDER BY e.ts DESC LIMIT %s""", (limit,))


async def loop():
    """Re-read every account every few minutes so the Fleet notices VMs created, deleted or stopped in the console."""
    while True:
        try:
            every = max(60.0, db.fsetting("cloud_sync_s"))
        except Exception:
            every = 300.0
        for acc in accounts():
            try:
                await sync(acc["id"])
            except Exception as e:   # one broken account must not stop the others
                log.warning("cloud sync %s failed: %s", acc["name"], e)
        await asyncio.sleep(every)
