"""Thread-safe in-memory config store with env var fallback.

Allows runtime overrides of provider/config settings without restarting
the service or editing .env files.

Canonical reference: Docs/Plan_Server_Management.md
"""

from __future__ import annotations

import os
import threading

_lock = threading.Lock()
_overrides: dict[str, str] = {}

_KNOWN_KEYS = frozenset({
    "LLM_PROVIDER",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "SERVICE_MOCK",
})


def get_config(key: str) -> str | None:
    """Get a config value: runtime override first, then env var fallback."""
    with _lock:
        val = _overrides.get(key)
    if val is not None:
        return val
    return os.getenv(key)


def set_config(key: str, value: str) -> None:
    """Set a runtime config override. Key must be in KNOWN_KEYS."""
    if key not in _KNOWN_KEYS:
        raise ValueError(f"Unknown config key: {key!r}")
    with _lock:
        _overrides[key] = value


def clear_overrides() -> None:
    """Remove all runtime overrides (for test cleanup)."""
    with _lock:
        _overrides.clear()


def get_config_status() -> dict:
    """Return current config status without exposing secret values."""
    provider = get_config("LLM_PROVIDER") or "azure"
    mock_raw = get_config("SERVICE_MOCK")
    mock_mode = mock_raw == "1" if mock_raw is not None else True

    azure_configured = bool(
        get_config("AZURE_OPENAI_ENDPOINT")
        and get_config("AZURE_OPENAI_API_KEY")
        and get_config("AZURE_OPENAI_DEPLOYMENT")
    )
    anthropic_configured = bool(get_config("ANTHROPIC_API_KEY"))

    return {
        "provider": provider,
        "mock_mode": mock_mode,
        "azure_configured": azure_configured,
        "anthropic_configured": anthropic_configured,
    }
