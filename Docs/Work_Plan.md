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

### Milestone 3: M4L Device — Clip Writing Pipeline ✓

- [x] JS helper files created in `m4l/js/`:
  - [x] `groove_http.js` — HTTP client (GET/POST to service, outlets for response + status)
  - [x] `note_writer.js` — clip writer (Live API: highlighted clip slot → remove/write notes)
  - [x] `post_process.js` — swing, humanize, velocity jitter (seeded RNG, all in Max)
  - [x] `request_builder.js` — builds /generate request JSON from UI values (dict-like interface)
  - [x] `response_router.js` — routes service responses to outlets (plan, summary, status, presets)
- [x] Build guide: [M4L_Build_Guide.md](M4L_Build_Guide.md) — step-by-step Max patching instructions
- [x] Created M4L device (`AI Groove Writer.amxd`) in Max editor
- [x] Wired UI patch (prompt, preset dropdown, control dials, seed/variation/bars, summary, status)
- [x] Connected JS objects: request_builder → groove_http → response_router → post_process → note_writer
- [x] Validated end-to-end with mock service (117 notes generated and written to clip)
- **Note:** `note_writer.js` uses deprecated `replace_selected_notes` API (deprecated since Live 11). Works fine but should be modernized to `apply_note_modifications` before distribution.

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
- [x] 106 tests passing (models, endpoints, prompts, validation, cache, provider)

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

### Milestone 7: Presets & UX Polish ✓

- [x] All 5 presets fully wired:
  - `breaks_atmos_130` — Atmospheric Breakbeats (primary)
  - `breaks_driving` — Progressive Breaks
  - `chill_psychill` — Downtempo / Psychill
  - `four_on_floor` — 4-to-the-Floor
  - `halftime_broken` — Half-Time / Broken
- [x] Preset dropdown updates default control values in UI
- [x] Summary text display from model response
- [x] Error message display with status
- [x] Variation and Randomize Seed buttons (wired, auto-generate via delay → request_builder)
- [x] Modernize `note_writer.js`: replaced deprecated `replace_selected_notes` chain with `add_new_notes` (Live 11+ API)
- [x] `response_router.js`: store preset defaults from `/presets`, output on outlet 5 when preset selected or surprise controls arrive
- [x] Per-request model override (`model` field on GenerateRequest)
- [x] Optional request fields for layered percussion: `allowed_pitches`, `instrument_hints`
- [x] LLM-driven Surprise Me feature: `POST /surprise` endpoint, `SurpriseRequest`/`SurpriseResponse` models, LLM-generated prompt + controls + sound suggestion
- [x] `response_router.js` surprise flow: outlet 7 emits request JSON, outlet 6 emits generated prompt text, outlet 5 emits matched controls
- [x] `begin_generate` message clears stale summary/status before request
- [x] Busy indicator on outlet 8 (1=working, 0=idle) for LED/label/panel visual feedback
- [x] UI bars/time-signature authority enforced in validation (clip settings always win over LLM metadata)
- [x] Windows-native setup: `setup.ps1`, `setup.cmd`, `configure_env.ps1`, `configure_env.cmd`
- [x] Azure OpenAI setup walkthrough in Setup Guide
- [x] Provider capability metadata and name normalization in `llm_provider.py`
- [x] Interactive Claude skills: `whitetiger-plugin-assistant`, `llm-config`, `cloud-provider`, `groove` (polished)

### Milestone 8: Demo Hardening (in progress)

- [x] Presentation mode polish (horizontal layout, panels, busy indicators)
- [x] Prompt quality improvements: system prompt with bar-filling rules, velocity dynamics, phrase structure, loop continuity, 4-bar few-shot reference
- [x] Preset templates refactored: style-only guidance, bar/BPM/time-sig constraints moved to authoritative clip constraints section in prompt builder
- [x] Surprise prompt enhanced for richer, production-ready generated prompts
- [x] Preset defaults tightened for better musical feel (lower swing/humanize/jitter)
- [x] Drum fill vocabulary added to system prompt and all preset templates
- [x] Instrument context scanner (`instrument_scanner.js`): reads Drum Rack pad names, pitches, sample filenames from Live API
- [x] `instrument_context` field on GenerateRequest, wired into prompt and cache key
- [x] Clip reader (`clip_reader.js`): reads MIDI notes from highlighted clip in groove JSON format
- [x] `reference_pattern` field on GenerateRequest: user can supply a real MIDI clip as a quality/style reference for the LLM
- [x] Validation coverage warning: logs when LLM output doesn't span all configured bars
- [ ] Prepare demo Ableton Live set with Drum Rack and empty clip slots
- [ ] Write demo script: 3 presets × 2 variations, under 5 minutes
- [ ] End-to-end smoke test (full flow from prompt to audible groove)
- [ ] Acceptance criteria verification (see [Project Plan](AI_Groove_Writer_Project_Plan.md) section 14)

