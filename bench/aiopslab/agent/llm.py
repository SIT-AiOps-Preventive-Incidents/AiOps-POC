"""LLM access, swappable: anything with complete(messages) -> str. The default talks to any OpenAI-compatible endpoint
(Ollama, vLLM, OpenAI ...). NoLLM makes the agent run on rules alone, to measure what the LLM adds."""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Protocol


class LLM(Protocol):
    name: str

    def complete(self, messages: list[dict], max_tokens: int = 300) -> str: ...


class OpenAICompatLLM:
    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str | None = None, timeout: int = 300):
        self.base_url = (base_url or os.environ.get("BENCH_LLM_URL", "http://localhost:11434/v1")).rstrip("/")
        self.model = model or os.environ.get("BENCH_LLM_MODEL", "qwen2.5:1.5b")
        self.api_key = api_key or os.environ.get("BENCH_LLM_KEY", "none")
        self.timeout = timeout
        self.name = self.model

    def complete(self, messages: list[dict], max_tokens: int = 300) -> str:
        body = json.dumps({"model": self.model, "messages": messages, "temperature": 0, "max_tokens": max_tokens}).encode()
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body,
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)["choices"][0]["message"]["content"]


class NoLLM:
    name = "rules-only"

    def complete(self, messages: list[dict], max_tokens: int = 300) -> str:
        return ""
