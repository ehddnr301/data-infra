#!/usr/bin/env bash
# =============================================================================
# deploy.sh — pseudolab-cloudflare 원클릭 배포 스크립트
# ops.md 2-2절 배포 절차를 자동화합니다.
#
# 사용법:
#   ./deploy.sh              # 전체 배포 (D1 → API → Web) + 스모크
#   ./deploy.sh --skip-d1    # D1 마이그레이션 건너뛰기
#   ./deploy.sh --skip-web   # Web 배포 건너뛰기
#   ./deploy.sh --skip-api   # API 배포 건너뛰기
#   ./deploy.sh --skip-smoke # 배포 후 스모크 테스트 건너뛰기
#   ./deploy.sh --dry-run    # 실제 배포 없이 체크만
#   ./deploy.sh --help       # 도움말
# =============================================================================
set -euo pipefail

# ── 색상 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ── 프로젝트 루트 ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 플래그 파싱 ──
SKIP_D1=false
SKIP_API=false
SKIP_WEB=false
SKIP_SMOKE=false
SKIP_SEED=false
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --skip-d1)    SKIP_D1=true ;;
    --skip-api)   SKIP_API=true ;;
    --skip-web)   SKIP_WEB=true ;;
    --skip-smoke) SKIP_SMOKE=true ;;
    --skip-seed)  SKIP_SEED=true ;;
    --dry-run)    DRY_RUN=true ;;
    --help|-h)
      echo "사용법: ./deploy.sh [옵션]"
      echo ""
      echo "옵션:"
      echo "  --skip-d1    D1 마이그레이션 건너뛰기"
      echo "  --skip-api   API Worker 배포 건너뛰기"
      echo "  --skip-web   Web Pages 배포 건너뛰기"
      echo "  --skip-smoke 배포 후 스모크 테스트 건너뛰기"
      echo "  --skip-seed  marketplace seed 적용 건너뛰기"
      echo "  --dry-run    실제 배포 없이 체크만 실행"
      echo "  --help, -h   이 도움말 표시"
      exit 0
      ;;
    *)
      echo -e "${RED}알 수 없는 옵션: $arg${NC}"
      echo "사용법을 보려면: ./deploy.sh --help"
      exit 1
      ;;
  esac
done

