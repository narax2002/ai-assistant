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
pytest                          # all tests (65 tests)
pytest tests/test_agents.py     # single file
pytest -k test_handle           # by name pattern

# Run
ollama serve                    # start Ollama (if not running as service)
python app.py                   # start Discord bot
```

Ruff config is in `pyproject.toml`: Python 3.11 target, line length 100, rules E/F/I.

## Architecture

Multi-agent research assistant that responds to Discord `/research` slash commands with a structured four-section format: **핵심 요약 / 비교 / 다음 행동 / 출처**.

### Request Flow

```
Discord /research "query"
    → interfaces/discord_bot.py (slash command handler)
        → orchestrator/supervisor.py (Supervisor.handle)
            → ResearchAgent.run(query)        # DuckDuckGo search → LLM summary
            → AnalystAgent.run(query+summary)  # comparison using research context
            → WriterAgent.run(query+summary)   # action items using research context
        → ResearchResponse.format_discord()
        → HistoryStore.save()                  # SQLite에 결과 저장
    → Discord followup message

Discord /followup "question"
    → HistoryStore.get_latest()                # 이전 리서치 로드
    → 이전 결과를 컨텍스트로 조립
    → Supervisor.handle(context_query)         # 동일 파이프라인 재사용
    → HistoryStore.save()
    → Discord followup message

Discord /history
    → HistoryStore.list_recent()               # 최근 기록 조회/검색
    → Discord response
```

### Key Design Decisions

- **Context chaining**: ResearchAgent runs first, its output is passed as context to AnalystAgent and WriterAgent so they produce grounded analysis
- **Web search**: Only ResearchAgent searches DuckDuckGo. Sources (URLs) flow through to the final response
- **Graceful degradation**: Each agent call is wrapped with retry (max 2 attempts) and timeout (`asyncio.wait_for`). On failure, a fallback message replaces that section
- **Agent-level tracking**: `AgentResult` records success/failure, elapsed time, token usage, and error per agent. Total pipeline time and token count shown in Discord response
- **Token tracking**: `BaseLLMProvider.last_usage` (ChatUsage dataclass) stores prompt/completion tokens after each call. Supervisor reads this after each agent run
- **Error hierarchy**: `LLMError` (permanent) → `LLMTimeoutError` (transient) / `LLMConnectionError` (transient). `transient` class attribute used for retry decisions and logging
- **LLM provider**: `OllamaProvider` wraps OpenAI-compatible API. `chat()` accepts optional `system_prompt` so each agent uses its own role prompt
- **Sync→Async bridge**: `OllamaProvider.chat()` is synchronous; agents use `asyncio.to_thread()` to call it from async context

### Package Layout

| Package | Responsibility |
|---------|---------------|
| `schemas/` | `ResearchRequest`, `ResearchResponse`, `AgentResult` dataclasses |
| `agents/` | `BaseAgent` ABC + three role agents (research, analyst, writer) |
| `orchestrator/` | `Supervisor` — sequential dispatch, retry, context chaining |
| `interfaces/` | Discord `Client` + `CommandTree` with `/research` and `/ping` |
| `sources/` | `web_search.py` — DuckDuckGo wrapper with `SearchResult` |
| `storage/` | `HistoryStore` — SQLite-backed research history (save, query, paginate) |
| `utils/` | `chunk_text()` for Discord message splitting |
| `llm/` | `BaseLLMProvider` ABC, `OllamaProvider` |
| `services/` | `router.py` (provider factory), `calendar_service.py` (legacy) |
| `bot/` | Legacy message-command bot (to be removed) |

### Configuration

All config via environment variables, loaded in `config.py` as frozen `Settings` dataclass. Key settings:
- `DISCORD_BOT_TOKEN` (required)
- `OLLAMA_MODEL` (default: `gemma3:4b`)
- `OLLAMA_TIMEOUT_SECONDS` (default: 60, used as per-agent timeout)
- `HISTORY_DB_PATH` (default: `data/research_history.db`)
- `MAX_HISTORY_RECORDS` (default: 200, 최대 보관 건수 — 초과 시 오래된 기록 자동 삭제)
- `MAX_HISTORY_SIZE_MB` (default: 50, DB 파일 크기 경고 임계값 — 초과 시 로그 경고)
- `DISCORD_DEV_GUILD_ID` (optional, for instant slash command sync during dev)

### Model

Current model is `gemma3:4b` (Google, via Ollama). Chosen for stable Korean output — `qwen2.5:7b` was removed due to Chinese language mixing.

### Roadmap

Phase 0–3, 5 complete. Phase 4 partially done (logging, token tracking, error handling done; provider fallback pending — OpenAI + Claude API planned). Phase 5 added history storage + follow-up questions. Full roadmap in `markdown/project-roadmap.md`, current status in `markdown/current-status.md`.
