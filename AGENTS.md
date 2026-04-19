# Repository Guidelines

## Project Structure & Module Organization
This repository is still in the bootstrap phase. `README.md` provides the high-level summary, and design notes live under `docs/`. As implementation is added, keep the planned Python layout:

- `app.py` for the entrypoint
- `bot/` for Discord integration
- `llm/` for provider adapters such as Ollama and Groq
- `services/` for routing and Google Calendar logic
- `data/` for local credentials and tokens
- `docs/` for planning notes and contributor-facing docs

Keep Discord, LLM, and calendar concerns separated so provider swaps and future deployment changes stay low-risk.

## Build, Test, and Development Commands
Linting and formatting are configured with Ruff through `pyproject.toml`. There is still no committed test automation yet.

Expected local bootstrap, based on the current design:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Use these development commands:

```bash
ruff check .
ruff check . --fix
ruff format .
```

When tests are added, prefer a single entry command such as `python -m pytest`.

## Coding Style & Naming Conventions
Target Python 3.11. Use 4-space indentation, `snake_case` for modules and functions, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for environment variables. Keep provider-specific code inside `llm/` and configuration in `.env`, not hardcoded paths. Store long-form notes in `docs/` using descriptive lowercase file names such as `deployment-plan.md`.

## Testing Guidelines
There is no committed test suite yet. Add tests under `tests/` with names like `test_router.py` or `test_calendar_service.py`. Prefer `pytest` and mock external systems such as Discord, Ollama or Groq, and Google Calendar. Cover routing decisions, provider fallbacks, and command handling before merging.

## Commit & Pull Request Guidelines
Git history currently starts with a single `Initial commit`, so use short imperative commit subjects, for example `Add Discord bot scaffold` or `Document env setup`. PRs should include a clear summary, any environment or secret handling changes, manual verification steps, and linked issues when applicable. Include screenshots or log excerpts for Discord-facing behavior changes.

## Security & Configuration Tips
Do not commit `.env`, `data/credentials.json`, or `data/token.json`. Keep API keys, provider URLs, and deployment-specific settings in environment variables so the project can move from a laptop to a Mac mini without code changes.
