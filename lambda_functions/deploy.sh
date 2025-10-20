#!/bin/bash

# Lambda Deployment Script for Yoga Evaluation System
# Handles Docker multi-architecture builds from Mac to Lambda (linux/amd64)

set -e

echo "🚀 Yoga Evaluation System - Lambda Deployment"
echo "=============================================="
echo ""

# Configuration - UPDATE THESE FOR YOUR AWS ACCOUNT
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-830251426724}"
ECR_REPO_TRAINING="yoga-training-lambda"
ECR_REPO_TESTING="yoga-testing-lambda"
LAMBDA_TRAINING="yoga-training-lambda"
LAMBDA_TESTING="yoga-testing-lambda"

# Parse arguments
COMPONENT=${1:-all}  # all, training, testing

case $COMPONENT in
  training)
    echo "📦 Deploying Training Lambda only..."
    ;;
  testing)
    echo "📦 Deploying Testing Lambda only..."
    ;;
  all)
    echo "📦 Deploying both Lambda functions..."
    ;;
  *)
    echo "❌ Invalid component: $COMPONENT"
    echo "Usage: ./deploy.sh [training|testing|all]"
    exit 1
    ;;
esac

echo ""

# Check AWS credentials
echo "🔍 Checking AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured"
    echo ""
    echo "Please configure AWS credentials:"
    echo "  export AWS_ACCESS_KEY_ID='your-key'"
    echo "  export AWS_SECRET_ACCESS_KEY='your-secret'"
    echo "  export AWS_SESSION_TOKEN='your-token'  # If using temporary credentials"
    echo ""
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ Connected to AWS Account: $ACCOUNT_ID"

# Check if buildx is available
echo ""
echo "🔍 Checking Docker buildx..."
if ! docker buildx version &> /dev/null; then
    echo "❌ Docker buildx not found. Please install Docker Desktop or enable buildx."
    echo ""
    echo "See DOCKER-BUILDX-GUIDE.md for setup instructions"
    exit 1
fi

# Create buildx builder if it doesn't exist
if ! docker buildx inspect multiarch-builder &> /dev/null; then
    echo "🔨 Creating multiarch builder..."
    docker buildx create --name multiarch-builder --use --platform linux/amd64,linux/arm64
else
    echo "✅ Using existing multiarch builder"
    docker buildx use multiarch-builder
fi

# Function to build and push Docker image using buildx
build_and_push() {
  local LAMBDA_NAME=$1
  local ECR_REPO=$2
  local DOCKERFILE=$3
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🐳 Building $LAMBDA_NAME for Lambda (linux/amd64)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  
  # Login to ECR first
  echo "🔐 Logging into ECR..."
  aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
  
  # Full ECR image URI
  ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest"
  
  echo "🏗️  Building and pushing image for linux/amd64..."
  echo "   Source: $DOCKERFILE"
  echo "   Target: $ECR_IMAGE_URI"
  echo ""
  
  # Build and push using buildx for linux/amd64 (Lambda architecture)
  docker buildx build \
    --platform linux/amd64 \
    --file $DOCKERFILE \
    --tag $ECR_IMAGE_URI \
    --output type=image,push=true \
    --provenance=false \
    --progress=plain \
    .
  
  if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
  fi
  
  echo ""
  echo "✅ Image built and pushed successfully!"
  
  # Get image digest from ECR
  echo "🔍 Getting image digest from ECR..."
  IMAGE_DIGEST=$(aws ecr describe-images \
    --repository-name $ECR_REPO \
    --image-ids imageTag=latest \
    --region $AWS_REGION \
    --query 'imageDetails[0].imageDigest' \
    --output text)
  
  echo "📦 Image digest: $IMAGE_DIGEST"
  
  # Update Lambda function
  echo ""
  echo "🔄 Updating Lambda function: $LAMBDA_NAME..."
  aws lambda update-function-code \
    --function-name $LAMBDA_NAME \
    --image-uri $ECR_IMAGE_URI \
    --region $AWS_REGION \
    --no-cli-pager
  
  echo ""
  echo "⏳ Waiting for Lambda update to complete..."
  aws lambda wait function-updated \
    --function-name $LAMBDA_NAME \
    --region $AWS_REGION
  
  echo ""
  echo "✅ $LAMBDA_NAME deployed successfully!"
  echo ""
}

# Deploy components
if [ "$COMPONENT" = "training" ] || [ "$COMPONENT" = "all" ]; then
  build_and_push $LAMBDA_TRAINING $ECR_REPO_TRAINING "Dockerfile.training"
fi

if [ "$COMPONENT" = "testing" ] || [ "$COMPONENT" = "all" ]; then
  build_and_push $LAMBDA_TESTING $ECR_REPO_TESTING "Dockerfile.testing"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Next Steps:"
echo ""
echo "1. Test via UI:"
echo "   cd ../ui && ./run-local.sh"
echo ""
echo "2. Monitor Lambda logs:"
if [ "$COMPONENT" = "training" ] || [ "$COMPONENT" = "all" ]; then
  echo "   aws logs tail /aws/lambda/$LAMBDA_TRAINING --follow"
fi
if [ "$COMPONENT" = "testing" ] || [ "$COMPONENT" = "all" ]; then
  echo "   aws logs tail /aws/lambda/$LAMBDA_TESTING --follow"
fi
echo ""
echo "3. Check Lambda status:"
echo "   aws lambda get-function --function-name $LAMBDA_TRAINING"
echo ""
echo "4. View ECR images:"
echo "   aws ecr describe-images --repository-name $ECR_REPO_TRAINING"
echo ""
