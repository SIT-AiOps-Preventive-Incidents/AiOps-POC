#!/bin/sh
# "Connect a computer -> its services are traced for you" demo.
# Two plain-Python processes with NO OpenTelemetry code: orders (:8200) calls stock (:8201).
# The host agent discovers both ports and traces them with eBPF; a small loop keeps traffic flowing.
D=$(cd "$(dirname "$0")" && pwd)
for p in $(pgrep -f "$D/legacy_app.py"); do kill "$p"; done
for p in $(pgrep -f "$D/traffic.sh"); do kill "$p"; done
nohup python3 "$D/legacy_app.py" stock 8201 >/dev/null 2>&1 &
nohup python3 "$D/legacy_app.py" orders 8200 >/dev/null 2>&1 &
nohup "$D/traffic.sh" >/dev/null 2>&1 &
echo "legacy demo running: orders :8200 -> stock :8201 (1 request / 2 s)"
