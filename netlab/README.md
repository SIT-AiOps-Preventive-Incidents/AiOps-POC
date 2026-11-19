# Demo network lab

A small real network between the demo services, so AIOps One's **Network** page has switches and routers to discover.

```
                  core-rtr  (FRR, OSPF)
                 /        \
           sw-app          sw-data          every node: SNMP v2c (IF-MIB, IP-MIB, LLDP-MIB) + LLDP
             |                |             + a management port on the "aiops" network
   frontend-a, frontend-b,   payment, inventory
   checkout   (10.20.1.0/24)  (10.20.2.0/24)
```

`up.sh` also makes checkout reach payment and inventory **through** the lab (a route plus an `/etc/hosts` entry
inside checkout), so a broken cable really breaks checkout's calls. Nothing in the main `docker-compose.yml` changes.

```bash
./netlab/up.sh     # build the node image, start 3 nodes, attach the services (~1 min)
./netlab/down.sh   # remove everything, services back on the flat network
```

AIOps One finds the nodes by their `aiops.netdevice=true` label and polls them every minute. Real gear works the
same way: list its addresses under Settings → `net_devices` (SNMP v2c read community in `net_snmp_community`).

## Test cases

Run them from **Demo scenarios → Network** (shown only while the lab runs), or with
`curl -X POST :8080/api/v1/scenarios/<id>/runs`. **Reset everything** undoes all of them.

| # | Case | What happens | Expect on Network (within ~1 min) | Expect elsewhere |
|---|---|---|---|---|
| 1 | Baseline | lab just started | 3 devices, 2 cables up, 5 known hosts, services frontend/checkout/payment/inventory, no unknown hosts. Changes is empty (first scan is the baseline). | - |
| 2 | `net_link_down` | sw-data's uplink to core-rtr goes down | cable core-rtr–sw-data red and dashed; payment and inventory **cut off**; tile "Services cut off: 2"; Changes: *link went down*, *payment / inventory lost their path to the core* | checkout errors rise → incident on checkout (existing detector) |
| 3 | `net_host_port` | sw-data's port toward the servers goes down | sw-data shows `1/2 down`; payment and inventory hosts **down** (then **missing** once sw-data's ARP entries expire) | same checkout incident |
| 4 | `net_rogue_device` | an unregistered container joins the app segment and pings | orange **Unknown device 10.20.1.x** with a `new` badge on `sw-app:eth*`; Changes: *Unknown device … appeared* | - |
| 5 | Reset | ports up, rogue removed | cables green again; Changes: *link is back up*, *reachable again*; the rogue turns **missing** (kept for a day) | checkout recovers |
| 6 | Device down | `docker stop sw-app` (manual) | sw-app **not answering**, its cable down, its hosts missing | frontend/checkout incidents |

Check from the command line:

```bash
docker exec core-rtr vtysh -c 'show ip ospf neighbor'                 # 2 neighbours, Full
docker exec core-rtr lldpcli show neighbors                           # sw-app and sw-data
docker exec aiops-api snmpbulkwalk -v2c -c public -On sw-app 1.0.8802.1.1.2.1.4.1.1.9   # LLDP over SNMP
curl -s :8080/api/v1/network | jq '.impacted_services, [.events[].text]'
```

Unit tests (no lab needed): `aiops-api/tests/test_netdisco.py`, `aiops-api/tests/test_routes_network.py`.
