"""PostgreSQL access. Thin helpers over psycopg 3; domain queries live in repo.py.

Timestamps are TIMESTAMPTZ in the database and epoch seconds (float) everywhere in Python and the API,
so the frontend never has to parse dates.
"""
import datetime as dt
import decimal
import json
import os
import threading
import time
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

DSN = os.environ.get("DATABASE_URL", "postgresql://aiops:aiops@postgres:5432/aiops")
SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")
_lock = threading.RLock()
_conn: psycopg.Connection | None = None

DEFAULT_SETTINGS = {
    "teams_webhook": "",
    "llm_model": "qwen2.5:1.5b",
    "auto_analyze": "1",
    "err_threshold": "0.05",
    "p95_threshold_ms": "800",
    "cpu_threshold": "70",
    "mem_threshold": "90",
    "disk_threshold": "90",
    "auth_fail_per_min": "40",
    "verify_after_s": "60",
    # the platform's own containers are not part of the monitored application
    "discovery_ignore_containers": "aiops-api,ollama,prometheus,loki,tempo,grafana,otel-collector,node-exporter,postgres,loadgen",
}


def _connect() -> psycopg.Connection:
    for attempt in range(30):  # postgres may still be starting
        try:
            return psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        except psycopg.OperationalError:
            time.sleep(2)
    raise RuntimeError("database unavailable")


def conn() -> psycopg.Connection:
    global _conn
    with _lock:
        if _conn is None or _conn.closed:
            _conn = _connect()
        return _conn


def init():
    with open(SCHEMA) as f:
        conn().execute(f.read())
    for k, v in DEFAULT_SETTINGS.items():
        ex("INSERT INTO settings(key, value) VALUES (%s, %s) ON CONFLICT DO NOTHING", (k, v))


def T(epoch: float | None):
    """epoch seconds -> timestamptz parameter."""
    return None if epoch is None else dt.datetime.fromtimestamp(epoch, dt.timezone.utc)


def J(v):
    """Wrap a dict/list for a JSONB parameter."""
    return Jsonb(v)


def _out(v):
    if isinstance(v, dt.datetime):
        return v.timestamp()
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    return v


def _row(r: dict) -> dict:
    return {k: _out(v) for k, v in r.items()}


def _retry(fn):
    """One reconnect on a dropped connection (e.g. postgres restarted)."""
    global _conn
    try:
        return fn()
    except psycopg.OperationalError:
        with _lock:
            _conn = None
        return fn()


def q(sql: str, args=()) -> list[dict]:
    def run():
        with _lock:
            return [_row(r) for r in conn().execute(sql, args).fetchall()]
    return _retry(run)


def one(sql: str, args=()) -> dict | None:
    rows = q(sql, args)
    return rows[0] if rows else None


def val(sql: str, args=()):
    r = one(sql, args)
    return next(iter(r.values())) if r else None


def ex(sql: str, args=()) -> None:
    def run():
        with _lock:
            conn().execute(sql, args)
    _retry(run)


@contextmanager
def tx():
    """Atomic block: `with db.tx() as c: c.execute(...)`."""
    with _lock:
        with conn().transaction():
            yield conn()


# ---------------- settings ----------------
def setting(key: str) -> str:
    v = val("SELECT value FROM settings WHERE key=%s", (key,))
    return v if v is not None else DEFAULT_SETTINGS.get(key, "")


def fsetting(key: str) -> float:
    try:
        return float(setting(key))
    except ValueError:
        return float(DEFAULT_SETTINGS[key])


def settings() -> dict:
    return {r["key"]: r["value"] for r in q("SELECT key, value FROM settings ORDER BY key")}


def set_setting(key: str, value: str):
    ex("INSERT INTO settings(key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
       (key, str(value)))


def now() -> float:
    return time.time()


def dumps(v) -> str:
    return json.dumps(v, default=str)
