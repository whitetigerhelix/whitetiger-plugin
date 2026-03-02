"""Tests for disk cache (service/cache.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache import cache_get, cache_key, cache_put
from models import (
    ClipInfo,
    Controls,
    GenerateRequest,
    GenerateResponse,
    MidiPlan,
    NoteEvent,
)


def _make_request(**overrides) -> GenerateRequest:
    data = {
        "prompt": "atmospheric breaks",
        "preset_id": "breaks_atmos_130",
        "clip": ClipInfo(bars=4, bpm=120),
        "controls": Controls(density=0.75, complexity=0.65),
        "seed": 42,
    }
    data.update(overrides)
    return GenerateRequest(**data)


def _make_response() -> GenerateResponse:
    return GenerateResponse(
        ok=True,
        summary="2 notes, 4 bars",
        plan=MidiPlan(
            version=1,
            mode="drums",
            bars=4,
            time_sig_num=4,
            time_sig_den=4,
            notes=[
                NoteEvent(pitch=36, start_beats=0.0, dur_beats=0.5, vel=100, mute=0),
                NoteEvent(pitch=42, start_beats=0.5, dur_beats=0.25, vel=80, mute=0),
            ],
        ),
    )


class TestCacheKey:
    def test_same_request_same_key(self):
        r1 = _make_request()
        r2 = _make_request()
        assert cache_key(r1) == cache_key(r2)

    def test_different_prompt_different_key(self):
        r1 = _make_request(prompt="breaks")
        r2 = _make_request(prompt="chill")
        assert cache_key(r1) != cache_key(r2)

    def test_different_seed_different_key(self):
        r1 = _make_request(seed=1)
        r2 = _make_request(seed=2)
        assert cache_key(r1) != cache_key(r2)

    def test_different_preset_different_key(self):
        r1 = _make_request(preset_id="breaks_atmos_130")
        r2 = _make_request(preset_id="four_on_floor")
        assert cache_key(r1) != cache_key(r2)

    def test_key_is_hex_hash(self):
        key = cache_key(_make_request())
        assert len(key) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in key)


class TestCacheGetPut:
    def test_miss_returns_none(self, tmp_path: Path):
        result = cache_get("nonexistent_key", cache_dir=tmp_path)
        assert result is None

    def test_roundtrip(self, tmp_path: Path):
        key = "test_roundtrip_key"
        response = _make_response()
        cache_put(key, response, cache_dir=tmp_path)

        loaded = cache_get(key, cache_dir=tmp_path)
        assert loaded is not None
        assert loaded.ok is True
        assert loaded.summary == "2 notes, 4 bars"
        assert loaded.plan is not None
        assert len(loaded.plan.notes) == 2
        assert loaded.plan.notes[0].pitch == 36

    def test_creates_directory(self, tmp_path: Path):
        cache_dir = tmp_path / "sub" / "cache"
        assert not cache_dir.exists()

        cache_put("key123", _make_response(), cache_dir=cache_dir)
        assert cache_dir.exists()

    def test_corrupted_file_returns_none(self, tmp_path: Path):
        key = "corrupted"
        path = tmp_path / f"{key}.json"
        path.write_text("not valid json!", encoding="utf-8")

        result = cache_get(key, cache_dir=tmp_path)
        assert result is None

    def test_full_flow_with_real_key(self, tmp_path: Path):
        """End-to-end: compute key from request, cache put, then get."""
        req = _make_request()
        key = cache_key(req)
        response = _make_response()

        cache_put(key, response, cache_dir=tmp_path)
        loaded = cache_get(key, cache_dir=tmp_path)

        assert loaded is not None
        assert loaded.plan.notes[0].pitch == 36
