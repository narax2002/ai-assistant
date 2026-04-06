# AI Assistant

Discord-based personal AI assistant bootstrap.

The current MVP direction is a Python application that uses local `Ollama` first, keeps external integrations in Python, and adds more providers or services incrementally.

## Current Status

- Phase 1 scaffold is implemented
- `!ask` is available through the Discord bot
- `!schedule` and `!today` are implemented but disabled by default
- Ollama is the only supported LLM provider in the current code
- Environment-based configuration is centralized in `config.py`
- Duplicate bot startup is blocked by a local process lock
- Korean typo reduction is enabled with a proofreading pass after response generation
- Planning and architecture notes live under `markdown/`

## Project Layout

- `app.py`: application entrypoint
- `config.py`: environment-backed settings loader
- `runtime_lock.py`: prevents duplicate bot instances
- `pyproject.toml`: Ruff lint and format settings
- `requirements-dev.txt`: development-only dependencies
- `bot/`: Discord bot setup and commands
- `llm/`: provider interface and Ollama implementation
- `services/`: routing and service-layer code
- `data/`: local Google OAuth files such as `credentials.json` and `token.json`
- `markdown/`: roadmap and design documents

## Local Run

1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Set `DISCORD_BOT_TOKEN` in `.env`.
5. In the Discord Developer Portal, enable `Message Content Intent` for the bot application.
6. Install Ollama and pull the configured model.
7. Leave Google Calendar disabled unless you explicitly want to enable the OAuth flow later.
8. Start Ollama and run the bot with `python app.py`.

Example setup:

```bash
python3 -m virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data
ollama serve
ollama pull gemma3:4b
python app.py
```

## Development

Install development tools:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run lint checks for all Python files:

```bash
ruff check .
```

Apply safe autofixes where possible:

```bash
ruff check . --fix
```

Format Python files:

```bash
ruff format .
```

Run the minimal test suite:

```bash
pytest
```


## Google Calendar Setup

`!schedule` and `!today` are disabled by default to avoid prompting for a Google login during normal bot use.

To enable them later:

1. Enable Google Calendar API in Google Cloud.
2. Create a desktop OAuth client.
3. Save the downloaded JSON as `data/credentials.json`, or update the path in `.env`.
4. Set `ENABLE_GOOGLE_CALENDAR=true` in `.env`.
5. Run `!schedule` once and complete the browser consent flow. The bot writes `data/token.json` automatically.

Update `.env` before starting the bot:

```env
DISCORD_BOT_TOKEN=your_real_discord_bot_token
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=ollama
OLLAMA_MODEL=gemma3:4b
OLLAMA_TIMEOUT_SECONDS=60
ENABLE_PROOFREAD=true
ENABLE_GOOGLE_CALENDAR=false
GOOGLE_CALENDAR_CREDENTIALS_PATH=data/credentials.json
GOOGLE_CALENDAR_TOKEN_PATH=data/token.json
GOOGLE_CALENDAR_ID=primary
```

Install Ollama on Ubuntu:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Stop Ollama if you started it manually with `ollama serve`:

```bash
Ctrl+C
```

If Ollama was started as a system service instead, stop it with:

```bash
sudo systemctl stop ollama
```

If `python app.py` is already running, a second start will exit immediately with a lock error instead of bringing up a duplicate bot.

## Environment Variables

Required now:

- `DISCORD_BOT_TOKEN`

Common defaults already exist in `.env.example` for:

- `COMMAND_PREFIX`
- `LOG_LEVEL`
- `ENABLE_PROOFREAD`
- `ENABLE_GOOGLE_CALENDAR`
- `MAX_REPLY_CHARS`
- `OLLAMA_TIMEOUT_SECONDS`
- `LLM_PROVIDER`
- `OLLAMA_BASE_URL`
- `OLLAMA_API_KEY`
- `OLLAMA_MODEL`
- `SYSTEM_PROMPT`
- `GOOGLE_CALENDAR_CREDENTIALS_PATH`
- `GOOGLE_CALENDAR_TOKEN_PATH`
- `GOOGLE_CALENDAR_ID`

## Notes

- `LLM_PROVIDER` currently supports only `ollama`.
- `ENABLE_PROOFREAD=true` adds an extra local correction pass, so response latency increases a little.
- `ENABLE_GOOGLE_CALENDAR=false` keeps login-based calendar commands turned off.
- `OLLAMA_TIMEOUT_SECONDS` sets the per-request timeout for Ollama calls.
- The current `!ask`, `!schedule`, and `!today` commands require `Message Content Intent` to be enabled in the Discord Developer Portal.
- Long responses are split before sending to Discord.
- `!schedule` and `!today` return a disabled message until `ENABLE_GOOGLE_CALENDAR=true` is set.
- Linting and formatting are configured through Ruff in `pyproject.toml`.
- The next implementation phase is Groq fallback and runtime hardening.
