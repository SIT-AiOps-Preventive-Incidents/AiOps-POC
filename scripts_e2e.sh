#!/bin/bash
# usage: scripts_e2e.sh <scenario>  — inject, wait for RCA, approve recommended action, wait for verification
API=localhost:8080
j() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }
before=$(curl -s $API/api/incidents | j 'print(max([x["id"] for x in d] or [0]))')
curl -s -XPOST $API/api/chaos/$1 >/dev/null; echo "[$1] injected at $(date +%T)"
for i in $(seq 1 60); do
  sleep 10
  id=$(curl -s $API/api/incidents | j "print(min([x['id'] for x in d if x['id']>$before] or [0]))")
  [ "$id" != 0 ] || continue
  st=$(curl -s $API/api/incidents/$id | j 'print(d["status"])')
  echo "  t=$((i*10))s P$id $st"
  [ "$st" = awaiting_approval ] && break
done
curl -s $API/api/incidents/$id | j '
print("  title     :", d["title"]); print("  skill     :", d["skill"], "| path:", d["path"], "| llm_ok:", d["llm_ok"], "| analysis", d["analysis_ms"]//1000, "s")
print("  root cause:", d["root_cause"]); print("  summary   :", (d["summary"] or "")[:400]); print("  action    :", d["action"]["label"])
print("  guard     :", [s["title"] for s in d["steps"] if s["kind"]=="guard"])
print("  owner     :", d.get("owner"))
for c in d.get("candidates") or []: print("  dry run   :", c["label"], "->", "PASS" if c["dry_run"]["ok"] else "FAIL", [ (k["name"], k["ok"]) for k in c["dry_run"]["checks"]])'
curl -s -XPOST $API/api/incidents/$id/approve -H 'Content-Type: application/json' -d '{"approver":"e2e-test","owner_confirmed":true}' | j 'print("  executed  :", d["execution"]["result"])'
sleep 80
curl -s $API/api/incidents/$id | j 'print("  final     :", d["status"], d["execution"].get("verification"))'
