# C Core + Python API Roadmap

## 문서 범위
이 문서는 장기 아키텍처와 선택적 C 코어 확장 전략을 다루는 보조 로드맵이다.
실제 기능 개발 순서와 제품 일정 기준은 [Project Roadmap](./project-roadmap.md)를 따른다.

## 목표

이 문서는 `ai-assistant`를 장기적으로 어떻게 확장할지 정리한다.
기본 방향은 `Python 애플리케이션 + 선택적 C 코어 라이브러리` 구조다.

핵심은 전체 애플리케이션을 C로 다시 만드는 것이 아니라,
Python이 제품 레이어와 외부 연동을 계속 담당하고,
성격이 안정된 내부 로직만 C 라이브러리로 분리하는 것이다.

## 배경

현재 프로젝트의 1차 목표는 아래와 같다.

- Discord에서 동작하는 개인용 AI 비서
- 로컬 `Ollama` 우선 사용
- 필요 시 `Groq` fallback 사용
- Google Calendar 읽기 연동
- 환경변수 기반 설정으로 Mac mini 이전 비용 최소화

이 목표에서 핵심 복잡도는 아래에 있다.

- Discord 연동
- LLM 제공자 라우팅
- Google Calendar 인증 및 조회
- 설정과 배포 환경 관리
- 예외 처리와 운영 흐름

즉, 이 프로젝트는 `simple-chat-app`처럼 low-level 네트워크 서버가 중심인 구조가 아니다.
따라서 언어 전략도 다르게 가져가야 한다.

## 권장 결론

현재 시점의 권장 결론은 아래와 같다.

`Python을 애플리케이션 본체로 유지하고, 필요할 때만 일부 내부 엔진을 C 코어 라이브러리로 분리한다.`

이 전략이 맞는 이유는 다음과 같다.

1. Discord, Ollama, Groq, Google Calendar 연동은 Python 생태계가 훨씬 강하다.
2. 초기에는 속도보다 구조 학습과 경계 설계가 더 중요하다.
3. 성능 병목이 확인된 모듈만 C로 내리면 재구현 비용을 줄일 수 있다.
4. 외부 서비스 의존 부분을 C로 옮기면 학습보다 보일러플레이트 비용이 커진다.
5. Python과 C의 역할을 분리하면 장기적으로도 유지보수가 단순하다.

## 목표 구조

권장 구조는 아래와 같다.

```text
[Python App / API Layer]
    |
    |---- app.py
    |---- bot/
    |---- llm/
    |---- services/
    |---- config / logging / retries
    |---- tests/
    |
    v
[C Core Libraries]
    |
    |---- command parsing
    |---- text normalization
    |---- chunking / ranking
    |---- local memory or index engine
    |---- scheduling / rule engine
    |---- cache / queue / persistence core
```

이 구조의 의도는 다음과 같다.

- Python은 외부 API와 사용자 인터페이스를 담당한다.
- C는 SDK 의존성이 적은 내부 엔진만 담당한다.
- Python에서 C를 호출하는 구조를 기본으로 한다.
- 외부 연동은 끝까지 Python에 남겨도 괜찮다.

## 설계 원칙

### 1. Python을 제품 셸로 유지한다

아래 영역은 Python 중심이 맞다.

- Discord bot
- slash command 또는 message command 처리
- LLM provider adapter
- Google Calendar OAuth 및 API 호출
- `.env` 설정 로딩
- 로깅, retry, timeout, 운영 스크립트

이 영역은 외부 SDK와 API 정책 변화에 민감하므로,
C보다 Python이 훨씬 유리하다.

### 2. C는 순수 로직과 내부 엔진에 집중한다

C로 옮길 후보는 아래 조건을 만족하는 것이 좋다.

- 입력과 출력이 명확하다.
- 외부 API SDK 의존성이 거의 없다.
- 반복 호출되거나 CPU 비용이 누적된다.
- 테스트 경계가 비교적 분명하다.

