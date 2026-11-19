"""Insights: what the incident history means for the business, in plain sentences.

Each finding is one number, one headline, one line of meaning, an action that goes somewhere, and its basis - the
arithmetic and the assumptions behind the number, so a manager can trust it or change the assumption (Settings:
downtime_cost_per_hour, manual_rca_minutes). Findings are ordered by what most deserves attention first.
Pure: the caller passes the rows in, so it is tested without a database.
"""
from __future__ import annotations

from collections import Counter

DAY, HOUR = 86400.0, 3600.0
CLOSED = ("resolved", "closed")
CURRENCY = {"THB": "฿", "USD": "$", "EUR": "€"}


def _money(v: float, cur: str) -> str:
    sym = CURRENCY.get(cur, cur + " ")
    return f"{sym}{v / 1e6:.1f}M" if v >= 1e6 else f"{sym}{round(v):,}"


def _days(s: float) -> str:
    d = s / DAY
    return f"{d:.0f} days" if d >= 1.5 else f"{s / HOUR:.0f} hours"


def compute(incidents: list[dict], feedback: list[dict], runbook_uses: int, unmonitored_near_problems: int,
            settings: dict, now: float) -> list[dict]:
    if not incidents:
        return [{"id": "no_data", "tone": "neutral", "value": "–", "headline": "No incidents yet",
                 "detail": "Insights appear once RadarOps has seen a few incidents. Run a demo scenario to see them now.",
                 "action": {"label": "Demo scenarios", "to": "/scenarios"}, "basis": "Nothing to count yet."}]
    cost_h = float(settings.get("downtime_cost_per_hour") or 0)
    manual_min = float(settings.get("manual_rca_minutes") or 45)
    cur = settings.get("currency") or "THB"
    month = [i for i in incidents if now - i["detected_at"] <= 30 * DAY]
    out = []

    # 1. fixes the AI has ready that nobody approved
    waiting = [i for i in incidents if i["status"] == "awaiting_approval"]
    if waiting:
        oldest = max(now - i["detected_at"] for i in waiting)
        out.append({"id": "approval_backlog", "tone": "action", "rank": 100 + len(waiting), "value": len(waiting),
                    "headline": f"{len(waiting)} fix{'es' if len(waiting) != 1 else ''} ready, waiting for a person",
                    "detail": f"The AI tested each one in a dry run. The oldest has waited {_days(oldest)}; every hour it waits is "
                              "an hour the problem stays live.",
                    "action": {"label": "Review fixes", "to": "/problems"},
                    "basis": "Incidents in 'awaiting approval'. Wait = now minus detection time."})

    # 2. one service behind a big share of incidents
    counts = Counter(i["entity_name"] for i in month or incidents)
    total = sum(counts.values())
    if total >= 5:
        name, n = counts.most_common(1)[0]
        share = n / total
        if share >= 0.25 and n >= 3:
            out.append({"id": "repeat_offender", "tone": "bad", "rank": 80 + share * 20, "value": f"{share:.0%}",
                        "headline": f"{name} causes {share:.0%} of incidents",
                        "detail": f"{n} of {total} incidents in the last 30 days. A lasting fix here removes more toil than anything else.",
                        "action": {"label": f"Open {name}", "to": f"/services/{name}"},
                        "basis": f"Incidents per affected service or host over 30 days; {name} has {n}."})

    # 3. what resolved incidents cost this month (open ones are not priced: a waiting fix has its own finding)
    done = [i for i in month if i["status"] in CLOSED and i.get("resolved_at")]
    hours = sum((i["resolved_at"] - i["detected_at"]) / HOUR for i in done)
    if cost_h > 0 and hours > 0:
        out.append({"id": "downtime_cost", "tone": "warn", "rank": 70, "value": _money(hours * cost_h, cur),
                    "headline": "What incidents cost in the last 30 days",
                    "detail": f"Time from detection to fix across {len(done)} resolved incident{'s' if len(done) != 1 else ''}, priced at your cost of an hour of disruption.",
                    "action": {"label": "Change the hourly cost", "to": "/settings"},
                    "basis": f"{hours:.1f} h of incidents x {_money(cost_h, cur)} per hour (Settings: downtime cost per hour)."})

    # 4. engineer time the AI saved
    resolved = [i for i in incidents if i["status"] in CLOSED and i.get("analysis_ms")]
    saved_min = sum(max(0.0, manual_min - i["analysis_ms"] / 60000) for i in resolved)
    if saved_min >= 30:
        out.append({"id": "hours_saved", "tone": "ok", "rank": 60, "value": f"{saved_min / 60:.1f} h",
                    "headline": "Engineer time the AI saved on root cause",
                    "detail": f"{len(resolved)} incidents investigated in about a minute each instead of by hand.",
                    "action": {"label": "See resolved incidents", "to": "/problems"},
                    "basis": f"Per resolved incident: {manual_min:.0f} min manual investigation minus the AI's measured time."})

    # 5. machines we cannot see, next to a problem
    if unmonitored_near_problems > 0:
        out.append({"id": "coverage_gap", "tone": "warn", "rank": 55, "value": unmonitored_near_problems,
                    "headline": "Unmonitored machines next to an active problem",
                    "detail": "They share a network with something failing right now. If the cause is there, the AI cannot see it.",
                    "action": {"label": "Monitor them", "to": "/network"},
                    "basis": "Fleet machines without our agent, on a network where a monitored machine has an open incident."})

    # 6. trend: this week against last week
    this_w = sum(1 for i in incidents if now - i["detected_at"] <= 7 * DAY)
    last_w = sum(1 for i in incidents if 7 * DAY < now - i["detected_at"] <= 14 * DAY)
    if last_w:
        ch = (this_w - last_w) / last_w
        out.append({"id": "weekly_trend", "tone": "bad" if ch > 0.1 else "ok" if ch < -0.1 else "neutral", "rank": 40,
                    "value": f"{ch:+.0%}", "headline": f"{this_w} incidents this week, {last_w} the week before",
                    "detail": "Rising: look for a recent change. Falling: the fixes are holding.",
                    "action": {"label": "Incidents", "to": "/problems"}, "basis": "Incidents detected in the last 7 days vs the 7 before."})

    # 7. fixes reused without a fresh investigation
    if runbook_uses:
        out.append({"id": "runbook_reuse", "tone": "ok", "rank": 30, "value": runbook_uses,
                    "headline": "Fixes reused from what the team taught the AI",
                    "detail": "A problem seen before is solved from a learned runbook instead of starting over.",
                    "action": {"label": "Runbooks", "to": "/runbooks"}, "basis": "Sum of uses across enabled runbooks."})

    # 8. how much the AI is being taught
    rated = len(feedback)
    if rated < max(5, len(incidents) // 4):
        out.append({"id": "rate_more", "tone": "info", "rank": 20, "value": f"{rated} of {len(incidents)}",
                    "headline": "Analyses rated by your team",
                    "detail": "Ratings are how the AI learns what a good answer looks like here. Rating a few resolved incidents sharpens it.",
                    "action": {"label": "Rate resolved incidents", "to": "/problems"},
                    "basis": "Incidents with a star rating, out of all incidents."})

    out.sort(key=lambda f: -f.pop("rank"))
    return out
