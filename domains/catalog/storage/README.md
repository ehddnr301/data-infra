# Catalog Storage (D1 스키마)

GitHub Archive Data Platform의 카탈로그 도메인 D1 데이터베이스 스키마 및 마이그레이션 관리 디렉토리.

## 디렉토리 구조

```
domains/catalog/storage/
├── wrangler.toml              # D1 바인딩 설정
├── migrations/
│   ├── 0001_catalog_core.sql  # 코어 테이블 생성 (DDL)
│   └── 0002_catalog_indexes.sql # 쿼리 성능 인덱스
├── seeds/
│   └── 0001_seed_catalog.sql  # 테스트용 샘플 데이터
└── README.md
```

## 테이블 구조

| 테이블 | 설명 |
|--------|------|
| `events` | GitHub Archive 정규화 이벤트. `id`를 멱등성 키로 사용하며 `payload`는 JSON TEXT로 저장 |
| `daily_stats` | 일별/조직/리포/이벤트타입 기준 집계 테이블. `(date, org_name, repo_name, event_type)` 복합 유니크 |
| `catalog_datasets` | 데이터셋 메타데이터. JSON-LD 스키마, 용어집, 리니지 정보 포함 |
| `catalog_columns` | 컬럼 수준 메타데이터. 데이터 타입, 설명, PII 플래그, 예시값 관리 |

## 운영 정책

- **스키마 변경은 반드시 `wrangler d1 migrations create` + `migrations apply`를 사용**합니다.
- `wrangler d1 execute --file`은 시드 데이터 삽입 등 비-마이그레이션 작업에만 사용합니다.
- 마이그레이션 이력은 `d1_migrations` 테이블에서 자동 추적됩니다.

## 마이그레이션 적용

### 로컬 (개발용)

```bash
# 테이블 생성
npx wrangler d1 migrations apply pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml

# 시드 데이터 삽입
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --file domains/catalog/storage/seeds/0001_seed_catalog.sql
```

### 리모트 (프로덕션)

```bash
# 테이블 생성
npx wrangler d1 migrations apply pseudolab-main --remote \
  --config domains/catalog/storage/wrangler.toml

# 시드 데이터 삽입
npx wrangler d1 execute pseudolab-main --remote \
  --config domains/catalog/storage/wrangler.toml \
  --file domains/catalog/storage/seeds/0001_seed_catalog.sql
```

## 검증 쿼리

```bash
# 테이블별 행 수 확인
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "SELECT 'events' AS tbl, COUNT(*) AS cnt FROM events
             UNION ALL SELECT 'daily_stats', COUNT(*) FROM daily_stats
             UNION ALL SELECT 'catalog_datasets', COUNT(*) FROM catalog_datasets
             UNION ALL SELECT 'catalog_columns', COUNT(*) FROM catalog_columns;"

# 인덱스 목록 확인
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name;"

# 마이그레이션 이력 확인
npx wrangler d1 execute pseudolab-main --local \
  --config domains/catalog/storage/wrangler.toml \
  --command "SELECT name FROM d1_migrations ORDER BY id;"
```

## D1 Free Tier 한도

| 항목 | 한도 |
|------|------|
| 저장 용량 | 5 GB |
| 읽기 행 수 | 5M rows/day |
| 쓰기 행 수 | 100K rows/day |
| 데이터베이스 수 | 50개 |

> 현재 프로젝트 예상치: ~30K rows/year 이벤트 기준으로 Free Tier 내 충분히 운영 가능.