### 3. 경계는 작고 명확하게 만든다

처음부터 큰 코어를 C로 만들지 않는다.
작은 모듈 하나를 정해 Python에서 라이브러리처럼 호출하는 방식으로 시작한다.

예를 들면 아래와 같다.

- `parse_command(text) -> ParsedCommand`
- `normalize_text(text) -> normalized_text`
- `rank_items(query, items) -> ranked_items`
- `next_schedule(events, rules) -> schedule_result`

### 4. callback 중심보다 request/response API를 우선한다

처음에는 Python이 C를 동기 호출하는 단순한 구조가 가장 낫다.
C에서 Python callback을 호출하는 구조는 초기에 피한다.

이유는 다음과 같다.

- 디버깅이 어렵다.
- 메모리 소유권 규칙이 복잡해진다.
- GIL과 스레드 이슈가 빨리 들어온다.
- 학습 초기에는 경계가 흐려진다.

### 5. C 확장은 성능보다 안정된 경계 기준으로 결정한다

아직 병목이 보이지 않았는데도 C로 옮기기 시작하면,
대부분은 속도 개선보다 개발 비용만 늘어난다.

우선순위는 아래 순서가 좋다.

1. 경계가 안정됐는가
2. Python 구현이 충분히 명확한가
3. 테스트가 준비됐는가
4. 성능 또는 학습 가치가 충분한가

## Python에 남길 것

아래 항목은 장기적으로도 Python에 두는 것이 자연스럽다.

- `app.py` 엔트리포인트
- `bot/discord_bot.py` 또는 이후 Discord 인터페이스
- `llm/` provider adapter
- `services/calendar_service.py`
- 환경변수와 설정 로딩
- 예외 처리, timeout, retry, 로깅
- 배포용 스크립트와 운영 도구

## C로 내리기 좋은 후보

### 1. 명령 파서와 전처리기

가장 좋은 첫 후보는 명령 파서다.
입출력이 단순하고, 외부 SDK 의존성이 없으며,
나중에 Discord 외의 인터페이스가 붙어도 재사용 가능하다.

예:

- `!ask`
- `!today`
- `!schedule`
- 관리자용 로컬 명령

### 2. 텍스트 정규화 / chunking / ranking

RAG나 문서 검색이 붙으면 이 부분은 점점 독립성이 높아진다.
문자열 처리와 반복 계산이 많아져 C 코어로 옮기기 좋다.

### 3. 로컬 메모리 저장소 또는 인덱스 엔진

장기 메모리나 검색 기능이 붙으면,
저장 구조와 검색 경로를 C 코어로 분리할 수 있다.
단, 파일 포맷과 API는 단순하게 시작해야 한다.

### 4. 일정 규칙 엔진

Google Calendar API 호출은 Python에 남기고,
가져온 이벤트를 해석해 우선순위나 알림 규칙을 계산하는 부분만
C로 분리하는 구조가 적절하다.

### 5. 캐시 / 큐 / 영속화 코어

응답 캐시, 작업 큐, 파일 기반 저장 같은 내부 메커니즘은
나중에 C 라이브러리로 분리할 수 있다.

## 지금 하지 않을 것

아래는 현재 단계에서 권장하지 않는다.

- Discord 연동을 C로 구현
- Ollama / Groq / OpenAI 호출부를 C로 구현
- Google OAuth 및 Calendar API를 C로 구현
- 전체 애플리케이션을 C로 다시 작성
- 처음부터 CPython extension으로 깊게 들어가기

이 방향은 학습 비용에 비해 얻는 가치가 낮다.
대부분의 시간은 제품 기능보다 HTTP, TLS, JSON, OAuth 보일러플레이트에 쓰이게 된다.

## 권장 FFI 접근

처음에는 아래 순서를 권장한다.

