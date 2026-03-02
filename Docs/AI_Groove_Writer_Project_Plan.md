# AI Groove Writer (Max for Live) — Project Plan & MVP Spec

**Project:** AI Groove Writer  
**Target host:** Ableton Live 12 (Suite) + Max for Live  
**Platform:** Windows (64-bit)  
**Primary genre focus:** Progressive / atmospheric breakbeats (≈130 BPM), with presets for chillout/psychill and 4-to-the-floor.

---

## 1) MVP Summary

### What the MVP does
A Max for Live MIDI device that:
1. Accepts a natural-language prompt (plus a style preset and a few musical controls).
2. Sends a request to a local Python service on `localhost`.
3. The Python service calls Azure OpenAI and returns a **structured JSON “MIDI plan”** (notes with beat times, durations, velocities).
4. The M4L device **writes** that plan into the currently selected Ableton MIDI clip:
   - If a clip is selected, it overwrites its notes (MVP behavior).
   - If no clip exists, it can create a clip and then write notes.
5. Applies deterministic **swing + humanize** and supports **seed + variation** for repeatable iteration.

### MVP constraints (to prevent scope creep)
- **Drums only** (MIDI notes targeting GM drum pitches).
- One clip at a time (the highlighted clip slot).
- Online AI (Azure) with caching + graceful error handling.
- Presets drive prompt templates and default control values.
- No audio processing; only MIDI clip authoring.

---

## 2) Why Max for Live + Local Service

### Why Max for Live
- M4L can **author MIDI clips in Live** (create/edit notes directly in the arrangement/session clip).
- Fast, DAW-native prototyping; great demo value.

### Why a local Python “companion service”
A small local service running on the same machine:
- Keeps Azure keys/secrets out of the Max device.
- Simplifies networking, retries, caching, JSON validation.
- Lets the Max device focus on UI + Ableton clip manipulation.

**Data flow**
```
[M4L Device] --HTTP--> [Local Python Service] --HTTPS--> [Azure OpenAI]
     |                         |
     +---- writes MIDI clip <---+
```

---

## 3) User Experience (Demo Flow)

1. Add **AI Groove Writer** to a MIDI track (ideally with Drum Rack).
2. Click an empty clip slot or select an existing MIDI clip.
3. Choose a preset (e.g., **Atmospheric Breakbeats (130)**).
4. Optionally tweak controls: bars, density, complexity, swing, humanize, seed.
5. Press **Generate** (preview result + status).
6. Press **Apply to Selected Clip** (or **Create+Apply**).
7. Hit play. Use **Variation** to iterate.

---

## 4) Device UI & Controls

### Core controls
- **Prompt** (multiline)
- **Style Preset** (dropdown)
- **Bars** (1–32) — default: 8
- **Density** (0–1) — default: varies by preset
- **Complexity** (0–1) — default: varies by preset
- **Swing** (0–1) — default: varies by preset
- **Humanize (ms)** (0–25) — default: 6–10
- **Velocity Jitter** (0–15) — default: 4–8
- **Seed** (integer) + **Randomize Seed**
- Buttons:
  - **Generate (Preview)** — calls service and stores result
  - **Apply to Selected Clip** — writes stored result into clip
  - **Create+Apply** — creates clip if needed, then writes
  - **Variation** — increments seed (or uses mutate mode) and regenerates

### Readouts
- **Status**: Ready / Generating… / Applied / Error
- **Summary**: short text description from the model

---

## 5) Ableton Clip Targeting & Write Behavior

### Target selection
- Always operates on `live_set view highlighted_clip_slot`.
- If highlighted slot has no clip:
  - `Create+Apply` creates a clip of requested length.
  - `Apply` shows error (“No clip selected. Use Create+Apply.”)

### Clip length in beats
Let:
- `beats_per_bar = time_sig_num * (4.0 / time_sig_den)`
- `clip_length_beats = bars * beats_per_bar`

### MVP write behavior
- **Overwrite**: remove notes in the clip region, then write the generated notes.

