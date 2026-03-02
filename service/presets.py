"""Preset registry for AI Groove Writer.

Each preset provides default control values and a prompt template for LLM generation.
Canonical reference: Docs/JSON_Contract.md (preset table), Docs/AI_Groove_Writer_Project_Plan.md (sections 12-13).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models import Controls


@dataclass
class Preset:
    id: str
    name: str
    defaults: Controls
    prompt_template: str


PRESETS: dict[str, Preset] = {}


def _register(preset: Preset) -> None:
    PRESETS[preset.id] = preset


# --- Atmospheric Breakbeats (primary) ---
_register(Preset(
    id="breaks_atmos_130",
    name="Atmospheric Breakbeats (130)",
    defaults=Controls(
        density=0.75,
        complexity=0.65,
        swing=0.35,
        humanize_ms=8,
        velocity_jitter=6,
    ),
    prompt_template=(
        "You are generating a DRUM MIDI pattern for a progressive / atmospheric "
        "breakbeat track around {BPM} BPM.\n"
        "Style: broken-beat groove, tasteful syncopation, not overcrowded, lots of "
        "space for atmos and bass.\n"
        "Drums allowed (GM): kick(36), snare(38), clap(39 optional), closed hat(42), "
        "open hat(46), crash(49 optional).\n"
        "Structure: {BARS} bars, {TIME_SIG_NUM}/{TIME_SIG_DEN}. Make it loop well. "
        "Add a subtle variation/fill near bar 4 and bar 8.\n"
        "User notes: {USER_PROMPT}\n\n"
        "Controls:\n"
        "- density={DENSITY} (more hits when higher)\n"
        "- complexity={COMPLEXITY} (more variation/fills when higher)\n"
        "Return ONLY JSON matching the schema. Times are in quarter-note beats."
    ),
))

# --- Progressive Breaks (Driving) ---
_register(Preset(
    id="breaks_driving",
    name="Progressive Breaks (Driving)",
    defaults=Controls(
        density=0.80,
        complexity=0.75,
        swing=0.28,
        humanize_ms=6,
        velocity_jitter=5,
    ),
    prompt_template=(
        "You are generating a DRUM MIDI pattern for a driving progressive breakbeat "
        "track around {BPM} BPM.\n"
        "Style: forward momentum, energetic hats, occasional ride accents, "
        "syncopated but propulsive.\n"
        "Drums allowed (GM): kick(36), snare(38), clap(39 optional), closed hat(42), "
        "open hat(46), ride(51 optional), crash(49 optional).\n"
        "Structure: {BARS} bars, {TIME_SIG_NUM}/{TIME_SIG_DEN}. Loopable. "
        "Fill on bar 8 (end of phrase).\n"
        "User notes: {USER_PROMPT}\n\n"
        "Controls:\n"
        "- density={DENSITY} (more hits when higher)\n"
        "- complexity={COMPLEXITY} (more variation/fills when higher)\n"
        "Return ONLY JSON matching the schema. Times are in quarter-note beats."
    ),
))

# --- Downtempo / Psychill ---
_register(Preset(
    id="chill_psychill",
    name="Downtempo / Psychill",
    defaults=Controls(
        density=0.55,
        complexity=0.45,
        swing=0.22,
        humanize_ms=10,
        velocity_jitter=8,
    ),
    prompt_template=(
        "Generate a DRUM MIDI pattern for downtempo/chillout/psychill.\n"
        "Groove: relaxed, airy, sparse, gentle offbeat accents. Softer velocities.\n"
        "Allowed drums: kick(36), snare(38), closed hat(42), open hat(46), "
        "light perc/clap(39 optional).\n"
        "{BARS} bars, {TIME_SIG_NUM}/{TIME_SIG_DEN}, loopable, minimal fills.\n"
        "BPM: {BPM}\n"
        "User notes: {USER_PROMPT}\n"
        "Return ONLY JSON, quarter-note beat units, within clip length."
    ),
))

# --- 4-to-the-Floor (House) ---
_register(Preset(
    id="four_on_floor",
    name="4-to-the-Floor (House)",
    defaults=Controls(
        density=0.70,
        complexity=0.45,
        swing=0.18,
        humanize_ms=6,
        velocity_jitter=5,
    ),
    prompt_template=(
        "Generate a DRUM MIDI pattern for 4-to-the-floor house-ish groove "
        "around {BPM} BPM.\n"
        "Kick on every beat, clap/snare on 2 and 4. Hats provide movement "
        "with light swing.\n"
        "Allowed drums: kick(36), snare(38), clap(39), closed hat(42), "
        "open hat(46), crash(49 optional).\n"
        "{BARS} bars, {TIME_SIG_NUM}/{TIME_SIG_DEN}, loopable, small fill at bar 8.\n"
        "User notes: {USER_PROMPT}\n"
        "Return ONLY JSON with quarter-note beat units."
    ),
))

# --- Half-Time / Broken ---
_register(Preset(
    id="halftime_broken",
    name="Half-Time / Broken (Experimental)",
    defaults=Controls(
        density=0.60,
        complexity=0.70,
        swing=0.30,
        humanize_ms=9,
        velocity_jitter=7,
    ),
    prompt_template=(
        "Generate a DRUM MIDI pattern with a half-time / broken feel "
        "around {BPM} BPM.\n"
        "Style: half-time snare feel, syncopated kicks, negative space, "
        "tasteful glitch/percussion stutters.\n"
        "Allowed drums: kick(36), snare(38), clap(39 optional), closed hat(42), "
        "open hat(46), crash(49 optional).\n"
        "{BARS} bars, {TIME_SIG_NUM}/{TIME_SIG_DEN}, loopable.\n"
        "User notes: {USER_PROMPT}\n\n"
        "Controls:\n"
        "- density={DENSITY}\n"
        "- complexity={COMPLEXITY}\n"
        "Return ONLY JSON matching the schema. Times are in quarter-note beats."
    ),
))


def get_preset(preset_id: str) -> Preset | None:
    return PRESETS.get(preset_id)


def list_presets() -> list[dict]:
    return [
        {"id": p.id, "name": p.name, "defaults": p.defaults.model_dump()}
        for p in PRESETS.values()
    ]
