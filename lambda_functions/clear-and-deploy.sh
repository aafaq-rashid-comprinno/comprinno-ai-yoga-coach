#!/bin/bash

# Clear Docker Cache and Deploy Fresh
# Use this to ensure no stale cache is used

set -e

echo "🧹 Clearing Docker Cache and Deploying Fresh"
echo "============================================="
echo ""

# Parse arguments
COMPONENT=${1:-testing}

echo "⚠️  This will clear Docker cache and rebuild everything from scratch"
echo "   This may take 5-10 minutes"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 1
fi

echo ""
echo "🧹 Step 1: Clearing Docker buildx cache..."
docker buildx prune -af || echo "No buildx cache to clear"

echo ""
echo "🧹 Step 2: Removing old images..."
docker rmi $(docker images -q 830251426724.dkr.ecr.us-east-1.amazonaws.com/yoga-*-lambda 2>/dev/null) 2>/dev/null || echo "No old images found"

echo ""
echo "🧹 Step 3: Clearing Docker system cache..."
docker system prune -f

echo ""
echo "✅ Cache cleared!"
echo ""
echo "🚀 Step 4: Starting fresh deployment..."
echo ""

./deploy.sh $COMPONENT
