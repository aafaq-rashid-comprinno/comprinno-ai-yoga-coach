# Promogen AI - Terraform Infrastructure

This repository contains Terraform configurations for deploying a complete serverless architecture for the Promogen AI video ad generation application using AWS ECS Fargate.

## Architecture Overview

The infrastructure deploys the following AWS services:

- **Amazon ECR** - Container registry for the Flask application
- **Amazon ECS Fargate** - Serverless container hosting
- **Amazon Cognito User Pools** - User authentication and authorization
- **Amazon S3** - Storage for generated content and assets
- **Amazon VPC** - Network isolation (optional)

## Features

- 🐳 **Containerized Deployment** - ECS Fargate with ARM64 support
- 🔐 **Secure Authentication** - Cognito User Pools with JWT tokens
- 📦 **Container Registry** - ECR with lifecycle policies
- 💾 **Scalable Storage** - S3 with encryption and lifecycle management
- 🌐 **Network Security** - VPC with public/private subnets
- 🏷️ **Flag-based Deployment** - Conditional resource creation

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate permissions
- Docker (for building and pushing container images)

## Quick Start

1. **Configure your deployment**
   
   Edit `flag.tfvars` to enable/disable resources:
   ```hcl
   create = {
     cognito_user_pool = true
     s3_bucket         = true
     ecr               = true
     ecs               = true
     vpc               = true
   }
   ```

   Customize `values.tfvars` for your environment (environment variables are configured here).

2. **Deploy the infrastructure**
   ```bash
   ./deploy.sh
   ```

   Or manually:
   ```bash
   cd aws_base_infra
   terraform init
   terraform plan -var-file="../values.tfvars" -var-file="../flag.tfvars"
   terraform apply -var-file="../values.tfvars" -var-file="../flag.tfvars"
   ```

## Environment Variables Configuration

The ECS task definition includes all necessary environment variables from your JSON configuration:

- **AWS Configuration**: Region, credentials, Bedrock agent ARN
- **Flask Configuration**: App settings, server configuration
- **Cognito Integration**: User pool ID, client ID, JWKS URL
- **S3 Integration**: Bucket name, base path
- **Media Processing**: FFmpeg settings, file formats
- **Security**: Session settings, CORS configuration

These are configured in `values.tfvars` under `ecs_conf.environment_variables`.

## Directory Structure

```
terraform/
├── aws_base_infra/           # Main infrastructure configuration
│   ├── providers.tf          # Terraform and AWS provider configuration
│   ├── variables.tf          # Input variables
│   ├── locals.tf            # Local values and naming conventions
│   ├── main.tf              # Main resource definitions
│   ├── ecs.tf               # ECS cluster and service
│   ├── vpc.tf               # VPC configuration
│   └── outputs.tf           # Output values
├── modules/                  # Reusable Terraform modules
│   ├── cognito/             # Cognito User Pool module
│   ├── ecr/                 # ECR repository module
│   ├── ecs/                 # ECS Fargate module
│   ├── s3_bucket/           # S3 bucket module
│   └── vpc/                 # VPC module
├── flag.tfvars              # Feature flags for resource creation
├── values.tfvars            # Configuration values
├── deploy.sh               # Deployment script
└── README.md               # This file
```

## Configuration

### Feature Flags (`flag.tfvars`)

Control which resources to create:

| Flag | Description | Default |
|------|-------------|---------|
| `cognito_user_pool` | Create Cognito User Pool for authentication | `true` |
| `s3_bucket` | Create S3 bucket for content storage | `true` |
| `ecr` | Create ECR repository for container images | `true` |
| `ecs` | Create ECS cluster and service | `true` |
| `vpc` | Create custom VPC (uses default VPC if false) | `true` |

### Environment Configuration (`values.tfvars`)

Key configurations:

- **Basic Settings**: Region, environment, project name
- **ECS Configuration**: CPU, memory, container settings
- **Environment Variables**: All Flask app environment variables
- **Cognito**: User pool settings, password policies
- **ECR**: Repository settings, lifecycle policies
- **S3**: Bucket configuration, lifecycle policies

## Container Deployment

After infrastructure deployment:

1. **Build and push your container**:
   ```bash
   # Get ECR login token
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

   # Build image
   docker build -t promogen-ai-flask-app .

   # Tag image
   docker tag promogen-ai-flask-app:latest <ecr-repository-url>:latest

   # Push image
   docker push <ecr-repository-url>:latest
   ```

2. **Update ECS service** (if needed):
   ```bash
   aws ecs update-service --cluster <cluster-name> --service <service-name> --force-new-deployment
   ```

## Outputs

After deployment, Terraform will output important values:

```hcl
# Authentication
cognito_user_pool_id         = "us-east-1_XXXXXXXXX"
cognito_user_pool_client_id  = "XXXXXXXXXXXXXXXXXXXXXXXXXX"

# Container Registry
ecr_repository_url           = "123456789012.dkr.ecr.us-east-1.amazonaws.com/promogen-ai-dev-promogen-ai-flask-app"

# ECS Service
ecs_cluster_name            = "promogen-ai-dev-promogen-ai-cluster"
ecs_service_name            = "promogen-ai-dev-promogen-ai-service"

# Storage
s3_storage_bucket_name      = "promogen-ai-dev-storage-xxxxxxxx"

# Network
vpc_id                      = "vpc-xxxxxxxxx"
```

## Security Features

- **Container Security**: ECS Fargate with ARM64 runtime
- **Authentication**: Cognito User Pools with JWT tokens
- **Data Encryption**: S3 server-side encryption
- **Network Security**: VPC with private subnets for ECS tasks
- **Access Control**: IAM roles with least privilege
- **Container Scanning**: ECR vulnerability scanning

## Cost Optimization

- **Serverless**: ECS Fargate with automatic scaling
- **ARM64**: Cost-effective ARM-based containers
- **Lifecycle Policies**: ECR and S3 automatic cleanup
- **Resource Tagging**: Cost allocation and tracking

## Monitoring and Logging

- **CloudWatch Logs**: ECS task logging with retention policies
- **Container Insights**: ECS cluster monitoring
- **ECR Scanning**: Automated vulnerability scanning

## Troubleshooting

### Common Issues

1. **ECR Access**: Ensure your AWS credentials have ECR permissions
2. **ECS Task Failures**: Check CloudWatch logs for container errors
3. **Resource Limits**: Verify AWS service quotas for your account
4. **Naming Conflicts**: S3 bucket names must be globally unique

### Debugging

```bash
# Check ECS service status
aws ecs describe-services --cluster <cluster-name> --services <service-name>

# View ECS task logs
aws logs tail /ecs/<task-family> --follow

# Check ECR repository
aws ecr describe-repositories --repository-names <repository-name>
```

## Clean Up

To destroy all resources:

```bash
cd aws_base_infra
terraform destroy -var-file="../values.tfvars" -var-file="../flag.tfvars"
```

## Support

For issues and questions:
- Check the AWS ECS documentation
- Review Terraform AWS provider documentation
- Check CloudWatch logs for application errors
