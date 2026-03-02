# Work Plan

Implementation roadmap for AI Groove Writer. Milestones are roughly sequential, but some tasks within a milestone can be parallelized.

---

## MVP Milestones

### Milestone 1: Project Scaffolding

- [x] Project plan document ([AI_Groove_Writer_Project_Plan.md](AI_Groove_Writer_Project_Plan.md))
- [ ] Documentation foundation (Architecture, Setup Guide, JSON Contract, Ideas, Work Plan)
- [ ] README, CLAUDE.md, /groove skill, .gitignore
- [ ] Repo structure: create `m4l/patches/`, `service/` directories

### Milestone 2: Python Service — Mock Mode

- [ ] Set up Python project (`pyproject.toml` or `requirements.txt`)
- [ ] Dependencies: FastAPI, Pydantic v2, uvicorn
- [ ] Implement `service/models.py` — Pydantic request/response models (see [JSON Contract](JSON_Contract.md))
- [ ] Implement `service/app.py` — `/health` and `/generate` endpoints, mock grooves
- [ ] Implement `service/presets.py` — preset registry (IDs, defaults, prompt templates)
- [ ] Basic tests for models and endpoint responses

### Milestone 3: M4L Device — Clip Writing Pipeline

- [ ] M4L device skeleton (`AIGrooveWriter.amxd`)
- [ ] UI patch: prompt input, preset dropdown, control dials, status text, buttons
- [ ] Clip target: resolve highlighted clip slot, create clip when requested
- [ ] HTTP client: send JSON POST to localhost service via `maxurl`
- [ ] JSON parser: parse `GenerateResponse`
- [ ] Note writer: `remove_notes` → `set_notes` → `done` via Live API
- [ ] Validate end-to-end with mock service response

### Milestone 4: LLM Integration

- [ ] Design provider abstraction layer (interface for swappable LLM backends)
- [ ] Implement first provider (Azure OpenAI GPT-4o — or chosen alternative)
- [ ] Prompt construction: system prompt + preset template + user prompt + controls
- [ ] JSON response parsing with retry on malformed output
- [ ] Note validation and clamping to clip boundaries
- [ ] Max note count enforcement (5000)

### Milestone 5: Post-Processing & Determinism

- [ ] Swing algorithm in M4L
  - Off-beat 8ths: full delay (`swing × 1/6 beats`)
  - 16th positions: half delay
- [ ] Humanize timing: seeded RNG, ms→beats conversion (`humanize_ms / (60000/bpm)`)
- [ ] Velocity jitter: seeded random ±offset, clamped 1–127
- [ ] Seed reproducibility verification (same seed + request = same output)
- [ ] Variation mode: seed increment for iterative exploration

### Milestone 6: Caching & Reliability

- [ ] Disk cache: SHA-256 hash of request → `service/cache/<hash>.json`
- [ ] Retry policy for LLM JSON parse failures (configurable retry count)
- [ ] Graceful error handling: service errors → `GenerateResponse` with `ok=false` + message
- [ ] Timeout handling with fallback to last cached result
- [ ] Basic logging (request/response, errors, cache hits/misses)

### Milestone 7: Presets & UX Polish

- [ ] All 5 presets fully wired:
  - `breaks_atmos_130` — Atmospheric Breakbeats (primary)
  - `breaks_driving` — Progressive Breaks
  - `chill_psychill` — Downtempo / Psychill
  - `four_on_floor` — 4-to-the-Floor
  - `halftime_broken` — Half-Time / Broken
- [ ] Preset dropdown updates default control values in UI
- [ ] Summary text display from model response
- [ ] Error message display with clear status (Ready / Generating / Applied / Error)
- [ ] Variation and Randomize Seed buttons

### Milestone 8: Demo Hardening

- [ ] Prepare demo Ableton Live set with Drum Rack and empty clip slots
- [ ] Write demo script: 3 presets × 2 variations, under 5 minutes
- [ ] End-to-end smoke test (full flow from prompt to audible groove)
- [ ] Acceptance criteria verification (see [Project Plan](AI_Groove_Writer_Project_Plan.md) section 14)

---

## Post-MVP Phases

### Phase 2: Bass / Melody / Chords
- Extend `mode` to support: bass, melody, chords
- Scale/key selection and chord progression guidance
- Multi-lane generation (drums + bass + chords in one request or sequential)

### Phase 3: Semantic Sample Search
- Audio embeddings-based indexing of local sample libraries
- Search by text description or example audio
- Surface results in M4L device, load into Simpler/Drum Rack
- See [Ideas & Brainstorm](Ideas_and_Brainstorm.md) #2

### Phase 4: Cross-DAW (VST3)
- Port generation core to a shared library
- VST3 plugin for real-time MIDI output
- Companion app for clip export workflows

### Phase 5+: Future Vision
- Conversational music co-creation (see [Ideas & Brainstorm](Ideas_and_Brainstorm.md) #1)
- Sacred geometry audio effect (see [Ideas & Brainstorm](Ideas_and_Brainstorm.md) #3)
- AI music video generation (see [Ideas & Brainstorm](Ideas_and_Brainstorm.md) #4)

---

## Decision Log

Track key decisions and their rationale here as the project evolves.

| Date | Decision | Rationale |
|---|---|---|
| 2026-03-02 | LLM provider TBD, start with Azure OpenAI GPT-4o | $150/month credits available; may switch to Anthropic Claude for ethical reasons |
| 2026-03-02 | Provider abstraction in service architecture | Avoid lock-in; enable easy switching between Azure, Anthropic, local models |
| 2026-03-02 | Post-processing in Max, not LLM | Deterministic reproducibility from seed; keeps LLM focused on pattern intent |
| 2026-03-02 | Docs/ as single source of truth | Avoid stale duplicated content across CLAUDE.md, README, and code comments |
| 2026-03-02 | AGPL-3.0 license (changed from MIT) | Strongest copyleft — protects against commercial exploitation; if anyone runs a modified version as a service, they must release changes |
