"""Let AIOps One run NIKA's own fault cases on a live NIKA lab, so the Network page shows a network from research.

Runs on the host (next to NIKA's virtualenv), stdlib only, HTTP on :18900:
  GET  /cases    the offered cases: NIKA's own rows from benchmark/working/pool/<scenario>/<fault>.yaml,
                 with their injection parameters and ground-truth root causes
  GET  /status   what is deployed and injected right now (session, case, ground truth)
  POST /play     {"id": "link_down.1"}: redeploy the lab clean, then inject that case with NIKA's injector
  POST /reset    redeploy the lab clean (NIKA has no "undo": a fresh lab is how it recovers)

Everything goes through NIKA's CLI (`nika env run`, `nika failure inject`, `nika session close`): this only picks
which of NIKA's cases to run. Start/stop with bridge.sh.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

NIKA_DIR = os.environ.get("NIKA_DIR", os.path.expanduser("~/nika-bench/NIKA"))
SCENARIO, SIZE = os.environ.get("NIKA_SCENARIO", "dc_clos"), os.environ.get("NIKA_SIZE", "s")
# Which of NIKA's cases to offer: (fault, index among the scenario/size rows of that fault). Chosen so the fault
# changes what a network monitor can see: a cable, a port, a router's routing.
OFFER = [("link_down", 0), ("link_down", 1), ("link_down", 2), ("link_detach", 1), ("frr_service_down", 0)]
ENV = {**os.environ, "PATH": f"{os.path.expanduser('~/nika-bench/bin')}:{os.environ.get('PATH', '')}",
       "UV_CACHE_DIR": os.path.expanduser("~/nika-bench/uv-cache")}


def load_cases(nika_dir: str = NIKA_DIR, scenario: str = SCENARIO, size: str = SIZE, offer=OFFER) -> list[dict]:
    out = []
    for fault, idx in offer:
        path = os.path.join(nika_dir, "benchmark", "working", "pool", scenario, f"{fault}.yaml")
        if not os.path.exists(path):
            continue
        rows = [c for c in (yaml.safe_load(open(path)) or {}).get("failure", {}).get("cases", []) if c.get("topo_size") == size]
        if idx < len(rows):
            r = rows[idx]
            out.append({"id": f"{fault}.{idx}", "fault": fault, "inject": r.get("inject") or {},
                        "root_causes": [{"resource": rc["resource"], "fault_type": rc["fault_type"]} for rc in r.get("root_causes", [])],
                        "source": f"NIKA pool {scenario}/{fault}.yaml"})
    return out


def resource_id(res: dict) -> str:
    """NIKA's catalog id: link/<a:eth--b:eth>, interface/<node>/<eth>, node/<node>."""
    k = res.get("kind")
    if k == "link":
        return f"link/{res['name']}"
    if k == "interface":
        return f"interface/{res['node']}/{res['name']}"
    return f"node/{res.get('node') or res.get('name')}"


class Lab:
    def __init__(self):
        self.cases = {c["id"]: c for c in load_cases()}
        self.state, self.case, self.error, self.session = "idle", None, "", None
        self.lock = threading.Lock()

    def nika(self, *args: str, timeout: int = 900) -> str:
        r = subprocess.run(["uv", "run", "-q", "nika", *args], cwd=NIKA_DIR, env=ENV, capture_output=True,
                           text=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout) else f"nika {args[0]} failed")
        return r.stdout

    def redeploy(self):
        self.state = "deploying"
        try:
            self.nika("session", "wipe", "-y")      # every running session and leftover lab, NIKA's own clean-up
        except RuntimeError:
            pass
        out = self.nika("env", "run", SCENARIO, "-s", SIZE)
        self.session = next((l.split("=", 1)[1] for l in out.splitlines() if l.startswith("session_id=")), None)

    def _run(self, case_id: str | None):
        try:
            self.redeploy()
            if case_id:
                c = self.cases[case_id]
                self.state = "injecting"
                sets = [x for k, v in c["inject"].items() for x in ("--set", f"{k}={v}")]
                self.nika("failure", "inject", c["fault"], *sets)
            self.state, self.case, self.error = "ready", case_id, ""
        except Exception as e:
            self.state, self.case, self.error = "error", None, str(e)[:300]

    def start(self, case_id: str | None):
        if case_id is not None and case_id not in self.cases:
            raise KeyError(case_id)
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("busy")

        def go():
            try:
                self._run(case_id)
            finally:
                self.lock.release()
        threading.Thread(target=go, daemon=True).start()

    def status(self) -> dict:
        c = self.cases.get(self.case) if self.case else None
        return {"state": self.state, "scenario": f"{SCENARIO} ({SIZE})", "session": self.session, "error": self.error,
                "case": c and {"id": c["id"], "fault": c["fault"], "inject": c["inject"],
                               "ground_truth": [{"resource_id": resource_id(r["resource"]), "fault_type": r["fault_type"]}
                                                for r in c["root_causes"]], "source": c["source"]},
                "reference": "NIKA, sands-lab (SIGCOMM NGNO 2025), github.com/sands-lab/nika"}


def serve(lab: Lab, host: str, port: int):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/cases":
                return self.send(200, list(lab.cases.values()))
            if self.path == "/status":
                return self.send(200, lab.status())
            self.send(404, {"error": "not found"})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            try:
                if self.path == "/play":
                    lab.start(body.get("id", ""))
                elif self.path == "/reset":
                    lab.start(None)
                else:
                    return self.send(404, {"error": "not found"})
            except KeyError:
                return self.send(404, {"error": f"unknown case {body.get('id')!r}"})
            except RuntimeError as e:
                return self.send(409, {"error": str(e)})
            self.send(202, lab.status())

    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    lab = Lab()
    print(f"NIKA bridge: {len(lab.cases)} cases from {NIKA_DIR}", flush=True)
    serve(lab, os.environ.get("BRIDGE_HOST", "0.0.0.0"), int(os.environ.get("BRIDGE_PORT", "18900")))
