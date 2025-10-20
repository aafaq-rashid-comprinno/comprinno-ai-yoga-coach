module "cognito" {
  count  = var.create.cognito_user_pool ? 1 : 0
  source = "../modules/cognito"
  
  user_pool_name                  = local.cognito_user_pool_name
  password_policy_min_length      = var.cognito_conf.password_policy_min_length
  password_policy_require_upper   = var.cognito_conf.password_policy_require_upper
  password_policy_require_lower   = var.cognito_conf.password_policy_require_lower
  password_policy_require_numbers = var.cognito_conf.password_policy_require_numbers
  password_policy_require_symbols = var.cognito_conf.password_policy_require_symbols
  mfa_configuration               = var.cognito_conf.mfa_configuration
  
  tags = local.common_tags
}

module "ecr" {
  count  = var.create.ecr ? 1 : 0
  source = "../modules/ecr"
  
  repository_name         = local.ecr_repository_name
  image_tag_mutability    = var.ecr_conf.image_tag_mutability
  scan_on_push            = var.ecr_conf.scan_on_push
  encryption_type         = var.ecr_conf.encryption_type
  lifecycle_policy_enabled = var.ecr_conf.lifecycle_policy_enabled
  max_image_count         = var.ecr_conf.max_image_count
  
  tags = local.common_tags
}

module "s3_bucket" {
  count  = var.create.s3_bucket ? 1 : 0
  source = "../modules/s3_bucket"
  
  storage_bucket_name    = local.s3_storage_bucket_name
  versioning_enabled     = var.s3_conf.versioning_enabled
  lifecycle_enabled      = var.s3_conf.lifecycle_enabled
  
  tags = local.common_tags
}
