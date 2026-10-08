#!/bin/bash
# usage: scripts_e2e.sh <scenario>  - inject, wait for the RCA, approve the recommended fix as the owner, wait for verification
API=localhost:8080/api/v1
j() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }
before=$(curl -s "$API/incidents" | j 'print(max([x["id"] for x in d] or [0]))')
curl -s -X POST "$API/scenarios/$1/runs" >/dev/null; echo "[$1] injected at $(date +%T)"
id=0
for i in $(seq 1 60); do
  sleep 10
  id=$(curl -s "$API/incidents" | j "print(min([x['id'] for x in d if x['id']>$before] or [0]))")
  [ "$id" != 0 ] || continue
  st=$(curl -s "$API/incidents/$id" | j 'print(d["status"])')
  echo "  t=$((i*10))s P$id $st"
  [ "$st" = awaiting_approval ] && break
done
curl -s "$API/incidents/$id" | j '
print("  title     :", d["title"]); print("  skill     :", d["skill_id"], "| path:", d["path"], "| llm_ok:", d["llm_ok"], "| analysis", (d["analysis_ms"] or 0)//1000, "s")
print("  root cause:", d["root_cause"]); print("  owner     :", d["owner"])
for c in d["candidates"]: print("  dry run   :", c["label"], "->", "PASS" if c["dry_run"]["ok"] else "FAIL", [(k["name"], k["ok"]) for k in c["dry_run"]["checks"]])'
curl -s -X POST "$API/incidents/$id/approvals" -H 'Content-Type: application/json' \
  -d '{"decision":"approve","approver":"e2e-test","owner_confirmed":true}' | j 'print("  executed  :", (d.get("approval") or {}).get("execution") or d.get("error"))'
sleep 90
curl -s "$API/incidents/$id" | j 'print("  final     :", d["status"], ((d.get("approval") or {}).get("execution") or {}).get("verified"))'
