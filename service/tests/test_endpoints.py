"""Tests for FastAPI endpoints — health, generate, presets, usage."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure mock mode is on for tests
os.environ["SERVICE_MOCK"] = "1"


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


class TestPresets:
    def test_presets_returns_list(self, client):
        resp = client.get("/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 5

    def test_presets_have_required_fields(self, client):
        resp = client.get("/presets")
        for preset in resp.json():
            assert "id" in preset
            assert "name" in preset
            assert "defaults" in preset


class TestGenerate:
    def test_generate_valid_request(self, client, valid_request_data):
        resp = client.post("/generate", json=valid_request_data)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["plan"] is not None
        assert len(data["plan"]["notes"]) > 0
        assert data["summary"] != ""

    def test_generate_returns_correct_bars(self, client, valid_request_data):
        valid_request_data["clip"]["bars"] = 4
        resp = client.post("/generate", json=valid_request_data)
        data = resp.json()
        assert data["plan"]["bars"] == 4

    def test_generate_unknown_preset(self, client, valid_request_data):
        valid_request_data["preset_id"] = "nonexistent_preset"
        resp = client.post("/generate", json=valid_request_data)
        data = resp.json()
        assert data["ok"] is False
        assert "Unknown preset_id" in data["error"]

    def test_generate_invalid_request_returns_422(self, client):
        resp = client.post("/generate", json={"bad": "data"})
        assert resp.status_code == 422

    def test_generate_notes_have_valid_pitches(self, client, valid_request_data):
        resp = client.post("/generate", json=valid_request_data)
        notes = resp.json()["plan"]["notes"]
        for note in notes:
            assert 0 <= note["pitch"] <= 127
            assert 1 <= note["vel"] <= 127
            assert note["start_beats"] >= 0
            assert note["dur_beats"] > 0

    def test_generate_all_presets(self, client, valid_request_data):
        preset_ids = [
            "breaks_atmos_130",
            "breaks_driving",
            "chill_psychill",
            "four_on_floor",
            "halftime_broken",
        ]
        for preset_id in preset_ids:
            valid_request_data["preset_id"] = preset_id
            resp = client.post("/generate", json=valid_request_data)
            data = resp.json()
            assert data["ok"] is True, f"Failed for preset {preset_id}"
            assert len(data["plan"]["notes"]) > 0, f"No notes for preset {preset_id}"

    def test_generate_minimal_request(self, client):
        resp = client.post("/generate", json={
            "prompt": "test",
            "preset_id": "breaks_atmos_130",
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_generate_with_variation(self, client, valid_request_data):
        valid_request_data["variation"] = 1
        resp = client.post("/generate", json=valid_request_data)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["plan"] is not None

    def test_generate_variation_zero_default(self, client, valid_request_data):
        """Request without variation field should default to 0 and succeed."""
        assert "variation" not in valid_request_data
        resp = client.post("/generate", json=valid_request_data)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_generate_with_model_override(self, client, valid_request_data):
        """Request with model field should succeed in mock mode."""
        valid_request_data["model"] = "gpt-4o-mini"
        resp = client.post("/generate", json=valid_request_data)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["plan"] is not None

    def test_generate_model_none_default(self, client, valid_request_data):
        """Request without model field should default to None and succeed."""
        assert "model" not in valid_request_data
        resp = client.post("/generate", json=valid_request_data)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


class TestUsage:
    def test_usage_returns_stats(self, client):
        resp = client.get("/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data
        assert "total_tokens" in data
        assert "total_estimated_cost_usd" in data
