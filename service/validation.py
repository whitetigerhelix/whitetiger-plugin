"""Response parsing and validation for LLM output.

Extracts JSON from LLM text, validates against the MidiPlan schema,
and clamps notes to clip boundaries.

Canonical reference: Docs/JSON_Contract.md (validation rules).
"""

from __future__ import annotations

import json
import re

from models import ClipInfo, MidiPlan, NoteEvent

MAX_NOTES = 5000


def _extract_json(text: str) -> str:
    """Extract JSON from LLM text, handling code fences and preamble."""
    text = text.strip()

    # Try to extract from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # Try to find a JSON object directly
    brace_start = text.find("{")
    if brace_start >= 0:
        # Find the matching closing brace
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[brace_start : i + 1]

    # Return as-is and let JSON parsing handle the error
    return text


def _clip_length_beats(clip: ClipInfo) -> float:
    """Calculate clip length in quarter-note beats."""
    return clip.bars * clip.time_sig_num * (4.0 / clip.time_sig_den)


def parse_llm_response(text: str, clip: ClipInfo) -> MidiPlan:
    """Parse LLM text into a validated, clamped MidiPlan.

    Raises ValueError if the text cannot be parsed into valid JSON
    or does not match the expected schema.
    """
    json_str = _extract_json(text)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    # Parse notes from the response
    raw_notes = data.get("notes", [])
    if not isinstance(raw_notes, list):
        raise ValueError(f"Expected 'notes' to be a list, got {type(raw_notes).__name__}")

    clip_len = _clip_length_beats(clip)
    valid_notes: list[NoteEvent] = []

    for raw_note in raw_notes:
        if not isinstance(raw_note, dict):
            continue

        try:
            pitch = int(raw_note.get("pitch", -1))
            start = float(raw_note.get("start_beats", -1))
            dur = float(raw_note.get("dur_beats", 0))
            vel = int(raw_note.get("vel", 0))
            mute = int(raw_note.get("mute", 0))
        except (TypeError, ValueError):
            continue

        # Skip notes with unfixable values
        if pitch < 0 or pitch > 127:
            continue
        if start < 0:
            continue
        if dur <= 0:
            continue
        if vel < 1:
            vel = 1
        if vel > 127:
            vel = 127
        if mute not in (0, 1):
            mute = 0

        # Clamp to clip boundaries
        if start >= clip_len:
            continue
        if start + dur > clip_len:
            dur = clip_len - start
            if dur <= 0:
                continue

        valid_notes.append(NoteEvent(
            pitch=pitch,
            start_beats=start,
            dur_beats=dur,
            vel=vel,
            mute=mute,
        ))

        if len(valid_notes) >= MAX_NOTES:
            break

    plan = MidiPlan(
        version=data.get("version", 1),
        mode=data.get("mode", "drums"),
        bars=data.get("bars", clip.bars),
        time_sig_num=data.get("time_sig_num", clip.time_sig_num),
        time_sig_den=data.get("time_sig_den", clip.time_sig_den),
        notes=valid_notes,
    )

    return plan
