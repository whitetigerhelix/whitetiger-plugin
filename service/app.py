"""FastAPI service for AI Groove Writer.

Endpoints:
  GET  /health   → {"ok": true}
  POST /generate → GenerateResponse (mock or real LLM)
  GET  /presets  → list of available presets
  GET  /usage    → usage statistics for LLM credit tracking

Canonical references:
  - Docs/Architecture.md
  - Docs/JSON_Contract.md
"""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI

from cache import cache_get, cache_key, cache_put
from llm_provider import estimate_cost, get_provider
from mock_grooves import get_mock_groove
from models import GenerateRequest, GenerateResponse, MidiPlan
from presets import get_preset, list_presets
from prompts import build_system_prompt, build_user_prompt
from usage import get_usage_summary, log_usage
from validation import parse_llm_response

load_dotenv()

log = logging.getLogger(__name__)

MAX_LLM_RETRIES = 3
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

app = FastAPI(
    title="AI Groove Writer Service",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/presets")
def presets_list() -> list[dict]:
    return list_presets()


@app.get("/usage")
def usage_stats() -> dict:
    """Return usage statistics for LLM credit tracking."""
    return get_usage_summary()


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    start_time = time.monotonic()

    # Resolve preset (for default values and prompt template)
    preset = get_preset(req.preset_id)
    if preset is None:
        return GenerateResponse(
            ok=False,
            error=f"Unknown preset_id: {req.preset_id}",
        )

    # Mock mode: return hardcoded groove
    is_mock = os.getenv("SERVICE_MOCK", "1") == "1"

    if is_mock:
        summary, notes = get_mock_groove(req.preset_id, req.clip.bars)
        plan = MidiPlan(
            version=1,
            mode=req.mode,
            bars=req.clip.bars,
            time_sig_num=req.clip.time_sig_num,
            time_sig_den=req.clip.time_sig_den,
            notes=notes,
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_usage(
            provider="mock",
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            preset_id=req.preset_id,
            bars=req.clip.bars,
            cached=False,
            duration_ms=duration_ms,
        )
        return GenerateResponse(ok=True, summary=summary, plan=plan)

    # --- Real LLM path ---

    # 1. Check disk cache
    key = cache_key(req)
    cached_response = cache_get(key)
    if cached_response is not None:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_usage(
            provider="cache",
            model="cache",
            prompt_tokens=0,
            completion_tokens=0,
            preset_id=req.preset_id,
            bars=req.clip.bars,
            cached=True,
            duration_ms=duration_ms,
        )
        return cached_response

    # 2. Build prompts (use effective seed = seed + variation)
    effective_seed = req.seed + req.variation
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(preset, req, effective_seed=effective_seed)

    # 3. Get LLM provider
    try:
        provider = get_provider()
    except ValueError as e:
        return GenerateResponse(ok=False, error=str(e))

    # 4. Call LLM with retry on parse failure
    last_error = ""
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            result = provider.generate(
                system_prompt, user_prompt, timeout=LLM_TIMEOUT_SECONDS,
            )
        except Exception as e:
            last_error = f"LLM call failed: {e}"
            log.warning("LLM call attempt %d failed: %s", attempt, e)
            continue

        try:
            plan = parse_llm_response(result.text, req.clip)
        except ValueError as e:
            last_error = f"LLM response parse failed (attempt {attempt}): {e}"
            log.warning("Parse attempt %d failed: %s", attempt, e)
            continue

        # Success — build response, cache it, log usage
        note_count = len(plan.notes)
        cost = estimate_cost(result.model, result.prompt_tokens, result.completion_tokens)
        summary = (
            f"{note_count} notes, {plan.bars} bars | "
            f"{result.provider}:{result.model} | "
            f"{result.prompt_tokens}+{result.completion_tokens} tokens | "
            f"${cost:.4f}"
        )

        response = GenerateResponse(ok=True, summary=summary, plan=plan)

        cache_put(key, response)

        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_usage(
            provider=result.provider,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            estimated_cost_usd=cost,
            preset_id=req.preset_id,
            bars=req.clip.bars,
            cached=False,
            duration_ms=duration_ms,
        )

        return response

    # All retries exhausted — try cached fallback
    # Look for a cached response from the base variation (variation=0)
    if req.variation > 0:
        from copy import copy
        fallback_req = copy(req)
        object.__setattr__(fallback_req, "variation", 0)
        fallback_key = cache_key(fallback_req)
        fallback = cache_get(fallback_key)
        if fallback is not None:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            log_usage(
                provider="cache-fallback",
                model="cache-fallback",
                prompt_tokens=0,
                completion_tokens=0,
                preset_id=req.preset_id,
                bars=req.clip.bars,
                cached=True,
                duration_ms=duration_ms,
            )
            fallback.summary = f"[fallback] {fallback.summary}"
            return fallback

    return GenerateResponse(
        ok=False,
        error=f"Failed after {MAX_LLM_RETRIES} attempts. Last error: {last_error}",
    )
