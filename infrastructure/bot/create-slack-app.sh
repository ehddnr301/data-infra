#!/usr/bin/env bash
set -euo pipefail

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_PATH="${MANIFEST_PATH:-${BOT_DIR}/slack-app-manifest.generated.json}"

if [[ -z "${OPENCLAW_PUBLIC_BASE_URL:-}" ]]; then
  cat >&2 <<'EOF'
ERROR: OPENCLAW_PUBLIC_BASE_URL is required.

Example:
  OPENCLAW_PUBLIC_BASE_URL="https://clawbot.example.com" ./infrastructure/bot/create-slack-app.sh
EOF
  exit 1
fi

BASE_URL="${OPENCLAW_PUBLIC_BASE_URL%/}"
OAUTH_REDIRECT_URL="${SLACK_OAUTH_REDIRECT_URL:-${BASE_URL}/health}"
APP_NAME="${SLACK_APP_NAME:-PseudoLab Clawbot}"
BOT_DISPLAY_NAME="${SLACK_BOT_DISPLAY_NAME:-clawbot}"
BOT_USERNAME="${SLACK_BOT_USERNAME:-clawbot}"
COMMAND_NAME="${SLACK_COMMAND_NAME:-/clawbot}"
COMMAND_DESCRIPTION="${SLACK_COMMAND_DESCRIPTION:-Generate and apply catalog enrichment plans}"
COMMAND_USAGE_HINT="${SLACK_COMMAND_USAGE_HINT:-plan \"seed text\"}"
APP_DESCRIPTION="${SLACK_APP_DESCRIPTION:-AI-powered catalog quality bot for PseudoLab}"

export BASE_URL APP_NAME APP_DESCRIPTION BOT_DISPLAY_NAME BOT_USERNAME
export COMMAND_NAME COMMAND_DESCRIPTION COMMAND_USAGE_HINT
export OAUTH_REDIRECT_URL

mkdir -p "$(dirname "${MANIFEST_PATH}")"

python - <<'PY' > "${MANIFEST_PATH}"
import json
import os

base_url = os.environ["BASE_URL"]
manifest = {
    "display_information": {
        "name": os.environ["APP_NAME"],
        "description": os.environ["APP_DESCRIPTION"],
        "background_color": "#1f2937",
    },
    "features": {
        "bot_user": {
            "display_name": os.environ["BOT_DISPLAY_NAME"],
            "always_online": True,
        },
        "slash_commands": [
            {
                "command": os.environ["COMMAND_NAME"],
                "url": f"{base_url}/slack/command",
                "description": os.environ["COMMAND_DESCRIPTION"],
                "usage_hint": os.environ["COMMAND_USAGE_HINT"],
                "should_escape": False,
            }
        ],
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "chat:write",
                "chat:write.public",
                "commands",
                "channels:history",
            ]
        },
        "redirect_urls": [
            os.environ["OAUTH_REDIRECT_URL"]
        ]
    },
    "settings": {
        "interactivity": {
            "is_enabled": True,
            "request_url": f"{base_url}/slack/interactive",
        },
        "org_deploy_enabled": False,
        "socket_mode_enabled": False,
        "token_rotation_enabled": False,
    },
}

print(json.dumps(manifest, ensure_ascii=False, indent=2))
PY

echo "Generated manifest: ${MANIFEST_PATH}"

if [[ -z "${SLACK_APP_CONFIG_TOKEN:-}" ]]; then
  cat <<EOF

No SLACK_APP_CONFIG_TOKEN provided, so only manifest generation was done.

Manual import:
1) Open https://api.slack.com/apps
2) Create New App -> From an app manifest
3) Target workspace -> paste ${MANIFEST_PATH}
4) Create app, then install to workspace

After install, copy these values into infrastructure/bot/.env:
- SLACK_BOT_TOKEN
- SLACK_SIGNING_SECRET
- SLACK_CHANNEL_ID
EOF
  exit 0
fi

export MANIFEST_PATH

manifest_json="$(python - <<'PY'
import json
import os
from pathlib import Path

manifest_path = Path(os.environ["MANIFEST_PATH"])
print(json.dumps(json.loads(manifest_path.read_text(encoding="utf-8")), ensure_ascii=False))
PY
)"

validate_payload=(
  --data-urlencode "manifest=${manifest_json}"
)

create_payload=(
  --data-urlencode "manifest=${manifest_json}"
)

if [[ -n "${SLACK_WORKSPACE_TEAM_ID:-}" ]]; then
  create_payload+=(--data-urlencode "team_id=${SLACK_WORKSPACE_TEAM_ID}")
fi

validate_response="$(
  curl -sS -X POST "https://slack.com/api/apps.manifest.validate" \
    -H "Authorization: Bearer ${SLACK_APP_CONFIG_TOKEN}" \
    "${validate_payload[@]}"
)"

export VALIDATE_RESPONSE="${validate_response}"

python - <<'PY'
import json
import os
import sys

data = json.loads(os.environ["VALIDATE_RESPONSE"])
if not data.get("ok"):
    print("Manifest validation failed:", file=sys.stderr)
    print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)
    sys.exit(1)
print("Manifest validation: ok")
PY

create_response="$(
  curl -sS -X POST "https://slack.com/api/apps.manifest.create" \
    -H "Authorization: Bearer ${SLACK_APP_CONFIG_TOKEN}" \
    "${create_payload[@]}"
)"

export CREATE_RESPONSE="${create_response}"

python - <<'PY'
import json
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
import sys

data = json.loads(os.environ["CREATE_RESPONSE"])
if not data.get("ok"):
    print("App creation failed:", file=sys.stderr)
    print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)
    sys.exit(1)

credentials = data.get("credentials", {})
oauth_url = data.get("oauth_authorize_url", "")

oauth_with_redirect = oauth_url
if oauth_url:
    parsed = urlparse(oauth_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["redirect_uri"] = os.environ["OAUTH_REDIRECT_URL"]
    oauth_with_redirect = urlunparse(parsed._replace(query=urlencode(query)))

print("Slack app created successfully")
print(f"- app_id: {data.get('app_id', '')}")
print(f"- client_id: {credentials.get('client_id', '')}")
print(f"- client_secret: {credentials.get('client_secret', '')}")
print(f"- signing_secret: {credentials.get('signing_secret', '')}")
print(f"- oauth_authorize_url: {data.get('oauth_authorize_url', '')}")
print(f"- oauth_authorize_url_with_redirect: {oauth_with_redirect}")
print(f"- configured_redirect_url: {os.environ['OAUTH_REDIRECT_URL']}")

print("\nNext steps:")
print("1) Open oauth_authorize_url and install app to workspace")
print("2) Invite bot to target channel and copy channel ID")
print("3) Fill infrastructure/bot/.env with SLACK_BOT_TOKEN / SLACK_SIGNING_SECRET / SLACK_CHANNEL_ID")
PY
