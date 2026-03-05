"""Prompt construction for LLM groove generation.

Builds the system prompt (strict JSON output instructions) and user prompt
(from preset template + user input + controls).

Canonical reference: Docs/AI_Groove_Writer_Project_Plan.md sections 11-13.
"""

from __future__ import annotations

from models import GenerateRequest
from presets import Preset

SYSTEM_PROMPT = """You are an expert drum pattern generator for music production. You output ONLY valid JSON, nothing else.

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

Critical rules:
- Return ONLY the JSON object. No markdown, no code fences, no explanation.
- All times are in quarter-note beats (Ableton-native). Beat 0.0 = start of bar 1.
- Every note must satisfy: start_beats + dur_beats <= clip_length_beats.
- Velocity range: 1-127 (never 0). Maximum 5000 notes total.
- If the user provides allowed pitch constraints, use only those pitches.

General MIDI drum pitches:
  kick=36, snare=38, clap=39, closed hat=42, open hat=46, crash=49
  (Also available: low tom=45, mid tom=47, high tom=50, ride=51)

Musical quality rules — these are critical for production-usable output:
- FILL ALL REQUESTED BARS. Notes must span the entire clip length, not just the first few bars.
- The pattern must loop seamlessly: beat 0 of the next loop should feel like a natural continuation.
- Use realistic velocity dynamics: accents on strong beats (100-120), ghost notes softer (40-65), mid-range for groove body (70-95).
- Kick provides the rhythmic foundation. Snare anchors the backbeat. Hats drive forward motion.
- Layer multiple drum voices thoughtfully: don't just repeat one instrument, create interplay between kick/snare/hats/percussion.
- Use dur_beats realistically: kick/snare hits ~0.25, closed hats ~0.15-0.25, open hats ~0.35-0.5, crashes ~0.5-1.0.
- Create phrase structure: bars 1-3 establish groove, bar 4 can add subtle variation, bars 5-7 develop, bar 8 can have a fill or turnaround.
- For longer patterns (16+ bars), create a larger arc: A section (bars 1-8), B section with evolution (bars 9-16).
- Avoid robotic repetition: introduce small variations in velocity and timing placement across bars.
- Sparse is often better than busy. Leave space for other instruments."""


SURPRISE_SYSTEM_PROMPT = """You are an expert music production assistant specializing in drum groove design. You create detailed, production-ready prompt ideas for an AI drum pattern generator.

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
- The prompt field should be detailed and musically specific (3-5 sentences). Include:
  - Overall mood and energy
  - Specific rhythmic direction (kick placement, snare feel, hat behavior)
  - Velocity dynamics guidance (accents, ghost notes, crescendos)
  - Phrase structure suggestion (fills, turnarounds, variation points)
- Use color (0=tight/safe, 1=adventurous) to scale boldness:
  - Low color: stay close to preset defaults, classic patterns, subtle dynamics
  - High color: more experimental rhythms, unusual accents, wider dynamic range, creative layering
- Controls must be coherent with the prompt (e.g., a sparse groove should have lower density).
- sound_suggestion should describe an ideal drum kit character in production terms (e.g., "tight vinyl-textured breakbeat kit with soft transient snare and airy metallic hats"). Never claim to scan local files.
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
        f"velocity_jitter={defaults.velocity_jitter}\n\n"
        "Generate a surprise drum-groove prompt idea with matching control values.\n"
        "The prompt should be detailed and production-ready:\n"
        "- Describe the emotional character and energy\n"
        "- Specify kick/snare/hat behavior and rhythmic feel\n"
        "- Include velocity dynamics guidance (ghost notes, accents, builds)\n"
        "- Suggest phrase structure (where to add fills, variation, turnarounds)\n"
        "- Make it feel like a complete, loopable musical idea\n"
        "The sound_suggestion should describe an ideal drum kit character."
    )
