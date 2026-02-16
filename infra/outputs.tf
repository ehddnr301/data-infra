output "r2_bucket_name" {
  description = "R2 버킷 이름"
  value       = cloudflare_r2_bucket.github_archive_raw.name
}

output "d1_database_id" {
  description = "D1 데이터베이스 ID (wrangler.toml에 입력)"
  value       = cloudflare_d1_database.pseudolab_main.id
}

output "d1_database_name" {
  description = "D1 데이터베이스 이름"
  value       = cloudflare_d1_database.pseudolab_main.name
}

output "kv_namespace_id" {
  description = "KV 네임스페이스 ID — production (wrangler.toml에 입력)"
  value       = cloudflare_workers_kv_namespace.pseudolab_cache.id
}

output "kv_namespace_preview_id" {
  description = "KV 네임스페이스 ID — preview (wrangler.toml에 입력)"
  value       = cloudflare_workers_kv_namespace.pseudolab_cache_preview.id
}

output "wrangler_binding_summary" {
  description = "wrangler.toml 바인딩 설정 요약"
  value       = <<-EOT
    # apps/api/wrangler.toml에 아래 ID를 입력하세요:
    #
    # [[d1_databases]]
    # database_id = "${cloudflare_d1_database.pseudolab_main.id}"
    #
    # [[kv_namespaces]]
    # id = "${cloudflare_workers_kv_namespace.pseudolab_cache.id}"
    # preview_id = "${cloudflare_workers_kv_namespace.pseudolab_cache_preview.id}"
    #
    # [[r2_buckets]]
    # bucket_name = "${cloudflare_r2_bucket.github_archive_raw.name}"
  EOT
}