1. Python 구현으로 기능과 경계를 먼저 확정한다.
2. 작은 모듈 하나를 C로 재구현한다.
3. `cffi` 또는 `ctypes`로 붙인다.
4. API와 메모리 소유권 규칙을 정리한다.
5. 필요할 때만 더 큰 코어나 CPython extension을 검토한다.

초기에는 `cffi` 또는 `ctypes`가 충분하다.
중요한 것은 속도보다 경계 명확성과 디버깅 가능성이다.

## 마일스톤

아래 마일스톤은 제품 일정의 대체가 아니라, [Project Roadmap](./project-roadmap.md)와 병행해 보는 기술 전략 체크포인트다.

### M0. Python 본체 구조 고정

목표:

- `app.py`, `bot/`, `llm/`, `services/`, `markdown/` 구조를 기준선으로 고정한다.
- 외부 연동은 계속 Python에 둔다는 원칙을 정한다.

완료 기준:

- 프로젝트 구조와 역할 분리가 문서화된다.
- 외부 서비스 연동 위치가 명확해진다.

### M1. Python MVP 안정화

목표:

- Discord 질의 응답 흐름을 먼저 안정화한다.
- Ollama 연결, Groq fallback, Calendar 읽기까지 Python으로 일관되게 구현한다.

완료 기준:

- 핵심 사용자 흐름이 Python만으로 동작한다.
- 라우터, 캘린더 서비스, 설정 로딩 경계가 분명하다.

### M2. C 후보 모듈 선정

목표:

- Python 구현을 바탕으로 C로 내릴 만한 첫 모듈을 고른다.
- 입력, 출력, 데이터 구조, 테스트 포인트를 정리한다.

권장 첫 후보:

- 명령 파서
- 텍스트 정규화기
- 간단한 랭킹 또는 규칙 엔진

완료 기준:

- 첫 C 모듈이 하나로 좁혀진다.
- Python 인터페이스가 먼저 고정된다.

### M3. 최소 C 라이브러리 도입

목표:

- 작은 C 라이브러리를 별도 모듈로 추가한다.
- Python에서 이를 함수 호출 형태로 사용한다.

완료 기준:

- Python 코드가 C 라이브러리를 호출해 같은 결과를 낸다.
- 메모리 소유권과 오류 처리 방식이 문서화된다.

### M4. 테스트 경계 분리

목표:

- Python 테스트와 C 테스트를 분리한다.
- FFI 경계에서 문자열, 오류, edge case를 집중 검증한다.

완료 기준:

- Python 단위 테스트와 C 단위 테스트가 모두 존재한다.
- 경계 입력에 대한 회귀 테스트가 생긴다.

### M5. 내부 엔진 확장

목표:

- 필요 시 메모리 저장소, 검색 인덱스, 일정 규칙 계산기 같은 코어를 추가로 C로 분리한다.

완료 기준:

- C 코어가 여러 개가 되더라도 Python API 층은 안정적으로 유지된다.
- Discord, LLM, Calendar 코드는 큰 수정 없이 유지된다.

## 즉시 다음 작업

현재 시점에서 권장하는 다음 작업은 아래와 같다.

1. Python MVP 구조를 먼저 문서와 코드로 고정한다.
2. 명령 파서와 라우터 경계를 분리한다.
3. 나중에 C로 분리할 수 있게 함수 시그니처를 단순하게 설계한다.
4. C 후보 모듈의 입출력 예시를 문서로 남긴다.
5. Python 테스트를 먼저 준비해 교체 전 기준 동작을 확보한다.

## 판단 요약

`ai-assistant`에서의 Python+C 구조는,
`simple-chat-app`처럼 C가 본체가 되는 형태가 아니다.
이 프로젝트에서는 Python이 본체이고,
C는 필요할 때 붙는 선택적 내부 엔진 계층이 된다.

한 줄로 요약하면 아래와 같다.

`Python으로 제품을 만들고, 안정된 내부 모듈만 C 코어 라이브러리로 분리한다.`
