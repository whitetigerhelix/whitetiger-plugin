# Plan: Server Management from Max for Live Device

## Context

Currently, users must manually start the Python service from a terminal (`uvicorn app:app ...`) and edit a `.env` file to configure API keys. This is fine for development but is a significant barrier to distribution. This plan adds the ability to start/stop the service and configure API keys directly from the Max for Live device — no terminal or text editor needed after initial setup (`setup.sh`).

## Approach: Tier B — Node.js Launcher + Runtime Config Endpoints

Users still need Python 3.12+ installed and must run `setup.sh` once. After that, everything is controlled from the M4L device.

**User flow after initial setup:**
1. Open Ableton, load the device
2. Click **Start Server** toggle → server starts automatically (using the venv Python)
3. Select provider, enter API key in the device UI → keys sent to service via HTTP
4. Generate grooves as usual
5. Close Ableton → server shuts down automatically (child process tied to Max)

---

## Implementation

### 1. New file: `service/runtime_config.py`

In-memory config store with thread-safe get/set. Provides:
- `set_config(key, value)` — set a runtime override for any known config key
- `get_config(key)` — returns runtime override if set, otherwise falls back to `os.getenv()`
- `get_config_status()` — returns dict with `provider`, `mock_mode`, `azure_configured`, `anthropic_configured` (booleans, never actual key values)
- `clear_overrides()` — reset all overrides (for test cleanup)

Known keys: `LLM_PROVIDER`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `SERVICE_MOCK`

### 2. Modify: `service/llm_provider.py`

Replace `os.getenv()` calls with `runtime_config.get_config()`:
- `AzureOpenAIProvider.__init__` (lines 73-76): endpoint, api_key, deployment, api_version
- `get_provider()` (line 165): LLM_PROVIDER

### 3. Add models: `service/models.py`

```python
class ConfigRequest(BaseModel):
    provider: str | None = None          # "azure" or "anthropic"
    mock_mode: bool | None = None
    azure_endpoint: str | None = None
    azure_api_key: str | None = None
    azure_deployment: str | None = None
    azure_api_version: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None

class ConfigStatusResponse(BaseModel):
    provider: str
    mock_mode: bool
    azure_configured: bool
    anthropic_configured: bool
```

### 4. Modify: `service/app.py`

Three new endpoints:

- **`POST /config`** — Accepts `ConfigRequest`, calls `set_config()` for each provided field, returns status. Validates provider is "azure" or "anthropic". Never logs key values.
- **`GET /config/status`** — Returns `ConfigStatusResponse` (what's configured, no secrets)
- **`POST /shutdown`** — Sends `SIGINT` to self after 0.5s delay (background thread) so the HTTP response can be sent first. Uvicorn handles SIGINT as graceful shutdown.

Also change the mock mode check (line 74) from `os.getenv("SERVICE_MOCK", "1")` to `runtime_config.get_config("SERVICE_MOCK") or "1"`.

### 5. New file: `m4l/js/server_launcher.js`

Node.js script for Max's `node.script` object. Handles:

| Message | Action |
|---------|--------|
| `start` | Spawn Python service (auto-detects venv at `service_dir/.venv/Scripts/python.exe` on Windows, `.venv/bin/python` on Mac) |
| `stop` | POST /shutdown, then force-kill after 3s as fallback |
| `status` | Report current state on outlet 0 |
| `python_path <path>` | Override Python executable path |
| `service_dir <path>` | Set path to `service/` directory |
| `port <number>` | Set port (default 8787) |

**Outlets:** 0 = status string (`stopped`/`starting`/`running`/`error: ...`), 1 = server stdout/stderr (debug)

Key behaviors:
- After spawn, polls `/health` up to 10 times at 1s intervals to confirm server is actually responding
- `windowsHide: true` prevents a console window appearing on Windows
- Child process is NOT detached — dies when Max closes (prevents orphans)
- `process.on("exit")` handler kills child as a safety net

### 6. Modify: `m4l/js/groove_http.js`

Add three new message handlers after `generate()` (line 66):
- `config <json>` — POST to `/config`
- `config_status` — GET `/config/status`
- `shutdown` — POST `/shutdown` with empty body

These reuse the existing `_post()` and `_get()` internal helpers.

### 7. Modify: `m4l/js/response_router.js`

- Add outlet 5 (`outlets = 6`) for config status JSON
- Add routing logic before the health check (line 64):
  - Object with `provider` field → config status response → outlet 5 + status message on outlet 2
  - Object with `updated` field → config update response → outlet 5 + status message on outlet 2
  - Object with `message` + `ok` → shutdown response → outlet 2

### 8. New file: `service/tests/test_config.py`

Tests for:
- `GET /config/status` returns expected shape, default provider is azure, no key values leaked
- `POST /config` with valid provider, invalid provider, mock mode toggle, Azure keys, partial updates, empty body
- `POST /shutdown` returns `{"ok": true}` with shutdown message

### 9. Modify: `service/tests/conftest.py`

Add `autouse` fixture to call `runtime_config.clear_overrides()` after each test for isolation.

### 10. Documentation updates

- **`Docs/Architecture.md`** — Add "Server Management" subsection, update security boundary notes
- **`Docs/Setup_Guide.md`** — Add "Starting the Service from Ableton" section
- **`Docs/M4L_Build_Guide.md`** — Add section with wiring instructions for server management panel (toggle, status display, API key input, provider selector)
- **`Docs/Work_Plan.md`** — Add Milestone 9 checklist

---

## Implementation Order

1. `service/runtime_config.py` (new, no dependencies)
2. `service/models.py` (add ConfigRequest, ConfigStatusResponse)
3. `service/llm_provider.py` (switch to runtime_config)
4. `service/app.py` (add endpoints + mock mode change)
5. `service/tests/conftest.py` (add cleanup fixture)
6. `service/tests/test_config.py` (new, verify all endpoints)
7. `m4l/js/groove_http.js` (add config/shutdown messages)
8. `m4l/js/response_router.js` (add outlet 5 + routing)
9. `m4l/js/server_launcher.js` (new Node.js launcher)
10. Documentation updates

Steps 1-6 are testable via pytest. Steps 7-9 require manual testing in Max. Step 10 is docs only.

---

## Security Notes

- API keys travel over `http://127.0.0.1` only (localhost loopback) — same trust boundary as existing `/generate`
- Keys stored in-memory only — never persisted to disk by the service, vanish on shutdown
- `.env` file still works as a fallback for users who prefer file-based config
- `/config` response never echoes back key values — only boolean `configured` flags
- No auth token on `/config` or `/shutdown` for MVP (localhost-only binding is the security boundary)

---

## Verification

1. **Run tests:** `cd service && .venv/Scripts/python.exe -m pytest tests/ -v` — all existing + new tests pass
2. **Manual service test:**
   - Start service: `uvicorn app:app --host 127.0.0.1 --port 8787`
   - `curl http://127.0.0.1:8787/config/status` → returns config status
   - `curl -X POST http://127.0.0.1:8787/config -H "Content-Type: application/json" -d '{"mock_mode": false, "azure_api_key": "test"}'` → returns ok + updated count
   - `curl -X POST http://127.0.0.1:8787/shutdown` → server shuts down
3. **Max for Live test:** Load device → click Start Server → status shows "running" → enter API key → generate → click Stop Server
