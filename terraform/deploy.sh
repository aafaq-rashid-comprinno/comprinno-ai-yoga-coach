#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "flag.tfvars" ] || [ ! -f "values.tfvars" ]; then
    print_error "Please run this script from the terraform directory"
    exit 1
fi

# Change to aws_base_infra directory
cd aws_base_infra

print_status "Initializing Terraform..."
terraform init

print_status "Validating Terraform configuration..."
terraform validate

print_status "Planning Terraform deployment..."
terraform plan -var-file="../values.tfvars" -var-file="../flag.tfvars"

# Ask for confirmation
echo
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Applying Terraform configuration..."
    terraform apply -var-file="../values.tfvars" -var-file="../flag.tfvars" -auto-approve
    
    print_status "Deployment completed successfully!"
    
    # Show outputs
    echo
    print_status "Important outputs:"
    terraform output
else
    print_warning "Deployment cancelled."
fi
