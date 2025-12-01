# AWS Bedrock Configuration for OpenCode

Your `opencode.json` is now configured with the correct inference profile IDs. Now you need to set up AWS credentials.

## AWS Bedrock requires one of three authentication methods:

### Option 1: AWS Bearer Token (Simplest for API Keys)
This is a long-term API key from the AWS Bedrock console:

1. Go to the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Settings** > **API Keys** (if available in your region)
3. Generate a long-term API key
4. Set the environment variable:

```bash
export AWS_BEARER_TOKEN_BEDROCK=your-bearer-token-here
export AWS_REGION=us-east-1  # or your preferred region
```

### Option 2: AWS Access Keys (IAM User)
If you have IAM user credentials:

1. Create an IAM user in AWS Console
2. Attach the `AmazonBedrockFullAccess` policy
3. Generate access keys for the user
4. Set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key
export AWS_REGION=us-east-1  # or your preferred region
```

### Option 3: AWS Profile (SSO/CLI)
If you use AWS CLI with SSO:

1. Configure AWS CLI: `aws configure sso`
2. Login: `aws sso login`
3. Set the profile:

```bash
export AWS_PROFILE=your-profile-name
export AWS_REGION=us-east-1  # or your preferred region
```

## Make it Permanent

Add the exports to your shell profile so they persist:

```bash
# Add to ~/.bashrc or ~/.bash_profile
echo 'export AWS_ACCESS_KEY_ID=your-key' >> ~/.bashrc
echo 'export AWS_SECRET_ACCESS_KEY=your-secret' >> ~/.bashrc
echo 'export AWS_REGION=us-east-1' >> ~/.bashrc
source ~/.bashrc
```

## Important: Model Access

Before using any model, you MUST request access in AWS Bedrock:

1. Go to [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Click **Model access** in the left sidebar
3. Click **Enable specific models** or **Manage model access**
4. Select the Anthropic Claude models you want to use:
   - Claude 3.5 Sonnet v2
   - Claude 3.5 Haiku
5. Submit the access request
6. Wait for approval (usually instant for most models)

## Available Models in Your Config

Your `opencode.json` is configured with these inference profiles:
- `us.anthropic.claude-3-5-sonnet-20241022-v2:0` - Claude 3.5 Sonnet v2 (US)
- `us.anthropic.claude-3-5-haiku-20241022-v1:0` - Claude 3.5 Haiku (US)
- `eu.anthropic.claude-3-5-sonnet-20241022-v2:0` - Claude 3.5 Sonnet v2 (EU)

## Test Your Setup

After setting credentials, test with:

```bash
~/.bun/bin/bun dev
```

Then in OpenCode TUI, run `/models` to verify Bedrock models appear.

## Troubleshooting

If you get errors:
1. Verify credentials are set: `echo $AWS_ACCESS_KEY_ID`
2. Check region: `echo $AWS_REGION`
3. Verify model access in Bedrock console
4. Ensure your IAM user/role has `bedrock:InvokeModel` permission
5. Check the model ID matches the inference profile format (e.g., `us.anthropic.*` not `anthropic.*`)

## Cost Note

AWS Bedrock charges per token usage. Check [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) for current rates.