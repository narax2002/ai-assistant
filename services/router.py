import logging

from config import Settings
from llm.base import BaseLLMProvider
from llm.claude_api_provider import ClaudeAPIProvider
from llm.claude_cli_provider import ClaudeCLIProvider
from llm.codex_cli_provider import CodexCLIProvider
from llm.fallback_provider import FallbackProvider
from llm.ollama_provider import OllamaProvider
from llm.openai_provider import OpenAIProvider

LOGGER = logging.getLogger(__name__)

# name → (class, availability check description)
_PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    "ollama": OllamaProvider,
    "openai-api": OpenAIProvider,
    "claude-api": ClaudeAPIProvider,
    "claude-cli": ClaudeCLIProvider,
    "codex-cli": CodexCLIProvider,
}


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    """Build a fallback chain: Ollama → CLI providers → API providers."""
    providers: list[BaseLLMProvider] = []

    # 1. Local (free, fast)
    providers.append(OllamaProvider(settings))

    # 2. CLI (subscription-based, no extra cost)
    if settings.claude_cli_enabled:
        providers.append(ClaudeCLIProvider(settings))
        LOGGER.info("Claude CLI provider enabled")
    if settings.codex_cli_enabled:
        providers.append(CodexCLIProvider(settings))
        LOGGER.info("Codex CLI provider enabled")

    # 3. API (paid, last resort)
    if settings.openai_api_key:
        providers.append(OpenAIProvider(settings))
        LOGGER.info("OpenAI API provider enabled (model=%s)", settings.openai_model)
    if settings.claude_api_key:
        providers.append(ClaudeAPIProvider(settings))
        LOGGER.info("Claude API provider enabled (model=%s)", settings.claude_model)

    LOGGER.info("Provider chain: %d provider(s)", len(providers))

    if len(providers) == 1:
        return providers[0]
    return FallbackProvider(providers)


def get_provider_by_name(name: str, settings: Settings) -> BaseLLMProvider:
    """Return a specific provider by name. Raises RuntimeError if unavailable."""
    if name == "ollama":
        return OllamaProvider(settings)
    if name == "openai-api":
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI API key가 설정되지 않았습니다.")
        return OpenAIProvider(settings)
    if name == "claude-api":
        if not settings.claude_api_key:
            raise RuntimeError("Claude API key가 설정되지 않았습니다.")
        return ClaudeAPIProvider(settings)
    if name == "claude-cli":
        if not settings.claude_cli_enabled:
            raise RuntimeError("Claude CLI가 비활성화되어 있습니다.")
        return ClaudeCLIProvider(settings)
    if name == "codex-cli":
        if not settings.codex_cli_enabled:
            raise RuntimeError("Codex CLI가 비활성화되어 있습니다.")
        return CodexCLIProvider(settings)
    raise RuntimeError(f"알 수 없는 프로바이더: {name}")


def list_available_providers(settings: Settings) -> list[dict[str, str]]:
    """Return list of available providers with name and type."""
    result: list[dict[str, str]] = []
    result.append({"name": "ollama", "type": "local", "model": settings.ollama_model})
    if settings.claude_cli_enabled:
        result.append({"name": "claude-cli", "type": "cli", "model": "claude"})
    if settings.codex_cli_enabled:
        result.append({"name": "codex-cli", "type": "cli", "model": "codex"})
    if settings.openai_api_key:
        result.append({"name": "openai-api", "type": "api", "model": settings.openai_model})
    if settings.claude_api_key:
        result.append({"name": "claude-api", "type": "api", "model": settings.claude_model})
    return result
