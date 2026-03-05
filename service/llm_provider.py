"""LLM provider abstraction for AI Groove Writer.

Defines a swappable interface for LLM backends. The active provider
is selected via the LLM_PROVIDER environment variable.

Canonical reference: Docs/Architecture.md (provider abstraction).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import runtime_config


@dataclass
class LLMResult:
    """Result from an LLM call."""
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    provider: str


@dataclass(frozen=True)
class ProviderCapability:
    """Describes provider readiness and configuration requirements."""

    name: str
    implemented: bool
    required_env: tuple[str, ...]
    notes: str


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        timeout: float | None = None,
        model_override: str | None = None,
    ) -> LLMResult:
        """Send prompts to the LLM and return the result.

        Args:
            model_override: If provided, use this model/deployment instead
                of the server default.
        """
        ...


# --- Cost estimation (USD per 1M tokens) ---
# Update these as pricing changes
COST_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for a request based on known model pricing."""
    pricing = COST_PER_1M_TOKENS.get(model)
    if pricing is None:
        return 0.0
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


# --- Azure OpenAI Provider ---

class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider using the openai SDK."""

    def __init__(self) -> None:
        endpoint = runtime_config.get_config("AZURE_OPENAI_ENDPOINT")
        api_key = runtime_config.get_config("AZURE_OPENAI_API_KEY")
        deployment = runtime_config.get_config("AZURE_OPENAI_DEPLOYMENT")
        api_version = runtime_config.get_config("AZURE_OPENAI_API_VERSION") or "2024-02-01"

        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
        if not deployment:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT environment variable is required")

        from openai import AzureOpenAI

        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self._deployment = deployment

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        timeout: float | None = None,
        model_override: str | None = None,
    ) -> LLMResult:
        deployment = model_override or self._deployment
        kwargs: dict = dict(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4096,
        )
        if timeout is not None:
            kwargs["timeout"] = timeout

        response = self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        usage = response.usage

        return LLMResult(
            text=choice.message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            model=deployment,
            provider="azure",
        )


# --- Anthropic Provider (stub) ---

class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider — stub for future implementation."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "Anthropic provider is not yet implemented. "
            "Set LLM_PROVIDER=azure to use Azure OpenAI, "
            "or set SERVICE_MOCK=1 for mock mode. "
            "If you want Anthropic later, you will need Anthropic API billing/key "
            "(Claude chat subscription is separate from API access)."
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        timeout: float | None = None,
        model_override: str | None = None,
    ) -> LLMResult:
        raise NotImplementedError


# --- Provider factory ---

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "azure": AzureOpenAIProvider,
    "anthropic": AnthropicProvider,
}


_PROVIDER_CAPABILITIES: dict[str, ProviderCapability] = {
    "azure": ProviderCapability(
        name="azure",
        implemented=True,
        required_env=(
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT",
        ),
        notes="Production-ready provider path.",
    ),
    "anthropic": ProviderCapability(
        name="anthropic",
        implemented=False,
        required_env=("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
        notes="Planned provider path; stub only in current build.",
    ),
}


def list_provider_capabilities() -> dict[str, ProviderCapability]:
    """Return capability metadata for all known providers."""
    return dict(_PROVIDER_CAPABILITIES)


def get_provider(provider_name: str | None = None) -> LLMProvider:
    """Create and return the configured LLM provider.

    Reads LLM_PROVIDER env var if provider_name is not specified.
    """
    raw_name = provider_name if provider_name is not None else (runtime_config.get_config("LLM_PROVIDER") or "azure")
    name = raw_name.strip().lower()
    provider_cls = _PROVIDERS.get(name)

    if provider_cls is None:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(
            f"Unknown LLM provider: {name!r}. Available: {available}"
        )

    return provider_cls()
