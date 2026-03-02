"""Prompt construction for LLM groove generation.

Builds the system prompt (strict JSON output instructions) and user prompt
(from preset template + user input + controls).

Canonical reference: Docs/AI_Groove_Writer_Project_Plan.md sections 11-13.
"""

from __future__ import annotations

from models import GenerateRequest
from presets import Preset

SYSTEM_PROMPT = """You are a drum pattern generator. You output ONLY valid JSON, nothing else.

Your output must match this exact schema:
{
  "version": 1,
  "mode": "drums",
  "bars": <number>,
  "time_sig_num": <number>,
  "time_sig_den": <number>,
  "notes": [
    {"pitch": <0-127>, "start_beats": <float >= 0>, "dur_beats": <float > 0>, "vel": <1-127>, "mute": <0 or 1>}
  ]
}

Rules:
- Return ONLY the JSON object. No markdown, no code fences, no explanation.
- All times are in quarter-note beats (Ableton-native).
- Use General MIDI drum pitches: kick=36, snare=38, clap=39, closed hat=42, open hat=46, crash=49.
- Every note must satisfy: start_beats + dur_beats <= clip_length_beats.
- Velocity range: 1-127 (never 0).
- Maximum 5000 notes total.
- Prefer repeatable musical structure with occasional fills.
- Make patterns loop well."""


def build_system_prompt() -> str:
    """Return the system prompt that instructs the LLM to output valid JSON."""
    return SYSTEM_PROMPT


def build_user_prompt(preset: Preset, request: GenerateRequest) -> str:
    """Build the user prompt by filling preset template placeholders."""
    clip = request.clip
    controls = request.controls

    clip_length_beats = clip.bars * clip.time_sig_num * (4.0 / clip.time_sig_den)

    prompt = preset.prompt_template.format(
        USER_PROMPT=request.prompt,
        BPM=clip.bpm,
        BARS=clip.bars,
        TIME_SIG_NUM=clip.time_sig_num,
        TIME_SIG_DEN=clip.time_sig_den,
        DENSITY=controls.density,
        COMPLEXITY=controls.complexity,
    )

    prompt += f"\n\nClip length: {clip_length_beats} quarter-note beats."
    prompt += f"\nSeed: {request.seed}"

    return prompt
