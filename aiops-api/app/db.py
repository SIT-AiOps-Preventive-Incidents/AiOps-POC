"""SQLite app database: connections, metadata, deployments, incidents, runbooks, feedback."""
import json
import os
import sqlite3
import threading
import time

DB_PATH = os.environ.get("DB_PATH", "/data/aiops.db")
_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

JSON_COLS = {"signal", "evidence", "runbook", "action", "steps", "labels", "facts",
             "candidates", "steps_json", "payload", "tools", "kinds", "execution", "dry_run"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS apps (
  id INTEGER PRIMARY KEY, name TEXT, service_name TEXT UNIQUE, language TEXT, team TEXT,
  repo TEXT, environment TEXT, container TEXT, admin_url TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS hosts (
  id INTEGER PRIMARY KEY, name TEXT UNIQUE, address TEXT, os TEXT, environment TEXT,
  labels TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS deployments (
  id INTEGER PRIMARY KEY, service TEXT, version TEXT, commit_hash TEXT, author TEXT,
  message TEXT, profile TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY, title TEXT, kind TEXT, entity_type TEXT, entity TEXT, severity TEXT,
  status TEXT, started_at REAL, detected_at REAL, analyzed_at REAL, approved_at REAL,
  resolved_at REAL, signal TEXT, skill TEXT, skill_reason TEXT, path TEXT, root_cause TEXT,
  summary TEXT, confidence REAL, facts TEXT, evidence TEXT, runbook TEXT, action TEXT,
  candidates TEXT, steps TEXT, execution TEXT, runbook_id INTEGER, approver TEXT,
  llm_model TEXT, llm_ok INTEGER, analysis_ms INTEGER, score INTEGER, feedback TEXT,
  rca_correct INTEGER);
CREATE TABLE IF NOT EXISTS runbooks (
  id INTEGER PRIMARY KEY, signature TEXT UNIQUE, title TEXT, kind TEXT, skill TEXT,
  root_cause TEXT, runbook TEXT, action TEXT, uses INTEGER DEFAULT 0, score_sum INTEGER DEFAULT 0,
  score_n INTEGER DEFAULT 0, enabled INTEGER DEFAULT 1, source_incident INTEGER, created_at REAL,
  updated_at REAL);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY, ts REAL, channel TEXT, incident_id INTEGER, event TEXT, status TEXT,
  payload TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""

# Columns added after the first deploy - applied idempotently on startup.
MIGRATIONS = [
    "ALTER TABLE apps ADD COLUMN owner TEXT",
    "ALTER TABLE apps ADD COLUMN kind TEXT DEFAULT 'service'",
    "ALTER TABLE hosts ADD COLUMN owner TEXT",
    "ALTER TABLE incidents ADD COLUMN owner TEXT",
    "ALTER TABLE incidents ADD COLUMN dry_run TEXT",
]

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
}


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
        for m in MIGRATIONS:
            try:
                _conn.execute(m)
            except sqlite3.OperationalError:
                pass  # column already exists
        for k, v in DEFAULT_SETTINGS.items():
            _conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        _conn.commit()
    return _conn


def _decode(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in JSON_COLS & d.keys():
        if isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except ValueError:
                pass
    return d


def _encode(v):
    return json.dumps(v, default=str) if isinstance(v, (dict, list)) else v


def q(sql: str, args=()) -> list[dict]:
    with _lock:
        return [_decode(r) for r in conn().execute(sql, args).fetchall()]


def one(sql: str, args=()) -> dict | None:
    rows = q(sql, args)
    return rows[0] if rows else None


def ex(sql: str, args=()) -> int:
    with _lock:
        c = conn().execute(sql, [_encode(a) for a in args])
        conn().commit()
        return c.lastrowid


def insert(table: str, data: dict) -> int:
    cols = ",".join(data)
    return ex(f"INSERT INTO {table}({cols}) VALUES({','.join('?' * len(data))})", list(data.values()))


def update(table: str, rid: int, data: dict):
    if data:
        sets = ",".join(f"{k}=?" for k in data)
        ex(f"UPDATE {table} SET {sets} WHERE id=?", [*data.values(), rid])


def setting(key: str) -> str:
    r = one("SELECT value FROM settings WHERE key=?", (key,))
    return r["value"] if r else DEFAULT_SETTINGS.get(key, "")


def fsetting(key: str) -> float:
    try:
        return float(setting(key))
    except ValueError:
        return float(DEFAULT_SETTINGS[key])


def settings() -> dict:
    return {r["key"]: r["value"] for r in q("SELECT key,value FROM settings")}


def now() -> float:
    return time.time()
