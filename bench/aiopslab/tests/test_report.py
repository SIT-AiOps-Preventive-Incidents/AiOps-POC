"""report.py turns result files into the comparison table; checked on hand-made results."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import report  # noqa: E402


def write(d, agent, pid, **rec):
    os.makedirs(d / agent, exist_ok=True)
    (d / agent / f"{pid}.json").write_text(json.dumps({"agent": agent, "problem": pid, "wall_s": 10, **rec}))


def test_counts_passes_per_task_and_agent(tmp_path):
    write(tmp_path, "aiopsone", "x-detection-1", results={"Detection Accuracy": "Correct"})
    write(tmp_path, "aiopsone", "x-localization-1", results={"success": True})
    write(tmp_path, "baseline", "x-detection-1", results={"Detection Accuracy": "Incorrect"})
    write(tmp_path, "baseline", "x-localization-1", error="TimeoutError: cluster")
    text = report.main(str(tmp_path))
    assert "| aiopsone | 1/1 | 1/1 | 0/0 | 0/0 | 2/2 |" in text
    assert "| baseline | 0/1 | 0/1 | 0/0 | 0/0 | 0/2 |" in text
    assert "error (10 s)" in text and (tmp_path / "REPORT.md").exists()


def test_noop_problem_counts_as_detection():
    assert report.task_of("noop_detection_hotel_reservation-1") == "detection"
