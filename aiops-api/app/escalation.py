"""Playbook escalations: a fix nobody approved within the playbook's wait is sent out again, once, as an escalation."""
import asyncio
import logging
import time

from . import automation, automation_store as st, notify

log = logging.getLogger(__name__)


async def tick():
    pbs = st.playbooks()
    if not pbs:
        return
    for iid, pid in automation.due_escalations(st.waiting_for_approval(), pbs, st.escalated(), time.time()):
        st.mark_escalated(iid, pid)      # first, so a failing webhook never sends it twice
        await notify.send(iid, "escalation")


async def loop():
    while True:
        try:
            await tick()
        except Exception as e:
            log.warning("escalation check failed: %s", e)
        await asyncio.sleep(60)
