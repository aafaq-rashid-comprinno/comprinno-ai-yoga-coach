#!/bin/bash

echo "🚀 Fast Code Update (Testing Lambda)"
echo "===================================="

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS credentials not configured"
    exit 1
fi

# Create temp directory and copy files from current location
TEMP_DIR=$(mktemp -d)
echo "📁 Temp directory: $TEMP_DIR"

# Copy files from current directory
cp -r ./shared/ "$TEMP_DIR/"
cp -r ./testing/ "$TEMP_DIR/"

# Create minimal Dockerfile with platform specification
cat > "$TEMP_DIR/Dockerfile" << 'EOF'
FROM --platform=linux/amd64 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-testing-lambda:latest
COPY shared/ /var/task/shared/
COPY testing/ /var/task/testing/
EOF

# Build with platform specification
cd "$TEMP_DIR"
docker build --platform=linux/amd64 -t yoga-testing-lambda:code-update .
docker tag yoga-testing-lambda:code-update 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-testing-lambda:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 830251426724.dkr.ecr.us-east-1.amazonaws.com
docker push 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-testing-lambda:latest

# Update Lambda function
aws lambda update-function-code \
    --function-name yoga-testing-lambda \
    --image-uri 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-testing-lambda:latest \
    --region us-east-1

echo "✅ Testing Lambda code updated successfully!"
rm -rf "$TEMP_DIR"
