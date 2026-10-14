#!/usr/bin/env bash
# Start the lab and put the demo services behind it. Safe to re-run. Undo with down.sh.
#   1. three nodes (core-rtr, sw-app, sw-data)
#   2. let LLDP frames cross the lab's Linux bridges (bridges drop 01:80:c2:00:00:0e by default)
#   3. give each demo service a port on its access segment and a route to the other segment through its switch
#   4. checkout reaches payment and inventory by their lab addresses, so those calls really cross the network
set -euo pipefail
cd "$(dirname "$0")"
docker compose up -d --build
NODE=aiops-netnode:latest
helper() { docker run --rm "$@"; }

for n in nl-core-app nl-core-data nl-seg-app nl-seg-data; do
  br="br-$(docker network inspect -f '{{.Id}}' "$n" | cut -c1-12)"
  helper --privileged --net host -v /sys:/sys --entrypoint sh "$NODE" -c "echo 16384 > /sys/class/net/$br/bridge/group_fwd_mask"
done

attach() {  # container network ip gateway
  docker network inspect -f '{{range .Containers}}{{.Name}} {{end}}' "$2" | grep -qw "$1" ||
    docker network connect --ip "$3" "$2" "$1"
  helper --net "container:$1" --cap-add NET_ADMIN --entrypoint sh "$NODE" -c "ip route replace 10.20.0.0/16 via $4"
}
attach frontend-a nl-seg-app 10.20.1.11 10.20.1.1
attach frontend-b nl-seg-app 10.20.1.12 10.20.1.1
attach checkout   nl-seg-app 10.20.1.13 10.20.1.1
attach payment    nl-seg-data 10.20.2.10 10.20.2.1
attach inventory  nl-seg-data 10.20.2.11 10.20.2.1

hosts_line() {  # container ip name: pin a name to its lab address (marked so down.sh can remove it)
  docker exec "$1" sh -c "grep -q ' $3 # netlab' /etc/hosts || echo '$2 $3 # netlab' >> /etc/hosts"
}
hosts_line checkout 10.20.2.10 payment
hosts_line checkout 10.20.2.11 inventory

echo "waiting for OSPF..."
for i in $(seq 1 30); do
  docker exec checkout python -c "import socket; socket.create_connection(('10.20.2.10', 8000), 2)" 2>/dev/null && break
  sleep 2
done
docker exec core-rtr vtysh -c 'show ip ospf neighbor'
echo "lab up: checkout -> payment now goes checkout - sw-app - core-rtr - sw-data - payment"
