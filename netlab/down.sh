#!/usr/bin/env bash
# Remove the lab and put the demo services back on the flat network exactly as before.
set -uo pipefail
cd "$(dirname "$0")"
for c in checkout; do
  docker exec "$c" sh -c "grep -v ' # netlab' /etc/hosts > /tmp/h && cat /tmp/h > /etc/hosts" 2>/dev/null
done
for net in nl-seg-app nl-seg-data; do   # every host attached by up.sh, whichever dataset; routes go with the port
  for c in $(docker network inspect -f '{{range .Containers}}{{.Name}} {{end}}' "$net" 2>/dev/null); do
    case "$c" in sw-*|core-rtr|rogue-*) ;; *) docker network disconnect "$net" "$c" 2>/dev/null ;; esac
  done
done
docker ps -aq --filter label=aiops.netlab=rogue | xargs -r docker rm -f >/dev/null
docker compose down --rmi local
echo "lab removed"
