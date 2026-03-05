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
        density=0.70,
        complexity=0.60,
        swing=0.20,
        humanize_ms=4,
        velocity_jitter=3,
    ),
    prompt_template=(
        "Generate a DRUM MIDI pattern for a progressive / atmospheric "
        "breakbeat style.\n"
        "Style: broken-beat groove, tasteful syncopation, not overcrowded, lots of "
        "space for atmos and bass.\n"
        "Drums (GM): kick(36), snare(38), clap(39 optional), closed hat(42), "
        "open hat(46), crash(49 optional).\n"
        "Phrase arc: establish groove early, subtle variation mid-phrase, "
        "develop with slight evolution, fill or turnaround at the end. "
        "For longer patterns, create an A/B structure with evolution.\n"
        "Fills: use snare drags, ghost-note flurries, open hat lifts, or a short "
        "tom cascade leading into the next phrase. Keep fills tasteful and brief.\n"
        "Velocity dynamics: kick accents 100-115, ghost snares 40-60, "
        "hat body 70-90 with occasional accents at 95-105.\n"
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
        density=0.75,
        complexity=0.70,
        swing=0.15,
        humanize_ms=3,
        velocity_jitter=3,
    ),
    prompt_template=(
        "Generate a DRUM MIDI pattern for a driving progressive breakbeat style.\n"
        "Style: forward momentum, energetic hats, occasional ride accents, "
        "syncopated but propulsive.\n"
        "Drums (GM): kick(36), snare(38), clap(39 optional), closed hat(42), "
        "open hat(46), ride(51 optional), crash(49 optional).\n"
        "Phrase arc: build energy through the phrase, fill on the last bar. "
        "For longer patterns, create an A/B with the B section adding intensity.\n"
        "Fills: use snare rolls with rising velocity, tom runs, crash accents. "
        "Make fills punchy and propulsive to match the driving energy.\n"
        "Velocity: driving kick at 105-120, snare backbeats 95-110, "
        "hats 75-95 with accent lifts.\n"
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
        density=0.50,
        complexity=0.40,
        swing=0.12,
        humanize_ms=5,
        velocity_jitter=4,
    ),
    prompt_template=(
        "Generate a DRUM MIDI pattern for downtempo/chillout/psychill style.\n"
        "Groove: relaxed, airy, sparse, gentle offbeat accents. Softer velocities.\n"
        "Drums (GM): kick(36), snare(38), closed hat(42), open hat(46), "
        "clap(39 optional).\n"
        "Even sparse grooves need consistent hat/kick presence across all bars.\n"
        "Fills: keep minimal — a single ghost snare drag or gentle open hat "
        "swell at phrase end. Nothing aggressive.\n"
        "Velocity: softer overall (kick 75-95, snare 60-85, hats 50-75). "
        "Ghost notes and gentle accents create texture.\n"
        "User notes: {USER_PROMPT}\n"
        "Return ONLY JSON, quarter-note beat units, within clip length."
    ),
))

# --- 4-to-the-Floor (House) ---
_register(Preset(
    id="four_on_floor",
    name="4-to-the-Floor (House)",
    defaults=Controls(
        density=0.65,
        complexity=0.40,
        swing=0.10,
        humanize_ms=3,
        velocity_jitter=3,
    ),
    prompt_template=(
        "Generate a DRUM MIDI pattern for 4-to-the-floor house-ish groove style.\n"
        "Kick on every beat, clap/snare on 2 and 4. Hats drive forward motion.\n"
        "Drums (GM): kick(36), snare(38), clap(39), closed hat(42), "
        "open hat(46), crash(49 optional).\n"
        "Hats should have consistent 8th or 16th subdivision across all bars.\n"
        "Fills: classic house fills — snare/clap roll on beat 4, open hat lift, "
        "or a single crash on the downbeat of the next phrase.\n"
        "Velocity: kick solid 100-115, clap/snare 90-105, "
        "hats 70-85 with offbeat accents at 85-95.\n"
        "User notes: {USER_PROMPT}\n"
        "Return ONLY JSON with quarter-note beat units."
    ),
))

# --- Half-Time / Broken ---
_register(Preset(
    id="halftime_broken",
    name="Half-Time / Broken (Experimental)",
    defaults=Controls(
        density=0.55,
        complexity=0.60,
        swing=0.18,
        humanize_ms=4,
        velocity_jitter=4,
    ),
    prompt_template=(
        "Generate a DRUM MIDI pattern with a half-time / broken feel.\n"
        "Style: half-time snare feel, syncopated kicks, negative space, "
        "tasteful percussive stutters.\n"
        "Drums (GM): kick(36), snare(38), clap(39 optional), closed hat(42), "
        "open hat(46), crash(49 optional).\n"
        "Snare typically on beat 3 (half-time feel). Kicks are syncopated and conversational. "
        "Use space deliberately but maintain presence across all bars.\n"
        "Fills: use unexpected rhythmic bursts — a tom stutter, rapid hat flurry, "
        "or ghost snare cascade. Keep fills textural, not bombastic.\n"
        "Velocity: varied and expressive. Kick 85-110, snare 80-105, "
        "ghost hits 35-55, hats 60-85.\n"
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
