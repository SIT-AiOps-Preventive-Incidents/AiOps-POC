"""report.py on a fake results tree shaped like NIKA's trial folders."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import report  # noqa: E402


def trial(root, agent, name, gt, metrics, sub=None):
    d = root / agent / "trials" / f"{name}__t01"
    d.mkdir(parents=True)
    (d / "ground_truth.json").write_text(json.dumps(gt))
    (d / "eval_metrics.json").write_text(json.dumps(metrics))
    if sub is not None:
        (d / "submission.json").write_text(json.dumps(sub))


def test_report_table_and_means(tmp_path):
    ok = {"detection_score": 1.0, "localization_f1": 1.0, "fault_type_f1": 1.0, "rca_f1": 1.0}
    trial(tmp_path, "aiopsone-net", "a", {"problem": "dns_service_down", "is_anomaly": True}, ok)
    trial(tmp_path, "aiopsone-net", "b", {"is_anomaly": False, "root_causes": []}, ok)
    trial(tmp_path, "byo.langgraph", "a", {"problem": "dns_service_down", "is_anomaly": True},
          {"detection_score": 1.0, "localization_f1": 0.0, "fault_type_f1": 0.0, "rca_f1": 0.0})
    text = report.main(str(tmp_path))
    assert "| healthy | 1.00 / 1.00 / 1.00 | not run |" in text
    assert "| dns_service_down | 1.00 / 1.00 / 1.00 | 1.00 / 0.00 / 0.00 |" in text
    assert "| aiopsone-net | 2 | 1.00 | 1.00 | 1.00 | 1.00 |" in text
    assert "| byo.langgraph | 1 | 1.00 | 0.00 | 0.00 | 0.00 |" in text
    assert (tmp_path / "REPORT.md").exists()
