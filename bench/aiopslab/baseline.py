"""AIOpsLab's own baseline agent (clients/generic_openai.py), adapted only where CPU-only hardware forces it.

Its client hard-codes a 60 s timeout per call and asks for up to 16,000 output tokens - fine on a GPU endpoint,
impossible for a 1.5B model on 3 CPU cores with a 16k context. Only those two numbers change here (900 s, 1,024 tokens,
which is plenty for one shell command). Prompt, temperature, top_p and the step loop stay exactly as published.
"""
from __future__ import annotations

import os

TIMEOUT_S = 900
MAX_TOKENS = 1024


def make_baseline():
    from clients.generic_openai import GenericOpenAIAgent

    agent = GenericOpenAIAgent(base_url=os.environ["BENCH_LLM_URL"], model=os.environ["BENCH_LLM_MODEL"],
                               api_key=os.environ.get("BENCH_LLM_KEY", "none"))
    llm = agent.llm

    def inference(payload):
        hit = llm.cache.get_from_cache(payload) if llm.cache is not None else None
        if hit is not None:
            return hit
        r = llm.client.chat.completions.create(messages=payload, model=llm.model, max_tokens=MAX_TOKENS, temperature=0.5,
                                               top_p=0.95, frequency_penalty=0.0, presence_penalty=0.0, n=1,
                                               timeout=TIMEOUT_S, stop=[])
        return [c.message.content for c in r.choices]

    llm.inference = inference
    return agent
