# AI Groove Writer — Pivot Plan: GrooveSpec DSL + Multi-Candidate Scoring (No Training)

**Project:** AI Groove Writer (Max for Live MIDI device + local Python service)  
**Pivot goal:** Improve musical quality + uniqueness without training a custom model by:
1) shifting GPT-4o from “emit raw MIDI notes” → “emit a structured **GrooveSpec** (DSL)”, and  
2) generating multiple candidates and selecting the best via fast, deterministic heuristics, then  
3) rendering GrooveSpec → MIDI procedurally (seeded), and applying groove feel (swing/humanize).

**Primary genre:** progressive / atmospheric breakbeats @ ~130 BPM  
**Also supports:** downtempo/chillout/psychill, 4-to-the-floor

---

## 0) Why this pivot works

### What’s going wrong with “LLM outputs MIDI notes”
- LLMs aren’t trained specifically on symbolic drum performance, so raw note lists tend to be:
  - generic and “square”
  - inconsistent (bad densities, fills everywhere)
  - sometimes suspiciously similar to known patterns
  - error-prone JSON without strict constraints

### What we do instead
- LLM outputs **intent + constraints** (GrooveSpec).
- We procedurally generate notes with:
  - deterministic randomness (seed)
  - hard musical rules and bounds
  - novelty levers (controlled variation)
- We generate *many* candidates cheaply, score them, keep the best.
- This creates grooves that are:
  - unique (not copied)
  - consistent
  - controllable
  - reliably within clip bounds

---

## 1) High-level architecture (after pivot)

```
[M4L Device]
  - collects prompt + controls + preset
  - requests N candidates
  - displays top groove summary
  - Apply/Variation writes MIDI clip

           HTTP (localhost)
                 |
                 v
[Python Service]
  1) Build prompt -> GPT-4o -> GrooveSpec JSON (N times or batched)
  2) Validate GrooveSpec (strict schema)
  3) Render GrooveSpec -> MIDI Plan (seeded procedural)
  4) Score candidates (heuristics) + pick best K
  5) Return chosen plan + debug info (scores + summaries)
                 |
                 v
[Ableton Clip Writer] (in M4L)
  - writes returned MIDI plan
  - applies final swing/humanize if desired (optional; can also be done in service)
```

**Key change:** GPT-4o no longer emits `notes[]` directly.

---

## 2) New contract: GrooveSpec (DSL)

### Design principles
- Express musical intent as *parameters and pattern archetypes*.
- Keep it compact and schema-valid.
- Procedural renderer turns it into actual note events.
- Works across presets; extensible for bass/melody later.

### GrooveSpec schema (v1)
```json
{
  "version": 1,
  "mode": "drums",
  "bars": 8,
  "time_sig_num": 4,
  "time_sig_den": 4,
  "seed": 12345,

  "style": {
    "preset_id": "breaks_atmos_130",
    "bpm": 130,
    "vibe_tags": ["atmospheric", "progressive", "breakbeat"],
    "energy": 0.65,
    "dark_bright": 0.45,
    "tight_loose": 0.55
  },

  "structure": {
    "phrase_bars": 4,
    "variation_strength": 0.35,
    "fill_bars": [4, 8],
    "fill_max_beats": 1.0
  },

  "lanes": {
    "kick": {
      "enabled": true,
      "archetype": "broken_two_step",
      "density": 0.70,
      "syncopation": 0.65,
      "pattern_bias": ["downbeat_support", "offbeat_push"],
      "velocity": { "min": 90, "max": 120 },
      "dur_beats": 0.25
    },
    "snare": {
      "enabled": true,
      "archetype": "backbeat_with_ghosts",
      "backbeat": [2, 4],
      "ghost_density": 0.25,
      "flam_chance": 0.08,
      "velocity": { "min": 70, "max": 115 },
      "ghost_velocity": { "min": 25, "max": 55 },
      "dur_beats": 0.25
    },
    "hats": {
      "enabled": true,
      "archetype": "swung_8ths_with_bursts",
      "base_subdivision": 8,
      "burst_chance": 0.22,
      "open_hat_chance": 0.10,
      "velocity": { "min": 35, "max": 85 },
      "dur_beats": 0.25
    },
    "perc": {
      "enabled": true,
      "archetype": "minimal_texture",
      "density": 0.25,
      "syncopation": 0.55,
      "velocity": { "min": 30, "max": 80 },
      "dur_beats": 0.25
    },
    "crash": {
      "enabled": true,
      "archetype": "phrase_hits",
      "hits": [
        { "bar": 1, "beat": 1.0, "prob": 0.35 },
        { "bar": 5, "beat": 1.0, "prob": 0.25 }
      ],
      "velocity": { "min": 70, "max": 110 },
      "dur_beats": 0.25
    }
  },

  "feel": {
    "swing": 0.35,
    "humanize_ms": 8,
    "velocity_jitter": 6
  },

  "notes_allowed": {
    "kick": 36,
    "snare": 38,
    "clap": 39,
    "hat_closed": 42,
    "hat_open": 46,
    "crash": 49,
    "ride": 51,
    "tom_low": 45,
    "tom_mid": 47,
    "tom_high": 50
  },

  "model_summary": "Broken-beat kick with airy swung hats, ghost snares, subtle 1-beat fills at bar 4 and 8."
}
```

