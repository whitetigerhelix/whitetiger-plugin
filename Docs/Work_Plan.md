# Work Plan

Implementation roadmap for AI Groove Writer. Milestones are roughly sequential, but some tasks within a milestone can be parallelized.

---

## MVP Milestones

### Milestone 1: Project Scaffolding ✓

- [x] Project plan document ([AI_Groove_Writer_Project_Plan.md](AI_Groove_Writer_Project_Plan.md))
- [x] Documentation foundation (Architecture, Setup Guide, JSON Contract, Ideas, Work Plan)
- [x] README, CLAUDE.md, /groove skill, .gitignore
- [x] Repo structure: create `m4l/patches/`, `service/` directories
- [x] License changed to AGPL-3.0

### Milestone 2: Python Service — Mock Mode ✓

- [x] Set up Python project (`pyproject.toml`, `requirements.txt`)
- [x] Dependencies: FastAPI, Pydantic v2, uvicorn, python-dotenv
- [x] Virtual environment: `service/.venv/` (Python 3.12.10)
- [x] Implement `service/models.py` — Pydantic v2 request/response models
- [x] Implement `service/app.py` — `/health`, `/generate`, `/presets`, `/usage` endpoints
- [x] Implement `service/presets.py` — all 5 preset registrations with prompt templates
- [x] Implement `service/mock_grooves.py` — musically sensible mock patterns per preset
- [x] Implement `service/usage.py` — LLM credit consumption tracking (JSONL log + stats)
- [x] Tests: 33 tests passing (models + endpoints)

### Milestone 3: M4L Device — Clip Writing Pipeline (scaffolding ✓, manual patching required)

- [x] JS helper files created in `m4l/js/`:
  - [x] `groove_http.js` — HTTP client (GET/POST to service, outlets for response + status)
  - [x] `note_writer.js` — clip writer (Live API: highlighted clip slot → remove/write notes)
  - [x] `post_process.js` — swing, humanize, velocity jitter (seeded RNG, all in Max)
- [x] Build guide: [M4L_Build_Guide.md](M4L_Build_Guide.md) — step-by-step Max patching instructions
- [ ] **Manual:** Create M4L device skeleton (`AIGrooveWriter.amxd`) — requires Max editor
- [ ] **Manual:** Wire UI patch (prompt, preset dropdown, control dials, status, buttons)
- [ ] **Manual:** Connect JS objects per wiring diagram in build guide
- [ ] **Manual:** Validate end-to-end with mock service response

### Milestone 4: LLM Integration ✓

- [x] Provider abstraction layer (`service/llm_provider.py`): `LLMProvider` ABC, `LLMResult` dataclass, `get_provider()` factory
- [x] Azure OpenAI provider (`AzureOpenAIProvider`) — reads env vars, calls `openai` SDK
- [x] Anthropic provider stub (`AnthropicProvider`) — raises NotImplementedError with helpful message
- [x] Prompt construction (`service/prompts.py`): system prompt (strict JSON output rules) + user prompt (preset template filling)
- [x] Response parsing and validation (`service/validation.py`): JSON extraction (handles code fences, preamble), note clamping to clip bounds
- [x] Max note count enforcement (5000)
- [x] Disk cache (`service/cache.py`): SHA-256 keyed, JSON on disk
- [x] LLM call retry (up to 3 attempts on parse failure)
- [x] Cost estimation: per-model pricing lookup table
- [x] `service/app.py` wired with full LLM path: cache check → prompt build → LLM call → validate → cache put → usage log
- [x] 100 tests passing (models, endpoints, prompts, validation, cache, provider)

### Milestone 5: Post-Processing & Determinism (mostly done via M3 JS)

- [x] Swing algorithm in `post_process.js` — off-beat 8ths get full delay, 16ths get half
- [x] Humanize timing: seeded xorshift32 RNG, ms→beats conversion
- [x] Velocity jitter: seeded random ±offset, clamped 1–127
- [x] Variation mode: `variation` field on GenerateRequest, effective seed = `seed + variation`, different cache keys per variation
- [ ] Seed reproducibility verification (same seed + request = same output) — deferred to end-to-end testing with M4L device

### Milestone 6: Caching & Reliability (mostly done via M4)

- [x] Disk cache: SHA-256 hash of request → `service/cache/<hash>.json`
- [x] Retry policy for LLM JSON parse failures (3 retries)
- [x] Graceful error handling: service errors → `GenerateResponse` with `ok=false` + message
- [x] Timeout handling: configurable `LLM_TIMEOUT_SECONDS` (default 30s), fallback to variation=0 cached result on failure
- [x] Logging (request/response, errors, cache hits/misses via usage.py)

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
