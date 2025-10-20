data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

module "vpc" {
  count  = var.create.vpc ? 1 : 0
  source = "../modules/vpc"
  
  vpc_name = "${local.name_prefix}-vpc"
  vpc_cidr = var.vpc_conf.vpc_cidr
  
  availability_zones = var.vpc_conf.availability_zones
  
  public_subnet_cidrs   = var.vpc_conf.public_subnet_cidrs
  private_subnet_cidrs  = var.vpc_conf.private_subnet_cidrs
  database_subnet_cidrs = var.vpc_conf.database_subnet_cidrs
  
  enable_nat_gateway = var.vpc_conf.enable_nat_gateway
  
  tags = local.common_tags
}
