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
- If the user provides allowed pitch constraints, use only those pitches.
- Prefer layered percussion and syncopated rhythms when requested.
- Every note must satisfy: start_beats + dur_beats <= clip_length_beats.
- Velocity range: 1-127 (never 0).
- Maximum 5000 notes total.
- Prefer repeatable musical structure with occasional fills.
- Make patterns loop well."""


SURPRISE_SYSTEM_PROMPT = """You are a music production assistant that creates surprise prompt ideas for drum groove generation.

Return ONLY valid JSON in this exact schema:
{
  "prompt": "<string>",
  "controls": {
    "density": <0..1>,
    "complexity": <0..1>,
    "swing": <0..1>,
    "humanize_ms": <0..25>,
    "velocity_jitter": <0..15>
  },
  "sound_suggestion": "<string>"
}

Rules:
- Return JSON only. No markdown, no prose.
- Keep prompt musically coherent with the provided preset style.
- Use color (0=tight/safe, 1=adventurous) to control how bold the prompt and controls are.
- Keep controls realistic for drum groove generation.
- sound_suggestion must be a stylistic suggestion only (never claim to scan local files).
"""


def build_system_prompt() -> str:
    """Return the system prompt that instructs the LLM to output valid JSON."""
    return SYSTEM_PROMPT


def build_surprise_system_prompt() -> str:
    """Return system prompt for surprise prompt/control generation."""
    return SURPRISE_SYSTEM_PROMPT


def build_user_prompt(
    preset: Preset,
    request: GenerateRequest,
    *,
    effective_seed: int | None = None,
) -> str:
    """Build the user prompt by filling preset template placeholders.

    If effective_seed is provided, it overrides request.seed in the prompt.
    This supports variation mode (seed + variation offset).
    """
    clip = request.clip
    controls = request.controls
    seed = effective_seed if effective_seed is not None else request.seed

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
    prompt += f"\nSeed: {seed}"

    if request.allowed_pitches:
        allowed = ", ".join(str(p) for p in request.allowed_pitches)
        prompt += f"\nAllowed MIDI pitches: [{allowed}]"

    if request.instrument_hints:
        hints = "; ".join(request.instrument_hints)
        prompt += f"\nInstrument/layer hints: {hints}"

    return prompt


def build_surprise_user_prompt(preset: Preset, color: float) -> str:
    """Build user prompt for surprise prompt/control generation."""
    defaults = preset.defaults
    return (
        f"Preset: {preset.id} ({preset.name})\n"
        f"Color: {color:.2f} (0=tight/safe, 1=adventurous)\n"
        f"Default controls: density={defaults.density}, complexity={defaults.complexity}, "
        f"swing={defaults.swing}, humanize_ms={defaults.humanize_ms}, "
        f"velocity_jitter={defaults.velocity_jitter}\n"
        "Generate one surprise drum-groove prompt idea with matching control values. "
        "The prompt should be emotionally coherent and production-usable."
    )
