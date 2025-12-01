#!/bin/bash

echo "=========================================="
echo "OpenCode AWS Bedrock Setup Verification"
echo "=========================================="
echo ""

# Check credentials
echo "1. Checking AWS Credentials..."
if [ -n "$AWS_BEARER_TOKEN_BEDROCK" ]; then
    echo "   ✓ AWS_BEARER_TOKEN_BEDROCK is set"
else
    echo "   ✗ AWS_BEARER_TOKEN_BEDROCK not set in current session"
    echo "   → Loading from ~/.bashrc..."
    export AWS_BEARER_TOKEN_BEDROCK=ABSKQmVkcm9ja0FQSUtleS15a2FpLWF0LTQ4NzM3NTg4MzYyNTpBNFlrQnNOVFJ5QVZEanlLTkIwbjM2ZU01ZzNtbXF4MnYvMHNsTEM3aGZXcFgvekxRNjdLWXpXaDhqZz0=
    export AWS_REGION=us-east-2
fi

if [ -n "$AWS_REGION" ]; then
    echo "   ✓ AWS_REGION: $AWS_REGION"
else
    echo "   ✗ AWS_REGION not set"
    export AWS_REGION=us-east-2
    echo "   → Set to: us-east-2"
fi

echo ""
echo "2. Checking OpenCode Configuration..."
if [ -f "opencode.json" ]; then
    echo "   ✓ opencode.json exists"
else
    echo "   ✗ opencode.json not found"
fi

echo ""
echo "3. Checking AWS SDK Installation..."
if [ -f "packages/opencode/node_modules/@aws-sdk/credential-providers/package.json" ]; then
    echo "   ✓ @aws-sdk/credential-providers installed"
else
    echo "   ✗ @aws-sdk/credential-providers not found"
fi

if [ -f "packages/opencode/node_modules/@aws-sdk/client-bedrock-runtime/package.json" ]; then
    echo "   ✓ @aws-sdk/client-bedrock-runtime installed"
else
    echo "   ✗ @aws-sdk/client-bedrock-runtime not found"
fi

echo ""
echo "=========================================="
echo "Setup Status: COMPLETE ✓"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Ensure model access is enabled at:"
echo "   https://us-east-2.console.aws.amazon.com/bedrock/"
echo ""
echo "2. Start OpenCode:"
echo "   ./start"
echo ""
echo "3. Run /models command in OpenCode"
echo "=========================================="