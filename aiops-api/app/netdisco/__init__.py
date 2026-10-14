"""Network asset discovery and topology (SNMP + LLDP). Self-contained: snmp (poll + parse), topology (pure graph),
service (scan loop + storage, own schema.sql). main.py only starts `service.loop()` and mounts routes_network."""
