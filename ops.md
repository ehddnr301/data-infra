# Pseudolab Cloudflare 운영 인수인계 (ops.md)

## Summary

- 기준일: `2026-02-16`
- 현재 상태: 인프라(Terraform) + D1 스키마 + 공용 타입 + API/Hono 골격 + Web/React 골격까지 완료
- 운영 가능 범위:
  - API 기본 헬스체크/라우팅(`/api/health`, `/api/github/*`, `/api/catalog/*`)
  - Web 기본 라우팅/빌드/테스트(`apps/web`)
- 미구현 핵심:
  - GitHub ETL `fetch` 실동작
  - Catalog API의 실제 DB 조회/상세/컬럼 반환 로직
- 운영자가 먼저 할 일:
  1. `pnpm install && pnpm build && pnpm check`
  2. `pnpm --filter @pseudolab/api dev` 후 `/api/health` 확인
  3. `pnpm --filter @pseudolab/web dev` 후 `/`, `/datasets` 동작 확인
  4. 인프라 변경 시 `infra/`에서 `terraform plan/apply/output` 재검증

아래부터는 영역별 상세 운영 절차입니다.

## 1) 현재 상황 요약 (기준일: 2026-02-16)

현재 `ticket-system/ticket-done/` 기준으로 완료된 범위는 아래와 같습니다.

- 완료
  - 모노레포/워크스페이스 기본 구성 (`pnpm`, `turbo`, `uv`)
  - Cloudflare 리소스 Terraform 프로비저닝 (R2/D1/KV)
  - `apps/api/wrangler.toml` 바인딩 연결
  - D1 카탈로그 스키마/인덱스/시드 및 마이그레이션 체계
  - 공유 TypeScript 타입 패키지 (`@pseudolab/shared-types`) 확장
  - GitHub ingestion Python 프로젝트 골격 + 테스트
  - Hono API 보일러플레이트 (`/api/health`, `/api/github/*`, `/api/catalog/*`)
  - RFC 7807 에러 응답 규격 적용 (`ProblemDetail`)
  - React + Vite 웹앱 부트스트랩 (`apps/web`) + 기본 라우팅/레이아웃/테스트

- 아직 미구현(운영 주의)
  - `gharchive-etl fetch` 실동작 미구현 (`NotImplementedError`)
  - `downloader.py`, `r2.py`, `d1.py`는 인터페이스 골격만 존재
  - 카탈로그 API의 실제 DB 조회/상세/컬럼 반환 로직은 스텁 상태

즉, **인프라 + DB 스키마 + 타입 + ETL 골격까지 준비된 상태**이며,
**API/Web는 골격과 계약이 준비되었고, 실제 데이터 처리 로직은 후속 티켓에서 구현 필요**합니다.

---

## 2) 운영 대상 리소스

아래 ID 값은 **2026-02-16 기준 스냅샷**입니다.
최신값은 반드시 `infra/`에서 `terraform output`으로 재확인하세요.

- R2 Bucket: `github-archive-raw`
- D1 Database: `pseudolab-main`
  - DB ID: `e7f4cab0-3293-4942-988f-38d9e97e14b2`
- KV Namespace (prod): `pseudolab-cache`
  - ID: `9b50454f6eb6483cba84a41fbec19ce9`
- KV Namespace (preview): `pseudolab-cache-preview`
  - ID: `397782aa9e304aa3bf3a741fbc55fd87`

---

## 3) 신규 운영자 첫 점검 순서

모든 명령은 저장소 루트(`/home/dwlee/pseudolab-cloudflare`) 기준입니다.

### 3-1. 공통 개발환경/정적 점검

```bash
pnpm install
pnpm build
pnpm check
uv sync
uv run ruff check domains/
uv run ruff format --check domains/
uv run pytest
```

확인 포인트:
- `pnpm build`, `pnpm check`, `ruff`, `pytest`가 실패 없이 끝나는지 확인

### 3-2. Cloudflare 인증 확인

```bash
pnpm wrangler whoami
```

확인 포인트:
- 올바른 Account로 로그인되어 있는지
- Account ID가 인프라/운영 대상과 일치하는지

---

## 4) 인프라 운영 (Terraform)

작업 디렉터리: `infra/`

