#!/bin/bash

echo "🚀 Fast Code Update (Container Lambda)"
echo "====================================="

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS credentials not configured"
    exit 1
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
echo "📁 Temp directory: $TEMP_DIR"

# Copy only code files (not dependencies)
cp -r shared/ training/ testing/ "$TEMP_DIR/"

# Create minimal Dockerfile for code update
cat > "$TEMP_DIR/Dockerfile" << 'EOF'
FROM 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-training-lambda:latest
COPY shared/ /var/task/shared/
COPY training/ /var/task/training/
COPY testing/ /var/task/testing/
EOF

# Build and push updated image
cd "$TEMP_DIR"
docker build -t yoga-training-lambda:code-update .
docker tag yoga-training-lambda:code-update 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-training-lambda:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 830251426724.dkr.ecr.us-east-1.amazonaws.com
docker push 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-training-lambda:latest

# Update Lambda function
aws lambda update-function-code \
    --function-name yoga-training-lambda \
    --image-uri 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-training-lambda:latest \
    --region us-east-1

echo "✅ Code updated successfully!"
rm -rf "$TEMP_DIR"
