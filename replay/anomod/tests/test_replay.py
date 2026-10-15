"""The replayer on a tiny AnoMod-shaped folder: loading, OTLP encoding, network following, fault hand-back."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import replay  # noqa: E402

HEAD = "trace_id,span_id,parent_span_id,service,operation,start_time,duration_us,http_status_code,http_method,http_url,component,tags,logs\n"
NORMAL = HEAD + (
    "aaaa000000000001,aaaa000000000001,aaaa000000000001,nginx-web-server,/wrk2-api/post/compose,2025-11-03 22:10:00.000000,900,200,POST,http://x/wrk2-api/post/compose,nginx,{},\n"
    "aaaa000000000001,b000000000000002,aaaa000000000001,compose-post-service,compose_post_client,2025-11-03 22:10:00.100000,700,,,,,{},\n"
    "aaaa000000000001,b000000000000003,b000000000000002,media-service,compose_media_server,2025-11-03 22:10:00.200000,300,,,,,{},\n"
    "cccc000000000009,cccc000000000009,cccc000000000009,nginx-web-server,/wrk2-api/home-timeline/read,2025-11-03 22:12:00.000000,500,500,GET,http://x/h,nginx,{},\n")
LOG = ("[2025-Nov-03 22:09:00.000000] <info>: (Main.cpp:1:main) before the run, dropped\n"
       "[2025-Nov-03 22:10:01.000000] <error>: (Handler.h:9:Compose) Failed to connect media-service\n"
       "[2025-Nov-03 22:10:02.000000] <info>: (Handler.h:10:Compose) ok\n")


def make(tmp, name="Normal_Baseline_20251103_220228"):
    t = tmp / "trace_data" / f"{name}_traces_2025-11-03_22-22-55"
    t.mkdir(parents=True)
    (t / "all_traces.csv").write_text(NORMAL)
    l = tmp / "log_data" / f"{name}_logs_2025-11-03_22-22-55"
    l.mkdir(parents=True)
    (l / "ComposePostService_.log").write_text(LOG)
    return tmp


def test_names_and_services():
    assert replay.short_name("/x/Svc_Kill_Media_20251104_000111_traces_2025-11-04_00-21-42") == "Svc_Kill_Media"
    assert replay.service_of_logfile("HomeTimelineService_.log") == "home-timeline-service"
    assert replay.service_of_logfile("NginxThrift_.log") == "nginx-web-server"


def test_load_run_offsets_and_logs(tmp_path):
    run = replay.load_run(str(make(tmp_path)), "Normal_Baseline")
    assert [round(s.offset, 1) for s in run.spans] == [0.0, 0.1, 0.2, 120.0]
    assert run.duration > 120
    assert run.spans[-1].error is True and run.spans[0].status == 200
    assert [l.severity for l in replay.load_logs(str(tmp_path / "log_data" / os.listdir(tmp_path / "log_data")[0]),
                                                  replay.parse_ts("2025-11-03 22:10:00"), 300, sample=1)] == ["error", "info"]


def test_kinds_and_otlp_shape(tmp_path):
    run = replay.load_run(str(make(tmp_path)), "Normal_Baseline")
    by = {s.span: s for s in run.spans}
    kinds = [replay.span_kind(s, by.get(s.parent)) for s in run.spans]
    assert kinds == [2, 3, 2, 2]          # gateway server, client call, callee server, root server
    body = replay.encode_spans([(s, k, False) for s, k in zip(run.spans, kinds)],
                               {s.span: 10**18 for s in run.spans}, "f" * 16)
    spans = {o["name"]: o for rs in body["resourceSpans"] for o in rs["scopeSpans"][0]["spans"]}
    root = spans["/wrk2-api/post/compose"]
    assert len(root["traceId"]) == 32 and root["traceId"].startswith("f" * 16) and "parentSpanId" not in root
    assert spans["compose_media_server"]["parentSpanId"] == "b000000000000002"
    assert spans["/wrk2-api/home-timeline/read"]["status"]["code"] == 2
    svc = {a["value"]["stringValue"] for rs in body["resourceSpans"] for a in rs["resource"]["attributes"] if a["key"] == "service.name"}
    assert svc == {"nginx-web-server", "compose-post-service", "media-service"}


def test_cut_off_service_vanishes_and_its_callers_fail(tmp_path):
    run = replay.load_run(str(make(tmp_path)), "Normal_Baseline")
    trace = [s for s in run.spans if s.trace == "aaaa000000000001"]
    out = replay.apply_network(trace, {"media-service"})
    assert [(s.service, failed) for s, failed in out] == [("nginx-web-server", True), ("compose-post-service", True)]
    assert all(not f for _, f in replay.apply_network(trace, {"user-service"}))
    body = replay.encode_spans([(s, 2, f) for s, f in out], {s.span: 1 for s, _ in out}, "0" * 16)
    codes = [a["value"]["intValue"] for rs in body["resourceSpans"] for o in rs["scopeSpans"][0]["spans"]
             for a in o["attributes"] if a["key"] == "http.status_code"]
    assert codes == ["503"]                # the gateway answered 503 instead of the recorded 200


def test_player_plays_a_fault_then_returns_to_normal(tmp_path, monkeypatch):
    root = make(tmp_path)
    import shutil
    src = root / "trace_data" / "Normal_Baseline_20251103_220228_traces_2025-11-03_22-22-55"
    shutil.copytree(src, root / "trace_data" / "Svc_Kill_Media_20251104_000111_traces_2025-11-04_00-21-42")
    sent = []
    monkeypatch.setattr(replay, "post", lambda url, body: sent.append(url))
    p = replay.Player(str(root))
    assert p.normal_name == "Normal_Baseline" and p.faults == ["Svc_Kill_Media"]
    p.play("Svc_Kill_Media", wait=True)
    assert p.status()["playing"] == "Svc_Kill_Media"
    p.tick()
    assert sent and sent[0].endswith("/v1/traces")
    p.started -= 10_000                     # the fault run is over
    p.tick()
    assert p.status()["normal"] is True
    try:
        p.play("nope")
        raise AssertionError("unknown case accepted")
    except KeyError:
        pass
