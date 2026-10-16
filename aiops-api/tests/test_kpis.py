"""Overview speed numbers: the AI's own run time and the fix after approval are reported apart from MTTR."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import repo  # noqa: E402


def test_kpis_report_investigation_and_fix_time_separately(monkeypatch):
    seen = {}

    def one(sql, args=None):
        seen["sql"] = sql
        return {"open": 2, "total": 40, "awaiting_approval": 2, "mttd_s": 30.0, "mtta_s": 1476.04,
                "mttr_s": 52560.44, "investigate_s": 82.26, "fix_s": 66.04}

    monkeypatch.setattr(repo.db, "one", one)
    monkeypatch.setattr(repo.db, "val", lambda *a, **k: None)
    k = repo.kpis()
    assert k["investigate_s"] == 82.3 and k["fix_s"] == 66.0
    assert "analysis_ms" in seen["sql"]            # the agent's measured run time, not analyzed_at - detected_at
    assert "verified_at" in seen["sql"] and "decided_at" in seen["sql"]   # approve -> verified
