"""Pydantic v2 models for the AI Groove Writer JSON contract.

Canonical reference: Docs/JSON_Contract.md
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClipInfo(BaseModel):
    bars: int = Field(default=8, ge=1, le=64)
    time_sig_num: int = Field(default=4, ge=1, le=12)
    time_sig_den: int = Field(default=4, ge=1, le=16)
    bpm: float = Field(default=130, ge=40, le=240)


class Controls(BaseModel):
    density: float = Field(default=0.75, ge=0, le=1)
    complexity: float = Field(default=0.65, ge=0, le=1)
    swing: float = Field(default=0.35, ge=0, le=1)
    humanize_ms: float = Field(default=8, ge=0, le=25)
    velocity_jitter: int = Field(default=6, ge=0, le=15)


class GenerateRequest(BaseModel):
    prompt: str
    preset_id: str
    mode: Literal["drums"] = "drums"
    clip: ClipInfo = Field(default_factory=ClipInfo)
    controls: Controls = Field(default_factory=Controls)
    seed: int = 12345
    variation: int = Field(default=0, ge=0)
    drum_map: Literal["gm"] = "gm"
    model: str | None = None
    allowed_pitches: list[int] | None = Field(default=None)
    instrument_hints: list[str] | None = Field(default=None)


class NoteEvent(BaseModel):
    pitch: int = Field(ge=0, le=127)
    start_beats: float = Field(ge=0)
    dur_beats: float = Field(gt=0)
    vel: int = Field(ge=1, le=127)
    mute: int = Field(default=0, ge=0, le=1)


class MidiPlan(BaseModel):
    version: int = 1
    mode: Literal["drums"] = "drums"
    bars: int
    time_sig_num: int
    time_sig_den: int
    notes: list[NoteEvent] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    ok: bool = True
    summary: str = ""
    plan: MidiPlan | None = None
    error: str | None = None


class SurpriseRequest(BaseModel):
    preset_id: str
    color: float = Field(default=0.5, ge=0, le=1)
    model: str | None = None


class SurpriseResult(BaseModel):
    prompt: str
    controls: Controls
    sound_suggestion: str = ""


class SurpriseResponse(BaseModel):
    ok: bool = True
    summary: str = ""
    surprise: SurpriseResult | None = None
    error: str | None = None
