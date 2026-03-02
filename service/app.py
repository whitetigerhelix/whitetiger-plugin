"""FastAPI service for AI Groove Writer.

Endpoints:
  GET  /health   → {"ok": true}
  POST /generate → GenerateResponse (mock mode for now)
  GET  /presets  → list of available presets
  GET  /usage    → usage statistics for LLM credit tracking

Canonical references:
  - Docs/Architecture.md
  - Docs/JSON_Contract.md
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI

from mock_grooves import get_mock_groove
from models import GenerateRequest, GenerateResponse, MidiPlan
from presets import get_preset, list_presets
from usage import get_usage_summary, log_usage

load_dotenv()

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

    # TODO: LLM integration (Milestone 4)
    # 1. Build prompt from preset template + user prompt + controls
    # 2. Check cache
    # 3. Call LLM provider
    # 4. Parse and validate response
    # 5. Log usage with real token counts
    # 6. Return GenerateResponse
    return GenerateResponse(
        ok=False,
        error="LLM integration not yet implemented. Set SERVICE_MOCK=1 for mock mode.",
    )
