"""Tests for prompt construction (service/prompts.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ClipInfo, Controls, GenerateRequest
from presets import PRESETS, get_preset
from prompts import build_system_prompt, build_user_prompt


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
