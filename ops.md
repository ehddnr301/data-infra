# 운영 가이드

> 기준일: 2026-02-18 | 상세 기술 레퍼런스: [`ops-reference.md`](ops-reference.md)

## 프로젝트 개요

GitHub Archive 데이터를 수집·가공하여 Cloudflare 인프라 위에서 제공하는 데이터 카탈로그 플랫폼.

```
gharchive.org → Python ETL (fetch/filter/transform) → R2(raw) + D1(14개 DL 테이블)
                                                        → Hono API → React 스키마 브라우저
```

현재 동작하는 것:
- GitHub ETL: 시간별 수집 → 14종 이벤트 타입별 DL 테이블 적재 → daily_stats 집계
- Airflow DAG: 매일 자동 수집/적재/정리 파이프라인
- Catalog API: 데이터셋/컬럼 메타데이터 조회
- Web UI: 데이터셋 검색/필터/상세 스키마 브라우저

---

## 1. 개발 환경 (로컬)

### 1-1. 처음 셋업

```bash
# TypeScript 패키지 (API, Web, shared-types)
pnpm install

# Python 패키지 (GitHub ETL)
uv sync
```

### 1-2. 전체 빌드·테스트 확인

```bash
# TypeScript 빌드 + 타입체크
pnpm build && pnpm check

# Python 린트 + 테스트
uv run ruff check domains/ && uv run ruff format --check domains/
uv run pytest domains/github/ingestion/tests/
```

**예상 결과**:
- `pnpm build`: 에러 없이 완료
- `pnpm check`: `tsc --noEmit` 에러 0건
- `ruff`: 린트/포매팅 위반 0건
- `pytest`: **220 passed, 7 skipped** (Airflow 6 + Slack 1 — 의존성 미설치로 정상 skip)

### 1-3. API 로컬 실행

```bash
# 로컬 D1 마이그레이션 적용 (최초 1회)
# ⚠️ 반드시 API의 wrangler.toml 기준으로 적용하세요.
#    로컬 D1는 wrangler.toml 위치 기준 .wrangler/state/ 에 저장되므로,
#    다른 config로 적용하면 API가 테이블을 찾지 못합니다.
npx wrangler d1 migrations apply pseudolab-main --local \
  --config apps/api/wrangler.toml

# API 서버 시작
pnpm --filter @pseudolab/api dev
```

**실행하면 볼 수 있는 것**:
```bash
# 헬스체크 — 200 OK + JSON
curl http://127.0.0.1:8787/api/health

# 데이터셋 목록 — pagination 객체 포함
curl "http://127.0.0.1:8787/api/catalog/datasets?page=1&pageSize=5"

# 도메인 필터 — github 도메인만 반환
curl "http://127.0.0.1:8787/api/catalog/datasets?domain=github"

# 없는 데이터셋 — 404 + application/problem+json
curl -i "http://127.0.0.1:8787/api/catalog/datasets/non-existent"
```

### 1-4. Web 로컬 실행

```bash
pnpm --filter @pseudolab/web dev
# → http://localhost:5173 에서 확인
```

**실행하면 볼 수 있는 것**:

| URL | 화면 |
|-----|------|
| `/` | 메인 페이지 |
| `/datasets` | 데이터셋 카드 목록, 검색란, 도메인 필터 버튼, 카드/테이블 뷰 토글 |
| `/datasets/:id` | 메타데이터 그리드 + 컬럼 테이블, 컬럼 클릭 시 사이드 패널 |

> API 서버가 꺼져 있으면 `ErrorCard` + 재시도 버튼이 표시됩니다.

### 1-5. ETL 로컬 실행

```bash
# 도움말 확인
uv run gharchive-etl --help

# 데이터 수집 (1시간분, 스모크 테스트)
uv run gharchive-etl fetch --date 2024-01-15 --start-hour 0 --end-hour 0 --no-json-log
```

**예상 결과**: `FETCH_SUMMARY` 로그가 출력되고 exit code `0`. 404 시간대는 경고만 남기고 진행.

```bash
# D1 업로드 dry-run (실제 전송 없이 검증만)
uv run gharchive-etl upload --date 2024-01-15 --input-dir /tmp/data \
  --target all --dry-run --config domains/github/ingestion/config.yaml --no-json-log
```

**예상 결과**: `DRY RUN` 표시와 함께 테이블별 적재 예정 건수 출력. auth/install 사전 검증은 수행.

### 1-6. Airflow 로컬 실행

```bash
cd domains/github/ingestion

# 환경변수 설정
cp .env.example .env
# .env 편집: CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, D1_DATABASE_ID 등

# Docker로 실행
docker compose up -d --build
```