# ── 유틸 함수 ──
step() {
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BOLD}${CYAN}▶ $1${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

ok()   { echo -e "  ${GREEN}✔ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠ $1${NC}"; }
fail() { echo -e "  ${RED}✖ $1${NC}"; exit 1; }
skip() { echo -e "  ${YELLOW}⏭ $1 (건너뜀)${NC}"; }

# ── 스모크 테스트 헬퍼 (실패해도 경고만, exit 안 함) ──
smoke_check() {
  local label="$1"
  local url="$2"
  local expected_status="${3:-200}"
  local status
  status=$(curl -sf -o /dev/null -w "%{http_code}" "$url" || echo "000")
  if [ "$status" = "$expected_status" ]; then
    ok "스모크 통과 [$label] HTTP $status"
  else
    warn "스모크 실패 [$label] 기대=${expected_status} 실제=${status}"
    warn "  URL: $url"
  fi
}

# ── ingestion .env 키-값 upsert ──
INGESTION_ENV="domains/github/ingestion/.env"

upsert_env_var() {
  local file="$1"
  local key="$2"
  local value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    if [ -s "$file" ]; then
      local last_byte
      last_byte=$(tail -c 1 "$file" 2>/dev/null | od -An -t x1 | tr -d '[:space:]')
      if [ -n "$last_byte" ] && [ "$last_byte" != "0a" ]; then
        printf '\n' >> "$file"
      fi
    fi
    echo "${key}=${value}" >> "$file"
  fi
}

# =============================================================================
# STEP 0: 배포 요약
# =============================================================================
step "배포 계획"
echo -e "  D1 마이그레이션: $([ "$SKIP_D1"    = true ] && echo "${YELLOW}건너뜀${NC}" || echo "${GREEN}실행${NC}")"
echo -e "  API Worker 배포: $([ "$SKIP_API"   = true ] && echo "${YELLOW}건너뜀${NC}" || echo "${GREEN}실행${NC}")"
echo -e "  Web Pages 배포:  $([ "$SKIP_WEB"   = true ] && echo "${YELLOW}건너뜀${NC}" || echo "${GREEN}실행${NC}")"
echo -e "  스모크 테스트:   $([ "$SKIP_SMOKE" = true ] && echo "${YELLOW}건너뜀${NC}" || echo "${GREEN}실행${NC}")"
echo -e "  marketplace seed:$([ "$SKIP_SEED"  = true ] && echo "${YELLOW}건너뜀${NC}" || echo "${GREEN}실행${NC}")"
echo -e "  모드:            $([ "$DRY_RUN"    = true ] && echo "${YELLOW}DRY RUN${NC}" || echo "${GREEN}LIVE${NC}")"

if [ "$DRY_RUN" = false ]; then
  echo ""
  echo -e "${YELLOW}5초 후 배포를 시작합니다. 취소하려면 Ctrl+C${NC}"
  sleep 5
fi

# =============================================================================
# STEP 1/6: 사전 체크 — 빌드, 타입체크, 테스트
# =============================================================================
step "STEP 1/6: 사전 체크"

echo -e "  ${CYAN}Web CSS 파이프라인 설정 점검 ...${NC}"
grep -q '"@tailwindcss/vite"' apps/web/package.json \
  || fail "apps/web/package.json에 @tailwindcss/vite가 없습니다"
grep -q 'tailwindcss()' apps/web/vite.config.ts \
  || fail "apps/web/vite.config.ts에 tailwindcss() 플러그인이 없습니다"
grep -q '@import "tailwindcss";' apps/web/src/index.css \
  || fail "apps/web/src/index.css에 @import \"tailwindcss\"; 선언이 없습니다"
ok "Web CSS 파이프라인 설정 점검 완료"

echo -e "  ${CYAN}pnpm install ...${NC}"
pnpm install --frozen-lockfile 2>&1 | tail -1
ok "패키지 설치 완료"

echo -e "  ${CYAN}pnpm build ...${NC}"
pnpm build
ok "빌드 성공"

echo -e "  ${CYAN}pnpm check (타입·린트) ...${NC}"
pnpm check
ok "타입·린트 체크 통과"

echo -e "  ${CYAN}pnpm test (유닛 테스트) ...${NC}"
pnpm test
ok "테스트 통과"

# =============================================================================
# STEP 2/6: Cloudflare 인증 확인
# =============================================================================
step "STEP 2/6: Cloudflare 인증 확인"

pnpm exec wrangler whoami
ok "인증 확인 완료"

if [ "$DRY_RUN" = true ]; then
  echo ""
  echo -e "${GREEN}${BOLD}✅ DRY RUN 완료 — 사전 체크 모두 통과${NC}"
  exit 0
fi

# =============================================================================
# STEP 3/6: Token 정합성 preflight
# =============================================================================
step "STEP 3/6: Token 정합성 preflight"

# ── 3-1. INTERNAL_API_TOKEN Worker secret ──
echo -e "  ${CYAN}INTERNAL_API_TOKEN Worker secret 확인 ...${NC}"
SECRET_LIST=$(pnpm exec wrangler secret list --config apps/api/wrangler.toml 2>&1 || true)
GENERATED_TOKEN=""
if echo "$SECRET_LIST" | grep -q "INTERNAL_API_TOKEN"; then
  ok "INTERNAL_API_TOKEN Worker secret 확인됨"
else
  warn "INTERNAL_API_TOKEN 미설정 — 신규 토큰 생성 및 등록 중 ..."
  GENERATED_TOKEN=$(openssl rand -hex 32)
  printf '%s' "$GENERATED_TOKEN" | pnpm exec wrangler secret put INTERNAL_API_TOKEN \
    --config apps/api/wrangler.toml
  ok "INTERNAL_API_TOKEN Worker secret 등록 완료"
fi

# ── 3-2. ingestion .env 파일 생성/동기화 ──
echo -e "  ${CYAN}ingestion .env 파일 확인 ...${NC}"
if [ ! -f "$INGESTION_ENV" ]; then
  cp "domains/github/ingestion/.env.example" "$INGESTION_ENV"
  ok ".env 파일 생성 (from .env.example)"
fi

# CATALOG_API_TOKEN — 신규 토큰이 생성된 경우 자동 동기화
if [ -n "$GENERATED_TOKEN" ]; then
  upsert_env_var "$INGESTION_ENV" "CATALOG_API_TOKEN" "$GENERATED_TOKEN"
  ok "CATALOG_API_TOKEN .env 동기화 완료 (INTERNAL_API_TOKEN과 동일 값)"
else
  EXISTING_CATALOG_TOKEN=$(grep "^CATALOG_API_TOKEN=" "$INGESTION_ENV" | cut -d'=' -f2- || true)
  if [ -z "$EXISTING_CATALOG_TOKEN" ]; then
    warn "CATALOG_API_TOKEN이 $INGESTION_ENV 에 비어 있습니다."
    warn "INTERNAL_API_TOKEN과 동일한 값으로 수동 설정하세요:"
    warn "  echo 'CATALOG_API_TOKEN=<token>' >> $INGESTION_ENV"
  else
    ok "CATALOG_API_TOKEN .env 확인됨"
  fi
fi

# CATALOG_API_BASE_URL — 로컬값이거나 비어 있으면 API 배포 후 자동 갱신 예약
EXISTING_CATALOG_URL=$(grep "^CATALOG_API_BASE_URL=" "$INGESTION_ENV" | cut -d'=' -f2- | tr -d '[:space:]' || true)
if [ -z "$EXISTING_CATALOG_URL" ] || [ "$EXISTING_CATALOG_URL" = "http://127.0.0.1:8787/api" ]; then
  warn "CATALOG_API_BASE_URL이 로컬값이거나 비어 있음 — API 배포 후 자동 갱신 예정"
  UPDATE_CATALOG_URL=true
else
  ok "CATALOG_API_BASE_URL 확인됨: $EXISTING_CATALOG_URL"
  UPDATE_CATALOG_URL=false
fi

# =============================================================================
# STEP 4/6: D1 마이그레이션 (운영)
# =============================================================================
step "STEP 4/6: D1 마이그레이션"

if [ "$SKIP_D1" = true ]; then
  skip "D1 마이그레이션"
else
  echo -e "  ${CYAN}로컬 D1 선검증 ...${NC}"
  pnpm exec wrangler d1 migrations apply pseudolab-main --local \
    --config apps/api/wrangler.toml
  ok "로컬 D1 마이그레이션 검증 완료"

  echo -e "  ${CYAN}운영 D1 마이그레이션 적용 ...${NC}"
  pnpm exec wrangler d1 migrations apply pseudolab-main --remote \
    --config domains/catalog/storage/wrangler.toml
  ok "운영 D1 마이그레이션 완료"

  if [ "$SKIP_SEED" = true ]; then
    skip "marketplace seed 적용"
  else
    echo -e "  ${CYAN}marketplace seed 적용 ...${NC}"
    pnpm exec wrangler d1 execute pseudolab-main --remote \
      --config domains/catalog/storage/wrangler.toml \
      --file domains/catalog/storage/seeds/0004_seed_marketplace_listings.sql
    ok "marketplace seed 적용 완료"
  fi
fi

# =============================================================================
# STEP 5/6: API Worker 배포
# =============================================================================
step "STEP 5/6: API Worker 배포"

API_URL=""

if [ "$SKIP_API" = true ]; then
  skip "API Worker 배포"
else
  echo -e "  ${CYAN}API 빌드 ...${NC}"
  pnpm --filter @pseudolab/api build
  ok "API 빌드 완료"

  echo -e "  ${CYAN}API Worker 배포 ...${NC}"
  DEPLOY_OUTPUT=$(pnpm exec wrangler deploy --config apps/api/wrangler.toml 2>&1)
  echo "$DEPLOY_OUTPUT"

  # 배포 출력에서 URL 추출
  API_URL=$(echo "$DEPLOY_OUTPUT" | grep -oP 'https://[a-zA-Z0-9._-]+\.workers\.dev' | head -1 || true)

  if [ -n "$API_URL" ]; then
    ok "API 배포 완료: $API_URL"
  else
    warn "API URL 자동 추출 실패 — 위 출력에서 URL을 확인하세요"
    echo -n "  API URL을 입력하세요 (예: https://pseudolab-api.xxx.workers.dev): "
    read -r API_URL
  fi

  # CATALOG_API_BASE_URL 자동 갱신 / drift 감지
  if [ -n "$API_URL" ]; then
    EXPECTED_URL="${API_URL}/api"
    CURRENT_CATALOG_URL=$(grep "^CATALOG_API_BASE_URL=" "$INGESTION_ENV" | cut -d'=' -f2- | tr -d '[:space:]' || true)
    if [ "${UPDATE_CATALOG_URL}" = true ] || [ "$CURRENT_CATALOG_URL" != "$EXPECTED_URL" ]; then
      if [ "$CURRENT_CATALOG_URL" != "$EXPECTED_URL" ] && [ "${UPDATE_CATALOG_URL}" = false ]; then
        warn "CATALOG_API_BASE_URL 드리프트 감지!"
        warn "  현재: $CURRENT_CATALOG_URL"
        warn "  배포됨: $EXPECTED_URL"
      fi
      upsert_env_var "$INGESTION_ENV" "CATALOG_API_BASE_URL" "$EXPECTED_URL"
      ok "CATALOG_API_BASE_URL → $EXPECTED_URL 갱신 완료"
    else
      ok "CATALOG_API_BASE_URL 일치 확인됨"
    fi
  fi

  # 헬스체크
  echo -e "  ${CYAN}API 헬스체크 ...${NC}"
  sleep 3  # 배포 반영 대기

  HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$API_URL/api/health" || echo "000")
  if [ "$HTTP_STATUS" = "200" ]; then
    ok "API 헬스체크 통과 (HTTP $HTTP_STATUS)"
  else
    fail "API 헬스체크 실패 (HTTP $HTTP_STATUS) — 롤백을 고려하세요"
  fi
fi

# =============================================================================
# STEP 6/6: Web Pages 배포
# =============================================================================
step "STEP 6/6: Web Pages 배포"

WEB_URL=""

if [ "$SKIP_WEB" = true ]; then
  skip "Web Pages 배포"
else
  # Pages 프로젝트 존재 확인
  echo -e "  ${CYAN}Pages 프로젝트 확인 ...${NC}"
  if ! pnpm exec wrangler pages project list 2>&1 | grep -q "pseudolab-web"; then
    warn "Pages 프로젝트 없음 — 생성 중 ..."
    pnpm exec wrangler pages project create pseudolab-web --production-branch main
    ok "Pages 프로젝트 생성 완료"
  else
    ok "Pages 프로젝트 확인됨"
  fi

  # API URL 결정
  if [ -z "${API_URL:-}" ]; then
    echo -e "  ${CYAN}기존 API Worker URL 조회 ...${NC}"
    DEPLOY_STATUS=$(pnpm exec wrangler deployments list --config apps/api/wrangler.toml 2>&1 || true)
    API_URL=$(echo "$DEPLOY_STATUS" | grep -oP 'https://[a-zA-Z0-9._-]+\.workers\.dev' | head -1 || true)

    if [ -z "$API_URL" ]; then
      echo -n "  API URL을 입력하세요 (예: https://pseudolab-api.xxx.workers.dev): "
      read -r API_URL
    fi
  fi

  echo -e "  ${CYAN}VITE_API_URL=${API_URL}${NC}"

  # Web 빌드
  echo -e "  ${CYAN}Web 빌드 ...${NC}"
  VITE_API_URL="$API_URL" pnpm turbo build --filter=@pseudolab/web
  ok "Web 빌드 완료"

  echo -e "  ${CYAN}Web CSS 산출물 검증 ...${NC}"
  shopt -s nullglob
  WEB_CSS_FILES=(apps/web/dist/assets/index-*.css)
  shopt -u nullglob

  if [ ${#WEB_CSS_FILES[@]} -eq 0 ]; then
    fail "Web CSS 파일을 찾지 못했습니다 (apps/web/dist/assets/index-*.css)"
  fi

  WEB_CSS_FILE="${WEB_CSS_FILES[0]}"
  grep -q 'tailwindcss v4' "$WEB_CSS_FILE" || fail "빌드 CSS에서 Tailwind v4 헤더를 찾지 못했습니다"
  grep -q '\.max-w-6xl' "$WEB_CSS_FILE" || fail "빌드 CSS에 .max-w-6xl 유틸리티가 없습니다"
  grep -q '\.min-h-screen' "$WEB_CSS_FILE" || fail "빌드 CSS에 .min-h-screen 유틸리티가 없습니다"
  grep -q '\.bg-white' "$WEB_CSS_FILE" || fail "빌드 CSS에 .bg-white 유틸리티가 없습니다"
  grep -q '\.border-b' "$WEB_CSS_FILE" || fail "빌드 CSS에 .border-b 유틸리티가 없습니다"
  ok "Web CSS 산출물 검증 완료: $WEB_CSS_FILE"

  # Pages 배포
  echo -e "  ${CYAN}Web Pages 배포 ...${NC}"
  PAGES_OUTPUT=$(pnpm exec wrangler pages deploy apps/web/dist --project-name=pseudolab-web 2>&1)
  echo "$PAGES_OUTPUT"
  WEB_URL=$(echo "$PAGES_OUTPUT" | grep -oP 'https://[a-zA-Z0-9._-]+\.pages\.dev' | head -1 || true)
  ok "Web Pages 배포 완료${WEB_URL:+: $WEB_URL}"

  # 배포된 URL 조회
  echo -e "  ${CYAN}최신 배포 URL 확인 ...${NC}"
  pnpm exec wrangler pages deployment list --project-name pseudolab-web | head -5
fi

# =============================================================================
# 배포 후 스모크 테스트
# =============================================================================
if [ "$SKIP_SMOKE" = true ]; then
  skip "배포 후 스모크 테스트"
elif [ -z "${API_URL:-}" ]; then
  warn "API_URL을 알 수 없어 스모크 테스트를 건너뜁니다"
else
  step "배포 후 스모크 테스트"

  echo -e "  ${CYAN}3초 대기 (CDN 전파) ...${NC}"
  sleep 3

  smoke_check "API health"                  "$API_URL/api/health"                                              "200"
  smoke_check "discord 데이터셋 목록"        "$API_URL/api/catalog/datasets?domain=discord&page=1&pageSize=20" "200"
  smoke_check "marketplace listings"         "$API_URL/api/marketplace/listings"                                "200"
  smoke_check "marketplace domains"          "$API_URL/api/marketplace/domains"                                 "200"
  smoke_check "discord listing detail"       "$API_URL/api/marketplace/listings/discord/messages.v1"           "200"
  smoke_check "github domain hub"            "$API_URL/api/marketplace/domains/github"                          "200"
  smoke_check "github.watch-events.v1 상세" "$API_URL/api/catalog/datasets/github.watch-events.v1"            "200"
  smoke_check "존재하지 않는 데이터셋 (404)" "$API_URL/api/catalog/datasets/__smoke_nonexistent__"             "404"

  ok "스모크 테스트 완료"
fi

# =============================================================================
# 완료
# =============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}🎉 배포 완료!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
[ -n "${API_URL:-}" ] && echo -e "  API: ${BOLD}${API_URL}/api/health${NC}"
[ -n "${WEB_URL:-}" ] && echo -e "  Web: ${BOLD}${WEB_URL}${NC}"
echo ""
