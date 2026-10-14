-- Network discovery. Owned by app/netdisco; drop these three tables to remove the feature's data.
CREATE TABLE IF NOT EXISTS net_assets (
  id          TEXT PRIMARY KEY,                -- dev:<sysName> | host:<mac> | svc:<service>
  kind        TEXT NOT NULL,                   -- device | host | service
  status      TEXT NOT NULL,
  data        JSONB NOT NULL DEFAULT '{}',     -- the node as the topology built it
  first_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen   TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS net_links (
  id          TEXT PRIMARY KEY,                -- sorted "a:port--b:port"
  status      TEXT NOT NULL,
  data        JSONB NOT NULL DEFAULT '{}',
  last_seen   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS net_events (
  id          SERIAL PRIMARY KEY,
  ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
  kind        TEXT NOT NULL,                   -- link_down | link_up | device_down | device_up | host_new | host_unknown | ...
  severity    TEXT NOT NULL,                   -- critical | warning | info
  entity      TEXT NOT NULL,
  text        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS net_events_ts ON net_events (ts DESC);