**실행하면 볼 수 있는 것**:
- `http://localhost:8080` → Airflow UI
- `docker compose logs -f` → admin 비밀번호 포함 로그
- DAG `github_archive_daily`: 매일 UTC 02:00 자동 실행 (fetch → validate → upload_r2 + upload_d1 → cleanup)

```bash
# 수동 트리거
docker compose exec airflow airflow dags trigger github_archive_daily

# 종료
docker compose down
```

### 1-7. Cloudflare 인증 확인

```bash
pnpm wrangler whoami
```

Account ID가 운영 리소스와 일치하는지 확인.

---

## 2. 운영 환경 (프로덕션)

### 2-1. 운영 리소스

> 아래 ID는 스냅샷입니다. 최신값: `cd infra && terraform output`

| 리소스 | 이름 | ID |
|--------|------|----|
| R2 Bucket | `github-archive-raw` | — |
| D1 Database | `pseudolab-main` | `e7f4cab0-3293-4942-988f-38d9e97e14b2` |
| KV (prod) | `pseudolab-cache` | `9b50454f6eb6483cba84a41fbec19ce9` |
| KV (preview) | `pseudolab-cache-preview` | `397782aa9e304aa3bf3a741fbc55fd87` |

### 2-2. 배포 절차

**순서**: D1 마이그레이션 → API Worker 배포 → Web Pages 배포 (롤백은 역순)

#### 배포 전 체크리스트

```bash
pnpm install && pnpm build && pnpm check   # 빌드/타입 통과
pnpm test                                    # 테스트 통과
pnpm wrangler whoami                        # 인증 확인
cd infra && terraform output                # 바인딩 ID 일치 확인
```

#### D1 마이그레이션 (운영)

```bash
# ⚠️ 반드시 로컬 선검증 후 적용
npx wrangler d1 migrations apply pseudolab-main --remote \
  --config domains/catalog/storage/wrangler.toml
```

**조심할 점**:
- 로컬(`--local`)에서 먼저 검증 완료한 후 `--remote` 적용
- 운영 DB 백업/복구 계획 확보 후 진행
- `0005_drop_events_table.sql`은 데이터 이관 검증 완료 전까지 적용 금지
- 적용 후 `d1_migrations` 테이블에서 이력 확인 (현재: 0001~0004)

#### API Worker 배포

```bash
pnpm --filter @pseudolab/api build
npx wrangler deploy --config apps/api/wrangler.toml
```

**배포 후 확인**:
```bash
curl -i https://<your-worker>.workers.dev/api/health          # → 200
curl "https://<your-worker>.workers.dev/api/catalog/datasets"  # → JSON + pagination
```

#### Web Pages 배포

```bash
VITE_API_URL=https://<your-worker>.workers.dev \
  pnpm turbo build --filter=@pseudolab/web
npx wrangler pages deploy apps/web/dist --project-name=pseudolab-web
```

**조심할 점**:
- `VITE_API_URL`이 운영 Worker 주소와 일치해야 함
- `apps/web/public/_redirects`에 `/* /index.html 200` 규칙 유지 (SPA fallback)

### 2-3. ETL 운영 실행

```bash
# 실제 수집 + 적재
uv run gharchive-etl fetch --date 2024-01-15 --start-hour 0 --end-hour 23 --no-json-log
uv run gharchive-etl upload --date 2024-01-15 --input-dir /tmp/data \
  --target all --config domains/github/ingestion/config.yaml --no-json-log
```

**필수 환경변수**:

| 환경변수 | 용도 | 필요 시점 |
|----------|------|-----------|
| `CLOUDFLARE_ACCOUNT_ID` | D1 HTTP API 계정 ID | `--target d1` 또는 `all` |
| `CLOUDFLARE_API_TOKEN` | D1 HTTP API 인증 토큰 | `--target d1` 또는 `all` |
| `D1_DATABASE_ID` | D1 DB ID 오버라이드 | 선택 (config.yaml 우선) |

**조심할 점**:
- `--dry-run`으로 먼저 검증 후 실제 실행 권장
- 배치 크기 초과(700KB) 행은 자동 스킵 — 경고 로그 확인
- D1 API 429/5xx는 자동 재시도됨 (최대 3회, 지수 백오프)
- `INSERT OR IGNORE`로 멱등성 보장 — 재실행 안전

### 2-4. Airflow 운영

```bash
cd domains/github/ingestion

# 시작/종료
docker compose up -d
docker compose down

# 상태 확인
docker compose exec airflow airflow dags list

# 수동 실행 (특정 날짜)
docker compose exec airflow airflow dags trigger github_archive_daily --exec-date 2024-06-15
```

