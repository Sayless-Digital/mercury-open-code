#!/bin/bash

# Set AWS Bedrock credentials
export AWS_BEARER_TOKEN_BEDROCK=ABSKQmVkcm9ja0FQSUtleS15a2FpLWF0LTQ4NzM3NTg4MzYyNTpBNFlrQnNOVFJ5QVZEanlLTkIwbjM2ZU01ZzNtbXF4MnYvMHNsTEM3aGZXcFgvekxRNjdLWXpXaDhqZz0=
export AWS_REGION=us-east-1

echo "✓ AWS credentials set in current session"
echo ""
echo "Testing credentials..."
./check-aws-setup.sh