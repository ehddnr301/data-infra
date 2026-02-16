terraform {
  required_version = ">= 1.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

# Cloudflare provider v5 사용
# v4에서 마이그레이션하는 경우:
#   - v4: version = "~> 4.0" — resource/data 이름이 다를 수 있음
#   - v5 마이그레이션 가이드: https://github.com/cloudflare/terraform-provider-cloudflare/blob/main/MIGRATION.md
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}