### Allowed archetypes (v1)
These are *renderer-implemented* behaviors. LLM picks among them.
- kick: `four_on_floor`, `broken_two_step`, `syncopated_breaks`, `halftime_sparse`
- snare: `backbeat`, `backbeat_with_ghosts`, `halftime_backbeat`
- hats: `straight_8ths`, `swung_8ths`, `swung_8ths_with_bursts`, `rolling_16ths`
- perc: `minimal_texture`, `syncopated_hits`, `tom_call_response`
- crash: `phrase_hits`, `none`

**Rule:** If the LLM outputs an unknown archetype, service must reject/repair.

---

## 3) Renderer: GrooveSpec → MIDI Plan (procedural)

### Output MIDI Plan schema (same as before)
```json
{
  "ok": true,
  "summary": "...",
  "plan": {
    "version": 1,
    "mode": "drums",
    "bars": 8,
    "time_sig_num": 4,
    "time_sig_den": 4,
    "notes": [
      { "pitch": 36, "start_beats": 0.0, "dur_beats": 0.25, "vel": 110, "mute": 0 }
    ]
  },
  "debug": {
    "candidates": [
      { "id": "c1", "score": 0.82, "reasons": ["solid backbeat", "good hat energy", "restrained fill"] }
    ]
  }
}
```

### Lane rendering behaviors (v1)
- Kick `broken_two_step`: anchors + controlled offbeats; density controls hits/bar.
- Snare `backbeat_with_ghosts`: strong 2&4 + ghost placement around them.
- Hats `swung_8ths_with_bursts`: base 8ths plus occasional 16th bursts; optional open hats.
- Perc `minimal_texture`: sparse offbeat hits, avoids key accents.
- Crash `phrase_hits`: phrase-start accents with probabilities.

### Variation & fills
- Phrase length usually 4 bars.
- `variation_strength` changes hats/perc per phrase and can swap 1–2 kick hits.
- Fill bars add up to `fill_max_beats` of extra activity near end-of-bar; keep restrained.

### Feel (apply once)
Choose one place to apply swing/humanize to avoid double-processing:
- Recommended: apply in **service** so M4L just writes notes.

---

## 4) Multi-candidate generation & scoring

### Candidate generation
Per request, generate `N` candidates (default 12):
- Same prompt/preset
- Different seed per candidate: `seed + i*9973` (prime multiplier)

For each candidate:
1) GPT-4o → GrooveSpec JSON
2) Validate (schema)
3) Render → MIDI Plan
4) Score → pick best (optionally return top K)

