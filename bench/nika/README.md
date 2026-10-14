# AIOps One on NIKA: network troubleshooting

[NIKA](https://github.com/sands-lab/nika) (sands-lab, MIT licence, SIGCOMM NGNO 2025) is a network-incident benchmark.
It builds real emulated networks (FRR routers, Linux hosts, bind DNS, web servers) in Docker with Kathará, injects one
of 75 kinds of fault, lets an agent investigate through MCP tools (`exec_shell` on any device, a pingmesh, packet
capture, curl, iperf), and scores the agent's answer against the fault it injected.

This folder plugs an AIOps One-style agent into it, so the network side of AIOps One (topology, reachability, config
drift) is measured on a public benchmark instead of a demo we built ourselves.

## Removable by design

Nothing outside `bench/nika/` changes, and nothing in the AIOps One stack imports it.

| Piece | Job | Depends on |
|---|---|---|
| `netagent/evidence.py` | the read-only commands run on each device, and parsers for their output | nothing |
| `netagent/skills.py` | rules: device facts -> findings -> NIKA catalog ids | `evidence` |
| `netagent/agent.py` | glue: calls NIKA's MCP tools, hands text to the two above | NIKA |
| `nika-agent.yaml` | registers the agent with NIKA (`nika agent add`) | - |
| `cases.yaml` | the 12 cases we run, copied from NIKA's pool with NIKA's ground truth | - |
| `scripts/` | install into `~/nika-bench`, and remove it all again | Docker |

`./bench.sh down` closes every lab, deletes NIKA's images, the model alias and `~/nika-bench`. To drop the feature
entirely, delete this folder.

## How the agent investigates

The same steps every time, like an AIOps One skill playbook:

1. **Pingmesh** across all endpoints: who cannot reach whom (symptoms only).
2. **One read-only probe per device**: addresses, link state, routes, does the default gateway answer, resolver,
   queueing disciplines (delay / loss / rate limits), firewall DROP/REJECT rules, CPU by process, DNS server state and
   zones, BGP neighbours.
3. **DNS lookups** from each client to each DNS server, timed.
4. **Rules** turn those facts into findings, strongest first: `3` = the config or state itself is wrong (a DOWN link,
   a resolver that is not a DNS server, a DROP rule for ICMP), `2` = a strong sign (slow answers, CPU taken by
   processes that should be idle), `1` = a symptom only.
5. **Submit** the strongest tier only, mapped to the resource and fault ids NIKA lists. Ids NIKA does not list are
   never sent.

No LLM is involved and the agent never reads NIKA's ground truth: it sees only what the MCP tools return.

## Fair comparison

* **Baseline** = NIKA's own `byo.langgraph` ReAct agent, unchanged, on the same small model the AIOps One stack runs
  (`qwen2.5:1.5b` in Ollama, 16k context). It decides every command itself.
* **Same cases, same scorer**: both agents run `cases.yaml` through `nika benchmark run`, and `report.py` only reads
  NIKA's `eval_metrics.json`.
* **What is tuned**: the rules were written for the nine fault kinds after `healthy` in `cases.yaml`, knowing what
  those faults are: from NIKA's one-line fault descriptions, the lab layout (bind DNS, FRR, resolv.conf) and the case
  parameters in `cases.yaml` (for example, the CPU case runs 4 stress workers), not from NIKA's injection code. The
  last two (`mtu_mismatch`, `bgp_asn_misconfig`) are held out: no rule names them. Read the scores on those nine as
  "the playbook works on a live network", and the held-out two as "what happens on a fault it was not written for".
* **Model size**: a 1.5B model is a weak baseline for an agent that must choose its own commands. Read the gap as
  "fixed playbook vs a small model", not as "playbook vs LLM agents in general".

## Run

On a Linux host with Docker (the capstone VM):

```bash
./bench.sh up        # NIKA into ~/nika-bench, register the agent, model alias (~5 min; labs build images on first use)
./bench.sh test      # unit tests, no lab needed
./bench.sh run       # both agents on cases.yaml; AGENTS="aiopsone-net" to run one
./bench.sh report    # results/REPORT.md
./bench.sh down      # remove everything
```

One case deploys ~7 containers (1 super-spine, 2 spines, 2 leaves, DNS, web server, client) with 0.5 CPU / 256 MB
each.
