# 통합 LLM 게이트웨이 로드맵

## 문서 범위
이 문서는 로컬 LLM(Ollama)과 외부 LLM(Claude API, OpenAI API)을 하나의 API 서버로 통합 관리하는 로드맵이다.
기존 멀티에이전트 리서치 비서(Phase 0~5)를 기반으로 확장한다.

## 배경

현재 상태:
- Ollama(gemma3:4b): ai-assistant 프로젝트 전용, Discord 봇으로만 접근
- Claude CLI: 터미널에서 별도 사용
- Codex: 터미널에서 별도 사용
- 세 도구 사이에 컨텍스트 공유 없음, 각각 독립 운영

목표:
- 하나의 API 서버에서 모든 LLM을 통합 관리
- 프로바이더 간 라우팅, 위임, 컨텍스트 공유
- Discord 외에 HTTP API로도 접근 가능

## 목표 아키텍처

```text
[클라이언트]
    |---- Discord 봇 (기존)
    |---- HTTP API (신규)
    |---- CLI (향후)
    |
    v
[FastAPI 통합 서버]
    |
    |---- /api/chat          → 단순 대화 (라우팅 규칙으로 LLM 자동 선택)
    |---- /api/research      → 멀티에이전트 리서치 파이프라인
    |---- /api/followup      → 후속 질문
    |---- /api/history       → 히스토리 조회
    |---- /api/providers     → 프로바이더 상태 확인
    |
    v
[LLM Router]
    |---- 라우팅 규칙 (복잡도, 비용, 가용성 기반)
    |---- 프로바이더 헬스 체크
    |---- 비용/토큰 추적
    |
    |---- [OllamaProvider]       로컬, 무료, 빠름 (gemma3:4b)
    |---- [ClaudeCLIProvider]   구독 내, 추가 비용 없음 (claude subprocess)
    |---- [CodexCLIProvider]    구독 내, 추가 비용 없음 (codex subprocess)
    |---- [ClaudeAPIProvider]   유료, 고품질 추론 (claude-haiku / sonnet)
    |---- [OpenAIAPIProvider]   유료, 범용 (gpt-4o-mini)
    |
    v
[HistoryStore (SQLite)]     → 모든 프로바이더 공유
```

## 단계별 로드맵

### Phase 6. 멀티 프로바이더 (기존 Phase 4-1 확장)
외부 LLM 프로바이더를 추가하고 fallback 체인을 구성한다.
API 직접 호출과 CLI subprocess 호출 두 가지 방식을 모두 지원한다.

#### 6-A. API 프로바이더 (유료, 사용량 과금)
- `llm/openai_provider.py` — OpenAI API 프로바이더 (openai 라이브러리 재사용)
- `llm/claude_api_provider.py` — Anthropic Claude API 프로바이더 (anthropic 라이브러리 추가)

#### 6-B. CLI 프로바이더 (구독 내 포함, 추가 비용 없음)
기존 Claude Code / Codex CLI 구독을 subprocess로 활용한다.
개인용 도구에서 추가 비용 없이 고품질 모델을 쓸 수 있는 실용적 방법이다.

- `llm/claude_cli_provider.py` — `claude -p "prompt"` subprocess 호출
- `llm/codex_cli_provider.py` — `codex -q "prompt"` subprocess 호출

CLI 프로바이더 특징:
```text
장점: 구독 내 포함 (추가 비용 없음), 고품질 모델 사용 가능
단점: 프로세스 생성 오버헤드로 응답 느림, 출력 파싱 필요, 동시성 제한
적합: 개인용, 비용 민감, 빈도 낮은 고품질 요청
```

구현 방식:
```python
# claude_cli_provider.py 핵심 구조
class ClaudeCLIProvider(BaseLLMProvider):
    async def _call_cli(self, prompt: str, system: str | None) -> str:
        cmd = ["claude", "-p", prompt]
        if system:
            cmd.extend(["--system", system])
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        return stdout.decode().strip()
```

#### 공통
- `llm/fallback_provider.py` — primary → fallback 체인 (transient 에러만 전환)
- `services/router.py` 확장 — API key / CLI 가용성에 따라 프로바이더 자동 조합
- `config.py` — 프로바이더별 설정

설정 예시:
```bash
# .env

# API 프로바이더 (유료 — API key가 있으면 활성화)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
CLAUDE_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-haiku-4-5-20251001

# CLI 프로바이더 (구독 내 — 바이너리 경로가 있으면 활성화)
CLAUDE_CLI_PATH=claude              # 기본: PATH에서 탐색
CODEX_CLI_PATH=codex                # 기본: PATH에서 탐색
CLAUDE_CLI_ENABLED=true             # CLI 프로바이더 사용 여부
CODEX_CLI_ENABLED=true              # CLI 프로바이더 사용 여부
```

프로바이더 우선순위 (기본):
```text
1. Ollama (로컬, 무료, 빠름)
2. Claude CLI / Codex CLI (구독 내, 추가 비용 없음, 느림)
3. Claude API / OpenAI API (유료, 빠름, 최후 수단)
```

완료 기준:
- Ollama 실패 시 CLI → API 순서로 자동 전환
- 프로바이더별 토큰/비용 추적
- 기존 Discord 봇이 fallback 체인으로 동작
- CLI 프로바이더는 구독만으로 추가 비용 없이 동작

### Phase 7. FastAPI 통합 서버
Discord 외에 HTTP API로도 접근 가능한 서버를 만든다.