### Scoring heuristics (progressive/atmos breaks)
Compute sub-scores and weighted sum (0..1):
1) Snare backbeat strength (2&4 present, ghosts not excessive)
2) Kick archetype adherence (avoid strict 4-on-floor unless preset)
3) Hat energy & air (target ~6–12 hits/bar; penalize >16)
4) Fill restraint (mainly bars 4/8; <= fill_max_beats)
5) Collision penalty (avoid constant kick+snare+crash pileups)
6) Variation balance (subtle evolution, not identical or chaotic)

Suggested weights:
- snare 0.22, kick 0.20, hats 0.18, fills 0.16, collisions 0.12, variation 0.12

Return debug:
- chosen score + top candidates with short reasons (for tuning)

---

## 5) Presets mapping (updated)

### breaks_atmos_130 (primary)
- Kick: `broken_two_step` / `syncopated_breaks`
- Snare: `backbeat_with_ghosts`
- Hats: `swung_8ths_with_bursts`
- Hat hits/bar target: 6–12
- Fill bars: [4,8], max 1 beat

### chill_psychill
- Lower density/energy; softer velocities
- Hat hits/bar target: 4–8
- Minimal fills (maybe only bar 8)

### four_on_floor
- Kick: `four_on_floor`
- Clap/snare on 2&4
- Light swing hats
- Hat hits/bar target: 6–10

---

## 6) Service API (post-pivot)

`POST /generate` adds:
- `candidate_count` (default 12)
- `return_top_k` (default 1)
- `debug` (default false)

Response includes:
- chosen MIDI Plan
- optional debug (scores, reasons)

---

## 7) GPT-4o prompting (GrooveSpec-only)

Hard requirements:
- JSON only; match schema exactly; no extra keys.
- Use only allowed archetypes and GM mapping keys.
- Respect bars/time sig/bpm/fill bars/fill length.

Recommended: include 1–2 few-shot GrooveSpec examples (breaks + four-on-floor) to stabilize outputs.

---

## 8) 5-day implementation plan (pivot)

Day 1: GrooveSpec Pydantic + renderer skeleton (backbeat + hats + basic kick)  
Day 2: Candidate loop + scoring + return best + debug  
Day 3: Implement key archetypes for atmos breaks; tune scoring targets  
Day 4: Fills + phrase variation + deterministic seed behavior  
Day 5: Hardening: repair/retry schema failures, disk cache, timeouts, demo set

---

## 9) Repo changes

```
service/
  groove_spec_models.py
  groove_renderer.py
  groove_scoring.py
  groove_presets.py
  azure_groove_spec.py
  cache.py
  app.py
docs/
  AI_Groove_Writer_PIVOT_GrooveSpec_Plan.md
```

---

## 10) Pydantic starter snippet (GrooveSpec skeleton)

```python
from pydantic import BaseModel, Field, conint, confloat
from typing import List, Literal, Dict, Optional

KickArch = Literal["four_on_floor","broken_two_step","syncopated_breaks","halftime_sparse"]
SnareArch = Literal["backbeat","backbeat_with_ghosts","halftime_backbeat"]
HatArch  = Literal["straight_8ths","swung_8ths","swung_8ths_with_bursts","rolling_16ths"]
PercArch = Literal["minimal_texture","syncopated_hits","tom_call_response"]
CrashArch= Literal["phrase_hits","none"]

class VelocityRange(BaseModel):
    min: conint(ge=1, le=127)
    max: conint(ge=1, le=127)

class KickLane(BaseModel):
    enabled: bool = True
    archetype: KickArch
    density: confloat(ge=0, le=1) = 0.7
    syncopation: confloat(ge=0, le=1) = 0.6
    velocity: VelocityRange
    dur_beats: confloat(gt=0) = 0.25

class GrooveSpec(BaseModel):
    version: int = 1
    mode: Literal["drums"] = "drums"
    bars: conint(ge=1, le=64) = 8
    time_sig_num: conint(ge=1, le=12) = 4
    time_sig_den: conint(ge=1, le=16) = 4
    seed: int
    # ...add style/structure/lanes/feel/notes_allowed
```

---

**End of document.**
