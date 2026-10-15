"""Replay AnoMod's SocialNetwork recordings live, as if the system were running now.

AnoMod (Ping et al., MSR'26, CC BY 4.0) recorded traces (Jaeger) and container logs from a real SocialNetwork
deployment: one normal run and 12 runs with a fault injected. This process plays the normal run in a loop and, when
asked, one fault run, re-stamping every span and log line to the current time and sending them over OTLP to the
OpenTelemetry collector. From there they reach Tempo, Loki and the span metrics, exactly like a traced app's
telemetry, so AIOps One's detector, service map and agent work on them unchanged.

It also follows the demo network lab: a service the Network page reports as cut off from the core stops answering,
and the calls to it fail, the way a real outage would look.

Stdlib only. HTTP API on :8000:  GET /cases · GET /status · POST /play {"case": "Svc_Kill_Media"} · POST /stop
"""
from __future__ import annotations

import csv
import glob
import json
import os
import random
import re
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA = os.environ.get("ANOMOD_DIR", "/data")
OTLP = os.environ.get("OTLP_HTTP", "http://otel-collector:4318").rstrip("/")
API = os.environ.get("AIOPS_API", "http://aiops-api:8080").rstrip("/")
INFO_SAMPLE = int(os.environ.get("INFO_LOG_SAMPLE", "20"))   # keep 1 in N info lines; warnings/errors are all kept
NAMESPACE = "socialnetwork"
csv.field_size_limit(1 << 26)

KIND = {"internal": 1, "server": 2, "client": 3}
LOG_TS = re.compile(r"^\[(\d{4}-\w{3}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\]\s*<(\w+)>")
SEVERITY = {"trace": 1, "debug": 5, "info": 9, "warning": 13, "warn": 13, "error": 17, "fatal": 21}


# ---------------- loading a recorded run ----------------
@dataclass
class Span:
    offset: float          # seconds after the run's first span
    trace: str
    span: str
    parent: str
    service: str
    name: str
    duration_us: int
    status: int            # HTTP status, 0 if none
    method: str = ""
    url: str = ""
    error: bool = False


@dataclass
class LogLine:
    offset: float
    service: str
    severity: str
    text: str


@dataclass
class Run:
    name: str
    spans: list[Span] = field(default_factory=list)
    logs: list[LogLine] = field(default_factory=list)
    duration: float = 0.0


def short_name(folder: str) -> str:
    """'Svc_Kill_Media_20251104_000111_traces_2025-11-04_00-21-42' -> 'Svc_Kill_Media'."""
    return re.split(r"_\d{8}_\d{6}", os.path.basename(folder))[0]


def parse_ts(s: str) -> float:
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%b-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            continue
    raise ValueError(s)


def load_spans(path: str) -> tuple[list[Span], float]:
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                t = parse_ts(r["start_time"])
            except (ValueError, KeyError):
                continue
            status = int(r["http_status_code"]) if (r.get("http_status_code") or "").isdigit() else 0
            err = status >= 500 or '"error": true' in (r.get("tags") or "").lower()
            rows.append((t, Span(0, r["trace_id"], r["span_id"], r.get("parent_span_id") or "", r["service"],
                                 r.get("operation") or "?", int(float(r.get("duration_us") or 0)), status,
                                 r.get("http_method") or "", r.get("http_url") or "", err)))
    if not rows:
        return [], 0.0
    t0 = min(t for t, _ in rows)
    for t, s in rows:
        s.offset = t - t0
    rows.sort(key=lambda x: x[0])
    return [s for _, s in rows], t0


def service_of_logfile(path: str) -> str:
    """'HomeTimelineService_.log' -> 'home-timeline-service' (NginxThrift is the gateway)."""
    base = os.path.basename(path).split(".")[0].rstrip("_")
    name = re.sub(r"(?<!^)(?=[A-Z])", "-", base).lower()
    return {"nginx-thrift": "nginx-web-server"}.get(name, name)


def load_logs(folder: str, t0: float, duration: float, sample: int = INFO_SAMPLE) -> list[LogLine]:
    out, n = [], 0
    for p in sorted(glob.glob(os.path.join(folder, "*.log"))):
        svc = service_of_logfile(p)
        with open(p, errors="replace") as f:
            for line in f:
                m = LOG_TS.match(line)
                if not m:
                    continue
                try:
                    off = parse_ts(m.group(1)) - t0
                except ValueError:
                    continue
                if not 0 <= off <= duration:
                    continue
                sev = m.group(2).lower()
                n += 1
                if sev in ("info", "debug", "trace") and n % max(sample, 1):
                    continue
                out.append(LogLine(off, svc, sev, line.rstrip()[:2000]))
    out.sort(key=lambda l: l.offset)
    return out


