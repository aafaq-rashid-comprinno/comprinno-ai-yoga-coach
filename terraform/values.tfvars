region      = "us-east-1"
environment = "dev"
project     = "promogen-ai"

cognito_conf = {
  user_pool_name                  = "promogen-ai-users"
  password_policy_min_length      = 8
  password_policy_require_upper   = true
  password_policy_require_lower   = true
  password_policy_require_numbers = true
  password_policy_require_symbols = false
  mfa_configuration               = "OFF"
}

ecr_conf = {
  repository_name         = "promogen-ai-flask-app"
  image_tag_mutability    = "MUTABLE"
  scan_on_push            = true
  encryption_type         = "AES256"
  lifecycle_policy_enabled = true
  max_image_count         = 10
}

ecs_conf = {
  cluster_name   = "promogen-ai"
  task_family    = "promogen-ai-flask-app"
  service_name   = "promogen-ai-service"
  task_cpu       = "1024"
  task_memory    = "3072"
  container_name = "promogen-ai-flask-app"
  container_image = ""
  image_tag      = "latest"
  container_port = 5000
  desired_count  = 1
  log_retention_days = 14
  environment_variables = {

    # AWS Configuration
    AWS_REGION = "us-east-1"

    # S3 and Lambda
    BUCKET_NAME = "yoga-eval-bucket"
    TRAINING_LAMBDA_ARN = "arn:aws:lambda:us-east-1:830251426724:function:yoga-training-lambda"
    TESTING_LAMBDA_ARN = "arn:aws:lambda:us-east-1:830251426724:function:yoga-testing-lambda"

    # AgentCore
    USE_AGENTCORE = "true"
    AGENTCORE_ARN = "arn:aws:bedrock-agentcore:us-east-1:830251426724:runtime/yoga_coach-tiHwXqEf7V"

    # Cognito Authentication
    COGNITO_CLIENT_ID = "3dhp1d4utt1rt2btd4e25b03ls"
    COGNITO_USER_POOL_ID = "us-east-1_fRyUPTqUA"
    COGNITO_REGION = "us-east-1"
    COGNITO_JWKS_URL_TEMPLATE = "https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"

    # Server Configuration
    SERVER_PORT = "5000"

  }
}

s3_conf = {
  bucket_name        = "yoga-eval-bucket"
  versioning_enabled = true
  lifecycle_enabled  = true
}

vpc_conf = {
  vpc_cidr                  = "10.0.0.0/16"
  availability_zones        = ["us-east-1a", "us-east-1b"]
  public_subnet_cidrs       = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs      = ["10.0.10.0/24", "10.0.20.0/24"]
  database_subnet_cidrs     = ["10.0.100.0/24", "10.0.200.0/24"]
  enable_nat_gateway        = true
}
