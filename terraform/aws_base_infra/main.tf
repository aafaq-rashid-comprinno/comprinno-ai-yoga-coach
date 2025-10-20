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

module "vpc" {
  count  = var.create.vpc ? 1 : 0
  source = "../modules/vpc"
  
  vpc_name                 = local.vpc_name
  vpc_cidr                 = var.vpc_conf.vpc_cidr
  availability_zones       = var.vpc_conf.availability_zones
  public_subnet_cidrs      = var.vpc_conf.public_subnet_cidrs
  private_subnet_cidrs     = var.vpc_conf.private_subnet_cidrs
  database_subnet_cidrs    = var.vpc_conf.database_subnet_cidrs
  enable_nat_gateway       = var.vpc_conf.enable_nat_gateway
  
  tags = local.common_tags
}

module "ecs" {
  count  = var.create.ecs ? 1 : 0
  source = "../modules/ecs"
  
  cluster_name          = local.ecs_cluster_name
  task_family           = local.ecs_task_family
  task_cpu              = var.ecs_conf.task_cpu
  task_memory           = var.ecs_conf.task_memory
  container_name        = var.ecs_conf.container_name
  container_image       = var.ecs_conf.container_image
  container_port        = var.ecs_conf.container_port
  image_tag             = var.ecs_conf.image_tag
  service_name          = local.ecs_service_name
  desired_count         = var.ecs_conf.desired_count
  log_retention_days    = var.ecs_conf.log_retention_days
  environment_variables = var.ecs_conf.environment_variables
  
  vpc_id            = var.create.vpc ? module.vpc[0].vpc_id : data.aws_vpc.default[0].id
  public_subnet_ids = var.create.vpc ? module.vpc[0].public_subnet_ids : data.aws_subnets.default[0].ids
  
  tags = local.common_tags
  
  depends_on = [module.vpc]
}

# Training Lambda Function
module "training_lambda" {
  count  = var.create.lambda_functions ? 1 : 0
  source = "../modules/lambda"
  
  function_name    = local.training_lambda_name
  handler          = "training_lambda_function.lambda_handler"
  source_path      = var.lambda_conf.training_source_path
  runtime          = var.lambda_conf.runtime
  timeout          = var.lambda_conf.timeout
  memory_size      = var.lambda_conf.memory_size
  s3_bucket        = var.create.s3_bucket ? module.s3_bucket[0].storage_bucket_name : var.lambda_conf.s3_bucket
  s3_trigger_prefix = "*/training/"
  s3_trigger_suffix = ".mp4"
  
  environment_variables = merge(var.lambda_conf.environment_variables, {
    BUCKET_NAME = var.create.s3_bucket ? module.s3_bucket[0].storage_bucket_name : var.lambda_conf.s3_bucket
  })
  
  vpc_config = var.create.vpc ? {
    subnet_ids = module.vpc[0].private_subnet_ids
  } : null
  
  vpc_id = var.create.vpc ? module.vpc[0].vpc_id : null
  
  tags = local.common_tags
  
  depends_on = [module.s3_bucket, module.vpc]
}

# Testing Lambda Function
module "testing_lambda" {
  count  = var.create.lambda_functions ? 1 : 0
  source = "../modules/lambda"
  
  function_name    = local.testing_lambda_name
  handler          = "testing_lambda_function.lambda_handler"
  source_path      = var.lambda_conf.testing_source_path
  runtime          = var.lambda_conf.runtime
  timeout          = var.lambda_conf.timeout
  memory_size      = var.lambda_conf.memory_size
  s3_bucket        = var.create.s3_bucket ? module.s3_bucket[0].storage_bucket_name : var.lambda_conf.s3_bucket
  s3_trigger_prefix = "*/testing/"
  s3_trigger_suffix = ".mp4"
  
  environment_variables = merge(var.lambda_conf.environment_variables, {
    BUCKET_NAME = var.create.s3_bucket ? module.s3_bucket[0].storage_bucket_name : var.lambda_conf.s3_bucket
  })
  
  vpc_config = var.create.vpc ? {
    subnet_ids = module.vpc[0].private_subnet_ids
  } : null
  
  vpc_id = var.create.vpc ? module.vpc[0].vpc_id : null
  
  tags = local.common_tags
  
  depends_on = [module.s3_bucket, module.vpc]
}

# Data sources for default VPC (when not creating custom VPC)
data "aws_vpc" "default" {
  count   = var.create.ecs && !var.create.vpc ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = var.create.ecs && !var.create.vpc ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}
