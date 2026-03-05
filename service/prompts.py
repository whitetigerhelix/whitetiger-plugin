"""Prompt construction for LLM groove generation.

Builds the system prompt (strict JSON output instructions) and user prompt
(from preset template + user input + controls).

Canonical reference: Docs/AI_Groove_Writer_Project_Plan.md sections 11-13.
"""

from __future__ import annotations

import json
from pathlib import Path

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
- If instrument context is provided, use those pitch mappings and tailor the pattern to the available sounds.

General MIDI drum pitches (default if no instrument context):
  kick=36, snare=38, clap=39, closed hat=42, open hat=46, crash=49
  (Also available: low tom=45, mid tom=47, high tom=50, ride=51)

Musical quality rules — these are critical for production-usable output:
- EVERY BAR must have notes. A bar with no notes is a failure. The pattern must span from beat 0.0 to the final bar.
- ALL drum voices (kick, snare, hats at minimum) must be present across ALL bars, not just some of them.
- The pattern must loop seamlessly: the last beat should set up beat 0 of the next loop (e.g., crash or open hat resolving on the downbeat).
- Use realistic velocity dynamics: accents on strong beats (100-120), ghost notes softer (40-65), mid-range for groove body (70-95).
- Kick provides the rhythmic foundation — it must appear in every bar. Snare anchors the backbeat — it must appear in every bar. Hats drive forward motion — they must run continuously.
- Layer multiple drum voices thoughtfully: create interplay between kick/snare/hats/percussion.
- Use dur_beats realistically: kick/snare hits ~0.25, closed hats ~0.15-0.25, open hats ~0.35-0.5, crashes ~0.5-1.0.
- Create phrase structure with tension and release:
  - Bars 1-3: establish the core groove
  - Bar 4: subtle variation (ghost note, hat accent, or brief snare drag)
  - Bars 5-7: develop with slight evolution (add a percussion accent, shift a kick)
  - Bar 8: drum fill leading back to bar 1 (snare roll, tom cascade, crash on downbeat of next loop)
- For longer patterns (16+ bars): A section (bars 1-8) establishes, B section (bars 9-16) evolves with more energy or variation, bar 16 fill resolves to loop.
- Avoid robotic repetition: introduce small velocity and placement variations across bars to keep listener interest.
- Sparse is often better than busy. Leave space for other instruments.
- Energy arc: the groove should breathe — build subtle tension through the phrase, release with the fill, then restart.

Drum fill guidelines (apply when complexity is moderate-to-high or fills are requested):
- Fills should lead into the next phrase (typically last 1-2 beats of bar 4, 8, 16, etc.)
- Good fill vocabulary: snare rolls (rapid 16ths on snare with rising velocity), tom cascades (high→mid→low tom descending), open hat lifts, crash on beat 1 of next phrase
- Keep fills short and purposeful — they punctuate, not dominate
- Match fill intensity to the groove: subtle grooves get gentle fills, driving grooves get more energetic fills

