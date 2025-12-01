#!/bin/bash

echo "========================================"
echo "AWS Bedrock Diagnostic Tool"
echo "========================================"
echo ""

echo "Checking AWS Environment Variables:"
echo "-----------------------------------"

if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    echo "✓ AWS_ACCESS_KEY_ID is set"
else
    echo "✗ AWS_ACCESS_KEY_ID is NOT set"
fi

if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✓ AWS_SECRET_ACCESS_KEY is set"
else
    echo "✗ AWS_SECRET_ACCESS_KEY is NOT set"
fi

if [ -n "$AWS_PROFILE" ]; then
    echo "✓ AWS_PROFILE is set to: $AWS_PROFILE"
else
    echo "✗ AWS_PROFILE is NOT set"
fi

if [ -n "$AWS_BEARER_TOKEN_BEDROCK" ]; then
    echo "✓ AWS_BEARER_TOKEN_BEDROCK is set"
else
    echo "✗ AWS_BEARER_TOKEN_BEDROCK is NOT set"
fi

if [ -n "$AWS_REGION" ]; then
    echo "✓ AWS_REGION is set to: $AWS_REGION"
else
    echo "⚠ AWS_REGION is NOT set (will default to us-east-1)"
fi

echo ""
echo "Checking AWS CLI:"
echo "-----------------------------------"
if command -v aws &> /dev/null; then
    echo "✓ AWS CLI is installed"
    echo ""
    echo "AWS CLI Version:"
    aws --version
    echo ""
    echo "Attempting to verify credentials..."
    if aws sts get-caller-identity &> /dev/null; then
        echo "✓ AWS credentials are valid!"
        aws sts get-caller-identity
    else
        echo "✗ AWS credentials test failed"
        echo "  This could mean:"
        echo "  - Credentials are not configured"
        echo "  - Credentials are expired"
        echo "  - No internet connection to AWS"
    fi
else
    echo "✗ AWS CLI is NOT installed"
    echo "  Install with: sudo apt install awscli  # or  brew install awscli"
fi

echo ""
echo "========================================"
echo "Summary & Recommendations:"
echo "========================================"

# Count what credentials are set
creds_count=0
[ -n "$AWS_ACCESS_KEY_ID" ] && ((creds_count++))
[ -n "$AWS_PROFILE" ] && ((creds_count++))
[ -n "$AWS_BEARER_TOKEN_BEDROCK" ] && ((creds_count++))

if [ $creds_count -eq 0 ]; then
    echo "❌ NO AWS CREDENTIALS FOUND"
    echo ""
    echo "You need to set ONE of these:"
    echo ""
    echo "Option 1: AWS Access Keys"
    echo "  export AWS_ACCESS_KEY_ID=your-key"
    echo "  export AWS_SECRET_ACCESS_KEY=your-secret"
    echo "  export AWS_REGION=us-east-1"
    echo ""
    echo "Option 2: AWS Profile"
    echo "  export AWS_PROFILE=your-profile"
    echo "  export AWS_REGION=us-east-1"
    echo ""
    echo "Option 3: Bearer Token"
    echo "  export AWS_BEARER_TOKEN_BEDROCK=your-token"
    echo "  export AWS_REGION=us-east-1"
    echo ""
    echo "After setting, add to ~/.bashrc to make permanent:"
    echo "  echo 'export AWS_ACCESS_KEY_ID=...' >> ~/.bashrc"
    echo "  source ~/.bashrc"
elif [ $creds_count -eq 1 ]; then
    echo "✓ AWS credentials are configured"
    echo ""
    echo "Next steps:"
    echo "1. Ensure model access is enabled in AWS Bedrock Console"
    echo "2. Restart OpenCode: ~/.bun/bin/bun dev"
    echo "3. Test with: /models command"
else
    echo "⚠ Multiple credential methods detected"
    echo "  Only one method is needed. AWS will use them in this priority:"
    echo "  1. AWS_BEARER_TOKEN_BEDROCK"
    echo "  2. AWS_ACCESS_KEY_ID"
    echo "  3. AWS_PROFILE"
fi

echo ""
echo "========================================"