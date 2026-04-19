# Current Status

## 기준 시점
- Date: 2026-04-12
- Current phase: Phase 7 완료 (FastAPI LLM 게이트웨이)
- Python: 3.10.12 (.venv)
- LLM: Ollama gemma3:4b (기본) + OpenAI / Claude API / CLI fallback
- Validation: ruff check + ruff format + pytest 116 passed

## 아키텍처 현재 상태

```text
[클라이언트]
    |---- Discord 슬래시 커맨드 (/research, /followup, /history, /ping)
    |---- FastAPI HTTP API (/api/chat, /api/research, /api/followup, /api/history, /api/providers)
    |
    v
[AppContext (공유)]
    |---- [Supervisor / Orchestrator]
    |         |---- [ResearchAgent] ← DuckDuckGo 웹 검색
    |         |---- [AnalystAgent]  ← 리서치 요약을 컨텍스트로 받음
    |         |---- [WriterAgent]   ← 리서치 요약을 컨텍스트로 받음
    |
    |---- [FallbackProvider (프로바이더 체인)]
    |         |---- OllamaProvider      (로컬, 무료, 빠름)
    |         |---- ClaudeCLIProvider   (구독 내, 추가 비용 없음)
    |         |---- CodexCLIProvider    (구독 내, 추가 비용 없음)
    |         |---- OpenAIProvider      (유료, 빠름)
    |         |---- ClaudeAPIProvider   (유료, 고품질)
    |
    |---- [HistoryStore (SQLite)] ← 리서치 결과 영구 저장
```

## 완료된 Phase

### Phase 0~3: 기반 구축 (완료)
- 그린필드 스캐폴드, 단일 에이전트 MVP, 오케스트레이터, DuckDuckGo 웹 검색

### Phase 4: 운영 안정화 (부분 완료)
- ✅ 구조화된 로깅, 토큰/시간 측정, 에러 계층, 회귀 테스트
- ✅ Provider fallback → Phase 6에서 완료

### Phase 5: 기능 확장 (완료)
- ✅ 리서치 히스토리 (SQLite, /history)
- ✅ 후속 질문 (/followup)

### Phase 6: 멀티 프로바이더 (완료)
- ✅ OpenAI API 프로바이더 (openai 라이브러리 재사용)
- ✅ Claude API 프로바이더 (anthropic 라이브러리)
- ✅ Claude CLI 프로바이더 (subprocess, 구독 내 비용 없음)
- ✅ Codex CLI 프로바이더 (subprocess, 구독 내 비용 없음)
- ✅ FallbackProvider (transient 에러 시 자동 전환)
- ✅ Router 확장 (체인 자동 구성, 이름 지정 조회, 상태 목록)

### Phase 7: FastAPI 통합 서버 (완료)
- ✅ AppContext 공유 모듈 (Discord + API 통합)
- ✅ Pydantic 스키마 (요청/응답 모델)
- ✅ 5개 엔드포인트: /api/chat, /api/research, /api/followup, /api/history, /api/providers
- ✅ API 전용 엔트리포인트 (api_app.py)
- ✅ discord_bot_token 선택적 (API 전용 모드 지원)

## 현재 디렉토리 구조 (주요 파일)

```text
ai-assistant/
├── app.py                          # Discord 봇 엔트리포인트
├── api_app.py                      # FastAPI 서버 엔트리포인트
├── config.py                       # Settings dataclass (새 프로바이더 설정 포함)
├── runtime_lock.py                 # 중복 실행 방지
├── schemas/
│   ├── research.py                 # ResearchRequest, AgentResult, ResearchResponse
│   └── api.py                      # Pydantic API 스키마
├── agents/
│   ├── base.py                     # BaseAgent ABC
│   ├── research_agent.py           # 웹 검색 + LLM 요약
│   ├── analyst_agent.py            # 비교 분석
│   └── writer_agent.py             # 다음 행동 제안
├── orchestrator/supervisor.py      # Supervisor (체이닝, 재시도, 추적)
├── interfaces/
│   ├── discord_bot.py              # 슬래시 커맨드 인터페이스 (AppContext 사용)
│   └── api_server.py               # FastAPI 앱
├── sources/web_search.py           # DuckDuckGo 검색 래퍼
├── storage/history.py              # HistoryStore (SQLite)
├── utils/text.py                   # chunk_text()
├── llm/
│   ├── base.py                     # BaseLLMProvider ABC, 에러 계층
│   ├── ollama_provider.py          # Ollama (로컬)
│   ├── openai_provider.py          # OpenAI API
│   ├── claude_api_provider.py      # Claude API
│   ├── claude_cli_provider.py      # Claude CLI subprocess
│   ├── codex_cli_provider.py       # Codex CLI subprocess
│   └── fallback_provider.py        # Fallback 체인
├── services/
│   ├── router.py                   # 프로바이더 팩토리 + 체인 빌더
│   ├── shared.py                   # AppContext (공유 컨텍스트)
│   └── calendar_service.py         # (레거시, Calendar 재통합 시 활용)
└── tests/                          # 116 tests
```

## 프로바이더 설정 (.env)

```bash
# 기본 (항상 활성)
OLLAMA_MODEL=gemma3:4b
OLLAMA_TIMEOUT_SECONDS=60

# CLI 프로바이더 (구독 내, 추가 비용 없음)
CLAUDE_CLI_ENABLED=true
CLAUDE_CLI_PATH=claude
CLAUDE_CLI_TIMEOUT_SECONDS=120
CODEX_CLI_ENABLED=true
CODEX_CLI_PATH=codex
CODEX_CLI_TIMEOUT_SECONDS=120

# API 프로바이더 (유료 — key가 있으면 활성화)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=60
CLAUDE_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-haiku-4-5-20251001
CLAUDE_TIMEOUT_SECONDS=60
```

## 실행 방법

```bash
cd /home/minje/pmj/ai-assistant
source .venv/bin/activate

# Discord 봇
python app.py

# API 서버 (Discord 토큰 없이도 실행 가능)
python api_app.py    # http://localhost:8000

# Ollama (필요 시)
ollama serve
```

## 다음 우선순위

자비스 로드맵 기능과 코드 개선을 병행한다.

### 단기 (바로 가능)
1. 레거시 코드 정리 (bot/, calendar_service.py)
2. .env.example 작성 (새 설정 반영)
3. 외부 API 연동 (날씨, 뉴스) — 자비스 3단계
4. Google Calendar 재통합 — 자비스 3단계
5. CLAUDE.md 업데이트

### 중기 (Mac mini 이전 후)
6. 음성 입출력 (Whisper STT + TTS) — 자비스 2단계
7. Phase 8: 스마트 라우팅 (프로바이더 다수 운영 시)
8. 상시 서버 운영 준비

### 장기
9. 프론트엔드 (React/Flutter)
10. 스마트홈 연동 (Home Assistant)
11. 개인화/습관 학습

## 메모
- gemma3:4b는 한국어 출력 안정, 중국어 전환 문제 없음
- 프로바이더 우선순위: Ollama(무료) → CLI(구독 내) → API(유료)
- CLI 프로바이더는 subprocess 호출이라 느리지만 추가 비용 없음
- Discord 봇과 API 서버는 별도 프로세스로 운영
- 테스트 헬퍼는 conftest.py의 make_settings()로 통합됨
