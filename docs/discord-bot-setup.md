# Discord Novice 봇 생성 가이드

## 1. Discord 애플리케이션 생성

1. [Discord Developer Portal](https://discord.com/developers/applications)에 로그인
2. **New Application** 클릭
3. 이름을 `Novice`로 입력하고 생성

## 2. Bot 설정

1. 왼쪽 메뉴에서 **Bot** 선택
2. **Reset Token** 클릭하여 토큰 생성 → 복사하여 `.env`의 `DISCORD_BOT_TOKEN`에 저장
3. **Privileged Gateway Intents** 설정:
   - **Message Content Intent**: 슬래시 커맨드만 사용하면 불필요, `!ask` 같은 메시지 커맨드를 쓸 경우 필요

## 3. 봇을 서버에 초대

1. 왼쪽 메뉴에서 **OAuth2** 선택
2. **OAuth2 URL Generator**에서:
   - **Scopes**: `bot`, `applications.commands` 체크
   - **Bot Permissions**: `Send Messages`, `Use Slash Commands` 체크
3. 생성된 URL을 브라우저에 붙여넣기
4. 초대할 서버를 선택하고 **승인**

## 4. 테스트 서버 설정

1. Discord 앱에서 **서버 추가** → 직접 만들기
2. 서버 이름 설정 후 생성
3. 서버 ID 확인:
   - Discord 설정 → **고급** → **개발자 모드** 켜기
   - 왼쪽 서버 목록에서 서버 **우클릭** → **서버 ID 복사**
4. `.env`에 `DISCORD_DEV_GUILD_ID=복사한ID` 추가

## 5. 제공되는 슬래시 커맨드

- `/ping`, `/research`, `/followup`, `/history`
- `DISCORD_DEV_GUILD_ID`가 설정되면 해당 길드에 즉시 동기화 (개발용)
- 미설정 시 전역 커맨드로 등록 (수 분 지연)

## 6. 실행

```bash
source .venv/bin/activate
python app.py
```
