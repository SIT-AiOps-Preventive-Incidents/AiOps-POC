"""Cloud inventory: every provider's instance list becomes one shape, then diffed and matched to our agents.

Fixtures are trimmed copies of each provider's documented response, no network and no database.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import cloud  # noqa: E402

# ------------------------------------------------------------------ OpenStack (Nova /servers/detail)
NOVA = {"servers": [
    {"id": "9e5f-a1", "name": "web-01", "status": "ACTIVE", "created": "2026-10-01T03:00:00Z",
     "OS-EXT-AZ:availability_zone": "bkk-1a", "flavor": {"original_name": "c2.m4"}, "metadata": {"team": "esg"},
     "addresses": {"prod-net": [{"addr": "10.20.0.11", "version": 4, "OS-EXT-IPS:type": "fixed"},
                                {"addr": "203.0.113.7", "version": 4, "OS-EXT-IPS:type": "floating"}]}},
    {"id": "9e5f-a2", "name": "db-01", "status": "SHUTOFF", "created": "2026-10-02T03:00:00Z",
     "OS-EXT-AZ:availability_zone": "bkk-1b", "flavor": {"id": "f-4"}, "metadata": {},
     "addresses": {"prod-net": [{"addr": "10.20.0.12", "version": 4, "OS-EXT-IPS:type": "fixed"}]}},
]}


def test_openstack_servers_become_instances():
    a, b = cloud.parse_openstack(NOVA)
    assert a == {"instance_id": "9e5f-a1", "name": "web-01", "state": "running", "private_ips": ["10.20.0.11"],
                 "public_ips": ["203.0.113.7"], "networks": ["prod-net"], "zone": "bkk-1a", "size": "c2.m4",
                 "created_at": "2026-10-01T03:00:00Z", "tags": {"team": "esg"}}
    assert b["state"] == "stopped" and b["size"] == "f-4" and b["public_ips"] == []


# ------------------------------------------------------------------ VMware Cloud Director (query type=vm)
VCD = {"record": [
    {"name": "app-01", "status": "POWERED_ON", "href": "https://vcd.example/api/vApp/vm-1111", "ipAddress": "172.16.5.21",
     "networkName": "org-routed", "vdcName": "GIST-VDC", "containerName": "esg-vapp", "guestOs": "Ubuntu Linux (64-bit)",
     "isVAppTemplate": False, "dateCreated": "2026-09-30T10:00:00.000+07:00"},
    {"name": "tmpl", "status": "POWERED_OFF", "href": "https://vcd.example/api/vAppTemplate/vm-2", "isVAppTemplate": True},
    {"name": "batch-01", "status": "POWERED_OFF", "href": "https://vcd.example/api/vApp/vm-2222", "ipAddress": "",
     "networkName": "org-routed", "vdcName": "GIST-VDC", "isVAppTemplate": False},
]}


def test_vcd_vms_become_instances_and_templates_are_skipped():
    out = cloud.parse_vcd(VCD)
    assert [i["instance_id"] for i in out] == ["vm-1111", "vm-2222"]
    assert out[0]["state"] == "running" and out[0]["private_ips"] == ["172.16.5.21"] and out[0]["zone"] == "GIST-VDC"
    assert out[0]["tags"] == {"vapp": "esg-vapp", "os": "Ubuntu Linux (64-bit)"}
    assert out[1]["state"] == "stopped" and out[1]["private_ips"] == []


# ------------------------------------------------------------------ Apache CloudStack (listVirtualMachines)
CS = {"listvirtualmachinesresponse": {"count": 1, "virtualmachine": [
    {"id": "cs-1", "name": "i-2-31-VM", "displayname": "api-01", "state": "Running", "zonename": "BKK",
     "serviceofferingname": "Medium", "created": "2026-09-01T00:00:00+0700", "publicip": "198.51.100.9",
     "nic": [{"ipaddress": "10.1.1.5", "networkname": "tier-app", "isdefault": True}],
     "tags": [{"key": "env", "value": "prod"}]}]}}


def test_cloudstack_vms_become_instances():
    (i,) = cloud.parse_cloudstack(CS)
    assert i["name"] == "api-01" and i["state"] == "running" and i["private_ips"] == ["10.1.1.5"]
    assert i["public_ips"] == ["198.51.100.9"] and i["networks"] == ["tier-app"] and i["tags"] == {"env": "prod"}
    assert cloud.parse_cloudstack({"listvirtualmachinesresponse": {}}) == []


# ------------------------------------------------------------------ AWS EC2 (DescribeInstances, XML)
EC2 = """<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/"><reservationSet><item><instancesSet>
<item><instanceId>i-0abc</instanceId><instanceState><code>16</code><name>running</name></instanceState>
<privateIpAddress>172.31.4.10</privateIpAddress><ipAddress>54.1.2.3</ipAddress><instanceType>t3.medium</instanceType>
<placement><availabilityZone>ap-southeast-7a</availabilityZone></placement><launchTime>2026-10-03T01:02:03.000Z</launchTime>
<vpcId>vpc-1</vpcId><subnetId>subnet-9</subnetId><tagSet><item><key>Name</key><value>esg-web</value></item>
<item><key>team</key><value>esg</value></item></tagSet></item>
<item><instanceId>i-0def</instanceId><instanceState><code>80</code><name>stopped</name></instanceState>
<instanceType>t3.small</instanceType><placement><availabilityZone>ap-southeast-7b</availabilityZone></placement></item>
</instancesSet></item></reservationSet></DescribeInstancesResponse>"""


def test_ec2_instances_become_instances():
    a, b = cloud.parse_ec2(EC2)
    assert a["instance_id"] == "i-0abc" and a["name"] == "esg-web" and a["state"] == "running"
    assert a["private_ips"] == ["172.31.4.10"] and a["public_ips"] == ["54.1.2.3"] and a["networks"] == ["vpc-1/subnet-9"]
    assert a["tags"] == {"Name": "esg-web", "team": "esg"} and a["zone"] == "ap-southeast-7a"
    assert b["name"] == "i-0def" and b["state"] == "stopped" and b["private_ips"] == []


def test_sigv4_matches_the_aws_documented_example():
    # docs.aws.amazon.com "Create a signed AWS API request", GET IAM ListUsers example
    h = cloud.sigv4_headers("GET", "https://iam.amazonaws.com/?Action=ListUsers&Version=2010-05-08",
                            region="us-east-1", service="iam", access_key="AKIDEXAMPLE",
                            secret_key="wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY", amz_date="20150830T123600Z",
                            extra={"content-type": "application/x-www-form-urlencoded; charset=utf-8"})
    assert h["Authorization"].endswith("Signature=5d672d79c15b13162d9279b0855cfba6789a8edb4c82c400e06b5924a6f2b5d7")
    assert "SignedHeaders=content-type;host;x-amz-date" in h["Authorization"]


# ------------------------------------------------------------------ Azure (ARM: VMs + NICs + public IPs)
AZ_VMS = {"value": [{"id": "/subscriptions/s/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/esg-vm",
                     "name": "esg-vm", "location": "southeastasia", "zones": ["1"], "tags": {"team": "esg"},
                     "properties": {"hardwareProfile": {"vmSize": "Standard_B2s"}, "timeCreated": "2026-10-04T00:00:00Z",
                                    "instanceView": {"statuses": [{"code": "ProvisioningState/succeeded"},
                                                                  {"code": "PowerState/deallocated"}]},
                                    "networkProfile": {"networkInterfaces": [{"id": "/x/nic-1"}]}}}]}
AZ_NICS = {"value": [{"id": "/x/nic-1", "properties": {"ipConfigurations": [{"properties": {
    "privateIPAddress": "10.0.0.4", "subnet": {"id": "/x/virtualNetworks/vnet-a/subnets/default"},
    "publicIPAddress": {"id": "/x/pip-1"}}}]}}]}
AZ_PIPS = {"value": [{"id": "/x/pip-1", "properties": {"ipAddress": "20.1.2.3"}}]}


def test_azure_vms_join_their_nics_and_public_ips():
    (i,) = cloud.parse_azure(AZ_VMS, AZ_NICS, AZ_PIPS)
    assert i["name"] == "esg-vm" and i["state"] == "stopped" and i["size"] == "Standard_B2s"
    assert i["private_ips"] == ["10.0.0.4"] and i["public_ips"] == ["20.1.2.3"] and i["networks"] == ["vnet-a/default"]
    assert i["zone"] == "southeastasia-1"


# ------------------------------------------------------------------ GCP (instances aggregatedList)
GCE = {"items": {"zones/asia-southeast1-a": {"instances": [
    {"id": "1234", "name": "gke-node", "status": "RUNNING", "creationTimestamp": "2026-10-05T00:00:00.000-07:00",
     "zone": "https://www.googleapis.com/compute/v1/projects/p/zones/asia-southeast1-a",
     "machineType": "https://www.googleapis.com/compute/v1/projects/p/zones/asia-southeast1-a/machineTypes/e2-medium",
     "labels": {"env": "prod"}, "networkInterfaces": [{"networkIP": "10.148.0.2",
     "network": "https://www.googleapis.com/compute/v1/projects/p/global/networks/default",
     "accessConfigs": [{"natIP": "203.0.113.10"}]}]}]},
    "zones/asia-southeast1-b": {"warning": {"code": "NO_RESULTS_ON_PAGE"}}}}


def test_gcp_instances_become_instances():
    (i,) = cloud.parse_gcp(GCE)
    assert i == {"instance_id": "1234", "name": "gke-node", "state": "running", "private_ips": ["10.148.0.2"],
                 "public_ips": ["203.0.113.10"], "networks": ["default"], "zone": "asia-southeast1-a", "size": "e2-medium",
                 "created_at": "2026-10-05T00:00:00.000-07:00", "tags": {"env": "prod"}}


# ------------------------------------------------------------------ sync: what changed since the last read
def _i(iid, state="running", ips=("10.0.0.1",)):
    return {"instance_id": iid, "name": iid, "state": state, "private_ips": list(ips)}


def test_diff_reports_added_removed_and_state_changes():
    before = {"a": _i("a"), "b": _i("b"), "c": _i("c", "running")}
    d = cloud.diff(before, [_i("a"), _i("c", "stopped"), _i("d")])
    assert [x["instance_id"] for x in d["added"]] == ["d"]
    assert [x["instance_id"] for x in d["removed"]] == ["b"]
    assert d["changed"] == [{"instance_id": "c", "name": "c", "from": "running", "to": "stopped"}]


def test_diff_on_first_sync_marks_everything_added_and_nothing_removed():
    d = cloud.diff({}, [_i("a")])
    assert len(d["added"]) == 1 and d["removed"] == [] and d["changed"] == []


# ------------------------------------------------------------------ match to our agents, and what the pair means
HOSTS = [{"name": "esg360-prod", "ip_addresses": ["10.148.0.2"], "status": "down"},
         {"name": "web-01", "ip_addresses": ["192.168.9.9"], "status": "ok"}]


def test_instances_match_agents_by_ip_then_by_name():
    inst = [_i("1234", ips=("10.148.0.2",)), {**_i("x", ips=()), "name": "web-01"}, _i("y", ips=("10.9.9.9",))]
    out = cloud.match(inst, HOSTS)
    assert [o["aiops_host"] for o in out] == ["esg360-prod", "web-01", None]


def test_cloud_state_and_agent_state_tell_what_is_really_wrong():
    assert cloud.verdict("running", "down")["code"] == "agent_silent"       # machine on, our agent not reporting
    assert cloud.verdict("stopped", "down")["code"] == "stopped_in_cloud"    # someone stopped it in the console
    assert cloud.verdict("running", "ok")["code"] == "ok"
    assert cloud.verdict("running", None)["code"] == "not_monitored"
    assert cloud.verdict("deleted", None)["code"] == "gone"


# ------------------------------------------------------------------ secrets never leave the server in clear
def test_secret_box_round_trips_and_the_stored_form_is_not_the_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOPS_SECRET_KEY_FILE", str(tmp_path / "k"))
    monkeypatch.delenv("AIOPS_SECRET_KEY", raising=False)
    blob = cloud.seal({"password": "s3cret"})
    assert "s3cret" not in blob and cloud.unseal(blob) == {"password": "s3cret"}
    assert oct(os.stat(tmp_path / "k").st_mode)[-3:] == "600"


def test_public_view_of_an_account_masks_every_secret():
    acc = {"id": 1, "provider": "openstack", "name": "GIST", "config": {"auth_url": "https://x/v3"}, "secret": "blob",
           "status": "ok", "last_sync_at": 1.0, "last_error": None}
    pub = cloud.public(acc)
    assert "secret" not in pub and pub["has_secret"] is True and pub["config"] == {"auth_url": "https://x/v3"}


def test_provider_config_is_validated_before_anything_is_stored():
    assert cloud.validate("openstack", {"auth_url": "https://cloud.gist/v3"},
                          {"application_credential_id": "i", "application_credential_secret": "s"}) == []
    errs = cloud.validate("openstack", {"auth_url": "http://plain/v3"}, {})
    assert any("https" in e for e in errs) and any("credential" in e for e in errs)
    assert cloud.validate("nope", {}, {}) == ["unknown provider 'nope'"]


# ------------------------------------------------------------------ fetchers speak each API (mocked transport)
def test_openstack_fetch_uses_an_application_credential_and_the_catalog():
    seen = []

    def handler(req: httpx.Request):
        seen.append((req.method, req.url.path, req.headers.get("X-Auth-Token")))
        if req.url.path == "/v3/auth/tokens":
            body = json.loads(req.content)
            assert body["auth"]["identity"]["methods"] == ["application_credential"]
            return httpx.Response(201, headers={"X-Subject-Token": "tok"}, json={"token": {"catalog": [
                {"type": "compute", "endpoints": [{"interface": "public", "region": "bkk", "url": "https://nova.gist/v2.1"}]}]}})
        if req.url.path == "/v2.1/servers/detail":
            return httpx.Response(200, json=NOVA)
        return httpx.Response(404)

    out = asyncio.run(cloud.fetch("openstack", {"auth_url": "https://keystone.gist/v3", "region": "bkk"},
                                  {"application_credential_id": "id", "application_credential_secret": "s"},
                                  transport=httpx.MockTransport(handler)))
    assert [i["name"] for i in out] == ["web-01", "db-01"]
    assert ("GET", "/v2.1/servers/detail", "tok") in seen


def test_vcd_fetch_trades_the_api_token_for_a_bearer_and_queries_vms():
    def handler(req: httpx.Request):
        if req.url.path == "/oauth/tenant/gist-org/token":
            assert b"refresh_token=rt" in req.content
            return httpx.Response(200, json={"access_token": "bear"})
        if req.url.path == "/api/query":
            assert req.headers["Authorization"] == "Bearer bear" and req.url.params["type"] == "vm"
            return httpx.Response(200, json=VCD)
        return httpx.Response(404)

    out = asyncio.run(cloud.fetch("vcd", {"url": "https://vcd.gist", "org": "gist-org"}, {"api_token": "rt"},
                                  transport=httpx.MockTransport(handler)))
    assert [i["instance_id"] for i in out] == ["vm-1111", "vm-2222"]


def test_a_rejected_credential_is_a_clear_error_not_a_crash():
    def handler(req):
        return httpx.Response(401, json={"error": "unauthorized"})
    try:
        asyncio.run(cloud.fetch("openstack", {"auth_url": "https://k/v3"},
                                {"application_credential_id": "i", "application_credential_secret": "s"},
                                transport=httpx.MockTransport(handler)))
    except cloud.CloudError as e:
        assert "401" in str(e) and "credential" in str(e).lower()
    else:
        raise AssertionError("expected CloudError")


# ------------------------------------------------------------------ the Fleet map: cloud networks as hubs
def test_graph_puts_each_cloud_network_under_its_account_and_links_matched_agents():
    accounts = [{"id": 7, "name": "GIST Starships", "provider": "openstack", "status": "ok"}]
    inst = cloud.match([
        {**_i("a", ips=("10.148.0.2",)), "networks": ["prod-net"], "zone": "bkk-1a"},
        {**_i("b", "stopped", ips=("10.20.0.12",)), "networks": ["prod-net"], "zone": "bkk-1a"},
        {**_i("c", ips=()), "networks": [], "zone": None}], HOSTS)
    for i in inst:
        i["account_id"] = 7
    g = cloud.graph(accounts, inst)
    ids = {n["id"]: n for n in g["nodes"]}
    assert ids["cloud:7"]["kind"] == "cloud" and ids["cloud:7"]["label"] == "GIST Starships"
    assert ids["hub:GIST Starships / prod-net"]["kind"] == "hub" and ids["hub:GIST Starships / prod-net"]["cloud"] is True
    assert ("host:esg360-prod", "hub:GIST Starships / prod-net") in {(l["source"], l["target"]) for l in g["links"]}
    vm = ids["cloud:7:b"]
    assert vm["kind"] == "cloud instance" and vm["status"] == "stopped" and vm["ip"] == "10.20.0.12"
    assert vm["verdict"]["code"] == "not_monitored" and vm["provider"] == "openstack"
    assert ("cloud:7:c", "hub:GIST Starships / (no network)") in {(l["source"], l["target"]) for l in g["links"]}
    assert ("hub:GIST Starships / prod-net", "cloud:7") in {(l["source"], l["target"]) for l in g["links"]}
    assert "host:esg360-prod" not in ids          # the host node itself comes from the agent side of the graph
    assert g["matched"] == {"esg360-prod": {"account": "GIST Starships", "state": "running", "verdict": "agent_silent"}}


# ------------------------------------------------------------------ Proxmox VE (GIST Starships Cloud runs on it)
PVE_RES = {"data": [
    {"type": "qemu", "vmid": 101, "name": "esg-app", "node": "pve-bkk-2", "pool": "cust-esg", "status": "running",
     "maxcpu": 4, "maxmem": 8589934592, "tags": "prod;esg"},
    {"type": "qemu", "vmid": 102, "name": "esg-db", "node": "pve-bkk-3", "pool": "cust-esg", "status": "stopped",
     "maxcpu": 2, "maxmem": 4294967296},
    {"type": "qemu", "vmid": 900, "name": "other-tenant", "node": "pve-bkk-2", "pool": "cust-other", "status": "running"},
    {"type": "node", "node": "pve-bkk-2", "status": "online"},
]}
PVE_NET = {101: {"result": [
    {"name": "lo", "ip-addresses": [{"ip-address": "127.0.0.1", "ip-address-type": "ipv4"}]},
    {"name": "eth0", "hardware-address": "bc:24:11:aa:bb:cc", "ip-addresses": [
        {"ip-address": "10.50.0.21", "ip-address-type": "ipv4"}, {"ip-address": "fe80::1", "ip-address-type": "ipv6"}]},
    {"name": "eth1", "ip-addresses": [{"ip-address": "103.10.20.30", "ip-address-type": "ipv4"}]}]}}
PVE_CFG = {101: {"net0": "virtio=BC:24:11:AA:BB:CC,bridge=vmbr10,tag=210"},
           102: {"net0": "virtio=BC:24:11:00:00:02,bridge=vmbr10", "ipconfig0": "ip=10.50.0.22/24,gw=10.50.0.1"}}


def test_proxmox_vms_in_the_pool_become_instances_with_guest_agent_ips():
    a, b = cloud.parse_proxmox(PVE_RES, PVE_NET, PVE_CFG, pool="cust-esg")
    assert a == {"instance_id": "101", "name": "esg-app", "state": "running", "private_ips": ["10.50.0.21"],
                 "public_ips": ["103.10.20.30"], "networks": ["vmbr10.210"], "zone": "pve-bkk-2", "size": "4 vCPU / 8 GB",
                 "created_at": None, "tags": {"pool": "cust-esg", "tags": "prod;esg"}}
    # no guest agent answer (it is stopped): fall back to the cloud-init address in its config
    assert b["state"] == "stopped" and b["private_ips"] == ["10.50.0.22"] and b["networks"] == ["vmbr10"]


def test_proxmox_without_a_pool_lists_every_vm_the_token_can_see():
    assert [i["instance_id"] for i in cloud.parse_proxmox(PVE_RES, {}, {})] == ["101", "102", "900"]


def test_proxmox_fetch_uses_the_api_token_and_asks_the_guest_agent_only_for_running_vms():
    asked = []

    def handler(req: httpx.Request):
        assert req.headers["Authorization"] == "PVEAPIToken=esg@pve!fleet=sec"
        p = req.url.path
        if p == "/api2/json/cluster/resources":
            return httpx.Response(200, json=PVE_RES)
        if p.endswith("/agent/network-get-interfaces"):
            asked.append(p)
            return httpx.Response(200, json={"data": PVE_NET[101]})
        if p.endswith("/config"):
            vmid = int(p.split("/")[-2])
            return httpx.Response(200, json={"data": PVE_CFG.get(vmid, {})})
        return httpx.Response(404)

    out = asyncio.run(cloud.fetch("proxmox", {"url": "https://pve.starships.cloud:8006", "pool": "cust-esg"},
                                  {"token_id": "esg@pve!fleet", "token_secret": "sec"}, transport=httpx.MockTransport(handler)))
    assert [i["name"] for i in out] == ["esg-app", "esg-db"] and out[0]["public_ips"] == ["103.10.20.30"]
    assert asked == ["/api2/json/nodes/pve-bkk-2/qemu/101/agent/network-get-interfaces"]


def test_merge_adds_cloud_nodes_once_and_tags_agent_hosts_with_their_cloud():
    base = {"nodes": [{"id": "internet", "kind": "internet"}, {"id": "host:esg360-prod", "kind": "connected", "status": "down"}],
            "links": [{"source": "host:esg360-prod", "target": "hub:10.0.0.0/24", "kind": "cable"}]}
    cg = {"nodes": [{"id": "cloud:7", "kind": "cloud"}, {"id": "internet", "kind": "internet"}],
          "links": [{"source": "cloud:7", "target": "internet", "kind": "cable"},
                    {"source": "host:esg360-prod", "target": "hub:10.0.0.0/24", "kind": "cable"}],
          "matched": {"esg360-prod": {"account": "GIST", "state": "running", "verdict": "agent_silent"}}}
    g = cloud.merge(base, cg)
    assert [n["id"] for n in g["nodes"]] == ["internet", "host:esg360-prod", "cloud:7"]
    assert len(g["links"]) == 2
    assert g["nodes"][1]["cloud"] == {"account": "GIST", "state": "running", "verdict": "agent_silent"}
