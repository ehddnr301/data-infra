resource "cloudflare_r2_bucket" "exp_bucket" {
  account_id = var.cloudflare_account_id
  name       = "pseudolab-exp"
}

resource "cloudflare_d1_database" "exp_db" {
  account_id = var.cloudflare_account_id
  name       = "pseudolab-exp"

  read_replication = {
    mode = "disabled"
  }
}