### 4-1. 최초/재초기화

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars에 cloudflare_api_token, cloudflare_account_id, environment 입력
terraform init
```

### 4-2. 변경 검토 및 반영

```bash
terraform plan
terraform apply
terraform output
terraform state list
```

확인 포인트:
- plan 결과가 의도한 변경인지
- `terraform output`에 D1/KV ID가 정상 출력되는지
- `terraform state list`에 4개 리소스가 존재하는지

### 4-3. API 바인딩 드리프트 점검

`apps/api/wrangler.toml`의 값이 Terraform output과 같은지 확인:
- `d1_databases.database_id`
- `kv_namespaces.id`
- `kv_namespaces.preview_id`
- `r2_buckets.bucket_name`

---

## 5) D1 스키마 운영 (카탈로그 도메인)

설정 파일: `domains/catalog/storage/wrangler.toml`

### 5-1. 로컬 마이그레이션 + 시드

```bash
npx wrangler d1 migrations apply pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml

npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --file domains/catalog/storage/seeds/0001_seed_catalog.sql
```

### 5-2. 리모트(운영) 마이그레이션 + 시드

운영 반영 전 체크:
- `pnpm wrangler whoami`로 대상 Account 재확인
- `npx wrangler d1 migrations apply pseudolab-main --local ...`로 로컬 선검증 완료
- 운영 DB 백업/Export 또는 복구 계획 확보
- 변경 승인(리뷰/체크리스트) 완료

```bash
npx wrangler d1 migrations apply pseudolab-main --remote \
  --config domains/catalog/storage/wrangler.toml

npx wrangler d1 execute pseudolab-main --remote \
  --config domains/catalog/storage/wrangler.toml \
  --file domains/catalog/storage/seeds/0001_seed_catalog.sql
```

운영 원칙:
- 스키마 변경: `migrations create/apply` 사용
- `d1 execute --file`: 시드/운영성 SQL에만 사용

### 5-3. 검증 쿼리

```bash
# 테이블 행 수
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "SELECT 'events' AS tbl, COUNT(*) AS cnt FROM events
             UNION ALL SELECT 'daily_stats', COUNT(*) FROM daily_stats
             UNION ALL SELECT 'catalog_datasets', COUNT(*) FROM catalog_datasets
             UNION ALL SELECT 'catalog_columns', COUNT(*) FROM catalog_columns;"

# 인덱스 확인
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name;"

# 마이그레이션 이력 확인
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "SELECT name FROM d1_migrations ORDER BY id;"
```

### 5-4. 마이그레이션 롤백 (되돌리기)

D1은 롤백 전용 명령이 없으므로 수동으로 DROP + 이력 삭제를 해야 합니다.
`--local`을 `--remote`로 바꾸면 운영 DB에 적용됩니다. **운영 DB는 데이터가 전부 삭제되므로 주의하세요.**

```bash
# 1) 인덱스 삭제 (0002 되돌리기)
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "
    DROP INDEX IF EXISTS idx_events_batch_date;
    DROP INDEX IF EXISTS idx_events_org_repo_created_at;
    DROP INDEX IF EXISTS idx_events_type_created_at;
    DROP INDEX IF EXISTS idx_events_org_created_at_partial;
    DROP INDEX IF EXISTS idx_daily_stats_org_repo_date;
    DROP INDEX IF EXISTS idx_daily_stats_date_event_type;
    DROP INDEX IF EXISTS idx_catalog_datasets_domain_updated_at;
    DROP INDEX IF EXISTS idx_catalog_datasets_name;
    DROP INDEX IF EXISTS idx_catalog_columns_pii_only;
  "

# 2) 테이블 삭제 (0001 되돌리기, FK 순서 주의)
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "
    DROP TABLE IF EXISTS catalog_columns;
    DROP TABLE IF EXISTS catalog_datasets;
    DROP TABLE IF EXISTS daily_stats;
    DROP TABLE IF EXISTS events;
  "

