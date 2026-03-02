# AI Groove Writer

Max for Live MIDI device + Python companion service that generates drum grooves from natural-language prompts via AI, writing them directly into Ableton Live clips.

## What It Does

- Accept a natural-language prompt plus a style preset and musical controls
- Send the request to a local Python service, which calls an LLM (provider-swappable)
- Receive a structured JSON "MIDI plan" (notes with beat positions, durations, velocities)
- Write the plan into the currently selected Ableton MIDI clip
- Apply deterministic swing, humanize, and velocity jitter from a seed for repeatable iteration

**MVP scope:** Drums only (GM drum pitches), one clip at a time, 5 style presets.

## Architecture

```
[M4L Device]  ──HTTP POST──▸  [Python FastAPI]  ──HTTPS──▸  [LLM Provider]
  (UI, clip I/O,                (validation,                 (structured JSON
   post-process)                 caching, prompts)            response)
```

See [Docs/Architecture.md](Docs/Architecture.md) for full details.

## Quick Start

1. **Run setup** — Creates virtual environment and installs dependencies:
   ```bash
   cd service
   ./setup.sh
   ```

2. **Configure environment** — Copy `service/.env.example` to `service/.env` and fill in your LLM credentials. See [Docs/Setup_Guide.md](Docs/Setup_Guide.md).

3. **Start the service**
   ```bash
   cd service
   source .venv/Scripts/activate   # or .venv\Scripts\activate on Windows cmd
   uvicorn app:app --host 127.0.0.1 --port 8787
   ```

4. **Load in Ableton** — Drag `m4l/AIGrooveWriter.amxd` onto a MIDI track with a Drum Rack. Select a clip slot, choose a preset, generate.

## Repo Layout

```
whitetiger-plugin/
  m4l/                         Max for Live device + patches
    AIGrooveWriter.amxd
    patches/
  service/                     Python FastAPI service
    app.py                     FastAPI entry point
    models.py                  Pydantic v2 request/response models
    presets.py                 Preset registry (5 presets)
    mock_grooves.py            Mock groove patterns for dev
    usage.py                   LLM credit tracking
    requirements.txt
    setup.sh                   Setup script (venv + deps)
    tests/                     pytest test suite
  Docs/                        Documentation (source of truth)
```

## Documentation

| Document | Description |
|---|---|
| [Architecture](Docs/Architecture.md) | System design, data flow, security boundary |
| [Setup Guide](Docs/Setup_Guide.md) | Prerequisites, env vars, running the service |
| [JSON Contract](Docs/JSON_Contract.md) | Request/response schemas, drum mapping, validation |
| [Project Plan](Docs/AI_Groove_Writer_Project_Plan.md) | Full MVP spec (source of truth) |
| [Work Plan](Docs/Work_Plan.md) | Implementation roadmap and milestones |
| [Ideas & Brainstorm](Docs/Ideas_and_Brainstorm.md) | Future vision and ideas |

## License

AGPL-3.0 — see [LICENSE](LICENSE).
