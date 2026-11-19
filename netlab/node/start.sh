#!/bin/sh
# snmpd first (lldpd attaches to it over AgentX), then lldpd, then FRR in the foreground.
mkdir -p /var/agentx
# -C: read only this file. It is also snmpd's default path, so without -C it is read twice, port 161 is bound
# twice and snmpd exits.
snmpd -Lsd -C -c /etc/snmp/snmpd.conf
sleep 1
# LLDP on the lab ports only (the ones holding a 10.20.x address), not on the management port.
ports=$(ip -o -4 addr | awk '$4 ~ /^10\.20\./ {print $2}' | sort -u | paste -sd, -)
# -x: serve LLDP-MIB through snmpd; -M 4: we are a network device
lldpd -x -X /var/agentx/master -M 4 -I "$ports"
# Ping-sweep the access subnets every minute, like an NMS does, so hosts that never talk to their gateway still
# show up in the ARP table that discovery reads.
( while true; do
    for net in $(ip -o -4 addr | awk '$4 ~ /^10\.20\.[0-9]+\.[0-9]+\/24$/ {split($4, a, "."); print a[1]"."a[2]"."a[3]}'); do
      for i in $(seq 2 40); do ping -c1 -W1 "$net.$i" >/dev/null 2>&1 & done
    done
    sleep 60
  done ) &
sed -i 's/^ospfd=no/ospfd=yes/' /etc/frr/daemons
exec /usr/lib/frr/docker-start
