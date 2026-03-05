#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOT_DIR="${ROOT_DIR}/infrastructure/bot"

if [[ ! -f "${BOT_DIR}/.env.tunnel" ]]; then
  echo "Missing ${BOT_DIR}/.env.tunnel" >&2
  echo "Copy .env.tunnel.example and set OPENCLAW_PUBLIC_BASE_URL" >&2
  exit 1
fi

if [[ -z "${SLACK_APP_CONFIG_TOKEN:-}" ]]; then
  echo "SLACK_APP_CONFIG_TOKEN is required" >&2
  echo "Example: SLACK_APP_CONFIG_TOKEN='xoxe.xoxp-...' ./infrastructure/bot/provision-slack-app.sh" >&2
  exit 1
fi

if ! grep -Eq '^OPENCLAW_PUBLIC_BASE_URL=https://.+$' "${BOT_DIR}/.env.tunnel"; then
  echo "OPENCLAW_PUBLIC_BASE_URL must be set to an https URL in ${BOT_DIR}/.env.tunnel" >&2
  exit 1
fi

set -a
source "${BOT_DIR}/.env.tunnel"
set +a

OPENCLAW_PUBLIC_BASE_URL="${OPENCLAW_PUBLIC_BASE_URL%/}"

OPENCLAW_PUBLIC_BASE_URL="${OPENCLAW_PUBLIC_BASE_URL}" \
SLACK_APP_CONFIG_TOKEN="${SLACK_APP_CONFIG_TOKEN}" \
"${BOT_DIR}/create-slack-app.sh"

cat <<EOF

Next step:
1) Open oauth_authorize_url from the output and install app.
2) Invite the bot to your target Slack channel.
3) Set SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_CHANNEL_ID in infrastructure/bot/.env.
EOF
