# Architecture

## Overview

AI Groove Writer is a three-component system that generates drum MIDI patterns from natural-language prompts and writes them directly into Ableton Live clips.

```
 Ableton Live 12
 ┌──────────────────────────────┐
 │  M4L Device                  │
 │  (UI, clip I/O, post-process)│
 └──────────────┬───────────────┘
                │ HTTP POST (JSON)
                │ localhost:8787
                ▼
 ┌──────────────────────────────┐
 │  Python FastAPI Service      │
 │  (validation, caching,       │
 │   prompt construction)       │
 └──────────────┬───────────────┘
                │ HTTPS
                ▼
 ┌──────────────────────────────┐
 │  LLM Provider                │
 │  (structured JSON response)  │
 └──────────────────────────────┘
```

## Components

### Max for Live Device

The M4L device is the user-facing component running inside Ableton Live. It handles:

- **UI**: Controls, prompt input, preset dropdown, status display
- **Clip targeting**: Resolves the highlighted clip slot in the Ableton session
- **HTTP client**: Sends JSON requests to the local Python service
- **JSON parsing**: Parses the structured MIDI plan from the response
- **Note writing**: Converts the MIDI plan into Ableton clip notes via the Live API
- **Post-processing**: Applies swing, humanize, and velocity jitter (deterministic, seeded)

HTTP is handled via `XMLHttpRequest` in the `groove_http.js` JS object. The device communicates only with `localhost` — never directly with an external LLM provider.

**JS module chain:** `request_builder.js` → `groove_http.js` → `response_router.js` → `post_process.js` → `note_writer.js`

| Module | Role |
|--------|------|
| `request_builder.js` | Collects UI values into a JSON request (dict-like `set key value` interface) |
| `groove_http.js` | HTTP POST/GET to the Python service |
| `response_router.js` | Routes responses by type (generate → plan+summary, presets → umenu, health → status) |
| `post_process.js` | Swing, humanize timing, velocity jitter (seeded xorshift32 RNG) |
| `note_writer.js` | Writes processed notes into the highlighted Ableton clip via Live API |

### Python FastAPI Service

A local companion service running on the same machine as Ableton. Responsibilities:

- Receives `GenerateRequest` JSON from the M4L device
- Constructs the LLM prompt from preset templates, user input, and control values
- Calls the LLM provider and parses the structured JSON response
- Validates and clamps notes to clip boundaries (Pydantic v2 models)
- Enforces max note count (5000)
- Caches results on disk keyed by SHA-256 hash of request fields
- Returns `GenerateResponse` JSON to the M4L device

Why a separate service (not embedded in Max)?
- Keeps API keys/secrets out of the Max device
- Simplifies HTTP, retries, caching, and JSON validation
- Python ecosystem is better suited for LLM client libraries
- Lets the Max device focus on UI and Ableton clip manipulation

### LLM Provider

The AI backend that generates the structured MIDI plan JSON. The service abstracts this behind a provider interface so the specific LLM can be swapped without changing the rest of the system.

**Provider options under consideration:**
- Azure OpenAI (GPT-4o) — initial development target
- Anthropic Claude — potential switch for ethical/quality reasons
- Local models — future possibility for offline use

The provider interface needs to support:
- Chat completions with system + user prompts
- Structured/JSON output mode (where available)
- Configurable via environment variables (endpoint, API key, model/deployment)
- Per-request model override via the `model` field on `GenerateRequest` (overrides the server default; included in cache key)

## Data Flow

### Generate Request (M4L → Service → LLM)

1. User configures controls and presses **Generate**
2. M4L device builds a `GenerateRequest` JSON (see [JSON Contract](JSON_Contract.md))
3. HTTP POST to `http://127.0.0.1:8787/generate`
4. Service checks disk cache — if hit, returns cached response immediately
5. Service constructs LLM prompt from preset template + user prompt + controls
6. Service calls LLM provider, receives raw JSON response
7. Service parses and validates response into `GenerateResponse`
8. Response returned to M4L device

### Apply to Clip (M4L internal)

1. User presses **Apply to Selected Clip** (or **Create+Apply**)
2. M4L resolves `live_set view highlighted_clip_slot`
3. If no clip exists and Create+Apply was used: `create_clip <length_beats>`
4. Remove existing notes: `remove_notes 0.0 <clip_length_beats> 0 127`
5. Apply post-processing chain to notes (swing → humanize → velocity jitter)
6. Batch write notes: `set_notes <N>` followed by note data and `done`

## Post-Processing Pipeline

Post-processing happens entirely in the M4L device, not in the LLM. This keeps the LLM focused on pattern intent while ensuring deterministic, reproducible results from a given seed.

**Order:**
1. **Swing** — Pushes off-beat 8th notes toward a triplet feel; 16th notes get half the delay
2. **Humanize (timing)** — Seeded random jitter in milliseconds, converted to beats
3. **Velocity jitter** — Seeded random offset, clamped to 1–127

All randomization uses the request's `seed` value for reproducibility. Same seed + same request = same output.

## Variation Mode

The `variation` field on `GenerateRequest` lets users iterate on the same prompt without changing it. The service computes an **effective seed** = `seed + variation`, which is passed to the LLM prompt and produces a different cache key. This means:

- `variation=0` (default) uses the seed as-is
- `variation=1, 2, 3...` each produce a fresh LLM call and a separate cache entry
- The M4L device can expose a "Next Variation" button that increments the counter

## Timeout & Fallback

The LLM call has a configurable timeout (`LLM_TIMEOUT_SECONDS` env var, default 30s). If all 3 retry attempts fail (timeout, network error, or JSON parse failure), the service attempts a **cached fallback**:

1. If `variation > 0`, look up the cached response for `variation=0` (the "base" result)
2. If found, return it with `[fallback]` prefix in the summary
3. If no fallback available, return an error response

This ensures users see *something* even if the LLM is slow or unreachable, as long as a base variation was previously cached.

## Security Boundary

- API keys and secrets live **only** in the Python service, loaded from environment variables
- The service binds to `127.0.0.1` (localhost only) — never `0.0.0.0`
- The M4L device never contacts external services directly
- `.env` files are gitignored
