# OpenClaw Bot 인수인계 문서

작성일: 2026-03-02

---

## 1. 인프라 요약

| 항목 | 값 |
|------|-----|
| 도메인 | `bearbot.win` (Cloudflare Registrar, ~$7.18/년) |
| 퍼블릭 URL | `https://bearbot.win` |
| Cloudflare Zone ID | `31f253fe77ab1bbaf658684c0255debd` |
| Cloudflare Account ID | `416e8fd0b74dcf8b9170b651f0b790ce` |
| 터널 이름 | `clawbot-tunnel` |
| 터널 ID | `c5cb825e-6d33-4a3d-a6c0-df60fbeff0a1` |
| 터널 CNAME 대상 | `c5cb825e-6d33-4a3d-a6c0-df60fbeff0a1.cfargotunnel.com` |

---

## 2. 컨테이너 구성

### 실행 명령
```bash
cd infrastructure/bot
./run-with-tunnel.sh        # cloudflared + clawbot 동시 기동
```

### 개별 compose 조작
```bash
# 상태 확인
docker compose -f compose.yaml -f compose.tunnel.yaml ps

# 로그 확인
docker logs clawbot-cloudflared -f
docker logs clawbot-pseudolab -f

# 재시작 (설정 변경 시에는 down → up)
docker compose -f compose.yaml -f compose.tunnel.yaml down
docker compose -f compose.yaml -f compose.tunnel.yaml up -d
```

### 컨테이너 목록

| 컨테이너 | 이미지 | 역할 |
|----------|--------|------|
| `clawbot-pseudolab` | `python:3.12-slim` | FastAPI 봇 서버 (`:8080`) |
| `clawbot-cloudflared` | `cloudflare/cloudflared:latest` | Cloudflare Tunnel 커넥터 |

- Docker 네트워크: `clawbot-net` (external)
- 로컬 포트: `30023` → 컨테이너 `8080`

---

## 3. 환경 파일

### `infrastructure/bot/.env`
봇 실행에 필요한 시크릿 (Slack, Anthropic, Catalog API 등)

### `infrastructure/bot/.env.tunnel`
```
CLOUDFLARED_TUNNEL_TOKEN=eyJ...  # Cloudflare Tunnel 인증 토큰
TUNNEL_TOKEN=eyJ...              # cloudflared가 읽는 env var (동일한 값)
OPENCLAW_PUBLIC_BASE_URL=https://bearbot.win
```

> **주의**: `TUNNEL_TOKEN`은 cloudflared가 `$TUNNEL_TOKEN` 환경변수로 자동 읽음.
> `compose.tunnel.yaml`의 `command: tunnel run`만 있으면 토큰 자동 인식.

---

## 4. Cloudflare Tunnel 설정 내역

### Ingress 규칙 (원격 관리)
```json
{
  "ingress": [
    { "hostname": "bearbot.win", "service": "http://clawbot:8080" },
    { "service": "http_status:404" }
  ]
}
```
> 변경 시: Cloudflare Zero Trust → Networks → Tunnels → clawbot-tunnel → Public Hostname

### DNS 레코드
| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `bearbot.win` (`@`) | `c5cb825e-...cfargotunnel.com` | ✅ Proxied |

---

## 5. ⚠️ 미완료 / 확인 필요 사항

### 5-1. DNS CNAME 업데이트 (필수)
Cloudflare API 토큰 권한 부족으로 수동 업데이트 필요.

**Cloudflare Dashboard → bearbot.win → DNS → CNAME 편집:**
- Target: `c5cb825e-6d33-4a3d-a6c0-df60fbeff0a1.cfargotunnel.com`

### 5-2. clawbot-pseudolab 헬스체크 unhealthy
컨테이너 기동 직후 `unhealthy` 상태. 봇 앱이 아직 초기화 중이거나 `.env`의 Slack 토큰 미설정 가능성 있음.

```bash
# 확인
docker logs clawbot-pseudolab | tail -30
curl -i http://127.0.0.1:30023/health
```

### 5-3. Slack App 설정
`.env`의 아래 값이 비어 있으면 봇 작동 불가:
```
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_CHANNEL_ID=
```

Slack App URL 등록 필요:
- Slash Command: `https://bearbot.win/slack/command`
- Interactivity: `https://bearbot.win/slack/interactive`

자동 설정:
```bash
./infrastructure/bot/provision-slack-app.sh
```

---

## 6. compose.tunnel.yaml 수정 내역

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 이미지 | `cloudflare/cloudflared:2026.2.1` (존재하지 않음) | `cloudflare/cloudflared:latest` |
| command | `tunnel --no-autoupdate run --token ${CLOUDFLARED_TUNNEL_TOKEN:-}` | `tunnel run` |

> ENTRYPOINT가 이미 `cloudflared --no-autoupdate`를 포함하므로
> command에 `--no-autoupdate` 중복 시 토큰 파싱 실패함.
> `TUNNEL_TOKEN` env var를 env_file에서 읽어 cloudflared가 자동 처리.

---

## 7. 헬스체크

```bash
# 로컬 봇 확인
curl -i http://127.0.0.1:30023/health
curl -i http://127.0.0.1:30023/health/ready

# 퍼블릭 URL 확인 (DNS 업데이트 후)
curl -i https://bearbot.win/health

# 터널 상태 확인
docker logs clawbot-cloudflared | grep -E "(Registered|ERR|WARN)"
```
