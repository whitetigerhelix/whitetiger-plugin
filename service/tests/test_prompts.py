"""Tests for prompt construction (service/prompts.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ClipInfo, Controls, GenerateRequest
from presets import PRESETS, get_preset
from prompts import (
    build_surprise_system_prompt,
    build_surprise_user_prompt,
    build_system_prompt,
    build_user_prompt,
)


class TestSystemPrompt:
    def test_contains_json_schema(self):
        prompt = build_system_prompt()
        assert '"version"' in prompt
        assert '"notes"' in prompt
        assert '"pitch"' in prompt
        assert '"start_beats"' in prompt

    def test_contains_output_instructions(self):
        prompt = build_system_prompt()
        assert "ONLY" in prompt
        assert "JSON" in prompt

    def test_mentions_gm_drum_pitches(self):
        prompt = build_system_prompt()
        assert "kick" in prompt.lower()
        assert "snare" in prompt.lower()
        assert "36" in prompt
        assert "38" in prompt

    def test_mentions_beat_units(self):
        prompt = build_system_prompt()
        assert "quarter-note" in prompt.lower()

    def test_mentions_max_notes(self):
        prompt = build_system_prompt()
        assert "5000" in prompt


class TestSurprisePrompt:
    def test_surprise_system_prompt_contains_schema(self):
        prompt = build_surprise_system_prompt()
        assert '"prompt"' in prompt
        assert '"controls"' in prompt
        assert '"sound_suggestion"' in prompt

    def test_surprise_system_prompt_mentions_color(self):
        prompt = build_surprise_system_prompt()
        assert "color" in prompt.lower()

    def test_surprise_user_prompt_contains_preset_and_color(self):
        preset = get_preset("breaks_atmos_130")
        prompt = build_surprise_user_prompt(preset, 0.75)
        assert "breaks_atmos_130" in prompt
        assert "0.75" in prompt


class TestUserPrompt:
    def _make_request(self, preset_id: str = "breaks_atmos_130") -> GenerateRequest:
        return GenerateRequest(
            prompt="test groove please",
            preset_id=preset_id,
            clip=ClipInfo(bars=4, bpm=120, time_sig_num=4, time_sig_den=4),
            controls=Controls(density=0.8, complexity=0.6),
            seed=42,
        )

    def test_placeholders_filled(self):
        preset = get_preset("breaks_atmos_130")
        req = self._make_request()
        prompt = build_user_prompt(preset, req)

        assert "test groove please" in prompt
        assert "120" in prompt  # BPM
        assert "4" in prompt    # BARS
        assert "{USER_PROMPT}" not in prompt
        assert "{BPM}" not in prompt
        assert "{BARS}" not in prompt

    def test_clip_length_included(self):
        preset = get_preset("breaks_atmos_130")
        req = self._make_request()
        prompt = build_user_prompt(preset, req)
        # 4 bars * 4/4 = 16 beats
        assert "16.0" in prompt or "16" in prompt

    def test_seed_included(self):
        preset = get_preset("breaks_atmos_130")
        req = self._make_request()
        prompt = build_user_prompt(preset, req)
        assert "42" in prompt

    def test_all_presets_produce_valid_prompts(self):
        """Every registered preset should produce a prompt without errors."""
        for preset_id, preset in PRESETS.items():
            req = self._make_request(preset_id)
            prompt = build_user_prompt(preset, req)
            assert len(prompt) > 50, f"Preset {preset_id} produced a very short prompt"
            assert "{" not in prompt or "}" not in prompt or "quarter" in prompt

    def test_density_and_complexity_in_prompt(self):
        preset = get_preset("breaks_atmos_130")
        req = self._make_request()
        prompt = build_user_prompt(preset, req)
        assert "0.8" in prompt   # density
        assert "0.6" in prompt   # complexity

    def test_effective_seed_overrides_request_seed(self):
        preset = get_preset("breaks_atmos_130")
        req = self._make_request()  # seed=42
        prompt = build_user_prompt(preset, req, effective_seed=99)
        assert "Seed: 99" in prompt
        assert "Seed: 42" not in prompt

    def test_effective_seed_none_uses_request_seed(self):
        preset = get_preset("breaks_atmos_130")
        req = self._make_request()  # seed=42
        prompt = build_user_prompt(preset, req)
        assert "Seed: 42" in prompt

    def test_allowed_pitches_included_when_present(self):
        preset = get_preset("breaks_atmos_130")
        req = self._make_request()
        req = req.model_copy(update={"allowed_pitches": [36, 38, 42, 46, 49]})

        prompt = build_user_prompt(preset, req)
        assert "Allowed MIDI pitches: [36, 38, 42, 46, 49]" in prompt

    def test_instrument_hints_included_when_present(self):
        preset = get_preset("breaks_atmos_130")
        req = self._make_request()
        req = req.model_copy(update={
            "instrument_hints": ["syncopated shaker layer", "ghost-note snare texture"],
        })

        prompt = build_user_prompt(preset, req)
        assert "Instrument/layer hints:" in prompt
        assert "syncopated shaker layer" in prompt
        assert "ghost-note snare texture" in prompt
