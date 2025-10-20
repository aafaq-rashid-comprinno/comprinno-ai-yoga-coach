variable "region" {
  description = "The AWS region where the resources will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "profile" {
  description = "AWS profile to use for authentication"
  type        = string
  default     = "default"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project" {
  description = "Project name for resource naming"
  type        = string
  default     = "promogen-ai"
}

variable "create" {
  description = "Flags to control the creation of resources"
  type = object({
    cognito_user_pool = bool
    s3_bucket         = bool
    ecr               = bool
    ecs               = bool
    vpc               = bool
    lambda_functions  = bool
  })
}

variable "cognito_conf" {
  description = "Configuration for Cognito User Pool"
}

variable "ecr_conf" {
  description = "Configuration for ECR repository"
}

variable "ecs_conf" {
  description = "Configuration for ECS cluster and service"
  type = object({
    cluster_name          = string
    task_family           = string
    task_cpu              = string
    task_memory           = string
    container_name        = string
    container_image       = string
    container_port        = number
    image_tag             = string
    service_name          = string
    desired_count         = number
    log_retention_days    = number
    environment_variables = map(string)
  })
}

variable "s3_conf" {
  description = "Configuration for S3 buckets"
}

variable "vpc_conf" {
  description = "Configuration for VPC"
}

variable "lambda_conf" {
  description = "Configuration for Lambda functions"
  type = object({
    runtime                = string
    timeout                = number
    memory_size            = number
    training_source_path   = string
    testing_source_path    = string
    s3_bucket              = string
    environment_variables  = map(string)
  })
}
