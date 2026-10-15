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
# Which hosts sit behind the switches: the shop's containers, or one small host per replayed AnoMod service
# (replay/anomod). DEMO_DATASET picks, like it does for aiops-api.
if [ "${DEMO_DATASET:-shop}" = anomod ]; then
  APP_HOSTS="sn-nginx-web-server sn-compose-post-service sn-home-timeline-service sn-user-timeline-service sn-text-service sn-media-service sn-url-shorten-service sn-user-mention-service sn-unique-id-service"
  DATA_HOSTS="sn-user-service sn-social-graph-service sn-post-storage-service"
else
  APP_HOSTS="frontend-a frontend-b checkout"
  DATA_HOSTS="payment inventory"
fi
i=11; for h in $APP_HOSTS; do attach "$h" nl-seg-app "10.20.1.$i" 10.20.1.1; i=$((i + 1)); done
i=10; for h in $DATA_HOSTS; do attach "$h" nl-seg-data "10.20.2.$i" 10.20.2.1; i=$((i + 1)); done

hosts_line() {  # container ip name: pin a name to its lab address (marked so down.sh can remove it)
  docker exec "$1" sh -c "grep -q ' $3 # netlab' /etc/hosts || echo '$2 $3 # netlab' >> /etc/hosts"
}
if [ "${DEMO_DATASET:-shop}" != anomod ]; then   # the shop's checkout really calls through the lab
  hosts_line checkout 10.20.2.10 payment
  hosts_line checkout 10.20.2.11 inventory
fi

echo "waiting for OSPF..."
first_app=${APP_HOSTS%% *}
for i in $(seq 1 30); do
  docker run --rm --net "container:$first_app" --entrypoint sh "$NODE" -c "ping -c1 -W1 10.20.2.10" >/dev/null 2>&1 && break
  sleep 2
done
docker exec core-rtr vtysh -c 'show ip ospf neighbor'
echo "lab up: $first_app reaches 10.20.2.10 through sw-app - core-rtr - sw-data"
