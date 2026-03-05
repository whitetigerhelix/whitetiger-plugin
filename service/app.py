"""FastAPI service for AI Groove Writer.

Endpoints:
  GET  /health        → {"ok": true}
  POST /generate      → GenerateResponse (mock or real LLM)
  POST /surprise      → SurpriseResponse (LLM-generated prompt + controls)
  GET  /presets       → list of available presets
  GET  /usage         → usage statistics for LLM credit tracking
  POST /config        → update runtime config (provider, keys, mock mode)
  GET  /config/status → config status (no secrets)
  POST /shutdown      → graceful shutdown

Canonical references:
  - Docs/Architecture.md
  - Docs/JSON_Contract.md
  - Docs/Plan_Server_Management.md
"""

from __future__ import annotations

import logging
import os
import time
import json

from dotenv import load_dotenv
from fastapi import FastAPI

from cache import cache_get, cache_key, cache_put
from llm_provider import estimate_cost, get_provider
from mock_grooves import get_mock_groove
from models import (
    ConfigRequest,
    ConfigStatusResponse,
    Controls,
    GenerateRequest,
    GenerateResponse,
    MidiPlan,
    RefineRequest,
    RefineResponse,
    SurpriseRequest,
    SurpriseResponse,
    SurpriseResult,
)
from presets import get_preset, list_presets
from prompts import (
    build_refine_prompt,
    build_surprise_system_prompt,
    build_surprise_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from usage import get_usage_summary, log_usage
from validation import parse_llm_response
import runtime_config

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


def _extract_json_object(text: str) -> dict:
    text = text.strip()
    fence_start = text.find("```")
    if fence_start >= 0:
        fence_end = text.rfind("```")
        if fence_end > fence_start:
            text = text[fence_start + 3:fence_end].strip()
            if text.startswith("json"):
                text = text[4:].strip()

    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    text = text[brace_start:i + 1]
                    break

    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("Expected JSON object")
    return obj


@app.post("/surprise", response_model=SurpriseResponse)
def surprise(req: SurpriseRequest) -> SurpriseResponse:
    start_time = time.monotonic()

    preset = get_preset(req.preset_id)
    if preset is None:
        return SurpriseResponse(ok=False, error=f"Unknown preset_id: {req.preset_id}")

    is_mock = (runtime_config.get_config("SERVICE_MOCK") or "1") == "1"

    if is_mock:
        suggestion = (
            f"Emotional groove idea for {preset.name}: syncopated breakbeat with ghost snare movement, "
            f"offbeat percussion texture, and a gentle phrase lift near the end."
        )
        result = SurpriseResult(
            prompt=suggestion,
            controls=Controls(**preset.defaults.model_dump()),
            sound_suggestion="Try a textured breakbeat kit with airy hats and soft snare tails.",
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_usage(
            provider="mock",
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            preset_id=req.preset_id,
            bars=8,
            cached=False,
            duration_ms=duration_ms,
        )
        return SurpriseResponse(ok=True, summary="surprise prompt ready (mock)", surprise=result)

    try:
        provider = get_provider()
    except ValueError as e:
        return SurpriseResponse(ok=False, error=str(e))

    system_prompt = build_surprise_system_prompt()
    user_prompt = build_surprise_user_prompt(preset, req.color)

    last_error = ""
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            llm = provider.generate(
                system_prompt,
                user_prompt,
                timeout=LLM_TIMEOUT_SECONDS,
                model_override=req.model,
            )
            obj = _extract_json_object(llm.text)
            prompt_text = str(obj.get("prompt", "")).strip()
            controls_obj = obj.get("controls", {})
            sound_suggestion = str(obj.get("sound_suggestion", "")).strip()

            if not prompt_text:
                raise ValueError("Missing surprise prompt text")

            controls = Controls(**controls_obj)
            result = SurpriseResult(
                prompt=prompt_text,
                controls=controls,
                sound_suggestion=sound_suggestion,
            )

            cost = estimate_cost(llm.model, llm.prompt_tokens, llm.completion_tokens)
            duration_ms = int((time.monotonic() - start_time) * 1000)
            log_usage(
                provider=llm.provider,
                model=llm.model,
                prompt_tokens=llm.prompt_tokens,
                completion_tokens=llm.completion_tokens,
                estimated_cost_usd=cost,
                preset_id=req.preset_id,
                bars=8,
                cached=False,
                duration_ms=duration_ms,
            )

            return SurpriseResponse(
                ok=True,
                summary=(
                    f"surprise ready | {llm.provider}:{llm.model} | "
                    f"{llm.prompt_tokens}+{llm.completion_tokens} tokens | ${cost:.4f}"
                ),
                surprise=result,
            )
        except Exception as e:
            last_error = f"Surprise parse/generation failed (attempt {attempt}): {e}"
            log.warning(last_error)

    return SurpriseResponse(
        ok=False,
        error=f"Failed after {MAX_LLM_RETRIES} attempts. Last error: {last_error}",
    )


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
    is_mock = (runtime_config.get_config("SERVICE_MOCK") or "1") == "1"

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
    system_prompt = build_system_prompt(req.mode)
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
                system_prompt, user_prompt,
                timeout=LLM_TIMEOUT_SECONDS,
                model_override=req.model,
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


@app.post("/refine", response_model=RefineResponse)
def refine(req: RefineRequest) -> RefineResponse:
    """Edit an existing pattern based on a natural-language instruction."""
    start_time = time.monotonic()

    is_mock = (runtime_config.get_config("SERVICE_MOCK") or "1") == "1"
    if is_mock:
        # In mock mode, just return the notes unchanged
        plan = MidiPlan(
            version=1,
            mode=req.mode,
            bars=req.clip.bars,
            time_sig_num=req.clip.time_sig_num,
            time_sig_den=req.clip.time_sig_den,
            notes=[],
        )
        try:
            from models import NoteEvent
            for n in req.current_notes:
                plan.notes.append(NoteEvent(**n))
        except Exception:
            pass
        return RefineResponse(ok=True, summary="refine (mock — notes unchanged)", plan=plan)

    try:
        provider = get_provider()
    except ValueError as e:
        return RefineResponse(ok=False, error=str(e))

    from prompts import REFINE_SYSTEM_PROMPT
    system_prompt = REFINE_SYSTEM_PROMPT
    user_prompt = build_refine_prompt(
        current_notes=req.current_notes,
        instruction=req.instruction,
        clip=req.clip,
        mode=req.mode,
        key=req.key,
        scale=req.scale,
    )

    last_error = ""
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            result = provider.generate(
                system_prompt, user_prompt,
                timeout=LLM_TIMEOUT_SECONDS,
                model_override=req.model,
            )
        except Exception as e:
            last_error = f"LLM call failed: {e}"
            log.warning("Refine attempt %d failed: %s", attempt, e)
            continue

        try:
            plan = parse_llm_response(result.text, req.clip)
            plan.mode = req.mode
        except ValueError as e:
            last_error = f"Refine parse failed (attempt {attempt}): {e}"
            log.warning("Refine parse attempt %d failed: %s", attempt, e)
            continue

        note_count = len(plan.notes)
        cost = estimate_cost(result.model, result.prompt_tokens, result.completion_tokens)
        summary = (
            f"refined {note_count} notes, {plan.bars} bars | "
            f"{result.provider}:{result.model} | "
            f"{result.prompt_tokens}+{result.completion_tokens} tokens | "
            f"${cost:.4f}"
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_usage(
            provider=result.provider,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            estimated_cost_usd=cost,
            preset_id=req.preset_id or "refine",
            bars=req.clip.bars,
            cached=False,
            duration_ms=duration_ms,
        )

        return RefineResponse(ok=True, summary=summary, plan=plan)

    return RefineResponse(
        ok=False,
        error=f"Refine failed after {MAX_LLM_RETRIES} attempts. Last error: {last_error}",
    )


# --- Config and shutdown endpoints ---

@app.post("/config")
def update_config(req: ConfigRequest) -> dict:
    """Update runtime config. Never logs or returns secret values."""
    updated = 0
    mapping = {
        "provider": ("LLM_PROVIDER", req.provider),
        "azure_endpoint": ("AZURE_OPENAI_ENDPOINT", req.azure_endpoint),
        "azure_api_key": ("AZURE_OPENAI_API_KEY", req.azure_api_key),
        "azure_deployment": ("AZURE_OPENAI_DEPLOYMENT", req.azure_deployment),
        "azure_api_version": ("AZURE_OPENAI_API_VERSION", req.azure_api_version),
        "anthropic_api_key": ("ANTHROPIC_API_KEY", req.anthropic_api_key),
        "anthropic_model": ("ANTHROPIC_MODEL", req.anthropic_model),
    }
    for field_name, (config_key, value) in mapping.items():
        if value is not None:
            runtime_config.set_config(config_key, str(value))
            updated += 1

    if req.mock_mode is not None:
        runtime_config.set_config("SERVICE_MOCK", "1" if req.mock_mode else "0")
        updated += 1

    status = runtime_config.get_config_status()
    return {"ok": True, "updated": updated, **status}


@app.get("/config/status", response_model=ConfigStatusResponse)
def config_status() -> ConfigStatusResponse:
    """Return current config status (no secrets)."""
    return ConfigStatusResponse(**runtime_config.get_config_status())


@app.post("/shutdown")
def shutdown() -> dict:
    """Graceful shutdown after a short delay so response can be sent."""
    import signal
    import threading

    def _delayed_shutdown():
        time.sleep(0.5)
        try:
            os.kill(os.getpid(), signal.SIGINT)
        except Exception:
            pass

    if not getattr(app.state, "_testing", False):
        threading.Thread(target=_delayed_shutdown, daemon=True).start()
    return {"ok": True, "message": "shutting down"}