---

## 6) MIDI Representation (JSON Contract)

This contract is the “truth” that both the Python service and Max device must obey.

### Request: `GenerateRequest` (M4L → Python)
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
  "drum_map": "gm"
}
```

### Response: `GenerateResponse` (Python → M4L)
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

### Units & rules
- `start_beats` and `dur_beats` are in **quarter-note beats** (Ableton-friendly).
- Notes must satisfy:
  - `0 <= pitch <= 127`
  - `start_beats >= 0`
  - `dur_beats > 0`
  - `start_beats + dur_beats <= clip_length_beats` (service should clamp; Max double-checks)
  - `1 <= vel <= 127`
  - `mute` is 0 or 1

---

## 7) Drum Mapping (GM for MVP)

Using General MIDI drum pitches (works well with Drum Rack defaults and common kits):
- Kick: 36
- Snare: 38
- Clap: 39
- Closed Hat: 42
- Open Hat: 46
- Ride: 51
- Crash: 49
- Low Tom: 45, Mid Tom: 47, High Tom: 50

**MVP note set (recommended)**
- Kick (36), Snare (38), Closed Hat (42), Open Hat (46), Perc/Clap (39), Crash (49)

---

## 8) Post-Processing in M4L (Swing + Humanize + Determinism)

### Why do swing/humanize in Max (not in the model)
- Deterministic, reproducible results from a seed.
- Avoids the model producing “messy” timing; keeps the model focused on pattern intent.

### Swing algorithm (practical)
Assume swing targets off-beat 8ths and lightly affects 16ths.

Definitions:
- `max8thDelayBeats = 1/6` (push toward triplet feel)
- `delay8 = swing * max8thDelayBeats`

For each note:
- `pos = start_beats % 1.0`
- If `pos` is ~0.5 (offbeat 8th), apply full delay: `start += delay8`
- If `pos` is ~0.25 or ~0.75 (16ths), apply half: `start += delay8 * 0.5`

Clamps:
- Ensure `start` does not exceed `clip_length_beats - dur`
- Ensure monotonic safety (don’t push past next grid if you enforce strict quantization)

### Humanize (timing)
- Compute beat duration in ms: `beat_ms = 60000 / bpm`
- Convert ms to beats: `humanize_beats = humanize_ms / beat_ms`
- Apply seeded random jitter: `start += rand(-humanize_beats, +humanize_beats)`

### Humanize (velocity)
- `vel += rand(-velocity_jitter, +velocity_jitter)` with clamp 1..127

### Seeded RNG
- Seed is part of request; both Max and Python should treat it as determinism anchor.
- Variation uses either:
  - `seed += 1` (simple), or
  - `seed = hash(seed, timestamp)` when “Randomize Seed” is clicked.

---

## 9) Max for Live Implementation Notes

### Recommended device modules (patch organization)
1. **UI**: controls, prompt box, preset dropdown, status text
2. **Clip Target**: resolve highlighted clip slot; create clip when requested
3. **HTTP Client**: send JSON request to localhost
4. **JSON Parser**: parse response into `dict`
5. **Note Writer**: convert `notes[]` into Ableton clip note API calls
6. **Post-Process**: swing/humanize before writing
7. **State**: store last response and last request for Apply/Variation

### HTTP in Max
Options:
- `maxurl` (native Max HTTP) for simplest integration
- `node.script` for more control if you prefer JS and async patterns

MVP suggestion: start with **maxurl** (fastest to wire).

### Writing notes into the clip (Ableton Live API)
High-level sequence:
1. Resolve highlighted clip slot object.
2. If needed, create clip: `create_clip <length_beats>`
3. Get clip object.
4. Remove existing notes: `remove_notes 0.0 <clip_length_beats> 0 127`
5. Batch write:
   - `set_notes <N> <pitch start dur vel mute> ...`
   - `done`

---

## 10) Python Service Spec (FastAPI)

### Endpoints
- `GET /health` → `{ "ok": true }`
- `POST /generate` → accepts `GenerateRequest`, returns `GenerateResponse`
- (Optional) `GET /presets` → returns preset definitions for UI auto-population

### Responsibilities
- Call Azure OpenAI (chat completion) to produce a MIDI plan JSON.
- Validate and clamp notes to clip boundaries.
- Enforce max note count (e.g., 5000).
- Cache results on disk keyed by request hash.
- Handle retries when JSON parsing fails.

### Environment variables
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION` (if needed)
- `SERVICE_PORT` (default 8787)