def load_run(root: str, name: str) -> Run:
    run = Run(name)
    tdir = next(iter(glob.glob(os.path.join(root, "trace_data", name + "_*"))), None)
    if not tdir:
        return run
    run.spans, t0 = load_spans(os.path.join(tdir, "all_traces.csv"))
    run.duration = max((s.offset for s in run.spans), default=0.0) + 1
    ldir = next(iter(glob.glob(os.path.join(root, "log_data", name + "_*"))), None)
    if ldir and run.spans:
        run.logs = load_logs(ldir, t0, run.duration)
    return run


def available(root: str) -> list[str]:
    return sorted({short_name(d) for d in glob.glob(os.path.join(root, "trace_data", "*")) if os.path.isdir(d)})


# ---------------- OTLP encoding ----------------
def span_kind(s: Span, parent: Span | None) -> int:
    if s.name.endswith("_client"):
        return KIND["client"]
    if parent is None or parent.service != s.service or s.name.endswith("_server") or s.status:
        return KIND["server"]
    return KIND["internal"]


def _attr(k: str, v) -> dict:
    return {"key": k, "value": {"intValue": str(v)} if isinstance(v, int) else {"stringValue": str(v)}}


def resource(service: str) -> dict:
    return {"attributes": [_attr("service.name", service), _attr("service.namespace", NAMESPACE),
                           _attr("service.instance.id", f"sn-{service}"), _attr("deployment.environment", "anomod"),
                           _attr("app.version", "anomod-sn"), _attr("app.commit", "recorded")]}


def encode_spans(spans: list[tuple[Span, int, bool]], start_ns: dict[str, int], salt: str) -> dict:
    """[(span, kind, failed)] -> OTLP/JSON body. Trace ids get a per-loop salt so a replayed run never collides
    with the previous pass in Tempo."""
    by_svc: dict[str, list] = {}
    for s, kind, failed in spans:
        st = start_ns[s.span]
        o = {"traceId": salt + s.trace.rjust(16, "0")[-16:], "spanId": s.span.rjust(16, "0")[-16:], "name": s.name,
             "kind": kind, "startTimeUnixNano": str(st), "endTimeUnixNano": str(st + max(s.duration_us, 1) * 1000),
             "attributes": [], "status": {"code": 2 if (s.error or failed) else 0}}
        if s.parent and s.parent != s.trace:
            o["parentSpanId"] = s.parent.rjust(16, "0")[-16:]
        if s.method:
            o["attributes"].append(_attr("http.method", s.method))
        if s.url:
            o["attributes"].append(_attr("http.url", s.url[:300]))
        code = 503 if failed and s.status else s.status
        if code:
            o["attributes"].append(_attr("http.status_code", code))
        by_svc.setdefault(s.service, []).append(o)
    return {"resourceSpans": [{"resource": resource(svc), "scopeSpans": [{"scope": {"name": "anomod-replay"}, "spans": sp}]}
                              for svc, sp in by_svc.items()]}


def encode_logs(lines: list[LogLine], now_ns: int) -> dict:
    by_svc: dict[str, list] = {}
    for l in lines:
        by_svc.setdefault(l.service, []).append({
            "timeUnixNano": str(now_ns), "severityText": l.severity.upper(),
            "severityNumber": SEVERITY.get(l.severity, 9), "body": {"stringValue": l.text}})
    return {"resourceLogs": [{"resource": resource(svc), "scopeLogs": [{"scope": {"name": "anomod-replay"}, "logRecords": r}]}
                             for svc, r in by_svc.items()]}


def apply_network(trace: list[Span], down: set[str]) -> list[tuple[Span, bool]]:
    """A service cut off from the network answers nothing: its spans vanish, and the calls that reached for it fail
    (the caller's span and every span above it in the trace, up to the gateway)."""
    if not down or not any(s.service in down for s in trace):
        return [(s, False) for s in trace]
    by_id = {s.span: s for s in trace}
    failed: set[str] = set()
    for s in trace:
        if s.service in down:
            p = by_id.get(s.parent)
            while p is not None and p.span not in failed:
                failed.add(p.span)
                p = by_id.get(p.parent)
    return [(s, s.span in failed) for s in trace if s.service not in down]


