# JSON Contract

This document is the canonical reference for the data contract between the M4L device and the Python service. Both sides must conform to these schemas.

## GenerateRequest (M4L → Python)

```json
{
  "prompt": "progressive atmospheric breaks, swung hats, ghost snares, subtle fills",
  "preset_id": "breaks_atmos_130",
  "mode": "drums",
  "clip": {
    "bars": 8,
    "time_sig_num": 4,
    "time_sig_den": 4,
    "bpm": 130
  },
  "controls": {
    "density": 0.75,
    "complexity": 0.65,
    "swing": 0.35,
    "humanize_ms": 8,
    "velocity_jitter": 6
  },
  "seed": 12345,
  "variation": 0,
  "drum_map": "gm",
  "model": "gpt-4o-mini"
}
```

## GenerateResponse (Python → M4L)

```json
{
  "ok": true,
  "summary": "Broken-beat groove with swung hats, ghost snares, and a light fill on bar 4 and 8.",
  "plan": {
    "version": 1,
    "mode": "drums",
    "bars": 8,
    "time_sig_num": 4,
    "time_sig_den": 4,
    "notes": [
      { "pitch": 36, "start_beats": 0.0, "dur_beats": 0.25, "vel": 110, "mute": 0 },
      { "pitch": 42, "start_beats": 0.5, "dur_beats": 0.25, "vel": 72,  "mute": 0 },
      { "pitch": 38, "start_beats": 1.0, "dur_beats": 0.25, "vel": 100, "mute": 0 }
    ]
  }
}
```

### Error Response

```json
{
  "ok": false,
  "summary": "",
  "plan": null,
  "error": "LLM returned invalid JSON after 3 retries"
}
```

## Beat Units

All timing values use **quarter-note beats** (Ableton-native).

- `start_beats`: Position of the note in quarter-note beats from clip start (0-based)
- `dur_beats`: Duration of the note in quarter-note beats

### Clip Length Formula

```
beats_per_bar = time_sig_num × (4.0 / time_sig_den)
clip_length_beats = bars × beats_per_bar
```

**Example:** 8 bars of 4/4 = 8 × 4 × (4/4) = 32 beats

## Validation Rules

### Note constraints
| Field | Type | Range | Notes |
|---|---|---|---|
| `pitch` | int | 0–127 | GM drum pitches for MVP |
| `start_beats` | float | ≥ 0 | Must be within clip bounds |
| `dur_beats` | float | > 0 | Note must have positive duration |
| `vel` | int | 1–127 | Never 0 (use `mute` flag instead) |
| `mute` | int | 0 or 1 | 0 = active, 1 = muted |

### Boundary rules
- `start_beats + dur_beats ≤ clip_length_beats` (service clamps; Max double-checks)
- Maximum 5000 notes per response (service enforces)

### Request constraints
| Field | Range | Default | Notes |
|---|---|---|---|
| `seed` | int | 12345 | Hint to LLM; also affects cache key |
| `variation` | ≥ 0 | 0 | Variation index — effective seed = `seed + variation`. Different variations produce different cache keys and LLM outputs. |
| `model` | string or null | null | Override the server's default LLM model/deployment. Omit or set to null to use the server default from env vars. Included in cache key. |
| `clip.bars` | 1–64 | 8 | |
| `clip.time_sig_num` | 1–12 | 4 | |
| `clip.time_sig_den` | 1–16 | 4 | |
| `clip.bpm` | 40–240 | 130 | |
| `controls.density` | 0–1 | varies by preset | |
| `controls.complexity` | 0–1 | varies by preset | |
| `controls.swing` | 0–1 | varies by preset | |
| `controls.humanize_ms` | 0–25 | varies by preset | |
| `controls.velocity_jitter` | 0–15 | varies by preset | |

## GM Drum Mapping (MVP)

General MIDI drum pitches — works with Drum Rack defaults and common kits.

### Full set
| Instrument | Pitch | Notes |
|---|---|---|
| Kick | 36 | Core |
| Snare | 38 | Core |
| Clap | 39 | Optional |
| Closed Hi-Hat | 42 | Core |
| Open Hi-Hat | 46 | Core |
| Low Tom | 45 | — |
| Mid Tom | 47 | — |
| High Tom | 50 | — |
| Ride | 51 | — |
| Crash | 49 | Optional |

### MVP recommended set
Kick (36), Snare (38), Closed Hat (42), Open Hat (46), Clap (39), Crash (49)

## Style Presets (MVP)

| Preset ID | Name | Density | Complexity | Swing | Humanize (ms) | Vel Jitter |
|---|---|---|---|---|---|---|
| `breaks_atmos_130` | Atmospheric Breakbeats | 0.75 | 0.65 | 0.35 | 8 | 6 |
| `breaks_driving` | Progressive Breaks (Driving) | 0.80 | 0.75 | 0.28 | 6 | 5 |
| `chill_psychill` | Downtempo / Psychill | 0.55 | 0.45 | 0.22 | 10 | 8 |
| `four_on_floor` | 4-to-the-Floor (House) | 0.70 | 0.45 | 0.18 | 6 | 5 |
| `halftime_broken` | Half-Time / Broken | 0.60 | 0.70 | 0.30 | 9 | 7 |

### Primary preset: `breaks_atmos_130`
- Broken kick pattern, snare on 2&4 with ghosts, shuffled hats, subtle syncopation
- Light fill near bar 4 and bar 8, not overcrowded
- Space for pads/bass (avoid constant max density)

See [AI_Groove_Writer_Project_Plan.md](AI_Groove_Writer_Project_Plan.md) sections 12–13 for full preset details and prompt templates.