Reference example (4 bars of atmospheric breakbeat, 4/4 — shows groove + variation + fill + loop point):
{"version":1,"mode":"drums","bars":4,"time_sig_num":4,"time_sig_den":4,"notes":[
{"pitch":36,"start_beats":0.0,"dur_beats":0.25,"vel":110,"mute":0},
{"pitch":42,"start_beats":0.0,"dur_beats":0.15,"vel":80,"mute":0},
{"pitch":42,"start_beats":0.5,"dur_beats":0.15,"vel":70,"mute":0},
{"pitch":38,"start_beats":1.0,"dur_beats":0.25,"vel":102,"mute":0},
{"pitch":42,"start_beats":1.0,"dur_beats":0.15,"vel":82,"mute":0},
{"pitch":42,"start_beats":1.5,"dur_beats":0.15,"vel":65,"mute":0},
{"pitch":36,"start_beats":1.75,"dur_beats":0.25,"vel":92,"mute":0},
{"pitch":42,"start_beats":2.0,"dur_beats":0.15,"vel":78,"mute":0},
{"pitch":46,"start_beats":2.5,"dur_beats":0.4,"vel":80,"mute":0},
{"pitch":38,"start_beats":3.0,"dur_beats":0.25,"vel":105,"mute":0},
{"pitch":42,"start_beats":3.0,"dur_beats":0.15,"vel":76,"mute":0},
{"pitch":36,"start_beats":3.5,"dur_beats":0.25,"vel":88,"mute":0},
{"pitch":42,"start_beats":3.5,"dur_beats":0.15,"vel":68,"mute":0},
{"pitch":36,"start_beats":4.0,"dur_beats":0.25,"vel":108,"mute":0},
{"pitch":42,"start_beats":4.0,"dur_beats":0.15,"vel":78,"mute":0},
{"pitch":42,"start_beats":4.5,"dur_beats":0.15,"vel":72,"mute":0},
{"pitch":38,"start_beats":5.0,"dur_beats":0.25,"vel":100,"mute":0},
{"pitch":42,"start_beats":5.0,"dur_beats":0.15,"vel":80,"mute":0},
{"pitch":42,"start_beats":5.5,"dur_beats":0.15,"vel":64,"mute":0},
{"pitch":36,"start_beats":5.75,"dur_beats":0.25,"vel":94,"mute":0},
{"pitch":42,"start_beats":6.0,"dur_beats":0.15,"vel":76,"mute":0},
{"pitch":46,"start_beats":6.5,"dur_beats":0.4,"vel":78,"mute":0},
{"pitch":38,"start_beats":7.0,"dur_beats":0.25,"vel":104,"mute":0},
{"pitch":42,"start_beats":7.0,"dur_beats":0.15,"vel":82,"mute":0},
{"pitch":38,"start_beats":7.5,"dur_beats":0.25,"vel":48,"mute":0},
{"pitch":42,"start_beats":7.75,"dur_beats":0.15,"vel":70,"mute":0},
{"pitch":36,"start_beats":8.0,"dur_beats":0.25,"vel":106,"mute":0},
{"pitch":42,"start_beats":8.0,"dur_beats":0.15,"vel":80,"mute":0},
{"pitch":42,"start_beats":8.5,"dur_beats":0.15,"vel":74,"mute":0},
{"pitch":38,"start_beats":9.0,"dur_beats":0.25,"vel":98,"mute":0},
{"pitch":42,"start_beats":9.0,"dur_beats":0.15,"vel":78,"mute":0},
{"pitch":39,"start_beats":9.5,"dur_beats":0.25,"vel":60,"mute":0},
{"pitch":42,"start_beats":9.5,"dur_beats":0.15,"vel":66,"mute":0},
{"pitch":36,"start_beats":9.75,"dur_beats":0.25,"vel":90,"mute":0},
{"pitch":42,"start_beats":10.0,"dur_beats":0.15,"vel":76,"mute":0},
{"pitch":46,"start_beats":10.5,"dur_beats":0.4,"vel":82,"mute":0},
{"pitch":38,"start_beats":11.0,"dur_beats":0.25,"vel":106,"mute":0},
{"pitch":42,"start_beats":11.0,"dur_beats":0.15,"vel":80,"mute":0},
{"pitch":36,"start_beats":11.5,"dur_beats":0.25,"vel":86,"mute":0},
{"pitch":42,"start_beats":11.5,"dur_beats":0.15,"vel":68,"mute":0},
{"pitch":36,"start_beats":12.0,"dur_beats":0.25,"vel":104,"mute":0},
{"pitch":42,"start_beats":12.0,"dur_beats":0.15,"vel":78,"mute":0},
{"pitch":42,"start_beats":12.5,"dur_beats":0.15,"vel":72,"mute":0},
{"pitch":38,"start_beats":13.0,"dur_beats":0.25,"vel":96,"mute":0},
{"pitch":42,"start_beats":13.0,"dur_beats":0.15,"vel":80,"mute":0},
{"pitch":42,"start_beats":13.5,"dur_beats":0.15,"vel":68,"mute":0},
{"pitch":38,"start_beats":13.75,"dur_beats":0.15,"vel":55,"mute":0},
{"pitch":38,"start_beats":14.0,"dur_beats":0.15,"vel":65,"mute":0},
{"pitch":38,"start_beats":14.25,"dur_beats":0.15,"vel":78,"mute":0},
{"pitch":38,"start_beats":14.5,"dur_beats":0.15,"vel":90,"mute":0},
{"pitch":47,"start_beats":14.75,"dur_beats":0.25,"vel":85,"mute":0},
{"pitch":45,"start_beats":15.0,"dur_beats":0.25,"vel":88,"mute":0},
{"pitch":45,"start_beats":15.25,"dur_beats":0.25,"vel":80,"mute":0},
{"pitch":46,"start_beats":15.5,"dur_beats":0.5,"vel":90,"mute":0},
{"pitch":49,"start_beats":15.75,"dur_beats":0.5,"vel":95,"mute":0}
]}
This example demonstrates:
- Bar 1-2: core groove (kick anchors, snare backbeat, hat 8ths with velocity variation, open hat accents)
- Bar 3: slight variation (clap layer, subtle shift)
- Bar 4: drum fill (snare roll with rising velocity → tom cascade → open hat lift → crash resolving to loop)
- ALL bars have kick, snare, and hats present. No empty bars.
- Pattern loops: the crash at beat 15.75 resolves when bar 1 kicks in again.
Use this as a quality and structural reference."""


BASS_SYSTEM_PROMPT = """You are an expert bass line generator for music production. You output ONLY valid JSON, nothing else.

