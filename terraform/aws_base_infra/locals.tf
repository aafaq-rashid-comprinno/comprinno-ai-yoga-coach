locals {
  # Common naming convention
  name_prefix = "${var.project}-${var.environment}"
  
  # Resource names
  cognito_user_pool_name = "${local.name_prefix}-${var.cognito_conf.user_pool_name}"
  ecr_repository_name    = "${local.name_prefix}-${var.ecr_conf.repository_name}"
  ecs_cluster_name       = "promogen-${var.environment}-cluster"
  ecs_task_family        = "promogen-${var.environment}-task"
  ecs_service_name       = "promogen-${var.environment}-service"
  
  # S3 bucket names (must be globally unique)
  s3_storage_bucket_name = "${var.s3_conf.bucket_name}-${random_string.bucket_suffix.result}"
  
  # Common tags
  common_tags = {
    Environment = var.environment
    Project     = var.project
    ManagedBy   = "terraform"
  }
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}
