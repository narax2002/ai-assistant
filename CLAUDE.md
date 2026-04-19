# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
cd /home/minje/pmj/ai-assistant
source .venv/bin/activate

# Lint and format
ruff check .                    # lint
ruff check . --fix              # autofix
ruff format .                   # format
ruff format --check .           # format check only

# Test
pytest                          # all tests (116 tests)
pytest tests/test_agents.py     # single file
pytest -k test_handle           # by name pattern

# Run
ollama serve                    # start Ollama (if not running as service)
python app.py                   # start Discord bot
python api_app.py               # start FastAPI server (http://localhost:8000)
```

Ruff config is in `pyproject.toml`: Python 3.11 target, line length 100, rules E/F/I.

## Architecture

Multi-agent research assistant with Discord and HTTP API interfaces. Responds to queries with a structured four-section format: **핵심 요약 / 비교 / 다음 행동 / 출처**.

### Request Flow

```
Discord /research "query"  OR  POST /api/research {"query": "..."}
    → AppContext (shared wiring: services/shared.py)
        → orchestrator/supervisor.py (Supervisor.handle)
            → ResearchAgent.run(query)        # DuckDuckGo search → LLM summary
            → AnalystAgent.run(query+summary)  # comparison using research context
            → WriterAgent.run(query+summary)   # action items using research context
        → ResearchResponse
        → HistoryStore.save()                  # SQLite에 결과 저장
    → Discord followup message  OR  JSON response

POST /api/chat {"message": "...", "provider": "auto"}
    → FallbackProvider.chat()  OR  specific provider
    → JSON response
```

### Key Design Decisions

- **Multi-provider fallback**: `FallbackProvider` chains providers in priority order (Ollama → CLI → API). Only `transient` errors trigger fallback; permanent errors fail immediately
- **Context chaining**: ResearchAgent runs first, its output is passed as context to AnalystAgent and WriterAgent so they produce grounded analysis
- **Web search**: Only ResearchAgent searches DuckDuckGo. Sources (URLs) flow through to the final response
- **Graceful degradation**: Each agent call is wrapped with retry (max 2 attempts) and timeout (`asyncio.wait_for`). On failure, a fallback message replaces that section
- **Agent-level tracking**: `AgentResult` records success/failure, elapsed time, token usage, and error per agent
- **Error hierarchy**: `LLMError` (permanent) → `LLMTimeoutError` (transient) / `LLMConnectionError` (transient). `transient` class attribute used for retry and fallback decisions
- **Sync→Async bridge**: All provider `chat()` methods are synchronous; agents use `asyncio.to_thread()` to call from async context
- **Shared context**: `AppContext` (services/shared.py) wires provider, supervisor, and store once — shared by Discord bot and FastAPI server

### Package Layout

| Package | Responsibility |
|---------|---------------|
| `schemas/` | `ResearchRequest`, `ResearchResponse`, `AgentResult` dataclasses; Pydantic API models |
| `agents/` | `BaseAgent` ABC + three role agents (research, analyst, writer) |
| `orchestrator/` | `Supervisor` — sequential dispatch, retry, context chaining |
| `interfaces/` | `discord_bot.py` (slash commands), `api_server.py` (FastAPI) |
| `sources/` | `web_search.py` — DuckDuckGo wrapper with `SearchResult` |
| `storage/` | `HistoryStore` — SQLite-backed research history (save, query, paginate) |
| `utils/` | `chunk_text()` for Discord message splitting |
| `llm/` | `BaseLLMProvider` ABC, 5 providers (Ollama, OpenAI, Claude API, Claude CLI, Codex CLI), `FallbackProvider` |
| `services/` | `router.py` (provider factory + chain builder), `shared.py` (AppContext), `calendar_service.py` (legacy) |

### Configuration

All config via environment variables, loaded in `config.py` as frozen `Settings` dataclass. Key settings:
- `DISCORD_BOT_TOKEN` (optional — required for Discord bot, not needed for API-only mode)
- `OLLAMA_MODEL` (default: `gemma3:4b`)
- `OLLAMA_TIMEOUT_SECONDS` (default: 60, used as per-agent timeout)
- `OPENAI_API_KEY`, `OPENAI_MODEL` (default: `gpt-4o-mini`) — enables OpenAI provider
- `CLAUDE_API_KEY`, `CLAUDE_MODEL` (default: `claude-haiku-4-5-20251001`) — enables Claude API provider
- `CLAUDE_CLI_ENABLED`, `CODEX_CLI_ENABLED` — enables CLI subprocess providers
- `HISTORY_DB_PATH` (default: `data/research_history.db`)
- `MAX_HISTORY_RECORDS` (default: 200), `MAX_HISTORY_SIZE_MB` (default: 50)

### Model

Default model is `gemma3:4b` (Google, via Ollama). Chosen for stable Korean output. External providers (OpenAI, Claude) available as fallback via env config.

### Roadmap

Phase 0–7 complete. Phase 8–10 on hold. Full roadmap in `docs/project-roadmap.md`, current status in `docs/current-status.md`, Jarvis vision in `docs/jarvis-roadmap.md`.