### Caching
- `cache_key = sha256(prompt + preset_id + clip + controls + seed + drum_map)`
- Disk cache: `service/cache/<cache_key>.json`

---

## 11) Prompting Strategy (Reliable JSON Output)

### Goals
- Get **valid JSON only**, matching the contract.
- Keep output musically sensible and within clip bounds.
- Encourage genre-appropriate patterns without overfitting.

### System prompt (template)
Use a strict instruction set:
- Return ONLY JSON.
- Use quarter-note beats.
- Use GM drum pitches only (for MVP).
- Keep within length.
- Prefer repeatable structure with occasional fills.

### User prompt construction
Combine:
1. Preset template (genre guidance + instrumentation)
2. User prompt (freeform)
3. Controls (density/complexity/swing/humanize) as explicit text
4. Hard constraints (bars, bpm, time sig, pitch set)

---

## 12) Style Presets (MVP Set)

These presets primarily:
- Provide prompt templates
- Set default control values
- Constrain pattern “intent”

### Preset 1: Atmospheric Breakbeats (130) — **Primary**
- `preset_id`: `breaks_atmos_130`
- Defaults:
  - density: 0.75
  - complexity: 0.65
  - swing: 0.35
  - humanize_ms: 8
  - velocity_jitter: 6
- Template guidance:
  - broken kick pattern, snare on 2&4 with ghosts, shuffled hats, subtle syncopation
  - light fill near bar ends (4, 8) but not too busy
  - space for pads/bass (avoid constant max density)

### Preset 2: Progressive Breaks (Driving)
- `preset_id`: `breaks_driving`
- Defaults:
  - density: 0.80
  - complexity: 0.75
  - swing: 0.28
  - humanize_ms: 6
  - velocity_jitter: 5
- Template guidance:
  - more forward momentum, more hat energy, occasional ride accents
  - fill on bar 8 (end of phrase)

### Preset 3: Downtempo / Chillout / Psychill
- `preset_id`: `chill_psychill`
- Defaults:
  - density: 0.55
  - complexity: 0.45
  - swing: 0.22
  - humanize_ms: 10
  - velocity_jitter: 8
- Template guidance:
  - sparse groove, softer velocities, less busy hats
  - gentle percussive texture and occasional offbeat accents

### Preset 4: 4-to-the-Floor (House-ish)
- `preset_id`: `four_on_floor`
- Defaults:
  - density: 0.70
  - complexity: 0.45
  - swing: 0.18
  - humanize_ms: 6
  - velocity_jitter: 5
- Template guidance:
  - kick on every beat, snare/clap on 2&4
  - hats on 8ths/16ths with light swing
  - occasional small fill at phrase end

### Preset 5: Half-Time / Broken (Experimental)
- `preset_id`: `halftime_broken`
- Defaults:
  - density: 0.60
  - complexity: 0.70
  - swing: 0.30
  - humanize_ms: 9
  - velocity_jitter: 7
- Template guidance:
  - halftime snare feel, syncopated kicks, more negative space
  - tasteful glitch/percussion stutters (still MIDI)

---

## 13) Prompt Templates (Copy/Paste Ready)

Each preset creates a prompt like:

