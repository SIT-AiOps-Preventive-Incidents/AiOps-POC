#!/usr/bin/env bash
# Remove the lab and put the demo services back on the flat network exactly as before.
set -uo pipefail
cd "$(dirname "$0")"
for c in checkout; do
  docker exec "$c" sh -c "grep -v ' # netlab' /etc/hosts > /tmp/h && cat /tmp/h > /etc/hosts" 2>/dev/null
done
for pair in frontend-a:nl-seg-app frontend-b:nl-seg-app checkout:nl-seg-app payment:nl-seg-data inventory:nl-seg-data; do
  docker network disconnect "${pair#*:}" "${pair%%:*}" 2>/dev/null   # its routes go with the port
done
docker ps -aq --filter label=aiops.netlab=rogue | xargs -r docker rm -f >/dev/null
docker compose down --rmi local
echo "lab removed"
