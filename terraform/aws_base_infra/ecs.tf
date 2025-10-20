module "ecs" {
  count  = var.create.ecs ? 1 : 0
  source = "../modules/ecs"
  
  cluster_name   = local.ecs_cluster_name
  task_family    = local.ecs_task_family
  task_cpu       = var.ecs_conf.task_cpu
  task_memory    = var.ecs_conf.task_memory
  container_name = var.ecs_conf.container_name
  container_image = var.create.ecr ? "${module.ecr[0].repository_url}:${var.ecs_conf.image_tag}" : var.ecs_conf.container_image
  container_port = var.ecs_conf.container_port
  service_name   = local.ecs_service_name
  desired_count  = var.ecs_conf.desired_count
  
  subnet_ids        = var.create.vpc ? module.vpc[0].private_subnet_ids : data.aws_subnets.default.ids
  public_subnet_ids = var.create.vpc ? module.vpc[0].public_subnet_ids : data.aws_subnets.default.ids
  vpc_id            = var.create.vpc ? module.vpc[0].vpc_id : data.aws_vpc.default.id
  assign_public_ip  = false
  
  environment_variables = merge(
    var.ecs_conf.environment_variables,
    {
      COGNITO_USER_POOL_ID = var.create.cognito_user_pool ? module.cognito[0].user_pool_id : ""
      COGNITO_CLIENT_ID    = var.create.cognito_user_pool ? module.cognito[0].user_pool_client_id : ""
      S3_BUCKET           = var.create.s3_bucket ? module.s3_bucket[0].storage_bucket_name : ""
    }
  )
  
  region             = var.region
  log_retention_days = var.ecs_conf.log_retention_days
  
  tags = local.common_tags
  
  depends_on = [
    module.ecr,
    module.cognito,
    module.s3_bucket
  ]
}
