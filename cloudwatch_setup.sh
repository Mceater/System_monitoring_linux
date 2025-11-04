#!/bin/bash
#
# CloudWatch Setup Script
# Helps configure AWS credentials and test CloudWatch connectivity
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== CloudWatch Setup ===${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${YELLOW}AWS CLI is not installed.${NC}"
    echo "Installing AWS CLI..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install awscli
        else
            echo "Please install AWS CLI manually: https://aws.amazon.com/cli/"
            exit 1
        fi
    fi
fi

# Check AWS credentials
echo -e "${BLUE}Checking AWS credentials...${NC}"
if aws sts get-caller-identity &> /dev/null; then
    echo -e "${GREEN}AWS credentials are configured.${NC}"
    aws sts get-caller-identity
else
    echo -e "${YELLOW}AWS credentials not found.${NC}"
    echo ""
    echo "To configure AWS credentials, run:"
    echo "  aws configure"
    echo ""
    echo "Or set environment variables:"
    echo "  export AWS_ACCESS_KEY_ID=your_access_key"
    echo "  export AWS_SECRET_ACCESS_KEY=your_secret_key"
    echo "  export AWS_DEFAULT_REGION=us-east-1"
    echo ""
    read -p "Do you want to configure AWS credentials now? (y/n): " configure
    if [[ $configure == "y" || $configure == "Y" ]]; then
        aws configure
    else
        echo "Skipping AWS configuration."
        exit 0
    fi
fi

# Test CloudWatch access
echo ""
echo -e "${BLUE}Testing CloudWatch access...${NC}"
region=$(aws configure get region || echo "us-east-1")
echo "Region: $region"

if aws cloudwatch list-metrics --namespace SystemMonitor --region "$region" &> /dev/null; then
    echo -e "${GREEN}CloudWatch access successful!${NC}"
else
    echo -e "${YELLOW}CloudWatch access test failed, but this might be normal if no metrics exist yet.${NC}"
    echo "The monitor will still work, but CloudWatch export may fail."
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "To use CloudWatch with the monitor, run:"
echo "  python monitor.py --cloudwatch --region $region"

