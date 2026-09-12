"""Unit tests for model-spec parsing and OpenRouter routing."""

import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

langchain = types.ModuleType("langchain")
chat_models = types.ModuleType("langchain.chat_models")
chat_models.init_chat_model = lambda *args, **kwargs: None
langchain_core = types.ModuleType("langchain_core")
language_models = types.ModuleType("langchain_core.language_models")
language_models.BaseChatModel = object
sys.modules.setdefault("langchain", langchain)
sys.modules.setdefault("langchain.chat_models", chat_models)
sys.modules.setdefault("langchain_core", langchain_core)
sys.modules.setdefault("langchain_core.language_models", language_models)

from app.core.llm import (
    _OPENROUTER_BASE_URL,
    _apply_provider_overrides,
    _effective_model_provider,
    _split_model_spec,
)


class ModelConfigTests(unittest.TestCase):
    def test_openrouter_free_model_keeps_complete_identifier(self):
        model, provider = _split_model_spec(
            "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"
        )
        self.assertEqual(model, "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(provider, "openrouter")
        self.assertEqual(_effective_model_provider(provider), "openai")

    def test_openrouter_overrides_use_openai_compatible_endpoint(self):
        kwargs = {}
        with patch(
            "app.core.llm.config_service.get_config",
            AsyncMock(return_value="test-key"),
        ):
            asyncio.run(_apply_provider_overrides("openrouter", kwargs))
        self.assertEqual(kwargs["base_url"], _OPENROUTER_BASE_URL)
        self.assertEqual(kwargs["api_key"], "test-key")
        self.assertNotIn("model_provider", kwargs)


if __name__ == "__main__":
    unittest.main()
