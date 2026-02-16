# =============================================================================
# R2 Bucket — GitHub Archive 원본 JSON 저장소
# =============================================================================
resource "cloudflare_r2_bucket" "github_archive_raw" {
  account_id = var.cloudflare_account_id
  name       = "github-archive-raw"
}

# =============================================================================
# D1 Database — 처리된 이벤트 + 메타데이터 + 카탈로그
# =============================================================================
resource "cloudflare_d1_database" "pseudolab_main" {
  account_id = var.cloudflare_account_id
  name       = "pseudolab-main"

  read_replication = {
    mode = "disabled"
  }
}

# =============================================================================
# KV Namespace — 캐시 레이어 (검색 결과, 인기 카탈로그 항목)
# =============================================================================
resource "cloudflare_workers_kv_namespace" "pseudolab_cache" {
  account_id = var.cloudflare_account_id
  title      = "pseudolab-cache"
}

resource "cloudflare_workers_kv_namespace" "pseudolab_cache_preview" {
  account_id = var.cloudflare_account_id
  title      = "pseudolab-cache-preview"
}
