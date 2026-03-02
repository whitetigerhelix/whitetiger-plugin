"""Tests for LLM provider abstraction (service/llm_provider.py)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_provider import (
    AnthropicProvider,
    AzureOpenAIProvider,
    LLMProvider,
    LLMResult,
    estimate_cost,
    get_provider,
)


class TestLLMResult:
    def test_fields(self):
        result = LLMResult(
            text="hello",
            prompt_tokens=10,
            completion_tokens=20,
            model="gpt-4o",
            provider="azure",
        )
        assert result.text == "hello"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.model == "gpt-4o"
        assert result.provider == "azure"


class TestEstimateCost:
    def test_gpt4o_pricing(self):
        # 1000 input + 500 output tokens
        cost = estimate_cost("gpt-4o", 1000, 500)
        expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert cost == pytest.approx(expected)

    def test_gpt4o_mini_pricing(self):
        cost = estimate_cost("gpt-4o-mini", 1000, 500)
        expected = (1000 / 1_000_000) * 0.15 + (500 / 1_000_000) * 0.60
        assert cost == pytest.approx(expected)

    def test_unknown_model_returns_zero(self):
        cost = estimate_cost("unknown-model-xyz", 1000, 500)
        assert cost == 0.0

    def test_zero_tokens(self):
        cost = estimate_cost("gpt-4o", 0, 0)
        assert cost == 0.0

    def test_large_token_count(self):
        cost = estimate_cost("gpt-4o", 1_000_000, 1_000_000)
        expected = 2.50 + 10.00
        assert cost == pytest.approx(expected)


class TestProviderFactory:
    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_provider("nonexistent_provider")

    def test_unknown_provider_shows_available(self):
        with pytest.raises(ValueError, match="azure"):
            get_provider("nonexistent_provider")

    def test_azure_missing_endpoint_raises(self):
        env = {
            "AZURE_OPENAI_ENDPOINT": "",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_DEPLOYMENT": "test-deploy",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
                get_provider("azure")

    def test_azure_missing_api_key_raises(self):
        env = {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "",
            "AZURE_OPENAI_DEPLOYMENT": "test-deploy",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY"):
                get_provider("azure")

    def test_azure_missing_deployment_raises(self):
        env = {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_DEPLOYMENT": "",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError, match="AZURE_OPENAI_DEPLOYMENT"):
                get_provider("azure")


class TestAnthropicStub:
    def test_init_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            AnthropicProvider()

    def test_error_message_suggests_alternatives(self):
        with pytest.raises(NotImplementedError, match="LLM_PROVIDER=azure"):
            AnthropicProvider()

    def test_error_message_suggests_mock(self):
        with pytest.raises(NotImplementedError, match="SERVICE_MOCK=1"):
            AnthropicProvider()


class TestLLMProviderABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_subclass_must_implement_generate(self):
        class IncompleteProvider(LLMProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()
