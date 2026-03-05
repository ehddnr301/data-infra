# OpenClaw Bot Operations Guide

## 0. Cloudflare Tunnel First (recommended)

OpenClaw is an always-on Docker service. The easiest production-safe exposure path is:

- run FastAPI in local/private Docker
- expose only through Cloudflare Tunnel
- register Slack request URLs with the Tunnel hostname

### 0.1 Prepare tunnel env

```bash
cp infrastructure/bot/.env.tunnel.example infrastructure/bot/.env.tunnel
```

Set at least:

- `CLOUDFLARED_TUNNEL_TOKEN`
- `OPENCLAW_PUBLIC_BASE_URL` (example: `https://clawbot.<your-domain>`)

### 0.1.1 Slack app one-shot provisioning with your config token

After `OPENCLAW_PUBLIC_BASE_URL` is set in `.env.tunnel`, run:

```bash
chmod +x infrastructure/bot/provision-slack-app.sh

SLACK_APP_CONFIG_TOKEN='xoxe.xoxp-...' \
./infrastructure/bot/provision-slack-app.sh
```

This wrapper reads `OPENCLAW_PUBLIC_BASE_URL` from `.env.tunnel` and calls
`infrastructure/bot/create-slack-app.sh` with Slack manifest validation + app creation.

### 0.2 Create remote-managed tunnel (Cloudflare Dashboard)

1. Go to Cloudflare Zero Trust > Networks > Tunnels > Create Tunnel.
2. Choose `cloudflared` connector and select Docker runtime.
3. In Public Hostnames, add:
   - Hostname: `clawbot.<your-domain>`
   - Service: `http://clawbot:8080`
4. Copy the tunnel token into `.env.tunnel`.

### 0.3 Run OpenClaw + Tunnel together

```bash
./infrastructure/bot/run-with-tunnel.sh
```

Validate:

```bash
curl -i http://127.0.0.1:30023/health
curl -i "${OPENCLAW_PUBLIC_BASE_URL}/health"
```

Now Slack URLs become:

- `${OPENCLAW_PUBLIC_BASE_URL}/slack/command`
- `${OPENCLAW_PUBLIC_BASE_URL}/slack/interactive`

## 1. Slack App Setup

### Option A) Script-assisted setup (recommended)

You can generate a Slack app manifest automatically, and optionally create the app via Slack API.

```bash
chmod +x infrastructure/bot/create-slack-app.sh

# 1) Manifest generation only
OPENCLAW_PUBLIC_BASE_URL="https://clawbot.<your-domain>" \
  ./infrastructure/bot/create-slack-app.sh

# 2) Create app via API (requires app config token)
OPENCLAW_PUBLIC_BASE_URL="https://clawbot.<your-domain>" \
SLACK_APP_CONFIG_TOKEN="xapp-..." \
./infrastructure/bot/create-slack-app.sh
```

Optional environment variables:

- `SLACK_WORKSPACE_TEAM_ID=T...` (recommended when token can access multiple workspaces)
- `SLACK_APP_NAME`, `SLACK_BOT_DISPLAY_NAME`, `SLACK_COMMAND_NAME`

The script outputs:

- `infrastructure/bot/slack-app-manifest.generated.json`
- app creation result (`app_id`, `client_id`, `signing_secret`, `oauth_authorize_url`) when API mode is used

After app install, fill `infrastructure/bot/.env` with:

- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`
- `SLACK_CHANNEL_ID`

### Option B) Manual setup

1. Open `https://api.slack.com/apps` and create a new app from scratch.
2. In OAuth scopes, add:
   - `chat:write`
   - `chat:write.public`
   - `commands`
   - `channels:history`
3. Create slash command `/clawbot` with request URL:
   - `https://<clawbot_host>/slack/command`
4. Enable Interactivity and set request URL:
   - `https://<clawbot_host>/slack/interactive`
5. Install app to workspace and copy `SLACK_BOT_TOKEN`.
6. Copy Signing Secret to `SLACK_SIGNING_SECRET`.
7. Invite bot to `#clawbot-ops` and set channel id as `SLACK_CHANNEL_ID`.

## 2. Environment Setup

1. Copy `.env.example` to `.env` in `infrastructure/bot/`.
2. Fill all required secrets.
3. Keep `OPENCLAW_RUN_MODE=dry-run` and `OPENCLAW_WRITE_ENABLED=false` during pilot.

## 3. Runbook

```bash
docker compose -f infrastructure/bot/compose.yaml config
docker compose -f infrastructure/bot/compose.yaml up -d
docker compose -f infrastructure/bot/compose.yaml ps
docker compose -f infrastructure/bot/compose.yaml logs -f clawbot
```

Health checks:

```bash
curl -i http://127.0.0.1:30023/health
curl -i http://127.0.0.1:30023/health/ready
```

Restart recovery test:

```bash
docker kill clawbot-pseudolab
docker ps --filter name=clawbot-pseudolab
```

## 4. cloudflared Tunnel (Pilot)

If OpenClaw runs in private/local Docker, Slack must reach your webhook URLs.

```bash
cloudflared tunnel login
cloudflared tunnel create clawbot-pilot
cloudflared tunnel route dns clawbot-pilot clawbot.<your-domain>
cloudflared tunnel run clawbot-pilot
```

Then set Slack URLs to:

- `https://clawbot.<your-domain>/slack/command`
- `https://clawbot.<your-domain>/slack/interactive`

## 5. Pilot Checklist

Daily:

- Container up and restart count
- `/clawbot plan` volume and approve/reject ratio
- `OCW0901` and TTL-expired counts
- P95 Claude latency and blocked dry-run spikes

Weekly SLO:

- Uptime >= 99.0%
- Apply terminal failure rate < 2.0%
- Avg plan-to-apply latency < 3000ms
