"""Demo "shop" microservice — one image, role picked by $SERVICE.

frontend -> checkout -> (inventory, payment)
Every service is instrumented with OpenTelemetry (traces + logs over OTLP) and
stamps each request span with app.version / app.commit, which the collector turns
into metric labels. /admin/* lets the AIOps platform (and the chaos panel) change
the running version, inject faults, and apply remediations.
"""
import logging
import os
import random
import subprocess
import time

import requests
from flask import Flask, jsonify, request
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE = os.environ["SERVICE"]
INSTANCE = os.environ.get("INSTANCE", SERVICE)
OTLP = os.environ.get("OTLP_ENDPOINT", "http://otel-collector:4317")
URL = {s: f"http://{s}:8000" for s in ("frontend", "checkout", "payment", "inventory")}

resource = Resource.create({
    "service.name": SERVICE,
    "service.namespace": "shop",
    "service.instance.id": INSTANCE,
    "deployment.environment": "poc",
})
tp = TracerProvider(resource=resource)
tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP, insecure=True)))
trace.set_tracer_provider(tp)
lp = LoggerProvider(resource=resource)
lp.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTLP, insecure=True)))
set_logger_provider(lp)

log = logging.getLogger(SERVICE)
log.setLevel(logging.INFO)
log.addHandler(LoggingHandler(level=logging.INFO, logger_provider=lp))
log.addHandler(logging.StreamHandler())
logging.getLogger("werkzeug").setLevel(logging.ERROR)

STATE = {
    "version": os.environ.get("APP_VERSION", "1.0.0"),
    "commit": os.environ.get("APP_COMMIT", "0000000"),
    "profile": "healthy",
    "error_rate": 0.0,
    "error_msg": "",
    "latency_ms": 0,
    "latency_msg": "",
    "blocked_ips": [],
}
HOGS: list[subprocess.Popen] = []

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app, excluded_urls="health,admin")
RequestsInstrumentor().instrument()
http = requests.Session()


class FaultError(Exception):
    pass


@app.before_request
def stamp_version():
    span = trace.get_current_span()
    span.set_attribute("app.version", STATE["version"])
    span.set_attribute("app.commit", STATE["commit"])


def maybe_fault(op: str):
    if STATE["latency_ms"]:
        delay = STATE["latency_ms"] * random.uniform(0.8, 1.3)
        time.sleep(delay / 1000)
        if STATE["latency_msg"]:
            log.warning(STATE["latency_msg"].format(ms=int(delay)))
    if STATE["error_rate"] and random.random() < STATE["error_rate"]:
        raise FaultError(STATE["error_msg"] or f"{op} failed")


@app.errorhandler(FaultError)
def on_fault(e):
    span = trace.get_current_span()
    span.record_exception(e)
    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
    log.error(f"{request.method} {request.path} failed: {e} [instance={INSTANCE} version={STATE['version']} commit={STATE['commit']}]")
    return jsonify(error=str(e)), 500


def call(method: str, svc: str, path: str, **kw):
    r = http.request(method, URL[svc] + path, timeout=8, **kw)
    if r.status_code >= 400:
        raise FaultError(f"{svc} {path} returned HTTP {r.status_code}")
    return r.json()


# ---------------- business endpoints ----------------
if SERVICE == "frontend":
    @app.get("/api/products")
    def products():
        maybe_fault("products")
        return jsonify(call("GET", "inventory", "/items"))

    @app.post("/api/checkout")
    def checkout():
        maybe_fault("checkout")
        try:
            return jsonify(call("POST", "checkout", "/checkout", json=request.get_json(silent=True) or {}))
        except FaultError as e:
            raise FaultError(f"checkout unavailable: {e}")

    @app.post("/api/login")
    def login():
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        body = request.get_json(silent=True) or {}
        user = body.get("user", "?")
        if ip in STATE["blocked_ips"]:
            log.warning(f"blocked request from ip={ip} user={user} (blocklist)")
            return jsonify(error="blocked"), 403
        if body.get("password") != "secret":
            log.warning(f"failed login for user={user} from ip={ip}")
            return jsonify(error="invalid credentials"), 401
        log.info(f"login ok user={user} ip={ip}")
        return jsonify(ok=True)

elif SERVICE == "checkout":
    @app.post("/checkout")
    def do_checkout():
        maybe_fault("checkout")
        order = request.get_json(silent=True) or {}
        items = call("POST", "inventory", "/reserve", json=order)
        try:
            pay = call("POST", "payment", "/charge", json={"amount": items.get("total", 0)})
        except FaultError as e:
            log.error(f"order failed, payment step: {e}")
            raise
        log.info(f"order placed total={items.get('total')} txn={pay.get('txn')}")
        return jsonify(order="ok", txn=pay.get("txn"))

elif SERVICE == "payment":
    @app.post("/charge")
    def charge():
        maybe_fault("charge")
        amt = (request.get_json(silent=True) or {}).get("amount", 0)
        time.sleep(random.uniform(0.02, 0.08))
        return jsonify(txn=f"tx{random.randint(100000, 999999)}", amount=amt)

elif SERVICE == "inventory":
    @app.get("/items")
    def items():
        maybe_fault("items")
        time.sleep(random.uniform(0.01, 0.04))
        return jsonify([{"sku": f"SKU-{i}", "stock": random.randint(0, 50)} for i in range(5)])

    @app.post("/reserve")
    def reserve():
        maybe_fault("reserve")
        time.sleep(random.uniform(0.01, 0.05))
        return jsonify(reserved=True, total=round(random.uniform(100, 2000), 2))


# ---------------- platform / admin endpoints ----------------
@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE, instance=INSTANCE, **{k: STATE[k] for k in ("version", "commit", "profile")})


@app.get("/admin/state")
def get_state():
    return jsonify(STATE | {"cpu_hogs": sum(1 for p in HOGS if p.poll() is None)})


@app.post("/admin/state")
def set_state():
    body = request.get_json(force=True)
    for k in STATE:
        if k in body:
            STATE[k] = body[k]
    log.info(f"runtime state changed: {body}")
    return get_state()


@app.post("/admin/cpu")
def cpu_hog():
    body = request.get_json(silent=True) or {}
    secs, workers = int(body.get("seconds", 300)), int(body.get("workers", 3))
    for _ in range(workers):
        HOGS.append(subprocess.Popen(["timeout", str(secs), "python", "-c", "while True: pass"]))
    log.warning(f"batch job reindex_ledger started with {workers} workers (expected 300s)")
    return get_state()


@app.post("/admin/blocklist")
def blocklist():
    ip = (request.get_json(force=True) or {}).get("ip")
    if ip and ip not in STATE["blocked_ips"]:
        STATE["blocked_ips"].append(ip)
        log.info(f"ip {ip} added to blocklist")
    return get_state()


if __name__ == "__main__":
    log.info(f"{SERVICE} ({INSTANCE}) starting version={STATE['version']} commit={STATE['commit']}")
    app.run(host="0.0.0.0", port=8000, threaded=True)
