# AI Groove Writer — Claude Code Context

## Project

AI Groove Writer — a Max for Live MIDI device + Python FastAPI companion service for AI-generated drum grooves. Drums-only MVP targeting progressive/atmospheric breakbeats (~130 BPM), with presets for chill, house, and experimental styles.

- **Target DAW:** Ableton Live 12.3.5 (Suite, with Max for Live)
- **Platform:** Windows 64-bit
- **Python:** 3.12+
- **LLM Provider:** TBD (starting with Azure OpenAI GPT-4o, may switch to Anthropic Claude). Architecture is provider-agnostic — don't hardcode to any specific provider.

## Documentation (source of truth)

Detailed specs and reference material live in `Docs/`. Always consult these rather than duplicating content:

- [Docs/Architecture.md](Docs/Architecture.md) — system design, data flow, security boundary, provider abstraction
- [Docs/JSON_Contract.md](Docs/JSON_Contract.md) — request/response schemas, drum mapping, beat conventions, validation rules, presets
- [Docs/Setup_Guide.md](Docs/Setup_Guide.md) — prerequisites, env vars, running the service, troubleshooting
- [Docs/AI_Groove_Writer_Project_Plan.md](Docs/AI_Groove_Writer_Project_Plan.md) — full MVP spec (primary source of truth)
- [Docs/Work_Plan.md](Docs/Work_Plan.md) — implementation roadmap, milestones, decision log
- [Docs/M4L_Build_Guide.md](Docs/M4L_Build_Guide.md) — step-by-step Max for Live device building instructions
- [Docs/Ideas_and_Brainstorm.md](Docs/Ideas_and_Brainstorm.md) — future vision and brainstorm ideas

## Key Conventions

- **Beat units:** All timing in quarter-note beats (Ableton-native). See JSON Contract for details.
- **Drum mapping:** GM pitches for MVP (Kick=36, Snare=38, CH=42, OH=46, Clap=39, Crash=49). Full table in JSON Contract.
- **Post-processing:** Swing → humanize timing → velocity jitter. Happens in M4L, NOT in the LLM. All seeded RNG for reproducibility.
- **Clip length:** `bars × time_sig_num × (4.0 / time_sig_den)` beats.
- **LLM provider abstracted:** Service uses a provider interface. Don't import Azure/Anthropic SDK directly in app.py — route through the abstraction layer.
- **Security:** API keys only in the Python service (env vars). Service binds `127.0.0.1` only. Never `0.0.0.0`. Keys never in `.amxd` or committed to repo.

## Repo Structure

```
m4l/                         Max for Live device
  patches/                   .amxd device (built manually in Max editor)
  js/                        JS objects for Max's `js` runtime
    groove_http.js           HTTP client (POST /generate, GET /health etc.)
    note_writer.js           Clip writer (Live API note insertion)
    post_process.js          Swing, humanize, velocity jitter (seeded RNG)
service/                     Python FastAPI service (.venv/ for virtual env)
  app.py                     FastAPI entry point (/health, /generate, /presets, /usage)
  models.py                  Pydantic v2 request/response models
  presets.py                 Preset registry (5 presets, defaults, prompt templates)
  mock_grooves.py            Hardcoded mock groove patterns for dev
  prompts.py                 System + user prompt construction for LLM
  validation.py              LLM response parsing, JSON extraction, note clamping
  cache.py                   Disk cache (SHA-256 keyed)
  llm_provider.py            Provider abstraction (Azure OpenAI, Anthropic stub)
  usage.py                   LLM credit consumption tracking
  requirements.txt           Python dependencies
  setup.sh                   Setup script (venv + deps + tests)
  .env.example               Environment variable template
  tests/                     pytest test suite (100 tests)
Docs/                        Documentation (source of truth)
```

## Development Commands

```bash
# First-time setup (or re-run to update)
cd service && PYTHON="path/to/python3.12" ./setup.sh

# Activate venv (Git Bash on Windows)
source service/.venv/Scripts/activate

# Start the service (mock mode — default, no LLM calls)
cd service && uvicorn app:app --host 127.0.0.1 --port 8787 --reload

# Health check
curl http://127.0.0.1:8787/health

# Check usage stats
curl http://127.0.0.1:8787/usage

# Run tests
cd service && .venv/Scripts/python.exe -m pytest tests/ -v
```

## What NOT To Do

- Don't put API keys in the M4L device or commit `.env` files
- Don't bind the service to `0.0.0.0`
- Don't generate audio — this project is MIDI-only
- Don't do swing/humanize in the LLM prompt — that's deterministic post-processing in Max
- Don't exceed 5000 notes per response
- Don't hardcode to a specific LLM provider — use the abstraction layer
- Don't duplicate content that belongs in `Docs/` — link to it instead
