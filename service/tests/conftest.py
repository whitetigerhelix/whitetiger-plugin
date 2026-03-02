"""Shared test fixtures for AI Groove Writer service tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure service package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app  # noqa: E402


@pytest.fixture
def client():
    """Synchronous test client for FastAPI."""
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def valid_request_data() -> dict:
    """A valid GenerateRequest payload."""
    return {
        "prompt": "atmospheric breaks with ghost snares",
        "preset_id": "breaks_atmos_130",
        "mode": "drums",
        "clip": {
            "bars": 8,
            "time_sig_num": 4,
            "time_sig_den": 4,
            "bpm": 130,
        },
        "controls": {
            "density": 0.75,
            "complexity": 0.65,
            "swing": 0.35,
            "humanize_ms": 8,
            "velocity_jitter": 6,
        },
        "seed": 42,
        "drum_map": "gm",
    }