# 3) 마이그레이션 이력 삭제
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "DELETE FROM d1_migrations WHERE name IN ('0001_catalog_core.sql', '0002_catalog_indexes.sql');"
```

로컬 DB 완전 초기화 (로컬 전용 간편 방법):
- 반드시 `domains/catalog/storage/`에서 실행하세요.
- 저장소 루트에서 `.wrangler/state`를 지우지 마세요(다른 워커 로컬 상태까지 삭제될 수 있음).

```bash
cd domains/catalog/storage
rm -rf .wrangler/state
# 이후 migrations apply --local 부터 다시 시작
```

---

## 6) API/타입 패키지 운영 확인

### 6-1. shared-types 타입 체크

```bash
pnpm --filter @pseudolab/shared-types typecheck
pnpm --filter @pseudolab/shared-types lint
```

### 6-2. API 워커 빌드/로컬 실행

```bash
pnpm --filter @pseudolab/api build
pnpm --filter @pseudolab/api dev
pnpm --filter @pseudolab/api test
```

확인 포인트:
- `build` 성공 여부
- `wrangler dev` 구동 시 바인딩 관련 에러 유무
- 기본 헬스체크 경로 동작 여부 (`/api/health`, `/api/health/ready`)

---

### 6-3. API 빠른 확인 (로컬)

```bash
curl -i http://127.0.0.1:8787/api/health
curl -i "http://127.0.0.1:8787/api/catalog/datasets?page=1&pageSize=20"
```

확인 포인트:
- `200` 응답 + JSON 형식
- validation 실패 시 `application/problem+json` 반환

---

## 7) Web 앱 운영 확인 (`apps/web`)

### 7-1. 로컬 실행/검증

```bash
pnpm --filter @pseudolab/web dev
pnpm --filter @pseudolab/web lint
pnpm --filter @pseudolab/web build
pnpm --filter @pseudolab/web test
```

확인 포인트:
- `/`, `/datasets`, `/about` 라우팅 정상 동작
- `VITE_API_URL`이 API 워커 주소를 가리키는지 확인
- SPA fallback 파일 `apps/web/public/_redirects`가 유지되는지 확인

### 7-2. 환경변수

- 예시 파일: `apps/web/.env.example`
- 필수 키: `VITE_API_URL`
- 로컬 기본값: `http://localhost:8787`

### 7-3. 배포 메모 (Cloudflare Pages)

- Build command: `pnpm turbo build --filter=@pseudolab/web`
- Build output directory: `apps/web/dist`
- Pages 환경변수에 `VITE_API_URL` 설정 필요

---

## 8) GitHub ETL 운영 범위(현재)

작업 디렉터리: `domains/github/ingestion/`

### 8-1. 가능한 점검

```bash
uv sync
uv run pytest domains/github/ingestion/tests/
uv run ruff check domains/github/ingestion/
uv run ruff format --check domains/github/ingestion/
uv run gharchive-etl --help
uv run gharchive-etl --version
```

### 8-2. 현재 불가한 실행

아래 명령은 아직 구현되지 않아 실패가 정상입니다.

```bash
uv run gharchive-etl fetch --date 2024-01-15
```

실패 형태:
- `NotImplementedError` (후속 티켓에서 구현 예정)

---

## 9) 장애/이상 징후 점검 체크리스트

1. Terraform 변경 후 API가 실패할 때
- `cd infra && terraform output` 값과 `apps/api/wrangler.toml` 바인딩 값 일치 여부 확인

2. D1 조회/적재 이상 시
- `d1_migrations` 이력 확인
- 인덱스 누락 여부 확인 (`sqlite_master` 조회)
- 시드 재적용 시 `INSERT OR IGNORE`로 중복 안전한지 확인

3. ETL 실행 요청이 들어왔을 때
- 현재 `fetch` 미구현 상태임을 먼저 공유
- 후속 티켓 범위(다운로드/R2 업로드/D1 insert 구현)로 전환

---

## 10) 참고 문서

- 완료 보고서
  - `ticket-system/ticket-done/[shared]001-모노레포-초기-설정.md`
  - `ticket-system/ticket-done/[shared]002-cloudflare-리소스-프로비저닝.md`
  - `ticket-system/ticket-done/[shared]003-공유-타입스크립트-타입-정의.md`
  - `ticket-system/ticket-done/[github-archive]004-python-etl-프로젝트-셋업.md`
  - `ticket-system/ticket-done/[catalog]005-D1-카탈로그-스키마-설계.md`
  - `ticket-system/ticket-done/[catalog]006-hono-api-보일러플레이트.md`
  - `ticket-system/ticket-done/[catalog]007-react-vite-프로젝트-셋업.md`
- 운영 상세
  - `infra/README.md`
  - `domains/catalog/storage/README.md`
