#!/bin/bash

# AWS Bedrock Setup Script for OpenCode
# This script helps you configure AWS credentials for Bedrock

echo "========================================"
echo "AWS Bedrock Configuration for OpenCode"
echo "========================================"
echo ""

# Check if any AWS credentials are already set
if [ -n "$AWS_ACCESS_KEY_ID" ] || [ -n "$AWS_PROFILE" ] || [ -n "$AWS_BEARER_TOKEN_BEDROCK" ]; then
    echo "✓ AWS credentials detected in environment"
    [ -n "$AWS_ACCESS_KEY_ID" ] && echo "  - AWS_ACCESS_KEY_ID is set"
    [ -n "$AWS_PROFILE" ] && echo "  - AWS_PROFILE is set to: $AWS_PROFILE"
    [ -n "$AWS_BEARER_TOKEN_BEDROCK" ] && echo "  - AWS_BEARER_TOKEN_BEDROCK is set"
    [ -n "$AWS_REGION" ] && echo "  - AWS_REGION is set to: $AWS_REGION" || echo "  - AWS_REGION not set (will default to us-east-1)"
    echo ""
else
    echo "⚠ No AWS credentials found in environment"
    echo ""
    echo "Choose your authentication method:"
    echo "1. AWS Access Keys (IAM User)"
    echo "2. AWS Profile (SSO/CLI)"
    echo "3. AWS Bearer Token (Bedrock API Key)"
    echo ""
    read -p "Enter choice (1-3): " choice
    
    case $choice in
        1)
            echo ""
            read -p "Enter AWS_ACCESS_KEY_ID: " access_key
            read -p "Enter AWS_SECRET_ACCESS_KEY: " secret_key
            read -p "Enter AWS_REGION (default: us-east-1): " region
            region=${region:-us-east-1}
            
            echo ""
            echo "Add these to your ~/.bashrc:"
            echo "export AWS_ACCESS_KEY_ID=$access_key"
            echo "export AWS_SECRET_ACCESS_KEY=$secret_key"
            echo "export AWS_REGION=$region"
            ;;
        2)
            echo ""
            read -p "Enter AWS_PROFILE name: " profile
            read -p "Enter AWS_REGION (default: us-east-1): " region
            region=${region:-us-east-1}
            
            echo ""
            echo "Add these to your ~/.bashrc:"
            echo "export AWS_PROFILE=$profile"
            echo "export AWS_REGION=$region"
            ;;
        3)
            echo ""
            read -p "Enter AWS_BEARER_TOKEN_BEDROCK: " token
            read -p "Enter AWS_REGION (default: us-east-1): " region
            region=${region:-us-east-1}
            
            echo ""
            echo "Add these to your ~/.bashrc:"
            echo "export AWS_BEARER_TOKEN_BEDROCK=$token"
            echo "export AWS_REGION=$region"
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    read -p "Do you want to add these to ~/.bashrc now? (y/n): " add_to_bashrc
    if [ "$add_to_bashrc" = "y" ]; then
        case $choice in
            1)
                echo "export AWS_ACCESS_KEY_ID=$access_key" >> ~/.bashrc
                echo "export AWS_SECRET_ACCESS_KEY=$secret_key" >> ~/.bashrc
                echo "export AWS_REGION=$region" >> ~/.bashrc
                ;;
            2)
                echo "export AWS_PROFILE=$profile" >> ~/.bashrc
                echo "export AWS_REGION=$region" >> ~/.bashrc
                ;;
            3)
                echo "export AWS_BEARER_TOKEN_BEDROCK=$token" >> ~/.bashrc
                echo "export AWS_REGION=$region" >> ~/.bashrc
                ;;
        esac
        echo "✓ Added to ~/.bashrc"
        echo "Run 'source ~/.bashrc' to load the variables"
    fi
fi

echo ""
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo "1. Request model access in AWS Bedrock Console:"
echo "   https://console.aws.amazon.com/bedrock/"
echo ""
echo "2. Enable these models:"
echo "   - Anthropic Claude 3.5 Sonnet v2"
echo "   - Anthropic Claude 3.5 Haiku"
echo ""
echo "3. Start OpenCode:"
echo "   ~/.bun/bin/bun dev"
echo ""
echo "4. Run /models in OpenCode to verify Bedrock models appear"
echo ""
echo "See AWS_BEDROCK_SETUP.md for detailed instructions"
echo "========================================"