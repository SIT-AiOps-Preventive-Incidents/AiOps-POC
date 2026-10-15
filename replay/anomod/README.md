# AnoMod SocialNetwork as the demo application

[AnoMod](https://doi.org/10.5281/zenodo.18342898) (Ping, Mazhar, Wang, Song, Mäntylä; MSR'26; CC BY 4.0) recorded a
real SocialNetwork deployment (DeathStarBench, 12 C++ microservices behind nginx) during one normal run and 12 runs
with a fault injected: resource (CPU, disk, network loss), service (a container killed), database (a Redis cache
capped) and code (a service stopped). This folder plays those recordings into AIOps One as live telemetry, in place
of the shop we built ourselves.

```bash
replay/anomod/switch.sh anomod   # fetch AnoMod once (202 MB), stop the shop, start the replay
replay/anomod/switch.sh shop     # back to the shop
```

## How it works

* `anomod-replay` loops the normal run and, when a scenario starts, plays one fault run, then returns to normal.
  Every span and log line is re-stamped to now and sent over OTLP to the OpenTelemetry collector, so it lands in
  Tempo, Loki and the span metrics like any traced app. AIOps One's detector, service map and agent are unchanged:
  what they find, they find themselves.
* `aiops-api` with `DEMO_DATASET=anomod` registers the 12 SocialNetwork services and offers the 12 fault runs under
  Demo scenarios (`anomod:<case>`); Reset returns the replay to the normal run.
* `sn-<service>` are 12 tiny hosts, one per service, that the network lab (`netlab/`) puts behind its switches, so
  the Network page shows SocialNetwork from the core router down to each service. When a link breaks, the replay
  follows: a service the Network page reports as cut off stops answering and calls to it fail (HTTP 503).

## What is real and what is not

* Real: every request, its timing, its errors and every log line come from AnoMod's recording of a running system.
* Re-timed: timestamps are shifted to now; the order and spacing inside a run are kept.
* Sampled: all warning and error log lines are sent; 1 in 20 info lines (`INFO_LOG_SAMPLE`), to keep Loki light.
* Not recorded by AnoMod and so not replayed: container CPU and memory per service. Faults that only show in those
  (a Redis cache limit, disk I/O) leave little for AIOps One to see; `bench/anomod` scores this honestly.
* The network-following behaviour is ours, not AnoMod's: it only applies while a netlab fault is active.

Tests: `python3 -m pytest -q replay/anomod/tests`.
