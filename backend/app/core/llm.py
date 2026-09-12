"""Role-based chat model factory.

Models are swapped via environment variables or the admin runtime config
using LangChain's unified ``init_chat_model``. Values must use the
``provider:model_name`` format::

    LLM_FAST_MODEL=google_genai:gemini-2.5-flash
    LLM_HEAVY_MODEL=openrouter:anthropic/claude-3.5-sonnet

Supported providers (BUILD_GUIDE Phase 3 / SPEC.md §5): Google GenAI
(``google_genai``), Anthropic (``anthropic``), OpenAI (``openai``),
OpenRouter (``openrouter``). The corresponding provider packages must be
installed (see requirements.txt).

OpenRouter is routed through LangChain's ``openai`` provider with a custom
base URL, since it is fully OpenAI-compatible.
"""

from __future__ import annotations

import os
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.core import config_service

#: Default model string, used only when an env var + config are both unset.
DEFAULT_MODEL = "google_genai:gemini-2.5-flash"

#: Maps the role argument to the config key that configures it.
_ROLE_CONFIG_KEYS = {
    "fast": "LLM_FAST_MODEL",
    "heavy": "LLM_HEAVY_MODEL",
}

#: Providers LangChain can route natively via ``model_provider=``.
_KNOWN_PROVIDERS = {
    "google_genai",
    "openai",
    "anthropic",
    "azure_openai",
    "bedrock",
    "ollama",
    "groq",
    "together",
    "mistralai",
    "fireworks",
    "openrouter",
}

#: OpenRouter is OpenAI-compatible, so we route it through the openai provider.
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class ModelConfigError(RuntimeError):
    """Raised when the environment model configuration is unusable."""


async def get_chat_model(role: str = "fast", **kwargs: Any) -> BaseChatModel:
    """Return a chat model for the given role.

    Resolution order for the model spec:
      1. Admin runtime config (database override)
      2. Environment variable (``LLM_FAST_MODEL`` / ``LLM_HEAVY_MODEL``)
      3. ``DEFAULT_MODEL``

    Args:
        role: ``"fast"`` (query planning / light steps) or ``"heavy"``
            (final structured synthesis).
        **kwargs: Extra parameters forwarded to the underlying model
            (e.g. ``temperature``).

    Raises:
        ModelConfigError: when the role is unknown or the provider
            packages / API keys are not available.
    """
    config_key = _ROLE_CONFIG_KEYS.get(role)
    if config_key is None:
        raise ModelConfigError(
            f"unknown model role: {role!r}; expected one of "
            f"{', '.join(_ROLE_CONFIG_KEYS)!r}"
        )

    spec = (await config_service.get_config(config_key, DEFAULT_MODEL)).strip()
    model, provider = _split_model_spec(spec)
    kwargs.setdefault("temperature", 0.0)
    await _apply_provider_overrides(provider, kwargs)
    effective_provider = _effective_model_provider(provider)

    try:
        return init_chat_model(model, model_provider=effective_provider, **kwargs)
    except Exception as exc:  # noqa: BLE001 - surface the real cause
        raise ModelConfigError(
            f"could not initialise role {role!r} from {config_key}={spec!r}. "
            f"Ensure the provider package is installed and the API key is "
            f"configured. ({exc})"
        ) from exc


def _split_model_spec(spec: str) -> tuple[str, str | None]:
    """Split ``provider:model_name`` while leaving bare names untouched."""
    if ":" in spec:
        provider, _, model = spec.partition(":")
        if provider.strip() in _KNOWN_PROVIDERS:
            return model.strip(), provider.strip()
    return spec, None


async def _apply_provider_overrides(
    provider: str | None, kwargs: dict[str, Any],
) -> None:
    """Inject provider-specific settings (base URL, API key) for OpenRouter."""
    if provider == "openrouter":
        kwargs.setdefault("base_url", _OPENROUTER_BASE_URL)
        key = await config_service.get_config("OPENROUTER_API_KEY")
        if not key:
            key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if key:
            kwargs.setdefault("api_key", key)
    else:
        _inject_api_key(provider, kwargs)


def _effective_model_provider(provider: str | None) -> str | None:
    """Return the installed LangChain provider used for a model spec.

    OpenRouter exposes an OpenAI-compatible API and this project installs
    ``langchain-openai``, so OpenRouter model IDs must be instantiated via
    that provider while retaining their complete IDs (including ``:free``).
    """
    return "openai" if provider == "openrouter" else provider


def _inject_api_key(provider: str | None, kwargs: dict[str, Any]) -> None:
    """Pass provider-specific API keys when present in the environment."""
    if provider == "google_genai":
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if key:
            kwargs.setdefault("google_api_key", key)
    elif provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        if key:
            kwargs.setdefault("anthropic_api_key", key)
    elif provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key:
            kwargs.setdefault("api_key", key)
