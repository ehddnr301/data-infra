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
| D1 Database | `pseudolab-main` | 처리된 이벤트 + 메타데이터 + 카탈로그 |
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

### 3. 철회 (Destroy)

```bash
# 삭제 대상 미리보기
terraform plan -destroy

# 전체 삭제
terraform destroy
```

> **주의**: D1, R2에 데이터가 있는 상태에서 destroy하면 데이터도 함께 삭제됩니다.

### 4. 부분 철회

```bash
# 특정 리소스만 삭제
terraform destroy -target=cloudflare_workers_kv_namespace.pseudolab_cache_preview

# Terraform 관리에서만 제외 (Cloudflare에 리소스는 유지)
terraform state rm cloudflare_r2_bucket.github_archive_raw
```

## 파일 구조

```
infra/
├── main.tf                  # 리소스 정의 (R2, D1, KV)
├── provider.tf              # Cloudflare provider 설정
├── variables.tf             # 입력 변수 정의
├── outputs.tf               # 출력 값 (wrangler.toml 바인딩용)
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
