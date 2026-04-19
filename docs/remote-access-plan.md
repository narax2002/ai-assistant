# 외부 접속 설정 계획

## 목표

서버 PC(Ubuntu, 16GB)에서 실행 중인 FastAPI AI 비서(`api_app.py`, 포트 8000)를 외부 네트워크(카페, 회사 등)에서 접근 가능하게 한다.

## 솔루션 비교

| 솔루션 | 무료 티어 | 설치 난이도 | 보안 | 상시 운영 | 지연 | 공개 노출 |
|--------|-----------|-------------|------|-----------|------|-----------|
| **Tailscale** | 100대, 3유저 | 매우 쉬움 (1패키지 + 로그인) | WireGuard 암호화, SSO | systemd 데몬, 자동 재연결 | 매우 낮음 (P2P) | 없음 — 비공개 메시 |
| Cloudflare Tunnel | 무제한 | 보통 (cloudflared + DNS) | Zero-trust, TLS | systemd, 자동 재연결 | 낮음~보통 | 있음 — 공개 URL |
| WireGuard | 무료 (오픈소스) | 어려움 (키 생성, 포트포워딩) | 강력한 암호화 | systemd | 최저 | 포트 오픈 필요 |
| ngrok | 1에이전트, 20req/분 | 가장 쉬움 | TLS | 재시작 시 URL 변경 | 보통 | 있음 — 공개 URL |
| ZeroTier | 25대 | 쉬움 | P2P 암호화 | systemd 데몬 | 매우 낮음 | 없음 |

## 추천: Tailscale

개인용 AI 비서 접속에 **Tailscale**이 최적인 이유:

1. **공개 노출 없음** — 포트가 인터넷에 노출되지 않음 (Cloudflare/ngrok은 공개 URL 생성)
2. **설치 1분** — 서버에 패키지 설치 + 클라이언트에 앱 설치, 라우터 설정 불필요
3. **NAT/방화벽 통과** — 포트포워딩 없이 동작 (DERP 릴레이 → P2P 자동 전환)
4. **ACL** — 포트 8000만 허용하도록 접근 제한 가능
5. **상시 운영** — systemd 데몬, 재부팅/네트워크 변경 시 자동 재연결
6. **무료** — 100대까지 무료, 개인용으로 충분

## 구현 계획

### 1단계: Tailscale 설치 (서버 PC)

```bash
# Ubuntu에 Tailscale 설치
curl -fsSL https://tailscale.com/install.sh | sh

# 로그인 (브라우저 열림)
sudo tailscale up

# 상태 확인
tailscale status

# IP 확인 (100.x.x.x 형식)
tailscale ip -4
```

설치 시 `tailscaled.service`가 자동으로 systemd에 등록됨 — 재부팅 후 자동 시작.

### 2단계: Tailscale 설치 (클라이언트 — 외부 PC/폰)

- **Mac/Windows/Linux**: https://tailscale.com/download
- **iOS/Android**: 앱스토어에서 Tailscale 설치
- 같은 계정으로 로그인

### 3단계: 접속 테스트

```bash
# 클라이언트에서 서버의 Tailscale IP로 접속
curl http://100.x.x.x:8000/api/providers

# 리서치 요청
curl -X POST http://100.x.x.x:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트 주제"}'
```

### 4단계: ACL 설정 (선택, 권장)

Tailscale 관리 콘솔(https://login.tailscale.com/admin/acls)에서 포트 제한:

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["your-email@gmail.com"],
      "dst": ["서버호스트명:8000"]
    }
  ]
}
```

→ 포트 8000만 허용, 나머지 포트는 차단.

### 5단계: api_app.py 상시 운영 (선택)

```bash
# systemd 서비스로 등록하여 재부팅 후 자동 시작
sudo tee /etc/systemd/system/ai-assistant-api.service << 'EOF'
[Unit]
Description=AI Assistant API Server
After=network.target tailscaled.service

[Service]
Type=simple
User=minje
WorkingDirectory=/home/minje/pmj/ai-assistant
ExecStart=/home/minje/pmj/ai-assistant/.venv/bin/python api_app.py
Restart=always
RestartSec=5
EnvironmentFile=/home/minje/pmj/ai-assistant/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-assistant-api
sudo systemctl start ai-assistant-api

# 상태 확인
sudo systemctl status ai-assistant-api
```

## Cloudflare Tunnel (대안)

Tailscale 대신 **다른 사람에게도 공유**하고 싶다면 Cloudflare Tunnel이 적합:
- 공개 URL 생성 (`https://api.yourdomain.com`)
- Cloudflare Access로 인증 추가 가능
- 단, 도메인 필요 + DNS 설정 필요

현재는 개인용이므로 Tailscale 우선.

## 요약

```text
설치: Tailscale (서버 + 클라이언트) → 5분
접속: http://100.x.x.x:8000/api/* → 즉시
보안: ACL로 포트 8000만 허용
운영: systemd 서비스로 상시 실행
```