Your output must match this exact schema:
{
  "version": 1,
  "mode": "bass",
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
- If key and scale are provided, ALL pitches must be in that scale.

Musical quality rules for bass:
- EVERY BAR must have notes. Fill all requested bars.
- Bass lines should be monophonic (one note at a time, no overlaps).
- Root notes anchor the groove — use them on strong beats. Octave shifts add movement.
- Use realistic durations: short staccato 0.15-0.25, legato 0.5-1.0, sustained 1.0-2.0.
- Velocity dynamics: accents on root/downbeat (100-115), passing tones softer (70-90).
- Lock to the kick drum rhythm where possible — bass and kick should work together.
- Typical bass range: MIDI pitches 28-60 (E1 to C4). Stay in the low register.
- Pattern must loop seamlessly.
- Create movement through the phrase with passing tones, octave jumps, and chromatic approach notes."""


MELODY_SYSTEM_PROMPT = """You are an expert melody/lead generator for music production. You output ONLY valid JSON, nothing else.

Your output must match this exact schema:
{
  "version": 1,
  "mode": "melody",
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
- If key and scale are provided, ALL pitches must be in that scale.

Musical quality rules for melody:
- EVERY BAR must have notes. Fill all requested bars.
- Melodies should be primarily monophonic with occasional intervals.
- Create a singable, memorable phrase — think hook, motif, or atmospheric lead.
- Use realistic durations: short notes 0.25-0.5, sustained 1.0-2.0, long holds 2.0-4.0.
- Typical melody range: MIDI pitches 60-84 (C4 to C6). Stay in the mid-upper register.
- Velocity dynamics: phrase peaks louder (100-120), softer passing notes (65-85).
- Create phrase structure: call and response, tension/resolution, repetition with variation.
- Pattern must loop seamlessly.
- Leave breathing room — rests are as important as notes in a good melody."""


CHORDS_SYSTEM_PROMPT = """You are an expert chord/harmony generator for music production. You output ONLY valid JSON, nothing else.

Your output must match this exact schema:
{
  "version": 1,
  "mode": "chords",
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
- If key and scale are provided, ALL pitches must be in that scale.

Musical quality rules for chords:
- EVERY BAR must have chord notes. Fill all requested bars.
- Chords are POLYPHONIC — multiple notes play simultaneously to form harmonies.
- Use 3-4 note voicings (triads and 7ths). Avoid overly thick voicings.
- Typical chord range: MIDI pitches 48-72 (C3 to C5). Mid register for warmth.
- Chord changes typically happen every 1, 2, or 4 beats depending on style.
- Use realistic durations: pad chords 2.0-4.0, rhythmic stabs 0.25-0.5, arpeggiated 0.25-1.0.
- Velocity: consistent for pads (80-95), accented for stabs (95-115), softer for ambient (60-80).
- Voice leading: minimize jumps between chord changes, move smoothly.
- Pattern must loop seamlessly with the last chord resolving to the first."""


REFINE_SYSTEM_PROMPT = """You are an expert music pattern editor. You modify existing MIDI patterns based on user instructions.

You receive an existing pattern (as JSON notes) and an edit instruction. Return the MODIFIED pattern as valid JSON.

Your output must match this exact schema:
{
  "version": 1,
  "mode": "<mode>",
  "bars": <number>,
  "time_sig_num": <number>,
  "time_sig_den": <number>,
  "notes": [
    {"pitch": <0-127>, "start_beats": <float >= 0>, "dur_beats": <float > 0>, "vel": <1-127>, "mute": <0 or 1>}
  ]
}

Rules:
- Return ONLY the modified JSON. No markdown, no explanation.
- Keep the parts the user didn't ask to change.
- Apply the edit instruction precisely — if they say "make hats busier in bars 5-8", only modify hat notes in bars 5-8.
- Maintain musical coherence: edits should feel natural, not robotic.
- All notes must stay within clip bounds.
- Pattern must still loop seamlessly after editing."""


_MODE_SYSTEM_PROMPTS = {
    "drums": SYSTEM_PROMPT,
    "bass": BASS_SYSTEM_PROMPT,
    "melody": MELODY_SYSTEM_PROMPT,
    "chords": CHORDS_SYSTEM_PROMPT,
}


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


def build_system_prompt(mode: str = "drums") -> str:
    """Return the system prompt for the given mode."""
    return _MODE_SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPT)


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

    prompt += f"\n\n--- CLIP CONSTRAINTS (authoritative, from UI configuration) ---"
    prompt += f"\nBars: {clip.bars} | Time signature: {clip.time_sig_num}/{clip.time_sig_den} | BPM: {clip.bpm}"
    prompt += f"\nClip length: {clip_length_beats} quarter-note beats."
    prompt += f"\nYou MUST generate notes from beat 0.0 through beat {clip_length_beats - 1}.0 at minimum."
    prompt += f"\nEvery single bar must contain kick, snare/clap, AND hat notes. No empty bars."
    beats_per_bar = clip.time_sig_num * (4.0 / clip.time_sig_den)
    last_bar_start = (clip.bars - 1) * beats_per_bar
    prompt += f"\nThe last bar (beats {last_bar_start}–{clip_length_beats}) should include a fill leading back to the loop start."

    # Make density/complexity have concrete meaning
    notes_per_bar_estimate = int(4 + controls.density * 12)  # 4-16 notes per bar
    prompt += f"\n\n--- GENERATION CONTROLS ---"
    prompt += f"\nDensity: {controls.density:.2f} — target approximately {notes_per_bar_estimate} note events per bar."
    if controls.density < 0.3:
        prompt += " Very sparse — lots of space, minimal hits."
    elif controls.density > 0.7:
        prompt += " Dense — busy pattern with layered hits."

    prompt += f"\nComplexity: {controls.complexity:.2f}"
    if controls.complexity < 0.3:
        prompt += " — keep it simple and repetitive, minimal variation between bars."
    elif controls.complexity < 0.6:
        prompt += " — moderate variation, subtle changes across bars, small fill at phrase end."
    else:
        prompt += " — high variation between bars, creative fills, evolving pattern, syncopated surprises."
    prompt += f"\nSeed: {seed} — this seed value means you must generate a UNIQUE pattern. Different seeds must produce noticeably different grooves with different kick placements, hat patterns, and fill choices. Do not repeat the same pattern."
    if request.key or request.scale:
        key_str = request.key or "C"
        scale_str = request.scale or "minor"
        prompt += f"\n\n--- KEY/SCALE ---"
        prompt += f"\nKey: {key_str} | Scale: {scale_str}"
        prompt += f"\nALL pitches must be in {key_str} {scale_str}. Do not use out-of-scale notes."
    if request.allowed_pitches:
        allowed = ", ".join(str(p) for p in request.allowed_pitches)
        prompt += f"\nAllowed MIDI pitches: [{allowed}]"

    if request.instrument_hints:
        hints = "; ".join(request.instrument_hints)
        prompt += f"\nInstrument/layer hints: {hints}"

    if request.instrument_context:
        prompt += "\n\nInstrument context (from current Ableton Drum Rack):"
        for pad in request.instrument_context:
            pitch = pad.get("pitch", "?")
            name = pad.get("name", "unknown")
            sample = pad.get("sample", "")
            line = f"\n  pitch {pitch}: {name}"
            if sample:
                line += f" ({sample})"
            prompt += line
        prompt += "\nUse these pitches and tailor the pattern to these specific sounds."

    # Reference pattern: user-provided takes priority, otherwise load from preset library
    ref_notes = None
    ref_source = ""
    if request.reference_pattern:
        ref_notes = request.reference_pattern
        ref_source = "user clip"
    else:
        ref_path = Path(__file__).parent / "reference_patterns" / f"{request.preset_id}.json"
        if ref_path.exists():
            try:
                ref_notes = json.loads(ref_path.read_text(encoding="utf-8"))
                ref_source = "preset library"
            except Exception:
                pass

    if ref_notes:
        ref_pitches = sorted(set(n.get("pitch", 0) for n in ref_notes))
        ref_count = len(ref_notes)

        # First 4 bars as groove feel sample
        sample_beats = min(4 * beats_per_bar, max((n.get("start_beats", 0) for n in ref_notes), default=0) + 1)
        sample_notes = [n for n in ref_notes if n.get("start_beats", 0) < sample_beats]
        sample_json = json.dumps(sample_notes)

        prompt += (
            f"\n\nReference groove ({ref_source} — {ref_count} total notes, pitches {ref_pitches}):\n"
            + sample_json
            + f"\nThis shows the FEEL and GROOVE PLACEMENT to draw from. "
            f"Use it as rhythmic inspiration for kick/snare/hat placement and velocity contour. "
            f"But you MUST generate a COMPLETELY NEW {clip.bars}-bar pattern — "
            f"do NOT copy these notes. Create an original groove that captures "
            f"a similar rhythmic character and energy level."
        )

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


def build_refine_prompt(
    current_notes: list[dict],
    instruction: str,
    clip: "ClipInfo",
    mode: str = "drums",
    key: str | None = None,
    scale: str | None = None,
) -> str:
    """Build user prompt for the refine/edit endpoint."""
    from models import ClipInfo  # avoid circular at module level

    clip_length_beats = clip.bars * clip.time_sig_num * (4.0 / clip.time_sig_den)
    notes_json = json.dumps(current_notes)

    prompt = (
        f"Current {mode} pattern ({len(current_notes)} notes, {clip.bars} bars):\n"
        + notes_json
        + f"\n\nEdit instruction: {instruction}"
        + f"\n\nClip length: {clip_length_beats} quarter-note beats ({clip.bars} bars)."
        + f"\nReturn the COMPLETE modified pattern as JSON. Keep everything the user didn't ask to change."
    )

    if key or scale:
        prompt += f"\nKey: {key or 'C'} | Scale: {scale or 'minor'}. Keep all pitches in scale."

    return prompt