**필수 환경변수** (`.env` 파일):

| 환경변수 | 필수 |
|----------|------|
| `CLOUDFLARE_ACCOUNT_ID` | O |
| `CLOUDFLARE_API_TOKEN` | O |
| `D1_DATABASE_ID` | O |
| `R2_ACCESS_KEY_ID` | O |
| `R2_SECRET_ACCESS_KEY` | O |
| `SLACK_WEBHOOK_URL` | X (미설정 시 알림 스킵) |

**조심할 점**:
- DAG이 UI에 안 보이면 볼륨 마운트 확인: `docker compose exec airflow ls /opt/airflow/dags/`
- `ModuleNotFoundError: gharchive_etl` → `docker compose up -d --build` 재빌드
- cleanup Task는 `trigger_rule=all_success` — 업로드 실패 시 파일 보존됨 (재실행 가능)

### 2-5. 인프라 변경 (Terraform)

```bash
cd infra
terraform plan    # 변경 사항 미리보기
terraform apply   # 반영
terraform output  # 리소스 ID 확인
```

**조심할 점**:
- 적용 후 `apps/api/wrangler.toml`의 바인딩 값과 `terraform output` 일치 여부 반드시 확인
  - `d1_databases.database_id`, `kv_namespaces.id`, `r2_buckets.bucket_name`

---

## 3. 장애 대응 빠른 참조

| 증상 | 원인 | 해결 |
|------|------|------|
| API 502/503 | D1 바인딩 불일치 | `wrangler tail`로 로그 확인 → wrangler.toml vs terraform output 비교 |
| Web에서 API 호출 실패 | CORS / URL 불일치 | `VITE_API_URL` 확인 |
| Pages 라우팅 404 | SPA fallback 누락 | `apps/web/public/_redirects` 파일 확인 |
| ETL fetch 실패 | 네트워크/gharchive 이상 | `--no-json-log`로 재현, 시간대별 재실행 |
| ETL upload 실패 | API 토큰 만료/미설정 | 환경변수 확인, `--dry-run`으로 사전 검증 |
| D1 적재 이상 | 마이그레이션 미적용 | `d1_migrations` 이력 + 인덱스 확인 |
| Airflow DAG 안 보임 | 볼륨 마운트 불일치 | `docker compose exec airflow ls /opt/airflow/dags/` |
| Airflow `ModuleNotFoundError` | 이미지 빌드 누락 | `docker compose up -d --build` |
| Airflow D1 적재 실패 (401) | API 토큰 만료 | `.env`의 `CLOUDFLARE_API_TOKEN` 확인 |
| Airflow 컨테이너 재시작 | 포트 충돌/메모리 부족 | `docker compose logs -f`로 확인 |
| 빌드 실패 (tsc 에러) | 타입 불일치 | `pnpm check`로 재현, `shared-types` 빌드 선행 확인 |

---

## 4. 참고 문서

### 상세 기술 레퍼런스

- **[`ops-reference.md`](ops-reference.md)** — 모듈 상세 구성, D1 검증 쿼리, 롤백 절차, Airflow DAG 상세, 스키마 브라우저 UI 테스트 가이드

### 인프라/스키마

- `infra/README.md` — Terraform 상세
- `domains/catalog/storage/README.md` — D1 스키마 상세

### 완료 보고서

| 티켓 | 범위 |
|------|------|
| `[shared]001-모노레포-초기-설정` | 모노레포 구성 |
| `[shared]002-cloudflare-리소스-프로비저닝` | Terraform 인프라 |
| `[shared]003-공유-타입스크립트-타입-정의` | shared-types 패키지 |
| `[github-archive]004-python-etl-프로젝트-셋업` | ETL 프로젝트 골격 |
| `[github-archive]008-github-archive-데이터-수집` | ETL fetch 구현 |
| `[github-archive]009-이벤트-필터링-가공-로직` | filter + transformer |
| `[github-archive]010-wrangler-업로드-스크립트` | upload (R2 + D1) |
| `[github-archive]011-airflow-dag-작성` | Airflow DAG 자동화 |
| `[github-archive]040-이벤트-타입별-DL-테이블-전환` | events → 14개 DL 테이블 |
| `[catalog]005-D1-카탈로그-스키마-설계` | D1 스키마 |
| `[catalog]006-hono-api-보일러플레이트` | Hono API |
| `[catalog]007-react-vite-프로젝트-셋업` | Web 앱 |
| `[catalog]012-스키마-브라우저-UI` | 스키마 브라우저 |

> 보고서 경로: `ticket-system/ticket-done/`
