"""Steady user traffic against the demo shop, plus an /admin/attack switch that
simulates a credential-stuffing burst from one IP (for the Security skill)."""
import random
import threading
import time

import requests
from flask import Flask, jsonify, request

FRONT = "http://edge-fw:80"  # clients enter through the firewall -> LB -> frontend replicas
ATTACK = {"until": 0.0, "ip": "203.0.113.77"}
USERS = ["somchai", "malee", "anan", "pim", "krit"]
s = requests.Session()


# Simulated customers on Thai consumer ISPs (public ranges), so firewall logs carry real-looking sources.
CLIENTS = [f"{a}.{random.randint(1, 250)}.{random.randint(1, 250)}" for a in ("49.228", "110.164", "171.97", "183.88")
           for _ in range(15)]


def users():
    while True:
        try:
            r = random.random()
            h = {"X-Forwarded-For": random.choice(CLIENTS)}
            if r < 0.5:
                s.get(f"{FRONT}/api/products", headers=h, timeout=10)
            elif r < 0.9:
                s.post(f"{FRONT}/api/checkout", json={"sku": f"SKU-{random.randint(0, 4)}", "qty": 1}, headers=h,
                       timeout=10)
            else:
                s.post(f"{FRONT}/api/login", json={"user": random.choice(USERS), "password": "secret"},
                       headers=h, timeout=10)
        except Exception:
            pass
        time.sleep(random.uniform(0.15, 0.35))


def attacker():
    while True:
        if time.time() < ATTACK["until"]:
            try:
                s.post(f"{FRONT}/api/login", json={"user": random.choice(["admin", "root", "test"]), "password": "x"},
                       headers={"X-Forwarded-For": ATTACK["ip"]}, timeout=5)
            except Exception:
                pass
            time.sleep(0.08)
        else:
            time.sleep(1)


app = Flask(__name__)


@app.post("/admin/attack")
def attack():
    body = request.get_json(silent=True) or {}
    ATTACK["ip"] = body.get("ip", ATTACK["ip"])
    ATTACK["until"] = time.time() + int(body.get("seconds", 180))
    return jsonify(ATTACK)


@app.get("/health")
def health():
    return jsonify(status="ok", attacking=time.time() < ATTACK["until"])


if __name__ == "__main__":
    for _ in range(2):
        threading.Thread(target=users, daemon=True).start()
    threading.Thread(target=attacker, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=True)
