# AI Groove Writer

AI Groove Writer is a Max for Live MIDI effect plus a local Python FastAPI service that generates structured drum MIDI from natural-language prompts and writes it directly into Ableton Live clips.

The current MVP focuses on progressive and atmospheric breakbeat workflows around 130 BPM, with deterministic variation controls for repeatable iteration.

## Key Capabilities

- Natural-language groove generation with style presets and musical control values.
- Local companion service for validation, caching, and provider abstraction.
- Structured JSON contract between Max for Live and Python service.
- Deterministic post-processing chain in Max: swing, humanize timing, velocity jitter.
- Clip writing to Ableton highlighted MIDI clip slot, including create-and-apply flow.

## Current Scope

- Drums-focused MIDI generation in a single clip lane.
- One clip target at a time via highlighted clip slot.
- General MIDI mapping baseline with optional pitch guidance for custom rack layering.
- Localhost-only service boundary for security.

## System Architecture

Ableton Live (M4L device) sends GenerateRequest JSON to local FastAPI, which builds prompts, calls configured provider, validates/clamps notes, caches results, and returns GenerateResponse for clip writing.

See [Docs/Architecture.md](Docs/Architecture.md) for full architecture and data flow.

## Requirements

- Ableton Live 12.3.5+ (Suite with Max for Live)
- Python 3.12+
- Windows 64-bit (primary target)
- Azure OpenAI credentials for real generation mode

## Quick Start

1. Prepare Python service

- Run setup from [service/setup.sh](service/setup.sh)
- This creates [service/.venv](service/.venv), installs dependencies, and runs tests

```bash
cd service
./setup.sh
```

2. Configure environment

- Copy [service/.env.example](service/.env.example) to [service/.env](service/.env)
- Set provider and credentials
- For real AI calls set `SERVICE_MOCK=0` and `LLM_PROVIDER=azure`

3. Start local service

- Launch uvicorn on localhost only
- Verify the health endpoint

```bash
cd service
.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8787
curl http://127.0.0.1:8787/health
```

4. Load device in Ableton

- Open [m4l/patches/AI Groove Writer.amxd](m4l/patches/AI%20Groove%20Writer.amxd)
- Place it on a MIDI track with Drum Rack
- Select a MIDI clip slot, choose preset, generate, and apply

For step-by-step setup details, see [Docs/Setup_Guide.md](Docs/Setup_Guide.md).

## Configuration Model

- API keys and provider settings are managed in [service/.env](service/.env) for v1.
- M4L does not store secrets in the device patch for this phase.
- Optional per-request model override is supported through the GenerateRequest field model.
- Optional request growth fields support custom layering guidance:
  - allowed_pitches
  - instrument_hints

Contract reference: [Docs/JSON_Contract.md](Docs/JSON_Contract.md).

## Testing

Service test suite lives under [service/tests](service/tests).

Recommended validation order:

1. Unit and contract tests via pytest
2. Service health and presets endpoint checks
3. Generate call checks in mock mode
4. Generate call checks in real Azure mode
5. End-to-end Ableton clip write verification

## Repository Structure

- [Docs](Docs): project documentation and source-of-truth specs
- [m4l/js](m4l/js): Max JavaScript modules for request, HTTP, routing, post-process, note writing
- [m4l/patches](m4l/patches): Max for Live device assets
- [service](service): FastAPI service, provider abstraction, validation, caching, tests

## Security Notes

- Service binds to localhost 127.0.0.1 only.
- Secrets stay in local environment configuration, not in patch/device files.
- No direct external provider calls from the M4L layer.

## Documentation Index

- [Docs/AI_Groove_Writer_Project_Plan.md](Docs/AI_Groove_Writer_Project_Plan.md)
- [Docs/Work_Plan.md](Docs/Work_Plan.md)
- [Docs/Architecture.md](Docs/Architecture.md)
- [Docs/JSON_Contract.md](Docs/JSON_Contract.md)
- [Docs/Setup_Guide.md](Docs/Setup_Guide.md)
- [Docs/M4L_Build_Guide.md](Docs/M4L_Build_Guide.md)
- [Docs/Plan_Server_Management.md](Docs/Plan_Server_Management.md)
- [Docs/Ideas_and_Brainstorm.md](Docs/Ideas_and_Brainstorm.md)

## License

Licensed under AGPL-3.0-or-later. See [LICENSE](LICENSE).
