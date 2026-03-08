"""Hardcoded mock grooves for development without LLM calls.

Each function returns a (summary, notes_list) tuple for a given preset.
Notes use GM drum pitches and quarter-note beat units.

GM reference: Kick=36, Snare=38, Clap=39, CH=42, OH=46, Crash=49
"""

from __future__ import annotations

# Shorthand pitch constants
KICK = 36
SNARE = 38
CLAP = 39
CH = 42  # closed hat
OH = 46  # open hat
CRASH = 49


def _note(pitch: int, start: float, dur: float = 0.25, vel: int = 100) -> dict:
    return {
        "pitch": pitch,
        "start_beats": start,
        "dur_beats": dur,
        "vel": vel,
        "mute": 0,
    }


def breaks_atmos_130(bars: int = 8) -> tuple[str, list[dict]]:
    """Atmospheric breakbeat — broken kick, snare on 2&4 with ghosts, shuffled hats."""
    notes: list[dict] = []
    for bar in range(bars):
        offset = bar * 4.0  # 4 beats per bar in 4/4

        # Kick: broken pattern (beat 1, and-of-2, beat 3.5 on even bars)
        notes.append(_note(KICK, offset + 0.0, vel=110))
        notes.append(_note(KICK, offset + 1.5, vel=95))
        if bar % 2 == 1:
            notes.append(_note(KICK, offset + 3.5, vel=85))

        # Snare: beats 2 and 4, ghost on and-of-3
        notes.append(_note(SNARE, offset + 1.0, vel=100))
        notes.append(_note(SNARE, offset + 3.0, vel=105))
        notes.append(_note(SNARE, offset + 2.5, vel=45))  # ghost

        # Closed hat: 8th notes with velocity variation
        for eighth in range(8):
            beat_pos = offset + eighth * 0.5
            vel = 80 if eighth % 2 == 0 else 60
            notes.append(_note(CH, beat_pos, dur=0.2, vel=vel))

        # Open hat: occasional off-beat accent
        if bar % 2 == 0:
            notes.append(_note(OH, offset + 1.5, dur=0.3, vel=70))

        # Fill on bars 4 and 8 (0-indexed: 3 and 7)
        if bar in (3, 7):
            notes.append(_note(SNARE, offset + 3.25, vel=65))
            notes.append(_note(SNARE, offset + 3.75, vel=75))
            if bar == 7:
                notes.append(_note(CRASH, offset + 3.75, dur=0.5, vel=90))

    summary = (
        f"Atmospheric breakbeat groove: {bars} bars, broken kick, "
        "snare on 2&4 with ghosts, shuffled hats, fills on bar 4 and 8. (Mock)"
    )
    return summary, notes


def breaks_driving(bars: int = 8) -> tuple[str, list[dict]]:
    """Driving progressive breaks — more forward momentum."""
    notes: list[dict] = []
    for bar in range(bars):
        offset = bar * 4.0

        # Kick: beats 1 and 3, plus and-of-2
        notes.append(_note(KICK, offset + 0.0, vel=115))
        notes.append(_note(KICK, offset + 1.5, vel=100))
        notes.append(_note(KICK, offset + 2.0, vel=105))

        # Snare on 2 and 4
        notes.append(_note(SNARE, offset + 1.0, vel=105))
        notes.append(_note(SNARE, offset + 3.0, vel=110))

        # Hats: 16th notes
        for sixteenth in range(16):
            beat_pos = offset + sixteenth * 0.25
            vel = 85 if sixteenth % 4 == 0 else (65 if sixteenth % 2 == 0 else 50)
            notes.append(_note(CH, beat_pos, dur=0.15, vel=vel))

        # Fill on bar 8
        if bar == bars - 1:
            notes.append(_note(SNARE, offset + 3.25, vel=80))
            notes.append(_note(SNARE, offset + 3.5, vel=90))
            notes.append(_note(SNARE, offset + 3.75, vel=100))

    return f"Driving progressive breaks: {bars} bars, energetic hats, fill on bar {bars}. (Mock)", notes


def chill_psychill(bars: int = 8) -> tuple[str, list[dict]]:
    """Downtempo psychill — sparse, airy, soft."""
    notes: list[dict] = []
    for bar in range(bars):
        offset = bar * 4.0

        # Kick: just beat 1 and occasional beat 3
        notes.append(_note(KICK, offset + 0.0, vel=90))
        if bar % 2 == 0:
            notes.append(_note(KICK, offset + 2.0, vel=75))

        # Snare: beat 3 only (half-time feel)
        notes.append(_note(SNARE, offset + 2.0, vel=80))

        # Hats: sparse, every other beat
        notes.append(_note(CH, offset + 0.5, dur=0.2, vel=55))
        notes.append(_note(CH, offset + 2.5, dur=0.2, vel=50))
        if bar % 2 == 1:
            notes.append(_note(OH, offset + 1.5, dur=0.4, vel=45))

    return f"Downtempo psychill groove: {bars} bars, sparse and airy. (Mock)", notes


def four_on_floor(bars: int = 8) -> tuple[str, list[dict]]:
    """4-to-the-floor house groove."""
    notes: list[dict] = []
    for bar in range(bars):
        offset = bar * 4.0

        # Kick: every beat
        for beat in range(4):
            notes.append(_note(KICK, offset + beat, vel=110))

        # Clap on 2 and 4
        notes.append(_note(CLAP, offset + 1.0, vel=100))
        notes.append(_note(CLAP, offset + 3.0, vel=100))

        # Hats: 8th notes, open hat on off-beats
        for eighth in range(8):
            beat_pos = offset + eighth * 0.5
            if eighth % 2 == 0:
                notes.append(_note(CH, beat_pos, dur=0.2, vel=75))
            else:
                notes.append(_note(OH, beat_pos, dur=0.3, vel=60))

    return f"4-to-the-floor house groove: {bars} bars, kick on every beat, claps on 2&4. (Mock)", notes


def halftime_broken(bars: int = 8) -> tuple[str, list[dict]]:
    """Half-time broken feel — syncopated, spacious."""
    notes: list[dict] = []
    for bar in range(bars):
        offset = bar * 4.0

        # Kick: beat 1 and syncopated hits
        notes.append(_note(KICK, offset + 0.0, vel=105))
        notes.append(_note(KICK, offset + 2.75, vel=85))

        # Snare: half-time on beat 3
        notes.append(_note(SNARE, offset + 2.0, vel=100))

        # Hats: sparse, offbeat
        notes.append(_note(CH, offset + 0.75, dur=0.2, vel=60))
        notes.append(_note(CH, offset + 1.75, dur=0.2, vel=55))
        notes.append(_note(CH, offset + 3.25, dur=0.2, vel=50))

        # Ghost snare
        if bar % 2 == 0:
            notes.append(_note(SNARE, offset + 1.25, vel=35))

    return f"Half-time broken groove: {bars} bars, syncopated kicks, spacious. (Mock)", notes


# Map preset_id → generator function
MOCK_GENERATORS: dict[str, callable] = {
    "breaks_atmos_130": breaks_atmos_130,
    "breaks_driving": breaks_driving,
    "chill_psychill": chill_psychill,
    "four_on_floor": four_on_floor,
    "halftime_broken": halftime_broken,
}


def get_mock_groove(preset_id: str, bars: int = 8) -> tuple[str, list[dict]]:
    """Return a mock groove for the given preset. Falls back to breaks_atmos_130."""
    generator = MOCK_GENERATORS.get(preset_id, breaks_atmos_130)
    return generator(bars)
