"""Tests for Pydantic models — validation, boundaries, rejection of invalid data."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    ClipInfo,
    Controls,
    GenerateRequest,
    GenerateResponse,
    MidiPlan,
    NoteEvent,
)


class TestNoteEvent:
    def test_valid_note(self):
        note = NoteEvent(pitch=36, start_beats=0.0, dur_beats=0.25, vel=110)
        assert note.pitch == 36
        assert note.mute == 0

    def test_pitch_boundaries(self):
        NoteEvent(pitch=0, start_beats=0, dur_beats=0.25, vel=1)
        NoteEvent(pitch=127, start_beats=0, dur_beats=0.25, vel=1)

    def test_pitch_out_of_range(self):
        with pytest.raises(Exception):
            NoteEvent(pitch=128, start_beats=0, dur_beats=0.25, vel=1)
        with pytest.raises(Exception):
            NoteEvent(pitch=-1, start_beats=0, dur_beats=0.25, vel=1)

    def test_vel_zero_rejected(self):
        with pytest.raises(Exception):
            NoteEvent(pitch=36, start_beats=0, dur_beats=0.25, vel=0)

    def test_vel_boundaries(self):
        NoteEvent(pitch=36, start_beats=0, dur_beats=0.25, vel=1)
        NoteEvent(pitch=36, start_beats=0, dur_beats=0.25, vel=127)

    def test_vel_out_of_range(self):
        with pytest.raises(Exception):
            NoteEvent(pitch=36, start_beats=0, dur_beats=0.25, vel=128)

    def test_dur_must_be_positive(self):
        with pytest.raises(Exception):
            NoteEvent(pitch=36, start_beats=0, dur_beats=0, vel=100)
        with pytest.raises(Exception):
            NoteEvent(pitch=36, start_beats=0, dur_beats=-0.5, vel=100)

    def test_negative_start_rejected(self):
        with pytest.raises(Exception):
            NoteEvent(pitch=36, start_beats=-1.0, dur_beats=0.25, vel=100)

    def test_mute_values(self):
        NoteEvent(pitch=36, start_beats=0, dur_beats=0.25, vel=100, mute=0)
        NoteEvent(pitch=36, start_beats=0, dur_beats=0.25, vel=100, mute=1)
        with pytest.raises(Exception):
            NoteEvent(pitch=36, start_beats=0, dur_beats=0.25, vel=100, mute=2)


class TestClipInfo:
    def test_defaults(self):
        clip = ClipInfo()
        assert clip.bars == 8
        assert clip.time_sig_num == 4
        assert clip.time_sig_den == 4
        assert clip.bpm == 130

    def test_bars_range(self):
        ClipInfo(bars=1)
        ClipInfo(bars=64)
        with pytest.raises(Exception):
            ClipInfo(bars=0)
        with pytest.raises(Exception):
            ClipInfo(bars=65)

    def test_bpm_range(self):
        ClipInfo(bpm=40)
        ClipInfo(bpm=240)
        with pytest.raises(Exception):
            ClipInfo(bpm=39)
        with pytest.raises(Exception):
            ClipInfo(bpm=241)


class TestControls:
    def test_defaults(self):
        controls = Controls()
        assert controls.density == 0.75
        assert controls.swing == 0.35

    def test_density_range(self):
        Controls(density=0)
        Controls(density=1)
        with pytest.raises(Exception):
            Controls(density=-0.1)
        with pytest.raises(Exception):
            Controls(density=1.1)

    def test_humanize_ms_range(self):
        Controls(humanize_ms=0)
        Controls(humanize_ms=25)
        with pytest.raises(Exception):
            Controls(humanize_ms=26)

    def test_velocity_jitter_range(self):
        Controls(velocity_jitter=0)
        Controls(velocity_jitter=15)
        with pytest.raises(Exception):
            Controls(velocity_jitter=16)


class TestGenerateRequest:
    def test_minimal_request(self):
        req = GenerateRequest(prompt="test", preset_id="breaks_atmos_130")
        assert req.mode == "drums"
        assert req.drum_map == "gm"
        assert req.seed == 12345

    def test_full_request(self):
        req = GenerateRequest(
            prompt="ghost snares, sparse kicks",
            preset_id="chill_psychill",
            clip=ClipInfo(bars=4, bpm=90),
            controls=Controls(density=0.3, swing=0.1),
            seed=99,
        )
        assert req.clip.bars == 4
        assert req.controls.density == 0.3


class TestMidiPlan:
    def test_empty_plan(self):
        plan = MidiPlan(bars=8, time_sig_num=4, time_sig_den=4)
        assert plan.notes == []
        assert plan.version == 1

    def test_plan_with_notes(self):
        plan = MidiPlan(
            bars=4,
            time_sig_num=4,
            time_sig_den=4,
            notes=[
                NoteEvent(pitch=36, start_beats=0, dur_beats=0.25, vel=110),
                NoteEvent(pitch=38, start_beats=1, dur_beats=0.25, vel=100),
            ],
        )
        assert len(plan.notes) == 2


class TestGenerateResponse:
    def test_success_response(self):
        resp = GenerateResponse(
            ok=True,
            summary="Test groove",
            plan=MidiPlan(bars=4, time_sig_num=4, time_sig_den=4),
        )
        assert resp.ok
        assert resp.error is None

    def test_error_response(self):
        resp = GenerateResponse(ok=False, error="Something went wrong")
        assert not resp.ok
        assert resp.plan is None
        assert resp.error == "Something went wrong"
