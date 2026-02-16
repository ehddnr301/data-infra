variable "cloudflare_api_token" {
  description = "Cloudflare API token (D1/R2/KV Edit 권한 필요)"
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID"
  type        = string
}

variable "environment" {
  description = "배포 환경 (dev, staging, production)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment는 dev, staging, production 중 하나여야 합니다."
  }
}
