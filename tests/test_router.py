import pytest
from conftest import make_settings

from llm.claude_api_provider import ClaudeAPIProvider
from llm.claude_cli_provider import ClaudeCLIProvider
from llm.codex_cli_provider import CodexCLIProvider
from llm.fallback_provider import FallbackProvider
from llm.ollama_provider import OllamaProvider
from llm.openai_provider import OpenAIProvider
from services.router import get_llm_provider, get_provider_by_name, list_available_providers


class TestGetLLMProvider:
    def test_ollama_only_returns_single_provider(self):
        provider = get_llm_provider(make_settings())
        assert isinstance(provider, OllamaProvider)

    def test_with_openai_key_returns_fallback(self):
        provider = get_llm_provider(make_settings(openai_api_key="sk-test"))
        assert isinstance(provider, FallbackProvider)
        assert len(provider._providers) == 2
        assert isinstance(provider._providers[0], OllamaProvider)
        assert isinstance(provider._providers[1], OpenAIProvider)

    def test_with_claude_key_returns_fallback(self):
        provider = get_llm_provider(make_settings(claude_api_key="sk-ant-test"))
        assert isinstance(provider, FallbackProvider)
        assert isinstance(provider._providers[1], ClaudeAPIProvider)

    def test_with_cli_enabled_returns_fallback(self):
        provider = get_llm_provider(make_settings(claude_cli_enabled=True))
        assert isinstance(provider, FallbackProvider)
        assert isinstance(provider._providers[1], ClaudeCLIProvider)

    def test_full_chain_order(self):
        provider = get_llm_provider(
            make_settings(
                claude_cli_enabled=True,
                codex_cli_enabled=True,
                openai_api_key="sk-test",
                claude_api_key="sk-ant-test",
            )
        )
        assert isinstance(provider, FallbackProvider)
        types = [type(p) for p in provider._providers]
        assert types == [
            OllamaProvider,
            ClaudeCLIProvider,
            CodexCLIProvider,
            OpenAIProvider,
            ClaudeAPIProvider,
        ]


class TestGetProviderByName:
    def test_ollama(self):
        p = get_provider_by_name("ollama", make_settings())
        assert isinstance(p, OllamaProvider)

    def test_openai_api_with_key(self):
        p = get_provider_by_name("openai-api", make_settings(openai_api_key="sk-test"))
        assert isinstance(p, OpenAIProvider)

    def test_openai_api_without_key_raises(self):
        with pytest.raises(RuntimeError, match="API key"):
            get_provider_by_name("openai-api", make_settings())

    def test_claude_api_with_key(self):
        p = get_provider_by_name("claude-api", make_settings(claude_api_key="sk-ant-test"))
        assert isinstance(p, ClaudeAPIProvider)

    def test_claude_cli_disabled_raises(self):
        with pytest.raises(RuntimeError, match="비활성화"):
            get_provider_by_name("claude-cli", make_settings())

    def test_unknown_name_raises(self):
        with pytest.raises(RuntimeError, match="알 수 없는"):
            get_provider_by_name("groq", make_settings())


class TestListAvailableProviders:
    def test_ollama_only(self):
        result = list_available_providers(make_settings())
        assert len(result) == 1
        assert result[0]["name"] == "ollama"

    def test_all_providers(self):
        result = list_available_providers(
            make_settings(
                claude_cli_enabled=True,
                codex_cli_enabled=True,
                openai_api_key="sk-test",
                claude_api_key="sk-ant-test",
            )
        )
        names = [p["name"] for p in result]
        assert names == ["ollama", "claude-cli", "codex-cli", "openai-api", "claude-api"]
