"""Role-based chat model factory.

Models are swapped via environment variables using LangChain's unified
``init_chat_model``. Values must use the ``provider:model_name`` format::

    LLM_FAST_MODEL=google_genai:gemini-2.5-flash
    LLM_HEAVY_MODEL=google_genai:gemini-2.5-flash

Supported providers (BUILD_GUIDE Phase 3 / SPEC.md §5): Google GenAI
(``google_genai``), Anthropic (``anthropic``), OpenAI (``openai``). The
corresponding provider packages must be installed (see requirements.txt).
"""

from __future__ import annotations

import os
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

#: Default model string, used only when an env var is unset.
DEFAULT_MODEL = "google_genai:gemini-2.5-flash"

#: Maps the role argument to the environment variable that configures it.
_ROLE_ENV_VARS = {
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
}


class ModelConfigError(RuntimeError):
    """Raised when the environment model configuration is unusable."""


def get_chat_model(role: str = "fast", **kwargs: Any) -> BaseChatModel:
    """Return a chat model for the given role.

    Args:
        role: ``"fast"`` (query planning / light steps) or ``"heavy"``
            (final structured synthesis). Reads ``LLM_FAST_MODEL`` /
            ``LLM_HEAVY_MODEL`` respectively.
        **kwargs: Extra parameters forwarded to the underlying model
            (e.g. ``temperature``).

    Raises:
        ModelConfigError: when the role is unknown or the provider
            packages / API keys are not available.
    """
    env_name = _ROLE_ENV_VARS.get(role)
    if env_name is None:
        raise ModelConfigError(
            f"unknown model role: {role!r}; expected one of "
            f"{', '.join(_ROLE_ENV_VARS)!r}"
        )

    spec = os.getenv(env_name, DEFAULT_MODEL).strip()
    model, provider = _split_model_spec(spec)
    kwargs.setdefault("temperature", 0.0)
    _inject_api_key(provider, kwargs)

    try:
        return init_chat_model(model, model_provider=provider, **kwargs)
    except Exception as exc:  # noqa: BLE001 - surface the real cause
        raise ModelConfigError(
            f"could not initialise role {role!r} from {env_name}={spec!r}. "
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