### Template: `breaks_atmos_130`
```
You are generating a DRUM MIDI pattern for a progressive / atmospheric breakbeat track around 130 BPM.
Style: broken-beat groove, tasteful syncopation, not overcrowded, lots of space for atmos and bass.
Drums allowed (GM): kick(36), snare(38), clap(39 optional), closed hat(42), open hat(46), crash(49 optional).
Structure: 8 bars, 4/4. Make it loop well. Add a subtle variation/fill near bar 4 and bar 8.
User notes: {USER_PROMPT}

Controls:
- density={DENSITY} (more hits when higher)
- complexity={COMPLEXITY} (more variation/fills when higher)
Return ONLY JSON matching the schema. Times are in quarter-note beats.
```

### Template: `chill_psychill`
```
Generate a DRUM MIDI pattern for downtempo/chillout/psychill.
Groove: relaxed, airy, sparse, gentle offbeat accents. Softer velocities.
Allowed drums: kick(36), snare(38), closed hat(42), open hat(46), light perc/clap(39 optional).
8 bars, 4/4, loopable, minimal fills.
User notes: {USER_PROMPT}
Return ONLY JSON, quarter-note beat units, within clip length.
```

### Template: `four_on_floor`
```
Generate a DRUM MIDI pattern for 4-to-the-floor house-ish groove around 130 BPM.
Kick on every beat, clap/snare on 2 and 4. Hats provide movement with light swing.
Allowed drums: kick(36), snare(38), clap(39), closed hat(42), open hat(46), crash(49 optional).
8 bars, 4/4, loopable, small fill at bar 8.
User notes: {USER_PROMPT}
Return ONLY JSON with quarter-note beat units.
```

(Driving breaks and halftime presets follow the same pattern with different guidance.)

---

## 14) Acceptance Criteria (MVP Done Definition)

### Functional
- [ ] Device generates drum MIDI from prompt and writes into selected clip.
- [ ] If no clip exists, Create+Apply creates one of correct length and writes notes.
- [ ] Swing, humanize, velocity jitter work and are reproducible from seed.
- [ ] Variation produces a different groove while preserving style/prompt.
- [ ] Preset dropdown changes defaults and influences generation.

### Reliability
- [ ] Service handles invalid JSON with retry and returns friendly error message.
- [ ] Max device shows clear status and doesn’t freeze on request.
- [ ] Notes always remain inside clip bounds.

### Demo readiness
- [ ] Demo Ableton set prepared with Drum Rack and empty clip slots.
- [ ] Demo script demonstrates 3 presets + 2 variations each in < 5 minutes.

---

## 15) Implementation Plan (5-Day Schedule)

### Day 1 — Clip writing pipeline
- Build M4L device skeleton.
- Implement: find highlighted clip slot → create clip → remove_notes → set_notes.
- Use a hardcoded JSON groove in Max to validate note writing.

### Day 2 — Service integration
- Build FastAPI service with `/health` and `/generate` returning mock JSON.
- M4L device sends request, parses response, applies notes.

### Day 3 — Azure + validation + caching
- Azure OpenAI call in Python.
- Parse + validate response (Pydantic), clamp bounds, enforce max notes.
- Disk cache by request hash.
- Retry policy for JSON parse failures.

### Day 4 — Presets + UX polish
- Implement presets with default control values and prompt templates.
- Add Variation and Randomize Seed.
- Add summary text + error messages.

### Day 5 — Demo hardening
- Add timeouts + graceful fallback (e.g., “use last cached”).
- Add basic logging.
- Prepare demo Ableton project and a tight demo script.

---

## 16) Suggested Repo Layout

```
ai-groove-writer/
  m4l/
    AIGrooveWriter.amxd
    patches/
      ui.maxpat
      http.maxpat
      clip_writer.maxpat
      post_process.maxpat
  service/
    app.py
    azure_client.py
    models.py          # Pydantic request/response + validators
    prompts.py         # preset templates
    presets.py         # preset registry
    cache.py
    requirements.txt
  docs/
    PROJECT_PLAN.md
    DEMO_SCRIPT.md
    TROUBLESHOOTING.md
```

---

## 17) Security & Key Handling

- Azure API key lives only in the Python service via environment variables.
- Do not store keys inside the `.amxd` device.
- For demo: local-only service binds to `127.0.0.1` not `0.0.0.0`.

