"""Outside-in checks: AIOps calls a website it cannot install anything on, and records each call as a trace."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import synthetic  # noqa: E402


def test_answer_is_ok_up_to_4xx_and_error_from_5xx():
    assert synthetic.outcome(200, None) == ("ok", None)
    assert synthetic.outcome(404, None) == ("ok", None)        # the site answered; a missing page is not an outage
    assert synthetic.outcome(503, None) == ("error", "HTTP 503")
    assert synthetic.outcome(None, "ConnectTimeout") == ("error", "ConnectTimeout")


def test_check_becomes_a_server_span_of_the_checked_service():
    res = {"url": "https://34.2.129.3:3000/", "status": 200, "error": None, "start": 1000.0, "ms": 312.5,
           "final_url": "https://34.2.129.3:3000/login", "cert_days_left": 6}
    body = synthetic.to_otlp("esg360", res, trace_id="a" * 32, span_id="b" * 16)
    rs = body["resourceSpans"][0]
    attrs = {a["key"]: list(a["value"].values())[0] for a in rs["resource"]["attributes"]}
    assert attrs["service.name"] == "esg360"
    span = rs["scopeSpans"][0]["spans"][0]
    assert span["name"] == "GET /" and span["kind"] == 2                   # SERVER: counted as the service's own requests
    assert int(span["endTimeUnixNano"]) - int(span["startTimeUnixNano"]) == 312_500_000
    assert span["status"] == {}
    sattrs = {a["key"]: list(a["value"].values())[0] for a in span["attributes"]}
    assert sattrs["http.response.status_code"] == 200 and sattrs["aiops.check"] == "outside-in"


def test_failed_check_is_an_error_span_with_the_reason():
    res = {"url": "https://34.2.129.3:3000/", "status": None, "error": "ConnectTimeout", "start": 1000.0, "ms": 8000.0,
           "final_url": None, "cert_days_left": None}
    span = synthetic.to_otlp("esg360", res, trace_id="a" * 32, span_id="b" * 16)["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span["status"] == {"code": 2, "message": "ConnectTimeout"}


def test_log_line_says_what_happened():
    ok = {"url": "https://x/", "status": 200, "error": None, "ms": 312.5, "final_url": "https://x/login", "cert_days_left": 6}
    assert synthetic.log_line(ok) == "GET https://x/ -> 200 in 312 ms (ended at https://x/login) · certificate valid 6 more days"
    bad = {"url": "https://x/", "status": None, "error": "ConnectTimeout", "ms": 8000.0, "final_url": None, "cert_days_left": None}
    assert synthetic.log_line(bad) == "GET https://x/ failed after 8000 ms: ConnectTimeout"


def test_only_plain_web_addresses_are_accepted():
    assert synthetic.valid_url("https://34.2.129.3:3000/")
    assert synthetic.valid_url("http://esg.example.com/health")
    for bad in ("ftp://x/", "file:///etc/passwd", "javascript:alert(1)", "https://", "not a url"):
        assert not synthetic.valid_url(bad), bad
