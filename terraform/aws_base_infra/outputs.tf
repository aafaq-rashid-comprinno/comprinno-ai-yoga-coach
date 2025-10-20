# Cognito Outputs
output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = var.create.cognito_user_pool ? module.cognito[0].user_pool_id : null
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito User Pool Client"
  value       = var.create.cognito_user_pool ? module.cognito[0].user_pool_client_id : null
}

output "cognito_jwks_url" {
  description = "Cognito JWKS URL"
  value       = var.create.cognito_user_pool ? "https://cognito-idp.${var.region}.amazonaws.com/${module.cognito[0].user_pool_id}/.well-known/jwks.json" : null
}

# ECR Outputs
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = var.create.ecr ? module.ecr[0].repository_url : null
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = var.create.ecr ? module.ecr[0].repository_name : null
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = var.create.ecs ? module.ecs[0].cluster_name : null
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = var.create.ecs ? module.ecs[0].service_name : null
}

output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = var.create.ecs ? module.ecs[0].task_definition_arn : null
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = var.create.ecs ? module.ecs[0].alb_dns_name : null
}

# S3 Outputs
output "s3_storage_bucket_name" {
  description = "Name of the S3 storage bucket"
  value       = var.create.s3_bucket ? module.s3_bucket[0].storage_bucket_name : null
}

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = var.create.vpc ? module.vpc[0].vpc_id : null
}

output "s3_endpoint_id" {
  description = "ID of the S3 VPC endpoint"
  value       = var.create.vpc ? module.vpc[0].s3_endpoint_id : null
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = var.create.vpc ? module.vpc[0].private_subnet_ids : null
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = var.create.vpc ? module.vpc[0].database_subnet_ids : null
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = var.create.vpc ? module.vpc[0].public_subnet_ids : null
}
