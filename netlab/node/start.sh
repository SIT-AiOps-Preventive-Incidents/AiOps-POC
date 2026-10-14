#!/bin/sh
# snmpd first (lldpd attaches to it over AgentX), then lldpd, then FRR in the foreground.
mkdir -p /var/agentx
snmpd -Lsd -c /etc/snmp/snmpd.conf
sleep 1
# LLDP on the lab ports only (the ones holding a 10.20.x address), not on the management port.
ports=$(ip -o -4 addr | awk '$4 ~ /^10\.20\./ {print $2}' | sort -u | paste -sd, -)
# -x: serve LLDP-MIB through snmpd; -M 4: we are a network device
lldpd -x -X /var/agentx/master -M 4 -I "$ports"
sed -i 's/^ospfd=no/ospfd=yes/' /etc/frr/daemons
exec /usr/lib/frr/docker-start
