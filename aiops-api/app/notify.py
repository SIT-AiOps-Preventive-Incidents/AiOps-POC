"""Microsoft Teams notifications (Incoming Webhook / Workflows) — every send is logged in-app too."""
import os

import httpx

from . import db, repo

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8080")

COLORS = {"detected": "attention", "rca_ready": "warning", "resolved": "good", "rejected": "default",
          "remediation_failed": "attention"}
TITLES = {"detected": "Problem detected", "rca_ready": "RCA + dry run ready - owner approval required",
          "resolved": "Problem resolved", "rejected": "Remediation rejected",
          "remediation_failed": "Remediation did not fix the problem"}


def _card(inc: dict, event: str) -> dict:
    link = f"{PUBLIC_URL}/#/problems/{inc['id']}"
    facts = [{"title": "Entity", "value": f"{inc['entity_type']}: {inc['entity']}"},
             {"title": "Severity", "value": inc.get("severity") or "-"},
             {"title": "Status", "value": inc.get("status") or "-"},
             {"title": "Owner", "value": inc.get("owner") or "-"}]
    body = [
        {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "color": COLORS.get(event, "default"),
         "text": f"P-{inc['id']} {TITLES.get(event, event)}"},
        {"type": "TextBlock", "text": inc["title"], "wrap": True},
        {"type": "FactSet", "facts": facts},
    ]
    if inc.get("root_cause"):
        body.append({"type": "TextBlock", "wrap": True, "text": f"**Root cause:** {inc['root_cause']}"})
    if inc.get("action") and event == "rca_ready":
        dr = inc["action"].get("dry_run") or {}
        body.append({"type": "TextBlock", "wrap": True,
                     "text": f"**Proposed action:** {inc['action'].get('label', '')} - dry run "
                             f"{'passed' if dr.get('ok') else 'FAILED'} "
                             f"({sum(c['ok'] for c in dr.get('checks', []))}/{len(dr.get('checks', []))} checks). "
                             f"Nothing has been changed; waiting for {inc.get('owner') or 'the owner'} to approve."})
    return {"type": "message", "attachments": [{
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "type": "AdaptiveCard",
                    "version": "1.4", "body": body,
                    "actions": [{"type": "Action.OpenUrl", "title": "Open in AIOps", "url": link}]}}]}


async def send(inc: dict | int, event: str):
    if isinstance(inc, int):
        inc = repo.incident(inc)
    url = db.setting("teams_webhook").strip()
    payload = _card(inc, event)
    status = "skipped: no Teams webhook configured"
    if url:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(url, json=payload)
            status = f"sent: HTTP {r.status_code}"
        except Exception as e:
            status = f"failed: {e}"[:200]
    repo.add_notification(inc.get("id") or None, event, status, payload)