### Milestone 9: Server Management from M4L Device ✓

Start/stop the Python service and configure API keys directly from the M4L device — no terminal needed after initial setup. Full plan: [Plan_Server_Management.md](Plan_Server_Management.md)

- [x] `service/runtime_config.py` — thread-safe in-memory config store (get/set with env var fallback)
- [x] `service/models.py` — add `ConfigRequest`, `ConfigStatusResponse` models
- [x] `service/llm_provider.py` — switch `os.getenv()` to `runtime_config.get_config()`
- [x] `service/app.py` — add `POST /config`, `GET /config/status`, `POST /shutdown` endpoints
- [x] `service/tests/conftest.py` — add `autouse` fixture for `clear_overrides()` cleanup
- [x] `service/tests/test_config.py` — tests for config and shutdown endpoints (13 tests)
- [x] `m4l/js/groove_http.js` — add `config`, `config_status`, `shutdown_service` message handlers
- [ ] `m4l/js/response_router.js` — add config status response routing (deferred to UI wiring phase)
- [ ] `m4l/js/server_launcher.js` — Node.js child process launcher (deferred)
- [ ] Documentation updates for device-side server management UI

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

| Date       | Decision                                                  | Rationale                                                                                                                                |
| ---------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-03-02 | LLM provider TBD, start with Azure OpenAI GPT-4o          | $150/month credits available; may switch to Anthropic Claude for ethical reasons                                                         |
| 2026-03-02 | Provider abstraction in service architecture              | Avoid lock-in; enable easy switching between Azure, Anthropic, local models                                                              |
| 2026-03-02 | Post-processing in Max, not LLM                           | Deterministic reproducibility from seed; keeps LLM focused on pattern intent                                                             |
| 2026-03-02 | Docs/ as single source of truth                           | Avoid stale duplicated content across CLAUDE.md, README, and code comments                                                               |
| 2026-03-02 | AGPL-3.0 license (changed from MIT)                       | Strongest copyleft — protects against commercial exploitation; if anyone runs a modified version as a service, they must release changes |
| 2026-03-03 | M4L device built, end-to-end mock MIDI generation working | Device manually patched in Max; 117 notes generated and written to clip via mock mode                                                    |
| 2026-03-03 | Per-request model override added to GenerateRequest       | Allows M4L device to select model/deployment without server restart                                                                      |
| 2026-03-03 | Server management plan (Milestone 9)                      | Enable start/stop service and API key config from within M4L device UI — see [Plan_Server_Management.md](Plan_Server_Management.md)      |
| 2026-03-04 | LLM-driven Surprise Me feature                            | `/surprise` endpoint generates prompt + controls + sound suggestion via LLM, replacing hardcoded palettes                                |
| 2026-03-04 | Busy indicator (outlet 8) on response_router              | Visual feedback for Generate/Surprise operations via LED, label color, or panel flash                                                    |
| 2026-03-04 | UI bars/time-sig authority                                | Validation enforces clip settings from UI, ignoring any conflicting LLM metadata                                                         |
| 2026-03-04 | Windows-native setup scripts                              | `setup.ps1`, `configure_env.ps1` with cmd wrappers replace bash-only workflow                                                            |
| 2026-03-04 | Prompt quality overhaul                                   | System prompt + preset templates enhanced with bar-filling rules, velocity dynamics, phrase structure, loop continuity                   |
| 2026-03-04 | Server management backend (Milestone 9)                   | `runtime_config.py`, `/config`, `/config/status`, `/shutdown` endpoints implemented with 13 tests                                        |
| 2026-03-04 | Instrument context scanning                               | `instrument_scanner.js` reads Drum Rack from Live API; LLM tailors patterns to available sounds                                          |
| 2026-03-04 | Clip reader + reference patterns                          | `clip_reader.js` reads MIDI clips; `reference_pattern` field lets users supply quality references to the LLM                             |
| 2026-03-04 | Preset templates refactored                               | Bar/BPM/time-sig removed from templates; authoritative clip constraints section in prompt builder prevents conflicts with UI             |
