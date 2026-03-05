#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOT_DIR="${ROOT_DIR}/infrastructure/bot"

if [[ ! -f "${BOT_DIR}/.env" ]]; then
  echo "Missing ${BOT_DIR}/.env" >&2
  exit 1
fi

if [[ ! -f "${BOT_DIR}/.env.tunnel" ]]; then
  echo "Missing ${BOT_DIR}/.env.tunnel" >&2
  echo "Copy .env.tunnel.example and set CLOUDFLARED_TUNNEL_TOKEN" >&2
  exit 1
fi

if ! grep -Eq '^CLOUDFLARED_TUNNEL_TOKEN=.+$' "${BOT_DIR}/.env.tunnel"; then
  echo "CLOUDFLARED_TUNNEL_TOKEN is not set in ${BOT_DIR}/.env.tunnel" >&2
  exit 1
fi

docker compose \
  -f "${BOT_DIR}/compose.yaml" \
  -f "${BOT_DIR}/compose.tunnel.yaml" \
  up -d

docker compose \
  -f "${BOT_DIR}/compose.yaml" \
  -f "${BOT_DIR}/compose.tunnel.yaml" \
  ps
