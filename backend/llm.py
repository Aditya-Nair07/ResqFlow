import json

import httpx

from config import (
    AICREDITS_API_KEY,
    AICREDITS_BASE_URL,
    AICREDITS_MODEL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
from schemas import SimulationSnapshot


def _prompt(kind: str, snapshot: SimulationSnapshot) -> str:
    payload = snapshot.model_dump()
    if kind == "briefing":
        task = (
            "Write a concise disaster-response situation briefing for a coordinator. "
            "Use only facts from the JSON. 5-8 short bullet lines. Plain text, no markdown."
        )
    else:
        task = (
            "Write a concise operational incident report for disaster coordinators. "
            "Use only facts from the JSON. Include resolved/pending counts, utilization, "
            "recent traces, and one bottleneck note. Plain text, no markdown."
        )
    return f"{task}\n\nSimulation snapshot JSON:\n{json.dumps(payload, indent=2)}"


async def generate_text(kind: str, snapshot: SimulationSnapshot) -> str:
    prompt = _prompt(kind, snapshot)
    provider = LLM_PROVIDER

    if provider == "gemini":
        return await _gemini(prompt)
    if provider == "openai":
        return await _openai_compatible(prompt, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
    if provider == "aicredits":
        return await _openai_compatible(prompt, AICREDITS_API_KEY, AICREDITS_BASE_URL, AICREDITS_MODEL)
    if provider in ("claude", "anthropic"):
        return await _anthropic(prompt)
    if provider == "openrouter":
        return await _openrouter(prompt)
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


async def _gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, params={"key": GEMINI_API_KEY}, json=body)
        resp.raise_for_status()
        data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def openai_compatible_chat(prompt: str) -> str:
    if LLM_PROVIDER == "aicredits":
        return await _openai_compatible(prompt, AICREDITS_API_KEY, AICREDITS_BASE_URL, AICREDITS_MODEL)
    if LLM_PROVIDER == "openai":
        return await _openai_compatible(prompt, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
    if LLM_PROVIDER == "openrouter":
        return await _openrouter(prompt)
    raise ValueError(f"Unsupported provider for chat: {LLM_PROVIDER}")


async def _openai_compatible(prompt: str, api_key: str, base_url: str, model: str) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


async def _anthropic(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 800,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return data["content"][0]["text"].strip()


async def _openrouter(prompt: str) -> str:
    model = OPENROUTER_MODEL or "google/gemini-2.0-flash-001"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