범위:
- `interfaces/api_server.py` — FastAPI 앱
  - `POST /api/chat` — 단순 대화 (프로바이더 지정 가능)
  - `POST /api/research` — 리서치 파이프라인 호출
  - `POST /api/followup` — 후속 질문
  - `GET /api/history` — 히스토리 조회/검색
  - `GET /api/providers` — 프로바이더 상태 및 가용성
- `app.py` 확장 — Discord 봇 + FastAPI 동시 운영 (또는 별도 엔트리포인트)
- 의존성 추가: `fastapi`, `uvicorn`

API 예시:
```
POST /api/chat
{
  "message": "RAG란 무엇인가?",
  "provider": "auto"           # auto | ollama | claude-cli | codex-cli | claude-api | openai-api
}

POST /api/research
{
  "query": "RAG vs fine-tuning 비교"
}
```

완료 기준:
- curl / HTTP 클라이언트로 리서치 파이프라인 호출 가능
- Discord 봇과 API 서버가 동일한 Supervisor, HistoryStore 공유
- 프로바이더를 명시적으로 선택하거나 auto로 라우팅 가능

### Phase 8. 스마트 라우팅
질문 복잡도와 비용 정책에 따라 자동으로 최적의 LLM을 선택한다.

범위:
- `services/routing_policy.py` — 라우팅 규칙 엔진
  - 규칙 예시: 토큰 수 < 200 → Ollama, 코드 생성 → OpenAI, 복잡한 추론 → Claude
  - 프로바이더 가용성 체크 (헬스 체크)
  - 일일 외부 API 비용 한도 설정
- 프로바이더별 헬스 체크 (Ollama 서버 상태 등)
- 비용 추적 테이블 (SQLite 또는 별도 집계)

라우팅 전략:
```text
1. 사용자가 프로바이더 지정 → 해당 프로바이더 사용
2. auto 모드 (비용 최소화 우선):
   a. Ollama 가용 + 간단한 쿼리 → Ollama (무료, 빠름)
   b. 복잡한 쿼리 + CLI 가용 → Claude CLI / Codex CLI (구독 내, 느림)
   c. CLI 불가용 또는 타임아웃 → API fallback (유료, 빠름)
   d. Ollama 불가용 → CLI → API 순서로 fallback
   e. 일일 API 비용 한도 초과 → Ollama + CLI only, API 차단 + 경고
```

완료 기준:
- 간단한 질문은 Ollama, 복잡한 질문은 CLI → API 순서로 자동 분배
- 일일 API 비용 한도를 설정하고 초과 시 경고
- 프로바이더 장애 시 자동 전환
- CLI 프로바이더 사용 시 추가 비용 없이 고품질 응답 가능

### Phase 9. 위임 체인 (에이전트 간 통신)
로컬 LLM이 작업의 일부를 외부 LLM에 위임할 수 있게 한다.

범위:
- 에이전트가 스스로 "이 작업은 더 강한 모델이 필요하다"고 판단하는 메커니즘
  - 응답 품질 자체 평가 (confidence score)
  - 특정 키워드/패턴 감지 (코드 생성, 수학, 긴 추론)
- 위임 프로토콜: ResearchAgent가 Ollama로 시도 → 품질 부족 시 Claude로 재시도
- 위임 이력 추적 (어떤 에이전트가 어떤 프로바이더를 사용했는지)

완료 기준:
- 로컬 모델의 한계를 넘는 질문이 자동으로 외부 LLM에 위임
- 위임 없이도 기존 파이프라인이 정상 동작 (opt-in 방식)

### Phase 10. 운영 고도화

후보 범위:
- API 인증 (API key 또는 JWT) — 외부 노출 시 필수
- 요청 큐 및 동시성 제한 (16GB 노트북 보호)
- 프로바이더별 비용 대시보드
- 요청/응답 로그 뷰어
- MCP 서버로 패키징 (Claude Code에서 직접 호출)
- Mac mini 배포 자동화

## 의존성 추가 예상

| Phase | 패키지 | 용도 |
|-------|--------|------|
| 6-A | `anthropic` | Claude API (유료 프로바이더 사용 시만) |
| 6-B | 없음 (stdlib subprocess) | CLI 프로바이더는 추가 의존성 없음 |
| 7 | `fastapi`, `uvicorn` | HTTP 서버 |
| 8~10 | 추가 없음 예상 | 내부 로직 |

## 주요 리스크

- 외부 API 비용 관리: 자동 라우팅이 의도치 않게 비용을 높일 수 있다 → 일일 한도 필수
- 로컬 모델 복잡도 판단의 정확도: gemma3:4b가 "내가 못 하는 질문"을 판단하기 어려울 수 있다 → 초기에는 규칙 기반, 점진적으로 개선
- Discord 봇 + FastAPI 동시 운영: 이벤트 루프 공유 또는 별도 프로세스 필요 → 초기에는 별도 엔트리포인트가 안전
- 16GB 노트북 리소스: Ollama + FastAPI + Discord 봇 동시 운영 시 메모리 부담 → Mac mini 이전 고려

## 구현 순서 요약

```text
Phase 6: 멀티 프로바이더     ← 내일 시작
Phase 7: FastAPI 서버
Phase 8: 스마트 라우팅
Phase 9: 위임 체인
Phase 10: 운영 고도화
```

Phase 6~7이 핵심이고, Phase 8~10은 실사용 피드백을 보고 범위를 조정한다.
