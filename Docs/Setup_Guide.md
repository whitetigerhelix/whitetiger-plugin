# Setup Guide

## Prerequisites

- **Ableton Live 12.3.5+** (Suite edition, includes Max for Live)
- **Python 3.12+**
- **LLM API access** — Azure OpenAI, Anthropic, or other supported provider
- **Windows 64-bit** (primary development platform)
- **Git**

## Environment Variables

Create a `.env` file in the `service/` directory (gitignored by default):

```env
# LLM Provider Configuration
# --------------------------
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01

# Anthropic (alternative — when provider is switched)
# ANTHROPIC_API_KEY=your-api-key-here
# ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Service
SERVICE_PORT=8787
SERVICE_MOCK=0
```

| Variable | Description | Default | Required |
|---|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | — | Yes (if using Azure) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | — | Yes (if using Azure) |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | — | Yes (if using Azure) |
| `AZURE_OPENAI_API_VERSION` | Azure API version | `2024-02-01` | No |
| `ANTHROPIC_API_KEY` | Anthropic API key | — | Yes (if using Anthropic) |
| `ANTHROPIC_MODEL` | Anthropic model ID | — | Yes (if using Anthropic) |
| `SERVICE_PORT` | Service listen port | `8787` | No |
| `SERVICE_MOCK` | Enable mock mode (no LLM calls) | `0` | No |

## First-Time Setup

A setup script handles virtual environment creation, dependency installation, and verification. A virtual environment is required (other Python projects exist on this machine).

```bash
cd service

# Run the setup script (creates venv, installs deps, copies .env, runs tests)
./setup.sh

# If your Python 3.12+ isn't the default `python`, specify it:
PYTHON="C:/Users/chroje/AppData/Local/Programs/Python/Python312/python.exe" ./setup.sh
```

The script:
1. Verifies Python 3.12+ is available
2. Creates `.venv/` virtual environment (if it doesn't exist)
3. Upgrades pip and installs dependencies from `requirements.txt`
4. Copies `.env.example` to `.env` (if `.env` doesn't exist yet)
5. Runs all tests to verify everything works

**Re-run anytime** to update dependencies or verify the environment after pulling changes.

### Manual Setup

```bash
cd service
python -m venv .venv

# Activate (Windows cmd)
.venv\Scripts\activate

# Activate (Git Bash on Windows)
source .venv/Scripts/activate

pip install -r requirements.txt
```

The venv is at `service/.venv/` and is gitignored.

## Starting the Service

```bash
# Make sure venv is activated, then:
cd service
uvicorn app:app --host 127.0.0.1 --port 8787

# With auto-reload for development
uvicorn app:app --host 127.0.0.1 --port 8787 --reload
```

### Health Check

```bash
curl http://127.0.0.1:8787/health
# Expected: {"ok": true}
```

### Mock Mode

For developing the M4L device without making LLM calls:

```bash
SERVICE_MOCK=1 uvicorn app:app --host 127.0.0.1 --port 8787
```

Mock mode returns hardcoded groove patterns, useful for testing the full pipeline without burning API credits.

## Loading the M4L Device

1. Open Ableton Live 12
2. Create a MIDI track with a Drum Rack (or any drum instrument)
3. Drag `m4l/AIGrooveWriter.amxd` onto the MIDI track
4. Click an empty clip slot or select an existing MIDI clip
5. Choose a preset, optionally tweak controls
6. Press **Generate** to preview, then **Apply to Selected Clip** to write

## Running Tests

```bash
cd service
pytest -v
```

## Usage Tracking

The service tracks LLM credit consumption to help monitor costs.

- **Usage log:** `service/usage_log.jsonl` (gitignored) — each LLM call logged with tokens, cost, model, preset
- **Usage endpoint:** `GET /usage` returns summary stats (total requests, tokens, cost by model and preset)
- **Presets endpoint:** `GET /presets` returns all available presets with default control values

```bash
curl http://127.0.0.1:8787/usage
```

## Troubleshooting

### Service unreachable from Max

1. Confirm the service is running: `curl http://127.0.0.1:8787/health`
2. Check Windows Firewall — ensure port 8787 is not blocked for localhost
3. Verify the M4L device is configured to use the correct port
4. Check the Max console for HTTP error messages

### Generation works but no notes appear in clip

1. Verify the selected slot contains a **MIDI clip** (not an audio clip)
2. Confirm clip length is computed correctly: `bars × time_sig_num × (4.0 / time_sig_den)`
3. Check `set_notes` payload format in the Max console
4. Verify notes are within clip bounds (start + duration ≤ clip length)

### Groove feels off-grid or messy

1. Reduce `humanize_ms` (try 0 to test without humanization)
2. Lower `swing` value (try 0 for straight timing)
3. Check that post-processing clamps are not pushing notes past clip end
4. Verify seed is consistent if expecting reproducible results

### LLM returns invalid JSON

1. Check service logs for the raw LLM response
2. The service retries on JSON parse failures — check retry count in logs
3. Verify the prompt template is producing clear JSON-only instructions
4. Check cached responses in `service/cache/` for debugging
