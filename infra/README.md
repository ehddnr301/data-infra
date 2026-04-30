# Cloudflare Infrastructure (Terraform)

Cloudflare 리소스(R2, D1, KV)를 Terraform으로 프로비저닝합니다.

## 사전 요구사항

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.0
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) (`npm install -g wrangler`)
- Cloudflare API Token (D1/R2/KV Edit 권한 필요)
- Cloudflare Account ID

### Account ID 확인 방법

```bash
# Wrangler CLI로 확인 (로그인 필요)
pnpm wrangler whoami

# 또는 로그인 후 계정 목록 확인
pnpm wrangler login
pnpm wrangler whoami
```

> 출력에서 `Account ID` 항목을 확인할 수 있습니다. 또는 [Cloudflare Dashboard](https://dash.cloudflare.com) → 좌측 사이드바 하단에서도 확인 가능합니다.

## 관리 리소스

| 리소스 | 이름 | 용도 |
|--------|------|------|
| R2 Bucket | `github-archive-raw` | GitHub Archive 원본 JSON 저장소 |
| R2 Bucket | `pseudolab-exp` | 실험팀 전용 원본/실험 데이터 저장소 |
| D1 Database | `pseudolab-main` | 처리된 이벤트 + 메타데이터 + 카탈로그 |
| D1 Database | `pseudolab-exp` | 실험팀 전용 D1 데이터베이스 |
| KV Namespace | `pseudolab-cache` | 캐시 레이어 (production) |
| KV Namespace | `pseudolab-cache-preview` | 캐시 레이어 (preview) |

## 사용법

### 1. 자격증명 설정

```bash
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars`에 실제 값을 입력합니다:

```hcl
cloudflare_api_token  = "실제-API-토큰"
cloudflare_account_id = "실제-Account-ID"
environment           = "dev"
```

> `terraform.tfvars`는 `.gitignore`에 의해 Git에서 제외됩니다.

### 2. 적용 (Apply)

```bash
# 초기화 (최초 1회 또는 provider 변경 시)
terraform init

# 변경사항 미리보기
terraform plan

# 실제 적용
terraform apply
```

apply 완료 후 출력되는 ID 값을 `apps/api/wrangler.toml`에 입력하세요:

```toml
[[d1_databases]]
database_id = "<출력된 d1_database_id>"

[[kv_namespaces]]
id = "<출력된 kv_namespace_id>"
preview_id = "<출력된 kv_namespace_preview_id>"

[[r2_buckets]]
bucket_name = "github-archive-raw"
```

실험팀 리소스는 아래 출력값으로 확인할 수 있습니다:

- `exp_r2_bucket_name`
- `exp_d1_database_id`
- `exp_d1_database_name`

### 2-1. 실험팀 전용 전달 패키지

실험팀에 운영 자격증명을 공유하지 말고, 별도 발급한 실험 전용 값만 전달합니다.

`CLOUDFLARE_API_TOKEN`은 실험팀용으로 별도 발급하되, D1 권한은 R2 버킷 키처럼 버킷 단위로 강제 스코프되지 않습니다. `pseudolab-exp` 데이터베이스 ID를 분리해 사용 대상을 구분하고, 운영 토큰과 반드시 분리해서 관리하세요.

1. Terraform 적용 후 `terraform output exp_d1_database_id`로 D1 ID를 확인합니다.
2. Cloudflare Dashboard에서 `pseudolab-exp` 전용 R2 키와 D1 토큰을 신규 발급합니다.
3. `experiment-team.env.example`를 복사해 실제 값을 채운 뒤 안전한 채널로만 전달합니다.

전달 허용 항목:

```dotenv
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...      # pseudolab-exp 전용 D1 토큰
D1_DATABASE_ID=...            # pseudolab-exp DB ID
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=pseudolab-exp
```

공유 금지 항목:

- Global API Key
- 운영용 API 토큰/키
- 운영 `.env` 원본

### 3. 철회 (Destroy)

실험 접근을 즉시 차단해야 하면 Terraform 삭제 전에 실험용 D1 토큰과 실험용 R2 키를 먼저 revoke 하세요.

```bash
# 삭제 대상 미리보기
terraform plan -destroy

# 전체 삭제
terraform destroy
```

> **주의**: D1, R2에 데이터가 있는 상태에서 destroy하면 데이터도 함께 삭제됩니다.

### 4. 부분 철회

```bash
# 실험팀 전용 리소스만 삭제
terraform destroy \
  -target=cloudflare_d1_database.exp_db \
  -target=cloudflare_r2_bucket.exp_bucket

# 특정 KV 리소스만 삭제
terraform destroy -target=cloudflare_workers_kv_namespace.pseudolab_cache_preview

# Terraform 관리에서만 제외 (Cloudflare에 리소스는 유지)
terraform state rm cloudflare_r2_bucket.github_archive_raw
```

## 파일 구조

```
infra/
├── main.tf                  # 기본 리소스 정의 (R2, D1, KV)
├── experiment.tf            # 실험팀 전용 리소스 정의 (R2, D1)
├── provider.tf              # Cloudflare provider 설정
├── variables.tf             # 입력 변수 정의
├── outputs.tf               # 출력 값 (wrangler.toml 바인딩용)
├── experiment-team.env.example # 실험팀 전달용 자격증명 템플릿
├── terraform.tfvars.example # 자격증명 템플릿
├── terraform.tfvars         # 실제 자격증명 (Git 제외)
├── terraform.tfstate        # 현재 상태 (Git 제외)
└── README.md
```

## 명령어 요약

| 작업 | 명령어 |
|------|--------|
| Account ID 확인 | `wrangler whoami` |
| 초기화 | `terraform init` |
| 미리보기 | `terraform plan` |
| 적용 | `terraform apply` |
| 전체 철회 | `terraform destroy` |
| 부분 철회 | `terraform destroy -target=<리소스>` |
| 관리 제외 | `terraform state rm <리소스>` |
| 현재 상태 확인 | `terraform show` |
| 출력 값 확인 | `terraform output` |
