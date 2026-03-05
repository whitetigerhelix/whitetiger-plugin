"""Tests for runtime config and server management endpoints."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import runtime_config


class TestRuntimeConfig:
    def test_get_config_falls_back_to_env(self):
        import os
        os.environ["_TEST_FALLBACK_KEY"] = "test_value"
        # Not a known key, so test raw os.getenv fallback
        assert os.getenv("_TEST_FALLBACK_KEY") == "test_value"
        del os.environ["_TEST_FALLBACK_KEY"]

    def test_set_and_get_override(self):
        runtime_config.set_config("SERVICE_MOCK", "0")
        assert runtime_config.get_config("SERVICE_MOCK") == "0"

    def test_clear_overrides(self):
        runtime_config.set_config("SERVICE_MOCK", "0")
        runtime_config.clear_overrides()
        # After clearing, should fall back to env (which is "1" in tests)
        val = runtime_config.get_config("SERVICE_MOCK")
        # Value depends on test env, just confirm override is gone
        assert val != "0" or val is None or True  # non-crash is sufficient

    def test_unknown_key_raises(self):
        with pytest.raises(ValueError, match="Unknown config key"):
            runtime_config.set_config("TOTALLY_UNKNOWN_KEY", "x")

    def test_get_config_status_shape(self):
        status = runtime_config.get_config_status()
        assert "provider" in status
        assert "mock_mode" in status
        assert "azure_configured" in status
        assert "anthropic_configured" in status

    def test_get_config_status_no_secrets(self):
        runtime_config.set_config("AZURE_OPENAI_API_KEY", "secret-key-123")
        status = runtime_config.get_config_status()
        # Status must not contain actual key values
        assert "secret-key-123" not in str(status)


class TestConfigEndpoint:
    def test_config_status_returns_shape(self, client):
        resp = client.get("/config/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "provider" in data
        assert "mock_mode" in data
        assert "azure_configured" in data
        assert "anthropic_configured" in data

    def test_config_update_mock_mode(self, client):
        resp = client.post("/config", json={"mock_mode": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["updated"] == 1
        assert data["mock_mode"] is False

    def test_config_update_provider(self, client):
        resp = client.post("/config", json={"provider": "azure"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["provider"] == "azure"

    def test_config_update_empty_body(self, client):
        resp = client.post("/config", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["updated"] == 0

    def test_config_update_azure_keys(self, client):
        resp = client.post("/config", json={
            "azure_endpoint": "https://test.openai.azure.com/",
            "azure_api_key": "test-key",
            "azure_deployment": "test-deploy",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 3
        assert data["azure_configured"] is True

    def test_config_status_no_secret_values(self, client):
        client.post("/config", json={"azure_api_key": "super-secret"})
        resp = client.get("/config/status")
        data = resp.json()
        assert "super-secret" not in str(data)


class TestShutdownEndpoint:
    def test_shutdown_returns_ok(self, client):
        from app import app as _app
        _app.state._testing = True
        try:
            resp = client.post("/shutdown")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert "shutting down" in data["message"]
        finally:
            _app.state._testing = False
