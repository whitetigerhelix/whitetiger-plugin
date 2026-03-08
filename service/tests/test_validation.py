"""Tests for LLM response parsing and validation (service/validation.py)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ClipInfo
from validation import parse_llm_response


def _clip(bars: int = 4, ts_num: int = 4, ts_den: int = 4) -> ClipInfo:
    return ClipInfo(bars=bars, time_sig_num=ts_num, time_sig_den=ts_den, bpm=120)


def _valid_json(notes: list[dict] | None = None, bars: int = 4) -> str:
    if notes is None:
        notes = [
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.5, "vel": 100, "mute": 0},
            {"pitch": 42, "start_beats": 0.5, "dur_beats": 0.25, "vel": 80, "mute": 0},
        ]
    return json.dumps({
        "version": 1,
        "mode": "drums",
        "bars": bars,
        "time_sig_num": 4,
        "time_sig_den": 4,
        "notes": notes,
    })


class TestParseValidJSON:
    def test_basic_parse(self):
        plan = parse_llm_response(_valid_json(), _clip())
        assert len(plan.notes) == 2
        assert plan.notes[0].pitch == 36
        assert plan.notes[1].pitch == 42

    def test_preserves_metadata(self):
        plan = parse_llm_response(_valid_json(), _clip())
        assert plan.version == 1
        assert plan.mode == "drums"
        assert plan.bars == 4
        assert plan.time_sig_num == 4
        assert plan.time_sig_den == 4

    def test_clip_metadata_overrides_llm_metadata(self):
        text = json.dumps({
            "version": 1,
            "mode": "drums",
            "bars": 8,
            "time_sig_num": 4,
            "time_sig_den": 4,
            "notes": [
                {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.5, "vel": 100, "mute": 0}
            ],
        })
        clip = ClipInfo(bars=16, time_sig_num=3, time_sig_den=4, bpm=120)
        plan = parse_llm_response(text, clip)
        assert plan.bars == 16
        assert plan.time_sig_num == 3
        assert plan.time_sig_den == 4


class TestCodeFenceExtraction:
    def test_json_code_fence(self):
        text = '```json\n' + _valid_json() + '\n```'
        plan = parse_llm_response(text, _clip())
        assert len(plan.notes) == 2

    def test_plain_code_fence(self):
        text = '```\n' + _valid_json() + '\n```'
        plan = parse_llm_response(text, _clip())
        assert len(plan.notes) == 2

    def test_preamble_text_before_json(self):
        text = "Here is the groove:\n\n" + _valid_json()
        plan = parse_llm_response(text, _clip())
        assert len(plan.notes) == 2

    def test_preamble_with_code_fence(self):
        text = "Sure! Here's the pattern:\n```json\n" + _valid_json() + "\n```\nEnjoy!"
        plan = parse_llm_response(text, _clip())
        assert len(plan.notes) == 2


class TestNoteClamping:
    def test_note_past_clip_end_removed(self):
        """Notes starting at or beyond clip length should be removed."""
        notes = [
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.5, "vel": 100, "mute": 0},
            {"pitch": 36, "start_beats": 16.0, "dur_beats": 0.5, "vel": 100, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert len(plan.notes) == 1

    def test_note_extending_past_clip_clamped(self):
        """Notes extending beyond clip length should have duration clamped."""
        notes = [
            {"pitch": 36, "start_beats": 15.5, "dur_beats": 1.0, "vel": 100, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert len(plan.notes) == 1
        assert plan.notes[0].dur_beats == pytest.approx(0.5)

    def test_velocity_clamped_to_range(self):
        """Velocity 0 should be clamped up to 1."""
        notes = [
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.5, "vel": 0, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert len(plan.notes) == 1
        assert plan.notes[0].vel == 1

    def test_velocity_above_127_clamped(self):
        notes = [
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.5, "vel": 200, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert len(plan.notes) == 1
        assert plan.notes[0].vel == 127

    def test_negative_pitch_removed(self):
        notes = [
            {"pitch": -1, "start_beats": 0.0, "dur_beats": 0.5, "vel": 100, "mute": 0},
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.5, "vel": 100, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert len(plan.notes) == 1
        assert plan.notes[0].pitch == 36

    def test_pitch_above_127_removed(self):
        notes = [
            {"pitch": 200, "start_beats": 0.0, "dur_beats": 0.5, "vel": 100, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert len(plan.notes) == 0


class TestMaxNotes:
    def test_truncation_at_5000(self):
        notes = [
            {"pitch": 36, "start_beats": i * 0.001, "dur_beats": 0.001, "vel": 100, "mute": 0}
            for i in range(6000)
        ]
        # Use a very long clip so notes aren't clipped by bounds
        clip = ClipInfo(bars=64, time_sig_num=4, time_sig_den=4, bpm=120)
        plan = parse_llm_response(_valid_json(notes, bars=64), clip)
        assert len(plan.notes) == 5000


class TestInvalidInput:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_llm_response("", _clip())

    def test_plain_text_raises(self):
        with pytest.raises(ValueError):
            parse_llm_response("I don't know how to do that", _clip())

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_llm_response("{bad json!", _clip())

    def test_array_instead_of_object_raises(self):
        with pytest.raises(ValueError, match="Expected JSON object"):
            parse_llm_response("[1, 2, 3]", _clip())

    def test_notes_not_a_list_raises(self):
        text = json.dumps({"notes": "not a list"})
        with pytest.raises(ValueError, match="Expected 'notes' to be a list"):
            parse_llm_response(text, _clip())


class TestEdgeCases:
    def test_zero_duration_note_removed(self):
        notes = [
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.0, "vel": 100, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert len(plan.notes) == 0

    def test_negative_start_removed(self):
        notes = [
            {"pitch": 36, "start_beats": -1.0, "dur_beats": 0.5, "vel": 100, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert len(plan.notes) == 0

    def test_invalid_mute_defaults_to_zero(self):
        notes = [
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.5, "vel": 100, "mute": 5},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        assert plan.notes[0].mute == 0

    def test_missing_fields_in_note_skipped(self):
        notes = [
            {"pitch": 36},  # missing start_beats, dur_beats, vel
            {"pitch": 42, "start_beats": 0.5, "dur_beats": 0.25, "vel": 80, "mute": 0},
        ]
        plan = parse_llm_response(_valid_json(notes), _clip())
        # First note should be skipped (start_beats=-1, dur_beats=0)
        assert len(plan.notes) == 1
        assert plan.notes[0].pitch == 42

    def test_3_4_time_signature(self):
        """Clip in 3/4 time should have correct beat length."""
        clip = ClipInfo(bars=4, time_sig_num=3, time_sig_den=4, bpm=120)
        notes = [
            {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.5, "vel": 100, "mute": 0},
            {"pitch": 36, "start_beats": 11.5, "dur_beats": 1.0, "vel": 100, "mute": 0},
        ]
        # 4 bars * 3 * (4/4) = 12 beats
        plan = parse_llm_response(_valid_json(notes, bars=4), clip)
        assert len(plan.notes) == 2
        assert plan.notes[1].dur_beats == pytest.approx(0.5)
