#!/bin/bash

echo "🚀 Fast Code Update (Training Lambda)"
echo "===================================="

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS credentials not configured"
    exit 1
fi

TEMP_DIR=$(mktemp -d)
echo "📁 Temp directory: $TEMP_DIR"

cp -r ./shared/ "$TEMP_DIR/"
cp -r ./training/ "$TEMP_DIR/"

cat > "$TEMP_DIR/Dockerfile" << 'EOF'
FROM --platform=linux/amd64 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-training-lambda:latest
COPY shared/ /var/task/shared/
COPY training/ /var/task/training/
EOF

cd "$TEMP_DIR"
docker build --platform=linux/amd64 -t yoga-training-lambda:code-update .
docker tag yoga-training-lambda:code-update 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-training-lambda:latest

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 830251426724.dkr.ecr.us-east-1.amazonaws.com
docker push 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-training-lambda:latest

aws lambda update-function-code \
    --function-name yoga-training-lambda \
    --image-uri 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-training-lambda:latest \
    --region us-east-1

echo "✅ Training Lambda updated with 10 frames + lower thresholds!"
rm -rf "$TEMP_DIR"