---

## 18) Troubleshooting Checklist

### Max can’t reach service
- Confirm service is running: `GET http://127.0.0.1:8787/health`
- Check Windows firewall / port blocked
- Ensure Max is using the correct port

### Generation works but no notes appear
- Verify selected slot is a **MIDI clip** (not audio)
- Confirm clip length beats computed correctly
- Confirm `set_notes` payload is formatted exactly

### Groove feels off-grid
- Reduce humanize_ms
- Lower swing
- Ensure post-process clamps do not push notes past clip end

---

## 19) Roadmap (Post-MVP)

### Phase 2: Bass / Melody / Chords
- Extend `mode` and schema to support multiple lanes:
  - drums (GM map)
  - bass (single-note line with scale constraints)
  - melody (scale + range + motif controls)
  - chords (voicings + rhythm)
- Add “Scale / Key” selection and chord progression guidance.

### Phase 3: Sample search (semantic)
- Add embeddings-based indexing service.
- M4L device surfaces results and can load into Simpler/Drum Rack.

### Phase 4: Cross-DAW (VST3)
- Port generation core to a shared library.
- VST3 outputs MIDI in real-time; provide a companion app for clip export workflows.

---

## 20) Appendix: Pydantic Models (Starter)

```python
# service/models.py
from pydantic import BaseModel, Field, conint, confloat
from typing import List, Literal, Optional

class ClipInfo(BaseModel):
    bars: conint(ge=1, le=64) = 8
    time_sig_num: conint(ge=1, le=12) = 4
    time_sig_den: conint(ge=1, le=16) = 4
    bpm: confloat(ge=40, le=240) = 130

class Controls(BaseModel):
    density: confloat(ge=0, le=1) = 0.75
    complexity: confloat(ge=0, le=1) = 0.65
    swing: confloat(ge=0, le=1) = 0.35
    humanize_ms: confloat(ge=0, le=25) = 8
    velocity_jitter: conint(ge=0, le=15) = 6

class GenerateRequest(BaseModel):
    prompt: str
    preset_id: str
    mode: Literal["drums"] = "drums"
    clip: ClipInfo
    controls: Controls
    seed: int = 12345
    drum_map: Literal["gm"] = "gm"

class NoteEvent(BaseModel):
    pitch: conint(ge=0, le=127)
    start_beats: confloat(ge=0)
    dur_beats: confloat(gt=0)
    vel: conint(ge=1, le=127)
    mute: conint(ge=0, le=1) = 0

class MidiPlan(BaseModel):
    version: int = 1
    mode: Literal["drums"] = "drums"
    bars: int
    time_sig_num: int
    time_sig_den: int
    notes: List[NoteEvent] = Field(default_factory=list)

class GenerateResponse(BaseModel):
    ok: bool = True
    summary: str = ""
    plan: Optional[MidiPlan] = None
    error: Optional[str] = None
```

---

## 21) Appendix: Minimal Service Skeleton (Starter)

```python
# service/app.py
import os
from fastapi import FastAPI
from service.models import GenerateRequest, GenerateResponse

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    # TODO:
    # 1) cache lookup
    # 2) azure call -> JSON
    # 3) parse & validate -> GenerateResponse
    # For Day 1/2: return a hardcoded tiny groove
    plan = {
        "version": 1,
        "mode": "drums",
        "bars": req.clip.bars,
        "time_sig_num": req.clip.time_sig_num,
        "time_sig_den": req.clip.time_sig_den,
        "notes": [
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.25, "vel": 110, "mute": 0},
            {"pitch": 38, "start_beats": 1.0, "dur_beats": 0.25, "vel": 100, "mute": 0},
            {"pitch": 42, "start_beats": 0.5, "dur_beats": 0.25, "vel": 72,  "mute": 0},
        ],
    }
    return {"ok": True, "summary": "Starter groove (mock).", "plan": plan}
```

---

**End of document.**
