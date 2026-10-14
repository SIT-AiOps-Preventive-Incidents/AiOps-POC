# A network node: FRR for routing, net-snmp for SNMP (IF-MIB, IP-MIB, ARP), lldpd for LLDP (also served over SNMP
# through AgentX, so LLDP-MIB answers like on a real switch).
FROM frrouting/frr:v10.2.1
RUN apk add --no-cache net-snmp net-snmp-tools lldpd tcpdump
COPY snmpd.conf /etc/snmp/snmpd.conf
COPY start.sh /start.sh
RUN chmod +x /start.sh
ENTRYPOINT ["/start.sh"]
