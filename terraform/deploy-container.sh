#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "values.tfvars" ]; then
    print_error "Please run this script from the terraform directory"
    exit 1
fi

# Get ECR repository URL from Terraform output
cd aws_base_infra
ECR_URL=$(terraform output -raw ecr_repository_url 2>/dev/null)

if [ -z "$ECR_URL" ]; then
    print_error "Could not get ECR repository URL. Make sure infrastructure is deployed."
    exit 1
fi

print_status "ECR Repository URL: $ECR_URL"

# Extract region and account ID from ECR URL
REGION=$(echo $ECR_URL | cut -d'.' -f4)
ACCOUNT_ID=$(echo $ECR_URL | cut -d'.' -f1 | cut -d'/' -f3)

print_status "Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Go back to project root to build Docker image
cd ../../services/ui

print_status "Building Docker image..."
docker build -t promogen-ai-flask-app .

print_status "Tagging image for ECR..."
docker tag promogen-ai-flask-app:latest $ECR_URL:latest

print_status "Pushing image to ECR..."
docker push $ECR_URL:latest

# Update ECS service
cd ../../terraform/aws_base_infra
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
SERVICE_NAME=$(terraform output -raw ecs_service_name)

print_status "Updating ECS service..."
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment --region $REGION

print_status "Container deployment completed successfully!"
print_status "Cluster: $CLUSTER_NAME"
print_status "Service: $SERVICE_NAME"
