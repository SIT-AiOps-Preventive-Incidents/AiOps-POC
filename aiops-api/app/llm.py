"""Small local LLM via Ollama (CPU). Always asked for JSON; callers keep a rule-based fallback."""
import json
import os
import re
import time

import httpx

from . import db

OLLAMA = os.environ.get("OLLAMA_URL", "http://ollama:11434")
# The model runs on the same host it monitors; the detector uses this to avoid
# flagging the platform's own inference as a CPU incident.
BUSY = {"n": 0, "last_end": 0.0}


def busy_recently(grace_s: float = 75) -> bool:
    return BUSY["n"] > 0 or time.time() - BUSY["last_end"] < grace_s


async def chat_json(system: str, user: str, max_tokens: int = 400, timeout: float = 240) -> tuple[dict | None, dict]:
    model = db.setting("llm_model")
    meta = {"model": model, "ok": False, "ms": 0}
    t0 = time.time()
    BUSY["n"] += 1
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(f"{OLLAMA}/api/chat", json={
                "model": model, "stream": False, "format": "json",
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": 0.2, "num_predict": max_tokens, "num_ctx": 2048, "num_thread": 3},
            })
            r.raise_for_status()
            body = r.json()
            text = body.get("message", {}).get("content", "")
            meta.update(ms=int((time.time() - t0) * 1000), tokens=body.get("eval_count"), raw=text[:1500])
            m = re.search(r"\{.*\}", text, re.S)
            out = json.loads(m.group(0) if m else text)
            meta["ok"] = isinstance(out, dict)
            return (out if meta["ok"] else None), meta
    except Exception as e:
        meta.update(ms=int((time.time() - t0) * 1000), error=f"{type(e).__name__}: {e}"[:300])
        return None, meta
    finally:
        BUSY["n"] -= 1
        BUSY["last_end"] = time.time()


async def status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            tags = (await c.get(f"{OLLAMA}/api/tags")).json().get("models", [])
        return {"up": True, "models": [m["name"] for m in tags], "active": db.setting("llm_model")}
    except Exception as e:
        return {"up": False, "error": str(e), "active": db.setting("llm_model")}