# ---------------- the player ----------------
class Player:
    def __init__(self, root: str):
        self.root = root
        names = available(root)
        self.normal_name = next((n for n in names if n.startswith("Normal")), names[0] if names else "")
        self.faults = [n for n in names if n != self.normal_name]
        self.normal = load_run(root, self.normal_name) if self.normal_name else Run("none")
        self.run, self.started, self.salt = self.normal, time.time(), self._salt()
        self.pos_span = self.pos_log = 0
        self.down: set[str] = set()
        self.sent = {"spans": 0, "logs": 0, "errors": 0}
        self.loading = ""
        self.lock = threading.Lock()

    @staticmethod
    def _salt() -> str:
        return f"{random.getrandbits(64):016x}"

    def play(self, name: str, wait: bool = False):
        """Load the fault run (~10 s for its logs) in the background, then switch to it."""
        if name not in self.faults:
            raise KeyError(name)
        self.loading = name

        def load():
            run = load_run(self.root, name)
            with self.lock:
                self.run, self.started, self.salt, self.pos_span, self.pos_log = run, time.time(), self._salt(), 0, 0
                self.loading = ""
        t = threading.Thread(target=load, daemon=True)
        t.start()
        if wait:
            t.join()

    def stop(self):
        with self.lock:
            self.run, self.started, self.salt, self.pos_span, self.pos_log = self.normal, time.time(), self._salt(), 0, 0

    def status(self) -> dict:
        el = time.time() - self.started
        return {"playing": self.run.name, "normal": self.run is self.normal, "loading": self.loading, "elapsed_s": round(el),
                "duration_s": round(self.run.duration), "cut_off": sorted(self.down), **self.sent}

    def tick(self):
        """Send everything whose recorded offset has now been reached. A finished fault run hands back to normal."""
        with self.lock:
            run, el = self.run, time.time() - self.started
            if el >= run.duration:
                if run is not self.normal:
                    self.run = self.normal
                self.started, self.salt, self.pos_span, self.pos_log = time.time(), self._salt(), 0, 0
                return
            i = self.pos_span
            while self.pos_span < len(run.spans) and run.spans[self.pos_span].offset <= el:
                self.pos_span += 1
            batch = run.spans[i:self.pos_span]
            j = self.pos_log
            while self.pos_log < len(run.logs) and run.logs[self.pos_log].offset <= el:
                self.pos_log += 1
            logs = run.logs[j:self.pos_log]
            base_ns, salt, down = int(self.started * 1e9), self.salt, set(self.down)
        if batch:
            traces: dict[str, list[Span]] = {}
            for s in batch:
                traces.setdefault(s.trace, []).append(s)
            out = []
            for tr in traces.values():
                by_id = {s.span: s for s in tr}
                for s, failed in apply_network(tr, down):
                    out.append((s, span_kind(s, by_id.get(s.parent)), failed))
            starts = {s.span: base_ns + int(s.offset * 1e9) for s, _, _ in out}
            if out:
                post(f"{OTLP}/v1/traces", encode_spans(out, starts, salt))
            self.sent["spans"] += len(out)
            self.sent["errors"] += sum(1 for s, _, f in out if f or s.error)
        if logs:
            now = time.time_ns()
            lines = [l for l in logs if l.service not in down]
            if lines:
                post(f"{OTLP}/v1/logs", encode_logs(lines, now))
            self.sent["logs"] += len(lines)

    def follow_network(self):
        try:
            with urllib.request.urlopen(f"{API}/api/v1/network", timeout=10) as r:
                topo = json.load(r)
            self.down = set(topo.get("impacted_services") or [])
        except Exception:
            pass   # no network lab, or the API is restarting: replay as recorded


def post(url: str, body: dict):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:
        print(f"send failed {url}: {e}", flush=True)


def serve(player: Player, port: int = 8000):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code: int, body: dict):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/cases":
                return self._send(200, {"normal": player.normal_name, "faults": player.faults})
            if self.path in ("/status", "/health"):
                return self._send(200, player.status())
            self._send(404, {"error": "not found"})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if self.path == "/play":
                try:
                    player.play(body.get("case", ""))
                except KeyError:
                    return self._send(404, {"error": f"unknown case {body.get('case')!r}", "faults": player.faults})
                return self._send(202, player.status())
            if self.path == "/stop":
                player.stop()
                return self._send(200, player.status())
            self._send(404, {"error": "not found"})

    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


def main():
    root = os.path.join(DATA, "SN_data") if os.path.isdir(os.path.join(DATA, "SN_data")) else DATA
    player = Player(root)
    print(f"AnoMod replay: normal={player.normal_name} ({len(player.normal.spans)} spans, {len(player.normal.logs)} log "
          f"lines, {player.normal.duration:.0f} s), {len(player.faults)} fault runs", flush=True)
    threading.Thread(target=serve, args=(player,), daemon=True).start()
    last_net = 0.0
    while True:
        if time.time() - last_net > 15:
            player.follow_network()
            last_net = time.time()
        player.tick()
        time.sleep(1)


if __name__ == "__main__":
    main()
